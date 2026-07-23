#!/usr/bin/env python3
"""bash_probe.py::_has_system32_segment() 精確路徑段比對回歸鎖（R31 Scan-B 修復）。

WHY：`scripts/bash_probe.py::usable_bash()` 原本用
`"system32" not in bare.replace("/", "\\").lower()` 任意子字串命中即排除 WSL
System32 佔位 bash，較 `tools/integration_gate_core.py::_has_system32_segment()`
（DEF-101-236 修復後的正確版本）寬鬆，會誤傷路徑含 "system32" 子字串但非該
目錄段的合法候選（如 `C:\\MySystem32Tools\\bash.exe`）。本測試鎖住 R31 對齊
`PureWindowsPath` 逐段精確比對後的行為，防退化回舊版寬鬆判斷。

執行：python -m pytest AISDLC_SDD/scripts/tests/test_bash_probe.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bash_probe  # noqa: E402


class TestHasSystem32Segment(unittest.TestCase):
    def test_true_for_full_path_segment(self) -> None:
        self.assertTrue(
            bash_probe._has_system32_segment(r"C:\Windows\System32\bash.exe")  # platform-ok: 純字串傳入，非真實檔案路徑
        )

    def test_true_case_insensitive(self) -> None:
        self.assertTrue(
            bash_probe._has_system32_segment(r"C:\WINDOWS\system32\bash.exe"),  # platform-ok: 同上
            "應不分大小寫",
        )

    def test_false_for_substring_but_not_full_segment(self) -> None:
        self.assertFalse(
            bash_probe._has_system32_segment(r"C:\MySystem32Tools\bash.exe"),  # platform-ok: 同上
            "含 'system32' 子字串但非完整路徑段，不應被排除（DEF-101-236 同款教訓）",
        )

    def test_false_for_legit_git_bash_path(self) -> None:
        self.assertFalse(
            bash_probe._has_system32_segment(r"C:\Program Files\Git\bin\bash.exe")  # platform-ok: 同上
        )


class TestUsableBashSystem32Guard(unittest.TestCase):
    """呼叫點層級的回歸鎖（比照 test_find_git_bash_parity.py::TestFindGitBashBehavior
    既有慣例）：只鎖 helper 本身不夠，退化回舊版寬鬆判斷也要能抓到。"""

    def test_skips_wsl_system32_placeholder(self) -> None:
        with (
            mock.patch.object(bash_probe.shutil, "which") as mock_which,
            mock.patch.object(bash_probe.subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: (
                r"C:\Windows\System32\bash.exe" if name == "bash" else None  # platform-ok: mock 回傳值
            )
            result = bash_probe.usable_bash()
        mock_run.assert_not_called()
        self.assertIsNone(result, "WSL System32 佔位 bash 應被排除、不應嘗試 subprocess.run")

    def test_does_not_reject_substring_false_positive_path(self) -> None:
        """R31 bug-injection 標的：PATH 上的 bash 位於「含 system32 子字串但非
        完整路徑段」的合法路徑時，不應被誤排除——若退化回舊版寬鬆判斷
        `"system32" not in bare.lower()`，本測試須變紅。"""
        legit_path = r"C:\MySystem32Tools\bash.exe"  # platform-ok: mock 回傳值，非真實檔案路徑
        with (
            mock.patch.object(bash_probe.shutil, "which") as mock_which,
            mock.patch.object(bash_probe.subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: legit_path if name == "bash" else None
            mock_run.return_value = mock.Mock(returncode=0, stdout="ok\n")
            result = bash_probe.usable_bash()
        self.assertEqual(result, legit_path)


if __name__ == "__main__":
    unittest.main()
