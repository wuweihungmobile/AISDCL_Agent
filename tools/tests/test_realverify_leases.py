"""realverify 排程租約帳（L2）單元測試：假排程器＋假主人存活縫；真排程另見
`tools/probe/realverify_leases_e2e.py`（E2E，**不算本檔**）。

WHY：DEF-200-632——代理被切斷時 `finally` 不會跑，真排程到點開幽靈 session。這裡鎖住的是「帳在動作前
就寫了」「主人死才撤、主人活不撤」「撤不掉不假裝結清」，任一條退化，孤兒排程就會再漏出去。
"""

from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib.realverify import leases, leases_discover, runner, sched  # noqa: E402

NOW = datetime(2026, 11, 21, 12, 0, 0).astimezone()
STARTED = "2026-11-21T10:00:00+08:00"


class _Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.dir = Path(self._td.name) / "leases"
        p = mock.patch.object(leases, "LEASE_DIR", self.dir)
        p.start()
        self.addCleanup(p.stop)
        self.existing: set[str] = set()  # 假排程器內「存在」的工作名
        for target, fn in (
            ("remove", lambda n: self.existing.discard(n)),
            ("read_back", lambda n: {"state": "Ready"} if n in self.existing else None),
            ("list_rv", lambda: sorted(self.existing)),
        ):
            q = mock.patch.object(sched, target, side_effect=fn)
            q.start()
            self.addCleanup(q.stop)
        self.alive: dict[int, tuple[bool, str | None]] = {}
        q = mock.patch("lib.sandbox_scope.proc_probe",
                       side_effect=lambda pid: self.alive.get(pid, (False, None)))
        q.start()
        self.addCleanup(q.stop)

    def put(self, run_id: str, ident: str, state: str, *, pid: int = 4242,
            started: str | None = STARTED, expires_at: datetime | None = None) -> None:
        leases.append(run_id, "sched_job", ident, state, owner_pid=pid, owner_started=started,
                      expires_at=expires_at)

    def rows(self, run_id: str) -> list[dict]:
        text = (self.dir / f"{run_id}.jsonl").read_text(encoding="utf-8")
        return [json.loads(x) for x in text.splitlines()]


class LedgerBeforeActionTest(_Base):
    def test_intent_is_on_disk_before_the_task_is_registered(self):
        seen: list[list[str]] = []

        def fake_register(name, at, args, **kw):
            seen.append([r["state"] for r in self.rows(leases.current_run_id())])
            self.existing.add(name)
            return {"next_run_time": "x"}

        with mock.patch.object(sched, "register_once", side_effect=fake_register):
            leases.register_once("AutoSDD_RV_t1", "2026-11-21T12:00:00", "-c pass")
        self.assertEqual(seen, [["intent"]], "動作前帳上必須已有 intent 列")
        states = [r["state"] for r in self.rows(leases.current_run_id())]
        self.assertEqual(states, ["intent", "made"])

    def test_register_failure_leaves_intent_so_replay_can_still_revoke(self):
        with mock.patch.object(sched, "register_once", side_effect=RuntimeError("boom")), \
                self.assertRaises(RuntimeError):
            leases.register_once("AutoSDD_RV_t2", "2026-11-21T12:00:00", "-c pass")
        self.existing.add("AutoSDD_RV_t2")  # 半登記：排程器其實有了
        self.assertEqual(leases.replay(NOW), [])  # 本行程 pid 沒被標活（假 proc_probe）＝死
        self.assertNotIn("AutoSDD_RV_t2", self.existing)

    def test_os_expiry_is_fire_plus_lease_max(self):
        with mock.patch.object(sched, "register_once", return_value={}) as reg:
            leases.register_once("AutoSDD_RV_t3", "2026-11-21T12:00:00", "-c pass")
        self.assertEqual(reg.call_args.kwargs["expire_at_local_iso"], "2026-11-21T12:30:00")

    def test_unknown_kind_is_refused_loudly(self):
        with self.assertRaises(ValueError):
            leases.append("r", "bogus_kind", "x", "intent")

    def test_sched_script_carries_endboundary_and_delete_expired_only_when_asked(self):
        with mock.patch.object(sched, "_ps", return_value=(0, "")) as ps, \
                mock.patch.object(sched, "read_back", return_value={"next_run_time": "x"}):
            sched.register_once("AutoSDD_RV_a", "2026-11-21T12:00:00", "-c pass",
                                expire_at_local_iso="2026-11-21T12:30:00")
            sched.register_once("AutoSDD_RV_b", "2026-11-21T12:00:00", "-c pass")
        with_exp, without = ps.call_args_list[0].args[0], ps.call_args_list[1].args[0]
        self.assertIn("EndBoundary = '2026-11-21T12:30:00'", with_exp)
        self.assertIn("DeleteExpiredTaskAfter = 'PT0S'", with_exp)
        self.assertNotIn("EndBoundary", without)
        self.assertNotIn("-Settings", without)


