"""單一權威額度判決（TCS-Autopilot-20261125 REQ-AP-QV-01～11；QVD v1.3）。

`QV::VerdictTest`／`RenderTest`：純函式 `quota_ruling.ruling()` 決策表七列、判決行、有效期、計費姿態。
`GatherTest`：`sessionctl/ruling_io.gather()` 取數（halt 標記不壓補量、429 降級）。
`ConsumerTest`／`ParkTest`／`WatchTest`：消費端改接（C1、C4～C7、C13、C21）。
`SingleHouseTest`：單一判讀家機械鎖（QVD §3.5.3；白名單 `RULING_INPUT_SITES` 相等比對）。
`LocTest`：LOC 抽出（`pace_report` 不在 hub）。

縫：`now` 注入、`AUTOSDD_TRACE_DIR`／`AUTOSDD_QUOTA_CACHE_DIR`／TEMP 圍到暫存、取數函式以
`mock.patch.object` 換成替身；不打真端點、不起真排程、不讀真 `~/.claude`。
"""
from __future__ import annotations

import ast
import itertools
import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_gate  # noqa: E402
import quota_policy  # noqa: E402
import quota_ruling as QR  # noqa: E402

from lib.sessionctl import qw_plan, ruling_io  # noqa: E402

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 25, 3, 46, 19, tzinfo=TPE)
POLICY = quota_policy.DEFAULT_POLICY
#: 真實 `~/.autosdd/traces/quota_burn.jsonl` 2026-11-24～25 的四列（逐字複製；AC-QV-01d 夾具）。
BURN_ROWS = r"""
{"bd": null, "fp": ["account=34cd3507237f", "five_hour", "session", "seven_day", "spend", "weekly_all"], "live": 0, "pct": {"five_hour": 2.0, "session": 2.0, "seven_day": 96.0, "spend": 0.0, "weekly_all": 96.0}, "resets_at": {"five_hour": "2026-11-24T15:00:00.156880+00:00", "session": "2026-11-24T15:00:00.156880+00:00", "seven_day": "2026-11-27T22:00:00.156903+00:00", "spend": null, "weekly_all": "2026-11-27T22:00:00.156903+00:00"}, "ts": "2026-11-24T20:50:10+08:00"}
{"bd": null, "fp": ["account=eaf5241f6fe2", "extra_usage", "five_hour", "session", "seven_day", "spend", "weekly_all"], "live": 0, "pct": {"extra_usage": 0.0, "five_hour": 77.0, "session": 77.0, "seven_day": 14.0, "spend": 0.0, "weekly_all": 14.0}, "resets_at": {"extra_usage": null, "five_hour": "2026-11-24T19:59:59.589030+00:00", "session": "2026-11-24T19:59:59.589030+00:00", "seven_day": "2026-12-01T10:59:59.589056+00:00", "spend": null, "weekly_all": "2026-12-01T10:59:59.589056+00:00"}, "ts": "2026-11-25T03:43:19+08:00"}
{"bd": null, "fp": ["account=eaf5241f6fe2", "extra_usage", "five_hour", "session", "seven_day", "spend", "weekly_all"], "live": 2, "pct": {"extra_usage": 0.0, "five_hour": 87.0, "session": 87.0, "seven_day": 15.0, "spend": 0.0, "weekly_all": 15.0}, "resets_at": {"extra_usage": null, "five_hour": "2026-11-24T20:00:00.546902+00:00", "session": "2026-11-24T20:00:00.546902+00:00", "seven_day": "2026-12-01T11:00:00.546927+00:00", "spend": null, "weekly_all": "2026-12-01T11:00:00.546927+00:00"}, "ts": "2026-11-25T03:46:19+08:00"}
{"bd": null, "fp": ["account=eaf5241f6fe2", "extra_usage", "five_hour", "session", "seven_day", "spend", "weekly_all"], "live": 0, "pct": {"extra_usage": 0.0, "five_hour": 0.0, "session": 0.0, "seven_day": 16.0, "spend": 0.0, "weekly_all": 16.0}, "resets_at": {"extra_usage": null, "five_hour": "2026-11-25T01:00:00.683250+00:00", "session": "2026-11-25T01:00:00.683250+00:00", "seven_day": "2026-12-01T11:00:00.683273+00:00", "spend": null, "weekly_all": "2026-12-01T11:00:00.683273+00:00"}, "ts": "2026-11-25T04:00:32+08:00"}
""".strip()  # noqa: E501


