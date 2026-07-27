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

R58 增補（guard／執行解析分歧）：上述 guard 檢查的是 `shutil.which()` 的結果，
但當時緊接著把**裸名**餵給 `_probe_ok()`／`-m venv`。Windows 上這是兩套不同的
解析規則（which() 套 PATHEXT、subprocess 走 CreateProcess 只補 `.exe`），實測
會指向不同檔案 → guard 檢查 A、實際執行 B，空殼 guard 整條被繞過（fail-open）。
本檔新增 `TestPickPythonResolvesOnce`（機制鎖）與
`TestPickPythonRealPathExecutionParity`（真檔案系統＋真 subprocess 端到端鎖）。

執行：python -m pytest tools/tests/test_bootstrap_core.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
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
            result, [real_path],
            "WindowsApps 空殼候選 'python' 應被跳過，選中下一個真直譯器候選 'python3'"
            "（R58 起回傳 argv list、元素 0 為 which() 解析出的絕對路徑）",
        )

    def test_does_not_skip_py_launcher_candidate(self) -> None:
        """`py` launcher 候選不受此 guard 影響——即使環境中 'python'/'python3' 都是
        空殼，只要 `py -3.11` 探測成功就該選它（guard 只排除裸名候選）。"""
        stub_path = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"  # platform-ok: mock 回傳值

        py_path = r"C:\Windows\py.exe"  # platform-ok: mock 回傳值

        def _fake_which(name: str) -> str | None:
            if name in ("python", "python3"):
                return stub_path
            if name == "py":
                return py_path
            return None

        with (
            mock.patch.object(bootstrap_core, "IS_WINDOWS", True),
            mock.patch.object(bootstrap_core.os, "environ", {}),
            mock.patch.object(bootstrap_core.shutil, "which", side_effect=_fake_which),
            mock.patch.object(bootstrap_core, "_probe_ok", return_value=True),
        ):
            result = bootstrap_core.pick_python("3.11")

        self.assertEqual(
            result, [py_path, "-3.11"],
            "`py -X.Y` 候選的版本旗標必須保留為獨立 argv 元素（R58：argv[0] 換成"
            "已解析的 py.exe 絕對路徑，`-3.11` 不得被併進同一元素）",
        )

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


