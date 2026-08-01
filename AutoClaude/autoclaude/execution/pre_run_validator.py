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
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from ..utils.trace_context import propagate_to_subprocess_env

# Gap-009-B 假陰性修復（Mac/Windows 相容性 R52）：evaluator_command 的主命令若
# 為 "python"/"python3"，且 shutil.which() 解析到的路徑落在 WindowsApps 目錄下，
# 該路徑多半是 Windows 系統自動註冊的 App Execution Alias 空殼——`shutil.which()`
# 找得到、但實際執行只會跳出 Microsoft Store 安裝提示，不會執行任何 Python 碼。
# 權威定義見 tools/bootstrap_core.py::_is_windows_apps_stub()（monorepo 根層
# bootstrap 階段既有 guard，pick_python() 已用其排除同款空殼）；`autoclaude` 為
# 可獨立 pip 安裝的套件，不可依賴 monorepo 根層 tools/*.py（同一理由記載於
# autoclaude/utils/logger.py 頂部 `_sanitize_log_filename` 註解），故本檔獨立
# 維護一份判斷邏輯（與 boot_helper.py 共用本函式，非各自重寫）。
_WINDOWS_APPS_STUB_BINARIES = frozenset({"python", "python3"})


def _is_windows_apps_alias_stub(resolved_path: str) -> bool:
    """resolved_path（shutil.which() 回傳值）是否落在 WindowsApps 目錄下。"""
    return any(
        part.lower() == "windowsapps" for part in PureWindowsPath(resolved_path).parts
    )


# R68 修復：原本是 `binary.lower() in _WINDOWS_APPS_STUB_BINARIES` 的精確字串比對，對
# Windows 慣用的 `python.exe`／`python3.exe`／`Python.EXE` 拼法全部漏判 → guard 整條被
# 跳過（實測：同一個 WindowsApps 空殼路徑，`python` 回 block、`python.exe` 回零 issue）。
# 改比對 `PureWindowsPath(binary).stem`，同時涵蓋副檔名與大小寫變體，並額外涵蓋 playbook
# 直接寫完整路徑（`C:\...\WindowsApps\python.exe -m pytest`）的情形。**scope 不放寬**：
# `pytest.exe` 的 stem 是 `pytest`、不在集合內，tests/test_gap009.py::
# test_non_python_binary_in_windowsapps_dir_not_flagged 的偽陽性鎖仍綠。用 PureWindowsPath
# 而非 Path 是為了讓 mac/Linux 上跑的單元測試也能正確拆解反斜線路徑（同上方 stub 判斷）。
def _is_stub_candidate_binary(binary: str) -> bool:
    """playbook 寫的 binary 名（自由文字）是否為 WindowsApps 空殼候選名稱。"""
    return PureWindowsPath(binary).stem.lower() in _WINDOWS_APPS_STUB_BINARIES


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
        evaluator_command: str | None,
        task_prompt: str,  # 預留：未來驗證邏輯可引用 prompt 內容
    ) -> list[PreRunIssue]:
        issues: list[PreRunIssue] = []
        if not evaluator_command:
            return issues
        issues.extend(self._check_evaluator_command(evaluator_command))
        issues.extend(self._check_test_file_syntax(evaluator_command))
        return issues

    def _check_evaluator_command(self, command: str) -> list[PreRunIssue]:
        """驗證 evaluator_command 的主命令是否存在（shutil.which），並排除
        Windows WindowsApps App Execution Alias 空殼（假陰性修復，見上方
        `_is_windows_apps_alias_stub` 註解）。"""
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return []
        binary = cmd_parts[0]
        resolved = shutil.which(binary)
        if resolved is None:
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
        if _is_stub_candidate_binary(binary) and _is_windows_apps_alias_stub(resolved):
            return [PreRunIssue(
                severity="block",
                category="evaluator_missing",
                message=(
                    f"evaluator_command 的命令 '{binary}' 解析到 Windows "
                    f"WindowsApps App Execution Alias 空殼（{resolved}），"
                    f"並非真正安裝的直譯器。"
                ),
                strategy_hint=(
                    f"⚠️ Playbook 配置問題：evaluator_command '{command}' 中的命令 "
                    f"'{binary}' 解析到 Windows Store App Execution Alias 空殼\n"
                    f"（{resolved}），實際執行只會跳出 Store 安裝提示，不會真正執行。\n"
                    f"請安裝真正的 Python（或改用 venv 內的直譯器路徑）後再執行任務。"
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
                    [sys.executable, "-m", "py_compile", test_file],
                    capture_output=True, text=True, timeout=10,
                    encoding="utf-8", errors="replace",
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
