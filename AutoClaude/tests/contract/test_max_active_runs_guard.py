"""tests/contract/test_max_active_runs_guard.py — PM #8 契約測試（SD_06 W2-T2-16）。

對應：
  - SD_Improving_06.md v1.2 §9.2 #8（MAX_ACTIVE_RUNS_PER_GOAL=5）
  - ADR-SD06-001 §6.5 環境變數解析優先序
  - SD06_Execution_Guide.md W2 T2-16（≥ 5 case：5 OK / 6 enqueue / abort）

PM #8 契約：
  (C1) 預設上限 5（無 env、無建構子參數）
  (C2) 環境變數 MAX_ACTIVE_RUNS_PER_GOAL 覆寫建構子參數
  (C3) active_runs == limit 即拒（>=）
  (C4) raise MaxActiveRunsExceeded 含足夠診斷資訊（active_runs + limit）
  (C5) caller pattern 範例：catch → enqueue pending；abort_run 不影響其他 run
"""
from __future__ import annotations

from typing import Optional

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.orchestration import (
    MaxActiveRunsExceeded,
    OrchestrationCoordinator,
)
from autoclaude.core.ports.brain import BrainCapabilities, RetryPolicy
from autoclaude.core.ports.executor import ExecutionOutput
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask


# ──────────────────────────────────────────────────────────────
# Fakes（最小驗證 surface）
# ──────────────────────────────────────────────────────────────
class _NopBrain:
    def capabilities(self) -> BrainCapabilities:
        return BrainCapabilities(
            max_context_tokens=100_000,
            supports_streaming=False,
            retry_policy=RetryPolicy(),
            model_id="nop",
            dimension=1024,
        )

    def decide_correction(self, **_kw):
        return None

    def decide_escalation(self, **_kw):
        from autoclaude.core.ports.brain import EscalationDecision
        return EscalationDecision(human_handoff=True, reasoning="nop")


class _NopExecutor:
    def __init__(self):
        self.execute_called = 0

    def execute(self, prompt, *, maintain_context=True, timeout=600, label="",
                on_event=None) -> ExecutionOutput:
        self.execute_called += 1
        return ExecutionOutput(text="", exit_code=0, completed=True)

    def send_interrupt(self, reason: str = "") -> bool:
        return True


def _make_coord(*, max_runs: Optional[int] = None) -> OrchestrationCoordinator:
    return OrchestrationCoordinator(
        bus=EventBus(),
        brain=_NopBrain(),
        executor=_NopExecutor(),
        max_active_runs_per_goal=max_runs,
    )


def _make_pb_task():
    pb = Playbook(version="1.0", project="t", global_invariants=GlobalInvariants(), tasks=[])
    task = PlaybookTask(step_id="T01", name="t", prompt="x", expected_output_regex="")
    return pb, task


# ──────────────────────────────────────────────────────────────
# C1：預設值契約
# ──────────────────────────────────────────────────────────────
class TestDefaultLimitContract:
    def test_default_is_five_per_pm_8(self, monkeypatch):
        """PM #8：預設 MAX_ACTIVE_RUNS_PER_GOAL=5。"""
        monkeypatch.delenv("MAX_ACTIVE_RUNS_PER_GOAL", raising=False)
        coord = _make_coord()
        assert coord.max_active_runs_per_goal == 5


# ──────────────────────────────────────────────────────────────
# C2：環境變數解析優先序契約（ADR §6.5）
# ──────────────────────────────────────────────────────────────
class TestEnvVarPrecedenceContract:
    def test_env_var_overrides_constructor(self, monkeypatch):
        """env > 建構子 > 預設。"""
        monkeypatch.setenv("MAX_ACTIVE_RUNS_PER_GOAL", "3")
        coord = _make_coord(max_runs=10)
        assert coord.max_active_runs_per_goal == 3

    def test_invalid_env_var_falls_back_to_constructor(self, monkeypatch):
        """env 非數字 → 退回建構子參數。"""
        monkeypatch.setenv("MAX_ACTIVE_RUNS_PER_GOAL", "abc")
        coord = _make_coord(max_runs=7)
        assert coord.max_active_runs_per_goal == 7

    def test_constructor_overrides_default(self, monkeypatch):
        """無 env、有建構子值 → 採建構子。"""
        monkeypatch.delenv("MAX_ACTIVE_RUNS_PER_GOAL", raising=False)
        coord = _make_coord(max_runs=9)
        assert coord.max_active_runs_per_goal == 9


