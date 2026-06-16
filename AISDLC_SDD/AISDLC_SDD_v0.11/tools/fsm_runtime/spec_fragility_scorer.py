"""Phase L M-L3 / ACT-093 — Proactive Spec Fragility Scorer（主動規格脆弱性預測）.

對應藍圖：SDD_improving_Automation_12.md §1.4 / §3.1 ACT-093 / Rule 9.24.5。

`spec_localizer`（Phase K）是**反應式**——訊號進來才回溯該補哪條 AC。本模組是其
**主動式互補**：在訊號發生前，把 RTM(AC↔TC↔FRD↔NFR) + 歷史漂移 + escalation 命中
當「事前風險圖」，對每個 spec 節點算**脆弱性分數**，凍結前就揭露「哪些 AC 最可能成為
下一個 escalation 源」，餵 steersman 熱圖 + intent_decomposer 脆弱依賴標記。

脆弱性 = 加權（blast-radius × 測試覆蓋缺口 × 歷史漂移頻率 × escalation 命中）。
評分強度凍結於 `FRAGILITY_PROFILE_VERSION`，調權重須 bump（Rule 9.24.5，比照
`SCORER_VERSION` / `ADVERSARIAL_PROFILE_VERSION`，防評分器自我放水）。

advisory（Rule 9.24.5）：只標記/建議，**絕不自動改 spec、絕不阻塞 SCG**。純離線、可重現。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from .pattern_matcher import normalize
# 複用 spec_localizer 的 RTM 模型（DRY，避免兩份 RTMRow 漂移）
from .spec_localizer import RTMRow, parse_rtm_markdown  # noqa: F401  (re-export parse_rtm_markdown)
from .state_loader import REPO_ROOT

FRAGILITY_REPORT_DIR = REPO_ROOT / "build" / "reports" / "fragility"

# === 凍結評分強度（Rule 9.24.5：調整須 bump version）===
FRAGILITY_PROFILE_VERSION = "v1.0"
_WEIGHTS: Dict[str, float] = {
    "blast": 0.30,        # blast-radius（改此 AC 影響的鄰域大小）
    "coverage_gap": 0.30, # 測試覆蓋缺口（TC 越少越脆弱）
    "drift": 0.25,        # 歷史漂移頻率（PBS-DRIFT / DRIFT_OBSERVATION 命中次數）
    "escalation": 0.15,   # 歷史 escalation 命中（decision_trace 出現過）
}


@dataclass
class FragilityScore:
    ac_id: str
    score: float
    blast: float
    coverage_gap: float
    drift: float
    escalation: float
    factors: str = ""


@dataclass
class FragilityReport:
    scores: List[FragilityScore] = field(default_factory=list)
    profile_version: str = FRAGILITY_PROFILE_VERSION

    def top(self, k: int = 3) -> List[str]:
        return [s.ac_id for s in self.scores[:k]]


def _blast_size(ac: RTMRow, frd_to_acs: Dict[str, List[str]]) -> int:
    """改此 AC 的一跳鄰域大小：父 FRD + 同 FRD 兄弟 AC + 自身 TC。"""
    n = 0
    if ac.frd_id:
        n += 1                                              # 父 FRD
        n += max(0, len(frd_to_acs.get(ac.frd_id, [])) - 1)  # 兄弟 AC（扣自己）
    n += len(ac.tc_ids)                                     # 自身 TC
    return n


def score_fragility(
    rtm: List[RTMRow],
    *,
    drift_counts: Optional[Dict[str, int]] = None,
    escalation_refs: Optional[Set[str]] = None,
) -> FragilityReport:
    """對每個 AC 算脆弱性分數（ranked desc）。純函式、deterministic、advisory。

    - drift_counts：{ac_id 或 nfr_id → 漂移次數}（來源 PBS-DRIFT / DRIFT_OBSERVATION）
    - escalation_refs：曾出現於 decision_trace escalation 的 spec 節點集合
    """
    drift_counts = drift_counts or {}
    escalation_refs = escalation_refs or set()

    frd_to_acs: Dict[str, List[str]] = {}
    for row in rtm:
        if row.frd_id:
            frd_to_acs.setdefault(row.frd_id, []).append(row.ac_id)

    # 正規化基準
    max_blast = 1
    blast_raw: Dict[str, int] = {}
    for row in rtm:
        b = _blast_size(row, frd_to_acs)
        blast_raw[row.ac_id] = b
        max_blast = max(max_blast, b)
    max_drift = max([1] + list(drift_counts.values()))

    scores: List[FragilityScore] = []
    for row in rtm:
        blast = blast_raw[row.ac_id] / max_blast
        coverage_gap = 1.0 / (1 + len(row.tc_ids))          # 0 TC → 1.0；TC 越多越低
        drift_hits = drift_counts.get(row.ac_id, 0) + drift_counts.get(row.nfr_id, 0)
        drift = drift_hits / max_drift
        escalation = 1.0 if (row.ac_id in escalation_refs or row.frd_id in escalation_refs) else 0.0
        s = (_WEIGHTS["blast"] * blast
             + _WEIGHTS["coverage_gap"] * coverage_gap
             + _WEIGHTS["drift"] * drift
             + _WEIGHTS["escalation"] * escalation)
        factors = (f"blast={blast:.2f} cov_gap={coverage_gap:.2f} "
                   f"drift={drift:.2f} esc={escalation:.0f}")
        scores.append(FragilityScore(
            ac_id=row.ac_id, score=round(s, 4),
            blast=round(blast, 4), coverage_gap=round(coverage_gap, 4),
            drift=round(drift, 4), escalation=escalation, factors=factors,
        ))

    scores.sort(key=lambda x: (-x.score, x.ac_id))
    return FragilityReport(scores=scores)


def fragility_report(report: FragilityReport, *, top_k: int = 5) -> str:
    """產出 markdown 脆弱性熱圖（advisory，餵 steersman；不阻塞 SCG）。"""
    lines = [
        "## 🔥 規格脆弱性熱圖（Proactive Spec Fragility — advisory，Rule 9.24.5）",
        "",
        f"- profile_version：`{report.profile_version}`（凍結；調權重須 bump）",
        f"- 評分 AC 數：{len(report.scores)}（顯示 top {min(top_k, len(report.scores))}）",
        "",
        "| 排名 | AC | 脆弱性 | 因子 |",
        "|------|----|--------|------|",
    ]
    for i, s in enumerate(report.scores[:top_k], 1):
        lines.append(f"| {i} | `{s.ac_id}` | {s.score} | {s.factors} |")
    lines += ["", "> advisory：僅事前風險標記，**絕不自動改 spec、絕不阻塞 SCG**；供舵手凍結前決策。"]
    return "\n".join(lines) + "\n"


def write_report(report: FragilityReport, *, out_dir: Optional[Path] = None,
                 today: Optional[str] = None, top_k: int = 5) -> Path:
    """落盤 build/reports/fragility/FRAGILITY-{date}.md（§2.1 承諾產物，餵 steersman）。

    與 counterfactual_replay.write_report 對稱：advisory 風險熱圖，AI 可推理格式。
    """
    target_dir = out_dir or FRAGILITY_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    path = target_dir / f"FRAGILITY-{date}.md"
    path.write_text(fragility_report(report, top_k=top_k), encoding="utf-8")
    return path


def fragile_node_ids(node_titles: Dict[str, str], fragile_terms: Set[str]) -> List[str]:
    """ACT-094 intent_decomposer 整合：標記分解 DAG 中落在「歷史脆弱領域」的節點。

    分解時 AC 尚未生成，故脆弱性以**領域關鍵詞**對映（`fragile_terms` 由 caller 從
    歷史脆弱來源提供——PBS-DRIFT 報告標題 / 既有脆弱 AC 描述 / decision_trace 證據）。
    回傳 title 與任一脆弱領域 token 有交集的 node_id（advisory，**不改 DAG acyclic 結構**）。
    """
    terms: Set[str] = set()
    for ft in fragile_terms:
        terms |= set(normalize(ft).split())
    flagged: List[str] = []
    for nid, title in node_titles.items():
        if set(normalize(title).split()) & terms:
            flagged.append(nid)
    return flagged
