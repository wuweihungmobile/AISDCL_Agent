# enforces (governance rules): R-9.20
"""W-17-1 / W-17-2 — 鷹架代謝「自動提議退役」接入主迴圈（B 軸 L4→L5 信號）測試。

驗證 improving_17：把既有 scaffold_gc.run_gc（產 RetirementProposal proposed 提議）接入
enter_scaffold_gc 主迴圈，flag-gated（SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE 預設 OFF＝零退化）、
fail-closed、紅線守界（GC 僅提議，active 規則退役仍 🔴 人工 set_maturity(reviewed_by=)）。

每個 case 編碼「為何此行為重要」（Rule 9）：flag OFF 零退化、L5 自走（不再需手動跑 GC）、
fail-closed 不偽造、R-9.20 #11 紅線 GC 永不自動退役、入口紀律不被 flag 弱化、L5 信號度量穩健。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import rule_loader, scaffold_gc  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime, TransitionError  # noqa: E402
from tools.fsm_runtime.scaffold_gc import RetirementProposal  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402


def _rt_in_release(tmp_path, name="gc17"):
    """建一個處 RELEASE 的 runtime（待測 enter_scaffold_gc）。"""
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = "RELEASE"
    save_state(st)
    rt = FSMRuntime(st)
    assert rt.state.current == "RELEASE"
    return rt


@pytest.fixture
def _redirect_gc_report(tmp_path, monkeypatch):
    """把 SCAFFOLD-ROI 報告落盤導向 tmp，避免污染框架真實 build/reports/gc。"""
    out = tmp_path / "gc_reports"
    monkeypatch.setattr(scaffold_gc, "GC_REPORT_DIR", out)
    return out


# ---------- Case 1/2：flag OFF = 零退化（flag 為唯一開關）----------

def test_flag_off_enter_pure_tracking_no_auto_gc(tmp_path, monkeypatch):
    """flag OFF + enter_scaffold_gc：只記 tracking、無 auto_gc 鍵 = v0.07 行為零退化。"""
    monkeypatch.delenv("SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE", raising=False)
    rt = _rt_in_release(tmp_path)
    result = rt.enter_scaffold_gc(reason="periodic GC")
    assert rt.state.current == "SCAFFOLD_GC"
    assert "auto_gc" not in result, "flag OFF 不得自動跑 GC（零退化）"
    tracking = rt.state.root["scaffold_gc_tracking"]
    assert "roi_report_ref" not in tracking, "flag OFF 不得產報告"


def test_flag_off_explicit_zero_is_sole_switch(tmp_path, monkeypatch):
    """flag 顯式 '0' 仍純記 tracking：flag 是唯一開關。"""
    monkeypatch.setenv("SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE", "0")
    rt = _rt_in_release(tmp_path)
    result = rt.enter_scaffold_gc()
    assert "auto_gc" not in result


# ---------- Case 3：flag ON = L5 自走（不再需手動跑 GC）----------

def test_flag_on_enter_auto_runs_gc_fills_tracking(tmp_path, monkeypatch, _redirect_gc_report):
    """flag ON + enter_scaffold_gc：自動跑 run_gc + 填 report_path/proposals_total = L5 自走。"""
    monkeypatch.setenv("SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE", "1")
    rt = _rt_in_release(tmp_path)
    result = rt.enter_scaffold_gc(reason="periodic GC")
    assert rt.state.current == "SCAFFOLD_GC"
    assert result["auto_gc"]["proposed"] is True
    tracking = rt.state.root["scaffold_gc_tracking"]
    assert tracking["origin"] == "auto"
    assert tracking["roi_report_ref"], "tracking 必須填 roi_report_ref（L5 自走信號）"
    assert "proposals_total" in tracking
    assert "rules_scanned" in tracking


# ---------- Case 4：SCAFFOLD-ROI 報告真實落盤 ----------

def test_flag_on_report_file_actually_written(tmp_path, monkeypatch, _redirect_gc_report):
    """flag ON → SCAFFOLD-ROI-{date}.md 真實落盤 build/reports/gc/（GAP-X2 代謝肌肉收縮）。"""
    monkeypatch.setenv("SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE", "1")
    rt = _rt_in_release(tmp_path)
    result = rt.enter_scaffold_gc()
    report = Path(result["auto_gc"]["report_path"])
    assert report.exists(), "SCAFFOLD-ROI 報告須真實產出（不再是空的 build/reports/gc）"
    assert report.parent == _redirect_gc_report
    assert "Scaffold ROI" in report.read_text(encoding="utf-8")


# ---------- Case 5：fail-closed（run_gc 失敗不阻塞進態、不偽造）----------

def test_run_gc_failure_fail_closed(tmp_path, monkeypatch, _redirect_gc_report):
    """flag ON + run_gc 拋例外 → fail-closed：進態仍成功、auto_gc.proposed=False、不偽造報告。"""
    monkeypatch.setenv("SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE", "1")

    def _boom(*a, **k):
        raise RuntimeError("synthetic GC failure")

    monkeypatch.setattr(scaffold_gc, "run_gc", _boom)
    rt = _rt_in_release(tmp_path)
    result = rt.enter_scaffold_gc()
    assert rt.state.current == "SCAFFOLD_GC", "fail-closed 仍完成既有進態"
    assert result["auto_gc"]["proposed"] is False
    assert "synthetic GC failure" in result["auto_gc"]["error"]
    tracking = rt.state.root["scaffold_gc_tracking"]
    assert tracking.get("roi_report_ref") in (None, ""), "失敗不得寫入假報告路徑"


# ---------- Case 6：R-9.20 #11 紅線（GC 永不自動退役 active 規則）----------

def test_red_line_gc_never_auto_retires(tmp_path, monkeypatch, _redirect_gc_report):
    """flag ON 全程零 set_maturity 呼叫：退役維持人工 gate（R-9.20 #11 不弱化）。"""
    monkeypatch.setenv("SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE", "1")
    calls = []
    real_set_maturity = rule_loader.set_maturity

    def _spy(*a, **k):
        calls.append((a, k))
        return real_set_maturity(*a, **k)

    monkeypatch.setattr(rule_loader, "set_maturity", _spy)
    rt = _rt_in_release(tmp_path)
    rt.enter_scaffold_gc()
    assert calls == [], "GC 自動提議路徑絕不可呼叫 set_maturity（退役須人工）"


