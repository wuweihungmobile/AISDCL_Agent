#!/usr/bin/env python
"""
check_frozen_surface_shim.py — M1 shim AST 驗證（SD_03 §2.2, W5 更新）

驗證 PlaybookRunner 中每個 M1 shim 方法：
  1. 每個 shim 方法必須存在（_evaluate / _apply_single_mutation / _validate_batch_compatibility）
  2. body 為 1~3 個 AST statement（合理範圍）
  3. _apply_single_mutation：必須包含 if self._orchestrator 條件檢查
  4. _evaluate：允許直接委派 _runner_compat 函式（不需 orchestrator check）

W5 変更（T-044）：
  - _evaluate 不再需要 super()，允許直接呼叫 _evaluate_impl
  - _apply_single_mutation 保留 if self._orchestrator + super() 模式
  - _validate_batch_compatibility 允許呼叫 _runner_compat 函式（非 super()）

使用：
  python tools/check_frozen_surface_shim.py        # 驗證（CI gate）
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = PROJECT_ROOT / "autoclaude" / "execution" / "playbook_runner.py"

# M1 shim 方法清單（SD_03 §2.2 表格 #1 / #2 / #3）
SHIM_METHODS = {"_evaluate", "_apply_single_mutation", "_validate_batch_compatibility"}

# 需要 orchestrator 條件檢查的 shim（W5：_evaluate 不需要）
REQUIRES_ORCHESTRATOR_CHECK = {"_apply_single_mutation", "_validate_batch_compatibility"}


def _has_orchestrator_check(body: list) -> bool:
    """body 中是否包含 if self._orchestrator 條件判斷。"""
    for stmt in body:
        if isinstance(stmt, ast.If):
            test = stmt.test
            if (
                isinstance(test, ast.Attribute)
                and isinstance(test.value, ast.Name)
                and test.value.id == "self"
                and test.attr == "_orchestrator"
            ):
                return True
    return False


def _check_shim(method: ast.FunctionDef) -> list[str]:
    """回傳此 shim 的所有違規訊息（空 list = 通過）。"""
    errors: list[str] = []
    name = method.name
    body = method.body

    # docstring 除外後的實際邏輯 body
    logic_body = [
        s for s in body
        if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
    ]

    # 規則 1：body 有 1~3 個 statements
    if len(logic_body) < 1 or len(logic_body) > 3:
        errors.append(
            f"{name}: logic body 應有 1~3 statements，實際 {len(logic_body)}"
        )
        return errors

    # 規則 2：需要 orchestrator check 的 shim 必須包含 if self._orchestrator
    if name in REQUIRES_ORCHESTRATOR_CHECK:
        if not _has_orchestrator_check(logic_body):
            errors.append(
                f"{name}: 必須包含 if self._orchestrator 條件檢查"
            )

    return errors


def main() -> int:
    # DEF-82-001/DEF-101-070 家族慣例：報表含中文/• 等非 ASCII，Windows cp950 console
    # 直接 print 會 UnicodeEncodeError 中斷；stdout + stderr 皆強制 utf-8。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass
    src = RUNNER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(RUNNER_PATH))

    # 找 PlaybookRunner 類別
    runner_cls: ast.ClassDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "PlaybookRunner":
            runner_cls = node
            break

    if runner_cls is None:
        print("ERROR: 找不到 PlaybookRunner 類別")
        return 1

    # 收集 PlaybookRunner 中的 shim 方法
    found: set[str] = set()
    all_errors: list[str] = []

    for node in runner_cls.body:
        if isinstance(node, ast.FunctionDef) and node.name in SHIM_METHODS:
            found.add(node.name)
            errs = _check_shim(node)
            all_errors.extend(errs)

    # 規則 3：所有 SHIM_METHODS 都必須存在
    missing = SHIM_METHODS - found
    for m in sorted(missing):
        all_errors.append(f"{m}: 找不到 shim 方法（PlaybookRunner 中未定義）")

    if all_errors:
        print("FAIL — M1 shim 驗證失敗：")
        for e in all_errors:
            print(f"  • {e}")
        return 1

    print(f"PASS — {len(found)} 個 M1 shim 全數符合規範（SD_03 §2.2 / W5）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
