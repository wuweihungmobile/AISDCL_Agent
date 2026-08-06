#!/usr/bin/env python3
"""smoke 腳本 ↔ compat-CI ↔ ONBOARDING 的數字/注記機械互鎖（R11 Architect B2）。

WHY：macos_smoke_local.sh / windows_smoke_local.ps1 / macos-compat-ci.yml /
windows-compat-ci.yml 是四份手寫實作，互相宣稱「同步維護」，但 R11 前純靠註解
自律、零機械互鎖——smoke 腳本改 PASS 下限釘選或增刪情境分組時，ONBOARDING.md
的宣稱數字（PASS=10 / PASS=8）與 CI 對應 step 不會有任何訊號。本測試機械抽取
兩腳本的釘選值與 `--- [n/m]` 情境分組標籤，交叉斷言文件宣稱一致、同步注記仍在；
抽取數量另設下限釘選，防宣告 pattern 漂移後靜默 0 命中假綠（比照
check_script_parity._MIN_EXTRACT_COUNTS 慣例）。
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _platform_helpers import usable_bash_for_fixture  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]
# 真跑受測 .sh 用的直譯器（WHY 不得寫裸 `"bash"`：見 `TestMacSmokeCliContract._run`
# 與 `_platform_helpers.usable_bash_for_fixture()` 的 docstring／DEF-101-753）。
_BASH = usable_bash_for_fixture()
_SH = _REPO_ROOT / "tools" / "macos_smoke_local.sh"
_PS1 = _REPO_ROOT / "tools" / "windows_smoke_local.ps1"
_MAC_CI = _REPO_ROOT / ".github" / "workflows" / "macos-compat-ci.yml"
_WIN_CI = _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml"
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"
_ROOT_INFRA_CI = _REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml"

# `git ls-files … -- '<pathspec>' …` 區塊（至第一個 `)` 為止；兩檔皆以續行寫多樣式）。
_LS_FILES_BLOCK_RE = re.compile(r"ls-files\s.*?\)", re.DOTALL)
_QUOTED_TOKEN_RE = re.compile(r"'([^']+)'")

# 情境分組標籤（echo/Write-Host 的字面 `--- [n/m]`；檔內框線註解用 U+2500「──」
# 不會誤中）。抽取數量下限釘選＝2026-07-17 現況分組數，刻意刪減分組時同步下修。
_GROUP_RE = re.compile(r"---\s*\[(\d+)/(\d+)\]")
_MIN_GROUPS = {"sh": 5, "ps1": 6}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _region(text: str, pattern: str, label: str) -> str:
    """抽出指定區塊全文（抽不到即 fail-loud——區塊結構被改動時不得靜默降級成
    整檔比對，那會讓區塊內的漂移被檔案別處的巧合字串滿足）。"""
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if m is None:
        raise AssertionError(f"抽不到 {label}（pattern 未命中：{pattern!r}）——結構已變動")
    return m.group(0)


def _code_only(text: str) -> str:
    """剝掉整行 `#` 註解（yml 與 sh 同款）——本檔既有 `_yml_python_tools` 風格的
    慣例：註解裡提及某字串是沿革記載/史料，不算實作，不得滿足接線斷言。"""
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


def _extract_pin(text: str, pattern: str) -> int:
    m = re.search(pattern, text, re.MULTILINE)
    if m is None:  # 不用裸 assert：python -O 會剝除 assert，守門靜默失效（R11 P4）
        raise AssertionError(f"抽取不到 PASS 下限釘選——pattern 未命中：{pattern!r}（宣告樣式已漂移）")
    return int(m.group(1))


# --- $MinPass/MIN_PASS 語意鎖（R19 修復包 B，DEF-101-243①）登記表 -----------------

_SH_PASS_RE = re.compile(r'pass\s+"([^"]*)"')

# macos_smoke_local.sh 裡「字面上兩個 pass 呼叫、實際執行只會命中其一」的互斥分支
# （case 分支 / if-else 分支）。每個 tuple 是該互斥組的完整訊息文字集合。
_SH_EXCLUSIVE_PASS_GROUPS = (
    (
        "dispatcher 直呼煙霧（pre-commit 放行/擋 NTFS 保留名、post-commit、pre-push 刪除跳過）",
        "dispatcher 直呼煙霧（pre-commit 放行、post-commit、pre-push 刪除跳過；NTFS 保留名子測試 SKIP——非 macOS 平台先擋）",
    ),
    (
        "install_mac_nightly.sh --render-only plist 產出＋plutil -lint＋log 落點斷言",
        "install_mac_nightly.sh --render-only（SKIP-計-PASS：非 macOS）",
    ),
)

_PS1_PASS_ITEM_RE = re.compile(r"Pass-Item\s+['\"]([^'\"]*)['\"]")

# windows_smoke_local.ps1 裡「函式定義內只有 1 個 Pass-Item 字面出現，但函式被
# 呼叫多次」的共用函式（每次呼叫最多貢獻 1 個實際 PASS）。
_PS1_MULTI_CALL_FUNCS = ("Test-InstallRoundtrip", "Test-WorktreeReject")


# --- [1/9] pwsh parse 掃描面三向鎖（R56 round 5，round 4 三方交叉印證）-----------

# windows_smoke_local.ps1 的 `@{ Rel = …; Floor = N }` 樹登記項；Rel 兩種形態：
# 字面字串（`'AutoClaude\tools'`）與 LATEST 的動態 `(Join-Path 'AISDLC_SDD' $latestName)`。
_PS1_TREE_ENTRY_RE = re.compile(
    r"@\{\s*Rel\s*=\s*(?P<rel>'[^']*'|\(Join-Path\s+[^)]*\))\s*;\s*Floor\s*=\s*(?P<floor>\d+)\s*\}"
)


def _load_ps51_module() -> ModuleType:
    """以檔案路徑載入 `tools/tests/test_ps51_compat.py`（不寫進 sys.modules，避免與
    unittest discover 出來的同名模組互相干擾）。

    刻意呼叫其 `scan_trees()` 取**實際回傳值**、而非用 regex 抽 `specs` 字面清單：
    後者只鎖得住原始碼長相，`_latest_root()` 或 `_git_tracked_ps1()` 被改壞時仍綠。
    """
    path = _REPO_ROOT / "tools" / "tests" / "test_ps51_compat.py"
    spec = importlib.util.spec_from_file_location("_ps51_compat_for_sync_lock", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"無法載入 {path}——.ps1 掃描面三向鎖失效（檔案被移除/改名？）")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ps1_scan_trees(region: str) -> dict[str, int]:
    """`windows_smoke_local.ps1` [1/9] 區塊的 {樹 key: 檔數下限}。

    正規化到與 `test_ps51_compat.scan_trees()` 同一鍵空間：反斜線 → `/`；
    LATEST 的動態 Join-Path 形 → 佔位符 `LATEST`（升版不失效）。
    """
    trees: dict[str, int] = {}
    for m in _PS1_TREE_ENTRY_RE.finditer(region):
        raw = m.group("rel")
        if raw.startswith("("):
            if "'AISDLC_SDD'" not in raw or "$latestName" not in raw:
                raise AssertionError(
                    f"windows_smoke_local.ps1 [1/9] 的動態樹寫法非預期：{raw!r}——"
                    "LATEST 必須是 `(Join-Path 'AISDLC_SDD' $latestName)`（SSOT 解析結果）"
                )
            key = "LATEST"
        else:
            key = raw.strip("'").replace("\\", "/")
        if key in trees:
            raise AssertionError(
                f"windows_smoke_local.ps1 [1/9] 出現重複掃描樹 {key!r}——"
                "同一棵樹登記兩次會讓下方集合比對誤判為一致"
            )
        trees[key] = int(m.group("floor"))
    return trees


def _extract_ps1_function_body(text: str, func_name: str) -> str:
    """抽出 `function <func_name> {` 到下一個「行首恰為 `}`」之間的函式體全文
    （本檔兩支共用函式皆以此縮排慣例撰寫：函式自身收尾 `}` 在行首列 0，內部巢狀
    區塊的收尾皆有縮排，不會提前誤中）。"""
    m = re.search(rf"^function\s+{re.escape(func_name)}\b.*?\n(.*?)^\}}", text, re.MULTILINE | re.DOTALL)
    if m is None:
        raise AssertionError(f"windows_smoke_local.ps1 找不到 {func_name} 函式定義——結構已變動，需同步更新語意鎖登記表")
    return m.group(1)


# R56 round 6（QA B-1）：CI 第 2 道掃描樹抽取式。字元類必須容納 `.`／`-`，
# 否則 `.github/scripts` 這類路徑被插進 CI 時本鎖靜默失效（實測 11 支全綠）。
# R57 修正（A2）：抽取式與計數錨原本在本檔／test_ps1_bom／test_ps51_compat 三份逐字
# 複製且皆硬綁 `-Path` 具名參數，位置參數形態（`-Path` 省略）可完全繞過；已收斂進
# `_ci_scan_anchors` SSOT（WHY 見該模組 docstring）。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ci_scan_anchors import (  # noqa: E402
    EXPECTED_CI_GCI_CALLS,
    EXPECTED_CI_SCAN_STATEMENTS,
    ci_fixed_trees,
    ci_gci_call_count,
    ci_scan_statement_count,
)

# --- windows-compat-ci.yml「shell 絕對宣稱」全檔掃描鎖（R60 DEF-101-540）-----------

_CLAIM_QUOTE_BEGIN = "CLAIM-QUOTE-BEGIN"
_CLAIM_QUOTE_END = "CLAIM-QUOTE-END"

# 四段式：(全部|其餘|所有) → (步驟|step) → 一律 → pwsh，中間允許跨行、跨註解符。
# 為何**不能**逐行比對：R60 實測的三個殘留站點裡，最後一個正是拆成兩行寫的
# （「…本 workflow 全部步驟（windows-smoke／windows-nightly-full）」＋「一律 shell:
# pwsh，從未用原生 Windows PowerShell 5.1」），逐行掃描對它天生零訊號——那恰好是
# 這句話能在 R57 訂正之後仍存活的原因之一。故先把註解符與換行攤平再掃。
_ABSOLUTE_SHELL_CLAIM_RE = re.compile(
    r"(?:全部|其餘|所有)[\s\S]{0,25}?(?:步驟|step)[\s\S]{0,80}?一律[\s\S]{0,40}?pwsh"
)

# 豁免區行數上限：防「把 sentinel 拉大到蓋住全檔」這種最省事的繞過方式。
# R60 落地時實測該區 68 行（自寫探針實量，非估算），留約 1.3 倍緩衝。
_MAX_CLAIM_QUOTE_LINES = 90


def _flatten_prose(text: str) -> str:
    """攤平換行與行首註解符，讓跨行的中文句子重新接成連續字串。"""
    return re.sub(r"\n[ \t]*#?[ \t]*", "", text)


class TestWindowsCiShellClaimConsistency(unittest.TestCase):
    """`windows-compat-ci.yml` 全檔不得再出現「全部／其餘步驟一律 shell: pwsh」式的
    絕對宣稱（訂正引述區除外）。

    WHY（DEF-101-540，R60 Scan-C C-02）：同一句宣稱已**三度失實**——R5 原文寫死、
    R57 round 1 改寫成「windows-latest 的步驟一律」仍被 pyyaml 稽核證偽、R57 收輪只改
    了檔頭而 step name 與兩處 step 註解逐字存活到 R60。實測分佈：windows-smoke
    ＝pwsh 19／bash 1，windows-nightly-full＝powershell 2／pwsh 3（其中 2 步原生
    PS 5.1 正是該宣稱的直接反例，且其中一步的 name 自己就掛著那句宣稱）。
    現行機械鎖 `test_gha_action_versions.py::TestWindowsCiHeaderSnapshotLock` 只比對
    **檔頭那張快照表** vs YAML 實況，對散文（step name／註解）零訊號。

    為何鎖住「措辭」而不是「數字」：R57 已立政策——不得寫死支數（寫死＝下一輪必再
    過期）。本鎖因此不驗任何計數，只禁止「一律／全部」這種不依賴實測就成立不了的
    絕對詞出現在宣稱句裡；要陳述分佈就去看檔頭那張由姊妹鎖看守的實測表。

    為何住在本檔：本檔 docstring 立的正是「四份手寫實作互相宣稱同步維護、零機械
    互鎖」這條軸，且本檔已在 `test_sync_maintenance_comments_present` 讀取
    `_WIN_CI` 做散文斷言——同一條軸、同一份輸入。姊妹鎖（檔頭快照表 vs YAML 實況）
    在 `tools/tests/test_gha_action_versions.py::TestWindowsCiHeaderSnapshotLock`，
    兩者互補：那支管「表要對」，本支管「別在表以外再自己講一遍」。

    鑑別力（鏡子自證，不靠改壞檔案）：豁免區內**必須**至少命中一次——那裡刻意逐字
    引述舊宣稱以資訂正。若有人把 `_ABSOLUTE_SHELL_CLAIM_RE` 改寬鬆到抓不到東西，
    正控會先紅；sentinel 兩端缺一、或豁免區被撐大到超過上限，也都會紅。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = _read(_WIN_CI)

    def _split_regions(self) -> tuple[str, str]:
        """回傳 (豁免區, 其餘全檔)。sentinel 缺失/重複/順序錯即 fail-loud。"""
        for marker in (_CLAIM_QUOTE_BEGIN, _CLAIM_QUOTE_END):
            self.assertEqual(
                self.text.count(marker), 1,
                f"{_WIN_CI.name} 的 {marker} sentinel 出現 {self.text.count(marker)} 次"
                f"（預期恰 1）——豁免區界被刪除或重複，本鎖的豁免判定失效",
            )
        begin = self.text.index(_CLAIM_QUOTE_BEGIN)
        end = self.text.index(_CLAIM_QUOTE_END)
        self.assertLess(begin, end, f"{_WIN_CI.name} 的 CLAIM-QUOTE sentinel 順序顛倒")
        return self.text[begin:end], self.text[:begin] + self.text[end:]

    def test_quote_exemption_region_is_bounded(self) -> None:
        """豁免區不得被撐大到蓋住全檔（最省事的繞過方式）。"""
        quoted, _rest = self._split_regions()
        lines = quoted.count("\n")
        self.assertLessEqual(
            lines, _MAX_CLAIM_QUOTE_LINES,
            f"{_WIN_CI.name} 的 CLAIM-QUOTE 豁免區已達 {lines} 行 > 上限 "
            f"{_MAX_CLAIM_QUOTE_LINES}——豁免區只該容納訂正引述，不該吞掉整份檔案；"
            "若確有正當需要請連同 _MAX_CLAIM_QUOTE_LINES 一併調整並說明 WHY",
        )

    def test_claim_regex_still_matches_the_known_false_claim(self) -> None:
        """正控（鏡子自證）：豁免區內至少一筆舊宣稱引述必須被本鎖的正則命中。"""
        quoted, _rest = self._split_regions()
        hits = _ABSOLUTE_SHELL_CLAIM_RE.findall(_flatten_prose(quoted))
        self.assertGreaterEqual(
            len(hits), 1,
            "CLAIM-QUOTE 豁免區內找不到任何「全部/其餘步驟一律 pwsh」式引述——"
            "正則可能已被改寬鬆到零鑑別力，或引述被刪除（引述被刪＝訂正的依據消失）",
        )

    def test_no_absolute_shell_claim_outside_quote_region(self) -> None:
        """本體斷言：豁免區以外（含 step name 與所有 step 註解）零命中。"""
        _quoted, rest = self._split_regions()
        flat = _flatten_prose(rest)
        hits = [m.group(0) for m in _ABSOLUTE_SHELL_CLAIM_RE.finditer(flat)]
        self.assertEqual(
            hits, [],
            f"{_WIN_CI.name} 在 CLAIM-QUOTE 豁免區之外仍出現「全部/其餘步驟一律 "
            f"shell: pwsh」式絕對宣稱（同一句已三度失實，DEF-101-486／529）：{hits}。"
            "實測分佈：windows-smoke=pwsh 19/bash 1、windows-nightly-full="
            "powershell 2/pwsh 3——請改用不依賴計數的措辭（例：「以 shell: pwsh 為"
            "主要引擎，實際分佈見檔頭逐 job 稽核表」），勿寫死支數",
        )


