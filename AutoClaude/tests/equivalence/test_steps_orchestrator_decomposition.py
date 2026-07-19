"""
SD_07 W1: steps_orchestrator/_impl.py 拆解後行為等價測試

驗證項目（≥ 8 case）：
1. `_escalation_handler.py` 公開 API 存在
   （handle_convergence_escalation / handle_max_retries_escalation）
2. `_correction_helpers.py` 公開 API 存在（apply_step_mutations / validate_and_retry_correction）
3. `_escalation_handler._handle_goal_synthesis_recovery` private helper 存在
4. 模組 import 不引入額外副作用（top-level import 無錯誤）
5. `apply_step_mutations` 回傳 `_MutationApplyOutcome` dataclass，五旗標皆 default 為「無事」
6. `_impl.py` 不再含 escalation / mutation_apply / validate_retry 原始邏輯標記
7. LOC 政策：`_impl.py` 邏輯行 ≤ 500（service tier 上限）
8. _impl.py 透過正確 import path 引用拆出子模組（local import 模式）

不在範圍：
- 完整 e2e 行為（已由 tests/equivalence/test_kernel_snapshot.py 等覆蓋）
- 個別 escalation branch 的回歸（由現有 1,828 case 覆蓋）
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# Test 1-3：拆解後子模組公開 API
# ──────────────────────────────────────────────────────────────


def test_escalation_handler_exposes_convergence_api():
    """_escalation_handler.handle_convergence_escalation 存在且為 callable"""
    from autoclaude.execution.steps_orchestrator import _escalation_handler
    assert hasattr(_escalation_handler, "handle_convergence_escalation")
    fn = _escalation_handler.handle_convergence_escalation
    assert callable(fn)
    # 簽名包含關鍵參數（keyword-only）
    sig = inspect.signature(fn)
    expected = {
        "runner", "playbook", "playbook_path", "task", "step_idx", "tracker",
        "convergence_trend", "convergence_reasoning", "eval_output", "error_cls",
        "step_log", "workflow", "total", "mutation_log", "completed_step_ids",
        "step_evolution_counter",
    }
    assert expected.issubset(set(sig.parameters.keys()))


def test_escalation_handler_exposes_max_retries_api():
    """_escalation_handler.handle_max_retries_escalation 存在且為 callable"""
    from autoclaude.execution.steps_orchestrator import _escalation_handler
    assert hasattr(_escalation_handler, "handle_max_retries_escalation")
    fn = _escalation_handler.handle_max_retries_escalation
    assert callable(fn)
    sig = inspect.signature(fn)
    expected = {
        "runner", "playbook", "playbook_path", "task", "step_idx", "tracker",
        "max_retries", "eval_output", "error_cls", "failure_reason",
        "step_log", "workflow", "total", "mutation_log", "completed_step_ids",
        "step_evolution_counter",
    }
    assert expected.issubset(set(sig.parameters.keys()))


def test_correction_helpers_exposes_public_api():
    """_correction_helpers 公開 apply_step_mutations + validate_and_retry_correction"""
    from autoclaude.execution.steps_orchestrator import _correction_helpers
    assert hasattr(_correction_helpers, "apply_step_mutations")
    assert hasattr(_correction_helpers, "validate_and_retry_correction")
    assert callable(_correction_helpers.apply_step_mutations)
    assert callable(_correction_helpers.validate_and_retry_correction)


# ──────────────────────────────────────────────────────────────
# Test 4：GOAL_SYNTHESIS 共用 helper
# ──────────────────────────────────────────────────────────────


def test_escalation_handler_has_goal_synthesis_recovery_helper():
    """_handle_goal_synthesis_recovery 私有 helper 共用於收斂 + 重試耗盡兩路徑"""
    from autoclaude.execution.steps_orchestrator import _escalation_handler
    assert hasattr(_escalation_handler, "_handle_goal_synthesis_recovery")
    fn = _escalation_handler._handle_goal_synthesis_recovery
    sig = inspect.signature(fn)
    # convergence_label 參數區分兩路徑
    assert "convergence_label" in sig.parameters
    assert "max_retries" in sig.parameters


# ──────────────────────────────────────────────────────────────
# Test 5：_MutationApplyOutcome 預設值
# ──────────────────────────────────────────────────────────────


def test_mutation_apply_outcome_defaults():
    """_MutationApplyOutcome 五旗標 default 皆為「無事」（None / False）"""
    from autoclaude.execution.steps_orchestrator._correction_helpers import _MutationApplyOutcome
    outcome = _MutationApplyOutcome()
    assert outcome.early_return is None
    assert outcome.inject_before_pending is False
    assert outcome.goto_target_idx is None
    assert outcome.clear_goal_summary is False
    assert outcome.should_break is False


# ──────────────────────────────────────────────────────────────
# Test 6：_impl.py 不再含原始 inline 邏輯標記
# ──────────────────────────────────────────────────────────────


def test_impl_no_inline_escalation_logic():
    """_impl.py 不再 inline escalation / mutation_apply / validate_retry 邏輯"""
    impl = Path("autoclaude/execution/steps_orchestrator/_impl.py").read_text(encoding="utf-8")
    # 兩個 escalation 區塊已外移：不應再含 GOAL_SYNTHESIS recovery / Gap-048 inline 文字
    assert "GOAL_SYNTHESIS ESCALATION（重試耗盡）：MinimaxEvolver 已補完步驟" not in impl
    assert "GOAL_SYNTHESIS ESCALATION（收斂）：MinimaxEvolver 已補完步驟" not in impl
    # mutation apply 已外移
    assert "Gap-019-B | [%s] 批次突變" not in impl
    # validate_and_retry 已外移
    assert "Gap-008-D | 品質驗證失敗" not in impl
    # 但應有對應 delegate import 字串
    assert "_escalation_handler" in impl
    assert "_correction_helpers" in impl


# ──────────────────────────────────────────────────────────────
# Test 7：LOC 政策 — _impl.py ≤ 500（透過 check_loc_budget.py classifier）
# ──────────────────────────────────────────────────────────────


def test_impl_loc_within_service_tier():
    """_impl.py 邏輯行 ≤ 500（service tier 上限，依 ADR-SD07-001）"""
    from tools.check_loc_budget import classify_file, count_loc

    impl_path = Path("autoclaude/execution/steps_orchestrator/_impl.py")
    tier_name, budget = classify_file(impl_path)
    assert tier_name == "service", f"_impl.py 應分類為 service tier，實得 {tier_name}"
    assert budget == 500
    loc = count_loc(impl_path)
    assert loc <= 500, f"_impl.py 邏輯行 {loc} 超過 service tier budget 500"


# ──────────────────────────────────────────────────────────────
# Test 8：_impl.py 透過 local import 引用拆出子模組
# ──────────────────────────────────────────────────────────────


def test_impl_uses_local_import_for_decomposed_modules():
    """_impl.py 採 function-local import 引用拆出模組（避免 top-level 循環依賴）"""
    impl = Path("autoclaude/execution/steps_orchestrator/_impl.py").read_text(encoding="utf-8")
    # 引用形式：from ._escalation_handler import / from ._correction_helpers import
    assert "from ._escalation_handler import handle_convergence_escalation" in impl
    assert "from ._escalation_handler import handle_max_retries_escalation" in impl
    assert "from ._correction_helpers import apply_step_mutations" in impl
    assert "from ._correction_helpers import validate_and_retry_correction" in impl


# ──────────────────────────────────────────────────────────────
# Test 9：模組 top-level import 不引入額外副作用（smoke）
# ──────────────────────────────────────────────────────────────


def test_decomposed_modules_import_cleanly():
    """新增子模組 top-level import 不應觸發 ImportError 或副作用"""
    result = subprocess.run(
        [
            sys.executable, "-c",
            "import autoclaude.execution.steps_orchestrator._escalation_handler; "
            "import autoclaude.execution.steps_orchestrator._correction_helpers; "
            "print('OK')",
        ],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    assert result.returncode == 0, f"import 失敗：{result.stderr}"
    assert "OK" in result.stdout
