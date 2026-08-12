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

import ast
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# 🔴 R80 S5-03：`_bash_exe()` 原本在本檔獨立寫一份，docstring 逐字宣稱那是「各消費者
# 獨立重寫」的架構慣例。實測：本檔那份與 `test_windowsapps_guard_bash_parity.py` 的
# 同名函式是同一段程式碼的兩份手抄，且**已經漂移**——本檔寫 `except OSError`、對面寫
# `except Exception`。`subprocess.TimeoutExpired` 繼承 `SubprocessError` 而不是
# `OSError` ⇒ 候選一旦卡住，本檔那份會讓例外逸出、module import 期就炸，對面那份會
# 安靜換下一個候選。兩份的行為分歧沒有任何一支測試在比對，也就是說「獨立重寫」在這裡
# 只買到兩種失敗模式。兩份收斂至既有 SSOT。
from _platform_helpers import usable_bash_for_fixture as _bash_exe  # noqa: E402
from _ps_engine import production_engine  # noqa: E402  # R60 DEF-101-548：引擎述詞 SSOT

_REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import git_paths  # noqa: E402  ← git 路徑列舉唯一取數層
import sdd_latest  # noqa: E402

_BOOTSTRAP_PS1 = _REPO_ROOT / "tools" / "bootstrap.ps1"
_DEV_START_PS1 = _REPO_ROOT / "tools" / "dev_start.ps1"
_BOOTSTRAP_CORE_PY = _REPO_ROOT / "tools" / "bootstrap_core.py"
_GUARD_PS1 = _REPO_ROOT / "tools" / "lib" / "WindowsAppsGuard.ps1"
_GUARD_SH = _REPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh"

# 共用函式的 dot-source 相對路徑（兩份呼叫端皆直接位於 tools/ 下，故皆為
# "lib/WindowsAppsGuard.ps1"；一併鎖住路徑片段本身，防呼叫端誤用其他相對路徑）
_DOT_SOURCE_RE = re.compile(
    r'\.\s+"\$PSScriptRoot/lib/WindowsAppsGuard\.ps1"'
)
_INLINE_NOTLIKE_RE = re.compile(r"-notlike\s+'\*\\WindowsApps\\\*'")

# R67 B3 修法後的 guard 邏輯本體形狀：以 `[\\/]` 切段 + 對段做小寫精確比對
# （比照姊妹 capability `tools/lib/Find-GitBash.ps1::Test-HasSystem32Segment`）。
_SEGMENT_SPLIT_RE = re.compile(r"-split\s+'\[\\\\/\]\+'")
_SEGMENT_EQ_RE = re.compile(r"ToLowerInvariant\(\)\s+-eq\s+'windowsapps'")

_PS_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)


def _ps_code_only(text: str) -> str:
    """剝掉 PowerShell 註解（`<# … #>` 區塊註解與 `#` 行尾註解），只留程式碼。

    🔴 R67 B3 才發現的假綠通道：`test_shared_guard_file_exists_and_defines_the_function`
    對整檔文字 `assertRegex(_INLINE_NOTLIKE_RE)`，而 R67 修法把舊寫法
    `-notlike '*\\WindowsApps\\*'` **原文引述**寫進了 `<# … #>` 檔頭沿革說明——
    邏輯本體已改成逐段比對，該斷言卻仍靠註解裡的字面值維持全綠（一個「宣稱鎖住
    邏輯本體、實際只鎖住字串曾出現過」的鎖，與本檔 R46 在 bash 側修過的
    `_has_ssot_guard` 是同一個病）。故靜態斷言一律先過本函式。

    侷限（誠實記載）：`#` 判定不追蹤字串內文，`"abc#def"` 這種行會被截斷。
    `WindowsAppsGuard.ps1` 現無此形狀；真正的行為鑑別力由下方 ④ 行為表 parity
    負責，本函式只是不讓靜態鎖被註解餵成假綠。
    """
    body = _PS_BLOCK_COMMENT_RE.sub("", text)
    return "\n".join(line.split("#", 1)[0] for line in body.splitlines())


def _pwsh_exe() -> str | None:
    """委派 `_ps_engine.production_engine()`（R60 收斂，DEF-101-548）。

    原實作是 `shutil.which("pwsh") or shutil.which("powershell")`＝**pwsh 7 優先**，
    與 R59 DEF-101-509 拍板的「生產引擎（Windows PowerShell 5.1）優先、pwsh 只作
    本機無 5.1 時的兜底」**方向相反**——本檔驗的正是受 `tools/` 5.1 政策約束的
    `bootstrap.ps1`／`dev_start.ps1`／`WindowsAppsGuard.ps1`，用 pwsh 7 去驗會讓
    「只在 5.1 上壞掉」的語法/語意差異整批漏放。函式名保留不改（呼叫點 4 處、
    語意不變＝「拿一個引擎來真跑」），只把引擎選擇交給唯一具名述詞。
    """
    return production_engine()


