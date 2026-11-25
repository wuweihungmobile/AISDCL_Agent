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
    """(i) 引用站點三元組 `(檔, 最外層 def｜<module>, 引用名稱)`。參數／區域同名不收（QVD 不算條）。"""
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
    """(ii) 門檻比較站點 `(檔, 最外層 def, "<compare>")`；`quota_policy*.py`／`quota_ruling.py` 不計。"""
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
    (_RI, "pace_report", "decide"): ("ruling", "引擎配速契約（pace 尺；診斷段，判斷看首行）"),
    (_RI, "pace_report", "read_halt_marker"): ("ruling", "halted 行（只在 HALT_WEEKLY 同帳號）"),
    (_RI, "sentinel_halt", "read_halt_marker"): ("ruling", "C11 哨兵 halt 輸入"),
    (_RI, "sentinel_halt_verdict", "halt_verdict"): ("ruling", "C11 哨兵 halt 判讀"),
    (_RI, "check_halted_line", "read_halt_marker"): ("ruling", "C3 --check halted 行"),
}
#: 尚未改接（WP-QV 交卷照實列出；改接後本表必須縮、相等比對保證不得漏刪）：QVD C10 SessionStart
#: 簡報需 SessionStart hook 注入判決（守衛面，WP-HOOK 親套；本包產 diff），簡報函式與其 25 支測試
#: 同 commit 改。白名單之外另列，`test_allowlist_entries_have_category_and_why` 對 QVD 表逐列比對時排除。
PENDING_REWIRE: dict[tuple[str, str, str], str] = {
    ("tools/lib/session_brief.py", "quota_line", "read_quota"): "C10：待 WP-HOOK 注入判決",
    ("tools/lib/session_brief.py", "quota_line", "decide"): "C10：待 WP-HOOK 注入判決",
    ("tools/lib/session_brief.py", "schtasks_trigger", "read_quota"): "C10：待同批改接",
    ("tools/lib/session_brief.py", "schtasks_trigger", "decide"): "C10：待同批改接",
}
#: QVD §3.5.3〈預期命中站點清單〉「改接後白名單＝是」的（檔::函式）；dispatch_decision 為 §3.5.2 B1。
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
    f"{_QW}::wall_state", f"{_QW}::_quota_reset", "tools/lib/sessionctl/switchfacts.py::quota_facts",
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
        ref = scan_source("def g(now):\n    fn = quota_gate.pace_state\n    return fn(now)\n", "a.py")
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
        """AC-QV-10e：`if axis.pct >= policy.prepare_pct:` 紅；寫在 quota_policy*／quota_ruling 不計。"""
        src = "def f(axis, policy):\n    if axis.pct >= policy.prepare_pct:\n        return 1\n"
        self.assertEqual(compare_source(src, "tools/lib/z.py"), {("tools/lib/z.py", "f",
                                                                  "<compare>")})
        self.assertEqual(compare_source(src, "tools/lib/quota_policy_x.py"), set())
        self.assertEqual(compare_source(src, "tools/lib/quota_ruling.py"), set())

    def test_flat_files_do_not_import_sessionctl(self):
        """AC-QV-10c：判讀相關扁平檔（QVD §8 點名的四支＋`quota_*` 族）不 import `lib.sessionctl`
        （AST）。誠實劃界：`sentinel_lifecycle.py`／`session_brief_oi.py` 在 WP-QV 之前即以函式內
        lazy import 取 sessionctl（非判讀用途），不在本鎖射程，已交主控裁示（交卷報告〈規格偏離〉）。"""
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
