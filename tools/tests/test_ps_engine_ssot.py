#!/usr/bin/env python3
"""PowerShell 引擎述詞 SSOT 的守門（R60 Scan-E E-A-03；R60 round-2 改 AST 判定）。

WHY（測意圖非僅行為，Rule 9）：`tools/tests/` 曾有 **6 檔／10 處行內寫法／5 種語意**
各自挑 PowerShell 引擎，其中一處（`test_windowsapps_guard_cross_consistency.py`
的 `_pwsh_exe()`）是 **pwsh 7 優先**，與 R59 **DEF-101-509** 拍板的「生產引擎（5.1）
優先」方向相反。這類「第 N+1 份選錯」在本 repo 已有兩次實證（DEF-101-285 的
`.cmd`/PATHEXT、DEF-101-509 的 pwsh-only skip），而過去**沒有任何鎖**在看著。

本鎖守四件事：
  1. **優先序方向**：`production_engine()` 在「兩引擎都在」時必須回 5.1。
     🔴 **在只裝了一個引擎的機器上**，任何「pwsh 優先」的實作都會靜默 fallback 到另一個、
     **測不出差別**——所以這支測試必須用合成的 `shutil.which` 偽造「兩者皆在」，否則它
     對整個 E-A-03 缺陷類別零鑑別力（同 R56 教訓：「驗證合法三元」與「驗證鎖是否真的
     漏抓」是兩件事）。合成的另一個好處是**與這台機器裝了什麼無關**：R73 訂正前這裡
     寫死了撰寫當輪那台機器只有 5.1，而 2026-08-04 它已同時具備兩者（DEF-101-777）。
  2. **語意④不得 fallback**：`native_ps51()` 在「只有 pwsh」的機器上必須回 None。
  3. **反增生**：`tools/tests/*.py` 不得再出現行內引擎挑選，除具名豁免。
  4. **正向委派**：已遷移的消費檔必須真的 import SSOT，且其引擎述詞函式的**程式碼本體**
     必須呼叫 `production_engine()`、不得回退成 `shutil.which(...)`。

🔴 **R60 round-2 訂正（ARCH-R60-06／SA-R60-03／SD-R60-03／QA-R60-07 四方獨立命中）**：
本鎖第 3 項原本是**逐行文字 regex**，只跳過整行 `#` 註解、**不剝 docstring**。後果是
`test_windowsapps_guard_cross_consistency.py` 靠自己 docstring 內兩句「原實作是
`shutil.which("pwsh") or shutil.which("powershell")`」的**史料引述**恆久「命中」，於是
①該檔以檔案級豁免（`_PENDING_MIGRATION_SITES`）掛在名單上，遷移完成後仍不會被判 stale
（豁免自陳「遷移完成後刪除本條目」卻永遠退不了場）；②該檔又不在正向 import 鎖名單內
⇒ **E-A-03 的原始動機案例檔零覆蓋**：把 `_pwsh_exe()` 改回 pwsh 優先，本鎖全綠。
四方各自以注入實證此假綠（`INJECTED_RUN ran=2 fail=0 err=0`）。

修法＝**判定改走 `ast`**（`_engine_selection_linenos()`）：只認**真正的 `Call` 節點**
`shutil.which("powershell"|"pwsh")` / `which("powershell"|"pwsh")`，docstring／註解／
字串常數內的史料引述在 AST 上根本不是 Call ⇒ 結構性不可能誤命中。連帶效果：
  · `_PENDING_MIGRATION_SITES` 整張表刪除（該檔已無真程式碼命中，遷移已完成）。
  · `test_windowsapps_guard_cross_consistency.py` 進入正向 import 鎖名單。
  · 本檔自己也不再需要永久豁免——`test_scanner_has_teeth` 的樣本是**字串常數**，
    AST 判定下本來就不是命中；反過來說，若有人把判定改回逐行文字掃描，本檔那些樣本
    會立刻變成 offender 讓 `test_no_unwaived_inline_engine_selection` 翻紅
    ⇒ **「掃描器退回文字掃描」本身成為自偵測項**（本次假綠的根因不會靜默復發）。
  · 另補 `_SSOT_DELEGATION_SITES` 正向鎖：直接對函式本體斷言，封住「留著 import
    卻把函式改回行內 which」這條 import 級鎖看不到的路（SD-R60-03 ③）。
方法論邊界（誠實揭露，勿留「已涵蓋全類別」錯覺）：AST 判定認的是字面引擎名的 `which`
呼叫；`shutil.which(name_from_variable)`／`getattr(shutil, "which")(...)`／`exec()` 組
出來的呼叫仍逃得掉（同 DEF-101-333 對逐行 regex 天花板的四方一致裁定，只是天花板換了
一層）。第 4 項正向委派鎖是這個邊界的補位：它不問「有沒有寫 which」，而問「函式本體
有沒有呼叫 SSOT」。

執行：python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(_TESTS_DIR))
import _ps_engine  # noqa: E402
from _platform_helpers import ABS_FAKE_REPO  # noqa: E402  # 平台中立假絕對路徑（R11）
from _ps_engine import (  # noqa: E402
    PRODUCTION_ENGINE_PRECEDENCE,
    available_engines,
    native_ps51,
    production_engine,
)

# 假引擎路徑刻意用平台中立的 `ABS_FAKE_REPO`（`_platform_helpers`）而非寫死磁碟機
# 代號——`tools/tests/test_platform_neutral_paths.py` 有一道「.py 內不得出現寫死
# Windows 假路徑」的鎖（本檔落地時當場被它攔下，同 R59 DEF-101-522 的先例）。
_FAKE_PS51 = str(ABS_FAKE_REPO / "System32" / "WindowsPowerShell" / "powershell.EXE")
_FAKE_PWSH = str(ABS_FAKE_REPO / "PowerShell" / "7" / "pwsh.EXE")


def _fake_which(available: dict[str, str]):
    """回傳一個假 `shutil.which`：只認 `available` 內的名字。"""

    def _which(name: str, *_a, **_kw):
        return available.get(name)

    return _which


# ── 反增生掃描（AST 判定，R60 round-2） ────────────────────────────────────────
# 引擎可執行檔名（大小寫不敏感、容許 `.exe` 後綴——`shutil.which("powershell.exe")`
# 與裸名語意相同，逐行 regex 版本漏了這個變體）。
_ENGINE_EXE_NAMES = frozenset({"powershell", "pwsh"})

# SSOT 本體：對「有沒有走 SSOT」的掃描而言它是定義處，不是違規站點，故整檔排除。
# （它以 `shutil.which(name)` 迴圈變數呼叫，AST 判定下本來也不算命中——引數不是
# 字面引擎名；此排除只是把「定義處」這件事寫明，不承載鑑別力。）
_SSOT_MODULE = "_ps_engine.py"

# **永久豁免**：這些站點必須保留行內 `shutil.which`（附 WHY），故加 stale 自檢——
# 條目失去對應的行內用法時 fail-loud 要求移除，防豁免清單腐化。
#
# R60 round-2：本表由 2 條縮為 1 條。刪掉的是 `test_ps_engine_ssot.py`（本檔自己）
# ——它先前唯一的「命中」是 `test_scanner_has_teeth` 裡當樣本的**字串常數**，改 AST
# 判定後那不是 Call、本來就不該算命中。留著會讓 stale 自檢誤紅，更重要的是：拿掉
# 之後「有人把判定改回逐行文字掃描」會讓本檔自己變成 offender ⇒ 假綠根因自偵測。
_PERMANENT_INLINE_SITES: dict[str, str] = {
    "test_install_windows_nightly.py": (
        "TestSyntaxGateEngineSelection.test_engine_selection_prefers_windows_powershell "
        "是優先序判準的**獨立 ground truth**——若改走 SSOT 述詞算 expected，"
        "優先序寫反時兩邊會一起寫反、斷言恆綠＝鎖失去鑑別力（該測試 docstring 亦記載）"
    ),
}

# R60 round-2 刪除 `_PENDING_MIGRATION_SITES`（原本只有
# `test_windowsapps_guard_cross_consistency.py` 一條）：遷移已完成（該檔 `_pwsh_exe()`
# 委派 `production_engine()`），且 AST 判定下該檔已無真程式碼命中，故無需任何豁免。
# 該檔改由下方 `_MIGRATED_CONSUMERS`（正向 import 鎖）＋`_SSOT_DELEGATION_SITES`
# （函式本體委派鎖）兩層覆蓋。**刻意不保留空表**：空的 pending 表是下一個「掛著
# pending 名義的永久豁免」的溫床（本輪的假綠正是這樣長出來的）。

# 正向鎖名單：R60 遷移過的消費檔必須真的 import SSOT。
_MIGRATED_CONSUMERS = (
    "test_bootstrap_ps1.py",
    "test_dev_start_ps1_lastexitcode.py",
    "test_git_hooks_install_common.py",
    "test_install_windows_nightly.py",
    "test_nightly_interpreter_determinism.py",
    "test_windowsapps_guard_cross_consistency.py",  # R60 DEF-101-548（round-2 補入）
)

# 函式級委派鎖：`{檔名: (必須委派 SSOT 的函式名, …)}`。
# WHY 另立一層（SD-R60-03 ③）：`_MIGRATED_CONSUMERS` 只證明「檔案 import 了 SSOT」，
# 無法排除「留著 import 卻把函式本體改回行內 which」；本表直接對**函式本體**斷言。
_SSOT_DELEGATION_SITES: dict[str, tuple[str, ...]] = {
    # DEF-101-548 的修復本體：pwsh-優先 → 委派 5.1-優先 SSOT。
    "test_windowsapps_guard_cross_consistency.py": ("_pwsh_exe",),
}


def _parse(source: str, origin: str) -> ast.Module:
    """`ast.parse` 的 fail-loud 包裝——解析失敗不得讓掃描面靜默縮小。"""
    try:
        return ast.parse(source, filename=origin)
    except SyntaxError as exc:  # pragma: no cover - 落地即代表該檔壞了
        raise AssertionError(
            f"{origin} 無法以 ast 解析（{exc}）——反增生掃描面不得靜默縮小"
        ) from exc


def _is_engine_which_call(node: ast.Call) -> bool:
    """`node` 是否為「以字面引擎名呼叫 which」＝行內引擎挑選。

    認兩種形狀：`shutil.which("pwsh")`（既有 9 處全是這形狀）與
    `which("pwsh")`（`from shutil import which` 的等價寫法——逐行 regex 版漏抓）。
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr != "which" or not (
            isinstance(func.value, ast.Name) and func.value.id == "shutil"
        ):
            return False
    elif isinstance(func, ast.Name):
        if func.id != "which":
            return False
    else:
        return False
    if not node.args:
        return False
    first = node.args[0]
    if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
        return False
    stem = first.value.lower()
    if stem.endswith(".exe"):
        stem = stem[: -len(".exe")]
    return stem in _ENGINE_EXE_NAMES


