"""SelfImproving P6 歷史缺陷反事實回測的驗收測試（TCS-SelfImproving-P6 BT 檔與 SY 的 BT 部分）。

受測模組：`tools/lib/selfimproving/btcases.py`、`btscore.py`、`btwrite.py`、`btrecord.py`、
`status.py`（`backtest` 鍵）、`evcheck.py`（結果帳本對帳）、`fourqparse.py`（`PROOF-BACKTEST`）、
`unattended.py`、入口 `tools/selfimproving.py`。方法名含 AT 底線形；全部以暫存 git repo 與假家目錄
（`px.claude_home`）進行，不讀真實家目錄、不連網、不呼叫任何模型、不在真 repo 建 worktree。
"""

from __future__ import annotations

import ast
import hashlib
import json
import ntpath
import os
import posixpath
import re
import shutil
import socket
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p6_fixtures as px
import _selfimproving_p7_fixtures as p7x

from lib.selfimproving import btcases, btscore, evspec, fourqparse
from lib.selfimproving import events as si_events
from lib.selfimproving import writeverbs as wv
from lib.selfimproving.git import Git

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "tools" / "lib" / "selfimproving"
SID = "00000000-0000-4000-8000-000000000001"


def setUpModule() -> None:
    fx.setup("si_bt_")


def tearDownModule() -> None:
    fx.teardown()


def git_out(repo: Path, *args: str) -> str:
    return fx.git(repo, *args)


class BtCase(fx.SiTestCase):
    """回測共用封裝：`backtest` 子命令、完整流程（prepare→answer→score）。"""

    def bt(self, repo, *args):
        return self.M(repo, "backtest", *args)

    def codes(self, out: str) -> set[str]:
        return fx.codes_of(out)

    def prepared(self, repo, n=5, k=5, seed=7, cases=None):
        """合成 `n` 案、`prepare`；回（batch, meta, bdir）。"""
        cs = cases if cases is not None else px.synthetic_cases(repo, n)
        px.write_cases(repo, cs)
        rc, out, err = self.bt(repo, "prepare", "--seed", str(seed), "--k", str(k))
        self.assertEqual(rc, 0, out + err)
        batch = re.search(r"batch=(BT-\d+)", out).group(1)
        bdir = self.home / "backtest" / batch
        return batch, json.loads((bdir / "batch.json").read_text(encoding="utf-8")), bdir

    def answer_all(self, repo, batch, meta, skip=(), tamper=None):
        """逐案落答案（第一個真 changed_file 為 suspect）；回 {agent_id: 逐字稿行}。"""
        agents = {}
        for i, c in enumerate(meta["cases"], 1):
            if c["slot"] in skip:
                continue
            aid = f"{int(re.sub(r'[^0-9]', '', batch)):04x}{i:04x}abcd"
            ans = {"case": c["slot"], "suspects": [c["changed_files"][0]], "hypothesis": "h",
                   "direction": "d"}
            f = self.home / f"ans-{batch}-{i}.json"
            f.write_text(json.dumps(ans), encoding="utf-8")
            rc, out, err = self.bt(repo, "answer", "--batch", batch, "--case", c["slot"],
                                   "--file", str(f), "--agent-id", aid)
            self.assertEqual(rc, 0, out + err)
            lines = px.clean_lines(c["nonce"], Path(c["snap"]), json.dumps(ans))
            agents[aid] = (tamper or {}).get(c["slot"], lambda x: x)(lines)
        return agents

    def scored(self, repo, n=5, k=5, seed=7, skip=(), tamper=None, cases=None):
        batch, meta, bdir = self.prepared(repo, n, k, seed, cases)
        agents = self.answer_all(repo, batch, meta, skip, tamper)
        with px.claude_home(repo, SID, agents):
            rc, out, err = self.bt(repo, "score", "--batch", batch, "--json")
        self.assertEqual(rc, 0, out + err)
        return batch, meta, bdir, json.loads(out)


class TestCases(BtCase):
    """tools/lib/selfimproving/btcases.py、btwrite.py（AC-SI-46-1）。"""

    def build(self, repo, *extra):
        rc, out, err = self.bt(repo, "cases", "--build", *extra)
        return rc, out, err

    def load(self, repo, n=1):
        return json.loads((repo / px.BT_DIR / f"cases-v{n}.json").read_text(encoding="utf-8"))

    def test_AT_646_1_1_build_matches_golden(self):
        repo, info = px.bt_repo()
        rc, out, err = self.build(repo)
        self.assertEqual(rc, 0, out + err)
        obj = self.load(repo)
        par = lambda sha: git_out(repo, "rev-parse", sha + "^")  # noqa: E731
        want = [
            {"id": fx.obs_id(11), "source": "OBS", "symptom": "回測症狀一：計數偏差",
             "fix_commit": info["f1"], "pre_commit": par(info["f1"]),
             "changed_files": ["src/a.py"]},
            {"id": fx.obs_id(12), "source": "OBS", "symptom": "回測症狀二：兩處同時錯",
             "fix_commit": info["f2"], "pre_commit": par(info["f2"]),
             "changed_files": ["src/b.py", "src/c.py"]},
            {"id": fx.def_id(2), "source": "DEF", "symptom": "回測症狀 DEF：另一個計數現象",
             "fix_commit": info["fd"], "pre_commit": par(info["fd"]),
             "changed_files": ["src/e.py"]}]
        self.assertEqual(obj["cases"], sorted(want, key=lambda c: c["id"].encode()))
        reasons = {**info["obs"], **info["def"]}
        self.assertEqual(obj["excluded"], sorted(
            ({"id": k, "reason": v} for k, v in reasons.items() if v),
            key=lambda e: e["id"].encode()))
        self.assertEqual(obj["head_sha"], info["head"])
        self.assertEqual(set(obj["ledgers"]), {"obs_sha256", "def_sha256"})

    def test_AT_646_1_E_1_every_exclusion_reason_is_applied(self):
        repo, info = px.bt_repo()
        self.build(repo)
        obj = self.load(repo)
        got = {e["id"]: e["reason"] for e in obj["excluded"]}
        self.assertEqual(set(got.values()), set(btcases.EXCLUDE_REASONS))
        case_ids = {c["id"] for c in obj["cases"]}
        for ident, why in {**info["obs"], **info["def"]}.items():
            if why:
                self.assertEqual(got[ident], why, ident)
                self.assertNotIn(ident, case_ids)

    def test_AT_646_1_2_deterministic_versioned_and_never_overwritten(self):
        repo, _ = px.bt_repo()
        with mock.patch.object(btcases, "now_iso", return_value="2026-11-10T09:00:00+08:00"):
            self.build(repo)
        with mock.patch.object(btcases, "now_iso", return_value="2026-11-10T10:00:00+08:00"):
            self.assertEqual(self.build(repo, "--version", "2")[0], 0)
        one, two = self.load(repo, 1), self.load(repo, 2)
        self.assertEqual((one["version"], two["version"]), (1, 2))
        self.assertNotEqual(one["generated_at"], two["generated_at"])
        self.assertEqual(btcases.dumps(one["cases"]), btcases.dumps(two["cases"]))
        path = repo / px.BT_DIR / "cases-v1.json"
        before = path.read_bytes()
        rc, out, _ = self.build(repo, "--version", "1")
        self.assertEqual((rc, self.codes(out)), (1, {"BT-CASES-VERSION-EXISTS"}))
        self.assertEqual(path.read_bytes(), before)
        rc, out, _ = self.build(fx.p1_base())  # 只有指向根 commit 的列＝零案例
        self.assertEqual((rc, self.codes(out)), (1, {"BT-CASES-EMPTY"}))

    def test_AT_646_1_3_file_is_normalized_and_check_detects_drift(self):
        repo, _ = px.bt_repo()
        self.build(repo)
        path = repo / px.BT_DIR / "cases-v1.json"
        raw = path.read_bytes()
        self.assertEqual(raw, btcases.dumps(json.loads(raw)).encode("utf-8"))
        self.assertTrue(raw.endswith(b"}\n") and b"\r" not in raw)
        self.assertEqual(self.bt(repo, "cases", "--check")[0], 0)
        path.write_bytes(raw.replace(b'"version": 1', b'"version":  1', 1))
        rc, out, _ = self.bt(repo, "cases", "--check")
        self.assertEqual((rc, self.codes(out)), (1, {"BT-CASES-FORMAT"}))
        obj = json.loads(raw)
        obj["cases"][0]["pre_commit"] = "0" * 40
        path.write_bytes(btcases.dumps(obj).encode("utf-8"))
        rc, out, _ = self.bt(repo, "cases", "--check")
        self.assertEqual((rc, self.codes(out)), (1, {"BT-CASES-FORMAT"}))


