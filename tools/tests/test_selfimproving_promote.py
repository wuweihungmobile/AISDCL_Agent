"""SelfImproving P2 `promote`／`rollback`／SUSPENDED 與可進化面重驗的驗收測試（TCS-P2 PM 檔；
`tools/lib/selfimproving/promote.py`，另含 `manifest.py` 的 pre／post 式）。

方法名含 AT 底線形（錨定 `-k AT_216_1_1_` 只收一個）。夾具全用 tmp 內的合成 repo 與真
git（hermetic；
`CLAUDE_CONFIG_DIR` 與 `AUTOSDD_SI_DIR` 指到 tmp；不碰真帳本、不上網）。受測模組＝`promote.py`。
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
from _selfimproving_p2_fixtures import P2TestCase

from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold
from lib.selfimproving import manifest as si_manifest

DEMO, OTHER, NEW = fx2.DEMO, fx2.OTHER, "docs/notes/new_note.md"
_OFFSET_SEC = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$"


def setUpModule() -> None:
    fx.setup("si_p2p_")


def tearDownModule() -> None:
    fx.teardown()


def say(R: Path, p: str, quote: str | None = None, **kw) -> None:
    rc, out, err, _, _ = fx2.decide_say(R, p, quote or f"晉升 {p}", **kw)
    assert rc == 0, out + err


def tpl(key: str, build):
    return fx2.template(key, build)


def b_verified(**kw):
    return lambda r: fx2.drive_to(r, "verified", **kw)


def b_said(**kw):
    def build(r):
        p = fx2.drive_to(r, "verified", **kw)
        say(r, p)
        return p
    return build


def b_mem(said: str | None = "晉升", state: str = "verified"):
    def build(r):
        mem = fx2.make_memdir(fx.new_dir("mem"))
        (mem / "unrelated.md").write_bytes(b"unrelated\n")
        p = fx2.drive_to(r, state, cls="M", memory=mem)
        if said and state == "verified":
            say(r, p, f"{said} {p}")
        return p, mem
    return build


def b_promoted(rollback: bool = False, **kw):
    def build(r):
        p = fx2.drive_to(r, "promoted", **kw)
        if rollback:
            say(r, p, f"回滾 {p} 太慢")
        return p
    return build


def ledger(R: Path) -> bytes:
    return (R / fx.EVL).read_bytes()


def events_of(R: Path, kind: str) -> list[dict]:
    return [e for e in fx.EV(R) if e["kind"] == kind]


def mem_hashes(mem: Path | None) -> dict:
    return fx2.snapshot_tree(mem) if mem is not None else {}


def copy_mem(mem: Path) -> Path:
    dest = fx.new_dir("memc")
    shutil.copytree(mem, dest)
    return dest


def independent_dry_run(R: Path, base: str, patch: Path, mem: Path | None = None) -> bool:
    """測試自寫的獨立乾跑：全新目錄 `git archive <base>`（M 類為記憶目錄複本，邏輯根 `memory/`）
    抽出、
    apply 再 apply -R，樹等於 base 副本。"""
    env = {**os.environ, **fx.hermetic()}
    raw = subprocess.run(["git", "-C", str(R), "archive", "--format=tar", base], check=True,
                         capture_output=True, env=env).stdout
    work, twin = fx.new_dir("dry"), fx.new_dir("twin")
    for d in (work, twin):
        d.mkdir(parents=True)
        if mem is not None:
            shutil.copytree(mem, d / "memory")
        else:
            with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
                tf.extractall(d, filter="data")
    for flag in ((), ("-R",)):
        subprocess.run(["git", "-C", str(work), "-c", "core.autocrlf=false", "apply", *flag,
                        str(patch)], check=True, capture_output=True, env=env)
    return fx2.manifest_raw(work) == fx2.manifest_raw(twin)


class PromoteCase(P2TestCase):
    """共用輔助：每個測試換全新家目錄；樣板複本；rc 1 的標準輸出判準。"""

    def fresh(self, key, build):
        self.new_home()
        return tpl(key, build)

    def state_of(self, R: Path, p: str) -> str:
        return self.MJ(R, "export", "--kind", "proposals", "--id", p)["items"][0]["state"]

    def refused(self, R, verb, argv, code, **kw):
        s0, ev0 = fx.snap(R), ledger(R)
        rc, out, err = self.M(R, verb, *argv)
        self.rejected(rc, out, [code] if isinstance(code, str) else code, f"{verb} {argv}")
        self.assertTrue(out.startswith(f"reject {verb} "), out)
        self.draft_ok(R, out)
        self.assertEqual((fx.snap(R), ledger(R)), (s0, ev0), f"{verb} {argv} 不得有任何變更")
        return out

    def finish(self, R, verb, argv, code):
        """對照組：同一呼叫的結果（成功）。"""
        rc, out, err = self.M(R, verb, *argv)
        self.assertEqual(rc, 0, f"{code} 對照組 {out}{err}")
        return out


class TestPromote(PromoteCase):
    def test_AT_216_1_1_promote_positive(self):
        self.new_home()
        R = fx2.p2_base()
        pa = fx2.drive_to(R, "verified")
        pn = fx2.drive_to(R, "verified", target=OTHER,
                          heldout=fx2.make_heldout(fx.new_dir("ho"), probes="none"))
        self.assertEqual(fx2.last_event(R, "app.verify")["reasons"], ["NO-PROBES"])
        head0, log0 = fx.head(R), fx.git(R, "rev-list", "--count", "HEAD")
        st0, snap0 = fx.git(R, "status", "--porcelain"), fx.snap(R)[0]
        for p, ack in ((pa, False), (pn, True)):
            say(R, p, f"晉升 {p}" + (" 未驗採納" if ack else ""))
            rc, out, err = self.M(R, "promote", p, "--by", "PR1")
            self.assertEqual((rc, err), (0, ""), out)
            self.assertRegex(out, rf"^ok app\.promote seq=\d+ id=APP-SI-\d{{3}} prop={p} "
                                  rf"unverified_ack={'true' if ack else 'false'} "
                                  r"head_sha=[0-9a-f]{40}\n$")
            ev = fx2.last_event(R, "app.promote")
            self.assertEqual(list(ev), ["seq", "t", "kind", "by", "id", "prop", "rev", "head_sha",
                                        "pre_sha256", "post_sha256", "unverified_ack"])
            self.assertEqual((ev["by"], ev["unverified_ack"]), ("PR1", ack))
        self.assertEqual((fx.head(R), fx.git(R, "rev-list", "--count", "HEAD")), (head0, log0))
        self.assertEqual(fx.git(R, "diff", "--cached"), "")
        lines = lambda s: {ln.strip() for ln in s.splitlines()}  # noqa: E731  # fx.git 會剝首行空白
        self.assertEqual(lines(fx.git(R, "status", "--porcelain")) - lines(st0),
                         {f"M {DEMO}", f"M {OTHER}"})
        self.assertIn("FIXED-LINE", fx.read(R, DEMO))
        now = fx.snap(R)[0]
        changed = {k for k in now.keys() | snap0.keys() if now.get(k) != snap0.get(k)}
        self.assertEqual(changed, {DEMO, OTHER, fx.EVL})
        for p in (pa, pn):
            self.assertEqual(self.state_of(R, p), "promoted")
        res = self.check(R)
        for item in ("events.transitions", "events.dec_quote", "events.verdict",
                     "events.prop_files"):
            self.assertEqual(self.S(res, item), "PASS", item)

    def test_AT_216_1_E_1_preconditions(self):
        mem_said = tpl("m_said", b_mem())

        def forged(quote, flags=(), **kw):
            def build(r):
                p = fx2.drive_to(r, "verified", **kw)
                fx2.forge_dec(r, p, quote.format(p=p), flags)
                return p
            return build
        none = fx2.make_heldout(fx.new_dir("hn"), probes="none")
        red = fx2.make_heldout(fx.new_dir("hr"), probes="always_red")
        table = [  # (標籤, 樣板鍵, 建構, 預期碼)
            ("a", "approved", lambda r: fx2.drive_to(r, "approved"), "STATE-NOT-VERIFIED"),
            ("b", "sandboxed", lambda r: fx2.drive_to(r, "sandboxed"), "STATE-NOT-VERIFIED"),
            ("c", "v_pass", b_verified(), "NO-PROMOTE-DEC"),
            ("d", "forge_d", forged("晉升 {p} 未驗採納", ["unverified_ack"]),
             "PROMOTE-FORM-MISMATCH"),
            ("e", "forge_e", forged("晉升 {p}", heldout=none), "PROMOTE-FORM-MISMATCH"),
            ("f", "forge_f", forged("晉升 {p}", heldout=red), "PROMOTE-FORM-MISMATCH"),
        ]
        for label, key, build, code in table:
            with self.subTest(label):
                R, p = self.fresh(key, build)
                if label == "f":
                    self.assertEqual(fx2.last_event(R, "app.verify")["verdict"], "FAIL")
                self.refused(R, "promote", [p], code)
        with self.subTest("g"):
            R, p = self.fresh("v_said", b_said())
            patch = R / fx.PROPS_REL / p / "r1.patch"
            raw = bytearray(patch.read_bytes())
            raw[raw.rindex(b"F")] ^= 1
            patch.write_bytes(bytes(raw))
            self.refused(R, "promote", [p], "DIGEST-MISMATCH")
        with self.subTest("h"):
            R, p = self.fresh("v_said", b_said())
            with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
                self.refused(R, "promote", [p], "UNATTENDED-REFUSED")
        with self.subTest("i"):
            R, p = self.fresh("v_said", b_said())
            self.refused(R, "promote", [f"PROP-SI-{int(p[-3:]) + 900}"], "PROP-NOT-FOUND")
        with self.subTest("j"):
            R, (p, mem) = self.fresh("m_said", b_mem())
            mem0 = mem_hashes(mem)
            self.refused(R, "promote", [p], "MEMORY-DIR-MISSING")
            self.assertEqual(mem_hashes(mem), mem0)
        with self.subTest("k"):
            R, (p, mem) = self.fresh("m_said", b_mem())
            mem = copy_mem(mem)
            (mem / "feedback_demo.md").write_bytes(b"drifted\n")
            mem0 = mem_hashes(mem)
            out = self.refused(R, "promote", [p, "--memory-dir", mem], "PREIMAGE-MISMATCH")
            self.assertIn("重新上卡", out)
            self.assertEqual(mem_hashes(mem), mem0)
        with self.subTest("l"):
            R, p = self.fresh("v_said", b_said())
            fx.put(R, DEMO, fx.read(R, DEMO).replace("line 050\n", "line 050 drift\n"))
            self.refused(R, "promote", [p], "APPLY-FAILED")
            self.assertEqual([x for x in fx.tree_files(R) if x.endswith((".orig", ".rej"))], [])
        R, p = self.fresh("v_said", b_said())
        for label, argv in (("m", []), ("n", [p, "--force"]), ("o", [p, "--commit"])):
            with self.subTest(label):
                self.usage_error(*self.M(R, "promote", *argv), label)
        del mem_said

    def test_AT_216_1_E_2_dec_verification(self):
        key = "v_said"

        def sids(R, p):
            decs = {e["dkind"]: e["sid"] for e in events_of(R, "dec") if e["prop"] == p}
            return {k: fx2.transcript_path(R, v) for k, v in decs.items()}

        def case(label, damage, code, detail=None, restore=None):
            with self.subTest(label):
                R, p = self.fresh(key, b_said())
                undo = damage(R, p)
                s0, ev0 = fx.snap(R), ledger(R)
                rc, out, err = self.M(R, "promote", p)
                self.rejected(rc, out, [code], label)
                if detail:
                    self.assertIn(detail, out)
                self.assertEqual((fx.snap(R), ledger(R)), (s0, ev0))
                if label in ("b", "c"):
                    got = self.check(R)
                    self.assertEqual(self.S(got, "events.dec_quote"), "NE")
                    self.assertIn("TRANSCRIPT-UNAVAILABLE", {c for _, c in self.F(got,
                        "events.dec_quote")})
                if undo:
                    undo()
                self.assertEqual(self.M(R, "promote", p)[0], 0, f"{label} 對照組")

        def rm(which):
            def go(R, p):
                path = sids(R, p)[which]
                raw = path.read_bytes()
                path.unlink()
                return lambda: path.write_bytes(raw)
            return go

        def empty_cfg(R, p):
            other = fx.new_dir("emptycfg")
            other.mkdir()
            patcher = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(other)})
            patcher.start()
            return patcher.stop

        def rewrite_lines(which, fn):
            def go(R, p):
                path = sids(R, p)[which]
                raw = path.read_bytes()
                lines = [json.loads(x) for x in raw.decode("utf-8").splitlines()]
                path.write_bytes("".join(json.dumps(fn(x), ensure_ascii=False) + "\n"
                                         for x in lines).encode("utf-8"))
                return lambda: path.write_bytes(raw)
            return go

        def sdk(rec):
            return {**rec, "origin": {"kind": "sdk"}} if rec.get("type") == "user" else rec

        def tweak_card(rec):
            if rec.get("type") == "assistant":
                block = rec["message"]["content"][0]
                if block.get("type") == "text":
                    block["text"] = block["text"].replace("PROP-SI", "PROP-S1", 1)
            return rec

        def bad_quote(R, p):
            seq = next(e["seq"] for e in events_of(R, "dec") if e["dkind"] == "promote")
            old = next(e["quote"] for e in fx.EV(R) if e["seq"] == seq)
            fx2.rewrite_event(R, seq, quote=old + " 多")
            return lambda: fx2.rewrite_event(R, seq, quote=old)
        def console_flow(label):
            """Console 載體：approve 與 promote 皆經 `decide --carrier console`，
            之後破壞稽核檔或金鑰。"""
            with self.subTest(label), mock.patch.dict(os.environ,
                                                      {"AUTOSDD_SI_AUDIT_KEY": fx2.AUDIT_KEY}):
                self.new_home()
                R = fx2.p2_base()
                p = fx2.new_prop(R)
                fx2.issue_card(R, p)
                fx2.transcript_dir(R).mkdir(parents=True, exist_ok=True)  # 暴露掃描要求目錄在場
                dg =fx2.prop_event(R, p)["digest"]
                refs = {}
                for dk in ("approve", "promote"):
                    refs[dk] = fx2.new_uuid()
                    if dk == "promote":
                        for verb, argv in (("heldout-freeze", ["--from", fx2.make_heldout(
                                fx.new_dir("ho"), probes="count"), "--by", "FZ"]),
                                           ("sandbox", ["--by", "SB1"]), ("verify", ["--by",
                                           "VF1"])):
                            rc, out, err = fx2.cli(R, verb, p, *argv)
                            self.assertEqual(rc, 0, out + err)
                        self.assertEqual(fx2.last_event(R, "app.verify")["verdict"], "PASS",
                                         fx2.last_event(R, "app.verify"))
                    fx2.write_audit(self.home, kind="decide", ref=refs[dk], subject=p,
                                    body=fx2.body_decide(refs[dk], p, dg, dk))
                    rc, out, err = self.M(R, "decide", p, "--carrier", "console", "--audit-ref",
                                          refs[dk])
                    self.assertEqual(rc, 0, out + err)
                path = self.home / "console_audit" / f"{refs['promote']}.json"
                raw = path.read_bytes()
                if label == "g":
                    path.unlink()
                    want, env = "CONSOLE-AUDIT-MISSING", {}
                else:
                    want, env = "CONSOLE-KEY-MISSING", {"AUTOSDD_SI_AUDIT_KEY": ""}
                s0, ev0 = fx.snap(R), ledger(R)
                with mock.patch.dict(os.environ, env):
                    rc, out, _ = self.M(R, "promote", p)
                self.rejected(rc, out, [want], label)
                self.assertEqual((fx.snap(R), ledger(R)), (s0, ev0))
                path.write_bytes(raw)
                self.assertEqual(self.M(R, "promote", p)[0], 0, f"{label} 對照組")
        console_flow("g")
        console_flow("h")
        case("a", rm("approve"), "TRANSCRIPT-UNAVAILABLE")
        case("b", rm("promote"), "TRANSCRIPT-UNAVAILABLE")
        case("c", empty_cfg, "TRANSCRIPT-UNAVAILABLE")
        case("d", rewrite_lines("approve", sdk), "DEC-VERIFY-FAILED", "NOT-HUMAN-UTTERANCE")
        case("e", rewrite_lines("promote", tweak_card), "DEC-VERIFY-FAILED", "CARD-NOT-DELIVERED")
        case("f", bad_quote, "DEC-VERIFY-FAILED", "QUOTE-MISMATCH")

    def test_AT_216_2_1_rollback_dryrun_is_premise(self):
        self.new_home()
        R = fx2.p2_base()
        mem = fx2.make_memdir(fx.new_dir("mem"))
        (mem / "unrelated.md").write_bytes(b"unrelated\n")
        pd = fx2.drive_to(R, "verified")
        pm = fx2.drive_to(R, "verified", cls="M", memory=mem)
        mem0 = mem_hashes(mem)
        for p in (pd, pm):
            patch = R / fx.PROPS_REL / p / "r1.patch"
            self.assertTrue(independent_dry_run(R, fx2.prop_event(R, p)["base"], patch,
                                                mem if p == pm else None), p)
            got = si_fold.fold(si_events.sound(fx.EV(R)), 2).props[p]
            self.assertEqual((got.rollback_ok, got.touched_ok), (True, True))
            say(R, p)
            extra = ["--memory-dir", mem] if p == pm else []
            rc, out, err = self.M(R, "promote", p, *extra)
            self.assertEqual(rc, 0, out + err)
            self.assertEqual(self.state_of(R, p), "promoted")
        after = mem_hashes(mem)
        self.assertEqual(after["unrelated.md"], mem0["unrelated.md"])
        self.assertNotEqual(after["feedback_demo.md"], mem0["feedback_demo.md"])
        self.assertIn(b"FIXED-MEM", (mem / "feedback_demo.md").read_bytes())

    def test_AT_216_2_E_1_premise_in_two_places(self):
        cases = {"a": {"rollback_ok": False}, "b": {"touched_ok": False},
                 "c": {"rollback_ok": False, "touched_ok": False}}
        want = {"a": {"PROMOTE-PREMISE-ROLLBACK"}, "b": {"PROMOTE-PREMISE-TOUCHED"},
                "c": {"PROMOTE-PREMISE-ROLLBACK", "PROMOTE-PREMISE-TOUCHED"}}
        for label, change in cases.items():
            with self.subTest(label):  # 記 DEC 時就擋
                R, p = self.fresh("v_pass", b_verified())
                fx2.rewrite_event(R, fx2.last_event(R, "app.sandbox")["seq"], **change)
                dec0 = len(events_of(R, "dec"))
                rc, out, _, _, _ = fx2.decide_say(R, p, f"晉升 {p}")
                self.rejected(rc, out, want[label])
                self.assertEqual(len(events_of(R, "dec")), dec0)
            with self.subTest(label + "2"):  # 之後被破壞：promote 再驗一次
                R, p = self.fresh("v_said", b_said())
                fx2.rewrite_event(R, fx2.last_event(R, "app.sandbox")["seq"], **change)
                s0 = fx.snap(R)[0]
                n0 = len(events_of(R, "app.promote"))
                rc, out, err = self.M(R, "promote", p)
                self.rejected(rc, out, want[label])
                self.assertEqual((len(events_of(R, "app.promote")), fx.snap(R)[0]), (n0, s0))
                if label == "a":
                    got = self.check(R)
                    self.assertEqual(self.S(got, "events.verdict"), "FAIL")
                    self.assertIn("VERDICT-MISMATCH", {c for _, c in self.F(got, "events.verdict")})

    def test_AT_216_3_1_promote_record_content(self):
        self.new_home()
        R = fx2.p2_base()
        pd = fx2.drive_to(R, "verified")
        pa = fx2.drive_to(R, "verified", action="add")
        for p, rel in ((pd, DEMO), (pa, NEW)):
            pre = fx2.manifest_lf(R, [rel])
            if p == pa:
                self.assertFalse((R / NEW).exists())
            say(R, p)
            rc, out, err = self.M(R, "promote", p, "--by", "PR1")
            self.assertEqual(rc, 0, out + err)
            ev = fx2.last_event(R, "app.promote")
            self.assertEqual((ev["pre_sha256"], ev["post_sha256"]),
                             (pre, fx2.manifest_lf(R, [rel])))
            self.assertNotEqual(ev["pre_sha256"], ev["post_sha256"])
            self.assertEqual((ev["head_sha"], ev["by"]), (fx.head(R), "PR1"))
            self.assertRegex(ev["t"], _OFFSET_SEC)
            self.assertNotIn("commit_sha", ev)
            dec = [e for e in events_of(R, "dec") if e["prop"] == p and e["dkind"] == "promote"][0]
            self.assertEqual((dec["decider"], dec["digest"]), ("掌舵者", fx2.prop_event(R,
                p)["digest"]))
            self.assertRegex(dec["decided_at"], _OFFSET_SEC)
            self.assertEqual(datetime.fromisoformat(dec["decided_at"]),
                             datetime.fromisoformat(fx2.ts(20)))
        lf, crlf = fx.new_dir("lf"), fx.new_dir("crlf")
        for d, data in ((lf, b"a\nb\n"), (crlf, b"a\r\nb\r\n")):
            (d / "x").mkdir(parents=True)
            (d / "x" / "f.txt").write_bytes(data)
        self.assertEqual(si_manifest.paths_manifest(lf, ["x/f.txt"]),
                         si_manifest.paths_manifest(crlf, ["x/f.txt"]))
        (lf / "x" / "empty.txt").write_bytes(b"")
        self.assertNotEqual(si_manifest.paths_manifest(lf, ["x/empty.txt"]),
                            si_manifest.paths_manifest(lf, ["x/none.txt"]))

    def test_AT_216_3_E_1_no_commit(self):
        base = {"prop": fx.pid(1)}
        for want, kind, extra in (("EVENT-KEY-UNKNOWN", "app.promote", {"commit_sha": "a" * 40}),
                                  ("EVENT-TYPE", "app.promote", {"head_sha": "abcdef0"}),
                                  ("EVENT-KEY-UNKNOWN", "app.rollback", {"commit_sha": "a" * 40})):
            obj = fx.compose([fx.ev(kind, "main", **base, **extra)], "0" * 40, [6])[0]
            self.assertIn(want, {c for c, _ in si_events.validate(obj)}, (kind, extra))
        obj = fx.compose([fx.ev("app.promote", "main", **base)], "0" * 40, [6])[0]
        del obj["post_sha256"]
        self.assertIn("EVENT-KEY-MISSING", {c for c, _ in si_events.validate(obj)})
        self.new_home()
        R = fx2.p2_base()
        head0, log0 = fx.head(R), fx.git(R, "rev-list", "--count", "HEAD")
        p = fx2.drive_to(R, "promoted", via="cli")
        say(R, p, f"回滾 {p} 太慢")
        self.assertEqual(self.M(R, "rollback", p)[0], 0)
        self.assertEqual((fx.head(R), fx.git(R, "rev-list", "--count", "HEAD")), (head0, log0))
        self.assertEqual((fx.git(R, "diff", "--cached"), fx.git(R, "stash", "list")), ("", ""))
        self.assertFalse((R / ".git" / "index.lock").exists())


class TestRollback(PromoteCase):
    def test_AT_240_7_1_rollback_positive(self):
        self.new_home()
        R = fx2.p2_base()
        mem = fx2.make_memdir(fx.new_dir("mem"))
        want = {DEMO: fx.read(R, DEMO).encode("utf-8"), NEW: None}
        mem0 = mem_hashes(mem)
        pres = {"PD": fx2.manifest_lf(R, [DEMO]), "PA": fx2.manifest_lf(R, [NEW]),
                "PM": fx2.manifest_lf(mem, ["memory/feedback_demo.md", "memory/MEMORY.md"],
                                      "memory/")}
        head0, log0 = fx.head(R), fx.git(R, "rev-list", "--count", "HEAD")
        pd = fx2.drive_to(R, "promoted")
        pa = fx2.drive_to(R, "promoted", action="add")
        pm = fx2.drive_to(R, "promoted", cls="M", memory=mem)
        self.assertTrue((R / NEW).is_file())
        for label, p in (("PD", pd), ("PA", pa), ("PM", pm)):
            promoted = [e for e in events_of(R, "app.promote") if e["prop"] == p][0]
            say(R, p, f"回滾 {p} 太慢")
            extra = ["--memory-dir", mem] if label == "PM" else []
            rc, out, err = self.M(R, "rollback", p, *extra, "--by", "RB1")
            self.assertEqual((rc, err), (0, ""), out)
            self.assertRegex(out, rf"^ok app\.rollback seq=\d+ id=APP-SI-\d{{3}} prop={p}\n$")
            ev = fx2.last_event(R, "app.rollback")
            self.assertEqual(list(ev), ["seq", "t", "kind", "by", "id", "prop", "rev",
                                        "pre_sha256", "post_sha256"])
            self.assertEqual((ev["by"], ev["pre_sha256"], ev["post_sha256"]),
                             ("RB1", promoted["post_sha256"], promoted["pre_sha256"]))
            self.assertEqual(ev["post_sha256"], pres[label])
            self.assertEqual(self.state_of(R, p), "promoted")
        self.assertEqual((R / DEMO).read_bytes(), want[DEMO])
        self.assertFalse((R / NEW).exists())
        self.assertEqual(mem_hashes(mem), mem0)
        self.assertEqual((fx.head(R), fx.git(R, "rev-list", "--count", "HEAD")), (head0, log0))
        self.assertEqual(self.S(self.check(R), "events.transitions"), "PASS")

    def test_AT_240_7_E_1_rollback_preconditions(self):
        table = [
            ("a", "v_pass", b_verified(), [], "STATE-NOT-PROMOTED"),
            ("b", "promoted", b_promoted(), [], "NO-ROLLBACK-DEC"),
        ]
        for label, key, build, _, code in table:
            with self.subTest(label):
                R, p = self.fresh(key, build)
                self.refused(R, "rollback", [p], code)
        key = "promoted_said"
        for label in ("c", "d"):
            with self.subTest(label):
                R, p = self.fresh(key, b_promoted(True))
                rb = [e for e in events_of(R, "dec") if e["dkind"] == "rollback"][0]
                if label == "c":
                    fx2.transcript_path(R, rb["sid"]).unlink()
                    self.refused(R, "rollback", [p], "TRANSCRIPT-UNAVAILABLE")
                else:
                    other = fx.new_dir("emptycfg")
                    other.mkdir()
                    with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(other)}):
                        self.refused(R, "rollback", [p], "TRANSCRIPT-UNAVAILABLE")
        with self.subTest("e"):
            R, p = self.fresh(key, b_promoted(True))
            text = fx.read(R, DEMO)
            fx.put(R, DEMO, text + "drift\n")
            self.refused(R, "rollback", [p], "TREE-CHANGED")
            fx.put(R, DEMO, text)
            self.finish(R, "rollback", [p], "e")
        with self.subTest("f"):
            R, p = self.fresh(key, b_promoted(True))
            seq = fx2.last_event(R, "app.promote")["seq"]
            fx2.rewrite_event(R, seq, pre_sha256=fx.H(77))
            self.refused(R, "rollback", [p], "ROLLBACK-NOT-EXACT")
        with self.subTest("g"):
            R, (p, mem) = self.fresh("m_promoted", lambda r: self._m_promoted(r))
            mem = copy_mem(mem)
            mem0 = mem_hashes(mem)
            self.refused(R, "rollback", [p], "MEMORY-DIR-MISSING")
            self.assertEqual(mem_hashes(mem), mem0)
        with self.subTest("h"):
            R, p = self.fresh(key, b_promoted(True))
            with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
                self.refused(R, "rollback", [p], "UNATTENDED-REFUSED")
        with self.subTest("i"):
            R, p = self.fresh(key, b_promoted(True))
            self.refused(R, "rollback", [f"PROP-SI-{int(p[-3:]) + 900}"], "PROP-NOT-FOUND")
        with self.subTest("j"):
            R, p = self.fresh(key, b_promoted(True))
            self.usage_error(*self.M(R, "rollback", p, "--commit"), "j")

    @staticmethod
    def _m_promoted(r):
        mem = fx2.make_memdir(fx.new_dir("mem"))
        p = fx2.drive_to(r, "promoted", cls="M", memory=mem)
        say(r, p, f"回滾 {p} 太慢")
        return p, mem


class TestSuspendedResume(PromoteCase):
    def susp(self):
        self.new_home()
        return fx2.make_p2_repo(fx.new_dir("susp"), events=fx.sc_susp())

    def prop_new(self, R, run):
        patch = fx.patch_insert(DEMO, 50, ["FIXED-LINE"], old=fx.fixture_files()[DEMO])
        return self.M(R, "prop-new", "--run", run,
                      *fx.good_prop_args(R, "D", patch=patch, target=[DEMO]))

    def revise(self, R):
        patch = fx.patch_insert(DEMO, 50, ["FIXED-LINE"], old=fx.fixture_files()[DEMO])
        return self.M(R, "prop-revise", "--run", fx.rid(3), "--prop", fx.pid(130),
                      *fx.revise_args(R, "D", patch=patch))

    def resume(self, R, run, quote, *argv):
        sid, line = fx2.pc03(R, quote)
        return self.M(R, "decide", run, "--kind", "resume", "--sid", sid, "--line", line, *argv)

    def test_AT_217_2_1_resume_unsuspends(self):
        R = self.susp()
        run = fx.rid(1)
        self.assertEqual(self.MJ(R, "status")["suspended"], {"run": run})
        rc, out, _ = self.prop_new(R, fx.rid(3))
        self.rejected(rc, out, ["SUSPENDED"])
        rc, out, err = self.resume(R, run, f"恢復 {run} 兩個壞窗已人工檢視")
        self.assertEqual(rc, 0, out + err)
        self.assertRegex(out, rf"^ok dec seq=\d+ id=DEC-SI-\d{{3}} run={run} dkind=resume\n$")
        dec = events_of(R, "dec")[-1]
        self.assertEqual(dec["reason"], "兩個壞窗已人工檢視")
        self.assertEqual(dec["decider"], "掌舵者")
        self.assertFalse({"prop", "digest", "card_seq"} & set(dec))
        self.assertEqual(dec["run"], run)
        rc, out, err = self.prop_new(R, fx.rid(3))
        self.assertEqual(rc, 0, out + err)
        self.assertIsNone(self.MJ(R, "status")["suspended"])
        # prop-revise 於 SUSPENDED 期間同樣被擋（另一份複本、returned 的 PROP），恢復後受理
        self.new_home()
        R2 = fx2.make_p2_repo(fx.new_dir("susp2"), events=[
            *fx.sc_susp(), fx.prop_ev(130, 3, target=[DEMO]), fx.dec_ev(130, "return")])
        rc, out, _ = self.revise(R2)
        self.rejected(rc, out)
        self.assertIn("SUSPENDED", fx.codes_of(out))
        self.assertEqual(self.resume(R2, run, f"恢復 {run} 兩個壞窗已人工檢視")[0], 0)
        rc, out, err = self.revise(R2)
        self.assertEqual(rc, 0, out + err)
        pkg = Path(__file__).resolve().parents[1] / "lib" / "selfimproving"
        for path in sorted(pkg.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            hits = [w for w in ("FSM-STATE", "fsm_runtime", "resume-from-escalation")
                    if w in text]
            self.assertEqual(hits, [], f"{path.name} 含禁字")

    def test_AT_217_2_E_1_only_resume_unsuspends(self):
        R = self.susp()
        run1, run2 = fx.rid(1), fx.rid(2)
        ev0 = ledger(R)
        rc, out, err = self.M(R, "run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by",
            "main")
        self.assertEqual(rc, 0, out + err)
        new = re.search(r"id=(\S+)", out).group(1)
        rc, out, err = self.M(R, "research", "--skip", "--run", new, "--reason", "offline",
            "--note", "x")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual([e for e in events_of(R, "dec") if e.get("dkind") == "resume"], [])
        self.assertEqual(self.MJ(R, "status")["suspended"], {"run": run1})
        ev0 = ledger(R)
        rc, out, _ = self.resume(R, run2, f"恢復 {run2} 理由")
        self.rejected(rc, out, ["RUN-MISMATCH"])
        rc, out, _ = self.resume(R, run1, f"恢復 {run1}")
        self.rejected(rc, out, ["GRAMMAR-REASON-MISSING"])
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, _ = self.resume(R, run1, f"恢復 {run1} 理由")
        self.rejected(rc, out, ["UNATTENDED-REFUSED"])
        self.assertEqual(ledger(R), ev0)
        self.assertEqual(self.MJ(R, "status")["suspended"], {"run": run1})
        sid, line = fx2.pc03(R, f"恢復 {run1} 理由")
        argv = ["decide", run1, "--kind", "resume", "--sid", sid, "--line", line]
        self.assertEqual(self.M(R, *argv)[0], 0)
        self.assertIsNone(self.MJ(R, "status")["suspended"])
        rc, out, _ = self.M(R, *argv)
        self.rejected(rc, out, ["NOT-SUSPENDED"])
        R2 = fx2.make_p2_repo(fx.new_dir("calm"), events=[fx.run_open_ev(1), fx.skip_ev(1)])
        ev1 = ledger(R2)
        rc, out, _ = self.resume(R2, run1, f"恢復 {run1} 理由")
        self.rejected(rc, out, ["NOT-SUSPENDED"])
        self.assertEqual(ledger(R2), ev1)


class TestNonEvolvableNow(PromoteCase):
    def lt(self):
        return f"AISDLC_SDD/{fx.VNEW}/agent/x.md"

    def test_AT_220_3_1_revalidation_passes(self):
        self.new_home()
        R = fx2.p2_base()
        pd = fx2.drive_to(R, "verified")
        pl = fx2.drive_to(R, "verified", action="add", target=self.lt())
        for p in (pd, pl):
            say(R, p)
            rc, out, err = self.M(R, "promote", p)
            self.assertEqual(rc, 0, out + err)
        self.assertEqual(len(events_of(R, "app.promote")), 2)
        self.assertTrue((R / self.lt()).is_file())
        path = "docs/06_quality/SelfImproving_Protocol/params.json"
        text = fx.read(R, path)
        run = fx2.open_run(R)
        rc, out, err = self.M(R, "prop-new", "--run", run, *fx.good_prop_args(
            R, "P", patch=fx.patch_diff(path, text, text + "\n"), target=[path], handoff="T1",
            action="modify"))
        self.assertEqual(rc, 0, out + err)
        ph = re.search(r"id=(\S+)", out).group(1)
        rc, out, _, _, _ = fx2.decide_say(R, ph, f"核准 {ph}")
        self.rejected(rc, out, ["ROUTE-HANDOFF"])

    def test_AT_220_3_E_1_revalidation_blocks(self):
        def block(label, key, build, damage, repair):
            with self.subTest(label):
                R, p = self.fresh(key, build)
                damage(R)
                self.refused(R, "promote", [p], "NON-EVOLVABLE-NOW")
                repair(R)
                self.finish(R, "promote", [p], label)

        def glob_of(pattern):
            def add(R):
                prm = json.loads(fx.read(R, fx.PARAMS))
                self.saved = list(prm["non_evolvable_globs"])
                fx.set_params(R, non_evolvable_globs=[*self.saved, pattern])
            return add

        def unglob(R):
            fx.set_params(R, non_evolvable_globs=self.saved)

        def hide_version(R):
            path = R / "AISDLC_SDD/scripts/sdd_version.py"
            self.hidden = path.read_bytes()
            path.unlink()

        def show_version(R):
            (R / "AISDLC_SDD/scripts/sdd_version.py").write_bytes(self.hidden)

        def newer(R):  # LATEST 由 `git ls-files` 決定：新版目錄須被追蹤
            fx.put(R, "AISDLC_SDD/AISDLC_SDD_v0.99/README.md", "newer\n")
            fx.commit_all(R, "newer version")

        def drop_newer(R):
            shutil.rmtree(R / "AISDLC_SDD/AISDLC_SDD_v0.99")
            fx.commit_all(R, "drop newer version")
        block("a", "v_said", b_said(), glob_of(DEMO), unglob)
        block("b", "v_said", b_said(), glob_of("docs/notes/*.md"), unglob)
        latest = b_said(action="add", target=self.lt())
        block("c", "latest_said", latest, hide_version, show_version)
        block("d", "latest_said", latest, newer, drop_newer)


if __name__ == "__main__":
    unittest.main()
