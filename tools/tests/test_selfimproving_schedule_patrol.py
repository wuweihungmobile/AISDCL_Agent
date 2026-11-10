# 受測面：tools/lib/selfimproving/patrol.py（程式碼鎖，非散文）
"""SelfImproving P4 巡邏心跳、無人運轉與授權（TCS-SelfImproving-P4 §2 B 節 SP 的 21 個 AT：
R143～R144、R148～R153、R167；受測 `tools/lib/selfimproving/patrol.py`、`patrolrun.py`、
`patrolbrief.py`）。

心跳以注入的 `now`、事件時間、本機時分、額度帶、對話靜默、`claude` 路徑與替身 `spawn_detached`
驅動（`Rig`，見 `_selfimproving_p4_fixtures.py`）；動詞走真入口（行程內）、夾具 repo 為真 git。
"""

from __future__ import annotations

import ast
import contextlib
import json
import os
import re
import secrets
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p4_fixtures as fx4
from _selfimproving_p4_fixtures import D1, MIN, STUB, H, O, P4TestCase, Rig, iso

from lib import resume_route, unattended_authz
from lib.selfimproving import evwrite, patrol, patrolbrief, runner, sched, status

ROOT = fx.ROOT
PKG = ROOT / "tools" / "lib" / "selfimproving"
RUN_A, RUN_B = fx.rid(1), fx.rid(2)
LEDGER_COORD = f"{fx.EVL}:1"


def setUpModule() -> None:
    fx.setup("si_p4_")


def tearDownModule() -> None:
    fx.teardown()


def evs(R: Path, kind: str) -> list[dict]:
    return [e for e in fx4.ledger(R) if e["kind"] == kind]


def skips(R: Path) -> list[dict]:
    return evs(R, "sched.skip")


def opens_f(R: Path) -> list[dict]:
    return [e for e in evs(R, "run.open") if e.get("trigger") == "f"]


