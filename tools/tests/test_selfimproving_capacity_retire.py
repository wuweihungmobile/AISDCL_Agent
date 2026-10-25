# 受測面：tools/lib/selfimproving/capacity.py（程式碼鎖，非散文）
"""SelfImproving P3 退役欄位、抖動防護、容量與 `capacity` 動詞的驗收（TCS-P3 §2 D 組；17 個 AT）。

受測：`tools/lib/selfimproving/retire.py`（退役欄位與目標在役）、`churn.py`（抖動與
capability-delta）、`capacity.py`（記憶索引、KB、偏好的容量與截斷風險）、`card.py`（R 類退役提示）
與 `capacity` 動詞。
"""

from __future__ import annotations

import ast
import json
import shutil
import unittest
from pathlib import Path

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p3_fixtures as f3
from _selfimproving_p3_fixtures import D3, T1, T2, cap_index, evl

from lib.selfimproving import capacity, retire
from lib.selfimproving import transcript as si_transcript

S1 = fx.obs_id(2)
RULE = f"AISDLC_SDD/{fx.VNEW}/governance/rules/R-9.2.yaml"
FORM = ("RETIRE-FIELD-FORM", "RETIRE-FIELD-MISSING", "RETIRE-TARGET-NOT-ADOPTED")
RETIRE_WHEN = "該段連續兩個運轉無人引用"
REOPEN = "同一條提示再度被研究者重寫"
ENGINE_KB = fx.ROOT / "AutoClaude/autoclaude/utils/knowledge_base.py"
ENGINE_PREFS = fx.ROOT / "AutoClaude/autoclaude/plugins/preference_memory_plugin.py"


def setUpModule():
    fx.setup("si_p3c_")


def tearDownModule():
    fx.teardown()


class CrTestCase(f3.P3TestCase):
    def scenario(self, build=None):
        self.new_home()
        R = f3.p3_base()
        fx.set_params(R, max_proposals_per_run=50)  # 預算碼與本檔各 AT 正交（手寫 PROP 皆屬運轉 1）
        s = build(R) if build else None
        fx.commit_all(R, "scenario")
        return R, s

    def copy(self, R: Path) -> Path:
        dest = fx.new_dir("cp")
        shutil.copytree(R, dest)
        return dest

    def retire_args(self, R, **over):
        kw = {"action": "retire", "target": T1, "sources": [S1]}
        kw.update(over)
        return f3.try_prop(R, fx.rid(1), **kw)

    def codes(self, out: str) -> set:
        return fx.codes_of(out)


