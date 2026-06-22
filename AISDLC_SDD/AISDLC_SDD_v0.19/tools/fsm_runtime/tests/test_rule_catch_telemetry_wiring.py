# enforces (governance rules): R-9.20
"""W-19-1 / W-19-2 / W-19-3 — 規則命中遙測「catch 側契約」接入 FSM 主迴圈（B 軸 L4→L5 信號）測試。

驗證 improving_19：閉合 DEF-18-001 點名的「catch 側語意未定義」——定義並接入 catch 契約。
catch（捕獲）三要件齊備才 catch_count+1（顯式可歸因，非時序鄰近猜測）：
  ① 規則自描述其守望的 failure_mode（非空）；
  ② 對應攔截事件（ESCALATION / MONITOR_VIOLATION）真實發生；
  ③ 該事件結構化攜帶此 rule_id（呼叫端明確歸因）。
flag-gated（SDD_ENABLE_RULE_CATCH_TELEMETRY 預設 OFF＝零退化）、fail-closed（缺證據不記、
不污染 ROI）、紅線守界（只增 catch_count，退役仍 🔴 人工 set_maturity）。

每個 case 編碼「為何此行為重要」（Rule 9）：flag OFF 零退化、helper 真記（非半接）、
monitor violation 呼叫點真接（R-9.21）、fail-closed 不阻塞、R-9.20 #11 紅線、要件①無
failure_mode 不歸因、寧缺勿濫空歸因不記、helper 子集語意、**持久化陷阱回歸鎖（fire round-trip
不抹 failure_mode）**、stats 覆蓋率誠實揭露。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import rule_loader  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402


def _write_rule(rules_dir: Path, rule_id: str, *, trigger_states, maturity="active",
                failure_mode="", fire_count=0, catch_count=0) -> None:
    """寫一份最小合法 R-*.yaml（含 optional failure_mode），供 catch 隔離測試。"""
    rules_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": rule_id,
        "title": f"synthetic {rule_id}",
        "trigger_states": list(trigger_states),
        "severity": "medium",
        "maturity": maturity,
        "spec": "synthetic test rule",
        "test_ref": "",
    }
    if failure_mode:
        payload["failure_mode"] = failure_mode
    payload["scaffold_roi"] = {
        "fire_count": fire_count, "catch_count": catch_count, "false_positive_count": 0,
    }
    (rules_dir / f"{rule_id}.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


@pytest.fixture
def _catch_rules(tmp_path, monkeypatch):
    """隔離 rules_dir，種 catch 測試規則（不污染 v0.10 凍結 governance）：
      R-9.1  / R-9.21：failure_mode 非空 → 可參與 catch 自動歸因（對應兩呼叫點）；
      R-nofm：trigger MONITOR_VIOLATION 但無 failure_mode → 要件①缺，不得記 catch；
      R-dep ：deprecated（含 failure_mode）→ 已退役，不得記 catch。
    """
    rdir = tmp_path / "rules"
    _write_rule(rdir, "R-9.1", trigger_states=["SCG_VALIDATION"],
                failure_mode="gate retry budget 耗盡 → ESCALATION")
    _write_rule(rdir, "R-9.21", trigger_states=["MONITOR_VIOLATION"],
                failure_mode="monitor invariant 破壞 → ESCALATION")
    _write_rule(rdir, "R-nofm", trigger_states=["MONITOR_VIOLATION"])  # 無 failure_mode
    _write_rule(rdir, "R-dep", trigger_states=["*"], maturity="deprecated",
                failure_mode="x")
    monkeypatch.setattr(rule_loader, "RULES_DIR", rdir)
    return rdir


def _catch_count(rules_dir: Path, rule_id: str) -> int:
    doc = yaml.safe_load((rules_dir / f"{rule_id}.yaml").read_text(encoding="utf-8"))
    return int(doc["scaffold_roi"]["catch_count"])


def _rt_in_init(tmp_path, name="ct19"):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = "INIT"
    save_state(st)
    return FSMRuntime(st)


# ---------- Case 1/2：flag OFF = 零退化（flag 為唯一開關）----------

def test_flag_off_records_no_catch(tmp_path, monkeypatch, _catch_rules):
    """flag OFF + _record_escalation_catches：catch_count 全程 0 = v0.09 行為零退化。"""
    monkeypatch.delenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", raising=False)
    rt = _rt_in_init(tmp_path)
    rt._record_escalation_catches(["R-9.1"])
    assert _catch_count(_catch_rules, "R-9.1") == 0, "flag OFF 不得記 catch（零退化）"


def test_flag_explicit_zero_is_sole_switch(tmp_path, monkeypatch, _catch_rules):
    """flag 顯式 '0' 仍不記 catch：flag 是唯一開關。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "0")
    rt = _rt_in_init(tmp_path)
    rt._record_escalation_catches(["R-9.1"])
    assert _catch_count(_catch_rules, "R-9.1") == 0