# ---------- Case 7：入口紀律不被 flag 弱化 ----------

def test_flag_on_non_release_source_still_raises(tmp_path, monkeypatch):
    """flag ON 不放寬入口：非 RELEASE 源 enter_scaffold_gc 仍 raise（入口紀律不被 flag 弱化）。"""
    monkeypatch.setenv("SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE", "1")
    p = tmp_path / "FSM-STATE-bad.yaml"
    st = load_state("bad", path=p, create_if_missing=True)
    st.root["current_state"] = "IMPLEMENTATION"
    save_state(st)
    rt = FSMRuntime(st)
    with pytest.raises(TransitionError):
        rt.enter_scaffold_gc()


# ---------- Case 8：scaffold_gc_stats 零提議度量穩健 + 升冪 ----------

def test_scaffold_gc_stats_zero_proposals_robust(tmp_path):
    """零提議（真實規則 fire=0）→ 不報錯、roi_ladder 空、safety_certificate 仍輸出。"""
    rt = _rt_in_release(tmp_path)
    stats = rt.scaffold_gc_stats()
    assert stats["proposals_total"] >= 0
    assert isinstance(stats["roi_ladder"], list)
    cert = stats["safety_certificate"]
    assert cert["auto_retire"] is False, "XAI 守界證書：永不自動退役恆真"
    assert "set_maturity" in cert["human_gate"]


def test_scaffold_gc_stats_roi_ladder_ascending(tmp_path, monkeypatch):
    """注入多提議 → roi_ladder 依 ROI 升冪（ROI 最低＝最該退役 critical path）+ by_transition 計數。"""
    fake = [
        RetirementProposal("R-a", "active", "audit-only", roi=0.5, fire_count=10,
                           catch_count=5, rationale="x"),
        RetirementProposal("R-b", "active", "audit-only", roi=0.0, fire_count=20,
                           catch_count=0, rationale="y"),
        RetirementProposal("R-c", "audit-only", "deprecated", roi=0.2, fire_count=5,
                           catch_count=1, rationale="z"),
    ]
    monkeypatch.setattr(scaffold_gc, "compute_proposals", lambda *a, **k: fake)
    rt = _rt_in_release(tmp_path)
    stats = rt.scaffold_gc_stats()
    assert stats["proposals_total"] == 3
    rois = [row["roi"] for row in stats["roi_ladder"]]
    assert rois == sorted(rois), "roi_ladder 須升冪（ROI 最低排最前＝最該退役）"
    assert stats["roi_ladder"][0]["rule_id"] == "R-b", "ROI=0 從不 catch 者排最前"
    assert stats["by_transition"]["active→audit-only"] == 2
    assert stats["by_transition"]["audit-only→deprecated"] == 1
