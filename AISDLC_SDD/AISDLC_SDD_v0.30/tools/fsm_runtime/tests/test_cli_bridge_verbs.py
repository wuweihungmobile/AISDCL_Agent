# enforces (governance rules): R-9.20, R-9.5, R-9.6
"""ADR-XPLAT-016 §4「SDD CLI 新動詞」的守護測試：以**真 CLI 子行程**＋真 `FSMRuntime`＋暫存狀態目錄
（`SDD_STATE_DIR`）逐項驗 rc 表、單行 JSON、`--must-exist`、摘要鍵與 CRLF 正規化；舊動詞輸出逐字不變。

為什麼要測「子行程」而不是直接呼叫函式：Bridge 靠 stdout 的**最後一個非空行**解析 JSON、靠 rc 分流錯誤
（0 成功／1 非預期例外／2 用法錯誤／3 前置狀態不符／4 參數值不合法／5 狀態檔不存在或不可讀）。
任何一支 `print` 漏進 stdout、任何一個 rc 變色，Bridge 端就是錯誤分流（把「前置不符」讀成「程式壞了」，
或反過來）——這些只有真的起行程、讀真的 stdout／stderr／rc 才量得到。

每一組都編碼「拿掉修法會怎樣」（Rule 9）：把非法轉態 rc 改成 2 ⇒ rc 3 案紅；摘要改用原始 bytes ⇒ CRLF 案紅；
`--must-exist` 不擋建檔 ⇒ rc 5 案與「未建檔」斷言紅；先改狀態再驗前置 ⇒ 「狀態檔位元組不變」案紅。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest
import yaml

_V_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_V_ROOT))

from tools.fsm_runtime import state_loader as sl  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.transition_rules import TransitionError  # noqa: E402

# `-W ignore::RuntimeWarning`：`python -m tools.fsm_runtime.fsm_runtime` 的 runpy 警告與成敗無關
# （ADR §2.3 #14），Bridge 也這樣起；成敗只看 rc＋stdout。
_CLI = [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "tools.fsm_runtime.fsm_runtime"]
_PROJECT = "bridge-proj"


class Run:
    """一次 CLI 子行程的結果。"""

    def __init__(self, proc: subprocess.CompletedProcess) -> None:
        self.rc = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr

    @property
    def out_lines(self) -> list[str]:
        return [ln for ln in self.stdout.splitlines() if ln.strip()]

    @property
    def err_lines(self) -> list[str]:
        return [ln for ln in self.stderr.splitlines() if ln.strip()]

    @property
    def payload(self) -> dict:
        return json.loads(self.out_lines[-1])


def _child_env(state_dir: Path, extra: Optional[dict] = None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("SDD_STATE_DIR", "SDD_PROJECT", "PYTHONPATH")}
    env.update({
        "SDD_STATE_DIR": str(state_dir), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(_V_ROOT),
    })
    env.update(extra or {})
    return env


def run_cli(state_dir: Path, *argv: str, env_extra: Optional[dict] = None) -> Run:
    proc = subprocess.run(
        [*_CLI, *argv], cwd=str(_V_ROOT), env=_child_env(state_dir, env_extra), capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    return Run(proc)


@pytest.fixture()
def sdd_dir(tmp_path: Path) -> Path:
    """慣例形狀的狀態目錄 `<專案根>/build/reports/fsm`（專案根＝`sdd_dir.parents[2]`）。"""
    path = tmp_path / "proj" / "build" / "reports" / "fsm"
    path.mkdir(parents=True)
    return path


def state_path(state_dir: Path, project: str = _PROJECT) -> Path:
    return state_dir / f"FSM-STATE-{sl._sanitize_component(project)}.yaml"


def make_state(state_dir: Path, current: str, project: str = _PROJECT) -> Path:
    """用真 `load_state`／`save_state` 在暫存目錄造一個處於 `current` 的狀態檔。"""
    path = state_path(state_dir, project)
    state = sl.load_state(project, path=path)
    state.current = current
    sl.save_state(state)
    return path


def read_state(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["fsm_state"]


def last_trace(path: Path) -> dict:
    return read_state(path)["decision_trace"][-1]


def assert_single_line_ascii_json(result: Run) -> dict:
    """§4.1 stdout 契約：**恰好一行**、緊湊分隔、`ensure_ascii=True`（逐字重新序列化必須相等）。"""
    assert len(result.out_lines) == 1, f"stdout 不是恰好一行：{result.stdout!r}"
    result.stdout.encode("ascii")
    payload = result.payload
    assert result.out_lines[0] == json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return payload


def assert_failure(result: Run, *, rc: int, error: str, verb: str, current_state: Optional[str] = None) -> dict:
    """§4.1 失敗契約：rc、stdout 單行 JSON（`ok:false`＋`error`＋ASCII `detail` ≤200）、stderr 恰一行。"""
    assert result.rc == rc, (result.rc, result.stdout, result.stderr)
    payload = assert_single_line_ascii_json(result)
    assert payload["ok"] is False and payload["error"] == error, payload
    assert len(payload["detail"]) <= 200
    if current_state is not None:
        assert payload["current_state"] == current_state
    assert len(result.err_lines) == 1, result.stderr
    assert result.err_lines[0].startswith(f"[SDD-FSM] {verb} failed: {error}: "), result.err_lines
    result.stderr.encode("ascii")
    return payload


def assert_success(result: Run, *, verb: str, from_state: str, current_state: str) -> dict:
    assert result.rc == 0, (result.rc, result.stdout, result.stderr)
    assert result.err_lines == [], f"成功時 stderr 必須是空的：{result.stderr!r}"
    payload = assert_single_line_ascii_json(result)
    assert payload["ok"] is True and payload["verb"] == verb
    assert payload["from_state"] == from_state and payload["current_state"] == current_state
    return payload


# ───────────────────────── 四個新動詞共通：用法／參數／狀態檔（§4.1） ─────────────────────────
_VERBS = [
    ("negotiate-enter", []),
    ("negotiate-exit", ["--outcome", "agreed"]),
    ("delegate-enter", []),
    ("delegate-exit", ["--decision", "done"]),
]


@pytest.mark.parametrize("verb,extra", _VERBS, ids=[v[0] for v in _VERBS])
def test_missing_or_blank_reason_is_rc4_invalid_argument(sdd_dir: Path, verb: str, extra: list) -> None:
    """`--reason` 必填且 strip 後非空：它是寫進 decision_trace 的稽核憑證（缺 ⇒ rc 4，不是 rc 2）。"""
    path = make_state(sdd_dir, "SPEC_FROZEN")
    before = path.read_bytes()
    for reason_args in ([], ["--reason", ""], ["--reason", "   "]):
        result = run_cli(sdd_dir, verb, "--project", _PROJECT, *extra, *reason_args)
        assert_failure(result, rc=4, error="invalid_argument", verb=verb)
        assert "--reason" in result.payload["detail"]
    assert path.read_bytes() == before, "參數壞時不得動狀態檔"


@pytest.mark.parametrize("verb,extra", _VERBS, ids=[v[0] for v in _VERBS])
def test_missing_project_is_an_argparse_usage_error_rc2(sdd_dir: Path, verb: str, extra: list) -> None:
    result = run_cli(sdd_dir, verb, *extra, "--reason", "x")
    assert result.rc == 2, (result.rc, result.stderr)
    assert result.stdout == "", "用法錯誤時 stdout 不得有 JSON（Bridge 把 rc 2 當成『自己的 bug』）"
    assert "--project" in result.stderr


@pytest.mark.parametrize("verb,extra", _VERBS, ids=[v[0] for v in _VERBS])
def test_unknown_project_is_rc5_state_not_found_and_creates_nothing(
    sdd_dir: Path, verb: str, extra: list
) -> None:
    """四個新動詞恆視為已帶 `--must-exist`：現行 CLI 的 `show`／`transition` 會替不存在的專案自動建出 INIT
    狀態檔（ADR §2.3 #12），Bridge 因此無從知道「專案根綁錯了」。"""
    result = run_cli(sdd_dir, verb, "--project", "no-such-project", *extra, "--reason", "x")
    assert_failure(result, rc=5, error="state_not_found", verb=verb)
    assert list(sdd_dir.iterdir()) == [], "不得建檔"


