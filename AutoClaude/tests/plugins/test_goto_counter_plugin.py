"""GotoCounterPlugin 單元測試（Phase 3 / W6 #6 v1.1 新增，≥ 12 cases）。

驗證 Gap-042 / Gap-048 / Gap-049 跨 Session 計數器行為。
"""
from __future__ import annotations

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import CounterSnapshot, GotoCounterPlugin
from autoclaude.utils.config import PlaybookConfig


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task(step_id="T01") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name="n", prompt="p")


class TestGotoCounterPluginBasics:
    def test_name(self):
        assert GotoCounterPlugin().name() == "goto_counter"

    def test_priority_is_85(self):
        assert GotoCounterPlugin().priority() == 85

    def test_subscribed_phases_includes_post_attempt_and_pre_run(self):
        phases = GotoCounterPlugin().subscribed_phases()
        assert KernelPhase.PRE_RUN in phases
        assert KernelPhase.POST_ATTEMPT in phases
        assert KernelPhase.ON_INTERRUPT in phases
        assert KernelPhase.ON_TOKEN_USAGE in phases


class TestGotoCounterPluginIncrement:
    def test_increment_goto(self):
        p = GotoCounterPlugin()
        assert p.increment_goto("T01") == 1
        assert p.increment_goto("T01") == 2
        assert p.increment_goto("T02") == 1

    def test_increment_inject_before(self):
        p = GotoCounterPlugin()
        assert p.increment_inject_before("T01") == 1
        assert p.increment_inject_before("T01") == 2

    def test_increment_skip_to(self):
        p = GotoCounterPlugin()
        assert p.increment_skip_to("T01") == 1

    def test_increment_step_evolution(self):
        p = GotoCounterPlugin()
        assert p.increment_step_evolution("T05") == 1
        assert p.increment_step_evolution("T05") == 2


class TestGotoCounterPluginLimits:
    def test_is_goto_over_limit_false_initially(self):
        p = GotoCounterPlugin()
        assert p.is_goto_over_limit("T01") is False

    def test_is_goto_over_limit_true_after_max(self):
        # PlaybookConfig.max_goto_per_step 預設 3
        p = GotoCounterPlugin()
        for _ in range(3):
            p.increment_goto("T01")
        assert p.is_goto_over_limit("T01") is True

    def test_max_goto_per_step_configurable_gap_049(self):
        cfg = PlaybookConfig(max_goto_per_step=5)
        p = GotoCounterPlugin(playbook_cfg=cfg)
        for _ in range(4):
            p.increment_goto("T01")
        assert p.is_goto_over_limit("T01") is False  # 4 < 5
        p.increment_goto("T01")
        assert p.is_goto_over_limit("T01") is True   # 5 >= 5

    def test_is_step_evolution_over_limit_gap_048(self):
        cfg = PlaybookConfig(max_evolutions=3)
        p = GotoCounterPlugin(playbook_cfg=cfg)
        for _ in range(3):
            p.increment_step_evolution("T01")
        assert p.is_step_evolution_over_limit("T01") is True


class TestGotoCounterPluginSnapshot:
    def test_snapshot_returns_independent_copy(self):
        p = GotoCounterPlugin()
        p.increment_goto("T01")
        snap = p.snapshot()
        assert isinstance(snap, CounterSnapshot)
        assert snap.goto_counter == {"T01": 1}
        # 修改原 plugin 不影響 snapshot
        p.increment_goto("T01")
        assert snap.goto_counter == {"T01": 1}

    def test_snapshot_contains_all_4_counters(self):
        p = GotoCounterPlugin()
        p.increment_goto("T01")
        p.increment_inject_before("T02")
        p.increment_skip_to("T03")
        p.increment_step_evolution("T04")
        snap = p.snapshot()
        assert snap.goto_counter == {"T01": 1}
        assert snap.inject_before_counter == {"T02": 1}
        assert snap.skip_to_counter == {"T03": 1}
        assert snap.step_evolution_counter == {"T04": 1}