def _iso(when: datetime) -> str:
    return when.isoformat(timespec="seconds")


def _axis(kind: str, pct: float, reset_min: float | None, *, scope=None, now=NOW):
    reset = None if reset_min is None else _iso(now + timedelta(minutes=reset_min))
    return quota_policy.Axis(kind, pct, reset, scope_model=scope)


def _state(*axes, acct="eaf5241f6fe2", now=NOW, retry=None):
    if not axes:
        return quota_policy.QuotaState((), "", "no-cache", "no-cache", retry_after=retry)
    return quota_policy.QuotaState(tuple(axes), _iso(now), "cache", "ok", acct)


def _short(pct, reset_min=150):
    return _axis("five_hour", pct, reset_min)


def _week(pct, reset_min=6000, kind="seven_day", scope=None):
    return _axis(kind, pct, reset_min, scope=scope)


def _dec(cap=4, band="converge"):
    return SimpleNamespace(cap=cap, band=band, recommended_fanout=cap or 0)


def _rule(state, decision=None, *, model="sonnet", plan=None, markers=(), next_est=None,
          now=NOW, **kw):
    return QR.ruling(state, decision or _dec(), model=model, policy=POLICY, now=now,
                     markers=markers, plan=plan, next_est=next_est, wait_min=45.0, **kw)


def _burn_state(row: dict) -> quota_policy.QuotaState:
    acct = next(f.split("=", 1)[1] for f in row["fp"] if f.startswith("account="))
    axes = tuple(quota_policy.Axis(k, float(v), row["resets_at"].get(k))
                 for k, v in row["pct"].items())
    return quota_policy.QuotaState(axes, row["ts"], "cache", "ok", acct)