# ---------- Case 3：flag ON helper 真記（非半接，閉合 DEF-18-001）----------

def test_flag_on_helper_records_catch_r91(tmp_path, monkeypatch, _catch_rules):
    """flag ON + _record_escalation_catches(['R-9.1'])：R-9.1 catch+1（真記，非 fire_count=0 半接）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt_in_init(tmp_path)
    rt._record_escalation_catches(["R-9.1"])
    assert _catch_count(_catch_rules, "R-9.1") == 1, "歸因 + failure_mode 齊備 → catch+1"


# ---------- Case 4：monitor violation 呼叫點整合（R-9.21 真接）----------

def test_flag_on_monitor_violation_integration_records_r921(tmp_path, monkeypatch, _catch_rules):
    """flag ON + 完整 enter/exit_monitor_violation 路徑 → R-9.21 catch+1（證 escalation 呼叫點真接）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt_in_init(tmp_path)
    rt.enter_monitor_violation(invariant="safety_invariant_x", detail="d")
    rt.exit_monitor_violation(reason="runtime monitor breach")
    assert rt.state.current == "ESCALATION", "monitor violation 出口仍進 ESCALATION"
    assert _catch_count(_catch_rules, "R-9.21") == 1, "R-9.21 守望的失敗模式真實發生 → catch+1"


# ---------- Case 5：fail-closed（catch 記帳失敗不阻塞攔截事件）----------

def test_fail_closed_catch_failure_does_not_raise(tmp_path, monkeypatch, _catch_rules):
    """flag ON + record_state_catches 拋例外 → helper 吞例外不外拋（escalation 不被記帳拖垮）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")

    def _boom(*a, **k):
        raise RuntimeError("synthetic catch telemetry failure")

    monkeypatch.setattr(rule_loader, "record_state_catches", _boom)
    rt = _rt_in_init(tmp_path)
    rt._record_escalation_catches(["R-9.1"])  # 不得拋例外
    assert _catch_count(_catch_rules, "R-9.1") == 0, "記帳失敗 fail-closed：不偽造 catch"


# ---------- Case 6：R-9.20 #11 紅線（catch 路徑永不自動退役）----------

def test_red_line_catch_never_set_maturity(tmp_path, monkeypatch, _catch_rules):
    """flag ON catch 全程零 set_maturity 呼叫：只增計數，退役維持人工 gate（R-9.20 #11）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    calls = []
    real = rule_loader.set_maturity
    monkeypatch.setattr(rule_loader, "set_maturity",
                        lambda *a, **k: (calls.append((a, k)), real(*a, **k))[1])
    rt = _rt_in_init(tmp_path)
    rt._record_escalation_catches(["R-9.1"])
    assert calls == [], "catch 記帳路徑絕不可呼叫 set_maturity（退役須人工）"


# ---------- Case 7：要件①——無 failure_mode 不歸因（fail-closed）----------

