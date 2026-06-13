# enforces (governance rules): R-9.7
"""Unit tests for ACT-023 HUMAN_PENDING wall-clock timeout checker."""
from __future__ import annotations

import datetime as _dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402
from tools.fsm_runtime import timeout_checker as tc  # noqa: E402


class TimeoutCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-timeout.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _new_runtime(self) -> FSMRuntime:
        state = load_state("timeout-proj", path=self.path)
        return FSMRuntime(state)

    def test_not_in_human_pending_is_ok(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "IMPLEMENTATION"
        verdict = tc.evaluate_human_pending(rt.state)
        self.assertEqual(verdict["outcome"], "OK")

    def test_no_timestamp_is_detected(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        # No human_pending_tracking.entered_at → NO_TIMESTAMP
        verdict = tc.evaluate_human_pending(rt.state)
        self.assertEqual(verdict["outcome"], "NO_TIMESTAMP")

    def test_elapsed_below_72h_is_ok(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=10)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": past.isoformat(timespec="seconds"),
            "reminder_hours": 72,
            "escalation_hours": 168,
        }
        verdict = tc.evaluate_human_pending(rt.state)
        self.assertEqual(verdict["outcome"], "OK")
        self.assertLess(verdict["elapsed_hours"] or 0, 72)

    def test_reminder_at_75h(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=75)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": past.isoformat(timespec="seconds"),
            "reminder_hours": 72,
            "escalation_hours": 168,
        }
        verdict = tc.evaluate_human_pending(rt.state)
        self.assertEqual(verdict["outcome"], "REMINDER")

    def test_exactly_72h_boundary_is_reminder(self) -> None:
        """QA Round-4 P3: boundary semantics — `elapsed >= reminder_h` triggers
        REMINDER, so exactly 72.0h must surface REMINDER (not OK).

        A regression to `elapsed > reminder_h` would make this 71.999h-ish.
        """
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        pinned_now = _dt.datetime(2026, 4, 23, 12, 0, 0, tzinfo=_dt.timezone.utc)
        past = pinned_now - _dt.timedelta(hours=72)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": past.isoformat(timespec="seconds"),
            "reminder_hours": 72,
            "escalation_hours": 168,
        }
        verdict = tc.evaluate_human_pending(rt.state, now=pinned_now)
        self.assertEqual(verdict["outcome"], "REMINDER")

    def test_exactly_168h_boundary_is_escalation(self) -> None:
        """QA Round-4 P3: boundary semantics — `elapsed >= escalation_h`
        triggers ESCALATION, so exactly 168.0h must surface ESCALATION
        (not REMINDER). Regressing to `>` would keep the caller in REMINDER
        state and defer escalation indefinitely.
        """
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        pinned_now = _dt.datetime(2026, 4, 23, 12, 0, 0, tzinfo=_dt.timezone.utc)
        past = pinned_now - _dt.timedelta(hours=168)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": past.isoformat(timespec="seconds"),
            "reminder_hours": 72,
            "escalation_hours": 168,
        }
        verdict = tc.evaluate_human_pending(rt.state, now=pinned_now)
        self.assertEqual(verdict["outcome"], "ESCALATION")

    def test_escalation_at_170h(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=170)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": past.isoformat(timespec="seconds"),
            "reminder_hours": 72,
            "escalation_hours": 168,
        }
        verdict = tc.evaluate_human_pending(rt.state)
        self.assertEqual(verdict["outcome"], "ESCALATION")

    def test_transition_into_human_pending_stamps_entered_at(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "SCG_VALIDATION"
        # Happy path: SCG_VALIDATION → HUMAN_PENDING
        rt.transition("HUMAN_PENDING")
        tracking = rt.state.root.get("human_pending_tracking") or {}
        self.assertIsNotNone(tracking.get("entered_at"))

    def test_transition_out_of_human_pending_clears_entered_at(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "SCG_VALIDATION"
        rt.transition("HUMAN_PENDING")
        self.assertIsNotNone(rt.state.root["human_pending_tracking"]["entered_at"])
        # HUMAN_PENDING → SPEC_FROZEN (happy path when no retry history)
        rt.transition("SPEC_FROZEN")
        self.assertIsNone(rt.state.root["human_pending_tracking"]["entered_at"])

    def test_future_entered_at_treated_as_no_timestamp(self) -> None:
        """P1-3 regression: clock skew / future-dated entered_at must not be
        silently treated as OK (elapsed would be negative). It should downgrade
        to NO_TIMESTAMP so the caller can re-stamp now() instead of deferring
        indefinitely.
        """
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        future = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=5)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": future.isoformat(timespec="seconds"),
            "reminder_hours": 72,
            "escalation_hours": 168,
        }
        verdict = tc.evaluate_human_pending(rt.state)
        self.assertEqual(verdict["outcome"], "NO_TIMESTAMP")
        # elapsed_hours is reported (negative) so operators can spot the skew
        self.assertIsNotNone(verdict["elapsed_hours"])
        self.assertLess(verdict["elapsed_hours"] or 0, 0)

    def test_spec_compliant_alias_available(self) -> None:
        """QA-01: 規格書 §SDD_improving_Automation_04.md §參 L344 指定公開 API 名稱
        為 check_human_pending_timeout；必須可匯入且與 evaluate_human_pending 同一物件。
        """
        from tools.fsm_runtime.timeout_checker import (
            check_human_pending_timeout,
            evaluate_human_pending,
        )
        self.assertIs(check_human_pending_timeout, evaluate_human_pending)

    def test_custom_thresholds_are_respected(self) -> None:
        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=5)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": past.isoformat(timespec="seconds"),
            "reminder_hours": 3,
            "escalation_hours": 10,
        }
        verdict = tc.evaluate_human_pending(rt.state)
        # 5h is between reminder(3h) and escalation(10h)
        self.assertEqual(verdict["outcome"], "REMINDER")

    def test_escalation_writes_abort_report(self) -> None:
        """QA-02: HUMAN_PENDING 逾時進入 ESCALATION 時，必須產出 Abort Report
        (CLAUDE.md Rule 9.5)。
        """
        import datetime as _dt2
        from tools.fsm_runtime.snapshot import save_abort_report

        rt = self._new_runtime()
        rt.state.current = "HUMAN_PENDING"
        past = _dt2.datetime.now(_dt2.timezone.utc) - _dt2.timedelta(hours=200)
        rt.state.root["human_pending_tracking"] = {
            "entered_at": past.isoformat(timespec="seconds"),
            "reminder_hours": 72,
            "escalation_hours": 168,
        }
        verdict = tc.evaluate_human_pending(rt.state)
        self.assertEqual(verdict["outcome"], "ESCALATION")

        # 模擬 session_start.py hook 的 ESCALATION 寫入路徑
        reason = (
            f"HUMAN_PENDING 逾時 {verdict['elapsed_hours']}h "
            f"(≥{verdict['escalation_hours']}h)，自動進入 ESCALATION (ACT-023)"
        )
        rt.state.record_escalation(reason)

        tmp_out = Path(self._tmp.name) / "abort"
        abort_path = save_abort_report(
            rt.state,
            reason=reason,
            category="human-pending-timeout",
            extra_context={
                "elapsed_hours": verdict["elapsed_hours"],
                "escalation_hours": verdict["escalation_hours"],
                "entered_at": verdict.get("entered_at"),
            },
            out_dir=tmp_out,
        )
        self.assertTrue(abort_path.exists(), f"Abort Report 未建立: {abort_path}")
        today = _dt2.date.today().isoformat()
        self.assertEqual(abort_path.name, f"ABORT-{today}-human-pending-timeout.md")
        content = abort_path.read_text(encoding="utf-8")
        self.assertIn("HUMAN_PENDING 逾時", content)
        self.assertIn("human-pending-timeout", content)
        self.assertIn("current_state", content)
        # extra_context 欄位應寫入
        self.assertIn("elapsed_hours", content)
        self.assertIn("escalation_hours", content)


if __name__ == "__main__":
    unittest.main()
