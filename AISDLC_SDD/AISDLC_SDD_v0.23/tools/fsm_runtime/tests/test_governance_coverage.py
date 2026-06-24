# enforces (governance rules): R-9.20, R-9.1, R-9.2, R-9.3, R-9.7, R-9.21, R-9.22, R-SELF-STRIDE
"""W-54（improving_55 / DEF-54-001 + DEF-19-001 後續標的）— 守門機制覆蓋度量測試。

improving_54 設計探索拍板：DEF-19-001 收尾後，FSM-escalation catch 達結構天花板 7/7=100%，
但其餘 32 條（hook/lint_tlc/meta_loop/manual）守門覆蓋零度量。本輪（improving_55）：

  W-54-1：把 W-39-1 五分類**機讀化**——每條 active R-*.yaml 加 enforcement_mechanism 欄
          （escalation|hook|lint_tlc|meta_loop|manual），並與既有 _ESCALATION_ATTRIBUTABLE_RULE_IDS
          **交叉鎖**（兩 SSOT 不得漂移）。修復 DEF-54-001（分類原僅存 archive 散文）。
  W-54-2：comprehensive_governance_coverage() 誠實證書——把「覆蓋」從**不可能的**『守門 runtime
          是否有效』重構為『守門機制是否真實分類 + (escalation 類) catch 是否接線』靜態-結構度量；
          manual 類**誠實排除於自動分母**、hook/lint_tlc/meta_loop runtime 度量標 deferred（justified）。

每個 case 編碼「為何此行為重要」（Rule 9）：分類完整＝無守門盲區；交叉鎖＝兩 SSOT 不漂移；
round-trip 保欄＝持久化不靜默遺失分類（避免 scaffold_roi 寫回時丟欄）；manual 誠實排除＝不灌假
覆蓋率（DEF-18-001 寧缺勿濫家族）；deferred 標記＝不偽裝 runtime 有效性。
"""
from __future__ import annotations

import sys
from pathlib import Path

from tools.fsm_runtime import rule_loader  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

_EXPECTED_ESCALATION = frozenset(
    {"R-9.1", "R-9.2", "R-9.3", "R-9.7", "R-9.21", "R-9.22", "R-SELF-STRIDE"}
)
# W-39-1 權威五分類計數（taxonomy 回歸鎖；新增規則須有意識分類，否則本 case 轉紅）
_EXPECTED_COUNTS = {
    "escalation": 7, "hook": 3, "lint_tlc": 3, "meta_loop": 14, "manual": 12,
}


def _active_rules():
    return [r for r in rule_loader.load_all() if r.maturity != "deprecated"]


def _coverage(tmp_path, name="w54"):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    save_state(st)
    return FSMRuntime(st).comprehensive_governance_coverage()


# ---------- W-54-1：分類完整性（fail-closed，無守門盲區）----------

def test_every_active_rule_is_classified():
    """每條 active 規則必有合法 enforcement_mechanism——未分類＝守門覆蓋盲區（fail-closed）。"""
    valid = FSMRuntime._ENFORCEMENT_MECHANISMS
    unclassified = [r.id for r in _active_rules() if r.enforcement_mechanism not in valid]
    assert unclassified == [], f"未分類/非法 enforcement_mechanism：{unclassified}"


def test_mechanism_distribution_matches_w39_taxonomy():
    """五分類分布鎖定 W-39-1 權威計數（7/3/3/14/12=39）；新增規則改變分布即轉紅，
    強制有意識分類（taxonomy 回歸鎖，DEF-54-001 機讀化的守護）。"""
    dist: dict = {}
    for r in _active_rules():
        dist[r.enforcement_mechanism] = dist.get(r.enforcement_mechanism, 0) + 1
    assert dist == _EXPECTED_COUNTS


# ---------- W-54-1：交叉鎖（兩 SSOT 不漂移）----------