class TestWindowsSmokeCarrierGuard(unittest.TestCase):
    """QA-R59-04：`windows_smoke_local.ps1` 的 MSYSTEM 載具守門必須有回歸鎖。

    WHY：DEF-101-511 的整個修法主張是「把只寫在註解的載具約束**升為機械強制**」，但守門
    本身若沒有鎖，刪掉它全套照綠——那就與註解同級，主張自我否定。實測 `grep -rn MSYSTEM
    tools/tests/ AutoClaude/tests/` 在本鎖之前為**零命中**。
    """

    def test_msystem_fail_fast_guard_present_and_before_any_work(self):
        ps1 = _REPO_ROOT / "tools" / "windows_smoke_local.ps1"
        text = ps1.read_text(encoding="utf-8-sig", errors="replace")
        self.assertIn(
            "if ($env:MSYSTEM)", text,
            "缺少 MSYSTEM 載具守門——經 Git Bash 呼叫會在非 ASCII 路徑步驟產生假紅"
            "（DEF-101-511；R59 實測 PASS=11 FAIL=2 vs 原生 PASS=12 FAIL=0）")
        guard_at = text.index("if ($env:MSYSTEM)")
        # 必須 fail-fast：守門區塊內要有 exit 1
        # R59 二審 QA-R59-P2 訂正：原為 `text[guard_at:guard_at + 1200]`，而守門區塊實際只有
        # **570 字元** → 1200 的窗口越界吃進緊接在後的 git 前置守門（該處自帶 `exit 1`），
        # 於是「把守門降級成只印警告」這個**最可能的實際退化**照樣綠（QA 以副本注入實證：
        # 刪守門→RED、搬位置→RED、移除 exit 1→**GREEN**）。改為切到本區塊自己的結尾。
        guard_block = text[guard_at:text.index("\n}", guard_at)]
        self.assertIn("exit 1", guard_block, "MSYSTEM 守門必須 exit 1 拒跑，不可只印警告")
        # 位置：必須早於第一個實際驗證段落（[1/ 標籤）與 git/python 前置守門
        first_step = text.index("--- [1/")
        self.assertLess(
            guard_at, first_step,
            "MSYSTEM 守門必須在任何驗證段落之前——晚於任何副作用就失去 fail-fast 意義")

    def test_engine_mismatch_guard_present_and_before_any_work(self):
        """🔴 R73（DEF-101-784）：ENGINE-MISMATCH 引擎守門必須有回歸鎖。

        WHY 與上一支同構（QA-R59-04 的原話直接適用）：「守門本身若沒有鎖，刪掉它
        全套照綠——那就與註解同級，主張自我否定」。R73 為 DEF-101-776 補了守門
        卻**沒補鎖**，而同一輪的 DEF-101-773 結案語才剛寫下「已知缺口不得只以劃界
        結案（DEF-101-757）」——同輪自我違反，QA 二審點名。實測本鎖之前全庫
        `*test*.py` 對 `ENGINE-MISMATCH` **零命中**。

        為何這個守門特別需要鎖：它的鑑別力來源是「[1/9] 的 Parser 解析必須用 5.1
        的文法」，而 5.1 對「UTF-8 無 BOM ＋ 中文註解」的 .ps1 會 parse 死、pwsh 7
        不會（R73 全庫 137 支實測 5.1 ERR=29 / 7.6.4 ERR=0）。守門被刪掉時**不會
        有任何紅燈**——本機照跑、CI 不執行這支腳本——直到某天有人在 mac/CI 上炸掉。
        """
        ps1 = _REPO_ROOT / "tools" / "windows_smoke_local.ps1"
        text = ps1.read_text(encoding="utf-8-sig", errors="replace")
        # 🔴 必須錨定**行首的程式碼行**，不能只用 `text.index(needle)`：該檔的 WHY
        # 註解裡逐字引述了 CI 側的同一個判準，`index` 會命中註解、於是切出的
        # guard_block 是一段註解而非程式碼（我第一版就是這樣寫的，實測誤判）。
        # 這與 R59 二審 QA-R59-P2 訂正的是同一類「窗口取錯」問題，只是方向不同。
        m = re.search(
            r"(?m)^if \(\$PSVersionTable\.PSVersion\.Major -ne 5\) \{", text)
        self.assertIsNotNone(
            m,
            "缺少引擎守門（行首的 if 程式碼行）——用 pwsh 7 跑本腳本會讓 [1/9] 的語法"
            "解析改用 PS 7 文法，「5.1 解析不過、7 解析得過」的寫法全部逸出，"
            "且不會有任何訊號（DEF-101-776）")
        guard_at = m.start()
        # 切到本區塊自己的結尾（沿用 R59 二審 QA-R59-P2 的訂正：固定寬度窗口會越界
        # 吃進後面自帶 exit 1 的守門，使「降級成只印警告」這個最可能的退化照綠）
        guard_block = text[guard_at:text.index("\n}", guard_at)]
        self.assertIn(
            "exit 1", guard_block,
            "引擎守門必須 exit 1 拒跑，不可只印警告——R73 之前它就是只 Write-Host 印版本")
        first_step = text.index("--- [1/")
        self.assertLess(
            guard_at, first_step,
            "引擎守門必須早於任何驗證段落：晚於 [1/9] 就等於先用錯的文法驗過一遍才拒絕")

    def test_engine_assertion_exists_on_both_sides(self):
        """跨檔字面鎖：本機 smoke 與 CI 兩側的引擎斷言必須並存。

        WHY（Rule 9）：R73 的整個敘事是「CI 有牙、本機沒牙」。若日後任一側被拿掉，
        就退回單側防護而另一側靜默降級——正是本輪要消滅的形態。兩側失敗形態不同
        （本機 `exit 1`、CI `throw`）是刻意的（載具不同），故只釘「斷言存在」。
        """
        ci = _REPO_ROOT / ".github" / "workflows" / "windows-compat-ci.yml"
        ci_text = ci.read_text(encoding="utf-8", errors="replace")
        self.assertIn(
            "ENGINE-MISMATCH", ci_text,
            "CI 側的 ENGINE-MISMATCH 斷言不見了——本機側單獨存在時，"
            "CI runner 上的引擎漂移會完全無訊號")
        self.assertIn(
            "$PSVersionTable.PSVersion.Major -ne 5", ci_text,
            "CI 側引擎斷言的判準已變動，需與本機側同步核對")
        ps1_text = (_REPO_ROOT / "tools" / "windows_smoke_local.ps1").read_text(
            encoding="utf-8-sig", errors="replace")
        self.assertIn(
            "ENGINE-MISMATCH", ps1_text,
            "本機側的 ENGINE-MISMATCH 訊息不見了——兩側必須並存（DEF-101-784）")


