# 受測面：tools/lib/selfimproving/schedcheck.py（程式碼鎖，非散文）
"""SelfImproving P4 的 `check` 兩新項、`console_pending` 新 kind、事件欄位表、`params` 九鍵與
範圍守衛（TCS-SelfImproving-P4 §2 B 節中屬 PKG-ROOT-SCHED 的 AT：AT-437-5、AT-440-1、
AT-440-2、AT-440-8；R139、R140、R158、R159、R164）。

留位（理由：以下 AT 的被測物由 PKG-ROOT-PATROL 與收尾單人窗口建立，本棒不得先寫成假綠）——
AT-436-4-x、AT-436-5-2、AT-438-7-1、AT-440-3-x（巡邏、`schedarm`、`runner` 匯入者四檔）、AT-440-4-x
（`sop_p4_problems`）、AT-440-5-x、AT-440-6-x、AT-440-7-x（26 個動詞與全部 105 個 AT 的錨定）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import unittest

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
from _selfimproving_p4_fixtures import D1, MIN, H, O, P4Case, iso

from lib.selfimproving import check as si_check
from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold
from lib.selfimproving import params as si_params
from lib.selfimproving import sched

ROOT = fx.ROOT
P = fx.params_dict()


def setUpModule() -> None:
    fx.setup("si_p4_")


def tearDownModule() -> None:
    fx.teardown()


def raw_events(*items) -> list[dict]:
    return fx.compose(list(items), "0" * 40)


class TestConsolePending(P4Case):
    def test_AT_437_5_1_new_kinds_appear_then_vanish(self):
        R = fx4.p4_base()
        sref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 120))
        rref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        want = [{"audit_ref": r, "kind": k} for r, k in sorted(
            [(sref, "sched-set"), (rref, "run-request")])]
        self.assertEqual(self.status(R)["console_pending"]["items"], want)
        for ref, verb in ((sref, "sched"), (rref, "open")):
            rc, out, err = self.ingest(R, ref, verb=verb)
            self.assertEqual(rc, 0, out + err)
        after = self.status(R)["console_pending"]
        self.assertEqual((after["count"], after["items"]), (0, []))
        rc, out, _ = self.M(R, "export", "--json", "--kind", "status")
        self.assertEqual(json.loads(out)["items"][0]["console_pending"],
                         {"status": "NOT-EVALUABLE", "reason": "export-reads-no-home"})

    def test_AT_437_5_2_check_has_35_items_and_rules_rev_5(self):
        ev = [fx4.sched_set_ev(O), fx4.run_open_f_ev(1, O + H, due_at=O),
              fx4.sched_skip_ev(O + 2 * H, "blackout", due_at=O),
              fx4.sched_skip_ev(O + 3 * H, "run-open", due_at=O, audit_ref=fx2.new_uuid())]
        res = self.check(fx4.p4_base(events=ev))
        ids = [i["id"] for i in res["items"]]
        self.assertEqual(len(ids), 35)
        self.assertEqual(ids[:33], list(si_check.ITEM_IDS[:33]))
        self.assertEqual(ids[33:], ["sched.events", "run.trigger_f_has_patrol_by"])
        self.assertEqual([self.S(res, i) for i in ids[33:]], ["PASS", "PASS"])
        self.assertEqual((si_params.CHECK_RULES_REV, res["_rc"]), (5, 0), res["overall"])
        real = self.run_main(["check", "--repo", str(ROOT), "--json"])
        self.assertEqual(real[0], 0, real[1][-400:])
        self.assertEqual(len(json.loads(real[1])["items"]), 35)


class TestSchedCheckCodes(P4Case):
    def codes(self, *items, item: str = "sched.events"):
        res = self.check(fx4.p4_base(events=list(items)))
        self.assertEqual(self.S(res, "events.structure"), "PASS" if item == "sched.events"
                         else self.S(res, "events.structure"))
        return {c for _, c in self.F(res, item)}, res

    def test_AT_437_5_E_1_sched_events_four_codes(self):
        s0 = fx4.sched_set_ev(O)
        f1 = fx4.run_open_f_ev(1, O + H, due_at=O)
        cases = {
            "range": ([fx4.sched_set_ev(O, period=59)], {"SCHED-PERIOD-RANGE"}),
            "run-dup": ([s0, f1, fx4.run_open_f_ev(2, O + 2 * H, due_at=O)], {"SCHED-RUN-DUP"}),
            "skip-dup": ([s0, fx4.sched_skip_ev(O + H, "blackout", due_at=O),
                          fx4.sched_skip_ev(O + 2 * H, "blackout", due_at=O)],
                         {"SCHED-SKIP-DUP"}),
            "skip-due": ([s0, fx4.sched_skip_ev(O + H, "blackout", due_at=O + MIN)],
                         {"SCHED-SKIP-DUE"}),
            "console-dup": ([s0, fx4.sched_skip_ev(O + H, "run-open", due_at=O, audit_ref=fx.UUID),
                             fx4.sched_skip_ev(O + 2 * H, "run-open", due_at=O,
                                               audit_ref=fx.UUID)], {"SCHED-SKIP-DUP"}),
        }
        for label, (events, want) in cases.items():
            with self.subTest(label):
                got, res = self.codes(*events)
                self.assertEqual(got, want)
                self.assertEqual(self.S(res, "sched.events"), "FAIL")
        for label, events in {
                "control": [s0, f1, fx4.sched_skip_ev(O + 2 * H, "blackout", due_at=O)],
                "two-console-refs": [s0, fx4.sched_skip_ev(
                    O + H, "run-open", due_at=O, audit_ref=fx.UUID), fx4.sched_skip_ev(
                    O + 2 * H, "run-open", due_at=O, audit_ref=fx.UUID2)]}.items():
            with self.subTest(label):
                got, res = self.codes(*events)
                self.assertEqual((got, self.S(res, "sched.events")), (set(), "PASS"))

    def test_AT_437_5_E_2_trigger_f_three_codes(self):
        item = "run.trigger_f_has_patrol_by"
        s0 = fx4.sched_set_ev(O)
        good = [s0, fx4.run_open_f_ev(1, O + H, due_at=O),
                fx4.run_open_f_ev(2, O + D1 + H, due_at=O + D1)]
        got, res = self.codes(*good, item=item)
        self.assertEqual((got, self.S(res, item)), (set(), "PASS"))  # 含 k 為 0 的邊界
        bad = {
            "by": ([s0, fx4.run_open_f_ev(1, O + H, due_at=O, by="main")], "TRIGGER-F-BY"),
            "no-due-at": ([s0, fx4.run_open_f_ev(1, O + H)], "TRIGGER-F-DUE-AT"),
            "off-grid": ([s0, fx4.run_open_f_ev(1, O + D1 + H, due_at=O + D1 + MIN)],
                         "TRIGGER-F-DUE-AT"),
            "no-origin": ([fx4.run_open_f_ev(1, O, due_at=O)], "TRIGGER-F-NO-ORIGIN"),
            "old-grid": ([s0, fx4.sched_set_ev(O + 20 * H, period=720),
                          fx4.run_open_f_ev(1, O + 21 * H, due_at=O)], "TRIGGER-F-DUE-AT"),
        }
        for label, (events, code) in bad.items():
            with self.subTest(label):
                got, res = self.codes(*events, item=item)
                self.assertEqual((got, self.S(res, item)), ({code}, "FAIL"))

    def test_AT_437_5_E_3_absent_carrier_and_empty_sets(self):
        absent = self.check(fx4.p4_base())
        for item in ("sched.events", "run.trigger_f_has_patrol_by"):
            self.assertEqual(self.S(absent, item), "NE")
            codes = {c for _, c in self.F(absent, item)}
            self.assertEqual((absent["_item"][item]["blocking"], codes),
                             (False, {"CARRIER-NOT-ESTABLISHED"}))
        self.assertEqual(absent["_rc"], 0)
        plain = self.check(fx4.p4_base(events=[fx.ev(
            "run.open", "main", t=iso(O), run=fx.rid(1), trigger="a")]))
        self.assertEqual([self.S(plain, i) for i in ("sched.events",
                                                     "run.trigger_f_has_patrol_by")], ["PASS"] * 2)


def good_events() -> dict[str, dict]:
    sets = {"console": fx4.sched_set_ev(O, carrier="console", reason="啟用"),
            "transcript": fx4.sched_set_ev(O),
            "host": fx4.sched_set_ev(O + H, enabled=False)}
    skips = {"skip": fx4.sched_skip_ev(O, "blackout", due_at=O),
             "skip-console": fx4.sched_skip_ev(O, "run-open", due_at=O, audit_ref=fx.UUID)}
    opens = {"open-f": fx4.run_open_f_ev(1, O, due_at=O)}
    return {**sets, **skips, **opens}


def composed(ev: dict) -> dict:
    return fx.compose([ev], "0" * 40, [3])[0]


class TestEventTables(unittest.TestCase):
    def test_AT_440_1_1_vocabulary_23_and_legal_events(self):
        self.assertEqual(len(si_events.KINDS), 23)
        self.assertTrue({"sched.set", "sched.skip"} <= set(si_events.KINDS))
        for label, ev in good_events().items():
            self.assertEqual(si_events.validate(composed(ev)), [], label)
        console_open = fx.ev("run.open", "console", t=iso(O), run=fx.rid(1), trigger="a",
                             carrier="console", audit_ref=fx.UUID, audit_sha256=fx.H(7),
                             key_id="00000000", decider="admin")
        self.assertEqual(si_events.validate(composed(console_open)), [])
        base = raw_events(fx.ev("run.open", "main", t=iso(O), run=fx.rid(1), trigger="a"))
        extra = raw_events(*good_events().values())
        mixed = [base[0], *[{**e, "seq": e["seq"] + 1} for e in extra]]
        plain = si_fold.fold(si_events.sound(base))
        fl = si_fold.fold(si_events.sound(
            [e for e in mixed if e["kind"] in ("sched.set", "sched.skip") or e["seq"] == 1]))
        self.assertEqual((list(fl.props), list(fl.runs)), (list(plain.props), list(plain.runs)))
        self.assertEqual((fl.problems, fl.suspended), (plain.problems, plain.suspended))

    def test_AT_440_1_E_1_each_deformation_gets_exactly_one_code(self):
        g = good_events()
        miss, unk, typ = "EVENT-KEY-MISSING", "EVENT-KEY-UNKNOWN", "EVENT-TYPE"

        def edit(name, fn):
            obj = composed(g[name])
            fn(obj)
            return obj
        cases = [
            ("缺 enabled", edit("transcript", lambda o: o.pop("enabled")), miss),
            ("缺 carrier", edit("transcript", lambda o: o.pop("carrier")), miss),
            ("enabled 字串", edit("transcript", lambda o: o.update(enabled="true")), typ),
            ("period 布林", edit("transcript", lambda o: o.update(period_minutes=True)), typ),
            ("console 缺 audit_ref", edit("console", lambda o: o.pop("audit_ref")), miss),
            ("host 配 enabled 真", edit("host", lambda o: o.update(enabled=True)), typ),
            ("transcript 帶 audit_ref", edit("transcript", lambda o: o.update(audit_ref=fx.UUID)),
             unk),
            ("skip 第八值", edit("skip", lambda o: o.update(reason="other")), typ),
            ("detail 121", edit("skip", lambda o: o.update(detail="字" * 121)), typ),
            ("due_at 缺 offset", edit("skip", lambda o: o.update(due_at="2026-11-02T08:00:00")),
             typ),
            ("只帶 audit_ref", edit("skip", lambda o: o.update(audit_ref=fx.UUID)), miss),
            ("f 缺 due_at", edit("open-f", lambda o: o.pop("due_at")), miss),
            ("a 帶 due_at", composed(fx.ev("run.open", "main", t=iso(O), run=fx.rid(1),
                                           trigger="a", due_at=iso(O))), unk),
            ("console run.open 缺 decider", composed(fx.ev(
                "run.open", "console", t=iso(O), run=fx.rid(1), trigger="a", carrier="console",
                audit_ref=fx.UUID, audit_sha256=fx.H(7), key_id="00000000")), miss),
            ("sched.set 表外鍵", edit("transcript", lambda o: o.update(digest=fx.H(1))), unk),
            ("sched.skip 表外鍵", edit("skip", lambda o: o.update(extra=1)), unk),
        ]
        for label, obj, code in cases:
            with self.subTest(label):
                self.assertEqual([c for c, _ in si_events.validate(obj)], [code])

    def test_AT_440_1_E_2_old_events_unchanged_and_message_counts(self):
        for trig in "abcde":
            old = composed(fx.ev("run.open", "main", t=iso(O), run=fx.rid(1), trigger=trig))
            self.assertEqual(si_events.validate(old), [], trig)
        bad = composed(fx.ev("run.open", "main", t=iso(O), run=fx.rid(1), trigger="g"))
        self.assertEqual([c for c, _ in si_events.validate(bad)], ["EVENT-TYPE"])
        unknown = {**composed(fx.ev("run.open", "main", t=iso(O), run=fx.rid(1), trigger="a")),
                   "kind": "sched.bogus"}
        out = si_events.validate(unknown)
        self.assertEqual([c for c, _ in out], ["EVENT-KIND"])
        self.assertIn("23 個詞彙", out[0][1])
        lines = si_events.read_lines((ROOT / si_events.LEDGER_REL).read_bytes())
        self.assertEqual([x for ln in lines if ln.obj for x in si_events.validate(ln.obj)], [])


class TestParamsNine(unittest.TestCase):
    NINE = {"sched_heartbeat_minutes": 15, "sched_period_minutes_default": 1440,
            "sched_period_minutes_min": 60, "sched_period_minutes_max": 10080,
            "sched_run_budget_minutes": 90, "sched_blackout_local": ["21:00-01:30"],
            "sched_driver_quiet_minutes": 30, "sched_auto_commit": True, "sched_auto_push": False}

    def real(self) -> dict:
        return json.loads(fx.REAL_PARAMS.read_text(encoding="utf-8"))

    def test_AT_440_2_1_41_keys_defaults_and_real_check_green(self):
        real = self.real()
        self.assertEqual(set(real), set(si_params.PARAM_SPECS))
        self.assertEqual(len(real), 41)
        raw = fx.REAL_PARAMS.read_bytes()
        self.assertEqual(si_params.params_file_problems(raw), [])
        self.assertEqual({k: real[k] for k in self.NINE}, self.NINE)
        self.assertEqual(si_params.param_findings(real), [])
        self.assertEqual(si_params.SCHED_KEYS, tuple(self.NINE))

    def test_AT_440_2_E_1_types_ranges_and_cross_keys(self):
        from lib import unattended_authz
        cap = unattended_authz.RESUME_BG_WAIT_CEILING_SECONDS // 60
        base = self.real()

        def codes(**kw):
            return {(f.subject, f.code) for f in si_params.param_findings({**base, **kw})}
        self.assertEqual(codes(), set())
        for key in self.NINE:
            gone = {k: v for k, v in base.items() if k != key}
            self.assertEqual({(f.subject, f.code) for f in si_params.param_findings(gone)},
                             {(key, "PARAM-MISSING")}, key)
        cases = {
            "commit-int": ({"sched_auto_commit": 1}, ("sched_auto_commit", "PARAM-TYPE")),
            "hb-bool": ({"sched_heartbeat_minutes": True}, ("sched_heartbeat_minutes",
                                                            "PARAM-TYPE")),
            "same-ends": ({"sched_blackout_local": ["21:00-21:00"]}, ("sched_blackout_local",
                                                                      "PARAM-RANGE")),
            "short-hour": ({"sched_blackout_local": ["9:00-10:00"]}, ("sched_blackout_local",
                                                                      "PARAM-RANGE")),
            "non-str": ({"sched_blackout_local": [1]}, ("sched_blackout_local", "PARAM-TYPE")),
            "push-true": ({"sched_auto_push": True}, ("sched_auto_push", "PARAM-RANGE")),
            "min>default": ({"sched_period_minutes_min": 2000},
                            ("sched_period_minutes_min", "PARAM-RANGE")),
            "default>max": ({"sched_period_minutes_default": 20000},
                            ("sched_period_minutes_default", "PARAM-RANGE")),
            "hb>min": ({"sched_heartbeat_minutes": 61}, ("sched_heartbeat_minutes",
                                                         "PARAM-RANGE")),
            "budget+1": ({"sched_run_budget_minutes": cap + 1},
                         ("sched_run_budget_minutes", "PARAM-RANGE")),
        }
        for label, (kw, want) in cases.items():
            with self.subTest(label):
                self.assertEqual(codes(**kw), {want})
        self.assertEqual(codes(sched_run_budget_minutes=cap, sched_blackout_local=[],
                               sched_auto_push=False), set())

    def test_AT_440_2_E_2_blackout_covers_triggers_fingerprint_and_baseline(self):
        import check_scheduled_task_drift as drift
        trig = drift.load_trigger_expectations(ROOT / "tools" / "scheduled_task_expectations.json")
        self.assertTrue(trig)
        ranges = self.real()["sched_blackout_local"]
        for task, hm in trig.items():
            h, m = (int(x) for x in hm.split(":"))
            for extra in (0, 80):
                total = (h * 60 + m + extra) % 1440
                self.assertTrue(sched.blackout_hit(f"{total // 60:02d}:{total % 60:02d}", ranges),
                                (task, hm, extra))
        self.assertFalse(sched.blackout_hit("21:30", ["22:00-23:00"]))  # 不涵蓋的副本判得出
        rev = si_params.CHECK_RULES_REV
        fp, parts = si_params.fingerprint(ROOT, self.real())
        copy = fx.new_dir("fp")
        import shutil
        shutil.copytree(ROOT / si_params.PROTOCOL_REL, copy / si_params.PROTOCOL_REL)
        pj = copy / si_params.PROTOCOL_REL / "params.json"
        pj.write_bytes(pj.read_bytes().replace(b'"sched_auto_commit": true',
                                               b'"sched_auto_commit": false'))
        fp2, parts2 = si_params.fingerprint(copy, self.real())
        self.assertNotEqual(parts["manifest"], parts2["manifest"])
        self.assertNotEqual(fp, fp2)
        self.assertEqual((parts["metrics_rev"], parts["check_rules_rev"]),
                         (parts2["metrics_rev"], rev))
        text = (ROOT / "docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md").read_text(
            encoding="utf-8")
        raw = fx.REAL_PARAMS.read_bytes()
        row = next(ln for ln in text.splitlines() if ln.startswith("| 協定目錄 params.json"))
        self.assertIn(hashlib.sha256(raw).hexdigest(), row)
        self.assertIn(f"{len(raw)} bytes", row)
        self.assertIn(fp, next(ln for ln in text.splitlines() if ln.startswith("| 指紋")))
        rev_row = next(ln for ln in text.splitlines() if ln.startswith("| CHECK_RULES_REV"))
        self.assertRegex(rev_row, rf"^\| CHECK_RULES_REV \| {rev}")


ALLOWED = (
    re.compile(r"^tools/lib/selfimproving/[a-z_]+\.py$"),
    re.compile(r"^tools/(selfimproving\.py|si_patrol_tick\.ps1|install_windows_nightly\.ps1"
               r"|scheduled_task_expectations\.json)$"),
    re.compile(r"^tools/tests/(_selfimproving_[a-z0-9_]+|test_selfimproving_[a-z0-9_]+"
               r"|test_install_windows_nightly)\.py$"),
    re.compile(r"^docs/06_quality/SelfImproving_Protocol/params\.json$"),
    re.compile(r"^docs/06_quality/SelfImproving_LedgerDb_P0_Baseline\.md$"),
)
FROZEN = (".claude/", "AgentConsole/", ".github/", "autoclaude/", "AutoClaude/autoclaude/",
          "tools/lib/schedule_backend.py", "tools/lib/resume_route.py",
          "tools/lib/unattended_authz.py", "tools/lib/model_roles.py",
          "tools/check_scheduled_task_drift.py", "docs/01_requirements/SelfImproving_PRD.md",
          "docs/05_development/SelfImproving_Operations_SOP.md",
          "docs/03_testing/contracts/TCS-SelfImproving-P")
# D-IMP-5：本檔的 oracle（P4 TCS）由主控追加勘誤，不屬 Developer 守衛面
FROZEN_EXEMPT = ("docs/03_testing/contracts/TCS-SelfImproving-P4-",)
_BANNED = ("unittest\\.sk" + "ip", "sk" + "ipTest", "sk" + "ipIf", "sk" + "ipUnless",
           "pytest\\.sk" + "ip", "mark\\.sk" + "ip", "xf" + "ail")  # 自身不含字面，免自我命中
NO_SKIP = re.compile("|".join(_BANNED))


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                          encoding="utf-8", check=False)


def git_names(*args: str) -> list[str]:
    cp = _git(*args)
    return [ln for ln in cp.stdout.splitlines() if ln.strip()] if cp.returncode == 0 else []


class TestScope(unittest.TestCase):
    def test_AT_440_8_1_changes_stay_inside_the_allowed_set(self):
        base = os.environ.get("SI_P4_BASE_SHA") or "HEAD~1"
        has_base = _git("rev-parse", "--verify", "--quiet", base + "^{commit}").returncode == 0
        names = {*(git_names("diff", "--name-only", base) if has_base else []),
                 *git_names("ls-files", "--others", "--exclude-standard")}
        note = (f"基準 {base}（未設 SI_P4_BASE_SHA 時取 HEAD 的父 commit"
                + ("" if has_base else "；父 commit 不可得，只看未追蹤檔") + "）")
        touched = [n for n in names if any(rx.match(n) for rx in ALLOWED)]
        if not touched:  # D-IMP-5：差異不含 P4 面＝範圍守衛未觸發，不把無關 commit 判紅
            print(f"[AT-440-8-1] {note}：差異不含 P4 面，範圍守衛未觸發")
        else:
            outside = sorted(n for n in names if not any(rx.match(n) for rx in ALLOWED))
            self.assertEqual(outside, [], note)
            frozen = sorted(n for n in names
                            if n.startswith(FROZEN) and not n.startswith(FROZEN_EXEMPT))
            self.assertEqual(frozen, [], note)
        for name in ("test_selfimproving_schedule_model", "test_selfimproving_schedule_gate",
                     "_selfimproving_p4_fixtures"):
            text = (ROOT / "tools" / "tests" / f"{name}.py").read_text(encoding="utf-8")
            self.assertIsNone(NO_SKIP.search(text), name)


if __name__ == "__main__":
    sys.exit(unittest.main())