class TestPrepare(BtCase):
    """tools/lib/selfimproving/btwrite.py（AC-SI-46-2）。"""

    def test_AT_646_2_1_reproducible_sampling_and_repo_outside_snapshots(self):
        repo, _ = px.bt_repo()
        cases = px.synthetic_cases(repo, 12)
        px.write_cases(repo, cases)
        root = fx.new_dir("btroot")
        rc, out, err = self.bt(repo, "prepare", "--seed", "7", "--root", str(root))
        self.assertEqual(rc, 0, out + err)
        rank = lambda seed: [c["id"] for c in sorted(  # noqa: E731
            cases, key=lambda c: hashlib.sha256(f"{seed}:{c['id']}".encode()).hexdigest())][:5]
        meta = json.loads((root / "BT-001" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual([c["id"] for c in meta["cases"]], rank(7))
        for c in meta["cases"]:
            by_id = next(x for x in cases if x["id"] == c["id"])
            snap = Path(c["snap"])
            self.assertEqual(git_out(snap, "rev-parse", "HEAD"), by_id["pre_commit"])
            self.assertEqual(git_out(snap, "rev-parse", "--abbrev-ref", "HEAD"), "HEAD")  # detached
            self.assertFalse(btscore.inside(repo, snap))
            task = (root / "BT-001" / "tasks" / f"{c['slot']}.md").read_text(encoding="utf-8")
            self.assertIn(c["nonce"], task)
            self.assertIn(c["snap"], task)
            self.assertIn("一句話根因假說，≤400 字元", task)
            self.assertIn("一句話修法方向，≤400 字元", task)
            self.assertIn(by_id["symptom"], task)
            lines = task.splitlines()
            for secret in (*by_id["changed_files"], by_id["id"], by_id["fix_commit"]):
                self.assertEqual([ln for ln in lines if secret in ln], [], secret)
            self.assertEqual(c["changed_files"], by_id["changed_files"])
        rc, out, _ = self.bt(repo, "prepare", "--seed", "7", "--root", str(root))
        again = json.loads((root / "BT-002" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual([c["id"] for c in again["cases"]], rank(7))
        self.assertNotEqual(rank(8), rank(7))
        self.assertEqual(self.bt(repo, "prepare", "--seed", "8", "--root", str(root))[0], 0)
        other = json.loads((root / "BT-003" / "batch.json").read_text(encoding="utf-8"))
        self.assertEqual([c["id"] for c in other["cases"]], rank(8))

    def test_AT_646_2_E_1_refusals_leave_no_batch_no_worktree_no_event(self):
        repo, _ = px.bt_repo()
        cases = px.synthetic_cases(repo, 5)
        px.write_cases(repo, cases)
        root = fx.new_dir("btroot")
        before = git_out(repo, "worktree", "list", "--porcelain")

        def refuse(*extra, code):
            rc, out, _ = self.bt(repo, "prepare", "--seed", "1", "--root", str(root), *extra)
            self.assertEqual((rc, self.codes(out)), (1, {code}), out)
            self.assertEqual(git_out(repo, "worktree", "list", "--porcelain"), before)
            self.assertEqual([p.name for p in root.glob("BT-*")] if root.is_dir() else [], [])
            self.assertFalse((repo / fx.EVL).exists())
            return out
        refuse("--k", "0", code="BT-K-RANGE")
        refuse("--k", "11", code="BT-K-RANGE")
        rc, out, _ = self.bt(repo, "prepare", "--seed", "1", "--root", str(repo / "inside"))
        self.assertEqual((rc, self.codes(out)), (1, {"BT-ROOT-INSIDE-REPO"}))
        sop = repo / px.SOP_REL
        good = sop.read_bytes()
        sop.write_bytes(good.replace(b"<NONCE>", b"<NONC>"))
        refuse("--k", "5", code="BT-TEMPLATE-INVALID")
        sop.write_bytes(good)
        px.write_cases(repo, [*cases[:4], {**cases[4], "pre_commit": "0" * 40}])
        refuse("--k", "5", code="BT-WORKTREE-FAILED")
        px.write_cases(repo, cases[:3])
        out = refuse("--k", "5", code="BT-POOL-TOO-SMALL")
        self.assertIn("pool=3 k=5", out)

    def test_AT_646_2_2_worktree_add_argv_and_no_force(self):
        repo, _ = px.bt_repo()
        px.write_cases(repo, px.synthetic_cases(repo, 2))
        calls = []
        real = Git.run

        def spy(self_, *a, **k):
            calls.append((a, k))
            return real(self_, *a, **k)
        with mock.patch.object(Git, "run", spy):
            rc, out, err = self.bt(repo, "prepare", "--seed", "3", "--k", "2")
        self.assertEqual(rc, 0, out + err)
        adds = [(a, k) for a, k in calls if a[:1] == ("-c",) and "worktree" in a and "add" in a]
        self.assertEqual(len(adds), 2)
        for a, k in adds:
            self.assertIn("--detach", a)
            self.assertEqual(a[:2], ("-c", "core.longpaths=true"))
            self.assertEqual(k.get("timeout"), 600)
        self.assertFalse(any("--force" in a for a, _ in calls))
        tree = ast.parse((PKG / "btwrite.py").read_text(encoding="utf-8"))
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Constant)
                          and isinstance(n.value, str) and "--force" in n.value])


class TestAnswer(BtCase):
    """tools/lib/selfimproving/btrecord.py（AC-SI-46-3）。"""

    def put(self, obj) -> str:
        f = fx.new_dir("ans")
        f.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
        return str(f)

    def test_AT_646_3_1_answer_is_copied_verbatim_and_bound(self):
        repo, _ = px.bt_repo()
        batch, meta, bdir = self.prepared(repo, 2, 2)
        raw = '{"direction":"d","hypothesis":"h","suspects":["src/s1.py"],"case":"s1"}'
        rc, out, err = self.bt(repo, "answer", "--batch", batch, "--case", "s1", "--file",
                               self.put(raw), "--agent-id", "abcdef01")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual((bdir / "answers" / "s1.json").read_bytes(), raw.encode("utf-8"))
        bound = json.loads((bdir / "binding.json").read_text(encoding="utf-8"))["answers"]["s1"]
        self.assertEqual(bound["agent_id"], "abcdef01")
        from datetime import datetime
        self.assertIsNotNone(datetime.fromisoformat(bound["answered_at"]).tzinfo)

    def test_AT_646_3_E_1_malformed_answers_are_refused_and_change_nothing(self):
        repo, _ = px.bt_repo()
        batch, _, bdir = self.prepared(repo, 2, 2)
        ok = {"case": "s1", "suspects": ["src/a.py"], "hypothesis": "h", "direction": "d"}
        variants = {
            "extra-key": {**ok, "x": 1}, "missing": {k: v for k, v in ok.items() if k != "case"},
            "case-mismatch": {**ok, "case": "s2"}, "empty": {**ok, "suspects": []},
            "six": {**ok, "suspects": [f"a{i}.py" for i in range(6)]},
            "non-str": {**ok, "suspects": [1]}, "abs": {**ok, "suspects": ["/etc/x"]},
            "dotdot": {**ok, "suspects": ["../x"]},
            "drive": {**ok, "suspects": ["C:\\x"]},  # platform-ok: 純字串
            "drive2": {**ok, "suspects": ["C:/x"]},  # platform-ok: 純字串
            "ctrl": {**ok, "suspects": ["a\x07b"]},
            "hyp-empty": {**ok, "hypothesis": ""}, "hyp-long": {**ok, "hypothesis": "x" * 401},
            "not-json": "{oops"}
        for label, obj in variants.items():
            rc, out, _ = self.bt(repo, "answer", "--batch", batch, "--case", "s1", "--file",
                                 self.put(obj), "--agent-id", "abcdef01")
            self.assertEqual((rc, self.codes(out)), (1, {"BT-ANSWER-FORMAT"}), label)
        rc, out, _ = self.bt(repo, "answer", "--batch", batch, "--case", "s1", "--file",
                             self.put(ok), "--agent-id", "xyz")
        self.assertEqual((rc, self.codes(out)), (1, {"BT-ANSWER-FORMAT"}))
        rc, out, _ = self.bt(repo, "answer", "--batch", batch, "--case", "s9", "--file",
                             self.put(ok), "--agent-id", "abcdef01")
        self.assertEqual((rc, self.codes(out)), (1, {"BT-ANSWER-CASE-UNKNOWN"}))
        self.assertEqual(list((bdir / "answers").iterdir()), [])
        args = ("answer", "--batch", batch, "--case", "s1", "--file", self.put(ok), "--agent-id",
                "abcdef01")
        self.assertEqual(self.bt(repo, *args)[0], 0)
        rc, out, _ = self.bt(repo, *args)
        self.assertEqual((rc, self.codes(out)), (1, {"BT-ANSWER-EXISTS"}))


class TestScore(unittest.TestCase):
    """tools/lib/selfimproving/btscore.py（AC-SI-46-4）。"""

    def test_AT_646_4_1_score_case_golden_table(self):
        two = ["src/a.py", "src/b.py"]
        table = [  # (changed_files, suspects, rank, hit1, hit3, hit5, precision, recall)
            (two, ["src/a.py", "x.py"], 1, 1, 1, 1, Fraction(1, 2), Fraction(1, 2)),
            (two, ["x.py", "y.py", "src/b.py"], 3, 0, 1, 1, Fraction(1, 3), Fraction(1, 2)),
            (two, ["1", "2", "3", "4", "src/b.py"], 5, 0, 0, 1, Fraction(1, 5), Fraction(1, 2)),
            (two, ["x.py", "y.py"], 0, 0, 0, 0, Fraction(0), Fraction(0)),
            (["src/a.py"], ["src/a.py", "SRC/A.py", "./src/a.py"], 1, 1, 1, 1, Fraction(1),
             Fraction(1)),
            (["src/a.py"], ["Src\\A.py"], 1, 1, 1, 1, Fraction(1), Fraction(1)),
            (two, ["src/a.py", "src/b.py"], 1, 1, 1, 1, Fraction(1), Fraction(1)),
        ]
        for changed, sus, rank, h1, h3, h5, prec, rec in table:
            got = btscore.score_case(changed, sus)
            self.assertEqual((got["rank"], got["hit1"], got["hit3"], got["hit5"],
                              got["precision"], got["recall"]),
                             (rank, h1, h3, h5, prec, rec), (changed, sus))

    def test_AT_646_4_E_1_aggregate_uses_exact_arithmetic(self):
        zero = btscore.aggregate([])
        self.assertEqual((zero["n"], zero["prec_pm"], zero["rec_pm"], zero["n0"]), (0, 0, 0, True))

        def agg(*ps):
            return btscore.aggregate([{"hit1": 0, "hit3": 0, "hit5": 0, "precision": p,
                                       "recall": Fraction(0)} for p in ps])
        self.assertEqual(agg(Fraction(1, 3))["prec_pm"], 333)
        self.assertEqual(agg(Fraction(2, 3))["prec_pm"], 667)
        self.assertEqual(agg(Fraction(1, 8), Fraction(3, 8))["prec_pm"], 250)
        self.assertEqual(agg(Fraction(1, 2000))["prec_pm"], 1)  # 恰 .5 進位
        tree = ast.parse((PKG / "btscore.py").read_text(encoding="utf-8"))
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {"float", "round"})
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Constant)
                          and isinstance(n.value, float)])


