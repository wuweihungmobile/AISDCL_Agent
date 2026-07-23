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
        python 就用」的裸邏輯退化。用 python3.exe 作真候選（迴圈第三順位），
        避免需要模擬完整可執行的 py/python 直譯器行為。
        """
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td) / "WindowsApps"
            stub_dir.mkdir()
            (stub_dir / "python.exe").write_bytes(b"")
            real_dir = Path(td) / "real"
            real_dir.mkdir()
            # 只需要 Get-Command 找得到、且被 & 呼叫時不會無限掛住；用一個會
            # 立刻印出可辨識字串並以非 0 結束的假直譯器，觀察 bootstrap.ps1
            # 是否真的選中它（而非空殼）去呼叫。
            fake = real_dir / "python3.exe"
            fake.write_bytes(b"MZ")  # 佔位位元組，PowerShell Get-Command 只看副檔名/存在性
            proc = self._run([stub_dir, real_dir])
            # 空殼被排除、python3 被選中後會嘗試以其執行 bootstrap_core.py；
            # 假直譯器不是真正可執行的 PE（僅 "MZ" 兩位元組），呼叫會失敗，
            # 但失敗訊息必須來自「嘗試執行選中的候選」而非「找不到 python」，
            # 藉此區分兩種失敗成因、確認 guard 真的往下選到了候選而非卡在空殼。
            self.assertNotIn("找不到 python/py/python3", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