def test_unreadable_state_file_is_rc5_state_unreadable(sdd_dir: Path) -> None:
    path = state_path(sdd_dir)
    path.write_text("fsm_state: [not, a, mapping\n", encoding="utf-8")  # 壞 YAML 且沒有 .bak
    result = run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "x")
    assert_failure(result, rc=5, error="state_unreadable", verb="delegate-enter")


@pytest.mark.parametrize("bad", ["relative/dir", ".", "..\\x"])
def test_relative_state_dir_is_rc4_naming_the_variable(sdd_dir: Path, bad: str) -> None:
    result = run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "x",
                     env_extra={"SDD_STATE_DIR": bad})
    payload = assert_failure(result, rc=4, error="invalid_argument", verb="delegate-enter")
    assert "SDD_STATE_DIR" in payload["detail"]


def test_non_ascii_project_and_reason_round_trip_with_ascii_only_stdout(sdd_dir: Path) -> None:
    """stdout／stderr 只能是 ASCII（CLI 入口無 UTF-8 stdio 保護，cp950 下非 ASCII 會炸），但中文原樣進 YAML。"""
    project = "訂單系統"
    path = make_state(sdd_dir, "IMPLEMENTATION", project)
    result = run_cli(sdd_dir, "delegate-enter", "--project", project, "--reason", "簽核：王小明 run=r1 START",
                     "--playbook-ref", "run:r1")
    payload = assert_success(result, verb="delegate-enter", from_state="IMPLEMENTATION",
                             current_state="AUTOCLAUDE_DELEGATED")
    assert payload["project"] == project
    assert last_trace(path)["reason"] == "簽核：王小明 run=r1 START"