class TestScoreFlow(BtCase):
    """tools/lib/selfimproving/btrecord.py（AC-SI-46-4 彙總只算 ok 案）。"""

    def test_AT_646_4_2_only_ok_cases_enter_the_denominator(self):
        repo, _ = px.bt_repo()

        def use_bash(lines):
            return [*lines[:-1], px.line("tool", name="Bash", input_={"command": "ls"}), lines[-1]]
        _, _, _, res = self.scored(repo, 5, 5, tamper={"s2": use_bash}, skip=("s5",))
        self.assertEqual((res["n"], res["unanswered"], res["contaminated"]), (3, 1, 1))
        self.assertEqual((res["hit1"], res["hit3"], res["hit5"]), (3, 3, 3))
        self.assertEqual(sorted(p["status"] for p in res["per_case"]),
                         ["contaminated", "ok", "ok", "ok", "unanswered"])


class TestInside(unittest.TestCase):
    """tools/lib/selfimproving/btscore.py 的 `inside`（兩種路徑語意各跑一組，零 skip）。"""

    def test_inside_table_for_both_path_semantics(self):
        ident = lambda p: p  # noqa: E731
        nt = [("C:\\snap\\s1", "C:\\snap\\s1\\a.py", True),  # platform-ok: 純字串
              ("C:\\snap\\s1", "C:\\snap\\s1x\\a.py", False),  # platform-ok: 純字串
              ("C:\\snap\\s1", "C:\\snap\\s1\\..\\s2\\a.py", False),  # platform-ok: 純字串
              ("C:\\snap\\s1", "c:\\SNAP\\S1\\a.py", True),  # platform-ok: 純字串
              ("C:\\snap\\s1", "D:\\snap\\s1\\a.py", False),  # platform-ok: 純字串
              ("C:\\snap\\s1", "C:/snap/s1/a.py", True)]  # platform-ok: 純字串
        posix = [("/snap/s1", "/snap/s1/a.py", True), ("/snap/s1", "/snap/s1x/a.py", False),
                 ("/snap/s1", "/snap/s1/../s2/a.py", False), ("/snap/s1", "/SNAP/s1/a.py", False),
                 ("/snap/s1", "/etc/passwd", False)]
        for mod, rows in ((ntpath, nt), (posixpath, posix)):
            for snap, target, want in rows:
                self.assertEqual(btscore.inside(snap, target, pathmod=mod, realpath=ident), want,
                                 (mod.__name__, target))
        link = {"/snap/s1/link": "/etc/passwd"}
        self.assertFalse(btscore.inside(  # posix-abs-ok: 同上
            "/snap/s1", "/snap/s1/link", pathmod=posixpath, realpath=lambda p: link.get(p, p)))


