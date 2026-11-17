"""`tools/lib/wastecensus/supervision.py`／`supervision_load.py` 的驗收測試（ARCH §9、AT-M1）。

守的是「上線前後可比較的量測」：每個指標的判準邊界（為什麼這樣算）、痕跡事件不存在時標「尚無資料」
而不是 0 當成好消息、入口不污染工作樹。縫＝造出來的小型記錄與逐字稿（隔離 tmp 目錄），
不讀真實 ~/.claude、~/.autosdd；時間一律 epoch 秒。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.wastecensus import supervision as sv  # noqa: E402

_T0 = 1_800_000_000.0
_PROBE = _REPO / "tools" / "probe" / "waste_census.py"


def _asst(t, *, cc=0, cr=0, inp=1, tools=()):
    return {"type": "assistant", "t": _T0 + t, "model": "m", "tools": list(tools),
            "use": {"input_tokens": inp, "cache_creation_input_tokens": cc,
                    "cache_read_input_tokens": cr, "output_tokens": 5}}


def _user(t, text="hi", ok="human"):
    return {"type": "user", "t": _T0 + t, "ok": ok, "meta": False, "tool_result": False,
            "text": text, "textlen": len(text)}


def _stop_voice(t):
    return {"type": "attachment", "t": _T0 + t, "hook_event": "Stop",
            "content": "本回合結束時仍有 1 支背景代理在跑"}


def _turn(t, pending=0):
    return {"type": "system", "sub": "turn_duration", "t": _T0 + t, "pending": pending}


def _sess(sid, recs, interactive=True):
    return {"sid": sid, "recs": recs, "interactive": interactive}


class UnwatchedIntervalTest(unittest.TestCase):
    def test_interval_counts_stop_to_next_assistant_and_merges_hook_with_turn(self) -> None:
        """WHY：Stop 出聲（A）與 turn_duration（B）是同一次回合結束的兩個記錄，不得重複計。"""
        recs = [_asst(0), _stop_voice(10), _turn(11, pending=1), _asst(10 * 60 + 10)]
        got = sv.m_w1([_sess("s", recs)])
        self.assertEqual((got["n"], got["n_hook_voiced"], got["total_hours"]), (1, 1, 0.2))

    def test_credential_function_removes_supervised_intervals(self) -> None:
        """WHY：有 watch 憑證的區間不是「無看管」；憑證判準以參數注入（待 WP-4 接上）。"""
        recs = [_asst(0), _turn(5, pending=2), _asst(600)]
        self.assertEqual(sv.m_w1([_sess("s", recs)])["n"], 1)
        self.assertEqual(sv.m_w1([_sess("s", recs)], credential=lambda _e: True)["n"], 0)

    def test_stop_without_background_work_is_not_counted_and_no_return_is_flagged(self) -> None:
        recs = [_asst(0), _turn(5, pending=0), _asst(50), _turn(60, pending=1)]
        got = sv.m_w1([_sess("s", recs)])
        self.assertEqual((got["n"], got["never_returned"]), (1, 1))


class ColdRewriteTest(unittest.TestCase):
    def _wake(self, kind, idle_min, cc=300_000, cr=0):
        recs = [_asst(0, cr=200_000), _user(idle_min * 60, ok=kind, text="x"),
        _asst(idle_min * 60 + 5, cc=cc, cr=cr)]
        return [_sess("s", recs)]

    def test_background_wake_and_human_wake_are_split_by_waker(self) -> None:
        """WHY：二者要不同的對策（watch／保溫 vs 轉送／封存），必須分開量。"""
        w2, f1 = sv.m_w2_f1(self._wake("task-notification", 90))
        self.assertEqual((w2["n"], w2["tokens"], f1["n"]), (1, 300_000, 0))
        w2, f1 = sv.m_w2_f1(self._wake("human", 90))
        self.assertEqual((w2["n"], f1["n"]), (0, 1))

    def test_warm_cache_or_short_idle_is_not_a_cold_rewrite(self) -> None:
        """WHY：快取壽命 1 小時；<60 分或首回合以讀為主不是冷重寫（否則改善會被稀釋）。"""
        self.assertEqual(sv.m_w2_f1(self._wake("task-notification", 30))[0]["n"], 0)
        self.assertEqual(sv.m_w2_f1(self._wake("task-notification", 90, cc=10, cr=200_000))[0]["n"],
        0)

    def test_non_interactive_sessions_are_excluded(self) -> None:
        s = self._wake("human", 90)
        s[0]["interactive"] = False
        self.assertEqual(sv.m_w2_f1(s)[1]["n"], 0)


class SwitchMetricsTest(unittest.TestCase):
    def test_s1_counts_only_end_of_turn_over_r1_with_nothing_in_flight_and_no_pack(self) -> None:
        recs = [_asst(0, cr=300_000), _turn(1), _asst(2, cr=100_000), _turn(3),
                _asst(4, cr=300_000), _turn(5, pending=1)]
        got = sv.m_s1([_sess("s", recs)], [])
        self.assertEqual((got["turn_ends_ge_r1"], got["without_finalized_pack"]), (1, 1))
        pack = [{"sid": "s", "built_at": _T0, "finalized": True}]
        self.assertEqual(sv.m_s1([_sess("s", recs)], pack)["without_finalized_pack"], 0)
        unfinished = [{"sid": "s", "built_at": _T0, "finalized": False}]
        self.assertEqual(sv.m_s1([_sess("s", recs)], unfinished)["without_finalized_pack"], 1)

    def test_s1_ignores_turns_before_the_mechanism_existed(self) -> None:
        """WHY：機制上線前沒有交接包是必然，不是缺口；計入會讓基線永遠難看。"""
        recs = [_asst(0, cr=300_000), _turn(1)]
        self.assertEqual(sv.m_s1([_sess("s", recs)], [], since=_T0 + 100)["turn_ends_ge_r1"], 0)

    def test_s2_flags_pasted_summaries_and_accepts_machine_prompts(self) -> None:
        pasted = _sess("a", [_user(0, "以下是上輪資訊 " + "x" * 50), _asst(1)])
        machine = _sess("b", [_user(0, "按交接包繼續：讀 x.md"), _asst(1)])
        short = _sess("c", [_user(0, "修一下這個"), _asst(1)])
        got = sv.m_s2([pasted, machine, short])
        self.assertEqual((got["pasted"], got["n_interactive"]), (1, 3))

    def test_s3_lag_is_minutes_between_pack_build_and_last_conversation_record(self) -> None:
        recs = [_asst(0), _asst(600)]
        got = sv.m_s3([_sess("s", recs)], [{"sid": "s", "built_at": _T0 + 60}])
        self.assertEqual(got["lag_min"]["max"], 9.0)

    def test_f3_counts_human_prompts_after_spawn_only(self) -> None:
        recs = [_user(0, "a"), _user(100, "b"), _user(200, "c")]
        trace = [{"event": sv.EV_SESSION_SPAWNED, "sid": "s", "_at": _T0 + 150}]
        self.assertEqual(sv.m_f3([_sess("s", recs)], trace)["human_prompts_after_spawn"], 1)


class NoDataLabelTest(unittest.TestCase):
    def test_missing_trace_events_say_no_data_instead_of_a_clean_zero(self) -> None:
        """WHY：機制還沒寫痕跡時的 0 不是「沒發生」；誤當好消息會讓撤回條件永遠不觸發。"""
        got = sv.compute([_sess("s", [_asst(0)])], [], [])
        self.assertEqual(got["m_w3"]["note"], sv.NO_DATA)
        self.assertEqual(got["m_f2"]["note"], sv.NO_DATA)
        seen = [{"event": sv.EV_SUPERVISE_STOP_BLOCK, "_at": _T0}]
        self.assertIsNone(sv.compute([_sess("s", [_asst(0)])], [], seen)["m_w3"]["note"])

    def test_event_names_are_the_ones_later_work_packages_will_write(self) -> None:
        self.assertEqual(
            sv.NEW_EVENTS,
            ("supervise_stop_block", "watch_verdict", "forward_spawned", "forward_spawn_failed",
             "forward_pass", "seal_stop_block"))


class CliTest(unittest.TestCase):
    def test_cli_prints_every_metric_and_writes_nothing_into_the_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            base = tmp / "proj"
            base.mkdir()
            (base / "s1.jsonl").write_text(json.dumps({
                "type": "assistant", "timestamp": "2026-11-16T01:00:00Z", "entrypoint": "cli",
                "message": {"model": "m", "content": [], "usage": {"input_tokens": 1}}}) + "\n",
                encoding="utf-8")
            (tmp / "ho").mkdir()
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"}
            before = sorted(p.name for p in _REPO.iterdir())
            r = subprocess.run(
                [sys.executable, str(_PROBE), "--base", str(base), "--since-days", "36500",
                 "--supervision-metrics", "--trace-file", str(tmp / "none.jsonl"),
                 "--handoff-dir", str(tmp / "ho")],
                capture_output=True, env=env, cwd=str(tmp), timeout=120)
            text = r.stdout.decode("utf-8")
            self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
            for tag in ("M-W1", "M-W2", "M-W3", "M-W4", "M-F1", "M-F2", "M-F3", "M-S1", "M-S2",
            "M-S3"):
                self.assertIn(tag, text)
            self.assertIn(sv.NO_DATA, text)
            self.assertEqual(sorted(p.name for p in _REPO.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
