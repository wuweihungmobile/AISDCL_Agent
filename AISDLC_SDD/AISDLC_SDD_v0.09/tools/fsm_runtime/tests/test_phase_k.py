# enforces (governance rules): R-9.23
"""Phase K（SDD_improving_Automation_11）測試套件 — ACT-082 FSM 整合.

INTENT_DECOMPOSITION（意圖分解 gatekeep）入口/出口/有界/三源契約。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime
from tools.fsm_runtime.state_loader import load_state, save_state
from tools.fsm_runtime.transition_rules import (
    OBSERVATION_STATES, _HAPPY_PATH, TransitionError,
)


def _rt(tmp_path: Path, name: str, src: str) -> FSMRuntime:
    state_path = tmp_path / f"FSM-STATE-{name}.yaml"
    state = load_state(name, path=state_path, create_if_missing=True)
    state.root["current_state"] = src
    save_state(state)
    return FSMRuntime(state)


# ---------- 入口契約 ----------

def test_enter_from_agent_load(tmp_path):
    rt = _rt(tmp_path, "ok", "AGENT_LOAD")
    res = rt.enter_intent_decomposition(max_nodes=32)
    assert res["entered"] is True
    assert rt.state.current == "INTENT_DECOMPOSITION"


def test_enter_from_illegal_source_rejected(tmp_path):
    rt = _rt(tmp_path, "bad", "SPEC_DRAFTING")
    with pytest.raises(TransitionError):
        rt.enter_intent_decomposition()


def test_enter_idempotent_noop(tmp_path):
    rt = _rt(tmp_path, "noop", "AGENT_LOAD")
    rt.enter_intent_decomposition()
    res = rt.enter_intent_decomposition()
    assert res.get("noop") is True
    assert rt.state.current == "INTENT_DECOMPOSITION"


def test_enter_records_tracking(tmp_path):
    rt = _rt(tmp_path, "trk", "AGENT_LOAD")
    rt.enter_intent_decomposition(max_nodes=16)
    trk = rt.state.root["intent_decomposition_tracking"]
    assert trk["max_nodes"] == 16
    assert "entered_at" in trk


# ---------- 出口契約 ----------

def test_exit_decomposed_to_backlog(tmp_path):
    rt = _rt(tmp_path, "dec", "AGENT_LOAD")
    rt.enter_intent_decomposition()
    res = rt.exit_intent_decomposition("decomposed")
    assert res["to"] == "BACKLOG_PRIORITIZED"
    assert rt.state.current == "BACKLOG_PRIORITIZED"


def test_exit_underspecified_to_human_pending(tmp_path):
    rt = _rt(tmp_path, "und", "AGENT_LOAD")
    rt.enter_intent_decomposition()
    res = rt.exit_intent_decomposition("underspecified")
    assert res["to"] == "HUMAN_PENDING"
    assert rt.state.current == "HUMAN_PENDING"


def test_exit_invalid_outcome_raises(tmp_path):
    rt = _rt(tmp_path, "inv", "AGENT_LOAD")
    rt.enter_intent_decomposition()
    with pytest.raises(ValueError):
        rt.exit_intent_decomposition("maybe")


def test_exit_when_not_in_state_raises(tmp_path):
    rt = _rt(tmp_path, "ns", "AGENT_LOAD")
    with pytest.raises(TransitionError):
        rt.exit_intent_decomposition("decomposed")


# ---------- 三源 / 結構契約 ----------

def test_intent_decomposition_is_gatekeep_not_observation():
    assert "INTENT_DECOMPOSITION" not in OBSERVATION_STATES


def test_happy_path_agent_load_includes_intent():
    assert "INTENT_DECOMPOSITION" in _HAPPY_PATH["AGENT_LOAD"]


def test_happy_path_intent_targets():
    assert _HAPPY_PATH["INTENT_DECOMPOSITION"] == {"BACKLOG_PRIORITIZED", "HUMAN_PENDING"}


def test_backward_compat_agent_load_edges_preserved():
    # ACT-068 既有邊不得被破壞（加法式新增）
    assert {"SPEC_DRAFTING", "BACKLOG_PRIORITIZED"} <= _HAPPY_PATH["AGENT_LOAD"]


# ---------- ACT-084: SPEC_DEBATE observation 整合 ----------

def test_spec_debate_enter_from_scg_validation(tmp_path):
    rt = _rt(tmp_path, "sd-ok", "SCG_VALIDATION")
    res = rt.enter_spec_debate(ac_id="AC-014")
    assert res["entered"] is True
    assert rt.state.current == "SPEC_DEBATE"


def test_spec_debate_enter_illegal_source(tmp_path):
    rt = _rt(tmp_path, "sd-bad", "IMPLEMENTATION")
    with pytest.raises(TransitionError):
        rt.enter_spec_debate()


def test_spec_debate_exit_consensus_to_scg(tmp_path):
    rt = _rt(tmp_path, "sd-con", "SCG_VALIDATION")
    rt.enter_spec_debate()
    res = rt.exit_spec_debate("consensus")
    assert res["to"] == "SCG_VALIDATION"
    assert rt.state.current == "SCG_VALIDATION"


def test_spec_debate_exit_divergence_to_human(tmp_path):
    rt = _rt(tmp_path, "sd-div", "SCG_VALIDATION")
    rt.enter_spec_debate()
    res = rt.exit_spec_debate("divergence")
    assert res["to"] == "HUMAN_PENDING"
    assert rt.state.current == "HUMAN_PENDING"


def test_spec_debate_exit_invalid_raises(tmp_path):
    rt = _rt(tmp_path, "sd-inv", "SCG_VALIDATION")
    rt.enter_spec_debate()
    with pytest.raises(ValueError):
        rt.exit_spec_debate("maybe")


def test_spec_debate_divergence_persists_disambiguation(tmp_path, monkeypatch):
    import yaml
    from tools.fsm_runtime import spec_debate as SD
    monkeypatch.setattr(SD, "DISAMBIG_DIR", tmp_path / "disambiguation")
    rt = _rt(tmp_path, "sd-persist", "SCG_VALIDATION")
    rt.enter_spec_debate(ac_id="AC-014")
    res = rt.exit_spec_debate(
        "divergence", interp_a="同時疊加套用", interp_b="互斥僅取其一",
        divergence=0.82, markers=["可疊加"],
    )
    assert res["to"] == "HUMAN_PENDING"
    assert "disambiguation" in res
    path = Path(res["disambiguation"])
    assert path.exists()
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert doc["ac_id"] == "AC-014"
    assert doc["maturity"] == "proposed"   # 禁自動 verified（Rule 9.23.4/9.23.5）
    assert doc["verdict"] is None          # 待人工裁決


def test_spec_debate_consensus_no_persist(tmp_path, monkeypatch):
    from tools.fsm_runtime import spec_debate as SD
    monkeypatch.setattr(SD, "DISAMBIG_DIR", tmp_path / "disambiguation")
    rt = _rt(tmp_path, "sd-nopersist", "SCG_VALIDATION")
    rt.enter_spec_debate(ac_id="AC-014")
    res = rt.exit_spec_debate("consensus")
    assert "disambiguation" not in res     # consensus 不落盤
    assert not (tmp_path / "disambiguation").exists()


def test_spec_debate_is_observation():
    assert "SPEC_DEBATE" in OBSERVATION_STATES


def test_spec_debate_happy_path_targets():
    assert _HAPPY_PATH["SPEC_DEBATE"] == {"SCG_VALIDATION", "HUMAN_PENDING"}


def test_spec_debate_tracking_recorded(tmp_path):
    rt = _rt(tmp_path, "sd-trk", "SCG_VALIDATION")
    rt.enter_spec_debate(ac_id="AC-9", rounds=5)
    trk = rt.state.root["spec_debate_tracking"]
    assert trk["ac_id"] == "AC-9"
    assert trk["rounds"] == 5
    assert trk["resume_state"] == "SCG_VALIDATION"
