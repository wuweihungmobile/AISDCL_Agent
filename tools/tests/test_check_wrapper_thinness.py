#!/usr/bin/env python3
"""tools/check_wrapper_thinness.py 的單元測試（S20 → R10 拍板案(a) hash 釘選）。

R10（DEF-101-134）守門改制：權威判定＝正規化內容 sha256 釘選（白名單化，
終結黑名單軍備競賽——曾三輪被 `for(`/`python3 -c`/`.ForEach(` 繞過）；
黑名單降級為非權威的補充訊號。既有關鍵字測試保留：fake root 內容
必然使 hash 紅燈，關鍵字診斷應伴隨出現（史料回歸鎖繼續有效）。

R60 Scan-E E-A-02：關鍵字偵測原本整段巢狀在「hash 已紅」分支內（＝兩道防線
串聯，更新 pin 即整組失效），已改為**並聯**。本檔下方 `TestKeywordDetectionParallel`
是該修復的回歸鎖（含「pin 已更新」的紅燈斷言＋兩個正控），10 個 forbidden 注入樣本
（R85 起收斂成單一表驅動判準，見 TestCheckWrapperThinness 內的注入表）全部走
`_make_fake_root()`＝必然 hash 紅燈態，對「pin 已更新」這條路徑天生零訊號，故必須另立。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _platform_helpers import ABS_FAKE_REPO  # noqa: E402  # 平台中立假絕對路徑（R11）

import check_wrapper_thinness as m  # noqa: E402


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
        # 🔴 兩種病因**刻意分成兩條訊息**（本輪併表）：固定相對路徑鍵是「檔案不存在」；
        # LATEST 鍵在 ROOT 被指到空目錄時連版本都解析不出來，那是另一回事，讀者的下一步
        # 也不同（一個去找檔案、一個去看 sdd_version.py）。此處逐筆要求命中其中之一，
        # 不接受任何一筆落在兩者之外＝靜默略過。
        self.assertTrue(
            all("檔案不存在" in p or "LATEST 版本解析失敗" in p for p in problems),
            problems,
        )
        self.assertEqual(
            sum("LATEST 版本解析失敗" in p for p in problems),
            sum(k.startswith(m._LATEST_KEY_PREFIX) for k in m._PINNED_SHA256),
            "LATEST 鍵未逐鍵回報解析失敗——解析不出來卻少報，等於釘選面無聲縮小",
        )

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

    #: 10 支史料回歸鎖的**單一判準表**（R85／訴求 2）。立案事實：同一個判準原本被寫了
    #: 10 遍，每一遍只有「注入什麼」與「期望診斷裡出現哪個 token」不同，其餘 12 行鷹架
    #: （tempfile → _make_fake_root → mock ROOT → check_wrapper_thinness）逐字相同。
    #: 🔴 **被拿掉的是那 10 份一模一樣的鷹架，不是覆蓋**：10 個注入樣本一個不少、期望
    #: token 一個不變，案例名與立案史料改由 subTest 的 case／why 逐案報出（哪一列紅的
    #: 在失敗訊息裡看得到）。判準本身（注入 → 必須被診斷命中）一個字都沒動。
    _FORBIDDEN_CASES: tuple[tuple[str, str, str, str, str], ...] = (
        ("sh:while", "while true; do echo x; done\n", "# fine\n",
         "'while '", "S20 原始黑名單"),
        ("sh:for-loop",
         'for f in "$@"; do\n  case "$f" in\n'
         "    --extra-flag) echo handling extra business logic ;;\n"
         "  esac\ndone\n", "# fine\n", "'for '",
         "P1 回歸防護：bash for 迴圈需與 .ps1 側 foreach ( 對稱收錄，"
         "否則迭代式業務邏輯（含 case 分支）外溢回 wrapper 會 false green"),
        ("sh:python3-dash-c",
         'result=$(python3 -c "import sys; print(sys.argv)")\n', "# fine\n",
         "'python3 -c'",
         "DEF-101-083 獨立複審：黑名單原本只收 python -c，python3 版本前綴不同、"
         "非其子字串，可完全繞過偵測"),
        ("ps1:c-style-for", "# fine\n",
         "for ($i=0; $i -lt 5; $i++) { Write-Host $i }\n", "'for ('",
         "DEF-101-083 獨立複審：.ps1 側原本只收 foreach (，C-style for (...) 是"
         "不同拼法、非其子字串"),
        ("ps1:foreach-object", "# fine\n",
         "Get-Content x.json | ForEach-Object { $_ }\n", "ForEach-Object",
         "DEF-101-083 獨立複審：ForEach-Object 管線 cmdlet 迭代語意等同迴圈，"
         "原黑名單完全未收錄"),
        ("ps1:convertfrom-json", "# fine\n", "$data = ConvertFrom-Json $raw\n",
         "ConvertFrom-Json", "S20 原始黑名單"),
        ("sh:for-no-space", 'for((i=0;i<3;i++)); do echo "$i"; done\n', "# fine\n",
         "'for('",
         "DEF-101-095 四方複審 SD 第三輪繞過：for((i=0;i<3;i++)) 的 for 緊接 (( 無空格，"
         "原黑名單只收含空格的 for "),
        ("ps1:foreach-no-space", "# fine\n",
         "foreach($x in @(1,2,3)){ Write-Host $x }\n", "'foreach('",
         "DEF-101-095 四方複審 SD 第三輪繞過：foreach($x in $y){...} 無空格，"
         "原黑名單只收含空格的 foreach ("),
        ("ps1:system-text-json", "# fine\n",
         "$o = [System.Text.Json.JsonSerializer]::Deserialize('{}', [object])\n",
         "[System.Text.Json",
         "DEF-101-095 四方複審 SD 第三輪繞過：.NET JsonSerializer 語意等同 "
         "ConvertFrom-Json/ConvertTo-Json，但完全不含這兩個 cmdlet 字串"),
        ("ps1:array-foreach-method", "# fine\n",
         "(1,2,3).ForEach({ Write-Host $_ })\n", "'.ForEach('",
         "DEF-101-095 四方複審 SD 第三輪繞過：(1,2,3).ForEach({...}) 是陣列型別的 "
         ".ForEach() 方法而非 ForEach-Object cmdlet"),
    )

    def test_forbidden_patterns_are_detected(self) -> None:
        """史料回歸鎖：每一個曾經繞過黑名單的寫法，今天都必須被診斷命中。

        WHY 逐案而不是「有任何一筆命中就算過」：本族的立案史料是**三輪繞過**，每一輪
        補的是不同拼法；用聚合斷言的話，任一拼法被刪掉都不會轉紅（而那正是這族在防的）。
        """
        import tempfile

        self.assertEqual(
            len(self._FORBIDDEN_CASES), 10,
            "注入樣本數變了——本族是史料回歸鎖，樣本只准增不准減；"
            "真的要退役某一列，請連同 _FORBIDDEN 內對應關鍵字一起談")
        for name, sh_text, ps1_text, token, why in self._FORBIDDEN_CASES:
            with self.subTest(case=name, why=why):
                with tempfile.TemporaryDirectory() as td:
                    fake_root = self._make_fake_root(
                        Path(td), sh_text=sh_text, ps1_text=ps1_text)
                    with mock.patch.object(m, "ROOT", fake_root):
                        problems = m.check_wrapper_thinness()
                self.assertTrue(
                    any(token in p for p in problems),
                    f"{name} 注入後診斷未出現 {token}（立案：{why}）；實得：{problems}")

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
        # 顯式傳 `[]`＝直說「零引數」。史料（R74，勿逐字沿用成現況）：`main(argv=None)`
        # 當時讀的是 `sys.argv[1:]`＝**跑測試的那條命令列**，於是 `m.main()` 在測「零引數
        # 行為」時其實餵了一整串 pytest 旗標進去。R75 已把讀 `sys.argv` 收進 `cli()`
        # （見 `TestRootGateToolsRejectUnknownFlags::test_rejection_never_reads_sys_argv_
        # inside_main`），故這個 `[]` 現在只是顯式，不再承載保護作用。
        with mock.patch.object(m, "check_wrapper_thinness", return_value=[]):
            self.assertEqual(m.main([]), 0)
        with mock.patch.object(m, "check_wrapper_thinness", return_value=["x broke"]):
            self.assertEqual(m.main([]), 1)


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
        latest_tools = m.latest_tools_root()
        ps1_rels = [r for r in m._PINNED_SHA256 if r.endswith(".ps1")]
        self.assertTrue(ps1_rels, "釘選表裡沒有 .ps1——本類別的前提消失")
        # 走 guard 自己的鍵→路徑解析（本輪併表後 LATEST 鍵不能再用 `ROOT / rel`
        # 拼——那樣拼出來的路徑不存在，恰好會讓本斷言靜默略過它）。
        no_bom = [
            rel for rel in ps1_rels
            if not m.pinned_path(rel, latest_tools).read_bytes().startswith(b"\xef\xbb\xbf")
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
        latest_tools = m.latest_tools_root()
        for rel, count in counts.items():
            path = m.pinned_path(rel, latest_tools)
            self.assertIsNotNone(path, f"{rel} 解析不出實體路徑（LATEST 解析失敗？）")
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
        防「只有 dev_start 被修好、其餘 6 支仍在覆蓋面外」。

        🔴 本輪併表時**差點在這裡開一個靜默洞**：本迴圈原本以 `ROOT / rel` 拼路徑並在
        `not path.is_file()` 時 `continue`，於是新併入的 LATEST 鍵會被無聲略過、而
        `checked` 仍達得到舊下限 ⇒ 覆蓋面縮小卻全綠。改走 guard 自己的鍵→路徑解析，
        並把下限一併上修（下限只准上修，這裡是收緊不是放寬）。
        """
        latest_tools = m.latest_tools_root()
        checked = 0
        for rel in m._PINNED_SHA256:
            path = m.pinned_path(rel, latest_tools)
            self.assertIsNotNone(path, f"{rel} 解析不出實體路徑（LATEST 解析失敗？）")
            if path.suffix != ".sh" or not path.is_file():
                continue
            first_line = m._read_source(path).splitlines()[0]
            self.assertTrue(first_line.startswith("#!"), f"{rel} 首行非 shebang：{first_line!r}")
            self.assertEqual(
                m.normalized_content(path).splitlines()[0], first_line,
                f"{rel} 的 shebang 未進入 hash 輸入",
            )
            checked += 1
        self.assertGreaterEqual(checked, 8, "釘選面內 .sh 支數低於預期，鎖可能已空轉")


