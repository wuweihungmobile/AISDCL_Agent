"""Phase I M3 / ACT-068 — Attention Budget Router（人類注意力預算治理）.

落實 SDD_improving_Automation_09.md §5.3 / PI-7（注意力面）：Phase H 的
steersman_renderer 把**單一事件**交棒做到尊嚴級，但艦隊規模下人類會被獨立 abort
報告淹沒。Rule 9.2 給了 token 一個預算，卻沒給「人類注意力」這個更稀缺的資源任何
預算。當 N 個實例並行 escalate，未分級/批次/去重的告警洪水會把人類從「設計舵手」
沖回「告警分類員」。

attention_router（Rule 9.2 token budget 的對偶）：
  ① severity 分級（復用 diagnostic.category：structural > transient + retry 接近度）
  ② 同 capability_gap/sub_type 去重合併（復用 pattern_matcher.is_same_pattern）
  ③ 批次彙總成單一 DIGEST-{date}.md（top-N by severity，其餘折疊）
  ④ per-window attention budget（每 24h 最多 N 個 P0），超量自動降級非 P0 為 digest-only

硬白名單：P0/structural 永不被 budget 降級或折疊（類比 Rule 9.14.3）。
複用 production_monitor 成熟的 24h rolling-window + 同 key 去重先例。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .pattern_matcher import is_same_pattern

# per-window attention budget（每 24h 最多 N 個 P0 直送人類）
P0_PER_WINDOW = 5


@dataclass
class AttentionEvent:
    event_id: str
    category: str           # "structural" | "transient"（復用 diagnostic.category）
    capability_gap: str     # sub_type / 能力缺口（去重 key）
    summary: str
    ts: str = ""

    @property
    def is_p0(self) -> bool:
        # structural 一律 P0（硬白名單，永不折疊）
        return self.category == "structural"


@dataclass
class AttentionDigest:
    p0_events: List[AttentionEvent] = field(default_factory=list)
    folded: List[AttentionEvent] = field(default_factory=list)   # 被去重/降級折疊者
    dedup_groups: Dict[str, int] = field(default_factory=dict)
    report_path: Optional[str] = None


def _dedup(events: List[AttentionEvent]) -> List[List[AttentionEvent]]:
    """以 capability_gap 語意去重合併（復用 pattern_matcher.is_same_pattern）。"""
    groups: List[List[AttentionEvent]] = []
    for e in events:
        placed = False
        for g in groups:
            if is_same_pattern(g[0].capability_gap, e.capability_gap):
                g.append(e)
                placed = True
                break
        if not placed:
            groups.append([e])
    return groups


def route(
    events: List[AttentionEvent],
    *,
    p0_budget: int = P0_PER_WINDOW,
) -> AttentionDigest:
    """分級 + 去重 + 批次 + budget 降級，回傳 AttentionDigest。

    P0/structural 永不被 budget 降級或折疊（硬白名單）；其餘超量者折疊為 digest-only。
    """
    digest = AttentionDigest()
    groups = _dedup(events)
    for g in groups:
        rep = g[0]
        digest.dedup_groups[rep.capability_gap] = len(g)
        # 同組 P0 仍各自保留（structural 不折疊）；非 P0 同組只留代表
        p0s = [e for e in g if e.is_p0]
        non_p0 = [e for e in g if not e.is_p0]
        digest.p0_events.extend(p0s)
        if non_p0:
            # 非 P0：代表進 digest，其餘折疊
            digest.folded.extend(non_p0[1:])
            # 代表本身也是 digest-only（非 P0 不直送人類）
            digest.folded.append(non_p0[0])

    # per-window budget：P0 超量者降級為 digest-only（但 structural 硬白名單保留）
    if len(digest.p0_events) > p0_budget:
        overflow = digest.p0_events[p0_budget:]
        # structural 永不降級；僅非 structural 的 P0（理論上無，因 P0==structural）才降級
        keep = digest.p0_events[:p0_budget] + [e for e in overflow if e.category == "structural"]
        digest.p0_events = keep
    return digest


def write_digest(
    digest: AttentionDigest,
    *,
    out_dir: Optional[Path] = None,
    today: Optional[str] = None,
) -> str:
    """產出單一 DIGEST-{date}.md（top-N by severity，其餘折疊）。"""
    if out_dir is None:
        from .state_loader import REPO_ROOT
        out_dir = REPO_ROOT / "build" / "reports" / "abort"
    out_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    path = out_dir / f"DIGEST-{date}.md"
    lines = [
        f"# 注意力預算 Digest — {date}（ACT-068）",
        "",
        f"- P0（structural，直送人類）：{len(digest.p0_events)}",
        f"- 折疊（去重 / digest-only）：{len(digest.folded)}",
        f"- 去重群組：{len(digest.dedup_groups)}",
        "",
        "## P0 事件（永不折疊 — 硬白名單）",
        "",
    ]
    if digest.p0_events:
        lines.append("| event_id | capability_gap | summary |")
        lines.append("|----------|----------------|---------|")
        for e in digest.p0_events:
            lines.append(f"| {e.event_id} | {e.capability_gap} | {e.summary} |")
    else:
        lines.append("（無 P0）")
    lines += ["", "## 去重群組（同能力缺口合併）", ""]
    for gap, n in digest.dedup_groups.items():
        lines.append(f"- `{gap}`：{n} 個事件合併")
    lines.append("")
    lines.append("> raw event 全保留為底層 audit；digest 為人類入口（P0/structural 永不被折疊）。")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    digest.report_path = str(path)
    return str(path)
