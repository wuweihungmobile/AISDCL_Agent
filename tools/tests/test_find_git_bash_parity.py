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

  3. **R60 P10-2（真 parity 缺陷，兩側對同一輸入相反裁決）**：上述第 2 點的靜態鎖
     只比對「兩邊拿哪個**字面詞**去比」，對「用什麼**手法**比」全然盲目。實測
     `C:/Windows/System32/bash.exe`（正斜線寫法；Windows 上與反斜線寫法指向同一個
     檔案）PS 側行內 regex `-notmatch '\\System32\\'` 判**放行**、Python 側
     `PureWindowsPath` 逐段比對判**排除**；且可觸達——`(Get-Command bash).Source` 由
     「PATH 條目 + 檔名」拼成，PATH 條目寫正斜線時 Source 就帶正斜線，修前
     `Find-GitBash` 實測回傳了 WSL 的 bash。PS 側已改為 `Test-HasSystem32Segment`
     逐段比對（Python 側為正解、不動），並新增下方 `TestSystem32VerdictParity`
     **行為表 parity 鎖**。

比對手法（兩層，缺一都有實證盲區）：
  - **靜態文字結構比對**：用正則從兩份原始碼各自抽出「候選路徑清單的 (環境變數名,
    相對路徑片段) 序列」與「System32 排除比對的目標片語」，斷言兩邊抽出結果相等
    ——抽取式比對手法比照 tools/check_script_parity.py 既有機制（不修改該檔案）。
  - **行為表 parity 鎖（R60 P10-2 新增）**：`TestSystem32VerdictParity` 真的起
    PowerShell dot-source `Find-GitBash.ps1` 執行判定，與 Python 側逐筆比對同一組
    輸入。無 PowerShell 引擎的機器（macOS/Linux）誠實 skip；引擎挑選走
    `tools/tests/_ps_engine.py` SSOT（5.1 優先，DEF-101-509 判準）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PS1_PATH = _REPO_ROOT / "tools" / "lib" / "Find-GitBash.ps1"
_PY_PATH = _REPO_ROOT / "tools" / "integration_gate_core.py"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _platform_helpers import cut_ps_inline_comment, strip_ps_comments  # noqa: E402
from _ps_engine import any_engine_available, production_engine  # noqa: E402

# bash 驗活探測：刻意 import test_pre_push_dispatcher 既有的 `_usable_bash()`，不在本檔
# 再寫一份副本——該函式 docstring 已載明它是 AISDLC_SDD/scripts/bash_probe.py 的鏡射，
# 再抄一份就是把同一個盲點多抄一遍（R57 Scan-E 判例）。
from test_pre_push_dispatcher import _usable_bash  # noqa: E402

import integration_gate_core  # noqa: E402

_BASH = _usable_bash()

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

    本輪已學到的教訓：**SSOT 沒有呼叫端鎖等於沒有強制力**——R56 把 CI 掃描樹抽取式
    抄三份、R57 又把註解剝除器抄兩份，兩次都是「同一個盲點抄 N 遍」，而兩次都沒有
    任何機械訊號。故：(a) `tools/tests/` 內除 SSOT 模組外，任何檔案
    重新自帶同名函式定義即紅；(b) 已知消費端必須真的 import 且真的呼叫（只 import
    不呼叫＝死 import，鎖零訊號）。

    **已實測涵蓋**（四次注入實驗，每次都精準指名單一測試後以檔案複製還原）：
    `def _strip_ps_comments` 複本、`def strip_ps_comments` 複本、只 import 不呼叫、
    完全不 import。**已知不涵蓋**（未窮舉，不做全備宣稱）：換一個名字重寫一份等價
    邏輯、以 `lambda`／賦值而非 `def` 提供同名物件、把複本放在 `tools/tests/` 以外
    的目錄、以 `exec`／動態 import 迂迴。
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
            "理由：複本無法互為交叉校驗（R57 已實證兩份複本同時帶著同一個 "
            "here-string fail-open），只會把盲點抄 N 遍",
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
    """R60 P10-2：PS1 側排除判定由行內 regex `-notmatch '\\\\System32\\\\'` 改為
    `Test-HasSystem32Segment` 的逐段比對，故字面值抽取改錨在段比對那一行
    （`$segment.ToLowerInvariant() -eq '…'`）。錨點刻意含 `ToLowerInvariant()`：
    檔內另有 `$envVarName -eq 'LocalAppData'`，只錨 `-eq '…'` 會抽錯詞。"""
    m = re.search(r"ToLowerInvariant\(\)\s*-eq\s+'([^']*)'", text)
    assert m, (
        "Find-GitBash.ps1 找不到 System32 排除段比對（`…ToLowerInvariant() -eq '…'`）"
        "——結構已變動；若又退回行內 regex 子字串比對，那正是 P10-2 的迴歸"
    )
    words = re.findall(r"[A-Za-z0-9]+", m.group(1))
    assert words, "Find-GitBash.ps1 的 System32 排除段抽不出任何字面詞"
    return words[0]