def home_tree(home: Path) -> dict[str, bytes]:
    return {p.relative_to(home).as_posix(): p.read_bytes() for p in sorted(home.rglob("*"))
            if p.is_file()}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestHeartbeatShape(P4TestCase):
    """受測模組 tools/lib/selfimproving/patrol.py：心跳步驟序、dry-run、用法、鎖與逃生口。"""

    def test_AT_436_3_1_single_heartbeat_steps_and_detached_spawn(self):
        R = self.enabled_repo()
        ref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 1440))
        rig = Rig()
        with fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.beat(R, O + H, rig)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(re.findall(r"(?m)^step=(\S+) ", out), ["巡視", "入帳", "到期", "運轉",
            "推進"])
        heads = [a[:2] if a[0] == "sched" else a[:1] for a in rig.verbs_log]
        order = [heads.index(["sched", "set"]), heads.index(["run-open"]),
                 heads.index(["research"]), heads.index(["scan"])]
        self.assertEqual(order, sorted(order), heads)
        self.assertEqual(len(rig.spawner.calls), 1)
        self.assertFalse((self.home / "locks" / "patrol.lock").exists(), "返回時鎖已釋放")
        run = opens_f(R)[0]["run"]
        self.assertTrue((self.home / "patrol" / run / "spawn.json").is_file())
        self.assertEqual([e["audit_ref"] for e in evs(R, "sched.set") if "audit_ref" in e], [ref])
        rc, out, _ = self.beat(R, O + H + MIN, rig, "--json")
        obj = json.loads(out)
        self.assertEqual((rc, obj["kind"], len(obj["steps"])), (0, "patrol", 5))
        self.assertEqual(list(obj), ["ok", "kind", "dry_run", "steps", "events"])
        src = (PKG / "patrol.py").read_text(encoding="utf-8").splitlines()
        code = [ln for ln in src if not ln.lstrip().startswith("#")]
        self.assertEqual([ln for ln in code if "communicate" in ln], [], "心跳本身不等待子行程")

    def test_AT_436_3_2_dry_run_writes_nothing(self):
        R = self.enabled_repo()
        ref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 1440))
        rig = Rig()
        before = (fx.snap(R), home_tree(self.home), sorted(p.name for p in self.home.rglob("*")))
        with fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.beat(R, O + H, rig, "--dry-run")
        self.assertEqual(rc, 0, out + err)
        self.assertIn(ref, out)
        self.assertIn("將", out)
        after = (fx.snap(R), home_tree(self.home), sorted(p.name for p in self.home.rglob("*")))
        self.assertEqual(after, before)
        self.assertEqual((rig.verbs_log, len(rig.spawner.calls)), ([], 0))
        self.assertFalse((self.home / "patrol").exists())

    def test_AT_436_3_E_1_usage_errors_are_rc3_before_anything(self):
        R = self.enabled_repo()
        before = fx.snap(R)
        for label, argv in {
                "no-offset": ["patrol", "--now", "2026-11-02T08:00:00"],
                "bogus": ["patrol", "--bogus"], "run-flag": ["patrol", "--run", RUN_A]}.items():
            with self.subTest(label):
                self.usage_error(*self.M(R, *argv), label)
        missing = fx.new_dir("missing")
        self.usage_error(*self.run_main(["patrol", "--repo", str(missing)]), "repo")
        blocker = fx.new_dir("blocker")
        blocker.write_bytes(b"x")  # 檔案底下建不出目錄＝家目錄不可寫（不依賴唯讀屬性）
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_DIR": str(blocker / "si")}):
            rc, out, err = self.M(R, "patrol", "--now", iso(O + H))
        self.usage_error(rc, out, err, "home")
        self.assertIn("HOME-UNWRITABLE", err)
        self.assertEqual(fx.snap(R), before)

    def test_AT_436_3_E_2_lock_unattended_and_exception_do_not_retry(self):
        R = self.enabled_repo()
        before = self.snap(R)
        lock = evwrite.ensure_home(self.home) / "patrol.lock"
        with unittest.mock.patch.object(evwrite, "LOCK_TIMEOUT_SECONDS",
            0), contextlib.ExitStack() as st:
            from lib import apply_lock
            st.enter_context(apply_lock.acquire(lock, 0, 7200))
            rc, out, err = self.beat(R, O + H)
        self.assertEqual(rc, 0)
        self.assertIn("已有巡邏在跑", out)
        self.assertEqual(self.snap(R), before)
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, _ = self.beat(R, O + H, Rig())
        self.rejected(rc, out, {"UNATTENDED-REFUSED"})
        self.assertEqual(self.snap(R), before)
        rig = Rig()
        rig.boom = RuntimeError("boom")
        rc, out, err = self.beat(R, O + H, rig)
        self.assertEqual(rc, 1)
        self.assertTrue(any("PATROL-EXCEPTION" in ln for ln in self.logs()), self.logs())
        self.assertEqual(len(rig.verbs_log), 1, "例外不重試")
        self.assertFalse(lock.exists(), "鎖已釋放")

    def test_D_IMP_9_real_verbs_find_the_entry_whatever_the_path_order(self):
        """OS 任務真機首跳（2026-11-09 20:30）：入口以腳本執行時 tools/lib 排在 tools 前，名字
        `selfimproving` 解析成同名套件 tools/lib/selfimproving/ ⇒ 每心跳入帳 AttributeError。"""
        R, saved = str(fx4.p4_base()), sys.modules.pop("selfimproving", None)
        try:
            order = [str(ROOT / "tools" / "lib"), str(ROOT / "tools"), *sys.path]
            with (mock.patch.object(sys, "path", order), mock.patch.object(runner, "run_argv",
                  return_value=types.SimpleNamespace(rc=0, out="ABSENT", err="", timed_out=False))):
                rc, out, err = patrol._real_verbs(["status", "--json", "--repo", R])
        finally:  # 不讓同名套件留在 sys.modules（後面的 `import selfimproving` 要拿到入口）
            if saved is not None:
                sys.modules["selfimproving"] = saved
            elif getattr(sys.modules.get("selfimproving"), "main", None) is None:
                sys.modules.pop("selfimproving", None)
        self.assertEqual((rc, "schedule" in json.loads(out)), (0, True), err)

    def test_AT_436_5_E_1_patrol_off_is_a_whole_no_op(self):
        R = self.enabled_repo()
        ref = self.audit("sched-set", lambda r: fx4.body_sched_set(r, True, 1440))
        for value in ("1", "0"):
            with self.subTest(value), mock.patch.dict(os.environ, {"AUTOSDD_SI_PATROL_OFF": value}):
                before_repo, n = fx.snap(R), len(self.logs())
                rc, out, err = self.beat(R, O + H, Rig())
                self.assertEqual(rc, 0, out + err)
                self.assertEqual(fx.snap(R), before_repo)
                self.assertFalse((self.home / "locks" / "patrol.lock").exists())
                self.assertEqual(len(self.logs()), n + 1)
                pend = status.console_pending(fx4.ledger(R), True)
                self.assertEqual([i["audit_ref"] for i in pend["items"]], [ref])
        with mock.patch.dict(os.environ,
            {"AUTOSDD_SI_PATROL_OFF": ""}), fx4.with_key(fx2.AUDIT_KEY):
            rc, out, err = self.beat(R, O + H, Rig())
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(len(opens_f(R)), 1)
        self.assertEqual(status.console_pending(fx4.ledger(R), True)["count"], 0)


