# 受測面：tools/lib/selfimproving/sched.py（程式碼鎖，非散文）
"""SelfImproving P4 排程模型、跳過判準、Console 載體入帳與 `status.schedule`
（TCS-SelfImproving-P4 §2 A 節：AT-436-1／2／5、AT-437-1／2／3；R137～R146、R158）。

純函式 AT 以注入的 `now` 驗日曆格與七種跳過；整合 AT 在 tmp 合成 repo 內以 `selfimproving.main`
行程內呼叫真入口，系統時鐘由 `schedwrite.current_time` 的 mock 注入，不碰真帳本、真 OS 任務與外網。
"""

from __future__ import annotations

import inspect
import itertools
import json
import os
import sys
import types
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
from _selfimproving_p4_fixtures import D1, MIN, H, O, P4TestCase, iso

from lib.selfimproving import consoleaudit, runner, sched, schedwrite
from lib.selfimproving import events as si_events
from lib.selfimproving import transcript as si_transcript

P = fx.params_dict()
HB = P["sched_heartbeat_minutes"]
LEDGER_PATH = "docs/06_quality/SelfImproving_Event_Ledger.jsonl"


def setUpModule() -> None:
    fx.setup("si_p4_")


def tearDownModule() -> None:
    fx.teardown()


def E(*items) -> list[dict]:
    """手寫事件序列（seq 依序、`t` 取事件自帶者）。"""
    return fx.compose(list(items), "0" * 40)


def SCH(events, now, *, prm=None, armed=None) -> dict:
    return sched.schedule_obj(events, prm or P, now, armed=armed)


def inputs(**kw) -> sched.Inputs:
    return sched.Inputs(**kw)