# ── 兩側判定行為表（R60 P10-2）─────────────────────────────────────────────────
# 同一組輸入餵 Python 側與 PowerShell 側，逐筆斷言同判。第二欄是**判準**（不是
# 「現況快照」）：目的是避開 WSL 啟動器 System32 下的 bash.exe，而 Windows 的 `/`
# 與 `\` 等價（實測 Test-Path -LiteralPath 對正斜線寫法亦為 True、指向同一個檔案）
# ⇒ 正斜線／混用寫法都必須排除。
#
# 🔴 為何本表逐列掛 `platform-ok` 而**不**改用 `_platform_helpers.ABS_FAKE_REPO`
# （R60 P10-2；`test_platform_neutral_paths` 的三條指路裡刻意選第三條）：
#   (a) 該常數**依平台分歧**（win32 取 D:/repo 磁碟機形態、其他平台取 /repo）。本表
#       的受測函式（`_has_system32_segment` / `Test-HasSystem32Segment`）語意是
#       「一律以 **Windows** 路徑語意切段」（前者 docstring 明載：即使在非 Windows
#       主機被直接呼叫也要依分隔符正確切段），餵一個在 POSIX 會變成 `/repo` 的常數
#       等於把受測語意換掉。
#   (b) 本表的鑑別力**就長在字面形態上**：`System32` 這個目錄段名、以及 `/`／`\`／
#       混用三種分隔符寫法。`ABS_FAKE_REPO` 既沒有 `System32` 段，在 POSIX 分支也
#       沒有分隔符歧義（三列會塌成同一種形態）⇒ 改用它＝行為表全體失去鑑別力。
#   (c) 這些字面值**不做任何 pathlib join**（純字串餵判定函式後比對 bool），故不觸
#       及 DEF-101-149「D:/repo 在 POSIX 非絕對路徑 → join 語意分歧假紅」那個病灶；
#       同理，`_platform_helpers.py` 自己也是以「win32 分支本來就該寫磁碟機路徑」
#       登記在該鎖的整檔豁免 `_ALLOWED` 內。
#   ⇒ 復核條件（下一輪據此判斷豁免是否仍成立）：若哪天受測函式改成吃 `Path` 物件、
#      或改為依宿主 OS 語意切段，本豁免即失效，必須連同本表一起重新設計。
_SEGMENT_CASES: tuple[tuple[str, bool, str], ...] = (
    # 病灶本體：舊 PS regex 要求 System32 前後皆反斜線 → 判放行；Python 判排除。
    (
        r"C:/Windows/System32/bash.exe",  # platform-ok: 正斜線分隔符即病灶本體
        True, "全正斜線",
    ),
    # `(Get-Command bash).Source` 實測形狀：PATH 條目正斜線 + 拼上的檔名反斜線。
    (
        r"C:/Windows/System32\bash.exe",  # platform-ok: 混用分隔符＝實測 Source 形狀
        True, "混用分隔符",
    ),
    (
        r"C:\Windows\System32\bash.exe",  # platform-ok: 反斜線基準列，舊實作唯一抓到者
        True, "全反斜線",
    ),
    (
        r"C:\WINDOWS\system32\bash.exe",  # platform-ok: 大小寫變體需真實 Windows 目錄名
        True, "大小寫",
    ),
    # 誘餌：含 system32 子字串但非完整段（DEF-101-236 修的偽陽性），不得誤排除。
    (
        r"C:\MySystem32Tools\bash.exe",  # platform-ok: 誘餌需含 system32 子字串但非整段
        False, "誘餌",
    ),
    (
        r"C:\Program Files\Git\bin\bash.exe",  # platform-ok: 陰性對照＝真實 Git 安裝路徑
        False, "真 Git Bash",
    ),
    # 判準邊界（Find-GitBash.ps1 comment-based help 亦記載）：Sysnative 是 32-bit
    # 行程看到的 64-bit System32 別名、其實同一支 WSL bash，兩側一致**不**排除。
    # 本列鎖住「這是已知殘餘盲區」而非「已驗證安全」——哪天要收掉它，本列必須
    # 連同兩側實作一起改，不會有人靜默單邊處理。
    (
        r"C:\Windows\Sysnative\bash.exe",  # platform-ok: Sysnative 別名字面不可替代
        False, "Sysnative 盲區",
    ),
)


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