class TestDueAndSkips(P4TestCase):
    """受測模組 tools/lib/selfimproving/patrol.py：到期判定、七種跳過的接線與每格至多一個運轉。"""

    def test_AT_436_2_E_0_patrol_real_quota_path_goes_through_measured_state(self):
        """D-IMP-11：巡邏器不注入 deps.quota 時走 sched.measured_state（補量），
        不再只讀過期快取。"""
        from lib import quota_policy
        ctx = types.SimpleNamespace(now=O, deps=types.SimpleNamespace(quota=None))
        seen = []

        def fake_state(now):
            seen.append(now)
            return types.SimpleNamespace()

        with mock.patch.object(sched, "measured_state", side_effect=fake_state), \
                mock.patch.object(quota_policy, "decide",
                                  return_value=types.SimpleNamespace(band="free")):
            band, verdict = patrol._quota(ctx)
        self.assertEqual((band, verdict, seen), ("free", {"skip": False, "degrade": False}, [O]))

    def test_AT_436_2_E_1_blackout_does_not_become_a_permanent_skip(self):
        R = self.enabled_repo(prm={"sched_blackout_local": ["21:00-00:30"]})
        rig = Rig()
        for minutes, hm in ((15, "22:15"), (30, "22:30"), (60, "23:00")):
            rc, out, err = self.beat(R, O + minutes * MIN, rig, hm=hm)
            self.assertEqual(rc, 0, out + err)
        got = skips(R)
        self.assertEqual([(s["reason"], s["due_at"]) for s in got], [("blackout", iso(O))])
        self.assertEqual((len(opens_f(R)), len(rig.spawner.calls)), (0, 0))
        rc, out, err = self.beat(R, O + 2 * H, rig, hm="00:40")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual([(e["trigger"], e["due_at"]) for e in opens_f(R)], [("f", iso(O))])
        self.assertEqual(len(rig.spawner.calls), 1)
        res = self.check(R)
        self.assertEqual([self.S(res, i) for i in ("sched.events", "run.trigger_f_has_patrol_by")],
                         ["PASS", "PASS"])

    def test_AT_436_6_1_at_most_one_f_run_per_cell(self):
        R = self.enabled_repo()
        rig = Rig()
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        n_skips = len(skips(R))
        for k in (2, 3):
            self.assertEqual(self.beat(R, O + k * H, rig)[0], 0)
        self.assertEqual((len(opens_f(R)), len(rig.spawner.calls), len(skips(R)) - n_skips),
                         (1, 1, 0))
        self.new_home()
        other =fx4.p4_base(events=[fx4.sched_set_ev(O), fx.run_open_ev(1)])
        rig2 = Rig()
        self.assertEqual(self.beat(other, O + H, rig2)[0], 0)
        self.assertEqual([s["reason"] for s in skips(other)], ["run-open"])
        self.assertEqual((len(opens_f(other)), len(rig2.spawner.calls)), (0, 0))

    def test_AT_436_6_E_1_prepare_band_skips_and_no_event_runs_are_not_results(self):
        R = self.enabled_repo()
        rig = Rig(band="prepare")
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        self.assertEqual([s["reason"] for s in skips(R)], ["quota-band"])
        self.assertEqual((len(opens_f(R)), len(rig.spawner.calls)), (0, 0))
        rig.band = "free"
        for when in (O + 2 * H, O + 3 * H, O + D1 + H, O + D1 + 2 * H):
            self.assertEqual(self.beat(R, when, rig)[0], 0)
        closes = evs(R, "run.close")
        self.assertEqual((len(opens_f(R)), [c.get("no_event") for c in closes]), (2, [True, True]))
        obj = self.status(R)
        self.assertEqual((obj["no_event"], obj["events_detected"]), (True, []))