class TestConvergenceTargetsArePerShell(unittest.TestCase):
    """本輪 E-05b：違規訊息的「該收斂到哪」必須逐殼查表，且那個目的地要真的在。

    病灶（修前逐字）：行數上限與 hash 不符兩條訊息一律寫「業務邏輯應收斂進
    `tools/dev_start.py`」，**不看 `rel` 屬於哪一棵樹**。兩個問題疊在一起——
      (1) 語意錯：`AISDLC_SDD/scripts/install-hooks.*` 的契約住
          `tools/git_hooks_install_common.py`，`AutoClaude/tools/run_act.*` 的核心是
          `run_act_core.py`，都不是 dev_start；
      (2) 可滿足性：被無條件指路的那支檔是 shrink-only 特例棘輪、餘裕個位數，照訊息
          辦事極可能當場撞 LOC violation（Scan-H 必跑項⑥「A 鎖要你加、B 鎖不准你加」）。
    這條分支從未被觸發過（受管殼全部遠低於上限），所以修前沒有任何人會發現。
    """

    def test_every_pinned_key_has_a_registered_core(self) -> None:
        """涵蓋面：每個釘選鍵都查得到目的地——查無登記時函式回 fail-loud 字樣，
        本斷言即是在擋那個字樣出現在真表上。"""
        unmapped = [
            rel for rel in m._PINNED_SHA256
            if "_CORE_TARGET 未登記" in m.convergence_target(rel)
        ]
        self.assertEqual(unmapped, [], f"下列釘選鍵沒有收斂目的地：{unmapped}")

    def test_every_registered_core_exists_on_disk(self) -> None:
        """反 stale：指路的目的地若不存在，訊息就是另一種形式的死路。"""
        latest_tools = m.latest_tools_root()
        self.assertIsNotNone(latest_tools, "真 repo 內 LATEST 解析不得失敗")
        missing = []
        for rel in m._PINNED_SHA256:
            target = m.convergence_target(rel)
            path = m.pinned_path(target, latest_tools)
            if path is None or not path.is_file():
                missing.append(target)
        self.assertEqual(sorted(set(missing)), [], f"指路目的地不存在：{missing}")

    def test_targets_really_differ_across_trees(self) -> None:
        """🔴 鑑別力本體：三棵樹不得指向同一個目的地。

        測意圖非僅行為——若哪天有人把 `_CORE_TARGET` 改回「全部指 dev_start」，
        上面兩支照樣全綠（dev_start.py 存在、每個鍵都查得到），只有本支會紅。
        """
        targets = {m.convergence_target(rel) for rel in m._PINNED_SHA256}
        self.assertGreaterEqual(
            len(targets), 4,
            f"收斂目的地只有 {sorted(targets)}——受管殼跨三棵樹，一律指同一個檔正是本"
            "修復要治的病（訊息在架構上錯，且該檔餘裕不足以照做）",
        )