@unittest.skipUnless(
    any_engine_available(),
    "本機無任何 PowerShell 引擎——無法真的執行 PS 側判定（非 Windows 開發機的誠實 skip）",
)
class TestSystem32VerdictParity(unittest.TestCase):
    """🔴 R60 P10-2 行為表 parity 鎖：兩側對同一組輸入必須逐筆同判。

    WHY 靜態鎖不夠（本檔既有 `test_system32_exclusion_targets_same_segment_name` 的
    盲區）：它只比對「兩邊拿哪個**字面詞**去比」，對「用什麼**手法**比」完全盲目。
    P10-2 實測：兩側字面詞都是 `System32`（該靜態鎖全綠），但 PS 側行內 regex
    `-notmatch '\\\\System32\\\\'` 要求前後皆為反斜線，於是

        輸入 `C:/Windows/System32/bash.exe`
          PS 側 accepts=True（放行）  ／  Python 側 excluded=True（排除）

    ——同一組輸入、相反裁決。而且**可觸達**：`(Get-Command bash).Source` 是「PATH 條目
    + 檔名」拼出來的，PATH 條目以正斜線書寫時 Source 就帶正斜線。實測（PS 5.1，
    `$env:PATH` 設為 `C:/Windows/System32`）得 Source=`C:/Windows/System32\\bash.exe`，
    修前 `Find-GitBash` **回傳了 WSL 的 bash**。

    本類別真的起 PowerShell 執行 `Test-HasSystem32Segment`，不是比對原始碼字面——
    任一側被改壞（如 PS 側退回 `-notmatch`、Python 側退回子字串命中）都必紅。
    """

    _CASE_TABLE_PATH = _PS1_PATH

    def _ps_verdicts(self, cases: tuple[str, ...]) -> dict[str, bool]:
        """起 PowerShell dot-source 真實 helper，回傳 `{輸入: 是否排除}`。"""
        import subprocess
        import tempfile

        for case in cases:
            self.assertNotIn(
                "'", case, "行為表輸入不得含單引號——會破壞下方 PS 單引號字面值產生"
            )
        lines = [f". '{self._CASE_TABLE_PATH.as_posix()}'"]
        for case in cases:
            lines.append(
                f"Write-Output ('V|{case}|' + (Test-HasSystem32Segment '{case}'))"
            )
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "verdicts.ps1"
            script.write_text("\n".join(lines) + "\n", encoding="utf-8")
            proc = subprocess.run(
                [
                    production_engine(), "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script),
                ],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120,
            )
        self.assertEqual(
            proc.returncode, 0,
            f"PowerShell 執行失敗（rc={proc.returncode}）：{proc.stdout}\n{proc.stderr}",
        )
        out: dict[str, bool] = {}
        for line in proc.stdout.splitlines():
            parts = line.split("|")
            if len(parts) != 3 or parts[0] != "V":
                continue
            out[parts[1]] = parts[2].strip() == "True"
        self.assertEqual(
            set(out), set(cases),
            f"PS 側回報的輸入集合與送進去的不符：{sorted(out)}（stdout={proc.stdout!r}）",
        )
        return out

    def test_both_sides_agree_with_the_criterion(self) -> None:
        """逐筆：Python 判定 == PS 判定 == 判準（`expected_excluded`）。"""
        cases = tuple(case for case, _exp, _why in _SEGMENT_CASES)
        ps_verdicts = self._ps_verdicts(cases)
        for case, expected, why in _SEGMENT_CASES:
            with self.subTest(case=case, why=why):
                py = integration_gate_core._has_system32_segment(case)
                self.assertEqual(
                    py, expected,
                    f"Python 側判定與判準不符（{why}）：excluded={py}，應為 {expected}",
                )
                self.assertEqual(
                    ps_verdicts[case], expected,
                    f"PS 側判定與判準不符（{why}）：excluded={ps_verdicts[case]}，"
                    f"應為 {expected}——兩側對同一輸入相反裁決即 P10-2 迴歸",
                )

    def test_find_git_bash_rejects_forward_slash_system32_end_to_end(self) -> None:
        """端到端（不依賴本機真有 WSL）：沙箱造一個 `<tmp>/System32/bash.exe` 假檔，
        PATH 以**正斜線**指向該目錄、並清空三個環境變數候選 ⇒ `Find-GitBash` 必須
        回傳空（找不到），不得回傳那支 System32 bash。

        修前實測形狀：`Find-GitBash` 回傳 `C:/…/System32\\bash.exe`（guard 整條失效）。
        用沙箱假檔而非本機真 WSL bash，是為了讓這條在任何 Windows 機器上都確定性成立。
        """
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            sysdir = Path(td) / "System32"
            sysdir.mkdir()
            (sysdir / "bash.exe").write_bytes(b"MZ fake, never executed")
            fwd = sysdir.as_posix()  # 正斜線寫法（病灶形狀）
            script = Path(td) / "e2e.ps1"
            script.write_text(
                f". '{self._CASE_TABLE_PATH.as_posix()}'\n"
                f"$env:PATH = '{fwd}'\n"
                "$env:ProgramFiles = ''\n"
                "${env:ProgramFiles(x86)} = ''\n"
                "$env:LocalAppData = ''\n"
                "$r = Find-GitBash\n"
                "if ($r) { Write-Output ('R|' + $r) } else { Write-Output 'R|(none)' }\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    production_engine(), "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(script),
                ],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=120,
            )
        self.assertEqual(proc.returncode, 0, f"{proc.stdout}\n{proc.stderr}")
        result = next(
            (ln[2:] for ln in proc.stdout.splitlines() if ln.startswith("R|")), None
        )
        self.assertIsNotNone(result, f"PS 未回報結果：{proc.stdout!r}")
        self.assertEqual(
            result, "(none)",
            "Find-GitBash 回傳了正斜線寫法的 System32 bash（WSL 啟動器）"
            f"：{result!r}——P10-2 迴歸",
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


# ===========================================================================
# R67-C18：tools/integration_gate.{sh,ps1,_core.py} 的本機活體載具
# ===========================================================================
#
# 為何住在本檔（收納契約，非雜物抽屜）：本檔已是 `tools/integration_gate_core.py` 的
# 既有鎖檔（上方 `find_git_bash` 家族即該模組的函式），import 與 `_PY_PATH` 都指著它。
# `DEF-101-561③`（由 `test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 機械強制）
# 要求「把新判準擴充進既有鎖檔」，本節即依該裁決把新判準併進同一模組的既有鎖檔。
# 🔴 R78 ARCH-03 訂正：該棘輪量的已不是**檔數**（R77 退場），而是逐檔行數表的**淨額**
# ——新增檔案只要同一次變更內刪掉等量以上的行就合法，別把舊語意當現行規則照抄。
#
# WHY 這組鎖必須存在（Rule 9 — 鎖意圖而不只鎖行為）：
# 整合層閘門的存在理由是「兩子專案各自綠燈不代表整合綠燈」（[3/5] SDD bridge 整合煙霧、
# [4/5] 回退驗證、[5/5] cc-switch A/B）。但 R67 全庫普查實測：它在整個自動化層**零呼叫端**
# ——唯二執行者是 .github/workflows/macos-compat-ci.yml 與 windows-compat-ci.yml 各一行
# （`bash tools/integration_gate.sh --skip-full` / `./tools/integration_gate.ps1 -SkipFull`），
# 而兩支 compat-CI 因 CI 帳務停擺（DEF-101-081）已多輪未真正執行。
# **雲端是唯一執行者的東西＝實質已死**：閘門本體被改壞在本機任何流程都不會紅。
#
# 三條各自獨立、彼此補不到的缺口：
#   A. 編排語意（`main` / `run_section` / `--skip-full` / 例外處理）——R67 動工前實測
#      `grep -rn "integration_gate_core\.\(main\|sec_\|run_section\|_run_cc\)" tools/tests/
#      AutoClaude/tests/` 為**空輸出**，全庫零測試觸及。這一層的故障模式是「閘門不會變紅」，
#      **實跑健康的 repo 抓不到**（真跑只會全綠，看不出它其實已經不會紅）——R67 注入實測：
#      把 `run_section` 的 `if rc != 0` 改成恆偽後，真閘門 `--skip-full` 仍 rc=0。
#   B. stage 目標存在性——閘門從不執行 ⇒ 它指向的目標被搬走／改名時零訊號。本節刻意
#      **不抄第二份路徑清單**（那正是本 repo 反覆抓到的「N 份複本只改 1 份」），而是攔截
#      `subprocess.run` 取出各 `sec_*` **實際會下的指令**再驗磁碟。Windows 分支
#      （local_ci_gate.ps1）一併攔一次：兩支 compat-CI 一起死了，兩邊都沒人看。
#   C. 薄殼→核心委派**實跑**——兩支薄殼由 tools/check_wrapper_thinness.py 以 sha256 釘選，
#      但 hash 只認「內容有沒有變」，對「內容變了但語意壞掉」（參數沒傳過去、exit code
#      被吞成 0）盲目——注入實測時 hash 鎖確實會紅，但它給的訊息是「請重釘新值」，
#      照做就會把壞掉的語意連同新 hash 一起釘進去。
#
# 與 pre-push 整合閘門 leg 的分工（兩者缺一不可）：
#   · `tools/git-hooks/pre-push` 的整合閘門 leg 只在 push **動到閘門本體**時實跑真閘門
#     （路徑範圍觸發，日常 push 零成本；實測偵測迴圈 0.01s、命中時 +2.24s）。
#   · 本節在**每次根層 push** 隨 `tools/run_root_unittests.py` 執行——抓的是「閘門沒被改，
#     但它指向的東西腐爛了」與「編排語意被改成吞掉失敗」。那兩者路徑觸發永遠看不到。

# stub 核心：把「薄殼到底把什麼交給核心」寫成 JSON 證物，並以環境變數決定 exit code。
_IG_STUB_CORE = """\
import json, os, sys
from pathlib import Path
Path(os.environ["IG_STUB_MARKER"]).write_text(
    json.dumps({"argv": sys.argv[1:], "pythonutf8": os.environ.get("PYTHONUTF8")}),
    encoding="utf-8",
)
raise SystemExit(int(os.environ.get("IG_STUB_RC", "0")))
"""


def _ig_python_shim_dir(tmp: Path) -> str:
    """回傳含名為 `python` 之可執行檔的目錄（薄殼以 `command -v python` 探測）。

    手法對齊 tools/tests/test_pre_push_dispatcher.py::_python_dir——venv 內天然有
    python(.exe)；只有 python3 別名的系統直譯器以 symlink shim 補上，建不了再退回複製。
    """
    exe_dir = Path(sys.executable).parent
    name = "python.exe" if os.name == "nt" else "python"
    if (exe_dir / name).exists():
        return str(exe_dir)
    shim = tmp / "pyshim"
    shim.mkdir(exist_ok=True)
    link = shim / name
    if not link.exists():
        try:
            link.symlink_to(Path(sys.executable))
        except OSError:
            shutil.copy2(sys.executable, link)
    return str(shim)


class _IgRunRecorder:
    """`subprocess.run` 替身：記下 (cmd, cwd) 並回 rc=0，不真的執行任何 stage。"""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.cwds: list[object] = []

    def __call__(self, cmd, **kwargs):  # noqa: ANN001, ANN204
        self.calls.append([str(a) for a in cmd])
        self.cwds.append(kwargs.get("cwd"))
        return subprocess.CompletedProcess(cmd, 0)


class TestIntegrationGateOrchestration(unittest.TestCase):
    """缺口 A：`main()` 編排語意（全庫先前零覆蓋）。

    WHY：這一層的故障模式是「閘門不會變紅」。實跑一次健康的 repo **證明不了**它壞沒壞
    ——真跑只會全綠。唯一能鑑別的手法就是注入一個失敗 stage，看閘門是否照實轉紅。
    """

    def setUp(self) -> None:
        # main() 會寫 os.environ["PYTHONUTF8"]，用 patch.dict 保證測試不汙染行程環境。
        env_patch = mock.patch.dict(os.environ, {}, clear=False)
        env_patch.start()
        self.addCleanup(env_patch.stop)
        # hooks liveness 是 advisory（會 spawn 子行程），與編排語意無關 → 停用求決定性。
        adv = mock.patch.object(integration_gate_core, "_hooks_liveness_advisory", lambda: None)
        adv.start()
        self.addCleanup(adv.stop)

    def _run_main(self, argv: list[str], rcs: dict[str, int]) -> tuple[int, list[str]]:
        """以指定 rc 替換四個 sec_*，回傳 (main 的 rc, 實際被呼叫的 stage 名順序)。"""
        called: list[str] = []

        def _make(name: str):
            def _fn() -> int:
                called.append(name)
                return rcs.get(name, 0)
            return _fn

        with mock.patch.object(integration_gate_core, "sec_autoclaude", _make("autoclaude")), \
                mock.patch.object(integration_gate_core, "sec_sdd", _make("sdd")), \
                mock.patch.object(integration_gate_core, "sec_bridge", _make("bridge")), \
                mock.patch.object(integration_gate_core, "sec_rollback", _make("rollback")):
            rc = integration_gate_core.main(argv)
        return rc, called

    def test_healthy_full_run_executes_all_four_sections_in_order(self) -> None:
        """完整模式：四個 stage 依 [1]→[2]→[3]→[4] 順序全跑、rc=0。

        WHY：順序不是美觀問題——[1]/[2] 是兩子專案各自的完整閘門，先跑它們才能讓
        [3]/[4] 的整合失敗被歸因為「整合層」而非「子專案本身壞了」。
        """
        rc, called = self._run_main([], {})
        self.assertEqual(rc, 0)
        self.assertEqual(called, ["autoclaude", "sdd", "bridge", "rollback"])

    def test_skip_full_runs_only_stage_3_and_4(self) -> None:
        """`--skip-full` 必須恰好略過 [1]/[2]，且**不得**順手略過 [3]/[4]。

        WHY：`--skip-full` 正是兩支 compat-CI 與新接的 pre-push leg 實際使用的模式；
        它若退化成「什麼都不跑」，閘門會以 0 PASS 印出 ✅（下方
        test_all_sections_skipped_is_not_silently_green 一併堵住該形狀）。
        """
        rc, called = self._run_main(["--skip-full"], {})
        self.assertEqual(rc, 0)
        self.assertEqual(called, ["bridge", "rollback"])

    def test_failing_stage_turns_gate_red(self) -> None:
        """任一 stage 非零 → 閘門 rc=1。**本組最核心的一條**。

        WHY：這是「閘門是閘門」的定義。`run_section` 若被改成吞掉 rc，整合層從此永遠
        綠燈，而且因為它本來就沒有本機呼叫端，沒有任何人會發現。
        """
        for broken in ("autoclaude", "sdd", "bridge", "rollback"):
            with self.subTest(stage=broken):
                rc, called = self._run_main([], {broken: 1})
                self.assertEqual(
                    rc, 1,
                    f"stage {broken} 回 rc=1，整合閘門卻回 {rc}——閘門吞掉失敗",
                )
                self.assertIn(broken, called)

    def test_failure_does_not_short_circuit_remaining_sections(self) -> None:
        """前面的 stage 失敗後，後面的 stage 仍必須跑完（逐項收集不中斷）。

        WHY：核心 docstring 與 `run_section` 的註解都明文承諾「逐項收集不中斷，對齊
        收斂前 run_section/Invoke-Section」。若改成 fail-fast，開發者每修一項就得重跑
        整輪（[1]/[2] 是分鐘級），實務上會直接放棄使用這道閘門。
        """
        rc, called = self._run_main([], {"autoclaude": 1})
        self.assertEqual(rc, 1)
        self.assertEqual(called, ["autoclaude", "sdd", "bridge", "rollback"])

    def test_section_exception_counts_as_failure_not_crash(self) -> None:
        """stage 拋例外 → 判 FAIL（rc=1）而非讓整支閘門炸掉。

        WHY：對齊 .ps1 的 Continue 語意（核心 docstring 明載）。例外若直接往外拋，
        呼叫端（pre-push leg / CI step）看到的是 traceback 而非「哪一段失敗」，
        且後續 stage 全部不跑。
        """
        def _boom() -> int:
            raise RuntimeError("stage 內部炸掉")

        with mock.patch.object(integration_gate_core, "sec_autoclaude", _boom), \
                mock.patch.object(integration_gate_core, "sec_sdd", lambda: 0), \
                mock.patch.object(integration_gate_core, "sec_bridge", lambda: 0), \
                mock.patch.object(integration_gate_core, "sec_rollback", lambda: 0):
            rc = integration_gate_core.main([])
        self.assertEqual(rc, 1, "stage 例外必須被判 FAIL，不得靜默視為通過")

    def test_all_sections_skipped_is_not_silently_green(self) -> None:
        """負面斷言：閘門的 PASS 計數必須真的來自跑過的 stage。

        WHY：`--skip-full` 的存在讓「少跑」變成合法狀態，而合法狀態最容易被進一步
        放寬成「什麼都不跑也算通過」。這裡以 PASS 段數把「跑了幾段」釘進行為：
        skip-full 模式必須嚴格少於完整模式，且兩者都不得為 0。
        """
        full_counters = {"pass": 0, "skip": 0}
        skip_counters = {"pass": 0, "skip": 0}
        real_run_section = integration_gate_core.run_section

        def _count(counters):
            def _wrapped(label, fn, failures, _c):
                return real_run_section(label, fn, failures, counters)
            return _wrapped

        with mock.patch.object(integration_gate_core, "sec_autoclaude", lambda: 0), \
                mock.patch.object(integration_gate_core, "sec_sdd", lambda: 0), \
                mock.patch.object(integration_gate_core, "sec_bridge", lambda: 0), \
                mock.patch.object(integration_gate_core, "sec_rollback", lambda: 0):
            with mock.patch.object(integration_gate_core, "run_section", _count(full_counters)):
                self.assertEqual(integration_gate_core.main([]), 0)
            with mock.patch.object(integration_gate_core, "run_section", _count(skip_counters)):
                self.assertEqual(integration_gate_core.main(["--skip-full"]), 0)

        self.assertEqual(full_counters["pass"], 4, "完整模式必須有 4 段 PASS")
        self.assertEqual(skip_counters["pass"], 2, "--skip-full 必須仍有 2 段 PASS")
        self.assertGreater(
            full_counters["pass"], skip_counters["pass"],
            "--skip-full 若與完整模式跑一樣多段，代表旗標語意已失效",
        )


class TestIntegrationGateStageTargets(unittest.TestCase):
    """缺口 B：stage 指向的目標必須真的存在於磁碟（雙平台分支都驗）。

    WHY：閘門零呼叫端 ⇒ 目標被搬走／改名時**沒有任何人會執行到那個 FileNotFoundError**。
    本鎖不抄第二份路徑清單，而是攔 `subprocess.run` 取出 sec_* 真正會下的指令再驗磁碟，
    故它跟著實作走：改對了就綠、打錯字就紅，不會有「鎖自己過期」的第三份真相源。
    """

    def _capture(self, fn, *, windows: bool) -> list[tuple[list[str], Path]]:
        rec = _IgRunRecorder()
        with mock.patch.object(
                integration_gate_core.platform_utils, "is_windows", lambda: windows), \
                mock.patch.object(integration_gate_core, "find_git_bash", lambda: "bash"), \
                mock.patch("subprocess.run", rec):
            fn()
        return [(cmd, Path(cwd)) for cmd, cwd in zip(rec.calls, rec.cwds, strict=True)]

    @staticmethod
    def _path_like(arg: str) -> list[str]:
        """挑出「看起來是相對路徑引數」的 token（排除旗標與直譯器本身）。"""
        if arg.startswith("-") or arg == sys.executable:
            return []
        if "/" in arg or arg.endswith((".sh", ".ps1", ".py")):
            return [arg]
        return []

    def test_all_stage_targets_exist_on_disk(self) -> None:
        targets: set[str] = set()
        sections = (
            integration_gate_core.sec_autoclaude,
            integration_gate_core.sec_sdd,
            integration_gate_core.sec_bridge,
            integration_gate_core.sec_rollback,
        )
        for windows in (False, True):
            for fn in sections:
                for cmd, cwd in self._capture(fn, windows=windows):
                    for arg in cmd:
                        for rel in self._path_like(arg):
                            resolved = cwd / rel
                            # as_posix()：str(PurePath) 在 Windows 是反斜線形態，
                            # 這個集合會被印進失敗訊息（且隨時可能被加上正斜線斷言）
                            # ——鍵一律平台中立（R69 P1 同型站點）。
                            targets.add(resolved.relative_to(_REPO_ROOT).as_posix())
                            self.assertTrue(
                                resolved.exists(),
                                f"integration_gate stage 目標不存在：{resolved}"
                                f"（來自指令 {cmd}，cwd={cwd}，windows={windows}）"
                                f"——整合閘門零本機呼叫端，此類腐爛先前零訊號",
                            )
        # 下限釘選：抽取管線被改壞的症狀是「空集合 → 迴圈零圈 → 恆綠」。
        self.assertGreaterEqual(
            len(targets), 5,
            f"只抽到 {len(targets)} 個 stage 目標 {sorted(targets)}——"
            f"抽取管線疑似失效（現況 5：兩子專案 gate 各一 + ps1 + bridge 目錄 + rollback 檔）",
        )

    def test_windows_branch_targets_the_ps1_gate(self) -> None:
        """Windows 分支必須指向 .ps1（而非在兩平台都跑 .sh）。

        WHY：windows-compat-ci 與 macos-compat-ci 同時死亡 ⇒ 兩個平台分支都沒人跑。
        分支若在某次收斂中被壓成單一路徑，Windows 端會去執行 bash 腳本而當場失敗，
        但沒有任何載具會看到。
        """
        cmds = [cmd for cmd, _cwd in self._capture(
            integration_gate_core.sec_autoclaude, windows=True)]
        self.assertTrue(
            any(any(a.endswith("local_ci_gate.ps1") for a in cmd) for cmd in cmds),
            f"Windows 分支未指向 local_ci_gate.ps1：{cmds}",
        )
        posix_cmds = [cmd for cmd, _cwd in self._capture(
            integration_gate_core.sec_autoclaude, windows=False)]
        self.assertTrue(
            any(any(a.endswith("local_ci_gate.sh") for a in cmd) for cmd in posix_cmds),
            f"POSIX 分支未指向 local_ci_gate.sh：{posix_cmds}",
        )


@unittest.skipIf(_BASH is None, "整合閘門薄殼為 bash 腳本，需可用 bash（非 WSL 佔位）")
class TestIntegrationGateShellDelegation(unittest.TestCase):
    """缺口 C：`tools/integration_gate.sh` → 核心的委派**實跑**。

    WHY：薄殼由 check_wrapper_thinness.py 以 sha256 釘選，但 hash 對「內容變了而語意壞掉」
    盲目——它只會要求「請以 --print-hash 取新值同步更新」，照做就把壞語意連同新 hash
    一起釘進去。本鎖在 tmp fake repo 內用真 bash 跑真薄殼＋stub 核心，把薄殼**唯一**該做
    的三件事（傳參數、設 PYTHONUTF8、傳 rc）逐項釘住。
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ig_shell_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        tools = self.tmp / "tools"
        (tools / "lib").mkdir(parents=True)
        shutil.copy(_REPO_ROOT / "tools" / "integration_gate.sh", tools / "integration_gate.sh")
        shutil.copy(
            _REPO_ROOT / "tools" / "lib" / "windowsapps_guard.sh",
            tools / "lib" / "windowsapps_guard.sh",
        )
        (tools / "integration_gate_core.py").write_text(
            _IG_STUB_CORE, encoding="utf-8", newline="\n"
        )
        self.marker = self.tmp / "stub_marker.json"

    def _run(self, args: list[str], stub_rc: int = 0) -> tuple[int, str, str]:
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join(
            [_ig_python_shim_dir(self.tmp), str(Path(_BASH).parent), env.get("PATH", "")]
        )
        env["IG_STUB_MARKER"] = str(self.marker)
        env["IG_STUB_RC"] = str(stub_rc)
        env.pop("PYTHONUTF8", None)  # 必須由薄殼自己設，不能靠繼承而假綠
        proc = subprocess.run(
            [_BASH, "tools/integration_gate.sh", *args],
            cwd=str(self.tmp), capture_output=True, env=env, timeout=120,
        )
        return (
            proc.returncode,
            proc.stdout.decode("utf-8", errors="replace"),
            proc.stderr.decode("utf-8", errors="replace"),
        )

    def _marker(self) -> dict:
        self.assertTrue(
            self.marker.exists(),
            "stub 核心未被執行——薄殼沒有把工作轉交給 integration_gate_core.py",
        )
        return json.loads(self.marker.read_text(encoding="utf-8"))

    def test_shell_delegates_to_core_with_skip_full_passthrough(self) -> None:
        rc, out, err = self._run(["--skip-full"])
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertEqual(
            self._marker()["argv"], ["--skip-full"],
            "薄殼未把 --skip-full 透傳給核心——兩支 compat-CI 與 pre-push leg 用的正是這個模式",
        )

    def test_shell_sets_pythonutf8(self) -> None:
        """WHY：核心會 print ✅/❌/⚠️ 等非 ASCII；Windows 非 UTF-8 終端下沒有這個
        環境變數就會在輸出階段炸掉，而那是在所有 stage 都跑完之後才發生的失敗。"""
        rc, out, err = self._run([])
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertEqual(self._marker()["pythonutf8"], "1")

    def test_shell_propagates_core_failure_exit_code(self) -> None:
        """核心非零 → 薄殼必須原樣傳出去（不得吞成 0）。

        WHY：呼叫端（pre-push leg、CI step）判斷閘門過沒過**只看 exit code**。薄殼
        若吞掉 rc，整道閘門就變成「印紅字但放行」——最惡劣的假綠形態。
        """
        rc, out, err = self._run(["--skip-full"], stub_rc=7)
        self.assertEqual(rc, 7, f"薄殼吞掉核心 rc：\nstdout={out}\nstderr={err}")

    def test_shell_runs_without_args(self) -> None:
        rc, out, err = self._run([])
        self.assertEqual(rc, 0, f"stdout={out}\nstderr={err}")
        self.assertEqual(self._marker()["argv"], [])


if __name__ == "__main__":
    unittest.main()
