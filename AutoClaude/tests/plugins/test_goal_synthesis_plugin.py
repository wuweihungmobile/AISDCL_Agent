"""GoalSynthesisPlugin 單元測試（Phase 3 / W11 #12，≥ 12 cases）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, MutationProposal
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.models.step_mutation import StepMutationType
from autoclaude.plugins import GoalSynthesisPlugin


def _pb(global_goal=None) -> Playbook:
    return Playbook(version="1.0", project="P", global_goal=global_goal,
                    global_invariants=GlobalInvariants(),
                    tasks=[PlaybookTask(step_id="T01", name="n", prompt="p")])


def _decision(is_achieved=True, completion_prompt=None, suggested_evaluator=None,
              gap_analysis=""):
    d = MagicMock()
    d.is_achieved = is_achieved
    d.completion_prompt = completion_prompt
    d.suggested_evaluator = suggested_evaluator
    d.gap_analysis = gap_analysis
    return d


class TestGoalSynthesisPluginBasics:
    def test_name(self):
        assert GoalSynthesisPlugin().name() == "goal_synthesis"

    def test_priority_is_50(self):
        assert GoalSynthesisPlugin().priority() == 50

    def test_subscribed_phases(self):
        assert GoalSynthesisPlugin().subscribed_phases() == [KernelPhase.POST_RUN]


class TestGoalSynthesisPluginNoOp:
    def test_disabled_returns_none(self):
        plugin = GoalSynthesisPlugin(minimax_client=MagicMock(), enabled=False)
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb("goal"))
        assert plugin.on_event(ctx) is None

    def test_no_client_returns_none(self):
        plugin = GoalSynthesisPlugin(minimax_client=None)
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb("goal"))
        assert plugin.on_event(ctx) is None

    def test_no_global_goal_returns_none(self):
        plugin = GoalSynthesisPlugin(minimax_client=MagicMock())
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb(None))
        assert plugin.on_event(ctx) is None


class TestGoalSynthesisPluginAchieved:
    def test_achieved_returns_none(self):
        client = MagicMock()
        client.validate_goal_achievement.return_value = _decision(is_achieved=True)
        plugin = GoalSynthesisPlugin(minimax_client=client)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb("complete all tests"),
            payload={"step_log": ["[OK] T01"]},
        )
        assert plugin.on_event(ctx) is None


class TestGoalSynthesisPluginNotAchieved:
    def test_not_achieved_returns_inject_after(self):
        client = MagicMock()
        client.validate_goal_achievement.return_value = _decision(
            is_achieved=False,
            completion_prompt="please add missing tests",
            suggested_evaluator="pytest -xvs",
        )
        plugin = GoalSynthesisPlugin(minimax_client=client)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb("complete all tests"),
            payload={"step_log": ["[OK] T01"]},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, MutationProposal)
        assert result.mutation.mutation_type == StepMutationType.INJECT_AFTER
        assert result.mutation.new_step_id == "T_GOAL_SYNTH"
        assert result.mutation.new_step_prompt == "please add missing tests"
        assert result.mutation.new_step_evaluator_command == "pytest -xvs"

    def test_not_achieved_no_completion_prompt_returns_none(self):
        client = MagicMock()
        client.validate_goal_achievement.return_value = _decision(
            is_achieved=False, completion_prompt=None,
        )
        plugin = GoalSynthesisPlugin(minimax_client=client)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb("g"),
            payload={"step_log": []},
        )
        assert plugin.on_event(ctx) is None


class TestGoalSynthesisPluginApiFailure:
    def test_api_exception_treats_as_achieved(self):
        client = MagicMock()
        client.validate_goal_achievement.side_effect = RuntimeError("api down")
        plugin = GoalSynthesisPlugin(minimax_client=client)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb("g"),
            payload={"step_log": ["[OK] T01"]},
        )
        # 不應拋例外
        assert plugin.on_event(ctx) is None


class TestGoalSynthesisPluginAchievementSummary:
    def test_short_log_full_join(self):
        log = [f"[OK] T{i:02d}" for i in range(15)]
        summary = GoalSynthesisPlugin.build_achievement_summary(log)
        # ≤ 20 步 → 完整 join
        assert "T00" in summary
        assert "T14" in summary

    def test_long_log_keeps_recent(self):
        log = [f"[OK] T{i:02d}" for i in range(30)]
        summary = GoalSynthesisPlugin.build_achievement_summary(log, max_recent=10)
        assert "前 20 個步驟已完成" in summary
        assert "最後 10 個步驟" in summary
        # 最後 10 筆應在
        assert "T29" in summary
        # 早期應省略
        assert "T00" not in summary


class TestGoalSynthesisPluginLatestDecision:
    def test_caches_latest_decision(self):
        client = MagicMock()
        decision = _decision(is_achieved=True)
        client.validate_goal_achievement.return_value = decision
        plugin = GoalSynthesisPlugin(minimax_client=client)
        plugin.on_event(HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb("g"),
            payload={"step_log": []},
        ))
        assert plugin.latest_decision() is decision


class TestGoalSynthesisPluginEventBusIntegration:
    def test_via_bus_emits_mutation_proposal_when_not_achieved(self):
        client = MagicMock()
        client.validate_goal_achievement.return_value = _decision(
            is_achieved=False, completion_prompt="補完", suggested_evaluator="echo ok",
        )
        bus = EventBus()
        bus.register(GoalSynthesisPlugin(minimax_client=client))
        merged = bus.emit(HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb("g"),
            payload={"step_log": []},
        ))
        assert merged.request_mutation is not None
        assert merged.request_mutation.mutation_type == StepMutationType.INJECT_AFTER


class TestGoalSynthesisPluginW4Absorbed:
    """SD_05 W4-4：吸收 4 mixin 方法的單元測試（SA-m2 boundary）。"""

    def test_prepend_global_goal_with_none(self):
        # global_goal=None → 不修改 prompt
        assert GoalSynthesisPlugin.prepend_global_goal("p", None) == "p"

    def test_prepend_global_goal_with_value(self):
        out = GoalSynthesisPlugin.prepend_global_goal("body", "GOAL_X")
        assert "本次自動化任務的總目標" in out
        assert "GOAL_X" in out
        assert out.endswith("\n\nbody")

    def test_prepend_global_goal_truncates_500_chars(self):
        long_goal = "G" * 600
        out = GoalSynthesisPlugin.prepend_global_goal("p", long_goal)
        assert "G" * 500 in out
        assert "G" * 501 not in out

    def test_prepend_global_goal_brief_none(self):
        assert GoalSynthesisPlugin.prepend_global_goal_brief("p", None) == "p"

    def test_prepend_global_goal_brief_default_100(self):
        # default brief_chars=100；short goal 不省略
        assert GoalSynthesisPlugin.prepend_global_goal_brief("p", "short") \
            == "[總目標方向] short\n\np"

    def test_prepend_global_goal_brief_exactly_100_no_ellipsis(self):
        goal = "G" * 100
        out = GoalSynthesisPlugin.prepend_global_goal_brief("p", goal)
        assert "…" not in out
        assert goal in out

    def test_prepend_global_goal_brief_101_with_ellipsis(self):
        goal = "G" * 101
        out = GoalSynthesisPlugin.prepend_global_goal_brief("p", goal)
        assert out.startswith("[總目標方向] " + "G" * 100 + "…")

    def test_prepend_global_goal_brief_cfg_override(self):
        # 模擬 cfg.playbook.global_goal_brief_chars=20
        class Inner:
            global_goal_brief_chars = 20
        class Cfg:
            playbook = Inner()
        goal = "G" * 50
        out = GoalSynthesisPlugin.prepend_global_goal_brief("p", goal, Cfg())
        assert "G" * 20 + "…" in out
        head = out.split("…")[0]
        assert "G" * 21 not in head

    def test_build_achievement_summary_under_20(self):
        log = [f"step {i}" for i in range(10)]
        out = GoalSynthesisPlugin.build_achievement_summary(log)
        assert out.count("\n") == 9  # 10 行用 9 個 \n 串

    def test_build_achievement_summary_over_20_keeps_recent_10(self):
        log = [f"step {i}" for i in range(25)]
        out = GoalSynthesisPlugin.build_achievement_summary(log)
        assert "[前 15 個步驟已完成" in out
        for i in range(15, 25):
            assert f"step {i}" in out

    def test_validate_global_goal_achievement_no_goal_returns_none(self):
        plugin = GoalSynthesisPlugin(minimax_client=MagicMock())
        # 既無 global_goal 參數也無 playbook.global_goal → 直接 None
        assert plugin.validate_global_goal_achievement(_pb(None), [], None) is None

    def test_validate_global_goal_achievement_no_client_returns_none(self):
        plugin = GoalSynthesisPlugin(minimax_client=None)
        assert plugin.validate_global_goal_achievement(_pb("g"), [], "g") is None

    def test_validate_global_goal_achievement_falls_back_to_playbook_goal(self):
        # 未傳 global_goal 參數 → 使用 playbook.global_goal
        client = MagicMock()
        client.validate_goal_achievement.return_value = _decision(is_achieved=True)
        plugin = GoalSynthesisPlugin(minimax_client=client)
        result = plugin.validate_global_goal_achievement(_pb("pg"), ["s1"])
        assert result is None
        call_kwargs = client.validate_goal_achievement.call_args.kwargs
        assert call_kwargs["global_goal"] == "pg"

    def test_validate_global_goal_achievement_code_snapshot_passed(self):
        client = MagicMock()
        client.validate_goal_achievement.return_value = _decision(
            is_achieved=False, completion_prompt="補完", suggested_evaluator="echo x",
        )
        plugin = GoalSynthesisPlugin(minimax_client=client)
        plugin.validate_global_goal_achievement(
            _pb("g"), [], "g", code_state_snapshot="SNAPSHOT_X",
        )
        call_kwargs = client.validate_goal_achievement.call_args.kwargs
        assert call_kwargs["code_state_snapshot"] == "SNAPSHOT_X"