class TestSmokeCiSync(unittest.TestCase):
    def test_onboarding_pass_claims_match_script_pins(self) -> None:
        """ONBOARDING.md 的 PASS=N 宣稱集合必須恰等於兩腳本釘選值集合。"""
        sh_pin = _extract_pin(_read(_SH), r"^MIN_PASS=(\d+)")
        ps1_pin = _extract_pin(_read(_PS1), r"^\$MinPass\s*=\s*(\d+)")
        claims = {int(v) for v in re.findall(r"(?<![A-Z_])PASS=(\d+)", _read(_ONBOARDING))}
        self.assertEqual(
            claims,
            {sh_pin, ps1_pin},
            f"ONBOARDING.md 宣稱的 smoke PASS 數字 {sorted(claims)} 與腳本釘選 "
            f"{{sh={sh_pin}, ps1={ps1_pin}}} 不一致——改釘選須同步改文件（反之亦然）",
        )

    def test_scenario_groups_consistent_and_floored(self) -> None:
        """分組標籤 [n/m]：n 連續 1..m、組數==m、組數不低於下限釘選（防 0 命中假綠）。"""
        for label, path in (("sh", _SH), ("ps1", _PS1)):
            groups = _GROUP_RE.findall(_read(path))
            floor = _MIN_GROUPS[label]
            self.assertGreaterEqual(
                len(groups), floor,
                f"{path.name} 抽取到 {len(groups)} 個分組標籤 < 下限 {floor}——"
                f"宣告 pattern 疑似漂移（靜默縮面）；刻意刪減請同步下修 _MIN_GROUPS",
            )
            declared_totals = {int(m) for _n, m in groups}
            self.assertEqual(
                declared_totals, {len(groups)},
                f"{path.name} 分組標籤宣告總數 {declared_totals} 與實際組數 "
                f"{len(groups)} 不一致（增刪分組漏改 [n/m] 分母）",
            )
            self.assertEqual(
                [int(n) for n, _m in groups], list(range(1, len(groups) + 1)),
                f"{path.name} 分組編號不連續：{[n for n, _m in groups]}",
            )

    def test_min_pass_equals_actual_step_count(self) -> None:
        """DEF-101-243①：$MinPass/MIN_PASS 釘選值本身須等於腳本實際會執行到的
        PASS 步驟數，而非只交叉比對「文件宣稱＝腳本釘選」（上方
        test_onboarding_pass_claims_match_script_pins 只鎖這一半）。QA 二審
        bug-injection 證實：只改錯釘選值本身、步驟仍在，既有測試不會變紅。

        兩腳本「原始碼字面 pass/Pass-Item 呼叫次數」與「實際執行到的步驟數」不
        直接相等：
        - macos_smoke_local.sh 有互斥分支（case/if-else 兩條路徑各呼叫一次
          pass，實際執行恰命中其一），字面數比實際數多。
        - windows_smoke_local.ps1 有共用函式（Test-InstallRoundtrip /
          Test-WorktreeReject）被呼叫多次、函式定義內只有 1 個 Pass-Item 字面
          出現，字面數比實際數少。

        通用剖析器精確歸納這兩種語意風險高（易在未來改版時悄悄算錯、製造假的
        安全感），改用顯式登記表 + fail-loud 存在性檢查（同 R19 修復包 A
        test_known_consumers_detected() 精神）：登記已知的「字面數與實際執行數
        不一致」樣式，明確列出其原始碼錨點；錨點消失（訊息被改寫/函式改名）即
        讓本測試紅，逼人工重新核算並更新登記表。
        """
        sh_text = _read(_SH)
        all_sh_msgs = _SH_PASS_RE.findall(sh_text)
        collapsed = 0
        for group in _SH_EXCLUSIVE_PASS_GROUPS:
            for msg in group:
                self.assertIn(
                    msg, all_sh_msgs,
                    f"macos_smoke_local.sh 互斥 pass 訊息錨點消失：{msg!r}——"
                    "MIN_PASS 語意登記表已腐化，需人工重新核對 _SH_EXCLUSIVE_PASS_GROUPS",
                )
            collapsed += len(group) - 1  # N 條互斥路徑實際執行只命中其一，收斂為 1
        actual_sh_steps = len(all_sh_msgs) - collapsed
        sh_pin = _extract_pin(sh_text, r"^MIN_PASS=(\d+)")
        self.assertEqual(
            actual_sh_steps, sh_pin,
            f"macos_smoke_local.sh 實際步驟數（互斥分支收斂後）={actual_sh_steps}，"
            f"與 MIN_PASS 釘選值 {sh_pin} 不一致——釘選值本身寫錯或步驟增減未同步",
        )

        ps1_text = _read(_PS1)
        all_ps1_msgs = _PS1_PASS_ITEM_RE.findall(ps1_text)
        in_shared_func_count = 0
        expanded = 0
        for func_name in _PS1_MULTI_CALL_FUNCS:
            body = _extract_ps1_function_body(ps1_text, func_name)
            body_pass_count = len(_PS1_PASS_ITEM_RE.findall(body))
            self.assertEqual(
                body_pass_count, 1,
                f"windows_smoke_local.ps1 函式 {func_name} 函式體內 Pass-Item "
                f"字面出現次數={body_pass_count}（預期恰 1）——多次呼叫語意鎖假設"
                "已被打破，需重新核對 _PS1_MULTI_CALL_FUNCS 登記表",
            )
            in_shared_func_count += 1
            call_count = len(
                re.findall(rf"^\s*{re.escape(func_name)}\b", ps1_text, re.MULTILINE)
            )
            self.assertGreaterEqual(
                call_count, 1,
                f"windows_smoke_local.ps1 找不到 {func_name} 任何呼叫點——"
                "語意鎖登記表已腐化（函式改名/移除？）",
            )
            expanded += call_count
        actual_ps1_steps = (len(all_ps1_msgs) - in_shared_func_count) + expanded
        ps1_pin = _extract_pin(ps1_text, r"^\$MinPass\s*=\s*(\d+)")
        self.assertEqual(
            actual_ps1_steps, ps1_pin,
            f"windows_smoke_local.ps1 實際步驟數（共用函式呼叫次數展開後）="
            f"{actual_ps1_steps}，與 $MinPass 釘選值 {ps1_pin} 不一致——"
            "釘選值本身寫錯或步驟增減未同步",
        )

    def test_exclusive_pass_groups_are_genuinely_branch_separated(self) -> None:
        """DEF-101-246⑤／DEF-101-247④（R19 QA 二審提案，R20 落地）：
        `_SH_EXCLUSIVE_PASS_GROUPS` 顯式登記表本身完全信任人工登記——R19 QA
        bug-injection 證實：在 macos_smoke_local.sh 插入兩個實際非互斥、但謊報
        登記進登記表的假互斥 `pass` 呼叫（連同同步竄改 MIN_PASS 與 ONBOARDING
        排除交叉訊號），test_min_pass_equals_actual_step_count 仍全綠。

        QA 提出的輕量緩解（非完整控制流解析，成本遠低於此）：斷言登記表內
        每組訊息在原始碼中的兩個錨點之間（a）存在 `else`/`;;` 其中之一的字面
        字串，且（b）行距不超過寬鬆上限——不能杜絕蓄意造假，但能擋下「兩個
        無條件執行、彼此相鄰又無分支關鍵字」這種注入手法。"""
        sh_text = _read(_SH)
        lines = sh_text.splitlines()
        msg_line: dict[str, int] = {}
        for i, line in enumerate(lines, start=1):
            m = _SH_PASS_RE.search(line)
            if m:
                msg_line.setdefault(m.group(1), i)

        separator_re = re.compile(r";;|(?<!\w)else(?!\w)")
        max_separation = 30
        for group in _SH_EXCLUSIVE_PASS_GROUPS:
            group_lines = []
            for msg in group:
                self.assertIn(
                    msg, msg_line,
                    f"macos_smoke_local.sh 找不到 pass 訊息所在行：{msg!r}——"
                    "登記表已腐化，需人工重新核對 _SH_EXCLUSIVE_PASS_GROUPS",
                )
                group_lines.append(msg_line[msg])
            group_lines.sort()
            for start, end in zip(group_lines, group_lines[1:]):
                distance = end - start
                self.assertLessEqual(
                    distance, max_separation,
                    f"macos_smoke_local.sh 互斥組兩錨點（行 {start}/{end}）行距 "
                    f"{distance} 超過寬鬆上限 {max_separation}——登記表可信度存疑，"
                    "需人工重新核對是否真的是同一組互斥分支",
                )
                # R20 四方一審 SD 訂正：`lines` 是 0-indexed、`start`/`end` 是 1-indexed
                # 行號，故 `lines[start:end]` 實際排除第一個錨點自身那一行、但包含
                # 第二個錨點自身那一行（而非原註解宣稱的「不含兩端」）——對 case 分支
                # （兩錨點緊鄰、distance=1）而言，`;;` 恰好落在第二個錨點自身的行尾，
                # 檢查因此仍然有效，但邏輯上是「第二錨點行是否含分隔符」而非真的檢查
                # 兩錨點之間；如實記錄此邊界，非本輪修復範圍（QA 已知 word-in-comment
                # 繞過亦不受此訂正影響，見 DEF-101-247④ 既有方法論邊界）。
                segment = "\n".join(lines[start:end])
                self.assertRegex(
                    segment, separator_re,
                    f"macos_smoke_local.sh 互斥組兩錨點（行 {start}~{end}）之間找不到 "
                    "`else`/`;;` 任一分支關鍵字——這兩個 pass 呼叫可能實際上是無條件"
                    "相鄰執行、被謊報登記為互斥分支（DEF-101-247④ 緩解目標情境）",
                )

    def test_sync_maintenance_comments_present(self) -> None:
        """四向同步注記仍在（防有人刪注記後兩邊靜默分道揚鑣）。"""
        checks = [
            (_SH, "macos-compat-ci.yml"), (_SH, "同步維護"),
            (_PS1, "windows-compat-ci.yml"), (_PS1, "同步維護"),
            (_MAC_CI, "macos_smoke_local.sh"), (_MAC_CI, "同步維護"),
            (_WIN_CI, "windows_smoke_local.ps1"), (_WIN_CI, "同步維護"),
        ]
        for path, needle in checks:
            self.assertIn(
                needle, _read(path),
                f"{path.name} 缺同步注記關鍵字「{needle}」——同步維護約定被刪除？",
            )

    def test_bash_n_scan_surface_matches_root_infra_ci(self) -> None:
        """R56 新增（Architect round 3 建議的治本鎖）：`root-infra-ci.yml` 第 1 道
        （bash -n）與 `macos_smoke_local.sh` [1/7] 是兩份手寫實作，兩者自述「同一份
        git ls-files 清單、同一套判準」，但此前零機械互鎖——R56 一輪之內就連續發生
        三種漂移：CI 擴面而本地沒跟上、下限釘選值訂在被凍結版稀釋的總數上、本地
        少了 CI 有的引號防護。凡「兩份硬編實作互稱鏡射」本 repo 一律建鎖（同
        test_root_infra_parity 的 CI↔pre-push 守門清單鎖），故機械斷言三件事：
          1. 兩處 `git ls-files` 的 pathspec 樣式集合逐字相同；
          2. 兩處的兩段下限釘選值（active .sh／無副檔名 git-hooks）逐字相同；
          3. 兩處都以 `sdd_version.py` SSOT 解析 LATEST 做凍結版排除（DEF-101-133：
             禁止任一方內嵌第二份版本 regex，否則 Copy-on-Evolve 建新版時兩邊分歧）。
        """
        # 三項斷言一律只看「bash -n 那一段」，不看整檔——整檔比對會被檔案別處
        # 剛好也提到同一字串的巧合滿足（bug-injection 實證：只改 [1/7] 段內的
        # `sdd_version.py`，整檔 assertIn 仍綠，因該檔 [4/7] 另有一處提及）。
        ci_text = _code_only(_region(
            _read(_ROOT_INFRA_CI), r"^ +- name: bash -n .*?(?=^ +- name: )",
            "root-infra-ci.yml 第 1 道 step",
        ))
        sh_text = _code_only(_region(
            _read(_SH), r"\[1/7\] bash -n.*?(?=# ── 建立 fake repo)",
            "macos_smoke_local.sh [1/7] 區塊",
        ))

        def _pathspec(text: str, label: str) -> list[str]:
            # 兩檔都另有 `ls-files` 的其他用途（檔頭註解提及、第 3 道 `--eol | awk`），
            # 故不取「第一個」而是取「帶 ≥4 條引號 pathspec 的那一個」，並要求唯一
            # ——第二個同形區塊出現時 fail-loud，逼人工指定要鎖哪一個。
            blocks = [
                sorted(_QUOTED_TOKEN_RE.findall(m.group(0)))
                for m in _LS_FILES_BLOCK_RE.finditer(text)
            ]
            candidates = [t for t in blocks if len(t) >= 4]
            self.assertEqual(
                len(candidates), 1,
                f"{label} 抽出帶 ≥4 條引號 pathspec 的 `git ls-files … )` 區塊有"
                f"{len(candidates)} 個（預期恰 1）——抽取 pattern 或實作疑似漂移"
                f"（實測各區塊：{blocks}）",
            )
            return candidates[0]

        self.assertEqual(
            _pathspec(ci_text, "root-infra-ci.yml"), _pathspec(sh_text, "macos_smoke_local.sh"),
            "root-infra-ci.yml 第 1 道與 macos_smoke_local.sh [1/7] 的 git ls-files "
            "pathspec 不一致——兩者自述『同一份清單』，任一方擴面/縮面必須同步",
        )

        def _floor(text: str, var: str, label: str) -> int:
            m = re.search(rf'"\${var}"\s+-lt\s+(\d+)', text)
            self.assertIsNotNone(
                m, f"{label} 抽不到 `\"${var}\" -lt N` 下限釘選——釘選被刪除或寫法漂移",
            )
            return int(m.group(1))

        self.assertEqual(
            (_floor(ci_text, "n_sh", "root-infra-ci.yml"),
             _floor(ci_text, "n_hook", "root-infra-ci.yml")),
            (_floor(sh_text, "syntax_sh", "macos_smoke_local.sh"),
             _floor(sh_text, "syntax_hook", "macos_smoke_local.sh")),
            "root-infra-ci.yml 第 1 道與 macos_smoke_local.sh [1/7] 的兩段下限釘選值"
            "不一致——現況 active .sh ≥23、無副檔名 git-hooks ≥6，刻意調整時兩處同步",
        )

        for text, label in ((ci_text, "root-infra-ci.yml"), (sh_text, "macos_smoke_local.sh")):
            # 認「`scripts/sdd_version.py` 呼叫路徑」而非裸檔名：bug-injection 實證
            # 裸檔名會被同區塊的 fail 訊息字串（「sdd_version.py 無輸出」）滿足，
            # 即實作已被拆掉仍綠燈。
            self.assertIn(
                "scripts/sdd_version.py", text,
                f"{label} 的 bash -n 掃描面未實際呼叫 scripts/sdd_version.py SSOT 解析"
                f"LATEST——凍結版排除不得內嵌第二份版本 regex（DEF-101-133）",
            )


    def test_ps1_parse_scan_surface_matches_root_infra_ci(self) -> None:
        """R56 round 5 新增（round 4 三方獨立命中同一根因）：`.ps1` parse 掃描面的
        Windows 側對稱鎖——與上一支 `test_bash_n_scan_surface_matches_root_infra_ci`
        同構。

        WHY：同一份「四棵樹 ＋ per-tree 檔數下限」硬編現存**四處**（R56 round 5 訂正：
        原寫「三處」漏數了 `tools/tests/test_ps1_bom.py::_scan_prefixes()`，該檔同輪
        已自行對 CI 建立互鎖並訂正此判定；本鎖負責其中三處，第四處由 test_ps1_bom
        自身對 CI 互鎖，四處自此全數有鎖）——
        `root-infra-ci.yml` 第 2 道（樹清單，無下限）、`test_ps51_compat.scan_trees()`
        （樹清單＋下限）、`windows_smoke_local.ps1` [1/9] 的 `$ps1Trees`（樹清單＋
        下限）。R56 本輪只鎖了前兩份互相對照，第三份零機械訊號：實測抽掉 `.ps1`
        內一整棵掃描樹（`AISDLC_SDD\\scripts`）、或把 `AutoClaude\\tools` 的 Floor
        由 7 改成 3，`python3 tools/run_root_unittests.py` 依然 `Ran 518 / OK`；
        而 macOS 側同款注入（`macos_smoke_local.sh` 下限 23→22）立刻 RED。

        該 `.ps1` 的 R56 註解**自稱**「與 root-infra-ci.yml 第 2 道同四棵樹」、
        「per-tree 檔數下限釘選…慣例對齊 test_bash32_compat.py」——自稱鏡射、零機械
        保證，正是上一支測試 docstring 立下的「凡兩份硬編實作互稱鏡射本 repo 一律
        建鎖」所指的情形。本輪 DEF-101-451 修掉 CI 層的平台不對稱後，不對稱被平移
        到「機械守門密度」這一層（該列狀態只記「實測計數與釘選值吻合」＝當下快照、
        不是回歸鎖），本測試即補上這道鎖。

        機械斷言：
          1. `.ps1` `$ps1Trees` 的樹集合 == `scan_trees()` key 集合
             == `root-infra-ci.yml` 第 2 道 `Get-ChildItem -Path <樹>` 集合；
          2. `.ps1` 每棵樹的 `Floor` == `scan_trees()` 對應下限（逐值）；
          3. `.ps1` 與 CI 兩處的 LATEST 都實際呼叫 `sdd_version.py` SSOT 解析
             （DEF-101-133：禁止任一方內嵌第二份版本 glob/regex）。
        """
        # 只看 [1/9] 區塊：整檔比對會被 [5/9] 另一處 resolver 呼叫等巧合字串滿足
        # （同上一支測試的 bug-injection 教訓）。起點錨 `[1/N]` 分母寫成 `\d+`，
        # 未來增減情境分組不會讓本鎖以「抽不到區塊」的形式假性崩掉。
        ps1_region = _code_only(_region(
            _read(_PS1), r"--- \[1/\d+\] Parser.*?(?=# ── 建立 fake repo)",
            "windows_smoke_local.ps1 [1/9] 區塊",
        ))
        ps1_trees = _ps1_scan_trees(ps1_region)
        self.assertEqual(
            len(ps1_trees), 4,
            f"windows_smoke_local.ps1 [1/9] 只抽到 {len(ps1_trees)} 棵掃描樹（預期 4）："
            f"{sorted(ps1_trees)}——整棵樹被刪，或 `@{{ Rel = …; Floor = N }}` 宣告樣式"
            "漂移導致靜默 0 命中假綠",
        )

        pinned = {key: floor for key, _files, floor in _load_ps51_module().scan_trees()}
        self.assertEqual(
            ps1_trees, pinned,
            f"windows_smoke_local.ps1 [1/9] 的掃描樹/下限 {ps1_trees} 與 "
            f"test_ps51_compat.scan_trees() 的 {pinned} 不一致——Windows 本機 smoke 是"
            "這組掃描面的第三份硬編實作，且該檔自述與另兩份同四棵樹；任一方增刪樹或"
            "調整 per-tree 下限必須同步（下限值由 scan_trees() 與 $ps1Trees 兩處持有；樹清單另含 test_ps1_bom._scan_prefixes() 共四處）",
        )

        ci_step = _code_only(_region(
            _read(_ROOT_INFRA_CI), r"^ +- name: pwsh 語法解析.*?(?=^ +- name: )",
            "root-infra-ci.yml 第 2 道 step",
        ))
        # R56 round 6 修正（QA B-1）：字元類擴充納入 `.`／`-`（原本 `.github/scripts`
        # 這類第 5 棵樹插進 CI 時本鎖完全看不到），並補抽取數量下限堵 fail-open。
        ci_trees = ci_fixed_trees(ci_step)
        self.assertEqual(
            len(ci_trees), 3,
            f"root-infra-ci.yml 第 2 道抽到 {len(ci_trees)} 棵固定樹（預期 3，LATEST 另以 Join-Path 表示）：{sorted(ci_trees)}",
        )
        # R56 round 7 修正（Architect F2 ／ QA ② 交叉發現）：上面的 `len(ci_trees)`
        # 等值斷言只對「_CI_TREE_RE 抽得到的樹」有效，對「抽不到的形態」天生零訊號
        # ——實測 `-Path "docs/scripts"`（引號界定）與 `-Path (Join-Path ".github"
        # "scripts")`（計算式，該 step 第 4 棵樹就是這種寫法、照抄最自然）插入第 5 棵
        # 樹時三支鎖全綠。故補一條**與字元類完全無關**的出現次數斷言。（round 6 宣稱
        # 「補抽取數量下限堵 fail-open」不精確——QA 實證那條下限被既有 set-equality
        # 涵蓋、是冗餘的，真正生效的只有字元類擴充。）
        # R57 訂正（A2）：round 7 原文宣稱「不論路徑長什麼樣，多一棵樹必紅」是**假
        # 宣稱**——舊錨硬綁 `-Path` 具名參數，而它是 PowerShell 位置參數可省略；實測
        # 插入 `Get-ChildItem docs/scripts -Recurse -Filter *.ps1 -File` 時三份共 20 支
        # 測試仍全綠。改錨 `-Recurse -Filter *.ps1 -File`：因尾巴不含路徑，故涵蓋
        # 具名/位置/引號/Join-Path 計算式任一種路徑寫法；但 filter 自身加引號、改用
        # -Include、三參數順序對調則抓不到（由下方 cmdlet 計數錨兜底）。
        self.assertEqual(
            ci_scan_statement_count(ci_step), EXPECTED_CI_SCAN_STATEMENTS,
            "root-infra-ci.yml 第 2 道的 `.ps1` 遞迴掃描語句數已變動（預期 4＝三棵固定樹＋LATEST 計算式樹）——本斷言涵蓋具名/位置/引號/Join-Path 任一種路徑寫法，請同步四處樹清單站點",
        )
        # R57 四方複審 ARCH-01 訂正：上一版在此寫「任何參數形態的掃描樹增刪都會命中」
        # 是假宣稱——實測 `-Filter "*.ps1"`／`-Include *.ps1`／`gci` 別名／`-Filter`
        # 寫在 `-Recurse` 前，四種形態全部逃逸，其中三種還是 R56 舊錨抓得到的＝淨退化。
        # R57 round 2 ARCH-01 再訂正：三條錨原本大小寫敏感，`get-childitem …
        # -recurse -filter *.ps1 -file` 全小寫實測全綠逃逸；SSOT 已加 re.IGNORECASE。
        # SA-R57R2-02：本檔餵的是 `_code_only()` 剝過註解的 step、另兩份餵原文，
        # 三份卻共用同一組 EXPECTED_*；現由 SSOT 內部統一剝整行註解（冪等）保證
        # 兩種輸入等值，契約由 test_ci_scan_anchors.TestInputPreprocessingContract 守住。
        self.assertEqual(
            ci_gci_call_count(ci_step), EXPECTED_CI_GCI_CALLS,
            "root-infra-ci.yml 第 2 道的 Get-ChildItem（含 gci/dir/ls 別名，皆不分大小寫）出現次數已變動（預期 4）——本斷言不解析參數，已實測涵蓋：引號 filter／-Include／參數重排／Join-Path 計算式路徑／全小寫或全大寫寫法；已實測不涵蓋（未窮舉）：[System.IO.Directory]::GetFiles、Get-Item、Resolve-Path 這三種非 Get-ChildItem 列舉途徑；整行 # 註解由 SSOT 統一剝除故不計入",
        )
        self.assertIn(
            'Join-Path "AISDLC_SDD" $latestName', ci_step,
            "root-infra-ci.yml 第 2 道未見 LATEST 樹（Join-Path AISDLC_SDD $latestName）"
            "——第 4 棵樹疑似被移除",
        )
        ci_trees.add("LATEST")
        self.assertEqual(
            ci_trees, set(ps1_trees),
            f"root-infra-ci.yml 第 2 道的掃描樹 {sorted(ci_trees)} 與 "
            f"windows_smoke_local.ps1 [1/9] 的 {sorted(ps1_trees)} 不一致——該 .ps1 "
            "自述「與 root-infra-ci.yml 第 2 道同四棵樹」，任一方擴面/縮面必須同步",
        )

        # LATEST 解析必須是「真的呼叫 resolver」：只認裸檔名會被同區塊的 fail 訊息
        # 字串滿足（`.ps1` 的 Fail-Item 訊息內就寫著 `scripts/sdd_version.py 無輸出`，
        # 實作被拆掉仍會綠——上一支測試踩過同款陷阱），故連 CLI 旗標 `--sdd-root`
        # 一起要求：內嵌第二份版本 regex 取代 resolver 時該旗標必然消失。
        for text, label in (
            (ps1_region.replace("\\", "/"), "windows_smoke_local.ps1 [1/9]"),
            (ci_step, "root-infra-ci.yml 第 2 道"),
        ):
            for needle in ("scripts/sdd_version.py", "--sdd-root"):
                self.assertIn(
                    needle, text,
                    f"{label} 未實際呼叫 SSOT resolver（缺「{needle}」）——LATEST 版"
                    "偵測不得內嵌第二份版本 glob/regex（DEF-101-133）",
                )


