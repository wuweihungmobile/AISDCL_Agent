"""tests/tools/test_shim_check.py — check_frozen_surface_shim.py 驗證工具測試（SD_03 §2.2, W5 更新）。

驗證：
  1. 正常 shim 通過（含 W5 新模式：_evaluate 直接委派 _runner_compat）
  2. 缺少 orchestrator check 的 _apply_single_mutation 被拒絕
  3. 4+ statements 的方法被拒絕
  4. 缺少 shim 方法被拒絕
  5. 整合測試：對真實 playbook_runner.py 執行全部通過
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

# 加入 tools 目錄到 sys.path
TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from check_frozen_surface_shim import (
    _check_shim, SHIM_METHODS, REQUIRES_ORCHESTRATOR_CHECK, RUNNER_PATH
)


def _parse_method(src: str) -> ast.FunctionDef:
    """解析單一 method 定義。"""
    tree = ast.parse(src.strip())
    return tree.body[0]


class TestCheckShim:
    """_check_shim() 單元測試（W5 更新）。"""

    def test_valid_shim_with_super_passes(self):
        """標準 2-statement shim（orchestrator check + super()）通過。"""
        src = """
def _apply_single_mutation(self, mutation, playbook, *args, **kwargs):
    if self._orchestrator:
        return self._orchestrator.kernel.mutation_service.apply(mutation, playbook, 0)
    return super()._apply_single_mutation(mutation, playbook, *args, **kwargs)
"""
        method = _parse_method(src)
        errors = _check_shim(method)
        assert errors == [], f"預期通過，但有錯誤: {errors}"

    def test_valid_evaluate_direct_delegation_passes(self):
        """W5: _evaluate 直接呼叫 _runner_compat（1 statement，無 orchestrator check）通過。"""
        src = """
def _evaluate(self, task, output):
    return _evaluate_impl(task, output)
"""
        method = _parse_method(src)
        errors = _check_shim(method)
        assert errors == [], f"預期通過，但有錯誤: {errors}"

    def test_valid_batch_compat_with_runner_compat_passes(self):
        """W5: _validate_batch_compatibility + _runner_compat 委派（非 super()）通過。"""
        src = """
def _validate_batch_compatibility(self, mutations):
    if self._orchestrator:
        return self._orchestrator.kernel.mutation_service.validate_batch(mutations)
    return _validate_batch_compatibility_impl(mutations)
"""
        method = _parse_method(src)
        errors = _check_shim(method)
        assert errors == [], f"預期通過，但有錯誤: {errors}"

    def test_too_many_statements_fails(self):
        """4+ statements 的方法被拒絕。"""
        src = """
def _apply_single_mutation(self, mutation, playbook, *args, **kwargs):
    x = 1
    y = 2
    if self._orchestrator:
        return self._orchestrator.kernel.mutation_service.apply(mutation, playbook, 0)
    return super()._apply_single_mutation(mutation, playbook, *args, **kwargs)
"""
        method = _parse_method(src)
        errors = _check_shim(method)
        assert len(errors) > 0, "應有錯誤（4 statements）"
        assert any("statements" in e for e in errors), f"應有 statement 數量錯誤: {errors}"

    def test_wrong_if_condition_fails(self):
        """_apply_single_mutation 缺少 self._orchestrator 條件被拒絕。"""
        src = """
def _apply_single_mutation(self, mutation, playbook, *args, **kwargs):
    if self._some_flag:
        return self._some_flag.apply(mutation, playbook, 0)
    return super()._apply_single_mutation(mutation, playbook, *args, **kwargs)
"""
        method = _parse_method(src)
        errors = _check_shim(method)
        assert any("_orchestrator" in e for e in errors), f"應有 if-條件錯誤: {errors}"

    def test_missing_orchestrator_check_for_required_shim_fails(self):
        """REQUIRES_ORCHESTRATOR_CHECK 中的 shim 缺少 if self._orchestrator 被拒絕。"""
        src = """
def _apply_single_mutation(self, mutation, playbook, *args, **kwargs):
    return super()._apply_single_mutation(mutation, playbook, *args, **kwargs)
"""
        method = _parse_method(src)
        errors = _check_shim(method)
        assert any("_orchestrator" in e for e in errors), f"應有 orchestrator check 錯誤: {errors}"

    def test_varargs_super_passes(self):
        """*args/**kwargs shim + super() 通過。"""
        src = """
def _apply_single_mutation(self, mutation, playbook, *args, **kwargs):
    if self._orchestrator:
        return self._orchestrator.kernel.mutation_service.apply(mutation, playbook, args[2] if len(args) > 2 else 0)
    return super()._apply_single_mutation(mutation, playbook, *args, **kwargs)
"""
        method = _parse_method(src)
        errors = _check_shim(method)
        assert errors == [], f"預期通過，但有錯誤: {errors}"

    def test_requires_orchestrator_check_contains_correct_methods(self):
        """REQUIRES_ORCHESTRATOR_CHECK 應包含 _apply_single_mutation 和 _validate_batch_compatibility。"""
        assert "_apply_single_mutation" in REQUIRES_ORCHESTRATOR_CHECK
        assert "_validate_batch_compatibility" in REQUIRES_ORCHESTRATOR_CHECK
        assert "_evaluate" not in REQUIRES_ORCHESTRATOR_CHECK


class TestShimCheckIntegration:
    """對真實 playbook_runner.py 執行整合驗證。"""

    def test_runner_file_exists(self):
        """playbook_runner.py 存在。"""
        assert RUNNER_PATH.exists(), f"找不到 {RUNNER_PATH}"

    def test_all_shim_methods_present(self):
        """PlaybookRunner 中包含所有 SHIM_METHODS。"""
        src = RUNNER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        runner_cls = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "PlaybookRunner"),
            None,
        )
        assert runner_cls is not None, "找不到 PlaybookRunner 類別"
        found = {n.name for n in runner_cls.body if isinstance(n, ast.FunctionDef)}
        missing = SHIM_METHODS - found
        assert not missing, f"PlaybookRunner 缺少 shim 方法: {missing}"

    def test_all_shims_pass_ast_check(self):
        """所有 shim 方法通過 AST 規則（W5 更新後）。"""
        src = RUNNER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        runner_cls = next(
            (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "PlaybookRunner"),
            None,
        )
        assert runner_cls is not None
        all_errors = []
        for node in runner_cls.body:
            if isinstance(node, ast.FunctionDef) and node.name in SHIM_METHODS:
                all_errors.extend(_check_shim(node))
        assert all_errors == [], "shim AST 驗證失敗:\n" + "\n".join(f"  • {e}" for e in all_errors)
