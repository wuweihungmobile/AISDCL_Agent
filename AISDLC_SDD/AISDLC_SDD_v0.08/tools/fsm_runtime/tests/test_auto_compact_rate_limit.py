# enforces (governance rules): R-9.4
"""Unit tests for ACT-026 AUTO_COMPACT rate limit (Phase E M1)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402
from tools.fsm_runtime.transition_rules import MAX_AUTO_COMPACT_PER_STAGE  # noqa: E402


class AutoCompactRateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-rate-limit.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _bootstrap(self) -> FSMRuntime:
        state = load_state("rate-limit-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "IMPLEMENTATION"
        return rt

    def _compact_cycle(self, rt: FSMRuntime, tokens: int = 180_000, ratio: float = 0.9) -> dict:
        result = rt.trigger_auto_compact(cumulative_tokens=tokens, ratio=ratio)
        if not result.get("escalated"):
            rt.complete_auto_compact(reset_ledger=False)
        return result

    def test_under_limit_does_not_escalate(self) -> None:
        rt = self._bootstrap()
        for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
            result = self._compact_cycle(rt)
            self.assertFalse(result.get("escalated", False))
        auto = rt.state.root["auto_compact_state"]
        self.assertEqual(auto["count_per_stage"], MAX_AUTO_COMPACT_PER_STAGE)

    def test_over_limit_escalates(self) -> None:
        rt = self._bootstrap()
        for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
            self._compact_cycle(rt)
        # The N+1 attempt must be rejected
        result = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91)
        self.assertTrue(result.get("escalated"))
        self.assertEqual(rt.state.current, "ESCALATION")
        self.assertIn("auto_compact exceeded", result["reason"])

    def test_stage_change_resets_counter(self) -> None:
        rt = self._bootstrap()
        for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
            self._compact_cycle(rt)
        # Record a new SPEC_FROZEN stage — stage_key changes, counter should reset
        rt.state.current = "SPEC_FROZEN"
        rt.state.root.setdefault("frozen_stages", []).append(
            {"stage": "Stage-2", "frozen_at": "2026-04-20T00:00:00Z", "spec_docs": []}
        )
        rt.state.current = "IMPLEMENTATION"
        result = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.9)
        self.assertFalse(result.get("escalated", False))
        self.assertEqual(result["count_per_stage"], 1)
        self.assertEqual(result["stage_key"], "Stage-2")

    def test_stage_key_initial_when_no_frozen_stages(self) -> None:
        rt = self._bootstrap()
        result = self._compact_cycle(rt)
        self.assertEqual(result.get("stage_key"), "initial")

    def test_idempotent_when_already_pending(self) -> None:
        rt = self._bootstrap()
        rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.9)
        # Calling again without complete → should short-circuit, not bump counter
        result = rt.trigger_auto_compact(cumulative_tokens=190_000, ratio=0.95)
        self.assertTrue(result.get("already_pending"))
        auto = rt.state.root["auto_compact_state"]
        self.assertEqual(auto["count_per_stage"], 1)

    def test_trigger_in_escalation_is_noop(self) -> None:
        """P1-1 regression: once FSM is in ESCALATION, trigger_auto_compact must
        NOT re-record an escalation nor attempt a transition — it becomes a no-op.
        """
        rt = self._bootstrap()
        # Exceed the per-stage limit to push state into ESCALATION
        for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
            self._compact_cycle(rt)
        rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91)
        self.assertEqual(rt.state.current, "ESCALATION")
        escalations_before = len(rt.state.root.get("escalations", []))

        # Second call while still ESCALATION
        result = rt.trigger_auto_compact(cumulative_tokens=195_000, ratio=0.97)

        self.assertTrue(result.get("noop"))
        self.assertTrue(result.get("escalated"))
        self.assertIn("already in ESCALATION", result["reason"])
        self.assertEqual(rt.state.current, "ESCALATION")
        # Must not append another escalation record
        self.assertEqual(len(rt.state.root.get("escalations", [])), escalations_before)

    def test_over_limit_writes_abort_report(self) -> None:
        """QA-04: AUTO_COMPACT 超限 ESCALATION 必須產出 Abort Report
        (CLAUDE.md Rule 9.5)。使用 monkeypatch 將 SNAPSHOT_DIR 導向 tmp 目錄。
        """
        import datetime as _dt
        from tools.fsm_runtime import snapshot as snap_mod

        # 重導 SNAPSHOT_DIR 至 tmp，避免污染真實 build/reports/abort/
        tmp_out = Path(self._tmp.name) / "abort"
        original_dir = snap_mod.SNAPSHOT_DIR
        snap_mod.SNAPSHOT_DIR = tmp_out
        try:
            rt = self._bootstrap()
            for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
                self._compact_cycle(rt)
            # 超限觸發 ESCALATION
            result = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91)
            self.assertTrue(result.get("escalated"))
            self.assertEqual(rt.state.current, "ESCALATION")
            # Abort Report 必須被建立
            self.assertIsNotNone(result.get("abort_report"))
            abort_path = Path(result["abort_report"])
            self.assertTrue(abort_path.exists(), f"Abort Report 未建立: {abort_path}")
            today = _dt.date.today().isoformat()
            self.assertEqual(abort_path.name, f"ABORT-{today}-auto-compact-rate-limit.md")
            content = abort_path.read_text(encoding="utf-8")
            self.assertIn("auto_compact exceeded", content)
            self.assertIn("auto-compact-rate-limit", content)
            self.assertIn("count_per_stage", content)
            self.assertIn("stage_key", content)
        finally:
            snap_mod.SNAPSHOT_DIR = original_dir

    def test_trigger_in_terminated_is_noop(self) -> None:
        """P1-1 regression: TERMINATED must also suppress auto-compact."""
        rt = self._bootstrap()
        rt.state.current = "TERMINATED"
        result = rt.trigger_auto_compact(cumulative_tokens=200_000, ratio=0.99)
        self.assertTrue(result.get("noop"))
        self.assertTrue(result.get("escalated"))
        self.assertIn("already in TERMINATED", result["reason"])
        self.assertEqual(rt.state.current, "TERMINATED")

    def test_snapshot_filenames_are_unique_per_compact(self) -> None:
        """P1-C 回歸：同 stage 連續多次 auto-compact 必須產生不同檔名的
        Snapshot，不可互相 overwrite（檔名應帶 -{count:02d} 後綴）。
        """
        from tools.fsm_runtime import snapshot as snap_mod

        tmp_out = Path(self._tmp.name) / "abort"
        original_dir = snap_mod.SNAPSHOT_DIR
        snap_mod.SNAPSHOT_DIR = tmp_out
        try:
            rt = self._bootstrap()
            paths: list[Path] = []
            for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
                result = rt.trigger_auto_compact(
                    cumulative_tokens=180_000, ratio=0.9
                )
                self.assertFalse(result.get("escalated", False))
                snap_path = Path(rt.state.root["auto_compact_state"]["snapshot_path"])
                paths.append(snap_path)
                rt.complete_auto_compact(reset_ledger=False)

            # 每次 Snapshot 路徑必須唯一
            unique = {str(p) for p in paths}
            self.assertEqual(
                len(unique), MAX_AUTO_COMPACT_PER_STAGE,
                msg=f"Snapshot 檔名重複（會 overwrite 歷史）：{paths}",
            )
            # 每個檔案必須真的存在於磁碟
            for p in paths:
                self.assertTrue(p.exists(), f"Snapshot 檔不存在：{p}")
            # 檔名後綴須為 -01 / -02 / -03
            suffixes = sorted(p.stem.rsplit("-", 1)[-1] for p in paths)
            self.assertEqual(suffixes, ["01", "02", "03"])
        finally:
            snap_mod.SNAPSHOT_DIR = original_dir


if __name__ == "__main__":
    unittest.main()