# ───────────────────────────── negotiate-enter（§4.2） ─────────────────────────────
def test_negotiate_enter_moves_spec_frozen_to_test_contract_negotiated(sdd_dir: Path) -> None:
    path = make_state(sdd_dir, "SPEC_FROZEN")
    result = run_cli(sdd_dir, "negotiate-enter", "--project", _PROJECT,
                     "--reason", "console-signoff approver=alice; run=r1",
                     "--contract-ref", "docs/03_testing/contracts/TCS-X.md")
    payload = assert_success(result, verb="negotiate-enter", from_state="SPEC_FROZEN",
                             current_state="TEST_CONTRACT_NEGOTIATED")
    assert payload["entered"] is True and payload["from"] == "SPEC_FROZEN"
    assert payload["to"] == "TEST_CONTRACT_NEGOTIATED"
    trace = last_trace(path)
    assert trace["trigger"] == "test_contract_enter"
    assert trace["reason"] == "console-signoff approver=alice; run=r1"
    assert trace["spec_refs"] == ["docs/03_testing/contracts/TCS-X.md"]


def test_negotiate_enter_twice_is_a_noop_that_writes_nothing(sdd_dir: Path) -> None:
    path = make_state(sdd_dir, "TEST_CONTRACT_NEGOTIATED")
    before = path.read_bytes()
    result = run_cli(sdd_dir, "negotiate-enter", "--project", _PROJECT, "--reason", "again")
    payload = assert_success(result, verb="negotiate-enter", from_state="TEST_CONTRACT_NEGOTIATED",
                             current_state="TEST_CONTRACT_NEGOTIATED")
    assert payload["noop"] is True
    assert path.read_bytes() == before, "noop 不寫 trace、不動檔"


@pytest.mark.parametrize("state", ["HUMAN_PENDING", "IMPLEMENTATION", "ESCALATION"])
def test_negotiate_enter_from_the_wrong_state_is_rc3(sdd_dir: Path, state: str) -> None:
    """前置狀態只有 SPEC_FROZEN。反向對照：把非法轉態的 rc 改成 2（argparse 已佔用）⇒ 本案紅。"""
    path = make_state(sdd_dir, state)
    before = path.read_bytes()
    result = run_cli(sdd_dir, "negotiate-enter", "--project", _PROJECT, "--reason", "x")
    assert_failure(result, rc=3, error="transition_not_allowed", verb="negotiate-enter", current_state=state)
    assert path.read_bytes() == before


# ───────────────────────────── negotiate-exit（§4.2） ─────────────────────────────
@pytest.mark.parametrize("outcome,target", [("agreed", "IMPLEMENTATION"), ("underspecified", "SPEC_DRAFTING")])
def test_negotiate_exit_maps_the_outcome_to_the_target_state(sdd_dir: Path, outcome: str, target: str) -> None:
    path = make_state(sdd_dir, "TEST_CONTRACT_NEGOTIATED")
    result = run_cli(sdd_dir, "negotiate-exit", "--project", _PROJECT, "--outcome", outcome,
                     "--reason", "console-signoff approver=alice; oracle=x@sha256:0; basis=import-draft-signoff")
    payload = assert_success(result, verb="negotiate-exit", from_state="TEST_CONTRACT_NEGOTIATED",
                             current_state=target)
    assert payload["exited"] is True and payload["outcome"] == outcome and payload["to"] == target
    assert last_trace(path)["trigger"] == "test_contract_exit"


@pytest.mark.parametrize("state", ["SPEC_FROZEN", "IMPLEMENTATION", "AUTOCLAUDE_DELEGATED"])
def test_negotiate_exit_outside_the_negotiation_state_is_rc3(sdd_dir: Path, state: str) -> None:
    path = make_state(sdd_dir, state)
    before = path.read_bytes()
    result = run_cli(sdd_dir, "negotiate-exit", "--project", _PROJECT, "--outcome", "agreed", "--reason", "x")
    payload = assert_failure(result, rc=3, error="transition_not_allowed", verb="negotiate-exit",
                             current_state=state)
    assert "TEST_CONTRACT_NEGOTIATED" in payload["detail"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("outcome_args", [[], ["--outcome", "maybe"]])
def test_negotiate_exit_needs_a_valid_outcome_rc2(sdd_dir: Path, outcome_args: list) -> None:
    make_state(sdd_dir, "TEST_CONTRACT_NEGOTIATED")
    result = run_cli(sdd_dir, "negotiate-exit", "--project", _PROJECT, *outcome_args, "--reason", "x")
    assert result.rc == 2 and result.stdout == ""


# ───────────────────────────── delegate-enter（§4.2） ─────────────────────────────
def test_delegate_enter_records_tracking_and_playbook_ref(sdd_dir: Path) -> None:
    path = make_state(sdd_dir, "IMPLEMENTATION")
    result = run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "console-run run=r1 START",
                     "--playbook-ref", "run:r1")
    payload = assert_success(result, verb="delegate-enter", from_state="IMPLEMENTATION",
                             current_state="AUTOCLAUDE_DELEGATED")
    assert payload["entered"] is True and payload["to"] == "AUTOCLAUDE_DELEGATED"
    state = read_state(path)
    tracking = state["autoclaude_delegated_tracking"]
    assert tracking["resume_state"] == "IMPLEMENTATION" and tracking["playbook_ref"] == "run:r1"
    assert tracking["entered_at"]
    trace = state["decision_trace"][-1]
    assert trace["trigger"] == "autoclaude_delegated_enter" and trace["spec_refs"] == ["run:r1"]
    assert trace["reason"] == "console-run run=r1 START"