class TestSpawnShape(P4TestCase):
    """受測模組 tools/lib/selfimproving/patrolrun.py：spawn 的 argv、環境白名單、牆鐘與前置序。"""

    def spawn_checks(self, R: Path, rig: Rig) -> dict:
        call = rig.spawner.calls[0]
        argv = call["argv"]
        self.assertEqual(argv[:2], [STUB, "-p"])
        run = re.search(r"無人運轉 (RUN-SI-\d+)", argv[2]).group(1)
        tdir = self.home / "patrol" / run
        self.assertEqual(argv, resume_route.fresh_argv(STUB, argv[2], tdir))
        brief = tdir / "brief.md"
        self.assertIn(str(brief), argv[2])
        self.assertTrue(brief.read_bytes())
        env = call["env"]
        self.assertEqual((env["AUTOSDD_UNATTENDED"], env["AUTOSDD_SI_PATROL_RUN"]), ("1", run))
        for k, v in resume_route.spawn_env().items():
            self.assertEqual(env[k], v, k)
        self.assertEqual(env[unattended_authz.HARNESS_BG_WAIT_ENV],
                         str(unattended_authz.RESUME_BG_WAIT_CEILING_SECONDS * 1000))
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(R))
        sj = read_json(tdir / "spawn.json")
        self.assertEqual(sj["pid"], rig.spawner.base + 1)
        wall = sched.datetime.fromisoformat(sj["wall_due_at"]) - sched.datetime.fromisoformat(
            sj["started_at"])
        self.assertEqual(wall.total_seconds(), unattended_authz.RESUME_HARD_WALL_SECONDS)
        return {"run": run, "brief": brief.read_text(encoding="utf-8")}

    def test_AT_438_1_1_spawn_argv_env_and_spawn_json(self):
        import inspect
        self.assertNotIn("timeout", inspect.signature(runner.spawn_detached).parameters)
        R = self.enabled_repo()
        rig = Rig()
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        got = self.spawn_checks(R, rig)
        self.assertIn("trigger=f", got["brief"])
        self.new_home()  # 兩個 repo 各一個家目錄（RUN 號會重疊，家目錄是機器層狀態）
        ref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        R2, rig2 = fx4.p4_base(), Rig()
        with fx4.with_key(fx2.AUDIT_KEY):
            self.assertEqual(self.beat(R2, O + H, rig2)[0], 0)
        got2 = self.spawn_checks(R2, rig2)
        self.assertIn("trigger=a", got2["brief"])
        self.assertEqual(evs(R2, "run.open")[0]["audit_ref"], ref)
        for plat, win in (("win32", True), ("linux", False)):  # 脫離旗標：兩個平臺各跑一次
            with self.subTest(plat), mock.patch.object(runner.sys, "platform", plat), \
                    mock.patch.object(runner.subprocess, "Popen") as popen:
                popen.return_value = types.SimpleNamespace(pid=77)
                self.assertEqual(runner.spawn_detached(["x"], env={}, cwd=Path(".")), 77)
                kw = popen.call_args.kwargs
                self.assertIs(kw["shell"], False)
                if win:
                    want = sum(getattr(runner.subprocess, n, 0) for n in (
                        "CREATE_BREAKAWAY_FROM_JOB", "CREATE_NEW_PROCESS_GROUP",
                        "DETACHED_PROCESS"))
                    self.assertEqual(kw["creationflags"], want)
                    self.assertNotIn("start_new_session", kw)
                else:
                    self.assertIs(kw["start_new_session"], True)
                    self.assertNotIn("creationflags", kw)

    def test_AT_438_1_2_research_branches_and_scan_only_in_log(self):
        R = self.enabled_repo()
        rig = Rig(fetch_rcs=[0, 2, 1])
        rig.scan_rows = ["| OBS-候選 | row-one |", "| OBS-候選 | row-two |"]
        obs0 = (R / fx.LEDGER).read_bytes()
        for k in range(3):
            if k:
                self.assertEqual(self.beat(R, O + k * D1 + 30 * MIN, rig)[0], 0)  # 收掉前一個運轉
            self.assertEqual(self.beat(R, O + k * D1 + H, rig)[0], 0)
        runs = opens_f(R)
        self.assertEqual(len(runs), 3)
        for k, e in enumerate(runs):
            self.assertEqual((e["by"], e["due_at"], e["coords"]),
                             ("patrol", iso(O + k * D1), [LEDGER_COORD]))
        kinds = [e["kind"] for e in evs_after(R, "run.open") if e["kind"].startswith("research")]
        self.assertEqual(kinds, ["research.scan", "research.scan", "research.skip"])
        self.assertEqual(evs(R, "research.skip")[0]["reason"], "offline")
        self.assertEqual(len(rig.spawner.calls), 3)
        joined = "\n".join(self.logs())
        self.assertIn("row-one", joined)
        self.assertIn("row-two", (self.home / "patrol" / runs[0]["run"] / "brief.md").read_text(
            encoding="utf-8"))
        self.assertEqual((R / fx.LEDGER).read_bytes(), obs0)

    def test_AT_438_1_3_changed_sources_are_copied_into_the_task_dir(self):
        """D-IMP-12：研究者只讀得到 --add-dir 的任務目錄，brief 只能列任務目錄下的副本。"""
        R = self.enabled_repo()
        rig = Rig()
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        run = opens_f(R)[0]["run"]
        tdir = self.home / "patrol" / run
        orig = next((self.home / "research").rglob("*.txt"))
        copy = tdir / "research" / orig.name
        self.assertEqual(copy.read_bytes(), orig.read_bytes())
        self.assertTrue(copy.read_bytes())
        brief = (tdir / "brief.md").read_text(encoding="utf-8")
        self.assertIn(str(copy), brief)
        self.assertNotIn(str(orig), brief)
        self.assertEqual(len(rig.spawner.calls), 1)

    def test_AT_438_1_E_4_source_copy_failure_does_not_spawn(self):
        R = self.enabled_repo()
        rig = Rig()
        rig.write_source = False  # 原檔不存在＝複製必失敗
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        self.assertEqual([(s["reason"], s["detail"].startswith("sources-copy-failed"))
                          for s in skips(R)], [("spawn-failed", True)])
        run = opens_f(R)[0]["run"]
        tdir = self.home / "patrol" / run
        self.assertEqual(len(rig.spawner.calls), 0)
        self.assertFalse((tdir / "spawn.json").exists())
        self.assertFalse((tdir / "research").exists())

    def test_AT_438_1_E_5_research_skip_has_no_copies_and_no_source_files(self):
        R = self.enabled_repo()
        rig = Rig(fetch_rcs=[1])
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        run = opens_f(R)[0]["run"]
        tdir = self.home / "patrol" / run
        self.assertEqual(len(evs(R, "research.skip")), 1)
        self.assertFalse((tdir / "research").exists())
        brief = (tdir / "brief.md").read_text(encoding="utf-8")
        self.assertNotIn(str(self.home / "research"), brief)
        self.assertEqual(len(rig.spawner.calls), 1)

    def test_AT_438_1_E_1_missing_claude_is_a_skip_before_any_run(self):
        R = self.enabled_repo()
        rig = Rig(which=None)
        for when in (O + H, O + 2 * H):
            self.assertEqual(self.beat(R, when, rig)[0], 0)
        got = skips(R)
        self.assertEqual([(s["reason"], "claude-not-found" in s["detail"]) for s in got],
                         [("spawn-failed", True)])
        self.assertEqual((evs(R, "run.open"), evs(R, "research.scan")), ([], []))
        self.assertEqual(list((self.home / "patrol").glob("RUN-*")), [])

    def test_AT_438_1_E_2_child_environment_is_a_whitelist(self):
        R = self.enabled_repo()
        planted = {k: "p-" + secrets.token_hex(6) for k in (
            "AUTOSDD_SI_AUDIT_KEY", "ANTHROPIC_API_KEY", "MY_SERVICE_TOKEN", "DB_PASSWORD",
            "AUTOSDD_QUOTA_HALT_PCT", "APPDATA")}
        rig = Rig()
        with mock.patch.dict(os.environ, {**planted, "AUTOSDD_SI_PATROL_OFF": ""}):
            self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        call = rig.spawner.calls[0]
        allowed = {*runner._ENV_KEYS, "APPDATA", "LOCALAPPDATA", "CLAUDE_CONFIG_DIR",
            "AUTOSDD_SI_DIR",
                   "AUTOSDD_UNATTENDED", "AUTOSDD_SI_PATROL_RUN",
                   unattended_authz.HARNESS_BG_WAIT_ENV,
                   *resume_route.spawn_env()}
        self.assertLessEqual(set(call["env"]), allowed)
        for key in ("AUTOSDD_SI_AUDIT_KEY", "ANTHROPIC_API_KEY", "MY_SERVICE_TOKEN", "DB_PASSWORD",
                    "AUTOSDD_QUOTA_HALT_PCT", "AUTOSDD_SI_PATROL_OFF"):
            self.assertNotIn(key, call["env"], key)
        blob = json.dumps(call["argv"], ensure_ascii=False) + "".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (self.home / "patrol").rglob("*") if p.is_file())
        for key in ("AUTOSDD_SI_AUDIT_KEY", "ANTHROPIC_API_KEY", "MY_SERVICE_TOKEN", "DB_PASSWORD",
                    "AUTOSDD_QUOTA_HALT_PCT"):
            self.assertNotIn(planted[key], blob, key)

    def test_AT_438_1_E_3_denied_breakaway_fails_closed(self):
        R = self.enabled_repo()
        rig = Rig()
        rig.spawner.fail = 1
        self.assertEqual(self.beat(R, O + H, rig)[0], 0)
        self.assertEqual([(s["reason"], s["detail"].startswith("breakaway-denied"))
            for s in skips(R)],
                         [("spawn-failed", True)])
        run = opens_f(R)[0]["run"]
        self.assertFalse((self.home / "patrol" / run / "spawn.json").exists())
        self.assertEqual(self.beat(R, O + H + 15 * MIN, rig)[0], 0)
        self.assertEqual((len(skips(R)), len(rig.spawner.calls), len(opens_f(R))), (1, 1, 1))
        self.new_home()
        ref = self.audit("run-request", lambda r: fx4.body_run_request(r))
        R2, rig2 = fx4.p4_base(), Rig()
        rig2.spawner.fail = 1
        with fx4.with_key(fx2.AUDIT_KEY):
            self.assertEqual(self.beat(R2, O + H, rig2)[0], 0)
        self.assertEqual((skips(R2), len(evs(R2, "run.open"))), ([], 1))
        self.assertTrue(any("breakaway-denied" in ln and "step=運轉" in ln for ln in self.logs()))
        self.assertFalse(any(p.name == "spawn.json" for p in (self.home / "patrol").rglob("*")
                             if evs(R2, "run.open")[0]["run"] in str(p) and False))
        self.assertEqual(self.beat(R2, O + H + 15 * MIN, rig2)[0], 0)
        self.assertEqual((len(rig2.spawner.calls), len(evs(R2, "run.open")), ref in json.dumps(
            evs(R2, "run.open"))), (1, 1, True))


