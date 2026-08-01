#!/usr/bin/env python3
"""tools/check_wrapper_thinness.py 的單元測試（S20 → R10 拍板案(a) hash 釘選）。

R10（DEF-101-134）守門改制：權威判定＝正規化內容 sha256 釘選（白名單化，
終結黑名單軍備競賽——曾三輪被 `for(`/`python3 -c`/`.ForEach(` 繞過）；
黑名單降級為非權威的補充訊號。既有關鍵字測試保留：fake root 內容
必然使 hash 紅燈，關鍵字診斷應伴隨出現（史料回歸鎖繼續有效）。

R60 Scan-E E-A-02：關鍵字偵測原本整段巢狀在「hash 已紅」分支內（＝兩道防線
串聯，更新 pin 即整組失效），已改為**並聯**。本檔下方 `TestKeywordDetectionParallel`
是該修復的回歸鎖（含「pin 已更新」的紅燈斷言＋兩個正控），既有 10 支
`test_forbidden_*` 全部走 `_make_fake_root()`＝必然 hash 紅燈態，對「pin 已更新」
這條路徑天生零訊號，故必須另立。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import re
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

    def test_pin_table_key_set_floor(self) -> None:
        """鍵集合釘選（R12 QA 一審 QA-1）：pin 表被清空/刪鍵時 `len(problems)==
        len(_PINNED_SHA256)` 類動態斷言會退化為 0==0 全綠——此鎖釘死已知四鍵
        必須存在（新增薄殼對時擴充本集合）。"""
        self.assertGreaterEqual(
            set(m._PINNED_SHA256),
            {
                "tools/dev_start.sh",
                "tools/dev_start.ps1",
                "AutoClaude/tools/local_ci_gate.sh",
                "AutoClaude/tools/local_ci_gate.ps1",
                # R61 ADR-XPLAT-002 Phase 1-B：DEF-101-088 由 _EXEMPT_PAIRS 零守門
                # 決策豁免升級為 hash 釘選（UEP 8→6）。
                "AutoClaude/tools/install_git_hooks.sh",
                "AutoClaude/tools/install_git_hooks.ps1",
                "AISDLC_SDD/scripts/install-hooks.sh",
                "AISDLC_SDD/scripts/install-hooks.ps1",
            },
        )

    def test_missing_wrapper_reported(self) -> None:
        # 平台中立的「不存在絕對路徑」（原寫死 Z: 磁碟機路徑在 POSIX 是相對路徑，
        # 碰巧綠——見 test_platform_neutral_paths.py WHY）。
        with mock.patch.object(m, "ROOT", ABS_FAKE_REPO.parent / "nonexistent-repo-root"):
            problems = m.check_wrapper_thinness()
        # 全部釘選 wrapper 皆回報不存在（R12 起釘選對象不只 dev_start，數量隨表走）
        self.assertEqual(len(problems), len(m._PINNED_SHA256))
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
            # fixture 只鋪 dev_start 對——釘選表縮至受測子集（R12 起表內另有
            # local_ci_gate 對，缺檔會汙染本測試的「零問題」斷言）
            dev_start_pins = {
                k: v for k, v in m._PINNED_SHA256.items() if k.startswith("tools/dev_start")
            }
            with mock.patch.object(m, "ROOT", fake_root), \
                 mock.patch.object(m, "_PINNED_SHA256", dev_start_pins):
                problems = m.check_wrapper_thinness()
        self.assertEqual(problems, [])

    def test_main_exit_code_reflects_result(self) -> None:
        with mock.patch.object(m, "check_wrapper_thinness", return_value=[]):
            self.assertEqual(m.main(), 0)
        with mock.patch.object(m, "check_wrapper_thinness", return_value=["x broke"]):
            self.assertEqual(m.main(), 1)


class TestKeywordDetectionParallel(unittest.TestCase):
    """R60 Scan-E E-A-02 回歸鎖：關鍵字偵測必須與 hash 釘選**並聯**，非串聯。

    WHY（測意圖非僅行為，Rule 9）：原實作把整組 `for keyword in _FORBIDDEN…` 縮排在
    `if actual != pinned:` 內，於是「以 `--print-hash` 取新值同步更新 pin」——本工具
    docstring 自己指示的正常維護動作——會把 hash 這道防線合法地消音，**同時**讓關鍵字
    偵測整組失效；MAX_LINES 也還沒到（各殼行數現查 `--print-lines`，餘裕仍大），三道
    訊號一起靜音。R60 round-2（SD-R60-08）：本段原寫死「最長殼 NN 行 / 上限 NN」，屬
    同一個「文件寫死機器算得出的數字」家族，已改為不引具體數字。
    既有 10 支 `test_forbidden_*` 全部用 `_make_fake_root()` 造內容＝必然 hash 紅燈，
    因此對這條路徑天生零鑑別力（它們在串聯實作下也全綠），必須另立本類別。
    """

    def _fake_dev_start(self, td: str, sh_text: str, ps1_text: str) -> Path:
        tools_dir = Path(td) / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / "dev_start.sh").write_text(sh_text, encoding="utf-8", newline="")
        (tools_dir / "dev_start.ps1").write_text(ps1_text, encoding="utf-8", newline="")
        return Path(td)

    def _run_with_refreshed_pins(self, sh_text: str, ps1_text: str) -> list[str]:
        """把 fixture 內容的 hash 當成新 pin（＝模擬 `--print-hash` 工作流），再跑守門。

        fixture 只鋪 dev_start 對，故釘選表縮至該子集（其餘 wrapper 缺檔會汙染斷言）。
        """
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake_root = self._fake_dev_start(td, sh_text, ps1_text)
            refreshed = {
                rel: m.normalized_sha256(fake_root / rel)
                for rel in ("tools/dev_start.sh", "tools/dev_start.ps1")
            }
            with mock.patch.object(m, "ROOT", fake_root), \
                 mock.patch.object(m, "_PINNED_SHA256", refreshed):
                return m.check_wrapper_thinness()

    def setUp(self) -> None:
        self.real_sh = (m.ROOT / "tools/dev_start.sh").read_text(encoding="utf-8")
        self.real_ps1 = (m.ROOT / "tools/dev_start.ps1").read_text(encoding="utf-8")

    def test_pin_refresh_alone_is_green(self) -> None:
        """正控 A：只更新 pin、內容無業務邏輯外溢 → 零問題。

        證明下一支的紅燈不是「一律回報」造成的，而且也釘住『合法的 pin 更新不該
        被本次並聯化變成常態噪音』這個意圖（R60 反駁者對本修法的主要顧慮）。
        """
        self.assertEqual(self._run_with_refreshed_pins(self.real_sh, self.real_ps1), [])

    def test_business_logic_still_caught_after_pin_refresh(self) -> None:
        """本鎖本體：注入 bash `for ` 迴圈**並同步更新 pin** → 仍必須被攔下。

        串聯實作下此案 `problems == []`（R60 實測：87 行、hash 相符、三訊號全靜音）。
        """
        injected = self.real_sh + 'for f in "$@"; do echo "$f"; done\n'
        problems = self._run_with_refreshed_pins(injected, self.real_ps1)
        self.assertEqual(
            [p for p in problems if "hash 與釘選不符" in p], [],
            f"前提失效：pin 已隨 fixture 內容更新，hash 這道防線本應靜音，實得：{problems}",
        )
        self.assertEqual(
            [p for p in problems if "超過薄殼上限" in p], [],
            f"前提失效：注入後行數仍應低於 MAX_LINES={m.MAX_LINES}，實得：{problems}",
        )
        self.assertTrue(
            any("'for '" in p and "dev_start.sh" in p for p in problems),
            "pin 更新後關鍵字偵測失效＝兩道防線又被接成串聯（R60 E-A-02 迴歸）："
            f"{problems}",
        )

    def test_ps1_side_business_logic_still_caught_after_pin_refresh(self) -> None:
        """`.ps1` 側對稱：兩側判準表分開維護，只修 `.sh` 側會留下一半的缺口。"""
        injected = self.real_ps1 + "foreach ($x in @(1,2,3)) { Write-Host $x }\n"
        problems = self._run_with_refreshed_pins(self.real_sh, injected)
        self.assertTrue(
            any("'foreach ('" in p and "dev_start.ps1" in p for p in problems),
            f"pin 更新後 .ps1 側關鍵字偵測失效（R60 E-A-02 迴歸）：{problems}",
        )

    def test_keyword_inside_comment_line_is_not_flagged(self) -> None:
        """正控 B（偽陽性面）：整行註解裡的關鍵字字樣不得命中。

        並聯化的代價風險是「說明文字誤觸→常態噪音→鎖失去可信度」。比對對象刻意
        取正規化內容（與 hash 同一份文字，整行 `#` 註解已剝除），故本案必須全綠。
        誠實邊界：`_normalize()` **不**剝行尾行內註解，`$x=1  # for the win` 仍會命中
        （見 check_wrapper_thinness 檔頭第 3 項的殘餘偽陽性揭露）。
        """
        commented = self.real_sh + "# 說明：業務邏輯的 for 迴圈只能長在 Python 核心內\n"
        self.assertEqual(self._run_with_refreshed_pins(commented, self.real_ps1), [])


class TestBomIsNotContent(unittest.TestCase):
    """R60 P10-1 回歸鎖：`.ps1` 的 UTF-8 BOM 不得被當成腳本內容。

    WHY（測意圖非僅行為，Rule 9）：`_read_source()` 前身是 `read_text(encoding="utf-8")`，
    於是 BOM（U+FEFF）留在文字裡；`_normalize()` 剝掉檔頭 `<# … #>` 後那一行只剩 BOM，
    而 `"\\ufeff".strip()` 在 Python 是**非空**（U+FEFF 屬 Cf、不算 whitespace）⇒ 正規化
    結果多出一行純 BOM 的假行，被釘進權威判定的 sha256 裡。修前實測：最小合成殼
    `NORM_LINES=3 / 首行 repr='\\ufeff'`，修後 `NORM_LINES=2 / 首行 'param()'`；真實
    `tools/integration_gate.ps1` 亦由 14→13（首行 `'\\ufeff'` → `'param('`）。

    這不是美觀問題而是**同一個量兩個答案**：`tools/check_script_parity.py` 對同一批
    `.ps1` 早就用 `utf-8-sig`，兩支工具因此對同一份檔案算出不同的正規化文字。

    🔴 修法邊界：`.ps1` 帶 BOM 是**刻意**的（PS 5.1 對無 BOM 的 UTF-8 檔改用 ANSI
    codepage 解讀、中文全毀；root-infra-ci 另有 BOM 守門），故修的是讀取端，
    **不准**拿掉 BOM——`test_real_ps1_wrappers_really_carry_bom` 同時守住這件事，
    並讓本類別不至於變成恆真斷言（BOM 若消失，本類別的前提就沒了）。
    """

    _BODY = "<#\n.SYNOPSIS\nminimal\n#>\nparam()\nWrite-Host 'x'\n"

    def _write_pair(self, tmp: Path) -> tuple[Path, Path]:
        """同一份內容寫兩份：帶 BOM／不帶 BOM，皆用 CRLF（仿 repo `.ps1` 實況）。"""
        crlf = self._BODY.replace("\n", "\r\n").encode("utf-8")
        with_bom = tmp / "with_bom.ps1"
        without_bom = tmp / "without_bom.ps1"
        with_bom.write_bytes(b"\xef\xbb\xbf" + crlf)
        without_bom.write_bytes(crlf)
        return with_bom, without_bom

    def test_bom_does_not_become_a_normalized_line(self) -> None:
        """本鎖本體：正規化後首行必須是真程式碼，不得是純 BOM 假行。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            with_bom, _ = self._write_pair(Path(td))
            lines = m.normalized_content(with_bom).splitlines()
        self.assertEqual(
            lines, ["param()", "Write-Host 'x'"],
            f"帶 BOM 的 .ps1 正規化結果不對（首行 repr={lines[0]!r} if any）——"
            "BOM 又被當成內容了（P10-1 迴歸：讀檔端漏用 utf-8-sig）",
        )

    def test_bom_presence_does_not_change_hash(self) -> None:
        """語意鎖：BOM 是編碼構件、不是內容 ⇒ 有無 BOM 的同一份腳本 hash 必須相同。

        比「首行不是 BOM」更強：就算未來換別種剝法，只要這條成立，hash 就不會再
        因編碼構件而分歧。修前此斷言必紅（兩者相差恰一行純 BOM 假行）。
        """
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            with_bom, without_bom = self._write_pair(Path(td))
            self.assertEqual(
                m.normalized_content(with_bom), m.normalized_content(without_bom)
            )
            self.assertEqual(
                m.normalized_sha256(with_bom), m.normalized_sha256(without_bom),
                "同一份腳本因 BOM 有無而 hash 不同——BOM 又被釘進權威判定裡",
            )

    def test_read_source_strips_bom_for_both_extensions(self) -> None:
        """讀檔口自身：`.sh`／`.ps1` 都不得讓 U+FEFF 流進下游。

        `.sh` 側目前磁碟上無 BOM，但讀檔口不該依副檔名分歧——否則哪天有人存錯就
        變成另一個只在單一副檔名上成立的盲區。
        """
        import tempfile

        crlf = self._BODY.replace("\n", "\r\n").encode("utf-8")
        with tempfile.TemporaryDirectory() as td:
            for name in ("x.ps1", "x.sh"):
                p = Path(td) / name
                p.write_bytes(b"\xef\xbb\xbf" + crlf)
                with self.subTest(name=name):
                    # 刻意寫成跳脫序列：原始碼裡放裸 U+FEFF 是隱形字元，
                    # 複審讀不到、diff 也看不出來。
                    self.assertNotIn(chr(0xFEFF), m._read_source(p))

    def test_real_ps1_wrappers_really_carry_bom(self) -> None:
        """鑑別力前提（反恆真）：釘選表內的 `.ps1` 在磁碟上**確實**帶 BOM。

        若哪天全部 `.ps1` 都不帶 BOM 了，上面三支就退化成恆真斷言（測不到任何東西），
        而且那本身是 PS 5.1 中文亂碼的前兆——故在此 fail-loud。
        """
        ps1_rels = [r for r in m._PINNED_SHA256 if r.endswith(".ps1")]
        self.assertTrue(ps1_rels, "釘選表裡沒有 .ps1——本類別的前提消失")
        no_bom = [
            rel for rel in ps1_rels
            if not (m.ROOT / rel).read_bytes().startswith(b"\xef\xbb\xbf")
        ]
        self.assertEqual(
            no_bom, [],
            f"下列 .ps1 薄殼已無 UTF-8 BOM：{no_bom}——PS 5.1 會改用 ANSI codepage "
            "解讀導致中文全毀（root-infra-ci 亦有 BOM 守門），請補回 BOM；"
            "同時本類別的鑑別力前提已失效",
        )

    def test_guard_has_a_single_encoding_decision(self) -> None:
        """架構鎖：`check_wrapper_thinness.py` 內只允許 `_read_source()` 一處決定編碼。

        WHY：本缺陷的根因不是「哪個編碼對」，而是「同一支工具的讀檔決策散落在三處」
        （`normalized_content`／`wrapper_line_counts`／`check_wrapper_thinness` 各自
        `read_text`）。只改三處字面值治不了病——下一個新增的讀檔點照樣可以再挑錯一次。
        本鎖以 `ast` 斷言原始碼裡的 `read_text(encoding=…)` 只有一處、且值為 utf-8-sig。
        """
        import ast

        source = Path(m.__file__).read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=Path(m.__file__).name)
        encodings = [
            kw.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "read_text"
            for kw in node.keywords
            if kw.arg == "encoding" and isinstance(kw.value, ast.Constant)
        ]
        self.assertEqual(
            encodings, ["utf-8-sig"],
            f"讀檔編碼決策不再是唯一一處：{encodings}——請一律改走 `_read_source()`"
            "（P10-1：三處各自 read_text 是本缺陷的根因，`utf-8` 會把 BOM 當內容）",
        )


