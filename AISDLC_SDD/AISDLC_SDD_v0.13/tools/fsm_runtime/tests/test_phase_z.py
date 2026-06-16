# enforces (governance rules): R-9.18
"""Phase Z / ACT-172 — AUTOCLAUDE_DELEGATED 觀察態落地測試.

驗證 SDD→AutoClaude 委派執行觀測態的 FSM 行為（improving_01 §6 / BRIDGE §5 落地）：
  - 入邊僅自 IMPLEMENTATION（observation 入口慣例：不走 _HAPPY_PATH 出邊，走 enter_*）
  - 出邊 done→IMPLEMENTATION（帶回 resume）/ failed→ESCALATION（升級）
  - 不變量：∈ OBSERVATION_STATES、∉ Terminals、∉ _EMERGENCY_TARGETS（Rule 9.18.4）

WHY：此態是「IMPLEMENTATION 期間委派 AutoClaude playbook 引擎執行」的非阻塞觀測態；
若退化為穩定態或可從任意態進入，將破壞 EventuallyTerminal 有界停機與規格先行邊界。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime
from tools.fsm_runtime.state_loader import load_state, save_state
from tools.fsm_runtime.transition_rules import (
    TransitionError,
    OBSERVATION_STATES,
    _HAPPY_PATH,
    _EMERGENCY_TARGETS,
    is_transition_allowed,
)


def _rt(tmp_path, name, current):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = current
    save_state(st)
    return FSMRuntime(st)


def test_delegated_done_returns_to_implementation(tmp_path):
    rt = _rt(tmp_path, "deleg1", "IMPLEMENTATION")
    res = rt.enter_autoclaude_delegated(playbook_ref="sdd_bridge.yaml")
    assert res["entered"] is True
    assert rt.state.current == "AUTOCLAUDE_DELEGATED"
    # resume_state 必記錄，供 done 帶回
    assert rt.state.root["autoclaude_delegated_tracking"]["resume_state"] == "IMPLEMENTATION"
    rt.exit_autoclaude_delegated("done")
    assert rt.state.current == "IMPLEMENTATION"


def test_delegated_failed_escalates(tmp_path):
    rt = _rt(tmp_path, "deleg2", "IMPLEMENTATION")
    rt.enter_autoclaude_delegated()
    assert rt.state.current == "AUTOCLAUDE_DELEGATED"
    rt.exit_autoclaude_delegated("failed")
    assert rt.state.current == "ESCALATION"


def test_delegated_entry_blocked_from_non_implementation(tmp_path):
    # 觀測態入口邊界：僅 IMPLEMENTATION 可委派；自其他態進入須 fail-fast
    rt = _rt(tmp_path, "deleg3", "SPEC_FROZEN")
    with pytest.raises(TransitionError):
        rt.enter_autoclaude_delegated()


def test_delegated_invalid_decision_raises(tmp_path):
    rt = _rt(tmp_path, "deleg4", "IMPLEMENTATION")
    rt.enter_autoclaude_delegated()
    with pytest.raises(ValueError):
        rt.exit_autoclaude_delegated("maybe")


def test_delegated_reentry_is_noop(tmp_path):
    rt = _rt(tmp_path, "deleg5", "IMPLEMENTATION")
    rt.enter_autoclaude_delegated()
    res = rt.enter_autoclaude_delegated()
    assert res.get("noop") is True
    assert rt.state.current == "AUTOCLAUDE_DELEGATED"


def test_delegated_is_observation_not_terminal_or_emergency():
    assert "AUTOCLAUDE_DELEGATED" in OBSERVATION_STATES
    assert "AUTOCLAUDE_DELEGATED" not in _EMERGENCY_TARGETS
    # 出邊集：done→IMPLEMENTATION / failed→ESCALATION
    assert _HAPPY_PATH["AUTOCLAUDE_DELEGATED"] == {"IMPLEMENTATION", "ESCALATION"}


def test_implementation_outset_excludes_delegated():
    # 觀測態入口慣例：IMPLEMENTATION 的 happy-path 出邊集**不含**本態
    # （入口走 runtime enter_autoclaude_delegated，比照 EVALUATOR_AUDIT/MEMORY_CONSOLIDATION）
    assert "AUTOCLAUDE_DELEGATED" not in _HAPPY_PATH["IMPLEMENTATION"]


def test_delegated_transition_rules_allowed():
    assert is_transition_allowed("AUTOCLAUDE_DELEGATED", "IMPLEMENTATION")
    assert is_transition_allowed("AUTOCLAUDE_DELEGATED", "ESCALATION")