# --- R67-C19：compat-CI step ↔ 本地載具「覆蓋差集」登記表 ------------------------
#
# WHY 這張表必須存在（測意圖非僅行為，Rule 9）：ONBOARDING §6.1 對兩支 smoke 腳本的
# 措辭是「**本地補償對等**＝…」。R67 Scan-C 逐步比對後實測：macos-smoke 22 step 扣掉
# checkout／setup-python／PATH 三個非驗證步後為 19 個實質驗證，其中 **5 步在本地零承載**
# （bootstrap 全新建立／bootstrap 重跑／dev_start 實跑／zsh source dev_start／
# integration_gate 實跑），另有 1 步只有部分承載（真實 git commit 經 core.hooksPath 觸發
# dispatcher——本地 smoke [2/7] 只做 dispatcher 直呼，`grep -n "git commit"
# tools/macos_smoke_local.sh` 空輸出）。「對等」二字讓讀者以為本地綠燈 ≈ CI 綠燈，而
# compat-CI 已因帳務停擺多輪未真正執行 ⇒ 這是一句**會讓人停止追問**的話。
#
# 而更關鍵的是**零機械訊號**：Scan-C 在乾淨 clone 注入一個全新、本地零對等的 CI step 後，
# 8 支根層守門全部 rc=0、`run_root_unittests.py` `Ran 1139 / OK`——包含本檔在內。本檔
# docstring 自述的職責是「抽取 PASS 下限釘選值與 `--- [n/m]` 分組標籤交叉斷言」，本來就
# 不是覆蓋差集鎖。故本節補的正是那條缺口：**CI 多一步而本地沒跟上，必須當場紅**。
#
# 為何登記表住在本檔而非新開掃描器：本檔已同時讀四份檔案（兩 smoke ＋ 兩 compat-CI），
# 是同一條軸、同一份輸入；DEF-101-519 定下的折中是「不新建掃描器檔案，併進既有鎖」。
#
# 為何 ONBOARDING 不再重抄一份對照表：44 列 markdown 表格＝保證下一輪就 stale 的站點
# （正是本輪在治的病）。文件改為**指向本表**這個 live 來源，數字/名單一律不寫進散文。
#
# 值的四種形態（前三種是「有載具」，`NO-LOCAL-CARRIER`／`PARTIAL` 必須附非空理由）：
#   INFRA:            非驗證步（checkout／setup-python／PATH／裝依賴），無需本地對等
#   <載具描述>        本地確有等價執行者（smoke 組號／nightly stage／根層 unittest 檔）
#   PARTIAL:          有部分承載，但缺一段關鍵路徑——必須寫明缺什麼
#   NO-LOCAL-CARRIER: 本地零承載——必須寫明為何無法本地化
#
# 🔴🔴 **這張表的取證邊界（R67 round 2 / QA-R67-04 補上；在此之前 repo 內零揭露）**
#
# 這是一張**兩邊等寬、但取證強度不對稱**的表。R67 是零 Windows 實機的一輪，而下一位讀者
# 看到 22 + 22 兩排整齊的登記，不會知道只有一半是量出來的——那正是本 repo 一路在治的
# 「讀起來像實測結果的推論」。三段式劃界（比照本輪 `snapshot-fingerprints-win32` 整欄
# `unrecorded`、ADR-XPLAT-002 §6 逐輪覆蓋表、DEF-101-659「GNU grep 側標為推論」的既有體例）：
#
#   (a) **已實測涵蓋**＝`macos-compat-ci.yml::macos-smoke` 那半邊。每一句承載宣稱都在
#       R67 macOS 真機上實查過，且佐證就寫在該列旁（例：下方「真實 git commit」那列的
#       `grep -n "git commit" tools/macos_smoke_local.sh` 空輸出）。
#   (b) **已實測不涵蓋**＝`windows-compat-ci.yml::windows-smoke` 那半邊。它是**讀**
#       `tools/windows_smoke_local.ps1`（9 組情境）與 `AutoClaude/tools/run_local_nightly.ps1`
#       **推得**的，R67 全輪無 Windows 機器可實跑核對。**別把它讀成實測結果**；待下一個
#       Windows 輪在原生 Windows 上逐列覆核一次（該交棒項另記於帳本 DEF-101-640）。
#   (c) **本節全部機械鎖的天花板**：下方四支鎖驗的是「**每一步都被歸屬**、`NO-LOCAL-CARRIER`／
#       `PARTIAL` 附了理由、指名的載具**檔案真的存在**、指名的 smoke **組號真的存在於該
#       腳本內**」。它們**都不驗「那個載具真的做了那一步做的事」**——語意等價要嘛靠實跑
#       （兩支 smoke 皆具破壞性且分鐘級，跑在開發者機器上會覆蓋 .venv／依賴基準，正是下表
#       多筆 `NO-LOCAL-CARRIER` 的成因），要嘛靠比對散文語意（那是另一種推論，不是取證）。
#       故此處**誠實劃界而不假裝**：本節買到的是「沒人想過這一步」與「想過、決定不做，理由
#       如下」的區別，以及「登記指向的東西還在」；買不到的是語意等價。
#
#   (d) **本輪把 (c) 的天花板往上頂了半階**：載具寫成 `nightly:<token>@<腳本相對路徑>` 者，
#       `TestNightlyCarrierReferencesResolve` 會要求 `<token>` **真的在該腳本內抓得到**。
#       WHY 非上不可：本輪在原生 Windows 上逐列覆核 Windows 半張表時，實測抓到**兩筆假
#       登記**——被指名的 `AutoClaude/tools/run_local_nightly.ps1` 自己的檔頭逐字否認它跑
#       那兩件事（`run_root_unittests` 與 `ci-gate` 兩個字樣在該檔全檔命中 0）。舊守門只驗
#       「檔案存在」，而那支腳本當然存在 ⇒ 這張表可以說謊而零訊號。`<token>` 必須挑「那一
#       步真的被做了」的**字面證據**（被呼叫的檔名／stage 函式名），不是好聽的 stage 別名：
#       別名只證明有人取過名字，證明不了那件事被做了。
#       兩筆的處置：一筆因本輪另一個修復包已把根層 unittest 掛進該檔而**轉為真**（token 改
#       成該呼叫的檔名，它若被撤回本鎖當場紅）；另一筆改判為零本機承載並寫明理由。
#       仍未買到的：token 命中證明「該檔提到／呼叫了它」，不證明「跑的範圍與 CI 那一步相同」。
_NO_CARRIER = "NO-LOCAL-CARRIER"
_PARTIAL = "PARTIAL"
_INFRA = "INFRA"

