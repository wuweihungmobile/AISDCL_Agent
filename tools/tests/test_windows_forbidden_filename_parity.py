"""交叉一致性鎖：Windows 禁用檔名邏輯三處獨立實作
（`tools/git-hooks/pre-commit` 的 `_ntfs_seg_bad()`、`tools/check_ntfs_paths.py`、
`AutoClaude/autoclaude/utils/logger.py`）目前內容一致，但沒有任何機械測試鎖住
這個一致性——R33 Architect 架構深度評估發現的缺口（DEF-101-295）。三處保持獨立
實作是刻意決策（bash 版無法 import Python 模組；logger.py 屬獨立可 pip 安裝的
`autoclaude` 套件，不可依賴 monorepo 根層 `tools/lib/*.py`，見 logger.py 內註解），
本檔只負責「漂移即知」，不合併三者。
"""

import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS_DIR = REPO_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import check_ntfs_paths  # noqa: E402

_AUTOCLAUDE_DIR = REPO_ROOT / "AutoClaude"
if str(_AUTOCLAUDE_DIR) not in sys.path:
    sys.path.insert(0, str(_AUTOCLAUDE_DIR))
from autoclaude.utils import logger as autoclaude_logger  # noqa: E402

PRE_COMMIT_HOOK = REPO_ROOT / "tools" / "git-hooks" / "pre-commit"

_FUNC_RE = re.compile(r"^_ntfs_seg_bad\(\)\s*\{.*?^\}\s*$", re.MULTILINE | re.DOTALL)

RESERVED_NAMES = ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"]
NON_RESERVED_NAMES = ["CONSOLE", "PRINTER", "COM10", "LPTX", "NULLABLE", "hello"]


def _extract_bash_function() -> str:
    text = PRE_COMMIT_HOOK.read_text(encoding="utf-8")
    m = _FUNC_RE.search(text)
    assert m, "pre-commit 內找不到 _ntfs_seg_bad() 函式定義——本測試的抽取假設已失效"
    return m.group(0)


