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
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PS1_PATH = _REPO_ROOT / "tools" / "lib" / "Find-GitBash.ps1"
_PY_PATH = _REPO_ROOT / "tools" / "integration_gate_core.py"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import integration_gate_core  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