class TestLeakAudit(BtCase):
    """tools/lib/selfimproving/btscore.py 的 `audit_case`（AC-SI-46-5；fail-closed）。"""

    NONCE = "n0nce1234567"

    def setUp(self) -> None:
        super().setUp()
        self.repo = fx.new_dir("auditrepo")
        self.repo.mkdir()
        self.snap = fx.new_dir("snap")
        (self.snap / "src").mkdir(parents=True)
        self.aid = "abcdef0123"

    def audit(self, lines, **kw):
        with px.claude_home(self.repo, SID, {self.aid: lines} if lines is not None else {}):
            return btscore.audit_case(self.repo, self.aid, str(self.snap), self.NONCE, **kw)

    def clean(self):
        return px.clean_lines(self.NONCE, self.snap)

    def test_AT_646_5_1_clean_transcript_is_ok(self):
        self.assertIsNone(self.audit(self.clean()))

    def test_AT_646_5_E_1_each_dirty_pattern_has_its_reason(self):
        c, snap = self.clean(), self.snap
        read = lambda p: px.line("tool", name="Read", input_={"file_path": p})  # noqa: E731
        tool = lambda n, **i: px.line("tool", name=n, input_=i)  # noqa: E731
        say = c[-1]
        cases = {
            "transcript-missing": None,
            "binding-mismatch": [px.line("user", "沒有任務碼"), *c[1:]],
            "tool-not-allowed:Bash": [*c[:-1], tool("Bash", command="ls"), say],
            "tool-not-allowed:Write": [*c[:-1], tool("Write", file_path="x"), say],
            "tool-not-allowed:PowerShell": [*c[:-1], tool("PowerShell", command="ls"), say],
            "tool-not-allowed:WebFetch": [*c[:-1], tool("WebFetch", url="x"), say],
            "outside-snapshot": [*c[:-1], read(str(snap) + "x" + os.sep + "a.py"), say],
            "path-missing": [*c[:-1], tool("Grep", pattern="x"), say],
            "pattern-escape": [*c[:-1], tool("Glob", path=str(snap), pattern="..\\..\\*"), say],
            "no-reads": [c[0], say],
            "transcript-open": [*c[:-1], tool("Read", file_path=str(snap / "src" / "a.py"))],
        }
        for reason, lines in cases.items():
            cwd = str(self.repo)
            if lines and reason == "path-missing":
                lines = [{**ln, "cwd": cwd} for ln in lines]
            self.assertEqual(self.audit(lines), reason, reason)
        for label, tgt in (("dotdot", str(snap / ".." / "other" / "a.py")),
                           ("foreign", str(self.repo / "a.py"))):
            self.assertEqual(self.audit([*c[:-1], read(tgt), say]), "outside-snapshot", label)
        link = str(snap / "src" / "link.py")
        secret = str(self.repo / "secret")

        def fake(p):
            return secret if p == link else os.path.realpath(p)
        self.assertEqual(self.audit([*c[:-1], read(link), say], realpath=fake), "outside-snapshot")
        for lines in ([{"type": "garbage"}], [px.line("user", f"任務碼 {self.NONCE}")]):
            self.assertEqual(self.audit(lines), "transcript-missing")  # 零 assistant 行
        with px.claude_home(self.repo, SID, {self.aid: c}):
            base = btscore.transcript.transcript_dir(self.repo) / SID / "subagents"
            sib = base.parent.parent / "other-sid" / "subagents"
            sib.mkdir(parents=True)
            shutil.copy(base / f"agent-{self.aid}.jsonl", sib / f"agent-{self.aid}.jsonl")
            self.assertEqual(btscore.audit_case(self.repo, self.aid, str(snap), self.NONCE),
                             "transcript-missing")  # 同 id 兩檔
            (base / f"agent-{self.aid}.jsonl").write_bytes(b"not json\n")
            (sib / f"agent-{self.aid}.jsonl").unlink()
            self.assertEqual(btscore.audit_case(self.repo, self.aid, str(snap), self.NONCE),
                             "transcript-missing")  # 不可解析

    def handback(self, hid="toolu_h1", *, err=False, flag=True, echo=True):
        """真實交卷收尾形狀：assistant 的 SubagentHandback tool_use＋user 的同 id tool_result。"""
        use = px.line("tool", name="SubagentHandback", input_={"message": "{}"})
        use["message"]["content"][0]["id"] = hid
        res = {"type": "user", "timestamp": "2026-11-10T09:00:01.000Z", "message": {
            "role": "user", "content": [{"type": "tool_result", "tool_use_id": hid,
                                         **({"is_error": True} if err else {}),
                                         "content": "Report delivered"}]}}
        if flag:
            res["toolEndsTurn"] = True
        return [use, res] if echo else [use]

    def real(self):
        """真實形狀乾淨逐字稿：交卷後沒有結尾 text。"""
        return [*self.clean()[:-1], *self.handback()]

    def test_AT_646_5_E_3_harness_handback_tool_is_not_a_leak(self):
        """tools/lib/selfimproving/btscore.py：交卷工具不算洩漏，路徑與其他工具判準不變。"""
        c = self.clean()
        bad_read = px.line("tool", name="Read", input_={"file_path": str(self.repo / "a.py")})
        bash = px.line("tool", name="Bash", input_={"command": "ls"})
        self.assertIsNone(self.audit(self.real()))
        self.assertEqual(self.audit([*c[:-1], bad_read, *self.handback()]), "outside-snapshot")
        self.assertEqual(self.audit([*c[:-1], bash, *self.handback()]), "tool-not-allowed:Bash")

    def test_AT_646_5_E_4_handback_closure_needs_a_matching_ok_result(self):
        """tools/lib/selfimproving/btscore.py `_closed`：收尾只認緊鄰交卷 id 的非錯誤回應。"""
        c = self.clean()[:-1]
        for flag in (True, False):
            self.assertIsNone(self.audit([*c, *self.handback(flag=flag)]), flag)
        noise = {"type": "api-request", "timestamp": "2026-11-10T09:00:02.000Z"}
        self.assertIsNone(self.audit([*c, *self.handback(), noise]))
        self.assertIsNone(self.audit([*c, self.handback()[0], noise, self.handback()[1]]))
        self.assertEqual(self.audit([*c, *self.handback(echo=False)]), "transcript-open")
        self.assertEqual(self.audit([*c, *self.handback(err=True)]), "transcript-open")
        use, res = self.handback()
        res["message"]["content"][0]["tool_use_id"] = "toolu_other"
        other = {"type": "user", "timestamp": "t", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_x", "content": "x"}]}}
        for t in ([*c, use, res], [*c, use, c[-1], self.handback()[1]], [*c, other]):
            self.assertEqual(self.audit(t), "transcript-open", len(t))

    def test_AT_646_5_E_5_handback_alone_is_not_a_read(self):
        """tools/lib/selfimproving/btscore.py：只交卷、零讀取＝no-reads（交卷不計入讀取）。"""
        c = self.clean()
        self.assertEqual(self.audit([c[0], *self.handback()]), "no-reads")

    def test_AT_646_5_E_6_read_target_falls_back_to_path_key(self):
        """tools/lib/selfimproving/btscore.py `_tool_verdict`：file_path 優先、其次 path。"""
        c, snap = self.clean(), self.snap
        inside, outside = str(snap / "src" / "a.py"), str(self.repo / "a.py")

        def read(**kw):
            return [*c[:-1], px.line("tool", name="Read", input_=kw), c[-1]]
        self.assertIsNone(self.audit(read(path=inside)))
        self.assertEqual(self.audit(read(path=outside)), "outside-snapshot")
        self.assertEqual(self.audit(read(offset=1)), "outside-snapshot")
        self.assertEqual(self.audit(read(file_path=outside, path=inside)), "outside-snapshot")
        self.assertEqual(self.audit(read(file_path=7, path=outside)), "outside-snapshot")

    def test_AT_646_5_E_2_missing_dir_or_renamed_layout_fails_closed(self):
        empty = fx.new_dir("emptyhome")
        empty.mkdir()
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(empty)}):
            self.assertEqual(btscore.audit_case(self.repo, self.aid, str(self.snap), self.NONCE),
                             "transcript-missing")
        repo, _ = px.bt_repo()
        batch, meta, bdir = self.prepared(repo, 2, 2)
        agents = self.answer_all(repo, batch, meta)
        with px.claude_home(repo, SID, agents, folder="workers"):
            rc, out, err = self.bt(repo, "score", "--batch", batch, "--json")
        res = json.loads(out)
        self.assertEqual((rc, res["n"], res["contaminated"]), (0, 0, 2), out + err)
        self.assertEqual({p["reason"] for p in res["per_case"]}, {"transcript-missing"})


