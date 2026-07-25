"""DEF-101-385 regression lock — `slv_generator._fpl_path()` FPL id validation.

WHY this test exists: `AISDLC_SDD/scripts/component_sanitizer_callsite_scan.py`
registers a filename-keyed AST-scanner exemption for `fpl_id` in this module,
justified purely by the claim (docstring/comment) that `_fpl_path()` validates
`fpl_id` via `FPL_ID_RE.match()` before it is used to build a filesystem path.
Because the exemption is keyed by filename (not by content), a future
Copy-on-Evolve round could weaken or remove this validation while keeping the
filename unchanged and sail through the scanner undetected. This test locks
the exact behaviour the exemption relies on, independent of the scanner.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.slv_generator import (  # noqa: E402
    FPL_DIR,
    FPLNotFound,
    _fpl_path,
)


class FplPathValidationTests(unittest.TestCase):
    """驗證 `_fpl_path()` 在建構路徑前確實擋下不合法／越權的 fpl_id。"""

    def test_path_traversal_id_raises_value_error(self) -> None:
        """路徑穿越字串不符 `^FPL-\\d{3,}$`，必須在格式檢查就被擋下（ValueError）。"""
        with self.assertRaises(ValueError):
            _fpl_path("../../etc/passwd")

    def test_malformed_id_raises_value_error(self) -> None:
        """非 FPL-NNN 格式一律 ValueError，不得進入 glob 查找。"""
        with self.assertRaises(ValueError):
            _fpl_path("not-an-fpl-id")

    def test_valid_format_does_not_raise_on_format_grounds(self) -> None:
        """合法格式（且對應檔案存在）不因格式檢查被拒，回傳 FPL_DIR 下的實際路徑。"""
        path = _fpl_path("FPL-001")
        self.assertEqual(path.parent, FPL_DIR)
        self.assertTrue(path.name.startswith("FPL-001-"))

    def test_valid_format_unknown_id_raises_not_found_not_value_error(self) -> None:
        """格式合法但無對應檔案 → FPLNotFound（非 ValueError），確認兩類失敗互斥。"""
        with self.assertRaises(FPLNotFound):
            _fpl_path("FPL-999")


if __name__ == "__main__":
    unittest.main()
