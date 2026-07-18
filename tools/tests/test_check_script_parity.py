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


class TestPairEnrollment(unittest.TestCase):
    """R10 拍板案(a)（DEF-101-134）：成對腳本註冊完整性發現鎖。

    WHY：marker_pairs / thinness 對象皆硬編碼——過去新增一對 .sh/.ps1 而不掛
    任何守門是零訊號的結構性缺口（Architect『新增腳本可繞過 parity 守門』）。
    此鎖使未納管對子紅燈、註冊清單 stale 亦紅燈。
    """

    def test_real_tree_enrollment_passes(self) -> None:
        self.assertTrue(m._check_pair_enrollment())

    def test_unknown_pair_detected(self) -> None:
        fake_root = _TMP_DIR / "enroll_unknown"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "rogue_pair.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (fake_root / "tools" / "rogue_pair.ps1").write_text("# x\n", encoding="utf-8")
        with mock.patch.object(m, "_REPO_ROOT", fake_root), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("rogue_pair", printed)
        self.assertIn("未註冊的成對腳本", printed)

    def test_stale_registration_detected(self) -> None:
        fake_root = _TMP_DIR / "enroll_stale"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)  # 空目錄，無任何對子
        with mock.patch.object(m, "_REPO_ROOT", fake_root), \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment()
        self.assertFalse(ok)
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        self.assertIn("stale", printed)


class TestSingleSidedEnrollment(unittest.TestCase):
    """R11 架構改善 C2：單邊（孤兒）腳本納管發現鎖。

    WHY：R11 前 _discover_pairs 只認同名成對——新增一支只有 .sh 或只有 .ps1 的
    腳本零機械訊號（跨平台對等從未被追問）。此鎖使未登記單邊紅燈、豁免清單
    stale（檔案消失或對邊已出現）亦紅燈。
    """

    @staticmethod
    def _patched(fake_root: Path, single_exempt: dict[str, str]):
        """把全部註冊清單 mock 成空、只保留受測的單邊豁免——隔離真 repo 清單。"""
        return (
            mock.patch.object(m, "_REPO_ROOT", fake_root),
            mock.patch.object(m, "_MARKER_PAIRS", []),
            mock.patch.object(m, "_GATECALL_ENROLLED", set()),
            mock.patch.object(m, "_THINNESS_ENROLLED", set()),
            mock.patch.object(m, "_EXEMPT_PAIRS", {}),
            mock.patch.object(m, "_SINGLE_SIDED_EXEMPT", single_exempt),
        )

    def _run_enrollment(self, fake_root: Path, single_exempt: dict[str, str]):
        patches = self._patched(fake_root, single_exempt)
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], \
             mock.patch("builtins.print") as fake_print:
            ok = m._check_pair_enrollment()
        printed = " ".join(
            str(arg) for call in fake_print.call_args_list for arg in call.args
        )
        return ok, printed

    def test_unregistered_single_sided_script_fails(self) -> None:
        """反例：磁碟上有未登記的單邊腳本 → 必紅並點名。"""
        fake_root = _TMP_DIR / "single_unknown"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "rogue_single.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        ok, printed = self._run_enrollment(fake_root, {})
        self.assertFalse(ok)
        self.assertIn("rogue_single.sh", printed)
        self.assertIn("未納管的單邊腳本", printed)

    def test_exempted_single_sided_script_passes(self) -> None:
        """正例：已附決策依據登記的單邊腳本 → 綠。"""
        fake_root = _TMP_DIR / "single_exempt"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "lonely.ps1").write_text("# x\n", encoding="utf-8")
        ok, printed = self._run_enrollment(
            fake_root, {"tools/lonely.ps1": "測試豁免依據"}
        )
        self.assertTrue(ok, f"已豁免單邊不應紅燈，輸出：{printed}")

    def test_stale_single_sided_exemption_file_gone_fails(self) -> None:
        """stale 之一：豁免清單條目的檔案已消失 → 紅（防清單腐化）。"""
        fake_root = _TMP_DIR / "single_stale_gone"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        ok, printed = self._run_enrollment(
            fake_root, {"tools/ghost.sh": "測試豁免依據"}
        )
        self.assertFalse(ok)
        self.assertIn("ghost.sh", printed)
        self.assertIn("stale", printed)

    def test_stale_single_sided_exemption_pair_appeared_fails(self) -> None:
        """stale 之二：對邊腳本已出現（不再是單邊）→ 紅並指路重新納管——
        run_local_nightly.sh 已於 R11（DEF-101-163）落地並依本語意轉登記為
        _EXEMPT_PAIRS 成對豁免（本案例正是當時實際出訊號的機制）。"""
        fake_root = _TMP_DIR / "single_stale_paired"
        (fake_root / "tools").mkdir(parents=True, exist_ok=True)
        (fake_root / "tools" / "lonely.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (fake_root / "tools" / "lonely.ps1").write_text("# x\n", encoding="utf-8")
        ok, printed = self._run_enrollment(
            fake_root, {"tools/lonely.ps1": "測試豁免依據"}
        )
        self.assertFalse(ok)
        self.assertIn("對邊腳本已出現", printed)
        self.assertIn("未註冊的成對腳本", printed)  # 新對子 unknown 的第二訊號


if __name__ == "__main__":
    unittest.main()
