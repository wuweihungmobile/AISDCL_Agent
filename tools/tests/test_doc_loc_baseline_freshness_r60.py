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

import contextlib
import datetime
import hashlib
import io
import re
import sys
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path, PurePosixPath

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"

sys.path.insert(0, str(_REPO_ROOT / "tools"))
import sync_onboarding_baselines as SYNC  # noqa: E402


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
            re.fullmatch(r"[0-9a-f]{%d}" % SYNC._FP_LEN, SYNC._UNRECORDED),
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

    def test_never_baselined_column_says_so_instead_of_faking_a_drift(self) -> None:
        """provenance 全 `unrecorded` ＝ 從未量過，不是「量過但過期」。

        原措辭把它畫成 `v001:unrecorded→8ffe3c3dabbd` 這種漂移箭頭，讀起來像「有人量過、
        後來樹變了」——實際上那一欄從來沒有任何人量過。同一個符號代表兩種完全不同的狀態，
        就是把「不知道」寫得像結論（同 `NO-LOCAL-CARRIER` 必須附理由的紀律）。
        """
        notice = self._notice({f: SYNC._UNRECORDED for f in SYNC._PROVENANCE_FIELDS})
        self.assertIn("尚未建立基線", notice)
        self.assertNotIn("→", notice, "從未回填過的欄不得以漂移箭頭呈現（把『沒量過』寫成『過期』）")

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


if __name__ == "__main__":
    unittest.main()
