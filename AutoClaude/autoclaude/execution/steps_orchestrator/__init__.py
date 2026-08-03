"""steps_orchestrator package — _run_steps 拆解承接（SD_06 W2-T2-1 / T2-2 / AC1-2 per-file 拆分）。

對應：
  - SD_Improving_06.md v1.2 §6.5 AC1-2（strategy 模組 each ≤ 250 LOC）
  - SD_Improving_06.md v1.2 §4 W2（_runner_internals.py god-class 拆解）
  - SD06_Execution_Guide.md W2

子模組：
  - _context.py — ExecutionContext dataclass
  - _impl.py    — run_steps_impl 主體（870 行；W3+ 進一步按邏輯區塊拆分為
                   context_negotiation / step_loop / correction_loop / mutation_dispatch /
                   evolution_trigger 5 子模組，預計各 ≤ 200 LOC）

backward compat：
  原 `from autoclaude.execution.steps_orchestrator import (run_steps_impl, ExecutionContext)`
  仍可使用（透過本 __init__.py re-export）。同批曾 re-export 的 StepsOrchestrator 為
  W2 預留的 skeleton 類別，全樹零呼叫端，已隨 _context.py 一併移除。
"""
from ._context import ExecutionContext
from ._impl import run_steps_impl

__all__ = ["ExecutionContext", "run_steps_impl"]
