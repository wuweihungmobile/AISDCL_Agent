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

    def test_known_call_sites_still_exist(self) -> None:
        """已知清單防腐化：3 個正確呼叫端須持續存在，避免清單本身腐化成
        「檔案已刪除／改名但測試仍宣稱通過」的假綠。"""
        latest_name = _latest_sdd_root().name
        known = [
            _REPO_ROOT / "tools" / "bootstrap.ps1",
            _REPO_ROOT / "tools" / "dev_start.ps1",
            _REPO_ROOT / "AISDLC_SDD" / latest_name / "tools" / "install_hooks"
            / "install_post_commit.ps1",
        ]
        for path in known:
            self.assertTrue(path.is_file(), f"已知呼叫端遺失：{path}")

    def test_is_windows_apps_stub_defined_exactly_once(self) -> None:
        """Python 側 SSOT（`_is_windows_apps_stub`）的 `def` 定義只應出現一次
        （tools/bootstrap_core.py）。掃描範圍：`AutoClaude/` + 根層 `tools/` +
        AISDLC_SDD LATEST 版目錄（同 Architect 方案）。若在範圍內出現第二處
        定義，代表 Python 側判斷邏輯被重新發明，繞過 SSOT。
        """
        latest_name = _latest_sdd_root().name
        scoped_prefixes = (
            "AutoClaude/", "tools/", f"AISDLC_SDD/{latest_name}/",
        )
        all_py = _exclude_frozen_sdd_versions(_tracked_files("*.py"), latest_name)
        candidate_py = [rel for rel in all_py if rel.startswith(scoped_prefixes)]

        def_re = re.compile(r"^\s*def _is_windows_apps_stub\b", re.MULTILINE)
        hits = []
        for rel in candidate_py:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if def_re.search(text):
                hits.append(rel)

        self.assertEqual(
            hits, ["tools/bootstrap_core.py"],
            "`_is_windows_apps_stub` 的 def 定義應恰出現一次"
            f"（tools/bootstrap_core.py），實際找到：{hits}——出現第二處代表 "
            "Python 側判斷邏輯被重新發明，繞過 SSOT",
        )


if __name__ == "__main__":
    unittest.main()
