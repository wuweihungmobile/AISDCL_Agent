# enforces (governance rules): R-9.11, R-9.24
"""W-16-1 / W-16-2 — 規則自演化「自動提議」接入主迴圈（B 軸 L4→L5 信號）測試。

驗證 improving_16：把既有 propose_slv_from_fpl（trust_level:proposed 草案）接入
exit_production_behavioral_signal("learn") 主迴圈，flag-gated（SDD_ENABLE_SLV_AUTO_PROPOSE）、
fail-closed、紅線守界（草案恆 proposed，trust_level→verified 仍 🔴 人工）。

improving_59（v0.23，B L4→L5 活體化）：flag 預設由 OFF 翻為 **ON**（unset → 自動提議活體；
顯式 falsy=0/false/no/off → opt-out 還原純轉態）。新增 default-ON 活體驗收 + 紅線恆守（預設
活體下 proposed 仍不自動升 verified）；保留顯式 opt-out 純轉態零退化守。

每個 case 編碼「為何此行為重要」（Rule 9）：default-ON 活體自走、顯式 opt-out 零退化、Block-2
紅線不可自動採納、fail-closed 不偽造、R-9.11 草案恆 proposed、L5 信號度量穩健。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import slv_generator  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402


def _rt_in_pbs(tmp_path, name="pbs16"):
    """建一個已進 PRODUCTION_BEHAVIORAL_SIGNAL 的 runtime（待測 learn 出口）。"""
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = "RELEASE"
    save_state(st)
    rt = FSMRuntime(st)
    rt.enter_production_behavioral_signal()
    assert rt.state.current == "PRODUCTION_BEHAVIORAL_SIGNAL"
    return rt


@pytest.fixture
def _redirect_rules(tmp_path, monkeypatch):
    """把 SLV 草案落盤導向 tmp，避免污染框架真實 rules 目錄。"""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(slv_generator, "RULES_DIR", rules_dir)
    return rules_dir


# ---------- Case 1：default ON（unset）= L5 活體自走（improving_59 翻環）----------

def test_default_on_learn_auto_drafts_proposed_def_59(tmp_path, monkeypatch, _redirect_rules):
    """改寫自 v0.22 Case 1（原斷言 delenv→無 auto_slv）：v0.23 翻環後 unset = 預設 ON。

    為何重要（Rule 9 / R-59-2）：B L4→L5 活體化的**定義性驗收**——env 完全未設（生產常態）時
    learn 出口即自動 draft 一份 proposed 草案，無需人手動跑 CLI。這是「自演化活體常態」相對
    「opt-in 鷹架」的可觀測差異；若預設仍 OFF（翻環失效 / 被回退）此 assert 立即轉紅。
    """
    monkeypatch.delenv("SDD_ENABLE_SLV_AUTO_PROPOSE", raising=False)  # 完全未設 = 預設 ON
    rt = _rt_in_pbs(tmp_path)
    result = rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    assert rt.state.current == "LEARNING_COMMIT"
    assert result["auto_slv"]["proposed"] is True, "v0.23 預設 ON：unset 即自動提議（活體化）"
    assert result["auto_slv"]["trust_level"] == "proposed"
    tracking = rt.state.root["learning_commit_tracking"]
    assert tracking["origin"] == "auto"
    assert Path(tracking["proposed_rule_path"]).exists()


def test_default_on_redline_proposed_never_auto_promotes_def_59(
    tmp_path, monkeypatch, _redirect_rules
):
    """為何重要（Rule 9 / R-59-3 紅線零弱化）：翻預設 ON 後，R-9.11 仍鐵打——env 未設時自動
    draft 的草案恆 trust_level=proposed，未經人工 verify 直接 approve 仍 raise。活體化**不得**
    順帶弱化「proposed 不可自動升 verified」這道人類掌舵紅線。
    """
    monkeypatch.delenv("SDD_ENABLE_SLV_AUTO_PROPOSE", raising=False)  # 預設 ON
    rt = _rt_in_pbs(tmp_path)
    result = rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    assert result["auto_slv"]["trust_level"] == "proposed", "自動草案恆 proposed（R-9.11）"
    with pytest.raises(ValueError):
        rt.exit_learning_commit("approved")  # 未 verify 禁自動採納（紅線守界）


# ---------- Case 2：顯式 opt-out（=0）= 純轉態零退化（保守模式守）----------

def test_explicit_opt_out_is_sole_switch_even_with_fpl(tmp_path, monkeypatch):
    """顯式 opt-out（flag=0）即使帶 fpl_id 仍純轉態：保留保守模式（v0.06 行為）零退化。

    為何重要（Rule 9）：翻預設 ON 後仍須保留「顯式關閉即還原純轉態」的逃生閥；flag=0 是唯一
    停用開關，非靠不傳 fpl_id。"""
    monkeypatch.setenv("SDD_ENABLE_SLV_AUTO_PROPOSE", "0")
    rt = _rt_in_pbs(tmp_path)
    result = rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    assert rt.state.current == "LEARNING_COMMIT"
    assert "auto_slv" not in result, "顯式 opt-out 不得自動提議（保守模式零退化）"


# ---------- Case 3：flag ON = L5 自走（不再需手動 CLI）----------

def test_flag_on_learn_auto_drafts_and_fills_tracking(tmp_path, monkeypatch, _redirect_rules):
    """flag ON + learn + fpl_id：自動 draft proposed 草案 + 填 tracking = L5 自走信號。"""
    monkeypatch.setenv("SDD_ENABLE_SLV_AUTO_PROPOSE", "1")
    rt = _rt_in_pbs(tmp_path)
    result = rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    assert rt.state.current == "LEARNING_COMMIT"
    assert result["auto_slv"]["proposed"] is True
    assert result["auto_slv"]["trust_level"] == "proposed"
    tracking = rt.state.root["learning_commit_tracking"]
    assert tracking["fpl_id"] == "FPL-001"
    assert tracking["proposed_slv_id"] == result["auto_slv"]["slv_id"]
    assert tracking["proposed_rule_path"], "tracking 必須填 proposed_rule_path（修 DEF-16-001）"
    assert tracking["review_status"] == "pending"
    assert tracking["origin"] == "auto"
    assert Path(tracking["proposed_rule_path"]).exists()


# ---------- Case 4：DEF-16-001 鏈閉合（人 verify 後 approve 鏈通）----------

def test_learn_to_approved_chain_closes_after_human_verify(
    tmp_path, monkeypatch, _redirect_rules
):
    """flag ON auto-draft 後，人工升 verified → exit_learning_commit('approved') 鏈通 RELEASE。

    這是 DEF-16-001 的修復驗收：原 learn 路徑不填 tracking 致此鏈 raise。
    並驗 Block-2 守界：approve 前必須有真實 verified YAML（人類掌舵點）。
    """
    monkeypatch.setenv("SDD_ENABLE_SLV_AUTO_PROPOSE", "1")
    rt = _rt_in_pbs(tmp_path)
    rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    rule_path = Path(rt.state.root["learning_commit_tracking"]["proposed_rule_path"])
    # 🔴 人工守界：把 proposed 升為 verified + 記 reviewer（模擬人類審批）
    doc = slv_generator.load_rule(rule_path)
    doc["trust_level"] = "verified"
    doc["reviewed_by"] = "qa-tester-zh"
    doc["reviewed_at"] = "2026-06-15"
    rule_path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    out = rt.exit_learning_commit("approved")
    assert out["to"] == "RELEASE", "人 verify 後 approve 鏈須閉合到 RELEASE"
    assert rt.state.current == "RELEASE"


# ---------- Case 5：Block-2 紅線（proposed 不可自動採納）----------

def test_approve_without_verify_raises(tmp_path, monkeypatch, _redirect_rules):
    """flag ON auto-draft（proposed）後直接 approve 未 verify → raise（R-9.11 守界）。"""
    monkeypatch.setenv("SDD_ENABLE_SLV_AUTO_PROPOSE", "1")
    rt = _rt_in_pbs(tmp_path)
    rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    with pytest.raises(ValueError):
        rt.exit_learning_commit("approved")  # 草案仍 proposed，禁自動採納


# ---------- Case 6：fail-closed（FPL 不存在不偽造）----------

def test_fpl_not_found_fail_closed(tmp_path, monkeypatch, _redirect_rules):
    """flag ON + 未知 FPL → fail-closed：auto_slv proposed=False、停 LEARNING_COMMIT 不偽造。"""
    monkeypatch.setenv("SDD_ENABLE_SLV_AUTO_PROPOSE", "1")
    rt = _rt_in_pbs(tmp_path)
    result = rt.exit_production_behavioral_signal("learn", fpl_id="FPL-999")
    assert rt.state.current == "LEARNING_COMMIT", "fail-closed 仍完成既有轉態"
    assert result["auto_slv"]["proposed"] is False
    assert "error" in result["auto_slv"]
    # 不得偽造 tracking proposal
    tracking = rt.state.root.get("learning_commit_tracking", {})
    assert tracking.get("proposed_rule_path") in (None, ""), "失敗不得寫入假草案路徑"


# ---------- Case 7：合成失敗亦 fail-closed ----------

def test_synthesis_failure_fail_closed(tmp_path, monkeypatch, _redirect_rules):
    """propose_slv_from_fpl 拋例外 → fail-closed（不破壞 FSM、不偽造）。"""
    monkeypatch.setenv("SDD_ENABLE_SLV_AUTO_PROPOSE", "1")

    def _boom(*a, **k):
        raise ValueError("synthetic synth failure")

    monkeypatch.setattr(slv_generator, "propose_slv_from_fpl", _boom)
    rt = _rt_in_pbs(tmp_path)
    result = rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    assert result["auto_slv"]["proposed"] is False
    assert "synthetic synth failure" in result["auto_slv"]["error"]


# ---------- Case 8：learning_loop_stats 零事件度量穩健 ----------

def test_learning_loop_stats_zero_events_no_div_by_zero(tmp_path):
    """零事件 → 不除零，termination_certificate 仍輸出（XAI 良基終止守界恆在）。"""
    p = tmp_path / "FSM-STATE-stats0.yaml"
    st = load_state("stats0", path=p, create_if_missing=True)
    rt = FSMRuntime(st)
    stats = rt.learning_loop_stats()
    assert stats["proposals_total"] == 0
    assert stats["auto_proposed"] == 0
    assert stats["approval_rate"] == 0.0
    assert stats["unattended_proposal_rate"] == 0.0
    cert = stats["termination_certificate"]
    assert cert["well_founded"] is True
    assert isinstance(cert["churn_max"], int) and 1 <= cert["churn_max"] <= 5


# ---------- Case 9：learning_loop_stats 計數 + termination certificate ----------

def test_learning_loop_stats_counts_auto_proposed(tmp_path, monkeypatch, _redirect_rules):
    """auto-draft 後 auto_proposed==1、unattended_proposal_rate 計算、churn_max 與 SSOT 一致。"""
    from tools.fsm_runtime.meta_halt.meta_halt_monitor import churn_max
    monkeypatch.setenv("SDD_ENABLE_SLV_AUTO_PROPOSE", "1")
    rt = _rt_in_pbs(tmp_path)
    rt.exit_production_behavioral_signal("learn", fpl_id="FPL-001")
    stats = rt.learning_loop_stats()
    assert stats["auto_proposed"] == 1
    assert stats["pending"] == 1
    assert stats["unattended_proposal_rate"] == 1.0  # 1 auto / 1 universe
    assert stats["termination_certificate"]["churn_max"] == churn_max()
