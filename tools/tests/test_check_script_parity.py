#!/usr/bin/env python3
"""tools/check_script_parity.py 的單元測試（R9 跨平台複審落地）。

守兩個「靜默退出守護範圍」的回歸鎖：
  1. gate 呼叫抽取須同時接受單/雙引號——舊版只認單引號，兩側同步改雙引號時
     該 gate 會靜默消失於比對清單且雙邊一致、無任何 diff 訊號。
  2. 抽取數量下限釘選（_MIN_EXTRACT_COUNTS）——宣告 pattern 被同步改寫時，
     數量低於釘選值必須紅燈，不得假綠。

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
import check_script_parity as m  # noqa: E402

# 系統暫存目錄放測試用 fixture 檔（非 repo 內），process 結束自動清除。
_TMP_DIR = Path(tempfile.mkdtemp(prefix="script_parity_test_"))
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))
_tmp_counter = [0]


def _write_tmp(text: str, suffix: str = ".sh") -> Path:
    _tmp_counter[0] += 1
    p = _TMP_DIR / f"fixture_{_tmp_counter[0]}{suffix}"
    p.write_text(text, encoding="utf-8")
    return p


class TestExtractGateCallsQuoteStyles(unittest.TestCase):
    def test_double_quoted_gate_calls_extracted(self) -> None:
        """R9 回歸鎖：雙引號 gate 呼叫必須被抽取（舊版只認單引號 → 兩側同步改
        雙引號時該 gate 靜默退出守護範圍且無 diff 訊號）。"""
        path = _write_tmp(
            'run_gate "pytest full suite" cmd_a\n'
            'run_gate "lint-imports" cmd_b\n'
        )
        self.assertEqual(
            m._extract_gate_calls(path, "run_gate"),
            ["pytest full suite", "lint-imports"],
        )

    def test_mixed_single_and_double_quotes_preserve_order(self) -> None:
        path = _write_tmp(
            "run_gate 'gate one' cmd_a\n"
            'run_gate "gate two" cmd_b\n'
            "run_gate 'gate three' cmd_c\n"
        )
        self.assertEqual(
            m._extract_gate_calls(path, "run_gate"),
            ["gate one", "gate two", "gate three"],
        )


class TestExtractFloor(unittest.TestCase):
    def test_below_floor_is_red(self) -> None:
        """R9 回歸鎖：任一側抽取數量低於 _MIN_EXTRACT_COUNTS 釘選即紅燈——
        即使雙邊清單完全一致（同步改壞宣告 pattern 的典型形狀）。"""
        floor = m._MIN_EXTRACT_COUNTS["local_ci_gate"]
        short = [f"gate {i}" for i in range(floor - 1)]
        with mock.patch("builtins.print"):
            self.assertFalse(m._check_extract_floor("local_ci_gate", short, short))

    def test_at_floor_passes(self) -> None:
        floor = m._MIN_EXTRACT_COUNTS["local_ci_gate"]
        items = [f"gate {i}" for i in range(floor)]
        with mock.patch("builtins.print"):
            self.assertTrue(m._check_extract_floor("local_ci_gate", items, items))

    def test_red_message_points_to_pin_update(self) -> None:
        """紅燈訊息必須指路：刻意刪減 step 時要同步更新釘選值（訊息說清楚）。"""
        with mock.patch("builtins.print") as fake_print:
            m._check_extract_floor("bootstrap", ["a"], ["a"])
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("_MIN_EXTRACT_COUNTS", printed)
        self.assertIn("bootstrap", printed)


if __name__ == "__main__":
    unittest.main()