def _engine_selection_linenos(source: str, origin: str) -> list[int]:
    """`source` 內所有行內引擎挑選的行號（1-based，升冪去重）。

    🔴 判定走 AST 而非逐行文字（R60 round-2 修 ARCH-R60-06 假綠）：docstring／註解／
    字串常數內的史料引述在 AST 上不是 `Call`，結構性不可能誤命中。
    """
    tree = _parse(source, origin)
    found = {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_engine_which_call(node)
    }
    return sorted(found)


def _function_bodies_code(source: str, origin: str, func_name: str) -> list[str]:
    """`func_name` 的**每一個**定義的本體程式碼（已剝除 docstring），至少一個。

    用 `ast.unparse` 而非切原始碼行：回傳文字保證不含註解與 docstring，故對它做
    「必須含 X、不得含 Y」的斷言不會被說明文字污染（本輪假綠的同一個病）。

    刻意回傳**全部**同名定義而非第一個：否則「多寫一個委派的誘餌 `def _pwsh_exe()`
    放在前面、真正被呼叫的那個改回行內 which」就能騙過鎖（同「第 N+1 份選錯」家族）。
    """
    tree = _parse(source, origin)
    bodies: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func_name:
            continue
        body = list(node.body)
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]
        bodies.append("\n".join(ast.unparse(stmt) for stmt in body))
    if not bodies:
        raise AssertionError(
            f"{origin} 內找不到函式 {func_name}()——委派鎖的標的消失（被改名或刪除？）"
            "：請同步更新 _SSOT_DELEGATION_SITES，不得讓鎖靜默失去標的"
        )
    return bodies


