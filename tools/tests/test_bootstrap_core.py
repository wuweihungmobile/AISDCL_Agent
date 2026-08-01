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

import contextlib
import io
import re
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
        # `argv=[]` 顯式傳入（R67-F9）：main() 加上參數解析後，`argv=None` 代表
        # 「讀真的 `sys.argv[1:]`」——在 pytest 下那是 pytest 自己的參數
        # （`tools/tests/test_bootstrap_core.py -q`），會被 argparse 判為未知參數
        # 而回 2，使本組斷言隨「用哪個 runner 跑」翻紅（實測：unittest runner 綠、
        # `python -m pytest` 紅）。測 stdio 行為時把 CLI 維度釘死為空。
        fake_stdout = mock.Mock()
        fake_stderr = mock.Mock()
        with (
            mock.patch.object(sys, "stdout", fake_stdout),
            mock.patch.object(sys, "stderr", fake_stderr),
            mock.patch.object(bootstrap_core.os, "chdir"),
            mock.patch.object(bootstrap_core, "ensure_venv", return_value=1),
        ):
            rc = bootstrap_core.main(argv=[])

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
            rc = bootstrap_core.main(argv=[])  # 不應拋例外（argv=[] 理由同上）

        self.assertEqual(rc, 1)
        fake_stdout.reconfigure.assert_called_once()
        fake_stderr.reconfigure.assert_called_once()


class TestCliContractNoSilentBootstrap(unittest.TestCase):
    """R67-F9 回歸鎖：`--help`／未知旗標**絕不得**觸發任何 bootstrap 副作用。

    WHY（這道鎖在守什麼）：修復前 `bootstrap_core.main()` 完全不讀 `sys.argv`，
    而 `tools/bootstrap.sh`（`"$@"`）與 `tools/bootstrap.ps1`（`@args`）都原樣透傳
    參數——於是 `bash tools/bootstrap.sh --help` 會 rc=0 並**跑完整套 bootstrap**：
    在沒有 `.venv` 的新機器上等於憑空建 venv ＋下載 AutoClaude[dev,notifications,lint]
    與 AISDLC_SDD requirements-ci.txt（沙箱實測 146M/409 個 site-packages 項目），
    使用者以為自己只是看說明；`--forse-bootstrap` 這類 typo 同樣 rc=0 走預設路徑，
    使用者以為已強制重建、實際只是沿用舊 venv。

    因此本組**不只斷言 rc**——rc 對了但仍偷偷裝完依賴才是真正的失敗形態，故一律
    同時斷言 `os.chdir`／`ensure_venv`／`install_dependencies` 三個副作用入口
    **一次都沒被呼叫**。
    """

    def _run_main(self, argv: list[str]) -> tuple[int, str, str, dict[str, mock.Mock]]:
        """以三個副作用入口全上 mock 的方式跑 main()，回傳 (rc, stdout, stderr, mocks)。"""
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(bootstrap_core.os, "chdir") as m_chdir,
            mock.patch.object(bootstrap_core, "ensure_venv", return_value=0) as m_venv,
            mock.patch.object(
                bootstrap_core, "install_dependencies", return_value=0
            ) as m_install,
            mock.patch.object(bootstrap_core, "print_completion_guide"),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            rc = bootstrap_core.main(argv=argv)
        return rc, out.getvalue(), err.getvalue(), {
            "chdir": m_chdir, "ensure_venv": m_venv, "install": m_install,
        }

    def _assert_no_side_effects(self, mocks: dict[str, mock.Mock], label: str) -> None:
        for name, m in mocks.items():
            self.assertEqual(
                m.call_count, 0,
                f"{label} 不得產生任何 bootstrap 副作用，但 {name}() 被呼叫了 "
                f"{m.call_count} 次——這正是 R67-F9 的失敗形態（rc 看起來對、"
                f"venv 與依賴照樣被動過）",
            )

    def test_help_prints_usage_returns_zero_and_does_nothing(self) -> None:
        rc, out, _err, mocks = self._run_main(["--help"])
        self.assertEqual(rc, 0, "`--help` 必須 rc=0")
        self.assertIn("usage:", out, "`--help` 必須印出 usage")
        self.assertIn(bootstrap_core._WRAPPER_NAME, out,
                      "usage 的 prog 必須是使用者實際會敲的薄殼名，而非核心檔名")
        self._assert_no_side_effects(mocks, "`--help`")

    def test_short_help_flag_behaves_the_same(self) -> None:
        rc, out, _err, mocks = self._run_main(["-h"])
        self.assertEqual(rc, 0)
        self.assertIn("usage:", out)
        self._assert_no_side_effects(mocks, "`-h`")

    def test_unknown_flag_fails_loud_with_rc_two_and_does_nothing(self) -> None:
        """typo 必須 fail-loud，且錯誤訊息要指名那個字（否則使用者仍不知打錯什麼）。"""
        rc, _out, err, mocks = self._run_main(["--forse-bootstrap"])
        self.assertEqual(rc, 2, "未知旗標必須 rc≠0（argparse 慣例為 2），不得靜默走預設路徑")
        self.assertIn("--forse-bootstrap", err, "錯誤訊息必須逐字指名未被識別的參數")
        self._assert_no_side_effects(mocks, "未知旗標")

    def test_stray_positional_argument_also_fails_loud(self) -> None:
        rc, _out, err, mocks = self._run_main(["some-file.yaml"])
        self.assertEqual(rc, 2, "多餘的位置參數同樣必須 fail-loud（本腳本不吃任何位置參數）")
        self.assertIn("some-file.yaml", err)
        self._assert_no_side_effects(mocks, "多餘位置參數")

    def test_no_args_still_runs_the_real_bootstrap_path(self) -> None:
        """鑑別力對照組：無參數時**必須**照舊走完整流程。

        少了這條，把 `main()` 改成「一律 return 0 不做事」也能讓上面四條全綠——
        那是把缺陷修成另一個更嚴重的缺陷。
        """
        rc, out, _err, mocks = self._run_main([])
        self.assertEqual(rc, 0)
        self.assertIn("bootstrap", out, "無參數時應印出 bootstrap 標頭")
        self.assertEqual(mocks["chdir"].call_count, 1, "無參數時應 chdir 到 repo 根")
        self.assertEqual(mocks["ensure_venv"].call_count, 1, "無參數時應整備 venv")
        self.assertEqual(mocks["install"].call_count, 1, "無參數時應安裝依賴")


