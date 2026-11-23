#!/usr/bin/env python3
"""`tools/lib/sessionctl/park.py::fire_route`／`park_cli.py` 到點選路的驗收測試（R216 WP-F；
TCS-SessionSwitch-CostModel REQ-SS-19、設計 §4.6）。

守的判準：park 的 job 到點時不再一律開新 session 帶交接包——快取仍熱、或冷了但續跑重寫比接手便宜
（F4：`W_CC1·c ≤ F(1+q)`）就 `claude -r <原 sid>` 續跑，保留上下文；續跑較貴才走既有交接包路。
上下文量不到一律走既有交接包路（`-r` 需要讀得到逐字稿；也保住 test_sessionctl_park.py 的既有契約）。
縫：NOW／FS（tmp 圍籬）／ENV／SPAWN／RESUME／RUN（假 runner）；不碰真排程器、真 claude、
真 `~/.claude`、真 `~/.autosdd`。真排程器＋真逐字稿的到點選路另由 realverify 案例 RV-K8／K9 驗。
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from test_sessionctl_park import NOW, RESET, SID, _CliFence, _marker  # noqa: E402

from lib.sessionctl import costmodel, park, park_cli  # noqa: E402

LATE = NOW + timedelta(hours=1)
_FACTORY_ENV = {costmodel.FRESH_COST_KEY: "480000", costmodel.VALUE_Q_KEY: "1"}


class FireRouteTest(unittest.TestCase):
    """tools/lib/sessionctl/park.py::fire_route：F4 在 park 到點的套用（純判準，無 I/O）。"""

    def test_unmeasurable_context_keeps_the_handoff_route(self) -> None:
        """WHY：`claude -r` 需要讀得到逐字稿；量不到上下文就不冒險續跑，走已封存的交接包。"""
        for held in (None, 0, -5):
            for cold in (True, False):
                route, why = park.fire_route(held, cold, _FACTORY_ENV)
                self.assertEqual(route, park.FIRE_FRESH, (held, cold))
                self.assertIn("量不到", why)

    def test_a_warm_cache_always_resumes_even_for_a_huge_context(self) -> None:
        """WHY：快取仍熱時續跑只付讀價 `0.1c`，必小於接手成本 F；F4 只判「已冷」的情境。
        反向變體（突變：忘了看冷熱）會把 80 萬熱上下文換成新 session。"""
        route, why = park.fire_route(800_000, False, _FACTORY_ENV)
        self.assertEqual(route, park.FIRE_RESUME)
        self.assertIn("快取仍熱", why)

    def test_cold_cache_flips_exactly_at_the_f4_threshold(self) -> None:
        """與 `costmodel.fresh_is_cheaper` 同一條邊界（嚴格大於才換新）：
        480,000 續跑、480,001 換新。"""
        self.assertEqual(park.fire_route(480_000, True, _FACTORY_ENV)[0], park.FIRE_RESUME)
        route, why = park.fire_route(480_001, True, _FACTORY_ENV)
        self.assertEqual(route, park.FIRE_FRESH)
        self.assertIn("F4", why)

    def test_the_route_agrees_with_the_costmodel_on_a_grid(self) -> None:
        """WHY：喚醒選路、轉送、park 三處必須是同一個判準，不得各算各的；改一處不改另一處即紅。"""
        for env in (_FACTORY_ENV, {costmodel.FRESH_COST_KEY: "100000", costmodel.VALUE_Q_KEY: "0"}):
            for held in (1, 49_999, 50_000, 50_001, 479_999, 480_000, 480_001, 900_000):
                for cold in (True, False):
                    want = costmodel.fresh_is_cheaper(held, cold=cold, env=env)
                    got = park.fire_route(held, cold, env)[0] == park.FIRE_FRESH
                    self.assertEqual(got, want, (held, cold, env))

    def test_the_cold_resume_reason_shows_both_costs(self) -> None:
        """WHY：掌舵者要能從痕跡看出為何續跑——續跑重寫 vs 換新兩個數字都要在理由裡。"""
        _route, why = park.fire_route(200_000, True, _FACTORY_ENV)
        self.assertIn("400,000", why)  # 2.0 × 200,000
        self.assertIn("960,000", why)  # 480,000 × (1+1)


def _assistant(at, *, cc=0, cr=0, inp=1) -> str:
    return json.dumps({"type": "assistant", "timestamp": at.isoformat(),
                       "message": {"model": "claude-x", "usage": {
                           "input_tokens": inp, "cache_creation_input_tokens": cc,
                           "cache_read_input_tokens": cr, "output_tokens": 5,
                           "cache_creation": {"ephemeral_1h_input_tokens": cc}}}})


class FireRoutingEndToEndTest(_CliFence, unittest.TestCase):
    """tools/lib/sessionctl/park_cli.py::_cmd_fire：真逐字稿 usage ⇒ 選路 ⇒ 走對的開法。
    WHY：選路判準對、但 job 本體沒接上，行為就仍是「一律開新 session」；這裡驗接線。"""

    def setUp(self) -> None:
        super().setUp()
        self.label = "AutoSDD_HandoffSpawn_798a7bf1_202611152002"
        self.backend.jobs.add(self.label)
        park.write_marker(dict(_marker("H"), pkg=str(self.pkg)))
        self.transcript = self.tmp / f"{SID}.jsonl"
        self.spawned: list[Path] = []
        self.resumed: list[str] = []
        self.rc = {"spawn": 0, "resume": 0}

    def transcript_with(self, ctx_tokens: int, *, hours_idle: float) -> None:
        stamp = LATE - timedelta(hours=hours_idle)
        # cc=1（1h 層寫入）讓快取壽命判為 1 小時（主控的真實形態）；ctx＝1＋1＋(ctx-2)
        self.transcript.write_text(_assistant(stamp, cc=1, cr=ctx_tokens - 2) + "\n",
                                   encoding="utf-8")
        old = (LATE - timedelta(hours=hours_idle + 1)).timestamp()
        os.utime(self.transcript, (old, old))

    def fire(self) -> int:
        def spawn(path):
            self.spawned.append(path)
            return self.rc["spawn"]

        def resume(sid, pkg, **_kw):
            self.resumed.append(sid)
            return self.rc["resume"]

        seams = {"backend": self.backend, "spawn": spawn, "resume": resume, "platform": "win32",
                 "preflight": lambda *_a, **_k: [], "sessions_dir": self.tmp / "sessions",
                 "notify": lambda *_a: 0, "transcript": lambda _s: self.transcript}
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            return park_cli.run(["--session-id", SID, "--fire", "--job", self.label, "--pkg",
                                 str(self.pkg), "--fire-at", RESET.isoformat()],
                                env={**self.env, **_FACTORY_ENV}, now=LATE, seams=seams)

    def events(self) -> list[str]:
        return [t["event"] for t in self.traces()]

    def test_small_cold_context_resumes_the_original_session(self) -> None:
        """c=17 萬、閒置 5 小時（快取已冷）：續跑重寫 34 萬 < 換新 96 萬 ⇒ RESUME，
        不 spawn 新 session。這是 R3 退役的對照事件（舊判準會在 c≥10 萬寫入時判 FRESH，方向錯）。"""
        self.transcript_with(170_000, hours_idle=5)
        self.assertEqual(self.fire(), 0)
        self.assertEqual((self.resumed, self.spawned), ([SID], []))
        self.assertEqual(park.read_marker(SID)["status"], "fired")
        self.assertIn("park_resumed", self.events())
        route = next(t for t in self.traces() if t["event"] == "park_route")
        self.assertEqual((route["route"], route["ctx"]), ("RESUME", 170_000))
        self.assertNotIn(self.label, self.backend.jobs)  # 自拆

    def test_large_cold_context_still_spawns_a_fresh_session_with_the_package(self) -> None:
        """c=60 萬、冷：續跑重寫 120 萬 > 換新 96 萬 ⇒ FRESH，沿用交接包 spawn。"""
        self.transcript_with(600_000, hours_idle=5)
        self.assertEqual(self.fire(), 0)
        self.assertEqual((self.resumed, self.spawned), ([], [self.pkg]))
        route = next(t for t in self.traces() if t["event"] == "park_route")
        self.assertEqual(route["route"], "FRESH")
        self.assertIn("park_spawned", self.events())

    def test_a_huge_but_warm_context_resumes(self) -> None:
        """反向變體：同樣 60 萬，但最後一次寫入只在 30 分鐘前（1h 層快取仍熱；且已超過 15 分鐘的
        「有人在動」寬限，不會被 live_driver 跳過）⇒ RESUME。"""
        self.transcript_with(600_000, hours_idle=0.5)
        self.assertEqual(self.fire(), 0)
        self.assertEqual((self.resumed, self.spawned), ([SID], []))

    def test_an_unreadable_transcript_keeps_the_handoff_route(self) -> None:
        """逐字稿不存在 ⇒ 量不到 ⇒ 走既有交接包路（不呼叫 `-r`）。"""
        self.assertEqual(self.fire(), 0)
        self.assertEqual((self.resumed, self.spawned), ([], [self.pkg]))

    def test_a_failed_resume_falls_back_to_the_handoff_spawn_and_records_both(self) -> None:
        """QW Q3（DES §7.5）：續跑失敗 ⇒ 改試另一條路（交接包 spawn），逐次嘗試記實際 rc；
        另一路成功 ⇒ fired。2026-11-20 22:42 事件的反面：只試一條路、失敗即靜默。"""
        self.transcript_with(170_000, hours_idle=5)
        self.rc["resume"] = 1
        self.assertEqual(self.fire(), 0)
        self.assertEqual((self.resumed, self.spawned), ([SID], [self.pkg]))
        marker = park.read_marker(SID)
        self.assertEqual(marker["status"], "fired")
        self.assertEqual([(a["route"], a["rc"]) for a in marker["outcome"]["attempts"]],
                         [("RESUME", 1), ("FRESH", 0)])
        self.assertIn("park_spawned", self.events())

    def test_both_routes_failing_writes_a_handback_that_lists_the_attempts(self) -> None:
        """兩條路都失敗 ⇒ failed、`park_chain_failed`、handback 逐次列出嘗試與 rc，rc 1。"""
        self.transcript_with(170_000, hours_idle=5)
        self.rc["resume"] = self.rc["spawn"] = 1
        self.assertEqual(self.fire(), 1)
        self.assertEqual(park.read_marker(SID)["status"], "failed")
        self.assertIn("park_chain_failed", self.events())
        text = (self.bdir / f"{SID}_park_failed.md").read_text(encoding="utf-8")
        self.assertIn("RESUME", text)
        self.assertIn("rc=1", text)

class _Runner:
    """假 runner：記下 argv／cwd／env／creationflags；回注定的 (rc, out, pid)。"""

    def __init__(self, pid=4242, rc=0) -> None:
        self.calls, self.pid, self.rc = [], pid, rc

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        return self.rc, "", self.pid


class SpawnResumeTest(_CliFence, unittest.TestCase):
    """tools/lib/sessionctl/park_cli.py::spawn_resume：開窗圍籬與成功憑證。
    WHY：開得出視窗不等於接手成功——憑證是「行程活著且原逐字稿真的變大」，否則照實回非零。"""

    def setUp(self) -> None:
        super().setUp()
        self.proj = self.tmp / "proj"
        self.proj.mkdir()
        self.transcript = self.proj / f"{SID}.jsonl"
        self.transcript.write_text("{}\n", encoding="utf-8")

    def go(self, runner, *, grow=True, alive=True, env=None, platform_name="win32"):
        def sleep(_s):
            if grow:
                with self.transcript.open("a", encoding="utf-8") as handle:
                    handle.write("{}\n")

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = park_cli.spawn_resume(SID, self.pkg, runner=runner, platform_name=platform_name,
                                       env={**self.env, **(env or {})}, projects_dir=self.proj,
                                       alive=lambda _p: alive, sleep=sleep, wait_seconds=5)
        return rc, out.getvalue(), err.getvalue()

    def test_success_needs_a_live_process_and_a_grown_transcript(self) -> None:
        runner = _Runner()
        rc, out, _err = self.go(runner)
        self.assertEqual(rc, 0)
        argv, kw = runner.calls[0]
        self.assertEqual(argv[:3], ["claude", "-r", SID])
        self.assertIn(str(self.pkg), argv[3])
        self.assertIn("重驗", argv[3])  # 硬規則二：第一個動作是重驗
        self.assertEqual(kw["cwd"], str(park_cli._REPO))
        self.assertNotIn("AUTOSDD_UNATTENDED", kw["env"])
        self.assertIn("已續跑原 session", out)
        self.assertTrue(any(t["event"] == "session_resume_spawned" and t["ok"]
                            for t in self.traces()))
        # R216 QA P2-1：續跑成功＝原主人回來，不是交棒 ⇒ 包被標記 resumed（封存作廢）
        self.assertTrue(self.pkg.with_suffix(".resumed").is_file())

    def test_a_process_that_never_writes_is_not_reported_as_success(self) -> None:
        """反向變體：行程活著但逐字稿沒變大（例如卡在 folder trust 對話框）⇒ 非零、
        說「逐字稿未增長」。"""
        rc, _out, err = self.go(_Runner(), grow=False)
        self.assertEqual(rc, 1)
        self.assertIn("逐字稿未增長", err)
        self.assertFalse(self.pkg.with_suffix(".resumed").exists(), "沒接上就不得標記續跑")
        self.assertTrue(any(t["event"] == "session_resume_spawned" and t["ok"] is False
                            for t in self.traces()))

    def test_a_dead_process_is_not_success_even_if_the_transcript_grew(self) -> None:
        rc, _out, err = self.go(_Runner(), alive=False)
        self.assertEqual(rc, 1)
        self.assertIn("行程已不在", err)

    def test_runner_failure_and_fences_never_open_a_window(self) -> None:
        """runner 失敗、無人窗口、模式非 auto、非 Windows ⇒ 一律非零；後三者連 runner 都不呼叫。"""
        self.assertEqual(self.go(_Runner(rc=1, pid=None))[0], 1)
        for kw in ({"env": {"AUTOSDD_UNATTENDED": "1"}},
                   {"env": {"AUTOSDD_SESSION_SWITCH_MODE": "notify"}},
                   {"platform_name": "linux"}):
            runner = _Runner()
            self.assertEqual(self.go(runner, **kw)[0], 1, kw)
            self.assertEqual(runner.calls, [], kw)


if __name__ == "__main__":
    unittest.main()
