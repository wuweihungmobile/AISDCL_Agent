#!/usr/bin/env python3
"""`_ci_scan_anchors` 錨本身的鑑別力測試（R57 A2）。

WHY 需要這一層：`test_ps1_bom.py`／`test_smoke_ci_sync.py`／`test_ps51_compat.py`
的 CI 掃描面鎖只會在「root-infra-ci.yml 真的被改」時翻紅；錨本身鑑別力被弱化
（R56 那次是硬綁 `-Path` 具名參數）時三份全部零訊號——本檔以**合成的變異 step
文字**把 R57 實測到的逃逸手法固化成常駐斷言：舊錨對它們全綠，新錨必紅。

執行：python3 tools/run_root_unittests.py
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _ci_scan_anchors  # noqa: E402  # 需要模組物件本身：雙向同步鎖要讀其 __doc__
from _ci_scan_anchors import (  # noqa: E402
    CI_GCI_CALL_RE,
    CI_SCAN_STMT_RE,
    CI_TREE_RE,
    EXPECTED_CI_GCI_CALLS,
    EXPECTED_CI_SCAN_STATEMENTS,
    ci_fixed_trees,
    ci_gci_call_count,
    ci_scan_statement_count,
    strip_line_comments,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROOT_INFRA_CI = _REPO_ROOT / ".github" / "workflows" / "root-infra-ci.yml"
_STEP_RE = r"^ +- name: pwsh 語法解析.*?(?=^ +- name: )"

# R56 那兩個硬綁 `-Path` 的舊錨，原樣保留在本檔作為「對照組」：下方測試斷言它們
# 對位置參數形態的擴面完全無感（＝R57 修的就是這件事），未來若有人把生產錨改回
# 這種形態，對照組與新錨的行為差異測試會立刻失去意義而翻紅。
_LEGACY_TREE_RE = r"Get-ChildItem -Path ([A-Za-z0-9_.\-/]+) -Recurse"
_LEGACY_COUNT_RE = r"Get-ChildItem\s+-Path"

# 位置參數形態的第 5 棵樹（`-Path` 省略）——PowerShell 合法且最省字，複製貼上
# 既有行後順手刪掉 `-Path` 就會長這樣。
_POSITIONAL_EVASION = (
    '            $files += @(Get-ChildItem docs/scripts -Recurse -Filter *.ps1 -File)\n'
)


def _real_step() -> str:
    ci = _ROOT_INFRA_CI.read_text(encoding="utf-8")
    m = re.search(_STEP_RE, ci, re.MULTILINE | re.DOTALL)
    assert m is not None, "root-infra-ci.yml 找不到 pwsh 語法解析 step——結構已變動"
    return m.group(0)


class TestCiScanAnchorsOnRealStep(unittest.TestCase):
    def test_fixed_trees_on_real_step(self) -> None:
        """新抽取式在真實 step 上抽到的樹集合，必須與 R56 舊式完全相同——
        本次修改是「擴大可辨識形態」，不是「改變現行判讀」。"""
        step = _real_step()
        self.assertEqual(
            ci_fixed_trees(step), {"tools", "AutoClaude/tools", "AISDLC_SDD/scripts"}
        )
        self.assertEqual(ci_fixed_trees(step), set(re.findall(_LEGACY_TREE_RE, step)))

    def test_scan_statement_count_on_real_step(self) -> None:
        self.assertEqual(
            ci_scan_statement_count(_real_step()), EXPECTED_CI_SCAN_STATEMENTS
        )

    def test_gci_call_count_on_real_step(self) -> None:
        """cmdlet 計數錨在真實 step 上＝4（`Get-ChildItem` 4 次、三個別名皆 0 次）。"""
        step = _real_step()
        self.assertEqual(ci_gci_call_count(step), EXPECTED_CI_GCI_CALLS)
        self.assertEqual(len(re.findall(r"Get-ChildItem", step)), EXPECTED_CI_GCI_CALLS)


class TestGciCallCountBoundaries(unittest.TestCase):
    """釘住 cmdlet 計數錨 docstring 裡的兩條可查證宣稱（別名邊界／不剝註解的代價）。"""

    def test_alias_word_boundaries_reject_lookalikes(self) -> None:
        """`$dir`／`$ls`／`.dir`／`-ls`／`gcignore` 不得被當成別名呼叫（偽陽性防線）。"""
        self.assertEqual(
            ci_gci_call_count("$dir = 1; $ls = 2; $x.dir; -ls; gcignore; dirs; lsof"), 0
        )

    def test_bare_aliases_are_counted(self) -> None:
        """`gci`／`dir`／`ls` 三個別名在指令位置皆計入（Architect 建議的兜底面）。"""
        self.assertEqual(ci_gci_call_count("@(gci x)\n@(dir y)\n@(ls z)\n"), 3)

    def test_full_line_comment_mention_is_not_counted(self) -> None:
        """SSOT 內部一律先剝整行 `#` 註解（R57 round 2 SA-R57R2-02），故註解裡提到
        cmdlet 字樣**不**計入——這是三份呼叫端能共用同一組 EXPECTED_* 的前提。"""
        self.assertEqual(
            ci_gci_call_count(_real_step() + "            # TODO 改用 Get-ChildItem\n"),
            EXPECTED_CI_GCI_CALLS,
        )


class TestAnchorsAreCaseInsensitive(unittest.TestCase):
    """R57 round 2 ARCH-01：PowerShell cmdlet／別名／參數名皆不分大小寫，上一版
    三條錨全部大小寫敏感 → `get-childitem …-recurse -filter *.ps1 -file` 全小寫
    第 5 棵樹實測三錨全綠逃逸。本類直接釘住 flag 與行為，未來有人拿掉 `re.IGNORECASE`
    會立刻翻紅（否則無訊號）。"""

    def test_all_three_compiled_anchors_carry_ignorecase_flag(self) -> None:
        for name, rx in (
            ("CI_TREE_RE", CI_TREE_RE),
            ("CI_SCAN_STMT_RE", CI_SCAN_STMT_RE),
            ("CI_GCI_CALL_RE", CI_GCI_CALL_RE),
        ):
            with self.subTest(anchor=name):
                self.assertTrue(
                    rx.flags & re.IGNORECASE,
                    f"{name} 缺 re.IGNORECASE——PowerShell 不分大小寫，"
                    f"全小寫寫法可 all-green 逃逸",
                )

    def test_lowercased_real_step_yields_identical_counts(self) -> None:
        """把整個 step 轉小寫後三錨讀數不變（樹名本身會跟著轉小寫，故只比棵數）。"""
        lowered = _real_step().lower()
        self.assertEqual(len(ci_fixed_trees(lowered)), 3)
        self.assertEqual(ci_scan_statement_count(lowered), EXPECTED_CI_SCAN_STATEMENTS)
        self.assertEqual(ci_gci_call_count(lowered), EXPECTED_CI_GCI_CALLS)


class TestInputPreprocessingContract(unittest.TestCase):
    """R57 round 2 SA-R57R2-02：三份呼叫端的輸入前處理曾經分歧（smoke 餵
    `_code_only()` 剝註解後的 step、另兩份餵原文）卻共用同一組 EXPECTED_* 常數，
    實測在 step 尾端加一行註解即 raw=5／code_only=4，**無任何單一常數能同時滿足
    三份**。修法是把前處理收進 SSOT 並保證冪等，本類以性質測試守住該契約。"""

    _WITH_COMMENT = "            # TODO 改用 Get-ChildItem -Recurse -Filter *.ps1 -File\n"

    def test_strip_line_comments_is_idempotent(self) -> None:
        for label, text in (
            ("real step", _real_step()),
            ("with comment", _real_step() + self._WITH_COMMENT),
            ("trailing newlines", "a\n\n"),
        ):
            with self.subTest(case=label):
                once = strip_line_comments(text)
                self.assertEqual(strip_line_comments(once), once)

    def test_anchors_agree_on_raw_and_precomment_stripped_input(self) -> None:
        """呼叫端不論餵原文或餵自己剝過註解的文字，三錨讀數必須相同——這是
        「一組 EXPECTED_* 服務三份呼叫端」在機械上成立的充要條件。"""
        for label, raw in (
            ("real step", _real_step()),
            ("real step + comment mentioning the cmdlet", _real_step() + self._WITH_COMMENT),
        ):
            with self.subTest(case=label):
                pre = strip_line_comments(raw)
                self.assertEqual(ci_fixed_trees(raw), ci_fixed_trees(pre))
                self.assertEqual(
                    ci_scan_statement_count(raw), ci_scan_statement_count(pre)
                )
                self.assertEqual(ci_gci_call_count(raw), ci_gci_call_count(pre))


class TestPositionalParameterEvasion(unittest.TestCase):
    """R57 實測的逃逸手法：`-Path` 是位置參數，省略後 R56 兩錨皆盲。"""

    def test_legacy_anchors_are_blind_to_positional_form(self) -> None:
        """對照組：舊錨對位置參數形態的第 5 棵樹**完全無感**（樹集合不變、
        計數不變）——這正是 R56 round 7 註解「不論路徑長什麼樣，多一棵樹必紅」
        為假宣稱的機械證據。"""
        mutated = _real_step() + _POSITIONAL_EVASION
        self.assertEqual(
            set(re.findall(_LEGACY_TREE_RE, mutated)),
            {"tools", "AutoClaude/tools", "AISDLC_SDD/scripts"},
        )
        self.assertEqual(len(re.findall(_LEGACY_COUNT_RE, mutated)), 4)

    def test_new_tree_anchor_catches_positional_form(self) -> None:
        self.assertIn("docs/scripts", ci_fixed_trees(_real_step() + _POSITIONAL_EVASION))

    def test_new_count_anchor_catches_positional_form(self) -> None:
        self.assertEqual(
            ci_scan_statement_count(_real_step() + _POSITIONAL_EVASION),
            EXPECTED_CI_SCAN_STATEMENTS + 1,
        )


class TestOtherEvasionForms(unittest.TestCase):
    """R56 round 7 已處理的形態（引號界定 / Join-Path 計算式）不得因 R57 換錨而退化。"""

    def test_count_anchor_catches_quoted_path_form(self) -> None:
        mutated = _real_step() + (
            '            $files += @(Get-ChildItem -Path "docs/scripts" '
            "-Recurse -Filter *.ps1 -File)\n"
        )
        self.assertEqual(
            ci_scan_statement_count(mutated), EXPECTED_CI_SCAN_STATEMENTS + 1
        )

    def test_count_anchor_catches_computed_path_form(self) -> None:
        mutated = _real_step() + (
            '            $files += @(Get-ChildItem -Path (Join-Path ".github" "scripts") '
            "-Recurse -Filter *.ps1 -File)\n"
        )
        self.assertEqual(
            ci_scan_statement_count(mutated), EXPECTED_CI_SCAN_STATEMENTS + 1
        )

    def test_tree_anchor_does_not_capture_the_path_switch_itself(self) -> None:
        """`-` 在字元類裡，抽取式若允許 capture 以 `-` 起頭就會把 `-Path` 自己
        當成樹名抓進來（偽陽性）。"""
        self.assertNotIn("-Path", ci_fixed_trees(_real_step()))

    def test_tree_anchor_ignores_removal_of_ps1_filter(self) -> None:
        """計數錨綁的是 `.ps1` 掃描語句；把 `-Filter *.ps1` 改掉＝不再是同一個
        掃描面，必須被計數變化揭露（而非靜默維持 4）。"""
        mutated = _real_step().replace("-Filter *.ps1 -File", "-Filter *.psm1 -File", 1)
        self.assertEqual(
            ci_scan_statement_count(mutated), EXPECTED_CI_SCAN_STATEMENTS - 1
        )


"""R57 四方複審 ARCH-01 / QA-R57-01 實測到的參數形態逃逸樣本。