_CI_STEP_LOCAL_CARRIER: dict[str, dict[str, str]] = {
    "macos-compat-ci.yml::macos-smoke": {
        "uses:actions/checkout": f"{_INFRA}: 取原始碼",
        "Set up Python 3.11": f"{_INFRA}: 準備直譯器",
        "將 .venv/bin 加入 PATH（比照本機開發慣例，供後續步驟裸呼叫 python）": f"{_INFRA}: 環境設定，非驗證步",
        "tools/tests 第三方相依（清單 SSOT＝tools/run_root_unittests.py 的 _THIRD_PARTY_PREREQS；漏裝時該 runner 會 fail-fast 指路）": (
            f"{_INFRA}: 環境設定，非驗證步——本機開發 .venv 早已具備這些相依，"
            "故無需對應載具；「CI 有沒有裝」這件事本身由 "
            "tools/tests/test_run_root_unittests.py::CiPrereqInstallLockTest 機械看守"
        ),
        # key 刻意折行（隱式字串串接）：本檔 `tools/tests/` 的 E501 存量債走 shrink-only
        # 棘輪（test_subprocess_encoding_hygiene.TestRootToolsLintPolicy），新寫的行不得
        # 加高天花板——舊 key 的過長是存量債，不是可照抄的體例。
        (
            "tools/tests 外部工具相依（清單 SSOT＝tools/tests/test_run_root_unittests.py 的 "
            "_EXTERNAL_TOOL_PREREQS；runner 無此層 fail-fast，漏裝時由 "
            "ExternalToolPrereqDeclarationTest 多紅一支點名）"
        ): (
            f"{_INFRA}: 環境設定，非驗證步——本機開發 .venv 早已具備 ruff（pre-push 快層"
            "第 ④ 段本來就要求它），故無需對應載具；「CI 有沒有裝」由 "
            "tools/tests/test_run_root_unittests.py::CiPrereqInstallLockTest::"
            "test_every_ci_job_running_the_runner_installs_all_external_tools 機械看守"
        ),
        "tools/tests/（SIGPIPE 回歸鎖 + dev_start.py 平台邏輯；R3 QA 發現：paths 雖已涵蓋 tools/tests/**，但先前從未有任何 step 真的執行過，只在 root-infra-ci.yml 的 ubuntu-latest 上以 mock 跑過）": "nightly:run_root_unittests.py@AutoClaude/tools/run_local_nightly.sh（stage 2 root_unittests）＋ pre-push root-infra leg",
        "install_mac_nightly.sh --render-only（plist 產出＋plutil -lint；鏡射本機 smoke [6]，QA-R13-3 補齊四向互鎖缺角）": "macos_smoke_local.sh [6/7]",
        "執行 tools/bootstrap.sh（全新 .venv 建立情境）": (
            f"{_NO_CARRIER}: 需在乾淨 checkout 上建立**全新** .venv；在開發者機器上跑會覆蓋"
            "現用 .venv 並重裝全部依賴（分鐘級且破壞性），本地 smoke 刻意不做"
        ),
        "重跑 tools/bootstrap.sh（既有 .venv 沿用情境）": (
            f"{_NO_CARRIER}: 同上，且此步的驗證對象是「既有 .venv 沿用」路徑，"
            "必須緊接在前一步的乾淨建立之後才有意義"
        ),
        "執行 tools/dev_start.sh（一般 checkout 情境，首次記錄依賴基準）": (
            f"{_NO_CARRIER}: 會改寫本機依賴基準狀態檔與 .venv；平台分支邏輯本身由 "
            "tools/tests/test_dev_start.py 單元測試覆蓋，但「殼實跑」這一段無本地載具"
        ),
        "觸發 tools/dev_start.py 的 cross_same_flavor 分支（linux→mac，僅 macOS runner 可測）": "tools/tests/test_dev_start.py（step_venv cross_same_flavor 分支）",
        "zsh source tools/dev_start.sh（macOS 預設 shell 的 source 路徑；R9 Fix-E）": (
            f"{_NO_CARRIER}: 需以 macOS 預設 shell zsh source 該殼並觀察其副作用，"
            "與上一步同樣具破壞性（R9 Fix-E）"
        ),
        "AutoClaude/tools/install_git_hooks.sh 安裝／解除往返驗證（一般 checkout）": "macos_smoke_local.sh [3/7]",
        "AutoClaude/tools/install_git_hooks.sh 於 linked worktree 下應正確拒絕（fail-loud）": "macos_smoke_local.sh [3/7]",
        "AISDLC_SDD/scripts/install-hooks.sh 安裝／解除往返驗證（一般 checkout）": "macos_smoke_local.sh [3/7]",
        "AISDLC_SDD/scripts/install-hooks.sh 於 linked worktree 下應正確拒絕（fail-loud）": "macos_smoke_local.sh [3/7]",
        "根層 dispatcher hooks：安裝 + 真實 git commit 觸發 pre-commit（經 core.hooksPath）": (
            f"{_PARTIAL}: macos_smoke_local.sh [2/7] 只做 dispatcher **直呼**；"
            "「經 core.hooksPath 由真實 git commit 觸發」這一段本地零覆蓋"
            "（`grep -n \"git commit\" tools/macos_smoke_local.sh` 空輸出）"
        ),
        "根層 dispatcher hooks：/bin/bash（系統 bash 3.2，非 Homebrew 新版）直接執行驗證": "macos_smoke_local.sh [2/7]",
        "AISDLC_SDD LATEST/tools/install_hooks/install_post_commit.sh 於 worktree 執行，驗證寫入共用 .git/hooks/post-commit": "macos_smoke_local.sh [4/7]",
        "pty_wrapper / hotkey_handler 平台解析單元測試（AutoClaude tests/test_perception.py）": "nightly stage 3 autoclaude_gate（AutoClaude 全套 pytest 含 AutoClaude/tests/test_perception.py）",
        # R76-11 新增（兩平台對稱）。key 折行理由同上（E501 shrink-only 棘輪）。
        (
            "AutoClaude 平台敏感測試子集（R76-11：push 閘門對 AutoClaude 生產樹"
            "此前零執行證據）"
        ): (
            "nightly stage 3 autoclaude_gate（AutoClaude 全套 pytest，是本步驟所選"
            "子集的**超集**）；本步驟買的不是新斷言，是「同一批斷言在真 macOS runner "
            "上、每次 push 都跑一次」——本地載具跑的是開發者自己那台機器"
        ),
        "執行 tools/integration_gate.sh --skip-full（實際執行，非僅語法解析；R34 Scan-C 發現修正）": (
            f"{_NO_CARRIER}: 全 repo 零自動呼叫端（R67-C19 實查：所有命中皆為文件／parity "
            "登記／薄殼守門，無任何本地流程執行它）"
        ),
        "執行（非僅解析）AISDLC_SDD/scripts/ci-gate.sh（凍結基線 v0.01 + LATEST 雙軌）":
            "nightly:sdd_gate@AutoClaude/tools/run_local_nightly.sh（stage 4 sdd_ci_gate）",
        "tools/check_script_parity.py（雙平台腳本對等 + pytest 釘選一致）": "macos_smoke_local.sh [5/7]",
        "tools/check_ntfs_paths.py（NTFS 敵意檔名，全量 tracked 路徑）": "macos_smoke_local.sh [5/7]",
    },
    "windows-compat-ci.yml::windows-smoke": {
        "uses:actions/checkout": f"{_INFRA}: 取原始碼",
        "Set up Python 3.11": f"{_INFRA}: 準備直譯器",
        "Install AutoClaude deps": f"{_INFRA}: 裝依賴，非驗證步",
        "安裝 AISDLC_SDD pinned deps": f"{_INFRA}: 裝依賴，非驗證步",
        # key 折行理由同上（E501 shrink-only 棘輪）。
        (
            "Windows PowerShell 5.1 核心驗證（Get-PythonGeMin 開箱可解析；DEF-101-760 "
            "症狀級迴歸鎖，以文件教學引擎執行）"
        ): (
            f"{_PARTIAL}: tools/tests/test_ps51_compat.py::TestPs51NativeArgvRoundTrip"
            "（pre-push root-infra leg 經 tools/run_root_unittests.py 帶到，在 Windows "
            "真機上以原生 powershell.exe 實跑）。**缺的那一段**：本地那支驗的是"
            "**代理指標**——探測碼字串交給原生 exe 後有沒有被改寫；CI 這一步驗的是"
            "**症狀本身**——`Get-PythonGeMin` 真的挑得到直譯器。任何非「引號被吃掉」"
            "成因的 $null（DEF-101-759 pyenv shim／DEF-101-766 PATHEXT 全淘汰）只有 CI "
            "這一步逮得到。刻意不把它搬進 pre-push：那會讓每次 push 多跑一次 guard 探測，"
            "而 pre-push 已是本 repo 最重的閘門，換到的覆蓋則與既有代理指標高度重疊"
        ),
        "tools/tests 第三方相依（清單 SSOT＝tools/run_root_unittests.py 的 _THIRD_PARTY_PREREQS；漏裝時該 runner 會 fail-fast 指路）": (
            f"{_INFRA}: 裝依賴，非驗證步——本機開發環境早已具備這些相依；"
            "「CI 有沒有裝」由 tools/tests/test_run_root_unittests.py::"
            "CiPrereqInstallLockTest 機械看守"
        ),
        # key 折行理由同 macOS 側（E501 shrink-only 棘輪，新行不得加高天花板）。
        (
            "tools/tests 外部工具相依（清單 SSOT＝tools/tests/test_run_root_unittests.py 的 "
            "_EXTERNAL_TOOL_PREREQS；runner 無此層 fail-fast，漏裝時由 "
            "ExternalToolPrereqDeclarationTest 多紅一支點名）"
        ): (
            f"{_INFRA}: 裝依賴，非驗證步——本機開發環境早已具備 ruff（pre-push 快層"
            "第 ④ 段本來就要求它）；「CI 有沒有裝」由 "
            "tools/tests/test_run_root_unittests.py::CiPrereqInstallLockTest::"
            "test_every_ci_job_running_the_runner_installs_all_external_tools 機械看守"
        ),
        "tools/tests/（SIGPIPE 回歸鎖 + dev_start.py 平台邏輯；R3 QA 發現：先前只在 root-infra-ci.yml 的 ubuntu-latest 上以 mock 跑過，從未在真實 Windows 執行過）": "nightly:run_root_unittests.py@AutoClaude/tools/run_local_nightly.ps1（掛在 local-ci-gate stage 內的第二道檢查）＋ pre-push root-infra leg",
        "install_windows_nightly.ps1 -WhatIf 預覽（R26 Scan-C 發現：從未在真實 CI 執行過；鏡射 macos-compat-ci.yml install_mac_nightly.sh --render-only 步驟，DEF-101-269）": "windows_smoke_local.ps1 [9/9]",
        "執行 tools/bootstrap.ps1（R1 SA 發現：Windows 新人上手入口從未被實測）": f"{_NO_CARRIER}: 同 macOS 側——需乾淨 checkout 建全新 .venv，破壞性且分鐘級",
        "重跑 tools/bootstrap.ps1（既有 .venv 沿用情境；R9 Fix-D）": f"{_NO_CARRIER}: 同上，驗證對象是「既有 .venv 沿用」路徑",
        "dot-source tools/dev_start.ps1（同上，日常開工入口）": f"{_NO_CARRIER}: 會改寫本機依賴基準狀態與 .venv（同 macOS 側 dev_start 實跑）",
        "觸發 tools/dev_start.py 的 .venv 形狀換手分支（posix→windows，僅 Windows runner 可測）": "tools/tests/test_dev_start.py（posix→windows 形狀換手分支）",
        "pty_wrapper / hotkey_handler 平台解析單元測試": "nightly autoclaude gate（AutoClaude 全套 pytest）",
        # R76-11 新增（兩平台對稱）。key 折行理由同上（E501 shrink-only 棘輪）。
        (
            "AutoClaude 平台敏感測試子集（R76-11：push 閘門對 AutoClaude 生產樹"
            "此前零執行證據）"
        ): (
            "nightly autoclaude gate（AutoClaude 全套 pytest，是本步驟所選子集的"
            "**超集**）；本步驟買的不是新斷言，是「同一批斷言在真 Windows runner 上、"
            "每次 push 都跑一次」——本地載具跑的是開發者自己那台機器"
        ),
        "執行 tools/integration_gate.ps1 -SkipFull（實際執行，非僅語法解析；P1 Architect 發現修正）": f"{_NO_CARRIER}: 同 macOS 側——integration_gate 全 repo 零自動呼叫端",
        "執行（非僅解析）ci-gate.ps1（凍結基線 + LATEST 雙軌）": (
            f"{_NO_CARRIER}: Windows 側零通道（本輪原生 Windows 實查）——"
            "run_local_nightly.ps1 內唯一的 SDD stage 是 sdd-fsm-chaos"
            "（chaos 子集），不含雙軌 pytest 與 10 道 lint 硬閘；"
            "該檔檔頭自述此項「仍是缺口，本輪未補」。"
            "act 也補不到：本 job runs-on=windows-latest，"
            "見下方 _ACT_NO_LOCAL_RUNNER_JOBS。"
            "手動出口＝在 AISDLC_SDD 下直接跑 scripts/ci-gate.ps1"
        ),
        "install_git_hooks.ps1 安裝／解除往返驗證": "windows_smoke_local.ps1 [2/9]",
        "GitHooksInstallCommon.ps1 Assert-NotLinkedWorktree 於 linked worktree 下應正確拒絕（fail-loud；獨立複審發現：macOS 側已測、Windows 側零覆蓋 P0）": "windows_smoke_local.ps1 [3/9]＋[7/9]",
        "AISDLC_SDD/scripts/install-hooks.ps1 驗證（R1 SA 發現：第二入口從未被測到）": "windows_smoke_local.ps1 [4/9]",
        "AISDLC_SDD/scripts/install-hooks.ps1 於 linked worktree 下應正確拒絕（fail-loud；同上，第二入口同樣零覆蓋）": "windows_smoke_local.ps1 [4/9]",
        "根層 dispatcher hooks：安裝 + 真實 git commit 經 core.hooksPath 觸發 dispatcher（R9 ARCH-F3）": (
            f"{_NO_CARRIER}: windows_smoke_local.ps1 九組情境內**沒有** dispatcher 組"
            "（macOS 側至少有 [2/7] 的直呼，Windows 側連直呼都沒有）⇒ 本地零覆蓋"
        ),
        "install_post_commit.ps1 執行 + 非 ASCII 路徑編碼損毀斷言（P1 回歸鎖，R1 SD 發現修正；R2 SD/Architect 發現再修正；2026-07-16 R8 SD 發現 linked-worktree 路徑解析 bug 修復後再修正）": "windows_smoke_local.ps1 [5/9]＋[6/9]",
        "install_post_commit.ps1 於 linked worktree 移除後仍應解析出有效路徑（P1 回歸鎖，2026-07-16 四方複審 SD 發現）": "windows_smoke_local.ps1 [5/9]",
        "tools/check_script_parity.py（雙平台腳本對等 + pytest 釘選一致；R4 複審發現：先前僅 macOS 側涵蓋）": "windows_smoke_local.ps1 [8/9]",
        "tools/check_ntfs_paths.py（NTFS 敵意檔名，全量 tracked 路徑；R4 複審發現：本工具本質為 Windows/NTFS 相容性檢查，先前卻只在 macOS/Linux 上被驗證過，從未在真正的目標平台 Windows 上跑過）": "windows_smoke_local.ps1 [8/9]",
    },
}