class TestRetireFields(CrTestCase):
    def test_AT_325_1_1_retire_fields_and_in_service_target_are_accepted(self):
        R, _ = self.scenario(lambda r: f3.promoted(r, target=T1))
        e0 = len(fx.EV(R))
        rc, out, err, p = self.retire_args(R)
        self.assertEqual(rc, 0, out + err)
        ev = next(e for e in fx.EV(R) if e["kind"] == "prop" and e["id"] == p)
        self.assertEqual(ev["action"], "retire")
        self.assertEqual(self.prop_state(R, p), "proposed")
        digests = {"P": ev["digest"]}
        for key, over in (("a", {"retire_when": "另一句退役條件"}),
                          ("b", {"reopen_symptom": "另一句再開症狀"})):
            Rx, _ = self.scenario(lambda r: f3.promoted(r, target=T1))
            rc, out, err, px = self.retire_args(Rx, body_over=over)
            self.assertEqual(rc, 0, out + err)
            digests[key] = next(e["digest"] for e in fx.EV(Rx)
                                if e["kind"] == "prop" and e["id"] == px)
        self.assertEqual(len(set(digests.values())), 3)
        Rc, _ = self.scenario(lambda r: f3.promoted(r, target=T1))
        rc, out, err, pc = self.retire_args(Rc, action="add", target=T2)
        self.assertEqual(rc, 0, out + err)
        evc = next(e for e in fx.EV(Rc) if e["kind"] == "prop" and e["id"] == pc)
        self.assertEqual(set(ev), set(evc))
        res = self.check(R)
        self.assertEqual((self.S(res, "events.structure"), self.S(res, "events.mea")),
                         ("PASS", "PASS"))
        self.assertEqual(len(fx.EV(R)) - e0, 1)

    def test_AT_325_1_E_1_rejections_and_the_in_service_moves_with_later_adoptions(self):
        R, _ = self.scenario(lambda r: f3.promoted(r, target=T1))
        run = fx.rid(1)
        z = fx2.new_prop(R, target=fx2.OTHER)
        fx2.issue_card(R, z)
        pe = fx2.prop_event(R, z)
        card = [e for e in fx.EV(R) if e["kind"] == "card" and e["prop"] == z][-1]
        fx.append_events(R, [fx.ev("dec", "掌舵者", prop=z, dkind="return", digest=pe["digest"],
                                   card_seq=card["seq"], quote=fx.std_quote("return", z))])
        fx.commit_all(R, "z")
        e0, snap0 = evl(R), fx.snap(R)
        branches = [Path(fx.new_dir("br")) for _ in range(4)]
        for b in branches:
            shutil.copytree(R, b)

        def bad(label, want, rc_want, call):
            with self.subTest(label=label):
                rc, out, err = call()
                self.assertEqual(rc, rc_want, out + err)
                if rc_want == 1:
                    self.assertEqual(self.codes(out), set(want), label)
                    self.draft_ok(R, out, label)
                    self.assertEqual((evl(R), fx.snap(R)), (e0, snap0))
                else:
                    self.assertTrue(err.startswith("selfimproving:"), err)

        def prop(**kw):
            return lambda: self.retire_args(R, **kw)[:3]

        bad("a", {"RETIRE-FIELD-MISSING"}, 1, prop(body_drop=("retire_when",)))
        bad("b", {"RETIRE-FIELD-MISSING"}, 1, prop(action="add", body_drop=("reopen_symptom",)))
        bad("c", {"RETIRE-FIELD-MISSING"}, 1, prop(body_over={"retire_when": ""}))
        bad("d", {"RETIRE-FIELD-FORM"}, 1, prop(body_over={"reopen_symptom": "見 2026-10-24"}))
        bad("e", {"RETIRE-FIELD-FORM"}, 1, prop(body_over={"retire_when": "R214 之後"}))
        bad("f", {"RETIRE-TARGET-NOT-ADOPTED"}, 1, prop(target=T2))
        bad("g", {"RETIRE-FIELD-MISSING"}, 1,
            lambda: f3.try_revise(R, run, z, body_drop=("reopen_symptom",)))
        bad("h", (), 3, prop(extra_args=("--retire-when", "x")))
        rc, out, err, p = self.retire_args(R)
        self.assertEqual(rc, 0, out + err)
        rj, rk, rl, rm = branches
        for label, Rx, action, extra in (("j", rj, "retire", None), ("k", rk, "retire", "rb"),
                                         ("l", rl, "retire", "add"), ("m", rm, "delete", None)):
            with self.subTest(label=label):
                b = f3.promoted(Rx, action=action, target=T1, t="2026-10-21T10:00:00+00:00")
                n = int(b[-3:])
                if extra == "rb":
                    fx.append_events(Rx, [fx.dec_ev(n, "rollback"), fx.rollback_ev(n)])
                elif extra == "add":
                    f3.promoted(Rx, action="add", target=T1, t="2026-10-22T10:00:00+00:00")
                fx.commit_all(Rx, label)
                ex0, sx0 = evl(Rx), fx.snap(Rx)
                rc, out, err, _ = f3.try_prop(Rx, run, action="retire", target=T1, sources=[S1])
                if label in ("j", "m"):
                    self.assertEqual((rc, self.codes(out)), (1, {"RETIRE-TARGET-NOT-ADOPTED"}))
                    self.draft_ok(Rx, out, label)
                    self.assertEqual((evl(Rx), fx.snap(Rx)), (ex0, sx0))
                else:
                    self.assertEqual(rc, 0, out + err)

    def test_AT_325_1_E_2_form_vectors(self):
        n = {"N1": ("含 R123 的句子", "輪號"), "N2": ("見 improving_117", "輪號"),
             "N3": ("於 2026-10-24 之後", "日期"), "N4": ("待排程再說", "待排程"),
             "N5": ("第一行\n第二行", "換行"), "N6": ("R7 之後", "輪號")}
        for key, (text, cause) in n.items():
            with self.subTest(key=key):
                got = retire.form_problems(text)
                self.assertEqual(len(got), 1)
                self.assertEqual(got[0][0], "RETIRE-FIELD-FORM")
                self.assertIn(cause, got[0][1])
        for key, text in {"C1": "見 PR123 說明", "C2": "ROW-MUTATED 不再出現", "C3": "CR2 的段落",
                          "C4": "  合規的一句  ", "C5": "", "C6": "   "}.items():
            with self.subTest(key=key):
                self.assertEqual(retire.form_problems(text), [])

    def test_AT_325_2_1_retire_goes_through_the_same_human_gate(self):
        def build(R):
            f3.promoted(R, target=fx2.DEMO)
            f3.promoted(R, cls="R", target=RULE)

        R, _ = self.scenario(build)
        pd = fx2.drive_to(R, "proposed", cls="D", action="retire", target=fx2.DEMO)
        states = [self.prop_state(R, pd)]
        fx2.issue_card(R, pd)
        states.append(self.prop_state(R, pd))
        rc, out, err, _, _ = fx2.decide_say(R, pd, f"核准 {pd}", issue=False)
        self.assertEqual(rc, 0, out + err)
        states.append(self.prop_state(R, pd))
        src = fx2.make_heldout(fx.new_dir("ho"), probes="count", target=fx2.DEMO)
        for argv in (("heldout-freeze", pd, "--from", src, "--by", "FZ"),
                     ("sandbox", pd, "--by", "SB1"), ("verify", pd, "--by", "VF1")):
            rc, out, err = fx2.cli(R, *argv)
            self.assertEqual(rc, 0, out + err)
            states.append(self.prop_state(R, pd))
        rc, out, err, _, _ = fx2.decide_say(R, pd, f"晉升 {pd}")
        self.assertEqual(rc, 0, out + err)
        states.append(self.prop_state(R, pd))
        rc, out, err = fx2.cli(R, "promote", pd, "--by", "PR1")
        self.assertEqual(rc, 0, out + err)
        states.append(self.prop_state(R, pd))
        self.assertEqual(states, ["proposed", "proposed", "approved", "approved", "sandboxed",
                                  "verified", "verified", "promoted"])
        pr = fx2.drive_to(R, "proposed", cls="R", action="retire", target=RULE)
        for p in (pd, pr):
            ev = next(e for e in fx.EV(R) if e["kind"] == "prop" and e["id"] == p)
            self.assertEqual((ev["route"], ev["action"]), ("loop", "retire"))
        hint = "SDD 規則退役須經 set_maturity(reviewed_by=<人>)；本迴圈不呼叫 SDD 碼"
        card_r = fx2.issue_card(R, pr)
        head, _, tail = card_r.partition("--- 以下不計入核心區 ---")
        self.assertIn(hint, tail)
        self.assertNotIn(hint, head)
        self.assertNotIn(hint, self.M(R, "card", pd)[1])

    def test_AT_325_2_E_1_the_system_only_proposes(self):
        def build(R):
            f3.s_base(R)
            f3.s_adopt(R)
            fx.set_params(R, memory_index_max_lines=20)
            idx = si_transcript.transcript_dir(R) / "memory" / "MEMORY.md"
            idx.parent.mkdir(parents=True)
            idx.write_bytes(cap_index(17))

        R, _ = self.scenario(build)
        e0, g0 = fx.EV(R), f3.porcelain(R)
        for argv in (("capacity",), ("scan",), ("measure",), ("status",)):
            rc, out, err = self.M(R, *argv)
            self.assertEqual(rc, 0, f"{argv} {out}{err}")
        new = fx.EV(R)[len(e0):]
        self.assertTrue(new and all(e["kind"].startswith("mea.") for e in new))
        self.assertEqual(f3.porcelain(R) - g0, {"docs/06_quality/SelfImproving_Event_Ledger.jsonl"})
        sources = [*sorted((fx.ROOT / "tools/lib/selfimproving").glob("*.py")),
                   fx.ROOT / "tools/selfimproving.py"]
        for p in sources:
            self.assertEqual(sdd_code_problems(p.read_text(encoding="utf-8")), [], p.name)
        self.assertEqual(len(sdd_code_problems("set_maturity(x)\n")), 1)
        self.assertEqual(len(sdd_code_problems("import rule_loader\n")), 1)
        self.assertEqual(len(sdd_code_problems("from fsm_runtime import x\n")), 1)


