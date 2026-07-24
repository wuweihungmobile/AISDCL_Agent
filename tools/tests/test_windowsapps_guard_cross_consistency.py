#!/usr/bin/env python3
"""Windows Store App Execution Alias（WindowsApps 空殼）排除 guard 收斂鎖
（R37 Architect 架構最佳化重構）。

背景：同一條規則（排除 WindowsApps 底下的 python.exe/python3.exe 空殼別名，
未真裝 Python 時 `Get-Command python` 仍會找到它，執行只會跳出 Microsoft Store
提示）過去在 `tools/bootstrap.ps1`（2 處）與 `tools/dev_start.ps1`（1 處）逐字
內嵌了三份獨立複製，互不相通，導致同一缺陷類別連續復發四次（DEF-101-273／
279／300／303）——其中 DEF-101-303（`$PyCand`/`$Py3Cand` 變數與 `Get-Command`
命令名稱錯配的手誤風險）正是「內嵌而非呼叫共用函式」才可能發生的錯配類型。

R37 抽出 `tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython` 共用函式（比照
`tools/lib/Find-GitBash.ps1` 既有先例），三處呼叫端改為 dot-source 後呼叫該
函式，取代原本各自內嵌的判斷式。三份內嵌複製彼此語意一致的問題已隨之消失
（只剩 1 份實作），本檔的舊靜態 regex/文字交叉比對手法（鎖「三份複製彼此一致」）
不再有意義，重構為：
  ① 存在性檢查：`bootstrap.ps1`／`dev_start.ps1` 確實 dot-source 共用檔案 +
     呼叫 `Test-IsRealPython`（且不得殘留內嵌判斷式，防未來繞過共用函式又
     內嵌一份）。
  ② 共用函式本身的行為測試：透過 shadow `Get-Command`（見下方
     `TestWindowsAppsGuardSharedFunctionBehavior` docstring 說明手法）直接
     驗證 `Test-IsRealPython` 的判斷邏輯，不受各平台 `Get-Command` 路徑解析
     語意差異影響。
  ③ 保留有意義的端到端行為回歸鎖（`TestDevStartPs1WindowsAppsGuard`，R34
     補齊的第 4 個實作零覆蓋缺口），調整 fixture 使其在新架構下仍具鑑別力
     （dot-source 目標檔案需隨腳本一併複製到隔離的臨時目錄，否則 dot-source
     會因找不到檔案而失敗、測試會因錯誤的理由而通過，喪失鑑別力）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BOOTSTRAP_PS1 = _REPO_ROOT / "tools" / "bootstrap.ps1"
_DEV_START_PS1 = _REPO_ROOT / "tools" / "dev_start.ps1"
_BOOTSTRAP_CORE_PY = _REPO_ROOT / "tools" / "bootstrap_core.py"
_GUARD_PS1 = _REPO_ROOT / "tools" / "lib" / "WindowsAppsGuard.ps1"

# 共用函式的 dot-source 相對路徑（兩份呼叫端皆直接位於 tools/ 下，故皆為
# "lib/WindowsAppsGuard.ps1"；一併鎖住路徑片段本身，防呼叫端誤用其他相對路徑）
_DOT_SOURCE_RE = re.compile(
    r'\.\s+"\$PSScriptRoot/lib/WindowsAppsGuard\.ps1"'
)
_INLINE_NOTLIKE_RE = re.compile(r"-notlike\s+'\*\\WindowsApps\\\*'")


def _pwsh_exe() -> str | None:
    return shutil.which("pwsh") or shutil.which("powershell")


# ---------------------------------------------------------------------------
# ① 存在性檢查：呼叫端須 dot-source 共用檔案 + 呼叫共用函式，且不得殘留內嵌判斷式
# ---------------------------------------------------------------------------
class TestWindowsAppsGuardEnrollment(unittest.TestCase):
    def setUp(self) -> None:
        self.bootstrap_text = _BOOTSTRAP_PS1.read_text(encoding="utf-8")
        self.dev_start_text = _DEV_START_PS1.read_text(encoding="utf-8")
        self.guard_text = _GUARD_PS1.read_text(encoding="utf-8")

    def test_shared_guard_file_exists_and_defines_the_function(self) -> None:
        self.assertTrue(_GUARD_PS1.is_file(), f"{_GUARD_PS1} 不存在")
        self.assertIn(
            "function Test-IsRealPython", self.guard_text,
            "tools/lib/WindowsAppsGuard.ps1 未定義 Test-IsRealPython 共用函式",
        )
        self.assertRegex(
            self.guard_text, _INLINE_NOTLIKE_RE,
            "共用函式內找不到 WindowsApps -notlike 排除 pattern——guard 邏輯本體"
            "是否被改寫或移除？",
        )

    def test_bootstrap_ps1_dot_sources_shared_guard(self) -> None:
        self.assertRegex(
            self.bootstrap_text, _DOT_SOURCE_RE,
            "tools/bootstrap.ps1 未 dot-source tools/lib/WindowsAppsGuard.ps1",
        )

    def test_dev_start_ps1_dot_sources_shared_guard(self) -> None:
        self.assertRegex(
            self.dev_start_text, _DOT_SOURCE_RE,
            "tools/dev_start.ps1 未 dot-source tools/lib/WindowsAppsGuard.ps1",
        )

    def test_bootstrap_ps1_calls_shared_function_for_both_python_and_python3(
        self,
    ) -> None:
        """bootstrap.ps1 有兩處候選（python／python3），皆須改呼叫共用函式，
        且以字面值（非變數）傳入候選名稱——呼叫端只是
        `Test-IsRealPython -CandidateName 'python'` 這種直接傳字面值的單行
        判斷式，不再有「兩個中繼變數互換」的複製貼上空間，DEF-101-303 描述的
        錯配情境在此架構下結構性消失（見本檔頂部 docstring）。
        """
        calls = re.findall(
            r"Test-IsRealPython\s+-CandidateName\s+'(python3?)'", self.bootstrap_text
        )
        self.assertEqual(
            sorted(calls), ["python", "python3"],
            f"tools/bootstrap.ps1 應恰有兩處以字面值呼叫 Test-IsRealPython"
            f"（'python' 與 'python3'），實際找到：{calls}",
        )

    def test_dev_start_ps1_calls_shared_function_for_python(self) -> None:
        calls = re.findall(
            r"Test-IsRealPython\s+-CandidateName\s+'(python3?)'", self.dev_start_text
        )
        self.assertEqual(
            calls, ["python"],
            f"tools/dev_start.ps1 應恰有一處以字面值 'python' 呼叫 Test-IsRealPython，"
            f"實際找到：{calls}",
        )

    def test_bootstrap_ps1_no_longer_has_inline_notlike_guard(self) -> None:
        """呼叫端不得殘留內嵌的 `-notlike '*\\WindowsApps\\*'` 判斷式——若殘留，
        代表有人繞過共用函式又內嵌了一份複製，正是本輪要收斂消滅的問題本身。
        """
        self.assertNotRegex(
            self.bootstrap_text, _INLINE_NOTLIKE_RE,
            "tools/bootstrap.ps1 仍殘留內嵌 WindowsApps -notlike 判斷式——"
            "應已全數改為呼叫 Test-IsRealPython 共用函式",
        )

    def test_dev_start_ps1_no_longer_has_inline_notlike_guard(self) -> None:
        self.assertNotRegex(
            self.dev_start_text, _INLINE_NOTLIKE_RE,
            "tools/dev_start.ps1 仍殘留內嵌 WindowsApps -notlike 判斷式——"
            "應已全數改為呼叫 Test-IsRealPython 共用函式",
        )

    def test_bootstrap_core_py_has_symmetric_stub_detector(self) -> None:
        """Python 核心側（bootstrap_core.py）須有對稱的 WindowsApps 空殼偵測，
        且比對邏輯為「路徑分段」（非任意子字串），避免 `C:\\FooWindowsAppsBar\\`
        這類非真實 WindowsApps 路徑被誤判命中（DEF-101-281 既有設計）。這是
        不同語言的獨立第 4 份實作，語言邊界問題不在本輪收斂範圍內，維持不動。
        """
        text = _BOOTSTRAP_CORE_PY.read_text(encoding="utf-8")
        self.assertIn("_is_windows_apps_stub", text)
        self.assertIn('part.lower() == "windowsapps"', text)


# ---------------------------------------------------------------------------
# ② 共用函式本身的行為測試
# ---------------------------------------------------------------------------
@unittest.skipIf(_pwsh_exe() is None, "需要 powershell/pwsh")
class TestWindowsAppsGuardSharedFunctionBehavior(unittest.TestCase):
    """直接對 `Test-IsRealPython` 做行為測試。

    手法：在 dot-source 共用檔案「之前」先定義一個同名 `Get-Command` 函式
    （PowerShell 的命令解析對函式與 cmdlet 同名時，函式優先於內建 cmdlet），
    讓 `Test-IsRealPython` 呼叫到的 `Get-Command` 回傳我們指定的假 `.Source`
    字串——藉此在任何平台（含本開發機的 macOS pwsh）上都能正確驗證
    `-notlike '*\\WindowsApps\\*'` 排除邏輯本身，不受各平台 `Get-Command`
    對裸名候選的路徑解析語意差異影響（真實 Windows 路徑用反斜線，macOS/Linux
    上 `Get-Command` 找到的可執行檔路徑用斜線，若改用真實 PATH 佈局測試會
    因平台差異而失去鑑別力，此為既有測試套件記載的已知侷限——見本檔其他
    class 的說明）。
    """

    def _run(self, get_command_body: str, call_expr: str) -> str:
        exe = _pwsh_exe()
        script = (
            "function Get-Command {\n"
            "  param(\n"
            "    [Parameter(Position=0)][string]$Name,\n"
            "    [Parameter(ValueFromRemainingArguments=$true)] $Rest\n"
            "  )\n"
            f"  {get_command_body}\n"
            "}\n"
            f'. "{_GUARD_PS1}"\n'
            f"Write-Output ({call_expr})\n"
        )
        proc = subprocess.run(
            [exe, "-NoProfile", "-Command", script],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout.strip()

    def test_windowsapps_stub_source_is_rejected(self) -> None:
        body = (
            'return [PSCustomObject]@{ '
            'Source = "C:\\Users\\me\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe" }'  # platform-ok: 純字面值餵給 PowerShell 腳本文字，非 Python Path join
        )
        out = self._run(body, "Test-IsRealPython -CandidateName 'python'")
        self.assertEqual(out, "False", out)

    def test_real_source_outside_windowsapps_is_accepted(self) -> None:
        body = 'return [PSCustomObject]@{ Source = "C:\\Python311\\python3.exe" }'  # platform-ok: 同上，純字面值餵給 PowerShell 腳本文字
        out = self._run(body, "Test-IsRealPython -CandidateName 'python3'")
        self.assertEqual(out, "True", out)

    def test_missing_candidate_returns_false(self) -> None:
        """`Get-Command` 找不到候選（回傳 `$null`）時必須回傳 `$false`，不得
        因 `$cmd.Source` 存取 null 屬性而拋例外或誤判為真直譯器。"""
        out = self._run("return $null", "Test-IsRealPython -CandidateName 'python'")
        self.assertEqual(out, "False", out)

    def test_windowsapps_segment_match_is_case_insensitive(self) -> None:
        """`-notlike` 預設不分大小寫；即使路徑中的 WindowsApps 區段大小寫不同
        （如系統本地化或大小寫不敏感檔案系統回傳的不同大小寫），仍須被排除。
        防未來有人改成 `-cnotlike`（大小寫敏感版本）而悄悄弱化 guard。"""
        body = (
            'return [PSCustomObject]@{ '
            'Source = "C:\\Users\\me\\AppData\\Local\\Microsoft\\windowsapps\\python.exe" }'  # platform-ok: 純字面值餵給 PowerShell 腳本文字，非 Python Path join
        )
        out = self._run(body, "Test-IsRealPython -CandidateName 'python'")
        self.assertEqual(out, "False", out)


# ---------------------------------------------------------------------------
# ③ 端到端行為回歸鎖：dev_start.ps1 本身（R34 前零覆蓋的第 4 個獨立實作）
# ---------------------------------------------------------------------------
def _windows_pwsh_available() -> bool:
    """僅供依賴 Windows PATHEXT／`.cmd` 解析語意的測試使用（見各該測試
    docstring）：這類測試用 `.cmd` 假直譯器讓 `Get-Command python` 命中它，
    但 `.cmd` 需要 `cmd.exe` 解譯——在裝有 pwsh 的 macOS/Linux 開發機上呼叫
    `.cmd` 檔案會靜默無回應，使測試確定性失敗而非雜訊。單純檢查
    `shutil.which("pwsh")` 不足以排除這類機器，必須同時檢查平台本身。
    """
    return sys.platform.startswith("win") and _pwsh_exe() is not None


@unittest.skipIf(_pwsh_exe() is None, "需要 powershell/pwsh")
class TestDevStartPs1WindowsAppsGuard(unittest.TestCase):
    def _run(self, path_dirs: list[Path]) -> subprocess.CompletedProcess:
        # dev_start.ps1 選直譯器前會先檢查 `$Root/.venv/Scripts/python.exe`
        # （$Root 由 $PSScriptRoot 反推）——若直接對本 repo 的真實 dev_start.ps1
        # 下手，本機既有 .venv 會讓 Test-Path 短路成功，guard 分支永遠不會被
        # 執行到。故複製一份到零 .venv 的臨時 fake <root>/tools/ 結構下執行，
        # 讓 $Root 解析到乾淨臨時目錄（同 test_bootstrap_ps1.py 手法的延伸——
        # 該檔的 bootstrap.ps1 本身無 .venv 短路分支，不需此步）。
        #
        # R37 架構收斂後 dev_start.ps1 dot-source `$PSScriptRoot/lib/
        # WindowsAppsGuard.ps1`——fake tools/ 結構下若不一併複製該共用檔案，
        # dot-source 會找不到檔案而失敗（非終止性錯誤），guard 呼叫
        # 也隨之失敗，腳本最終仍會落到「找不到 Python」分支，但那是「共用檔案
        # 遺失」而非「guard 邏輯正確排除空殼」造成的假綠——故必須一併複製，
        # 保持測試對 guard 邏輯本身的鑑別力。
        exe = _pwsh_exe()
        with tempfile.TemporaryDirectory() as fake_root_td:
            fake_tools = Path(fake_root_td) / "tools"
            fake_lib = fake_tools / "lib"
            fake_lib.mkdir(parents=True)
            fake_ps1 = fake_tools / "dev_start.ps1"
            fake_ps1.write_text(_DEV_START_PS1.read_text(encoding="utf-8"), encoding="utf-8")
            (fake_lib / "WindowsAppsGuard.ps1").write_text(
                _GUARD_PS1.read_text(encoding="utf-8"), encoding="utf-8"
            )
            env = dict(os.environ)
            env["PATH"] = os.pathsep.join(str(p) for p in path_dirs)
            cmd = (
                "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
                f"& '{fake_ps1}'"
            )
            return subprocess.run(
                [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=30, env=env,
            )

    def test_windowsapps_only_python_stub_is_skipped_and_reports_not_found(self) -> None:
        """PATH 上只有一個位於 WindowsApps 路徑下的 python.exe 空殼、無 py 時，
        dev_start.ps1 必須跳過該空殼並回報「找不到 Python 直譯器」，而不是把
        空殼當真直譯器去呼叫 tools/dev_start.py（那樣只會跳出 Store 提示，
        永遠不會真正整備環境）——與 bootstrap.ps1 既有回歸鎖同款情境。

        已知侷限（bug-injection 驗證時發現，如實揭露）：在 macOS/Linux 上的
        `pwsh`，`Get-Command python` 不會透過 Windows PATHEXT 語意把裸名
        `python` 解析到 `python.exe`——即使把本測試用的 guard 暫時拔掉（改為
        `if ($PyCand) { ... }`），`$PyCand` 在 macOS pwsh 上仍恆為 null，本測試
        會因「本來就找不到任何 python」而通過，並非真的驗證了 guard 邏輯本身
        （`test_bootstrap_ps1.py` 同款寫法的等價測試亦有此侷限；共用函式本身
        的排除邏輯已由上方 `TestWindowsAppsGuardSharedFunctionBehavior` 用
        shadow `Get-Command` 手法在任何平台上都具鑑別力地驗證過）。本測試在真
        Windows PowerShell（PATHEXT 生效）上才具備鑑別力——CI 端
        `windows-compat-ci.yml` 於 `windows-latest` runner 執行，該環境才是本測
        試實際發揮回歸鎖作用之處。
        """
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td) / "WindowsApps"
            stub_dir.mkdir()
            (stub_dir / "python.exe").write_bytes(b"")
            proc = self._run([stub_dir])
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("找不到", proc.stdout + proc.stderr)

    @unittest.skipUnless(
        _windows_pwsh_available(),
        "此測試用 .cmd 假直譯器驗證 WindowsApps guard，依賴 Windows PATHEXT "
        "解析語意，僅能在真 Windows 平台上跑（見 _windows_pwsh_available 說明）",
    )
    def test_real_python_outside_windowsapps_is_used_even_when_windowsapps_stub_present_first(
        self,
    ) -> None:
        """WindowsApps 空殼與真直譯器同時在 PATH 上時（空殼排在前面），必須
        跳過空殼、採用後面真正的候選——證明 guard 是「排除」而非「一找到
        python 就用」的裸邏輯退化。手法同 `test_bootstrap_ps1.py` 既有寫法：
        用 `.cmd` 假直譯器（Windows PATHEXT 解析下 `Get-Command python`／
        `& python` 皆會找到 `python.cmd`）取代不可執行的位元組佔位，令假
        直譯器被呼叫時印出唯一標記字串，正向斷言該標記真的出現。
        """
        with tempfile.TemporaryDirectory() as td:
            stub_dir = Path(td) / "WindowsApps"
            stub_dir.mkdir()
            (stub_dir / "python.exe").write_bytes(b"")
            real_dir = Path(td) / "real"
            real_dir.mkdir()
            fake = real_dir / "python.cmd"
            fake.write_text("@echo off\r\necho FAKE_PYTHON_INVOKED\r\nexit /b 42\r\n",
                             encoding="ascii")
            proc = self._run([stub_dir, real_dir])
            self.assertIn("FAKE_PYTHON_INVOKED", proc.stdout + proc.stderr,
                          proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
