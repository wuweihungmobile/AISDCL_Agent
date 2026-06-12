"""Kernel POST_RUN → GoalProgressLedger 端到端測試（QA audit P1-2 修復）。

驗證意圖：F-C2 驗收「跨 ≥2 個 playbook run 進度可彙總」的完整鏈路 ——
Kernel 於 POST_RUN 附帶 completed_step_ids/total_steps payload →
GoalProgressPlugin 記錄 → ledger.summarize 跨 run 彙總。
若 kernel.py 的 POST_RUN payload 被移除，本檔必紅（堵 QA 攻擊推演 #4）。
"""
from __future__ import annotations

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.plugins.goal_progress_plugin import GoalProgressPlugin
from autoclaude.utils.goal_progress import GoalProgressLedger
from tests.plugins._template import FakeEvaluator, FakeExecutor, sample_playbook


def _run_once(ledger) -> None:
    bus = EventBus()
    bus.register(GoalProgressPlugin(ledger=ledger))
    kernel = PlaybookKernel(
        executor=FakeExecutor(), evaluator=FakeEvaluator(), bus=bus,
    )
    result = kernel.run(sample_playbook(n_tasks=2))
    assert result.success


class TestKernelToLedgerEndToEnd:
    def test_two_runs_summarized(self, tmp_path):
        """F-C2 驗收原文：跨 2 個 run 後可彙總查詢（真 kernel + 真 ledger）。"""
        ledger = GoalProgressLedger(str(tmp_path / "goal_progress.jsonl"))
        _run_once(ledger)
        _run_once(ledger)

        summary = ledger.summarize("project:TEST")
        assert summary["run_count"] == 2
        assert summary["completed_features"] == ["T01", "T02"]
        assert summary["progress_pct"] == 100.0

    def test_post_run_payload_contains_run_summary(self, tmp_path):
        """直接守住 kernel POST_RUN payload 契約（completed_step_ids/total_steps）。"""
        captured: list[HookContext] = []

        class _Probe:
            def name(self):
                return "probe"

            def priority(self):
                return 50

            def subscribed_phases(self):
                return [KernelPhase.POST_RUN]

            def on_event(self, ctx):
                captured.append(ctx)
                return None

        bus = EventBus()
        bus.register(_Probe())
        kernel = PlaybookKernel(
            executor=FakeExecutor(), evaluator=FakeEvaluator(), bus=bus,
        )
        kernel.run(sample_playbook(n_tasks=2))

        assert len(captured) == 1
        payload = captured[0].payload
        assert payload["completed_step_ids"] == ["T01", "T02"]
        assert payload["total_steps"] == 2


class TestResumeProgressSemantics:
    """複驗 P1-1 修復：resume run（start_idx>0）的 POST_RUN 進度摘要必須
    含 resume 前已完成步驟，否則 progress_pct 系統性低估。"""

    def test_resume_run_reports_full_progress(self, tmp_path):
        ledger = GoalProgressLedger(str(tmp_path / "goal_progress.jsonl"))
        bus = EventBus()
        bus.register(GoalProgressPlugin(ledger=ledger))
        kernel = PlaybookKernel(
            executor=FakeExecutor(), evaluator=FakeEvaluator(), bus=bus,
        )
        # 模擬 checkpoint resume：T01 已完成，從 idx=1 續跑
        result = kernel.run(sample_playbook(n_tasks=2), start_idx=1)
        assert result.success

        summary = ledger.summarize("project:TEST")
        assert summary["completed_features"] == ["T01", "T02"]  # 含 resume 前段
        assert summary["progress_pct"] == 100.0  # 非 50%

    def test_fully_completed_resume_reports_100_not_0(self, tmp_path):
        """極端：start_idx >= len（全完成 resume）應記 100% 非 0%。"""
        ledger = GoalProgressLedger(str(tmp_path / "goal_progress.jsonl"))
        bus = EventBus()
        bus.register(GoalProgressPlugin(ledger=ledger))
        kernel = PlaybookKernel(
            executor=FakeExecutor(), evaluator=FakeEvaluator(), bus=bus,
        )
        result = kernel.run(sample_playbook(n_tasks=2), start_idx=5)
        assert result.success
        assert ledger.summarize("project:TEST")["progress_pct"] == 100.0

    def test_kernel_result_keeps_per_run_semantics(self, tmp_path):
        """KernelResult.completed_steps 維持「本次 run」口徑（刻意與 payload 不同）。"""
        kernel = PlaybookKernel(
            executor=FakeExecutor(), evaluator=FakeEvaluator(), bus=EventBus(),
        )
        result = kernel.run(sample_playbook(n_tasks=2), start_idx=1)
        assert result.completed_steps == 1  # 本次只跑 T02