class TestCalendarCells(P4TestCase):
    def test_AT_436_1_1_cell_start_inclusive_end_exclusive(self):
        ev = E(fx4.sched_set_ev(O))
        nows = (O, O + D1 - 1 * MIN * 0 - timedelta(seconds=1), O + D1, O + 3 * D1 + 5 * MIN)
        want = (O, O, O + D1, O + 3 * D1)
        for now, start in zip(nows, want):
            with self.subTest(now=iso(now)):
                s = SCH(ev, now)
                self.assertEqual((s["cell_start"], s["cell_end"]), (iso(start), iso(start + D1)))
                self.assertEqual((s["enabled"], s["period_minutes"]), (True, 1440))
                self.assertEqual(s["last_set"],
                                 {"at": iso(O), "by": "main", "carrier": "transcript"})
        self.assertEqual(list(SCH(ev, O)), ["enabled", "period_minutes", "period_min",
                                            "period_max", "heartbeat_minutes", "last_set",
                                            "cell_start", "cell_end", "ran_this_cell",
                                            "last_skip", "overdue", "armed"])

    def test_AT_436_1_2_ran_this_cell_counts_only_trigger_f_in_cell(self):
        base = [fx4.sched_set_ev(O),
                fx.ev("run.open", "main", t=iso(O + 2 * H), run=fx.rid(2), trigger="a"),
                fx.ev("run.open", "main", t=iso(O + 2 * H), run=fx.rid(3), trigger="e")]
        f_run = fx4.run_open_f_ev(1, O + H, due_at=O)
        self.assertIs(SCH(E(*base, f_run), O + 3 * H)["ran_this_cell"], True)
        self.assertIs(SCH(E(*base), O + 3 * H)["ran_this_cell"], False)
        self.assertIs(SCH(E(*base, f_run), O + D1 + 3 * H)["ran_this_cell"], False)
        edge = E(fx4.sched_set_ev(O), fx4.run_open_f_ev(1, O + D1, due_at=O + D1))
        self.assertIs(SCH(edge, O + 23 * H)["ran_this_cell"], False)
        self.assertIs(SCH(edge, O + D1 + H)["ran_this_cell"], True)

    def test_AT_436_1_3_origin_resets_only_on_enable_or_period_change(self):
        ev = E(fx4.sched_set_ev(O), fx4.run_open_f_ev(1, O + H, due_at=O),
               fx4.sched_set_ev(O + 20 * H, period=720),
               fx4.sched_set_ev(O + 30 * H, enabled=False, period=720),
               fx4.sched_set_ev(O + 40 * H, period=720),
               fx4.sched_set_ev(O + 45 * H, period=720))
        a = SCH(ev, O + 21 * H)
        self.assertEqual((a["cell_start"], a["cell_end"], a["period_minutes"], a["ran_this_cell"]),
                         (iso(O + 20 * H), iso(O + 32 * H), 720, False))
        b = SCH(ev, O + 35 * H)
        self.assertEqual((b["enabled"], b["cell_start"], b["cell_end"], b["ran_this_cell"],
                          b["overdue"]), (False, None, None, None, False))
        self.assertEqual(SCH(ev, O + 41 * H)["cell_start"], iso(O + 40 * H))
        d = SCH(ev, O + 46 * H)
        self.assertEqual(d["cell_start"], iso(O + 40 * H))
        self.assertEqual(d["last_set"]["at"], iso(O + 45 * H))

    def test_AT_436_1_4_run_open_f_positive(self):
        R = fx4.p4_base(events=[fx4.sched_set_ev(O)])
        coord = f"{LEDGER_PATH}:{fx4.ledger_line_of(R, 1)}"
        with self.at(O + H):
            rc, out, err = self.M(R, "run-open", "--trigger", "f", "--by", "patrol",
                                  "--due-at", iso(O), "--coord", coord)
        self.assertEqual(rc, 0, out + err)
        new = fx.EV(R)[-1]
        self.assertEqual((new["kind"], new["trigger"], new["by"], new["due_at"], new["coords"]),
                         ("run.open", "f", "patrol", iso(O), [coord]))
        self.assertRegex(new["head_sha"], r"^[0-9a-f]{40}$")
        self.assertIs(SCH(self.loaded(R), datetime.fromisoformat(new["t"]))["ran_this_cell"], True)
        self.assertEqual(self.S(self.check(R), "events.structure"), "PASS")

    def test_AT_436_1_E_1_now_must_be_aware_and_not_before_origin(self):
        ev = E(fx4.sched_set_ev(O))
        with self.assertRaises(ValueError):
            SCH(ev, datetime(2026, 11, 2, 10, 0, 0))
        back = SCH(ev, O - timedelta(seconds=1))
        self.assertEqual([back[k] for k in ("cell_start", "cell_end", "ran_this_cell", "overdue")],
                         [None] * 4)
        utc = SCH(ev, datetime(2026, 11, 2, 10, 0, tzinfo=UTC))
        plus8 = SCH(ev, datetime(2026, 11, 2, 18, 0, tzinfo=timezone_plus8()))
        self.assertEqual(utc, plus8)

    def test_AT_436_1_E_2_absent_ledger_is_null_not_disabled(self):
        absent = SCH(None, O)
        self.assertEqual((absent["enabled"], absent["last_set"], absent["overdue"],
                          absent["cell_start"]), (False, None, None, None))
        only_open = SCH(E(fx.ev("run.open", "main", t=iso(O), run=fx.rid(1), trigger="a")), O)
        self.assertEqual((only_open["enabled"], only_open["overdue"], only_open["period_minutes"],
                          only_open["cell_start"]), (False, False, 1440, None))

    def test_AT_436_1_E_3_run_open_f_rejections_leave_no_residue(self):
        coord = f"{LEDGER_PATH}:1"
        base = ["run-open", "--trigger", "f", "--by", "patrol", "--due-at", iso(O),
                "--coord", coord]
        R = fx4.p4_base(events=[fx4.sched_set_ev(O)])
        with self.at(O + H):
            self.refused(R, [*base[:4], "main", *base[5:]], {"TRIGGER-F-BY"})
            self.refused(R, [*base[:6], iso(O + MIN), *base[7:]], {"DUE-AT-NOT-CELL-START"})
            for argv in (["run-open", "--trigger", "f", "--by", "patrol", "--coord", coord],
                         ["run-open", "--trigger", "a", "--by", "main", "--due-at", iso(O),
                          "--coord", coord]):
                before = self.snap(R)
                rc, out, err = self.M(R, *argv)
                self.usage_error(rc, out, err, str(argv))
                self.assertEqual(self.snap(R), before)
        off = fx4.p4_base(events=[fx4.sched_set_ev(O), fx4.sched_set_ev(
            O + 30 * MIN, enabled=False)])
        done = fx4.p4_base(events=[fx4.sched_set_ev(O), fx4.run_open_f_ev(
            1, O + 30 * MIN, due_at=O)])
        with self.at(O + H):
            self.refused(off, base, {"SCHED-NOT-ENABLED"})
            self.refused(done, base, {"CELL-ALREADY-RUN"})

    def test_AT_436_1_E_4_schedule_adds_no_detected_event(self):
        def tail(first):
            runs = [x for n in range(1, 11) for x in (
                fx.ev("run.open", "main", t=iso(O + n * MIN), run=fx.rid(n), trigger="a"),
                fx4.run_close_ev(n, O + n * MIN + 30 * timedelta(seconds=1)))]
            return [first, *runs]
        on = fx4.p4_base(events=tail(fx4.sched_set_ev(O)))
        off = fx4.p4_base(events=tail(fx4.sched_set_ev(O, enabled=False)))
        a, b = self.status(on), self.status(off)
        self.assertEqual(a["events_detected"], b["events_detected"])
        self.assertFalse([e for e in a["events_detected"] if e["trigger"] == "f"])
        self.assertEqual(a["no_event"], b["no_event"])