class TestLedger(BtCase):
    """tools/lib/selfimproving/btrecord.py、evcheck.py（AC-SI-46-6）。"""

    def test_AT_646_6_1_ledger_row_and_event_agree(self):
        repo, _ = px.bt_repo(matrix=False)
        _, _, _, res = self.scored(repo, 3, 3)
        rows = (repo / px.BT_RESULTS).read_bytes().split(b"\n")
        self.assertEqual(rows[1], b"")
        row = json.loads(rows[0])
        self.assertEqual(list(row)[:3], ["batch", "scored_at", "cases_version"])
        ev = [e for e in fx.EV(repo) if e["kind"] == "backtest.result"][0]
        self.assertEqual((ev["ledger_line"], ev["row_sha256"], ev["by"]),
                         (1, "sha256:" + hashlib.sha256(rows[0]).hexdigest(), "main"))
        for k in ("batch", "n", "unanswered", "contaminated", "hit1", "hit3", "hit5", "prec_pm",
                  "rec_pm", "cases_version", "cases_sha256", "seed", "k"):
            self.assertEqual(ev[k], row[k], k)
        self.assertEqual(si_events.validate(ev), [])
        _, _, _, res2 = self.scored(repo, 3, 3, seed=8)
        self.assertEqual([e["ledger_line"] for e in fx.EV(repo) if e["kind"] == "backtest.result"],
                         [1, 2])
        self.assertTrue(res["ok"] and res2["ok"])

    def test_AT_646_6_E_1_rescore_and_failed_event_leave_ledger_intact(self):
        repo, _ = px.bt_repo(matrix=False)
        batch, _, _, _ = self.scored(repo, 3, 3)
        ledger = repo / px.BT_RESULTS
        before, events = ledger.read_bytes(), (repo / fx.EVL).read_bytes()
        rc, out, _ = self.bt(repo, "score", "--batch", batch)
        self.assertEqual((rc, self.codes(out)), (1, {"BT-BATCH-SCORED"}))
        batch2, meta2, _ = self.prepared(repo, 0, 3, seed=9, cases=json.loads(
            (repo / px.BT_DIR / "cases-v1.json").read_text(encoding="utf-8"))["cases"])
        agents = self.answer_all(repo, batch2, meta2)
        with px.claude_home(repo, SID, agents), \
                mock.patch.object(wv, "params_for", return_value={"event_max_bytes": 100}):
            rc, out, _ = self.bt(repo, "score", "--batch", batch2)
        self.assertEqual((rc, "EVENT-BYTES-OVER" in out), (1, True), out)
        self.assertEqual((ledger.read_bytes(), (repo / fx.EVL).read_bytes()), (before, events))

    def test_AT_646_6_2_check_binds_rows_events_and_cases(self):
        repo, _ = px.bt_repo(matrix=False)
        self.assertEqual(self.bt(repo, "cases", "--build")[0], 0)  # 真帳本 id（合成 id 會懸空）
        real = json.loads((repo / px.BT_DIR / "cases-v1.json").read_text(encoding="utf-8"))["cases"]
        self.scored(repo, 0, 3, cases=real)
        res = self.check(repo)
        item = res["_item"]["events.prop_files"]
        self.assertEqual((res["_rc"], len(res["items"])), (0, 35), item)
        ledger, cases = repo / px.BT_RESULTS, repo / px.BT_DIR / "cases-v1.json"
        row, craw = ledger.read_bytes(), cases.read_bytes()

        def codes():
            r = self.check(repo)
            return r["_rc"], {f["code"] for f in r["_item"]["events.prop_files"]["findings"]}
        ledger.write_bytes(row.replace(b'"seed":7', b'"seed":6', 1))
        self.assertEqual(codes(), (1, {"BT-RESULT-SHA-MISMATCH"}))
        ledger.write_bytes(b"")
        self.assertEqual(codes(), (1, {"BT-RESULT-MISSING"}))
        ledger.write_bytes(row + row)
        self.assertEqual(codes(), (1, {"BT-ROW-UNBOUND"}))
        ledger.write_bytes(row)
        cases.write_bytes(craw.replace(b'"schema_rev": 1', b'"schema_rev":  1', 1))
        self.assertEqual(codes(), (1, {"BT-CASES-SHA-MISMATCH"}))
        cases.write_bytes(craw)
        self.assertEqual(codes()[0], 0)