def evs_after(R: Path, kind: str) -> list[dict]:
    """所有事件（依 seq）；供「某事件之後依序出現什麼」的斷言。"""
    return fx4.ledger(R)


class TestBrief(P4TestCase):
    """受測模組 tools/lib/selfimproving/patrolbrief.py：任務書生成與範本結構判準。"""

    FIELDS = {k: f"〈{k}〉" for k in patrolbrief.UPPER_FIELDS}

    def test_AT_438_2_1_render_fills_uppercase_and_keeps_field_placeholders(self):
        sop = fx.REAL_SOP.read_text(encoding="utf-8")
        tpl = patrolbrief.template_of(sop)
        self.assertEqual(patrolbrief.template_problems(sop), [])
        for band, degrade in (("free", ""), ("notice",
            patrolbrief.DEGRADE_TEXT.format(band="notice")),
                              ("converge", patrolbrief.DEGRADE_TEXT.format(band="converge"))):
            with self.subTest(band):
                text = patrolbrief.render(tpl, {**self.FIELDS, "BAND": band,
                    "DEGRADE_NOTE": degrade})
                left = [m for m in re.findall(r"<[A-Z][A-Z_]*>", text)
                        if m[1:-1] in patrolbrief.UPPER_FIELDS]
                self.assertEqual(left, [])
                for keep in ("<來源 id>", "<PROP>", "<held-out 目錄>", "<凍結者>"):
                    self.assertIn(keep, text)
                for k in ("RUN", "DUE_AT", "EVENTS", "RESEARCH_RESULT", "SOURCE_FILES",
                          "SCAN_CANDIDATES", "BUDGET_MINUTES", "HANDBACK_PATH"):
                    self.assertIn(f"〈{k}〉", text)
                self.assertIn("trigger=f", text)
                self.assertIn("## 禁止事項", text)
                self.assertEqual(len(re.findall(r"(?m)^[1-9]\. ", text)), 9)
                for marker in resume_route.HANDBACK_MARKERS:
                    self.assertIn(marker, text.splitlines())
                self.assertEqual("降載聲明：額度帶" in text, band != "free")

    def test_AT_438_2_E_1_template_defects_refuse_spawn(self):
        sop = fx.REAL_SOP.read_text(encoding="utf-8")
        tpl = patrolbrief.template_of(sop)
        fence_free = sop.replace("```text\n" + tpl, tpl).replace(tpl + "```", tpl)
        variants = {
            "heading": sop.replace("## 做了什麼", ""),
            "forbidden": sop.replace("## 禁止事項\n", ""),
            "step7": re.sub(r"(?m)^7\. .*\n", "", sop),
            "run": sop.replace("<RUN>", ""),
            "fence": fence_free.replace("```text\n", "").replace("\n```\n", "\n"),
        }
        R = self.enabled_repo()
        codes = {}
        for i, (label, text) in enumerate(variants.items()):
            problems = patrolbrief.template_problems(text)
            self.assertTrue(problems, label)
            codes[label] = problems[0].split(":")[0]
            fx.putb(R, fx4.SOP_REL, text.encode("utf-8"))
            fx.commit_all(R, f"sop-{label}")
            rig = Rig()
            self.assertEqual(self.beat(R, O + i * D1 + H, rig)[0], 0)
            last = skips(R)[-1]
            self.assertEqual(last["reason"], "spawn-failed", label)
            self.assertTrue(last["detail"].startswith("sop-template:"), last["detail"])
            self.assertEqual(len(rig.spawner.calls), 0, label)
        self.assertEqual((len(opens_f(R)), len(set(codes.values()))), (0, 5), codes)
        fx.putb(R, fx4.SOP_REL, sop.encode("utf-8"))  # 對照組：未刪的真 SOP 可 spawn
        fx.commit_all(R, "sop-control")
        rig = Rig()
        self.assertEqual(self.beat(R, O + 5 * D1 + H, rig)[0], 0)
        self.assertEqual((len(opens_f(R)), len(rig.spawner.calls)), (1, 1))


