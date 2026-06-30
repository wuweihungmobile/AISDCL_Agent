# enforces (governance rules): R-9.20, R-9.1, R-9.2, R-9.3, R-9.7, R-9.21, R-9.22, R-SELF-STRIDE
"""W-39 — catch_attribution_coverage 分母正當性透明化（DEF-39-001）測試。

improving_39 B 軌調查確立：catch_attribution_coverage 舊欄位 rules_total（全部非 deprecated
規則=39）**高估了 catch 應接線範圍**。機械分類證實只有 7 條規則具「唯一生產 escalation 落點 +
可結構化歸因 catch」（R-9.1/9.2/9.3/9.7/9.21/9.22/R-SELF-STRIDE）；其餘 32 條由 hook / lint /
arch_fitness / TLC / meta-loop guard / 人工守門，**本質非 FSM-escalation catch-可歸因**——其
catch_count 恆 0 是設計使然、非覆蓋缺口。故 7/39≈18% 為誤導性讀數；escalation-scoped 真實覆蓋
＝7/7＝100%（improving_38 已把全部 escalation-attributable 規則接線完畢，達此機制結構天花板）。

W-39-2 在 rule_fire_telemetry_stats() 純 additive 加 escalation-scoped 分母透明化：
  - 新增 escalation_attributable_rule_ids / _total（正當分母）、escalation_scoped_coverage_pct、
    non_escalation_governed_total、denominator_note；
  - 既有三欄位（rules_with_failure_mode / rules_total / attributed_rule_ids）逐字不變＝零退化。

每個 case 編碼「為何此行為重要」（Rule 9）：
  - 註冊表釘住正當分母＝7（denominator legitimacy 的 SSOT）；
  - escalation_scoped＝100%（天花板達成，不是 82% 未接線缺口）；
  - 舊欄位不變（既有 stats 消費者零退化）；
  - **靜態掃描防漂移**（DEF-05-002/07-001 家族）：註冊表 == 本檔 _record_escalation_catches 實際
    接線之 rule_id 集合，杜絕「未來新增/移除接線但忘了同步註冊表」。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

_FSM_SRC = Path(__file__).resolve().parents[1] / "fsm_runtime.py"
_EXPECTED_SEVEN = frozenset(
    {"R-9.1", "R-9.2", "R-9.3", "R-9.7", "R-9.21", "R-9.22", "R-SELF-STRIDE"}
)


def _stats_cov(tmp_path, name="w39"):
    """以真實凍結 governance 規則 bootstrap，取 catch_attribution_coverage 區段（唯讀）。"""
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    save_state(st)
    rt = FSMRuntime(st)
    return rt.rule_fire_telemetry_stats()["safety_certificate"]["catch_attribution_coverage"]


# ---------- 正當分母 SSOT ----------

def test_escalation_attributable_registry_pins_seven():
    """正當分母＝具唯一生產 escalation 落點、catch-可歸因的 7 條規則（denominator legitimacy）。"""
    assert FSMRuntime._ESCALATION_ATTRIBUTABLE_RULE_IDS == _EXPECTED_SEVEN


def test_real_rules_escalation_scoped_coverage_is_100pct(tmp_path):
    """天花板達成：全部 escalation-attributable 規則皆已接 failure_mode → scoped 覆蓋＝100%，
    非「7/39≈18% 未接線」之誤導讀數。"""
    cov = _stats_cov(tmp_path)
    assert cov["escalation_attributable_total"] == 7
    assert sorted(cov["escalation_attributable_rule_ids"]) == sorted(_EXPECTED_SEVEN)
    assert cov["escalation_scoped_coverage_pct"] == 100.0


def test_non_escalation_governed_breakdown_is_honest(tmp_path):
    """誠實 breakdown：rules_total - escalation_attributable ＝ 非-escalation 守門規則數
    （hook/lint/TLC/meta-loop/人工，catch_count 恆 0 屬設計使然非缺口）。"""
    cov = _stats_cov(tmp_path)
    assert cov["non_escalation_governed_total"] == cov["rules_total"] - cov["escalation_attributable_total"]
    assert cov["non_escalation_governed_total"] == 32  # 39 - 7（v0.17 凍結基線）
    assert "DEF-39-001" in cov["denominator_note"]


# ---------- 零退化：既有三欄位逐字不變 ----------

def test_legacy_coverage_fields_unchanged_zero_regression(tmp_path):
    """既有 stats 消費者依賴的三欄位（rules_with_failure_mode/rules_total/attributed_rule_ids）
    在 W-39 additive 後完全不變＝零退化。"""
    cov = _stats_cov(tmp_path)
    assert cov["rules_with_failure_mode"] == 7
    assert cov["rules_total"] == 39
    assert sorted(cov["attributed_rule_ids"]) == sorted(_EXPECTED_SEVEN)


def test_numerator_subset_of_legitimate_denominator(tmp_path):
    """數值一致性：已接 failure_mode 的規則（catch 接線）必為正當分母子集——
    不可能有「接了 catch 卻無 escalation 落點」的規則（DEF-18-001 寧缺勿濫）。"""
    cov = _stats_cov(tmp_path)
    assert set(cov["attributed_rule_ids"]) <= set(cov["escalation_attributable_rule_ids"])


# ---------- 靜態掃描防漂移（DEF-05-002/07-001 家族）----------

def test_registry_matches_wired_calls_no_drift():
    """SSOT 防漂移：_ESCALATION_ATTRIBUTABLE_RULE_IDS 必精確等於本檔 _record_escalation_catches(...)
    呼叫點實際歸因的 rule_id 集合。未來新增/移除 catch 接線而忘了同步註冊表 → 本 case 立即轉紅。
    （排除註冊表常數定義自身的字串字面，只掃 _record_escalation_catches([...]) 呼叫。）"""
    src = _FSM_SRC.read_text(encoding="utf-8")
    wired = set()
    for m in re.finditer(r"_record_escalation_catches\(\s*\[([^\]]*)\]", src):
        wired.update(re.findall(r'"([^"]+)"', m.group(1)))
    assert wired == _EXPECTED_SEVEN, (
        f"接線集合 {sorted(wired)} 與註冊表 {sorted(_EXPECTED_SEVEN)} 漂移；"
        "新增/移除 escalation catch 接線時須同步 _ESCALATION_ATTRIBUTABLE_RULE_IDS"
    )
