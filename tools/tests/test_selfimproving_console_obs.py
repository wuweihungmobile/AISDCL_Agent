# 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
"""SelfImproving P2 Console 載體的根層半驗收測試（TCS-P2 CN 檔：`decide --carrier console`、
`obs-add`、
`obs-close`、`check`／`status`／`export` 的擴充；受測模組＝`consoleaudit.py`、`obsrows.py`、
`obswrite.py`、
`decheck.py`）。方法名含 AT 底線形（錨定 `-k AT_233_1_1_` 只收一個）。夾具全用 tmp 內的合成 repo 與
合成稽核檔（hermetic；`AUTOSDD_SI_DIR`、`CLAUDE_CONFIG_DIR` 指到 tmp；金鑰為 §5.5 的公開測試金鑰）。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
from _selfimproving_p2_fixtures import P2TestCase, new_uuid, write_audit

from lib.selfimproving import consoleaudit
from lib.selfimproving import events as si_events

KEY = fx2.AUDIT_KEY
OBS_REL = "docs/06_quality/SelfImproving_Observation_Ledger.md"
V_DIGEST = "sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe"
VECTORS = {  # §5.5 逐字：(kind, audit_ref, body 字串, mac)
    "V1": ("decide", "6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b",
           '{"schema_rev":1,"audit_ref":"6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b","kind":"decide",'
           '"user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","prop":"PROP-SI-004",'
           f'"digest":"{V_DIGEST}","dkind":"approve","flags":[]}}',
           "a23f62da5cc2b8668a05570632b60700316350667c2fef600beda100c4bf3c21"),
    "V2": ("decide", "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
           '{"schema_rev":1,"audit_ref":"0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d","kind":"decide",'
           '"user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","prop":"PROP-SI-004",'
           f'"digest":"{V_DIGEST}","dkind":"reject","reason_class":"證據不足",'
           '"reason":"證據座標不足，無法判定","flags":[]}',
           "830722c9fcfccc37861f9fe62498aa0074822595e85578e48c8a04298de0ce9b"),
    "V3": ("obs-add", "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
           '{"schema_rev":1,"audit_ref":"b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e","kind":"obs-add",'
           '"user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00",'
           '"context":"Console・自我進化頁","symptom":"待入帳徽章在入帳後仍顯示",'
           '"evidence":"AgentConsole/frontend/components/domain/si/SiView.tsx:88",'
           '"category":"bug","severity":"P3","face":"產品","external_derived":false}',
           "0e67b0e0be050c07dc3b539fed87b3f53f88856446d2468b0e9f1da71cb94f35"),
    "V4": ("obs-close", "c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f",
           '{"schema_rev":1,"audit_ref":"c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f","kind":"obs-close",'
           '"user":"admin","role":"ADMIN","time":"2026-10-21T09:15:30+08:00","obs_id":"OBS-SI-247",'
           '"disposition":"decided：掌舵者裁決，已修復"}',
           "f299d74dd7c261072b69a4c14a79999cda39716b5a9851b65fce8b6da016f6bc"),
}


def setUpModule() -> None:
    fx.setup("si_p2c_")


def tearDownModule() -> None:
    fx.teardown()


def home_state(home: Path) -> dict:
    box = home / "console_audit"
    return {p.name: p.read_bytes() for p in box.iterdir()} if box.is_dir() else {}


class ConsoleCase(P2TestCase):
    def setUp(self) -> None:
        super().setUp()
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": KEY})
        patcher.start()
        self.addCleanup(patcher.stop)

    def audit(self, kind, body, subject, **kw):
        return write_audit(self.home, kind=kind, ref=body["audit_ref"], subject=subject, body=body,
                           **kw)

    def decide_c(self, R, ident, body, *, subject=None, extra=(), **kw):
        self.audit("decide", body, ident if subject is None else subject, **kw)
        return self.M(R, "decide", ident, "--carrier", "console", "--audit-ref", body["audit_ref"],
                      *extra)

    def digest_of(self, R, p) -> str:
        return fx2.prop_event(R, p)["digest"]

    def guard(self, R, rc, out, codes, msg=""):
        """rc 1 的標準判準：碼恰為 `codes`、草稿列可貼入。"""
        self.rejected(rc, out, codes, msg)
        self.draft_ok(R, out, msg)

    def assert_untouched(self, R, s0, ev0, h0):
        self.assertEqual((fx.snap(R), (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b"",
                          home_state(self.home)), (s0, ev0, h0))

    def base(self, state="proposed", **kw):
        self.new_home()
        R = fx2.p2_base()
        return R, fx2.drive_to(R, state, **kw) if state != "none" else None


class TestDecideConsole(ConsoleCase):
    def _pre_states(self):
        """十列決定的前提態：(標籤, 建構 -> (R, id), dkind, body 附加參數)。"""
        none = lambda: fx2.make_heldout(fx.new_dir("hn"), probes="none")  # noqa: E731
        return [
            ("approve", lambda: self.base(), "approve", {}),
            ("reject", lambda: self.base(), "reject", {"reason_class": "證據不足", "reason": "x"}),
            ("return", lambda: self.base(), "return", {"reason_class": "證據不足", "reason": "x"}),
            ("promote", lambda: self.base("verified"), "promote", {}),
            ("promote-ack", lambda: self.base("verified", heldout=none()), "promote",
             {"flags": ["unverified_ack"]}),
            ("decline-promote", lambda: self.base("verified"), "decline-promote",
             {"reason_class": "風險過高", "reason": "x"}),
            ("ack-handoff", lambda: self.base(route="handoff:T1"), "ack-handoff", {}),
            ("unblock", lambda: self._rejected(), "unblock", {}),
            ("rollback", lambda: self.base("promoted"), "rollback", {"reason": "太慢"}),
            ("resume", lambda: self._suspended(), "resume", {"reason": "已人工檢視"}),
        ]

    def _rejected(self):
        R, p = self.base()
        body = fx2.body_decide(new_uuid(), p, self.digest_of(R, p), "reject",
                               reason_class="證據不足", reason="x")
        rc, out, err = self.decide_c(R, p, body)
        self.assertEqual(rc, 0, out + err)
        return R, p

    def _suspended(self):
        self.new_home()
        return fx2.make_p2_repo(fx.new_dir("susp"), events=fx.sc_susp()), fx.rid(1)

    def test_AT_233_1_1_ten_decisions(self):
        for label, build, dkind, extra in self._pre_states():
            with self.subTest(label):
                R, ident = build()
                digest = None if dkind in ("unblock", "rollback", "resume") else \
                    self.digest_of(R, ident)
                ref = new_uuid()
                body = fx2.body_decide(ref, ident, digest, dkind, **extra)
                _, sha = self.audit("decide", body, ident)
                pend = self.MJ(R, "status")["console_pending"]
                self.assertEqual((pend["count"], pend["items"]),
                                 (1, [{"audit_ref": ref, "kind": "decide"}]))
                h0 = home_state(self.home)
                rc, out, err = self.M(R, "decide", ident, "--carrier", "console", "--audit-ref",
                                      ref, "--by", "ops1")
                self.assertEqual((rc, err), (0, ""), out)
                tail = "" if dkind == "resume" else r" digest8=[0-9a-f]{8}"
                key = "run" if dkind == "resume" else "prop"
                self.assertRegex(out, rf"^ok dec seq=\d+ id=DEC-SI-\d{{3}} {key}={ident} "
                                      rf"dkind={dkind}{tail}\n$")
                ev = fx2.last_event(R, "dec")
                self.assertEqual((ev["carrier"], ev["audit_ref"], ev["audit_sha256"],
                                  ev["key_id"], ev["decider"], ev["decided_at"], ev["by"]),
                                 ("console", ref, sha, hashlib.sha256(KEY.encode()).hexdigest()[:8],
                                  "ops_admin", fx2.AUDIT_TIME, "ops1"))
                self.assertFalse({"quote", "sid", "line", "card_seq"} & set(ev))
                if digest is not None:
                    self.assertEqual(ev["digest"], digest)
                self.assertEqual(ev.get("flags"), extra.get("flags"))
                self.assertEqual(si_events.validate(ev), [])
                res = self.check(R)
                for item in ("events.dec_console", "events.transitions"):
                    self.assertEqual(self.S(res, item), "PASS", (label, item, self.F(res, item)))
                self.assertEqual(self.MJ(R, "status")["console_pending"]["count"], 0)
                self.assertEqual(home_state(self.home), h0)

    def test_AT_233_1_2_vectors(self):
        self.new_home()
        kb = KEY.encode()
        self.assertEqual(hashlib.sha256(kb).hexdigest()[:8], "f076edf0")
        for name, (kind, ref, text, mac) in VECTORS.items():
            with self.subTest(name):
                obj = json.loads(text)
                self.assertEqual(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), text)
                self.assertEqual(hmac.new(kb, text.encode("utf-8"), hashlib.sha256).hexdigest(),
                    mac)
                subject = None if kind == "obs-add" else obj.get("prop") or obj.get("obs_id")
                path, sha = write_audit(self.home, kind=kind, ref=ref, subject=subject, body=text)
                got = consoleaudit.verify(path, [kb])
                self.assertEqual(got.sha, sha)
                self.assertEqual(sha, "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest())
                if name == "V2":
                    ascii_mac = hmac.new(kb, json.dumps(obj, ensure_ascii=True,
                                                        separators=(",", ":")).encode(),
                                         hashlib.sha256).hexdigest()
                    self.assertNotEqual(ascii_mac, mac)

    def _proposed_with(self, key="p"):
        R, p = self.base()
        return R, p, self.digest_of(R, p)

    def test_AT_233_1_E_1_audit_defects(self):
        R, p, dg = self._proposed_with()
        ref0 = new_uuid()
        good = lambda **o: fx2.body_decide(ref0, p, dg, "approve", **o)  # noqa: E731
        other = new_uuid()
        cases = [  # (標籤, 碼, 稽核檔參數 | None＝不存在, 環境)
            ("a", "AUDIT-FILE-MISSING", None, {}),
            *[("b", "AUDIT-SCHEMA", {"outer": o}, {}) for o in (
                {"x": 1}, {"mac": KeyError}, {"schema_rev": 2}, {"kind": 7}, {"body": {"a": 1}})],
            ("c1", "AUDIT-REF-MISMATCH", {"name": other}, {}),
            ("c2", "AUDIT-REF-MISMATCH", {"outer": {"audit_ref": other}}, {}),
            *[("d", "AUDIT-BODY-INVALID", {"body": b}, {}) for b in ("not json", "[1]", '"s"')],
            ("e1", "AUDIT-KIND-MISMATCH", {"body": {**good(), "kind": "obs-add"}}, {}),
            ("e2", "AUDIT-KIND-MISMATCH", {"body": {**good(), "kind": "purge"},
                                           "outer": {"kind": "purge"}}, {}),
            *[("f", "AUDIT-USER-FORMAT", {"body": good(user=u)}, {})
              for u in ("a;b", "x=y", "a b", "管理者", "a|b", "", "a" * 65)],
            ("f2", "AUDIT-USER-FORMAT", {"body": {k: v for k, v in good().items() if k != "user"}},
            {}),
            *[("g", "ROLE-NOT-ADMIN", {"body": {**good(), "role": r}}, {}) for r in ("USER",
            "admin", "")],
            ("g2", "ROLE-NOT-ADMIN", {"body": {k: v for k, v in good().items() if k != "role"}},
            {}),
            *[("h", "AUDIT-TIME-FORMAT", {"body": good(time=t)}, {}) for t in (
                "2026-10-21T09:15:30Z", "2026-10-21T09:15:30", "2026-10-21T09:15:30.5+08:00",
                "2026-10-21", "2026-13-40T25:61:61+08:00")],
            ("h2", "AUDIT-TIME-FORMAT", {"body": {k: v for k, v in good().items() if k != "time"}},
            {}),
            ("i1", "AUDIT-SUBJECT-MISMATCH", {"subject": fx.pid(901)}, {}),
            *[("j", "AUDIT-KEY-MISSING", {}, {"AUTOSDD_SI_AUDIT_KEY": v}) for v in ("", " , ,")],
            ("k", "AUDIT-KEY-UNKNOWN", {"key_id": "deadbeef"}, {}),
            ("l", "AUDIT-MAC-MISMATCH", {"mac": ("0" if True else "") * 64}, {}),
        ]
        for label, code, spec, env in cases:
            with self.subTest(label + code):
                self.new_home()
                s0, ev0 = fx.snap(R), (R / fx.EVL).read_bytes()
                if spec is not None:
                    kw = dict(spec)
                    body = kw.pop("body", good())
                    write_audit(self.home, kind="decide", ref=ref0,
                                subject=kw.pop("subject", p), body=body, **kw)
                h0 = home_state(self.home)
                call_ref = (spec or {}).get("name", ref0)  # 檔名即 --audit-ref；外層 audit_ref 不同
                with mock.patch.dict(os.environ, env):
                    rc, out, _ = self.M(R, "decide", p, "--carrier", "console", "--audit-ref",
                                        call_ref)
                self.guard(R, rc, out, [code], label)
                self.assert_untouched(R, s0, ev0, h0)
        with self.subTest("j-unset"):
            self.new_home()
            self.audit("decide", good(), p)
            env = {k: v for k, v in os.environ.items() if k != "AUTOSDD_SI_AUDIT_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                rc, out, _ = self.M(R, "decide", p, "--carrier", "console", "--audit-ref", ref0)
            self.guard(R, rc, out, ["AUDIT-KEY-MISSING"])

    def test_AT_233_1_E_2_duplicates_and_preconditions(self):
        def run(R, ident, body, **kw):
            return self.decide_c(R, ident, body, **kw)
        R, p, dg = self._proposed_with()
        ref = new_uuid()
        rc, out, err = run(R, p, fx2.body_decide(ref, p, dg, "approve"))
        self.assertEqual(rc, 0, out + err)
        rc, out, _ = self.M(R, "decide", p, "--carrier", "console", "--audit-ref", ref)
        self.guard(R, rc, out, ["AUDIT-REF-REUSED"], "a")
        # (b) 事件帳本已有 obs.add 的 audit_ref；(c) OBS 列標記 audit_ref 但無事件
        for label in ("b", "c"):
            R, p, dg = self._proposed_with()
            x = new_uuid()
            if label == "b":
                fx.append_events(R, [fx.obs_add_ev(audit_ref=x)])
            else:
                row = (f"| OBS-SI-{900 + 1} | 2026-10-21 09:15 +08:00 | c | s | tools/a.py:1 "
                       f"| bug | P3 | open | 面=產品;來源=人;回報者=a;"
                       f"carrier=console;audit_ref={x} |")
                fx.put(R, OBS_REL, fx.read(R, OBS_REL).rstrip("\n") + "\n" + row + "\n")
            rc, out, _ = run(R, p, fx2.body_decide(x, p, dg, "approve"))
            self.guard(R, rc, out, ["AUDIT-REF-REUSED"], label)
        R, p, dg = self._proposed_with()
        ref = new_uuid()
        self.audit("decide", fx2.body_decide(ref, p, dg, "approve"), p)
        for label, argv in (("d1", ["--kind", "approve"]), ("d2", ["--sid", fx2.new_sid()]),
                            ("d3", ["--line", "3"]), ("d4", ["--reason-class", "證據不足"])):
            with self.subTest(label):
                rc, out, err = self.M(R, "decide", p, "--carrier", "console", "--audit-ref", ref,
                    *argv)
                self.usage_error(rc, out, err, label)
        with self.subTest("d5"):
            self.usage_error(*self.M(R, "decide", p, "--carrier", "web", "--audit-ref", ref), "web")
        with self.subTest("d6"):
            self.usage_error(*self.M(R, "decide", p, "--carrier", "console"), "no ref")
        with self.subTest("d7"):
            self.usage_error(*self.M(R, "decide", p, "--carrier", "console", "--audit-ref",
                "12345"), "bad")
        with self.subTest("e"), mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, _ = self.M(R, "decide", p, "--carrier", "console", "--audit-ref", ref)
            self.guard(R, rc, out, ["UNATTENDED-REFUSED"])
        with self.subTest("f"):
            rc, out, _ = run(R, p, fx2.body_decide(new_uuid(), p, fx.H(33), "approve"))
            self.guard(R, rc, out, ["STALE-CARD"])
        with self.subTest("g"):
            R2, p2, dg2 = self._proposed_with()
            self.assertEqual(run(R2, p2, fx2.body_decide(new_uuid(), p2, dg2, "reject",
                                                         reason_class="證據不足", reason="x"))[0],
                                                         0)
            rc, out, _ = run(R2, p2, fx2.body_decide(new_uuid(), p2, dg2, "approve"))
            self.guard(R2, rc, out, ["PRECONDITION-STATE"])
        with self.subTest("h"):
            R3, p3 = self.base(route="handoff:T1")
            rc, out, _ = run(R3, p3, fx2.body_decide(new_uuid(), p3, self.digest_of(R3, p3),
                "approve"))
            self.guard(R3, rc, out, ["ROUTE-HANDOFF"])
        none = fx2.make_heldout(fx.new_dir("hn"), probes="none")
        for label, build, flags, code in (
                ("i", lambda: self.base("verified"), ["unverified_ack"], "PROMOTE-FORM-MISMATCH"),
                ("j", lambda: self.base("verified", heldout=none), [], "PROMOTE-FORM-MISMATCH")):
            with self.subTest(label):
                R4, p4 = build()
                rc, out, _ = run(R4, p4, fx2.body_decide(new_uuid(), p4, self.digest_of(R4, p4),
                                                         "promote", flags=flags))
                self.guard(R4, rc, out, [code], label)
        with self.subTest("k"):
            R5, p5 = self.base("verified")
            fx2.rewrite_event(R5, fx2.last_event(R5, "app.sandbox")["seq"], rollback_ok=False)
            rc, out, _ = run(R5, p5, fx2.body_decide(new_uuid(), p5, self.digest_of(R5, p5),
                "promote"))
            self.guard(R5, rc, out, ["PROMOTE-PREMISE-ROLLBACK"])
        R6, p6, dg6 = self._proposed_with()
        with self.subTest("l"):
            rc, out, _ = run(R6, p6, fx2.body_decide(new_uuid(), p6, dg6, "reject", reason="x"))
            self.guard(R6, rc, out, ["REASON-CLASS-MISSING"])
        with self.subTest("m"):
            rc, out, _ = run(R6, p6, fx2.body_decide(new_uuid(), p6, dg6, "reject",
                                                     reason_class="隨便", reason="x"))
            self.guard(R6, rc, out, ["REASON-CLASS-INVALID"])
        with self.subTest("n"):
            rc, out, _ = run(R6, p6, fx2.body_decide(new_uuid(), p6, None, "unblock"))
            self.guard(R6, rc, out, ["NOT-IN-COOLDOWN"])
        with self.subTest("o"):
            Rs = fx2.make_p2_repo(fx.new_dir("susp"), events=fx.sc_susp())
            rc, out, _ = run(Rs, fx.rid(2), fx2.body_decide(new_uuid(), fx.rid(2), None, "resume",
                                                            reason="r"))
            self.guard(Rs, rc, out, ["RUN-MISMATCH"])
        self.assertNotIn("CARD-NOT-ISSUED", out)

    def test_AT_233_1_E_3_vector_variants_and_key_hygiene(self):
        R, p, dg = self._proposed_with()
        seen = []

        def attempt(body_text, *, key=KEY, ring=KEY, mac=None, key_id=None):
            ref = json.loads(body_text)["audit_ref"] if body_text.startswith("{") else new_uuid()
            write_audit(self.home, kind="decide", ref=ref, subject=p, body=body_text, key=key,
                        mac=mac, key_id=key_id)
            with mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": ring}):
                res = self.M(R, "decide", p, "--carrier", "console", "--audit-ref", ref)
            seen.append(res)
            return res

        def v1():
            b = fx2.body_decide(new_uuid(), p, dg, "approve", user="admin")
            return b, fx2._jdump(b)
        b, text = v1()
        rc, out, _ = attempt(text.replace('"approve"', '"reject"'), mac=hmac.new(
            KEY.encode(), text.encode(), hashlib.sha256).hexdigest())
        self.guard(R, rc, out, ["AUDIT-MAC-MISMATCH"], "a")
        b, text = v1()
        rc, out, _ = attempt(text, key=KEY + "x",
            key_id=hashlib.sha256(KEY.encode()).hexdigest()[:8])
        self.guard(R, rc, out, ["AUDIT-MAC-MISMATCH"], "b")
        b, text = v1()
        rc, out, _ = attempt(text.replace("+08:00", "Z"), mac=hmac.new(
            KEY.encode(), text.encode(), hashlib.sha256).hexdigest())
        self.guard(R, rc, out, ["AUDIT-TIME-FORMAT"], "c")
        second = KEY + "-second"
        b, text = v1()
        rc, out, err = attempt(text, key=second, ring=f" {KEY} , {second} ")
        self.assertEqual(rc, 0, out + err)
        b, text = v1()
        rc, out, _ = attempt(text, key=second, ring=KEY)
        self.guard(R, rc, out, ["AUDIT-KEY-UNKNOWN"], "e")
        blob = "".join(o + e for _, o, e in seen) + (R / fx.EVL).read_text(encoding="utf-8")
        for secret in (KEY, second, f" {KEY} , {second} "):
            for i in range(len(secret) - 7):
                self.assertNotIn(secret[i:i + 8], blob, "金鑰洩漏")


class TestCheckConsoleDecision(ConsoleCase):
    def _decided(self, dkind="reject", **extra):
        R, p = self.base()
        ref = new_uuid()
        body = fx2.body_decide(ref, p, self.digest_of(R, p), dkind, **extra)
        rc, out, err = self.decide_c(R, p, body)
        self.assertEqual(rc, 0, out + err)
        return R, p, ref, body

    def test_AT_233_2_1_reconciliation_passes(self):
        for dkind, extra in (("approve", {}), ("reject", {"reason_class": "證據不足",
            "reason": "x"})):
            R, _, _, _ = self._decided(dkind, **extra)
            res = self.check(R)
            self.assertEqual((self.S(res, "events.dec_console"), res["_rc"]), ("PASS", 0))
        Rn, _ = self.base("verified", heldout=fx2.make_heldout(fx.new_dir("hn"), probes="none"))
        p = fx2.prop_event(Rn, [e for e in fx.EV(Rn) if e["kind"] == "prop"][0]["id"])["id"]
        body = fx2.body_decide(new_uuid(), p, self.digest_of(Rn, p), "promote",
                               flags=["unverified_ack"])
        self.assertEqual(self.decide_c(Rn, p, body)[0], 0)
        self.assertEqual(self.S(self.check(Rn), "events.dec_console"), "PASS")
        R4, _ = self.base()
        fx2.issue_card(R4, [e for e in fx.EV(R4) if e["kind"] == "prop"][0]["id"])
        self.assertEqual(self.S(self.check(R4), "events.dec_console"), "PASS")

    def test_AT_233_2_E_1_reconciliation_failures(self):
        def broken(label, change, code="CONSOLE-AUDIT-MISMATCH"):
            with self.subTest(label):
                R, p, ref, body = self._decided("reject", reason_class="證據不足", reason="x")
                change(R, p, ref, body)
                res = self.check(R)
                self.assertEqual(self.S(res, "events.dec_console"), "FAIL")
                self.assertIn(code, {c for _, c in self.F(res, "events.dec_console")})
                self.assertEqual(res["_rc"], 1)
        seq = lambda R: fx2.last_event(R, "dec")["seq"]  # noqa: E731
        broken("prop", lambda R, p, r, b: self._second_prop_swap(R, p, seq(R)))
        broken("digest", lambda R, p, r, b: fx2.rewrite_event(R, seq(R), digest=fx.H(55)))
        broken("dkind", lambda R, p, r, b: fx2.rewrite_event(R, seq(R), dkind="return"))
        broken("decider", lambda R, p, r, b: fx2.rewrite_event(R, seq(R), decider="someone"))
        broken("decided_at", lambda R, p, r, b: fx2.rewrite_event(
            R, seq(R), decided_at="2026-10-21T09:15:31+08:00"))
        broken("reason", lambda R, p, r, b: fx2.rewrite_event(R, seq(R), reason="另一個理由"))
        broken("reason_class", lambda R, p, r, b: fx2.rewrite_event(R, seq(R),
            reason_class="風險過高"))
        broken("sha", lambda R, p, r, b: write_audit(
            self.home, kind="decide", ref=r, subject=p, body={**b, "reason": "重簽"}))
        broken("mac", lambda R, p, r, b: self._flip_mac(r))
        for label, change, code, env in (
                ("missing", lambda R, p, r, b: (self.home / "console_audit" / f"{r}.json").unlink(),
                 "CONSOLE-AUDIT-MISSING", {}),
                ("nokey", lambda R, p, r, b: None, "CONSOLE-KEY-MISSING",
                {"AUTOSDD_SI_AUDIT_KEY": ""}),
                ("otherkey", lambda R, p, r, b: None, "CONSOLE-KEY-MISSING",
                 {"AUTOSDD_SI_AUDIT_KEY": "another-key-value-xyz"})):
            with self.subTest(label):
                R, p, ref, body = self._decided("reject", reason_class="證據不足", reason="x")
                change(R, p, ref, body)
                with mock.patch.dict(os.environ, env):
                    res = self.check(R)
                self.assertEqual((self.S(res, "events.dec_console"), res["overall"], res["_rc"]),
                                 ("NE", "PASS", 0))
                self.assertIn(code, {c for _, c in self.F(res, "events.dec_console")})
        with self.subTest("flags"):
            Rn, pn = self.base("verified", heldout=fx2.make_heldout(fx.new_dir("hn"),
                probes="none"))
            body = fx2.body_decide(new_uuid(), pn, self.digest_of(Rn, pn), "promote",
                                   flags=["unverified_ack"])
            self.assertEqual(self.decide_c(Rn, pn, body)[0], 0)
            ev = [e for e in fx.EV(Rn) if e["kind"] == "dec" and e["dkind"] == "promote"][-1]
            lines = (Rn / fx.EVL).read_text(encoding="utf-8").splitlines()
            out = []
            for ln in lines:
                o = json.loads(ln)
                if o["seq"] == ev["seq"]:
                    o.pop("flags")
                out.append(fx.dumps_line(o))
            (Rn / fx.EVL).write_text("\n".join(out) + "\n", encoding="utf-8")
            self.assertEqual(self.S(self.check(Rn), "events.dec_console"), "FAIL")

    def _flip_mac(self, ref):
        path = self.home / "console_audit" / f"{ref}.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["mac"] = ("1" if obj["mac"][0] == "0" else "0") + obj["mac"][1:]
        path.write_text(fx2._jdump(obj) + "\n", encoding="utf-8")

    def _second_prop_swap(self, R, p, seq):
        fx2.new_prop(R, target=fx2.OTHER)
        q = [e["id"] for e in fx.EV(R) if e["kind"] == "prop" and e["id"] != p][0]
        fx2.rewrite_event(R, seq, prop=q)


PROSE = "\n## 說明\n\n這是帳本之後的說明散文。\n"
ROW_RE = re.compile(r"^\| (OBS-SI-\d{3,}) \| (.*) \|$")


def obs_ledger(R: Path) -> bytes:
    return (R / OBS_REL).read_bytes()


def cells_of(row: str) -> list[str]:
    return [c.strip() for c in row.strip()[1:-1].split(" | ")]


class ObsCase(ConsoleCase):
    def obs_repo(self, *, prose: bool = True, extra=(), events=None, crlf: bool = False) -> Path:
        self.new_home()
        R = fx2.make_p2_repo(fx.new_dir("obs"), extra_obs=extra, events=events)
        text = fx.read(R, OBS_REL)
        if prose:
            text = text.rstrip("\n") + "\n" + PROSE
        if crlf:
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        fx.putb(R, OBS_REL, text.encode("utf-8"))
        fx.commit_all(R, "obs prep")
        return R

    def add_c(self, R, body, *, extra=(), name=None, **kw):
        self.audit("obs-add", body, None, name=name, **kw)
        return self.M(R, "obs-add", "--carrier", "console", "--audit-ref",
                      name or body["audit_ref"], *extra)

    def close_c(self, R, obs_id, disposition, *, ref=None, body=None, kind="obs-close"):
        ref = ref or new_uuid()
        body = body or fx2.body_obs_close(ref, obs_id, disposition)
        self.audit(kind, body, obs_id if kind == "obs-close" else None)
        return self.M(R, "obs-close", "--carrier", "console", "--audit-ref", ref, "--by",
            "ops1"), ref

    def top_row(self, R) -> str:
        rows = [ln for ln in obs_ledger(R).decode("utf-8").splitlines() if ROW_RE.match(ln)]
        return max(rows, key=lambda r: ROW_RE.match(r).group(1))

    def whole_check_pass(self, R):
        res = self.check(R)
        for item in res["_item"]:
            if item.startswith("row.") or item == "obs.console_audit":
                self.assertEqual(self.S(res, item), "PASS", (item, self.F(res, item)))
        self.assertEqual(res["overall"], "PASS")

    def zero_change(self, R, rc, out, codes, label=""):
        pass


class TestObsAdd(ObsCase):
    def test_AT_235_1_1_positive(self):
        R = self.obs_repo()
        ref = new_uuid()
        l0, head0 = obs_ledger(R), fx.head(R)
        body = fx2.body_obs_add(ref)
        self.audit("obs-add", body, None)
        self.assertIn(ref, {i["audit_ref"] for i in self.MJ(R,
            "status")["console_pending"]["items"]})
        rc, out, err = self.M(R, "obs-add", "--carrier", "console", "--audit-ref", ref, "--by",
            "ops1")
        self.assertEqual((rc, err), (0, ""), out)
        self.assertRegex(out, rf"^ok obs\.add seq=\d+ id=OBS-SI-011 audit_ref={ref}\n$")
        want = (f"| OBS-SI-011 | 2026-10-21 09:15 +08:00 | {body['context']} | {body['symptom']} | "
                f"{body['evidence']} | bug | P3 | open | "
                f"面=產品;來源=人;回報者=admin;carrier=console;audit_ref={ref} |")
        old_lines, new_lines = l0.decode().split("\n"), obs_ledger(R).decode().split("\n")
        last = max(i for i, ln in enumerate(old_lines) if ROW_RE.match(ln))
        self.assertEqual(new_lines, old_lines[:last + 1] + [want] + old_lines[last + 1:])
        ev = fx2.last_event(R, "obs.add")
        self.assertEqual(list(ev), ["seq", "t", "kind", "by", "obs", "audit_ref", "audit_sha256",
                                    "key_id", "decider", "carrier"])
        self.assertEqual((ev["obs"], ev["decider"], ev["carrier"], ev["by"]),
                         ("OBS-SI-011", "admin", "console", "ops1"))
        self.assertLessEqual(len(want.encode("utf-8")), 700)
        self.whole_check_pass(R)
        self.assertEqual(fx.head(R), head0)
        self.assertNotIn(ref, {i["audit_ref"] for i in self.MJ(R,
            "status")["console_pending"]["items"]})

    def test_AT_235_1_2_dry_run(self):
        R = self.obs_repo()
        ref = new_uuid()
        body = fx2.body_obs_add(ref)
        bf = fx.new_dir("bf").with_suffix(".json")
        bf.write_text(fx2._jdump(body), encoding="utf-8")
        nowhere = fx.new_dir("nowhere")  # 家目錄不存在
        env = {"AUTOSDD_SI_DIR": str(nowhere)}
        snap0 = fx.snap(R)
        no_key = {k: v for k, v in os.environ.items() if k != "AUTOSDD_SI_AUDIT_KEY"}
        with mock.patch.dict(os.environ, {**no_key, **env}, clear=True):
            rc, out, err = self.M(R, "obs-add", "--dry-run", "--body-file", bf)
            self.assertEqual((rc, err), (0, ""), out)
            self.assertIn("dry-run ok", out)
            self.assertIn("row_bytes=", out)
            self.assertIn("row_max_bytes=700", out)
            j = self.MJ(R, "obs-add", "--dry-run", "--body-file", bf)
            self.assertEqual(list(j), ["ok", "row", "row_bytes", "row_max_bytes", "findings"])
            self.assertEqual((j["ok"], j["findings"]), (True, []))
            import io
            with mock.patch("sys.stdin", mock.Mock(buffer=io.BytesIO(bf.read_bytes()))):
                self.assertEqual(self.M(R, "obs-add", "--dry-run", "--body-file", "-")[0], 0)
            nokey = {k: v for k, v in body.items() if k != "time"}
            bf2 = bf.with_name(bf.stem + "2.json")
            bf2.write_text(fx2._jdump(nokey), encoding="utf-8")
            j2 = self.MJ(R, "obs-add", "--dry-run", "--body-file", bf2)
            self.assertRegex(cells_of(j2["row"])[1], r"^\d{4}-\d\d-\d\d \d\d:\d\d [+-]\d\d:\d\d$")
        self.assertEqual(fx.snap(R), snap0)
        self.assertFalse(nowhere.exists())
        R2 = self.obs_repo()
        self.audit("obs-add", body, None)
        self.assertEqual(self.M(R2, "obs-add", "--carrier", "console", "--audit-ref", ref)[0], 0)
        real = self.top_row(R2)
        self.assertEqual(cells_of(j["row"])[1:], cells_of(real)[1:])
        self.assertEqual(cells_of(j["row"])[0], "OBS-SI-011")
        mods = imported_modules(["obs-add", "--dry-run", "--body-file", str(bf), "--repo", str(R)],
                                {**os.environ, **env})
        self.assertFalse(mods & FORBIDDEN, mods & FORBIDDEN)

    def test_AT_235_1_E_1_body_rules(self):
        R = self.obs_repo()
        self.assertEqual(self.M(R, "obs-add", "--dry-run", "--body-file", self._bf(R, {}))[0], 0)
        base = lambda **o: fx2.body_obs_add(new_uuid(), **o)  # noqa: E731
        calibrate = self._calibrate(R)
        table = [
            ("a", "PIPE-IN-FIELD", base(symptom="a|b")),
            ("b1", "FIELD-EMPTY", base(context="")), ("b2", "FIELD-EMPTY", base(context="  ")),
            ("c", "ENUM-CATEGORY", base(category="defect")),
            ("d", "ENUM-SEVERITY", base(severity="P5")),
            ("e", "FACE-INVALID", base(face="前端")),
            ("f", "EXPOSURE-REQUIRED", base(face="守衛")),
            ("g", "EXPOSURE-UNEXPECTED", base(exposure="a")),
            ("h1", "MARKS-EXTRA-KEY", base(marks_extra={"src": "x"})),
            ("h2", "MARKS-EXTRA-KEY", base(marks_extra={"x": "y"})),
            ("i", "REL-CONFLICT", base(corrects=fx.obs_id(1), marks_extra={"rel": "z"})),
            ("j", "CORRECTS-NOT-FOUND", base(corrects=fx.obs_id(700))),
            ("k", "COORD-NONE", base(evidence="沒有任何座標的一句話")),
            ("l", "CTRL-CHAR", base(symptom="含\t控制字元")),
            ("m", "GUARD-P12-NO-EXPOSURE", base(face="守衛", exposure="無", severity="P2")),
            ("o", "ROW-BYTES-OVER", base(symptom="s" * (calibrate + 1))),
        ]
        for label, code, body in table:
            with self.subTest(label):
                l0, e0 = obs_ledger(R), (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""
                rc, out, _ = self.add_c(R, body)
                self.guard(R, rc, out, [code], label)
                self.assertEqual((obs_ledger(R), (R / fx.EVL).read_bytes()
                                  if (R / fx.EVL).exists() else b""), (l0, e0))
        with self.subTest("n"):
            body = base(symptom="s" * calibrate)
            self.assertEqual(self.M(R, "obs-add", "--dry-run", "--body-file", self._bf(R, body))[0],
                0)
            self.assertEqual(self.add_c(R, body)[0], 0)
            self.assertEqual(len(self.top_row(R).encode("utf-8")), 700)
        with self.subTest("o-dry"):
            j = self.MJ(R, "obs-add", "--dry-run", "--body-file",
                        self._bf(R, base(symptom="s" * (calibrate + 1))))
            self.assertIn("ROW-BYTES-OVER", {f["code"] for f in j["findings"]})
        with self.subTest("p"):
            ref = new_uuid()
            self.audit("decide", fx2.body_decide(ref, fx.pid(1), V_DIGEST, "approve"), fx.pid(1))
            rc, out, _ = self.M(R, "obs-add", "--carrier", "console", "--audit-ref", ref)
            self.guard(R, rc, out, ["AUDIT-KIND-MISMATCH"])
        with self.subTest("q"):
            body = base()
            self.assertEqual(self.add_c(R, body)[0], 0)
            rc, out, _ = self.M(R, "obs-add", "--carrier", "console", "--audit-ref",
                body["audit_ref"])
            self.guard(R, rc, out, ["AUDIT-REF-REUSED"])
        with self.subTest("r"), mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, _ = self.add_c(R, base())
            self.guard(R, rc, out, ["UNATTENDED-REFUSED"])

    def _bf(self, R, body) -> Path:
        p = fx.new_dir("bf").with_suffix(".json")
        full = body if body else fx2.body_obs_add(new_uuid())
        p.write_text(fx2._jdump(full), encoding="utf-8")
        return p

    def _calibrate(self, R) -> int:
        """自我校準：回使新列恰為 700 位元組的 symptom 長度。"""
        n = 100
        j = self.MJ(R, "obs-add", "--dry-run", "--body-file",
                    self._bf(R, fx2.body_obs_add(new_uuid(), symptom="s" * n)))
        return n + (700 - j["row_bytes"])

    def test_AT_235_1_E_2_write_order_and_rollback(self):
        from lib.selfimproving import evwrite, obswrite
        with self.subTest("a"):
            R = self.obs_repo()
            l0, e0 = obs_ledger(R), (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""

            def boom():
                raise OSError("injected")
            with mock.patch.object(evwrite, "PAUSE_HOOK", boom):
                rc, out, err = self.add_c(R, fx2.body_obs_add(new_uuid()))
            self.assertNotEqual(rc, 0)
            self.assertEqual(obs_ledger(R), l0)
            self.assertEqual((R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b"", e0)
            self.assertEqual(self.check(R)["_rc"], 0)
        with self.subTest("b"):
            R = self.obs_repo()

            def boom_dirty():
                with (R / OBS_REL).open("ab") as fh:
                    fh.write("別人加的一行\n".encode())
                raise OSError("injected")
            with mock.patch.object(evwrite, "PAUSE_HOOK", boom_dirty):
                rc, out, err = self.add_c(R, fx2.body_obs_add(new_uuid()))
            self.assertNotEqual(rc, 0)
            self.assertIn("OBS-ORPHAN", err)
            self.assertIn("別人加的一行", obs_ledger(R).decode())
            res = self.check(R)
            self.assertEqual(self.S(res, "obs.console_audit"), "FAIL")
            self.assertIn("CONSOLE-EVENT-MISSING", {c for _, c in self.F(res, "obs.console_audit")})
        with self.subTest("c"):
            import concurrent.futures
            R = self.obs_repo()
            refs_ = [new_uuid(), new_uuid()]
            for r in refs_:
                self.audit("obs-add", fx2.body_obs_add(r), None)
            # 執行緒內的例外由 future.result() 重新拋出（pre-push 18 worker 下曾只見 KeyError）
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futs = {r: pool.submit(obswrite.add_console_row, R, r, "ops1") for r in refs_}
            results = {r: f.result() for r, f in futs.items()}
            self.assertEqual([results[r][0] for r in refs_], [0, 0], results)
            adds = [e for e in fx.EV(R) if e["kind"] == "obs.add"]
            self.assertEqual(len({e["obs"] for e in adds}), 2)
            ids = [ROW_RE.match(ln).group(1) for ln in obs_ledger(R).decode().splitlines()
                   if ROW_RE.match(ln)]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(self.check(R)["_rc"], 0)
        with self.subTest("d"):
            R = self.obs_repo(prose=False)

            def other_process():
                row = ("| OBS-SI-050 | 2026-10-21 10:00 +08:00 | 並行 | 並行症狀 | tools/a.py:1 "
                       "| bug | P3 | open | 面=流程;來源=人;回報者=x |")
                with (R / OBS_REL).open("ab") as fh:
                    fh.write((row + "\n").encode())
            ref = new_uuid()
            self.audit("obs-add", fx2.body_obs_add(ref), None)
            with mock.patch.object(obswrite, "PAUSE_HOOK", other_process):
                rc, out, err = self.M(R, "obs-add", "--carrier", "console", "--audit-ref", ref)
            self.assertEqual(rc, 0, out + err)
            self.assertEqual(fx2.last_event(R, "obs.add")["obs"], "OBS-SI-051")
            self.assertEqual(self.check(R)["_rc"], 0)
        self.assertEqual(list((self.home / "locks").glob("*.lock")), [])

    def test_AT_235_1_E_3_dynamic_purity(self):
        R = self.obs_repo()
        p = fx2.new_prop(R)
        env = dict(os.environ)
        bf = self._bf(R, {})
        readonly = [["check"], ["status"], ["scan"], *[["export", "--kind", k, "--json"] for k in (
            "observations", "events", "proposals", "runs", "status")], ["card", p],
            ["obs-add", "--dry-run", "--body-file", str(bf)]]
        for argv in readonly:
            with self.subTest(argv[0] + str(argv[1:2])):
                before = fx.snap(R)
                mods = imported_modules([*argv, "--repo", str(R)], env)
                self.assertFalse(mods & FORBIDDEN, (argv, mods & FORBIDDEN))
                self.assertEqual(fx.snap(R), before)
        ref = new_uuid()
        self.audit("obs-add", fx2.body_obs_add(ref), None)
        mods = imported_modules(["obs-add", "--carrier", "console", "--audit-ref", ref, "--repo",
                                 str(R)], env)
        self.assertIn("obswrite", mods)
        ref2 = new_uuid()
        self.audit("obs-close", fx2.body_obs_close(ref2, fx.obs_id(1), "decided：測試"),
            fx.obs_id(1))
        mods = imported_modules(["obs-close", "--carrier", "console", "--audit-ref", ref2, "--repo",
                                 str(R)], env)
        self.assertIn("obswrite", mods)
        mods = imported_modules(["run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by",
                                 "main", "--repo", str(R)], env)
        self.assertIn("writeverbs", mods)


def open_rows(first: int, n: int) -> list[list[str]]:
    """含中文字與連續空白症狀的 open 列（使「其餘位元組逐字不變」有牙）。"""
    return [[fx.obs_id(first + i), "2026-10-21 08:00 +08:00", "情境  含連續空白",
             "症狀  有中文  與連續空白", "tools/a.py:1", "bug", "P3", "open",
             "面=流程;來源=人;回報者=SA"] for i in range(n)]


class TestObsClose(ObsCase):
    def _forms(self, R, prop):
        return ["fixed@" + fx.head(R)[:12], fx.def_id(1), "deferred：等 P3 輪",
                "retired：docs/notes/old.md:3", "decided：掌舵者裁決不修", "merged@" + fx.obs_id(1),
                "proposed@" + prop]

    def test_AT_235_2_1_seven_terminal_forms(self):
        R = self.obs_repo(extra=open_rows(11, 7), crlf=True)
        prop = fx2.new_prop(R)
        fx.commit_all(R, "prop")
        forms = self._forms(R, prop)
        replaced = []
        real_replace = os.replace
        for i, disp in enumerate(forms):
            obs_id = fx.obs_id(11 + i)
            before = obs_ledger(R)
            ledger_dir = (R / OBS_REL).parent
            with mock.patch("os.replace", side_effect=lambda s, d: (replaced.append((s, d)),
                                                                     real_replace(s, d))[1]):
                (rc, out, err), ref = self.close_c(R, obs_id, disp)
            self.assertEqual((rc, err), (0, ""), out)
            self.assertRegex(out, rf"^ok obs\.close seq=\d+ id={obs_id} audit_ref={ref}\n$")
            after = obs_ledger(R)
            b_lines, a_lines = before.split(b"\n"), after.split(b"\n")
            self.assertEqual(len(b_lines), len(a_lines))
            diff = [k for k, (x, y) in enumerate(zip(b_lines, a_lines)) if x != y]
            self.assertEqual(len(diff), 1)
            self.assertEqual(b_lines[diff[0]].replace(b" | open | ", f" | {disp} | ".encode(), 1),
                             a_lines[diff[0]])
            ev = fx2.last_event(R, "obs.close")
            self.assertEqual(list(ev), ["seq", "t", "kind", "by", "obs", "audit_ref",
                "audit_sha256",
                                        "key_id", "decider", "carrier", "disposition"])
            self.assertEqual(ev["disposition"], disp)
            self.assertEqual([p for p in ledger_dir.iterdir() if p.name.endswith(".tmp")], [])
        mine = [(s, d) for s, d in replaced if str(d).endswith("Observation_Ledger.md")]
        self.assertEqual(len(mine), 7)
        self.assertTrue(all(Path(s).parent == (R / OBS_REL).parent for s, _ in mine))
        res = self.check(R)
        for item in ("history.row_mutated", "obs.console_audit"):
            self.assertEqual(self.S(res, item), "PASS", (item, self.F(res, item)))
        self.assertEqual(res["overall"], "PASS", [(i, self.F(res, i)) for i,
            v in res["_item"].items()
                                                  if v["status"] == "FAIL"])

    def _close_repo(self):
        events = [fx.run_open_ev(1), fx.skip_ev(1), fx.prop_ev(124, 1)]
        R = self.obs_repo(extra=open_rows(11, 3), events=events)
        arch = [fx.obs_id(902), "2026-10-20 08:00 +08:00", "封存", "封存列", "tools/a.py:1", "bug",
            "P3",
                "open", "面=流程;來源=人;回報者=SA"]
        fx.put(R, "docs/06_quality/SelfImproving_Observation_Ledger_archive_01.md",
               fx.render_ledger([arch]))
        fx.commit_all(R, "archive")
        return R

    def test_AT_235_2_E_1_preconditions(self):
        from lib.selfimproving import obswrite
        R = self._close_repo()
        target = fx.obs_id(11)
        raw_row = next(ln for ln in obs_ledger(R).decode().splitlines() if target in ln[:20])
        pad = 700 - (len(raw_row.encode()) - len(b"open")) - len("decided：".encode())
        table = [
            ("a", "OBS-NOT-FOUND", fx.obs_id(777), "decided：x"),
            ("b", "OBS-ARCHIVED", fx.obs_id(902), "decided：x"),
            ("c", "NOT-OPEN", fx.obs_id(2), "decided：x"),
            ("d", "NOT-OPEN", fx.obs_id(4), "decided：x"),
            ("e1", "DISPOSITION-INVALID", target, "open"),
            ("e2", "DISPOSITION-INVALID", target, "finished"),
            ("e3", "DISPOSITION-INVALID", target, "fixed@zzzz"),
            ("f1", "DISPOSITION-TEXT-MISSING", target, "deferred"),
            ("f2", "DISPOSITION-TEXT-MISSING", target, "retired：沒有座標"),
            ("g", "PIPE-IN-FIELD", target, "decided：a|b"),
            ("h1", "ROW-BYTES-OVER", target, "decided：" + "x" * (pad + 1)),
        ]
        for label, code, obs_id, disp in table:
            with self.subTest(label):
                l0 = obs_ledger(R)
                arch = R / "docs/06_quality/SelfImproving_Observation_Ledger_archive_01.md"
                a0 = arch.read_bytes()
                e0 = (R / fx.EVL).read_bytes()
                (rc, out, _), _ref = self.close_c(R, obs_id, disp)
                self.guard(R, rc, out, [code], label)
                self.assertEqual((obs_ledger(R), (R / fx.EVL).read_bytes()), (l0, e0))
                self.assertEqual([p.name for p in (R / OBS_REL).parent.iterdir()
                                  if p.name.endswith(".tmp")], [])
                self.assertEqual(arch.read_bytes(), a0)
        with self.subTest("h2"):
            (rc, out, err), _ = self.close_c(R, target, "decided：" + "x" * pad)
            self.assertEqual(rc, 0, out + err)
        with self.subTest("i"):
            ref = new_uuid()
            self.audit("obs-add", fx2.body_obs_add(ref), None)
            rc, out, _ = self.M(R, "obs-close", "--carrier", "console", "--audit-ref", ref)
            self.guard(R, rc, out, ["AUDIT-KIND-MISMATCH"])
        with self.subTest("j"):
            (rc, _, _), ref = self.close_c(R, fx.obs_id(12), "decided：x")
            self.assertEqual(rc, 0)
            rc, out, _ = self.M(R, "obs-close", "--carrier", "console", "--audit-ref", ref)
            self.guard(R, rc, out, ["AUDIT-REF-REUSED"])
        with self.subTest("k"), mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            (rc, out, _), _ = self.close_c(R, fx.obs_id(13), "decided：x")
            self.guard(R, rc, out, ["UNATTENDED-REFUSED"])
        with self.subTest("l"):
            def bump():
                raw = (R / OBS_REL).read_bytes()
                (R / OBS_REL).write_bytes(raw.replace("基線症狀 003".encode(),
                    "基線症狀 00X".encode(), 1))
            l0 = obs_ledger(R)
            with mock.patch.object(obswrite, "PAUSE_HOOK", bump):
                (rc, out, _), _ = self.close_c(R, fx.obs_id(13), "decided：x")
            self.guard(R, rc, out, ["LEDGER-CHANGED"])
            self.assertNotEqual(obs_ledger(R), l0)
            self.assertEqual(list((self.home / "locks").glob("*.lock")), [])

    def test_AT_235_2_E_2_write_failures(self):
        R = self.obs_repo(extra=open_rows(11, 1))
        target = fx.obs_id(11)
        real_replace, calls = os.replace, []

        def pick(label):
            def fake_fsync(fd):
                raise OSError("fsync injected")

            def fake_replace(s, d):
                if str(d).endswith("Observation_Ledger.md"):
                    calls.append(label)
                    raise PermissionError(13,
                        "denied") if label == "b" else OSError("replace injected")
                return real_replace(s, d)
            return fake_fsync, fake_replace
        for label in ("a", "b", "c"):
            with self.subTest(label):
                calls.clear()
                l0, e0 = obs_ledger(R), (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""
                fsync, replace = pick(label)
                with mock.patch("os.replace", side_effect=replace), \
                        mock.patch("os.fsync", side_effect=fsync if label == "a" else os.fsync):
                    (rc, out, err), _ = self.close_c(R, target, "decided：x")
                self.assertEqual(rc, 1, out + err)
                if label != "a":
                    self.assertEqual(len(calls), 1)
                self.assertEqual((obs_ledger(R), (R / fx.EVL).read_bytes()
                                  if (R / fx.EVL).exists() else b""), (l0, e0))
                self.assertEqual([p.name for p in (R / OBS_REL).parent.iterdir()
                                  if p.name.endswith(".tmp")], [])
                self.assertEqual(list((self.home / "locks").glob("*.lock")), [])
        (rc, out, err), _ = self.close_c(R, target, "decided：x")
        self.assertEqual(rc, 0, out + err)
        src = "".join(p.read_text(encoding="utf-8") for p in
                      (Path(fx.ROOT) / "tools/lib/selfimproving").glob("*.py"))
        self.assertNotIn("time.sleep", src)
        self.assertNotIn("while True", src)

    def test_AT_235_3_1_no_delete_or_renumber(self):
        import selfimproving
        verbs = set(selfimproving._build_parser()._subparsers._group_actions[0].choices)
        self.assertEqual(len(verbs), 23)
        self.assertEqual({v for v in verbs if "obs" in v}, {"obs-add", "obs-close"})
        R = self.obs_repo(extra=open_rows(11, 1))
        snap0, l0 = fx.snap(R), obs_ledger(R)
        for name in ("obs-delete", "obs-remove", "obs-rm", "obs-edit", "obs-update", "obs-renumber",
                     "obs-retire", "obs-purge", "obs-set"):
            with self.subTest(name):
                rc, out, err = self.M(R, name)
                self.assertEqual((rc, out), (3, ""))
                self.assertTrue(err.strip())
        self.assertEqual(fx.snap(R), snap0)
        rows0 = [ln for ln in l0.decode().splitlines() if ROW_RE.match(ln)]
        (rc, out, err), _ = self.close_c(R, fx.obs_id(11), "retired：docs/notes/old.md:3")
        self.assertEqual(rc, 0, out + err)
        rows1 = [ln for ln in obs_ledger(R).decode().splitlines() if ROW_RE.match(ln)]
        self.assertEqual(len(rows0), len(rows1))
        self.assertEqual([cells_of(r)[0] for r in rows0], [cells_of(r)[0] for r in rows1])
        self.assertEqual(cells_of(rows1[-1])[7], "retired：docs/notes/old.md:3")

    def test_AT_235_3_E_1_invariants(self):
        R = self.obs_repo(extra=open_rows(11, 3))

        def snapshot():
            return [cells_of(ln) for ln in obs_ledger(R).decode().splitlines() if ROW_RE.match(ln)]
        steps = [
            ("add", fx2.body_obs_add(new_uuid(), symptom="第一列"), 0),
            ("add", fx2.body_obs_add(new_uuid(), symptom="第二列"), 0),
            ("add-corrects", fx2.body_obs_add(new_uuid(), symptom="更正列", corrects=fx.obs_id(11)),
            0),
            ("close", fx.obs_id(11), 0), ("close", fx.obs_id(12), 0), ("close", fx.obs_id(13), 0),
            ("close", fx.obs_id(11), 1), ("add", fx2.body_obs_add(new_uuid(), symptom="a|b"), 1),
        ]
        prev = snapshot()
        for kind, arg, want in steps:
            with self.subTest(kind + str(arg)[:14]):
                if kind.startswith("add"):
                    rc = self.add_c(R, arg)[0]
                else:
                    rc = self.close_c(R, arg, "decided：x")[0][0]
                self.assertEqual(rc, want)
                cur = snapshot()
                self.assertGreaterEqual(len(cur), len(prev))
                ids = [r[0] for r in cur]
                self.assertEqual(ids, sorted(set(ids)))
                old = {r[0]: r for r in prev}
                for r in cur:
                    if r[0] in old:
                        o = old[r[0]]
                        self.assertEqual([r[i] for i in (0, 1, 2, 3, 4, 5, 6, 8)],
                                         [o[i] for i in (0, 1, 2, 3, 4, 5, 6, 8)])
                        self.assertTrue(r[7] == o[7] or o[7] == "open")
                prev = cur
        self.assertNotEqual(self.S(self.check(R), "history.row_mutated"), "FAIL")


class TestConsoleObsRules(ObsCase):
    def test_AT_235_4_1_eligible_accounts(self):
        R = self.obs_repo()
        for user in ("a", "Admin.Ops-01_x", "a" * 64, "0123456789"):
            with self.subTest(user[:8]):
                body = fx2.body_obs_add(new_uuid(), user=user)
                rc, out, err = self.add_c(R, body)
                self.assertEqual(rc, 0, out + err)
                marks = cells_of(self.top_row(R))[8].split(";")
                self.assertEqual(len(marks), 5)
                self.assertIn(f"回報者={user}", marks)
                self.assertEqual(fx2.last_event(R, "obs.add")["decider"], user)
        res = self.check(R)
        self.assertEqual((self.S(res, "row.markers"), self.S(res, "row.provenance")), ("PASS",
            "PASS"))

    def test_AT_235_4_E_1_ineligible_accounts(self):
        R = self.obs_repo()
        l0 = obs_ledger(R)
        ev0 = (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""
        for user in ("a;面=守衛", "a=b", "a b", "a|b", "a" * 65, "管理者", ""):
            with self.subTest("user" + user[:6]):
                rc, out, _ = self.add_c(R, fx2.body_obs_add(new_uuid(), user=user))
                self.guard(R, rc, out, ["AUDIT-USER-FORMAT"])
        for role in ("OPERATOR", "VIEWER", "admin", None):
            with self.subTest("role" + str(role)):
                body = fx2.body_obs_add(new_uuid())
                body = {**body, "role": role} if role else {k: v for k,
                    v in body.items() if k != "role"}
                rc, out, _ = self.add_c(R, body)
                self.guard(R, rc, out, ["ROLE-NOT-ADMIN"])
        self.assertEqual((obs_ledger(R),
            (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""),
                         (l0, ev0))

    def test_AT_235_5_1_pending_and_reconcile(self):
        events = [fx.run_open_ev(1), fx.skip_ev(1)]
        R = self.obs_repo(events=events)
        p = fx2.new_prop(R, target=fx2.OTHER)
        before_keys = list(self.MJ(R, "status"))[:13]
        add_ref, close_ref, dec_ref = new_uuid(), new_uuid(), new_uuid()
        self.audit("obs-add", fx2.body_obs_add(add_ref), None)
        self.audit("obs-close", fx2.body_obs_close(close_ref, fx.obs_id(1), "decided：測試"),
                   fx.obs_id(1))
        self.audit("decide", fx2.body_decide(dec_ref, p, self.digest_of(R, p), "approve"), p)
        box = self.home / "console_audit"
        (box / "notes.json").write_text("{}", encoding="utf-8")
        (box / f"{new_uuid()}.json").write_text("not json", encoding="utf-8")
        pend = self.MJ(R, "status")["console_pending"]
        self.assertEqual((pend["status"], pend["count"]), ("read", 4))
        refs_ = [i["audit_ref"] for i in pend["items"]]
        self.assertEqual(refs_, sorted(refs_))
        self.assertEqual(sorted(str(i["kind"]) for i in pend["items"]),
                         sorted(["decide", "obs-add", "obs-close", "None"]))
        for verb, ref in (("obs-add", add_ref), ("obs-close", close_ref)):
            got = self.M(R, verb, "--carrier", "console", "--audit-ref", ref)
            self.assertEqual(got[0], 0, got)
        self.assertEqual(self.M(R, "decide", p, "--carrier", "console", "--audit-ref", dec_ref)[0],
            0)
        st = self.MJ(R, "status")
        self.assertEqual((st["console_pending"]["count"], list(st)[:13]), (1, before_keys))
        res = self.check(R)
        for item in ("obs.console_audit", "events.dec_console"):
            self.assertEqual(self.S(res, item), "PASS", (item, self.F(res, item)))

    def _added(self):
        R = self.obs_repo()
        ref = new_uuid()
        body = fx2.body_obs_add(ref)
        self.audit("obs-add", body, None)
        self.assertEqual(self.M(R, "obs-add", "--carrier", "console", "--audit-ref", ref)[0], 0)
        return R, ref, body

    def test_AT_235_5_E_1_reconciliation_gaps(self):
        def item(R, **env):
            with mock.patch.dict(os.environ, env):
                return self.check(R)
        with self.subTest("a"):
            R, ref, _ = self._added()
            fx2.drop_events(R, "obs.add")
            res = item(R)
            self.assertEqual((self.S(res, "obs.console_audit"),
                              {c for _, c in self.F(res, "obs.console_audit")}),
                             ("FAIL", {"CONSOLE-EVENT-MISSING"}))
        with self.subTest("b"):
            R, _, _ = self._added()
            fx.append_events(R, [fx.obs_close_ev(obs=fx.obs_id(1), audit_ref=new_uuid())])
            res = item(R)
            self.assertIn("CONSOLE-CLOSE-NOT-APPLIED", {c for _, c in self.F(res,
                "obs.console_audit")})
        for label, change in (
                ("c", lambda R, ref, b: write_audit(self.home, kind="obs-add", ref=ref,
                subject=None,
                                                    body={**b, "symptom": "被改過的症狀"})),
                ("d", lambda R, ref, b: write_audit(self.home, kind="obs-add", ref=ref,
                subject=None,
                                                    body={**b, "user": "someone"})),
                ("h", lambda R, ref, b: self._flip(ref))):
            with self.subTest(label):
                R, ref, body = self._added()
                change(R, ref, body)
                res = item(R)
                self.assertEqual((self.S(res, "obs.console_audit"),
                                  {c for _, c in self.F(res, "obs.console_audit")}),
                                 ("FAIL", {"CONSOLE-AUDIT-MISMATCH"}))
        for label, prep, env, code in (
                ("e", lambda R, ref: (self.home / "console_audit" / f"{ref}.json").unlink(), {},
                 "CONSOLE-AUDIT-MISSING"),
                ("f", lambda R, ref: None, {"AUTOSDD_SI_AUDIT_KEY": ""}, "CONSOLE-KEY-MISSING"),
                ("g", lambda R, ref: None, {"AUTOSDD_SI_AUDIT_KEY": "other-key-xyz"},
                 "CONSOLE-KEY-MISSING")):
            with self.subTest(label):
                R, ref, _ = self._added()
                prep(R, ref)
                res = item(R, **env)
                self.assertEqual((self.S(res, "obs.console_audit"), res["overall"], res["_rc"]),
                                 ("NE", "PASS", 0))
                self.assertIn(code, {c for _, c in self.F(res, "obs.console_audit")})
        marks = {
            "i": (lambda m, ref: m.replace(f";audit_ref={ref}", ""), "row.markers",
            "CONSOLE-MARK-PAIR"),
            "j": (lambda m, ref: m.replace(";carrier=console", ""), "row.markers",
            "CONSOLE-MARK-PAIR"),
            "l": (lambda m, ref: m.replace("carrier=console", "carrier=web"), "row.markers",
            "MARK-VALUE"),
            "m": (lambda m, ref: m.replace(ref, "not-a-uuid"), "row.markers", "MARK-VALUE")}
        for label, (edit, name, code) in marks.items():
            with self.subTest(label):
                R, ref, _ = self._added()
                text = obs_ledger(R).decode()
                new_row = self.top_row(R)
                edited = new_row[:-2] if False else new_row
                text = text.replace(new_row, new_row.replace(
                    cells_of(new_row)[8], edit(cells_of(new_row)[8], ref)))
                (R / OBS_REL).write_bytes(text.encode())
                self.assertIn(code, {c for _, c in self.F(item(R), name)})
                del edited
        with self.subTest("k"):
            R, ref, _ = self._added()
            row = self.top_row(R)
            dup = row.replace(cells_of(row)[0], "OBS-SI-" + f"{int(cells_of(row)[0][-3:]) + 1:03d}")
            fx.put(R, OBS_REL, obs_ledger(R).decode().replace(row, row + "\n" + dup))
            found = [(s, c) for s, c in self.F(item(R), "row.markers") if c == "CONSOLE-AUDIT-DUP"]
            self.assertEqual([s for s, _ in found], [cells_of(dup)[0]])
        with self.subTest("n"):
            R = self.obs_repo(extra=open_rows(11, 1))
            (rc, out, err), ref = self.close_c(R, fx.obs_id(11), "decided：甲")
            self.assertEqual(rc, 0, out + err)
            fx.put(R, OBS_REL, obs_ledger(R).decode().replace("decided：甲", "decided：乙"))
            res = item(R)
            self.assertIn("CONSOLE-AUDIT-MISMATCH", {c for _, c in self.F(res,
                "obs.console_audit")})
        with self.subTest("home"):
            R, _, _ = self._added()
            with mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(fx.new_dir("absent"))}):
                self.assertEqual(self.MJ(R, "status")["console_pending"],
                                 {"status": "NOT-EVALUABLE", "reason": "home-unavailable"})

    def _flip(self, ref):
        path = self.home / "console_audit" / f"{ref}.json"
        obj = json.loads(path.read_text(encoding="utf-8"))
        obj["mac"] = ("1" if obj["mac"][0] == "0" else "0") + obj["mac"][1:]
        path.write_text(fx2._jdump(obj) + "\n", encoding="utf-8")


class TestExportStatus(ObsCase):
    COORDS = [("tools/lib/selfimproving/fold.py:10", ["SelfImproving"]),
              ("AutoClaude/tests/a.py:3", ["AutoClaude"]), ("AISDLC_SDD/x/y.md:1", ["AISDLC_SDD"]),
              ("AgentConsole/frontend/z.tsx:9", ["AgentConsole"]), ("docs/notes/demo.md:2",
              ["根層"]),
              ("AutoClaude/a.py:1、AgentConsole/b.ts:2", ["AutoClaude", "AgentConsole"]),
              ("`git status` rc=0", ["未分類"]), ("autoclaude/tests/a.py:3", ["根層"])]

    def test_AT_240_12_1_buckets_and_pending(self):
        from lib.selfimproving import scan
        rows = [[fx.obs_id(11 + i), "2026-10-21 08:00 +08:00", "c", "s", ev, "bug", "P3", "open",
                 "面=流程;來源=人;回報者=SA"] for i, (ev, _) in enumerate(self.COORDS)]
        rows.append([fx.obs_id(40), "壞列"])
        R = self.obs_repo(extra=rows, prose=False)
        obj = self.MJ(R, "export", "--kind", "observations")
        self.assertEqual(obj["schema_rev"], 1)
        items = {i["id"]: i for i in obj["items"] if "id" in i}
        for k, (ev, want) in enumerate(self.COORDS):
            it = items[fx.obs_id(11 + k)]
            self.assertEqual(list(it)[-3:], ["marks_kv", "line", "buckets"])
            self.assertEqual(it["buckets"], want, ev)
        bad = [i for i in obj["items"] if i.get("valid") is False]
        self.assertTrue(bad and all("buckets" not in i for i in bad))
        self.assertEqual(scan.bucket_of("autoclaude/tests/a.py"), "根層")
        keys = list(self.MJ(R, "status"))
        self.assertEqual((keys[-2], keys[-1]), ("console_pending", "measure"))
        self.assertEqual(len(keys), 15)
        st = self.MJ(R, "export", "--kind", "status")["items"][0]
        self.assertEqual(list(st)[-1], "measure")
        self.assertEqual(st["console_pending"], {"status": "NOT-EVALUABLE",
                                                 "reason": "export-reads-no-home"})

    def test_AT_240_12_E_1_export_reads_no_home(self):
        import builtins
        import io
        R = self.obs_repo()
        mark = f"SENTINEL-HOME-{new_uuid()}"
        ref = new_uuid()
        write_audit(self.home, kind="obs-add", ref=ref, subject=None,
                    body={**fx2.body_obs_add(ref), "symptom": mark})
        for sub in ("heldout", "sandbox", "research"):
            (self.home / sub).mkdir(exist_ok=True)
            (self.home / sub / "x.txt").write_text(mark, encoding="utf-8")
        seen: list[str] = []

        def spy(real):
            def wrapper(path, *a, **k):
                seen.append(str(path))
                return real(path, *a, **k)
            return wrapper
        real = (builtins.open, io.open, os.scandir, os.listdir)

        def recording():
            return mock.patch.multiple("os", scandir=spy(real[2]), listdir=spy(real[3])), \
                mock.patch("builtins.open", spy(real[0])), mock.patch("io.open", spy(real[1]))

        def run(argv):
            seen.clear()
            ctx = recording()
            with ctx[0], ctx[1], ctx[2]:
                got = self.M(R, *argv)
            return got, [p for p in seen if str(self.home) in p]
        for kind in ("observations", "events", "proposals", "runs", "status"):
            for flag in ("--json",):
                (rc, out, err), in_home = run(["export", "--kind", kind, flag])
                self.assertEqual(rc, 0, err)
                self.assertNotIn(mark, out)
                self.assertEqual(in_home, [], kind)
        (rc, out, err), in_home = run(["status", "--json"])
        self.assertEqual(rc, 0, err)
        self.assertNotIn(mark, out)
        self.assertTrue(all("console_audit" in p or p.rstrip("\\/").endswith(self.home.name)
                            for p in in_home), in_home)
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(fx.new_dir("absent"))}):
            self.assertEqual(self.M(R, "export", "--kind", "runs", "--json")[0], 0)
            self.assertEqual(self.MJ(R, "status")["console_pending"],
                             {"status": "NOT-EVALUABLE", "reason": "home-unavailable"})


class TestPreWriteGuards(ObsCase):
    """P3 D12（承接 DEF-200-568）：Console 載體三動詞的寫入前判準（TCS-P3 R136；AT-340-10 系）。

    受測：`tools/lib/selfimproving/consoleaudit.py` 的 `body_guard` 與其三個呼叫點（`decwrite`、
    `obsrows`、`obswrite`）；`events.dec_key_problems` 與 `check` 的 `dec` 判準同源。
    """

    def ev_bytes(self, R) -> bytes:
        return (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""

    def home_minus(self, ref) -> dict:
        return {k: v for k, v in home_state(self.home).items() if k != f"{ref}.json"}

    def snapshot(self, R) -> tuple:
        status = {i["id"]: i["status"] for i in self.check(R)["items"]}
        return (self.ev_bytes(R), obs_ledger(R), home_state(self.home), status)

    def guarded(self, R, call, codes, snap0, label=""):
        """呼叫一次被拒收的動詞：rc 1、碼恰為 `codes`、草稿列、零殘留、check 仍綠。"""
        rc, out, err = call()
        self.guard(R, rc, out, codes, label)
        self.assertEqual((self.ev_bytes(R), obs_ledger(R)), snap0[:2], label)
        self.assertEqual({i["id"]: i["status"] for i in self.check(R)["items"]}, snap0[3], label)

    def proposed_repo(self, state="proposed", **kw):
        self.new_home()
        R = fx2.make_p2_repo(fx.new_dir("pw"))
        p = fx2.drive_to(R, state, **kw)
        return R, p

    def decide_call(self, R, p, dkind, **kw):
        ref = new_uuid()
        body = fx2.body_decide(ref, p, self.digest_of(R, p), dkind, **kw)
        return lambda: self.decide_c(R, p, body)

    def test_AT_340_10_1_valid_audit_files_are_still_booked(self):
        R = self.obs_repo()
        p1 = fx2.drive_to(R, "proposed", target=fx2.DEMO)
        p2 = fx2.drive_to(R, "proposed", target=fx2.OTHER)
        fx.commit_all(R, "props")
        l0, n0 = obs_ledger(R).decode("utf-8"), len(fx.EV(R))
        rc, out, err = self.decide_call(R, p1, "approve")()
        self.assertEqual(rc, 0, out + err)
        rc, out, err = self.decide_call(R, p2, "reject", reason_class="證據不足", reason="a")()
        self.assertEqual(rc, 0, out + err)
        ref_add = new_uuid()
        body = fx2.body_obs_add(ref_add, face="守衛", exposure="a", marks_extra={"根因": "docs/x"})
        rc, out, err = self.add_c(R, body)
        self.assertEqual(rc, 0, out + err)
        (rc, out, err), ref_close = self.close_c(R, fx.obs_id(1), "decided：掌舵者裁決，已修復")
        self.assertEqual(rc, 0, out + err)
        new = fx.EV(R)[n0:]
        self.assertEqual([e["kind"] for e in new], ["dec", "dec", "obs.add", "obs.close"])
        self.assertEqual((new[1]["dkind"], new[1]["reason"]), ("reject", "a"))
        self.assertFalse({"reason", "flags"} & set(new[0]))
        l1 = obs_ledger(R).decode("utf-8")
        old_rows, new_rows = l0.splitlines(), l1.splitlines()
        added = [r for r in new_rows if r not in old_rows]
        marks = [r for r in added if f"audit_ref={ref_add}" in r]
        self.assertEqual(len(marks), 1)
        self.assertIn("carrier=console", marks[0])
        res = self.check(R)
        self.assertEqual(res["overall"], "PASS")
        for item in ("events.structure", "events.dec_console", "obs.console_audit"):
            self.assertEqual(self.S(res, item), "PASS", item)
        self.assertIn(ref_close, "".join(e.get("audit_ref", "") for e in new))

    def test_AT_340_10_E_1_control_characters_are_refused_before_writing(self):
        R, p = self.proposed_repo()
        R2 = self.obs_repo()
        variants = []
        for ch in ("\n", "\r", "\x00", "\x1f", "\t"):
            variants.append((f"decide{ord(ch)}", R, lambda ch=ch: self.decide_call(
                R, p, "reject", reason_class="證據不足", reason=f"a{ch}b")()))
        specs = {"context": "\n", "symptom": "\r", "evidence": "\x00"}
        for key, ch in specs.items():
            body = fx2.body_obs_add(new_uuid(), **{key: f"a{ch}b"})
            variants.append((f"add-{key}", R2, lambda body=body: self.add_c(R2, body)))
        body = fx2.body_obs_add(new_uuid(), face="守衛", exposure="a\nb")
        variants.append(("add-exposure", R2, lambda body=body: self.add_c(R2, body)))
        body = fx2.body_obs_add(new_uuid(), marks_extra={"根因": "a\nb"})
        variants.append(("add-extra", R2, lambda body=body: self.add_c(R2, body)))
        snaps = {id(R): self.snapshot(R), id(R2): self.snapshot(R2)}
        for label, repo, call in variants:
            with self.subTest(label):
                self.guarded(repo, call, {"CTRL-CHAR"}, snaps[id(repo)], label)
                self.assertEqual(self.snapshot(repo)[:2], snaps[id(repo)][:2])
        Rc, pc = self.proposed_repo()
        rc, out, err = self.decide_call(Rc, pc, "reject", reason_class="證據不足",
                                        reason="a b")()
        self.assertEqual(rc, 0, out + err)
        Rd = self.obs_repo()
        rc, out, err = self.add_c(Rd, fx2.body_obs_add(new_uuid(), context="a b"))
        self.assertEqual(rc, 0, out + err)

    def test_AT_340_10_E_2_keys_the_dkind_does_not_take_are_refused(self):
        def rej(R, p):
            return self.decide_call(R, p, "reject", reason_class="證據不足", reason="x",
                                    flags=["x"])

        cases = []
        R, p = self.proposed_repo()
        cases += [("a", R, self.decide_call(R, p, "approve", reason="x"), "EVENT-KEY-UNKNOWN"),
                  ("b", R, self.decide_call(R, p, "approve", flags=["unverified_ack"]),
                   "EVENT-KEY-UNKNOWN"),
                  ("c", R, rej(R, p), "EVENT-KEY-UNKNOWN"),
                  ("d", R, self.decide_call(R, p, "return", reason_class="證據不足", reason="x",
                                            flags=["unverified_ack"]), "EVENT-KEY-UNKNOWN")]
        Rh, ph = self.proposed_repo(route="handoff:T1")
        cases.append(("e", Rh, self.decide_call(Rh, ph, "ack-handoff", reason="x"),
                      "EVENT-KEY-UNKNOWN"))
        Rv, pv = self.proposed_repo("verified")
        cases.append(("f", Rv, self.decide_call(Rv, pv, "promote", reason="x"),
                      "EVENT-KEY-UNKNOWN"))
        cases.append(("h", Rv, self.decide_call(Rv, pv, "promote", flags=["x"]), "EVENT-TYPE"))
        Ru, pu = self.proposed_repo()
        rc, out, err = self.decide_call(Ru, pu, "reject", reason_class="證據不足", reason="x")()
        self.assertEqual(rc, 0, out + err)
        cases.append(("g", Ru, self.decide_call(Ru, pu, "unblock", reason="x"),
                      "EVENT-KEY-UNKNOWN"))
        for label, repo, call, code in cases:
            with self.subTest(label):
                snap0 = self.snapshot(repo)
                self.guarded(repo, call, {code}, snap0, label)
        Rw, pw = self.proposed_repo()
        rc, out, err = self.decide_call(Rw, pw, "approve", flags=[])()
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.check(Rw)["overall"], "PASS")
        rc, out, err = self.decide_call(Rv, pv, "promote")()
        self.assertEqual(rc, 0, out + err)
        events = {"approve": (Rw, "reason", "x", "EVENT-KEY-UNKNOWN"),
                  "promote": (Rv, "flags", ["x"], "EVENT-TYPE")}
        for dkind, (repo, key, value, code) in events.items():
            copy = fx.new_dir("cp")
            shutil.copytree(repo, copy)
            ev = next(e for e in reversed(fx.EV(copy)) if e["kind"] == "dec"
                      and e["dkind"] == dkind)
            fx2.rewrite_event(copy, ev["seq"], **{key: value})
            res = self.check(copy)
            self.assertEqual(self.S(res, "events.structure"), "FAIL")
            self.assertEqual({c for _, c in self.F(res, "events.structure")}, {code})

    def test_AT_340_10_E_3_empty_reasons_are_refused(self):
        specs = []
        R, p = self.proposed_repo()
        specs += [("a", R, p, "reject", {"reason_class": "證據不足", "reason": ""}),
                  ("c", R, p, "return", {"reason_class": "證據不足", "reason": ""})]
        Rv, pv = self.proposed_repo("verified")
        specs.append(("b", Rv, pv, "decline-promote", {"reason_class": "風險過高", "reason": ""}))
        Rp, pp = self.proposed_repo("promoted")
        specs.append(("d", Rp, pp, "rollback", {"reason": ""}))
        self.new_home()
        Rs = fx2.make_p2_repo(fx.new_dir("susp"), events=fx.sc_susp())
        specs.append(("e", Rs, fx.rid(1), "resume", {"reason": ""}))
        for label, repo, ident, dkind, kw in specs:
            with self.subTest(label):
                ref = new_uuid()
                digest = None if dkind in ("rollback", "resume") else self.digest_of(repo, ident)
                body = fx2.body_decide(ref, ident, digest, dkind, **kw)
                snap0 = self.snapshot(repo)
                self.guarded(repo, lambda: self.decide_c(repo, ident, body), {"REASON-EMPTY"},
                             snap0, label)
        ref = new_uuid()
        body = fx2.body_decide(ref, p, self.digest_of(R, p), "reject", reason_class="證據不足")
        rc, out, err = self.decide_c(R, p, body)
        self.rejected(rc, out, {"AUDIT-BODY-INVALID"})
        Rx, px = self.proposed_repo()
        rc, out, err = self.decide_call(Rx, px, "reject", reason_class="證據不足", reason="a")()
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(fx2.last_event(Rx, "dec")["reason"], "a")

    def test_AT_340_10_E_4_disposition_with_a_newline_or_a_bad_first_word(self):
        R = self.obs_repo()
        sha12 = fx.head(R)[:12]
        ox = fx.obs_id(1)
        snap0 = self.snapshot(R)
        cases = {"a": "decided：甲\n乙", "b": "decided：甲\r\n乙", "c": "decided：甲\n",
                 "d": f"fixed@{sha12}\n文字", "e": "bogus", "f": "open"}
        for label, disp in cases.items():
            with self.subTest(label):
                self.guarded(R, lambda disp=disp: self.close_c(R, ox, disp)[0],
                             {"DISPOSITION-INVALID"}, snap0, label)
        with self.subTest("g"):
            self.guarded(R, lambda: self.close_c(R, ox, "decided：甲\t乙")[0], {"CTRL-CHAR"},
                         snap0, "g")

    def test_AT_340_10_E_5_rejected_files_leave_no_trace(self):
        R = self.obs_repo()
        ox = fx.obs_id(1)
        l0, e0 = obs_ledger(R), self.ev_bytes(R)
        a1_ref, a3_ref = new_uuid(), new_uuid()
        body1 = fx2.body_obs_close(a1_ref, ox, "decided：甲\n乙")
        self.audit("obs-close", body1, ox)
        rc, out, err = self.M(R, "obs-close", "--carrier", "console", "--audit-ref", a1_ref)
        self.assertEqual(rc, 1, out + err)
        self.assertEqual((obs_ledger(R), self.ev_bytes(R)), (l0, e0))
        rc, out, err = self.add_c(R, fx2.body_obs_add(a3_ref, symptom="a\nb"))
        self.assertEqual(rc, 1, out + err)
        self.assertEqual((obs_ledger(R), self.ev_bytes(R)), (l0, e0))
        text = obs_ledger(R).decode("utf-8") + self.ev_bytes(R).decode("utf-8")
        self.assertNotIn(a1_ref, text)
        self.assertNotIn(a3_ref, text)
        res = self.check(R)
        self.assertEqual(self.S(res, "history.row_mutated"), "PASS")
        self.assertIn(self.S(res, "obs.console_audit"), ("PASS", "NE"))
        self.assertEqual(res["overall"], "PASS")
        (rc, out, err), _ = self.close_c(R, ox, "decided：掌舵者裁決，已修復")
        self.assertEqual(rc, 0, out + err)
        old, new = l0.decode("utf-8").splitlines(), obs_ledger(R).decode("utf-8").splitlines()
        self.assertEqual(len(old), len(new))
        diff = [(a, b) for a, b in zip(old, new) if a != b]
        self.assertEqual(len(diff), 1)
        self.assertEqual(cells_of(diff[0][0])[:7], cells_of(diff[0][1])[:7])
        self.assertEqual(cells_of(diff[0][1])[7], "decided：掌舵者裁決，已修復")
        self.assertEqual([e["kind"] for e in fx.EV(R)[len(e0.splitlines()):]], ["obs.close"])
        self.assertEqual(self.check(R)["overall"], "PASS")


FORBIDDEN = {"obswrite", "decwrite", "sandbox", "promote", "runner", "verify", "fetch", "research",
             "writeverbs"}


def imported_modules(argv, env) -> set[str]:
    """以子行程 `python -X importtime tools/selfimproving.py <argv>` 取 `selfimproving.<名>`
    的模組名。"""
    import subprocess
    import sys
    cp = subprocess.run([sys.executable, "-X", "importtime",
        str(fx.ROOT / "tools/selfimproving.py"),
                         *argv], capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env={**env, **fx.hermetic(), "PYTHONUTF8": "1"})
    names = set()
    for ln in cp.stderr.splitlines():
        if ln.startswith("import time:") and "|" in ln:
            mod = ln.rsplit("|", 1)[1].strip()
            parts = mod.split(".")
            if len(parts) >= 2 and parts[-2] == "selfimproving":
                names.add(parts[-1])
    return names


if __name__ == "__main__":
    unittest.main()