def test_delegate_enter_without_playbook_ref_leaves_the_key_out(sdd_dir: Path) -> None:
    """缺省不寫 `playbook_ref` 鍵：回收點靠「鍵缺或不以 `run:` 開頭」辨認外來（人進入的）委派（§10.3）。"""
    path = make_state(sdd_dir, "IMPLEMENTATION")
    assert run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "manual").rc == 0
    assert "playbook_ref" not in read_state(path)["autoclaude_delegated_tracking"]


def test_delegate_enter_twice_is_a_noop_that_keeps_the_first_tracking(sdd_dir: Path) -> None:
    path = make_state(sdd_dir, "IMPLEMENTATION")
    run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "first", "--playbook-ref", "run:r1")
    before = path.read_bytes()
    result = run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "second",
                     "--playbook-ref", "run:r2")
    payload = assert_success(result, verb="delegate-enter", from_state="AUTOCLAUDE_DELEGATED",
                             current_state="AUTOCLAUDE_DELEGATED")
    assert payload["noop"] is True
    assert path.read_bytes() == before, "noop 不寫 trace、不更新 tracking（ADR §4.2）"
    assert read_state(path)["autoclaude_delegated_tracking"]["playbook_ref"] == "run:r1"


@pytest.mark.parametrize("state", ["SPEC_FROZEN", "HUMAN_PENDING", "ESCALATION"])
def test_delegate_enter_only_from_implementation_rc3(sdd_dir: Path, state: str) -> None:
    path = make_state(sdd_dir, state)
    before = path.read_bytes()
    result = run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "x")
    payload = assert_failure(result, rc=3, error="transition_not_allowed", verb="delegate-enter",
                             current_state=state)
    assert "IMPLEMENTATION" in payload["detail"]
    assert path.read_bytes() == before


# ───────────────────────────── delegate-exit（§4.2） ─────────────────────────────
def _delegated(sdd_dir: Path) -> Path:
    path = make_state(sdd_dir, "IMPLEMENTATION")
    assert run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "start",
                   "--playbook-ref", "run:r1").rc == 0
    return path


def test_delegate_exit_done_hands_control_back_without_clearing_the_tracking(sdd_dir: Path) -> None:
    """D-115-15：`done`＝交還控制權、不是「成功」。tracking 不清除（〔乾跑 #15〕），所以任何人讀它之前
    都必須先看 `current_state`——這個『不清除』是契約的一部分，不是疏漏。"""
    path = _delegated(sdd_dir)
    result = run_cli(sdd_dir, "delegate-exit", "--project", _PROJECT, "--decision", "done",
                     "--reason", "console-run run=r1 CANCELLED")
    payload = assert_success(result, verb="delegate-exit", from_state="AUTOCLAUDE_DELEGATED",
                             current_state="IMPLEMENTATION")
    assert payload["exited"] is True and payload["decision"] == "done" and payload["to"] == "IMPLEMENTATION"
    state = read_state(path)
    assert state["autoclaude_delegated_tracking"]["playbook_ref"] == "run:r1"
    trace = state["decision_trace"][-1]
    assert trace["trigger"] == "autoclaude_delegated_exit"
    assert trace["reason"] == "console-run run=r1 CANCELLED"


def test_delegate_exit_failed_escalates_with_provenance_and_an_open_history_entry(sdd_dir: Path) -> None:
    path = _delegated(sdd_dir)
    reason = "console-run run=r1 ENGINE-ESCALATION step=s1: retries exhausted"
    result = run_cli(sdd_dir, "delegate-exit", "--project", _PROJECT, "--decision", "failed", "--reason", reason)
    assert_success(result, verb="delegate-exit", from_state="AUTOCLAUDE_DELEGATED", current_state="ESCALATION")
    state = read_state(path)
    provenance = state["escalation_provenance"]
    assert provenance["source"] == "autoclaude_delegated_failed" and provenance["reason"] == reason
    last = state["escalation_history"][-1]
    assert last["trigger_reason"] == reason and last["resolved_at"] is None, "恢復只有人：歷史尾端必須是未結的"
    assert state["autoclaude_delegated_tracking"]["playbook_ref"] == "run:r1", "ESCALATION 時仍保留，Console 據此指出哪個 run"


