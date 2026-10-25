# 受測面：tools/lib/selfimproving/mea.py（程式碼鎖，非散文）
"""SelfImproving P3 採納量測窗、回滾偵測與劣化暫停的驗收（TCS-SelfImproving-P3 §2 A 組；21 個 AT）。

受測：`tools/lib/selfimproving/mea.py`、`meaplan.py`、`meawrite.py`（`measure` 動詞與 attr 動詞的
同鎖追加）、`fold.py`（R114 的 amend 校驗與 SUSPENDED）。情境建構器住
`_selfimproving_p3_fixtures.py`。
"""

from __future__ import annotations

import json
import re
import unittest
from datetime import timedelta
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p3_fixtures as f3
from _selfimproving_p3_fixtures import D3, evl, win

from lib.selfimproving import card as si_card
from lib.selfimproving import decgrammar
from lib.selfimproving import meawrite as si_meawrite


def setUpModule():
    fx.setup("si_p3m_")


def tearDownModule():
    fx.teardown()


S1 = fx.obs_id(2)
EVL_REL = "docs/06_quality/SelfImproving_Event_Ledger.jsonl"
SPEND_RE = r"^\[(PROP-SI-\d{3})\] 回滾提案｜窗：recurred｜digest：[0-9a-f]{8}$"


class MeasureTestCase(f3.P3TestCase):
    def scenario(self, build, **kw):
        """備妥一份 P3 基線複本並套用情境；回 (repo, 情境回傳值)。"""
        self.new_home()
        R = f3.p3_base()
        s = build(R, **kw)
        fx.commit_all(R, "scenario")
        return R, s

    def measure_ok(self, R, *extra):
        rc, out, err = self.M(R, "measure", *extra)
        self.assertEqual(rc, 0, out + err)
        return out

    def closes(self, R):
        return [e for e in win(R) if e["kind"] == "mea.close"]

    def only_close(self, R):
        got = self.closes(R)
        self.assertEqual(len(got), 1, got)
        return got[0]