def _build_a(src: Path) -> dict:
    """受測模組 tools/lib/selfimproving/unattended.py（run-scoped 授權閘）的 A 類八動詞共同世界：
    運轉 `RUN_A`（已開、尚無研究事件）、一個已確認的根因歸因與一個待審的連結歸因、
    三個 PROP（待決、已退回、已核准）；回各編號。"""
    def ok(*argv):
        rc, out, err = fx2.cli(src, *argv)
        assert rc == 0, f"{argv} -> {out}{err}"
        return out
    out = ok("run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main")
    assert re.search(r"id=(\S+)", out).group(1) == RUN_A
    ok("research", "--skip", "--run", RUN_A, "--reason", "offline", "--note", "x")
    root = ["attr", "--type", "root", "--by", "SA", "--obs", fx.obs_id(1), "--item",
            "DOC=docs/06_quality/", "--root-cause", "docs/stale-note"]
    ok(*root)
    ok("attr-confirm", "--att", fx.aid(1), "--by", "QA")
    ok("attr", "--type", "link", "--by", "SA", "--from", fx.obs_id(9), "--reopens", fx.obs_id(2))
    ids = {"att": fx.aid(2)}
    ids["card"] = fx2.new_prop(src)
    ids["returned"] = fx2.new_prop(src, target=fx2.OTHER)
    pe = fx2.prop_event(src, ids["returned"])
    fx.append_events(src, [fx.ev("dec", "掌舵者", prop=ids["returned"], dkind="return",
                                 digest=pe["digest"], reason="夾具理由", reason_class="證據不足")])
    ids["frozen"] = fx2.new_prop(src, action="add")
    fx2.issue_card(src, ids["frozen"])
    rc, out, err, _, _ = fx2.decide_say(src, ids["frozen"], f"核准 {ids['frozen']}")
    assert rc == 0, out + err
    return ids


def _build_r(src: Path) -> dict:
    """`research` 專用世界：運轉 `RUN_A` 已開、尚無研究事件（其餘 A 類動詞的世界在研究之後）。"""
    rc, out, err = fx2.cli(src, "run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by",
        "main")
    assert rc == 0 and RUN_A in out, out + err
    return {}


def _build_n(src: Path) -> dict:
    """受測模組 tools/lib/selfimproving/unattended.py 的 `prop-new` 所屬運轉解析專用世界：
    運轉已研究、根因歸因已確認、尚無 PROP（每運轉新 PROP 有上限）。"""
    for argv in (["run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main"],
                 ["research", "--skip", "--run", RUN_A, "--reason", "offline", "--note", "x"],
                 ["attr", "--type", "root", "--by", "SA", "--obs", fx.obs_id(1), "--item",
                  "DOC=docs/06_quality/", "--root-cause", "docs/stale-note"],
                 ["attr-confirm", "--att", fx.aid(1), "--by", "QA"]):
        rc, out, err = fx2.cli(src, *argv)
        assert rc == 0, f"{argv} -> {out}{err}"
    return {}


def world(verb: str):
    build = {"research": ("p4r", _build_r), "prop-new": ("p4n", _build_n)}.get(
        verb, ("p4a", _build_a))
    return fx2.template(*build)