class VerdictTest(unittest.TestCase):
    """REQ-AP-QV-01／07：決策表七列（QVD §3.2）。"""

    def test_87pct_14min_waits_reset_not_park(self):
        """AC-QV-01a：E2 情境（87%、D=14、stage=free、等待上限 45）⇒ WAIT_RESET，輸出不含 PARK。"""
        r = _rule(_state(_short(87, 14)), plan=qw_plan.Plan("free", d_min=14, r=13, v=1, limit=5))
        self.assertEqual(r.action, QR.WAIT_RESET)
        self.assertNotIn("PARK", QR.line(r))
        self.assertEqual(r.cap, 0)

    def test_table_rows_1_spend_halts_without_reset(self):
        r = _rule(_state(_short(10), _axis("spend", 100.0, None)))
        self.assertEqual((r.action, r.wk), (QR.HALT_WEEKLY, None))
        self.assertIn("月度支出上限", r.reason)
        neg = _rule(_state(_short(10), _axis("spend", 99.0, None)))
        self.assertEqual(neg.action, QR.CONTINUE)

    def test_table_rows_2_weekly_beats_short(self):
        r = _rule(_state(_short(90, 10), _week(96)))
        self.assertEqual(r.action, QR.HALT_WEEKLY, "週軸須優先於同時成立的短窗第 3 列")
        self.assertIsNotNone(r.wk)
        neg = _rule(_state(_short(10), _week(94)))
        self.assertEqual(neg.action, QR.CONTINUE)

    def test_table_rows_2_weekly_marker_same_account(self):
        reset = _iso(NOW + timedelta(days=2))
        marker = {"binding": "seven_day", "reset_at": reset, "account": "eaf5241f6fe2"}
        self.assertEqual(_rule(_state(_short(10)), markers=[marker]).action, QR.HALT_WEEKLY)
        other = dict(marker, account="34cd3507237f")
        self.assertEqual(_rule(_state(_short(10)), markers=[other]).action, QR.CONTINUE,
                         "別帳號的標記不得當輸入（交 §7 作廢）")

    def test_table_rows_3_park_or_nodispatch(self):
        self.assertEqual(_rule(_state(_short(90, 120))).action, QR.PARK)
        no_reset = _rule(_state(_axis("five_hour", 90, None)), plan=qw_plan.Plan("close"))
        self.assertEqual(no_reset.action, QR.NODISPATCH, "短窗 reset 量不到不出 PARK（F-07）")
        stage = _rule(_state(_short(40, 100)), plan=qw_plan.Plan("close", reset=(
            NOW + timedelta(minutes=100)).timestamp()))
        self.assertEqual(stage.action, QR.PARK, "stage close 走第 3 列")
        neg = _rule(_state(_short(84, 120)))
        self.assertEqual(neg.action, QR.CONTINUE)

    def test_table_rows_4_nodispatch(self):
        r = _rule(_state(_short(40)), plan=qw_plan.Plan("nodispatch", r=60, v=1, limit=70))
        self.assertEqual(r.action, QR.NODISPATCH)
        self.assertEqual(_rule(_state(_short(40)), plan=qw_plan.Plan("free")).action, QR.CONTINUE)

    def test_table_rows_5_next_est_three_ways(self):
        plan = qw_plan.Plan("free", r=20.0, v=2.0)
        far = _rule(_state(_short(80, 120)), plan=plan, next_est=18.0)
        near = _rule(_state(_short(80, 20)), plan=plan, next_est=18.0)
        none = _rule(_state(_axis("five_hour", 80, None)), plan=plan, next_est=18.0)
        self.assertEqual((far.action, near.action, none.action),
                         (QR.PARK, QR.WAIT_RESET, QR.NODISPATCH))
        self.assertEqual(_rule(_state(_short(80, 120)), plan=plan, next_est=17.9).action,
                         QR.CONTINUE, "next_est < R−V 不命中（等號才命中）")

    def test_table_rows_7_continue_cap_is_decision(self):
        r = _rule(_state(_short(30)), _dec(cap=8, band="notice"))
        self.assertEqual((r.action, r.cap, r.degraded), (QR.CONTINUE, 8, False))

    def test_exactly_one_action_property(self):
        """AC-QV-01c：笛卡兒積上恰一個 ACTION、cap>0 僅在 CONTINUE。"""
        stages = (None, "free", "nodispatch", "close", "wall")
        resets = (5, 30, 120, None)
        markers = ((), ({"binding": "five_hour", "reset_at": _iso(NOW + timedelta(minutes=20))},),
                   ({"binding": "seven_day", "reset_at": _iso(NOW + timedelta(days=1))},))
        for pct, stage, rm, est, mk, model, usable in itertools.product(
                (10, 60, 86, 96), stages, resets, (None, 1.0, 50.0), markers,
                ("fable", "sonnet"), (True, False)):
            st = _state(_axis("five_hour", pct, rm), _week(pct)) if usable else _state()
            plan = None if stage is None else qw_plan.Plan(stage, r=30.0, v=2.0)
            r = _rule(st, _dec(cap=3), model=model, plan=plan, markers=mk, next_est=est)
            with self.subTest(pct=pct, stage=stage, rm=rm, est=est, mk=len(mk), usable=usable):
                self.assertIn(r.action, QR.ACTIONS)
                self.assertEqual(QR.parse(QR.line(r))["action"], r.action)
                self.assertTrue(r.cap > 0 if r.action == QR.CONTINUE else r.cap == 0)

    def test_named_moments_from_burn_ledger(self):
        """AC-QV-01d：真實燃燒帳四列（複製到 tmp 再讀）。"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quota_burn.jsonl"
            path.write_text(BURN_ROWS + "\n", encoding="utf-8")
            rows = {json.loads(x)["ts"]: json.loads(x)
                    for x in path.read_text(encoding="utf-8").splitlines()}
        at346 = datetime.fromisoformat("2026-11-25T03:46:19+08:00")
        r = _rule(_burn_state(rows["2026-11-25T03:46:19+08:00"]), now=at346,
                  plan=qw_plan.Plan("free"))
        self.assertEqual(r.action, QR.WAIT_RESET)
        self.assertTrue(r.win.startswith("2026-11-25T04:00"), r.win)
        at400 = datetime.fromisoformat("2026-11-25T04:00:32+08:00")
        self.assertEqual(_rule(_burn_state(rows["2026-11-25T04:00:32+08:00"]), now=at400).action,
                         QR.CONTINUE)
        for ts, acct in (("2026-11-24T20:50:10+08:00", "34cd3507237f"),
                         ("2026-11-25T03:43:19+08:00", "eaf5241f6fe2")):
            got = _rule(_burn_state(rows[ts]), now=datetime.fromisoformat(ts))
            self.assertIn(f"acct={acct}", QR.head(got))

    def test_model_scoped_weekly_axis(self):
        """AC-QV-01e：Fable 專屬週軸 100%、全模型週軸 60%。"""
        st = _state(_short(10), _week(60, kind="weekly_all"),
                    _week(100, kind="weekly_scoped", scope="Fable"))
        self.assertEqual(_rule(st, model="sonnet").action, QR.CONTINUE)
        self.assertEqual(_rule(st, model="fable").action, QR.HALT_WEEKLY)

    def test_pace_floor_and_rush_affect_cap_only(self):
        """AC-QV-01f：同一份原始讀數、四種 decision（配速床／rush 有無）⇒ 動作相同、cap 可不同。"""
        st = _state(_short(60, 100))
        got = {_rule(st, _dec(cap=c, band=b)).action
               for c, b in ((8, "notice"), (2, "prepare"), (4, "converge"), (16, "free"))}
        self.assertEqual(got, {QR.CONTINUE}, "墊高帶不得改動作（MU-QV-14）")
        caps = {_rule(st, _dec(cap=c)).cap for c in (8, 2)}
        self.assertEqual(caps, {8, 2})

    def test_cap_is_dispatch_pipeline(self):
        """AC-QV-01g：cap＝decision.cap；None ⇒ max_fanout；plan 替身帶 cap 屬性也不影響。"""
        st = _state(_short(30))
        fake_plan = SimpleNamespace(stage="free", cap=1, k=0, r=None, v=None, reset=None)
        self.assertEqual(_rule(st, _dec(cap=5), plan=fake_plan).cap, 5)
        self.assertEqual(_rule(st, _dec(cap=None, band="free"), plan=fake_plan).cap,
                         POLICY.max_fanout)

    def test_unreadable_is_capped_continue(self):
        """AC-QV-07a：量不到 ⇒ CONTINUE deg=unmeasured、1 ≤ cap ≤ cap_prepare；有標記走標記。"""
        dec = quota_policy.decide(_state(), NOW, POLICY)
        r = _rule(_state(), dec)
        self.assertEqual((r.action, r.degraded), (QR.CONTINUE, True))
        self.assertTrue(1 <= r.cap <= POLICY.cap_prepare, r.cap)
        self.assertIn("deg=unmeasured", QR.head(r))
        marker = {"binding": "five_hour", "reset_at": _iso(NOW + timedelta(minutes=10))}
        self.assertEqual(_rule(_state(), dec, markers=[marker]).action, QR.WAIT_RESET)


class RenderTest(unittest.TestCase):
    """REQ-AP-QV-02／07：判決行格式、有效期、計費姿態。"""

    def test_line_fields_and_expiry(self):
        r = _rule(_state(_short(30, 2)))
        head = QR.head(r)
        keys = [p.split("=", 1)[0] for p in head.split()[1:]]
        self.assertEqual(keys[:8], ["acct", "win", "wk", "cap", "measured_at", "expires_at", "vid",
                                    "mdl"])
        self.assertEqual(r.expires_at, _iso(NOW + timedelta(minutes=2)), "min(+180s, reset)")
        far = _rule(_state(_short(30, 120)))
        self.assertEqual(far.expires_at, _iso(NOW + timedelta(seconds=180)))
        self.assertIn("+08:00", far.expires_at)
        self.assertEqual(far.vid, _rule(_state(_short(30, 120))).vid, "同輸入 vid 穩定")
        self.assertNotEqual(far.vid, _rule(_state(_short(30, 119))).vid)
        self.assertEqual(QR.parse(QR.line(far))["vid"], far.vid)

    def test_unusable_state_expiry_in_future(self):
        """AC-QV-02d：讀數不可用 ⇒ expires_at＝now＋max(180, retry_after) 且 > now。"""
        self.assertEqual(_rule(_state()).expires_at, _iso(NOW + timedelta(seconds=180)))
        self.assertEqual(_rule(_state(retry="600")).expires_at, _iso(NOW + timedelta(seconds=600)))
        self.assertFalse(_rule(_state()).expired(NOW))

    def test_expired_parse_and_recompute_rule(self):
        r = _rule(_state(_short(30)))
        fields = QR.parse("noise\n" + QR.line(r))
        self.assertFalse(QR.expired(fields, NOW))
        self.assertTrue(QR.expired(fields, NOW + timedelta(seconds=181)))
        self.assertTrue(QR.expired(None, NOW), "缺判決行＝過期")

    def test_billing_from_posture(self):
        """AC-QV-07b：四值推導；`posture_line()` 呼叫同一函式。"""
        cases = ((None, "unknown"), ({}, "unknown"),
                 ({"credits_present": False}, "subscription_only"),
                 ({"credits_present": True, "fallback_available": True}, "credits_fallback"),
                 ({"credits_present": True, "fallback_available": False}, "subscription_only"),
                 ({"credits_present": False, "source": "api_key"}, "api_key"))
        for posture, want in cases:
            self.assertEqual(QR.billing_from_posture(posture), want, posture)
        import inspect  # noqa: PLC0415

        import quota_messages  # noqa: PLC0415

        self.assertIn("billing_from_posture(", inspect.getsource(quota_messages.posture_line))

    def test_ttl_and_wait_alias_parity(self):
        self.assertEqual(QR.TTL_SECONDS, quota_gate.QUOTA_CACHE_TTL_SECONDS)
        self.assertEqual(QR.wait_reset_min({}), 45.0)
        self.assertEqual(QR.wait_reset_min({"AUTOSDD_KEEPWARM_MINUTES": "30"}), 30.0)
        self.assertEqual(QR.wait_reset_min({"AUTOSDD_KEEPWARM_MINUTES": "999"}), 45.0)


class _Fenced(unittest.TestCase):
    """痕跡／快取／暫存全部圍到 tmp（DEF-200-652：避免真憑證線上補量）。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qv_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        env = {"AUTOSDD_TRACE_DIR": str(self.tmp / "traces"), "TEMP": str(self.tmp),
               "TMP": str(self.tmp), "TMPDIR": str(self.tmp),
               "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp / "cache"),
               "CLAUDE_CONFIG_DIR": str(self.tmp / "claude"), "AUTOSDD_SESSION_SWITCH_MODE": "auto"}
        self.enterContext(mock.patch.dict(os.environ, env))
        self.enterContext(mock.patch.object(tempfile, "tempdir", str(self.tmp)))


