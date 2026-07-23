#!/usr/bin/env python3
"""tools/bootstrap.ps1 的 Windows Store App Execution Alias 排除 guard 回歸鎖
（DEF-101-273：帳本原宣稱「新增針對性測試」但實際未落地，R27 二審前補齊，
避免宣稱與現況不符）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_PS1 = _REPO_ROOT / "tools" / "bootstrap.ps1"


@unittest.skipIf(
    shutil.which("powershell") is None and shutil.which("pwsh") is None,
    "需要 powershell/pwsh",
)
class TestBootstrapWindowsAppsGuard(unittest.TestCase):
    def _run(self, path_dirs: list[Path]) -> subprocess.CompletedProcess:
        # Windows PowerShell 5.1 的 Write-Host 預設走主控台 OEM/ANSI codepage 輸出
        # 中文，非 UTF-8；用 -Command 前置 [Console]::OutputEncoding 才能讓 Python
        # 端以 utf-8 正確解碼（同款陷阱見 windows_smoke_local.ps1 R10 註記）。
        exe = shutil.which("powershell") or shutil.which("pwsh")
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join(str(p) for p in path_dirs)
        cmd = (
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
            f"& '{_BOOTSTRAP_PS1}'"
        )
        return subprocess.run(
            [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, env=env,
        )

    def test_windowsapps_only_python_stub_is_skipped_and_reports_not_found(self) -> None:
        """PATH 上只有一個位於 WindowsApps 路徑下的 python.exe 空殼、無 py/python3
        時，bootstrap.ps1 必須跳過該空殼並回報「找不到 python」，而不是把空殼
        當真直譯器去呼叫 bootstrap_core.py（那樣只會跳出 Store 提示，永遠不會
        真正整備環境）。
        """
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td) / "WindowsApps"
            stub_dir.mkdir()
            (stub_dir / "python.exe").write_bytes(b"")
            proc = self._run([stub_dir])
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("找不到", proc.stdout + proc.stderr)

    def test_real_python_outside_windowsapps_is_used_even_when_windowsapps_stub_present_first(
        self,
    ) -> None:
        """WindowsApps 空殼與真直譯器同時在 PATH 上時（空殼排在前面），必須
        跳過空殼、採用後面真正的候選——證明 guard 是「排除」而非「一找到
        python 就用」的裸邏輯退化。

        R27 二審 QA 對抗式驗證揪出首版本此測試唯一斷言
        `assertNotIn("找不到 python/py/python3", ...)` 對「選中空殼後執行失敗」
        與「選中真候選後執行失敗」兩條路徑皆為真（皆不含「找不到」字樣）——
        對 bug-injection（改回舊版裸迴圈、誤選空殼）跑此測試**不會變紅**，屬
        裝飾性斷言、未真正背書 docstring 宣稱的「證明選中真候選」。改用
        `.cmd` 假直譯器（Windows PATHEXT 解析下 `Get-Command python3`／`& python3`
        皆會找到 `python3.cmd`，經實測確認）取代先前不可執行的 "MZ" 佔位位元
        組，令假直譯器被呼叫時印出唯一標記字串，正向斷言該標記真的出現——
        直接證明 bootstrap.ps1 選中並執行了 python3 這個候選，而非空殼（不
        斷言 exit code：實測 `-Command "& 'script.ps1'"` 這種巢狀呼叫下，內層
        腳本的 `exit N` 不會透傳成外層 powershell.exe 行程自身的 exit code
        〔最小 repro 確認：`exit 42` 單獨測試外層恆回 1〕，這是 `-Command`
        巢狀呼叫本身的獨立行為特性、非 bootstrap.ps1 缺陷，與本輪
        `GitHooksInstallCommon.ps1` 呼叫棧語意同屬「`-Command` 巢狀呼叫有
        自己一套規則」家族，不宜作為斷言依據，故本測試只驗證標記字串）。
        """
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td) / "WindowsApps"
            stub_dir.mkdir()
            (stub_dir / "python.exe").write_bytes(b"")
            real_dir = Path(td) / "real"
            real_dir.mkdir()
            fake = real_dir / "python3.cmd"
            fake.write_text("@echo off\r\necho FAKE_PYTHON3_INVOKED\r\nexit /b 42\r\n",
                             encoding="ascii")
            proc = self._run([stub_dir, real_dir])
            self.assertIn("FAKE_PYTHON3_INVOKED", proc.stdout + proc.stderr,
                          proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