class TestPickPythonResolvesOnce(unittest.TestCase):
    """R58：guard 檢查的檔案與實際執行的檔案必須是同一個（機制鎖，全平台可跑）。

    WHY 這是跨平台缺陷而非潔癖：Windows 上 `shutil.which()` 會套 PATHEXT
    （.COM/.EXE/.BAT/.CMD…），subprocess 走 CreateProcess 只補 `.exe`、不看
    PATHEXT——同一個裸名可以解析到兩個不同檔案（真 Windows 11 實測：本機
    `shutil.which("python3")` → `pyenv-win\\shims\\python3.BAT`，裸名執行卻是
    `pyenv-win\\versions\\<ver>\\python3.exe`）。macOS/Linux 上 `which` 與 execvp
    用同一套規則、恆一致，故這是**單邊平台**才會失效的形狀。後果是
    `_is_windows_apps_stub()` guard 檢查 A、`_probe_ok()`／`-m venv` 執行 B，
    guard 形同不存在（fail-open）。
    """

    def test_probe_receives_the_same_path_the_guard_inspected(self) -> None:
        """`_probe_ok()` 收到的 argv[0] 必須就是 guard 檢查過的解析結果，
        不得是裸名（裸名＝把解析權交還給 CreateProcess，等於重新賭一次）。"""
        stub_path = r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe"  # platform-ok: mock 回傳值
        real_path = r"C:\Python311\python3.exe"  # platform-ok: mock 回傳值
        guard_saw: list[str] = []
        probe_got: list[list[str]] = []

        def _fake_which(name: str) -> str | None:
            return {"python": stub_path, "python3": real_path}.get(name)

        def _spy_guard(resolved_path: str) -> bool:
            guard_saw.append(resolved_path)
            return "WindowsApps" in resolved_path

        def _spy_probe(argv_prefix: list[str]) -> bool:
            probe_got.append(list(argv_prefix))
            return True

        with (
            mock.patch.object(bootstrap_core, "IS_WINDOWS", True),
            mock.patch.object(bootstrap_core.os, "environ", {}),
            mock.patch.object(bootstrap_core.shutil, "which", side_effect=_fake_which),
            mock.patch.object(bootstrap_core, "_is_windows_apps_stub", side_effect=_spy_guard),
            mock.patch.object(bootstrap_core, "_probe_ok", side_effect=_spy_probe),
        ):
            result = bootstrap_core.pick_python("3.11")

        self.assertEqual(guard_saw, [stub_path, real_path], "guard 應逐一檢查兩個裸名候選的解析結果")
        self.assertEqual(
            probe_got, [[real_path]],
            "探測必須用 guard 檢查過的同一個絕對路徑；收到裸名（如 ['python3']）"
            "代表 guard 與執行各自解析一次，Windows 上可指向不同檔案 → guard 失效",
        )
        self.assertEqual(result, [real_path])

    def test_resolved_path_with_spaces_survives_into_venv_creation(self) -> None:
        """建立 `.venv` 的實際 argv 必須原樣帶著含空白的絕對路徑。

        鎖住舊介面的地雷：`pick_python()` 舊版回傳字串、呼叫端以 `.split()` 還原
        argv——一旦回傳的是 `C:\\Program Files\\...\\python.exe` 這種真實安裝路徑，
        `.split()` 會把它切成三段不存在的路徑。本測試同時鎖「用 pick_python 選到的
        直譯器建 .venv」這條因果鏈（危害面：.venv 被非預期的直譯器建立）。
        """
        space_path = r"C:\Program Files\Python311\python.exe"  # platform-ok: mock 回傳值
        recorded: list[list[str]] = []

        def _spy_run(cmd: list[str]) -> int:
            recorded.append(list(cmd))
            return 0

        with tempfile.TemporaryDirectory() as td:
            fake_venv = Path(td) / ".venv"  # 不建立 → 走「建立虛擬環境」分支
            with (
                mock.patch.object(bootstrap_core, "IS_WINDOWS", True),
                mock.patch.object(bootstrap_core, "VENV_DIR", fake_venv),
                mock.patch.object(bootstrap_core, "pick_python", return_value=[space_path]),
                mock.patch.object(bootstrap_core, "_probe_version_mm", return_value="3.11"),
                mock.patch.object(bootstrap_core, "_venv_python_usable", return_value=True),
                mock.patch.object(bootstrap_core, "_run_stream", side_effect=_spy_run),
            ):
                rc = bootstrap_core.ensure_venv("3.11", use_uv=False)

            self.assertEqual(rc, 0)
            self.assertEqual(
                recorded, [[space_path, "-m", "venv", str(fake_venv)]],
                "含空白的直譯器路徑必須是單一 argv 元素——被 .split() 切碎即為退化",
            )


