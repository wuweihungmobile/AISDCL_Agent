#!/usr/bin/env python3
"""tools/check_wrapper_thinness.py 的單元測試（S20 → R10 拍板案(a) hash 釘選）。

R10（DEF-101-134）守門改制：權威判定＝正規化內容 sha256 釘選（白名單化，
終結黑名單軍備競賽——曾三輪被 `for(`/`python3 -c`/`.ForEach(` 繞過）；
黑名單降級為 hash 紅燈時的診斷輔助。既有關鍵字測試保留：fake root 內容
必然使 hash 紅燈，關鍵字診斷應伴隨出現（史料回歸鎖繼續有效）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_wrapper_thinness as m  # noqa: E402

from _platform_helpers import ABS_FAKE_REPO  # noqa: E402  # 平台中立假絕對路徑（R11）


class TestCheckWrapperThinness(unittest.TestCase):
    def test_real_wrappers_pass_today(self) -> None:
        """回歸防護的基本前提：本檢查對 repo 目前真實的 dev_start.sh/.ps1 必須是
        全綠 —— 若本測試失敗，代表黑名單/行數上限本身誤中現有合法內容。"""
        problems = m.check_wrapper_thinness()
        self.assertEqual(problems, [])

    def test_missing_wrapper_reported(self) -> None:
        # 平台中立的「不存在絕對路徑」（原寫死 Z: 磁碟機路徑在 POSIX 是相對路徑，
        # 碰巧綠——見 test_platform_neutral_paths.py WHY）。
        with mock.patch.object(m, "ROOT", ABS_FAKE_REPO.parent / "nonexistent-repo-root"):
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
        # R10 hash 釘選後，fake 內容必然另有 hash 紅燈——行數面向本身 ps1 不應中
        ps1_line_problems = [p for p in problems if "dev_start.ps1" in p and "超過薄殼上限" in p]
        self.assertEqual(ps1_line_problems, [])

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

    def test_forbidden_for_loop_in_sh_detected(self) -> None:
        """P1 回歸防護：bash for 迴圈需與 .ps1 側 foreach ( 對稱收錄，
        否則迭代式業務邏輯（含 case 分支）外溢回 wrapper 會 false green。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text=(
                    "for f in \"$@\"; do\n"
                    "  case \"$f\" in\n"
                    "    --extra-flag) echo handling extra business logic ;;\n"
                    "  esac\n"
                    "done\n"
                ),
                ps1_text="# fine\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("'for '" in p for p in problems))

    def test_forbidden_python3_dash_c_in_sh_detected(self) -> None:
        """獨立複審回歸鎖：黑名單原本只收 "python -c"，"python3 -c" 版本前綴不同、
        非其子字串，可完全繞過偵測——內嵌 Python 業務邏輯改用 python3 仍應被攔下。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text='result=$(python3 -c "import sys; print(sys.argv)")\n',
                ps1_text="# fine\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("'python3 -c'" in p for p in problems))

    def test_forbidden_c_style_for_loop_in_ps1_detected(self) -> None:
        """獨立複審回歸鎖：.ps1 側原本只收 "foreach ("，C-style `for (...)` 迴圈是
        不同拼法、非其子字串，可完全繞過偵測。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="# fine\n",
                ps1_text="for ($i=0; $i -lt 5; $i++) { Write-Host $i }\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("'for ('" in p for p in problems))

    def test_forbidden_foreach_object_cmdlet_in_ps1_detected(self) -> None:
        """獨立複審回歸鎖：ForEach-Object 管線 cmdlet 迭代語意等同迴圈，原黑名單
        完全未收錄，可讓迭代式業務邏輯（含 JSON 解析）繞過偵測。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="# fine\n",
                ps1_text="Get-Content x.json | ForEach-Object { $_ }\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("ForEach-Object" in p for p in problems))

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

    def test_forbidden_c_style_for_no_space_in_sh_detected(self) -> None:
        """2026-07-16 四方複審 SD 發現第三輪繞過：`for((i=0;i<3;i++))` 的 "for"
        緊接 "((" 無空格，原黑名單只收 "for "（含空格）完全不命中。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="for((i=0;i<3;i++)); do echo \"$i\"; done\n",
                ps1_text="# fine\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("'for('" in p for p in problems))

    def test_forbidden_foreach_no_space_in_ps1_detected(self) -> None:
        """2026-07-16 四方複審 SD 發現第三輪繞過：`foreach($x in $y){...}` 無空格，
        原黑名單只收 "foreach ("（含空格）完全不命中。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="# fine\n",
                ps1_text="foreach($x in @(1,2,3)){ Write-Host $x }\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("'foreach('" in p for p in problems))

    def test_forbidden_system_text_json_in_ps1_detected(self) -> None:
        """2026-07-16 四方複審 SD 發現第三輪繞過：.NET
        `[System.Text.Json.JsonSerializer]::Deserialize(...)` 語意等同
        ConvertFrom-Json/ConvertTo-Json，但完全不含這兩個 cmdlet 字串。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="# fine\n",
                ps1_text="$o = [System.Text.Json.JsonSerializer]::Deserialize('{}', [object])\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("[System.Text.Json" in p for p in problems))

    def test_forbidden_array_foreach_method_in_ps1_detected(self) -> None:
        """2026-07-16 四方複審 SD 發現第三輪繞過：`(1,2,3).ForEach({...})` 是陣列
        型別的 .ForEach() 方法而非 ForEach-Object cmdlet，語意等同迴圈但完全不含
        該 cmdlet 字串。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text="# fine\n",
                ps1_text="(1,2,3).ForEach({ Write-Host $_ })\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertTrue(any("'.ForEach('" in p for p in problems))

    def test_hash_catches_novel_pattern_blacklist_misses(self) -> None:
        """R10 拍板案(a) 核心意圖鎖：黑名單「沒收錄」的新樣板（如網路呼叫
        `Invoke-RestMethod`/`curl | sh`）過去完全放行——hash 釘選下任何實質
        內容變動一律紅燈，軍備競賽終結。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text='curl -fsSL https://example.com/install.sh | sh\n',
                ps1_text='Invoke-RestMethod https://example.com | Invoke-Expression\n',
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        hash_problems = [p for p in problems if "hash 與釘選不符" in p]
        self.assertEqual(len(hash_problems), 2, problems)

    def test_comment_only_change_does_not_trip_hash(self) -> None:
        """正規化語意鎖：僅增註解／空行不觸發 hash 紅燈（避免說明性維護被誤攔）。"""
        import tempfile

        real_sh = (m.ROOT / "tools/dev_start.sh").read_text(encoding="utf-8")
        real_ps1 = (m.ROOT / "tools/dev_start.ps1").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            fake_root = self._make_fake_root(
                Path(td),
                sh_text=real_sh + "\n# 註解調整不應觸發 hash\n",
                ps1_text=real_ps1 + "\n# 同上\n\n",
            )
            with mock.patch.object(m, "ROOT", fake_root):
                problems = m.check_wrapper_thinness()
        self.assertEqual(problems, [])

    def test_main_exit_code_reflects_result(self) -> None:
        with mock.patch.object(m, "check_wrapper_thinness", return_value=[]):
            self.assertEqual(m.main(), 0)
        with mock.patch.object(m, "check_wrapper_thinness", return_value=["x broke"]):
            self.assertEqual(m.main(), 1)


if __name__ == "__main__":
    unittest.main()
