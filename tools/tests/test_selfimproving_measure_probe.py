# 受測面：tools/probe/selfimproving_measure.py（程式碼鎖，非散文）
"""SelfImproving P3 量測腳本（C11）的驗收（TCS-SelfImproving-P3 §2 C 組；12 個 AT）。

受測：`tools/probe/selfimproving_measure.py`（M1～M5、資訊欄、反證條件、判準指紋、純度與不接閘門）與
其唯讀依賴 `tools/lib/selfimproving/meastat.py`、`mea.py`、`defs.py`（DEF 解析差分）。
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p3_fixtures as f3
from _selfimproving_p3_fixtures import D3, evl, win

from lib.selfimproving import defs as si_defs
from lib.selfimproving import params as si_params

PROBE = fx.ROOT / "tools" / "probe" / "selfimproving_measure.py"
ALLOWED_RO = {"mea", "meastat", "defs", "params", "events", "fold", "refs", "git", "rows",
              "ledger"}
_NET = {"socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp", "ftplib", "smtplib"}
_MODEL = {"anthropic", "openai", "claude_agent_sdk"}
_SECRET = re.compile(r"KEY|TOKEN|SECRET")
PROTOCOL = "docs/06_quality/SelfImproving_Protocol"


def setUpModule():
    fx.setup("si_p3p_")


def tearDownModule():
    fx.teardown()


def fp_ref(parts: dict) -> str:
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _env_names(tree: ast.AST) -> list[str]:
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Subscript) and ast.unparse(n.value) == "os.environ":
            out.append(ast.unparse(n.slice))
        elif isinstance(n, ast.Call) and ast.unparse(n.func) in ("os.environ.get", "os.getenv"):
            out.append(ast.unparse(n.args[0]) if n.args else "")
    return [x.strip("'\"") for x in out]


def _import_targets(node: ast.ImportFrom) -> list[str] | None:
    mod = node.module or ""
    if node.level == 0 and not mod.startswith("lib.selfimproving"):
        return None
    rest = mod[len("lib.selfimproving"):].lstrip(".") if node.level == 0 else mod
    return [a.name for a in node.names] if not rest else [rest.split(".")[0]]


def probe_purity_problems(src: str) -> list[str]:
    """探針原始碼的純度問題碼（AST）：子行程、網路、模型客戶端、寫入原語、環境變數、非 ro 匯入。"""
    out: list[str] = []
    tree = ast.parse(src)
    for node in ast.walk(tree):
        roots: list[str] = []
        if isinstance(node, ast.Import):
            roots = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            roots = [(node.module or "").split(".")[0]] if node.level == 0 else []
            for t in _import_targets(node) or []:
                if t not in ALLOWED_RO:
                    out.append("P-NON-RO-IMPORT")
        out += ["P-SUBPROCESS" for r in roots if r == "subprocess"]
        out += ["P-NET" for r in roots if r in _NET]
        out += ["P-MODEL" for r in roots if r in _MODEL]
        if isinstance(node, ast.Call):
            name = ast.unparse(node.func)
            mode = next((ast.unparse(k.value) for k in node.keywords if k.arg == "mode"), None)
            if mode is None and len(node.args) > 1:
                mode = ast.unparse(node.args[1])
            if name == "open" and mode and re.search(r"[wax+]", mode):
                out.append("P-WRITE")
            if name.endswith((".write_text", ".write_bytes")):
                out.append("P-WRITE")
    out += ["P-ENV" for n in _env_names(tree) if n.startswith("AUTOSDD_") or _SECRET.search(n)]
    return out


def load_probe():
    spec = importlib.util.spec_from_file_location("si_probe_measure", PROBE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ProbeTestCase(f3.P3TestCase):
    def scenario(self, build):
        self.new_home()
        R = f3.p3_base()
        s = build(R)
        fx.commit_all(R, "scenario")
        return R, s

    def run_probe(self, R, *extra, cwd=None):
        repo = ["--repo", str(R)] if R else []
        cp = subprocess.run([sys.executable, str(PROBE), *extra, *repo],
                            capture_output=True, check=False, cwd=cwd)
        return cp.returncode, cp.stdout, cp.stderr

    def report(self, R):
        rc, out, err = self.run_probe(R, "--json")
        self.assertEqual((rc, err), (0, b""), err)
        return json.loads(out.decode("utf-8"))

    def text(self, R):
        rc, out, err = self.run_probe(R)
        self.assertEqual((rc, err), (0, b""), err)
        return out.decode("utf-8")

    def rows(self, rep):
        return {r["prop"]: r for r in rep["success"]["m1"]["per_prop"]}


class TestM1AndFalsification(ProbeTestCase):
    def test_AT_322_1_1_m1_per_prop(self):
        R, s = self.scenario(f3.s_probe_a)
        rep = self.report(R)
        m1 = rep["success"]["m1"]
        self.assertEqual((m1["status"], m1["n"], m1["recurred"]), ("read", 3, 1))
        self.assertLess(abs(m1["value"] - 1 / 3), 1e-9)
        rows = self.rows(rep)
        p = s["props"]
        self.assertEqual(len(rows), 8)
        self.assertEqual([k for k, r in rows.items() if r["evaluable"]], [p[0], p[1], p[6]])
        self.assertEqual([rows[p[i]]["reason"] for i in (2, 3, 4, 5, 7)],
                         ["BASELINE-EVENTS-BELOW-W-EVT", "BASELINE-ROWS-BELOW-W-MIN",
                          "WINDOW-PENDING", "ROLLED-BACK-NO-RECURRENCE", "WINDOW-OPEN"])
        self.assertEqual((rows[p[0]]["events"], rows[p[0]]["opp_n"]), (2, 5))
        fal = rep["falsification"]
        self.assertEqual((fal["falsified"], fal["falsified_keys"]), (False, []))
        text = self.text(R)
        head, tail = text.split("== 資訊欄 ==")
        self.assertIn("== 成功指標 ==", head)
        self.assertIn("n=3", head)
        for code in ("BASELINE-EVENTS-BELOW-W-EVT", "WINDOW-PENDING", "WINDOW-OPEN"):
            self.assertIn(code, head)

    def test_AT_322_1_2_m4_m5_and_information_fields(self):
        def build(R):
            s = f3.s_probe_a(R)
            f3.s_m23(R)
            s.update(f3.s_cooldown(R))
            return s

        R, s = self.scenario(build)
        rep = self.report(R)
        m4 = rep["success"]["m4"]
        self.assertEqual((m4["status"], m4["value"], len(m4["drafts"])), ("read", 1, 1))
        self.draft_ok(R, "obs-draft:\n" + m4["drafts"][0])
        m5 = rep["success"]["m5"]
        self.assertEqual(list(m5), ["main", "all"])
        for k in m5:
            self.assertEqual(list(m5[k]), ["status", "value", "n"])
        self.assertEqual((m5["main"]["value"], m5["main"]["n"]), (0.0, 5))
        self.assertLess(abs(m5["all"]["value"] - 1 / 6), 1e-9)
        self.assertEqual(m5["all"]["n"], 6)
        info = rep["info"]
        ledger = fx.read(R, f3.LEDGER)
        self.assertEqual(info["obs_rows"], len(re.findall(r"(?m)^\| OBS-SI-\d+ \|", ledger)))
        self.assertEqual((info["proposals"], info["closed_by_decision"], info["unverified_ack"]),
                         (10, 1, 1))
        dec = info["decisions"]
        self.assertEqual((dec["approve"], dec["promote"], dec["rollback"], dec["reject"]),
                         (8, 8, 1, 1))
        self.assertEqual((info["m2"]["value"], info["m2"]["n"], info["m2"]["excluded"]), (5, 5, 1))
        for k in ("m3", "global_m1"):
            self.assertEqual((info[k]["status"], info[k]["reason"]),
                             ("NOT-EVALUABLE", "sample-below-w-min"))
        self.assertFalse({"proposals", "m2", "m3", "obs_rows"} & set(rep["success"]))

    def test_AT_322_1_E_1_m1_not_evaluable_rules(self):
        def a(R):
            s = f3.s_probe_a(R)
            p9 = f3.promoted(R, target=f"{D3}/p9.md", sources=[fx.obs_id(2)])
            f3.mea_chain(R, p9, "clean", ev=0, opp=5)
            p10 = f3.promoted(R, target=f"{D3}/p10.md", sources=[fx.obs_id(2)])
            return {**s, "p9": p9, "p10": p10}

        def b(R):
            s = a(R)
            fx.set_params(R, migration_base_sha=None)
            return s

        def c(R):
            p = f3.promoted(R, target=f"{D3}/c1.md", sources=[fx.obs_id(5)])
            f3.mea_chain(R, p, "clean", ev=1)
            return p

        Ra, sa = self.scenario(a)
        rep_a = self.report(Ra)
        rows = self.rows(rep_a)
        self.assertEqual(rows[sa["p9"]]["reason"], "BASELINE-EVENTS-BELOW-W-EVT")
        self.assertEqual(rows[sa["p10"]]["reason"], "NO-BASELINE")
        Rb, _ = self.scenario(b)
        rep_b = self.report(Rb)
        self.assertEqual(json.dumps(rep_b["success"]["m1"]), json.dumps(rep_a["success"]["m1"]))
        self.assertEqual(rep_b["info"]["global_m1"]["reason"], "anchor-unavailable")
        Rc, _ = self.scenario(c)
        m1 = self.report(Rc)["success"]["m1"]
        self.assertEqual((m1["status"], m1["reason"], m1["n"]), ("NOT-EVALUABLE",
                                                                  "no-evaluable-window", 0))
        self.assertNotIn("value", m1)
        text = self.text(Rc)
        self.assertIn("NOT-EVALUABLE（no-evaluable-window）", text)
        self.assertNotRegex(text, r"(?m)^M1: 0")

    def test_AT_322_1_E_2_m5_not_evaluable_partitions_and_late_rollback(self):
        def head(n):
            return lambda R: f3.s_probe_a(R, count=n)

        def b(R):
            s = f3.s_probe_a(R)
            p9 = f3.promoted(R, target=f"{D3}/p9.md", sources=[fx.obs_id(2)])
            f3.mea_chain(R, p9, "clean")
            fx.append_events(R, [fx.dec_ev(int(p9[-3:]), "rollback",
                                           decided_at="2026-10-26T00:00:00+00:00")])
            return s

        def c(R):
            s = f3.s_probe_a(R)
            p6 = s["props"][5]
            close = next(e["seq"] for e in fx.EV(R) if e["kind"] == "mea.close"
                         and e["prop"] == p6)
            fx.append_events(R, [fx.ev("mea.amend", "main", prop=p6, window=close,
                                       **{"from": "rolled-back"}, to="recurred", cause=4)])
            return s

        Ra, _ = self.scenario(head(4))
        m5 = self.report(Ra)["success"]["m5"]
        for k in ("main", "all"):
            self.assertEqual((m5[k]["status"], m5[k]["reason"], m5[k]["n"]),
                             ("NOT-EVALUABLE", "sample-below-w-min", 4))
        Rb, _ = self.scenario(b)
        rep = self.report(Rb)
        self.assertEqual(rep["info"]["late_rollbacks"], 1)
        m5 = rep["success"]["m5"]
        self.assertLess(abs(m5["all"]["value"] - 1 / 7), 1e-9)
        self.assertEqual((m5["all"]["n"], m5["main"]["value"], m5["main"]["n"]), (7, 0.0, 6))
        Rc, sc = self.scenario(c)
        rep = self.report(Rc)
        self.assertLess(abs(rep["success"]["m5"]["all"]["value"] - 1 / 6), 1e-9)
        self.assertTrue(self.rows(rep)[sc["props"][5]]["evaluable"])
        m1 = rep["success"]["m1"]
        self.assertEqual((m1["n"], m1["recurred"]), (4, 2))

    def test_AT_322_1_E_3_falsification_needs_adjacent_recurred_windows_of_one_key(self):
        R, _ = self.scenario(f3.s_fals)
        rc, out, err = self.run_probe(R, "--json")
        fal = json.loads(out)["falsification"]
        self.assertEqual(rc, 0)
        self.assertEqual((fal["falsified"], fal["falsified_keys"]), (True, ["k/x"]))
        Rb, _ = self.scenario(lambda r: f3.s_fals(r, only=(7,)))
        fal = self.report(Rb)["falsification"]
        self.assertEqual((fal["falsified"], fal["falsified_keys"]), (None, []))
        self.assertIn("no-evaluable-window", fal["missing"])
        Rc, _ = self.scenario(lambda r: f3.s_fals(r, only=(5,)))
        fal = self.report(Rc)["falsification"]
        self.assertIs(fal["falsified"], False)
        self.assertNotIn("no-evaluable-window", fal["missing"])

    def test_AT_322_1_E_4_events_shortfall_is_named_before_the_rows_shortfall(self):
        def build(ev, opp):
            def inner(R):
                p = f3.promoted(R)
                f3.mea_chain(R, p, "clean", ev=ev, opp=opp)
                return p
            return inner

        for ev, opp, reason in ((1, 2, "BASELINE-EVENTS-BELOW-W-EVT"),
                                (2, 2, "BASELINE-ROWS-BELOW-W-MIN"), (2, 5, None)):
            with self.subTest(ev=ev, opp=opp):
                R, p = self.scenario(build(ev, opp))
                row = self.rows(self.report(R))[p]
                self.assertEqual((row["evaluable"], row["reason"]), (reason is None, reason))


class TestFingerprintAndGate(ProbeTestCase):
    def test_AT_322_2_1_sections_and_fingerprint_parts(self):
        R, _ = self.scenario(f3.s_probe_a)
        rep = self.report(R)
        self.assertEqual(list(rep), ["schema_rev", "fingerprint", "fingerprint_parts", "head_sha",
                                     "params", "success", "info", "falsification", "ne"])
        self.assertEqual(list(rep["success"]), ["m1", "m4", "m5"])
        self.assertEqual(list(rep["success"]["m5"]), ["main", "all"])
        parts = rep["fingerprint_parts"]
        self.assertEqual(sorted(parts), ["manifest", "metrics_rev"])
        self.assertEqual(rep["fingerprint"], fp_ref(parts))
        prm = json.loads(fx.read(R, fx.PARAMS))
        self.assertEqual(parts["manifest"], si_params.fingerprint(R, prm)[1]["manifest"])
        self.assertEqual(rep["head_sha"], fx.head(R))
        lines = self.text(R).splitlines()
        self.assertEqual((lines.count("== 成功指標 =="), lines.count("== 資訊欄 ==")), (1, 1))
        i, j = lines.index("== 成功指標 =="), lines.index("== 資訊欄 ==")
        self.assertLess(i, j)
        def labels(seg):
            return {m.group(1) for ln in seg if (m := re.match(r"^(M\d)", ln))}

        self.assertEqual((labels(lines[i:j]), labels(lines[j:])), ({"M1", "M4", "M5"},
                                                                    {"M2", "M3"}))
        self.assertEqual(len([ln for ln in lines[i:j] if ln.startswith("M5")]), 2)
        self.assertTrue(any(ln.startswith("提案數") for ln in lines[j:]))
        self.assertEqual(lines[-1], f"fingerprint={rep['fingerprint']}")

    def test_AT_322_2_E_1_fingerprint_sensitivity(self):
        probe = load_probe()
        R, _ = self.scenario(f3.s_probe_a)
        f0 = probe.build_report(R)["fingerprint"]

        def copy():
            dest = fx.new_dir("fp")
            shutil.copytree(R, dest)
            return dest

        def fp_of(dest):
            return probe.build_report(dest)["fingerprint"]

        a = copy()
        fx.set_params(a, w_opp=6)
        b = copy()
        mpath = b / PROTOCOL / "metrics.md"
        mpath.write_bytes(mpath.read_bytes() + b"x")
        c = copy()
        fx.set_params(c, metrics_rev=2)
        d = copy()
        fx.put(d, f"{PROTOCOL}/research_sources.json", '{"changed": true}\n')
        e = copy()
        mpath = e / PROTOCOL / "metrics.md"
        mpath.write_bytes(mpath.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(len({f0, fp_of(a), fp_of(b), fp_of(c)}), 4)
        self.assertEqual(probe.build_report(c)["fingerprint_parts"]["metrics_rev"], 2)
        self.assertEqual((fp_of(d), fp_of(e)), (f0, f0))
        prm = json.loads(fx.read(R, fx.PARAMS))
        old = si_params.fingerprint(R, prm)[1]["check_rules_rev"]
        with mock.patch.object(si_params, "CHECK_RULES_REV", old + 7):
            self.assertEqual(probe.build_report(R)["fingerprint"], f0)
            self.assertEqual(si_params.fingerprint(R, prm)[1]["check_rules_rev"], old + 7)

    def test_AT_322_2_E_2_not_wired_into_any_gate_and_writes_nothing(self):
        def scan(paths):
            return [p for p in paths if "selfimproving_measure" in p.read_text(
                encoding="utf-8", errors="replace")]

        Ra, _ = self.scenario(f3.s_fals)
        Rb = fx.p1_base()
        for R, want in ((Ra, True), (Rb, None)):
            snap0, g0 = fx.snap(R), f3.porcelain(R)
            rc, out, err = self.run_probe(R, "--json")
            self.assertEqual(rc, 0, err)
            if want:
                self.assertIs(json.loads(out)["falsification"]["falsified"], True)
            self.assertEqual((fx.snap(R), f3.porcelain(R)), (snap0, g0))
        paths = [*(fx.ROOT / ".github" / "workflows").glob("*"),
                 *(fx.ROOT / "tools" / "git-hooks").glob("*"),
                 fx.ROOT / ".claude" / "settings.json"]
        self.assertEqual(scan([p for p in paths if p.is_file()]), [])
        dummy = fx.new_dir("gate")
        dummy.mkdir()
        (dummy / "x.yml").write_text("run: python tools/probe/selfimproving_measure.py\n",
                                     encoding="utf-8")
        self.assertEqual(len(scan([dummy / "x.yml"])), 1)

    def test_AT_340_6_1_deterministic_cwd_free_and_equal_to_measure(self):
        R, _ = self.scenario(lambda r: (f3.s_base(r), f3.s_adopt(r))[0])
        self.assertEqual(self.M(R, "measure")[0], 0)
        X = fx.new_dir("cwd")
        X.mkdir()
        e0, g0, h0 = evl(R), f3.porcelain(R), fx2.snapshot_tree(self.home)
        snap0 = fx.snap(R)
        outs = []
        for _ in range(2):
            rc, out, err = self.run_probe(R, "--json", cwd=X)
            self.assertEqual((rc, err), (0, b""))
            outs.append(out)
        self.assertEqual(outs[0], outs[1])
        self.assertNotIn(b"\r", outs[0])
        outs[0].decode("utf-8")
        self.assertEqual((evl(R), f3.porcelain(R), fx2.snapshot_tree(self.home), fx.snap(R)),
                         (e0, g0, h0, snap0))
        self.assertEqual(list(X.iterdir()), [])
        rep = json.loads(outs[0])
        row = rep["success"]["m1"]["per_prop"][0]
        meas = self.MJ(R, "measure")["windows"][0]
        base = next(e for e in win(R) if e.get("report") == "baseline")
        self.assertEqual((row["evaluable"], row["result"], row["events"], row["opp_n"]),
                         (True, "clean", 2, 5))
        self.assertEqual((row["result"], row["opp_n"], row["events"]),
                         (meas["result"], meas["baseline"]["opp_n"], base["events"]))
        self.assertEqual((rep["success"]["m1"]["n"], rep["success"]["m1"]["value"]), (1, 0.0))

    def test_AT_340_6_E_1_purity(self):
        src = PROBE.read_text(encoding="utf-8")
        self.assertEqual(probe_purity_problems(src), [])
        inject = [("import subprocess", "P-SUBPROCESS"), ("import socket", "P-NET"),
                  ("import urllib.request", "P-NET"), ("import anthropic", "P-MODEL"),
                  ('open("x.txt", "w")', "P-WRITE"), ('Path("x").write_text("y")', "P-WRITE"),
                  ('import os\n_v = os.environ.get("AUTOSDD_X")', "P-ENV"),
                  ("from lib.selfimproving import evwrite", "P-NON-RO-IMPORT")]
        for snippet, code in inject:
            with self.subTest(snippet=snippet):
                self.assertEqual(probe_purity_problems(src + "\n" + snippet + "\n"), [code])
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertIn(a.name.split(".")[0], sys.stdlib_module_names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                top = (node.module or "").split(".")[0]
                self.assertTrue(top in sys.stdlib_module_names or top == "lib", node.module)
        self.assertEqual([n for n in _env_names(tree) if _SECRET.search(n)], [])

    def test_AT_340_6_E_2_def_parsing_matches_the_crossref_checker(self):
        import check_defect_log_crossref as cdl

        hdr = "| ID | 狀態 | 發現日期 | 嚴重度 | 現象與證據（file:line） |"
        sep = "|---|---|---|---|---|"
        d = fx.def_id

        def row(n, status):
            return f"| {d(n)} | {status} | 2026-10-01 | P3 | x.md:1 |"

        edge = [(1, "fixed@abc1234", "fixed"), (2, "closed-by-decision", "closed-by-decision"),
                (3, "no_action_needed", "closed-by-decision"), (4, "open", "open"),
                (5, "wontfix", "wontfix"), (6, "", None)]
        body = [row(n, s) for n, s, _ in edge]
        # ID 欄含空白的無效列：編號於執行期組出（測試原始碼不寫不存在於真帳本的字面編號）
        body.insert(2, f"| {d(99)} 99 | open | 2026-10-01 | P3 | x.md:1 |")
        gd = fx.new_dir("gd")
        gd.mkdir()
        synthetic = gd / "AutoSDD_Defect_Log.md"
        synthetic.write_text("\n".join([hdr, sep, *body]) + "\n", encoding="utf-8")
        real = fx.ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
        for path in (synthetic, real):
            mine = si_defs.load_ledger_status(path)
            with mock.patch.object(cdl, "_DEFECT_LOG", path):
                theirs = cdl._load_ledger_status()
            self.assertEqual(mine, theirs, path.name)
            self.assertEqual({r.ident: r.status for r in si_defs.load_rows(path)}, mine)
        mine = si_defs.load_ledger_status(synthetic)
        self.assertEqual(mine, {d(n): c for n, _, c in edge})

    def test_AT_340_6_E_4_bad_mea_fields_are_not_evaluable_not_a_traceback(self):
        R0, _ = self.scenario(lambda r: (f3.s_base(r), f3.s_adopt(r))[0])
        self.assertEqual(self.M(R0, "measure")[0], 0)
        for which, key, value, _code in f3.BAD_MEA:
            with self.subTest(which=which, key=key, value=value):
                R = fx.new_dir("bad")
                shutil.copytree(R0, R)
                f3.corrupt_mea(R, which, key, value)
                rep = self.report(R)  # rc 0、stderr 為空
                m5 = rep["success"]["m5"]
                for x in (rep["success"]["m1"], m5["main"], m5["all"]):
                    self.assertEqual((x["status"], x["reason"]), ("NOT-EVALUABLE",
                                                                   "mea-events-invalid"))
                self.assertEqual(rep["falsification"]["missing"], ["mea-events-invalid"])
                ne = {n["field"]: n["reason"] for n in rep["ne"]}
                for field in ("success.m1", "success.m5.main", "success.m5.all"):
                    self.assertEqual(ne[field], "mea-events-invalid")
                self.assertIn("M1: NOT-EVALUABLE（mea-events-invalid）", self.text(R))
        self.assertEqual(self.report(R0)["success"]["m1"]["status"], "read")

    def test_AT_340_6_E_3_usage_errors_and_absent_carrier(self):
        R, _ = self.scenario(lambda r: None)
        f = fx.new_dir("afile")
        f.write_bytes(b"x")
        bad_w_n = fx.new_dir("bw")
        shutil.copytree(R, bad_w_n)
        fx.set_params(bad_w_n, w_n=KeyError)
        bad_w_opp = fx.new_dir("bo")
        shutil.copytree(R, bad_w_opp)
        fx.set_params(bad_w_opp, w_opp="5")
        calls = [(None, ["--force"], None), (f, [], None), (fx.new_dir("nonexistent"), [], None),
                 (bad_w_n, [], "w_n"), (bad_w_opp, [], "w_opp")]
        for repo, extra, name in calls:
            rc, out, err = self.run_probe(repo, *extra)
            self.assertEqual((rc, out), (3, b""))
            self.assertTrue(err.strip())
            if name:
                self.assertIn(name, err.decode("utf-8"))
        P0 = fx.p1_base()
        rep = self.report(P0)
        for field in ("m1", "m4"):
            self.assertEqual((rep["success"][field]["status"], rep["success"][field]["reason"]),
                             ("NOT-EVALUABLE", "carrier-not-established"))
        for k in ("main", "all"):
            self.assertEqual(rep["success"]["m5"][k]["reason"], "carrier-not-established")
        fields = {x["field"] for x in rep["ne"]}
        self.assertTrue({"success.m1", "success.m4", "success.m5.main", "success.m5.all"}
                        <= fields)
        text = self.text(P0)
        self.assertIn("NOT-EVALUABLE（carrier-not-established）", text)
        self.assertNotRegex(text, r"(?m)^M(1|4): 0")


if __name__ == "__main__":
    unittest.main()
