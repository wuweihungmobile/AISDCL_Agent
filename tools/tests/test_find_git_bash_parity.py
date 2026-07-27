#!/usr/bin/env python3
"""find_git_bash 兩套實作結構等價鎖（R17 DEF-101-236 修復配套）。

背景（Scan-A 掃描實證的兩處真實語意分歧，已於本輪修復）：
  1. 環境變數空值處理：`tools/lib/Find-GitBash.ps1` 舊版對
     `$env:ProgramFiles(x86)` 等環境變數不存在時直接做字串插值，會插出裸路徑
     （如缺變數時 `"${env:ProgramFiles(x86)}\\Git\\bin\\bash.exe"` 變成
     `"\\Git\\bin\\bash.exe"`）仍呼叫 `Test-Path`；
     `tools/integration_gate_core.py::find_git_bash()` 明確 `if not base: continue`
     跳過。PS1 版已改用 `[System.Environment]::GetEnvironmentVariable` + 明確空值
     判斷對齊。
  2. System32 排除鬆緊：PS1 版 regex `-notmatch '\\System32\\'` 要求完整路徑段
     匹配；Python 版原本 `"system32" not in found.lower()` 任意子字串命中即排除
     （較寬鬆，可能誤傷路徑含 "system32" 子字串但非該目錄段的候選）。Python 版
     已改為 `_has_system32_segment()` 依 `PureWindowsPath` 路徑段逐一比對對齊。

本測試**不**在 macOS 上真的執行 PowerShell 版本比對回傳值（環境跑不了 pwsh 也
沒有真實候選路徑可測），改用**靜態文字結構比對**：用正則從兩份原始碼各自抽出
「候選路徑清單的 (環境變數名, 相對路徑片段) 序列」與「System32 排除比對的目標
片語」，斷言兩邊抽出結果相等——抽取式比對手法比照 tools/check_script_parity.py
既有機制（不修改該檔案，本測試獨立成新檔）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
import warnings
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PS1_PATH = _REPO_ROOT / "tools" / "lib" / "Find-GitBash.ps1"
_PY_PATH = _REPO_ROOT / "tools" / "integration_gate_core.py"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import integration_gate_core  # noqa: E402
from _platform_helpers import cut_ps_inline_comment, strip_ps_comments  # noqa: E402

_TESTS_DIR = Path(__file__).resolve().parent
# PowerShell 註解剝除的 SSOT 模組與符號（呼叫端鎖 `TestPsCommentStripperSsotCallsiteLock`
# 以此為準；R57 SA-R57R2-03 收斂前這兩支函式在本檔與 nightly parity 檔各有一份複本）。
_PS_STRIPPER_SSOT_MODULE = "_platform_helpers"
_PS_STRIPPER_SYMBOLS = ("cut_ps_inline_comment", "strip_ps_comments")
# 兩支函式的舊複本名（含底線私有版）——任何檔案重新自帶同名定義即視為複本復發。
_PS_STRIPPER_FORBIDDEN_DEFS = frozenset(
    {"cut_ps_inline_comment", "strip_ps_comments", "_cut_inline_comment", "_strip_ps_comments"}
)


class StripPsCommentsTest(unittest.TestCase):
    """`strip_ps_comments` 自身的鑑別力鎖（QA-R57-02 原坑：只剝整行註解，
    把呼叫改成內聯 `Get-Command bash` 並留 `# was: = Find-GitBash` 即全綠）。

    R57 SA-R57R2-03 收斂後本類是**唯一**一份（原本 nightly parity 檔另有一份
    複本，同函式被測兩遍只是把同一個盲點抄兩遍）；nightly 側錨點所依賴的行為由
    本類與 `StripPsCommentsBoundaryTest` 一併守護。
    """

    def test_strips_trailing_inline_comment(self) -> None:
        self.assertEqual(
            strip_ps_comments("$x = (Get-Command bash).Source  # was: = Find-GitBash"),
            "$x = (Get-Command bash).Source",
        )
        # nightly parity 側原本自帶的同語意樣本（收斂時併入，不讓覆蓋面淨減）
        self.assertEqual(
            strip_ps_comments("$dummy = 1   # TODO -WakeToRun 之後補回"), "$dummy = 1"
        )

    def test_strips_whole_line_and_block_comments(self) -> None:
        self.assertEqual(
            strip_ps_comments("  # Find-GitBash\n<#\nFind-GitBash\n#>\n$x = 1"), "$x = 1"
        )
        self.assertEqual(
            strip_ps_comments("  # -WakeToRun\n<#\n-WakeToRun\n#>\n$x = 1"), "$x = 1"
        )

    def test_keeps_hash_inside_string_literals(self) -> None:
        for src in ('$p = "seg\\#path"', "$p = 'a#b'", '$p = "a#b" + "c"'):
            with self.subTest(src=src):
                self.assertEqual(strip_ps_comments(src), src)

    def test_keeps_here_string_body_verbatim(self) -> None:
        for anchor in ("Find-GitBash", "-WakeToRun"):
            with self.subTest(anchor=anchor):
                src = f'$s = @"\n# not a comment {anchor}\n"@\n$y = 2  # gone'
                self.assertEqual(
                    strip_ps_comments(src), f'$s = @"\n# not a comment {anchor}\n"@\n$y = 2'
                )


class StripPsCommentsBoundaryTest(unittest.TestCase):
    """R57 round 2 A-R57R2-02／R57R2-QA-01 的回歸鎖：兩處「不具引號感知」的
    fail-open——一行普通字串以 `@"` 收尾即誤開 here-string、`<#…#>` 用 DOTALL 正則
    盲剝——都會讓其後的**尾隨註解不再被剝除**，於是「把功能碼刪掉、只在註解留錨點
    字樣」的繞過原封不動復活（QA 實測：注入後 `Ran 10 tests / OK`）。

    這些是 latent（137 支 git 追蹤 `.ps1` 內實掃無此形態），故必須用合成樣本鎖；
    每支都以「錨點字樣只留在註解裡」的形狀斷言，紅燈語意＝繞過復活。
    """

    def test_string_literal_ending_with_at_does_not_open_here_string(self) -> None:
        # A-R57R2-02 / QA-01(1)：舊實作 `re.search(r'@(["\'])\s*$', cut)` 只看行尾兩
        # 字元，`"user@"` 即誤開 here-string，而終止條件 `"@` 幾乎不出現 → 吃到檔尾。
        for lit in ('Write-Host "user@"', "$s = 'a@'", 'Write-Host "contact: ops@"'):
            with self.subTest(lit=lit):
                self.assertEqual(
                    strip_ps_comments(f"{lit}\n$y = 1  # Find-GitBash -WakeToRun"),
                    f"{lit}\n$y = 1",
                )

    def test_here_string_misfire_does_not_leak_past_first_line(self) -> None:
        # 舊缺陷的汙染範圍是「其後全部」而非一行——三行註解全存活即為復發訊號。
        src = '$msg = "see docs@"\n$v0 = 0  # c0\n$v1 = 1  # c1\n$v2 = 2  # Find-GitBash'
        self.assertEqual(strip_ps_comments(src), '$msg = "see docs@"\n$v0 = 0\n$v1 = 1\n$v2 = 2')

    def test_real_here_string_openers_still_recognised(self) -> None:
        # 反向：修法不能把真的 here-string 起始判丟（否則內文的 `#` 會被當註解剝掉）。
        for opener in ('$h = @"', "$h = @'", '@"', '$h=@"', 'Foo(@"'):
            with self.subTest(opener=opener):
                delim = opener[-1]
                src = f"{opener}\n# body {delim}stays\n{delim}@\n$y = 1  # gone"
                self.assertEqual(
                    strip_ps_comments(src), f"{opener}\n# body {delim}stays\n{delim}@\n$y = 1"
                )

    def test_block_comment_markers_inside_strings_are_not_stripped(self) -> None:
        # QA-01(3)：舊 `re.sub(r"<#.*?#>", "", text, DOTALL)` 不具引號感知，
        # `$x = "<# … #>"` 字串內容被吃掉、`$a = "<#"` 起更會讓功能碼整行靜默消失。
        self.assertEqual(
            strip_ps_comments('$x = "<# not a comment #>"\n$y = 2'),
            '$x = "<# not a comment #>"\n$y = 2',
        )
        self.assertEqual(
            strip_ps_comments('$a = "<#"\n$b = 1\n$c = Find-GitBash'),
            '$a = "<#"\n$b = 1\n$c = Find-GitBash',
        )

    def test_inline_block_comment_is_stripped_but_code_kept(self) -> None:
        self.assertEqual(strip_ps_comments("$a = 1 <# Find-GitBash #> + 2"), "$a = 1  + 2")

    def test_comment_after_closing_bracket_or_quote_is_stripped(self) -> None:
        """R57 round 3 SD-R57R3-01：`)` `}` `]` `"` `'` 之後的 `#` 必須被視為註解。

        這五個收尾字元原本不在 `_PS_COMMENT_LEAD` 內，於是「以它們結尾的功能碼 +
        尾隨註解」整段原樣保留 → 錨點鎖 fail-open。SD 以 pwsh 7 真 parser 的
        Comment token 取得 ground truth 逐條確認這五種在 PowerShell 中確實都是註解，
        並實證可讓 `test_windows_nightly_anchor_parity.py` 6 支全綠地繞過。
        """
        anchor = "bin\\bash.exe"  # 姊妹鎖實際比對的黑名單字樣之一
        for code in (
            "Write-Host (1)",
            "if ($true) { }",
            "$a[0]",
            'Write-Host "a"',
            "Write-Host 'a'",
        ):
            with self.subTest(code=code):
                out = strip_ps_comments(f"{code}#note {anchor} note")
                self.assertNotIn(
                    anchor, out,
                    f"以 {code[-1]!r} 收尾的功能碼後的尾隨註解未被剝除，錨點鎖 fail-open："
                    f"{out!r}",
                )
                self.assertIn(code, out, f"連功能碼本身都被剝掉了：{out!r}")

    def test_protected_forms_still_not_stripped_after_lead_set_widening(self) -> None:
        """擴大 `_PS_COMMENT_LEAD` 不得傷及原本刻意保護的形態（防修復引入偽陽性）。"""
        for src in ("$c#d", "Write-Host $x#y", 'Write-Host "a#b"', "Write-Host 'a#b'"):
            with self.subTest(src=src):
                self.assertEqual(
                    strip_ps_comments(src), src,
                    "非註解的 `#` 被誤剝——`$#`／`c#`／字串內 `#` 必須原樣保留",
                )

    def test_documented_known_gaps_are_still_the_measured_behaviour(self) -> None:
        """`strip_ps_comments` docstring 的「已知不涵蓋」逐條可執行化。

        清單腐化（宣稱與實作脫節）本身就是本輪 P1 的成因，故把它釘成測試：任何一
        條的實際行為改變，這支就紅，強迫同步更新 docstring。
        """
        # 1 跨行字串：第二行起的引號狀態不追蹤 → 字串內的 `# x` 被誤剝
        self.assertEqual(
            strip_ps_comments('$s = "line1\nline2 # x"\n$y = 1'), '$s = "line1\nline2\n$y = 1'
        )
        # 2 `--%` stop-parsing：其後的 `#` 仍被當註解剝除（刻意不修，理由見 docstring）
        self.assertEqual(
            strip_ps_comments('& cmd --% /c "echo #x"  # gone'), '& cmd --% /c "echo #x"'
        )
        # 3 `<#` 位於未閉合字串內時不被視為區塊起始
        self.assertEqual(strip_ps_comments('$x = "<# oops\n$b = 1'), '$x = "<# oops\n$b = 1')
        # 4 here-string 終止判定較 PowerShell 寬鬆：亦接受縮排後的 `"@`
        self.assertEqual(
            strip_ps_comments('$s = @"\nbody\n  "@\n$y = 1  # gone'),
            '$s = @"\nbody\n  "@\n$y = 1',
        )

    def test_cut_ps_inline_comment_single_line_contract(self) -> None:
        self.assertEqual(cut_ps_inline_comment("$x = 1  # c"), "$x = 1  ")
        self.assertEqual(cut_ps_inline_comment('$p = "a#b"'), '$p = "a#b"')
        self.assertEqual(cut_ps_inline_comment("$c#d"), "$c#d")
        self.assertEqual(cut_ps_inline_comment("Write-Host `# not a comment"),
                         "Write-Host `# not a comment")


class TestPsCommentStripperSsotCallsiteLock(unittest.TestCase):
    """SSOT 呼叫端鎖（R57 SA-R57R2-03）。

    本輪已學到的教訓：**SSOT 沒有呼叫端鎖等於沒有強制力**——R56 把
    `_CI_TREE_RE` 抄三份、R57 又把註解剝除器抄兩份，兩次都是「同一個盲點抄 N 遍」，
    而兩次都沒有任何機械訊號。故：(a) `tools/tests/` 內除 SSOT 模組外，任何檔案
    重新自帶同名函式定義即紅；(b) 已知消費端必須真的 import 且真的呼叫（只 import
    不呼叫＝死 import，鎖零訊號）。

    **已實測涵蓋**（四次注入實驗，每次都精準指名單一測試後以檔案複製還原）：
    `def _strip_ps_comments` 複本、`def strip_ps_comments` 複本、只 import 不呼叫、
    完全不 import。**已知不涵蓋**（未窮舉，不做全備宣稱）：換一個名字重寫一份等價
    邏輯、以 `lambda`／賦值而非 `def` 提供同名物件、把複本放在 `tools/tests/` 以外
    的目錄、以 `exec`／動態 import 迂迴（比照 A-R57R2-03 對 `_ci_scan_anchors`
    呼叫端鎖量到的同類逃逸面）。
    """

    _CONSUMERS = ("test_find_git_bash_parity.py", "test_windows_nightly_anchor_parity.py")

    def test_no_test_module_hand_rolls_its_own_ps_comment_stripper(self) -> None:
        offenders: list[str] = []
        for path in sorted(_TESTS_DIR.glob("*.py")):
            if path.name == f"{_PS_STRIPPER_SSOT_MODULE}.py":
                continue
            with warnings.catch_warnings():
                # 掃描面內既有檔案（如 test_ps51_compat.py 的模組 docstring）帶有
                # 非 raw 字串的 `\s`，`ast.parse` 會噴 DeprecationWarning。那是別的
                # 檔案的既有債、不在本包檔案邊界內，本鎖不因掃描動作替它產生噪音。
                warnings.simplefilter("ignore", DeprecationWarning)
                tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef)
                    and node.name in _PS_STRIPPER_FORBIDDEN_DEFS
                ):
                    offenders.append(f"{path.name}:{node.lineno}:{node.name}")
        self.assertEqual(
            offenders, [],
            f"tools/tests/ 內偵測到 PowerShell 註解剝除器的自帶複本：{offenders}——"
            f"唯一實作應在 {_PS_STRIPPER_SSOT_MODULE}.py，請改為 import。"
            "理由與 _ci_scan_anchors.py 同一判準：複本無法互為交叉校驗（R57 已實證"
            "兩份複本同時帶著同一個 here-string fail-open），只會把盲點抄 N 遍",
        )

    def test_consumers_import_and_actually_call_the_ssot(self) -> None:
        for name in self._CONSUMERS:
            with self.subTest(consumer=name):
                path = _TESTS_DIR / name
                self.assertTrue(path.is_file(), f"消費端名冊已過期：{name} 不存在")
                tree = ast.parse(path.read_text(encoding="utf-8"))
                imported = {
                    alias.asname or alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                    and node.module == _PS_STRIPPER_SSOT_MODULE
                    for alias in node.names
                    if alias.name in _PS_STRIPPER_SYMBOLS
                }
                self.assertTrue(
                    imported,
                    f"{name} 未從 {_PS_STRIPPER_SSOT_MODULE} import 任何註解剝除函式",
                )
                called = {
                    node.func.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                }
                self.assertTrue(
                    imported & called,
                    f"{name} 只 import 未呼叫 {sorted(imported)}——死 import 讓本鎖零訊號",
                )


def _find_line(text: str, needle: str, source_label: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line
    raise AssertionError(f"{source_label} 找不到含 {needle!r} 的行——結構已變動，請同步更新本測試")


def _extract_py_candidates(text: str) -> list[tuple[str, str]]:
    """從 integration_gate_core.py 抽出 [(環境變數名, 相對路徑片段), ...]。"""
    names_line = _find_line(text, "for env_var in (", "integration_gate_core.py")
    names = re.findall(r'"([^"]*)"', names_line)
    assert names, "integration_gate_core.py 抽不出任何環境變數名"

    sub_match = re.search(
        r'sub\s*=\s*"([^"]*)"\s+if\s+env_var\s*==\s*"LocalAppData"\s+else\s*"([^"]*)"',
        text,
    )
    assert sub_match, "integration_gate_core.py 找不到 sub 賦值行——結構已變動，請同步更新本測試"
    # Python 原始碼裡的字面文字是跳脫過的（雙反斜線代表單反斜線），用
    # ast.literal_eval 還原真正的字串值，而非手動 replace 猜測跳脫規則。
    local_appdata_sub = ast.literal_eval('"' + sub_match.group(1) + '"')
    default_sub = ast.literal_eval('"' + sub_match.group(2) + '"')

    return [
        (name, local_appdata_sub if name == "LocalAppData" else default_sub)
        for name in names
    ]


def _extract_ps1_candidates(text: str) -> list[tuple[str, str]]:
    """從 Find-GitBash.ps1 抽出 [(環境變數名, 相對路徑片段), ...]。"""
    names_line = _find_line(text, "envVarName in @(", "Find-GitBash.ps1")
    names = re.findall(r"'([^']*)'", names_line)
    assert names, "Find-GitBash.ps1 抽不出任何環境變數名"

    sub_match = re.search(
        r"\$sub\s*=\s*if\s*\(\$envVarName\s*-eq\s*'LocalAppData'\)\s*\{\s*'([^']*)'\s*\}"
        r"\s*else\s*\{\s*'([^']*)'\s*\}",
        text,
    )
    assert sub_match, "Find-GitBash.ps1 找不到 $sub 賦值行——結構已變動，請同步更新本測試"
    # PowerShell 單引號字串為literal（無跳脫處理），抽出的原文即字面值。
    local_appdata_sub = sub_match.group(1)
    default_sub = sub_match.group(2)

    return [
        (name, local_appdata_sub if name == "LocalAppData" else default_sub)
        for name in names
    ]


def _extract_py_system32_word(text: str) -> str:
    """DEF-101-307 收斂：Python 端已改 import `bash_probe_spec.SYSTEM32_SEGMENT`
    （tools/lib 單一真相源，AISDLC_SDD/scripts/bash_probe.py 既有消費者），不再
    硬編字面值。結構比對改為斷言原始碼確實依賴該常數（防退回硬編字面值），
    實際比對值改由 import 取得 runtime 常數——與舊有「抽字面值」手法功能等價。
    """
    m = re.search(r"part\.lower\(\)\s*==\s*_spec\.SYSTEM32_SEGMENT\b", text)
    assert m, (
        "integration_gate_core.py 的 System32 排除比對未依賴 _spec.SYSTEM32_SEGMENT"
        "——DEF-101-307 收斂後不可退回硬編字面值（如 `part.lower() == \"system32\"`）"
    )
    import bash_probe_spec  # noqa: PLC0415  （tools/lib 已由 `import integration_gate_core` 的 side effect 插入 sys.path）

    return bash_probe_spec.SYSTEM32_SEGMENT


def _extract_ps1_system32_word(text: str) -> str:
    m = re.search(r"-notmatch\s+'([^']*)'", text)
    assert m, "Find-GitBash.ps1 找不到 System32 排除 regex"
    words = re.findall(r"[A-Za-z0-9]+", m.group(1))
    assert words, "Find-GitBash.ps1 的 System32 排除 regex 抽不出任何字面詞"
    return words[0]


def _normalize_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return sorted(pairs)


class TestFindGitBashParity(unittest.TestCase):
    def setUp(self) -> None:
        self.py_text = _PY_PATH.read_text(encoding="utf-8")
        self.ps1_text = _PS1_PATH.read_text(encoding="utf-8")

    def test_source_files_exist(self) -> None:
        """清單本身不得腐化（檔案消失須 fail-loud）。"""
        self.assertTrue(_PY_PATH.is_file(), f"{_PY_PATH} 不存在")
        self.assertTrue(_PS1_PATH.is_file(), f"{_PS1_PATH} 不存在")

    def test_candidate_env_var_and_subpath_sequences_match(self) -> None:
        """兩邊「候選路徑清單」的 (環境變數名, 相對路徑片段) 序列必須一致
        （DEF-101-236 掃描實證分歧修復後的等價鎖，防未來單邊改動又漂移）。"""
        py_candidates = _extract_py_candidates(self.py_text)
        ps1_candidates = _extract_ps1_candidates(self.ps1_text)
        self.assertEqual(
            _normalize_pairs(py_candidates),
            _normalize_pairs(ps1_candidates),
            "候選路徑 (環境變數名, 相對路徑片段) 序列不一致——"
            f"Python={py_candidates} / PS1={ps1_candidates}",
        )

    def test_system32_exclusion_targets_same_segment_name(self) -> None:
        """兩邊排除 WSL System32 佔位所比對的目標片語必須指向同一個字面詞
        （不分大小寫），即使比對手法不同（Python 依路徑段逐一比對，PS1 用
        完整路徑段 regex）——防未來任一邊改成其他詞（如誤植 "system64"）
        而另一邊沒有同步更新。"""
        py_word = _extract_py_system32_word(self.py_text)
        ps1_word = _extract_ps1_system32_word(self.ps1_text)
        self.assertEqual(
            py_word.lower(),
            ps1_word.lower(),
            f"System32 排除目標片語不一致：Python={py_word!r} / PS1={ps1_word!r}",
        )


class TestFindGitBashBehavior(unittest.TestCase):
    """行為驅動測試（R19 修復包 B，DEF-101-242①）：直接呼叫函式斷言真實行為，
    不依賴上方的原始碼結構比對。R19 Scan-A 已 bug-injection 證實：把 find_git_bash()
    呼叫點改回舊版寬鬆判斷（`"system32" not in found.lower()`），上方結構比對測試
    仍全綠——本類別補上呼叫點行為本身的回歸鎖。"""

    def test_has_system32_segment_true_for_full_path_segment(self) -> None:
        self.assertTrue(
            integration_gate_core._has_system32_segment(r"C:\Windows\System32\bash.exe")  # platform-ok: 純字串傳入，非真實檔案路徑
        )
        self.assertTrue(
            integration_gate_core._has_system32_segment(r"C:\WINDOWS\system32\bash.exe"),  # platform-ok: 同上
            "應不分大小寫",
        )

    def test_has_system32_segment_false_for_substring_or_legit_path(self) -> None:
        self.assertFalse(
            integration_gate_core._has_system32_segment(r"C:\Program Files\Git\bin\bash.exe")  # platform-ok: 同上
        )
        self.assertFalse(
            integration_gate_core._has_system32_segment(r"C:\MySystem32Tools\bash.exe"),  # platform-ok: 同上
            "含 'system32' 子字串但非完整路徑段，不應被排除（DEF-101-236 修復標的）",
        )

    def test_find_git_bash_prefers_path_bash_when_not_system32(self) -> None:
        with mock.patch.object(
            integration_gate_core.shutil, "which",
            return_value=r"C:\Program Files\Git\bin\bash.exe",  # platform-ok: mock 回傳值＋下方純字串斷言
        ):
            self.assertEqual(
                integration_gate_core.find_git_bash(), r"C:\Program Files\Git\bin\bash.exe"  # platform-ok: 同上
            )

    def test_find_git_bash_skips_system32_false_positive_and_falls_back_to_env_var(
        self,
    ) -> None:
        """PATH 上的 bash 是 WSL System32 佔位（假陽性）時，應跳過並改查環境變數候選。"""
        with (
            mock.patch.object(
                integration_gate_core.shutil, "which",
                return_value=r"C:\Windows\System32\bash.exe",  # platform-ok: mock 回傳值
            ),
            mock.patch.object(
                integration_gate_core.os, "environ",
                {"ProgramFiles": r"C:\Program Files"},  # platform-ok: mock 環境變數值
            ),
            mock.patch.object(integration_gate_core.Path, "is_file", return_value=True),
        ):
            result = integration_gate_core.find_git_bash()
            # 對齊 find_git_bash() 實作：sub 是含反斜線的單一字面字串（Windows 路徑片段），
            # 在本機（POSIX）以 Path 組合時反斜線不會被當成路徑分隔符切開。
            self.assertEqual(
                result, str(Path(r"C:\Program Files") / "Git\\bin\\bash.exe")  # platform-ok: 純字串斷言，鏡射受測函式的字面組合行為
            )

    def test_find_git_bash_does_not_reject_substring_false_positive_on_path(self) -> None:
        """呼叫點層級的迴歸鎖（R19 Scan-A bug-injection 標的）：PATH 上的 bash 位於
        「含 system32 子字串但非完整路徑段」的合法路徑時，不應被誤排除——若呼叫點
        退化回舊版寬鬆判斷 `"system32" not in found.lower()`，本測試須變紅。"""
        legit_path = r"C:\MySystem32Tools\bash.exe"  # platform-ok: 純字串 mock 值，非真實檔案路徑
        with mock.patch.object(integration_gate_core.shutil, "which", return_value=legit_path):
            self.assertEqual(integration_gate_core.find_git_bash(), legit_path)

    def test_find_git_bash_returns_none_when_nothing_found(self) -> None:
        with (
            mock.patch.object(integration_gate_core.shutil, "which", return_value=None),
            mock.patch.object(integration_gate_core.os, "environ", {}),
        ):
            self.assertIsNone(integration_gate_core.find_git_bash())

    def test_find_git_bash_skips_env_var_candidate_that_does_not_exist_on_disk(self) -> None:
        """R19 四方一審 QA 對抗式 bug-injection 標的：環境變數候選路徑的存在性檢查
        （`cand.is_file()`）若被拿掉，函式會無條件回傳幽靈路徑（磁碟上根本不存在的
        路徑）。上面 `test_find_git_bash_prefers_path_bash_when_not_system32` 等測試
        只驗證了 PATH 檢查那條分支，完全沒保護這條環境變數候選分支——本測試補上：
        PATH 上找不到 bash、環境變數候選路徑存在但磁碟上該檔不存在時，必須回傳
        None，不得回傳幽靈路徑。"""
        with (
            mock.patch.object(integration_gate_core.shutil, "which", return_value=None),
            mock.patch.object(
                integration_gate_core.os, "environ", {"ProgramFiles": r"C:\Program Files"},  # platform-ok: mock 環境變數值
            ),
            mock.patch.object(integration_gate_core.Path, "is_file", return_value=False),
        ):
            self.assertIsNone(integration_gate_core.find_git_bash())

    def test_find_git_bash_continues_to_next_env_var_candidate_when_earlier_one_missing(
        self,
    ) -> None:
        """R19 四方一審 QA 二審對抗式 bug-injection 標的：上一個測試只 mock 了單一
        環境變數候選，QA 二審證實這種寫法無法區分「正確回 None」與「迴圈提前
        中止（第一個候選不存在就直接放棄，不再檢查後續候選）」這兩種行為——兩者在
        單候選情境下觀察到的結果都是 None。改用兩個候選（`ProgramFiles` 磁碟上不
        存在、`LocalAppData` 磁碟上存在）才能區分：Git for Windows per-user 安裝
        預設就落在 `LocalAppData`，若 `ProgramFiles` 剛好沒有 Git、迴圈卻提前中止，
        會誤判「找不到 Git Bash」——這是有實務風險的情境，不只是理論案例。"""
        program_files_cand = str(Path(r"C:\Program Files") / "Git\\bin\\bash.exe")  # platform-ok: 純字串斷言
        local_appdata_cand = str(
            Path(r"C:\Users\me\AppData\Local") / "Programs\\Git\\bin\\bash.exe"  # platform-ok: 純字串斷言
        )

        def _fake_is_file(self: Path) -> bool:
            return str(self) == local_appdata_cand

        with (
            mock.patch.object(integration_gate_core.shutil, "which", return_value=None),
            mock.patch.object(
                integration_gate_core.os, "environ",
                {
                    "ProgramFiles": r"C:\Program Files",  # platform-ok: mock 環境變數值，磁碟上不存在
                    "LocalAppData": r"C:\Users\me\AppData\Local",  # platform-ok: mock 環境變數值，磁碟上存在
                },
            ),
            mock.patch.object(integration_gate_core.Path, "is_file", _fake_is_file),
        ):
            result = integration_gate_core.find_git_bash()
        self.assertNotEqual(
            result, program_files_cand,
            "不應命中 ProgramFiles 候選（磁碟上不存在，mock 已設為 False）",
        )
        self.assertEqual(
            result, local_appdata_cand,
            "ProgramFiles 候選不存在時應繼續檢查下一候選（LocalAppData），"
            "不得提前 return None（Git for Windows per-user 安裝落在 LocalAppData 的常見情境）",
        )


class TestFindGitBashCallSites(unittest.TestCase):
    """R57 新增（A3）：呼叫端**真的有用**這個共用 helper。

    WHY：本檔 R17~R21 累積的 11 支測試，全部只驗 `Find-GitBash.ps1` 自身的行為與
    它跟 `integration_gate_core.py` 的結構等價——**沒有任何一支驗證三支 `.ps1`
    呼叫端真的 dot-source 並呼叫它**。呼叫端只要退回自己內聯寫一段 `Get-Command
    bash` 偵測（也就是 DEF-101-099 當年在 `integration_gate.ps1` 踩過的原坑），
    這 11 支測試依然全綠：helper 完好無損，只是沒人用了。S11 抽共用的整個價值
    在於「單一真相源被實際消費」，而那正是原本零覆蓋的一段。

    另（R56 backlog 項目 4）：「三支呼叫點」這個計數在 `AutoSDD_Defect_Log.md`
    與多處註解反覆出現卻無機械鎖。下方 `test_call_site_registry_matches_repo_scan`
    以 git 追蹤檔全掃比對登記表，增刪任一呼叫端皆必紅（不是下限、是等值）。
    """

    # 三支已知呼叫端（S11 抽共用時的收斂範圍）。
    _CALLERS = (
        "AutoClaude/tools/install_git_hooks.ps1",
        "AISDLC_SDD/scripts/ci-gate.ps1",
        "AISDLC_SDD/scripts/install-hooks.ps1",
    )
    _HELPER_REL = "tools/lib/Find-GitBash.ps1"

    @staticmethod
    def _code_only(text: str) -> str:
        """只認功能碼（比照 macos_smoke_local.sh [7/7] 的 QA-R15-REV-1 訂正：
        註解裡留著舊字樣會讓錨點假陽性）。剝除範圍／已知邊界以
        `_platform_helpers.strip_ps_comments` 的 docstring 為準。區塊註解必須一併
        剝除：R57 實測 `tools/lib/WindowsAppsGuard.ps1` 的 comment-based help 裡
        引用了 `tools/lib/Find-GitBash.ps1` 當「同款模式的既有先例」，只剝行註解
        會把它誤判成第 4 個呼叫端。"""
        return strip_ps_comments(text)

    def _tracked_ps1(self) -> list[str]:
        import subprocess

        out = subprocess.run(
            ["git", "ls-files", "*.ps1"],
            cwd=_REPO_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=True,  # 非 UTF-8 終端下的 mojibake 防護
        ).stdout
        return [ln for ln in out.splitlines() if ln.strip()]

    def test_call_site_registry_matches_repo_scan(self) -> None:
        """登記表 ≡ 全 repo 實況（等值，非下限）：新增第 4 個呼叫端而未登記 → 紅；
        某支呼叫端悄悄不再用共用 helper → 也紅（登記腐化）。"""
        found = set()
        for rel in self._tracked_ps1():
            if rel == self._HELPER_REL:
                continue  # 定義處自身（docstring 範例亦提及函式名）
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")
            if "Find-GitBash" in self._code_only(text):
                found.add(rel)
        self.assertEqual(
            found, set(self._CALLERS),
            f"Find-GitBash 呼叫端實況 {sorted(found)} 與登記 {sorted(self._CALLERS)} "
            "不符——多出者請登記進 `_CALLERS`（並確認它走的是共用 helper 而非自己"
            "重寫偵測），少掉者代表該呼叫端已繞過 S11 抽出的單一真相源",
        )

    def test_each_call_site_dot_sources_and_invokes_helper(self) -> None:
        """逐一驗「dot-source 該檔」＋「呼叫 `Find-GitBash`」兩件事都在功能碼行上。"""
        for rel in self._CALLERS:
            with self.subTest(caller=rel):
                code = self._code_only(
                    (_REPO_ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")
                )
                self.assertRegex(
                    code, r"(?m)^\s*\.\s+\"\$PSScriptRoot[^\"]*Find-GitBash\.ps1\"",
                    f"{rel} 未以 dot-source 載入 tools/lib/Find-GitBash.ps1"
                    "（S11 單一真相源）——呼叫端疑似退回自行內聯偵測",
                )
                self.assertRegex(
                    # 錨在行首賦值式（QA-R57-02）：`=\s*Find-GitBash` 不限位置，
                    # 任何殘留字樣都能滿足；本形態要求「某變數確實被賦成呼叫結果」。
                    code, r"(?m)^\s*\$\w+\s*=\s*Find-GitBash\b",
                    f"{rel} 有 dot-source 卻沒有呼叫 `Find-GitBash`——載入了不用"
                    "等於沒接線",
                )

    def test_call_sites_do_not_reimplement_detection(self) -> None:
        """呼叫端不得自己內聯重寫偵測邏輯。黑名單三個特徵：候選路徑
        `\\Git\\bin\\bash.exe` 字面值、System32 排除比對，以及 `Get-Command bash`
        （DEF-101-099 當年 `integration_gate.ps1` 的原坑寫法，R57 QA-R57-02 實測
        的繞過手法）。R57 round 1 修復後實測三支呼叫端功能碼皆無此三者
        （ci-gate.ps1 的 System32 字樣只在註解裡），故本斷言當下為真且具鑑別力
        ——任何一支複製貼上回舊寫法即紅。"""
        for rel in self._CALLERS:
            with self.subTest(caller=rel):
                code = self._code_only(
                    (_REPO_ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")
                ).lower()
                for needle in (r"bin\bash.exe", "system32", "get-command bash"):
                    self.assertNotIn(
                        needle, code,
                        f"{rel} 功能碼行出現 `{needle}`——疑似內聯重寫 Git Bash 偵測，"
                        "請改為 dot-source tools/lib/Find-GitBash.ps1 呼叫 Find-GitBash",
                    )


if __name__ == "__main__":
    unittest.main()
