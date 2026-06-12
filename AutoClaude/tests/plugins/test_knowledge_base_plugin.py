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


class TestKnowledgeBasePluginPostRunPersist:
    """F-C3：POST_RUN 必須觸發 KB metrics 持久化（重啟不清零的落地時機）。"""

    def test_post_run_calls_persist_metrics(self):
        # autospec（QA P2-3）：若 persist_metrics 被改名/移除，本測試於
        # create_autospec 即紅；plugin 內 try/except 吞 AttributeError，
        # 普通 MagicMock 抓不到此類漂移
        from unittest.mock import create_autospec

        from autoclaude.utils.knowledge_base import FailureKnowledgeBase

        kb = create_autospec(FailureKnowledgeBase, instance=True)
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb())
        plugin.on_event(ctx)
        kb.persist_metrics.assert_called_once()

    def test_post_run_persist_with_real_kb_writes_backend(self, tmp_path):
        """真 KB + LocalKbMetricStore 的 plugin 級整合（非 mock 路徑）。"""
        from autoclaude.infra.adapters.local_kb_metric_store import LocalKbMetricStore
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase

        store_path = tmp_path / ".kb_metrics_local.jsonl"
        kb = FailureKnowledgeBase(
            str(tmp_path / "kb.jsonl"),
            metric_store=LocalKbMetricStore(str(store_path)),
        )
        kb.query("sig")
        plugin = KnowledgeBasePlugin(knowledge_base=kb)
        plugin.on_event(HookContext(phase=KernelPhase.POST_RUN, playbook=_pb()))
        assert store_path.exists()

    def test_post_run_subscribed(self):
        assert KernelPhase.POST_RUN in KnowledgeBasePlugin().subscribed_phases()

    def test_post_run_without_kb_is_noop(self):
        plugin = KnowledgeBasePlugin(knowledge_base=None)
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb())
        assert plugin.on_event(ctx) is None
