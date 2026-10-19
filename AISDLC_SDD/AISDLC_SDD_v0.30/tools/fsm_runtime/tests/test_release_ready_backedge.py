# enforces (governance rules): R-9.1, R-9.18
"""OBS-SI-117：`RELEASE_READY → IMPLEMENTATION` 有界回邊的守護測試。

為什麼有這條邊：雲端 CI 在 RELEASE_READY（SCG-6）才紅時，此前唯一出邊是 RELEASE，沒有任何合法回邊，
功能鍵只能以「鍵外的維護 commit」修（真機實例：P0 鍵遇 root-infra-ci ubuntu 夾具競態）。新邊走
`gate --gate RELEASE_READY --result FAIL --reason …`，由 `RETRY_LIMITS["RELEASE_READY"]`（同 RTM_VERIFY：
第 2 次失敗即 ESCALATION）把關，且不可自動恢復——所以「有界」要在**磁碟上**成立，不是只在印出的 JSON 裡。

每一組都編碼「拿掉修法會怎樣」（Rule 9）：回邊不入 `_HAPPY_PATH` ⇒ 回邊案紅；不記次數 ⇒ 第 2 次不升級案紅；
升級分支不存檔 ⇒ 「磁碟上是 ESCALATION」案紅（這正是本輪順手揪出的既有缺陷：`record_gate_result` 耗盡分支
從未存檔，`SDD_ENABLE_AUTO_RECOVERY=0` 時 CLI 印 `escalated: true`、狀態檔卻原封不動）；回邊改成無界的
`Move` ⇒ TLA 形狀案紅。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest
import yaml

_V_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_V_ROOT))

from tools.fsm_runtime import spec_monitor  # noqa: E402
from tools.fsm_runtime import state_loader as sl  # noqa: E402
from tools.fsm_runtime import transition_rules as tr  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402

_PROJECT = "relready-proj"
_TLA = _V_ROOT / "tools" / "fsm_runtime" / "formal" / "SDD_FSM.tla"
_CLI = [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "tools.fsm_runtime.fsm_runtime"]


# ───────────────────────────── 共用小工具 ─────────────────────────────
def _runtime(tmp_path: Path, current: str = "RELEASE_READY") -> FSMRuntime:
    """真 `load_state`／`save_state` 造出、處於 `current` 的 runtime（已存檔）。"""
    state = sl.load_state(_PROJECT, path=tmp_path / "FSM-STATE-relready.yaml")
    state.current = current
    sl.save_state(state)
    return FSMRuntime(state)


def _disk(runtime: FSMRuntime) -> dict:
    """從磁碟重新讀（不是看記憶體）：有界停機必須在這裡成立。"""
    return yaml.safe_load(runtime.state.path.read_text(encoding="utf-8"))["fsm_state"]


def _walk_back_to_release_ready(runtime: FSMRuntime) -> None:
    """IMPLEMENTATION →（實作完）PR_REVIEW →（SCG-4 PASS）RTM_VERIFY →（SCG-5 PASS）RELEASE_READY：真走一遍合法路徑。"""
    assert runtime.state.current == "IMPLEMENTATION"
    runtime.transition("PR_REVIEW", reason="fixed, back to review")
    runtime.record_gate_result("PR_REVIEW", "PASS", "SCG-4 PASS")
    runtime.record_gate_result("RTM_VERIFY", "PASS", "SCG-5 PASS")
    assert runtime.state.current == "RELEASE_READY"


# ───────────────────────────── 規則表層 ─────────────────────────────
def test_release_ready_exits_are_release_and_the_new_back_edge_to_implementation() -> None:
    assert tr._HAPPY_PATH["RELEASE_READY"] == {"RELEASE", "IMPLEMENTATION"}
    assert tr.is_transition_allowed("RELEASE_READY", "IMPLEMENTATION")
    assert tr.is_transition_allowed("RELEASE_READY", "RELEASE"), "原本唯一的出邊不得被新邊擠掉"


def test_the_limit_is_two_with_the_same_semantics_as_rtm_verify() -> None:
    """語意釘死：`limit` 次失敗即升級——2＝第 1 次失敗退回 IMPLEMENTATION、第 2 次失敗 ESCALATION。
    （與 RTM_VERIFY 同值同語意；想放寬成「兩次回邊」就把常數改 3，並同步 md／TLA 註解，不是改判斷式。）"""
    assert tr.RETRY_LIMITS["RELEASE_READY"] == tr.RETRY_LIMITS["RTM_VERIFY"] == 2
    assert tr.next_state_on_gate_fail("RELEASE_READY", 1) == ("IMPLEMENTATION", False)
    assert tr.next_state_on_gate_fail("RELEASE_READY", 2) == ("ESCALATION", True)
    assert tr.next_state_on_gate_pass("RELEASE_READY") == "RELEASE"


def test_every_gate_that_can_fail_can_also_pass() -> None:
    """有 FAIL 就必須有 PASS：只能失敗不能通過的 gate，`gate --result PASS` 會是 KeyError traceback。"""
    for gate in tr.RETRY_LIMITS:
        assert tr.next_state_on_gate_pass(gate)
        assert tr.next_state_on_gate_fail(gate, 1)[0]


def test_the_state_template_carries_the_release_ready_block_with_the_code_limit() -> None:
    """模板的 `max_limit` 只是資訊欄，但資訊欄與常數各說各話就是下一個「文件與實況不一致」。"""
    template = yaml.safe_load(sl.TEMPLATE_PATH.read_text(encoding="utf-8"))
    block = template["fsm_state"]["retry_history"]["RELEASE_READY"]
    assert block["current_count"] == 0 and block["history"] == []
    assert block["max_limit"] == tr.RETRY_LIMITS["RELEASE_READY"]


def test_the_engine_doc_states_the_code_limit_in_its_state_block_and_retry_budget_table() -> None:
    """md↔py 同步測試只比邊，不比次數；上限數字各說各話是下一個「文件與實況不一致」。"""
    md = (_V_ROOT / "workflow" / "sdd-fsm-engine" / "SDD_FSM_ENGINE.md").read_text(encoding="utf-8")
    limit = tr.RETRY_LIMITS["RELEASE_READY"]
    table_row = re.search(r"^\| RELEASE_READY[^|]*\| (\d+)次 \|", md, re.MULTILINE)
    assert table_row is not None, "SDD_FSM_ENGINE.md 的 Retry Budget 速查表沒有 RELEASE_READY 列"
    assert int(table_row.group(1)) == limit
    block = re.search(r"^  RELEASE_READY:\n(?:    .*\n)+", md, re.MULTILINE)
    assert block is not None and f"retry_limit: {limit}" in block.group(0)


def test_the_tla_back_edge_is_the_bounded_gate_retry_shape_not_an_unbounded_move() -> None:
    """Rule 9.18.1：邊的**形狀**也要同步，不只是 (src,dst) 配對。回邊必須是 GateRetry（retry<MAX_RETRY 才可走、
    ++retry）加 GateExhaust（耗盡即 ESCALATION），而且兩者都列在 Next 裡；改成 `Move` 就成了無界回邊，
    而 test_tla_python_sync 只比配對、看不出來。"""
    tla = _TLA.read_text(encoding="utf-8")
    assert re.search(r'^T_RelReadyFail\s*==\s*GateRetry\("RELEASE_READY",\s*"IMPLEMENTATION"\)', tla, re.M)
    assert re.search(r'^T_RelReadyExhaust\s*==\s*GateExhaust\("RELEASE_READY"\)', tla, re.M)
    next_body = tla.split("Next ==", 1)[1].split("Fairness ==", 1)[0]
    assert "T_RelReadyFail" in next_body and "T_RelReadyExhaust" in next_body


# ───────────────────────────── API 層：回邊與計數 ─────────────────────────────
def test_first_failure_goes_back_to_implementation_with_a_count_and_an_audit_trace(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    reason = "root-infra-ci ubuntu fixture race (run 123)"
    payload = runtime.record_gate_result("RELEASE_READY", "FAIL", reason)
    assert payload["next_state"] == "IMPLEMENTATION" and payload["retry_count"] == 1
    assert "escalated" not in payload
    disk = _disk(runtime)
    assert disk["current_state"] == "IMPLEMENTATION"
    assert disk["retry_history"]["RELEASE_READY"]["current_count"] == 1
    assert disk["retry_history"]["RELEASE_READY"]["history"][-1]["failure_reason"] == reason
    trace = disk["decision_trace"][-1]
    assert (trace["from"], trace["to"], trace["trigger"]) == ("RELEASE_READY", "IMPLEMENTATION", "gate_fail")
    assert reason in trace["reason"]


@pytest.mark.parametrize("auto_recovery", ["unset", "0"])
def test_second_failure_escalates_and_the_escalation_is_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, auto_recovery: str
) -> None:
    """有界停機要在**磁碟上**成立。auto-recovery 預設開（unset）與顯式關（0）兩種都要綠：RELEASE_READY 不可
    恢復，所以兩種設定下都是「停在已落盤的 ESCALATION 等人」，不得進 AUTO_RECOVERY_ATTEMPT／ESCALATION_FINAL。"""
    if auto_recovery == "unset":
        monkeypatch.delenv("SDD_ENABLE_AUTO_RECOVERY", raising=False)
    else:
        monkeypatch.setenv("SDD_ENABLE_AUTO_RECOVERY", auto_recovery)
    runtime = _runtime(tmp_path)
    runtime.record_gate_result("RELEASE_READY", "FAIL", "CI red #1")
    _walk_back_to_release_ready(runtime)
    assert _disk(runtime)["retry_history"]["RELEASE_READY"]["current_count"] == 1, "走完 PR/RTM 兩關計數不得被洗掉"

    payload = runtime.record_gate_result("RELEASE_READY", "FAIL", "CI red #2")

    assert payload["escalated"] is True and payload["next_state"] == "ESCALATION"
    assert "auto_recovery" not in payload, "RELEASE_READY 刻意不可自動恢復"
    disk = _disk(runtime)
    assert disk["current_state"] == "ESCALATION", "CLI 印 escalated 而磁碟沒寫＝有界停機只存在於輸出"
    assert disk["retry_history"]["RELEASE_READY"]["current_count"] == 2
    assert disk["escalation_provenance"]["source"] == "gate_retry_budget:RELEASE_READY"
    assert disk["escalation_history"][-1]["resolved_at"] is None, "恢復只有人"


def test_escalation_on_disk_also_holds_for_the_existing_gates_when_auto_recovery_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """同一個既有缺陷的原樣重現：SDD_ENABLE_AUTO_RECOVERY=0 時，任何 gate 的耗盡升級此前都不存檔
    （記憶體是 ESCALATION、磁碟停在 RTM_VERIFY 且計數少一次）。修在 record_gate_result 的耗盡分支。"""
    monkeypatch.setenv("SDD_ENABLE_AUTO_RECOVERY", "0")
    runtime = _runtime(tmp_path, "RTM_VERIFY")
    runtime.record_gate_result("RTM_VERIFY", "FAIL", "gap #1")
    runtime.state.current = "RTM_VERIFY"
    payload = runtime.record_gate_result("RTM_VERIFY", "FAIL", "gap #2")
    assert payload["escalated"] is True
    disk = _disk(runtime)
    assert disk["current_state"] == "ESCALATION"
    assert disk["retry_history"]["RTM_VERIFY"]["current_count"] == 2


def test_a_failure_without_a_reason_is_refused_before_anything_changes(tmp_path: Path) -> None:
    """RELEASE_READY FAIL 是把已到發布關卡的規格退回實作：沒有理由就沒有稽核憑證。先於任何改動就拒絕——
    不得留下「計數 +1 但 trace 沒理由」的半套。"""
    runtime = _runtime(tmp_path)
    before = runtime.state.path.read_bytes()
    for blank in ("", "   ", "\n"):
        with pytest.raises(ValueError, match="reason"):
            runtime.record_gate_result("RELEASE_READY", "FAIL", blank)
    assert runtime.state.path.read_bytes() == before
    assert runtime.state.current == "RELEASE_READY"
    assert runtime.state.root["retry_history"]["RELEASE_READY"]["current_count"] == 0


def test_the_reason_rule_is_scoped_to_release_ready_fail_and_pass_needs_no_reason(tmp_path: Path) -> None:
    """不得牽連其他 gate 的既有行為（RTM_VERIFY FAIL 理由可省），RELEASE_READY 的 PASS 也不要理由。"""
    other = tmp_path / "other"
    other.mkdir()
    rtm = _runtime(other, "RTM_VERIFY")
    assert rtm.record_gate_result("RTM_VERIFY", "FAIL")["next_state"] == "IMPLEMENTATION"
    release = _runtime(tmp_path, "RELEASE_READY")
    assert release.record_gate_result("RELEASE_READY", "PASS")["next_state"] == "RELEASE"


def test_pass_reaches_release_and_resets_the_counter(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.record_gate_result("RELEASE_READY", "FAIL", "CI red")
    _walk_back_to_release_ready(runtime)
    payload = runtime.record_gate_result("RELEASE_READY", "PASS", "SCG-6 PASS")
    assert payload["next_state"] == "RELEASE"
    disk = _disk(runtime)
    assert disk["current_state"] == "RELEASE" and disk["retry_history"]["RELEASE_READY"]["current_count"] == 0


def test_a_new_freeze_starts_a_new_cycle_for_the_release_ready_counter(tmp_path: Path) -> None:
    """SPEC_FROZEN 重置所有 gate 的 current_count（md：重置所有 retry_counter）；RELEASE_READY 有計數了就該一視同仁，
    否則舊階段留下的 1 次失敗會讓新階段的 SCG-6 少一次機會。"""
    runtime = _runtime(tmp_path, "HUMAN_PENDING")
    runtime.state.retry("RELEASE_READY")["current_count"] = 1
    runtime.record_spec_frozen("Stage-2", ["docs/x.md"])
    assert runtime.state.retry("RELEASE_READY")["current_count"] == 0
    assert runtime.state.cumulative()["total_spec_frozen_count"] == 1, "歸零的是 current_count，不是累計史"


def test_a_legacy_state_file_without_the_block_is_read_as_zero_without_hand_editing(tmp_path: Path) -> None:
    """不得要求人手改既有狀態檔：真機的 FSM-STATE 檔（含已 RELEASE_READY／RELEASE 的）都沒有這個區塊。"""
    runtime = _runtime(tmp_path)
    doc = yaml.safe_load(runtime.state.path.read_text(encoding="utf-8"))
    assert "RELEASE_READY" in doc["fsm_state"]["retry_history"], "前提：新建的狀態檔（模板）有這個區塊"
    del doc["fsm_state"]["retry_history"]["RELEASE_READY"]  # 拿掉＝真機上既有的舊格式狀態檔
    runtime.state.path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    reloaded = FSMRuntime(sl.load_state(_PROJECT, path=runtime.state.path, create_if_missing=False))
    assert "RELEASE_READY" not in reloaded.state.root["retry_history"]
    assert spec_monitor.check_invariants(reloaded.state).ok, "執行期 monitor 對缺計數區塊的舊檔不得誤報"

    payload = reloaded.record_gate_result("RELEASE_READY", "FAIL", "CI red")

    assert payload["retry_count"] == 1 and payload["next_state"] == "IMPLEMENTATION"
    assert _disk(reloaded)["retry_history"]["RELEASE_READY"]["current_count"] == 1


def test_returning_to_implementation_leaves_the_implementation_budget_logic_untouched(tmp_path: Path) -> None:
    """交卷前要查的假設：`check-impl` 只看 implementation_budget 計數器，對 RELEASE_READY 沒有任何假設；
    從發布關卡回到 IMPLEMENTATION 後它照常運作（不誤升級、不誤轉態）。"""
    runtime = _runtime(tmp_path)
    runtime.record_gate_result("RELEASE_READY", "FAIL", "CI red")
    payload = runtime.check_implementation_budget()
    assert payload["escalated"] is False and runtime.state.current == "IMPLEMENTATION"


# ───────────────────────────── CLI 層：真子行程、真磁碟 ─────────────────────────────
class _Run:
    def __init__(self, proc: subprocess.CompletedProcess) -> None:
        self.rc, self.stdout, self.stderr = proc.returncode, proc.stdout, proc.stderr


def _cli(state_dir: Path, *argv: str, env_extra: Optional[dict] = None) -> _Run:
    env = {k: v for k, v in os.environ.items() if k not in ("SDD_STATE_DIR", "SDD_PROJECT", "PYTHONPATH")}
    env.update({"SDD_STATE_DIR": str(state_dir), "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(_V_ROOT)})
    env.update(env_extra or {})
    return _Run(subprocess.run([*_CLI, *argv], cwd=str(_V_ROOT), env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=120))


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    path = tmp_path / "proj" / "build" / "reports" / "fsm"
    path.mkdir(parents=True)
    return path


def _cli_state(state_dir: Path, current: str) -> Path:
    path = state_dir / f"FSM-STATE-{sl._sanitize_component(_PROJECT)}.yaml"
    state = sl.load_state(_PROJECT, path=path)
    state.current = current
    sl.save_state(state)
    return path


def _cli_disk(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["fsm_state"]


def test_cli_gate_fail_needs_a_reason_and_a_refused_call_leaves_the_file_byte_identical(state_dir: Path) -> None:
    path = _cli_state(state_dir, "RELEASE_READY")
    before = path.read_bytes()
    for reason_args in ([], ["--reason", ""], ["--reason", "   "]):
        result = _cli(state_dir, "gate", "--project", _PROJECT, "--gate", "RELEASE_READY", "--result", "FAIL",
                      *reason_args)
        assert result.rc == 2 and result.stdout == "", (result.rc, result.stdout, result.stderr)
        assert "--reason" in result.stderr
    assert path.read_bytes() == before


def test_cli_the_whole_bounded_loop_ends_in_an_escalation_that_a_fresh_process_can_read(state_dir: Path) -> None:
    """端到端、每一步都是獨立行程（每一步都重新讀磁碟）：回邊 → 走完 PR／RTM 兩關 → 第二次失敗升級。
    最後用另一個行程 `show` 讀回——修法前這裡讀到的是 RELEASE_READY、計數 1（升級沒落盤）。"""
    path = _cli_state(state_dir, "RELEASE_READY")

    def run(*argv: str) -> str:
        result = _cli(state_dir, *argv, "--project", _PROJECT)
        assert result.rc == 0, (argv, result.stdout, result.stderr)
        return result.stdout

    first = json.loads(run("gate", "--gate", "RELEASE_READY", "--result", "FAIL", "--reason", "root-infra-ci red"))
    assert first["next_state"] == "IMPLEMENTATION" and first["retry_count"] == 1
    run("transition", "--to", "PR_REVIEW", "--reason", "fixed")
    run("gate", "--gate", "PR_REVIEW", "--result", "PASS", "--reason", "SCG-4 PASS")
    run("gate", "--gate", "RTM_VERIFY", "--result", "PASS", "--reason", "SCG-5 PASS")
    assert _cli_disk(path)["current_state"] == "RELEASE_READY"

    second = json.loads(run("gate", "--gate", "RELEASE_READY", "--result", "FAIL", "--reason", "red again"))

    assert second["escalated"] is True and second["next_state"] == "ESCALATION"
    shown = _cli(state_dir, "show", "--project", _PROJECT, "--must-exist")
    disk = json.loads(shown.stdout)["fsm_state"]
    assert disk["current_state"] == "ESCALATION"
    assert disk["retry_history"]["RELEASE_READY"]["current_count"] == 2


def test_cli_gate_pass_at_release_ready_reaches_release(state_dir: Path) -> None:
    path = _cli_state(state_dir, "RELEASE_READY")
    result = _cli(state_dir, "gate", "--project", _PROJECT, "--gate", "RELEASE_READY", "--result", "PASS",
                  "--reason", "SCG-6 PASS")
    assert result.rc == 0, (result.stdout, result.stderr)
    assert json.loads(result.stdout)["next_state"] == "RELEASE"
    assert _cli_disk(path)["current_state"] == "RELEASE"


def test_cli_a_legacy_gate_still_accepts_an_empty_reason(state_dir: Path) -> None:
    """理由必填只屬於 RELEASE_READY：既有驅動腳本的 `gate --gate RTM_VERIFY --result FAIL`（無理由）不得變色。"""
    _cli_state(state_dir, "RTM_VERIFY")
    result = _cli(state_dir, "gate", "--project", _PROJECT, "--gate", "RTM_VERIFY", "--result", "FAIL")
    assert result.rc == 0, (result.stdout, result.stderr)
    assert json.loads(result.stdout)["next_state"] == "IMPLEMENTATION"
