"""Phase J / ACT-077 — Competence Envelope / OOD Early-Halt（能力邊界偵測，advisory）.

補 L6 缺口 PJ-2（meta-cognition 面）：系統不知道自己何時操作在「能力封套」之外。
本模組以 pattern_matcher 比對「當前任務描述」vs 既有 FPL/SPL/ADV 語料分佈；相似度
低於 OOD_THRESHOLD → 標記 out_of_competence（advisory），建議 SCG-0 早期 escalation。

關鍵守則（Rule 9.22.4）：advisory-only —— 不自動阻塞 SCG，僅建議；人工確認才升級
（沿用 Rule 9.11.3 proposed/advisory 設計）。不新增 FSM 狀態（做為 gate pre-check，
類比 AmbiguityScorer），降低 FSM 表面積。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from .state_loader import REPO_ROOT


def _tokens(text: str) -> set:
    return {t for t in re.split(r"[^0-9a-z一-鿿]+", (text or "").lower()) if t}


def _vocab_overlap(a: str, b: str) -> float:
    """詞彙重疊度（token Jaccard）。OOD 偵測用詞彙分佈，非字元相似度 —— 避免
    SequenceMatcher 對無關英文字串的字元層噪音（~0.4）誤判 in-distribution。"""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

# 與既有 corpus 的最大相似度低於此值 → 視為 OOD（env 可覆寫，clamp [0,1]）
_DEFAULT_OOD_THRESHOLD = 0.3

_CORPUS_DIRS = (
    REPO_ROOT / "knowledge" / "failure-patterns",
    REPO_ROOT / "knowledge" / "skill-patterns",
    REPO_ROOT / "knowledge" / "adversarial-patterns",
)


def ood_threshold() -> float:
    raw = os.environ.get("SDD_OOD_THRESHOLD")
    if raw is None:
        return _DEFAULT_OOD_THRESHOLD
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return _DEFAULT_OOD_THRESHOLD
    return max(0.0, min(1.0, v))


@dataclass
class CompetenceVerdict:
    out_of_competence: bool
    max_similarity: float
    nearest_ref: Optional[str]
    threshold: float
    advisory: str = ""
    corpus_size: int = 0
    # advisory-only — 永不自動阻塞（Rule 9.22.4）
    blocking: bool = False


def _load_corpus(dirs: Sequence[Path]) -> List[str]:
    """從 FPL/SPL/ADV 語料目錄抽出描述文字（檔名 + 第一段標題），形成分佈樣本。"""
    out: List[str] = []
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            out.append(p.stem.replace("-", " "))
            try:
                head = p.read_text(encoding="utf-8")[:400]
            except Exception:  # noqa: BLE001
                head = ""
            for line in head.splitlines():
                line = line.strip().lstrip("#").strip()
                if line:
                    out.append(line)
                    break
        for p in sorted(d.glob("*.yaml")):
            out.append(p.stem.replace("-", " "))
    return out


def assess(
    task_description: str,
    *,
    corpus: Optional[List[str]] = None,
    threshold: Optional[float] = None,
) -> CompetenceVerdict:
    """評估任務是否落在能力封套外（OOD）。advisory-only。"""
    thr = threshold if threshold is not None else ood_threshold()
    samples = corpus if corpus is not None else _load_corpus(_CORPUS_DIRS)
    if not samples:
        # 無語料基準 → 無法判定 OOD，保守視為 in-distribution（不誤報阻塞）
        return CompetenceVerdict(False, 1.0, None, thr,
                                 advisory="無 FPL/SPL/ADV 語料基準，跳過 OOD 評估",
                                 corpus_size=0)
    best = 0.0
    best_ref: Optional[str] = None
    for s in samples:
        sim = _vocab_overlap(task_description, s)
        if sim > best:
            best, best_ref = sim, s
    is_ood = best < thr
    advisory = (
        f"任務與既有語料最大相似度 {best:.2f} < 門檻 {thr:.2f} —— 疑似能力封套外，"
        f"建議 SCG-0 早期 escalation 由人工確認（advisory，不自動阻塞）。"
        if is_ood else
        f"任務落在能力封套內（最大相似度 {best:.2f} ≥ {thr:.2f}）。"
    )
    return CompetenceVerdict(
        out_of_competence=is_ood,
        max_similarity=round(best, 4),
        nearest_ref=best_ref,
        threshold=thr,
        advisory=advisory,
        corpus_size=len(samples),
    )


__all__ = ["ood_threshold", "CompetenceVerdict", "assess"]
