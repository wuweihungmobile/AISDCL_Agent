# 受測面：tools/lib/selfimproving/patrolreport.py（程式碼鎖，非散文）
"""SelfImproving P7 RD 半：提案詳情、巡邏快照、白話對照表、低於下限警告（TCS-SelfImproving-P7 §1 的
AC-SI-47-1～47-15 與自增 AC 的 RD 部分；受測 `nextstep.py`、`propdetail.py`、`patrolreport.py` 與
`export.py`、`patrol.py`、`patrolrun.py`、`sandbox.py`、`patrolbrief.py` 的 P7 接線）。

夾具 `_selfimproving_p7_fixtures.py`（`p7x`）。每條 AT 的測試名帶編號（`AT_747_<AC>_<序>`）；
AT-790-*
中屬後棒（MM、PU）與收尾的部分不在本檔（能力登記總數、四守衛聯集見 HB_ROOT_RD 交卷檔）。
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
import _selfimproving_p5_fixtures as fx5
import _selfimproving_p6_fixtures as px
import _selfimproving_p7_fixtures as p7x
from _selfimproving_p4_fixtures import MIN, H, O, iso
from _selfimproving_p7_fixtures import P7TestCase, Rig7, add_prop, base_repo, export_item

from lib import apply_lock
from lib.selfimproving import check as si_check
from lib.selfimproving import events as si_events
from lib.selfimproving import (
    evspec,
    evwrite,
    export,
    issuemap,
    nextstep,
    patrol,
    patrolbrief,
    patrolreport,
    patrolrun,
)
from lib.selfimproving import fold as si_fold
from lib.selfimproving import params as si_params
from lib.selfimproving import verdict as si_verdict
from lib.selfimproving.git import Git

ROOT = fx.ROOT
PKG = ROOT / "tools" / "lib" / "selfimproving"
LEDGER_ROWS = {r[0]: r for r in fx.base_rows()}
DETAIL_KEYS = {"patch", "body", "sourceObs", "heldout", "sandbox", "verify", "next", "timeline"}
TOP_KEYS = ["schema_rev", "generated_at", "off", "heartbeat_minutes", "ledger_seq", "truncated",
            "steps", "schedule", "ingest", "props", "runs", "push"]
PUSH_KEYS = ["enabled", "state", "code", "text", "retry", "sha", "ahead", "attempts",
             "finished_at", "tick_at"]


def setUpModule() -> None:
    fx.setup("si_p7_")


def tearDownModule() -> None:
    fx.teardown()


def committed(R: Path) -> Path:
    fx.commit_all(R, "p7")
    return R


def detail_of(case, R: Path, ident: str) -> dict:
    return export_item(case, R, ident)["items"][0]["detail"]


def folded(events: list[dict]):
    """手寫事件鏈（含 `run.open`）的折疊與 sound 事件列。"""
    composed = fx.compose([fx.run_open_ev(1), fx.skip_ev(1), *events], "0" * 40)
    sound = si_events.sound(composed)
    return si_fold.fold(sound), sound


def one_line(text: str, limit: int = 80) -> bool:
    return bool(text) and "\n" not in text and len(text) <= limit and "｜" not in text \
        and re.search(r"[一-鿿]", text) is not None


def string_constants(path: Path) -> list[str]:
    return [n.value for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


class TestDetail(P7TestCase):
    """AC-SI-47-1～47-7：`export --kind proposals --id` 的 `detail`
    （受測 tools/lib/selfimproving/propdetail.py、tools/lib/selfimproving/export.py）。"""

    def test_AT_747_1_1_detail_has_exactly_eight_fields_and_keeps_the_original_keys(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified")
        committed(R)
        obj = export_item(self, R, pid)
        self.assertEqual(len(obj["items"]), 1)
        item = obj["items"][0]
        self.assertEqual(set(item["detail"]), DETAIL_KEYS)
        rc, out, _ = self.M(R, "export", "--kind", "proposals", "--json")
        plain = next(i for i in json.loads(out)["items"] if i["id"] == pid)
        self.assertNotIn("detail", plain)
        self.assertEqual({k: v for k, v in item.items() if k != "detail"}, plain)

    def test_AT_747_1_E_1_only_proposals_with_id_carry_detail(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified")
        committed(R)
        rc, out, _ = self.M(R, "export", "--kind", "proposals", "--json")
        self.assertTrue(json.loads(out)["items"])
        self.assertTrue(all("detail" not in i for i in json.loads(out)["items"]))
        run = fx.rid(1)
        _, with_id, _ = self.M(R, "export", "--kind", "runs", "--id", run, "--json")
        _, listed, _ = self.M(R, "export", "--kind", "runs", "--json")
        mine = [i for i in json.loads(listed)["items"] if i["id"] == run]
        self.assertEqual(json.loads(with_id)["items"], mine)
        self.assertTrue(all("detail" not in i for i in mine))
        rc, out, _ = self.M(R, "export", "--kind", "proposals", "--id", fx.pid(999), "--json")
        self.assertEqual((rc, json.loads(out)["items"]), (0, []))
        self.assertEqual(pid, fx.pid(124))

    def test_AT_747_2_1_patch_at_the_limit_is_whole(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified")
        p7x.prop_files(R, 124, patch=b"a" * 262144, body="短\n")
        committed(R)
        d = detail_of(self, R, pid)
        self.assertEqual(d["patch"], {
            "rel": f"docs/06_quality/SelfImproving_Proposals/{pid}/r1.patch", "bytes": 262144,
            "text": "a" * 262144, "truncated": False})
        self.assertEqual((d["body"]["rel"], d["body"]["text"]),
                         (f"docs/06_quality/SelfImproving_Proposals/{pid}/r1.md", "短\n"))

    def test_AT_747_2_E_1_truncation_is_by_bytes_and_never_splits_a_character(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified")
        p7x.prop_files(R, 124, patch=b"a" * 262142 + "中".encode())
        committed(R)
        d = detail_of(self, R, pid)["patch"]
        self.assertEqual((d["truncated"], d["bytes"]), (True, 262145))
        raw = d["text"].encode("utf-8")
        self.assertTrue(262141 <= len(raw) <= 262144, len(raw))
        self.assertEqual(raw.decode("utf-8"), d["text"])

    def test_AT_747_2_E_2_unreadable_files_become_null_with_a_plain_note(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified")
        committed(R)
        (R / fx.PROPS_REL / pid / "r1.patch").unlink()
        shutil.rmtree(R / fx.PROPS_REL / pid / "r1.md", ignore_errors=True)
        (R / fx.PROPS_REL / pid / "r1.md").unlink()
        obj = export_item(self, R, pid)
        d = obj["items"][0]["detail"]
        self.assertEqual((d["patch"], d["body"]), (None, None))
        notes = {n["reason"]: n for n in obj["ne"] if "text" in n}
        self.assertEqual(notes["PATCH-UNREADABLE"]["field"], f"proposals.{pid}.detail.patch")
        self.assertEqual(notes["BODY-UNREADABLE"]["text"],
                         nextstep.reason("BODY-UNREADABLE").text)
        self.assertEqual(set(d), DETAIL_KEYS)
        self.assertEqual(d["next"]["code"], "WAIT-PROMOTE-DECISION")

    def test_AT_747_3_1_source_observations_follow_the_sources_order(self):
        R = base_repo()
        srcs = [fx.obs_id(3), fx.obs_id(1)]
        pid = add_prop(R, 124, "proposed", sources=srcs)
        committed(R)
        got = detail_of(self, R, pid)["sourceObs"]
        self.assertEqual([g["id"] for g in got], srcs)
        for g in got:
            row = LEDGER_ROWS[g["id"]]
            self.assertEqual(set(g), {"id", "context", "symptom", "severity", "disposition"})
            self.assertEqual((g["context"], g["symptom"], g["severity"], g["disposition"]),
                             (row[2], row[3], row[6], row[7]))
            self.assertNotIn("｜", json.dumps(g, ensure_ascii=False))

    def test_AT_747_3_E_1_missing_rows_and_an_unreadable_ledger(self):
        R = base_repo()
        pid = add_prop(R, 124, "proposed", sources=[fx.obs_id(1), fx.obs_id(999)])
        committed(R)
        got = detail_of(self, R, pid)["sourceObs"]
        self.assertEqual(got[1], {"id": fx.obs_id(999), "missing": True})
        self.assertNotIn("missing", got[0])
        (R / fx.LEDGER).unlink()
        obj = export_item(self, R, pid)
        self.assertTrue(
            all(g.get("missing") is True for g in obj["items"][0]["detail"]["sourceObs"]))
        self.assertIn("OBS-LEDGER-UNREADABLE", {n["reason"] for n in obj["ne"]})

    def test_AT_747_4_1_evalset_status_is_derived_from_the_ledger_and_params(self):
        digest = "sha256:abcd" + "0123456789abcdef" * 3 + "0123456789ab"
        R = base_repo()
        pid = add_prop(R, 124, "frozen", cases=4, digest=digest)
        committed(R)
        seq = next(e["seq"] for e in fx.EV(R) if e["kind"] == "heldout.freeze")
        h = detail_of(self, R, pid)["heldout"]
        self.assertEqual(set(h), {"frozen", "seq", "n", "min", "belowMin", "frozenBy", "digest8",
                                  "neNote"})
        self.assertEqual({k: h[k] for k in h if k != "neNote"}, {
            "frozen": True, "seq": seq, "n": 4, "min": 5, "belowMin": True, "frozenBy": "FZ",
            "digest8": "abcd0123"})
        for needle in ("驗證必判 NE", "4", "5"):
            self.assertIn(needle, h["neNote"])
        R2 = base_repo()
        pid2 = add_prop(R2, 124, "frozen", cases=5, digest=digest)
        committed(R2)
        h2 = detail_of(self, R2, pid2)["heldout"]
        self.assertEqual((h2["belowMin"], h2["neNote"], h2["n"], h2["min"]), (False, None, 5, 5))

    def test_AT_747_4_E_1_not_frozen_and_unknown_minimum(self):
        R = base_repo()
        pid = add_prop(R, 124, "approved")
        committed(R)
        self.assertEqual(detail_of(self, R, pid)["heldout"], {
            "frozen": False, "seq": None, "n": None, "min": 5, "belowMin": None,
            "frozenBy": None, "digest8": None, "neNote": None})
        fx.set_params(R, min_heldout=KeyError)
        obj = export_item(self, R, pid)
        h = obj["items"][0]["detail"]["heldout"]
        self.assertEqual((h["min"], h["belowMin"]), (None, None))
        self.assertIn("HELDOUT-MIN-UNKNOWN", {n["reason"] for n in obj["ne"]})

    def test_AT_747_4_E_2_no_evalset_content_ever_reaches_the_output(self):
        R = base_repo()
        pid = add_prop(R, 124, "frozen", cases=4)
        committed(R)
        folder = self.home / "heldout" / pid
        secrets_ = {"案例編號": "zz-case-" + "7f3a9c", "探針檔": "probe-" + "1b2c3d4e.py",
                    "突變內容": "MUTANT-" + "55aa66bb"}
        folder.mkdir(parents=True)
        (folder / secrets_["探針檔"]).write_text(secrets_["突變內容"], encoding="utf-8")
        (folder / "manifest.json").write_text(json.dumps({"cases": [{"id": secrets_["案例編號"]}]}),
                                              encoding="utf-8")
        for argv in (("--id", pid), ()):
            rc, out, err = self.M(R, "export", "--kind", "proposals", *argv, "--json")
            self.assertEqual(rc, 0, err)
            for name, value in secrets_.items():
                self.assertNotIn(value, out, name)
        text = (PKG / "propdetail.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        self.assertEqual([c for c in string_constants(PKG / "propdetail.py") if "heldout" in c], [])
        calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        self.assertEqual({c for c in calls if c.endswith("si_dir") or c == "open"}, set())
        self.assertNotIn("home", {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)})

    def test_AT_747_5_1_sandbox_and_verify_come_from_the_latest_same_rev_events(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified", cases=5)
        fx.append_events(R, [fx.sandbox_ev(124), fx.verify_ev(124, "NE"), fx.verify_ev(124, "PASS"),
                             fx.sandbox_ev(124, rev=2)])
        committed(R)
        events = fx.EV(R)

        def last(kind):
            return [e for e in events if e["kind"] == kind and e["rev"] == 1][-1]

        d = detail_of(self, R, pid)
        self.assertEqual(set(d["sandbox"]), {"seq", "id", "applied", "touchedOk", "rollbackOk",
                                             "failCode", "failText"})
        self.assertEqual((d["sandbox"]["seq"], d["sandbox"]["id"]),
                         (last("app.sandbox")["seq"], last("app.sandbox")["id"]))
        v = d["verify"]
        self.assertEqual(set(v), {"seq", "id", "verdict", "baselineRed", "patchedGreen",
                                  "mutatedRed", "probesN", "carrierProof", "reasons"})
        self.assertEqual((v["seq"], v["verdict"]), (last("app.verify")["seq"], "PASS"))
        for key in ("baselineRed", "patchedGreen", "mutatedRed", "carrierProof"):
            self.assertIs(v[key], True, key)
        self.assertEqual(v["probesN"], 1)
        pid2 = add_prop(R, 125, "sandboxed", sandbox={"applied": False})
        committed(R)
        s = detail_of(self, R, pid2)["sandbox"]
        self.assertEqual((s["applied"], s["failCode"], s["failText"]),
                         (False, "SANDBOX-NOT-APPLIED",
                          nextstep.reason("SANDBOX-NOT-APPLIED").text))
        ok = detail_of(self, R, pid)["sandbox"]
        self.assertEqual((ok["failCode"], ok["failText"]), (None, None))

    def test_AT_747_5_2_reasons_are_recomputed_not_copied(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified", cases=4, verdict="PASS")
        committed(R)
        ev = {k: [e for e in fx.EV(R) if e["kind"] == k][-1]
              for k in ("app.sandbox", "app.verify", "heldout.freeze")}
        self.assertEqual(ev["app.verify"]["reasons"], [])
        want = si_verdict.verdict_of(ev["app.sandbox"], ev["app.verify"], ev["heldout.freeze"],
                                     5)[1]
        self.assertIn("HELDOUT-TOO-SMALL", want)
        got = detail_of(self, R, pid)["verify"]["reasons"]
        self.assertEqual([r["code"] for r in got], want)
        self.assertEqual([r["text"] for r in got], [nextstep.reason(c).text for c in want])

    def test_AT_747_5_E_1_missing_sandbox_or_verify(self):
        R = base_repo()
        pid = add_prop(R, 124, "approved")
        committed(R)
        d = detail_of(self, R, pid)
        self.assertEqual((d["sandbox"], d["verify"]), (None, None))
        pid2 = add_prop(R, 125, "verified")
        fx2.drop_events(R, "app.sandbox", pid2)
        d2 = detail_of(self, R, pid2)
        self.assertIsNone(d2["sandbox"])
        self.assertIn("SANDBOX-NOT-APPLIED", [r["code"] for r in d2["verify"]["reasons"]])

    def test_AT_747_7_1_timeline_is_ascending_and_only_this_prop(self):
        R = base_repo()
        pid = add_prop(R, 124, "decided")
        add_prop(R, 125, "verified")
        committed(R)
        events = fx.EV(R)
        mine = [e for e in events if e.get("prop") == pid or e.get("id") == pid]
        tl = detail_of(self, R, pid)["timeline"]
        self.assertEqual([t["seq"] for t in tl], [e["seq"] for e in mine])
        self.assertTrue(all(set(t) == {"seq", "t", "by", "kind", "action"} for t in tl))
        self.assertEqual([t["kind"] for t in tl][:3], ["prop", "card", "dec"])
        acts = {t["kind"]: t["action"] for t in tl}
        self.assertEqual(acts["prop"], issuemap.event_label("prop"))
        decs = [t["action"] for t in tl if t["kind"] == "dec"]
        self.assertEqual(decs, [issuemap.DEC_PREFIX + issuemap.dkind_label("approve"),
                                issuemap.DEC_PREFIX + issuemap.dkind_label("promote")])
        self.assertFalse([t for t in tl if t["kind"].startswith("research")])

    def test_AT_747_7_E_1_unknown_kinds_and_more_than_500_events(self):
        R = base_repo()
        pid = add_prop(R, 124, "approved")
        committed(R)
        with mock.patch.dict(issuemap.EVENT_LABELS):
            issuemap.EVENT_LABELS.pop("card")
            tl = detail_of(self, R, pid)["timeline"]
        self.assertEqual([t["action"] for t in tl if t["kind"] == "card"], ["card"])
        fx.append_events(R, [fx.card_ev(124)] * 520)
        obj = export_item(self, R, pid)
        tl2 = obj["items"][0]["detail"]["timeline"]
        self.assertEqual(len(tl2), 500)
        self.assertEqual(tl2[-1]["seq"], fx.EV(R)[-1]["seq"])
        self.assertIn("TIMELINE-TRUNCATED", {n["reason"] for n in obj["ne"]})


class TestReasons(P7TestCase):
    """AC-SI-47-6、47-12：`nextstep` 的判定與白話表單一家。"""

    def chains(self) -> list[tuple[str, list[dict], str, str, dict]]:
        """（說明, 事件鏈, 碼, who, 要在 PROP 上做的修改）——附錄 A.2 的每一列。"""
        c, n = p7x.prop_chain, 124
        rows = [
            ("proposed-loop", c(n, "proposed"), "WAIT-DECISION", "掌舵者"),
            ("proposed-handoff", c(n, "proposed", route="handoff:DEF"), "WAIT-HANDOFF", "掌舵者"),
            ("approved-nofreeze", c(n, "approved"), "NO-HELDOUT", "主機管理者"),
            ("approved-below", c(n, "frozen", cases=4), "HELDOUT-BELOW-MIN", "巡邏器"),
            ("sandboxed-below", c(n, "sandboxed", cases=4), "HELDOUT-BELOW-MIN", "巡邏器"),
            ("approved-frozen", c(n, "frozen"), "WAIT-SANDBOX", "巡邏器"),
            ("sandboxed", c(n, "sandboxed"), "WAIT-VERIFY", "巡邏器"),
            ("verified-nocard", c(n, "verified", carded=False), "WAIT-CARD", "巡邏器"),
            ("verified-pass", c(n, "verified"), "WAIT-PROMOTE-DECISION", "掌舵者"),
            ("verified-ne", c(n, "verified", verdict="NE"), "WAIT-PROMOTE-DECISION", "掌舵者"),
            ("verified-fail", c(n, "verified", verdict="FAIL"), "WAIT-PROMOTE-DECISION", "掌舵者"),
            ("decided", c(n, "decided"), "WAIT-PROMOTE", "巡邏器"),
            ("promoted-rollback", c(n, "promoted", rollback=True), "WAIT-ROLLBACK", "巡邏器"),
            ("measuring-rollback", c(n, "measuring", rollback=True), "WAIT-ROLLBACK", "巡邏器"),
            ("closed-rollback", c(n, "closed", rollback=True), "WAIT-ROLLBACK", "巡邏器"),
            ("promoted", c(n, "promoted"), "MEASURING", "無"),
            ("measuring", c(n, "measuring"), "MEASURING", "無"),
            ("closed", c(n, "closed"), "CLOSED", "無"),
            ("returned", c(n, "returned"), "WAIT-REVISION", "主機管理者"),
            ("rejected-cooling", c(n, "rejected"), "COOLDOWN", "掌舵者"),
            ("rejected-unblocked", [*c(n, "rejected"), fx.dec_ev(n, "unblock")], "REJECTED", "無"),
            ("handed-off", [*c(n, "proposed", route="handoff:DEF"), fx.dec_ev(n, "ack-handoff")],
             "HANDED-OFF", "無"),
        ]
        return [(a, b, code, who, {}) for a, b, code, who in rows]

    def test_AT_747_6_1_every_row_of_appendix_a2_has_a_definite_answer(self):
        seen_text = set()
        for name, chain, code, who, _ in self.chains():
            with self.subTest(name):
                f, sound = folded(chain)
                got = nextstep.of(f, f.props[fx.pid(124)], {"min_heldout": 5}, sound)
                self.assertEqual((got["code"], got["who"]), (code, who))
                self.assertTrue(one_line(got["text"]), got)
                self.assertIn(got["who"], nextstep.WHO)
                if code == "WAIT-PROMOTE-DECISION":
                    seen_text.add(got["text"])
        self.assertEqual(len(seen_text), 3, "PASS／NE／FAIL 三種句子各異")

    def test_AT_747_6_E_1_unknown_state_and_missing_params_do_not_raise(self):
        f, sound = folded(p7x.prop_chain(124, "proposed"))
        p = f.props[fx.pid(124)]
        p.state = "weird"
        self.assertEqual(nextstep.of(f, p, {}, sound), {
            "code": "UNKNOWN-STATE", "who": "無", "text": nextstep.reason("UNKNOWN-STATE").text})
        self.assertEqual(nextstep.of(f, fx.pid(999), {}, sound)["code"], "UNKNOWN-STATE")
        f2, sound2 = folded(p7x.prop_chain(124, "frozen", cases=4))
        self.assertEqual(nextstep.of(f2, fx.pid(124), {}, sound2)["code"], "WAIT-SANDBOX")

    def test_AT_747_6_2_pure_and_shared_by_detail_and_snapshot(self):
        f, sound = folded(p7x.prop_chain(124, "verified", verdict="NE"))
        a = nextstep.of(f, fx.pid(124), {"min_heldout": 5}, sound)
        self.assertEqual(a, nextstep.of(f, fx.pid(124), {"min_heldout": 5}, sound))
        tree = ast.parse((PKG / "nextstep.py").read_text(encoding="utf-8"))
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module}
        self.assertEqual(mods & {"os", "subprocess", "socket", "time", "datetime", "sys"}, set())
        R = self.enabled_repo(prm={"sched_auto_commit": False})
        pid = add_prop(R, 124, "verified", verdict="NE")
        committed(R)
        rc, out, err = self.beat7(R, O + H)
        self.assertEqual(rc, 0, out + err)
        row = next(r for r in self.report()["props"] if r["id"] == pid)
        det = detail_of(self, R, pid)["next"]
        self.assertEqual({k: row[k] for k in ("code", "who", "text")}, det)

    def test_AT_747_12_1_the_table_covers_every_code_of_appendix_a(self):
        codes = [
            "STALE-CARD", "CARD-CHANGED", "CARD-NOT-ISSUED", "PRECONDITION-STATE",
            "STATE-ILLEGAL", "TRANSITION-ILLEGAL", "PRECONDITION-VERDICT", "PROMOTE-FORM-MISMATCH",
            "PROMOTE-PREMISE-ROLLBACK", "PROMOTE-PREMISE-TOUCHED", "ROUTE-VERB-MISMATCH",
            "ROUTE-HANDOFF", "KIND-MISMATCH", "NOT-IN-COOLDOWN", "NOT-SUSPENDED", "RUN-MISMATCH",
            "RUN-NOT-FOUND", "PROP-NOT-FOUND", "OBS-NOT-FOUND", "OBS-ARCHIVED", "NOT-OPEN",
            "REASON-CLASS-MISSING", "REASON-CLASS-INVALID", "REASON-CLASS-UNEXPECTED",
            "REASON-CLASS-MISMATCH", "REASON-EMPTY", "DISPOSITION-INVALID",
            "DISPOSITION-TEXT-MISSING", "PIPE-IN-FIELD", "CTRL-CHAR", "FIELD-BLANK",
            "FIELD-TOO-LONG", "AUDIT-BODY-INVALID", "AUDIT-SCHEMA", "AUDIT-REF-MISMATCH",
            "AUDIT-KIND-MISMATCH", "AUDIT-KIND-UNKNOWN", "AUDIT-USER-FORMAT", "AUDIT-TIME-FORMAT",
            "AUDIT-SUBJECT-MISMATCH", "AUDIT-FILE-MISSING", "AUDIT-FILE-TOO-LARGE",
            "ROLE-NOT-ADMIN", "AUDIT-MAC-MISMATCH", "AUDIT-KEY-MISSING", "AUDIT-KEY-UNKNOWN",
            "LOCK-BUSY", "LEDGER-WRITE-FAILED", "HOME-UNWRITABLE", "GIT-UNAVAILABLE",
            "STATE-CHANGED", "AUDIT-REF-REUSED", "REG-STALE", "PERIOD-OUT-OF-RANGE",
            "SCHED-QUOTE-REQUIRED", "SCHED-NOT-ENABLED",
            "WAIT-DECISION", "WAIT-HANDOFF", "NO-HELDOUT", "HELDOUT-BELOW-MIN", "WAIT-SANDBOX",
            "WAIT-VERIFY", "WAIT-CARD", "WAIT-PROMOTE-DECISION", "WAIT-PROMOTE", "WAIT-ROLLBACK",
            "MEASURING", "CLOSED", "WAIT-REVISION", "COOLDOWN", "REJECTED", "HANDED-OFF",
            "UNKNOWN-STATE",
            "dirty-tree", "PUSH-IN-PROGRESS", "MEMORY-DIR-UNRESOLVED", "PREIMAGE-MISMATCH",
            "POSTIMAGE-MISMATCH", "COMMIT-FAILED", "COMMIT-LEDGER-RULE", "COMMIT-LEFTOVER",
            "COMMIT-RECORD-FAILED", "APPLY-FAILED", "NON-EVOLVABLE-NOW", "DIGEST-MISMATCH",
            "STATE-NOT-VERIFIED", "NO-PROMOTE-DEC", "NO-ROLLBACK-DEC", "TREE-CHANGED",
            "ROLLBACK-NOT-EXACT", "MEMORY-DIR-MISSING", "SANDBOX-NOT-APPLIED",
            "SANDBOX-EXPORT-FAILED", "SANDBOX-APPLY-TIMEOUT", "TOUCHED-SUPERSET",
            "ROLLBACK-DRYRUN-FAILED",
            "PUSH-OFF", "PUSH-RUNNING", "PUSH-OK", "PUSH-NOT-AHEAD", "PUSH-NOT-MAIN",
            "PUSH-DIRTY-TREE", "PUSH-FOREIGN-COMMITS", "PUSH-APP-KIND-INVALID", "PUSH-APP-REUSED",
            "PUSH-PATH-OUTSIDE", "PUSH-CONTENT-MISMATCH", "PUSH-NOT-RECORDED",
            "PUSH-RECORD-MISMATCH", "PUSH-LEDGER-RULE", "PUSH-GIT-UNAVAILABLE", "PUSH-HOOK-FAILED",
            "PUSH-REJECTED", "PUSH-AUTH", "PUSH-WALL-EXCEEDED", "PUSH-FAILED",
            "PUSH-INTERNAL-ERROR", "PUSH-PENDING", "PUSH-WAITING-LOGIN",
            "NO-PROBES", "CARRIER-PROOF-FAILED", "HELDOUT-DIGEST-MISMATCH", "HELDOUT-TOO-SMALL",
            "HELDOUT-EXPOSED", "EXPOSURE-UNKNOWN", "PROBE-TIMEOUT", "BASELINE-NOT-RED",
            "PATCHED-NOT-GREEN", "MUTATION-NOT-RED", "MUTATION-ABSENT",
            "SCHED-DISABLED", "SCHED-CELL-RAN", "SCHED-DUE", "SKIP-BLACKOUT", "SKIP-QUOTA-BAND",
            "SKIP-OTHER-DRIVER", "SKIP-DIRTY-TREE", "SKIP-RUN-OPEN", "SKIP-SPAWN-FAILED",
            "RUN-BUSY",
            "PATCH-UNREADABLE", "BODY-UNREADABLE", "OBS-LEDGER-UNREADABLE", "HELDOUT-MIN-UNKNOWN",
            "TIMELINE-TRUNCATED",
        ]
        self.assertEqual([c for c in codes if c not in nextstep.REASON], [])
        self.assertLessEqual(set(evspec.VERIFY_REASONS), set(nextstep.REASON))
        for code, row in nextstep.REASON.items():
            with self.subTest(code):
                self.assertEqual(set(row), {"who", "permanent", "text"})
                self.assertIn(row["who"], nextstep.WHO)
                self.assertIsInstance(row["permanent"], bool)
                self.assertTrue(one_line(row["text"]), row["text"])

    def test_AT_747_12_2_unregistered_codes_and_detail_sanitising(self):
        r = nextstep.reason("ZZ-NOT-LISTED")
        self.assertEqual((r.who, r.permanent), ("主機管理者", True))
        self.assertIn("ZZ-NOT-LISTED", r.text)
        self.assertNotIn("{", r.text)
        long = nextstep.reason("PUSH-NOT-RECORDED", "x" * 300).text
        # 超長細節中段省略（保留尾段）
        self.assertEqual((long.count("x"), long.count("…")), (79, 1))
        messy = nextstep.reason("PUSH-NOT-RECORDED", "a\nb｜c|d").text
        self.assertIn("（a b c d）", messy)
        self.assertNotIn("{", nextstep.reason("PUSH-NOT-RECORDED").text)
        self.assertEqual(nextstep.reason("REGISTRY-ANYTHING").who, "掌舵者")

    def test_AT_747_12_3_the_plain_sentences_live_only_in_nextstep(self):
        seen = {}
        for path in sorted(PKG.glob("*.py")):
            if path.name != "nextstep.py":
                seen[path.name] = string_constants(path)
        known = {("RUN-BUSY", "patrol.py"), ("PUSH-GIT-UNAVAILABLE", "btwrite.py"),
                 ("PUSH-GIT-UNAVAILABLE", "promote.py"), ("PUSH-GIT-UNAVAILABLE", "schedwrite.py"),
                 # P7 前既有字串；固定白話句無法在實作端迴避
                 ("PUSH-GIT-UNAVAILABLE", "writeverbs.py")}
        clash, hit_pairs = [], set()
        for code, row in nextstep.REASON.items():
            text = row["text"]
            for name, consts in seen.items():
                if len(text) >= 8:
                    hits = [c for c in consts if text[:8] in c]
                else:
                    hits = [c for c in consts if c == text]
                if hits:
                    hit_pairs.add((code, name))
                if hits and (code, name) not in known:
                    clash.append((code, name, hits[0][:40]))
        self.assertEqual(clash, [])
        # E-2 第二層：豁免清單只減不增，清單內某對已不再命中就必須自清單移除
        self.assertEqual(sorted(known - hit_pairs), [], "豁免清單過時：請移除已不命中的項目")
        new_files = {"patrolreport.py", "propdetail.py", "pushguard.py", "patrolpush.py",
                     "memdir.py"}
        self.assertEqual(sorted(n for _, n in hit_pairs if n in new_files), [],
                         "本鍵新增或改動的檔不得有任何豁免")
        for name in ("patrolreport.py", "propdetail.py"):
            src = (PKG / name).read_text(encoding="utf-8")
            self.assertIn("nextstep", src, name)


class TestFreezeWarning(P7TestCase):
    """AC-SI-47-13：`heldout-freeze` 低於下限只警告。"""

    def freeze(self, R: Path, pid: str, cases: int, *extra: str):
        src = fx2.make_heldout(fx.new_dir("ho"), cases=cases)
        return self.M(R, "heldout-freeze", pid, "--from", src, "--by", "FZ", *extra)

    def test_AT_747_13_1_below_the_minimum_is_a_stderr_warning_only(self):
        R1, R2 = base_repo(), base_repo()
        p1, p2 = add_prop(R1, 124, "approved"), add_prop(R2, 125, "approved")
        rc, out, err = self.freeze(R1, p1, 4)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(err, "warn HELDOUT-BELOW-MIN n=4 min=5\n")
        self.assertEqual([e["n"] for e in fx.EV(R1) if e["kind"] == "heldout.freeze"], [4])
        rc2, out2, err2 = self.freeze(R2, p2, 5)
        self.assertEqual((rc2, err2), (0, ""))
        norm = lambda s: re.sub(r"n=\d+|digest8=\w+|seq=\d+|prop=\S+", "", s)  # noqa: E731
        self.assertEqual(norm(out), norm(out2))
        self.assertNotIn("warn", out)

    def test_AT_747_13_E_1_json_stays_one_object_and_the_card_is_untouched(self):
        R1, R2 = base_repo(), base_repo()
        p1, p2 = add_prop(R1, 124, "approved"), add_prop(R2, 125, "approved")
        rc, out, err = self.freeze(R1, p1, 4, "--json")
        rc2, out2, _ = self.freeze(R2, p2, 5, "--json")
        self.assertEqual((rc, rc2), (0, 0), out + err)
        self.assertEqual(list(json.loads(out)), list(json.loads(out2)))
        self.assertIn("warn HELDOUT-BELOW-MIN", err)
        self.new_home()
        R3 = fx2.p2_base()
        pid = fx2.new_prop(R3)
        before = self.M(R3, "card", pid)[1]
        rc3, out3, err3 = self.freeze(R3, pid, 4)
        self.assertEqual(rc3, 0, out3 + err3)
        self.assertEqual(self.M(R3, "card", pid)[1], before)
        R4 = base_repo()
        p4 = add_prop(R4, 126, "approved")
        fx.set_params(R4, min_heldout=KeyError)
        rc4, out4, err4 = self.freeze(R4, p4, 4)
        self.assertEqual((rc4, err4), (0, ""), out4)


class TestSnapshot(P7TestCase):
    """AC-SI-47-8～47-11、47-15：巡邏快照
    （受測 tools/lib/selfimproving/patrolreport.py、tools/lib/selfimproving/patrolrun.py）。"""

    def repo(self, **kw) -> Path:
        return self.enabled_repo(prm={"sched_auto_commit": False, **kw})

    def test_AT_747_8_1_a_heartbeat_writes_the_snapshot_without_a_sixth_step(self):
        R = self.repo()
        add_prop(R, 124, "verified")
        committed(R)
        rc, out, err = self.beat7(R, O + H)
        self.assertEqual(rc, 0, out + err)
        raw = self.report_path().read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n") and b"\r" not in raw)
        rep = json.loads(raw.decode("utf-8"))
        self.assertEqual(list(rep), TOP_KEYS)
        self.assertEqual((rep["schema_rev"], rep["off"], rep["heartbeat_minutes"]), (1, False, 15))
        self.assertEqual(rep["ledger_seq"], max(e["seq"] for e in fx.EV(R)))
        self.assertEqual(datetime.fromisoformat(rep["generated_at"]), O + H)
        self.assertEqual([s["step"] for s in rep["steps"]],
                         ["巡視", "入帳", "到期", "運轉", "推進"])
        self.assertEqual(sorted(p.name for p in (self.home / "console_report").iterdir()),
                         ["patrol.json"])
        self.assertEqual(re.findall(r"(?m)^step=(\S+) ", out), [s["step"] for s in rep["steps"]])
        rc, out, _ = self.beat7(R, O + H + MIN, None, "--json")
        self.assertEqual(len(json.loads(out)["steps"]), 5)
        self.assertEqual(datetime.fromisoformat(self.report()["generated_at"]), O + H + MIN)

    def test_AT_747_8_2_a_failed_write_leaves_the_old_file_and_the_rc(self):
        R = self.repo()
        self.assertEqual(self.beat7(R, O + H)[0], 0)
        old = self.report_path().read_bytes()
        n = len(self.logs())
        with mock.patch.object(patrolreport.os, "replace", side_effect=PermissionError("x")):
            rc, out, err = self.beat7(R, O + H + MIN)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(self.report_path().read_bytes(), old)
        self.assertEqual(sorted(p.name for p in (self.home / "console_report").iterdir()),
                         ["patrol.json"])
        fails = [ln for ln in self.logs()[n:] if "code=REPORT-WRITE-FAILED" in ln]
        self.assertEqual(len(fails), 1)
        orig = Path.mkdir

        def boom(path, *a, **k):
            if path.name == patrolreport.REPORT_DIR:
                raise OSError("no dir")
            return orig(path, *a, **k)
        with mock.patch.object(Path, "mkdir", boom):
            rc2, out2, err2 = self.beat7(R, O + H + 2 * MIN)
        self.assertEqual(rc2, 0, out2 + err2)
        self.assertEqual(self.report_path().read_bytes(), old)
        self.assertEqual(len([ln for ln in self.logs() if "code=REPORT-WRITE-FAILED" in ln]), 2)

    def test_AT_747_8_3_size_caps_and_single_line_texts(self):
        R = self.repo()
        fx.append_events(R, [fx.run_open_ev(1), fx.skip_ev(1),
                             *[fx.prop_ev(500 + k, 1) for k in range(300)]])
        committed(R)
        params = si_check.params_for(R, *si_params.SCHED_KEYS, "stop_after_bad")
        ctx = patrol.Ctx(R, O + H, False, patrol.Deps(), params)
        ctx.ingest_rows = [(fx2.new_uuid(), "decide", "STALE-CARD")] * 250
        rep = patrolreport.build(ctx, [], [], lambda *a: False)
        self.assertEqual((len(rep["ingest"]), len(rep["props"]), rep["truncated"]),
                         (200, 200, True))
        self.assertLessEqual(len(patrolreport.dump(rep)), patrolreport.REPORT_MAX_BYTES)
        texts = [r["text"] for r in (*rep["ingest"], *rep["props"])]
        self.assertTrue(all("\n" not in t and len(t) <= 120 for t in texts))
        ctx.ingest_rows = ctx.ingest_rows[:3]
        small = patrolreport.build(ctx, [], [], lambda *a: False)
        self.assertEqual((len(small["ingest"]), small["truncated"]), (3, True), "props 仍超界")

    def test_AT_747_8_4_staleness_is_strictly_greater_than_two_beats_plus_five(self):
        g = O
        rep = {"generated_at": iso(g), "heartbeat_minutes": 15}
        edge = g + timedelta(minutes=35)
        self.assertFalse(patrolreport.is_stale(rep, edge))
        self.assertTrue(patrolreport.is_stale(rep, edge + timedelta(seconds=1)))
        self.assertTrue(patrolreport.is_stale({"heartbeat_minutes": 15}, edge))
        self.assertTrue(patrolreport.is_stale({"generated_at": "x", "heartbeat_minutes": 15}, edge))
        self.assertTrue(patrolreport.is_stale({"generated_at": iso(g)}, edge))
        with self.assertRaises(ValueError):
            patrolreport.is_stale(rep, datetime(2026, 1, 1))

    def test_AT_747_8_E_1_dry_run_unattended_and_a_busy_lock_write_nothing(self):
        R = self.repo()
        rc, out, err = self.beat7(R, O + H, None, "--dry-run")
        self.assertEqual(rc, 0, out + err)
        self.assertFalse((self.home / "console_report").exists())
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, err = self.beat7(R, O + H)
        self.assertEqual(rc, 1, out + err)
        self.assertFalse((self.home / "console_report").exists())
        self.assertEqual(self.beat7(R, O + H)[0], 0)
        old = self.report_path().read_bytes()
        lock = evwrite.ensure_home(self.home) / "patrol.lock"
        with apply_lock.acquire(lock, 0, 7200):
            rc, out, err = self.beat7(R, O + H + MIN)
        self.assertEqual((rc, "已有巡邏在跑" in out), (0, True), out + err)
        self.assertEqual(self.report_path().read_bytes(), old)

    def test_AT_747_8_E_2_an_unexpected_exception_still_writes_the_snapshot(self):
        R = self.repo()
        ref = self.audit("obs-add", lambda r: fx2.body_obs_add(r), key_id="deadbeef")
        with mock.patch.object(patrol, "launch_all", side_effect=RuntimeError("boom")), \
                fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.beat7(R, O + H)
        self.assertEqual(rc, 1, out + err)
        rep = self.report()
        self.assertIn("PATROL-EXCEPTION", rep["steps"][-1]["result"])
        self.assertEqual([r["audit_ref"] for r in rep["ingest"]], [ref])

    def audit_set(self, R: Path, now: datetime, *, kinds=("stale", "unknown", "good")):
        """三個稽核檔：舊 digest 的 decide、金鑰不明的 obs-add、合法的 obs-add；
        回 (ref 們, PROP)。"""
        pid = add_prop(R, 124, "proposed")
        committed(R)
        refs = {}
        if "stale" in kinds:
            refs["stale"] = self.audit("decide", lambda r: fx2.body_decide(
                r, pid, fx.H(5), "approve"), subject=pid)
        if "unknown" in kinds:
            refs["unknown"] = self.audit("obs-add", lambda r: fx2.body_obs_add(r),
                                         key_id="deadbeef")
        if "good" in kinds:
            refs["good"] = self.audit("obs-add", lambda r: fx2.body_obs_add(r))
        return refs, pid

    def test_AT_747_9_1_rejected_and_deferred_files_are_listed_with_plain_text(self):
        R = self.repo()
        refs, _ = self.audit_set(R, O + H)
        with fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.beat7(R, O + H)
        self.assertEqual(rc, 0, out + err)
        rows = {r["audit_ref"]: r for r in self.report()["ingest"]}
        self.assertEqual(set(rows), {refs["stale"], refs["unknown"]})
        for row in rows.values():
            self.assertEqual(list(row),
                             ["audit_ref", "kind", "status", "code", "text", "permanent"])
            self.assertEqual(row["text"], nextstep.reason(row["code"]).text)
        a, b = rows[refs["stale"]], rows[refs["unknown"]]
        self.assertEqual((a["kind"], a["status"], a["code"], a["permanent"]),
                         ("decide", "rejected", "STALE-CARD", True))
        self.assertEqual((b["kind"], b["status"], b["code"], b["permanent"]),
                         ("obs-add", "deferred", "AUDIT-KEY-UNKNOWN", False))
        self.assertEqual(sum(e["kind"] == "obs.add" for e in fx.EV(R)), 1)

    def test_AT_747_9_2_the_snapshot_is_stateless_and_clears_once_fixed(self):
        R = self.repo()
        refs, _ = self.audit_set(R, O + H, kinds=("unknown",))
        for k in (0, 1):
            with fx4.with_key(fx2.AUDIT_KEY):
                self.assertEqual(self.beat7(R, O + H + k * MIN)[0], 0)
            self.assertEqual([r["audit_ref"] for r in self.report()["ingest"]], [refs["unknown"]])
        rejects = [ln for ln in self.logs() if refs["unknown"] in ln
                   and "code=AUDIT-KEY-UNKNOWN" in ln]
        self.assertEqual(len(rejects), 1, "日誌沿既有去重只記一次")
        fx2.write_audit(self.home, kind="obs-add", ref=refs["unknown"], subject=None,
                        key=fx2.AUDIT_KEY, body=fx2.body_obs_add(refs["unknown"]))
        with fx4.with_key(fx2.AUDIT_KEY):
            self.assertEqual(self.beat7(R, O + H + 2 * MIN)[0], 0)
        self.assertEqual(self.report()["ingest"], [])
        self.assertEqual(sum(e["kind"] == "obs.add" for e in fx.EV(R)), 1)

    def test_AT_747_9_E_1_unknown_kind_unlisted_code_and_unmeasurable_inbox(self):
        R = self.repo()
        ref = fx2.new_uuid()
        fx2.write_audit(self.home, kind="weird", ref=ref, subject=None, key=fx2.AUDIT_KEY,
                        body=fx2.body_obs_add(ref))
        rig = Rig7(script={"decide": (1, "reject decide ZZ-UNLISTED-CODE\n", "")})
        ref2 = self.audit("decide", lambda r: fx2.body_decide(r, fx.pid(1), fx.H(5), "approve"),
                          subject=fx.pid(1))
        with fx4.with_key(fx2.AUDIT_KEY):
            self.assertEqual(self.beat7(R, O + H, rig)[0], 0)
        rows = {r["audit_ref"]: r for r in self.report()["ingest"]}
        self.assertEqual((rows[ref]["code"], rows[ref]["kind"]), ("AUDIT-KIND-UNKNOWN", None))
        self.assertEqual((rows[ref2]["code"], rows[ref2]["permanent"]), ("ZZ-UNLISTED-CODE", True))
        self.assertIn("ZZ-UNLISTED-CODE", rows[ref2]["text"])
        bad = {"status": "NOT-EVALUABLE", "reason": "boom"}
        with mock.patch.object(patrol.status, "console_pending", return_value=bad):
            self.assertEqual(self.beat7(R, O + H + MIN)[0], 0)
        rep = self.report()
        self.assertEqual(rep["ingest"], [])
        self.assertIn("量不到", next(s for s in rep["steps"] if s["step"] == "入帳")["result"])

    def test_AT_747_9_3_permanence_follows_the_table_of_appendix_a1(self):
        false = {"AUDIT-KEY-MISSING", "AUDIT-KEY-UNKNOWN", "LOCK-BUSY", "LEDGER-WRITE-FAILED",
                 "HOME-UNWRITABLE", "GIT-UNAVAILABLE", "STATE-CHANGED"}
        true = {"STALE-CARD", "CARD-CHANGED", "CARD-NOT-ISSUED", "PRECONDITION-STATE",
                "STATE-ILLEGAL", "TRANSITION-ILLEGAL", "PRECONDITION-VERDICT",
                "PROMOTE-FORM-MISMATCH", "PROMOTE-PREMISE-ROLLBACK", "PROMOTE-PREMISE-TOUCHED",
                "ROUTE-VERB-MISMATCH", "ROUTE-HANDOFF", "KIND-MISMATCH", "NOT-IN-COOLDOWN",
                "NOT-SUSPENDED", "RUN-MISMATCH", "RUN-NOT-FOUND", "PROP-NOT-FOUND",
                "OBS-NOT-FOUND", "OBS-ARCHIVED", "NOT-OPEN", "REASON-CLASS-MISSING", "REASON-EMPTY",
                "AUDIT-BODY-INVALID", "AUDIT-SCHEMA", "AUDIT-KIND-UNKNOWN", "AUDIT-FILE-TOO-LARGE",
                "ROLE-NOT-ADMIN", "AUDIT-MAC-MISMATCH", "AUDIT-REF-REUSED", "REG-STALE",
                "PERIOD-OUT-OF-RANGE", "SCHED-NOT-ENABLED"}
        self.assertEqual({c for c in false if nextstep.reason(c).permanent}, set())
        self.assertEqual({c for c in true if not nextstep.reason(c).permanent}, set())

    def test_AT_747_10_1_each_open_prop_gets_a_stuck_point_and_finished_ones_do_not(self):
        R = self.repo()
        chains = {124: "proposed", 125: "approved", 126: "frozen", 127: "sandboxed",
                  128: "verified", 129: "returned", 130: "rejected", 131: "measuring",
                  132: "closed", 133: "measuring"}
        folded_state = {126: "approved"}  # 「已凍結」是 approved 的子階段
        for n, st in chains.items():
            kw = {"cases": 4} if n == 126 else {"rollback": True} if n == 133 else {}
            add_prop(R, n, st, **kw)
        committed(R)
        self.assertEqual(self.beat7(R, O + H)[0], 0)
        rows = {r["id"]: r for r in self.report()["props"]}
        self.assertEqual(sorted(rows),
                         [fx.pid(n) for n in (124, 125, 126, 127, 128, 129, 130, 133)])
        want = {124: "WAIT-DECISION", 125: "NO-HELDOUT", 126: "HELDOUT-BELOW-MIN",
                127: "WAIT-VERIFY", 128: "WAIT-PROMOTE-DECISION", 129: "WAIT-REVISION",
                130: "COOLDOWN", 133: "WAIT-ROLLBACK"}
        for n, code in want.items():
            row = rows[fx.pid(n)]
            self.assertEqual(list(row), ["id", "state", "code", "who", "text"])
            self.assertEqual((row["state"], row["code"], row["who"]),
                             (folded_state.get(n, chains[n]), code, nextstep.reason(code).who))

    def test_AT_747_10_2_this_heartbeats_note_overrides_and_lives_one_heartbeat(self):
        R = self.repo()
        add_prop(R, 124, "decided")
        add_prop(R, 125, "frozen")
        committed(R)
        fx.put(R, "docs/notes/untracked.md", "x\n")
        rig = Rig7(script={"sandbox": (1, "reject sandbox SANDBOX-NOT-APPLIED\n", "")})
        self.assertEqual(self.beat7(R, O + H, rig)[0], 0)
        rows = {r["id"]: r for r in self.report()["props"]}
        self.assertEqual((rows[fx.pid(124)]["code"], rows[fx.pid(124)]["who"]),
                         ("dirty-tree", "主機管理者"))
        self.assertEqual(rows[fx.pid(125)]["code"], "SANDBOX-NOT-APPLIED")
        (R / "docs/notes/untracked.md").unlink()
        self.assertEqual(self.beat7(R, O + H + MIN)[0], 0)
        rows = {r["id"]: r for r in self.report()["props"]}
        self.assertEqual(rows[fx.pid(124)]["code"], "WAIT-PROMOTE")
        self.assertEqual(rows[fx.pid(125)]["code"], "WAIT-SANDBOX")

    def test_AT_747_10_2_b_a_failed_commit_is_a_note(self):
        R = self.repo()
        pid = add_prop(R, 124, "promoted")
        committed(R)
        fx.put(R, f"{fx.PROPS_REL}/{pid}/r2.md", "changed\n")  # 提案目錄只准新增檔（AC-SI-49-2）
        params = si_check.params_for(R, *si_params.SCHED_KEYS, "stop_after_bad")
        ctx = patrol.Ctx(R, O + H, False, patrol.Deps(), params)
        real = Git.run

        def fail_commit(self_, *args, **kw):
            if "commit" in args:
                return None
            return real(self_, *args, **kw)
        with mock.patch.object(Git, "run", fail_commit):
            patrolrun._commit(ctx, pid, "promote")
        self.assertEqual(ctx.notes[pid][0], "COMMIT-FAILED")
        rep = patrolreport.build(ctx, [], [], lambda *a: False)
        self.assertEqual([(r["code"], r["who"]) for r in rep["props"] if r["id"] == pid],
                         [("COMMIT-FAILED", "主機管理者")])

    def test_AT_747_10_3_every_early_return_with_a_code_also_notes_it(self):
        tree = ast.parse((PKG / "patrolrun.py").read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                  and n.name == "_advance_prop")
        blocks = [n.body for n in ast.walk(fn) if isinstance(n, ast.If)]
        logged = 0
        for body in blocks:
            calls = [c for s in body for c in ast.walk(s) if isinstance(c, ast.Call)]
            logs = [c.args[2].value for c in calls if ast.unparse(c.func) == "ctx.log"
                    and len(c.args) > 2 and isinstance(c.args[2], ast.Constant)
                    and c.args[2].value is not None and c.args[0].value == "推進"]
            notes = {c.args[1].value for c in calls if ast.unparse(c.func) == "ctx.note"}
            logged += len(logs)
            self.assertEqual(set(logs), notes & set(logs) if logs else set(), (logs, notes))
        self.assertGreaterEqual(logged, 4)
        step = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                    and n.name == "_step")
        self.assertIn("ctx.note", ast.unparse(step))

    def test_AT_747_11_1_live_runs_have_a_purpose_and_closed_ones_are_not_listed(self):
        R = self.repo()
        o = fx4.O
        extra = [fx4.run_open_f_ev(11, O + MIN, due_at=o + timedelta(days=9)), fx.skip_ev(11),
                 fx.ev("run.open", "console", run=fx.rid(12), trigger="a", carrier="console",
                       audit_ref=fx2.new_uuid(), audit_sha256=fx.H(6), key_id="00000000",
                       decider="admin", coords=["console_audit/x.json"]),
                 fx.skip_ev(12), fx.run_open_ev(13), fx.skip_ev(13), fx.run_open_ev(14),
                 fx.skip_ev(14)]
        fx.append_events(R, extra)
        committed(R)
        rig = Rig7()
        for n, pidn in ((11, 4411), (12, 4412), (13, 4413), (14, 4414)):
            spawn = self.home / "patrol" / fx.rid(n) / "spawn.json"
            spawn.parent.mkdir(parents=True)
            data = {"pid": pidn, "started_at": iso(O + H), "wall_due_at": iso(O + 3 * H)}
            if n == 14:
                data["closed_at"] = iso(O + 2 * H)
            spawn.write_text(json.dumps(data), encoding="utf-8")
            rig.live.add(pidn)
        self.assertEqual(self.beat7(R, O + H + 10 * MIN, rig)[0], 0)
        runs = self.report()["runs"]
        self.assertEqual(list(runs), ["live", "waiting", "queued"])
        self.assertEqual({r["run"]: r["purpose"] for r in runs["live"]},
                         {fx.rid(11): "scheduled", fx.rid(12): "console", fx.rid(13): "manual"})
        self.assertEqual(runs["queued"], [])
        self.assertEqual(list(runs["live"][0]), ["run", "purpose", "started_at", "wall_due_at"])

    def test_AT_747_11_2_off_still_writes_a_snapshot_with_no_side_effects(self):
        R = self.repo()
        add_prop(R, 124, "verified")
        committed(R)
        before, n = fx.snap(R), len(self.logs())
        calls = []
        real = Git.run
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_PATROL_OFF": "1"}), \
                mock.patch.object(Git, "run", lambda s, *a, **k: calls.append(a)
                                  or real(s, *a, **k)):
            rc, out, err = self.beat7(R, O + H)
        self.assertEqual(rc, 0, out + err)
        rep = self.report()
        self.assertEqual((rep["off"], rep["ingest"], rep["props"], rep["steps"], rep["schedule"]),
                         (True, [], [], [], None))
        self.assertEqual(rep["runs"], {"live": [], "waiting": [], "queued": []})
        self.assertEqual((rep["push"]["state"], rep["push"]["code"]), ("off", "PUSH-OFF"))
        self.assertEqual(datetime.fromisoformat(rep["generated_at"]), O + H)
        self.assertEqual((fx.snap(R), calls), (before, []))
        self.assertFalse((self.home / "locks" / "patrol.lock").exists())
        self.assertEqual(len(self.logs()), n + 1)
        self.assertEqual(self.beat7(R, O + H + MIN)[0], 0)
        self.assertFalse(self.report()["off"])

    def test_AT_747_11_3_the_push_block_has_ten_keys_and_fixed_types(self):
        R = self.repo()
        self.assertEqual(self.beat7(R, O + H)[0], 0)
        self.assertEqual(list(self.report()["push"]), PUSH_KEYS)
        home, now = self.home, O + H
        prm = {"sched_heartbeat_minutes": 15, "sched_push_attempts_max": 3,
               "sched_push_retry_minutes": 10}
        (home / "push" / "results").mkdir(parents=True)
        dead = lambda *a: False  # noqa: E731
        guard = {"ahead": 1, "head": "b" * 40, "code": None, "detail": None}
        blocked = dict(guard, code="PUSH-DIRTY-TREE")
        cases = [
            (False, None, dead, "off"), (True, None, dead, "blocked"),
            (True, dict(guard, ahead=0), dead, "idle"),
            (True, blocked, dead, "blocked"), (True, guard, dead, "waiting-login"),
        ]
        for enabled, g, alive, state in cases:
            blk = patrolreport.push_block(home, prm, now, enabled, g, alive)
            with self.subTest(state):
                self.assertEqual(list(blk), PUSH_KEYS)
                self.assertEqual(blk["state"], state)
                self.assertTrue(all(isinstance(blk[k], str) and blk[k] for k in
                                    ("state", "code", "text")))
                self.assertIsInstance(blk["enabled"], bool)
                self.assertIsInstance(blk["ahead"], int)
                self.assertIsInstance(blk["attempts"], int)
        (home / "push" / "tick.json").write_text(json.dumps({"tick_at": iso(now - 5 * MIN)}),
                                                 encoding="utf-8")
        self.assertEqual(patrolreport.push_block(home, prm, now, True, guard, dead)["state"],
                         "pending")
        (home / "push" / "current.json").write_text(json.dumps({
            "sha": "b" * 40, "pid": 1, "started_at": iso(now), "wall_due_at": iso(now + H)}),
            encoding="utf-8")
        live = patrolreport.push_block(home, prm, now, True, guard, lambda *a: True)
        self.assertEqual((live["state"], live["sha"]), ("running", "b" * 40))
        (home / "push" / "current.json").unlink()
        res = {"sha": "b" * 40, "finished_at": iso(now - MIN), "rc": 1, "code": "PUSH-AUTH",
               "text": "x", "attempts": 1, "tree_changed": False}
        (home / "push" / "results" / ("b" * 12 + ".json")).write_text(json.dumps(res),
                                                                     encoding="utf-8")
        never = patrolreport.push_block(home, prm, now, True, guard, dead)
        self.assertEqual((never["state"], never["retry"], never["attempts"]),
                         ("failed", "never", 1))

    def sched_beat(self, R: Path, rig=None, *, hm="12:00", now=None) -> dict:
        self.new_home()  # 每個情境各用乾淨的家目錄（運轉目錄、快照不互相殘留）
        self.assertEqual(self.beat7(R, now or O + H, rig, hm=hm)[0], 0)
        return self.report()["schedule"]

    def test_AT_747_15_1_schedule_block_names_why_no_run_was_started(self):
        sched_keys = ["enabled", "current", "last_skip"]
        disabled = self.sched_beat(base_repo())
        self.assertEqual(list(disabled), sched_keys)
        self.assertEqual((disabled["enabled"], disabled["current"]["code"]),
                         (False, "SCHED-DISABLED"))
        dirty = self.repo()
        fx.put(dirty, "docs/notes/untracked.md", "x\n")
        opened = self.repo()
        fx.append_events(opened, [fx.run_open_ev(7), fx.skip_ev(7)])
        committed(opened)
        scenes = {
            "SKIP-BLACKOUT": (self.repo(), Rig7(), "23:00"),
            "SKIP-QUOTA-BAND": (self.repo(), Rig7(band="stop"), "12:00"),
            "SKIP-OTHER-DRIVER": (self.repo(), Rig7(quiet=False), "12:00"),
            "SKIP-DIRTY-TREE": (dirty, Rig7(), "12:00"),
            "SKIP-RUN-OPEN": (opened, Rig7(), "12:00"),
            "SKIP-SPAWN-FAILED": (self.repo(), Rig7(which=None), "12:00"),
            "SCHED-DUE": (self.repo(), Rig7(), "12:00"),
        }
        for code, (R, rig, hm) in scenes.items():
            with self.subTest(code):
                got = self.sched_beat(R, rig, hm=hm)
                self.assertEqual(got["current"]["code"], code)
                self.assertEqual(got["current"]["text"], got["current"]["text"].strip())
                if code.startswith("SKIP-"):
                    self.assertEqual(got["last_skip"]["code"], code)
                    self.assertEqual(got["last_skip"]["text"], got["current"]["text"])
                    self.assertEqual(list(got["last_skip"]),
                                     ["seq", "t", "code", "text", "audit_ref"])
        ran = self.repo()
        fx.append_events(ran, [fx4.run_open_f_ev(8, O + MIN, due_at=O), fx.skip_ev(8),
                               fx4.run_close_ev(8, O + 2 * MIN)])
        committed(ran)
        self.assertEqual(self.sched_beat(ran, now=O + H)["current"]["code"], "SCHED-CELL-RAN")

    def test_AT_747_15_2_a_console_run_request_eaten_as_a_skip_is_visible(self):
        R = base_repo()  # 排程停用：本心跳的 due() 不另記 sched.skip，最近一筆就是被消耗的那筆
        fx.append_events(R, [fx.run_open_ev(7), fx.skip_ev(7)])
        committed(R)
        ref = self.audit("run-request", fx4.body_run_request)
        before = sum(e["kind"] == "run.open" for e in fx.EV(R))
        with fx4.with_key(fx2.AUDIT_KEY):
            self.assertEqual(self.beat7(R, O + H)[0], 0)
        ev = [e for e in fx.EV(R) if e["kind"] == "sched.skip" and e.get("audit_ref") == ref]
        self.assertEqual([(e["reason"], e["carrier"]) for e in ev], [("run-open", "console")])
        self.assertEqual(sum(e["kind"] == "run.open" for e in fx.EV(R)), before)
        last = self.report()["schedule"]["last_skip"]
        self.assertEqual((last["code"], last["audit_ref"]), ("SKIP-RUN-OPEN", ref))
        for needle in ("已有未關運轉", fx.rid(7), "第二波起可由 Console 處理"):
            self.assertIn(needle, last["text"])

    def test_AT_747_15_3_waiting_runs_carry_the_reason_they_were_held_back(self):
        R = self.repo()
        waiting = [fx.ev("run.open", "console", run=fx.rid(21), trigger="a", carrier="console",
                         audit_ref=fx2.new_uuid(), audit_sha256=fx.H(6), key_id="00000000",
                         decider="admin", coords=["console_audit/x.json"])]
        fx.append_events(R, waiting)
        committed(R)
        self.assertEqual(self.beat7(R, O + H, Rig7(band="stop"))[0], 0)
        runs = self.report()["runs"]
        self.assertEqual(runs["waiting"], [{
            "run": fx.rid(21), "code": "SKIP-QUOTA-BAND",
            "text": runs["waiting"][0]["text"]}])
        self.assertIn("額度帶", runs["waiting"][0]["text"])
        busy = Rig7()
        spawn = self.home / "patrol" / fx.rid(5) / "spawn.json"
        spawn.parent.mkdir(parents=True)
        spawn.write_text(json.dumps({"pid": 4141, "started_at": iso(O + H),
                                     "wall_due_at": iso(O + 3 * H)}), encoding="utf-8")
        busy.live.add(4141)
        self.assertEqual(self.beat7(R, O + H + MIN, busy)[0], 0)
        self.assertEqual([(w["run"], w["code"]) for w in self.report()["runs"]["waiting"]],
                         [(fx.rid(21), "RUN-BUSY")])
        self.assertNotIn(fx.rid(21), {r["run"] for r in self.report()["runs"]["live"]})

    def test_AT_747_15_E_1_a_failing_due_keeps_the_rest_of_the_snapshot(self):
        R = self.repo()
        with mock.patch.object(patrol, "due", side_effect=RuntimeError("boom")):
            rc, out, err = self.beat7(R, O + H)
        self.assertEqual(rc, 1, out + err)
        sched_part = self.report()["schedule"]
        self.assertEqual((sched_part["enabled"], sched_part["current"]), (True, None))
        for code in ("SCHED-DISABLED", "SCHED-CELL-RAN", "SCHED-DUE", "SKIP-BLACKOUT",
                     "SKIP-QUOTA-BAND", "SKIP-OTHER-DRIVER", "SKIP-DIRTY-TREE", "SKIP-RUN-OPEN",
                     "SKIP-SPAWN-FAILED", "RUN-BUSY"):
            self.assertTrue(one_line(nextstep.REASON[code]["text"]), code)


class TestBrief(P7TestCase):
    """AC-SI-47-14：SOP 勘誤與範本占位符。"""

    sop = (fx.REAL_SOP.read_text(encoding="utf-8")).replace("\r\n", "\n")

    @staticmethod
    def part(text: str, key: str) -> str:
        lines, out, on, level = text.split("\n"), [], False, 0
        for ln in lines:
            m = re.match(r"^(#+) ", ln)
            if m and key in ln:
                on, level = True, len(m.group(1))
            elif m and on and len(m.group(1)) <= level:
                break
            if on:
                out.append(ln)
        return "\n".join(out)

    def test_AT_747_14_1_sop_has_the_corrected_sections_and_all_judges_agree(self):
        held = self.part(self.sop, "held-out 目錄")
        for frag in ("min_heldout", "HELDOUT-TOO-SMALL", "NO-PROBES", "warn HELDOUT-BELOW-MIN"):
            self.assertIn(frag, held, frag)
        files = self.part(self.sop, "提案檔")
        for frag in ("RUN-NOT-OPEN", "RESEARCH-MISSING"):
            self.assertIn(frag, files, frag)
        step7 = next(ln for ln in patrolbrief.template_of(self.sop).split("\n")
                     if ln.startswith("7. "))
        self.assertIn("<MIN_HELDOUT>", step7)
        self.assertIn("驗證必判 NE", step7)
        self.assertEqual(patrolbrief.template_problems(self.sop), [])
        self.assertEqual(fx.sop_problems(self.sop), [])
        self.assertEqual(fx5.sop_p5_problems(self.sop), [])

    def test_AT_747_14_2_the_brief_carries_the_minimum_from_params(self):
        R = base_repo()
        params = si_check.params_for(R, *si_params.SCHED_KEYS, "stop_after_bad",
                                     "max_proposals_per_run")
        ctx = patrol.Ctx(R, O + H, False, patrol.Deps(), params)
        brief = patrolrun.compose(ctx, fx.rid(1), "f", iso(O), [])
        self.assertIn("下限 5", brief)
        self.assertNotIn("<MIN_HELDOUT>", brief)
        stripped = self.sop.replace("<MIN_HELDOUT>", "")
        self.assertIn("PLACEHOLDER-MISSING:MIN_HELDOUT", patrolbrief.template_problems(stripped))
        fx.set_params(R, min_heldout=7)
        params7 = si_check.params_for(R, *si_params.SCHED_KEYS, "stop_after_bad")
        ctx7 = patrol.Ctx(R, O + H, False, patrol.Deps(), params7)
        self.assertIn("下限 7", patrolrun.compose(ctx7, fx.rid(1), "f", iso(O), []))

    def test_AT_747_14_E_1_stale_wording_is_gone_and_new_sections_precede_the_template(self):
        self.assertNotIn("sched_auto_push` 只准 false", self.sop)
        self.assertNotIn("sched_auto_push 只准 false", self.sop)
        opening = self.part(self.sop, "巡邏與無人運轉（P4）").split("\n")[1:4]
        self.assertTrue(any("巡邏器本體不 push" in ln and "自動推送（P7）" in ln for ln in opening),
                        opening)
        tpl = self.sop.index("## 無人運轉任務書範本")
        for key in ("## 自動推送（P7", "## 巡邏快照與 M 類自動推進（P7"):
            at = self.sop.find(key)
            self.assertTrue(0 <= at < tpl, key)
        self.assertEqual(patrolbrief.template_of(self.sop).count("# 無人運轉任務書"), 1)


class TestSystem(P7TestCase):
    """AC-P7-090 自增 AC 的 RD 部分：純度、行數、黃金樣本、範圍守衛。"""

    def test_AT_790_1_E_1_the_new_files_have_teeth_in_the_registry_judge(self):
        import test_selfimproving_capability as cap
        reg = dict(cap.CAPABILITY)
        self.assertEqual({k: reg[k] for k in ("nextstep.py", "propdetail.py", "patrolreport.py")},
                         {"nextstep.py": "ro", "propdetail.py": "ro", "patrolreport.py": "rw"})
        self.assertEqual(cap.capability_problems(cap.PKG, reg, cap.ENTRY), [])
        injections = {
            "nextstep": ("\nopen('x', 'w')\n", "寫入"),
            "propdetail": ("\nimport socket\n", "socket"),
            "patrolreport": ("\nimport subprocess\n", "subprocess"),
        }
        for key, (code, cause) in injections.items():
            with self.subTest(key):
                root = fx.new_dir("capcopy")
                pkg = root / "lib" / "selfimproving"
                shutil.copytree(cap.PKG, pkg, ignore=shutil.ignore_patterns("__pycache__"))
                target = pkg / f"{key}.py"
                target.write_text(target.read_text(encoding="utf-8") + code, encoding="utf-8")
                got = cap.capability_problems(pkg, reg, cap.ENTRY)
                self.assertTrue([g for g in got if f"{key}.py" in g and cause in g], got)
        short = {k: v for k, v in reg.items() if k != "nextstep.py"}
        self.assertTrue([g for g in cap.capability_problems(cap.PKG, short, cap.ENTRY)
                         if "nextstep.py" in g and "未登記" in g])
        for name, banned in (("propdetail.py", {"os"}),
                             ("patrolreport.py", {"runner", "patrol", "patrolrun", "patrolpush",
                                                  "subprocess"})):
            tree = ast.parse((PKG / name).read_text(encoding="utf-8"))
            names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                     for a in n.names}
            names |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                      and n.level == 1 for a in n.names}
            self.assertEqual(names & banned, set(), name)
        lines = (PKG / "propdetail.py").read_text(encoding="utf-8").splitlines()
        self.assertEqual([ln for ln in lines if "environ" in ln], [])

    def test_AT_790_1_1_the_capability_registry_grows_by_exactly_the_six_new_files(self):
        import test_selfimproving_capability as cap
        reg = cap.CAPABILITY
        self.assertEqual(cap.capability_problems(cap.PKG, reg, cap.ENTRY), [])
        self.assertEqual(len(reg), 72 + 6)  # P6 現值 72＋本鍵六個新檔
        want = {"nextstep.py": "ro", "propdetail.py": "ro", "memdir.py": "ro",
                "pushguard.py": "ro", "patrolreport.py": "rw", "patrolpush.py": "exec"}
        self.assertEqual({k: reg.get(k) for k in want}, want)
        texts = {p.name: p.read_text(encoding="utf-8") for p in cap.PKG.glob("*.py")}
        self.assertEqual({n for n, t in texts.items() if "subprocess" in t},
                         {"git.py", "runner.py"})
        importers = {n for n, t in texts.items()
                     if "runner" in cap._rel_imports(t, cap.PKG.name)}
        self.assertIn("patrolpush.py", importers)
        self.assertEqual({n for n in importers if reg.get(n) != "exec"}, set())
        self.assertEqual({n for n, t in texts.items() if cap._abs_imports(t) & cap.NET_MODULES},
                         {"fetch.py"})
        self.assertEqual(sorted(n for n, v in reg.items() if v == "net"),
                         ["fetch.py", "research.py"])

    def test_AT_790_2_1_every_sync_site_holds_its_p7_value_and_the_loc_ratchet(self):
        import selfimproving
        from lib.selfimproving import unattended
        self.assertEqual(len(si_params.PARAM_SPECS), 47)
        self.assertEqual(len(unattended.C_CLASS), 16)
        self.assertEqual(len(selfimproving._HELP), 30)
        self.assertEqual((len(si_events.KINDS), len(si_check.ITEM_IDS)), (27, 35))
        self.assertEqual(si_params.CHECK_RULES_REV, 6)
        self.assertEqual(sorted(si_params.FINGERPRINT_EXCLUDED),
                         ["research_registry.json", "research_sources.json"])
        self.assertEqual(len(export.KINDS), 6)
        sys.path.insert(0, str(ROOT / "AutoClaude" / "tools"))
        try:
            import check_loc_budget as loc
        finally:
            sys.path.pop(0)
        for name, p6, cap_ in (("patrol", 356, 400), ("patrolrun", 339, 400)):
            now = loc.count_loc(PKG / f"{name}.py")
            self.assertLessEqual(now, cap_, name)
            self.assertLessEqual(now - p6, 30, f"{name}：新邏輯一律進新模組（淨增 {now - p6}）")
        for name in ("nextstep", "propdetail", "patrolreport"):
            self.assertLessEqual(loc.count_loc(PKG / f"{name}.py"), 400, name)
        self.assertEqual(export.KINDS, ("observations", "events", "proposals", "runs", "status",
                                        "issues"))
        self.assertEqual((len(si_events.KINDS), len(issuemap.EVENT_LABELS)), (27, 27))
        self.assertEqual(si_params.CHECK_RULES_REV, 6)

    def test_AT_790_3_1_rd_part_old_outputs_do_not_change(self):
        R = base_repo()
        pid = add_prop(R, 124, "verified")
        committed(R)
        res = self.check(R)
        self.assertEqual(len(res["items"]), 35)
        self.assertEqual(len(json.loads(self.M(R, "status", "--json")[1])), 20)
        _, lst, _ = self.M(R, "export", "--kind", "proposals", "--json")
        item = json.loads(lst)["items"][0]
        self.assertEqual(item["id"], pid)
        self.assertEqual(len(item), 19)
        rig = Rig7()
        self.assertEqual(self.beat7(self.enabled_repo(), O + H, rig)[0], 0)

    def test_AT_790_4_1_scope_guard_needs_an_explicit_base(self):
        base = px.scope_base()
        if base is None:
            print("[AT-790-4-1] guard-not-triggered (no SI_SCOPE_BASE)")
        else:
            self.assertEqual(self.scope_problems(ROOT, base), [], f"基準 {base}")
        bad, b0 = px.scope_fixture({"README.md": "x\n"}, {
            "tools/lib/selfimproving/nextstep.py": "a\n",
            "docs/01_requirements/SelfImproving_PRD.md": "p\n"})
        good, g0 = px.scope_fixture({"README.md": "x\n"}, {
            "tools/lib/selfimproving/nextstep.py": "a\n",
            "tools/tests/fixtures/selfimproving/p7/patrol.golden.json": "{}\n"})
        for repo in (bad, good):
            self.addCleanup(shutil.rmtree, repo.parent, True)
        prd = "docs/01_requirements/SelfImproving_PRD.md"
        self.assertEqual(self.scope_problems(bad, b0), [prd] * 2)
        self.assertEqual(self.scope_problems(good, g0), [])

    def test_AT_790_4_2_the_four_scope_guards_agree_on_a_typical_p7_diff(self):
        import test_selfimproving_backtest as p6
        import test_selfimproving_fourq_gate as p5
        import test_selfimproving_schedule_gate as p4
        lib = "tools/lib/selfimproving/"
        typical = {f"{lib}{n}.py": "a\n" for n in ("nextstep", "propdetail", "memdir", "pushguard",
                                                     "patrolreport", "patrolpush", "export")}
        for n in ("report", "memory", "push"):
            typical[f"tools/tests/test_selfimproving_p7_{n}.py"] = "t\n"
        typical.update({
            "tools/tests/_selfimproving_p7_fixtures.py": "f\n",
            "docs/06_quality/SelfImproving_Protocol/params.json": "{}\n",
            "docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md": "b\n",
            "tools/selfimproving.py": "s\n",
            "tools/tests/test_selfimproving_capability.py": "c\n",
            "tools/tests/test_selfimproving_schedule_gate.py": "g\n"})
        guards = {"P4": p4.scope_problems, "P5": p5.scope_problems, "P6": p6.scope_problems,
                  "P7": self.scope_problems}
        good, g0 = px.scope_fixture({"README.md": "x\n"}, typical)
        bad, b0 = px.scope_fixture({"README.md": "x\n"}, {**typical, "AgentConsole/x": "z\n"})
        for repo in (good, bad):
            self.addCleanup(shutil.rmtree, repo.parent, True)
        for name, fn in guards.items():
            with self.subTest(name):
                self.assertEqual(fn(good, g0), [], "典型 P7 差分被誤判")
                self.assertNotEqual(fn(bad, b0), [], "夾帶 AgentConsole 卻沒紅")
        self.assertTrue(p7x.P7_FORBIDDEN and not any(
            "params.json" in f or "P0_Baseline" in f for f in p6.FORBIDDEN))

    @staticmethod
    def scope_problems(root: Path, base: str) -> list[str]:
        touched, outside, frozen = px.scope_verdict(px.committed_names(root, base),
                                                    p7x.P7_ALLOWED, p7x.P7_FORBIDDEN)
        return [*outside, *frozen] if touched else []

    def golden(self, name: str) -> bytes:
        path = p7x.GOLDEN_DIR / name
        self.assertTrue(path.is_file(), f"黃金樣本缺：{path}")
        return path.read_bytes()

    def test_AT_790_5_1_golden_samples_are_reproduced_byte_for_byte(self):
        for name, make in (("patrol.golden.json", p7x.golden_patrol),
                           ("detail.golden.json", p7x.golden_detail)):
            with self.subTest(name):
                raw = self.golden(name)
                self.assertEqual(make(self), raw, "產生規則漂移或樣本被改")
                self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
                self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n")
                                and b"\r" not in raw)
                self.assertEqual(p7x.dump(json.loads(raw.decode("utf-8"))), raw)
        pat = json.loads(self.golden("patrol.golden.json").decode("utf-8"))
        self.assertEqual((pat["off"], pat["truncated"], pat["push"]["state"]),
                         (False, False, "waiting-login"))
        self.assertEqual({(r["status"], r["permanent"]) for r in pat["ingest"]},
                         {("rejected", True), ("deferred", False)})
        self.assertEqual({r["who"] for r in pat["props"]}, {"掌舵者", "巡邏器", "主機管理者"})
        self.assertEqual((len(pat["runs"]["live"]), len(pat["runs"]["waiting"])), (1, 1))
        self.assertTrue(pat["schedule"]["current"] and pat["schedule"]["last_skip"]["audit_ref"])
        det = json.loads(self.golden("detail.golden.json").decode("utf-8"))["detail"]
        self.assertTrue(all(det[k] is not None for k in DETAIL_KEYS))
        self.assertTrue(det["sandbox"]["failText"])
        self.assertTrue(det["verify"]["reasons"])
        self.assertTrue(det["heldout"]["belowMin"] and det["heldout"]["neNote"])
        self.assertTrue(any(s.get("missing") for s in det["sourceObs"]))
        self.assertGreaterEqual(len(det["timeline"]), 3)

    def test_AT_790_5_E_1_the_samples_match_the_contract_and_leak_nothing(self):
        pat = json.loads(self.golden("patrol.golden.json").decode("utf-8"))
        self.assertEqual(list(pat), TOP_KEYS)
        self.assertEqual(list(pat["push"]), PUSH_KEYS)
        self.assertEqual(list(pat["runs"]), ["live", "waiting", "queued"])
        self.assertEqual(list(pat["schedule"]), ["enabled", "current", "last_skip"])
        for row in pat["ingest"]:
            self.assertEqual(list(row),
                             ["audit_ref", "kind", "status", "code", "text", "permanent"])
        for row in pat["props"]:
            self.assertEqual(list(row), ["id", "state", "code", "who", "text"])
        det_item = json.loads(self.golden("detail.golden.json").decode("utf-8"))
        self.assertEqual(set(det_item["detail"]), DETAIL_KEYS)

        def fits(code: str, text: str) -> bool:
            rx = ".*".join(re.escape(part)
                           for part in nextstep.REASON[code]["text"].split("{detail}"))
            return re.fullmatch(rx, text) is not None
        pairs = [(r["code"], r["text"]) for r in (*pat["ingest"], *pat["props"],
                                                   *pat["runs"]["waiting"])]
        pairs += [(pat["push"]["code"], pat["push"]["text"]),
                  (pat["schedule"]["current"]["code"], pat["schedule"]["current"]["text"]),
                  (pat["schedule"]["last_skip"]["code"], pat["schedule"]["last_skip"]["text"])]
        det = det_item["detail"]
        pairs += [(r["code"], r["text"]) for r in det["verify"]["reasons"]]
        pairs += [(det["sandbox"]["failCode"], det["sandbox"]["failText"]),
                  (det["next"]["code"], det["next"]["text"])]
        for code, text in pairs:
            self.assertIn(code, nextstep.REASON, code)
            if code != "WAIT-PROMOTE-DECISION":
                self.assertTrue(fits(code, text), (code, text))
        blob = self.golden("patrol.golden.json") + self.golden("detail.golden.json")
        text = blob.decode("utf-8")
        self.assertIsNone(re.search(r"://[^/\s\"]*@", text))
        self.assertNotIn("token=", text.lower())
        self.assertNotIn("ghp_", text)


if __name__ == "__main__":
    unittest.main()
