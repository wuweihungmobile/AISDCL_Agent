"""ConditionalStrategy（IMutationStrategy 之一，Gap-021）。

職責：
  - 依 ``condition_evaluator`` 的 exit code 選擇 true_mutation / false_mutation 分支
  - 將選中的分支突變遞迴交回 MutationApplyService.apply 處理
  - 三層縱深防禦：
      (1) 白名單字元 regex（Gap-046）
      (2) 黑名單字元拒絕（!/`/>/</~/$）
      (3) 預設 evaluator 使用 ``shell=False`` + ``shlex.split``，根絕 shell 介入
  - 巢狀 CONDITIONAL 上限：遞迴深度 > 4 直接拒絕，防 IO 風暴（SD_05 W4 SD-M1）

跨平台注意（R16 P2；比照 execution/evaluator.py Evaluator.run 的可攜指令慣例）：
``_SHELL_FALSE_COND_WHITELIST`` 白名單刻意不含反斜線，Windows 風格路徑（如
``C:\\path\\to\\check.py``）會被拒絕並記警告（見 ``apply()``）。condition_evaluator
若需寫路徑，請一律用正斜線（``C:/path/to/check.py``，Windows API 原生接受）；
不要放寬白名單去接受反斜線 —— ``_default_evaluator`` 用 POSIX 模式
``shlex.split``，反斜線會被當跳脫字元吃掉、把路徑拆爛而非清楚拒絕
（見 ``_conditional_evaluator.py`` docstring）。

設計原則：
  - 為維持 Layer 2 純度，subprocess 透過注入的 ``evaluator`` callable 執行
  - shell 安全層拆至 ``_conditional_evaluator.py``（W4 三方審查 LOC ≤ 80 預算）
  - counter increment 不在此處理（GotoCounterPlugin 統一維護）

行數預算：本檔 ≤ 80 行。
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from ....models.playbook import Playbook
from ....models.step_mutation import StepMutation, StepMutationType
from ._conditional_evaluator import (
    _DENY_CHARS,
    _SHELL_FALSE_COND_WHITELIST,
    _default_evaluator,
)

if TYPE_CHECKING:
    from .service import MutationApplyService

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 30
# SD_05 W4 SD-M1：巢狀 CONDITIONAL 深度上限（防 IO 風暴 / stack 爆炸）
_MAX_RECURSION_DEPTH = 4


class ConditionalStrategy:
    """Gap-021：條件式分支突變。"""

    def __init__(
        self,
        evaluator: Callable[[str, int], int] | None = None,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    ):
        self._evaluator = evaluator or _default_evaluator
        self._timeout = timeout_seconds
        self._service: MutationApplyService | None = None

    def _set_service(self, service: MutationApplyService) -> None:
        """由 MutationApplyService 於建構末注入自身（避免循環依賴）。

        TODO(SD_05 W6 / SA-M3)：W6 改 constructor 必填參數。
        """
        self._service = service

    def kind(self) -> str:
        return StepMutationType.CONDITIONAL.value

    def can_handle(self, mutation: StepMutation) -> bool:
        return mutation.mutation_type == StepMutationType.CONDITIONAL

    def apply(
        self,
        mutation: StepMutation,
        playbook: Playbook,
        current_idx: int,
        _depth: int = 0,
    ) -> bool:
        """SD_05 W4 SD-M1：``_depth`` 為內部巢狀計數，超過 _MAX_RECURSION_DEPTH 拒絕。"""
        if _depth > _MAX_RECURSION_DEPTH:
            logger.warning(
                "ConditionalStrategy | 巢狀深度超過上限 %d，拒絕執行",
                _MAX_RECURSION_DEPTH,
            )
            return False
        if not mutation.condition_evaluator:
            return False
        cmd = mutation.condition_evaluator.strip()
        if not cmd or not _SHELL_FALSE_COND_WHITELIST.match(cmd):
            # R16 P2：對齊姊妹實作 execution/mutation_applier/_conditional.py 的
            # 警告訊息（原本靜默拒絕，Windows 路徑如 C:\path\to\check.py 因白名單
            # 不含反斜線被拒時完全無跡可尋，難以除錯）。
            logger.warning(
                "=== Gap-046 | CONDITIONAL evaluator 包含不安全字符，略過: %s ===",
                cmd[:80],
            )
            return False
        if any(ch in _DENY_CHARS for ch in cmd):
            logger.warning(
                "=== Gap-046 | CONDITIONAL evaluator 包含不安全字符，略過: %s ===",
                cmd[:80],
            )
            return False
        exit_code = self._evaluator(cmd, self._timeout)
        branch = mutation.true_mutation if exit_code == 0 else mutation.false_mutation
        if branch is None:
            return True
        if self._service is None:
            return False
        if branch.mutation_type == StepMutationType.CONDITIONAL:
            return self.apply(branch, playbook, current_idx, _depth=_depth + 1)
        return self._service.apply(branch, playbook, current_idx)