def test_no_failure_mode_not_attributed(tmp_path, monkeypatch, _catch_rules):
    """flag ON 對無 failure_mode 的 R-nofm 歸因 → 不記 catch（要件①缺，fail-closed 寧缺勿濫）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt_in_init(tmp_path)
    rt._record_escalation_catches(["R-nofm"])
    assert _catch_count(_catch_rules, "R-nofm") == 0, "無 failure_mode 不參與歸因（防污染 ROI）"


# ---------- Case 8：空 attribution 寧缺勿濫 ----------

def test_empty_attribution_records_nothing(tmp_path, monkeypatch, _catch_rules):
    """flag ON + 空 attribution → 不記任何 catch（DEF-18-001 無證據不映射）。"""
    monkeypatch.setenv("SDD_ENABLE_RULE_CATCH_TELEMETRY", "1")
    rt = _rt_in_init(tmp_path)
    rt._record_escalation_catches([])
    assert rule_loader.record_state_catches([]) == [], "空歸因回空清單、不記"


# ---------- Case 9：record_state_catches 子集語意 + deprecated 不記 ----------

def test_record_state_catches_subset_and_deprecated(tmp_path, monkeypatch, _catch_rules):
    """helper 直測：只對『attributed ∩ failure_mode 非空 ∩ 非 deprecated』子集記 catch。"""
    # 歸因含 R-9.1（記）、R-nofm（無 failure_mode 不記）、R-dep（deprecated 不記）、R-x（不存在）
    caught = rule_loader.record_state_catches(["R-9.1", "R-nofm", "R-dep", "R-x"])
    assert caught == ["R-9.1"], "僅 R-9.1 三要件齊備"
    assert _catch_count(_catch_rules, "R-9.1") == 1
    assert _catch_count(_catch_rules, "R-nofm") == 0
    assert _catch_count(_catch_rules, "R-dep") == 0


# ---------- Case 10：持久化陷阱回歸鎖（fire round-trip 不抹 failure_mode）----------

def test_failure_mode_survives_fire_roundtrip(tmp_path, monkeypatch, _catch_rules):
    """record_state_fires 對 R-9.1 round-trip 重寫 YAML 後，failure_mode **不得被抹掉**。

    鎖住 W-19-1 識別的持久化陷阱：_write_rule 若不條件寫回 failure_mode，fire/catch 記帳會
    悄悄抹掉規則的 failure_mode 欄位 → 該規則此後無法參與 catch 歸因（污染凍結本體）。
    """
    rule_loader.record_state_fires("SCG_VALIDATION")  # 命中 R-9.1，round-trip 重寫
    doc = yaml.safe_load((_catch_rules / "R-9.1.yaml").read_text(encoding="utf-8"))
    assert doc["scaffold_roi"]["fire_count"] == 1, "fire 已記（round-trip 發生）"
    assert doc.get("failure_mode", "").strip(), "failure_mode 不得被 round-trip 抹掉（持久化陷阱）"
    # 反證：無 failure_mode 的規則 round-trip 後仍不應冒出空 failure_mode 欄位（潔淨度）
    rule_loader.record_state_fires("MONITOR_VIOLATION")  # 命中 R-nofm
    doc2 = yaml.safe_load((_catch_rules / "R-nofm.yaml").read_text(encoding="utf-8"))
    assert "failure_mode" not in doc2, "無 failure_mode 規則 round-trip 不得插入空欄位（潔淨度）"


# ---------- Case 11：stats catch_attribution_coverage 誠實揭露 ----------

def test_stats_attribution_coverage(tmp_path, monkeypatch, _catch_rules):
    """rule_fire_telemetry_stats：catch_side_wired=True + coverage 反映有 failure_mode 的規則。"""
    rt = _rt_in_init(tmp_path)
    stats = rt.rule_fire_telemetry_stats()
    cert = stats["safety_certificate"]
    assert cert["catch_side_wired"] is True
    cov = cert["catch_attribution_coverage"]
    # 種子 active 規則中 R-9.1 / R-9.21 有 failure_mode（R-dep deprecated 不入 ladder、
    # R-nofm 無 failure_mode）
    assert set(cov["attributed_rule_ids"]) == {"R-9.1", "R-9.21"}
    assert cov["rules_with_failure_mode"] == 2
    assert "total_catches" in stats, "W-19：頂層揭露 total_catches（與 total_fires 對偶）"