括號內記錄 R57 當下「前兩條錨（樹抽取 + `-Recurse -Filter *.ps1 -File` 尾巴）」
的實測反應，僅供理解為何需要第三條錨；斷言本身只要求「三錨合起來必紅」與
「cmdlet 計數錨必紅」，不把前兩錨的盲點寫死成契約（未來若有人把前兩錨補強，
這裡不該因此翻紅）。
"""
_FORM_EVASIONS = {
    # 前兩錨全綠逃逸（ARCH-01 V2）：filter 自身加引號，尾巴 regex 的 `\*\.ps1` 抓不到
    "V2 quoted path + quoted filter": (
        'Get-ChildItem -Path "docs/scripts" -Recurse -Filter "*.ps1" -File'
    ),
    # 前兩錨全綠逃逸（ARCH-01 V5）：`gci` 是 Get-ChildItem 的內建別名
    "V5 gci alias + quoted filter": (
        'gci -Path "docs/scripts" -Recurse -Filter "*.ps1" -File'
    ),
    # 前兩錨全綠逃逸（ARCH-01 V6）：`-Include` 取代 `-Filter`，配引號路徑避開樹抽取式
    "V6 -Include instead of -Filter": (
        'Get-ChildItem -Path "docs/scripts" -Recurse -Include *.ps1 -File'
    ),
    # 前兩錨全綠逃逸（ARCH-01 V7）：Join-Path 計算式路徑＋引號 filter，
    # 與該 step 既有第 4 棵樹同構，照抄最自然
    "V7 Join-Path computed + quoted filter": (
        'Get-ChildItem -Path (Join-Path "docs" "scripts") -Recurse -Filter "*.ps1" -File'
    ),
    # 前兩錨全綠逃逸（QA-R57-01）：位置參數 ＋ `-Filter` 寫在 `-Recurse` 前；
    # PowerShell 具名參數無順序限制，此寫法完全合法
    "QA positional + -Filter before -Recurse": (
        "Get-ChildItem docs/scripts -Filter *.ps1 -Recurse -File"
    ),
    # 前兩錨已抓得到的形態，一併納入迴歸（確認補第三錨沒有讓它們退化）
    "V1 positional, unquoted filter": (
        "Get-ChildItem docs/scripts -Recurse -Filter *.ps1 -File"
    ),
    "V3 quoted path, unquoted filter": (
        'Get-ChildItem -Path "docs/scripts" -Recurse -Filter *.ps1 -File'
    ),
    "V4 -File before -Filter": (
        "Get-ChildItem -Path docs/scripts -Recurse -File -Filter *.ps1"
    ),
    # R57 round 2 ARCH-01 實測的大小寫逃逸（加 re.IGNORECASE 前三錨全綠）：
    # PowerShell 的 cmdlet 名、別名與參數名一律不分大小寫
    "R2 lowercase cmdlet + lowercase params": (
        "get-childitem docs/scripts -recurse -filter *.ps1 -file"
    ),
    "R2 GCI uppercase alias": (
        'GCI -Path "docs/scripts" -Recurse -Filter *.ps1 -File'
    ),
    "R2 Dir capitalised alias": (
        "Dir docs/scripts -Recurse -Filter *.ps1 -File"
    ),
    "R2 GET-CHILDITEM all caps": (
        "GET-CHILDITEM DOCS/SCRIPTS -RECURSE -FILTER *.PS1 -FILE"
    ),
    # R57 round 3 QA-R57R3-01：SSOT docstring 的「已實測涵蓋」清單列了 `ls` 別名，
    # 但本表原本沒有 `ls` 樣本——「逐條釘住」的宣稱與實況脫節（同輪反覆抓的類別）。
    # 補樣本而非從 docstring 刪 `ls`：Architect round 3 實測 `ls` 確實會被 cmdlet
    # 錨命中（RED），該宣稱本身為真，缺的只是常駐樣本。
    "R3 ls alias": "ls docs/scripts -Recurse -Filter *.ps1 -File",
}

# 三錨皆抓不到的列舉途徑（已實測，屬**已知殘餘風險**而非可修的漏洞）。
# 本表存在的意義：把「不涵蓋」也釘成常駐斷言，未來若有人擴大錨面涵蓋到這些形態，
# 這裡會翻紅並強迫同步更新 `_ci_scan_anchors` docstring 的「已實測不涵蓋」清單，
# 避免文件與實作再度漂移（R57 兩輪都栽在「宣稱涵蓋面」與實況不符）。
_KNOWN_UNCOVERED = {
    "System.IO.Directory::GetFiles": (
        '[System.IO.Directory]::GetFiles("docs/scripts", "*.ps1", "AllDirectories")'
    ),
    "Get-Item wildcard": "Get-Item docs/scripts/*.ps1",
    "Resolve-Path wildcard": "Resolve-Path docs/scripts/*.ps1",
    # R57 round 3 SD-R57R3-03：同族的 `EnumerateFiles` 亦三錨全綠，原本未登記。
    # 「已知不涵蓋」清單漏列，與「涵蓋清單多列」（QA-R57R3-01）是同一枚硬幣的兩面。
    "System.IO.Directory::EnumerateFiles": (
        '[IO.Directory]::EnumerateFiles("docs/scripts", "*.ps1", "AllDirectories")'
    ),
}


def _with_fifth_tree(line: str) -> str:
    return _real_step() + f"            $files += @({line})\n"


class TestParameterFormEvasions(unittest.TestCase):
    """ARCH-01 淨退化修復：對 `_FORM_EVASIONS` 逐條列出的每一種第 5 棵樹寫法，
    掃描面鎖必須翻紅。

    種類數不寫在這裡，一律由 `len(_FORM_EVASIONS)` 生成到失敗訊息內（QA-R57R4-03：
    上一版寫死「8 種」，該表其後成長卻沒人改這行，於是 docstring 自己就是失實宣稱）。"""

    def test_cmdlet_count_anchor_catches_every_measured_form(self) -> None:
        for name, line in _FORM_EVASIONS.items():
            with self.subTest(form=name):
                self.assertEqual(
                    ci_gci_call_count(_with_fifth_tree(line)),
                    EXPECTED_CI_GCI_CALLS + 1,
                    f"cmdlet 計數錨對「{name}」形態的第 5 棵樹無感——此錨不解析參數，"
                    f"失效代表 CI_GCI_CALL_RE 被弱化",
                )

    def test_combined_lock_is_red_for_every_measured_form(self) -> None:
        """三錨合起來（樹集合 / 尾巴計數 / cmdlet 計數）對每種形態至少一條翻紅。"""
        base_trees = ci_fixed_trees(_real_step())
        for name, line in _FORM_EVASIONS.items():
            with self.subTest(form=name):
                mutated = _with_fifth_tree(line)
                red = (
                    ci_fixed_trees(mutated) != base_trees
                    or ci_scan_statement_count(mutated) != EXPECTED_CI_SCAN_STATEMENTS
                    or ci_gci_call_count(mutated) != EXPECTED_CI_GCI_CALLS
                )
                self.assertTrue(
                    red,
                    f"「{name}」形態的第 5 棵樹可全綠逃逸三錨"
                    f"（本表共 {len(_FORM_EVASIONS)} 種形態）",
                )

    def test_known_uncovered_forms_stay_documented_as_uncovered(self) -> None:
        """已實測的殘餘風險：`_KNOWN_UNCOVERED` 列出的非 Get-ChildItem 系列列舉途徑，
        三錨皆無感。此斷言不是在「保護漏洞」，而是把 docstring 的「已實測不涵蓋」清單
        釘住——任一項未來被涵蓋時這裡翻紅，強迫同步改文件（不再有失實的涵蓋面宣稱）。

        項數不寫在這裡（上一版寫「三種」，該表補進 `EnumerateFiles` 後即失實——
        ARCH-R57R4-02），改由 `len(_KNOWN_UNCOVERED)` 生成到失敗訊息。**本方向只鎖
        「錨變強」**；反方向（表變長／docstring 沒跟）由
        `TestDocstringClaimsMatchAnchorTables` 補上，兩者合起來才構成雙向鎖。"""
        base_trees = ci_fixed_trees(_real_step())
        for name, line in _KNOWN_UNCOVERED.items():
            with self.subTest(form=name):
                mutated = _with_fifth_tree(line)
                msg = (
                    f"「{name}」已被三錨之一涵蓋（_KNOWN_UNCOVERED 現有 "
                    f"{len(_KNOWN_UNCOVERED)} 項）——請先同步 {_ci_scan_anchors.__name__} "
                    f"docstring 的「已實測不涵蓋」清單，再把該項從本表移除"
                )
                self.assertEqual(ci_fixed_trees(mutated), base_trees, msg)
                self.assertEqual(
                    ci_scan_statement_count(mutated), EXPECTED_CI_SCAN_STATEMENTS, msg
                )
                self.assertEqual(ci_gci_call_count(mutated), EXPECTED_CI_GCI_CALLS, msg)


# ---------------------------------------------------------------------------
# docstring ↔ 樣本表 雙向同步鎖（R57 round 4 ARCH-R57R4-02 / QA-R57R4-03）
# ---------------------------------------------------------------------------
# WHY：上一版只有「錨變強 → 翻紅」這**一個方向**的鎖
# （`TestParameterFormEvasions.test_known_uncovered_forms_stay_documented_as_uncovered`），
# 對「常數表變長、docstring 沒跟」完全無感——而該方向的漂移**已經發生**：
# `_KNOWN_UNCOVERED` 補進 `EnumerateFiles` 後，SSOT docstring 仍寫「…這三種」，
# 下一輪審查者讀 docstring 會以為殘餘逃逸面只有三種、據此判斷已收斂到可接受，
# 實際比宣稱多一種。這是 R57 反覆在抓的「涵蓋面假宣稱」在同一檔內第四次復發，
# 只是方向變成「不涵蓋清單少列」（見帳本 DEF-101-501 的 R58 backlog 清單）。
# 故本節把兩張樣本表與 docstring 的對應關係鎖成**雙向**：任一邊單獨變動即翻紅。
#
# 反寫死數字設計：docstring 不再出現「這三種」這類中文數字，項數改由 `[UNCOVERED]`
# 標記行的行數表達；本節失敗訊息一律以 `len(...)` 生成，故不可能過期。
_SSOT_DOC = _ci_scan_anchors.__doc__ or ""
_DOC_COVERED_HEAD = "已實測涵蓋"
_DOC_UNCOVERED_HEAD = "已實測**不**涵蓋"
_DOC_NOT_EXHAUSTIVE_HEAD = "未窮舉："
# 「不涵蓋」逐項行的機械標記（散文裡提到它時一律加反引號包起來，故 `startswith` 判準
# 不會把說明文字誤當清單項；`test_uncovered_marker_ignores_prose_mention` 釘住此點）。
_DOC_UNCOVERED_ITEM = "[UNCOVERED]"
_BACKTICKED_RE = re.compile(r"`([^`]+)`")
# 樣本行裡的 PowerShell 參數名。`-` 必須前接空白或行首：否則 `get-childitem` 的
# `-childitem` 會被當成參數名（實測），把 cmdlet 名的後半污染進參數集合。
_PARAM_IN_LINE_RE = re.compile(r"(?:(?<=\s)|^)(-[A-Za-z]+)", re.MULTILINE)
_PARAM_TOKEN_RE = re.compile(r"-[A-Za-z]+")


def _doc_section(head: str, next_head: str) -> str:
    """取 SSOT docstring 中 `head` 到 `next_head` 之間的段落（含 `head` 行）。

    標題缺失、不唯一，或**不在行首**時一律直接 AssertionError：docstring 被改寫時
    本鎖必須**大聲失敗**，而不是靜默退化成「段落抽錯／抽到空字串、什麼都沒檢查」的假綠。

    行首要求不是潔癖，是實測過的假綠來源：本鎖開發過程中一次編輯意外吃掉
    `EnumerateFiles` 項與 `未窮舉：` 之間的換行，兩行黏成一行後 `index(next_head)`
    仍能切在行中間，項數照樣算到 4、全部斷言照樣綠——docstring 已被弄壞卻零訊號。
    加上行首判準後同一情形立刻翻紅（已實測）。
    """
    for marker in (head, next_head):
        found = _SSOT_DOC.count(marker)
        assert found == 1, (
            f"{_ci_scan_anchors.__name__} docstring 的「{marker}」標題出現 {found} 次"
            f"（需恰好 1 次）——docstring 結構已變動致本鎖無法定位段落，請同步修本鎖"
        )
        at = _SSOT_DOC.index(marker)
        assert at == 0 or _SSOT_DOC[at - 1] == "\n", (
            f"{_ci_scan_anchors.__name__} docstring 的「{marker}」標題不在行首"
            f"（前一字元為 {_SSOT_DOC[at - 1]!r}）——段落邊界會切在行中間而讓本鎖假綠"
        )
    return _SSOT_DOC[_SSOT_DOC.index(head) : _SSOT_DOC.index(next_head)]


def _doc_uncovered_items() -> list[str]:
    """SSOT docstring「已實測不涵蓋」段落內的逐項標記行（去掉標記前綴）。"""
    section = _doc_section(_DOC_UNCOVERED_HEAD, _DOC_NOT_EXHAUSTIVE_HEAD)
    return [
        line.strip()[len(_DOC_UNCOVERED_ITEM) :].strip()
        for line in section.split("\n")
        if line.strip().startswith(_DOC_UNCOVERED_ITEM)
    ]


def _uncovered_doc_token(key: str) -> str:
    """由 `_KNOWN_UNCOVERED` 的 key 機械推導「docstring 必須出現的識別字樣」。

    `System.IO.Directory::GetFiles` → `GetFiles`、`Get-Item wildcard` → `Get-Item`。
    刻意用推導而非另寫一張 key→字樣對照表：對照表會是**第三份**可漂移的清單，
    新增第 5 項卻忘記登記時就又退回單向鎖——那正是本節要修的病。
    """
    return key.split("::")[-1].split()[0]


def _doc_covered_cmdlet_spellings() -> set[str]:
    """docstring「已實測涵蓋」段落宣稱的 cmdlet／別名拼法（反引號內、逐字比對）。"""
    section = _doc_section(_DOC_COVERED_HEAD, _DOC_UNCOVERED_HEAD)
    return {t for t in _BACKTICKED_RE.findall(section) if CI_GCI_CALL_RE.fullmatch(t)}


def _doc_covered_param_names() -> set[str]:
    """docstring「已實測涵蓋」段落宣稱的參數名（正規化為小寫——PS 不分大小寫）。"""
    section = _doc_section(_DOC_COVERED_HEAD, _DOC_UNCOVERED_HEAD)
    return {
        t.lower() for t in _BACKTICKED_RE.findall(section) if _PARAM_TOKEN_RE.fullmatch(t)
    }


def _sample_cmdlet_spellings() -> set[str]:
    return {s for line in _FORM_EVASIONS.values() for s in CI_GCI_CALL_RE.findall(line)}


def _sample_param_names() -> set[str]:
    return {
        p.lower() for line in _FORM_EVASIONS.values() for p in _PARAM_IN_LINE_RE.findall(line)
    }


class TestDocstringClaimsMatchAnchorTables(unittest.TestCase):
    """SSOT docstring 的涵蓋面宣稱 ↔ 本檔兩張樣本表，**雙向**鎖住（WHY 見上方註解）。

    已實測涵蓋（本鎖會翻紅的漂移）：`_KNOWN_UNCOVERED` 增／減一項而 docstring 沒跟、
    docstring 增／減一項而該表沒跟、`_FORM_EVASIONS` 引入新的 cmdlet 拼法（含大小寫
    變體、新別名）或新的參數名而 docstring 的涵蓋清單沒跟，以及反向的「docstring 多列
    一種拼法／參數名卻無對應樣本」（＝未經實測的宣稱）。
    已實測**不**涵蓋：新增樣本若只是既有拼法＋既有參數名的重新排列（例如再加一種
    參數順序），本鎖無訊號——那類樣本不擴大 docstring 這兩個維度的宣稱面，刻意不鎖，
    以免每加一個迴歸樣本就得改文件。
    未窮舉：docstring 的散文描述（如「任意順序」「任一大小寫」）無法機械核對其真偽，
    本鎖只核對「清單型」宣稱的**成員與項數**，不核對散文語意。
    """

    def test_uncovered_item_count_matches_the_table(self) -> None:
        """項數對齊——這是上一版缺的那個方向（常數表變長、docstring 沒跟）。"""
        items = _doc_uncovered_items()
        self.assertEqual(
            len(items),
            len(_KNOWN_UNCOVERED),
            f"{_ci_scan_anchors.__name__} docstring 的「已實測不涵蓋」列了 {len(items)} "
            f"項，_KNOWN_UNCOVERED 有 {len(_KNOWN_UNCOVERED)} 項——"
            f"docstring 列：{items}；表內識別字樣："
            f"{sorted(_uncovered_doc_token(k) for k in _KNOWN_UNCOVERED)}",
        )

    def test_every_table_entry_is_named_in_the_docstring(self) -> None:
        """表→docstring 方向：每個常駐樣本都必須在 docstring 的不涵蓋清單裡具名。"""
        items = _doc_uncovered_items()
        for key in _KNOWN_UNCOVERED:
            with self.subTest(form=key):
                token = _uncovered_doc_token(key)
                self.assertTrue(token, f"「{key}」推導不出識別字樣，key 命名需可推導")
                self.assertTrue(
                    any(token in item for item in items),
                    f"_KNOWN_UNCOVERED 的「{key}」（識別字樣 {token!r}）未出現在 "
                    f"{_ci_scan_anchors.__name__} docstring 的「已實測不涵蓋」清單"
                    f"{items}——殘餘逃逸面比 docstring 宣稱的多，屬涵蓋面假宣稱",
                )

    def test_every_docstring_item_is_backed_by_a_table_entry(self) -> None:
        """docstring→表 方向：文件列了卻無常駐樣本的「不涵蓋」項＝未經實測的宣稱。"""
        tokens = sorted(_uncovered_doc_token(k) for k in _KNOWN_UNCOVERED)
        for item in _doc_uncovered_items():
            with self.subTest(item=item):
                self.assertTrue(
                    any(t in item for t in tokens),
                    f"docstring 宣稱不涵蓋「{item}」，但 _KNOWN_UNCOVERED 無對應樣本"
                    f"（表內識別字樣：{tokens}）——該宣稱沒有常駐斷言撐著",
                )

    def test_covered_cmdlet_spellings_match_the_sample_table(self) -> None:
        """涵蓋清單的 cmdlet／別名拼法與樣本表必須集合相等（雙向）。"""
        doc, sample = _doc_covered_cmdlet_spellings(), _sample_cmdlet_spellings()
        self.assertEqual(
            doc,
            sample,
            f"docstring 涵蓋清單的 cmdlet 拼法與 _FORM_EVASIONS 樣本不一致："
            f"樣本有而文件沒列 {sorted(sample - doc)}；文件列了而無樣本 "
            f"{sorted(doc - sample)}（樣本表共 {len(_FORM_EVASIONS)} 種形態）",
        )

    def test_covered_parameter_names_match_the_sample_table(self) -> None:
        """涵蓋清單的參數名與樣本表必須集合相等（大小寫正規化後，雙向）。"""
        doc, sample = _doc_covered_param_names(), _sample_param_names()
        self.assertEqual(
            doc,
            sample,
            f"docstring 涵蓋清單的參數名與 _FORM_EVASIONS 樣本不一致："
            f"樣本有而文件沒列 {sorted(sample - doc)}；文件列了而無樣本 "
            f"{sorted(doc - sample)}",
        )

    def test_uncovered_marker_ignores_prose_mention(self) -> None:
        """散文裡提到標記字樣時一律加反引號，故不會被 `startswith` 誤收成清單項——
        否則「解釋這個鎖怎麼運作」的說明文字自己就會把項數撐大而假綠。"""
        self.assertNotIn(
            _DOC_UNCOVERED_ITEM,
            _doc_uncovered_items(),
            "有清單項的內容恰為標記字樣本身，抽取邏輯疑似把散文行也收進來了",
        )
        for item in _doc_uncovered_items():
            with self.subTest(item=item):
                self.assertTrue(item, "抽到空的清單項——標記行後面沒有內容")


# ---------------------------------------------------------------------------
# 呼叫端鎖（R57 四方複審 ARCH-02）
# ---------------------------------------------------------------------------
# WHY：A2 把 R56 三份逐字複本收斂成本 SSOT，但沒有任何測試強制「三份必須用 SSOT」
# ——Architect 實測把 test_ps1_bom.py 的 import 換回自寫舊正則，558 支測試 rc=0 全綠
# 零訊號，收斂等於把三個弱鎖換成一個沒有強制力的弱鎖。本節比照本 repo 既有慣例
# （test_platform_utils_dedup.py::test_definition_exists_only_in_platform_utils、
# AISDLC_SDD/scripts/tests/test_sanitize_component_callsite_frozen_versions.py）補上。
#
# 反繞過設計（QA-R57-02 教訓：姊妹鎖 test_find_git_bash_parity.py 的呼叫端鎖被「尾隨
# 行內註解」繞過）：本鎖全程走 `ast`，不做文字 regex 比對。Python 的 `ast.parse` 在
# 建樹時即丟棄註解，字串字面值也永遠不會變成 ImportFrom/Call 節點，故「把 import 或
# 呼叫留在註解／字串裡」在結構上無法滿足本鎖——下方
# `test_lock_is_immune_to_comment_or_string_only_wiring` 以合成原始碼證明之。
_SSOT_MODULE = "_ci_scan_anchors"
_SSOT_EXPORTS = frozenset(
    {
        "EXPECTED_CI_GCI_CALLS",
        "EXPECTED_CI_SCAN_STATEMENTS",
        "ci_fixed_trees",
        "ci_gci_call_count",
        "ci_scan_statement_count",
    }
)
_SSOT_FUNCS = frozenset(n for n in _SSOT_EXPORTS if n.startswith("ci_"))
# 呼叫端清單（份數即鎖）：新增第 4 份時 roster 測試會翻紅，強迫一併登記。
_SSOT_CALLERS = ("test_ps1_bom.py", "test_ps51_compat.py", "test_smoke_ci_sync.py")
_TESTS_DIR = Path(__file__).resolve().parent
# 「這份測試在鎖 root-infra-ci.yml 第 2 道掃描面」的辨識標記（該 step 的 name）。
_CI_STEP_MARKER = "pwsh 語法解析"
# 自寫正則的判別特徵：字面值同時含 cmdlet 名與 regex 語法標記。
# （test_ps51_compat.py 有 `Get-ChildItem | ? Name -eq 'x'` 這類 PS 樣本字串，
#   不含下列任一標記，故不會被誤判。）
_REGEX_MARKERS = ("\\s", "\\b", "\\S", "(?", "[A-Za-z", ".*", "\\w")
# 偵測「這個字面值提到 Get-ChildItem 系列」用——直接沿用 SSOT 的 cmdlet 錨（含別名
# 與 IGNORECASE），避免此處自己再寫一份會漂移的 cmdlet 名單。
_CMDLET_NAME_RE = CI_GCI_CALL_RE
# 拼接式正則（`'Get-' + 'ChildItem…'`／f-string）專用的較鬆片段判準：插值部分無法
# 靜態求值，故只要出現 cmdlet 名的任一片段＋regex 標記就算可疑。
_FRAGMENT_RE = re.compile(r"Get-|ChildItem|(?<![\w$.\-])gci(?![\w-])", re.IGNORECASE)


def _static_truth(node: ast.AST) -> bool | None:
    """常數條件的靜態真值（`if False:` → False）；非常數回 None＝兩支都可能執行。"""
    return bool(node.value) if isinstance(node, ast.Constant) else None


def _iter_reachable(node: ast.AST):
    """如 `ast.walk` 但**剪掉靜態不可達分支**。

    R57 round 2 A-R57R2-03(a)：舊版用 `ast.walk` 收集呼叫，於是
    `if False: ci_fixed_trees(step)` 這種死碼呼叫照樣滿足「有實際呼叫」——
    實測把 test_ps1_bom.py 的真呼叫換成自寫正則、只把 SSOT 呼叫留在 `if False:`
    區塊內，本鎖全綠零訊號。
    """
    yield node
    if isinstance(node, ast.If):
        truth = _static_truth(node.test)
        children: list[ast.AST] = [node.test]
        if truth is not False:
            children += node.body
        if truth is not True:
            children += node.orelse
    else:
        children = list(ast.iter_child_nodes(node))
    for child in children:
        yield from _iter_reachable(child)


def _prose_string_nodes(tree: ast.AST) -> set[int]:
    """docstring／裸字串陳述（`ast.Expr` 底下的字串）的 id 集合——那些是散文。"""
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }


def _joined_literal_text(node: ast.AST) -> str:
    """把 `BinOp`／`JoinedStr` 子樹裡的字串字面值**依序無縫接起來**。

    `ast.unparse()` 對 `'Get-' + 'ChildItem\\s+-Path'` 會保留 `' + '` 運算子、對
    f-string 會保留 `{expr}`，兩者都讓 cmdlet 名不再是連續字串而漏抓（實測）；
    改接字面值本身即可還原 `Get-ChildItem…`（f-string 的插值部分無法靜態求值，
    故以 `_FRAGMENT_RE` 這種「片段即算」的較鬆判準搭配 regex 標記使用）。
    """
    return "".join(
        sub.value
        for sub in ast.walk(node)
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
    )


def _looks_like_gci_regex(text: str) -> bool:
    """字面值同時含 cmdlet 名（或別名，皆不分大小寫）與 regex 語法標記。"""
    has_cmdlet = bool(_CMDLET_NAME_RE.search(text))
    return has_cmdlet and any(m in text for m in _REGEX_MARKERS)


def _hand_rolled_gci_patterns(tree: ast.AST) -> list[str]:
    """回傳「自寫 Get-ChildItem 正則」的可疑字面值。

    R57 round 2 A-R57R2-03(b) 擴面（舊版只看兩處**裸 `ast.Constant`**：`re.*()` 的
    引數與 `Assign`/`AnnAssign` 的右側，實測 dict/list 容器內的正則、
    `"Get-" + "ChildItem…"`（BinOp）、f-string（JoinedStr）建構的正則全部逃逸）：
      1. 餵給 `re.*(...)` 的字串字面值，只要含 cmdlet 名（含別名、不分大小寫）就算；
      2. **樹中任何位置**的字串字面值（含容器內），且同時含 cmdlet 名與
         `_REGEX_MARKERS` 之一；
      3. `BinOp`／`JoinedStr` 節點 `ast.unparse()` 後同樣以 (2) 的判準檢查。
    docstring 與裸字串陳述（散文）刻意排除——本檔與呼叫端的說明文字大量提到
    cmdlet 名，納入只會製造偽陽性而無鑑別力（`_prose_string_nodes`）。
    已知不涵蓋（未窮舉，誠實記載）：從檔案／環境變數讀進來的 pattern、
    `chr()`／`"".join()` 之類執行期組字串、`getattr(re, "findall")` 動態取用。
    """
    hits: list[str] = []
    prose = _prose_string_nodes(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "re"
        ):
            for arg in node.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and _CMDLET_NAME_RE.search(arg.value)
                ):
                    hits.append(f"L{node.lineno}: re.* pattern {arg.value[:60]!r}")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in prose
            and _looks_like_gci_regex(node.value)
        ):
            hits.append(f"L{node.lineno}: literal {node.value[:60]!r}")
        elif isinstance(node, (ast.BinOp, ast.JoinedStr)):
            text = _joined_literal_text(node)
            if _FRAGMENT_RE.search(text) and any(m in text for m in _REGEX_MARKERS):
                hits.append(f"L{node.lineno}: built {text[:60]!r}")
    return sorted(set(hits))


def _test_method_calls(tree: ast.AST) -> set[str]:
    """`test_*` 方法內、**靜態可達**位置上被呼叫的裸函式名。"""
    called: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name.startswith("test")
            ):
                continue
            for sub in _iter_reachable(item):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    called.add(sub.func.id)
    return called


def _assert_referenced_names(tree: ast.AST) -> set[str]:
    """出現在 `self.assert*(...)` 引數運算式裡的 identifier。

    R57 round 2 A-R57R2-03(c)：舊版只檢查 identifier 在**檔案任一處**出現過，
    失敗訊息卻寫「未在斷言中引用」——實測「常數只在無關行出現、斷言寫死 4」全綠。
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.startswith("assert")
        ):
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
    return names


