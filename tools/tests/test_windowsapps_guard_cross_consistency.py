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
        "[WINDOWS-NATIVE-ONLY] 此測試用 .cmd 假直譯器驗證 WindowsApps guard，依賴 "
        "Windows PATHEXT 解析語意，僅能在真 Windows 平台上跑（見 "
        "_windows_pwsh_available 說明；R43 DEF-101-348 標籤，供 run_root_unittests.py "
        "彙整可見度）",
    )
    def test_windowsapps_stub_present_first_is_rejected_not_silently_bypassed(
        self,
    ) -> None:
        """R42 四方複審修正（前身
        `test_real_python_outside_windowsapps_is_used_even_when_windowsapps_stub_present_first`
        的期待本身是錯的，見下方說明）：

        dev_start.ps1 只有 **單一** `python` 候選名稱（無 `python3`／`py`
        等第二候選可退而求其次）。`Test-IsRealPython` 目前實作是
        `Get-Command $CandidateName`（單一結果，依 PATH 目錄順序取第一個），
        呼叫端拿到 `$true` 後一律用**候選名稱字面值**（`'python'`）而非解析出
        的完整路徑去實際呼叫（`& $Py` 其中 `$Py = 'python'`）。

        前身測試建構「WindowsApps 空殼排前面、真直譯器排後面」的 PATH，卻
        期待 dev_start.ps1 最終會呼叫到後面那個真直譯器——這在目前架構下
        物理上不可能發生且**不應該**發生：本機實測（見 R42 修復報告）證實
        PowerShell `&` 對裸名稱的命令解析，与 `Test-IsRealPython` 內部
        `Get-Command` 各自獨立依 PATH 順序解析，兩者解析結果一致（都會拿到
        最前面的 WindowsApps 空殼）；`Test-IsRealPython` 目前回傳布林值前已
        用 `Get-Command $CandidateName`（單一結果）判斷該第一個候選是否為
        空殼，若是則正確回傳 `$false`，`$Py` 保持 `$null`，程式走「❌ 找不到
        Python 直譯器」分支並停下——這是**正確且更安全**的行為。

        若要讓 guard 真的「跳過空殼、找到後面的真直譯器」（例如改用
        `Get-Command -All` 逐一排除 WindowsApps 後取第一個真實候選），
        `Test-IsRealPython` 必須同時回傳該真直譯器的**完整解析路徑**，且三個
        呼叫端都要跟著改成用該完整路徑呼叫——否則就算函式回傳 `$true`，呼叫
        端 `& 'python'` 實際執行時，PowerShell 一樣會照 PATH 目錄順序解析到
        最前面那個 WindowsApps 空殼（本測試命名的原始期待），造成「guard 說
        安全，但實際執行的還是空殼」的靜默失敗，比現在「誠實回報找不到並
        停下」更危險。這是一個牽動三個入口腳本呼叫慣例的高風險大改動，超出
        本輪比例原則，故修正本測試期待而非動 production 邏輯。

        已知既有迴避手法（如實記載）：`test_bootstrap_ps1.py` 的同名測試
        `test_real_python_outside_windowsapps_is_used_even_when_windowsapps_stub_present_first`
        之所以能正向斷言「真直譯器被呼叫」且維持綠燈，是因為 bootstrap.ps1
        有 `python`／`python3` **兩個**候選名稱：該測試把 WindowsApps 空殼放在
        `python.exe`（第一候選會被排除），把真直譯器放在 `python3.cmd`
        （**不同**候選名稱、PATH 上沒有 python3 的空殼與它競爭），guard 對
        `python3` 這個全新候選重新走一次 `Get-Command python3`，天然只找到
        `real_dir` 底下那一個，不涉及「同一候選名稱有兩個 PATH 條目、跳過前
        面選後面」的場景，因此迴避掉了本測試揭露的問題。dev_start.ps1 只有
        `'python'` 一個候選名，沒有第二個候選名可用這招迴避。
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
            output = proc.stdout + proc.stderr
            self.assertNotIn("FAKE_PYTHON_INVOKED", output, output)
            self.assertNotEqual(proc.returncode, 0, output)
            self.assertIn("找不到", output)


# ---------------------------------------------------------------------------
# ④ repo-wide 前瞻防增生鎖：不得有新的 WindowsApps guard 獨立副本繞過 SSOT
#    （R40 Architect 架構最佳化）。
#
# 背景：本檔頂部 docstring 記載的復發模式（DEF-101-273/279/300/303）過去每次
# 都是「內嵌重寫」被人工掃描碰運氣抓到；R37 抽出 SSOT 後，①②節只鎖「3 個
# 已知具名檔案」的行為細節，若有人在 repo 別處新增第 4、5 個呼叫點卻忘記
# dot-source SSOT（或乾脆內嵌重寫一份判斷式），①②節完全看不見——這正是本節
# 要收斂的缺口：repo-wide 掃描「有沒有經過 SSOT」，不管新檔案叫什麼名字、
# 放在哪裡。
# ---------------------------------------------------------------------------
def _latest_sdd_root() -> Path:
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。

    手法與 tools/tests/test_ps1_bom.py 等既有測試一致：subprocess 呼叫
    scripts/sdd_version.py CLI（而非 process 內 import），避免 sys.path 汙染。
    """
    sdd_root = _REPO_ROOT / "AISDLC_SDD"
    resolver = sdd_root / "scripts" / "sdd_version.py"
    proc = subprocess.run(
        [sys.executable, str(resolver), "--sdd-root", str(sdd_root)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise AssertionError(
            f"LATEST 解析失敗（sdd_version.py rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return sdd_root / name


def _tracked_files(pattern: str) -> list[str]:
    """git tracked 且符合 glob pattern 的 repo-relative 路徑清單（fail-loud）。

    用 `git ls-files` 而非 `Path.rglob`：天然排除 `.git`／`.venv`／
    `__pycache__`／`node_modules`（只要未被 commit），且與同目錄下
    test_ps1_bom.py／test_bash32_compat.py 等既有測試同款慣例。
    """
    proc = subprocess.run(
        ["git", "-C", str(_REPO_ROOT), "-c", "core.quotePath=false",
         "ls-files", "--", pattern],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git ls-files 失敗（rc={proc.returncode}；stderr="
            f"{proc.stderr.strip()!r}）——掃描邊界不得靜默縮小"
        )
    return [line for line in proc.stdout.splitlines() if line]


_FROZEN_SDD_VERSION_RE = re.compile(r"^AISDLC_SDD/(AISDLC_SDD_v\d+\.\d+)/")


def _exclude_frozen_sdd_versions(paths: list[str], latest_name: str) -> list[str]:
    """排除 AISDLC_SDD 凍結版本（v0.01 ~ 除 LATEST 以外者）——凍結版依鐵律
    (CLAUDE.md「Copy-on-Evolve」慣例) 不應被新規則追殺歷史快照。"""
    kept = []
    for rel in paths:
        m = _FROZEN_SDD_VERSION_RE.match(rel)
        if m and m.group(1) != latest_name:
            continue
        kept.append(rel)
    return kept


_WINDOWSAPPS_LITERAL = "WindowsApps"
_SSOT_REL_PATH = "tools/lib/WindowsAppsGuard.ps1"

# Python 側 WindowsApps 空殼判斷式的站點偵測＝**雙錨聯集**（函式名 ∪ 判斷式字面值）。
#
# 沿革與 WHY（R56 訂正）：R56 前一輪把判準由函式名錨
# （`^\s*def _is_windows_apps_stub\b`）**取代**為判斷式運算式錨
# （`part\.lower\(\)\s*==\s*["']windowsapps["']`），理由是「逐字相同但只改函式名的
# 第二實作完整逃過」。本輪 Architect 與 SD 各自以進程內對照實測證明兩錨是**互補**
# 而非包含關係，取代等於一邊補洞一邊新開洞：
#   再發明變體                                            函式名錨  運算式錨
#   A 同名 + `part.lower() == "windowsapps"`（現行實作）      HIT     HIT
#   B 同名 + `"windowsapps" in [x.lower() for x in …parts]`  HIT     MISS ← 取代後新失守
#   C 同名 + `"windowsapps" in p.lower()`                    HIT     MISS ← 取代後新失守
#   D 改名 + 逐字同運算式                                     MISS    HIT  （前一輪修好的那格）
#   E 改名 + 另一種寫法                                       MISS    MISS （兩錨皆盲）
#   F 同名 + `"windowsapps" == part.lower()`（反向比較序）     HIT     MISS ← 取代後仍盲
# 故本輪改為**聯集**，並把判斷式錨從「運算式形狀」降級為「不可能被改名的小寫引號
# 字面值」——變體 B／C／F 都必然帶 `"windowsapps"` 字面值，一併收攏。
#
# R56 修正（讀表勿誤解）：上表兩欄是**兩個候選錨各自**的命中，其中「運算式錨」欄
# 描述的是**前一輪的**判準（`part\.lower\(\)\s*==\s*…`），**不是**本鎖最終部署的第二
# 錨（部署的是上述小寫引號字面值）。下表才是本鎖（雙錨聯集）的實際鑑別力，由本輪
# bug-injection 實測取得——把變體逐一注入一支生產 `.py`（`tools/check_hooks_liveness.py`），
# 在「強化前＝僅舊運算式錨」與「強化後＝本鎖」兩種狀態下各跑一次本測試：
#   變體                                                       強化前  強化後
#   A 同名 + 逐字同運算式                                        RED     RED
#   B 同名 + in 列表判斷                                        GREEN   RED
#   C 同名 + 路徑子串                                           GREEN   RED
#   D 改名 + 逐字同運算式                                        RED     RED
#   E 改名 + 另一種寫法（變體 B 去掉權威函式名）                  GREEN   RED ← 字面值錨新收攏
#   F 同名 + 反向比較序                                         GREEN   RED
#   G 迴圈變數改名 `seg`／`p`（改名，SD 構造）                    GREEN   RED
#   H `part.casefold() == "windowsapps"`（改名，SD 構造）        GREEN   RED
#   I `part.lower() in ("windowsapps",)`（改名，SD 構造）        GREEN   RED
#   K 改名 + 字面值嵌進更大字串（見下方「方法論邊界」）           GREEN   GREEN
# 即：8 種原本靜默通過的再發明形狀因本次強化轉為紅燈。
# 對照組（未注入任何變體）在兩種狀態下皆 GREEN，確認上述紅燈非環境雜訊。
#
# R56 round 5 修正（三位審查員互不知會、各自實測命中同一根因）：上表原本的結語寫
# 「唯一仍逃得掉的是 K」，該宣稱已被注入證偽——兩個錨當時都**大小寫敏感**，只要把
# 字面值或函式名寫成 repo 自己慣用的大寫 `WindowsApps` 就整組逃逸。本輪注入實測
# （同款手法，標的同樣是 `tools/check_hooks_liveness.py`）：
#   變體                                                        加旗標前  加旗標後
#   L  改名 + **裸大寫**字面值                                    GREEN     RED
#      `def _is_store_alias(p): return any(x == "WindowsApps" …)`
#   L2 對照組：同 L 但字面值為 `"windowsapps"`                     RED       RED
#   N  camelCase 函式名 `def isWindowsAppsStub(...)`（名錨側）     GREEN     RED
#   O  改名 + `("windows"+"apps")` 字串串接                       GREEN     GREEN
# L2 紅、L 綠即證明缺口就是 `re.I` 的缺席本身。觸發情境具體而非罕見：姊妹語言 SSOT
# `tools/lib/WindowsAppsGuard.ps1:55` 正是 `-notlike '*\WindowsApps\*'`（**大寫**），
# 仿照它在 Python 側新寫一份判斷式的人最自然就會打出變體 L 的形狀。故兩錨各補一個
# `re.I` 旗標（見下方常數；鑑別力由 `TestStubAnchorDiscriminatingPower` 常駐鎖住，
# 不必靠下一輪再做一次 bug-injection 才發現旗標被拿掉）。
#
# 零偽陽性實測（round 5 親自重跑本鎖自身的候選集合，非引用他人數字）：scoped prefix
# ∩ 非測試檔＝**378 支**生產 `.py`，「加旗標前 vs 加旗標後」命中集合**完全相同**
# （`pre_run_validator.py` ＋ `tools/bootstrap_core.py`），新增偽陽性 **0**。
#
# 已刪除的錯誤理由（round 5 訂正，勿再寫回）：本處原有一段「大小寫敏感（刻意）：
# `pre_run_validator.py` 的使用者訊息文字寫 `WindowsApps`，不分大小寫會把純文字提及
# 誤判為判斷式實作」。兩層皆不成立——該檔 L70/L98 是 `f"WindowsApps App Execution
# Alias 空殼（…"`，`WindowsApps` 後接**空白**，引號界定的 `["']windowsapps["']` 本來
# 就不匹配（已實測，且由下方 negative case 常駐鎖住）；且該檔早已登記在
# `_APPROVED_SECOND_IMPLS`，即使命中也不會翻紅。
#
# 精度取捨（2026-07-27 實測；round 5 在 re.I 下重驗仍成立）：引號界定必須保留。若改掃
# **裸**字面值，`windowsapps` 會多命中三支只是提及 `tools/lib/windowsapps_guard.sh`
# 檔名的守門工具（check_script_parity.py／check_wrapper_thinness.py／
# check_gha_action_versions.py）＝5 支；再加 re.I 還會多命中 boot_helper.py＝6 支。
# 「引號界定 ＋ re.I」則穩定維持在 2 支。
#
# 方法論邊界（如實揭露，勿留「已涵蓋全類別」錯覺）：**兩錨同時避開**者仍逃得掉。
# round 5 收攏 L／N 之後，既知邊界收斂為兩種——共同特徵是「字面值不以完整 token 形式
# 出現在一對引號內，且函式名不含 windows/apps 字樣」：
#   K 改名 + 把字面值嵌進更大字串（如
#     `def _stub_path(p): return "\\windowsapps\\" in p.lower()`）
#   O 改名 + 字串串接（如 `("windows"+"apps")`）
# 這是正則/靜態掃描
# 類防護的既知極限（同 DEF-101-333 對本測試家族殘留繞過向量的四方一致裁定：三方各自
# 構造出不同類型繞過＝已觸及逐行正則相對於 AST 解析的結構性天花板，誠實記載而不追殺。
# R56 訂正：本處原引 DEF-101-433，但該則的前提〔薄殼守門缺前瞻機制〕已於 R56 經
# bug-injection 證偽〔反向驗證實存於 check_script_parity.py〕，其「比例原則裁定」建立在
# 不成立的前提上，不宜作為判例；真正的判例是 DEF-101-333），
# 非本鎖可解。放大因素（R56 SD 指出，如實記載）：本鎖已是 Python 側的 repo-wide
# 前瞻掃描，但**只有這一層**——bash 側另有白名單斷言（`test_all_known_callers_source_
# shared_guard`／`test_no_raw_unguarded_python_check_remains`）與 repo-wide 掃描兩層
# 互相補位，Python 側破了本鎖即零訊號。
# R56 round 5 修正：兩錨皆補 `re.I`（名錨須寫成 `re.MULTILINE | re.I`，勿覆蓋掉
# 原有的 MULTILINE）。理由與零偽陽性實測見上方註解。
_STUB_NAME_RE = re.compile(r"^\s*def\s+\w*windows_?apps\w*", re.MULTILINE | re.I)
_STUB_PREDICATE_RE = re.compile(r"""["']windowsapps["']""", re.I)


def _matches_stub_anchor(text: str) -> bool:
    """兩錨的**聯集**——只要任一錨命中即視為「疑似第二份 stub 判斷式實作」。

    R56 round 6 修正（QA 複核以 bug-injection 證實）：本判定原本直接內聯寫在掃描
    迴圈裡（`_STUB_NAME_RE.search(text) or _STUB_PREDICATE_RE.search(text)`），
    使得「∪」這個 round 5 的**核心交付物本身完全無鎖**——把該處 `or` 改成 `and`
    （3 個字元），全檔 40 支測試維持 OK、變體 L（改名 ＋ 裸大寫字面值）完整逃逸。
    `TestStubAnchorDiscriminatingPower` 當時鎖住的是兩個錨**各自**的 `re.I`／
    `MULTILINE`／引號界定三項屬性，唯獨沒鎖住把它們接起來的運算子。

    觸發情境具體、非理論：下方「精度取捨」段明載放寬字面值會多出 5~6 支偽陽性，
    未來任何一次偽陽性壓力下，「改成必須兩個錨同時命中才算」都是最自然的收緊
    動作——它看起來像精度改善，且不會讓任何一支測試翻紅。

    抽成純函式後由 `TestStubAnchorDiscriminatingPower` 的兩支單錨樣本斷言鎖住
    （兩者在 `∩` 語意下必死），並與同檔 `_invokes_python_in_ps1`／
    `_all_python_invocations_are_ssot_protected` 的「測組合後純函式」慣例對齊
    ——原本只有 stub 這一側測裸 regex 常數，是對本檔自身慣例的偏離。
    """
    return bool(_STUB_NAME_RE.search(text) or _STUB_PREDICATE_RE.search(text))

# 已核准的第二份 Python 實作（附理由白名單，比照 `_EXEMPT_PS1_FILES` 慣例）。
_APPROVED_SECOND_IMPLS = {
    "AutoClaude/autoclaude/execution/pre_run_validator.py": (
        "`autoclaude` 為可獨立 pip 安裝的套件，不可 import monorepo 根層 "
        "tools/*.py（該檔 L25-28 明文論證，同 autoclaude/utils/logger.py "
        "`_sanitize_log_filename` 語言/套件邊界先例）；boot_helper.py 是從本檔 "
        "import 共用，非再寫第三份"
    ),
}


def _is_test_py(rel: str) -> bool:
    """是否為測試檔（`tools/tests/…`、`AutoClaude/tests/…`、`test_*.py`）——
    測試檔內出現判斷式字面值是「對 SSOT 內容做斷言」，非生產路徑第二實作。"""
    return "/tests/" in rel or Path(rel).name.startswith("test_")

# R44 Architect 深度架構評估找到的系統性缺口：`test_ps1_mentions_of_windowsapps_all_go_through_ssot`
# 只掃「檔案內文字提及 WindowsApps 字面值」者——若一支 .ps1 直接裸呼叫 python
# 卻從未提及 WindowsApps 這個字（例如只寫了 `Get-Command python` 或連
# `Get-Command` 判斷都沒有、直接 `& python ...`），舊判準完全不會去檢查它，
# 是比「有判斷但沒 SSOT」更原始的繞過形狀。以下為此新掃描（不再要求先提及
# WindowsApps 字面值）已知需要豁免的檔案，皆附理由：
#
# R44 二審 Architect 對抗式複審揪出：本清單原本還登記 `AISDLC_SDD/scripts/
# ci-gate.ps1`，理由引用 bash 側 `test_migrated_with_fallback_branch_is_not_flagged`
# 判例（guard 檔案物理缺席才降級用裸判斷）——但親自檢查 ci-gate.ps1 原始碼後
# 發現兩者並不對等：`tools/lib/WindowsAppsGuard.ps1` 在該情境下明明存在、可以
# 像本輪其他呼叫端一樣直接 dot-source 後判斷，只是先前選擇不接上，並非「做不
# 到」。既然可補救、成本又低（僅需 2 行），已直接補上 guard（見 ci-gate.ps1
# fallback 分支開頭），故該檔已從本豁免清單移除——多出的 SSOT dot-source +
# `Test-IsRealPython` 呼叫自然通過下方 repo-wide 掃描，成為新的回歸鎖。
#
# R44 SA 另一位一審對抗式複審（同一輪、獨立於上一段的 Architect 二審）對僅存的
# `AutoClaude/tools/g0_gate_check.ps1` 一筆豁免提出同款質疑：豁免理由（假設呼叫
# 者已透過 bootstrap.ps1／dev_start.ps1 整備過環境）本身只是「未強制的假設」——
# 沒有任何機制保證排程／人工執行這支腳本時，該次環境真的整備成功過，只要機器上
# 仍只有 WindowsApps 空殼，一樣會重現本輪要修的原始缺口。親自確認 `tools/lib/
# WindowsAppsGuard.ps1` 在該情境下同樣物理存在、可補救、成本同樣低（同款 2 行）
# ——故已直接補上 guard（見 g0_gate_check.ps1 開頭，`$Log`／`W()` 定義好之後、
# 兩處裸 `python` 呼叫之前），該檔已從本豁免清單移除，目前無殘留豁免項。
_EXEMPT_PS1_FILES: set[str] = set()

# 真正的 dot-source 呼叫語法（PowerShell dot-source 運算子只能出現在陳述式
# 開頭：行首（可有前導空白）緊接 `.` + 空白）。兩種既有呼叫端寫法皆須涵蓋：
#   ① 字面路徑：`. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"`（bootstrap.ps1／
#      dev_start.ps1）
#   ② 變數持有路徑：`. $WindowsAppsGuardPath`（install_post_commit.ps1，變數
#      名稱本身含 WindowsAppsGuard，其值由前面 `Join-Path ... "...
#      WindowsAppsGuard.ps1"` 組出）
# 只鎖「提及字串」會被 SD 對抗式驗證構造的偽裝繞過（把兩個子字串塞進註解／
# 字串常數即可放行）；改鎖「陳述式開頭的 dot-source 語法」才是本質判準。
_DOT_SOURCE_SSOT_RE = re.compile(
    r'^[ \t]*\.\s+(?:"[^"\n]*WindowsAppsGuard\.ps1"|\$\w*WindowsAppsGuard\w*)'
)
_TEST_IS_REAL_PYTHON_CALL_RE = re.compile(
    r'\bTest-IsRealPython\s+-CandidateName\b'
)


def _line_is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _strip_trailing_line_comment(line: str) -> str:
    """移除行尾不在字串常值內的 `#` 註解（PowerShell 行內註解字元）。

    R40 QA 二審對抗式驗證揪出：舊版只濾掉「整行以 `#` 開頭」的註解，未濾掉
    「程式碼陳述式後緊接的行尾註解」——攻擊者可在同一行放一段完全不相關的
    真實敘述（如 `Write-Host $x`），再接行尾註解裝飾性提及
    `Test-IsRealPython -CandidateName`，讓掃描器誤判為「真正呼叫」。逐字掃
    描追蹤是否身處雙/單引號字串內，遇到不在字串內的 `#` 即截斷該行之後的
    內容，關閉此裝飾性行尾註解繞過向量。"""
    in_double = False
    in_single = False
    for i, ch in enumerate(line):
        if ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == "#" and not in_double and not in_single:
            return line[:i]
    return line


def _quote_parity_open(line: str, pos: int) -> bool:
    """`pos` 之前的同一行文字內，雙引號或單引號的出現次數是否為奇數（代表
    `pos` 落在尚未關閉的字串常值內）。不處理跳脫字元——本專案 .ps1 呼叫端
    寫法皆簡單，足以擋下「呼叫語法整段藏在字串常數/註解裡偽裝」的繞過手法。
    """
    prefix = line[:pos]
    return (prefix.count('"') % 2 == 1) or (prefix.count("'") % 2 == 1)


def _has_real_dot_source_of_ssot(text: str) -> bool:
    """檔案中是否存在「真正的」dot-source SSOT 陳述式（非註解、非字串常值、
    非行尾裝飾性註解）。"""
    for raw_line in text.splitlines():
        if _line_is_comment(raw_line):
            continue
        line = _strip_trailing_line_comment(raw_line)
        m = _DOT_SOURCE_SSOT_RE.search(line)
        if m and not _quote_parity_open(line, m.start()):
            return True
    return False


_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)
_BARE_PYTHON_WORD_RE = re.compile(r"\bpython3?\b")


def _strip_block_comments(text: str) -> str:
    """移除 PowerShell `<# ... #>` 區塊註解（含 comment-based help），保留原本
    的換行數（用等量 `\\n` 取代整段，而非直接刪空）——避免區塊註解前後文字
    因刪除而被意外接合到同一行，干擾逐行掃描與同行的引號奇偶追蹤。"""
    return _BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _invokes_python_in_ps1(text: str) -> bool:
    """R44 Architect 深度架構評估找到的系統性缺口：檔案是否有呼叫
    python/python3 的痕跡——刻意用寬鬆的全字比對（不限定 `& python` 呼叫運算子
    語法），因為既有 7 支真實命中檔案的呼叫寫法不一致（`& python (...)`／裸
    `python -m ...`／裸 `python <script>.py ...`皆有）。逐行跳過整行註解 +
    行尾裝飾性註解（沿用 `_line_is_comment` / `_strip_trailing_line_comment`），
    並用 `_quote_parity_open` 排除純字串常值內的提及（如 Write-Host 印出的
    說明文字、或 `-CandidateName 'python'` 這種傳給共用函式的字面值參數，
    不是直接呼叫直譯器本身）。呼叫前須先 `_strip_block_comments`，否則
    `.DESCRIPTION`／`.EXAMPLE` 這類 comment-based help 區塊內提及 python 的
    說明文字會被誤判為真實呼叫。"""
    stripped_text = _strip_block_comments(text)
    for raw_line in stripped_text.splitlines():
        if _line_is_comment(raw_line):
            continue
        line = _strip_trailing_line_comment(raw_line)
        for m in _BARE_PYTHON_WORD_RE.finditer(line):
            if not _quote_parity_open(line, m.start()):
                return True
    return False


def _has_real_test_is_real_python_call(text: str) -> bool:
    """檔案中是否存在「真正呼叫」`Test-IsRealPython -CandidateName ...` 的陳
    述式（非註解、非字串常值、非行尾裝飾性註解——單純提及函式名稱不算，也
    不能是另一個函式名稱如 `Test-IsRealPython-Reimplemented` 的一部分，
    `-CandidateName` 參數名稱要求已天然排除此類命名混淆）。"""
    for raw_line in text.splitlines():
        if _line_is_comment(raw_line):
            continue
        line = _strip_trailing_line_comment(raw_line)
        for m in _TEST_IS_REAL_PYTHON_CALL_RE.finditer(line):
            if not _quote_parity_open(line, m.start()):
                return True
    return False


# ---------------------------------------------------------------------------
# R44 SA 一審對抗式複審揪出：`test_python_calls_in_ps1_all_go_through_ssot` 舊版
# 只做「檔案層級」判斷——`if _has_real_dot_source_of_ssot(text) and
# _has_real_test_is_real_python_call(text): continue` 只要檔案內某處存在真正
# 的 dot-source SSOT 陳述式、某處存在真正呼叫 Test-IsRealPython 的陳述式，
# 全檔即視為安全，不檢查每一個裸 python 呼叫點是否真的受該次判斷保護。實測：
# 把 `AutoClaude/tools/run_local_nightly.ps1` 改回「僅 1 處 guard、其餘 15+
# 處裸呼叫且與 guard 判斷結果無關」的狀態（bug-injection 對抗式驗證，改壞後
# 確認測試仍綠），該測試依舊全綠——因為判準只看「guard 是否存在」，不看
# 「guard 的判斷結果是否真的擋住了這些呼叫」。
#
# 修復：改為呼叫點層級判斷。掃描現存全部正確呼叫端（bootstrap.ps1／
# dev_start.ps1／local_ci_gate.ps1／run_act.ps1／integration_gate.ps1／
# GitHooksInstallCommon.ps1／windows_smoke_local.ps1／ci-gate.ps1／
# install_post_commit.ps1／run_self_evolution.ps1）後歸納出兩種目前皆存在、
# 皆合法的安全形狀：
#   (A) 「fail-fast 後裸呼叫」：guard 判斷失敗時緊接 `exit`/`return`/`throw`
#       提前結束，之後的裸 `python` 呼叫因此保證只在 guard 判斷通過時才會
#       執行到——這批呼叫端在 guard 呼叫後數行內（實測最大間隔 7 行）即有此
#       提前結束陳述式；
#   (B) 「變數替換」：guard 判斷結果存進變數（如 `$script:PyExe`），之後全部
#       呼叫點一律改用該變數（`& $script:PyExe ...`），檔案裡 `python` 字面值
#       本身不再作為呼叫出現（只留在 guard 呼叫自身的 `-CandidateName` 字面
#       值參數裡，本就已被引號奇偶排除）。
# 只要 guard 呼叫附近（同一視窗內）找不到提前結束陳述式，且檔案裡仍有真正的
# 裸 `python`/`python3` 呼叫，代表 guard 的判斷結果對這些呼叫點形同虛設，判
# 定為未受保護。
# ---------------------------------------------------------------------------
_EARLY_EXIT_RE = re.compile(r"\b(?:exit|return|throw)\b", re.IGNORECASE)
# 排除 Docker image tag 這種 `python:3.11-slim` 寫法（`run_local_nightly.ps1`
# 既有真實案例）——冒號緊接在後代表這是映像檔標籤字面值，不是呼叫直譯器。
_CALL_SHAPED_PYTHON_RE = re.compile(r"\bpython3?\b(?!:)")
# 觀察到的最大「guard 呼叫→提前結束陳述式」間隔為 7 行（tools/dev_start.ps1／
# tools/bootstrap.ps1 巢狀候選分支各自的判斷式與其提前結束陳述式之間）；window
# 取 15 行留有餘裕，同時遠小於 run_local_nightly.ps1 guard 呼叫到檔尾無關
# `exit 0` 的行距（750+ 行），不會誤將無關的檔尾退出陳述式當成此 guard 的
# fail-fast 保護。
_EARLY_EXIT_WINDOW = 15


def _real_match_line_indices(text: str, pattern: re.Pattern[str]) -> list[int]:
    """逐行掃描 `pattern`（先經 `_strip_block_comments` 前處理，保留行號對齊），
    回傳所有「真正」命中（非整行註解、非行尾裝飾性註解、非字串常值內）的
    0-based 行號列表。"""
    stripped_text = _strip_block_comments(text)
    indices: list[int] = []
    for i, raw_line in enumerate(stripped_text.splitlines()):
        if _line_is_comment(raw_line):
            continue
        line = _strip_trailing_line_comment(raw_line)
        for m in pattern.finditer(line):
            if not _quote_parity_open(line, m.start()):
                indices.append(i)
                break
    return indices


def _all_python_invocations_are_ssot_protected(text: str) -> bool:
    """呼叫點層級判斷（取代舊版純檔案層級判斷）：檔案內每一個真正的裸
    `python`/`python3` 呼叫，是否都能歸類到上方 docstring 記載的兩種已知安全
    形狀之一——(A) guard 判斷失敗時緊接 fail-fast、(B) guard 判斷結果存進變
    數後檔案裡已無真正的裸字面值呼叫。任一裸呼叫點找不到歸類即回傳 False。"""
    if not _has_real_dot_source_of_ssot(text):
        return False
    guard_lines = _real_match_line_indices(text, _TEST_IS_REAL_PYTHON_CALL_RE)
    if not guard_lines:
        return False
    call_lines = _real_match_line_indices(text, _CALL_SHAPED_PYTHON_RE)
    if not call_lines:
        return True  # (B) 變數替換：檔案裡已無真正的裸字面值呼叫
    guard_line = max(guard_lines)
    exit_lines = _real_match_line_indices(text, _EARLY_EXIT_RE)
    nearby_exit = [
        e for e in exit_lines if guard_line <= e <= guard_line + _EARLY_EXIT_WINDOW
    ]
    if not nearby_exit:
        return False  # (A) 不成立：guard 判斷附近找不到提前結束陳述式
    gate_line = min(nearby_exit)
    return all(c > gate_line for c in call_lines)  # 所有裸呼叫皆在提前結束之後


class TestInvokesPythonInPs1(unittest.TestCase):
    """R44 Architect 深度架構評估新增的鑑別力回歸鎖：直接對
    `_invokes_python_in_ps1` 純函式單元測試各種情境，確認寬鬆的全字比對不會
    誤判註解／字串內的提及為真實呼叫，也不會漏放各種既有呼叫寫法。"""

    def test_call_operator_invocation_is_detected(self) -> None:
        text = "& python (Join-Path $PSScriptRoot 'local_ci_gate.py') @CliArgs\n"
        self.assertTrue(_invokes_python_in_ps1(text))

    def test_bare_module_invocation_without_call_operator_is_detected(self) -> None:
        text = 'python -m tools.arch_fitness.arch_fitness --strict --quiet --json $JsonOut | Out-Null\n'
        self.assertTrue(_invokes_python_in_ps1(text))

    def test_bare_script_path_invocation_is_detected(self) -> None:
        text = '$ac4 = python tools/ac4_progress_check.py --history .ac4_history.jsonl --json 2>&1 | Out-String\n'
        self.assertTrue(_invokes_python_in_ps1(text))

    def test_mention_inside_double_quoted_string_is_not_flagged(self) -> None:
        text = (
            'Write-Host "  替代：bash tools/fsm_runtime/formal/run_tlc.sh，'
            '或五軌權威路徑 python -m tools.fsm_runtime.tlc_runner" -ForegroundColor Yellow\n'
        )
        self.assertFalse(_invokes_python_in_ps1(text))

    def test_candidate_name_literal_argument_is_not_flagged(self) -> None:
        """傳給共用函式的字面值參數（`-CandidateName 'python'`）是字串常值，
        不是直接呼叫直譯器——即使被漏判，這類檔案本就因具備
        `_has_real_dot_source_of_ssot` + `_has_real_test_is_real_python_call`
        而在上層被排除，本測試單純鎖住 helper 本身的鑑別力。"""
        text = "Test-IsRealPython -CandidateName 'python'\n"
        self.assertFalse(_invokes_python_in_ps1(text))

    def test_mention_inside_line_comment_is_not_flagged(self) -> None:
        text = "#    python -m tools.fsm_runtime.tlc_runner --module <五軌各一>\n"
        self.assertFalse(_invokes_python_in_ps1(text))

    def test_mention_inside_block_comment_help_is_not_flagged(self) -> None:
        text = (
            "<#\n.SYNOPSIS\n本地 nightly 排程腳本\n.EXAMPLE\n"
            "    python -m tools.arch_fitness.arch_fitness\n#>\n"
            "Write-Host 'ok'\n"
        )
        self.assertFalse(_invokes_python_in_ps1(text))

    def test_no_mention_at_all_is_not_flagged(self) -> None:
        self.assertFalse(_invokes_python_in_ps1("Write-Host 'hello'\n"))


class TestAllPythonInvocationsAreSsotProtected(unittest.TestCase):
    """R44 SA 一審對抗式複審回歸鎖：直接對
    `_all_python_invocations_are_ssot_protected` 純函式單元測試，鎖住「呼叫點
    層級」判斷的鑑別力——尤其是舊版「檔案層級」判準會誤判為安全的部分覆蓋情
    境（guard 存在，但呼叫點與其判斷結果無關）。"""

    _GUARD_HEADER = (
        '. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"\n'
        "if (Test-IsRealPython -CandidateName 'python') { $script:PyExe = 'python' }\n"
    )

    def test_fail_fast_pattern_with_many_bare_calls_after_is_protected(self) -> None:
        """(A) 形狀：guard 判斷失敗時緊接 exit，之後任意多個裸呼叫皆安全
        （比照 tools/bootstrap.ps1／local_ci_gate.ps1 既有實作）。"""
        text = (
            '. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"\n'
            "if (-not (Test-IsRealPython -CandidateName 'python')) {\n"
            "  Write-Host 'not found'\n"
            "  exit 1\n"
            "}\n"
            "& python tools/a.py\n"
            "python -m tools.b\n"
            "python tools/c.py\n"
        )
        self.assertTrue(_all_python_invocations_are_ssot_protected(text))

    def test_variable_substitution_pattern_with_no_bare_calls_is_protected(self) -> None:
        """(B) 形狀：guard 判斷結果存進變數，之後全部呼叫點改用該變數，檔案裡
        已無真正的裸字面值呼叫（比照 AutoClaude/tools/run_local_nightly.ps1
        既有實作，且不要求 guard 附近有 exit——設計上刻意不 fail-fast）。"""
        text = (
            self._GUARD_HEADER
            + "if (-not $script:PyExe) { Log 'not found' }\n"
            + "& $script:PyExe tools/a.py\n"
            + "& $script:PyExe -m tools.b\n"
        )
        self.assertTrue(_all_python_invocations_are_ssot_protected(text))

    def test_docker_image_tag_is_not_mistaken_for_a_bare_call(self) -> None:
        """`python:3.11-slim` 是 Docker image tag 字面值，不是呼叫直譯器——
        比照 AutoClaude/tools/run_local_nightly.ps1 mutation stage 既有實作，
        不應被計入需要保護的裸呼叫點。"""
        text = (
            self._GUARD_HEADER
            + "if (-not $script:PyExe) { Log 'not found' }\n"
            + "docker run --rm python:3.11-slim bash script.sh\n"
            + "& $script:PyExe tools/a.py\n"
        )
        self.assertTrue(_all_python_invocations_are_ssot_protected(text))

    def test_guard_exists_but_unrelated_bare_calls_afterward_is_not_protected(self) -> None:
        """R44 SA 一審對抗式複審實測構造的核心反例：guard（dot-source +
        Test-IsRealPython 呼叫）確實存在，但其判斷結果從未 gate 任何東西——
        既未 fail-fast、也未存進變數給後續呼叫點使用——後續裸呼叫點與 guard
        判斷結果無關。舊版檔案層級判準只看「guard 是否存在」會誤判為安全
        （PASSED，本該 FAILED）；本測試鎖住新版呼叫點層級判準能正確抓到。"""
        text = (
            self._GUARD_HEADER
            + "if (-not $script:PyExe) { Log 'not found' 'ERROR' } else { Log 'ok' }\n"
            + "& python tools/a.py\n"  # 裸呼叫：與 $script:PyExe 判斷結果無關
            + "python -m tools.b\n"
        )
        self.assertFalse(_all_python_invocations_are_ssot_protected(text))

    def test_bare_call_before_the_guard_is_not_protected(self) -> None:
        """即使檔案稍後有 fail-fast，發生在 guard 判斷之前的裸呼叫仍不安全
        （guard 尚未執行，判斷結果不可能保護到它）。"""
        text = (
            "& python tools/too_early.py\n"
            + '. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"\n'
            + "if (-not (Test-IsRealPython -CandidateName 'python')) {\n"
            + "  exit 1\n"
            + "}\n"
        )
        self.assertFalse(_all_python_invocations_are_ssot_protected(text))

    def test_missing_dot_source_is_not_protected_even_with_guard_call(self) -> None:
        text = (
            "if (-not (Test-IsRealPython -CandidateName 'python')) { exit 1 }\n"
            "& python tools/a.py\n"
        )
        self.assertFalse(_all_python_invocations_are_ssot_protected(text))

    def test_missing_guard_call_is_not_protected_even_with_dot_source(self) -> None:
        text = (
            '. "$PSScriptRoot/lib/WindowsAppsGuard.ps1"\n'
            "& python tools/a.py\n"
        )
        self.assertFalse(_all_python_invocations_are_ssot_protected(text))


class TestStubAnchorDiscriminatingPower(unittest.TestCase):
    """R56 round 5 新增：直接對 `_STUB_NAME_RE`／`_STUB_PREDICATE_RE` 兩個錨做純
    函式鑑別力測試（比照本檔 `TestInvokesPythonInPs1` 慣例）。

    WHY 不只靠上方 repo-wide 掃描：掃描鎖只會在「repo 裡真的出現第二實作」時才
    翻紅，兩個錨的鑑別力被悄悄弱化（例如有人拿掉 `re.I`，或把名錨的
    `re.MULTILINE | re.I` 誤寫回單一旗標）時完全零訊號——round 5 之前的大小寫
    敏感缺口正是這樣存活到第四輪複審才被三方各自以 bug-injection 撞出來。本
    class 把那次 bug-injection 的結論固化成常駐斷言：旗標被拿掉即紅。
    """

    def test_union_catches_name_only_reinvention(self) -> None:
        """R56 round 6（QA 複核）：**只有名錨命中**的形狀——函式名帶 WindowsApps
        但字面值以字串串接組出，判斷式錨盲。掃描端若把兩錨的 `or` 收緊為 `and`，
        本例即逃逸（QA 實測：改 3 個字元後全檔 40 支測試仍 OK）。"""
        self.assertTrue(_matches_stub_anchor(
            'def isWindowsAppsStub(p):\n'
            '    return any(s.casefold() == ("win" + "dowsapps") for s in p.parts)\n'
        ))

    def test_union_catches_predicate_only_reinvention(self) -> None:
        """R56 round 6（QA 複核）：**只有判斷式錨命中**的形狀——函式名完全不含
        windows/apps（名錨盲），靠裸大寫字面值被判斷式錨收攏。與上一支共同鎖住
        「∪」語意本身，兩者在 `∩` 下必死。"""
        self.assertTrue(_matches_stub_anchor(
            'def _store_alias_path(p):\n'
            '    return any(x == "WindowsApps" for x in p.parts)\n'
        ))

    def test_name_anchor_matches_camel_case_reinvention(self) -> None:
        """變體 N：camelCase 函式名（`re.I` 缺席時整組逃逸）。"""
        self.assertRegex("def isWindowsAppsStub(p):\n", _STUB_NAME_RE)

    def test_name_anchor_still_matches_canonical_snake_case(self) -> None:
        self.assertRegex("def _is_windows_apps_stub(p):\n", _STUB_NAME_RE)

    def test_name_anchor_keeps_multiline_semantics(self) -> None:
        """`re.MULTILINE` 不得因補 `re.I` 而被覆蓋掉：`^` 必須仍能錨到檔案中間
        任一行的行首（實務上判斷式不會出現在檔案第一行）。"""
        self.assertRegex("import os\n\n\ndef _is_windows_apps_stub(p):\n", _STUB_NAME_RE)

    def test_predicate_anchor_matches_upper_case_literal(self) -> None:
        """變體 L：**裸大寫**字面值——與姊妹語言 SSOT
        `tools/lib/WindowsAppsGuard.ps1` 的 `'*\\WindowsApps\\*'` 同款寫法，是
        仿照它新寫 Python 判斷式時最自然會打出的形狀。"""
        self.assertRegex('any(x == "WindowsApps" for x in p.parts)', _STUB_PREDICATE_RE)

    def test_predicate_anchor_still_matches_lower_case_literal(self) -> None:
        """變體 L2 對照組：`re.I` 缺席時本例即已翻紅，L 卻放行——兩者的差異就是
        缺口本身，故兩例都要鎖。"""
        self.assertRegex('part.lower() == "windowsapps"', _STUB_PREDICATE_RE)

    def test_predicate_anchor_does_not_match_prose_mention(self) -> None:
        """零偽陽性的關鍵 negative case（取自 `pre_run_validator.py:98` 實際文字）：
        引號後緊接 `WindowsApps` 但其後是**空白**而非引號，屬使用者訊息文字而非
        判斷式，補 `re.I` 後仍不得命中——這正是被 round 5 證偽的「刻意大小寫敏感」
        理由所擔心的情境，實際由引號界定（而非大小寫）擋下。"""
        self.assertNotRegex(
            'f"WindowsApps App Execution Alias 空殼（{resolved}），"', _STUB_PREDICATE_RE
        )

    def test_predicate_anchor_does_not_match_guard_script_filename(self) -> None:
        """另一個零偽陽性關鍵 negative case：守門工具提及的
        `"tools/lib/windowsapps_guard.sh"` 檔名（`windowsapps` 後接 `_`），
        補 `re.I` 後仍不得命中（見上方「精度取捨」段）。"""
        self.assertNotRegex('"tools/lib/windowsapps_guard.sh"', _STUB_PREDICATE_RE)


class TestNoOrphanWindowsAppsImplementation(unittest.TestCase):
    """repo-wide 前瞻防增生鎖——任何新增的呼叫點／獨立副本都逃不過。

    ①②節（`TestWindowsAppsGuardEnrollment`／`TestWindowsAppsGuardSharedFunctionBehavior`）
    只守「3 個已知呼叫端」的行為細節；本 class 守「repo-wide 有沒有新的獨立
    副本繞過 SSOT」——兩者分工互補，缺一不可。
    """

    def test_ps1_mentions_of_windowsapps_all_go_through_ssot(self) -> None:
        """任何提及 `WindowsApps` 字面字串的 .ps1 檔案，必須是 SSOT 本身，或
        同時具備「真正的」dot-source SSOT 陳述式與「真正呼叫」
        `Test-IsRealPython` 的陳述式——否則列為 offender（獨立副本嫌疑）。

        R40 SD 對抗式驗證實測揪出前版漏洞：舊判定僅檢查全檔文字是否「同時
        含有 `WindowsAppsGuard.ps1` 與 `Test-IsRealPython` 兩個子字串」，
        SD 構造出一個完全獨立重寫判斷邏輯、從未 dot-source SSOT 的 .ps1，
        只在註解裡提及這兩個子字串做偽裝，就騙過了測試（PASSED，本該
        FAILED）。改為 `_has_real_dot_source_of_ssot` /
        `_has_real_test_is_real_python_call`：要求匹配的是陳述式開頭的
        dot-source 語法、以及非註解非字串常值的實際函式呼叫，而非任意位置
        的文字提及；並在此基礎上濾掉行尾裝飾性註解（`_strip_trailing_line_comment`），
        關閉 QA 二審用「真實程式碼行 + 行尾裝飾性註解偽裝呼叫」構造出的第二
        種繞過。

        **已知殘留限制（如實記載，非本測試涵蓋範圍，列 R41 backlog）**：本
        測試是逐行靜態文字/正則掃描，非真正的 PowerShell AST 解析或執行期
        驗證，因此仍可被以下手法繞過（R40 四方複審中 Architect 與 QA 各自
        獨立構造並驗證成立，判定為此類前瞻鎖依 Rule 2 比例原則暫不需要更
        重的 AST 層修復，但必須誠實記載，不可讓人誤以為已完全封閉）：
        (a) 檔案中存在「真實但死碼」的 dot-source SSOT 陳述式（語法正確、
            執行期真的會讀入該檔案），但實際生效的判斷邏輯是另一個完全獨立
            重寫的函式，`Test-IsRealPython` 只在從未被呼叫的死碼分支或無關
            變數指派中「提及」（Architect 複審實測構造）；
        (b) 把兩段魔法字串包進 PowerShell here-string（`@"..."@`/`@'...'@`）
            當誘餌，本測試的逐行引號奇偶追蹤不追蹤跨行 here-string 開闔狀
            態，門外的真正獨立重寫邏輯因此不會被辨識為 offender（QA 複審
            實測構造）。
        若未來要徹底封閉，需要真正的 PowerShell AST 解析（追蹤變數賦值是否
        被實際呼叫使用、正確處理 here-string 狀態機），而非本測試目前採用
        的逐行正則掃描；在該投入被判定值得之前，此為已知的方法論邊界。
        """
        latest_name = _latest_sdd_root().name
        scoped_ps1 = _exclude_frozen_sdd_versions(_tracked_files("*.ps1"), latest_name)

        offenders = []
        for rel in scoped_ps1:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if _WINDOWSAPPS_LITERAL not in text:
                continue
            if rel == _SSOT_REL_PATH:
                continue  # SSOT 本身
            if _has_real_dot_source_of_ssot(text) and _has_real_test_is_real_python_call(text):
                continue  # 正確經過 SSOT dot-source + 呼叫
            offenders.append(rel)

        self.assertEqual(
            offenders, [],
            "發現提及 WindowsApps 但未經 SSOT（須同時具備真正的 dot-source "
            "tools/lib/WindowsAppsGuard.ps1 陳述式 + 真正呼叫 "
            f"Test-IsRealPython 陳述式）的 .ps1 檔案，疑似獨立副本繞過共用"
            f"函式：{offenders}——新呼叫點須 dot-source tools/lib/"
            "WindowsAppsGuard.ps1 後呼叫 Test-IsRealPython，不得內嵌重新發明"
            "判斷式（同本檔頂部 docstring 記載的 DEF-101-273/279/300/303 復發模式）",
        )

    def test_python_calls_in_ps1_all_go_through_ssot(self) -> None:
        """R44 Architect 深度架構評估找到的系統性缺口：上一測試
        （`test_ps1_mentions_of_windowsapps_all_go_through_ssot`）只掃『檔案內
        文字提及 WindowsApps 字面值』者，抓不到『整支檔案從頭到尾根本沒有
        任何 WindowsApps 相關字樣、直接裸呼叫 python』這個更原始形狀——例如
        `AutoClaude/tools/local_ci_gate.ps1`／`run_act.ps1`／
        `tools/integration_gate.ps1`／`tools/lib/GitHooksInstallCommon.ps1`／
        `tools/windows_smoke_local.ps1` 確實有 `Get-Command python` 判斷，但
        從未提及 WindowsApps，故被舊判準完全忽略；
        `AutoClaude/tools/run_local_nightly.ps1` 與
        `AISDLC_SDD/AISDLC_SDD_v0.30/tools/arch_fitness/run_self_evolution.ps1`
        更是連 `Get-Command python` 判斷都沒有，直接裸呼叫。

        本測試 repo-wide 掃描全部 tracked `*.ps1`（同上排除凍結版本），找出
        「呼叫 python 但未 dot-source WindowsAppsGuard.ps1 且未呼叫
        Test-IsRealPython」者，不再要求先提及 WindowsApps 字面值才檢查。

        R44 SA 一審對抗式複審追加揪出：初版判準仍是「檔案層級」——只要檔案內
        某處存在 dot-source SSOT 陳述式、某處存在 Test-IsRealPython 呼叫，全
        檔即視為安全，不檢查每個裸 python 呼叫點是否真的受該次判斷保護。實測
        把 `AutoClaude/tools/run_local_nightly.ps1` 改回「僅 1 處 guard、其餘
        15+ 處裸呼叫且與 guard 判斷結果無關」的狀態，該測試仍全綠，證實此掃描
        鎖抓不到「guard 已檢查、但呼叫點根本沒接上其判斷結果」的部分覆蓋缺口
        （已修復＋自動化鎖護航的雙重假象）。改用
        `_all_python_invocations_are_ssot_protected`：改為呼叫點層級，要求每
        一個真正的裸呼叫都能歸類到現存兩種已知安全形狀之一——(A) guard 判斷
        失敗時緊接 fail-fast（`exit`/`return`/`throw`），之後的裸呼叫因此保
        證只在判斷通過時才會執行到；或 (B) guard 判斷結果存進變數、之後全部
        呼叫點改用該變數（檔案裡已無真正的裸字面值呼叫）。任一裸呼叫點找不
        到歸類即判定未受保護（見該函式與其呼叫的 helper docstring）。
        """
        latest_name = _latest_sdd_root().name
        scoped_ps1 = _exclude_frozen_sdd_versions(_tracked_files("*.ps1"), latest_name)

        offenders = []
        for rel in scoped_ps1:
            if rel == _SSOT_REL_PATH or rel in _EXEMPT_PS1_FILES:
                continue
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if not _invokes_python_in_ps1(text):
                continue
            if _all_python_invocations_are_ssot_protected(text):
                continue  # 每個真正的裸呼叫點皆已歸類到已知安全形狀 (A)/(B)
            offenders.append(rel)

        self.assertEqual(
            offenders, [],
            "發現呼叫 python 但未經 SSOT（須同時具備真正的 dot-source "
            "tools/lib/WindowsAppsGuard.ps1 陳述式 + 真正呼叫 "
            f"Test-IsRealPython 陳述式）的 .ps1 檔案：{offenders}——新呼叫點須"
            "dot-source tools/lib/WindowsAppsGuard.ps1 後呼叫 "
            "Test-IsRealPython，不得裸呼叫 python（同本檔頂部 docstring 記載的"
            "DEF-101-273/279/300/303 復發模式；R44 Architect 深度架構評估：舊"
            "判準僅在檔案提及 WindowsApps 字面值時才檢查，本測試移除此前提，"
            "或於 _EXEMPT_PS1_FILES 附理由登記豁免）",
        )

    def test_known_call_sites_still_exist(self) -> None:
        """已知清單防腐化：5 個正確呼叫端須持續存在，避免清單本身腐化成
        「檔案已刪除／改名但測試仍宣稱通過」的假綠。

        `AISDLC_SDD/scripts/ci-gate.ps1` 為 R44 二審新收斂的第 4 個呼叫端
        （原豁免清單登記，經對抗式複審揪出豁免理由與既有判例不對等後補上
        guard，見 `_EXEMPT_PS1_FILES` 前方註解）。`AutoClaude/tools/
        g0_gate_check.ps1` 為同輪另一位一審對抗式複審對僅存豁免提出同款質疑後
        新收斂的第 5 個呼叫端（同一原因：豁免清單現已清空）。"""
        latest_name = _latest_sdd_root().name
        known = [
            _REPO_ROOT / "tools" / "bootstrap.ps1",
            _REPO_ROOT / "tools" / "dev_start.ps1",
            _REPO_ROOT / "AISDLC_SDD" / latest_name / "tools" / "install_hooks"
            / "install_post_commit.ps1",
            _REPO_ROOT / "AISDLC_SDD" / "scripts" / "ci-gate.ps1",
            _REPO_ROOT / "AutoClaude" / "tools" / "g0_gate_check.ps1",
        ]
        for path in known:
            self.assertTrue(path.is_file(), f"已知呼叫端遺失：{path}")

    def test_windows_apps_predicate_impls_are_all_registered(self) -> None:
        """Python 側 WindowsApps 空殼判斷式的實作站點必須全部登記在案。

        R56 訂正（原名 `test_is_windows_apps_stub_defined_exactly_once`）：舊判準
        以**函式名**為錨（`^\\s*def _is_windows_apps_stub\\b`），而
        `AutoClaude/autoclaude/execution/pre_run_validator.py:33` 的第二份實作
        判斷式**逐字相同**、只差函式名多兩個字（`_is_windows_apps_alias_stub`），
        在掃描範圍內（`AutoClaude/` 前綴）卻完整逃過，斷言訊息宣稱的「只出現
        一次」因此為假、鎖零訊號。改以**判斷式內容**為錨，並比照本檔
        `_EXEMPT_PS1_FILES`／bash 側 `_EXEMPT_SH_FILES` 的「附理由白名單」慣例
        登記已核准的第二實作。

        R56 二次訂正（本輪 Architect／SD 各自實測揪出）：上述「取代」是平移而非
        升級——函式名錨與運算式錨互補，取代後「同名但換寫法」的變體反而新失守。
        本鎖現以 `_STUB_NAME_RE`（函式名）∪ `_STUB_PREDICATE_RE`（引號界定的
        `windowsapps` 字面值）雙錨判定，涵蓋範圍與兩錨各自盲區的完整對照表見兩個
        常數上方註解。

        R56 round 5 三次訂正（三位審查員互不知會、各自 bug-injection 命中同一根因）：
        兩錨原本都**大小寫敏感**，把字面值／函式名寫成 repo 慣用的大寫 `WindowsApps`
        即整組逃逸；兩錨各補 `re.I` 後收攏（378 支候選生產 `.py` 實測命中集合不變、
        新增偽陽性 0）。**本鎖仍不宣稱涵蓋「重新發明」全類別**：改名且把字面值嵌進
        更大字串（K）或以字串串接組出（O）者仍逃得掉，屬正則/靜態掃描類防護的既知
        邊界。

        白名單腐化保護：登記項若被刪除／改寫成不再命中任一錨，`hits` 就不會
        包含它而使本鎖翻紅（等值斷言天然含 stale 檢查），不會靜默留著死條目。

        測試檔本身排除在外：`tools/tests/*` 內出現同一字面值是「對 SSOT 內容
        做斷言」（如上方 `test_bootstrap_core_py_has_symmetric_stub_detector`），
        不是生產路徑上的第二實作。

        R56 round 5 修正（QA 複核以 bug-injection 證實）：本鎖原本另以
        `scoped_prefixes = ("AutoClaude/", "tools/", f"AISDLC_SDD/{LATEST}/")`
        縮面，導致 16 支生產 `.py` 完全不被掃——`.claude/hooks/sdd_hook_router.py`、
        `AISDLC_SDD/conftest.py` 與 `AISDLC_SDD/scripts/` 下 14 支。把逐字相同的
        canonical 第二實作放進其中任一支，本鎖 100% 綠燈。而同檔兩支 `.ps1` 掃描與
        姊妹鎖 `test_windowsapps_guard_bash_parity.py` 的 `.sh` 掃描**都是無前綴、
        repo-wide**（只排凍結版）——即三語言中唯獨 Python 側被縮面，正是本輪主題
        所指的「平台/語言待遇不對稱」。改為與姊妹掃描同政策：只排凍結版與測試檔。
        實測：候選由 378 → 394 支，命中集合完全不變（仍為 `pre_run_validator.py`
        ＋ `bootstrap_core.py`），新增偽陽性 0，故取消縮面零代價。
        """
        latest_name = _latest_sdd_root().name
        all_py = _exclude_frozen_sdd_versions(_tracked_files("*.py"), latest_name)
        candidate_py = [rel for rel in all_py if not _is_test_py(rel)]

        hits = []
        for rel in candidate_py:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if _matches_stub_anchor(text):
                hits.append(rel)

        expected = sorted(["tools/bootstrap_core.py", *_APPROVED_SECOND_IMPLS])
        self.assertEqual(
            sorted(hits), expected,
            f"WindowsApps 判斷式的實作站點與登記不符（雙錨，皆不分大小寫：函式名 "
            f"`def \\w*windows_?apps\\w*` ∪ 引號界定字面值 `\"windowsapps\"`）——"
            f"實測：{sorted(hits)}；登記：{expected}。多出的站點代表**本鎖涵蓋範圍內**"
            f"出現新的 Python 側判斷實作（繞過 SSOT），若確有語言/套件邊界理由請在"
            f"`_APPROVED_SECOND_IMPLS` 附理由登記；少掉的站點代表登記已腐化"
            f"（檔案移除或兩錨皆不再命中），請同步清單",
        )

    def test_scan_loop_goes_through_matches_stub_anchor(self) -> None:
        """R57 新增（A4）：**掃描端本身**必須走 `_matches_stub_anchor()`。

        WHY：R56 round 6 把「兩錨聯集」抽成純函式並補了兩支單錨樣本測試，鎖住的
        只是 helper 內部語意（`or` 不得收緊為 `and`）。掃描迴圈**呼叫誰**這件事
        沒有任何鎖——把上一支測試裡的 `if _matches_stub_anchor(text):` 換回內聯
        `if _STUB_NAME_RE.search(text) and _STUB_PREDICATE_RE.search(text):`
        （繞過 helper ＋ 翻運算子的複合動作），helper 的兩支單錨測試依然全綠，
        變體 L 完整逃逸——等於 round 6 的修復被整個繞過。本斷言直接讀掃描測試的
        原始碼，要求它呼叫 helper、且不得內聯任一裸錨。
        """
        import inspect

        # 剝除 docstring：上一支測試的 docstring 詳述了兩個裸錨的沿革（會讓下方
        # `assertNotIn` 假紅），本斷言只針對可執行碼。
        src = re.sub(
            r'"""(?:.|\n)*?"""',
            "",
            inspect.getsource(
                type(self).test_windows_apps_predicate_impls_are_all_registered
            ),
        )
        self.assertIn(
            "_matches_stub_anchor(", src,
            "repo-wide 掃描迴圈未呼叫 `_matches_stub_anchor()`——兩錨聯集語意的"
            "唯一真相源被繞過，helper 的單錨測試對此零訊號",
        )
        for raw_anchor in ("_STUB_NAME_RE", "_STUB_PREDICATE_RE"):
            self.assertNotIn(
                raw_anchor, src,
                f"掃描迴圈直接內聯裸錨 `{raw_anchor}`——請一律經 "
                "`_matches_stub_anchor()`，否則聯集/交集語意可被就地改寫而無訊號",
            )


if __name__ == "__main__":
    unittest.main()