# 抽取數量下限釘選（比照 `_MIN_GROUPS`／`check_script_parity._MIN_EXTRACT_COUNTS` 慣例）：
# 防「step 抽取式漂移導致 0 命中，於是包含關係恆成立而靜默假綠」。
_MIN_CI_STEPS = 20

# 一個 step 起始行：`      - name: …` / `      - uses: …`（steps 清單縮排 6 空格）。
_CI_STEP_START_RE = re.compile(r"^      - (\w+): (.*)$", re.MULTILINE)


def _ci_step_key(kind: str, value: str) -> str:
    """step 起始行 → 登記表鍵。

    `name:` 取**整串名稱**（僅正規化連續空白）。刻意**不**截到第一個括號之前：實測那樣
    做會把「執行（非僅解析）AISDLC_SDD/scripts/ci-gate.sh…」壓成無資訊的 `執行`，而
    Windows 側另有一步也壓成 `執行` ⇒ 鍵撞在一起、登記表無法逐一對應。代價明說：**純
    改寫 step name 的括號註記也會讓本鎖紅**——這與本檔既有的 `_SH_EXCLUSIVE_PASS_GROUPS`
    採逐字訊息登記是同一慣例，且「name 變了就重新確認它的本地承載」本來就該是人工動作。
    `uses:` 去掉 `@版本`：版本釘選由 `check_gha_action_versions.py` 另行守門，不重複；
    版本升級是常態，讓它連帶紅這張表沒有意義。
    """
    if kind == "uses":
        return "uses:" + value.strip().split("@")[0]
    return " ".join(value.split())


def _ci_smoke_steps(path: Path, job: str) -> dict[str, str]:
    """compat-CI 某 job 的 {step 鍵: step 起始行原文}；重複鍵即 fail-loud。"""
    text = _read(path)
    m = re.search(rf"^  {re.escape(job)}:\s*$(.*?)(?=^  \S|\Z)", text, re.MULTILINE | re.DOTALL)
    if m is None:
        raise AssertionError(f"{path.name} 找不到 job `{job}`——job 改名或結構變動")
    steps: dict[str, str] = {}
    for kind, value in _CI_STEP_START_RE.findall(m.group(1)):
        key = _ci_step_key(kind, value)
        if key in steps:
            raise AssertionError(
                f"{path.name}::{job} 出現重複 step 鍵 {key!r}——兩個 step 的主詞相同會讓"
                "覆蓋差集登記表無法逐一對應，請讓 step name 的主詞可區分"
            )
        steps[key] = f"{kind}: {value}"
    return steps


