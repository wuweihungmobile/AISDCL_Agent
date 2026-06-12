"""GoalProgressPlugin 測試（F-C2 / US-AGT-004）。

驗證意圖：POST_RUN 結果摘要必須轉為 ledger 紀錄（鍵 fallback project:{name}）；
無 ledger / 無 payload 時零干擾。
"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.plugins.goal_progress_plugin import GoalProgressPlugin


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="MyProj",
        tasks=[PlaybookTask(step_id="T01", name="t", prompt="p")],
    )


def _ctx(payload=None) -> HookContext:
    return HookContext(phase=KernelPhase.POST_RUN, playbook=_pb(),
                       payload=payload or {})


class TestBasics:
    def test_name_and_priority(self):
        p = GoalProgressPlugin()
        assert p.name() == "goal_progress"
        assert p.priority() == 50

    def test_subscribes_post_run_only(self):
        assert GoalProgressPlugin().subscribed_phases() == [KernelPhase.POST_RUN]


class TestRecording:
    def test_records_with_project_fallback_key(self):
        ledger = MagicMock()
        plugin = GoalProgressPlugin(ledger=ledger)
        plugin.on_event(_ctx({"completed_step_ids": ["T01", "T02"], "total_steps": 4}))
        args, kwargs = ledger.record.call_args
        assert args[0] == "project:MyProj"
        assert kwargs["completed_features"] == ["T01", "T02"]
        assert kwargs["progress_pct"] == 50.0

    def test_goal_task_id_takes_precedence(self):
        ledger = MagicMock()
        plugin = GoalProgressPlugin(ledger=ledger)
        plugin.on_event(_ctx({
            "completed_step_ids": ["T01"], "total_steps": 1, "goal_task_id": "g-123",
        }))
        assert ledger.record.call_args[0][0] == "g-123"


class TestNoInterference:
    def test_no_ledger_is_noop(self):
        assert GoalProgressPlugin().on_event(
            _ctx({"completed_step_ids": ["T01"], "total_steps": 1})
        ) is None

    def test_missing_payload_skips_record(self):
        ledger = MagicMock()
        GoalProgressPlugin(ledger=ledger).on_event(_ctx({}))
        ledger.record.assert_not_called()

    def test_broken_ledger_does_not_raise(self):
        ledger = MagicMock()
        ledger.record.side_effect = RuntimeError("boom")
        GoalProgressPlugin(ledger=ledger).on_event(
            _ctx({"completed_step_ids": ["T01"], "total_steps": 1})
        )
