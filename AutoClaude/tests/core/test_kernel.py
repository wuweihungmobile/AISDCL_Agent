"""PlaybookKernel 狀態機單元測試（Phase 2）。

驗證：
  - PRE_RUN / POST_RUN / PRE_STEP / POST_STEP / PRE_ATTEMPT / POST_ATTEMPT 等 phase 觸發
  - PRE_RUN veto 直接結束
  - 步驟成功 → ADVANCE
  - 步驟失敗超過 max_retries → ESCALATE
  - POST_ATTEMPT request_escalation → 立刻 escalate
  - POST_ATTEMPT request_halt → 立刻 halt
  - PRE_ATTEMPT inject prefix 成功疊加到 prompt
  - completed_step_ids 正確收集

策略：用 fake IExecutor / IEvaluator 控制行為，不啟動真實 PTY。
"""
from __future__ import annotations

from typing import Any, Optional

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import (
    HookContext,
    KernelPhase,
    PromptInjectionResult,
    ResourceRequest,
    VetoResult,
)
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.kernel_state import KernelResult
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask


# ──────────────────────────────────────────────
# Fake IExecutor / IEvaluator
# ──────────────────────────────────────────────
class FakeExecutor:
    def __init__(self, outputs: dict[str, str] | str = "OK"):
        self.outputs = outputs
        self.calls: list[str] = []

    def execute(self, prompt, *, maintain_context=True, timeout=600, label=""):
        self.calls.append(prompt)
        if isinstance(self.outputs, dict):
            text = self.outputs.get(label, "")
        else:
            text = self.outputs
        return ExecutionOutput(text=text)


class FakeEvaluator:
    def __init__(self, fails_for_steps: Optional[list[str]] = None,
                 fail_count_for: Optional[dict[str, int]] = None):
        # fail_count_for: {step_id: 連續失敗次數，達到後就成功}
        self._fails = set(fails_for_steps or [])
        self._fail_counts = dict(fail_count_for or {})

    def evaluate(self, task, output):
        if task.step_id in self._fails:
            return f"step {task.step_id} forced fail", "", 1
        if task.step_id in self._fail_counts:
            n = self._fail_counts[task.step_id]
            if n > 0:
                self._fail_counts[task.step_id] = n - 1
                return f"need more retries: {task.step_id}", "", 1
        return None, "", 0


class _SpyPlugin:
    def __init__(self, name, priority_v, phases, result_factory=None):
        self._n = name
        self._p = priority_v
        self._ph = phases
        self._rf = result_factory or (lambda ctx: None)
        self.calls: list[KernelPhase] = []

    def name(self): return self._n
    def priority(self): return self._p
    def subscribed_phases(self): return self._ph
    def on_event(self, ctx):
        self.calls.append(ctx.phase)
        return self._rf(ctx)


def _pb(*tasks: PlaybookTask, max_retries=2) -> Playbook:
    return Playbook(
        version="1.0", project="kernel-test",
        global_invariants=GlobalInvariants(max_retries_per_step=max_retries),
        tasks=list(tasks),
    )


def _t(step_id: str, regex: Optional[str] = None) -> PlaybookTask:
    return PlaybookTask(
        step_id=step_id, name=f"step {step_id}", prompt=f"prompt-{step_id}",
        expected_output_regex=regex,
    )


# ──────────────────────────────────────────────
class TestKernelHappyPath:
    def test_single_step_success_returns_success_result(self):
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator())
        result = kernel.run(_pb(_t("T01")))
        assert isinstance(result, KernelResult)
        assert result.success is True
        assert result.completed_steps == 1
        assert "T01" in result.completed_step_ids
        assert result.escalated is False
        assert result.halted is False

    def test_multi_step_success_all_advance(self):
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator())
        result = kernel.run(_pb(_t("T01"), _t("T02"), _t("T03")))
        assert result.success is True
        assert result.completed_steps == 3
        assert result.completed_step_ids == ["T01", "T02", "T03"]

    def test_step_log_contains_ok_entries(self):
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator())
        result = kernel.run(_pb(_t("T01"), _t("T02")))
        assert any("[T01]" in entry and "✓" in entry for entry in result.step_log)
        assert any("[T02]" in entry and "✓" in entry for entry in result.step_log)


class TestKernelEscalation:
    def test_failed_step_exhausts_retries_and_escalates(self):
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(fails_for_steps=["T01"]))
        result = kernel.run(_pb(_t("T01"), max_retries=2))
        assert result.success is False
        assert result.escalated is True
        assert "max_retries_exhausted" in result.reason

    def test_eventual_success_after_retries(self):
        # T01 失敗 2 次後成功（max_retries=3 + 1 = 允許 4 次嘗試）
        kernel = PlaybookKernel(
            FakeExecutor(),
            FakeEvaluator(fail_count_for={"T01": 2}),
        )
        result = kernel.run(_pb(_t("T01"), max_retries=3))
        assert result.success is True
        assert "T01" in result.completed_step_ids