class TestProductionEnginePrecedence(unittest.TestCase):
    def test_precedence_tuple_puts_windows_powershell_first(self) -> None:
        """優先序常數本體：5.1 在前。順序即判準（DEF-101-509），對調即紅。"""
        self.assertEqual(
            PRODUCTION_ENGINE_PRECEDENCE, ("powershell", "pwsh"),
            "生產引擎優先序被改動——R59 DEF-101-509 拍板「Windows PowerShell 5.1 優先，"
            "pwsh 7 只作兜底」：生產以 `powershell -ExecutionPolicy Bypass -File` 執行，"
            "且 `tools/` 樹受 test_ps51_compat.py 的 PS 5.1 相容政策約束",
        )

    def test_prefers_ps51_when_both_engines_present(self) -> None:
        """🔴 核心鑑別力：合成「兩引擎都在」——在只裝一個引擎的機器上驗不到方向。"""
        with mock.patch.object(
            _ps_engine.shutil, "which",
            _fake_which({"powershell": _FAKE_PS51, "pwsh": _FAKE_PWSH}),
        ):
            self.assertEqual(
                production_engine(), _FAKE_PS51,
                "兩引擎皆在時選了 pwsh 7——與 DEF-101-509 判準方向相反（E-A-03 迴歸）",
            )
            self.assertEqual(
                available_engines(), {"powershell": _FAKE_PS51, "pwsh": _FAKE_PWSH},
            )

    def test_falls_back_to_pwsh_only_when_ps51_absent(self) -> None:
        """兜底路徑（macOS/Linux 現實）：只有 pwsh 時才回 pwsh。"""
        with mock.patch.object(
            _ps_engine.shutil, "which", _fake_which({"pwsh": _FAKE_PWSH})
        ):
            self.assertEqual(production_engine(), _FAKE_PWSH)
            self.assertTrue(_ps_engine.any_engine_available())

    def test_none_when_no_engine(self) -> None:
        with mock.patch.object(_ps_engine.shutil, "which", _fake_which({})):
            self.assertIsNone(production_engine())
            self.assertFalse(_ps_engine.any_engine_available())
            self.assertEqual(available_engines(), {})


