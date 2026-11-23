#!/usr/bin/env python3
"""`tools/lib/sessionctl/park.py`／`park_cli.py` 的驗收測試（TCS-SessionPark；H 路，W 路不做）。

守的判準（WHY 全文＝ADR-XPLAT-004 §2.17）：2026-11-15 事故——短窗額度 98%、43 分鐘後 reset，
主控把「請回來說繼續」當交棒結束回合，舊視窗上下文已冷、一開口整份重寫。所以：
- 停工前必須有排程器自己回報的憑證（拿不到憑證不准宣稱已排程、不准寫標記）；
- 「快撞線」只認伺服器原值（不認攤提／配速床墊高的 band）；
- 例外一律放行（Stop fail-open），標記壞掉一律當無憑證（fail-closed）；
- job 本體先查有沒有人在動，再 spawn，且只信對話記錄、不信檔案 mtime。

縫：Q（假額度）、NOW、FS（tmp 圍籬）、ENV、ARM（假排程）、RUN（假 runner）、SPAWN。
不碰真排程器、真 `~/.claude`、真 `~/.autosdd`。
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_policy  # noqa: E402
import quota_policy_env  # noqa: E402
from test_sessionctl_handoff import FakeRoster, FakeRunner  # noqa: E402

from lib.sessionctl import converge, handoff, park  # noqa: E402

SID = "798a7bf1-a991-4a08-8ab8-d0736296f823"
NOW = datetime(2026, 11, 15, 19, 17, 15, tzinfo=UTC)
RESET = datetime(2026, 11, 15, 20, 0, 0, tzinfo=UTC)
_FULL_MAIN = "\n\n".join(f"{h}\n內容 {i}" for i, h in enumerate(handoff.SECTIONS))


def _state(five: float = 98.0, resets: str = RESET.isoformat(), week: float = 78.0,
           week_resets: str | None = None, axes=None) -> quota_policy.QuotaState:
    """夾具 INC：five_hour／session 各 `five`、seven_day＋weekly_scoped(Fable) 各 `week`。"""
    week_resets = week_resets or (NOW + timedelta(minutes=8467)).isoformat()
    built = axes if axes is not None else (
        quota_policy.Axis("five_hour", five, resets), quota_policy.Axis("session", five, resets),
        quota_policy.Axis("seven_day", week, week_resets),
        quota_policy.Axis("weekly_scoped", week, week_resets, scope_model="Fable"))
    return quota_policy.QuotaState(tuple(built), NOW.isoformat(), "test")


def _policy(prepare: float = 85.0) -> quota_policy.Policy:
    return quota_policy_env.load_policy({"AUTOSDD_QUOTA_PREPARE_PCT": str(prepare)})[0]


class RouteTest(unittest.TestCase):
    """tools/lib/sessionctl/park.py::park_route：H 路選路與拒絕條件（AT-PK-01～11；W 路各列略過）
    。"""

    def test_at_pk_02_the_incident_goes_to_h_route(self) -> None:
        """park.py：事故（reset 約 47 分後）走 H；H 是「到點換手」，不需要任何 ctx／TTL 判斷。"""
        route, reason = park.park_route(2820, unattended=False, mode="auto", carrier_ok=True)
        self.assertEqual(route, park.ROUTE_H)
        self.assertIn("新 session", reason)

    def test_at_pk_05_unattended_is_refused(self) -> None:
        """park.py：無人窗口一律拒絕（無人續跑是 planner FRESH 路的事，這裡掛排程會雙駕駛）。"""
        route, reason = park.park_route(2820, unattended=True, mode="auto", carrier_ok=True)
        self.assertEqual(route, park.ROUTE_REFUSE)
        self.assertIn("無人窗口", reason)

    def test_at_pk_06_unknown_reset_is_refused_without_assuming_five_hours(self) -> None:
        """park.py：reset 不明 ⇒ REFUSE，理由含「reset」與「不假設」（reset 只能觀測不能算）。"""
        route, reason = park.park_route(None, unattended=False, mode="auto", carrier_ok=True)
        self.assertEqual(route, park.ROUTE_REFUSE)
        self.assertIn("reset", reason)
        self.assertIn("不假設", reason)

    def test_at_pk_10_mode_and_carrier_refusals(self) -> None:
        """park.py：模式非 auto、無排程載具各自拒絕（沒有載具就沒有憑證可言）。"""
        for kwargs in ({"mode": "notify", "carrier_ok": True}, {"mode": "off", "carrier_ok": True},
                       {"mode": "auto", "carrier_ok": False}):
            with self.subTest(**kwargs):
                self.assertEqual(
                    park.park_route(60, unattended=False, **kwargs)[0], park.ROUTE_REFUSE)

    def test_at_pk_09_negative_wait_is_not_a_refusal(self) -> None:
        """park.py：觸發時刻已到（wait_s<0）視為 0，仍走 H（不得因負數誤拒）。"""
        self.assertEqual(
            park.park_route(-5, unattended=False, mode="auto", carrier_ok=True)[0], park.ROUTE_H)


class ReadingTest(unittest.TestCase):
    """tools/lib/sessionctl/park.py::prepare_hits／short_axes／reset_of：
    只認伺服器原值（AT-PK-12～20）。"""

    def test_at_pk_12_amortised_band_is_not_a_hit(self) -> None:
        """park.py：AMORT——五小時軸 23%，`decide` 因攤提把 band 墊成 prepare，但 raw 23%
        不是快撞線；
        吃 band 的實作會在此誤命中（先釘前置，夾具失效則整條無意義）。"""
        now = NOW
        state = _state(five=23.0, resets=(now + timedelta(minutes=43)).isoformat(),
                       week_resets=(now + timedelta(minutes=8467)).isoformat())
        decision = quota_policy.decide(state, now, quota_policy.DEFAULT_POLICY, 4.3, "n=84",
                                       active_model="fable")
        five = next(r for r in decision.per_axis if r.axis.kind == "five_hour")
        self.assertEqual(five.band, "prepare")  # 前置：夾具真的重現「被墊高」
        self.assertEqual(park.prepare_hits(state, quota_policy.DEFAULT_POLICY, now), [])

    def test_at_pk_13_threshold_edges_match_pct_band(self) -> None:
        """park.py：84.9／85.0／85.1 與 `pct_band` 逐格同義（不得自己再發明一把尺）。"""
        pol = _policy()
        for pct in [x / 2 for x in range(0, 201)]:
            hit = bool(park.prepare_hits(_state(five=pct), pol, NOW))
            band = quota_policy.pct_band(pct, pol) in ("prepare", "halt")
            self.assertEqual(hit, band, pct)
        self.assertEqual(park.prepare_hits(_state(five=89.9), _policy(90.0), NOW), [])
        self.assertTrue(park.prepare_hits(_state(five=90.0), _policy(90.0), NOW))

    def test_at_pk_14_17_weekly_axes_never_count(self) -> None:
        """park.py：週軸／模型分軌 99% 但短窗 10% ⇒ []（週額度停工走 --at，不走自動判準）。"""
        self.assertEqual(park.prepare_hits(_state(five=10.0, week=99.0), _policy(), NOW), [])

    def test_at_pk_15_reset_of_takes_the_latest(self) -> None:
        """park.py：兩短窗軸 reset 不同 ⇒ 取較晚者（所有達標軸都翻頁才醒）。"""
        later = (RESET + timedelta(minutes=30)).isoformat()
        state = _state(axes=(quota_policy.Axis("five_hour", 90.0, RESET.isoformat()),
                             quota_policy.Axis("session", 90.0, later)))
        hits = park.prepare_hits(state, _policy(), NOW)
        self.assertEqual(len(hits), 2)
        self.assertEqual(park.reset_of(hits), datetime.fromisoformat(later))

    def test_at_pk_16_bad_readings_are_not_hits(self) -> None:
        """park.py：NaN／inf／bool／naive／過去／None 的軸不命中；NaN 不得沿用 pct_band 的
        fail-closed。"""
        past = (NOW - timedelta(minutes=1)).isoformat()
        for pct, resets in ((float("nan"), RESET.isoformat()), (float("inf"), RESET.isoformat()),
                            (True, RESET.isoformat()), (95.0, "2026-11-15T20:00:00"),
                            (95.0, None), (95.0, past)):
            with self.subTest(pct=pct, resets=resets):
                state = _state(axes=(quota_policy.Axis("five_hour", pct, resets),))
                hits = park.prepare_hits(state, _policy(), NOW)
                self.assertEqual(hits, [])
                self.assertIsNone(park.reset_of(hits))

    def test_at_pk_18_unmeasured_is_none_not_empty(self) -> None:
        """park.py：量不到（axes==()）回 None——量不到≠量到零，呼叫端要能分辨。"""
        self.assertIsNone(park.prepare_hits(_state(axes=()), _policy(), NOW))

    def test_at_pk_19_parity_with_quota_gate(self) -> None:
        """park.py：短窗判準常數與 quota_gate 同值（兩家各算各的會漂移）。"""
        import quota_gate
        self.assertEqual(park.SHORT_WINDOW_KINDS, quota_gate._FIVE_HOUR_KINDS)
        self.assertEqual(park.SHORT_WINDOW_MINUTES, quota_gate._FIVE_HOUR_MINUTES)

    def test_at_pk_20_window_length_is_derived_not_named(self) -> None:
        """park.py：不認得的 kind 但窗長導出 300 分 ⇒ 是短窗軸；窗長 10080 的軸不是。"""
        import quota_pace
        with mock.patch.object(quota_pace, "windows", return_value=(300.0, 10080.0)):
            axes = (quota_policy.Axis("mystery", 90.0, RESET.isoformat()),
                    quota_policy.Axis("other", 90.0, RESET.isoformat()))
            self.assertEqual([a.kind for a in park.short_axes(axes)], ["mystery"])

    def test_yield_grace_matches_quiesce(self) -> None:
        """park.py：哨兵讓路寬限與 `HALT_QUIESCE_SECONDS` 同值（parity）。"""
        import quota_messages
        self.assertEqual(park.YIELD_GRACE_SECONDS, quota_messages.HALT_QUIESCE_SECONDS)


def _marker(route: str = "H", status: str = "armed", sid: str = SID, cred: str = "NextRunTime = x",
            valid: datetime | None = None, why: str | None = None) -> dict:
    valid = valid or (RESET + timedelta(seconds=120 + park.YIELD_GRACE_SECONDS))
    jobs = ([{"label": "AutoSDD_HandoffSpawn_798a7bf1_202611152002", "role": "primary",
              "fire_at": (RESET + timedelta(seconds=120)).isoformat(), "credential": cred}]
            if route == "H" else [])
    return {"schema": park.SCHEMA, "sid": sid, "route": route, "status": status,
            "parked_at": NOW.isoformat(), "reset_at": RESET.isoformat(),
            "fire_at": (RESET + timedelta(seconds=120)).isoformat(),
            "valid_until": valid.isoformat(),
            "axis": {"kind": "five_hour", "pct": 98.0}, "pkg": None, "why": why, "jobs": jobs,
            "reason": "測試", "outcome": None}


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="tw-park-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.tdir, self.hdir, self.bdir = (self.tmp / "traces", self.tmp / "handoff",
                                           self.tmp / "handback")
        for d in (self.tdir, self.hdir, self.bdir):
            d.mkdir()
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        patch = mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tdir), "AUTOSDD_HANDOFF_DIR": str(self.hdir),
            "AUTOSDD_HANDBACK_DIR": str(self.bdir)})
        patch.start()
        self.addCleanup(patch.stop)

    def traces(self) -> list[dict]:
        target = self.tdir / "autosdd_session_switch.jsonl"
        return ([json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]
                if target.exists() else [])

    def package(self, *, finalized: bool = True, sid: str = SID) -> Path:
        main = _FULL_MAIN if finalized else "\n\n".join(f"{h}\nTODO: 填" for h in handoff.SECTIONS)
        path = self.hdir / f"{sid}_20261115T191000Z.md"
        path.write_text(f"# 交接包 <!-- sessionctl-handoff sid={sid} at=x -->\n\n"
                        f"## 機械層\n\n資料\n\n{handoff.MAIN_MARK}\n\n{main}\n", encoding="utf-8")
        return path


class MarkerTest(_Fence):
    """tools/lib/sessionctl/park.py::read_marker／write_marker：標記讀寫與驗證（AT-PK-36）。"""

    def test_roundtrip_h_and_done(self) -> None:
        """park.py：H／DONE 寫後原樣讀回（讀寫兩端同一份驗證）。"""
        for marker in (_marker("H"), _marker("DONE", why="沒有任何剩餘的工作")):
            with self.subTest(route=marker["route"]):
                ok, _msg = park.write_marker(marker)
                self.assertTrue(ok)
                self.assertEqual(park.read_marker(SID), marker)

    def test_invalid_markers_read_as_none_and_are_refused_on_write(self) -> None:
        """park.py：schema 錯／naive 時間／DONE 的 why 7 字／sid 含 `../` ⇒ 讀回 None、寫入被拒
        （拒寫勝過寫一份讀不回來的標記）。"""
        bad = [dict(_marker(), schema="x"), dict(_marker(), parked_at="2026-11-15T19:00:00"),
               _marker("DONE", why="七個字的原因啊"), dict(_marker(), sid="../evil"),
               dict(_marker(), route="W")]
        for marker in bad:
            with self.subTest(marker=marker.get("schema"), sid=marker["sid"]):
                self.assertFalse(park.write_marker(marker)[0])
        path = park.marker_path(SID, write=True)
        for text in ("{not json", json.dumps(dict(_marker(), schema="x")), ""):
            path.write_text(text, encoding="utf-8")
            self.assertIsNone(park.read_marker(SID))
        self.assertIsNone(park.marker_path("../evil"))

    def test_reading_creates_nothing(self) -> None:
        """park.py：讀取端不建目錄（Stop 熱路徑不得憑空長出痕跡目錄）。"""
        ghost = self.tmp / "ghost"
        with mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(ghost)}):
            self.assertIsNone(park.read_marker(SID))
        self.assertFalse(ghost.exists())


class StopVerdictTest(_Fence):
    """tools/lib/sessionctl/park.py::stop_verdict：Stop 推回判準（AT-PK-21～34；W 列略過）。"""

    def verdict(self, *, five: float = 98.0, env=None, payload=None, **seams) -> str:
        payload = payload if payload is not None else {"session_id": SID,
                                                       "hook_event_name": "Stop"}
        seams.setdefault("read_quota", lambda _n: _state(five=five))
        seams.setdefault("policy_fn", _policy)
        seams.setdefault("carrier_fn", lambda: True)
        seams.setdefault("spawned_fn", lambda _s, _e: False)
        return park.stop_verdict(payload, env if env is not None else {}, now=NOW, **seams)

    def test_at_pk_21_incident_without_marker_is_pushed_back(self) -> None:
        """park.py：事故回放（98%、43 分後 reset、無標記）⇒ 推回，給 park 與 --done 兩個出口，
        且不叫人回舊視窗。"""
        text = self.verdict()
        for needle in ("python tools/sessionctl.py park", "park --done --why", "pp",
                       "沒有任何續航憑證"):
            self.assertIn(needle, text)
        self.assertNotIn("%", text)
        self.assertNotIn("在這個視窗說一聲", text)
        self.assertEqual([t["event"] for t in self.traces()], ["park_stop_block"])

    def test_at_pk_21b_total_entry_via_converge(self) -> None:
        """tools/lib/sessionctl/converge.py：總入口 `stop_verdict` 在收斂閘不成立時落到 park
        判準。"""
        # QuotaWall Q4：總入口先問 `quotawall.plan`；額度量不到（stage none）才落到既有 park 判準
        # （S-16）。這裡把額度讀數圍成「量不到」，不讀真實額度。
        with (mock.patch("lib.sessionctl.qw_wall.default_read", return_value=None),
              mock.patch.object(park, "stop_verdict", return_value="PARK-REASON") as fake):
            self.assertEqual(converge.stop_verdict({"session_id": SID}, {}), "PARK-REASON")
            fake.assert_called_once()

    def test_at_pk_22_valid_h_marker_passes(self) -> None:
        """park.py：有效 H 標記（憑證非空、未過期）⇒ 放行。"""
        park.write_marker(_marker("H"))
        self.assertEqual(self.verdict(), "")

    def test_at_pk_24_done_marker_validity(self) -> None:
        """park.py：DONE 有效期內放行；過期推回；為何 7 字的手寫標記無效（讀取端同寫入端下限）。"""
        park.write_marker(_marker("DONE", why="沒有任何剩餘的工作"))
        self.assertEqual(self.verdict(), "")
        expired = _marker("DONE", why="沒有任何剩餘的工作", valid=NOW - timedelta(seconds=1))
        park.write_marker(expired)
        self.assertNotEqual(self.verdict(), "")
        path = park.marker_path(SID, write=True)
        path.write_text(json.dumps(_marker("DONE", why="七個字的原因啊")), encoding="utf-8")
        self.assertNotEqual(self.verdict(), "")

    def test_at_pk_25_low_quota_is_not_pushed_back(self) -> None:
        """park.py：額度 72%（收斂帶）不推回（負控；本守衛只管「快撞線」）。"""
        self.assertEqual(self.verdict(five=72.0), "")

    def test_at_pk_26_stop_hook_active_passes(self) -> None:
        """park.py：第二次 Stop（stop_hook_active）一律放行，否則會無限迴圈。"""
        self.assertEqual(self.verdict(payload={"session_id": SID, "stop_hook_active": True}), "")

    def test_at_pk_27_unattended_does_not_even_read_quota(self) -> None:
        """park.py：無人窗口回 ""，且不讀額度、不讀標記（前一步不成立就不做後面的 I/O）。"""
        calls = []
        text = self.verdict(env={"AUTOSDD_UNATTENDED": "1"},
                            read_quota=lambda n: calls.append(n) or _state())
        self.assertEqual(text, "")
        self.assertEqual(calls, [])

    def test_at_pk_28_escape_hatches(self) -> None:
        """park.py：GUARD_OFF／模式 notify／off／無載具各自放行（park 在這些情境本來就會 rc 4）。"""
        for env in ({park.GUARD_OFF_ENV: "1"}, {"AUTOSDD_SESSION_SWITCH_MODE": "notify"},
                    {"AUTOSDD_SESSION_SWITCH_MODE": "off"}):
            with self.subTest(env=env):
                self.assertEqual(self.verdict(env=env), "")
        self.assertEqual(self.verdict(carrier_fn=lambda: False), "")

    def test_at_pk_29_unknown_reset_is_not_pushed_back(self) -> None:
        """park.py：reset 缺／naive／已過 ⇒ 不推回（推回了也沒法 park）。"""
        for resets in (None, "2026-11-15T20:00:00", (NOW - timedelta(minutes=1)).isoformat()):
            with self.subTest(resets=resets):
                state = _state(axes=(quota_policy.Axis("five_hour", 98.0, resets),))
                self.assertEqual(self.verdict(read_quota=lambda _n, s=state: s), "")

    def test_at_pk_18b_unmeasured_is_traced(self) -> None:
        """park.py：量不到不推回，但落 `park_verdict_unmeasured`（失效可偵測，不靜默）。"""
        self.assertEqual(self.verdict(read_quota=lambda _n: _state(axes=())), "")
        self.assertEqual([t["event"] for t in self.traces()], ["park_verdict_unmeasured"])

    def test_at_pk_30_non_credentials_are_pushed_back(self) -> None:
        """park.py：fired／cancelled／failed／skipped、sid 不符、過 valid_until、空憑證、壞 JSON ⇒
        都不算憑證。"""
        for status in ("fired", "cancelled", "failed", "skipped"):
            park.write_marker(_marker(status=status))
            self.assertNotEqual(self.verdict(), "", status)
        park.write_marker(_marker(valid=NOW - timedelta(seconds=1)))
        self.assertNotEqual(self.verdict(), "")
        park.write_marker(_marker(cred="  "))
        self.assertNotEqual(self.verdict(), "")
        park.marker_path(SID, write=True).write_text("{壞", encoding="utf-8")
        self.assertNotEqual(self.verdict(), "")

    def test_at_pk_31_any_exception_fails_open(self) -> None:
        """park.py：額度讀取拋例外／payload 非 dict ⇒ ""（P0：守衛自己壞掉不得卡住使用者）。"""
        def boom(_n):
            raise RuntimeError("x")
        self.assertEqual(self.verdict(read_quota=boom), "")
        self.assertEqual(self.verdict(payload="not-a-dict"), "")

    def test_at_pk_33_spawned_package_is_not_pushed_back(self) -> None:
        """park.py：交接包已 `--spawn`（換 session 路徑已處理）⇒ 不推回。"""
        self.assertEqual(self.verdict(spawned_fn=lambda _s, _e: True), "")

    def test_handed_off_reads_the_spawn_trace(self) -> None:
        """park.py::handed_off：只認 `session_switch_spawned ∧ sid ∧ ok=True` 且在 TTL 內的痕跡。"""
        target = self.tdir / "autosdd_session_switch.jsonl"
        now = datetime.now().astimezone()
        stamp = now.isoformat()
        base = {"event": "session_switch_spawned", "at": stamp}
        rows = [{**base, "sid": SID, "ok": False}, {**base, "sid": "other", "ok": True}]
        target.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        self.assertFalse(park.handed_off(SID, self.env))
        rows.append({**base, "sid": SID, "ok": True})
        target.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        self.assertTrue(park.handed_off(SID, self.env))

    def test_yields_only_for_armed_h_inside_window(self) -> None:
        """park.py::yields：armed ∧ H ∧ 窗內才讓路；DONE／過期／非 armed 不讓（哨兵照原判準）。"""
        self.assertTrue(park.yields(_marker("H"), NOW))
        self.assertFalse(park.yields(_marker("DONE", why="沒有任何剩餘的工作"), NOW))
        self.assertFalse(park.yields(_marker("H", status="fired"), NOW))
        self.assertFalse(park.yields(_marker("H"), RESET + timedelta(hours=2)))
        self.assertFalse(park.yields(None, NOW))


#: AT-PK-83 黃金字串：`_arm_schtasks(interactive=False)` 在本次修改**之前**以假 planner 現跑凍成。
_GOLDEN_SCHTASKS = (
    "$ErrorActionPreference = 'Stop'\n"
    "$action = New-ScheduledTaskAction -Execute 'py/pythonw.exe' "
    "-Argument '\"a.py\" \"b c\"' -WorkingDirectory 'repo'\n"
    "$trigger = New-ScheduledTaskTrigger -Once -At '2026-11-16 04:02:00'\n"
    "$settings = SETTINGS-SENTINEL\n$principal = PRINCIPAL-SENTINEL\n"
    "$common = @{TaskName='LBL'; Action=$action; Trigger=$trigger; Settings=$settings; "
    "Force=$true}\n"
    "try { Register-ScheduledTask @common -Principal $principal -EA Stop | Out-Null }\n"
    "catch { Register-ScheduledTask @common | Out-Null; "
    "Write-Output 'PRINCIPAL-FALLBACK=default-interactive' }\n\nEVIDENCE LBL\n")


class _FakePlanner:
    """假 planner：截取 `_arm_schtasks` 組出的 PowerShell 腳本（不碰真排程器）。"""

    _SCHTASKS_SETTINGS = "SETTINGS-SENTINEL"
    _SCHTASKS_PRINCIPAL = "PRINCIPAL-SENTINEL"
    _EVIDENCE_TEMPLATE = "EVIDENCE {task}"

    def __init__(self, moment: str = "2026-11-16 04:02:00") -> None:
        self.scripts: list[str] = []
        self.moment = moment

    @staticmethod
    def _ps_single_quote(text: str) -> str:
        return text.replace("'", "''")

    def next_run_time(self, _out: str) -> str:
        return self.moment

    def run_powershell(self, script: str):
        self.scripts.append(script)
        return mock.Mock(stdout="NextRunTime = x\n", stderr="", returncode=0)


class EngineOneshotTest(unittest.TestCase):
    """tools/lib/engine_resume_job.py：`_arm_schtasks(interactive)`／`arm_oneshot`（AT-PK-82～84）。
    WHY：S4U 落 session 0，開不出使用者看得見的視窗；park 的新 session 必須用 Interactive。"""

    FIRE = datetime(2026, 11, 16, 4, 2, tzinfo=UTC)

    def _arm(self, planner, **kw):
        import engine_resume_job as erj
        with mock.patch.object(erj.win_spawn, "quiet_python", return_value="py/pythonw.exe"), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return erj._arm_schtasks(planner, "LBL", ["pyw", "a.py", "b c"], "repo",
                                     self.FIRE, **kw)

    def test_at_pk_82_interactive_script_has_no_s4u_and_no_fallback(self) -> None:
        """engine_resume_job.py：interactive 腳本含 Interactive，不含
        S4U／PRINCIPAL-FALLBACK（不得悄悄退回 S4U）。"""
        planner = _FakePlanner()
        self.assertEqual(self._arm(planner, interactive=True)[0], 0)
        script = planner.scripts[0]
        self.assertIn("-LogonType Interactive", script)
        self.assertNotIn("S4U", script)
        self.assertNotIn("PRINCIPAL-FALLBACK", script)
        self.assertIn("SETTINGS-SENTINEL", script)  # 設定（四項）仍來自 planner 單一來源
        self.assertEqual(self._arm(_FakePlanner(moment=""), interactive=True), (1, ""))

    def test_at_pk_83_default_script_is_byte_identical_to_the_pre_change_script(self) -> None:
        """engine_resume_job.py：interactive=False（引擎續跑用）腳本與修前逐位元組相同（黃金字串）
        。"""
        planner = _FakePlanner()
        self._arm(planner)
        self.assertEqual(planner.scripts[0], _GOLDEN_SCHTASKS)

    def test_at_pk_84_arm_oneshot_without_carrier_is_refused(self) -> None:
        """engine_resume_job.py：載具為 none／planner 不可達 ⇒ (1, "") 並說明；launchd 委派既有
        `_arm_launchd`。"""
        import engine_resume_job as erj
        none = mock.Mock()
        none.name = "none"
        with mock.patch.object(erj.sb, "select", return_value=none), \
                mock.patch.object(erj.sb, "_planner", return_value=_FakePlanner()), \
                redirect_stderr(io.StringIO()) as err:
            self.assertEqual(erj.arm_oneshot("L", ["x"], ".", self.FIRE), (1, ""))
        self.assertIn("沒有已實作的排程載具", err.getvalue())
        lau = mock.Mock()
        lau.name = "launchd"
        with mock.patch.object(erj.sb, "select", return_value=lau), \
                mock.patch.object(erj.sb, "_planner", return_value=_FakePlanner()), \
                mock.patch.object(erj, "_arm_launchd", return_value=(0, "cred")) as fake:
            self.assertEqual(erj.arm_oneshot("L", ["x"], ".", self.FIRE), (0, "cred"))
        fake.assert_called_once()


class PreflightTest(_Fence):
    """tools/lib/sessionctl/handoff.py::spawn_preflight：spawn 三前置的唯讀預演（FR-PK-05）。"""

    def test_preflight_matches_spawn_refusals(self) -> None:
        """handoff.py：未 finalize／工作樹髒／有執行中代理各自回原因；都過回
        []（到點必失敗的事現在就拒）。"""
        ok = FakeRunner(status="", tags="")
        self.assertEqual(
            handoff.spawn_preflight(self.package(), runner=ok, roster_mod=FakeRoster()), [])
        self.assertTrue(handoff.spawn_preflight(self.package(finalized=False, sid="b" * 8),
                                                runner=ok, roster_mod=FakeRoster()))
        dirty = FakeRunner(status=" M a.py\n", tags="")
        self.assertIn("未提交變更", "".join(handoff.spawn_preflight(
            self.package(), runner=dirty, roster_mod=FakeRoster())))
        busy = FakeRoster(running=[{"description": "QA 鏡", "id": "x"}])
        self.assertIn("QA 鏡", "".join(handoff.spawn_preflight(
            self.package(), runner=ok, roster_mod=busy)))


class FakeBackend:
    """假排程後端：只記 job 名單與呼叫，不碰真排程器。"""

    name = "schtasks"

    def __init__(self, disarm_rc: int = 0, listing: bool = True) -> None:
        self.jobs: set[str] = set()
        self.disarm_rc, self.listing, self.calls = disarm_rc, listing, []

    def disarm(self, label: str) -> int:
        self.calls.append(("disarm", label))
        if self.disarm_rc == 0:
            self.jobs.discard(label)
        return self.disarm_rc

    def list_jobs(self, prefix: str):
        self.calls.append(("list", prefix))
        return [j for j in self.jobs if j.startswith(prefix)] if self.listing else None


class _CliFence(_Fence):
    """park_cli 的共同夾具：假額度、假排程、假 runner；呼叫序列記在 `self.order`。"""

    CRED = "NextRunTime = 2026-11-16 04:02:00（排程器自報）"

    def setUp(self) -> None:
        super().setUp()
        from lib.sessionctl import park_cli
        self.cli = park_cli
        self.backend, self.order, self.armed = FakeBackend(), [], []
        self.arm_result = (0, self.CRED)
        real_write = park.write_marker

        def write(marker, **kw):
            self.order.append("marker")
            return real_write(marker, **kw)
        patch = mock.patch.object(park, "write_marker", side_effect=write)
        patch.start()
        self.addCleanup(patch.stop)
        self.pkg = self.package()
        self.quota = lambda _n: _state()

    def arm(self, label, argv, cwd, fire, *, interactive):
        self.order.append("arm")
        self.armed.append({"label": label, "argv": argv, "fire": fire, "interactive": interactive})
        if self.arm_result[0] == 0 and self.arm_result[1].strip():
            self.backend.jobs.add(label)
        return self.arm_result

    def run_cli(self, *argv, env=None, now=NOW, **extra):
        seams = {"quota": self.quota, "policy": _policy, "arm": self.arm, "backend": self.backend,
                 "runner": FakeRunner(), "roster": FakeRoster(), **extra}
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.cli.run(["--session-id", SID, *argv], env={**self.env, **(env or {})},
                              now=now, seams=seams)
        return rc, out.getvalue(), err.getvalue()


class ParkCliTest(_CliFence):
    """tools/lib/sessionctl/park_cli.py：`park` 自動選路、--at、--done、--cancel、
    --status（AT-PK-34、37～50）。
    WHY：流程順序是契約——先拿到排程器憑證才寫標記，標記寫不進去就回滾排程。"""

    def test_at_pk_37_h_route_arms_then_writes_the_marker(self) -> None:
        """park_cli.py：事故回放 ⇒ rc 0；呼叫序列＝arm → marker（不是事後看檔）；
        憑證逐字等於排程器回值；
        觸發時刻＝reset＋120 s 向後取整；成功訊息告訴主控可以結束回合、不要請人回視窗。"""
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertEqual(self.order, ["arm", "marker"])
        marker = park.read_marker(SID)
        self.assertEqual((marker["route"], marker["status"]), ("H", "armed"))
        self.assertEqual(marker["jobs"][0]["credential"], self.CRED)
        self.assertTrue(marker["jobs"][0]["label"].startswith("AutoSDD_HandoffSpawn_798a7bf1_"))
        self.assertEqual(datetime.fromisoformat(marker["fire_at"]),
                         datetime(2026, 11, 15, 20, 12, tzinfo=UTC))  # 備援＝主載具預定醒來＋10 分
        self.assertEqual(datetime.fromisoformat(marker["primary_wake_at"]),
                         datetime(2026, 11, 15, 20, 2, tzinfo=UTC))
        self.assertTrue(self.armed[0]["interactive"])
        self.assertIn(self.CRED, out)
        self.assertIn("現在可以結束回合；不要請人回這個視窗接手", out)
        self.assertRegex(out.strip().splitlines()[-1], r"^PARK_VERDICT=armed route=H sid=798a7bf1 ")
        self.assertIn("park_armed", [t["event"] for t in self.traces()])

    def test_at_pk_38_no_credential_means_no_marker(self) -> None:
        """park_cli.py：排程 rc=0 但憑證空／rc=1 ⇒ rc 1、不寫標記、落 park_arm_failed、
        stderr 說「不會說它已排程」（宣稱已排程必須有排程器自己的值）。"""
        for result in ((0, ""), (1, ""), (0, "  ")):
            with self.subTest(result=result):
                self.arm_result = result
                rc, _out, err = self.run_cli()
                self.assertEqual(rc, 1)
                self.assertIn("不會說它已排程", err)
                self.assertIsNone(park.read_marker(SID))
        self.assertIn("park_arm_failed", [t["event"] for t in self.traces()])

    def test_at_pk_41_marker_write_failure_rolls_the_job_back(self) -> None:
        """park_cli.py：標記寫入失敗 ⇒ rc 1、剛登記的排程被 disarm 且 list_jobs 驗證不在
        （沒有標記的排程是無人認領的孤兒，到點仍會 spawn）。"""
        with mock.patch.object(park, "write_marker", return_value=(False, "唯讀")):
            rc, _out, err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertEqual(self.backend.jobs, set())
        self.assertIn("已移除", err)
        self.assertTrue(any(t["event"] == "park_arm_failed" and t["rolled_back"]
                            for t in self.traces()))

    def test_at_pk_42_package_preconditions(self) -> None:
        """park_cli.py：沒有交接包／未 finalize ⇒ rc 2，
        且完全沒有呼叫排程（到點必失敗的事現在就拒絕）。"""
        self.pkg.unlink()
        rc, _out, err = self.run_cli()
        self.assertEqual(rc, 2)
        self.assertIn("handoff --build", err)
        self.package(finalized=False)
        rc, _out, err = self.run_cli()
        self.assertEqual(rc, 2)
        self.assertIn("未通過 finalize", err)
        self.assertEqual(self.order, [])

    def test_at_pk_43_preflight_failures_arm_nothing(self) -> None:
        """park_cli.py：工作樹髒且無 wip 標籤、有執行中代理 ⇒ rc 2 並列出與 spawn 同字面的原因。"""
        rc, _out, err = self.run_cli(runner=FakeRunner(status=" M a.py\n", tags=""))
        self.assertEqual(rc, 2)
        self.assertIn("未提交變更", err)
        busy = FakeRoster(running=[{"description": "QA 鏡", "id": "x"}])
        rc, _out, err = self.run_cli(roster=busy)
        self.assertEqual(rc, 2)
        self.assertIn("QA 鏡", err)
        self.assertEqual(self.order, [])

    def test_at_pk_44_unattended_is_refused_before_anything_is_read(self) -> None:
        """park_cli.py：無人窗口 ⇒ rc 4；額度與排程皆未被呼叫（無人續跑走 planner FRESH 路）。"""
        calls = []
        rc, _out, err = self.run_cli(env={"AUTOSDD_UNATTENDED": "1"},
                                     quota=lambda n: calls.append(n) or _state())
        self.assertEqual(rc, 4)
        self.assertIn("無人窗口", err)
        self.assertEqual((calls, self.order), ([], []))
        self.assertIn("park_refused", [t["event"] for t in self.traces()])

    def test_at_pk_28b_mode_and_carrier_refusals_match_the_stop_guard(self) -> None:
        """park_cli.py：notify／off／無載具 ⇒ rc 4（與 Stop 守衛在同情境放行同源：
        推回的前提必能被滿足）。"""
        for mode in ("notify", "off"):
            with self.subTest(mode=mode):
                self.assertEqual(
                    self.run_cli(env={"AUTOSDD_SESSION_SWITCH_MODE": mode})[0], 4)
        none = FakeBackend()
        none.name = "none"
        self.assertEqual(self.run_cli(backend=none)[0], 4)

    def test_at_pk_34_invariant_what_the_guard_demands_park_can_satisfy(self) -> None:
        """park_cli.py／park.py：Stop 推回的情境，同一份夾具下 `park` rc 0（I-1：
        不得推回一個做不到的指令）。"""
        text = park.stop_verdict({"session_id": SID}, {}, now=NOW, read_quota=self.quota,
                                 policy_fn=_policy, carrier_fn=lambda: True,
                                 spawned_fn=lambda _s, _e: False)
        self.assertIn("python tools/sessionctl.py park", text)
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(park.stop_verdict({"session_id": SID}, {}, now=NOW, read_quota=self.quota,
                                           policy_fn=_policy, carrier_fn=lambda: True,
                                           spawned_fn=lambda _s, _e: False), "")

    def test_at_pk_45_unknown_reset_is_refused_loudly(self) -> None:
        """park_cli.py：量不到 reset（無讀數／已達標軸 reset 缺）⇒ rc 4，訊息含「不假設 5 小時」，
        不排程。"""
        for state in (_state(axes=()),
                      _state(axes=(quota_policy.Axis("five_hour", 98.0, None),))):
            with self.subTest(axes=len(state.axes)):
                rc, _out, err = self.run_cli(quota=lambda _n, s=state: s)
                self.assertEqual(rc, 4)
                self.assertIn("不假設 5 小時", err)
        self.assertEqual(self.order, [])

    def test_at_pk_46_weekly_only_needs_explicit_at(self) -> None:
        """park_cli.py：只有週軸高 ⇒ rc 4 指向 `--at`；`--at` 缺 why／why 太短／過去／超過 8 天 ⇒
        rc 2；
        合格的 `--at` 走 H，觸發時刻＝`--at`（週額度停工的唯一明示出口）。"""
        weekly = lambda _n: _state(five=10.0, week=99.0)  # noqa: E731
        rc, _out, err = self.run_cli(quota=weekly)
        self.assertEqual(rc, 4)
        self.assertIn("--at", err)
        at = (NOW + timedelta(days=2)).isoformat()
        for argv in (["--at", at], ["--at", at, "--why", "七個字的原因啊"],
                     ["--at", (NOW - timedelta(hours=1)).isoformat(), "--why", "足夠長的原因說明"],
                     ["--at", (NOW + timedelta(days=9)).isoformat(), "--why", "足夠長的原因說明"]):
            with self.subTest(argv=argv):
                self.assertEqual(self.run_cli(*argv, quota=weekly)[0], 2)
        self.assertEqual(self.order, [])
        self.assertEqual(self.run_cli("--at", at, "--why", "週額度用完等重置", quota=weekly)[0], 0)
        self.assertEqual(datetime.fromisoformat(park.read_marker(SID)["primary_wake_at"]),
                         datetime.fromisoformat(at).replace(second=0, microsecond=0)
                         + timedelta(minutes=1 if datetime.fromisoformat(at).second else 0))

    def test_at_pk_46b_below_threshold_parks_only_with_a_stated_why(self) -> None:
        """park_cli.py：短窗 84%（未達準備門檻）⇒ 無 why／why 太短 rc 4 並指路 `--why`；
        帶合格 why ⇒ rc 0，觸發時刻仍取短窗軸**觀測**的 reset（不必手打 --at、不假設 5 小時）。
        WHY：2026-11-16 真機——主控在 84% 判斷下一棒放不下要停工，卻被固定門檻擋下；
        「放不下」是相對下一棒大小的判斷。短窗 reset 量不到時即使帶 why 也拒絕。"""
        low = lambda _n: _state(five=84.0)  # noqa: E731
        for argv in ([], ["--why", "七個字的原因啊"]):
            with self.subTest(argv=argv):
                rc, _out, err = self.run_cli(*argv, quota=low)
                self.assertEqual(rc, 4)
                self.assertIn("--why", err)
        self.assertEqual(self.order, [])
        blind = lambda _n: _state(five=84.0, resets=None)  # noqa: E731
        rc, _out, err = self.run_cli("--why", "下一棒約二十點放不下", quota=blind)
        self.assertEqual(rc, 4)
        self.assertIn("不假設 5 小時", err)
        self.assertEqual(self.order, [])
        self.assertEqual(self.run_cli("--why", "下一棒約二十點放不下", quota=low)[0], 0)
        marker = park.read_marker(SID)
        self.assertEqual(datetime.fromisoformat(marker["primary_wake_at"]),
                         datetime(2026, 11, 15, 20, 2, tzinfo=UTC))
        self.assertEqual((marker["axis"]["pct"], marker["why"]), (84.0, "下一棒約二十點放不下"))

    def test_at_pk_47_done_marker(self) -> None:
        """park_cli.py：`--done --why`（8 字）寫 DONE 標記、有效到最早短窗 reset；7 字 rc 2；無人
        rc 4；
        量不到 reset 時有效 5 小時（上限）。"""
        rc, out, _err = self.run_cli("--done", "--why", "沒有任何剩餘的工作")
        self.assertEqual(rc, 0)
        marker = park.read_marker(SID)
        self.assertEqual(marker["route"], "DONE")
        self.assertEqual(datetime.fromisoformat(marker["valid_until"]), RESET)
        self.assertIn("park_done", [t["event"] for t in self.traces()])
        self.assertEqual(self.run_cli("--done", "--why", "七個字的原因啊")[0], 2)
        self.assertEqual(self.run_cli("--done", "--why", "沒有任何剩餘的工作",
                                      env={"AUTOSDD_UNATTENDED": "1"})[0], 4)
        self.assertEqual(self.run_cli("--done", "--why", "沒有任何剩餘的工作",
                                      quota=lambda _n: _state(axes=()))[0], 0)
        self.assertEqual(datetime.fromisoformat(park.read_marker(SID)["valid_until"]),
                         NOW + timedelta(seconds=park.DONE_MAX_SECONDS))

    def test_at_pk_48_cancel_verifies_removal(self) -> None:
        """park_cli.py：`--cancel` 成功才改 cancelled；disarm 失敗或 list 量不到 ⇒ 標記維持
        armed、rc 1
        （量不到不宣稱已移除）；無標記 rc 0。"""
        self.assertEqual(self.run_cli("--cancel")[0], 0)
        self.run_cli()
        self.backend.disarm_rc = 1
        rc, _out, err = self.run_cli("--cancel")
        self.assertEqual((rc, park.read_marker(SID)["status"]), (1, "armed"))
        self.assertIn("仍在排程器裡", err)
        self.backend.disarm_rc, self.backend.listing = 0, False
        self.assertEqual(self.run_cli("--cancel")[0], 1)
        self.backend.listing = True
        self.assertEqual(self.run_cli("--cancel")[0], 0)
        self.assertEqual(park.read_marker(SID)["status"], "cancelled")
        self.assertIn("park_cancelled", [t["event"] for t in self.traces()])

    def test_at_pk_49_status_is_read_only_unless_verify(self) -> None:
        """park_cli.py：`--status` 不碰排程器（零副作用）；`--status --verify` 才查「排程器中：
        在／不在」。"""
        self.run_cli()
        before = len(self.backend.calls)
        rc, out, _err = self.run_cli("--status")
        self.assertEqual(rc, 0)
        self.assertIn("route=H status=armed", out)
        self.assertIn(self.CRED, out)
        # 零副作用＝不 arm／disarm；QW §10 三列憑證的哨兵列為唯讀 list 查詢
        self.assertEqual([c for c in self.backend.calls[before:] if c[0] != "list"], [])
        _rc, out, _err = self.run_cli("--status", "--verify")
        self.assertIn("排程器中：在", out)

    def test_at_pk_50_second_park_replaces_the_first(self) -> None:
        """park_cli.py：同 sid 第二次 park ⇒ 舊排程先被 disarm（並驗證）才登記新的，
        新標籤≠舊標籤。"""
        self.run_cli()
        old = park.read_marker(SID)["jobs"][0]["label"]
        at = (NOW + timedelta(days=1)).isoformat()
        low = lambda _n: _state(five=10.0)  # noqa: E731
        self.assertEqual(self.run_cli("--at", at, "--why", "改成明天一早再醒來", quota=low)[0], 0)
        new = park.read_marker(SID)["jobs"][0]["label"]
        self.assertNotEqual(old, new)
        self.assertEqual(self.backend.jobs, {new})
        self.assertIn(("disarm", old), self.backend.calls)  # 舊的先被撤（且驗證過）
        self.assertEqual(self.order.count("arm"), 2)

    def test_missing_or_bad_session_id(self) -> None:
        """park_cli.py：缺 sid ⇒ rc 3；含路徑字元 ⇒ rc 2（sid 直接進檔名，擋路徑穿越）。"""
        with redirect_stderr(io.StringIO()):
            self.assertEqual(self.cli.run([], env={}, now=NOW), 3)
            self.assertEqual(self.cli.run(["--session-id", "../x"], env={}, now=NOW), 2)


class SentinelYieldTest(unittest.TestCase):
    """`tools/session_resume_planner.py::sentinel_decide`：park
    標記有效窗內哨兵讓路（AT-PK-66～71）。
    WHY：park 排程待命時哨兵若照撞線事件去探測／排 reset 喚醒，會與到點的新 session 變成雙駕駛。"""

    TZ = timezone(timedelta(hours=8))
    EVENT = {"kind": "session", "timestamp": "2026-08-07T00:44:01.000Z",
             "text": "You've hit your session limit · resets 9am (Asia/Taipei)"}

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
        import context_budget_guard

        import session_resume_planner
        cls.planner, cls.guard = session_resume_planner, context_budget_guard

    def now(self, hour: int = 0, minute: int = 45) -> datetime:
        return datetime(2026, 8, 7, hour, minute, tzinfo=UTC).astimezone(self.TZ)

    def marker(self, now: datetime, **kw) -> dict:
        return dict(_marker("H", valid=now + timedelta(hours=1)), **kw)

    def test_at_pk_66_a_valid_marker_yields_to_the_scheduled_job(self) -> None:
        """planner：未處理撞線（reset 未到）＋有效 H 標記 ⇒ patrol 讓路、理由點名 park；
        不是 arm_reset／probe（那會與到點的新 session 搶駕駛）。"""
        now = self.now()
        got = self.planner.sentinel_decide(self.EVENT, "", 10.0, now, park=self.marker(now))
        self.assertEqual(got["action"], "patrol")
        self.assertIn("park", got["reason"])
        self.assertEqual((got["at"] - now).total_seconds(), self.planner.SENTINEL_INTERVAL_SECONDS)

    def test_at_pk_67_69_no_effective_marker_means_the_old_decision_exactly(self) -> None:
        """planner：park=None／標記非 armed／DONE／窗已過 ⇒ 與沒有 park 參數時的判定逐項相同
        （代表輸入表：撞線 reset 未到／已過、無事件 live／idle 過久／月度上限）。"""
        spend = {"kind": self.guard.LIMIT_SPEND, "timestamp": self.EVENT["timestamp"], "text": "x"}
        table = [(self.EVENT, 10.0, self.now(0, 45)), (self.EVENT, 10.0, self.now(7, 0)),
                 (None, 60.0, self.now(7, 0)),
                 (None, self.planner.SENTINEL_IDLE_SECONDS + 1, self.now(7, 0)),
                 (spend, 10.0, self.now(7, 0))]
        for event, idle, now in table:
            baseline = self.planner.sentinel_decide(event, "", idle, now)
            for label, marker in (("None", None),
                                  ("fired", self.marker(now, status="fired")),
                                  ("done", dict(self.marker(now), route="DONE", jobs=[],
                                                why="沒有任何剩餘的工作")),
                                  ("expired", self.marker(now) | {"valid_until": (
                                      now - timedelta(seconds=1)).isoformat()})):
                with self.subTest(event=(event or {}).get("kind"), idle=idle, marker=label):
                    self.assertEqual(
                        self.planner.sentinel_decide(event, "", idle, now, park=marker), baseline)

    def test_at_pk_68_monthly_spend_still_escalates_under_a_valid_marker(self) -> None:
        """planner：LIMIT_SPEND 即使有有效標記仍 escalate（錢的事只有人能解，讓路等於吞掉警報）。"""
        now = self.now(7, 0)
        spend = {"kind": self.guard.LIMIT_SPEND, "timestamp": self.EVENT["timestamp"], "text": "x"}
        got = self.planner.sentinel_decide(spend, "", 10.0, now, park=self.marker(now))
        self.assertEqual(got["action"], "escalate")

    def test_at_pk_70_the_tick_passes_the_marker_through(self) -> None:
        """planner：`_sentinel_tick` 呼叫 `sentinel_decide` 時帶 `park=…read_marker(sid)`
        （少了這個接線，判準層全綠而哨兵照搶駕駛——fail-open 表徵與修好相同）。"""
        text = (_REPO_ROOT / "tools" / "session_resume_planner.py").read_text(encoding="utf-8")
        head = "decision = sentinel_decide("
        call = next(ln for ln in text.splitlines() if ln.lstrip().startswith(head))
        self.assertIn("park=sessionctl_park.read_marker(sid)", call)


class MessageTest(unittest.TestCase):
    """tools/lib/quota_messages.py::quota_prepare_message：準備帶訊息的 park 指引（AT-PK-72～73）。
    WHY：事故當天主控讀到的是「收斂」卻沒人告訴它停工前要掛續航憑證。"""

    def test_at_pk_72_prepare_message_points_at_park_and_not_at_the_old_window(self) -> None:
        """quota_messages.py：含 `sessionctl.py park`、不含手寫的 85~95%、不叫人回視窗說繼續；
        既有的「準備」「現查還能派幾個」仍在；新增句不含 %（水位數字由 describe 逐軸印）。"""
        import quota_messages
        decision = quota_policy.decide(_state(five=98.0), NOW, _policy(), None, "")
        text = quota_messages.quota_prepare_message(decision, "plan.md", NOW)
        for needle in ("python tools/sessionctl.py park", "準備", "現查還能派幾個"):
            self.assertIn(needle, text)
        for banned in ("85~95%", "在這個視窗說一聲", "說一聲繼續"):
            self.assertNotIn(banned, text)
        added = next(ln for ln in text.splitlines() if "sessionctl.py park" in ln)
        self.assertNotIn("%", added)


def _line(**rec) -> str:
    return json.dumps(rec, ensure_ascii=False)


class JobTest(_CliFence):
    """tools/lib/sessionctl/park_cli.py：job 本體 `--fire`（AT-PK-57～64；W 兜底列略過）。
    WHY：到點時舊 session 可能已被人叫醒——先查有沒有人在動，只信對話記錄、不信檔案 mtime。"""

    LATE = NOW + timedelta(hours=1)

    def setUp(self) -> None:
        super().setUp()
        self.label = "AutoSDD_HandoffSpawn_798a7bf1_202611152002"
        self.backend.jobs.add(self.label)
        park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
        self.transcript = self.tmp / f"{SID}.jsonl"
        self.spawned: list[Path] = []
        self.resumed: list[int] = []
        self.spawn_rc = self.resume_rc = 0

    def records(self, *lines: str, mtime_now: bool = False) -> None:
        self.transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
        if not mtime_now:
            old = (self.LATE - timedelta(hours=5)).timestamp()
            os.utime(self.transcript, (old, old))

    def fire(self, *, pkg=None, env=None, label=None):
        def spawn(path):
            self.spawned.append(path)
            return self.spawn_rc
        def resume(*_a, **_kw):  # 失敗鏈會試另一條路：兩條路都要有縫，絕不開真視窗
            self.resumed.append(1)
            return self.resume_rc
        seams = {"backend": self.backend, "spawn": spawn, "resume": resume, "platform": "win32",
                 "preflight": lambda *_a, **_k: [], "transcript": lambda _s: self.transcript,
                 "sessions_dir": self.tmp / "sessions",
                 "notify": lambda *_a: 0}
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = self.cli.run(["--session-id", SID, "--fire", "--job", label or self.label,
                               "--pkg", str(pkg or self.pkg), "--fire-at", RESET.isoformat()],
                              env={**self.env, **(env or {})}, now=self.LATE, seams=seams)
        return rc

    def stamp(self, minutes_ago: float) -> str:
        return (self.LATE - timedelta(minutes=minutes_ago)).isoformat()

    def skipped_reasons(self) -> list[str]:
        return [t["reason"] for t in self.traces() if t["event"] == "handoff_spawn_skipped"]

    def test_at_pk_57_58_a_live_driver_blocks_the_spawn(self) -> None:
        """park_cli.py：近 900 秒內有 assistant／human／auto-continuation 記錄 ⇒ 不 spawn、
        標記 skipped、job 自拆（舊 session 還在動時再開新視窗＝同工作樹雙駕駛）。"""
        five = self.stamp(5)
        for rec in (_line(type="assistant", timestamp=five, message={"model": "claude-fable-5"}),
                    _line(type="user", timestamp=five, origin={"kind": "human"}),
                    _line(type="user", timestamp=five, origin={"kind": "auto-continuation"})):
            with self.subTest(rec=rec[:40]):
                park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
                self.backend.jobs.add(self.label)
                self.records(rec)
                self.assertEqual(self.fire(), 0)
                self.assertEqual(self.spawned, [])
                self.assertEqual(park.read_marker(SID)["status"], "skipped")
                self.assertNotIn(self.label, self.backend.jobs)
        self.assertEqual(set(self.skipped_reasons()), {"live_driver"})

    def test_at_pk_59_synthetic_records_and_fresh_mtime_are_not_a_driver(self) -> None:
        """park_cli.py：只有 away_summary／cost-state／tool_result／合成限額記錄，且檔案 mtime
        剛剛才動 ⇒
        照常 spawn（DEF-200-560 同型：harness 的背景寫入會讓 mtime 一直新，不是有人在動）。"""
        self.records(_line(type="system", subtype="away_summary", timestamp=self.stamp(1)),
                     _line(type="system", subtype="cost-state", timestamp=self.stamp(2)),
                     _line(type="user", timestamp=self.stamp(3),
                           message={"content": [{"type": "tool_result", "content": "x"}]}),
                     _line(type="assistant", timestamp=self.stamp(4),
                           message={"model": "<synthetic>"}), mtime_now=True)
        self.assertEqual(self.fire(), 0)
        self.assertEqual(self.spawned, [self.pkg])

    def test_at_pk_60_acked_or_expired_package_is_skipped(self) -> None:
        """park_cli.py：交接包已 ack／檔案不存在／超過 TTL ⇒ 跳過、不 spawn、job 自拆。"""
        self.records()
        self.pkg.with_suffix(".ack").write_text("acked", encoding="utf-8")
        self.assertEqual(self.fire(), 0)
        self.assertEqual(self.skipped_reasons(), ["acked"])
        park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
        self.pkg.with_suffix(".ack").unlink()
        old = (self.LATE - timedelta(days=30)).timestamp()
        os.utime(self.pkg, (old, old))
        self.assertEqual(self.fire(), 0)
        self.assertEqual(self.skipped_reasons(), ["acked", "expired"])
        self.assertEqual(self.spawned, [])

    def test_at_pk_61_cancelled_or_missing_marker_is_skipped(self) -> None:
        """park_cli.py：標記 cancelled／缺／不含本 job ⇒ 跳過（reason=cancelled／not_armed）、
        自拆、rc 0。"""
        self.records()
        park.write_marker(dict(_marker("H", status="cancelled"), pkg=str(self.pkg)))
        self.assertEqual(self.fire(), 0)
        self.assertEqual(self.fire(label="AutoSDD_HandoffSpawn_798a7bf1_other"), 0)
        park.marker_path(SID).unlink()
        self.assertEqual(self.fire(), 0)
        self.assertEqual(self.skipped_reasons(), ["cancelled", "cancelled", "not_armed"])
        self.assertEqual(self.spawned, [])

    def test_at_pk_62_success_marks_fired_and_removes_the_job(self) -> None:
        """park_cli.py：spawn rc 0 ⇒ 標記 fired、落 park_spawned、job 自拆、rc 0。"""
        self.records()
        self.assertEqual(self.fire(), 0)
        self.assertEqual(park.read_marker(SID)["status"], "fired")
        self.assertIn("park_spawned", [t["event"] for t in self.traces()])
        self.assertNotIn(self.label, self.backend.jobs)

    def test_at_pk_63_failure_writes_a_handback_with_the_four_headings(self) -> None:
        """park_cli.py：兩條路都失敗 ⇒ 標記 failed（outcome.attempts 逐筆實際值）、落
        park_chain_failed、寫四標題齊備的 handback、rc 1（下次 SessionStart 由既有
        announce_handbacks 出聲，不是靜默失敗）。QW Q3：不再只試一條路。"""
        self.records()
        self.spawn_rc = self.resume_rc = 1
        self.assertEqual(self.fire(), 1)
        marker = park.read_marker(SID)
        self.assertEqual(marker["status"], "failed")
        self.assertEqual([(a["route"], a["rc"]) for a in marker["outcome"]["attempts"]],
                         [("FRESH", 1), ("RESUME", 1)])
        self.assertNotIn("spawn_rc", marker["outcome"]["detail"])
        text = (self.bdir / f"{SID}_park_failed.md").read_text(encoding="utf-8")
        for head in ("## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步指令"):
            self.assertIn(head, text)
        events = [t["event"] for t in self.traces()]
        self.assertIn("park_chain_failed", events)
        self.assertEqual(events.count("park_attempt"), 2)

    def test_at_pk_64_unattended_job_refuses_to_spawn(self) -> None:
        """park_cli.py：job 環境有 AUTOSDD_UNATTENDED（不該有，防禦）⇒ 拒絕 spawn、rc 4。"""
        self.records()
        self.assertEqual(self.fire(env={"AUTOSDD_UNATTENDED": "1"}), 4)
        self.assertEqual(self.spawned, [])


if __name__ == "__main__":
    unittest.main()
