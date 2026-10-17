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