class GatherTest(_Fenced):
    """REQ-AP-QV-03／07：取數（QVD §3.4）。"""

    def _cache(self, pct, *, age=0, reset_min=120):
        now = datetime.now().astimezone()
        path = self.tmp / "autosdd_quota.json"
        path.write_text(json.dumps({
            "schema": quota_gate.quota_schema(), "source": "endpoint",
            "measured_at": _iso(now - timedelta(seconds=age)),
            "axes": [{"kind": "five_hour", "pct": pct,
                      "resets_at": _iso(now + timedelta(minutes=reset_min))}]}),
            encoding="utf-8")
        self.enterContext(mock.patch.object(quota_gate, "quota_cache_path", lambda: path))
        return path

    def test_halt_does_not_suppress_refresh(self):
        """AC-QV-03a：halt 標記有效＋快取逾 TTL ⇒ 補量恰一次（同 TTL 內第二次不補）。"""
        self._cache(30, age=900)
        sid = "11111111-2222-4333-8444-555555555555"
        quota_gate.write_halt_marker(sid, {"sid": sid, "binding": "five_hour", "at": _iso(NOW),
                                           "reset_at": _iso(datetime.now().astimezone()
                                                            + timedelta(minutes=30))})
        calls = []
        meter = SimpleNamespace(SCHEMA=quota_gate.quota_schema(), measure_detail=lambda _t: calls.append(1) or (None, "http-429"),
                                write_cache=lambda *_a: True,
                                read_retry_hint=lambda _p: "600")
        self.enterContext(mock.patch.object(quota_gate, "quota_meter", meter))
        ruling_io.gather(sid)
        ruling_io.gather(sid)
        self.assertEqual(len(calls), 1, "halt 有效時仍須補量一次；同 TTL 內不補第二次")

    def test_429_degrades_to_capped_continue(self):
        """AC-QV-03b：429（帶 retry-after）⇒ CONTINUE deg=unmeasured、1 ≤ cap ≤ cap_prepare。"""
        self._cache(30, age=900)
        meter = SimpleNamespace(SCHEMA=quota_gate.quota_schema(), measure_detail=lambda _t: (None, "http-429"),
                                write_cache=lambda *_a: True, read_retry_hint=lambda _p: "600")
        self.enterContext(mock.patch.object(quota_gate, "quota_meter", meter))
        now = datetime.now().astimezone()
        r = ruling_io.gather("", now=now).ruling
        self.assertEqual((r.action, r.degraded), (QR.CONTINUE, True))
        self.assertTrue(1 <= r.cap <= POLICY.cap_prepare)
        self.assertGreater(datetime.fromisoformat(r.expires_at), now + timedelta(seconds=590))


class LocTest(unittest.TestCase):
    def test_pace_report_moved_out_of_hub(self):
        """AC-QV-08b：`pace_report` 不再存在於 `quota_gate`（hub 成員只縮不長）。"""
        self.assertFalse(hasattr(quota_gate, "pace_report"))
        self.assertTrue(callable(ruling_io.pace_report))


if __name__ == "__main__":
    unittest.main()
