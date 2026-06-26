"""tests/core/test_kernel_start_idx_boundary.py
SD_Improving_04 W2 三方審查 Dev-W2-Min-2~4：補強 Kernel.run(start_idx=...) 邊界測試。

覆蓋：
  - start_idx == len(tasks)：直接進 POST_RUN 成功（視為已完整恢復）
  - start_idx < 0：截至 0 從頭開始
  - start_idx > len(tasks)：截至 len，直接成功
"""
from __future__ import annotations

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask


class _OkExecutor:
    def __init__(self):
        self.calls: list[str] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="", on_event=None):
        self.calls.append(prompt)
        return ExecutionOutput(text="OK")


class _OkEvaluator:
    def evaluate(self, task, output):  # noqa: ARG002
        # 介面契約（autoclaude.core.ports.evaluator.IEvaluator.evaluate）：
        # 回傳 (failure_reason, eval_output, exit_code)；None 為成功
        return None, "", 0


def _make_playbook(num_tasks: int) -> Playbook:
    return Playbook(
        version="1.0",
        project="boundary-test",
        global_invariants=GlobalInvariants(max_retries_per_step=1),
        tasks=[
            PlaybookTask(
                step_id=f"T{i + 1:02d}",
                name=f"task-{i}",
                prompt="dummy",
                expected_output_regex="OK",
            )
            for i in range(num_tasks)
        ],
    )


def _make_kernel() -> tuple[PlaybookKernel, _OkExecutor]:
    executor = _OkExecutor()
    kernel = PlaybookKernel(
        executor=executor,
        evaluator=_OkEvaluator(),
        bus=EventBus(),
    )
    return kernel, executor


class TestStartIdxBoundary:
    """SD_04 W2 Arch-W2-Min-2 / Dev-W2-Min-2~4：start_idx 邊界對稱性。"""

    def test_start_idx_at_total_tasks_returns_success(self):
        """start_idx == len(tasks)：while 迴圈立即結束，直接 POST_RUN 成功。"""
        kernel, executor = _make_kernel()
        pb = _make_playbook(3)
        result = kernel.run(pb, start_idx=3)
        assert result.success is True
        # while step_idx < len(tasks) 立即結束 → 無步驟執行
        assert executor.calls == []

    def test_start_idx_negative_clamped_to_zero(self):
        """start_idx=-5：應截至 0，從頭執行全部步驟。"""
        kernel, executor = _make_kernel()
        pb = _make_playbook(2)
        result = kernel.run(pb, start_idx=-5)
        assert result.success is True
        # 兩個步驟都應該執行
        assert len(executor.calls) == 2

    def test_start_idx_above_total_clamped_to_len(self):
        """start_idx=999：應截至 len(tasks)，直接成功不執行任何步驟。"""
        kernel, executor = _make_kernel()
        pb = _make_playbook(2)
        result = kernel.run(pb, start_idx=999)
        assert result.success is True
        assert executor.calls == []
