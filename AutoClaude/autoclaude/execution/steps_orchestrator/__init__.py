"""steps_orchestrator package — _run_steps 拆解承接（SD_06 W2-T2-1 / T2-2 / AC1-2 per-file 拆分）。

對應：
  - SD_Improving_06.md v1.2 §6.5 AC1-2（strategy 模組 each ≤ 250 LOC）
  - SD_Improving_06.md v1.2 §4 W2（_runner_internals.py god-class 拆解）
  - SD06_Execution_Guide.md W2

子模組：
  - _context.py — ExecutionContext dataclass + StepsOrchestrator skeleton（128 LOC）
  - _impl.py    — run_steps_impl 主體（870 行；W3+ 進一步按邏輯區塊拆分為
                   context_negotiation / step_loop / correction_loop / mutation_dispatch /
                   evolution_trigger 5 子模組，預計各 ≤ 200 LOC）

backward compat：
  原 `from autoclaude.execution.steps_orchestrator import (run_steps_impl, ExecutionContext,
  StepsOrchestrator)` 仍可使用（透過本 __init__.py re-export）。
"""
from ._context import ExecutionContext, StepsOrchestrator
from ._impl import run_steps_impl

__all__ = ["ExecutionContext", "StepsOrchestrator", "run_steps_impl"]