class TestKernelPreRunVeto:
    def test_pre_run_veto_short_circuits(self):
        bus = EventBus()
        spy = _SpyPlugin("blocker", 5, [KernelPhase.PRE_RUN],
                        result_factory=lambda ctx: VetoResult(contributor="blocker", reason="forbid"))
        bus.register(spy)
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(), bus=bus)
        result = kernel.run(_pb(_t("T01")))
        assert result.success is False
        assert result.completed_steps == 0
        assert "vetoed" in result.reason


class TestKernelPostAttempt:
    def test_request_escalation_short_circuits(self):
        bus = EventBus()
        bus.register(_SpyPlugin(
            "convergence", 65, [KernelPhase.POST_ATTEMPT],
            result_factory=lambda ctx: ResourceRequest(
                contributor="convergence", request_escalation=True,
            ),
        ))
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(fails_for_steps=["T01"]),
                                bus=bus)
        result = kernel.run(_pb(_t("T01"), max_retries=10))
        # 即使 max_retries=10，第 1 次失敗後 ConvergencePlugin escalate → 立即結束
        assert result.escalated is True

    def test_request_halt_short_circuits(self):
        bus = EventBus()
        bus.register(_SpyPlugin(
            "tg", 30, [KernelPhase.POST_ATTEMPT],
            result_factory=lambda ctx: ResourceRequest(
                contributor="tg", request_halt=True,
            ),
        ))
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(fails_for_steps=["T01"]),
                                bus=bus)
        result = kernel.run(_pb(_t("T01"), max_retries=10))
        assert result.halted is True
        assert result.escalated is False


class TestKernelPromptInjection:
    def test_pre_attempt_prefix_prepended_to_prompt(self):
        bus = EventBus()
        bus.register(_SpyPlugin(
            "anchor", 35, [KernelPhase.PRE_ATTEMPT],
            result_factory=lambda ctx: PromptInjectionResult(
                contributor="anchor", prefix="GOAL:\n",
            ),
        ))
        executor = FakeExecutor()
        kernel = PlaybookKernel(executor, FakeEvaluator(), bus=bus)
        kernel.run(_pb(_t("T01")))
        # 第一個 call 的 prompt 應含 GOAL: 前綴
        assert executor.calls
        assert executor.calls[0].startswith("GOAL:")
        assert "prompt-T01" in executor.calls[0]


class TestKernelPhaseEmissions:
    def test_emits_pre_and_post_run(self):
        bus = EventBus()
        spy = _SpyPlugin("obs", 50,
                         [KernelPhase.PRE_RUN, KernelPhase.POST_RUN])
        bus.register(spy)
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(), bus=bus)
        kernel.run(_pb(_t("T01")))
        assert KernelPhase.PRE_RUN in spy.calls
        assert KernelPhase.POST_RUN in spy.calls

    def test_emits_per_step_phases(self):
        bus = EventBus()
        spy = _SpyPlugin("obs", 50, [
            KernelPhase.PRE_STEP, KernelPhase.POST_STEP,
            KernelPhase.PRE_ATTEMPT, KernelPhase.ON_SUCCESS,
        ])
        bus.register(spy)
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(), bus=bus)
        kernel.run(_pb(_t("T01")))
        assert KernelPhase.PRE_STEP in spy.calls
        assert KernelPhase.PRE_ATTEMPT in spy.calls
        assert KernelPhase.ON_SUCCESS in spy.calls
        assert KernelPhase.POST_STEP in spy.calls

    def test_on_failure_emitted_after_retries_exhausted(self):
        bus = EventBus()
        spy = _SpyPlugin("kb", 50, [KernelPhase.ON_FAILURE])
        bus.register(spy)
        kernel = PlaybookKernel(FakeExecutor(),
                                FakeEvaluator(fails_for_steps=["T01"]),
                                bus=bus)
        kernel.run(_pb(_t("T01"), max_retries=1))
        assert KernelPhase.ON_FAILURE in spy.calls


class TestKernelStateMachineGuards:
    def test_pre_step_veto_escalates(self):
        bus = EventBus()
        bus.register(_SpyPlugin(
            "validator", 15, [KernelPhase.PRE_STEP],
            result_factory=lambda ctx: VetoResult(contributor="validator", reason="unsafe"),
        ))
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(), bus=bus)
        result = kernel.run(_pb(_t("T01")))
        assert result.escalated is True

    def test_pre_attempt_veto_escalates(self):
        bus = EventBus()
        bus.register(_SpyPlugin(
            "hotkey", 10, [KernelPhase.PRE_ATTEMPT],
            result_factory=lambda ctx: VetoResult(contributor="hotkey", reason="ESC pressed"),
        ))
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator(), bus=bus)
        result = kernel.run(_pb(_t("T01")))
        assert result.escalated is True


class TestKernelEmptyPlaybook:
    def test_empty_playbook_succeeds_immediately(self):
        kernel = PlaybookKernel(FakeExecutor(), FakeEvaluator())
        result = kernel.run(_pb())  # 0 步驟
        assert result.success is True
        assert result.completed_steps == 0
        assert result.completed_step_ids == []
