#!/usr/bin/env python3
"""DEF-200-203：落款樣本的**連續性（斷層）**判準 `quota_reconcile.gap_line`。

此前 `--pace` 只給「現在的讀數」，不說「落款這串樣本中間斷過」：兩個相鄰樣本相距超過可等
視界，就沒有依據斷言它們落在同一個 reset 視窗內自洽。本判準只出聲、不阻斷、不改任何判定。
史料與實測見本輪證據檔〈九〉。
"""
from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_messages  # noqa: E402
import quota_reconcile  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402

import session_resume_planner as planner  # noqa: E402

_MODULE_FENCES: list[dict] = []  # DEF-200-446：模組級圍籬 handle 堆疊（後進先出）


def setUpModule() -> None:  # DEF-200-446：單模組直跑也不得碰真實 TEMP／快取／痕跡目錄
    _MODULE_FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_MODULE_FENCES.pop())

_T0 = datetime.fromisoformat("2026-10-01T22:24:24+08:00")
_HORIZON = quota_messages.RESET_ARM_HORIZON_SECONDS
_WARNING = "落款樣本有斷層"


def _ledger(*offsets_s: float) -> str:
    """合成落款：每個偏移（相對 `_T0` 的秒）一列；帶兩種窗長的軸（`rows_from_jsonl` 的下限）。"""
    return "".join(
        json.dumps({"ts": (_T0 + timedelta(seconds=s)).isoformat(),
                    "pct": {"five_hour": 10.0 + i, "seven_day": 20.0 + i}}) + "\n"
        for i, s in enumerate(offsets_s))


#: 真實落款的凍結片段（2026-10-01 22:24 ～ 2026-10-02 08:21，已去掉帳號指紋欄）：相鄰間隔
#: 53.2／85.3／447.5／11.0 分鐘，447.5 分鐘＝昨夜斷線（DEF-200-203 敘事裡的那種斷層）。
_FROZEN = "".join(
    json.dumps({"ts": ts, "pct": {"five_hour": five, "seven_day": seven}}) + "\n"
    for ts, five, seven in (
        ("2026-10-01T22:24:24+08:00", 76.0, 40.0), ("2026-10-01T23:17:35+08:00", 7.0, 43.0),
        ("2026-10-02T00:42:54+08:00", 30.0, 47.0), ("2026-10-02T08:10:25+08:00", 1.0, 49.0),
        ("2026-10-02T08:21:25+08:00", 5.0, 50.0)))


class GapLineJudgementTest(unittest.TestCase):
    def test_a_gap_inside_the_last_five_rows_is_called_out(self) -> None:
        line = quota_reconcile.gap_line(_ledger(0, 3000, 6000, 6000 + 26852, 6000 + 26852 + 660))
        self.assertIn(_WARNING, line)
        self.assertIn("447.5", line, "必須帶出斷層的實際分鐘數，讀者才知道斷了多久")
        self.assertTrue(line.endswith("\n"), "整行要能被 `print(..., end='')` 直接帶走")

    def test_a_ledger_without_a_gap_is_silent(self) -> None:
        self.assertEqual(quota_reconcile.gap_line(_ledger(0, 1000, 5000, 20000, 40000)), "")

    def test_the_boundary_is_closed_on_the_horizon(self) -> None:
        """恰好一個可等視界不判斷層、多 1 秒判（同 A7-b 的閉上界紀律；`>` 改 `>=` 必紅）。"""
        self.assertEqual(quota_reconcile.gap_line(_ledger(0, _HORIZON)), "")
        self.assertIn(_WARNING, quota_reconcile.gap_line(_ledger(0, _HORIZON + 1)))

    def test_only_the_most_recent_five_rows_are_judged(self) -> None:
        """五列之外的舊斷層不算（改掃全部列必紅）；`k` 放大到涵蓋它才會出聲。"""
        text = _ledger(0, 30000, 31000, 32000, 33000, 34000, 35000)
        self.assertEqual(quota_reconcile.gap_line(text), "")
        self.assertIn(_WARNING, quota_reconcile.gap_line(text, k=7))

    def test_unreadable_ledgers_are_silent_and_never_raise(self) -> None:
        """判不出就不出聲：列數不足、空檔、壞 JSON、壞時間戳、缺軸的列，一律回空字串。"""
        pct = {"five_hour": 1, "seven_day": 2}
        bad_ts = json.dumps({"ts": "x", "pct": pct}) + "\n" + _ledger(0)
        naive = (json.dumps({"ts": "2026-10-01T22:24:24", "pct": pct}) + "\n") * 2
        one_axis = json.dumps({"ts": _T0.isoformat(), "pct": {"session": 1}}) + "\n"
        for label, text in (("空檔", ""), ("壞 JSON", "{not json\n"), ("單列", _ledger(0)),
                            ("壞時間戳", bad_ts), ("naive 時間戳", naive), ("缺軸", one_axis)):
            with self.subTest(label):
                self.assertEqual(quota_reconcile.gap_line(text), "")

    def test_the_horizon_default_is_the_existing_ssot_not_a_new_constant(self) -> None:
        default = inspect.signature(quota_reconcile.gap_line).parameters["horizon_s"].default
        self.assertEqual(default, quota_messages.RESET_ARM_HORIZON_SECONDS)

    def test_a_frozen_fragment_of_the_real_ledger_replays_to_the_known_gap(self) -> None:
        line = quota_reconcile.gap_line(_FROZEN)
        self.assertIn(_WARNING, line)
        self.assertIn("447.5", line)


class PaceWiresTheGapLineTest(unittest.TestCase):
    """`--pace` 真的把判準接到輸出上（只出聲不阻斷：rc 仍是 0、原報告原樣在前）。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="def203_gap_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        env = unittest.mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tmp)})
        env.start()
        self.addCleanup(env.stop)

    def _pace(self, ledger: str | None) -> tuple[int, str]:
        if ledger is not None:
            (self.tmp / "quota_burn.jsonl").write_text(ledger, encoding="utf-8", newline="\n")
        out = io.StringIO()
        with unittest.mock.patch.object(planner, "resolve_transcript_source",
                                        return_value=(None, "")), \
                unittest.mock.patch.object(planner.quota_gate, "pace_report",
                                           return_value="PACE-REPORT\n"), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = planner.main(["--pace"])
        return rc, out.getvalue()

    def test_pace_prints_the_gap_line_after_the_report(self) -> None:
        rc, out = self._pace(_FROZEN)
        self.assertEqual(rc, 0)
        self.assertIn("PACE-REPORT", out)
        self.assertIn(_WARNING, out, "--pace 沒有把斷層判準接到輸出面")
        self.assertLess(out.index("PACE-REPORT"), out.index(_WARNING), "原報告必須原樣在前")

    def test_pace_without_a_gap_or_without_a_ledger_prints_nothing_extra(self) -> None:
        for label, ledger in (("無斷層", _ledger(0, 1000, 2000, 3000, 4000)), ("無落款檔", None)):
            with self.subTest(label):
                rc, out = self._pace(ledger)
                self.assertEqual((rc, out), (0, "PACE-REPORT\n"))


if __name__ == "__main__":
    unittest.main()
