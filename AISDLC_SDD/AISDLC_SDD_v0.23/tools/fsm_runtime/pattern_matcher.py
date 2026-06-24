"""Semantic same-pattern matcher for PR_REVIEW (ACT-021, Phase E M2).

Previous behaviour (string equality) missed semantically-identical failure
reasons that differ only in phrasing, such as:

    "test_login_p95 > 200ms at concurrency 100"
    "test_login_p95 exceeded 200ms under 100 concurrent users"

This module normalises both strings and computes a fuzzy ratio. A threshold
of 0.75 (by default) is enough to treat them as the same failure pattern,
which lets SPEC_AUDIT fire sooner and prevents wasted PR_REVIEW retries.

Design choices (see §ACT-021):

- No external dependencies (stdlib `difflib`).
- Normalisation step strips timestamps, numbers, file paths and common English
  articles so irrelevant variance disappears before comparison.
- Configurable threshold via env `SDD_PATTERN_MATCH_THRESHOLD` (default 0.75).
- Pure functions — safe to call from hooks / Runtime / tests.
"""
from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Iterable, Optional

_DEFAULT_THRESHOLD = 0.75

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_TIMESTAMP_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+\-]\d{2}:?\d{2})?)?\b"
)
_PATH_RE = re.compile(r"(?:[A-Za-z]:)?(?:[\\/][\w.\-]+){2,}")
_WHITESPACE_RE = re.compile(r"\s+")
# Filler words / articles that add no semantic weight in failure reasons.
# 中文 stopwords 涵蓋常見虛詞與介詞（CLAUDE.md Rule 1 繁中專案必備）。
_STOPWORDS = {
    # 英文虛詞
    "the", "a", "an", "at", "on", "in", "to", "of", "for", "with",
    "than", "by", "and", "or", "but",
    "is", "was", "were", "be", "been", "being",
    "users", "user",
    # 中文虛詞 / 介詞 / 助詞
    "的", "之", "了", "為", "於", "在", "是", "則",
    "此", "該", "也", "而", "以", "與", "及",
}

# Map comparison phrasing variants to a single canonical token. This
# catches "exceeded 200ms", "> 200ms", "above 200ms" all as the same thing.
_SYNONYMS = {
    # greater-than family
    ">": "gt", "gt": "gt",
    "exceeded": "gt", "exceeds": "gt", "exceed": "gt",
    "above": "gt", "over": "gt", "greater": "gt",
    # less-than family
    "<": "lt", "lt": "lt",
    "below": "lt", "under": "lt", "less": "lt", "fewer": "lt",
    # "not equal" — rare but worth normalising
    "≠": "neq", "!=": "neq",
    # concurrency phrasing
    "concurrent": "concurrency",
    "concurrency": "concurrency",
}

# 中文同義詞（multi-character phrases）— 採 string-level 替換，於 normalize
# 開頭把「超過 / 大於 / 高於」等折射為英文 canonical token，與英文 paraphrase
# 收斂到相同 token bag。CLAUDE.md Rule 1 強制繁中專案必須支援。
_CHINESE_SYNONYMS = {
    # greater-than 家族 → "gt"
    "超過": " gt ", "大於": " gt ", "高於": " gt ",
    "多於": " gt ", "超出": " gt ", "大過": " gt ",
    # less-than 家族 → "lt"
    "低於": " lt ", "小於": " lt ", "少於": " lt ",
    "不足": " lt ", "未達": " lt ", "小過": " lt ",
    # concurrency 家族 → "concurrency"
    "同時性": " concurrency ", "並發": " concurrency ",
    "併發": " concurrency ", "同時": " concurrency ",
}


def _apply_synonyms(token: str) -> str:
    return _SYNONYMS.get(token, token)


def _load_threshold() -> float:
    raw = os.environ.get("SDD_PATTERN_MATCH_THRESHOLD")
    if not raw:
        return _DEFAULT_THRESHOLD
    try:
        val = float(raw)
    except ValueError:
        return _DEFAULT_THRESHOLD
    return max(0.0, min(1.0, val))


def normalize(text: Optional[str]) -> str:
    """Normalise a failure reason for fuzzy comparison."""
    if not text:
        return ""
    s = str(text).lower()
    s = _TIMESTAMP_RE.sub(" ", s)
    s = _PATH_RE.sub(" ", s)
    # 中文同義詞先做 string-level 替換（多字短語 split 不開）。
    # 注意：須以較長 key 優先（「同時性」必須在「同時」之前），dict 為 Py3.7+
    # 保序，已按長度排好。
    for cn_key, canon in _CHINESE_SYNONYMS.items():
        if cn_key in s:
            s = s.replace(cn_key, canon)
    # Apply symbol synonyms before killing non-word characters.
    for sym, canon in (
        (">", " gt "), ("<", " lt "), ("≠", " neq "), ("!=", " neq "),
    ):
        s = s.replace(sym, canon)
    s = _NUMBER_RE.sub("N", s)
    # Replace non-word chars (keep letters/digits/underscore/Chinese) with spaces.
    s = re.sub(r"[^\w\u4e00-\u9fff]+", " ", s, flags=re.UNICODE)
    tokens = [_apply_synonyms(t) for t in s.split() if t and t not in _STOPWORDS]
    return _WHITESPACE_RE.sub(" ", " ".join(tokens)).strip()


def _token_jaccard(a: str, b: str) -> float:
    ta = set(a.split())
    tb = set(b.split())
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    union = ta | tb
    return len(inter) / len(union) if union else 0.0


def similarity(a: Optional[str], b: Optional[str]) -> float:
    """Return similarity in [0.0, 1.0].

    Combines two signals and returns the stronger one:
    - Character-level SequenceMatcher ratio (sensitive to ordering/shape)
    - Token-set Jaccard (robust to reordering and filler words)
    """
    na = normalize(a)
    nb = normalize(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    jac = _token_jaccard(na, nb)
    return max(seq, jac)


def is_same_pattern(
    prev: Optional[str],
    curr: Optional[str],
    *,
    threshold: Optional[float] = None,
) -> bool:
    """Return True if `prev` and `curr` describe the same failure pattern."""
    if prev is None or curr is None:
        return False
    if prev == curr:
        return True
    thr = threshold if threshold is not None else _load_threshold()
    return similarity(prev, curr) >= thr


def best_match(
    curr: Optional[str],
    history: Iterable[Optional[str]],
    *,
    threshold: Optional[float] = None,
) -> Optional[int]:
    """Return the index of the best matching history entry, or None.

    Useful for debugging — callers can persist the matched history index
    alongside `same_pattern_count` for audit trails.
    """
    if curr is None:
        return None
    thr = threshold if threshold is not None else _load_threshold()
    best_idx = None
    best_score = thr
    for i, h in enumerate(history):
        score = similarity(h, curr)
        if score >= best_score:
            best_score = score
            best_idx = i
    return best_idx
