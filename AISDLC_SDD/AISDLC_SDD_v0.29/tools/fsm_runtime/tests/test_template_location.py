# enforces (governance rules): R-9.8
"""DEF-15-001 深層重構回歸鎖：FSM 種子模板須在 tracked 源碼位，非 runtime 輸出目錄。

WHY：種子模板（state_loader._load_template() 必需的真輸入）原寄居於 runtime 輸出目錄
build/reports/fsm/，導致 copy_on_evolve.sh 須特例補回 + .gitignore 須逐層 negate（反覆打
補丁的結構異味，DEF-11-001/15-001 家族）。improving_22 將其移至 tools/fsm_runtime/templates/
（與 loader 同層、tracked、build/reports 之外）。下列測試鎖定此意圖：若模板被移回 build/reports
或 TEMPLATE_PATH 指回輸出目錄，即紅。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import state_loader  # noqa: E402


class TemplateLocationTests(unittest.TestCase):
    def test_template_path_in_tracked_source_not_build_reports(self) -> None:
        """TEMPLATE_PATH 必落在 tools/fsm_runtime/templates/，且不得在 build/reports/ 下。"""
        p = state_loader.TEMPLATE_PATH.resolve()
        parts = p.parts
        self.assertIn("templates", parts, f"模板未在 templates/ 源碼位：{p}")
        self.assertEqual(p.parent.name, "templates")
        self.assertEqual(p.parent.parent.name, "fsm_runtime")
        self.assertNotIn(
            "reports", parts,
            f"模板不得寄居 runtime 輸出目錄 build/reports/（DEF-15-001 深層回歸）：{p}",
        )

    def test_template_file_present_and_loadable(self) -> None:
        """模板實體存在且可被 _load_template() 載入為非空 dict（FSM bootstrap 真輸入）。"""
        self.assertTrue(
            state_loader.TEMPLATE_PATH.is_file(),
            f"FSM 種子模板不存在於 {state_loader.TEMPLATE_PATH}",
        )
        doc = state_loader._load_template()
        self.assertIsInstance(doc, dict)
        self.assertTrue(doc, "種子模板載入後為空 dict")

    def test_state_output_dir_unchanged(self) -> None:
        """runtime 狀態檔輸出目錄仍為 build/reports/fsm/（輸入移走、輸出不動）。"""
        d = state_loader.DEFAULT_STATE_DIR.resolve()
        self.assertEqual(d.name, "fsm")
        self.assertEqual(d.parent.name, "reports")
        self.assertEqual(d.parent.parent.name, "build")


if __name__ == "__main__":
    unittest.main()
