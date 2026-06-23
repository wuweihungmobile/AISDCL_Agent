"""Phase I M3 / ACT-068 — Value-Driven Goal Planner（價值目標自治）.

落實 SDD_improving_Automation_09.md §5.3 / PI-7：真正的 autonomy 不只是 task
execution，是 goal selection。transition_rules happy-path 入口假設「做哪個 spec」
已由人工給定；系統內唯一 ROI（scaffold_gc 的 catch/fire）衡量的是治理規則價值，
不是 feature 商業價值。

本模組 v1 rule-based 評分 `business_value × confidence / estimated_cost`：
  - cost 復用 path_cost（估算 token 成本）
  - 不確定性復用 ambiguity_scorer（confidence = 1 - ambiguity）
輸出 BACKLOG-RANK-{date}.yaml，**人工 signoff 後才選定**（BACKLOG_PRIORITIZED 閘）。
value model 只排序不裁決，嚴守人類設計舵手 gate（Rule 8）。

冷啟動採保守 default 標 cold_start（仿 Rule 9.19.1）。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# 冷啟動保守 default（樣本/資訊不足時）
COLD_START_COST = 8000           # 對齊 path_cost cold_start（Rule 9.19.1）
COLD_START_CONFIDENCE = 0.5      # 不確定性未知時中性


@dataclass
class BacklogCandidate:
    candidate_id: str
    title: str
    business_value: float = 0.0          # 0~1（人工/PM 給定）
    confidence: float = COLD_START_CONFIDENCE   # 0~1（1 - ambiguity）
    estimated_cost: int = COLD_START_COST       # token 估算（path_cost）
    cold_start: bool = False

    def roi(self) -> float:
        cost = max(1, int(self.estimated_cost))
        return round(self.business_value * self.confidence / cost * 1000, 6)


@dataclass
class RankedBacklog:
    ranked: List[BacklogCandidate] = field(default_factory=list)
    report_path: Optional[str] = None


def rank_candidates(candidates: List[BacklogCandidate]) -> List[BacklogCandidate]:
    """依 ROI 由高到低排序（只排序不裁決）。"""
    return sorted(candidates, key=lambda c: c.roi(), reverse=True)


def write_backlog_rank(
    candidates: List[BacklogCandidate],
    *,
    out_dir: Optional[Path] = None,
    today: Optional[str] = None,
) -> RankedBacklog:
    """產出 BACKLOG-RANK-{date}.yaml（人工 signoff gate 入口）。"""
    ranked = rank_candidates(candidates)
    result = RankedBacklog(ranked=ranked)
    try:
        import yaml  # type: ignore
    except Exception:  # noqa: BLE001
        return result
    if out_dir is None:
        from .state_loader import REPO_ROOT
        out_dir = REPO_ROOT / "build" / "reports" / "orchestrator"
    out_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    path = out_dir / f"BACKLOG-RANK-{date}.yaml"
    doc = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "model": "value_planner v1 rule-based (business_value × confidence / cost)",
        "note": "只排序不裁決；須人工 signoff 後經 BACKLOG_PRIORITIZED 閘選定（Rule 8）",
        "ranked": [
            {
                "candidate_id": c.candidate_id,
                "title": c.title,
                "business_value": c.business_value,
                "confidence": c.confidence,
                "estimated_cost": c.estimated_cost,
                "roi": c.roi(),
                "cold_start": c.cold_start,
            }
            for c in ranked
        ],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tmp.replace(path)
    result.report_path = str(path)
    return result
