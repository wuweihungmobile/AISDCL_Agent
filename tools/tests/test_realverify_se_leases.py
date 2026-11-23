"""realverify 副作用租約帳的全種類、重放、abandon、發現式掃描與拒跑出口（DES
RealVerify_SideEffect_Isolation §5；
AT-SE-19／20／26／27／30／41）。

受測模組：`tools/lib/realverify/leases.py`、`leases_undo.py`、`leases_discover.py`、`sandbox.py`。
全部用假家目錄、假排程器、假行程表；真行程 smoke 另見 `tools/probe/realverify_leases_e2e.py`。
WHY：任一條退化，孤兒就會在掌舵者桌面再冒出一次（DEF-200-632 的同型）。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib import sandbox_scope  # noqa: E402
from lib.realverify import (  # noqa: E402  # noqa: E402
    leases,
    leases_discover,
    leases_undo,
    sandbox,
    sched,
)

NOW = datetime(2026, 11, 22, 12, 0, 0).astimezone()
STARTED = "2026-11-22T10:00:00+08:00"
SID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _Fake(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.alive: dict[int, tuple[bool, str | None]] = {}
        self.sched_tasks: dict[str, str] = {}
        self.procs: list[tuple[int, str, str]] = []
        self.calls: list[str] = []
        self.removed_dirs: list[str] = []

        def rm(name):
            self.calls.append(f"sched:{name}")
            self.sched_tasks.pop(name, None)

        def kill(pid):
            self.calls.append(f"kill:{pid}")
            self.procs = [p for p in self.procs if p[0] != pid]

        def git(args, cwd):
            self.calls.append("git:" + " ".join(args[:2]))
            return mock.Mock(stdout="", returncode=0)

        for target, kw in (
            (mock.patch.object(leases, "LEASE_DIR", self.tmp / "leases"), {}),
            (
                mock.patch(
                    "lib.sandbox_scope.proc_probe",
                    side_effect=lambda pid: self.alive.get(
                        pid, (False, None)
                    ),
                ),
                {},
            ),
            (mock.patch.object(sched, "remove", side_effect=rm), {}),
            (
                mock.patch.object(
                    sched,
                    "read_back",
                    side_effect=lambda n: (
                        {"s": 1} if n in self.sched_tasks else None
                    ),
                ),
                {},
            ),
            (
                mock.patch.object(
                    sched,
                    "list_rv",
                    side_effect=lambda: [
                        n
                        for n in self.sched_tasks
                        if n.startswith("AutoSDD_RV_")
                    ],
                ),
                {},
            ),
            (
                mock.patch.object(
                    sched,
                    "list_actions",
                    side_effect=lambda pattern="AutoSDD_*": dict(
                        self.sched_tasks
                    ),
                ),
                {},
            ),
            (
                mock.patch.object(
                    leases_undo,
                    "list_procs",
                    side_effect=lambda: list(self.procs),
                ),
                {},
            ),
            (
                mock.patch.object(leases_undo, "kill_pid", side_effect=kill),
                {},
            ),
            (mock.patch.object(leases_undo, "run_git", side_effect=git), {}),
        ):
            target.start()
            self.addCleanup(target.stop)

    def ours(self, name: str) -> Path:
        d = self.tmp / name
        d.mkdir()
        return d

    def put(self, run_id, kind, ident, state="made", *, pid=4242, meta=None):
        leases.append(
            run_id,
            kind,
            str(ident),
            state,
            owner_pid=pid,
            owner_started=STARTED,
            meta=meta,
        )

    def states(self, run_id):
        return [
            (r["kind"], r["ident"], r["state"])
            for r in leases.read_rows(leases.LEASE_DIR / f"{run_id}.jsonl")
        ]


class ReplayAllKindsTest(_Fake):
    """leases.replay：撤銷序 process → sched_job → worktree → 目錄；process 先驗身分（
    AT-SE-19、MU-SE-09／17）。"""

    def test_dead_owner_rows_are_revoked_in_the_documented_order(self):
        root = self.ours("AutoSDD_RV_sbx_aaaa1111")
        wt = self.ours("AutoSDD_RV_sbx_aaaa1111_wt")
        self.procs = [(900, "claude.exe", f"claude.exe -r {SID} x")]
        self.sched_tasks["AutoSDD_HandoffSpawn_aaaaaaaa_x"] = "a"
        for kind, ident, meta in (
            ("sandbox_root", root, None),
            ("worktree", wt, {"host": str(self.tmp)}),
            ("sched_job", "AutoSDD_HandoffSpawn_aaaaaaaa_x", None),
            ("process", f"sid:{SID}", {"keys": [SID, str(root)]}),
        ):
            self.put("r1", kind, ident, meta=meta)
        real_rt = sandbox._remove_tree
        with mock.patch.object(
            sandbox,
            "_remove_tree",
            side_effect=lambda p, k, **kw: (
                self.calls.append(f"rm:{k}"),
                real_rt(p, k, **kw),
            )[1],
        ):
            self.assertEqual(leases.replay(NOW), [])
        order = [
            c.split(":")[0] if not c.startswith("git") else "worktree"
            for c in self.calls
        ]
        first = {
            k: order.index(k) for k in ("kill", "sched", "worktree", "rm")
        }
        self.assertTrue(
            first["kill"] < first["sched"] < first["worktree"] < first["rm"],
            self.calls,
        )
        self.assertFalse(root.exists())
        self.assertEqual(self.states("r1")[-1], ("run", "*", "closed"))

    def test_unverifiable_process_is_not_killed_then_revoked_once_gone(
        self,
    ):
        self.alive[777] = (True, "2026-11-22T09:00:00+08:00")
        self.procs = [(777, "python.exe", "python sleeper.py")]
        self.put(
            "r1",
            "process",
            "pid:777",
            meta={
                "keys": [SID],
                "pid": 777,
                "pid_started": "2026-11-22T09:00:00+08:00",
            },
        )
        rep = leases.replay_report(NOW)
        self.assertEqual(rep.unrevoked, ["process pid:777"])
        self.assertNotIn(
            "kill:777", self.calls, "驗不到沙盒身分不得砍（MU-SE-09）"
        )
        self.assertEqual(self.states("r1")[-1][2], "unverified")
        self.assertNotIn(("run", "*", "closed"), self.states("r1"))
        self.alive.pop(777)  # 之後行程自己結束
        self.assertEqual(leases.replay_report(NOW).unrevoked, [])
        self.assertEqual(self.states("r1")[-1], ("run", "*", "closed"))

    def test_fork_session_window_is_matched_by_the_old_sid(self):
        self.procs = [
            (55, "claude.exe", f"claude.exe -r {SID} --fork-session")
        ]
        self.put("r1", "process", f"sid:{SID}", meta={"keys": [SID]})
        self.assertEqual(leases.replay(NOW), [])
        self.assertIn("kill:55", self.calls)

    def test_a_live_verified_owner_is_never_replayed_whatever_the_kind(self):
        root = self.ours("AutoSDD_RV_sbx_bbbb2222")
        self.alive[4242] = (True, STARTED)
        self.put("r1", "sandbox_root", root)
        self.assertEqual(leases.replay(NOW), [])
        self.assertTrue(root.exists())

    def test_paths_without_a_harness_prefix_are_refused_even_if_the_ledger_says_so(
        self,
    ):
        victim = self.ours("precious")
        self.put("r1", "sandbox_root", victim)
        self.assertEqual(leases.replay(NOW), [str(victim)])
        self.assertTrue(victim.exists(), "帳被改壞也不得刪到非載具前綴的路徑")

    def test_process_row_is_unique_per_kind_and_ident(self):
        self.put("r1", "process", "sid:a", "intent")
        self.put("r1", "sandbox_root", "sid:a", "made")
        self.assertEqual(
            len(
                leases._pending(
                    leases.read_rows(leases.LEASE_DIR / "r1.jsonl")
                )
            ),
            2,
        )  # noqa: SLF001


class AbandonTest(_Fake):
    """leases.abandon：只動帳，不砍行程、不刪檔、不撤排程（AT-SE-41、MU-SE-23／24）。"""

    def test_abandon_only_touches_the_ledger_and_later_replays_have_nothing_to_do(
        self,
    ):
        root = self.ours("AutoSDD_RV_sbx_cccc3333")
        self.procs = [(9, "x", f"x {SID}")]
        self.put("r1", "sandbox_root", root)
        self.put("r1", "process", f"sid:{SID}", meta={"keys": [SID]})
        self.sched_tasks["AutoSDD_RV_t"] = "a"
        self.put("r1", "sched_job", "AutoSDD_RV_t")
        with self.assertRaises(ValueError):
            leases.abandon("r1", "短")
        self.assertEqual(self.calls, [])
        gone = leases.abandon("r1", "E2E 驗人工出口")
        self.assertEqual(len(gone), 3)
        self.assertEqual(
            self.calls, [], "abandon 期間 kill／disarm／rmtree 皆 0"
        )
        self.assertTrue(root.exists())
        self.assertEqual(leases.replay(NOW), [])
        self.assertIn(
            os.path.normcase(str(root.resolve())), leases.abandoned_paths()
        )
        self.assertEqual(leases.account_state("r1", NOW), "closed")

    def test_unknown_account_is_an_error_not_a_silent_success(self):
        with self.assertRaises(FileNotFoundError):
            leases.abandon("nope", "八個字以上的理由")


class DiscoverTest(_Fake):
    """leases_discover.scan／apply：主人可驗證存活 ⇒ 不動；RVprod 依帳判（AT-SE-26、MU-SE-34）。"""

    def identity(self, home: Path, pid: int):
        sandbox_scope.write_identity(
            home, run_id="rid", sid=SID, owner_pid=pid, now=NOW
        )

    def scan(self):
        return leases_discover.scan(
            NOW,
            tmp_root=self.tmp,
            projects=self.tmp / "projects",
            sessions=self.tmp / "ses",
        )

    def test_dirs_with_a_dead_owner_are_found_a_live_owner_is_kept(self):
        dead, live = (
            self.ours("AutoSDD_RV_sbx_dead0001"),
            self.ours("AutoSDD_RV_sbx_live0002"),
        )
        self.alive[100] = (True, None)
        self.identity(dead, 99)
        self.identity(live, 100)
        names = {Path(f.ident).name for f in self.scan() if f.kind == "dir"}
        self.assertEqual(names, {dead.name})

    def test_identityless_dir_needs_to_be_older_than_lease_cap(self):
        old = self.ours("AutoSDD_RV_sbx_old00003")
        self.ours(
            "AutoSDD_RV_sbx_new00004"
        )  # 新目錄：mtime 未過 LEASE_CAP ⇒ 不該被找到
        past = datetime.now().timestamp() - (sandbox_scope.LEASE_CAP + 1) * 60
        os.utime(old, (past, past))
        names = {Path(f.ident).name for f in self.scan() if f.kind == "dir"}
        self.assertEqual(names, {old.name})

    def test_scheduled_task_with_a_sandbox_root_in_its_action(self):
        dead, live = (
            self.ours("AutoSDD_RV_sbx_dead0005"),
            self.ours("AutoSDD_RV_sbx_live0006"),
        )
        self.alive[100] = (True, None)
        self.identity(dead, 99)
        self.identity(live, 100)
        self.sched_tasks.update(
            {
                "AutoSDD_HandoffSpawn_a": f'pythonw "{dead}\\tools\\x.py"',
                "AutoSDD_Sentinel_b": f'pythonw "{live}\\tools\\x.py"',
                "AutoSDD_Sentinel_plain": r"pythonw D:\repo\tools\x.py",
            }
        )
        self.assertEqual(
            {f.ident for f in self.scan() if f.kind == "sched"},
            {"AutoSDD_HandoffSpawn_a"},
        )

    def test_rvprod_follows_the_run_account_owner(self):
        rid = [
            "20261122T100000-11-aaaaaa",
            "20261122T100000-12-bbbbbb",
            "20261122T100000-13-cccccc",
            "20261122T100000-14-dddddd",
        ]
        self.alive[11] = (True, STARTED)
        leases.append(
            rid[0],
            "temp_file",
            "x",
            "made",
            owner_pid=11,
            owner_started=STARTED,
        )
        leases.append(
            rid[1],
            "temp_file",
            "x",
            "made",
            owner_pid=12,
            owner_started=STARTED,
        )
        leases.append(
            rid[3],
            "temp_file",
            "x",
            "made",
            owner_pid=14,
            owner_started=STARTED,
        )
        leases.append(
            rid[3], "run", "*", "closed", owner_pid=14, owner_started=STARTED
        )
        for i, r in enumerate(rid):
            self.sched_tasks[f"AutoSDD_Sentinel_p{i}"] = (
                rf"pythonw C:\t\AutoSDD_RVprod_{r}\tools\x.py"
            )
        self.sched_tasks["AutoSDD_Sentinel_ok"] = r"pythonw D:\repo\x.py"
        found = {f.ident for f in self.scan() if f.kind == "sched"}
        self.assertEqual(
            found,
            {
                "AutoSDD_Sentinel_p1",
                "AutoSDD_Sentinel_p2",
                "AutoSDD_Sentinel_p3",
            },
            "主人活⇒留；主人死／帳不存在／帳 closed⇒撤；一般正式 repo 不動",
        )

    def test_abandoned_path_and_its_children_are_note_only(self):
        root = self.ours("AutoSDD_RV_sbx_aban0007")
        child = root / "tools"
        child.mkdir()
        self.put("r1", "sandbox_root", root)
        leases.abandon("r1", "放棄這個沙盒根的帳")
        with mock.patch.object(
            leases_discover,
            "_scan_dirs",
            return_value=[
                leases_discover.Finding("dir", str(root), "x"),
                leases_discover.Finding("dir", str(child), "y"),
            ],
        ):
            found = self.scan()
        self.assertEqual(
            {f.action for f in found if f.kind == "dir"}, {"note"}
        )
        with mock.patch.object(
            leases_undo, "revoke_path", return_value=(False, "locked")
        ):
            done, stuck = leases_discover.apply(found)
        self.assertEqual(
            (done, stuck), ([], {}), "abandoned 之下撤不掉：只記 note、不計入 unrevoked"
        )
        self.assertTrue(root.exists())

    def test_abandoned_leftover_is_still_disposed_once_it_can_be(self):
        """`leases_discover.apply`：DES §5.3「殘留物仍由發現式掃描在條件成立時處理」（E2E-SE-18：
        殺 P1 後 sweep 刪 X 根）。abandon 不等於永久豁免處置。"""
        root = self.ours("AutoSDD_RV_sbx_aban0008")
        self.put("r1", "sandbox_root", root)
        leases.abandon("r1", "放棄這個沙盒根的帳")
        found = [leases_discover.Finding("dir", str(root), "x", "note")]
        done, stuck = leases_discover.apply(found)
        self.assertEqual((done, stuck), ([str(root)], {}))
        self.assertFalse(root.exists())

    def test_projects_dir_of_a_vanished_sandbox_is_swept_unless_a_live_cwd_uses_it(
        self,
    ):
        projects = self.tmp / "projects"
        gone = projects / "C--T-AutoSDD-RV-sbx-gone0008"
        gone.mkdir(parents=True)
        res = sandbox.sweep_orphans(
            projects=projects,
            sessions=self.tmp / "ses",
            tmp_root=self.tmp,
            dry_run=True,
        )
        self.assertEqual(res["removed"], [gone.name])
        self.assertTrue(gone.exists(), "dry_run 不刪")


class RootLockedKeepsIdentityTest(_Fake):
    """`tools/lib/realverify/sandbox.py::_remove_tree`：根被行程 cwd 卡住而刪不掉時，身分檔須留著
    （E2E-SE-18：內容被清空、身分檔一起沒了，主人已死的孤兒就被發現式掃描誤判 live）。"""

    def _locked_rmtree(self, path, **_kw):
        for child in Path(path).iterdir():  # 模擬 Windows：內容清得掉、根因 cwd 佔用刪不掉
            child.unlink()
        raise PermissionError("WinError 32 root is the cwd of another process")

    def test_identity_survives_a_failed_root_removal_and_marks_the_owner_dead(self):
        root = self.tmp / "AutoSDD_RV_sbx_locked1"
        root.mkdir()
        sandbox_scope.write_identity(root, run_id="r1", sid=SID, owner_pid=2**22 + 7, now=NOW)
        (root / "payload.txt").write_text("x", encoding="utf-8")
        with mock.patch.object(sandbox.shutil, "rmtree", self._locked_rmtree), \
                mock.patch.object(sandbox.time, "sleep"):
            notes = sandbox._remove_tree(root, "sandbox")  # noqa: SLF001
        self.assertTrue(notes and notes[0].startswith("RESIDUE sandbox"), notes)
        self.assertFalse((root / "payload.txt").exists())
        self.assertTrue((root / sandbox_scope.IDENTITY_NAME).is_file(), "身分檔必須寫回")
        self.assertEqual(leases_discover._home_state(root, NOW), "dead")  # noqa: SLF001
        found = leases_discover.scan(NOW, tmp_root=self.tmp, projects=self.tmp / "p")
        self.assertIn(str(root), [f.ident for f in found if f.kind == "dir"])

    def test_no_identity_is_not_invented(self):
        root = self.tmp / "AutoSDD_RV_sbx_locked2"
        root.mkdir()
        (root / "payload.txt").write_text("x", encoding="utf-8")
        with mock.patch.object(sandbox.shutil, "rmtree", self._locked_rmtree), \
                mock.patch.object(sandbox.time, "sleep"):
            sandbox._remove_tree(root, "sandbox")  # noqa: SLF001
        self.assertFalse((root / sandbox_scope.IDENTITY_NAME).exists())


class AllSettledStillClosesTest(_Fake):
    """`tools/lib/realverify/leases.py::_revoke_rows`：項目都已個別結清時，案例收尾仍須補寫 closed
    （RV-SE11「本批所有帳檔都應 closed」；沒補＝帳永遠停在 revoked）。"""

    def test_revoke_run_appends_closed_when_everything_was_settled_individually(self):
        root = self.ours("AutoSDD_RV_sbx_settled1")
        self.put("r9", "sandbox_root", root)
        self.put("r9", "sandbox_root", root, "revoked")
        self.assertEqual(leases.revoke_run("r9"), [])
        rows = leases.read_rows(leases.LEASE_DIR / "r9.jsonl")
        self.assertEqual((rows[-1]["kind"], rows[-1]["state"]), ("run", "closed"))
        before = len(rows)
        leases.revoke_run("r9")
        self.assertEqual(len(leases.read_rows(leases.LEASE_DIR / "r9.jsonl")), before)


class DeadRegistryRowsTest(_Fake):
    """`tools/lib/realverify/sandbox.py::_drop_dead_registry_rows_in`：被強殺行程的 `~/.claude/sessions`
    登記檔由 cleanup 收掉（否則 RV-SE11／sessionctl_watch 的快照在 cleanup 後量到洩漏）。"""

    def _row(self, folder, pid, cwd):
        body = {"pid": pid, "sessionId": "s", "cwd": str(cwd)}
        (folder / f"{pid}.json").write_text(json.dumps(body), encoding="utf-8")

    def test_only_dead_rows_inside_the_sandbox_are_removed(self):
        folder = self.tmp / "sessions"
        folder.mkdir()
        box = self.tmp / "AutoSDD_RV_sbx_dr1"
        other = self.tmp / "AutoSDD_RV_sbx_dr1x"
        self._row(folder, 2**22 + 11, box / "wt")  # 死行程、cwd 在沙盒內 ⇒ 刪
        self._row(folder, 2**22 + 12, other)  # 死行程、別的沙盒（前綴相同）⇒ 留
        self.alive[os.getpid()] = (True, None)
        self._row(folder, os.getpid(), box)  # 活行程 ⇒ 留
        with mock.patch.object(sandbox.time, "sleep"):
            notes = sandbox._drop_dead_registry_rows_in(  # noqa: SLF001
                folder, [box], wait_s=0.0
            )
        self.assertEqual(notes, [])
        left = sorted(p.name for p in folder.glob("*.json"))
        self.assertEqual(left, sorted([f"{2**22 + 12}.json", f"{os.getpid()}.json"]))


class RefusalOutletTest(_Fake):
    """leases_discover.refusal_handback：handback 走 endurance_env 居所並依通知語意入佇列（
    REQ-SE-37）。"""

    def test_handback_lands_in_the_configured_residence_and_lists_the_abandon_command(
        self,
    ):
        hb = self.tmp / "hb"
        with (
            mock.patch.dict(os.environ, {"AUTOSDD_HANDBACK_DIR": str(hb)}),
            mock.patch("lib.quota_escalation.notify", return_value=1) as nt,
            mock.patch("lib.quota_escalation.queue_notify") as q,
        ):
            path = leases_discover.refusal_handback(
                "rid9", {"process pid:1": "驗不到身分"}, now=5.0
            )
        self.assertEqual(path, hb / "realverify_orphans_rid9.md")
        text = path.read_text(encoding="utf-8")
        self.assertIn("process pid:1", text)
        self.assertIn("sweep --abandon", text)
        nt.assert_called_once()
        q.assert_called_once()
        self.assertEqual(q.call_args.args[2:], (1, 5.0))


class LedgerFormatLockTest(unittest.TestCase):
    """leases.py 帳格式與 `sessionctl/rv_orphans.py` 的讀端常數相等（改格式就要同步，
    REQ-SE-36）。"""

    def test_reader_constants_equal_the_writer(self):
        from lib.sessionctl import rv_orphans  # noqa: PLC0415

        self.assertEqual(rv_orphans.PENDING, leases._PENDING)  # noqa: SLF001
        self.assertEqual(rv_orphans.SCHED_KIND, "sched_job")
        self.assertEqual(
            (rv_orphans.SCHED_KIND,), leases.KINDS
        )  # status 只讀排程種類（見 leases.KINDS 註解）
        self.assertEqual(
            Path.home().joinpath(*rv_orphans.LEASE_DIR_PARTS),
            leases.LEASE_DIR,
        )
        self.assertEqual(
            set(leases.UNDO_ORDER),
            set(leases.ALL_KINDS),
            "每個種類都有撤銷序",
        )

    def test_sandbox_ledger_rows_are_written_before_the_directory_exists(
        self,
    ):
        with (
            tempfile.TemporaryDirectory() as d,
            mock.patch.object(leases, "LEASE_DIR", Path(d) / "L"),
            mock.patch.object(leases_undo, "list_procs", return_value=[]),
        ):
            seen: list[list] = []
            real = Path.mkdir

            def spy(self_, *a, **k):
                if self_.name.startswith(sandbox.SANDBOX_PREFIX):
                    seen.append(
                        [
                            r["state"]
                            for r in leases.read_rows(
                                next((Path(d) / "L").glob("*.jsonl"))
                            )
                        ]
                    )
                return real(self_, *a, **k)

            with mock.patch.object(Path, "mkdir", spy):
                sb = sandbox.Sandbox.create()
            try:
                self.assertEqual(
                    seen[0].count("intent"),
                    3,
                    "sandbox_root／transcript_dir／process 三列都在 mkdir 之前",
                )
                self.assertTrue(
                    (sb.root / sandbox_scope.IDENTITY_NAME).is_file()
                )
            finally:
                self.assertEqual(sb.cleanup(), [])


if __name__ == "__main__":
    unittest.main()
