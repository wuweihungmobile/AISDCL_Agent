"""研究面 FSM 驅動（`app/research/fsm_ops.py`）。

TCS-ResearchToPRD-P0-20261102：AT-960-13-3（建檔唯一例外）、13-4（鏡像邊表與預檢）、
13-5（固定環境）、13-6（暫存狀態目錄實跑）、13-8（人工恢復後預算不歸零）、
13-E-2（`gate` 以回傳為準）、13-E-3（框架負控）。

兩種樹：`fake`＝tests/fake_sdd.py 的假 CLI（永遠跑）；`real`＝真的 SDD 樹（`SDD_ROOT` 環境
變數有設就用它、否則用 `load_settings` 找到的樹；樹不在＝
`pytest.skip("TOOL-ABSENCE: SDD_ROOT 不存在")`，SCG-4 要求兩者皆在場、0 skipped 重跑）。
同一組斷言對兩種樹各跑一次，就是假 CLI 與真 CLI 的行為對拍（D-60）。狀態目錄一律在 pytest
的暫存目錄（`<tmp>/ws/build/reports/fsm`），用畢由 pytest 清掉；真狀態目錄零接觸。
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app import procutil, sdd_cli
from app.errors import ApiError
from app.research import fsm_ops
from app.security import AuditLog
from app.settings import load_settings
from tests.fake_sdd import (
    make_fake_sdd,
    read_calls,
    read_state,
    seed_state,
    set_control,
    state_path,
)

APP_DIR = Path(sdd_cli.__file__).resolve().parent
OUTER = "research-agent-memory-gc"
INNER = "autoclaude-demo"
GATE = "SCG_VALIDATION"
SECRET = "t0ken-" + "x" * 40
#: 測試端自己的子行程（扮演「人在終端機」）用原版 Popen，不被下面的記錄器看到。
_REAL_POPEN = subprocess.Popen


# ── 夾具與小工具 ─────────────────────────────────────────────────────────────────────────
def real_sdd_root() -> Path:
    """真的 SDD 樹；不存在＝TOOL-ABSENCE 跳過（SCG-4 須 0 skipped）。"""
    env = os.environ.get("SDD_ROOT")
    root = load_settings({"SDD_ROOT": env} if env else {}).sdd_root
    if root is None or not (root / "tools" / "fsm_runtime" / "fsm_runtime.py").is_file():
        pytest.skip("TOOL-ABSENCE: SDD_ROOT 不存在")
    return root


@pytest.fixture
def fake(tmp_path: Path) -> Path:
    return make_fake_sdd(tmp_path / "sdd")


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    """研究工作區根；其下 `build/reports/fsm` 是外環鍵的狀態目錄（Plan 附錄 A 的目錄形態）。"""
    return tmp_path / "ws"


@pytest.fixture
def state_dir(ws: Path) -> Path:
    return ws / "build" / "reports" / "fsm"


@pytest.fixture(params=["fake", "real"])
def tree(request: pytest.FixtureRequest, fake: Path) -> Path:
    return fake if request.param == "fake" else real_sdd_root()


@pytest.fixture
def popen_log(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """記錄 Bridge 起的每個子行程（argv、kwargs、`communicate` 的逾時）；子行程照常執行。"""
    log: list[dict[str, Any]] = []

    class Recording(_REAL_POPEN):  # type: ignore[misc, valid-type]
        def __init__(self, args: Any, **kwargs: Any) -> None:
            self._entry: dict[str, Any] = {"args": list(args), "kwargs": dict(kwargs),
                                           "timeout": None}
            log.append(self._entry)
            super().__init__(args, **kwargs)

        def communicate(self, input: Any = None, timeout: float | None = None) -> Any:  # noqa: A002
            self._entry["timeout"] = timeout
            return super().communicate(input, timeout=timeout)

    monkeypatch.setattr(subprocess, "Popen", Recording)
    return log


def make_ctx(tree: Path, state_dir: Path, key: str = OUTER, **kw: Any) -> fsm_ops.FsmCtx:
    return fsm_ops.FsmCtx(sdd_root=tree, state_dir=state_dir, key=key, **kw)


def verbs_of(log: list[dict[str, Any]]) -> list[str]:
    return [e["args"][e["args"].index(sdd_cli.CLI_MODULE) + 1] for e in log]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(state: dict[str, Any], gate: str = GATE) -> tuple[int, int]:
    entry = state["retry_history"][gate]
    return entry["current_count"], len(entry["history"])


def to_review(ctx: fsm_ops.FsmCtx, ws: Path) -> None:
    """Plan 附錄 A 的前半：show 建檔、四個 transition 到 SCG_VALIDATION。"""
    assert fsm_ops.create_key(ctx, allowed_roots=[ws]) == "INIT"
    assert fsm_ops.bring_to_agent_load(ctx) == "AGENT_LOAD"
    assert fsm_ops.transition(ctx, to="SPEC_DRAFTING", reason="start drafting") == "SPEC_DRAFTING"
    assert fsm_ops.transition(ctx, to=GATE, reason="ready for review") == GATE


def fail_to_escalation(ctx: fsm_ops.FsmCtx) -> list[dict[str, Any]]:
    """Plan 附錄 A 的後半：gate FAIL×3（前兩次之後回 SCG_VALIDATION 再審）。"""
    results = []
    for n in (1, 2, 3):
        results.append(fsm_ops.gate(ctx, gate=GATE, result="FAIL", reason=f"round {n} failed"))
        if n < 3:
            fsm_ops.transition(ctx, to=GATE, reason="revised, review again")
    return results


def human_resume(tree: Path, state_dir: Path, key: str) -> dict[str, Any]:
    """扮演「人在終端機」執行 `resume-from-escalation`（Bridge 的白名單沒有這個動詞）。"""
    env = sdd_cli.build_cli_env(os.environ, sdd_root=tree, state_dir=state_dir, project=key)
    argv = [sys.executable, "-W", "ignore::RuntimeWarning", "-m", sdd_cli.CLI_MODULE,
            "resume-from-escalation", "--project", key, "--must-exist", "--to", "SPEC_DRAFTING",
            "--reason", "人工恢復：規格已修正"]
    proc = _REAL_POPEN(argv, cwd=str(tree), env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(timeout=60)
    assert proc.returncode == 0, err.decode("utf-8", errors="replace")
    return json.loads(out.decode("utf-8").strip().splitlines()[-1])


# ══ AT-960-13-3：show 建檔唯一例外 ════════════════════════════════════════════════════════
KEYS_OK = {
    "plain": "research-agent-memory-gc",
    "generation": "research-agent-memory-gc-g2",
    "slug30": "research-" + "a" * 30,
    "slug30+g2": "research-" + "a" * 30 + "-g2",
}
KEYS_BAD = {
    "uppercase": "research-A",
    "empty slug": "research-",
    "slug31": "research-" + "a" * 31,
    "slug31+g2": "research-" + "a" * 31 + "-g2",
    "other prefix": "other-x",
    "dot": "research-a.b",
    "space": "research-a b",
    "underscore": "research-a_b",
    "leading dash": "research--a",
}


@pytest.mark.parametrize("key", list(KEYS_OK.values()), ids=list(KEYS_OK))
def test_AT_960_13_3_a_valid_key_is_created_as_init_and_only_that_call_lacks_must_exist(
        key: str, tree: Path, ws: Path, state_dir: Path, popen_log: list[dict[str, Any]]) -> None:
    ctx = make_ctx(tree, state_dir, key)
    assert fsm_ops.create_key(ctx, allowed_roots=[ws]) == "INIT"
    assert read_state(state_dir, key)["current_state"] == "INIT"
    assert fsm_ops.show(ctx)["current_state"] == "INIT"
    assert fsm_ops.transition(ctx, to="SCENARIO_DETECT", reason="init") == "SCENARIO_DETECT"
    assert verbs_of(popen_log) == ["show", "show", "transition"]
    creation, *rest = (e["args"] for e in popen_log)
    assert "--must-exist" not in creation, "建檔那一次是唯一不帶 --must-exist 的呼叫"
    assert all("--must-exist" in argv for argv in rest), "其餘呼叫逐一帶 --must-exist"


@pytest.mark.parametrize("key", list(KEYS_BAD.values()), ids=list(KEYS_BAD))
def test_AT_960_13_3_a_malformed_key_is_refused_before_any_process_or_directory(
        key: str, fake: Path, ws: Path, state_dir: Path, popen_log: list[dict[str, Any]]) -> None:
    with pytest.raises(ApiError) as caught:
        fsm_ops.create_key(make_ctx(fake, state_dir, key), allowed_roots=[ws])
    err = caught.value
    assert (err.status_code, err.body["reason"]) == (422, "sanitization_failed"), key
    assert err.body["violations"][0]["field"] == "fsm_project"
    assert popen_log == [] and read_calls(fake) == []
    assert not state_dir.exists(), "被拒的鍵不得留下任何目錄"


def test_AT_960_13_3_an_existing_state_file_is_never_recreated(
        tree: Path, ws: Path, state_dir: Path, popen_log: list[dict[str, Any]]) -> None:
    ctx = make_ctx(tree, state_dir)
    fsm_ops.create_key(ctx, allowed_roots=[ws])
    path = state_path(state_dir, OUTER)
    before = sha256_of(path)
    with pytest.raises(ApiError) as caught:
        fsm_ops.create_key(ctx, allowed_roots=[ws])
    err = caught.value
    assert (err.status_code, err.body["reason"]) == (409, "fsm_state_conflict")
    assert err.body["details"] == {"current_state": "INIT", "cause": "key_exists"}
    assert sha256_of(path) == before, "已存在的檔案位元組不變"
    assert verbs_of(popen_log) == ["show"], "第二次沒有起子行程"
    fsm_ops.bring_to_agent_load(ctx)
    with pytest.raises(ApiError) as caught:
        fsm_ops.create_key(ctx, allowed_roots=[ws])
    assert caught.value.body["details"]["current_state"] == "AGENT_LOAD"


def test_AT_960_13_3_a_state_directory_outside_the_roots_or_of_the_wrong_shape_is_refused(
        tmp_path: Path, fake: Path, ws: Path, popen_log: list[dict[str, Any]]) -> None:
    cases = {
        "outside the allowed roots": tmp_path / "elsewhere" / "build" / "reports" / "fsm",
        "dotdot out of the root": ws / ".." / "elsewhere" / "build" / "reports" / "fsm",
        "suffix fsm only": ws / "fsm",
        "suffix build/fsm": ws / "build" / "fsm",
        "suffix with an extra part": ws / "build" / "reports" / "fsm" / "x",
        "relative": Path("build") / "reports" / "fsm",
    }
    for label, bad_dir in cases.items():
        with pytest.raises(ApiError) as caught:
            fsm_ops.create_key(make_ctx(fake, bad_dir), allowed_roots=[ws])
        err = caught.value
        assert (err.status_code, err.body["reason"]) == (422, "sanitization_failed"), label
        assert err.body["violations"][0]["field"] == "state_dir", label
    assert popen_log == [] and not (tmp_path / "elsewhere").exists() and not ws.exists()


def test_AT_960_13_3_only_the_creation_helper_builds_a_show_without_must_exist() -> None:
    assert sdd_cli.build_research_argv("show", [], OUTER)[-1] == "--must-exist"
    created = sdd_cli.build_research_argv("show", [], OUTER, create=True)
    assert "--must-exist" not in created and created[-3:] == ["show", "--project", OUTER]
    for verb in ("transition", "gate", "spec-frozen", "spec-refreeze"):
        assert "--must-exist" in sdd_cli.build_research_argv(verb, [], OUTER)


def test_AT_960_13_3_creation_is_only_for_show_on_an_outer_key(fake: Path, state_dir: Path) -> None:
    for verb, args, key in (("transition", ["--to", "AGENT_LOAD", "--reason", "r", "--trigger",
                                             "research_bridge"], OUTER), ("show", [], INNER)):
        with pytest.raises(ApiError) as caught:
            sdd_cli.run_research_verb(verb, args, sdd_root=fake, state_dir=state_dir, project=key,
                                      create=True)
        assert (caught.value.status_code, caught.value.body["reason"]) == (500, "sdd_cli_usage")
    assert read_calls(fake) == []


# ══ AT-960-13-4：鏡像邊表與預檢、事後讀驗 ═══════════════════════════════════════════════════
@cache
def transition_rules(sdd_root: str) -> ModuleType:
    """以路徑載入真 SDD 樹的 `transition_rules.py`（只依 typing）。"""
    path = Path(sdd_root) / "tools" / "fsm_runtime" / "transition_rules.py"
    spec = importlib.util.spec_from_file_location("sdd_transition_rules_probe", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_AT_960_13_4_every_mirror_edge_is_a_happy_path_edge() -> None:
    rules = transition_rules(str(real_sdd_root()))
    happy = rules._HAPPY_PATH
    edges = {(src, dst) for src, dsts in fsm_ops.MIRROR_EDGES.items() for dst in dsts}
    assert len(edges) >= 10
    missing = sorted(e for e in edges if e[1] not in happy.get(e[0], set()))
    assert missing == [], f"鏡像邊表有框架 _HAPPY_PATH 不認的邊：{missing}"
    assert fsm_ops.edge_allowed("AGENT_LOAD", "SPEC_DRAFTING")
    assert not fsm_ops.edge_allowed("AGENT_LOAD", "SPEC_FROZEN")


def test_AT_960_13_4_the_value_domain_is_covered_by_the_mirror_and_the_pass_table() -> None:
    reachable = {dst for dsts in fsm_ops.MIRROR_EDGES.values() for dst in dsts}
    domain = set(sdd_cli.INNER_TRANSITION_TARGETS) | {sdd_cli.BASELINE_ADOPTION_TARGET}
    assert domain <= reachable, f"--to 的值域有鏡像邊表到不了的目標：{domain - reachable}"
    # `gate PASS` 之後的下一態：與框架的 next_state_on_gate_pass 逐閘一致
    rules = transition_rules(str(real_sdd_root()))
    gates = sdd_cli.OUTER_GATES | sdd_cli.INNER_GATES
    assert gates == set(fsm_ops._PASS_NEXT)
    for gate in gates:
        assert fsm_ops._PASS_NEXT[gate] == rules.next_state_on_gate_pass(gate), gate
    for src, dst in zip(("INIT", "SCENARIO_DETECT"), fsm_ops.INIT_PATH, strict=True):
        assert fsm_ops.edge_allowed(src, dst)


def test_AT_960_13_4_an_edge_the_mirror_lacks_is_refused_before_any_process_starts(
        fake: Path, ws: Path, state_dir: Path) -> None:
    ctx = make_ctx(fake, state_dir)
    fsm_ops.create_key(ctx, allowed_roots=[ws])
    fsm_ops.bring_to_agent_load(ctx)
    before = len(read_calls(fake))
    with pytest.raises(ApiError) as caught:
        fsm_ops.transition(ctx, to=GATE, reason="skip the drafting")
    err = caught.value
    assert (err.status_code, err.body["reason"]) == (409, "fsm_state_conflict")
    assert err.body["details"] == {"current_state": "AGENT_LOAD", "target": GATE,
                                   "cause": "transition_not_allowed"}
    with pytest.raises(ApiError) as caught:       # 值域外（如 AGENT_LOAD→SPEC_FROZEN）
        fsm_ops.transition(ctx, to="SPEC_FROZEN", reason="freeze it")
    assert (caught.value.status_code, caught.value.body["reason"]) == (500, "sdd_cli_usage")
    assert len(read_calls(fake)) == before, "非法轉態在起子行程之前就被拒"
    assert read_state(state_dir, OUTER)["current_state"] == "AGENT_LOAD"


def test_AT_960_13_4_the_baseline_adoption_edge_exists_only_from_scg_validation(
        fake: Path, state_dir: Path) -> None:
    """內環鍵的 `--to HUMAN_PENDING` 限現態 SCG_VALIDATION（reason 的起頭另由旗標矩陣把關）。"""
    reason = "baseline adoption: SCG PASS on the research PRD"
    seed_state(state_dir, INNER, "SPEC_DRAFTING")
    with pytest.raises(ApiError) as caught:
        fsm_ops.transition(make_ctx(fake, state_dir, INNER), to="HUMAN_PENDING", reason=reason)
    assert (caught.value.status_code, caught.value.body["reason"]) == (409, "fsm_state_conflict")
    assert read_calls(fake) == []
    seed_state(state_dir, INNER, GATE)
    assert fsm_ops.transition(make_ctx(fake, state_dir, INNER), to="HUMAN_PENDING",
                              reason=reason) == "HUMAN_PENDING"


@pytest.mark.parametrize(("claimed", "case"), [
    ("OK transitioned to AGENT_LOAD", "the cli claims success but the state file did not move"),
    ("OK transitioned to SPEC_DRAFTING", "the cli reports another state than the one requested"),
    ("done", "the output is not the expected sentence"),
    ("", "the output is empty"),
])
def test_AT_960_13_4_a_response_that_disagrees_with_the_target_is_502_not_silent_success(
        claimed: str, case: str, fake: Path, ws: Path, state_dir: Path, tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    ctx = make_ctx(fake, state_dir, audit=audit, actor="alice@example.com")
    fsm_ops.create_key(ctx, allowed_roots=[ws])
    fsm_ops.transition(ctx, to="SCENARIO_DETECT", reason="init")
    path = state_path(state_dir, OUTER)
    before = sha256_of(path)
    set_control(fake, raw_stdout={"transition": claimed})
    with pytest.raises(ApiError) as caught:
        fsm_ops.transition(ctx, to="AGENT_LOAD", reason="next")
    err = caught.value
    assert (err.status_code, err.body["reason"]) == (502, "sdd_cli_failed"), case
    assert sha256_of(path) == before and read_state(state_dir, OUTER)["current_state"] == (
        "SCENARIO_DETECT"), "沒有任何東西被當成已轉態"
    entries = [json.loads(x) for x in (tmp_path / "audit.jsonl").read_text("utf-8").splitlines()]
    assert entries[-1]["event"] == "sdd_cli" and entries[-1]["verb"] == "transition"
    assert str(entries[-1]["result"]).startswith(("rejected:", "bad_output")), case


# ══ AT-960-13-5：固定環境、argv、逾時、互斥鎖 ═══════════════════════════════════════════════
def test_AT_960_13_5_the_child_environment_is_fixed_and_only_the_outer_key_disables_recovery(
        fake: Path, ws: Path, state_dir: Path, popen_log: list[dict[str, Any]],
        monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = {"BRIDGE_DB_DSN": f"postgresql://u:{SECRET}@db/x", "BRIDGE_X": "1",
                "BRIDGE_RESEARCH_WRITE_TOKEN": SECRET, "SDD_ROOT": "/not/this",
                "SDD_ENABLE_AUTO_RECOVERY": "1", "SDD_STATE_DIR": "/elsewhere",
                "SDD_PROJECT": "someone-else", "PYTHONPATH": "/evil/path"}
    for name, value in sentinel.items():
        monkeypatch.setenv(name, value)
    outer, inner = make_ctx(fake, state_dir, OUTER), make_ctx(fake, state_dir, INNER)
    to_review(outer, ws)
    fsm_ops.gate(outer, gate=GATE, result="FAIL", reason="not good enough")
    seed_state(state_dir, INNER, "IMPLEMENTATION")
    fsm_ops.transition(inner, to="PR_REVIEW", reason="review the implementation")
    fsm_ops.gate(inner, gate="PR_REVIEW", result="PASS", reason="all green")
    assert popen_log and {"transition", "gate"} <= set(verbs_of(popen_log))
    calls = read_calls(fake)
    assert len(calls) == len(popen_log)
    for entry, call in zip(popen_log, calls, strict=True):
        argv, kwargs, key = entry["args"], entry["kwargs"], call["argv"][2]
        env = kwargs["env"]
        upper = {k.upper(): v for k, v in env.items()}
        assert isinstance(argv, list) and not kwargs.get("shell"), "argv 為列表、不經 shell"
        assert os.path.normcase(kwargs["cwd"]) == os.path.normcase(str(fake)), "cwd＝SDD 版本目錄"
        assert entry["timeout"] == 20.0 == sdd_cli.DEFAULT_TIMEOUT_SECONDS
        expected_platform = procutil.popen_platform_kwargs()
        assert {k: kwargs.get(k) for k in expected_platform} == expected_platform, \
            "平台旗標來自 procutil.popen_platform_kwargs()"
        assert not [k for k in upper if k.startswith("BRIDGE_")], "BRIDGE_* 一個都不能洩進去"
        assert upper["PYTHONPATH"] == str(fake) and Path(upper["SDD_STATE_DIR"]).is_absolute()
        assert upper["SDD_STATE_DIR"] == str(state_dir) and upper["SDD_PROJECT"] == key
        fixed = {"SDD_STATE_DIR", "SDD_PROJECT", "SDD_ENABLE_RULE_FIRE_TELEMETRY",
                 "SDD_ENABLE_RULE_CATCH_TELEMETRY"}
        if key == OUTER:
            assert upper["SDD_ENABLE_AUTO_RECOVERY"] == "0", "外環鍵固定關閉自動恢復"
            fixed |= {"SDD_ENABLE_AUTO_RECOVERY"}
        assert {k for k in upper if k.startswith("SDD_")} == fixed, (key, sorted(upper))
        assert SECRET not in json.dumps(call), "權杖與 DB 密碼不得出現在子行程的任何環境值"
    assert {c["argv"][2] for c in calls} == {OUTER, INNER}


def test_AT_960_13_5_calls_for_the_same_state_dir_and_key_are_serialised_by_the_guard(
        fake: Path, ws: Path, state_dir: Path, popen_log: list[dict[str, Any]]) -> None:
    ctx = make_ctx(fake, state_dir)
    fsm_ops.create_key(ctx, allowed_roots=[ws])
    popen_log.clear()
    done: list[str] = []

    def worker() -> None:
        done.append(fsm_ops.current_state(ctx))
        done.append(fsm_ops.transition(ctx, to="SCENARIO_DETECT", reason="init"))

    with sdd_cli.state_guard(state_dir, OUTER):
        thread = threading.Thread(target=worker)
        thread.start()
        time.sleep(0.5)
        assert done == [] and popen_log == [], "別的執行緒持鎖時，這把鍵的讀寫都得等"
    thread.join(20)
    assert done == ["INIT", "SCENARIO_DETECT"] and verbs_of(popen_log) == ["transition"]


# ══ AT-960-13-6：暫存狀態目錄實跑（三次 FAIL → ESCALATION；PASS 歸零 → HUMAN_PENDING）═════════
def test_AT_960_13_6_three_fails_end_in_escalation_never_in_auto_recovery(
        tree: Path, ws: Path, state_dir: Path, popen_log: list[dict[str, Any]]) -> None:
    ctx = make_ctx(tree, state_dir)
    to_review(ctx, ws)
    first, second, third = fail_to_escalation(ctx)
    assert (first["next_state"], first["retry_count"]) == ("SPEC_DRAFTING", 1)
    assert (second["next_state"], second["retry_count"]) == ("SPEC_DRAFTING", 2)
    assert third["escalated"] is True and third["retry_count"] == 3
    shown = fsm_ops.show(ctx)
    assert shown["current_state"] == "ESCALATION"
    assert shown["current_state"] not in {"AUTO_RECOVERY_ATTEMPT", "ESCALATION_FINAL"}
    assert counts(shown) == (3, 3)
    assert shown["escalation_history"][-1]["resolved_at"] is None, "恢復只有人能做：沒人恢復過"
    assert fsm_ops.snapshot(ctx)["state"] == "ESCALATION"
    assert "resume-from-escalation" not in verbs_of(popen_log), "Bridge 從不呼叫恢復動詞"
    assert all("tools.fsm_runtime" in " ".join(e["args"]) for e in popen_log), "只起 CLI 子行程"


def test_AT_960_13_6_a_pass_resets_the_count_and_moves_to_human_pending(
        tree: Path, ws: Path, state_dir: Path) -> None:
    ctx = make_ctx(tree, state_dir)
    to_review(ctx, ws)
    fsm_ops.gate(ctx, gate=GATE, result="FAIL", reason="first review failed")
    fsm_ops.transition(ctx, to=GATE, reason="revised")
    passed = fsm_ops.gate(ctx, gate=GATE, result="PASS", reason="second review passed")
    assert passed["next_state"] == "HUMAN_PENDING" and not passed.get("escalated")
    shown = fsm_ops.show(ctx)
    assert shown["current_state"] == "HUMAN_PENDING"
    assert shown["retry_history"][GATE]["current_count"] == 0, "通過即歸零（歷史列保留）"
    assert len(shown["retry_history"][GATE]["history"]) == 1


def test_AT_960_13_6_reads_never_touch_the_state_file(
        tree: Path, ws: Path, state_dir: Path) -> None:
    ctx = make_ctx(tree, state_dir)
    to_review(ctx, ws)
    path = state_path(state_dir, OUTER)
    before = (sha256_of(path), path.stat().st_mtime_ns)
    fsm_ops.current_state(ctx)
    fsm_ops.read_current(ctx)
    fsm_ops.snapshot(ctx)
    assert (sha256_of(path), path.stat().st_mtime_ns) == before, "唯讀路徑不寫狀態檔"


# ══ INT-14 ④：容器內的恢復指令另附主機 PowerShell 形式 ═════════════════════════════════════════
@pytest.mark.parametrize("container, hostname, expected", [
    (True, "9f8e7d6c5b4a", "docker exec -it 9f8e7d6c5b4a sh"),        # Docker 預設主機名＝容器 ID
    (True, "aisdlc-engine-bridge", "docker exec -it aisdlc-engine-bridge sh"),
    (False, "9f8e7d6c5b4a", None),                              # 主機上的 Bridge：路徑本來就可讀
    (True, None, None), (True, "", None),
    (True, "a b", None), (True, "x;rm -rf /", None), (True, "$(id)", None),      # 不是合法識別字
])
def test_INT_14_the_host_form_enters_the_container_and_is_never_guessed(
        container: bool, hostname: str | None, expected: str | None) -> None:
    assert fsm_ops.host_enter_command(container=container, hostname=hostname) == expected


def test_INT_14_an_escalated_409_in_a_container_carries_the_host_powershell_form(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ctx = fsm_ops.FsmCtx(sdd_root=Path("/sdd/AISDLC_SDD_v0.30"),
                         state_dir=tmp_path / "build" / "reports" / "fsm", key="research-demo")
    state = {"current_state": "ESCALATION"}
    monkeypatch.setenv("HOSTNAME", "9f8e7d6c5b4a")
    monkeypatch.setattr(fsm_ops, "in_container", lambda: False)
    host = fsm_ops.escalated_error(ctx, state).body["details"]["recovery"]
    assert set(host) == {"target", "powershell", "posix"}, "主機上的 Bridge：形狀與此前逐鍵相同"
    monkeypatch.setattr(fsm_ops, "in_container", lambda: True)
    boxed = fsm_ops.escalated_error(ctx, state).body["details"]["recovery"]
    assert set(boxed) == {"target", "powershell", "posix", "host_powershell"}
    assert boxed["host_powershell"] == "docker exec -it 9f8e7d6c5b4a sh"
    assert {k: boxed[k] for k in host} == host, "容器內路徑照給（容器裡的真實路徑），只是另附一個鍵"
    assert "sh" == boxed["host_powershell"].rsplit(" ", 1)[1] and "resume-from-escalation" in (
        boxed["posix"]), "進容器後貼 posix 那一行"


# ══ AT-960-13-8：人工恢復後預算不歸零 ═══════════════════════════════════════════════════════
@pytest.mark.parametrize("after", ["fail", "pass"])
def test_AT_960_13_8_after_a_human_resume_the_budget_is_not_reset(
        after: str, tree: Path, ws: Path, state_dir: Path,
        popen_log: list[dict[str, Any]]) -> None:
    key = f"research-resume-{after}"
    ctx = make_ctx(tree, state_dir, key)
    to_review(ctx, ws)
    fail_to_escalation(ctx)
    escalated = fsm_ops.show(ctx)
    assert escalated["current_state"] == "ESCALATION" and counts(escalated) == (3, 3)
    resumed = human_resume(tree, state_dir, key)
    assert (resumed["from"], resumed["to"]) == ("ESCALATION", "SPEC_DRAFTING")
    after_resume = fsm_ops.show(ctx)
    assert after_resume["current_state"] == "SPEC_DRAFTING"
    assert counts(after_resume) == (3, 3), "resume-from-escalation 不動計數也不動歷史"
    assert fsm_ops.transition(ctx, to=GATE, reason="revised after the human resume") == GATE
    if after == "fail":
        result = fsm_ops.gate(ctx, gate=GATE, result="FAIL", reason="still not good")
        assert result["escalated"] is True and result["retry_count"] == 3, "夾在上限、不是 4"
        final = fsm_ops.show(ctx)
        assert final["current_state"] == "ESCALATION"
        assert final["current_state"] != "AUTO_RECOVERY_ATTEMPT"
        history = final["retry_history"][GATE]["history"]
        assert len(history) == 4 and "tamper detected" in history[3]["failure_reason"], \
            "引擎既有行為（已知邊界、不當作竄改缺陷；D-60）"
    else:
        result = fsm_ops.gate(ctx, gate=GATE, result="PASS", reason="the revision passed")
        assert result["next_state"] == "HUMAN_PENDING"
        final = fsm_ops.show(ctx)
        assert final["current_state"] == "HUMAN_PENDING"
        assert final["retry_history"][GATE]["current_count"] == 0
    assert "resume-from-escalation" not in verbs_of(popen_log), "只有測試端跑過那個動詞"


# ══ AT-960-13-E-2：gate 以回傳為準 ═════════════════════════════════════════════════════════
def _gate_json(**over: Any) -> str:
    body = {"gate": GATE, "result": "FAIL", "retry_count": 1, "next_state": "SPEC_DRAFTING"}
    body.update(over)
    return json.dumps({k: v for k, v in body.items() if v is not None})


_BAD_GATE_OUTPUTS = {
    "not json": ("FAIL", "gate done"),
    "a json list": ("FAIL", "[1, 2]"),
    "empty output": ("FAIL", ""),
    "next_state missing": ("FAIL", _gate_json(next_state=None)),
    "retry_count missing on a FAIL": ("FAIL", _gate_json(retry_count=None)),
    "retry_count is a string": ("FAIL", _gate_json(retry_count="1")),
    "retry_count is zero": ("FAIL", _gate_json(retry_count=0)),
    "retry_count is a bool": ("FAIL", _gate_json(retry_count=True)),
    "echoes another gate": ("FAIL", _gate_json(gate="PR_REVIEW")),
    "echoes another result": ("FAIL", _gate_json(result="PASS")),
    "escalated but next_state is not": ("FAIL", _gate_json(escalated=True)),
    "next_state ESCALATION but not escalated": ("FAIL", _gate_json(next_state="ESCALATION")),
    "a PASS that ends in IMPLEMENTATION": (
        "PASS", _gate_json(result="PASS", retry_count=None, next_state="IMPLEMENTATION")),
    "a PASS that claims escalated": (
        "PASS", _gate_json(result="PASS", retry_count=None, next_state="HUMAN_PENDING",
                           escalated=True)),
    "valid shape but the state file did not move": ("FAIL", _gate_json()),
}


@pytest.mark.parametrize(("result", "output"), list(_BAD_GATE_OUTPUTS.values()),
                         ids=list(_BAD_GATE_OUTPUTS))
def test_AT_960_13_E_2_a_malformed_or_contradictory_gate_output_is_502_and_changes_nothing(
        result: str, output: str, fake: Path, ws: Path, state_dir: Path, tmp_path: Path) -> None:
    audit = AuditLog(tmp_path / "audit.jsonl")
    ctx = make_ctx(fake, state_dir, audit=audit)
    to_review(ctx, ws)
    path = state_path(state_dir, OUTER)
    before = sha256_of(path)
    set_control(fake, raw_stdout={"gate": output})
    with pytest.raises(ApiError) as caught:
        fsm_ops.gate(ctx, gate=GATE, result=result, reason="a verdict from the evaluator")
    assert (caught.value.status_code, caught.value.body["reason"]) == (502, "sdd_cli_failed")
    assert sha256_of(path) == before, "不改任何游標、不標 PASS"
    last = json.loads((tmp_path / "audit.jsonl").read_text("utf-8").splitlines()[-1])
    assert (last["event"], last["verb"]) == ("sdd_cli", "gate")
    assert str(last["result"]).startswith(("rejected:", "bad_output")), "拒絕有稽核記錄"


def test_AT_960_13_E_2_a_well_formed_output_is_adopted_as_is(
        fake: Path, ws: Path, state_dir: Path) -> None:
    ctx = make_ctx(fake, state_dir)
    to_review(ctx, ws)
    fail = fsm_ops.gate(ctx, gate=GATE, result="FAIL", reason="needs work")
    assert fail == {"gate": GATE, "result": "FAIL", "retry_count": 1, "next_state": "SPEC_DRAFTING"}
    assert read_state(state_dir, OUTER)["current_state"] == fail["next_state"]
    fsm_ops.transition(ctx, to=GATE, reason="revised")
    ok = fsm_ops.gate(ctx, gate=GATE, result="PASS", reason="fine now")
    assert ok == {"gate": GATE, "result": "PASS", "next_state": "HUMAN_PENDING"}


def _fail_body(**over: Any) -> dict[str, Any]:
    return {"gate": GATE, "result": "FAIL", "retry_count": 1, "next_state": "SPEC_DRAFTING", **over}


@pytest.mark.parametrize(("gate", "result", "payload", "problem"), [
    (GATE, "FAIL", _fail_body(retry_count=2), False),
    (GATE, "fail", _fail_body(retry_count=3, next_state="ESCALATION", escalated=True), False),
    (GATE, "FAIL", _fail_body(next_state="HUMAN_PENDING"), False),
    ("RTM_VERIFY", "PASS", {"gate": "RTM_VERIFY", "result": "PASS",
                            "next_state": "RELEASE_READY"}, False),
    (GATE, "PASS", {"gate": GATE, "result": "PASS", "next_state": "RELEASE_READY"}, True),
    (GATE, "FAIL", _fail_body(next_state=7), True),
    (GATE, "FAIL", _fail_body(escalated="yes"), True),
    (GATE, "FAIL", ["not", "an", "object"], True),
], ids=["fail-1", "fail-escalated", "fail-in-human-pending", "other-gate-pass", "pass-wrong-next",
        "next-state-not-a-string", "escalated-not-a-bool", "not-an-object"])
def test_AT_960_13_E_2_the_payload_check_is_a_pure_function_of_request_and_output(
        gate: str, result: str, payload: Any, problem: bool) -> None:
    assert (fsm_ops.gate_payload_problem(gate, result, payload) is not None) is problem


def retry_increment_sites(source: str) -> list[int]:
    """AST 判準：名稱含 retry 的目標被自增（`x += …`、`x = x + …`）的行號。"""
    hits: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.AugAssign) and "retry" in ast.dump(node.target).lower():
            hits.append(node.lineno)
        elif (isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp)
              and isinstance(node.value.op, ast.Add)
              and any("retry" in ast.dump(t).lower() for t in node.targets)):
            hits.append(node.lineno)
    return hits


def test_AT_960_13_E_2_the_bridge_keeps_no_retry_counter_of_its_own() -> None:
    assert retry_increment_sites("retry_count += 1") == [1]
    assert retry_increment_sites("state['retry_history'][g] = state['retry_history'][g] + 1") == [1]
    assert retry_increment_sites("n = 0\nn += 1\nretry_count = payload['retry_count']") == []
    scanned = sorted(APP_DIR.joinpath("research").rglob("*.py"))
    scanned += [p for p in (APP_DIR / "routers" / "research.py",) if p.is_file()]
    assert scanned, "鎖要有標的"
    offenders = {p.relative_to(APP_DIR).as_posix(): retry_increment_sites(p.read_text("utf-8"))
                 for p in scanned}
    assert {rel: hits for rel, hits in offenders.items() if hits} == {}, \
        "retry 計數只讀 CLI 的回傳（next_state／retry_count／escalated），Bridge 不自增"


# ══ AT-960-13-E-3：框架負控（HUMAN_PENDING 下的 gate）═══════════════════════════════════════
def test_AT_960_13_E_3_a_pass_in_human_pending_fails_and_fails_only_move_the_count(
        tree: Path, ws: Path, state_dir: Path, popen_log: list[dict[str, Any]]) -> None:
    ctx = make_ctx(tree, state_dir)
    to_review(ctx, ws)
    fsm_ops.gate(ctx, gate=GATE, result="PASS", reason="the review passed")
    assert fsm_ops.current_state(ctx) == "HUMAN_PENDING"
    path = state_path(state_dir, OUTER)
    sent = len(popen_log)
    before = sha256_of(path)
    with pytest.raises(ApiError) as caught:                         # （一）框架以非 0 結束
        fsm_ops.gate(ctx, gate=GATE, result="PASS", reason="again")
    assert (caught.value.status_code, caught.value.body["reason"]) == (502, "sdd_cli_failed")
    assert sha256_of(path) == before, "狀態檔位元組與呼叫前相同"
    for expected in (1, 2):                              # （二）FAIL：計數加一、現態不動
        blocked = fsm_ops.gate(ctx, gate=GATE, result="FAIL", reason="人工審查：需補充證據")
        assert (blocked["next_state"], blocked["retry_count"]) == ("HUMAN_PENDING", expected)
        assert fsm_ops.current_state(ctx) == "HUMAN_PENDING"
        assert fsm_ops.show(ctx)["decision_trace"][-1]["trigger"] == "gate_fail_blocked"
    last = fsm_ops.gate(ctx, gate=GATE, result="FAIL", reason="人工審查：仍需補充")   # （三）
    assert last["escalated"] is True and last["next_state"] == "ESCALATION"
    final = fsm_ops.show(ctx)
    assert final["current_state"] == "ESCALATION"
    assert final["current_state"] != "AUTO_RECOVERY_ATTEMPT"
    calls = [e["args"] for e in popen_log[sent:] if "transition" in verbs_of([e])]
    assert calls == [], "全程沒有任何 transition 呼叫（尤其不是 --to SPEC_DRAFTING）"
