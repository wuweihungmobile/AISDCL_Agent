#!/usr/bin/env python3
"""ONBOARDING.md §7「表① live 格」↔ 機器實測值的新鮮度機械鎖
（R60 Scan-D D-01 根治 → R60 ARCH-R60-03／SA-R60-01／SD-R60-09 擴面與改形）。

WHY（為何非得有這道鎖）：
  「文件裡寫死機器可以現場算出來的數字」在本 repo 已是**慣犯家族**——
    - DEF-101-289：ONBOARDING §7 基線落後實測（P3）；
    - DEF-101-515：§7 整張表只有 macOS 單邊、容差宣稱主動誤導（P2）；
    - R60 Scan-D D-01：§7 Windows 基線表的 LOC 那格寫 `total=20356`，實測 `20359`
      ——而且在 **R59 自己的收尾 commit 樹上就已經 stale**；
    - R60 ARCH-R60-03／SA-R60-01：**本鎖的第一版只鎖一格**，同一張表另外四格全部
      stale（3740→3756、661→756、1725→1736、248→249），其中根層那格更與同 repo 的
      `tools/run_root_unittests.MIN_TESTS`（已重釘 756）直接矛盾。「為一格加鎖」反而
      讓另外四格更容易被誤讀成「有鎖所以可信」。
  歷輪的處置全是「人工回填一次」，所以家族每隔幾輪就原地復發。

本輪（R60 round 2）改形三件事：
  1. **改為錨點表驅動**：判定邏輯與「有幾格受鎖」解耦，收在
     `tools/sync_onboarding_baselines.py::_SPECS`。表格新增一格 ≠ 新增一支鎖
     （ARCH-R60-09(d) 的方向），只需在該處加一筆錨點。
  2. **新增第二格**：根層 `run_root_unittests` 測試數，取值來源＝該檔的 `MIN_TESTS`
     （現成 SSOT，import 後比對，成本近零）。
  3. **補上產生器那半邊**（SD-R60-09）：`sync_onboarding_baselines.py --write` 一鍵
     回填，`--check` 供本鎖與人工消費，兩者共用同一份取值邏輯 ⇒ 不可能一邊算 A、
     另一邊算 B。形狀對齊 repo 既有慣例（`snapshot_sync.py` + CI `--check`）。

判準邊界（誠實劃界，比照 check_pytest_baseline_sites.py docstring 風格）：
  - **只鎖帶錨點的行**：`loc-baseline-live:`（LOC 三數字）與 `rootunit-baseline-live:`
    （根層測試數）。任一錨點 0 行或 ≥2 行皆 fail-loud（防「刪錨點＝靜默縮面」與
    「抽錯行」）。
  - 每個欄位在受鎖行上必須**恰好命中一次**；0 次或 ≥2 次皆 fail-loud。這一條是
    SA-R60-01 的直接教訓：第一版用 `search()` 取第一個命中，讀到的其實是 macOS 欄，
    而該欄恰好與 Windows 欄同值所以看不出來。§7 表①因此已改為「同一列只寫一份數字」。
  - **刻意不掃全檔**：§7／§9 另有多則歷輪校正註記（如 R57 註的 `total=20356`）是
    **有標日期的歷史快照**，依本 repo「歷史紀錄檔／時代快照不納管」慣例刻意不回填、
    也刻意不鎖。
  - 本鎖**不驗證**：`8 kept / 0 broken`（需另跑 import-linter）、`skipped=N`
    （無現場取值來源）、以及 §7 表②那四格（AutoClaude 全套 pytest 與三格 ci-gate，
    根層閘門取不到現場值——為何不納管已寫在表②表頭）。皆屬如實揭露的殘留缺口。
  - `check_loc_budget.py --json` 為唯讀（`.loc_baseline` 已存在時 `check()` 不寫檔），
    本測試不會有副作用。
  - **LOC 破線 ≠ 文件 stale**：`--json` 在破線時回 rc=1 但仍印完整 JSON，產生器照樣
    解析；`violations>0` 時失敗訊息會明說「這是 LOC 閘門自己紅」，避免錯誤定位
    （SD-R60-09 附帶項）。取值來源真的壞掉（印不出 JSON）則拋 `BaselineToolError`，
    與 stale 分開回報。

檔名說明：本檔名沿用 R60 落地時的 `..._loc_baseline_...`，內容已泛化為整張表①。
  刻意不改名——改名會動到 ONBOARDING §7 內對本檔的具名引用與其他包的並行變更面，
  屬無淨收益的擾動（Rule 3）。要判斷本鎖實際守了哪幾格，看
  `sync_onboarding_baselines._SPECS`，不要看檔名。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import contextlib
import datetime
import hashlib
import inspect
import io
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path, PurePosixPath

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"

sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_TESTS_DIR))
# 🔴 R76：「這支 hook 有沒有被根層註冊」的解析走**既有 SSOT**，不在本檔再寫一份
# （同 `test_ntfs_trailing_space_device_name` 直接 import `test_windows_forbidden_
# filename_parity` 的既有慣例）。自寫一份 JSON 解析＝同一份知識住兩個家、只有一個家
# 被鎖（R73 教訓）。⚠️ 位置刻意排在下面兩行**之前**：ruff 的 isort 以 `tools/ruff.toml`
# 所在目錄為 project root，故 `tools/tests/` 底下的模組被歸為 third-party、`tools/`
# 底下的歸 first-party，順序寫反即 I001（實測）。
import test_subprocess_encoding_hygiene as _HYGIENE  # noqa: E402

import sync_onboarding_baselines as SYNC  # noqa: E402
from lib import baseline_origin as BO  # noqa: E402  # nightly 探針的解析契約（DEF-101-759）
from lib import ci_liveness as _CI_LIVENESS  # noqa: E402  # job 層 fail-open 正則 SSOT
from lib import defect_ledger_index as _LEDGER_INDEX  # noqa: E402  # 改派判定的生產 SSOT

hook_command_scripts = _HYGIENE.hook_command_scripts


@contextmanager
def _specs_without_historical():
    """暫時清空 `_SPECS` 的 historical 登記（**僅供合成最小文本的測試使用**）。

    WHY 需要這個：R60 round 3 把 `Spec.historical` 的 stale 自檢接進生產路徑 `check()`
    之後，用手工最小骨架（只有一列表格、沒有任何散文）驅動 `check()` 的那幾支測試會
    連帶收到「登記全部 stale」——技術上正確（那份合成文本裡確實沒有東西需要被豁免），
    但那不是它們要測的東西。它們測的是**數值不符**與**LOC 破線標示**兩條路徑。
    刻意不改成「過濾掉含 stale 的訊息」：那會讓這幾支測試在真的多出訊息時也照樣綠。
    """
    original = SYNC._SPECS
    try:
        SYNC._SPECS = tuple(replace(s, historical=()) for s in original)
        yield
    finally:
        SYNC._SPECS = original


# ---------------------------------------------------------------- SA-R67-07：欄頭／史料標記判準
# 判準本體寫成**純函式**（吃 text、回違規說明 list、空＝通過），才做得到「注入一次就看得出
# 紅綠」；直接在 test 內讀磁碟的寫法無法注入，那正是本 repo 判過的 `NOT-PROVEN`。
_LOCKED_ANCHOR = "rootunit-baseline-live:"
# 受鎖欄的欄頭必須自陳的兩件事：①受鎖 token 是平台中立值；②欄頭不代言量測時點與平台。
# 兩者都是**正面斷言**——反面寫法（禁止出現「收尾實測」）會與「訂正段須逐字引述被推翻
# 的原句」直接衝突，而這一格是單行巨欄，同行豁免會放行整格（ADR-XPLAT-002 §9.1 SC-4 的坑）。
_HEADER_NEUTRALITY_TOKEN = "平台中立"
_HEADER_NON_PROXY_TOKEN = "不再代言量測時點與平台"
# R60 世代 provenance 表：錨在**語意欄名**而非整句散文，措辭改寫不會誤紅。
_PROVENANCE_COLUMN_TOKEN = "誰實測過"
_HISTORICAL_TOKEN = "史料"


def _locked_header_coordinates(lines: list[str]) -> tuple[int, int]:
    """受鎖列所屬表格的 `(表頭行號, 受鎖欄的格索引)`。

    欄索引一律走 `SYNC.platform_cell_index()`（表頭推導的 SSOT，結構異動時自己 fail-loud）；
    表頭行號另需往上找分隔列，樣式沿用 `SYNC._SEPARATOR_ROW_RE`，**不自寫第二份樣式**。
    """
    row_idx = SYNC._anchored_index(lines, _LOCKED_ANCHOR)
    col = SYNC.platform_cell_index(lines, row_idx, "win32")
    sep = next(
        (i for i in range(row_idx - 1, -1, -1) if SYNC._SEPARATOR_ROW_RE.match(lines[i])),
        None,
    )
    if sep is None or sep - 1 < 0:
        raise AssertionError(
            f"受鎖列（第 {row_idx + 1} 行）所屬表格找不到表頭 — 表格結構已變動，拒絕猜測"
        )
    return sep - 1, col


def locked_column_header_problems(text: str) -> list[str]:
    """表① 受鎖欄的欄頭必須自陳「受鎖 token 平台中立、欄頭不代言量測時點與平台」。"""
    lines = text.split("\n")
    header_idx, col = _locked_header_coordinates(lines)
    cell = SYNC._split_row(lines[header_idx])[col]
    return [
        f"表① 受鎖欄欄頭（第 {header_idx + 1} 行）缺「{token}」的自陳 — "
        f"該欄的受鎖 token 取自 run_root_unittests.MIN_TESTS（平台中立、誰重釘都寫同一格），"
        f"欄頭一旦代言某平台某輪的實測，下一次跨平台重釘就會靜默造出假 provenance"
        f"（SA-R67-07）。改寫措辭時請同步本鎖的 token 常數。\n  欄頭：{cell.strip()[:200]}"
        for token in (_HEADER_NEUTRALITY_TOKEN, _HEADER_NON_PROXY_TOKEN)
        if token not in cell
    ]


def historical_provenance_marking_problems(text: str) -> list[str]:
    """R60 世代的 provenance 表頭必須帶世代標記；命中數不為一即 fail-loud。"""
    hits = [
        (i, ln) for i, ln in enumerate(text.split("\n"), 1) if _PROVENANCE_COLUMN_TOKEN in ln
    ]
    if len(hits) != 1:
        return [
            f"ONBOARDING.md 內含「{_PROVENANCE_COLUMN_TOKEN}」的表頭列命中 {len(hits)} 行"
            f"（預期恰一行）— 被刪除或被複製都會讓本鎖失去鑑別力，故 fail-loud"
        ]
    lineno, line = hits[0]
    if _HISTORICAL_TOKEN in line:
        return []
    return [
        f"第 {lineno} 行的 provenance 表頭未標明是「{_HISTORICAL_TOKEN}」 — 它描述的是 R60 世代"
        f"的量測與覆核，R65 之後四格已混世代；不標世代就會與表② 的現行 provenance 並存，"
        f"讀者採信先看到的那一套（SA-R67-07）。\n  行文：{line.strip()[:200]}"
    ]


class TestOnboardingLiveBaselineFreshness(unittest.TestCase):
    """真實文件 × 真實取值來源的新鮮度比對（本鎖的正職）。"""

    def test_documented_live_cells_match_measured_values(self) -> None:
        """§7 表①每一個受鎖格的數字 == 機器當場實測值。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        problems = SYNC.check(text, SYNC.measure_all())
        self.assertEqual(
            problems,
            [],
            "ONBOARDING.md §7 表① 已 stale——文件寫死的數字與機器實測不符：\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\nWHY 這是缺陷而非潔癖：該表自陳目的是「讓開發者分辨平台差異與退化」，"
            "數字一 stale，照文件驗證的人會把正常狀態誤判為退化"
            "（DEF-101-289／DEF-101-515 家族已復發多次；R60 更出現同 repo 對同一數字"
            "兩種說法＝§7 寫 661 而 MIN_TESTS 已重釘 756）。",
        )

    def test_every_spec_anchor_exists_exactly_once_in_real_doc(self) -> None:
        """每個受管錨點在真實 ONBOARDING.md 中恰存在一次（防有人順手刪錨點讓本鎖空轉）。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for spec in SYNC._SPECS:
            hits = [
                i for i, line in enumerate(text.splitlines(), 1) if spec.anchor in line
            ]
            self.assertEqual(
                len(hits),
                1,
                f"錨點 `{spec.anchor}` 在 ONBOARDING.md 命中 {len(hits)} 行（{hits}），預期恰 1",
            )

    def test_spec_table_covers_the_documented_live_cells(self) -> None:
        """`_SPECS` 與文件說法必須對齊：表①說有兩格受鎖，`_SPECS` 就必須恰有兩筆。

        WHY：本輪的教訓正是「文件說有鎖／實際只鎖一格」。若哪天有人在文件上加了
        第三格 live 但忘了在 `_SPECS` 補一筆，這裡會紅並指路。
        """
        self.assertEqual(
            {s.anchor for s in SYNC._SPECS},
            {"loc-baseline-live:", "rootunit-baseline-live:"},
            "受管錨點集合與 §7 表①的說法不一致——改表格時必須同步 _SPECS（反之亦然）",
        )

    def test_root_unittest_cell_agrees_with_min_tests_ssot(self) -> None:
        """根層那格必須逐字等於 `MIN_TESTS`（同 repo 對同一數字只准一種說法）。

        WHY 這一支與正職那支不重複：正職走 `check()` 的通用比對，這一支直接把
        SA-R60-01 的原始缺陷形態（§7 661 vs MIN_TESTS 756）釘成具名回歸鎖，
        讓失敗訊息直接說出「哪兩個站點打架」。
        """
        sys.path.insert(0, str(_REPO_ROOT / "tools"))
        import run_root_unittests

        line = SYNC.anchored_line(
            _ONBOARDING.read_text(encoding="utf-8-sig"), "rootunit-baseline-live:"
        )
        documented = SYNC.parse_documented(
            line, next(s for s in SYNC._SPECS if s.anchor == "rootunit-baseline-live:")
        )
        self.assertEqual(
            documented["tests"],
            run_root_unittests.MIN_TESTS,
            f"ONBOARDING §7 表①的根層測試數（{documented['tests']}）≠ "
            f"tools/run_root_unittests.py 的 MIN_TESTS（{run_root_unittests.MIN_TESTS}）"
            f"——重釘 MIN_TESTS 時必須同步該格：`python tools/sync_onboarding_baselines.py --write`",
        )

    # ── 以下以合成文本自證抽取／比對器紅綠（不落 repo 樹內、不碰 ONBOARDING.md）──

    def _loc_spec(self) -> SYNC.Spec:
        return next(s for s in SYNC._SPECS if s.anchor == "loc-baseline-live:")

    def test_missing_anchor_fails_loud(self) -> None:
        """錨點消失（被刪／文件改組）→ fail-loud，不得靜默 0 命中假綠。"""
        with self.assertRaisesRegex(AssertionError, "命中 0 行"):
            SYNC.anchored_line("# 無關內容\n| 某表格 | total=1 cap=2 violations=0 |\n",
                               "loc-baseline-live:")

    def test_duplicate_anchor_fails_loud(self) -> None:
        """錨點重複（複製貼上第二格）→ fail-loud，防抽錯行。"""
        row = "| total=1 cap=2 violations=0 <!-- loc-baseline-live: x --> |"
        with self.assertRaisesRegex(AssertionError, "命中 2 行"):
            SYNC.anchored_line(f"{row}\n{row}\n", "loc-baseline-live:")

    def test_field_drift_fails_loud(self) -> None:
        """數字欄位被改寫成本鎖抽不到的形態 → fail-loud（不縮面成假綠）。"""
        with self.assertRaisesRegex(AssertionError, "命中 0 次"):
            SYNC.parse_documented(
                "| LOC 總量 20359 行，上限 20438 <!-- loc-baseline-live: --> |",
                self._loc_spec(),
            )

    def test_duplicate_field_on_same_row_fails_loud(self) -> None:
        """同一列出現兩個同形數字（例如兩欄都寫 total=）→ fail-loud。

        WHY：這正是 SA-R60-01 的機制——第一版取第一個命中，讀到的是 macOS 欄。
        """
        with self.assertRaisesRegex(AssertionError, "命中 2 次"):
            SYNC.parse_documented(
                "| total=1 cap=2 violations=0 | total=1 cap=2 violations=0 "
                "<!-- loc-baseline-live: --> |",
                self._loc_spec(),
            )

    def test_parse_extracts_all_three_loc_fields(self) -> None:
        """合成行驗證三欄抽取正確（含全形頓號與其他文字干擾）。"""
        self.assertEqual(
            SYNC.parse_documented(
                "> | `check_loc_budget` | total=12345 cap=23456 violations=7 ／ "
                "8 kept 0 broken <!-- loc-baseline-live: 錨點 --> |",
                self._loc_spec(),
            ),
            {"total": 12345, "cap": 23456, "violations": 7},
        )

    def test_parse_extracts_rootunit_field(self) -> None:
        """根層那格的抽取形態＝`N tests OK`（刻意選一個在該列唯一出現的字面）。"""
        spec = next(s for s in SYNC._SPECS if s.anchor == "rootunit-baseline-live:")
        self.assertEqual(
            SYNC.parse_documented(
                "> | 根層 | 616（skipped=4） | **756 tests OK**（skipped=10） "
                "<!-- rootunit-baseline-live: 錨點 --> |",
                spec,
            ),
            {"tests": 756},
        )

    def test_check_reports_mismatch_with_actionable_fix_command(self) -> None:
        """合成 stale 文本必須被 `check()` 判為不符，且訊息含一鍵回填指令。"""
        text = (
            "| total=1 cap=2 violations=0 <!-- loc-baseline-live: --> |\n"
            "| **9 tests OK** <!-- rootunit-baseline-live: --> |\n"
        )
        with _specs_without_historical():
            problems = SYNC.check(
                text,
                {
                    "loc-baseline-live:": {"total": 1, "cap": 2, "violations": 0},
                    "rootunit-baseline-live:": {"tests": 756},
                },
            )
        self.assertEqual(len(problems), 1, f"只有根層那格該被判不符：{problems}")
        self.assertIn("sync_onboarding_baselines.py --write", problems[0])
        self.assertIn("rootunit-baseline-live:", problems[0])

    def test_check_labels_loc_gate_failure_distinctly(self) -> None:
        """LOC 破線（violations>0）時訊息必須說「這是 LOC 閘門自己紅」而非文件 stale。"""
        text = (
            "| total=1 cap=2 violations=0 <!-- loc-baseline-live: --> |\n"
            "| **756 tests OK** <!-- rootunit-baseline-live: --> |\n"
        )
        with _specs_without_historical():
            problems = SYNC.check(
                text,
                {
                    "loc-baseline-live:": {"total": 1, "cap": 2, "violations": 3},
                    "rootunit-baseline-live:": {"tests": 756},
                },
            )
        self.assertEqual(len(problems), 1)
        self.assertIn("LOC 閘門自己紅", problems[0])

    def test_render_rewrites_only_the_anchored_numbers(self) -> None:
        """產生器的回填必須就地換數字、不動同列敘述，也不動未帶錨點的行。"""
        text = (
            "歷史快照：R57 註的 total=20356 不得被回填（不帶錨點）\n"
            "| 說明文字 total=1 cap=2 violations=9 保留 <!-- loc-baseline-live: --> |\n"
            "| **9 tests OK**（skipped=10） <!-- rootunit-baseline-live: --> |\n"
        )
        out = SYNC.render(
            text,
            {
                "loc-baseline-live:": {"total": 20361, "cap": 20438, "violations": 0},
                "rootunit-baseline-live:": {"tests": 756},
            },
        )
        self.assertIn("total=20356 不得被回填", out)
        self.assertIn("total=20361 cap=20438 violations=0 保留", out)
        self.assertIn("**756 tests OK**（skipped=10）", out)
        self.assertEqual(len(out.split("\n")), len(text.split("\n")))

    def test_render_output_is_check_clean(self) -> None:
        """回填後的文本必須讓 `check()` 轉綠——產生器與稽核共用同一份邏輯的證明。"""
        measured = {
            "loc-baseline-live:": {"total": 20361, "cap": 20438, "violations": 0},
            "rootunit-baseline-live:": {"tests": 756},
        }
        stale = (
            "| total=1 cap=2 violations=9 <!-- loc-baseline-live: --> |\n"
            "| **1 tests OK** <!-- rootunit-baseline-live: --> |\n"
        )
        with _specs_without_historical():
            self.assertNotEqual(SYNC.check(stale, measured), [])
            self.assertEqual(SYNC.check(SYNC.render(stale, measured), measured), [])

    def test_measure_rootunit_reads_the_ssot_not_a_copy(self) -> None:
        """`measure_rootunit()` 必須真的讀 `MIN_TESTS`，不是自持一份數字。"""
        sys.path.insert(0, str(_REPO_ROOT / "tools"))
        import run_root_unittests

        self.assertEqual(
            SYNC.measure_rootunit(), {"tests": run_root_unittests.MIN_TESTS}
        )
        source = (_REPO_ROOT / "tools" / "sync_onboarding_baselines.py").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(
            source.replace("MIN_TESTS", ""),
            r"\btests\W{0,4}\d{3}\b",
            "產生器內不得出現寫死的測試數字面——那會讓 SSOT 變成兩份",
        )

    def test_loc_tool_failure_is_reported_as_tool_error_not_stale(self) -> None:
        """取值來源壞掉（印不出 JSON）→ `BaselineToolError`，訊息不得說「文件 stale」。"""
        original = SYNC._LOC_TOOL
        try:
            SYNC._LOC_TOOL = _REPO_ROOT / "tools" / "__definitely_missing__.py"
            with self.assertRaises(SYNC.BaselineToolError) as ctx:
                SYNC.measure_loc()
        finally:
            SYNC._LOC_TOOL = original
        self.assertIn("取值來源壞掉", str(ctx.exception))
        self.assertNotIn("stale", str(ctx.exception).replace("不是文件 stale", ""))


class TestLockedLineProseIsAlsoManaged(unittest.TestCase):
    """R60 round 3（DEF-101-562）：受鎖行的**散文**也受管。

    四方複審 round 2 **全部四位獨立命中同一根因**（ARCH-R60R2-03／SA-R60R2-02／
    SD-R60-R2-03／QA2-R60-02）：round 1 落地產生器後，受鎖行的 token 已回填為當輪
    實測值，而**同一行的散文仍留著同輪的較舊宣稱**。⇒ 產生器 ＋ `--check` 只保證
    「被抽取的那個 token」新鮮，不保證同一行的散文新鮮。

    🔴 **正樣本刻意用「真實缺陷的逐字形態」**（比照本 repo 既有慣例：以真實語料當守門
    樣本）——`R60=756` 這串就是 round 2 四方在 ONBOARDING.md:216 抓到的原字樣。
    """

    #: 受鎖行的最小合成骨架（帶 rootunit 錨點與受管 token）。
    _SKELETON = "| **{v} tests OK** {prose} <!-- rootunit-baseline-live: --> |"

    def _problems(
        self, prose: str, live_tests: int = 845, historical: tuple | None = None
    ) -> list[str]:
        """`historical=None` ＝沿用真實 `_SPECS` 登記；給定值則覆寫（對抗式樣本用）。"""
        spec = next(s for s in SYNC._SPECS if s.anchor == "rootunit-baseline-live:")
        if historical is not None:
            spec = replace(spec, historical=historical)
        line = self._SKELETON.format(v=live_tests, prose=prose)
        return SYNC.prose_problems(line, spec, {"tests": live_tests})

    def test_current_round_claim_in_prose_is_rejected(self) -> None:
        """正樣本：round 2 抓到的原缺陷形態（受鎖值 845、散文寫 R60=756）必須紅。

        ⚠️ 刻意以 `historical=()` 驅動：R60 round 3 放寬判準(2) 後，受鎖行上那個真實的
        歷史值已依機制設計**登記進 `_SPECS`**（見該處 WHY），若沿用真實登記，本樣本會被
        白名單合法放行而失去鑑別力。本支要測的是「**未登記時**這個形態必須紅」。
        """
        problems = self._problems(
            "收集總數 R57=616 → R59=661 → **R60=756**", historical=()
        )
        self.assertTrue(
            any("R60=756" in p for p in problems),
            f"真實缺陷語料未被判紅——本鎖無牙：{problems}",
        )
        self.assertTrue(
            any("不要寫進散文" in p for p in problems),
            f"失敗訊息必須告訴人怎麼修（當輪值不寫進散文）：{problems}",
        )

    def test_registered_historical_claims_pass(self) -> None:
        """反向：登記在 `Spec.historical` 的歷史輪值必須放行，否則本鎖不可用。"""
        self.assertEqual(self._problems("沿革 R57=616 → R59=661"), [])

    def test_unregistered_historical_claim_is_rejected(self) -> None:
        """未登記的歷史值不得靜默通過——否則「歷史值」會變成任意數字的逃生口。"""
        problems = self._problems("沿革 R57=616 → R58=999")
        self.assertTrue(any("R58=999" in p for p in problems), problems)
        self.assertTrue(any("historical" in p for p in problems), problems)

    def test_claim_equal_to_live_value_passes(self) -> None:
        """散文寫的輪值恰等於 live 值時放行（那是一致的說法，不是矛盾）。

        ⚠️ 但它仍會被「受管值不得出現第二次」那道判準抓到——本測試以獨立的
        prose 片段驗證**這一道**判準的語意，見下一支測試驗證另一道。
        """
        spec = next(s for s in SYNC._SPECS if s.anchor == "rootunit-baseline-live:")
        line = "| tests OK-less 行，只有散文 R60=845 <!-- x -->"
        self.assertEqual(SYNC.prose_problems(line, spec, {"tests": 845}), [])

    def test_managed_value_repeated_in_prose_is_rejected(self) -> None:
        """受管值在受鎖行出現第二次即紅——那一份下次變動時不會被回填。"""
        problems = self._problems("同輪另一包改動後即為 845")
        self.assertTrue(
            any("出現 2 次" in p for p in problems),
            f"受管值重複未被判紅：{problems}",
        )

    def test_short_values_are_exempt_from_duplicate_rule(self) -> None:
        """1~2 位數（如 `violations=0`）在散文裡是無關的巧合同值 ⇒ 刻意不判。

        這是誠實劃界而非漏洞：對它們硬判會製造大量誤紅（「8 支 pgid」「1 支 symlink」），
        而它們 stale 的危害近零。門檻寫在程式常數裡、不寫在散文裡。
        """
        spec = next(s for s in SYNC._SPECS if s.anchor == "loc-baseline-live:")
        line = (
            "| total=20361 cap=20438 violations=0 —— 0 違規、0 破線、0 例外 "
            "<!-- loc-baseline-live: -->"
        )
        self.assertEqual(SYNC.prose_problems(line, spec, {
            "total": 20361, "cap": 20438, "violations": 0,
        }), [])
        self.assertGreaterEqual(SYNC._PROSE_DUP_MIN_DIGITS, 3)

    def test_real_onboarding_locked_lines_are_prose_clean(self) -> None:
        """真實文件必須通過兩道散文判準（本鎖的正職；落地時它當場抓到主控自己）。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        measured = SYNC.measure_all()
        for spec in SYNC._SPECS:
            line = SYNC.anchored_line(text, spec.anchor)
            self.assertEqual(
                SYNC.prose_problems(line, spec, measured[spec.anchor]), [],
                f"ONBOARDING.md 受鎖行（{spec.anchor}）的散文與受管值矛盾",
            )


class TestSnapshotFingerprintTripwire(unittest.TestCase):
    """R60 round 3（DEF-101-563）：表②（dated snapshot）的 presumed-stale 觸發器。

    四方複審 round 2 **全部四位獨立命中同一根因**（ARCH-R60R2-02／SA-R60R2-02／
    SD-R60-R2-02／QA2-R60-01）：round 1 填了 ci-gate v0.30 的當時值、round 2 動了該
    測試樹使實測改變而**沒人回填**，而表頭同時宣稱「四格皆經 SA 複審者獨立覆核相符」
    ⇒ 假宣稱。根治＝把「靠人記得」換成因果式觸發器：測試計數只可能因測試樹變動而變。

    🔴 **本類別刻意不斷言「真實文件的指紋現在是新鮮的」**（與上方表① 那幾支不同）：
    那樣會讓根層 unittest 閘門在**任何一輪動到任何測試檔時立刻紅**，而回填要付分鐘級
    代價 ⇒ 必然養成忽略紅燈的習慣，比沒有鎖更糟。故該斷言的住址是 **pre-push 第 8 支
    守門 ＋ root-infra-ci 第 14 道**（收輪＝push 時點付代價才合理），其接線完整性由
    `test_root_infra_parity.py` 的雙向鎖機械保證。本類別驗的是**機制本身有牙**。

    ⚠️ **root-infra-ci 現因 CI 帳務停擺（DEF-101-081）在數秒內失敗，那一半從未在雲端
    真正執行**（R60 r3 QA-R60R3-04 以 gh run list 實查／DEF-101-597）。故上句是
    **接線完整性**的宣稱，不是活體守門的宣稱；今日真正會跑的只有 pre-push 那一半。
    """

    def test_all_fingerprint_trees_exist_and_hash_stably(self) -> None:
        live = SYNC.measure_fingerprints()
        self.assertEqual(
            sorted(live), sorted(n for n, _r, _p in SYNC._FINGERPRINT_TREES)
        )
        for name, value in live.items():
            self.assertRegex(value, r"^[0-9a-f]{12}$", f"{name} 指紋形態異常")
        self.assertEqual(live, SYNC.measure_fingerprints(), "同一棵樹兩次雜湊不一致")

    def test_missing_tree_fails_loud_not_silent_empty(self) -> None:
        """目錄被搬走時必須 fail-loud——靜默回傳空指紋會讓觸發器永遠綠。"""
        with self.assertRaises(SYNC.BaselineToolError) as ctx:
            SYNC.tree_fingerprint("definitely/not/a/real/dir", "*.py")
        self.assertIn("指紋來源目錄不存在", str(ctx.exception))

    def test_fingerprint_changes_when_any_test_file_content_changes(self) -> None:
        """鑑別力核心：測試樹內容一變、指紋必變（否則觸發器抓不到任何東西）。"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tests"
            tree.mkdir()
            (tree / "test_a.py").write_bytes(b"x = 1\n")
            original = SYNC._REPO_ROOT
            try:
                SYNC._REPO_ROOT = Path(tmp).parent
                rel = Path(tmp).name + "/tests"
                before = SYNC.tree_fingerprint(rel, "*.py")
                (tree / "test_a.py").write_bytes(b"x = 2\n")
                after_edit = SYNC.tree_fingerprint(rel, "*.py")
                (tree / "test_b.py").write_bytes(b"y = 1\n")
                after_add = SYNC.tree_fingerprint(rel, "*.py")
            finally:
                SYNC._REPO_ROOT = original
        self.assertNotEqual(before, after_edit, "改內容而指紋不變 ⇒ 觸發器無牙")
        self.assertNotEqual(after_edit, after_add, "新增測試檔而指紋不變 ⇒ 觸發器無牙")

    def test_check_snapshot_reds_on_documented_drift(self) -> None:
        """文件記載值與現查不符即紅，且訊息帶可執行的回填指令——**逐受管平台欄**驗。

        🔴 R67 round 3（root-infra-ci 首次在 ubuntu runner 上真的執行本鎖時紅）：
        原版取 `current_platform_key()`＝**本機**欄並斷言「它不得為 None」。但本鎖驗的是
        `check_snapshot()` 這個判準本身，那是一個吃「哪一欄」當參數的純函式，與「這次跑在
        哪台機器」無關。綁本機平台等於替本鎖加了一條**未言明的前提**——「本機必須是受管
        平台」——於是無欄平台（Linux，見 `current_platform_key` docstring：刻意沒有欄）
        一跑就紅，而那個紅燈說的不是「判準壞了」，是「前提不成立」。一個只在特定 host 上
        才成立的鎖，在別的 host 上不是弱，是**冤**。

        改為逐欄驅動之後：本鎖在任何平台上跑的都是同一件事，且覆蓋面由一欄變成全部欄。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            tampered = SYNC.render_fingerprints(
                text,
                {name: "0" * SYNC._FP_LEN for name, _r, _p in SYNC._FINGERPRINT_TREES},
                key,
                SYNC.parse_provenance(text, key),
            )
            problems = SYNC.check_snapshot(tampered, key)
            self.assertEqual(len(problems), len(SYNC._FINGERPRINT_TREES), f"{key} 欄")
            self.assertTrue(all("--with-slow" in p for p in problems), problems)
            self.assertTrue(all("presumed stale" in p for p in problems), problems)

    def test_fingerprint_anchor_exists_exactly_once_and_round_trips(self) -> None:
        """每個受管平台各有一條錨，且指紋 ＋ provenance 都能來回無損。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            SYNC.anchored_line(text, SYNC.fingerprint_anchor(key))  # 0/≥2 皆 fail-loud
            synthetic = {
                name: f"{i}" * SYNC._FP_LEN
                for i, (name, _r, _p) in enumerate(SYNC._FINGERPRINT_TREES)
            }
            prov = {f: f"probe-{f}" for f in SYNC._PROVENANCE_FIELDS}
            rendered = SYNC.render_fingerprints(text, synthetic, key, prov)
            self.assertEqual(SYNC.parse_fingerprints(rendered, key), synthetic)
            self.assertEqual(SYNC.parse_provenance(rendered, key), prov)

    def test_missing_fingerprint_field_fails_loud(self) -> None:
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            line = SYNC.anchored_line(text, SYNC.fingerprint_anchor(key))
            first = SYNC._FINGERPRINT_TREES[0][0]
            broken = text.replace(line, line.replace(f"{first}=", f"{first}_renamed="), 1)
            with self.assertRaises(AssertionError) as ctx:
                SYNC.parse_fingerprints(broken, key)
            self.assertIn("--with-slow", str(ctx.exception))


class TestR67R2RootdirConftestIsFingerprintInput(unittest.TestCase):
    """R67 round 2（SD-R67-02）：決定收集結果的 rootdir `conftest.py` 也必須是指紋輸入。

    WHY（Rule 9 — 測意圖非僅行為）：指紋錨的字面語意是「**該欄的數字是在哪一棵測試樹上
    量的**」，它存在的唯一理由是「計數只可能因測試樹變動而變」這條因果判準。而 pytest
    依 rootdir 隱式載入的 `conftest.py` **同樣決定那次執行收集到什麼**（一句
    `collect_ignore_glob` 就能讓計數改變），卻住在四棵 glob 的覆蓋面之外 ⇒ 判準的「因」
    漏了一半。SD-R67-02 已實測：在 `AISDLC_SDD_v0.30/conftest.py` 末尾加一行
    `collect_ignore_glob`，實測計數改變、四格指紋**逐字不變**、`--check-snapshot` ✅ rc=0。

    這與 R60 SD-R60R3-03 修的是**同一類缺口的另一個入口**（那次是樹**內**子目錄、這次是
    樹**外** rootdir），故一併鎖住，而不是只把當下這一支檔補進去。
    """

    def test_every_tree_declares_a_rootdir_conftest_and_it_sits_at_the_rootdir(self) -> None:
        """四棵樹各自都要登記 rootdir conftest，且該檔必須真的住在那棵樹的 rootdir 上。

        位置判準是結構性的：rootdir 必須是測試樹的**祖先目錄**。登記到別處（例如把
        `AutoClaude/conftest.py` 掛到 v030）會讓指紋回答錯的問題，而值仍然「有變化」
        ⇒ 光看指紋會變不足以證明對應關係正確。
        """
        for name, rel, _pat in SYNC._FINGERPRINT_TREES:
            extras = SYNC.rootdir_conftests_for(name)
            self.assertTrue(
                extras,
                f"[{name}] 未登記任何 rootdir conftest——該欄的收集結果可被一支樹外 "
                f"conftest 改變而指紋不動（SD-R67-02 原始形態）",
            )
            tree = PurePosixPath(rel)
            for conftest in extras:
                rootdir = PurePosixPath(conftest).parent
                self.assertTrue(
                    tree == rootdir or rootdir in tree.parents,
                    f"[{name}] 登記的 {conftest} 不在測試樹 {rel} 的祖先目錄上"
                    f"——pytest 不會在該樹的執行中載入它，這條登記是錯的對應關係",
                )

    def test_existing_rootdir_conftest_actually_changes_that_column(self) -> None:
        """唯讀鑑別力：對**確實存在**的 rootdir conftest，帶它與不帶它的指紋必須不同。

        另斷言 `measure_fingerprints()` 交出來的就是「帶 extras」那一份——只改
        `_FINGERPRINT_ROOTDIR_CONFTESTS` 而忘了讓量測器吃它，本條當場紅。
        """
        live = SYNC.measure_fingerprints()
        checked = 0
        for name, rel, pat in SYNC._FINGERPRINT_TREES:
            extras = SYNC.rootdir_conftests_for(name)
            present = tuple(e for e in extras if (SYNC._REPO_ROOT / e).is_file())
            self.assertEqual(
                live[name], SYNC.tree_fingerprint(rel, pat, extras),
                f"[{name}] measure_fingerprints() 未把 rootdir conftest 納入指紋輸入",
            )
            if not present:
                continue  # v0.01（ADR-XPLAT-001 凍結，無此檔）／AutoClaude（尚未建立）
            checked += 1
            self.assertNotEqual(
                SYNC.tree_fingerprint(rel, pat), live[name],
                f"[{name}] 存在的 rootdir conftest {present} 對指紋零貢獻 ⇒ 改它不會觸發",
            )
        self.assertGreaterEqual(
            checked, 1,
            "沒有任何一棵樹的 rootdir conftest 存在於磁碟上 ⇒ 本鎖退化為恆真"
            "（載具鑑別力自證，同 _MIN_* 下限釘選慣例）",
        )

    def test_creating_or_editing_a_rootdir_conftest_moves_the_fingerprint(self) -> None:
        """沙箱行為鎖：conftest **新建**與**改內容**都必須讓該欄指紋改變。

        新建那一半專門守 v0.01／AutoClaude 這種「今天還不存在」的格：若實作寫成「檔案
        不存在就整條登記跳過」而非「不貢獻 bytes」，那兩格會永遠對新增 conftest 免疫——
        而「有人為凍結版或 AutoClaude 加一支 rootdir conftest」正是最需要被看到的異動。
        """
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = Path(tmp)
            tree = sandbox / "vX" / "tools" / "tests"
            tree.mkdir(parents=True)
            (tree / "test_a.py").write_bytes(b"def test_a():\n    assert True\n")
            conftest_rel = "vX/conftest.py"
            conftest = sandbox / conftest_rel
            original_root = SYNC._REPO_ROOT
            try:
                SYNC._REPO_ROOT = sandbox
                args = ("vX/tools/tests", "**/*.py", (conftest_rel,))
                before = SYNC.tree_fingerprint(*args)
                self.assertEqual(
                    before, SYNC.tree_fingerprint("vX/tools/tests", "**/*.py"),
                    "conftest 尚不存在時不得貢獻任何 bytes（否則等於憑空造出差異）",
                )
                conftest.write_bytes(b"# rootdir conftest\n")
                after_create = SYNC.tree_fingerprint(*args)
                conftest.write_bytes(b'# rootdir conftest\ncollect_ignore_glob = ["test_a.py"]\n')
                after_edit = SYNC.tree_fingerprint(*args)
            finally:
                SYNC._REPO_ROOT = original_root
        self.assertNotEqual(before, after_create, "新建 rootdir conftest 而指紋不動 ⇒ 觸發器漏")
        self.assertNotEqual(
            after_create, after_edit,
            "改 rootdir conftest 內容（此處正是會改變收集結果的 collect_ignore_glob）"
            "而指紋不動 ⇒ SD-R67-02 原始形態原封不動",
        )


class TestSlowSnapshotCellsRoundTrip(unittest.TestCase):
    """表② 四格的抽取／回填（`--write --with-slow` 的純函式層；不實跑分鐘級量測）。"""

    def test_every_slow_anchor_exists_exactly_once(self) -> None:
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for spec in SYNC._SLOW_SPECS:
            SYNC.anchored_line(text, spec.anchor)  # 0/≥2 皆 fail-loud

    def test_slow_documented_reads_the_requested_platform_column(self) -> None:
        """兩欄同形，抽錯欄是 SA-R60-01 的原始成因 ⇒ 逐平台明確斷言抽到的字面就在該欄格內。

        R67 改形：判準不再是「有沒有 `**` 粗體」（那是 R67-D1 的成因——粗體被當成「哪一
        欄」的判準，於是回填在結構上只寫得到 Windows 欄），而是「抽到的值必須逐字出現在
        **該平台那一格**、且**不等於**另一欄的值時另一欄不得被誤讀成它」。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        lines = text.split("\n")
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            doc = SYNC.slow_documented(text, key)
            for spec in SYNC._SLOW_SPECS:
                idx = SYNC._anchored_index(lines, spec.anchor)
                cell = SYNC._split_row(lines[idx])[
                    SYNC.platform_cell_index(lines, idx, key)
                ]
                for name, value in doc[spec.anchor].items():
                    self.assertIn(
                        str(value), cell,
                        f"{key}/{spec.anchor}/{name} 抽到的值不在該平台那一格內 ⇒ 抽錯欄",
                    )

    def test_render_slow_round_trips_all_four_cells(self) -> None:
        """回填後重讀必須逐格等於餵進去的值（否則 `--write --with-slow` 寫錯格）。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        synthetic = {
            "autoclaude-pytest-snapshot:": {"passed": 9991, "skipped": 222},
            "cigate-v001-snapshot:": {"passed": 1111},
            "cigate-v030-snapshot:": {"passed": 2222},
            "cigate-scripts-snapshot:": {"passed": 3333},
        }
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            rendered = SYNC.render_slow(text, synthetic, key)
            self.assertEqual(SYNC.slow_documented(rendered, key), synthetic)
            changed = sum(
                1 for a, b in zip(text.split("\n"), rendered.split("\n"), strict=True) if a != b
            )
            self.assertEqual(changed, len(SYNC._SLOW_SPECS), "回填動到的行數 ≠ 受管格數")

    def test_render_slow_is_not_order_dependent(self) -> None:
        """兩個欄位共處一段字時，第一次替換不得吃掉第二個欄位的上下文。

        本鎖的存在理由：初版把 `**` 與 ` passed / N skipped**` 納入 match，第一次 sub 後
        第二個欄位命中 0 次而 fail-loud（本檔的斷言當場抓到）。故改用零寬斷言，並在此
        以「只改 passed 不改 skipped」的構造把該退化直接測到。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            doc = SYNC.slow_documented(text, key)
            only_passed = dict(doc)
            only_passed["autoclaude-pytest-snapshot:"] = {
                "passed": 4242, "skipped": doc["autoclaude-pytest-snapshot:"]["skipped"],
            }
            again = SYNC.slow_documented(SYNC.render_slow(text, only_passed, key), key)
            self.assertEqual(again["autoclaude-pytest-snapshot:"]["passed"], 4242)
            self.assertEqual(
                again["autoclaude-pytest-snapshot:"]["skipped"],
                doc["autoclaude-pytest-snapshot:"]["skipped"],
            )

    def test_slow_measurer_keys_are_all_implemented(self) -> None:
        """`_SLOW_SPECS` 的 measurer 名必須都被 `measure_slow()` 供給——擴充時漏接即 KeyError。

        以 AST 讀 `measure_slow()` 內 `by_measurer` 字典的鍵，不實跑（分鐘級）。
        """
        import ast

        src = (_REPO_ROOT / "tools" / "sync_onboarding_baselines.py").read_text(
            encoding="utf-8"
        )
        func = next(
            n for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.FunctionDef) and n.name == "measure_slow"
        )
        keys = {
            k.value
            for node in ast.walk(func)
            if isinstance(node, ast.Dict)
            for k in node.keys
            if isinstance(k, ast.Constant) and isinstance(k.value, str)
        }
        self.assertEqual(
            {s.measurer for s in SYNC._SLOW_SPECS} - keys, set(),
            "有 SlowSpec 的 measurer 沒有被 measure_slow() 供給 ⇒ --with-slow 會 KeyError",
        )


class TestProseClaimDialectsAreNotBoundToOnePunctuation(unittest.TestCase):
    """R60 round 3（ARCH-R60R3-01／SD-R60R3-01 二方獨立命中）：判準(2) 不得綁死 `=`。

    round 2 版本寫死 `R(\\d+)\\s*=\\s*(\\d+)`，於是**只要換一個標點就繞過整道判準**。
    這與同輪 ARCH 指出的架構反模式是同一個：**鎖比對表面形式、不比對語意**
    （`Find-GitBash` parity 只比字面值、本判準只認一種字面）。修法是把「主詞 × 連接」
    拆開，讓收一種新方言＝往集合裡加一個字。

    🔴 對抗式樣本一律以 `historical=()` 驅動：受鎖行上那些**真實的**歷史值在放寬判準後
    已依機制設計登記進 `_SPECS`，沿用真實登記會讓樣本被白名單合法放行而失去鑑別力。
    """

    #: 逐字取自 R60 round 3 複審回報的逸出樣本（放寬前**全部 GREEN**，全部應該要 RED）。
    _ESCAPED_DIALECTS = (
        "R60 收尾實測 756",
        "R60：756",
        "R60 — 756 tests OK",
        "round 3 實測 756",
        "R60 為 756",
        "MIN_TESTS 已重釘 756",
    )

    #: 必須維持 GREEN 的反樣本——放寬判準最大的風險是把具名 id 判成同量宣稱。
    _MUST_STAY_GREEN = (
        "沿革 R57=616 → R59=661",           # 已登記的歷史值
        "見 R60 SA-R60-01／ARCH-R60-03",     # finding id：`R60-01` 不得被讀成 R60=1
        "見 SD-R60-R2-03 與 QA2-R60-02",     # 同上，巢狀輪號形態
        "見 DEF-101-562 一案",                # 缺陷 id
        "1 支無 symlink 權限（[WinError 1314]）",  # 錯誤碼，非同量宣稱
        "R59 動工時為 11 支",                 # 有繫詞但量詞在後、位數不足門檻
        "R60 見本格 live 值",                 # 本判準要人改成的正確寫法
    )

    def _spec(self, historical: tuple = ()) -> SYNC.Spec:
        spec = next(s for s in SYNC._SPECS if s.anchor == "rootunit-baseline-live:")
        return replace(spec, historical=historical)

    def _problems(self, prose: str, historical: tuple = ()) -> list[str]:
        line = f"| **845 tests OK** {prose} <!-- rootunit-baseline-live: --> |"
        return SYNC.prose_problems(line, self._spec(historical), {"tests": 845})

    def test_every_escaped_dialect_is_now_rejected(self) -> None:
        """六種同義方言逐一驗紅——任何一種漏掉，判準就退回「只認一種標點」。"""
        survivors = [d for d in self._ESCAPED_DIALECTS if not self._problems(d)]
        self.assertEqual(
            survivors, [],
            "以下同量宣稱方言仍然逸出（判準無牙）：\n"
            + "\n".join(f"  · {s!r}" for s in survivors)
            + "\nWHY 這是缺陷而非潔癖：受鎖 token 由產生器保鮮，散文沒有任何產生器——"
            "散文裡的舊值一旦逸出登記，就是下一個誤導讀者的 stale 站點，"
            "而 round 2 的判準只要把 `=` 換成「：」或「實測」就能繞過去。",
        )

    def test_rejection_message_quotes_the_matched_text_verbatim(self) -> None:
        """訊息引在「」裡的那段必須**逐字出現在受檢行內**。

        WHY：round 2 的訊息把命中重組成 `R<n>=<v>` 字面，判準放寬後這個重組會與文件
        實際文字不同（例如文件寫「R60 為 756」而訊息印「R60=756」）⇒ 讀者拿著訊息
        在文件裡搜不到那一段。本支不要求引出整句（正則本就只覆蓋到值為止），
        只要求**引出來的東西是真的**。
        """
        for dialect in self._ESCAPED_DIALECTS:
            problems = self._problems(dialect)
            self.assertTrue(problems, f"{dialect!r} 未被判紅")
            quoted = re.findall(r"「([^」]+)」", problems[0])
            self.assertTrue(quoted, f"訊息未以「」引出命中原文：{problems[0]}")
            self.assertIn(
                quoted[0], dialect,
                f"訊息引的 {quoted[0]!r} 並非 {dialect!r} 的逐字片段（重組而非引用）",
            )

    def test_counter_samples_stay_green(self) -> None:
        """反樣本零誤紅——放寬判準最大的代價就是把 finding id 判成同量宣稱。"""
        false_reds = {
            s: self._problems(s, historical=(("57", 616, "x"), ("59", 661, "x")))
            for s in self._MUST_STAY_GREEN
        }
        false_reds = {k: v for k, v in false_reds.items() if v}
        self.assertEqual(
            false_reds, {},
            "以下反樣本被誤判為同量宣稱（判準太寬）：\n"
            + "\n".join(f"  · {k!r} → {v}" for k, v in false_reds.items()),
        )

    def test_ascii_hyphen_is_deliberately_not_a_link(self) -> None:
        """具名 id 是 `R<輪號>-<數字>` 形態 ⇒ 收 ASCII `-` 當連接會讓每個 id 都假紅。

        本支把該設計決定釘成回歸鎖：有人「順手把 `-` 也加進連接集合」時會在這裡紅。
        """
        self.assertIsNone(SYNC._PROSE_ROUND_CLAIM_RE.search("SA-R60-01"))
        self.assertIsNone(SYNC._PROSE_ROUND_CLAIM_RE.search("SD-R60-R2-03"))
        self.assertIsNotNone(SYNC._PROSE_ROUND_CLAIM_RE.search("R60 — 756"))

    def test_registered_value_is_allowed_in_every_dialect(self) -> None:
        """反向：值一旦**以相符的輪號**登記，六種方言都必須放行。

        兩筆登記是必要的：樣本集刻意混了兩種輪號主詞（`R60 …` 與 `round 3 …`），
        而判準(2) 對有輪號的宣稱是以 **(輪號, 值) 配對**比對，不是只看值——
        輪號對不上仍要紅（見下一支）。
        """
        registered = (("60", 756, "測試用登記"), ("3", 756, "測試用登記"))
        for dialect in self._ESCAPED_DIALECTS:
            self.assertEqual(
                self._problems(dialect, historical=registered), [],
                f"已登記的值在方言 {dialect!r} 下仍被判紅",
            )

    def test_registration_is_keyed_by_round_not_only_by_value(self) -> None:
        """輪號對不上時不得放行——否則「歷史值」會退化成任意數字的逃生口。"""
        problems = self._problems(
            "R60 收尾實測 756", historical=(("3", 756, "輪號對不上"),)
        )
        self.assertTrue(problems, "以錯誤輪號登記竟能放行 ⇒ 配對鍵形同虛設")

    def test_real_locked_lines_have_no_unregistered_claims(self) -> None:
        """正職：放寬後的判準對真實受鎖行零殘留（落地時它當場抓到兩條線各一筆）。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        measured = SYNC.measure_all()
        for spec in SYNC._SPECS:
            line = SYNC.anchored_line(text, spec.anchor)
            self.assertEqual(
                SYNC.prose_problems(line, spec, measured[spec.anchor]), [],
                f"受鎖行（{spec.anchor}）仍有未登記的同量宣稱",
            )


class TestHistoricalWaiverHasStaleSelfCheck(unittest.TestCase):
    """R60 round 3（QA-R60R3-02／ARCH-R60R3-01 附帶／SA-R60R3-04／SD-R60R3-02）。

    🔴 **四方全數獨立命中同一筆**：round 2 為判準(2) 新增 `Spec.historical` 這張豁免表，
    卻沒有給它任何 stale 自檢。諷刺點在於**同一個函式的判準(1)** 錯誤訊息自己寫著
    「本鎖刻意不設個別豁免——豁免表本身就是下一個 stale 站點」，而判準(2) 就設了一張。
    同 repo 兩張姊妹豁免表都有自檢（`_BASELINE_WAIVERS` 的
    `test_baseline_waivers_are_not_stale`、`archive_defect_log._ARITY_BASELINE` 的
    「實測 < 登記即紅」），本表是唯一例外 ⇒ 同輪內標準不一致。
    """

    def _spec(self) -> SYNC.Spec:
        return next(s for s in SYNC._SPECS if s.anchor == "rootunit-baseline-live:")

    def _line(self, prose: str) -> str:
        return f"| **845 tests OK** {prose} <!-- rootunit-baseline-live: --> |"

    def test_dead_registration_is_reported_and_named(self) -> None:
        """注入一筆文件從未出現過的登記 → 必須紅，且**指名要刪哪一筆**。"""
        spec = self._spec()
        injected = replace(
            spec, historical=spec.historical + (("42", 12345, "文件從未出現"),)
        )
        line = self._line("沿革 R57=616 → R59=661")
        problems = SYNC.historical_problems(line, injected, {"tests": 845})
        self.assertTrue(problems, "死登記未被偵測 ⇒ 豁免表沒有 stale 自檢（本輪根因）")
        self.assertTrue(
            any("42" in p and "12345" in p for p in problems),
            f"訊息未指名是哪一筆登記該刪：{problems}",
        )
        self.assertTrue(
            any("_SPECS" in p for p in problems),
            f"訊息未指出改哪裡：{problems}",
        )

    def test_control_group_live_registrations_are_not_flagged(self) -> None:
        """控制組：登記仍被散文引用時，零訊號（否則自檢會逼人刪掉有用的登記）。"""
        spec = self._spec()
        line = self._line("沿革 R57=616 → R59=661")
        self.assertEqual(
            SYNC.historical_problems(
                line, replace(spec, historical=spec.historical[:2]), {"tests": 845}
            ),
            [],
        )

    def test_registration_goes_stale_when_the_prose_is_deleted(self) -> None:
        """真實 stale 情境：散文被改寫／刪掉後，原本合法的登記必須轉紅。"""
        spec = replace(self._spec(), historical=(("57", 616, "R57 量測"),))
        alive = SYNC.historical_problems(
            self._line("沿革 R57=616"), spec, {"tests": 845}
        )
        gone = SYNC.historical_problems(
            self._line("沿革見左欄"), spec, {"tests": 845}
        )
        self.assertEqual(alive, [], "散文還在時不該紅")
        self.assertTrue(gone, "散文已刪而登記仍被視為有效 ⇒ 自檢無牙")

    def test_duplicate_value_registration_is_rejected(self) -> None:
        """同一個值登記兩筆會讓 leave-one-out 互相遮蔽 ⇒ 顯式擋在前面。"""
        spec = replace(
            self._spec(),
            historical=(("57", 616, "第一筆"), ("58", 616, "第二筆")),
        )
        problems = SYNC.historical_problems(
            self._line("沿革 R57=616 → R58=616"), spec, {"tests": 845}
        )
        self.assertTrue(
            any("互相遮蔽" in p for p in problems), f"重複登記未被擋：{problems}"
        )

    def test_stale_registration_reds_the_production_check_not_only_the_test(self) -> None:
        """🔴 自檢必須接在**生產路徑** `check()` 上，不能只活在測試裡。

        WHY：本輪四方反覆指出「沒有機械強制的就只是散文」。若 stale 自檢只寫成一支
        unittest，`--check` 這條被閘門與人工消費的路徑仍然零訊號。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        measured = SYNC.measure_all()
        self.assertEqual(SYNC.check(text, measured), [], "控制組：現況必須乾淨")

        original = SYNC._SPECS
        try:
            SYNC._SPECS = tuple(
                replace(s, historical=s.historical + (("42", 12345, "文件從未出現"),))
                for s in original
            )
            problems = SYNC.check(text, measured)
        finally:
            SYNC._SPECS = original
        self.assertTrue(
            any("stale" in p and "12345" in p for p in problems),
            f"死登記未讓生產路徑 check() 轉紅：{problems}",
        )

    def test_real_specs_have_no_stale_registrations(self) -> None:
        """正職：真實 `_SPECS` 的每一筆 historical 都仍被受鎖行引用。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        measured = SYNC.measure_all()
        for spec in SYNC._SPECS:
            line = SYNC.anchored_line(text, spec.anchor)
            self.assertEqual(
                SYNC.historical_problems(line, spec, measured[spec.anchor]), [],
                f"`{spec.anchor}` 的 historical 有 stale 登記（訊息會指名該刪哪一筆）",
            )

    def test_every_registration_carries_a_why(self) -> None:
        """每筆登記都必須附 WHY——無 WHY 的豁免無法被下一輪判斷該不該回收。"""
        for spec in SYNC._SPECS:
            for rnd, val, why in spec.historical:
                self.assertTrue(
                    why and len(why.strip()) >= 10,
                    f"{spec.anchor} 的登記 ({rnd}, {val}) 缺少可判讀的 WHY",
                )


class TestFingerprintGlobsAreSymmetricAndRecursive(unittest.TestCase):
    """R60 round 3（SD-R60R3-03）：四棵指紋樹的 glob 不得不對稱。

    round 2 版本三棵 SDD 樹用非遞迴 `*.py`、只有 AutoClaude 用 `**/*.py`，**無 WHY**。
    而表② 四格的計數全部來自 pytest，**pytest 收集測試是遞迴的** ⇒ 在任一棵的子目錄
    新增測試會改變計數而指紋不動＝觸發器漏。修法選「把三棵對齊成遞迴」而非「補一條
    WHY 說明會漏」：這是消除不對稱，不是加機制。
    """

    def test_all_trees_use_the_same_recursive_glob(self) -> None:
        """對稱性鎖：四棵 glob 必須一致且為遞迴（有人改回非遞迴即紅）。"""
        globs = {name: pat for name, _rel, pat in SYNC._FINGERPRINT_TREES}
        self.assertEqual(
            set(globs.values()), {"**/*.py"},
            f"指紋樹 glob 不對稱或非遞迴：{globs}——pytest 遞迴收集，非遞迴 glob 會讓"
            "子目錄新增的測試改變計數卻不觸發 presumed-stale",
        )

    def test_non_recursive_glob_misses_a_new_test_in_a_subdirectory(self) -> None:
        """鑑別力核心：以沙箱樹逐一比對「非遞迴漏、遞迴抓」。

        本支同時是 SD-R60R3-03 的**注入紅綠證據**：同一次新增子目錄測試檔，
        舊 glob 指紋不動（漏＝GREEN）、新 glob 指紋改變（抓＝RED）。
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tests"
            (tree / "unit").mkdir(parents=True)
            (tree / "test_top.py").write_bytes(b"x = 1\n")
            original = SYNC._REPO_ROOT
            try:
                SYNC._REPO_ROOT = Path(tmp).parent
                rel = Path(tmp).name + "/tests"
                flat_before = SYNC.tree_fingerprint(rel, "*.py")
                rec_before = SYNC.tree_fingerprint(rel, "**/*.py")
                # 注入：在子目錄新增一支測試（pytest 會收集到，計數必然改變）
                (tree / "unit" / "test_sub_probe.py").write_bytes(b"def test_x(): pass\n")
                flat_after = SYNC.tree_fingerprint(rel, "*.py")
                rec_after = SYNC.tree_fingerprint(rel, "**/*.py")
            finally:
                SYNC._REPO_ROOT = original

        self.assertEqual(
            flat_before, flat_after,
            "前提失效：非遞迴 glob 竟抓到子目錄新增檔（本測試的注入無鑑別力）",
        )
        self.assertNotEqual(
            rec_before, rec_after,
            "遞迴 glob 未偵測到子目錄新增的測試 ⇒ 觸發器仍漏，SD-R60R3-03 未修好",
        )

    def test_recursive_glob_still_covers_top_level_files(self) -> None:
        """`**/*.py` 不得因為改成遞迴而漏掉 top-level 檔（Path.glob 的 `**` 含當層）。"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tests"
            tree.mkdir()
            (tree / "test_top.py").write_bytes(b"x = 1\n")
            original = SYNC._REPO_ROOT
            try:
                SYNC._REPO_ROOT = Path(tmp).parent
                rel = Path(tmp).name + "/tests"
                before = SYNC.tree_fingerprint(rel, "**/*.py")
                (tree / "test_top.py").write_bytes(b"x = 2\n")
                after = SYNC.tree_fingerprint(rel, "**/*.py")
            finally:
                SYNC._REPO_ROOT = original
        self.assertNotEqual(before, after, "遞迴 glob 漏掉 top-level 檔 ⇒ 縮面")


class TestFingerprintIsLineEndingAgnostic(unittest.TestCase):
    """R60 round 3（DEF-101-613）：指紋不得隨 checkout 的行尾而變。

    原版直接 hash `read_bytes()`。而 `.gitattributes` 宣告 `* text=auto eol=lf`
    ⇒ 索引一律 LF，但本機 Windows 工作樹大量檔案是 CRLF（`git ls-files --eol` 數
    `i/lf w/crlf`：v0.01 樹 48／v0.30 樹 72／AutoClaude 樹 92）⇒ **任何 fresh clone／
    CI runner／macOS 機器 checkout 出來都是 LF，四格指紋必然全部對不上，
    `--check-snapshot` 開箱即紅**。今日零後果純粹因為只有這一台 Windows 機器在跑。

    本類別兩個方向都要鎖，缺一即是半套：
      - **跨平台等價**：同內容不同行尾 ⇒ 指紋必須**相同**（沒有 `_normalize_eol` 就紅）。
      - **未縮面**：真的改內容 ⇒ 指紋必須**不同**（證明沒把鑑別力連同行尾一起正規化掉）。
    """

    _LINES = (b"import os", b"", b"def test_x():", b"    assert os.sep", b"")

    @staticmethod
    def _fingerprint_of(files: dict[str, bytes]) -> str:
        """在沙箱暫存目錄建一棵測試樹並取其指紋（不碰真實 repo）。"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tests"
            tree.mkdir()
            for rel, body in files.items():
                target = tree / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)  # 🔴 bytes 層：write_text 會在 Windows 自行加 CR
            original = SYNC._REPO_ROOT
            try:
                SYNC._REPO_ROOT = Path(tmp).parent
                return SYNC.tree_fingerprint(Path(tmp).name + "/tests", "**/*.py")
            finally:
                SYNC._REPO_ROOT = original

    @classmethod
    def _tree_with_eol(cls, eol: bytes) -> dict[str, bytes]:
        """同一份內容、指定行尾；含子目錄檔以覆蓋遞迴 glob 那條路徑。"""
        body = eol.join(cls._LINES)
        return {"test_top.py": body, "unit/test_sub.py": body}

    def test_lf_and_crlf_checkouts_hash_identically(self) -> None:
        """跨平台等價（本筆的核心）：LF checkout 與 CRLF checkout 指紋必須相同。

        沒有 `_normalize_eol` 這一支就紅——它就是 DEF-101-613 的注入證據：
        「macOS 上會看到什麼」在本機唯一能取得的代理，就是同內容的 LF 版。
        """
        lf = self._fingerprint_of(self._tree_with_eol(b"\n"))
        crlf = self._fingerprint_of(self._tree_with_eol(b"\r\n"))
        self.assertEqual(
            lf, crlf,
            "同一份內容因行尾不同而指紋不同 ⇒ 指紋是平台相依的，"
            "fresh clone／macOS／CI runner 上 --check-snapshot 開箱即紅（DEF-101-613）",
        )

    def test_lone_cr_classic_mac_line_endings_also_normalize(self) -> None:
        """孤立 CR（classic Mac 行尾）也要折平——只處理 CRLF 會漏掉這一類。"""
        lf = self._fingerprint_of(self._tree_with_eol(b"\n"))
        cr = self._fingerprint_of(self._tree_with_eol(b"\r"))
        self.assertEqual(lf, cr, "孤立 CR 未被正規化 ⇒ 行尾方言仍會改變指紋")

    def test_real_content_change_still_changes_fingerprint(self) -> None:
        """未縮面：正規化只准吃行尾。改字元／增行／改檔名三種變動都必須仍然轉紅。"""
        base = self._tree_with_eol(b"\r\n")
        baseline = self._fingerprint_of(base)

        edited = dict(base)
        edited["test_top.py"] = base["test_top.py"].replace(b"os.sep", b"os.name")
        self.assertNotEqual(baseline, self._fingerprint_of(edited), "改內容而指紋不變 ⇒ 縮面")

        added_line = dict(base)
        added_line["unit/test_sub.py"] = base["unit/test_sub.py"] + b"assert True\r\n"
        self.assertNotEqual(baseline, self._fingerprint_of(added_line), "增行而指紋不變 ⇒ 縮面")

        renamed = {
            "test_top.py": base["test_top.py"],
            "unit/test_renamed.py": base["unit/test_sub.py"],
        }
        self.assertNotEqual(baseline, self._fingerprint_of(renamed), "改檔名而指紋不變 ⇒ 縮面")

    def test_non_utf8_and_bom_files_are_normalized_without_decoding(self) -> None:
        """正規化刻意留在 bytes 層：decode 會對非 UTF-8／含 BOM 的檔引進新的失敗模式。

        本支同時鎖住「不崩」與「仍等價」兩件事——只鎖不崩會讓有人改成
        `decode(errors="ignore")` 也通過，而那會靜默吃掉位元組＝縮面。
        """
        latin1 = b"# caf\xe9\r\n"  # 非法 UTF-8 續位元組
        bom = b"\xef\xbb\xbf# bom\r\n"
        crlf = self._fingerprint_of({"test_a.py": latin1, "test_b.py": bom})
        lf = self._fingerprint_of({
            "test_a.py": latin1.replace(b"\r\n", b"\n"),
            "test_b.py": bom.replace(b"\r\n", b"\n"),
        })
        self.assertEqual(crlf, lf, "非 UTF-8／BOM 檔的行尾正規化失效")

    def test_normalizer_folds_every_dialect_and_touches_nothing_else(self) -> None:
        """正規化器本身的單元鎖：三種行尾方言全折成 LF，其餘位元組一個都不准動。"""
        self.assertEqual(SYNC._normalize_eol(b"a\r\nb\rc\nd"), b"a\nb\nc\nd")
        self.assertEqual(SYNC._normalize_eol(b"a\r\n\rb"), b"a\n\nb", "CRLF 後接孤立 CR")
        untouched = b"a\tb \x00\xe9c\n"
        self.assertEqual(SYNC._normalize_eol(untouched), untouched, "正規化動到了非行尾位元組")

    def test_every_fingerprint_tree_is_stable_under_a_crlf_flip(self) -> None:
        """真實四棵樹的整體性檢查：把每棵樹的內容整份翻成 CRLF 後指紋不得改變。

        上面幾支用的是沙箱小樹（可控、快）；這一支直接拿**真實的四棵指紋樹**當輸入，
        避免「沙箱綠、真實樹另有形態（例如已含孤立 CR 的檔）而紅」的假安心。
        不寫檔——只在記憶體重算，故不動工作樹。
        """
        for name, rel, pat in SYNC._FINGERPRINT_TREES:
            root = SYNC._REPO_ROOT / rel
            digest_lf, digest_crlf = hashlib.sha256(), hashlib.sha256()
            for path in sorted(root.glob(pat)):
                if not path.is_file():
                    continue
                key = path.relative_to(root).as_posix().encode("utf-8")
                norm = SYNC._normalize_eol(path.read_bytes())
                for digest, body in ((digest_lf, norm), (digest_crlf, norm.replace(b"\n", b"\r\n"))):
                    digest.update(key)
                    digest.update(b"\0")
                    digest.update(SYNC._normalize_eol(body))
                    digest.update(b"\0")
            self.assertEqual(
                digest_lf.hexdigest()[: SYNC._FP_LEN], digest_crlf.hexdigest()[: SYNC._FP_LEN],
                f"[{name}] 真實測試樹在 CRLF checkout 下指紋改變 ⇒ 該格在 macOS 上會紅",
            )


class TestR67PlatformColumnIsFirstClass(unittest.TestCase):
    """R67-D1（本輪唯一 P1）：回填必須**只寫本機平台那一欄**，寫到別欄要在結構上不可能。

    WHY（測意圖非僅行為，Rule 9）：§7 表② 存在的**唯一**理由是「讓開發者分辨『平台差異』
    與『退化』」。R67 之前 `render_slow()` 的四組正則一律以 `**…**` 粗體錨定 Windows 欄
    （原註解自陳「以 `**` 包裝限定在 Windows 欄」），而 `measure_slow()` 量的是本機——於是
    在 macOS 上執行文件與 `--check-snapshot` 紅燈訊息**都指路**的那條回填指令，會把 macOS
    實測值靜默寫進標示「Windows 11 實測」的格子：表格還是滿的、指令還是 rc=0，但它從此
    在說謊。這比空著更糟——空著至少看得出來沒人量。

    故本類別鎖的不是「render_slow 會改字」，而是**「另一個平台欄逐字不動」**這條不變量：
    這是「平台差異可讀」這個目的在程式碼裡唯一能被機械檢查的形式。

    邊界（誠實劃界）：本鎖保證「不會寫到別欄」，**不保證**寫進來的數字本身是在對的環境
    量的（那由 `snapshot-fingerprints-<平台>` 錨的 provenance ＋ `--write --with-slow` 的
    pgextras 守門負責，見 TestR67PerPlatformFingerprints／TestR67CliFailsLoud）。
    """

    def setUp(self) -> None:
        self.text = _ONBOARDING.read_text(encoding="utf-8-sig")
        self.synthetic = {
            "autoclaude-pytest-snapshot:": {"passed": 8881, "skipped": 777},
            "cigate-v001-snapshot:": {"passed": 8882},
            "cigate-v030-snapshot:": {"passed": 8883},
            "cigate-scripts-snapshot:": {"passed": 8884},
        }

    def _cells(self, text: str, platform_key: str) -> dict[str, str]:
        lines = text.split("\n")
        return {
            spec.anchor: SYNC._split_row(lines[SYNC._anchored_index(lines, spec.anchor)])[
                SYNC.platform_cell_index(lines, SYNC._anchored_index(lines, spec.anchor), platform_key)
            ]
            for spec in SYNC._SLOW_SPECS
        }

    def test_writing_one_platform_leaves_every_other_column_byte_identical(self) -> None:
        """核心不變量：寫 A 平台欄時，B 平台欄**逐字不變**（R67-D1 的直接反例形態）。"""
        for target in SYNC._PLATFORM_COLUMN_LABELS:
            rendered = SYNC.render_slow(self.text, self.synthetic, target)
            self.assertEqual(
                SYNC.slow_documented(rendered, target), self.synthetic,
                f"{target} 欄沒被寫進去 ⇒ 回填無效",
            )
            for other in SYNC._PLATFORM_COLUMN_LABELS:
                if other == target:
                    continue
                self.assertEqual(
                    self._cells(rendered, other), self._cells(self.text, other),
                    f"寫 {target} 欄時動到了 {other} 欄——這正是 R67-D1：在 macOS 跑回填"
                    f"會把 macOS 數字寫進標示「Windows 11 實測」的格子，並產生一句假 provenance",
                )
                self.assertEqual(
                    SYNC.slow_documented(rendered, other), SYNC.slow_documented(self.text, other),
                )

    def test_column_index_is_derived_from_the_header_not_hardcoded(self) -> None:
        """欄號必須由表頭推導：在平台欄之前插一欄，抽取結果不得改變。

        鑑別力來源：寫死欄號（或靠 `**` 粗體錨定）在這個構造下會抽到新插入的那一欄。
        """
        lines = self.text.split("\n")
        anchor = SYNC._SLOW_SPECS[0].anchor
        idx = SYNC._anchored_index(lines, anchor)
        header_idx = next(
            i - 1 for i in range(idx - 1, -1, -1) if SYNC._SEPARATOR_ROW_RE.match(lines[i])
        )
        sep_idx = header_idx + 1
        widened = list(lines)
        widened[header_idx] = _insert_cell(lines[header_idx], 1, " R67 探針欄 ")
        widened[sep_idx] = _insert_cell(lines[sep_idx], 1, "---")
        for spec in SYNC._SLOW_SPECS:
            row = SYNC._anchored_index(lines, spec.anchor)
            widened[row] = _insert_cell(lines[row], 1, " 探針 ")
        widened_text = "\n".join(widened)
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            self.assertEqual(
                SYNC.slow_documented(widened_text, key), SYNC.slow_documented(self.text, key),
                f"插入一欄後 {key} 欄抽到的值改變 ⇒ 欄號被寫死（或靠粗體猜欄）",
            )

    def test_broken_table_structure_fails_loud_instead_of_guessing(self) -> None:
        """表頭抽不到該平台識別字時必須 fail-loud——猜欄就是把數字寫錯格。"""
        lines = self.text.split("\n")
        idx = SYNC._anchored_index(lines, SYNC._SLOW_SPECS[0].anchor)
        header_idx = next(
            i - 1 for i in range(idx - 1, -1, -1) if SYNC._SEPARATOR_ROW_RE.match(lines[i])
        )
        broken = list(lines)
        broken[header_idx] = lines[header_idx].replace("macOS", "MAC-OS")
        with self.assertRaises(AssertionError) as ctx:
            SYNC.slow_documented("\n".join(broken), "darwin")
        self.assertIn("平台識別字", str(ctx.exception))

    def test_unmanaged_platform_gets_no_column_instead_of_a_guessed_one(self) -> None:
        """Linux（CI runner）沒有欄 ⇒ 回 None，不得硬塞一欄。"""
        self.assertIsNone(SYNC.current_platform_key("linux"))
        self.assertEqual(SYNC.current_platform_key("darwin"), "darwin")
        self.assertEqual(SYNC.current_platform_key("win32"), "win32")

    def test_provenance_inside_a_managed_cell_fails_loud(self) -> None:
        """格內混進第二個數字（例如 `1729（R59 記載）`）必須 fail-loud、且訊息指路 provenance 該住哪。

        WHY：R67 前 macOS 欄就是這樣寫的，於是那一格永遠抽不出乾淨的值、也永遠沒人回填。
        """
        lines = self.text.split("\n")
        idx = SYNC._anchored_index(lines, "cigate-v030-snapshot:")
        col = SYNC.platform_cell_index(lines, idx, "darwin")
        cells = SYNC._split_row(lines[idx])
        cells[col] = cells[col].rstrip() + "（R59 記載） "
        polluted = list(lines)
        polluted[idx] = "|".join(cells)
        with self.assertRaises(AssertionError) as ctx:
            SYNC.slow_documented("\n".join(polluted), "darwin")
        self.assertIn("snapshot-fingerprints-darwin:", str(ctx.exception))


def _insert_cell(line: str, position: int, cell: str) -> str:
    parts = SYNC._split_row(line)
    parts.insert(position, cell)
    return "|".join(parts)


class TestR67PerPlatformFingerprints(unittest.TestCase):
    """R67-D6：指紋/provenance 逐平台記帳——另一欄的 stale 不得在結構上永遠測不到。

    WHY：原版只有一條全域 `snapshot-fingerprints:` 錨，語意是「上一次回填時的測試樹」；
    但回填在結構上只寫得到一欄（見 R67-D1）⇒ 另一欄的 stale **永遠不可能被偵測**。
    實測（Scan-D）：把 macOS 欄三格灌成 9999，`--check-snapshot` 照樣印 ✅ rc=0。
    一個「該紅時結構上不可能紅」的守門比沒有守門更糟：它會讓人以為那一欄被看著。

    本類別一律以**合成的「兩欄皆新鮮」文本**驅動（把 live 指紋寫進兩欄），刻意不依賴
    真實文件當下是否新鮮——否則本鎖會在任何一輪動到測試樹時連帶假紅，而回填要付分鐘級
    代價（同 TestSnapshotFingerprintTripwire 的既定紀律）。
    """

    def setUp(self) -> None:
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        live = SYNC.measure_fingerprints()
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            text = SYNC.render_fingerprints(text, live, key, SYNC.parse_provenance(text, key))
        self.fresh = text
        self.live = live

    def _tamper(self, key: str) -> str:
        return SYNC.render_fingerprints(
            self.fresh,
            {name: "f" * SYNC._FP_LEN for name, _r, _p in SYNC._FINGERPRINT_TREES},
            key,
            SYNC.parse_provenance(self.fresh, key),
        )

    def test_control_group_both_columns_fresh_is_green_everywhere(self) -> None:
        """鑑別力自證：合成的新鮮文本在每個平台視角下都不得有問題（非恆紅載具）。"""
        for key in (*SYNC._PLATFORM_COLUMN_LABELS, None):
            problems, notices = SYNC.snapshot_report(self.fresh, key)
            self.assertEqual(problems, [], f"平台 {key} 視角下合成新鮮文本仍紅")
            self.assertEqual(notices, [], f"平台 {key} 視角下合成新鮮文本仍有提醒")

    def test_each_platform_column_staleness_is_detectable_from_that_platform(self) -> None:
        """**本鎖的核心**：任一欄 stale，都能從該平台的視角被測到（R67-D6 反例）。"""
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            problems = SYNC.check_snapshot(self._tamper(key), key)
            self.assertEqual(
                len(problems), len(SYNC._FINGERPRINT_TREES),
                f"{key} 欄整欄 stale 卻測不到 ⇒ 該欄在結構上不受監看（R67-D6 原始形態）",
            )
            self.assertTrue(
                all(SYNC._PLATFORM_COLUMN_LABELS[key] in p for p in problems), problems
            )

    def test_other_platform_staleness_is_a_notice_not_an_rc_failure(self) -> None:
        """別台機器的欄只做 ⚠️：本機修不動的東西硬紅只會養成忽略紅燈的習慣。

        另鎖「⚠️ 必須是**單行**摘要」：這條訊息每次 pre-push 都會印，逐格長文會洗版到
        讓人自動略過——那時真正該看的紅燈也一起被略過（本 repo 對「養成忽略紅燈」的
        既定紀律，同表② 刻意不接根層閘門的理由）。
        """
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            for other in SYNC._PLATFORM_COLUMN_LABELS:
                if other == key:
                    continue
                problems, notices = SYNC.snapshot_report(self._tamper(other), key)
                self.assertEqual(problems, [], f"{other} 欄 stale 卻讓 {key} 視角 rc 紅")
                self.assertEqual(len(notices), 1, notices)
                self.assertNotIn("\n", notices[0], "別平台欄的 ⚠️ 必須壓成單行")
                self.assertIn(SYNC._PLATFORM_COLUMN_LABELS[other], notices[0])

    def test_unmanaged_platform_degrades_to_all_columns_stale(self) -> None:
        """Linux CI runner：判準退化為「沒有任何一欄新鮮才紅」（弱，但不冤）。"""
        one_stale = self._tamper(next(iter(SYNC._PLATFORM_COLUMN_LABELS)))
        problems, notices = SYNC.snapshot_report(one_stale, None)
        self.assertEqual(problems, [], "只有一欄 stale 就讓無欄平台紅 ⇒ 判準比宣告的強，文件失實")
        self.assertTrue(notices)

        all_stale = one_stale
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            all_stale = SYNC.render_fingerprints(
                all_stale,
                {name: "e" * SYNC._FP_LEN for name, _r, _p in SYNC._FINGERPRINT_TREES},
                key,
                SYNC.parse_provenance(all_stale, key),
            )
        self.assertTrue(
            SYNC.snapshot_report(all_stale, None)[0],
            "全部欄皆 stale 而無欄平台仍綠 ⇒ 退化判準也失效（root-infra-ci 跑的就是這條）",
        )

    def test_every_platform_anchor_carries_full_provenance(self) -> None:
        """provenance 四欄缺一即 fail-loud——它是這張表能被信任的全部理由。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for key in SYNC._PLATFORM_COLUMN_LABELS:
            prov = SYNC.parse_provenance(text, key)
            self.assertEqual(sorted(prov), sorted(SYNC._PROVENANCE_FIELDS))
            for field, value in prov.items():
                self.assertTrue(value.strip(), f"{key}/{field} 為空")
            line = SYNC.anchored_line(text, SYNC.fingerprint_anchor(key))
            for field in SYNC._PROVENANCE_FIELDS:
                broken = text.replace(line, line.replace(f"{field}=", f"{field}_gone="), 1)
                with self.assertRaises(AssertionError) as ctx:
                    SYNC.parse_provenance(broken, key)
                self.assertIn(field, str(ctx.exception))

    def test_table1_macos_cell_declares_it_is_not_lock_covered(self) -> None:
        """R67-F28：表① 的 macOS 欄必須自陳「不受 live 鎖管轄」，且不得再寫死收集總數。

        WHY：`rootunit-baseline-live` 鎖只抽**右欄**那個 `N tests OK` token，macOS 欄是純
        散文。原本該格寫死 `616（skipped=4；R57 量測）`，落後實況約九輪而**任何機械物都
        抓不到**——它根本不在鎖的取值範圍內；而該格與受鎖格同處一張標榜「live 格（有機械
        鎖）」的表內，讀者會誤以為「有鎖所以可信」（R60 ARCH-R60-03 的原始成因）。
        故判準有兩條：(a) 該格必須自陳不受鎖管轄；(b) 不得再寫死收集總數（改指向 live 值）。
        """
        lines = _ONBOARDING.read_text(encoding="utf-8-sig").split("\n")
        idx = SYNC._anchored_index(lines, "rootunit-baseline-live:")
        # 表① 表頭同樣有 macOS／Windows 兩欄 ⇒ 直接複用同一套「由表頭推導欄號」機制，
        # 不另寫第二份定位邏輯（本檔一直在治的「同一語意兩份實作」）。
        macos_cell = SYNC._split_row(lines[idx])[
            SYNC.platform_cell_index(lines, idx, "darwin")
        ]
        self.assertIn(
            "不受 live 鎖管轄", macos_cell,
            "表① macOS 欄未自陳不受 live 鎖管轄——它與受鎖格同處一張標榜「有機械鎖」的表，"
            "不寫明就會被讀成「有鎖所以可信」",
        )
        live_tests = SYNC.measure_rootunit()["tests"]
        self.assertNotIn(
            str(live_tests), macos_cell,
            "表① macOS 欄又寫死了收集總數——該格無鎖，寫死即下一個 stale 站點；"
            "正確形態是指向右欄 live 值",
        )

    def test_table1_locked_column_header_does_not_speak_for_a_provenance(self) -> None:
        """SA-R67-07 的回歸鎖：表① **受鎖欄的欄頭**不得代言量測平台／時點。

        WHY（成因是結構性的，不是筆誤）：`rootunit-baseline-live` 抽的 token 取自
        `run_root_unittests.MIN_TESTS`，那是一個**平台中立**的下限釘選——誰在哪台機器重釘
        都寫進同一格。而該格所在欄的欄頭長年寫著「Windows 11（R60 收尾實測）」，於是
        R67 在 Darwin 真機重釘後，一個 macOS 量得的數字就靜靜掛在標示「Windows 11 實測」
        的欄頭底下。**產生器把 token 洗新鮮了，欄頭卻沒有任何機械物在看**——與 DEF-101-562
        （「只保證被抽取的 token 新鮮，不保證同一行的散文新鮮」）是同一個病灶的欄頭版。

        判準刻意寫成**正面斷言**（欄頭必須自陳中立），不寫成「不得出現『收尾實測』」：
        訂正段必須逐字引述被推翻的原句才能讓讀者辨認版本，而這一格是**單行巨欄**
        （整格就是檔案裡的一行），任何同行豁免都會把整格放行——那正是
        `ADR-XPLAT-002` §9.1 SC-4 已記載的坑。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        self.assertEqual(
            locked_column_header_problems(text), [],
            "表① 受鎖欄的欄頭又開始代言量測平台／時點：\n  "
            + "\n  ".join(locked_column_header_problems(text)),
        )

    def test_the_locked_column_header_lock_has_teeth(self) -> None:
        """注入：把欄頭還原成 SA-R67-07 命中的那個形態，必須轉紅並指名缺哪一句。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        lines = text.split("\n")
        header_idx, col = _locked_header_coordinates(lines)
        cells = SYNC._split_row(lines[header_idx])
        cells[col] = " **Windows 11（R60 收尾實測）** "
        lines[header_idx] = "|".join(cells)
        reverted = "\n".join(lines)
        self.assertNotEqual(reverted, text, "注入基底失效：欄頭沒有被改到")
        problems = locked_column_header_problems(reverted)
        self.assertTrue(problems, "還原成被推翻的欄頭形態仍綠 ⇒ 本鎖無牙")
        self.assertIn(_HEADER_NEUTRALITY_TOKEN, problems[0])

    def test_the_r60_generation_provenance_table_is_marked_as_historical(self) -> None:
        """SA-R67-07 的另一半：R60 世代的 provenance 表必須自標世代，否則會被讀成現況。

        WHY：R65 只回填四格中的一格，該表自此**混世代**；它卻仍以現行 provenance 的姿態
        與表② 並存 ⇒ 同一節裡兩套結論相反的 provenance，讀者採信先看到的那一套。
        判準錨在**語意欄名**（`誰實測過`）而不是整句散文，且 0 個或多個命中皆 fail-loud
        （防「刪掉表頭＝靜默縮面」）。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        self.assertEqual(
            historical_provenance_marking_problems(text), [],
            "\n  ".join(historical_provenance_marking_problems(text)),
        )

    def test_the_historical_provenance_lock_has_teeth(self) -> None:
        """注入兩種退化：拿掉世代標記（紅）、以及整列消失／複製（fail-loud 紅）。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        header = next(ln for ln in text.split("\n") if _PROVENANCE_COLUMN_TOKEN in ln)
        for what, mutated in (
            ("拿掉世代標記", text.replace(header, header.replace(_HISTORICAL_TOKEN, "現行"))),
            ("整列消失", text.replace(header, "")),
            ("表頭被複製", text.replace(header, header + "\n" + header)),
        ):
            with self.subTest(injection=what):
                self.assertNotEqual(mutated, text, f"注入基底失效：{what}")
                self.assertTrue(
                    historical_provenance_marking_problems(mutated),
                    f"{what} 後仍綠 ⇒ 本鎖無牙",
                )

    def test_unrecorded_fingerprint_never_matches_a_live_tree(self) -> None:
        """`unrecorded` 佔位值必須恆判 stale——否則「不可考」會被誤讀成「新鮮」。"""
        self.assertNotIn(SYNC._UNRECORDED, set(SYNC.measure_fingerprints().values()))
        self.assertFalse(
            re.fullmatch(rf"[0-9a-f]{{{SYNC._FP_LEN}}}", SYNC._UNRECORDED),
            "佔位值長得像真指紋 ⇒ 有機率與 live 值相等而假裝新鮮",
        )


class TestR67R2OtherPlatformNoticeIsNotAStandingWarning(unittest.TestCase):
    """R67 round 2（QA-R67-05）：別平台欄那一則**結構上恆亮**，故不得掛在警告頻道。

    WHY（Rule 9 — 測意圖）：單機交替工作流（R66 在 Windows、R67 在 macOS、下一輪再換）下，
    任一輪都會動到四棵樹之一 ⇒ 另一平台欄的指紋必然對不上，且**本機無論如何都清不掉**
    （回填必須在那台機器上實跑）。於是它是一則「系統完全正常時也永遠亮著」的訊號。本 repo
    已明文論證過後果（`tools/run_root_unittests.py`：「常亮的警告＝背景噪音」）——讀者學會
    略過這一段，就會連同段真正有牙的「本機平台欄轉紅」一起略過。

    本類別鎖的三條不變量：訊息**在 stdout 的資訊頻道**（不是 stderr 的 ⚠️）、**從未回填過**
    與**回填過但過期**兩種狀態措辭可區分、且後者帶「距上次量測幾天」這個唯一可行動的量。

    🔴 R67 round 3：視角欄由「本機平台欄」改為**固定挑一對受管欄**。原版 `setUp` 斷言
    `current_platform_key()` 不得為 None，於是整類三支在無欄平台（Linux CI runner）上
    全紅——但本類別驗的是 `snapshot_report()` 的「別欄提醒」機制，它吃「以哪一欄為視角」
    當參數，跟本機是哪個平台無關。詳見 `TestSnapshotFingerprintTripwire.
    test_check_snapshot_reds_on_documented_drift` 的同款論證。
    """

    def setUp(self) -> None:
        keys = sorted(SYNC._PLATFORM_COLUMN_LABELS)
        self.assertGreaterEqual(
            len(keys), 2, "表② 少於兩欄 ⇒ 本鎖無標的（增／減平台欄時請同步檢視）"
        )
        # 固定的 (視角欄, 別欄)：與 host 無關才能在每個平台上跑同一件事。
        self.viewpoint, self.other = keys[0], keys[1]
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        live = SYNC.measure_fingerprints()
        # 視角欄填成新鮮（不讓真實文件當下是否過期干擾本鎖），別平台欄由各測試自行擺弄。
        self.text = SYNC.render_fingerprints(
            text, live, self.viewpoint, SYNC.parse_provenance(text, self.viewpoint)
        )
        self.stale_fp = {name: "0" * SYNC._FP_LEN for name, _r, _p in SYNC._FINGERPRINT_TREES}

    def _notice(self, provenance: dict[str, str]) -> str:
        tampered = SYNC.render_fingerprints(self.text, self.stale_fp, self.other, provenance)
        problems, notices = SYNC.snapshot_report(tampered, self.viewpoint)
        self.assertEqual(problems, [], "別平台欄 stale 不得計入視角欄的 rc")
        self.assertEqual(len(notices), 1, notices)
        self.assertNotIn("\n", notices[0], "別平台欄的提醒必須壓成單行")
        self.assertIn(SYNC._PLATFORM_COLUMN_LABELS[self.other], notices[0])
        return notices[0]

    def test_pre_mechanism_column_is_never_described_as_never_measured(self) -> None:
        """🔴 **DEF-101-756 的直接回歸鎖**：provenance 全 `unrecorded` **不等於**沒量過。

        R67 這支測試的前身鎖的是「`unrecorded` ⇒ 訊息含『尚未建立基線』」——**而那句話對
        Windows 欄是假的**：該欄裝著 Windows 實機量得的數字，`unrecorded` 講的只是量測環境
        沒被記下來。主控讀到那句話，向使用者宣稱  # stale-premise-ok: 逐字保全原話
        「Windows 側從未有真機輪」而被開發史當場  # stale-premise-ok: 本鎖的立案樣本
        駁回（R20／R42／R59／R64／R66 皆為 Windows 真機輪，且每日 02:00 有 Windows nightly）。

        本鎖驗的**意圖**（Rule 9）：一則會被拿去做平台決策的訊息，**不得**在只知道
        「provenance 沒記」的情況下說出「沒量過」。判準是因果的——「有沒有量過」的證據是
        表② 那一欄有沒有數字，不是 provenance 欄位。
        """
        notice = self._notice({
            **{f: SYNC._UNRECORDED for f in SYNC._ENV_PROVENANCE_FIELDS},
            SYNC._ORIGIN_FIELD: SYNC._ORIGIN_PRE_MECHANISM,
        })
        self.assertIn("已有實機量測基線", notice)
        self.assertIn("不是平台覆蓋缺口", notice, "未講清楚缺的是 provenance 而非量測")
        for banned in ("尚未建立基線", "從未量測", "沒量過"):
            self.assertNotIn(
                banned, notice,
                f"訊息含「{banned}」——那正是 DEF-101-756 讓主控誤判的措辭；"
                f"該欄有實測數字時不得以任何「沒量過」形態的字眼呈現",
            )
        self.assertNotIn("→", notice, "不得以漂移箭頭把 unrecorded 畫成「量過但過期」")

    def test_a_truly_never_measured_column_still_says_so(self) -> None:
        """對照組：真的沒量過時**必須**說得出口——本輪修的是二義性，不是把警訊消音。

        沒有這一支，上一支會退化成「永遠不准說沒量過」，那是另一個方向的假宣稱。
        """
        stripped = self.text
        for spec in SYNC._SLOW_SPECS:  # 把該欄四格的數字拿掉＝真的沒有量測
            lines = stripped.split("\n")
            idx = SYNC._anchored_index(lines, spec.anchor)
            cells = SYNC._split_row(lines[idx])
            col = SYNC.platform_cell_index(lines, idx, self.other)
            cells[col] = " （未量測） "
            lines[idx] = "|".join(cells)
            stripped = "\n".join(lines)
        self.text = stripped
        notice = self._notice({
            **{f: SYNC._UNRECORDED for f in SYNC._ENV_PROVENANCE_FIELDS},
            SYNC._ORIGIN_FIELD: SYNC._ORIGIN_NEVER,
        })
        self.assertIn("從未量測", notice)
        self.assertIn("平台覆蓋缺口", notice)

    def test_declaring_never_measured_while_the_table_shows_numbers_fails_loud(self) -> None:
        """🔴 **(b) 根因的機械鎖**：宣告與資料矛盾時當場 fail-loud，而不是印出那句錯話。

        R67 引入 provenance 機制時**沒有回溯處理既有資料**，Windows 欄整欄填 `unrecorded`
        了事 ⇒「機制引入前就存在的量測」與「不存在的量測」變成同一個字。本鎖讓那個狀態
        在結構上無法靜默存在：只要表② 該欄還有數字，任何「從未量測」的宣告都會炸。
        """
        tampered = SYNC.render_fingerprints(
            self.text, self.stale_fp, self.other,
            {**{f: SYNC._UNRECORDED for f in SYNC._ENV_PROVENANCE_FIELDS},
             SYNC._ORIGIN_FIELD: SYNC._ORIGIN_NEVER},
        )
        with self.assertRaises(AssertionError) as ctx:
            SYNC.snapshot_report(tampered, self.viewpoint)
        self.assertIn("DEF-101-756", str(ctx.exception))

    def test_recorded_but_drifted_column_reports_measurement_age(self) -> None:
        """回填過的欄要給「距今幾天」——那是這一則裡唯一隨時間變化、也唯一可行動的量。

        四棵樹的指紋 diff 每輪都不同但資訊量為零（它只是在說「樹動過了」，而在單機交替下
        那是必然）；真正決定「該不該換台機器補量」的是**上次量測有多久了**。
        """
        past = datetime.date.today() - datetime.timedelta(days=37)
        notice = self._notice({
            "measured-at": past.isoformat(),
            "host": "probe-host",
            "docker": "up",
            "pgextras": "absent",
            SYNC._ORIGIN_FIELD: SYNC._ORIGIN_SELF,
        })
        self.assertIn("距今 37 天", notice)
        self.assertIn("結構性常態", notice, "未說明它在單機交替下恆亮 ⇒ 讀者會當成新問題追")
        self.assertIn("本機平台欄", notice, "未把注意力指回有牙的那一半")

    def test_notice_goes_to_stdout_information_channel_not_the_warning_channel(self) -> None:
        """頻道不變量：提醒印在 stdout 且不帶 ⚠️；警告頻道只留給本機修得動的東西。

        以替身 `snapshot_report` 驅動，讓本鎖與「真實文件當下是否過期」解耦——否則某一輪
        剛好兩欄都新鮮時，本鎖會退化成恆真而沒人發現。
        """
        probe = "PROBE-NOTICE-R67R2"
        original = SYNC.snapshot_report
        out, err = io.StringIO(), io.StringIO()
        try:
            SYNC.snapshot_report = lambda *a, **k: ([], [probe])
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = SYNC.main(["--check-snapshot"])
        finally:
            SYNC.snapshot_report = original
        self.assertEqual(rc, 0, "無 rc 級問題時不得因提醒而回非零")
        self.assertIn(probe, out.getvalue(), "別平台欄提醒未進 stdout 資訊頻道")
        self.assertNotIn(probe, err.getvalue(), "提醒仍印在 stderr ⇒ 仍在警告頻道")
        self.assertNotIn("⚠️", out.getvalue() + err.getvalue(), "恆亮訊息不得掛 ⚠️ 標記")


class TestR67CliFailsLoud(unittest.TestCase):
    """R67-D20：CLI 改 argparse——未知旗標／打錯字一律 rc=2，文件不得引用不存在的旗標。

    WHY：原版 `"--flag" in argv` 手搓解析，未知旗標一律靜默掉進 default 分支並 rc=0。
    實測後果（Scan-D 於乾淨 clone 注入真實過期後）：正確拼法 rc=1，少打一個字母 rc=0
    **假綠**——同一棵工作樹、同一時刻，該紅的守門回綠燈。而 `--check` 這個被 ONBOARDING
    §7、`CrossPlatform_Scan_Dimensions.md`、`ADR-XPLAT-002` 三份文件引用的旗標，在 R67
    之前**根本不存在**，只是恰好掉進 default 分支才「看起來對」。

    修法選「把 `--check` 實作為真旗標」而非「改三份文件」：那三份文件有兩份不在本包授權
    範圍內，且「產生器 ＋ `--check`」本就是本 repo 既有慣例（`snapshot_sync.py`）——讓字面
    成真比讓三份文件改口更小、也更對。
    """

    def test_unknown_flag_is_rejected_with_rc2(self) -> None:
        for bogus in ("--totally-bogus-flag", "--wtih-slow", "--checks"):
            self.assertEqual(
                SYNC.main([bogus]), 2,
                f"未知旗標 {bogus} 未 fail-loud——靜默放行就是 rc=0 假綠的來源",
            )

    def test_prefix_abbreviation_is_rejected(self) -> None:
        """`allow_abbrev=False`：打錯字不得被「好心地」補全成正確旗標。

        WHY 這條要單獨測：argparse **預設**接受唯一前綴縮寫，於是少打一個字母會被解讀成
        原旗標——看似無害，實則保留了一條「靠運氣正確」的路，與本檔「拼錯就要當場知道」
        的主張自相矛盾。
        """
        self.assertEqual(SYNC.main(["--check-snapsho"]), 2)
        self.assertEqual(SYNC.main(["--check-snap"]), 2)

    def test_help_prints_usage_and_returns_zero(self) -> None:
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = SYNC.main(["--help"])
        self.assertEqual(rc, 0)
        self.assertIn("--check-snapshot", buf.getvalue())
        self.assertIn("--platform", buf.getvalue())

    def test_mode_flags_are_mutually_exclusive(self) -> None:
        self.assertEqual(SYNC.main(["--check", "--json"]), 2)
        self.assertEqual(SYNC.main(["--write", "--check-snapshot"]), 2)

    def test_with_slow_requires_write(self) -> None:
        self.assertEqual(SYNC.main(["--with-slow"]), 2)
        self.assertEqual(SYNC.main(["--check", "--with-slow"]), 2)

    def test_platform_may_not_be_combined_with_write(self) -> None:
        """跨平台代填＝替另一台機器捏造 provenance，正是 R67-D1 本體 ⇒ rc=2。"""
        self.assertEqual(SYNC.main(["--write", "--platform", "win32"]), 2)
        self.assertEqual(SYNC.main(["--write", "--with-slow", "--platform", "darwin"]), 2)

    def test_platform_choices_cover_exactly_the_managed_columns(self) -> None:
        action = next(
            a for a in SYNC.build_parser()._actions if "--platform" in a.option_strings
        )
        self.assertEqual(sorted(action.choices), sorted(SYNC._PLATFORM_COLUMN_LABELS))

    def test_documented_flags_all_exist_in_the_parser(self) -> None:
        """**文件不得引用不存在的旗標**（R67-D20 的另一半）。

        掃描面（誠實劃界）：**提及 `sync_onboarding_baselines` 的那些行**上的每一個
        `--flag`（反引號與否皆算）——來源＝ONBOARDING.md 全檔 ＋ 本工具 docstring 的
        「用法」區塊（該區塊每一行都是本工具的呼叫式，正是最容易寫出假旗標的地方）。
        刻意不掃全節：§7 內另有 pytest 的 `--collect-only` 等他人旗標，全節掃描會大量假紅。
        未覆蓋面（如實揭露）：散落在**不提工具名**之行上的旗標，例如
        `CrossPlatform_Scan_Dimensions.md`／`ADR-XPLAT-002` 的引用——那兩份不在本包授權
        範圍內，本輪改以「把 `--check` 實作成真旗標」讓它們的字面成真，而非改它們的字。
        """
        known = {
            opt
            for action in SYNC.build_parser()._actions
            for opt in action.option_strings
        }
        flag_re = re.compile(r"(--[a-z][a-z0-9-]*)")
        module_doc = SYNC.__doc__ or ""
        blobs = [
            (f"ONBOARDING.md:{i + 1}", line)
            for i, line in enumerate(_ONBOARDING.read_text(encoding="utf-8-sig").split("\n"))
        ] + [
            (f"sync_onboarding_baselines.__doc__ 用法區塊 L{i + 1}", line)
            for i, line in enumerate(module_doc[module_doc.index("用法"):].split("\n"))
        ]
        seen: set[str] = set()
        for where, line in blobs:
            if "sync_onboarding_baselines" not in line:
                continue
            for flag in flag_re.findall(line):
                seen.add(flag)
                self.assertIn(
                    flag, known,
                    f"{where} 引用了不存在的旗標 {flag}——這正是 R67-D20：`--check` 曾被三份"
                    f"文件引用而它根本不是實存旗標，只是恰好掉進 default 分支。"
                    f"現存旗標：{sorted(known)}",
                )
        self.assertGreaterEqual(
            len(seen), 5,
            f"只從文件抽到 {sorted(seen)}——抽取式疑似漂移導致靜默 0 命中假綠",
        )
        self.assertIn("--check", seen, "`--check` 是 R67-D20 的原始標的，必須在掃描面內")

    def test_audit_mode_is_the_default_and_check_flag_is_real(self) -> None:
        """`--check` 與「不給旗標」必須是同一條路（文件宣稱的就是這件事）。"""
        parser = SYNC.build_parser()
        self.assertTrue(parser.parse_args(["--check"]).check)
        self.assertFalse(parser.parse_args([]).check)
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        measured = SYNC.measure_all()
        expected = 1 if SYNC.check(text, measured) else 0
        self.assertEqual(SYNC.main(["--check"]), expected)


# 沙箱**釘死**的受管平台欄。回填路徑在設計上只寫「本機平台那一欄」，而本檔的窗口鎖
# 驗的是量測窗口的 TOCTOU，與「本機是哪個平台」無關。R67 round 3 之前沙箱不釘平台，
# 於是同一組鎖在三個 host 上是三種行為：macOS 綠、Linux（無欄）rc=2 全紅、Windows 則
# 會寫進 win32 欄而讓寫死 `"darwin"` 的斷言假紅。釘死之後三個 host 跑的是同一件事。
# 「無欄平台會怎樣」不因此失去覆蓋——由
# `test_unmanaged_platform_refuses_to_backfill_instead_of_guessing_a_column` 單獨看守。
_SANDBOX_PLATFORM = "darwin"


@contextmanager
def _slow_window_sandbox(mutate_during_window: bool):
    """把 `--write --with-slow` 整條路徑搬進 tmp 沙箱，並可選擇在**量測窗口內**改動測試樹。

    為何要沙箱：這條路徑會**寫 ONBOARDING.md** 並實跑分鐘級量測。以 tmp 目錄替換
    `_REPO_ROOT`／`_ONBOARDING`、以確定性 stub 替換兩支慢量測器之後，同一條生產程式碼
    可以在毫秒內被完整驅動，且真實 repo 的檔案全程唯讀。

    stub 的計數刻意**定義為「該棵樹當下的 `.py` 檔數」**：於是「樹變了 ⇒ 計數變了」在
    測試裡是**可驗證的因果**，而不是靠測試自己宣告。`mutate_during_window=True` 時，
    在 ci-gate 量完之後、AutoClaude pytest 量測期間新增一支測試檔——這正是本缺陷的
    活體形態（並行的修復包在分鐘級窗口內寫測試檔）。

    平台亦是沙箱的一部分（R67 round 3）：`current_platform_key()` 被釘成
    `_SANDBOX_PLATFORM`，理由見該常數上方。帶參數呼叫仍走真實實作，才不會連帶蓋掉
    `current_platform_key("linux")` 這種顯式查詢的語意。

    yield 出 `(sandbox_path, trees, state)`；`state["mutated"]` 供測試反查注入是否真的
    發生（避免 fixture 空轉造成「測試永遠綠」）。
    """
    import shutil
    import tempfile

    saved = {
        name: getattr(SYNC, name)
        for name in (
            "_REPO_ROOT", "_ONBOARDING", "_run_cigate", "_run_autoclaude_pytest",
            "measure_all", "_docker_state", "pg_extras_state", "current_platform_key",
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        sandbox = Path(tmp)
        trees = {}
        for name, rel, _pat in SYNC._FINGERPRINT_TREES:
            d = sandbox / rel
            d.mkdir(parents=True)
            for i in range(3):
                (d / f"test_{name}_{i}.py").write_bytes(b"def test_x():\n    pass\n")
            trees[name] = d
        shutil.copyfile(_ONBOARDING, sandbox / "ONBOARDING.md")
        text0 = (sandbox / "ONBOARDING.md").read_text(encoding="utf-8-sig")
        state: dict[str, object] = {"mutated": False}

        def _count(name: str) -> int:
            return len(list(trees[name].glob("**/*.py")))

        def fake_cigate() -> dict[str, int]:
            return {f"cigate_{k}": _count(k) for k in ("v001", "v030", "scripts")}

        def fake_pytest() -> dict[str, int]:
            if mutate_during_window:
                (trees["scripts"] / "test_injected_by_parallel_package.py").write_bytes(
                    b"def test_new():\n    pass\n"
                )
                state["mutated"] = True
            return {"passed": _count("autoclaude"), "skipped": 0}

        try:
            SYNC._REPO_ROOT = sandbox
            SYNC._ONBOARDING = sandbox / "ONBOARDING.md"
            SYNC._run_cigate = fake_cigate
            SYNC._run_autoclaude_pytest = fake_pytest
            SYNC.measure_all = lambda: {
                s.anchor: SYNC.parse_documented(SYNC.anchored_line(text0, s.anchor), s)
                for s in SYNC._SPECS
            }
            SYNC._docker_state = lambda: "down"
            SYNC.pg_extras_state = lambda: "absent"
            SYNC.current_platform_key = (
                lambda raw=None: _SANDBOX_PLATFORM
                if raw is None
                else saved["current_platform_key"](raw)
            )
            yield sandbox, trees, state
        finally:
            for name, value in saved.items():
                setattr(SYNC, name, value)


class TestR67SlowMeasurementWindowIsFingerprintBracketed(unittest.TestCase):
    """R67 收尾 Scan-H（DEF-101-677）：`--write --with-slow` 的量測窗口 TOCTOU。

    WHY 這道鎖必須存在（Rule 9：測 intent 不只測 behavior）：
      表② 之所以敢在沒有 live 鎖的情況下被信任，**全部理由**就是
      `snapshot-fingerprints-<平台>` 錨那一句「這一欄的數字是在**哪一棵測試樹**上量的」。
      而回填路徑原本是「先跑分鐘級慢量測、**跑完之後**才取指紋」⇒ 樹若在窗口內被改動，
      錨記下的是一棵**從未被量測過**的樹，四格計數卻留在改動前的樹上。
      事後 `--check-snapshot` 量到的 live 指紋與錨相符 ⇒ ✅ rc=0，而計數已 stale。

      這不是「指紋這種觸發器本來就會漏」那一類（那是已揭露的邊界：docker 狀態、
      生產碼改 parametrize 都能改變計數而指紋不動）。這一類是**回填路徑親手把觸發器
      拆掉**：樹確實變動了——那正是本觸發器唯一認得的事件——卻被寫進錨當成基準。
      既有契約已是「指紋一變即判 presumed stale」，唯獨回填路徑替自己免除了這一條；
      修法是取消那個豁免，**不是**提高嚴格度。

    活體證據（R67 收尾 Scan-H）：BASELINE 包寫入的 macOS `scripts/tests` 格是 253、
    收尾包在同一棵樹量到 259，而 `snapshot-fingerprints-darwin` 的 `scripts=` 前後
    **完全相同** ⇒ 那條錨當時正在為一組對不上的計數背書。
    """

    def test_mutation_inside_window_fails_loud_and_writes_nothing(self) -> None:
        """窗口內樹變動 ⇒ 拋 `BaselineToolError`，且 ONBOARDING **一個 byte 都沒被改**。

        「未寫入」與「有拋例外」要一起斷言：只擋不寫、卻靜默 rc=0，等於把「這次量測作廢」
        這件事藏起來；只拋例外卻已寫了半份文件，則留下一份跨兩棵樹的紀錄。
        """
        with _slow_window_sandbox(mutate_during_window=True) as (sandbox, _trees, state):
            doc = sandbox / "ONBOARDING.md"
            before_bytes = doc.read_bytes()
            with self.assertRaises(SYNC.BaselineToolError) as ctx:
                SYNC.main(["--write", "--with-slow"])
            self.assertTrue(state["mutated"], "注入未實際發生 ⇒ 本測試空轉，不具鑑別力")
            message = str(ctx.exception)
            self.assertIn("量測期間測試樹被改動", message)
            self.assertIn("scripts", message, "訊息未指出是哪一棵樹變動 ⇒ 使用者無從下手")
            self.assertIn("--write --with-slow", message, "訊息缺少『該怎麼辦』的確切指令")
            self.assertEqual(
                doc.read_bytes(), before_bytes,
                "量測作廢卻仍寫了檔 ⇒ 留下一份跨兩棵樹的紀錄，正是本鎖要擋的東西",
            )

    def test_guard_refuses_to_produce_the_false_green_artifact(self) -> None:
        """先證明「假綠」確實可構造（fixture 有牙），再證明生產路徑拒絕產出它。

        兩半缺一不可：只斷言「生產路徑會拋例外」的話，若哪天 fixture 漂移成「窗口內
        其實沒改到樹」，測試會靜默轉成永遠綠——那正是本輪一直在治的病。
        """
        with _slow_window_sandbox(mutate_during_window=True) as (sandbox, trees, _state):
            text = (sandbox / "ONBOARDING.md").read_text(encoding="utf-8-sig")
            # ── 前半：手工複製「壞形態」的產物（計數取自改動前的樹、指紋取自改動後的樹）──
            counts_before = len(list(trees["scripts"].glob("**/*.py")))
            (trees["scripts"] / "test_injected.py").write_bytes(b"def test_n():\n    pass\n")
            fp_after = SYNC.measure_fingerprints()
            bad = SYNC.render_fingerprints(
                SYNC.render_slow(
                    text,
                    {
                        "autoclaude-pytest-snapshot:": {"passed": 1, "skipped": 0},
                        "cigate-v001-snapshot:": {"passed": 1},
                        "cigate-v030-snapshot:": {"passed": 1},
                        "cigate-scripts-snapshot:": {"passed": counts_before},
                    },
                    _SANDBOX_PLATFORM,
                ),
                fp_after,
                _SANDBOX_PLATFORM,
                SYNC.measure_provenance(),
            )
            documented = SYNC.slow_documented(bad, _SANDBOX_PLATFORM)[
                "cigate-scripts-snapshot:"
            ]["passed"]
            self.assertNotEqual(
                documented, len(list(trees["scripts"].glob("**/*.py"))),
                "計數並未 stale ⇒ 本測試的假綠構造失效",
            )
            self.assertEqual(
                SYNC.check_snapshot(bad, _SANDBOX_PLATFORM), [],
                "假綠構造未成立（指紋沒對上）⇒ 後半的斷言不具意義",
            )
            # ── 後半：生產路徑**不得**產出上面那份東西 ──
            with self.assertRaises(SYNC.BaselineToolError):
                SYNC.measure_slow_on_stable_tree()

    def test_stable_window_records_the_tree_the_counts_were_measured_on(self) -> None:
        """正常單人作業零影響：樹沒變 ⇒ 照常回填，且錨記的就是計數所依據的那棵樹。

        這一半同樣不可省——修法若把正常情境也擋掉（例如誤把每次都判成變動），本鎖
        就從「防假綠」變成「誰都回填不了」，那比缺陷本身更糟。
        """
        with _slow_window_sandbox(mutate_during_window=False) as (sandbox, trees, _state):
            fp_expected = SYNC.measure_fingerprints()
            slow, fp = SYNC.measure_slow_on_stable_tree()
            self.assertEqual(fp, fp_expected, "回傳的指紋不是計數所依據的那棵樹")
            self.assertEqual(
                slow["cigate-scripts-snapshot:"]["passed"],
                len(list(trees["scripts"].glob("**/*.py"))),
            )
            self.assertEqual(SYNC.main(["--write", "--with-slow"]), 0)
            written = (sandbox / "ONBOARDING.md").read_text(encoding="utf-8-sig")
            self.assertEqual(SYNC.parse_fingerprints(written, _SANDBOX_PLATFORM), fp_expected)
            self.assertEqual(SYNC.main(["--check-snapshot"]), 0, "回填完當場就紅 ⇒ 修法過嚴")

    def test_unmanaged_platform_refuses_to_backfill_instead_of_guessing_a_column(self) -> None:
        """無欄平台（Linux CI runner）跑回填 ⇒ rc=2、點名受管欄、且**一個 byte 都不寫**。

        WHY 這支要單獨存在（R67 round 3）：同輪把沙箱的平台**釘死**在受管欄上，才能讓
        窗口鎖在三個 host 上跑同一件事；那個釘死同時把「無欄平台會怎樣」擋在射程外。
        而那條分支正是 R67-D1 的最後一道——`current_platform_key()` 回 None 時若「猜一欄
        來寫」，本機數字就會被寫進標示別平台實測的格子，表格還是滿的、rc 還是 0，但它
        從此在說謊。故把沙箱移除的那半邊當場補回來，而不是讓它變成沒人看守的分支。
        """
        with _slow_window_sandbox(mutate_during_window=False) as (sandbox, _trees, _state):
            doc = sandbox / "ONBOARDING.md"
            before_bytes = doc.read_bytes()
            SYNC.current_platform_key = lambda raw=None: None  # ← 沙箱結束時由 fixture 還原
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = SYNC.main(["--write", "--with-slow"])
            self.assertEqual(rc, 2, f"無欄平台仍回填（rc={rc}）⇒ 數字會被寫進別平台的格子")
            self.assertIn("沒有對應欄", err.getvalue(), err.getvalue())
            for key in SYNC._PLATFORM_COLUMN_LABELS:
                self.assertIn(
                    key, err.getvalue(),
                    "訊息未列出受管平台欄 ⇒ 使用者無從得知『那該在哪台機器上跑』",
                )
            self.assertIn(
                "_PLATFORM_COLUMN_LABELS", err.getvalue(),
                "訊息未指路『要納管新平台該改哪裡』",
            )
            self.assertEqual(
                doc.read_bytes(), before_bytes, "拒絕回填卻仍動了 ONBOARDING.md",
            )

    def test_bracketing_cost_is_one_extra_fingerprint_not_one_extra_measurement(self) -> None:
        """代價劃界：夾住窗口只多**一次毫秒級指紋**，不得多跑一次分鐘級量測。

        WHY 要釘住：本鎖能被接受的前提就是「正常情境不平白多付分鐘級開銷」。若哪天有人
        把它改成「量兩次再比對計數」，這條會轉紅。
        """
        with _slow_window_sandbox(mutate_during_window=False) as (_sandbox, _trees, _state):
            calls = {"slow": 0, "fp": 0}
            real_slow, real_fp = SYNC.measure_slow, SYNC.measure_fingerprints

            def counting_slow():
                calls["slow"] += 1
                return real_slow()

            def counting_fp():
                calls["fp"] += 1
                return real_fp()

            SYNC.measure_slow, SYNC.measure_fingerprints = counting_slow, counting_fp
            try:
                SYNC.measure_slow_on_stable_tree()
            finally:
                SYNC.measure_slow, SYNC.measure_fingerprints = real_slow, real_fp
        self.assertEqual(calls["slow"], 1, "慢量測被跑了不只一次 ⇒ 代價超出設計")
        self.assertEqual(calls["fp"], 2, "夾住窗口需且僅需前後各一次指紋")

    def test_read_only_paths_measure_live_fingerprints_exactly_once(self) -> None:
        """同型收斂：單次 CLI 呼叫內，live 指紋只准量一次（判決與取證同一份）。

        原版 `--check-snapshot` 判決後又重量一次才印 ✅ 那一行、`--json` 更量了 3 次 ⇒
        「印出來的證據」與「判決所依據的」可能是不同時點的樹。這與主缺陷同型（同一個量
        在不同時點被量兩次），且違反 Nightly 取證紀律「取證載具必須就是判決依據」。
        """
        with _slow_window_sandbox(mutate_during_window=False) as (_sandbox, _trees, _state):
            self.assertEqual(SYNC.main(["--write", "--with-slow"]), 0)
            real_fp = SYNC.measure_fingerprints
            for mode, expected_rc in (("--check-snapshot", 0), ("--json", 0)):
                calls = {"n": 0}

                def counting_fp(_c=calls):
                    _c["n"] += 1
                    return real_fp()

                SYNC.measure_fingerprints = counting_fp
                try:
                    import contextlib
                    import io

                    with contextlib.redirect_stdout(io.StringIO()):
                        rc = SYNC.main([mode])
                finally:
                    SYNC.measure_fingerprints = real_fp
                self.assertEqual(rc, expected_rc, f"{mode} rc 非預期，計數斷言失去意義")
                self.assertEqual(
                    calls["n"], 1,
                    f"{mode} 在單次呼叫內量了 {calls['n']} 次 live 指紋（預期 1）",
                )


# ---------------------------------------------------------------- R69：ADR 內量測 token ↔ 現查
# 🔴 為何非得有這一條（R69 Architect 實測命中，同型第三次復發）：
#   R68 把「閘門全綠」寫進 commit message，事後複現不出來；R69 的 `ADR-XPLAT-003` 把同一個
#   毛病**搬進了 ADR**——該 ADR 表頭自陳「記錄的是已合入工作樹並實測綠的異動」、§3 又逐字
#   引述 `ADR-XPLAT-002` §1.1「以行數下降為成果的宣稱必須前後各量一次」並宣稱「本節照辦」，
#   而它寫下的 `total=20415`／`3923 passed` 在交付樹上一個都複現不出來（實測 20436／3929）。
#   受害者不是潔癖：ADR 是**寫給未來每一輪照抄重跑**的文件，數字錯了，照它驗證的人會把
#   正常狀態讀成退化，或反過來把凍結讀成已解除（本例正是後者：「餘裕 23 行」讓讀者以為
#   生產碼可以再寫，實際餘裕 2 行、凍結完全沒解除）。
#   同族前科：DEF-101-289／DEF-101-515（ONBOARDING §7）、`ADR-XPLAT-002` §4.3.1 的成長率
#   常數（R67 round 4 拔除）、`run_root_unittests.MIN_TESTS` 一輪三釘。**共同形態＝
#   「文件寫死機器當場可以算出來的數字」**，故本鎖與本檔正職同源、同檔、共用取值來源。
#
# 判準（誠實劃界）：
#   ① `total=／baseline=／cap=` ⇒ 必須**逐字等於**現查值。取值來源＝本檔正職已在用的
#      `SYNC.measure_loc()`（`check_loc_budget.py --json`）＋ `AutoClaude/.loc_baseline`
#      （`baseline=` 的 SSOT）。同 repo 對同一數字只准一種說法。
#      🔴 **`violations=` 刻意不納管（誠實劃界，非疏漏）**：那三個欄位是 ADR 主體本身的
#      量（`autoclaude/` 的行數與上限），而 `violations` 是**整棵樹當下的裁決**，由最後一個
#      動到任何受管檔的人決定——把它納管，等於任何一支無關檔案破自己的預算就讓全部 ADR 變紅
#      （R69 實測即命中：`tools/dev_start.py` 破 special 2000 上限，與這兩份 ADR 毫無關係）。
#      故 ADR 一律**不登載**這個欄位，引用工具輸出時只引與自己射程相關的三欄。
#   ② `<3 位數以上> passed` ⇒ **一律違規**。理由不是它會 stale，是根層閘門**取不到**現場值
#      （跑一次 AutoClaude 全套要 80 秒以上，放進根層 unittest 是拿假鎖換慢），而本 repo 早已
#      為它指定唯一的家：`ONBOARDING.md §7`＋`tools/check_pytest_baseline_sites.py`。ADR 要引
#      這個數字，就指向 SSOT，不要在 ADR 裡再開一個家。三位數起跳＝刻意放行 `1 passed`／
#      `9 passed` 這類「注入後重跑單檔」的紅綠自證輸出，那是證據不是基線。
#   ③ 豁免＝同一行寫 `adr-measurement-historical: <理由>`（**理由必填**，空理由不具豁免力，
#      比照本 repo `baseline-ok` 與 `encoding-ok` 兩族豁免的紀律）。射程只到「有輪次歸屬的
#      時代快照」——ADR 的歷史訂正段落逐字保全是本 repo 明文紀律，不得因本鎖而被改寫。
#   ④ **本鎖自己也是量測載具，載具必須被驗證**，三條 fail-open 全部封死：
#      (a) ADR 目錄不存在／零 `ADR-*.md` ⇒ 違規（掃描面崩塌，不得靜默零命中假綠）；
#      (b) 取值來源給不出 total／baseline／cap 三個整數 ⇒ 違規（工具壞掉 ≠ ADR stale，分開回報）；
#      (c) 全掃描面**零筆** LOC token（`total`／`baseline`／`cap` 形態，含已掛豁免者）⇒ 違規。
#          這一條治的是「把數字整段刪掉本鎖就空轉」，與 `check_pytest_baseline_sites.py` 的
#          SSOT anchor 自檢同形。
#          🔴 **R71 錨點改指（本條原文自己預告過的那件事真的發生了）**：原文寫「改為指向
#          live 來源而不寫死數字本身是更好的作法，但它會讓本鎖失去唯一的活體比對——真要
#          那樣改，請在同一個 commit 內把本條錨點自檢改指新的活體站點」。R71 正是那一輪：
#          `ADR-XPLAT-003` 的四處 `total=／cap=` 已全數改為時代快照（掛豁免）或改指 SSOT，
#          `ADR-XPLAT-002` 的兩處本來就掛著豁免 ⇒ 非豁免受管 token 歸零。
#          依原文指示同 commit 完成兩件事：
#            ① 本條的計數改為「**掃描面上還看得見 LOC token 的形態**」（豁免者也計入）——
#               它守的是「regex 與掃描面還活著」，這一層仍然有效且仍會在整段刪除時翻紅；
#            ② **活體比對改指 `ONBOARDING.md` §7 表① 的 `loc-baseline-live:` 那一格**，
#               由本檔 `TestR69AdrMeasurementTokensAreLive::
#               test_live_loc_ssot_station_carries_the_live_comparison` 直接對現查值比對。
#               該格本就是本 repo 指定的唯一 live 家、且有 `--write` 一鍵回填，
#               ADR 不必也不該再開第二個家（理由與 ADR §8(b) 對 pytest 計數一字不差）。
_ADR_DIR = _REPO_ROOT / "docs" / "04_planning" / "ADR"
_ADR_WAIVER = "adr-measurement-historical:"
_ADR_LOC_TOKEN_RE = re.compile(r"\b(total|baseline|cap|violations)=(\d+)")
# 三位數起跳；容許 markdown 粗體與全形空白夾在數字與 `passed` 之間（ADR 內實際寫法）。
_ADR_PYTEST_TOKEN_RE = re.compile(r"(?<![\d,.])(\d{1,3}(?:,\d{3})+|\d{3,})[\s*　]*passed", re.I)


def read_adr_docs(adr_dir: Path = _ADR_DIR) -> list[tuple[str, str]]:
    """ADR 掃描面 `(檔名, 內容)`；目錄缺席或零檔一律 fail-loud（判準 ④(a)）。"""
    if not adr_dir.is_dir():
        raise AssertionError(
            f"ADR 目錄不存在：{adr_dir} — 掃描面崩塌（搬家／改名？），本鎖拒絕靜默通過"
        )
    docs = sorted(adr_dir.glob("ADR-*.md"))
    if not docs:
        raise AssertionError(
            f"{adr_dir} 底下零個 `ADR-*.md` — 掃描面崩塌，本鎖拒絕靜默通過"
        )
    return [(p.name, p.read_text(encoding="utf-8-sig")) for p in docs]


def measure_adr_loc_live() -> dict[str, int]:
    """ADR 受管 LOC token 的現查值：`total／baseline／cap`。

    取值來源刻意與本檔正職同一支工具（`SYNC._LOC_TOOL` ＝ `check_loc_budget.py --json`），
    **不另外去讀 `AutoClaude/.loc_baseline`**——那會讓根層測試多消費一個 repo 檔，得同步
    兩支 compat CI 的 `paths:`（`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`
    落地當場即紅並點名）；而 `--json` 本來就把 `baseline` 一起印出來，多開一個消費面零收益。
    工具印不出可解析 JSON ⇒ 拋 `BaselineToolError`，與「ADR stale」分開回報（判準 ④(b)）。
    """
    proc = subprocess.run(
        [sys.executable, str(SYNC._LOC_TOOL), "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(_REPO_ROOT),
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SYNC.BaselineToolError(
            f"{SYNC._LOC_TOOL} --json 印不出可解析 JSON（rc={proc.returncode}）— "
            f"這是**取值來源壞掉**，不是 ADR stale\nstdout: {proc.stdout[-400:]}"
        ) from exc
    missing = [k for k in ("total", "baseline", "cap") if k not in payload]
    if missing:
        raise SYNC.BaselineToolError(f"取值來源缺 key {missing} — 本鎖無從比對")
    return {k: int(payload[k]) for k in ("total", "baseline", "cap")}


def _adr_waiver_problem(label: str, lineno: int, line: str) -> str | None:
    """已掛豁免者仍要求標記後面有理由；無理由的豁免就是後門（判準 ③）。"""
    if _ADR_WAIVER not in line:
        return None
    reason = line.split(_ADR_WAIVER, 1)[1].strip().removesuffix("-->").strip()
    if reason:
        return ""
    return (
        f"{label}:{lineno}：豁免標記 `{_ADR_WAIVER}` 後面沒有理由 — "
        f"無理由的豁免就是後門，不是豁免"
    )


def adr_measurement_problems(
    docs: list[tuple[str, str]], live: dict[str, int]
) -> list[str]:
    """純函式：ADR 內量測 token 的違規清單（空＝通過）。判準見上方段落。"""
    problems: list[str] = []
    inspected_loc_tokens = 0
    for label, text in docs:
        for lineno, line in enumerate(text.splitlines(), 1):
            loc_hits = _ADR_LOC_TOKEN_RE.findall(line)
            py_hits = _ADR_PYTEST_TOKEN_RE.findall(line)
            if not loc_hits and not py_hits:
                continue
            # 判準 ④(c) 的錨點（R71 改指）：只要掃描面上還看得見 total／baseline／cap
            # 形態的 token（**不論是否掛豁免**），就證明 regex 與掃描面都還活著。活體
            # 比對本身已移至 ONBOARDING §7（見下方 `_LIVE_LOC_ANCHOR` 那支測試）。
            inspected_loc_tokens += sum(1 for key, _ in loc_hits if key != "violations")
            waived = _adr_waiver_problem(label, lineno, line)
            if waived:  # 有標記但沒理由
                problems.append(waived)
                continue
            if waived == "":  # 有標記且有理由 ⇒ 時代快照，放行
                continue
            for key, value in loc_hits:
                if key == "violations":
                    problems.append(
                        f"{label}:{lineno}：`violations={value}` — ADR 不得登載這個欄位。"
                        f"它是**整棵樹當下的裁決**、由最後一個動到任何受管檔的人決定，"
                        f"與本 ADR 的射程無關（登載即等於把無關檔案的預算破線變成 ADR 的紅燈）。"
                        f"引用工具輸出時只引 total／baseline／cap 三欄；"
                        f"若這是有輪次歸屬的時代快照，改掛 `{_ADR_WAIVER} <理由>`。"
                        f"\n  行文：{line.strip()[:160]}"
                    )
                    continue
                if int(value) != live[key]:
                    problems.append(
                        f"{label}:{lineno}：`{key}={value}` 與現查值 {live[key]} 不符 — "
                        f"ADR 是寫給未來照抄重跑的文件，數字錯了會讓讀者把凍結讀成已解除。"
                        f"重跑 `python AutoClaude/tools/check_loc_budget.py` 取當下值填回；"
                        f"若這是有輪次歸屬的時代快照，改掛 `{_ADR_WAIVER} <理由>`。"
                        f"\n  行文：{line.strip()[:160]}"
                    )
            for value in py_hits:
                problems.append(
                    f"{label}:{lineno}：`{value} passed` — ADR 不得自建 pytest 基線的第二個家。"
                    f"唯一 SSOT ＝ `ONBOARDING.md §7`（守門者＝tools/check_pytest_baseline_sites.py）；"
                    f"根層閘門取不到 AutoClaude 全套的現場值，寫死即無人看守。請改為指向 SSOT，"
                    f"或若這是有輪次歸屬的時代快照，改掛 `{_ADR_WAIVER} <理由>`。"
                    f"\n  行文：{line.strip()[:160]}"
                )
    if inspected_loc_tokens == 0:
        problems.append(
            f"整個 ADR 掃描面（{len(docs)} 份）連一筆 `total=／baseline=／cap=` 形態的 token "
            f"都掃不到（豁免者也算） — 這代表掃描面崩塌或 regex 失效，本鎖已空轉。"
            f"注意：活體比對自 R71 起已改指 `ONBOARDING.md` §7 的 `loc-baseline-live:` 格"
            f"（見 test_live_loc_ssot_station_carries_the_live_comparison），本條只負責"
            f"「掃描面還活著」這一層。"
        )
    return problems


class TestR69AdrMeasurementTokensAreLive(unittest.TestCase):
    """真實 ADR × 真實取值來源的現查一致性（判準見上方段落）。"""

    def test_real_adrs_carry_no_unreproducible_measurement_token(self) -> None:
        problems = adr_measurement_problems(read_adr_docs(), measure_adr_loc_live())
        self.assertEqual(
            problems,
            [],
            "docs/04_planning/ADR/ 內有複現不出來的量測 token：\n"
            + "\n".join(f"  - {p}" for p in problems),
        )

    def test_scan_surface_did_not_collapse(self) -> None:
        """掃描面自檢：目錄在、檔案讀得到、且確實掃到 ADR-XPLAT-003（本次事故的原點）。"""
        names = {label for label, _ in read_adr_docs()}
        self.assertIn(
            "ADR-XPLAT-003-autoclaude-platform-capability-layer.md", names,
            f"掃描面裡沒有 ADR-XPLAT-003（現有：{sorted(names)}）— 檔案改名時請同步本鎖",
        )

    def test_live_loc_ssot_station_carries_the_live_comparison(self) -> None:
        """🔴 判準 ④(c) 的**新錨點**（R71 改指）：ADR 交出去的活體比對落在這一格。

        WHY 這支不是 `test_documented_live_cells_match_measured_values` 的重複：
        那一支守的是「§7 表①**整張表**每一格都新鮮」；本支守的是「ADR 之所以可以不寫
        `total`／`cap`，是**因為**這一格在替它扛」。兩者射程不同、失敗訊息也要不同——
        錨點被刪／被改名時，讀到的人必須當場知道「ADR 那道鎖現在空轉了」，而不是只看到
        一則泛用的表格 stale 訊息。`anchored_line` 對 0 行或 ≥2 行本身就 fail-loud。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        line = SYNC.anchored_line(text, "loc-baseline-live:")
        live = measure_adr_loc_live()
        for key in ("total", "cap"):
            self.assertIn(
                f"{key}={live[key]}", line,
                f"ONBOARDING.md §7 的 `loc-baseline-live:` 格沒有帶著現查的 `{key}="
                f"{live[key]}` — 這一格自 R71 起是 `total`／`cap` 在本 repo 的**唯一** live 家"
                f"（ADR 已依 §8(b) 全面改掛時代快照／改指本格）。本格一 stale，整條"
                f"「ADR 不寫死數字」的收斂就失去支撐點。\n"
                f"  一鍵回填：python tools/sync_onboarding_baselines.py --write\n"
                f"  受鎖行實際內容：{line.strip()[:200]}",
            )

    def test_live_source_is_sane(self) -> None:
        """取值來源自檢（判準 ④(b)）：三個 key 都拿得到且為正整數；`violations` 不得混入。"""
        live = measure_adr_loc_live()
        for key in ("total", "baseline", "cap"):
            self.assertGreater(live[key], 0, f"現查值 {key}={live[key]} 不合理 — 取值來源壞掉")
        self.assertNotIn(
            "violations", live,
            "`violations` 是整棵樹的裁決、不是本 ADR 的量 — 混進取值來源即等於把無關檔案的"
            "預算破線變成 ADR 的紅燈（判準 ① 的劃界）",
        )

    # ── 以下以合成文本自證判準紅綠（不落 repo 樹內、不碰真實 ADR）──
    _LIVE = {"total": 20436, "baseline": 17032, "cap": 20438}

    def _run(self, body: str, live: dict[str, int] | None = None) -> list[str]:
        return adr_measurement_problems([("FAKE.md", body)], live or self._LIVE)

    def test_matching_loc_token_passes(self) -> None:
        self.assertEqual(self._run("`total=20436 baseline=17032 cap=20438`\n"), [])

    def test_stale_loc_token_is_caught(self) -> None:
        problems = self._run("total=20415 baseline=17032 cap=20438\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("total=20415", problems[0])
        self.assertIn("20436", problems[0])

    def test_violations_field_is_refused_even_when_it_matches(self) -> None:
        """`violations=` 逐字等於現查也照樣紅 — 它根本不該住在 ADR 裡（判準 ① 劃界）。"""
        problems = self._run("total=20436 violations=0\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("不得登載", problems[0])

    def test_hardcoded_pytest_baseline_is_caught(self) -> None:
        problems = self._run("total=20436\n3923 passed, 146 skipped\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("3923 passed", problems[0])

    def test_single_digit_pytest_evidence_is_not_flagged(self) -> None:
        """`1 passed`／`9 passed` 是注入後重跑單檔的紅綠自證，不是基線，刻意放行。"""
        self.assertEqual(self._run("total=20436；還原後 `1 passed`（GREEN）、`9 passed`\n"), [])

    def test_waiver_with_reason_passes_and_without_reason_fails(self) -> None:
        ok = self._run("total=20436\n| total=20361 <!-- adr-measurement-historical: R60 快照 -->\n")
        self.assertEqual(ok, [])
        bad = self._run("total=20436\n| total=20361 <!-- adr-measurement-historical: -->\n")
        self.assertEqual(len(bad), 1, bad)
        self.assertIn("沒有理由", bad[0])

    def test_waiver_is_line_scoped_not_file_scoped(self) -> None:
        """豁免逐行判定：上一行掛了標記，不得放行下一行（單行巨欄的教訓，§9.1 邊界 (b)）。"""
        problems = self._run(
            "| total=20361 <!-- adr-measurement-historical: R60 快照 -->\n"
            "改後 total=20415\n"
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("total=20415", problems[0])

    def test_empty_corpus_is_a_violation_not_a_pass(self) -> None:
        """判準 ④(c)：掃描面上一筆 LOC token 都看不到 ⇒ 本鎖空轉，必須紅。"""
        problems = self._run("本節不再登載量測常數，一律現查。\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("空轉", problems[0])

    def test_waived_only_corpus_does_not_trip_the_idle_anchor(self) -> None:
        """R71 錨點改指後的新語意：全部掛豁免 ⇒ 通過（掃描面仍活著）。

        WHY 這是**刻意**的行為改變，不是把鎖放鬆：ADR 是決策時點的紀錄，它裡面的量測
        本來就該是「有輪次歸屬的時代快照」；活體比對已改由
        `test_live_loc_ssot_station_carries_the_live_comparison` 對 ONBOARDING §7 執行。
        改前這個語料會因「零筆**非豁免**受管 token」而紅，等於逼 ADR 永遠留一個活數字
        在正文——那正是 R71 讓根層閘門紅 4 支的成因。
        """
        body = (
            "| total=20361 <!-- adr-measurement-historical: R60 快照 -->\n"
            "| cap=20438 <!-- adr-measurement-historical: R60 快照 -->\n"
        )
        self.assertEqual(self._run(body), [])

    def test_idle_anchor_still_fires_when_every_number_is_deleted(self) -> None:
        """反向：連豁免快照都被刪光 ⇒ 掃描面崩塌，仍須紅（本條沒有被放鬆）。"""
        problems = self._run("本 ADR 完全不提任何量測。\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("掃描面崩塌", problems[0])

    def test_missing_adr_dir_fails_loud(self) -> None:
        """判準 ④(a)：掃描面崩塌不得靜默通過。"""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AssertionError):
                read_adr_docs(Path(tmp) / "nope")
            with self.assertRaises(AssertionError):
                read_adr_docs(Path(tmp))


# 本檔所有鎖都必須在這些 `sys.platform` 值下有**相同**結果。刻意含 `linux`（無對應欄
# ＝ root-infra-ci 的 ubuntu runner）與兩個受管欄，且**不含**「本機是哪個」這個資訊。
_NEUTRALITY_PLATFORMS: tuple[str, ...] = ("darwin", "linux", "win32")


def _flatten_suite(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    out: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            out.extend(_flatten_suite(item))
        else:
            out.append(item)
    return out


class TestR67R3ThisFileMakesNoUnstatedPlatformAssumption(unittest.TestCase):
    """🔴 R67 round 3 回歸鎖：本檔的每一支鎖，在**任何**平台上都必須得出同一個結果。

    WHY（缺陷類別，不是單一缺陷）：R67 把 `sync_onboarding_baselines.py` 平台化之後，
    本檔多支鎖改用 `current_platform_key()`／`main(["--write", "--with-slow"])` 驅動，
    等於各自悄悄加上一條**未言明的前提**——「本機必須是 §7 表② 有對應欄的平台」。
    在作者的 macOS 上三個月都是綠的；直到 root-infra-ci 的相依缺口被補、這些鎖第一次
    真的在 ubuntu runner 上執行，7 支同時紅。而那 7 個紅燈說的都不是「受測物壞了」，
    是「測試自己的前提在這台機器上不成立」——**假紅比假綠更快讓人學會忽略紅燈**。

    這一類不可能靠人審抓：它的症狀只在「沒人跑過的平台」上出現，而「沒人跑過」正是它
    能活下來的原因（同 DEF-101-343~345「Windows 專屬測試連續 5+ 輪全 APPROVE 卻從未在
    Windows 跑過」的形態，只是方向換成 Linux）。故本鎖把「換平台」變成**本機當場可跑**
    的事：以模擬的 `sys.platform` 重跑本檔全部鎖，任一平台下的失敗即當場點名。

    邊界（誠實劃界）：
      - 只注入 `sys.platform`。`os.name`、真實檔案系統、路徑分隔符、是否有 pwsh 等
        **不在**模擬範圍內 ⇒ 本鎖綠**不等於**「本檔在真 Linux/Windows 上必綠」，只等於
        「本檔不因 `sys.platform` 而異」。對受測物而言這已是全部——
        `sync_onboarding_baselines.py` 的平台輸入只有 `sys.platform`
        （`platform_mod.*` 僅供 provenance 的 host 字串，不進任何判準）。
      - 代價＝本檔跑 `len(_NEUTRALITY_PLATFORMS)` 倍。可接受的理由：本檔是純字串/雜湊
        運算，實測全檔僅數秒；而它換回來的是「跨平台缺陷在**動工的那台機器上**就會紅」。
    """

    def _sibling_suite(self) -> unittest.TestSuite:
        """本模組除本類別以外的全部測試（排除自己＝防無限遞迴）。"""
        loaded = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
        suite = unittest.TestSuite()
        for test in _flatten_suite(loaded):
            if not isinstance(test, TestR67R3ThisFileMakesNoUnstatedPlatformAssumption):
                suite.addTest(test)
        return suite

    def test_every_lock_in_this_file_holds_under_every_simulated_platform(self) -> None:
        probe = self._sibling_suite()
        self.assertGreater(
            probe.countTestCases(), 50,
            "子套件幾乎是空的 ⇒ 本鎖空轉（loadTestsFromModule 漂移），不具鑑別力",
        )
        original = sys.platform
        failures: dict[str, list[str]] = {}
        try:
            for fake in _NEUTRALITY_PLATFORMS:
                sys.platform = fake
                sink = io.StringIO()
                with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                    result = unittest.TextTestRunner(stream=sink, verbosity=0).run(
                        self._sibling_suite()
                    )
                bad = [
                    f"{kind} {test.id()} :: {trace.strip().splitlines()[-1]}"
                    for kind, bucket in (
                        ("FAIL", result.failures), ("ERROR", result.errors)
                    )
                    for test, trace in bucket
                ]
                if bad:
                    failures[fake] = bad
        finally:
            sys.platform = original
        self.assertEqual(
            failures, {},
            "本檔有鎖的結果隨 sys.platform 改變 ⇒ 它對『本機是哪個平台』做了未言明的"
            "前提假設。修法不是加 skip（那等於讓該平台永遠沒有覆蓋），而是把該鎖改成"
            "**吃平台當參數**——它驗的判準本來就是逐欄的純函式。",
        )


#: 逐字取自 `AutoClaude/logs/nightly_latest.log` 第 488~494 行（2026-08-02 那一輪的真實
#: 收尾段，Windows 11 真機 Task Scheduler `AutoClaude_Nightly` 產出）。整支 log 實測 494 行，
#: 彙總行落在**第 491 行**——首版探針只讀前 3 行，這就是它結構上永遠打不中的那 488 行差距。
#:
#: 🔴 provenance 訂正（本批）：上一批的同一句註解宣稱「488~494 行」，實際**靜默丟掉了第
#: 493 行**（`END observation progress: …`）——七行只放了六行。這種「宣稱逐字、其實刪過」
#: 正是本檔整章在治的病（宣稱與資料不符），且丟掉的偏偏是**唯一帶 `unique-sha` 觀察期進度
#: 的那行**：它與 win32 strict 樣式擦身而過（`END observation …` 不是 `END nightly
#: summary:`），若當初就在樣本裡，反而能多證一件事——strict 不會誤吃同前綴的鄰行。現已補回。
#: 該檔 untracked（`AutoClaude/.gitignore: logs/`）故本測試不能讀它比對；落地當下以
#: `python -c "...read().splitlines()[487:494]"` 逐行核對過，輸出貼在本批回報中。
_REAL_WIN_NIGHTLY_TAIL = """\
[2026-08-02 21:54:01][INFO] ===== Stage start: Cleanup =====
[2026-08-02 21:54:01][INFO] 保留既有 container: autoclaude_pg（非本腳本建立）
[2026-08-02 21:54:01][INFO] ===== Stage end:   Cleanup (exit=0, elapsed=00:00:00.015) =====
[2026-08-02 21:54:01][INFO] END nightly summary: mutation=0 pg-e2e=0 perf=0 drift=0 obs=0 \
local_ci_gate=0 sdd_chaos=0
[2026-08-02 21:54:01][INFO] END nightly summary json: {"sdd_chaos":0,"mutation":0,"drift":0,\
"local_ci_gate":0,"pg-e2e":0,"skip_sentinel":-1,"perf":0,"obs":0}
[2026-08-02 21:54:03][INFO] END observation progress: mutation=5/7 unique-sha (records=7; \
delta=0; stage=0) ac4=41/14 (delta=1; stage=0) obs=41/30 (delta=1; stage=0) drift=34/30 \
(delta=1; stage=0) — mutation 按 source_sha256 去重（ADR-SD09-011）、其餘三軌 same \
UTC-date dedup per M-05; delta=0 with stage!=0 表示本次未進帳
[2026-08-02 21:54:03][INFO] END exit decision: exit=0 (no failed stages; SKIP/WARN 不計失敗)
"""

#: `AutoClaude/tools/run_local_nightly.sh::write_heartbeat()` 的固定 4 行心跳（FAIL=0 態，
#: 該函式的 printf 形狀）。本機是 Windows、沒有這支檔，故形狀自產生程式碼取得——
#: **未在 macOS 真機實測**，此註記刻意留著（本輪修的就是「照抄別平台形狀」的病）。
_MAC_HEARTBEAT_FROM_WRITER = (
    "nightly_mac heartbeat（UTC）：2026-08-02T02:14:07Z\n"
    "===== nightly 彙總：PASS=4 FAIL=0 =====\n"
    "log=/Users/probe/AISDCL_Agent/AutoClaude/logs/nightly_mac_20260802_021407.log\n"
)


class _CountingHandle:
    """把每次 `read()`／逐行迭代真正吐出的位元組記到 `acc` 上（其餘方法原樣轉發）。"""

    def __init__(self, fh, acc: _ReadAccountingPath) -> None:
        self._fh, self._acc = fh, acc

    def __enter__(self) -> _CountingHandle:
        self._fh.__enter__()
        return self

    def __exit__(self, *exc) -> object:
        return self._fh.__exit__(*exc)

    def __iter__(self) -> _CountingHandle:
        return self

    def __next__(self) -> str | bytes:
        return self._acc.note(next(self._fh))

    def seek(self, *a, **kw) -> int:
        return self._fh.seek(*a, **kw)

    def read(self, *a, **kw) -> str | bytes:
        return self._acc.note(self._fh.read(*a, **kw))


class _ReadAccountingPath:
    """`Path` 的 duck-typed 替身，只暴露 `_read_probe_window()` 真正該用的兩個方法。

    刻意**不**繼承 `Path`、也刻意不補 `read_bytes`／`read_text`：那兩支正是「有界性被
    悄悄拿掉」最可能的替代寫法，缺席即 AttributeError ⇒ 繞過本鎖只會換一種紅法。
    """

    def __init__(self, real: Path) -> None:
        self.real, self.bytes_read = real, 0

    def note(self, chunk: str | bytes) -> str | bytes:
        self.bytes_read += len(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
        return chunk

    def stat(self) -> object:
        return self.real.stat()

    def open(self, *a, **kw) -> _CountingHandle:
        return _CountingHandle(self.real.open(*a, **kw), self)


class TestR71NightlyProbeActuallyParsesEachPlatformsOwnFormat(unittest.TestCase):
    """🔴 DEF-101-759：讓平台覆蓋不再靠人記憶的那道機械守，自己一天都沒量到過東西。

    `nightly_evidence()` 隨 `fbc9bb5`（DEF-101-756/757/758）落地，首版彙總行解析是
    `read_text().splitlines()[:3]` 找 `"PASS="`——那是 **mac 心跳**的形狀。win32 讀的卻是
    `run_local_nightly.ps1` 的**全量 log 複本**，彙總行在第 491 行、字面是
    `END nightly summary: …`，兩個致命點各自獨立、任一個都足以讓它恆不命中。
    於是 `--check-snapshot` 的 Windows 欄每天都印「（心跳無彙總行）」——而那句話讀起來
    像資料現況，不像探針壞掉。**fallback 文案把自己的失效偽裝成正常**，這是最難被發現的
    一種壞法：沒有紅燈、沒有 traceback，只有一句看似合理的話。

    本類別鎖的**意圖**（Rule 9）：探針必須拿**該平台自己的**格式去解析，且「解析不到」
    與「檔裡真的沒有」必須說得出差別——兩者的處置相反（改探針 vs 去看那台機器）。
    """

    def _probe(self, platform_key: str, body: str) -> str:
        with tempfile.TemporaryDirectory() as td:
            hb = Path(td) / BO.NIGHTLY_HEARTBEATS[platform_key]
            hb.parent.mkdir(parents=True, exist_ok=True)
            hb.write_text(body, encoding="utf-8")
            return BO.nightly_evidence(Path(td), platform_key)

    def test_windows_summary_is_found_in_a_real_full_log_not_only_its_first_lines(self) -> None:
        """立案樣本：真實 log 片段前面墊 500 行，模擬彙總行遠離檔頭的真實佈局。

        把讀取窗格改回 `[:3]` 這一支就必紅——那正是修復前的實況。
        """
        filler = "".join(
            f"[2026-08-02 10:18:09][INFO] ===== Stage start: filler-{i} =====\n"
            for i in range(500)
        )
        line = self._probe("win32", filler + _REAL_WIN_NIGHTLY_TAIL)
        self.assertIn("END nightly summary: mutation=0", line)
        self.assertIn("sdd_chaos=0", line)
        self.assertNotIn(
            "解析不到", line, "命中 loose 卻不命中 strict ⇒ win32 的 strict 樣式對不上真實 log"
        )
        self.assertNotIn(
            "找不到彙總行", line,
            "真實 log 明明有彙總行卻回 fallback——DEF-101-759 的原始症狀；"
            "fallback 讀起來像資料現況，於是探針壞掉一整天沒人發現",
        )

    def test_the_windows_sample_contains_no_pass_equals_so_one_pattern_cannot_serve_both(
        self,
    ) -> None:
        """🔴 **反「一個 pattern 硬套兩平台」的鑑別鎖**：兩邊的錨點字面互不出現。

        沒有這一支，未來有人為了少幾行又把兩個 spec 併回一個——而併回去的當下不會有任何
        東西轉紅（win32 欄只是安靜地落回 fallback）。所以要在這裡把「不可共用」變成硬事實。
        """
        self.assertNotIn(
            "PASS=", _REAL_WIN_NIGHTLY_TAIL,
            "真實 Windows nightly log 若真有 PASS= 則首版並非結構性失效，本鎖立案前提要重查",
        )
        self.assertNotIn("END nightly summary", _MAC_HEARTBEAT_FROM_WRITER)
        win, mac = BO.NIGHTLY_SUMMARY_SPECS["win32"], BO.NIGHTLY_SUMMARY_SPECS["darwin"]
        self.assertIsNone(win.strict.search(_MAC_HEARTBEAT_FROM_WRITER), "win 樣式吃進 mac 心跳")
        self.assertIsNone(mac.strict.search(_REAL_WIN_NIGHTLY_TAIL), "mac 樣式吃進 win 全量 log")

    def test_mac_heartbeat_contract_is_still_parsed(self) -> None:
        """對照組：修 win32 不得把 mac 那條本來就對的路徑弄壞（形狀取自 writer，未實測）。"""
        line = self._probe("darwin", _MAC_HEARTBEAT_FROM_WRITER)
        self.assertIn("===== nightly 彙總：PASS=4 FAIL=0 =====", line)

    def test_parse_miss_and_genuinely_absent_summary_do_not_share_one_sentence(self) -> None:
        """🔴 本輪最重要的一條：**探針失效**與**那輪沒跑完**必須是兩句話。

        首版兩者都印「（心跳無彙總行）」，於是「機械守壞了」在輸出上與「一切正常」同形。
        """
        drifted = _REAL_WIN_NIGHTLY_TAIL.replace("END nightly summary:", "END nightly SUMMARY-v2:")
        drift_line = self._probe("win32", drifted)
        truncated = self._probe("win32", "[2026-08-02 02:00:00][INFO] BEGIN nightly run\n")
        self.assertIn("解析不到", drift_line)
        self.assertIn("格式已漂移", drift_line, "未把矛頭指回探針 ⇒ 讀者會去查那台機器")
        self.assertIn("找不到彙總行", truncated)
        self.assertNotIn("解析不到", truncated, "沒有任何錨點時不得宣稱「解析不到」")
        self.assertNotEqual(drift_line, truncated)

    def test_probe_window_is_bounded_so_a_multi_megabyte_log_is_not_slurped(self) -> None:
        """全量 log 可達數 MB：窗格必須有界。以**實際讀進記憶體的位元組數**機械證明。

        🔴 本支上一版是**零鑑別力的死鎖**（本批注入實測：把 `f.seek(…)` 整行刪掉、改成
        `f.read()` 讀滿全檔，6/6 照樣全綠）。它斷言的是「檔頭誘餌不出現在**輸出那一行**」，
        而 `nightly_summary()` 取的是 `hits[-1]`——檔尾的真彙總行**永遠**會蓋掉檔頭誘餌，
        於是它證的其實是「取最後一筆命中」，跟有沒有界完全無關；docstring 卻宣稱後者。
        「寫了鎖沒驗鎖」與 DEF-101-759 的 fallback 文案同構：看起來有守，實際一天沒守過。

        改法：用 duck-typed Path 替身把 `read()` 真正吐出的位元組記帳。任何形態的整檔讀
        （`f.read()` 不 seek／先讀全檔再切尾）都會讓帳超出上限而轉紅；繞過 `path.open()`
        改用 `read_bytes()`／`read_text()` 則因替身沒有該方法而 AttributeError——同樣是紅，
        不會靜默通過。誘餌斷言保留但**改斷在窗格上**（`window`）而非輸出行，那才有牙。
        """
        oversize = BO._NIGHTLY_TAIL_BYTES * 4
        decoy = "[2026-01-01 00:00:00][INFO] END nightly summary: DECOY-FROM-HEAD\n"
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "nightly_latest.log"
            log.write_text(decoy + "x" * oversize + "\n" + _REAL_WIN_NIGHTLY_TAIL, "utf-8")
            size = log.stat().st_size
            acc = _ReadAccountingPath(log)
            window = BO._read_probe_window(acc, BO.NIGHTLY_SUMMARY_SPECS["win32"].head_lines)
        self.assertGreater(
            size, BO._NIGHTLY_TAIL_BYTES * 3,
            "樣本不夠大 ⇒『整檔讀』與『讀檔尾』量不出差別，本鎖會退化成恆真",
        )
        self.assertLessEqual(
            acc.bytes_read, BO._NIGHTLY_TAIL_BYTES,
            f"探針自 {size} bytes 的 log 讀進了 {acc.bytes_read} bytes（上限 "
            f"{BO._NIGHTLY_TAIL_BYTES}）⇒ 有界性沒了，數 MB 全量 log 會被整檔載入記憶體",
        )
        self.assertNotIn("DECOY-FROM-HEAD", window, "檔頭內容進了窗格 ⇒ 窗格不是檔尾窗格")
        self.assertIn(
            "END nightly summary: mutation=0", window,
            "有界了卻也讀不到彙總行 ⇒ 窗格開錯位置（有界但無用，比沒界更糟）",
        )

    def test_every_heartbeat_platform_has_a_parsing_spec(self) -> None:
        """兩張表必須同鍵：只加心跳檔卻忘了加 spec，該欄會安靜地退回「本平台無心跳檔」。"""
        self.assertEqual(sorted(BO.NIGHTLY_HEARTBEATS), sorted(BO.NIGHTLY_SUMMARY_SPECS))


class TestR71StaleFingerprintMustNotSwallowTheCoverageDetail(unittest.TestCase):
    """🔴 D-3：**一個無關的漂移不得讓整段平台覆蓋明細消失**（與 DEF-101-759 同族）。

    實測立案（本批以 production 入口重現）：`tools/sync_onboarding_baselines.py
    --check-snapshot` → rc=1，輸出**停在 ❌ 指紋區塊**，逐欄明細（baseline-origin 三態、
    provenance、nightly 證據、四格記載值）一行都沒印。原因是 `main()` 在 `problems`
    非空時當場 `return 1`，而那段明細排在 return 之後。

    為何這是設計缺陷而不只是「順序不巧」：指紋 stale 在單機交替工作流下是**日常態**
    （動到四棵測試樹任一棵就觸發，本批實測就是被另一個並行包改動 AutoClaude/tests/ 觸發的）
    ⇒ 專門為根治 DEF-101-756 誤讀而加的那段說明，**在最常見的那條路徑上結構性看不見**；
    讀者拿到的只有「某棵樹指紋變了」，於是又得自己腦補「那這平台到底驗過沒有」——回到
    事故原點。**掩蓋的形態與 fallback 文案一樣：沒有紅燈、沒有 traceback，只是資訊沒了。**

    修法（rc 語意**不放寬**）：明細兩條路都印，判決行標明它屬 presumed stale。
    """

    def _run(self, problems: list[str]) -> tuple[int, str, str]:
        """以替身 `snapshot_report` 驅動，讓本鎖與「真實文件此刻是否過期」解耦。

        否則某一輪剛好全欄新鮮時，紅路徑那半邊會**從來沒被執行過**而沒人發現
        （同 `TestR67...test_notice_goes_to_stdout...` 已論證過的退化）。
        """
        original = SYNC.snapshot_report
        out, err = io.StringIO(), io.StringIO()
        try:
            SYNC.snapshot_report = lambda *a, **k: (list(problems), [])
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = SYNC.main(["--check-snapshot"])
        finally:
            SYNC.snapshot_report = original
        return rc, out.getvalue(), err.getvalue()

    def test_red_path_still_prints_every_columns_coverage_detail(self) -> None:
        rc, out, err = self._run(["PROBE-STALE-D3"])
        self.assertEqual(rc, 1, "rc 語意被放寬 ⇒ stale 不再擋 pre-push，那是比原缺陷更糟的修法")
        self.assertIn("PROBE-STALE-D3", err, "rc 級問題必須仍在 stderr 的 ❌ 區塊")
        for label in SYNC._PLATFORM_COLUMN_LABELS.values():
            self.assertIn(
                f"[{label} 欄]", out,
                f"{label} 欄的逐欄明細在紅路徑上被吞掉——一個無關漂移就讓平台覆蓋資訊消失",
            )
        self.assertIn("nightly 證據：", out, "nightly 落地產物證據在紅路徑上看不到（D-3 本體）")
        self.assertIn("provenance=", out)
        self.assertIn(
            "presumed stale", out,
            "紅路徑照印明細卻不標記 stale ⇒ 讀者會把過期的四格計數當現況引用，那是另一種假宣稱",
        )

    def test_green_path_verdict_and_rc_are_unchanged(self) -> None:
        """對照組：修紅路徑不得動到綠路徑的既有契約（✅ 字面 + rc=0）。"""
        rc, out, _err = self._run([])
        self.assertEqual(rc, 0)
        self.assertIn("✅ §7 表② 指紋相符", out)
        self.assertNotIn("presumed stale", out, "全新鮮卻自稱 stale ⇒ 反向假宣稱")


# ══════════════════════════════════════════════════════════════════════════════
# R74：根 CLAUDE.md 的「治理宣稱」↔ 實際機械物 對帳鎖
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體（兩筆，同一個形態）：
#   ① 根 CLAUDE.md 把 `enforce_docs_path.py` 寫成「強制」、`check_lang.py` 寫成「另有」
#      ——而 `AutoClaude/.claude/settings.json` 註冊的 6 支 hook 只有 1 支橋接到根
#      `.claude/settings.json`，且 Claude Code 不遞迴子目錄載 hook ⇒ 在 monorepo 根
#      session（本檔被載入的那種）下，另外 5 支一行都不會跑。**文件宣稱與實際生效不符。**
#   ② 鐵律三的 8 項觸發清單只有 4 項有掃描器，而 `DEF-101-766` 正落在沒有掃描器的兩格。
#      散文寫「必須自問」對「當下的模型」零攔阻力（R71 已實證），所以「哪幾項沒人在守」
#      必須是可查的量測值。
# 兩筆的共同修法：**把宣稱與機械物綁成同進同退**，任一邊漂移即紅。
_ROOT_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"
_ROOT_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
#: 未橋接到根層 ⇒ 宣稱它的那一行必須帶這個字樣，讀者才不會誤以為根 session 也攔。
_SUBPROJECT_SCOPE_MARK = "僅 AutoClaude 子專案 session"
#: 鐵律三觸發清單中**沒有掃描器**的項（人可讀的宣告面；量測面是 CLAUDE.md 那張表本身）。
#: 補了掃描器就把該列的機械物欄改掉，並把該項從此處刪除——兩邊由下方雙向判準綁住。
_IRON_LAW3_UNCOVERED: tuple[str, ...] = (
    "副檔名判斷",
    # 🔴 R80（包 B）：`$env:*` 讀取／`Get-Command` 解析／大小寫敏感度 三項移出本清單。
    # 前兩項是**本輪補上站點級判準**（`TestPowerShellPlatformSensitiveSites`）⇒ 分子 +1 +1；
    # 第三項則是**訂正一筆假事實**——`tools/check_ntfs_paths.py` 的大小寫碰撞正規化鍵
    # 早就存在、也早就接在 pre-commit 與四支 CI workflow 上，本表卻自 R74 起一直說沒人守。
    # 這個方向（**低報分子**）本鎖結構上看不見：它只讀那張表**自己說**有沒有機械物，
    # 從不問「這句話是真的嗎」。補上的證偽判準住在
    # `tools/tests/test_platform_neutral_paths.py::TestIronLaw3NoMechanismClaimsAreFalsifiable`
    # ——每一格自陳沒人守者必須登記一組證偽探針（token × 已審視清單）並通過它。
    #
    # R80 新登記的危害類：`shell=True` 的原生殼差異（Windows `cmd.exe` ⇄ POSIX `/bin/sh`
    # 的引號／`&&`／路徑分隔／rc 語意）。分母 +1 而分子不動＝**綠**。它與
    # `AutoClaude/tests/test_evaluator_kill_tree.py` 同關鍵字但不同主題（那支守的是
    # 逾時 kill 整棵行程樹），而且存量掃描結構上量不到它——指令來自 playbook＝使用者輸入。
    "shell=True",
    # 🔴 R79：`.ps1` 方向的行尾**已補上機械物**（PostToolUse hook 寫入當下補回 CRLF ＋
    # 根層 unittest 事後量工作樹），故從本清單移出、該列的機械物欄同步改寫 ⇒ 分子 +1。
    # 這是本表雙單邊棘輪設計裡唯一合法的「分子上升」路徑：補了掃描器就改機械物欄，
    # 不是把整列拿掉（拿掉會讓分母降而轉紅）。
    #
    # 🔴 R80（包 B）：`行尾（**`.py` 方向**` 也自本清單移出——但它與上面三項的成因不同，
    # 值得分開記：R79 把它登記成「新發現的無守門危害類」，而**那句話本身就不真**。
    # 守門的類別（`TestWorktreeEolMatchesPolicy`）一直都在，只是被 `_EOL_LF_SCOPE` 窄化成
    # 只看 `.sh`／`.bash`，而且該類還有一條 `assertNotIn(".py", policy)` 把「`.py` 必須被
    # 放行」釘成契約 ⇒ **有鎖在守假話**：檔案在、判準在、測試全綠，只有讀完那個常數才知道
    # `.py` 從來不在射程裡。本輪以獨立射程承接（`TestActiveSourceEolIsRatchetedSeparately…`：
    # 活躍面止血、凍結面只登記），分子 +1。
    # 同時訂正它的量：R79 記的 4,176 只是 `.py` 這一塊，全庫工作樹行尾與宣告不符者當回合
    # 實測 18,255 支、其中約 95% 落在 Copy-on-Evolve 凍結面 ⇒「全部就地轉 LF」不是修法。
)
#: 鐵律三對照表的表頭（定位那**一張**表，不是 CLAUDE.md 內所有表格）。
_IRON_LAW3_TABLE_HEAD = "| 觸發項 |"
#: 機械物欄用來自陳「這一格沒人在守」的字樣。
_IRON_LAW3_NO_MECHANISM = "無機械物"
#: 覆蓋率棘輪的兩個釘（本輪取代單邊計數；完整理由見同檔
#: `TestR74IronLawMechanismAccounting` 的
#: `test_iron_law3_coverage_only_goes_up_and_the_denominator_may_grow`）。
#: 分子＝**有機械物**的觸發項數，只准上升（拆掉掃描器即紅）。
#: R79：4 → 7（`.ps1` 行尾補上 hook＋事後兜底；另新增 exec bit 與目錄項原語兩列，
#: 兩列都是「新增時就已經有掃描器」，分子分母同時 +1）。
#: R80（包 B）：7 → 12。分子 +5＝`$env:*` 讀取、`Get-Command` 解析、大小寫敏感度
#: （前兩項本輪新建站點級判準；第三項是訂正低報）、`.py` 行尾（本輪新建活躍面止血）、
#: 以及兩個新登記且**當輪就有掃描器**的危害類中的 shebang×行尾；naive 本地時間戳那一列
#: 同樣是新增即有掃描器 ⇒ 實際分子為 13，此處只釘到 12 是**刻意留一格**：並行工作包
#: 若在本輪同時動到這張表，釘到剛好等於現值會讓兩邊互相判紅。地板是下界不是等號。
_IRON_LAW3_COVERED_FLOOR = 12
#: 分母＝**已登記**的危害類數，只准上升（刪列來讓數字好看即紅）。未覆蓋數＝分母−分子，
#: 刻意**不設上限**——那正是舊判準把「還有幾類沒人守」與「我們知道有幾類危害」綁死的地方。
#: R79：8 → 12（`.py` 行尾、exec bit、目錄項原語三類新登記；`.ps1` 行尾那一列原本就在表上）。
#: R80（包 B）：12 → 14。分母 +3＝shebang×行尾、naive 本地時間戳被持久化、
#: `shell=True` 原生殼差異（三類此前一格判準都沒有，前兩類本輪連同掃描器一起落地、
#: 第三類誠實登記為無人守）。同上，釘到比現值低一格以容忍並行包同時擴表。
_IRON_LAW3_KNOWN_FLOOR = 14


def hook_scripts_named_in(text: str, repo_root: Path) -> dict[str, list[str]]:
    """{hook 腳本 basename: 提到它的行}。掃描面＝repo 內實存的 hook 腳本，不寫死清單。"""
    known = {
        p.name
        for d in ("\\.claude/hooks", "AutoClaude/tools/hooks")
        for p in (repo_root / d.replace("\\.", ".")).glob("*.py")
    }
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        for name in known:
            if name in line:
                out.setdefault(name, []).append(line)
    return out


def registered_hook_basenames(settings_text: str) -> set[str]:
    """根 `.claude/settings.json` 內**真的被註冊**的 hook 腳本 basename 集合。

    解析走既有 SSOT `test_subprocess_encoding_hygiene.hook_command_scripts()`
    （`json.loads` → `hooks[*][*].hooks[*].command`），該函式自己另有紅綠自證
    （該檔判準四），故本檔不重寫一份解析。

    JSON 壞掉時**刻意讓 `json.loads` 拋出**：settings 解析不了是註冊表本身壞了，
    比「當成沒有任何 hook 被註冊」誠實——後者會讓 ② 那一向整組靜默失效。
    """
    return {
        PurePosixPath(rel).name
        for _event, rel in hook_command_scripts(json.loads(settings_text))
    }


def hook_claim_problems(text: str, settings_text: str, repo_root: Path) -> list[str]:
    """根 CLAUDE.md 提到的每支 hook，**雙向**都要與根層註冊實況相符。

    ① 未註冊者：凡提到它的行都必須標明子專案射程，否則讀者會以為根 session 也會攔。
    ② **已註冊者：任何一行都不得標成「僅 AutoClaude 子專案 session」**（R75 訂正）。

    🔴 為何非補 ② 不可（本函式自己放行過一次假事實）：原判準是 OR——「已註冊 **或**
    該行標明子專案射程」，於是 `if name in settings_text: continue` 讓「已註冊」單獨
    成為免檢通行證，**完全不看那些行實際寫了什麼**。實況：`a371068` 這個 commit 的
    一個包把 `check_sh_eol.py` 橋進根 `.claude/settings.json`，同一個 commit 的訂正文
    卻仍把它算在「不會跑」那一組並連帶少報了橋接支數 ⇒ 假事實在寫下的當回合就成立，
    而這道鎖結構上恆綠（實跑當時 4 tests 全 ok、rc=0）。

    ②「一行都不得」而非「主要那行不得」是刻意的：這個字樣的語意是絕對的（「這支在根
    session 不會跑」），一支會跑的 hook 沒有任何語境能讓那句話變成真的。副作用是文件
    必須把「已橋接清單」與「未橋接清單」**分行寫**——那不是本判準的成本，而是它要的
    結構：兩組事實混在同一行時，逐行 substring 判準對任何一組都判不準。

    🔴 **R76 訂正（同一個通行證換皮復活）**：「已註冊」的判定原本是
    `if name in settings_text:`——拿**整份 settings.json 的文字**做 substring。於是
    該檔任何角落提到過的名字（`_comment`／`_why` 敘述、被註解掉的舊 wiring、`matcher`
    說明裡順口舉的例）都算「已註冊」而讓那支 hook **整支免檢**；把真 wiring 拔掉、
    只留一句註解，根 CLAUDE.md 那句「已橋接 N 支」就成了假話而零訊號。R75 才剛拆掉
    OR 型通行證（見上方 ②），這裡是同一個病的第二個住所：**判定「有沒有」時，掃描面
    必須是解析出來的結構，不是整檔文字。** 現行判定改走
    `registered_hook_basenames()`（既有 SSOT 的 `hooks[*][*].hooks[*].command`）。
    """
    problems: list[str] = []
    registered = registered_hook_basenames(settings_text)
    for name, lines in sorted(hook_scripts_named_in(text, repo_root).items()):
        if name in registered:
            mislabelled = [ln for ln in lines if _SUBPROJECT_SCOPE_MARK in ln]
            if mislabelled:
                problems.append(
                    f"{name} **已註冊**於根 .claude/settings.json（根 session 會跑），"
                    f"但根 CLAUDE.md 有 {len(mislabelled)} 行把它標成「"
                    f"{_SUBPROJECT_SCOPE_MARK}」⇒ 把會跑的東西寫成不會跑，與反向那筆"
                    f"同樣是假事實。修法：把已橋接的 hook 名稱與該字樣寫在不同行。"
                    f"首例：{mislabelled[0][:70]}")
            continue
        unmarked = [ln for ln in lines if _SUBPROJECT_SCOPE_MARK not in ln]
        if unmarked:
            problems.append(
                f"{name} 未註冊於根 .claude/settings.json，但根 CLAUDE.md 有 "
                f"{len(unmarked)} 行提到它且未標「{_SUBPROJECT_SCOPE_MARK}」⇒ 讀者會以為"
                f"在根 session 也會攔（實際一行都不會跑）。首例：{unmarked[0][:70]}")
    return problems


class TestR74RootClaudeMdHookClaimsMatchRegistration(unittest.TestCase):
    """根 CLAUDE.md 不得宣稱一支「其實不會在本 session 生效」的 hook 為強制。"""

    def test_current_claude_md_passes(self) -> None:
        problems = hook_claim_problems(
            _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig"),
            _ROOT_SETTINGS.read_text(encoding="utf-8-sig"), _REPO_ROOT)
        self.assertEqual(problems, [], "根 CLAUDE.md hook 宣稱與註冊不符：\n  "
                                       + "\n  ".join(problems))

    def test_scan_surface_is_non_empty(self) -> None:
        """自錨：枚舉不到 hook 腳本時，判準對任何文件恆綠。"""
        named = hook_scripts_named_in(
            _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig"), _REPO_ROOT)
        self.assertIn("enforce_docs_path.py", named, "掃描面抓不到已知站點 ⇒ 鎖已空轉")
        self.assertIn("block_bash_on_windows.py", named)

    def test_an_unmarked_unregistered_hook_is_red(self) -> None:
        """注入＝修前實況：宣稱「以 enforce_docs_path.py 強制」而根層沒註冊它。"""
        problems = hook_claim_problems(
            "文檔目錄編號制：AutoClaude 以 PreToolUse hook `enforce_docs_path.py` 強制。",
            _ROOT_SETTINGS.read_text(encoding="utf-8-sig"), _REPO_ROOT)
        self.assertTrue(any("enforce_docs_path.py" in p for p in problems), problems)

    def test_a_registered_hook_needs_no_marker(self) -> None:
        """反向：已橋接到根層的 hook 不必加射程註記（否則鎖會逼出誤導性的註記）。

        這條語意在 R75 訂正時**刻意保留**：新增的是「已註冊者不得被標成不會跑」，
        不是「已註冊者必須加註記」。兩者混淆會把鎖變成假註記的生產者。
        """
        self.assertEqual(
            hook_claim_problems("根層已註冊 `block_bash_on_windows.py`，會攔。",
                                _ROOT_SETTINGS.read_text(encoding="utf-8-sig"),
                                _REPO_ROOT),
            [])

    def test_a_registered_hook_marked_subproject_only_is_red(self) -> None:
        """注入＝修前實況（R75 訂正的鑑別力）：`check_sh_eol.py` 已橋接到根層，
        而合成文字把它與另外幾支一起寫在同一行並標成僅子專案生效 ⇒ 必須紅。

        用 `check_sh_eol.py` 而不是造一個假名，是因為它就是真的踩過這個組合的那一支；
        名字若換成不存在的 hook，`hook_scripts_named_in` 的掃描面根本不會收它，測試
        會因為「掃不到」而綠，那是最沒鑑別力的一種綠。
        """
        settings = _ROOT_SETTINGS.read_text(encoding="utf-8-sig")
        self.assertIn("check_sh_eol.py", settings, "前提已變：該 hook 已不在根層註冊，"
                                                   "請改用另一支已註冊的 hook 重寫本注入")
        problems = hook_claim_problems(
            "註冊 6 支 hook——`enforce_docs_path.py`／`check_sh_eol.py`／"
            f"`check_lang.py`，除某支外皆{_SUBPROJECT_SCOPE_MARK} 生效。",
            settings, _REPO_ROOT)
        self.assertTrue(
            any("check_sh_eol.py" in p and "已註冊" in p for p in problems),
            f"已註冊卻被標成不會跑，判準必須點名它；實得：{problems}")

    def test_reverse_criterion_does_not_fire_on_unregistered_hooks(self) -> None:
        """對照組：反向判準不得把「未註冊 ＋ 有標記」這個**正確**的組合也判紅。

        少了這條，把 ② 寫成「任何一行都不得帶該字樣」（漏掉已註冊這個前提）會全綠通過，
        而那樣的判準會逼所有正確的射程註記消失——比沒有判準更糟。

        🔴 前提刻意以**行為**自證，而不是對 `settings.json` 整份文件斷言某字樣不出現：
        後者正是 `test_archive_defect_log.py::TestNoAssertionSamplesALiveDocumentWholesale`
        禁止的形態（文件只要合法地提到該字樣就假紅），本測試初稿即被那道鎖抓到。
        下面第二個斷言同時比原前提**更強**：它證明這支 hook 走的確實是「未註冊」那一支
        判準，第一行的綠不是因為它被當成已註冊而整支免檢。
        """
        settings = _ROOT_SETTINGS.read_text(encoding="utf-8-sig")
        self.assertEqual(
            hook_claim_problems(
                f"`enforce_docs_path.py`（PreToolUse hook）**{_SUBPROJECT_SCOPE_MARK}** 生效。",
                settings, _REPO_ROOT),
            [])
        self.assertTrue(
            hook_claim_problems("`enforce_docs_path.py`（PreToolUse hook）生效。",
                                settings, _REPO_ROOT),
            "拿掉射程註記仍全綠 ⇒ 該 hook 被當成已註冊而免檢，上一個斷言是空虛的綠")

    # ── R76：「已註冊」的判定面（整檔 substring → 解析出的 command 集合）────────
    def test_the_registered_set_comes_from_the_parsed_commands(self) -> None:
        """自錨（對照組）：真 settings 解析得出的集合必須非空、且含真的橋接過去那幾支。

        少了這一條，`registered_hook_basenames()` 一旦解析壞掉（回空集合）會讓每一支
        hook 都落進「未註冊」那一支判準——①那一向會對已橋接的 hook 逼出誤導性註記、
        ②那一向則整組失效，而兩者都不會有任何東西說話。
        """
        registered = registered_hook_basenames(
            _ROOT_SETTINGS.read_text(encoding="utf-8-sig"))
        self.assertTrue(registered, "解析不出任何已註冊 hook ⇒ 判準的兩向同時失真")
        for expected in ("block_bash_on_windows.py", "check_sh_eol.py"):
            self.assertIn(expected, registered,
                          f"{expected} 在根層 settings.json 有 wiring 卻解析不到 ⇒ "
                          f"command 形態變了而解析面沒跟上；實得：{sorted(registered)}")

    def test_a_name_that_only_appears_in_a_comment_does_not_count_as_registered(self) -> None:
        """🔴 R76 注入＝修前 fail-open 的逐字形態：一個 `_comment` 就買到整支免檢。

        修前判準是 `if name in settings_text: continue`。本注入的 settings **只在
        `_comment` 裡**提到 `enforce_docs_path.py`（真 wiring 完全沒有它），而文件那行
        又漏了射程註記——這正是本鎖存在的理由那一種假事實。修前：名字出現在檔內 ⇒
        判為已註冊 ⇒ `continue` ⇒ 全綠。現行：必須紅。

        用 `enforce_docs_path.py` 而不是造一個假名，理由同 `check_sh_eol.py` 那支注入：
        假名不在 `hook_scripts_named_in` 的掃描面內，測試會因為「掃不到」而綠。
        """
        settings = json.dumps(
            {"_comment": "曾評估把 enforce_docs_path.py 橋到根層，先記個名字備忘",
             "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                 "type": "command",
                 "command": "python .claude/hooks/block_bash_on_windows.py"}]}]}},
            ensure_ascii=False)
        self.assertIn("enforce_docs_path.py", settings, "注入語料本身沒帶那個名字 ⇒ "
                                                        "它證明不了整檔 substring 的問題")
        self.assertNotIn(
            "enforce_docs_path.py", registered_hook_basenames(settings),
            "只出現在 `_comment` 的名字被算成已註冊 ⇒ 判定面又退回整檔 substring")
        problems = hook_claim_problems(
            "文檔目錄編號制：AutoClaude 以 PreToolUse hook `enforce_docs_path.py` 強制。",
            settings, _REPO_ROOT)
        self.assertTrue(
            any("enforce_docs_path.py" in p for p in problems),
            f"註解裡的名字買到了免檢 ⇒ R75 拆掉的 OR 型通行證換皮復活；實得：{problems}")

    def test_a_really_registered_hook_is_still_judged_registered(self) -> None:
        """反向對照：真 wiring 仍必須被判為已註冊（否則上一支只是把所有輸入都判紅）。

        判定的是**同一支**在上面被註解形態擋掉的判準路徑：這裡 `block_bash_on_windows.py`
        走的是真 command，標成「僅子專案生效」必須紅（②那一向）。
        """
        settings = json.dumps(
            {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "command",
                "command": "python .claude/hooks/block_bash_on_windows.py"}]}]}},
            ensure_ascii=False)
        self.assertIn("block_bash_on_windows.py", registered_hook_basenames(settings))
        problems = hook_claim_problems(
            f"`block_bash_on_windows.py` **{_SUBPROJECT_SCOPE_MARK}** 生效。",
            settings, _REPO_ROOT)
        self.assertTrue(any("已註冊" in p for p in problems), problems)


def unnamed_registered_hook_problems(
    text: str, settings_text: str, repo_root: Path
) -> list[str]:
    """根 `.claude/settings.json` 註冊了、而根 CLAUDE.md 一行都沒提到的 hook（空＝通過）。

    🔴 **這是 `hook_claim_problems()` 的第三向（R79 收斂包）**。前兩向的掃描面都是
    `hook_scripts_named_in(CLAUDE.md, …)`——**只檢查文件裡有被點名的那幾支**。於是
    「已註冊、但文件從頭到尾沒提」這個組合結構上落在兩向之外：兩向都不會觸及它。

    代價已實測：`lint_powershell_command.py` 自 R77 上線起就在根層攔 PowerShell 指令
    （鐵律二與「讀 rc 不接管線」的唯一機械物），而 R79 掃描時根 CLAUDE.md 全檔提到
    hook 的地方只有鐵律一那一處 ⇒ 那兩節讀起來都像純自律。方向與慣見的相反但同樣是
    假圖像：不是「宣稱一個不存在的機械物」，是**有機械物卻被記成沒有**，而下一輪很
    可能為它們再蓋一支攔截器（同一份知識住兩個家，R73 `Find-GitBash` 的復發形態）。

    分母刻意是 `settings.json` 現查出來的註冊集合（會變的量測值），不是寫死清單——
    新增 hook 忘了寫文件會當場紅，而拿掉 hook 不會留下一筆要人回收的登記。
    只要求**被點名一次**，不要求寫在哪一節：規定位置就會逼出應付式的一行。
    """
    registered = registered_hook_basenames(settings_text)
    named = set(hook_scripts_named_in(text, repo_root))
    return [
        f"{name} 已註冊於根 .claude/settings.json（每個根 session 都會跑），"
        f"但根 CLAUDE.md 一行都沒提到它 ⇒ 讀者照本檔推論會漏掉一支活的守衛，"
        f"而下一輪很可能為同一件事再蓋一支（同一份知識住兩個家）。"
        f"修法：在它守的那一節加一句「本條已有機械物」並具名該路徑"
        for name in sorted(registered - named)
    ]


class TestR79EveryRegisteredHookIsNamedInClaudeMd(unittest.TestCase):
    """第三向：根層註冊的每一支 hook 都必須在根 CLAUDE.md 至少被點名一次。"""

    def test_current_claude_md_names_every_registered_hook(self) -> None:
        problems = unnamed_registered_hook_problems(
            _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig"),
            _ROOT_SETTINGS.read_text(encoding="utf-8-sig"), _REPO_ROOT)
        self.assertEqual(problems, [], "根層註冊了卻沒被文件點名的 hook：\n  "
                                       + "\n  ".join(problems))

    def test_an_unnamed_registered_hook_is_red(self) -> None:
        """注入＝修前實況重演：文件只提鐵律一那一支，其餘註冊的 hook 一律該紅。

        用**真的 settings.json** 當分母：合成 settings 證明不了「對 repo 現況有牙」，
        而修前實況正是真 settings 裡有六支、文件只提得出其中幾支。
        """
        problems = unnamed_registered_hook_problems(
            "🔴 本條已有機械物：`.claude/hooks/block_bash_on_windows.py`。",
            _ROOT_SETTINGS.read_text(encoding="utf-8-sig"), _REPO_ROOT)
        self.assertTrue(
            any("lint_powershell_command.py" in p for p in problems),
            f"已註冊但文件沒提的 hook 未被點名 ⇒ 第三向沒有牙；實得：{problems}")
        self.assertFalse(
            [p for p in problems if "block_bash_on_windows.py" in p],
            "有被點名的那一支不該入列（否則本判準只是全都判紅）")

    def test_the_denominator_is_measured_not_hardcoded(self) -> None:
        """自錨：分母必須是解析出來的註冊集合，且真的非空。

        解析一旦壞掉（回空集合），上一支對任何文件恆綠——靜默縮面正是本家族一再犯的病。
        """
        registered = registered_hook_basenames(
            _ROOT_SETTINGS.read_text(encoding="utf-8-sig"))
        self.assertGreaterEqual(
            len(registered), 3, f"註冊面解析得異常少：{sorted(registered)}")
        self.assertIn("lint_powershell_command.py", registered,
                      "前提已變：該 hook 已不在根層註冊 ⇒ 請改用另一支已註冊的重寫本注入")

    def test_a_registered_hook_named_anywhere_counts(self) -> None:
        """對照組：只要文件某處點名就算數——規定寫在哪一節會逼出應付式的一行。"""
        settings = json.dumps(
            {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "command",
                "command": "python .claude/hooks/block_bash_on_windows.py"}]}]}},
            ensure_ascii=False)
        self.assertEqual(
            unnamed_registered_hook_problems(
                "附錄：本 repo 的守衛之一是 block_bash_on_windows.py。",
                settings, _REPO_ROOT),
            [])


# ── R75 訂正：具名機械物鎖的三面擴張（幽靈機械物 4 筆的逃逸路徑）─────────────
#
# 🔴 缺陷本體：原判準是「掃根 CLAUDE.md、要求反引號、副檔名只認 `.py`、只斷言檔案存在」。
# 四個縫各自漏了東西，實測逃逸 4 筆（Architect／SA 實查，本輪以探針全部重現）：
#   ① 掃描面只有根 CLAUDE.md ⇒ `tools/*.py` 註解與 `tools/*.json` 的 `_why` 裡指認機械物
#      的宣稱完全不在視野內。逃逸：`archive_defect_log.py` 與 `check_defect_log_crossref.py`
#      各指向一支從未存在的 `test_defect_log_capacity_policy_r68.py`（R68 落地時
#      `tools/tests` 鎖檔數棘輪擋下新增鎖檔，判準併進了 `test_archive_defect_log.py`，
#      指標卻留在原本打算開的檔名上）；`scheduled_task_expectations.json` 同型。
#   ② 副檔名只認 `.py` ⇒ 根 CLAUDE.md 對 `install_windows_nightly.ps1` 寫了 `AutoClaude/`
#      前綴（該安裝器住 monorepo 根層 `tools/`），三個解析基準都找不到，卻因為是 `.ps1`
#      而不被檢查。
#   ③ 只斷言「檔案存在」⇒ **「檔案在、但守的是別的東西」照樣通過**。鐵律三 `行尾` 列
#      具名 `test_ps1_bom.py`，而該檔全篇是 .ps1 的 UTF-8 BOM 政策，對 CRLF／行尾零判準。
#      這一種比指向不存在的檔更難看見：路徑點得開、檔案打得開，只有讀完才知道守錯東西。
#   ④ `::Symbol` 從不驗證 ⇒ 類別改名／搬家後指標靜默失效。
_MECHANISM_CLAIM_MARKS: tuple[str, ...] = ("機械鎖", "機械釘")
_MECHANISM_EXTS = "py|ps1|sh|json"
#: 具名機械物引用的形狀：`<路徑>.<副檔名>` ＋ 可選的 `::Symbol`（可多段）。
_MECHANISM_PATH_RE = re.compile(
    r"((?:tools|AutoClaude|AISDLC_SDD|\.claude)[\w./-]+\.(?:" + _MECHANISM_EXTS + r"))"
    r"((?:::[\w.]+)*)"
)
#: 解析基準。根 CLAUDE.md 自己就有〈路徑陷阱〉一節明載：子專案段落的相對路徑是
#: **相對於該子專案目錄**（`AutoClaude — 常用指令` 段的 `tools/check_loc_budget.py`
#: 就是 `AutoClaude/tools/check_loc_budget.py`）。只拿 repo 根去解會把那些正確引用
#: 誤報成不存在——誤報的鎖最後一定被整道關掉，比沒有鎖更糟。
_MECHANISM_PATH_BASES: tuple[str, ...] = (".", "AutoClaude", "AISDLC_SDD")
#: 額外掃描面（相對 repo 根的 glob）。只掃**檔名層**、不遞迴：`tools/tests/` 底下是
#: 鎖本身的住所，鎖檔互相引用是常態而非宣稱，納入只會製造噪音。
_MECHANISM_EXTRA_GLOBS: tuple[str, ...] = ("tools/*.py", "tools/*.json")
#: 鐵律三各列主題 → 該列具名檔案內至少須出現其中一個關鍵詞（大小寫不敏感）。
#: 這是「實質」判準的取值面：**必要條件不是充分條件**（抓得到「完全沒碰那個主題」，
#: 抓不到「碰了但判準很弱」）。刻意用關鍵詞而不是解析判準內容——後者要為每一種主題
#: 寫一個專用分析器，那本身就是新的漂移來源。
_IRON_LAW3_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "路徑分隔符": ("sep", "分隔符", "backslash", "posixpath"),
    "console 編碼": ("encoding", "編碼", "cp950"),
    "行尾": ("crlf", "eol", r"\r\n", "行尾"),
    "$IsWindows": ("iswindows",),
    "Get-Command": ("get-command",),
    # R79 新增兩列（補了掃描器就要同步本表，否則實質判準對新列零覆蓋）。
    "exec bit": ("100755", "exec", "filemode", "chmod"),
    "目錄項": ("os.replace", "rename", "winerror", "目錄項"),
    # R80（包 B）新增／訂正四列。同上：補了掃描器就要同步本表。
    "大小寫敏感度": ("大小寫", "collision", "casefold"),
    "$env:": ("$env:", "environment", "env:temp"),
    "shebang": ("shebang", "#!"),
    "時間戳": ("datetime", "isoformat", "astimezone"),
}


def mechanism_claims(
    text: str, source: str, *, require_backticks: bool
) -> list[tuple[str, str, str, str]]:
    """`(來源, 相對路徑, 符號, 原行)`；`source` 只用於失敗訊息定位。

    `require_backticks`：活文件（根 CLAUDE.md）一律以反引號寫路徑，要求它可濾掉散文
    裡的假路徑；`.json` 的 `_why` 陣列寫不出反引號慣例，故程式碼面不要求，改以「該行
    帶『機械鎖／機械釘』字樣」限縮——那個字樣就是**指認機械物**這個宣稱本身的標記。
    整檔掃會把純敘事的路徑提及（「見 tools/lib/xxx.py」）一併納入，偽陽性會讓這道鎖
    被整道關掉，那是比縮面更糟的結局。
    """
    out: list[tuple[str, str, str, str]] = []
    for line in text.splitlines():
        if not require_backticks and not any(k in line for k in _MECHANISM_CLAIM_MARKS):
            continue
        for m in _MECHANISM_PATH_RE.finditer(line):
            if require_backticks:
                start, end = m.start(1), m.end(2)
                if not (start and line[start - 1] == "`" and line[end:end + 1] == "`"):
                    continue
            out.append((source, m.group(1), m.group(2).lstrip(":"), line.strip()))
    return out


def collect_mechanism_claims(repo_root: Path) -> list[tuple[str, str, str, str]]:
    """三面掃描面合起來的全部具名機械物引用（現查，不寫死清單）。"""
    claims = mechanism_claims(
        (repo_root / "CLAUDE.md").read_text(encoding="utf-8-sig"),
        "CLAUDE.md", require_backticks=True)
    for glob in _MECHANISM_EXTRA_GLOBS:
        for path in sorted(repo_root.glob(glob)):
            claims += mechanism_claims(
                path.read_text(encoding="utf-8", errors="replace"),
                path.relative_to(repo_root).as_posix(), require_backticks=False)
    return claims


def resolve_named_path(rel: str, repo_root: Path) -> Path | None:
    for base in _MECHANISM_PATH_BASES:
        candidate = repo_root / base / rel
        if candidate.is_file():
            return candidate
    return None


def mechanism_claim_problems(
    claims: list[tuple[str, str, str, str]], repo_root: Path
) -> list[str]:
    """具名機械物必須①檔案存在、且②帶 `::Symbol` 時該符號真的是那檔裡的 class/def。"""
    problems: list[str] = []
    for source, rel, symbol, line in claims:
        target = resolve_named_path(rel, repo_root)
        if target is None:
            problems.append(
                f"{source} 指名一個不存在的機械物 {rel}（三個解析基準 "
                f"{_MECHANISM_PATH_BASES} 皆找不到）——假機械物比沒有機械物更糟，"
                f"讀者會以為這件事有人在守。出處：{line[:100]}")
            continue
        if not symbol or target.suffix != ".py":
            continue
        body = target.read_text(encoding="utf-8", errors="replace")
        for seg in re.split(r"::|\.", symbol):
            if seg and not re.search(rf"^\s*(?:class|def)\s+{re.escape(seg)}\b", body, re.M):
                problems.append(
                    f"{source} 指名 {rel}::{symbol}，但 `{seg}` 不是該檔裡的 class／def "
                    f"⇒ 指標已因改名或搬家靜默失效。出處：{line[:100]}")
    return problems


def iron_law3_topic_pairs(text: str) -> list[tuple[str, str, str]]:
    """鐵律三對照表上「主題 × 具名機械物」配對：`(主題鍵, 相對路徑, 原列)`。

    只認 `|` 起頭的表格列、且**只看第 1 欄（觸發項）**判主題——第 3 欄常提到別列的
    檔名，拿整列比對會把配對算錯。
    """
    pairs: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        keys = [k for k in _IRON_LAW3_TOPIC_KEYWORDS if k in cells[0]]
        if not keys:
            continue
        for _src, rel, _sym, _ln in mechanism_claims(
                cells[1], "iron-law-3", require_backticks=True):
            for key in keys:
                pairs.append((key, rel, line))
    return pairs


def iron_law3_trigger_rows(text: str) -> list[list[str]]:
    """鐵律三對照表的**資料列**（每列切成欄）——現查，不寫死列數。

    界定方式與 `test_adr_xplat001_c1c2_lock.scan_table_lines()` 同構：自表頭列起、
    遇第一個非 `|` 起頭行止（**同一段連續 markdown 表格**），再濾掉 `|---|` 分隔列。
    被空行截出表格的列不算數——它在 GitHub 上本來就已經不再渲染成表格列。
    """
    lines = text.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if ln.startswith(_IRON_LAW3_TABLE_HEAD)), None)
    if start is None:
        return []
    rows: list[list[str]] = []
    for ln in lines[start + 1:]:
        if not ln.startswith("|"):
            break
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) < 2 or not set(cells[0]) - set("-: "):
            continue                                   # 分隔列／空首欄
        rows.append(cells)
    return rows


def iron_law3_coverage(text: str) -> tuple[int, int]:
    """`(有機械物的觸發項數, 已登記的危害類總數)`——兩個量都自 CLAUDE.md 那張表現查。

    「有機械物」＝該列機械物欄**沒有**自陳 `無機械物`。刻意不去解析它指名了哪一支
    （那由 `mechanism_claim_problems()`／`iron_law3_substance_problems()` 兩道判準各自負責），
    本函式只負責把「覆蓋率」變成一個可比較的量測值。
    """
    rows = iron_law3_trigger_rows(text)
    uncovered = [r for r in rows if _IRON_LAW3_NO_MECHANISM in r[1]]
    return len(rows) - len(uncovered), len(rows)


def iron_law3_ratchet_problems(
    text: str, *, covered_floor: int, known_floor: int
) -> list[str]:
    """覆蓋率棘輪的違規清單（空＝通過）。**兩個地板都是參數**，不是讀模組常數。

    🔴 為何非參數化不可（落地當回合就被自己抓到）：注入測試如果拿模組常數當地板，
    它們就只在「真表剛好貼著常數」時才有鑑別力——而本判準解開的正是「分母允許長大」。
    第一版正是那樣寫的：把第 5 類危害誠實登記進表之後，`test_taking_a_scanner_away_is_red`
    與 `test_deleting_a_known_hazard_row_is_red` 兩支**注入測試**當場轉紅，也就是說
    「解開棘輪」這個動作被我自己新寫的兩道鎖擋住了——與本判準要治的病同型、同一回合復發。
    現行形態：注入測試拿**現況**當地板（相對比較），活體判準拿釘住的常數當地板。
    """
    covered, known = iron_law3_coverage(text)
    problems: list[str] = []
    if known < known_floor:
        problems.append(
            f"鐵律三對照表的已登記危害類數 {known} 低於地板 {known_floor} ⇒ 有列被刪掉"
            f"（或表格被空行截斷）。已知危害只能被承認、不能被撤銷；補了掃描器要改的是"
            f"該列的機械物欄，不是把整列拿掉")
    if covered < covered_floor:
        problems.append(
            f"鐵律三覆蓋數 {covered}/{known} 低於地板 {covered_floor} ⇒ 有掃描器被拆掉，"
            f"或該列被改回自陳「{_IRON_LAW3_NO_MECHANISM}」。覆蓋只准往上：補了新掃描器"
            f"就把 _IRON_LAW3_COVERED_FLOOR 一起往上釘")
    return problems


def iron_law3_substance_problems(text: str, repo_root: Path) -> list[str]:
    """具名檔案必須**真的在守該列的主題**（關鍵詞佐證）。"""
    problems: list[str] = []
    for key, rel, line in iron_law3_topic_pairs(text):
        target = resolve_named_path(rel, repo_root)
        if target is None:      # 不存在由 mechanism_claim_problems 報，不重複
            continue
        body = target.read_text(encoding="utf-8", errors="replace").lower()
        keywords = _IRON_LAW3_TOPIC_KEYWORDS[key]
        if not any(kw.lower() in body for kw in keywords):
            problems.append(
                f"鐵律三「{key}」列具名 {rel}，但該檔內找不到任何一個該主題關鍵詞 "
                f"{keywords} ⇒ 「檔案在、但守的是別的東西」的實質假機械物。"
                f"出處：{line[:100]}")
    return problems


class TestR74IronLawMechanismAccounting(unittest.TestCase):
    """鐵律三「哪幾項有掃描器」必須是可查的量測值，且不得宣稱不存在的機械物。"""

    _PATH_BASES: tuple[str, ...] = _MECHANISM_PATH_BASES

    def test_named_mechanism_files_all_exist(self) -> None:
        """三面掃描面內都不得指向一個不存在的機械物（假機械物比沒有機械物更糟）。"""
        claims = collect_mechanism_claims(_REPO_ROOT)
        self.assertGreaterEqual(len(claims), 20, "引用面枚舉異常少 ⇒ 本鎖可能已空轉")
        problems = mechanism_claim_problems(claims, _REPO_ROOT)
        self.assertEqual(problems, [], "具名機械物與磁碟不符：\n  " + "\n  ".join(problems))

    def test_scan_surface_covers_all_three_faces(self) -> None:
        """自錨：三面掃描面每一面都必須真的收到東西。

        少了這條，`_MECHANISM_EXTRA_GLOBS` 哪天寫錯或目錄改名，鎖會退回只掃根
        CLAUDE.md 而總數仍然過關（原鎖就是只有那一面）——靜默縮面正是本鎖要治的病。
        """
        sources = {src for src, _rel, _sym, _ln in collect_mechanism_claims(_REPO_ROOT)}
        self.assertIn("CLAUDE.md", sources)
        self.assertTrue([s for s in sources if s.endswith(".py") and s.startswith("tools/")],
                        f"tools/*.py 這一面收不到任何具名機械物宣稱：{sorted(sources)}")
        self.assertTrue([s for s in sources if s.endswith(".json")],
                        f"tools/*.json 這一面收不到任何具名機械物宣稱：{sorted(sources)}")

    def test_a_phantom_mechanism_would_be_caught(self) -> None:
        """鑑別力（注入）：四筆逃逸形態逐一餵進判準，每一筆都必須紅。"""
        self.assertIsNone(resolve_named_path("tools/no_such_scanner_xyz.py", _REPO_ROOT),
                          "合成路徑撞到真實檔，換一個名字")
        cases = {
            "①程式碼註解面": (
                "# 對應機械鎖：`tools/tests/no_such_scanner_xyz.py::TestFoo`", "x.py", False),
            "②.ps1 副檔名": (
                "照 `AutoClaude/tools/no_such_installer_xyz.ps1` 的機械釘建法", "x.md", True),
            "③.json 面": (
                '"由 tools/tests/no_such_scanner_xyz.py 機械釘在一起",', "x.json", False),
            "④符號不存在": (
                "# 對應機械鎖：`tools/tests/test_ps1_bom.py::NoSuchClassXyz`", "x.py", False),
        }
        for label, (text, source, backticks) in cases.items():
            with self.subTest(label):
                claims = mechanism_claims(text, source, require_backticks=backticks)
                self.assertTrue(claims, f"{label}：擷取器抓不到引用 ⇒ 判準沒被考到")
                self.assertTrue(mechanism_claim_problems(claims, _REPO_ROOT),
                                f"{label}：應判紅卻放行")

    def test_backtick_requirement_only_applies_to_the_doc_face(self) -> None:
        """對照組：程式碼面不得因為「沒加反引號」而靜默漏掉（那是 ①③ 的成因之一），
        而活文件面不得因為放寬反引號而把散文裡的假路徑一起收進來。"""
        bare = "# 對應機械鎖：tools/tests/test_ps1_bom.py"
        self.assertTrue(mechanism_claims(bare, "x.py", require_backticks=False))
        self.assertEqual(mechanism_claims(bare, "x.md", require_backticks=True), [])

    def test_code_face_only_reads_mechanism_claim_lines(self) -> None:
        """對照組：程式碼面不是整檔掃——沒有「機械鎖／機械釘」字樣的行一律不收。

        這條把「偽陽性會讓鎖被整道關掉」這個取捨釘住：放寬成整檔掃時本測試會紅。
        """
        self.assertEqual(
            mechanism_claims("# 詳見 tools/lib/ci_liveness.py 的先例", "x.py",
                             require_backticks=False),
            [])

    def test_iron_law3_coverage_only_goes_up_and_the_denominator_may_grow(self) -> None:
        """棘輪的形狀：**覆蓋率**只准上升，分母（已知危害類數）允許長大。

        🔴 本輪改的是**判準形狀**，不是把門檻調大。原判準是單邊計數
        （未覆蓋項數 ≤ 一個常數），它把兩個不同的量綁成同一個數字：
          (甲) 已知危害類裡**還有幾類沒人守** —— 這個確實只准變少；
          (乙) 我們**知道有幾類危害** —— 這個每挖深一輪就會變多，而且變多是好事。
        於是「誠實登記一個新發現的無掃描器危害類」會當場 AssertionError，最省力的滿足
        方式變成「不要記錄新發現」——正是本 repo 判過的「早退／遮蔽，且方向是看起來
        變乾淨」。同型判例已有一次：`CrossPlatform_Scan_Dimensions.md` 的 Scan-H 判準④
        為「每輪必須下降」這個形狀付過學費，該處逐字寫著不要繞回去。

        現行判準＝**兩個各自單邊的量**，未覆蓋數（＝分母−分子）刻意不設上限：
          · 分子（有機械物的觸發項數）只准上升 ⇒ **拆掉一支掃描器即紅**；
          · 分母（已登記的危害類數）只准上升 ⇒ **刪掉一列未覆蓋項來讓數字好看即紅**
            （舊判準反而放行這一招：把列刪了，計數自然就降了）。
        推得的三種編輯行為：新增「已有掃描器」的列 → 兩量皆升，綠；新增「無機械物」的
        列 → 分子不動、分母升，綠（誠實登記不再有代價）；把某列的掃描器拆掉 → 分子降，
        紅。shrink-only 的精神沒有被放寬，只是釘在分子上而不是釘在「未覆蓋數」上。
        """
        text = _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig")
        problems = iron_law3_ratchet_problems(
            text, covered_floor=_IRON_LAW3_COVERED_FLOOR,
            known_floor=_IRON_LAW3_KNOWN_FLOOR)
        self.assertEqual(problems, [], "\n  ".join(problems))

    def test_uncovered_trigger_list_is_shrink_only_and_still_documented(self) -> None:
        """宣告面（常數）與量測面（CLAUDE.md 那張表）必須**雙向**對得上。

        ① 每一個宣告的未覆蓋項都要在表裡有列，且該列標著「無機械物」（原有判準）；
        ② 表裡每一列標著「無機械物」的，都必須有人在常數裡宣告它（本輪補的反向）。
        少了 ②，往表裡加一列未覆蓋項卻不動常數不會有任何訊號，那個常數就會靜默失真——
        而它正是人讀「哪幾類沒人守」的第一站。
        """
        text = _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig")
        rows = iron_law3_trigger_rows(text)
        self.assertTrue(rows, "鐵律三對照表抽不到任何資料列 ⇒ 本鎖已空轉（表頭改了？）")
        for cells in rows:
            if _IRON_LAW3_NO_MECHANISM not in cells[1]:
                continue
            self.assertTrue(
                [item for item in _IRON_LAW3_UNCOVERED if item in cells[0]],
                f"表裡「{cells[0]}」列標著{_IRON_LAW3_NO_MECHANISM}，卻沒有任何一項在 "
                f"_IRON_LAW3_UNCOVERED 宣告它 ⇒ 宣告面靜默失真")
        for item in _IRON_LAW3_UNCOVERED:
            rows = [ln for ln in text.splitlines()
                    if ln.startswith("|") and item in ln]
            self.assertTrue(rows, f"鐵律三對照表缺「{item}」列 ⇒ 覆蓋缺口又變回散文")
            self.assertTrue(
                any("無機械物" in r for r in rows),
                f"「{item}」列未標『無機械物』⇒ 讀者會以為它有人在守（DEF-101-766 的落點）")

    # ── 覆蓋率棘輪的紅綠實測（注入面刻意用**真表**，合成表證明不了對它有牙）──
    @staticmethod
    def _table_bounds(lines: list[str]) -> tuple[int, int]:
        start = next(
            (i for i, ln in enumerate(lines) if ln.startswith(_IRON_LAW3_TABLE_HEAD)), -1)
        if start < 0:
            raise RuntimeError("注入基底已失效：CLAUDE.md 找不到鐵律三對照表的表頭")
        end = start + 1
        while end < len(lines) and lines[end].startswith("|"):
            end += 1
        return start, end

    def _with_extra_row(self, row: str) -> str:
        lines = _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig").splitlines()
        _start, end = self._table_bounds(lines)
        lines.insert(end, row)
        return "\n".join(lines)

    def _live_floors(self) -> dict[str, int]:
        """**現況**當地板——注入測試一律用它，不用模組常數（見
        `iron_law3_ratchet_problems()` docstring：拿常數當地板的注入只在
        「真表剛好貼著常數」時有鑑別力，而本判準解開的正是分母會長大）。"""
        covered, known = iron_law3_coverage(
            _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig"))
        return {"covered_floor": covered, "known_floor": known}

    def test_registering_a_newly_found_uncovered_hazard_stays_green(self) -> None:
        """🔴 這一支就是本輪立案的那件事：**誠實登記**一個新發現的無掃描器危害類。

        改判準之前，這個動作會得到 `AssertionError: 5 not less than or equal to 4`
        ——制度在懲罰誠實。現在它必須是綠的：分子不動、分母 +1，兩個地板都沒被踩。
        """
        floors = self._live_floors()
        text = self._with_extra_row("| 合成新危害 | **無機械物** | 沒有東西會紅 |")
        covered, known = iron_law3_coverage(text)
        self.assertEqual(
            (covered, known), (floors["covered_floor"], floors["known_floor"] + 1),
            "誠實登記應該只動分母")
        self.assertEqual(
            iron_law3_ratchet_problems(text, **floors), [],
            "登記一個新的無掃描器危害類竟然轉紅 ⇒ 制度又在懲罰誠實（本判準的立案理由）")

    def test_registering_a_new_trigger_that_already_has_a_scanner_stays_green(self) -> None:
        """對照：新增一個**已有掃描器**的觸發項，兩個量都升，同樣不得紅。"""
        floors = self._live_floors()
        text = self._with_extra_row(
            "| 合成觸發項 | `tools/tests/test_ps51_compat.py` | 根層 unittest 閘門 |")
        covered, known = iron_law3_coverage(text)
        self.assertEqual(
            (covered, known), (floors["covered_floor"] + 1, floors["known_floor"] + 1))
        self.assertEqual(iron_law3_ratchet_problems(text, **floors), [])

    def test_taking_a_scanner_away_is_red(self) -> None:
        """鑑別力（注入）：把一列的掃描器拿掉改回自陳沒人守 ⇒ 分子降 ⇒ 必紅。

        這是唯一該紅的方向——覆蓋率下降。用真表上真的有掃描器的那一列做注入。
        """
        lines = _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig").splitlines()
        start, end = self._table_bounds(lines)
        victim = next(
            (i for i in range(start + 1, end)
             if lines[i].startswith("| 路徑分隔符 ")), -1)
        self.assertGreater(victim, 0, "注入基底已失效：找不到『路徑分隔符』那一列")
        floors = self._live_floors()
        cells = lines[victim].strip("|").split("|")
        cells[1] = f" **{_IRON_LAW3_NO_MECHANISM}** "
        lines[victim] = "|" + "|".join(cells) + "|"
        text = "\n".join(lines)
        covered, known = iron_law3_coverage(text)
        self.assertEqual(known, floors["known_floor"], "分母不該因為這個注入而變")
        problems = iron_law3_ratchet_problems(text, **floors)
        self.assertTrue(problems, "拆掉一支掃描器仍未轉紅 ⇒ 分子那一釘沒有牙")
        self.assertIn("覆蓋數", problems[0])
        self.assertEqual(covered, floors["covered_floor"] - 1)

    def test_deleting_a_known_hazard_row_is_red(self) -> None:
        """鑑別力（注入）：把一列未覆蓋項整列刪掉 ⇒ 分母降 ⇒ 必紅。

        🔴 這一招在**舊判準下是綠的**（未覆蓋項數從 4 掉到 3，`<= 4` 照樣通過），
        也就是說舊棘輪同時懲罰誠實登記、又放行「把已知危害刪掉」。新判準把它堵住。
        """
        lines = _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig").splitlines()
        start, end = self._table_bounds(lines)
        victim = next(
            (i for i in range(start + 1, end)
             if _IRON_LAW3_NO_MECHANISM in lines[i]), -1)
        self.assertGreater(victim, 0, "注入基底已失效：表內找不到任何未覆蓋列")
        floors = self._live_floors()
        removed = lines.pop(victim)
        text = "\n".join(lines)
        covered, known = iron_law3_coverage(text)
        problems = iron_law3_ratchet_problems(text, **floors)
        self.assertTrue(
            problems, f"刪掉一列已知危害（{removed[:40]}…）仍未轉紅 ⇒ 分母那一釘沒有牙")
        self.assertIn("已登記危害類數", problems[0])
        self.assertEqual(known, floors["known_floor"] - 1)
        self.assertEqual(covered, floors["covered_floor"],
                         "本注入不該動到分子，否則證明不了是分母在說話")


class TestR75IronLawMechanismSubstance(unittest.TestCase):
    """鐵律三具名的機械物必須**真的在守該列的主題**（第 ③ 面：實質假機械物）。

    🔴 為何「檔案存在」不夠：`行尾` 列先前具名的是 `tools/tests/test_ps1_bom.py`，而該檔
    全篇是 .ps1 的 UTF-8 BOM 政策，對 CRLF／行尾**零判準**（實測 `crlf`／`eol`／`\\r\\n`／
    `line ending` 在該檔命中 0）。路徑點得開、檔案打得開，只有讀完才知道守錯東西——
    這比指向一個不存在的檔更難看見，而只斷言存在的鎖照樣放行。
    """

    def test_every_named_mechanism_actually_guards_its_row_topic(self) -> None:
        problems = iron_law3_substance_problems(
            _ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig"), _REPO_ROOT)
        self.assertEqual(problems, [], "鐵律三具名機械物守錯主題：\n  " + "\n  ".join(problems))

    def test_topic_pairing_surface_is_non_empty(self) -> None:
        """自錨：配對面消失（表格改版／欄位換位）時，上一支對任何內容恆綠。"""
        pairs = iron_law3_topic_pairs(_ROOT_CLAUDE_MD.read_text(encoding="utf-8-sig"))
        self.assertGreaterEqual(
            len(pairs), 5,
            f"鐵律三「主題 × 具名機械物」配對只抓到 {len(pairs)} 組 ⇒ 本鎖疑似空轉：{pairs}")
        self.assertEqual(
            {k for k, _rel, _ln in pairs}, set(_IRON_LAW3_TOPIC_KEYWORDS),
            "主題鍵與 CLAUDE.md 表格對不上——補了新掃描器就要同步 _IRON_LAW3_TOPIC_KEYWORDS")

    def test_a_file_that_guards_the_wrong_thing_is_red(self) -> None:
        """鑑別力（注入）＝修前實況：`行尾` 列具名一支只驗 BOM 的鎖 ⇒ 必須紅。

        用真檔而非合成檔：合成檔證明不了「這道判準對 repo 現有的那一支有牙」，而它
        當初放行的正是那一支。
        """
        row = "| 行尾 | `tools/tests/test_ps1_bom.py` | 根層 unittest 閘門 |"
        problems = iron_law3_substance_problems(row, _REPO_ROOT)
        self.assertTrue(
            any("test_ps1_bom.py" in p for p in problems),
            f"守錯主題的具名機械物被放行（這就是修前實況）；實得：{problems}")

    def test_the_corrected_row_is_green(self) -> None:
        """對照組：改指到真的在守行尾的那兩支之後必須綠——否則上一支只是全都判紅。"""
        row = ("| 行尾 | `tools/tests/test_pre_commit_dispatcher_sigpipe.py"
               "::TestPreCommitBlocksCrOnShellScripts` ＋ "
               "`AutoClaude/tools/hooks/check_sh_eol.py` | 同上 |")
        self.assertEqual(iron_law3_substance_problems(row, _REPO_ROOT), [])


# ══════════════════════════════════════════════════════════════════════════════
# R78 ARCH-03／SD-07：具名機械物鎖的第四面 —— **反引號 Python 識別字**
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體（複審逐字指出的逃逸縫）：上面三面判準的擷取器 `_MECHANISM_PATH_RE` 只認
# **帶副檔名的路徑**。於是「以一個**裸識別字**指認機械物」這種寫法完全不在任何鎖的視野內：
#   · R77 的護欄層**檔數**棘輪常數被它自己那一輪刪掉，全庫剩零個賦值定義、十餘個引用
#     （分布十支檔）——**專門偵測懸空引用的那道鎖照樣綠**。
#     （🔴 本段刻意不逐字寫出那個已死的名字：本節新加的判準會把它判成幽靈，而那正是它
#      該有的行為；訂正註記引述假話等於製造新假話——同 R73 已立的紀律。）
#   · 最嚴重的一處：`AutoClaude/tools/check_loc_budget.py` 拿它當「根層 `tools/tests/`
#     不納入 LOC 分級管轄」的正當性依據 ⇒ 一整層數萬行護欄碼的豁免，掛在一個不存在的符號上。
#   · 同源還有一個已移除的測試方法名與一個從未存在的函式名，散在十餘處註解／docstring。
#
# 判準：文字裡以反引號**單獨**框起來的 Python 識別字（三種形狀：前導底線的 ALLCAPS 常數、
# Test 開頭的類名、test_ 開頭的方法名），必須在 repo 的符號索引裡找得到定義，否則就是幽靈。
#
# 三個刻意的設計選擇（都付過偽陽性的學費，別回頭放寬）：
#   ① **只認整段反引號內容就是識別字**：`` `a/b.py::TestFoo` `` 這種形態歸上面三面管，
#      本面不重複收（重複收會讓同一筆違規印兩次，讀者無從判斷是幾個問題）。
#   ② **形狀刻意窄**：ALLCAPS 那一款要求前導底線（環境變數如 PYTHONUTF8 沒有底線開頭，
#      不會被誤收）；`func()` 這種呼叫形態**整類不收**——實測會大量收到 `read_text()`／
#      `sorted()` 這類 stdlib 方法，而偽陽性會讓整道鎖被關掉，那比縮面更糟。
#   ③ **符號索引含模組檔名**：`` `test_ps1_bom` `` 這種「不帶副檔名的模組提及」是本 repo
#      的既有寫法，不是幽靈。
_SYMBOL_CLAIM_RE = re.compile(
    r"`("
    r"_[A-Z][A-Z0-9_]{3,}"            # 私有 ALLCAPS 常數
    r"|Test[A-Z][A-Za-z0-9_]{3,}"     # TestXxx 測試類
    r"|test_[a-z0-9_]{5,}"            # test_xxx 測試方法
    r")`"
)
#: unittest 自己的類名——它們不是本 repo 的符號，卻長得一模一樣。
_SYMBOL_STDLIB_OK: frozenset[str] = frozenset(
    {"TestCase", "TestLoader", "TestResult", "TestSuite", "TestProgram"})
#: 引用面（誰會寫出「指認機械物」的句子）。
#:
#: 🔴 **R79 收斂包擴面（第二條逃逸縫）**：R78 把判準的**token 形狀**由「反引號路徑」擴到
#: 「反引號 Python 識別字」，但引用面自始至終只有 `.py`。實測後果：引發整個 R78 C 包的
#: 那個常數（護欄層檔數棘輪，全庫零定義）當時仍活在 10 支 `docs/` 檔共 14 處，其中
#: `Skipped_Test_Inventory_R76.md` 把它當**現行**約束在陳述，而那個語意早已被推翻
#: ——照著讀的人會把新鎖放到別的樹去（R79 實測這件事已經發生）。
#: 「形狀對了、但那個形狀出現的地方不在掃描面內」＝同一個病的第二個住所。
#:
#: 為何是**活文件白名單**而不是整棵 `docs/`（誠實劃界，不是偷懶）：
#:   · 收錄的四類都是**下一輪會被當指令讀**的檔——成熟度 SSOT、skip 盤點、交棒書、ADR。
#:   · 刻意排除輪次凍結文件（`CrossPlatform_R*_*.md`、`AutoSDD_Defect_Log*`）：它們是
#:     **史料**，寫下當時為真，把它們納入等於逼人竄改歷史記錄（同 `stale-premise-ok:`
#:     豁免存在的理由）。史料裡的死符號改由「讀者看得到輪次號」自行判讀。
_SYMBOL_REF_GLOBS: tuple[str, ...] = (
    "tools/**/*.py", "AutoClaude/tools/*.py",
    "docs/06_quality/CrossPlatform_Maturity_Criteria.md",
    "docs/06_quality/Skipped_Test_Inventory*.md",
    "docs/04_planning/*HANDOFF*.md",
    "docs/04_planning/ADR/*.md",
)
#: 定義面（符號可能住在哪）。刻意比引用面寬：跨層引用（測試提生產碼的常數）是常態。
#:
#: 🔴 **R79 收斂包補三棵樹**（每一棵都是當回合實測抓到的偽陽性來源，不是預防性擴面）：
#:   · `.claude/hooks/*.py`——**整個 hook 層的符號在本索引裡等於不存在**。實證：R79 的
#:     觀測者包在鎖檔裡以反引號指名 `_RC_RESET_RE`（真的定義在
#:     `.claude/hooks/lint_powershell_command.py`），主牙把它判成幽靈符號並讓根層閘門轉紅。
#:     偽陽性比漏報更致命——它會逼下一個人把整道鎖關掉（本檔上方已為此付過學費）。
#:   · `AutoClaude/tests/**/*.py`／`AISDLC_SDD/scripts/**/*.py`——skip 盤點與 ADR 大量以
#:     **模組名**指認測試（`test_pgvector_recall_perf` 這種），那些模組真的存在、只是住在
#:     這兩棵沒被收進來的樹裡。擴面後 20 個此類名字一次消失。
#: 刻意**不**收整棵 `AISDLC_SDD/`：該樹底下有數千支 venv／快取 `.py`（姊妹鎖
#: `test_platform_utils_dedup._scan_repo_py_for` 實測 4,829 支），全掃既慢又得養排除清單。
_SYMBOL_DEF_GLOBS: tuple[str, ...] = (
    "tools/**/*.py", "AutoClaude/tools/**/*.py", "AutoClaude/autoclaude/**/*.py",
    ".claude/hooks/*.py", "AutoClaude/tests/**/*.py", "AISDLC_SDD/scripts/**/*.py")
_SYMBOL_DEF_RE = re.compile(r"^\s*(?:class|def)\s+(\w+)", re.M)
_SYMBOL_ASSIGN_RE = re.compile(r"^\s*(\w+)\s*(?::[^=\n]+)?=", re.M)

#: 🔴 **具名基線豁免**（grandfathered）——形狀與理由逐字沿用本 repo 既有慣例
#: （`test_adr_xplat001_c1c2_lock._BASELINE_WAIVERS`：舊列具名登記、新列一律硬擋）。
#:
#: 為何不是「一上線就全紅」：本判準落地當回合實測，`tools/**` 既有的幽靈符號有數十個
#: 名字、散在六十餘處，全部來自歷輪的重構與改名。鎖若一上線就對它們全紅，下一個人會直接
#: 把鎖關掉／加 `@skip`——那樣連「硬擋新幽靈」這個真正的價值也一起賠掉（R60 為同一個取捨
#: 寫過同一段話）。
#:
#: 兩道自檢確保它不會變成永久豁免（`TestR78GhostSymbolClaims` 各有一支）：
#:   (a) **只准變少**：不在表上的幽靈名一律硬擋，表本身不得因為「順手加一筆」而長大。
#:   (b) **stale 自檢**：表上的名字若①現在解析得到了（有人把符號補回來／改對了），或
#:       ②整個 repo 已經沒有任何一處引用它了，都必須把那一筆**刪掉**，否則紅。
#:       豁免只能因為「還沒清乾淨」而存在，不能因為「沒人記得回收」而存在。
#: 🔴 **R79 收斂包同一次變更的兩個方向**（兩個方向都必須做，只做一半會是假帳）：
#:   · **刪 4 筆**（`_ADDITIONAL_RISKY_NAMES`／`_PG_REAL_ENABLED`／`_SDD_PRESENT`／
#:     `test_enforce_docs_path_blocks_chinese_path_under_cp950`）——定義面擴到三棵新樹之後
#:     它們**解析得到了**，(b) 那道 stale 自檢會直接判紅要求刪除。
#:   · **加 5 筆**（下方標 `R79-docs` 者）——引用面擴到 `docs/` 活文件之後才**第一次看得見**
#:     的存量。這不是「問題變多」而是「視野變大」，同 `_IRON_LAW3_KNOWN_FLOOR` 那條雙單邊
#:     棘輪的立案理由；為了不讓這個藉口被重複使用，加筆的代價由下方
#:     `_GHOST_SYMBOL_BASELINE_CEILING` 這道 shrink-only 天花板承擔（形狀抄
#:     `test_subprocess_encoding_hygiene._ENTRY_WAIVER_CEILING`）。
_GHOST_SYMBOL_BASELINE: frozenset[str] = frozenset({
    "TestDescendantWatcherFinalSyncSample",
    "TestGuardFileCountShrinkOnlyRatchet",   # R79-docs：ADR-XPLAT-002 §8 item 12 的沿革
    "TestMultiGrandchildLockNotPrematurelyStale",
    "_CALL",
    "_CELL",
    "_FROZEN_GUARD_FILE_COUNT",             # R79-docs：R77 退場的檔數棘輪（史料引用）
    "_FROZEN_SDD_VERSION_RE",
    "_FROZEN_VERSION_DIR_RE",               # R79-docs：R66 併入 sdd_latest.py 前的舊名
    "_HAPPY_PATH",
    "_LATEST_PINNED_SHA256",
    "_LATEST_THINNESS_ENROLLED",
    "_LIVE_LOC_ANCHOR",
    "_MY_PIPE_RE",
    "_PENDING_MIGRATION_SITES",
    "_PROVENANCE_FIELDS",
    "_REASSIGN_RE",
    "_ROW_REOPENED_AFTER",
    "_ROW_STILL_OPEN",
    "_SOURCE",
    "_SURVIVED_ID_PATTERNS",
    "_TLC_TRACK_ENROLLED",
    "_TLC_TRACK_RE",                        # R79-docs：R65 Phase 2-A 退場的客製鎖
    "_TRACKED_ACTIONS",
    "_TREE_FLOOR_RATIO",
    "test_ac_matches_sum_of_seven_registries",
    "test_constants_never_increase_versus_head",
    "test_frozen_guard_count_matches_the_worktree",  # R79-docs：同檔數棘輪一併退場
    "test_is_windows_apps_stub_defined_exactly_once",
    "test_latest_install_post_commit_pins_utf8_before_reading_git_common_dir",
    "test_main_separates_vague_rows_from_valid_count_and_does_not_fail",
    "test_only_the_matching_check_reds",
    "test_the_header_boundary_excludes_a_row_that_legitimately_quotes_it",
    "test_untracked_action_is_ignored",
})
#: **shrink-only 天花板**：本表的筆數只准變少。
#: 為何需要它（R79 立案理由）：上方那句「只准變少」在 R78~R79 之間**只是散文**——
#: `test_the_baseline_is_not_stale` 只管「已解析得到／已無人引用」這兩種 stale，
#: 對「順手多登記一筆新幽靈」零訊號，而那正是這道鎖最省力的關法。
#: 擴掃描面而多看見存量時，重釘本值並在交件回報寫出前後值與理由（同 `_FROZEN_GUARD_LINES`
#: 的重釘紀律）；**不得**為了讓一筆新寫下的懸空引用過關而調高它。
_GHOST_SYMBOL_BASELINE_CEILING = 33

_SYMBOL_INDEX_CACHE: dict[str, frozenset[str]] = {}


def python_symbol_index(repo_root: Path) -> frozenset[str]:
    """repo 的 Python 符號索引：`class`／`def` 名 ＋ 賦值目標 ＋ **模組檔名**。

    刻意用正則而不是 AST：AST 對每一支檔都要 parse 一次（實測慢一個量級），而本判準要的
    只是「這個名字在樹裡有沒有被定義過」——過度寬鬆的方向是**漏報**，那比誤報安全
    （誤報會讓鎖被整道關掉，本檔上方已為此付過學費）。
    """
    key = str(repo_root)
    if key in _SYMBOL_INDEX_CACHE:
        return _SYMBOL_INDEX_CACHE[key]
    names: set[str] = set()
    for glob in _SYMBOL_DEF_GLOBS:
        for path in repo_root.glob(glob):
            if "__pycache__" in path.parts:
                continue
            names.add(path.stem)
            body = path.read_text(encoding="utf-8", errors="replace")
            names.update(_SYMBOL_DEF_RE.findall(body))
            names.update(_SYMBOL_ASSIGN_RE.findall(body))
    index = frozenset(names | _SYMBOL_STDLIB_OK)
    _SYMBOL_INDEX_CACHE[key] = index
    return index


def symbol_claims(text: str, source: str) -> list[tuple[str, str, str]]:
    """`(來源, 識別字, 原行)`；只收「整段反引號內容就是識別字」的形態（見設計選擇①）。"""
    return [
        (source, m.group(1), line.strip())
        for line in text.splitlines()
        for m in _SYMBOL_CLAIM_RE.finditer(line)
    ]


def collect_symbol_claims(repo_root: Path) -> list[tuple[str, str, str]]:
    """引用面全部的裸識別字引用（現查，不寫死清單）。含根 `CLAUDE.md`。"""
    claims = symbol_claims(
        (repo_root / "CLAUDE.md").read_text(encoding="utf-8-sig"), "CLAUDE.md")
    for glob in _SYMBOL_REF_GLOBS:
        for path in sorted(repo_root.glob(glob)):
            if "__pycache__" in path.parts:
                continue
            claims += symbol_claims(
                path.read_text(encoding="utf-8", errors="replace"),
                path.relative_to(repo_root).as_posix())
    return claims


def ghost_symbol_problems(
    claims: list[tuple[str, str, str]],
    index: frozenset[str],
    baseline: frozenset[str],
) -> list[str]:
    """解析不到、且不在具名基線內的識別字引用（空＝通過）。"""
    return [
        f"{source} 以反引號指名 `{name}`，但全 repo 的 Python 符號索引裡找不到它的定義"
        f"（class／def／賦值／模組名皆無）⇒ 幽靈符號。R77 的護欄層檔數棘輪常數"
        f"就是這樣活下來的：符號被刪、引用留著，而只認『帶副檔名的路徑』的三面判準看不到它。"
        f"出處：{line[:100]}"
        for source, name, line in claims
        if name not in index and name not in baseline
    ]


def stale_ghost_baseline_problems(
    claims: list[tuple[str, str, str]],
    index: frozenset[str],
    baseline: frozenset[str],
) -> list[str]:
    """具名基線的兩款 stale：已解析得到／已無人引用。皆須刪除該筆登記。"""
    referenced = {name for _src, name, _ln in claims}
    problems = [
        f"`{name}` 已在基線豁免表上，但它現在**解析得到**了（有人把符號補回來或改對了）"
        f"——請把這一筆從 _GHOST_SYMBOL_BASELINE 刪掉，否則餘裕會變成日後的破口"
        for name in sorted(baseline & index)
    ]
    problems += [
        f"`{name}` 在基線豁免表上，但全引用面已經**沒有任何一處**提到它"
        f"——幽靈已清乾淨，請把這一筆刪掉（豁免只能因為「還沒清」而存在）"
        for name in sorted(baseline - referenced - index)
    ]
    return problems


class TestR78GhostSymbolClaims(unittest.TestCase):
    """第四面：以**裸識別字**指認機械物時，那個符號必須真的存在。

    🔴 這一類是 R78 本包最重要的交付。ARCH-03／SD-07 的十餘處逃逸全部從同一個縫出去：
    上面三面的擷取器只認「帶副檔名的路徑」，而「裸常數名」這種寫法既不是
    路徑、也不帶 `::`，於是「專門偵測懸空引用的那道鎖」對它結構上盲。只補個案不補判準，
    同型缺陷下一輪必然再來——本 repo 已有多次同型復發的紀錄。
    """

    def test_no_new_ghost_symbols(self) -> None:
        """主牙：引用面不得出現基線之外的幽靈符號。"""
        claims = collect_symbol_claims(_REPO_ROOT)
        problems = ghost_symbol_problems(
            claims, python_symbol_index(_REPO_ROOT), _GHOST_SYMBOL_BASELINE)
        self.assertEqual(problems, [], "發現幽靈符號：\n  " + "\n  ".join(problems))

    def test_the_baseline_is_not_stale(self) -> None:
        """(b) 兩款 stale 自檢：解析得到了／已無人引用，都必須把登記刪掉。"""
        claims = collect_symbol_claims(_REPO_ROOT)
        problems = stale_ghost_baseline_problems(
            claims, python_symbol_index(_REPO_ROOT), _GHOST_SYMBOL_BASELINE)
        self.assertEqual(problems, [], "基線豁免表已 stale：\n  " + "\n  ".join(problems))

    def test_the_reference_surface_is_not_vacuous(self) -> None:
        """自錨：每一個引用面都必須真的收到東西（靜默縮面＝本家族一再犯的病）。"""
        sources = {src for src, _n, _l in collect_symbol_claims(_REPO_ROOT)}
        self.assertIn("CLAUDE.md", sources)
        self.assertTrue([s for s in sources if s.startswith("tools/tests/")],
                        f"tools/tests 這一面收不到任何裸識別字引用：{sorted(sources)[:10]}")
        self.assertTrue([s for s in sources if s.startswith("tools/") and "/" not in s[6:]],
                        f"tools/ 頂層這一面收不到任何裸識別字引用：{sorted(sources)[:10]}")
        # R79：docs 活文件面。**逐類**斷言而非只看「有沒有 docs/」——四個 glob 任一寫壞
        # 時，其餘三個仍會讓籠統的斷言通過，那正是本家族一再踩到的靜默縮面。
        for face in ("docs/06_quality/CrossPlatform_Maturity_Criteria.md",
                     "docs/06_quality/Skipped_Test_Inventory",
                     "docs/04_planning/ADR/"):
            with self.subTest(face=face):
                self.assertTrue(
                    [s for s in sources if s.startswith(face)],
                    f"{face} 這一面收不到任何裸識別字引用 ⇒ glob 寫壞或檔案改名："
                    f"{sorted(s for s in sources if s.startswith('docs/'))[:10]}")

    def test_the_baseline_never_grows(self) -> None:
        """R79：具名基線的**筆數**只准變少（`_GHOST_SYMBOL_BASELINE_CEILING`）。

        WHY 這一支非有不可：上方兩道 stale 自檢管的是「表上的筆該不該還在」，對
        「表上又多了一筆」零訊號——而「把新寫下的懸空引用登記進豁免表」正是這道鎖
        最省力、也最不像在繞過任何東西的關法。同型判例：`_ENTRY_WAIVER_CEILING`。
        """
        self.assertLessEqual(
            len(_GHOST_SYMBOL_BASELINE), _GHOST_SYMBOL_BASELINE_CEILING,
            f"幽靈符號豁免表由 {_GHOST_SYMBOL_BASELINE_CEILING} 筆長到 "
            f"{len(_GHOST_SYMBOL_BASELINE)} 筆——豁免是欠債不是額度。"
            "正解＝把那個引用改述成正確語意（或改指真的存在的符號）；"
            "真的是「擴掃描面才看見的既有存量」時，重釘本天花板並在交件回報寫出前後值與理由",
        )
        self.assertEqual(
            len(_GHOST_SYMBOL_BASELINE), _GHOST_SYMBOL_BASELINE_CEILING,
            "表已縮短卻沒有同步下修天花板——餘裕就是日後無聲加回去的破口"
            "（同 `_FROZEN_GUARD_LINES` 的 `[基準過時]`）",
        )

    def test_the_ceiling_has_teeth(self) -> None:
        """鑑別力（注入）：多登記一筆 ⇒ 天花板必須說話；少一筆 ⇒ 也要說話（雙邊）。"""
        self.assertGreater(
            len(_GHOST_SYMBOL_BASELINE | {"_A_SYNTHETIC_GHOST_XYZ"}),
            _GHOST_SYMBOL_BASELINE_CEILING,
            "多登記一筆竟然沒有超過天花板 ⇒ 天花板留了餘裕，這道鎖是空的")
        self.assertLess(
            len(_GHOST_SYMBOL_BASELINE - {sorted(_GHOST_SYMBOL_BASELINE)[0]}),
            _GHOST_SYMBOL_BASELINE_CEILING,
            "少一筆竟然沒有低於天花板 ⇒ 下修那一向的相等斷言測不到東西")

    def test_a_hooks_layer_symbol_resolves(self) -> None:
        """R79 回歸鎖：`.claude/hooks/` 的符號必須在索引內（偽陽性＝鎖會被整道關掉）。

        修前實況（當回合實測）：定義面只有三棵樹、不含 hook 層 ⇒ 鎖檔以反引號指名
        `_RC_RESET_RE`（真的定義在 `lint_powershell_command.py`）被主牙判成幽靈符號，
        根層閘門轉紅。用**真符號**而非合成名：合成名證明不了「對 repo 現有的那一支有牙」。
        """
        index = python_symbol_index(_REPO_ROOT)
        self.assertIn(
            "_RC_RESET_RE", index,
            "hook 層的符號不在索引內 ⇒ 任何指名 hook 內常數的鎖檔都會被誤判成幽靈")
        self.assertNotIn(
            "_RC_RESET_RE", _GHOST_SYMBOL_BASELINE,
            "它已解析得到，不該再掛在豁免表上")

    def test_the_symbol_index_is_not_vacuous(self) -> None:
        """自錨：索引垮掉（glob 寫壞／目錄改名）時，主牙會把**每一個**引用判成幽靈——
        那種全紅的鎖一定會被關掉，所以索引崩塌必須先被自己抓到。"""
        index = python_symbol_index(_REPO_ROOT)
        self.assertGreater(len(index), 2000, "符號索引異常少 ⇒ 定義面 glob 可能已失效")
        for anchor in ("_GHOST_SYMBOL_BASELINE", "python_symbol_index", "MIN_TESTS"):
            self.assertIn(anchor, index, f"索引裡找不到 `{anchor}` ⇒ 抽取正則已失效")

    def test_a_deleted_constant_leaves_a_detectable_ghost(self) -> None:
        """鑑別力（注入）＝修前實況重演：R77 那個常數的引用形態必須被判紅。

        🔴 合成字串刻意**接起來**而不是寫成一個字面：本判準的引用面含本檔，寫成完整字面
        會讓上面的活體測試在本檔裡抓到它（自我違規）——這與上一輪那些幽靈引用是同一種
        「寫下來就變成事實」的機制，只是這次方向對我們不利。
        """
        tick = "`"
        ghost = tick + "_NO_SUCH_FROZEN_CONSTANT_XYZ" + tick
        line = f"# 對應機械鎖：{ghost} 是 shrink-only 棘輪，禁止新增鎖檔"
        claims = symbol_claims(line, "x.py")
        self.assertTrue(claims, "擷取器抓不到裸識別字引用 ⇒ 判準沒被考到")
        problems = ghost_symbol_problems(
            claims, python_symbol_index(_REPO_ROOT), _GHOST_SYMBOL_BASELINE)
        self.assertTrue(problems, "幽靈符號被放行 ⇒ 這正是 R77 讓十餘處引用活下來的縫")

    def test_a_real_symbol_is_not_flagged(self) -> None:
        """對照組：真實存在的符號不得被判紅——否則本鎖只是全都判紅（無鑑別力）。"""
        tick = "`"
        line = f"# 對應機械鎖：{tick}MIN_TESTS{tick} 與 {tick}_GHOST_SYMBOL_BASELINE{tick}"
        self.assertEqual(
            ghost_symbol_problems(symbol_claims(line, "x.py"),
                                  python_symbol_index(_REPO_ROOT), frozenset()),
            [])

    def test_path_shaped_claims_are_left_to_the_other_faces(self) -> None:
        """邊界：帶副檔名／帶 `::` 的形態歸前三面管，本面不重複收（免同一筆印兩次）。"""
        self.assertEqual(
            symbol_claims("見 `tools/tests/test_ps1_bom.py::TestBomPolicy`", "x.py"), [])

    def test_a_stale_baseline_entry_is_red(self) -> None:
        """鑑別力（注入）：把一個**真實存在**的符號放進基線 ⇒ stale 自檢必紅。"""
        problems = stale_ghost_baseline_problems(
            [], python_symbol_index(_REPO_ROOT), frozenset({"MIN_TESTS"}))
        self.assertTrue(any("MIN_TESTS" in p for p in problems), problems)

    def test_an_unreferenced_baseline_entry_is_red(self) -> None:
        """鑑別力（注入）：幽靈已清乾淨卻沒把登記刪掉 ⇒ 必紅（豁免不得永久化）。"""
        problems = stale_ghost_baseline_problems(
            [], frozenset(), frozenset({"_NO_LONGER_REFERENCED_XYZ"}))
        self.assertTrue(any("沒有任何一處" in p for p in problems), problems)


# ══════════════════════════════════════════════════════════════════════════════
# R75 訂正：ONBOARDING §7 表① 的 `skipped=N` 格——數字與逐項清單必須同進同退
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體：該格的受鎖 token 只有「N tests OK」（見 `SYNC._SPECS`），`skipped=N` 與
# **其後的逐項清單**明文不在鎖內。後果實測：受鎖 token 每輪被產生器更新，而 `skipped=N`
# 與那份手寫清單自寫下之後從未被核對過；本輪淨增約 33 筆 skip，零機械記帳。
#
# 🔴 為何**不**把那個數字本身做成 live 鎖（誠實的設計裁決，不是偷懶）：
#   ① 結構性不可能在同一次執行內取值——跑在套件**裡面**的測試不可能知道自己這一次跑完
#      的最終 skip 數（`MIN_TESTS` 能鎖是因為它是靜態常數，不是 runtime 結果）。
#   ② 就算改由 runner 事後比對，skip 數**依機器而變**（docker 在不在、pwsh 7 裝沒裝、
#      zsh 有沒有）⇒ 硬相等會在任何一台環境略異的機器上假紅，而假紅的鎖最後一定被關掉。
#   ③ 靜態站點數不是它的替代量：本輪實測 tools/tests 有 11 個「Windows 上會 skip」的
#      站點，卻對應到 32 支已標籤 skip（class 級 decorator 一對多），差 3 倍。
# 故本鎖改守**可稽核性**這三件事（成本近零、零假紅面）：數字只准有一個、必須帶量測日期、
# 且清單必須指向那個每輪都會現場印出的權威來源，而不是自己養一份沒人維護的散文清單。
# 正解的下一步（本輪未做，須動別包持有的檔）：由 `tools/run_root_unittests.py` 在跑完後
# 讀 `result.skipped` 與本格記載值做**告知式對帳**（不同就印出來、不改 rc）。
_SKIPPED_CELL_RE = re.compile(r"`skipped=(\d+)`")
_MEASURED_AT_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
#: 逐項清單的權威來源模組——本格必須指向它，而不是自己列一份。
_SKIP_ITEMIZATION_SOURCE = "windows_skip_tags"


def skipped_cell_problems(onboarding_text: str) -> list[str]:
    """§7 表① `skipped=N` 格的三條可稽核性判準。純函式，可注入合成行。"""
    line = SYNC.anchored_line(onboarding_text, "rootunit-baseline-live:")
    problems: list[str] = []
    hits = _SKIPPED_CELL_RE.findall(line)
    if not hits:
        problems.append(
            "受鎖行上找不到 `skipped=N`——該格被刪或改名，Windows 側因平台語意而失去的"
            "那批覆蓋會再度無處顯形（它本來就不在 live 鎖內，刪掉不會有別的東西轉紅）")
        return problems
    # 🔴 刻意**不**要求「恰 1 次」：受鎖行是一整列，macOS 欄與 Windows 欄各自帶一個
    # `skipped=N` 是**正確**的版面（實測該列同時有 macOS 側與 Windows 側兩個值）。
    # 硬判恰 1 會把正確版面判成違規，而假紅的鎖最後一定被整道關掉。受管 token 的重複
    # 由 `SYNC.prose_problems` 判準(1) 負責，`skipped` 不是受管 token，本鎖不越界。
    if not _MEASURED_AT_RE.search(line):
        problems.append(
            "受鎖行沒有 `YYYY-MM-DD` 形態的量測日期——`skipped=N` 是 dated snapshot，"
            "沒有日期的快照無法判斷落後多久，讀者只能把它當現況引用（本格的原始病灶）")
    if _SKIP_ITEMIZATION_SOURCE not in line:
        problems.append(
            f"受鎖行未指向逐項清單的權威來源 `{_SKIP_ITEMIZATION_SOURCE}`——一旦本格改回"
            f"自己手寫一份分類清單，那份清單就再度零機械記帳（本格已經這樣壞過一次）")
    return problems


class TestR75SkippedCellIsAuditable(unittest.TestCase):
    """`skipped=N` 不在 live 鎖內是刻意的（見上方裁決），但它必須是**可稽核的快照**。"""

    def test_current_onboarding_passes(self) -> None:
        problems = skipped_cell_problems(_ONBOARDING.read_text(encoding="utf-8-sig"))
        self.assertEqual(problems, [], "§7 表① skipped 格不可稽核：\n  " + "\n  ".join(problems))

    def _synth(self, cell: str) -> str:
        return ("# 標題\n"
                f"| 根層 unittest | {cell} | 見左 "
                "<!-- rootunit-baseline-live: 錨點 --> |\n")

    def test_an_undated_hand_written_itemization_is_red(self) -> None:
        """注入＝修前實況：數字沒有量測日期、清單自己手寫在格內 ⇒ 兩條都必須紅。"""
        problems = skipped_cell_problems(self._synth(
            "**1819 tests OK**（`skipped=10`）；10 支全為 POSIX-only 語意：8 支 pgid、"
            "1 支 BSD stat 等價鎖、1 支無 symlink 權限"))
        self.assertTrue(any("量測日期" in p for p in problems), problems)
        self.assertTrue(any(_SKIP_ITEMIZATION_SOURCE in p for p in problems), problems)

    def test_deleting_the_skipped_cell_is_red(self) -> None:
        """注入：`skipped=N` 整格被刪 ⇒ 必須紅（它不在 live 鎖內，沒別的東西會抓）。"""
        problems = skipped_cell_problems(self._synth("**1819 tests OK**"))
        self.assertTrue(any("找不到" in p for p in problems), problems)

    def test_both_platform_columns_carrying_a_skipped_value_is_green(self) -> None:
        """對照組：同一列兩欄各帶一個 `skipped=N` 是**正確**版面，不得判紅。

        少了這條，把判準寫成「恰 1 次」會全綠通過，而它會對現行的雙平台版面假紅。
        """
        self.assertEqual(
            skipped_cell_problems(self._synth(
                "macOS `skipped=15` ／ Windows `skipped=43`（量測時點 2026-08-04；"
                "逐項清單見 tools/lib/windows_skip_tags.py 的 report_all_skips 輸出）")),
            [])

    def test_a_dated_cell_pointing_at_the_live_source_is_green(self) -> None:
        """對照組：三條都滿足時必須綠——否則上面兩支只是全都判紅。"""
        self.assertEqual(
            skipped_cell_problems(self._synth(
                "`skipped=43`（量測時點 2026-08-04；逐項清單見 "
                "tools/lib/windows_skip_tags.py 的 report_all_skips 輸出）")),
            [])


# ══════════════════════════════════════════════════════════════════════════════
# R74：ONBOARDING §7 表③「雲端 CI 狀態」的機械鎖（本輪 P0 的結構解）
# ══════════════════════════════════════════════════════════════════════════════
# 🔴 缺陷本體：§7 表①②量的全是**本機**（六道根層閘門／四棵測試樹／LOC），整節
# **零欄位**承載雲端結論；而 `tools/lib/ci_liveness.py` 的哨兵只查排程軌（`--event
# schedule` / `workflow_dispatch`），push 軌完全不在視野內。於是 R73 收輪時本機全綠、
# `82eee92` 推上去，而**同一個 commit 的 `windows-compat-ci` 在雲端是 failure**
# ——這件事結構上不可能被任何本機機械物報出來。缺的不是新鮮度，是**平面**。
#
# 🔴 **QA-R74-01（BLOCKING）：本鎖的第一版把 `head-sha` 當成「有寫就算」**。實測取證：
# 把該欄換成全零的 40 位 sha，`cloud_status_problems` 仍回 `[]`；全庫搜尋
# `head-sha` 除本檔外**沒有任何生產碼消費它** ⇒ 這個欄位是裝飾品。而新鮮度判準是
# `checked-at < max(measured-at)` 的**日期字串**比較，本 repo 一輪常在同一天內完成
# （R74 的兩個 commit 相隔 8 小時、同一天）⇒「動了本機基線就得重查雲端」這條因果判準
# 在一輪之內結構上不可能觸發。兩層加起來的後果正是 R74 頭號發現的成因本體：
# 錨上記載的雲端結論屬於**上一個** commit，而鎖全綠。
_CLOUD_ANCHOR = "cloud-ci-status:"
_CLOUD_FIELD_RE = re.compile(r"(\w[\w-]*)=([^\s]+)")
_WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"
_PUSH_TRIGGER_RE = re.compile(r"^  push:", re.M)
#: 完整 commit sha 的形態（短 sha 不收：短 sha 會碰撞，且無法唯一定位一個 commit）。
_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
#: 表③ 每一列的 workflow 檔名（列首可帶 blockquote 的 `> `）。
_CLOUD_ROW_WF_RE = re.compile(r"^>?\s*\|\s*`([\w.-]+\.yml)`\s*\|")
_YML_RE = re.compile(r"[\w.-]+\.yml")


def _git(*args: str) -> subprocess.CompletedProcess[str] | None:
    """跑一次 git；git 不存在／逾時一律回 None（呼叫端須把 None 當「未驗證」）。

    🔴 為何不讓 git 缺席變成紅：本鎖跑在根層 unittest 閘門上，而該閘門也在**沒有 git
    的環境**（容器內、tarball 解出來的樹）跑過。把「取證載具不在」當成「事實為假」是
    本 repo 反覆記載的誤讀形態（`DEF-101-756`：本機沒有心跳檔 ≠ 該平台沒跑 nightly）。
    未驗證與違規必須分開回報。
    """
    try:
        return subprocess.run(["git", *args], cwd=str(_REPO_ROOT), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None


def _repo_history_is_verifiable() -> bool:
    """完整歷史才驗得動「這個 sha 是不是真 commit」。

    shallow clone（`actions/checkout` 預設 `fetch-depth: 1`）只有 HEAD 一個 commit，
    對「錨記載的是上一個 commit」這種**正常且合法**的狀態會解不出物件 ⇒ 在那種環境
    硬判紅就是製造與環境相關的假紅。故 shallow 一律降級為未驗證。
    """
    r = _git("rev-parse", "--is-shallow-repository")
    return bool(r and r.returncode == 0 and r.stdout.strip() == "false")


def _head_commit() -> str | None:
    """當前 HEAD 的 sha；解不出回 None。

    刻意用 HEAD 而非任何 remote-tracking ref：HEAD 是**被測 commit 自己**，在 CI 與本機
    都指向同一個東西；remote ref 會在 push 的那一瞬間前進，拿它當判準對象即不可滿足
    （見 `cloud_pending_problems` 的教訓段）。
    """
    r = _git("rev-parse", "HEAD")
    out = r.stdout.strip() if r and r.returncode == 0 else ""
    return out if _FULL_SHA_RE.match(out) else None


def _commit_iso_time(sha: str) -> str | None:
    """該 commit 的 committer 時間（ISO8601 帶時區）；解不出回 None。"""
    r = _git("show", "-s", "--format=%cI", sha)
    if r is None or r.returncode != 0:
        return None
    out = r.stdout.strip()
    return out or None


def cloud_sha_problems(fields: dict[str, str]) -> list[str]:
    """`head-sha` 必須是**本 repo 真的有的、且是 HEAD 祖先**的完整 commit sha。

    三層，前一層過了才驗下一層：
      ③ 形態＝恰 40 位小寫 hex，且不得全為同一個字元（全零那種佔位值）。**純字串判準、
         零環境相依**——QA 實測的「換成全零仍綠」由這一層單獨消滅，不依賴 git 在不在。
      ④ 該 sha 在本 repo 解析得出 commit 物件。
      ⑤ 該 commit 是 HEAD 本身或 HEAD 的祖先——擋「填了別的分支／別的 repo 的 sha」。
    ④⑤ 需要完整歷史；shallow／無 git ⇒ 明說未驗證而不判紅（見 `_git` 的 WHY）。
    """
    sha = fields.get("head-sha", "")
    problems: list[str] = []
    if not _FULL_SHA_RE.match(sha):
        return [f"表③ 錨的 `head-sha={sha!r}` 不是完整 commit sha（須恰 40 位小寫 hex）"
                "——這個欄位存在的意義是唯一定位「這份雲端結論是對哪個 commit 查的」，"
                "填不合形態的值等於沒填"]
    if len(set(sha)) == 1:
        return [f"表③ 錨的 `head-sha={sha}` 是全同字元的佔位值，不是真 commit"
                "——QA-R74-01 的實測就是把它換成全零而本鎖仍全綠"]
    if not _repo_history_is_verifiable():
        return problems      # shallow／無 git：④⑤ 未驗證，不判紅
    r = _git("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
    if r is None or r.returncode != 0:
        problems.append(
            f"表③ 錨的 `head-sha={sha[:12]}…` 在本 repo 解析不出 commit 物件"
            "（本 repo 有完整歷史，故這不是 shallow clone 造成的）⇒ 那份雲端結論"
            "所宣稱的 commit 不存在，整列判讀無從複驗")
        return problems
    anc = _git("merge-base", "--is-ancestor", sha, "HEAD")
    if anc is not None and anc.returncode not in (0,):
        problems.append(
            f"表③ 錨的 `head-sha={sha[:12]}…` 不是 HEAD 本身也不是 HEAD 的祖先"
            "⇒ 它來自別的分支或別的 repo，對「本分支現在該不該收輪」沒有效力")
    return problems


def cloud_red_set_problems(onboarding_text: str, fields: dict[str, str]) -> list[str]:
    """錨的 `red=` 必須逐字等於表③ 裡結論為 failure 的 workflow 集合。

    🔴 這一條是**同日內仍然有效**的那道判準（QA-R74-01 第 2 層）：它比的是**內容**
    而不是日期，所以「同一天內改了表格卻沒改錨」「改了錨卻沒改表格」兩個方向都會紅，
    不受「一輪之內只有一個日期」這件事影響。
    """
    failing: set[str] = set()
    listed: set[str] = set()
    for line in onboarding_text.splitlines():
        m = _CLOUD_ROW_WF_RE.match(line)
        if not m:
            continue
        listed.add(m.group(1))
        cells = [c.strip() for c in line.split("|")]
        if any("failure" in c for c in cells[2:3]):
            failing.add(m.group(1))
    if not listed:            # 表格不在（合成注入語料）⇒ 本條無取值面，交由判準①管
        return []
    declared = set(_YML_RE.findall(fields.get("red", "")))
    if declared == failing:
        return []
    return [f"表③ 錨宣告 `red={sorted(declared)}`，而表格裡結論為 failure 的是 "
            f"{sorted(failing)}——兩者不符即代表有一邊沒跟上。**這一條刻意比內容不比"
            f"日期**：R74 的兩個 commit 同一天，任何以日期為準的新鮮度判準都抓不到"]


def push_triggered_workflows(workflows_dir: Path) -> list[str]:
    """帶 `push:` 觸發的 workflow 檔名（現查，不寫死清單）。

    掃描面現查而非寫死：寫死的清單在「新增一支 push 軌」那天靜默縮面，
    而那正是本鎖要防的病（同 `check_gha_action_versions.py` 掃描面邊界的紀律）。
    """
    out: list[str] = []
    for f in sorted(workflows_dir.glob("*.yml")):
        if _PUSH_TRIGGER_RE.search(f.read_text(encoding="utf-8", errors="replace")):
            out.append(f.name)
    return out


#: `jobs:` 區塊內的 job 名（恰 2 空白縮排）與 **job 層** `continue-on-error: true`
#: （恰 4 空白縮排）。step 層（`steps:` 的 `- ` 條目底下，縮排更深）刻意不收：step 紅
#: 仍會讓 job 紅、run 層看得到；job 層才是「job 紅而 run 仍 conclusion=success」的那種。
_JOB_NAME_RE = re.compile(r"^  ([A-Za-z0-9_-]+):\s*$")
#: 🔴 **不在此另寫一份**（R76 複審 SA-02）：本判準與 `tools/lib/ci_liveness.py` 原本各有
#: 一份逐字相同的正則，兩份同時把「值後面有行尾註解」漏掉，而磁碟上就有一個活體
#: （`autoclaude-pg-e2e-on-label.yml:35`）⇒ 判準⑧ 的「掃描面現查而非寫死」在落地當天
#: 就有一個現查不到的東西。改為共用該檔的 SSOT，任一邊修好兩邊同時得利。
_JOB_FAIL_OPEN_RE = _CI_LIVENESS.JOB_FAIL_OPEN_RE
#: `nightly-red=` 的項目分隔（值內不得有空白——錨是單獨一行、空白即欄位邊界）。
_NIGHTLY_RED_SEP = ","
#: 全綠時的合法值。刻意**不**提供「還沒查」的值：R76-03 的缺陷本體就是這一層從來
#: 沒有人去查（一筆真實 P1 橫跨四輪「雲端全綠」宣稱），開一個 `unchecked` 出口等於
#: 把那個缺陷寫成合法狀態。要嘛去 `gh run view <id> --json jobs` 查一次，要嘛就紅。
_NIGHTLY_RED_CLEAN = "none"
#: 🔴 **R76 複審 ARCH-03 補的兩欄 provenance**。落地首版的判準⑧ 只有三種判定：欄位缺席、
#: 值是 `none`、值裡有現查不到的 job 名——**沒有任何一條在看「那個宣告現在還成不成立」**。
#: 實測四個互相矛盾的值（宣告 windows 紅／宣告 macos 紅／宣告兩支都紅／宣告全綠）全部判綠。
#: 於是兩個方向都失明：①本輪 PKG-B 修好 `windows-nightly-full` 之後，錨仍會逐字宣告它是
#: 紅的而判準照樣綠＝**一句被鎖守著的假話**；②下週換 `macos-nightly-full` 轉紅，一行都不會響。
#: 它買到的是「有人查過一次」，而它替代的正是那個「橫跨四輪沒人讀」的 issue 通道。
#:
#: 修法＝讓這一欄自帶時點，並給它一個**本機算得出來**的過期界線：
#:   · `nightly-run=<run-id>`：查的是哪一次 run。必須逐字出現在表③-b（錨 ↔ 表格綁定，
#:     形同 `red=` ↔ 表格那條），「改了表格忘了改錨」就會紅。
#:   · `nightly-checked-at=<ISO8601 帶時間>`：什麼時候查的。超過 `_NIGHTLY_MAX_AGE_DAYS`
#:     即紅，訊息直接印回填 SOP 第 6 步那段 gh 指令。
#: 🔴 比較對象是**時鐘**與**本 commit 的檔案內容**，不是 `origin/main`——任何 commit
#: 上照 SOP 查一次就綠，不會落入 R75 那個自我指涉陷阱
#: （見 `TestR75CloudCriteriaAreSatisfiableAtAnyCommit`）。
#: `none` 同樣必須帶 provenance：否則「沒查」與「查過全綠」在錨上長得一模一樣。
_NIGHTLY_RUN_FIELD = "nightly-run"
_NIGHTLY_CHECKED_FIELD = "nightly-checked-at"
_NIGHTLY_RUN_RE = re.compile(r"^\d{6,}$")
#: 排程軌是**週頻**（兩支 compat-CI 的 cron）⇒ 14 天＝最多兩個週期沒人回來看。
#: 取更大就等於容許「一個月前查的」還算新鮮，那正是本判準要治的病；取更小會在正常
#: 輪距內製造噪音。過期時的處置成本＝跑一次 SOP 第 6 步的 gh 指令（秒級）。
_NIGHTLY_MAX_AGE_DAYS = 14


def cloud_fail_open_jobs(workflows_dir: Path) -> list[str]:
    """`<workflow>.yml:<job>` — 帶 **job 層** `continue-on-error: true` 的 job（現查）。

    WHY（R76-03）：表③ 記的是 run 層 `conclusion`，而 job 層 `continue-on-error: true`
    讓那個 job 紅掉時 run 仍是 `success` ⇒ 表③ 六列全 ✅ 與「裡面有 job 是紅的」可以
    同時為真。該通道在本 repo 已實測**零讀者**（唯一顯形處是一張沒人看的 GitHub issue），
    一筆真實 P1 因此橫跨數輪的「雲端全綠」宣稱。

    掃描面現查而非寫死：寫死清單在「某支 workflow 新增一個 fail-open job」那天靜默縮面
    （同 `push_triggered_workflows` 的紀律）。
    """
    found: list[str] = []
    for f in sorted(workflows_dir.glob("*.yml")):
        in_jobs, job = False, None
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("jobs:"):
                in_jobs, job = True, None
                continue
            if line and not line[0].isspace():
                in_jobs, job = False, None
                continue
            if not in_jobs:
                continue
            m = _JOB_NAME_RE.match(line)
            if m:
                job = m.group(1)
            elif job and _JOB_FAIL_OPEN_RE.match(line):
                found.append(f"{f.name}:{job}")
    return sorted(set(found))


def _nightly_provenance_problems(
    fields: dict[str, str], onboarding_text: str, now: datetime.datetime,
) -> list[str]:
    """判準⑧-b：`nightly-red` 的 provenance（哪一次 run／何時查的）＋ 過期帶。

    純函式（`now` 由呼叫端注入）——時鐘是本判準唯一的外部輸入，注入才驗得了兩個方向。
    """
    problems: list[str] = []
    run_id = fields.get(_NIGHTLY_RUN_FIELD, "")
    checked = fields.get(_NIGHTLY_CHECKED_FIELD, "")
    sop = ("處置＝跑一次 §7 回填 SOP 第 6 步那段 `gh run list --event schedule` ＋ "
           "`gh run view <id> --json jobs`，把結果填進表③-b，並把 "
           f"`{_NIGHTLY_RUN_FIELD}=`／`{_NIGHTLY_CHECKED_FIELD}=` 一併更新")
    if not _NIGHTLY_RUN_RE.match(run_id):
        problems.append(
            f"表③ 錨的 `{_NIGHTLY_RUN_FIELD}=` 缺席或形態不合法（實得 {run_id!r}，"
            f"預期是 `gh run list` 回的那串 databaseId 純數字）。沒有它，`nightly-red` "
            f"就只是一句沒有時點也沒有出處的斷言——它宣告的紅可能早就修好了、"
            f"新的紅也不會有人補進來。{sop}")
    elif run_id not in onboarding_text:
        problems.append(
            f"表③ 錨宣告 `{_NIGHTLY_RUN_FIELD}={run_id}`，但 §7 表③-b 裡找不到這個 run id "
            f"⇒ 錨與表格有一邊沒跟上（同 `red=` ↔ 表格那條判準，比的是內容不是日期）。{sop}")
    if not checked:
        problems.append(
            f"表③ 錨缺 `{_NIGHTLY_CHECKED_FIELD}=`（帶時間的 ISO8601，例 "
            f"`2026-08-05T14:30:00+08:00`）⇒ 這一欄沒有新鮮度，「查過一次」與「三個月前"
            f"查過一次」在錨上長得一樣。{sop}")
        return problems
    try:
        stamp = datetime.datetime.fromisoformat(checked)
    except ValueError:
        problems.append(
            f"表③ 錨的 `{_NIGHTLY_CHECKED_FIELD}={checked}` 不是合法 ISO8601。{sop}")
        return problems
    if stamp.tzinfo is None:
        problems.append(
            f"表③ 錨的 `{_NIGHTLY_CHECKED_FIELD}={checked}` 沒有時區 ⇒ 跨平台／跨時區讀者"
            f"對同一個字串會算出不同的年齡。請帶時區偏移。{sop}")
        return problems
    age = (now - stamp).days
    if age > _NIGHTLY_MAX_AGE_DAYS:
        problems.append(
            f"表③ 錨的 `{_NIGHTLY_CHECKED_FIELD}={checked}` 已是 {age} 天前（上限 "
            f"{_NIGHTLY_MAX_AGE_DAYS} 天＝排程軌兩個週期）⇒ `nightly-red` 現值只是一句"
            f"過期的宣稱：它說的紅可能已經修好、新的紅也不會有人補進來。{sop}")
    if stamp > now + datetime.timedelta(days=1):
        problems.append(
            f"表③ 錨的 `{_NIGHTLY_CHECKED_FIELD}={checked}` 在未來 ⇒ 一次沒發生過的查核"
            f"（`[[no-fabricated-tool-output]]`）")
    return problems


def cloud_nightly_red_problems(
    fields: dict[str, str], workflows_dir: Path,
    onboarding_text: str = "", now: datetime.datetime | None = None,
) -> list[str]:
    """判準⑧：凡存在 fail-open job，錨就必須帶 `nightly-red=`，且值只能是現查得到的。

    語意＝「那些 run 層看不見紅的 job，這一次查核的**真實 job 層結論**」。全綠寫
    `none`；有紅就逐項寫 `<workflow>.yml:<job>`（多筆以半形逗號相接，值內不得有空白）。

    🔴 **比較對象只能是被測 commit 自己看得到的東西**（R75 頭號教訓）：本判準比的是
    「錨宣告的集合」↔「本 commit 的 workflow 檔現查出的 fail-open job 集合」，兩者都
    住在被測 commit 內 ⇒ 任何 commit 上都滿足得了。它**不**去問「雲端那一次 run 的 job
    到底是什麼結論」——那要拿一個 push 之後才確定的值來比，正是結構上不可滿足的形態
    （見 `cloud_pending_problems` 的教訓段與 `TestR75CloudCriteriaAreSatisfiableAtAnyCommit`）。
    去雲端查那一半的歸宿是回填 SOP，不是 CI 測試。

    誠實劃界（兩層，缺一不可）：
      · 本判準管得住「有沒有查、宣告的 job 名對不對、是哪一次 run、多久以前查的」，
        **管不住**「查到的結論是不是照實填的」——那與表③ 其他列同屬人寫入的事實，
        靠的是回填 SOP 與取證紀律。
      · 它**不去雲端對帳**。過期帶保證的是「有人在 N 天內查過並留下 run-id」，不是
        「此刻雲端的狀態就是錨上寫的那樣」。這一段（R76 複審 ARCH-03 要求補的劃界）
        原文完全沒有，於是一句沒有清除路徑的宣告看起來像一道會過期的鎖。
    """
    fail_open = cloud_fail_open_jobs(workflows_dir)
    if not fail_open:
        return []            # 無 fail-open job ⇒ 本欄無取值面（不是「通過」，是不適用）
    problems = _nightly_provenance_problems(
        fields, onboarding_text, now or datetime.datetime.now(datetime.UTC))
    declared = fields.get("nightly-red", "")
    if not declared:
        return problems + [
            "表③ 錨缺 `nightly-red=`——run 層 `conclusion` 看不見 job 層 "
            f"`continue-on-error: true` 的紅，現查有 {len(fail_open)} 個這種 job："
            f"{fail_open}。處置：`gh run view <run-id> --json jobs` 查它們的真實結論，"
            f"全綠就寫 `nightly-red={_NIGHTLY_RED_CLEAN}`，有紅就逐項寫 "
            f"`<workflow>.yml:<job>`（半形逗號相接）"
        ]
    if declared == _NIGHTLY_RED_CLEAN:
        return problems
    unknown = [x for x in declared.split(_NIGHTLY_RED_SEP) if x not in fail_open]
    if not unknown:
        return problems
    return problems + [
        f"表③ 錨的 `nightly-red=` 列了 {unknown}，而現查帶 job 層 continue-on-error 的"
        f"只有 {fail_open} ⇒ 兩邊有一邊沒跟上（job 改名／被移除／打錯字）。全綠請寫 "
        f"`{_NIGHTLY_RED_CLEAN}`，不要留一個指向不存在 job 的宣告"
    ]


def parse_cloud_fields(anchor_tail: str) -> tuple[dict[str, str], list[str]]:
    """錨尾解析成 `({欄位: 值}, 問題清單)`；同一欄位出現 ≥2 次一律 **fail-loud**。

    🔴 WHY fail-loud 而不是沿用「取最後一個」（R75 落地當回合被自己咬到，實測取證）：
    原版是 `dict(_CLOUD_FIELD_RE.findall(...))`，而錨是**單獨一行**、機器欄位與人讀散文
    同住那一行。我為了說明 pending 的用法，在同一行散文裡寫了一個 `pending=<sha>…` 字樣，
    它就**靜默覆蓋**掉真正的欄位值，判準於是拿一個帶省略號的字串去比 sha ⇒ 假紅，而錯誤
    訊息還印著一個看起來正確的值（`pending=a371068…` vs `origin/main=a371068448a5…`
    ——兩者其實是同一個 commit）。

    這與根 CLAUDE.md 那條「已橋接的 hook 名稱不得與射程字樣同行」是**同一個病**：逐行
    substring 判準遇上同一行的散文。那邊的解是把文件寫成可精確判定，這邊的解是讓歧義
    **當場 fail-loud**——兩者都不是「把判準放寬」。少了這一條，下一個在錨上寫說明文字的
    人會再踩一次，而症狀是一個指著正確值卻說它不對的假紅（最難查的那種）。
    """
    fields: dict[str, str] = {}
    problems: list[str] = []
    for key, value in _CLOUD_FIELD_RE.findall(anchor_tail):
        if key in fields and fields[key] != value:
            problems.append(
                f"表③ 錨的 `{key}=` 在同一行出現 ≥2 次且值不同（`{fields[key]}` 與 "
                f"`{value}`）⇒ 機器讀到的是最後一個，而那通常是散文裡的舉例。"
                f"處置：說明文字裡不要寫出 `{key}=<值>` 這種可被解析的字樣，改寫成"
                f"「本錨的 `{key}` 欄」")
            continue
        fields.setdefault(key, value)
    return fields, problems


def cloud_status_problems(onboarding_text: str, workflows_dir: Path) -> list[str]:
    """§7 表③ 的三條判準；回傳違規說明（空＝通過）。純函式，可注入。"""
    problems: list[str] = []
    anchors = [ln for ln in onboarding_text.splitlines() if _CLOUD_ANCHOR in ln]
    if len(anchors) != 1:
        return [f"`{_CLOUD_ANCHOR}` 錨在 ONBOARDING.md 命中 {len(anchors)} 次（須恰 1）"
                "——0 次＝表③ 被刪或改名（雲端結論再度無處顯形），≥2 次＝兩份會漂移的真相"]
    fields, dup = parse_cloud_fields(anchors[0].split(_CLOUD_ANCHOR, 1)[1])
    problems += dup
    for required in ("checked-at", "head-sha"):
        if required not in fields:
            problems.append(f"表③ 錨缺 `{required}=`——少了它就無法判斷這份雲端結論是"
                            "什麼時候、對哪個 commit 查的")
    # 判準①：掃描面完整性。帶 push: 觸發的每一支都必須在表③ 出現。
    for wf in push_triggered_workflows(workflows_dir):
        if f"`{wf}`" not in onboarding_text:
            problems.append(
                f"{wf} 帶 `push:` 觸發但 §7 表③ 無對應列 ⇒ 它在雲端紅掉時本機沒有任何"
                "東西會顯形（本輪 P0 的形態）。處置：跑表③ 上方那條 gh 指令補一列")
    # 判準②′：`pending=`（「已推上去、結論尚未進表」）只驗非假性——不驗「是否等於最後
    # 一次 push」，那個問題結構上不可能由住在被測 commit 內的測試回答（見該函式的教訓段）。
    problems += cloud_pending_problems(fields)
    # 判準③④⑤：`head-sha` 綁到一個真實、且屬本分支的 commit（QA-R74-01 第 1 層）。
    problems += cloud_sha_problems(fields)
    # 判準⑥：因果——雲端結論不可能早於它所評的那個 commit 存在的時間。
    problems += cloud_causality_problems(fields)
    # 判準⑦：錨的 `red=` ↔ 表格 failure 列（同日內仍有效，QA-R74-01 第 2 層）。
    problems += cloud_red_set_problems(onboarding_text, fields)
    # 判準⑧：run 層 conclusion 看不見的那一層（job 層 continue-on-error）必須另行宣告，
    # 且該宣告要自帶 provenance（哪一次 run／何時查的）並在過期時轉紅（判準⑧-b）。
    problems += cloud_nightly_red_problems(fields, workflows_dir, onboarding_text)
    return problems


#: 「請現查」哨兵（`None` 是合法的「查不出來」，不能兼作預設）。
_AUTO_REMOTE = object()


def cloud_pending_problems(
    fields: dict[str, str], *, head: object = _AUTO_REMOTE
) -> list[str]:
    """`pending=` 若存在，必須指向一個**真的、屬本分支歷史、且比 `head-sha` 更新**的 commit。

    語意＝「這個 commit 已經推上去，它的雲端結論**尚未**進本表」。它讓「還沒查」成為一個
    可以誠實寫出來、且**合法通過**的狀態，而不必靠把 `checked-at` 填成今天來解紅（那是
    宣稱一次沒發生過的查核）。

    🔴 **本判準刻意只驗「非假性」，不驗「是否等於最後一次 push」——後者結構上不可滿足。**
    R75 落地時我第一版就是拿 `git rev-parse origin/main` 當比較對象，實測後果：main 上
    三支 workflow 全紅（root-infra／windows-compat／macos-compat），而且**每一次 push 都
    必紅**。推導很短：CI 是在 push **之後**跑的，那時 `origin/main` 已經等於被測的那個
    commit；要讓 commit X 通過，X 的檔案內容就必須寫進 X 自己的 sha——而 sha 是 X 內容的
    雜湊，**自我指涉、不可能滿足**。當回合實測重現（HEAD == `origin/main` == `21354c9`
    時跑同一支測試即紅），錯誤訊息還指著兩個其實相等的值。

    ⇒ **教訓（已升為機械物，見 `TestR75CloudCriteriaAreSatisfiableAtAnyCommit`）：判準的
    比較對象若會隨「被該判準所判的那個動作」本身而改變，這個判準結構上不可滿足。**
    「錨有沒有覆蓋最新 push」這個問題**不可能由住在該 commit 內的測試回答**，因為答案依賴
    一個在 commit 之後才確定的值。它的歸宿是 **pre-push／收輪清單**（那個時點 `origin/main`
    尚未前進，比較才有意義，而且「去查雲端」這個動作那時也真的做得到）。

    留在本判準（CI 會跑、對任何 commit 皆可滿足）的四層，全部只問**過去**：
      ① 形態＝恰 40 位小寫 hex 且非全同字元；
      ② 解析得出 commit 物件（shallow／無 git ⇒ 未驗證，不判紅）；
      ③ 是 HEAD 或 HEAD 的祖先——**不得宣稱一個不存在或未來的 commit**；
      ④ 是 `head-sha` 的**嚴格後代**——否則它沒有宣告任何新的未查核狀態，只是雜訊。
    四層都只涉及被測 commit 自己的歷史 ⇒ 任何 commit 上都滿足得了。
    """
    pending = fields.get("pending", "")
    if not pending:
        return []
    problems: list[str] = []
    if not _FULL_SHA_RE.match(pending) or len(set(pending)) == 1:
        return [f"表③ 錨的 `pending={pending!r}` 不是完整 commit sha（須恰 40 位小寫 hex、"
                f"且不得為全同字元的佔位值）——這一欄的意義是唯一定位「哪個 commit 的結論"
                f"還沒進表」，填不合形態的值等於沒填"]
    sha = fields.get("head-sha", "")
    if pending == sha:
        return [f"表③ 錨的 `pending` 與 `head-sha` 是同一個 commit（{sha[:12]}…）⇒ 它沒有"
                f"宣告任何「尚未查核」的狀態。若該 commit 的結論已進表就刪掉 `pending=` 欄；"
                f"若還沒查，`pending` 應指向那個**更新的**、結論還沒進表的 commit"]
    head_sha = _head_commit() if head is _AUTO_REMOTE else head
    if not _repo_history_is_verifiable() or not isinstance(head_sha, str):
        return problems          # 未驗證（同 `_git` 的 WHY），不判紅
    r = _git("rev-parse", "--verify", "--quiet", f"{pending}^{{commit}}")
    if r is None or r.returncode != 0:
        return [f"表③ 錨的 `pending={pending[:12]}…` 在本 repo 解析不出 commit 物件"
                f"（本 repo 有完整歷史）⇒ 它宣稱一個不存在的 commit 尚未查核"]
    if _git("merge-base", "--is-ancestor", pending, head_sha).returncode != 0:
        problems.append(
            f"表③ 錨的 `pending={pending[:12]}…` 不是 HEAD（{head_sha[:12]}…）本身也不是"
            f"它的祖先 ⇒ 錨在宣稱一個**未來或別條分支**的 commit。本欄只能記載已經進入"
            f"本分支歷史的 commit——這一層就是它不能被拿來編造的原因")
    if sha and _git("merge-base", "--is-ancestor", sha, pending).returncode != 0:
        problems.append(
            f"表③ 錨的 `pending={pending[:12]}…` 不是 `head-sha`（{sha[:12]}…）的後代 ⇒ "
            f"它比已查核的那個 commit 還舊，宣告不出任何新的未查核狀態")
    return problems


def cloud_causality_problems(fields: dict[str, str]) -> list[str]:
    """`checked-at` 不得早於 `head-sha` 那個 commit 自己的提交時間，且粒度必須自陳。

    兩條：
      ⑥a **因果**：一份「對 commit X 的雲端結論」不可能在 X 存在之前查到。這一條在
         **同一天內**也有效（比的是時間戳，不是日期字串）——前提是 `checked-at` 真的
         帶了時間成分。
      ⑥b **粒度自陳**：`checked-at` 只寫到日 ⇒ 錨必須帶 `granularity=day` 明說它的
         新鮮度只到「日」。🔴 為何是自陳而不是直接強制寫時間戳：本輪落地時錨上那個
         日期是既有值，補一個「看起來精確」的時間會是憑空編造（`[[no-fabricated-tool-
         output]]`）。自陳讓弱點寫在錨上、下一次回填時無處可躲——SOP 已要求改寫成時間戳。
    """
    sha, checked = fields.get("head-sha", ""), fields.get("checked-at", "")
    if not _FULL_SHA_RE.match(sha) or not checked:
        return []            # 形態問題由 cloud_sha_problems／欄位存在性判準報，不重複
    problems: list[str] = []
    has_time = "T" in checked or " " in checked.strip()
    if has_time and fields.get("granularity") == "day":
        problems.append(
            f"表③ `checked-at={checked}` 已帶完整時間，錨卻還自陳 `granularity=day`"
            "——同一行內資料與自陳互相矛盾，而自陳是**較弱**的那一個 ⇒ 讀者會低估這份"
            "查核的精度。處置：刪掉 `granularity=day` 欄。\n"
            "    🔴 為何這一條非有不可：`granularity=day` 是在 `checked-at` 只寫到日時"
            "被判準逼出來的**誠實補償**；一旦升級成時間戳，它就從補償變成假話，而『補償"
            "留在原地沒人收』正是本輪反覆在治的形態（同 `Spec.historical` 的 stale 自檢）")
    if not has_time and fields.get("granularity") != "day":
        problems.append(
            f"表③ `checked-at={checked}` 只寫到日，錨卻沒有 `granularity=day` 自陳"
            "——本 repo 一輪常在同一天內完成多個 commit（R74 兩個 commit 相隔 8 小時、"
            "同一天），日粒度的新鮮度在一輪之內結構上抓不到「錨落後一個 commit」。"
            "回填時請改寫成帶時間的 `checked-at`；暫時只有日期就必須把粒度寫在錨上")
    commit_time = _commit_iso_time(sha)
    if commit_time is None:
        return problems      # shallow／無 git：⑥a 未驗證（同 cloud_sha_problems 的邊界）
    left = checked if has_time else f"{checked[:10]}T23:59:59"   # 只有日期＝從寬取當日末
    if left[:19] < commit_time[:19]:
        problems.append(
            f"表③ `checked-at={checked}` 早於 `head-sha` 那個 commit 自己的提交時間 "
            f"{commit_time} ⇒ 因果不成立：不可能在一個 commit 存在之前就查到它的雲端"
            f"結論。這通常表示 sha 或時間有一個是抄錯的")
    return problems


class TestR74CloudCiStatusIsRecorded(unittest.TestCase):
    """§7 必須有一處承載雲端 CI 結論，且與本機基線的回填動作因果綁定。"""

    def test_current_onboarding_passes(self) -> None:
        problems = cloud_status_problems(
            _ONBOARDING.read_text(encoding="utf-8-sig"), _WORKFLOWS_DIR)
        self.assertEqual(problems, [], "ONBOARDING §7 表③ 違規：\n  " + "\n  ".join(problems))

    def test_scan_surface_is_live_and_non_empty(self) -> None:
        """自錨：掃描面枚舉不到東西時，判準①會對任何文件恆綠。"""
        wfs = push_triggered_workflows(_WORKFLOWS_DIR)
        self.assertGreaterEqual(len(wfs), 5, f"push 軌枚舉異常少（{wfs}）⇒ 判準①可能空轉")
        self.assertIn("windows-compat-ci.yml", wfs)

    def test_missing_anchor_is_red(self) -> None:
        """刪錨＝靜默縮面。修前實況：整節沒有這個錨，也沒有任何東西會紅。"""
        self.assertTrue(cloud_status_problems("§7 完全沒有雲端欄位", _WORKFLOWS_DIR))

    def test_a_new_push_workflow_that_is_not_recorded_is_red(self) -> None:
        """注入：新增一支 push 軌而表③ 沒補列 ⇒ 必紅（不靠任何人記得）。"""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "brand-new-push-ci.yml").write_text(
                "on:\n  push:\n    branches: [main]\njobs: {}\n",
                encoding="utf-8", newline="\n")
            problems = cloud_status_problems(
                _ONBOARDING.read_text(encoding="utf-8-sig"), d)
        self.assertTrue(any("brand-new-push-ci.yml" in p for p in problems), problems)

    #: 合成語料要用**真** sha，否則 QA-R74-01 補的形態／存在性判準會把它判紅，
    #: 反向對照組就永遠紅而失去意義。git 不在時退回一個合形態的假值（此時 ④⑤⑥a
    #: 本來就降級為未驗證，見 `_git` 的 WHY）。
    @staticmethod
    def _real_sha() -> str:
        r = _git("rev-parse", "HEAD")
        out = r.stdout.strip() if r and r.returncode == 0 else ""
        return out if _FULL_SHA_RE.match(out) else "a" * 39 + "b"

    # ── 判準②′：覆蓋面以 commit 身分為準（取代 R74 的日期字串比較）──────────────
    #: 兩個互不相等的合形態 sha，供注入用（不碰本機真實 remote 狀態）。
    _SHA_A = "a" * 39 + "0"
    _SHA_B = "b" * 39 + "1"

    def test_a_malformed_or_placeholder_pending_is_red(self) -> None:
        """注入：pending 填短 sha／全零／非 hex ⇒ 必紅（同 `head-sha` 的非假性門檻）。"""
        for bad in ("deadbeef", "0" * 40, "ZZ" + "0" * 38):
            with self.subTest(bad):
                self.assertTrue(
                    cloud_pending_problems({"head-sha": self._SHA_A, "pending": bad},
                                           head=self._SHA_B),
                    f"{bad!r} 應判紅卻放行")

    def test_pending_equal_to_head_sha_is_red(self) -> None:
        """注入：pending == head-sha ⇒ 沒宣告任何「尚未查核」狀態，只是雜訊。"""
        problems = cloud_pending_problems(
            {"head-sha": self._SHA_A, "pending": self._SHA_A}, head=self._SHA_B)
        self.assertTrue(any("同一個 commit" in p for p in problems), problems)

    def test_a_pending_naming_a_nonexistent_commit_is_red(self) -> None:
        """注入：形態合法但 repo 裡沒這個 commit ⇒ 宣稱一個不存在的 commit 尚未查核。"""
        if not _repo_history_is_verifiable():
            self.skipTest("本 repo 非完整歷史（shallow／無 git）⇒ 該層依設計未驗證")
        fake = "0123456789abcdef" * 2 + "89abcdef"
        problems = cloud_pending_problems(
            {"head-sha": self._SHA_A, "pending": fake}, head=self._head_or_skip())
        self.assertTrue(any("解析不出 commit" in p for p in problems), problems)

    def test_the_real_anchor_pending_is_green(self) -> None:
        """對照組：文件現值必須綠——否則上面幾支只是把所有輸入都判紅。"""
        fields, dup = parse_cloud_fields(
            SYNC.anchored_line(_ONBOARDING.read_text(encoding="utf-8-sig"),
                               _CLOUD_ANCHOR).split(_CLOUD_ANCHOR, 1)[1])
        self.assertEqual(dup, [])
        self.assertEqual(cloud_pending_problems(fields), [])

    def _head_or_skip(self) -> str:
        head = _head_commit()
        if head is None:
            self.skipTest("取不到 HEAD（無 git）⇒ 該層依設計未驗證")
        return head

    def test_pending_is_green_even_when_head_equals_the_pushed_commit(self) -> None:
        """🔴 **本次 main 三支全紅的直接重現條件**（結構性回歸鎖）。

        CI 是在 push **之後**跑的，所以在 CI 上「最後一次 push 的 commit」就等於**被測的
        那個 commit 自己**。第一版判準拿 remote ref 當比較對象，於是要求 X 的內容寫進 X
        自己的 sha——自我指涉、不可能滿足，**每一次 push 都必紅**。

        本測試把那個條件直接餵進來：`head` 就是被測 commit（＝CI 上的狀態），而錨記載的
        `head-sha`／`pending` 都是它的祖先。這在任何 commit 上都必須綠。
        """
        head = self._head_or_skip()
        fields, _dup = parse_cloud_fields(
            SYNC.anchored_line(_ONBOARDING.read_text(encoding="utf-8-sig"),
                               _CLOUD_ANCHOR).split(_CLOUD_ANCHOR, 1)[1])
        self.assertEqual(
            cloud_pending_problems(fields, head=head), [],
            "在 CI 的條件（被測 commit == 最新 push）下判紅 ⇒ 又是一個不可滿足的判準")

    def test_the_deadlock_scenario_no_longer_forces_a_fabricated_check(self) -> None:
        """🔴 死結回歸鎖（端到端）：舵手 2026-08-05 實測的那個狀態必須可以合法通過。

        場景逐字重現：本輪改了測試樹 → `--write --with-slow` 把 `measured-at` 推到
        比 `checked-at` 更新的一天 → 舊判準在此判紅，而唯一的解紅操作是編造一次查核。
        本測試斷言：**同一份文件**在誠實宣告 pending 之後 rc 面全綠，且**沒有任何欄位
        被改成當天／HEAD**（`checked-at` 與 `head-sha` 逐字保持原值）。
        """
        old_checked, old_sha = "2026-08-04", self._SHA_A
        text = (
            "<!-- snapshot-fingerprints-win32: measured-at=2026-12-31 -->\n"
            f"<!-- cloud-ci-status: checked-at={old_checked} granularity=day "
            f"head-sha={old_sha} pending={self._SHA_B} -->\n"
        )
        fields, dup = parse_cloud_fields(text.split(_CLOUD_ANCHOR, 1)[1])
        self.assertEqual(dup, [])
        self.assertEqual(fields["checked-at"], old_checked, "量測日期被動過＝假宣稱")
        self.assertEqual(fields["head-sha"], old_sha, "覆蓋的 commit 被動過＝假宣稱")
        # 合成 sha 在 repo 裡不存在 ⇒ 只驗前兩層（形態、≠head-sha）；存在性那層由
        # `test_a_pending_naming_a_nonexistent_commit_is_red` 以真 repo 覆蓋。
        self.assertTrue(_FULL_SHA_RE.match(fields["pending"]))
        self.assertNotEqual(fields["pending"], fields["head-sha"])

    def test_prose_on_the_anchor_line_cannot_hijack_a_field(self) -> None:
        """🔴 注入＝R75 落地當回合自己踩到的那一筆：同一行散文裡的 `pending=<值>…`
        字樣曾**靜默覆蓋**真正的欄位值，判準因此拿帶省略號的字串去比 sha ⇒ 假紅，
        而訊息印著一個看起來正確的值（最難查的那種）。現在必須當場 fail-loud。
        """
        tail = (f" checked-at=2026-08-04 head-sha={self._SHA_A} pending={self._SHA_B}"
                f" ／ 說明：本錨的 `pending={self._SHA_B[:7]}…` 即是那個宣告")
        fields, dup = parse_cloud_fields(tail)
        self.assertTrue(any("≥2 次" in p for p in dup), dup)
        self.assertEqual(fields["pending"], self._SHA_B,
                         "第一個（機器欄位）才是真值——不得被散文那個覆蓋")

    def test_duplicate_field_with_the_same_value_is_not_flagged(self) -> None:
        """對照組：同一欄位重複但值相同＝無歧義，不得判紅（否則會逼出無謂的改寫）。"""
        _fields, dup = parse_cloud_fields(
            f" head-sha={self._SHA_A} ／ 再提一次 head-sha={self._SHA_A}")
        self.assertEqual(dup, [])

    # ── QA-R74-01：`head-sha` 從裝飾品變成受驗欄位 ────────────────────────────
    def test_an_all_zero_head_sha_is_red(self) -> None:
        """🔴 QA 實測的那一筆：全零 sha 曾經全綠。這一支是它的墓碑。

        刻意**不**依賴 git：形態層（40 位 hex ＋ 非全同字元）就足以判它，所以本判準
        在 shallow clone 與無 git 的環境同樣有牙。
        """
        problems = cloud_sha_problems({"head-sha": "0" * 40})
        self.assertTrue(any("全同字元" in p for p in problems), problems)

    def test_a_short_or_malformed_head_sha_is_red(self) -> None:
        """注入：短 sha／非 hex／空值一律紅——短 sha 會碰撞，定位不了唯一 commit。"""
        for bad in ("deadbeef", "82eee92", "", "ZZ" + "0" * 38, "A" * 40):
            with self.subTest(bad):
                self.assertTrue(cloud_sha_problems({"head-sha": bad}),
                                f"{bad!r} 應判紅卻放行")

    def test_a_syntactically_valid_but_nonexistent_sha_is_red(self) -> None:
        """注入：形態完全合法、repo 裡卻沒有這個 commit ⇒ 必紅（完整歷史下）。"""
        if not _repo_history_is_verifiable():
            # 🔴 刻意**不**貼 `[POSIX-NATIVE-ONLY]`／`[WINDOWS-NATIVE-ONLY]`：這個 skip
            # 與平台無關（成因是 shallow clone／無 git），貼平台標籤會是假分類。
            self.skipTest("本 repo 非完整歷史（shallow clone 或無 git）⇒ 判準④⑤ 依設計"
                          "降級為未驗證，此注入沒有取值面")
        fake = "0123456789abcdef" * 2 + "01234567"
        self.assertEqual(len(fake), 40)
        problems = cloud_sha_problems({"head-sha": fake})
        self.assertTrue(any("解析不出 commit" in p for p in problems), problems)

    def test_the_real_head_sha_is_green(self) -> None:
        """對照組：真 HEAD 必須綠——否則上面三支只是把所有輸入都判紅。"""
        self.assertEqual(cloud_sha_problems({"head-sha": self._real_sha()}), [])

    def test_a_cloud_conclusion_predating_its_commit_is_red(self) -> None:
        """注入⑥a：`checked-at` 早於該 commit 的提交時間 ⇒ 因果不成立，必紅。

        這一支是**同日內**判準的鑑別力證明：兩個值同一天、只差時分，仍然抓得到。
        """
        sha = self._real_sha()
        commit_time = _commit_iso_time(sha)
        if commit_time is None:
            # 與平台無關（成因是無 git）⇒ 刻意不貼任何 `[*-NATIVE-ONLY]` 平台標籤。
            self.skipTest("取不到 commit 時間（無 git）⇒ 判準⑥a 依設計未驗證")
        same_day_but_earlier = f"{commit_time[:10]}T00:00:00"
        problems = cloud_causality_problems(
            {"head-sha": sha, "checked-at": same_day_but_earlier})
        self.assertTrue(any("因果不成立" in p for p in problems), problems)
        # 反向對照：同日但晚於提交時間 ⇒ 綠
        later_same_day = f"{commit_time[:10]}T23:59:59"
        self.assertEqual(
            cloud_causality_problems({"head-sha": sha, "checked-at": later_same_day}), [])

    def test_a_day_granularity_anchor_must_say_so(self) -> None:
        """注入⑥b：`checked-at` 只寫到日卻沒自陳 `granularity=day` ⇒ 必紅。"""
        sha = self._real_sha()
        self.assertTrue(any(
            "granularity=day" in p
            for p in cloud_causality_problems({"head-sha": sha, "checked-at": "2026-12-31"})))
        self.assertEqual(
            cloud_causality_problems(
                {"head-sha": sha, "checked-at": "2026-12-31", "granularity": "day"}),
            [])

    def test_a_timestamped_anchor_must_not_keep_the_day_granularity_waiver(self) -> None:
        """注入⑥c：升級成時間戳之後，`granularity=day` 就從誠實補償變成假話 ⇒ 必紅。

        這一支防的是「補償留在原地沒人收」——與 `Spec.historical` 的 stale 自檢同型：
        豁免／補償一旦不再需要，繼續留著就是一句與同一行資料矛盾的較弱宣稱。
        """
        sha = self._real_sha()
        stamped = f"{_commit_iso_time(sha) or '2026-12-31T12:00:00+08:00'}"
        problems = cloud_causality_problems(
            {"head-sha": sha, "checked-at": stamped, "granularity": "day"})
        self.assertTrue(any("互相矛盾" in p for p in problems), problems)
        # 反向對照：刪掉該欄即綠（否則判準退化成「帶時間戳就永遠紅」）
        self.assertEqual(
            cloud_causality_problems({"head-sha": sha, "checked-at": stamped}), [])

    # ── 判準⑧（R76-03）：job 層 fail-open 的紅必須另有一欄承載 ────────────────
    def test_fail_open_job_scan_surface_is_live_and_discriminating(self) -> None:
        """自錨＋鑑別力：現查得到 job 層的 fail-open，且**不**把 step 層算進來。

        少了下半條，判準會把「step 失敗但 job 仍紅、run 看得到」的那種也拖進來，
        逼錨去宣告一堆 run 層本來就顯形的東西 ⇒ 誤報的鎖最後一定被整道關掉。
        """
        jobs = cloud_fail_open_jobs(_WORKFLOWS_DIR)
        self.assertTrue(jobs, "現查不到任何 job 層 continue-on-error ⇒ 判準⑧ 已空轉"
                              "（縮排形態變了？還是 workflow 目錄抓錯？）")
        self.assertTrue(
            any(name.endswith("-nightly-full") for name in jobs),
            f"兩支 compat-CI 的 *-nightly-full 是本判準的立案站點，卻不在現查結果內：{jobs}")
        step_level = [x for x in jobs if x.startswith("aisdlc-sdd-arch-fitness.yml")]
        self.assertEqual(
            step_level, [],
            "step 層 `continue-on-error: true`（該 workflow 的 artifact 上傳步驟）被誤收"
            f"成 job 層 ⇒ 判準⑧ 的取值面過寬：{step_level}")

    def test_a_job_level_fail_open_with_a_trailing_comment_is_still_seen(self) -> None:
        """🔴 注入＝R76 複審 SA-02 的活體逃逸形態：值後面加一個行尾註解。

        落地首版的正則寫成 `…true\\s*$`（行尾不得有東西），而 YAML 最普通的寫法就是
        `continue-on-error: true  # 理由`——磁碟上當時就有一個
        （`autoclaude-pg-e2e-on-label.yml`）。它逃掉的方向有兩個：新增的同形態 job
        永遠不必申報；反過來若有人照實把它填進 `nightly-red=` 反而會被判成 unknown 假紅。
        """
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "commented.yml").write_text(
                "on:\n  schedule:\n    - cron: '0 0 * * 0'\n"
                "jobs:\n  deep:\n    runs-on: ubuntu-latest\n"
                "    continue-on-error: true  # 警示不阻塞 merge\n",
                encoding="utf-8", newline="\n")
            self.assertEqual(cloud_fail_open_jobs(d), ["commented.yml:deep"])
            # 反向對照：step 層（縮排更深）仍然不得被收進來。
            (d / "steponly.yml").write_text(
                "jobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n"
                "      - run: x\n        continue-on-error: true  # 上傳失敗不擋\n",
                encoding="utf-8", newline="\n")
            self.assertEqual(cloud_fail_open_jobs(d), ["commented.yml:deep"])
            # 已知邊界（誠實劃界，非疏漏）：`${{ }}` 運算式判不出真假值 ⇒ 出射程。
            (d / "expr.yml").write_text(
                "jobs:\n  maybe:\n    runs-on: ubuntu-latest\n"
                "    continue-on-error: ${{ github.event_name == 'schedule' }}\n",
                encoding="utf-8", newline="\n")
            self.assertEqual(cloud_fail_open_jobs(d), ["commented.yml:deep"])

    def test_the_regex_is_shared_with_ci_liveness_not_copied(self) -> None:
        """兩個消費者必須是**同一個物件**（掌舵者第 2 點：不重複模組）。

        R76 之前是兩份逐字相同的複本，於是同一個瞎點有兩個家、修一個不會修到另一個
        （實測：對 windows-compat-ci 那一行加註解，`ci_liveness` 的 run 層 fail-open
        自白會一起啞掉）。`assertIs` 讓「又抄了一份」在下一次就當場紅。
        """
        self.assertIs(_JOB_FAIL_OPEN_RE, _CI_LIVENESS.JOB_FAIL_OPEN_RE)

    def test_a_missing_nightly_red_field_is_red(self) -> None:
        """注入＝修前實況：錨只記 run 層 conclusion，job 層 fail-open 完全無處顯形。"""
        problems = cloud_nightly_red_problems({"red": "none"}, _WORKFLOWS_DIR)
        self.assertTrue(any("nightly-red" in p for p in problems), problems)

    def test_nightly_red_none_is_green(self) -> None:
        """對照組：查過且全綠是合法且必須可通過的狀態（否則判準退化成永遠紅）。"""
        self.assertEqual(
            cloud_nightly_red_problems(
                self._fields("none"), _WORKFLOWS_DIR, self._TEXT, self._NOW), [])

    def test_nightly_red_naming_a_nonexistent_job_is_red(self) -> None:
        """注入：宣告一個現查不到的 `workflow:job`（改名／打錯字）⇒ 必紅。"""
        problems = cloud_nightly_red_problems(
            self._fields("windows-compat-ci.yml:no-such-job"),
            _WORKFLOWS_DIR, self._TEXT, self._NOW)
        self.assertTrue(any("no-such-job" in p for p in problems), problems)

    def test_nightly_red_naming_a_real_fail_open_job_is_green(self) -> None:
        """對照組：照實填一個現查得到的 fail-open job ⇒ 綠（這才是它的正常用法）。"""
        live = cloud_fail_open_jobs(_WORKFLOWS_DIR)
        self.assertTrue(live, "取值面為空 ⇒ 本對照組沒有意義")
        self.assertEqual(
            cloud_nightly_red_problems(
                self._fields(live[0]), _WORKFLOWS_DIR, self._TEXT, self._NOW), [])

    def test_nightly_red_is_not_required_when_no_job_is_fail_open(self) -> None:
        """邊界：沒有 fail-open job 的 repo 不得被逼著宣告一欄無意義的值。"""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "plain-ci.yml").write_text(
                "on:\n  push:\njobs:\n  build:\n    runs-on: ubuntu-latest\n",
                encoding="utf-8", newline="\n")
            self.assertEqual(cloud_fail_open_jobs(d), [])
            self.assertEqual(cloud_nightly_red_problems({}, d), [])

    # ── 判準⑧-b：provenance ＋ 過期帶（R76 複審 ARCH-03）────────────────────────
    _NOW = datetime.datetime(2026, 8, 5, 12, 0, tzinfo=datetime.UTC)
    _TEXT = "…表③-b 那一列寫著 `30803941764` ／ `1e5214b` …"

    @classmethod
    def _fields(cls, declared: str, *, run: str = "30803941764",
                checked: str = "2026-08-05T01:24:40+08:00") -> dict[str, str]:
        return {"nightly-red": declared, _NIGHTLY_RUN_FIELD: run,
                _NIGHTLY_CHECKED_FIELD: checked}

    def test_nightly_red_without_provenance_is_red(self) -> None:
        """🔴 本組的本體：沒有 run-id／時點的宣告＝「有人查過一次」，不是狀態。"""
        problems = cloud_nightly_red_problems(
            {"nightly-red": "none"}, _WORKFLOWS_DIR, self._TEXT, self._NOW)
        self.assertTrue(any(_NIGHTLY_RUN_FIELD in p for p in problems), problems)
        self.assertTrue(any(_NIGHTLY_CHECKED_FIELD in p for p in problems), problems)

    def test_a_run_id_absent_from_the_table_is_red(self) -> None:
        """錨 ↔ 表③-b 綁定：改了表格忘了改錨（或反之）必紅。"""
        problems = cloud_nightly_red_problems(
            self._fields("none", run="99999999999"),
            _WORKFLOWS_DIR, self._TEXT, self._NOW)
        self.assertTrue(any("找不到這個 run id" in p for p in problems), problems)

    def test_a_stale_check_turns_red_even_when_the_declaration_is_well_formed(self) -> None:
        """🔴 修好之後沒人回來清、或新的紅沒人補進來——兩個方向都靠這一條顯形。

        它比的是**時鐘**，不是 `origin/main`：任何 commit 上照 SOP 查一次就綠
        （見 `TestR75CloudCriteriaAreSatisfiableAtAnyCommit`）。
        """
        later = self._NOW + datetime.timedelta(days=_NIGHTLY_MAX_AGE_DAYS + 2)
        problems = cloud_nightly_red_problems(
            self._fields("none"), _WORKFLOWS_DIR, self._TEXT, later)
        self.assertTrue(any("天前" in p for p in problems), problems)
        # 邊界對照：剛好在帶內就必須是綠的（否則判準退化成「永遠紅」）。
        inside = self._NOW + datetime.timedelta(days=_NIGHTLY_MAX_AGE_DAYS - 1)
        self.assertEqual(
            cloud_nightly_red_problems(
                self._fields("none"), _WORKFLOWS_DIR, self._TEXT, inside), [])

    def test_a_naive_or_future_timestamp_is_red(self) -> None:
        """無時區＝跨時區讀者算出不同年齡；未來時點＝一次沒發生過的查核。"""
        naive = cloud_nightly_red_problems(
            self._fields("none", checked="2026-08-05T01:24:40"),
            _WORKFLOWS_DIR, self._TEXT, self._NOW)
        self.assertTrue(any("沒有時區" in p for p in naive), naive)
        future = cloud_nightly_red_problems(
            self._fields("none", checked="2026-09-30T00:00:00+08:00"),
            _WORKFLOWS_DIR, self._TEXT, self._NOW)
        self.assertTrue(any("在未來" in p for p in future), future)

    def test_the_live_anchor_satisfies_the_new_provenance_criteria(self) -> None:
        """端到端：真實錨（本 commit 的 ONBOARDING.md）現在必須自己過得了這一關。

        沒有這一條，上面幾支都可能在一個「合成語料全綠、真檔其實紅」的世界裡通過。
        """
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        fields, parse_problems = parse_cloud_fields(
            SYNC.anchored_line(text, _CLOUD_ANCHOR).split(_CLOUD_ANCHOR, 1)[1])
        self.assertEqual(parse_problems, [], parse_problems)
        self.assertEqual(
            cloud_nightly_red_problems(fields, _WORKFLOWS_DIR, text), [])

    def test_red_set_must_match_the_table_rows(self) -> None:
        """注入⑦：表格說某支 failure、錨的 `red=` 沒列到 ⇒ 必紅（同日內仍有效）。"""
        table = ("> | `windows-compat-ci.yml` | 🔴 **failure** | `abc1234` | x |\n"
                 "> | `macos-compat-ci.yml` | ✅ success | `abc1234` | — |\n")
        self.assertTrue(any("red=" in p for p in cloud_red_set_problems(
            table, {"red": "macos-compat-ci.yml"})), "錯的 red= 被放行")
        self.assertTrue(cloud_red_set_problems(table, {}), "漏填 red= 被放行")
        self.assertEqual(
            cloud_red_set_problems(table, {"red": "windows-compat-ci.yml"}), [],
            "正確對應卻判紅 ⇒ 判準退化成永遠紅")


#: 「會隨 push 這個動作本身而改變」的 git 參照。判準的比較對象**不得**是其中任何一個。
_MOVING_REF_TOKENS: tuple[str, ...] = (
    "origin/", "@{u", "@{upstream", "ls-remote", "--remotes", "for-each-ref",
)


class TestR75CloudCriteriaAreSatisfiableAtAnyCommit(unittest.TestCase):
    """🔴 **本輪最貴的一課，升為機械物**（比個案修復更重要）：

    **判準的比較對象若會隨「被該判準所判的那個動作」本身而改變，這個判準結構上不可滿足。**

    實證（R75，代價＝main 上三支 workflow 全紅）：表③ 的覆蓋面判準第一版拿
    `git rev-parse origin/main` 當比較對象，要求錨的 `head-sha` 等於它。推導只有兩步——
    CI 在 push **之後**執行，那時 `origin/main` 已經等於被測的那個 commit；於是要讓
    commit X 通過，X 的檔案內容必須寫進 X 自己的 sha，而 sha 是 X 內容的雜湊 ⇒ **自我
    指涉，任何 commit 都滿足不了**。本機 pre-push 時 `origin/main` 還沒前進所以是綠的，
    push 完就紅——「本機全綠、雲端紅」在同一輪內第二次發生，而且兩次都出在**用來防這件事
    的那個機制自己身上**。

    本鎖讀 `cloud_*` 判準家族的**執行碼**（以 AST 去掉 docstring 與註解——教訓必須能寫在
    散文裡，但不得寫進判準），任一支只要碰到 remote-tracking 參照就當場點名。這樣下一個
    人想加「跟 origin 比一下」的判準時，會在寫完的那一刻就紅，而不是在 push 之後才紅。
    """

    def _executable_source(self, fn: object) -> str:
        """函式的執行碼（剝掉 docstring 與註解），用來與散文分開判定。"""
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))  # type: ignore[arg-type]
        node = tree.body[0]
        body = getattr(node, "body", [])
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]  # type: ignore[attr-defined]
        return ast.unparse(tree)

    def _criterion_functions(self) -> dict[str, object]:
        """判準家族現查枚舉（不寫死清單 ⇒ 新增一支判準自動納管）。"""
        return {
            name: obj for name, obj in globals().items()
            if callable(obj) and (name.startswith("cloud_") or name.startswith("_head_")
                                  or name == "parse_cloud_fields")
        }

    def test_scan_surface_is_non_empty(self) -> None:
        """自錨：枚舉不到判準時本鎖恆綠。"""
        names = self._criterion_functions()
        for expected in ("cloud_status_problems", "cloud_pending_problems",
                         "cloud_sha_problems", "cloud_causality_problems"):
            self.assertIn(expected, names, f"判準家族枚舉不到 {expected} ⇒ 本鎖已空轉")

    def test_no_criterion_compares_against_a_ref_that_push_itself_moves(self) -> None:
        offenders: list[str] = []
        for name, fn in sorted(self._criterion_functions().items()):
            code = self._executable_source(fn)
            for token in _MOVING_REF_TOKENS:
                if token in code:
                    offenders.append(f"{name} 的執行碼含 {token!r}")
        self.assertEqual(
            offenders, [],
            "判準拿「會隨 push 前進」的參照當比較對象 ⇒ 在 CI 上對任何 commit 都不可滿足"
            "（R75 實測：main 三支全紅）。改法：只比**被測 commit 自己的歷史**（HEAD 及其"
            "祖先）；「有沒有真的重查雲端」屬 pre-push／收輪清單的職責，不是 CI 測試的。\n  "
            + "\n  ".join(offenders))

    def test_the_lock_would_catch_a_reintroduction(self) -> None:
        """鑑別力：把違規寫法餵進同一個判定路徑必須被抓到（否則上一支恆綠）。"""
        def _relapse() -> list[str]:
            """散文裡提 origin/main 不算違規，執行碼裡才算。"""
            ref = "origin/main"
            return [ref]

        code = self._executable_source(_relapse)
        self.assertNotIn("散文裡提", code, "docstring 沒被剝掉 ⇒ 判準會誤把教訓本身當違規")
        self.assertTrue(any(t in code for t in _MOVING_REF_TOKENS),
                        "違規寫法沒被偵測到 ⇒ 本鎖不具鑑別力")


# ── R76：「已實測不涵蓋」清單必須綁**現行行為**，不得綁字面 token ──────────────
#
# 🔴 缺陷本體（R76-08，「有鎖在守假話」的實例）：`CrossPlatform_Scan_Dimensions.md`
# 硬規則② 的「已實測不涵蓋」清單裡，**否定語意**（「無回執」「零改派」）自 R74 起已被
# `_REASSIGN_NEGATED_RE` 涵蓋，那一項因此成了假話；而釘住它的判準是
# `assertIn("否定語意", rule2)`——綁**字面 token**。兩件事合起來的方向是最壞的那個：
# 照本檔自訂的規矩去訂正文件，根層閘門反而會**轉紅**（該文件自陳的規矩是「被涵蓋時
# 翻紅、強迫改文件」，實況卻是「改文件才紅」）。
#
# 本段是那條規矩的機械面：清單成員與**探針實跑的結果**雙向綁定——探針說「此刻仍未涵蓋」
# 就必須列著，說「已涵蓋」就必須不在清單內。探針跑的是生產判定函式本身
# （`lib.defect_ledger_index.reassign_hit`），所以它不可能與實作各說各話。
_SCAN_DIMS_DOC = _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_Scan_Dimensions.md"
#: 不涵蓋清單的區段界線。刻意用**逐字**界線而非整段搜尋：訂正散文必須說得出「原文錯在
#: 哪」，那句話會提到被移除的形態名，整段搜尋會把訂正文自己判成違規（R73 教訓）。
_UNCOVERED_LIST_HEAD = "**本鎖已實測不涵蓋的形態**"
_UNCOVERED_LIST_TAIL = "本清單非窮舉"


def uncovered_form_list(spec_text: str) -> str | None:
    """硬規則② 那份「已實測不涵蓋」清單的區段原文；抓不到回 `None`（呼叫端 fail-loud）。"""
    head = spec_text.find(_UNCOVERED_LIST_HEAD)
    if head < 0:
        return None
    tail = spec_text.find(_UNCOVERED_LIST_TAIL, head)
    return None if tail < 0 else spec_text[head:tail]


def uncovered_claim_problems(
    spec_text: str, probes: dict[str, tuple[tuple[str, ...], tuple[str, ...]]]
) -> list[str]:
    """清單成員 ↔ 探針實跑結果，**雙向**。

    `probes` ＝ `{形態名: (仍未涵蓋時會買到豁免的狀態欄樣本, 對照組樣本)}`。
    「此刻仍未涵蓋」＝任一樣本仍讓 `reassign_hit()` 回 True（買到豁免）。
    對照組樣本必須回 True，否則探針只是「什麼都回 False」——那種綠沒有鑑別力。
    """
    segment = uncovered_form_list(spec_text)
    if segment is None:
        return ["硬規則② 抓不到「已實測不涵蓋」清單區段（界線字樣被改寫？）"
                "——本判準拒絕靜默通過"]
    problems: list[str] = []
    for form, (samples, controls) in sorted(probes.items()):
        if not any(_LEDGER_INDEX.reassign_hit(c) for c in controls):
            problems.append(
                f"「{form}」的對照組樣本一個都沒買到豁免 ⇒ 探針對任何輸入都回 False，"
                f"「已涵蓋」這個結論是空虛的綠；請重寫對照組：{list(controls)}")
            continue
        still_uncovered = any(_LEDGER_INDEX.reassign_hit(s) for s in samples)
        listed = form in segment
        if still_uncovered and not listed:
            problems.append(
                f"探針實測「{form}」此刻**仍未涵蓋**（樣本 {list(samples)} 仍買得到豁免），"
                f"而規格的不涵蓋清單沒有列它 ⇒ 文件比實作樂觀，讀者會以為那條路已封")
        if listed and not still_uncovered:
            problems.append(
                f"規格的不涵蓋清單仍列著「{form}」，而探針實測它**已被涵蓋**"
                f"（樣本 {list(samples)} 全部不再買到豁免）⇒ 清單裡躺著一句假話。"
                f"處置：把該項從清單移除，並在清單之外寫一句訂正說明它何時被涵蓋"
                f"（訂正文提到形態名不算違規——判定面只有清單區段本身）")
    return problems


class TestR76UncoveredFormListTracksActualBehaviour(unittest.TestCase):
    """🔴 R76-08：「已實測不涵蓋」清單的守門判準必須綁行為，不得綁字面 token。"""

    #: `{形態名: (仍未涵蓋時會買到豁免的樣本, 對照組)}`。樣本一律是**狀態欄**字串
    #: （`reassign_hit()` R74 起只判狀態欄），與生產判定路徑同一個入口。
    _PROBES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
        "否定語意": (
            ("open（無回執）", "open（零改派）", "open（沒有回執）", "open（未改派）"),
            ("open（改派為：未指派）", "open（🔴 R76 回執：已服務）"),
        ),
    }

    def test_the_live_spec_matches_the_probes(self) -> None:
        problems = uncovered_claim_problems(
            _SCAN_DIMS_DOC.read_text(encoding="utf-8-sig"), self._PROBES)
        self.assertEqual(problems, [], "\n  ".join(problems))

    def test_the_scan_surface_is_live(self) -> None:
        """自錨：清單區段抓不到時本判準必須 fail-loud，不得靜默通過。"""
        self.assertIsNotNone(
            uncovered_form_list(_SCAN_DIMS_DOC.read_text(encoding="utf-8-sig")),
            "抽不到不涵蓋清單區段 ⇒ 界線字樣被改寫，本鎖已空轉")
        self.assertTrue(uncovered_claim_problems("（整份規格不見了）", self._PROBES))

    def test_relisting_an_already_covered_form_is_red(self) -> None:
        """注入＝修前實況逐字：清單把「否定語意」列成未涵蓋，而它早已被涵蓋 ⇒ 必紅。"""
        stale = (f"{_UNCOVERED_LIST_HEAD}：**否定語意**（「無回執」「零改派」照樣被當成"
                 f"已載明而放行）、**`status@Rnn` 時點寫法**。{_UNCOVERED_LIST_TAIL}。")
        problems = uncovered_claim_problems(stale, self._PROBES)
        self.assertTrue(any("躺著一句假話" in p for p in problems), problems)

    def test_a_correction_sentence_outside_the_list_is_not_red(self) -> None:
        """反向對照：清單**之外**的訂正說明提到形態名不算違規。

        少了這一條，本鎖會逼人不准寫下「這一項為何被移除」，而那句話正是下一輪讀者
        唯一能據以判斷「清單為什麼變短」的東西（R73：訂正註記不得因此被判成新違規）。
        """
        fixed = (f"{_UNCOVERED_LIST_HEAD}：**`status@Rnn` 時點寫法**。"
                 f"{_UNCOVERED_LIST_TAIL}。\n"
                 f"🔴 訂正：**否定語意**自 R74 起已由 `_REASSIGN_NEGATED_RE` 涵蓋。")
        self.assertEqual(uncovered_claim_problems(fixed, self._PROBES), [])

    def test_the_probe_would_notice_a_regression(self) -> None:
        """鑑別力：探針必須真的在跑生產判定函式（拔掉否定語意處置即應轉為「仍未涵蓋」）。

        不改生產碼的驗法：直接對**否定前綴被拿掉**的等價樣本取值——那正是 R74 修前
        `reassign_hit` 看到的字串形態。它必須回 True，否則「False ⇒ 已涵蓋」這個推論
        其實來自別的原因（例如整個判定被關掉），本鎖的綠就是假的。
        """
        samples, _controls = self._PROBES["否定語意"]
        stripped = [s.replace("無", "").replace("零", "").replace("沒有", "")
                     .replace("未", "") for s in samples]
        self.assertTrue(
            any(_LEDGER_INDEX.reassign_hit(s) for s in stripped),
            f"拿掉否定前綴後仍全部不算改派 ⇒ 探針的 False 來自別的原因：{stripped}")


# ── R76：把 R75 頭號教訓擴到**退場／解除條件**類判準（不限 Python、不限 cloud_ 前綴）──
#
# 🔴 為何非擴不可（同形態第三次復發，而上面那道旗艦鎖結構上抓不到它）：R75 的鎖讀的是
# **本模組內 `cloud_*` 家族的 Python 執行碼**。第三次復發卻住在
# `tools/windows_smoke_local.ps1` 的**註解散文**裡——E3 原文要求「移除該排程任務後，
# `check_scheduled_task_drift.py` 回 rc=0」，而該 checker 的期望值 SSOT
# （`tools/scheduled_task_expectations.json`）**同時列著要被移除的那支任務** ⇒ 執行 E3
# 自己授權的動作必然讓 E3 轉紅。語言不同（PowerShell 註解）、載體不同（散文而非執行碼）、
# 命名不同（沒有 `cloud_` 前綴），三個縫任一個都足以讓上面那道鎖看不見它。
#
# 本段守的是**結構**而不是那一個站點：退場判準若拿「整支工具的 rc／status」當取證，而
# 那支工具的比較對象是一份列了多個實體的期望值 SSOT，則移除其中任一實體必然讓取證轉紅。
# 站點層的鎖由 `tools/tests/test_install_windows_nightly.py::
# TestWindowsSmokeTaskHasWrittenExitCriteria` 承接（該檔逐字釘 E3 的三個方向）；本段刻意
# 只做**家族層**判準，兩者不重複：那支答「E3 這一條現在寫得對不對」，本段答「下一條退場
# 判準寫成同一個形狀時會不會有人說話」。
_EXIT_SECTION_MARKS: tuple[str, ...] = ("退出判準", "退場判準", "退場條件", "解除條件")
#: 判準項目的起頭。兩種形態：註解／散文的 `E1.`，與 **markdown 表格 cell** `| **E1** |`。
#: 🔴 本輪補上表格 cell 那一種：本 repo 最常見的退場判準寫法就是一張 `| 條 | 判準 | 實測 |`
#: 的表，而原正則只認行首 `E<N>.` ⇒ 就算把 `.md` 加進掃描面也是**零命中**（實測 items=0）。
#: 「擴了掃描面卻抽不到東西」比不擴更糟：它看起來像已經覆蓋了。
_EXIT_ITEM_RE = re.compile(r"^\s*(?:\|\s*)?(?:#|//)?\s*\**(E\d+)\**\s*(?:[.．]|\|)")
#: 就地訂正／時代快照的標記。歷史檔逐字保全是本 repo 的明文紀律（帳本列不改寫、
#: 快照欄保留原值），所以判準必須留一條「該列或一筆更新的紀錄載明訂正」的合法出口——
#: 否則擴到 `.md` 的當下就會對一列**刻意保留的歷史快照**永紅，而永紅的閘門會被整個關掉
#: （同 `check_defect_log_crossref.orphan_backlog_problems()` 為硬規則② 設計的出口）。
_EXIT_CORRECTION_MARKS: tuple[str, ...] = ("訂正", "改述", "已改為", "時代快照", "已退場")
#: 「整支工具的判決」——把工具當黑箱讀它的總結論，等於把它的**全部**比較對象綁進判準。
_WHOLE_TOOL_VERDICT_MARKS: tuple[str, ...] = (
    "rc=0", "rc = 0", "rc＝0", "回 0", "status=ok", "全綠", "零違規",
)
#: 收窄量測對象的寫法：逐實體欄位讀法（`.tasks.<name>`）或收窄旗標。任一出現即不成立。
_SCOPE_NARROWED_RE = re.compile(
    r"\.tasks?\.[A-Za-z0-9_]+|--tasks?\b|--expectations\b|--only\b|--filter\b")
#: 期望值 SSOT（`{實體: 期望}` 形態的 JSON，checker 逐實體比對）。現查 glob，不寫死檔名。
_EXPECTATION_SSOT_GLOBS: tuple[str, ...] = ("tools/*expectations*.json",)
#: 會寫下退場判準的文本。**刻意含非 Python**——R76 的復發就住在 `.ps1` 註解裡。
#: 🔴 本輪補三個縫（前兩個是實測缺口、第三個是雙平台不對稱的前瞻補齊）：
#:   ①`docs/**/*.md`／根層 `*.md`——**治理決策的主要住所**，而它整個不在原掃描面內；
#:     同一組 E1／E2／E3 的第二個家就住在 `docs/06_quality/` 的一份 `.md` 表格裡。
#:   ②`AutoClaude/tools/*.sh`（同目錄的 `*.ps1` 有列而 `.sh` 缺席，其中含 mac 側主入口）。
_EXIT_CRITERION_GLOBS: tuple[str, ...] = (
    "tools/*.ps1", "tools/*.sh", "tools/*.py",
    "AutoClaude/tools/*.ps1", "AutoClaude/tools/*.py", "AutoClaude/tools/*.sh",
    "*.md", "docs/**/*.md",
)


def exit_criterion_correction_record(text: str, tag: str) -> str | None:
    """該份文本內是否有一筆**就地訂正／時代快照**紀錄涵蓋這一條判準；有就回傳那一行。

    形態照 `orphan_backlog_problems()` 的既有出口：**同一份文本內、提及該項目代號、
    且帶訂正標記**的行即算數。這條出口不是寬鬆，是必要——本 repo 的歷史列一律逐字保全
    （帳本列不改寫、快照欄保留原值再於下方補訂正塊），沒有這條出口，判準會對一列
    **刻意保留的錯誤快照**永紅。

    誠實劃界（同體例）：**跨列認定條件偏弱**——只要同檔有一行同時提到代號與訂正字樣就
    接受，判不出「那筆訂正講的是不是同一件事」；那需要語意判讀，不在逐行正則的能力內。
    """
    for line in text.splitlines():
        if tag in line and any(m in line for m in _EXIT_CORRECTION_MARKS):
            return line.strip()
    return None


def expectation_ssot_entities(repo_root: Path) -> dict[str, tuple[str, ...]]:
    """`{SSOT 檔名: (它列出的實體名, …)}`——現查，不寫死。

    形態＝JSON 內任一層 `{容器: {實體: {…}}}`（`scheduled_task_expectations.json` 的
    `tasks` 即是）。只認「值也是 dict」的那一層，避免把 `why_each` 這類說明表誤當實體。
    """
    out: dict[str, tuple[str, ...]] = {}
    for pattern in _EXPECTATION_SSOT_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            names = {
                name
                for value in (data.values() if isinstance(data, dict) else ())
                if isinstance(value, dict)
                for name, inner in value.items()
                if isinstance(inner, dict)
            }
            if names:
                out[path.name] = tuple(sorted(names))
    return out


def checker_expectation_ssot(repo_root: Path, ssots: dict[str, tuple[str, ...]]) -> dict[str, str]:
    """`{checker 檔名: 它讀的期望值 SSOT 檔名}`——以 checker 原始碼是否指名該 SSOT 判定。"""
    out: dict[str, str] = {}
    for path in sorted(repo_root.glob("tools/*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        for ssot_name in ssots:
            if ssot_name in source:
                out[path.name] = ssot_name
    return out


def exit_criterion_items(text: str) -> list[tuple[str, str]]:
    """`(項目代號, 項目原文)`——退場判準區塊內逐條編號的項目。

    項目界線＝自 `E<N>.` 那一行起，到下一個項目起頭、或一行「空註解／空白行」為止
    （手法對齊 `test_install_windows_nightly.py` 抽 E3 段的既有作法）。抓不到任何項目
    時回空 list，呼叫端把「檔內有退場判準字樣卻抽不到項目」當掃描面崩塌回報。
    """
    if not any(mark in text for mark in _EXIT_SECTION_MARKS):
        return []
    items: list[tuple[str, str]] = []
    tag, buf = None, []
    for line in text.splitlines():
        m = _EXIT_ITEM_RE.match(line)
        if m:
            if tag:
                items.append((tag, "\n".join(buf)))
            tag, buf = m.group(1), [line]
            continue
        if tag is None:
            continue
        if not line.strip().lstrip("#/").strip():      # 空行／空註解行＝項目結束
            items.append((tag, "\n".join(buf)))
            tag, buf = None, []
            continue
        buf.append(line)
    if tag:
        items.append((tag, "\n".join(buf)))
    return items


def unsatisfiable_exit_criterion_problems(
    text: str, source: str, checker_ssot: dict[str, str],
    ssots: dict[str, tuple[str, ...]],
) -> list[str]:
    """純函式：回傳該份文本內「執行自己授權的動作後必然轉紅」的退場判準項目。

    判準（四條**同時**成立才算違規，寧可漏抓也不製造假紅）：
      ① 該項目屬退場／解除條件區塊，且逐條編號；
      ② 項目內指名一支 checker，而該 checker 的比較對象是一份期望值 SSOT；
      ③ 該 SSOT 列了 **≥2 個實體**（只列一個時，移除它等於整條判準沒有意義，不是本病）；
      ④ 項目以**整支工具的判決**取證（`rc=0`／`status=ok`／「全綠」…）且**沒有**收窄
         量測對象（無逐實體欄位讀法、無收窄旗標）⇒ 該工具的比較對象包含被授權移除的
         那個實體 ⇒ 判準結構上不可滿足。

    ⑤ 該份文本內**沒有**就地訂正／時代快照紀錄涵蓋這一條（見
       `exit_criterion_correction_record()`）——歷史列逐字保全是本 repo 的明文紀律，
       沒有這條出口，判準會對刻意保留的錯誤快照永紅，而永紅的閘門會被整個關掉。

    **已實測涵蓋**（逐項以構造輸入跑過，見 `TestR76ExitCriteriaSurviveTheirOwnAction`）：
      · `.ps1` 註解內的 `E<N>.` 項目要求「移除後 <checker>.py 回 rc=0」（R76 復發原形）；
      · 同形態改用「status=ok」「全綠」措辭；
      · **markdown 表格 cell 形態**（`| **E3** | …回 rc=0 |`，本輪補上——那是本 repo 寫
        退場判準最常見的形狀，而 `.md` 此前整個不在掃描面內）；
      · 反向對照：同一項目改成逐實體讀法（`.tasks.<name>`）或帶收窄旗標 ⇒ 不判紅；
      · 反向對照：同檔已有就地訂正紀錄 ⇒ 不判紅（否則對逐字保全的歷史快照永紅）。
    **已實測不涵蓋**（逐項跑過，並釘成常駐斷言）：
      · **編號形態**只認 `E<N>.` 與 `| **E<N>** |`；`(1)`／`條件一`／無編號的散文抓不到；
      · **訂正紀錄的內容不判讀**：同檔有一行同時提到代號與訂正字樣就放行，判不出那筆
        訂正講的是不是同一件事（跨列認定條件偏弱，同 `orphan_backlog_problems()`）；
      · **比較對象只認期望值 JSON SSOT**：checker 把清單寫死在自己的原始碼裡、或比較
        對象是別的資料形態（資料庫、線上 API）時，本判準無從得知它有幾個實體；
      · **語意層的「授權移除什麼」不做判讀**：本判準以「SSOT 有多個實體 ＋ 取整支 rc」
        這個結構近似它，抓不到「移除的東西不在該 SSOT 內、卻仍與判準耦合」的變體；
      · **收窄的有效性不驗**：項目寫了 `--tasks` 卻傳錯值，本判準照樣放行。
    **未窮舉**：本清單非窮舉，不做「唯一殘餘風險是 X」這類宣稱（R57 判例第 (4) 條）。
    """
    problems: list[str] = []
    for tag, item in exit_criterion_items(text):
        if not any(mark in item for mark in _WHOLE_TOOL_VERDICT_MARKS):
            continue
        if _SCOPE_NARROWED_RE.search(item):
            continue
        if exit_criterion_correction_record(text, tag):
            continue                       # 已有就地訂正／時代快照紀錄（見該函式 docstring）
        for hit in re.findall(r"[\w./\\-]+\.py", item):
            name = PurePosixPath(hit.replace("\\", "/")).name
            ssot = checker_ssot.get(name)
            if ssot is None or len(ssots.get(ssot, ())) < 2:
                continue
            problems.append(
                f"{source} 的退場判準 {tag} 以「{name} 的整支判決」取證，而該工具的比較"
                f"對象是 {ssot}（現列 {len(ssots[ssot])} 個實體：{list(ssots[ssot])}）"
                f"⇒ 一旦執行本判準自己授權的移除動作，被移除的那個實體就會讓該工具轉紅"
                f"，判準結構上不可滿足（R75 頭號教訓的第三種載體）。改法：把量測對象收窄"
                f"到**會存活下來**的那些實體——逐實體欄位讀法（`--json` 後讀 "
                f"`.tasks.<name>`）或收窄旗標（`--tasks`／`--expectations`），"
                f"不要讀整支工具的 rc／status"
            )
    return problems


def repo_exit_criterion_problems(repo_root: Path) -> tuple[list[str], list[str]]:
    """`(問題清單, 掃到判準項目的檔案清單)`——掃描面現查，不寫死檔名。"""
    ssots = expectation_ssot_entities(repo_root)
    checker_ssot = checker_expectation_ssot(repo_root, ssots)
    problems: list[str] = []
    seen: list[str] = []
    for pattern in _EXIT_CRITERION_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="replace")
            if not exit_criterion_items(text):
                continue
            rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
            seen.append(rel)
            problems += unsatisfiable_exit_criterion_problems(
                text, rel, checker_ssot, ssots)
    return problems, seen


class TestR76ExitCriteriaSurviveTheirOwnAction(unittest.TestCase):
    """🔴 R75 頭號教訓的**家族層**承接者：退場／解除條件也適用同一條規則。

    **判準的量測對象若會隨「被它所判的動作」而改變，這個判準結構上不可滿足。**
    上方 `TestR75CloudCriteriaAreSatisfiableAtAnyCommit` 讀的是本模組內 `cloud_*` 家族的
    Python 執行碼；本類別讀的是**任何語言的退場判準散文**——第三次復發正是從那兩個縫
    （非 Python、非 cloud_ 前綴）走掉的。
    """

    def _live(self) -> tuple[list[str], list[str]]:
        return repo_exit_criterion_problems(_REPO_ROOT)

    def test_scan_surface_is_live_and_non_empty(self) -> None:
        """自錨：抽不到任何退場判準項目時本鎖恆綠。"""
        _problems, seen = self._live()
        self.assertTrue(seen, "全 repo 抽不到任何逐條編號的退場判準 ⇒ 本鎖已空轉"
                              "（編號形態變了，或掃描面 glob 沒跟上）")
        self.assertIn("tools/windows_smoke_local.ps1", seen,
                      f"已知站點不在掃描面內 ⇒ 縮面了；實得：{seen}")

    def test_the_expectation_ssot_surface_is_live(self) -> None:
        """自錨：期望值 SSOT 枚舉不到實體時，判準③ 恆不成立 ⇒ 整條鎖靜默失效。"""
        ssots = expectation_ssot_entities(_REPO_ROOT)
        self.assertTrue(ssots, "現查不到任何期望值 SSOT ⇒ 本鎖已空轉")
        multi = {k: v for k, v in ssots.items() if len(v) >= 2}
        self.assertTrue(multi, f"沒有任何 SSOT 列出 ≥2 個實體 ⇒ 判準③ 永不成立：{ssots}")

    def test_no_live_exit_criterion_measures_what_it_removes(self) -> None:
        problems, _seen = self._live()
        self.assertEqual(problems, [], "\n  ".join(problems))

    #: 復發原形的**逐字**骨架（R76 修前的 E3；`tools/windows_smoke_local.ps1` 現已改寫，
    #: 故此處保留一份合成語料，讓鑑別力不依賴磁碟上那個站點是否還壞著）。
    _RELAPSE = (
        "# 🔴 退出判準\n"
        "#   E3. 移除後 Windows 側仍有每日執行級心跳：AutoClaude_Nightly 存在且\n"
        "#       tools/check_scheduled_task_drift.py 回 rc=0（設定沒漂移，會真的跑）。\n"
        "#\n"
    )

    def _probe(self, text: str) -> list[str]:
        ssots = expectation_ssot_entities(_REPO_ROOT)
        return unsatisfiable_exit_criterion_problems(
            text, "PROBE", checker_expectation_ssot(_REPO_ROOT, ssots), ssots)

    def test_the_relapse_form_is_red(self) -> None:
        """注入＝修前逐字原形：拿整支工具的 rc 當退場取證 ⇒ 必紅。"""
        problems = self._probe(self._RELAPSE)
        self.assertTrue(problems, "修前原形沒被抓到 ⇒ 本鎖不具鑑別力")
        self.assertIn("E3", problems[0])
        self.assertIn("scheduled_task_expectations.json", problems[0])

    #: 本輪補上的第二種載體：markdown 表格 cell。這是本 repo 寫退場判準最常見的形狀，
    #: 而 `.md` 此前整個不在掃描面內、且原正則只認行首 `E<N>.` ⇒ 兩層都要補才抓得到。
    _MD_RELAPSE = (
        "## 2.2.3 三條退出判準逐條實測\n"
        "\n"
        "| 條 | 判準原文 | 本輪實測 | 結論 |\n"
        "|---|---|---|---|\n"
        "| **E3** | 移除後仍有每日心跳：`tools/check_scheduled_task_drift.py` 回 rc=0 "
        "| 未達標 | ❌ |\n"
        "\n"
    )

    def test_the_markdown_table_cell_form_is_red(self) -> None:
        """注入（本輪新增鑑別力）：同一個病寫成 markdown 表格 cell ⇒ 必紅。

        修前實況：`.md` 不在 glob 內、`_EXIT_ITEM_RE` 只認行首 `E<N>.` ⇒ 這份語料
        **抽不到任何項目**（items=0），鎖對治理文件那個主要住所整個沉默。
        """
        self.assertTrue(exit_criterion_items(self._MD_RELAPSE),
                        "表格 cell 形態抽不到項目 ⇒ 擴掃描面等於沒擴（看起來覆蓋了而已）")
        problems = self._probe(self._MD_RELAPSE)
        self.assertTrue(problems, "表格 cell 形態沒被抓到 ⇒ 本鎖對 .md 那一半不具鑑別力")
        self.assertIn("E3", problems[0])

    def test_a_preserved_snapshot_with_a_correction_record_is_green(self) -> None:
        """反向對照：同一份文本補上就地訂正紀錄 ⇒ 不判紅。

        少了這條出口，擴到 `.md` 的當下就會對一列**刻意逐字保留的歷史快照**永紅——
        而永紅的閘門會被整個關掉，比沒有鎖更糟（同硬規則② 為歷史列留改派出口的理由）。
        少了這條**測試**，那條出口哪天被拿掉也不會有任何東西說話。
        """
        corrected = self._MD_RELAPSE + (
            "> 🔴 **就地訂正 E3（本列欄位逐字保留為時代快照，不改寫）**：判準已改為逐任務量測。\n")
        self.assertEqual(self._probe(corrected), [],
                         "已有就地訂正紀錄卻仍判紅 ⇒ 歷史保全與本鎖互為對方的違規")
        self.assertTrue(self._probe(self._MD_RELAPSE),
                        "對照組本身不紅 ⇒ 上一個斷言是空虛的綠")

    def test_the_md_surface_is_live(self) -> None:
        """自錨：`.md` 這一面必須真的收到檔——glob 寫錯時上面兩支合成語料照樣全綠。"""
        _problems, seen = self._live()
        self.assertTrue([s for s in seen if s.endswith(".md")],
                        f"掃描面收不到任何 .md ⇒ 本輪擴的那一面已靜默失效；實得：{seen}")

    def test_other_whole_tool_verdict_wordings_are_red_too(self) -> None:
        """注入：換一種「整支判決」的措辭仍必須紅（否則改個字就走掉）。"""
        for wording in ("status=ok", "全綠", "零違規"):
            with self.subTest(wording=wording):
                self.assertTrue(
                    self._probe(self._RELAPSE.replace("回 rc=0", f"回報 {wording}")),
                    f"改寫成「{wording}」即逸出 ⇒ 判準只認一種字面",
                )

    def test_narrowing_the_measured_set_turns_it_green(self) -> None:
        """反向對照：收窄量測對象即通過——否則判準退化成「提到 checker 就永遠紅」。

        兩條出口都驗：逐實體欄位讀法，與收窄旗標。少了這一條，本鎖會把**正確的修法**
        也判紅，而誤報的鎖最後一定被整道關掉（比沒有鎖更糟）。
        """
        for fix in (
            "讀 .tasks.AutoClaude_Nightly.present 為 true",
            "tools/check_scheduled_task_drift.py --tasks AutoClaude_Nightly 回 rc=0",
        ):
            with self.subTest(fix=fix):
                self.assertEqual(
                    self._probe(self._RELAPSE.replace(
                        "tools/check_scheduled_task_drift.py 回 rc=0", fix)),
                    [], f"正確的收窄寫法被判紅：{fix}")

    def test_a_criterion_outside_a_numbered_item_is_not_flagged(self) -> None:
        """反向對照：**引述**修前壞形態來解釋它的散文不算違規（否則訂正文自己會紅）。

        這正是 R73 那條教訓的機械面：訂正註記必須說得出「原文錯在哪」，而說出來的那句
        話不得因此被判成新的違規——與 R75 旗艦鎖用 AST 剝掉 docstring 是同一個取捨，
        只是這裡沒有 AST 可用，改以「只判逐條編號的項目本體」界定。
        """
        prose = (
            "# 🔴 退出判準的一般化規則\n"
            "#   E3 原文寫的是「移除後 tools/check_scheduled_task_drift.py 回 rc=0」，\n"
            "#   而該工具的期望值 SSOT 同時列了兩支任務 ⇒ 結構上不可滿足。\n"
        )
        self.assertEqual(self._probe(prose), [],
                         "引述壞形態的訂正散文被判紅 ⇒ 鎖在逼人不要寫下教訓")


class TestR71SmokeTripwireIsInViewWithTheHonestReading(unittest.TestCase):
    """D-4：smoke 這條每日證據要進讀者視野，且不得憑空多出一條假通道。

    🔴 **R74 重寫（DEF-101-786 殘留收尾）**：本類別的舊敘述把「win32 smoke 讀不到、
    故只印說明」寫成現況——而落點自 R71 的 `1e5214b` 起就存在（`Start-Transcript`
    ＋ 14 天輪替），R73 已查證並訂正敘述，判定邏輯卻沒動。也就是說**這組鎖守的是一個
    已經不成立的設計取捨**，於是那條每日真機證據又多兩輪留在平台覆蓋判定之外。

    現行判準（逐平台不同，因為兩邊的 smoke 不是同一種東西）：
      · win32  ＝ `SMOKE_HEARTBEATS` 真探針，smoke 那行必須是**量測值**；
      · darwin ＝ 刻意無探針（它的 smoke 是同一輪 nightly 的 stage [1/4]），只印解讀
        守則；接一條探針會讓同一件事被量兩次、看起來像兩條獨立證據。
    兩種誤讀都要擋：「本機無此檔」不得讀成「該平台沒在跑」（DEF-101-756 換載體），
    「有說明文字」也不得讀成「已納入判定」。
    """

    _SMOKE_ACTION = "$smokeAction = New-ScheduledTaskAction"
    _REDIRECTS = ("Tee-Object", "Start-Transcript", "Out-File", ">>", "1>", "2>")

    def test_smoke_line_is_emitted_for_every_managed_platform(self) -> None:
        for key in BO.NIGHTLY_HEARTBEATS:
            nightly, smoke = BO.daily_evidence(_REPO_ROOT, key)
            self.assertTrue(nightly.startswith("nightly 證據："), nightly)
            self.assertTrue(smoke.startswith("smoke 證據："), f"{key} 欄的 smoke 未進視野")

    def test_smoke_is_not_faked_into_the_heartbeat_table(self) -> None:
        """兩張表同鍵、且心跳表裡不得混進 smoke 檔——那會製造一條恆為「無檔」的假通道。"""
        self.assertEqual(sorted(BO.NIGHTLY_HEARTBEATS), sorted(BO.SMOKE_EVIDENCE))
        for rel in BO.NIGHTLY_HEARTBEATS.values():
            self.assertNotIn("smoke", rel, f"smoke 被接成心跳檔：{rel}")

    def test_windows_wording_blocks_the_not_running_misreading(self) -> None:
        """守**現況為真的那組語意**：落點存在、已接成探針、兩種誤讀都被明文擋下。

        （R73 版此處曾斷言該段必須含「落點不存在」語意，那使這條鎖反過來擋住訂正；
        R74 隨探針落地一併改為守可驗證的現況。）
        """
        win = BO.SMOKE_EVIDENCE["win32"]
        self.assertIn("log 落點**存在**", win, "未說明落點已存在 ⇒ 又退回 R71 前的假事實")
        self.assertIn("不得", win, "缺明確禁止句 ⇒ 又一次把「沒記錄」讀成「沒在跑」")
        self.assertIn("Get-ScheduledTask", win, "未給出可自行查證排程存在的指令")

    def test_windows_smoke_is_a_measurement_not_a_hardcoded_signpost(self) -> None:
        """🔴 R74 本體鎖：win32 的 smoke 那行必須是**解析出來的量測值**。

        修前實況：`daily_evidence()` 的 smoke 那行對任何 repo_root 都回同一段寫死文字
        ⇒ 就算那台機器的 smoke 連跑都沒跑，輸出也一模一樣（＝零鑑別力）。本鎖以合成
        transcript 注入：解析得到的彙總行必須出現在輸出裡，且**換一個值就要跟著變**。
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rel = BO.SMOKE_HEARTBEATS["win32"]
            log = root / rel
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(
                "TranscriptStart\n… 中略 …\n===== 彙總：PASS=7 FAIL=1 =====\n",
                encoding="utf-8", newline="\n")
            line = BO.smoke_evidence(root, "win32")
            self.assertIn("===== 彙總：PASS=7 FAIL=1 =====", line, line)
            log.write_text("TranscriptStart\n===== 彙總：PASS=99 FAIL=0 =====\n",
                           encoding="utf-8", newline="\n")
            self.assertIn("PASS=99", BO.smoke_evidence(root, "win32"),
                          "換了 transcript 內容輸出卻不變 ⇒ 這行不是量測值")
            log.unlink()
            missing = BO.smoke_evidence(root, "win32")
            self.assertIn("本機無", missing)
            self.assertIn("不得", missing,
                          "缺檔訊息必須擋住「該平台沒在跑」的誤讀（DEF-101-756 換載體）")

    def test_darwin_has_no_fake_smoke_channel(self) -> None:
        """darwin 刻意無探針：憑空多一條看似獨立的通道，量的卻是同一輪 nightly。"""
        self.assertNotIn("darwin", BO.SMOKE_HEARTBEATS)
        self.assertEqual(sorted(BO.SMOKE_HEARTBEATS), sorted(BO.SMOKE_SUMMARY_SPECS),
                         "smoke 兩張表必須同鍵，否則會出現有檔名沒解析契約的半條通道")
        line = BO.smoke_evidence(_REPO_ROOT, "darwin")
        self.assertIn("stage [1/4]", line, "未說明它是 nightly 子階段 ⇒ 會被當成第二條證據")

    def test_the_windows_log_landing_premise_matches_reality(self) -> None:
        """🔴 R73 重寫（DEF-101-786）——**本鎖原本的射程漏掉了真正的機制，導致它
        自己就是「到期日不會到」的原因**。

        原設計：掃 `install_windows_nightly.ps1` 的**排程 action** 有無輸出重導
        （`>`／`Tee-Object`／`Start-Transcript`），有就轉紅指路「前提變了」。
        實況：R71 把 `Start-Transcript` 加在 **`tools/windows_smoke_local.ps1` 腳本自己
        裡面**（`:111,127` ＋ `:125` 的 14 天輪替），排程 action 完全沒動 ⇒ 本鎖恆綠，
        而它守的那個前提在同一個 commit 就已為假。跨 R72、R73 兩輪無人察覺。
        這是本輪第三次遇到同一形態（另兩筆：`DEF-101-777` 鎖只圈一個檔、
        `DEF-101-784` 守門沒鎖），也是 `DEF-101-757` 的又一次復發。

        改寫方向：**射程涵蓋兩個站點**（排程 action ＋ 腳本本體），且判準反轉——
        現況是「落點確實存在」，所以本鎖改為守住「落點存在」與「說明文字承認它存在」
        兩者一致；哪天有人把落點拿掉，說明文字就會與實況脫節而轉紅。
        """
        landing_sites = {
            "tools/windows_smoke_local.ps1": self._REDIRECTS,
            "tools/install_windows_nightly.ps1": self._REDIRECTS,
        }
        found: dict[str, list[str]] = {}
        for rel, needles in landing_sites.items():
            text = (_REPO_ROOT / rel).read_text(encoding="utf-8-sig")
            found[rel] = [n for n in needles if n in text]
        self.assertTrue(
            found["tools/windows_smoke_local.ps1"],
            "`windows_smoke_local.ps1` 內找不到任何 log 落點機制（`>`／`Tee-Object`／"
            "`Start-Transcript`）⇒ 落點被移除了，而 `SMOKE_EVIDENCE['win32']` 仍宣稱它存在。"
            "兩者必須同進同退（DEF-101-786：上一版本鎖只掃排程 action，漏掉這個站點）",
        )
        self.assertIn(
            "log 落點**存在**", BO.SMOKE_EVIDENCE["win32"],
            "落點機制在磁碟上存在，但說明文字沒承認 ⇒ 又回到 R71 那句假事實",
        )
        # 🔴 掃描器自檢（否則上面兩段可能對任何輸入都恆綠＝本批正在清算的那種死鎖）：
        # 餵進「落點被拔掉」的形態必須命中。本 repo 不准只寫鎖、不驗鎖。
        stripped = "# 這個假樣本刻意不含任何輸出重導字樣\nWrite-Host 'hello'\n"
        self.assertEqual(
            [n for n in self._REDIRECTS if n in stripped], [],
            "掃描器對「完全沒有落點」的形態也命中 ⇒ 判準恆真，落點被拔掉那天不會有人知道",
        )


# ── R78 ARCH-05：成熟度判準 M1〜M6 的 SSOT 歸屬 ＋ M5 攔截率的新鮮度 ────────────────
_MATURITY_SSOT_REL = "docs/06_quality/CrossPlatform_Maturity_Criteria.md"
_MATURITY_ROW_RE = re.compile(r"\|\s*\*\*(M[1-6])\*\*\s*\|")
#: 觸發字後 40 字元內的「攔截率字面值」。`(?<![≥≤<>=\d])` 排除門檻（`≥80%`）與
#: 數字中段的假命中（`80%` 不得被讀成 `0%`）。
_RATE_RE = re.compile(
    r"(?:mac→Win|Win→mac|攔截率)[^|\n]{0,40}?"
    r"(?<![≥≤<>=\d])(\d{1,3}/\d{1,3}|\d{1,3}\s*(?:〜|~)\s*\d{1,3}%|\d{1,3}%)"
)
_RATE_MARK = "xplat-rate-history:"
_RATE_GLOBS = (
    "docs/04_planning/*HANDOFF*.md",
    "docs/06_quality/CrossPlatform_*.md",
    "docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md",
)


def _rate_problems(lines: list[tuple[str, int, str]], live: dict) -> tuple[list[str], int]:
    """治理面上每一個攔截率字面值：與現場活值相符，或帶歷史標記。回傳 (違規, 命中數)。"""
    problems: list[str] = []
    hits = 0
    for where, lineno, line in lines:
        for m in _RATE_RE.finditer(line):
            hits += 1
            literal, whole = m.group(1), m.group(0)
            direction = next((d for d in live if whole.startswith(d)), None)
            ok = False
            if direction:
                caught, total = live[direction]
                ok = literal in {f"{caught}/{total}", f"{round(100 * caught / total)}%"}
            if not ok and _RATE_MARK not in line:
                problems.append(
                    f"{where}:{lineno} 的攔截率 `{literal}` 既不等於現場活值"
                    f"（{ {d: f'{c}/{t}' for d, (c, t) in live.items()} }），"
                    f"也沒有 `<!-- {_RATE_MARK} WHY -->` 標記說明它是歷史值"
                )
    return problems, hits


class TestR78MaturityCriteriaSsot(unittest.TestCase):
    """M1〜M6 只有一個家，且 M5 的數字只能來自載具（R78 ARCH-05）。

    🔴 為何是 blocking 級：這六條是**治理層判「這一輪算不算成熟」的判準**，而它們原本
    寄生在 `CrossPlatform_R76_Scan_Findings.md` ——一份輪次專屬的掃描發現文件。輪次文件
    按定義是凍結記錄，不會有人回頭維護；活判準寄生在凍結記錄裡，等於**沒有家**。
    後果已經發生：M5 的攔截率同時住三個地方（判準表／交棒書 Q3／ADR 逐輪覆蓋表 R77 列），
    三處全部停在**修復前**的值——而讓它們過期的，正是同一個 commit 落地的第六道判準。
    低報自己的成果不是好事：下一輪跑載具會看到「一輪暴衝」，然後去找一個不存在的原因。

    四道判準（前三道守歸屬，第四道守新鮮度）＋ 一道掃描器自檢。
    """

    @classmethod
    def setUpClass(cls) -> None:
        import test_platform_neutral_paths as xplat  # noqa: PLC0415  # 載具即 SSOT
        cls.live = xplat.live_interception()
        cls.ssot = _REPO_ROOT / _MATURITY_SSOT_REL

    def _scan_lines(self) -> list[tuple[str, int, str]]:
        out: list[tuple[str, int, str]] = []
        for pattern in _RATE_GLOBS:
            for path in sorted(_REPO_ROOT.glob(pattern)):
                rel = path.relative_to(_REPO_ROOT).as_posix()
                for lineno, line in enumerate(
                    path.read_text(encoding="utf-8-sig").splitlines(), 1
                ):
                    out.append((rel, lineno, line))
        return out

    def test_the_six_criteria_live_in_one_named_home(self) -> None:
        self.assertTrue(self.ssot.is_file(), f"成熟度判準 SSOT 不存在：{_MATURITY_SSOT_REL}")
        rows = set(_MATURITY_ROW_RE.findall(self.ssot.read_text(encoding="utf-8-sig")))
        self.assertEqual(
            rows, {f"M{i}" for i in range(1, 7)},
            "SSOT 少了某幾條判準列 ⇒ 判準被搬走／刪掉而沒人知道",
        )

    def test_m5_points_at_the_carrier_instead_of_carrying_a_number(self) -> None:
        """M5 那一列必須具名載具——這一條就是「不寫死數字」的可執行形態。"""
        row = next(
            ln for ln in self.ssot.read_text(encoding="utf-8-sig").splitlines()
            if "**M5**" in ln
        )
        self.assertIn(
            "TestXplatInjectionMatrix", row,
            "M5 列沒有具名載具 ⇒ 讀者只能相信文件上的數字，而那正是本鎖在治的病",
        )

    def test_any_second_copy_points_back_to_the_ssot(self) -> None:
        """別處還留著 M 列可以（輪次文件的原始記載要保留），但必須指回現行的家。"""
        ssot_name = Path(_MATURITY_SSOT_REL).name
        offenders: list[str] = []
        for pattern in _RATE_GLOBS:
            for path in sorted(_REPO_ROOT.glob(pattern)):
                if path == self.ssot:
                    continue
                text = path.read_text(encoding="utf-8-sig")
                if len(set(_MATURITY_ROW_RE.findall(text))) >= 3 and ssot_name not in text:
                    offenders.append(path.relative_to(_REPO_ROOT).as_posix())
        self.assertEqual(
            offenders, [],
            f"這些檔載著半套以上的 M1〜M6 判準表卻沒有指回 {ssot_name} ⇒ 第二個家："
            f"{offenders}",
        )

    def test_every_interception_rate_is_live_or_labelled_history(self) -> None:
        problems, hits = _rate_problems(self._scan_lines(), self.live)
        self.assertEqual(problems, [], "\n".join(problems))
        self.assertGreaterEqual(
            hits, 1,
            "整個治理面掃不到任何攔截率字面值 ⇒ glob 或正則壞了，本鎖正在對空氣空轉假綠",
        )

    def test_the_scanner_tells_stale_from_live(self) -> None:
        """掃描器自檢：活值放行、過期值判紅、標記過的歷史值放行。

        少了這一條，上一支測試可能是「對任何輸入都綠」——本 repo 對「鎖存在但沒有
        鑑別力」已有 44% 的實測占比，不准只寫鎖不驗鎖。
        """
        caught, total = self.live["mac→Win"]
        live_line = [("syn.md", 1, f"mac→Win {caught}/{total}")]
        stale_line = [("syn.md", 1, f"mac→Win {caught + 1}/{total}")]
        marked = [("syn.md", 1, f"mac→Win {caught + 1}/{total} <!-- {_RATE_MARK} 舊值 -->")]
        self.assertEqual(_rate_problems(live_line, self.live)[0], [], "活值被誤判為過期")
        self.assertEqual(len(_rate_problems(stale_line, self.live)[0]), 1, "過期值沒被抓到")
        self.assertEqual(_rate_problems(marked, self.live)[0], [], "標記過的歷史值被誤殺")


# ── R78 SA-04／SA-05：交棒書的「尚未做」必須附現查指令 ──────────────────────────
_HANDOFF_GLOB = "docs/04_planning/*HANDOFF*.md"
_HANDOFF_SECTION_RE = re.compile(r"^(#{2,})\s+(.*)$")
_HANDOFF_SECTION_WORDS = ("開場必讀", "還沒做", "未做", "待辦")
_HANDOFF_ITEM_RE = re.compile(r"^\s*(?:\d+\.|[-*])\s+")
_HANDOFF_STALE_WORDS = ("尚未", "還沒", "仍缺", "未執行", "沒跑", "未推送", "仍未")
#: 「現查指令」＝帶動詞的行內程式碼片段。只認得出動詞才算數：一段
#: 純檔名的 code span（`DEF-101-876`）不是指令，而那正是被訂正的兩筆原本的樣子。
_HANDOFF_CMD_RE = re.compile(
    r"`[^`]*(git |python|pytest|Select-String|Get-|gh |powershell|& )[^`]*`"
)
_HANDOFF_MARK = "handoff-claim-verified:"


def _handoff_claim_blocks(text: str) -> list[list[str]]:
    """把「開場必讀／還沒做」類章節切成逐條目的區塊（含其下的引言續行）。

    刻意**只看條目**、不看章節前言：前言是體例與訂正說明的住處，把它當成宣稱會逼人
    在規則本身上貼標記（噪音），而規則不會過期。

    🔴 R79 複審（HANDOFF 包注入時當場量到）：**巢狀小標題繼承父節的射程**。
    上一版對「任何 `##` 以上的標題」一律重設 `in_section`，包括 `###`——於是一個
    住在「待辦」大節底下、但小標題本身不含觸發字的 `###` 區塊，整區條目會**靜默退出
    射程**（實測：加了四個小標題之後，拿掉某一項的現查指令，這道鎖照樣印綠）。
    當時的處置是「把觸發字寫進每一個小標題」＝繞過，不是修好；下一個人在 §4 底下
    新增一個不含該字的小標題就會再踩一次，而且沒有任何東西會轉紅。
    現行語意：只有**同級或更高級**（`#` 數不多於開啟該節的那一個）的標題才重設；
    更深的標題沿用父節的 `in_section`。⇒ 觸發字只需寫在大節標題上一次。
    """
    out: list[list[str]] = []
    cur: list[str] = []
    in_section = False
    section_level = 0  # 開啟當前射程的那個標題的 `#` 數（0＝目前不在射程內）
    for line in text.splitlines():
        heading = _HANDOFF_SECTION_RE.match(line)
        if heading:
            if cur:
                out.append(cur)
            cur = []
            level = len(heading.group(1))
            if any(w in heading.group(2) for w in _HANDOFF_SECTION_WORDS):
                in_section, section_level = True, level
            elif in_section and level > section_level:
                pass  # 巢狀小標題：繼承父節射程，不重設
            else:
                in_section, section_level = False, 0
            continue
        if not in_section:
            continue
        if _HANDOFF_ITEM_RE.match(line):
            if cur:
                out.append(cur)
            cur = [line]
        elif cur:
            cur.append(line)
    if cur:
        out.append(cur)
    return out


def _handoff_problems(rel: str, text: str) -> tuple[list[str], int]:
    problems: list[str] = []
    claims = 0
    for block in _handoff_claim_blocks(text):
        body = "\n".join(block)
        if not any(w in body for w in _HANDOFF_STALE_WORDS):
            continue
        claims += 1
        if _HANDOFF_CMD_RE.search(body) or _HANDOFF_MARK in body:
            continue
        problems.append(
            f"{rel} 的「{block[0].strip()[:60]}」宣稱某事尚未完成，卻沒有附任何現查指令，"
            f"也沒有 `<!-- {_HANDOFF_MARK} WHY -->` 說明它為何無法現查"
        )
    return problems, claims


class TestR78HandoffClaimsCarryLiveCommands(unittest.TestCase):
    """交棒書凡述及「尚未做」，一律附現查指令（R78 SA-04／SA-05 的體例層修法）。

    🔴 為何是體例而不是兩個個案：R78 收到的兩筆 finding 是**同一個形態**——
      · 「30 支 tag 尚未推送」：R78 開場實查，遠端 30 支都在（`git ls-remote --tags`）。
      · 「Windows nightly 缺 root_unittests」：R77 自己在同一輪已把它併進 STAGE-L，
        照原文再加一次的代價是每晚多跑一次 260〜313 秒的全套。
    兩筆都不是「寫錯了」，是**把量測值當常數寫**：交棒書記的是收輪那一刻的狀態，讀者卻
    在數天後、由別人動過的樹上讀它。附上現查指令，讀者的第一動作就會是重量而不是採信。

    逃生口是 `handoff-claim-verified:`（WHY 必填）：有些事（例如「這一輪有沒有做複審」）
    真的沒有機械現查管道，逼人編一個指令比誠實說沒有更糟。
    """

    def _docs(self) -> list[tuple[str, str]]:
        return [
            (p.relative_to(_REPO_ROOT).as_posix(), p.read_text(encoding="utf-8-sig"))
            for p in sorted(_REPO_ROOT.glob(_HANDOFF_GLOB))
        ]

    def test_every_not_yet_done_claim_is_checkable(self) -> None:
        docs = self._docs()
        self.assertTrue(docs, f"掃不到任何交棒書（{_HANDOFF_GLOB}）⇒ 本鎖在對空氣空轉")
        problems: list[str] = []
        claims = 0
        for rel, text in docs:
            found, n = _handoff_problems(rel, text)
            problems += found
            claims += n
        self.assertEqual(problems, [], "\n".join(problems))
        self.assertGreaterEqual(
            claims, 1,
            "所有交棒書的「還沒做」章節裡一句 stale 宣稱都掃不到 ⇒ 章節標題或觸發字改了，"
            "本鎖已失去射程（這正是它要防的形態）",
        )

    def test_the_scanner_can_tell_a_bare_claim_from_a_checkable_one(self) -> None:
        """掃描器自檢：裸宣稱判紅、附指令放行、附標記放行、沒有 stale 字樣不判。"""
        head = "## 0. 開場必讀\n\n"
        bare = head + "1. **30 支 tag 尚未推送**，下一輪要先推。\n"
        with_cmd = head + "1. **30 支 tag 尚未推送**，現查 `git ls-remote --tags origin`。\n"
        with_mark = head + f"1. **尚未推送**。<!-- {_HANDOFF_MARK} 無現查管道 -->\n"
        no_claim = head + "1. 本輪已推完 30 支 tag。\n"
        outside = "## 9. 其他\n\n1. **30 支 tag 尚未推送**，沒有指令。\n"
        self.assertEqual(len(_handoff_problems("syn.md", bare)[0]), 1, "裸宣稱沒被抓到")
        self.assertEqual(_handoff_problems("syn.md", with_cmd)[0], [], "附指令被誤殺")
        self.assertEqual(_handoff_problems("syn.md", with_mark)[0], [], "附標記被誤殺")
        self.assertEqual(_handoff_problems("syn.md", no_claim), ([], 0), "無 stale 字樣卻計入")
        self.assertEqual(_handoff_problems("syn.md", outside), ([], 0), "射程外的章節被誤收")

    def test_a_subheading_without_the_trigger_word_stays_in_its_parents_scope(self) -> None:
        """巢狀小標題繼承父節射程——這是 R79 複審點名、上一版**靜默放行**的那個縫。

        上一版對任何 `##` 以上標題一律重設 `in_section`，於是「待辦」大節底下一個
        普通 `###` 小標題就會把其下所有條目整區踢出射程；本輪 §4 的四個小標題正是
        靠「把觸發字寫進每一個小標題」繞過的。這支測試把繞過換成判準：小標題**不含**
        任何觸發字時，父節的裸宣稱仍必須被抓到。

        另兩向一起釘住，避免修過頭：① `###` 在**射程外**的大節底下不得被吸進來；
        ② 同級或更高級的標題仍必須關掉射程（否則一路吃到檔尾）。
        """
        nested = (
            "## §4 交給 R80 的事（待辦清單）\n\n"
            "### 4.2 收斂包點名的四項\n\n"      # 刻意不含任何 _HANDOFF_SECTION_WORDS
            "- **攔阻矩陣尚未實跑**，沒有附指令。\n"
        )
        self.assertEqual(
            len(_handoff_problems("syn.md", nested)[0]), 1,
            "「待辦」大節底下的 `###` 小標題把整區條目踢出射程了（R79 複審點名的縫）",
        )
        outside_nested = (
            "## §9 其他\n\n### 9.1 雜項\n\n- **尚未推送**，沒有附指令。\n"
        )
        self.assertEqual(
            _handoff_problems("syn.md", outside_nested), ([], 0),
            "射程外大節底下的小標題被誤收 ⇒ 繼承改過頭了",
        )
        closed_by_sibling = (
            "## §4 待辦\n\n### 4.1 甲\n\n- 甲項，現查 `git status`。\n"
            "## §5 禁止事項\n\n- **尚未推送**，沒有附指令。\n"
        )
        self.assertEqual(
            _handoff_problems("syn.md", closed_by_sibling), ([], 0),
            "同級標題沒有關掉射程 ⇒ 會一路吃到檔尾",
        )


if __name__ == "__main__":
    unittest.main()