def _run_bash_seg_check(segment: str) -> tuple[int, str]:
    """實際執行 pre-commit 的 `_ntfs_seg_bad()`（動態抽取＋source），非靜態文字比對。"""
    func_src = _extract_bash_function()
    proc = subprocess.run(
        ["bash", "-c", f'{func_src}\n_ntfs_seg_bad "$1"', "check", segment],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return proc.returncode, proc.stdout


class TestForbiddenCharsCrossConsistency(unittest.TestCase):
    def test_python_sets_match(self) -> None:
        self.assertEqual(
            check_ntfs_paths._FORBIDDEN_CHARS,
            set(autoclaude_logger._WIN_FORBIDDEN_CHARS),
        )

    def test_bash_flags_every_char_in_python_forbidden_set(self) -> None:
        for ch in sorted(check_ntfs_paths._FORBIDDEN_CHARS):
            rc, out = _run_bash_seg_check(f"file{ch}name")
            self.assertEqual(rc, 0, f"bash 未攔下 Python 集合內的禁用字元 {ch!r}：{out!r}")
            self.assertIn("不允許字元", out)

    def test_bash_does_not_flag_chars_outside_python_forbidden_set(self) -> None:
        safe_chars = [c for c in "!#$%&'()+,-.0123456789ABCabc_~" if c not in check_ntfs_paths._FORBIDDEN_CHARS]
        for ch in safe_chars:
            rc, out = _run_bash_seg_check(f"file{ch}name")
            self.assertNotIn(
                "不允許字元", out, f"bash 誤攔了不在 Python 禁用集合內的字元 {ch!r}：{out!r}"
            )


class TestReservedNameCrossConsistency(unittest.TestCase):
    def test_python_regexes_agree_on_reserved_names(self) -> None:
        for name in RESERVED_NAMES:
            self.assertTrue(check_ntfs_paths._RESERVED_RE.match(name), name)
            self.assertTrue(autoclaude_logger._WIN_RESERVED_NAME_RE.match(name), name)
            self.assertTrue(autoclaude_logger._WIN_RESERVED_NAME_RE.match(name.lower()), name)

    def test_python_regexes_agree_on_non_reserved_names(self) -> None:
        for name in NON_RESERVED_NAMES:
            self.assertFalse(check_ntfs_paths._RESERVED_RE.match(name), name)
            self.assertFalse(autoclaude_logger._WIN_RESERVED_NAME_RE.match(name), name)

    def test_bash_flags_every_reserved_name_python_flags(self) -> None:
        for name in RESERVED_NAMES:
            rc, out = _run_bash_seg_check(name)
            self.assertEqual(rc, 0, f"bash 未攔下保留裝置名 {name!r}：{out!r}")
            self.assertIn("保留裝置名", out)

    def test_bash_does_not_flag_non_reserved_names(self) -> None:
        for name in NON_RESERVED_NAMES:
            rc, out = _run_bash_seg_check(name)
            self.assertNotEqual(rc, 0, f"bash 誤攔了非保留名 {name!r}：{out!r}")


# R33 QA 二審發現：logger.py 原用 rsplit(".", 1) 剝副檔名（只切最後一個點），對多重
# 副檔名的保留名（如 lpt5.tar.gz）算出 stem="lpt5.tar" 而漏判；check_ntfs_paths.py／
# bash 皆用「第一個點起」剝離（split(".", 1) / ${seg%%.*}），三者對此不對稱。已改
# logger.py 為 split(".", 1) 與另兩處一致（DEF-101-295 追加修復）。
MULTI_EXTENSION_RESERVED = ["lpt5.tar.gz", "com1.a.b.c", "aux.setup.retry"]


class TestMultiExtensionReservedNameCrossConsistency(unittest.TestCase):
    def test_check_ntfs_paths_flags_multi_extension_reserved_names(self) -> None:
        for name in MULTI_EXTENSION_RESERVED:
            self.assertIsNotNone(check_ntfs_paths._ntfs_seg_bad(name), name)

    def test_bash_flags_multi_extension_reserved_names(self) -> None:
        for name in MULTI_EXTENSION_RESERVED:
            rc, out = _run_bash_seg_check(name)
            self.assertEqual(rc, 0, f"bash 未攔下多重副檔名保留名 {name!r}：{out!r}")
            self.assertIn("保留裝置名", out)

    def test_logger_prefixes_multi_extension_reserved_names(self) -> None:
        for name in MULTI_EXTENSION_RESERVED:
            sanitized = autoclaude_logger._sanitize_log_filename(name)
            self.assertTrue(
                sanitized.startswith("_"),
                f"logger.py 未攔下多重副檔名保留名 {name!r}：{sanitized!r}",
            )


# R33 QA 一審發現：logger.py 原本缺控制字元淨化，與 bash/check_ntfs_paths.py 不對稱
# （DEF-101-295 修復追加，關閉此維度的既有落差）。0x00 無法放進 subprocess argv，故略過。
CONTROL_CHARS = [chr(c) for c in range(0x01, 0x20)] + [chr(0x7F)]

# \n（0x0A）在 pre-commit 的 bash 版偵測不到（DEF-101-297，backlog）：
# `printf '%s' "$p" | grep '[[:cntrl:]]'` 逐行比對時，換行本身被當成行分隔符消耗掉，
# 不會出現在任一行的「內容」裡讓 [[:cntrl:]] 比對到；兩個 Python 版（`ord(ch) < 0x20`
# 逐字元比對）不受此限。CI 端 check_ntfs_paths.py 仍會擋下，非完全繞過，故不在本輪
# 改寫 bash 邏輯（範圍外），僅在此排除、避免測試本身對已知限制誤報。
_BASH_CONTROL_CHARS = [c for c in CONTROL_CHARS if c != "\n"]


class TestControlCharCrossConsistency(unittest.TestCase):
    def test_check_ntfs_paths_flags_every_control_char(self) -> None:
        for ch in CONTROL_CHARS:
            segment = f"file{ch}name"
            self.assertIsNotNone(check_ntfs_paths._ntfs_seg_bad(segment), repr(ch))

    def test_logger_sanitizes_every_control_char(self) -> None:
        for ch in CONTROL_CHARS:
            segment = f"file{ch}name"
            sanitized = autoclaude_logger._sanitize_log_filename(segment)
            self.assertNotIn(ch, sanitized, f"logger.py 未淨化控制字元 {ch!r}：{sanitized!r}")

    def test_bash_flags_every_control_char(self) -> None:
        for ch in _BASH_CONTROL_CHARS:
            rc, out = _run_bash_seg_check(f"file{ch}name")
            self.assertEqual(rc, 0, f"bash 未攔下控制字元 {ch!r}：{out!r}")
            self.assertIn("控制字元", out)


if __name__ == "__main__":
    unittest.main()
