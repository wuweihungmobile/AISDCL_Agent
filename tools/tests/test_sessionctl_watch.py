"""tools/lib/sessionctl/watch.py：背景代理監督程序（R3 WP-4A；ARCH §1.2／§4 AT-W1～W10）。

縫：時鐘／sleep／名冊／額度全以參數注入（A-3：不開任何測試用環境變數）；痕跡與心跳目錄用
`AUTOSDD_TRACE_DIR` 圍到暫存，絕不碰真實 `~/.autosdd`。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_policy_env  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402  # 模組級圍籬原語（本模組寫額度快取＝寫端）
import unattended_authz  # noqa: E402

from lib.sessionctl import switch, watch  # noqa: E402
from lib.wastecensus import supervision  # noqa: E402

_MODULE_FENCES: list[dict] = []  # 模組級圍籬 handle 堆疊（後進先出）


def setUpModule() -> None:  # 單模組直跑也不得碰真實 TEMP／快取目錄
    _MODULE_FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_MODULE_FENCES.pop())

SID = "70f1bbb5-bed3-40a6-a826-8f3b0988d55d"
T0 = 1_800_000_000.0  # 固定基準時刻（epoch 秒）
MIN = 60.0


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def _agent(aid: str = "a1", *, last: float = T0, started: float = T0, ctx: int = 1000,
           end_turn: bool | None = None) -> dict:
    row = {"id": aid, "model": "sonnet", "description": f"任務{aid}", "last_at": _iso(last),
           "started_at": _iso(started), "ctx_tokens": ctx}
    if end_turn is not None:
        row["end_turn"] = end_turn
    return row


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="wp4a-watch-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        patcher = mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tmp / "trace"),
            "AUTOSDD_HANDOFF_DIR": str(self.tmp / "handoff"),
            "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp / "quota")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in (switch.WATCH_STALL_KEY, switch.WATCH_WALL_KEY, switch.WATCH_CTX_KEY,
                    "AUTOSDD_UNATTENDED"):
            os.environ.pop(key, None)
        (self.tmp / "trace").mkdir()


class _Clock:
    """假時鐘：`sleep` 讓時間前進；`on_sleep` 可在每輪睡眠時抓現場。"""

    def __init__(self, start: float = T0, on_sleep=None) -> None:
        self.t, self.on_sleep, self.sleeps = start, on_sleep, 0

    def now(self) -> float:
        return self.t

    #: 合法案例最多睡約 100 輪（保溫點 50 分÷輪詢 30 秒）；超過＝watch 迴圈不會自己停。
    #: WHY（QA P3-1）：突變拿掉保溫判斷時，測試是無限迴圈而不是紅燈，CI 只能等 job 逾時、
    #: 也看不出根因；有上限就變成一條指名的失敗。
    MAX_SLEEPS = 10_000

    def sleep(self, sec: float) -> None:
        self.sleeps += 1
        if self.sleeps > self.MAX_SLEEPS:
            raise AssertionError(f"watch 迴圈未終止（假時鐘已睡 {self.MAX_SLEEPS:,} 輪）")
        if self.on_sleep:
            self.on_sleep(self)
        self.t += sec


def _run(roster_fn, *, cfg: watch.Cfg | None = None, clock: _Clock | None = None, quota=False,
         poll: float = 30.0) -> tuple[int, str, _Clock]:
    clock = clock or _Clock()
    out = io.StringIO()
    rc = watch.run(SID, cfg or watch.Cfg(), now_fn=clock.now, sleep_fn=clock.sleep, poll_sec=poll,
                   roster_fn=roster_fn, end_turn_fn=lambda a: bool(a.get("end_turn")),
                   quota_fn=lambda: quota, out=out, pid=4242)
    return rc, out.getvalue(), clock


class EventTests(_Fence):
    def test_w1_all_done_after_grace_when_never_seen(self) -> None:
        """AT-W1。WHY：主控派工失敗或代理瞬間交卷時，watch 不能永遠等；但剛啟動時名冊可能還空，
        所以要寬限 150 秒才當「全部交卷」。"""
        rc, out, clock = _run(lambda: [])
        self.assertEqual(rc, 0)
        self.assertIn("WATCH_VERDICT=all_done", out.splitlines()[-1])
        self.assertGreaterEqual(clock.t - T0, watch.GRACE_SECONDS)

    def test_w1b_all_done_immediately_once_seen(self) -> None:
        """AT-W1 續。WHY：曾見過代理、之後名冊清空＝真的交卷，不必再等寬限（主控越早醒越暖）。"""
        seq = iter([[_agent(last=T0 + 30)], []])
        rc, out, clock = _run(lambda: next(seq))
        self.assertEqual(rc, 0)
        self.assertIn("WATCH_VERDICT=all_done", out)
        self.assertLess(clock.t - T0, watch.GRACE_SECONDS)

    def test_w2_overrun(self) -> None:
        """AT-W2（rc 2）。WHY：代理自啟動起超過牆鐘仍未交卷＝失控，要叫醒主控決定繼續或拆小。"""
        clock = _Clock()

        def roster():
            now = clock.now()
            return [_agent(last=now, started=T0)]  # 一直有活動（不停滯），只是太久
        cfg = watch.Cfg(wall_min=10, keepwarm_min=999)
        rc, out, _ = _run(roster, cfg=cfg, clock=clock)
        self.assertEqual(rc, 2)
        self.assertIn("WATCH_VERDICT=overrun", out)

    def test_w3_stall(self) -> None:
        """AT-W3（rc 3）。WHY：代理最後一筆記錄過久＝卡死，閒置的主控沒人發現就是整段浪費。"""
        rc, out, _ = _run(lambda: [_agent(last=T0)], cfg=watch.Cfg(stall_min=15, keepwarm_min=999))
        self.assertEqual(rc, 3)
        self.assertIn("WATCH_VERDICT=stall", out)
        self.assertIn("任務a1", out)

    def test_w4_budget(self) -> None:
        """AT-W4（rc 4）。WHY：代理上下文越大每輪越貴，1M 視窗前要先叫醒主控 TaskStop。"""
        rc, out, _ = _run(lambda: [_agent(last=T0 + 29, ctx=800_000)],
        cfg=watch.Cfg(ctx_max=700_000))
        self.assertEqual(rc, 4)
        self.assertIn("WATCH_VERDICT=budget", out)

    def test_w5_quota(self) -> None:
        """AT-W5（rc 5）。WHY：主控閒置期間額度警報沒人聽（PostToolUse 只在主控呼叫工具時出聲）。"""
        rc, out, _ = _run(lambda: [_agent(last=T0 + 29)], quota=True)
        self.assertEqual(rc, 5)
        self.assertIn("WATCH_VERDICT=quota", out)

    def test_w6_keepwarm(self) -> None:
        """AT-W6（rc 6）。WHY：主控快取 1 小時；在冷掉前叫醒主控重掛，避免交卷時整份重寫。"""
        clock = _Clock()
        rc, out, _ = _run(lambda: [_agent(last=clock.now(), started=clock.now())],
                          cfg=watch.Cfg(wall_min=9999), clock=clock)
        self.assertEqual(rc, 6)
        self.assertIn("WATCH_VERDICT=keepwarm", out)
        self.assertGreaterEqual(clock.t - T0, 50 * MIN)

    def test_w6_keepwarm_boundary_in_decide(self) -> None:
        """保溫點邊界（QA P3-1）。WHY：只靠常數值斷言與迴圈時，拿掉 `decide` 的保溫判斷不會紅
        （迴圈卡住）；這條直接釘「watch 啟動滿 50 分成立、差 1 秒不成立」。"""
        agents = [_agent(last=T0, started=T0)]
        cfg = watch.Cfg(wall_min=9999)
        self.assertEqual(watch.decide(agents, T0, T0 - 50 * MIN, cfg, False)[0], "keepwarm")
        self.assertIsNone(watch.decide(agents, T0, T0 - 50 * MIN + 1, cfg, False))

    def test_w7_end_turn_agent_is_not_stalled(self) -> None:
        """AT-W7（FR-W3）。WHY：代理已 end_turn 在等自己的背景 shell 時合法長時間靜默，判 stall
        是誤醒。"""
        agents = [_agent(last=T0 - 20 * MIN, end_turn=True)]
        self.assertIsNone(watch.decide(agents, T0, T0 - 5, watch.Cfg(keepwarm_min=999), False))
        agents[0]["end_turn"] = False
        self.assertEqual(watch.decide(agents, T0, T0 - 5, watch.Cfg(keepwarm_min=999), False)[0],
                         "stall")

    def test_event_order_is_pinned(self) -> None:
        """先後次序（quota＞budget＞stall＞overrun＞all_done＞keepwarm）。WHY：同輪多事件時，
        主控只看到一個判決——要先講不可逆／最貴的（額度牆、預算），保溫最輕所以排最後。"""
        cfg = watch.Cfg(stall_min=15, wall_min=10, ctx_max=100, keepwarm_min=1)
        agents = [_agent(last=T0 - 60 * MIN, started=T0 - 60 * MIN, ctx=500)]
        names = []
        for quota in (True, False):
            for ctx in (500, 1):
                ag = [dict(agents[0], ctx_tokens=ctx)]
                names.append(watch.decide(ag, T0, T0 - 3600, cfg, quota)[0])
        self.assertEqual(names, ["quota", "quota", "budget", "stall"])
        ag = [_agent(last=T0, started=T0 - 60 * MIN, ctx=1)]
        self.assertEqual(watch.decide(ag, T0, T0 - 3600, cfg, False)[0], "overrun")
        self.assertEqual(watch.decide([], T0, T0 - 3600, cfg, False)[0], "all_done")
        self.assertEqual(watch.decide(ag, T0, T0 - 3600, watch.Cfg(wall_min=9999, keepwarm_min=1),
                                      False)[0], "keepwarm")
        self.assertEqual(watch.ORDER, ("quota", "budget", "stall", "overrun", "all_done",
        "keepwarm"))

    def test_disposal_row_and_rc_table(self) -> None:
        """判決後印 ARCH §1.5 對應列＋rc 表固定。WHY：被叫醒的主控沒有上下文，處置要隨判決一起印。
        """
        rc, out, _ = _run(lambda: [_agent(last=T0)], cfg=watch.Cfg(keepwarm_min=999))
        self.assertIn(watch.DISPOSAL["stall"], out)
        self.assertEqual(watch.RC, {"all_done": 0, "overrun": 2, "stall": 3, "budget": 4,
                                    "quota": 5, "keepwarm": 6})
        self.assertEqual(rc, watch.RC["stall"])

    def test_verdict_is_traced_with_the_shared_event_name(self) -> None:
        """WHY：sessionctl 不得 import wastecensus（A-8），事件名兩邊各定義——這條防它們漂開。"""
        self.assertEqual(watch.EV_WATCH_VERDICT, supervision.EV_WATCH_VERDICT)
        _run(lambda: [_agent(last=T0)], cfg=watch.Cfg(keepwarm_min=999))
        rows = (self.tmp / "trace" / "autosdd_session_switch.jsonl").read_text(
            encoding="utf-8").splitlines()
        row = json.loads(rows[-1])
        self.assertEqual((row["event"], row["verdict"], row["rc"]), ("watch_verdict", "stall", 3))

    def test_watch_module_does_not_import_wastecensus(self) -> None:
        """A-8。WHY：守衛面不依賴量測探針，也避免 engine-bridge 閉包連動。"""
        src = Path(watch.__file__).read_text(encoding="utf-8")
        self.assertNotIn("wastecensus", src.replace("`wastecensus`", "").replace("wastecensus.",
        ""))


class ConfigTests(_Fence):
    def test_w8_stall_floor_is_11(self) -> None:
        """AT-W8。WHY：前景工具逾時上限 600 秒；門檻低於 11 分會把合法的長指令誤判停滯。"""
        for kwargs, env in (({"stall_min": 5}, {}), ({}, {switch.WATCH_STALL_KEY: "5"})):
            buf = io.StringIO()
            with redirect_stderr(buf):
                cfg = watch.resolve_cfg(env, **kwargs)
            self.assertEqual(cfg.stall_min, 15)
            self.assertIn("下限", buf.getvalue())
        self.assertEqual(watch.resolve_cfg({switch.WATCH_STALL_KEY: "20"}).stall_min, 20)
        self.assertEqual(watch.resolve_cfg({}, stall_min=11).stall_min, 11)

    def test_w9_ctx_only_downward(self) -> None:
        """AT-W9。WHY：放大上限＝代理可無限長大，每輪都更貴；只准下修（env 與 CLI 兩處）。"""
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.assertEqual(watch.resolve_cfg({switch.WATCH_CTX_KEY: "900000"}).ctx_max, 700_000)
            self.assertEqual(watch.resolve_cfg({}, ctx_max=900_000).ctx_max, 700_000)
        self.assertEqual(watch.resolve_cfg({switch.WATCH_CTX_KEY: "500000"},
        ctx_max=400_000).ctx_max,
                         400_000)
        self.assertIn(switch.WATCH_CTX_KEY, switch._DOWNWARD_ONLY)

    def test_wall_and_defaults_come_from_env_spec(self) -> None:
        """WHY：出廠值唯一的家是 ENV_SPEC，watch 常數與它漂開時退回值會不一致。"""
        spec = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        self.assertEqual(spec[switch.WATCH_STALL_KEY], watch.STALL_DEFAULT_MINUTES)
        self.assertEqual(spec[switch.WATCH_WALL_KEY], watch.WALL_DEFAULT_MINUTES)
        self.assertEqual(spec[switch.WATCH_CTX_KEY], watch.Cfg().ctx_max)
        self.assertEqual(watch.resolve_cfg({switch.WATCH_WALL_KEY: "30"}).wall_min, 30)
        self.assertEqual(watch.resolve_cfg({switch.WATCH_WALL_KEY: "30"}, wall_min=45).wall_min, 45)

    def test_keepwarm_constant_is_below_cache_lifetime(self) -> None:
        """方向鎖。WHY：主控快取壽命 1 小時；保溫點 ≥ 60 分就等於沒保溫（醒來時快取已冷）。"""
        self.assertLess(watch.KEEPWARM_MINUTES, 60)
        self.assertEqual(watch.keepwarm_minutes({}), watch.KEEPWARM_MINUTES)

    def test_keepwarm_in_unattended_window_stays_below_harness_ceiling(self) -> None:
        """WHY：無人窗口 harness 會在背景等待上限把行程全停掉；keepwarm 必須先於它醒。"""
        ceiling = unattended_authz.RESUME_BG_WAIT_CEILING_SECONDS / 60
        got = watch.keepwarm_minutes({"AUTOSDD_UNATTENDED": "1"})
        self.assertEqual(got, min(watch.KEEPWARM_MINUTES, ceiling - 5))
        with mock.patch.object(unattended_authz, "RESUME_BG_WAIT_CEILING_SECONDS", 600):
            self.assertEqual(watch.keepwarm_minutes({"AUTOSDD_UNATTENDED": "1"}), 5)


class HeartbeatTests(_Fence):
    def test_w10_heartbeat_rewritten_each_round_with_offset(self) -> None:
        """AT-W10。WHY：WP-4B 的憑證判準靠心跳新鮮度分辨「watch 活著」與「卡死」；時間戳不帶 offset
        會在跨時區／DST 時算錯。"""
        seen: list[dict] = []

        def grab(clock: _Clock) -> None:
            seen.append(json.loads(watch.heartbeat_path(SID).read_text(encoding="utf-8")))

        clock = _Clock(on_sleep=grab)
        calls = {"n": 0}

        def roster():
            calls["n"] += 1
            return [_agent(last=clock.now(), started=clock.now())] if calls["n"] < 4 else []
        rc, _out, _ = _run(roster, cfg=watch.Cfg(keepwarm_min=999, wall_min=9999), clock=clock)
        self.assertEqual(rc, 0)
        self.assertEqual(len(seen), 3)
        stamps = [row["heartbeat_at"] for row in seen]
        self.assertEqual(len(set(stamps)), 3)  # 每輪覆寫（值在變）
        for row in seen:
            self.assertEqual(row["schema"], "autosdd.watch/1")
            self.assertEqual(row["pid"], 4242)
            for key in ("started_at", "heartbeat_at", "keepwarm_at"):
                self.assertIsNotNone(datetime.fromisoformat(row[key]).tzinfo, key)
            self.assertEqual((row["stall_min"], row["wall_min"], row["ctx_max"]), (15, 9999,
            700_000))
        self.assertFalse(watch.heartbeat_path(SID).exists())  # 結束時刪除

    def test_heartbeat_path_lives_under_trace_dir_watch(self) -> None:
        """WHY：WP-4B 與 status 讀同一個路徑函式，不各算各的。"""
        self.assertEqual(watch.heartbeat_path(SID), self.tmp / "trace" / "watch" / f"{SID}.json")


class RealReaderTests(_Fence):
    def _agent_file(self, lines: list[dict]) -> Path:
        folder = self.tmp / "projects" / SID / "subagents"
        folder.mkdir(parents=True)
        path = folder / "agent-a1.jsonl"
        path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
        return path

    def test_ended_turn_reads_last_message_record(self) -> None:
        """FR-W3 的讀檔函式。WHY：只有「最後一筆是 assistant end_turn」才豁免；最後是 tool_use 或
        user（工具結果）＝還在做事，不能豁免。"""
        end = {"type": "assistant", "message": {"stop_reason": "end_turn"}}
        tool = {"type": "assistant", "message": {"stop_reason": "tool_use"}}
        base = str(self.tmp / "projects")
        path = self._agent_file([tool, end, {"type": "system"}])
        self.assertTrue(watch.ended_turn(SID, "a1", base))
        path.write_text("\n".join(json.dumps(x) for x in (end, tool)) + "\n", encoding="utf-8")
        self.assertFalse(watch.ended_turn(SID, "a1", base))
        self.assertFalse(watch.ended_turn(SID, "nope", base))

    def test_cli_all_done_after_shortened_grace(self) -> None:
        """CLI 層。WHY：子行程真跑 `sessionctl.py watch`——驗分派、sid 解析、rc
        與末行（寬限以參數縮短）。隔離額度快取先種一份新鮮低水位讀數：空目錄會讓子行程的
        `pace_state` 拿真憑證量真額度（2026-11-17 nightly 短窗過門檻 ⇒ rc 5＝quota）。"""
        import quota_meter  # noqa: PLC0415
        now = datetime.now().astimezone()
        (self.tmp / "quota").mkdir()
        axis = {"kind": "five_hour", "pct": 1.0, "via": "test", "resets_at":
                datetime.fromtimestamp(now.timestamp() + 7200).astimezone().isoformat()}
        self.assertTrue(quota_meter.write_cache({"schema": quota_meter.SCHEMA, "axes": [axis],
            "measured_at": now.isoformat(timespec="seconds")}, quota_meter.cache_path()))
        (self.tmp / "projects" / SID).mkdir(parents=True)
        env = {**os.environ, "PYTHONUTF8": "1"}
        proc = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"), "watch", "--sid", SID,
             "--projects-dir", str(self.tmp / "projects"), "--grace-sec", "1", "--poll-sec", "0.2"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("WATCH_VERDICT=all_done", proc.stdout)

    def test_cli_without_sid_is_rc2(self) -> None:
        """WHY：沒有 sid 就不知道看管誰；靜默亂猜會看管到別的 session。"""
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
        proc = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"), "watch"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60, check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("CLAUDE_CODE_SESSION_ID", proc.stderr)


if __name__ == "__main__":
    unittest.main()