class TestForbiddenKeywordsCoverEveryPin(unittest.TestCase):
    """R79 ARCH：並聯的第三訊號必須覆蓋**每一個**釘選鍵，缺席不得靜默。

    病灶（修前實測）：`_PINNED_SHA256` 16 鍵、`_FORBIDDEN` 只有 14 鍵，缺的兩鍵是
    兩支 LATEST run_tlc 薄殼；`check_wrapper_thinness()` 用 `_FORBIDDEN.get(rel, ())`
    取關鍵字，缺鍵靜默回空 tuple ⇒ 迴圈零次、零訊號。後果是那兩支只剩 hash 一道
    訊號，而**更新 pin 正是它的合法維護動作**——那正是 R60 Scan-E E-A-02 把串聯改
    並聯所要消滅的形態，只是對這兩鍵而言並聯的那一路從落地起就是空的。同一支檔的
    `_CORE_TARGET` 早有對等的完整性鎖（見上一個 class），`_FORBIDDEN` 沒有——同檔內
    的不對稱，而且沒有任何東西會提醒人去補。

    本鎖刻意用「集合相等」而非「子集」：多登記一個已不存在的釘選鍵（stale）與少
    登記一個（缺口）都是問題，兩個方向都要紅。刻意不設關鍵字的殼請寫成顯式的
    `(): # WHY …` 而非缺鍵——讓「這支殼沒有第三訊號」成為 diff 上看得見的決定。
    """

    def test_pinned_keys_and_forbidden_keys_are_the_same_set(self) -> None:
        pinned, forbidden = set(m._PINNED_SHA256), set(m._FORBIDDEN)
        self.assertEqual(
            pinned, forbidden,
            f"_FORBIDDEN 未涵蓋的釘選鍵={sorted(pinned - forbidden)}；"
            f"_FORBIDDEN 多出的孤兒鍵={sorted(forbidden - pinned)}"
            "——並聯的第三訊號必須逐鍵登記（刻意留空也要顯式寫成空 tuple ＋ WHY）",
        )

    def test_every_registered_keyword_tuple_is_non_vacuous(self) -> None:
        """自錨：全表若被清空成一堆空 tuple，上一支仍會綠（鍵集合不變）。

        本斷言要求「有第三訊號的殼」佔多數——不是禁止空 tuple（刻意留空是合法的
        決定），而是禁止整表被無聲掏空成一個只比對鍵名的空殼。
        """
        non_empty = [rel for rel, kws in m._FORBIDDEN.items() if kws]
        self.assertGreaterEqual(
            len(non_empty), len(m._FORBIDDEN),
            f"_FORBIDDEN 有 {len(m._FORBIDDEN) - len(non_empty)} 筆是空集合："
            f"{sorted(set(m._FORBIDDEN) - set(non_empty))}——刻意留空請同步下修本下限"
            "並就地寫 WHY，否則第三訊號會在無人察覺下逐鍵消失",
        )

    def test_the_two_run_tlc_shells_really_get_checked(self) -> None:
        """鑑別力（真跑而非讀表）：把違規字樣注進正規化文字，這兩鍵必須各出一筆。

        只斷言表的形狀不夠——`check_wrapper_thinness()` 那一行若被改回巢狀在 hash
        分支內（串聯），表照樣完整而訊號照樣沒有。故直接餵含違規字的假內容進判準。
        """
        for rel, keyword in (
            ("LATEST/tools/fsm_runtime/formal/run_tlc.sh", "jq "),
            ("LATEST/tools/fsm_runtime/formal/run_tlc.ps1", "ConvertFrom-Json"),
        ):
            with self.subTest(rel=rel):
                self.assertIn(
                    keyword, m._FORBIDDEN[rel],
                    f"{rel} 的第三訊號不含 {keyword!r} ⇒ 下面的注入不成立",
                )
                hits = [k for k in m._FORBIDDEN[rel] if k in f"x {keyword} y"]
                self.assertEqual(
                    hits, [keyword],
                    f"{rel}：含 {keyword!r} 的內容未被第三訊號命中（並聯訊號失效）",
                )
        self.assertEqual(
            m.convergence_target("AISDLC_SDD/scripts/install-hooks.ps1"),
            "tools/git_hooks_install_common.py",
        )
        self.assertEqual(
            m.convergence_target("AutoClaude/tools/run_act.sh"),
            "AutoClaude/tools/run_act_core.py",
        )

    def test_unregistered_key_is_fail_loud_not_silent(self) -> None:
        """缺陷注入：查無登記時必須回可讀的 fail-loud 字樣，不得回空字串／None。

        空字串會讓訊息長成「應收斂進 ，不應長在 wrapper 內」——讀者看不出是登記漏了。
        """
        msg = m.convergence_target("tools/never_registered_shell.sh")
        self.assertIn("_CORE_TARGET 未登記", msg)
        self.assertIn("never_registered_shell", msg)

    def test_violation_message_carries_the_headroom_hint(self) -> None:
        """訊息必須要人**先量目的地餘裕**，而不是照著撞上另一道棘輪。"""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            fake = Path(td)
            (fake / "tools").mkdir(parents=True)
            (fake / "tools" / "dev_start.sh").write_text(
                "#!/usr/bin/env bash\n" + "echo x\n" * (m.MAX_LINES + 3), encoding="utf-8"
            )
            pins = {"tools/dev_start.sh": "0" * 64}
            with mock.patch.object(m, "ROOT", fake), \
                 mock.patch.object(m, "_PINNED_SHA256", pins):
                problems = m.check_wrapper_thinness()
        over = [p for p in problems if "超過薄殼上限" in p]
        self.assertTrue(over, problems)
        self.assertIn("tools/dev_start.py", over[0])
        self.assertIn("check_loc_budget.py --json", over[0])