class TestCiStepLocalCarrierCoverage(unittest.TestCase):
    """R67-C19：compat-CI 的每一個 smoke step 都必須在登記表裡有明確的本地承載歸屬。

    這道鎖要擋的**具體失敗**：有人在 compat-CI 加一個新驗證步（例如新平台守門），本地
    smoke／nightly 完全沒跟上，而 compat-CI 因帳務停擺不會執行 ⇒ 那一步實際上**從未在
    任何地方跑過**，卻讓 §6.1 的「本地補償」措辭看起來仍成立。Scan-C 已實測注入證明此
    情境下 56 支護欄測試（含本檔）全綠、零訊號。

    刻意**不**斷言「零本地承載的步數必須是 N」：寫死支數＝下一輪必過期（R57 已立政策）。
    本鎖只要求「每一步都被明確歸屬，且無承載者必須寫明為何」——把「沒人想過這一步」與
    「想過、決定不做，理由如下」區分開來，是這張表唯一要買的東西。
    """

    def test_every_ci_step_is_registered(self) -> None:
        """新增 CI step 而未登記本地承載 ⇒ 紅（本鎖的正職，Scan-C 注入 D 的直接對策）。"""
        for spec, registry in _CI_STEP_LOCAL_CARRIER.items():
            filename, job = spec.split("::")
            steps = _ci_smoke_steps(_REPO_ROOT / ".github" / "workflows" / filename, job)
            self.assertGreaterEqual(
                len(steps), _MIN_CI_STEPS,
                f"{spec} 只抽到 {len(steps)} 個 step < 下限 {_MIN_CI_STEPS}——step 抽取式"
                f"疑似漂移（0 命中會讓下方包含關係恆成立而靜默假綠）",
            )
            missing = sorted(set(steps) - set(registry))
            self.assertEqual(
                missing, [],
                f"{spec} 有 CI step 未登記本地承載：{missing}\n"
                f"  處置：在 tools/tests/test_smoke_ci_sync.py 的 `_CI_STEP_LOCAL_CARRIER` "
                f"為每一步補上載具；本地確實無法承載者寫 `{_NO_CARRIER}: <為何無法本地化>`。\n"
                f"  這一步不是形式——ONBOARDING §6.1 對外宣稱本地 smoke 是 compat-CI 的"
                f"「本地補償」，而 compat-CI 因帳務停擺多輪未真正執行；沒登記＝沒人想過"
                f"這一步在本地由誰跑。\n  原文：{[steps[k] for k in missing]}",
            )

    def test_registry_has_no_stale_entries(self) -> None:
        """登記表反向自檢：登記了 CI 裡已不存在的 step ⇒ 紅（豁免表自己也會 stale）。"""
        for spec, registry in _CI_STEP_LOCAL_CARRIER.items():
            filename, job = spec.split("::")
            steps = _ci_smoke_steps(_REPO_ROOT / ".github" / "workflows" / filename, job)
            dead = sorted(set(registry) - set(steps))
            self.assertEqual(
                dead, [],
                f"{spec} 的登記表有 CI 裡已不存在的 step：{dead}——step 被刪除或改名後"
                f"沒人回收登記，這張表就開始說謊（同 `Spec.historical` 的 stale 自檢紀律）",
            )

    def test_no_carrier_and_partial_entries_carry_a_reason(self) -> None:
        """`NO-LOCAL-CARRIER`／`PARTIAL` 必須附非空理由——否則只是把「不知道」寫得像結論。"""
        for spec, registry in _CI_STEP_LOCAL_CARRIER.items():
            for step, carrier in registry.items():
                self.assertTrue(carrier.strip(), f"{spec}::{step} 載具欄為空")
                for marker in (_NO_CARRIER, _PARTIAL, _INFRA):
                    if carrier.startswith(marker):
                        reason = carrier[len(marker):].lstrip(": ：").strip()
                        self.assertTrue(
                            reason,
                            f"{spec}::{step} 標了 {marker} 卻沒寫理由——"
                            f"「想過、決定不做，理由如下」與「沒人想過」的差別就在這一句",
                        )

    def test_registry_discloses_its_evidentiary_boundary(self) -> None:
        """三段式取證邊界必須留在 repo 內（R67 round 2 / QA-R67-04）。

        WHY 這也要上鎖：R67 之前，「windows-smoke 那半張表是零 Windows 實機的讀碼推論」
        與「這些鎖只驗載具存在、不驗它真的做了那件事」兩項限制**只存在於當輪的修復回報
        JSON 裡**，repo 內 `grep` 零命中。下一輪的讀者只看得到一張兩邊等寬的表，會把推論
        讀成實測——而本輪各處（`snapshot-fingerprints-win32` 整欄 `unrecorded`、
        ADR-XPLAT-002 §6 逐輪覆蓋表、DEF-101-659）都已逐項標示推論／實測，體例是存在的，
        只有這裡漏了。註解被刪掉就會退回零揭露，故機械守住它還在。

        🔴 **判定範圍刻意只取登記表之前那段註解**，不是整檔 `in src`：本測試自己的 marker
        清單就寫著那幾個詞，整檔比對會被**自己**滿足而恆真——那正是本輪三度踩到的「換上的
        驗證自己也是假驗證」。實測佐證：整檔版在「把註解裡的字樣改掉」的注入下仍 rc=0
        （自我滿足），改成本段切片後同一注入 rc=1。**第二次踩到同一形態**：改成「登記表
        之前的全部原始碼」仍 rc=0——本檔第 638 行另一支測試的失敗訊息裡剛好也寫著「已實測
        涵蓋／已實測不涵蓋」（那是 Get-ChildItem 列舉途徑的邊界說明，與本表無關）。故切片
        **兩端都要錨**：只取取證邊界那一段註解本身。
        """
        src = Path(__file__).read_text(encoding="utf-8")
        head = "這張表的取證邊界"
        self.assertIn(head, src, "取證邊界註解區段的起始錨已不存在（整段被刪？）")
        start, end = src.index(head), src.index('_NO_CARRIER = "NO-LOCAL-CARRIER"')
        # 整段被刪時 `.index` 會退而命中本測試自己這行字面 ⇒ start > end，於是這條紅
        # （不是靜默取到一段空/錯的區間；同「載具自身也要被驗證」紀律）。
        self.assertLess(start, end, "取證邊界註解不在登記表之前——整段疑似已被刪除")
        boundary_section = src[start:end]
        self.assertGreater(
            len(boundary_section), 500,
            "取證邊界註解區段幾乎為空——切片錨點失效時本鎖會退化為恆真",
        )
        for marker in ("已實測涵蓋", "已實測不涵蓋", "天花板", "無 Windows 機器可實跑核對"):
            self.assertIn(
                marker, boundary_section,
                f"`_CI_STEP_LOCAL_CARRIER` 的取證邊界段落缺「{marker}」——"
                f"這張表會退回「兩邊等寬、取證強度不對稱卻零揭露」的狀態（QA-R67-04）",
            )

    def test_registered_smoke_groups_exist_in_that_script(self) -> None:
        """比「檔案存在」強一階：登記成 `<smoke 腳本> [n/m]` 者，該組號必須真的在那支腳本裡。

        WHY（R67 round 2 / QA-R67-04）：`test_named_local_carriers_actually_exist` 只驗
        「檔名存在」——smoke 腳本本身幾乎不可能被刪，所以那條鎖在實務上**接近恆真**；而真正
        會發生的腐化是「情境分組被重新編號／被刪掉一組」，此時檔案還在、登記卻已指向不存在
        的組號，這張表就開始說謊而無人知曉。本鎖把判準往前推到組號層級（`[3/7]` 這種標籤
        本來就是腳本自己 echo 出來的字面，`_GROUP_RE` 已在本檔他處消費同一來源）。

        **仍未買到的**（誠實劃界，見上方 `_CI_STEP_LOCAL_CARRIER` 邊界 (c)）：本鎖不驗
        「[3/7] 那一組做的事＝該 CI step 做的事」。語意等價要嘛實跑（破壞性、分鐘級），
        要嘛比對散文（另一種推論）——兩者都不是本鎖能誠實宣稱的東西。
        """
        # 歸屬**不靠文字鄰近**（實測會歸錯：windows 側某筆 NO-LOCAL-CARRIER 理由句在提到
        # `windows_smoke_local.ps1` 之後又引用 macOS 的 `[2/7]` 作對照），改由**分母**判定
        # ——每支腳本的分組總數就是它自己的身分證（sh=7、ps1=9），且這份對照表是**當場從
        # 腳本重算**的，不是寫死：任何一支重新編組（7→8）會讓全部舊引用的分母查無此腳本而
        # 當場紅，正是本鎖要抓的腐化。
        script_groups = {
            name: set(_GROUP_RE.findall(_read(path)))
            for name, path in (("macos_smoke_local.sh", _SH), ("windows_smoke_local.ps1", _PS1))
        }
        by_total: dict[str, str] = {}
        for name, groups in script_groups.items():
            totals = {total for _n, total in groups}
            self.assertEqual(
                len(totals), 1, f"{name} 的 `--- [n/m]` 分母不一致：{sorted(totals)}——分組宣告已壞"
            )
            total = totals.pop()
            self.assertNotIn(
                total, by_total,
                f"{name} 與 {by_total.get(total)} 的分組總數同為 {total} ⇒ 組號引用無法歸屬"
                f"到唯一腳本；請改回不同分組數，或改寫本鎖的歸屬判準",
            )
            by_total[total] = name
        carrier_group_re = re.compile(r"\[(\d+)/(\d+)\]")
        checked = 0
        for spec, registry in _CI_STEP_LOCAL_CARRIER.items():
            for step, carrier in registry.items():
                for group in carrier_group_re.findall(carrier):
                    n, total = group
                    checked += 1
                    self.assertIn(
                        total, by_total,
                        f"{spec}::{step} 引用的分組 [{n}/{total}] 分母不屬於任何 smoke 腳本"
                        f"（現有：{ {k: v for k, v in by_total.items()} }）——腳本重新編組後"
                        f"登記未同步，這張表已開始說謊",
                    )
                    script = by_total[total]
                    self.assertIn(
                        group, script_groups[script],
                        f"{spec}::{step} 引用的 {script} [{n}/{total}] 在該腳本內不存在"
                        f"（該腳本現有分組：{sorted(script_groups[script])}）",
                    )
        self.assertGreaterEqual(
            checked, 15,
            f"只驗到 {checked} 筆組號引用——登記表寫法或抽取式疑似漂移（0 命中會讓本鎖恆真）",
        )

    def test_named_local_carriers_actually_exist(self) -> None:
        """指名的本地載具檔案必須真的存在——指向已刪除的腳本＝紙上承載。

        ⚠️ **本鎖的天花板**（R67 round 2 / QA-R67-04；在此之前只寫在修復回報 JSON 裡、
        repo 內零揭露）：它只保證「被指名的檔案還在」，**不保證那個檔案真的執行了那一步**。
        組號層級的較強判準見上一支 `test_registered_smoke_groups_exist_in_that_script`；
        語意等價則刻意不宣稱，理由見 `_CI_STEP_LOCAL_CARRIER` 上方的邊界 (c)。
        """
        carriers = {
            carrier
            for registry in _CI_STEP_LOCAL_CARRIER.values()
            for carrier in registry.values()
            if not carrier.startswith((_NO_CARRIER, _PARTIAL, _INFRA))
        }
        referenced = {
            path
            for carrier in carriers
            for path in re.findall(r"[\w./\\-]+\.(?:sh|ps1|py)", carrier)
        }
        self.assertGreaterEqual(len(referenced), 4, f"抽到的載具檔案過少：{sorted(referenced)}")
        for rel in sorted(referenced):
            candidates = [_REPO_ROOT / rel, _REPO_ROOT / "tools" / rel]
            self.assertTrue(
                any(p.exists() for p in candidates),
                f"登記表指名的本地載具 {rel} 不存在——載具被刪除/改名後登記未同步",
            )

    def test_onboarding_does_not_claim_full_equivalence(self) -> None:
        """§6.1 不得再宣稱兩支 smoke 與 compat-CI「對等」。

        WHY 鎖措辭而非數字：Scan-C 量到的差集是 5/19 零承載 ＋ 1 部分承載，但**寫死支數
        ＝下一輪必過期**（R57 政策）。真正會誤導讀者的是「對等」這個絕對詞——它讓人以為
        本地綠燈 ≈ CI 綠燈，於是停止追問差集。措辭改掉、差集指向本檔登記表這個 live 來源。
        """
        text = _read(_ONBOARDING)
        for smoke in ("windows_smoke_local.ps1", "macos_smoke_local.sh"):
            lines = [ln for ln in text.split("\n") if smoke in ln and "compat-ci" in ln.lower()]
            self.assertTrue(lines, f"ONBOARDING §6.1 找不到 {smoke} 的 compat-CI 對照列")
            for line in lines:
                self.assertNotIn(
                    "本地補償對等", line,
                    f"ONBOARDING §6.1 仍宣稱 {smoke} 與 compat-CI「本地補償對等」——"
                    f"實測有步驟在本地零承載（見 `_CI_STEP_LOCAL_CARRIER` 內標 "
                    f"{_NO_CARRIER} 者），「對等」會讓讀者停止追問差集",
                )
        self.assertIn(
            "_CI_STEP_LOCAL_CARRIER", text,
            "ONBOARDING 未指向覆蓋差集的 live 來源——若只改措辭而不給出差集在哪，"
            "讀者只會得到一句更模糊的話",
        )


if __name__ == "__main__":
    unittest.main()


class TestMacSmokeCliContract(unittest.TestCase):
    """R69（DEF-101-702／R68-19＋R68-21）：`macos_smoke_local.sh` 的兩道入口守門。

    WHY 這兩件事住同一支測試：它們是同一個病灶的兩面——**這支腳本先前對「怎麼被呼叫」
    完全沒有意見**。① 任何打錯的旗標（例如把 `--help` 敲成 `--hlep`）都被靜默丟棄、整套
    smoke 照跑完再印綠；② 以 macOS 預設的 zsh 執行時 `${BASH_SOURCE[0]}` 未定義，腳本
    目錄解到呼叫端 cwd，guard source 失敗後 `is_real_python_candidate` 變成 command not
    found，於是印出**與事實相反**的「找不到 python」——使用者被指去裝一個早就裝好的東西。

    兩者都以「真的把腳本跑起來」驗證，不做字面比對：字面比對驗不到 rc，也驗不到
    「整套 smoke 有沒有真的被跳過」。
    """

    def _run(self, argv: list[str], shell: str | None = None) -> subprocess.CompletedProcess[str]:
        """以**真正的 bash**（`shell=None` 時）跑受測腳本。

        🔴 R69 後續（DEF-101-753）：本方法原本寫死 `shell: str = "bash"`，把**裸名**
        交給 `subprocess`。Windows 上這條路必敗——`CreateProcess` 解析裸名時把
        `System32` 排在 PATH **之前**，於是 `C:\\Windows\\System32\\bash.exe`
        （WSL 啟動器）必定先命中，無發行版時以 UTF-16LE 印
        `Windows Subsystem for Linux has no installed distributions.` 並 `exit 1`。
        受測腳本**一行都沒被執行**，本組三支卻據此斷言「腳本回了非預期 rc」——
        雲端 windows-compat-ci 上是三筆歸因完全錯誤的紅燈（本機 macOS 全綠、
        R69 四輪四方複審亦未發現）。改走 `_platform_helpers.usable_bash_for_fixture()`
        單一真相源（回傳**絕對路徑**：git 相鄰優先 + System32 整段排除 + coreutils
        驗活；完整機制與同輪對照組取證見該函式 docstring）。
        """
        exe = shell or _BASH
        if exe is None:
            self.skipTest(
                "本機探不到可用的 bash（候選皆未通過驗活）——本組刻意真跑腳本驗 rc，"
                "無 bash 時跳過而非降級成字面比對（字面比對驗不到 rc）"
            )
        return subprocess.run(
            [exe, str(_SH), *argv], cwd=str(_REPO_ROOT),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )

    def test_help_prints_usage_and_exits_zero(self) -> None:
        for flag in ("-h", "--help"):
            with self.subTest(flag=flag):
                proc = self._run([flag])
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("用法：bash tools/macos_smoke_local.sh", proc.stderr + proc.stdout)
                self.assertNotIn("[1/", proc.stdout, "印用法時不得開始跑 smoke 步驟")

    def test_unknown_flag_is_rejected_loudly(self) -> None:
        """修前：未知旗標被丟掉、整套照跑並印綠 ⇒ 使用者以為自己下的旗標生效了。"""
        proc = self._run(["--fulll"])
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("未知旗標", proc.stderr)
        self.assertNotIn("[1/", proc.stdout)

    def test_zsh_invocation_fails_loud_with_the_correct_reason(self) -> None:
        """修前：zsh 執行會走到 guard 缺席分支，印出與事實相反的「找不到 python」。

        本鎖要求：rc 非 0、訊息必須指出「請用 bash」，且**不得**出現 python 相關誤導字樣。
        zsh 不存在時 skip（本判準是 macOS 預設 shell 專屬）。
        """
        if shutil.which("zsh") is None:
            self.skipTest("本機無 zsh")
        proc = self._run([], shell="zsh")
        combined = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, combined)
        self.assertIn("需以 bash 執行", combined)
        # 比對的是**誤導性結論那一行**（含 `❌` 與可行動指示），不是「找不到 python」
        # 這個詞——修好後的訊息本身就會引述該詞來解釋自己在防什麼。
        self.assertNotIn("❌ 找不到 python", combined)
        self.assertNotIn("source .venv/bin/activate", combined)

    def test_guard_source_failure_is_fatal(self) -> None:
        """guard 檔缺席時必須硬錯——原本 `.` 失敗只印一行就繼續，guard 靜默蒸發。"""
        text = _read(_SH)
        self.assertRegex(
            _code_only(text),
            r"\.\s+\"\$SCRIPT_DIR/lib/windowsapps_guard\.sh\"\s*\|\|",
            "windowsapps_guard.sh 的 dot-source 未接失敗分支——載入失敗會被靜默吞掉",
        )


# --- `nightly:<token>@<腳本>` 載具指涉解析（本輪；見上方取證邊界 (d)）--------------

_NIGHTLY_CARRIER_RE = re.compile(r"nightly:([^@\s]+)@([\w./\\-]+\.(?:sh|ps1))")
_PS1_BLOCK_COMMENT_RE = re.compile(r"<#.*?#>", re.DOTALL)


def _script_code_only(path: Path) -> str:
    """腳本的**可執行內容**：先剝 `.ps1` 的 `<# … #>` 區塊，再剝整行 `#` 註解。

    WHY 兩層都要剝：本輪抓到的兩筆假登記中，被指名的那支 `.ps1` 檔頭區塊註解裡
    **逐字寫著**要找的那個檔名（在說明「mac 那支有、本檔沒有」）。只剝整行 `#`
    的話，token 會被那句「說明自己沒有」的散文滿足——鎖回報「有」，而可執行內容
    裡一個呼叫都沒有。判準必須落在會被執行的那些行上。
    """
    text = _read(path)
    if path.suffix.lower() == ".ps1":
        text = _PS1_BLOCK_COMMENT_RE.sub("", text)
    return _code_only(text)


