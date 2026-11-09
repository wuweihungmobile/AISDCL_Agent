# 受測面：tools/lib/selfimproving/fourqparse.py（程式碼鎖，非散文）
"""SelfImproving P5 四問答案檔、`fourq` 動詞與事件（TCS-SelfImproving-P5 FM 組；AT-441、AT-442）。

受測：`tools/lib/selfimproving/fourqparse.py`（判準）、`fourq.py`（動詞）、`evspec.py`（欄位表）。
所有測試在暫存 repo 與暫存家目錄內跑，不碰真帳本、外網、真 `claude`。
"""

from __future__ import annotations

import ast
import contextlib
import json
import re
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p5_fixtures as f5
from _selfimproving_p5_fixtures import P5TestCase, answers

from lib.selfimproving import events as si_events
from lib.selfimproving import evspec, fourq, fourqparse

SOP = f5.SOP_REL
NONZERO = f5.Q1_LINE.replace("＝零命中｜查詢：「漸進", "＝命中不涵蓋：x｜查詢：「漸進")


def setUpModule() -> None:
    fx.setup("si_p5m_")


def tearDownModule() -> None:
    fx.teardown()


def codes(probs) -> set[str]:
    return {c for c, _ in probs}


class ParseCase(P5TestCase):
    """受測：`tools/lib/selfimproving/fourqparse.py`（validate 的共用夾具）。"""

    def V(self, R: Path, text: str, **kw):
        kw.setdefault("events", fx.EV(R))
        probs, items, hits = fourqparse.validate(text.encode("utf-8"), R, run=f5.RUN, **kw)
        return probs, items, hits

    def base(self) -> Path:
        R = f5.p5_base()
        fx2.open_run(R)  # RUN-SI-001
        return R

    def lines(self, **mods) -> list[str]:
        return answers(**mods).split("\n")


class TestSopRole(unittest.TestCase):
    """受測：`tools/tests/_selfimproving_p5_fixtures.py::sop_p5_problems`（SOP 角色節判準）。"""

    def test_AT_441_1_1_real_sop_section_passes(self):
        text = fx.REAL_SOP.read_text(encoding="utf-8")
        self.assertEqual([p for p in f5.sop_p5_problems(text) if "RESEARCHER" not in p], [])

    def test_AT_441_1_E_1_variants_each_report_their_code(self):
        text = fx.REAL_SOP.read_text(encoding="utf-8")
        for tok in f5.REQ:
            self.assertIn(f"SOP-P5-REQ-MISSING:{tok}", f5.sop_p5_problems(text.replace(tok, "x")))
        q3 = fourqparse.QS[2]
        self.assertIn("SOP-P5-QUESTION-MISSING:3",
                      f5.sop_p5_problems(text.replace(q3, q3[:-2] + "嗎")))
        a = text.index("```text\n# 四問審視")
        self.assertIn("SOP-P5-SECTION-MISSING", f5.sop_p5_problems(
            "## 研究者\n\n```text\n## 四問審視者\n```\n## 運轉配方\n" + text[a:a + 10]))
        self.assertIn("SOP-P5-SECTION-MISSING",
                      f5.sop_p5_problems(text.replace("## 四問審視者", "## 四問審查者")))


