"""autoclaude.core.ports — DAL/Adapter 介面集合（SD_Improving_02.md v1.1 §1.2）。

對應 SD_Improving_01.md v1.1 §3.3 Layer 2 Core / Domain：
  - IExecutor    — Claude Code 執行介面（PtyExecutor / DryRunExecutor 實作）
  - IEvaluator   — 步驟成功評估介面（ShellEvaluator 實作）
  - IBrain       — Minimax 決策介面（MinimaxBrainAdapter 實作）

設計原則（SD_Improving_01.md v1.1 §3.4 / §3.9）：
  - 純 Protocol，零依賴，零實作
  - 任一 Adapter 實作必須通過契約測（Phase 5 才落地，Phase 1 預留）
"""
from .brain import CorrectionResult, IBrain
from .evaluator import IEvaluator
from .executor import ExecutionOutput, IExecutor
from .kb_metric_store import IKbMetricStore, MetricValue
from .memory_store import IMemoryStore
from .observability import IObservabilityPort, ISpan, NullObservability
from .playbook_repository import IPlaybookRepository
from .preference_store import IPreferenceStore
from .state_repository import (
    IQueryableStateRepository,
    IStateRepository,
    StateRepositoryError,
)

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
    # Improving_012 Phase 1（F-C3 / F-C1；ADR-SD09-006 / ADR-AGT-003）
    "IKbMetricStore", "MetricValue",
    "IPreferenceStore",
]