class TestNightlyCarrierReferencesResolve(unittest.TestCase):
    """登記成 `nightly:<token>@<腳本>` 者，token 必須在該腳本的可執行內容裡抓得到。

    這道鎖要擋的**具體失敗**（本輪實測，不是假想）：登記表把兩個 CI step 指給
    `AutoClaude/tools/run_local_nightly.ps1`，而該檔當時**根本沒有**那兩件事——
    舊守門 `test_named_local_carriers_actually_exist` 只驗「被指名的檔案存在」，
    nightly 腳本當然存在，於是這張表可以說謊而零訊號。ONBOARDING §6.1 又刻意
    不再重抄、直接指向本表當唯一真相源 ⇒ 任何人拿它回答「什麼只能等雲端」都會
    得到錯的答案，而雲端此刻因帳務停擺根本不會跑。

    **仍未買到的**（誠實劃界，同上方邊界 (c)）：token 命中只證明「那支腳本真的
    呼叫／定義了它」，不證明「跑的範圍與 CI 那一步相同」。
    """

    def test_registered_nightly_tokens_exist_in_that_script(self) -> None:
        checked = 0
        for spec, registry in _CI_STEP_LOCAL_CARRIER.items():
            for step, carrier in registry.items():
                for token, rel in _NIGHTLY_CARRIER_RE.findall(carrier):
                    checked += 1
                    path = _REPO_ROOT / rel
                    self.assertTrue(
                        path.is_file(),
                        f"{spec}::{step} 登記的 nightly 載具 {rel} 不存在",
                    )
                    # 用 assertTrue 而非 assertIn：後者失敗時會把整支腳本（數萬字元）
                    # 傾印進訊息，判決句被埋在最後——與 F-09「紅不得被綠行淹掉」同族。
                    self.assertTrue(
                        token in _script_code_only(path),
                        f"{spec}::{step} 登記成 nightly:{token}@{rel}，但 {rel} 的"
                        f"可執行內容裡抓不到 {token!r}——註解裡提到不算數（那正是本鎖"
                        f"要抓的假登記）。處置：要嘛讓該腳本真的跑它，要嘛把本列改判為 "
                        f"{_NO_CARRIER} 並寫明理由",
                    )
        self.assertGreaterEqual(
            checked, 3,
            f"只驗到 {checked} 筆 nightly 載具指涉——登記寫法或抽取式疑似漂移"
            f"（0 命中會讓本鎖恆真，方向正好是「看起來變乾淨」）",
        )


# --- act 地端通道：workflow 可達性 ＋ 零通道 job 逐個具名登記（本輪 Scan-F）--------
#
# WHY：`AutoClaude/tools/run_act_core.py` 原先把 workflow 寫死成模組常數，於是薄殼
# 只指得到 autoclaude-ci.yml 一支；同一時間根層有 11 支 workflow 共 25 個 job，其中
# root-infra-ci.yml（承載根層全部守門）與兩支 compat-CI 的 nightly 告警鏈**一個都碰
# 不到**。本輪實測：`run_act.ps1 -List` 印 9 個 job、repo 根 `act -l` 印 25 個。而根
# CLAUDE.md 與 ONBOARDING 都把 act 寫成「Linux 容器跑真 CI」且無任何限定詞 ⇒ 讀者會
# 把 9/25 讀成全部。雲端帳務停擺期間，這個差是實質的驗證真空。
#
# 本節鎖三件事：
#   ① 每一支帶 ubuntu runs-on 的 workflow 都指得到（`--workflow` 真的被消費）；
#   ② 未指定旗標時的執行標的**維持原值**——零行為變更的機械證明，不是宣稱；
#   ③ runs-on 非 ubuntu 的 job 逐個具名登記為「結構上零本機通道」，不留白。
#
# 邊界（誠實劃界）：只驗「指得到」與「登記完整」，**不驗那支在 act 上跑得完**。跑得完
# 與否取決於 runner 映像缺件（pwsh/gh/ruff）與 act 0.2.89 對 `services:` 的上游 panic，
# 兩者由 `run_act_core.preflight()` 在燒掉幾分鐘之前逐項講明，不由本節代為裁決。
_ACT_CORE_PATH = _REPO_ROOT / "AutoClaude" / "tools" / "run_act_core.py"

#: runs-on 不是 ubuntu 的 job ⇒ act 結構上零通道。值＝為何零通道 ＋ 該平台的替代出口。
#: 判準刻意用**逐字相等**而非「只准變少」：新增一個 non-ubuntu job 時必須在這裡補一句
#: 話。留白正是本表要治的病——這 4 個 job 先前在 repo 任何登記表裡都不存在。
_ACT_NO_LOCAL_RUNNER_JOBS: dict[str, str] = {
    "macos-compat-ci.yml::macos-smoke": (
        "runs-on=macos-latest —— Docker 無 macOS 容器，act 結構上不可能有此 runner。"
        "替代＝mac 真機直接跑 tools/macos_smoke_local.sh"
    ),
    "macos-compat-ci.yml::macos-nightly-full": (
        "runs-on=macos-latest —— 同上。"
        "替代＝mac 真機直接跑 AutoClaude/tools/run_local_nightly.sh"
    ),
    "windows-compat-ci.yml::windows-smoke": (
        "runs-on=windows-latest —— act 只起 Linux 容器，Windows runner 無此通道。"
        "替代＝Windows 真機直接跑 tools/windows_smoke_local.ps1"
    ),
    "windows-compat-ci.yml::windows-nightly-full": (
        "runs-on=windows-latest —— 同上。"
        "替代＝Windows 真機直接跑 AutoClaude/tools/run_local_nightly.ps1"
    ),
}

#: 全庫 job 數下限（防抽取式漂移後 0 命中，讓下方每一條 for 迴圈都恆真）。
_MIN_ACT_JOBS = 20
#: workflow 檔數下限（同上，另一個維度）。
_MIN_ACT_WORKFLOWS = 8


def _load_act_core() -> ModuleType:
    """以檔案路徑載入 `run_act_core`（不寫 sys.modules，沿用本檔 `_load_ps51_module`）。

    刻意載入**模組本體**並呼叫它的函式，而不是用 regex 讀原始碼：後者只鎖得住長相，
    「旗標宣告了但沒人消費」照樣綠——而那正是本鎖要抓的失敗形態。
    """
    spec = importlib.util.spec_from_file_location("_run_act_core_for_sync_lock", _ACT_CORE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"無法載入 {_ACT_CORE_PATH}——act 地端通道鎖失效")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestActWorkflowReachability(unittest.TestCase):
    """act 薄殼的射程：全庫 workflow 都指得到，指不到的逐個具名登記。"""

    def setUp(self) -> None:
        self.core = _load_act_core()

    def _target(self, argv: list[str]) -> str:
        """在環境變數被清空的前提下解析出「實際會交給 act 的 workflow」。

        WHY 要清：本機若剛好設了那個環境變數，下面的斷言會量到它而不是被測邏輯——
        載具自身不得成為變因（本 repo 對「量測管道給假數字」已付過多次學費）。
        """
        saved = os.environ.pop(self.core.WORKFLOW_ENV, None)
        try:
            return self.core.run_workflow(self.core.parse_args(argv))
        finally:
            if saved is not None:
                os.environ[self.core.WORKFLOW_ENV] = saved

    def test_default_target_is_unchanged_without_the_flag(self) -> None:
        """未給旗標＝沿用原本那支。這條是「零行為變更」的機械證明。"""
        self.assertEqual(
            self._target([]), self.core.WORKFLOW,
            "未指定 --workflow 時的執行標的已被改動——加旗標不得順手改預設，"
            "既有使用者（含文件、薄殼、AutoClaude 側呼叫端）都靠它",
        )

    def test_every_ubuntu_workflow_is_reachable_via_the_flag(self) -> None:
        """每一支含 ubuntu job 的 workflow 都指得到，且 preflight 認得那條路徑。"""
        rows = self.core.job_inventory()
        self.assertGreaterEqual(
            len(rows), _MIN_ACT_JOBS,
            f"全庫只盤到 {len(rows)} 個 job < 下限 {_MIN_ACT_JOBS}——job 抽取式疑似漂移",
        )
        self.assertGreaterEqual(len(self.core.workflow_files()), _MIN_ACT_WORKFLOWS)
        ubuntu_files = sorted({wf for wf, _j, label, _r, _s in rows if label.startswith("ubuntu")})
        self.assertTrue(ubuntu_files, "一支帶 ubuntu job 的 workflow 都沒盤到——抽取式已壞")
        for name in ubuntu_files:
            rel = f"{self.core.WORKFLOW_DIR}/{name}"
            self.assertEqual(
                self._target(["--workflow", rel]), rel,
                f"--workflow {rel} 沒有被消費——旗標宣告了卻沒接到執行路徑上，"
                f"薄殼會退回只看得到單一 workflow 的狀態",
            )
            blockers, _warnings = self.core.preflight(rel, "")
            self.assertEqual(
                [b for b in blockers if "不存在" in b], [],
                f"preflight 認為 {rel} 不存在——路徑基準（repo 相對）已不一致",
            )

    def test_workflows_without_push_are_blocked_not_silently_green(self) -> None:
        """`on:` 不含預設事件者，必須被 preflight **阻斷**，不得零執行卻回 rc=0。

        WHY 這條非有不可：本輪把 `--workflow` 接上之後，第一次真跑就踩到——act 對事件
        對不上的 workflow 是「不跑任何 job 然後回 rc=0」，畫面上只有一行 `Using docker
        host`。實測逐字：`--workflow …arch-fitness.yml --job pr-advisory` → ACT_RC=0、
        零 job 執行。全庫 11 支裡有 5 支的 `on:` 不含 push ⇒ 把 workflow 指得到這件事
        **本身**讓這個假綠第一次變得碰得到，兩者必須同批落地。
        """
        no_push = 0
        for path in self.core.workflow_files():
            events = self.core.workflow_events(path)
            # 解析式漂移會讓 workflow_events 回空集合（刻意 fail-open，見該函式 docstring）
            # ⇒ preflight 的事件判準整條靜默失效。那個方向看起來正好像「都沒問題」。
            self.assertTrue(
                events, f"{path.name} 解析不到 on: 觸發事件——事件判準會整條靜默失效",
            )
            rel = f"{self.core.WORKFLOW_DIR}/{path.name}"
            hit = [
                b for b in self.core.preflight(rel, "", self.core.DEFAULT_EVENT)[0]
                if "觸發事件" in b  # preflight 事件不符那筆的判別詞（改措辭會讓本鎖紅）
            ]
            if self.core.DEFAULT_EVENT in events:
                self.assertEqual(hit, [], f"{path.name} 有 {self.core.DEFAULT_EVENT} 觸發卻被誤擋")
                continue
            no_push += 1
            self.assertTrue(
                hit,
                f"{path.name} 的 on: 是 {sorted(events)}，不含 {self.core.DEFAULT_EVENT}，"
                f"preflight 卻放行——使用者會拿到零執行的 rc=0 假綠",
            )
            ok = [b for b in self.core.preflight(rel, "", sorted(events)[0])[0] if "觸發事件" in b]
            self.assertEqual(
                ok, [],
                f"{path.name} 改用它自己接受的事件 {sorted(events)[0]} 後仍被擋——"
                f"這條判準會變成沒有出口的死鎖",
            )
        self.assertGreaterEqual(
            no_push, 1,
            "全庫沒有任何一支缺預設事件的 workflow——若屬實可刪本鎖；更可能是 on: 抽取式"
            "已漂移，而漂移方向正好是「看起來都沒問題」",
        )

    def test_every_ubuntu_job_has_a_runner_mapping_in_actrc(self) -> None:
        """ubuntu job 必須在 `.actrc` 的 `-P` 映射內，否則 act 只印一行就回 rc=0＝假綠。"""
        for wf, job, label, has_runner, _services in self.core.job_inventory():
            if label.startswith("ubuntu"):
                self.assertTrue(
                    has_runner,
                    f"{wf}::{job} runs-on={label} 不在 .actrc 的 -P 映射內 —— act 對沒有"
                    f"映射的 runner 會印「Skipping unsupported platform」然後**回 rc=0**"
                    f"（假綠）。處置：在根層 .actrc 補一行 -P {label}=<映像>",
                )

    def test_non_ubuntu_jobs_are_registered_as_having_no_local_channel(self) -> None:
        """非 ubuntu 的 job 必須逐個具名登記並寫明替代出口——不得留白。"""
        actual = {
            f"{wf}::{job}"
            for wf, job, label, _r, _s in self.core.job_inventory()
            if not label.startswith("ubuntu")
        }
        self.assertEqual(
            actual, set(_ACT_NO_LOCAL_RUNNER_JOBS),
            "本機 act 零通道的 job 清單與 `_ACT_NO_LOCAL_RUNNER_JOBS` 不一致——"
            "新增／刪除非 ubuntu 的 job 時必須同步登記。留白會讓下一位讀者以為"
            "「act 跑得動全部 CI」，而那正是本節在治的病",
        )
        for key, reason in _ACT_NO_LOCAL_RUNNER_JOBS.items():
            self.assertIn("替代", reason, f"{key} 的登記沒寫替代出口——只說「不行」不夠")
