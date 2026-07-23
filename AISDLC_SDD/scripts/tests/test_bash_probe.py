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
            mock_run.return_value = mock.Mock(returncode=0, stdout="probe_ok\n/tmp/probe_dir\n")
            result = bash_probe.usable_bash()
        self.assertEqual(result, legit_path)


class TestUsableBashCoreutilsValidation(unittest.TestCase):
    """DEF-101-275（R27 開出、連續 5 輪〔R27~R31〕未收斂）回歸鎖：`usable_bash()`
    原本只用 `echo ok` 驗活，未驗證 coreutils（如 `dirname`）真的可執行，精簡版
    Git Bash（缺 coreutils）會通過驗活、實際跑腳本才失敗。R32 改用
    `bash_probe_spec.PROBE_CMD`（echo + dirname 兩段 `&&` 串接）驗活，本類別鎖住
    正向（真的可用的 bash 應通過）與負向（只有 echo、沒有 dirname 的殘缺 bash
    應被拒絕）兩分支。"""

    def test_accepts_bash_with_working_coreutils(self) -> None:
        """正向：echo 與 dirname 皆正確輸出、rc=0 時應被接受。"""
        legit_path = r"C:\Program Files\Git\usr\bin\bash.exe"  # platform-ok: mock 回傳值
        with (
            mock.patch.object(bash_probe.shutil, "which") as mock_which,
            mock.patch.object(bash_probe.subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: legit_path if name == "bash" else None
            mock_run.return_value = mock.Mock(returncode=0, stdout="probe_ok\n/tmp/probe_dir\n")
            result = bash_probe.usable_bash()
        self.assertEqual(result, legit_path)

    def test_rejects_bash_missing_coreutils_dirname(self) -> None:
        """R32 bug-injection 標的：只有 `echo` 可用、缺 `dirname` 的殘缺 Git
        Bash（`bash: dirname: command not found`）——echo 段已輸出，但 `&&` 串接
        的第二段因指令不存在而使整串以非 0 回傳碼失敗，必須被拒絕。若退化回舊版
        只驗 `echo ok`，本測試須變紅。"""
        legit_path = r"C:\Program Files\Git\usr\bin\bash.exe"  # platform-ok: mock 回傳值
        with (
            mock.patch.object(bash_probe.shutil, "which") as mock_which,
            mock.patch.object(bash_probe.subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: legit_path if name == "bash" else None
            mock_run.return_value = mock.Mock(returncode=127, stdout="probe_ok\n")
            result = bash_probe.usable_bash()
        self.assertIsNone(result, "缺 coreutils（dirname）的殘缺 bash 應被拒絕")

    def test_rejects_bash_with_wrong_dirname_output(self) -> None:
        """負向補強：rc=0 但 dirname 輸出與期望不符（假設某環境的 dirname 行為
        異常），不應被誤判為可用——驗證比對的是精確輸出，不只是 rc。"""
        legit_path = r"C:\Program Files\Git\usr\bin\bash.exe"  # platform-ok: mock 回傳值
        with (
            mock.patch.object(bash_probe.shutil, "which") as mock_which,
            mock.patch.object(bash_probe.subprocess, "run") as mock_run,
        ):
            mock_which.side_effect = lambda name: legit_path if name == "bash" else None
            mock_run.return_value = mock.Mock(returncode=0, stdout="probe_ok\nsomething_wrong\n")
            result = bash_probe.usable_bash()
        self.assertIsNone(result, "dirname 輸出與期望不符時應被拒絕")


if __name__ == "__main__":
    unittest.main()