def test_escalation_class_cross_locks_with_attributable_ssot():
    """yaml 中 enforcement_mechanism==escalation 的集合，必精確等於 fsm_runtime 既有
    _ESCALATION_ATTRIBUTABLE_RULE_IDS 常數。兩 SSOT 漂移（任一側改而忘了同步另一側）→ 轉紅。
    這是 W-54-1 把新分類錨定到既有 catch-attribution 真相源、防分裂的核心不變量。"""
    yaml_escalation = {r.id for r in _active_rules() if r.enforcement_mechanism == "escalation"}
    assert yaml_escalation == set(FSMRuntime._ESCALATION_ATTRIBUTABLE_RULE_IDS)
    assert yaml_escalation == set(_EXPECTED_ESCALATION)


# ---------- W-54-1：持久化 round-trip 保欄（避免靜默遺失分類）----------

def test_enforcement_mechanism_survives_write_roundtrip(tmp_path):
    """record_fire（→_write_rule）持久化 scaffold_roi 後，enforcement_mechanism 必須保留。
    若 _write_rule payload 漏帶此欄，首次記帳即靜默丟分類 → 守門證書失真。本 case 鎖死該 round-trip。"""
    rdir = tmp_path / "rules"
    rdir.mkdir()
    src = next(p for p in (rule_loader.RULES_DIR).glob("R-9.6-*.yaml"))  # hook 類，無 failure_mode
    dst = rdir / src.name
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    before = rule_loader._load_rule_file(dst)
    assert before.enforcement_mechanism == "hook"
    rule_loader.record_fire("R-9.6", caught=False, rules_dir=rdir)  # 觸發 _write_rule
    after = rule_loader._load_rule_file(dst)
    assert after.enforcement_mechanism == "hook", "round-trip 後 enforcement_mechanism 遺失（payload 漏帶）"
    assert after.scaffold_roi["fire_count"] == before.scaffold_roi["fire_count"] + 1  # 確實有寫回


# ---------- W-54-2：誠實覆蓋證書 ----------

def test_certificate_totals_and_partition(tmp_path):
    """證書涵蓋全部 active 規則、by_mechanism 分區加總==total、無 unclassified（fail-closed）。"""
    cov = _coverage(tmp_path)
    assert cov["total_active_rules"] == 39
    assert sum(v["count"] for v in cov["by_mechanism"].values()) == 39
    assert cov["unclassified_rule_ids"] == []
    assert {m: v["count"] for m, v in cov["by_mechanism"].items()} == _EXPECTED_COUNTS


def test_escalation_coverage_reuses_catch_attribution(tmp_path):
    """escalation 類覆蓋沿用既有 catch-attribution：wired ⊆ escalation SSOT、達天花板 100%。
    證實 W-54-2 未重複造輪、與 W-39 既有度量一致（不雙重計數、不誤報）。"""
    cov = _coverage(tmp_path)
    ec = cov["escalation_coverage"]
    assert ec["denominator"] == 7
    assert set(ec["wired_rule_ids"]) <= set(_EXPECTED_ESCALATION)
    assert ec["coverage_pct"] == 100.0


def test_manual_class_honestly_excluded_not_faked(tmp_path):
    """manual（人工/憲法）類**誠實排除於自動分母**——標在 non_auto_measurable、不在 auto_measurable，
    denominator_note 明示重構語意。杜絕為衝覆蓋率對人工規則灌假數字（DEF-18-001 寧缺勿濫家族）。"""
    cov = _coverage(tmp_path)
    assert "manual" in cov["non_auto_measurable_mechanisms"]
    assert "manual" not in cov["auto_measurable_mechanisms"]
    assert "誠實排除" in cov["denominator_note"]


def test_deferred_runtime_mechanisms_marked_not_faked(tmp_path):
    """hook/lint_tlc/meta_loop 標 deferred（justified：無消費者 + Rule 2 + meta_loop 恐觸 TLC），
    分類在位但**不偽裝 runtime 有效性度量**。誠實揭露「尚未量」而非假綠。"""
    cov = _coverage(tmp_path)
    assert set(cov["deferred_runtime_mechanisms"]) == {"hook", "lint_tlc", "meta_loop"}
    assert "escalation" in cov["auto_measurable_mechanisms"]
