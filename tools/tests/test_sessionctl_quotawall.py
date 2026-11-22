"""tools/lib/sessionctl/quotawall.py（含 qw_calc／qw_wall／qw_plan／qw_latch／qw_verdict／
qw_matrix）
與 tools/lib/sessionctl/qw_schema.py：R218 QuotaWall Q1 判準核心（TCS-QuotaWall AT-QW-01～16、20、
21、36、60～62、66、70、76～78；MU-QW-01、02、12、30、40、43、45、46、47、49）。

縫：假時鐘（`NOW` 注入）、`read_quota`／`refresh` 注入、tmp 逐字稿、`AUTOSDD_TRACE_DIR` 圍到暫存；
不開任何測試用環境變數、不 monkeypatch 被測判準（AT-QW-04 替換的是常數的「家」：
`quota_messages`／`quota_gate`／`keepwarm`／`watch`）。
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_gate  # noqa: E402
import quota_messages  # noqa: E402
import quota_policy  # noqa: E402
import quota_policy_env  # noqa: E402

from lib.sessionctl import (  # noqa: E402
    handoff,
    holder,
    keepwarm,
    park,
    quotawall,
    qw_calc,
    qw_matrix,
    qw_schema,
    qw_wall,
    seal,
    watch,
)

SID = "6c1d2e3f-8a41-4c1d-9d0e-3a52c1d8e911"
NOW = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC)
MIN = 60.0


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def _state(pct: float, reset_min: float = 150, *, age_sec: float = 0, kind: str = "five_hour",
           extra=()):
    """`Q`：伺服器原值的短窗讀數；`reset_min`＝距 NOW 的分鐘；`age_sec`＝讀數年齡。"""
    axes = (quota_policy.Axis(kind, pct, _iso(NOW.timestamp() + reset_min * 60)), *extra)
    return quota_policy.QuotaState(axes, _iso(NOW.timestamp() - age_sec), "test")


def _reader(state):
    return lambda _now: state


def _write_transcript(path: Path, ctx: int = 200_000, extra=()) -> Path:
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    rows = [{"type": "assistant", "timestamp": _iso(NOW.timestamp() - 600),
             "message": {"id": "m1", "usage": usage}}, *extra]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


class _Base(unittest.TestCase):
    """tmp 痕跡目錄＋tmp 逐字稿；不碰真 `~/.autosdd`。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tmp / "trace"),
                                               "AUTOSDD_HANDOFF_DIR": str(self.tmp / "handoff")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ("AUTOSDD_UNATTENDED", "AUTOSDD_QUOTAWALL_OFF", "AUTOSDD_SESSION_SWITCH_MODE"):
            os.environ.pop(key, None)
        self.env: dict = {}
        self.transcript = _write_transcript(self.tmp / "t.jsonl")

    def plan(self, pct, reset_min=150, **kw):
        env = {**self.env, **kw.pop("env", {})}
        return quotawall.plan(SID, self.transcript, env, NOW,
                              read_quota=_reader(kw.pop("state", None) or _state(pct, reset_min)),
                              ledger=kw.pop("ledger", {}), **kw)