class TestCleanup(BtCase):
    """tools/lib/selfimproving/btwrite.py（AC-SI-46-7）。"""

    def test_AT_646_7_1_cleanup_uses_worktree_remove_then_prune(self):
        repo, _ = px.bt_repo()
        batch, meta, bdir = self.prepared(repo, 2, 2)
        calls = []
        real = Git.run

        def spy(self_, *a, **k):
            calls.append(a)
            return real(self_, *a, **k)
        with mock.patch.object(Git, "run", spy):
            rc, out, err = self.bt(repo, "cleanup", "--batch", batch)
        self.assertEqual(rc, 0, out + err)
        self.assertIn(("worktree", "prune"), calls)
        self.assertEqual(len([a for a in calls if a[:2] == ("worktree", "remove")]), 2)
        self.assertFalse(any("--force" in a for a in calls))
        listed = git_out(repo, "worktree", "list", "--porcelain")
        self.assertNotIn(bdir.name, listed)
        self.assertEqual(list((bdir / "snap").iterdir()), [])
        self.assertFalse((repo / ".git" / "worktrees").exists()
                         and list((repo / ".git" / "worktrees").iterdir()))

    def test_AT_646_7_E_1_dirty_snapshot_is_kept_and_others_cleaned(self):
        repo, _ = px.bt_repo()
        batch, meta, bdir = self.prepared(repo, 3, 3)
        dirty = Path(meta["cases"][1]["snap"])
        (dirty / "untracked.txt").write_bytes(b"x")
        calls = []
        real = Git.run

        def spy(self_, *a, **k):
            calls.append(a)
            return real(self_, *a, **k)
        with mock.patch.object(Git, "run", spy):
            rc, out, _ = self.bt(repo, "cleanup", "--batch", batch)
        self.assertEqual((rc, self.codes(out)), (1, {"BT-WORKTREE-DIRTY"}))
        self.assertTrue(dirty.is_dir())
        self.assertEqual(sorted(p.name for p in (bdir / "snap").iterdir()), [dirty.name])
        self.assertIn(("worktree", "prune"), calls)