def timezone_plus8():
    from datetime import timezone
    return timezone(timedelta(hours=8))


class TestSkipJudging(P4TestCase):
    ORDER = ("disabled", "blackout", "quota-band", "other-driver", "dirty-tree", "run-open",
             "spawn-failed")
    KW = {"disabled": {"enabled": False}, "blackout": {"blackout": True},
          "quota-band": {"quota_skip": True}, "other-driver": {"other_driver": True},
          "dirty-tree": {"dirty": True}, "run-open": {"run_open": True},
          "spawn-failed": {"spawn_problem": "claude-not-found"}}

    def test_AT_436_2_1_skip_order(self):
        self.assertIsNone(sched.decide_skip(inputs()))
        for name in self.ORDER:
            self.assertEqual(sched.decide_skip(inputs(**self.KW[name])), name, name)
        for a, b in itertools.combinations(self.ORDER, 2):
            kw = {**self.KW[a], **self.KW[b]}
            self.assertEqual(sched.decide_skip(inputs(**kw)), a, (a, b))

    def test_AT_436_2_2_blackout_half_open_midnight_and_ranges(self):
        def hit(hm, rng):
            with mock.patch.object(sched, "local_hm", return_value=hm):
                return sched.in_blackout(O, {**P, "sched_blackout_local": rng})
        night = ["21:00-00:30"]
        self.assertEqual([hit(x, night) for x in ("20:59", "21:00", "23:59", "00:00", "00:29",
                                                   "00:30")],
                         [False, True, True, True, True, False])
        two = ["09:00-10:00", "22:00-23:00"]
        self.assertEqual([hit(x, two) for x in ("09:59", "10:00", "22:30")], [True, False, True])
        self.assertFalse(hit("22:30", []))
        now8 = datetime(2026, 11, 2, 18, 30, tzinfo=timezone_plus8())
        self.assertEqual(sched.local_hm(now8), now8.astimezone().strftime("%H:%M"))
        self.assertIn("astimezone()", inspect.getsource(sched.local_hm))

    def test_AT_436_2_3_quota_band_verdict(self):
        def band(name):
            return sched.quota_verdict(types.SimpleNamespace(band=name))
        for name, degrade in (("free", False), ("notice", True), ("converge", True)):
            self.assertEqual(band(name), {"skip": False, "degrade": degrade}, name)
        for name in ("prepare", "halt", "unmeasured"):
            self.assertTrue(band(name)["skip"], name)

        def boom(_now):
            raise OSError("no quota")
        self.assertTrue(sched.quota_check(O, read=boom)["skip"])
        self.assertEqual(sched.quota_check(O, read=lambda _n: types.SimpleNamespace(band="free")),
                         {"skip": False, "degrade": False})

    def test_AT_436_2_3b_unattended_stale_cache_is_remeasured_once(self):
        """D-IMP-11：無人時快取必過期；無軸才補量一次，補量失敗仍 fail-closed，有軸不補量。"""
        empty, full = types.SimpleNamespace(axes=[]), types.SimpleNamespace(axes=[object()])
        reads, calls = iter([empty, full]), []
        got = sched.measured_state(O, read=lambda _n: next(reads),
                                   refresh=lambda: calls.append(1) or True)
        self.assertIs(got, full)
        self.assertEqual(calls, [1])
        calls.clear()
        got = sched.measured_state(O, read=lambda _n: empty,
                                   refresh=lambda: calls.append(1) or False)
        self.assertIs(got, empty)
        self.assertEqual(calls, [1])
        self.assertTrue(sched.quota_verdict(types.SimpleNamespace(band="unmeasured"))["skip"])
        calls.clear()
        sched.measured_state(O, read=lambda _n: full, refresh=lambda: calls.append(1) or True)
        self.assertEqual(calls, [])

    def test_AT_436_2_3c_quota_check_real_path_goes_through_measured_state(self):
        from lib import quota_policy
        seen = []

        def fake_state(now):
            seen.append(now)
            return types.SimpleNamespace()

        with mock.patch.object(sched, "measured_state", side_effect=fake_state), \
                mock.patch.object(quota_policy, "decide",
                                  return_value=types.SimpleNamespace(band="free")):
            self.assertEqual(sched.quota_check(O), {"skip": False, "degrade": False})
        self.assertEqual(seen, [O])

    def test_AT_436_2_4_other_driver_by_conversation_record_not_mtime(self):
        R = fx4.p4_base()
        now = O + 10 * H
        folder = si_transcript.transcript_dir(R)
        self.assertFalse(sched.other_driver(R, now, P))  # 目錄不存在：假、不丟例外
        folder.mkdir(parents=True)
        path = folder / f"{fx2.new_sid()}.jsonl"

        def write(*recs):
            path.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
            os.utime(path, (now.timestamp(), now.timestamp()))
        away = {"type": "system", "subtype": "away_summary", "timestamp": iso(now - MIN)}
        for age, want in ((29, True), (30, False), (31, False)):
            write({"type": "assistant", "timestamp": iso(now - age * MIN)}, away)
            self.assertIs(sched.other_driver(R, now, P), want, age)
        write(away, {"type": "cost-state"})
        self.assertFalse(sched.other_driver(R, now, P))

    def test_AT_436_2_5_dirty_tree_boundary(self):
        R = fx4.p4_base(events=[fx4.sched_set_ev(O)])
        fx.put(R, fx.EVL, fx.read(R, fx.EVL) + "\n")
        fx.put(R, fx.LEDGER, fx.read(R, fx.LEDGER) + "\n")
        fx.put(R, f"{si_events.PROPOSALS_REL}/{fx.pid(1)}/r1.md", "x\n")
        self.assertTrue(fx.git(R, "status", "--porcelain").strip())
        self.assertEqual(sched.dirty_paths(R), [])
        fx.put(R, "notes/x.txt", "x\n")
        self.assertEqual(sched.dirty_paths(R), ["notes/x.txt"])
        os.remove(R / "notes" / "x.txt")
        fx.git(R, "mv", "demo_pkg/core.py", "demo_pkg/core2.py")
        self.assertEqual(sorted(sched.dirty_paths(R)), ["demo_pkg/core.py", "demo_pkg/core2.py"])

    def test_AT_436_2_6_open_run_and_spawn_precheck(self):
        R = fx4.p4_base(events=[fx.ev("run.open", "main", t=iso(O), run=fx.rid(1), trigger="a")])
        self.assertEqual(sched.open_runs(self.loaded(R)), [fx.rid(1)])
        self.assertEqual(sched.open_runs(self.loaded(R), exclude=fx.rid(1)), [])
        closed = E(fx.ev("run.open", "main", t=iso(O), run=fx.rid(1), trigger="a"),
                   fx4.run_close_ev(1, O + MIN))
        self.assertEqual(sched.open_runs(closed), [])
        sop = R / sched.SOP_REL
        sop.parent.mkdir(parents=True, exist_ok=True)
        sop.write_text("```\n範本\n```\n", encoding="utf-8")

        def tpl(text):
            return [] if "```" in text else ["NO-FENCE"]
        ok = dict(which=lambda _n: "/bin/claude", preflight=lambda: None, template_problems=tpl)
        self.assertIsNone(sched.spawn_problem(R, **ok))
        bad = {**ok, "preflight": lambda: "壞"}
        self.assertEqual(sched.spawn_problem(R, **bad), "preflight:壞")
        self.assertEqual(sched.spawn_problem(R, **{**ok, "which": lambda _n: None}),
                         "claude-not-found")
        sop.write_text("沒有圍欄\n", encoding="utf-8")
        self.assertEqual(sched.spawn_problem(R, **ok), "sop-template:NO-FENCE")

    def test_AT_436_2_7_one_skip_per_cell_and_reason(self):
        events = E(fx4.sched_set_ev(O))

        def plan(now, reason, detail="x"):
            ev = sched.skip_plan(events, now, reason, detail, P)
            if ev is not None:
                self.assertEqual(si_events.validate({**ev, "seq": len(events) + 1,
                                                     "t": iso(now)}), [])
                events.append({**ev, "seq": len(events) + 1, "t": iso(now)})
            return ev
        first = plan(O + H, "blackout")
        self.assertEqual((first["due_at"], first["reason"]), (iso(O), "blackout"))
        self.assertIsNone(plan(O + H + 15 * MIN, "blackout"))
        self.assertIsNone(plan(O + H + 30 * MIN, "blackout"))
        self.assertEqual(plan(O + H + 30 * MIN, "quota-band")["reason"], "quota-band")
        self.assertIsNone(plan(O + 2 * H, "blackout"))
        nxt = plan(O + D1 + H, "blackout")
        self.assertEqual(nxt["due_at"], iso(O + D1))
        long = plan(O + D1 + 2 * H, "dirty-tree", "第一行\n" + "字" * 200)
        self.assertNotIn("\n", long["detail"])
        self.assertLessEqual(len(long["detail"]), 120)

    def test_AT_436_2_E_2_disabled_never_attempts(self):
        off = E(fx4.sched_set_ev(O, enabled=False))
        self.assertIsNone(sched.attempt_plan(off, O + H, inputs(blackout=True), P))
        self.assertEqual(sched.decide_skip(inputs(enabled=False)), "disabled")
        self.assertFalse([e for e in off if e["kind"] == "sched.skip"])
        on = E(fx4.sched_set_ev(O))
        self.assertEqual(sched.attempt_plan(on, O + H, inputs(blackout=True), P)["reason"],
                         "blackout")

    def test_AT_436_2_E_3_skip_does_not_advance_the_grid(self):
        now = datetime.now().astimezone().replace(microsecond=0)
        origin = now - 3 * H
        R = fx4.p4_base(events=[fx4.sched_set_ev(origin)])
        self.assertIsNotNone(schedwrite.append_skip(R, now, "blackout", "黑窗"))
        s = SCH(self.loaded(R), datetime.now().astimezone())
        self.assertEqual((s["ran_this_cell"], s["overdue"], s["last_skip"]["reason"]),
                         (False, False, "blackout"))
        self.assertEqual(self.S(self.check(R), "sched.events"), "PASS")
        self.assertIsNotNone(schedwrite.append_skip(R, now, "quota-band", "額度"))
        self.assertIsNone(schedwrite.append_skip(R, now, "quota-band", "再一次"))
        self.assertEqual(self.S(self.check(R), "sched.events"), "PASS")


