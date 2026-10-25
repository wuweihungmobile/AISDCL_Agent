# 受測面：tools/lib/selfimproving/meacheck.py（程式碼鎖，非散文）
"""SelfImproving P3 的 `mea.*` 欄位表、`measure` 動詞與 `status`／`export` 增量（TCS-P3 §2 B 組）。

受測：`tools/lib/selfimproving/meacheck.py`（`events.mea`，`check` 第 33 項）、`meawrite.py`
（`measure` 的 CLI 契約、拒收與並行）、`status.py`、`export.py`（`window` 末鍵與 `measure` 物件）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p3_fixtures as f3
from _selfimproving_p3_fixtures import D3, evl, win

from lib import apply_lock
from lib.selfimproving import evwrite, meacheck
from lib.selfimproving import meawrite as si_meawrite
from lib.selfimproving import transcript as si_transcript

PROBE = fx.ROOT / "tools" / "probe" / "selfimproving_measure.py"
S1 = fx.obs_id(2)
TUPLE_KEYS = {"mea.report-baseline": 14, "mea.open": 7, "mea.close": 8, "mea.amend": 9}


def setUpModule():
    fx.setup("si_p3v_")


def tearDownModule():
    fx.teardown()


def adopt(R):
    f3.s_base(R)
    f3.s_adopt(R)


class VerbTestCase(f3.P3TestCase):
    def scenario(self, build):
        self.new_home()
        R = f3.p3_base()
        s = build(R)
        fx.commit_all(R, "scenario")
        return R, s

    def measure_ok(self, R, *extra):
        rc, out, err = self.M(R, "measure", *extra)
        self.assertEqual(rc, 0, out + err)
        return out

    def probe(self, R, *extra):
        cp = subprocess.run([sys.executable, str(PROBE), "--repo", str(R), "--json", *extra],
                            capture_output=True, check=False)
        return cp.returncode, json.loads(cp.stdout.decode("utf-8")) if cp.stdout else None


class TestEventTableAndCheck(VerbTestCase):
    def test_AT_340_1_1_written_events_match_the_table_and_check_is_green(self):
        def pend(R):
            s = f3.s_pend(R)
            return s

        for build in (adopt, f3.s_rec, pend):
            with self.subTest(build=build.__name__):
                R, s = self.scenario(build)
                self.measure_ok(R)
                if build is pend:
                    rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c1"], "--by", "main")
                    self.assertEqual(rc, 0, out + err)
                res = self.check(R)
                self.assertEqual(len(res["items"]), 33)
                self.assertEqual(res["items"][32]["id"], "events.mea")
                for item in ("events.mea", "events.transitions"):
                    self.assertEqual(self.S(res, item), "PASS", item)
                self.assertEqual((res["overall"], res["_rc"]), ("PASS", 0))
                limit = json.loads(fx.read(R, fx.PARAMS))["event_max_bytes"]
                for e in win(R):
                    kind = e["kind"] if e.get("report") != "baseline" else "mea.report-baseline"
                    if e.get("report") == "check":
                        continue
                    self.assertEqual(len(e), TUPLE_KEYS[kind], e)
                    self.assertEqual(e["by"], "main")
                    self.assertRegex(
                        e["t"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
                    self.assertLessEqual(len(fx.dumps_line(e).encode("utf-8")), limit)

    def neg_cases(self, R, base_seqs, other_prop):
        """MEA-NEG（§5.4）：十四列各一處改寫；回 `{N: (動作, 預期碼集合)}`。"""
        seqs = base_seqs
        add_check = lambda **o: fx.append_events(R, [f3.ev3("mea.report", **{  # noqa: E731
            k: v for k, v in f3.check_event(**o).items() if k != "kind"})])
        return {
            "N1": (lambda: f3.drop_key(R, seqs["open"], "w_opp"), {"MEA-KEY-MISSING"}),
            "N2": (lambda: fx2.rewrite_event(R, seqs["close"], note="x"), {"MEA-KEY-UNKNOWN"}),
            "N3": (lambda: add_check(prop=seqs["prop"]), {"MEA-KEY-UNKNOWN"}),
            "N4": (lambda: fx2.rewrite_event(R, seqs["open"], w_opp="5"), {"MEA-TYPE"}),
            "N5": (lambda: fx2.rewrite_event(R, seqs["base"], events=-1), {"MEA-TYPE"}),
            "N6": (lambda: add_check(missing=["x" * 61]), {"MEA-TYPE"}),
            "N7": (lambda: fx2.rewrite_event(R, seqs["close"], result="weird"), {"MEA-ENUM"}),
            "N8": (lambda: fx2.rewrite_event(R, seqs["base"], report="weird"), {"MEA-ENUM"}),
            "N9": (lambda: fx2.rewrite_event(R, seqs["close"], n_opp=6), {"MEA-CLOSE-N"}),
            "N10": (lambda: fx2.rewrite_event(R, seqs["close"], n_opp=4), {"MEA-CLOSE-N"}),
            "N11": (lambda: fx2.rewrite_event(R, seqs["open"], promote_seq=1),
                    {"MEA-PROMOTE-SEQ"}),
            "N12": (lambda: fx2.rewrite_event(R, seqs["open"], prop=other_prop),
                    {"MEA-NOT-PROMOTED"}),
            "N13": (lambda: f3.rewrite_events(R, lambda evs: _dup_baseline(evs)),
                    {"MEA-BASELINE-DUP"}),
            "N14": (lambda: f3.rewrite_events(R, lambda evs: _baseline_after_open(evs)),
                    {"MEA-BASELINE-ORDER"}),
        }

    def test_AT_340_1_E_1_field_table_negatives_each_report_exactly_their_code(self):
        R0, _ = self.scenario(adopt)
        _, _, _, other = f3.try_prop(R0, fx.rid(1), action="add", target=f"{D3}/np.md")
        fx.commit_all(R0, "np")
        self.measure_ok(R0)
        control = self.check(R0)
        self.assertEqual(self.S(control, "events.mea"), "PASS")
        evs = fx.EV(R0)
        seqs = {"prop": next(e["prop"] for e in evs if e["kind"] == "mea.open"),
                "base": next(e["seq"] for e in evs if e.get("report") == "baseline"),
                "open": next(e["seq"] for e in evs if e["kind"] == "mea.open"),
                "close": next(e["seq"] for e in evs if e["kind"] == "mea.close")}
        same = {i["id"]: i["status"] for i in control["items"]}
        for label in [f"N{k}" for k in range(1, 15)]:
            with self.subTest(label=label):
                R = fx.new_dir("neg")
                shutil.copytree(R0, R)
                action, want = self.neg_cases(R, seqs, other)[label]
                action()
                res = self.check(R)
                self.assertEqual(self.S(res, "events.mea"), "FAIL")
                self.assertEqual({c for _, c in self.F(res, "events.mea")}, want)
                for item in res["items"]:
                    if item["id"] == "events.mea":
                        continue
                    if label == "N7" and item["id"] == "events.transitions":
                        continue  # 既有 fold：result 表外值＝TRANSITION-ILLEGAL（P1 行為，⚖）
                    if label == "N12" and item["id"] == "events.transitions":
                        continue  # 未晉升 PROP 的 mea.open：fold 記 TRANSITION-ILLEGAL（只放過它）
                    self.assertEqual(item["status"], same[item["id"]], (label, item["id"]))

    def test_AT_340_1_E_2_rules_revision_item_order_and_absent_carrier(self):
        P0 = fx.p1_base()
        self.new_home()
        r0 = self.check(P0)
        R_none = f3.p3_base()
        R_adopt, _ = self.scenario(adopt)
        self.measure_ok(R_adopt)
        names = fx.P0_ITEMS21 + fx.P1_ITEMS7 + fx.P2_ITEMS4
        for label, R in (("p0", P0), ("none", R_none), ("adopt", R_adopt)):
            res = self.check(R)
            self.assertEqual(res["fingerprint_parts"]["check_rules_rev"], 4, label)
            ids = [i["id"] for i in res["items"]]
            self.assertEqual((ids[:32], ids[32]), (names, "events.mea"), label)
        item = r0["_item"]["events.mea"]
        self.assertEqual((item["status"], item["blocking"]), ("NE", False))
        self.assertEqual([f["code"] for f in item["findings"]], ["CARRIER-NOT-ESTABLISHED"])
        self.assertEqual((r0["overall"], r0["_rc"]), ("PASS", 0))
        for R in (R_none, R_adopt):
            self.assertEqual(self.S(self.check(R), "events.mea"), "PASS")

    @staticmethod
    def codes(events):
        return sorted({f.code for f in meacheck.findings(events)})

    def test_AT_340_1_E_3_missing_list_must_be_sorted_and_deduplicated(self):
        def codes(missing):
            ev = {**f3.check_event(missing=missing), "seq": 1, "t": f3.TA, "by": "main"}
            return self.codes([ev])

        for missing in ([], ["a"], ["a", "b"], ["no-evaluable-window", "sample-below-w-min"]):
            self.assertEqual(codes(missing), [], missing)
        for missing in (["b", "a"], ["a", "a"], ["a", "c", "b"], "a", [1]):
            self.assertEqual(codes(missing), ["MEA-TYPE"], missing)

    def test_AT_340_1_E_4_open_before_promote_is_not_promoted_a_wrong_seq_is_promote_seq(self):
        prop = f3.pid(1)
        promote = {"seq": 1, "t": f3.TA, "kind": "app.promote", "by": "main", "prop": prop}

        def opened(seq, promote_seq):
            return {"seq": seq, "t": f3.TA, "kind": "mea.open", "by": "main", "prop": prop,
                    "w_opp": 5, "promote_seq": promote_seq}

        self.assertEqual(self.codes([promote, opened(2, 1)]), [])
        # `promote_seq` 欄位等於 app.promote 的 seq，仍因 mea.open 排在它之前（或同 seq）而拒
        self.assertEqual(self.codes([opened(1, 2), {**promote, "seq": 2}]), ["MEA-NOT-PROMOTED"])
        self.assertEqual(self.codes([promote, opened(1, 1)]), ["MEA-NOT-PROMOTED"])
        self.assertEqual(self.codes([opened(1, 1)]), ["MEA-NOT-PROMOTED"])
        self.assertEqual(self.codes([promote, opened(2, 9)]), ["MEA-PROMOTE-SEQ"])


def _dup_baseline(evs):
    i = next(k for k, e in enumerate(evs) if e.get("report") == "baseline")
    return [*evs[:i + 1], dict(evs[i]), *evs[i + 1:]]


def _baseline_after_open(evs):
    i = next(k for k, e in enumerate(evs) if e.get("report") == "baseline")
    j = next(k for k, e in enumerate(evs) if e["kind"] == "mea.open")
    return [*evs[:i], *evs[i + 1:j + 1], evs[i], *evs[j + 1:]]


class TestMeasureVerb(VerbTestCase):
    def test_AT_340_2_1_cli_contract_text_json_order_and_lock(self):
        R, s = self.scenario(adopt)
        P = self.status(R)  # 取 PROP 號之前先確認 status 可跑
        P = next(e["id"] for e in fx.EV(R) if e["kind"] == "prop")
        rc, out, err = self.M(R, "measure", "--by", "ops1")
        self.assertEqual(rc, 0, out + err)
        lines = out.splitlines()
        self.assertEqual(lines[0], "ok measure events=3 props=1")
        self.assertRegex(
            lines[1], rf"^window {P} state=closed result=clean n_opp=5/5 baseline=2/5$")
        new = win(R)
        self.assertEqual([(e["kind"], e["by"]) for e in new],
                         [("mea.report", "ops1"), ("mea.open", "ops1"), ("mea.close", "ops1")])
        before = fx2.snapshot_tree(self.home)
        raw = self.M(R, "measure", "--json")[1]
        obj = json.loads(raw)
        self.assertEqual(list(obj), ["ok", "kind", "events", "props", "appended", "windows",
                                     "rollback_cards", "check_report"])
        self.assertEqual((obj["events"], obj["appended"], obj["check_report"]), (0, [], None))
        after = fx2.snapshot_tree(self.home)
        self.assertTrue(set(after) - set(before) <= {k for k in after if k.endswith(".lock")})

    def test_AT_340_2_2_record_check_keeps_the_falsification_record(self):
        def build_a(R):
            f3.s_probe_a(R)

        R, _ = self.scenario(build_a)
        n0 = len(win(R))
        out1 = self.measure_ok(R, "--record-check")
        self.assertIn("check-report appended=true", out1)
        reports = [e for e in win(R) if e.get("report") == "check"]
        self.assertEqual(len(win(R)) - n0, 1)
        rep = reports[0]
        self.assertNotIn("prop", rep)
        self.assertEqual((rep["windows"], rep["m1_n"], rep["m4"], rep["m5_n"], rep["falsified"],
                          rep["metrics_rev"]), (3, 3, 0, 6, False, 1))
        rc, probe = self.probe(R)
        self.assertEqual((rc, rep["fingerprint"]), (0, probe["fingerprint"]))
        out2 = self.measure_ok(R, "--record-check")
        self.assertIn("check-report appended=false", out2)
        self.assertEqual(len([e for e in win(R) if e.get("report") == "check"]), 1)
        p9 = f3.promoted(R, target=f"{D3}/p9.md")
        f3.mea_chain(R, p9, "clean")
        self.assertIn("appended=true", self.measure_ok(R, "--record-check"))
        self.assertEqual(len([e for e in win(R) if e.get("report") == "check"]), 2)
        limit = json.loads(fx.read(R, fx.PARAMS))["event_max_bytes"]
        self.assertTrue(all(len(fx.dumps_line(e).encode("utf-8")) <= limit for e in win(R)))
        self.assertEqual(self.S(self.check(R), "events.mea"), "PASS")
        R2, _ = self.scenario(lambda r: None)
        self.measure_ok(R2, "--record-check")
        rep2 = [e for e in win(R2) if e.get("report") == "check"][0]
        self.assertEqual((rep2["windows"], rep2["m1"], rep2["falsified"]), (0, None, None))
        self.assertIn("no-evaluable-window", rep2["missing"])
        self.assertEqual(self.S(self.check(R2), "events.mea"), "PASS")

    def test_AT_340_2_E_1_refusals_and_usage_errors(self):
        R, _ = self.scenario(adopt)
        e0, h0 = evl(R), fx2.snapshot_tree(self.home)

        def untouched():
            self.assertEqual(evl(R), e0)

        for value in ("0", "1"):
            with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": value}):
                rc, out, err = self.M(R, "measure")
            self.rejected(rc, out, {"UNATTENDED-REFUSED"})
            untouched()
        rc, out, err = self.M(R, "measure", "--force")
        self.usage_error(rc, out, err)
        rc, out, err = self.M(R, "measure", "--by", "a b")
        self.usage_error(rc, out, err)
        good = fx.read(R, fx.PARAMS)
        fx.set_params(R, w_opp=KeyError)
        rc, out, err = self.M(R, "measure")
        self.usage_error(rc, out, err)
        self.assertIn("w_opp", err)
        fx.put(R, fx.PARAMS, good)
        bad_home = fx.new_dir("nohome")
        bad_home.write_bytes(b"x")
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(bad_home)}):
            rc, out, err = self.M(R, "measure")
        self.usage_error(rc, out, err)
        self.assertIn("HOME-UNWRITABLE", err)
        untouched()
        si = self.home
        ledger = R / fx.EVL
        evwrite.ensure_home(si)
        with mock.patch.object(evwrite, "LOCK_TIMEOUT_SECONDS", 0.3):
            with apply_lock.acquire(evwrite.lock_path_for(si, ledger), 5, 300):
                rc, out, err = self.M(R, "measure")
        self.rejected(rc, out, {"LOCK-BUSY"})
        untouched()
        self.assertEqual(self.M(R, "measure")[0], 0)
        self.assertTrue(h0 is not None)

    def test_AT_340_2_E_2_concurrent_measures_do_not_duplicate_events(self):
        R, _ = self.scenario(adopt)
        n0 = len(fx.EV(R))

        def hook():
            import time
            time.sleep(0.05)

        with mock.patch.object(evwrite, "PAUSE_HOOK", hook), ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(si_meawrite.measure, R, by="main") for _ in range(2)]
            results = [f.result() for f in futures]
        self.assertEqual([r.rc for r in results], [0, 0])
        evs = fx.EV(R)
        kinds = [e["kind"] for e in evs[n0:]]
        self.assertEqual(sorted(kinds), ["mea.close", "mea.open", "mea.report"])
        self.assertEqual([e["seq"] for e in evs], list(range(1, len(evs) + 1)))
        self.assertEqual(sum(r.obj["events"] for r in results), len(evs) - n0)

    def test_AT_340_2_E_3_a_plan_that_never_empties_is_cut_off_at_five_per_prop(self):
        R, s = self.scenario(f3.s_base)
        endless = {"kind": "mea.open", "prop": s["P"], "w_opp": 5,
                   "promote_seq": f3.promote_seq(R, s["P"])}
        n0 = len(fx.EV(R))
        plans = [[dict(endless)] for _ in range(9)] + [[]] * 3
        with mock.patch.object(si_meawrite.meaplan, "plan", side_effect=plans):
            res = si_meawrite.measure(R, by="main")
        self.assertEqual(res.rc, 1, res.text)
        self.assertIn("MEASURE-NOT-CONVERGING", res.text)
        self.assertEqual(len(fx.EV(R)) - n0, 5)  # 上限＝5 × 1 個 promoted PROP；第 6 筆起零追加

    def test_AT_340_2_E_4_every_line_of_a_batch_is_size_checked_all_or_nothing(self):
        ledger = fx.new_dir("evw")
        ledger.mkdir()
        ledger = ledger / "ledger.jsonl"
        ok = {"kind": "mea.open", "by": "main", "prop": f3.pid(1), "w_opp": 5, "promote_seq": 1}
        big = {"kind": "mea.amend", "by": "main", "prop": f3.pid(1), "note": "x" * 300}
        for batch in ([ok, big], [big, ok], [big]):
            with self.assertRaises(evwrite.Reject) as cm:
                evwrite.append_event(ledger, None, lambda st, b=batch: b, max_bytes=200)
            self.assertEqual([c for c, _ in cm.exception.codes], ["EVENT-BYTES-OVER"])
            self.assertFalse(ledger.exists())
        small = {**big, "note": "x"}
        first = evwrite.append_event(ledger, None, lambda st: [ok, small], max_bytes=200)
        self.assertEqual(first["seq"], 1)
        self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 2)

    def ledger_variant(self, mode):
        def build(R):
            s = f3.s_base(R)
            path = R / f3.LEDGER
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            body = {"bytes": raw + b"\xff\xfe",
                    "nohdr": "# 觀察帳本\n\n（沒有表）\n".encode(),
                    "hdr-only": "\n".join(ln for ln in text.split("\n")
                                          if not ln.startswith("| OBS-SI-")).encode(),
                    "bom-crlf": ("﻿" + text.replace("\n", "\r\n")).encode()}[mode]
            path.write_bytes(body)
            return s
        return self.scenario(build)

    def test_AT_340_2_E_5_obs_ledger_must_decode_and_have_a_header(self):
        for mode in ("bytes", "nohdr"):
            with self.subTest(mode=mode):
                R, _ = self.ledger_variant(mode)
                e0 = evl(R)
                rc, out, err = self.M(R, "measure")
                self.rejected(rc, out, {"OBS-LEDGER-UNAVAILABLE"})
                self.assertEqual(evl(R), e0)
                self.assertEqual(self.status(R)["measure"]["reason"], "obs-ledger-unavailable")
        for mode in ("hdr-only", "bom-crlf"):  # 零列的空帳本與 BOM／CRLF 都是合法帳本
            with self.subTest(mode=mode):
                R, _ = self.ledger_variant(mode)
                self.measure_ok(R)
                base = next(e for e in win(R) if e.get("report") == "baseline")
                if mode == "hdr-only":
                    self.assertEqual((base["opp"], base["events"], base["pending"]), ([], 0, 0))
                self.assertEqual([e["kind"] for e in win(R)][:2], ["mea.report", "mea.open"])

    def test_AT_340_2_E_6_bad_mea_fields_reject_measure_and_leave_the_ledger_alone(self):
        R0, _ = self.scenario(adopt)
        self.measure_ok(R0)
        for which, key, value, code in f3.BAD_MEA:
            with self.subTest(which=which, key=key, value=value):
                R = fx.new_dir("bad")
                shutil.copytree(R0, R)
                f3.corrupt_mea(R, which, key, value)
                e0 = evl(R)
                for extra in ((), ("--record-check",)):
                    rc, out, err = self.M(R, "measure", *extra)
                    self.rejected(rc, out, {code})
                    self.assertEqual(evl(R), e0)
        R, s = self.scenario(f3.s_pend)
        self.measure_ok(R)
        f3.corrupt_mea(R, "close", "n_opp", "x")
        n0 = len(fx.EV(R))
        rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c1"], "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        evs = fx.EV(R)
        self.assertEqual((len(evs) - n0, evs[-1]["kind"]), (1, "attr.confirm"))  # 不追加 amend


class TestStatusAndExport(VerbTestCase):
    def test_AT_340_5_1_status_has_15_keys_and_live_capacity_and_measure(self):
        R, _ = self.scenario(adopt)
        self.measure_ok(R)
        fx.set_params(R, memory_index_max_lines=20)
        idx = si_transcript.transcript_dir(R) / "memory" / "MEMORY.md"
        ctrl = fx.new_dir("ctrl")
        shutil.copytree(R, ctrl)
        idx.parent.mkdir(parents=True)
        idx.write_bytes(f3.cap_index(16))
        st = self.status(R)
        keys = list(st)
        self.assertEqual(len(keys), 15)
        self.assertEqual((keys[0], keys[13], keys[14]), ("events_detected", "console_pending",
                                                          "measure"))
        m = st["measure"]
        self.assertEqual((m["status"], m["due"], m["candidates_unsettled"], m["rollback_pending"]),
                         ("read", 0, 0, []))
        self.assertEqual([(w["state"], w["result"]) for w in m["windows"]], [("closed", "clean")])
        self.assertEqual((st["capacity"]["status"], st["capacity"]["over_cap"]),
                         ("read", ["memory_index"]))
        self.assertIn("e", {e["trigger"] for e in st["events_detected"]})
        idx.unlink()
        st0 = self.status(ctrl)
        self.assertEqual((st0["capacity"]["status"], st0["capacity"]["reason"]),
                         ("NOT-EVALUABLE", "no-axis-evaluable"))
        self.assertIn("capacity NOT-EVALUABLE", self.M(ctrl, "status")[1])

    def test_AT_340_5_2_export_window_key_and_capacity_never_read_home(self):
        def build(R):
            a = f3.promoted(R, target=f"{D3}/e1.md")
            b = f3.promoted(R, target=f"{D3}/e2.md")
            c = f3.promoted(R, target=f"{D3}/e3.md")
            f3.mea_chain(R, b, "clean", stop_at="open")
            f3.mea_chain(R, c, "clean")
            return a, b, c

        R, (a, b, c) = self.scenario(build)
        sentinel = "SENTINEL-" + "p3-home-unique"
        (self.home / "sentinel.txt").write_text(sentinel, encoding="utf-8")
        idx = si_transcript.transcript_dir(R) / "memory" / "MEMORY.md"
        idx.parent.mkdir(parents=True)
        idx.write_text("- e01 INDEX-UNIQUE-CONTENT\n", encoding="utf-8")
        snap0, home0 = fx.snap(R), fx2.snapshot_tree(self.home)
        exp = self.MJ(R, "export", "--kind", "proposals")
        self.assertEqual(exp["schema_rev"], 1)
        wins = {p["id"]: p["window"] for p in exp["items"]}
        for p in exp["items"]:
            keys = list(p)
            self.assertEqual(keys[-2:], ["card", "window"])
        self.assertIsNone(wins[a])
        subkeys = ["state", "opened_seq", "closed_seq", "result", "n_opp", "baseline"]
        self.assertEqual(list(wins[b]), subkeys)
        self.assertEqual((wins[b]["closed_seq"], wins[b]["result"]), (None, None))
        self.assertEqual((wins[c]["state"], wins[c]["result"]), ("closed", "clean"))
        st = self.MJ(R, "export", "--kind", "status")
        item = st["items"][0]
        self.assertEqual(item["capacity"], {"status": "NOT-EVALUABLE",
                                            "reason": "export-reads-no-home"})
        self.assertEqual(len(item), 15)
        text = json.dumps(exp) + json.dumps(st)
        self.assertNotIn(sentinel, text)
        self.assertNotIn("INDEX-UNIQUE-CONTENT", text)
        self.assertEqual((fx.snap(R), fx2.snapshot_tree(self.home)), (snap0, home0))

    def test_AT_340_5_E_2_export_window_state_maps_a_pending_window(self):
        R, s = self.scenario(f3.s_pend)
        self.measure_ok(R)

        def window():
            items = self.MJ(R, "export", "--kind", "proposals")["items"]
            return next(p["window"] for p in items if p["id"] == s["P"])

        w = window()
        self.assertEqual((w["state"], w["result"]), ("pending", "pending"))
        self.assertEqual(self.prop_state(R, s["P"]), "measuring")  # fold 的態仍是 measuring
        rc, out, err = self.M(R, "attr-confirm", "--att", s["att_c1"], "--by", "QA")
        self.assertEqual(rc, 0, out + err)
        w = window()
        self.assertEqual((w["state"], w["result"]), ("closed", "recurred"))

    def test_AT_340_5_E_3_bad_mea_fields_are_not_evaluable_not_a_traceback(self):
        R0, _ = self.scenario(adopt)
        self.measure_ok(R0)
        for which, key, value, _code in f3.BAD_MEA:
            with self.subTest(which=which, key=key, value=value):
                R = fx.new_dir("bad")
                shutil.copytree(R0, R)
                f3.corrupt_mea(R, which, key, value)
                want = {"status": "NOT-EVALUABLE", "reason": "mea-events-invalid"}
                rc, out, err = self.M(R, "status", "--json")
                self.assertEqual((rc, err), (0, ""), out)
                self.assertEqual(json.loads(out)["measure"], want)
                rc, out, err = self.M(R, "export", "--kind", "status", "--json")
                self.assertEqual((rc, err), (0, ""), out)
                self.assertEqual(json.loads(out)["items"][0]["measure"], want)
                rc, out, err = self.M(R, "export", "--kind", "proposals", "--json")
                self.assertEqual((rc, err), (0, ""), out)
                self.assertEqual([p["window"] for p in json.loads(out)["items"]], [None])
                self.assertIn("NOT-EVALUABLE", self.M(R, "status")[1])
        rc, out, err = self.M(R0, "status", "--json")
        self.assertEqual(json.loads(out)["measure"]["status"], "read")

    def test_AT_340_5_E_1_not_evaluable_reasons_and_read_only(self):
        def with_prop(R):
            return f3.s_base(R)

        def none(R):
            return None

        def a(R):
            (R / fx.EVL).unlink()

        def b(R):
            with_prop(R)
            fx.set_params(R, migration_base_sha=None)

        def c(R):
            with_prop(R)
            for p in (R / "docs/06_quality").glob("AutoSDD_*.md"):
                p.unlink()

        want = {"a": ("NOT-EVALUABLE", "carrier-not-established"),
                "b": ("NOT-EVALUABLE", "anchor-unavailable"),
                "c": ("NOT-EVALUABLE", "defect-ledger-unavailable"), "d": ("read", None)}
        for key, build in {"a": a, "b": b, "c": c, "d": none}.items():
            with self.subTest(key=key):
                R, _ = self.scenario(build)
                snap0, home0 = fx.snap(R), fx2.snapshot_tree(self.home)
                m1 = self.status(R)["measure"]
                m2 = self.MJ(R, "export", "--kind", "status")["items"][0]["measure"]
                self.assertEqual(json.dumps(m1), json.dumps(m2))
                self.assertEqual((m1["status"], m1.get("reason")), want[key])
                if key == "d":
                    self.assertEqual((m1["due"], m1["windows"]), (0, []))
                self.assertEqual((fx.snap(R), fx2.snapshot_tree(self.home)), (snap0, home0))


if __name__ == "__main__":
    unittest.main()