class TestStatusAndGuards(BtCase):
    """tools/lib/selfimproving/status.py、fourqparse.py、unattended.py（AC-SI-46-8）。"""

    def bt_event(self, repo, sha, hit5, **kw):
        ev = {"kind": "backtest.result", "by": "main", "batch": "BT-001", "cases_version": 1,
              "cases_sha256": "sha256:" + sha * 64, "seed": 7, "k": 5, "n": 5, "unanswered": 0,
              "contaminated": 0, "hit1": 0, "hit3": 0, "hit5": hit5, "prec_pm": 100,
              "rec_pm": 100, "ledger_line": 1, "row_sha256": "sha256:" + "d" * 64, **kw}
        cur = fx.EV(repo)
        seq = cur[-1]["seq"] + 1 if cur else 1
        line = {"seq": seq, "t": px.TIME, **ev}
        with (repo / fx.EVL).open("ab") as fh:
            fh.write((json.dumps(line, ensure_ascii=False, separators=(",", ":")) + "\n").encode())

    def test_AT_646_8_1_status_key_and_trend_stays_within_one_cases_version(self):
        repo = fx.p1_base()
        obj = json.loads(self.M(repo, "status", "--json")[1])
        self.assertEqual((len(obj), list(obj)[-1], obj["backtest"]), (20, "backtest", None))
        self.assertIn("backtest: null", self.M(repo, "status")[1])
        self.bt_event(repo, "b", 5)
        for h in range(1, 8):
            self.bt_event(repo, "a", h % 5 + 1, batch=f"BT-{h + 1:03d}")
        got = json.loads(self.M(repo, "status", "--json")[1])["backtest"]
        self.assertEqual(list(got), ["cases_version", "cases_sha256", "n", "hit1", "hit3", "hit5",
                                     "prec_pm", "rec_pm", "contaminated", "hit5_trend"])
        self.assertEqual(got["cases_sha256"], "sha256:" + "a" * 64)
        self.assertEqual(got["hit5_trend"], [h % 5 + 1 for h in range(3, 8)])
        self.bt_event(repo, "b", 2)
        got = json.loads(self.M(repo, "status", "--json")[1])["backtest"]
        self.assertEqual((got["cases_sha256"], got["hit5_trend"]), ("sha256:" + "b" * 64, [5, 2]))
        self.assertIn("backtest: cases_v1", self.M(repo, "status")[1])

    def test_AT_646_8_E_1_proof_may_not_cite_backtest_scores(self):
        params = {"fourq_from_run": 1}
        proof = "指標類別：定性；症狀定義：x；反證：y；收斂：{}"
        for word in ("回測", "backtest", "BackTest"):
            got = fourqparse.body_codes({"method": "m", "proof": proof.format(word)},
                                        fx.rid(1), params)
            self.assertIn("PROOF-BACKTEST", [c for c, _ in got], word)
        clean = fourqparse.body_codes({"method": "m", "proof": proof.format("人工審視")},
                                      fx.rid(1), params)
        self.assertNotIn("PROOF-BACKTEST", [c for c, _ in clean])
        self.assertFalse([t for t in evspec.GOODHART if "backtest" in t.lower() or "回測" in t])

    def test_AT_646_8_2_measures_do_not_read_backtest_results(self):
        repo, _ = px.bt_repo(matrix=False)
        self.scored(repo, 3, 3)
        probe = ROOT / "tools" / "probe" / "selfimproving_measure.py"

        def run():
            argv = [sys.executable, str(probe), "--repo", str(repo), "--json"]
            cp = subprocess.run(argv, capture_output=True)  # child-encoding-ok: 只比位元組
            return cp.returncode, cp.stdout
        before = run()
        (repo / px.BT_RESULTS).write_bytes(b"garbage\n")
        self.assertEqual(run(), before)
        (repo / px.BT_RESULTS).unlink()
        self.assertEqual(run(), before)

    def test_AT_646_8_3_unattended_refuses_every_subcommand_and_nothing_touches_the_network(self):
        repo, _ = px.bt_repo()
        argvs = [("cases", "--build"), ("cases", "--check"), ("prepare", "--seed", "1"),
                 ("answer", "--batch", "BT-001", "--case", "s1", "--file", "x", "--agent-id",
                  "abcdef01"), ("score", "--batch", "BT-001"), ("cleanup", "--batch", "BT-001")]
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("連網")), \
                mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            for argv in argvs:
                rc, out, _ = self.bt(repo, *argv)
                self.assertEqual((rc, self.codes(out)), (1, {"UNATTENDED-REFUSED"}), argv)
        self.assertEqual(sorted(p.name for p in (repo / px.BT_DIR).glob("*")) if
                         (repo / px.BT_DIR).exists() else [], [])
        with mock.patch.object(socket.socket, "connect", side_effect=AssertionError("連網")):
            self.assertEqual(self.build_and_prepare(repo), 0)

    def build_and_prepare(self, repo) -> int:
        rc = self.bt(repo, "cases", "--build")[0]
        return rc or self.bt(repo, "prepare", "--seed", "1", "--k", "2")[0]


# --------------------------------------------------------------------------- 自增 AC（SY，BT 部分）
CAP = None


def cap():
    global CAP
    if CAP is None:
        import test_selfimproving_capability as module
        CAP = module
    return CAP


ALLOWED = tuple(re.compile(p) for p in (
    r"^tools/lib/selfimproving/(registry|netguard|htmltext|expand|evspec6|btcases|btscore|regwrite"
    r"|btwrite|btrecord)\.py$",
    r"^tools/lib/selfimproving/(fetch|research|evspec|events|evcheck|check|fourqparse|params"
    r"|consoleaudit|patrol|patrolrun|status|unattended|sched|issuemap)\.py$",
    r"^tools/selfimproving\.py$",
    r"^tools/tests/(test_selfimproving_(registry|netfetch|backtest)"
    r"|_selfimproving_p6_fixtures)\.py$",
    r"^tools/tests/fixtures/selfimproving/(G-S1\.audit\.json|html_golden\.(html|txt))$",
    # 既有測試同步（TCS §2 所列；§4 漏列的動詞數／能力登記同步站點＝issues、console_obs、p3_meta）
    r"^tools/tests/test_selfimproving_(capability|fourq_gate|issuemap|fourq_model|events_p2"
    r"|schedule_gate|export_status|events|research_scan|issues|console_obs|p3_meta|p2_meta"
    r"|measure_verb|schedule_model|check|ledgerdb_p0|sandbox)\.py$",
    # 重釘三檔（護欄層行數棘輪與兩站點 doc-total）
    r"^tools/tests/test_adr_xplat001_c1c2_lock\.py$",
    r"^docs/04_planning/AutoSDD_improving_112\.md$",
    r"^docs/06_quality/CrossPlatform_R145_Scan_Findings\.md$",
    r"^tools/tests/_selfimproving_(fixtures|p5_fixtures)\.py$",
    r"^tools/tests/test_root_module_layout\.py$",
    r"^docs/06_quality/SelfImproving_Protocol/research_registry\.json$",
    r"^docs/06_quality/SelfImproving_Backtest/.+$",
    r"^docs/06_quality/SelfImproving_Event_Ledger\.jsonl$",
))
FORBIDDEN = ("docs/01_requirements/SelfImproving_PRD.md",
             "docs/05_development/SelfImproving_Operations_SOP.md",
             "docs/03_testing/contracts/TCS-SelfImproving-P", "docs/02_architecture/Root_Layout",
             "tools/lib/selfimproving/fold.py", "tools/lib/selfimproving/writeverbs.py",
             ".claude/", "AgentConsole/", ".github/",
             "docs/06_quality/SelfImproving_Protocol/research_sources.json")