class TestNativePs51NeverFallsBack(unittest.TestCase):
    """語意④與語意①**不可合併**：前者 fallback 就失去鑑別力（PATH 反斜線語意只在 5.1 成立）。"""

    def test_native_ps51_is_none_when_only_pwsh_present(self) -> None:
        with mock.patch.object(
            _ps_engine.shutil, "which", _fake_which({"pwsh": _FAKE_PWSH})
        ):
            self.assertIsNone(
                native_ps51(),
                "native_ps51() 兜底到了 pwsh 7——語意④要求「只認原生 5.1」，"
                "fallback 會讓 PATH 反斜線正規化的行為驗證跑在錯誤引擎上",
            )
            self.assertFalse(_ps_engine.windows_with_native_ps51())

    def test_native_ps51_returns_ps51_when_present(self) -> None:
        with mock.patch.object(
            _ps_engine.shutil, "which",
            _fake_which({"powershell": _FAKE_PS51, "pwsh": _FAKE_PWSH}),
        ):
            self.assertEqual(native_ps51(), _FAKE_PS51)


class TestNoInlineEngineSelection(unittest.TestCase):
    """反增生：`tools/tests/*.py` 不得再出現行內引擎挑選（第 10 處重新發明必紅）。"""

    def _hits(self) -> dict[str, list[int]]:
        found: dict[str, list[int]] = {}
        for path in sorted(_TESTS_DIR.glob("*.py")):
            if path.name == _SSOT_MODULE:
                continue
            linenos = _engine_selection_linenos(
                path.read_text(encoding="utf-8", errors="replace"), path.name
            )
            if linenos:
                found[path.name] = linenos
        return found

    def test_scanner_has_teeth(self) -> None:
        """鑑別力自檢：掃描器對合成樣本必須命中，對對照樣本必須不命中。"""
        for sample in (
            'exe = shutil.which("powershell") or shutil.which("pwsh")',
            "engine = shutil.which('pwsh')",
            'if shutil.which( "powershell" ) is None: pass',
            'exe = shutil.which("PowerShell.exe")',   # 大小寫／.exe 變體
            'from shutil import which\nexe = which("pwsh")',  # 等價 import 寫法
        ):
            self.assertTrue(
                _engine_selection_linenos(sample, "<sample>"), f"掃描器漏抓：{sample!r}"
            )
        for benign in (
            'git = shutil.which("git")',
            "bash = shutil.which('bash')",
            "exe = production_engine()",
            'name = "powershell"\nexe = shutil.which(name)',  # 變數引數＝天花板，如實揭露
        ):
            self.assertEqual(
                _engine_selection_linenos(benign, "<benign>"), [],
                f"掃描器偽陽性：{benign!r}",
            )

    def test_scanner_ignores_docstrings_comments_and_string_literals(self) -> None:
        """🔴 ARCH-R60-06／SA-R60-03／SD-R60-03／QA-R60-07 的回歸鎖（四方獨立命中）。

        本輪 round 1 的假綠根因：逐行文字掃描把 **docstring 內的史料引述**當成命中，
        於是 `test_windowsapps_guard_cross_consistency.py` 恆久有 hit 撐著它的檔案級
        豁免，遷移完成後仍永遠退不了場，而該檔又不在正向鎖名單內 ⇒ 動機案例檔零覆蓋。
        本支用**與該檔同構的合成樣本**（docstring 引述舊 pwsh-優先實作 ＋ 函式本體
        委派 SSOT）釘死「引述不算命中、真呼叫才算」：判定退回文字掃描即翻紅。
        """
        historical_note = '''
def _pwsh_exe():
    """委派 production_engine()（R60 收斂）。

    原實作是 shutil.which("pwsh") or shutil.which("powershell")＝pwsh 7 優先，
    與 DEF-101-509 拍板方向相反。
    """
    return production_engine()


# 史料（整行註解）：shutil.which("pwsh") or shutil.which("powershell")
SAMPLE = 'shutil.which("powershell")'   # 字串常數內的樣本
'''
        self.assertEqual(
            _engine_selection_linenos(historical_note, "<historical>"), [],
            "掃描器把 docstring／註解／字串常數內的史料引述當成行內引擎挑選——"
            "這正是 R60 round 1 讓動機案例檔取得永久假豁免的根因（ARCH-R60-06）",
        )
        # 正控：同一段樣本把 `return` 改回行內挑選 ⇒ 必須命中（證明上面的綠不是恆綠）。
        reverted = historical_note.replace(
            "    return production_engine()",
            '    return shutil.which("pwsh") or shutil.which("powershell")',
        )
        self.assertTrue(
            _engine_selection_linenos(reverted, "<reverted>"),
            "正控失效：真正的行內引擎挑選也沒被抓到＝掃描器整體失能",
        )

    def test_no_unwaived_inline_engine_selection(self) -> None:
        waived = set(_PERMANENT_INLINE_SITES)
        offenders = {
            name: linenos for name, linenos in self._hits().items()
            if name not in waived
        }
        self.assertEqual(
            offenders, {},
            "以下檔案自己行內挑 PowerShell 引擎，未走 `_ps_engine` SSOT 述詞"
            f"：{offenders}。請改用 `production_engine()`（語意①：5.1 優先）／"
            "`any_engine_available()`（語意②）／`windows_with_engine()`（語意③）／"
            "`native_ps51()`／`windows_with_native_ps51()`（語意④）；"
            "若確有無法收斂的理由，請登記 `_PERMANENT_INLINE_SITES` 並附 WHY",
        )

    def test_permanent_waivers_are_not_stale(self) -> None:
        """永久豁免的 stale 自檢：條目失去對應行內用法即要求移除（防清單腐化）。

        R60 round-2：判定改 AST 後本自檢才真的有意義——先前 docstring 引述會讓任何
        條目「永遠有 hit 撐著」，stale 自檢對那類條目結構性不可能翻紅（SA-R60-03）。
        """
        hits = self._hits()
        stale = [name for name in _PERMANENT_INLINE_SITES if name not in hits]
        self.assertEqual(
            stale, [],
            f"以下永久豁免已 stale（該檔已無行內引擎挑選）：{stale}"
            "——請自 _PERMANENT_INLINE_SITES 移除",
        )

    def test_waiver_reasons_are_non_empty(self) -> None:
        for name, why in _PERMANENT_INLINE_SITES.items():
            self.assertTrue(
                why.strip(),
                f"_PERMANENT_INLINE_SITES[{name!r}] 的 WHY 為空——豁免必須附理由",
            )

    def test_no_pending_migration_waiver_table_reappears(self) -> None:
        """🔴 「掛著 pending 名義的永久豁免」不得復辟（SA-R60-03／QA-R60-07 根因）。

        R60 round 1 的 `_PENDING_MIGRATION_SITES` 刻意不加 stale 自檢（理由：遷移完成
        後條目只是「無用（無害）」），該理由經四方實測為假——它讓被豁免檔案零覆蓋，
        且因掃描器誤把 docstring 算成 hit 而永遠退不了場。本支釘死：本模組不得再出現
        「無 stale 自檢的豁免表」；任何豁免一律進 `_PERMANENT_INLINE_SITES`（有自檢）。
        """
        self.assertFalse(
            hasattr(sys.modules[__name__], "_PENDING_MIGRATION_SITES"),
            "`_PENDING_MIGRATION_SITES` 又出現了——豁免表必須帶 stale 自檢，"
            "請改用 `_PERMANENT_INLINE_SITES`（`test_permanent_waivers_are_not_stale` 看著）",
        )
        source = Path(__file__).read_text(encoding="utf-8")
        tree = _parse(source, Path(__file__).name)
        assigned = {
            target.id
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
            if isinstance(target, ast.Name)
        }
        waiver_tables = {n for n in assigned if n.endswith("_SITES")}
        self.assertEqual(
            waiver_tables, {"_PERMANENT_INLINE_SITES", "_SSOT_DELEGATION_SITES"},
            f"本模組出現了預期外的 *_SITES 表：{sorted(waiver_tables)}——每一張豁免表"
            "都必須有對應的 stale 自檢，否則會長成本輪那種永久假豁免",
        )

    def test_migrated_consumers_import_the_ssot(self) -> None:
        """正向鎖：R60 遷移過的消費檔必須真的 import SSOT。

        負面斷言（上面那支）只能證明「沒人寫行內 which」；把述詞呼叫整段刪掉、
        改成別的第三種寫法時它仍全綠。本支釘住「這些檔確實接在 SSOT 上」。
        """
        missing = [
            name for name in _MIGRATED_CONSUMERS
            if "from _ps_engine import"
            not in (_TESTS_DIR / name).read_text(encoding="utf-8")
        ]
        self.assertEqual(
            missing, [],
            f"以下 R60 已遷移的檔案不再 import `_ps_engine` SSOT：{missing}"
            "——疑似有人把引擎挑選改回別的寫法（E-A-03 迴歸）",
        )

    def test_migrated_consumers_list_covers_delegation_sites(self) -> None:
        """兩張表不得脫鉤：委派鎖的每個檔案都必須同時在正向 import 鎖名單內。"""
        uncovered = sorted(set(_SSOT_DELEGATION_SITES) - set(_MIGRATED_CONSUMERS))
        self.assertEqual(
            uncovered, [],
            f"以下檔案有函式級委派鎖但不在 `_MIGRATED_CONSUMERS`：{uncovered}",
        )

    def test_delegation_sites_call_the_ssot_predicate(self) -> None:
        """🔴 SD-R60-03 ③／QA-R60-07 的核心回歸鎖：函式本體必須委派 SSOT。

        WHY（測意圖非僅行為）：import 級鎖看不到「留著 import 卻把函式本體改回
        `shutil.which("pwsh") or shutil.which("powershell")`」——而那正是
        DEF-101-548 的原始缺陷形狀（pwsh 7 去驗一支受 `tools/` 5.1 政策約束的
        `.ps1`）。在只裝了一個引擎的機器上，行為面測不出差別（fallback 會靜默補上），
        所以只能從**原始碼結構**釘死——這條理由與這台機器現在裝了什麼無關，
        故 R73 把原本寫死機器屬性的措辭一併改掉（DEF-101-777）。
        斷言對象是 `ast.unparse` 後的函式本體（不含 docstring／註解），故該檔
        docstring 逐字保留舊實作當史料不會讓本鎖誤綠也不會誤紅。
        """
        for name, func_names in _SSOT_DELEGATION_SITES.items():
            source = (_TESTS_DIR / name).read_text(encoding="utf-8")
            for func_name in func_names:
                for body in _function_bodies_code(source, name, func_name):
                    self.assertIn(
                        "production_engine()", body,
                        f"{name}::{func_name}() 的本體沒有呼叫 `production_engine()`"
                        f"（實得：{body!r}）——DEF-101-548 迴歸：引擎挑選必須走 5.1-優先 SSOT",
                    )
                    self.assertNotIn(
                        "shutil.which", body,
                        f"{name}::{func_name}() 的本體回退成行內 `shutil.which`"
                        f"（實得：{body!r}）——這正是 DEF-101-548 的原始缺陷形狀"
                        "（pwsh 7 優先，方向與 R59 DEF-101-509 相反）",
                    )

    def test_delegation_lock_covers_every_same_named_definition(self) -> None:
        """誘餌防護：同名多重定義時，鎖必須檢查**每一個**而非第一個。

        攻擊形狀：在真正的 `_pwsh_exe()` 之前多放一個委派版誘餌，把真正被呼叫的那個
        改回行內 which——若鎖只看第一個定義就會全綠。
        """
        decoy = (
            "def _pwsh_exe():\n"
            "    return production_engine()\n"
            "\n\n"
            "def _pwsh_exe():\n"
            '    return shutil.which("pwsh") or shutil.which("powershell")\n'
        )
        bodies = _function_bodies_code(decoy, "<decoy>", "_pwsh_exe")
        self.assertEqual(len(bodies), 2, bodies)
        self.assertTrue(
            any("shutil.which" in b for b in bodies),
            "誘餌情境下沒有回傳第二個定義＝鎖只看第一個，可被繞過",
        )


