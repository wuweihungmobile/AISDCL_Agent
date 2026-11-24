"""`wastecensus/sections_ctl.py`／`ctl_load.py` 與 `--replay-plan`（Control_Handover W5；TCS-Control
AT-CTL-70～74、88）。

WHY：換手與掌控機制上線後，只能靠可重跑的數字回答「有沒有變好」：M-W1 修正版（讀真實憑證，舊口徑只當
上界）、M-C1（A4 回歸率）、M-C2～M-C5、M-C6（無人窗口子代理被終止）與決策重放表。本檔證明每個指標的
邊界（為什麼這樣算）、判準函式就是實作函式（`switchplan.decide`／`park.recovered` 的判準，不另寫第二
份）、母體快照重放決定性、入口零 token 且不污染工作樹。
縫：造出來的小型母體與逐字稿（tmp），不讀真實 `~/.claude`、`~/.autosdd`；時間一律 epoch 秒。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.sessionctl import control, costmodel, switch  # noqa: E402
from lib.wastecensus import ctl_load, keep_load  # noqa: E402
from lib.wastecensus import sections_ctl as sc  # noqa: E402
from lib.wastecensus import supervision as sv  # noqa: E402

_T0 = 1_800_000_000.0
_MIN = 60.0
_PROBE = _REPO / "tools" / "probe" / "waste_census.py"
HARD = switch.threshold(switch.HARD_CTX_KEY, {})[0]
R2 = switch.threshold(switch.R2_KEY, {})[0]
BIG = int(costmodel.fresh_ctx_threshold() * 1.5)
SMALL = int(costmodel.fresh_ctx_threshold() * 0.5)


def _iso(at: float) -> str:
    return datetime.fromtimestamp(at).astimezone().isoformat()


def _turn(at_min: float, ctx: int, tools=()) -> dict:
    return {"ts_first": _T0 + at_min * _MIN, "ts_last": _T0 + at_min * _MIN + 5, "inp": 1,
            "cc": 0, "cr": ctx - 1, "out": 5, "cc5": 0, "cc1": 0, "cause": "human",
            "tools": list(tools)}


def _main(sid: str, turns: list, compactions=()) -> dict:
    return {"sid": sid, "handoff_start": False, "turns": turns, "compactions": list(compactions),
            "kw_calls": [], "walls": []}


def _pop(mains=(), subs=(), **ctl) -> dict:
    return {"schema": keep_load._SNAPSHOT_SCHEMA, "since_days": 14, "main": list(mains),  # noqa: SLF001
            "sub": list(subs), "ctl": {"packs": [], "parks": [], "burn": [], **ctl}}


# ───────────────────────────────────────────────────────── M-W1（AT-CTL-70）
def _rec(t_min: float, typ: str, **kw) -> dict:
    return {"t": _T0 + t_min * _MIN, "type": typ, "sub": None, "ok": None, "meta": False, **kw}


def _stop(t_min: float, text: str) -> dict:
    return _rec(t_min, "attachment", hook_event="Stop", content=text)


def _assistant(t_min: float) -> dict:
    return _rec(t_min, "assistant", model="x", use=None, tools=[])


class MW1Test(unittest.TestCase):
    UNSUP = "本回合結束時仍有 2 支背景代理在跑"
    SUP = "本回合結束時仍有 2 支背景代理由監督程序看管中（下次叫醒最晚 15:30）"

    def sessions(self, text: str) -> list[dict]:
        return [{"sid": "s1", "interactive": True,
                 "recs": [_assistant(0), _stop(1, text), _assistant(51)]}]

    def test_no_credential_counts_and_the_old_basis_is_labelled_an_upper_bound(self) -> None:
        got = sc.m_w1_dual(self.sessions(self.UNSUP))
        self.assertEqual(got["corrected"]["n"], 1)
        self.assertEqual(got["corrected"]["gt_30min"], 1)
        self.assertEqual(got["upper_bound"]["n"], 1)
        self.assertIn("上界", got["upper_bound"]["label"])

    def test_voice_with_a_valid_credential_is_not_counted(self) -> None:
        got = sc.m_w1_dual(self.sessions(self.SUP))
        self.assertEqual(got["corrected"]["n"], 0)  # 憑證有效
        self.assertEqual(got["upper_bound"]["n"], 1)  # 舊口徑恆無憑證 ⇒ 仍計（上界）
        self.assertEqual(got["credential_spans"], {"payload": 1})

    def test_a_live_heartbeat_span_covers_the_event(self) -> None:
        span = [(_T0, _T0 + 120 * _MIN, "heartbeat")]
        got = sc.m_w1_dual(self.sessions(self.UNSUP), {"s1": span})
        self.assertEqual(got["corrected"]["n"], 0)
        self.assertEqual(got["credential_spans"], {"heartbeat": 1})
        miss = sc.m_w1_dual(self.sessions(self.UNSUP), {"s1": [(_T0 + 90 * _MIN, _T0 + 99 * _MIN,
                                                                 "heartbeat")]})
        self.assertEqual(miss["corrected"]["n"], 1)  # 區間不含事件 ⇒ 不算憑證

    def test_the_two_bases_are_never_subtracted(self) -> None:
        got = sc.m_w1_dual(self.sessions(self.SUP))
        self.assertNotIn("delta", got)
        self.assertNotEqual(got["corrected"]["n"], got["upper_bound"]["n"])


# ───────────────────────────────────────────────────────── M-C1（AT-CTL-71）
class MC1Test(unittest.TestCase):
    def rows(self, event: str, n: int, at0: float = 0.0) -> list[dict]:
        return [{"event": event, "sid": "s1", "_at": _T0 + at0 + i} for i in range(n)]

    def test_old_trace_counts_every_block_after_seal_work_and_the_new_one_counts_zero(self) -> None:
        judge = lambda _row: control.SEAL_INVALIDATED  # noqa: E731 — 夾具：每筆推回當下封存已失效
        old = sc.m_c1(self.rows("finalized_wake_block", 12), judge)
        self.assertEqual((old["blocks"], old["after_seal_work"], old["exempt"]), (12, 12, 0))
        self.assertIsNone(old["regression"])  # 機制還沒留痕＝尚無資料，不是好消息
        self.assertEqual(old["note"], sv.NO_DATA)
        new = sc.m_c1(self.rows(control.EV_COLD_WAKE_EXEMPT, 12, at0=100), lambda _r: "unknown")
        self.assertEqual((new["blocks"], new["after_seal_work"], new["exempt"]), (0, 0, 12))
        self.assertEqual(new["regression"], 0)  # W1 後同情境：放行（分母 12）、推回 0

    def test_a_block_after_the_first_exempt_event_is_a_regression(self) -> None:
        trace = (self.rows(control.EV_COLD_WAKE_EXEMPT, 1, at0=50)
                 + self.rows("finalized_wake_block", 1, at0=60))
        got = sc.m_c1(trace, lambda _r: control.SEAL_INVALIDATED)
        self.assertEqual(got["regression"], 1)

    def test_only_a_sealed_and_still_effective_block_is_not_the_a4_bug(self) -> None:
        got = sc.m_c1(self.rows("finalized_wake_block", 3), lambda _r: control.SEAL_EFFECTIVE)
        self.assertEqual(got["after_seal_work"], 0)


# ───────────────────────────────────────────────────────── M-C2～M-C6（AT-CTL-74、88）
class MC2to6Test(unittest.TestCase):
    def test_m_c2_counts_pasted_summaries_and_rereads_of_old_data(self) -> None:
        human = lambda t, text: _rec(t, "user", ok="human", tool_result=False, text=text)  # noqa: E731
        fresh = {"sid": "n1", "interactive": True, "recs": [
            human(0, "按交接包繼續：x"),
            dict(_assistant(1), reads=[r"C:\u\.autosdd\handoff\a.prompts.md", "git status"]),
            dict(_assistant(2), reads=["C:\\u\\.claude\\projects\\p\\old.jsonl"]),
            dict(_assistant(90), reads=["a.prompts.md"])]}  # 第一小時之後不算
        pasted = {"sid": "n2", "interactive": True, "recs": [human(0, "以下是上輪資訊 " + "x" * 10)]}
        got = sc.m_c2([fresh, pasted], ctl_load.OLD_DATA)
        self.assertEqual((got["pasted"], got["n_interactive"], got["machine_start"]), (1, 2, 1))
        self.assertEqual(got["reread_median"], 2)
        self.assertEqual(got["reread_nonzero"], 1)
        self.assertEqual(got["paste_pct"], 50.0)

    def test_m_c3_sums_saved_minutes_and_unmeasured_ratio(self) -> None:
        trace = [{"event": control.EV_PARK_EARLY_RECOVERED, "saved_min": 120.5},
                 {"event": control.EV_PARK_EARLY_RECOVERED, "saved_min": 10},
                 {"event": control.EV_PARK_EARLY_PROBE, "reason": "unmeasured"},
                 {"event": control.EV_PARK_EARLY_PROBE, "reason": "hold"}]
        got = sc.m_c3(trace)
        self.assertEqual((got["recovered"], got["saved_min"], got["unmeasured_ratio"]),
                         (2, 130.5, 0.5))

    def test_m_c4_distribution_followthrough_and_trigger_sources(self) -> None:
        at = lambda m: _T0 + m * _MIN  # noqa: E731
        trace = [
            {"event": control.EV_SWITCH_PLAN, "action": "STAY", "reason": "ok"},
            {"event": control.EV_SWITCH_PLAN, "action": "SWITCH_NOW", "reason": "hard"},
            {"event": control.EV_SWITCH_ADVISE, "sid": "a", "_at": at(0)},
            {"event": control.EV_SWITCH_ADVISE, "sid": "b", "_at": at(0)},
            {"event": sv.EV_SESSION_SPAWNED, "ok": True, "sid": "a", "_at": at(10),
             "handoff": "p1"},
            {"event": "seal_stop_block", "sid": "c", "_at": at(0)},
            {"event": sv.EV_SESSION_SPAWNED, "ok": True, "sid": "c", "_at": at(5), "handoff": "p2"},
            {"event": "forward_spawned", "handoff": "p3"},
            {"event": sv.EV_SESSION_SPAWNED, "ok": True, "sid": "d", "_at": at(1), "handoff": "p3"},
            {"event": sv.EV_SESSION_SPAWNED, "ok": True, "sid": "e", "_at": at(1), "route": "H"},
            {"event": sv.EV_SESSION_SPAWNED, "ok": True, "sid": "f", "_at": at(1), "handoff": "p9"},
            {"event": sv.EV_SESSION_SPAWNED, "ok": False, "sid": "z", "_at": at(1)}]
        got = sc.m_c4(trace)
        self.assertEqual(got["by_action"], {"STAY": 1, "SWITCH_NOW": 1})
        self.assertEqual((got["advise"], got["advise_followed"], got["follow_pct"]), (2, 1, 50.0))
        self.assertEqual(got["triggers"], {"advise": 1, "seal_gate": 1, "forward": 1, "park": 1,
                                           "manual": 1})

    def test_m_c5_counts_cold_returns_that_f4_wants_to_replace_but_have_no_carrier(self) -> None:
        a = _main("aaaa", [_turn(0, BIG), _turn(120, BIG)])  # 冷回、F4 判換新、有封存包 ⇒ F
        b = _main("bbbb", [_turn(0, BIG), _turn(120, BIG)])  # 同上、沒有包 ⇒ F′
        c = _main("cccc", [_turn(0, SMALL), _turn(120, SMALL)])  # 冷回但 F4 不判換新
        d = _main("dddd", [_turn(0, BIG), _turn(10, BIG)])  # 沒冷
        packs = [{"sid": "aaaa", "sealed_at": _T0 + 5 * _MIN, "acker": None, "acked_at": None}]
        got = sc.m_c5(_pop([a, b, c, d], packs=packs))
        self.assertEqual(got, {"cold_returns": 3, "f4_fresh": 2, "f_prime": 1})

    def test_a_sealed_pack_followed_by_real_work_is_not_a_carrier(self) -> None:
        turns = [_turn(0, BIG), _turn(20, BIG, tools=["Edit"]), _turn(180, BIG)]
        packs = [{"sid": "aaaa", "sealed_at": _T0 + 5 * _MIN}]
        self.assertEqual(sc.sealed_state("aaaa", _T0 + 170 * _MIN, packs, turns),
                         control.SEAL_INVALIDATED)
        calm = [_turn(0, BIG), _turn(20, BIG, tools=["Read", "TaskStop"]), _turn(180, BIG)]
        self.assertEqual(sc.sealed_state("aaaa", _T0 + 170 * _MIN, packs, calm),
                         control.SEAL_EFFECTIVE)
        self.assertEqual(sc.sealed_state("zzzz", _T0, packs, calm), control.SEAL_NONE)

    def test_m_c6_counts_killed_subagents_only_in_unattended_windows(self) -> None:
        note = _rec(5, "user", ok="task-notification", tool_result=False,
                    text="<task-notification><status>killed</status>")
        got = sc.m_c6([{"sid": "u1", "interactive": False, "recs": [note]},
                       {"sid": "i1", "interactive": True, "recs": [note]},
                       {"sid": "u2", "interactive": False, "recs": []}])
        self.assertEqual((got["killed"], got["sessions"], got["target"]), (1, 1, 0))


# ───────────────────────────────────────────────────────── --replay-plan（AT-CTL-72）
class ReplayPlanTest(unittest.TestCase):
    def pop(self) -> dict:
        a = _main("aaaa", [_turn(0, SMALL), _turn(100, HARD)])
        b = _main("bbbb", [_turn(0, SMALL), _turn(100, HARD)])
        c = _main("cccc", [_turn(0, SMALL), _turn(10, SMALL)], compactions=[
            {"ts": _T0, "trigger": "manual", "pre": 1, "idle_min": None}] * R2)
        d = _main("dddd", [_turn(0, BIG), _turn(120, BIG)])
        sub = {"sid": "aaaa", "turns": [_turn(90, 10), _turn(110, 10)], "kw_calls": []}
        packs = [{"sid": "x1", "sealed_at": _T0, "acker": "y1", "acked_at": _T0 + 60},
                 {"sid": "y1", "sealed_at": _T0 + 60 + 10 * _MIN, "acker": None, "acked_at": None},
                 {"sid": "x2", "sealed_at": _T0, "acker": "y2", "acked_at": _T0 + 60},
                 {"sid": "y2", "sealed_at": _T0 + 60 + 400 * _MIN, "acker": None, "acked_at": None}]
        return _pop([a, b, c, d], [sub], packs=packs)

    def row(self, res: dict, prefix: str) -> dict:
        return next(r for r in res["rows"] if r["name"].startswith(prefix))

    def test_every_row_of_the_design_table_is_present_and_deterministic(self) -> None:
        first, second = sc.replay_plan(self.pop()), sc.replay_plan(self.pop())
        self.assertEqual(first, second)
        self.assertEqual([r["name"][:2] for r in first["rows"]],
                         ["H：", "R2", "冷回", "D：", "pa"])

    def test_h_row_splits_drain_from_now_by_agents_in_flight(self) -> None:
        h = self.row(sc.replay_plan(self.pop()), "H")
        self.assertEqual(h["hits"], 2)
        self.assertIn("1 個當下有在飛代理 ⇒ SWITCH_AFTER_DRAIN", h["note"])
        self.assertIn("1 個 ⇒ SWITCH_NOW", h["note"])

    def test_r2_cold_and_debounce_rows(self) -> None:
        res = sc.replay_plan(self.pop())
        self.assertEqual(self.row(res, "R2")["hits"], 1)
        self.assertIn("無推回：1", self.row(res, "R2")["note"])
        cold = self.row(res, "冷回")
        self.assertEqual(cold["hits"], 3)  # a、b（SMALL 回來）與 d（BIG 回來）
        self.assertIn("F′）1", cold["note"])
        deb = self.row(res, "D：")
        self.assertEqual(deb["hits"], 1)  # 10 分的那筆 < 30；400 分的不算
        self.assertEqual(res["detail"]["debounce_gaps"], [10.0, 400.0])

    def park(self, *, drop: bool, same_account: bool = False) -> dict:
        def burn(at_min: float, five: float, week: float, acct: str) -> dict:
            return {"fp": [f"account={acct}", "five_hour", "seven_day"], "ts": _iso(_T0 + at_min * _MIN),
                    "pct": {"five_hour": five, "session": five, "seven_day": week, "weekly_all": week,
                            "spend": 0.0}, "resets_at": {}}
        rows = [burn(-10, 0, 100, "A"), burn(120, 0, 3 if drop else 100, "A" if same_account else "B")]
        marker = {"sid": "pppp", "parked_at": _iso(_T0), "fire_at": _iso(_T0 + 300 * _MIN)}
        return sc.replay_plan(_pop(parks=[marker], burn=rows))

    def test_park_early_hit_reports_a_lower_bound_and_the_account_change(self) -> None:
        got = self.row(self.park(drop=True), "park")
        self.assertEqual(got["hits"], 1)
        self.assertIn("pppp"[:8], got["note"])
        self.assertIn("換帳號", got["note"])
        self.assertIn("下界", got["note"])

    def test_park_early_negative_controls_do_not_hit(self) -> None:
        self.assertEqual(self.row(self.park(drop=False), "park")["hits"], 0)  # 讀數沒降
        # 同帳號、讀數降了仍判恢復（換帳號只影響選路，不影響是否恢復）
        self.assertEqual(self.row(self.park(drop=True, same_account=True), "park")["hits"], 1)

    def test_the_replay_uses_the_implementation_not_a_second_copy(self) -> None:
        """AT-CTL-72 末句：`sections_ctl.py` 不複製判準——只呼叫 decide／parkprobe／costmodel 本體。"""
        text = (_REPO / "tools/lib/wastecensus/sections_ctl.py").read_text(encoding="utf-8")
        for needle in ("switchplan.decide", "parkprobe.evaluate", "switchplan.Inputs"):
            self.assertIn(needle, text)
        for forbidden in ("W_CC1", "fresh_total", "EARLY_DROP_PP", "prepare_pct <", "< policy"):
            self.assertNotIn(forbidden, text)


# ───────────────────────────────────────────────────────── 入口（真行程；零 token）
class EntryPointTest(unittest.TestCase):
    def test_replay_plan_on_a_population_snapshot_is_deterministic_and_clean(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctl-w5-census-") as tmp:
            snap = Path(tmp) / "pop.json"
            snap.write_text(json.dumps(ReplayPlanTest().pop()), encoding="utf-8")
            before = subprocess.run(["git", "status", "--porcelain"], cwd=_REPO, text=True,
                                    capture_output=True, encoding="utf-8").stdout
            runs = [subprocess.run([sys.executable, str(_PROBE), "--replay-plan", "--population",
                                    str(snap), "--base", tmp, "--trace-file",
                                    str(Path(tmp) / "none.jsonl")], capture_output=True, text=True,
                                   encoding="utf-8", timeout=120, cwd=tmp) for _ in range(2)]
            after = subprocess.run(["git", "status", "--porcelain"], cwd=_REPO, text=True,
                                   capture_output=True, encoding="utf-8").stdout
        for done in runs:
            self.assertEqual(done.returncode, 0, msg=done.stderr)
        self.assertEqual(runs[0].stdout, runs[1].stdout)  # 同快照兩次輸出逐位元組相同
        self.assertIn("| 判定點 | 命中 | 備註 |", runs[0].stdout)
        self.assertEqual(len(re.findall(r"^\| (?:H|R2|冷回|D|park)", runs[0].stdout, re.M)), 5)
        self.assertEqual(before, after)  # 入口不污染工作樹

    def test_switch_metrics_on_a_snapshot_prints_the_m_c_lines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctl-w5-census-") as tmp:
            snap, trace = Path(tmp) / "pop.json", Path(tmp) / "trace.jsonl"
            snap.write_text(json.dumps(ReplayPlanTest().pop()), encoding="utf-8")
            trace.write_text(json.dumps({"event": control.EV_SWITCH_PLAN, "action": "STAY",
                                         "reason": "ok", "at": _iso(_T0)}) + "\n", encoding="utf-8")
            done = subprocess.run(
                [sys.executable, str(_PROBE), "--switch-metrics", "--population", str(snap),
                 "--base", tmp, "--trace-file", str(trace), "--handoff-dir", tmp],
                capture_output=True, text=True, encoding="utf-8", timeout=120, cwd=tmp)
        self.assertEqual(done.returncode, 0, msg=done.stderr)
        for token in ("M-C3", "M-C4", "M-C5"):
            self.assertIn(token, done.stdout)


class EventNamesTest(unittest.TestCase):
    def test_trace_events_used_by_the_census_are_the_control_constants(self) -> None:
        text = (_REPO / "tools/lib/wastecensus/sections_ctl.py").read_text(encoding="utf-8")
        for const in ("EV_COLD_WAKE_EXEMPT", "EV_SWITCH_PLAN", "EV_SWITCH_ADVISE",
                      "EV_PARK_EARLY_RECOVERED", "EV_PARK_EARLY_PROBE"):
            self.assertIn(f"control.{const}", text)
        self.assertEqual(len(set(control.CTL_EVENTS)), len(control.CTL_EVENTS))


if __name__ == "__main__":
    unittest.main()