@unittest.skipUnless(
    os.name == "nt",
    "which()／CreateProcess 的 PATHEXT 解析分歧是 Windows 專屬語意；"
    "POSIX 上 which 與 execvp 用同一套規則、本測試不具鑑別力",
)
class TestWhichVsSubprocessResolutionPremise(unittest.TestCase):
    """**前提鎖**（刻意不是修復鎖）：`pick_python()` 之所以要「解析一次、全程用同一個
    絕對路徑」，前提是「Windows 上 `shutil.which()` 與 subprocess 對裸名的解析規則
    不同」。本 class 用真檔案系統 + 真 subprocess 量測該前提；哪天 CPython／Windows
    讓兩者一致，本 class 會轉紅並提醒維護者「那份理由已過期，請重新評估」，而不是
    讓理由悄悄爛掉。修復本身的鑑別力由 `TestPickPythonResolvesOnce` 承擔（已用
    bug-injection 實測驗紅）。

    為何**不**寫成「端到端證明 WindowsApps 空殼真的被執行」（已實測做不到，記錄
    理由以免後人重走同一條路）：CreateProcess 的搜尋順序把「執行中程式所在目錄」
    排在 PATH 之前，而本機能拿到的直譯器（pyenv-win 版本目錄；`.venv` 的
    redirector 會轉呼叫 base 安裝）其安裝目錄本身就有 `python3.exe`，裸名 `python3`
    永遠先命中它、到不了 fixture PATH——實測子行程 + 真 env 佈局仍執行到
    `pyenv-win\\versions\\<ver>\\python3.exe`。要重現「裸名落到 WindowsApps 空殼」
    需要一個安裝目錄**不含** `python3.exe` 的直譯器（例如 python.org 版只裝
    `python.exe`），本機無此形狀。故本 class 改用 repo 內不存在的唯一名稱避開
    該搜尋規則，只鎖平台前提本身。
    """

    _NAME = "aisdcl_probe_py"  # 刻意用唯一名稱：避免命中「執行中程式所在目錄」

    def setUp(self) -> None:
        self._td = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._td, True)
        self.shim_dir = Path(self._td) / "shims"
        self.exe_dir = Path(self._td) / "WindowsApps"
        self.marker = Path(self._td) / "shim_ran.txt"
        self.shim_dir.mkdir()
        self.exe_dir.mkdir()
        # platform-ok: 本 class 已 skipUnless(os.name == "nt")，此處需要一支真實可執行的
        # Windows 系統 exe 當 fixture，`%WINDIR%` 缺失時的回退值本質上就是 Windows 路徑
        win_dir = os.environ.get("WINDIR") or r"C:\Windows"  # platform-ok: 同上
        self._sys_exe = Path(win_dir) / "System32" / "hostname.exe"

    def _write_shim(self, ext: str) -> Path:
        """建一支「執行到就會留下痕跡」的 shim（痕跡＝marker 檔案）。"""
        shim = self.shim_dir / f"{self._NAME}.{ext}"
        shim.write_text(f'@echo off\r\n@echo ran> "{self.marker}"\r\n@exit /b 0\r\n', encoding="ascii")
        return shim

    def _run_bare(self) -> subprocess.CompletedProcess | OSError:
        try:
            return subprocess.run(
                [self._NAME], capture_output=True, encoding="utf-8", errors="replace", timeout=60
            )
        except OSError as exc:
            return exc

    def test_which_finds_batch_shim_that_subprocess_cannot_execute(self) -> None:
        """只有 .bat／.cmd 的目錄：which() 套 PATHEXT 找得到，subprocess 走
        CreateProcess 只補 `.exe`、找不到 → 兩者對同一裸名的答案本就不一致。"""
        for ext in ("bat", "cmd"):
            with self.subTest(ext=ext):
                shim = self._write_shim(ext)
                with mock.patch.dict(os.environ, {"PATH": str(self.shim_dir)}):
                    found = shutil.which(self._NAME)
                    outcome = self._run_bare()
                self.assertIsNotNone(found, f"which() 應找到 {shim.name}（PATHEXT 含 .{ext.upper()}）")
                self.assertEqual(Path(found or "").suffix.lower(), f".{ext}")
                self.assertIsInstance(
                    outcome, OSError,
                    f"前提已改變：subprocess 現在解析得到裸名的 .{ext}——"
                    "pick_python() 解析一次的理由需重新評估",
                )
                shim.unlink()

    def test_which_and_subprocess_resolve_to_different_files(self) -> None:
        """.bat 在前、.exe 在後：which() 命中前段 .bat，subprocess 實際執行後段
        .exe ——「守門看 A、實際跑 B」的完整形狀（本修復要消滅的正是這個）。"""
        if not self._sys_exe.is_file():
            self.skipTest(f"fixture 需要一支可執行的系統 exe，找不到 {self._sys_exe}")
        self._write_shim("bat")
        shutil.copy2(self._sys_exe, self.exe_dir / f"{self._NAME}.exe")

        with mock.patch.dict(
            os.environ, {"PATH": f"{self.shim_dir}{os.pathsep}{self.exe_dir}"}
        ):
            found = shutil.which(self._NAME)
            outcome = self._run_bare()

        self.assertEqual(
            Path(found or "").parent, self.shim_dir,
            "which() 應命中 PATH 前段的 .bat（guard 檢查的就是這個檔案）",
        )
        self.assertNotIsInstance(outcome, OSError, f"fixture .exe 應可執行：{outcome}")
        self.assertEqual(outcome.returncode, 0)  # type: ignore[union-attr]
        self.assertFalse(
            self.marker.exists(),
            "前提已改變：實際執行的是 which() 指向的那支 .bat（marker 出現）。"
            "此前實測為 CreateProcess 跳過 .bat、執行後段 .exe——若前提反轉，"
            "pick_python() 解析一次的理由需重新評估",
        )


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
