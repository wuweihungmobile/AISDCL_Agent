"""單一權威額度判決（TCS-Autopilot-20261125 REQ-AP-QV-01～11；QVD v1.3）。

`QV::VerdictTest`／`RenderTest`：純函式 `quota_ruling.ruling()` 決策表七列、判決行、有效期、
計費姿態。
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_gate  # noqa: E402
import quota_policy  # noqa: E402
import quota_ruling as QR  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402  # 模組級圍籬原語（判決取數會寫額度快取／痕跡）

from lib.sessionctl import qw_plan, ruling_io  # noqa: E402

_MODULE_FENCES: list[dict] = []


def setUpModule() -> None:
    """寫端模組圍籬（`test_run_root_unittests.TestWriterModulesDeclareTheModuleFence`）：本檔的判決
    取數、park／watch／保溫測試會寫痕跡與額度快取；類別級 `_Fenced` 之外再兜一層模組級。"""
    _MODULE_FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_MODULE_FENCES.pop())


TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 25, 3, 46, 19, tzinfo=TPE)
POLICY = quota_policy.DEFAULT_POLICY
#: 真實 `~/.autosdd/traces/quota_burn.jsonl` 2026-11-24～25 的四列（逐字複製；AC-QV-01d 夾具）。
BURN_ROWS = "\n".join([  # 逐字複製（各列以字串相接，值與原檔逐位元組相同）
    '{"bd": null, "fp": ["account=34cd3507237f", "five_hour", "session", "seven_day", '
    '"spend", "weekly_all"], "live": 0, "pct": {"five_hour": 2.0, "session": 2.0, '
    '"seven_day": 96.0, "spend": 0.0, "weekly_all": 96.0}, '
    '"resets_at": {"five_hour": "2026-11-24T15:00:00.156880+00:00", '
    '"session": "2026-11-24T15:00:00.156880+00:00", '
    '"seven_day": "2026-11-27T22:00:00.156903+00:00", "spend": null, '
    '"weekly_all": "2026-11-27T22:00:00.156903+00:00"}, '
    '"ts": "2026-11-24T20:50:10+08:00"}',
    '{"bd": null, "fp": ["account=eaf5241f6fe2", "extra_usage", "five_hour", "session", '
    '"seven_day", "spend", "weekly_all"], "live": 0, "pct": {"extra_usage": 0.0, '
    '"five_hour": 77.0, "session": 77.0, "seven_day": 14.0, "spend": 0.0, '
    '"weekly_all": 14.0}, "resets_at": {"extra_usage": null, '
    '"five_hour": "2026-11-24T19:59:59.589030+00:00", '
    '"session": "2026-11-24T19:59:59.589030+00:00", '
    '"seven_day": "2026-12-01T10:59:59.589056+00:00", "spend": null, '
    '"weekly_all": "2026-12-01T10:59:59.589056+00:00"}, '
    '"ts": "2026-11-25T03:43:19+08:00"}',
    '{"bd": null, "fp": ["account=eaf5241f6fe2", "extra_usage", "five_hour", "session", '
    '"seven_day", "spend", "weekly_all"], "live": 2, "pct": {"extra_usage": 0.0, '
    '"five_hour": 87.0, "session": 87.0, "seven_day": 15.0, "spend": 0.0, '
    '"weekly_all": 15.0}, "resets_at": {"extra_usage": null, '
    '"five_hour": "2026-11-24T20:00:00.546902+00:00", '
    '"session": "2026-11-24T20:00:00.546902+00:00", '
    '"seven_day": "2026-12-01T11:00:00.546927+00:00", "spend": null, '
    '"weekly_all": "2026-12-01T11:00:00.546927+00:00"}, '
    '"ts": "2026-11-25T03:46:19+08:00"}',
    '{"bd": null, "fp": ["account=eaf5241f6fe2", "extra_usage", "five_hour", "session", '
    '"seven_day", "spend", "weekly_all"], "live": 0, "pct": {"extra_usage": 0.0, '
    '"five_hour": 0.0, "session": 0.0, "seven_day": 16.0, "spend": 0.0, '
    '"weekly_all": 16.0}, "resets_at": {"extra_usage": null, '
    '"five_hour": "2026-11-25T01:00:00.683250+00:00", '
    '"session": "2026-11-25T01:00:00.683250+00:00", '
    '"seven_day": "2026-12-01T11:00:00.683273+00:00", "spend": null, '
    '"weekly_all": "2026-12-01T11:00:00.683273+00:00"}, '
    '"ts": "2026-11-25T04:00:32+08:00"}',
])


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
        bare = _rule(_state(_axis("five_hour", 90, None), _week(10)))
        self.assertEqual((bare.action, bare.win), (QR.NODISPATCH, None),
                         "短窗讀數 ≥ prepare 而 reset 缺：不得因軸被濾掉而落 CONTINUE（F-07）")
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
        meter = SimpleNamespace(SCHEMA=quota_gate.quota_schema(),
                                measure_detail=lambda _t: calls.append(1) or (None, "http-429"),
                                write_cache=lambda *_a: True,
                                read_retry_hint=lambda _p: "600")
        self.enterContext(mock.patch.object(quota_gate, "quota_meter", meter))
        ruling_io.gather(sid)
        ruling_io.gather(sid)
        self.assertEqual(len(calls), 1, "halt 有效時仍須補量一次；同 TTL 內不補第二次")

    def test_429_degrades_to_capped_continue(self):
        """AC-QV-03b：429（帶 retry-after）⇒ CONTINUE deg=unmeasured、1 ≤ cap ≤ cap_prepare。"""
        self._cache(30, age=900)
        meter = SimpleNamespace(SCHEMA=quota_gate.quota_schema(),
                                measure_detail=lambda _t: (None, "http-429"),
                                write_cache=lambda *_a: True, read_retry_hint=lambda _p: "600")
        self.enterContext(mock.patch.object(quota_gate, "quota_meter", meter))
        now = datetime.now().astimezone()
        r = ruling_io.gather("", now=now).ruling
        self.assertEqual((r.action, r.degraded), (QR.CONTINUE, True))
        self.assertTrue(1 <= r.cap <= POLICY.cap_prepare)
        self.assertGreater(datetime.fromisoformat(r.expires_at), now + timedelta(seconds=590))


SID = "11111111-2222-4333-8444-555555555555"


def _live_state(pct, reset_min, now):
    """以真實牆鐘為準的短窗讀數（派工閘、取數內部用 `datetime.now()`）。"""
    return _state(_axis("five_hour", pct, reset_min, now=now),
                  _axis("seven_day", 10, 6000, now=now), now=now)


def _traces(root: Path) -> list[dict]:
    rows = []
    for path in root.rglob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


class ConsumerTest(_Fenced):
    """消費端改接（QVD §3.5 C1、C3、C10、C13、C14、C21；§4 有效期）。"""

    def _gate(self, state, tool="Agent"):
        """真 `quota_gate.quota_gate()`＋hook 端要注入的 `session_brief_oi.dispatch_rule`（C1）。"""
        import session_brief_oi  # noqa: PLC0415

        seen = {}

        def rule(*a):
            seen["verdict"] = session_brief_oi.dispatch_rule(*a)
            return seen["verdict"]

        def floor(decision, _now):
            seen["cap"] = decision.cap

        payload = {"tool_name": tool, "hook_event_name": "PreToolUse", "session_id": SID,
                   "transcript_path": str(self.tmp / f"{SID}.jsonl")}
        err = __import__("io").StringIO()
        with mock.patch.object(quota_gate, "read_quota", lambda *_a, **_k: state), \
                mock.patch.object(quota_gate, "fanout_ledger_path", lambda: self.tmp / "fan"), \
                mock.patch.object(quota_gate.quota_rush, "log_floor", floor), \
                mock.patch("sys.stderr", err):
            rc = quota_gate.quota_gate(
                payload, blocking=("Agent", "Task", "Workflow"), latch_read=lambda _p: set(),
                latch_write=lambda *_a: None, plan_writer=lambda *_a, **_k: None,
                waker=lambda *_a, **_k: {}, event="PreToolUse", rule=rule)
        return rc, err.getvalue(), seen

    def test_gate_and_line_share_cap(self):
        """AC-QV-01g 後半：
        PreToolUse 記派發帳所用的 cap＝同一時刻判決行 `cap=`（C1 經 hook 注入縫）。"""
        now = datetime.now().astimezone()
        rc, _err, seen = self._gate(_live_state(40, 150, now))
        self.assertEqual(rc, 0)
        self.assertEqual(seen["verdict"].action, QR.CONTINUE)
        self.assertEqual(seen["cap"], seen["verdict"].cap)
        self.assertIn(f" cap={seen['cap']} ", QR.head(seen["verdict"]))

    def test_gate_blocks_on_any_non_continue_verdict(self):
        """C1：判決非 CONTINUE ⇒ 擋展開型派工（rc 2），訊息附判決行；致動器只此一處（C2 退役）。
        注入縫組判決失敗 ⇒ `None` ⇒ 退回既有 band 判讀（不崩潰、halt 帶照舊擋）。"""
        now = datetime.now().astimezone()
        rc, err, seen = self._gate(_live_state(87, 14, now))
        self.assertEqual((rc, seen["verdict"].action), (2, QR.WAIT_RESET))
        self.assertIn("QUOTA_VERDICT=WAIT_RESET", err)
        import session_brief_oi  # noqa: PLC0415
        with mock.patch.object(ruling_io, "rule_from_decision", side_effect=RuntimeError("x")):
            self.assertIsNone(session_brief_oi.dispatch_rule(None, None, now, {}, None))

    def test_consumers_print_verdict_first(self):
        """AC-QV-02b：交接包、watch、park、SessionStart 簡報、`--pace` 的第一個額度行皆為判決行。"""
        import session_brief  # noqa: PLC0415

        from lib.sessionctl import handoff_build, park_reset, watch_wake  # noqa: PLC0415
        now = datetime.now().astimezone()
        state = _live_state(87, 14, now)
        text = handoff_build._quota_text(now, lambda _n: state, SID)  # noqa: SLF001
        first = text.splitlines()[0]
        self.assertTrue(first.startswith(QR.PREFIX), first)
        keys = watch_wake.quota_keys(SID, None, {}, now.timestamp(), read_quota=lambda _n: state)
        self.assertTrue(keys and keys[0][5].startswith(QR.PREFIX), keys)
        err = __import__("io").StringIO()
        with mock.patch("sys.stderr", err):
            park_reset.resolve(SimpleNamespace(next_est=None, at=None), SID,
                               {"quota": lambda _n: state}, now)
        self.assertTrue(err.getvalue().splitlines()[1].startswith(QR.PREFIX), err.getvalue())
        snap = ruling_io.current(SID, None, {}, now, read_quota=lambda _n: state)
        self.assertTrue(session_brief.quota_line(lambda: snap).startswith("額度判決：" + QR.PREFIX))
        with mock.patch.object(quota_gate, "pace_state", lambda _n: state):
            pace = ruling_io.pace_report(now=now)
        self.assertTrue(pace.startswith(QR.PREFIX), pace[:120])

    def test_stale_verdict_recomputed(self):
        """AC-QV-02c／MU-QV-16：過期判決行（舊 vid 為 PARK）⇒ 重算為 CONTINUE、落
        `stale_verdict_recomputed`；未過期 ⇒ 不重算。"""
        now = datetime.now().astimezone()
        old = _rule(_state(_short(95, 120)))
        self.assertEqual(old.action, QR.PARK)
        with mock.patch.object(quota_gate, "pace_state", lambda _n: _live_state(0, 200, now)):
            fields, fresh = ruling_io.fresh_or_recompute(QR.line(old), now)
        self.assertEqual((fields["action"], fresh.action), (QR.CONTINUE, QR.CONTINUE))
        rows = [r for r in _traces(self.tmp / "traces")
                if r.get("event") == "stale_verdict_recomputed"]
        self.assertEqual([r.get("old_vid") for r in rows], [old.vid])
        live = _rule(_state(_short(95, 120), now=now), now=now)
        self.assertIsNone(ruling_io.fresh_or_recompute(QR.line(live), now)[1])

    @staticmethod
    def _plan_quota(r, **kw):
        from lib.sessionctl import switchplan  # noqa: PLC0415
        return switchplan.Quota(action=r.action, win=r.win, wk=r.wk, vid=r.vid, **kw)

    def test_switchplan_wait_reset_never_parks(self):
        """AC-QV-12a：E2 讀數（87%、D=14、stage free）⇒ WAIT_RESET ⇒ STAY wait_reset、keepwarm。"""
        from lib.sessionctl import switchplan  # noqa: PLC0415
        r = _rule(_state(_short(87, 14)), plan=qw_plan.Plan("free"))
        got = switchplan.decide(switchplan.Inputs(quota=self._plan_quota(r, wait_min=14)))
        self.assertEqual((got.action, got.flags.keepwarm), ("STAY", True))
        self.assertIn("wait_reset", got.reason)

    def test_switchplan_maps_ruling_actions(self):
        """AC-QV-12b：PARK⇒PARK_UNTIL(win)／D>6h⇒PARK_POLL；HALT_WEEKLY⇒PARK_POLL(wk)；spend⇒STAY；
        CONTINUE／NODISPATCH／None 不由額度列命中；credential 為真不重出 PARK（R-06）；
        判讀欄已退役。"""
        from lib.sessionctl import switchplan  # noqa: PLC0415
        A, inp = switchplan.Action, switchplan.Inputs

        def d(q):
            return switchplan.decide(inp(quota=q))
        park_r = _rule(_state(_short(92, 90), _week(10)), plan=qw_plan.Plan("close"))
        self.assertEqual(park_r.action, QR.PARK)
        got = d(self._plan_quota(park_r, wait_min=90))
        self.assertEqual((got.action, got.target), (A.PARK_UNTIL, park_r.win))
        self.assertEqual(d(self._plan_quota(park_r, wait_min=7 * 60)).action, A.PARK_POLL)
        self.assertEqual(d(self._plan_quota(park_r, wait_min=90, credential=True)).action, A.STAY)
        wk = _rule(_state(_short(10), _week(100)))
        got = d(self._plan_quota(wk))
        self.assertEqual((got.action, got.target), (A.PARK_POLL, wk.wk))
        self.assertEqual(d(self._plan_quota(wk, credential=True)).action, A.STAY)
        spend = _rule(_state(_short(10), _axis("spend", 100, None)))
        self.assertEqual(d(self._plan_quota(spend)).reason, "spend_limit")
        for r in (_rule(_state(_short(10), _week(80))),
                  _rule(_state(_short(40)), plan=qw_plan.Plan("nodispatch"))):
            self.assertNotIn(d(self._plan_quota(r)).action, (A.PARK_UNTIL, A.PARK_POLL))
        self.assertNotIn(d(switchplan.Quota(action=None)).action, (A.PARK_UNTIL, A.PARK_POLL))
        names = {f.name for f in __import__("dataclasses").fields(switchplan.Quota)}
        self.assertFalse(names & {"short_pct", "weekly_pct", "prepare_pct", "stage"})

    def _early(self, state, ruling, marker=None):
        from lib.sessionctl import parkearly, parkprobe  # noqa: PLC0415
        marker = marker or {parkprobe.MK_PARKED_PCT: 92.0, "route": "H"}
        fired = []
        snap = SimpleNamespace(state=state, ruling=ruling)
        with mock.patch.object(parkearly, "_sid", lambda _a: SID), \
                mock.patch.object(parkearly.park, "read_marker", lambda _s: marker), \
                mock.patch.object(parkearly, "_precheck", lambda *_a: ""), \
                mock.patch.object(parkearly, "_primary_handles", lambda *_a: False), \
                mock.patch.object(parkearly, "_live_driver", lambda *_a: False), \
                mock.patch("lib.sessionctl.park_reset.ruling_for", lambda *_a, **_k: snap), \
                mock.patch.object(parkearly, "fire_early",
                                  lambda *_a: fired.append(1) or "fired"):
            verdict = parkearly.tick(SimpleNamespace(), NOW, {}, env={})
        return verdict, len(fired)

    def test_parkearly_respects_park_ruling(self):
        """AC-QV-13a／MU-QV-29：基準 92、當下 80（< prepare、低 12pp）但 stage close ⇒ 判決 PARK ⇒
        不呼叫 `fire_early`（縫計數 0）、痕跡 `park_early_probe` 帶 `action=PARK`。"""
        from lib.sessionctl import parkprobe  # noqa: PLC0415
        state = _state(_short(80, 120))
        r = _rule(state, plan=qw_plan.Plan("close"))
        self.assertEqual(r.action, QR.PARK)
        verdict, fired = self._early(state, r)
        self.assertEqual((verdict["action"], verdict["recovered"], fired), (QR.PARK, False, 0))
        rows = [x for x in _traces(self.tmp / "traces") if x.get("event") == parkprobe.EV_PROBE]
        self.assertEqual(rows[-1]["action"], QR.PARK)
        zero = _state(_short(0, 120))
        self.assertEqual(self._early(zero, _rule(zero))[1], 1, "判決 CONTINUE 且大降 ⇒ 恰一次")

    def test_parkearly_fires_only_on_continue_with_drop(self):
        """AC-QV-13b／MU-QV-30：CONTINUE 且降 ≥5pp ⇒ recovered；只降 3pp ⇒ 否（遲滯閘保留）；
        CONTINUE deg=unmeasured ⇒ 否；`parkprobe.evaluate` 原始碼不再引用 `prepare_pct`。"""
        from lib.sessionctl import parkprobe  # noqa: PLC0415
        marker = {parkprobe.MK_PARKED_PCT: 50.0}
        for cur, want in ((44.0, True), (47.0, False)):
            state = _state(_short(cur, 120))
            r = _rule(state)
            self.assertEqual(r.action, QR.CONTINUE)
            self.assertIs(parkprobe.evaluate(marker, state, r, NOW)["recovered"], want, cur)
        degraded = SimpleNamespace(action=QR.CONTINUE, degraded=True, vid="x")
        self.assertFalse(parkprobe.evaluate(marker, _state(_short(10, 120)), degraded,
                                            NOW)["recovered"])
        src = Path(parkprobe.__file__).read_text(encoding="utf-8")
        fn = next(n for n in ast.parse(src).body
                  if isinstance(n, ast.FunctionDef) and n.name == "evaluate")
        self.assertNotIn("prepare_pct", ast.get_source_segment(src, fn))


class ParkTest(_Fenced):
    """park 前置（QVD §3.5 C6、§5；REQ-AP-QV-04）。"""

    def _resolve(self, state, *, next_est=None, plan=None):
        from lib.sessionctl import park_reset  # noqa: PLC0415
        S = {"quota": lambda _n: state}
        if plan is not None:
            S["plan"] = lambda *_a, **_k: plan
        err = __import__("io").StringIO()
        with mock.patch("sys.stderr", err):
            got = park_reset.resolve(SimpleNamespace(next_est=next_est, at=None), SID, S, NOW)
        return got, err.getvalue()

    def test_continue_refuses_and_why_retired(self):
        """AC-QV-04a／MU-QV-5：判決 CONTINUE ⇒ rc 4 並印判決行；
        傳 `--why` ⇒ 拒絕並指路 `--next-est`。"""
        from lib.sessionctl import park_cli  # noqa: PLC0415
        (_r, _a, _s, rc), err = self._resolve(_state(_short(40, 150)))
        self.assertEqual(rc, 4)
        self.assertIn("QUOTA_VERDICT=CONTINUE", err)
        buf = __import__("io").StringIO()
        with mock.patch("sys.stderr", buf):
            rc = park_cli.run(["--session-id", SID, "--why", "下一棒放不下要先停工"], env={})
        self.assertEqual(rc, 2)
        self.assertIn("--next-est", buf.getvalue())

    def test_next_est_drives_park_or_wait(self):
        """AC-QV-04b／MU-QV-10：`--next-est` ≥ R−V 且 D>45 ⇒ PARK（回 reset＝win）；D≤45 ⇒
        WAIT_RESET 不登記；`next_est` < R−V（且缺省下界也小於）⇒ CONTINUE。"""
        plan = qw_plan.Plan("free", r=40.0, v=5.0, n_live=0)
        (reset, _a, _s, rc), _err = self._resolve(_state(_short(60, 120)), next_est=36.0,
                                                  plan=plan)
        self.assertEqual(rc, 0)
        self.assertEqual(reset, datetime.fromisoformat(_iso(NOW + timedelta(minutes=120))))
        (_r, _a, _s, rc), err = self._resolve(_state(_short(60, 14)), next_est=36.0, plan=plan)
        self.assertEqual(rc, 4)
        self.assertIn("判決 WAIT_RESET", err)
        (_r, _a, _s, rc), err = self._resolve(_state(_short(60, 120)), next_est=1.0, plan=plan)
        self.assertEqual(rc, 4)
        self.assertIn("判決 CONTINUE", err)

    def test_park_messages_match_verdict(self):
        """AC-QV-04c／MU-QV-11：拒絕文案的動作與判決行一致、不含 `--why`；短窗 reset 量不到 ⇒
        NODISPATCH 而非 PARK。"""
        cases = ((_state(_short(87, 14)), QR.WAIT_RESET), (_state(_short(40, 150)), QR.CONTINUE),
                 (_state(_axis("five_hour", 92, None), _week(10)), QR.NODISPATCH))
        for state, action in cases:
            with self.subTest(action=action):
                (_r, _a, _s, rc), err = self._resolve(state)
                self.assertEqual(rc, 4)
                self.assertIn(f"判決 {action}", err)
                self.assertEqual(QR.parse(err)["action"], action)
                self.assertNotIn("--why", err)

    def test_next_est_default_and_floor(self):
        """AC-QV-04d／MU-QV-18：缺省＝`cal_agent × max(1, n_plan)`；給的值低於缺省 ⇒ 取缺省。"""
        from lib.sessionctl import qw_calc  # noqa: PLC0415
        agent = qw_calc.AGENT_EST_DEFAULT_PP
        self.assertEqual(ruling_io.default_next_est(SimpleNamespace(n_live=3), {}), agent * 3)
        self.assertEqual(ruling_io.default_next_est(SimpleNamespace(n_live=0), {}), agent)
        plan = qw_plan.Plan("free", r=agent * 2 + 5.0, v=5.0, n_live=2)  # R−V＝2×cal_agent
        (_r, _a, _s, rc), _err = self._resolve(_state(_short(60, 120)), next_est=0.5, plan=plan)
        self.assertEqual(rc, 0, "給的 0.5pp 低於缺省 2×cal_agent ⇒ 取缺省 ⇒ 放不下 ⇒ PARK")


class WatchTest(_Fenced):
    """watch 額度事件（QVD §3.5 C4／C5；REQ-AP-QV-05）。"""

    def test_single_series_latch(self):
        """AC-QV-05a／MU-QV-2：單一序列鍵 `(acct, ACTION, win)`；同鍵只觸發一次；末行欄位。"""
        from lib.sessionctl import keepwarm, watch_wake  # noqa: PLC0415
        now = datetime.now().astimezone()
        state = _live_state(87, 14, now)
        keys = watch_wake.quota_keys(SID, None, {}, now.timestamp(), read_quota=lambda _n: state)
        self.assertEqual(len(keys), 1)
        self.assertEqual((keys[0][0], keys[0][2]), (QR.WAIT_RESET, "eaf5241f6fe2"))
        self.assertEqual(len(watch_wake.fire_hits(SID, keys, 0)), 1)
        self.assertEqual(watch_wake.fire_hits(SID, keys, 0), [], "同鍵第二次不觸發")
        tail = watch_wake.verdict_tail(keys)
        self.assertRegex(tail, r"^ action=WAIT_RESET vid=[0-9a-f]{8} expires_at=\S+$")
        self.assertFalse(hasattr(keepwarm, "SERIES"))

    def test_wait_reset_disposition_has_no_park(self):
        """AC-QV-05b：`WAIT_RESET` 處置列不含 park；`keepwarm.SERIES` 不存在。"""
        from lib.sessionctl import keepwarm, watch_wake  # noqa: PLC0415
        self.assertNotIn("park", watch_wake.quota_disposal(QR.WAIT_RESET).lower())
        self.assertIn("park", watch_wake.quota_disposal(QR.PARK))
        self.assertFalse(hasattr(keepwarm, "SERIES"))


class RulingWaitResetTest(_Fenced):
    """WAIT_RESET 叫醒載具（QVD §3.6；REQ-AP-QV-11）。"""

    def _transcript(self, ctx=None) -> Path:
        path = self.tmp / f"{SID}.jsonl"
        rows = [{"type": "user", "timestamp": _iso(NOW), "message": {"content": "x"}}]
        if ctx is not None:
            rows.append({"type": "assistant", "timestamp": _iso(NOW), "message": {
                "id": "m1", "usage": {"input_tokens": 1, "cache_read_input_tokens": ctx,
                                      "cache_creation_input_tokens": 0, "output_tokens": 1}}})
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return path

    def _wait(self):
        r = _rule(_state(_short(87, 14)), plan=qw_plan.Plan("free"))
        self.assertEqual(r.action, QR.WAIT_RESET)
        return r

    def test_small_ctx_still_wakes_at_win(self):
        """AC-QV-11a／MU-QV-22：判決 WAIT_RESET、ctx 小 ⇒ `wake_target` 回 `ruling_wait_reset`
        （win＋skew）；small_ctx 只是軟原因，`kind_of` 為單跳。"""
        from lib.sessionctl import keepwarm, kw_wake, qw_calc  # noqa: PLC0415
        r = self._wait()
        at, src, _ref = qw_plan.wake_target(SID, None, {}, NOW, marker=None,
                                            plan_=qw_plan.Plan("free"), ruling=r)
        win = datetime.fromisoformat(r.win).timestamp()
        self.assertEqual((src, at), ("ruling_wait_reset", win + qw_calc.skew_min() * 60))
        env = {"AUTOSDD_SESSION_SWITCH_MODE": "auto"}
        self.assertEqual(keepwarm.skip_reason(SID, env, ctx=10), "small_ctx")
        self.assertNotIn("small_ctx", kw_wake.HARD_SKIPS)
        car = kw_wake.Carrier(SID, None, env, 45.0, 50.0, soft="small_ctx", target=at,
                              source=src, plan=qw_plan.Plan("free", r=13.0))
        self.assertEqual(kw_wake.kind_of(car, NOW.timestamp())[0], "single")

    def test_cap_does_not_block_single_hop(self):
        """AC-QV-11b／MU-QV-23：保溫帳已達 n* 也照單跳（`kind_of` 不看帳；`kw_run` 的 cap 只管
        periodic 無目標者）。"""
        from lib.sessionctl import kw_run, kw_wake  # noqa: PLC0415
        car = kw_wake.Carrier(SID, None, {}, 45.0, 50.0, target=NOW.timestamp() + 900,
                              source="ruling_wait_reset", plan=qw_plan.Plan("free", r=13.0))
        self.assertFalse(car.periodic)
        self.assertEqual(kw_wake.kind_of(car, NOW.timestamp()), ("single", 0, False))
        src = Path(kw_run.__file__).read_text(encoding="utf-8")
        self.assertIn('if car.periodic and row["pings"] >= star:', src)

    def test_unattended_hands_to_sentinel(self):
        """AC-QV-11c／MU-QV-24：無人窗口不掛 keepwarm（硬豁免）；哨兵對 WAIT_RESET 維持撞線等待、
        reset＝win。"""
        from lib.sessionctl import keepwarm  # noqa: PLC0415
        self.assertEqual(keepwarm.skip_reason(SID, {"AUTOSDD_UNATTENDED": "1"}, ctx=10**6),
                         "unattended")
        self.assertIn(QR.WAIT_RESET, ruling_io.SENTINEL_WAIT_ACTIONS)
        r = self._wait()
        snap = SimpleNamespace(ruling=r)
        # 哨兵巡邏只讀快取（零 token、零子行程）⇒ 注入點是 `cached`，不是會補量的 `gather`
        with mock.patch.object(ruling_io, "cached", lambda *_a, **_k: snap), \
                mock.patch.object(ruling_io.qg, "read_halt_marker", lambda _sid: None):
            halt = ruling_io.sentinel_halt(SID, None, NOW, {"AUTOSDD_UNATTENDED": "1"})
            self.assertIsNone(ruling_io.sentinel_halt(SID, None, NOW, {}),
                              "互動窗口的 WAIT_RESET 由 keepwarm 叫醒，不交哨兵")
        self.assertEqual((halt["reset_at"], halt["ruling"]), (r.win, QR.WAIT_RESET))

    def test_no_carrier_is_said(self):
        """AC-QV-11d 前半：模式非 auto 或 `AUTOSDD_KEEPWARM_OFF` ⇒ 理由句寫「不會在重置後自動叫醒」
        。"""
        for env in ({"AUTOSDD_SESSION_SWITCH_MODE": "notify"}, {"AUTOSDD_KEEPWARM_OFF": "1"}):
            with self.subTest(env=env):
                self.assertTrue(ruling_io._no_carrier(env))  # noqa: SLF001
        r = _rule(_state(_short(87, 14)), plan=qw_plan.Plan("free"), no_carrier=True)
        self.assertIn("不會在重置後自動叫醒", r.reason)
        self.assertNotIn(QR.NO_CARRIER_NOTE, self._wait().reason)

    def _stop(self, tasks, *, ruling=None, env=None, ctx=None, **extra):
        from lib.sessionctl import keepwarm  # noqa: PLC0415
        payload = {"session_id": SID, "transcript_path": str(self._transcript(ctx)),
                   "background_tasks": tasks, **extra}
        r = ruling or self._wait()
        return keepwarm.stop_verdict(payload, env or {"AUTOSDD_SESSION_SWITCH_MODE": "auto"},
                                     NOW, ruling_fn=lambda _s, _t: r)

    def test_stop_pushes_keepwarm_on_wait_reset_despite_small_ctx(self):
        """AC-QV-11e／MU-QV-34～36：WAIT_RESET＋小上下文＋無 running ⇒ 推回（含 `keepwarm --sid`
        與判決行）；no_usage、pings ≥ n*、只有 watch 在跑也推；有 running keepwarm ⇒ 不推；
        `stop_hook_active` ⇒ 不推；`park.stop_verdict` 對同一讀數回空（C7）。"""
        from lib.sessionctl import keepwarm, park  # noqa: PLC0415
        why = self._stop([], ctx=5000)
        self.assertIn("keepwarm --sid", why)
        self.assertIn("QUOTA_VERDICT=WAIT_RESET", why)
        self.assertTrue(self._stop([], ctx=None))
        with mock.patch.object(keepwarm, "load_ledger", lambda *_a: {"pings": 999}):
            self.assertTrue(self._stop([], ctx=5000))
        watch_task = {"type": "shell", "status": "running",
                      "command": f"python tools/sessionctl.py watch --sid {SID}"}
        self.assertTrue(self._stop([watch_task], ctx=5000))
        kw_task = {"type": "shell", "status": "running",
                   "command": f"python tools/sessionctl.py keepwarm --sid {SID}"}
        self.assertEqual(self._stop([kw_task], ctx=5000), "")
        self.assertEqual(self._stop([], ctx=5000, stop_hook_active=True), "")
        now = datetime.now().astimezone()
        self.assertEqual(park.stop_verdict(
            {"session_id": SID}, {"AUTOSDD_SESSION_SWITCH_MODE": "auto"}, now=now,
            read_quota=lambda _n: _live_state(87, 14, now), carrier_fn=lambda: True,
            spawned_fn=lambda _s, _e: False), "")

    def test_stop_first_four_still_exempt(self):
        """AC-QV-11f／MU-QV-37：前四項（無人／模式非 auto／保溫關閉／已交棒）仍豁免；判決非
        WAIT_RESET ⇒ 回原判準（小上下文不推）。"""
        from lib.sessionctl import keepwarm  # noqa: PLC0415
        for env in ({"AUTOSDD_UNATTENDED": "1"}, {"AUTOSDD_SESSION_SWITCH_MODE": "notify"},
                    {"AUTOSDD_SESSION_SWITCH_MODE": "auto", "AUTOSDD_KEEPWARM_OFF": "1"}):
            with self.subTest(env=env):
                self.assertEqual(self._stop([], env=env, ctx=5000), "")
        with mock.patch.object(keepwarm.seal, "handed_over", lambda *_a: "x"):
            self.assertEqual(self._stop([], ctx=5000), "")
        cont = _rule(_state(_short(40, 150)))
        self.assertEqual(self._stop([], ruling=cont, ctx=5000), "")


class QuotaCliE2ETest(_Fenced):
    """E2E-AP-QV-01／07（真行程 `python tools/sessionctl.py quota`；
    sid 406454ea 03:46 錄製讀數以時間平移
    重放：短窗 87%、reset＝now＋14 分；舊帳號 `34cd3507237f` 的 halt 標記原樣放進沙盒）。
    子行程繼承本類
    圍籬（快取／痕跡／TEMP／`CLAUDE_CONFIG_DIR` 皆在 tmp），不讀真快取、不拿真憑證線上補量。"""

    OLD, NEW = "34cd3507237f", "eaf5241f6fe2"

    def _cache(self, axes, *, account=NEW, posture=None):
        now = datetime.now().astimezone()
        body = {"schema": quota_gate.quota_schema(), "source": "endpoint",
                "measured_at": _iso(now), "account_key": account,
                "axes": [{"kind": k, "pct": p, "resets_at": _iso(now + timedelta(minutes=m))}
                         for k, p, m in axes]}
        if posture is not None:
            body["posture"] = posture
        path = quota_gate.quota_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body), encoding="utf-8")

    def _cli(self, *argv) -> tuple[int, str]:
        import subprocess  # noqa: PLC0415
        env = {k: v for k, v in os.environ.items()
               if k not in ("AUTOSDD_UNATTENDED", "CLAUDE_CODE_SESSION_ID")}
        done = subprocess.run([sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"),
                               "quota", *argv], capture_output=True, text=True, encoding="utf-8",
                              env=env, timeout=120, cwd=str(self.tmp))
        return done.returncode, done.stdout + done.stderr

    def test_e2e_ap_qv_01_time_shifted_replay(self):
        """E2E-AP-QV-01：平移到「reset＝now＋14 分」⇒ `WAIT_RESET acct=eaf5241f6fe2`；
        平移到「reset 已過、
        0%」⇒ `CONTINUE acct=eaf5241f6fe2`；舊帳號 halt 標記不當輸入、兩次皆無 halted 行。"""
        now = datetime.now().astimezone()
        quota_gate.write_halt_marker(SID, {"sid": SID, "binding": "five_hour", "at": _iso(now),
                                           "reset_at": _iso(now + timedelta(minutes=30)),
                                           "account": self.OLD})
        self._cache([("five_hour", 87.0, 14), ("session", 87.0, 14), ("seven_day", 15.0, 9000)])
        rc, out = self._cli("--sid", SID)
        self.assertEqual(rc, 0, out)
        fields = QR.parse(out)
        self.assertEqual((fields["action"], fields["acct"]), (QR.WAIT_RESET, self.NEW), out)
        self.assertTrue(out.startswith(QR.PREFIX), out)
        self.assertNotIn("halted", out)
        self._cache([("five_hour", 0.0, 300), ("session", 0.0, 300), ("seven_day", 16.0, 9000)])
        rc, out = self._cli("--json", "--sid", SID)
        self.assertEqual(rc, 0, out)
        got = json.loads(out.strip().splitlines()[-1])
        self.assertEqual((got["action"], got["acct"], got["deg"]), (QR.CONTINUE, self.NEW, None))
        self.assertNotIn("halted", out)

    def test_e2e_ap_qv_07_billing_and_unmeasured(self):
        """E2E-AP-QV-07：三種錄製快取（缺 posture、無 credits、credits 可用）的 `billing`；
        快取缺席且
        憑證量不到（`CLAUDE_CONFIG_DIR` 圍在 tmp）⇒ `CONTINUE deg=unmeasured`、
        `1 ≤ cap ≤ cap_prepare`、
        `expires_at > now`（不是 cap 0、也不是不設限）。"""
        axes = [("five_hour", 30.0, 200), ("seven_day", 10.0, 9000)]
        for posture, want in ((None, "unknown"), ({"credits_present": False}, "subscription_only"),
                              ({"credits_present": True, "fallback_available": True},
                               "credits_fallback")):
            with self.subTest(billing=want):
                self._cache(axes, posture=posture)
                rc, out = self._cli("--json")
                self.assertEqual(rc, 0, out)
                self.assertEqual(json.loads(out.strip().splitlines()[-1])["billing"], want)
        quota_gate.quota_cache_path().unlink()
        before = datetime.now().astimezone()
        rc, out = self._cli("--json")
        self.assertEqual(rc, 0, out)
        got = json.loads(out.strip().splitlines()[-1])
        self.assertEqual((got["action"], got["deg"]), (QR.CONTINUE, QR.DEG_UNMEASURED), out)
        self.assertTrue(1 <= got["cap"] <= POLICY.cap_prepare, got)
        self.assertGreater(datetime.fromisoformat(got["expires_at"]), before)


class SingleHouseLockE2ETest(unittest.TestCase):
    """E2E-AP-QV-10：沙盒 repo 副本（`tools/lib`、`tools/*.py`、本測試檔）植入一個私有判讀站點，
    真子行程
    跑 `SingleHouseTest.test_sites_equal_allowlist` ⇒ rc≠0 且訊息列出該站點；移除後 rc 0。"""

    def test_e2e_ap_qv_10_planted_site_turns_the_real_lock_red(self):
        import shutil  # noqa: PLC0415
        import subprocess  # noqa: PLC0415
        root = Path(tempfile.mkdtemp(prefix="qv_e2e10_"))
        self.addCleanup(shutil.rmtree, root, True)
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
        sandbox_lib = root / "tools" / "lib"  # 只寫沙盒（tmp）；真樹只讀
        shutil.copytree(src=_REPO_ROOT.joinpath("tools", "lib"), dst=sandbox_lib, ignore=ignore)
        for path in (_REPO_ROOT / "tools").glob("*.py"):
            shutil.copy2(path, root / "tools" / path.name)
        (root / "tools" / "tests").mkdir()
        shutil.copy2(Path(__file__), root / "tools" / "tests" / Path(__file__).name)
        planted = root / "tools" / "lib" / "zz_private_peek.py"
        planted.write_text("import quota_gate\n\n\ndef peek(now):\n"
                           "    return quota_gate.read_quota(now)\n", encoding="utf-8")

        def run() -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-m", "unittest",
                 f"{Path(__file__).stem}.SingleHouseTest.test_sites_equal_allowlist"],
                capture_output=True, text=True, encoding="utf-8", timeout=300,
                cwd=str(root / "tools" / "tests"), env={**os.environ, "PYTHONPATH": ""})
        red = run()
        self.assertNotEqual(red.returncode, 0, red.stderr[-800:])
        self.assertIn("tools/lib/zz_private_peek.py", red.stderr)
        planted.unlink()
        green = run()
        self.assertEqual(green.returncode, 0, green.stderr[-1500:])


class LocTest(unittest.TestCase):
    def test_pace_report_moved_out_of_hub(self):
        """AC-QV-08b：`pace_report` 不再存在於 `quota_gate`（hub 成員只縮不長）。"""
        self.assertFalse(hasattr(quota_gate, "pace_report"))
        self.assertTrue(callable(ruling_io.pace_report))


# ═════════════════════════════════════════════════ 單一判讀家機械鎖（QVD §3.5.3；REQ-AP-QV-10）
#: (i) 引用站點清單名稱（屬性任何根、名稱解析到模組層綁定）；`decide`／`plan` 為限定名。
LOCK_NAMES = frozenset({"read_quota", "refresh_quota_blocking", "settled_quota", "pace_state",
                        "_pace_state", "default_read", "default_refresh", "prepare_hits",
                        "halt_verdict", "read_halt_marker", "weekly_forces_fresh"})
LOCK_QUAL = {"decide": "quota_policy", "plan": "qw_plan"}
#: B4（量測與重放）、B5（測試）不掃。
LOCK_EXCLUDE = ("tools/probe/", "tools/lib/wastecensus/", "tools/lib/realverify/", "tools/tests/")
#: (ii) 門檻比較：運算元子樹含這兩個屬性名；判決家與政策檔本身不計。
COMPARE_ATTRS = frozenset({"prepare_pct", "halt_pct"})


def _lock_files(root: Path):
    for path in sorted((root / "tools").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if not rel.startswith(LOCK_EXCLUDE):
            yield path, rel
    for path in sorted((root / ".claude" / "hooks").glob("*.py")):
        yield path, path.relative_to(root).as_posix()


def _bindings(tree: ast.Module) -> tuple[dict, dict]:
    """`(名稱→(實名, 來源模組末段))`、`(別名→模組末段)`；本模組頂層 def 記 `<self>`。"""
    bind, alias = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                bind[a.asname or a.name] = (a.name, (node.module or "").split(".")[-1])
                alias[a.asname or a.name] = a.name
        elif isinstance(node, ast.Import):
            for a in node.names:
                alias[a.asname or a.name.split(".")[0]] = a.name.split(".")[-1]
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bind.setdefault(node.name, (node.name, "<self>"))
    return bind, alias


def scan_source(text: str, rel: str) -> set[tuple[str, str, str]]:
    """(i) 引用站點三元組 `(檔, 最外層 def｜<module>, 引用名稱)`。參數／區域同名不收（QVD 不算條）
    。"""
    tree = ast.parse(text)
    bind, alias = _bindings(tree)
    hits: set[tuple[str, str, str]] = set()

    def visit(node, outer):
        for ch in ast.iter_child_nodes(node):
            o = ch.name if (isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and outer == "<module>") else outer
            if isinstance(ch, ast.Attribute) and isinstance(ch.ctx, ast.Load):
                v = ch.value
                vn = v.id if isinstance(v, ast.Name) else (v.attr if isinstance(v, ast.Attribute)
                                                           else None)
                real = alias.get(vn, vn) if vn else None
                if ch.attr in LOCK_NAMES or (ch.attr in LOCK_QUAL and real == LOCK_QUAL[ch.attr]):
                    hits.add((rel, o, ch.attr))
            elif isinstance(ch, ast.Name) and isinstance(ch.ctx, ast.Load):
                b = bind.get(ch.id)
                if b and (b[0] in LOCK_NAMES or (b[0] in LOCK_QUAL and b[1] == LOCK_QUAL[b[0]])):
                    hits.add((rel, o, b[0]))
            visit(ch, o)

    visit(tree, "<module>")
    return hits


def compare_source(text: str, rel: str) -> set[tuple[str, str, str]]:
    """(ii) 門檻比較站點 `(檔, 最外層 def, "<compare>")`；
    `quota_policy*.py`／`quota_ruling.py` 不計。"""
    name = rel.rsplit("/", 1)[-1]
    if name.startswith("quota_policy") or name == "quota_ruling.py":
        return set()
    out: set[tuple[str, str, str]] = set()
    for top in ast.parse(text).body:
        outer = top.name if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)) \
            else "<module>"
        for node in ast.walk(top):
            if isinstance(node, ast.Compare) and any(
                    isinstance(x, ast.Attribute) and x.attr in COMPARE_ATTRS
                    for side in (node.left, *node.comparators) for x in ast.walk(side)):
                out.add((rel, outer, "<compare>"))
    return out


def scan_tree(root: Path) -> set[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for path, rel in _lock_files(root):
        out |= scan_source(path.read_text(encoding="utf-8"), rel)
    return out


def compare_sites(root: Path) -> set[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for path, rel in _lock_files(root):
        out |= compare_source(path.read_text(encoding="utf-8"), rel)
    return out

_B1 = "判決管線內部取數／組帶（判決的輸入，不據以行動；QVD §3.5.2 B1）"
_B1W = "包裝入口：只轉手讀數、本身不比門檻（QVD §3.5.2 B1 包裝入口）"
_B1P = "計畫內部取數：計畫是判決輸入 plan（QVD §3.5.2 B1 計畫內部取數）"
_RULING = "判決家本身（ruling_io 取數＋組判決；QVD §3.5.3 白名單定義）"
_QG, _QW = "tools/lib/quota_gate.py", "tools/lib/sessionctl/qw_wall.py"
_RI = "tools/lib/sessionctl/ruling_io.py"
#: 白名單（相等比對；QVD §3.5.3）：三元組 → (分類, WHY)。改白名單＝改 QVD §3.5 同 commit。
RULING_INPUT_SITES: dict[tuple[str, str, str], tuple[str, str]] = {
    ("tools/lib/quota_burndown.py", "issue", "read_quota"): ("B1", "清倉判定內的取數"),
    ("tools/lib/quota_burndown.py", "status", "read_quota"): ("B1", "清倉狀態查詢的取數"),
    ("tools/lib/quota_burndown.py", "status", "decide"): ("B1", "halt 門檻內的清倉判定"),
    ("tools/lib/quota_burndown.py", "_eligible", "<compare>"): ("B1", "清倉判定的門檻比較"),
    ("tools/lib/quota_burndown.py", "_why", "<compare>"): ("B1", "清倉判定的門檻比較"),
    (_QG, "degraded_posture", "decide"): ("B1", _B1),
    (_QG, "dispatch_decision", "decide"): ("B1", "派工閘管線（cap 唯一來源；QVD §3.1）"),
    (_QG, "endpoint_probe_verdict", "read_quota"): ("B1", "L0 零成本探針（只回伺服器事實）"),
    (_QG, "endpoint_probe_verdict", "refresh_quota_blocking"): ("B1", "L0 探針補量一次"),
    (_QG, "pace_state", "read_quota"): ("B1", _B1),
    (_QG, "pace_state", "settled_quota"): ("B1", _B1),
    (_QG, "settled_quota", "read_quota"): ("B1", _B1),
    (_QG, "quota_gate", "read_quota"): ("B1", "C1 取數部分（動作改依注入判決）"),
    (_QG, "quota_gate", "refresh_quota_blocking"): ("B1", "C1 取數部分（單一補量站點）"),
    (_QG, "quota_gate", "settled_quota"): ("B1", "C1 取數部分（等贏家重讀）"),
    (_QG, "draining", "read_quota"): ("B6", "壓縮可否（非五類決定）"),
    (_QG, "draining", "decide"): ("B6", "壓縮可否（非五類決定）"),
    (_QG, "compact_margin_breached", "<compare>"): ("B6", "壓縮成本是否推過 DRAIN 線"),
    ("tools/lib/resume_cost.py", "five_hour_reading", "read_quota"): ("B2", "續跑選路成本"),
    ("tools/lib/resume_route.py", "weekly_why", "read_quota"): ("B2", "續跑選路成本"),
    ("tools/lib/resume_route.py", "weekly_why", "weekly_forces_fresh"): ("B2", "續跑選路成本"),
    ("tools/lib/sessionctl/modelmix.py", "pace_line", "read_quota"): ("B3", "模型平衡建議"),
    ("tools/sessionctl.py", "_advice", "read_quota"): ("B3", "模型平衡建議（advice 動詞）"),
    ("tools/lib/sessionctl/park.py", "_pace_state", "pace_state"): ("B1", _B1W),
    (_QW, "default_read", "_pace_state"): ("B1", _B1W),
    (_QW, "default_refresh", "settled_quota"): ("B1", _B1W),
    (_QW, "fresh_reading", "default_read"): ("B1", _B1P),
    (_QW, "fresh_reading", "default_refresh"): ("B1", _B1P),
    (_QW, "wall_state", "default_read"): ("B1", _B1P),
    (_QW, "_quota_reset", "default_read"): ("B1", _B1P),
    ("tools/lib/sessionctl/park_cli.py", "_cmd_done", "pace_state"): ("B7", "--done 的時限上限"),
    ("tools/lib/sessionctl/parkprobe.py", "baseline", "_pace_state"): ("B8", "park 基準記錄"),
    ("tools/lib/sessionctl/switchfacts.py", "account_changed", "_pace_state"):
        ("B8", "只取 account_key 判帳號換了沒"),
    ("tools/lib/sessionctl/watch.py", "run", "plan"):
        ("diag", "watch plan_fn：只取 d_min 決定下一次 tick；判決另取"),
    ("tools/lib/sessionctl/kw_wake.py", "_measure", "plan"):
        ("diag", "保溫 ping 時刻與 wake_target；五類由叫醒後判決重算"),
    ("tools/lib/sessionctl/kw_wake.py", "_measure", "read_quota"):
        ("diag", "同上鏈：注入縫轉手給計畫"),
    ("tools/lib/sessionctl/watch_wake.py", "start", "read_quota"):
        ("diag", "WakeCtl.start 把注入的取數縫轉手給 kw_wake.begin"),
    ("tools/lib/sessionctl/switchfacts.py", "quota_facts", "plan"):
        ("diag", "只取 d_min／stale 供輪詢形態"),
    ("tools/lib/sessionctl/qw_cli.py", "cli", "plan"): ("diag", "計畫細節診斷段（首行判決行）"),
    ("tools/lib/sessionctl/qw_cli.py", "pace_line", "plan"): ("diag", "--pace 的 QW 診斷行"),
    (_RI, "compose", "plan"): ("ruling", _RULING),
    (_RI, "compose", "read_halt_marker"): ("ruling", _RULING),
    (_RI, "gather", "pace_state"): ("ruling", _RULING),
    (_RI, "gather", "refresh_quota_blocking"): ("ruling", "換帳號觸發後 TTL 名額內補量（QVD §7.1）"),
    (_RI, "gather", "settled_quota"): ("ruling", "同上：補量後等贏家重讀（QVD §7.1）"),
    (_RI, "cached", "read_quota"): ("ruling", "只讀快取的判決（C10 簡報、手動排程時刻；零網路）"),
    (_RI, "pace_report", "decide"): ("ruling", "引擎配速契約（pace 尺；診斷段，判斷看首行）"),
    (_RI, "pace_report", "read_halt_marker"): ("ruling", "halted 行（只在 HALT_WEEKLY 同帳號）"),
    (_RI, "sentinel_halt", "read_halt_marker"): ("ruling", "C11 哨兵 halt 輸入"),
    (_RI, "sentinel_halt_verdict", "halt_verdict"): ("ruling", "C11 哨兵 halt 判讀"),
    (_RI, "check_halted_line", "read_halt_marker"): ("ruling", "C3 --check halted 行"),
}
#: 尚未改接（改接後本表必須縮、相等比對保證不得漏刪）。WP-QV 第三棒：C10 SessionStart 簡報與手動
#: 排程時刻已改接（判決經 `session_brief_oi.ruling_of` 注入，hook 不需改），本表清空、常數保留作
#: 「日後分段改接」的唯一登記處。白名單之外另列，
#: `test_allowlist_entries_have_category_and_why` 排除。
PENDING_REWIRE: dict[tuple[str, str, str], str] = {}
#: QVD §3.5.3〈預期命中站點清單〉「改接後白名單＝是」的（檔::函式）；
#: dispatch_decision 為 §3.5.2 B1。
QVD_EXPECTED = frozenset({
    "tools/lib/quota_burndown.py::issue", "tools/lib/quota_burndown.py::status",
    "tools/lib/quota_burndown.py::_eligible", "tools/lib/quota_burndown.py::_why",
    f"{_QG}::degraded_posture", f"{_QG}::draining", f"{_QG}::endpoint_probe_verdict",
    f"{_QG}::pace_state", f"{_QG}::settled_quota", f"{_QG}::quota_gate",
    f"{_QG}::dispatch_decision", f"{_QG}::compact_margin_breached",
    "tools/lib/resume_cost.py::five_hour_reading", "tools/lib/resume_route.py::weekly_why",
    "tools/lib/sessionctl/kw_wake.py::_measure", "tools/lib/sessionctl/modelmix.py::pace_line",
    "tools/sessionctl.py::_advice", "tools/lib/sessionctl/park.py::_pace_state",
    "tools/lib/sessionctl/park_cli.py::_cmd_done", "tools/lib/sessionctl/parkprobe.py::baseline",
    "tools/lib/sessionctl/qw_cli.py::cli", "tools/lib/sessionctl/qw_cli.py::pace_line",
    f"{_QW}::default_read", f"{_QW}::default_refresh", f"{_QW}::fresh_reading",
    f"{_QW}::wall_state", f"{_QW}::_quota_reset",
    "tools/lib/sessionctl/switchfacts.py::quota_facts",
    "tools/lib/sessionctl/switchfacts.py::account_changed", "tools/lib/sessionctl/watch.py::run",
    "tools/lib/sessionctl/watch_wake.py::start"})
_FLAT_LIB = _REPO_ROOT / "tools" / "lib"


def _synthetic(files: dict[str, str]) -> Path:
    root = Path(tempfile.mkdtemp(prefix="qv_lock_"))
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


class SingleHouseTest(unittest.TestCase):
    """REQ-AP-QV-10：單一判讀家機械鎖（QVD §3.5.3）。"""

    def test_sites_equal_allowlist(self):
        """AC-QV-10a：真樹的 (i)∪(ii) 站點＝白名單∪待改接（相等比對：多一處、少一處皆紅）。"""
        got = scan_tree(_REPO_ROOT) | compare_sites(_REPO_ROOT)
        want = set(RULING_INPUT_SITES) | set(PENDING_REWIRE)
        self.assertEqual(sorted(got - want), [], "新增私有判讀站點（改讀判決，或先改 QVD §3.5）")
        self.assertEqual(sorted(want - got), [], "白名單有站點而樹上已無（同 commit 刪白名單項）")

    def test_lock_discriminates(self):
        """AC-QV-10b：多一個私有站點紅；別名 import 仍可認；白名單多一個不存在站點紅。"""
        src = ("import quota_gate as qg\nfrom quota_gate import read_quota as rq\n\n"
               "def peek(now):\n    return qg.read_quota(now)\n\n"
               "def alias(now):\n    return rq(now)\n")
        got = scan_source(src, "tools/lib/x.py")
        self.assertIn(("tools/lib/x.py", "peek", "read_quota"), got)
        self.assertIn(("tools/lib/x.py", "alias", "read_quota"), got)
        root = _synthetic({"tools/lib/y.py": src})
        self.assertTrue(scan_tree(root) - set(RULING_INPUT_SITES), "合成私有站點沒被看見")
        ghost = {**RULING_INPUT_SITES, ("tools/lib/none.py", "f", "read_quota"): ("B1", "x")}
        self.assertTrue(set(ghost) - scan_tree(_REPO_ROOT) - compare_sites(_REPO_ROOT))

    def test_wrapper_entry_sites_are_seen(self):
        """AC-QV-10d 前半：以包裝入口取數（`park._pace_state`、`quota_gate.pace_state`、
        `settled_quota`、`qw_wall.default_read`）各一次都紅並列出檔＋函式。"""
        for call in ("park._pace_state(now)", "quota_gate.pace_state(now)",
                     "quota_gate.settled_quota(True)", "qw_wall.default_read(now)"):
            src = f"def f(now):\n    return {call}\n"
            got = scan_source(src, "tools/lib/w.py")
            self.assertEqual({(s[0], s[1]) for s in got}, {("tools/lib/w.py", "f")}, call)

    def test_seam_references_are_seen(self):
        """AC-QV-10d 縫形與反例、粒度（v1.3，R-01）。"""
        seam = scan_source('def f(S, now):\n    return (S.get("quota") or park._pace_state)(now)\n',
                           "a.py")
        self.assertEqual(seam, {("a.py", "f", "_pace_state")})
        ref = scan_source("def g(now):\n    fn = quota_gate.pace_state\n    return fn(now)\n",
                          "a.py")
        self.assertEqual(ref, {("a.py", "g", "pace_state")})
        bound = scan_source("from lib.sessionctl.qw_wall import default_read\n\n"
                            "def f(read_quota=None, now=None):\n"
                            "    return (read_quota or default_read)(now)\n", "a.py")
        self.assertEqual(bound, {("a.py", "f", "default_read")})
        self.assertEqual(scan_source("def g(read_quota=None):\n"
                                     "    return h(read_quota=read_quota)\n", "a.py"), set(),
                         "參數同名轉手不得計入")
        self.assertEqual(scan_source('def g():\n    return getattr(quota_gate, "read_quota")\n',
                                     "a.py"), set(), "getattr 字串取用照實劃界為不計")
        two = scan_source("import quota_policy\n\ndef f(now):\n    quota_gate.read_quota(now)\n"
                          "    quota_gate.read_quota(now)\n    return quota_policy.decide(1)\n",
                          "a.py")
        self.assertEqual(two, {("a.py", "f", "read_quota"), ("a.py", "f", "decide")},
                         "同名稱多處引用不新增站點；新名稱＝新三元組")

    def test_threshold_compare_sites_are_seen(self):
        """AC-QV-10e：`if axis.pct >= policy.prepare_pct:` 紅；
        寫在 quota_policy*／quota_ruling 不計。"""
        src = "def f(axis, policy):\n    if axis.pct >= policy.prepare_pct:\n        return 1\n"
        self.assertEqual(compare_source(src, "tools/lib/z.py"), {("tools/lib/z.py", "f",
                                                                  "<compare>")})
        self.assertEqual(compare_source(src, "tools/lib/quota_policy_x.py"), set())
        self.assertEqual(compare_source(src, "tools/lib/quota_ruling.py"), set())

    def test_flat_files_do_not_import_sessionctl(self):
        """AC-QV-10c：判讀相關扁平檔（QVD §8 點名的四支＋`quota_*` 族）不 import `lib.sessionctl`
        （AST）。誠實劃界：`sentinel_lifecycle.py`／`session_brief_oi.py` 在 WP-QV 之前即以函式內
        lazy import 取 sessionctl（非判讀用途），不在本鎖射程，已交主控裁示（交卷報告〈規格偏離〉）
        。"""
        bad = []
        names = {"quota_gate.py", "session_brief.py", "quota_escalation.py", "relay_machine.py"}
        for path in sorted(_FLAT_LIB.glob("*.py")):
            if path.name not in names and not path.name.startswith("quota_"):
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                mods = ([a.name for a in node.names] if isinstance(node, ast.Import) else
                        [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
                bad += [f"{path.name}:{m}" for m in mods if "sessionctl" in m]
        self.assertEqual(bad, [])

    def test_allowlist_entries_have_category_and_why(self):
        """AC-QV-10f：每項帶分類與非空 WHY；diag 恰為五處；與 QVD 預期表逐列相符（待改接另列）。"""
        cats = {"B1", "B2", "B3", "B6", "B7", "B8", "ruling", "diag"}
        for key, (cat, why) in RULING_INPUT_SITES.items():
            self.assertIn(cat, cats, key)
            self.assertTrue(why.strip(), key)
        diag = {k[0].rsplit("/", 1)[-1].replace(".py", "") for k, v in RULING_INPUT_SITES.items()
                if v[0] == "diag"}
        self.assertEqual(diag, {"watch", "kw_wake", "watch_wake", "switchfacts", "qw_cli"})
        pairs = {f"{k[0]}::{k[1]}" for k, v in RULING_INPUT_SITES.items() if v[0] != "ruling"}
        self.assertEqual(pairs, set(QVD_EXPECTED))
        self.assertTrue(all(why.strip() for why in PENDING_REWIRE.values()))

if __name__ == "__main__":
    unittest.main()
