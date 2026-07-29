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
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[2]
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


if __name__ == "__main__":
    unittest.main()
