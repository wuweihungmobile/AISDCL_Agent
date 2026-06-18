"""Phase M M-M3 / ACT-101 — Composition Blast Analyzer（組合級脆弱性）.

對應藍圖：SDD_improving_Automation_13.md §1.4 / §3.1 ACT-101 / Rule 9.25.6。

`spec_fragility_scorer`（Phase L）算的是**單一 AC** 的脆弱性；但在組合層，一個脆弱的
**共享 spec 節點**若被 ≥2 個在飛的意圖同時依賴，它一旦爆炸會**跨意圖串級失敗**——這個
「組合級爆炸半徑乘數」目前無人計算。本模組把單一脆弱性升級為組合脆弱性：

  組合爆炸半徑 = 單一脆弱分數 × 共享意圖數 × 跨意圖耦合度

並據此建議排程器把高組合脆弱度的意圖排**序列**而非並行（降低串級爆炸面），餵 steersman
讓舵手在組合凍結前就看到「哪些共享節點是跨意圖定時炸彈」。

評分強度凍結於 `COMPOSITION_FRAGILITY_PROFILE_VERSION`，調權重須 bump（Rule 9.25.6）。
advisory：只建議排程器/steersman，**絕不自動改 spec、絕不阻塞 SCG**。純離線、可重現。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .intent_composer import CompositionResult, IntentSpec, compose
from .state_loader import REPO_ROOT

COMP_FRAGILITY_REPORT_DIR = REPO_ROOT / "build" / "reports" / "composition-fragility"

# === 凍結評分強度（Rule 9.25.6：調整須 bump version）===
COMPOSITION_FRAGILITY_PROFILE_VERSION = "v1.0"

# 高組合脆弱度門檻（超過則排程器建議序列化）。
_SERIALIZE_THRESHOLD = 1.0


@dataclass
class BlastScore:
    node_id: str
    blast: float                # 組合爆炸半徑乘數
    single_fragility: float     # 單一規格脆弱分數（承 spec_fragility_scorer）
    shared_count: int           # 共享此節點的意圖數
    coupling: float             # 跨意圖耦合度（衝突數 + 1，正規化）
    intents: List[str] = field(default_factory=list)


@dataclass
class BlastReport:
    scores: List[BlastScore] = field(default_factory=list)
    profile_version: str = COMPOSITION_FRAGILITY_PROFILE_VERSION

    def top(self, k: int = 3) -> List[str]:
        return [s.node_id for s in self.scores[:k]]

    def high_blast_nodes(self, *, threshold: float = _SERIALIZE_THRESHOLD) -> List[str]:
        return [s.node_id for s in self.scores if s.blast >= threshold]


def analyze_blast(
    intents: List[IntentSpec],
    *,
    single_fragility: Optional[Dict[str, float]] = None,
    composition: Optional[CompositionResult] = None,
) -> BlastReport:
    """對每個共享 spec 節點算組合爆炸半徑乘數（ranked desc）。純函式、deterministic、advisory。

    - single_fragility：{node_id → 單一脆弱分數 0~1}（來源 spec_fragility_scorer；缺則視 0.5 中性）
    - composition：可選；缺則由 intents 即時 compose（DRY）。
    """
    comp = composition or compose(intents)
    single_fragility = single_fragility or {}
    by_id = {it.intent_id: it for it in intents}
    ordered_ids = [it.intent_id for it in intents]

    # 每個共享節點的衝突數（耦合度基礎）
    conflict_count: Dict[str, int] = {}
    for c in comp.conflicts:
        conflict_count[c.node_id] = conflict_count.get(c.node_id, 0) + 1

    scores: List[BlastScore] = []
    for node in comp.shared_nodes:
        holders = [iid for iid in ordered_ids if node in by_id[iid].node_stances]
        shared_count = len(holders)
        sf = float(single_fragility.get(node, 0.5))
        coupling = 1.0 + conflict_count.get(node, 0)   # 衝突越多耦合越緊
        blast = round(sf * shared_count * coupling, 4)
        scores.append(BlastScore(
            node_id=node, blast=blast, single_fragility=round(sf, 4),
            shared_count=shared_count, coupling=round(coupling, 4), intents=holders,
        ))
    scores.sort(key=lambda x: (-x.blast, x.node_id))
    return BlastReport(scores=scores)


def recommend_schedule(
    intents: List[IntentSpec],
    report: BlastReport,
    *,
    threshold: float = _SERIALIZE_THRESHOLD,
) -> dict:
    """建議排程：共享高組合脆弱節點的意圖排序列，其餘可並行（advisory，不強制）。

    回傳 {"serialize": [[intent_ids 群組...]], "parallel": [intent_ids]}。
    **不改 value_planner ROI 排序、不阻塞**（守 Rule 9.25.6 / planner 不自我裁決）。
    """
    high_nodes = set(report.high_blast_nodes(threshold=threshold))
    by_id = {it.intent_id: it for it in intents}
    serialize_groups: List[List[str]] = []
    serialized: set = set()
    for node in [s.node_id for s in report.scores if s.node_id in high_nodes]:
        group = [iid for iid in (it.intent_id for it in intents)
                 if node in by_id[iid].node_stances]
        if len(group) >= 2:
            serialize_groups.append(group)
            serialized.update(group)
    parallel = [it.intent_id for it in intents if it.intent_id not in serialized]
    return {"serialize": serialize_groups, "parallel": parallel}


def blast_markdown(report: BlastReport, *, top_k: int = 5) -> str:
    """產出 markdown 組合脆弱性熱圖（advisory，餵 steersman；不阻塞 SCG）。"""
    lines = [
        "## 💥 組合級脆弱性熱圖（Composition Blast — advisory，Rule 9.25.6）",
        "",
        f"- profile_version：`{report.profile_version}`（凍結；調權重須 bump）",
        f"- 共享節點數：{len(report.scores)}（顯示 top {min(top_k, len(report.scores))}）",
        "",
        "| 排名 | 共享節點 | 組合爆炸半徑 | 單一脆弱 | 共享意圖數 | 耦合 |",
        "|------|----------|--------------|----------|------------|------|",
    ]
    for i, s in enumerate(report.scores[:top_k], 1):
        lines.append(f"| {i} | `{s.node_id}` | {s.blast} | {s.single_fragility} | "
                     f"{s.shared_count} | {s.coupling} |")
    lines += ["",
              "> advisory：高組合脆弱 → 建議排程器序列化（非並行）；**絕不自動改 spec、絕不阻塞 SCG**。"]
    return "\n".join(lines) + "\n"


def write_report(report: BlastReport, *, out_dir: Optional[Path] = None,
                 today: Optional[str] = None, top_k: int = 5) -> Path:
    """落盤 build/reports/composition-fragility/COMP-FRAGILITY-{date}.md。"""
    target_dir = out_dir or COMP_FRAGILITY_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    path = target_dir / f"COMP-FRAGILITY-{date}.md"
    path.write_text(blast_markdown(report, top_k=top_k), encoding="utf-8")
    return path