@pytest.mark.parametrize("state", ["IMPLEMENTATION", "ESCALATION", "SPEC_FROZEN"])
def test_delegate_exit_outside_a_delegation_is_rc3(sdd_dir: Path, state: str) -> None:
    """回收只對 AUTOCLAUDE_DELEGATED 成立：ESCALATION 只有人能解（絕對禁令 #6；〔乾跑 #18〕）。"""
    path = make_state(sdd_dir, state)
    before = path.read_bytes()
    result = run_cli(sdd_dir, "delegate-exit", "--project", _PROJECT, "--decision", "done", "--reason", "x")
    payload = assert_failure(result, rc=3, error="transition_not_allowed", verb="delegate-exit",
                             current_state=state)
    assert "AUTOCLAUDE_DELEGATED" in payload["detail"]
    assert path.read_bytes() == before


@pytest.mark.parametrize("decision_args", [[], ["--decision", "aborted"]])
def test_delegate_exit_needs_a_valid_decision_rc2(sdd_dir: Path, decision_args: list) -> None:
    _delegated(sdd_dir)
    result = run_cli(sdd_dir, "delegate-exit", "--project", _PROJECT, *decision_args, "--reason", "x")
    assert result.rc == 2 and result.stdout == ""


def test_human_resume_after_a_failed_delegation_allows_the_next_delegation(sdd_dir: Path) -> None:
    """ADR §5.3：failed → ESCALATION → 人工 `resume-from-escalation`（現行 CLI，不改）→ 下一批次可直接啟動。"""
    path = _delegated(sdd_dir)
    run_cli(sdd_dir, "delegate-exit", "--project", _PROJECT, "--decision", "failed", "--reason", "boom")
    blocked = run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "retry")
    assert_failure(blocked, rc=3, error="transition_not_allowed", verb="delegate-enter", current_state="ESCALATION")
    resumed = run_cli(sdd_dir, "resume-from-escalation", "--project", _PROJECT, "--to", "IMPLEMENTATION",
                      "--reason", "human fixed env; retry delegation")
    assert resumed.rc == 0, resumed.stderr
    assert read_state(path)["escalation_history"][-1]["resolved_at"]
    again = run_cli(sdd_dir, "delegate-enter", "--project", _PROJECT, "--reason", "retry", "--playbook-ref", "run:r2")
    assert_success(again, verb="delegate-enter", from_state="IMPLEMENTATION", current_state="AUTOCLAUDE_DELEGATED")
    assert read_state(path)["autoclaude_delegated_tracking"]["playbook_ref"] == "run:r2"


# ───────────────────────────── spec-frozen（§4.3）：舊行為逐字不變 ─────────────────────────────
def test_spec_frozen_without_the_new_flags_is_exactly_the_legacy_behaviour(sdd_dir: Path) -> None:
    """不帶 `--digest`／`--json`＝現行行為：不查檔、不算摘要、`spec_docs` 照字面記、輸出就是那一行。
    這保住既有測試與 F-SBR 驅動腳本；新鍵「只在有值時才出現」，舊讀者不受影響。"""
    path = make_state(sdd_dir, "HUMAN_PENDING")
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "Stage-2",
                     "--doc", "docs/03_testing/contracts/TCS-DOES-NOT-EXIST.md")
    assert result.rc == 0, result.stderr
    assert result.stdout.replace("\r\n", "\n") == "OK spec frozen: Stage-2\n"
    state = read_state(path)
    entry = state["frozen_stages"][0]
    assert set(entry) == {"stage", "frozen_at", "compaction_report", "spec_docs"}
    assert entry["spec_docs"] == ["docs/03_testing/contracts/TCS-DOES-NOT-EXIST.md"]
    assert state["current_state"] == "SPEC_FROZEN"
    assert state["decision_trace"][-1]["reason"] == "Stage frozen: Stage-2"
    assert state["decision_trace"][-1]["spec_refs"] == entry["spec_docs"]


def test_legacy_spec_frozen_from_the_wrong_state_is_still_a_traceback_with_rc1(sdd_dir: Path) -> None:
    """現行非法轉態＝traceback＋rc 1（ADR §2.3 #5）：不帶新旗標的呼叫者不得被新契約改變 rc。"""
    path = make_state(sdd_dir, "IMPLEMENTATION")
    before = path.read_bytes()
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "Stage-X")
    assert result.rc == 1 and result.stdout == ""
    assert "TransitionError" in result.stderr and "IMPLEMENTATION -> SPEC_FROZEN" in result.stderr
    assert path.read_bytes() == before


def test_legacy_verbs_keep_their_output_and_rc(sdd_dir: Path) -> None:
    make_state(sdd_dir, "INIT")
    ok = run_cli(sdd_dir, "transition", "--project", _PROJECT, "--to", "SCENARIO_DETECT")
    assert ok.rc == 0 and ok.stdout.replace("\r\n", "\n") == "OK transitioned to SCENARIO_DETECT\n"
    bad = run_cli(sdd_dir, "transition", "--project", _PROJECT, "--to", "PR_REVIEW")
    assert bad.rc == 1 and bad.stdout == "" and "TransitionError" in bad.stderr


