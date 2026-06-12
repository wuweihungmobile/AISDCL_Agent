"""MutationApplyService — Layer 2 Domain Service（SD_Improving_01.md v1.1 §3.5）。

職責：
  - 以 7 個 IMutationStrategy 處理 7 種 StepMutationType
  - 由 Kernel 直接呼叫（非 Plugin）
  - 對 Playbook 進行就地修改

每個 Strategy ≤ 80 行（行數預算 CI 強制，01 v1.1 §3.13.1）。
"""
from .service import MutationApplyService
from .revise_current import ReviseCurrentStrategy
from .inject_after import InjectAfterStrategy
from .inject_before import InjectBeforeStrategy
from .goto_step import GotoStepStrategy
from .skip_to import SkipToStrategy
from .delete_step import DeleteStepStrategy
from .conditional import ConditionalStrategy
from .noop import NoOpStrategy

__all__ = [
    "MutationApplyService",
    "ReviseCurrentStrategy",
    "InjectAfterStrategy",
    "InjectBeforeStrategy",
    "GotoStepStrategy",
    "SkipToStrategy",
    "DeleteStepStrategy",
    "ConditionalStrategy",
    "NoOpStrategy",
]
