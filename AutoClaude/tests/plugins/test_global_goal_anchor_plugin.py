"""GlobalGoalAnchorPlugin 單元測試（Phase 3 / W7 #7，≥ 10 cases）。"""
from __future__ import annotations

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, PromptInjectionResult
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import GlobalGoalAnchorPlugin
from autoclaude.utils.config import PlaybookConfig


def _pb(global_goal=None) -> Playbook:
    return Playbook(version="1.0", project="P", global_goal=global_goal,
                    global_invariants=GlobalInvariants(), tasks=[])


def _t(step_id="T01") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name="n", prompt="p")


class TestGlobalGoalAnchorPluginBasics:
    def test_name(self):
        assert GlobalGoalAnchorPlugin().name() == "global_goal_anchor"

    def test_priority_is_35(self):
        assert GlobalGoalAnchorPlugin().priority() == 35

    def test_subscribed_phases(self):
        phases = GlobalGoalAnchorPlugin().subscribed_phases()
        assert KernelPhase.PRE_ATTEMPT in phases
        assert KernelPhase.ON_TOKEN_USAGE in phases


class TestGlobalGoalAnchorPluginNoGoal:
    def test_no_global_goal_returns_none(self):
        plugin = GlobalGoalAnchorPlugin()
        ctx = HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(global_goal=None),
            task=_t(), step_idx=0, attempt=0,
        )
        assert plugin.on_event(ctx) is None


class TestGlobalGoalAnchorPluginPreAttempt:
    def test_first_step_uses_full_header_gap_011_a(self):
        plugin = GlobalGoalAnchorPlugin()
        pb = _pb(global_goal="完成所有測試")
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=pb,
                          task=_t(), step_idx=0, attempt=0)
        result = plugin.on_event(ctx)
        assert isinstance(result, PromptInjectionResult)
        assert "本次自動化任務的總目標" in result.prefix
        assert "完成所有測試" in result.prefix

    def test_subsequent_step_uses_brief_header_gap_015_a(self):
        plugin = GlobalGoalAnchorPlugin()
        pb = _pb(global_goal="完成所有測試")
        # 先觸發第一步將 _is_first_step 設為 False
        plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=pb, task=_t(),
            step_idx=0, attempt=0,
        ))
        # 第二步應使用精簡版
        result = plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=pb, task=_t("T02"),
            step_idx=1, attempt=0,
        ))
        assert isinstance(result, PromptInjectionResult)
        assert "[總目標方向]" in result.prefix

    def test_attempt_gt_zero_no_inject(self):
        plugin = GlobalGoalAnchorPlugin()
        pb = _pb(global_goal="目標")
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=pb,
                          task=_t(), step_idx=0, attempt=1)  # 重試
        assert plugin.on_event(ctx) is None

    def test_brief_header_truncates_at_configured_length(self):
        cfg = PlaybookConfig(global_goal_brief_chars=50)
        plugin = GlobalGoalAnchorPlugin(playbook_cfg=cfg)
        pb = _pb(global_goal="X" * 100)
        # 觸發第一步
        plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=pb, task=_t(),
            step_idx=0, attempt=0,
        ))
        # 第二步精簡版
        result = plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=pb, task=_t("T02"),
            step_idx=1, attempt=0,
        ))
        # brief_chars=50，後面應有截斷符號 "…"
        assert "…" in result.prefix


class TestGlobalGoalAnchorPluginCompactAnchor:
    def test_build_compact_anchor_with_task_gap_039(self):
        plugin = GlobalGoalAnchorPlugin()
        anchor = plugin.build_compact_anchor(
            global_goal="達成 100% 覆蓋率",
            task=PlaybookTask(step_id="T05", name="測試", prompt="p",
                              expected_output_regex=r"\[OK\]"),
            attempt=2,
            failure_summary="last error here",
        )
        assert "MEMORY ANCHOR" in anchor
        assert "[ACTIVE_TASK] T05" in anchor
        assert "[ATTEMPT] 3" in anchor   # attempt+1
        assert "[SUCCESS_CONDITION]" in anchor
        assert "[LAST_FAILURE]" in anchor
        assert "[GLOBAL_GOAL]" in anchor

    def test_anchor_chars_configurable_gap_013_h(self):
        cfg = PlaybookConfig(global_goal_anchor_chars=200)
        plugin = GlobalGoalAnchorPlugin(playbook_cfg=cfg)
        anchor = plugin.build_compact_anchor(
            global_goal="X" * 500,
            task=PlaybookTask(step_id="T01", name="n", prompt="p"),
            attempt=0,
        )
        # global_goal 應被截斷至 200 + …
        assert "…" in anchor

    def test_no_task_returns_empty(self):
        plugin = GlobalGoalAnchorPlugin()
        anchor = plugin.build_compact_anchor(
            global_goal="x", task=None, attempt=0,
        )
        assert anchor == ""


class TestGlobalGoalAnchorPluginEventBusIntegration:
    def test_via_bus_full_header_first_step(self):
        bus = EventBus()
        bus.register(GlobalGoalAnchorPlugin())
        pb = _pb(global_goal="總目標")
        merged = bus.emit(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=pb, task=_t(),
            step_idx=0, attempt=0,
        ))
        assert "本次自動化任務的總目標" in merged.accumulated_prefix