def _locks_the_ci_step(source: str) -> bool:
    """這份測試檔是否「以可執行碼鎖 root-infra-ci.yml 第 2 道 step」。

    R57 round 2 SA-R57R2-05：舊判準是「檔案任一處出現字串 `pwsh 語法解析`」（含
    散文與註解），於是未來任何只是在註解裡**提到**該 step 的測試檔都會被 roster
    強拉進來、進而被要求 import 全部 5 個符號並實際呼叫 3 支函式（「提及即被迫
    接線」）；反向則抓不到不寫該字面字串的真呼叫端。改為兩條 AST 判準（任一成立）：
      1. 檔案 `from _ci_scan_anchors import …`（真呼叫端必然如此）；
      2. 檔案有**非散文**的字串字面值（排除 docstring／裸字串陳述）含該 step name
         ——即用它做 regex／切片定位。
    已實測涵蓋：現況 5 個含該字串的檔案中，3 個真呼叫端命中、2 個純散文提及
    （`_ci_scan_anchors.py` 的模組 docstring／`test_ci_scan_anchors.py` 的 `_STEP_RE`）
    不再靠 glob 與檔名巧合排除。
    已知不涵蓋（未窮舉）：把 step name 寫在 assert 訊息裡（非散文位置）仍會被判為
    呼叫端；以及從外部檔案讀入 step name 的動態定位法本判準看不到。
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - 語法壞掉的檔案由別的閘門負責
        return False
    prose = _prose_string_nodes(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _SSOT_MODULE:
            return True
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in prose
            and _CI_STEP_MARKER in node.value
        ):
            return True
    return False


def _ssot_wiring(source: str) -> dict[str, object]:
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == _SSOT_MODULE:
            imported |= {alias.name for alias in node.names}
    return {
        "imported": imported,
        "called": _test_method_calls(tree),
        "names": _assert_referenced_names(tree),
        "hand_rolled": _hand_rolled_gci_patterns(tree),
    }


class TestSsotCallsiteLock(unittest.TestCase):
    """三份呼叫端必須真的用 SSOT，且不得自帶 Get-ChildItem 正則。"""

    def test_every_caller_imports_and_actually_calls_the_ssot(self) -> None:
        for name in _SSOT_CALLERS:
            with self.subTest(caller=name):
                w = _ssot_wiring((_TESTS_DIR / name).read_text(encoding="utf-8"))
                self.assertEqual(
                    _SSOT_EXPORTS - w["imported"], set(),
                    f"{name} 未從 {_SSOT_MODULE} import 全部錨（缺 "
                    f"{sorted(_SSOT_EXPORTS - w['imported'])}）——SSOT 被繞過",
                )
                self.assertEqual(
                    _SSOT_FUNCS - w["called"], set(),
                    f"{name} import 了 SSOT 卻沒實際呼叫 "
                    f"{sorted(_SSOT_FUNCS - w['called'])}——載入不等於接線",
                )
                for const in _SSOT_EXPORTS - _SSOT_FUNCS:
                    self.assertIn(
                        const, w["names"],
                        f"{name} 未在斷言中引用 SSOT 常數 {const}——期望值疑似被寫死",
                    )

    def test_no_caller_hand_rolls_its_own_get_childitem_regex(self) -> None:
        for name in _SSOT_CALLERS:
            with self.subTest(caller=name):
                w = _ssot_wiring((_TESTS_DIR / name).read_text(encoding="utf-8"))
                self.assertEqual(
                    w["hand_rolled"], [],
                    f"{name} 出現自寫的 Get-ChildItem 正則 {w['hand_rolled']}——"
                    f"錨一律走 {_SSOT_MODULE}，否則 R56 的三份複本盲點會復活",
                )

    def test_caller_roster_is_complete(self) -> None:
        """凡是鎖 root-infra-ci.yml 第 2 道掃描面的測試檔，都必須登記進 _SSOT_CALLERS
        並受上面兩條鎖管轄——否則第 4 份呼叫端會靜默逸出。"""
        discovered = {
            p.name
            for p in _TESTS_DIR.glob("test_*.py")
            if p.name != Path(__file__).name
            and _locks_the_ci_step(p.read_text(encoding="utf-8"))
        }
        self.assertEqual(
            discovered, set(_SSOT_CALLERS),
            f"鎖 root-infra-ci.yml 第 2 道的測試檔清單已變動：{sorted(discovered)}"
            f"（登記在案：{sorted(_SSOT_CALLERS)}）——請同步 _SSOT_CALLERS",
        )

    def test_lock_catches_the_three_r2_measured_bypasses(self) -> None:
        """R57 round 2 A-R57R2-03 實測的三個缺口，修好後必須各自留下常駐訊號。

        每個樣本都是「表面上 import 齊、看起來有呼叫」但實質繞過 SSOT 的形狀；
        `_ssot_wiring` 必須在對應欄位上曝露它（呼叫沒進 test_*／自寫正則被抓到／
        常數沒出現在斷言引數）。"""
        head = (
            "import re\n"
            "import unittest\n"
            "from _ci_scan_anchors import (EXPECTED_CI_GCI_CALLS, "
            "EXPECTED_CI_SCAN_STATEMENTS, ci_fixed_trees, ci_gci_call_count, "
            "ci_scan_statement_count)\n"
        )
        dead_code = head + (
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        if False:\n"
            "            ci_fixed_trees(s); ci_gci_call_count(s); "
            "ci_scan_statement_count(s)\n"
            "            _ = (EXPECTED_CI_GCI_CALLS, EXPECTED_CI_SCAN_STATEMENTS)\n"
            "        self.assertEqual(len(re.findall(r'gci\\s+-Path', s)), 4)\n"
        )
        self.assertTrue(
            _SSOT_FUNCS - _ssot_wiring(dead_code)["called"],
            "(a) `if False:` 死碼裡的 SSOT 呼叫仍被當成實際接線",
        )
        for label, body in (
            (
                "(b1) concat-built regex",
                "PAT = 'Get-' + r'ChildItem\\\\s+-Path'\n",
            ),
            (
                "(b2) f-string built regex",
                "CM = 'ChildItem'\nPAT = rf'Get-{CM}\\\\s+-Path'\n",
            ),
            (
                "(b3) regex inside dict literal",
                "PATS = {'tree': r'Get-ChildItem\\\\s+-Path\\\\s+([A-Za-z0-9]+)'}\n",
            ),
            (
                "(b4) alias regex",
                "PAT = r'(?<![\\\\w$.-])gci\\\\s+-Path'\n",
            ),
        ):
            with self.subTest(case=label):
                self.assertNotEqual(
                    _ssot_wiring(head + body)["hand_rolled"], [],
                    f"{label}：自寫的 Get-ChildItem 系列正則未被偵測到",
                )
        hard_coded = head + (
            "class T(unittest.TestCase):\n"
            "    def test_x(self):\n"
            "        _ = (EXPECTED_CI_GCI_CALLS, EXPECTED_CI_SCAN_STATEMENTS)\n"
            "        ci_fixed_trees(s); ci_gci_call_count(s); ci_scan_statement_count(s)\n"
            "        self.assertEqual(ci_gci_call_count(s), 4)\n"
        )
        self.assertNotIn(
            "EXPECTED_CI_GCI_CALLS", _ssot_wiring(hard_coded)["names"],
            "(c) 常數只在無關行出現、斷言寫死數字，仍被判為「在斷言中引用」",
        )

    def test_roster_marker_ignores_prose_only_mentions(self) -> None:
        """SA-R57R2-05：只在註解／docstring 提到該 step name 的檔案不得被拉進 roster；
        真接線（import SSOT）或以字面值定位該 step 的檔案則必須被抓到。"""
        prose = f'"""說明：本檔順帶提到 {_CI_STEP_MARKER} 這個 step。"""\nX = 1\n'
        commented = f"# 沿革：{_CI_STEP_MARKER} step 曾經改過\nX = 1\n"
        by_import = f"from {_SSOT_MODULE} import ci_fixed_trees\n"
        by_literal = f'STEP_RE = r"^ +- name: {_CI_STEP_MARKER}.*?$"\n'
        self.assertFalse(_locks_the_ci_step(prose), "docstring 散文提及不該進 roster")
        self.assertFalse(_locks_the_ci_step(commented), "註解提及不該進 roster")
        self.assertTrue(_locks_the_ci_step(by_import), "import SSOT 必須進 roster")
        self.assertTrue(_locks_the_ci_step(by_literal), "以字面值定位 step 必須進 roster")

    def test_lock_is_immune_to_comment_or_string_only_wiring(self) -> None:
        """QA-R57-02 的繞過手法（把接線留在尾隨註解／字串裡）對本鎖無效。"""
        fake = (
            '"""from _ci_scan_anchors import ci_fixed_trees; ci_fixed_trees(x)"""\n'
            "import re\n"
            "# from _ci_scan_anchors import ci_gci_call_count\n"
            "TREE = re.compile(r'Get-ChildItem\\s+-Path')   # was: ci_fixed_trees\n"
        )
        w = _ssot_wiring(fake)
        self.assertEqual(w["imported"], set())
        self.assertEqual(w["called"] & _SSOT_FUNCS, set())
        self.assertNotEqual(w["hand_rolled"], [])


if __name__ == "__main__":
    unittest.main()