# ══════════════════════════════════════════════════════════════════════════════
# R74：根層守門工具的「未知引數 fail-loud」行為級鎖（R67-D20 射程自 3 站擴至全部）
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 **為何併進本檔而非另立新檔**：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
# `TestGuardLayerRatchet` 是 shrink-only 棘輪，`DEF-101-561③` 明文裁決「禁止新增
# 鎖檔、只准合併／刪除」（🔴 R78 ARCH-03 訂正：那是 R74 當時**檔數**棘輪的語意；R77 起
# 換成逐檔行數表，現行語意是**淨行數不得上升**。R73 首版新建獨立檔案當場被擋下的實錄見
# `test_check_hooks_liveness.py` 同款註記）。本檔是「根層守門工具自身契約」的既有家。
#
# 🔴 **為何是行為級枚舉而不是逐檔比對原始碼**：R67-D20 的修法只落在三支具名工具上，
# 於是同一個洞在其餘工具身上活了七輪。實測（本輪唯讀）：`check_wrapper_thinness.py`
# ／`check_pytest_baseline_sites.py`／`check_gha_action_versions.py`
# ／`check_script_parity.py` 拿到 `--bogus-flag-xyz` 全部 **rc=0 並印綠燈**。
# 本鎖改為 **現查全體 CLI 入口 ＋ 真的拿假引數跑一遍**：
#   · 新增一支守門工具而忘了接 `_cli_flags` ⇒ 本鎖當場紅，不必有人記得；
#   · 「靜默吞掉」是**行為**，故判準也只能是行為——比對原始碼有沒有某個 import
#     會被任何一種等價寫法繞過（同 `DEF-101-757` 的劃界結案形態）。
#
# 🔴 **R74 射程修復（SD 獨立複審抓到）：判準原本是 `glob("check_*.py")`，用檔名劃界**
# ——於是不叫 `check_*` 的工具全部在射程外，而**後果最大的那一支正好在射程外**：
# `tools/run_root_unittests.py` 是 pre-push root-infra leg ＋ 三支 CI 真正執行的那一支，
# 修前全檔 grep `argv|argparse|_cli_flags` 零命中，帶未知旗標時直接跑預設路徑、跑完整棵樹
# （逾 120 秒），最終 rc 反映的是「套件結果」而非「旗標被拒收」。它逃掉的唯一原因是檔名。
# ⇒ 判準改為 **`tools/*.py` 中帶 `if __name__ == "__main__"` 者**（＝真正的 CLI 入口）。
# 這與 `DEF-101-757`「已知的鎖射程缺口不得只以劃界結案」同型，只是這次的界是**檔名**；
# 修法刻意**不是**「把那一支加進白名單」——那等於把同一個機制再用一次。
_BOGUS_ARGV = "--bogus-flag-xyz-not-a-real-flag"

#: CLI 入口的判準。刻意只認 `__main__` guard，**不**額外要求「而且要讀 `sys.argv`」：
#: 後者會原地複製同一個洞——「不讀 `sys.argv`」正是「靜默吞掉未知旗標」的實作方式，
#: 拿它當射程條件等於自動豁免每一支還沒修的工具（`run_root_unittests.py` 修前就是
#: 這個樣子）。**射程條件必須與「有沒有病」正交**，否則病人自己決定要不要被檢查。
#: `_` 前綴的共用模組（`_cli_flags.py`／`_stdio_utf8.py`／`_script_scan_surface.py`）
#: 沒有 `__main__` guard，自然落在射程外——不必也不該再用檔名把它們排除。
_MAIN_GUARD_RE = re.compile(r"^if __name__ == ['\"]__main__['\"]", re.MULTILINE)

#: 「`sys.argv` 只在 `__main__` 那一行讀」這條性質的射程判準＝**接 `_cli_flags` SSOT 的檔**。
#: 同樣刻意由現查枚舉、不寫死清單：新工具接上 SSOT 的那一刻就落進射程。
#: ⚠️ 誠實劃界：自行用 argparse 拒收、沒接本 SSOT 的工具（`sync_onboarding_baselines.py`
#: 等）**不在本鎖射程**——它們的「未知旗標要拒收」那一半由下方行為級鎖
#: `test_every_gate_tool_rejects_an_unknown_flag` 覆蓋，但「`main()` 讀不讀 `sys.argv`」
#: 這一半確實仍無人看守。要納管得先取得那些檔的所有權，R75 本包界外。
_CLI_FLAGS_IMPORT_RE = re.compile(r"^import _cli_flags\b", re.MULTILINE)