class TestBaselineAndOpen(MeasureTestCase):
    def test_AT_323_1_1_baseline_then_open_and_second_call_is_empty(self):
        R, s = self.scenario(f3.s_base)
        P = s["P"]
        sp = f3.promote_seq(R, P)
        out1 = self.measure_ok(R)
        self.assertEqual(out1.splitlines()[0], "ok measure events=2 props=1")
        got = win(R)
        self.assertEqual([e["kind"] for e in got], ["mea.report", "mea.open"])
        base, opened = got
        self.assertEqual((base["report"], base["prop"], base["promote_seq"]), ("baseline", P, sp))
        self.assertEqual(base["opp"], [s["b"][k] for k in (2, 4, 6, 7, 8)])
        self.assertEqual((base["events"], base["pending"]), (2, 1))
        self.assertEqual((base["w_opp"], base["w_evt"], base["w_min"]), (5, 2, 5))
        self.assertEqual(base["anchor"], f3.TA)
        self.assertEqual((opened["w_opp"], opened["promote_seq"]), (5, sp))
        e1 = evl(R)
        out2 = self.measure_ok(R)
        self.assertEqual(out2.splitlines()[0], "ok measure events=0 props=1")
        self.assertEqual(evl(R), e1)
        self.assertEqual(self.prop_state(R, P), "measuring")
        res = self.check(R)
        self.assertEqual(self.S(res, "events.mea"), "PASS")

    def test_AT_323_1_2_full_window_closes_clean_at_the_end_of_the_def_day(self):
        R, s = self.scenario(lambda r: (f3.s_base(r), f3.s_adopt(r))[0])
        P = s["P"]
        out1 = self.measure_ok(R)
        self.assertEqual(out1.splitlines()[0], "ok measure events=3 props=1")
        self.assertEqual([e["kind"] for e in win(R)], ["mea.report", "mea.open", "mea.close"])
        close = self.only_close(R)
        self.assertEqual((close["result"], close["n_opp"], close["at"]),
                         ("clean", 5, "2026-10-25T23:59:59+00:00"))
        self.assertEqual(self.prop_state(R, P), "closed")
        self.assertTrue(self.measure_ok(R).startswith("ok measure events=0"))
        w = self.status(R)["measure"]["windows"]
        self.assertEqual([(x["state"], x["result"], x["n_opp"]) for x in w],
                         [("closed", "clean", 5)])

    def test_AT_323_1_3_m_class_rows_and_recurrence_first(self):
        def build(R, link):
            rows = {1: ("2026-10-21 09:00", f3.MEM), 2: ("2026-10-22 09:00", f3.MEM)}
            ids = {k: f3.obs_at(R, 20 + k, w, p) for k, (w, p) in rows.items()}
            ids["n1"] = f3.obs_at(R, 23, "2026-10-22 12:00 +00:00", "docs/notes/other.md",
                                  reopens=S1)
            ids["m3"] = f3.obs_at(R, 24, "2026-10-23 10:00 +00:00", "docs/notes/other.md")
            for k, (n, w) in {"q1": (25, "24 09:00"), "q2": (26, "25 09:00"),
                              "q3": (27, "26 09:00")}.items():
                ids[k] = f3.obs_at(R, n, f"2026-10-{w} +00:00", f3.MEM)
            f3.link_attr(R, ids["n1"], S1, settle=link)
            return {"Pm": f3.promoted(R, cls="M", target=f3.MEM, sources=[S1]), "ids": ids}

        want = {"confirm": ("recurred", 2, "2026-10-22T12:00:00+00:00", "closed"),
                "reject": ("clean", 5, "2026-10-25T09:00:00+00:00", "closed"),
                None: ("pending", 5, "2026-10-26T09:00:00+00:00", "measuring")}
        for link, (res, n, at, state) in want.items():
            with self.subTest(link=link):
                R, s = self.scenario(build, link=link)
                self.measure_ok(R)
                close = self.only_close(R)
                self.assertEqual((close["result"], close["n_opp"], close["at"]), (res, n, at))
                self.assertEqual(self.prop_state(R, s["Pm"]), state)

    def test_AT_323_1_4_recurrence_belongs_to_the_latest_promoted_prop(self):
        def build(R, case):
            if case == "a":
                f3.obs_at(R, 31, "2026-10-21 09:00 +00:00", f"{D3}/f.md")
                r1 = f3.obs_at(R, 32, "2026-10-23 09:00 +00:00", f"{D3}/f.md", reopens=S1)
                f3.link_attr(R, r1, S1, settle="confirm")
            else:
                f3.obs_at(R, 31, "2026-10-22 11:00 +00:00", f"{D3}/f.md")
            p1 = f3.promoted(R, t="2026-10-20T10:00:00+00:00")
            p2 = f3.promoted(R, target=f"{D3}/t2.md", t="2026-10-22T10:00:00+00:00")
            return p1, p2

        R, (p1, p2) = self.scenario(build, case="a")
        self.measure_ok(R)
        closes = self.closes(R)
        self.assertEqual([c["prop"] for c in closes], [p2])
        self.assertEqual((closes[0]["result"], closes[0]["n_opp"], closes[0]["at"]),
                         ("recurred", 0, "2026-10-23T09:00:00+00:00"))
        self.assertEqual(self.prop_state(R, p1), "measuring")
        wins = {w["prop"]: w for w in self.status(R)["measure"]["windows"]}
        self.assertEqual(wins[p1]["n_opp"], 2)
        R, (p1, p2) = self.scenario(build, case="b")
        self.measure_ok(R)
        wins = {w["prop"]: w for w in self.status(R)["measure"]["windows"]}
        self.assertEqual([(wins[p]["state"], wins[p]["n_opp"]) for p in (p1, p2)],
                         [("measuring", 1), ("measuring", 1)])

    def test_AT_323_1_5_rollback_decision_closes_the_window_first(self):
        def build(R):
            s = f3.s_base(R)
            f3.obs_at(R, 31, "2026-10-21 09:00 +00:00", f"{D3}/f.md")
            f3.obs_at(R, 32, "2026-10-22 09:00 +00:00", f"{D3}/f.md")
            fx.append_events(R, [fx.dec_ev(int(s["P"][-3:]), "rollback",
                                           decided_at="2026-10-22T12:00:00+00:00")])
            f3.obs_at(R, 33, "2026-10-22 15:00 +00:00", f"{D3}/f.md")
            return s

        R, s = self.scenario(build)
        out = self.measure_ok(R)
        close = self.only_close(R)
        self.assertEqual((close["result"], close["n_opp"], close["at"]),
                         ("rolled-back", 2, "2026-10-22T12:00:00+00:00"))
        self.assertEqual(self.prop_state(R, s["P"]), "closed")
        self.assertFalse([e for e in win(R) if e["kind"] == "mea.amend"])
        out2 = self.measure_ok(R)
        self.assertTrue(out2.startswith("ok measure events=0"))
        self.assertNotIn("回滾提案", out + out2)

    def test_AT_323_1_E_6_same_instant_priority_is_recurrence_then_rollback_then_full(self):
        def full_vs_rollback(R):
            s = f3.s_base(R)
            f3.s_adopt(R, 5)  # 第 5 個機會列是 DEF 列：日末 2026-10-25T23:59:59+00:00
            fx.append_events(R, [fx.dec_ev(int(s["P"][-3:]), "rollback",
                                           decided_at="2026-10-25T23:59:59+00:00")])
            return s

        def recurrence_vs_rollback(R):
            s = f3.s_rec(R)
            fx.append_events(R, [fx.dec_ev(int(s["P"][-3:]), "rollback",
                                           decided_at="2026-10-23T09:00:00+00:00")])
            return s

        R, _ = self.scenario(full_vs_rollback)
        self.measure_ok(R)
        close = self.only_close(R)
        self.assertEqual((close["result"], close["n_opp"], close["at"]),
                         ("rolled-back", 4, "2026-10-25T23:59:59+00:00"))
        R, _ = self.scenario(recurrence_vs_rollback)
        self.measure_ok(R)
        close = self.only_close(R)
        self.assertEqual((close["result"], close["n_opp"], close["at"]),
                         ("recurred", 1, "2026-10-23T09:00:00+00:00"))


