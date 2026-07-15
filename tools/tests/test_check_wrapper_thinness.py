#!/usr/bin/env python3
"""tools/check_wrapper_thinness.py 的單元測試（S20：薄殼 wrapper 退化守門）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_wrapper_thinness as m  # noqa: E402


class TestCheckWrapperThinness(unittest.TestCase):
    def test_real_wrappers_pass_today(self) -> None:
        """回歸防護的基本前提：本檢查對 repo 目前真實的 dev_start.sh/.ps1 必須是
        全綠 —— 若本測試失敗，代表黑名單/行數上限本身誤中現有合法內容。"""
        problems = m.check_wrapper_thinness()
        self.assertEqual(problems, [])

    def test_missing_wrapper_reported(self) -> None:
        with mock.patch.object(m, "ROOT", Path("Z:/nonexistent-repo-root")):
            problems = m.check_wrapper_thinness()
        self.assertEqual(len(problems), 2)  # 兩份 wrapper 皆回報不存在
        self.assertTrue(all("檔案不存在" in p for p in problems))

    def _make_fake_root(self, tmp_dir: Path, sh_text: str, ps1_text: str) -> Path:
        tools_dir = tmp_dir / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / "dev_start.sh").write_text(sh_text, encoding="utf-8")
        (tools_dir / "dev_start.ps1").write_text(ps1_text, encoding="utf-8")
        return tmp_dir

    def test_line_count_violation_detected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="\n".join(f"# line {i}" for i in range(m.MAX_LINES + 5)),
                ps1_text="# short and fine\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        sh_problems = [p for p in problems if "dev_start.sh" in p and "超過薄殼上限" in p]
        self.assertEqual(len(sh_problems), 1)
        ps1_problems = [p for p in problems if "dev_start.ps1" in p]
        self.assertEqual(ps1_problems, [])

    def test_forbidden_keyword_in_sh_detected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="while true; do echo x; done\n",
                ps1_text="# fine\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("'while '" in p for p in problems))

    def test_forbidden_keyword_in_ps1_detected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="# fine\n",
                ps1_text="$data = ConvertFrom-Json $raw\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("ConvertFrom-Json" in p for p in problems))

    def test_main_exit_code_reflects_result(self) -> None:
        with mock.patch.object(m, "check_wrapper_thinness", return_value=[]):
            self.assertEqual(m.main(), 0)
        with mock.patch.object(m, "check_wrapper_thinness", return_value=["x broke"]):
            self.assertEqual(m.main(), 1)


if __name__ == "__main__":
    unittest.main()