class TestNoHardcodedLineCounts(unittest.TestCase):
    """R60 round-2（SD-R60-08）：guard 本體不得再寫死各薄殼的行數快照。

    WHY（測意圖非僅行為，Rule 9）：`check_wrapper_thinness.py` 原本在 `MAX_LINES`
    上方列了 8 支殼的行數（`dev_start.sh=78 行、…local_ci_gate.ps1=39 行…`），複審
    逐檔實測**8 支全部過期**——其中 `local_ci_gate.ps1` 是同一輪自己改長了卻沒回頭
    同步，清單還把 `run_act.*` 誤記在 `tools/` 下。行數是機器隨時算得出的量，寫進
    原始碼註解就等於製造一份必然腐化的第二真相源（同 DEF-101-289／515 家族，本輪
    另有 ONBOARDING LOC 格的新鮮度鎖）。**只把 8 個數字改對治不了病**：下一輪照樣
    stale。根治＝(a) 刪掉快照、(b) 由 `--print-lines` 現查、(c) 本鎖守著不准寫回。
    """

    # 兩種「行數快照」形狀。第一條對應原註解的 `<檔名>=<數字>`／`.ps1=<數字>` 寫法；
    # 第二條對應中文敘述式的 `<數字> 行`。兩條各附正控樣本（下方 teeth 測試），避免
    # 「鎖存在但抓不到原案」的假綠。
    _CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("`<殼檔名>=<數字>`（例：`dev_start.sh=78`、`bootstrap.sh=24/.ps1=50`）",
         re.compile(r"\.(?:sh|ps1)\s*[=＝:：]\s*\d+")),
        ("`<數字> 行`（例：`75 行`、`上限抓 100 行`）", re.compile(r"\d+\s*行")),
    )

    # 原始碼實況樣本（正控）：這正是 R60 round 1 留在 guard 內、8 支全 stale 的那段。
    _STALE_SNAPSHOT_SAMPLE = (
        "# 目前 dev_start.sh=78 行、dev_start.ps1=75 行、local_ci_gate.sh=23 行、\n"
        "# local_ci_gate.ps1=39 行、bootstrap.sh=24/.ps1=50、\n"
        "# integration_gate.sh=23/.ps1=30、run_act.sh=21/.ps1=54；\n"
        "# 上限抓 100 行，留自然增長空間。\n"
    )

    def test_patterns_have_teeth_against_the_real_stale_snapshot(self) -> None:
        """鑑別力自檢：兩條判準都必須抓得到 round 1 的真實 stale 註解。

        不用合成範例——用被刪掉的那段原文本身當正控（同 repo 慣例：合成範例證明不了
        對真實迴歸有鑑別力）。
        """
        for label, pattern in self._CLAIM_PATTERNS:
            self.assertTrue(
                pattern.search(self._STALE_SNAPSHOT_SAMPLE),
                f"判準 {label} 抓不到 round 1 的真實 stale 註解——鎖無鑑別力",
            )

    def test_patterns_do_not_false_positive_on_benign_text(self) -> None:
        """偽陽性面：不得誤中「不承諾具體行數」的正常敘述與常數本身。"""
        for benign in (
            "MAX_LINES = 100",
            "上限值見 MAX_LINES；各殼行數現查 --print-lines",
            "# R43：補上 WindowsApps guard dot-source（同上 DEF-101-353）",
            '"tools/dev_start.sh": (',
            "# bash 側對稱 .ps1 側 R37 先例",
        ):
            for label, pattern in self._CLAIM_PATTERNS:
                self.assertIsNone(
                    pattern.search(benign),
                    f"判準 {label} 對正常敘述偽陽性：{benign!r}",
                )

    def test_guard_source_has_no_line_count_snapshot(self) -> None:
        """本鎖本體：`tools/check_wrapper_thinness.py` 原始碼不得含行數快照。"""
        source = Path(m.__file__).read_text(encoding="utf-8")
        for label, pattern in self._CLAIM_PATTERNS:
            hits = [
                f"L{i}: {line.strip()}"
                for i, line in enumerate(source.splitlines(), start=1)
                if pattern.search(line)
            ]
            self.assertEqual(
                hits, [],
                f"tools/check_wrapper_thinness.py 又寫死了行數快照（判準 {label}）："
                f"{hits}——行數請一律用 `python tools/check_wrapper_thinness.py "
                "--print-lines` 現查，不要存進註解（SD-R60-08：原快照 8 支全 stale）",
            )

    def test_print_lines_reports_real_counts(self) -> None:
        """產生器側：`wrapper_line_counts()` 必須是真算的，不是另一份寫死表。"""
        counts = m.wrapper_line_counts()
        self.assertEqual(set(counts), set(m._PINNED_SHA256))
        for rel, count in counts.items():
            path = m.ROOT / rel
            self.assertTrue(path.is_file(), f"{rel} 不存在——釘選表與磁碟脫鉤")
            # 走 guard 自己的讀檔口：這裡若另寫 `encoding="utf-8"`，等於在測試側
            # 重建 P10-1 的錯誤慣例（帶 BOM 的 .ps1 又變成第二種讀法）。
            expected = len(m._read_source(path).splitlines())
            self.assertEqual(count, expected, rel)
            self.assertLessEqual(count, m.MAX_LINES, f"{rel} 已超過 MAX_LINES")

    def test_print_lines_cli_mode(self) -> None:
        import contextlib
        import io as _io

        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = m.main(["--print-lines"])
        out = buf.getvalue()
        self.assertEqual(rc, 0)
        for rel, count in m.wrapper_line_counts().items():
            self.assertIn(f"{rel}: {count} / {m.MAX_LINES}", out)

    def test_missing_wrapper_reports_none_line_count(self) -> None:
        with mock.patch.object(m, "ROOT", ABS_FAKE_REPO.parent / "nonexistent-repo-root"):
            counts = m.wrapper_line_counts()
        self.assertTrue(all(v is None for v in counts.values()), counts)