class TestGotoCounterPluginRestore:
    def test_restore_from_counter_snapshot(self):
        p = GotoCounterPlugin()
        snap = CounterSnapshot(
            goto_counter={"T01": 2, "T03": 1},
            step_evolution_counter={"T05": 1},
        )
        p.restore(snap)
        assert p.snapshot().goto_counter == {"T01": 2, "T03": 1}
        assert p.snapshot().step_evolution_counter == {"T05": 1}


class TestGotoCounterPluginPreRunRestore:
    def test_pre_run_restores_from_payload_dict_gap_042(self):
        p = GotoCounterPlugin()
        ctx = HookContext(
            phase=KernelPhase.PRE_RUN, playbook=_pb(),
            payload={"counter_snapshot": {
                "goto_counter": {"T01": 2},
                "inject_before_counter": {"T02": 1},
                "skip_to_counter": {},
                "step_evolution_counter": {"T03": 1},
            }},
        )
        p.on_event(ctx)
        assert p.is_goto_over_limit("T01") is False  # 2 < 3 預設
        snap = p.snapshot()
        assert snap.goto_counter == {"T01": 2}
        assert snap.step_evolution_counter == {"T03": 1}

    def test_pre_run_restores_from_counter_snapshot_object(self):
        p = GotoCounterPlugin()
        snap = CounterSnapshot(goto_counter={"T01": 3})
        ctx = HookContext(
            phase=KernelPhase.PRE_RUN, playbook=_pb(),
            payload={"counter_snapshot": snap},
        )
        p.on_event(ctx)
        assert p.is_goto_over_limit("T01") is True

    def test_pre_run_no_payload_keeps_empty(self):
        p = GotoCounterPlugin()
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb())
        p.on_event(ctx)
        assert p.snapshot().goto_counter == {}


class TestGotoCounterPluginPostAttempt:
    def test_post_attempt_increments_goto_on_applied_mutation(self):
        p = GotoCounterPlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task("T01"),
            payload={"applied_mutation_kind": "GOTO_STEP"},
        )
        p.on_event(ctx)
        assert p.snapshot().goto_counter == {"T01": 1}

    def test_post_attempt_no_payload_no_change(self):
        p = GotoCounterPlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
        )
        p.on_event(ctx)
        assert p.snapshot().goto_counter == {}

    def test_post_attempt_revise_increments_evolution_gap_048(self):
        p = GotoCounterPlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task("T05"),
            payload={"applied_mutation_kind": "REVISE_CURRENT"},
        )
        p.on_event(ctx)
        assert p.snapshot().step_evolution_counter == {"T05": 1}

    def test_post_attempt_inject_before_increments_correct_counter(self):
        p = GotoCounterPlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task("T01"),
            payload={"applied_mutation_kind": "INJECT_BEFORE"},
        )
        p.on_event(ctx)
        assert p.snapshot().inject_before_counter == {"T01": 1}
        assert p.snapshot().goto_counter == {}


class TestGotoCounterPluginObserverContract:
    def test_returns_none_except_save_request(self):
        """SD_05 W1 Step-2：除 ON_CHECKPOINT_SAVE_REQUEST 外，其他 phase 仍為純觀察者。

        SAVE_REQUEST 改回傳 CounterSnapshotResult（取代 M-4 anti-pattern）。
        """
        from autoclaude.core.hookspec import CounterSnapshotResult, KernelPhase
        p = GotoCounterPlugin()
        for phase in p.subscribed_phases():
            ctx = HookContext(phase=phase, playbook=_pb(), task=_task())
            result = p.on_event(ctx)
            if phase == KernelPhase.ON_CHECKPOINT_SAVE_REQUEST:
                assert isinstance(result, CounterSnapshotResult), (
                    "W1 Step-2 規格：SAVE_REQUEST 必須回傳 CounterSnapshotResult"
                )
            else:
                assert result is None, f"phase {phase} 應為純觀察者"
