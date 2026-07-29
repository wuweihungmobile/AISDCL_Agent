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

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ps_engine import any_engine_available, production_engine  # noqa: E402  # R60 E-A-03

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEV_START_PS1 = _REPO_ROOT / "tools" / "dev_start.ps1"


@unittest.skipIf(
    not any_engine_available(),  # R60 E-A-03：語意② SSOT 述詞
    "需要 powershell/pwsh",
)
class TestDevStartPs1DotSourceLastExitCode(unittest.TestCase):
    def _run(self) -> subprocess.CompletedProcess:
        exe = production_engine()  # R60 E-A-03：5.1 優先（DEF-101-509 判準）
        # R42 修復（DEF-101-350）：本機真實 Windows 11 開發機已有真實 `.venv`，
        # dev_start.ps1 的 `$VenvPy = Join-Path $Root '.venv\Scripts\python.exe'`
        # 用 Test-Path 短路判斷排在 PATH 查詢之前——原本只清空 PATH 的手法在「本
        # repo 目前開發中、已有真實 .venv」的機器上完全觸發不到「找不到 Python」
        # 分支（`Test-Path $VenvPy` 恆真，PATH 清空與否已不相關）。改把
        # dev_start.ps1 複製到隔離的臨時 `tools/` 目錄下執行（`$PSScriptRoot` 因而
        # 解析到臨時 $Root，`$VenvPy` 保證不存在），比照本 repo 既有 WindowsApps
        # guard 測試的臨時目錄隔離慣例，不依賴真實開發機器上是否已有 `.venv`。
        with tempfile.TemporaryDirectory() as td:
            tmp_tools = Path(td) / "tools"
            tmp_tools.mkdir()
            tmp_ps1 = tmp_tools / "dev_start.ps1"
            tmp_ps1.write_text(_DEV_START_PS1.read_text(encoding="utf-8"), encoding="utf-8")
            # dev_start.ps1 用相對路徑 dot-source `lib/WindowsAppsGuard.ps1`，
            # 隔離目錄需一併複製，否則 dot-source 找不到檔案會在抵達
            # 「找不到 Python」分支之前就先拋出無關的腳本錯誤。
            tmp_lib = tmp_tools / "lib"
            tmp_lib.mkdir()
            guard_src = _REPO_ROOT / "tools" / "lib" / "WindowsAppsGuard.ps1"
            (tmp_lib / "WindowsAppsGuard.ps1").write_text(
                guard_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
            # PATH 只留最基本目錄，排除任何 py/python 候選，穩定觸發
            # 「找不到 Python 直譯器」這條 dot-source 失敗分支。
            # [Console]::OutputEncoding 設 UTF-8（R42 修復，DEF-101-350）：本機
            # 為繁體中文 Windows（Big5/950 codepage），dev_start.ps1 的中文錯誤
            # 訊息若不明確指定輸出編碼會被以錯誤 codepage 解讀成亂碼，斷言
            # 因而誤判失敗——同一根因/同一修法比照本輪稍早
            # test_install_post_commit_windowsapps_guard.py::_run_with_shadowed_python()
            # 的既有修復。
            cmd = (
                '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; '
                '$env:PATH = "/usr/bin:/bin"; '
                f". '{tmp_ps1}'; "
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
