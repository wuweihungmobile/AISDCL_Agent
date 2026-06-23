"""diagnostic.py — Phase G M1 / ACT-032 DiagnosticAgent

Rule-based classifier for ESCALATION reasons. Decides whether a 1-shot
bounded auto-recovery is allowed (transient) or must escalate to human
(structural). Conservative: unknown patterns default to structural.

Classification priority: structural > transient (when both match,
structural wins to avoid 自動修復 spec/data 層問題).

Public surface:
    DiagnosticResult — dataclass returned by ``diagnose()``
    diagnose(reason, *, spec_refs=None) -> DiagnosticResult
    is_auto_recoverable(reason) -> bool   (convenience wrapper)

Used by:
    auto_recovery.py — enter_auto_recovery() consults diagnose() before
    transitioning into AUTO_RECOVERY_ATTEMPT (Rule 9.14.3).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Tuple

CATEGORIES = ("transient", "structural")
SUB_TYPES = (
    "ci_timeout",
    "network_flap",
    "rate_limit",
    "spec_conflict",
    "data_corruption",
    "retry_exhausted",
    "sandbox_policy_violation",
    "adversarial_counterexample",  # Phase J / ACT-074 (transient)
    "adversarial_spec_gap",        # Phase J / ACT-074 (structural)
    "unknown",
)

# Rules ordered: structural first (priority), transient second.
# Each entry: (sub_type, category, [regex_patterns])
_RULES: List[Tuple[str, str, List[str]]] = [
    # ----- structural (auto_recoverable=False) -----
    (
        "data_corruption",
        "structural",
        [
            r"yaml.?error",
            r"schema.?violation",
            r"\.bak\s+fallback",
            r"primary=.*bak=",
            r"non_dict",
            r"missing_root",
            r"corrupt",
        ],
    ),
    (
        "spec_conflict",
        "structural",
        [
            r"SPEC_AUDIT.*resolution",
            r"SLV.*FAIL",
            r"SLV-\d{3}",
            r"AC[-\s].*conflict.*INV",
            r"INV[-\s].*conflict.*AC",
            r"spec[_\s]conflict",
            r"contradict",
        ],
    ),
    (
        "retry_exhausted",
        "structural",
        [
            r"retry_count.*(?:≥|>=)",
            r"exhausted",
            r"max_iterations",
            r"consecutive_compile_fail",
            r"budget.*exceeded",
        ],
    ),
    (
        # Phase I M1 / ACT-061：執行器自身安全違反（image 不在 allow-list /
        # spec 簽章不符 / lockfile 雜湊不符 / self-STRIDE 控制違反）。structural —
        # 不可 auto-recover（誤自動修「跑惡意碼」是更大風險）。
        "sandbox_policy_violation",
        "structural",
        [
            r"sandbox[_\s]policy[_\s]violation",
            r"image.*allow.?list",
            r"unsigned.*spec",
            r"spec.*signature.*mismatch",
            r"lockfile.*hash.*mismatch",
            r"self.?STRIDE",
            r"supply.?chain",
        ],
    ),
    (
        # Phase J / ACT-074：對抗判官揭露「AC 自洽但違反隱含 latent 關係」（spec 漏寫）。
        # structural — 不可 auto-recover（須回 SPEC_AUDIT / 規格自癒，不是重跑能解）。
        "adversarial_spec_gap",
        "structural",
        [
            r"adversarial.*spec.?gap",
            r"metamorphic.*violat",
            r"latent.*(?:invariant|relation).*violat",
            r"spec.?gap.*adversarial",
        ],
    ),
    # ----- transient (auto_recoverable=True) -----
    (
        # Phase J / ACT-074：對抗判官找到 runtime 反例（違反已宣告性質 / fuzz crash）。
        # transient — 可 1-shot auto-recovery（回 IMPLEMENTATION 重修，per Rule 9.22.1）。
        "adversarial_counterexample",
        "transient",
        [
            r"adversarial.*counterexample",
            r"fuzz.*crash",
            r"property.*(?:based)?.*violat",
            r"counterexample.*adversarial",
        ],
    ),
    (
        "ci_timeout",
        "transient",
        [
            r"ci.runner.*timeout",
            r"actions/runner-images.*502",
            r"\bCI\b.*timeout",
            r"job.*timed.?out",
            r"workflow.*cancelled",
            r"runner.*offline",
        ],
    ),
    (
        "network_flap",
        "transient",
        [
            r"ConnectionError",
            r"NetworkTimeout",
            r"EAI_AGAIN",
            r"DNS.*failure",
            r"socket.*timeout",
            r"ETIMEDOUT",
            r"network.*unreachable",
        ],
    ),
    (
        "rate_limit",
        "transient",
        [
            r"\b429\b",
            r"rate.?limit",
            r"Retry-After",
            r"too.many.requests",
            r"throttle",
            r"quota.*exceeded",
        ],
    ),
]

# Recovery playbook — only consulted for transient sub_types.
# Bounded by Rule 9.14.1 (max 3 AUTO_RECOVERY_ATTEMPT per session).
_RECOVERY_PLAYBOOK = {
    "ci_timeout": {"action": "wait_and_rerun", "wait_sec": 30},
    "network_flap": {"action": "exponential_backoff", "wait_sec": 5},
    "rate_limit": {"action": "wait_per_retry_after", "wait_sec": 60},
    # Phase J / ACT-074：對抗反例 → 回 IMPLEMENTATION 重修（no wait）
    "adversarial_counterexample": {"action": "reimplement_and_rerun", "wait_sec": 0},
}

_BASE_CONFIDENCE = 0.85
_MULTI_MATCH_PENALTY = 0.15
_UNKNOWN_CONFIDENCE = 0.5
_AUTO_RECOVER_THRESHOLD = 0.7


@dataclass
class DiagnosticResult:
    category: str
    sub_type: str
    auto_recoverable: bool
    confidence: float
    recovery_action: Optional[str]
    recovery_max_wait_sec: Optional[int]
    rationale: str
    escalation_reason: str
    spec_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def diagnose(
    escalation_reason: str,
    *,
    spec_refs: Optional[List[str]] = None,
) -> DiagnosticResult:
    """Classify an ESCALATION reason into a DiagnosticResult.

    Args:
        escalation_reason: The free-text reason recorded by
            ``FSMState.record_escalation()`` (or equivalent).
        spec_refs: Optional list of spec/decision_trace IDs for audit chain.

    Returns:
        DiagnosticResult with category, sub_type, auto_recoverable flag,
        confidence and (for transient) recovery_action.

    Notes:
        - Conservative default: no rule matched → structural/unknown,
          auto_recoverable=False, confidence=0.5.
        - When both structural and transient rules match, structural wins
          (Rule 9.14.3: structural ESCALATIONs forbid auto-recovery).
    """
    refs = list(spec_refs or [])
    text = (escalation_reason or "")

    matched: List[Tuple[str, str]] = []
    for sub_type, category, patterns in _RULES:
        for pat in patterns:
            if re.search(pat, text, flags=re.IGNORECASE):
                matched.append((sub_type, category))
                break  # one regex match per sub_type is enough

    if not matched:
        return DiagnosticResult(
            category="structural",
            sub_type="unknown",
            auto_recoverable=False,
            confidence=_UNKNOWN_CONFIDENCE,
            recovery_action=None,
            recovery_max_wait_sec=None,
            rationale=(
                "No diagnostic rule matched the escalation reason; "
                "conservative default = structural/unknown (no auto-recovery)."
            ),
            escalation_reason=escalation_reason or "",
            spec_refs=refs,
        )

    # Structural priority — protects against false auto-recovery on spec/data.
    structural_matches = [(s, c) for s, c in matched if c == "structural"]
    transient_matches = [(s, c) for s, c in matched if c == "transient"]
    chosen_sub_type, chosen_category = (
        structural_matches[0] if structural_matches else transient_matches[0]
    )

    has_both = bool(structural_matches and transient_matches)
    confidence = _BASE_CONFIDENCE - (_MULTI_MATCH_PENALTY if has_both else 0.0)

    if chosen_category == "transient":
        playbook = _RECOVERY_PLAYBOOK[chosen_sub_type]
        return DiagnosticResult(
            category="transient",
            sub_type=chosen_sub_type,
            auto_recoverable=True,
            confidence=confidence,
            recovery_action=playbook["action"],
            recovery_max_wait_sec=playbook["wait_sec"],
            rationale=(
                f"Pattern matched {chosen_sub_type} (transient); "
                f"recovery playbook: {playbook['action']} "
                f"(wait {playbook['wait_sec']}s)"
            ),
            escalation_reason=escalation_reason or "",
            spec_refs=refs,
        )

    # structural — explicit no-recovery
    return DiagnosticResult(
        category="structural",
        sub_type=chosen_sub_type,
        auto_recoverable=False,
        confidence=confidence,
        recovery_action=None,
        recovery_max_wait_sec=None,
        rationale=(
            f"Pattern matched {chosen_sub_type} (structural); "
            "must escalate to human per Rule 9.14.3."
        ),
        escalation_reason=escalation_reason or "",
        spec_refs=refs,
    )


def is_auto_recoverable(escalation_reason: str) -> bool:
    """Convenience wrapper: True iff confident transient diagnosis."""
    result = diagnose(escalation_reason)
    return result.auto_recoverable and result.confidence >= _AUTO_RECOVER_THRESHOLD
