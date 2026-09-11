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

    def test_over_limit_marks_cap_exceeded_not_escalated(self) -> None:
        """D13（DEF-200-275 第五輪）：超限不再 escalated=True／轉 project-level ESCALATION，
        改為 session 級 `cap_exceeded` 一次性標記，state 維持原狀——改名自
        test_over_limit_escalates。"""
        rt = self._bootstrap()
        for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
            self._compact_cycle(rt)
        # The N+1 attempt must be rejected（不再進 ESCALATION，只落 session 級標記）
        result = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91)
        self.assertFalse(result.get("escalated"))
        self.assertTrue(result.get("cap_exceeded"))
        self.assertEqual(rt.state.current, "IMPLEMENTATION")
        self.assertIn("auto_compact exceeded", result["reason"])
        self.assertEqual(rt.state.root.get("escalation_history") or [], [])
        marker = rt.state.root["auto_compact_state"]["cap_exceeded"]
        self.assertEqual(marker["stage_key"], "initial")

    def test_cap_exceeded_marker_and_abort_report_are_per_stage_not_global(self) -> None:
        """複審 R-D13（DEF-200-275 第五輪）：`first_mark` 原是「有無 marker」的全域一次性旗標、
        不分 stage——stage-A 撞 cap 後，stage-B（全新 stage／全新 session）再撞 cap 時會被 stage-A
        的舊 marker 卡死：`abort_report` 回 None、`cap_exceeded` marker 仍是 stage-A/舊 session 的
        值，與現實不符。改為「無 marker，或 marker 的 stage_key 已不是目前 stage」才算首次——第二
        個 stage 自己的 cap 事件必須有獨立的 abort_report 與更新後的 marker。"""
        import datetime as _dt
        from tools.fsm_runtime import snapshot as snap_mod

        tmp_out = Path(self._tmp.name) / "abort"
        original_dir = snap_mod.SNAPSHOT_DIR
        snap_mod.SNAPSHOT_DIR = tmp_out
        try:
            rt = self._bootstrap()
            rt.state.root["frozen_stages"] = [{"stage": "stage-A"}]
            for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
                self._compact_cycle(rt)
            res1 = rt.trigger_auto_compact(
                cumulative_tokens=180_000, ratio=0.91, details={"session_id": "sess-A"})
            self.assertTrue(res1.get("cap_exceeded"))
            self.assertIsNotNone(res1.get("abort_report"))
            marker1 = dict(rt.state.root["auto_compact_state"]["cap_exceeded"])
            self.assertEqual(marker1["stage_key"], "stage-A")
            self.assertEqual(marker1["session_id"], "sess-A")

            # 換 stage：current_stage_key() 讀 frozen_stages 最後一筆。stage 換過會讓
            # count_per_stage 歸零，所以要重新打滿 MAX_AUTO_COMPACT_PER_STAGE 次才會在
            # stage-B 命中 cap（模擬「新 stage 也連續 N 次 compact 都沒見效」）。
            rt.state.root["frozen_stages"] = [{"stage": "stage-A"}, {"stage": "stage-B"}]
            for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
                rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91,
                                        details={"session_id": "sess-B"})
                rt.complete_auto_compact(reset_ledger=False, observed_effective=False)
            res2 = rt.trigger_auto_compact(
                cumulative_tokens=180_000, ratio=0.91, details={"session_id": "sess-B"})
            self.assertTrue(res2.get("cap_exceeded"))
            self.assertIsNotNone(
                res2.get("abort_report"),
                msg="stage-B 自己的 cap 事件必須有獨立的 abort_report，不得被 stage-A 的舊"
                    "marker 卡死（R-D13）",
            )
            marker2 = dict(rt.state.root["auto_compact_state"]["cap_exceeded"])
            self.assertEqual(marker2["stage_key"], "stage-B")
            self.assertEqual(
                marker2["session_id"], "sess-B",
                msg="marker 必須更新為第二個 stage 事件，不得殘留 stage-A/sess-A 的舊值（R-D13）",
            )
            # 兩次事件的 abort_report 應各自落盤且不同檔（同一 category 但不同 timestamp/內容
            # 也可能同名——本測試只斷言路徑存在且可讀，不強求不同檔名）。
            self.assertTrue(Path(res2["abort_report"]).exists())
            today = _dt.date.today().isoformat()
            self.assertEqual(Path(res2["abort_report"]).name,
                             f"ABORT-{today}-auto-compact-rate-limit.md")
        finally:
            snap_mod.SNAPSHOT_DIR = original_dir

    def test_observed_effective_clears_cap_exceeded_marker(self) -> None:
        """複審 R-D13：`complete_auto_compact(observed_effective=True)` 既然把 `count_per_stage`
        歸零（證明該 stage 沒卡住），殘留的 `cap_exceeded` marker 也必須一併清掉——否則下一次同
        stage 命中 cap 時，`first_mark` 判準會誤讀成「已存在同 stage marker」而不重寫、不補
        abort_report（與 observed_effective 想表達的『重新開始』語意矛盾）。"""
        from tools.fsm_runtime import snapshot as snap_mod

        tmp_out = Path(self._tmp.name) / "abort"
        original_dir = snap_mod.SNAPSHOT_DIR
        snap_mod.SNAPSHOT_DIR = tmp_out
        try:
            rt = self._bootstrap()
            for _ in range(MAX_AUTO_COMPACT_PER_STAGE):
                self._compact_cycle(rt)
            res = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91,
                                          details={"session_id": "sess-A"})
            self.assertTrue(res.get("cap_exceeded"))
            self.assertIn("cap_exceeded", rt.state.root["auto_compact_state"])

            # cap 超限後 state.current 仍是 IMPLEMENTATION（D13：不進 PENDING），要能呼叫
            # complete_auto_compact 必須先讓它進 PENDING——這裡直接呼叫底層方法驗證 D4 出口
            # 對 cap_exceeded 標記的清除語意（trigger_auto_compact 對 cap 超限本身是 no-op，
            # 不會轉態；真正會清除 marker 的路徑是「下一次全新 compact 週期」被觀測為有效）。
            rt.state.current = "AUTO_COMPACT_PENDING"
            rt.state.root["auto_compact_state"]["resume_state"] = "IMPLEMENTATION"
            rt.complete_auto_compact(reset_ledger=False, observed_effective=True)
            self.assertNotIn(
                "cap_exceeded", rt.state.root["auto_compact_state"],
                msg="observed_effective=True 出口必須清掉 cap_exceeded（R-D13）",
            )
        finally:
            snap_mod.SNAPSHOT_DIR = original_dir

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

        D13（DEF-200-275 第五輪）：per-stage cap 超限不再是通往 ESCALATION 的路徑（改成 session
        級 cap_exceeded 標記），所以這裡改用 `record_escalation` 直接把 state 推進 ESCALATION，
        單獨測這個既有、與 cap-exceeded 分支正交的「已在 ESCALATION 就 no-op」頂端守衛。
        """
        rt = self._bootstrap()
        rt.state.record_escalation("manual_trigger_for_test")
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
        """QA-04: AUTO_COMPACT 超限必須產出 Abort Report (CLAUDE.md Rule 9.5)——D13 起不再進
        project-level ESCALATION，但「人須被通知」的精神保留：cap 超限仍寫 Abort Report。
        使用 monkeypatch 將 SNAPSHOT_DIR 導向 tmp 目錄。
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
            # 超限觸發 session 級 cap_exceeded 標記（D13：不再是 ESCALATION）
            result = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.91)
            self.assertFalse(result.get("escalated"))
            self.assertTrue(result.get("cap_exceeded"))
            self.assertEqual(rt.state.current, "IMPLEMENTATION")
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