def sdd_code_problems(src: str) -> list[str]:
    """對 `set_maturity` 的呼叫、對 `rule_loader` 與 `fsm_runtime` 的 import（AST）。"""
    out = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Call) and ast.unparse(n.func).split(".")[-1] == "set_maturity":
            out.append("CALL-SET-MATURITY")
        mods = ([a.name for a in n.names] if isinstance(n, ast.Import)
                else [n.module or ""] if isinstance(n, ast.ImportFrom) else [])
        out += ["IMPORT-SDD" for m in mods if m.split(".")[0] in ("rule_loader", "fsm_runtime")]
    return out


class TestChurn(CrTestCase):
    def churn_try(self, R, s, *, sources, target=T1):
        return f3.try_prop(R, fx.rid(1), action="add", target=target, sources=sources)

    def test_AT_326_1_1_second_cycle_is_allowed(self):
        R, s = self.scenario(lambda r: f3.s_churn(r, 4))
        rc, out, err, p = self.churn_try(R, s, sources=[s["n1"], s["c1"]])
        self.assertEqual(rc, 0, out + err)
        ev = next(e for e in fx.EV(R) if e["kind"] == "prop" and e["id"] == p)
        self.assertEqual(ev["action"], "add")
        self.assertEqual(self.prop_state(R, p), "proposed")
        R2, s2 = self.scenario(lambda r: f3.s_churn(r, 4))
        fx.set_params(R2, churn_max=1)
        e0, snap0 = evl(R2), fx.snap(R2)
        rc, out, err, _ = self.churn_try(R2, s2, sources=[s2["n1"], s2["c1"]])
        self.assertEqual(rc, 1)
        self.assertIn("CHURN-EXCEEDED", self.codes(out))
        self.assertNotIn("CAPABILITY-DELTA-MISSING", self.codes(out))
        self.assertEqual((evl(R2), fx.snap(R2)), (e0, snap0))

    def test_AT_326_1_E_1_third_cycle_is_blocked(self):
        R, s = self.scenario(lambda r: f3.s_churn(r, 6))
        e0, snap0 = evl(R), fx.snap(R)
        rc, out, err, _ = self.churn_try(R, s, sources=[s["n1"], s["c1"]])
        self.assertEqual(rc, 1)
        self.assertIn("CHURN-EXCEEDED", self.codes(out))
        self.assertNotIn("CAPABILITY-DELTA-MISSING", self.codes(out))
        self.draft_ok(R, out)
        self.assertEqual((evl(R), fx.snap(R)), (e0, snap0))
        for label in "abc":
            Rx, sx = self.scenario(lambda r: f3.s_churn(r, 6))
            if label == "a":
                fx.set_params(Rx, churn_max=3)
                args = {"sources": [sx["n1"], sx["c1"]]}
            elif label == "b":
                args = {"sources": [sx["n1"], sx["c1"]], "target": T2}
            else:
                args = {"sources": [sx["n1"], sx["c2"]]}
            rc, out, err, _ = self.churn_try(Rx, sx, **args)
            self.assertEqual(rc, 0, f"{label} {out}{err}")
        Rd, sd = self.scenario(lambda r: f3.s_churn(r, 6))
        rc, out, err, _ = self.churn_try(Rd, sd, sources=[sd["c1"]])
        self.assertEqual(rc, 1)
        self.assertLessEqual({"CHURN-EXCEEDED", "CAPABILITY-DELTA-MISSING"}, self.codes(out))

    def test_AT_326_1_E_2_a_second_add_does_not_count_a_cycle_without_a_retire(self):
        def build(R):
            s = f3.s_churn(R, 0)
            s["props"] = [f3.promoted(R, action=a, target=T1, sources=[s["c1"]],
                                      t=f"2026-10-{day}T10:00:00+00:00")
                          for a, day in (("add", 12), ("retire", 13), ("add", 14), ("add", 15),
                                         ("retire", 16))]
            return s

        # 序列 add、retire、add、add、retire：只有 retire 之後的第一個 add 計一個循環（共 1 個）
        R, s = self.scenario(build)
        fx.set_params(R, churn_max=2)
        rc, out, err, _ = self.churn_try(R, s, sources=[s["n1"], s["c1"]])
        self.assertEqual(rc, 0, out + err)
        Rb, sb = self.scenario(build)
        fx.set_params(Rb, churn_max=1)
        e0 = evl(Rb)
        rc, out, err, _ = self.churn_try(Rb, sb, sources=[sb["n1"], sb["c1"]])
        self.assertEqual((rc, self.codes(out)), (1, {"CHURN-EXCEEDED"}))
        self.assertEqual(evl(Rb), e0)

    def test_AT_326_1_E_3_unconfirmed_root_keys_do_not_join_the_group(self):
        def build(confirm):
            def inner(R):
                s = f3.s_churn(R, 4)
                s["x1"] = f3.obs_at(R, 27, "2026-10-12 09:00 +00:00", "",
                                    evidence=f"{D3}/f.md:15")
                f3.root_attr(R, [s["x1"]], "k/c", confirm=confirm)
                return s
            return inner

        R, s = self.scenario(build(False))
        fx.set_params(R, churn_max=1)
        rc, out, err, p = self.churn_try(R, s, sources=[s["x1"]])
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("CHURN-EXCEEDED", out + err)
        self.assertNotIn("CAPABILITY-DELTA-MISSING", out + err)
        self.assertEqual(self.prop_state(R, p), "proposed")
        Rc, sc = self.scenario(build(True))
        fx.set_params(Rc, churn_max=1)
        e0 = evl(Rc)
        rc, out, err, _ = self.churn_try(Rc, sc, sources=[sc["x1"]])
        self.assertEqual(rc, 1)
        self.assertLessEqual({"CHURN-EXCEEDED", "CAPABILITY-DELTA-MISSING"}, self.codes(out))
        self.assertEqual(evl(Rc), e0)

    def test_AT_326_2_1_capability_delta_present(self):
        def build(R):
            s = f3.s_churn(R, 2)
            s["n2"] = f3.def_at(R, 8, "2026-10-13", "", evidence=f"{D3}/f.md:14")
            return s

        for label, pick in (("a", ("n1", "c1")), ("b", ("n2", "c1"))):
            R, s = self.scenario(build)
            rc, out, err, p = self.churn_try(R, s, sources=[s[pick[0]], s[pick[1]]])
            self.assertEqual(rc, 0, f"{label} {out}{err}")
            ev = next(e for e in fx.EV(R) if e["kind"] == "prop" and e["id"] == p)
            self.assertIn(s[pick[0]], ev["sources"])
        R, s = self.scenario(build)
        e0, snap0 = evl(R), fx.snap(R)
        rc, out, err, _ = self.churn_try(R, s, sources=[s["c1"]])
        self.assertEqual((rc, self.codes(out)), (1, {"CAPABILITY-DELTA-MISSING"}))
        self.draft_ok(R, out)
        self.assertEqual((evl(R), fx.snap(R)), (e0, snap0))

    def test_AT_326_2_E_1_capability_delta_boundaries(self):
        def build(tr=None):
            def inner(R):
                s = f3.s_churn(R, 2, tr=tr)
                s["o1"] = f3.obs_at(R, 24, "2026-10-14 10:00 +00:00", "",
                                    evidence=f"{D3}/f.md:3")
                s["o2"] = f3.obs_at(R, 25, "2026-10-12 09:00 +00:00", "",
                                    evidence=f"{D3}/f.md:11")
                s["d0"] = f3.def_at(R, 8, "2026-10-12", "", evidence=f"{D3}/f.md:12")
                s["d1"] = f3.def_at(R, 9, "2026-10-13", "", evidence=f"{D3}/f.md:13")
                return s
            return inner

        for label, extra, ok in (("a", None, False), ("b", "o1", False), ("c", "o2", False),
                                 ("d", "d0", False), ("e", "d1", True)):
            R, s = self.scenario(build())
            e0, snap0 = evl(R), fx.snap(R)
            sources = [s["c1"]] + ([s[extra]] if extra else [])
            rc, out, err, _ = self.churn_try(R, s, sources=sources)
            if ok:
                self.assertEqual(rc, 0, f"{label} {out}{err}")
            else:
                self.assertEqual((rc, self.codes(out)), (1, {"CAPABILITY-DELTA-MISSING"}), label)
                self.draft_ok(R, out, label)
                self.assertEqual((evl(R), fx.snap(R)), (e0, snap0))
        R, s = self.scenario(build("2026-10-14T00:00:00+00:00"))
        rc, out, err, _ = self.churn_try(R, s, sources=[s["c1"], s["d1"]])
        self.assertEqual((rc, self.codes(out)), (1, {"CAPABILITY-DELTA-MISSING"}))

    def test_AT_326_2_E_2_evidence_at_the_same_instant_as_the_retire_is_not_new(self):
        def build(tr):
            def inner(R):
                s = f3.s_churn(R, 2, tr=tr)
                s["d1"] = f3.def_at(R, 9, "2026-10-13", "", evidence=f"{D3}/f.md:13")
                return s
            return inner

        # DEF 列的 instant 一律為發現日當天 23:59:59+00:00；退役晉升時刻取同一刻 ⇒ 不算「晚於」
        R, s = self.scenario(build("2026-10-13T23:59:59+00:00"))
        e0 = evl(R)
        rc, out, err, _ = self.churn_try(R, s, sources=[s["c1"], s["d1"]])
        self.assertEqual((rc, self.codes(out)), (1, {"CAPABILITY-DELTA-MISSING"}))
        self.assertEqual(evl(R), e0)
        R, s = self.scenario(build("2026-10-13T23:59:58+00:00"))
        rc, out, err, _ = self.churn_try(R, s, sources=[s["c1"], s["d1"]])
        self.assertEqual(rc, 0, out + err)