def test_must_exist_on_a_legacy_verb_refuses_to_create_a_state_file(sdd_dir: Path) -> None:
    result = run_cli(sdd_dir, "show", "--project", "ghost", "--must-exist")
    assert_failure(result, rc=5, error="state_not_found", verb="show")
    assert list(sdd_dir.iterdir()) == []
    make_state(sdd_dir, "INIT", "real")
    shown = run_cli(sdd_dir, "show", "--project", "real", "--must-exist")
    assert shown.rc == 0 and json.loads(shown.stdout)["fsm_state"]["current_state"] == "INIT"


def test_legacy_show_still_creates_the_state_file_which_is_why_must_exist_exists(sdd_dir: Path) -> None:
    result = run_cli(sdd_dir, "show", "--project", "auto-created")
    assert result.rc == 0 and state_path(sdd_dir, "auto-created").is_file()


# ───────────────────────────── spec-frozen --digest／--json（§4.3） ─────────────────────────────
def _tcs(sdd_dir: Path, name: str = "TCS-X.md", raw: bytes = b"# AT-001-1-1\r\nline\r\n") -> Path:
    """在專案根（`sdd_dir.parents[2]`）建一份規格檔，回其絕對路徑。"""
    doc = sdd_dir.parents[2] / "docs" / "03_testing" / "contracts" / name
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_bytes(raw)
    return doc


def _lf_digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def test_spec_frozen_digest_json_records_digests_approver_and_reason(sdd_dir: Path) -> None:
    path = make_state(sdd_dir, "HUMAN_PENDING")
    raw = b"# AT-001-1-1\r\nline\r\n"
    _tcs(sdd_dir, raw=raw)
    reason = "console-freeze approver=alice; reason=SCG-3 ok"
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "Stage-3", "--digest", "--json",
                     "--must-exist", "--root", str(sdd_dir.parents[2]), "--approver", "alice", "--reason", reason,
                     "--doc", "docs/03_testing/contracts/TCS-X.md")
    payload = assert_success(result, verb="spec-frozen", from_state="HUMAN_PENDING", current_state="SPEC_FROZEN")
    key = "docs/03_testing/contracts/TCS-X.md"
    assert payload["stage"] == "Stage-3" and payload["spec_doc_digests"] == {key: _lf_digest(raw)}
    state = read_state(path)
    entry = state["frozen_stages"][-1]
    assert entry["spec_docs"] == [key], "spec_docs 與摘要鍵必須是同一組正規化字串"
    assert entry["spec_doc_digests"] == {key: _lf_digest(raw)}
    assert entry["approved_by"] == "alice"
    assert state["decision_trace"][-1]["reason"] == reason and state["decision_trace"][-1]["spec_refs"] == [key]
    assert state["cumulative_history"]["total_spec_frozen_count"] == 1


def test_crlf_and_lf_files_get_the_same_digest_so_an_editor_save_does_not_break_the_freeze(sdd_dir: Path) -> None:
    """摘要是**正規化文字**不是原始 bytes：Windows 編輯器存成 CRLF 是常態。反向對照：改回原始 bytes ⇒ 紅。"""
    make_state(sdd_dir, "HUMAN_PENDING", "crlf")
    make_state(sdd_dir, "HUMAN_PENDING", "lf")
    _tcs(sdd_dir, "CRLF.md", b"a\r\nb\r\n")
    _tcs(sdd_dir, "LF.md", b"a\nb\n")
    digests = {}
    for project, name in (("crlf", "CRLF.md"), ("lf", "LF.md")):
        result = run_cli(sdd_dir, "spec-frozen", "--project", project, "--stage", "S", "--digest", "--json",
                         "--doc", f"docs/03_testing/contracts/{name}")
        digests[project] = next(iter(assert_success(
            result, verb="spec-frozen", from_state="HUMAN_PENDING", current_state="SPEC_FROZEN"
        )["spec_doc_digests"].values()))
    assert digests["crlf"] == digests["lf"] == _lf_digest(b"a\nb\n")


def test_digest_without_json_prints_the_legacy_line_but_still_records_the_digests(sdd_dir: Path) -> None:
    path = make_state(sdd_dir, "HUMAN_PENDING")
    _tcs(sdd_dir)
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "Stage-1", "--digest",
                     "--doc", "docs/03_testing/contracts/TCS-X.md")
    assert result.rc == 0 and result.stdout.replace("\r\n", "\n") == "OK spec frozen: Stage-1\n"
    assert read_state(path)["frozen_stages"][-1]["spec_doc_digests"]


def test_json_without_digest_reports_the_stage_only(sdd_dir: Path) -> None:
    make_state(sdd_dir, "HUMAN_PENDING")
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "Stage-1", "--json",
                     "--doc", "docs/whatever.md")
    payload = assert_success(result, verb="spec-frozen", from_state="HUMAN_PENDING", current_state="SPEC_FROZEN")
    assert payload["stage"] == "Stage-1" and "spec_doc_digests" not in payload


