"""GoalProgressLedger 測試（F-C2 / US-AGT-004）。

驗證意圖：凍結計畫 Phase 1 驗收條件三「跨 ≥2 個 playbook run 的進度可彙總查詢」
— summarize 必須回傳跨 run features 聯集與最新達成度。
"""
from __future__ import annotations

from autoclaude.utils.goal_progress import GoalProgressLedger


def _ledger(tmp_path) -> GoalProgressLedger:
    return GoalProgressLedger(str(tmp_path / "goal_progress.jsonl"))


class TestRecordAndSummarize:
    def test_two_runs_union_features(self, tmp_path):
        """F-C2 核心驗收：跨 2 run 彙總 = features 聯集 + 最新 progress_pct。"""
        led = _ledger(tmp_path)
        led.record("project:P", playbook_id="P", completed_features=["T01", "T02"],
                   progress_pct=50.0)
        led.record("project:P", playbook_id="P", completed_features=["T02", "T03"],
                   progress_pct=75.0)
        summary = led.summarize("project:P")
        assert summary["run_count"] == 2
        assert summary["completed_features"] == ["T01", "T02", "T03"]
        assert summary["progress_pct"] == 75.0
        assert summary["last_recorded_at"] is not None

    def test_summarize_survives_restart(self, tmp_path):
        path = str(tmp_path / "goal_progress.jsonl")
        GoalProgressLedger(path).record("g1", completed_features=["A"])
        summary = GoalProgressLedger(path).summarize("g1")
        assert summary["completed_features"] == ["A"]

    def test_goal_isolation(self, tmp_path):
        led = _ledger(tmp_path)
        led.record("g1", completed_features=["A"])
        led.record("g2", completed_features=["B"])
        assert led.summarize("g1")["completed_features"] == ["A"]

    def test_unknown_goal_empty_summary(self, tmp_path):
        summary = _ledger(tmp_path).summarize("nope")
        assert summary["run_count"] == 0
        assert summary["completed_features"] == []
        assert summary["progress_pct"] is None
