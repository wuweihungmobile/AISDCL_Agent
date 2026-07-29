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

import sys
import unittest
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _TESTS_DIR.parents[1]
_ONBOARDING = _REPO_ROOT / "ONBOARDING.md"

sys.path.insert(0, str(_REPO_ROOT / "tools"))
import sync_onboarding_baselines as SYNC  # noqa: E402


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

    def _problems(self, prose: str, live_tests: int = 845) -> list[str]:
        spec = next(s for s in SYNC._SPECS if s.anchor == "rootunit-baseline-live:")
        line = self._SKELETON.format(v=live_tests, prose=prose)
        return SYNC.prose_problems(line, spec, {"tests": live_tests})

    def test_current_round_claim_in_prose_is_rejected(self) -> None:
        """正樣本：round 2 抓到的原缺陷形態（受鎖值 845、散文寫 R60=756）必須紅。"""
        problems = self._problems("收集總數 R57=616 → R59=661 → **R60=756**")
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
        """文件記載值與現查不符即紅，且訊息帶可執行的回填指令。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        tampered = SYNC.render_fingerprints(text, {
            name: "0" * SYNC._FP_LEN for name, _r, _p in SYNC._FINGERPRINT_TREES
        })
        problems = SYNC.check_snapshot(tampered)
        self.assertEqual(len(problems), len(SYNC._FINGERPRINT_TREES))
        self.assertTrue(all("--with-slow" in p for p in problems), problems)
        self.assertTrue(all("presumed stale" in p for p in problems), problems)

    def test_fingerprint_anchor_exists_exactly_once_and_round_trips(self) -> None:
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        SYNC.anchored_line(text, SYNC._FINGERPRINT_ANCHOR)  # 0/≥2 皆 fail-loud
        synthetic = {
            name: f"{i}" * SYNC._FP_LEN
            for i, (name, _r, _p) in enumerate(SYNC._FINGERPRINT_TREES)
        }
        self.assertEqual(
            SYNC.parse_fingerprints(SYNC.render_fingerprints(text, synthetic)), synthetic
        )

    def test_missing_fingerprint_field_fails_loud(self) -> None:
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        line = SYNC.anchored_line(text, SYNC._FINGERPRINT_ANCHOR)
        first = SYNC._FINGERPRINT_TREES[0][0]
        broken = text.replace(line, line.replace(f"{first}=", f"{first}_renamed="), 1)
        with self.assertRaises(AssertionError) as ctx:
            SYNC.parse_fingerprints(broken)
        self.assertIn("--with-slow", str(ctx.exception))


class TestSlowSnapshotCellsRoundTrip(unittest.TestCase):
    """表② 四格的抽取／回填（`--write --with-slow` 的純函式層；不實跑分鐘級量測）。"""

    def test_every_slow_anchor_exists_exactly_once(self) -> None:
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        for spec in SYNC._SLOW_SPECS:
            SYNC.anchored_line(text, spec.anchor)  # 0/≥2 皆 fail-loud

    def test_slow_documented_extracts_windows_column_not_macos(self) -> None:
        """macOS 欄與 Windows 欄同形，抽錯欄是 SA-R60-01 的原始成因 ⇒ 明確斷言。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        doc = SYNC.slow_documented(text)
        line = SYNC.anchored_line(text, "autoclaude-pytest-snapshot:")
        windows = doc["autoclaude-pytest-snapshot:"]
        self.assertIn(f"**{windows['passed']} passed / {windows['skipped']} skipped**", line)

    def test_render_slow_round_trips_all_four_cells(self) -> None:
        """回填後重讀必須逐格等於餵進去的值（否則 `--write --with-slow` 寫錯格）。"""
        text = _ONBOARDING.read_text(encoding="utf-8-sig")
        synthetic = {
            "autoclaude-pytest-snapshot:": {"passed": 9991, "skipped": 222},
            "cigate-v001-snapshot:": {"passed": 1111},
            "cigate-v030-snapshot:": {"passed": 2222},
            "cigate-scripts-snapshot:": {"passed": 3333},
        }
        rendered = SYNC.render_slow(text, synthetic)
        self.assertEqual(SYNC.slow_documented(rendered), synthetic)
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
        doc = SYNC.slow_documented(text)
        only_passed = dict(doc)
        only_passed["autoclaude-pytest-snapshot:"] = {
            "passed": 4242, "skipped": doc["autoclaude-pytest-snapshot:"]["skipped"],
        }
        again = SYNC.slow_documented(SYNC.render_slow(text, only_passed))
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


if __name__ == "__main__":
    unittest.main()
