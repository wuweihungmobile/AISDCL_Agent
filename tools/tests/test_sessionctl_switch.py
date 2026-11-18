#!/usr/bin/env python3
"""`tools/lib/sessionctl/switch.py` 的驗收測試（TCS-SessionCtl-20261113 §2.1～§2.3；
AT-SC-01～24、28～33）。

守的判準（WHY 全文＝ADR-XPLAT-004 §2.13）：
- 無人喚醒選路量「續跑成本」不量檔案大小（F4 快取冷後按帳選路／R2 壓縮次數；R1／R3 於 R216
退役）：事故 E1
  （20,518,438 B 逐字稿≈60 萬 token 仍判 RESUME，續棒舊代理燒掉五小時窗）；
- 成本門檻（R2、硬線 HARD）與 `RESUME_AGENT_TOKENS` 只准下修（放寬＝退回 E1）；
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
import sentinel_lifecycle as SL  # noqa: E402

import session_resume_planner as planner  # noqa: E402
from lib.sessionctl import costmodel, switch  # noqa: E402

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
        self.tr = self.tmp / f"{SID}.jsonl"

    def feed(self, used: int | None, sid: str = SID) -> None:
        doc = {"session_id": sid, "model": {"id": "claude-fable-5"}, "context_window": {
            "context_window_size": 1_000_000,
            "current_usage": {"input_tokens": used, "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 0}}}
        (self.tmp / "feed").mkdir(exist_ok=True)
        (self.tmp / "feed" / f"{sid}.json").write_text(json.dumps(doc), encoding="utf-8")

    def reasons(self, size: int | None = 5000, **kw):
        return switch.fresh_reasons(SID, self.tr, size, guard=guard, env={}, **kw)

    def route(self, **kw) -> dict:
        return switch.choose_resume_route("claude", SID, self.tr, str(self.plan), guard=guard,
                                          env={}, **kw)


class RouteTest(_Env):
    """AT-SC-01～13＋AT-SS-46／47：`switch.fresh_reasons`／`choose_resume_route` 的 F4／R2／R4
    判準。

    R216（掌舵者 2026-11-18「專注在不要讓 Cache 過期」）語意改變，不是放寬：R1（25 萬）與 R3
    （上次續跑寫入）退役；快取**已冷**之後才按帳選路（F4：續跑重寫 2.0c > 換新 F(1+q)＝960,000，
    即 c > 480,000）。夾具逐字稿時間戳是 1970 年代 ⇒ 快取恆冷；要測「熱」就寫當下時間的記錄。"""

    def setUp(self) -> None:
        super().setUp()
        _write(self.tr, [_asst(1_000_000.0, 1000)])

    def test_at_sc_01_25_wan_is_no_longer_a_switch_line(self) -> None:
        """AT-SC-01（改）：冷、feed ctx=250,000（舊 R1 線）⇒ 不命中、RESUME。WHY：重寫 25 萬只要
        50 萬單位 < 換新 96 萬單位，續跑比換新便宜；舊版此處判 FRESH 是方向錯誤。"""
        self.feed(250_000)
        self.assertEqual(self.reasons()[0], [])
        self.assertEqual(self.route()["strategy"], switch.STRATEGY_RESUME)

    def test_at_sc_02_f4_boundary_cold_480000_resumes_480001_goes_fresh(self) -> None:
        """AT-SC-02／AT-SS-46：冷，480,000 ⇒ 不命中（相等不換）、480,001 ⇒ 只命中 F4、FRESH。"""
        self.feed(480_000)
        self.assertEqual(self.reasons()[0], [])
        self.assertEqual(self.route()["strategy"], switch.STRATEGY_RESUME)
        self.feed(480_001)
        hits, _ = self.reasons()
        self.assertEqual([h[:2] for h in hits], ["F4"], hits)
        self.assertEqual(self.route()["strategy"], switch.STRATEGY_FRESH)

    def test_f4_does_not_judge_a_warm_cache_however_big_the_context_is(self) -> None:
        """AT-SS-46（熱）／MU-20：快取仍熱（最後一筆 assistant 在現在）、ctx 800,000 ⇒ 不命中、
        RESUME（讀價 0.1c 必小於 F；對熱快取判 F4 的突變必紅）。R2 與快取冷熱無關：同一份熱逐字稿
        加兩個 compact_boundary ⇒ 仍命中 R2。"""
        now = datetime.now(UTC).timestamp()
        _write(self.tr, [_asst(now - 5, 800_000)])
        self.assertEqual(self.reasons()[0], [])
        self.assertEqual(self.route()["strategy"], switch.STRATEGY_RESUME)
        _write(self.tr, [_boundary(now - 30), _boundary(now - 20), _asst(now - 5, 800_000)])
        self.assertEqual([h[:2] for h in self.reasons()[0]], ["R2"])

    def test_at_sc_03_two_compact_boundaries_hit_only_r2(self) -> None:
        """AT-SC-03：逐字稿 2 個 compact_boundary ⇒ 只命中 R2（計數取逐字稿，不取 hook 事件檔）。"""
        _write(self.tr, [_asst(1_000_000.0), _boundary(1_000_010.0), _boundary(1_000_020.0)])
        hits, _ = self.reasons()
        self.assertEqual([h[:2] for h in hits], ["R2"], hits)

    def test_at_ss_47_r3_is_retired_a_big_last_resume_no_longer_forces_fresh(self) -> None:
        """AT-SS-47／MU-21：舊 R3 情境（上次續跑首回合寫入 15 萬）、冷、c=170,000 ⇒ 不命中
        （按帳續跑 34 萬單位 < 換新 96 萬單位，R3 是錯方向）；env 設了 R3 鍵 ⇒ notes 說「已退役」
        且仍不命中——舊 .env 不會壞、也不會讓退役變成改名。"""
        self.feed(170_000)
        env = {switch.R3_KEY: "100000"}
        hits, notes = switch.fresh_reasons(SID, self.tr, 5000, guard=guard, env=env)
        self.assertEqual(hits, [])
        self.assertTrue(any("已退役" in n and switch.R3_KEY in n for n in notes), notes)
        self.assertEqual(switch.fresh_reasons(SID, self.tr, 5000, guard=guard, env={})[1], [],
                         "沒設退役鍵就不該出聲")

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
        """AT-SC-08：feed 缺、冷、逐字稿最後 usage 合計 500,001 ⇒ F4 命中且理由標 transcript
        來源。"""
        _write(self.tr, [_asst(1_000_000.0, 500_000)])
        hits, _ = self.reasons()
        self.assertTrue(hits and hits[0].startswith("F4") and "transcript" in hits[0], hits)

    def test_at_sc_09_size_estimate_is_flagged_estimated(self) -> None:
        """AT-SC-09：feed 缺、逐字稿無 usage、size 20,518,438（≈51 萬 token 估計）、冷（注入）⇒ F4
        命中且理由含 `estimated`。同一份逐字稿不注入時冷熱量不到＝當熱 ⇒ 不命中（量不到不單方面
        造成資訊損失）。"""
        _write(self.tr, [{"type": "user", "timestamp": _iso(1_000_000.0)}])
        hits, _ = self.reasons(size=20_518_438, cache=lambda _p, _n: {"cold": True})
        self.assertTrue(hits and "estimated" in hits[0], hits)
        self.assertEqual(self.reasons(size=20_518_438)[0], [])

    def test_at_sc_10_unmeasurable_context_is_said_but_does_not_fire(self) -> None:
        """AT-SC-10：三個來源皆缺 ⇒ 不命中、說明含「上下文量不到」（量不到≠超標）。"""
        _write(self.tr, [{"type": "user", "timestamp": _iso(1_000_000.0)}])
        hits, notes = self.reasons(size=None)
        self.assertEqual(hits, [])
        self.assertTrue(any("上下文量不到" in n for n in notes), notes)

    def test_at_sc_11_e1_replay_with_the_real_numbers(self) -> None:
        """AT-SC-11（E1 回歸鎖）：size 20,518,438 B（上限 33,554,432）、feed 缺、最後
        usage≈600,000、壓縮 2 次、冷 ⇒ FRESH，理由同時含 F4／R2。修前（只看位元組）判 RESUME——
        這條是 sessionctl 存在的理由；R1／R3 退役後同一事故改由 F4（60 萬 > 48 萬臨界）接住。"""
        rows = "".join(json.dumps(r) + "\n" for r in (
            _asst(1_000_000.0, 100_000), _boundary(1_000_010.0), _boundary(1_000_020.0),
            _asst(1_000_030.0, 599_000))).encode("utf-8")
        # 填充放在**前面**：真實逐字稿的尾端一定是最近的記錄，快取冷熱只讀尾端 256 KB
        self.tr.write_bytes(b"x" * (20_518_438 - len(rows) - 1) + b"\n" + rows)
        self.assertEqual(self.tr.stat().st_size, 20_518_438)
        route = self.route(max_bytes=33_554_432)
        self.assertEqual(route["strategy"], switch.STRATEGY_FRESH)
        for rule in ("F4", "R2"):
            self.assertIn(rule, route["reason"])
        self.assertNotIn("-r", route["argv"])

    def test_advise_purpose_judges_only_the_hard_line_and_ignores_cache_state(self) -> None:
        """`advise=True`（handoff.advise_once 用）：只看硬線——849,999 不命中、850,000 命中；
        熱／冷都一樣（硬線防的是 autocompact，不是快取過期）；不判 F4（冷、60 萬不命中）。"""
        now = datetime.now(UTC).timestamp()
        for label, rows in (("冷", [_asst(1_000_000.0, 600_000)]),
                            ("熱", [_asst(now - 5, 600_000)])):
            _write(self.tr, rows)
            with self.subTest(label):
                self.assertEqual(self.reasons(advise=True)[0], [], "60 萬在硬線下，不得出聲")
        for used, expect in ((849_999, False), (850_000, True)):
            for label, stamp in (("冷", 1_000_000.0), ("熱", now - 5)):
                _write(self.tr, [_asst(stamp, used - 1)])  # input_tokens 1 ＋ cache_read used-1
                with self.subTest(used=used, label=label):
                    hits = self.reasons(advise=True)[0]
                    self.assertEqual(bool(hits), expect, hits)
                    if expect:
                        self.assertIn("硬線", hits[0])

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
        """AT-SC-14：出廠 R2≤2、RESUME_AGENT_TOKENS≤150,000、HARD＝850,000 且嚴格小於觀測到的
        autocompact 最小點（方向鎖：改大即紅）；R1／R3 已退役＝無出廠值、不在 `_DOWNWARD_ONLY`。"""
        got = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        for key, ceiling in ((switch.R2_KEY, 2), (switch.AGENT_TOKENS_KEY, 150_000),
                             (switch.HARD_CTX_KEY, 850_000)):
            self.assertLessEqual(got[key], ceiling, f"{key} 出廠值被放寬＝退回 E1")
        self.assertLess(got[switch.HARD_CTX_KEY], costmodel.OBSERVED_AUTOCOMPACT_MIN)
        for key in (switch.R1_KEY, switch.R3_KEY):
            self.assertIsNone(got[key], f"{key} 已退役，出廠值必須移除")
            self.assertNotIn(key, switch._DOWNWARD_ONLY)
        self.assertNotIn(switch.STALE_HOURS_KEY, switch._DOWNWARD_ONLY)

    def test_at_sc_15_a_lower_override_takes_effect(self) -> None:
        """AT-SC-15：env 覆寫 HARD=200,000 生效（可收緊）；feed 200,000 ⇒ advise 判準命中硬線。"""
        env = {switch.HARD_CTX_KEY: "200000"}
        self.assertEqual(switch.threshold(switch.HARD_CTX_KEY, env), (200_000, ""))
        self.feed(200_000)
        hits, _ = switch.fresh_reasons(SID, self.tr, 5000, guard=guard, env=env, advise=True)
        self.assertEqual(len(hits), 1)
        self.assertIn("硬線 200,000", hits[0])

    def test_at_sc_16_a_looser_override_falls_back_and_says_so(self) -> None:
        """AT-SC-16：HARD=900,000（大於出廠）⇒ 退出廠值＋stderr 一行（只收緊不放寬）。"""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            value, note = switch.threshold(switch.HARD_CTX_KEY, {switch.HARD_CTX_KEY: "900000"})
        self.assertEqual(value, int(switch._factory(switch.HARD_CTX_KEY)))
        self.assertTrue(note and "只准下修" in err.getvalue())
        for key in (switch.R2_KEY, switch.AGENT_TOKENS_KEY):  # 其餘方向鎖鍵一樣要有
            with self.subTest(key), contextlib.redirect_stderr(io.StringIO()) as e:
                loose = str(int(switch._factory(key)) + 1)
                self.assertEqual(switch.threshold(key, {key: loose})[0], int(switch._factory(key)))
                self.assertIn("只准下修", e.getvalue())
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
        for key in _KEYS + ("AUTOSDD_HANDOFF_TTL_HOURS", "AUTOSDD_ROSTER_QUIET_MINUTES",
                            costmodel.FRESH_COST_KEY, costmodel.VALUE_Q_KEY):
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
        last = self.now.timestamp() - 23 * 3600
        self.peer(30, start=last + 60)  # 他 sid 的活動晚於本 sid 最後活動 ⇒ 擋下它的只剩閒置門檻
        self.assertIsNone(self.check(last=last))

    def test_the_idle_threshold_boundary_is_inclusive(self) -> None:
        """AT-SC-20 的邊界：恰等於門檻（24h）命中；差 1 秒不命中（`<` 不是 `<=`）。"""
        edge = self.now.timestamp() - 24 * 3600
        self.peer(30, start=edge + 60)
        self.assertEqual(self.check(last=edge)["sid"], "peer")
        self.assertIsNone(self.check(last=edge + 1))

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
        sub = _write(self.tmp / "peer" / "subagents" / "agent-a.jsonl", rows)
        # 明確設 mtime 晚於 since（不依賴真實時鐘）⇒ 流程真的走到「只掃目錄直下」的判準
        os.utime(sub, (self.now.timestamp(), self.now.timestamp()))
        self.assertGreater(sub.stat().st_mtime, self.last)
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

    def gc_rows(self) -> list[dict]:
        """`gc(apply=False)` 的假後端列舉：一支 waiting 哨兵、逐字稿閒置 4 天（遠超 6h）。
        當前 session 保護關掉（否則 SID 自己被當成「最近仍在寫」而恆保留，測不到接線）。"""
        task = SL.TASK_PREFIX + SID
        plan = self.tmp / f"autosdd_resume_plan_{SID}.md"
        plan.write_text("# E2\n\n" + planner.render_relay(_plan_state(plan, self.tr, task)),
                        encoding="utf-8")
        os.utime(self.tr, (self.t_old, self.t_old))
        with unittest.mock.patch.object(SL, "sentinel_task_names", return_value=[task]), \
                unittest.mock.patch.object(SL, "_newest_session", return_value=""):
            rows = SL.gc(apply=False, tmp_dir=str(self.tmp))
        self.assertEqual([r["session_id"] for r in rows], [SID])
        self.assertEqual(rows[0]["state"], "waiting")
        return rows

    def test_gc_reaps_a_waiting_sentinel_only_when_a_newer_session_took_over(self) -> None:
        """FR-SC-09 的呼叫端接線（兩向）：waiting＋已被接手 ⇒ 收（理由含 superseded）；
        waiting＋沒人接手 ⇒ 留（等額度期間不拆，E2 反向的誤拆後果）。判準只有 `switch` 一個家。"""
        self.peer()
        taken = self.gc_rows()[0]
        self.assertTrue(taken["reap"], taken)
        self.assertIn("superseded", taken["why"])
        (self.tmp / "peer-new.jsonl").unlink()
        quiet = self.gc_rows()[0]
        self.assertFalse(quiet["reap"], quiet)
        self.assertIn("可能還在等額度", quiet["why"])

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