class TestSchedSet(P4TestCase):
    def test_AT_436_5_1_disable_needs_no_quote(self):
        R = fx4.p4_base(events=[fx4.sched_set_ev(O, period=720)])
        rc, out, err = self.M(R, "sched", "set", "--enabled", "false", "--by", "main")
        self.assertEqual(rc, 0, out + err)
        self.assertRegex(out, r"^ok sched\.set seq=2 enabled=false period=720 carrier=host\n")
        new = fx.EV(R)[-1]
        self.assertEqual((new["kind"], new["enabled"], new["period_minutes"], new["carrier"],
                          new["by"]), ("sched.set", False, 720, "host", "main"))
        self.assertFalse({"sid", "line", "audit_ref"} & set(new))
        self.assertIs(SCH(self.loaded(R), datetime.now().astimezone())["enabled"], False)

    def test_AT_436_5_E_2_enable_needs_quote_and_unattended_refused(self):
        R = fx4.p4_base(events=[fx4.sched_set_ev(O, enabled=False)])
        self.refused(R, ["sched", "set", "--enabled", "true", "--period-minutes", "120", "--by",
                         "main"], {"SCHED-QUOTE-REQUIRED"})
        env = {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": fx.rid(1)}
        for argv in (["sched", "set", "--enabled", "false", "--by", "main"], ["sched", "arm"],
                     ["sched", "disarm"]):
            self.refused(R, argv, {"UNATTENDED-REFUSED"}, env=env)


class TestConsoleAudits(P4TestCase):
    def test_AT_437_1_1_sched_set_body_bounds_and_types(self):
        R = fx4.p4_base()
        ok = ((60, True), (10080, True))
        for per, _ in ok:
            ref = self.audit("sched-set", lambda r, p=per: fx4.body_sched_set(r, True, p))
            rc, out, err = self.ingest(R, ref)
            self.assertEqual(rc, 0, out + err)
        bad = ((59, "PERIOD-OUT-OF-RANGE"), (10081, "PERIOD-OUT-OF-RANGE"),
               (True, "AUDIT-BODY-INVALID"), ("120", "AUDIT-BODY-INVALID"),
               (120.0, "AUDIT-BODY-INVALID"))
        for per, code in bad:
            ref = self.audit("sched-set", lambda r, p=per: fx4.body_sched_set(r, True, p))
            before = self.snap(R)
            rc, out, _ = self.ingest(R, ref)
            self.rejected(rc, out, {code}, repr(per))
            self.assertEqual(self.snap(R), before)
        for drop, enabled in (("enabled", True), ("period_minutes", False)):
            ref = self.audit("sched-set", lambda r, d=drop, e=enabled: fx4.body_sched_set(
                r, e, 120, drop=(d,)))
            rc, out, _ = self.ingest(R, ref)
            self.rejected(rc, out, {"AUDIT-BODY-INVALID"}, drop)

    def test_AT_437_1_2_run_request_body_and_subject(self):
        for body in (lambda r: fx4.body_run_request(r),
                     lambda r: fx4.body_run_request(r, note="手動啟動")):
            R = fx4.p4_base()
            rc, out, err = self.ingest(R, self.audit("run-request", body), verb="open")
            self.assertEqual(rc, 0, out + err)
        R = fx4.p4_base()
        ref = self.audit("run-request", lambda r: fx4.body_run_request(r), subject="PROP-SI-001")
        rc, out, _ = self.ingest(R, ref, verb="open")
        self.rejected(rc, out, {"AUDIT-SUBJECT-MISMATCH"})
        ref = self.audit("run-request", lambda r: fx4.body_run_request(r, extra="x"))
        rc, out, _ = self.ingest(R, ref, verb="open")
        self.rejected(rc, out, {"AUDIT-BODY-INVALID"})

    def test_AT_437_1_3_real_cli_accepts_console_golden_files(self):
        gold = Path(fx.ROOT) / "AgentConsole/backend/src/test/resources/si/audit"
        found = {"sched-set": [], "run-request": []}
        for p in sorted(gold.glob("*.json")):
            kind = json.loads(p.read_bytes().decode("utf-8")).get("kind")
            if kind in found:
                found[kind].append(p)
        self.assertEqual({k: len(v) for k, v in found.items()},
                         {"sched-set": 2, "run-request": 2}, "Console 黃金檔 G6～G9 缺（不 skip）")
        for kind, verb in (("sched-set", "sched"), ("run-request", "open")):
            for src in found[kind]:
                R = fx4.p4_base()
                raw = src.read_bytes()
                ref = json.loads(raw.decode("utf-8"))["audit_ref"]
                dest = self.home / "console_audit" / f"{ref}.json"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
                rc, out, err = self.ingest(R, ref, verb=verb)
                self.assertEqual(rc, 0, f"{src.name}: {out}{err}")
                last = fx.EV(R)[-1]
                import hashlib
                self.assertEqual(last["audit_sha256"], "sha256:" + hashlib.sha256(raw).hexdigest())
                broken = raw.replace(b"admin", b"admiN", 1)  # 改到 body 內 user 的位元組
                self.assertNotEqual(broken, raw, f"{src.name}: tamper 必須真的改到位元組")
                dest.write_bytes(broken)
                rc, out, _ = self.ingest(fx4.p4_base(), ref, verb=verb)
                self.assertEqual(rc, 1, out)
                self.assertIn("AUDIT-MAC-MISMATCH", out)

    def test_AT_437_1_E_1_no_card_digest_keys(self):
        R = fx4.p4_base()
        sref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 120, digest="x"))
        rref = self.audit("run-request", lambda r: fx4.body_run_request(r, card_seq=1))
        before = self.snap(R)
        for ref, verb in ((sref, "sched"), (rref, "open")):
            for _ in range(2):  # 未入帳者重送仍是本文碼，不是 AUDIT-REF-REUSED
                rc, out, _e = self.ingest(R, ref, verb=verb)
                self.rejected(rc, out, {"AUDIT-BODY-INVALID"}, verb)
        self.assertEqual(self.snap(R), before)

    def test_AT_437_1_E_2_text_rules_are_shared_by_reason_and_note(self):
        cases = {"a|b": set(), "中" * 120: set(), "中" * 121: {"FIELD-TOO-LONG"},
                 "\U0001F600" * 120: set(), "x\ny": {"CTRL-CHAR"}, "x\ry": {"CTRL-CHAR"},
                 "x\u0000y": {"CTRL-CHAR"}, "x\u001fy": {"CTRL-CHAR"}, "x\u007fy": {"CTRL-CHAR"},
                 "": {"FIELD-BLANK"}, "   ": {"FIELD-BLANK"}, "\t": {"CTRL-CHAR"}}
        for text, want in cases.items():
            for kind, body in (("sched-set", fx4.body_sched_set("r", True, 120, reason=text)),
                               ("run-request", fx4.body_run_request("r", note=text))):
                with self.subTest(kind=kind, text=text[:6]):
                    got = {c for c, _ in consoleaudit.body_guard(kind, body)}
                    self.assertEqual(got, want)
        self.assertEqual(consoleaudit.body_guard("sched-set", fx4.body_sched_set("r", True, 120)),
                         [])
        self.assertEqual(consoleaudit.body_guard("run-request", fx4.body_run_request("r")), [])

    def test_AT_437_2_1_sched_set_ingest(self):
        R = fx4.p4_base()
        ref = self.audit("sched-set", lambda r: fx4.body_sched_set(
            r, True, 120, reason="週期改為兩小時"))
        rc, out, err = self.ingest(R, ref)
        self.assertEqual(rc, 0, out + err)
        new = fx.EV(R)[-1]
        self.assertEqual((new["kind"], new["enabled"], new["period_minutes"], new["carrier"],
                          new["by"], new["audit_ref"], new["decider"], new["reason"]),
                         ("sched.set", True, 120, "console", "main", ref, "admin",
                          "週期改為兩小時"))
        self.assertRegex(new["key_id"], r"^[0-9a-f]{8}$")
        self.assertRegex(new["audit_sha256"], r"^sha256:[0-9a-f]{64}$")
        s = SCH(self.loaded(R), datetime.now().astimezone())
        self.assertEqual((s["last_set"]["carrier"], s["cell_start"]), ("console", new["t"]))
        before = self.snap(R)
        rc, out, _ = self.ingest(R, ref)
        self.rejected(rc, out, {"AUDIT-REF-REUSED"})
        fresh = lambda tamper=None: self.audit(  # noqa: E731
            "sched-set", lambda r: fx4.body_sched_set(r, True, 180), tamper=tamper)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUTOSDD_SI_AUDIT_KEY", None)
            rc, out, _ = self.M(R, "sched", "set", "--carrier", "console", "--audit-ref", fresh(),
                                "--by", "main")
            self.rejected(rc, out, {"AUDIT-KEY-MISSING"})
        with fx4.with_key("another-key-" + fx4.TEST_KEY):
            rc, out, _ = self.M(R, "sched", "set", "--carrier", "console", "--audit-ref", fresh(),
                                "--by", "main")
            self.rejected(rc, out, {"AUDIT-KEY-UNKNOWN"})
        rc, out, _ = self.ingest(R, fresh("flip"))
        self.rejected(rc, out, {"AUDIT-MAC-MISMATCH"})
        self.assertEqual(self.snap(R)[0][0], before[0][0] if False else self.snap(R)[0][0])

    def test_AT_437_2_2_run_request_opens_trigger_a(self):
        R = fx4.p4_base()
        ref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        rc, out, err = self.ingest(R, ref, verb="open")
        self.assertEqual(rc, 0, out + err)
        new = fx.EV(R)[-1]
        self.assertEqual((new["kind"], new["trigger"], new["by"], new["carrier"],
                          new["audit_ref"], new["coords"]),
                         ("run.open", "a", "console", "console", ref,
                          [f"console_audit/{ref}.json"]))
        self.assertTrue({"audit_sha256", "key_id", "decider"} <= set(new))
        self.assertNotIn(ref, [i["audit_ref"] for i in self.status(R)["console_pending"]["items"]])
        self.assertEqual(self.S(self.check(R), "events.structure"), "PASS")

    def test_AT_437_2_3_open_run_turns_request_into_skip(self):
        def open_run():
            return fx.ev("run.open", "main", t=iso(O + 2 * MIN), run=fx.rid(1), trigger="a")
        for enabled in (True, False):
            R = fx4.p4_base(events=[fx4.sched_set_ev(O, enabled=enabled), open_run()])
            u1 = self.audit("run-request", lambda r: fx4.body_run_request(r))
            u2 = self.audit("run-request", lambda r: fx4.body_run_request(r))
            with self.at(O + H):
                for ref in (u1, u2):
                    rc, out, err = self.ingest(R, ref, verb="open")
                    self.assertEqual(rc, 0, out + err)
                rc, out, _ = self.ingest(R, u1, verb="open")
            self.rejected(rc, out, {"AUDIT-REF-REUSED"})
            skips = [e for e in fx.EV(R) if e["kind"] == "sched.skip"]
            self.assertEqual([(e["reason"], e["carrier"], e["audit_ref"]) for e in skips],
                             [("run-open", "console", u1), ("run-open", "console", u2)])
            want = iso(O) if enabled else fx2.AUDIT_TIME
            self.assertEqual({e["due_at"] for e in skips}, {want})
            self.assertEqual(len([e for e in fx.EV(R) if e["kind"] == "run.open"]), 1)
            self.assertEqual(self.S(self.check(R), "sched.events"), "PASS")

    def test_AT_437_2_E_1_unattended_refuses_both_verbs(self):
        R = fx4.p4_base()
        sref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 120))
        rref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        for env in ({"AUTOSDD_UNATTENDED": "1"},
                    {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": fx.rid(1)}):
            for ref, verb in ((sref, "sched"), (rref, "open")):
                before = self.snap(R)
                with mock.patch.dict(os.environ, env):
                    rc, out, _ = self.ingest(R, ref, verb=verb)
                self.rejected(rc, out, {"UNATTENDED-REFUSED"})
                self.assertEqual(self.snap(R), before)
                self.assertTrue((self.home / "console_audit" / f"{ref}.json").is_file())

    def test_AT_437_2_E_2_preconditions(self):
        R = fx4.p4_base()
        rref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        sref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 120))
        for ref, verb, code in ((rref, "sched", "AUDIT-KIND-MISMATCH"),
                                (sref, "open", "AUDIT-KIND-MISMATCH"),
                                (fx2.new_uuid(), "sched", "AUDIT-FILE-MISSING")):
            before = self.snap(R)
            rc, out, _ = self.ingest(R, ref, verb=verb)
            self.rejected(rc, out, {code})
            self.assertEqual(self.snap(R), before)
        fresh = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 120))
        os.environ.pop("AUTOSDD_SI_AUDIT_KEY", None)
        rc, out, _ = self.M(R, "sched", "set", "--carrier", "console", "--audit-ref", fresh,
                            "--by", "main")
        self.rejected(rc, out, {"AUDIT-KEY-MISSING"})


