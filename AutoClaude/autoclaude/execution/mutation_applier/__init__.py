"""mutation_applier package — _apply_single_mutation_full 拆解（SD_06 W2 G2 deferred 收尾）。

對應：
  - SD_Improving_06.md v1.2 §4 W2-2（apply / verify / persist；each ≤ ~100 LOC）
  - SD_Improving_06.md v1.2 §6.5 AC1-2（strategy 模組 each ≤ 250 LOC）

子模組（4 個，全部 ≤ 200 LOC）：
  - _dispatcher.py        — MutationCtx + apply_single_mutation_full_impl（主分發）
  - _simple_mutations.py  — REVISE_CURRENT / INJECT_AFTER / DELETE_STEP / SKIP_TO
  - _complex_mutations.py — INJECT_BEFORE / GOTO_STEP（含 escalation/evolution）
  - _conditional.py       — CONDITIONAL（含 shell 安全 + 遞迴 dispatch）

backward compat：
  原 `from autoclaude.execution.mutation_applier import apply_single_mutation_full_impl`
  仍可使用（透過本 __init__.py re-export）。
"""
from ._dispatcher import MutationCtx, apply_single_mutation_full_impl

__all__ = ["MutationCtx", "apply_single_mutation_full_impl"]
