"""tests/core/ports/test_brain_capabilities.py — AC0-1（SD_Improving_06 W1 T1-7）。

驗證 BrainCapabilities + RetryPolicy + EscalationDecision 三 dataclass +
IBrain Protocol 結構（capabilities + decide_escalation 簽名）。

對應 ADR-SD06-001 §6.2 五欄定案：
  max_context_tokens / supports_streaming / retry_policy / model_id / dimension
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from autoclaude.core.ports.brain import (
    BrainCapabilities,
    CorrectionResult,
    EscalationDecision,
    IBrain,
    RetryPolicy,
)


# ──────────────────────────────────────────────────────────────
# AC0-1：BrainCapabilities 五欄 + frozen 不可變
# ──────────────────────────────────────────────────────────────
class TestBrainCapabilities:
    def test_has_five_required_fields(self):
        """ADR §6.2 五欄全到位。"""
        names = {f.name for f in fields(BrainCapabilities)}
        assert names == {
            "max_context_tokens",
            "supports_streaming",
            "retry_policy",
            "model_id",
            "dimension",
        }

    def test_is_frozen(self):
        """BrainCapabilities frozen，instance 不可變。"""
        cap = BrainCapabilities(
            max_context_tokens=200_000,
            supports_streaming=True,
            retry_policy=RetryPolicy(),
            model_id="claude-opus-4-7",
            dimension=1024,
        )
        with pytest.raises(FrozenInstanceError):
            cap.dimension = 1536  # type: ignore[misc]

    def test_dimension_aligns_with_sd06_w3_default(self):
        """SD §6.2：dimension 預設與 SD_06 W3 BGE-M3 一致（1024 維）。"""
        from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter

        assert MinimaxBrainAdapter._DEFAULT_DIMENSION == 1024

    def test_retry_policy_default_values(self):
        """RetryPolicy 預設值符合穩定 retry 規範。"""
        rp = RetryPolicy()
        assert rp.max_attempts >= 1
        assert rp.backoff_seconds >= 0
        assert isinstance(rp.jitter, bool)


# ──────────────────────────────────────────────────────────────
# IBrain Protocol 結構驗證
# ──────────────────────────────────────────────────────────────
class TestIBrainProtocol:
    def test_capabilities_in_protocol(self):
        """IBrain.capabilities 必須在 Protocol 中可用。"""
        assert hasattr(IBrain, "capabilities")

    def test_decide_escalation_in_protocol(self):
        """IBrain.decide_escalation 必須在 Protocol 中可用。"""
        assert hasattr(IBrain, "decide_escalation")

    def test_decide_correction_preserved(self):
        """SD_Improving_01 既有 decide_correction 必須保留（向下相容）。"""
        assert hasattr(IBrain, "decide_correction")


# ──────────────────────────────────────────────────────────────
# MinimaxBrainAdapter 結構性實作 IBrain
# ──────────────────────────────────────────────────────────────
class TestMinimaxBrainAdapterCapabilities:
    def test_adapter_capabilities_returns_brain_capabilities(self):
        """MinimaxBrainAdapter.capabilities() 回傳 BrainCapabilities 實例。"""
        from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter

        class _FakeClient:
            _model = "abab6.5-chat"

        adapter = MinimaxBrainAdapter(_FakeClient())  # type: ignore[arg-type]
        cap = adapter.capabilities()
        assert isinstance(cap, BrainCapabilities)
        assert cap.model_id == "abab6.5-chat"
        assert cap.dimension == 1024
        assert isinstance(cap.retry_policy, RetryPolicy)

    def test_adapter_capabilities_idempotent_no_side_effect(self):
        """capabilities() 必須無副作用（ADR §6.2 註明）。"""
        from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter

        class _FakeClient:
            _model = "abab6.5-chat"

        adapter = MinimaxBrainAdapter(_FakeClient())  # type: ignore[arg-type]
        cap1 = adapter.capabilities()
        cap2 = adapter.capabilities()
        assert cap1 == cap2  # frozen dataclass equality


# ──────────────────────────────────────────────────────────────
# EscalationDecision 結構驗證
# ──────────────────────────────────────────────────────────────
class TestEscalationDecision:
    def test_human_handoff_true_by_default_adapter(self):
        """Phase 1 預設策略：MinimaxBrainAdapter.decide_escalation → human_handoff=True。"""
        from autoclaude.infra.adapters.minimax_brain import MinimaxBrainAdapter
        from autoclaude.models.playbook import PlaybookTask

        class _FakeClient:
            _model = "abab6.5-chat"

        adapter = MinimaxBrainAdapter(_FakeClient())  # type: ignore[arg-type]
        task = PlaybookTask(step_id="T01", name="x", prompt="y")
        decision = adapter.decide_escalation(
            task=task,
            failure_history=[{"attempt": 0}, {"attempt": 1}],
            convergence_trend="stuck",
        )
        assert isinstance(decision, EscalationDecision)
        assert decision.human_handoff is True
        assert "stuck" in decision.reasoning
        assert "failure_count=2" in decision.reasoning