# ──────────────────────────────────────────────────────────────
# C3：邊界拒絕契約（>=）
# ──────────────────────────────────────────────────────────────
class TestBoundaryRejectContract:
    @pytest.mark.parametrize("active,expect_pass", [
        (0, True),
        (4, True),     # 5 OK 邊界內
        (5, False),    # 5 等於上限即拒（>=）
        (6, False),    # 6 enqueue 觸發點
        (100, False),
    ])
    def test_boundary_at_and_above_limit_rejected(self, active, expect_pass):
        coord = _make_coord(max_runs=5)
        pb, task = _make_pb_task()
        if expect_pass:
            result = coord.run_step(playbook=pb, task=task, step_idx=0,
                                    active_runs_for_goal=active)
            assert result.output.completed is True
        else:
            with pytest.raises(MaxActiveRunsExceeded):
                coord.run_step(playbook=pb, task=task, step_idx=0,
                               active_runs_for_goal=active)


# ──────────────────────────────────────────────────────────────
# C4：例外訊息診斷資訊
# ──────────────────────────────────────────────────────────────
class TestExceptionDiagnosticsContract:
    def test_exception_message_carries_active_and_limit(self):
        """raise 訊息必須含 active_runs_for_goal 與 MAX_ACTIVE_RUNS_PER_GOAL 數值。"""
        coord = _make_coord(max_runs=5)
        pb, task = _make_pb_task()
        with pytest.raises(MaxActiveRunsExceeded) as exc_info:
            coord.run_step(playbook=pb, task=task, step_idx=0,
                           active_runs_for_goal=8)
        msg = str(exc_info.value)
        assert "active_runs_for_goal=8" in msg
        assert "MAX_ACTIVE_RUNS_PER_GOAL=5" in msg


# ──────────────────────────────────────────────────────────────
# C5：caller pattern — enqueue + abort 不影響其他 run
# ──────────────────────────────────────────────────────────────
class TestCallerPatternContract:
    def test_caller_can_catch_and_enqueue_pending(self):
        """6 enqueue 範例：caller catch → pending queue；不破壞 coord 狀態。"""
        coord = _make_coord(max_runs=5)
        pb, task = _make_pb_task()
        pending: list[int] = []

        for goal_idx in range(7):
            try:
                coord.run_step(playbook=pb, task=task, step_idx=goal_idx,
                               active_runs_for_goal=5)
            except MaxActiveRunsExceeded:
                pending.append(goal_idx)

        # 5 個 run 都被擋（5 == 5），全部 enqueue
        assert len(pending) == 7
        # coord 仍可立即接受 active=4 的下個 run（狀態未污染）
        result = coord.run_step(playbook=pb, task=task, step_idx=99,
                                active_runs_for_goal=4)
        assert result.output.completed is True

    def test_abort_one_run_allows_pending_to_proceed(self):
        """abort 模擬：active 從 5 降為 4 → pending 可繼續（caller 邏輯，coord 不持狀態）。"""
        coord = _make_coord(max_runs=5)
        pb, task = _make_pb_task()
        active = 5
        # 第一輪：active=5 必拒
        with pytest.raises(MaxActiveRunsExceeded):
            coord.run_step(playbook=pb, task=task, step_idx=0,
                           active_runs_for_goal=active)
        # caller 模擬 abort_run：active 減 1
        active -= 1
        # 第二輪：active=4 通過
        result = coord.run_step(playbook=pb, task=task, step_idx=1,
                                active_runs_for_goal=active)
        assert result.output.completed is True
