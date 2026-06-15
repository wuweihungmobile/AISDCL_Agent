"""Phase M M-M2 / ACT-100 — Scaffold Ceiling Detector（淨負天花板鷹架偵測）.

對應藍圖：SDD_improving_Automation_13.md §1.3 / §3.1 ACT-100 / Rule 9.25.5。

`scaffold_gc`（Phase H/J）只退役 **0-fire 死鷹架** 或 **capability_surpassed 被超越** 的
鷹架；它**偵測不到「仍在 fire、未被正式判定超越、卻已成淨負天花板（crutch/ceiling）」**
的鷹架——即鷹架還在動、卻在拖慢/封頂產出（拿掉它反而更好）。這把 Anthropic「大膽移除
鷹架」從「退死鷹架」推到「退淨負鷹架」。

機制：對仍在 fire 的鷹架做 **A/B 影子評估**（隔離 context，WITH vs WITHOUT，用既有
output_quality_scorer 的客觀 OQS 比較）。WITHOUT 顯著優於 WITH（淨負，差 >
SDD_CEILING_DELTA）→ 輸出 CEILING 建議。

🔴 關鍵安全約束（Rule 9.25.5）：本模組**只建議，永不自動退役**——退役仍走
`rule_loader.set_maturity(reviewed_by=...)` 人工 gate。detector 絕不自呼叫 set_maturity。
純離線、可重現、零 LLM（v1 用既有 OQS）。
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .output_quality_scorer import ExecutionObservation, score
from .state_loader import REPO_ROOT

CEILING_REPORT_DIR = REPO_ROOT / "build" / "reports" / "ceiling"

_DEFAULT_CEILING_DELTA = 0.05
_DELTA_CLAMP = (0.01, 0.50)


def ceiling_delta() -> float:
    """讀 SDD_CEILING_DELTA（env 可調），clamp[0.01,0.50]，預設 0.05。

    WITHOUT - WITH 的 OQS 差超過此值才視為「淨負天花板」（避免雜訊誤判）。
    """
    raw = os.environ.get("SDD_CEILING_DELTA")
    if not raw:
        return _DEFAULT_CEILING_DELTA
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_CEILING_DELTA
    lo, hi = _DELTA_CLAMP
    return max(lo, min(hi, val))


@dataclass
class ABSample:
    """單一鷹架的 A/B 影子評估觀測對（皆由 Evaluator 在隔離 context 實跑收集）。"""
    scaffold_id: str
    with_obs: ExecutionObservation       # 帶鷹架跑
    without_obs: ExecutionObservation    # 不帶鷹架跑
    still_firing: bool = True            # 僅對「仍在 fire」的鷹架評估（死/被超越走 scaffold_gc）


@dataclass
class CeilingProposal:
    scaffold_id: str
    with_score: float
    without_score: float
    delta: float                # without - with（>0 = 淨負天花板）
    rationale: str


@dataclass
class CeilingResult:
    proposals: List[CeilingProposal] = field(default_factory=list)
    scanned: int = 0
    delta_threshold: float = _DEFAULT_CEILING_DELTA
    report_path: Optional[str] = None


def detect_ceilings(samples: List[ABSample]) -> CeilingResult:
    """掃 A/B 樣本，回傳淨負天花板鷹架的退役**建議**（不寫入、不自動退役）。

    只評估 still_firing=True 的鷹架（死/被超越的鷹架由 scaffold_gc 既有路徑處理）。
    """
    thr = ceiling_delta()
    proposals: List[CeilingProposal] = []
    scanned = 0
    for s in samples:
        if not s.still_firing:
            continue
        scanned += 1
        ws = score(s.with_obs).score
        wos = score(s.without_obs).score
        delta = round(wos - ws, 4)
        if delta > thr:
            proposals.append(CeilingProposal(
                scaffold_id=s.scaffold_id,
                with_score=ws, without_score=wos, delta=delta,
                rationale=(f"A/B 影子評估：WITHOUT OQS={wos} 顯著優於 WITH OQS={ws}"
                           f"（淨負 Δ={delta} > 閾值 {thr}）— 此鷹架已成天花板/crutch，"
                           f"建議人工退役（set_maturity(reviewed_by=...)）。"),
            ))
    # 依淨負程度排序（最該退的在前）
    proposals.sort(key=lambda p: -p.delta)
    return CeilingResult(proposals=proposals, scanned=scanned, delta_threshold=thr)


def ceiling_markdown(result: CeilingResult) -> str:
    lines = [
        "## 🪜 淨負天花板鷹架偵測（Scaffold Ceiling — advisory，Rule 9.25.5）",
        "",
        f"- A/B 影子評估鷹架數（仍在 fire）：{result.scanned}",
        f"- 淨負閾值 SDD_CEILING_DELTA：{result.delta_threshold}",
        f"- 退役建議數：{len(result.proposals)}",
        "",
    ]
    if result.proposals:
        lines.append("| 鷹架 | WITH OQS | WITHOUT OQS | 淨負 Δ | 理由 |")
        lines.append("|------|----------|-------------|--------|------|")
        for p in result.proposals:
            lines.append(f"| {p.scaffold_id} | {p.with_score} | {p.without_score} | "
                         f"{p.delta} | {p.rationale} |")
    else:
        lines.append("（本次無淨負天花板鷹架——所有仍在 fire 的鷹架皆淨正或中性。）")
    lines += ["",
              "> 🔴 advisory：**只建議，永不自動退役**——退役須人工 set_maturity(reviewed_by=)（Rule 9.25.5）。"]
    return "\n".join(lines) + "\n"


def write_report(result: CeilingResult, *, out_dir: Optional[Path] = None,
                 today: Optional[str] = None) -> Path:
    """落盤 build/reports/ceiling/CEILING-{date}.md。"""
    target_dir = out_dir or CEILING_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    path = target_dir / f"CEILING-{date}.md"
    path.write_text(ceiling_markdown(result), encoding="utf-8")
    result.report_path = str(path)
    return path
