"""ambiguity_scorer.py — Phase G M3 / ACT-037 AmbiguityScorer

Rule-based 6-dimension ambiguity scorer for FRD AC sentences.
Outputs a score in [0, 1]. SCG-0 阻擋 score >= 0.4 (Rule 9.16.2).

Public surface:
    SCORER_VERSION              — bump invalidates all caches (Rule 9.16.4)
    AmbiguityScore              — dataclass with score + dim breakdown
    score_ac(text) -> AmbiguityScore
    score_frd(frd_path)         — batch with caching
    invalidate_cache(version=None)

Cache layout: build/cache/ambiguity/{SCORER_VERSION}/{frd_sha256}.json
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SCORER_VERSION = "v1.0"

# ─────────────────────────────────────────────────────────────
# Dictionaries (see AMBIGUITY-SCORER-SPEC.md §2)
# ─────────────────────────────────────────────────────────────

_QUANTIFIER_TERMS = (
    # zh
    "快速", "緩慢", "適當", "適度", "適合", "盡可能", "盡量", "足夠",
    "少量", "大量", "大部分", "一些", "若干",
    # en
    "fast", "slow", "appropriate", "reasonable", "sufficient", "adequate",
    "many", "few", "some", "several", "mostly", "partial",
)

_PASSIVE_PATTERNS = [
    re.compile(r"應(被|要被|將被|可被)[一-鿿\w]+"),
    re.compile(r"被[一-鿿\w]+(?=$|，|。|；)"),
    re.compile(r"\b(is|are|shall be|will be|may be|can be)\s+\w+ed\b", re.IGNORECASE),
]

_NFR_KEYWORDS = (
    # zh
    "效能", "延遲", "吞吐", "容量", "可用性", "響應時間", "回應時間",
    # en
    "performance", "latency", "throughput", "capacity", "availability",
    "response time", "rto", "rpo",
)

_NUMBER_UNIT_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ms|s|sec|min|h|hr|req|qps|rps|mb|gb|tb|%|百分|秒|分鐘|小時)",
    re.IGNORECASE,
)

_NEGATIVE_CONDITION_PATTERNS = [
    re.compile(r"(若|如果|當|除非|否則|在.*情況下|在.*條件下)"),
    re.compile(r"\b(if|when|unless|otherwise|in case)\b", re.IGNORECASE),
]

_UI_API_KEYWORDS = (
    "ui", "畫面", "頁面", "按鈕", "endpoint", "api", "request", "response",
    "form", "表單", "對話框", "modal",
)
_ANCHOR_PATTERN = re.compile(r"<!--\s*anchor:[\w-]+:[\w-]+\s*-->")

_AMBIGUOUS_REFERENCES = (
    "如同", "類似", "相應", "相關", "對應", "匹配",
    "similar to", "corresponding", "related", "matching", "alike",
)

# ─────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────


@dataclass
class DimensionScores:
    d1_quantifier: float = 0.0
    d2_passive: float = 0.0
    d3_no_number: float = 0.0
    d4_no_negative: float = 0.0
    d5_no_anchor: float = 0.0
    d6_ambiguous_ref: float = 0.0

    def total(self) -> float:
        raw = (
            self.d1_quantifier + self.d2_passive + self.d3_no_number
            + self.d4_no_negative + self.d5_no_anchor + self.d6_ambiguous_ref
        )
        return round(min(raw, 1.0), 2)


@dataclass
class AmbiguityScore:
    text: str
    score: float
    dimensions: DimensionScores = field(default_factory=DimensionScores)
    triggered: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "score": round(self.score, 4),
            "dimensions": {k: round(v, 4) for k, v in asdict(self.dimensions).items()},
            "triggered": self.triggered,
        }


# ─────────────────────────────────────────────────────────────
# Per-dimension evaluators
# ─────────────────────────────────────────────────────────────


def _eval_d1(text: str) -> float:
    lowered = text.lower()
    hits = sum(1 for term in _QUANTIFIER_TERMS if term.lower() in lowered)
    if hits == 0:
        return 0.0
    if hits == 1:
        return 0.10
    return 0.25


def _eval_d2(text: str) -> float:
    sentences = [s for s in re.split(r"[。；;.\n]", text) if s.strip()]
    if not sentences:
        return 0.0
    passive_hits = sum(
        1 for s in sentences
        if any(p.search(s) for p in _PASSIVE_PATTERNS)
    )
    return min(0.20 * (passive_hits / len(sentences)), 0.20)


def _eval_d3(text: str) -> float:
    lowered = text.lower()
    if not any(kw in lowered for kw in _NFR_KEYWORDS):
        return 0.0
    if _NUMBER_UNIT_PATTERN.search(text):
        return 0.0
    return 0.20


def _eval_d4(text: str) -> float:
    if any(p.search(text) for p in _NEGATIVE_CONDITION_PATTERNS):
        return 0.0
    return 0.15


def _eval_d5(text: str) -> float:
    lowered = text.lower()
    if not any(kw in lowered for kw in _UI_API_KEYWORDS):
        return 0.0
    if _ANCHOR_PATTERN.search(text):
        return 0.0
    return 0.10


def _eval_d6(text: str) -> float:
    lowered = text.lower()
    hits = sum(1 for term in _AMBIGUOUS_REFERENCES if term.lower() in lowered)
    if hits == 0:
        return 0.0
    if hits == 1:
        return 0.05
    return 0.10


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────


def score_ac(text: str) -> AmbiguityScore:
    """Compute ambiguity score for a single AC text."""
    if not text or not text.strip():
        return AmbiguityScore(text=text, score=0.0)
    dims = DimensionScores(
        d1_quantifier=_eval_d1(text),
        d2_passive=_eval_d2(text),
        d3_no_number=_eval_d3(text),
        d4_no_negative=_eval_d4(text),
        d5_no_anchor=_eval_d5(text),
        d6_ambiguous_ref=_eval_d6(text),
    )
    triggered = [k for k, v in asdict(dims).items() if v > 0]
    return AmbiguityScore(text=text, score=dims.total(), dimensions=dims, triggered=triggered)


_AC_PATTERN = re.compile(
    r"(?:^|\n)#{2,4}\s*(AC-[\w\-]+)[^\n]*\n(.*?)(?=\n#{2,4}\s*(?:AC-|F-|US-)|\Z)",
    re.DOTALL,
)


def _extract_acs(frd_text: str) -> Dict[str, str]:
    """Extract AC blocks by ID. Returns {AC-ID: text}."""
    out: Dict[str, str] = {}
    for m in _AC_PATTERN.finditer(frd_text):
        ac_id = m.group(1)
        body = m.group(2).strip()
        out[ac_id] = body
    return out


def _frd_sha(frd_path: Path) -> str:
    return hashlib.sha256(frd_path.read_bytes()).hexdigest()[:16]


def _cache_path(repo_root: Path, frd_sha: str) -> Path:
    return repo_root / "build" / "cache" / "ambiguity" / SCORER_VERSION / f"{frd_sha}.json"


def score_frd(
    frd_path: Path | str,
    *,
    repo_root: Optional[Path] = None,
    use_cache: bool = True,
) -> Dict[str, AmbiguityScore]:
    """Batch score all ACs in an FRD, with cache."""
    frd_path = Path(frd_path)
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    sha = _frd_sha(frd_path)
    cache_file = _cache_path(repo_root, sha)
    if use_cache and cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("scorer_version") == SCORER_VERSION:
                return {
                    ac_id: AmbiguityScore(
                        text=entry["text"],
                        score=entry["score"],
                        dimensions=DimensionScores(**entry["dimensions"]),
                        triggered=entry["triggered"],
                    )
                    for ac_id, entry in cached["scores"].items()
                }
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # corrupt cache → recompute
    text = frd_path.read_text(encoding="utf-8")
    acs = _extract_acs(text)
    results = {ac_id: score_ac(body) for ac_id, body in acs.items()}
    if use_cache:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(
                {
                    "scorer_version": SCORER_VERSION,
                    "frd_sha": sha,
                    "scores": {k: v.to_dict() for k, v in results.items()},
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return results


def invalidate_cache(repo_root: Optional[Path] = None, version: Optional[str] = None) -> int:
    """Delete cache directory for given (or current) SCORER_VERSION."""
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "build" / "cache" / "ambiguity" / (version or SCORER_VERSION)
    if not target.exists():
        return 0
    count = 0
    for f in target.glob("*.json"):
        f.unlink()
        count += 1
    return count


def is_blocking(scores: Dict[str, AmbiguityScore], threshold: float = 0.4) -> Tuple[bool, List[str]]:
    """SCG-0 ambiguity gate decision (Rule 9.16.2). Returns (block?, blocking_ac_ids)."""
    blocking = [ac_id for ac_id, s in scores.items() if s.score >= threshold]
    return bool(blocking), blocking
