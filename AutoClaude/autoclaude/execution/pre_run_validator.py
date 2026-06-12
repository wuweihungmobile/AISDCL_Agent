"""
PreRunValidator — 在每個 step 的第一次 attempt 前，
預先掃描已知可驗證的錯誤來源，節省 Claude Code 執行時間。

Gap-009-B：在 EXECUTE 前攔截「必然失敗」的情況：
  1. evaluator_command 的主命令不在 PATH（Playbook typo）
  2. evaluator_command 引用的測試檔本身有語法錯誤
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..utils.trace_context import propagate_to_subprocess_env


@dataclass
class PreRunIssue:
    severity: str       # "block" | "warn"
    category: str       # "test_syntax" | "evaluator_missing" | "file_not_found"
    message: str
    strategy_hint: str  # 直接注入 prompt 的硬性約束
    affected_file: str = ""


class PreRunValidator:
    """
    在執行 Claude Code 前進行快速靜態驗證。
    發現 "block" 級問題時，呼叫方可用 strategy_hint 替代首次 Prompt，
    讓 Claude 先修復阻斷問題再執行原始任務。
    """

    def validate_step(
        self,
        evaluator_command: Optional[str],
        task_prompt: str,  # 預留：未來驗證邏輯可引用 prompt 內容
    ) -> list[PreRunIssue]:
        issues: list[PreRunIssue] = []
        if not evaluator_command:
            return issues
        issues.extend(self._check_evaluator_command(evaluator_command))
        issues.extend(self._check_test_file_syntax(evaluator_command))
        return issues

    def _check_evaluator_command(self, command: str) -> list[PreRunIssue]:
        """驗證 evaluator_command 的主命令是否存在（shutil.which）。"""
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return []
        binary = cmd_parts[0]
        if shutil.which(binary) is None:
            return [PreRunIssue(
                severity="block",
                category="evaluator_missing",
                message=(
                    f"evaluator_command 的命令 '{binary}' 不在 PATH 中，"
                    f"Playbook 配置可能有誤（typo 或工具未安裝）。"
                ),
                strategy_hint=(
                    f"⚠️ Playbook 配置問題：evaluator_command '{command}' "
                    f"中的命令 '{binary}' 不在 PATH 中。\n"
                    f"請先確認命令名稱是否正確（如 'pytest' 而非 'pytset'），"
                    f"或安裝所需工具後再執行任務。"
                ),
            )]
        return []

    def _check_test_file_syntax(self, command: str) -> list[PreRunIssue]:
        """從 evaluator_command 萃取 Python 測試檔路徑，預先 py_compile 驗證語法。"""
        path_pattern = re.compile(
            r'((?:[a-zA-Z0-9_\-]+[/\\])*(?:test_\w+|\w+_test)\.py'
            r'|tests?[/\\](?:[a-zA-Z0-9_\-/\\]*(?:test_\w+|\w+_test)\.py))',
            re.IGNORECASE,
        )
        issues: list[PreRunIssue] = []
        for m in path_pattern.finditer(command):
            test_file = m.group(1).replace('\\', '/')
            if not Path(test_file).exists():
                continue
            try:
                result = subprocess.run(
                    ["python", "-m", "py_compile", test_file],
                    capture_output=True, text=True, timeout=10,
                    env=propagate_to_subprocess_env(dict(os.environ)),
                )
                if result.returncode != 0:
                    issues.append(PreRunIssue(
                        severity="block",
                        category="test_syntax",
                        message=f"Pre-Run 驗證：{test_file} 有語法錯誤（py_compile 失敗）",
                        strategy_hint=(
                            f"🚫 Pre-Run 硬性約束：在開始實作前，"
                            f"{test_file} 已有語法錯誤，必須先修復。\n"
                            f"第一步：修復 {test_file} 的以下語法錯誤：\n"
                            f"{result.stderr[:300]}\n\n"
                            f"修復語法錯誤後，再繼續執行原始任務。"
                        ),
                        affected_file=test_file,
                    ))
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return issues
