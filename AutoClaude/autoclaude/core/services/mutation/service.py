"""MutationApplyService — Layer 2 Domain Service。

職責：
  - 維護 IMutationStrategy 註冊表（依 kind 路由）
  - apply(mutation, playbook, current_idx) → 委派給對應 strategy
  - validate_batch(mutations) → 驗證 batch 突變是否相容（Phase 3 EvolutionPlugin 使用）

行數預算：本檔 ≤ 80 行（行數預算 CI 強制）。
"""
from __future__ import annotations

from typing import Optional

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation, StepMutationType
from ...hookspec import IMutationStrategy
from .revise_current import ReviseCurrentStrategy
from .inject_after import InjectAfterStrategy
from .inject_before import InjectBeforeStrategy
from .goto_step import GotoStepStrategy
from .skip_to import SkipToStrategy
from .delete_step import DeleteStepStrategy
from .conditional import ConditionalStrategy
from .noop import NoOpStrategy


class MutationApplyService:
    """7 個 IMutationStrategy 的協調者（SD_05 W4-1 完備）。

    Counter SSOT：本 service 不維護任何 counter（goto / inject_before / skip_to）。
    Counter 由 GotoCounterPlugin 透過訂閱 phase 統一管理（SD_05 W1）。
    """

    def __init__(self, strategies: Optional[list[IMutationStrategy]] = None):
        if strategies is None:
            strategies = [
                ReviseCurrentStrategy(),
                InjectAfterStrategy(),
                InjectBeforeStrategy(),
                GotoStepStrategy(),
                SkipToStrategy(),
                DeleteStepStrategy(),
                ConditionalStrategy(),
                # NoOpStrategy 必為最後（永遠匹配）
            ]
        self._strategies = list(strategies) + [NoOpStrategy()]
        # SD_05 W4-1：反向注入 service 給需要遞迴呼叫的 strategy（如 Conditional）
        for s in self._strategies:
            injector = getattr(s, "_set_service", None)
            if callable(injector):
                injector(self)

    def apply(
        self, mutation: StepMutation, playbook: Playbook, current_idx: int
    ) -> bool:
        """套用單一突變至 playbook。回傳 True 代表成功；False 代表拒絕。"""
        for s in self._strategies:
            if isinstance(s, NoOpStrategy):
                continue   # NoOp 是最後 fallback
            if s.can_handle(mutation):
                return s.apply(mutation, playbook, current_idx)
        # fallback to NoOp
        return self._strategies[-1].apply(mutation, playbook, current_idx)

    def validate_batch(self, mutations: list[StepMutation]) -> bool:
        """驗證 batch 突變是否相容（簡化版：禁止同時 INJECT_BEFORE + DELETE_STEP 同一 target）。"""
        if not mutations:
            return True
        injected = {m.new_step_id for m in mutations
                    if m.mutation_type in (StepMutationType.INJECT_AFTER, StepMutationType.INJECT_BEFORE)
                    and m.new_step_id}
        deleted = {m.delete_step_id for m in mutations
                   if m.mutation_type == StepMutationType.DELETE_STEP and m.delete_step_id}
        # 同一 step_id 不可被同時 inject 又 delete
        if injected & deleted:
            return False
        return True
