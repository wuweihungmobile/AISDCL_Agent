# 受測面：tools/lib/selfimproving/params.py（程式碼鎖，非散文）
"""SelfImproving P3 元層驗收（TCS-SelfImproving-P3 §2 E 組；M3 檔 10 個 AT）：新參數、Operations SOP
〈P3 動詞〉與提案者隔離、零退化與夾具升級、AT 錨定可重跑檢查。

受測：`tools/lib/selfimproving/params.py`（`PARAM_SPECS`、`CHECK_RULES_REV`）、Operations SOP 文字、
夾具 `_selfimproving_p3_fixtures.py` 與 `_selfimproving_fixtures.py` 的升級。判準函式
（`sop_p3_problems`）取 SOP 文字，故真檔與合成副本用同一份碼自證；錨定檢查沿用
`test_selfimproving_p2_meta.py` 的同名函式。
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import unittest
from pathlib import Path

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p3_fixtures as f3
from _selfimproving_p3_fixtures import D3, win
from test_selfimproving_p2_meta import (
    anchor_problems,
    collect_nodes,
    parse_at_headers,
    real_tcs,
    underscore_form,
)

import selfimproving
from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold
from lib.selfimproving import params as si_params

ROOT = fx.ROOT
SOP = ROOT / "docs" / "05_development" / "SelfImproving_Operations_SOP.md"
TESTS = ROOT / "tools" / "tests"
SEVEN = ("test_selfimproving_measure.py", "test_selfimproving_measure_verb.py",
         "test_selfimproving_measure_probe.py", "test_selfimproving_capacity_retire.py",
         "test_selfimproving_p3_meta.py", "test_selfimproving_capability.py",
         "test_selfimproving_console_obs.py")
FORBID = ("params.json", "selfimproving_measure", "metrics.md", "w_opp", "w_evt", "w_min",
          "stop_after_bad", "churn_max", "M1", "fingerprint")
FOUR = ("擷取者", "歸因者", "提案者", "研究者")
# SOP-P3-REQ：(列號, 同一行（圍欄外）須依序含的片段)；第 6 列（兩個圍欄）與第 7 列（逐片段）另判
LINE_REQS = {
    1: ("`measure`", "AUTOSDD_UNATTENDED", "rc 1"),
    2: ("`capacity`", "NOT-EVALUABLE", "量不到不是 rc 3"),
    3: ("`promote`", "主控 `commit`", "`measure`"),
    4: ("`run-close`", "之前跑一次 `measure` 作補記"),
    5: ("`measure`", "卡面逐字貼給掌舵者", "掌舵者打字回滾", "`decide --kind rollback`",
        "`rollback`"),
    8: ("set_maturity(reviewed_by=",),
    9: ("NOT-EVALUABLE 不得改寫為達標", "M1 不得單獨宣稱成效", "反證條件成立只列為 T1 決策項"),
    10: ("提案者任務書不含指標目標值、計算細節與 params.json 路徑",),
}
EXTRA_ATS = (
    "AT-323-1-E-6", "AT-323-1-E-7", "AT-323-1-E-8", "AT-323-1-E-9", "AT-322-1-E-4",
    "AT-326-1-E-2", "AT-326-1-E-3", "AT-326-2-E-2", "AT-327-2-E-2", "AT-340-1-E-3",
    "AT-340-1-E-4", "AT-340-2-E-3", "AT-340-2-E-4", "AT-340-2-E-5", "AT-340-2-E-6",
    "AT-340-5-E-2", "AT-340-5-E-3", "AT-340-6-E-4")
ORDERED = (3, 5)
RECIPE = ("`--cls M`", "`--action retire`", "retire_when", "reopen_symptom", "目標在役")
PROBES = {1: "AUTOSDD_UNATTENDED", 2: "量不到不是 rc 3", 3: "主控 `commit`", 4: "之前跑一次",
          5: "掌舵者打字回滾", 6: "```bash", 7: "目標在役", 8: "set_maturity(reviewed_by=",
          9: "M1 不得單獨宣稱成效", 10: "提案者任務書不含"}


def setUpModule():
    fx.setup("si_p3t_")


def tearDownModule():
    fx.teardown()


def section(text: str, title: str) -> str:
    """`## <title>` 或 `### <title>` 之後到下一個同級或更高標題為止。"""
    m = re.search(rf"(?m)^(#{{2,3}}) [^\n]*{re.escape(title)}[^\n]*\n", text)
    if not m:
        return ""
    end = re.search(rf"(?m)^#{{1,{len(m.group(1))}}} ", text[m.end():])
    return text[m.start():m.end() + (end.start() if end else len(text))]


def outside_fences(body: str) -> list[str]:
    return fx.lines_outside_fences(body)


def _in_order(line: str, frags) -> bool:
    pos = 0
    for f in frags:
        at = line.find(f, pos)
        if at < 0:
            return False
        pos = at + len(f)
    return True


def sop_p3_problems(text: str) -> list[str]:
    """R133／SOP-P3-REQ：回問題字串（碼起頭）；每項只在自己的片段缺失時被點名。"""
    out: list[str] = []
    for title in FOUR:
        body = section(text, title)
        out += [f"SOP-P3-FORBIDDEN 〈{title}〉含 {frag}" for frag in FORBID if frag in body]
    p3, p2 = section(text, "P3 動詞"), section(text, "P2 動詞")
    if not p3 or text.find(p3) < text.find(p2) or not p2:
        return out + ["SOP-P3-REQ-MISSING REQ-0：〈P3 動詞〉節缺或不在〈P2 動詞〉之後"]
    lines = outside_fences(p3)
    for n, frags in LINE_REQS.items():
        hits = [ln for ln in lines if all(f in ln for f in frags)]
        if not hits:
            out.append(f"SOP-P3-REQ-MISSING REQ-{n}：缺必備片段 {frags}")
        elif n in ORDERED and not any(_in_order(ln, frags) for ln in hits):
            out.append(f"SOP-P3-ORDER REQ-{n}：片段次序不符 {frags}")
    fences = re.findall(r"```(\w*)\n(.*?)```", p3, re.S)
    ok = all(any(lang.lower() == want and "decide" in body and "rollback" in body
                 for lang, body in fences) for want in ("powershell", "bash"))
    if not ok:
        out.append("SOP-P3-REQ-MISSING REQ-6：powershell 與 bash 圍欄須各含 decide 與 rollback")
    joined = "\n".join(lines)
    if [f for f in RECIPE if f not in joined]:
        out.append("SOP-P3-REQ-MISSING REQ-7：退役配方片段不全")
    if "待補" in p3 or "TODO" in p3:
        out.append("SOP-P3-PLACEHOLDER 〈P3 動詞〉含待補或 TODO")
    if "尚無該動詞" in section(text, "啟動條件"):
        out.append("SOP-P3-STALE-WORDING 〈啟動條件〉含尚無該動詞")
    return out


def code_of(problem: str) -> str:
    return problem.split(" ", 1)[0]


class TestSop(unittest.TestCase):
    text = SOP.read_text(encoding="utf-8")

    def test_AT_322_3_1_four_sections_have_no_forbidden_fragments(self):
        self.assertEqual(sop_p3_problems(self.text), [])
        for title in FOUR:
            body = section(self.text, title)
            self.assertTrue(body, title)
            for frag in FORBID:
                self.assertNotIn(frag, body, (title, frag))
        p3 = "\n".join(outside_fences(section(self.text, "P3 動詞")))
        self.assertIn(LINE_REQS[10][0], p3)

    def test_AT_322_3_E_1_isolation_check_has_teeth(self):
        for title in FOUR:
            body = section(self.text, title)
            for frag in FORBID:
                with self.subTest(title=title, frag=frag):
                    changed = self.text.replace(body, body.rstrip("\n") + f"\n{frag}\n", 1)
                    got = sop_p3_problems(changed)
                    self.assertEqual(len(got), 1, got)
                    self.assertEqual(code_of(got[0]), "SOP-P3-FORBIDDEN")
                    self.assertIn(title, got[0])
                    self.assertIn(frag, got[0])
        iso = LINE_REQS[10][0]
        deleted = self.text.replace(iso, "", 1)
        got = sop_p3_problems(deleted)
        self.assertEqual([code_of(p) for p in got], ["SOP-P3-REQ-MISSING"])
        self.assertIn("REQ-10", got[0])
        line = next(ln for ln in self.text.split("\n") if iso in ln)
        fenced = self.text.replace(line, f"```\n{line}\n```", 1)
        got = sop_p3_problems(fenced)
        self.assertEqual([code_of(p) for p in got], ["SOP-P3-REQ-MISSING"])
        self.assertEqual(sop_p3_problems(self.text), [])

    def test_AT_340_7_1_p3_verbs_section_is_complete(self):
        self.assertEqual(sop_p3_problems(self.text), [])
        p3, p2 = section(self.text, "P3 動詞"), section(self.text, "P2 動詞")
        self.assertTrue(p2 and p3)
        self.assertGreater(self.text.find(p3), self.text.find(p2))
        self.assertNotIn("尚無該動詞", section(self.text, "啟動條件"))
        self.assertNotIn("尚無該動詞", self.text)
        for word in ("待補", "TODO"):
            self.assertNotIn(word, p3)
        langs = {m.lower() for m in re.findall(r"```(\w*)", p3)}
        self.assertLessEqual({"powershell", "bash"}, langs)

    def test_AT_340_7_E_1_sop_check_has_teeth(self):
        text = self.text
        p3 = section(text, "P3 動詞")
        for n, probe in PROBES.items():
            with self.subTest(req=n):
                # 全部移除：同一字面可重複出現
                changed_p3 = p3.replace(probe, "" if n != 6 else "```")
                self.assertNotEqual(changed_p3, p3, n)
                got = sop_p3_problems(text.replace(p3, changed_p3, 1))
                self.assertEqual([code_of(p) for p in got], ["SOP-P3-REQ-MISSING"], (n, got))
                self.assertIn(f"REQ-{n}", got[0])
        line = next(ln for ln in outside_fences(p3) if all(f in ln for f in LINE_REQS[5]))
        got = sop_p3_problems(text.replace(line, f"```\n{line}\n```", 1))
        self.assertEqual([code_of(p) for p in got], ["SOP-P3-REQ-MISSING"])
        row3 = next(ln for ln in outside_fences(p3) if all(f in ln for f in LINE_REQS[3]))
        swapped = row3.replace("`promote`", "@@").replace("`measure`", "`promote`").replace(
            "@@", "`measure`")
        got = sop_p3_problems(text.replace(row3, swapped, 1))
        self.assertEqual([code_of(p) for p in got], ["SOP-P3-ORDER"])
        got = sop_p3_problems(text.replace(p3, p3 + "\n待補\n", 1))
        self.assertEqual([code_of(p) for p in got], ["SOP-P3-PLACEHOLDER"])
        start = section(text, "啟動條件")
        got = sop_p3_problems(text.replace(start, start.rstrip("\n") + "\n尚無該動詞\n", 1))
        self.assertEqual([code_of(p) for p in got], ["SOP-P3-STALE-WORDING"])


class TestParams(f3.P3TestCase):
    def test_AT_340_4_1_two_new_parameters(self):
        real = json.loads((ROOT / f3.fx.PARAMS).read_text(encoding="utf-8"))
        self.assertEqual(len(real), 32)
        self.assertEqual(list(real), sorted(real, key=lambda k: k.encode("utf-8")))
        self.assertEqual((real["memory_index_max_lines"], real["memory_index_max_bytes"]),
                         (200, 25600))
        for key in ("memory_index_max_lines", "memory_index_max_bytes"):
            self.assertEqual(si_params.PARAM_SPECS[key], "int1")
        self.assertEqual(set(real), set(si_params.PARAM_SPECS))
        self.assertEqual(si_params.params_file_problems((ROOT / f3.fx.PARAMS).read_bytes()), [])
        self.new_home()
        res = self.check(f3.p3_base())
        for item in ("params.keys", "params.globs", "params.coupling"):
            self.assertEqual(self.S(res, item), "PASS", item)
        self.assertEqual(res["overall"], "PASS")

    def test_AT_340_4_E_1_invalid_values_are_named_not_defaulted(self):
        self.new_home()
        base = f3.p3_base()
        idx = __import__("lib.selfimproving.transcript", fromlist=["x"]).transcript_dir(base)
        cases = {"a": ("memory_index_max_lines", KeyError, "PARAM-MISSING"),
                 "b": ("memory_index_max_bytes", KeyError, "PARAM-MISSING"),
                 "c": ("memory_index_max_lines", "x", "PARAM-TYPE"),
                 "d": ("memory_index_max_bytes", True, "PARAM-TYPE"),
                 "e": ("memory_index_max_lines", 0, "PARAM-RANGE"),
                 "f": ("memory_index_max_bytes", -1, "PARAM-RANGE"),
                 "g": ("memory_index_max_lines", 1.5, "PARAM-TYPE"),
                 "h": ("memory_index_max_lines", 200, None)}
        for label, (key, value, code) in cases.items():
            with self.subTest(label):
                R = fx.new_dir("pv")
                shutil.copytree(base, R)
                fx.set_params(R, **{key: value})
                res = self.check(R)
                if code:
                    self.assertEqual(self.S(res, "params.keys"), "FAIL")
                    self.assertEqual({c for _, c in self.F(res, "params.keys")}, {code})
                else:
                    self.assertEqual(self.S(res, "params.keys"), "PASS")
                path = idx.parent / (idx.name) / "memory" / "MEMORY.md"
                path = __import__("lib.selfimproving.transcript", fromlist=["x"]).transcript_dir(
                    R) / "memory" / "MEMORY.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(f3.cap_index(3))
                for verb in ("capacity", "status"):
                    rc, out, err = self.M(R, verb)
                    if code:
                        self.usage_error(rc, out, err, verb)
                        self.assertIn(key, err, verb)
                    else:
                        self.assertEqual(rc, 0, (verb, err))


class TestZeroRegression(f3.P3TestCase):
    def test_AT_340_8_1_upgraded_fixtures_replay_the_old_scenarios(self):
        scenarios = {"sc_close": (fx.sc_close(), None), "sc_legal": (fx.sc_legal(), None),
                     "sc_rev": (fx.sc_rev(), None), "sc_susp": (fx.sc_susp(), None),
                     "sc_seq": fx.sc_seq(), "sc_p2_legal": (fx2.sc_p2_legal(), None)}
        for name, (events, seqs) in scenarios.items():
            with self.subTest(name):
                self.new_home()
                R = fx2.make_p2_repo(fx.new_dir("zr"))
                fx.write_events(R, events, seqs=seqs)
                res = self.check(R)
                self.assertEqual(self.S(res, "events.structure"), "PASS", name)
                folded = si_fold.fold(si_events.sound(fx.EV(R)), 2)
                bad = {c for c, _, _ in folded.problems}
                self.assertFalse(bad & {"TRANSITION-ILLEGAL", "TRANSITION-ORPHAN"}, (name, bad))
        counts = {}
        for prefix, want in (("P0", 42), ("P1", 163), ("P2", 137)):
            ats = parse_at_headers(real_tcs(prefix))
            counts[prefix] = len(ats)
            self.assertEqual(len(ats), want, prefix)
        surface = [*TESTS.glob("*.py"),
                   ROOT / "AutoClaude" / "tests" / "contract" / "test_evolution_propose_only.py"]
        names = "\n".join(n for p in surface if p.is_file()
                          for n in re.findall(r"def (test_\w+)", p.read_text(encoding="utf-8")))
        for prefix in ("P0", "P1", "P2"):
            ids = [a for a, _, _ in parse_at_headers(real_tcs(prefix))]
            self.assertEqual([a for a in ids if underscore_form(a) not in names], [], prefix)
        import test_selfimproving_capability as cap
        self.assertEqual(si_params.CHECK_RULES_REV, 4)
        self.assertEqual(len(selfimproving._HELP), 23)
        self.assertIn(len(cap.CAPABILITY), (47, 48))
        want = {47: (35, 8, 2, 2), 48: (36, 8, 2, 2)}[len(cap.CAPABILITY)]
        got = tuple(sum(1 for v in cap.CAPABILITY.values() if v == k)
                    for k in ("ro", "rw", "net", "exec"))
        self.assertEqual(got, want)
        body = fx.body_md("D")
        self.assertTrue("| retire_when |" in body and "| reopen_symptom |" in body)
        props_src = (TESTS / "test_selfimproving_props.py").read_text(encoding="utf-8")
        self.assertIn('"retire_when": fields["retire_when"]', props_src)
        events_src = (TESTS / "test_selfimproving_events.py").read_text(encoding="utf-8")
        node = next(n for n in ast.walk(ast.parse(events_src)) if isinstance(n, ast.FunctionDef)
                    and n.name.startswith("test_AT_140_1_E_1_"))
        self.assertNotIn('("capacity", "frobnicate")', ast.get_source_segment(events_src, node))
        self.assertIn('"console_pending", "measure"', events_src)
        self.new_home()
        R = f3.p3_base()
        f3.promoted(R, target=f"{D3}/z.md")
        prop = self.MJ(R, "export", "--kind", "proposals")["items"][0]
        self.assertEqual((len(prop), list(prop)[-1]), (19, "window"))
        self.assertEqual(len(list(self.MJ(R, "status"))), 15)

    def test_AT_340_8_E_1_explicit_wrong_values_survive_the_defaults(self):
        self.new_home()
        base = f3.p3_base()
        s = f3.s_base(base)
        f3.s_adopt(base)
        fx.commit_all(base, "scn")
        self.assertEqual(self.M(base, "measure")[0], 0)
        P = s["P"]
        sp = f3.promote_seq(base, P)
        evs = fx.EV(base)
        seq = {k: next(e["seq"] for e in evs if e["kind"] == k or e.get("report") == k)
               for k in ("mea.open", "mea.close", "baseline")}
        D = fx.DROP
        cases = [
            ("mea.open", seq["mea.open"], dict(prop=P, promote_seq=sp, w_opp=0), "MEA-TYPE"),
            ("mea.open", seq["mea.open"], dict(prop=P, promote_seq=D), "MEA-KEY-MISSING"),
            ("mea.close", seq["mea.close"], dict(prop=P, result="weird"), "MEA-ENUM"),
            ("mea.close", seq["mea.close"], dict(prop=P, n_opp=-1), "MEA-TYPE"),
            ("mea.amend", seq["mea.close"], dict(prop=P, to="weird"), "MEA-ENUM"),
            ("mea.report", seq["baseline"], dict(prop=P, promote_seq=sp, events=-1), "MEA-TYPE"),
            ("mea.report", seq["baseline"], dict(report="check", prop=P), "MEA-KEY-UNKNOWN"),
            ("mea.amend", seq["mea.close"], dict(prop=P, cause=0), "MEA-TYPE"),
            ("mea.report", seq["baseline"], dict(prop=P, promote_seq=sp, report="weird"),
             "MEA-ENUM")]
        head = fx.head(base)
        for i, (kind, at, over, code) in enumerate(cases):
            with self.subTest(i=i, code=code):
                R = fx.new_dir("ne")
                shutil.copytree(base, R)
                obj = fx.compose([fx.ev(kind, "main", **over)], head, [at])[0]
                for k, v in over.items():
                    if v is not D:
                        self.assertEqual(obj[k], v, k)
                    else:
                        self.assertNotIn(k, obj)

                def swap(events, obj=obj, at=at):
                    return [obj if e["seq"] == at else e for e in events]
                f3.rewrite_events(R, swap)
                res = self.check(R)
                self.assertEqual(self.S(res, "events.mea"), "FAIL")
                self.assertIn(code, {c for _, c in self.F(res, "events.mea")})
        good = fx.compose([fx.ev("mea.open", "main", prop=P, promote_seq=sp)], head,
                          [seq["mea.open"]])[0]
        R = fx.new_dir("ok")
        shutil.copytree(base, R)
        f3.rewrite_events(R, lambda events: [good if e["seq"] == good["seq"] else e
                                             for e in events])
        self.assertEqual(self.S(self.check(R), "events.mea"), "PASS")
        self.assertTrue(win(R))


class TestAnchors(unittest.TestCase):
    def test_AT_340_9_1_every_at_anchors_one_function(self):
        text = real_tcs("P3")
        ats = parse_at_headers(text)
        in_tcs = {a for a, _, _ in ats}
        # 凍結 TCS 為 78 個；SCG-4 一審修復新增的 18 個在勘誤 refreeze 前只在測試端
        # （refreeze 後 TCS 含 96 個）
        self.assertEqual(len(ats), len(in_tcs))
        self.assertIn(len(ats), (78, 78 + len(EXTRA_ATS)))
        extra = [a for a in EXTRA_ATS if a not in in_tcs]
        self.assertIn(len(extra), (0, len(EXTRA_ATS)))
        self.assertTrue(all(Path(f).name in SEVEN for _, f, _ in ats))
        collected = collect_nodes([TESTS / n for n in SEVEN], ROOT)
        self.assertEqual(anchor_problems(ats, collected), [])
        names = [n.rsplit("::", 1)[-1] for nodes in collected.values() for n in nodes]
        for at in extra:  # 勘誤前：新 AT 各恰有一個底線形錨定的函式
            hits = [n for n in names if n.startswith(f"test_{underscore_form(at)}_")]
            self.assertEqual(len(hits), 1, (at, hits))
        mine = {underscore_form(a) for a in in_tcs | set(EXTRA_ATS)}
        for nodes in collected.values():
            for node in nodes:
                name = node.rsplit("::", 1)[-1]
                if name.startswith("test_AT_3"):
                    self.assertTrue(any(name.startswith(f"test_{m}_") for m in mine), node)

    def test_AT_340_9_E_1_anchor_check_has_teeth(self):
        tmp = fx.new_dir("anchor")
        tmp.mkdir(parents=True)
        path = tmp / "test_synth.py"
        path.write_text("import unittest\n\n\nclass T(unittest.TestCase):\n"
                        "    def test_AT_999_1_E_1_alpha(self): pass\n"
                        "    def test_AT_999_1_E_10_beta(self): pass\n"
                        "    def test_AT_999_2_1_gamma(self): pass\n"
                        "    def test_AT_999_3_1(self): pass\n", encoding="utf-8")
        collected = collect_nodes([path], tmp)
        syn = "tools/tests/" + "test_synth.py"

        def mk(at, k):
            return [(at, syn, k)]
        cases = [(mk("AT-999-1-E-1", "AT_999_1_E_1"), "非錨定"),
                 (mk("AT-999-2-1", "AT_999_2_2_"), "不等於 AT 底線形"),
                 (mk("AT-999-4-1", "AT_999_4_1_"), "零命中"),
                 (mk("AT-999-1-E-1", "AT_999_1_"), "命中"),
                 (mk("AT-999-3-1", "AT_999_3_1_"), "缺 slug")]
        for ats, why in cases:
            got = anchor_problems(ats, collected)
            self.assertTrue(got and ats[0][0] in got[0], (ats, got))
            self.assertTrue(any(why in p for p in got), (why, got))
        twice = [("AT-999-2-1", syn, "AT_999_2_1_"), ("AT-999-2-2", syn, "AT_999_2_1_")]
        self.assertTrue(any("同時被" in p for p in anchor_problems(twice, collected)))
        ok = [("AT-999-1-E-1", syn, "AT_999_1_E_1_"), ("AT-999-1-E-10", syn, "AT_999_1_E_10_"),
              ("AT-999-2-1", syn, "AT_999_2_1_")]
        self.assertEqual(anchor_problems(ok, collected), [])


if __name__ == "__main__":
    unittest.main()
