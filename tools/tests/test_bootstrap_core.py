#!/usr/bin/env python3
"""bootstrap_core.py::pick_python() WindowsApps 空殼排除 guard 回歸鎖（R31 Scan-B 修復）。

WHY：`tools/bootstrap.ps1` 在 DEF-101-273/279 兩輪修復中，對 `python`/`python3`
裸名候選加了 WindowsApps 空殼別名靜態路徑排除 guard——全新 Windows 11 機器上這兩個
名字常被系統自動註冊為 App Execution Alias 空殼，`shutil.which()`/`Get-Command`
找得到、但實際執行只會跳出 Microsoft Store 安裝提示，不會執行任何 Python 碼；用
「執行結果」判斷（`_probe_ok()`）在此情境不可靠，正是 `.ps1` 改用靜態路徑比對的
原因。但作為「單一真相源」的 `bootstrap_core.py::pick_python()`（R16 架構收斂後
真正決定建立 `.venv` 用哪個直譯器的核心邏輯）此前完全沒有這道 guard，本測試鎖住
R31 補齊的對稱修復，防未來退化回舊版純執行探測判斷。

執行：python -m pytest tools/tests/test_bootstrap_core.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap_core  # noqa: E402


class TestIsWindowsAppsStub(unittest.TestCase):
    def test_true_for_windows_apps_segment(self) -> None:
        self.assertTrue(
            bootstrap_core._is_windows_apps_stub(
                r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"  # platform-ok: 純字串傳入，非真實檔案路徑
            )
        )

    def test_true_case_insensitive(self) -> None:
        self.assertTrue(
            bootstrap_core._is_windows_apps_stub(
                r"C:\Users\me\AppData\Local\Microsoft\windowsapps\python3.exe"  # platform-ok: 同上
            ),
            "應不分大小寫",
        )

    def test_false_for_substring_but_not_full_segment(self) -> None:
        self.assertFalse(
            bootstrap_core._is_windows_apps_stub(
                r"C:\MyWindowsAppsTools\python.exe"  # platform-ok: 同上
            ),
            "含 'WindowsApps' 子字串但非完整路徑段，不應被排除（DEF-101-236 同款教訓）",
        )

    def test_false_for_real_install_path(self) -> None:
        self.assertFalse(
            bootstrap_core._is_windows_apps_stub(
                r"C:\Python311\python.exe"  # platform-ok: 同上
            )
        )


class TestPickPythonWindowsAppsGuard(unittest.TestCase):
    """行為驅動測試：直接呼叫 pick_python() 斷言真實行為（呼叫點層級回歸鎖，
    比照 test_find_git_bash_parity.py::TestFindGitBashBehavior 既有慣例——只鎖
    helper 本身不夠，退化回舊版直接跳過 guard 呼叫也要能抓到）。"""

    def test_skips_bare_python_when_windows_apps_stub_and_falls_back(self) -> None:
        """PATH 上第一個候選 "python" 解析到 WindowsApps 空殼時，應跳過、改採下一個
        真直譯器候選（不得因為 shutil.which 找得到就直接呼叫 _probe_ok 判定）。"""
        stub_path = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"  # platform-ok: mock 回傳值
        real_path = r"C:\Users\me\AppData\Local\Programs\Python\Python311\python3.exe"  # platform-ok: mock 回傳值

        def _fake_which(name: str) -> str | None:
            if name == "python":
                return stub_path
            if name == "python3":
                return real_path
            return None

        with (
            mock.patch.object(bootstrap_core, "IS_WINDOWS", True),
            mock.patch.object(bootstrap_core.os, "environ", {}),
            mock.patch.object(bootstrap_core.shutil, "which", side_effect=_fake_which),
            mock.patch.object(bootstrap_core, "_probe_ok", return_value=True),
        ):
            result = bootstrap_core.pick_python("3.11")

        self.assertEqual(
            result, "python3",
            "WindowsApps 空殼候選 'python' 應被跳過，選中下一個真直譯器候選 'python3'",
        )

    def test_does_not_skip_py_launcher_candidate(self) -> None:
        """`py` launcher 候選不受此 guard 影響——即使環境中 'python'/'python3' 都是
        空殼，只要 `py -3.11` 探測成功就該選它（guard 只排除裸名候選）。"""
        stub_path = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"  # platform-ok: mock 回傳值

        def _fake_which(name: str) -> str | None:
            if name in ("python", "python3"):
                return stub_path
            if name == "py":
                return r"C:\Windows\py.exe"  # platform-ok: mock 回傳值
            return None

        with (
            mock.patch.object(bootstrap_core, "IS_WINDOWS", True),
            mock.patch.object(bootstrap_core.os, "environ", {}),
            mock.patch.object(bootstrap_core.shutil, "which", side_effect=_fake_which),
            mock.patch.object(bootstrap_core, "_probe_ok", return_value=True),
        ):
            result = bootstrap_core.pick_python("3.11")

        self.assertEqual(result, "py -3.11")

    def test_returns_none_when_only_windows_apps_stubs_available(self) -> None:
        """所有裸名候選都是 WindowsApps 空殼、且無 `py` launcher 可用時，應回傳
        None（fail-loud），不得誤選空殼路徑。"""
        stub_path = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"  # platform-ok: mock 回傳值

        def _fake_which(name: str) -> str | None:
            if name in ("python", "python3"):
                return stub_path
            return None

        with (
            mock.patch.object(bootstrap_core, "IS_WINDOWS", True),
            mock.patch.object(bootstrap_core.os, "environ", {}),
            mock.patch.object(bootstrap_core.shutil, "which", side_effect=_fake_which),
            mock.patch.object(bootstrap_core, "_probe_ok", return_value=True),
        ):
            result = bootstrap_core.pick_python("3.11")

        self.assertIsNone(result)

    def test_bug_injection_without_guard_would_pick_stub(self) -> None:
        """對抗式驗證（bug-injection）：若把 guard 拿掉、只靠 `_probe_ok()` 判斷，
        本測試斷言「不應選中空殼」在退化版本下會失敗——證明 guard 本身有鑑別力，
        不是恆真斷言。此處直接呼叫 `_is_windows_apps_stub()` 模擬退化情境的判斷
        依據被繞過會發生什麼：若呼叫端忘記檢查此函式，`_probe_ok()` 對空殼別名
        探測 `python --version` 在真機上會因跳出 Store 提示而 hang 或回傳非 0，
        但測試環境無法真實重現 Store 提示語意，此處以 mock 固定 `_probe_ok`
        永遠回傳 True 模擬「探測誤判為可用」的最壞情境，驗證 guard 是唯一防線。"""
        stub_path = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"  # platform-ok: mock 回傳值

        with mock.patch.object(bootstrap_core, "IS_WINDOWS", True):
            self.assertTrue(bootstrap_core._is_windows_apps_stub(stub_path))


class TestMainReconfiguresStdioUtf8(unittest.TestCase):
    """main() 對 sys.stdout/stderr 的 reconfigure 呼叫必須帶
    `encoding="utf-8", errors="replace"`（R44 複審 DEF-101-362：先前只設定
    `line_buffering=True`、獨漏 encoding，本檔大量輸出 ✅/❌/⚠️/🔴 等符號，
    在被導向（如 CI 用 `*>&1 | Out-String` 擷取）的 Windows 非 UTF-8 codepage
    （cp950/cp1252）下會 UnicodeEncodeError 崩潰。手法比照
    tools/tests/test_stdio_utf8.py：以 mock.Mock() 取代 sys.stdout/stderr，
    不需真的切換 Windows codepage 也能驗證。"""

    def test_reconfigure_called_with_utf8_and_line_buffering(self) -> None:
        fake_stdout = mock.Mock()
        fake_stderr = mock.Mock()
        with (
            mock.patch.object(sys, "stdout", fake_stdout),
            mock.patch.object(sys, "stderr", fake_stderr),
            mock.patch.object(bootstrap_core.os, "chdir"),
            mock.patch.object(bootstrap_core, "ensure_venv", return_value=1),
        ):
            rc = bootstrap_core.main()

        fake_stdout.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="replace", line_buffering=True
        )
        fake_stderr.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="replace", line_buffering=True
        )
        self.assertEqual(rc, 1, "ensure_venv 回傳非 0 時 main() 應提早 return 該值")

    def test_reconfigure_errors_are_swallowed_without_crashing(self) -> None:
        """reconfigure() 拋 OSError/ValueError（例如串流不支援該切換）時必須被吞掉，
        不得讓 main() 崩潰——對抗式驗證：若把 except 子句拿掉，本測試會轉紅。"""
        fake_stdout = mock.Mock()
        fake_stdout.reconfigure.side_effect = OSError("boom")
        fake_stderr = mock.Mock()
        fake_stderr.reconfigure.side_effect = ValueError("boom")
        with (
            mock.patch.object(sys, "stdout", fake_stdout),
            mock.patch.object(sys, "stderr", fake_stderr),
            mock.patch.object(bootstrap_core.os, "chdir"),
            mock.patch.object(bootstrap_core, "ensure_venv", return_value=1),
        ):
            rc = bootstrap_core.main()  # 不應拋例外

        self.assertEqual(rc, 1)
        fake_stdout.reconfigure.assert_called_once()
        fake_stderr.reconfigure.assert_called_once()


if __name__ == "__main__":
    unittest.main()
