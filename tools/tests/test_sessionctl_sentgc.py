#!/usr/bin/env python3
"""WP-SW REQ-CTL-58（TCS-Control §8；AT-CTL-136～141）：舊哨兵殘骸 GC（`sentgc`）與唯讀
`job_states`。

WHY（暴露證據）：`AutoSDD_Sentinel_406454ea-…`（`NextRunTime` 空、`LastTaskResult=1`）無人 GC；
而最危險的錯拆是
把「tick 進行中、NextRunTime 為空、結果 267009 的活哨兵」拆掉——斷其喚醒鏈（與 R-4.5.6-4（b）
相反的無聲斷線）。
所以判準是四合取，且列舉在沙盒 repo 下於**列舉階段**就濾掉真實殘骸。
縫：假後端（`job_states`／`disarm` 記錄器；絕不碰真排程器——真殘骸是證據，不准拆）、假 NOW、
假任務書狀態。
"""
from __future__ import annotations

import ast
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import sandbox_scope  # noqa: E402

from lib.sessionctl import schedstates, sentgc  # noqa: E402

NOW = datetime(2026, 11, 28, 12, 0, 0).astimezone()
OLD = (NOW - timedelta(hours=2)).isoformat()
FRESH = (NOW - timedelta(minutes=3)).isoformat()
ACKER = "bbbbbbbb-1111-2222-3333-444444444444"
MIN_IDLE = 1500


def _row(sid: str, **over) -> dict:
    return {"name": f"AutoSDD_Sentinel_{sid}", "state": "Ready", "last_run": OLD, "last_result": 1,
            "next_run": "", **over}