class TestPendingAndLate(MeasureTestCase):
    def pending_repo(self):
        R, s = self.scenario(f3.s_pend)
        self.measure_ok(R)
        return R, s

    def test_AT_323_1_6_settling_verbs_append_the_amend_under_the_same_lock(self):
        for verb in ("attr-confirm", "attr-reject"):
            with self.subTest(verb=verb):
                R, s = self.pending_repo()
                P, close = s["P"], self.only_close(R)
                self.assertEqual((close["result"], close["n_opp"], close["at"]),
                                 ("pending", 5, "2026-10-25T23:59:59+00:00"))
                self.assertEqual(self.prop_state(R, P), "measuring")
                st = self.status(R)
                self.assertEqual(st["measure"]["candidates_unsettled"], 1)
                self.assertEqual([w["prop"] for w in st["pending_windows"]], [P])
                extra = ["--note", "夾具駁回理由"] if verb == "attr-reject" else []
                before = evl(R)
                rc, out, err = self.M(R, verb, "--att", s["att_c1"], "--by", "QA", *extra)
                self.assertEqual(rc, 0, out + err)
                evs = fx.EV(R)
                settle, amend = evs[-2], evs[-1]
                self.assertEqual(settle["kind"], verb.replace("-", "."))
                self.assertEqual(amend["kind"], "mea.amend")
                self.assertEqual((amend["seq"], amend["cause"]), (settle["seq"] + 1, settle["seq"]))
                self.assertEqual((amend["from"], amend["to"], amend["window"]),
                                 ("pending", "recurred" if verb == "attr-confirm" else "clean",
                                  close["seq"]))
                st = self.status(R)
                self.assertEqual((st["measure"]["due"], st["pending_windows"]), (0, []))
                self.assertEqual(self.prop_state(R, P), "closed")
                self.assertTrue(evl(R).startswith(before))
                after = evl(R)
                for _ in range(2):
                    self.assertTrue(self.measure_ok(R).startswith("ok measure events=0"))
                self.assertEqual(evl(R), after)

    def test_AT_323_1_E_7_settling_a_root_attr_never_appends_an_amend(self):
        R, s = self.pending_repo()
        with mock.patch.object(si_meawrite, "plan_amends", return_value=[]):
            rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c1"], "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.status(R)["measure"]["due"], 1)  # amend 已到期、尚未追加
        att = f3.root_attr(R, [s["a"][1]], "k/late-root", confirm=False)
        n0 = len(fx.EV(R))
        rc, out, err = self.M(R, "attr-confirm", "--att", att, "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        evs = fx.EV(R)
        self.assertEqual(([e["kind"] for e in evs[n0:]], self.status(R)["measure"]["due"]),
                         (["attr.confirm"], 1))
        self.assertEqual(self.measure_ok(R).splitlines()[0], "ok measure events=1 props=1")
        self.assertEqual(fx.EV(R)[-1]["kind"], "mea.amend")

    def test_AT_323_1_E_8_the_attr_path_amend_carries_the_verbs_by(self):
        for verb, by in (("attr-confirm", "zz"), ("attr-reject", "yy")):
            with self.subTest(verb=verb):
                R, s = self.pending_repo()
                extra = ["--note", "夾具駁回理由"] if verb == "attr-reject" else []
                rc, out, err = self.M(R, verb, "--att", s["att_c1"], "--by", by, *extra)
                self.assertEqual(rc, 0, out + err)
                settle, amend = fx.EV(R)[-2:]
                self.assertEqual((settle["by"], amend["kind"], amend["by"]), (by, "mea.amend", by))

    def test_AT_323_1_E_9_the_cause_is_the_last_settlement_of_the_candidate_set(self):
        def build(R):
            s = f3.s_pend(R)
            s["c2"] = f3.obs_at(R, 42, "2026-10-23 12:00 +00:00", f"{D3}/f.md", reopens=S1)
            s["att_c2"] = f3.link_attr(R, s["c2"], S1)
            return s

        R, s = self.scenario(build)
        self.measure_ok(R)
        self.assertEqual(self.only_close(R)["result"], "pending")
        rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c1"], "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        first = fx.EV(R)[-1]
        self.assertEqual(first["kind"], "attr.confirm")  # c2 仍未落定 ⇒ 還不能 amend
        rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c2"], "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        settle, amend = fx.EV(R)[-2:]
        self.assertEqual((amend["kind"], amend["to"]), ("mea.amend", "recurred"))
        self.assertEqual(amend["cause"], settle["seq"])
        self.assertGreater(settle["seq"], first["seq"])

    def late_repo(self, case):
        def build(R):
            s = f3.s_base(R)
            f3.obs_at(R, 31, "2026-10-21 09:00 +00:00", f"{D3}/f.md")
            f3.obs_at(R, 32, "2026-10-22 09:00 +00:00", f"{D3}/f.md")
            s["l1"] = f3.obs_at(R, 33, "2026-10-23 08:00 +00:00", f"{D3}/f.md")
            f3.obs_at(R, 34, "2026-10-24 09:00 +00:00", f"{D3}/f.md")
            f3.def_at(R, 5, "2026-10-25", f"{D3}/f.md")
            s["l2"] = f3.obs_at(R, 50, "2026-10-27 09:00 +00:00", f"{D3}/f.md", reopens=S1)
            return s

        R, s = self.scenario(build)
        self.measure_ok(R)
        close = self.only_close(R)
        self.assertEqual((close["result"], close["at"]), ("clean", "2026-10-25T23:59:59+00:00"))
        return R, s, close

    def test_AT_323_1_7_late_confirmation_by_filing_time_not_confirmation_time(self):
        R, s, close = self.late_repo("a")
        att = f3.link_attr(R, s["l1"], S1)
        rc, out, err = self.M(R, "attr-confirm", "--att", att, "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        k = fx.EV(R)[-2]["seq"]
        amend = fx.EV(R)[-1]
        self.assertEqual((amend["kind"], amend["seq"], amend["from"], amend["to"], amend["cause"]),
                         ("mea.amend", k + 1, "clean", "recurred", k))
        self.assertEqual(amend["window"], close["seq"])
        st = self.status(R)["measure"]
        self.assertEqual(st["due"], 0)
        self.assertIn(s["P"], st["rollback_pending"])
        for _ in range(2):
            self.assertTrue(self.measure_ok(R).startswith("ok measure events=0"))
        R, s, close = self.late_repo("b")
        att = f3.link_attr(R, s["l2"], S1)
        rc, out, err = self.M(R, "attr-confirm", "--att", att, "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        self.assertFalse([e for e in win(R) if e["kind"] == "mea.amend"])
        self.assertEqual(self.status(R)["measure"]["due"], 0)
        for _ in range(2):
            self.assertTrue(self.measure_ok(R).startswith("ok measure events=0"))
        self.assertEqual(self.only_close(R), close)


class TestBaselineDeterminismAndBounds(MeasureTestCase):
    def test_AT_323_1_E_1_baseline_is_not_backfilled_by_later_settlements(self):
        s3, s2 = fx.obs_id(4), fx.obs_id(3)

        def build(R, late):
            def pre(R, b):
                b10 = f3.obs_at(R, 30, "2026-10-11 15:00 +00:00", f"{D3}/f.md", reopens=s3)
                f3.root_attr(R, [s3], "k/late")
                f3.link_attr(R, b10, s3, settle="confirm")
            s = f3.s_base(R, pre=pre, sources=[S1, s2])
            if late:
                f3.root_attr(R, [s2], "k/late")
                rc, out, err = self.M(R, "attr-confirm", "--att", s["att"][9], "--by", "QA")
                self.assertEqual(rc, 0, out + err)
                f3.s_adopt(R, 2)
            return s

        reports = []
        for late in (False, True):
            R, s = self.scenario(build, late=late)
            self.measure_ok(R)
            base = win(R)[0]
            reports.append({k: v for k, v in base.items() if k not in ("seq", "t")})
        self.assertEqual(reports[0], reports[1])
        ids = [fx.obs_id(n) for n in (30, 24, 26, 27, 28)]
        self.assertEqual((reports[0]["opp"], reports[0]["events"], reports[0]["pending"]),
                         (ids, 2, 1))

    def test_AT_323_1_E_2_row_boundaries_and_rule_negatives(self):
        def build(R):
            fx.put(R, f3.LEDGER, fx.read(R, f3.LEDGER))  # 檔頭 tz 為 +08:00（夾具預設）
            rows = {}
            rows["x1"] = f3.obs_at(R, 21, "2026-10-09 12:00", f"{D3}/f.md")
            rows["x2"] = f3.def_at(R, 1, "2026-10-09", f"{D3}/f.md")
            rows["x3"] = f3.def_at(R, 2, "2026-10-10", f"{D3}/f.md")
            rows["y1"] = f3.obs_at(R, 22, "2026-10-20 09:59 +00:00", f"{D3}/f.md")
            rows["y2"] = f3.obs_at(R, 23, "2026-10-20 10:00 +00:00", f"{D3}/f.md")
            rows["y3"] = f3.obs_at(R, 24, "2026-10-21 09:00 +00:00", f"{D3}/f.md")
            rows["y4"] = f3.def_at(R, 3, "2026-10-20", f"{D3}/f.md")
            rows["y5"] = f3.obs_at(R, 25, "2026-10-21 18:30", f"{D3}/f.md")
            rows["z1"] = f3.obs_at(R, 26, "2026-10-22 09:00 +00:00", "docs/p3/areax/f.md")
            rows["z2"] = f3.obs_at(R, 27, "2026-10-22 10:00 +00:00", "DOCS/P3/AREA/F.MD")
            rows["z3"] = f3.obs_at(R, 28, "2026-10-22 11:00 +00:00", "",
                                   evidence="commit 1234567")
            return {"P": f3.promoted(R), "rows": rows}

        R, s = self.scenario(build)
        self.measure_ok(R)
        base = win(R)[0]
        r = s["rows"]
        self.assertEqual((base["opp"], base["anchor"]), ([r["x3"], r["y1"]], f3.TA))
        windows = self.status(R)["measure"]["windows"]
        self.assertEqual(windows[0]["n_opp"], 4)

    def test_AT_323_1_E_3_unavailable_inputs_fail_loud_without_writing(self):
        def tweak(kind):
            def build(R):
                s = f3.s_base(R) if kind != "e" else {}
                if kind in ("a", "e"):
                    fx.set_params(R, migration_base_sha=None)
                elif kind == "b":
                    fx.set_params(R, migration_base_sha="0" * 40)
                elif kind == "c":
                    (R / f3.LEDGER).unlink()
                elif kind == "d":
                    for p in (R / "docs/06_quality").glob("AutoSDD_*.md"):
                        p.unlink()
                return s
            return build

        want = {"a": "ANCHOR-UNAVAILABLE", "b": "ANCHOR-UNAVAILABLE",
                "c": "OBS-LEDGER-UNAVAILABLE", "d": "DEFECT-LEDGER-UNAVAILABLE"}
        reasons = {"a": "anchor-unavailable", "b": "anchor-unavailable",
                   "c": "obs-ledger-unavailable", "d": "defect-ledger-unavailable"}
        for kind in "abcde":
            with self.subTest(kind=kind):
                R, _ = self.scenario(tweak(kind))
                e0 = evl(R)
                rc, out, err = self.M(R, "measure")
                st = self.status(R)["measure"]
                if kind == "e":
                    self.assertEqual((rc, out.splitlines()[0]), (0, "ok measure events=0 props=0"))
                    self.assertEqual(st["status"], "read")
                    continue
                self.rejected(rc, out, {want[kind]})
                self.assertEqual(evl(R), e0)
                self.assertEqual((st["status"], st["reason"]), ("NOT-EVALUABLE", reasons[kind]))
                if kind in "cd":
                    self.assertIn("obs-draft:", out)

    def test_AT_323_1_E_4_forged_amends_and_second_open_do_not_take_effect(self):
        def build(R, case):
            p1 = f3.promoted(R, target=f"{D3}/t1.md")
            p2 = f3.promoted(R, target=f"{D3}/t2.md")
            c1 = f3.mea_chain(R, p1, "clean")
            c2 = f3.mea_chain(R, p2, "recurred", n_opp=2)
            sp1 = f3.promote_seq(R, p1)
            open1 = next(e["seq"] for e in fx.EV(R) if e["kind"] == "mea.open" and e["prop"] == p1)
            forged = {
                "a": fx.ev("mea.amend", "main", prop=p1, window=c2, **{"from": "clean"},
                           to="recurred", cause=1),
                "b": fx.ev("mea.amend", "main", prop=p1, window=c1, **{"from": "pending"},
                           to="recurred", cause=1),
                "c": fx.ev("mea.amend", "main", prop=p2, window=c2, **{"from": "recurred"},
                           to="clean", cause=1),
                "d": fx.ev("mea.amend", "main", prop=p1, window=open1, **{"from": "clean"},
                           to="recurred", cause=1),
                "e": fx.ev("mea.open", "main", prop=p1, w_opp=5, promote_seq=sp1)}[case]
            fx.append_events(R, [forged])
            return {"p1": p1, "p2": p2, "subject": forged["prop"]}

        for case in "abcde":
            with self.subTest(case=case):
                R, s = self.scenario(build, case=case)
                f = self.folded(R)
                self.assertEqual([w["effective"] for w in
                                  __import__("lib.selfimproving.fold", fromlist=["x"])
                                  .effective_windows(f)], ["clean", "recurred"])
                self.assertEqual([f.props[s["p1"]].state, f.props[s["p2"]].state],
                                 ["closed", "closed"])
                res = self.check(R)
                self.assertEqual(self.S(res, "events.transitions"), "FAIL")
                self.assertIn((s["subject"], "TRANSITION-ILLEGAL"),
                              self.F(res, "events.transitions"))
                self.assertEqual(self.S(res, "events.mea"), "PASS")
                self.assertEqual([w["result"] for w in self.status(R)["measure"]["windows"]],
                                 ["clean", "recurred"])

    def test_AT_323_1_E_5_measure_backfills_an_amend_the_attr_verb_skipped(self):
        pair = []
        for patched in (True, False):
            R, s = self.scenario(f3.s_pend)
            self.measure_ok(R)
            if patched:
                with mock.patch.object(si_meawrite, "plan_amends", return_value=[]):
                    rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c1"], "--by", "QA")
            else:
                rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c1"], "--by", "QA")
            self.assertEqual(rc, 0, out + err)
            pair.append((R, s))
        (rx, sx), (ry, _) = pair
        self.assertFalse([e for e in win(rx) if e["kind"] == "mea.amend"])
        self.assertEqual(self.status(rx)["measure"]["due"], 1)
        out = self.measure_ok(rx)
        self.assertEqual(out.splitlines()[0], "ok measure events=1 props=1")
        self.assertEqual(self.status(rx)["measure"]["due"], 0)
        self.assertTrue(self.measure_ok(rx).startswith("ok measure events=0"))

        def amend(R):
            return [{k: v for k, v in e.items() if k not in ("seq", "t", "by")}
                    for e in win(R) if e["kind"] == "mea.amend"]
        self.assertEqual(len(amend(rx)), 1)
        self.assertEqual(amend(rx), amend(ry))
        self.assertEqual(amend(rx)[0]["from"], "pending")
        self.assertEqual(amend(rx)[0]["to"], "recurred")
        for R in (rx, ry):
            self.assertEqual(self.prop_state(R, sx["P"]), "closed")


class TestRollbackCard(MeasureTestCase):
    def real_recurrence(self):
        """真 `prop-new` 推到 promoted，其後 a1（+1 日）與已確認的再現 r1（+2 日）。"""
        self.new_home()
        R = f3.p3_base()
        P = f3.real_promoted(R)
        pe = next(e for e in fx.EV(R) if e["kind"] == "app.promote" and e["prop"] == P)
        tp = f3.parse_t(pe["t"])

        def cell(days):
            dt = tp + timedelta(days=days)
            return dt.strftime("%Y-%m-%d %H:%M ") + dt.isoformat()[-6:]
        f3.obs_at(R, 31, cell(1), "docs/notes/other.md")
        r1 = f3.obs_at(R, 32, cell(2), "docs/notes/other.md", reopens=S1)
        att = f3.link_attr(R, r1, S1, settle="confirm")
        fx.commit_all(R, "recurrence")
        return R, P, pe, r1, att

    def test_AT_323_2_1_recurrence_prints_the_card_and_decides_nothing(self):
        R, P, promote, r1, att = self.real_recurrence()
        g0 = f3.porcelain(R)
        out = self.measure_ok(R)
        lines = out.splitlines()
        blocks = [ln for ln in lines if re.match(SPEND_RE, ln)]
        self.assertEqual(len(blocks), 1)
        i = lines.index(blocks[0])
        j = lines.index("--- 以下不計入核心區 ---", i)
        core, tail = lines[i:j], lines[j + 1]
        prm = json.loads(fx.read(R, fx.PARAMS))
        self.assertLessEqual(len(core), 12)
        self.assertTrue(all(si_card.width(x) <= prm["card_line_max"] for x in core[1:]))
        text = "\n".join(core)
        for frag in (r1, "docs/notes/other.md", att, "QA", str(promote["seq"]), "還原該行"):
            self.assertIn(frag, text)
        self.assertTrue(tail.startswith(f"決定：回滾 {P} "))
        parsed = decgrammar.parse(tail.split("：", 1)[1].replace("<一句理由>", "夾具理由"))
        self.assertEqual((parsed.verb, parsed.id), ("回滾", P))
        self.assertEqual(len(self.MJ(R, "measure")["rollback_cards"]), 1)
        again = self.measure_ok(R)
        self.assertIn(blocks[0], again)
        self.assertTrue(again.startswith("ok measure events=0"))
        self.assertEqual(f3.porcelain(R) - g0, {EVL_REL})
        rc, dout, derr, _, _ = fx2.decide_say(R, P, f"回滾 {P} 夾具理由")
        self.assertEqual(rc, 0, dout + derr)
        self.assertNotIn("回滾提案", self.measure_ok(R))

    def test_AT_323_2_E_1_no_card_without_a_confirmed_recurrence(self):
        def rolled(R, at):
            s = f3.s_base(R)
            f3.obs_at(R, 31, "2026-10-21 09:00 +00:00", f"{D3}/f.md")
            f3.obs_at(R, 32, "2026-10-22 09:00 +00:00", f"{D3}/f.md")
            fx.append_events(R, [fx.dec_ev(int(s["P"][-3:]), "rollback", decided_at=at)])
            return s

        def a(R):
            s = f3.s_base(R)
            f3.obs_at(R, 31, "2026-10-21 09:00 +00:00", f"{D3}/f.md")
            c = f3.obs_at(R, 41, "2026-10-22 12:00 +00:00", f"{D3}/f.md", reopens=S1)
            f3.link_attr(R, c, S1)
            return s

        def e(R):
            s = f3.s_rec(R)
            fx.append_events(R, [fx.dec_ev(int(s["P"][-3:]), "rollback",
                                           decided_at="2026-10-24T00:00:00+00:00")])
            return s

        clean = f3.s_base, f3.s_adopt
        builds = {"a": a, "b": f3.s_pend, "c": lambda R: (clean[0](R), clean[1](R))[0],
                  "d": lambda R: rolled(R, "2026-10-22T12:00:00+00:00"), "e": e}
        for key, build in builds.items():
            with self.subTest(key=key):
                R, s = self.scenario(build)
                out = self.measure_ok(R)
                self.assertNotIn("回滾提案", out)
                st = self.status(R)["measure"]
                self.assertEqual((self.MJ(R, "measure")["rollback_cards"], st["rollback_pending"]),
                                 ([], []))
                if key == "a":
                    self.assertEqual(st["candidates_unsettled"], 1)
                if key == "b":
                    self.assertIn("pending", [w["state"] for w in st["windows"]])
        R, s = self.scenario(builds["c"])
        self.measure_ok(R)
        f3.link_attr(R, fx.obs_id(33), S1, settle="confirm")
        out = self.measure_ok(R)
        self.assertTrue(out.startswith("ok measure events=1"))
        self.assertEqual(win(R)[-1]["kind"], "mea.amend")
        self.assertIn("回滾提案", out)
        self.assertIn(s["P"], self.status(R)["measure"]["rollback_pending"])

    def test_AT_323_2_E_2_measure_never_decides_and_refuses_unattended(self):
        clean = f3.s_base, f3.s_adopt
        builds = {"clean": lambda R: (clean[0](R), clean[1](R))[0], "rec": f3.s_rec,
                  "pend": f3.s_pend}
        for key, build in builds.items():
            with self.subTest(key=key):
                R, _ = self.scenario(build)
                g0, h0 = f3.porcelain(R), fx.head(R)
                n0 = len(fx.EV(R))
                self.measure_ok(R)
                kinds = {e["kind"] for e in fx.EV(R)[n0:]}
                self.assertLessEqual(kinds, {"mea.report", "mea.open", "mea.close", "mea.amend"})
                self.assertEqual(fx.head(R), h0)
                self.assertEqual(f3.porcelain(R) - g0, {EVL_REL})
        R, _ = self.scenario(builds["clean"])
        e0, h0 = f3.evl(R), fx2.snapshot_tree(self.home)
        for value in ("0", "1"):
            with mock.patch.dict("os.environ", {"AUTOSDD_UNATTENDED": value}):
                rc, out, err = self.M(R, "measure")
            self.rejected(rc, out, {"UNATTENDED-REFUSED"})
            self.assertEqual((f3.evl(R), fx2.snapshot_tree(self.home)), (e0, h0))
        self.assertEqual(self.M(R, "measure")[0], 0)


class TestSuspended(MeasureTestCase):
    def susp(self, results=("recurred", "rolled-back"), stop=2):
        def build(R):
            fx.set_params(R, stop_after_bad=stop)
            return f3.susp_events(R, results)
        return self.scenario(build)

    def suspended(self, R):
        return self.status(R)["suspended"]

    def prop_new(self, R, run):
        return f3.try_prop(R, run, action="add", target=f"{D3}/n1.md")

    def test_AT_324_1_1_two_bad_windows_suspend_until_resume(self):
        R, _ = self.susp()
        self.assertEqual(self.suspended(R)["run"], fx.rid(2))
        before = fx.snap(R)
        rc, out, err, _ = self.prop_new(R, fx.rid(2))
        self.rejected(rc, out)
        self.assertIn("SUSPENDED", out)
        self.assertEqual(fx.snap(R), before)
        rc, out, err, _, _ = fx2.decide_say(R, fx.rid(2), f"恢復 {fx.rid(2)} 已人工檢視")
        self.assertEqual(rc, 0, out + err)
        self.assertIsNone(self.suspended(R))
        self.assertEqual(self.prop_new(R, fx.rid(2))[0], 0)

    def test_AT_324_1_2_pending_neither_counts_nor_interrupts(self):
        def build(R, amend):
            a = f3.promoted(R, target=f"{D3}/s0.md")
            f3.mea_chain(R, a, "recurred", n_opp=2)
            fx.append_events(R, [fx.run_open_ev(2), fx.skip_ev(2)])
            b = f3.promoted(R, target=f"{D3}/s1.md")
            f3.mea_chain(R, b, "pending", amend=amend)
            fx.append_events(R, [fx.run_open_ev(3), fx.skip_ev(3)])
            c = f3.promoted(R, target=f"{D3}/s2.md")
            f3.mea_chain(R, c, "recurred", n_opp=2)
            return b

        want = {None: (True, 1), ("pending", "clean", 4): (False, 0),
                ("pending", "recurred", 4): (True, 0)}
        for amend, (susp, pend) in want.items():
            with self.subTest(amend=amend):
                R, b = self.scenario(build, amend=amend)
                self.assertEqual(self.suspended(R) is not None, susp)
                self.assertEqual(len(self.status(R)["pending_windows"]), pend)

    def test_AT_324_1_E_1_non_suspending_sequences_and_the_threshold(self):
        cases = {"a": (("recurred",), 2, False), "b": (("recurred", "clean", "recurred"), 2, False),
                 "c": (("recurred", "rolled-back"), 3, False),
                 "d": (("recurred", "rolled-back", "recurred"), 3, True),
                 "e": (("clean", "recurred", "rolled-back"), 2, True)}
        for key, (results, stop, want) in cases.items():
            with self.subTest(key=key):
                R, _ = self.susp(results, stop)
                self.assertEqual(self.suspended(R) is not None, want)
                if key == "d":
                    fx.set_params(R, stop_after_bad=4)
                    self.assertIsNone(self.suspended(R))

    def test_AT_324_1_E_2_resume_binds_to_the_folded_run_and_does_not_reset(self):
        R, _ = self.susp()
        rc, out, err, _, _ = fx2.decide_say(R, fx.rid(1), f"恢復 {fx.rid(1)} 已人工檢視")
        self.rejected(rc, out, {"RUN-MISMATCH"})
        R2, _ = self.susp(("clean",))
        rc, out, err, _, _ = fx2.decide_say(R2, fx.rid(1), f"恢復 {fx.rid(1)} 已人工檢視")
        self.rejected(rc, out, {"NOT-SUSPENDED"})

        def resumed():
            Rx, _ = self.susp()
            rc, out, err, _, _ = fx2.decide_say(Rx, fx.rid(2), f"恢復 {fx.rid(2)} 已人工檢視")
            self.assertEqual((rc, self.suspended(Rx)), (0, None), out + err)
            return Rx

        Rc = resumed()
        c = f3.promoted(Rc, target=f"{D3}/s9.md")
        f3.mea_chain(Rc, c, "recurred", n_opp=2)
        self.assertIsNotNone(self.suspended(Rc))
        Rd = resumed()
        d = f3.promoted(Rd, target=f"{D3}/s9.md")
        close = f3.mea_chain(Rd, d, "pending")
        self.assertIsNone(self.suspended(Rd))
        fx.append_events(Rd, [fx.ev("mea.amend", "main", prop=d, window=close,
                                    **{"from": "pending"}, to="recurred", cause=4)])
        self.assertIsNotNone(self.suspended(Rd))

    def test_AT_324_2_1_observation_continues_while_suspended(self):
        results = {}
        for key, res in (("s", ("recurred", "rolled-back")), ("n", ("recurred", "clean"))):
            R, _ = self.susp(res)
            seen = []
            argvs = [("run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main"),
                     ("scan",), ("status",), ("check",), ("export", "--json", "--kind", "events"),
                     ("measure",), ("capacity",)]
            for argv in argvs:
                rc, out, err = self.M(R, *argv)
                seen.append((argv[0], rc, tuple(sorted(fx.codes_of(out)))))
            run = [e for e in fx.EV(R) if e["kind"] == "run.open"][-1]["run"]
            rc, out, err = self.M(R, "research", "--skip", "--run", run, "--reason", "offline",
                                  "--note", "x")
            seen.append(("research", rc, tuple(sorted(fx.codes_of(out)))))
            rc, out, err = self.M(R, "attr", "--type", "root", "--by", "SA", "--obs",
                                  fx.obs_id(3), "--item", "DOC=docs/06_quality/",
                                  "--root-cause", "k/x")
            att = re.search(r"id=(\S+)", out).group(1)
            seen.append(("attr", rc, ()))
            rc, out, err = self.M(R, "attr-confirm", "--att", att, "--by", "QA")
            seen.append(("attr-confirm", rc, ()))
            results[key] = (seen, self.suspended(R) is not None)
        self.assertEqual(results["s"][0], results["n"][0])
        self.assertEqual((results["s"][1], results["n"][1]), (True, False))

    def test_AT_324_2_E_1_new_proposals_are_blocked_in_flight_ones_are_not(self):
        def build(R):
            q = fx2.new_prop(R, target=fx2.DEMO)
            z = fx2.new_prop(R, target=fx2.OTHER)
            fx2.issue_card(R, z)
            pe = fx2.prop_event(R, z)
            card = [e for e in fx.EV(R) if e["kind"] == "card" and e["prop"] == z][-1]
            fx.append_events(R, [fx.ev("dec", "掌舵者", prop=z, dkind="return", digest=pe["digest"],
                                       card_seq=card["seq"], quote=fx.std_quote("return", z))])
            f3.susp_events(R)
            return q, z

        R, (q, z) = self.scenario(build)
        run = fx.rid(1)
        self.assertIsNotNone(self.suspended(R))
        before = fx.snap(R)
        rc, out, err, _ = f3.try_prop(R, run, action="add", target=f"{D3}/n1.md")
        self.rejected(rc, out)
        self.assertIn("SUSPENDED", out)
        rc, out, err = f3.try_revise(R, run, z)
        self.rejected(rc, out)
        self.assertIn("SUSPENDED", out)
        self.assertEqual(fx.snap(R), before)
        rc, out, err = fx2.cli(R, "card", q, "--issue")
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("SUSPENDED", out)
        rc, out, err, _, _ = fx2.decide_say(R, q, f"核准 {q}", issue=False)
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("SUSPENDED", out)
        self.assertEqual(self.prop_state(R, q), "approved")


if __name__ == "__main__":
    unittest.main()
