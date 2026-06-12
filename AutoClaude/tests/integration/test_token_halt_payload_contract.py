"""W2 DoD：TokenGuardPlugin.on_post_attempt payload 契約測試（SD_03 §2.3）。

驗證 TokenGuardPlugin 可正確處理 SD_03 §2.3 規定的完整 payload：
  {
    "tracker": FailureTracker,
    "attempt": int,
    "goto_counter": dict,
    "inject_before_counter": dict,
    "skip_to_counter": dict,
    "completed_step_ids": set[str],
    "step_evolution_counter": dict,
    "token_pct": float,   # TokenGuardPlugin 核心欄位
  }

並驗證：
  1. token_pct >= halt_threshold → ResourceRequest(request_halt=True)
  2. token_pct >= compact_threshold (< halt) → ResourceRequest(request_compact=True)
  3. token_pct 低 → None
  4. 額外 payload 欄位不影響 Plugin 行為（前向相容）
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autoclaude.core.hookspec import HookContext, KernelPhase, ResourceRequest
from autoclaude.execution.failure_tracker import FailureTracker
from autoclaude.models.playbook import Playbook, PlaybookTask, GlobalInvariants
from autoclaude.plugins.token_guard_plugin import TokenGuardPlugin
from autoclaude.utils.config import TokenGuardConfig


def _make_playbook() -> Playbook:
    return Playbook(
        project="contract-test",
        tasks=[PlaybookTask(step_id="T01", name="test step", prompt="do x")],
        global_invariants=GlobalInvariants(),
    )


def _make_full_payload(
    token_pct: float = 50.0,
    attempt: int = 1,
) -> dict:
    """依 SD_03 §2.3 契約構造完整 payload。"""
    tracker = FailureTracker(step_id="T01")
    return {
        "token_pct": token_pct,
        "tracker": tracker,
        "attempt": attempt,
        "goto_counter": {"T01": 1},
        "inject_before_counter": {},
        "skip_to_counter": {},
        "completed_step_ids": {"T00"},
        "step_evolution_counter": {"T01": 0},
        "failure_reason": "regex miss",
        "max_retries": 3,
    }


def _make_ctx(payload: dict) -> HookContext:
    return HookContext(
        phase=KernelPhase.POST_ATTEMPT,
        playbook=_make_playbook(),
        task=_make_playbook().tasks[0],
        step_idx=0,
        attempt=payload.get("attempt", 0),
        payload=payload,
    )


class TestTokenHaltPayloadContract:
    """SD_03 §2.3 TokenGuardPlugin payload 契約驗證。"""

    def test_halt_when_token_pct_above_halt_threshold(self):
        """token_pct >= halt_threshold（預設 90）→ ResourceRequest(request_halt=True)。"""
        cfg = TokenGuardConfig(enabled=True, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=cfg)
        payload = _make_full_payload(token_pct=92.5)
        result = plugin.on_event(_make_ctx(payload))
        assert isinstance(result, ResourceRequest), f"預期 ResourceRequest，得到 {result}"
        assert result.request_halt is True
        assert result.request_compact is False

    def test_compact_when_token_pct_between_thresholds(self):
        """compact_threshold <= token_pct < halt_threshold → request_compact=True。"""
        cfg = TokenGuardConfig(enabled=True, compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=cfg)
        payload = _make_full_payload(token_pct=85.0)
        result = plugin.on_event(_make_ctx(payload))
        assert isinstance(result, ResourceRequest), f"預期 ResourceRequest，得到 {result}"
        assert result.request_compact is True
        assert result.request_halt is False

    def test_none_when_token_pct_below_thresholds(self):
        """token_pct 低 → None（無資源請求）。"""
        cfg = TokenGuardConfig(enabled=True, compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=cfg)
        payload = _make_full_payload(token_pct=50.0)
        result = plugin.on_event(_make_ctx(payload))
        assert result is None

    def test_extra_contract_fields_do_not_break_plugin(self):
        """SD_03 §2.3 要求的額外欄位（tracker/goto_counter/…）不影響 Plugin 行為。"""
        cfg = TokenGuardConfig(enabled=True, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=cfg)
        payload = _make_full_payload(token_pct=95.0)
        # 確認包含契約所有欄位
        required = {"tracker", "attempt", "goto_counter", "inject_before_counter",
                    "skip_to_counter", "completed_step_ids", "step_evolution_counter"}
        assert required.issubset(set(payload.keys())), (
            f"payload 缺少必要欄位: {required - set(payload.keys())}"
        )
        # Plugin 不應因額外欄位崩潰
        result = plugin.on_event(_make_ctx(payload))
        assert isinstance(result, ResourceRequest)
        assert result.request_halt is True

    def test_disabled_guard_returns_none(self):
        """token_guard.enabled=False 時無論 token_pct 為何都不觸發。"""
        cfg = TokenGuardConfig(enabled=False)
        plugin = TokenGuardPlugin(token_guard_cfg=cfg)
        payload = _make_full_payload(token_pct=99.0)
        result = plugin.on_event(_make_ctx(payload))
        assert result is None

    def test_halt_reason_contains_pct_value(self):
        """halt 的 reason 應包含 token_pct 數值，便於排查。"""
        cfg = TokenGuardConfig(enabled=True, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=cfg)
        payload = _make_full_payload(token_pct=92.5)
        result = plugin.on_event(_make_ctx(payload))
        assert isinstance(result, ResourceRequest)
        assert "92.5" in result.reason or "92" in result.reason

    def test_attempt_field_affects_dynamic_compact_threshold(self):
        """attempt 欄位影響 dynamic compact threshold（高 attempt → 較低門檻）。"""
        cfg = TokenGuardConfig(enabled=True, compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        plugin = TokenGuardPlugin(token_guard_cfg=cfg)
        # 低 attempt（0/3）→ 門檻約 80%；token_pct=79 應不 compact
        payload_low = _make_full_payload(token_pct=79.0, attempt=0)
        payload_low["max_retries"] = 3
        result_low = plugin.on_event(_make_ctx(payload_low))
        assert result_low is None, "attempt=0 時 79% 應低於門檻"
        # 高 attempt（3/3）→ 門檻約 65%；token_pct=70 應觸發 compact
        payload_high = _make_full_payload(token_pct=70.0, attempt=3)
        payload_high["max_retries"] = 3
        result_high = plugin.on_event(_make_ctx(payload_high))
        assert isinstance(result_high, ResourceRequest)
        assert result_high.request_compact is True