class _Jobs:
    """假排程後端：`job_states` 回固定表（記呼叫次數）、`disarm` 記錄移除。"""

    name = "schtasks"

    def __init__(self, rows) -> None:
        self.rows, self.state_calls, self.disarmed = rows, 0, []

    def job_states(self, prefix):
        self.state_calls += 1
        return None if self.rows is None else [dict(r) for r in self.rows
            if r["name"].startswith(prefix)]

    def disarm(self, name: str) -> int:
        self.disarmed.append(name)
        return 0


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="wpsw-gc-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tmp / "traces")})
        patch.start()
        self.addCleanup(patch.stop)
        (self.tmp / "traces").mkdir()
        self.said: list[str] = []

    def sweep(self, backend, *, repo=None, plan=lambda _sid: None, **kw):
        return sentgc.sweep(ACKER, os.environ, repo_root=repo or _REPO_ROOT, min_idle_s=MIN_IDLE,
                            backend=backend, now=NOW, plan_state=plan, say=self.said.append, **kw)

    def gc_rows(self) -> list[dict]:
        import json  # noqa: PLC0415

        path = self.tmp / "traces" / "autosdd_session_switch.jsonl"
        rows = [json.loads(x)
            for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
        return [r for r in rows if r["event"] == "sentinel_gc"]


class SweepTest(_Fence):
    def test_at_ctl_136_only_the_dead_idle_residue_is_removed(self) -> None:
        """AT-CTL-136：A 拆；B NextRunTime 非空、C sid＝acker、D 結果 0＋任務書 waiting、E
        267009＋Running、
        F 剛跑完（LastRunTime < min_idle_s）、G State／LastRunTime 讀不到、H 267011 ⇒ 原樣。"""
        rows = [
            _row("aaaaaaaa-0001-4000-8000-00000000000a"),                                   # A
            _row("aaaaaaaa-0002-4000-8000-00000000000b", next_run=NOW.isoformat()),         # B
            _row(ACKER),                                                                      # C
            _row("aaaaaaaa-0004-4000-8000-00000000000d", last_result=0),                    # D
            _row("aaaaaaaa-0005-4000-8000-00000000000e", last_result=267009, state="Running"),  # E
            _row("aaaaaaaa-0006-4000-8000-00000000000f", last_run=FRESH),                   # F
            _row("aaaaaaaa-0007-4000-8000-000000000010", state=None, last_run=None),        # G
            _row("aaaaaaaa-0008-4000-8000-000000000011", last_result=267011, last_run=""),  # H
        ]
        be = _Jobs(rows)
        plan = {"aaaaaaaa-0004-4000-8000-00000000000d": "waiting"}.get
        self.assertEqual(self.sweep(be, plan=plan),
            ["AutoSDD_Sentinel_aaaaaaaa-0001-4000-8000-00000000000a"])
        self.assertEqual(be.disarmed, ["AutoSDD_Sentinel_aaaaaaaa-0001-4000-8000-00000000000a"])
        (gc,) = self.gc_rows()
        for key in ("task", "reason", "next_run", "last_result", "last_run", "state", "sid"):
            self.assertIn(key, gc)
        self.assertEqual(gc["next_run"], "")
        # D 變體：任務書 abandoned ＋ State=Ready ＋ LastRunTime 夠舊 ⇒ 也拆
        d = _row("aaaaaaaa-0004-4000-8000-00000000000d", last_result=0)
        be2 = _Jobs([d])
        self.assertEqual(len(self.sweep(be2,
            plan={d["name"].removeprefix("AutoSDD_Sentinel_"): "abandoned"}.get)), 1)

    def test_at_ctl_136_unmeasured_table_does_nothing_and_says_so(self) -> None:
        be = _Jobs(None)
        self.assertEqual(self.sweep(be), [])
        self.assertEqual(be.disarmed, [])
        self.assertTrue(any("量不到" in s for s in self.said))

    def test_at_ctl_136_launchd_style_rows_without_last_run_are_never_removed(self) -> None:
        rows = [_row("aaaaaaaa-0009-4000-8000-000000000012", state=None, last_run=None,
            last_result=None)]
        be = _Jobs(rows)
        self.assertEqual(self.sweep(be), [])
        self.assertTrue(any("LastRunTime" in s for s in self.said), "macOS：誠實出聲，不假裝清了")

    def test_at_ctl_138_cap_and_failures_never_stop_the_rest(self) -> None:
        sids = [f"aaaaaaaa-00{n:02d}-4000-8000-0000000000{n:02d}" for n in range(10, 17)]
        be = _Jobs([_row(s) for s in sids])
        self.assertEqual(len(self.sweep(be)), sentgc.SENTGC_MAX_PER_ACK)
        be = _Jobs([_row(s) for s in sids[:3]])

        def disarm(name: str) -> int:
            be.disarmed.append(name)
            if name.endswith(sids[0]):
                raise OSError("boom")
            return 0

        be.disarm = disarm
        removed = self.sweep(be)
        self.assertEqual(len(removed), 2, "第一個拋例外，其餘照處理，整體不拋")

    def test_at_ctl_139_status_is_read_only(self) -> None:
        """AT-CTL-139：`sessionctl status` 路徑（roster.render_snapshot）不碰排程器、不 GC。"""
        from lib.sessionctl import roster  # noqa: PLC0415

        be = _Jobs([_row("aaaaaaaa-0001-4000-8000-00000000000a")])
        snap = {"agents": [], "windows": [], "schedules": [], "stale_sentinels": ["x"],
            "handoffs": []}
        with mock.patch("schedule_backend.select", return_value=be):
            roster.render_snapshot(snap)
        self.assertEqual((be.state_calls, be.disarmed), (0, []))
        src = (_REPO_ROOT / "tools" / "lib" / "sessionctl"
            / "roster.py").read_text(encoding="utf-8")
        self.assertEqual([], [ln for ln in src.splitlines() if "sentgc" in ln], "GC 不得進 status")

    def test_at_ctl_136_running_or_unknown_state_is_never_a_candidate_when_dead(self) -> None:
        """MU-CTL-75：④「State≠Running」是獨立判準——tick 進行中（Running）或排程器沒回 State
        的哨兵，即使
        LastRunTime 很舊、結果非 0、NextRunTime 空白，也不得入候選（拆它＝斷活哨兵的喚醒鏈）。"""
        sid = "aaaaaaaa-0042-4000-8000-000000000042"
        for state in ("Running", None, ""):
            rows = [{**_row(sid), "sid": sid, "state": state, "last_result": 1}]
            self.assertEqual(sentgc.candidates(rows, ACKER, min_idle_s=MIN_IDLE, now=NOW,
                plan_state=lambda _s: None),
                             [], state)
        ready = [{**_row(sid), "sid": sid, "state": "Ready", "last_result": 1}]
        self.assertEqual(len(sentgc.candidates(ready, ACKER, min_idle_s=MIN_IDLE, now=NOW,
            plan_state=lambda _s: None)), 1)

    def test_at_ctl_137_removal_goes_only_through_the_existing_disarm_site(self) -> None:
        src = (_REPO_ROOT / "tools" / "lib" / "sessionctl"
            / "sentgc.py").read_text(encoding="utf-8")
        code = "\n".join(src.split('"""')[2::2])
        for banned in ("Unregister-ScheduledTask", "schtasks /delete", "launchctl bootout",
            "bootout"):
            self.assertNotIn(banned, code)
        self.assertIn("backend.disarm(", code)
        tree = ast.parse(src)
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertNotIn("subprocess", names)
        sites = (_REPO_ROOT / "tools" / "lib" / "sandbox_scope.py").read_text(encoding="utf-8")
        added = [ln for ln in sites.splitlines() if "sentgc" in ln]
        self.assertEqual([], added, "SITES 登記無新增")


class ScopeTest(_Fence):
    def _sandbox(self, sid: str) -> Path:
        home = self.tmp / "AutoSDD_RV_sbx_unit"
        home.mkdir()
        sandbox_scope.write_identity(home, run_id="r1", sid=sid, owner_pid=os.getpid(), now=NOW)
        return home

    def test_at_ctl_140_sandbox_repo_never_sees_real_residue(self) -> None:
        """AT-CTL-140：沙盒 repo ⇒ 只有 `AutoSDD_Sentinel_<S>` 與 `…-ctl` 進表；真殘骸形狀不進候選、
        不進表、sweep 零移除呼叫；非沙盒 ⇒ 全部進表；非前綴工作一律不碰。"""
        sb = "cccccccc-9999-4000-8000-0000000000cc"
        home = self._sandbox(sb)
        rows = [_row(sb), _row(f"{sb}-ctl"), _row("406454ea-91fc-4481-9c11-b28ed7d9e95f"),
                {**_row("x"), "name": "AutoSDD_HandoffSpawn_798a7bf1_202611152002"},
                {**_row("x"), "name": "AutoSDD_RV_Sentinel_x"}]
        be = _Jobs(rows)
        table = sentgc.job_table(os.environ, repo_root=home, backend=be)
        self.assertEqual(sorted(r["name"] for r in table),
                         sorted([f"AutoSDD_Sentinel_{sb}", f"AutoSDD_Sentinel_{sb}-ctl"]))
        self.assertEqual(self.sweep(be, repo=home), [f"AutoSDD_Sentinel_{sb}",
            f"AutoSDD_Sentinel_{sb}-ctl"])
        self.assertNotIn("AutoSDD_Sentinel_406454ea-91fc-4481-9c11-b28ed7d9e95f", be.disarmed)
        real = sentgc.job_table(os.environ, repo_root=_REPO_ROOT, backend=_Jobs(rows))
        self.assertIn("AutoSDD_Sentinel_406454ea-91fc-4481-9c11-b28ed7d9e95f", [r["name"]
            for r in real])
        self.assertTrue(all(r["name"].startswith("AutoSDD_Sentinel_") for r in real))

    def test_at_ctl_140_sandbox_with_unreadable_identity_scopes_to_nothing(self) -> None:
        home = self.tmp / "AutoSDD_RV_sbx_noid"
        home.mkdir()
        be = _Jobs([_row("406454ea-91fc-4481-9c11-b28ed7d9e95f")])
        self.assertEqual(sentgc.job_table(os.environ, repo_root=home, backend=be), [])
        self.assertEqual(self.sweep(be, repo=home), [])

    def test_at_ctl_141_summary_then_gc_share_one_enumeration(self) -> None:
        """AT-CTL-141：摘要先印（GC 前現況）、GC 後落 sentinel_gc；`job_states` 只被呼叫 1 次。"""
        import io  # noqa: PLC0415
        from contextlib import redirect_stdout  # noqa: PLC0415

        from lib.sessionctl import ackhook  # noqa: PLC0415

        sb = "cccccccc-9999-4000-8000-0000000000cc"
        home = self._sandbox(sb)
        pkg = self.tmp / f"{sb}_20261126T154649Z.md"
        pkg.write_text(f"# x <!-- sessionctl-handoff sid={sb} at=x -->\n", encoding="utf-8")
        pkg.with_suffix(".sealed").write_text((NOW - timedelta(days=1)).isoformat() + "\n",
            encoding="utf-8")
        be = _Jobs([_row(sb)])
        out = io.StringIO()
        with redirect_stdout(out), mock.patch("lib.sessionctl.park_cli._REPO", home), \
                mock.patch("lib.sessionctl.ackevents._default_proc", return_value=("dead", None)):
            ackhook.summarize_and_gc(pkg, ACKER, os.environ, backend=be)
        self.assertEqual(be.state_calls, 1)
        text = out.getvalue()
        self.assertIn("LastTaskResult=1", text, "摘要顯示 GC 前的舊哨兵現況")
        self.assertIn(f"AutoSDD_Sentinel_{sb}", text)
        self.assertEqual(len(self.gc_rows()), 1)


class JobStatesTest(unittest.TestCase):
    def test_parse_rows_handles_never_run_and_empty_next_run(self) -> None:
        out = ("AutoSDD_Sentinel_a\tReady\t2026-11-28T10:21:52.0000000+08:00\t1\t\n"
               "AutoSDD_Sentinel_b\tRunning\t\t267011\t2026-11-28T13:00:00.0000000+08:00\n"
               "壞行\n" "Other_x\tReady\t\t0\t\n")
        rows = schedstates.parse_rows(out, "AutoSDD_Sentinel_")
        self.assertEqual([r["name"] for r in rows], ["AutoSDD_Sentinel_a", "AutoSDD_Sentinel_b"])
        self.assertEqual((rows[0]["next_run"], rows[0]["last_result"]), ("", 1))
        self.assertEqual((rows[1]["last_run"], rows[1]["last_result"]), ("", 267011))

    def test_three_backends_expose_the_same_read_only_job_states(self) -> None:
        import schedule_backend as sb  # noqa: PLC0415

        for cls in (sb.SchtasksBackend, sb.LaunchdBackend, sb.NoCarrierBackend):
            self.assertTrue(callable(getattr(cls, "job_states", None)), cls.__name__)
        self.assertEqual(sb.NoCarrierBackend().job_states("AutoSDD_Sentinel_"), [])
        launchd = sb.LaunchdBackend()
        with mock.patch.object(launchd, "list_jobs", return_value=["AutoSDD_Sentinel_a"]):
            (row,) = launchd.job_states("AutoSDD_Sentinel_")
        self.assertEqual((row["last_run"], row["next_run"]), (None, None))
        with mock.patch.object(launchd, "list_jobs", return_value=None):
            self.assertIsNone(launchd.job_states("AutoSDD_Sentinel_"))


if __name__ == "__main__":
    unittest.main()
