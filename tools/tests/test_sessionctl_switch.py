#!/usr/bin/env python3
"""`tools/lib/sessionctl/switch.py` 的驗收測試（TCS-SessionCtl-20261113 §2.1～§2.3；
AT-SC-01～24、28～33）。

守的判準（WHY 全文＝ADR-XPLAT-004 §2.13）：
- 無人喚醒選路量「續跑成本」不量檔案大小（R1 上下文／R2 壓縮次數／R3 上次續跑快取寫入）：事故 E1
  （20,518,438 B 逐字稿≈60 萬 token 仍判 RESUME，續棒舊代理燒掉五小時窗）；
- 三個成本門檻與 `RESUME_AGENT_TOKENS` 只准下修（放寬＝退回 E1）；
- 過期 session 不續跑（SUPERSEDED）：事故 E2（waiting 的哨兵 reset 一到會無人續跑四天前的
  session），
  整週無人（沒有更新的 session）仍照舊續航。

縫：FS（tmp 目錄造逐字稿／feed／成本檔）、ENV（`env` 參數或 `mock.patch.dict`）、NOW（`now` 參數）。
不讀本機真實 `~/.claude`、不起真排程、不起真 claude。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import context_budget_guard as guard  # noqa: E402
import quota_policy_env  # noqa: E402
import resume_cost  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402

import session_resume_planner as planner  # noqa: E402
from lib.sessionctl import switch  # noqa: E402

_MODULE_FENCES: list[dict] = []  # 單模組直跑也不得碰真實 TEMP／快取／痕跡目錄（DEF-200-446）


def setUpModule() -> None:
    _MODULE_FENCES.append(SL.fence_enter())
    os.environ[guard.SENTINEL_OFF_ENV] = "1"  # 全程不准碰真排程器


def tearDownModule() -> None:
    SL.fence_exit(_MODULE_FENCES.pop())


SID = "11111111-2222-3333-4444-555555555555"
_KEYS = (switch.R1_KEY, switch.R2_KEY, switch.R3_KEY, switch.STALE_HOURS_KEY,
         switch.AGENT_TOKENS_KEY, switch.MODE_KEY)


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat().replace("+00:00", "Z")


def _asst(epoch: float, used: int = 1000) -> dict:
    return {"type": "assistant", "timestamp": _iso(epoch), "message": {
        "model": "claude-fable-5", "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0,
                                             "cache_read_input_tokens": used}}}


def _boundary(epoch: float) -> dict:
    return {"type": "system", "subtype": "compact_boundary", "timestamp": _iso(epoch)}


def _write(path: Path, rows: list[dict], pad_to: int | None = None) -> Path:
    """寫 jsonl；`pad_to` 給定時補一行不含 `"usage"` 的填充（壞 JSON 行，被各掃描器跳過），
    補到恰好該位元組數。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = "".join(json.dumps(r) + "\n" for r in rows).encode("utf-8")
    if pad_to is not None:
        raw += b"x" * (pad_to - len(raw) - 1) + b"\n"
    path.write_bytes(raw)
    return path