class TestCapacity(CrTestCase):
    def cap(self, R, *argv):
        return self.MJ(R, "capacity", *argv)

    def write(self, name, data: bytes) -> Path:
        p = fx.new_dir(name)
        p.write_bytes(data)
        return p

    def draft_cells(self, row: str) -> list[str]:
        return [c.strip() for c in row.strip("| \n").split(" | ")]

    def test_AT_327_1_1_memory_index_axes_candidates_and_drafts(self):
        R, _ = self.scenario()
        cases = {"a": (cap_index(17), {"memory_index_max_lines": 20}, (19, 20, 3, 17, 19)),
                 "b": (cap_index(18), {"memory_index_max_bytes": 1000}, (928, 1000, 2, 19, 20))}
        for key, (data, prm, (used, limit, n_cand, first, last)) in cases.items():
            with self.subTest(key=key):
                Rx = self.copy(R)
                fx.set_params(Rx, **prm)
                rep = self.cap(Rx, "--memory-index", str(self.write("ix", data)))
                mem = rep["memory_index"]
                self.assertEqual((mem["over_cap"], mem["used"], mem["limit"]), (True, used, limit))
                cards = rep["retire_candidates"]
                self.assertEqual(len(cards), 1)
                lines = data.split(b"\n")
                entries = [ln + b"\n" for ln in lines if ln.startswith(b"- ")]
                self.assertEqual(cards[0]["card"].encode(), b"".join(entries[-n_cand:]))
                self.assertEqual((cards[0]["first_line"], cards[0]["last_line"]), (first, last))
                self.assertEqual([(e["trigger"], e["subject"]) for e in rep["events_detected"]],
                                 [("e", "memory_index")])
                self.assertEqual(len(rep["obs_drafts"]), 1)
                cells = self.draft_cells(rep["obs_drafts"][0])
                self.assertEqual(cells[5:8], ["process", "P3", "open"])
                self.draft_ok(Rx, "obs-draft:\n" + rep["obs_drafts"][0])
        Rc = self.copy(R)
        fx.set_params(Rc, memory_index_max_lines=20)
        rep = self.cap(Rc, "--memory-index", str(self.write("ix", cap_index(15))))
        self.assertEqual((rep["memory_index"]["over_cap"], rep["retire_candidates"],
                          rep["events_detected"], rep["obs_drafts"]), (False, [], [], []))

    def test_AT_327_1_2_kb_and_prefs_only_report_and_constants_match_the_engine(self):
        R, _ = self.scenario()
        kb = self.write("kb", json.dumps({"kb_cache_eviction_count": 1}).encode())
        pf = self.write("pf", json.dumps({f"k{i}": i for i in range(9)}).encode())
        rep = self.cap(R, "--kb-metrics", str(kb), "--prefs", str(pf))
        self.assertEqual((rep["kb"]["over_cap"], rep["prefs"]["over_cap"]), (True, True))
        self.assertEqual(rep["retire_candidates"], [])
        self.assertEqual(len(rep["obs_drafts"]), 2)
        for row in rep["obs_drafts"]:
            self.assertEqual(self.draft_cells(row)[5:8], ["process", "P4", "open"])
            self.draft_ok(R, "obs-draft:\n" + row)
        self.assertEqual([e["subject"] for e in rep["events_detected"]], ["kb", "prefs"])
        kb0 = self.write("kb0", json.dumps({"kb_cache_eviction_count": 0}).encode())
        pf8 = self.write("pf8", json.dumps({f"k{i}": i for i in range(8)}).encode())
        rep = self.cap(R, "--kb-metrics", str(kb0), "--prefs", str(pf8))
        self.assertEqual((rep["kb"]["over_cap"], rep["prefs"]["over_cap"], rep["obs_drafts"]),
                         (False, False, []))

        def const(path, name):
            for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == name
                                                     for t in n.targets):
                    return ast.literal_eval(n.value)
            self.fail(f"{path.name} 找不到 {name}")

        self.assertEqual(capacity.KB_MAX_ENTRIES, const(ENGINE_KB, "_MAX_ENTRIES"))
        self.assertEqual(capacity.PREFS_MAX_KEYS, const(ENGINE_PREFS, "_MAX_KEYS"))

    def test_AT_327_1_E_1_threshold_edges_and_not_evaluable(self):
        R, _ = self.scenario()
        fx.set_params(R, memory_index_max_lines=20, memory_index_max_bytes=1000)
        snap0, e0, h0 = fx.snap(R), evl(R), fx2.snapshot_tree(self.home)
        files = {"L18": cap_index(16), "L17": cap_index(15), "B900": cap_index(3, total_bytes=900),
                 "B899": cap_index(3, total_bytes=899)}
        want = {"L18": True, "L17": False, "B900": True, "B899": False}
        for name, data in files.items():
            rep = self.cap(R, "--memory-index", str(self.write(name, data)))
            self.assertEqual(rep["memory_index"]["over_cap"], want[name], name)
        rep = self.cap(R, "--memory-index", str(fx.new_dir("absent")))
        self.assertEqual(rep["memory_index"], {"status": "NOT-EVALUABLE",
                                               "reason": "memory-index-missing"})
        self.assertEqual((rep["obs_drafts"], rep["events_detected"]), ([], []))
        bad = self.write("kb_bad", b"{not json")
        lst = self.write("prefs_list", b"[1, 2]")
        rep = self.cap(R, "--kb-metrics", str(bad), "--prefs", str(lst))
        self.assertEqual((rep["kb"]["reason"], rep["prefs"]["reason"]),
                         ("kb-metrics-unparseable", "prefs-unparseable"))
        rep = self.cap(R)
        self.assertEqual((rep["kb"]["reason"], rep["prefs"]["reason"]),
                         ("kb-not-supplied", "prefs-not-supplied"))
        self.assertEqual((fx.snap(R), evl(R), fx2.snapshot_tree(self.home)), (snap0, e0, h0))

    def test_AT_327_1_E_2_cards_are_split_and_verbatim(self):
        params = {"cap_frac": 0.9, "memory_index_max_lines": 140, "memory_index_max_bytes": 25600,
                  "max_archive_entries_per_card": 3}
        for eol in ("\n", "\r\n"):
            data = cap_index(130, trail=2, eol=eol)
            rep = capacity.evaluate(data, None, None, params)
            cards = rep["retire_candidates"]
            self.assertEqual([(c["lines"], c["first_line"], c["last_line"]) for c in cards],
                             [(3, 125, 127), (3, 128, 130), (2, 131, 132)])
            raw = data.split(b"\n")
            for c in cards:
                want = b"".join(ln + b"\n" for ln in raw[c["first_line"] - 1:c["last_line"]])
                self.assertEqual(c["card"].encode("utf-8"), want)
            params4 = dict(params, max_archive_entries_per_card=4)
            cards4 = capacity.evaluate(data, None, None, params4)["retire_candidates"]
            self.assertEqual([(c["first_line"], c["last_line"]) for c in cards4],
                             [(125, 128), (129, 132)])

    def test_AT_327_2_1_truncation_risk_lines_and_bytes(self):
        R, _ = self.scenario()
        for key, prm, data, want in (
                ("a", {"memory_index_max_lines": 20}, cap_index(25), (7, 21)),
                ("b", {"memory_index_max_bytes": 500}, cap_index(12), (3, 12))):
            with self.subTest(key=key):
                Rx = self.copy(R)
                fx.set_params(Rx, **prm)
                path = str(self.write("ix", data))
                rep = self.cap(Rx, "--memory-index", path)
                risk = rep["truncation_risk"]
                self.assertEqual((risk["entries"], risk["first_line"]), want)
                row = next(r for r in rep["obs_drafts"] if "截斷風險：" in r)
                cells = self.draft_cells(row)
                self.assertEqual(cells[5:8], ["bug", "P2", "open"])
                self.assertTrue(cells[3].startswith("截斷風險："))
                self.draft_ok(Rx, "obs-draft:\n" + row)
                self.assertIn("truncation_risk", self.M(Rx, "capacity", "--memory-index", path)[1])

    def test_AT_327_2_E_1_no_risk_cases(self):
        p = {"memory_index_max_lines": 20, "memory_index_max_bytes": 25600}
        base = cap_index(18).decode()
        self.assertIsNone(capacity.truncation_risk(cap_index(18), p))
        pb = {"memory_index_max_lines": 200, "memory_index_max_bytes": 500}
        self.assertIsNone(capacity.truncation_risk(cap_index(9, total_bytes=500), pb))
        for tail in ("\n# 註解\n", "  - 子項\n"):
            data = (base + tail).encode()
            lines = data.split(b"\n")
            self.assertGreater(len(lines), 20)
            self.assertIsNone(capacity.truncation_risk(data, p))
        control = (base + "- e99 條目\n").encode()
        self.assertEqual(capacity.truncation_risk(control, p), {"entries": 1, "first_line": 21})

    def test_AT_327_2_E_2_entry_ending_exactly_at_the_byte_limit_is_not_at_risk(self):
        # 表頭 10 位元組、每個條目行 51 位元組：第 10 個條目的結束偏移恰為 520
        prm = {"memory_index_max_lines": 200, "memory_index_max_bytes": 520}
        data = cap_index(12)
        self.assertGreater(len(data), 520)
        self.assertEqual(capacity.truncation_risk(data, prm), {"entries": 2, "first_line": 13})
        under = dict(prm, memory_index_max_bytes=521)
        self.assertEqual(capacity.truncation_risk(data, under), {"entries": 2, "first_line": 13})
        over = dict(prm, memory_index_max_bytes=519)
        self.assertEqual(capacity.truncation_risk(data, over), {"entries": 3, "first_line": 12})

    def test_AT_340_3_1_capacity_cli_contract_is_read_only(self):
        def build(R):
            fx.set_params(R, memory_index_max_lines=20)
            idx = si_transcript.transcript_dir(R) / "memory" / "MEMORY.md"
            idx.parent.mkdir(parents=True)
            idx.write_bytes(cap_index(17))

        R, _ = self.scenario(build)
        kb = self.write("kb", json.dumps({"kb_cache_eviction_count": 0}).encode())
        pf = self.write("pf", json.dumps({"a": 1, "b": 2, "c": 3}).encode())
        idx = si_transcript.transcript_dir(R) / "memory" / "MEMORY.md"
        e0, g0, snap0 = evl(R), f3.porcelain(R), fx.snap(R)
        h0 = fx2.snapshot_tree(self.home)
        dirs0 = sorted(p for p in self.home.rglob("*") if p.is_dir())
        r1 = self.cap(R)
        keys = ["schema_rev", "cap_frac", "memory_index", "kb", "prefs", "retire_candidates",
                "truncation_risk", "obs_drafts", "events_detected"]
        self.assertEqual((list(r1), r1["schema_rev"]), (keys, 1))
        self.assertEqual((r1["kb"]["reason"], r1["prefs"]["reason"]),
                         ("kb-not-supplied", "prefs-not-supplied"))
        text = self.M(R, "capacity")
        self.assertEqual(text[0], 0)
        r3 = self.cap(R, "--memory-index", str(idx), "--kb-metrics", str(kb), "--prefs", str(pf))
        self.assertEqual((r3["kb"]["status"], r3["kb"]["over_cap"], r3["prefs"]["status"],
                          r3["prefs"]["over_cap"]), ("read", False, "read", False))
        from unittest import mock
        with mock.patch.dict("os.environ", {"AUTOSDD_UNATTENDED": "1"}):
            r4 = self.M(R, "capacity", "--json")
        self.assertEqual((r4[0], json.loads(r4[1])), (0, r1))
        lines = text[1].splitlines()
        self.assertEqual([ln.split(":")[0] for ln in lines[:3]], ["memory_index", "kb", "prefs"])
        self.assertIn("obs-draft:", lines)
        self.assertTrue(lines[-1].startswith("| OBS-SI-"))
        self.assertEqual((evl(R), f3.porcelain(R), fx.snap(R), fx2.snapshot_tree(self.home)),
                         (e0, g0, snap0, h0))
        self.assertEqual(sorted(p for p in self.home.rglob("*") if p.is_dir()), dirs0)

    def test_AT_340_3_E_1_usage_errors_versus_not_evaluable(self):
        R, _ = self.scenario()
        snap0 = fx.snap(R)
        rc, out, err = self.M(R, "capacity", "--force")
        self.usage_error(rc, out, err)
        for key in ("cap_frac", "memory_index_max_lines", "memory_index_max_bytes",
                    "max_archive_entries_per_card"):
            for label, value in (("missing", KeyError), ("type", "x")):
                with self.subTest(key=key, label=label):
                    Rx = self.copy(R)
                    fx.set_params(Rx, **{key: value})
                    rc, out, err = self.M(Rx, "capacity")
                    self.usage_error(rc, out, err)
                    self.assertIn(key, err)
        afile = self.write("afile", b"x")
        rc, out, err = self.run_main(["capacity", "--repo", str(afile)])
        self.usage_error(rc, out, err)
        rep = self.cap(R, "--memory-index", str(fx.new_dir("absent")))
        self.assertEqual(rep["memory_index"]["reason"], "memory-index-missing")
        adir = fx.new_dir("adir")
        adir.mkdir()
        rep = self.cap(R, "--kb-metrics", str(adir))
        self.assertEqual(rep["kb"]["reason"], "kb-metrics-unparseable")
        self.assertEqual(fx.snap(R), snap0)


if __name__ == "__main__":
    unittest.main()