class ReplayOwnerTest(_Base):
    def test_dead_owner_is_orphan_and_gets_revoked_and_closed(self):
        self.put("r1", "AutoSDD_RV_x", "made")
        self.existing.add("AutoSDD_RV_x")
        self.assertEqual(leases.replay(NOW), [])
        self.assertEqual(self.existing, set())
        self.assertEqual([r["state"] for r in self.rows("r1")], ["made", "revoked", "closed"])

    def test_verified_alive_owner_is_never_revoked_even_after_expiry(self):
        self.alive[4242] = (True, STARTED)
        self.put("r1", "AutoSDD_RV_x", "made", expires_at=NOW - timedelta(hours=9))
        self.existing.add("AutoSDD_RV_x")
        self.assertEqual(leases.replay(NOW), [])
        self.assertIn("AutoSDD_RV_x", self.existing)

    def test_pid_reuse_with_different_start_time_counts_as_dead(self):
        self.alive[4242] = (True, "2026-11-21T11:59:00+08:00")
        self.put("r1", "AutoSDD_RV_x", "made")
        self.existing.add("AutoSDD_RV_x")
        leases.replay(NOW)
        self.assertEqual(self.existing, set())

    def test_unverifiable_owner_falls_back_to_expires_at(self):
        self.alive[4242] = (True, None)
        self.put("r1", "AutoSDD_RV_keep", "made", expires_at=NOW + timedelta(minutes=5))
        self.put("r2", "AutoSDD_RV_drop", "made", expires_at=NOW - timedelta(minutes=5))
        self.existing |= {"AutoSDD_RV_keep", "AutoSDD_RV_drop"}
        leases.replay(NOW)
        self.assertEqual(self.existing, {"AutoSDD_RV_keep"})

    def test_unrevokable_task_is_reported_and_account_is_not_closed(self):
        self.put("r1", "AutoSDD_RV_x", "made")
        self.existing.add("AutoSDD_RV_x")
        with mock.patch.object(sched, "remove"):  # 撤銷動作無效：回讀仍在
            self.assertEqual(leases.replay(NOW), ["AutoSDD_RV_x"])
        self.assertNotIn("closed", [r["state"] for r in self.rows("r1")])
        self.assertEqual(leases.orphan_idents(NOW), ["AutoSDD_RV_x"], "下次仍是孤兒，不會被假結清")

    def test_corrupt_line_does_not_blind_the_ledger(self):
        self.put("r1", "AutoSDD_RV_x", "made")
        with (self.dir / "r1.jsonl").open("a", encoding="utf-8") as f:
            f.write('{"truncated": \n')
        self.existing.add("AutoSDD_RV_x")
        leases.replay(NOW)
        self.assertEqual(self.existing, set())

    def test_fully_closed_old_account_is_pruned_but_pending_one_is_not(self):
        self.put("old", "AutoSDD_RV_a", "revoked")
        self.put("pend", "AutoSDD_RV_b", "made")
        self.alive[4242] = (True, STARTED)
        past = datetime.now().timestamp() - leases.PRUNE_AFTER_S - 60
        for n in ("old", "pend"):
            import os
            os.utime(self.dir / f"{n}.jsonl", (past, past))
        leases.replay(NOW)
        self.assertFalse((self.dir / "old.jsonl").exists())
        self.assertTrue((self.dir / "pend.jsonl").exists())


class DiscoverSweepTest(_Base):
    def test_unregistered_residue_is_removed_but_live_owner_account_is_kept(self):
        self.alive[4242] = (True, STARTED)
        self.put("other", "AutoSDD_RV_theirs", "made")  # 別的視窗、主人活
        self.existing |= {"AutoSDD_RV_theirs", "AutoSDD_RV_stray"}
        self.assertEqual(leases.discover_sweep(NOW), ["AutoSDD_RV_stray"])
        self.assertEqual(self.existing, {"AutoSDD_RV_theirs"})

    def test_own_run_leftover_is_reported_as_leak(self):
        self.alive[4242] = (True, STARTED)
        self.put("mine", "AutoSDD_RV_left", "made")
        self.existing.add("AutoSDD_RV_left")
        self.assertEqual(leases.discover_sweep(NOW, own_run_id="mine"), ["AutoSDD_RV_left"])

    def test_dry_run_removes_nothing(self):
        self.existing.add("AutoSDD_RV_stray")
        self.assertEqual(leases.discover_sweep(NOW, dry_run=True), ["AutoSDD_RV_stray"])
        self.assertEqual(self.existing, {"AutoSDD_RV_stray"})


class RunnerWiringTest(_Base):
    def _case(self):
        return runner.Case("RV-T-s", "t", lambda ctx: None, (), False, True)

    def test_orphan_that_cannot_be_revoked_refuses_the_whole_batch(self):
        stuck = ([], {"AutoSDD_RV_z": "stuck"})
        with mock.patch.object(leases_discover, "preflight", return_value=stuck), \
                mock.patch.object(leases_discover, "refusal_handback", return_value=None), \
                mock.patch.object(runner, "run_case") as rc:
            self.assertEqual(runner.run("t", [self._case()], write_ledger=False), 2)
        rc.assert_not_called()

    def test_leaked_task_after_batch_fails_the_run(self):
        passed = runner.Outcome("RV-T-s", "pass")
        with mock.patch.object(leases_discover, "preflight", return_value=([], {})), \
                mock.patch.object(runner, "_take", return_value=None), \
                mock.patch.object(runner, "run_case", return_value=passed), \
                mock.patch.object(sched, "sched_lock", mock.MagicMock()), \
                mock.patch.object(leases, "revoke_run", return_value=[]), \
                mock.patch.object(leases, "discover_sweep", return_value=["AutoSDD_RV_leak"]):
            self.assertEqual(runner.run("t", [self._case()], write_ledger=False), 1)

    def test_cleanup_all_rv_is_gone_and_sched_remove_lives_only_in_leases(self):
        self.assertFalse(hasattr(sched, "cleanup_all_rv"))
        for p in sorted((_TOOLS / "lib" / "realverify").rglob("*.py")):
            if p.name == "leases.py":
                continue
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                fn = node.func if isinstance(node, ast.Call) else None
                if isinstance(fn, ast.Attribute) and fn.attr == "remove" \
                        and getattr(fn.value, "id", "") == "sched":
                    self.fail(f"{p.name}:{node.lineno} 排程撤銷只准在 leases.py")


if __name__ == "__main__":
    unittest.main()
