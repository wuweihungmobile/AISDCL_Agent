"""Phase J / ACT-078 — Spec-Patch Proposer（規格自癒）.

補 L6 最大斷鏈 PJ-3：系統會「診斷」spec 缺陷（steersman_renderer 說「請 sa-analyst
改 AC」），卻從不「草擬」具體 spec diff。本模組在 spec_defect verdict 重複 ≥2 次時
（沿用 pattern_matcher 語意同模式），蒐集反例證據、產出具體 AC before/after diff
草案 docs/01_requirements/SPEC-PATCH-{AC}-{date}.md，出口固定 → HUMAN_PENDING
（人類只 approve/reject diff，維持掌舵者高度）。

嚴格守則：
  - 絕不自動套用 spec patch（Rule 9.22.5 / Rule 8 人工確認）；草案 trust_level=proposed、
    source=spec_defect-auto-generated。
  - 同一 AC 全 session ≤ 2 次（防 patch 抖動，由 FSM enter_spec_patch_proposal 計數）。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .pattern_matcher import is_same_pattern
from .state_loader import REPO_ROOT, _sanitize_component

DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "01_requirements"
MAX_PATCH_PER_AC = 2  # Rule 9.22.5（與 FSM tracking 對齊）


@dataclass
class DefectSignal:
    ac_id: str
    defect_reason: str
    counterexample: str = ""    # 來自 ADVERSARIAL_EVALUATION / SLV / EXECUTION_EVALUATION


@dataclass
class PatchProposal:
    ac_id: str
    before: str
    after: str
    evidence: List[str] = field(default_factory=list)
    trust_level: str = "proposed"               # 絕不 verified（Rule 9.22.5）
    source: str = "spec_defect-auto-generated"
    report_path: Optional[str] = None


def is_repeated_defect(signals: List[DefectSignal], *, min_count: int = 2) -> bool:
    """spec_defect 是否「語意同模式」重複 ≥ min_count 次（沿用 pattern_matcher）。"""
    if len(signals) < min_count:
        return False
    base = signals[0].defect_reason
    same = sum(1 for s in signals if is_same_pattern(base, s.defect_reason))
    return same >= min_count


def _synthesize_after(before: str, signals: List[DefectSignal]) -> str:
    """v1 啟發式：保留原 AC，附上由反例導出的明確化補充子句（供人工 review）。"""
    clarifications = []
    for s in signals:
        detail = s.counterexample or s.defect_reason
        clarifications.append(
            f"- 明確定義反例情境的預期行為：{detail}"
        )
    uniq = list(dict.fromkeys(clarifications))  # 去重保序
    return (
        before.rstrip()
        + "\n\n# 規格補強（proposed，待人工 review）\n"
        + "\n".join(uniq)
    )


def propose(
    ac_id: str,
    before_text: str,
    signals: List[DefectSignal],
    *,
    today: Optional[str] = None,
    out_dir: Optional[Path] = None,
    write: bool = True,
    localization: str = "",
    replay_evidence: str = "",
) -> PatchProposal:
    """產出 SPEC-PATCH 草案（before/after diff + 反例證據三段）。永不自動套用。

    Phase L M-L2 / ACT-092：`replay_evidence` 為離線反事實重放命中率一行
    （counterfactual_replay.ReplayReport.evidence_line()），附掛供人工 approve 時參考
    「此補丁可擋住過去 X/Y 筆同源失敗」——advisory，不改 approve/reject 二元語意（Rule 9.24.4）。
    """
    evidence = [s.counterexample or s.defect_reason for s in signals if (s.counterexample or s.defect_reason)]
    after = _synthesize_after(before_text, signals)
    proposal = PatchProposal(
        ac_id=ac_id,
        before=before_text,
        after=after,
        evidence=evidence,
    )
    if not write:
        return proposal

    target = out_dir or DEFAULT_OUT_DIR
    target.mkdir(parents=True, exist_ok=True)
    date = today or _dt.date.today().isoformat()
    # Path traversal defence: ac_id is externally-controlled (R44
    # cross-platform review fix; see state_loader.py _sanitize_component()).
    path = target / f"SPEC-PATCH-{_sanitize_component(ac_id)}-{date}.md"
    lines = [
        f"# SPEC-PATCH — {ac_id}（{date}）",
        "",
        f"- trust_level: `{proposal.trust_level}`（絕不自動套用，Rule 9.22.5）",
        f"- source: `{proposal.source}`",
        "- 出口：人工 approve → SPEC_DRAFTING 套用；reject → 維持原 AC",
        "",
    ]
    if localization:   # Phase K M-K3 / ACT-086：因果定位（advisory，告訴人類「補哪條 AC」）
        lines += [localization.rstrip(), ""]
    if replay_evidence:   # Phase L M-L2 / ACT-092：離線反事實重放命中率（advisory）
        lines += [
            "## 0. 反事實重放證據（離線，Rule 9.24.4 — advisory，不影響 approve/reject 語意）",
            "",
            f"> {replay_evidence.rstrip()}",
            "",
        ]
    lines += [
        "## 1. 反例證據（來自 ADVERSARIAL_EVALUATION / SLV / EXECUTION_EVALUATION）",
        "",
    ]
    if evidence:
        for e in evidence:
            lines.append(f"- {e}")
    else:
        lines.append("（無附帶反例 — 來自重複 spec_defect verdict 聚合）")
    lines += [
        "",
        "## 2. Before（現行 AC）",
        "",
        "```",
        before_text.rstrip(),
        "```",
        "",
        "## 3. After（建議補強 — proposed diff）",
        "",
        "```",
        after.rstrip(),
        "```",
        "",
        "> 本草案為 advisory；人類維持設計掌舵者高度，只需 approve / reject 一個 diff。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proposal.report_path = str(path)
    return proposal


__all__ = [
    "MAX_PATCH_PER_AC", "DefectSignal", "PatchProposal",
    "is_repeated_defect", "propose",
]
