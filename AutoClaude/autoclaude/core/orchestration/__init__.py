"""OrchestrationCoordinator — Layer 1.5 協調層（SD_Improving_06 W1）。

對應 ADR-SD06-001：
  - Layer 1.5：單一 step 內 Brain / Executor 協調
  - 6 phase 序：BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC
  - 不可訂閱 / emit Layer 2 事件（如 ON_AUTO_RESUME_WAKE）
"""
from .coordinator import (
    CoordinatorResult,
    MaxActiveRunsExceeded,
    OrchestrationCoordinator,
    PhaseOrderViolation,
)

__all__ = [
    "CoordinatorResult",
    "MaxActiveRunsExceeded",
    "OrchestrationCoordinator",
    "PhaseOrderViolation",
]