def a_calls(R: Path, ids: dict) -> dict[str, list[str]]:
    """受測模組 tools/lib/selfimproving/unattended.py：A 類八動詞的 argv（AT-438-3-1）。"""
    heldout = fx2.make_heldout(fx.new_dir("ho"), probes="exists", target=fx2.NEW_NOTE)
    revised = fx.patch_insert(fx2.OTHER, 50, ["FIXED-LINE-2"], old=fx.fixture_files()[fx2.OTHER])
    return {
        "research": ["research", "--skip", "--run", RUN_A, "--reason", "offline", "--note", "x"],
        "attr": ["attr", "--type", "root", "--by", "SA", "--obs", fx.obs_id(3), "--item",
                 "DOC=docs/06_quality/", "--root-cause", "docs/other-note"],
        "attr-confirm": ["attr-confirm", "--att", ids.get("att"), "--by", "QA"],
        "attr-reject": ["attr-reject", "--att", ids.get("att"), "--by", "QA", "--note", "x"],
        "prop-new": ["prop-new", "--run", RUN_A, *fx.good_prop_args(R, "P")],
        "prop-revise": ["prop-revise", "--run", RUN_A, "--prop", ids.get("returned"),
                        *fx.revise_args(R, "D", patch=revised)],
        "heldout-freeze": ["heldout-freeze", ids.get("frozen"), "--from", str(heldout), "--by",
        "FZ"],
        "card --issue": ["card", ids.get("card"), "--issue"],
    }