class TestFormat(ParseCase):
    """受測：`tools/lib/selfimproving/fourqparse.py`（答案檔格式、項數、管線、位元組界）。"""

    def test_AT_441_2_1_legal_file_parses_and_counts(self):
        R = self.base()
        probs, items, hits = self.V(R, answers())
        self.assertEqual(probs, [])
        c = fourqparse.counts(items)
        self.assertEqual((c["q1"], c["q2"], c["q3"], c["q4"], c["gaps"]), (1, 2, 1, 1, 1))
        self.assertEqual(hits, [0, 0])

    def test_AT_441_2_E_1_format_variants_each_fail(self):
        R, good = self.base(), answers()
        t = fourqparse.TITLES
        variants = {
            "no-head": good.split("\n", 1)[1],
            "title-missing": good.replace(t[3], ""),
            "title-swapped": answers(titles=[t[1], t[0], t[2], t[3]]),
            "title-extra": good + "## Q5 多\n",
            "title-word": good.replace("## Q3 ", "## Q3　"),
            "num-gap": good.replace("Q3-1｜", "Q3-2｜"),
            "f0-and-f1": good.replace("- Q2-F1｜", "- Q2-F0｜免掃：x\n- Q2-F1｜"),
            "no-domain": good.replace("領域：SRE｜", ""),
            "domain-long": good.replace("領域：SRE", "領域：" + "長" * 21),
            "q4-extra-label": good.replace("收斂：", "備註：x｜收斂："),
        }
        for name, text in variants.items():
            probs, _, _ = self.V(R, text)
            self.assertIn("FOURQ-FORMAT", codes(probs), name)

    def test_AT_441_2_E_2_pipe_control_and_byte_limits(self):
        R, good = self.base(), answers()
        bad = good.replace("機制：漸進放量比對錯誤率", "機制：漸進放量比對錯誤率|x")
        self.assertIn("FOURQ-PIPE", codes(self.V(R, bad)[0]))
        g = good.replace("更新頻率：每週", "更新頻率：每週|x")
        self.assertIn("FOURQ-PIPE", codes(self.V(R, g)[0]))
        ok = good.replace("`git grep -c x`", "`git grep -c x | wc`").replace(
            "工具：playbooks/demo.yaml", "工具：playbooks/demo.yaml")
        self.assertNotIn("FOURQ-PIPE", codes(self.V(R, ok)[0]))
        for ch in ("\x07", "\x85"):
            self.assertIn("FOURQ-FORMAT", codes(self.V(R, good.replace("SRE", "S" + ch))[0]))
        self.assertIn("FOURQ-LINE", codes(self.V(R, good.replace("每週", "週" * 400))[0]))
        big = good + "\n".join("" for _ in range(1)) + ("x" * 700 + "\n") * 40
        self.assertIn("FOURQ-FILE-BYTES", codes(self.V(R, big)[0]))
        raw = good.encode("utf-8") + b"\xff"
        probs, _, _ = fourqparse.validate(raw, R, run=f5.RUN, events=fx.EV(R))
        self.assertIn("FOURQ-FORMAT", codes(probs))

    def test_AT_441_2_E_3_items_cap_by_band(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        many = answers(run, q3=[f5.Q3_LINE.replace("Q3-1", f"Q3-{i}") for i in (1, 2, 3, 4)])
        self.assertEqual([c for c, _ in fourqparse.validate(many.encode(), R, run=run,
                                                            items_max=3)[0]
                          if c == "FOURQ-ITEMS-OVER"], ["FOURQ-ITEMS-OVER"])
        self.assertNotIn("FOURQ-ITEMS-OVER", codes(fourqparse.validate(
            many.encode(), R, run=run, items_max=4)[0]))
        two = answers(run, q3=[f5.Q3_LINE, f5.Q3_LINE.replace("Q3-1", "Q3-2")])
        for band in ("notice", "converge", "stop"):  # 真入口：非 free 帶＝降載上限 1
            with f5.free_band(band):
                rc, out, _ = self.fq(R, two, run=run)
            self.rejected(rc, out, {"FOURQ-ITEMS-OVER"}, band)
        with f5.free_band("free"):  # 同一檔在 free 帶＝上限 3，入帳成功
            rc, out, err = self.fq(R, two, run=run)
        self.assertEqual(rc, 0, out + err)


class TestCoordsAndQueries(ParseCase):
    """受測：`tools/lib/selfimproving/fourqparse.py`（座標、查詢重放、全文引用）。"""

    def test_AT_441_3_1_coordinate_forms_and_query_states_pass(self):
        R = self.base()
        defs = fx.def_id(1)
        forms = [f"{SOP}:1", defs, fx.obs_id(1), f"sid {fx.UUID} line 3", "src=src-old 片段"]
        for coord in forms:
            text = answers(q1=[f5.Q1_LINE.replace(f"{SOP}:1", coord)])
            self.assertEqual(self.V(R, text)[0], [], coord)

    def test_AT_441_3_E_1_bad_coordinates_tools_and_urls(self):
        R, good = self.base(), answers()
        for coord, code in ((f"{SOP}:9999", "FOURQ-COORD-MISSING"), ("無", "FOURQ-COORD-MISSING"),
                            (fx.def_id(99), "FOURQ-COORD-MISSING"),
                            ("src=nope 片段", "FOURQ-SRC-UNKNOWN")):
            text = answers(q1=[f5.Q1_LINE.replace(f"{SOP}:1", coord)])
            self.assertIn(code, codes(self.V(R, text)[0]), coord)
        for a, b in (("playbooks/demo.yaml", "tools/nope.py"),
                     ("playbooks/demo.yaml", "外部：某工具")):
            self.assertIn("FOURQ-TOOL-UNKNOWN", codes(self.V(R, good.replace(a, b))[0]))
        for a, b in (("https://example.org/feed", "http://example.org/feed"),
                     ("https://example.org/feed", "https://u@example.org/feed"),
                     ("分級：T1", "分級：T3")):
            self.assertIn("FOURQ-FORMAT", codes(self.V(R, good.replace(a, b))[0]), b)
        self.escape_variants(R)

    def escape_variants(self, R: Path) -> None:
        """座標與工具路徑的逃逸：字面判定先於任何檔案系統存取（SCG-4 P2-1）。"""
        bad = ("../x.md:1", "C:\\Windows\\win.ini:1", "\\\\localhost\\c$\\x:1", "//host/share/x:1",
               "/etc/passwd:1")
        marks = ("win.ini", "localhost", "/host/share", "etc/passwd", "..")

        def guard(orig):
            def wrapped(self, *a, **k):
                text = str(self).replace("\\", "/")
                if any(m in text for m in marks):
                    raise AssertionError(f"touched {text}")
                return orig(self, *a, **k)
            return wrapped
        names = ("exists", "is_file", "is_dir", "read_bytes", "read_text", "open", "resolve",
                 "stat")
        with contextlib.ExitStack() as stack:
            for n in names:
                stack.enter_context(mock.patch.object(Path, n, guard(getattr(Path, n))))
            for coord in bad:
                text = answers(q1=[f5.Q1_LINE.replace(f"{SOP}:1", coord)])
                self.assertIn("FOURQ-COORD-ESCAPE", codes(self.V(R, text)[0]), coord)
                tool = coord.rsplit(":", 1)[0]
                text = answers(q3=[f5.Q3_LINE.replace("playbooks/demo.yaml", tool)])
                self.assertIn("FOURQ-COORD-ESCAPE", codes(self.V(R, text)[0]), tool)
            ctl = answers(q1=[f5.Q1_LINE.replace(f"{SOP}:1", "a\x07b:1")])
            self.assertIn("FOURQ-COORD-ESCAPE", codes(self.V(R, ctl)[0]))
    def test_AT_441_3_2_corpus_is_fixed_and_replay_is_zero_nonzero(self):
        R = self.base()
        fx.put(R, "docs/06_quality/SelfImproving_Observation_Ledger.md.bak", "金絲雀回滾演練\n")
        fx.put(R, "docs/06_quality/Other_notes.md", "金絲雀回滾演練\n")
        self.assertEqual(self.V(R, answers())[0], [])
        self.assertTrue(all("bak" not in f and "Other" not in f
                            for f in fourqparse.corpus_files(R)))
        hit = answers(q1=[NONZERO])
        self.assertIn("FOURQ-QUERY-MISMATCH", codes(self.V(R, hit)[0]))
        fx.put(R, SOP, f5.MINI_SOP.replace("\n", "\r\n") + "金絲雀回滾演練\r\n")
        text = answers(q1=[NONZERO])
        probs, _, hits = self.V(R, text)
        self.assertNotIn("FOURQ-QUERY-MISMATCH", codes([p for p in probs if "漸進" not in p[1]]))
        self.assertEqual(hits[0], 1)
        rc, out, _ = self.M(R, "fourq", "--corpus")
        self.assertEqual((rc, out.split()), (0, fourqparse.corpus_files(R)))

    def test_AT_441_3_E_2_query_shape_binding_and_empty_proof(self):
        R = self.base()
        one = answers(q1=[f5.Q1_LINE.split("｜查詢：「漸進")[0]])
        self.assertIn("FOURQ-QUERY-DUP", codes(self.V(R, one)[0]))
        same = f5.Q1_LINE.replace("「漸進放量比對」", "「金絲雀回滾演練」")
        self.assertIn("FOURQ-QUERY-DUP", codes(self.V(R, answers(q1=[same]))[0]))
        short = f5.Q1_LINE.replace("「漸進放量比對」", "「漸」")
        self.assertIn("FOURQ-QUERY-TOO-SHORT", codes(self.V(R, answers(q1=[short]))[0]))
        three = f5.Q1_LINE.replace("錯誤率｜座標", "錯誤率abc｜座標")
        three = three.replace("「漸進放量比對」", "「abc」")
        self.assertIn("FOURQ-QUERY-TOO-SHORT", codes(self.V(R, answers(q1=[three]))[0]))
        long_ = "做法：" + "漸進放量比對錯誤率的長查詢"
        for q, code in (("漸進放量比對錯誤率", "FOURQ-QUERY-TOO-LONG"),
                        ("漸進放量比對錯", None), ("漸進放量比對錯誤", None)):
            line = (f5.Q1_LINE.replace("機制：漸進放量比對錯誤率", "機制：漸進放量比對錯誤率的長")
                    .replace("「漸進放量比對」", f"「{q}」"))
            got = codes(self.V(R, answers(q1=[line]))[0])
            self.assertEqual("FOURQ-QUERY-TOO-LONG" in got, code == "FOURQ-QUERY-TOO-LONG", q)
        self.assertIsNotNone(long_)
        unbound = f5.Q1_LINE.replace("「漸進放量比對」", "「完全無關的字串」")
        self.assertIn("FOURQ-QUERY-UNBOUND", codes(self.V(R, answers(q1=[unbound]))[0]))
        zero = [f5.Q1X_LINE.format(n=1)]
        self.assertIn("FOURQ-Q1-EMPTY-UNJUSTIFIED", codes(self.V(R, answers(q1=zero))[0]))
        two = [f5.Q1X_LINE.format(n=1), f5.Q1X_LINE.format(n=2)]
        self.assertEqual(self.V(R, answers(q1=two))[0], [])
        nohit = [f5.Q1X_LINE.format(n=1), f5.Q1X_LINE.format(n=2).replace("迷你 SOP", "完全不存在")]
        self.assertIn("FOURQ-Q1-EMPTY-UNJUSTIFIED", codes(self.V(R, answers(q1=nohit))[0]))
        wrongline = [f5.Q1X_LINE.format(n=1), f5.Q1X_LINE.format(n=2).replace(":1", ":3")]
        self.assertIn("FOURQ-Q1-EMPTY-UNJUSTIFIED", codes(self.V(R, answers(q1=wrongline))[0]))
        (R / SOP).unlink()
        self.assertIn("FOURQ-CORPUS-UNAVAILABLE", codes(self.V(R, answers())[0]))

    def test_AT_441_3_3_existing_refs_pass(self):
        R = self.base()
        text = answers(q2=[f5.Q2F_LINE.replace("片段一", f"片段 {fx.obs_id(1)} {f5.RUN}"),
                           f5.Q2G_LINE])
        self.assertEqual(self.V(R, text)[0], [])

    def test_AT_441_3_E_3_dangling_refs_are_real_failures(self):
        R = self.base()
        ghost = fx.obs_id(777)
        for tok in (ghost, fx.pid(777), fx.rid(777), "MEA" + "-SI-001"):
            text = answers(q2=[f5.Q2F_LINE.replace("片段一", f"片段 {tok}"), f5.Q2G_LINE])
            probs = self.V(R, text)[0]
            self.assertIn("FOURQ-REF-DANGLING", codes(probs), tok)
            self.assertTrue(any(tok in d for c, d in probs if c == "FOURQ-REF-DANGLING"))
        row = fx.render_ledger([[ghost] + ["x"] * 8])
        self.assertTrue(row)
        fx.put(R, "docs/06_quality/SelfImproving_Proposals/_fourq/" + f5.RUN + ".md",
               answers(q2=[f5.Q2F_LINE.replace("片段一", f"片段 {ghost}"), f5.Q2G_LINE]))
        fx.commit_all(R, "ghost")
        res = self.check(R)
        self.assertEqual(self.S(res, "ref.obs"), "FAIL")


class TestQ4(ParseCase):
    """受測：`tools/lib/selfimproving/fourqparse.py`（Q4 子欄、禁字、迴圈層快照）。"""

    def test_AT_441_4_1_q4_legal_forms(self):
        R = self.base()
        for cat, sym in (("M4", "`git grep -c x | wc -l`"), ("M5", f"{SOP}:1"),
                         ("症狀：某具名症狀", "`git log -1`")):
            line = f5.Q4_LINE.replace("指標類別：M1", f"指標類別：{cat}").replace(
                "`git grep -c x`", sym)
            self.assertEqual(self.V(R, answers(q4=[line]))[0], [], cat)

    def test_AT_441_4_E_1_leak_and_goodhart_terms(self):
        R = self.base()
        from lib.selfimproving import params as si_params

        key = sorted(si_params.PARAM_SPECS)[0]
        for bad in ("n=5", "30%", "基線", "門檻", "閾值", key, "params.json", "W_MIN"):
            line = f5.Q4_LINE.replace("演練後症狀仍再現", f"演練後 {bad} 仍再現")
            self.assertIn("FOURQ-Q4-LEAK", codes(self.V(R, answers(q4=[line]))[0]), bad)
        for bad in ("觀察筆數上升", "提案筆數", "採納率", "自評", "信心"):
            line = f5.Q4_LINE.replace("演練後症狀仍再現", f"以{bad}為準")
            self.assertIn("FOURQ-Q4-LEAK", codes(self.V(R, answers(q4=[line]))[0]), bad)
        ok = f5.Q4_LINE.replace("演練後症狀仍再現", "不以觀察筆數為成效；並非以採納率判斷")
        self.assertEqual(self.V(R, answers(q4=[ok]))[0], [])
        single = f5.Q4_LINE.replace("演練後症狀仍再現", "非觀察筆數為準")
        self.assertIn("FOURQ-Q4-LEAK", codes(self.V(R, answers(q4=[single]))[0]))
        sneaky = f5.Q4_LINE.replace("演練後症狀仍再現", "非常看重觀察筆數")
        self.assertIn("FOURQ-Q4-LEAK", codes(self.V(R, answers(q4=[sneaky]))[0]))
        inside = f5.Q4_LINE.replace("`git grep -c x`", "`git grep -c 基線 n=5`")
        self.assertEqual(self.V(R, answers(q4=[inside]))[0], [])

    def test_AT_441_4_2_loop_snapshot_is_read_only_and_ne_is_honest(self):
        R = self.base()
        before = (R / fx.EVL).read_bytes()
        out_json = self.MJ_fq(R)
        after = fx.EV(R)
        self.assertEqual([e["kind"] for e in after if e["kind"].startswith("mea.")], [])
        self.assertTrue(len(before) < len((R / fx.EVL).read_bytes()))
        ev = [e for e in after if e["kind"] == "fourq.review"][0]
        from lib.selfimproving import mea, meastat
        from lib.selfimproving.git import Git

        prm = json.loads(fx.read(R, fx.PARAMS))
        before_ev = after[:-1]
        git = Git(R)
        s = meastat.metrics(R, git, mea.build_ctx(R, git, prm, before_ev), carrier=True)["success"]

        def one(name, it):  # 測試自己的格式化：與被測函式獨立書寫
            if it["status"] != "read":
                return f"{name}=NE({str(it.get('reason', ''))[:24]})"
            n = it.get("n")
            return f"{name}=read({it['value']:.4g}" + ("" if n is None else f",n={n}") + ")"
        want = ";".join([one("M1", s["m1"]), one("M4", s["m4"]), one("M5a", s["m5"]["main"]),
                         one("M5b", s["m5"]["all"])])
        self.assertEqual(ev["loop"], want)
        self.assertTrue(all(k in ev["loop"] for k in ("M1=", "M4=", "M5a=", "M5b=")))
        for line in ev["loop"].split(";"):
            self.assertIn(line, out_json)
        fake = {"success": {
            "m1": {"status": "read", "value": 0.1, "n": 3}, "m4": {"status": "read", "value": 2},
            "m5": {"main": {"status": "read", "value": 0.25, "n": 4},
                   "all": {"status": "read", "value": 0.5, "n": 8}}}}
        with mock.patch.object(meastat, "metrics", return_value=fake):
            snap = fourqparse.loop_snapshot(R, prm, before_ev)
        self.assertEqual(fourqparse.loop_text(snap),
                         "M1=read(0.1,n=3);M4=read(2);M5a=read(0.25,n=4);M5b=read(0.5,n=8)")
        none = fourqparse.loop_snapshot(R, prm, None)
        self.assertTrue(all(v["reason"] == "carrier-not-established" for v in none.values()))
        bad = {k: v for k, v in prm.items() if k != "w_min"}
        got = fourqparse.loop_snapshot(R, bad, after)
        self.assertTrue(all(v == {"status": "NOT-EVALUABLE", "reason": "params-invalid"}
                            for v in got.values()))
        with mock.patch.dict("os.environ", {"AUTOSDD_UNATTENDED": "1",
                                            "AUTOSDD_SI_PATROL_RUN": "x"}):
            snap = fourqparse.loop_snapshot(R, prm, after)
        self.assertEqual(set(snap), {"m1", "m4", "m5a", "m5b"})

    def MJ_fq(self, R: Path) -> str:
        rc, out, err = self.fq(R, answers())
        self.assertEqual(rc, 0, out + err)
        return out

    def test_AT_441_4_E_2_no_loop_layer_in_answers_and_no_mismatch_code(self):
        R = self.base()
        for text in (answers() + "## Q4-L 迴圈層\n", answers(q4=[f5.Q4_LINE, "M1：read"])):
            self.assertTrue(self.V(R, text)[0])
        src = Path(fourqparse.__file__).read_text(encoding="utf-8")
        self.assertNotIn("FOURQ-LOOP-MISMATCH", src)
        self.assertNotIn("FOURQ-LOOP-MISMATCH", Path(fourq.__file__).read_text(encoding="utf-8"))


class TestVerb(P5TestCase):
    """受測：`tools/lib/selfimproving/fourq.py`（入帳、免審、落地、事件欄位表）。"""

    def test_AT_442_1_1_review_appends_one_event_and_lands_file(self):
        R = f5.p5_base()
        text = answers(fx2.open_run(R))
        rc, out, err = self.fq(R, text)
        self.assertEqual(rc, 0, out + err)
        ev = [e for e in fx.EV(R) if e["kind"] == "fourq.review"]
        self.assertEqual(len(ev), 1)
        landed = (R / ev[0]["path"]).read_bytes()
        self.assertEqual(landed, text.encode("utf-8"))
        self.assertEqual(ev[0]["sha256"], fx.sha(landed))
        self.assertEqual([ev[0][k] for k in ("q1", "q2", "q3", "q4", "gaps")], [1, 2, 1, 1, 1])
        self.assertEqual(ev[0]["qhits"], "0,0")
        self.assertIn("loop", ev[0])
        seqs = [e["seq"] for e in fx.EV(R)]
        self.assertEqual(seqs, list(range(1, len(seqs) + 1)))

    def test_AT_442_1_E_1_refusals_leave_nothing(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        good = answers(run)
        cases = [("--by", "main"), ("--by", "researcher")]
        for flag, val in cases:
            before = self.snap(R)
            rc, out, _ = self.fq(R, good, by=val)
            self.rejected(rc, out, {"FOURQ-BY-RESERVED"})
            self.assertEqual(self.snap(R), before)
        rc, out, err = self.fq(R, good, by="a b")
        self.usage_error(rc, out, err)
        rc, out, err = self.fq(R, b"\xff\xfe", run=run)
        self.usage_error(rc, out, err)
        rc, out, err = self.M(R, "fourq", "--run", run, "--answers-file", str(R / "nope.md"),
                              "--by", "REV")
        self.usage_error(rc, out, err)
        rc, out, _ = self.fq(R, answers(fx.rid(9)), run=fx.rid(9))
        self.rejected(rc, out, {"RUN-NOT-OPEN", "FOURQ-REF-DANGLING"})
        R2 = f5.p5_base()
        fx.append_events(R2, [fx.run_open_ev(2)])
        rc, out, _ = self.fq(R2, answers(fx.rid(2)), run=fx.rid(2))
        self.rejected(rc, out, {"FOURQ-BEFORE-RESEARCH"})
        self.assertEqual(self.fq(R, good)[0], 0)
        rc, out, _ = self.fq(R, good, by="REV2")
        self.rejected(rc, out, {"FOURQ-ALREADY"})

    def test_AT_442_1_E_2_append_failure_leaves_no_file(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        before = (R / fx.EVL).read_bytes()
        prm = json.loads(fx.read(R, fx.PARAMS))
        fx.set_params(R, event_max_bytes=100)
        rc, out, _ = self.fq(R, answers(run))
        self.assertEqual(rc, 1, out)
        self.assertFalse((R / si_events.fourq_path(run)).exists())
        self.assertEqual((R / fx.EVL).read_bytes(), before)
        fx.set_params(R, event_max_bytes=prm["event_max_bytes"])
        fx.put(R, si_events.fourq_path(run), "既有\n")
        rc, out, _ = self.fq(R, answers(run))
        self.rejected(rc, out, {"FOURQ-FILE-EXISTS"})
        self.assertEqual(fx.read(R, si_events.fourq_path(run)), "既有\n")
        self.assertEqual((R / fx.EVL).read_bytes(), before)

    def test_AT_442_1_2_dry_run_matches_real_codes_and_writes_nothing(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        before = self.snap(R)
        rc, out, _ = self.fq(R, answers(run), "--dry-run")
        self.assertEqual(rc, 0, out)
        bad = answers(run).replace("機制：漸進放量比對錯誤率", "機制：漸進放量比對錯誤率|x")
        rc1, out1, _ = self.fq(R, bad, "--dry-run")
        self.assertEqual(self.snap(R), before)
        rc2, out2, _ = self.fq(R, bad)
        self.assertEqual((rc1, rc2), (1, 1))
        self.assertEqual(fx.codes_of(out1), fx.codes_of(out2))
        self.assertEqual(self.snap(R), before)

    def test_AT_442_2_1_skip_by_band_and_helmsman(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        with f5.free_band("notice"):
            rc, out, err = self.M(R, "fourq", "--skip", "--run", run, "--reason", "quota-band",
                                  "--band", "notice", "--note", "額度")
            self.assertEqual(rc, 0, out + err)
        R2 = f5.p5_base()
        run2 = fx2.open_run(R2)
        rc, out, err = self.M(R2, "fourq", "--skip", "--run", run2, "--reason", "helmsman",
                              "--sid", fx.UUID, "--line", "3", "--note", "掌舵者明示")
        self.assertEqual(rc, 0, out + err)
        ev = [e for e in fx.EV(R2) if e["kind"] == "fourq.skip"]
        self.assertEqual((len(ev), ev[0]["by"]), (1, "main"))
        rc, out, _ = self.fq(R2, answers(run2), run=run2)
        self.rejected(rc, out, {"FOURQ-ALREADY"})

    def test_AT_442_2_E_1_skip_refusals(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        argv = ["fourq", "--skip", "--run", run, "--reason", "quota-band", "--note", "x"]
        before = self.snap(R)
        with mock.patch.dict("os.environ", {"AUTOSDD_UNATTENDED": "1",
                                            "AUTOSDD_SI_PATROL_RUN": run}):
            rc, out, _ = self.M(R, *argv, "--band", "notice")
        self.rejected(rc, out, {"FOURQ-SKIP-REFUSED"})
        rc, out, _ = self.M(R, *argv, "--band", "notice")
        self.rejected(rc, out, {"FOURQ-SKIP-BAND-FREE"})
        for extra in (["--band", "free"], [], ["--sid", fx.UUID]):
            rc, out, err = self.M(R, *argv[:-2], "--note", "x", *extra, "--reason", "quota-band")
            self.assertEqual(rc, 3, extra)
        for sid, line, note in (("abc", "1", "x"), (fx.UUID, "0", "x"), (fx.UUID, "1", ""),
                                (fx.UUID, "1", "x" * 121)):
            rc, *_ = self.M(R, "fourq", "--skip", "--run", run, "--reason", "helmsman", "--sid",
                            sid, "--line", line, "--note", note)
            self.assertEqual(rc, 3, (sid, line, len(note)))
        rc, *_ = self.M(R, "fourq", "--skip", "--run", run, "--reason", "offline", "--note", "x")
        self.assertEqual(rc, 3)
        self.assertEqual(self.snap(R), before)

    def test_AT_442_3_1_landed_file_is_invisible_to_scans(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        self.assertEqual(self.fq(R, answers(run), run=run)[0], 0)
        res = self.check(R)
        self.assertNotIn("PROP-DIR-ORPHAN", {c for _, c in self.F(res, "ref.carrier_families")})
        self.assertEqual(self.S(res, "events.prop_files"), "PASS")
        rc, out, _ = self.M(R, "export", "--kind", "proposals", "--json")
        self.assertNotIn("_fourq", out)
        from lib.selfimproving import sched

        self.assertEqual([p for p in sched.dirty_paths(R) if "_fourq" in p], [])

    def test_AT_442_3_E_1_orphan_dir_and_edited_file(self):
        R = f5.p5_base()
        run = fx2.open_run(R)
        self.assertEqual(self.fq(R, answers(run), run=run)[0], 0)
        fx.put(R, f"{fx.PROPS_REL}/{fx.pid(555)}/r1.md", "x\n")
        res = self.check(R)
        self.assertIn(fx.pid(555), {s for s, c in self.F(res, "ref.carrier_families")
                                    if c == "PROP-DIR-ORPHAN"} | {
            s for i in res["items"] for f in i["findings"]
            for s in [f["subject"]] if f["code"] == "PROP-DIR-ORPHAN"})
        path = R / si_events.fourq_path(run)
        path.write_bytes(path.read_bytes().replace(b"SRE", b"SRX"))
        res = self.check(R)
        self.assertIn("FOURQ-SHA-MISMATCH", {c for _, c in self.F(res, "events.research")})

    def test_AT_442_4_1_kinds_and_events_validate(self):
        self.assertEqual(len(si_events.KINDS), 25)
        for name in ("validate", "sound", "read_lines", "KINDS", "SKIP_REASONS", "LEDGER_REL",
                     "PROPOSALS_REL", "OBS_ID_RE", "RUN_RE", "PROP_RE", "DKINDS", "valid_by"):
            self.assertIs(getattr(si_events, name), getattr(evspec, name, getattr(
                si_events, name)))
        rev = fx.ev("fourq.review", "REV", seq=1, t="2026-11-10T00:00:00+00:00", run=f5.RUN,
                    path=si_events.fourq_path(f5.RUN), sha256=fx.H(1), q1=1, q2=2, q3=1, q4=1,
                    gaps=1, qhits="0,0", loop="M1=NE(x)")
        obj = {"seq": 1, "t": "2026-11-10T00:00:00+00:00", **rev}
        self.assertEqual(si_events.validate(obj), [])
        sk = {"seq": 2, "t": obj["t"], "kind": "fourq.skip", "by": "main", "run": f5.RUN,
              "reason": "quota-band", "note": "x", "band": "notice"}
        self.assertEqual(si_events.validate(sk), [])
        evs = [obj, {**obj, "seq": 2, "run": fx.rid(2), "path": si_events.fourq_path(fx.rid(2))}]
        got = fourqparse.fourq_events(evs)
        self.assertEqual(got[f5.RUN][:2], ("fourq.review", 1))

    def test_AT_442_4_E_1_event_shape_violations(self):
        base = {"seq": 1, "t": "2026-11-10T00:00:00+00:00", "kind": "fourq.review", "by": "REV",
                "run": f5.RUN, "path": si_events.fourq_path(f5.RUN), "sha256": fx.H(1), "q1": 1,
                "q2": 2, "q3": 1, "q4": 1, "gaps": 1, "qhits": "0,0", "loop": "M1=NE(x)"}
        bad = [{k: v for k, v in base.items() if k != "path"}, {**base, "path": "x/y.md"},
               {**base, "sha256": "abc"}, {**base, "q1": -1}, {**base, "q1": True},
               {**base, "gaps": 3}, {**base, "loop": 5}, {**base, "qhits": "é"},
               {**base, "loop": "M" * 257}, {**base, "qhits": "1," * 70 + "1"},
               {**base, "by": "main"}, {**base, "extra": 1}]
        for obj in bad:
            self.assertTrue(si_events.validate(obj), obj)
        skip = {"seq": 1, "t": base["t"], "kind": "fourq.skip", "by": "main", "run": f5.RUN,
                "reason": "quota-band", "note": "x", "band": "notice"}
        for obj in ({**skip, "by": "REV"}, {**skip, "reason": "offline"}, {**skip, "k": 1}):
            self.assertTrue(si_events.validate(obj), obj)
        self.assertEqual(si_events.sound([base, bad[1]]), [base])
        self.assertTrue(re.match(r"^[0-9a-f]{8}$", "0a1b2c3d"))
        self.assertIsNotNone(ast)


if __name__ == "__main__":
    unittest.main()