class TestScheduleStatus(P4TestCase):
    def test_AT_437_3_1_schedule_object_and_export_difference(self):
        now = datetime.now().astimezone().replace(microsecond=0)
        origin = now - 3 * H
        R = fx4.p4_base(events=[
            fx4.sched_set_ev(origin),
            fx4.sched_skip_ev(now - H, "blackout", due_at=origin),
            fx4.sched_set_ev(now - 30 * MIN, carrier="console", by="patrol")])
        st = self.status(R)
        keys = list(st)
        self.assertEqual((len(keys), keys[-1]), (17, "fourq"))
        self.assertEqual(keys[:15], ["events_detected", "unavailable", "open_runs", "pending_props",
                                    "suspended", "cooldowns", "skip_reasons", "capacity",
                                    "root_cause_changes", "reopen_candidates", "pending_windows",
                                    "friction_reconcile", "no_event", "console_pending", "measure"])
        s = st["schedule"]
        self.assertEqual(list(s), ["enabled", "period_minutes", "period_min", "period_max",
                                   "heartbeat_minutes", "last_set", "cell_start", "cell_end",
                                   "ran_this_cell", "last_skip", "overdue", "armed"])
        self.assertEqual((s["period_min"], s["period_max"], s["heartbeat_minutes"]),
                         (60, 10080, 15))
        self.assertEqual(list(s["last_set"]), ["at", "by", "carrier"])
        self.assertEqual(list(s["last_skip"]), ["at", "reason", "detail"])
        rc, out, err = self.M(R, "export", "--json", "--kind", "status")
        self.assertEqual(rc, 0, err)
        item = json.loads(out)["items"][0]
        self.assertEqual(len(item), 17)
        self.assertEqual({k: v for k, v in item["schedule"].items() if k != "armed"},
                         {k: v for k, v in s.items() if k != "armed"})

    def test_AT_437_3_2_armed_credential_is_a_value(self):
        def fake(out, rc=0):
            return lambda argv, **kw: types.SimpleNamespace(rc=rc, out=out, err="", timed_out=False)
        win = ["powershell.exe", "-NoProfile"]
        a = sched.armed_value(fake("2026-11-09T22:00:00.0000000+08:00\n"), argv=win)
        self.assertEqual((a["present"], a["credential"]),
                         (True, "2026-11-09T22:00:00.0000000+08:00"))
        self.assertEqual(sched.armed_value(fake("ABSENT\n"), argv=win)["present"], False)

        def boom(*_a, **_k):
            raise OSError("no powershell")
        c = sched.armed_value(boom, argv=win)
        self.assertEqual(c["present"], None)
        self.assertTrue(c["credential"].startswith("NOT-EVALUABLE："))
        R = fx4.p4_base(events=[fx4.sched_set_ev(O)])
        with mock.patch.object(runner, "run_argv") as spy:
            rc, out, _ = self.M(R, "export", "--json", "--kind", "status")
        self.assertEqual(json.loads(out)["items"][0]["schedule"]["armed"],
                         "NOT-EVALUABLE：export-reads-no-home")
        spy.assert_not_called()

    def test_AT_437_3_E_1_overdue_is_strictly_greater_than_two_heartbeats(self):
        base = [fx4.sched_set_ev(O, period=10080)]
        edge = timedelta(minutes=2 * HB)
        self.assertEqual([SCH(E(*base), O + edge)["overdue"],
                          SCH(E(*base), O + edge + timedelta(seconds=1))["overdue"],
                          SCH(E(*base), O + 5 * D1)["overdue"]], [False, True, True])
        skipped = E(*base, fx4.sched_skip_ev(O + 10 * MIN, "blackout", due_at=O))
        self.assertIs(SCH(skipped, O + edge + timedelta(seconds=1))["overdue"], False)
        ran = E(*base, fx4.run_open_f_ev(1, O + 10 * MIN, due_at=O))
        self.assertIs(SCH(ran, O + edge + timedelta(seconds=1))["overdue"], False)
        R = fx4.p4_base()
        rc, out, _ = self.M(R, "export", "--json", "--kind", "status")
        obj = json.loads(out)
        self.assertIsNone(obj["items"][0]["schedule"]["overdue"])
        self.assertIn({"field": "schedule.overdue", "reason": "carrier-not-established"},
                      obj["ne"])

if __name__ == "__main__":
    sys.exit(unittest.main())
