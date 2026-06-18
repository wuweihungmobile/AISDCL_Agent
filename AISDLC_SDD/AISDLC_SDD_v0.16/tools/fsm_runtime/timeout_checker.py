"""ACT-023: HUMAN_PENDING wall-clock timeout checker.

Called from session_start hook (and optionally from a cron job).
No daemon required — timeouts are evaluated whenever the checker runs.

Outcomes:
- "OK"         : not in HUMAN_PENDING, or within 72h
- "REMINDER"   : 72h ≤ elapsed < 168h (hook emits a warning, state stays)
- "ESCALATION" : elapsed ≥ 168h (hook triggers record_escalation)
- "NO_TIMESTAMP": in HUMAN_PENDING but no entered_at recorded — caller
                  should back-fill with now() (best-effort recovery).
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional, TypedDict


class TimeoutVerdict(TypedDict):
    outcome: str            # OK | REMINDER | ESCALATION | NO_TIMESTAMP
    elapsed_hours: Optional[float]
    reminder_hours: int
    escalation_hours: int
    entered_at: Optional[str]


def _parse_iso(value: str) -> Optional[_dt.datetime]:
    if not value:
        return None
    try:
        # fromisoformat accepts "...+00:00" but not "Z" in <3.11; be defensive
        v = value.rstrip("Z")
        dt = _dt.datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        return dt
    except ValueError:
        return None


def evaluate_human_pending(state, *, now: Optional[_dt.datetime] = None) -> TimeoutVerdict:
    """Evaluate whether a state in HUMAN_PENDING has timed out.

    `state` is a FSMState (not typed to avoid circular imports).
    """
    reminder_h = 72
    escalation_h = 168
    tracking = (state.root.get("human_pending_tracking") or {}) if hasattr(state, "root") else {}
    if tracking:
        reminder_h = int(tracking.get("reminder_hours", reminder_h))
        escalation_h = int(tracking.get("escalation_hours", escalation_h))

    current = getattr(state, "current", None)
    if current != "HUMAN_PENDING":
        return TimeoutVerdict(
            outcome="OK",
            elapsed_hours=None,
            reminder_hours=reminder_h,
            escalation_hours=escalation_h,
            entered_at=tracking.get("entered_at"),
        )

    entered_at = tracking.get("entered_at") if tracking else None
    entered_dt = _parse_iso(entered_at) if entered_at else None
    if not entered_dt:
        return TimeoutVerdict(
            outcome="NO_TIMESTAMP",
            elapsed_hours=None,
            reminder_hours=reminder_h,
            escalation_hours=escalation_h,
            entered_at=entered_at,
        )

    now_dt = now or _dt.datetime.now(_dt.timezone.utc)
    elapsed = (now_dt - entered_dt).total_seconds() / 3600.0
    # Defensive: clock skew or future-dated entered_at → treat as NO_TIMESTAMP
    # so the caller can re-stamp now() instead of silently deferring forever.
    if elapsed < 0:
        return TimeoutVerdict(
            outcome="NO_TIMESTAMP",
            elapsed_hours=round(elapsed, 2),
            reminder_hours=reminder_h,
            escalation_hours=escalation_h,
            entered_at=entered_at,
        )
    if elapsed >= escalation_h:
        outcome = "ESCALATION"
    elif elapsed >= reminder_h:
        outcome = "REMINDER"
    else:
        outcome = "OK"
    return TimeoutVerdict(
        outcome=outcome,
        elapsed_hours=round(elapsed, 2),
        reminder_hours=reminder_h,
        escalation_hours=escalation_h,
        entered_at=entered_at,
    )


# ACT-023 規格相容別名（§SDD_improving_Automation_04.md §參 L344）
# 規格書指定的公開名稱為 check_human_pending_timeout；保留 evaluate_human_pending
# 作為實作名稱，向後相容現有測試與 hook。
check_human_pending_timeout = evaluate_human_pending


def mark_entered_now(state) -> str:
    """Stamp human_pending_tracking.entered_at with current UTC; returns timestamp."""
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    tracking = state.root.setdefault("human_pending_tracking", {})
    tracking["entered_at"] = now
    tracking.setdefault("reminder_hours", 72)
    tracking.setdefault("escalation_hours", 168)
    tracking["reminder_sent_at"] = None
    return now


def mark_reminder_sent(state) -> str:
    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    tracking = state.root.setdefault("human_pending_tracking", {})
    tracking["reminder_sent_at"] = now
    return now


def clear_tracking(state) -> None:
    """Called when leaving HUMAN_PENDING (transition to SPEC_FROZEN / regression / etc)."""
    tracking = state.root.setdefault("human_pending_tracking", {})
    tracking["entered_at"] = None
    tracking["reminder_sent_at"] = None
