"""`app/sdd_cli.py`：Bridge 呼叫 FSMRuntime CLI 的固定環境、rc 對映、逾時殺樹、動詞白名單、互斥鎖。

以假 SDD 樹（tests/fake_sdd.py）真起子行程——斷言的是「Bridge 送出了什麼、環境長什麼樣」，
不是假 CLI 的內部。ADR-XPLAT-016 §3.5、§4.1、§4.4、§9、§15。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil
import pytest

from app import sdd_cli
from app.errors import ApiError
from app.security import AuditLog
from tests.fake_sdd import make_fake_sdd, read_calls, seed_state, set_control

SECRET = "t0ken-" + "x" * 40


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_sdd(tmp_path / "sdd")


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "proj" / "build" / "reports" / "fsm"


@pytest.fixture
def audit(tmp_path: Path) -> AuditLog:
    return AuditLog(tmp_path / "audit.jsonl")


def _audit_entries(tmp_path: Path) -> list[dict]:
    path = tmp_path / "audit.jsonl"
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def _run(fake: Path, state_dir: Path, verb: str, args: list[str], *, project: str = "alpha",
         audit: AuditLog | None = None, timeout: float = 20.0) -> dict:
    return sdd_cli.run_verb(verb, args, sdd_root=fake, state_dir=state_dir, project=project,
                            audit=audit, timeout=timeout)


def _error(fake: Path, state_dir: Path, verb: str, args: list[str], **kw) -> ApiError:
    with pytest.raises(ApiError) as caught:
        _run(fake, state_dir, verb, args, **kw)
    return caught.value


# ── 固定環境、argv、cwd（§3.5）────────────────────────────────────────────────────────────
def test_the_argv_is_the_fixed_form_with_project_and_must_exist() -> None:
    argv = sdd_cli.build_cli_argv("delegate-enter", ["--reason", "r"], "訂單系統 v2")
    assert argv == [sys.executable, "-W", "ignore::RuntimeWarning", "-m",
                    "tools.fsm_runtime.fsm_runtime", "delegate-enter", "--project", "訂單系統 v2",
                    "--must-exist", "--reason", "r"]


def test_the_child_gets_the_fixed_environment_and_never_the_bridge_secrets(
        fake: Path, state_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    monkeypatch.setenv("BRIDGE_DB_DSN", f"postgresql://u:{SECRET}@db/x")
    monkeypatch.setenv("BRIDGE_SDD_WRITE_TOKEN", SECRET)
    monkeypatch.setenv("SDD_STATE_DIR", str(state_dir.parent / "elsewhere"))
    monkeypatch.setenv("SDD_PROJECT", "someone-else")
    monkeypatch.setenv("SDD_ROOT", "/not/this")
    monkeypatch.setenv("PYTHONPATH", "/evil/path")
    out = _run(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(
        reason="console-run run=R1 START", playbook_ref="run:R1"))
    assert out["ok"] is True and out["current_state"] == "AUTOCLAUDE_DELEGATED"
    (call,) = read_calls(fake)
    assert call["argv"] == ["delegate-enter", "--project", "alpha", "--must-exist", "--reason",
                            "console-run run=R1 START", "--playbook-ref", "run:R1"]
    assert call["warnoptions"] == ["ignore::RuntimeWarning"], "runpy 警告與成敗無關：用 -W 靜音"
    assert os.path.normcase(call["cwd"]) == os.path.normcase(str(fake)), "cwd＝SDD 版本目錄"
    assert Path(call["executable"]).exists(), "子行程用 Bridge 自己的直譯器（sys.executable）"
    env = call["env"]
    upper = {k.upper(): v for k, v in env.items()}
    assert upper["PYTHONPATH"] == str(fake), "PYTHONPATH 被換成版本目錄（不是繼承來的）"
    assert upper["PYTHONDONTWRITEBYTECODE"] == "1" and upper["PYTHONUTF8"] == "1"
    assert upper["SDD_ENABLE_RULE_FIRE_TELEMETRY"] == "0"
    assert upper["SDD_ENABLE_RULE_CATCH_TELEMETRY"] == "0"
    assert upper["SDD_STATE_DIR"] == str(state_dir) and upper["SDD_PROJECT"] == "alpha"
    assert sorted(k for k in upper if k.startswith("SDD_")) == [
        "SDD_ENABLE_RULE_CATCH_TELEMETRY", "SDD_ENABLE_RULE_FIRE_TELEMETRY", "SDD_PROJECT",
        "SDD_STATE_DIR"], "繼承來的 SDD_ROOT 等其他 SDD_* 一律移除"
    assert not [k for k in upper if k.startswith("BRIDGE_")], "BRIDGE_* 一個都不能洩進 CLI 子行程"
    assert SECRET not in json.dumps(call), "權杖與 DB 密碼不得出現在子行程的任何環境值"


def test_build_cli_env_strips_every_bridge_sdd_and_pythonpath_name_case_insensitively(
        tmp_path: Path) -> None:
    base = {"PATH": "/bin", "HOME": "/h", "bridge_x": "1", "Sdd_Anything": "2", "SDD_ROOT": "3",
            "pythonpath": "/evil", "BRIDGE_DB_DSN": "dsn", "KEEP": "me"}
    env = sdd_cli.build_cli_env(base, sdd_root=tmp_path / "v", state_dir=tmp_path / "s",
                                project="p")
    assert env["PATH"] == "/bin" and env["HOME"] == "/h" and env["KEEP"] == "me"
    assert not any(k.upper().startswith("BRIDGE_") for k in env)
    assert "SDD_ROOT" not in env and "Sdd_Anything" not in env and "pythonpath" not in env
    assert env["SDD_PROJECT"] == "p" and env["PYTHONPATH"] == str(tmp_path / "v")


# ── rc 表（§4.1）：每一格都對映到契約的 HTTP 與 reason ────────────────────────────────────────
def test_success_returns_the_single_json_line_including_noop(fake: Path, state_dir: Path) -> None:
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    args = sdd_cli.delegate_enter_args(reason="console-run run=R START", playbook_ref="run:R")
    first = _run(fake, state_dir, "delegate-enter", args)
    again = _run(fake, state_dir, "delegate-enter", args)
    assert first["entered"] is True and "noop" not in first
    assert again["noop"] is True, "已在委派態再 enter＝noop，rc 仍是 0"


def test_rc3_is_a_409_state_conflict_carrying_the_current_state(
        fake: Path, state_dir: Path, tmp_path: Path, audit: AuditLog) -> None:
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    err = _error(fake, state_dir, "negotiate-exit",
                 sdd_cli.negotiate_exit_args(reason="console-signoff x"), audit=audit)
    assert (err.status_code, err.body["reason"]) == (409, "fsm_state_conflict")
    assert err.body["current_state"] == "IMPLEMENTATION"
    assert err.body["detail"]["current_state"] == "IMPLEMENTATION"
    assert err.body["cli_error"] == "transition_not_allowed"


def test_rc4_is_a_422_invalid_argument_with_the_cli_error_code(
        fake: Path, state_dir: Path, tmp_path: Path) -> None:
    seed_state(state_dir, "alpha", "HUMAN_PENDING")
    err = _error(fake, state_dir, "spec-frozen", sdd_cli.freeze_args(
        stage="Stage-1", docs=["docs/missing.md"], root=str(tmp_path / "proj"),
        reason="console-freeze approver=a; reason=r", approver="a"))
    assert (err.status_code, err.body["reason"]) == (422, "sdd_invalid_argument")
    assert err.body["error"] == "doc_not_found"


def test_rc5_state_missing_is_404_and_unreadable_is_422(fake: Path, state_dir: Path) -> None:
    missing = _error(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(reason="r"))
    assert (missing.status_code, missing.body["reason"], missing.body["project"]) == (
        404, "fsm_not_found", "alpha")
    state_dir.mkdir(parents=True)
    (state_dir / "FSM-STATE-alpha.yaml").write_text("this: [is: not valid yaml", encoding="utf-8")
    broken = _error(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(reason="r"))
    assert (broken.status_code, broken.body["reason"]) == (422, "fsm_state_unreadable")


@pytest.mark.parametrize(("forced", "status", "reason"), [
    (1, 502, "sdd_cli_failed"),            # 非預期例外（traceback）
    (2, 500, "sdd_cli_usage"),             # argparse 用法錯誤＝Bridge 自己的 bug
    (6, 502, "sdd_cli_failed"),            # 未列於 rc 表的值：不猜、當 CLI 失敗
])
def test_other_return_codes_map_to_the_documented_errors_and_hide_stderr(
        forced: int, status: int, reason: str, fake: Path, state_dir: Path, tmp_path: Path,
        audit: AuditLog) -> None:
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    set_control(fake, rc={"delegate-enter": forced})
    err = _error(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(reason="r"),
                 audit=audit)
    assert (err.status_code, err.body["reason"]) == (status, reason)
    shown = json.dumps(err.body)
    assert "Traceback" not in shown and "forced traceback" not in shown
    entry = _audit_entries(tmp_path)[-1]
    assert entry["event"] == "sdd_cli" and entry["rc"] == forced
    if forced == 1:
        assert "forced traceback" in entry["stderr_tail"], "stderr 只進稽核（診斷用），不進回應"


def test_a_success_exit_with_a_non_json_stdout_is_a_502_not_a_silent_pass(
        fake: Path, state_dir: Path) -> None:
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    set_control(fake, raw_stdout={"delegate-enter": "garbage that is not json"})
    err = _error(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(reason="r"))
    assert (err.status_code, err.body["reason"]) == (502, "sdd_cli_failed")


def test_a_cli_that_cannot_be_started_is_a_502(
        fake: Path, state_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a, **_k):
        raise OSError("no such interpreter")

    monkeypatch.setattr(subprocess, "Popen", boom)
    err = _error(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(reason="r"))
    assert (err.status_code, err.body["reason"]) == (502, "sdd_cli_failed")


def test_without_a_usable_sdd_tree_the_call_is_503(state_dir: Path, tmp_path: Path) -> None:
    for root in (None, tmp_path / "nope"):
        with pytest.raises(ApiError) as caught:
            sdd_cli.run_verb("delegate-enter", ["--reason", "r"], sdd_root=root,
                             state_dir=state_dir, project="alpha")
        assert (caught.value.status_code, caught.value.body["reason"]) == (503, "sdd_unavailable")


# ── 逾時：整棵行程樹被殺（§3.5）────────────────────────────────────────────────────────────
def test_a_timeout_is_504_and_the_whole_process_tree_is_gone(
        fake: Path, state_dir: Path, tmp_path: Path, audit: AuditLog) -> None:
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    set_control(fake, sleep={"delegate-enter": 60})
    began = time.monotonic()
    err = _error(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(reason="r"),
                 audit=audit, timeout=5.0)
    assert (err.status_code, err.body["reason"]) == (504, "sdd_cli_timeout")
    assert time.monotonic() - began < 20, "逾時後不得卡在等行程"
    (call,) = read_calls(fake)
    deadline = time.monotonic() + 10
    while psutil.pid_exists(call["pid"]) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not psutil.pid_exists(call["pid"]), "逾時要殺掉 CLI（含 Windows 的啟動器殼與其子行程）"
    assert _audit_entries(tmp_path)[-1]["result"] == "timeout"
    # 逾時沒有改動狀態檔：該動詞在 sleep 時還沒寫任何東西
    assert "AUTOCLAUDE_DELEGATED" not in (state_dir / "FSM-STATE-alpha.yaml").read_text("utf-8")


# ── 動詞白名單（§3.5；F-4 的執行期面）────────────────────────────────────────────────────────
@pytest.mark.parametrize("verb", [
    "transition", "gate", "resume-from-escalation", "spec-audit", "check-impl",
    "complete-auto-compact", "reset-ledger", "reconcile", "show", "init", "",
])
def test_verbs_outside_the_whitelist_are_refused_before_any_process_starts(
        verb: str, fake: Path, state_dir: Path) -> None:
    err = _error(fake, state_dir, verb, ["--reason", "r"])
    assert (err.status_code, err.body["reason"]) == (500, "sdd_cli_usage")
    assert read_calls(fake) == [], "越界的動詞連子行程都不該起"


@pytest.mark.parametrize(("verb", "args"), [
    ("negotiate-exit", ["--outcome", "underspecified", "--reason", "r"]),     # §3.5：只准 agreed
    ("negotiate-exit", ["--reason", "r"]),                                    # 缺 --outcome
    ("negotiate-exit", ["--outcome", "agreed", "--outcome", "agreed", "--reason", "r"]),
    ("delegate-exit", ["--decision", "aborted", "--reason", "r"]),            # 只准 done｜failed
    ("delegate-exit", ["--reason", "r"]),                                     # 缺 --decision
    ("delegate-enter", []),                                                   # --reason 必填
    ("delegate-enter", ["--reason", "   "]),                                  # strip 後空白
    ("delegate-enter", ["--reason", "r", "--to", "IMPLEMENTATION"]),          # 不在旗標白名單
    # --project 由 Bridge 加
    ("delegate-enter", ["--project", "other", "--reason", "r"]),
    ("delegate-enter", ["--must-exist", "--reason", "r"]),                    # --must-exist 同上
    ("spec-frozen", ["--stage", "S", "--result", "PASS"]),
    ("negotiate-enter", ["--reason"]),                                        # 旗標沒有值
])
def test_flags_and_values_outside_the_whitelist_are_refused(
        verb: str, args: list[str], fake: Path, state_dir: Path) -> None:
    err = _error(fake, state_dir, verb, args)
    assert (err.status_code, err.body["reason"]) == (500, "sdd_cli_usage")
    assert read_calls(fake) == []


def test_a_reason_that_looks_like_a_flag_is_taken_as_a_value_not_parsed(
        fake: Path, state_dir: Path) -> None:
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    out = _run(fake, state_dir, "delegate-enter", ["--reason", "--decision done --to X"])
    assert out["ok"] is True
    assert read_calls(fake)[0]["argv"][-1] == "--decision done --to X"


def test_the_builders_only_produce_whitelisted_invocations() -> None:
    sdd_cli.check_allowed("spec-frozen", sdd_cli.freeze_args(
        stage="Stage-1", docs=["a.md", "b.md"], root="/r", reason="x", approver="y"))
    sdd_cli.check_allowed("negotiate-enter", sdd_cli.negotiate_enter_args(
        reason="x", contract_ref="docs/tcs.md"))
    sdd_cli.check_allowed("negotiate-exit", sdd_cli.negotiate_exit_args(reason="x"))
    sdd_cli.check_allowed("delegate-enter", sdd_cli.delegate_enter_args(
        reason="x", playbook_ref="run:1"))
    for decision in ("done", "failed"):
        sdd_cli.check_allowed("delegate-exit", sdd_cli.delegate_exit_args(
            decision=decision, reason="x"))
    assert sdd_cli.ALLOWED_VERBS == {
        "spec-frozen", "negotiate-enter", "negotiate-exit", "delegate-enter", "delegate-exit"}


# ── (狀態目錄, 專案鍵) 互斥鎖（§3.5）──────────────────────────────────────────────────────────
def test_the_state_guard_serializes_the_same_state_dir_and_project(tmp_path: Path) -> None:
    events: list[str] = []
    entered = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with sdd_cli.state_guard(tmp_path, "alpha"):
            events.append("a-in")
            entered.set()
            release.wait(5)
            events.append("a-out")

    def waiter() -> None:
        with sdd_cli.state_guard(tmp_path, "alpha"):
            events.append("b-in")

    first = threading.Thread(target=holder)
    first.start()
    assert entered.wait(5)
    second = threading.Thread(target=waiter)
    second.start()
    time.sleep(0.3)
    assert events == ["a-in"], "同一 (狀態目錄, 專案鍵) 的第二個臨界區必須等第一個結束"
    release.set()
    first.join(5)
    second.join(5)
    assert events == ["a-in", "a-out", "b-in"]


def test_the_state_guard_does_not_block_other_projects_or_directories_and_is_reentrant(
        tmp_path: Path) -> None:
    with sdd_cli.state_guard(tmp_path, "alpha"):
        # 可重入：同臨界區內連呼多次 CLI
        with sdd_cli.state_guard(tmp_path, "alpha"):
            pass
        results: list[str] = []

        def other() -> None:
            with sdd_cli.state_guard(tmp_path, "beta"):
                results.append("beta")
            with sdd_cli.state_guard(tmp_path / "elsewhere", "alpha"):
                results.append("elsewhere")

        thread = threading.Thread(target=other)
        thread.start()
        thread.join(5)
        assert results == ["beta", "elsewhere"], "不同專案鍵、不同狀態目錄互不阻塞"


def test_the_lock_key_ignores_case_nfc_and_the_lock_table_does_not_grow(tmp_path: Path) -> None:
    keys = {sdd_cli._lock_key(tmp_path, name) for name in ("Alpha", "alpha", "ALPHA")}
    assert len(keys) == 1, "Windows／macOS 檔名不分大小寫：寧可多互斥也不漏"
    nfd, nfc = "e\N{COMBINING ACUTE ACCENT}cole", "école"
    assert sdd_cli._lock_key(tmp_path, nfd) == sdd_cli._lock_key(tmp_path, nfc)
    before = len(sdd_cli._locks)
    with sdd_cli.state_guard(tmp_path, "transient-project"):
        assert len(sdd_cli._locks) == before + 1
    assert len(sdd_cli._locks) == before, "鎖表是弱參照：沒人持有就回收"


def test_the_cli_call_runs_inside_the_guard_so_a_reader_waits_for_it(
        fake: Path, state_dir: Path) -> None:
    """CLI 本身不自己拿鎖（呼叫端包 state_guard）；但讀取端（GET）與寫入端用同一把鎖。這裡驗：
    持鎖時另一條執行緒的臨界區進不去，放開後立刻進得去。"""
    seed_state(state_dir, "alpha", "IMPLEMENTATION")
    observed: list[str] = []
    with sdd_cli.state_guard(state_dir, "alpha"):
        _run(fake, state_dir, "delegate-enter", sdd_cli.delegate_enter_args(reason="r"))

        def reader() -> None:
            with sdd_cli.state_guard(state_dir, "alpha"):
                observed.append("read")

        thread = threading.Thread(target=reader)
        thread.start()
        time.sleep(0.3)
        assert observed == []
    thread.join(5)
    assert observed == ["read"]


# ══ 研究面動詞表（ResearchToPRD；TCS-ResearchToPRD-P0-20261102 AC-960-13；ADR-XPLAT-017 D2）══
# 上面各列一字不動：既有五動詞的白名單、旗標與 `run_verb` 照舊；研究面是獨立的動詞表與獨立的
# 執行入口 `run_research_verb`（只對 `/research/*` 開放）。
_OUTER_KEY = "research-demo"
_INNER_KEY = "autoclaude-demo"
_FORBIDDEN_RESEARCH_VERBS = [
    ("resume-from-escalation", ["--to", "SPEC_DRAFTING", "--reason", "r"]),
    ("reconcile", ["--reason", "r"]),
    ("spec-audit", ["--reason", "r"]),
    ("check-impl", ["--reason", "r"]),
    ("complete-auto-compact", ["--reason", "r"]),
    ("reset-ledger", ["--reason", "r"]),
    ("negotiate-exit", ["--outcome", "underspecified", "--reason", "r"]),
    ("negotiate-enter", ["--reason", "r"]),
    ("delegate-enter", ["--reason", "r"]),
    ("", ["--reason", "r"]),
]


def _research_error(fake: Path, state_dir: Path, verb: str, args: list[str], *,
                    project: str = _OUTER_KEY, **kw) -> ApiError:
    with pytest.raises(ApiError) as caught:
        sdd_cli.run_research_verb(verb, args, sdd_root=fake, state_dir=state_dir,
                                  project=project, **kw)
    return caught.value


def test_AT_960_13_1_the_five_existing_verbs_stay_and_the_research_table_is_separate() -> None:
    assert sdd_cli.ALLOWED_VERBS == {
        "spec-frozen", "negotiate-enter", "negotiate-exit", "delegate-enter", "delegate-exit"}
    assert sdd_cli.RESEARCH_VERBS == {
        "show", "transition", "gate", "spec-frozen", "spec-refreeze"}
    assert sdd_cli.RESEARCH_VERBS & sdd_cli.ALLOWED_VERBS == {"spec-frozen"}, \
        "兩張表只共用 spec-frozen；研究面其餘動詞不得滲進既有白名單"
    assert sdd_cli.RESEARCH_VERBS is not sdd_cli.ALLOWED_VERBS


@pytest.mark.parametrize(("verb", "args"), _FORBIDDEN_RESEARCH_VERBS,
                         ids=[v or "empty" for v, _a in _FORBIDDEN_RESEARCH_VERBS])
def test_AT_960_13_1_a_forbidden_verb_is_refused_before_any_process_starts(
        verb: str, args: list[str], fake: Path, state_dir: Path) -> None:
    err = _research_error(fake, state_dir, verb, args)
    assert (err.status_code, err.body["reason"]) == (500, "sdd_cli_usage"), f"verb={verb!r}"
    assert read_calls(fake) == [], f"禁用動詞 {verb!r} 連子行程都不該起"


@pytest.mark.parametrize("verb", ["show", "transition", "gate", "spec-refreeze"])
def test_AT_960_13_1_the_existing_entry_refuses_every_research_only_verb(
        verb: str, fake: Path, state_dir: Path) -> None:
    """`:freeze` 與 `/autoclaude/runs` 的 sdd 區塊走的 `run_verb` 不認研究面動詞。"""
    err = _error(fake, state_dir, verb, ["--reason", "r"])
    assert (err.status_code, err.body["reason"]) == (500, "sdd_cli_usage")
    assert read_calls(fake) == []


def test_AT_960_13_1_only_the_research_surface_names_the_research_entry() -> None:
    import ast

    app_dir = Path(sdd_cli.__file__).resolve().parent
    names = {"run_research_verb", "check_research_allowed", "build_research_argv",
             "build_research_env", "research_transition_args", "research_gate_args",
             "research_freeze_args", "research_refreeze_args", "validate_research_approver"}
    found: set[str] = set()
    for path in sorted(app_dir.rglob("*.py")):
        rel = path.relative_to(app_dir).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            ident = (node.id if isinstance(node, ast.Name) else node.attr
                     if isinstance(node, ast.Attribute) else node.name
                     if isinstance(node, ast.alias) else "")
            if ident in names or ident.startswith("RESEARCH_VERB"):
                found.add(rel)
    allowed = {rel for rel in found if rel == "sdd_cli.py" or rel == "routers/research.py"
               or rel.startswith("research/")}
    assert found and found == allowed, \
        f"研究面動詞入口只准研究面自己引用（:freeze 與 sdd run 不得）：{sorted(found - allowed)}"


# ── 動詞旗標與值域矩陣（鍵類別 × 動詞 × 旗標 × 值；逐格表驅動）─────────────────────────────
def _tr(to: str, reason: str = "why", trigger: str = "research_bridge") -> list[str]:
    return ["--to", to, "--reason", reason, "--trigger", trigger]


def _gt(gate: str, result: str = "PASS", reason: str = "why") -> list[str]:
    return ["--gate", gate, "--result", result, "--reason", reason]


def _fz(stage: str, docs: tuple[str, ...] = ("a.md",), *, drop: str | None = None) -> list[str]:
    args = ["--stage", stage]
    for doc in docs:
        args += ["--doc", doc]
    tail = ["--digest", "--root", "/r", "--reason", "x", "--approver", "alice", "--json"]
    if drop is not None:
        at = tail.index(drop)
        tail = tail[:at] + tail[at + (1 if drop in ("--digest", "--json") else 2):]
    return [*args, *tail]


def _rf(docs: tuple[str, ...] = ("a.md",), *, drop: str | None = None) -> list[str]:
    args: list[str] = []
    for doc in docs:
        args += ["--doc", doc]
    tail = ["--root", "/r", "--reason", "x", "--approver", "alice"]
    if drop is not None:
        at = tail.index(drop)
        tail = tail[:at] + tail[at + 2:]
    return [*args, *tail]


_OUTER_TO = ("SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING", "SCG_VALIDATION",
             "SPEC_REGRESSION_CHECK")
_INNER_ONLY_TO = ("SPEC_AUDIT", "PR_REVIEW", "RELEASE")
_NEVER_TO = ("INIT", "SPEC_FROZEN", "IMPLEMENTATION", "ESCALATION", "ESCALATION_FINAL",
             "RELEASE_READY", "AUTO_RECOVERY_ATTEMPT", "TERMINATED", "NOPE", "", "spec_drafting",
             "SPEC_DRAFTING ")


def _matrix() -> list[tuple[str, str, str, list[str], bool]]:
    cells: list[tuple[str, str, str, list[str], bool]] = []

    def add(label: str, key: str, verb: str, args: list[str], ok: bool) -> None:
        cells.append((f"{'outer' if key == _OUTER_KEY else 'inner'}:{verb}:{label}",
                      key, verb, args, ok))

    both = (_OUTER_KEY, _INNER_KEY)
    for to in _OUTER_TO:
        for key in both:
            add(f"--to={to}", key, "transition", _tr(to), True)
    for to in _INNER_ONLY_TO:
        add(f"--to={to}", _OUTER_KEY, "transition", _tr(to), False)
        add(f"--to={to}", _INNER_KEY, "transition", _tr(to), True)
    for to in _NEVER_TO:
        for key in both:
            add(f"--to={to!r}", key, "transition", _tr(to), False)
    add("--to=HUMAN_PENDING baseline", _INNER_KEY, "transition",
        _tr("HUMAN_PENDING", "baseline adoption: SCG PASS"), True)
    for reason in ("adopt baseline", "Baseline adoption", " baseline adoption", "why"):
        add(f"--to=HUMAN_PENDING reason={reason!r}", _INNER_KEY, "transition",
            _tr("HUMAN_PENDING", reason), False)
    for reason in ("baseline adoption: SCG PASS", "why"):
        add(f"--to=HUMAN_PENDING reason={reason!r}", _OUTER_KEY, "transition",
            _tr("HUMAN_PENDING", reason), False)
    for key in both:
        add("trigger missing", key, "transition",
            ["--to", "SPEC_DRAFTING", "--reason", "why"], False)
        add("trigger=cli_manual", key, "transition", _tr("SPEC_DRAFTING", trigger="cli_manual"),
            False)
        add("trigger=empty", key, "transition", _tr("SPEC_DRAFTING", trigger=""), False)
        add("reason missing", key, "transition",
            ["--to", "SPEC_DRAFTING", "--trigger", "research_bridge"], False)
        add("reason empty", key, "transition", _tr("SPEC_DRAFTING", reason=""), False)
        add("reason blank", key, "transition", _tr("SPEC_DRAFTING", reason="   \t"), False)
        add("reason like a flag", key, "transition", _tr("SPEC_DRAFTING", reason="--to X"), True)
        add("to missing", key, "transition",
            ["--reason", "why", "--trigger", "research_bridge"], False)
        add("--to twice", key, "transition", [*_tr("SPEC_DRAFTING"), "--to", "AGENT_LOAD"], False)
        add("--gate is not a transition flag", key, "transition",
            [*_tr("SPEC_DRAFTING"), "--gate", "SCG_VALIDATION"], False)
        add("flag without value", key, "transition", [*_tr("SPEC_DRAFTING"), "--reason"], False)
        add("NUL in value", key, "transition", _tr("SPEC_DRAFTING", reason="a\x00b"), False)
    add("--gate=SCG_VALIDATION", _OUTER_KEY, "gate", _gt("SCG_VALIDATION"), True)
    add("--gate=SCG_VALIDATION", _INNER_KEY, "gate", _gt("SCG_VALIDATION"), False)
    for gate in ("PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"):
        add(f"--gate={gate}", _OUTER_KEY, "gate", _gt(gate), False)
        add(f"--gate={gate}", _INNER_KEY, "gate", _gt(gate), True)
    for gate in ("SPEC_REGRESSION_CHECK", "NOPE", "", "scg_validation"):
        for key in both:
            add(f"--gate={gate!r}", key, "gate", _gt(gate), False)
    for key, gate in ((_OUTER_KEY, "SCG_VALIDATION"), (_INNER_KEY, "PR_REVIEW")):
        for result in ("PASS", "FAIL"):
            add(f"--result={result}", key, "gate", _gt(gate, result), True)
        for result in ("pass", "fail", "ESCALATE", "", "PASS "):
            add(f"--result={result!r}", key, "gate", _gt(gate, result), False)
        add("reason missing", key, "gate", ["--gate", gate, "--result", "PASS"], False)
        add("reason blank", key, "gate", _gt(gate, reason="  "), False)
        add("result missing", key, "gate", ["--gate", gate, "--reason", "why"], False)
        add("gate missing", key, "gate", ["--result", "PASS", "--reason", "why"], False)
        add("--trigger is not a gate flag", key, "gate",
            [*_gt(gate), "--trigger", "research_bridge"], False)
        add("--result twice", key, "gate", [*_gt(gate), "--result", "FAIL"], False)
    for stage in ("Gate-0", "Gate-0-SCR1", "Gate-0-SCR12", "Stage-1"):
        add(f"--stage={stage}", _OUTER_KEY, "spec-frozen", _fz(stage), True)
    for stage in ("Gate-0-SCR", "Gate-0-SCRx", "Gate-0-SCR1a", "Gate-1", "Stage-2", "Stage-0",
                  "gate-0", "Gate-0 ", ""):
        add(f"--stage={stage!r}", _OUTER_KEY, "spec-frozen", _fz(stage), False)
    add("--stage=Stage-1", _INNER_KEY, "spec-frozen", _fz("Stage-1"), True)
    for stage in ("Gate-0", "Gate-0-SCR1", "Stage-2"):
        add(f"--stage={stage}", _INNER_KEY, "spec-frozen", _fz(stage), False)
    for key, stage in ((_OUTER_KEY, "Gate-0"), (_INNER_KEY, "Stage-1")):
        add("several --doc", key, "spec-frozen", _fz(stage, ("a.md", "b.md", "c.md")), True)
        add("no --doc", key, "spec-frozen", _fz(stage, ()), False)
        for flag in ("--digest", "--root", "--reason", "--approver", "--json"):
            add(f"{flag} missing", key, "spec-frozen", _fz(stage, drop=flag), False)
        add("--result is not a freeze flag", key, "spec-frozen",
            [*_fz(stage), "--result", "PASS"], False)
        add("--root blank", key, "spec-frozen", [
            "--stage", stage, "--doc", "a.md", "--digest", "--root", " ", "--reason", "x",
            "--approver", "alice", "--json"], False)
        add("--digest twice", key, "spec-frozen", [*_fz(stage), "--digest"], False)
        add("--root twice", key, "spec-frozen", [*_fz(stage), "--root", "/other"], False)
        add("one --doc", key, "spec-refreeze", _rf(), True)
        add("no --doc", key, "spec-refreeze", _rf(()), False)
        add("several --doc", key, "spec-refreeze", _rf(("a.md", "b.md")), True)
        for flag in ("--root", "--reason", "--approver"):
            add(f"{flag} missing", key, "spec-refreeze", _rf(drop=flag), False)
        add("--digest is not a refreeze flag", key, "spec-refreeze",
            [*_rf(), "--digest"], False)
        add("--stage is not a refreeze flag", key, "spec-refreeze",
            [*_rf(), "--stage", "Stage-1"], False)
    for key in both:
        add("no flags", key, "show", [], True)
        add("any flag", key, "show", ["--reason", "x"], False)
        add("--json", key, "show", ["--json"], False)
        for verb, args in (("transition", _tr("SPEC_DRAFTING")), ("gate", _gt(
                "SCG_VALIDATION" if key == _OUTER_KEY else "PR_REVIEW")),
                ("spec-frozen", _fz("Gate-0" if key == _OUTER_KEY else "Stage-1")),
                ("spec-refreeze", _rf()), ("show", [])):
            add("--project given", key, verb, ["--project", "other", *args], False)
            add("--must-exist given", key, verb, ["--must-exist", *args], False)
            add("unknown flag", key, verb, [*args, "--nope", "1"], False)
    return cells


_MATRIX = _matrix()


@pytest.mark.parametrize(("key", "verb", "args", "ok"), [c[1:] for c in _MATRIX],
                         ids=[c[0] for c in _MATRIX])
def test_AT_960_13_2_the_flag_and_value_matrix_cell(
        key: str, verb: str, args: list[str], ok: bool, fake: Path, state_dir: Path) -> None:
    if ok:
        sdd_cli.check_research_allowed(verb, args, key=key)
        return
    with pytest.raises(ApiError) as caught:
        sdd_cli.check_research_allowed(verb, args, key=key)
    assert (caught.value.status_code, caught.value.body["reason"]) == (500, "sdd_cli_usage")
    err = _research_error(fake, state_dir, verb, args, project=key)
    assert (err.status_code, err.body["reason"]) == (500, "sdd_cli_usage")
    assert read_calls(fake) == [], "越格組合在起子行程之前就被拒"


def test_AT_960_13_2_the_matrix_covers_both_key_classes_and_every_research_verb() -> None:
    assert sdd_cli.is_outer_key(_OUTER_KEY) and not sdd_cli.is_outer_key(_INNER_KEY)
    for key in (_OUTER_KEY, _INNER_KEY):
        for verb in sorted(sdd_cli.RESEARCH_VERBS):
            verdicts = {c[4] for c in _MATRIX if c[1] == key and c[2] == verb}
            assert verdicts == {True, False}, f"{key} × {verb} 須同時有放行格與越格"


def test_AT_960_13_2_the_research_builders_only_produce_accepted_invocations() -> None:
    sdd_cli.check_research_allowed("transition", sdd_cli.research_transition_args(
        to="SPEC_DRAFTING", reason="why"), key=_OUTER_KEY)
    sdd_cli.check_research_allowed("gate", sdd_cli.research_gate_args(
        gate="SCG_VALIDATION", result="FAIL", reason="why"), key=_OUTER_KEY)
    sdd_cli.check_research_allowed("gate", sdd_cli.research_gate_args(
        gate="RTM_VERIFY", result="PASS", reason="why"), key=_INNER_KEY)
    sdd_cli.check_research_allowed("spec-frozen", sdd_cli.research_freeze_args(
        stage="Gate-0", docs=["a.md", "b.md"], root="/r", reason="x", approver="alice@example.com"),
        key=_OUTER_KEY)
    sdd_cli.check_research_allowed("spec-refreeze", sdd_cli.research_refreeze_args(
        docs=["a.md"], root="/r", reason="x", approver="ops_01"), key=_OUTER_KEY)
    assert sdd_cli.research_transition_args(to="AGENT_LOAD", reason="r")[-2:] == [
        "--trigger", "research_bridge"]
