"""交叉一致性鎖：state_loader._sanitize_component 與 AutoClaude 側
autoclaude.utils.logger._sanitize_log_filename 是兩個獨立實作（R38，Mac/Windows
相容性複審 Scan-A 掃描發現 DEF-101 系列同缺陷類別姊妹未覆蓋位置）。

兩者刻意不共用同一顆函式物件——AISDLC_SDD 與 AutoClaude 是兩個獨立可發布子專案
（各自 releases/ 打包發布機制），依既有先例（bootstrap_core.py::
_is_windows_apps_stub() 語言邊界獨立實作）不可跨子專案 import 生產程式碼。

本檔只驗證「安全性質對齊」：對同一組危險輸入（正常字串、Windows 禁用字元、
保留裝置名、路徑穿越、超長字串），兩邊都必須把危險成分擋下（不要求輸出
逐字元相同）——比照既有 tools/tests/test_windows_forbidden_filename_parity.py
的手法，只是本檔比較的是「AISDLC_SDD 側新函式」而非 bash/CI 版三方。

超長字串截斷是本檔（AISDLC_SDD）獨有的額外防線（AutoClaude 側
_sanitize_log_filename 本身不做長度截斷，見該檔內註解），故不在本檔的 parity
比較範圍內，改由 test_phase_i_m5.py / test_phase_j.py 個別鎖定。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_THIS_SUBPROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../AISDLC_SDD_v0.30
if str(_THIS_SUBPROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_THIS_SUBPROJECT_ROOT))

from tools.fsm_runtime.state_loader import _sanitize_component  # noqa: E402

_MONOREPO_ROOT = Path(__file__).resolve().parents[5]  # .../AISDCL_Agent
_AUTOCLAUDE_DIR = _MONOREPO_ROOT / "AutoClaude"

_autoclaude_logger = None
if _AUTOCLAUDE_DIR.is_dir():
    if str(_AUTOCLAUDE_DIR) not in sys.path:
        sys.path.insert(0, str(_AUTOCLAUDE_DIR))
    try:
        from autoclaude.utils import logger as _autoclaude_logger  # noqa: E402
    except ImportError:
        _autoclaude_logger = None

_SKIP_REASON = (
    "本測試需 monorepo 內同時存在 AutoClaude/ 子專案（獨立 release 情境下允許缺席，"
    "AISDLC_SDD 不硬相依 AutoClaude 套件邊界）"
)

RESERVED_NAMES = ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"]
NON_RESERVED_NAMES = ["CONSOLE", "PRINTER", "COM10", "LPTX", "hello"]
FORBIDDEN_CHARS = '<>:"|?*\\'
CONTROL_CHARS = [chr(c) for c in range(0x01, 0x20)] + [chr(0x7F)]


@unittest.skipIf(_autoclaude_logger is None, _SKIP_REASON)
class TestForbiddenCharParity(unittest.TestCase):
    def test_both_strip_every_forbidden_char(self) -> None:
        for ch in FORBIDDEN_CHARS:
            ours = _sanitize_component(f"proj{ch}name")
            theirs = _autoclaude_logger._sanitize_log_filename(f"proj{ch}name")
            self.assertNotIn(ch, ours, f"AISDLC_SDD 側未擋下 {ch!r}：{ours!r}")
            self.assertNotIn(ch, theirs, f"AutoClaude 側未擋下 {ch!r}：{theirs!r}")

    def test_both_leave_safe_chars_untouched(self) -> None:
        for ch in "!#$%&'()+,-.0123456789ABCabc_~":
            ours = _sanitize_component(f"proj{ch}name")
            theirs = _autoclaude_logger._sanitize_log_filename(f"proj{ch}name")
            self.assertIn(ch, ours, f"AISDLC_SDD 側誤擋了安全字元 {ch!r}：{ours!r}")
            self.assertIn(ch, theirs, f"AutoClaude 側誤擋了安全字元 {ch!r}：{theirs!r}")


@unittest.skipIf(_autoclaude_logger is None, _SKIP_REASON)
class TestReservedNameParity(unittest.TestCase):
    def test_both_flag_every_reserved_name(self) -> None:
        for name in RESERVED_NAMES:
            ours = _sanitize_component(name)
            theirs = _autoclaude_logger._sanitize_log_filename(name)
            self.assertTrue(ours.startswith("_"), f"AISDLC_SDD 側未擋下保留名 {name!r}：{ours!r}")
            self.assertTrue(theirs.startswith("_"), f"AutoClaude 側未擋下保留名 {name!r}：{theirs!r}")

    def test_both_leave_non_reserved_names_untouched(self) -> None:
        for name in NON_RESERVED_NAMES:
            self.assertEqual(_sanitize_component(name), name)
            self.assertEqual(_autoclaude_logger._sanitize_log_filename(name), name)


@unittest.skipIf(_autoclaude_logger is None, _SKIP_REASON)
class TestControlCharParity(unittest.TestCase):
    def test_both_strip_every_control_char(self) -> None:
        for ch in CONTROL_CHARS:
            ours = _sanitize_component(f"proj{ch}name")
            theirs = _autoclaude_logger._sanitize_log_filename(f"proj{ch}name")
            self.assertNotIn(ch, ours, f"AISDLC_SDD 側未淨化控制字元 {ord(ch):#x}：{ours!r}")
            self.assertNotIn(ch, theirs, f"AutoClaude 側未淨化控制字元 {ord(ch):#x}：{theirs!r}")


@unittest.skipIf(_autoclaude_logger is None, _SKIP_REASON)
class TestPathTraversalParity(unittest.TestCase):
    """兩側都必須讓輸出無法被解讀為多層路徑（「/」與「\\」皆須淨化）。"""

    def test_both_strip_path_separators(self) -> None:
        hostile = "../../etc/passwd"
        ours = _sanitize_component(hostile)
        theirs = _autoclaude_logger._sanitize_log_filename(hostile)
        self.assertNotIn("/", ours)
        self.assertNotIn("/", theirs)

    def test_both_strip_backslash_separators(self) -> None:
        hostile = "..\\..\\windows\\system32"
        ours = _sanitize_component(hostile)
        theirs = _autoclaude_logger._sanitize_log_filename(hostile)
        self.assertNotIn("\\", ours)
        self.assertNotIn("\\", theirs)


@unittest.skipIf(_autoclaude_logger is None, _SKIP_REASON)
class TestNormalStringParity(unittest.TestCase):
    def test_both_pass_through_ordinary_identifiers(self) -> None:
        for name in ("AISDLC_SDD", "feature-track-01", "AC-005"):
            self.assertEqual(_sanitize_component(name), name)
            self.assertEqual(_autoclaude_logger._sanitize_log_filename(name), name)


if __name__ == "__main__":
    unittest.main()