class TestR67ShebangIsNotAComment(unittest.TestCase):
    """R67（Scan-H R67-H35）回歸鎖：首行 shebang 必須進入 hash 輸入。

    WHY（測意圖非僅行為，Rule 9）：薄殼的三項職責第一項就是「選直譯器」，而
    `_normalize()` 原本以 `not line.lstrip().startswith("#")` 一律剝除註解行，
    連 `#!/usr/bin/env bash` 一起吃掉——8 支釘選 `.sh` 的 shebang 可被改成
    `#!/bin/sh` 而 hash 紋風不動（實測 `check_wrapper_thinness.py` rc=0、
    `check_script_parity.py` rc=0、`tools/tests` 全綠）。`tools/dev_start.sh`
    實際用了 `${BASH_SOURCE[0]}` 與 `local`，在 dash（Ubuntu runner 的 /bin/sh）
    下會直接語法/展開失敗。守門對象的頭號職責整條不在覆蓋面內＝這道 hash 鎖對
    「殼被改成用錯直譯器」天生零訊號。

    邊界：本鎖只保證「shebang 變動一律紅」，不保證 shebang 內容本身正確
    （`#!/usr/bin/env python3` 掛在 .sh 上照樣通過釘選——那是另一個判準）。
    """

    def _fake_root(self, tmp_dir: Path, sh_text: str) -> Path:
        tools_dir = tmp_dir / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / "dev_start.sh").write_text(sh_text, encoding="utf-8")
        return tmp_dir

    def _dev_start_sh_pin_only(self) -> dict[str, str]:
        return {
            k: v for k, v in m._PINNED_SHA256.items() if k == "tools/dev_start.sh"
        }

    def test_normalize_keeps_leading_shebang(self) -> None:
        """單元層：shebang 留在正規化文字第一行，其餘註解照舊剝除。"""
        norm = m._normalize("#!/usr/bin/env bash\n# 註解\n\nreal=1\n", is_ps1=False)
        self.assertEqual(norm, "#!/usr/bin/env bash\nreal=1")

    def test_normalize_strips_non_leading_hashbang_like_comment(self) -> None:
        """對照組：非首行的 `#!` 仍是註解（shebang 只有首行才是宣告）。"""
        norm = m._normalize("real=1\n#!/bin/sh\n", is_ps1=False)
        self.assertEqual(norm, "real=1")

    def test_shebang_change_trips_hash(self) -> None:
        """缺陷注入（本鎖的核心）：只把 `#!/usr/bin/env bash` 換成 `#!/bin/sh`、
        其餘一個字元不動 ⇒ 必須紅燈。修前此情境 rc=0 全綠。"""
        import tempfile

        real_sh = (m.ROOT / "tools/dev_start.sh").read_text(encoding="utf-8")
        self.assertTrue(real_sh.startswith("#!/usr/bin/env bash"), "前提：真檔首行是 shebang")
        tampered = real_sh.replace("#!/usr/bin/env bash", "#!/bin/sh", 1)
        with tempfile.TemporaryDirectory() as td:
            fake_root = self._fake_root(Path(td), tampered)
            with mock.patch.object(m, "ROOT", fake_root), \
                 mock.patch.object(m, "_PINNED_SHA256", self._dev_start_sh_pin_only()):
                problems = m.check_wrapper_thinness()
        hash_problems = [p for p in problems if "hash 與釘選不符" in p]
        self.assertEqual(len(hash_problems), 1, f"shebang 換直譯器必須紅燈，實得：{problems}")

    def test_untouched_shebang_is_green(self) -> None:
        """正控（雙向驗證的綠燈側）：同一 fixture 不動 shebang ⇒ 零問題。
        沒有這一支，上一支的紅燈可能只是 fixture 本身壞掉。"""
        import tempfile

        real_sh = (m.ROOT / "tools/dev_start.sh").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            fake_root = self._fake_root(Path(td), real_sh)
            with mock.patch.object(m, "ROOT", fake_root), \
                 mock.patch.object(m, "_PINNED_SHA256", self._dev_start_sh_pin_only()):
                problems = m.check_wrapper_thinness()
        self.assertEqual(problems, [])

    def test_comment_only_change_still_green_alongside_shebang_lock(self) -> None:
        """界線宣告：本鎖不得把「僅增註解」也一起攔下——shebang 是宣告、註解仍是註解。
        （與既有 `test_comment_only_change_does_not_trip_hash` 並存，這支專證兩者可共存。）"""
        import tempfile

        real_sh = (m.ROOT / "tools/dev_start.sh").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            fake_root = self._fake_root(Path(td), real_sh + "\n# 事後補的說明註解\n")
            with mock.patch.object(m, "ROOT", fake_root), \
                 mock.patch.object(m, "_PINNED_SHA256", self._dev_start_sh_pin_only()):
                problems = m.check_wrapper_thinness()
        self.assertEqual(problems, [])

    def test_every_pinned_sh_carries_its_shebang_into_the_hash(self) -> None:
        """全面性：釘選面內每一支 `.sh` 的正規化首行都必須是它自己的 shebang——
        防「只有 dev_start 被修好、其餘 6 支仍在覆蓋面外」。"""
        checked = 0
        for rel in m._PINNED_SHA256:
            path = m.ROOT / rel
            if path.suffix != ".sh" or not path.is_file():
                continue
            first_line = m._read_source(path).splitlines()[0]
            self.assertTrue(first_line.startswith("#!"), f"{rel} 首行非 shebang：{first_line!r}")
            self.assertEqual(
                m.normalized_content(path).splitlines()[0], first_line,
                f"{rel} 的 shebang 未進入 hash 輸入",
            )
            checked += 1
        self.assertGreaterEqual(checked, 7, "釘選面內 .sh 支數低於預期，鎖可能已空轉")


if __name__ == "__main__":
    unittest.main()
