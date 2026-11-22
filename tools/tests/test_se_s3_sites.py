#!/usr/bin/env python3
"""DES S3 非 sessionctl 站點的產品面拒絕與 job 環境（TCS-SideEffectIsolation AT-SE-07／11／14）。

受測模組：`tools/lib/engine_resume_job.py`（arm／run_job）、`tools/lib/openitems/drive.py` 與
`verbs.py`（drive／run-driver）、`tools/lib/quota_escalation.py`（通知呼叫者）、
`tools/lib/selfimproving/schedarm.py`／`patrolrun.py`、`tools/selfimproving.py`、
`tools/session_resume_planner.py`（`--claude` 別名）、`tools/lib/sched_isolation.py`。

WHY（Rule 9）：A6f 鑑定的外洩路徑＝沙盒目標呼叫了產品站點、站點照常登記排程／起 `claude`／出 toast。
每條斷言對應「拿掉那個接點就會重演」：登記首判拿掉 ⇒ 無租約的沙盒也能登記；到點首判拿掉 ⇒ 失效沙盒
的排程照跑案例；通知首判拿掉 ⇒ 驗證沙盒的撞線會敲真使用者的桌面；`--job-env` 搬運拿掉 ⇒ 排程 job 回
到真居所；正式目標路徑一旦多出任何旗標或 EndBoundary，REQ-SE-15 的「逐字不變」即破。
站點登記表與原始碼對帳（AT-SE-07）：函式真的存在且本體真的呼叫 `sched_isolation`。
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
import uuid
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "tools"))
sys.path.insert(0, str(_ROOT / "tools" / "lib"))

import endurance_env  # noqa: E402
import engine_resume_job as erj  # noqa: E402
import quota_escalation  # noqa: E402
import sandbox_scope as ss  # noqa: E402
import sched_isolation as si  # noqa: E402
import schedule_backend as sb  # noqa: E402

import session_resume_planner as planner  # noqa: E402
from lib.openitems import drive, driver_run, verbs  # noqa: E402
from lib.openitems import ledger as oi_ledger  # noqa: E402
from lib.openitems import params as oi_params  # noqa: E402
from lib.selfimproving import check as si_check  # noqa: E402
from lib.selfimproving import patrolrun, schedarm  # noqa: E402


def _load_entry():
    """`tools/selfimproving.py`（入口檔）；頂層名 `selfimproving` 會解析到 `tools/lib/` 的同名套件，
    故以檔案路徑載入。"""
    spec = importlib.util.spec_from_file_location("si_entry_under_test",
                                                  _ROOT / "tools" / "selfimproving.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


si_entry = _load_entry()
NOW = datetime.now().astimezone().replace(microsecond=0)
SRC ="docs/03_testing/contracts/TCS-WorkProgress-20261119.md:277"


@contextlib.contextmanager
def clean_env(**extra: str):
    """排程器真環境的等價物：沒有任何 AUTOSDD_*（顯式給的除外）。"""
    keep = {k: v for k, v in os.environ.items() if not k.startswith("AUTOSDD_")}
    with mock.patch.dict(os.environ, {**keep, **extra}, clear=True):
        yield


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()

    def sandbox(self, lease_min: int | None = 30) -> Path:
        home = self.tmp / f"AutoSDD_RV_sbx_{uuid.uuid4().hex[:8]}"
        (home / ".git").mkdir(parents=True)
        (home / "traces").mkdir()
        ss.write_identity(home, run_id="r1", sid="s1", owner_pid=os.getpid(), now=NOW)
        if lease_min is not None:
            ss.grant(home, until=NOW + timedelta(minutes=lease_min), now=NOW)
        return home

    @staticmethod
    def refused_rows(home: Path) -> list[dict]:
        path = home / "traces" / si.TRACE_NAME
        if not path.is_file():
            return []
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


class EngineResumeSiteTest(_Base):
    """tools/lib/engine_resume_job.py：`arm`（登記）與 `run_job`（到點）。"""

    def _arm(self, home: Path, **env: str):
        backend = SimpleNamespace(name="schtasks", disarm=mock.Mock())
        pb = home / "pb.yaml"
        pb.write_text("x: 1\n", encoding="utf-8")
        with (
            clean_env(**env),
            mock.patch.object(erj, "_REPO", home),
            mock.patch.object(sb, "select", return_value=backend),
            mock.patch.object(erj, "_refusal", return_value=""),
            mock.patch.object(erj, "_mine", return_value=[]),
            mock.patch.object(erj, "_arm_schtasks", return_value=(0, "cred")) as arm,
            mock.patch("sys.stderr"),
        ):
            rc, _ = erj.arm(str(pb), NOW + timedelta(minutes=5), cwd=str(home), now=NOW)
        return rc, arm

    def test_leaseless_sandbox_is_refused_before_the_scheduler(self) -> None:
        home = self.sandbox(lease_min=None)
        rc, arm = self._arm(home, AUTOSDD_TRACE_DIR=str(home / "traces"))
        self.assertEqual(rc, si.RC_REGISTER_REFUSED)
        arm.assert_not_called()
        trace = (home / "traces" / erj.TRACE_NAME).read_text(encoding="utf-8").splitlines()
        refused = [json.loads(x) for x in trace if '"sideeffect_refused"' in x]
        self.assertEqual(refused[0]["site"], "engine_resume_job.arm")

    def test_leased_sandbox_registers_with_expiry_and_job_env(self) -> None:
        home = self.sandbox()
        rc, arm = self._arm(home, AUTOSDD_TRACE_DIR=str(home / "traces"))
        self.assertEqual(rc, 0)
        self.assertEqual(arm.call_args.kwargs["expire_at"], ss.job_expiry(home, NOW))
        argv = arm.call_args.args[2]
        self.assertIn("--job-env", argv)
        self.assertIn(f"AUTOSDD_TRACE_DIR={home / 'traces'}", argv)

    def test_official_target_is_unchanged_no_expiry_no_job_env(self) -> None:
        rc, arm = self._arm(self.tmp)
        self.assertEqual(rc, 0)
        self.assertIsNone(arm.call_args.kwargs["expire_at"])
        self.assertNotIn("--job-env", arm.call_args.args[2])

    def test_run_job_in_a_dead_sandbox_refuses_and_disarms_itself(self) -> None:
        home = self.sandbox(lease_min=None)
        backend = SimpleNamespace(name="schtasks", disarm=mock.Mock())
        pb = home / "pb.yaml"
        pb.write_text("x: 1\n", encoding="utf-8")
        with (
            clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")),
            mock.patch.object(erj, "_REPO", home),
            mock.patch.object(sb, "select", return_value=backend),
            mock.patch.object(erj.subprocess, "run") as engine,
            mock.patch("sys.stderr"),
        ):
            rc = erj.run_job("L", str(pb), str(home), None, NOW.isoformat(timespec="seconds"))
        self.assertEqual(rc, ss.RC_SIDEEFFECT_REFUSED)
        backend.disarm.assert_called_once_with("L")
        engine.assert_not_called()


class _OpenItemsBase(_Base):
    def setUp(self) -> None:
        super().setUp()
        self.root = self.tmp / "root"
        data = json.loads((_ROOT / oi_params.PARAMS_REL).read_text(encoding="utf-8"))
        dest = self.root / oi_params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        dest.write_text(json.dumps(data), encoding="utf-8")
        self.params = oi_params.load(self.root)

    def open_item(self, root: Path | None = None) -> str:
        target = root or self.root

        def make(events):
            return [{"ev": "open", "id": oi_ledger.next_id(events, NOW), "by": "human",
                     "title": "t", "source": SRC, "scope": "r218", "kind": "auto",
                     "ts": (NOW - timedelta(hours=1)).isoformat(timespec="seconds"),
                     "check": {"realverify": "RV-L1"}}]
        return oi_ledger.append(target, make)[0]["id"]


class _Backend:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def register(self, task, at, argv, cwd, **kw):
        self.calls.append({"task": task, "argv": argv, **kw})
        return "2026/11/23 10:00:00"

    def unregister(self, task):
        return True

    def list_tasks(self, prefix):
        return {}


class OpenItemsSiteTest(_OpenItemsBase):
    """tools/lib/openitems/drive.py：drive 登記首判；verbs.py：run-driver 到點首判。"""

    def _sandbox_root(self) -> Path:
        home = self.sandbox()
        data = (self.root / oi_params.PARAMS_REL).read_bytes()
        dest = home / oi_params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        dest.write_bytes(data)
        return home

    def test_official_drive_argv_has_no_job_env_and_no_expiry(self) -> None:
        backend, item = _Backend(), self.open_item()
        with clean_env():
            drive.drive_item(self.root, self.params, item, backend=backend, now=NOW, by="human",
                             at=NOW + timedelta(hours=2))
        self.assertNotIn("--job-env", backend.calls[0]["argv"])
        self.assertNotIn("expire_at", backend.calls[0])

    def test_leaseless_sandbox_drive_is_refused_with_the_ledger_untouched(self) -> None:
        home = self.sandbox(lease_min=None)
        data = (self.root / oi_params.PARAMS_REL).read_bytes()
        dest = home / oi_params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        dest.write_bytes(data)
        item, backend = self.open_item(home), _Backend()
        before = oi_params.ledger_path(home).read_bytes()
        with clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")), mock.patch("sys.stderr"):
            with self.assertRaises(drive.DriveRefused) as caught:
                drive.drive_item(home, oi_params.load(home), item, backend=backend, now=NOW,
                                 by="human", at=NOW + timedelta(minutes=10))
        self.assertEqual(caught.exception.rc, si.RC_REGISTER_REFUSED)
        self.assertEqual(backend.calls, [], "拒絕登記 ⇒ 排程器 0 次")
        self.assertEqual(oi_params.ledger_path(home).read_bytes(), before)
        self.assertEqual(self.refused_rows(home)[0]["site"], "openitems.drive")

    def test_leased_sandbox_drive_carries_expiry_and_residence(self) -> None:
        home = self._sandbox_root()
        item, backend = self.open_item(home), _Backend()
        with clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")):
            drive.drive_item(home, oi_params.load(home), item, backend=backend, now=NOW,
                             by="human", at=NOW + timedelta(minutes=10))
        call = backend.calls[0]
        self.assertEqual(call["expire_at"], ss.job_expiry(home, NOW))
        self.assertIn(f"AUTOSDD_TRACE_DIR={home / 'traces'}", call["argv"])

    def test_drive_verb_maps_a_refusal_to_its_rc_without_the_driver_failed_text(self) -> None:
        a = Namespace(root=self.root, id="OI-x", at=None, by="human", verify=False)
        with (
            mock.patch.object(verbs.drive, "drive_item", side_effect=drive.DriveRefused(4)),
            mock.patch.object(verbs.schedcache, "select_backend", return_value=_Backend()),
            mock.patch("sys.stderr") as err,
        ):
            self.assertEqual(verbs._do_drive(a, self.params, NOW), 4)
        self.assertNotIn("驅動器沒有掛上", "".join(c.args[0] for c in err.write.call_args_list))

    def test_run_driver_in_a_dead_sandbox_never_runs_a_case_and_unregisters(self) -> None:
        home = self.sandbox(lease_min=None)
        backend = _Backend()
        backend.unregister = mock.Mock(return_value=True)
        a = Namespace(root=home, id="OI-x", task="AutoSDD_OpenItem_OI-x_1")
        with (
            clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")),
            mock.patch.object(verbs.schedcache, "select_backend", return_value=backend),
            mock.patch.object(driver_run, "run_driver") as run,
            mock.patch("sys.stderr"),
        ):
            rc = verbs._do_run_driver(a, {}, NOW)
        self.assertEqual(rc, ss.RC_SIDEEFFECT_REFUSED)
        run.assert_not_called()
        backend.unregister.assert_called_once_with(a.task)
        self.assertEqual(self.refused_rows(home)[0]["site"], "openitems.run_driver")

    def test_main_applies_job_env_before_parsing(self) -> None:
        res = self.tmp / "res"
        res.mkdir()
        with clean_env():
            rc = verbs.main(["--root", str(self.root), "--job-env", f"AUTOSDD_TRACE_DIR={res}",
                             "check"])
            self.assertIn(rc, (0, 1, 2, 3))
            self.assertEqual(os.environ.get("AUTOSDD_TRACE_DIR"), str(res))


class NotifySiteTest(_Base):
    """tools/lib/quota_escalation.py：`alert`／`patrol_housekeeping` 的通知首判。"""

    def _dead_sandbox_transcript(self) -> Path:
        path = self.tmp / "C--x-AutoSDD-RV-sbx-abc12345" / "s.jsonl"
        path.parent.mkdir()
        path.write_text("{}", encoding="utf-8")
        return path

    def test_alert_for_a_sandbox_target_neither_toasts_nor_queues(self) -> None:
        log = self.tmp / "log.jsonl"
        state = {"transcript": str(self._dead_sandbox_transcript()), "log_path": str(log),
                 "session_id": "s"}
        with (
            clean_env(AUTOSDD_TRACE_DIR=str(self.tmp)),
            mock.patch.object(quota_escalation, "notify") as toast,
            mock.patch.object(quota_escalation, "queue_notify") as queue,
            mock.patch("sys.stderr"),
        ):
            got = quota_escalation.alert("r", state, loud=True, dead_agents=2)
        self.assertEqual(got, {"sideeffect_refused": True, "notify_queued": False})
        toast.assert_not_called()
        queue.assert_not_called()
        self.assertEqual(json.loads(log.read_text("utf-8").splitlines()[0])["site"], "alert")

    def test_housekeeping_for_a_sandbox_target_does_nothing(self) -> None:
        log = self.tmp / "hk.jsonl"
        with (
            clean_env(AUTOSDD_TRACE_DIR=str(self.tmp)),
            mock.patch.object(quota_escalation, "notify") as toast,
            mock.patch.object(quota_escalation, "queue_notify") as queue,
            mock.patch.object(quota_escalation, "snapshot_fanout") as fan,
            mock.patch("sys.stderr"),
        ):
            got = quota_escalation.patrol_housekeeping(
                self._dead_sandbox_transcript(), None, NOW, {}, 600.0, "t", log)
        self.assertEqual(got, {"sideeffect_refused": True})
        for spy in (toast, queue, fan):
            spy.assert_not_called()

    def test_an_ordinary_transcript_is_not_refused(self) -> None:
        path = self.tmp / "C--proj" / "s.jsonl"
        path.parent.mkdir()
        path.write_text("{}", encoding="utf-8")
        with clean_env(AUTOSDD_TRACE_DIR=str(self.tmp)):
            self.assertFalse(si.notify_refused(_ROOT, str(path), "alert"))


class SelfImprovingSiteTest(_Base):
    """tools/lib/selfimproving/schedarm.py、patrolrun.py 與 tools/selfimproving.py。"""

    def test_arm_refuses_a_leaseless_sandbox_before_touching_the_scheduler(self) -> None:
        home = self.sandbox(lease_min=None)
        run_argv = mock.Mock()
        with clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")), mock.patch("sys.stderr"):
            rc, text = schedarm.arm(home, run_argv, as_json=False)
        self.assertNotEqual(rc, 0)
        self.assertIn("SCHED-SIDEEFFECT-REFUSED", text)
        run_argv.assert_not_called()

    def test_windows_installer_cannot_carry_job_env_so_sandbox_or_claude_is_refused(self) -> None:
        home = self.sandbox()
        with clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")):
            self.assertIn("sandbox_installer_no_job_env", si.si_arm_problem(home, os.environ,
                                                                           None, True))
            self.assertIsNone(si.si_arm_problem(home, os.environ, None, False))
        with clean_env():
            self.assertIn("claude_flag_unsupported",
                          si.si_arm_problem(self.tmp, os.environ, "x/claude", True))
            self.assertIsNone(si.si_arm_problem(self.tmp, os.environ, None, True))

    def _seed_params(self, repo: Path) -> None:
        rel = si_check.PARAMS_REL
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_bytes((_ROOT / rel).read_bytes())

    def test_mac_plist_carries_claude_and_job_env_and_official_is_bare(self) -> None:
        self._seed_params(self.tmp)
        with clean_env():
            bare = schedarm._write_plist(self.tmp, self.tmp / "plist")
            args = __import__("plistlib").loads(bare.read_bytes())["ProgramArguments"]
            self.assertEqual(args[2:5], ["patrol", "--repo", str(self.tmp)])
            self.assertEqual(len(args), 5, "正式目標且無顯式 env／--claude ⇒ argv 不多任何旗標")
        home = self.sandbox()
        self._seed_params(home)
        with clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")):
            fake = str(home / "bin" / "claude.exe")
            path = schedarm._write_plist(home, self.tmp / "plist2", claude=fake)
            args = __import__("plistlib").loads(path.read_bytes())["ProgramArguments"]
        self.assertEqual(args[args.index("--claude") + 1], fake)
        self.assertIn(f"AUTOSDD_TRACE_DIR={home / 'traces'}", args)

    def _ctx(self, repo: Path, which: str = "claude") -> SimpleNamespace:
        return SimpleNamespace(si=self.tmp, repo=repo, now=NOW, environ={}, load=lambda: [],
                               verb=mock.Mock(return_value=(0, "", "")), log=mock.Mock(),
                               spawn=mock.Mock(return_value=4242),
                               deps=SimpleNamespace(which=lambda _n: which))

    def _launch(self, ctx) -> tuple[str, str]:
        with (
            mock.patch.object(patrolrun, "task_dir", return_value=self.tmp / "task"),
            mock.patch.object(patrolrun, "_research_text", return_value=("", "", "ok")),
            mock.patch.object(patrolrun, "_scan_rows", return_value=[]),
            mock.patch.object(patrolrun, "stage_sources"),
            mock.patch.object(patrolrun, "compose", return_value="brief"),
            mock.patch.object(patrolrun, "child_env", return_value={}),
            clean_env(AUTOSDD_TRACE_DIR=str(self.tmp)),
            mock.patch("sys.stderr"),
        ):
            return patrolrun.launch(ctx, "RUN-1", trigger="t", due_at="d")

    def test_launch_never_spawns_a_real_claude_for_a_sandbox_target(self) -> None:
        home = self.sandbox()
        ctx = self._ctx(home)
        status, why = self._launch(ctx)
        self.assertEqual(status, "failed")
        self.assertIn("sideeffect-refused", why)
        ctx.spawn.assert_not_called()

    def test_launch_for_the_official_target_still_spawns(self) -> None:
        ctx = self._ctx(self.tmp)
        status, _ = self._launch(ctx)
        self.assertEqual(status, "spawned")
        ctx.spawn.assert_called_once()

    def test_patrol_entry_refuses_a_dead_sandbox_with_rc0_and_never_runs_patrol(self) -> None:
        home = self.sandbox(lease_min=None)
        args = Namespace(claude=None, now=None, dry_run=False, json=False)
        with (
            clean_env(AUTOSDD_TRACE_DIR=str(home / "traces")),
            mock.patch("lib.selfimproving.patrol.main") as patrol_main,
            mock.patch("sys.stderr"),
        ):
            self.assertEqual(si_entry._patrol(home, args), 0)
        patrol_main.assert_not_called()
        self.assertEqual(self.refused_rows(home)[0]["site"], "selfimproving.patrol")

    def test_patrol_entry_hands_the_claude_flag_to_patrol_deps(self) -> None:
        args = Namespace(claude="X/claude", now=None, dry_run=False, json=False)
        with clean_env(), mock.patch("lib.selfimproving.patrol.main", return_value=0) as pm:
            self.assertEqual(si_entry._patrol(self.tmp, args), 0)
        deps = pm.call_args.args[1]
        self.assertEqual(deps.which("claude"), "X/claude")

    def test_entry_strips_job_env_only_for_scheduled_verbs(self) -> None:
        res = self.tmp / "res"
        res.mkdir()
        pair = f"AUTOSDD_TRACE_DIR={res}"
        with clean_env():
            self.assertEqual(si_entry._apply_job_env(["patrol", "--job-env", pair, "--repo", "r"]),
                             ["patrol", "--repo", "r"])
            self.assertEqual(os.environ["AUTOSDD_TRACE_DIR"], str(res))
        with clean_env():
            untouched = ["check", "--job-env", pair]
            self.assertEqual(si_entry._apply_job_env(untouched), untouched)
            self.assertNotIn("AUTOSDD_TRACE_DIR", os.environ)
        with clean_env(), mock.patch("sys.stderr"), self.assertRaises(SystemExit) as caught:
            si_entry._apply_job_env(["sched", "--job-env", "FOO_DIR=x", "arm"])
        self.assertEqual(caught.exception.code, 2)


class PlannerClaudeFlagTest(unittest.TestCase):
    """tools/session_resume_planner.py：`--claude` 正名、`--probe-command` 同 dest 別名。"""

    def test_both_spellings_land_in_the_same_dest(self) -> None:
        parser = planner.build_parser()
        self.assertEqual(parser.parse_args(["--claude", "A"]).probe_command, "A")
        self.assertEqual(parser.parse_args(["--probe-command", "B"]).probe_command, "B")
        self.assertEqual(parser.parse_args([]).probe_command, "claude")


class SiteRegistryTest(unittest.TestCase):
    """tools/lib/sandbox_scope.py::SITES 的非 sessionctl 列與原始碼對帳（AT-SE-07）。"""

    _MINE = {"lib.engine_resume_job", "lib.openitems.drive", "lib.openitems.verbs",
             "lib.selfimproving.schedarm", "lib.selfimproving.patrolrun", "selfimproving",
             "lib.quota_escalation"}

    def test_each_registered_site_exists_and_calls_the_matching_gate(self) -> None:
        rows = [s for s in ss.SITES if s.module in self._MINE]
        self.assertEqual(len(rows), 9)
        gate_by_kind = {"register": {"register_gate", "si_arm_problem"},
                        "tick": {"tick_gate"}, "fire": {"tick_gate"},
                        "headless": {"tick_gate", "headless_refusal"},
                        "notify": {"notify_refused"}}
        for site in rows:
            path = _ROOT / "tools" / (site.module.replace(".", "/") + ".py")
            tree = ast.parse(path.read_text(encoding="utf-8"))
            func = next(n for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef) and n.name == site.function)
            calls = [n.func for n in ast.walk(func)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
            # 接收者可為 `sched_isolation`／`isolation`（別名）或 `x.sched_isolation`（屬性）
            called = {c.attr for c in calls if ast.unparse(c.value).split(".")[-1]
                      in ("sched_isolation", "isolation")}
            want = gate_by_kind[site.kind]
            self.assertTrue(called & want, f"{site} 沒有呼叫 {want}")

    def test_job_env_pairs_for_an_official_target_without_env_is_empty(self) -> None:
        with clean_env():
            self.assertEqual(si.job_env_pairs(_ROOT, os.environ), [])
            self.assertEqual(endurance_env.job_env_argv({}, sandbox=False), [])


if __name__ == "__main__":
    unittest.main()