def test_root_is_derived_from_a_conventional_state_dir(sdd_dir: Path) -> None:
    """省略 `--root`：狀態目錄以 `build/reports/fsm` 結尾 ⇒ 取其上三層（兩種情況在預設框架目錄下一致）。"""
    make_state(sdd_dir, "HUMAN_PENDING")
    _tcs(sdd_dir)
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--digest", "--json",
                     "--doc", "docs/03_testing/contracts/TCS-X.md")
    assert result.rc == 0, result.stdout


def test_a_custom_state_dir_without_root_fails_loudly_instead_of_digesting_the_wrong_file(tmp_path: Path) -> None:
    """自訂 `SDD_STATE_DIR` 落在慣例之外而未給 `--root`：退回框架自身專案根，`doc_not_found` 大聲失敗。"""
    custom = tmp_path / "custom-state"
    custom.mkdir()
    make_state(custom, "HUMAN_PENDING")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "TCS-X.md").write_text("x", encoding="utf-8")
    result = run_cli(custom, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--digest", "--json",
                     "--doc", "docs/TCS-X.md")
    assert_failure(result, rc=4, error="doc_not_found", verb="spec-frozen")


@pytest.mark.parametrize(
    "case",
    ["missing", "outside_root", "not_utf8", "too_large", "directory"],
)
def test_bad_docs_are_rc4_and_leave_the_state_file_byte_identical(sdd_dir: Path, case: str) -> None:
    """**先驗前置、再算摘要、最後才改狀態**：任何一份文件有問題，狀態檔位元組不得改變（含 trace、重試歸零）。"""
    path = make_state(sdd_dir, "HUMAN_PENDING")
    before = path.read_bytes()
    root = sdd_dir.parents[2]
    (root.parent / "outside.md").write_text("outside", encoding="utf-8")  # 根外「存在」的檔：擋的是路徑不是缺檔
    doc, error = {
        "missing": ("docs/03_testing/contracts/NOPE.md", "doc_not_found"),
        "outside_root": ("../outside.md", "doc_outside_root"),
        "not_utf8": ("docs/bad.md", "doc_not_utf8"),
        "too_large": ("docs/huge.md", "doc_too_large"),
        "directory": ("docs", "doc_not_found"),
    }[case]
    (root / "docs").mkdir(exist_ok=True)
    if case == "not_utf8":
        (root / "docs" / "bad.md").write_bytes(b"\xff\xfe\x00 not utf-8")
    if case == "too_large":  # 上限 16 MiB（含）；多一個 byte 即超限
        (root / "docs" / "huge.md").write_bytes(b"x" * (16 * 1024 * 1024 + 1))
    _tcs(sdd_dir)  # 一份好的排在前面：證明「部分成功」也不會寫入
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--digest", "--json",
                     "--doc", "docs/03_testing/contracts/TCS-X.md", "--doc", doc)
    assert_failure(result, rc=4, error=error, verb="spec-frozen")
    assert path.read_bytes() == before


def test_wrong_state_is_rc3_even_when_a_doc_is_also_bad(sdd_dir: Path) -> None:
    """優先序：前置狀態先於摘要——狀態不對時根本不該去讀檔（也不洩漏檔案存在與否）。"""
    path = make_state(sdd_dir, "IMPLEMENTATION")
    before = path.read_bytes()
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--digest", "--json",
                     "--doc", "docs/missing.md")
    assert_failure(result, rc=3, error="transition_not_allowed", verb="spec-frozen", current_state="IMPLEMENTATION")
    assert path.read_bytes() == before


def test_digest_needs_at_least_one_doc(sdd_dir: Path) -> None:
    """`--digest` 沒給任何 `--doc` 會記一個空摘要表＝被讀成「沒綁內容」而放行；寧可大聲拒絕。"""
    make_state(sdd_dir, "HUMAN_PENDING")
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--digest", "--json")
    payload = assert_failure(result, rc=4, error="invalid_argument", verb="spec-frozen")
    assert "--doc" in payload["detail"]


@pytest.mark.parametrize("approver", ["   ", "x" * 101, "ali\nce", "ali\tce"])
def test_invalid_approver_is_rc4(sdd_dir: Path, approver: str) -> None:
    path = make_state(sdd_dir, "HUMAN_PENDING")
    before = path.read_bytes()
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--json",
                     "--approver", approver)
    assert_failure(result, rc=4, error="invalid_argument", verb="spec-frozen")
    assert path.read_bytes() == before


def test_approver_boundary_100_chars_is_accepted(sdd_dir: Path) -> None:
    path = make_state(sdd_dir, "HUMAN_PENDING")
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--json",
                     "--approver", "王" * 100)
    assert result.rc == 0, result.stdout
    assert read_state(path)["frozen_stages"][-1]["approved_by"] == "王" * 100