def _skip_reason_linenos(text: str) -> set[int]:
    """走 `ast` 找出「skip 機制的理由字串」佔用的行號集合。

    WHY 要豁免這一類：`@unittest.skipUnless(_ps_engine(), "<缺引擎時要印的理由>")`
    的理由字串**只在條件成立時才會被人看到**——它是對活檢查結果的描述，不是把機器屬性
    寫成常數。若不豁免，R73 擴射程當場製造 2 筆假紅（`test_install_windows_nightly.py`
    的 `:377` skipUnless 與 `:447` skipTest），而假紅會逼下一輪的人去「修」正確的程式碼。
    判定走 AST 而非文字：與本檔第 3 項鎖 R60 round-2 的訂正同一個理由——文字判定會被
    docstring／註解裡的引述誤命中（該次假綠讓 E-A-03 動機案例檔零覆蓋）。
    """
    exempt: set[int] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return exempt
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fname = ""
        if isinstance(node.func, ast.Attribute):
            fname = node.func.attr
        elif isinstance(node.func, ast.Name):
            fname = node.func.id
        if "skip" not in fname.lower():
            continue
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                for ln in range(arg.lineno, (arg.end_lineno or arg.lineno) + 1):
                    exempt.add(ln)
    return exempt


# 行尾豁免標記：偵測器自己的樣本字串。沿用 repo 既有的 `# ps7-ok:` 行尾標記慣例
# （獨立註解行無效，必須行尾），並由 `test_stale_sample_marker_stays_bounded` 界定射程。
_STALE_SAMPLE_MARKER = "# stale-sample:"