def scope_problems(root: Path, base: str) -> list[str]:
    """`<base>..<tip>` 已提交差異觸及允許集合時：集合之外與不得改路徑（空＝守衛綠）。"""
    touched, outside, frozen = px.scope_verdict(px.committed_names(root, base),
                                                (*ALLOWED, *p7x.P7_ALLOWED), FORBIDDEN)
    return [*outside, *frozen] if touched else []


class TestSystem(BtCase):
    """tools/tests/test_selfimproving_capability.py 的登記表與範圍守衛（AC-P6-090-1、3、4）。"""

    def test_AT_690_1_1_capability_registry_is_72_with_the_new_ten(self):
        c = cap()
        self.assertEqual(c.capability_problems(c.PKG, c.CAPABILITY, c.ENTRY), [])
        counts = {k: sum(1 for v in c.CAPABILITY.values() if v == k) for k in c.CATEGORIES}
        want = {"ro": 56, "rw": 14, "net": 2, "exec": 6}
        self.assertEqual((len(c.CAPABILITY), counts), (78, want))
        for n in ("registry", "netguard", "htmltext", "expand", "evspec6", "btcases", "btscore"):
            self.assertEqual(c.CAPABILITY[f"{n}.py"], "ro", n)
        for n in ("regwrite", "btwrite", "btrecord"):
            self.assertEqual(c.CAPABILITY[f"{n}.py"], "rw", n)
        names = {p.name for p in c.PKG.glob("*.py")}
        texts = {n: (c.PKG / n).read_text(encoding="utf-8") for n in names}
        self.assertEqual({n for n, t in texts.items() if c._abs_imports(t) & c.NET_MODULES},
                         {"fetch.py"})
        self.assertEqual({n for n, t in texts.items() if "subprocess" in t},
                         {"git.py", "runner.py"})

    def test_AT_690_1_E_1_registry_judgement_has_teeth_for_the_new_files(self):
        c = cap()
        injections = {
            "btcases": ("\n_X = Path('a').write_text('x')\n", "btcases.py", "寫入"),
            "htmltext": ("\nimport socket\n", "htmltext.py", "socket"),
            "btscore": ("\nfrom . import btwrite\n", "btscore.py", "btwrite"),
            "btwrite": ("\nimport subprocess\n", "btwrite.py", "subprocess"),
        }
        for key, (code, fname, cause) in injections.items():
            with self.subTest(key):
                root = fx.new_dir("capcopy")
                pkg = root / "lib" / "selfimproving"
                shutil.copytree(c.PKG, pkg, ignore=shutil.ignore_patterns("__pycache__"))
                (pkg / f"{key}.py").write_text((pkg / f"{key}.py").read_text(encoding="utf-8")
                                               + code, encoding="utf-8")
                got = c.capability_problems(pkg, c.CAPABILITY, c.ENTRY)
                self.assertTrue([g for g in got if fname in g and cause in g], got)
        reg = {k: v for k, v in c.CAPABILITY.items() if k != "btcases.py"}
        got = c.capability_problems(c.PKG, reg, c.ENTRY)
        self.assertTrue([g for g in got if "btcases.py" in g and "未登記" in g], got)

    def test_AT_690_3_1_no_regression_on_counts_and_skip_output(self):
        repo = fx.p1_base()
        res = self.check(repo)
        self.assertEqual(len(res["items"]), 35)
        self.assertEqual(len(json.loads(self.M(repo, "status", "--json")[1])), 20)
        out = self.cli_ok(repo, "run-open", "--trigger", "a", "--coord", "tools/a.py:1",
                          "--by", "main")
        run = re.search(r"id=(\S+)", out).group(1)
        skip = self.cli_ok(repo, "research", "--skip", "--run", run, "--reason", "offline",
                           "--note", "離線驗證")
        self.assertRegex(skip, rf"^ok research\.skip seq=\d+ run={run} reason=offline\n$")

    def test_AT_690_4_1_scope_guard_needs_an_explicit_base(self):
        base = px.scope_base()
        if base is None:
            print("[AT-690-4-1] guard-not-triggered (no SI_SCOPE_BASE)")
        else:
            self.assertEqual(scope_problems(ROOT, base), [], f"基準 {base}")

    def test_scope_guard_negative_control_a_base_makes_out_of_set_commits_red(self):
        """tools/tests/_selfimproving_p6_fixtures.py 的範圍守衛機制（AT-690-4-1）：夾具 git repo 上
        「設了基準且越界＝紅」「只改允許集合＝綠」「終點早於 HEAD 時只看 BASE..TIP」。"""
        bad, base = px.scope_fixture({"README.md": "x\n"}, {
            "tools/lib/selfimproving/btcases.py": "a\n",
            "docs/01_requirements/SelfImproving_PRD.md": "p\n"})
        good, gbase = px.scope_fixture({"README.md": "x\n"},
                                       {"tools/lib/selfimproving/btcases.py": "a\n"})
        tipped, tbase = px.scope_fixture({"README.md": "x\n"},
                                         {"tools/lib/selfimproving/btscore.py": "a\n"},
                                         {"AgentConsole/late.txt": "z\n"})
        for repo in (bad, good, tipped):
            self.addCleanup(shutil.rmtree, repo.parent, True)
        prd = "docs/01_requirements/SelfImproving_PRD.md"
        self.assertEqual(scope_problems(bad, base), [prd] * 2)
        self.assertEqual(scope_problems(good, gbase), [])
        self.assertNotEqual(scope_problems(tipped, tbase), [])
        with mock.patch.dict(os.environ, {"SI_SCOPE_TIP": "HEAD~1"}):
            self.assertEqual(scope_problems(tipped, tbase), [])
        with mock.patch.dict(os.environ, {"SI_SCOPE_BASE": "", "SI_P4_BASE_SHA": ""}):
            self.assertIsNone(px.scope_base())


if __name__ == "__main__":
    unittest.main()