class TestUnattendedGate(P4TestCase):
    """受測模組 tools/lib/selfimproving/unattended.py 經 patrol 的行程環境：run-scoped 授權
    真值表。"""

    ENVS = {"甲": {}, "乙": {"AUTOSDD_UNATTENDED": "1"},
            "丙": {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": RUN_A},
            "丁": {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": RUN_B}}

    def run_env(self, R: Path, argv: list[str], env: dict):
        with mock.patch.dict(os.environ):
            for k in ("AUTOSDD_UNATTENDED", "AUTOSDD_SI_PATROL_RUN"):
                os.environ.pop(k, None)
            os.environ.update(env)
            return self.M(R, *argv)

    def test_AT_438_3_1_a_class_truth_table_32_cells(self):
        verbs = ("research", "attr", "attr-confirm", "attr-reject", "prop-new", "prop-revise",
                 "heldout-freeze", "card --issue")
        for verb in verbs:
            for tag, env in self.ENVS.items():
                with self.subTest(f"{verb}/{tag}"):
                    self.new_home()  # 凍結的 held-out 等住在家目錄：每格一個新家目錄
                    R, ids = world(verb)
                    argv = a_calls(R, ids)[verb] if verb != "research" else [
                        "research", "--skip", "--run", RUN_A, "--reason", "offline", "--note", "x"]
                    before = self.snap(R)
                    rc, out, err = self.run_env(R, argv, env)
                    if tag in ("甲", "丙"):
                        self.assertEqual(rc, 0, out + err)
                    else:
                        self.rejected(rc, out, {"UNATTENDED-REFUSED"}, verb)
                        self.assertEqual(self.snap(R), before)

    def test_AT_438_3_2_c_class_always_refused_readonly_unaffected(self):
        R, ids = fx2.template("p4a", _build_a)
        ref = fx2.new_uuid()
        c_calls = {
            "run-open": ["run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main"],
            "run-close": ["run-close", "--run", RUN_A, "--by", "main"],
            "obs-add": ["obs-add", "--carrier", "console", "--audit-ref", ref, "--by", "main"],
            "obs-close": ["obs-close", "--carrier", "console", "--audit-ref", ref, "--by", "main"],
            "sched set": ["sched", "set", "--enabled", "false", "--by", "main"],
            "sched arm": ["sched", "arm"], "sched disarm": ["sched", "disarm"],
            "sandbox": ["sandbox", ids["card"]], "verify": ["verify", ids["card"]],
            "promote": ["promote", ids["card"]], "rollback": ["rollback", ids["card"]],
            "measure": ["measure"], "patrol": ["patrol"],
        }
        self.assertEqual(len(c_calls), 13)
        env = self.ENVS["丙"]
        for verb, argv in c_calls.items():
            with self.subTest(verb):
                before = self.snap(R)
                rc, out, err = self.run_env(R, argv, env)
                self.rejected(rc, out, {"UNATTENDED-REFUSED"}, verb)
                self.assertEqual(self.snap(R), before)
        rc, out, _ = self.run_env(R, ["decide", ids["card"], "--kind", "approve", "--sid", fx.UUID,
                                      "--line", "1"], env)
        self.rejected(rc, out, {"UNATTENDED-REFUSED"})
        rc, out, _ = self.run_env(R, ["decide", ids["card"], "--carrier", "console", "--audit-ref",
                                      ref], env)
        self.assertEqual(rc, 1)
        self.assertNotIn("UNATTENDED-REFUSED", out)
        body = fx.fixture_files()
        plain = fx.new_dir("dry") / "body.json"
        plain.parent.mkdir(parents=True)
        plain.write_bytes(json.dumps(fx2.body_obs_add(ref), ensure_ascii=False).encode("utf-8"))
        readonly = [["check"], ["status"], ["scan"], ["card", ids["card"]],
                    ["export", "--json", "--kind", "status"], ["capacity"], ["issues"],
                    ["sched", "show"], ["obs-add", "--dry-run", "--body-file", str(plain)]]
        self.assertEqual((len(readonly), bool(body)), (9, True))
        for argv in readonly:
            with self.subTest(argv[0]):
                with mock.patch.object(runner, "run_argv", return_value=types.SimpleNamespace(
                        rc=0, out="ABSENT", err="", timed_out=False)):
                    rc, out, err = self.run_env(R, argv, env)
                self.assertEqual(rc, 0, out + err)

    def test_AT_438_3_E_1_cross_run_writes_are_still_refused(self):
        R, ids = fx2.template("p4a", _build_a)
        calls = a_calls(R, ids)
        six = ("research", "prop-new", "prop-revise", "heldout-freeze", "card --issue",
            "attr-confirm")
        for verb in six:
            with self.subTest(f"{verb}/RUN_B"):
                before = self.snap(R)
                rc, out, err = self.run_env(R, calls[verb], self.ENVS["丁"])
                self.rejected(rc, out, {"UNATTENDED-REFUSED"}, verb)
                self.assertEqual(self.snap(R), before)
            with self.subTest(f"{verb}/RUN_A"):
                rc, out, err = self.run_env(R, calls[verb], self.ENVS["丙"])
                self.assertNotIn("UNATTENDED-REFUSED", out + err, verb)

    def test_AT_438_3_E_2_env_value_edges_and_single_implementation(self):
        for label, env in {"zero": {"AUTOSDD_UNATTENDED": "0"}, "empty": {"AUTOSDD_UNATTENDED": ""},
                           "patrol-run-alone": {"AUTOSDD_SI_PATROL_RUN": RUN_B}}.items():
            with self.subTest(label):
                outs = {}
                for verb, argv_of in (
                        ("a", lambda r, i: ["research", "--skip", "--run", RUN_A, "--reason",
                                            "offline", "--note", "x"]),
                        ("c", lambda r, i: ["run-close", "--run", RUN_A, "--by", "main"])):
                    R, ids = world("research" if verb == "a" else "c")
                    outs[verb] = self.run_env(R, argv_of(R, ids), env)
                    R0, ids0 = world("research" if verb == "a" else "c")
                    base = self.run_env(R0, argv_of(R0, ids0), {})
                    if label == "zero":
                        self.rejected(outs[verb][0], outs[verb][1], {"UNATTENDED-REFUSED"})
                    else:
                        self.assertEqual(outs[verb][0], base[0])
                        self.assertEqual(re.sub(r"seq=\d+", "", outs[verb][1]),
                                         re.sub(r"seq=\d+", "", base[1]))
        reads = []
        for path in sorted(PKG.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
            for node in ast.walk(tree):
                name = node.value if isinstance(node, ast.Constant) and isinstance(
                    node.value, str) else getattr(node, "id", getattr(node, "attr", ""))
                if name not in ("AUTOSDD_UNATTENDED", "UNATTENDED_ENV"):
                    continue
                up = parent.get(node)
                is_doc = isinstance(up, ast.Expr)
                is_store = isinstance(up, ast.Subscript) and isinstance(up.ctx, ast.Store)
                if not (is_doc or is_store):
                    reads.append(path.name)
        self.assertEqual(sorted(set(reads)), ["unattended.py"], reads)

    def test_AT_438_4_1_decide_accepts_only_console_carrier(self):
        R, ids = fx2.template("p4a", _build_a)
        pe = fx2.prop_event(R, ids["card"])
        n_dec = len(evs(R, "dec"))
        ref = self.audit("decide", lambda r: fx2.body_decide(r, ids["card"], pe["digest"],
            "approve"),
                         subject=ids["card"])
        env = {"AUTOSDD_UNATTENDED": "1", "AUTOSDD_SI_PATROL_RUN": RUN_A}
        before = self.snap(R)
        rc, out, _ = self.run_env(R, ["decide", ids["card"], "--kind", "approve", "--sid", fx.UUID,
                                      "--line", "1"], env)
        self.rejected(rc, out, {"UNATTENDED-REFUSED"})
        rc, out, _ = self.run_env(R, ["decide", ids["card"], "--carrier", "console", "--audit-ref",
                                      ref], env)
        self.rejected(rc, out, {"AUDIT-KEY-MISSING"})
        self.assertEqual(self.snap(R), before)
        self.assertEqual(len(evs(R, "dec")), n_dec)  # 沒有新的 dec


class TestPatrolDoesNotDecide(P4TestCase):
    """受測模組 tools/lib/selfimproving/patrol.py：巡邏器對待決 PROP 不下決定、不推進。"""

    def test_AT_438_4_E_1_no_dec_means_no_motion(self):
        R, ids = fx2.template("p4a", _build_a)
        fx.append_events(R, [fx4.sched_set_ev(O)])
        rig = Rig()
        for when in (O + H, O + D1 + H, O + 2 * D1 + H):
            self.assertEqual(self.beat(R, when, rig)[0], 0)
        names = {tuple(a[:1]) for a in rig.verbs_log}
        for banned in ("decide", "promote", "rollback"):
            self.assertNotIn((banned,), names)
        self.assertNotIn(("sandbox",), {tuple(a[:1]) for a in rig.verbs_log if a[1] == ids["card"]})
        self.assertEqual(sum(1 for e in evs(R, "card") if e["prop"] == ids["card"]), 0)
        pend = self.status(R)["pending_props"]
        self.assertIn(ids["card"], [p["id"] for p in pend])
        self.assertEqual(next(p for p in pend if p["id"] == ids["card"])["state"], "proposed")


if __name__ == "__main__":
    sys.exit(unittest.main())
