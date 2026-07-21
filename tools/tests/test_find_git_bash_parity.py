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
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PS1_PATH = _REPO_ROOT / "tools" / "lib" / "Find-GitBash.ps1"
_PY_PATH = _REPO_ROOT / "tools" / "integration_gate_core.py"


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
    m = re.search(r'part\.lower\(\)\s*==\s*"([^"]*)"', text)
    assert m, "integration_gate_core.py 找不到 System32 排除比對片語"
    return m.group(1)


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


if __name__ == "__main__":
    unittest.main()