class _Env(unittest.TestCase):
    """共用夾具：tmp 目錄＋隔離 feed／handback／trace 目錄＋乾淨的門檻環境。"""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory(
            prefix="sc_switch_", ignore_cleanup_errors=True)))
        env = {guard.CONTEXT_FEED_DIR_ENV: str(self.tmp / "feed"),
               "AUTOSDD_HANDBACK_DIR": str(self.tmp / "hb"),
               "AUTOSDD_TRACE_DIR": str(self.tmp / "traces")}
        self.enterContext(unittest.mock.patch.dict(os.environ, env))
        for key in _KEYS + (switch.RESUME_MAX_TRANSCRIPT_ENV,):
            os.environ.pop(key, None)
        self.plan = self.tmp / "plan.md"
        self.plan.write_text("# 任務書\n", encoding="utf-8")
        self.cost = self.tmp / "cost.jsonl"
        self.tr = self.tmp / f"{SID}.jsonl"

    def feed(self, used: int | None, sid: str = SID) -> None:
        doc = {"session_id": sid, "model": {"id": "claude-fable-5"}, "context_window": {
            "context_window_size": 1_000_000,
            "current_usage": {"input_tokens": used, "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 0}}}
        (self.tmp / "feed").mkdir(exist_ok=True)
        (self.tmp / "feed" / f"{sid}.json").write_text(json.dumps(doc), encoding="utf-8")

    def cost_rows(self, *values: int | None) -> None:
        rows = [{"session_id": SID, "cache_creation_input_tokens": v} for v in values]
        self.cost.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def reasons(self, size: int | None = 5000, **kw):
        return switch.fresh_reasons(SID, self.tr, size, guard=guard, env={}, cost_path=self.cost,
                                    **kw)

    def route(self, **kw) -> dict:
        return switch.choose_resume_route("claude", SID, self.tr, str(self.plan), guard=guard,
                                          env={}, cost_path=self.cost, **kw)


class RouteTest(_Env):
    """AT-SC-01～13：`switch.fresh_reasons`／`choose_resume_route` 的 R1～R4 判準與缺值處理。"""

    def setUp(self) -> None:
        super().setUp()
        _write(self.tr, [_asst(1_000_000.0, 1000)])

    def test_at_sc_01_r1_fires_at_exactly_the_threshold(self) -> None:
        """AT-SC-01：feed ctx=250,000 ⇒ 只命中 R1（R1 是 `>=`；WHY：E1）。"""
        self.feed(250_000)
        hits, _ = self.reasons()
        self.assertEqual([h[:2] for h in hits], ["R1"], hits)
        self.assertEqual(self.route()["strategy"], switch.STRATEGY_FRESH)

    def test_at_sc_02_r1_boundary_just_below_is_not_a_hit(self) -> None:
        """AT-SC-02：249,999 不成立（邊界的另一側；證明門檻不是「恆命中」）。"""
        self.feed(249_999)
        self.assertEqual(self.reasons()[0], [])
        self.assertEqual(self.route()["strategy"], switch.STRATEGY_RESUME)

    def test_at_sc_03_two_compact_boundaries_hit_only_r2(self) -> None:
        """AT-SC-03：逐字稿 2 個 compact_boundary ⇒ 只命中 R2（計數取逐字稿，不取 hook 事件檔）。"""
        _write(self.tr, [_asst(1_000_000.0), _boundary(1_000_010.0), _boundary(1_000_020.0)])
        hits, _ = self.reasons()
        self.assertEqual([h[:2] for h in hits], ["R2"], hits)

    def test_at_sc_04_r3_uses_the_most_recent_cost_record(self) -> None:
        """AT-SC-04：成本檔同 sid 較舊 0、最近 100,000 ⇒ 只命中 R3（取最近一筆，非最大）。"""
        self.cost_rows(0, 100_000)
        hits, _ = self.reasons()
        self.assertEqual([h[:2] for h in hits], ["R3"], hits)
        self.cost_rows(100_000, 0)
        self.assertEqual(self.reasons()[0], [], "最近一筆是 0 卻仍命中＝取到舊值")

    def test_at_sc_05_r4_oversized_transcript_still_degrades(self) -> None:
        """AT-SC-05（R4 回歸）：逐字稿 > 上限 ⇒ FRESH，理由含既有字串「超上限」。"""
        route = self.route(max_bytes=10)
        self.assertEqual(route["strategy"], switch.STRATEGY_FRESH)
        self.assertIn("超上限", route["reason"])

    def test_at_sc_06_r4_weekly_axis_still_degrades(self) -> None:
        """AT-SC-06（R4 回歸）：`weekly` 非空 ⇒ FRESH，理由含該週軸字串。"""
        route = self.route(weekly="週軸 weekly_all=75% 已達 converge 帶")
        self.assertEqual(route["strategy"], switch.STRATEGY_FRESH)
        self.assertIn("weekly_all=75%", route["reason"])

    def test_at_sc_07_all_low_resumes_with_dash_r(self) -> None:
        """AT-SC-07（負向）：全部低 ⇒ RESUME、argv 含 `-r <sid>`（降級只准單向）。"""
        route = self.route()
        self.assertEqual(route["strategy"], switch.STRATEGY_RESUME)
        self.assertEqual(route["argv"][route["argv"].index("-r") + 1], SID)

    def test_at_sc_08_transcript_usage_is_the_fallback_when_feed_is_absent(self) -> None:
        """AT-SC-08：feed 缺、逐字稿最後 usage 合計 300,000 ⇒ R1 命中且理由標 transcript 來源。"""
        _write(self.tr, [_asst(1_000_000.0, 300_000)])
        hits, _ = self.reasons()
        self.assertTrue(hits and hits[0].startswith("R1") and "transcript" in hits[0], hits)

    def test_at_sc_09_size_estimate_is_flagged_estimated(self) -> None:
        """AT-SC-09：feed 缺、逐字稿無 usage、size 20,518,438 ⇒ R1 命中且理由含 `estimated`。"""
        _write(self.tr, [{"type": "user", "timestamp": _iso(1_000_000.0)}])
        hits, _ = self.reasons(size=20_518_438)
        self.assertTrue(hits and "estimated" in hits[0], hits)

    def test_at_sc_10_unmeasurable_r1_is_said_but_does_not_fire(self) -> None:
        """AT-SC-10：三個來源皆缺 ⇒ R1 不成立、說明含「R1 量不到」，其餘規則照判（量不到≠超標）。"""
        _write(self.tr, [{"type": "user", "timestamp": _iso(1_000_000.0)}])
        self.cost_rows(100_000)
        hits, notes = self.reasons(size=None)
        self.assertEqual([h[:2] for h in hits], ["R3"], "R1 量不到時 R3 仍要照判")
        self.assertTrue(any("R1 量不到" in n for n in notes), notes)

    def test_at_sc_11_e1_replay_with_the_real_numbers(self) -> None:
        """AT-SC-11（E1 回歸鎖）：size 20,518,438 B（上限 33,554,432）、feed 缺、最後
        usage≈600,000、壓縮 2 次、上次續跑 cache_creation 138,811 ⇒ FRESH，理由同時含
        R1／R2／R3。修前（只看位元組）判 RESUME——這條是 sessionctl 存在的理由。"""
        _write(self.tr, [_asst(1_000_000.0, 100_000), _boundary(1_000_010.0),
                         _boundary(1_000_020.0), _asst(1_000_030.0, 599_000)], pad_to=20_518_438)
        self.assertEqual(self.tr.stat().st_size, 20_518_438)
        self.cost_rows(138_811)
        route = self.route(max_bytes=33_554_432)
        self.assertEqual(route["strategy"], switch.STRATEGY_FRESH)
        for rule in ("R1", "R2", "R3"):
            self.assertIn(rule, route["reason"])
        self.assertNotIn("-r", route["argv"])

    def test_at_sc_12_fresh_prompt_carries_handoff_path_and_both_hard_rules(self) -> None:
        """AT-SC-12：FRESH 的 prompt 含交接包路徑與兩條硬規則字面（不得 SendMessage 續舊
        代理＋第一個動作重驗）；argv 不含 `-r`。`handoff_path=None` 時沿用現行任務書路徑
        （參數縫，下一包注入交接包）。"""
        handoff = str(self.tmp / "hand" / "h.md")
        route = self.route(max_bytes=10, handoff_path=handoff)
        prompt = route["argv"][2]
        self.assertIn(handoff, prompt)
        self.assertIn("不得用 SendMessage 續舊 session 的任何代理", prompt)
        self.assertIn("第一個動作＝重驗 git status／HEAD", prompt)
        self.assertNotIn("-r", route["argv"])
        default = self.route(max_bytes=10)["argv"][2]
        self.assertIn(str(self.plan), default)
        self.assertNotIn(handoff, default)

    def test_at_sc_13_missing_plan_still_refuses(self) -> None:
        """AT-SC-13（既有行為不變）：任務書缺席 ⇒ REFUSE、argv None。"""
        self.plan.unlink()
        route = self.route()
        self.assertEqual((route["strategy"], route["argv"]), (switch.STRATEGY_REFUSE, None))


class ThresholdTest(_Env):
    """AT-SC-14～18：門檻住 ENV_SPEC、方向鎖、病態值。"""

    def test_at_sc_14_factory_values_are_pinned_downward_only(self) -> None:
        """AT-SC-14：出廠 R1≤250,000、R2≤2、R3≤100,000、RESUME_AGENT_TOKENS≤150,000
        （方向鎖：改大即紅）。"""
        got = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        for key, ceiling in ((switch.R1_KEY, 250_000), (switch.R2_KEY, 2),
                             (switch.R3_KEY, 100_000), (switch.AGENT_TOKENS_KEY, 150_000)):
            self.assertLessEqual(got[key], ceiling, f"{key} 出廠值被放寬＝退回 E1")
        self.assertNotIn(switch.STALE_HOURS_KEY, switch._DOWNWARD_ONLY)

    def test_at_sc_15_a_lower_override_takes_effect(self) -> None:
        """AT-SC-15：env 覆寫 R1=200,000 生效（可收緊）。"""
        self.assertEqual(switch.threshold(switch.R1_KEY, {switch.R1_KEY: "200000"}), (200_000, ""))
        self.feed(200_000)
        hits, _ = switch.fresh_reasons(SID, self.tr, 5000, guard=guard, cost_path=self.cost,
                                       env={switch.R1_KEY: "200000"})
        self.assertEqual([h[:2] for h in hits], ["R1"])

    def test_at_sc_16_a_looser_override_falls_back_and_says_so(self) -> None:
        """AT-SC-16：R1=400,000（大於出廠）⇒ 退出廠值＋stderr 一行（只收緊不放寬）。"""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            value, note = switch.threshold(switch.R1_KEY, {switch.R1_KEY: "400000"})
        self.assertEqual(value, int(switch._factory(switch.R1_KEY)))
        self.assertTrue(note and "只准下修" in err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(switch.threshold(switch.STALE_HOURS_KEY,
                                          {switch.STALE_HOURS_KEY: "48"}), (48, ""),
                             "STALE_SESSION_HOURS 不加方向鎖，調大要生效")

    def test_at_sc_17_pathological_values_fall_back_and_say_so(self) -> None:
        """AT-SC-17：`abc`／`-1`／`0` ⇒ 退出廠值＋出聲。"""
        for raw in ("abc", "-1", "0"):
            with self.subTest(raw), contextlib.redirect_stderr(io.StringIO()) as err:
                value, note = switch.threshold(switch.R2_KEY, {switch.R2_KEY: raw})
                self.assertEqual(value, int(switch._factory(switch.R2_KEY)))
                self.assertTrue(note and "病態值" in err.getvalue())

    def test_at_sc_18_new_keys_are_in_the_env_example(self) -> None:
        """AT-SC-18：新鍵全在生成物與 repo `.env.example`（新鮮度鎖同步，生成物不得手寫）。"""
        text = quota_policy_env.render_env_example()
        for key in _KEYS + ("AUTOSDD_HANDOFF_TTL_HOURS", "AUTOSDD_ROSTER_QUIET_MINUTES"):
            self.assertIn(f"{key}=", text)
        on_disk = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertEqual(quota_policy_env.env_example_problems(on_disk), [])

    def test_switch_mode_rejects_unknown_values(self) -> None:
        """`switch_mode`：auto／notify／off 以外退 auto 並出聲（D5 的三個模式）。"""
        self.assertEqual([switch.switch_mode({switch.MODE_KEY: m}) for m in switch.MODES],
                         list(switch.MODES))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(switch.switch_mode({switch.MODE_KEY: "wat"}), "auto")
        self.assertEqual(switch.switch_mode({}), "auto")


class LastCostTest(_Env):
    """`resume_cost.last_cost`（R3 的資料源）：唯讀、取同 sid 最近一筆、量不到回 None。"""

    def test_last_cost_picks_the_latest_row_of_that_sid_only(self) -> None:
        """WHY：R3 要「上次」那一次的成本；別的 sid 或沒量到的列不得頂替。"""
        rows = [{"session_id": SID, "cache_creation_input_tokens": 1},
                {"session_id": "other", "cache_creation_input_tokens": 999_999},
                {"session_id": SID, "cache_creation_input_tokens": 138_811}]
        self.cost.write_text("".join(json.dumps(r) + "\n" for r in rows) + "壞行\n",
                             encoding="utf-8")
        self.assertEqual(resume_cost.last_cost(SID, self.cost), 138_811)
        self.assertIsNone(resume_cost.last_cost("nobody", self.cost))
        self.assertIsNone(resume_cost.last_cost(SID, self.tmp / "absent.jsonl"))
        self.cost_rows(None)
        self.assertIsNone(resume_cost.last_cost(SID, self.cost), "未量到的最近一列要回 None")


class SupersededTest(_Env):
    """AT-SC-19～24：`switch.superseded_by` 的判準（閒置 ≥ 門檻 ∧ 他 session 其後有真實活動）。"""

    def setUp(self) -> None:
        super().setUp()
        self.now = datetime(2026, 11, 15, 2, 2, tzinfo=UTC)
        self.last = self.now.timestamp() - 25 * 3600

    def peer(self, n: int, start: float | None = None, step: float = 32.0, name="peer") -> Path:
        t0 = (self.last + 60) if start is None else start
        path = _write(self.tmp / f"{name}.jsonl", [_asst(t0 + i * step) for i in range(n)])
        os.utime(path, (self.now.timestamp(), self.now.timestamp()))
        return path

    def check(self, last: float | None = None, project: Path | None = None):
        return switch.superseded_by(project or self.tmp, SID, self.last if last is None else last,
                                    self.now, env={})

    def test_at_sc_19_idle_and_real_peer_activity_is_superseded(self) -> None:
        """AT-SC-19：本 sid 最後對話 25h 前、他 sid 其後 30 回合／≥600 s ⇒ 回
        {sid,turns,span_seconds,last_at}。"""
        self.peer(30)
        got = self.check()
        self.assertEqual((got["sid"], got["turns"]), ("peer", 30), got)
        self.assertGreaterEqual(got["span_seconds"], 600)
        self.assertIn("last_at", got)

    def test_at_sc_20_not_yet_idle_enough_is_none(self) -> None:
        """AT-SC-20：本 sid 閒置 23h（< 24h 門檻）⇒ None。"""
        self.peer(30)
        self.assertIsNone(self.check(last=self.now.timestamp() - 23 * 3600))

    def test_at_sc_21_a_one_turn_probe_is_not_a_takeover(self) -> None:
        """AT-SC-21：他 sid 只有 1 回合（`claude -p ok`）⇒ None（同武裝門檻那把尺）。"""
        self.peer(1)
        self.assertIsNone(self.check())

    def test_at_sc_22_peer_activity_before_own_last_is_not_a_takeover(self) -> None:
        """AT-SC-22：他 sid 的活動全在本 sid 最後活動之前 ⇒ None（先後順序才是「接手」）。"""
        self.peer(30, start=self.last - 5000)
        self.assertIsNone(self.check())

    def test_at_sc_23_subagent_files_are_not_another_session(self) -> None:
        """AT-SC-23：他 sid 的活動只在 `<sid>/subagents/` 下 ⇒ None（子代理不是另一個 session）。"""
        rows = [_asst(self.last + 60 + i * 32) for i in range(30)]
        _write(self.tmp / "peer" / "subagents" / "agent-a.jsonl", rows)
        self.assertIsNone(self.check())

    def test_at_sc_24_unreadable_directory_fails_towards_continuing(self) -> None:
        """AT-SC-24：目錄不在／讀不動（OSError）⇒ None（量不到≠已接手；判了＝拆排程，不可逆）。"""
        self.peer(30)
        self.assertIsNone(self.check(project=self.tmp / "no_such_dir"))
        with unittest.mock.patch.object(Path, "glob", side_effect=OSError("denied")):
            self.assertIsNone(self.check())
        self.assertIsNone(switch.superseded_by(self.tmp, SID, None, self.now, env={}),
                          "本 session 無對話記錄 ⇒ 不判")


def _plan_state(plan: Path, transcript: Path, task: str) -> dict:
    """合法 relay 狀態塊（`relay_problems()` 必須回空）；E2 那支哨兵 state=`waiting`、
    allow_resume=true。"""
    state = {
        "schema": planner.RELAY_SCHEMA, "session_id": SID, "plan_path": str(plan),
        "state": "waiting", "kind": "sentinel", "reset_at": "2026-11-15T02:02:00+08:00",
        "reset_source": "transcript-verbatim", "attempts": 0,
        "max_attempts": planner.MAX_PROBE_ATTEMPTS, "allow_resume": True, "task_name": task,
        "carrier": "test", "log_path": str(planner.endurance_log_path(plan)),
        "transcript": str(transcript),
        planner.schedule_backend.CRED_KEY_SCHTASKS: "2026/11/15 02:02:00"}
    return state


class E2ReplayTest(_Env):
    """AT-SC-28／29：E2 的真實數值重放（waiting、allow_resume、逐字稿 29,652,867 B、ctx 556,777、
    閒置 4 天、更新的 session 其後有活動）。修前 reset 一到就 probe→無人續跑四天前的 session。"""

    #: 與 `test_sentinel_tick_e2e_r145` 同一句真實 session 撞線字樣（`classify_limit` →
    #: LIMIT_SESSION；weekly 字樣不算「會被等待」的事件類別，用它會測不到優先序）。
    HIT = "You've hit your session limit · resets 9am (Asia/Taipei)"

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(unittest.mock.patch("tempfile.gettempdir", return_value=str(self.tmp)))
        self.enterContext(unittest.mock.patch.object(
            planner, "project_transcript_dir", lambda _root: self.tmp / "slug"))
        now = datetime.now(UTC).timestamp()
        self.t_old = now - 4 * 86400
        self.tr = _write(self.tmp / f"{SID}.jsonl", [
            _asst(self.t_old - 600, 556_777),
            {"type": "assistant", "timestamp": _iso(self.t_old),
             "message": {"model": guard.SYNTHETIC_MODEL, "content": [{"text": self.HIT}]}}],
            pad_to=29_652_867)
        self.assertEqual(self.tr.stat().st_size, 29_652_867)

    def peer(self, n: int = 30) -> None:
        path = _write(self.tmp / "peer-new.jsonl", [_asst(self.t_old + 3600 + i * 40)
                                                    for i in range(n)])
        self.assertTrue(path.is_file())

    def plan_for(self, task: str) -> Path:
        plan = self.tmp / "plan-e2.md"
        plan.write_text("# E2\n\n" + planner.render_relay(_plan_state(plan, self.tr, task)),
                        encoding="utf-8")
        return plan

    def events(self, plan: Path) -> dict[str, dict]:
        rows = planner.endurance_log_path(plan).read_text(encoding="utf-8").splitlines()
        return {r["event"]: r for r in map(json.loads, rows)}

    def run_tick(self, tick: str, task: str):
        plan = self.plan_for(task)
        args = planner.build_parser().parse_args(
            [tick, "--plan", str(plan), "--task-name", task])
        probes, spawns = [], []
        mock_patch = unittest.mock.patch.object
        real_resume_tick = planner._resume_tick  # 哨兵 tick 的 probe 分支交棒它；測試只記錄呼叫
        with mock_patch(planner, "probe_quota", lambda cmd: probes.append(cmd) or
                        {"rc": 0, "kind": "none", "open": True, "text": "", "source": ""}), \
                mock_patch(planner, "_run_resume", lambda *a: spawns.append(a) or 0), \
                mock_patch(planner, "_resume_tick",
                           lambda a: spawns.append(("handoff-to-resume-tick",)) or 7), \
                mock_patch(planner, "_schtasks_remove", return_value=0) as remove, \
                mock_patch(planner, "_register_and_record", lambda *a: (0, "cred")):
            rc = (planner._sentinel_tick if tick == "--sentinel-tick" else real_resume_tick)(args)
        return plan, rc, probes, spawns, remove

    def check_superseded(self, plan: Path, rc, probes, spawns, remove, task: str) -> None:
        self.assertEqual((probes, spawns), ([], []), "過期 session 不得探測、spawn、交棒")
        remove.assert_called_once_with(task)
        events = self.events(plan)
        self.assertIn("sentinel_superseded", events)
        self.assertNotIn("probed", events)
        state = planner.parse_relay(plan.read_text(encoding="utf-8"))
        self.assertEqual(state["state"], "superseded")
        hb = Path(events["sentinel_superseded"]["handback"])
        self.assertIn(f"claude -r {SID}", hb.read_text(encoding="utf-8"))
        self.assertTrue(all(m in hb.read_text(encoding="utf-8")
                            for m in switch.resume_route.HANDBACK_MARKERS))
        self.assertEqual(rc, 0)

    def test_at_sc_28_the_sentinel_tick_dissolves_a_stale_waiting_session(self) -> None:
        """AT-SC-28（E2 回歸鎖，`_sentinel_tick`）：撞線事件仍「未處理」的 waiting 哨兵，
        因他 session 接手 ⇒ 不探測、不 spawn、排程解除、狀態 `superseded`、痕跡
        `sentinel_superseded`、handback 含 `claude -r`。優先序在撞線分支之前（SUPERSEDED
        若排在後面，這支永遠輪不到）。"""
        self.peer()
        task = "T-e2-sentinel"
        plan, rc, probes, spawns, remove = self.run_tick("--sentinel-tick", task)
        self.check_superseded(plan, rc, probes, spawns, remove, task)

    def test_at_sc_29_the_resume_tick_applies_the_same_check_before_probing(self) -> None:
        """AT-SC-29：`-Once` 續航路（`_resume_tick`）不經 `sentinel_decide`，探測額度之前
        也要攔下。"""
        self.peer()
        task = "T-e2-resume"
        plan, rc, probes, spawns, remove = self.run_tick("--resume-tick", task)
        self.check_superseded(plan, rc, probes, spawns, remove, task)

    def test_a_week_with_nobody_else_still_goes_the_old_way(self) -> None:
        """對照（AT-SC-27 的 tick 版／FR-SC-07）：同一份 E2 數值但**沒有更新的 session** ⇒
        照舊撞線分支（reset 早已過 ⇒ probe ⇒ 交棒給 `_resume_tick`；行為與修前相同，
        不得出現 `superseded`）。"""
        task = "T-e2-quiet"
        plan, rc, _probes, spawns, remove = self.run_tick("--sentinel-tick", task)
        events = self.events(plan)
        self.assertNotIn("sentinel_superseded", events)
        self.assertEqual(events["sentinel_decided"]["action"], "probe")
        self.assertEqual((rc, spawns), (7, [("handoff-to-resume-tick",)]))
        remove.assert_not_called()


class ReapSupersededTest(unittest.TestCase):
    """AT-SC-31～33：`reap_verdict` 的 `superseded`（waiting 才算判準）與終態登記。"""

    def test_at_sc_31_a_superseded_waiting_sentinel_is_reaped(self) -> None:
        """AT-SC-31：waiting＋superseded＋閒置達門檻 ⇒ 收，理由含 superseded。"""
        reap, why = SL.reap_verdict(transcript_exists=True, idle_seconds=7 * 3600,
                                    state="waiting", protected=False, superseded=True)
        self.assertTrue(reap)
        self.assertIn("superseded", why)

    def test_at_sc_32_a_plain_waiting_sentinel_is_never_reaped(self) -> None:
        """AT-SC-32：waiting 且未 superseded ⇒ 不收（原紀律：等額度期間不拆）；預設值不改行為。"""
        for kwargs in ({}, {"superseded": False}):
            reap, why = SL.reap_verdict(transcript_exists=True, idle_seconds=7 * 3600,
                                        state="waiting", protected=False, **kwargs)
            self.assertFalse(reap)
            self.assertIn("可能還在等額度", why)

    def test_at_sc_33_superseded_is_a_terminal_state(self) -> None:
        """AT-SC-33：`superseded` ∈ TERMINAL_STATES（GC 收得到，且仍屬「閒置夠久就可收」集合）。"""
        self.assertIn("superseded", SL.TERMINAL_STATES)
        self.assertIn("superseded", SL.REAPABLE_WHEN_IDLE)


class SupersedingSinceTest(unittest.TestCase):
    """AT-SC-30 的補強：抽參數後舊包裝 `superseding_session(halt_marker)` 與新
    `superseding_since` 同結果（既有測試全綠由 test_context_budget_guard／
    test_sentinel_tick_e2e_r145 負責）。"""

    def test_the_halt_wrapper_delegates_to_the_since_scan(self) -> None:
        """WHY：兩個用途必須共用同一份掃描碼（不得兩個家）；包裝只轉 `at`→since。"""
        import sentinel_lifecycle_arm as arm
        with tempfile.TemporaryDirectory(prefix="sc_since_") as raw:
            root, t0 = Path(raw), datetime.now(UTC).timestamp() - 5000
            _write(root / "peer.jsonl", [_asst(t0 + 60 + i * 32) for i in range(30)])
            marker = {"at": _iso(t0)}
            via_halt = arm.superseding_session(root, SID, marker)
            via_since = arm.superseding_since(root, SID, t0)
            self.assertEqual(via_halt, via_since)
            self.assertEqual(via_halt["sid"], "peer")
            self.assertIsNone(arm.superseding_session(root, SID, None))


if __name__ == "__main__":
    unittest.main()