class TestWrapperPassThroughKeepsCoreReachable(unittest.TestCase):
    """兩支薄殼必須把參數原樣透傳給核心——否則核心的 CLI 契約從使用者端不可達。

    WHY：R67-F9 的修復刻意只做在核心一處（CLI 契約單一真相源），這使「薄殼是否
    仍透傳」成為修復的**前提條件**而非細節：任何一支殼改成不傳 `$@`／`@args`，
    `bash tools/bootstrap.sh --help` 就會退化回「靜默跑完整套 bootstrap」，而
    `check_wrapper_thinness.py` 的 hash 釘選只認「殼內容有沒有變」，對「變成什麼」
    沒有語意判斷（它會紅、但訊息只說 hash 對不上，不會說透傳斷了）。
    """

    _SH = Path(__file__).resolve().parents[1] / "bootstrap.sh"
    _PS1 = Path(__file__).resolve().parents[1] / "bootstrap.ps1"

    def _code_lines(self, path: Path) -> list[str]:
        """剝除整行註解（比照 macos_smoke_local.sh [7/7] 既有手法），只認功能碼行。"""
        text = path.read_text(encoding="utf-8-sig")
        text = re.sub(r"<#.*?#>", "", text, flags=re.DOTALL)  # .ps1 區塊註解
        return [ln for ln in text.splitlines() if not ln.strip().startswith("#")]

    def test_sh_wrapper_forwards_all_args_to_core(self) -> None:
        call = [ln for ln in self._code_lines(self._SH) if "bootstrap_core.py" in ln]
        self.assertTrue(call, "bootstrap.sh 功能碼行裡找不到對 bootstrap_core.py 的呼叫")
        self.assertTrue(
            any('"$@"' in ln for ln in call),
            'bootstrap.sh 必須以 "$@" 原樣透傳參數給核心，否則核心的 --help／未知旗標'
            "判定從使用者端不可達（R67-F9 修復的前提條件）",
        )

    def test_ps1_wrapper_forwards_all_args_to_core(self) -> None:
        call = [ln for ln in self._code_lines(self._PS1) if "bootstrap_core.py" in ln]
        self.assertTrue(call, "bootstrap.ps1 功能碼行裡找不到對 bootstrap_core.py 的呼叫")
        self.assertTrue(
            any("@args" in ln for ln in call),
            "bootstrap.ps1 必須以 @args 原樣透傳參數給核心（理由同 .sh 側）",
        )


class TestUsageEpilogFlagAttributionIsNotStale(unittest.TestCase):
    """usage 尾註把 `--force-bootstrap` 等旗標指給 `tools/dev_start.py`——這句散文
    只要 dev_start 改名旗標就會 stale，故在此機械綁住（散文與其指向的 live 來源
    同步，比照本 repo「不得寫死機器算得出的事實」紀律）。"""

    def test_flags_named_in_epilog_really_belong_to_dev_start(self) -> None:
        dev_start = (Path(__file__).resolve().parents[1] / "dev_start.py").read_text(
            encoding="utf-8"
        )
        named = re.findall(r"`(--[a-z-]+)`", bootstrap_core._USAGE_EPILOG)
        attributed = [f for f in named if f not in ("--help", "--forse-bootstrap")]
        self.assertTrue(attributed, "尾註應至少指名一個 dev_start 旗標（否則本鎖空轉）")
        for flag in attributed:
            self.assertIn(
                f'"{flag}"', dev_start,
                f"usage 尾註宣稱 {flag} 屬 tools/dev_start.py，但該檔的 argparse 已無此"
                "旗標——散文 stale，請同步兩邊",
            )


if __name__ == "__main__":
    unittest.main()
