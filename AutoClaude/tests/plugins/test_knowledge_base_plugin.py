"""KnowledgeBasePlugin 單元測試（Phase 3 / W6 #5，≥ 10 cases）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import KnowledgeBasePlugin


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task(step_id="T01") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name="n", prompt="p")


class TestKnowledgeBasePluginBasics:
    def test_name(self):
        assert KnowledgeBasePlugin().name() == "knowledge_base"

    def test_priority_is_50(self):
        assert KnowledgeBasePlugin().priority() == 50

    def test_subscribed_phases(self):
        phases = KnowledgeBasePlugin().subscribed_phases()
        assert KernelPhase.ON_SUCCESS in phases
        assert KernelPhase.ON_FAILURE in phases
        assert KernelPhase.ON_ESCALATION in phases


class TestKnowledgeBasePluginOnSuccess:
    def test_calls_record_success_with_signature(self):
        kb = MagicMock()
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(
            phase=KernelPhase.ON_SUCCESS, playbook=_pb(), task=_task(),
            payload={
                "error_signature": "regex_miss",
                "strategy": "retry_with_hint",
                "error_class": "syntax",
            },
        )
        plugin.on_event(ctx)
        assert kb.record_success.called
        kwargs = kb.record_success.call_args.kwargs
        assert kwargs["error_signature"] == "regex_miss"
        assert kwargs["strategy"] == "retry_with_hint"
        assert kwargs["step_id"] == "T01"
        assert kwargs["error_class"] == "syntax"

    def test_skips_when_no_signature(self):
        kb = MagicMock()
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(
            phase=KernelPhase.ON_SUCCESS, playbook=_pb(), task=_task(),
            payload={},
        )
        plugin.on_event(ctx)
        assert not kb.record_success.called

    def test_returns_none_always_observer(self):
        kb = MagicMock()
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(
            phase=KernelPhase.ON_SUCCESS, playbook=_pb(), task=_task(),
            payload={"error_signature": "x"},
        )
        assert plugin.on_event(ctx) is None


class TestKnowledgeBasePluginOnFailure:
    def test_failure_does_not_record(self):
        """ON_FAILURE 期間（重試中）不寫 KB，避免污染統計。"""
        kb = MagicMock()
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(
            phase=KernelPhase.ON_FAILURE, playbook=_pb(), task=_task(),
            payload={"error_signature": "x", "failure_reason": "regex miss"},
        )
        plugin.on_event(ctx)
        assert not kb.record_success.called
        assert not kb.record_escalation.called


class TestKnowledgeBasePluginOnEscalation:
    def test_calls_record_escalation_with_tried_strategies(self):
        kb = MagicMock()
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(), task=_task("T05"),
            payload={
                "error_signature": "import_err",
                "tried_strategies": ["retry", "evolve"],
            },
        )
        plugin.on_event(ctx)
        assert kb.record_escalation.called
        kwargs = kb.record_escalation.call_args.kwargs
        assert kwargs["error_signature"] == "import_err"
        assert kwargs["tried_strategies"] == ["retry", "evolve"]
        assert kwargs["step_id"] == "T05"

    def test_escalation_skips_when_no_signature(self):
        kb = MagicMock()
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(), task=_task(),
            payload={},
        )
        plugin.on_event(ctx)
        assert not kb.record_escalation.called


class TestKnowledgeBasePluginNoKb:
    def test_returns_none_when_kb_is_none(self):
        plugin = KnowledgeBasePlugin(knowledge_base=None)
        ctx = HookContext(
            phase=KernelPhase.ON_SUCCESS, playbook=_pb(), task=_task(),
            payload={"error_signature": "x"},
        )
        assert plugin.on_event(ctx) is None


class TestKnowledgeBasePluginErrorSafety:
    def test_record_success_exception_is_logged_not_propagated(self):
        kb = MagicMock()
        kb.record_success.side_effect = TypeError("bad signature")
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(
            phase=KernelPhase.ON_SUCCESS, playbook=_pb(), task=_task(),
            payload={"error_signature": "x"},
        )
        # 不應拋例外（純觀察者，異常需吞掉）
        result = plugin.on_event(ctx)
        assert result is None