#: `__main__` 那一行的唯一合法形狀（分層的最後一段：讀 `sys.argv` 只能發生在這裡）。
_CLI_ENTRY_RE = re.compile(
    r"if __name__ == [\"']__main__[\"']:\s*\n\s*sys\.exit\(cli\(sys\.argv\[1:\]\)\)")

#: 本輪**未持有所有權**、因此仍是舊行為的工具：shrink-only 豁免，只准變少。
#: 逐支寫 WHY 與承接者，不寫「TODO」——無主詞的交棒正是缺陷跨輪蒸發的原因。
#:
#: 🔴 **R74 射程擴張後的實查結論（誠實記錄，免得下一輪把它當成擴張引入的新缺口）**：
#: 擴張新納入 9 支 CLI 入口（`run_root_unittests` / `sync_onboarding_baselines` /
#: `dev_start` / `bootstrap_core` / `integration_gate_core` / `archive_defect_log` /
#: `check_defect_log_crossref` / `check_scheduled_task_drift` / `git_hooks_install_common`），
#: 逐一實測後 8 支**早就已經拒收**（argparse 或自寫分派，rc=2、≤0.1s），唯一不拒收的是
#: `run_root_unittests.py`，已於同一包修好。⇒ **擴張暴露的新違規數＝0**，本字典維持兩筆、
#: 內容未動。那兩支對射程修復包同樣是所有權界外（本包只持有 `run_root_unittests.py`／
#: `_cli_flags.py`／本檔），承接者仍見各筆自己的 WHY。
_UNKNOWN_ARGV_WAIVED: dict[str, str] = {
    "check_ntfs_paths.py": (
        "R74 PKG-5 檔案所有權界外（本包只持有 wrapper_thinness／script_parity／"
        "pytest_baseline_sites／gha_action_versions 四支的未知旗標處理段）；"
        "修法逐字同已修四支（R75 起為 `cli`/`main` 分層）＝把 "
        "`_cli_flags.reject_unknown_argv(<prog>, argv, ())` 放進 `cli(argv)`、"
        "`main()` 完全不碰 `sys.argv`、`__main__` 只留 `sys.exit(cli(sys.argv[1:]))`"
    ),
    "check_hooks_liveness.py": (
        "同上，界外；另其對應鎖檔 `test_check_hooks_liveness.py` 亦屬別包，"
        "修它必須連同鎖一起改才有鑑別力"
    ),
}


