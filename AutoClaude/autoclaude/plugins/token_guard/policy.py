"""policy.py — TokenGuardPlugin 主類（SD_06 W2-T2-13 拆 5 子模組組合層）。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 1 列（priority=30）
  - SD_Improving_06.md v1.2 §6.5 AC1-3（token_guard package 5 子模組）

訂閱 phase：
  - POST_ATTEMPT / ON_TOKEN_USAGE：策略決定（compact/halt）

公開 API（與原 token_guard_plugin.py 100% 等價，30+ 既有測試 patch path 維持）：
  - get_dynamic_compact_threshold / should_compact / should_halt
  - record_compact_failure / reset_compact_failure / is_compact_failure_critical
  - compact_failure_count（property）
  - verify_correction_applied
  - build_compact_prompt / process_compact_result
  - observe_token_line
  - resolve_per_step_cfg
"""
from __future__ import annotations

from typing import Any, Optional

from ...core.hookspec import HookContext, KernelPhase, ResourceRequest
from ...utils.config import TokenGuardConfig
from .compactor import (
    CompactFailureState,
    build_compact_prompt as _build_compact_prompt,
    process_compact_result as _process_compact_result,
)
from .git_verifier import verify_correction_applied as _verify_correction_applied
from .thresholds import (
    get_dynamic_compact_threshold as _get_dynamic_compact_threshold,
    should_compact_decision,
    should_halt_decision,
)
from .watcher import (
    observe_token_line as _observe_token_line,
    resolve_per_step_cfg as _resolve_per_step_cfg,
)


class TokenGuardPlugin:
    """Token / Context 用量保護 Plugin（組合層）。"""

    PRIORITY = 30

    def __init__(self, token_guard_cfg: Optional[TokenGuardConfig] = None):
        self._cfg = token_guard_cfg or TokenGuardConfig()
        self._compact_state = CompactFailureState()

    def name(self) -> str:
        return "token_guard"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.POST_ATTEMPT, KernelPhase.ON_TOKEN_USAGE]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if not self._cfg.enabled:
            return None
        if ctx.phase == KernelPhase.POST_ATTEMPT:
            return self._evaluate_resources(ctx)
        if ctx.phase == KernelPhase.ON_TOKEN_USAGE:
            return self._evaluate_resources(ctx)
        return None

    # ──────────────────────────────────────────────
    # 公開 API（與原 token_guard_plugin.py 100% 等價）
    # ──────────────────────────────────────────────
    def get_dynamic_compact_threshold(
        self, attempt: int, max_retries: int,
    ) -> float:
        return _get_dynamic_compact_threshold(
            base_threshold=self._cfg.compact_threshold_pct,
            attempt=attempt, max_retries=max_retries,
        )

    def should_compact(
        self, token_pct: float, attempt: int = 0, max_retries: int = 3,
        in_correction_loop: bool = False, correction_history_len: int = 0,
    ) -> bool:
        threshold = self.get_dynamic_compact_threshold(attempt, max_retries)
        return should_compact_decision(
            token_pct=token_pct, threshold=threshold,
            in_correction_loop=in_correction_loop,
            correction_history_len=correction_history_len,
        )

    def should_halt(self, token_pct: float) -> bool:
        return should_halt_decision(
            token_pct=token_pct, halt_threshold=self._cfg.halt_threshold_pct,
        )

    def record_compact_failure(self) -> int:
        return self._compact_state.record_failure()

    def reset_compact_failure(self) -> None:
        self._compact_state.reset()

    def is_compact_failure_critical(self) -> bool:
        return self._compact_state.is_critical()

    @property
    def compact_failure_count(self) -> int:
        """SD_05 W2 SD-M1：唯讀公開 property。"""
        return self._compact_state.count

    @property
    def _compact_failure_count(self) -> int:
        """SD_05 W2 backward-compat alias（既有測試直接讀 _compact_failure_count）。"""
        return self._compact_state.count

    @_compact_failure_count.setter
    def _compact_failure_count(self, value: int) -> None:
        self._compact_state.count = int(value)

    def resolve_per_step_cfg(self, task: Optional[Any] = None) -> TokenGuardConfig:
        return _resolve_per_step_cfg(global_cfg=self._cfg, task=task)

    def observe_token_line(
        self, pct: Optional[float], peak_pct: float,
        triggered_compact: bool, triggered_halt: bool,
    ) -> tuple[float, bool, bool]:
        return _observe_token_line(
            pct=pct, peak_pct=peak_pct,
            triggered_compact=triggered_compact, triggered_halt=triggered_halt,
            cfg=self._cfg,
        )

    def build_compact_prompt(
        self, *, task: Optional[Any] = None, attempt: int = 0,
        failure_summary: str = "", global_goal: Optional[str] = None,
        global_goal_anchor_chars: int = 200,
    ) -> str:
        return _build_compact_prompt(
            task=task, attempt=attempt, failure_summary=failure_summary,
            global_goal=global_goal,
            global_goal_anchor_chars=global_goal_anchor_chars,
        )

    def process_compact_result(
        self, triggered_compact: bool, peak_token_pct: float,
    ) -> bool:
        return _process_compact_result(
            state=self._compact_state, triggered_compact=triggered_compact,
        )

    def verify_correction_applied(self, attempt: int) -> Optional[str]:
        return _verify_correction_applied(attempt)

    # ──────────────────────────────────────────────
    # 內部
    # ──────────────────────────────────────────────
    def _evaluate_resources(self, ctx: HookContext) -> Optional[ResourceRequest]:
        payload = ctx.payload or {}
        token_pct = float(payload.get("token_pct", 0.0))
        attempt = int(ctx.attempt or 0)
        max_retries = int(payload.get("max_retries", 3))
        in_correction = bool(payload.get("in_correction_loop", False))
        history_len = int(payload.get("correction_history_len", 0))

        if self.should_halt(token_pct):
            return ResourceRequest(
                contributor=self.name(),
                request_halt=True,
                reason=f"token_pct={token_pct:.1f}% >= halt_threshold "
                       f"{self._cfg.halt_threshold_pct:.0f}%",
            )

        if self.should_compact(
            token_pct=token_pct, attempt=attempt, max_retries=max_retries,
            in_correction_loop=in_correction, correction_history_len=history_len,
        ):
            return ResourceRequest(
                contributor=self.name(),
                request_compact=True,
                reason=f"token_pct={token_pct:.1f}% >= dynamic_compact_threshold "
                       f"{self.get_dynamic_compact_threshold(attempt, max_retries):.1f}%",
            )

        return None