# ---------------------------------------------------------------------------
# ① 存在性檢查：呼叫端須 dot-source 共用檔案 + 呼叫共用函式，且不得殘留內嵌判斷式
# ---------------------------------------------------------------------------
class TestWindowsAppsGuardEnrollment(unittest.TestCase):
    def setUp(self) -> None:
        self.bootstrap_text = _BOOTSTRAP_PS1.read_text(encoding="utf-8")
        self.dev_start_text = _DEV_START_PS1.read_text(encoding="utf-8")
        self.guard_text = _GUARD_PS1.read_text(encoding="utf-8")

    def test_shared_guard_file_exists_and_defines_the_function(self) -> None:
        """guard 邏輯本體必須在（且是 R67 修法後的逐段比對形狀）。

        🔴 R67 B3：本測試原本 `assertRegex(self.guard_text, _INLINE_NOTLIKE_RE)`
        ——比對**整檔文字**，而修法把舊寫法原文引述進了 `<# … #>` 沿革說明，於是
        邏輯本體換掉了、斷言仍靠註解裡的字面值全綠。改為 (a) 只看非註解程式碼、
        (b) 斷言**新形狀在**且**舊形狀不在**（舊形狀回歸＝B3 復發）。
        """
        self.assertTrue(_GUARD_PS1.is_file(), f"{_GUARD_PS1} 不存在")
        code = _ps_code_only(self.guard_text)
        self.assertIn(
            "function Test-IsRealPython", code,
            "tools/lib/WindowsAppsGuard.ps1 未定義 Test-IsRealPython 共用函式",
        )
        self.assertRegex(
            code, _SEGMENT_SPLIT_RE,
            "共用函式內找不到 `-split '[\\\\/]+'` 分隔符正規化——R67 B3 修法本體"
            "（`/` 與 `\\` 同視為路徑分隔符）是否被改寫或移除？",
        )
        self.assertRegex(
            code, _SEGMENT_EQ_RE,
            "共用函式內找不到 `ToLowerInvariant() -eq 'windowsapps'` 逐段精確比對"
            "——退化成子字串比對會誤傷 `MyWindowsAppsBackup`（bash 側 R43 二審修過"
            "的同一個偽陽性）",
        )
        self.assertNotRegex(
            code, _INLINE_NOTLIKE_RE,
            "共用函式又出現分隔符敏感的 `-notlike '*\\WindowsApps\\*'`——R67 B3 迴歸"
            "（正斜線／混用分隔符的 WindowsApps 空殼會被判為真 Python）",
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

    def test_dev_start_ps1_delegates_candidate_selection_to_ssot(self) -> None:
        """🔴 R69 P2 改寫（鎖**遷移**，非放寬）：舊鎖要求 dev_start.ps1 內恰有一處
        `Test-IsRealPython -CandidateName 'python'`——那正是本輪修掉的缺陷形狀：
        「命中裸 python 即用、不看版本」。macOS 真機重現的姊妹缺陷（`python3` 恆
        為系統 3.9，`brew install python@3.11` 不改寫它 ⇒ dev_start 核心版本閘
        rc=2、ONBOARDING §2.1「全新機器可直接跑 dev_start」為假）迫使候選鏈上移
        到 SSOT `Get-PythonGeMin`（>= 3.11 才算數，內部逐個裸名候選仍呼叫
        `Test-IsRealPython`）。舊鎖若原地保留，等於要求 wrapper 永遠留著那個
        不看版本的分支。

        新鎖強度不減，且改守本輪真正要守的東西：
          ① wrapper 必須把候選挑選**委派**給 SSOT（恰一處 `Get-PythonGeMin`）；
          ② wrapper 內不得再出現任何自行判斷候選的 `Test-IsRealPython
             -CandidateName '<裸名>'`（回填該分支＝缺陷復發）。
        「SSOT 內部真的有做空殼排除」另由本檔 ②④ 節的行為表 parity 鎖看著。
        """
        selector_calls = re.findall(r"\bGet-PythonGeMin\b", _ps_code_only(self.dev_start_text))
        self.assertEqual(
            len(selector_calls), 1,
            f"tools/dev_start.ps1 應恰有一處呼叫 SSOT 候選鏈 Get-PythonGeMin"
            f"（tools/lib/WindowsAppsGuard.ps1），實際找到 {len(selector_calls)} 處",
        )
        inline_calls = re.findall(
            r"Test-IsRealPython\s+-CandidateName\s+'(python3?)'", self.dev_start_text
        )
        self.assertEqual(
            inline_calls, [],
            f"tools/dev_start.ps1 又出現自行判斷裸名候選的 Test-IsRealPython 呼叫："
            f"{inline_calls}——候選挑選（含 >= 3.11 版本下限）一律由 SSOT "
            f"Get-PythonGeMin 負責，wrapper 只做委派（R69 P2 迴歸鎖）",
        )

    def test_ssot_selector_applies_windowsapps_guard_to_bare_candidates(self) -> None:
        """R69 P2：候選鏈本體必須真的把裸名候選餵給 `Test-IsRealPython`——否則
        鎖遷移就變成把 guard 整條丟掉（`py` launcher 候選依檔頭記載刻意不套）。"""
        code = _ps_code_only(_GUARD_PS1.read_text(encoding="utf-8"))
        self.assertIn("function Get-PythonGeMin", code, "SSOT 未定義 Get-PythonGeMin")
        self.assertRegex(
            code, r"Test-IsRealPython\s+-CandidateName\s+\$exe",
            "Get-PythonGeMin 內找不到對裸名候選呼叫 Test-IsRealPython——"
            "候選鏈繞過空殼 guard 即 DEF-101-273/279/300/303 復發",
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
    WindowsApps 段排除邏輯本身（R67 B3 前為 `-notlike '*\\WindowsApps\\*'`，
    現為 `Test-HasWindowsAppsSegment` 逐段比對），不受各平台 `Get-Command`
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
        """路徑中的 WindowsApps 區段大小寫不同（系統本地化／大小寫不敏感檔案系統
        回傳的不同大小寫）仍須被排除。R67 B3 前這靠 `-notlike` 天生不分大小寫，
        現靠 `Test-HasWindowsAppsSegment` 的 `ToLowerInvariant()`——本測試防的是
        「改寫比對方式時把大小寫不敏感這條性質弄丟」（如 `-ceq`／`-cnotlike`）。"""
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
    """LATEST 版根目錄（sdd_version.py SSOT；解析失敗即 AssertionError）。委派
    tools/lib/sdd_latest.py 單一真相源（ADR-XPLAT-002 Phase 2-C，R66 收斂）。"""
    return sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")


def _tracked_files(pattern: str) -> list[str]:
    """git tracked 且符合 glob pattern 的 repo-relative 路徑清單（fail-loud）。

    用 `git ls-files` 而非 `Path.rglob`：天然排除 `.git`／`.venv`／
    `__pycache__`／`node_modules`（只要未被 commit）。

    🔴 R85／訴求 2：取數本體改委派 `tools/lib/git_paths.py`（根 CLAUDE.md 鐵律三表
    逐字指定的唯一取數層）——「每個站點各自記得帶 quotepath 旗標」正是該 SSOT 立案時
    要消滅的形態。fail-loud 留在本層（該 SSOT 刻意不代呼叫端決定 rc≠0 怎麼處置）。
    """
    rels = git_paths.ls_files(_REPO_ROOT, "--", pattern)
    assert rels, f"git ls-files -- {pattern} 回空 ⇒ 掃描邊界不得靜默縮小"
    return rels


# R66 ADR-XPLAT-002 Phase 2-D 收斂（DEF-101-624）：`_FROZEN_SDD_VERSION_RE` 與
# 本函式本體改委派 tools/lib/sdd_latest.py 單一真相源（同批收斂另四份複本，見
# tools/tests/test_windows_forbidden_filename_parity.py 檔內 R59/R66 沿革註解）。


def _exclude_frozen_sdd_versions(paths: list[str], latest_name: str) -> list[str]:
    """排除 AISDLC_SDD 凍結版本（v0.01 ~ 除 LATEST 以外者）——凍結版依鐵律
    (CLAUDE.md「Copy-on-Evolve」慣例) 不應被新規則追殺歷史快照。"""
    return sdd_latest.exclude_frozen_sdd_versions(paths, latest_name)


_WINDOWSAPPS_LITERAL = "WindowsApps"
_SSOT_REL_PATH = "tools/lib/WindowsAppsGuard.ps1"

# Python 側 WindowsApps 空殼判斷式的站點偵測＝**雙錨聯集**（函式名 ∪ 小寫引號字面值），
# 兩錨皆帶 `re.I`。以下每一句都是「不准回頭改掉」的設計約束；逐輪沿革（R56 round 1~5 的
# A~O 變體注入矩陣、三位審查員各自實測的紅綠對照、以及被證偽後刪掉的那條錯誤理由的完整
# 經過）已搬進 `docs/06_quality/AutoSDD_Defect_Log.md` 的 R84「護欄層淨減法」列（本檔刻意
# 不寫死 DEF 編號：編號由帳本持有者在收輪時配，寫死會在配號漂移時變成懸空引用）——那些
# 表格記的是**當時**兩個候選錨各自的命中，而今天
# 真正在守的是 `TestStubAnchorDiscriminatingPower`（常駐、逐變體注入），不是那些表格。
#
#   · **聯集不是取代**：兩錨互補而非包含。實測過的四個象限都存在（同名改寫法／改名同
#     寫法／同名反向比較序／改名另寫法），把函式名錨換成運算式錨等於「一邊補洞一邊新開
#     洞」。第二錨刻意由「運算式形狀」降級為「不可能被改名的小寫引號字面值」——所有改寫
#     法的變體都必然帶 `"windowsapps"` 字面值。
#   · **`re.I` 不得拿掉**：姊妹語言 SSOT `tools/lib/WindowsAppsGuard.ps1:55` 逐字寫的是
#     `-notlike '*\WindowsApps\*'`（**大寫**），仿照它在 Python 側新寫一份判斷式的人最
#     自然就會打出大寫形態；旗標缺席時那一整組（含 camelCase 函式名）靜默逃逸。
#     名錨須寫成 `re.MULTILINE | re.I`，**勿覆蓋掉**原有的 MULTILINE。
#   · **引號界定必須保留**（精度取捨，2026-07-27 實測、round 5 在 re.I 下重驗仍成立）：
#     改掃**裸**字面值會多命中只是提及 `tools/lib/windowsapps_guard.sh` 檔名的三支守門
#     工具（check_script_parity.py／check_wrapper_thinness.py／check_gha_action_versions.py）
#     ＝5 支，再加 re.I 還會多命中 boot_helper.py＝6 支；「引號界定 ＋ re.I」穩定維持 2 支。
#     零偽陽性實測：候選集合（scoped prefix ∩ 非測試檔）378 支生產 `.py`，加旗標前後命中
#     集合**完全相同**（`pre_run_validator.py` ＋ `tools/bootstrap_core.py`），新增偽陽性 0。
#   · **不得回頭寫「大小寫敏感是刻意的」**（round 5 訂正、已被實測證偽的錯誤理由）：
#     `pre_run_validator.py` 的使用者訊息是 `f"WindowsApps App Execution Alias 空殼（…"`，
#     `WindowsApps` 後接**空白**，引號界定的 `["']windowsapps["']` 本來就不匹配（已實測，
#     並由下方 negative case 常駐鎖住）；且該檔早已登記在 `_APPROVED_SECOND_IMPLS`。
#
# 方法論邊界（如實揭露，勿留「已涵蓋全類別」錯覺）：**兩錨同時避開**者仍逃得掉，既知邊界
# 收斂為兩種，共同特徵是「字面值不以完整 token 形式出現在一對引號內，且函式名不含
# windows/apps 字樣」：把字面值嵌進更大字串（`"\\windowsapps\\" in p.lower()`）、
# 字串串接（`("windows"+"apps")`）。這是逐行正則相對於 AST 解析的結構性天花板，同
# `DEF-101-333` 的四方一致裁定（**不是** `DEF-101-433`——該則的前提已於 R56 由
# bug-injection 證偽，不宜作為判例），非本鎖可解。
# **R60 訂正**：本段原句寫「Python 側只有這一層，破了本鎖即零訊號」，該宣稱自本檔末段的
# `TestZeroGuardBarePythonSitesAreEnrolled`（B-01）起已失實——兩層互為補位：本鎖漏掉的
# 「改名 ＋ 字面值拆開」若仍以裸 `python` 名稱交給 OS 會被那一層抓到，反之那一層豁免的檔
# 哪天內嵌一份判斷式會被本鎖抓到。**仍不宣稱兩層合併後涵蓋全類別**：兩者同時避開者
# （例如 `os.environ["PY"]`）依舊逃得掉。
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
# 🔴 R69 P2：SSOT 的**入口函式**由一個變成兩個——`Get-PythonGeMin`（挑 >= 3.11
# 直譯器的候選鏈）同樣定義在 `tools/lib/WindowsAppsGuard.ps1`、內部**逐個裸名
# 候選**呼叫 `Test-IsRealPython`，故呼叫它與直接呼叫 `Test-IsRealPython` 對
# 「有沒有繞過空殼 guard」等價（強度不變，不是放寬：兩個名字都只存在於 SSOT
# 一份實作裡，自行內嵌判斷式的 .ps1 照樣被判 offender）。bash 側對稱調整見
# `test_windowsapps_guard_bash_parity.py::_SSOT_ENTRYPOINTS`。
_SSOT_ENTRYPOINT_CALL_RE = re.compile(
    r'\b(?:Test-IsRealPython\s+-CandidateName|Get-PythonGeMin)\b'
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


def _has_real_ssot_entrypoint_call(text: str) -> bool:
    """R69 P2：同 `_has_real_test_is_real_python_call`，但認得 SSOT 的**兩個**
    入口函式（見 `_SSOT_ENTRYPOINT_CALL_RE` 上方 WHY）。repo-wide 掃描改用本
    述詞；`_has_real_test_is_real_python_call` 保留給「必須逐字呼叫
    Test-IsRealPython」的既有專屬鎖（bootstrap.ps1 兩處候選）。"""
    for raw_line in text.splitlines():
        if _line_is_comment(raw_line):
            continue
        line = _strip_trailing_line_comment(raw_line)
        for m in _SSOT_ENTRYPOINT_CALL_RE.finditer(line):
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
    # R69 P2：guard 判斷可以是 `Test-IsRealPython`，也可以是同屬 SSOT 的候選鏈
    # 入口 `Get-PythonGeMin`（內部逐個裸名候選呼叫前者）。
    guard_lines = _real_match_line_indices(text, _SSOT_ENTRYPOINT_CALL_RE)
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
            if _has_real_dot_source_of_ssot(text) and _has_real_ssot_entrypoint_call(text):
                continue  # 正確經過 SSOT dot-source + 呼叫（兩個入口函式擇一，R69 P2）
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


# ═══════════════════════════════════════════════════════════════════════════
# Python 側「零 guard 裸 python 名稱」repo-wide 前瞻掃描（R60，B-01）
#
# WHY 這一層原本缺席：同一個 guard 家族在另兩種語言各有**兩條**前瞻掃描軸——
#   .sh ：`test_repo_wide_scan_finds_no_unmigrated_sh_scripts`（有裸 `command -v` 判斷
#         但沒接 SSOT）＋ `test_repo_wide_scan_finds_no_zero_guard_python_calls`
#         （整支檔案零可用性判斷、直接裸呼叫）
#   .ps1：`test_ps1_mentions_of_windowsapps_all_go_through_ssot`（有提及但沒走 SSOT）
#         ＋ `test_python_calls_in_ps1_all_go_through_ssot`（有呼叫但沒 guard）
# Python 側只有 `test_windows_apps_predicate_impls_are_all_registered` 一條，而它的兩個
# 錨（函式名 `def *windows*apps*` ∪ 引號界定 `"windowsapps"` 字面值）都長在「**判斷式
# 實作**」上。對於一支**從頭到尾不提 WindowsApps、只是把裸 `python` 名稱交給 OS 解析**
# 的新檔案，兩錨結構上完全看不到它——正是 `_has_zero_guard_python_call` 在 .sh 側處理的
# 那個形狀（R44 曾在該側掰出真實命中）。實測本檔既有 helper 對此形狀正反皆零訊號：
#   bare subprocess / which() 無 guard → `_matches_stub_anchor` 皆 False；
#   對照組（第二份 predicate 實作）→ True ⇒ 鎖沒壞，是掃描面缺這個形狀。
#
# 軸別澄清（R60 反駁者訂正 (1)，勿再混指）：本節補的是**呼叫端納管（enrollment）**，
# 不是 `CrossPlatform_Scan_Dimensions.md` §(2) 講的「三份實作之間的行為等價」。等價軸在
# Python 側**已有**機械鎖（同檔 `test_bootstrap_core_py_has_symmetric_stub_detector`
# ＋ `tools/tests/test_bootstrap_core.py` 五支行為測試，含「拔掉 guard 就會挑到空殼」的
# bug-injection）。把兩條軸說成同一條會導出錯誤的修法。
#
# 暴露面比另兩種語言**窄**（R60 反駁者訂正 (2)，本節不宣稱相反）：bootstrap 悖論的內容是
# 「guard 必須在 Python 可用之前就能運作」，故 Python 側這份本質上只在真直譯器已存在時才
# 跑（`sys.executable` 必然可用）。本節因此是**前瞻性**防護（動工時 repo 內 live 違規＝0，
# 由本輪獨立 AST 全掃確認），而不是「Python 側是最後也最容易被繞過的一環」。
#
# WHY 判準刻意寬鬆（字面值而非呼叫語法）：窄判準（只認 `which("python")`／subprocess
# argv[0] 字面值／`or "python3"` 兜底）對本 repo 自己的**正典形狀盲**——`tools/
# bootstrap_core.py` 是把候選名放進 list literal（`["python", "python3", …]`）再以
# `shutil.which(parts[0])` 解析，變數化之後窄判準看不到任何裸名。實測窄判準只命中 2 支、
# 且**不含** bootstrap_core.py 自己；再發明者最可能照抄的就是這個正典形狀。故比照 .sh 側
# `_invokes_python_bare`（刻意用寬鬆全字比對，理由同款：R44 目標形狀就含變數預設值間接
# 呼叫）改採字面值判準。過度觸發是 fail-loud（有人得看一眼並登記角色），漏報才是 fail-open。
#
# 相對 .sh/.ps1 的一個結構性優勢（可正面主張）：本節走 **AST**，註解與 docstring 由語法
# 結構天然排除，不需要 `_strip_bash_comment` 那類逐字元剝註解——而 R46 已證明那條路是無底洞
# （繞過從整行註釋 → no-op 前綴 → heredoc 逐層復發）。
#
# 邊界宣稱（三段式，見 CrossPlatform_Scan_Dimensions.md §「邊界宣稱必須實測」）：
#   【已實測涵蓋】① `subprocess.run(["python", "x.py"])`；② `shutil.which("python3")`；
#     ③ 正典多候選 list literal ＋ `which(變數)`（窄判準對此盲）；④ shell 字串形態
#     `subprocess.run("python -m foo", shell=True)`；⑤ `sys.executable or "python3"` 兜底；
#     ⑥ 帶 guard 的檔案（`_matches_stub_anchor`）不重複計入本軸；⑦ 掃描面塌陷為 0 份 →
#     等值斷言翻紅；⑧ 無法 parse 的候選 `.py` → AssertionError（不靜默略過）。
#   【已實測不涵蓋】① 註解／docstring 內的提及（AST 結構性排除，**刻意**如此，見上）；
#     ② 測試檔（`_is_test_py`，同姊妹掃描判準）；③ 凍結版 v0.01~v0.29（Copy-on-Evolve）；
#     ④ 尚未 `git add` 的新檔（`git ls-files` 固有性質）；⑤ 字面值被拆開或間接組出
#     （`"pyth" + "on"`、f-string、`os.environ["PY"]`）——與 `_matches_stub_anchor` 的
#     K／O 既知邊界同源，屬靜態掃描天花板；⑥ 首 token 非裸名者（`"py -3.11"`／
#     `"python3.11"`／`"python:3.11-slim"`）——前者是 Windows py launcher（不經 PATH 撞
#     WindowsApps，`bootstrap_core.py:141` 註解已論證），後兩者是版本化名稱/docker tag。
#   【未窮舉】本清單只是本輪真正跑過的項目，不主張已列出全部繞過路徑。
# ═══════════════════════════════════════════════════════════════════════════
# 首個空白分隔 token 恰為裸 `python`／`python3`（`$` 錨定尾端或空白）——即「會被交給 OS／
# shell 當指令首 token 的裸直譯器名稱」。`python3.11`／`python:3.11-slim`／`py -3.11`
# 皆不匹配（後接 `.`／`:`／不同字首）。
_BARE_PY_COMMAND_RE = re.compile(r"^python3?(?:\s|$)")


def _docstring_constant_ids(tree: ast.AST) -> set[int]:
    """module／class／def 的 docstring 常數節點 id 集合——供掃描時排除。

    docstring 在 AST 裡與一般字串常數同型（`ast.Constant`），不排除的話本家族每一支
    帶說明文字的檔案都會命中（本檔自己的 docstring 就提了好幾次 `python`）。
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            ids.add(id(body[0].value))
    return ids


def _bare_python_command_literals(text: str, rel: str = "<memory>") -> list[str]:
    """回傳「首 token 為裸 python/python3 的字串常數」站點描述（`L<行號>:<值>`）。

    parse 失敗一律 fail-loud（AssertionError），不得靜默回空——掃描邊界不得靜默縮小
    （同 `_tracked_files()`／`_latest_sdd_root()` 判準）。
    """
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:  # pragma: no cover - repo 內生產 .py 應恆可 parse
        raise AssertionError(
            f"{rel} 無法以 ast.parse 解析（{exc}）——掃描邊界不得靜默縮小；"
            "若確為刻意的語法示例檔，請登記豁免而非讓掃描沉默"
        ) from exc
    skip = _docstring_constant_ids(tree)
    hits = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in skip
            and _BARE_PY_COMMAND_RE.match(node.value)
        ):
            hits.append(f"L{node.lineno}:{node.value!r}")
    return hits


def _has_zero_guard_bare_python(text: str, rel: str = "<memory>") -> bool:
    """檔案含裸 python 指令首 token 字面值、且**自身不帶**任何 WindowsApps 可用性判斷。

    帶 guard 者（`_matches_stub_anchor`）由 `test_windows_apps_predicate_impls_are_all_
    registered` 那條「等價／實作站點」軸負責，本軸不重複計——兩條軸各自維護註冊表，
    同一支檔案不會同時出現在兩邊，避免登記漂移時互相掩護。
    """
    if not _bare_python_command_literals(text, rel):
        return False
    return not _matches_stub_anchor(text)


# 註冊表：鍵＝repo 相對路徑（LATEST 版前綴正規化為 `<LATEST>`），值＝**角色**註記。
# 登記時必須當場分診「是真的把裸名交給 OS，還是只是資料/樣式/訊息字串」——比照
# `_KNOWN_NTFS_ANCHOR_SITES`（tools/tests/test_windows_forbidden_filename_parity.py）
# 與 `_EXEMPT_PS1_FILES`／bash 側 `_EXEMPT_SH_FILES` 的附理由登記慣例。
_ZERO_GUARD_BARE_PY_SITES = {
    # ── 真的以裸名兜底（暴露面存在，但結構性極窄）────────────────────────────
    "AutoClaude/autoclaude/evolution/_evaluator_derivation.py": (
        "真兜底：`_QUOTED_PY = '\"%s\"' % (sys.executable or \"python3\")`——僅在 "
        "sys.executable 為空（嵌入式/凍結直譯器）時才落到裸名。AutoClaude 的入口是 "
        "`python -m autoclaude`／console script，該情境下 sys.executable 恆為 venv 內"
        "絕對路徑（本輪實測本機 .venv 與 AutoClaude/.venv 皆非空）；且該行是**模組載入期**"
        "求值，若真為空則整個套件早已無法運作。不改生產碼，改在此登記並保留訊號。"
    ),
    "AutoClaude/autoclaude/execution/mutation_applier/_simple_mutations.py": (
        "真兜底：`python_bin = sys.executable or \"python3\"`，理由同上一筆。該函式的 "
        "docstring 自陳「W6 已拔除、目前無非測試呼叫點，暫不可觸發」，暴露面更窄。"
    ),
    # ── 非呼叫：資料/樣式/訊息字串（粗粒度字面值判準的可見成本）────────────────
    "AISDLC_SDD/<LATEST>/tools/fsm_runtime/sandbox_runner.py": (
        "非呼叫：docker image tag 白名單元素（`\"busybox\", \"alpine\", \"python\", "
        "\"python:3.11-slim\"…`）——交給 `docker run` 當 image 名，不經 PATH 解析"
    ),
    "AutoClaude/autoclaude/models/escalation.py": (
        "非呼叫：ESCALATION 報告內給人看的建議修復指令字串（`python -m py_compile …`），"
        "本行程不 spawn 它"
    ),
    "AutoClaude/autoclaude/tools/sdd_compile.py": (
        "非呼叫：`argparse.ArgumentParser(prog=\"python -m autoclaude.tools.sdd_compile\")`"
        "——只用於 usage/help 輸出"
    ),
    "AutoClaude/tools/three_tier_to_playbook.py": (
        "非呼叫：`_EVAL_ALLOWED_HEAD`／`_PY_HEADS` 是 evaluator 指令**首 token 白名單**"
        "（驗證用途，本檔不 spawn）。註：被放行的 evaluator 字串日後由 ShellEvaluator "
        "以 shell 執行，那條路的 guard 屬 evaluator/載具領域，不在本軸"
    ),
    "tools/check_wrapper_thinness.py": (
        "非呼叫：薄殼守門工具的**禁用子字串樣式**字面值（`\"python -c\"`／"
        "`\"python3 -c\"`，用來偵測厚殼），是比對資料而非指令"
    ),
    "tools/run_root_unittests.py": (
        "非呼叫：`install_hint()` 組給**人**複製貼上的安裝指令字串"
        "（`\"python -m pip install \" + …`）——本行程只 print 它、不 spawn。"
        "R68 新增：缺第三方相依時 runner fail-fast 並印出這行修法"
    ),
    "tools/probe/console_spawn_watch.py": (
        "非呼叫：`str(record.get(\"ParentName\") or \"\").lower().startswith(\"python\")` "
        "的**比對字面**。那個字串是 WMI 從 OS **讀回來**的行程映像名，判準只拿它分類"
        "（`cmd.exe` 的父行程是不是 Python ⇒ `shell=True` 的形狀），一次都不交給 "
        "subprocess／shell／`shutil.which` 去解析 ⇒ 沒有 PATH 撞 WindowsApps 的暴露面。"
        "與同表 `tools/check_wrapper_thinness.py`（禁用子字串樣式字面值）、"
        "`tools/lib/script_interface_parity.py`（外部執行檔白名單資料）同型：都是**資料**"
        "而非指令。同檔 L71 的 `\"python.exe\"` 不匹配 `_BARE_PY_COMMAND_RE`（後接 `.`）。"
        "🔴 立此筆的成因與上一筆 `tools/probe/xplat_injection_matrix.py`、"
        "`tools/lib/script_interface_parity.py` **逐字同型，至此第四次**："
        "該檔是 R82 新增、`git add` 的那一刻才進入本鎖射程（掃描面只看 git-tracked）。"
        "前三次都只把個案登記掉，沒有人動「收尾在 tracked 狀態改變前跑」這個順序，"
        "所以它必然再來——這一次至少是在 commit **之前**被抓到的。"
    ),
    "tools/probe/xplat_injection_matrix.py": (
        "非呼叫：`Gate.describe` 欄位的**人可讀說明字串**"
        "（`\"python tools/run_root_unittests.py（根層護欄層全套）\"`），"
        "只用於報表印出「這一格量的是哪道閘門」，本行程不 spawn 它——"
        "真正跑閘門走的是 `sys.executable`。與同表 `tools/run_root_unittests.py` 同型。"
        "🔴 R79 立此筆的成因本身值得記：該檔在 commit 前是 untracked，"
        "本鎖的掃描面只看 git-tracked ⇒ 它在 commit 的那一刻才首次進入射程並當場轉紅。"
        "「commit 改變 tracked 狀態使掃描面漂移」在本 repo 已是第二次（R78 收輪同型）"
    ),
    "tools/lib/platform_utils.py": (
        "非呼叫：`venv_dir / \"bin\" / \"python\"` 的**路徑片段**（組出 venv 內絕對路徑），"
        "不經 PATH 解析。粗粒度判準看不出「字面值當路徑片段」與「當指令首 token」的差別，"
        "此筆即該取捨的成本"
    ),
    "tools/lib/script_interface_parity.py": (
        "非呼叫：`_EXTERNAL_BINS` 是「兩平台同名外部執行檔」的**比對用白名單資料**"
        "（`\"python\", \"python3\"` 與 act／docker／ruff 等並列），供 .sh／.ps1 介面等價"
        "判準辨識指令首 token 用；本檔一次都不 spawn 它們。與同表 "
        "`tools/check_wrapper_thinness.py`（禁用子字串樣式字面值）同型。"
        "🔴 立此筆的成因與 `tools/probe/xplat_injection_matrix.py` 那筆**逐字同型**："
        "該檔 commit 前是 untracked、本鎖掃描面只看 git-tracked ⇒ 它在 commit 的那一刻"
        "才首次進入射程並當場轉紅（收尾跑的是 commit 前的樹，所以當時是綠的）。"
        "「commit 改變 tracked 狀態使掃描面漂移」至此已是**第三次**（R78 收輪、R79 那筆、"
        "本筆）——前兩次都只把個案登記掉，沒有人去改「收尾在 commit 前跑」這個順序，"
        "所以它必然再來一次。"
    ),
    "tools/sync_onboarding_baselines.py": (
        "非呼叫：`argparse.ArgumentParser(prog=\"python tools/sync_onboarding_baselines.py\")`"
        "——只用於 usage/help 輸出，與上面 `AutoClaude/autoclaude/tools/sdd_compile.py` 同型。"
        "R67 該檔 argparse 化（R67-D20：原本 `\"--flag\" in argv` 手搓解析，未知旗標靜默 "
        "rc=0）時新增，非新暴露面"
    ),
}


def _normalize_latest_rel(rel: str, latest_name: str) -> str:
    """LATEST 版目錄名換成 `<LATEST>` 佔位——否則與本鎖無關的 Copy-on-Evolve 升版
    （建 v0.31）也會讓註冊表翻紅。手法同 `test_windows_forbidden_filename_parity.py::
    _normalize_latest`（tools/tests 無 `__init__.py`，跨檔 import 需 sys.path 手術，
    沿用本目錄「共用資料規格才抽檔、執行邏輯各自獨立」的既有慣例）。"""
    return rel.replace(f"AISDLC_SDD/{latest_name}/", "AISDLC_SDD/<LATEST>/", 1)


class TestZeroGuardBarePythonSitesAreEnrolled(unittest.TestCase):
    """repo-wide：含裸 python 指令首 token 字面值、且自身無 guard 的生產 `.py` 必須
    與註冊表**等值**。

    WHY 等值而非下限（沿用姊妹鎖判例）：等值一次拿到兩個方向——多一份＝出現未經分診的
    新站點；少一份＝登記腐化或某支檔案的字面值被改寫（例如兜底被改掉了卻沒人更新註記）。
    等值另外免費得到 fail-open 防護：pathspec／排除清單被改壞而掃到 0 份時，`hits=[]`
    ≠ 註冊表必然翻紅，故刻意**不**另設下限。
    """

    def test_zero_guard_bare_python_sites_match_registry_exactly(self) -> None:
        latest_name = _latest_sdd_root().name
        all_py = _exclude_frozen_sdd_versions(_tracked_files("*.py"), latest_name)
        candidates = [rel for rel in all_py if not _is_test_py(rel)]
        self.assertGreater(
            len(candidates), 0,
            "候選 `.py` 為 0——掃描面塌陷（pathspec 或排除清單被改壞）",
        )

        hits = {}
        for rel in candidates:
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if _has_zero_guard_bare_python(text, rel):
                hits[_normalize_latest_rel(rel, latest_name)] = _bare_python_command_literals(
                    text, rel
                )

        self.assertEqual(
            sorted(hits), sorted(_ZERO_GUARD_BARE_PY_SITES),
            f"零 guard 裸 python 名稱的站點集合與註冊表不符（本次實掃候選 "
            f"{len(candidates)} 份）。實掃命中明細：{hits}\n"
            "  · **多出**檔案 → 出現新的裸 python 名稱站點：先分診它是「真的把裸名交給 "
            "OS 解析」還是「只是資料/樣式/訊息字串」。前者請改走 guard（Python 側 SSOT ＝ "
            "`tools/bootstrap_core.py::_is_windows_apps_stub`，或已核准的 "
            "`_APPROVED_SECOND_IMPLS`），後者連同**角色註記**登記進 "
            "`_ZERO_GUARD_BARE_PY_SITES`。\n"
            "  · **少掉**檔案 → 該站點的字面值消失或該檔已帶 guard：確認是刻意收斂"
            "（而非重構時被順手改成間接組字串而逃出掃描面），確認後同步下修註冊表。",
        )


class TestZeroGuardBarePythonDetectorDiscriminatingPower(unittest.TestCase):
    """對**自建假內容**驗證 helper 正反皆判對（不改任何生產碼）。

    WHY 常駐而非一次性 bug-injection：R56 round 6 的判例——`_matches_stub_anchor` 的
    「∪」語意當時是核心交付物卻完全無鎖，把 `or` 改成 `and`（3 個字元）全檔測試照樣全綠。
    判準函式的鑑別力必須自己有鎖，不能靠下一輪再做一次注入才發現被改弱。
    """

    _GUARD_SRC = (
        'def _is_windows_apps_stub(p):\n'
        '    return any(part.lower() == "windowsapps" for part in p.split("/"))\n'
    )

    def test_subprocess_bare_argv0_is_flagged(self) -> None:
        text = 'import subprocess\nsubprocess.run(["python", "x.py"], check=True)\n'
        self.assertTrue(_has_zero_guard_bare_python(text))

    def test_shutil_which_bare_name_is_flagged(self) -> None:
        text = 'import shutil\nexe = shutil.which("python3")\n'
        self.assertTrue(_has_zero_guard_bare_python(text))

    def test_canonical_list_literal_with_variable_which_is_flagged(self) -> None:
        """本 repo 正典形狀（`bootstrap_core.py` 的寫法）——窄判準對此盲，是本節
        刻意採寬鬆字面值判準的理由，故必須有一支斷言釘住它會被抓到。"""
        text = (
            'import shutil\n'
            'candidates = ["python", "python3"]\n'
            'for cand in candidates:\n'
            '    resolved = shutil.which(cand)\n'
        )
        self.assertTrue(_has_zero_guard_bare_python(text))

    def test_shell_string_command_is_flagged(self) -> None:
        text = 'import subprocess\nsubprocess.run("python -m foo", shell=True)\n'
        self.assertTrue(_has_zero_guard_bare_python(text))

    def test_sys_executable_or_bare_fallback_is_flagged(self) -> None:
        text = 'import sys\npy = sys.executable or "python3"\n'
        self.assertTrue(_has_zero_guard_bare_python(text))

    def test_file_carrying_a_guard_is_not_flagged_by_this_axis(self) -> None:
        """帶 guard 者歸「實作站點」那條軸，本軸不重複計（否則兩張註冊表互相掩護）。"""
        text = 'import shutil\n' + self._GUARD_SRC + 'exe = shutil.which("python")\n'
        self.assertTrue(_matches_stub_anchor(text), "前置條件：本樣本應被視為帶 guard")
        self.assertFalse(_has_zero_guard_bare_python(text))

    def test_comment_only_mention_is_not_flagged(self) -> None:
        text = '# 這裡以前是 python foo.py，現已改走 sys.executable\nimport sys\n'
        self.assertFalse(_has_zero_guard_bare_python(text))

    def test_docstring_only_mention_is_not_flagged(self) -> None:
        text = '"""用法：python -m tool ..."""\n\n\ndef f():\n    """python3 也可以。"""\n'
        self.assertFalse(_has_zero_guard_bare_python(text))

    def test_versioned_and_docker_tag_names_are_not_flagged(self) -> None:
        """首 token 非裸名者不算：py launcher 不經 PATH、版本化名稱與 docker tag 亦然。"""
        for value in ("py -3.11", "python3.11", "python:3.11-slim", "python.exe", "pythonic"):
            with self.subTest(value=value):
                self.assertFalse(
                    _has_zero_guard_bare_python(f'x = {value!r}\n'),
                    f"{value!r} 不應被判為裸直譯器名稱",
                )

    def test_absence_of_any_python_literal_is_not_flagged(self) -> None:
        self.assertFalse(_has_zero_guard_bare_python('import sys\nprint(sys.executable)\n'))

    def test_unparseable_file_fails_loud(self) -> None:
        with self.assertRaises(AssertionError):
            _bare_python_command_literals("def (:\n", "fake.py")


# ---------------------------------------------------------------------------
# ④ 四份實作的**行為表 parity**（R67 B3）
#
# WHY 這一節必須存在（不是「再加一層保險」，是既有鎖的結構性盲區）：
# `real_python_candidate` 家族有四份獨立實作（ADR-XPLAT-002 §3.2 明列，bootstrap
# 悖論定案不收斂）——
#
#   ① `tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython`（PowerShell）
#   ② `tools/lib/windowsapps_guard.sh::is_real_python_candidate`（bash）
#   ③ `tools/bootstrap_core.py::_is_windows_apps_stub`（Python，根層）
#   ④ `AutoClaude/autoclaude/execution/pre_run_validator.py::
#      _is_windows_apps_alias_stub`（Python，子專案；刻意不 import 根層 tools/*.py）
#
# R67 之前，四份之間**沒有任何一支測試餵同一組輸入、比對四方裁決**：本檔上面的
# ② 節驗 ① 自身行為（但 4 個樣本全是反斜線）、`test_windowsapps_guard_bash_parity.py`
# 驗 ②、`test_bootstrap_core.py` 驗 ③。三處各自全綠，卻對「四份對同一條路徑給相反
# 答案」完全零訊號——R67 B3 實測就落在這個縫裡：
#
#     輸入 `C:/Users/me/AppData/Local/Microsoft/WindowsApps\python.exe`
#       ①（PS）判「真 Python」  ／  ②③④ 判「Store 空殼」
#
# ——1 對 3 相反裁決，且**可觸達**：`(Get-Command python).Source` 是「PATH 條目 +
# 檔名」拼出來的，PATH 條目以正斜線書寫時 Source 就帶正斜線（同一機制在姊妹
# capability 已有真 Windows 實測，見 `tools/lib/Find-GitBash.ps1` 檔頭 R60 P10-2
# 段）。姊妹缺陷（System32／`Find-GitBash.ps1`）R60 P10-2 修好時**一併補了同款行為表
# parity 鎖**（`test_find_git_bash_parity.py::TestSystem32VerdictParity`），WindowsApps
# 這半漏修 7 輪（R60→R66）——**因為那半有行為表鎖、這半沒有**。
#
# ADR-XPLAT-002 §3.2 明令：「強制機制改為行為表 parity（餵同一組輸入給各語言實作、
# 比對裁決），取代現行的字面 parity……字面比對型 parity 鎖自本 ADR 起不計為機械
# 釘選」。本節即該裁決在 `real_python_candidate` 家族的落地。
#
# 手法（與姊妹鎖同款）：**真的起 PowerShell／bash 去執行生產實作**，不比對原始碼
# 字面；四份吃同一張 `_VERDICT_CASES`（同一個暫存樣本檔同時餵 PS 與 bash，連「兩邊
# 樣本抄歪了」都沒有空間）。
#
# 落點說明：本節原本寫成獨立檔 `tools/tests/test_windowsapps_verdict_parity.py`，
# 被 `test_adr_xplat001_c1c2_lock.py` 的護欄層檔數棘輪擋下（DEF-101-561③：R61 起
# `tools/tests/` 只准合併／刪除，新判準一律**擴充進既有鎖檔**），故併入本檔——本檔
# 正是 WindowsApps guard 家族的傘狀鎖，且 ② 節那張 4 列全反斜線的行為電池正是 B3
# 得以潛伏 7 輪的缺口所在。
# ---------------------------------------------------------------------------
sys.path.insert(0, str(_REPO_ROOT / "tools"))
import bootstrap_core  # noqa: E402

_AUTOCLAUDE_DIR = _REPO_ROOT / "AutoClaude"
if str(_AUTOCLAUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_AUTOCLAUDE_DIR))
# 第 4 份實作住在子專案裡且刻意不 import 根層 tools/*.py（見該檔的套件邊界論證）。
# 直接 import 該函式物件比對其行為，是本 repo 既有慣例——
# `tools/tests/test_windows_forbidden_filename_parity.py` 對
# `autoclaude.utils.logger._sanitize_log_filename` 走的就是同一條路。
from autoclaude.execution.pre_run_validator import (  # noqa: E402
    _is_windows_apps_alias_stub as _autoclaude_is_stub,
)

# 共用樣本表 — 四份實作吃同一張表。`expected_stub=True` 代表「該排除（Store 空殼）」。
#
# 判準（四份實作共同的**意圖**，非某一份的現行行為）：路徑中存在名為 `windowsapps`
# 的**完整路徑段**即為 Store 空殼；`/` 與 `\` 皆為路徑分隔符；比對不分大小寫。
# 三條性質各自都有專屬樣本列，任一份實作單邊弱化任一條性質都會在此翻紅。
_VERDICT_CASES: tuple[tuple[str, bool, str], ...] = (
    # 反斜線基準列：R67 修復前唯一被 PS 側 `-notlike` 抓到的形狀（控制組——
    # 若連這列都翻，代表是驅動器壞了而不是分隔符缺陷）。
    (
        r"C:\Users\me\AppData\Local\Microsoft\WindowsApps\python.exe",  # platform-ok: 純字面值餵給四份實作，非 Path join
        True, "全反斜線（修復前唯一命中）",
    ),
    # 病灶本體①：PATH 條目整條以正斜線書寫。
    (
        r"C:/Users/me/AppData/Local/Microsoft/WindowsApps/python.exe",  # platform-ok: 同上
        True, "全正斜線",
    ),
    # 病灶本體②：`(Get-Command python).Source` 的實測形狀——PATH 條目正斜線，
    # PowerShell 補上的分隔符是反斜線（Find-GitBash.ps1 檔頭 R60 P10-2 段的
    # 真 Windows 實測即此形狀，只是那次的目標段是 System32）。
    (
        r"C:/Users/me/AppData/Local/Microsoft/WindowsApps\python.exe",  # platform-ok: 同上
        True, "混用分隔符（Get-Command Source 實測形狀）",
    ),
    # 病灶本體③④：分隔符混用出現在 WindowsApps 段的前／後。
    (
        r"C:\Users\me\AppData\Local\Microsoft/WindowsApps\python.exe",  # platform-ok: 同上
        True, "混用分隔符（前緣正斜線）",
    ),
    (
        r"C:\Users\me\AppData\Local\Microsoft\WindowsApps/python.exe",  # platform-ok: 同上
        True, "混用分隔符（後緣正斜線）",
    ),
    # 病灶本體⑤：Git Bash（MSYS）風格掛載路徑——`command -v python` 在 Git Bash
    # 上回的就是這個形狀，是 bash 側呼叫端的真實輸入。
    (
        "/c/Users/me/AppData/Local/Microsoft/WindowsApps/python",
        True, "Git Bash MSYS 掛載路徑",
    ),
    # 大小寫：四份都必須不分大小寫（bash 側 R43 二審修過大小寫敏感缺陷；PS 側
    # R67 前靠 `-notlike` 天生不分大小寫，改逐段比對後靠 `ToLowerInvariant()`）。
    (
        r"C:\Users\me\AppData\Local\Microsoft\WINDOWSAPPS\python.exe",  # platform-ok: 同上
        True, "大小寫變體",
    ),
    # UNC 路徑：分隔符正規化不得把 `\\server\share` 的前導雙反斜線吃掉判準。
    (
        r"\\wsl$\Ubuntu\home\me\WindowsApps\python",  # platform-ok: 同上
        True, "UNC 路徑",
    ),
    # 誘餌（偽陽性防線）：含 WindowsApps 子字串但**不是**完整路徑段。bash 側 R43
    # 二審修的就是這個偽陽性；PS 側 R67 改逐段比對時必須一併守住，不得退化成
    # `-like '*windowsapps*'` 這種「順手把大小寫與分隔符一起解決」的寫法。
    (
        r"C:\Users\me\MyWindowsAppsBackup\python.exe",  # platform-ok: 同上
        False, "誘餌：子字串非完整段",
    ),
    # 陰性對照：真直譯器安裝路徑。
    (
        r"C:\Python311\python.exe",  # platform-ok: 同上
        False, "真直譯器路徑",
    ),
    # 判準邊界（如實記載為「已知殘餘盲區」，非「已驗證安全」）：Windows 檔案系統
    # 會忽略目錄名的尾隨點，故 `WindowsApps.` 實際指向同一個目錄，但四份實作
    # **一致**不排除它。本列鎖住「四方一致」這件事——哪天要收掉這個盲區，四份必須
    # 一起改，不會有人靜默單邊處理（同 test_find_git_bash_parity.py 的 Sysnative
    # 盲區那列的用意）。
    (
        r"C:\Users\me\AppData\Local\Microsoft\WindowsApps.\python.exe",  # platform-ok: 同上
        False, "尾隨點盲區（四方一致不排除）",
    ),
)


def _case_inputs() -> tuple[str, ...]:
    return tuple(case for case, _exp, _why in _VERDICT_CASES)


def _write_verdict_samples(td: str) -> Path:
    """把樣本表寫成一個 ASCII 檔案，PS 與 bash 兩側**讀同一個檔**。

    刻意不用命令列參數傳樣本：反斜線／`$`／UNC 前導 `\\\\` 在兩種 shell 的引號語意
    下各有轉義陷阱，一旦轉義歪掉，測試會因為「餵進去的字串已經不是表上那個」而
    假綠。走檔案則兩側都是逐行原文讀取，沒有轉義層。

    🔴 一律走 bytes 層寫入、行尾**硬編碼 LF**（R68 windows-compat-ci 首度在真 Windows
    執行 `tools/tests/` 時炸出的病灶，3 筆紅）：原本的 `write_text(..., encoding="ascii")`
    其 `newline` 預設為 `None` ＝「翻成平台行尾」，在 Windows 上寫出的是 **CRLF**。
    bash 側驅動器 `while IFS= read -r line` 只以 LF 斷行，`$line` 於是尾帶一個 `\\r`，
    那個 CR 跟著被 `printf` 印進判定行——**送進生產函式的字串已經不是表上那個**，正是
    本 docstring 上一段要防的假綠，只是改由行尾而非轉義層造成。PS 側走 `Get-Content`
    會吃掉行終止符故免疫，這也是 CI 上只有 bash 那三筆紅、PS 三筆全綠的原因。
    同型先例：`test_doc_loc_baseline_freshness_r60.py::_fingerprint_of` 的
    「🔴 bytes 層：write_text 會在 Windows 自行加 CR」。
    """
    path = Path(td) / "verdict_cases.txt"
    path.write_bytes(("\n".join(_case_inputs()) + "\n").encode("ascii"))
    return path


def _run_verdict_driver(argv: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """跑判定驅動器，取回**換行未被改寫**的 stdout／stderr。

    🔴 刻意不傳 `text=True`（R68）：那會把管線包進 universal-newlines 的
    `TextIOWrapper`，把孤立的 `\\r` **就地翻成 `\\n`**。CR 汙染於是偽裝成一個憑空多出來
    的換行，解析層看到的是兩截殘行（`V|<輸入>` 與 `|STUB`，兩者都不是 3 欄故雙雙被
    跳過）而非一行帶 CR 的完整記錄，只能報「樣本被吃掉」，指不出真兇。
    windows-compat-ci 上的實際形狀正是如此：11 筆樣本全數「不見」，而失敗訊息裡的
    stdout repr 只看得到 `V|…python.exe\\n|STUB`——**CR 早在解析前就被 Python 抹掉了，
    所以在解析層 strip `\\r` 根本救不回來**。改取 bytes 自行解碼，CR 才留得到
    `_parse_verdicts` 裡被具名指認。
    """
    proc = subprocess.run(argv, capture_output=True, timeout=timeout)
    return subprocess.CompletedProcess(
        proc.args,
        proc.returncode,
        proc.stdout.decode("utf-8", errors="replace"),
        proc.stderr.decode("utf-8", errors="replace"),
    )


def _parse_verdicts(stdout: str, expected_inputs: tuple[str, ...]) -> dict[str, bool]:
    """解析 `V|<輸入>|STUB|REAL` 行；輸入集合必須與送進去的完全相同。

    行終止符一律自行處理（呼叫端走 `_run_verdict_driver`，stdout 未經 universal
    newlines 改寫）：只以 LF 斷行；行**尾**的 CR 視為 CRLF 的另一半而剝除——PowerShell
    的 `Write-Output` 在 Windows 上輸出的就是 CRLF，那是合法行終止符。CR 出現在行的
    **中間**則代表欄位內容被行尾汙染，就地 fail loud 並指名 CR：既不得默默剝掉當沒事
    （判定不是對表上那個字串做的，剝掉即假綠），也不得放它流到下方的集合比對（那會
    誤報成「驅動器把樣本吃掉了」，把查案方向指往錯的地方——R68 就是這樣被誤導的）。
    """
    out: dict[str, bool] = {}
    for raw_line in stdout.split("\n"):
        line = raw_line[:-1] if raw_line.endswith("\r") else raw_line
        if "\r" in line:
            raise AssertionError(
                f"判定行的欄位內含 CR（{line!r}）——樣本在送進生產函式的路上被行尾"
                "汙染（典型成因：樣本檔被寫成 CRLF，而 bash `read -r` 只斷 LF、"
                "把 CR 留在 $line 裡），此時的判定不是對樣本表上那個字串做的，"
                f"「全數同判」同樣是假綠。stdout={stdout!r}"
            )
        parts = line.split("|")
        if len(parts) != 3 or parts[0] != "V":
            continue
        out[parts[1]] = parts[2].strip() == "STUB"
    if set(out) != set(expected_inputs):
        missing = sorted(set(expected_inputs) - set(out))
        raise AssertionError(
            f"回報的輸入集合與送進去的不符（缺 {missing}）——驅動器把某些樣本吃掉了，"
            f"這種情況下的「全數同判」是假綠。stdout={stdout!r}"
        )
    return out


# `Test-IsRealPython` 回 $true ＝「真 Python」＝ 非空殼，故此處反相為 STUB/REAL。
# shadow `Get-Command` 手法同本檔 ② 節（見該節 class docstring）。
_PS_VERDICT_DRIVER = """\
$ErrorActionPreference = 'Stop'
$script:FakeSource = ''
function Get-Command {{
  param(
    [Parameter(Position=0)][string]$Name,
    [Parameter(ValueFromRemainingArguments=$true)] $Rest
  )
  return [PSCustomObject]@{{ Source = $script:FakeSource }}
}}
. '{guard}'
foreach ($line in (Get-Content -LiteralPath '{samples}')) {{
  if ([string]::IsNullOrEmpty($line)) {{ continue }}
  $script:FakeSource = $line
  if (Test-IsRealPython -CandidateName 'python') {{
    Write-Output ('V|' + $line + '|REAL')
  }} else {{
    Write-Output ('V|' + $line + '|STUB')
  }}
}}
"""

# shadow `command` builtin：bash 側的對稱手法。`is_real_python_candidate` 內部唯一
# 的外部依賴就是 `command -v "$name"`，覆寫它即可把任意 resolved path 餵進生產函式。
#
# 🔴 路徑刻意用**位置參數**（`bash -c <script> bash <guard> <samples>`）注入，不像
# `_PS_VERDICT_DRIVER` 那樣走 `str.format`：bash 函式定義本身帶 `{ }`，用 `.format`
# 就得把每個大括號寫成 `{{`／`}}`，漏一個即 `KeyError`（R67 本節初稿正是這樣寫、
# 且沒跑過就交出去，三支 bash／四方測試全爆）。位置參數沒有這層轉義，也順帶免掉
# 「路徑含空白／引號」的注入面。
_BASH_VERDICT_DRIVER = r"""
. "$1"
while IFS= read -r line; do
  [ -z "$line" ] && continue
  command() { printf '%s\n' "$line"; }
  if is_real_python_candidate python; then
    printf 'V|%s|REAL\n' "$line"
  else
    printf 'V|%s|STUB\n' "$line"
  fi
done < "$2"
"""


class TestVerdictSourcesExist(unittest.TestCase):
    """四份實作的載體不得腐化（檔案消失／函式改名須 fail-loud，不得靜默少驗一份）。"""

    def test_all_four_implementations_are_present(self) -> None:
        self.assertTrue(_GUARD_PS1.is_file(), f"{_GUARD_PS1} 不存在")
        self.assertTrue(_GUARD_SH.is_file(), f"{_GUARD_SH} 不存在")
        self.assertTrue(callable(bootstrap_core._is_windows_apps_stub))
        self.assertTrue(callable(_autoclaude_is_stub))

    def test_case_table_is_ascii_and_delimiter_safe(self) -> None:
        """樣本必須是 ASCII 且不含 `|`——否則檔案往返／輸出解析會靜默吃掉樣本。"""
        for case, _exp, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                case.encode("ascii")  # 非 ASCII 直接拋 UnicodeEncodeError
                self.assertNotIn("|", case, "樣本不得含 `|`（驅動器輸出的欄位分隔符）")
                self.assertNotIn("\n", case)
                # R68：CR 同樣是行終止符的一半。樣本表本身不得含 CR，`_parse_verdicts`
                # 才能把「判定行裡出現 CR」無歧義地判成行尾汙染而非樣本內容。
                self.assertNotIn("\r", case)

    def test_case_table_has_both_verdicts(self) -> None:
        """表本身必須雙向有樣本——全 True（或全 False）的表對「永遠回同一個值」的
        壞實作零鑑別力。"""
        verdicts = {exp for _c, exp, _w in _VERDICT_CASES}
        self.assertEqual(verdicts, {True, False}, "樣本表必須同時含排除與不排除兩類")


class TestVerdictParsingIsNewlineTransparent(unittest.TestCase):
    """🔴 R68 迴歸鎖：判定行的解析不得被行尾形態左右。

    病灶（windows-compat-ci 首度在真 Windows 跑 `tools/tests/` 時炸出的 3 筆紅）：
    樣本檔在 Windows 被 `write_text` 的預設 `newline` 翻成 CRLF ⇒ bash `read -r` 只斷
    LF、把 `\\r` 留在 `$line` ⇒ 判定行變成 `V|<輸入>\\r|STUB` ⇒ `subprocess(text=True)`
    的 universal newlines 又把那個孤立 CR 翻成 `\\n`、一行裂成兩截殘行 ⇒ 11 筆樣本
    「全數消失」，而失敗訊息只能說「樣本被吃掉」，完全指不出 CR。

    本 class 對 `_parse_verdicts` 純函式釘死三條性質（不需要 bash／PowerShell，
    任何平台都跑）。三條缺一即代表解析層又對換行敏感了。
    """

    # 刻意含一筆帶反斜線的樣本：真實表上的樣本幾乎都是 Windows 路徑。
    _CASES = ("A/x", "B\\y")

    def test_crlf_terminated_lines_parse_identically_to_lf(self) -> None:
        """CRLF 是**合法行終止符**（PowerShell 在 Windows 上的 `Write-Output` 就輸出
        CRLF），必須與 LF 版本解析出完全相同的結果；否則 PS 側會整批誤判為樣本被
        吃掉——那正是「只把 text=True 拿掉、卻沒處理行尾 CR」會踩到的反向坑。"""
        lf = "".join(f"V|{c}|STUB\n" for c in self._CASES)
        crlf = lf.replace("\n", "\r\n")
        self.assertEqual(
            _parse_verdicts(crlf, self._CASES),
            _parse_verdicts(lf, self._CASES),
        )

    def test_cr_inside_a_field_fails_loud_and_names_cr(self) -> None:
        """CR 卡在欄位中間＝樣本在送進生產函式的路上被行尾汙染，判定不是對表上那個
        字串做的。必須 fail loud 並**指名 CR**：默默剝掉是假綠，報「樣本被吃掉」則是
        把查案方向指往錯的地方。"""
        polluted = "".join(f"V|{c}\r|STUB\n" for c in self._CASES)
        with self.assertRaises(AssertionError) as ctx:
            _parse_verdicts(polluted, self._CASES)
        self.assertIn("CR", str(ctx.exception))

    def test_genuinely_eaten_sample_still_reports_eaten(self) -> None:
        """🔴 不得讓原訊息退化：真的少報一筆樣本（與 CR 無關）時，仍必須是原本那句
        「驅動器把某些樣本吃掉了…假綠」，並指名缺的是哪一筆。新增的 CR 檢查是**加在
        前面的更精準診斷**，不是取代這道有牙的自檢。"""
        partial = f"V|{self._CASES[0]}|STUB\n"
        with self.assertRaises(AssertionError) as ctx:
            _parse_verdicts(partial, self._CASES)
        message = str(ctx.exception)
        self.assertIn("吃掉", message)
        self.assertIn("假綠", message)
        self.assertIn(repr(self._CASES[1]), message)


class TestPythonSideVerdicts(unittest.TestCase):
    """兩份 Python 實作（無外部相依，任何平台都實跑）逐筆符合判準。"""

    def test_bootstrap_core_matches_criterion(self) -> None:
        for case, expected, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                self.assertEqual(
                    bootstrap_core._is_windows_apps_stub(case), expected,
                    f"tools/bootstrap_core.py::_is_windows_apps_stub 判定與判準不符（{why}）",
                )

    def test_autoclaude_pre_run_validator_matches_criterion(self) -> None:
        for case, expected, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                self.assertEqual(
                    _autoclaude_is_stub(case), expected,
                    "AutoClaude/autoclaude/execution/pre_run_validator.py::"
                    f"_is_windows_apps_alias_stub 判定與判準不符（{why}）",
                )


@unittest.skipIf(_pwsh_exe() is None, "需要 powershell/pwsh")
class TestPowerShellSideVerdicts(unittest.TestCase):
    """🔴 R67 B3 迴歸鎖：真的起 PowerShell 執行 `Test-IsRealPython`。

    退回 `-notlike '*\\WindowsApps\\*'`（或任何要求分隔符為反斜線的寫法）即紅。
    """

    def _ps_verdicts(self) -> dict[str, bool]:
        with tempfile.TemporaryDirectory() as td:
            samples = _write_verdict_samples(td)
            script = Path(td) / "verdicts.ps1"
            script.write_text(
                _PS_VERDICT_DRIVER.format(
                    guard=_GUARD_PS1.as_posix(), samples=samples.as_posix()
                ),
                encoding="utf-8",
            )
            proc = _run_verdict_driver(
                [
                    _pwsh_exe(), "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script),
                ],
                timeout=120,
            )
        self.assertEqual(
            proc.returncode, 0,
            f"PowerShell 執行失敗（rc={proc.returncode}）：{proc.stdout}\n{proc.stderr}",
        )
        return _parse_verdicts(proc.stdout, _case_inputs())

    def test_powershell_matches_criterion(self) -> None:
        verdicts = self._ps_verdicts()
        for case, expected, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                self.assertEqual(
                    verdicts[case], expected,
                    f"tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython 判定與判準不符"
                    f"（{why}）：is_stub={verdicts[case]}，應為 {expected}——"
                    "與另三份實作相反裁決即 R67 B3 迴歸",
                )

    def test_powershell_agrees_with_both_python_impls(self) -> None:
        """四方等值的 PS↔Python 那兩條邊（不經判準常數，直接比對兩份實作的輸出）。"""
        verdicts = self._ps_verdicts()
        for case, _expected, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                self.assertEqual(
                    verdicts[case], bootstrap_core._is_windows_apps_stub(case),
                    f"PS 與 bootstrap_core 對同一輸入相反裁決（{why}）",
                )
                self.assertEqual(
                    verdicts[case], _autoclaude_is_stub(case),
                    f"PS 與 pre_run_validator 對同一輸入相反裁決（{why}）",
                )


@unittest.skipUnless(_bash_exe(), "本機找不到可用 bash，略過 bash 側判定")
class TestBashSideVerdicts(unittest.TestCase):
    """真的起 bash 執行 `is_real_python_candidate`（shadow `command` builtin）。"""

    def _bash_verdicts(self) -> dict[str, bool]:
        with tempfile.TemporaryDirectory() as td:
            samples = _write_verdict_samples(td)
            proc = _run_verdict_driver(
                [
                    _bash_exe(), "-c", _BASH_VERDICT_DRIVER,
                    "bash", str(_GUARD_SH), str(samples),
                ],
                timeout=60,
            )
        self.assertEqual(
            proc.returncode, 0,
            f"bash 執行失敗（rc={proc.returncode}）：{proc.stdout}\n{proc.stderr}",
        )
        return _parse_verdicts(proc.stdout, _case_inputs())

    def test_bash_matches_criterion(self) -> None:
        verdicts = self._bash_verdicts()
        for case, expected, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                self.assertEqual(
                    verdicts[case], expected,
                    "tools/lib/windowsapps_guard.sh::is_real_python_candidate 判定與"
                    f"判準不符（{why}）：is_stub={verdicts[case]}，應為 {expected}",
                )

    def test_bash_agrees_with_both_python_impls(self) -> None:
        verdicts = self._bash_verdicts()
        for case, _expected, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                self.assertEqual(
                    verdicts[case], bootstrap_core._is_windows_apps_stub(case),
                    f"bash 與 bootstrap_core 對同一輸入相反裁決（{why}）",
                )
                self.assertEqual(
                    verdicts[case], _autoclaude_is_stub(case),
                    f"bash 與 pre_run_validator 對同一輸入相反裁決（{why}）",
                )


@unittest.skipUnless(_bash_exe(), "本機找不到可用 bash，略過行尾紀律端到端驗證")
class TestBashDriverEndToEndNewlineDiscipline(unittest.TestCase):
    """🔴 R68 迴歸鎖（端到端，且**任何平台都跑得動**）：把 Windows 上的病灶鏈在本機
    原樣重放——樣本檔寫成 CRLF，其餘全走真實 bash 驅動器與真實解析層。

    為何本機就足以證明：CRLF 樣本檔是整條鏈**唯一**的平台變因（Windows 的
    `write_text` 行尾翻譯造成），其後每一段——bash `read -r` 只斷 LF、`printf` 原樣
    輸出、Python 側解碼——在 macOS／Linux 上行為相同。故把那個變因手動注入，本機
    重現出的失敗形態即與 windows-compat-ci 上實測到的一致。
    """

    def _drive(self, samples_bytes: bytes) -> str:
        with tempfile.TemporaryDirectory() as td:
            samples = Path(td) / "verdict_cases.txt"
            samples.write_bytes(samples_bytes)
            proc = _run_verdict_driver(
                [
                    _bash_exe(), "-c", _BASH_VERDICT_DRIVER,
                    "bash", str(_GUARD_SH), str(samples),
                ],
                timeout=60,
            )
        self.assertEqual(
            proc.returncode, 0,
            f"bash 執行失敗（rc={proc.returncode}）：{proc.stdout}\n{proc.stderr}",
        )
        return proc.stdout

    def test_crlf_samples_are_diagnosed_as_cr_not_as_eaten_samples(self) -> None:
        """CRLF 樣本檔 ⇒ 解析層必須指名 CR。若哪天有人把 `text=True` 加回
        `_run_verdict_driver`，universal newlines 會把 CR 翻成換行、訊息退回含糊的
        「樣本被吃掉」，本條即紅。"""
        stdout = self._drive(("\r\n".join(_case_inputs()) + "\r\n").encode("ascii"))
        with self.assertRaises(AssertionError) as ctx:
            _parse_verdicts(stdout, _case_inputs())
        self.assertIn("CR", str(ctx.exception))

    def test_written_samples_are_lf_only_and_round_trip_verbatim(self) -> None:
        """正向對照，鎖住寫入側的修法：`_write_verdict_samples` 實際寫出的位元組不得
        含 CR，且每一筆樣本都要逐字原樣回得來。若有人把 `write_bytes` 改回
        `write_text(...)`（`newline` 預設＝平台行尾），本條在 Windows 上直接紅。"""
        with tempfile.TemporaryDirectory() as td:
            written = _write_verdict_samples(td).read_bytes()
        self.assertNotIn(b"\r", written, "樣本檔不得含 CR——行尾必須硬編碼 LF")
        self.assertEqual(
            set(_parse_verdicts(self._drive(written), _case_inputs())),
            set(_case_inputs()),
        )


@unittest.skipUnless(
    _pwsh_exe() is not None and _bash_exe(),
    "需要同時有 PowerShell 引擎與可用 bash 才能一次比齊四方",
)
class TestFourWayVerdictParity(unittest.TestCase):
    """四方一次比齊：任兩份實作對同一輸入給出不同裁決即紅（含判準本身）。

    上面各 class 逐份對「判準常數」比對；本 class 直接兩兩比對**實作彼此**——判準
    常數若哪天被人跟著壞掉的實作一起改（「改測試讓它綠」的典型手法），逐份比對會
    一起變綠，而本 class 仍會抓到四方之間的分歧。
    """

    def test_all_four_implementations_agree_on_every_case(self) -> None:
        ps = TestPowerShellSideVerdicts()._ps_verdicts()
        sh = TestBashSideVerdicts()._bash_verdicts()
        for case, expected, why in _VERDICT_CASES:
            with self.subTest(case=case, why=why):
                verdicts = {
                    "WindowsAppsGuard.ps1": ps[case],
                    "windowsapps_guard.sh": sh[case],
                    "bootstrap_core.py": bootstrap_core._is_windows_apps_stub(case),
                    "pre_run_validator.py": _autoclaude_is_stub(case),
                }
                self.assertEqual(
                    len(set(verdicts.values())), 1,
                    f"四份實作對同一輸入裁決分歧（{why}）：{verdicts}",
                )
                self.assertEqual(
                    set(verdicts.values()), {expected},
                    f"四方雖一致但與判準不符（{why}）：{verdicts}，判準={expected}",
                )


if __name__ == "__main__":
    unittest.main()
