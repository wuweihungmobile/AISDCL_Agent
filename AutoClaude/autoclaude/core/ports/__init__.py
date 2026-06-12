"""autoclaude.core.ports — DAL/Adapter 介面集合（SD_Improving_02.md v1.1 §1.2）。

對應 SD_Improving_01.md v1.1 §3.3 Layer 2 Core / Domain：
  - IExecutor    — Claude Code 執行介面（PtyExecutor / DryRunExecutor 實作）
  - IEvaluator   — 步驟成功評估介面（ShellEvaluator 實作）
  - IBrain       — Minimax 決策介面（MinimaxBrainAdapter 實作）

設計原則（SD_Improving_01.md v1.1 §3.4 / §3.9）：
  - 純 Protocol，零依賴，零實作
  - 任一 Adapter 實作必須通過契約測（Phase 5 才落地，Phase 1 預留）
"""
from .executor import IExecutor, ExecutionOutput
from .evaluator import IEvaluator
from .brain import IBrain, CorrectionResult
from .state_repository import (
    IStateRepository,
    IQueryableStateRepository,
    StateRepositoryError,
)
from .memory_store import IMemoryStore
from .playbook_repository import IPlaybookRepository
from .observability import IObservabilityPort, ISpan, NullObservability

__all__ = [
    "IExecutor", "ExecutionOutput",
    "IEvaluator",
    "IBrain", "CorrectionResult",
    # Phase 5 DAL
    "IStateRepository", "IQueryableStateRepository", "StateRepositoryError",
    "IMemoryStore",
    "IPlaybookRepository",
    # SD_Improving_08 W4 / ADR-SD08-004
    "IObservabilityPort", "ISpan", "NullObservability",
]
