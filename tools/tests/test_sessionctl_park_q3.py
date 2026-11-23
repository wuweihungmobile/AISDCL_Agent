#!/usr/bin/env python3
"""R218 QuotaWall Q3（park 備援）新模組的驗收測試（TCS-QuotaWall §1.4／§1.6；DES §7）。

受測模組：`tools/lib/sessionctl/park_yield.py`（§7.3 讓路）、`park_chain.py`（§7.4～§7.5 失敗鏈）、
`park_spawn.py`（fork 成功判準 S-20）、`park_announce.py`（失敗出聲）、
`park_takeover.py`（§7.6 哨兵接手）、
`park_register.py`／`park_status.py`（登記欄位與三列憑證）、`park.py::credential_ok`。
WHY：2026-11-20 22:42 真事件——park 到點只試一條路、失敗即靜默，主控斷線沒有人知道。
縫：FS（tmp 圍籬）、NOW（假時鐘）、SPAWN／RESUME 記錄器（絕不開真視窗）。
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import sandbox_scope  # noqa: E402
from test_sessionctl_park import NOW, SID, _CliFence, _Fence, _marker, _state  # noqa: E402

from lib.sessionctl import (  # noqa: E402
    park,
    park_announce,
    park_chain,
    park_register,
    park_status,
    park_takeover,
    park_yield,
    qw_schema,
    seal,
)

W32 = "win32"
FAKE_CLAUDE = str(Path("x") / "fake")  # 平台中性的假執行檔路徑（不寫 POSIX 絕對路徑字面值）


class _Clock:
    """假時鐘：`sleep` 把時間往前推（觀察期不真的睡）。"""

    def __init__(self) -> None:
        self.now = NOW
        self.slept: list[float] = []

    def __call__(self):
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += timedelta(seconds=seconds)


def _write_trace(fence: _Fence, event: str, **fields) -> None:
    row = {"event": event, "at": fields.pop("at", NOW.isoformat()), **fields}
    with (fence.tdir / "autosdd_session_switch.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


class CredentialPackageLiveTest(_Fence):
    """tools/lib/sessionctl/park.py::credential_ok：標記的交接包仍 live（REQ-QW-31；MU-QW-26）。"""

    def test_at_qw_39_resumed_and_acked_packages_invalidate_the_credential(self) -> None:
        pkg = self.package()
        marker = dict(_marker("H"), pkg=str(pkg))
        self.assertTrue(park.credential_ok(marker, NOW)[0])
        pkg.with_suffix(".resumed").write_text("x", encoding="utf-8")
        self.assertFalse(park.credential_ok(marker, NOW)[0])
        pkg.with_suffix(".resumed").unlink()
        pkg.with_suffix(".ack").write_text("acked t sid=other", encoding="utf-8")
        ok, why = park.credential_ok(marker, NOW)
        self.assertFalse(ok)
        self.assertIn("交接包", why)

    def test_done_markers_do_not_need_a_package(self) -> None:
        self.assertTrue(park.credential_ok(_marker("DONE", why="沒有任何剩餘的工作"), NOW)[0])


class YieldTest(_Fence):
    """tools/lib/sessionctl/park_yield.py::decide：主載具讓路四分支（REQ-QW-32；AT-QW-41／64）。"""

    def setUp(self) -> None:
        super().setUp()
        self.clock = _Clock()
        self.marker = dict(_marker("H"), pkg=str(self.package()))
        self.drivers: list = []

    def decide(self, row, live=True, marker=None):
        S = {"holder": lambda _sid: row, "holder_live": lambda _r: live, "sleep": self.clock.sleep}
        with mock.patch("transcript_activity.live_driver",
                        side_effect=lambda *_a, **_k: (
                            self.drivers.pop(0) if self.drivers else None)):
            return park_yield.decide(SID, marker or self.marker, {}, S, self.clock,
                                     lambda _sid: self.tmp / "t.jsonl")

    def row(self, wake_in_s: float) -> dict:
        extra = qw_schema.holder_extra((NOW + timedelta(seconds=wake_in_s)).timestamp(),
                                       "chain", "reset")
        return {"pid": 4242, "sid": SID, **extra}

    def test_a_alive_and_not_yet_due_reschedules_up_to_three_times(self) -> None:
        got = self.decide(self.row(300))
        self.assertEqual(got["act"], "rearm")
        self.assertEqual(got["when"], (NOW + timedelta(seconds=300 + 600)).timestamp())
        spent = dict(self.marker, **{park_yield.RESCHEDULES_KEY: park_yield.MAX_RESCHEDULES})
        again = self.decide(self.row(300), marker=spent)
        self.assertEqual((again["act"], again["reason"]), ("go", "yield_exhausted"))

    def test_b_alive_and_due_waits_for_a_driver_then_skips(self) -> None:
        self.drivers = [None, None, {"kind": "human", "timestamp": NOW.isoformat()}]
        got = self.decide(self.row(-60))
        self.assertEqual((got["act"], got["reason"]), ("skip", "primary_woke"))
        self.assertEqual(self.clock.slept, [park_yield.OBSERVE_STEP] * 2)

    def test_b_alive_and_due_without_any_driver_is_stuck_after_the_observe_window(self) -> None:
        got = self.decide(self.row(-60))
        self.assertEqual((got["act"], got["stuck"]), ("go", True))
        self.assertGreaterEqual(sum(self.clock.slept), park_yield.OBSERVE_SEC)

    def test_c_normal_release_handed_over_skips_and_other_verdicts_observe(self) -> None:
        later = (NOW + timedelta(seconds=5)).isoformat()
        _write_trace(self, "keepwarm_verdict", sid=SID, verdict="handed_over", at=later)
        got = self.decide(None)
        self.assertEqual((got["act"], got["reason"]), ("skip", "handed_over"))
        _write_trace(self, "keepwarm_verdict", sid=SID, verdict="resume", at=later)
        got = self.decide(None)
        self.assertEqual((got["act"], got["stuck"]), ("go", True))

    def test_d_dead_or_never_mounted_goes_down(self) -> None:
        self.assertEqual(self.decide(self.row(300), live=False)["act"], "go")
        self.assertEqual(self.decide(None)["reason"], "no_primary")

    def test_b_holder_vanishing_during_observation_turns_into_branch_c(self) -> None:
        rows = [self.row(-60), None]
        S = {"holder": lambda _sid: rows.pop(0) if len(rows) > 1 else None,
             "holder_live": lambda _r: True, "sleep": self.clock.sleep}
        _write_trace(self, "keepwarm_verdict", sid=SID, verdict="handed_over",
                     at=(NOW + timedelta(seconds=1)).isoformat())
        with mock.patch("transcript_activity.live_driver", return_value=None):
            got = park_yield.decide(SID, self.marker, {}, S, self.clock, lambda _s: None)
        self.assertEqual((got["act"], got["reason"]), ("skip", "handed_over"))


class ChainTest(_Fence):
    """tools/lib/sessionctl/park_chain.py::run：失敗鏈
    （REQ-QW-34／38／44；AT-QW-45／65／69③／71）。"""

    def setUp(self) -> None:
        super().setUp()
        self.pkg = self.package()
        self.calls: list = []
        self.results = {"RESUME": [0], "FRESH": [0]}
        self.gate = {"act": "go", "reason": ""}
        patch = mock.patch("lib.sessionctl.oldwin_park.resume_gate",
                           side_effect=lambda *a, **k: self.gate)
        patch.start()
        self.addCleanup(patch.stop)

    def S(self, **extra) -> dict:
        def resume(sid, pkg, **kw):
            self.calls.append(("RESUME", kw))
            return self.results["RESUME"].pop(0)

        def spawn(pkg, **kw):
            self.calls.append(("FRESH", kw))
            return self.results["FRESH"].pop(0)

        return {"platform": W32, "resume": resume, "spawn": spawn, **extra}

    def run_chain(self, first="RESUME", claude=None, **extra):
        return park_chain.run(SID, self.pkg, first, claude=claude, env={}, S=self.S(**extra),
                              clock=lambda: NOW)

    def attempts_traced(self) -> list[dict]:
        return [t for t in self.traces() if t["event"] == "park_attempt"]

    def test_at_qw_45_resume_failure_then_fresh_preflight_refusal_is_a_failed_chain(self) -> None:
        self.results["RESUME"] = [3]
        out = self.run_chain(preflight=lambda *_a, **_k: ["工作樹有 2 行未提交變更"])
        self.assertEqual(out.kind, "failed")
        self.assertEqual([(a["route"], a["attempted"], a["rc"]) for a in out.attempts],
                         [("RESUME", True, 3), ("FRESH", False, None)])
        self.assertIn("未提交變更", out.attempts[1]["reason"])
        self.assertEqual(len(self.attempts_traced()), 2)
        self.assertEqual([c[0] for c in self.calls], ["RESUME"], "前置拒絕不呼叫 FRESH spawn")

    def test_success_records_exactly_one_attempt_with_the_real_rc(self) -> None:
        out = self.run_chain()
        self.assertEqual((out.kind, out.event), ("fired", "park_resumed"))
        self.assertEqual([(t["route"], t["rc"], t["attempted"]) for t in self.attempts_traced()],
                         [("RESUME", 0, True)])

    def test_failure_writes_a_same_attempt_failure_row_so_no_handover(self) -> None:
        self.results["RESUME"], self.results["FRESH"] = [1], [1]
        self.run_chain(preflight=lambda *_a, **_k: [])
        rows = [t for t in self.traces() if t["event"] == qw_schema.EV_SPAWNING]
        self.assertEqual([(r.get("attempt"), r.get("ok")) for r in rows],
                         [(1, None), (1, False), (2, None), (2, False)])
        self.assertFalse(seal._spawned(self.pkg), "全部失敗＝沒有交棒")

    def test_plain_resume_intent_never_looks_like_a_handover(self) -> None:
        """普通 `-r` 是同 session 自續跑：意圖列不帶 handoff 欄，否則 seal 在 TTL 內
        把它判成已交棒。"""
        park_chain.write_intent(SID, self.pkg, 1, "RESUME", False)
        self.assertFalse(seal._spawned(self.pkg))
        park_chain.write_intent(SID, self.pkg, 2, "FRESH", False)
        self.assertTrue(seal._spawned(self.pkg))

    def test_at_qw_69_a_spawn_site_refusal_is_terminal_and_skips_the_other_route(self) -> None:
        self.results["RESUME"] = [sandbox_scope.RC_SIDEEFFECT_REFUSED]
        out = self.run_chain()
        self.assertEqual(out.kind, "refused")
        self.assertEqual([c[0] for c in self.calls], ["RESUME"])
        self.assertEqual([(t["reason"], t["rc"]) for t in self.attempts_traced()],
                         [("sideeffect_refused", sandbox_scope.RC_SIDEEFFECT_REFUSED)])

    def test_at_qw_65_non_windows_never_calls_a_spawn_function(self) -> None:
        out = self.run_chain(platform="darwin")
        self.assertEqual((out.kind, self.calls), ("failed", []))
        self.assertEqual([(a["attempted"], a["reason"]) for a in out.attempts],
                         [(False, "platform_unsupported")])

    def test_at_qw_71_the_claude_path_reaches_every_spawn_attempt(self) -> None:
        self.results["RESUME"] = [1]
        self.run_chain(claude=FAKE_CLAUDE, preflight=lambda *_a, **_k: [])
        self.assertEqual([c[1].get("claude") for c in self.calls], [FAKE_CLAUDE, FAKE_CLAUDE])
        self.calls.clear()
        self.results["RESUME"] = [0]
        self.gate = {"act": "fork", "reason": ""}
        self.run_chain(claude=FAKE_CLAUDE)
        self.assertEqual({k: v for k, v in self.calls[0][1].items() if k != "env"},
                         {"fork": True, "claude": FAKE_CLAUDE})
        self.calls.clear()
        self.results["RESUME"] = [0]
        self.run_chain()
        self.assertNotIn("claude", self.calls[0][1])

    def test_a_skipping_gate_returns_skipped_without_spawning(self) -> None:
        self.gate = {"act": "skip", "reason": "live_driver"}
        out = self.run_chain()
        self.assertEqual((out.kind, out.reason, self.calls), ("skipped", "live_driver", []))

    def test_attempt_numbers_continue_across_runs_of_the_same_package(self) -> None:
        self.run_chain()
        self.results["RESUME"] = [0]
        self.run_chain()
        nums = [t["attempt"] for t in self.traces() if t["event"] == qw_schema.EV_SPAWNING]
        self.assertEqual(nums, [1, 2])


class AnnounceTest(_Fence):
    """tools/lib/sessionctl/park_announce.py::announce：終局出聲（REQ-QW-35；AT-QW-46／53）。"""

    def setUp(self) -> None:
        super().setUp()
        self.pkg = self.package()
        self.attempts = [{"route": "RESUME", "attempted": True, "rc": 3, "reason": "resume_failed",
                          "fork": False}]
        self.notified: list = []

    def run_announce(self, desktop: str, env=None):
        marker = dict(_marker("H"), pkg=str(self.pkg),
                      **qw_schema.marker_extra(NOW.timestamp(), "reset", NOW.timestamp(), False,
                                               desktop or None))
        park_announce.announce(SID, self.pkg, marker, self.attempts, env=env or {},
                               notify=lambda t, b: self.notified.append(t) or 0)

    def queue_rows(self) -> list:
        import quota_escalation
        return quota_escalation._load_queue(quota_escalation.notify_queue_path())

    def test_at_qw_46_handback_queue_and_toast_follow_the_saved_preference(self) -> None:
        self.run_announce("1")
        text = (self.bdir / f"{SID}_park_failed.md").read_text(encoding="utf-8")
        for head in ("## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步指令"):
            self.assertIn(head, text)
        self.assertIn("park_chain_failed", text)
        self.assertEqual((len(self.queue_rows()), len(self.notified)), (1, 1))
        self.notified.clear()
        self.run_announce("1", env={"AUTOSDD_DESKTOP_NOTIFY": ""})  # argv 轉送的關閉值
        self.assertEqual((len(self.queue_rows()), len(self.notified)), (2, 0))

    def test_at_qw_53_empty_preference_never_toasts_but_still_queues_and_writes(self) -> None:
        self.run_announce("")
        self.assertEqual(self.notified, [])
        self.assertEqual(len(self.queue_rows()), 1)
        self.assertTrue((self.bdir / f"{SID}_park_failed.md").is_file())

    def test_notify_env_is_restored_after_the_call(self) -> None:
        before = os.environ.get("AUTOSDD_DESKTOP_NOTIFY")
        self.run_announce("1")
        self.assertEqual(os.environ.get("AUTOSDD_DESKTOP_NOTIFY"), before)


class RegisterAndStatusTest(_Fence):
    """tools/lib/sessionctl/park_register.py／park_status.py
    （REQ-QW-30／37／38；AT-QW-37／55／82）。"""

    def test_marker_fields_follow_the_registering_process_environment(self) -> None:
        fields = park_register.marker_fields(
            NOW, park_register.backup_time(NOW), at_mode=False,
            env={"AUTOSDD_PARK_CLOSE_STUCK_WINDOW": "1", "AUTOSDD_DESKTOP_NOTIFY": "1"})
        prim = qw_schema.marker_primary(fields)
        self.assertEqual((prim.source, prim.close_stuck_window, prim.desktop_notify),
                         ("reset", True, "1"))
        self.assertEqual(prim.backup_fire_at - prim.wake_at, 600)
        at_fields = park_register.marker_fields(NOW, NOW, at_mode=True, env={})
        self.assertEqual(qw_schema.marker_primary(at_fields).source, "at")

    def test_sentinel_off_never_touches_the_scheduler(self) -> None:
        touched: list = []
        S = {"jobs": lambda _p: touched.append(1) or [],
             "arm_sentinel": lambda *a: touched.append(2)}
        got = park_register.ensure_sentinel(SID, {"AUTOSDD_SENTINEL_OFF": "1"}, S)
        self.assertEqual((got, touched), (("absent", "sentinel_off"), []))

    def test_sentinel_armed_or_refused_is_reported_truthfully(self) -> None:
        listing: list = []
        S = {"jobs": lambda _p: list(listing), "arm_sentinel": lambda *a: 5}
        self.assertEqual(park_register.ensure_sentinel(SID, {}, S), ("absent", "arm_rc_5"))
        import sentinel_lifecycle
        listing.append(f"{sentinel_lifecycle.TASK_PREFIX}{SID}")
        self.assertEqual(park_register.ensure_sentinel(SID, {}, S), ("armed", ""))

    def test_verdict_lines_carry_six_fields_and_the_platform_note(self) -> None:
        lines = park_register.verdict_lines(SID, NOW, park_register.backup_time(NOW),
                                            "NextRunTime = x（排程器自報）", ("absent", "arm_rc_5"),
                                            platform_name="darwin")
        last = lines[-1]
        for needle in ("PARK_VERDICT=armed route=H backup=absent(platform)", "primary_wake_at=",
                       "backup_fire_at=", "next_run=NextRunTime = x",
                       "sentinel=absent reason=arm_rc_5"):
            self.assertIn(needle, last)

    def test_at_qw_55_status_prints_three_lines_with_absent_when_missing(self) -> None:
        pkg = self.package()
        marker = dict(_marker("H"), pkg=str(pkg))
        lines = park_status.lines(SID, marker, {"holder_row": None, "jobs": lambda _p: []},
                                  platform_name=W32)
        self.assertEqual([ln.split(":")[0] for ln in lines], ["primary", "backup", "sentinel"])
        self.assertEqual(lines[0], "primary: absent")
        self.assertTrue(lines[1].startswith("backup: next_run="))
        self.assertEqual(lines[2], "sentinel: absent")
        row = {"pid": 7, **qw_schema.holder_extra(NOW.timestamp(), "chain", "park")}
        live = park_status.primary_line(SID, row=row, live=lambda _r: True)
        self.assertIn("live pid=7", live)
        self.assertIn("mode=chain", live)
        self.assertEqual(park_status.backup_line(marker, platform_name="darwin"),
                         "backup: absent(platform)")


class TakeoverTest(_Fence):
    """tools/lib/sessionctl/park_takeover.py::on_patrol：哨兵接手（REQ-QW-36；AT-QW-48／74）。"""

    def setUp(self) -> None:
        super().setUp()
        self.pkg = self.package()
        self.log = self.tmp / "patrol.jsonl"
        self.log.write_text(json.dumps({"event": "sentinel_woken", "at": (
            NOW - timedelta(minutes=10)).isoformat()}) + "\n", encoding="utf-8")
        self.spawned: list = []
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        patches = [
            mock.patch("lib.sessionctl.park_cli._fire_route",
                       return_value=(park.FIRE_FRESH, "t", None)),
            mock.patch("lib.sessionctl.se_gate.check", return_value=None),
            mock.patch("transcript_activity.live_driver", return_value=None),
            mock.patch("lib.sessionctl.park_cli._find_transcript", return_value=None),
            mock.patch("lib.sessionctl.park_yield.decide",
                       return_value={"act": "go", "reason": "", "stuck": False, "when": None})]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.rc = 0

    def failed_marker(self, *, outcome_at=None, **extra) -> dict:
        at = (outcome_at or (NOW - timedelta(minutes=2))).isoformat()
        marker = dict(_marker("H", status="failed"), pkg=str(self.pkg),
                      outcome={"at": at, "event": "park_chain_failed", "detail": "{}",
                               "attempts": [{"route": "RESUME", "attempted": True, "rc": 3,
                                             "reason": "resume_failed", "fork": False}]}, **extra)
        self.assertTrue(park.write_marker(marker)[0])
        return marker

    def tick(self):
        S = {"platform": W32, "projects_dir": str(self.proj),
             "spawn": lambda pkg, **kw: self.spawned.append(kw) or self.rc,
             "resume": lambda *a, **kw: self.spawned.append(kw) or self.rc,
             "preflight": lambda *a, **k: [], "alive": lambda _p: False,
             "notify": lambda *a: 0}
        return park_takeover.on_patrol(SID, self.log, env=self.env, S=S, clock=lambda: NOW)

    def test_at_qw_48_a_fresh_failure_is_taken_over_once_with_the_marker_claude(self) -> None:
        self.failed_marker(claude=FAKE_CLAUDE)
        self.assertEqual(self.tick(), "fired")
        self.assertEqual(self.spawned, [{"claude": FAKE_CLAUDE}])
        self.assertEqual(park.read_marker(SID)["status"], "fired")
        self.assertEqual(self.tick(), None, "已 fired 不再動作")
        self.assertIn("sentinel_park_takeover", [t["event"] for t in self.traces()])

    def test_a_failure_older_than_the_last_patrol_or_refused_marker_is_ignored(self) -> None:
        self.failed_marker(outcome_at=NOW - timedelta(minutes=30))
        self.assertIsNone(self.tick())
        park.write_marker(dict(_marker("H", status="refused"), pkg=str(self.pkg)))
        self.assertIsNone(self.tick())
        self.assertEqual(self.spawned, [])

    def test_a_second_failure_is_final_and_announced_again(self) -> None:
        self.failed_marker()
        self.rc = 1
        with mock.patch("lib.sessionctl.park_announce.announce") as announce:
            self.assertEqual(self.tick(), "failed_final")
        announce.assert_called_once()
        self.assertEqual(park.read_marker(SID)["outcome"]["takeover"], "failed_final")

    def test_at_qw_74_expired_intent_without_a_new_transcript_fails_then_takes_over(self) -> None:
        park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
        old = (NOW - timedelta(seconds=qw_schema.SPAWN_INTENT_TTL_SEC + 30)).isoformat()
        _write_trace(self, qw_schema.EV_SPAWNING, sid=SID, handoff=str(self.pkg), route="FRESH",
                     fork=False, attempt=1, at=old)
        with mock.patch("lib.sessionctl.park_announce.announce"):
            self.assertEqual(self.tick(), "fired")
        names = [t["event"] for t in self.traces()]
        self.assertIn("park_intent_expired", names)
        self.assertEqual(len(self.spawned), 1)

    def test_at_qw_74_expired_intent_with_a_new_transcript_is_recovered(self) -> None:
        park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
        old = NOW - timedelta(seconds=qw_schema.SPAWN_INTENT_TTL_SEC + 30)
        _write_trace(self, qw_schema.EV_SPAWNING, sid=SID, handoff=str(self.pkg), route="FRESH",
                     fork=False, attempt=1, at=old.isoformat())
        fresh = self.proj / "11111111-2222-3333-4444-555555555555.jsonl"
        fresh.write_text("{}\n", encoding="utf-8")
        os.utime(fresh, (NOW.timestamp(), NOW.timestamp()))
        self.assertEqual(self.tick(), "recovered")
        self.assertEqual(self.spawned, [])
        self.assertEqual(park.read_marker(SID)["status"], "fired")
        rows = [t for t in self.traces() if t["event"] == "session_switch_spawned"]
        self.assertTrue(rows and rows[0]["ok"] is True and rows[0]["recovered"] is True)

    def test_an_intent_inside_the_ttl_is_left_alone(self) -> None:
        park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
        _write_trace(self, qw_schema.EV_SPAWNING, sid=SID, handoff=str(self.pkg), route="FRESH",
                     fork=False, attempt=1, at=(NOW - timedelta(seconds=10)).isoformat())
        self.assertIsNone(self.tick())
        self.assertEqual(self.spawned, [])

    def test_a_takeover_error_never_kills_the_patrol(self) -> None:
        self.failed_marker()
        with mock.patch("lib.sessionctl.park_takeover._chain", side_effect=RuntimeError("x")):
            self.assertIsNone(self.tick())


class RegisterCliTest(_CliFence):
    """tools/lib/sessionctl/park_cli.py::_cmd_park：QW 登記增量
    （REQ-QW-30／38；AT-QW-37／38／40／75／82）。
    WHY：標記必須記下登記當下的偏好（job 的環境帶不過去），備援排程在主載具預定醒來之後 10 分鐘。"""

    def setUp(self) -> None:
        super().setUp()
        self.sentinel_calls: list = []
        self.listed: list = []

    def sentinel_seams(self) -> dict:
        import sentinel_lifecycle

        def arm(sid, *_a):
            self.sentinel_calls.append(sid)
            self.listed.append(f"{sentinel_lifecycle.TASK_PREFIX}{sid}")
            return 0
        return {"arm_sentinel": arm, "jobs": lambda _p: list(self.listed)}

    def test_at_qw_40_the_job_fires_at_primary_wake_plus_ten_minutes(self) -> None:
        rc, _out, _err = self.run_cli(**self.sentinel_seams())
        self.assertEqual(rc, 0)
        marker = park.read_marker(SID)
        prim = qw_schema.marker_primary(marker)
        self.assertEqual((NOW.replace(hour=20, minute=2, second=0, microsecond=0)).timestamp(),
                         prim.wake_at)
        self.assertEqual(prim.backup_fire_at - prim.wake_at, 600)
        self.assertEqual(self.armed[0]["fire"].isoformat(), marker["jobs"][0]["fire_at"])
        self.assertEqual(marker["jobs"][0]["fire_at"], marker["fire_at"])
        from lib.sessionctl import park_cli  # 標籤的分鐘取排程時刻（本機時區），不寫死時區
        self.assertEqual(marker["jobs"][0]["label"], park_cli.job_label(
            SID, datetime.fromisoformat(marker["jobs"][0]["fire_at"])))

    def test_at_qw_37_last_line_has_six_fields_and_the_sentinel_is_armed(self) -> None:
        rc, out, _err = self.run_cli(**self.sentinel_seams())
        self.assertEqual(rc, 0)
        last = out.strip().splitlines()[-1]
        for key in ("PARK_VERDICT=armed route=H", "primary_wake_at=", "backup_fire_at=",
                    "next_run=NextRunTime", "sentinel=armed"):
            self.assertIn(key, last)
        self.assertEqual(self.sentinel_calls, [SID])
        self.assertIn("KEEPWARM_PLAN", out.strip().splitlines()[-2])

    def test_a_refused_sentinel_is_reported_not_hidden(self) -> None:
        rc, out, _err = self.run_cli(arm_sentinel=lambda *a: 5, jobs=lambda _p: [])
        self.assertEqual(rc, 0)
        self.assertIn("sentinel=absent reason=arm_rc_5", out.strip().splitlines()[-1])

    def test_at_qw_82_sentinel_off_never_calls_the_scheduler(self) -> None:
        seams = self.sentinel_seams()
        rc, out, _err = self.run_cli(env={"AUTOSDD_SENTINEL_OFF": "1"}, **seams)
        self.assertEqual((rc, self.sentinel_calls), (0, []))
        self.assertIn("sentinel=absent reason=sentinel_off", out.strip().splitlines()[-1])
        self.assertEqual(park.read_marker(SID)["status"], "armed")

    def test_the_marker_records_the_registering_process_preferences(self) -> None:
        self.run_cli(env={"AUTOSDD_DESKTOP_NOTIFY": "1", "AUTOSDD_PARK_CLOSE_STUCK_WINDOW": "1"},
                     **self.sentinel_seams())
        prim = qw_schema.marker_primary(park.read_marker(SID))
        self.assertEqual((prim.desktop_notify, prim.close_stuck_window, prim.source),
                         ("1", True, "reset"))

    def test_at_qw_75_at_mode_is_recorded_as_primary_source_at(self) -> None:
        at = (NOW + timedelta(minutes=30)).isoformat()
        rc, _out, _err = self.run_cli("--at", at, "--why", "週額度停工到時間再接手",
                                      **self.sentinel_seams())
        self.assertEqual(rc, 0)
        self.assertEqual(qw_schema.marker_primary(park.read_marker(SID)).source, "at")

    def test_at_qw_38_a_close_stage_below_the_prepare_threshold_is_accepted(self) -> None:
        import types
        low = lambda _n: _state(five=80.0)  # noqa: E731
        rc, _out, err = self.run_cli(quota=low, plan=lambda *a, **k: types.SimpleNamespace(
            stage="free"), **self.sentinel_seams())
        self.assertEqual(rc, 4, err)
        self.assertIsNone(park.read_marker(SID))
        rc, _out, err = self.run_cli(quota=low, plan=lambda *a, **k: types.SimpleNamespace(
            stage="close"), **self.sentinel_seams())
        self.assertEqual(rc, 0, err)
        self.assertEqual(park.read_marker(SID)["status"], "armed")

    def test_at_qw_65_non_windows_says_the_backup_is_absent_for_the_platform(self) -> None:
        rc, out, _err = self.run_cli(platform="darwin", **self.sentinel_seams())
        self.assertEqual(rc, 0)
        self.assertIn("route=H backup=absent(platform)", out.strip().splitlines()[-1])

    def test_status_prints_the_three_credential_lines(self) -> None:
        self.run_cli(**self.sentinel_seams())
        rc, out, _err = self.run_cli("--status", platform="win32",
                                     jobs=lambda _p: list(self.listed))
        self.assertEqual(rc, 0)
        lines = out.splitlines()
        self.assertTrue(any(ln.startswith("primary: ") for ln in lines))
        self.assertTrue(any(ln.startswith("backup: next_run=") for ln in lines))
        self.assertIn("sentinel: armed", lines)

class ForkSpawnSuccessTest(_Fence):
    """tools/lib/sessionctl/park_spawn.py::finish 經 park_cli.spawn_resume(fork=True)
    （REQ-QW-48；AT-QW-72；MU-QW-38）。WHY：fork 的前提是舊窗還活著、會自己寫原逐字稿——
    把「原逐字稿變大」當成功＝兩個視窗都沒起來卻報成功（零駕駛）。"""

    def setUp(self) -> None:
        super().setUp()
        self.pkg = self.package()
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        self.orig = self.proj / f"{SID}.jsonl"
        self.orig.write_text("{}\n", encoding="utf-8")
        self.argvs: list = []
        patch = mock.patch("lib.sessionctl.se_gate.check", return_value=None)
        patch.start()
        self.addCleanup(patch.stop)
        resumed = mock.patch("lib.sessionctl.seal.mark_resumed")
        self.mark_resumed = resumed.start()
        self.addCleanup(resumed.stop)

    def spawn(self, *, fork: bool, alive: bool, during=None):
        from lib.sessionctl import park_cli

        def runner(argv, **_kw):
            self.argvs.append(argv)
            return 0, "", 4242

        def sleep(_s):
            if during:
                during()

        return park_cli.spawn_resume(
            SID, self.pkg, runner=runner, platform_name=W32, fork=fork, repo=_REPO_ROOT,
            env={"AUTOSDD_SESSION_SWITCH_MODE": "auto"}, projects_dir=self.proj,
            alive=lambda _p: alive, sleep=sleep, wait_seconds=0.3)

    def grow_original(self) -> None:
        with self.orig.open("a", encoding="utf-8") as handle:
            handle.write("{}\n")

    def test_at_qw_72_only_a_new_stem_with_a_live_process_counts_for_fork(self) -> None:
        for name, during, alive in (("①原逐字稿變大", self.grow_original, True),
                                    ("④新檔但行程已死", lambda: (self.proj / "n.jsonl").write_text(
                                        "{}\n", encoding="utf-8"), False)):
            with self.subTest(case=name):
                with mock.patch("sys.stderr"):
                    self.assertNotEqual(self.spawn(fork=True, alive=alive, during=during), 0)
        self.assertEqual(self.mark_resumed.call_count, 0)
        self.assertFalse([t for t in self.traces() if t["event"] == "session_switch_spawned"])
        self.assertIn("--fork-session", self.argvs[0])

    def test_at_qw_72_a_new_uuid_transcript_is_a_handover_and_never_mark_resumed(self) -> None:
        fresh = "11111111-2222-3333-4444-555555555555"
        got = self.spawn(fork=True, alive=True, during=lambda: (self.proj / f"{fresh}.jsonl")
                         .write_text("{}\n", encoding="utf-8"))
        self.assertEqual(got, 0)
        row = [t for t in self.traces() if t["event"] == "session_switch_spawned"][0]
        self.assertEqual((row["ok"], row["new_sid"], row["route"]), (True, fresh, "fork"))
        self.assertEqual(self.mark_resumed.call_count, 0)
        self.assertEqual(str(seal.handed_over(SID)), str(self.pkg))

    def test_a_plain_resume_keeps_the_original_grew_rule_and_marks_resumed(self) -> None:
        self.assertEqual(self.spawn(fork=False, alive=True, during=self.grow_original), 0)
        self.assertNotIn("--fork-session", self.argvs[0])
        self.assertEqual(self.mark_resumed.call_count, 1)


class FireL1RefusalNeverReadsThePrimaryTest(_CliFence):
    """tools/lib/sessionctl/park_cli.py::_cmd_fire（AT-QW-69①）：L1 拒絕早於讀 holder、讓路、spawn；
    標記 `refused`、無 park_attempt／handback／佇列。"""

    def test_at_qw_69_refusal_is_terminal_and_the_holder_is_never_read(self) -> None:
        label = "AutoSDD_HandoffSpawn_798a7bf1_202611152002"
        self.backend.jobs.add(label)
        park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
        reads: list = []
        verdict = mock.Mock(reason="sandbox_no_lease")
        seams = {"backend": self.backend, "holder": lambda _s: reads.append(1) or None,
                 "spawn": lambda *a, **k: self.fail("不得 spawn"),
                 "resume": lambda *a, **k: self.fail("不得 spawn"), "platform": W32}
        with mock.patch("lib.sessionctl.se_gate.check", return_value=verdict):
            rc = self.cli.run(
                ["--session-id", SID, "--fire", "--job", label, "--pkg", str(self.pkg),
                 "--fire-at", NOW.isoformat()], env=self.env, now=NOW, seams=seams)
        self.assertEqual((rc, reads), (0, []))
        self.assertEqual(park.read_marker(SID)["status"], "refused")
        events = [t["event"] for t in self.traces()]
        self.assertFalse({"park_attempt", "park_yield_primary", "park_chain_failed"} & set(events))
        self.assertEqual(list(self.bdir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
