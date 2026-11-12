# 受測面：tools/lib/selfimproving/patrol.py（程式碼鎖，非散文）
"""SelfImproving P4 入帳之後的推進、本機 commit、收尾與 Console (a) 運轉（TCS-SelfImproving-P4 §2 B
節
SA 的 21 個 AT：R149、R155～R157、R166、R167；受測 `tools/lib/selfimproving/patrol.py`、
`patrolrun.py`）。

人的決定（DEC）一律由測試事先入帳（Console 稽核檔經真 `decide`，或逐字稿載體）；巡邏器只做決定之後的
機械步驟。夾具 repo 為真 git，`pre-commit` hook 為會計數的腳本，無 remote。
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
from _selfimproving_p4_fixtures import MIN, H, O, P4TestCase, Rig, iso

from lib import apply_lock, unattended_authz
from lib.selfimproving import events as si_events
from lib.selfimproving import evwrite, patrolrun, promote, sandbox, sched, status
from lib.selfimproving.git import Git

NOW = datetime.now().astimezone().replace(microsecond=0)
OWN = ("docs/06_quality/SelfImproving_Event_Ledger.jsonl",
       "docs/06_quality/SelfImproving_Observation_Ledger.md",
       "docs/06_quality/SelfImproving_Proposals")
LOG_LINE = re.compile(r"^\S+ step=(巡視|入帳|到期|運轉|推進|commit) rc=-?\d+ code=\S+ \S.*$")


def setUpModule() -> None:
    fx.setup("si_p4_")


def tearDownModule() -> None:
    fx.teardown()


def evs(R: Path, kind: str) -> list[dict]:
    return [e for e in fx4.ledger(R) if e["kind"] == kind]


def skips(R: Path) -> list[dict]:
    return evs(R, "sched.skip")


def commits(R: Path) -> int:
    return int(fx.git(R, "rev-list", "--count", "HEAD"))


def last_paths(R: Path) -> list[str]:
    return fx.git(R, "show", "--name-only", "--format=", "HEAD").split()


def install_hook(R: Path, rc: int = 0) -> Path:
    marker = R / ".git" / "hook_calls"
    hook = R / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_bytes(f'#!/bin/sh\necho x >> .git/hook_calls\nexit {rc}\n'.encode())
    os.chmod(hook, 0o755)
    return marker


def hook_calls(marker: Path) -> int:
    return len(marker.read_text(encoding="utf-8").split()) if marker.exists() else 0


@contextlib.contextmanager
def git_calls():
    """記錄巡邏器對 git 的每個呼叫（只記 argv，行為不變）。"""
    seen: list[tuple] = []
    orig = Git.run

    def rec(self, *args, **kw):
        seen.append(args)
        return orig(self, *args, **kw)
    with mock.patch.object(Git, "run", rec):
        yield seen


class AdvanceCase(P4TestCase):
    """推進類 AT 的共用夾具：一個走到 verified 的 PROP（真沙盒與驗證）與 Console 載體的人的決定。"""

    def beat(self, *args, **kw):
        """決定的稽核檔簽章回查需要金鑰：與包裝腳本一樣，金鑰只存在於巡邏行程環境。"""
        with fx4.with_key(fx2.AUDIT_KEY):
            return super().beat(*args, **kw)

    def verified_repo(self, *events, state: str = "verified") -> tuple[Path, str]:
        R = fx4.p4_base(events=list(events))
        prop = fx2.drive_to(R, state)
        return R, prop

    def cdec(self, R: Path, prop: str, dkind: str, **extra) -> str:
        digest = None if dkind in ("rollback", "unblock", "resume") else fx2.prop_event(
            R, prop)["digest"]
        ref = self.audit("decide", lambda r: fx2.body_decide(r, prop, digest, dkind, **extra),
                         subject=prop)
        with fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.M(R, "decide", prop, "--carrier", "console", "--audit-ref", ref)
        self.assertEqual(rc, 0, out + err)
        return ref

    def promotable(self, *events, hook_rc: int = 0) -> tuple[Path, str, Path]:
        R, prop = self.verified_repo(*events)
        self.cdec(R, prop, "promote")
        fx.commit_all(R, "pre-heartbeat")
        return R, prop, install_hook(R, hook_rc)

    def touched_of(self, R: Path, prop: str) -> list[str]:
        return sandbox.prop_context(R, fx2.prop_event(R, prop))[1]


class TestAutoCommit(AdvanceCase):
    """受測模組 tools/lib/selfimproving/patrol.py：核准晉升後的本機 commit（白名單、髒樹、
    hook）。"""

    def test_AT_438_5_1_promote_then_a_local_commit_of_touched_paths_only(self):
        R, prop, marker = self.promotable()
        n0, rig = commits(R), Rig()
        with git_calls() as seen:
            rc, out, err = self.beat(R, NOW, rig)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(commits(R), n0 + 1)
        paths, touched = set(last_paths(R)), self.touched_of(R, prop)
        self.assertTrue(set(touched) <= paths, (touched, paths))
        self.assertTrue(all(p in touched or p.startswith(OWN) for p in paths), paths)
        msg = fx.git(R, "log", "-1", "--format=%B")
        app = evs(R, "app.promote")[-1]["id"]
        dec = [e for e in evs(R, "dec") if e["dkind"] == "promote"][-1]["id"]
        for token in (prop, dec, app):
            self.assertIn(token, msg)
        self.assertEqual(hook_calls(marker), 1)
        for banned in ("push", "--no-verify"):
            self.assertFalse([a for a in seen if banned in a], banned)
        self.assertFalse([a for a in seen if a[:1] == ("add",) and ("-A" in a or "." in a)])
        self.assertTrue(rig.verbs_named("measure"))

    def test_AT_438_5_E_1_dirty_tree_is_a_log_line_not_a_skip(self):
        for label, events in (("enabled", [fx4.sched_set_ev(O), fx4.run_open_f_ev(50, O + MIN,
            due_at=O),
                                           fx4.run_close_ev(50, O + 2 * MIN)]), ("disabled", [])):
            with self.subTest(label):
                self.new_home()
                R, prop, marker = self.promotable(*events)
                fx.put(R, "notes/dirty.txt", "未提交\n")
                n0, k0, before = commits(R), len(skips(R)), (R / fx.EVL).read_bytes()
                rig = Rig()
                for k in (0, 1):
                    self.assertEqual(self.beat(R, O + H if events else NOW, rig)[0], 0)
                self.assertEqual((evs(R, "app.promote"), commits(R), len(skips(R))), ([], n0, k0))
                self.assertFalse(rig.verbs_named("promote"))
                self.assertEqual(sum("step=推進" in ln and "dirty-tree" in ln
                    for ln in self.logs()), 2)
                self.assertEqual(fx.read(R, "notes/dirty.txt"), "未提交\n")
                if not events:
                    self.assertEqual((R / fx.EVL).read_bytes(), before)
                (R / "notes" / "dirty.txt").unlink()
                self.assertEqual(self.beat(R, O + H if events else NOW, rig)[0], 0)
                self.assertEqual(len(evs(R, "app.promote")), 1)

    def test_AT_438_5_E_2_stray_files_are_never_added(self):
        R, prop, _ = self.promotable()
        real = promote.promote

        def with_stray(repo, ns, as_json):
            out = real(repo, ns, as_json)
            fx.put(repo, "stray/extra.txt", "套用器多寫\n")
            return out
        with mock.patch.object(promote, "promote", with_stray):
            rc, out, err = self.beat(R, NOW, Rig())
        self.assertEqual(rc, 0, out + err)
        paths = last_paths(R)
        self.assertNotIn("stray/extra.txt", paths)
        self.assertTrue(set(self.touched_of(R, prop)) <= set(paths))
        self.assertTrue(all(p in self.touched_of(R, prop) or p.startswith(OWN) for p in paths))
        self.assertIn("stray/extra.txt", fx.git(R, "status", "--porcelain",
            "--untracked-files=all"))

    def test_AT_438_5_E_3_hook_rejection_and_auto_commit_off(self):
        R, prop, marker = self.promotable(hook_rc=1)
        n0, h0, rig = commits(R), hook_calls(marker), Rig()
        with git_calls() as seen:
            rc, out, err = self.beat(R, NOW, rig)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual((len(evs(R, "app.promote")), commits(R), hook_calls(marker) - h0),
                         (1, n0, 1))
        self.assertTrue(any("step=commit" in ln and not re.search(r"rc=0 ", ln)
            for ln in self.logs()))
        self.assertIn("obs-draft:", out)
        self.assertFalse([a for a in seen if "--no-verify" in a])
        self.new_home()
        R2, prop2, marker2 = self.promotable()
        fx.set_params(R2, sched_auto_commit=False)
        fx.commit_all(R2, "auto-commit-off")
        n2, h2, rig2 = commits(R2), hook_calls(marker2), Rig()
        self.assertEqual(self.beat(R2, NOW, rig2)[0], 0)
        self.assertEqual((len(evs(R2, "app.promote")), commits(R2), hook_calls(marker2) - h2),
                         (1, n2, 0))
        self.assertTrue(rig2.verbs_named("measure"))
        self.assertIn("M", fx.git(R2, "status", "--porcelain")[:3] + "M")

    def test_AT_438_7_E_1_non_evolvable_touch_is_refused_by_the_existing_gate(self):
        R, prop, marker = self.promotable()
        prm = json.loads((R / fx.PARAMS).read_text(encoding="utf-8"))
        fx.set_params(R, non_evolvable_globs=[*prm["non_evolvable_globs"], "docs/notes/*.md"])
        fx.commit_all(R, "nonevolvable-now")
        params0, n0, h0, tree0 = (R / fx.PARAMS).read_bytes(), commits(R), hook_calls(marker), \
            fx.snap(R)[0]
        self.assertEqual(self.beat(R, NOW, Rig())[0], 0)
        self.assertEqual((evs(R, "app.promote"), commits(R), hook_calls(marker) - h0), ([], n0, 0))
        self.assertTrue(any("NON-EVOLVABLE-NOW" in ln for ln in self.logs()), self.logs())
        self.assertEqual((R / fx.PARAMS).read_bytes(), params0)
        after = {k: v for k, v in fx.snap(R)[0].items() if not k.startswith("docs/06_quality/Self")}
        before = {k: v for k, v in tree0.items() if not k.startswith("docs/06_quality/Self")}
        self.assertEqual(after, before)


class TestAdvanceSteps(AdvanceCase):
    """受測模組 tools/lib/selfimproving/patrol.py：approve 後的 sandbox／verify／card、
    晉升回滾與收尾。"""

    def frozen(self, R: Path, **kw) -> str:
        return fx2.drive_to(R, "frozen", **kw)

    def test_AT_439_3_1_approve_runs_sandbox_verify_card_verbatim(self):
        R = fx4.p4_base()
        p1 = self.frozen(R)
        p3 = self.frozen(R, target=fx2.OTHER, heldout=fx2.make_heldout(
            fx.new_dir("ho"), probes="always_red", target=fx2.OTHER))
        p2 = fx2.new_prop(R, action="add")
        fx2.issue_card(R, p2)
        rc, out, err, _, _ = fx2.decide_say(R, p2, f"核准 {p2}")
        self.assertEqual(rc, 0, out + err)
        n_dec, rig = len(evs(R, "dec")), Rig()
        for _ in (0, 1):
            self.assertEqual(self.beat(R, NOW, rig)[0], 0)
        for p in (p1, p3):
            kinds = [e["kind"] for e in fx4.ledger(R) if e.get("prop") == p
                     and e["kind"] in ("app.sandbox", "app.verify", "card")]
            self.assertEqual([k for k in kinds if k != "card"], ["app.sandbox", "app.verify"], p)
            self.assertEqual(kinds[-1], "card")
            ver = [e for e in evs(R, "app.verify") if e["prop"] == p][-1]
            text = self.M(R, "card", p)[1]
            self.assertIn(f"驗證：{ver['verdict']}", text)
        self.assertEqual([e for e in evs(R, "app.verify") if e["prop"] == p3][-1]["verdict"],
            "FAIL")
        self.assertEqual(len(evs(R, "dec")), n_dec, "巡邏器不代決（FAIL 的退回與否決是人的決定）")
        self.assertEqual([e for e in evs(R, "app.sandbox") if e["prop"] == p2], [])
        self.assertTrue(any("缺 heldout.freeze" in ln for ln in self.logs()))
        self.assertEqual(skips(R), [])
        self.assertEqual(len([e for e in evs(R, "app.sandbox") if e["prop"] == p1]), 1)

    def test_AT_439_3_2_promote_rollback_then_run_close(self):
        R = fx4.p4_base()
        pb = fx2.drive_to(R, "promoted")
        fx.commit_all(R, "pb-promoted")
        pa = fx2.drive_to(R, "verified", target=fx2.OTHER, heldout=fx2.make_heldout(
            fx.new_dir("ho"), probes="count", target=fx2.OTHER))
        self.cdec(R, pa, "promote")
        self.cdec(R, pb, "rollback", reason="太慢")
        fx.commit_all(R, "decisions")
        install_hook(R)
        n0, rig = commits(R), Rig()
        for _ in (0, 1):
            self.assertEqual(self.beat(R, NOW, rig)[0], 0)
        self.assertEqual(commits(R), n0 + 2)
        for prop, kind in ((pa, "app.promote"), (pb, "app.rollback")):
            self.assertEqual(len([e for e in evs(R, kind) if e["prop"] == prop]), 1, kind)
        self.assertTrue(rig.verbs_named("measure"))
        subjects = fx.git(R, "log", "-2", "--format=%B")
        self.assertTrue(pa in subjects and pb in subjects)
        close = evs(R, "run.close")
        self.assertEqual(len(close), 1)
        self.assertEqual(set(close[0]["outcomes"]), {pa, pb})
        self.assertEqual(len(rig.verbs_named("run-close")), 1)

    def test_AT_439_3_E_1_only_approve_moves_sandbox(self):
        R = fx4.p4_base()
        props = {}
        for n, (label, dkind, extra) in enumerate((
                ("reject", "reject", {"reason_class": "證據不足", "reason": "x"}),
                ("return", "return", {"reason_class": "證據不足", "reason": "x"}),
                ("approve", "approve", {})), start=1):
            props[label] = fx2.new_prop(R, target=f"docs/notes/f{n}.md")
            self.cdec(R, props[label], dkind, **extra)
            self.cli_ok(R, "run-close", "--run", fx2.open_run(R), "--by", "main")
        props["decline"] = fx2.drive_to(R, "verified", target="docs/notes/f4.md")
        self.cdec(R, props["decline"], "decline-promote", reason_class="風險過高", reason="x")
        self.cli_ok(R, "run-close", "--run", fx2.open_run(R), "--by", "main")
        props["handoff"] = fx2.new_prop(R, route="handoff:T1")
        self.cdec(R, props["handoff"], "ack-handoff")
        before = {k: len([e for e in fx4.ledger(R) if e.get("prop") == v and e["kind"].startswith(
            ("app.", "card"))]) for k, v in props.items()}
        n_dec = len(evs(R, "dec"))
        rig = Rig()
        for _ in (0, 1):
            self.assertEqual(self.beat(R, NOW, rig)[0], 0)
        after = {k: len([e for e in fx4.ledger(R) if e.get("prop") == v and e["kind"].startswith(
            ("app.", "card"))]) for k, v in props.items()}
        self.assertEqual(after, before)
        self.assertEqual(len(evs(R, "dec")), n_dec)
        self.assertEqual(skips(R), [])

    def test_AT_439_4_1_no_dec_no_motion_and_forged_dec_is_refused(self):
        R = fx4.p4_base()
        pc = fx2.new_prop(R, target=fx2.OTHER)
        pd = fx2.drive_to(R, "verified")
        pe = fx2.prop_event(R, pd)  # 手寫的 Console 載體 dec：稽核檔不存在，decverify 回查必失敗
        fx.append_events(R, [fx.ev("dec", "掌舵者", prop=pd, dkind="promote", digest=pe["digest"],
                                   carrier="console", audit_ref=fx2.new_uuid(),
                                   audit_sha256=fx.H(5), key_id="00000000", decider="admin")])
        fx.commit_all(R, "forged")
        before_c = [e for e in fx4.ledger(R) if e.get("prop") == pc]
        n0, rig = commits(R), Rig()
        for _ in (0, 1):
            self.assertEqual(self.beat(R, NOW, rig)[0], 0)
        self.assertEqual([e for e in fx4.ledger(R) if e.get("prop") == pc], before_c)
        self.assertEqual(([e for e in evs(R, "app.promote") if e["prop"] == pd], commits(R)), ([],
            n0))
        self.assertTrue(any("step=推進" in ln and re.search(r"rc=1 code=[A-Z]", ln)
            for ln in self.logs()),
                        self.logs())
        res = self.check(R)
        # 偵測面仍在（NE：稽核檔缺席）
        self.assertNotEqual(self.S(res, "events.dec_console"), "PASS")

    def test_AT_439_4_E_1_missing_freeze_skips_without_a_sched_skip(self):
        R, prop, marker = self.promotable(fx4.sched_set_ev(O), fx4.run_open_f_ev(50, O + MIN,
            due_at=O),
                                          fx4.run_close_ev(50, O + 2 * MIN))
        fx2.drop_events(R, "heldout.freeze", prop)
        fx.commit_all(R, "freeze-dropped")
        n0, rig = commits(R), Rig()
        for _ in (0, 1):
            self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        self.assertEqual((evs(R, "app.promote"), commits(R), len(skips(R))), ([], n0, 0))
        self.assertEqual(sum("缺 heldout.freeze" in ln for ln in self.logs()), 2)
        fx.append_events(R, [fx.ev("heldout.freeze", "FZ", prop=prop, t=iso(O + H))])
        fx.commit_all(R, "freeze-restored")
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        self.assertEqual((len(evs(R, "app.promote")), commits(R)), (1, n0 + 2))


class TestRunLifecycle(P4TestCase):
    """受測模組 tools/lib/selfimproving/patrolrun.py 與 patrol.py：脫離式 spawn 之後的收尾與
    Console (a)。"""

    def spawned(self, *, with_prop: bool = False):
        R = self.enabled_repo()
        rig = Rig()
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        run = [e for e in evs(R, "run.open") if e.get("trigger") == "f"][0]["run"]
        tdir = self.home / "patrol" / run
        sj = json.loads((tdir / "spawn.json").read_text(encoding="utf-8"))
        rig.live.add(sj["pid"])  # 預設：無人主控的行程還活著
        return R, rig, run, tdir, sj

    def write_handback(self, tdir: Path, drop: str | None = None) -> None:
        heads = ["## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步指令"]
        (tdir / "handback.md").write_text("\n".join(f"{h}\n內容" for h in heads if h != drop),
                                          encoding="utf-8")

    def test_AT_438_6_1_close_follows_the_event_ledger_not_the_self_report(self):
        R, rig, run, tdir, sj = self.spawned()
        self.assertEqual(set(sj), {"pid", "started_at", "wall_due_at", "process_started_utc"})
        self.assertFalse((self.home / "locks" / "patrol.lock").exists())
        self.assertEqual(evs(R, "run.close"), [])
        self.write_handback(tdir)
        rig.live.clear()
        self.assertEqual(self.beat(R, O + H + 15 * MIN, rig)[0], 0)
        close = evs(R, "run.close")
        self.assertEqual([(c["run"], c.get("no_event")) for c in close], [(run, True)])
        self.assertIn("closed_at", json.loads((tdir / "spawn.json").read_text(encoding="utf-8")))
        self.new_home()
        R2 = self.enabled_repo()
        self.cli_ok(R2, "attr", "--type", "root", "--by", "SA", "--obs", fx.obs_id(1), "--item",
                    "DOC=docs/06_quality/", "--root-cause", "docs/stale-note")
        self.cli_ok(R2, "attr-confirm", "--att", fx.aid(1), "--by", "QA")
        rig2 = Rig()
        self.assertEqual(self.beat(R2, O + H, rig2)[0], 0)
        run2 = [e for e in evs(R2, "run.open") if e.get("trigger") == "f"][0]["run"]
        env = {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": run2}
        with mock.patch.dict(os.environ, env):
            rc, out, err = self.M(R2, "prop-new", "--run", run2, *fx.good_prop_args(R2, "P"))
        self.assertEqual(rc, 0, out + err)
        self.write_handback(self.home / "patrol" / run2)
        rig2.live.clear()
        self.assertEqual(self.beat(R2, O + H + 15 * MIN, rig2)[0], 0)
        self.assertEqual(evs(R2, "run.close"), [])
        self.assertIn(run2, [r["run"] for r in self.status(R2)["open_runs"]])
        self.assertIn("closed_at", json.loads(
            (self.home / "patrol" / run2 / "spawn.json").read_text(encoding="utf-8")))

    def test_AT_438_6_2_one_unattended_run_at_a_time(self):
        R = fx4.p4_base(events=[fx4.sched_set_ev(O, period=60)])  # 一小時一格：硬牆內可跨格
        rig = Rig()
        self.assertEqual(self.beat(R, O + 30 * MIN, rig)[0], 0)
        run = [e for e in evs(R, "run.open") if e.get("trigger") == "f"][0]["run"]
        rig.live.add(json.loads((self.home / "patrol" / run / "spawn.json").read_text(
            encoding="utf-8"))["pid"])
        ref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        with fx4.with_key(fx2.AUDIT_KEY):
            for when in (O + 40 * MIN, O + H + 10 * MIN):
                self.assertEqual(self.beat(R, when, rig)[0], 0)
        self.assertEqual(len(rig.spawner.calls), 1)
        self.assertEqual(sum("已有進行中的無人運轉" in ln for ln in self.logs()), 2)
        mine = [s for s in skips(R) if s.get("audit_ref") == ref]
        self.assertEqual([s["reason"] for s in mine], ["run-open"])
        plain = [s for s in skips(R) if "carrier" not in s and s["reason"] == "run-open"]
        self.assertEqual(len(plain), 1)
        rig.live.clear()
        self.assertEqual(self.beat(R, O + H + 20 * MIN, rig)[0], 0)
        self.assertEqual(len(rig.spawner.calls), 2)

    def test_AT_438_6_E_1_incomplete_handback_harness_kill_and_overdue(self):
        mark = unattended_authz.HARNESS_BG_KILL_MARK
        cases = {"handback": ("handback 不完整", False), "harness": ("harness 背景殺行程", False),
                 "overdue": ("逾牆終止", True)}
        for label, (needle, alive) in cases.items():
            with self.subTest(label):
                self.new_home()
                R, rig, run, tdir, sj = self.spawned()
                self.write_handback(tdir, drop="## 卡在哪" if label == "handback" else None)
                if label == "harness":
                    (tdir / "stderr.txt").write_text(f"x\n{mark}\n", encoding="utf-8")
                now = O + H + 15 * MIN
                if alive:
                    now = sched.datetime.fromisoformat(sj["wall_due_at"]) + MIN
                else:
                    rig.live.clear()
                self.assertEqual(self.beat(R, now, rig)[0], 0)
                self.assertEqual(len(rig.spawner.calls), 1)
                self.assertEqual(sum(needle in ln for ln in self.logs()), 1, self.logs())
                self.assertEqual(rig.killed, [sj["pid"]] if alive else [])
                self.assertEqual([c.get("no_event") for c in evs(R, "run.close")], [True])

    def test_AT_438_8_1_console_run_request_runs_in_the_same_heartbeat(self):
        R = fx4.p4_base()
        ref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        rig = Rig()
        with fx4.with_key(fx2.AUDIT_KEY):
            self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        opened = evs(R, "run.open")
        self.assertEqual([(e["trigger"], e["carrier"], e["audit_ref"]) for e in opened],
                         [("a", "console", ref)])
        self.assertEqual(len(evs(R, "research.scan")), 1)
        self.assertEqual(len(rig.spawner.calls), 1)
        run = opened[0]["run"]
        self.assertIn("trigger=a",
            (self.home / "patrol" / run / "brief.md").read_text(encoding="utf-8"))
        self.assertTrue((self.home / "patrol" / run / "spawn.json").is_file())
        rig.live.clear()
        self.assertEqual(self.beat(R, O + H + 15 * MIN, rig)[0], 0)
        self.assertEqual([c.get("no_event") for c in evs(R, "run.close")], [True])
        self.assertEqual(skips(R), [])

    def test_AT_438_8_E_1_blocked_console_run_stays_open_and_logs_only(self):
        cases = {"quota-band": dict(band="prepare"), "other-driver": dict(quiet=False),
                 "blackout": dict(hm="22:00"), "spawn-failed": dict(which=None)}
        for code, kw in cases.items():
            with self.subTest(code):
                self.new_home()
                R = fx4.p4_base()
                self.audit("run-request", lambda r: fx4.body_run_request(r))
                hm = kw.pop("hm", "12:00")
                rig = Rig(**kw)
                with fx4.with_key(fx2.AUDIT_KEY):
                    self.assertEqual(self.beat(R, O + H, rig, hm=hm)[0], 0)
                self.assertEqual((len(evs(R, "run.open")), len(rig.spawner.calls), skips(R)), (1, 0,
                    []))
                self.assertTrue(any("step=運轉" in ln and f"code={code}" in ln
                    for ln in self.logs()),
                                self.logs())
                rig.band, rig.quiet, rig.which = "free", True, fx4.STUB
                with fx4.with_key(fx2.AUDIT_KEY):
                    self.assertEqual(self.beat(R, O + H + 15 * MIN, rig)[0], 0)
                self.assertEqual((len(evs(R, "run.open")), len(rig.spawner.calls)), (1, 1))


class TestIngestAndLog(P4TestCase):
    """受測模組 tools/lib/selfimproving/patrol.py：Console 稽核檔入帳順序、拒收處置與日誌格式。"""

    def t(self, minutes: int) -> str:
        return f"2026-10-21T09:{minutes:02d}:00+08:00"

    def beat_key(self, R: Path, now: datetime, rig: Rig | None = None, *args: str):
        with fx4.with_key(fx2.AUDIT_KEY):
            return self.beat(R, now, rig, *args)

    def test_AT_439_1_1_five_kinds_in_audit_time_order(self):
        R = fx4.p4_base()
        prop = fx2.new_prop(R)
        digest = fx2.prop_event(R, prop)["digest"]
        # audit_ref 遞減、time 遞增：排序鍵若只看 audit_ref（SCG-4 一審 B-1 存活突變）入帳序反轉
        refs = sorted((fx2.new_uuid() for _ in range(5)), reverse=True)
        self.audit("run-request", lambda r: fx4.body_run_request(r, time=self.t(1)), ref=refs[0])
        self.audit("obs-add", lambda r: fx2.body_obs_add(r, time=self.t(2)), ref=refs[1])
        self.audit("sched-set", lambda r: fx4.body_sched_set(r, False, 1440, time=self.t(3)),
                   ref=refs[2])
        self.audit("decide", lambda r: fx2.body_decide(r, prop, digest, "approve", time=self.t(4)),
                   subject=prop, ref=refs[3])
        self.audit("obs-close", lambda r: fx2.body_obs_close(r, fx.obs_id(1), "decided：測試",
                                                             time=self.t(5)), subject=fx.obs_id(1),
                   ref=refs[4])
        nokey = fx4.clone(R)
        self.assertEqual(self.beat(nokey, NOW, Rig())[0], 0)  # 無金鑰變數：全部拒收、稽核檔保留
        self.assertEqual(status.console_pending(fx4.ledger(nokey), True)["count"], 5)
        self.assertEqual(sum("AUDIT-KEY-MISSING" in ln for ln in self.logs()), 5)
        rig = Rig()
        self.assertEqual(self.beat_key(R, NOW, rig)[0], 0)
        ingest = [("sched-set" if a[0] == "sched" else a[0]) for a in rig.verbs_log
                  if a[0] in ("run-open", "obs-add", "obs-close", "sched", "decide")
                  and "--audit-ref" in a]
        self.assertEqual(ingest, ["run-open", "obs-add", "sched-set", "decide", "obs-close"])
        self.assertEqual(status.console_pending(fx4.ledger(R), True)["count"], 0)
        self.assertEqual(len(evs(R, "obs.add")) + len(evs(R, "obs.close")), 2)
        self.new_home()  # 同 time：依 audit_ref 位元組序
        R2 = fx4.p4_base()
        low, high = sorted([fx2.new_uuid(), fx2.new_uuid()])
        fx4.audit_file(self.home, "sched-set", lambda r: fx4.body_sched_set(r, False, 1440,
                                                                           time=self.t(7)),
                       ref=high, key=fx2.AUDIT_KEY)
        fx4.audit_file(self.home, "run-request", lambda r: fx4.body_run_request(r, time=self.t(7)),
                       ref=low, key=fx2.AUDIT_KEY)
        rig2 = Rig()
        self.assertEqual(self.beat_key(R2, NOW, rig2)[0], 0)
        order = [a[0] for a in rig2.verbs_log if "--audit-ref" in a]
        self.assertEqual(order, ["run-open", "sched"])

    def test_AT_439_1_E_1_key_never_reaches_any_output(self):
        key = fx2.AUDIT_KEY
        R = self.enabled_repo()
        self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 120, time=self.t(1)))
        self.audit("run-request", lambda r: fx4.body_run_request(r, time=self.t(2)))
        rig = Rig()
        rc, out, err = self.beat_key(R, O + H, rig)
        rc2, out2, err2 = self.beat_key(R, O + H + MIN, rig, "--json")
        self.assertEqual((rc, rc2), (0, 0))
        blobs = [out, err, out2, err2, json.dumps(rig.spawner.calls, default=str)]
        for root in (self.home, R / "docs"):
            blobs += [p.read_bytes().decode("utf-8", errors="replace")
                      for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts]
        self.assertEqual(sum(key in b for b in blobs), 0)
        kinds = [e["kind"] for e in fx4.ledger(R) if e["kind"] in ("sched.set", "run.open")]
        self.assertEqual(kinds[:3], ["sched.set", "sched.set", "run.open"])
        self.assertEqual(evs(R, "sched.set")[-1]["period_minutes"], 120)
        obj = sched.schedule_obj(si_events.load_sound_events(R / fx.EVL), fx.params_dict(),
                                 O + H + MIN)
        self.assertEqual(obj["cell_start"], iso(O + H))

    def test_AT_439_2_1_rejected_file_kept_logged_once_and_lock_busy_retried(self):
        R = fx4.p4_base()
        ux = self.audit("sched-set", lambda r: fx4.body_sched_set(r, False, 1440), tamper="flip")
        uy = self.audit("sched-set", lambda r: fx4.body_sched_set(r, False, 1440))
        rig = Rig()
        ledger = evwrite.lock_path_for(evwrite.ensure_home(self.home).parent, R / fx.EVL)
        with mock.patch.object(evwrite, "LOCK_TIMEOUT_SECONDS", 0.3), \
                apply_lock.acquire(ledger, 5, 600):
            self.assertEqual(self.beat_key(R, NOW, rig)[0], 0)
        self.assertEqual([e for e in evs(R, "sched.set") if e.get("audit_ref") == uy], [])
        self.assertEqual(self.beat_key(R, NOW, rig)[0], 0)
        self.assertEqual(len([e for e in evs(R, "sched.set") if e.get("audit_ref") == uy]), 1)
        rc, out, _ = self.ingest(R, uy)  # 互動視窗手動入帳：同一 audit_ref 不得二次入帳
        self.assertEqual(rc, 1)
        self.assertEqual(self.beat_key(R, NOW, rig)[0], 0)
        self.assertEqual(len([e for e in evs(R, "sched.set") if e.get("audit_ref") == uy]), 1)
        self.assertTrue((self.home / "console_audit" / f"{ux}.json").exists())
        pend = status.console_pending(fx4.ledger(R), True)
        self.assertEqual([i["audit_ref"] for i in pend["items"]], [ux])
        mine = [ln for ln in self.logs() if ux in ln]
        self.assertEqual(len(mine), 1)
        self.assertIn("AUDIT-MAC-MISMATCH", mine[0])
        self.assertIn("obs-draft", mine[0])
        self.assertEqual(sum(a[:2] == ["sched", "set"] and ux in a for a in rig.verbs_log), 3)

    def test_AT_439_2_E_1_each_refusal_keeps_the_file_and_logs_one_line(self):
        R = fx4.p4_base()
        good = fx4.body_sched_set
        refs = {"AUDIT-KEY-MISSING": self.audit("sched-set", lambda r: good(r, False, 1440))}
        kind_ref = fx2.new_uuid()
        fx2.write_audit(self.home, kind="obs-add", ref=kind_ref, subject=None,
                        body=fx2._jdump(good(kind_ref, False, 1440)), key=fx2.AUDIT_KEY)
        refs["AUDIT-KIND-MISMATCH"] = kind_ref
        name_ref, body_ref = fx2.new_uuid(), fx2.new_uuid()
        fx2.write_audit(self.home, kind="sched-set", ref=body_ref, subject=None, name=name_ref,
                        body=fx2._jdump(good(body_ref, False, 1440)), key=fx2.AUDIT_KEY)
        refs["AUDIT-REF-MISMATCH"] = name_ref
        ev0, obs0, rig = (R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b"", \
            (R / fx.LEDGER).read_bytes(), Rig()
        for _ in (0, 1):
            self.assertEqual(self.beat(R, NOW, rig)[0], 0)
        for code, ref in refs.items():
            lines = [ln for ln in self.logs() if ref in ln]
            self.assertEqual(len(lines), 1, (code, lines))
            self.assertIn(f"code={code}", lines[0])
            self.assertIn("obs-draft", lines[0])
            self.assertTrue((self.home / "console_audit" / f"{ref}.json").exists())
        pend = {i["audit_ref"] for i in status.console_pending(fx4.ledger(R), True)["items"]}
        self.assertEqual(pend, set(refs.values()))
        self.assertEqual(((R / fx.EVL).read_bytes() if (R / fx.EVL).exists() else b"",
                          (R / fx.LEDGER).read_bytes()), (ev0, obs0))
        calls = [a for a in rig.verbs_log if "--audit-ref" in a]
        self.assertEqual(len(calls), 6)  # 每份每心跳至多一次
        used = fx4.audit_file(self.home, "sched-set", lambda r: good(r, False, 1440),
                              key=fx2.AUDIT_KEY)
        # 已入帳的檔不再出現在待入帳清單（也就不會被重試）
        self.assertEqual(self.ingest(R, used)[0], 0)
        n = len([a for a in rig.verbs_log if used in a])
        self.assertEqual(self.beat(R, NOW, rig)[0], 0)
        self.assertEqual(len([a for a in rig.verbs_log if used in a]), n)

    def test_AT_439_5_1_log_format_and_steps_are_independent(self):
        R = self.enabled_repo()
        self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 1440), tamper="flip")
        rig = Rig()
        self.assertEqual(self.beat_key(R, O + H, rig)[0], 0)
        lines = self.logs()
        self.assertTrue(all(LOG_LINE.match(ln) for ln in lines), lines)
        self.assertTrue(any(re.match(r"\S+ step=入帳 rc=1 code=\S+ ", ln) for ln in lines), lines)
        self.assertTrue(any("step=到期" in ln for ln in lines))
        self.assertTrue(any("step=運轉" in ln for ln in lines))
        self.assertEqual(len([e for e in evs(R, "run.open") if e.get("trigger") == "f"]), 1)
        before_check = [(i["id"], i["status"]) for i in self.check(R)["items"]]
        before_sched = self.status(R)["schedule"]
        (self.home / "patrol" / "patrol.log").unlink()
        self.assertEqual([(i["id"], i["status"]) for i in self.check(R)["items"]], before_check)
        self.assertEqual(self.status(R)["schedule"], before_sched)

    def test_AT_439_5_E_1_every_line_is_one_line_and_free_of_the_key(self):
        R = self.enabled_repo()
        ref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 1440,
            reason="換行\n原因"),
                         tamper="flip")
        rig = Rig()
        self.assertEqual(self.beat_key(R, O + H, rig)[0], 0)
        raw = (self.home / "patrol" / "patrol.log").read_text(encoding="utf-8")
        for ln in raw.splitlines():
            self.assertRegex(ln, LOG_LINE)
            ok_step = "rc=0 code=-" in ln
            bad_step = re.search(r"rc=[1-9]\d* code=[A-Z][A-Z-]+", ln)
            self.assertTrue(ok_step or bad_step or "code=" in ln, ln)
        failing = [ln for ln in raw.splitlines() if ref in ln]
        self.assertEqual(len(failing), 1)
        self.assertRegex(failing[0], r"step=入帳 rc=[1-9]\d* code=AUDIT-MAC-MISMATCH ")
        self.assertEqual([ln for ln in raw.splitlines() if fx2.AUDIT_KEY in ln], [])

    def test_D_IMP_9_m_class_asks_for_memory_dir_only_when_a_step_is_pending(self):
        """真機首跳 21:00：已晉升、量測中、無待回滾的 M 類 PROP（PROP-SI-004／006／007）
        每心跳被記「須人工給 --memory-dir」，其實無事可做；只有待 sandbox／verify／promote／
        rollback 才解析記憶目錄（D-IMP-6 (7) 的原意；P7 起解析不到記 `MEMORY-DIR-UNRESOLVED`，
        舊碼 `MEMORY-DIR` 已移除，TCS-P7 AC-SI-48-2／48-5）。"""
        un = "MEMORY-DIR-UNRESOLVED"
        cases = (("measuring", 0, None, []), ("promoted", 0, None, []), ("closed", 0, None, []),
                 ("approved", 0, None, [un]), ("sandboxed", 0, None, [un]),
                 ("verified", 0, "dec", [un]), ("measuring", 1, None, [un]))
        for state, rollbacks, pend, want in cases:
            p = mock.Mock(cls="M", state=state, pending_promote=pend, pending_rollbacks=rollbacks)
            codes, ctx = [], mock.Mock()
            ctx.fold.return_value.props = {"P": p}
            ctx.log.side_effect = lambda *a, codes=codes: codes.append(a[2])
            with self.subTest(state=state, rollbacks=rollbacks), \
                    mock.patch.object(patrolrun.memdir, "resolve", return_value=None):
                self.assertFalse(patrolrun._advance_prop(ctx, "P"))
                self.assertEqual(codes, want)


if __name__ == "__main__":
    sys.exit(unittest.main())
