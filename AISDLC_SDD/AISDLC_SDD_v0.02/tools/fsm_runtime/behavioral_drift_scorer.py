"""Phase I M3 / ACT-067 — Behavioral Drift Scorer（生產功能性偏差量化）.

落實 SDD_improving_Automation_09.md §4.3 / PI-5：production_monitor 的 schema 強制
observed/target/duration_minutes 三個**數值**欄位，使生產現實只能用「P95 超標」這種
數字進閉環；而「API 回傳結構偏離契約」「業務流程順序錯」「業務不變量在生產被違反」
這類**功能性 behavioral 偏差**連 schema 都過不了，直接被 quarantine。

本模組比對生產遙測 vs 凍結 AC/OpenAPI/INV，量化功能性偏差 0~1：
  divergence_kind ∈ {contract_shape, ordering, invariant_violation, missing_branch}
  v1 限 rule-based 結構比對（保確定性零成本，呼應 ambiguity_scorer v1 原則）。

⚠️ 與 drift_monitor.py（commit-time 靜態 code↔spec diff）明確區隔：
   behavioral_drift_scorer 是**生產 runtime 行為 drift**，資料源不同，不可混為一談。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

DIVERGENCE_KINDS = ("contract_shape", "ordering", "invariant_violation", "missing_branch")

# 各 divergence_kind 權重（總和 = 1.0）
_WEIGHTS = {
    "contract_shape": 0.30,
    "ordering": 0.20,
    "invariant_violation": 0.35,   # 業務不變量被違反最嚴重
    "missing_branch": 0.15,
}


@dataclass
class BehavioralObservation:
    """一筆生產 behavioral 觀測（由 observability_query 從 production/*.ndjson 取得）。"""
    ac_id: str = ""
    observed_fields: List[str] = field(default_factory=list)   # 實際回傳欄位
    observed_order: List[str] = field(default_factory=list)    # 實際業務步驟順序
    invariants_violated: List[str] = field(default_factory=list)
    branches_hit: List[str] = field(default_factory=list)


@dataclass
class FrozenContract:
    """凍結的功能性契約（從 AC/OpenAPI/INV 萃取）。"""
    ac_id: str = ""
    required_fields: List[str] = field(default_factory=list)
    expected_order: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    required_branches: List[str] = field(default_factory=list)


@dataclass
class BehavioralDriftResult:
    score: float                      # 0~1，越高偏差越大
    divergences: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, list] = field(default_factory=dict)

    @property
    def diverged(self) -> bool:
        return self.score > 0.0


def score_behavioral_drift(
    obs: BehavioralObservation,
    contract: FrozenContract,
) -> BehavioralDriftResult:
    """量化生產行為 vs 凍結契約的功能性偏差（0~1，rule-based 確定性）。"""
    details: Dict[str, list] = {}

    # contract_shape：回傳結構偏離（缺必填欄位）
    missing_fields = [f for f in contract.required_fields if f not in set(obs.observed_fields)]
    d_shape = _ratio(len(missing_fields), len(contract.required_fields))
    details["contract_shape"] = missing_fields

    # ordering：業務流程順序錯
    d_order = 0.0 if _order_ok(contract.expected_order, obs.observed_order) else 1.0
    if d_order:
        details["ordering"] = [f"expected={contract.expected_order}", f"observed={obs.observed_order}"]

    # invariant_violation：業務不變量在生產被違反
    violated = [i for i in obs.invariants_violated if i in set(contract.invariants)]
    d_inv = _ratio(len(violated), len(contract.invariants))
    details["invariant_violation"] = violated

    # missing_branch：契約要求的分支未被觸及（僅 happy path）
    missing_branches = [b for b in contract.required_branches if b not in set(obs.branches_hit)]
    d_branch = _ratio(len(missing_branches), len(contract.required_branches))
    details["missing_branch"] = missing_branches

    divergences = {
        "contract_shape": round(d_shape, 4),
        "ordering": round(d_order, 4),
        "invariant_violation": round(d_inv, 4),
        "missing_branch": round(d_branch, 4),
    }
    total = round(sum(_WEIGHTS[k] * divergences[k] for k in _WEIGHTS), 4)
    return BehavioralDriftResult(score=total, divergences=divergences, details=details)


def dominant_kind(result: BehavioralDriftResult) -> Optional[str]:
    """回傳偏差最大的 divergence_kind（供 FPL 草案標註）。"""
    if not result.diverged:
        return None
    return max(result.divergences, key=lambda k: result.divergences[k])


def _ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return max(0.0, min(1.0, num / den))


def _order_ok(expected: List[str], observed: List[str]) -> bool:
    """expected 是否為 observed 的子序列（順序保留）。expected 空 → 視為 OK。"""
    if not expected:
        return True
    it = iter(observed)
    return all(step in it for step in expected)
