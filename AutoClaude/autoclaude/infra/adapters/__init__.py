"""autoclaude.infra.adapters — Port 介面的具體實作（Layer 1）。

設計原則：
  - 每個 Adapter 是「薄包裝」（thin wrapper），無業務邏輯
  - 所有業務邏輯在 Layer 2 Core（Kernel + MutationApplyService + EventBus + Plugin）
  - Phase 1 期間 Adapter 與舊 PlaybookRunner._evaluate / _execute_prompt 並存
"""
from .pty_executor import PtyExecutor
from .shell_evaluator import ShellEvaluator
from .minimax_brain import MinimaxBrainAdapter

__all__ = ["PtyExecutor", "ShellEvaluator", "MinimaxBrainAdapter"]
