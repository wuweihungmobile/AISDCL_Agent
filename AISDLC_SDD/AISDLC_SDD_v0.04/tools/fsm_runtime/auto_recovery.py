"""auto_recovery.py — Phase G M1 / ACT-033 1-shot bounded auto-recovery

Operates strictly within Rule 9.14:
  9.14.1  ≤ 3 AUTO_RECOVERY_ATTEMPT per session (regardless of stage)
  9.14.2  ≤ 1 attempt per same escalation_reason per session
  9.14.3  category=structural is forbidden (DiagnosticAgent guard)
  9.14.4  failed attempt → ESCALATION_FINAL, no further recovery

Public API:
    RecoveryProposal     — dataclass returned by propose_recovery()
    RecoveryRefused      — exception raised when bounds exhausted / structural
    propose_recovery(reason) -> RecoveryProposal
    bounds_check(state, reason_hash) -> Tuple[bool, str]
    reason_hash(reason: str) -> str
    record_attempt_start(state, diagnostic, resume_state)
    record_attempt_outcome(state, outcome: "success"|"fail")

Note: this module does NOT execute the recovery action (wait/rerun) itself.
Wall-clock waits and CI reruns are left to the caller (orchestrator agent
or CI workflow) so the FSM stays I/O-free and chaos-testable.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .diagnostic import DiagnosticResult, diagnose

MAX_SESSION_ATTEMPTS = 3        # Rule 9.14.1
MAX_ATTEMPTS_PER_REASON = 1     # Rule 9.14.2
_AUTO_RECOVER_THRESHOLD = 0.7   # mirrors diagnostic._AUTO_RECOVER_THRESHOLD

_GATE_RESUMABLE_TARGETS = {
    "SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW",
    "RTM_VERIFY", "SCG_VALIDATION", "SPEC_REGRESSION_CHECK",
}


class RecoveryRefused(RuntimeError):
    """Raised when auto-recovery is forbidden by Rule 9.14 bounds or structural diagnosis."""


@dataclass
class RecoveryProposal:
    allowed: bool
    refusal_reason: Optional[str]   # populated iff allowed=False
    diagnostic: Optional[Dict[str, Any]]
    action: Optional[str]
    wait_sec: Optional[int]
    resume_state_required: bool     # True → caller must supply a valid resume_state

    def to_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def reason_hash(reason: str) -> str:
    """Normalize + hash escalation_reason for Rule 9.14.2 dedup.

    Normalization: lowercase, collapse runs of whitespace, strip surrounding
    whitespace, truncate to 200 chars. SHA-256 hex digest, truncated to 16 chars.
    """
    normalized = re.sub(r"\s+", " ", (reason or "").lower()).strip()[:200]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _recovery_state(state) -> Dict[str, Any]:
    """Returns mutable recovery_state container, creating defaults on first call.

    NOTE (QA Round-1 P1 #4): this function uses setdefault which materialises an
    empty `recovery_state` dict on `state.root` even when called from a read-only
    code path (e.g. propose_recovery's bounds_check on a refused proposal).
    This is intentional and safe:

      * The materialised dict only contains the four counter fields with their
        zero/empty defaults — no audit data, no PII, no decision trace.
      * The bounded counters (session_attempt_count, per_reason_count) are the
        sole authoritative source for Rule 9.14.1/9.14.2 enforcement; reading
        them via this helper guarantees subsequent writes (record_attempt_start)
        observe the same container, avoiding torn read-modify-write under
        concurrent FSM transitions.
      * Callers that do not record an attempt (i.e. propose-only flows) leave
        the counters at zero; this does not affect audit fidelity because
        `history` remains empty and `current` remains None.

    If a future refactor moves to lazy materialisation, BoundsCheckTests and
    RecordAttemptTests in test_auto_recovery.py both rely on the helper writing
    to state.root in-place — adjust them in lockstep.
    """
    rs = state.root.setdefault("recovery_state", {})
    rs.setdefault("session_attempt_count", 0)
    rs.setdefault("per_reason_count", {})
    rs.setdefault("current", None)
    rs.setdefault("history", [])
    return rs


def bounds_check(state, reason_hash_value: str) -> Tuple[bool, str]:
    """Check Rule 9.14.1 and 9.14.2 against current state. Returns (ok, reason)."""
    rs = _recovery_state(state)
    if int(rs["session_attempt_count"]) >= MAX_SESSION_ATTEMPTS:
        return False, (
            f"Rule 9.14.1: session_attempt_count "
            f"({rs['session_attempt_count']}) ≥ {MAX_SESSION_ATTEMPTS}"
        )
    per_reason = rs["per_reason_count"].get(reason_hash_value, 0)
    if int(per_reason) >= MAX_ATTEMPTS_PER_REASON:
        return False, (
            f"Rule 9.14.2: same reason already attempted "
            f"({per_reason} ≥ {MAX_ATTEMPTS_PER_REASON})"
        )
    return True, ""


def propose_recovery(
    escalation_reason: str,
    *,
    state=None,
    spec_refs: Optional[List[str]] = None,
) -> RecoveryProposal:
    """Compute whether auto-recovery is allowed, and the recovery plan.

    If `state` is provided, also enforces Rule 9.14.1/9.14.2 bounds.
    If state is None, only the diagnostic + Rule 9.14.3 (structural) guard runs
    — useful for previewing without committing to an attempt.
    """
    diag: DiagnosticResult = diagnose(escalation_reason, spec_refs=spec_refs)

    if not diag.auto_recoverable:
        return RecoveryProposal(
            allowed=False,
            refusal_reason=(
                f"Rule 9.14.3: diagnostic category={diag.category} "
                f"(sub_type={diag.sub_type}) is not auto-recoverable"
            ),
            diagnostic=diag.to_dict(),
            action=None,
            wait_sec=None,
            resume_state_required=False,
        )
    if diag.confidence < _AUTO_RECOVER_THRESHOLD:
        return RecoveryProposal(
            allowed=False,
            refusal_reason=(
                f"diagnostic confidence {diag.confidence:.2f} "
                f"< threshold {_AUTO_RECOVER_THRESHOLD}"
            ),
            diagnostic=diag.to_dict(),
            action=None,
            wait_sec=None,
            resume_state_required=False,
        )

    if state is not None:
        ok, reason = bounds_check(state, reason_hash(escalation_reason))
        if not ok:
            return RecoveryProposal(
                allowed=False,
                refusal_reason=reason,
                diagnostic=diag.to_dict(),
                action=None,
                wait_sec=None,
                resume_state_required=False,
            )

    return RecoveryProposal(
        allowed=True,
        refusal_reason=None,
        diagnostic=diag.to_dict(),
        action=diag.recovery_action,
        wait_sec=diag.recovery_max_wait_sec,
        resume_state_required=True,
    )


def record_attempt_start(
    state,
    *,
    diagnostic: Dict[str, Any],
    resume_state: str,
) -> Dict[str, Any]:
    """Persist attempt-start metadata. Caller must already have transitioned FSM."""
    if resume_state not in _GATE_RESUMABLE_TARGETS:
        raise ValueError(
            f"resume_state {resume_state!r} not in allowed targets "
            f"{sorted(_GATE_RESUMABLE_TARGETS)}"
        )
    rs = _recovery_state(state)
    rh = reason_hash(diagnostic.get("escalation_reason", ""))
    current = {
        "started_at": _now(),
        "resume_state": resume_state,
        "diagnostic": diagnostic,
        "reason_hash": rh,
        "outcome": None,
        "completed_at": None,
    }
    rs["current"] = current
    rs["session_attempt_count"] = int(rs["session_attempt_count"]) + 1
    rs["per_reason_count"][rh] = int(rs["per_reason_count"].get(rh, 0)) + 1
    return current


def record_attempt_outcome(state, outcome: str) -> Dict[str, Any]:
    """Mark current attempt as success or fail; flush to history."""
    if outcome not in ("success", "fail"):
        raise ValueError(f"outcome must be 'success' or 'fail', got {outcome!r}")
    rs = _recovery_state(state)
    current = rs.get("current")
    if not current:
        raise RuntimeError("no current AUTO_RECOVERY_ATTEMPT in progress")
    current["outcome"] = outcome
    current["completed_at"] = _now()
    history = rs.setdefault("history", [])
    history.append(current)
    # cap history to last 20 entries (consistent with patterns history cap)
    if len(history) > 20:
        del history[0:len(history) - 20]
    rs["current"] = None
    return current
