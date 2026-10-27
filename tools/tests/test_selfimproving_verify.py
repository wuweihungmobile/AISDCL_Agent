"""SelfImproving P2 `verify`、三態判定與證據的驗收測試（TCS-P2 VF 檔；`runner.py`、`verify.py`、
`verdict.py`）。方法名含 AT 底線形（錨定 `-k AT_219_1_1_` 只收一個）。夾具全用 tmp 內的合成 repo
與本機
子行程（hermetic；探針腳本由夾具寫入 held-out 目錄），不碰真帳本、不上網。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
from _selfimproving_p2_fixtures import P2TestCase

from lib.selfimproving import events as si_events
from lib.selfimproving import git as si_git
from lib.selfimproving import runner as si_runner
from lib.selfimproving import sandbox as si_sandbox
from lib.selfimproving import verdict as si_verdict


def setUpModule() -> None:
    fx.setup("si_p2v_")


def tearDownModule() -> None:
    fx.teardown()


def sandboxed(**kw):
    """已沙盒的 PROP 的獨立複本；每次換用全新家目錄與 held-out（`heldout` 由呼叫端指定）。"""
    R = fx2.p2_base()
    return R, fx2.drive_to(R, "sandboxed", **kw)


def verify_files(R: Path, p: str) -> list[Path]:
    return sorted((R / fx.PROPS_REL / p).glob("verify*.json"))


def state_of(case, R: Path, p: str) -> str:
    """PROP 現態（`export --kind proposals` 的折疊結果）。"""
    return case.MJ(R, "export", "--kind", "proposals", "--id", p)["items"][0]["state"]


def draft_rows(text: str) -> list[str]:
    return [ln for ln in text.split("\n") if ln.startswith("| OBS")]


class TestVerdictTable(unittest.TestCase):
    """AT-219-2-1（純函式）：三態判定表逐列；由 `test_AT_219_2_1_no_probes_is_ne` 呼叫（一 AT
    一函式）。"""

    def check_verdict_table(self):
        sb = {"applied": True, "touched_ok": True, "rollback_ok": True, "fail_code": None}
        fr = {"digest": fx.H(7), "n": 5}
        ve = {"probes_n": 1, "carrier_proof": True, "baseline_red": True, "patched_green": True,
              "mutated_red": True, "heldout_digest": fx.H(7), "reasons": []}

        def go(sandbox=None, verify=None, freeze=None):
            return si_verdict.verdict_of({**sb, **(sandbox or {})}, {**ve, **(verify or {})},
                                         {**fr, **(freeze or {})}, 5)
        nulls = {k: None for k in ("carrier_proof", "baseline_red", "patched_green", "mutated_red")}
        table = [
            ({}, ("PASS", [])),
            ({"verify": {"probes_n": 0, **nulls}}, ("NE", ["NO-PROBES"])),
            ({"verify": {"carrier_proof": False}}, ("NE", ["CARRIER-PROOF-FAILED"])),
            ({"verify": {"heldout_digest": fx.H(8)}}, ("NE", ["HELDOUT-DIGEST-MISMATCH"])),
            ({"freeze": {"n": 4}}, ("NE", ["HELDOUT-TOO-SMALL"])),
            ({"verify": {"carrier_proof": False}, "freeze": {"n": 4}},
             ("NE", ["CARRIER-PROOF-FAILED", "HELDOUT-TOO-SMALL"])),
            ({"verify": {"reasons": ["HELDOUT-EXPOSED"]}}, ("NE", ["HELDOUT-EXPOSED"])),
            ({"verify": {"reasons": ["EXPOSURE-UNKNOWN"]}}, ("NE", ["EXPOSURE-UNKNOWN"])),
            ({"verify": {"reasons": ["PROBE-TIMEOUT"], "baseline_red": None}},
             ("NE", ["PROBE-TIMEOUT"])),
            ({"verify": {"baseline_red": False}}, ("NE", ["BASELINE-NOT-RED"])),
            ({"verify": {"patched_green": False}}, ("FAIL", ["PATCHED-NOT-GREEN"])),
            ({"verify": {"mutated_red": False}}, ("NE", ["MUTATION-NOT-RED"])),
            ({"verify": {"mutated_red": None}}, ("NE", ["MUTATION-ABSENT"])),
            ({"verify": {"baseline_red": False, "patched_green": False}},
             ("NE", ["BASELINE-NOT-RED"])),
            ({"sandbox": {"applied": False, "touched_ok": None, "rollback_ok": None}},
             ("NE", ["SANDBOX-NOT-APPLIED"])),
            ({"sandbox": {"applied": False, "touched_ok": None, "rollback_ok": None,
                          "fail_code": "SANDBOX-APPLY-TIMEOUT"}},
             ("NE", ["SANDBOX-APPLY-TIMEOUT"])),
            ({"sandbox": {"applied": False, "touched_ok": None, "rollback_ok": None,
                          "fail_code": "SANDBOX-EXPORT-FAILED"}},
             ("NE", ["SANDBOX-EXPORT-FAILED"])),
            ({"sandbox": {"touched_ok": False}}, ("NE", ["TOUCHED-SUPERSET"])),
            ({"sandbox": {"rollback_ok": False}}, ("FAIL", ["ROLLBACK-DRYRUN-FAILED"])),
            ({"sandbox": {"touched_ok": False, "rollback_ok": False}},
             ("NE", ["TOUCHED-SUPERSET", "ROLLBACK-DRYRUN-FAILED"])),
        ]
        for kw, want in table:
            with self.subTest(kw):
                got = go(**kw)
                self.assertEqual(got, want)
                self.assertEqual(got[0] == "PASS", got[1] == [])
                self.assertIn(got[0], ("PASS", "FAIL", "NE"))


class TestRunner(unittest.TestCase):
    def test_runner_masks_and_tail(self):
        text = ("Authorization: Bearer abcdef0123456789abcdef\nkey=" + "s"
                "k-ABCDEF0123456789abcdef"
                "\npostgres://admin:s3cr3tpw@db.example/x\nAuthorization: Basic dXNlcjpwYXNz")
        masked = si_runner.mask(text)
        for secret in ("abcdef0123456789abcdef", "ABCDEF0123456789abcdef", "s3cr3tpw",
                       "dXNlcjpwYXNz"):
            self.assertNotIn(secret, masked)
        self.assertEqual(len(si_runner._tail(("結" * 400).encode("utf-8")).encode("utf-8")) % 3, 0)


class TestVerify(P2TestCase):
    def fresh(self, **kw):
        self.new_home()
        return sandboxed(**kw)

    def held(self, **kw):
        return fx2.make_heldout(fx.new_dir("ho"), **kw)

    def test_AT_219_1_1_three_steps_pass(self):
        counter = fx.new_dir("cnt").with_suffix(".txt")
        R, p = self.fresh(heldout=self.held(counter=counter))
        sb_dir = self.home / "sandbox" / p
        sb0, s0 = fx2.manifest_raw(sb_dir), fx.snap(R)
        rc, out, err = self.M(R, "verify", p, "--by", "VF1", "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        self.assertEqual(list(obj), ["ok", "kind", "seq", "id", "verdict", "probes_n", "reasons",
                                     "baseline_red", "patched_green", "mutated_red",
                                     "carrier_proof"])
        self.assertEqual((obj["verdict"], obj["probes_n"], obj["reasons"]), ("PASS", 1, []))
        self.assertTrue(all(obj[k] is True for k in ("baseline_red", "patched_green",
                                                     "mutated_red", "carrier_proof")))
        ev = fx2.last_event(R, "app.verify")
        self.assertEqual(list(ev), ["seq", "t", "kind", "by", "id", "prop", "rev", "verdict",
                                    "baseline_red", "patched_green", "mutated_red",
                                    "carrier_proof", "probes_n", "verify_sha256",
                                    "heldout_digest", "reasons"])
        self.assertEqual(ev["by"], "VF1")
        self.assertEqual(ev["heldout_digest"], fx2.last_event(R, "heldout.freeze")["digest"])
        vf = verify_files(R, p)
        self.assertEqual([x.name for x in vf], ["verify1.json"])
        raw = vf[0].read_bytes()
        self.assertEqual(ev["verify_sha256"], "sha256:" + hashlib.sha256(raw).hexdigest())
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n"))
        doc = json.loads(raw)
        self.assertEqual(list(doc), ["schema_rev", "prop", "rev", "k", "base", "heldout_digest",
                                     "carrier", "steps"])
        self.assertEqual((doc["k"], doc["carrier"]), (1, {}))
        rcs = [[r["rc"] for r in doc["steps"][s]] for s in ("baseline", "patched", "mutated")]
        self.assertEqual(rcs, [[1], [0], [1]])
        rec = doc["steps"]["baseline"][0]
        self.assertEqual(rec["cmd"][0], "{python}")
        self.assertTrue(any("{heldout}" in a for a in rec["cmd"]))
        self.assertTrue(any("{sandbox}" in a for a in rec["cmd"]))
        self.assertEqual((rec["timed_out"], rec["n_pop"]), (False, 5))
        self.assertEqual(len(counter.read_text(encoding="utf-8").splitlines()), 3)
        self.assertEqual(fx2.manifest_raw(sb_dir), sb0)
        files, _ = fx.snap(R)
        added = set(files) - set(s0[0])
        self.assertEqual(added, {f"{fx.PROPS_REL}/{p}/verify1.json"})
        self.assertEqual(self.S(self.check(R), "events.verdict"), "PASS")
        self.assertEqual(self.S(self.check(R), "events.prop_files"), "PASS")
        # 文字形態（另一份複本）
        R2, p2 = self.fresh(heldout=self.held())
        rc, out, err = self.M(R2, "verify", p2)
        self.assertRegex(out, r"^ok app\.verify seq=\d+ id=APP-SI-\d{3} verdict=PASS probes_n=1 "
                              r"reasons=-\n$")

    def test_AT_219_2_1_no_probes_is_ne(self):
        TestVerdictTable().check_verdict_table()
        R, p = self.fresh(heldout=self.held(probes="none"))
        calls = []
        real = si_runner.run_probe
        with mock.patch.object(si_runner, "run_probe", lambda *a, **k: calls.append(1) or real(
                *a, **k)):
            rc, out, err = self.M(R, "verify", p, "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        self.assertEqual((obj["verdict"], obj["reasons"], obj["probes_n"]), ("NE", ["NO-PROBES"],
            0))
        ev = fx2.last_event(R, "app.verify")
        self.assertIsNone(ev["verify_sha256"])
        self.assertEqual([ev[k] for k in ("baseline_red", "patched_green", "mutated_red",
                                          "carrier_proof")], [None] * 4)
        self.assertEqual(calls, [])
        self.assertEqual(verify_files(R, p), [])
        self.assertEqual(self.S(self.check(R), "events.verdict"), "PASS")

    def test_AT_217_1_1_within_limits_and_endpoint(self):
        R, p = self.fresh(heldout=self.held(probes="slow", delay=1))
        fx.set_params(R, probe_timeout_seconds=4, verify_runs_max=2)
        for k in (1, 2):
            t0 = time.monotonic()
            rc, out, err = self.M(R, "verify", p, "--json")
            self.assertEqual(rc, 0, out + err)
            self.assertLess(time.monotonic() - t0, 15)
            obj = json.loads(out)
            self.assertEqual((obj["verdict"], obj["reasons"]), ("PASS", []), out)
        docs = [json.loads(x.read_text(encoding="utf-8")) for x in verify_files(R, p)]
        self.assertEqual(len(docs), 2)
        for d in docs:
            recs = [r for s in ("baseline", "patched", "mutated") for r in d["steps"][s]]
            self.assertTrue(all(r["timed_out"] is False for r in recs))
        res = self.check(R)
        for item in ("events.transitions", "events.prop_files", "events.verdict"):
            self.assertEqual(self.S(res, item), "PASS", item)

    def test_AT_217_1_E_1_runs_exceeded(self):
        R, p = self.fresh(heldout=self.held())
        for _ in range(2):
            self.assertEqual(self.M(R, "verify", p)[0], 0)
        snap0, home0 = fx.snap(R), sorted(fx.tree_files(self.home))
        calls = []
        real = si_runner.run_probe
        with mock.patch.object(si_runner, "run_probe", lambda *a, **k: calls.append(1) or real(
                *a, **k)):
            rc, out, err = self.M(R, "verify", p)
        self.rejected(rc, out, {"VERIFY-RUNS-EXCEEDED"})
        self.assertIn("升級人工", out)
        self.draft_ok(R, out)
        self.assertEqual((fx.snap(R), sorted(fx.tree_files(self.home))), (snap0, home0))
        self.assertEqual(calls, [])
        Rb, pb = self.fresh(heldout=self.held())
        fx.set_params(Rb, verify_runs_max=1)
        self.assertEqual(self.M(Rb, "verify", pb)[0], 0)
        rc, out, err = self.M(Rb, "verify", pb)
        self.rejected(rc, out, {"VERIFY-RUNS-EXCEEDED"})

    def test_AT_219_1_E_1_steps_missing(self):
        always_ok = {"probes": "always_ok"}
        cases = {
            "a": (dict(probes="always_ok"), None, "NE", ["BASELINE-NOT-RED"], (False, True, False)),
            "b": (dict(probes="always_red"), None, "FAIL", ["PATCHED-NOT-GREEN"], (True, False,
            True)),
            "c": (dict(mutation="noop"), None, "NE", ["MUTATION-NOT-RED"], (True, True, False)),
            "d": (dict(mutation=None), None, "NE", ["MUTATION-ABSENT"], (True, True, None)),
        }
        del always_ok
        for label, (kw, _, verdict_, reasons, flags) in cases.items():
            with self.subTest(label):
                R, p = self.fresh(heldout=self.held(**kw))
                rc, out, err = self.M(R, "verify", p, "--json")
                self.assertEqual(rc, 0, out + err)
                obj = json.loads(out)
                self.assertEqual((obj["verdict"], obj["reasons"]), (verdict_, reasons))
                self.assertEqual((obj["baseline_red"], obj["patched_green"], obj["mutated_red"]),
                                 flags)
                res = self.check(R)
                self.assertEqual(self.S(res, "events.verdict"), "PASS")
                self.assertEqual(self.S(res, "events.prop_files"), "PASS")
        # (e) 兩個突變來源並存：rc 3、零寫入；(f) 只給旗標：PASS
        R, p = self.fresh(heldout=self.held())
        before = (R / fx.EVL).read_bytes()
        mut = self.home / "sandbox" / ".." / "heldout" / p / "mutation.patch"
        self.usage_error(*self.M(R, "verify", p, "--mutation", mut))
        self.assertEqual((R / fx.EVL).read_bytes(), before)
        held = self.held(mutation=None)
        flag = fx2.mutation_patch(True)
        flag_path = fx.new_dir("mut").with_suffix(".patch")
        flag_path.write_bytes(flag)
        R, p = self.fresh(heldout=held)
        rc, out, err = self.M(R, "verify", p, "--mutation", flag_path, "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        self.assertEqual((obj["verdict"], obj["mutated_red"]), ("PASS", True))

    def test_AT_217_1_E_2_probe_timeout_kills_the_tree(self):
        # (標籤, 探針, (baseline_red, patched_green, mutated_red), patched 步筆數, mutated 步筆數)
        cases = (("a", "hang", (None, None, None), 0, None),
                 ("b", "hang_fixed", (True, None, None), 1, None),
                 ("c", "hang_mutated", (True, True, None), 1, 1))
        for label, probes, flags, n_patched, n_mutated in cases:
            with self.subTest(label):
                tmp = fx.new_dir("hb")
                tmp.mkdir()
                hb, pidfile = tmp / "hb.txt", tmp / "pid.txt"
                src = self.held(probes=probes)
                m = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
                m["probes"][0]["argv"] = [a.replace("{heldout}/hb", str(hb)).replace(
                    "{heldout}/pidfile", str(pidfile)) for a in m["probes"][0]["argv"]]
                (src / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
                R, p = self.fresh(heldout=src)
                fx.set_params(R, probe_timeout_seconds=2)
                self.addCleanup(self._reap, pidfile, hb)
                t0 = time.monotonic()
                rc, out, err = self.M(R, "verify", p, "--json")
                self.assertEqual(rc, 0, out + err)
                self.assertLess(time.monotonic() - t0, 15)
                obj = json.loads(out)
                self.assertEqual((obj["verdict"], obj["reasons"]), ("NE", ["PROBE-TIMEOUT"]))
                s0 = hb.stat().st_size if hb.exists() else 0
                time.sleep(1.5)
                s1 = hb.stat().st_size if hb.exists() else 0
                self.assertGreater(s0, 0)
                self.assertEqual(s1, s0)
                doc = json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))
                hung = [r for s in ("baseline", "patched", "mutated")
                        for r in doc["steps"][s] or [] if r["timed_out"]]
                self.assertEqual([(r["timed_out"], r["rc"]) for r in hung], [(True, None)])
                self.assertEqual(fx2.manifest_raw(self.home / "sandbox" / p),
                                 fx2.last_event(R, "app.sandbox")["sandbox_sha256"])
                # 步驟欄位：逾時步驟記 null（不是 False）、其後步驟不執行（TCS 第二個 And）
                ev = fx2.last_event(R, "app.verify")
                for got in (obj, ev):
                    self.assertEqual((got["baseline_red"], got["patched_green"],
                                      got["mutated_red"]), flags)
                self.assertIsNotNone(ev["verify_sha256"])
                steps = doc["steps"]
                mutated = steps["mutated"]
                self.assertEqual((len(steps["patched"]), None if mutated is None else len(mutated)),
                                 (n_patched, n_mutated))
                # PROP 態與草稿列：態仍為 verified、草稿恰一列且症狀含 si verify 與 PROBE-TIMEOUT
                self.assertEqual(state_of(self, R, p), "verified")
                rows = draft_rows(obj["obs_draft"])
                self.assertEqual(len(rows), 1, rows)
                self.assertTrue("si verify" in rows[0] and "PROBE-TIMEOUT" in rows[0], rows)
                if label == "a":  # 文字形態：stdout 末尾為 `obs-draft:` 加恰一行草稿列
                    rc, out, err = self.M(R, "verify", p)
                    self.assertEqual(rc, 0, out + err)
                    lines = out.rstrip("\n").split("\n")
                    self.assertEqual(lines[-2], "obs-draft:")
                    self.assertTrue(lines[-1].startswith("| OBS") and "PROBE-TIMEOUT" in lines[-1])

    def _reap(self, pidfile: Path, hb: Path) -> None:
        try:
            if time.time() - hb.stat().st_mtime < 1.0:  # 心跳 1 s 內才砍（PID 重用會誤砍，rc=15）
                os.kill(int(pidfile.read_text(encoding="utf-8")), 15)
        except (OSError, ValueError):
            pass


def ledger(R: Path) -> bytes:
    return (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""


def events_of(R: Path, kind: str) -> list[dict]:
    return [e for e in fx.EV(R) if e["kind"] == kind]


class VerifyHelpers:
    def run_json(self, R, p, *argv):
        rc, out, err = self.M(R, "verify", p, "--json", *argv)
        self.assertEqual(rc, 0, out + err)
        return json.loads(out)

    def fresh(self, **kw):
        self.new_home()
        return sandboxed(**kw)

    def held(self, **kw):
        return fx2.make_heldout(fx.new_dir("ho"), **kw)


class TestVerifyPreconditionsAndCarrier(VerifyHelpers, P2TestCase):
    def test_AT_219_1_E_2_carrier_proof(self):
        decoy = fx.new_dir("decoy")
        (decoy / "demo_pkg").mkdir(parents=True)
        (decoy / "demo_pkg" / "core.py").write_text("VALUE = 99\n", encoding="utf-8")
        R, p = self.fresh(heldout=self.held(module="json"))
        obj = self.run_json(R, p)
        self.assertEqual((obj["carrier_proof"], obj["verdict"], obj["reasons"]),
                         (False, "NE", ["CARRIER-PROOF-FAILED"]))
        self.assertEqual((obj["baseline_red"], obj["patched_green"], obj["mutated_red"]),
                         (True, True, True))
        with mock.patch.dict(os.environ, {"PYTHONPATH": str(decoy)}):
            R, p = self.fresh(heldout=self.held(module="demo_pkg.core"))
            obj = self.run_json(R, p)
        self.assertEqual((obj["carrier_proof"], obj["verdict"]), (True, "PASS"))
        doc = json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))
        self.assertEqual(doc["carrier"], {"demo_pkg.core": "demo_pkg/core.py"})
        R, p = self.fresh(heldout=self.held())
        obj = self.run_json(R, p)
        self.assertEqual((obj["carrier_proof"], obj["verdict"]), (True, "PASS"))
        self.assertEqual(json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))["carrier"],
            {})
        with mock.patch.dict(os.environ, {"PYTHONPATH": str(decoy)}):
            R, p = self.fresh(heldout=self.held(probes="flags", module="demo_pkg.core"))
            self.run_json(R, p)
        doc = json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))
        tail = doc["steps"]["baseline"][0]["tail"]
        self.assertIn("isolated=0", tail)
        self.assertIn("safe_path=False", tail)

    def test_AT_219_1_E_3_preconditions_drift_race(self):
        def refused(label, R, argv, code):
            s0, ev0 = fx.snap(R), ledger(R)
            rc, out, err = self.M(R, "verify", *argv)
            self.rejected(rc, out, {code}, label)
            self.draft_ok(R, out, label)
            self.assertEqual((fx.snap(R), ledger(R)), (s0, ev0), label)
        R, p = self.fresh()
        refused("e", R, [f"PROP-SI-{int(p[-3:]) + 900}"], "PROP-NOT-FOUND")
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            refused("d", R, [p], "UNATTENDED-REFUSED")
        Rc, pc = self.fresh()
        fx2.drop_events(Rc, "heldout.freeze", pc)
        refused("c", Rc, [pc], "HELDOUT-NOT-FROZEN")
        self.new_home()
        Ra = fx2.p2_base()
        refused("a", Ra, [fx2.drive_to(Ra, "approved")], "STATE-NOT-VERIFIABLE")
        self.new_home()
        Rb = fx2.p2_base()
        refused("b", Rb, [fx2.drive_to(Rb, "promoted")], "STATE-NOT-VERIFIABLE")
        for label, prm, expect in (("f", {"probe_timeout_seconds": 0}, "probe_timeout_seconds"),
                                   ("g", {"verify_runs_max": True}, "verify_runs_max")):
            Rf, pf = self.fresh()
            fx.set_params(Rf, **prm)
            s0 = fx.snap(Rf)
            rc, out, err = self.M(Rf, "verify", pf)
            self.usage_error(rc, out, err, label)
            self.assertIn(expect, err)
            self.assertEqual(fx.snap(Rf), s0)
        Rh, ph = self.fresh()
        afile = fx.new_dir("afile")
        afile.write_text("x", encoding="utf-8")
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(afile)}):
            rc, out, err = self.M(Rh, "verify", ph)
        self.usage_error(rc, out, err, "h")
        self.assertIn("HOME-UNWRITABLE", err)
        self.usage_error(*self.M(Rh, "verify", ph, "--override"), "i")
        self.usage_error(*self.M(Rh, "verify"), "j")
        clean = self.run_json(*self.fresh())
        for label, damage in (("k", lambda box: shutil.rmtree(box)),
                              ("l", lambda box: (box / "stray.txt").write_text("s",
                              encoding="utf-8"))):
            Rk, pk = self.fresh()
            box = self.home / "sandbox" / pk
            sha = fx2.last_event(Rk, "app.sandbox")["sandbox_sha256"]
            damage(box)
            obj = self.run_json(Rk, pk)
            self.assertEqual((obj["verdict"], obj["reasons"]), (clean["verdict"], clean["reasons"]))
            self.assertEqual(fx2.manifest_raw(box), sha)
            self.assertFalse((box / "stray.txt").exists())
        Rm, pm = self.fresh()
        fx2.rewrite_event(Rm, fx2.last_event(Rm, "app.sandbox")["seq"], sandbox_sha256=fx.H(66))
        refused("m", Rm, [pm], "SANDBOX-TREE-DRIFT")
        Rn, pn = self.fresh()
        real = si_runner.run_probe
        hit = []

        def racing(*a, **k):
            if not hit:
                hit.append(1)
                fx.append_events(Rn, [self._plain_verify(Rn, pn)] * 2)
            return real(*a, **k)
        before = {x.name for x in (Rn / fx.PROPS_REL / pn).iterdir()}
        with mock.patch.object(si_runner, "run_probe", racing):
            rc, out, err = self.M(Rn, "verify", pn)
        self.rejected(rc, out, {"STATE-CHANGED"})
        self.assertEqual({x.name for x in (Rn / fx.PROPS_REL / pn).iterdir()}, before)

    @staticmethod
    def _plain_verify(R, p) -> dict:
        pe = fx2.prop_event(R, p)
        return fx.ev("app.verify", "main", prop=p, rev=pe["rev"], verdict="NE", probes_n=0,
                     baseline_red=None, patched_green=None, mutated_red=None, carrier_proof=None,
                     verify_sha256=None, heldout_digest=None, reasons=["NO-PROBES"])

    def test_d11_verify_json_rejection_is_json(self):
        """SCG-4 修復棒二後續（非 AT 命名）：`verify` 於沙盒樹重建階段的拒收（`SANDBOX-TREE-DRIFT`、
        `SANDBOX-SWAP-FAILED`）在 `--json` 下與其他拒收同形——stdout 是 JSON（TCS R69）；
        文字模式不變。"""
        for code in ("SANDBOX-TREE-DRIFT", "SANDBOX-SWAP-FAILED"):
            with self.subTest(code):
                R, p = self.fresh()
                ghost = "PROP-SI-" + f"{int(p.rsplit('-', 1)[1]) + 900:03d}"
                shape = list(json.loads(self.M(R, "verify", ghost, "--json")[1]))  # 閘門拒收的鍵序
                ctx, real = mock.MagicMock(), os.replace
                if code == "SANDBOX-TREE-DRIFT":  # 重新匯出後 manifest 仍不等於記錄值
                    fx2.rewrite_event(R, fx2.last_event(R, "app.sandbox")["seq"],
                                      sandbox_sha256=fx.H(66))
                else:  # 樹不在 ⇒ 重新匯出後換入失敗
                    shutil.rmtree(self.home / "sandbox" / p)

                    def fake(src, dst, *a, **kw):
                        if Path(dst).name == p:
                            raise PermissionError(13, "denied")
                        return real(src, dst, *a, **kw)
                    ctx = mock.patch("os.replace", side_effect=fake)
                with ctx:
                    rc, out, err = self.M(R, "verify", p, "--json")
                    rc_t, out_t, err_t = self.M(R, "verify", p)
                obj = json.loads(out)  # 修前這裡是文字拒收，json.loads 會炸
                self.assertEqual((rc, obj["ok"], obj["rc"], obj["verb"]), (1, False, 1, "verify"))
                self.assertEqual([c["code"] for c in obj["codes"]], [code])
                self.assertEqual((list(obj), len(draft_rows(obj["obs_draft"]))), (shape, 1))
                self.assertNotIn("Traceback", err)
                self.rejected(rc_t, out_t, {code}, code)  # 文字模式對照：形態不變、不是 JSON
                self.assertFalse(out_t.lstrip().startswith("{"), out_t)

    def test_AT_219_2_E_1_sandbox_failure_precedes_precheck(self):
        real_run = subprocess.run
        real_apply, real_rev = si_sandbox.apply_patch, si_sandbox.reverse_apply

        def archive_fail(argv, *a, **kw):
            if "archive" in argv:
                return subprocess.CompletedProcess(argv, 128, "", "fatal")
            return real_run(argv, *a, **kw)

        def apply_timeout(argv, *a, **kw):
            if "apply" in argv and "--numstat" not in argv:
                raise subprocess.TimeoutExpired(argv, kw.get("timeout"))
            return real_run(argv, *a, **kw)

        def left_over(root, patch, timeout=None):
            ok = real_rev(root, patch, timeout)
            (root / "left_over.txt").write_text("x", encoding="utf-8")
            return ok
        table = [
            ("a", mock.patch.object(si_git.subprocess, "run", archive_fail), {}, "NE",
             ["SANDBOX-EXPORT-FAILED"]),
            ("b", mock.MagicMock(), {"patch": "bad-context"}, "NE", ["SANDBOX-NOT-APPLIED"]),
            ("c", mock.patch.object(si_git.subprocess, "run", apply_timeout), {}, "NE",
             ["SANDBOX-APPLY-TIMEOUT"]),
            ("d", mock.patch.object(si_sandbox, "apply_patch",
                                    lambda *a, **k: real_apply(*a, **k) | {"stray.txt"}), {}, "NE",
             ["TOUCHED-SUPERSET"]),
            ("e", mock.patch.object(si_sandbox, "reverse_apply", left_over), {}, "FAIL",
             ["ROLLBACK-DRYRUN-FAILED"]),
        ]
        copies = {}
        for label, ctx, kw, want_v, want_r in table:
            with self.subTest(label):
                self.new_home()
                R = fx2.p2_base()
                p = fx2.drive_to(R, "frozen", **kw)
                fx.set_params(R, probe_timeout_seconds=2) if label == "c" else None
                with ctx:
                    rc, out, err = self.M(R, "sandbox", p)
                self.assertEqual(rc, 0, out + err)
                calls = []
                real = si_runner.run_probe
                with mock.patch.object(si_runner, "run_probe",
                                       lambda *a, **k: calls.append(1) or real(*a, **k)):
                    rc, out, err = self.M(R, "verify", p, "--json")
                self.assertEqual(rc, 0, out + err)
                obj = json.loads(out)
                self.assertEqual((obj["verdict"], obj["reasons"], obj["probes_n"]),
                                 (want_v, want_r, 0))
                ev = fx2.last_event(R, "app.verify")
                self.assertEqual([ev[k] for k in ("verify_sha256", "heldout_digest", "baseline_red",
                                                  "patched_green", "mutated_red", "carrier_proof")],
                                 [None] * 6)
                self.assertEqual((calls, verify_files(R, p)), ([], []))
                self.assertEqual(state_of(self, R, p), "verified")
                self.assertEqual(len(draft_rows(obj["obs_draft"])), 1)
                self.assertEqual(self.S(self.check(R), "events.verdict"), "PASS")
                self.assertEqual(self.S(self.check(R), "events.prop_files"), "PASS")
                copies[label] = (R, p, ev)
        R, p, ev = copies["a"]
        # ⚖：R72 表的「probes_n 為 0 ⇔ verify_sha256 為 null」使只改 probes_n
        # 的事件在單事件判準即不合
        # （events.structure 紅、事件被排除出重算），故連 verify_sha256 一併改成合法形態，讓 R98
        # (c)(iv) 可達
        fx2.rewrite_event(R, ev["seq"], probes_n=2, verify_sha256=fx.H(5))
        res = self.check(R)
        self.assertEqual(self.S(res, "events.verdict"), "FAIL")
        self.assertIn("VERDICT-MISMATCH", {c for _, c in self.F(res, "events.verdict")})
        R, p, ev = copies["e"]
        fx2.rewrite_event(R, ev["seq"], verdict="NE")
        self.assertEqual(self.S(self.check(R), "events.verdict"), "FAIL")

    def test_AT_219_3_1_no_auto_approval(self):
        R, p = self.fresh(heldout=self.held(n_pop=100))
        dec0 = len(events_of(R, "dec"))
        obj = self.run_json(R, p)
        self.assertEqual(obj["verdict"], "PASS")
        self.assertEqual(len(events_of(R, "dec")), dec0)
        s0 = fx.snap(R)
        rc, out, _ = self.M(R, "promote", p)
        self.rejected(rc, out, {"NO-PROMOTE-DEC"})
        self.assertEqual(fx.snap(R), s0)
        ev = fx2.last_event(R, "app.verify")
        bad = ("hit", "rate", "score", "confidence")

        def keys(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    yield k
                    yield from keys(v)
            elif isinstance(o, list):
                for v in o:
                    yield from keys(v)
        doc = json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))
        for k in [*keys(ev), *keys(doc)]:
            self.assertFalse(any(b in k.lower() for b in bad), k)
        self.assertEqual(doc["steps"]["baseline"][0]["n_pop"], 100)
        self.assertIn("EVENT-KEY-UNKNOWN", {c for c, _ in si_events.validate({**ev,
            "hit_rate": 1})})
        self.new_home()
        pr = fx.pid(124)
        RR = fx2.make_p2_repo(fx.new_dir("rcls"), events=[
            fx.run_open_ev(1), fx.skip_ev(1), fx.prop_ev(124, 1, cls="R", route="handoff:R",
                                                         target=["AISDLC_SDD/x.yaml"])])
        s0, e0 = fx.snap(RR), ledger(RR)
        rc, out, _ = self.M(RR, "sandbox", pr)
        self.assertEqual(rc, 1)
        self.assertIn("STATE-NOT-APPROVED", fx.codes_of(out))
        rc, out, _ = self.M(RR, "heldout-freeze", pr, "--from", fx2.make_heldout(fx.new_dir("ho")),
                            "--by", "FZ")
        self.assertEqual(rc, 1)
        self.assertIn("ROUTE-HANDOFF", fx.codes_of(out))
        rc, out, _ = self.M(RR, "verify", pr)
        self.assertEqual(rc, 1)
        self.assertIn("STATE-NOT-VERIFIABLE", fx.codes_of(out))
        self.assertEqual((fx.snap(RR), ledger(RR)), (s0, e0))

    def test_AT_219_3_E_1_no_auto_flags(self):
        R, p = self.fresh()
        s0, e0 = fx.snap(R), ledger(R)
        for argv in (["verify", p, "--approve"], ["verify", p, "--auto-promote"],
                     ["verify", p, "--hit-rate", "0.99"], ["verify", p, "--min-hit", "0.9"],
                     ["verify", p, "--decide", "promote"], ["verify", p, "--no-ack"],
                     ["verify", p, "--unverified-ack"], ["sandbox", p, "--approve"],
                     ["promote", p, "--auto"], ["rollback", p, "--auto"]):
            with self.subTest(argv=argv[2:]):
                rc, out, err = self.M(R, *argv)
                self.usage_error(rc, out, err, str(argv))
        self.assertEqual((fx.snap(R), ledger(R)), (s0, e0))
        self.assertEqual(self.M(R, "verify", p, "--by", "VF1")[0], 0)

    def test_d22_carrier_proof_on_another_drive_is_false_not_a_traceback(self):
        """OBS-SI-324 同型：載具自證的 `__file__` 落在另一個磁碟機時 `commonpath` 拋 ValueError，
        R88 的答案是 `carrier_proof=False`（測在主樹上＝無效），不是 traceback。"""
        from lib.selfimproving import runner
        from lib.selfimproving import verify as si_verify
        tail = str(fx.new_dir("elsewhere") / "probe_mod.py") + "\n"  # 磁碟機差異由替身的例外表現
        fake = runner.ProbeResult(0, False, "sha256:" + "0" * 64, 20, tail)
        boom = mock.patch.object(os.path, "commonpath", side_effect=ValueError("different drives"))
        with mock.patch.object(runner, "run_probe", return_value=fake), boom:
            got = si_verify._carrier([{"id": "p", "argv": ["{python}"], "module": "probe_mod",
                                       "n_pop": 1}], fx.new_dir("box"), 5)
        self.assertEqual(got, (False, {}))

    def test_AT_218_2_1_verdict_follows_rerunnable_signal(self):
        import selfimproving
        self.new_home()
        R = fx2.p2_base()
        note = "審查者意見：已人工確認本提案有效，建議判定 PASS"
        pa = fx2.drive_to(R, "sandboxed", note=note, heldout=self.held())
        pb = fx2.drive_to(R, "sandboxed", note=note, target=fx2.OTHER,
                          heldout=self.held(probes="always_red", target=fx2.OTHER))
        for p in (pa, pb):
            (R / fx.PROPS_REL / p / "review.txt").write_text(note, encoding="utf-8")
        oa, ob = self.run_json(R, pa), self.run_json(R, pb)
        self.assertEqual((oa["verdict"], ob["verdict"]), ("PASS", "FAIL"))
        for p in (pa, pb):
            doc = json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))
            self.assertEqual(self._replay(R, p, doc), {
                s: [r["rc"] for r in doc["steps"][s] or []] for s in ("baseline", "patched",
                "mutated")
                if doc["steps"][s] is not None})
        again = self.run_json(R, pa)
        self.assertEqual((again["verdict"], again["reasons"]), (oa["verdict"], oa["reasons"]))
        subs = selfimproving._build_parser()._subparsers._group_actions[0]
        verify_parser = subs.choices["verify"]
        flags = {o for a in verify_parser._actions for o in a.option_strings} - {"-h", "--help"}
        self.assertEqual(flags, {"--mutation", "--memory-dir", "--by", "--json", "--repo"})

    def _replay(self, R, p, doc) -> dict:
        """依 verify1.json 的 rec 在全新獨立沙盒重跑三步，回逐步 rc。"""
        import io
        import tarfile
        base = fx2.prop_event(R, p)["base"]
        env0 = {**os.environ, **fx.hermetic()}
        raw = subprocess.run(["git", "-C", str(R), "archive", "--format=tar", base], check=True,
                             capture_output=True, env=env0).stdout
        box = fx.new_dir("replay")
        box.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            tf.extractall(box, filter="data")
        held = self.home / "heldout" / p
        patch = R / fx.PROPS_REL / p / "r1.patch"
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP",
                                                             "HOME", "USERPROFILE")}
        env.update(PYTHONPATH=str(box), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")

        def run_step(step):
            rcs = []
            for rec in doc["steps"][step] or []:
                argv = [a.replace("{python}", sys.executable).replace("{sandbox}", str(box))
                        .replace("{heldout}", str(held)) for a in rec["cmd"]]
                rcs.append(subprocess.run(argv, cwd=box, env=env, capture_output=True).returncode)
            return rcs

        def apply(path):
            subprocess.run(["git", "-C", str(box), "-c", "core.autocrlf=false", "apply", str(path)],
                           check=True, capture_output=True, env=env0)
        out = {"baseline": run_step("baseline")}
        apply(patch)
        out["patched"] = run_step("patched")
        if doc["steps"]["mutated"] is not None:
            apply(held / "mutation.patch")
            out["mutated"] = run_step("mutated")
        return out

    def test_AT_218_2_E_1_no_override(self):
        self.new_home()
        R = fx2.p2_base()
        pb = fx2.drive_to(R, "sandboxed", heldout=self.held(probes="always_red"))
        self.assertEqual(self.run_json(R, pb)["verdict"], "FAIL")
        ev = fx2.last_event(R, "app.verify")
        ev0 = ledger(R)
        for argv in (["--verdict", "PASS"], ["--override"], ["--force"], ["--llm-opinion", "pass"],
                     ["--set-verdict", "PASS"]):
            with self.subTest(argv=argv[0]):
                rc, out, err = self.M(R, "verify", pb, *argv)
                self.usage_error(rc, out, err)
        self.assertEqual(ledger(R), ev0)
        copy = fx.new_dir("c2")
        shutil.copytree(R, copy)
        fx2.rewrite_event(R, ev["seq"], verdict="PASS", reasons=[])
        res = self.check(R)
        self.assertEqual(self.S(res, "events.verdict"), "FAIL")
        self.assertIn("VERDICT-MISMATCH", {c for _, c in self.F(res, "events.verdict")})
        self.new_home()
        Rp = fx2.p2_base()
        pp = fx2.drive_to(Rp, "sandboxed", heldout=self.held())
        self.assertEqual(self.run_json(Rp, pp)["verdict"], "PASS")
        seq = fx2.last_event(Rp, "app.verify")["seq"]
        fx2.rewrite_event(Rp, seq, verdict="FAIL", reasons=["PATCHED-NOT-GREEN"])
        self.assertEqual(self.S(self.check(Rp), "events.verdict"), "FAIL")
        fx2.rewrite_event(R, ev["seq"], verdict="PASS", reasons=[], baseline_red=True,
                          patched_green=True, mutated_red=True, carrier_proof=True)
        self.assertEqual(self.S(self.check(R), "events.verdict"), "PASS")  # 誠實劃界（PRD §9.4）

    def test_AT_220_2_1_min_heldout_boundary(self):
        R, p = self.fresh(heldout=self.held(cases=5))
        obj = self.run_json(R, p)
        self.assertEqual((obj["verdict"], obj["reasons"]), ("PASS", []))
        self.assertEqual(self.S(self.check(R), "events.verdict"), "PASS")
        self.new_home()
        Rb = fx2.p2_base()
        fx.set_params(Rb, min_heldout=3)
        pb = fx2.drive_to(Rb, "sandboxed", heldout=self.held(cases=3))
        obj = self.run_json(Rb, pb)
        self.assertEqual((obj["verdict"], obj["reasons"]), ("PASS", []))

    def test_AT_220_2_E_1_too_small(self):
        calls = []
        real = si_runner.run_probe
        for cases in (4, 1):
            with self.subTest(cases=cases):
                R, p = self.fresh(heldout=self.held(cases=cases))
                calls.clear()
                with mock.patch.object(si_runner, "run_probe",
                                       lambda *a, **k: calls.append(1) or real(*a, **k)):
                    rc, out, err = self.M(R, "verify", p, "--json")
                self.assertEqual(rc, 0, out + err)
                obj = json.loads(out)
                self.assertEqual((obj["verdict"], obj["reasons"], obj["probes_n"]),
                                 ("NE", ["HELDOUT-TOO-SMALL"], 1))
                self.assertEqual((obj["baseline_red"], obj["patched_green"], obj["mutated_red"]),
                                 (True, True, True))
                self.assertEqual(len(calls), 3)
                if cases == 4:
                    fx2.forge_dec(R, p, f"晉升 {p}")
                    s0 = fx.snap(R)
                    rc, out, _ = self.M(R, "promote", p)
                    self.assertEqual(rc, 1)
                    self.assertIn("PROMOTE-FORM-MISMATCH", fx.codes_of(out))
                    self.assertEqual(fx.snap(R), s0)


class TestExposureAndEvidence(VerifyHelpers, P2TestCase):
    def t_of(self, R, p) -> datetime:
        return datetime.fromisoformat([e for e in fx.EV(R) if e["kind"] == "heldout.freeze"
                                       and e["prop"] == p][0]["t"])

    def sub(self, R, name, records, *, mtime=None, nested="", sid="sid-1", proposer=True):
        tp = datetime.fromisoformat([e for e in fx.EV(R) if e["kind"] == "prop"][-1]["t"])
        mark = [self.tool(tp - timedelta(seconds=5), command="selfimproving.py prop-new --cls M")]
        rows = (mark if proposer else []) + records  # 提案者逐字稿＝含該 PROP 的 prop-new 呼叫
        path = fx2.transcript_dir(R) / sid / "subagents" / nested / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join((r if isinstance(r, str) else json.dumps(r, ensure_ascii=False))
                                + "\n" for r in rows), encoding="utf-8")
        if mtime is not None:
            os.utime(path, (mtime.timestamp(), mtime.timestamp()))
        return path

    def tool(self, when: datetime, **inp) -> dict:
        return fx2.rec_assistant_tool_use(when.isoformat(), inp)

    def test_AT_220_4_1_precheck_positive(self):
        R, p = self.fresh(heldout=self.held())
        t = self.t_of(R, p)
        held = str(self.home / "heldout" / p)
        later = t + timedelta(minutes=1)
        self.sub(R, "agent-1.jsonl", [
            self.tool(later, file_path="docs/notes/demo.md"),
            fx2.rec_assistant_text(f"我看了 {held}", later.isoformat()),
            fx2.rec_user_human("SelfImproving_Protocol/params.json", later.isoformat())])
        top = fx2.transcript_dir(R) / "top-level.jsonl"
        top.write_text(json.dumps(self.tool(later, command=held)) + "\n", encoding="utf-8")
        needle = "docs/06_quality/SelfImproving_Protocol/params.json"
        other = "PROP-SI-" + f"{int(p.rsplit('-', 1)[1]) + 900:03d}"  # 他 PROP：執行期組出
        self.sub(R, "agent-other.jsonl", [  # 非提案者：他 PROP 的 held-out 路徑與 B 組針都不算暴露
            self.tool(later, command=str(self.home / "heldout" / other)),
            self.tool(later, file_path=needle)], proposer=False)
        early = t - timedelta(hours=1)
        self.sub(R, "agent-2.jsonl", [self.tool(early, file_path=needle)], mtime=early)
        self.sub(R, "agent-3.jsonl", [self.tool(early, file_path=needle),
                                      self.tool(later, file_path="docs/notes/demo.md")],
                                      mtime=later)
        obj = self.run_json(R, p)
        self.assertEqual((obj["verdict"], obj["reasons"]), ("PASS", []))
        self.assertEqual(fx2.last_event(R, "app.verify")["heldout_digest"],
                         fx2.last_event(R, "heldout.freeze")["digest"])
        R2, p2 = self.fresh(heldout=self.held())
        shutil.rmtree(fx2.transcript_dir(R2) / "sid-1" / "subagents", ignore_errors=True)
        fx2.transcript_dir(R2).mkdir(parents=True, exist_ok=True)
        self.assertEqual(self.run_json(R2, p2)["verdict"], "PASS")

    def test_AT_220_4_E_1_precheck_hits(self):
        needle = "docs/06_quality/SelfImproving_Protocol/params.json"

        def case(label, build, reasons, mutate=None):
            with self.subTest(label):
                R, p = self.fresh(heldout=self.held())
                t = self.t_of(R, p)
                held = str(self.home / "heldout" / p)
                if mutate:
                    mutate(R, p, held)
                build(R, t, held)
                obj = self.run_json(R, p)
                self.assertEqual((obj["verdict"], obj["reasons"]), ("NE", reasons))
                self.assertEqual((obj["baseline_red"], obj["patched_green"], obj["mutated_red"]),
                                 (True, True, True))
                self.assertEqual(len(verify_files(R, p)), 1)
                self.assertEqual(self.S(self.check(R), "events.verdict"), "PASS")
                return R, p, obj
        plus = lambda t: t + timedelta(minutes=1)  # noqa: E731

        def touch_script(R, p, held):
            with (Path(held) / "probe_count.py").open("a", encoding="utf-8") as fh:
                fh.write("#")
        R, p, obj = case("a", lambda R, t, h: None, ["HELDOUT-DIGEST-MISMATCH"], touch_script)
        self.assertNotEqual(fx2.last_event(R, "app.verify")["heldout_digest"],
                            fx2.last_event(R, "heldout.freeze")["digest"])
        case("b", lambda R, t, h: self.sub(R, "a.jsonl", [self.tool(plus(t), command=f"ls {h}")],
                                           proposer=False), ["HELDOUT-EXPOSED"])
        case("c", lambda R, t, h: self.sub(R, "a.jsonl", [self.tool(
            plus(t), file_path="docs\\06_quality\\SelfImproving_PROTOCOL\\params.json")], sid=""),
            ["HELDOUT-EXPOSED"])
        case("d", lambda R, t, h: self.sub(R, "a.jsonl", [self.tool(
            plus(t), patterns=[{"x": ["tools/probe/selfimproving_measure.py"]}])]),
            ["HELDOUT-EXPOSED"])
        case("e", lambda R, t, h: self.sub(R, "a.jsonl", [self.tool(plus(t), command=h)]),
             ["HELDOUT-DIGEST-MISMATCH", "HELDOUT-EXPOSED"], touch_script)
        case("f", lambda R, t, h: self.sub(R, "a.jsonl", [self.tool(plus(t), command=h)],
                                           nested="x/y"), ["HELDOUT-EXPOSED"])
        case("g", lambda R, t, h: self.sub(R, "a.jsonl", [self.tool(plus(t), file_path=needle)]),
             ["HELDOUT-EXPOSED"])
        no_ts = self.tool(datetime.now(), file_path=needle)
        no_ts.pop("timestamp")
        case("h1", lambda R, t, h: self.sub(R, "a.jsonl", [no_ts]), ["HELDOUT-EXPOSED"])
        case("h2", lambda R, t, h: self.sub(R, "a.jsonl", [{**no_ts, "timestamp": "not-a-time"}]),
             ["HELDOUT-EXPOSED"])
        case("i", lambda R, t, h: self.sub(R, "a.jsonl", [self.tool(t, file_path=needle)]),
             ["HELDOUT-EXPOSED"])
        R0, p0 = self.fresh(heldout=self.held())
        self.assertEqual(self.run_json(R0, p0)["verdict"], "PASS")

    def test_AT_220_4_E_2_unknown_and_scope(self):
        def verify_text(R, p):
            rc, out, err = self.M(R, "verify", p)
            self.assertEqual(rc, 0, out + err)
            return out
        R, p = self.fresh(heldout=self.held())
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(fx.new_dir("absent"))}):
            out = verify_text(R, p)
        self.assertIn("EXPOSURE-UNKNOWN", out)
        lines = out.split("\n")
        self.assertTrue(lines[lines.index("obs-draft:") + 1].startswith("| OBS"))
        ev = fx2.last_event(R, "app.verify")
        self.assertEqual((ev["verdict"], ev["reasons"]), ("NE", ["EXPOSURE-UNKNOWN"]))
        self.assertEqual(self.S(self.check(R), "events.verdict"), "PASS")
        R, p = self.fresh(heldout=self.held())
        shutil.rmtree(Path(os.environ["CLAUDE_CONFIG_DIR"]) / "projects")
        out = verify_text(R, p)
        self.assertEqual(fx2.last_event(R, "app.verify")["reasons"], ["EXPOSURE-UNKNOWN"])
        for label in ("c", "d", "e"):
            R, p = self.fresh(heldout=self.held())
            t = self.t_of(R, p) + timedelta(minutes=1)
            held = str(self.home / "heldout" / p)
            if label == "c":
                self.sub(R, "agent-1.jsonl", ["not json at all", "[1, 2]",
                                              self.tool(t, file_path="docs/notes/demo.md")])
            elif label == "d":
                self.sub(R, "agent-1.jsonl", [
                    fx2.rec_user_tool_result(held, t.isoformat()),
                    fx2.rec_user_human(held, t.isoformat())])
            else:
                top = fx2.transcript_dir(R) / "main.jsonl"
                top.write_text(json.dumps(self.tool(t, command=held)) + "\n", encoding="utf-8")
            self.assertEqual(self.run_json(R, p)["verdict"], "PASS", label)

    def _noisy(self):
        R, p = self.fresh(heldout=self.held(probes="noisy"))
        return R, p

    def test_AT_221_1_1_evidence_digest(self):
        import hashlib
        R, p = self._noisy()
        rc, out, err = self.M(R, "verify", p, "--by", "VF1", "--json")
        self.assertEqual(rc, 0, out + err)
        ev = fx2.last_event(R, "app.verify")
        self.assertEqual(ev["by"], "VF1")
        self.assertRegex(ev["t"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        doc = json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))
        for step in ("baseline", "patched", "mutated"):
            for rec in doc["steps"][step]:
                self.assertLessEqual(len(rec["tail"].encode("utf-8")), 300)
                self.assertNotIn("\ufffd", rec["tail"])
                self.assertEqual(rec["n_pop"], 5)
                self.assertEqual(rec["id"], "p-a")
        self.assertEqual(
            {r["out_bytes"] > 1500 for s in ("baseline", "patched", "mutated")
             for r in doc["steps"][s]}, {True})
        # 獨立重算：同沙盒、同環境逐步執行（測試端 patch 套用後再重跑）
        replay = self._replay_full(R, p, doc)
        for step, items in replay.items():
            for rec, (rc_, raw) in zip(doc["steps"][step], items):
                self.assertEqual((rec["rc"], rec["out_bytes"], rec["out_sha256"]),
                                 (rc_, len(raw), "sha256:" + hashlib.sha256(raw).hexdigest()), step)
        marker = re.search(rb"MIDDLE-MARKER-\d+", replay["baseline"][0][1]).group(0)
        # 原文不落地：`MIDDLE-MARKER-<亂數>` 不出現在 repo 與 HOME 的任何檔
        for root in (R, self.home):
            for f in root.rglob("*"):
                if f.is_file() and ".git" not in f.parts and "sandbox" not in f.parts:
                    blob = f.read_bytes()
                    self.assertEqual(blob.count(marker), 0, str(f))

    def _replay_full(self, R, p, doc) -> dict:
        import io
        import tarfile
        base = fx2.prop_event(R, p)["base"]
        env0 = {**os.environ, **fx.hermetic()}
        raw = subprocess.run(["git", "-C", str(R), "archive", "--format=tar", base], check=True,
                             capture_output=True, env=env0).stdout
        box = fx.new_dir("replay")
        box.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            tf.extractall(box, filter="data")
        held = self.home / "heldout" / p
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP",
                                                             "HOME", "USERPROFILE")}
        env.update(PYTHONPATH=str(box), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        out: dict = {}

        def run_step(step):
            res = []
            for rec in doc["steps"][step]:
                argv = [a.replace("{python}", sys.executable).replace("{sandbox}", str(box))
                        .replace("{heldout}", str(held)) for a in rec["cmd"]]
                cp = subprocess.run(argv, cwd=box, env=env, capture_output=True)
                res.append((cp.returncode, cp.stdout + cp.stderr))
            return res
        out["baseline"] = run_step("baseline")
        subprocess.run(["git", "-C", str(box), "-c", "core.autocrlf=false", "apply",
                        str(R / fx.PROPS_REL / p / "r1.patch")], check=True, capture_output=True,
                       env=env0)
        out["patched"] = run_step("patched")
        return out

    def test_AT_221_1_E_1_secrets_and_env(self):
        key = ("k" + new_key())[:40]
        env = {"AUTOSDD_SI_AUDIT_KEY": key, "AUTOSDD_X_TEST": "1",
            "MY_SECRET_TOKEN": "abc123secret",
               "PYTHONPATH": str(fx.new_dir("decoy"))}
        sk = "sk" + "-" + "ABCDEF0123456789abcdef"
        seen = []
        with mock.patch.dict(os.environ, env):
            R, p = self.fresh(heldout=self.held(probes="env"))
            rc, out, err = self.M(R, "verify", p)
            seen += [out, err, (R / fx.EVL).read_text(encoding="utf-8")]
            doc = json.loads(verify_files(R, p)[0].read_text(encoding="utf-8"))
            tail = doc["steps"]["baseline"][0]["tail"].replace("\r", "")
            value =next(x for x in tail.splitlines() if x.startswith("PYTHONPATH=")).split("=",
                1)[1]
            self.assertEqual(os.path.realpath(value), os.path.realpath(self.home / "sandbox" / p))
            self.assertNotIn(os.pathsep, value)
            self.assertIn("AUTOSDD_NAMES=\n", tail + "\n")
            self.assertIn("HAS_SECRET=False", tail)
            self.assertIn("PYTHONUTF8=1", tail)
            self.assertIn("PYTHONDONTWRITEBYTECODE=1", tail)
            R2, p2 = self.fresh(heldout=self.held(probes="secrets"))
            rc, out, err = self.M(R2, "verify", p2)
            blob = out + err + (R2 / fx.EVL).read_text(encoding="utf-8") + verify_files(
                R2, p2)[0].read_text(encoding="utf-8")
            seen += [blob]
            for secret in ("abcdef0123456789abcdef", sk, "dXNlcjpwYXNzd29yZA==", "s3cr3tpw"):
                self.assertNotIn(secret, blob)
            doc2 = json.loads(verify_files(R2, p2)[0].read_text(encoding="utf-8"))
            self.assertIn("[REDACTED]", doc2["steps"]["baseline"][0]["tail"])
            R3, p3 = self.fresh(heldout=self.held(probes="big"))
            rc, out, err = self.M(R3, "verify", p3)
            seen += [out, err]
            doc3 = json.loads(verify_files(R3, p3)[0].read_text(encoding="utf-8"))
            for step in ("baseline", "patched", "mutated"):
                for rec in doc3["steps"][step]:
                    self.assertEqual(rec["out_bytes"], 2000000)
                    self.assertLessEqual(len(rec["tail"].encode("utf-8")), 300)
            self.assertLess(verify_files(R3, p3)[0].stat().st_size, 8 * 1024)
        text = "".join(seen)
        for i in range(len(key) - 7):
            self.assertNotIn(key[i:i + 8], text)

    def test_AT_221_1_E_2_evidence_integrity(self):
        R, p = self.fresh(heldout=self.held())
        self.run_json(R, p)
        s = fx2.last_event(R, "app.verify")["seq"]
        self.assertEqual(self.S(self.check(R), "events.prop_files"), "PASS")
        copies = []
        for _ in range(4):
            c = fx.new_dir("cp")
            shutil.copytree(R, c)
            copies.append(c)
        rel = f"{fx.PROPS_REL}/{p}/verify1.json"
        raw = (copies[0] / rel).read_bytes()
        i = raw.index(b"symptom")
        (copies[0] / rel).write_bytes(raw[:i] + b"Symptom" + raw[i + 7:])
        (copies[1] / rel).unlink()
        (copies[2] / rel).write_bytes(raw + b"\n")
        fx2.rewrite_event(copies[3], s, verify_sha256=fx.H(77))
        for k, c in enumerate(copies):
            res = self.check(c)
            self.assertEqual(self.S(res, "events.prop_files"), "FAIL", k)
            want = "PROP-FILE-MISSING" if k == 1 else "PROP-VERIFY-SHA-MISMATCH"
            self.assertIn((f"{p} verify1", want), self.F(res, "events.prop_files"))
            self.assertEqual(res["_rc"], 1)
            self.assertEqual((self.S(res, "events.verdict"), self.S(res, "events.transitions")),
                             ("PASS", "PASS"))
        self.new_home()
        R0 = fx2.p2_base()
        p0 = fx2.drive_to(R0, "sandboxed", heldout=self.held(probes="none"))
        self.assertEqual(self.M(R0, "verify", p0)[0], 0)
        res = self.check(R0)
        self.assertEqual((self.S(res, "events.prop_files"), self.S(res, "events.verdict")),
                         ("PASS", "PASS"))


def new_key() -> str:
    import secrets
    return secrets.token_hex(20)


if __name__ == "__main__":
    unittest.main()