@pytest.mark.parametrize("root_arg", ["relative/root", "{missing}"])
def test_bad_root_is_rc4(sdd_dir: Path, root_arg: str) -> None:
    make_state(sdd_dir, "HUMAN_PENDING")
    root_arg = root_arg.replace("{missing}", str(sdd_dir.parents[2] / "does-not-exist"))
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--digest", "--json",
                     "--root", root_arg, "--doc", "docs/x.md")
    assert_failure(result, rc=4, error="invalid_argument", verb="spec-frozen")


def test_root_without_digest_is_a_usage_error(sdd_dir: Path) -> None:
    make_state(sdd_dir, "HUMAN_PENDING")
    result = run_cli(sdd_dir, "spec-frozen", "--project", _PROJECT, "--stage", "S", "--json",
                     "--root", str(sdd_dir.parents[2]))
    assert result.rc == 2 and result.stdout == ""


def test_spec_frozen_must_exist_refuses_to_create_a_state_file(sdd_dir: Path) -> None:
    result = run_cli(sdd_dir, "spec-frozen", "--project", "ghost", "--stage", "S", "--json", "--must-exist")
    assert_failure(result, rc=5, error="state_not_found", verb="spec-frozen")
    assert list(sdd_dir.iterdir()) == []


# ───────────────────────────── 端到端：Bridge 一個批次會走的整條路 ─────────────────────────────
def test_the_whole_bridge_sequence_through_the_cli(sdd_dir: Path) -> None:
    """HUMAN_PENDING →（凍結）SPEC_FROZEN →（談判）TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION →（委派）
    AUTOCLAUDE_DELEGATED → IMPLEMENTATION。全程不改 `_HAPPY_PATH`、不碰任何 `*.tla`（ADR §2.3 判讀 a）。"""
    path = make_state(sdd_dir, "HUMAN_PENDING")
    _tcs(sdd_dir)
    steps = [
        (["spec-frozen", "--stage", "Stage-1", "--digest", "--json", "--must-exist", "--approver", "alice",
          "--reason", "console-freeze approver=alice; reason=ok", "--doc", "docs/03_testing/contracts/TCS-X.md"],
         "SPEC_FROZEN"),
        (["negotiate-enter", "--reason", "console-signoff approver=alice; run=r1"], "TEST_CONTRACT_NEGOTIATED"),
        (["negotiate-exit", "--outcome", "agreed", "--reason", "console-signoff approver=alice; basis=import-draft-signoff"],
         "IMPLEMENTATION"),
        (["delegate-enter", "--reason", "console-run run=r1 START", "--playbook-ref", "run:r1"],
         "AUTOCLAUDE_DELEGATED"),
        (["delegate-exit", "--decision", "done", "--reason", "console-run run=r1 COMPLETED"], "IMPLEMENTATION"),
    ]
    for argv, expected in steps:
        result = run_cli(sdd_dir, argv[0], "--project", _PROJECT, *argv[1:])
        assert result.rc == 0, (argv[0], result.stdout, result.stderr)
        assert assert_single_line_ascii_json(result)["current_state"] == expected
    triggers = [e["trigger"] for e in read_state(path)["decision_trace"]]
    assert triggers[-5:] == ["spec_frozen", "test_contract_enter", "test_contract_exit",
                             "autoclaude_delegated_enter", "autoclaude_delegated_exit"]


# ───────────────────────────── API 層：`record_spec_frozen` 先驗前置 ─────────────────────────────
def test_record_spec_frozen_validates_the_precondition_before_touching_memory(tmp_path: Path) -> None:
    """此前 `record_spec_frozen` 先改記憶體（`frozen_stages`／計數／retry 歸零）再轉態：前置不合法時
    `TransitionError` 留下一個改了一半的記憶體狀態，持有同一個 runtime 物件的呼叫端會看到它。
    現在先驗：不合法就什麼都沒動（錯誤型別與訊息不變）。"""
    state = sl.load_state("api-proj", path=tmp_path / "FSM-STATE-api.yaml")
    state.current = "IMPLEMENTATION"
    state.retry("SCG_VALIDATION")["current_count"] = 2
    runtime = FSMRuntime(state)
    with pytest.raises(TransitionError, match="IMPLEMENTATION -> SPEC_FROZEN"):
        runtime.record_spec_frozen("Stage-1", ["docs/x.md"], spec_doc_digests={"docs/x.md": "sha256:0"})
    assert not state.root.get("frozen_stages")
    assert state.root["retry_history"]["SCG_VALIDATION"]["current_count"] == 2
    assert int(state.cumulative().get("total_spec_frozen_count", 0)) == 0
    assert state.current == "IMPLEMENTATION"


def test_record_spec_frozen_omits_the_new_keys_when_they_have_no_value(tmp_path: Path) -> None:
    state = sl.load_state("api-proj", path=tmp_path / "FSM-STATE-api.yaml")
    state.current = "HUMAN_PENDING"
    FSMRuntime(state).record_spec_frozen("Stage-1", ["docs/x.md"])
    assert set(state.root["frozen_stages"][-1]) == {"stage", "frozen_at", "compaction_report", "spec_docs"}
