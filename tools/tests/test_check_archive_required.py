#!/usr/bin/env python3
"""`tools/check_archive_required.py` 判準①（DEF-200-222：commit 是否觸碰帳本家族）的
回歸鎖。判準②（`--apply` 序列化保護）的鎖住在 `tools/tests/test_apply_lock.py` 與
`tools/tests/test_archive_apply_locked.py`；本檔只管「要不要縮小阻斷面」這一半。

既有的 bytes×movable 判準回歸鎖住在 `tools/tests/test_check_defect_log_crossref.py`
的 `TestArchiveRequiredProblems`（該檔已卡在 LOC 分級的鄰居 SPECIAL_FILES 棘輪帳號
底下，新增判準①的獨立測試面另立本檔，不塞進去）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import atexit
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import archive_defect_log as adl  # noqa: E402
import check_archive_required as car  # noqa: E402
import check_defect_log_crossref as m  # noqa: E402

_TMP_DIR = Path(tempfile.mkdtemp(prefix="check_archive_required_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))

#: 帳本《格式定義》§ 狀態的權威散文，逐字複製自 docs/06_quality/AutoSDD_Defect_Log.md
#: （與 test_check_defect_log_crossref.py 的 `_STATUS_PROSE_LINE` 同一句，見該檔 WHY）。
_STATUS_PROSE_LINE = (
    ">   🔴 **合法首詞**＝`open`／`routed`／`fixed`／`wontfix`／"
    "`closed-by-decision`／`no_action_needed`／`partial`。"
)

#: WARN／FAIL 中點——確保落在帶內時有充分餘裕，不受合成列本身位元組數微幅影響。
_MID_BAND_BYTES = (m._LEDGER_WARN_BYTES + m._LEDGER_FAIL_BYTES) // 2


def _isolated_ledger(name: str, row: str, pad_to: int | None) -> Path:
    """建一份孤立目錄下的合成帳本（表頭＋單一列），視需要 padding 到指定 bytes。

    手法沿用 `test_check_defect_log_crossref.py::TestArchiveRequiredProblems`：帳本
    刻意放在 repo 外的 tmp 目錄，藉此同時驗證 `_touches_ledger_family()` 不依賴
    `_DEFECT_LOG` 位於 `_REPO_ROOT` 之下（見該函式 docstring 的「不比對目錄」設計）。
    """
    d = Path(_TMP_DIR) / name
    d.mkdir(parents=True, exist_ok=True)
    ledger = d / "AutoSDD_Defect_Log.md"
    text = (
        "# 缺陷帳本\n\n" + _STATUS_PROSE_LINE + "\n\n"
        "| ID | 發現日期 | 發現情境 | 現象 | 嚴重度 | 分流去向 | 狀態 |\n"
        "|----|----------|----------|------|--------|----------|------|\n"
        + row
    )
    if pad_to is not None:
        pad = max(0, pad_to - len(text.encode("utf-8")))
        text += "x" * pad  # 純填充：不含 `|` 前綴，不會被誤判為表格列（既有慣例）
    ledger.write_text(text, encoding="utf-8")
    return ledger


def _row(def_id: str, status: str) -> str:
    return f"| {def_id} | 2026-07-28 | 情境 | 現象 | P2 | 去向 | {status} |\n"


class TestTouchesLedgerFamily(unittest.TestCase):
    """純函式層：`_touches_ledger_family()` 對各種 staged 清單的判定。"""

    def test_main_ledger_path_matches(self) -> None:
        self.assertTrue(
            car._touches_ledger_family(["docs/06_quality/AutoSDD_Defect_Log.md"]))

    def test_archive_glob_matches(self) -> None:
        self.assertTrue(car._touches_ledger_family(
            ["docs/06_quality/AutoSDD_Defect_Log_archive_31.md"]))

    def test_archive_index_matches(self) -> None:
        self.assertTrue(car._touches_ledger_family(
            ["docs/06_quality/AutoSDD_Defect_Log_archive_INDEX.md"]))

    def test_unrelated_paths_do_not_match(self) -> None:
        self.assertFalse(car._touches_ledger_family(
            ["AutoClaude/autoclaude/core/kernel.py", "README.md"]))

    def test_empty_staged_list_does_not_match(self) -> None:
        self.assertFalse(car._touches_ledger_family([]))

    def test_similarly_named_but_different_file_does_not_match(self) -> None:
        """名稱夠像但少了 `_archive_` 這個必要片段——不可被寬鬆判成命中。"""
        self.assertFalse(car._touches_ledger_family(
            ["docs/06_quality/AutoSDD_Defect_Logs.md"]))


class TestArchiveRequiredProblemsNarrowing(unittest.TestCase):
    """整合層：`archive_required_problems()` 在 bytes+movable 皆觸發的前提下，
    依 `_staged_paths()` 的三種回傳形態分流（觸碰／未觸碰／取不到）。
    """

    def test_touching_ledger_still_blocks(self) -> None:
        ledger = _isolated_ledger(
            "narrowing_touch",
            _row("DEF-999-601", "fixed@x"),  # 已結、無活躍字樣、無交棒字樣 → 應可搬
            _MID_BAND_BYTES,
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(adl, "_LEDGER", ledger), \
             mock.patch.object(adl, "_QUALITY_DIR", ledger.parent), \
             mock.patch.object(
                 car, "_staged_paths",
                 return_value=["docs/06_quality/AutoSDD_Defect_Log.md"]):
            problems = car.archive_required_problems()
        self.assertTrue(problems, "本次 commit 觸碰帳本家族時應維持既有阻斷")
        joined = "\n".join(problems)
        self.assertIn("archive_apply_locked.py", joined,
                      "導引訊息應指向序列化保護版入口，不是裸 archive_defect_log.py --apply")

    def test_not_touching_ledger_is_suppressed(self) -> None:
        """DEF-200-222 判準①核心案例：同一份會觸發 bytes+movable 的帳本，若本次
        commit 的暫存清單完全不含帳本家族任何一員，則不應阻斷。"""
        ledger = _isolated_ledger(
            "narrowing_no_touch",
            _row("DEF-999-602", "fixed@x"),
            _MID_BAND_BYTES,
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(adl, "_LEDGER", ledger), \
             mock.patch.object(adl, "_QUALITY_DIR", ledger.parent), \
             mock.patch.object(
                 car, "_staged_paths",
                 return_value=["AutoClaude/autoclaude/core/kernel.py"]):
            problems = car.archive_required_problems()
        self.assertEqual(
            problems, [],
            "本次 commit 未觸碰帳本家族卻仍觸發——判準①（縮小阻斷面）未生效")

    def test_staged_unavailable_falls_back_to_blocking_with_fail_loud_note(
        self,
    ) -> None:
        """取不到暫存清單（`_staged_paths()` 回 `None`）時，不得 fail-open 靜默放行，
        必須維持既有阻斷並在訊息中說明原因（可稽核，不是靜默）。"""
        ledger = _isolated_ledger(
            "narrowing_unavailable",
            _row("DEF-999-603", "fixed@x"),
            _MID_BAND_BYTES,
        )
        with mock.patch.object(m, "_DEFECT_LOG", ledger), \
             mock.patch.object(adl, "_LEDGER", ledger), \
             mock.patch.object(adl, "_QUALITY_DIR", ledger.parent), \
             mock.patch.object(car, "_staged_paths", return_value=None):
            problems = car.archive_required_problems()
        self.assertTrue(problems, "取不到暫存清單時應維持既有阻斷（fail-loud，非 fail-open）")
        joined = "\n".join(problems)
        self.assertIn("DEF-200-222", joined)
        self.assertIn("無法取得本次 commit 的暫存檔清單", joined)


if __name__ == "__main__":
    unittest.main()
