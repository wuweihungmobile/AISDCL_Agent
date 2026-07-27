#!/usr/bin/env python3
"""架構判準的機械強制：**宣稱結束代碼契約者，不得只有文字錨**（R58 落地）。

## 病灶（本輪抓到的鐵證，這條判準就是為它而立）

`tools/install_windows_nightly.ps1` 的 `-Status` 有明確的結束代碼契約（任務存在→0、不存在→1，
帳本 DEF-101-248 宣稱已修）。守它的是兩行**文字斷言**：

    self.assertIn("$loaded = Show-NightlyStatus", status_block)
    self.assertIn("if ($loaded) { exit 0 } else { exit 1 }", status_block)

這兩行**一直是綠的**。而真實行為是 `-Status` **輸出 0 bytes、恆 exit 0**——PowerShell 的變數
指派會捕獲 success stream，`Write-Output` 印的報告全被吃進 `$loaded`，使它變成元素數 ≥2 的
`Object[]`，而 PowerShell 對這種陣列一律判真 ⇒ `if ($loaded) { exit 0 }` 恆成立。
**「程式碼長得對」被驗過了，「跑起來對」從來沒有。** 這個缺陷在 `3f81d5c`「R20 真 Windows 11
首輪機器複審」那一輪引入，在真 Windows 機器上通過複審，之後歷經多輪四方 APPROVE 都沒被抓到
——因為四位複審者讀的是同一份文字、看的是同一批綠色靜態錨。

## 判準

> 凡以**文字斷言**宣稱某可執行標的的**結束代碼控制流**（`exit 0`／`exit 1`／`$LASTEXITCODE`／
> `return $true`／`$? -eq` 等原始碼片段）者，同一支測試檔內**必須**另有至少一處**行為層**
> 斷言——即真的執行它並對觀測到的 `returncode` 表態（或以 `check=True` 讓非零直接拋）。

文字錨本身**不是壞東西**（它便宜、跨平台、能鎖住「這行接線還在」），本判準不禁止它；
禁止的是**只有**它。

## 掃描面（三段式，不做全備宣稱）

**已實測涵蓋**：全 repo `test_*.py`（**tracked ∪ untracked-but-not-ignored**，見 `_scanned_test_modules`）內，對「含結束代碼控制流語法的字串字面值」
所做的 `assertIn`／`assertNotIn`／`assertRegex`／`assertNotRegex`／`assertEqual`。R58 落地當下
實掃命中 **2 處**（皆在 `test_install_windows_nightly.py`），且該檔已有行為層斷言 ⇒ offender 0。

**已實測不涵蓋**（誠實劃界）：
  1. **粒度是「同檔」而非「同一個標的」**——同檔的行為層斷言可能驗的是別的東西。刻意選擇
     較粗的粒度：更嚴的「同一個標的必須配對」需要把「這段文字屬於哪支腳本」機械化，而本
     repo 的測試常以 helper／here-string／`-Command` payload 間接引用腳本，那種配對做出來
     假陽性會遠多於真陽性（R58 實測過一版「腳本是否被真的執行」的分類器，35 支 active 腳本
     中 28 支被誤判為『只有文字錨』，其中多支其實有 dot-source 執行的測試——**該版本因假陽性
     過高而未採用**，此處記下避免後人重造）。
  2. 斷言字串以變數／f-string 拼接組成者抓不到（本檔只看字面值 `ast.Constant`）。
  3. 行為層斷言的判準是「檔內有 `.returncode` 引用或 runner 帶 `check=True`」——以 `assert
     proc.stdout == …` 間接驗證行為者不算（方向為多要求＝fail-closed，不影響正確性）。

**未窮舉**：以上只列已實機量測過的形態，不做「唯一殘餘風險是 X」這類宣稱。
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry_hygiene import stale_problems  # noqa: E402
from _repo_scan import scanned  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 結束代碼控制流的原始碼特徵（PowerShell 與 bash 皆納）。
_EXIT_CONTROL_FLOW_RE = re.compile(
    r"exit\s+\$?\d"          # exit 0 / exit 1 / exit $n
    r"|exit\s+\$LASTEXITCODE"
    r"|LASTEXITCODE"
    r"|return\s+\$(?:true|false)"
    r"|\$\?\s*-eq"           # bash: if [ $? -eq 0 ]
    r"|rc=\$\?",
    re.IGNORECASE,
)
_TEXT_ASSERTS = frozenset(
    {"assertIn", "assertNotIn", "assertRegex", "assertNotRegex", "assertEqual"}
)
_SUBPROCESS_RUNNERS = frozenset({"run", "Popen", "check_output", "check_call", "call"})

# 🔴 **本表只豁免核心判準**（「文字錨必須配行為層斷言」）。**不要**拿它來消音成長觸發
# ——那會同時關掉核心判準（R58 round 3 ARCH-R58R3-03 立案；round 4 ARCH-R58R4-01 以注入矩陣
# 實證實害：模組塞進本表後核心判準轉綠，而維護者原本要修的成長紅燈**依然亮著**＝白白交出
# 一道大鎖卻換不到任何東西）。成長觸發有自己的逃生口 `_GROWTH_EXEMPT`，見下。
#
# 兩表**各自**須附理由（空理由視為未附 → 紅）、**各自**做 stale 自檢（檔案不存在也紅），
# 由 `test_exemption_registry_is_not_stale` 一併驗（round 4 ARCH-R58R4 P3 ①：原本只迭代
# `_EXEMPT`，於是「兩個決定各自獨立可審」這個宣稱少了一半）。
_EXEMPT: dict[str, str] = {}

# 成長觸發（`test_registry_grows_with_every_new_exit_code_text_anchor`）的**獨立**逃生口。
# 為什麼要分開：兩者共用 `_EXEMPT` 時，遇到「某模組有結束代碼文字錨、但它錨的標的已由別的
# 模組登記為擁有者」這種合法情形，維護者唯一的出路是把該模組塞進 `_EXEMPT`，而那會**連帶
# 關掉核心判準**——用一個小問題換掉一道大鎖。分開後兩個決定各自獨立可審。
_GROWTH_EXEMPT: dict[str, str] = {}

# ── 結束代碼契約的「行為層擁有者」正向登記表（R58 round 1 QA-R58R1-02 落地）──────────
# **為什麼需要這張表**：上面那條掃描的粒度是「同檔」（docstring 已自陳），而複審者實測證明
# 這個粒度**不只是理論限制、它放行了立案病灶本身**：`install_windows_nightly.ps1 -Status` 的
# 結束代碼契約退化時（在 `Show-NightlyStatus` 內插一行裸表達式即可），該檔因為有**別的**
# 行為層斷言（驗被呼叫者 `Test-TaskPowerSettings` 的回傳型別）而恆綠——三位複審者各自獨立
# 用同一手法注入，24 支測試全綠。
#
# 全自動的「哪段文字屬於哪支腳本」分類器已被實測否決（見模組 docstring「已實測不涵蓋」第 1
# 條：35 支 active 腳本中 28 支被誤判，假陽性遠多於真陽性）。故改用**小而人工維護的正向登記
# 表**：key＝有結束代碼契約的可執行標的，value＝負責它的行為層測試（`模組路徑::類別`）。
# 這張表的價值不在自動發現，而在**強迫具名一個擁有者**——「誰負責證明它跑起來是對的」這個
# 問題從此有書面答案，而不是散落在「某個檔案裡大概有吧」。
#
# 收錄判準（刻意窄，避免變成無人維護的大清單）：該標的**有明確的結束代碼契約**，且該契約
# 曾經（或可能）在退化時無訊號。新增條目時請一併新增／指名真正執行它的測試類別。
_EXIT_CODE_CONTRACT_TARGETS: dict[str, str] = {
    "tools/install_windows_nightly.ps1": (
        "tools/tests/test_install_windows_nightly.py::TestShowNightlyStatusReturnsCleanBoolean"
    ),
    "AutoClaude/tools/reschedule_g0_gatecheck.ps1": (
        "AutoClaude/tests/tools/test_reschedule_g0_gatecheck_static.py"
    ),
}


def _scanned_test_modules() -> list[str]:
    """掃描面 ＝ tracked ∪ untracked-but-not-ignored（委派 `_repo_scan.scanned`）。

    **R58 round 2 ARCH-R58R2-01 訂正**：本函式原名 `_tracked_test_modules()` 且只跑
    `git ls-files`（tracked-only）。round 1 已把姊妹掃描器改為 tracked ∪ untracked，
    論證是「新檔在 `git add` 之前也必須被守，否則新程式碼享有豁免」——**該論證對本檔
    逐字適用，卻沒落地**，於是兩支同輪、同需求的掃描器有兩套政策。而本檔正是那條最重要
    判準（文字錨 vs 行為層）的機械鎖，留在 tracked-only 意味著下一輪的新測試檔又一次
    在定義上不在面內，與 round 1 造成假綠基線的形態一模一樣。
    """
    return scanned("*test_*.py")


def _call_name(node: ast.Call) -> str | None:
    fn = node.func
    if isinstance(fn, ast.Attribute):
        return fn.attr
    if isinstance(fn, ast.Name):
        return fn.id
    return None


def has_behavioural_assertion(tree: ast.AST) -> bool:
    """檔內是否有「對真實執行結果表態」的斷言：引用 `.returncode`，或 runner 帶 `check=True`。"""
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "returncode":
            return True
        if isinstance(node, ast.Call) and _call_name(node) in _SUBPROCESS_RUNNERS:
            for kw in node.keywords:
                if (
                    kw.arg == "check"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    return True
    return False


def exit_code_text_anchors(tree: ast.AST) -> list[tuple[int, str]]:
    """檔內以文字斷言宣稱結束代碼控制流的位置與被斷言的字串（前 60 字）。"""
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) not in _TEXT_ASSERTS:
            continue
        # 只看前兩個位置引數：`assertIn(needle, haystack)` 的 needle 與（少數寫法的）haystack
        for arg in node.args[:2]:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and _EXIT_CONTROL_FLOW_RE.search(arg.value)
            ):
                hits.append((node.lineno, arg.value[:60].replace("\n", "\\n")))
                break
    return hits


class ExitCodeContractNeedsBehaviouralLockTest(unittest.TestCase):
    def test_no_module_claims_exit_code_contract_with_text_anchor_only(self) -> None:
        offenders: list[str] = []
        for rel in _scanned_test_modules():
            if rel in _EXEMPT:
                continue
            try:
                with warnings.catch_warnings():
                    # 掃描面內既有檔案帶有非 raw 字串的 `\s`（如 test_ps51_compat.py 的模組
                    # docstring），`ast.parse` 會噴 DeprecationWarning。那是別的檔案的既有債，
                    # 本鎖不因掃描動作替它產生噪音（沿用 test_find_git_bash_parity.py 慣例）。
                    warnings.simplefilter("ignore", DeprecationWarning)
                    tree = ast.parse((_REPO_ROOT / rel).read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue  # 語法／編碼問題由別的閘門負責，本鎖不重複翻紅
            anchors = exit_code_text_anchors(tree)
            if anchors and not has_behavioural_assertion(tree):
                where = "、".join(f"L{ln}({txt!r})" for ln, txt in anchors)
                offenders.append(f"{rel}: {where}")
        self.assertEqual(
            offenders, [],
            "下列測試檔以**文字斷言**宣稱了結束代碼控制流，但同檔沒有任何**行為層**斷言"
            "（無 `.returncode` 引用、也無 runner 帶 `check=True`）：\n"
            + "\n".join(f"  - {o}" for o in offenders)
            + "\n\n這正是 R58 抓到的病灶形態：`install_windows_nightly.ps1 -Status` 的兩行文字"
            "錨一直是綠的，而真實行為是輸出 0 bytes、恆 exit 0（PowerShell success stream 被"
            "變數指派吃掉）——「程式碼長得對」驗過了，「跑起來對」從來沒有，於是該缺陷在真"
            "Windows 機器上通過複審並存活多輪。\n"
            "修法：補一支**真的執行**該標的並斷言 `proc.returncode` 的測試（可用合成輸入 + "
            "可丟棄的暫存資源，不必動到真實系統狀態；本輪 "
            "`test_install_windows_nightly.TestStatusPowerSettingsFunctionBehaviour` 與 "
            "`AutoClaude/tests/tools/test_reschedule_g0_gatecheck_static.py` 皆為可照抄的範例）。"
            "確實無法行為層驗證者，加入本檔 `_EXEMPT` 並附理由。",
        )

    def test_every_exit_code_contract_target_has_a_named_behavioural_owner(self) -> None:
        """正向登記表：每個標的都必須存在，且其具名的行為層擁有者必須真的存在且真的行為層。

        三段檢查：①標的檔案存在 ②擁有者模組存在 ③（若指定了 `::類別`）該類別確實在該模組的
        AST 內、且該模組有行為層斷言。**第 ③ 條的類別存在性是這張表的核心價值**——它讓
        「我補了一支測試」這件事被釘在名字上，重構改名時會翻紅而不是靜默失去擁有者。
        """
        problems: list[str] = []
        for target, owner in _EXIT_CODE_CONTRACT_TARGETS.items():
            if not (_REPO_ROOT / target).is_file():
                problems.append(f"標的已不存在：{target}（請移除或更新登記）")
            mod_rel, _, cls_name = owner.partition("::")
            mod_path = _REPO_ROOT / mod_rel
            if not mod_path.is_file():
                problems.append(f"{target} 的行為層擁有者模組不存在：{mod_rel}")
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    tree = ast.parse(mod_path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError) as exc:
                problems.append(f"{mod_rel} 無法解析（{type(exc).__name__}）")
                continue
            if not has_behavioural_assertion(tree):
                problems.append(
                    f"{target} 的擁有者 {mod_rel} 沒有任何行為層斷言"
                    "（無 `.returncode` 引用、也無 runner 帶 `check=True`）"
                )
            if cls_name:
                classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
                if cls_name not in classes:
                    problems.append(
                        f"{target} 具名的行為層類別 {cls_name} 不在 {mod_rel} 內"
                        "——測試被改名或刪除，擁有者登記已失效"
                    )
        self.assertEqual(
            problems, [],
            "結束代碼契約的行為層擁有者登記表已失效：\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\n\n這張表存在的理由見 `_EXIT_CODE_CONTRACT_TARGETS` 上方註解："
            "同檔粒度的自動掃描已被實測證明會放行立案病灶本身（三位複審者各自獨立注入、"
            "24 支測試全綠），故改以具名擁有者補足。",
        )

    def test_registry_grows_with_every_new_exit_code_text_anchor(self) -> None:
        """**成長觸發**（R58 round 2 ARCH-R58R2-04）：凡出現結束代碼文字錨的測試模組，
        都必須以擁有者身分出現在 `_EXIT_CODE_CONTRACT_TARGETS` 的 value 內（或列入附理由的
        `_GROWTH_EXEMPT`——**不是** `_EXEMPT`，那是核心判準的逃生口，混用會關掉大鎖卻不解本紅燈；
        理由見下方失敗訊息與 `_GROWTH_EXEMPT` 上方註解）。

        沒有這一條時，這張表只會腐化不會成長：它驗得了「已登記兩筆是健康的」，卻對
        「出現了新的結束代碼契約標的卻沒人登記」完全無訊號——兩三輪後就會被當成歷史遺跡，
        而同檔粒度的破口對新標的依然開著（下一個標的照樣可以只有文字錨、且同檔剛好有別的
        行為層斷言就恆綠）。

        刻意用「模組」而非「腳本」當觸發單位：把「這段文字屬於哪支腳本」機械化的分類器已被
        實測否決（見模組 docstring「已實測不涵蓋」第 1 條），而「哪個模組寫了文字錨」是零
        假陽性的事實，且它強迫的正是我們要的那個動作——**具名一個擁有者**。
        """
        owners = {v.partition("::")[0] for v in _EXIT_CODE_CONTRACT_TARGETS.values()}
        unowned: list[str] = []
        for rel in _scanned_test_modules():
            if rel in _GROWTH_EXEMPT or rel in owners:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    tree = ast.parse((_REPO_ROOT / rel).read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            if exit_code_text_anchors(tree):
                unowned.append(rel)
        self.assertEqual(
            unowned, [],
            "下列測試模組含結束代碼文字錨，卻未被任何 `_EXIT_CODE_CONTRACT_TARGETS` 條目"
            f"指名為擁有者：{unowned}\n"
            "請在該表新增一筆（key＝有結束代碼契約的可執行標的、value＝本模組『路徑::類別』），"
            "並確認該類別真的執行那個標的並斷言觀測結果。\n"
            "🔴 **確實無法具名擁有者時，逃生口是本檔的 `_GROWTH_EXEMPT`，不是 `_EXEMPT`**"
            "——`_EXEMPT` 是**核心判準**（文字錨必須配行為層斷言）的逃生口，把模組塞進去會"
            "**連帶關掉那道大鎖**，而你正在修的這盞紅燈**依然不會解掉**"
            "（R58 round 4 ARCH-R58R4-01 以注入矩陣雙向實證：入 `_EXEMPT` ⇒ 核心轉綠、成長仍紅；"
            "入 `_GROWTH_EXEMPT` ⇒ 成長轉綠、核心仍紅——後者才是你要的）。\n"
            "理由見 `_EXIT_CODE_CONTRACT_TARGETS` 上方註解：同檔粒度的自動掃描已被實測證明會"
            "放行立案病灶本身（三位複審者各自獨立注入、24 支測試全綠）。",
        )

    def test_exemption_registry_is_not_stale(self) -> None:
        """兩張表各自驗「檔案存在 + 理由非空」，判準實作委派名冊衛生 SSOT。

        **R58 round 5 ARCH-R58R5 P3 ④ 收斂**：本測試原**就地手寫**這兩條 invariant，而
        `stale_problems()` 早已是同兩條的純函式實作、且配有鑑別力自驗——也就是在本輪
        「消滅同一行為的多份複本」這個立案主題上，round 4 的修復（把 `_GROWTH_EXEMPT`
        加進手寫那一份）自己又生出一份複本。改為委派 `_registry_hygiene`，訊息字面不變
        （`label` 參數保留表名前綴），並因此連帶取得那支自驗的鑑別力保障。
        """
        # 🔴 **本斷言在現況下不可能失敗**（兩表皆為空 dict，`stale_problems({}, …)` 恆回 `[]`）。
        # 這是刻意的：鑑別力**寄放在** `test_platform_guard_availability.py::
        # ExemptionRegistryHygieneTest.test_stale_detector_has_discrimination`（餵合成輸入證明
        # 存在性、空白理由、label 前綴三條路徑都活著）。若有人刪掉那支自驗，本處的保護會
        # **靜默消失且無任何紅燈**——故此註解即為交叉引用（R58 round 6 ARCH-R58R6 P3）。
        problems = stale_problems(_EXEMPT, _REPO_ROOT, "_EXEMPT")
        problems += stale_problems(_GROWTH_EXEMPT, _REPO_ROOT, "_GROWTH_EXEMPT")
        self.assertEqual(problems, [], f"豁免名冊已腐化：{problems}")


class DetectorSelfTest(unittest.TestCase):
    """偵測器自驗：合成樣本必須被正確分類。

    一支「掃全 repo 都沒發現問題」的測試若不自驗，無從分辨「乾淨」與「偵測器壞了」
    （本 repo 既有慣例，見 `test_python_c_percent_shim.py`、`test_platform_guard_availability.py`）。
    """

    _BAD = (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_x(self):\n"
        '        self.assertIn("if ($loaded) { exit 0 } else { exit 1 }", src)\n'
    )
    _GOOD_BEHAVIOURAL = _BAD + (
        "    def test_y(self):\n"
        "        proc = subprocess.run([exe])\n"
        "        self.assertEqual(proc.returncode, 1)\n"
    )
    _GOOD_CHECK_TRUE = _BAD + (
        "    def test_y(self):\n"
        "        subprocess.run([exe], check=True)\n"
    )

    def test_text_anchor_without_behavioural_is_flagged(self) -> None:
        tree = ast.parse(self._BAD)
        self.assertEqual(len(exit_code_text_anchors(tree)), 1)
        self.assertFalse(has_behavioural_assertion(tree))

    def test_returncode_assertion_counts_as_behavioural(self) -> None:
        self.assertTrue(has_behavioural_assertion(ast.parse(self._GOOD_BEHAVIOURAL)))

    def test_check_true_counts_as_behavioural(self) -> None:
        self.assertTrue(has_behavioural_assertion(ast.parse(self._GOOD_CHECK_TRUE)))

    def test_plain_text_assertion_is_not_an_exit_code_anchor(self) -> None:
        """反向：不含結束代碼語法的文字斷言不得被誤報（否則整個 repo 都是 offender）。"""
        tree = ast.parse(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            '        self.assertIn("Register-ScheduledTask", src)\n'
        )
        self.assertEqual(exit_code_text_anchors(tree), [])

    def test_known_real_world_hit_is_still_detected(self) -> None:
        """回源鎖：本判準立案所依據的那支檔案必須仍被偵測到有結束代碼文字錨。

        若它哪天被改寫成不含文字錨，本鎖對真實語料的鑑別力就無從證明——那時應改以別的
        真實命中回填本測試，而不是刪掉它。
        """
        rel = "tools/tests/test_install_windows_nightly.py"
        path = _REPO_ROOT / rel
        self.assertTrue(path.is_file(), f"立案依據檔已不存在：{rel}")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        self.assertTrue(
            exit_code_text_anchors(tree),
            f"{rel} 已不含結束代碼文字錨——請改以其他真實命中回填本測試（見 docstring）",
        )
        self.assertTrue(
            has_behavioural_assertion(tree),
            f"{rel} 失去行為層斷言——R58 為 DEF-101-248 補的行為層驗證已退化",
        )


if __name__ == "__main__":
    unittest.main()
