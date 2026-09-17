#!/usr/bin/env python3
"""nightly 載具的直譯器必須「決定性 + 可取證」（DEF-101-506，紀律 #14 延伸；
DEF-200-302 起改為「釘死」而非「使其等價」，見下方訂正）。

WHY（2026-07-27 真機事故，DEF-101-506 立案時的原始問題）：
`run_local_nightly.ps1` 把直譯器存成字面 token `$script:PyExe = 'python'`，每個
呼叫點都由 PATH **現場解析**。於是同一支 nightly：

  - schtasks 排程下 → pyenv-win 的 python（`python.bat` shim，且裝了 psycopg2）
  - 已啟用 monorepo .venv 的終端機／agent 下 → `.venv\\Scripts\\python.exe`
    （真 .exe，且**未**裝 `[postgres,pgvector]` 選配）

兩者跑出來的紅綠不可互相比較：實測一次以 .venv 跑出 `pg-e2e=1`（psycopg2 缺席）
與 `perf=1` 兩個假紅並寫進 `nightly_latest.log`；更隱蔽的是它讓 DEF-101-503
（`%` 被 batch shim 吃掉）的修復「綠得沒有鑑別力」——真 .exe 本來就不觸發該 bug，
沒修也會綠。而 log 當時只印字面 token「python」，事後完全無法指認是哪一顆。

🔴 **DEF-200-302 訂正（掌舵者 2026-09-15 裁決 B 案）**：DEF-101-506 當時的修法＝讓
schtasks 與已啟用 venv 兩種啟動方式「殊途同歸」（互動 shell 偵測到已啟用 venv
就把它的 Scripts 從本行程 PATH 剝除，使解析退回 pyenv 全域）；本檔原本因此在
下方（已刪除的）A/D 兩類鎖住這段「正規化」邏輯與其斜線比對細節。前提已由主控
本場實測推翻：根層 .venv 的 `pyvenv.cfg` home 本身就是同一顆 pyenv-win 3.11.9
二進位，且 xdist／psycopg2／sqlalchemy／pgvector／asyncpg／alembic／pytest 七
項在 pyenv 全域與根 .venv 兩邊皆 PRESENT——「兩套互不受控、可能分岔的依賴集
合」這個風險已不成立（2026-09-13 nightly 曾因 PATH 上的 pyenv 全域缺 xdist 而
pytest rc=4，正是那個風險的真實代價）。故 Windows 側改為與 mac 側同款「絕對路
徑釘死」：不論 schtasks 或已啟用 venv 的終端機／agent 觸發，`run_local_nightly.
ps1`／`windows_smoke_local.ps1` 一律直接使用 `<repo 根>/.venv/Scripts/python.exe`
絕對路徑，不再靠 PATH 現場解析「使其等價」；找不到就 fail-loud（exit 1）。

本檔鎖五件事（B/C 為既有行級靜態檢查；E 為 Windows 絕對路徑釘死鎖，鎖的三支檔＝
`AutoClaude/tools/run_local_nightly.ps1`／`tools/windows_smoke_local.ps1`／
`AutoClaude/tools/local_ci_gate.ps1`；新增 F 為 DEF-200-302 mac 側補齊，鎖的兩支
檔＝`AutoClaude/tools/run_local_nightly.sh`／`tools/macos_smoke_local.sh`）：
  B. 兩支載具都必須把**解析後的直譯器路徑**寫進 log（禁止只印字面 token）。
  C. mac 側維持「絕對路徑釘死」而非 PATH 現場解析（見 F：本輪起兩支 .sh 皆已
     拔除缺席時的 PATH 退路，不再只是「主路徑釘死、缺席仍退回現場解析」）。
  E.（DEF-200-302 新增）Windows 側兩支 .ps1（`run_local_nightly.ps1`／
     `windows_smoke_local.ps1`）都必須絕對路徑釘死根層 `.venv\\Scripts\\
     python.exe`、都必須有 fail-loud 分支（`Test-Path` 不成立即 `exit 1`）；
     `run_local_nightly.ps1` 不得再把 PATH 現場解析的 `Test-IsRealPython
     -CandidateName 'python'` 當直譯器決定者，也不得再含「偵測 `$env:VIRTUAL_ENV`
     即剝除其 Scripts」的正規化區塊；nightly 對 `local_ci_gate.ps1` 的呼叫必須
     帶 `--unattended`（DEF-200-291 無人值守 advisory 降級的前置條件）。
  F.（DEF-200-302 mac 側補齊，2026-09-15）`run_local_nightly.sh` 與
     `macos_smoke_local.sh` 都必須絕對路徑釘死根層 `.venv/bin/python`、都必須
     有 fail-loud 分支（`[ ! -x "$PY" ]`／`[ ! -x "$python_bin" ]` 不成立即
     `exit 1`）；兩檔皆不得再含 `command -v python || command -v python3` 這類
     缺席時退回 PATH 現場解析的分支——`run_local_nightly.sh` 原本就有這段退路
     （C 項此前只驗證「主路徑有沒有釘死」，沒驗證「缺席時是否真的 fail-loud」，
     故放過了它），`macos_smoke_local.sh` 則原本只用 `is_real_python_candidate
     python` 判斷 PATH 上的 python 是否為真直譯器，未保證它就是本 repo 根層
     .venv 那一顆。
  G.（DEF-200-314 新增，2026-09-17）mac launchd nightly 三症狀之二：
     `run_local_nightly.sh` 對 `local_ci_gate.sh` 的呼叫必須帶 `--unattended`
     （E 項已鎖 Windows 側 `-Unattended`，本項補 mac 對稱半——鐵律三漏補）；
     且必須以存在性探測 prepend 兩種 Homebrew bin 前綴（`/opt/homebrew/bin`
     與 `/usr/local/bin`，不可用 `brew --prefix`），修 launchd 極簡 PATH 缺
     pwsh 導致需要 powershell/pwsh 的測試從 platform skip 落成 untagged、
     撞 skip 天花板的問題。

原 A 項（Windows PATH 正規化區塊行級檢查）與 D 項（該正規化比對式的行為級鎖，
DEF-101-522）鎖的正是本輪拔除的那段邏輯，隨程式碼一併移除——史料見 git 歷史與
docs/06_quality/AutoSDD_Defect_Log.md 的 DEF-200-302 條目，不再保留無程式碼可
對照的死鎖。

刻意仍不鎖「兩平台必須用同一顆直譯器」這個問題本身的框架：mac 釘
`.venv/bin/python`、Windows 釘 `.venv\\Scripts\\python.exe`，兩邊本就分屬各自
平台的 `.venv`、路徑分隔符也天然不同——這不是「兩顆不同的直譯器」，只是同一
種「絕對路徑釘死」政策在兩個平台上的自然表達。
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ps_engine import (  # noqa: E402  # R60 E-A-03：引擎述詞 SSOT（語意④）
    native_ps51,
)

_ROOT = Path(__file__).resolve().parents[2]
_PS1 = _ROOT / "AutoClaude" / "tools" / "run_local_nightly.ps1"
_SH = _ROOT / "AutoClaude" / "tools" / "run_local_nightly.sh"
_SMOKE_PS1 = _ROOT / "tools" / "windows_smoke_local.ps1"
# DEF-200-302 mac 側補齊（F 項）：與 _SH 同款需要「無 PATH 退路 + fail-loud」
# 兩支斷言的第二支 .sh 載具。
_MAC_SMOKE = _ROOT / "tools" / "macos_smoke_local.sh"

# DEF-200-302：兩支 .ps1 皆需釘死的絕對路徑字面（相對於各自的 repo 根變數，
# 故只鎖尾段——`.venv\Scripts\python.exe`——不鎖前導變數名，因兩檔前導變數
# 名稱不同（$MonorepoRoot／$RepoRoot）且本鎖只關心「釘死了沒」，不關心變數名）。
_PINNED_VENV_PY_RE = re.compile(r"\.venv\\Scripts\\python\.exe")
# fail-loud 判定：`-not (Test-Path $VenvPy)` 或 `-not (Test-Path $script:PyExe)`
# 出現後，其所在 if 的大括號區塊內必須有 `exit 1`（見 `_has_fail_loud_venv_check`
# 的大括號配對，QA-3 訂正）——本正則只需命中條件本身，不需顧及兩檔外層 if 括號
# 巢狀深度不同（windows_smoke_local.ps1 是 `-or` 複合條件，多包一層括號），因為
# 找區塊起點是用 `text.find("{", ...)` 而非正則，括號巢狀深度不影響命中。
_FAIL_LOUD_CONDITION_RE = re.compile(
    r"-not\s*\(\s*Test-Path\s+\$(?:script:PyExe|VenvPy)\s*\)"
)


def _has_fail_loud_venv_check(text: str) -> bool:
    """QA-3（四方複審）：大括號感知判準——原本「命中條件行後 N 行內找 exit 1」的
    視窗式寫法對兩種 mutant 皆誤判 True：① 條件配對寫反（`exit 1` 錯放在 `else`
    分支，實際只在 venv **存在**時才 exit）；② `exit 1` 落在 if 區塊外（緊接在
    `}` 之後、無條件執行，不論 venv 存不存在都會跑）。兩者都不是「venv 缺席才
    fail-loud」，卻因為文字上仍落在原窗口內而被舊判準放行。

    改法：命中條件後，從**該條件之後第一個 `{`**（if 區塊起點）做大括號配對，
    只在配對出的區塊**內文**找 `exit 1`——區塊外或另一分支的 `exit 1` 一律不算數。
    """
    for match in _FAIL_LOUD_CONDITION_RE.finditer(text):
        brace_start = text.find("{", match.end())
        if brace_start == -1:
            continue
        depth = 0
        block_end = None
        for i in range(brace_start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    block_end = i
                    break
        if block_end is None:
            continue
        block = text[brace_start + 1 : block_end]
        if re.search(r"exit\s+1", block):
            return True
    return False


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _code_only(text: str) -> str:
    """剝除整行 `#` 註解（.sh 慣例；同 test_smoke_ci_sync.py 既有 `_code_only`）。
    F 項訂正文本身逐字引述了被拔除的 `command -v python || command -v python3`
    舊寫法（史料/訂正說明），若不剝除註解，反向鎖會被自己的訂正註記誤判成仍
    殘留該退路。"""
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


_SH_BARE_PATH_FALLBACK_RE = re.compile(r"command\s+-v\s+python3?\b")

# F 項 fail-loud 判準：`[ ! -x "$PY" ]` 或 `[ ! -x "$python_bin" ]`（兩檔變數名
# 不同，機械物只需認出「缺席就 fail-loud」這個形狀）。
_SH_FAIL_LOUD_CONDITION_RE = re.compile(r'\[\s*!\s*-x\s+"\$(?:PY|python_bin)"\s*\]')


def _has_fail_loud_venv_check_sh(text: str) -> bool:
    """F 項 sh 版判準：本 repo 兩支 .sh 載具的 fail-loud 分支皆是單層
    `if [ ! -x "$VAR" ]; then ... exit 1; fi`（無巢狀大括號可比對，不需要
    `_has_fail_loud_venv_check` 的大括號配對），改抓「條件命中後到下一個
    行首 `fi` 之間」是否含 `exit 1`。"""
    code = _code_only(text)
    for match in _SH_FAIL_LOUD_CONDITION_RE.finditer(code):
        fi_at = code.find("\nfi", match.end())
        if fi_at == -1:
            continue
        if re.search(r"exit\s+1", code[match.end():fi_at]):
            return True
    return False


class TestCarrierFilesExist(unittest.TestCase):
    def test_both_carriers_present(self):
        """檔案改名/搬家時本檔其餘斷言會全部靜默失效，先釘存在性。"""
        self.assertTrue(_PS1.is_file(), f"找不到 {_PS1}")
        self.assertTrue(_SH.is_file(), f"找不到 {_SH}")
        self.assertTrue(_SMOKE_PS1.is_file(), f"找不到 {_SMOKE_PS1}")
        self.assertTrue(_MAC_SMOKE.is_file(), f"找不到 {_MAC_SMOKE}")


class TestInterpreterIsForensicallyLogged(unittest.TestCase):
    """B：兩支載具都要把解析後的直譯器寫進 log；只印字面 token 等於沒印。"""

    def test_ps1_logs_resolved_path_not_bare_token(self):
        text = _read(_PS1)
        # 必須解析出絕對路徑，且必須用**兩步式**取 .Source——鏈式
        # `(Get-Command ... -ErrorAction SilentlyContinue).Source` 在 StrictMode 3.0
        # 下 $null.Source 會拋例外（紀律 #14 後半，另有 test_run_local_nightly_static
        # 的機械鎖；本修復初稿即因寫成鏈式被它攔下）。
        # 用 $script:PyExe 而非裸 `python` 字面值：test_windowsapps_guard_cross_consistency
        # 的呼叫點層級判準要求檔內不得有裸字面值 python 呼叫（本修復初稿寫成
        # `Get-Command python` 而被它攔下）。
        self.assertRegex(
            text, r"\$pyCmd\s*=\s*Get-Command\s+\$script:PyExe",
            "run_local_nightly.ps1 必須解析出 python 絕對路徑供取證（DEF-101-506）")
        self.assertRegex(
            text, r"\$pyResolved\s*=\s*if\s*\(\s*\$pyCmd\s*\)",
            "取 .Source 必須兩步式（先存變數再判 $null），不可鏈式存取（紀律 #14）")
        self.assertRegex(
            text, r"可用性驗證通過[^\n]*\$pyResolved",
            "驗證通過的 log 行必須帶上解析後路徑 $pyResolved")
        # 反向鎖：不可退回舊寫法「python 可用性驗證通過…：$script:PyExe」
        self.assertNotRegex(
            text, r"可用性驗證通過[^\n]*：\$script:PyExe\"",
            "log 不可只印字面 token $script:PyExe（值恆為 'python'，無取證價值）")

    def test_sh_logs_resolved_path(self):
        self.assertRegex(
            _read(_SH), r"python 直譯器：",
            "run_local_nightly.sh 必須印出解析後的直譯器路徑，與 .ps1 側取證對稱")


class TestMacInterpreterStaysPinned(unittest.TestCase):
    """C：mac 側的「絕對路徑釘死」是它不受本缺陷影響的原因，不可被改回現場解析。

    F（DEF-200-302 mac 側補齊）：`run_local_nightly.sh` 與 `macos_smoke_local.sh`
    兩支 .sh 載具都須無 PATH 退路、缺席即 fail-loud——與 Windows 側 E 項對稱。
    """

    def test_pins_venv_absolute_path(self):
        self.assertRegex(
            _read(_SH), r'PY="\$ROOT/\.venv/bin/python"',
            "run_local_nightly.sh 必須維持絕對路徑釘死；改回裸 `python` 會把 Windows "
            "側的啟動方式漂移問題複製到 mac（DEF-101-506）")

    def test_no_longer_resolves_bare_python_from_path(self) -> None:
        """F：兩支 .sh 載具不得再有 `command -v python`／`python3` 退路——
        `run_local_nightly.sh` 原本只有主路徑釘死，缺席時仍退回此退路（C 項
        此前只驗證「主路徑有沒有釘死」，未驗證「缺席時是否真的 fail-loud」）；
        `macos_smoke_local.sh` 原本用 `is_real_python_candidate python` 判斷
        PATH 上的 python，未保證那就是本 repo 根層 .venv 那一顆。"""
        for path in (_SH, _MAC_SMOKE):
            code = _code_only(_read(path))
            self.assertNotRegex(
                code, _SH_BARE_PATH_FALLBACK_RE,
                f"{path.name} 不得再以 `command -v python`／`python3` 退回 PATH "
                "現場解析當直譯器決定者（DEF-200-302）")

    def test_fail_loud_when_venv_missing(self) -> None:
        """F：兩支 .sh 載具都必須有「根層 .venv 直譯器不存在即 exit 1」的
        fail-loud 分支，不得只印警告或靜默退回其他解析方式。"""
        for path in (_SH, _MAC_SMOKE):
            text = _read(path)
            self.assertTrue(
                _has_fail_loud_venv_check_sh(text),
                f"{path.name} 必須有「根層 .venv 直譯器不存在即 exit 1」的 "
                "fail-loud 分支（DEF-200-302）")


class TestDetectorItself(unittest.TestCase):
    """紀律「驗證鏡子自身要被驗證」：確認上面的反向鎖真的抓得到舊寫法。"""

    def test_old_bare_token_pattern_would_be_caught(self):
        legacy = 'Log "python 可用性驗證通過（非 WindowsApps 空殼）：$script:PyExe"'
        self.assertTrue(
            re.search(r"可用性驗證通過[^\n]*：\$script:PyExe\"", legacy),
            "反向鎖的 regex 必須能命中修復前的舊寫法，否則該斷言是空殼")


class TestHasFailLoudVenvCheckIsBraceAware(unittest.TestCase):
    """QA-3（四方複審）反事實測試：舊的「視窗式」判準對下列兩段 mutant 文字皆會
    誤判 `True`（`exit 1` 字面剛好落在命中行後 5 行內）；大括號感知版必須正確
    判定這兩段皆是 `False`——`exit 1` 沒有真的落在該 if 的區塊內。"""

    def test_condition_and_exit_swapped_across_if_else_is_false(self) -> None:
        """mutant①「條件寫反」：`exit 1` 錯放在 `else` 分支，實際只在 venv
        **存在**（`Test-Path` 為真）時才會 exit，缺席時反而只印一行 log——
        與「缺席才 fail-loud」的原意完全相反。"""
        mutant = (
            "if (-not (Test-Path $VenvPy)) {\n"
            '  Write-Host "venv 存在，正常"\n'
            "} else {\n"
            "  exit 1\n"
            "}\n"
        )
        self.assertFalse(
            _has_fail_loud_venv_check(mutant),
            "exit 1 落在 else 分支（條件配對寫反）時，判準不應判定為有效的 "
            "fail-loud 檢查，卻回傳 True")

    def test_exit_after_if_block_closes_is_false(self) -> None:
        """mutant②「exit 1 在 if 區塊外」：`exit 1` 緊接在 `}` 之後、不受條件保護，
        不論 venv 存不存在都會無條件執行——同樣不是「缺席才 fail-loud」。"""
        mutant = (
            "if (-not (Test-Path $VenvPy)) {\n"
            '  Write-Host "缺 venv" \'WARN\'\n'
            "}\n"
            'Write-Host "無論如何都會印這行" \'INFO\'\n'
            "exit 1\n"
        )
        self.assertFalse(
            _has_fail_loud_venv_check(mutant),
            "exit 1 落在 if 區塊外（無條件執行）時，判準不應判定為有效的 "
            "fail-loud 檢查，卻回傳 True")


class TestWindowsInterpreterStaysPinned(unittest.TestCase):
    """E（DEF-200-302 新增）：Windows 兩支 .ps1 都必須絕對路徑釘死根層 .venv，
    不得再靠 PATH 現場解析「使其與 schtasks 排程等價」。"""

    def test_both_windows_carriers_pin_venv_python_absolute_path(self):
        for path in (_PS1, _SMOKE_PS1):
            text = _read(path)
            self.assertRegex(
                text, _PINNED_VENV_PY_RE,
                f"{path.name} 必須含 `.venv\\Scripts\\python.exe` 絕對路徑字面"
                "（DEF-200-302：釘死根層 .venv，不靠 PATH 現場解析）")

    def test_both_windows_carriers_fail_loud_when_venv_missing(self):
        for path in (_PS1, _SMOKE_PS1):
            text = _read(path)
            self.assertTrue(
                _has_fail_loud_venv_check(text),
                f"{path.name} 必須有「根層 .venv 直譯器不存在即 exit 1」的 "
                "fail-loud 分支，不得再退化為 PATH 現場解析（DEF-200-302）")

    def test_run_local_nightly_no_longer_resolves_bare_python_from_path(self):
        """DEF-101-506 舊決定者：`Test-IsRealPython -CandidateName 'python'`
        （裸字面值 'python'）不得再作為直譯器判定式——現在應改判定 $VenvPy／
        $script:PyExe 這個已釘死的絕對路徑。"""
        text = _read(_PS1)
        self.assertNotIn(
            "Test-IsRealPython -CandidateName 'python'", text,
            "run_local_nightly.ps1 不得再以裸字面值 'python' 現場解析 PATH 當"
            "直譯器決定者（DEF-200-302：改用已釘死的根層 .venv 絕對路徑）")

    def test_run_local_nightly_no_longer_strips_active_venv_from_path(self):
        """DEF-101-506 舊「殊途同歸」正規化區塊（偵測已啟用 venv 就從 PATH 剝除
        其 Scripts）已隨 DEF-200-302 拔除——保留會與「直接釘死」的新設計互相矛盾。"""
        text = _read(_PS1)
        self.assertNotIn(
            "if ($env:VIRTUAL_ENV)", text,
            "run_local_nightly.ps1 不應再有偵測 $env:VIRTUAL_ENV 並剝除其 Scripts "
            "的正規化區塊（DEF-200-302：已改為直接釘死根層 .venv，不需要「使其"
            "與 schtasks 等價」這個中間步驟）")

    def test_run_local_nightly_calls_local_ci_gate_with_unattended_flag(self):
        """DEF-200-302 step(e)：無人值守 nightly 呼叫 local_ci_gate.ps1 必須帶
        無人值守旗標，讓 check_skip_census 對未登記剖面降級為真正的 advisory
        （DEF-200-291 的前置條件）。

        🔴 DEF-200-303 訂正：斷言目標由 `--unattended`（位置參數）改為 `-Unattended`
        （PowerShell switch 形態）——`local_ci_gate.ps1` 是 `[CmdletBinding()]` 薄殼，
        `param()` 只認具名參數，位置參數 `--unattended` 會讓參數綁定失敗（rc=1）。
        核心 `local_ci_gate.py` 的 `--unattended` 由薄殼在內部轉發（見該檔
        `if ($Unattended) { $CliArgs += '--unattended' }`），呼叫端只能打 `-Unattended`。
        """
        text = _read(_PS1)
        self.assertRegex(
            text, r"-File\s+tools/local_ci_gate\.ps1\s+-Unattended",
            "nightly 對 local_ci_gate.ps1 的呼叫必須附加 -Unattended 引數（PowerShell "
            "switch 形態；-File 薄殼不吃位置參數 --unattended）")

    def test_run_local_nightly_sh_calls_local_ci_gate_with_unattended_flag(self):
        """DEF-200-314 G 項：mac 對稱鎖——run_local_nightly.sh 呼叫
        local_ci_gate.sh 必須帶 --unattended。mac 側 local_ci_gate.sh 是
        `python local_ci_gate.py "$@"` 薄殼，位置旗標直接轉發給核心（與
        Windows 側 CmdletBinding 具名參數語意不同，故正則不同）。

        🔴 四方複審訂正：鎖緊到 `run_stage 3 autoclaude_gate` 那一整行本身
        （而非任意子字串 `local_ci_gate.sh" --unattended`），避免未來有人把
        旗標搬到不相干的呼叫上也能矇混過關——本判準就是要那一行、原封不動。

        WHY：run_local_nightly.sh 檔頭 stage 3 說明句自陳「鏡像 CI push
        gating」，但 GitHub Actions 靠 GITHUB_ACTIONS 環境變數自動判定
        unattended，launchd 排程執行沒有這個變數；不顯式帶旗標，
        check_skip_census 對未登記剖面就不會降級為 advisory，會撞 skip
        天花板（DEF-200-314 S3：.ps1 側早於 DEF-200-302/303 補齊，.sh 側
        當時漏補，鐵律三未落實的具體案例）。
        """
        text = _read(_SH)
        self.assertRegex(
            text,
            re.compile(
                r'^run_stage 3 autoclaude_gate bash '
                r'"\$ROOT/AutoClaude/tools/local_ci_gate\.sh" --unattended\s*$',
                re.MULTILINE,
            ),
            "run_local_nightly.sh 的 run_stage 3 那一整行必須逐字附加 --unattended"
            "（mac 對稱：Windows 側已由 DEF-200-302 step(e) 補齊，本測補 mac 半）")

    def test_run_local_nightly_sh_prepends_homebrew_bin_by_existence_probe(self):
        """DEF-200-314 S1：launchd 極簡 PATH 缺 Homebrew bin ⇒ pwsh 不可解析 ⇒
        24 支「需要 powershell/pwsh」測試從 platform 語意的 skip 落成
        untagged／debt 語意，撞 skip 天花板。修法是兩種 Homebrew 前綴都做
        存在性探測後 **append 到 PATH 尾端**（鐵律三：Apple Silicon=/opt/
        homebrew、Intel=/usr/local，不可寫死單一架構），且不可用
        `brew --prefix`——極簡 PATH 下 brew 本身可能解析不到。

        🔴 四方複審訂正（QA＋Architect 同時抓到）：探測迴圈原本往前插
        （`PATH="${_hb_bin}:${PATH}"`）會把 Homebrew 排到 `.venv/bin` 前面，
        違反單一 .venv 原則（本機未炸純屬僥倖：Homebrew 目錄當下無裸
        `python`）。改為 append 到尾端後補三支斷言：①迴圈必須在第一個
        `run_stage ` 呼叫之前出現（PATH 設定本就該搶在任何 stage 執行前）；
        ②必須是尾端追加形態；③不得含往前插形態。三者皆先剝掉整行 `#`
        註解再比對（與既有 `brew --prefix` 判準對稱處理，理由同）。
        """
        text = _read(_SH)
        code_lines = [
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#")
        ]
        code_text = "\n".join(code_lines)
        self.assertRegex(
            code_text, r'for _hb_bin in .*/opt/homebrew/bin',
            "run_local_nightly.sh 必須以存在性探測 prepend /opt/homebrew/bin"
            "（Apple Silicon Homebrew 前綴）")
        self.assertRegex(
            code_text, r'/usr/local/bin',  # posix-abs-ok: 比對對象是 .sh（bash-only）原始檔文字，非 Path/os.fspath 產物，不受 Windows 反斜線渲染影響
            "run_local_nightly.sh 必須同時探測 /usr/local/bin"
            "（Intel Homebrew 前綴），不可只認單一架構）")
        self.assertNotRegex(
            code_text, r'brew\s+--prefix',
            "不可用 `brew --prefix` 探測 Homebrew 路徑——極簡 PATH 下 brew "
            "本身可能解析不到（DEF-200-314 S1；本判準只查非註解行，允許 "
            "WHY 註解討論此決策）")

        loop_match = re.search(r'for _hb_bin in ', code_text)
        run_stage_match = re.search(r'^run_stage ', code_text, re.MULTILINE)
        self.assertIsNotNone(loop_match, "找不到 Homebrew 探測迴圈")
        self.assertIsNotNone(run_stage_match, "找不到任何 run_stage 呼叫")
        self.assertLess(
            loop_match.start(), run_stage_match.start(),
            "Homebrew 探測迴圈必須在第一個 run_stage 呼叫之前完成——PATH 設定"
            "本就該搶在任何 stage 執行前生效，四方複審訂正的位置鎖")
        self.assertRegex(
            code_text, r'PATH="\$\{PATH\}:\$\{_hb_bin\}"',
            "Homebrew 探測必須是**尾端追加**形態（`PATH=\"${PATH}:${_hb_bin}\"`）"
            "——往前插會把 Homebrew 排到 .venv/bin 前面，違反單一 .venv 原則")
        self.assertNotRegex(
            code_text, r'PATH="\$\{_hb_bin\}:\$\{PATH\}"',
            "不得再含往前插形態（`PATH=\"${_hb_bin}:${PATH}\"`）——四方複審"
            "訂正：往前插會讓 Homebrew 排到 .venv/bin 前面")


# ── 行為級鎖（既有）：兩支 .ps1 必須能被原生 PowerShell 5.1 解析 ────────────────
class TestWindowsPs1ParseCleanly(unittest.TestCase):
    """行為級補強：DEF-200-302 改動了兩支 .ps1 的開頭區塊，用真的
    [System.Management.Automation.Language.Parser]::ParseFile 確認零語法錯誤——
    純字串鎖抓不到「改壞語法但字面值仍命中 regex」這類缺陷。"""

    @unittest.skipUnless(
        # DEF-200-303（主控追加）：標籤改為 `[WINDOWS-NATIVE-ONLY]`——
        # `tools/lib/skip_tag_policy.ALL_SKIP_TAGS` 只認這個字面（不認 `[WINDOWS-ONLY]`），
        # 舊字面會被 `unregistered_tag_problems()` 的反向檢查判成未登記標籤。
        sys.platform == "win32", "[WINDOWS-NATIVE-ONLY] 需要原生 PowerShell 引擎解析 .ps1"
    )
    def test_both_windows_carriers_parse_with_zero_errors(self) -> None:
        for path in (_PS1, _SMOKE_PS1):
            script = (
                "$errors = $null; "
                f"[void][System.Management.Automation.Language.Parser]::ParseFile("
                f"'{path}', [ref]$null, [ref]$errors); "
                "Write-Output ($errors.Count)"
            )
            proc = subprocess.run(
                [native_ps51(), "-NoProfile", "-Command", script],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
            )
            self.assertEqual(
                proc.returncode, 0,
                f"{path.name} parser 呼叫失敗：\n{proc.stdout}\n{proc.stderr}",
            )
            self.assertEqual(
                proc.stdout.strip(), "0",
                f"{path.name} 有 {proc.stdout.strip()} 個 parse error：\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
