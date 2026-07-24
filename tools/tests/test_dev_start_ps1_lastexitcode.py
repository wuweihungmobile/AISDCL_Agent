#!/usr/bin/env python3
"""tools/dev_start.ps1 dot-source 失敗分支 $LASTEXITCODE 回歸鎖（DEF-101-304）。

`tools/dev_start.ps1` 的 `.NOTES` 明載「dot-source 呼叫端判斷成功/失敗請讀
$LASTEXITCODE，不要用 $?」，但早期失敗分支（找不到 repo 根／找不到 Python
直譯器）在 dot-source 情境下只執行裸 `return`，未對 `$LASTEXITCODE` 賦值——
呼叫前的殘值（可能是 0）會被誤判為成功。對等的 `tools/dev_start.sh` 用
`return 1` 正確傳遞失敗，兩邊在 exit code 語意上不對稱（R35 Scan-A 發現）。

本測試只驗證「找不到 Python 直譯器」這條分支（PATH 清空即可穩定觸發，
不依賴 Windows PATHEXT／`.cmd` 解析語意，pwsh 在 macOS/Linux/Windows 上
dot-source 與 `$LASTEXITCODE` 的語言層行為一致，故不比照
`test_bootstrap_ps1.py` 的 `_windows_pwsh_available()` 額外限定真 Windows）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEV_START_PS1 = _REPO_ROOT / "tools" / "dev_start.ps1"


@unittest.skipIf(
    shutil.which("powershell") is None and shutil.which("pwsh") is None,
    "需要 powershell/pwsh",
)
class TestDevStartPs1DotSourceLastExitCode(unittest.TestCase):
    def _run(self) -> subprocess.CompletedProcess:
        exe = shutil.which("powershell") or shutil.which("pwsh")
        # PATH 只留最基本目錄，排除任何 py/python/.venv 候選，穩定觸發
        # 「找不到 Python 直譯器」這條 dot-source 失敗分支。
        cmd = (
            '$env:PATH = "/usr/bin:/bin"; '
            f". '{_DEV_START_PS1}'; "
            'Write-Output "RC_AFTER=$LASTEXITCODE"'
        )
        return subprocess.run(
            [exe, "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )

    def test_python_not_found_sets_lastexitcode_nonzero_after_dot_source(self) -> None:
        """dot-source 情境下「找不到 Python」必須讓 $LASTEXITCODE 為非零值，
        修復前該分支只 `return`、$LASTEXITCODE 停留在呼叫前殘值（本測試以
        乾淨 pwsh 子行程執行，殘值恆為空字串，等同「看似成功」的誤判）。
        """
        proc = self._run()
        output = proc.stdout + proc.stderr
        self.assertIn("找不到", output, output)
        self.assertIn("RC_AFTER=1", output, output)
        self.assertNotIn("RC_AFTER=\n", output, output)


class TestDevStartPs1BothFailureBranchesSetLastExitCode(unittest.TestCase):
    """靜態一致性鎖，補齊上面行為測試的覆蓋盲區（R35 四方一審 Architect/QA/SD
    交叉獨立發現）：「找不到 Python」分支可用清空 PATH 穩定觸發並實際執行驗證，
    但同構的「找不到 repo 根」分支只在腳本被複製到磁碟根時才會觸發（見腳本
    第 26 行註解），無法在不需要磁碟根寫入權限的前提下安全地實際執行觸發。
    改用靜態文字比對鎖住兩個分支同時擁有修復，防止「只修一個分支」的回歸
    （SD 一審 bug-injection 證實：只還原其中一支修復，行為測試仍全綠）。
    """

    def test_both_dotsourced_failure_branches_set_lastexitcode_before_return(self) -> None:
        text = _DEV_START_PS1.read_text(encoding="utf-8")
        fixed = text.count("if ($DotSourced) { $global:LASTEXITCODE = 1; return }")
        bare = text.count("if ($DotSourced) { return }")
        self.assertEqual(
            fixed, 2,
            f"預期兩處 dot-source 失敗分支（找不到 repo 根／找不到 Python）皆設 "
            f"$LASTEXITCODE，實際命中 {fixed} 處",
        )
        self.assertEqual(
            bare, 0,
            "偵測到未設 $LASTEXITCODE 的裸 `if ($DotSourced) { return }`，"
            "回歸至修復前的失敗語意",
        )


if __name__ == "__main__":
    unittest.main()