class TestRootGateToolsRejectUnknownFlags(unittest.TestCase):
    """`tools/check_*.py` 拿到未宣告的引數必須 rc≠0，不得靜默改跑預設路徑。

    測意圖（Rule 9）：`rc=0` 對呼叫端（pre-push／CI／人）的語意是「這道守門通過了」。
    一支工具在**根本沒理解使用者要它做什麼**的情況下印綠燈，是最壞的一種假綠——
    使用者以為自己下的旗標生效了，實際上跑的是別的東西（R67-D20 實測：
    `--check-snapsho` 少一個字母就在確實過期的工作樹上回 rc=0）。
    """

    _TOOLS_DIR = Path(__file__).resolve().parents[1]

    #: 射程下限。取落地當下實查值（`tools/*.py` 共 18 支，其中 15 支帶 `__main__` guard）。
    #: 掉到下限以下＝掃描面壞掉（目錄搬走／讀檔失敗），與「工具變少」不可分辨 ⇒ 一律判紅。
    _SCOPE_FLOOR = 15

    @staticmethod
    def _cli_entrypoints(tools_dir: Path) -> list[Path]:
        """`tools_dir` 底下**真正是 CLI 入口**的 `*.py`（判準見 `_MAIN_GUARD_RE`）。

        `tools_dir` 參數化是為了讓**判準本身**也能被合成注入證明——舊版把目錄寫死在
        方法裡，於是「射程對不對」只能靠讀原始碼判斷，那正是本輪要修掉的那種盲信。
        """
        return [
            path for path in sorted(tools_dir.glob("*.py"))
            if _MAIN_GUARD_RE.search(path.read_text(encoding="utf-8"))
        ]

    def _gate_tools(self) -> list[Path]:
        found = self._cli_entrypoints(self._TOOLS_DIR)
        self.assertGreaterEqual(
            len(found), self._SCOPE_FLOOR,
            f"掃描面只枚舉到 {len(found)} 支 CLI 入口（下限 {self._SCOPE_FLOOR}）"
            f"—— 本鎖可能已空轉")
        return found

    @staticmethod
    def _offenders(tools: list[Path], waived: dict[str, str]) -> list[str]:
        """真的拿假引數跑一遍，回傳仍然 rc=0 的工具（＝靜默吞掉）。

        抽成純函式是為了讓**鑑別力可被合成注入證明**：判準若只跑真實目錄，
        「現在是綠的」無法區分「守衛有牙」與「守衛根本沒被叫到」。

        🔴 逾時**也算 offender**（R74 補）：不拒收的工具會改跑預設路徑，而那條路徑可能
        很長——`run_root_unittests.py` 修前就是跑完整棵樹（逾 120 秒）。放任
        `TimeoutExpired` 拋出去，讀者看到的是一坨堆疊「error」而不是「這支不拒收」的
        **fail**，很容易被當成環境抖動放過（本 repo 剛為同一形態付過學費：`DEF-101-803`）。
        """
        import subprocess  # noqa: PLC0415  # 僅本鎖需要，不進本檔 import 期

        offenders: list[str] = []
        for tool in tools:
            if tool.name in waived:
                continue
            try:
                proc = subprocess.run(
                    [sys.executable, str(tool), _BOGUS_ARGV],
                    capture_output=True, encoding="utf-8", errors="replace", timeout=60)
            except subprocess.TimeoutExpired:
                offenders.append(
                    f"{tool.name}（逾時未回：拿到未知引數後改跑預設路徑，"
                    f"而拒收應該是**秒回**的）")
                continue
            if proc.returncode == 0:
                offenders.append(f"{tool.name}（rc=0，靜默吞掉未知引數）")
        return offenders

    def test_a_synthetic_swallower_is_caught(self) -> None:
        """鑑別力注入：合成一支「吞掉任何引數並 rc=0」的守門工具 ⇒ 必須被點名。

        修前實況即長這樣（本輪唯讀實測：四支真實工具拿 `--bogus-flag-xyz` 全 rc=0）。
        合成注入而**不動 tracked 生產碼**：對主樹做突變會與同輪並行的其他包互踩假紅
        （本 repo 已重演三次）。
        """
        import tempfile  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as td:
            swallower = Path(td) / "check_synthetic_swallower.py"
            swallower.write_text("import sys\nsys.exit(0)\n", encoding="utf-8",
                                 newline="\n")
            self.assertEqual(
                self._offenders([swallower], {}),
                ["check_synthetic_swallower.py（rc=0，靜默吞掉未知引數）"],
            )
            self.assertEqual(
                self._offenders([swallower], {swallower.name: "具名豁免"}), [],
                "具名豁免必須真的讓該支退出判定，否則豁免機制形同虛設",
            )

    def test_scope_is_not_a_filename_glob(self) -> None:
        """**本輪缺陷的直接回歸鎖**：射程不得回退成檔名 glob。

        測意圖（Rule 9）：一條紀律「管誰」如果由命名習慣決定，那它管不到的地方就是
        缺陷的永久居所——而 R74 SD 複審實測到的正是「後果最大的那一支剛好不叫
        `check_*`」。故本鎖同時釘三件事：① 那一支確實在射程內（具名，因為它是 pre-push
        ＋三支 CI 唯一真正執行的工具）；② 射程內有足夠多**非** `check_*` 的工具，
        證明判準不是換個前綴的檔名 glob；③ 判準的實作面不得出現 `check_*` 這種前綴 glob。
        """
        import inspect  # noqa: PLC0415

        names = {p.name for p in self._gate_tools()}
        self.assertIn(
            "run_root_unittests.py", names,
            "pre-push root-infra leg ＋ 三支 CI 真正執行的那一支不在射程內——"
            "這正是 R74 SD 複審抓到的缺口本體，不得回退",
        )
        non_check = sorted(n for n in names if not n.startswith("check_"))
        self.assertGreaterEqual(
            len(non_check), 5,
            f"射程內非 check_* 的 CLI 入口只有 {non_check}——判準疑似又退回檔名劃界",
        )
        src = inspect.getsource(TestRootGateToolsRejectUnknownFlags._cli_entrypoints)
        self.assertNotIn(
            'glob("check_', src,
            "判準又用檔名前綴 glob 劃界了——那正是本輪修掉的機制（見本節 R74 註記）",
        )

    def test_a_synthetic_tools_dir_discriminates_entrypoints_from_helpers(self) -> None:
        """判準的注入式鑑別力：合成一棵 `tools/` 目錄，三支檔各代表一種身分。

        🔴 為何合成在 tmpdir 而**不是**真的往 `tools/` 丟一支探針：本輪多個 agent 同樹
        並行，往 `tools/` 新增一支 `*.py` 會同時污染 ruff／LOC 棘輪／`_script_scan_surface`
        等多個掃描面 ⇒ 別人的全套會假紅（本 repo 已重演三次「並行突變互踩假紅」）。
        判準已參數化，注入不需要動真實目錄。

        本合成樹刻意**不含任何** `check_*` 命名 ⇒ 舊判準在這棵樹上枚舉不到任何東西，
        故本測試同時是「射程已不再是檔名 glob」的**行為級**證明，而非只讀原始碼。
        """
        import tempfile  # noqa: PLC0415

        entry = 'import sys\n\n\nif __name__ == "__main__":\n    sys.exit({})\n'
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "shared_helper.py").write_text(
                "VALUE = 1\n", encoding="utf-8", newline="\n")          # 無 guard＝非入口
            (d / "swallowing_tool.py").write_text(
                entry.format("0"), encoding="utf-8", newline="\n")      # 吞掉引數 rc=0
            (d / "rejecting_tool.py").write_text(
                entry.format("2 if sys.argv[1:] else 0"),
                encoding="utf-8", newline="\n")                          # 拒收 rc=2
            self.assertEqual(
                sorted(p.name for p in d.glob("check_*.py")), [],
                "合成樹刻意零 check_* 命名——這是舊判準在此枚舉不到東西的前提",
            )
            found = [p.name for p in self._cli_entrypoints(d)]
            self.assertEqual(
                found, ["rejecting_tool.py", "swallowing_tool.py"],
                "判準必須恰好收進兩支 CLI 入口：無 `__main__` guard 的共用模組不該進來"
                "（會被當成不拒收的工具而假紅），有 guard 的一支都不能漏",
            )
            self.assertEqual(
                self._offenders(self._cli_entrypoints(d), {}),
                ["swallowing_tool.py（rc=0，靜默吞掉未知引數）"],
                "注入的吞掉者必須被點名——否則本鎖對『判準+行為』整條鏈零鑑別力",
            )

    @staticmethod
    def _cli_flags_consumers(tools_dir: Path) -> list[Path]:
        """`tools_dir` 底下接了 `_cli_flags` SSOT 的 CLI 入口（判準見 `_CLI_FLAGS_IMPORT_RE`）。"""
        return [
            path for path in TestRootGateToolsRejectUnknownFlags._cli_entrypoints(tools_dir)
            if _CLI_FLAGS_IMPORT_RE.search(path.read_text(encoding="utf-8"))
        ]

    @staticmethod
    def _layering_offenders(tools: list[Path]) -> list[str]:
        """回傳違反 `cli`/`main` 分層的工具（純函式 ⇒ 鑑別力可被合成注入證明）。

        以 **AST 讀原始碼**而刻意**不 import** 目標模組：這一層的工具在 import 期會做
        stdio 手術（`tools/_stdio_utf8.py`）、注入 `sys.path`、甚至解析整棵 repo。為了
        讀一段原始碼去觸發那些副作用，本身就是「驗證載具汙染被驗證對象」的另一種形態。

        🔴 判準看的是 **AST 節點**、不是原始碼字串（R75 落地當回合實測到的假陽性）：
        本鎖第一版用 `"sys.argv" in ast.get_source_segment(...)`，於是 `main()` 裡一句
        「本層絕不讀 `sys.argv`」的**註解**就被判成違規。字串比對在這裡不只是不精確，
        它的方向是錯的——**它懲罰把紀律寫下來的人**，而那正是本 repo 要鼓勵的行為。
        """
        import ast  # noqa: PLC0415

        def reads_sys_argv(node: ast.AST) -> bool:
            return any(
                isinstance(n, ast.Attribute) and n.attr == "argv"
                and isinstance(n.value, ast.Name) and n.value.id == "sys"
                for n in ast.walk(node)
            )

        def calls_reject(node: ast.AST) -> bool:
            return any(
                (isinstance(n, ast.Attribute) and n.attr == "reject_unknown_argv")
                or (isinstance(n, ast.Name) and n.id == "reject_unknown_argv")
                for n in ast.walk(node)
            )

        offenders: list[str] = []
        for tool in tools:
            src = tool.read_text(encoding="utf-8")
            funcs = {
                node.name: node
                for node in ast.parse(src).body
                if isinstance(node, ast.FunctionDef)
            }
            for name in ("main", "cli"):
                if name not in funcs:
                    offenders.append(f"{tool.name}：缺頂層 `{name}()` ⇒ 未走 cli/main 分層")
            if "main" in funcs and reads_sys_argv(funcs["main"]):
                offenders.append(f"{tool.name}：`main()` 讀了 `sys.argv`")
            if "cli" in funcs and not calls_reject(funcs["cli"]):
                offenders.append(f"{tool.name}：拒收不在 `cli()` 這一層")
            if not _CLI_ENTRY_RE.search(src):
                offenders.append(
                    f"{tool.name}：`__main__` 那一行不是 `sys.exit(cli(sys.argv[1:]))`")
        return offenders

    def test_rejection_never_reads_sys_argv_inside_main(self) -> None:
        """`sys.argv` 只能在 `__main__` 那一行讀；`main()` 一律只吃顯式引數。

        測意圖（Rule 9）：`main()` 有**程式化呼叫端**，而它們的 `sys.argv` 裝的是別人的
        參數。兩筆實測都是「一道真鎖被弄成假紅」，不是風格偏好：
          · `python -m unittest tools.tests.test_gha_action_versions` —— unittest 把模組名
            放進 `sys.argv`，被 `main()` 當成未知旗標拒收 rc=2，而該測試斷言 rc=1
            ⇒ **HEAD 既存 3 支假紅**（R75 實測 `Ran 14 / FAILED (failures=3)`）；
          · `test_run_root_unittests.py` 的零相依探針在子行程內叩 `R.main()`，該子行程的
            `sys.argv` 帶的是探針自己的三個參數（blocked JSON／mode／tools_dir）。
        🔴 為何非機械釘住不可：這個洞在**閘門路徑**（`sys.argv[1:] == []`）恆綠，所以
        「四支工具跑起來都是綠的」對本性質零鑑別力——它就是這樣活過七輪的。
        🔴 R75 射程擴張：原版只具名釘 `run_root_unittests.py` 一支，而同一個洞當時正躺在
        另外四支上（`DEF-101-757`「已知的鎖射程缺口不得只以劃界結案」同型，這次的界是
        「上一包剛好修到的那一支」）。射程改為現查枚舉 `_cli_flags` 消費者。
        """
        consumers = self._cli_flags_consumers(self._TOOLS_DIR)
        names = sorted(p.name for p in consumers)
        self.assertGreaterEqual(
            len(consumers), 5,
            f"只枚舉到 {names}——`_cli_flags` 消費者不該少於 R75 落地當下的 5 支；"
            f"掉下來與「工具真的變少」不可分辨 ⇒ 一律判紅（掃描面壞掉也算紅）",
        )
        self.assertIn(
            "run_root_unittests.py", names,
            "pre-push root-infra leg ＋ 三支 CI 唯一真正執行的那一支必須在射程內",
        )
        self.assertEqual(
            self._layering_offenders(consumers), [],
            "下列工具未走 `cli`/`main` 分層 —— 修法＝把 `reject_unknown_argv` 搬進 "
            "`cli(argv)`、`main()` 完全不碰 `sys.argv`、`__main__` 只留一行 "
            "`sys.exit(cli(sys.argv[1:]))`（先例：`tools/run_root_unittests.py`；"
            "拍板記錄見 `tools/_cli_flags.py` 檔頭〈接線紀律〉R75 段）",
        )

    def test_the_layering_judgement_has_teeth(self) -> None:
        """注入式鑑別力：合成一棵樹，每支檔代表一種形態 ⇒ 逐筆點名，正控不得誤報。

        合成在 tmpdir 而**不動 tracked 生產碼**：對主樹做突變會與同輪並行的其他包互踩
        假紅（本 repo 已重演三次）。同時證明射程選取有效——沒接 SSOT 的那支不得被枚舉。
        """
        import tempfile  # noqa: PLC0415

        cli_block = (
            'def cli(argv):\n'
            '    rc = _cli_flags.reject_unknown_argv("t", argv, ())\n'
            '    return main(argv) if rc is None else rc\n\n\n'
            'if __name__ == "__main__":\n'
            '    sys.exit(cli(sys.argv[1:]))\n'
        )
        head = "import sys\n\nimport _cli_flags\n\n\n"
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "good_tool.py").write_text(
                head + "def main(argv=None):\n    return 0\n\n\n" + cli_block,
                encoding="utf-8", newline="\n")
            (d / "argv_in_main_tool.py").write_text(
                head + "def main(argv=None):\n"
                "    args = sys.argv[1:] if argv is None else argv\n"
                "    return 0 if args else 1\n\n\n" + cli_block,
                encoding="utf-8", newline="\n")
            (d / "no_cli_layer_tool.py").write_text(
                head + 'def main(argv=None):\n    return 0\n\n\n'
                'if __name__ == "__main__":\n    sys.exit(main())\n',
                encoding="utf-8", newline="\n")
            (d / "argparse_tool.py").write_text(
                'import sys\n\n\ndef main(argv=None):\n'
                "    return 0 if sys.argv[1:] else 1\n\n\n"
                'if __name__ == "__main__":\n    sys.exit(main())\n',
                encoding="utf-8", newline="\n")
            # 反向正控：只在**散文**裡提到那個名字，不得被判違規（本鎖第一版的假陽性本體）。
            (d / "prose_only_tool.py").write_text(
                head + 'def main(argv=None):\n'
                '    """本層絕不讀 sys.argv（拒收在 cli()）。"""\n'
                "    # 這一行也只是註解：sys.argv 三個字不等於讀它\n"
                "    return 0\n\n\n" + cli_block,
                encoding="utf-8", newline="\n")

            enrolled = sorted(p.name for p in self._cli_flags_consumers(d))
            self.assertEqual(
                enrolled,
                ["argv_in_main_tool.py", "good_tool.py", "no_cli_layer_tool.py",
                 "prose_only_tool.py"],
                "射程選取壞了：沒接 `_cli_flags` 的 argparse 工具不得被枚舉"
                "（納管它得先有那些檔的所有權），接了的一支都不能漏",
            )
            self.assertEqual(
                self._layering_offenders([d / "good_tool.py"]), [],
                "正控被誤報 ⇒ 本判準會逼出「為了過鎖而改壞正確寫法」的假修復",
            )
            self.assertEqual(
                self._layering_offenders([d / "prose_only_tool.py"]), [],
                "只在 docstring／註解提到 `sys.argv` 被判違規＝本鎖第一版的假陽性復發；"
                "它會逼人刪掉紀律說明才能過鎖，方向完全相反",
            )
            self.assertEqual(
                self._layering_offenders([d / "argv_in_main_tool.py"]),
                ["argv_in_main_tool.py：`main()` 讀了 `sys.argv`"],
                "注入「main() 讀 sys.argv」必須被點名——這就是 HEAD 既存那 3 支假紅的形狀",
            )
            self.assertEqual(
                self._layering_offenders([d / "no_cli_layer_tool.py"]),
                [
                    "no_cli_layer_tool.py：缺頂層 `cli()` ⇒ 未走 cli/main 分層",
                    "no_cli_layer_tool.py：`__main__` 那一行不是 "
                    "`sys.exit(cli(sys.argv[1:]))`",
                ],
                "缺 cli() 層必須同時點名兩件事：函式不存在、入口那一行形狀不對",
            )

    def test_every_gate_tool_rejects_an_unknown_flag(self) -> None:
        """修前實況：四支 `check_*` 全部 rc=0 印綠燈；R74 擴射程後另納入 `run_root_unittests.py`
        （修前不拒收、跑整棵樹）與其餘 8 支既已拒收的 CLI 入口。修後全體必須 rc≠0。"""
        offenders = self._offenders(self._gate_tools(), _UNKNOWN_ARGV_WAIVED)
        self.assertEqual(
            offenders, [],
            "下列根層守門工具對未知引數靜默 rc=0 —— 請接 `tools/_cli_flags.py` 的 "
            "`reject_unknown_argv()`（SSOT），或在 `_UNKNOWN_ARGV_WAIVED` 具名豁免"
            "（附 WHY ＋ 承接者）：\n  " + "\n  ".join(offenders),
        )

    def test_waiver_set_is_shrink_only_and_every_entry_still_exists(self) -> None:
        """豁免只准變少；豁免掉一支已不存在的檔＝棘輪張力靜默消失。"""
        self.assertLessEqual(
            len(_UNKNOWN_ARGV_WAIVED), 2,
            "未知引數豁免集合只准往下改（shrink-only）：要新增一筆，先問「為什麼這支"
            "不能接 `_cli_flags`」——七輪的教訓是劃界結案會讓缺口活下來",
        )
        names = {p.name for p in self._gate_tools()}
        for waived, why in _UNKNOWN_ARGV_WAIVED.items():
            self.assertIn(waived, names, f"{waived} 已不在掃描面內，請刪掉這筆豁免")
            self.assertTrue(why.strip(), f"{waived} 的豁免 WHY 為空 ⇒ 不具豁免力")

    def test_the_helper_itself_has_teeth(self) -> None:
        """SSOT 本體的鑑別力：合法引數回 None（不干擾），未知引數回 rc=2。"""
        import _cli_flags  # noqa: PLC0415

        self.assertIsNone(_cli_flags.reject_unknown_argv("t", [], ()))
        self.assertIsNone(_cli_flags.reject_unknown_argv("t", ["--x"], ("--x",)))
        self.assertEqual(
            _cli_flags.reject_unknown_argv("t", ["--xy"], ("--x",)),
            _cli_flags.UNKNOWN_FLAG_RC,
            "前綴縮寫不得被「好心地」補全成合法旗標——那正是 --check-snapsho 那個洞",
        )


if __name__ == "__main__":
    unittest.main()