# ═════════════════════════════════════════════════════════════ plan 階段與數值
class PlanStageTest(_Base):
    """tools/lib/sessionctl/qw_plan.py：階段邊界（AT-QW-01；MU-QW-01、02）。"""

    def test_stage_boundaries_c200k_d150(self):
        """c＝20 萬、D＝150 ⇒ k＝3、V＝7.5、L＝12.5；等號邊界含（R ≤ V 為 close）。"""
        for r, stage in ((13, "free"), (12.5, "nodispatch"), (8, "nodispatch"), (7.5, "close")):
            with self.subTest(r=r):
                p = self.plan(100 - r)
                self.assertEqual((p.stage, p.k, round(p.v, 2), round(p.limit, 2)),
                                 (stage, 3, 7.5, 12.5))

    def test_wall_beats_everything_at_100(self):
        """讀數 100 ⇒ `wall`（source=quota），不是 close。"""
        p = self.plan(100)
        self.assertEqual((p.stage, p.wall["source"]), ("wall", "quota"))

    def test_none_reasons_are_distinct(self):
        """量不到／reset 不明／無人窗口／mode=off ⇒ 皆 none，reason 各異（AT-QW-02）。"""
        no_reset = quota_policy.QuotaState((quota_policy.Axis("five_hour", 50, None),),
                                           _iso(NOW.timestamp()), "t")
        cases = {
            "unmeasured": dict(state=quota_policy.QuotaState((), _iso(NOW.timestamp()), "t")),
            "no_reset": dict(state=no_reset),
            "unattended": dict(env={"AUTOSDD_UNATTENDED": "1"}),
            "mode_off": dict(env={"AUTOSDD_SESSION_SWITCH_MODE": "off"}),
        }
        reasons = set()
        for want, kw in cases.items():
            with self.subTest(want=want):
                p = self.plan(50, **kw)
                self.assertEqual((p.stage, p.reason), ("none", want))
                reasons.add(p.reason)
        self.assertEqual(len(reasons), 4)

    def test_notify_mode_still_plans(self):
        """notify 模式照算階段（只是不擋）。"""
        self.assertEqual(self.plan(93, env={"AUTOSDD_SESSION_SWITCH_MODE": "notify"}).stage,
                         "close")

    def test_weekly_axis_alone_never_changes_the_stage(self):
        """週軸 99％、五小時 40％ ⇒ free；只有模型分軌 99％ 亦然（AT-QW-12、MU-QW-12）。"""
        week = quota_policy.Axis("seven_day", 99,
                                 _iso(NOW.timestamp() + 5 * 86400))
        opus = quota_policy.Axis("seven_day_opus", 99, _iso(NOW.timestamp() + 5 * 86400))
        self.assertEqual(self.plan(40, state=_state(40, extra=(week,))).stage, "free")
        self.assertEqual(self.plan(40, state=_state(40, extra=(opus,))).stage, "free")
        only_week = quota_policy.QuotaState((week,), _iso(NOW.timestamp()), "t")
        self.assertEqual(self.plan(0, state=only_week).stage, "none")

    def test_pace_floor_and_rush_never_leak_in(self):
        """階段只看短窗原始讀數：配速床墊高、趕工戳記無影響（AT-QW-13；不 import decide）。"""
        src = (_REPO_ROOT / "tools/lib/sessionctl")
        for name in ("qw_plan.py", "qw_wall.py", "qw_calc.py", "qw_verdict.py"):
            tree = ast.parse((src / name).read_text(encoding="utf-8"))
            used = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | {
                n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            self.assertFalse({"decide", "pace_floor", "quota_pace_floor", "quota_rush"} & used,
                             name)
        self.assertEqual(self.plan(40).stage, "free")

    def test_exception_in_reader_is_fail_open(self):
        """讀數函式拋例外 ⇒ none、`pretool_verdict`＝(0,"")（AT-QW-11）。"""
        def boom(_now):
            raise RuntimeError("x")
        p = quotawall.plan(SID, self.transcript, self.env, NOW, read_quota=boom, ledger={})
        self.assertEqual(p.stage, "none")
        payload = {"tool_name": "Agent", "session_id": SID, "tool_input": {}}
        self.assertEqual(quotawall.pretool_verdict(payload, self.env, NOW, read_quota=boom,
                                                   ledger={}), (0, ""))


class KTableTest(_Base):
    """tools/lib/sessionctl/qw_calc.py：k(D)、V(k)、L 與常數的家（AT-QW-03～05、08；MU-QW-02）。"""

    def test_k_by_d(self):
        want = {0: 0, 48: 0, 49: 1, 93: 1, 94: 2, 224: 4, 251: 5, 300: 6}
        for d, k in want.items():
            with self.subTest(d=d):
                self.assertEqual(quotawall.k_of(d, 200_000, {}), k)

    def test_small_context_is_k0_and_v6(self):
        """c＝2 萬（< MIN_CTX）、D＝150 ⇒ k＝0、V＝6。"""
        _write_transcript(self.transcript, 20_000)
        p = self.plan(88)
        self.assertEqual((p.k, round(p.v, 2)), (0, 6.0))

    def test_v_and_l_per_k(self):
        want = {0: 6, 1: 6.5, 2: 7, 3: 7.5, 4: 8, 5: 8.5, 6: 9}
        for k, v in want.items():
            with self.subTest(k=k):
                got = quotawall.v_of(k, 0.5, 1.0)
                self.assertAlmostEqual(got, v)
                self.assertAlmostEqual(got + qw_calc.AGENT_EST_DEFAULT_PP, v + 5)

    def test_constants_live_in_their_homes(self):
        """AT-QW-04：換掉 skew／T_kw／TTL 的家 ⇒ k、V 隨之變，沒有複寫常數。"""
        with mock.patch.object(quota_messages, "HALT_RESET_SKEW_SECONDS", 300):
            self.assertEqual(quotawall.k_of(46, 200_000, {}), 1)   # (46+5-50)/45 → 1
        with mock.patch.object(keepwarm, "t_kw_minutes", lambda env=None: 30.0):
            self.assertEqual(quotawall.k_of(150, 200_000, {}), 4)  # (150+2-50)/30 → 4
        with mock.patch.object(quota_gate, "QUOTA_CACHE_TTL_SECONDS", 60):
            self.assertEqual(qw_calc.detect_min(), 2)              # ceil(90/60)
        self.assertEqual(qw_calc.detect_min(), 4)
        self.assertEqual(quotawall.IDLE_LIMIT_MIN, 50)
        self.assertEqual(quotawall.W_CLOSE, 4)

    def test_watch_poll_is_read_from_its_home(self):
        with mock.patch.object(watch, "POLL_SECONDS", 150):
            self.assertEqual(qw_calc.detect_min(), 6)  # ceil((180+150)/60)


class InvariantTest(_Base):
    """invariant 以 V 判（AT-QW-06、REQ-QW-04）。"""

    def test_broken_when_v_reaches_prepare_gap(self):
        env = {qw_calc.KEY_BURN: "2.875"}  # V＝7.5＋4×2.875＝19 ⇒ ≥ 15
        buf = io.StringIO()
        with redirect_stderr(buf):
            p = self.plan(80, env=env)
        self.assertEqual(p.invariant, "broken")
        self.assertEqual(buf.getvalue().count("invariant=broken"), 1)
        self.assertIn(p.stage, ("close", "nodispatch", "free"))  # 判準照算
        self.assertIn("invariant=broken", quotawall.plan_lines(p)[-1])

    def test_l_over_gap_but_v_under_is_not_broken(self):
        env = {qw_calc.KEY_AGENT: "8.5"}  # L＝16、V＝7.5
        buf = io.StringIO()
        with redirect_stderr(buf):
            p = self.plan(80, env=env)
        self.assertEqual((p.invariant, round(p.limit, 1)), ("ok", 16.0))
        self.assertNotIn("invariant=broken", buf.getvalue())


class PingPpTest(_Base):
    """ping_pp 縮放與校準（AT-QW-07、62；MU-QW-30）。"""

    def test_scaled_values(self):
        want = {0: 0.5, 200_000: 0.5, 230_000: 0.5, 300_000: 0.639, 430_000: 0.896,
                600_000: 1.233}
        for ctx, pp in want.items():
            with self.subTest(ctx=ctx):
                got, cal = quotawall.ping_pp(ctx, {})
                self.assertAlmostEqual(got, pp, places=2)
                self.assertFalse(cal)
                self.assertGreaterEqual(got, 0.5)

    def test_proportional_to_p_above_c_ref(self):
        """c ≥ 23 萬時 ping_pp/p(c) 為常數（拿掉縮放＝MU-QW-30）。"""
        ratios = {quotawall.ping_pp(c, {})[0] / qw_calc.p_of(c)
                  for c in (250_000, 309_000, 480_000, 700_000)}
        self.assertEqual(len({round(x, 12) for x in ratios}), 1)

    def test_calibration_keys(self):
        ctx = 309_000
        self.assertAlmostEqual(quotawall.ping_pp(ctx, {})[0], 0.656, places=3)
        got, cal = quotawall.ping_pp(ctx, {qw_calc.KEY_PP: "0.02"})
        self.assertTrue(cal)
        self.assertAlmostEqual(got, qw_calc.p_of(ctx) / 1000 * 0.02)
        for bad in ("-1", "0", "nan", "inf", "x"):
            buf = io.StringIO()
            with self.subTest(bad=bad), redirect_stderr(buf):
                got, cal = quotawall.ping_pp(ctx, {qw_calc.KEY_PP: bad})
            self.assertFalse(cal)
            self.assertAlmostEqual(got, 0.656, places=3)
            self.assertIn(qw_calc.KEY_PP, buf.getvalue())

    def test_env_spec_declares_the_three_keys_and_env_example_matches(self):
        names = {v.name for v in quota_policy_env.ENV_SPEC}
        keys = {qw_calc.KEY_PP, qw_calc.KEY_BURN, qw_calc.KEY_AGENT}
        self.assertTrue(keys <= names)
        example = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        for key in keys:
            self.assertEqual(sum(1 for ln in example.splitlines() if ln.startswith(key + "=")), 1)


class PlanSeamsTest(_Base):
    """tools/lib/sessionctl/qw_plan.py：S-25 ping_pp_eff、S-23 讀數年齡（AT-QW-76；MU-QW-45）。"""

    def test_measured_mean_only_raises(self):
        """實測近 3 筆平均較大 ⇒ 用實測；較小 ⇒ 仍用縮放（只抬不降；MU-QW-49 取 min 即紅）。"""
        hi = self.plan(88, ledger={qw_schema.LEDGER_PING_COSTS: [0.9, 1.0, 1.1]})
        self.assertEqual((hi.ping_pp_src, round(hi.ping_pp, 2)), ("measured", 1.0))
        lo = self.plan(88, ledger={qw_schema.LEDGER_PING_COSTS: [0.1, 0.2, 0.3]})
        self.assertEqual((lo.ping_pp_src, lo.ping_pp), ("scaled", 0.5))

    def test_stale_reading_triggers_one_refresh(self):
        calls = []

        def refresh(_now):
            calls.append(1)
            return _state(95)
        p = self.plan(0, state=_state(86, age_sec=15 * 60), refresh=refresh)
        self.assertEqual((p.stage, p.stale, len(calls)), ("close", False, 1))

    def test_refresh_failure_extrapolates_conservatively(self):
        def refresh(_now):
            raise OSError("down")
        p = self.plan(0, state=_state(86, age_sec=300), refresh=refresh)
        self.assertEqual((p.stage, p.stale, p.reading_age), ("nodispatch", True, 300))
        self.assertAlmostEqual(p.r, 14 - 5)  # R_eff＝14 − ceil(300/60)×burn
        self.assertIn("stale=yes reading_age=300", quotawall.plan_lines(p)[-1])

    def test_fresh_reading_is_not_refreshed(self):
        calls = []
        p = self.plan(0, state=_state(86, age_sec=180), refresh=lambda n: calls.append(1))
        self.assertEqual((p.stage, p.stale, calls), ("free", False, []))

    def test_dead_window_reading_is_unmeasured(self):
        def refresh(_now):
            raise OSError("down")
        p = self.plan(0, state=_state(86, reset_min=-10), refresh=refresh)
        self.assertEqual((p.stage, p.reason), ("none", "stale_window"))
        payload = {"tool_name": "Agent", "session_id": SID, "tool_input": {}}
        self.assertEqual(quotawall.pretool_verdict(payload, {}, NOW,
                                                   read_quota=_reader(_state(86, reset_min=-10)),
                                                   refresh=refresh, ledger={}), (0, ""))

    def test_refresh_only_old_by_age_not_by_dead_window(self):
        """補量後讀到新窗 ⇒ 用新值（舊快取的 reset 已過、補量成功）。"""
        p = self.plan(0, state=_state(86, reset_min=-10), refresh=lambda n: _state(30))
        self.assertEqual(p.stage, "free")


# ═════════════════════════════════════════════════════════════ wall_state
class WallStateTest(_Base):
    """tools/lib/sessionctl/qw_wall.py：三條件（AT-QW-09、10；REQ-QW-05）。"""

    def _cut(self, tail: list[dict]) -> Path:
        cut_at = NOW.timestamp() - 300
        rows = [{"type": "system", "timestamp": _iso(cut_at),
                 "content": "5-hour limit reached · continuing automatically at 3:00pm"}, *tail]
        _write_transcript(self.transcript, extra=rows)
        return self.transcript

    def test_cut_without_resume_is_wall_with_cold_at(self):
        path = self._cut([])
        got = quotawall.wall_state(path, NOW, read_quota=_reader(None))
        self.assertEqual((got["wall"], got["source"]), (True, "cut"))
        self.assertEqual(got["cold_at"], keepwarm.anchor(path) + qw_wall.CACHE_LIFE_SEC)

    def test_cut_followed_by_real_usage_is_not_wall(self):
        usage = {"input_tokens": 1, "cache_read_input_tokens": 9, "output_tokens": 1}
        path = self._cut([{"type": "assistant", "timestamp": _iso(NOW.timestamp() - 100),
                           "message": {"id": "m2", "usage": usage}}])
        self.assertFalse(quotawall.wall_state(path, NOW, read_quota=_reader(None))["wall"])

    def test_cut_followed_by_auto_continuation_is_not_wall(self):
        path = self._cut([{"type": "user", "timestamp": _iso(NOW.timestamp() - 100),
                           "origin": {"kind": "auto-continuation"},
                           "message": {"role": "user", "content": "go"}}])
        self.assertFalse(quotawall.wall_state(path, NOW, read_quota=_reader(None))["wall"])

    def test_synthetic_limit_record_is_wall(self):
        row = {"type": "assistant", "timestamp": _iso(NOW.timestamp() - 30),
               "message": {"model": "<synthetic>",
                           "content": [{"type": "text", "text": "You've hit your usage limit"}]}}
        _write_transcript(self.transcript, extra=[row])
        got = quotawall.wall_state(self.transcript, NOW, read_quota=_reader(None))
        self.assertEqual((got["wall"], got["source"]), (True, "synthetic"))

    def test_quota_100_with_future_reset_is_wall(self):
        got = quotawall.wall_state(self.transcript, NOW, read_quota=_reader(_state(100, 40)))
        self.assertEqual((got["wall"], got["source"]), (True, "quota"))
        self.assertEqual(got["reset"], NOW.timestamp() + 40 * 60)

    def test_quota_100_with_dead_reset_is_not_wall(self):
        self.assertFalse(quotawall.wall_state(self.transcript, NOW,
                                              read_quota=_reader(_state(100, -5)))["wall"])

    def test_missing_transcript_and_errors_are_not_wall(self):
        self.assertFalse(quotawall.wall_state(None, NOW, read_quota=_reader(None))["wall"])

        def boom(_n):
            raise RuntimeError("x")
        self.assertFalse(quotawall.wall_state(self.tmp / "none.jsonl", NOW,
                                              read_quota=boom)["wall"])


# ═════════════════════════════════════════════════════════════ 判決
class VerdictTest(_Base):
    """tools/lib/sessionctl/qw_verdict.py（AT-QW-14～16；MU-QW-14）。"""

    def payload(self, **extra):
        return {"tool_name": "Agent", "session_id": SID, "transcript_path": str(self.transcript),
                "tool_input": {"prompt": "x"}, **extra}

    def verdict(self, pct, payload=None, env=None, **kw):
        return quotawall.pretool_verdict(payload or self.payload(), env or {}, NOW,
                                         read_quota=_reader(_state(pct)), ledger={}, **kw)

    def test_matrix_of_modes(self):
        """close × auto／notify／off／UNATTENDED／QUOTAWALL_OFF。"""
        self.assertEqual(self.verdict(93)[0], 2)
        rc, msg = self.verdict(93, env={"AUTOSDD_SESSION_SWITCH_MODE": "notify"})
        self.assertEqual(rc, 0)
        self.assertTrue(msg)
        for env in ({"AUTOSDD_SESSION_SWITCH_MODE": "off"}, {"AUTOSDD_UNATTENDED": "1"},
                    {qw_calc.OFF_ENV: "1"}):
            with self.subTest(env=env):
                self.assertEqual(self.verdict(93, env=env), (0, ""))

    def test_dispatch_boundaries(self):
        """R＝13 放行／12.5 擋／7.5 擋（AT-QW-15）。"""
        self.assertEqual(self.verdict(87)[0], 0)
        self.assertEqual(self.verdict(87.5)[0], 2)
        self.assertEqual(self.verdict(93.5)[0], 2)

    def test_non_dispatch_tools_and_subagents_pass(self):
        self.assertEqual(self.verdict(93, payload=self.payload(tool_name="Read")), (0, ""))
        self.assertEqual(self.verdict(93, payload=self.payload(agent_id="a1")), (0, ""))

    def test_escape_phrase_needs_eight_chars_and_is_traced(self):
        ok = self.payload(tool_input={"prompt": "續派理由：補最後一個測試檔案"})
        short = self.payload(tool_input={"prompt": "續派理由：短"})
        self.assertEqual(self.verdict(93, payload=ok), (0, ""))
        trace = Path(os.environ["AUTOSDD_TRACE_DIR"]) / "autosdd_session_switch.jsonl"
        self.assertIn("quotawall_override", trace.read_text(encoding="utf-8"))
        self.assertEqual(self.verdict(93, payload=short)[0], 2)

    def test_escape_ignored_when_unattended(self):
        ok = self.payload(tool_input={"prompt": "續派理由：補最後一個測試檔案"})
        self.assertEqual(self.verdict(93, payload=ok, env={"AUTOSDD_UNATTENDED": "1"}), (0, ""))
        trace = Path(os.environ["AUTOSDD_TRACE_DIR"]) / "autosdd_session_switch.jsonl"
        self.assertFalse(trace.exists() and "quotawall_override" in trace.read_text("utf-8"))

    def test_block_text_carries_facts_and_steps(self):
        msg = self.verdict(93)[1]
        for needle in ("R=", "V=", "L=", "D=", "calibrated=", "TaskStop", "--finalize", "park",
                       "keepwarm"):
            self.assertIn(needle, msg)
        nod = self.verdict(90)[1]
        self.assertIn("不再派新代理", nod)
        self.assertNotIn("--finalize", nod)

    def test_stop_verdict_stage_and_loop_guard(self):
        pay = self.payload()
        kw = dict(read_quota=_reader(_state(93)), ledger={})
        self.assertEqual(quotawall.stop_verdict(self.payload(stop_hook_active=True), {}, NOW,
                                                inflight=False, **kw), "")
        self.assertEqual(quotawall.stop_verdict(pay, {}, NOW, inflight=False,
                                                read_quota=_reader(_state(40)), ledger={}), "")
        inflight = quotawall.stop_verdict(pay, {}, NOW, inflight=True, **kw)
        self.assertIn("TaskStop", inflight)
        self.assertNotIn("--finalize", inflight)  # D-D：在飛側不要求先封存
        idle = quotawall.stop_verdict(pay, {}, NOW, inflight=False, **kw)
        for step in ("handoff --build", "--finalize", "park", "keepwarm --sid"):
            self.assertIn(step, idle)

    def test_stop_mute(self):
        pay = self.payload()
        self.assertEqual(quotawall.stop_mute(pay, {}, NOW, read_quota=_reader(_state(100, 40)),
                                             ledger={}), "wall")
        self.assertEqual(quotawall.stop_mute(pay, {}, NOW, read_quota=_reader(_state(93)),
                                             ledger={}), "quota")
        self.assertEqual(quotawall.stop_mute(pay, {}, NOW, read_quota=_reader(_state(40)),
                                             ledger={}), "")
        # QUOTAWALL_OFF：牆中靜音是正確性、照舊；quota 靜音不設
        off = {qw_calc.OFF_ENV: "1"}
        self.assertEqual(quotawall.stop_mute(pay, off, NOW, read_quota=_reader(_state(100, 40)),
                                             ledger={}), "wall")
        self.assertEqual(quotawall.stop_mute(pay, off, NOW, read_quota=_reader(_state(93)),
                                             ledger={}), "")


# ═════════════════════════════════════════════════════════════ wake_target
class WakeTargetTest(_Base):
    """tools/lib/sessionctl/qw_plan.py：目標優先序與 ref（AT-QW-36、REQ-QW-22）。"""

    def _marker(self, *, pkg_state="live", source="reset", status="armed"):
        pkg = self.tmp / "pkg.md"
        pkg.write_text("x", encoding="utf-8")
        if pkg_state == "resumed":
            pkg.with_suffix(".resumed").write_text("", encoding="utf-8")
        valid = _iso(NOW.timestamp() + 7200)
        base = {"schema": "x", "status": status, "valid_until": valid, "pkg": str(pkg),
                "primary_job": "AutoSDD_x", "credential": "c"}
        return {**base, **qw_schema.marker_extra(NOW.timestamp() + 9000, source,
                                                 NOW.timestamp() + 9600, False, None)}

    def target(self, pct, marker, reset_min=150):
        return quotawall.wake_target(SID, self.transcript, {}, NOW, marker=marker,
                                     read_quota=_reader(_state(pct, reset_min)), ledger={})

    def test_priority(self):
        s = qw_calc.skew_min() * 60
        with mock.patch.object(park, "credential_ok", lambda m, n: (True, "ok")):
            at, src, ref = self.target(93, self._marker())
            self.assertEqual((at, src), (NOW.timestamp() + 9000, "park"))
            self.assertEqual(ref[0], NOW.timestamp() + 9000 - s)
            at, src, ref = self.target(93, self._marker(source="at"))
            self.assertEqual((src, ref), ("park", (None, None, None)))
            at, src, ref = self.target(93, self._marker(pkg_state="resumed"))
            self.assertEqual((src, at), ("reset", NOW.timestamp() + 150 * 60 + s))
            self.assertEqual(ref[0], NOW.timestamp() + 150 * 60)
            self.assertEqual(ref[1], 93)
        at, src, ref = self.target(93, None)
        self.assertEqual((src, at is not None), ("reset", True))
        self.assertEqual(self.target(40, None), (None, "none", (None, None, None)))

    def test_wall_with_known_reset_targets_reset_plus_s(self):
        at, src, _ref = self.target(100, None, reset_min=40)
        self.assertEqual((src, at), ("reset", NOW.timestamp() + 40 * 60
                                     + qw_calc.skew_min() * 60))


# ═════════════════════════════════════════════════════════════ schedule／affordable／early_reset
class ScheduleTest(unittest.TestCase):
    """tools/lib/sessionctl/qw_calc.py：schedule 窮舉（AT-QW-20、21；MU-QW-06、47）。"""

    def test_exhaustive_chain_properties(self):
        s_min = 2.0
        for t_kw in (45.0, 30.0, 15.0):
            for idle in (50.0, 20.0):
                reset = 100_000.0
                target = reset + s_min * 60
                for off in range(0, 301):
                    anchor = reset - off * 60
                    d_min = (reset - anchor) / 60
                    k = max(0, -(-int(d_min + s_min - idle) // int(t_kw)))  # 整數 ceil
                    seq = quotawall.schedule(anchor, target, None, True, t_kw, s_min, idle)
                    with self.subTest(t_kw=t_kw, idle=idle, off=off):
                        self.assertEqual(seq[-1], target)
                        self.assertEqual(len(seq) - 1, k)
                        points = [anchor, *seq]
                        gaps = [b - a for a, b in zip(points, points[1:])]
                        self.assertTrue(all(g <= max(t_kw, idle) * 60 + 1e-6 for g in gaps))
                        self.assertTrue(all(g >= 0 for g in gaps))

    def test_no_target_is_r216_deadline(self):
        self.assertEqual(quotawall.schedule(1000.0, None, None, True, 45, 2), [1000.0 + 2700])

    def test_unaffordable_is_a_single_hop(self):
        self.assertEqual(quotawall.schedule(0.0, 9000.0, 3, False, 45, 2), [9000.0])

    def test_choose_mode(self):
        self.assertEqual(quotawall.choose_mode(None, True), "periodic")
        self.assertEqual(quotawall.choose_mode(1.0, True), "chain")
        self.assertEqual(quotawall.choose_mode(1.0, False), "single")


class AffordableTest(unittest.TestCase):
    """tools/lib/sessionctl/qw_calc.py：S-24 只算未來 k（AT-QW-78；MU-QW-47）。"""

    def test_future_k_only(self):
        ctx = 480_000
        n = keepwarm.n_star(ctx)
        pp = quotawall.ping_pp(ctx, {})[0]
        self.assertAlmostEqual(pp, 0.995, places=2)
        self.assertTrue(quotawall.affordable(5, 4, pp, ctx))      # 5 ≥ 3.98 且 4 ≤ n*（pings 不計）
        self.assertGreaterEqual(n, 4)
        self.assertFalse(quotawall.affordable(12, n + 1, pp, ctx))  # 未來 k > n*
        self.assertFalse(quotawall.affordable(3, 4, pp, ctx))       # R < k·pp
        self.assertTrue(quotawall.affordable(0, 0, pp, ctx))        # k＝0 恆真

    def test_k_of_d205_at_480k(self):
        self.assertEqual(quotawall.k_of(205, 480_000, {}), 4)


class EarlyResetAndWindowTest(unittest.TestCase):
    """tools/lib/sessionctl/qw_calc.py::early_reset、qw_latch.same_window（AT-QW-77；MU-QW-46）。"""

    def test_early_reset_conditions(self):
        ref = (1000.0, 89.0, 500.0)
        self.assertTrue(quotawall.early_reset(ref, 1300.0, 30, 600.0))
        self.assertFalse(quotawall.early_reset(ref, 1300.0, 91, 600.0))     # 讀數未降
        self.assertFalse(quotawall.early_reset(ref, 900.0, 30, 600.0))      # reset 沒變晚
        self.assertFalse(quotawall.early_reset(ref, 1300.0, 30, 400.0))     # 舊讀數（S-23⑥）
        self.assertFalse(quotawall.early_reset((None, None, None), 1300.0, 30, 600.0))
        self.assertFalse(quotawall.early_reset(ref, None, 30, 600.0))
        self.assertFalse(quotawall.early_reset(None, 1300.0, 30, 600.0))
        self.assertFalse(quotawall.early_reset((1000.0, 100.0, 500.0), 1300.0, 100, 600.0))

    def test_same_window(self):
        r, t1 = 100_000.0, 90_000.0
        latched = {"reset": r, "pct": 95, "at": t1}
        now = t1 + 10
        self.assertTrue(quotawall.same_window(latched, r, 86, now, t1 - 600))   # 舊讀數不算換窗
        self.assertFalse(quotawall.same_window(latched, r, 86, now, t1 + 60))   # 讀數已降
        self.assertTrue(quotawall.same_window(latched, r + 300, 95, now, t1 + 60))
        self.assertTrue(quotawall.same_window(latched, r + 70 * 60, 95, r + 59 * 60, t1 + 60))
        self.assertFalse(quotawall.same_window(latched, r + 300, 96, r + 61 * 60, t1 + 60))
        self.assertTrue(quotawall.same_window(latched, None, None, now))        # 量不到只看時間
        self.assertFalse(quotawall.same_window(None, r, 90, now))

    def test_reset_precise_value_is_not_the_key(self):
        """MU-QW-40：reset 觀測值漂移 ±5 分、+70 分都不算換窗。"""
        latched = {"reset": 100_000.0, "pct": 94, "at": 90_000.0}
        for drift in (-300, 300, 70 * 60):
            self.assertTrue(quotawall.same_window(latched, 100_000.0 + drift, 94, 90_100.0,
                                                  90_050.0))


# ═════════════════════════════════════════════════════════════ 閂鎖與主載具憑證
class LatchTest(_Base):
    """tools/lib/sessionctl/qw_latch.py：閂鎖與 primary_live（AT-QW-70、REQ-QW-43；MU-QW-40）。"""

    def test_latch_roundtrip_and_new_window(self):
        r, t = NOW.timestamp() + 600, NOW.timestamp()
        self.assertFalse(quotawall.latch_seen(SID, r, 94, t))
        self.assertTrue(quotawall.latch_mark(SID, r, 94, t))
        self.assertTrue(quotawall.latch_seen(SID, r + 300, 94, t + 10))
        self.assertFalse(quotawall.latch_seen(SID, r, 91, t + 10, t + 5))   # 讀數降 ⇒ 新窗
        self.assertFalse(quotawall.latch_seen(SID, r, 96, r + 61 * 60))     # 過 reset＋60 分

    def test_unwritable_latch_never_hides_a_push(self):
        (Path(os.environ["AUTOSDD_TRACE_DIR"])).mkdir(parents=True)
        (Path(os.environ["AUTOSDD_TRACE_DIR"]) / "quotawall").write_text("file", encoding="utf-8")
        self.assertFalse(quotawall.latch_mark(SID, 1.0, 94, 1.0))
        self.assertFalse(quotawall.latch_seen(SID, 1.0, 94, 2.0))

    def test_grace_only_once_per_task(self):
        self.assertTrue(quotawall.latch_grace(SID, "task-1"))
        self.assertFalse(quotawall.latch_grace(SID, "task-1"))
        self.assertTrue(quotawall.latch_grace(SID, "task-2"))

    def _row(self, mode="chain", wake_min=30, pid=4242):
        row = {"schema": holder.SCHEMA, "sid": SID, "pid": pid, "proc_start": "tok"}
        return {**row, **qw_schema.holder_extra(NOW.timestamp() + wake_min * 60, mode, "reset")}

    def _payload(self, running=True):
        task = {"id": "b1", "type": "shell", "status": "running" if running else "done",
                "command": f"python tools/sessionctl.py keepwarm --sid {SID}"}
        return {"session_id": SID, "background_tasks": [task]}

    def live(self, payload, row):
        return quotawall.primary_live(payload, SID, NOW, row=row, alive=lambda p: True,
                                      token=lambda p: "tok")

    def test_primary_live_conditions(self):
        self.assertTrue(self.live(self._payload(), self._row()))
        self.assertTrue(self.live(self._payload(), self._row("single")))
        self.assertFalse(self.live(self._payload(), self._row("periodic")))
        self.assertFalse(self.live(self._payload(), self._row(wake_min=-1)))
        self.assertFalse(self.live(self._payload(False), self._row()))
        self.assertFalse(self.live({"session_id": SID}, self._row()))
        self.assertFalse(self.live(self._payload(), None))
        self.assertFalse(self.live(self._payload(), {"schema": holder.SCHEMA, "sid": SID,
                                                     "pid": 1, "proc_start": "tok"}))  # 舊格式
        self.assertFalse(quotawall.primary_live(self._payload(), SID, NOW, row=self._row(),
                                                alive=lambda p: False, token=lambda p: "tok"))

    def test_stop_pushes_missing_park_once_per_window(self):
        """主載具在跑、只缺 park：第 1 次推、第 2 次（同窗）不推、新窗再推（S-18）。"""
        pay = {**self._payload(), "transcript_path": str(self.transcript)}
        kw = dict(inflight=False, read_quota=_reader(_state(94)), ledger={})
        self.assertTrue(holder.acquire(SID, os.getpid(), extra=qw_schema.holder_extra(
            NOW.timestamp() + 1800, "chain", "reset")))  # 真 holder 檔（tmp 痕跡目錄）＋本行程
        if True:
            first = quotawall.stop_verdict(pay, {}, NOW, **kw)
            self.assertIn("park", first)
            self.assertNotIn("keepwarm --sid", first)  # 主載具已在
            self.assertEqual(quotawall.stop_verdict(pay, {}, NOW, **kw), "")
            self.assertIn("備援缺席", quotawall.absent_notice(
                pay, {}, NOW, read_quota=_reader(_state(94)), ledger={}))
            later = quotawall.stop_verdict(pay, {}, NOW + timedelta(minutes=5), inflight=False,
                                           read_quota=_reader(_state(91, 450, age_sec=-300)),
                                           ledger={})
            self.assertIn("park", later)


# ═════════════════════════════════════════════════════════════ 矩陣
class MatrixTest(unittest.TestCase):
    """tools/lib/sessionctl/qw_matrix.py：續航情境矩陣（AT-QW-60、REQ-QW-61）。"""

    def test_keys_and_cells(self):
        want = {(s, p) for s in qw_matrix.SITUATIONS for p in qw_matrix.PLATFORMS}
        self.assertEqual(set(quotawall.continuity.MATRIX), want)
        for key, cell in quotawall.continuity.MATRIX.items():
            with self.subTest(key=key):
                self.assertEqual(set(cell), {"primary", "backup", "notify"})
                self.assertTrue(all(isinstance(v, str) and v for v in cell.values()))
                for carrier_field in ("primary", "backup"):
                    text = cell[carrier_field]
                    ok = any(c in text for c in qw_matrix.CARRIERS) or text.startswith(
                        qw_matrix.ABSENT)
                    self.assertTrue(ok, text)
                if cell["backup"].startswith(qw_matrix.ABSENT):
                    self.assertIn("OI-", cell["notify"])


# ═════════════════════════════════════════════════════════════ schema／holder／seal
class SchemaTest(unittest.TestCase):
    """tools/lib/sessionctl/qw_schema.py：十一欄名與讀寫函式（REQ-QW-63、AT-QW-66）。"""

    ELEVEN = ("primary_wake_at", "primary_source", "backup_fire_at", "close_stuck_window",
              "desktop_notify", "wake_at", "target_source", "session_switch_spawning",
              "last_ping_pct", "last_ping_at", "ping_costs")

    def test_eleven_names(self):
        consts = {v for k, v in vars(qw_schema).items()
                  if isinstance(v, str) and k.startswith(("MK_", "HOLDER_", "EV_", "LEDGER_"))}
        self.assertTrue(set(self.ELEVEN) <= consts)

    def test_marker_roundtrip(self):
        extra = qw_schema.marker_extra(1_800_000_000.0, "reset", 1_800_000_600.0, True, "1")
        got = qw_schema.marker_primary(extra)
        self.assertEqual((got.wake_at, got.source, got.backup_fire_at, got.close_stuck_window,
                          got.desktop_notify), (1_800_000_000.0, "reset", 1_800_000_600.0, True,
                                                "1"))
        old = qw_schema.marker_primary({"status": "armed"})  # R217 舊標記
        self.assertEqual((old.wake_at, old.source, old.close_stuck_window), (None, None, False))
        self.assertIsNone(qw_schema.marker_primary({"primary_source": "x"}).source)

    def test_holder_roundtrip_and_old_format(self):
        row = qw_schema.holder_extra(1_800_000_000.0, "chain", "park")
        got = qw_schema.holder_wake(row)
        self.assertEqual((got.wake_at, got.mode, got.target_source),
                         (1_800_000_000.0, "chain", "park"))
        self.assertIsNone(qw_schema.holder_wake({"schema": "x"}))
        self.assertIsNone(qw_schema.holder_wake(None))
        junk = qw_schema.holder_wake({"wake_at": "2026-01-01T00:00:00+00:00", "mode": "zz",
                                      "target_source": "zz"})
        self.assertEqual((junk.mode, junk.target_source), (None, None))

    def test_naive_timestamps_are_rejected(self):
        self.assertIsNone(qw_schema.parse_epoch("2026-01-01T00:00:00"))
        self.assertIsNone(qw_schema.parse_epoch("garbage"))
        self.assertIsNotNone(qw_schema.parse_epoch("2026-01-01T00:00:00Z"))

    def test_ping_costs_defensive_read(self):
        self.assertEqual(qw_schema.ping_costs({}), [])
        self.assertEqual(qw_schema.ping_costs(None), [])
        self.assertEqual(qw_schema.ping_costs({"ping_costs": "x"}), [])
        row = {"ping_costs": [1, True, -1, float("inf"), "a", 0.5, 2, 3, 4, 5, 6]}
        self.assertEqual(qw_schema.ping_costs(row), [0.5, 2.0, 3.0, 4.0, 5.0, 6.0][-5:])

    def test_ledger_helpers(self):
        costs = qw_schema.append_cost([1, 2, 3, 4, 5], 6)
        self.assertEqual(costs, [2, 3, 4, 5, 6])
        self.assertEqual(qw_schema.measured_mean(costs), 5.0)
        self.assertIsNone(qw_schema.measured_mean([]))
        led = qw_schema.ledger_extra(90.0, 1_800_000_000.0, costs)
        self.assertEqual(qw_schema.last_ping(led), (90.0, 1_800_000_000.0))
        self.assertIsNone(qw_schema.last_ping(qw_schema.ledger_extra(None, None, [])))
        self.assertIsNone(qw_schema.last_ping({}))

    def test_intent_ttl(self):
        self.assertGreaterEqual(qw_schema.SPAWN_INTENT_TTL_SEC,
                                handoff.SPAWN_WAIT_SECONDS + 30)
        now = 1_800_000_000.0
        self.assertTrue(qw_schema.intent_live(_iso(now - 10), now))
        self.assertTrue(qw_schema.intent_live(_iso(now - qw_schema.SPAWN_INTENT_TTL_SEC), now))
        self.assertFalse(qw_schema.intent_live(_iso(now - 91), now))
        self.assertFalse(qw_schema.intent_live(_iso(now + 5), now))
        self.assertFalse(qw_schema.intent_live("zz", now))

    def test_park_cli_wait_constant_is_covered(self):
        """TTL ≥ park_cli 續跑等待＋30（若該常數存在；park_cli 屬 Q3 持有面，只讀）。"""
        from lib.sessionctl import park_cli  # noqa: PLC0415
        for name in dir(park_cli):
            if name.endswith("WAIT_SECONDS") or name == "RESUME_WAIT_SEC":
                val = getattr(park_cli, name)
                if isinstance(val, (int, float)):
                    self.assertGreaterEqual(qw_schema.SPAWN_INTENT_TTL_SEC, val + 30, name)

    def test_leaf_imports_only_stdlib(self):
        tree = ast.parse((_REPO_ROOT / "tools/lib/sessionctl/qw_schema.py").read_text("utf-8"))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                mods.add((node.module or "").split(".")[0])
        self.assertTrue(mods <= set(sys.stdlib_module_names) | {"__future__"}, mods)


class HolderExtraTest(_Base):
    """tools/lib/sessionctl/holder.py::acquire(extra=)（DES §5.6）。"""

    def test_extra_written_and_rewritable_by_owner(self):
        pid = os.getpid()
        extra = qw_schema.holder_extra(NOW.timestamp() + 1800, "chain", "reset")
        self.assertTrue(holder.acquire(SID, pid, extra=extra))
        row = holder.read(SID)
        self.assertEqual(qw_schema.holder_wake(row).mode, "chain")
        self.assertEqual((row["sid"], row["pid"]), (SID, pid))
        # 自己再呼叫一次＝改寫（defer 後 wake_at 變了）
        later = qw_schema.holder_extra(NOW.timestamp() + 7200, "single", "park")
        self.assertTrue(holder.acquire(SID, pid, extra=later))
        again = qw_schema.holder_wake(holder.read(SID))
        self.assertEqual((again.wake_at, again.mode), (NOW.timestamp() + 7200, "single"))

    def test_extra_cannot_overwrite_identity_fields(self):
        pid = os.getpid()
        evil = {"sid": "x", "pid": 1, "schema": "y", "proc_start": "z", "wake_at": "bad"}
        self.assertTrue(holder.acquire(SID, pid, extra=evil))
        row = holder.read(SID)
        self.assertEqual((row["sid"], row["pid"], row["schema"]), (SID, pid, holder.SCHEMA))
        self.assertNotEqual(row["proc_start"], "z")

    def test_without_extra_old_behaviour(self):
        self.assertTrue(holder.acquire(SID, os.getpid()))
        self.assertIsNone(qw_schema.holder_wake(holder.read(SID)))
        self.assertTrue(holder.is_live(holder.read(SID)))

    def test_live_other_still_blocks(self):
        self.assertTrue(holder.acquire(SID, 111, alive=lambda p: True, token=lambda p: "t"))
        self.assertFalse(holder.acquire(SID, 222, alive=lambda p: True, token=lambda p: "t",
                                        extra=qw_schema.holder_extra(
                                            NOW.timestamp(), "chain", "none")))


class SealSpawningTest(_Base):
    """tools/lib/sessionctl/seal.py::_spawned／handed_over 認 spawning 意圖（AT-QW-66）。"""

    def setUp(self) -> None:
        super().setUp()
        self.pkg = self.tmp / "pkg.md"
        self.pkg.write_text("x", encoding="utf-8")
        self.trace = Path(os.environ["AUTOSDD_TRACE_DIR"]) / "autosdd_session_switch.jsonl"
        self.trace.parent.mkdir(parents=True, exist_ok=True)

    def put(self, *rows):
        self.trace.write_text("\n".join(json.dumps({"handoff": str(self.pkg), **r})
                                        for r in rows) + "\n", encoding="utf-8")

    def spawning(self, secs_ago, attempt="a1", **extra):
        return {"event": qw_schema.EV_SPAWNING, qw_schema.SPAWN_ATTEMPT_KEY: attempt,
                "at": _iso(NOW.timestamp() - secs_ago), **extra}

    def test_cases(self):
        spawned = {"event": "session_switch_spawned", "ok": True}
        fail = {"event": "session_switch_spawned", "ok": False, "attempt": "a1"}
        cases = [
            ("intent live", [self.spawning(10)], True),
            ("intent + same-attempt failure", [self.spawning(10), fail], False),
            ("intent then spawned ok", [self.spawning(10), spawned], True),
            ("intent past TTL", [self.spawning(91)], False),
            ("expired intent but success row", [self.spawning(91), spawned], True),
            ("spawning with ok False itself", [self.spawning(10, ok=False)], False),
            ("other attempt failure does not cancel", [self.spawning(10), {**fail,
                                                                            "attempt": "zz"}],
             True),
            ("nothing", [], False),
        ]
        for name, rows, want in cases:
            with self.subTest(name):
                self.put(*rows)
                self.assertIs(seal._spawned(self.pkg, NOW), want)

    def test_other_package_rows_do_not_count(self):
        self.trace.write_text(json.dumps({"handoff": "other", "event": qw_schema.EV_SPAWNING,
                                          "attempt": "a", "at": _iso(NOW.timestamp())}) + "\n",
                              encoding="utf-8")
        self.assertFalse(seal._spawned(self.pkg, NOW))

    def test_missing_trace_file(self):
        self.trace.unlink(missing_ok=True)
        self.assertFalse(seal._spawned(self.pkg, NOW))


# ═════════════════════════════════════════════════════════════ plan_lines
class PlanLinesTest(_Base):
    """tools/lib/sessionctl/qw_plan.py::plan_lines：末行機器可讀（REQ-QW-03、64）。"""

    def test_machine_line_fields(self):
        lines = quotawall.plan_lines(self.plan(93))
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[1].startswith("QUOTAWALL_PLAN=stage=close"))
        for field in ("D=", "k=", "V=", "L=", "R=", "ctx=", "calibrated=no", "burn_calibrated=",
                      "agent_calibrated=", "invariant=ok", "stale=no", "ping_pp=",
                      "ping_pp_src=scaled"):
            self.assertIn(field, lines[1])

    def test_none_line(self):
        lines = quotawall.plan_lines(self.plan(50, env={"AUTOSDD_UNATTENDED": "1"}))
        self.assertEqual(lines[1], "QUOTAWALL_PLAN=stage=none reason=unattended")


# ═════════════════════════════════════════════════════════════ AT-QW-61 原始碼掃描鎖
def _field_literals(source: str) -> list[tuple[int, str]]:
    """AST 中「整串等於」十一欄名的字串常數（輸出格式字串如 `"wake_at="`、f-string 片段不算）。"""
    names = set(SchemaTest.ELEVEN)
    return [(n.lineno, n.value) for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in names]


class FieldNameScanLockTest(unittest.TestCase):
    """tools/lib/sessionctl/qw_schema.py：跨包欄名字面只住葉模組（AT-QW-61；MU-QW-34）。"""

    def _files(self):
        roots = [*(_REPO_ROOT / "tools" / "lib").rglob("*.py"),
                 *(_REPO_ROOT / "tools").glob("*.py"),
                 *(_REPO_ROOT / ".claude" / "hooks").glob("*.py")]
        return [p for p in roots if p.name != "qw_schema.py" and "__pycache__" not in p.parts]

    def test_literals_live_only_in_the_leaf(self):
        offenders = []
        for path in self._files():
            for line, value in _field_literals(path.read_text(encoding="utf-8")):
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{line} {value!r}")
        self.assertEqual(offenders, [], "跨包欄名字面只准在 qw_schema.py；其他模組 import 常數")

    def test_the_scan_goes_red_on_a_planted_literal(self):
        src = 'X = "primary_wake_at"\nY = "wake_at="\nZ = f"wake_at={1}"'
        self.assertEqual(_field_literals(src),
                         [(1, "primary_wake_at")])

    def test_leaf_defines_all_eleven(self):
        found = {v for _l, v in _field_literals(
            (_REPO_ROOT / "tools/lib/sessionctl/qw_schema.py").read_text(encoding="utf-8"))}
        self.assertEqual(found, set(SchemaTest.ELEVEN))

    def test_no_import_cycle_between_quotawall_and_park(self):
        """quotawall 家族頂層不 import park；park 頂層不 import quotawall 家族（只准 lazy）。"""
        def top_level_imports(path: Path) -> set[str]:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            out: set[str] = set()
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    out |= {a.name for a in node.names} | {node.module or ""}
                elif isinstance(node, ast.Import):
                    out |= {a.name for a in node.names}
            return out
        base = _REPO_ROOT / "tools/lib/sessionctl"
        for name in ("quotawall", "qw_calc", "qw_wall", "qw_plan", "qw_latch", "qw_verdict",
                     "qw_matrix", "qw_schema"):
            self.assertNotIn("park", top_level_imports(base / f"{name}.py"), name)
            self.assertNotIn("keepwarm", top_level_imports(base / f"{name}.py"), name)
        parked = top_level_imports(base / "park.py")
        self.assertFalse(parked & {"quotawall", "qw_plan", "qw_verdict", "qw_wall"})

if __name__ == "__main__":
    unittest.main()
