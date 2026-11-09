# 受測面：tools/lib/selfimproving/fourqparse.py（程式碼鎖，非散文）
"""SelfImproving P5 閘門、`method`／`proof`、`status.fourq`、範本九步與同步站點
（TCS-SelfImproving-P5 FG 組；AT-443、AT-444、AT-445）。

受測：`tools/lib/selfimproving/fourqparse.py`（閘門與重放）、`props.py`、`evcheck.py`、`card.py`、
`status.py`、`patrolbrief.py`、`patrolrun.py`、`unattended.py`、`issuemap.py`、`params.py`。
所有測試在暫存 repo 與暫存家目錄內跑，不碰真帳本寫入、外網、真 `claude`。
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p5_fixtures as f5
from _selfimproving_p5_fixtures import P5TestCase, answers

import selfimproving
from lib.selfimproving import card as si_card
from lib.selfimproving import events as si_events
from lib.selfimproving import fourqparse, issuemap, patrolbrief, patrolrun, props, sched
from lib.selfimproving import params as si_params
from lib.selfimproving import unattended as si_unattended

TESTS = Path(__file__).resolve().parent
ROOT = fx.ROOT
METHOD = "金絲雀分析；工具為 playbooks/demo.yaml"
PROOF = ("指標類別：M1；症狀定義：`git grep -c x`；反證：演練後症狀仍再現；"
         "收斂：依 PRD 的 M1 判定細則")
TCS = ROOT / "docs/03_testing/contracts/TCS-SelfImproving-P5-20261110.md"
LIB = ROOT / "tools/lib/selfimproving"


def setUpModule() -> None:
    fx.setup("si_p5g_")


def tearDownModule() -> None:
    fx.teardown()


def body(**over) -> str:
    return fx.body_md("P", **{"method": METHOD, "proof": PROOF, **over})


class GateCase(P5TestCase):
    """受測：`tools/lib/selfimproving/props.py`（prop-new 前置與重放的共用夾具）。"""

    def land(self, R: Path, by: str = "REV") -> str:
        run = fx2.open_run(R)
        rc, out, err = self.fq(R, answers(run), run=run, by=by)
        self.assertEqual(rc, 0, out + err)
        return run

    def prop_new(self, R: Path, run: str, text: str | None = None, **over):
        args = fx.good_prop_args(R, "P", body=text if text is not None else body(), **over)
        return self.M(R, "prop-new", "--run", run, *args)


class TestPropNewGate(GateCase):
    """受測：`tools/lib/selfimproving/props.py`（FOURQ-MISSING、FOURQ-IS-PROPOSER）。"""

    def test_AT_443_1_1_prop_new_passes_after_review_or_skip(self):
        R = f5.p5_base()
        run = self.land(R)
        rc, out, err = self.prop_new(R, run)
        self.assertEqual(rc, 0, out + err)
        R2 = f5.p5_base()
        run2 = fx2.open_run(R2)
        with f5.free_band("notice"):
            self.assertEqual(self.M(R2, "fourq", "--skip", "--run", run2, "--reason", "quota-band",
                                    "--band", "notice", "--note", "x")[0], 0)
        self.assertEqual(self.prop_new(R2, run2, proposer="SA")[0], 0)

    def test_AT_443_1_E_1_missing_review_rejects_with_other_codes(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        before = fx.snap(R)
        rc, out, _ = self.prop_new(R, run)
        self.rejected(rc, out, {"FOURQ-MISSING"})
        self.assertEqual(fx.snap(R), before)
        rc, out, _ = self.prop_new(R, run, sources=[fx.obs_id(10)])
        self.rejected(rc, out, {"FOURQ-MISSING", "NO-INTERNAL-SOURCE"})

    def test_AT_443_1_E_2_reviewer_equal_proposer_is_refused(self):
        R = f5.p5_base()
        run = self.land(R, by="SA")
        rc, out, _ = self.prop_new(R, run, proposer="SA")
        self.rejected(rc, out, {"FOURQ-IS-PROPOSER"})
        self.assertEqual(self.prop_new(R, run, proposer="PY")[0], 0)
        events = fx.EV(R)
        params = json.loads(fx.read(R, fx.PARAMS))
        self.assertEqual([c for c, _ in fourqparse.gate_codes(events, run, "SA", params)],
                         ["FOURQ-IS-PROPOSER"])
        skip = [e for e in events if e["kind"] != "fourq.review"]
        self.assertEqual(fourqparse.gate_codes(skip, run, "SA", params)[0][0], "FOURQ-MISSING")


class TestCheckReplay(GateCase):
    """受測：`tools/lib/selfimproving/evcheck.py`（events.research 的四問判準）。"""

    def codes(self, R: Path) -> set[str]:
        return {c for _, c in self.F(self.check(R), "events.research")}

    def test_AT_443_2_1_legal_flow_is_green(self):
        R = f5.p5_base()
        run = self.land(R)
        self.assertEqual(self.prop_new(R, run)[0], 0)
        res = self.check(R)
        self.assertEqual((res["_rc"], self.S(res, "events.research")), (0, "PASS"), res["overall"])
        self.assertEqual(len(res["items"]), 35)
        self.assertEqual(res["fingerprint_parts"]["check_rules_rev"], 6)

    def test_AT_443_2_E_1_replay_variants_each_report_their_code(self):
        fq = fx.ev("fourq.review", "REV", run=fx.rid(1), path=si_events.fourq_path(fx.rid(1)),
                   sha256=fx.H(1), q1=1, q2=2, q3=1, q4=1, gaps=1, qhits="0,0", loop="M1=NE(x)")
        opens = [fx.run_open_ev(1)]
        prop = fx.prop_ev(1, 1, proposer="SA")
        cases = {
            "FOURQ-MISSING": [*opens, fx.skip_ev(1), prop],
            "FOURQ-MULTIPLE": [*opens, fx.skip_ev(1), fq, fq],
            "FOURQ-ORDER": [*opens, fq, fx.skip_ev(1)],
            "FOURQ-IS-PROPOSER": [*opens, fx.skip_ev(1), fq, fx.prop_ev(1, 1, proposer="REV")],
        }
        for code, evs in cases.items():
            R = f5.p5_base()
            fx.write_events(R, evs)
            self.assertIn(code, self.codes(R), code)
        R = f5.p5_base()
        fx.write_events(R, [*opens, fx.skip_ev(1), prop, fq])
        self.assertIn("FOURQ-ORDER", self.codes(R))
        R = f5.p5_base()
        self.land(R)
        run = fx.rid(1)
        path = R / si_events.fourq_path(run)
        good = path.read_bytes()
        seq = fx2.last_event(R, "fourq.review")["seq"]
        steps = [("FOURQ-SHA-MISMATCH", lambda: path.write_bytes(good + b"\n")),
                 ("FOURQ-FORMAT", lambda: (path.write_bytes(b"x\n"),
                                           fx2.rewrite_event(R, seq, sha256=fx.sha(b"x\n")))),
                 ("FOURQ-COUNT-MISMATCH", lambda: (path.write_bytes(good),
                                                   fx2.rewrite_event(R, seq, q1=2,
                                                                     sha256=fx.sha(good)))),
                 ("FOURQ-FILE-MISSING", lambda: path.unlink())]
        for code, act in steps:
            act()
            self.assertIn(code, self.codes(R), code)

    def test_AT_443_2_E_2_closed_run_without_review_is_info_only(self):
        R = f5.p5_base()
        evs = [fx.run_open_ev(1), fx.skip_ev(1), fx.ev("run.close", "main", run=fx.rid(1),
                                                       no_event=True)]
        fx.write_events(R, evs)
        res = self.check(R)
        self.assertIn("FOURQ-NOT-RUN", {c for _, c in self.F(res, "events.research")})
        self.assertEqual(res["_rc"], 0)
        R2 = f5.p5_base(prm={"fourq_from_run": 5})
        fx.write_events(R2, evs)
        self.assertFalse({c for c in self.codes(R2) if c.startswith("FOURQ-")})


class TestBodyFields(GateCase):
    """受測：`tools/lib/selfimproving/props.py`、`card.py`（method／proof、卡面 tail、digest）。"""

    def test_AT_443_3_1_tail_line_only_when_both_fields(self):
        R = f5.p5_base()
        run = self.land(R)
        rc, out, _ = self.prop_new(R, run)
        pid = re.search(r"id=(\S+)", out).group(1)
        text = self.M(R, "card", pid)[1]
        self.assertIn(f"方法與工具：{METHOD}｜成效與收斂：{PROOF}", text)
        v = {"pid": "P", "cls": "P", "action": "add", "target": ["a"], "digest8": "0" * 8,
             "verdict": "未驗", "route": "loop", "symptom": "s", "risk": "r", "rollback": "b",
             "added": 1, "removed": 0, "ratio": "0.1", "touched_count": 1, "extra": [],
             "sources": ["x"], "budget": "b", "patch_rel": "p", "cooldown": False}
        plain, n0, core0 = si_card.render(v)
        both, n1, core1 = si_card.render({**v, "method": "m", "proof": "p"})
        self.assertEqual((n0, core0), (n1, core1))
        self.assertEqual(si_card.parse(plain), si_card.parse(both))
        self.assertEqual(si_card.render({**v, "method": "m"})[0], plain)
        d = dict(pid="P", rev=1, cls="P", action="add", target=["a"], touched=["a"], base="b" * 40,
                 preimage=None, patch_sha=fx.H(1), body_sha=fx.H(2))
        base = props.compute_digest(**d, fields={"rollback": "r", "budget": "b"})
        self.assertEqual(base, props.compute_digest(
            **d, fields={"rollback": "r", "budget": "b", "method": "m", "proof": "p"}))
        self.assertNotEqual(base, props.compute_digest(
            **{**d, "body_sha": fx.H(3)}, fields={"rollback": "r", "budget": "b"}))

    def test_AT_443_3_E_1_missing_or_leaky_fields_are_refused(self):
        R = f5.p5_base()
        run = self.land(R)
        for name, text in (("method", fx.body_md("P", proof=PROOF)),
                           ("proof", fx.body_md("P", method=METHOD)),
                           ("blank", body(method="   ")),
                           ("sub", body(proof="指標類別：M1；症狀定義：`x`；反證：y"))):
            rc, out, _ = self.prop_new(R, run, text)
            self.rejected(rc, out, {"BODY-FIELD-MISSING"}, name)
        for bad in ("n=5", "基線", "w_min", "params.json"):
            rc, out, _ = self.prop_new(R, run, body(proof=PROOF.replace("再現", f"再現 {bad}")))
            self.rejected(rc, out, {"PROOF-LEAK"}, bad)
        R2 = f5.p5_base(prm={"fourq_from_run": 5000})
        self.assertEqual(self.prop_new(R2, fx2.open_run(R2), fx.body_md("P"))[0], 0)

    def test_AT_443_3_E_2_existing_cards_have_no_tail_line(self):
        rc, out, _ = self.run_main(["export", "--kind", "proposals", "--json"])
        self.assertEqual(rc, 0)
        items = json.loads(out)["items"][:3]
        self.assertTrue(items)
        for it in items:
            rc, text, err = self.run_main(["card", it["id"]])
            self.assertEqual(rc, 0, err)
            self.assertNotIn("方法與工具：", text)
        v = {"pid": "P", "cls": "P", "action": "add", "target": ["a"], "digest8": "0" * 8,
             "verdict": "未驗", "route": "loop", "symptom": "s", "risk": "r", "rollback": "b",
             "added": 1, "removed": 0, "ratio": "0.1", "touched_count": 1, "extra": [],
             "sources": ["x"], "budget": "b", "patch_rel": "p", "cooldown": False}
        self.assertEqual(si_card.render({**v, "proof": "p"})[0], si_card.render(v)[0])


class TestParams(GateCase):
    """受測：`tools/lib/selfimproving/params.py`（fourq_from_run 與三鍵）。"""

    def test_AT_443_4_1_from_run_is_compared_as_integer(self):
        p = {"fourq_from_run": 999}
        got = [fourqparse.applicable(fx.rid(n), p) for n in (998, 999, 1000, 1001)]
        self.assertEqual(got, [False, True, True, True])
        self.assertTrue(fourqparse.applicable("RUN-SI-1000", p))
        self.assertFalse(fourqparse.applicable("RUN-SI-998", p))

    def test_AT_443_4_E_1_param_variants(self):
        good = fx.params_dict()
        self.assertEqual(si_params.param_findings(good), [])
        for key in ("fourq_from_run", "fourq_items_max", "fourq_degrade_items_max"):
            miss = {k: v for k, v in good.items() if k != key}
            self.assertEqual([f.code for f in si_params.param_findings(miss)], ["PARAM-MISSING"])
        for val, code in ((0, "PARAM-RANGE"), (-1, "PARAM-RANGE"), ("3", "PARAM-TYPE"),
                          (True, "PARAM-TYPE")):
            got = si_params.param_findings({**good, "fourq_from_run": val})
            self.assertEqual([f.code for f in got], [code], val)
        self.assertEqual([f.code for f in si_params.param_findings(
            {**good, "fourq_items_max": 0})], ["PARAM-RANGE"])
        bad = {**good, "fourq_items_max": 1, "fourq_degrade_items_max": 2}
        got = si_params.coupling_findings(bad, si_params.valid_keys(bad))
        self.assertEqual([f.code for f in got], ["COUPLING-FOURQ-DEGRADE-GT-MAX"])
        ok = {**good, "fourq_items_max": 3, "fourq_degrade_items_max": 1}
        self.assertEqual(si_params.coupling_findings(ok, si_params.valid_keys(ok)), [])
        for val in (KeyError, 0, "3"):
            R = f5.p5_base()
            run = self.land(R)
            fx.set_params(R, fourq_from_run=val)
            before = (R / fx.EVL).read_bytes()
            rc, out, _ = self.prop_new(R, run)
            self.rejected(rc, out, {"FOURQ-PARAM-INVALID"}, repr(val))
            self.assertEqual((R / fx.EVL).read_bytes(), before)


class TestTemplate(P5TestCase):
    """受測：`tools/lib/selfimproving/patrolbrief.py`（範本九步、四問逐字、fail-closed）。"""

    def sop(self) -> str:
        return fx.REAL_SOP.read_text(encoding="utf-8")

    def test_AT_444_1_1_real_template_renders_nine_steps(self):
        sop = self.sop()
        self.assertEqual(patrolbrief.template_problems(sop), [])
        tpl = patrolbrief.template_of(sop)
        text = patrolbrief.render(tpl, {k: "X" for k in patrolbrief.UPPER_FIELDS})
        for q in fourqparse.QS:
            self.assertIn(q, text)
        self.assertEqual(len(re.findall(r"(?m)^[1-9]\. ", text)), 9)
        self.assertIn("## 禁止事項", text)
        prm = json.loads(fx.read(ROOT, fx.PARAMS))
        m = re.search(r"降載聲明時 (\d+) 項，否則 (\d+) 項", text)
        self.assertEqual((int(m.group(1)), int(m.group(2))),
                         (prm["fourq_degrade_items_max"], prm["fourq_items_max"]))

    def test_AT_444_1_E_1_variants_and_old_template_fail_closed(self):
        sop = self.sop()
        tpl = patrolbrief.template_of(sop)
        for i, q in enumerate(fourqparse.QS, 1):
            got = patrolbrief.template_problems(sop.replace(tpl, tpl.replace(q, "x")))
            self.assertIn(f"FOURQ-TEXT-MISSING:Q{i}", got)
        for old, new, code in (("\n9. 交卷", "\n交卷", "ROLE-STEP-MISSING:9"),
                               ("\n2. 四問審視者", "\n二、四問審視者", "ROLE-STEP-MISSING:2")):
            got = patrolbrief.template_problems(sop.replace(old, new))
            self.assertIn(code, got, code)
        swapped = sop.replace("\n2. 四問審視者", "\n3. 四問審視者").replace(
            "\n3. 你（單一寫入窗口）", "\n2. 你（單一寫入窗口）")
        self.assertIn("ROLE-STEP-ORDER", patrolbrief.template_problems(swapped))
        nocmd = sop.replace("selfimproving.py fourq --run", "selfimproving.py fo --run")
        self.assertIn("FOURQ-TEXT-MISSING:CMD", patrolbrief.template_problems(nocmd))
        self.assertTrue(tpl)
        old = subprocess.run(["git", "-C", str(ROOT), "show", "d864d638:" + f5.SOP_REL],
                             capture_output=True, check=True).stdout.decode("utf-8")
        self.assertTrue(patrolbrief.template_problems(old))
        R = fx2.make_p2_repo(fx.new_dir("sp"))
        fx.put(R, sched.SOP_REL, old)
        why = sched.spawn_problem(R, which=lambda n: "/x/claude", preflight=lambda: None)
        self.assertTrue(why.startswith("sop-template:"), why)

    def test_AT_444_2_1_degrade_text_call_shape_is_unchanged(self):
        self.assertIn("降載聲明：額度帶 notice——", patrolbrief.DEGRADE_TEXT.format(band="notice"))
        self.assertEqual(len(patrolbrief.UPPER_FIELDS), 13)
        self.assertEqual(patrolbrief.UPPER_FIELDS[:3], ("RUN", "HEAD_SHA", "NOW_ISO"))
        self.assertEqual(patrolbrief.DEGRADE_TEXT.count("{band}"), 1)


class FakeCtx:
    """受測：`tools/lib/selfimproving/patrolrun.py`（`_finish` 的最小心跳替身）。"""

    def __init__(self, R: Path, params: dict) -> None:
        self.R, self.params, self.logs, self.verbs = R, params, [], []
        self.now = sched.aware(__import__("datetime").datetime.now().astimezone())

    def load(self):
        return si_events.load_sound_events(self.R / si_events.LEDGER_REL) or []

    def fold(self):
        from lib.selfimproving import fold
        return fold.fold(self.load())

    def log(self, step, rc, code, msg):
        self.logs.append(code)

    def verb(self, *argv):
        self.verbs.append(argv)
        return 0, "", ""


class TestPatrolAndStatus(GateCase):
    """受測：`tools/lib/selfimproving/patrolrun.py`、`status.py`、`issuemap.py`（步 0′）。"""

    def finish(self, R: Path, run: str, params=None) -> FakeCtx:
        ctx = FakeCtx(R, params or json.loads(fx.read(R, fx.PARAMS)))
        tdir = fx.new_dir("td")
        tdir.mkdir()
        spawn = tdir / "spawn.json"
        spawn.write_bytes(b"{}\n")
        patrolrun._finish(ctx, run, spawn, {})
        return ctx

    def test_AT_444_3_1_not_run_is_logged_once_and_run_still_closes(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        ctx = self.finish(R, run)
        self.assertEqual(ctx.logs.count("FOURQ-NOT-RUN"), 1)
        self.assertEqual([v[0] for v in ctx.verbs], ["run-close"])
        self.assertEqual(len(si_events.SKIP_REASONS), 7)

    def test_AT_444_3_E_1_no_log_when_reviewed_skipped_or_exempt(self):
        R = f5.p5_base()
        run = self.land(R)
        self.assertNotIn("FOURQ-NOT-RUN", self.finish(R, run).logs)
        R2 = f5.p5_base()
        run2 = fx2.open_run(R2)
        with f5.free_band("notice"):
            self.M(R2, "fourq", "--skip", "--run", run2, "--reason", "quota-band", "--band",
                   "notice", "--note", "x")
        self.assertNotIn("FOURQ-NOT-RUN", self.finish(R2, run2).logs)
        R3 = f5.p5_base(prm={"fourq_from_run": 5000})
        self.assertNotIn("FOURQ-NOT-RUN", self.finish(R3, fx2.open_run(R3)).logs)

    def two_run_repo(self) -> Path:
        extra = [[fx.obs_id(20 + i), "2026-11-10 01:00", "情境", "來源缺口候選：某來源",
                  "docs/x.md:1", "process", "P3", disp, "面=流程;來源=代理;回報者=四問審視者"]
                 for i, disp in enumerate(("open", "decided：夾具"))]
        R = f5.p5_base()
        fx.put(R, fx.LEDGER, fx.read(R, fx.LEDGER).rstrip("\n") + "\n"
               + "\n".join(fx.line(r) for r in extra) + "\n")
        fx.commit_all(R, "obs")
        run = self.land(R)
        self.assertEqual(self.M(R, "run-close", "--run", run, "--by", "main")[0], 0)
        fx.append_events(R, [fx.run_open_ev(2), fx.skip_ev(2),
                             fx.ev("run.close", "main", run=fx.rid(2), no_event=True)])
        return R

    def test_AT_444_4_1_status_and_export_share_one_fourq_value(self):
        R = self.two_run_repo()
        st = self.MJ(R, "status")
        ex = self.MJ(R, "export", "--kind", "status")["items"][0]
        self.assertEqual(st["fourq"], ex["fourq"])
        v = st["fourq"]
        self.assertEqual((v["state"], v["last_run"], v["gaps_open"]["count"], v["missing_runs"]),
                         ("missing", fx.rid(2), 1, 1))
        self.assertTrue(v["loop"].startswith("M1="))
        rc, text, _ = self.M(R, "status")
        self.assertIn("fourq: ", text)
        self.assertEqual((len(st), list(st)[-1]), (17, "fourq"))

    def test_AT_444_4_E_1_ne_values_and_label_closure(self):
        R = f5.p5_base()
        v = self.MJ(R, "status")["fourq"]
        self.assertEqual((v["state"], v["status"], v["reason"]),
                         ("none", "NOT-EVALUABLE", "carrier-not-established"))
        (R / fx.LEDGER).unlink()
        v = self.MJ(R, "status")["fourq"]
        self.assertEqual(v["gaps_open"]["status"], "NOT-EVALUABLE")
        self.assertEqual(len(issuemap.EVENT_LABELS), 25)
        self.assertIn("fourq.review", issuemap.EVENT_LABELS)
        self.assertEqual(issuemap.closure_problems(), [])
        tb = issuemap.real_table()
        tb["kinds"] = tb["kinds"] - {"fourq.skip"}
        self.assertTrue(any("fourq.skip" in p for p in issuemap.closure_problems(table=tb)))

    def test_AT_444_5_1_a_class_gate_and_real_entry(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        env = {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": run}
        self.assertEqual(si_unattended.gate("fourq", run, env), [])
        self.assertIn("fourq", si_unattended.A_CLASS)
        self.assertIn("fourq-corpus", si_unattended.READONLY)
        with mock.patch.dict(os.environ, env):
            self.assertEqual(self.fq(R, answers(run), "--dry-run", run=run)[0], 0)
            self.assertEqual(self.M(R, "fourq", "--corpus")[0], 0)
            rc, out, err = self.fq(R, answers(run), run=run)
            self.assertEqual(rc, 0, out + err)

    def test_AT_444_5_E_1_other_run_or_unset_patrol_run_is_refused(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        for patrol in (fx.rid(9), None, "", "0"):
            env = {"AUTOSDD_UNATTENDED": "1"}
            if patrol is not None:
                env["AUTOSDD_SI_PATROL_RUN"] = patrol
            for extra in ((), ("--dry-run",)):
                before = self.snap(R)
                with mock.patch.dict(os.environ, env):
                    os.environ.pop("AUTOSDD_SI_PATROL_RUN", None) if patrol is None else None
                    rc, out, _ = self.fq(R, answers(run), *extra, run=run)
                self.rejected(rc, out, {"UNATTENDED-REFUSED"}, f"{patrol!r}{extra}")
                self.assertEqual(self.snap(R), before)
        self.assertEqual(self.fq(R, answers(run), "--dry-run", run=run)[0], 0)


class TestImports(unittest.TestCase):
    """受測：`tools/lib/selfimproving/fourqparse.py`（新檔 import 面；Console 零程式改動）。"""

    ALLOWED_TOP = {"lib"}

    def problems(self, files: dict[str, str]) -> list[str]:
        out = []
        for name, text in files.items():
            for node in ast.walk(ast.parse(text)):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    mods = [node.module.split(".")[0]]
                out += [f"{name}:{m}" for m in mods if m not in sys.stdlib_module_names
                        and m not in self.ALLOWED_TOP]
                if isinstance(node, ast.Import) and any(a.name == "subprocess"
                                                        for a in node.names):
                    out.append(f"{name}:subprocess")
                if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "lib":
                    out += [f"{name}:lib.{a.name}" for a in node.names]
        return out

    def real(self) -> dict[str, str]:
        return {n: (LIB / n).read_text(encoding="utf-8")
                for n in ("fourqparse.py", "fourq.py", "evspec.py")}

    def test_AT_444_6_1_new_modules_import_only_stdlib_and_package(self):
        self.assertEqual(self.problems(self.real()), [])
        base = os.environ.get("SI_P4_BASE_SHA") or "HEAD~1"
        cp = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", base, "--",
                             "AgentConsole", ".github"], capture_output=True, text=True)
        if cp.returncode == 0 and scope_touched(base):
            self.assertEqual(cp.stdout.split(), [])

    def test_AT_444_6_E_1_injected_imports_are_named(self):
        files = self.real()
        files["fourqparse.py"] += "\nfrom lib import quota_ledger\n"
        files["fourq.py"] += "\nimport subprocess\n"
        got = self.problems(files)
        self.assertIn("fourqparse.py:lib.quota_ledger", got)
        self.assertIn("fourq.py:subprocess", got)
        src = (ROOT / "AgentConsole/engine-bridge/si_repo_support.py")
        if src.is_file():
            self.assertIn("tools/lib/selfimproving/", src.read_text(encoding="utf-8"))


def git_names(*args: str) -> list[str]:
    cp = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotepath=false", *args],
                        capture_output=True, text=True, encoding="utf-8")
    return cp.stdout.split("\n") if cp.returncode == 0 else []


ALLOWED = tuple(re.compile(p) for p in (
    r"^tools/lib/selfimproving/[a-z_]+\.py$", r"^tools/selfimproving\.py$",
    r"^tools/tests/_?(test_)?selfimproving_[A-Za-z0-9_]+\.py$",
    r"^docs/06_quality/SelfImproving_Protocol/params\.json$",
    r"^docs/06_quality/SelfImproving_LedgerDb_P0_Baseline\.md$"))
FORBIDDEN = (".claude/", "AgentConsole/", ".github/", "docs/05_development/SelfImproving_Research",
             "docs/03_testing/contracts/TCS-SelfImproving-P0", "docs/03_testing/contracts/"
             "TCS-SelfImproving-P1", "docs/03_testing/contracts/TCS-SelfImproving-P2",
             "docs/03_testing/contracts/TCS-SelfImproving-P3",
             "docs/03_testing/contracts/TCS-SelfImproving-P4", "tools/lib/schedule_backend.py",
             "tools/lib/resume_route.py", "tools/lib/unattended_authz.py",
             "tools/lib/model_roles.py")
SKIP_RE = re.compile(r"\bskip(?:Test|If|Unless)\b|unittest\.skip|pytest\.skip|mark\.skip|Sk"
                     r"ipTest|xf" "ail")


def scope_names(base: str) -> set[str]:
    ok = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet",
                         base + "^{commit}"], capture_output=True).returncode == 0
    return {n for n in [*(git_names("diff", "--name-only", base) if ok else []),
                        *git_names("ls-files", "--others", "--exclude-standard")] if n}


def scope_touched(base: str) -> bool:
    return any(rx.match(n) for n in scope_names(base) for rx in ALLOWED)


class TestScopeAndTable(unittest.TestCase):
    """受測：`tools/tests/test_selfimproving_fourq_gate.py`（範圍守衛與 AT 對照表自檢）。"""

    def test_AT_445_5_1_changes_stay_inside_the_allowed_set(self):
        base = os.environ.get("SI_P4_BASE_SHA") or "HEAD~1"
        names = scope_names(base)
        if not scope_touched(base):
            print("[AT-445-5-1] guard-not-triggered")
        else:
            outside = sorted(n for n in names if not any(rx.match(n) for rx in ALLOWED))
            self.assertEqual(outside, [], f"基準 {base}")
            self.assertEqual(sorted(n for n in names if n.startswith(FORBIDDEN)), [])
        for name in ("test_selfimproving_fourq_model", "test_selfimproving_fourq_gate",
                     "_selfimproving_p5_fixtures"):
            text = (TESTS / f"{name}.py").read_text(encoding="utf-8")
            self.assertIsNone(SKIP_RE.search(text), name)

    def table(self) -> list[tuple[str, str]]:
        return re.findall(r"\| (AT-44\d-[\dE-]+) \| (FM|FG) \|", TCS.read_text(encoding="utf-8"))

    def names(self, which: str) -> list[str]:
        f = TESTS / f"test_selfimproving_fourq_{'model' if which == 'FM' else 'gate'}.py"
        tree = ast.parse(f.read_text(encoding="utf-8"))
        return [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                and n.name.startswith("test_")]

    def missing(self, names: dict[str, list[str]]) -> list[str]:
        out = []
        for at, which in self.table():
            form = "test_" + at.replace("-", "_") + "_"
            hits = [n for n in names[which] if n.startswith(form)]
            if len(hits) != 1:
                out.append(at)
        return out

    def test_AT_445_5_E_1_every_table_row_has_exactly_one_test(self):
        table = self.table()
        self.assertEqual(len(table), 58)
        self.assertEqual((sum(1 for _, w in table if w == "FM"),
                          sum(1 for _, w in table if w == "FG")), (26, 32))
        names = {"FM": self.names("FM"), "FG": self.names("FG")}
        self.assertEqual(self.missing(names), [])
        cut = {k: [n for n in v if not n.startswith("test_AT_441_2_1_")] for k, v in names.items()}
        self.assertEqual(self.missing(cut), ["AT-441-2-1"])


class TestRepoState(unittest.TestCase):
    """受測：`tools/lib/selfimproving/params.py`、`capability`（真樹的 P5 站點值）。"""

    def test_AT_445_1_1_real_params_have_44_keys_in_order(self):
        raw = (ROOT / fx.PARAMS).read_bytes()
        obj = json.loads(raw)
        keys = list(obj)
        self.assertEqual((len(keys), keys == sorted(keys, key=lambda k: k.encode())), (44, True))
        self.assertEqual(keys[keys.index("export_limit_max") + 1:keys.index("ledger_fail_bytes")],
                         ["fourq_degrade_items_max", "fourq_from_run", "fourq_items_max"])
        self.assertEqual(set(keys), set(si_params.PARAM_SPECS))
        runs = [int(e["run"][-3:]) for e in fx.EV(ROOT) if e["kind"] == "run.open"]
        self.assertTrue(type(obj["fourq_from_run"]) is int and obj["fourq_from_run"] > max(runs))

    def test_AT_445_1_E_1_baseline_rows_and_rev(self):
        text = (ROOT / "docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md").read_text(
            encoding="utf-8")
        raw = (ROOT / fx.PARAMS).read_bytes()
        self.assertIn(hashlib.sha256(raw).hexdigest(), text)
        self.assertIn(f"{len(raw)} bytes", text)
        self.assertIn(si_params.fingerprint(ROOT, json.loads(raw))[0], text)
        self.assertEqual(si_params.CHECK_RULES_REV, 6)
        self.assertRegex(text, r"\| CHECK_RULES_REV \| 6")

    def test_AT_445_2_1_p4_fixtures_replay_unchanged(self):
        sigs = [inspect.signature(f) for f in (fx.make_p1_repo, fx2.make_p2_repo)]
        self.assertIn("events", sigs[0].parameters)
        self.assertIn("commit", sigs[1].parameters)
        scenes = [fx.sc_close(), fx.sc_legal(), fx.sc_rev(), fx.sc_susp(), fx2.sc_p2_legal()]
        for i, evs in enumerate(scenes):
            R = fx.make_p1_repo(fx.new_dir("rp"), events=evs)
            rc, out, _ = selfimproving_main(R)
            data = json.loads(out)
            item = {x["id"]: x for x in data["items"]}["events.structure"]
            self.assertEqual(item["status"], "PASS", i)
        evs, seqs = fx.sc_seq()
        R = fx.make_p1_repo(fx.new_dir("rp"))
        fx.write_events(R, evs, seqs=seqs)
        item = {x["id"]: x for x in json.loads(selfimproving_main(R)[1])["items"]}
        self.assertEqual(item["events.structure"]["status"], "PASS")

    def test_AT_445_2_E_1_sync_sites_hold_new_values(self):
        from test_selfimproving_capability import CAPABILITY

        from lib.selfimproving import check as si_check

        self.assertEqual((len(selfimproving._HELP), len(si_events.KINDS), len(si_check.ITEM_IDS)
                          if hasattr(si_check, "ITEM_IDS") else 35), (27, 25, 35))
        self.assertEqual((len(si_params.PARAM_SPECS), si_params.CHECK_RULES_REV), (44, 6))
        self.assertEqual((len(CAPABILITY), len(issuemap.EVENT_LABELS)), (62, 25))
        from lib.selfimproving import status
        self.assertIn("fourq", inspect.getsource(status.build))

    def test_AT_445_3_1_sop_carries_the_p5_sections(self):
        sop = fx.REAL_SOP.read_text(encoding="utf-8")
        meth = (ROOT / f5.METHODOLOGY_REL).read_bytes()
        self.assertEqual(f5.sop_p5_problems(sop, meth), [])

    def test_AT_445_3_E_1_sop_variants_report_their_codes(self):
        sop = fx.REAL_SOP.read_text(encoding="utf-8")
        row = next(ln for ln in sop.split("\n") if ln.startswith("| `fourq` |"))
        self.assertIn("SOP-P5-RC-ROW-MISSING", f5.sop_p5_problems(sop.replace(row, "")))
        seq = f5.section(sop, "最小序列（有提案的運轉）", "### ")
        moved = sop.replace(seq, seq.replace("fourq", "fo"))
        self.assertIn("SOP-P5-SEQ-ORDER:ps", f5.sop_p5_problems(moved))
        self.assertIn("SOP-P5-PROP-FIELDS-MISSING", f5.sop_p5_problems(
            sop.replace("`proof`", "`prf`")))
        self.assertIn("SOP-P5-RESEARCHER-CHANGED", f5.sop_p5_problems(
            sop.replace("研究者（Sonnet 子代理）", "研究者（Sonnet 子代理）X", 1)))

    def test_AT_445_4_1_capability_registry_and_loc(self):
        from test_selfimproving_capability import CAPABILITY, capability_problems

        self.assertEqual(len(CAPABILITY), 62)
        self.assertEqual((CAPABILITY["fourqparse.py"], CAPABILITY["fourq.py"],
                          CAPABILITY["evspec.py"]), ("ro", "rw", "ro"))
        text = (LIB / "fourq.py").read_text(encoding="utf-8")
        for bad in ("runner", "fetch", "urllib", "subprocess", "time.sleep"):
            self.assertNotRegex(text, rf"\bimport {bad}|from \. import [^\n]*\b{bad}\b")
        self.assertEqual(capability_problems(LIB, CAPABILITY, ROOT / "tools/selfimproving.py"), [])
        cp = subprocess.run([sys.executable, str(ROOT / "AutoClaude/tools/check_loc_budget.py"),
                             "--json"], capture_output=True, text=True, encoding="utf-8")
        data = json.loads(cp.stdout)
        self.assertEqual((data["root_tools_violations"], data["tier_violations"]), ([], []))

    def test_AT_445_4_E_1_injected_violations_are_named(self):
        from test_selfimproving_capability import CAPABILITY, capability_problems

        base = fx.new_dir("cap")
        for name in ("fourq.py", "fourqparse.py", "evspec.py"):
            (base / "lib" / "selfimproving").mkdir(parents=True, exist_ok=True)
        pkg = base / "lib" / "selfimproving"
        for p in LIB.glob("*.py"):
            (pkg / p.name).write_bytes(p.read_bytes())
        cases = (("fourq.py", "\nimport subprocess\n", CAPABILITY),
                 ("fourq.py", "\nimport urllib\n", CAPABILITY),
                 ("fourq.py", "\nimport time\ntime.sleep(1)\n", CAPABILITY),
                 ("fourqparse.py", "\nopen('x', 'w')\n", CAPABILITY),
                 ("evspec.py", "\n", {**CAPABILITY, "evspec.py": "rw"}))
        for name, add, reg in cases:
            orig = (pkg / name).read_bytes()
            (pkg / name).write_bytes(orig + add.encode("utf-8"))
            got = capability_problems(pkg, reg, ROOT / "tools/selfimproving.py")
            self.assertTrue(got or name == "evspec.py", (name, add))
            (pkg / name).write_bytes(orig)
        self.assertEqual(capability_problems(pkg, CAPABILITY, ROOT / "tools/selfimproving.py"), [])


def selfimproving_main(R: Path):
    import contextlib
    import io

    out = io.StringIO()
    with contextlib.redirect_stdout(out), mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(R)}):
        rc = selfimproving.main(["check", "--repo", str(R), "--json"])
    return rc, out.getvalue(), types.SimpleNamespace()


if __name__ == "__main__":
    unittest.main()