class TestNoStaleLocalEngineClaims(unittest.TestCase):
    """不得把「這台機器有沒有某個引擎」寫成常數。**射程＝整個 `tools/` 樹**（R73 擴）。

    WHY（R69 原案）：`_ps_engine.py` 的 docstring 有兩處把「這台機器沒有 pwsh 7」寫成
    常數，那是撰寫當輪那台 Windows 機器的屬性；R69 在 macOS 真機上 `shutil.which("pwsh")` 命中
    ⇒ 該前提為假，而它正是「⑤ 這條為什麼測不出差別」的**唯一理由**——理由失效後，
    讀者會以為那個風險在本機不存在，實際上正在發生。同 ADR-XPLAT-002 §6 邊界 1 已裁定
    的原則：平台／環境可用性是**輪次屬性**，治理文件與護欄程式一律指向現查來源。

    🔴 **R73 擴射程的理由（DEF-101-777）——這是「劃界結案」的代價被實際收取**：
    R69 訂正了 `_ps_engine.py` 並上了這條鎖，但鎖只圈**那一個檔**。2026-08-04 這台機器裝上
    PowerShell 7.6.4（`shutil.which("pwsh")` 實測命中 `Program Files/WindowsApps/
    Microsoft.PowerShell_7.6.4.0_x64__8wekyb3d8bbwe/pwsh.EXE`，size=301368、非 0 byte
    佔位版）後，**射程外的同型句子同時變成假事實**，實查 5 處：
      · `tools/lib/windows_skip_tags.py`（🔴 **護欄層**——拿現在為假的前提在描述豁免依據）
      · `tools/tests/test_install_windows_nightly.py`（宣稱「走不到兩引擎皆有的分支」，
        而該分支現在**每次都走得到**，且實測 `production_engine()` 正確回 5.1）
      · 本檔自己 3 處（鎖的檔案犯了鎖在抓的病，而鎖看不到自己）
    這正是 `DEF-101-757`「已知的鎖射程缺口不得只以劃界結案」的同型復發：**知道有缺口、
    只在文件裡註明缺口，四輪後缺口自己發火**。修法必須是擴射程，不是再註明一次。

    判準刻意窄（沿用 R69）：只抓「本機 + 無/沒有/不存在 + 引擎名」這種**斷言句**，不碰
    「本機根本沒有 5.1（macOS/Linux）」這類通則敘述。另有兩類結構性豁免，各有獨立鎖：
      · **skip 理由**（`_skip_reason_linenos`，走 AST）——見該函式 docstring。
      · **偵測器自己的樣本**（行尾 `# stale-sample:` 標記）——由
        `test_stale_sample_marker_stays_bounded` 防它被拿去豁免真的違規。
    """

    _STALE_RE = re.compile(
        r"本機[^。\n]{0,8}?(?:無|沒有|不存在)[^。\n]{0,4}?(pwsh|powershell|PS\s*[57])"
    )
    # 射程＝`tools/` 樹全部 .py。刻意不限 `tools/tests/`：本輪命中的最嚴重一筆在
    # `tools/lib/windows_skip_tags.py`＝護欄層生產碼，只掃測試就會漏掉它。
    _SCAN_ROOT = Path(__file__).resolve().parents[1]

    @classmethod
    def _scan_files(cls) -> list[Path]:
        return sorted(p for p in cls._SCAN_ROOT.rglob("*.py") if "__pycache__" not in p.parts)

    def test_tools_tree_has_no_hardcoded_local_engine_absence(self) -> None:
        offenders: list[str] = []
        scanned = 0
        for path in self._scan_files():
            text = path.read_text(encoding="utf-8")
            scanned += 1
            exempt = _skip_reason_linenos(text)
            for lineno, line in enumerate(text.splitlines(), 1):
                if not self._STALE_RE.search(line):
                    continue
                if lineno in exempt or _STALE_SAMPLE_MARKER in line:
                    continue
                rel = path.relative_to(self._SCAN_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
        self.assertGreater(scanned, 20, "射程掃到的檔案數異常少——rglob 可能沒對上樹根")
        self.assertEqual(
            offenders, [],
            "把「這台機器有沒有某引擎」寫成了常數（共 "
            f"{len(offenders)} 處，掃描 {scanned} 檔）：\n" + "\n".join(offenders) +
            "\n改法：改指向現查（`available_engines()`／`shutil.which`），"
            "或改寫成不依賴特定機器的通則敘述。若確為 skip 理由字串，"
            "它會自動豁免；若是偵測器樣本，行尾加 `# stale-sample: <WHY>`。",
        )

    def test_detector_catches_the_pre_fix_sentence(self) -> None:
        """鑑別力：R69 修掉的逐字原句必須被命中。"""
        pre_fix = "⑤ 在**本機**（無 pwsh 7）會靜默 fallback"  # stale-sample: R69 原句
        self.assertIsNotNone(self._STALE_RE.search(pre_fix))

    def test_detector_catches_the_r73_sites(self) -> None:
        """🔴 R73 鑑別力：射程擴大前逃過鎖的三種真實句型，必須逐句被命中。

        意圖（Rule 9）：這三句不是我編的樣本，是 R73 實查到的**逐字原文**（分別來自
        護欄層、測試 docstring、本檔自己）。若有人把 `_SCAN_ROOT` 縮回單一檔案，
        `test_tools_tree_has_no_hardcoded_local_engine_absence` 會變綠而缺陷復活——
        本 case 讓「偵測器認不認得這些句型」與「射程涵不涵蓋它們」分開受測。
        """
        for sample in (
            "語法解析因本機無 pwsh 7 而 skip",  # stale-sample: 護欄層原文片段
            "本機無 pwsh 7，`expected` 恆等於 5.1",  # stale-sample: 測試原文片段
            "🔴 **本機無 pwsh 7**（實測 rc=1）",  # stale-sample: 本檔原文片段
        ):
            with self.subTest(sample=sample):
                self.assertIsNotNone(self._STALE_RE.search(sample))

    def test_detector_does_not_flag_conditional_prose(self) -> None:
        """對照組：說通則而非說這台機器的句子不得誤報。"""
        for sample in (
            "pwsh 7 只作「本機根本沒有 5.1」（macOS/Linux）時的兜底",
            "合成情境：讓判準在任何機器上都測得到方向",
        ):
            with self.subTest(sample=sample):
                self.assertIsNone(self._STALE_RE.search(sample))

    def test_skip_reason_exemption_is_ast_based_and_narrow(self) -> None:
        """豁免只認 skip 機制的理由字串，不得外溢到一般字串或註解。"""
        src = (
            'import unittest\n'
            '@unittest.skipUnless(cond, "本機無 pwsh 7")\n'  # stale-sample: 正向
            'class A(unittest.TestCase):\n'
            '    def t(self):\n'
            '        self.skipTest("本機無 powershell")\n'  # stale-sample: AST 豁免正向樣本
            '        msg = "本機無 pwsh 7"\n'  # stale-sample: 一般字串對照組（不得豁免）
            '        # 本機無 pwsh 7\n'  # stale-sample: 註解對照組（不在 AST 上）
        )
        exempt = _skip_reason_linenos(src)
        self.assertIn(2, exempt, "skipUnless 的理由字串必須豁免")
        self.assertIn(5, exempt, "skipTest 的理由字串必須豁免")
        self.assertNotIn(6, exempt, "一般字串賦值不是 skip 理由，不得豁免")
        self.assertNotIn(7, exempt, "註解不在 AST 上，本來就不該出現在豁免集合")

    def test_stale_sample_marker_stays_bounded(self) -> None:
        """行尾豁免標記不得擴散：只允許出現在本檔（偵測器自己的樣本）。

        意圖（Rule 9）：豁免標記是鎖上的洞。本 repo 已有「豁免自陳『完成後刪除』卻永遠
        退不了場」的實證（R60 `_PENDING_MIGRATION_SITES`）。把標記的**居所**也鎖住，
        任何人想用它繞過真的違規，就得先讓本 case 翻紅。
        """
        users: list[str] = []
        for path in self._scan_files():
            if path.resolve() == Path(__file__).resolve():
                continue
            if _STALE_SAMPLE_MARKER in path.read_text(encoding="utf-8"):
                users.append(str(path.relative_to(self._SCAN_ROOT)))
        self.assertEqual(
            users, [],
            f"`{_STALE_SAMPLE_MARKER}` 只允許用在偵測器自己的樣本上，"
            f"卻出現在：{users}。真正的機器屬性斷言請改寫成現查，不要貼標籤。",
        )


if __name__ == "__main__":
    unittest.main()
