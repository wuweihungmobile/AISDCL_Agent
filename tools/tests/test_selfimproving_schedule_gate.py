# 受測面：tools/lib/selfimproving/schedcheck.py（程式碼鎖，非散文）
"""SelfImproving P4 的 `check` 兩新項、`console_pending` 新 kind、事件欄位表、`params` 九鍵與
範圍守衛（TCS-SelfImproving-P4 §2 B 節中屬 PKG-ROOT-SCHED 的 AT：AT-437-5、AT-440-1、
AT-440-2、AT-440-8；R139、R140、R158、R159、R164）。

PKG-ROOT-PATROL 補入的 AT（OS 載具、`schedarm`、能力登記、SOP、同步站點、錨定與入口）——
AT-436-4-x、AT-436-5-2、AT-438-7-1、AT-440-3-x、AT-440-4-x、AT-440-5-x、AT-440-6-x、AT-440-7-x。
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
from _selfimproving_p4_fixtures import D1, MIN, H, O, P4TestCase, iso

from lib.selfimproving import check as si_check
from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold
from lib.selfimproving import params as si_params
from lib.selfimproving import patrolbrief, runner, sched, schedarm

ROOT = fx.ROOT
P = fx.params_dict()
PKG = ROOT / "tools" / "lib" / "selfimproving"
INSTALLER = ROOT / "tools" / "install_windows_nightly.ps1"
EXPECT = ROOT / "tools" / "scheduled_task_expectations.json"
TICK = ROOT / "tools" / "si_patrol_tick.ps1"


def setUpModule() -> None:
    fx.setup("si_p4_")


def tearDownModule() -> None:
    fx.teardown()


def raw_events(*items) -> list[dict]:
    return fx.compose(list(items), "0" * 40)


class TestConsolePending(P4TestCase):
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


class TestSchedCheckCodes(P4TestCase):
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
    """受測模組 tools/lib/selfimproving/params.py：PARAM_SPECS 九鍵、界與跨鍵關係；
    對表 docs/06_quality/SelfImproving_Protocol/params.json 與基線文件三列。"""

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
            print(f"[AT-440-8-1] base={base} has_base={has_base} p4=0 guard-not-triggered")
        else:
            outside = sorted(n for n in names if not any(rx.match(n) for rx in ALLOWED))
            self.assertEqual(outside, [], note)
            frozen = sorted(n for n in names
                            if n.startswith(FROZEN) and not n.startswith(FROZEN_EXEMPT))
            self.assertEqual(frozen, [], note)
        for name in ("test_selfimproving_schedule_model", "test_selfimproving_schedule_gate",
                     "test_selfimproving_schedule_patrol", "test_selfimproving_schedule_advance",
                     "_selfimproving_p4_fixtures"):
            text = (ROOT / "tools" / "tests" / f"{name}.py").read_text(encoding="utf-8")
            self.assertIsNone(NO_SKIP.search(text), name)


# --------------------------------------------------------------------------- OS 任務載具（R161）
def code_only(text: str) -> str:
    text = re.sub(r"(?s)<#.*?#>", "", text)
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))


def installer_problems(installer: str, spec: dict) -> list[str]:
    """安裝器與期望表的三層鎖（逐任務逐值）：任務集合、期望值↔套用手段、小時數、principal、Register
    次數。"""
    tasks, out = spec["tasks"], []
    names = {n: v for v, n in re.findall(r"(?m)^\$((?:Smoke|Patrol)?TaskName)\s*=\s*'([^']+)'",
        installer)}
    if set(names) != set(tasks):
        out.append("TASK-SET")
    com = re.findall(r"Set-MultipleInstancesStopExisting\s+-Name\s+\$(\w+)", installer)
    for task, body in tasks.items():
        exp, var = body["expected"], names.get(task, "")
        sv = "patrolSettings" if var == "PatrolTaskName" else "settings"
        m = re.search(rf"\${sv}\s*=\s*New-ScheduledTaskSettingsSet((?:[^\n]*`[ \t]*\n)*[^\n]*)",
            installer)
        block = m.group(1) if m else ""
        if len(exp) != 7:
            out.append(f"KEYS:{task}")
        if ("-WakeToRun" in block) != (exp["Settings/WakeToRun"] == "true"):
            out.append(f"WAKE:{task}")
        hours = re.search(r"-ExecutionTimeLimit\s+\(New-TimeSpan\s+-Hours\s+(\d+)\)", block)
        if not hours or exp["Settings/ExecutionTimeLimit"] != f"PT{hours.group(1)}H":
            out.append(f"HOURS:{task}")
        if exp["Settings/MultipleInstancesPolicy"] == "StopExisting":
            ok = var in com and "-MultipleInstances IgnoreNew" not in block
        else:
            ok = bool(re.search(r"-MultipleInstances\s+IgnoreNew", block)) and var not in com
        if not ok:
            out.append(f"POLICY:{task}")
    regs = re.findall(r"(?m)^[ \t]*Register-ScheduledTask(?:[^\r\n]*`[ \t]*\r?\n)*[^\r\n]*",
                      code_only(installer))
    if len(regs) != 3 or any("-Principal $principal" not in r for r in regs):
        out.append("REGISTER")
    return out


class TestOsCarrier(P4TestCase):
    """受測模組 tools/install_windows_nightly.ps1 與 tools/scheduled_task_expectations.json：
    三支任務。"""

    def test_AT_436_4_1_three_tasks_and_per_task_locks(self):
        installer = INSTALLER.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
        spec = json.loads(EXPECT.read_text(encoding="utf-8"))
        self.assertEqual(installer_problems(installer, spec), [])
        t = spec["tasks"]
        self.assertEqual(set(t), {"AutoClaude_Nightly", "AutoClaude_WindowsSmoke",
            "AutoSDD_SI_Patrol"})
        self.assertEqual(len({frozenset(v["expected"]) for v in t.values()}), 1)
        self.assertEqual(len(t["AutoSDD_SI_Patrol"]["expected"]), 7)
        want = {"Settings/ExecutionTimeLimit": "PT1H", "Settings/WakeToRun": "false",
                "Settings/MultipleInstancesPolicy": "IgnoreNew",
                "Principals/Principal/LogonType": "S4U"}
        self.assertEqual({k: t["AutoSDD_SI_Patrol"]["expected"][k] for k in want}, want)
        self.assertNotIn("expected_trigger_time", t["AutoSDD_SI_Patrol"])
        for other in ("AutoClaude_Nightly", "AutoClaude_WindowsSmoke"):
            self.assertEqual(t[other]["expected"]["Settings/WakeToRun"], "true")
            self.assertEqual(t[other]["expected"]["Settings/MultipleInstancesPolicy"],
                "StopExisting")
            self.assertIn("expected_trigger_time", t[other])
        com = re.findall(r"Set-MultipleInstancesStopExisting\s+-Name\s+\$(\w+)", installer)
        self.assertEqual(sorted(com), ["SmokeTaskName", "TaskName"])
        self.assertIn("-MultipleInstances IgnoreNew", installer)
        mutated = {
            "ignorenew-removed": (installer.replace("  -MultipleInstances IgnoreNew", ""), spec),
            "patrol-hours-4": (installer.replace("-ExecutionTimeLimit (New-TimeSpan -Hours 1)",
                                                 "-ExecutionTimeLimit (New-TimeSpan -Hours 4)"),
                                                 spec),
            "patrol-policy-stopexisting": (installer, json.loads(json.dumps(spec).replace(
                '"Settings/MultipleInstancesPolicy": "IgnoreNew"',
                '"Settings/MultipleInstancesPolicy": "StopExisting"'))),
            "task-missing": (installer.replace("$PatrolTaskName = 'AutoSDD_SI_Patrol'\n", ""),
            spec),
        }
        for label, (text, sp) in mutated.items():
            with self.subTest(label):
                self.assertNotEqual(installer_problems(text, sp), [], label)
        names = git_names("diff", "--name-only", "HEAD", "--", "tools/lib/schedule_backend.py",
                          "tools/check_scheduled_task_drift.py")
        self.assertEqual(names, [])

    def test_AT_436_4_2_trigger_action_and_whatif(self):
        installer = INSTALLER.read_bytes().decode("utf-8-sig")
        self.assertRegex(installer, r"New-TimeSpan\s+-Minutes\s+\$HeartbeatMinutes")
        self.assertIn("sched_heartbeat_minutes", installer)
        self.assertNotRegex(code_only(installer), r"-Minutes\s+\d+")  # 不寫死第二份心跳分鐘數
        self.assertIn("New-ScheduledTaskTrigger -Daily -At '00:00'", installer)
        self.assertIn("-RepetitionDuration (New-TimeSpan -Days 1)", installer)
        arg_re = r"\$patrolAction = New-ScheduledTaskAction[^\n]*\n\s*-Argument \"([^\"]*)\""
        patrol_arg = re.search(arg_re, installer)
        self.assertIsNotNone(patrol_arg, "找不到巡邏任務 Action 的 -Argument 字串")
        for flag in ("-NoProfile", "-WindowStyle Hidden", "-ExecutionPolicy Bypass", "-File"):
            self.assertIn(flag, patrol_arg.group(1))  # D-IMP-7：逐旗標判在場（R84 同型）
        self.assertIn(r"tools\si_patrol_tick.ps1", installer)
        import test_install_windows_nightly as inst
        engine = inst._ps_engine()
        if engine is None:
            return  # 無引擎的平台只走靜態判準（不 skip）
        listing = [engine, "-NoProfile", "-Command",
                   "(Get-ScheduledTask -ErrorAction SilentlyContinue | ForEach-Object TaskName | "
                   "Sort-Object) -join ','"]

        def tasks() -> str:
            return subprocess.run(listing, capture_output=True, encoding="utf-8", errors="replace",
                                  check=False).stdout.strip()
        before = tasks()
        cp = subprocess.run([engine, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(INSTALLER), "-WhatIf"], capture_output=True, encoding="utf-8",
                            errors="replace", check=False)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        for name in ("AutoClaude_Nightly", "AutoClaude_WindowsSmoke", "AutoSDD_SI_Patrol"):
            self.assertIn(name, cp.stdout)
        self.assertEqual(tasks(), before)

    def test_AT_436_4_3_wrapper_script_key_surface(self):
        raw = TICK.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(raw.count(b"\r\n"), raw.count(b"\n"))
        text = raw.decode("utf-8-sig")
        self.assertNotRegex(text, r"\$Is(Windows|MacOS|Linux)\b|\?\?|&&")
        self.assertEqual(set(re.findall(r"\b[A-Z][A-Z0-9_]*AUDIT_KEY\b", text)),
                         {"CONSOLE_SI_AUDIT_KEY", "AUTOSDD_SI_AUDIT_KEY"})
        self.assertNotRegex(text, r"(?m)^\s*\.\s+\S|Invoke-Expression|\biex\b|Get-Content")
        self.assertIn("[System.IO.File]::ReadLines", text)
        self.assertRegex(text, r"-match '\^\\s\*CONSOLE_SI_AUDIT_KEY")
        self.assertRegex(text, r"\bbreak\b")
        for cmdlet in ("Write-Output", "Write-Host", "Out-File", "Add-Content", "Tee-Object"):
            for ln in text.splitlines():
                self.assertFalse(cmdlet in ln and re.search(r"\$(first|Matches)\b", ln), ln)
        for needle in (r".venv\Scripts\python.exe", r"tools\selfimproving.py", " patrol",
            "Rotation"):
            self.assertIn(needle, text)
        import test_install_windows_nightly as inst
        engine = inst._ps_engine()
        if engine is None:
            return
        parse = ("$e = $null; $t = $null; "
                 "[void][System.Management.Automation.Language.Parser]::ParseFile("
                 f"'{TICK}', [ref]$t, [ref]$e); $e.Count")
        cp = subprocess.run([engine, "-NoProfile", "-Command", parse], capture_output=True,
                            encoding="utf-8", errors="replace", check=False)
        self.assertEqual(cp.stdout.strip(), "0", cp.stderr)
        tmp = fx.new_dir("tick")
        (tmp / "tools").mkdir(parents=True)
        (tmp / "AgentConsole").mkdir()
        k1, k2, k3 = (f"k-{os.urandom(6).hex()}" for _ in range(3))
        (tmp / "AgentConsole" / ".env").write_text(
            f"OTHER=x\nCONSOLE_SI_AUDIT_KEY={k1},{k2}\nCONSOLE_SI_AUDIT_KEY={k3}\n",
            encoding="utf-8")
        (tmp / "tools" / "selfimproving.py").write_text(
            "import os, sys\nopen(os.path.join(os.path.dirname(__file__), '..', 'seen.txt'), 'w')."
            "write(os.environ.get('AUTOSDD_SI_AUDIT_KEY', 'ABSENT'))\n", encoding="utf-8")
        script = text.replace(r"Join-Path $RepoRoot '.venv\Scripts\python.exe'",
            f"'{sys.executable}'")
        self.assertNotEqual(script, text)
        (tmp / "tools" / "si_patrol_tick.ps1").write_bytes(
            b"\xef\xbb\xbf" + script.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))
        env = {k: v for k, v in os.environ.items() if k != "AUTOSDD_SI_AUDIT_KEY"}
        env["AUTOSDD_SI_DIR"] = str(tmp / "si")
        cp = subprocess.run([engine, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                             str(tmp / "tools" / "si_patrol_tick.ps1")], env=env,
                            capture_output=True, encoding="utf-8", errors="replace", check=False)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertEqual((tmp / "seen.txt").read_text(encoding="utf-8"), k1)
        blob = cp.stdout + cp.stderr + "".join(
            p.read_text(encoding="utf-8", errors="replace") for p in (tmp / "si").rglob("*")
            if p.is_file())
        for k in (k1, k2, k3):
            self.assertNotIn(k, blob)


class FakeOS:
    """`runner.run_argv` 的替身：安裝、移除、查詢三種呼叫各給可設的結果，記錄每個 argv。"""

    def __init__(self, *, install_rc=0, install_err="", query_out="2026-11-09T00:15:00+08:00",
                 remove_rc=0, list_rc=0) -> None:
        self.calls: list[list[str]] = []
        self.install_rc, self.install_err, self.query_out = install_rc, install_err, query_out
        self.remove_rc, self.list_rc = remove_rc, list_rc

    def __call__(self, argv, *, env, timeout, cwd=None):
        self.calls.append(list(argv))
        out, rc, err = "", 0, ""
        if argv[0] == "launchctl":
            rc = self.list_rc if argv[1] == "list" else 0
        elif "-File" in argv:
            rc, err = self.install_rc, self.install_err
        elif any("Unregister-ScheduledTask" in a for a in argv):
            rc = self.remove_rc
        else:
            out = self.query_out
        return types.SimpleNamespace(rc=rc, out=out, err=err, timed_out=False)


class TestArm(P4TestCase):
    """受測模組 tools/lib/selfimproving/schedarm.py：憑證是值、disarm 驗證、與啟用旗標相互獨立。"""

    def test_AT_436_4_E_1_no_credential_no_claim(self):
        R = fx4.p4_base()
        with mock.patch.object(schedarm.sys, "platform", "win32"):
            rc, text = schedarm.arm(R, FakeOS(), as_json=False)
            self.assertEqual(rc, 0, text)
            self.assertIn("2026-11-09T00:15:00+08:00", text)
            fake = FakeOS(query_out="")
            rc, text = schedarm.arm(R, fake, as_json=False)
            self.assertEqual(rc, 1)
            self.assertIn("SCHED-NO-CREDENTIAL", text)
            self.assertFalse(re.search("已排程|armed", text), text)
            self.assertEqual(fake.calls[0][:6], ["powershell.exe", "-NoProfile", "-ExecutionPolicy",
                                                 "Bypass", "-File",
                                                 str(R / "tools" / INSTALLER.name)])
            rc, text = schedarm.arm(R, FakeOS(install_rc=1, install_err="Access is denied"),
                                    as_json=False)
            self.assertEqual(rc, 1)
            self.assertIn("SCHED-ELEVATION-REQUIRED", text)
            self.assertIn("powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
                          f"{R / 'tools' / INSTALLER.name}", text)
        plist_dir = fx.new_dir("plist")
        with mock.patch.object(schedarm.sys, "platform", "darwin"):
            fake = FakeOS()
            rc, text = schedarm.arm(R, fake, as_json=False, plist_dir=plist_dir)
        self.assertEqual(rc, 0, text)
        data = plistlib.loads((plist_dir / "AutoSDD_SI_Patrol.plist").read_bytes())
        self.assertEqual((data["Label"], data["RunAtLoad"]), ("AutoSDD_SI_Patrol", False))
        self.assertEqual(data["StartInterval"], P["sched_heartbeat_minutes"] * 60)
        self.assertIn("StandardOutPath", data)
        self.assertTrue(all(c[0] == "launchctl" for c in fake.calls))

    def test_AT_436_4_E_2_os_task_and_enable_flag_are_independent(self):
        R = fx4.p4_base(events=[fx4.sched_set_ev(O)])
        fake = FakeOS()
        with mock.patch.object(runner, "run_argv", fake):
            rc, out, _ = self.M(R, "sched", "set", "--enabled", "false", "--by", "main")
        self.assertEqual((rc, fake.calls), (0, []))
        before = (R / fx.EVL).read_bytes()
        with mock.patch.object(schedarm.sys, "platform", "win32"):
            schedarm.arm(R, FakeOS(), as_json=False)
            schedarm.disarm(R, FakeOS(query_out="ABSENT"), as_json=False)
        self.assertEqual((R / fx.EVL).read_bytes(), before)
        events = fx4.ledger(R)
        now = O + 3 * H
        present = {"task": "AutoSDD_SI_Patrol", "present": True,
            "credential": "2026-11-09T00:15:00+08:00"}
        absent = {"task": "AutoSDD_SI_Patrol", "present": False, "credential": "-"}
        a = sched.schedule_obj(events, P, now, armed=present)
        b = sched.schedule_obj(events, P, now, armed=absent)
        self.assertEqual((a["overdue"], a["cell_start"]), (b["overdue"], b["cell_start"]))
        self.assertTrue(a["overdue"])

    def test_AT_436_5_2_disarm_verifies_the_task_is_gone(self):
        R = fx4.p4_base()
        before = (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""
        with mock.patch.object(schedarm.sys, "platform", "win32"):
            fake = FakeOS(query_out="ABSENT")
            rc, text = schedarm.disarm(R, fake, as_json=False)
            self.assertEqual(rc, 0, text)
            flat = " ".join(" ".join(c) for c in fake.calls)
            self.assertNotIn("AutoClaude_Nightly", flat)
            self.assertNotIn("AutoClaude_WindowsSmoke", flat)
            self.assertFalse(any("-Uninstall" in c for c in fake.calls))
            self.assertIn("AutoSDD_SI_Patrol", flat)
            rc, text = schedarm.disarm(R, FakeOS(query_out="2026-11-09T00:15:00+08:00"),
                as_json=False)
            self.assertEqual(rc, 1)
            self.assertIn("仍在", text)
        with mock.patch.object(schedarm.sys, "platform", "darwin"):
            self.assertEqual(schedarm.disarm(R, FakeOS(list_rc=113), as_json=False,
                                             plist_dir=fx.new_dir("pl"))[0], 0)
            self.assertEqual(schedarm.disarm(R, FakeOS(list_rc=0), as_json=False,
                                             plist_dir=fx.new_dir("pl"))[0], 1)
        after = (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b""
        self.assertEqual(after, before)


# --------------------------------------------------------------------------- 權限列、能力登記
# （R154、R160）
ALLOWED_VERBS = {"research", "scan", "run-open", "run-close", "sandbox", "verify", "promote",
    "rollback",
                 "measure", "card", "sched set", "decide", "obs-add", "obs-close", "status",
                 "check"}
ALLOWED_GIT = {"status", "add", "commit", "rev-parse", "diff", "log", "show"}


def patrol_verb_calls(src: str) -> tuple[set[str], set[str], list[str]]:
    """AST：（動詞集合, git 子命令集合, 問題碼）。動詞取自 `ctx.verb("x", …)`、`_step(ctx, pid,
    "x", …)` 與
    入帳 argv 清單（第一個元素為已知動詞者）；git 子命令取自 `.run(…)`（略過 `-c k=v` 前綴）。"""
    tree = ast.parse(src)
    verbs: set[str] = set()
    gits: set[str] = set()
    codes: list[str] = []
    known = ALLOWED_VERBS | {"sched"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            args = [a.value if isinstance(a, ast.Constant) else None for a in node.args]
            if fn.endswith(".verb") and args and isinstance(args[0], str):
                verbs.add(args[0] + (" set" if args[0] == "sched" else ""))
            elif fn == "_step" and len(args) > 2 and isinstance(args[2], str):
                verbs.add(args[2])
            elif fn.endswith(".run") and args and isinstance(args[0],
                str) and "git" in ast.unparse(node.func):
                strs = [a for a in args if isinstance(a, str)]
                sub = strs[2] if strs[:1] == ["-c"] else strs[0]
                gits.add(sub)
                if sub == "add" and ("-A" in strs or "." in strs):
                    codes.append("V-ADD-ALL")
        elif isinstance(node, ast.List) and node.elts and isinstance(node.elts[0], ast.Constant):
            head = node.elts[0].value
            strs = [e.value for e in node.elts if isinstance(e, ast.Constant)]
            if head in known and head != "status":
                verbs.add(head + (" set" if head == "sched" else ""))
                if head == "decide" and ("--sid" in strs or "transcript" in strs):
                    codes.append("V-DECIDE-TRANSCRIPT")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value == "--no-verify":
                codes.append("V-NOVERIFY")
            if "--carrier transcript" in node.value:
                codes.append("V-DECIDE-TRANSCRIPT")
    if "push" in gits:
        codes.append("V-PUSH")
    codes += [f"V-UNKNOWN-VERB:{v}" for v in sorted(verbs - ALLOWED_VERBS)]
    codes += [f"V-UNKNOWN-GIT:{g}" for g in sorted(gits - ALLOWED_GIT)]
    return verbs, gits, codes


class TestPermissions(unittest.TestCase):
    def test_AT_438_7_1_patrol_sources_stay_inside_the_allowed_call_set(self):
        names = ("patrol", "patrolrun", "patrolbrief", "schedarm", "sched", "schedwrite")
        for name in names:
            verbs, gits, codes = patrol_verb_calls((PKG / f"{name}.py").read_text(encoding="utf-8"))
            self.assertEqual(codes, [], name)
            self.assertLessEqual(verbs, ALLOWED_VERBS, name)
            self.assertLessEqual(gits, ALLOWED_GIT, name)
        base = (PKG / "patrol.py").read_text(encoding="utf-8")
        injected = {
            "V-PUSH": 'def f(ctx):\n    ctx.git().run("push", "origin")\n',
            "V-NOVERIFY": 'X = ["commit", "--no-verify"]\n',
            "V-ADD-ALL": 'def f(ctx):\n    ctx.git().run("add", "-A")\n',
            "V-DECIDE-TRANSCRIPT": 'X = ["decide", "PROP", "--kind", "approve", "--sid", "S"]\n',
            "V-UNKNOWN-VERB": 'def f(ctx):\n    ctx.verb("rm")\n',
            "V-DECIDE-TRANSCRIPT2": 'Y = "decide --carrier transcript"\n',
        }
        for want, extra in injected.items():
            with self.subTest(want):
                got = patrol_verb_calls(base + "\n" + extra)[2]
                self.assertTrue(any(c.startswith(want.rstrip("2")) for c in got), (want, got))


class TestCapabilityP4(unittest.TestCase):
    """受測模組 tools/lib/selfimproving/runner.py、schedarm.py 與能力登記表
    （tools/tests/test_selfimproving_capability.py）。"""

    @staticmethod
    def cap():
        import test_selfimproving_capability as cap
        return cap

    def test_AT_440_3_1_registry_counts_classes_and_runner_users(self):
        cap = self.cap()
        self.assertEqual(cap.capability_problems(cap.PKG, cap.CAPABILITY, cap.ENTRY), [])
        n = len(cap.CAPABILITY)
        counts = tuple(sum(1 for v in cap.CAPABILITY.values() if v == k) for k in cap.CATEGORIES)
        self.assertIn((n, counts), {(59, (43, 9, 2, 5)), (60, (44, 9, 2, 5))})
        if n == 60:
            self.assertEqual(cap.CAPABILITY["evspec.py"], "ro")
        self.assertEqual({p.name for p in cap.PKG.glob("*.py")}, set(cap.CAPABILITY))
        reg = cap.CAPABILITY
        for name in ("sched", "unattended", "patrolbrief", "schedcheck"):
            self.assertEqual(reg[f"{name}.py"], "ro", name)
        self.assertEqual(reg["schedwrite.py"], "rw")
        for name in ("patrol", "patrolrun", "schedarm"):
            self.assertEqual(reg[f"{name}.py"], "exec", name)
        self.assertEqual({k for k, v in reg.items() if v == "exec"},
                         {"runner.py", "verify.py", "patrol.py", "patrolrun.py", "schedarm.py"})
        users = {p.name for p in cap.PKG.glob("*.py") if "runner" in cap._rel_imports(
            p.read_text(encoding="utf-8"), "selfimproving")}
        self.assertEqual(users, {"verify.py", "patrol.py", "patrolrun.py", "schedarm.py"})
        for start in cap.CLOSURE_ONLY_RO:
            seen, todo = set(), [start]
            while todo:
                cur = todo.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                todo += [f"{d}.py"
                    for d in cap._rel_imports((cap.PKG / cur).read_text(encoding="utf-8"),
                                                             "selfimproving")
                                                             if (cap.PKG / f"{d}.py").exists()]
            self.assertFalse(seen & {"schedwrite.py", "patrol.py", "patrolrun.py", "schedarm.py",
                                     "runner.py"}, (start, seen))

    @staticmethod
    def fn_problems(runner_src: str) -> list[str]:
        """`run_argv`／`spawn_detached` 的靜態不變量：不讀 `os.environ`、`shell` 為假、`run_argv` 的
        `communicate` 帶 timeout、`spawn_detached` 不等待。"""
        tree, out = ast.parse(runner_src), []
        fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for name in ("run_argv", "spawn_detached"):
            body = ast.unparse(fns[name]) if name in fns else ""
            if not body:
                out.append(f"MISSING:{name}")
            if any(isinstance(a, ast.Attribute) and ast.unparse(a) in ("os.environ", "os.getenv")
                   or isinstance(a, ast.Name) and a.id == "environ"
                   for a in ast.walk(fns.get(name, tree))) or "environ.copy" in body:
                out.append(f"ENV:{name}")
            for call in ast.walk(fns.get(name, tree)):
                if isinstance(call, ast.Call) and ast.unparse(call.func).endswith("Popen"):
                    shell = [k.value for k in call.keywords if k.arg == "shell"]
                    if not shell or not (isinstance(shell[0], ast.Constant)
                        and shell[0].value is False):
                        out.append(f"SHELL:{name}")
        comm = [c for c in ast.walk(fns.get("run_argv", tree)) if isinstance(c, ast.Call)
                and ast.unparse(c.func).endswith("communicate")]
        if not any(k.arg == "timeout" for c in comm for k in c.keywords):
            out.append("COMMUNICATE-TIMEOUT:run_argv")
        if any(isinstance(c, ast.Call) and ast.unparse(c.func).endswith("communicate")
               for c in ast.walk(fns.get("spawn_detached", tree))):
            out.append("WAITS:spawn_detached")
        for flag in ("CREATE_BREAKAWAY_FROM_JOB", "CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS"):
            if f'getattr(subprocess, "{flag}", 0)' not in runner_src:
                out.append(f"GETATTR:{flag}")
        return out

    def test_AT_440_3_2_runner_static_invariants_and_forbidden_words(self):
        cap = self.cap()
        src = (cap.PKG / "runner.py").read_text(encoding="utf-8")
        self.assertEqual(self.fn_problems(src), [])
        texts = {p.name: p.read_text(encoding="utf-8") for p in cap.PKG.glob("*.py")}
        self.assertEqual({n for n, t in texts.items() if "subprocess" in t}, {"git.py",
            "runner.py"})
        for n, t in texts.items():
            self.assertEqual(cap.forbidden_hits(t, n), [], n)
        self.assertEqual(cap.unguarded_sites(src), [])
        self.assertEqual(len(cap.FORBIDDEN), 14)
        self.assertEqual(cap.FORBIDDEN_EXEMPT, {"schedarm.py": ("schtasks", "launchctl",
                                                                 "Register-ScheduledTask")})
        self.run_foreign_guards()

    @staticmethod
    def run_foreign_guards() -> None:
        import io

        import test_platform_neutral_paths as root_tests
        suite = unittest.TestSuite()
        for cls in ("TestForeignExecutableArgvIsGuarded", "TestForeignPlatformApiIsGuarded",
                    "TestForeignApiVocabularyOnlyGrows"):
            suite.addTests(unittest.TestLoader().loadTestsFromTestCase(getattr(root_tests, cls)))
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        assert result.wasSuccessful(), result.failures + result.errors
        for table in ("_FOREIGN_EXE_ARGV_DEBT", "_FOREIGN_API_SCOPE_DEBT"):
            assert not [k for k in getattr(root_tests, table)
                if "selfimproving" in str(k).lower()], table

    def test_AT_440_3_E_1_injections_are_caught(self):
        cap = self.cap()

        def copy_with(**edits) -> Path:
            dest = fx.new_dir("pkgi")
            shutil.copytree(cap.PKG, dest)
            for name, fn in edits.items():
                path = dest / f"{name}.py"
                old = path.read_text(encoding="utf-8") if path.exists() else ""
                path.write_text(fn(old), encoding="utf-8")
            return dest
        add = lambda line: (lambda t: t.rstrip("\n") + "\n" + line + "\n")  # noqa: E731
        control = copy_with()
        self.assertEqual(cap.capability_problems(control, cap.CAPABILITY, cap.ENTRY), [])
        reg_patrol_ro = {**cap.CAPABILITY, "patrol.py": "ro"}
        cases = [
            ("甲", dict(newmod=lambda t: "X = 1\n"), cap.CAPABILITY, "未登記"),
            ("乙", dict(sched=add("from . import runner")), cap.CAPABILITY, "②′"),
            ("丙", {}, reg_patrol_ro, "②′"),
            ("戊", dict(sched=add("X = 'launchctl'")), cap.CAPABILITY, "launchctl"),
            ("己", dict(schedarm=add("time.sleep(1)")), cap.CAPABILITY, "time.sleep"),
        ]
        for label, edits, registry, needle in cases:
            with self.subTest(label):
                got = cap.capability_problems(copy_with(**edits), registry, cap.ENTRY)
                self.assertTrue(any(needle in g for g in got), (label, got))
        src = (cap.PKG / "runner.py").read_text(encoding="utf-8")
        bad = src.replace("def run_argv(", "def run_argv_old(", 1) + (
            "\n\ndef run_argv(argv, *, env, timeout, cwd=None):\n    env = dict(os.environ)\n"
            "    proc = subprocess.Popen(argv, env=env, shell=False)\n"
            "    return proc.communicate(timeout=timeout)\n")
        self.assertIn("ENV:run_argv", self.fn_problems(bad))
        self.assertEqual(self.fn_problems(src), [])

    def test_AT_440_3_3_foreign_argv_lives_inside_platform_guards(self):
        src = (PKG / "schedarm.py").read_text(encoding="utf-8")

        def unguarded(text: str) -> list[str]:
            tree = ast.parse(text)
            parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
            bad = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and node.value in ("powershell.exe", "schtasks",
                    "launchctl"):
                    up, ok = node, False
                    while up in parent and not ok:
                        up = parent[up]
                        ok = isinstance(up, ast.If) and "sys.platform" in ast.unparse(up.test)
                    if not ok:
                        bad.append(node.value)
            return bad
        self.assertEqual(unguarded(src), [])
        literals = {n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant)}
        self.assertTrue({"powershell.exe", "launchctl"} <= literals)
        self.assertEqual(unguarded(src + '\nX = ["launchctl", "list"]\n'), ["launchctl"])
        self.assertEqual(unguarded(src + '\ndef f():\n    return ["powershell.exe"]\n'),
            ["powershell.exe"])
        TestCapabilityP4.run_foreign_guards()


# --------------------------------------------------------------------------- SOP 條文（R162）
REQ_UPPER = ("RUN", "HEAD_SHA", "NOW_ISO", "DUE_AT", "BAND", "DEGRADE_NOTE", "BUDGET_MINUTES",
    "EVENTS",
             "RESEARCH_RESULT", "SOURCE_FILES", "SCAN_CANDIDATES", "MAX_PROPOSALS", "HANDBACK_PATH")
SKIPS = ("disabled", "blackout", "quota-band", "other-driver", "dirty-tree", "run-open",
    "spawn-failed")
OVERGEN = "無人值守：有設時寫入動詞一律 rc 1"


def sop_p4_problems(text: str) -> list[str]:
    """R162／§5.6：回問題字串（碼起頭）。必含字面須位於程式碼圍欄之外（範本除外：須位於圍欄內）。"""
    import test_selfimproving_p3_meta as p3m
    out: list[str] = []
    for title in p3m.FOUR:
        body = p3m.section(text, title)
        out += [f"SOP-P4-FORBIDDEN 〈{title}〉含 {frag}" for frag in p3m.FORBID if frag in body]
    main = p3m.section(text, "巡邏與無人運轉（P4）")
    for sub in ("安裝與憑證", "每心跳做什麼", "停用與逃生口", "日誌與逾期處置"):
        if f"### {sub}" not in main:
            out.append(f"SOP-P4-REQ-MISSING REQ-1：缺子節〈{sub}〉")

    def need(code_no: int, title: str, frags: tuple[str, ...]) -> None:
        body = p3m.section(text, title)
        outside = "\n".join(p3m.outside_fences(body))
        for frag in frags:
            if frag not in outside:
                where = "SOP-P4-FENCE" if frag in body else "SOP-P4-REQ-MISSING"
                out.append(f"{where} REQ-{code_no}：〈{title}〉缺 {frag}")
    need(2, "每心跳做什麼", ("入帳", "到期判定", "運轉", "推進", *SKIPS))
    need(3, "停用與逃生口", ("sched set --enabled false", "sched disarm", "AUTOSDD_SI_PATROL_OFF"))
    need(4, "日誌與逾期處置", ("overdue", "手補 `sched.skip`"))
    need(6, "啟動條件", ("日曆格", "第六類"))
    p2 = p3m.section(text, "P2 動詞")
    if "run-scoped" not in p2 and "AUTOSDD_SI_PATROL_RUN" not in p2:
        out.append("SOP-P4-REQ-MISSING REQ-7：〈P2 動詞〉缺 run-scoped")
    if OVERGEN in p2:
        out.append("SOP-P4-STALE-WORDING 〈P2 動詞〉含過度概括句")
    # 範本節在檔尾；圍欄內含 `## ` 標題，不能用「到下一個標題」切
    start = text.find("## 無人運轉任務書範本")
    tmpl = text[start:] if start >= 0 else ""
    inside = re.findall(r"```\w*\n(.*?)```", tmpl, re.S)
    body = "\n".join(inside)
    if not inside:
        out.append("SOP-P4-FENCE REQ-5：範本無程式碼圍欄")
    out += [f"SOP-P4-PLACEHOLDER REQ-5：範本缺 <{u}>" for u in REQ_UPPER if f"<{u}>" not in body]
    from lib import resume_route
    out += [f"SOP-P4-REQ-MISSING REQ-5：範本缺 {m}" for m in resume_route.HANDBACK_MARKERS
            if m not in body.splitlines()]
    return out


class TestSopP4(unittest.TestCase):
    """受測模組 docs/05_development/SelfImproving_Operations_SOP.md 的 P4 條文（唯讀；判準在本
    檔）；執行期消費者＝tools/lib/selfimproving/patrolbrief.py 的 template_problems（範本結構）
    與 tools/lib/selfimproving/sched.py 的 spawn_problem（R143 (g)：範本不過即不 spawn）。"""

    SOP = fx.REAL_SOP

    def test_AT_440_4_1_real_sop_passes(self):
        text = self.SOP.read_text(encoding="utf-8")
        self.assertEqual(sop_p4_problems(text), [])
        self.assertEqual(patrolbrief.template_problems(text), [])

    def test_AT_440_4_E_1_deletions_fence_moves_and_injections_are_caught(self):
        text = self.SOP.read_text(encoding="utf-8")
        needles = ("入帳", "到期判定", *SKIPS, "sched set --enabled false", "sched disarm",
                   "AUTOSDD_SI_PATROL_OFF", "overdue", "日曆格", "第六類")
        for frag in needles:
            with self.subTest(frag):
                import test_selfimproving_p3_meta as p3m
                body = p3m.section(text, "巡邏與無人運轉（P4）") + p3m.section(text, "啟動條件")
                self.assertIn(frag, body)
                self.assertNotEqual(sop_p4_problems(text.replace(frag, "XX")), [], frag)
        line = "2. **移除 OS 任務**：`python tools/selfimproving.py sched disarm`"
        wrapped = text.replace(line, f"```\n{line}\n```", 1)
        self.assertNotEqual(wrapped, text)
        got = sop_p4_problems(wrapped)
        self.assertTrue(any(g.startswith("SOP-P4-FENCE") for g in got), got)
        stale = text.replace("### P3 動詞", f"{OVERGEN}\n\n### P3 動詞", 1)
        self.assertTrue(any(g.startswith("SOP-P4-STALE-WORDING") for g in sop_p4_problems(stale)))
        forbidden = text.replace("## 審查者", "## 審查者\n\nparams.json 的值", 1)
        self.assertTrue(any(g.startswith("SOP-P4-FORBIDDEN") for g in sop_p4_problems(
            text.replace("## 提案者", "## 提案者\n\n見 params.json", 1))))
        self.assertNotEqual(forbidden, text)
        lower = text.replace("<RUN>", "<run>")
        self.assertTrue(any(g.startswith("SOP-P4-PLACEHOLDER") for g in sop_p4_problems(lower)))
        self.assertEqual(sop_p4_problems(text), [])


# --------------------------------------------------------------------------- 零退化、錨定與入口
# （R137、R163、R164）
class TestZeroRegression(P4TestCase):
    def test_AT_440_5_1_old_scenario_tables_replay_on_the_p4_fixture(self):
        scenarios = {"sc_close": fx.sc_close(), "sc_legal": fx.sc_legal(), "sc_rev": fx.sc_rev(),
                     "sc_susp": fx.sc_susp(), "sc_p2_legal": fx2.sc_p2_legal()}
        for label, events in scenarios.items():
            with self.subTest(label):
                R = fx4.p4_base()
                fx.write_events(R, events)
                res = self.check(R)
                self.assertEqual(self.S(res, "events.structure"), "PASS", label)
        events, seqs = fx.sc_seq()
        R = fx4.p4_base()
        fx.write_events(R, events, seqs=seqs)
        self.assertEqual(self.S(self.check(R), "events.structure"), "PASS")
        self.assertEqual(len(json.loads((fx4.p4_base() / fx.PARAMS).read_text(encoding="utf-8"))),
            41)
        sigs = {"make_p1_repo": ("dest", "events", "sources", "extra_obs", "defs", "prm", "rows",
            "commit"),
                "make_p2_repo": ("dest", "commit", "kw")}
        for name, want in sigs.items():
            fn = getattr(fx if name.startswith("make_p1") else fx2, name)
            self.assertEqual(tuple(inspect.signature(fn).parameters), want, name)

    def test_AT_440_5_E_1_every_sync_site_holds_its_new_value(self):
        import test_selfimproving_capability as cap

        import selfimproving
        from lib.selfimproving import check as si_check
        from lib.selfimproving import events as si_events
        from lib.selfimproving import params as si_params
        self.assertEqual(len(selfimproving._HELP), 26)
        self.assertEqual(len(si_events.KINDS), 23)
        self.assertEqual(len(si_check.ITEM_IDS), 35)
        self.assertEqual(len(si_params.PARAM_SPECS), 41)
        self.assertEqual(si_params.CHECK_RULES_REV, 5)
        self.assertEqual(len(cap.CAPABILITY), 59)
        self.assertEqual(len(self.status(fx4.p4_base())), 16)
        spec = json.loads(EXPECT.read_text(encoding="utf-8"))
        self.assertEqual(len(spec["tasks"]), 3)
        tests = ROOT / "tools" / "tests"
        for name, needle in (("test_selfimproving_p3_meta.py", "len(selfimproving._HELP), 26"),
                             ("test_selfimproving_issues.py", "len(verbs), 26"),
                             ("test_selfimproving_console_obs.py", "len(verbs), 26")):
            self.assertIn(needle, (tests / name).read_text(encoding="utf-8"), name)
        base = os.environ.get("SI_P4_BASE_SHA") or "HEAD~1"
        ok = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet",
            base + "^{commit}"],
                            capture_output=True, check=False).returncode == 0
        changed = [n for n in git_names("diff", "--name-only", base) if (
            n.startswith("tools/tests/test_selfimproving_")
            or n.startswith("tools/tests/test_install_windows")
            or n.startswith("tools/tests/_selfimproving_"))] if ok else []
        new_files = {f"tools/tests/test_selfimproving_schedule_{x}.py" for x in
                     ("model", "patrol", "advance",
                     "gate")} | {"tools/tests/_selfimproving_p4_fixtures.py"}
        allowed = {"tools/tests/test_selfimproving_capability.py",
            "tools/tests/test_selfimproving_p3_meta.py",
                   "tools/tests/test_selfimproving_console_obs.py",
                   "tools/tests/test_selfimproving_issues.py",
                   "tools/tests/test_selfimproving_events.py",
                   "tools/tests/test_selfimproving_measure_verb.py",
                   "tools/tests/test_selfimproving_events_p2.py",
                   "tools/tests/test_selfimproving_check.py",
                   "tools/tests/test_selfimproving_export_status.py",
                   "tools/tests/test_selfimproving_issuemap.py",
                   "tools/tests/test_selfimproving_ledgerdb_p0.py",
                   "tools/tests/test_install_windows_nightly.py",
                   "tools/tests/test_selfimproving_p2_meta.py",
                   "tools/tests/_selfimproving_fixtures.py",
                   "tools/tests/_selfimproving_p2_fixtures.py"} | new_files
        self.assertEqual(sorted(set(changed) - allowed), [])


TARGET_FILES = ("test_selfimproving_schedule_model.py", "test_selfimproving_schedule_patrol.py",
                "test_selfimproving_schedule_advance.py", "test_selfimproving_schedule_gate.py")


class TestAnchors(unittest.TestCase):
    def test_AT_440_6_1_every_at_anchors_exactly_one_function(self):
        import test_selfimproving_p2_meta as p2m
        text = p2m.real_tcs("P4")
        ats = p2m.parse_at_headers(text)
        self.assertEqual(len(ats), 105)
        files = sorted({ROOT / f for _, f, _ in ats})
        self.assertEqual({f.name for f in files}, set(TARGET_FILES))
        collected = p2m.collect_nodes(files, ROOT)
        self.assertEqual(p2m.anchor_problems(ats, collected), [])
        for f in files:
            self.assertLessEqual(sum(1 for _, ff, _ in ats if ff.endswith(f.name)), 35, f.name)
        section = text.split("## 1. AC → AT 映射表")[1].split("## 2.")[0]
        table_ids = {m.group(1) for m in re.finditer(r"(?m)^\| AC-\S+ \| [^|]*\| (AT-[\w-]+) \|",
            section)}
        self.assertEqual({a for a, _, _ in ats}, table_ids)

    def test_AT_440_6_E_1_anchor_check_has_teeth(self):
        import test_selfimproving_p2_meta as p2m
        good = [("AT-900-1-1", "tools/tests/x.py", "AT_900_1_1_")]
        nodes = {"x.py": ["x.py::T::test_AT_900_1_1_slug"]}
        self.assertEqual(p2m.anchor_problems(good, nodes), [])
        cases = {
            "非錨定": ([("AT-900-1-1", "tools/tests/x.py", "AT_900_1_1")], nodes),
            "不等於 AT 底線形": ([("AT-900-1-1", "tools/tests/x.py", "AT_900_1_2_")], nodes),
            "零命中": (good, {"x.py": []}),
            "命中 2 個": (good, {"x.py": ["x.py::T::test_AT_900_1_1_a",
            "x.py::T::test_AT_900_1_1_b"]}),
        }
        for word, (ats, coll) in cases.items():
            with self.subTest(word):
                self.assertTrue(any(word in p for p in p2m.anchor_problems(ats, coll)), word)


class TestEntry(P4TestCase):
    """受測模組 tools/selfimproving.py：26 個動詞、sched 與 patrol 的旗標、用法錯誤 rc 3。"""

    def test_AT_440_7_1_twenty_six_verbs_and_new_flags(self):
        import selfimproving
        self.assertEqual(len(selfimproving._HELP), 26)
        rc, out, _ = self.run_main(["--help"])
        self.assertEqual(rc, 0)
        self.assertTrue(all(v in out for v in selfimproving._HELP), out)
        self.assertTrue({"sched", "patrol"} <= set(selfimproving._HELP))
        sched_help = self.run_main(["sched", "--help"])[1]
        for sub in ("show", "set", "arm", "disarm"):
            self.assertIn(sub, sched_help)
        patrol_help = self.run_main(["patrol", "--help"])[1]
        for flag in ("--now", "--dry-run", "--json", "--repo"):
            self.assertIn(flag, patrol_help)
        self.assertNotIn("--run", patrol_help)
        open_help = self.run_main(["run-open", "--help"])[1]
        for flag in ("--due-at", "--carrier", "--audit-ref", "a,b,c,d,e,f"):
            self.assertIn(flag, open_help)
        R = fx4.p4_base(events=[fx4.sched_set_ev(O)])
        with mock.patch.object(runner, "run_argv", return_value=types.SimpleNamespace(
                rc=0, out="ABSENT", err="", timed_out=False)):
            rc, out, err = self.M(R, "sched", "show", "--json", "--now", iso(O + H))
            self.assertEqual(rc, 0, err)
            self.assertEqual(list(json.loads(out)), [
                "enabled", "period_minutes", "period_min", "period_max", "heartbeat_minutes",
                "last_set",
                "cell_start", "cell_end", "ran_this_cell", "last_skip", "overdue", "armed"])
            rc, out, err = self.M(R, "sched", "show", "--now", iso(O + H))
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith("schedule: enabled="), out)
        entry = (ROOT / "tools" / "selfimproving.py").read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(len([ln for ln in entry if ln.strip()
            and not ln.strip().startswith("#")]), 750)

    def test_AT_440_7_E_1_usage_errors_are_rc3(self):
        R = fx4.p4_base()
        calls = [["sched"], ["sched", "set", "--by", "main"],
                 ["sched", "set", "--enabled", "maybe", "--by", "main"],
                 ["sched", "show", "--now", "2026-11-02T08:00:00"],
                 ["run-open", "--trigger", "g", "--coord", "x:1", "--by", "main"],
                 ["patrol", "--run", "X"], ["sched", "bogus"], ["schedule"]]
        for argv in calls:
            with self.subTest(" ".join(argv)):
                self.usage_error(*self.M(R, *argv), " ".join(argv))


if __name__ == "__main__":
    sys.exit(unittest.main())
