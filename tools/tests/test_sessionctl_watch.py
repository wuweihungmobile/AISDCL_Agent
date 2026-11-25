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

from lib.sessionctl import keepwarm, switch, watch  # noqa: E402
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

    #: 合法案例最多睡約 100 輪（保溫點 45 分÷輪詢 30 秒）；超過＝watch 迴圈不會自己停。
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


class _Budget:
    """叫醒預算的縫（`keepwarm.WakeBudget` 形狀）：`why`＝不掛原因（空＝適用）、`pings`／`star`＝
    保溫帳與上限；`charge` 記下被收費的次數並照 `saved` 回報是否寫進帳
    （真帳的行為另有整合測試）。"""

    def __init__(self, why: str = "", pings: int = 0, star: int = 9, saved: bool = True) -> None:
        self.why, self.pings, self.star, self.saved = why, pings, star, saved
        self.checks, self.charged = 0, []

    def check(self) -> tuple[str, int, int, int]:
        self.checks += 1
        return self.why, self.pings, self.star, 400_000

    def charge(self, pings: int, ctx: int, star: int) -> bool:
        self.charged.append((pings + 1, ctx, star))
        return self.saved


def _no_refresh(_now):
    raise RuntimeError("測試：補量端點不可用")


def _run(roster_fn, *, cfg: watch.Cfg | None = None, clock: _Clock | None = None, quota=False,
         poll: float = 30.0, anchor=None, budget: _Budget | None = None, pid: int = 4242,
         plan_fn=None) -> tuple[int, str, _Clock]:
    """`anchor`＝主控最後一筆 usage 記錄的 epoch（`None`＝量不到，退回 watch 啟動時刻）。
    縫一律注入：
    不讓測試去讀真實 `~/.claude/projects` 裡剛好同 sid 的逐字稿（那會讓時鐘假值與真記錄相減）。"""
    clock = clock or _Clock()
    out = io.StringIO()
    rc = watch.run(SID, cfg or watch.Cfg(), now_fn=clock.now, sleep_fn=clock.sleep, poll_sec=poll,
                   roster_fn=roster_fn, end_turn_fn=lambda a: bool(a.get("end_turn")),
                   quota_fn=lambda: quota, anchor_fn=lambda: anchor, out=out, pid=pid,
                   budget=budget or _Budget(), read_quota=lambda _now: None, refresh=_no_refresh,
                   plan_fn=plan_fn)
    return rc, out.getvalue(), clock


def _event(out: str) -> str:
    """末行 `WATCH_VERDICT=<事件> n=…` 的事件名。WHY：判決一律 rc 0（DEF-200-622），只看末行。"""
    last = out.strip().splitlines()[-1]
    assert last.startswith("WATCH_VERDICT="), last
    return last.split()[0].split("=", 1)[1]


class EventTests(_Fence):
    def test_at_wp_30_all_delivered_does_not_end_the_watch_no_all_done_event(self) -> None:
        """AT-WP-30／MU-WP-06。WHY：harness 對每支背景子代理完成都會送 task-notification；watch 再因
        「全部交卷」退出＝同一事件叫醒主控兩次（M-WB2＝14 天 21 次，每次冷讀 40 萬～99 萬 token）。
        所以全部交卷（曾見過代理後名冊清空、或從來沒有代理）watch 都不退出，輪詢一直走到保溫點
        才由保溫族結束；ORDER、處置表、CLI 都不得再有 `all_done`。"""
        self.assertNotIn("all_done", watch.ORDER)
        self.assertNotIn("all_done", watch.DISPOSAL)
        seq = iter([[_agent(last=T0 + 30)]])  # 先有代理、之後名冊清空
        clock = _Clock()
        rc, out, clock = _run(lambda: next(seq, []), clock=clock)
        self.assertEqual((rc, _event(out)), (0, "keepwarm"))
        self.assertGreaterEqual(clock.t - T0, 45 * MIN)  # 交卷那一刻不退出，等到保溫點
        self.assertGreater(clock.sleeps, 10)
        # 反向：從來沒有代理（過去的寬限期備援）也不會在寬限後就退出
        rc2, out2, clock2 = _run(lambda: [])
        self.assertEqual((rc2, _event(out2)), (0, "keepwarm"))
        self.assertGreaterEqual(clock2.t - T0, 45 * MIN)

    def test_at_wp_31_after_all_delivered_the_point_wakes_once_with_keepwarm_and_charges_a_ping(
            self) -> None:
        """AT-WP-31／REQ-WP-36。WHY：全部交卷後 watch 只在保溫點再叫醒一次（不與 harness 的完成通知
        重疊），而且這一次要算進共用的保溫帳——否則 watch 與 keepwarm 各算各的、預算形同虛設。"""
        budget = _Budget(pings=3, star=9)
        rc, out, clock = _run(lambda: [], budget=budget)
        self.assertEqual((rc, _event(out)), (0, "keepwarm"))
        self.assertEqual(budget.charged, [(4, 400_000, 9)])
        self.assertIn(watch.DISPOSAL["keepwarm"], out)
        self.assertEqual(clock.t - T0, 45 * MIN)

    def test_w2_overrun(self) -> None:
        """AT-W2。WHY：代理自啟動起超過牆鐘仍未交卷＝失控，要叫醒主控決定繼續或拆小。"""
        clock = _Clock()

        def roster():
            now = clock.now()
            return [_agent(last=now, started=T0)]  # 一直有活動（不停滯），只是太久
        cfg = watch.Cfg(wall_min=10, keepwarm_min=999)
        rc, out, _ = _run(roster, cfg=cfg, clock=clock)
        self.assertEqual((rc, _event(out)), (0, "overrun"))

    def test_w3_stall(self) -> None:
        """AT-W3。WHY：代理最後一筆記錄過久＝卡死，閒置的主控沒人發現就是整段浪費。"""
        rc, out, _ = _run(lambda: [_agent(last=T0)], cfg=watch.Cfg(stall_min=15, keepwarm_min=999))
        self.assertEqual((rc, _event(out)), (0, "stall"))
        self.assertIn("任務a1", out)

    def test_w4_budget(self) -> None:
        """AT-W4。WHY：代理上下文越大每輪越貴，1M 視窗前要先叫醒主控 TaskStop。"""
        rc, out, _ = _run(lambda: [_agent(last=T0 + 29, ctx=800_000)],
                          cfg=watch.Cfg(ctx_max=700_000))
        self.assertEqual((rc, _event(out)), (0, "budget"))

    def test_w5_quota(self) -> None:
        """AT-W5。WHY：主控閒置期間額度警報沒人聽（PostToolUse 只在主控呼叫工具時出聲）。"""
        rc, out, _ = _run(lambda: [_agent(last=T0 + 29)], quota=True)
        self.assertEqual((rc, _event(out)), (0, "quota"))

    def test_w6_keepwarm(self) -> None:
        """AT-W6。WHY：主控快取 1 小時；在冷掉前叫醒主控重掛，避免交卷時整份重寫。"""
        clock = _Clock()
        rc, out, _ = _run(lambda: [_agent(last=clock.now(), started=clock.now())],
                          cfg=watch.Cfg(wall_min=9999), clock=clock)
        self.assertEqual((rc, _event(out)), (0, "keepwarm"))
        self.assertGreaterEqual(clock.t - T0, 45 * MIN)

    def test_w6_keepwarm_boundary_in_decide(self) -> None:
        """保溫點邊界（QA P3-1）。WHY：只靠常數值斷言與迴圈時，拿掉 `decide` 的保溫判斷不會紅
        （迴圈卡住）；這條直接釘「錨點（量不到時為 watch 啟動）滿 45 分成立、差 1 秒不成立」。
        45 分＝R216 保溫截止（早於閒置約 55 分的自動壓縮）；改回 50 分這條會紅。"""
        agents = [_agent(last=T0, started=T0)]
        cfg = watch.Cfg(wall_min=9999)
        self.assertEqual(watch.decide(agents, T0, T0 - 45 * MIN, cfg, False)[0], "keepwarm")
        self.assertIsNone(watch.decide(agents, T0, T0 - 45 * MIN + 1, cfg, False))

    def test_at_ss_24_keepwarm_is_anchored_on_the_last_main_record_not_on_watch_start(self) -> None:
        """AT-SS-24（MU-05）。WHY：主控在 watch 執行前已閒置 10 分鐘——快取是從主控最後一筆請求起算
        的，不是從 watch 啟動起算；錨 started_at 會晚 10 分鐘叫醒、越過閒置自動壓縮的邊緣。"""
        clock = _Clock(start=T0 + 10 * MIN)  # watch 啟動於 T0+10，主控最後記錄 T0
        rc, out, clock = _run(lambda: [_agent(last=clock.now(), started=clock.now())],
                              cfg=watch.Cfg(wall_min=9999), clock=clock, anchor=T0)
        self.assertEqual((rc, _event(out)), (0, "keepwarm"))
        self.assertEqual(clock.t - T0, 45 * MIN)  # 於 T0+45 判 keepwarm（不是 T0+55）
        # 反向：錨點新（主控剛剛才動過）⇒ 保溫點往後延，不因 watch 啟動久了而提早叫醒
        late = T0 + 50 * MIN
        decided = watch.decide([_agent(last=late, started=late)], late, T0, watch.Cfg(
            wall_min=9999), False, kw_anchor=T0 + 40 * MIN)
        self.assertIsNone(decided)

    def test_heartbeat_keepwarm_at_follows_the_anchor(self) -> None:
        """WHY：`status`／Stop 出聲的「下次叫醒最晚 HH:MM」讀心跳的 keepwarm_at；錨點變了它不跟著
        變，主控看到的叫醒時間就是假的。"""
        seen: list[dict] = []
        clock = _Clock(on_sleep=lambda c: seen.append(
            json.loads(watch.heartbeat_path(SID, 4242).read_text(encoding="utf-8"))))
        _run(lambda: [_agent(last=clock.now(), started=clock.now())],
             cfg=watch.Cfg(wall_min=9999), clock=clock, anchor=T0 - 10 * MIN)
        stamp = datetime.fromisoformat(seen[0]["keepwarm_at"]).timestamp()
        self.assertEqual(stamp, T0 - 10 * MIN + 45 * MIN)

    def test_w7_end_turn_agent_is_not_stalled(self) -> None:
        """AT-W7（FR-W3）。WHY：代理已 end_turn 在等自己的背景 shell 時合法長時間靜默，判 stall
        是誤醒。"""
        agents = [_agent(last=T0 - 20 * MIN, end_turn=True)]
        self.assertIsNone(watch.decide(agents, T0, T0 - 5, watch.Cfg(keepwarm_min=999), False))
        agents[0]["end_turn"] = False
        self.assertEqual(watch.decide(agents, T0, T0 - 5, watch.Cfg(keepwarm_min=999), False)[0],
                         "stall")

    def test_at_wp_37_keepwarm_family_after_all_delivered(self) -> None:
        """AT-WP-37／MU-WP-11。WHY：全部交卷後 watch 在保溫點只有三種結局，而且每一種都要行程結束
        （否則 watch 永不退出＝一個永遠掛著的背景任務）：(a) 帳已達 n* ⇒ cap（再叫醒比放冷更貴）、
        (b) 保溫不適用（無人窗口…）⇒ idle、(c) 還有預算 ⇒ keepwarm；(d) 還沒到保溫點就不退出。
        (a) 回到「達上限後不退出」的舊稿行為時，這條會變成假時鐘跑滿 10,000 輪而指名失敗。"""
        for name, budget, want in (("a", _Budget(pings=9, star=9), "cap"),
                                   ("b", _Budget(why="unattended"), "idle"),
                                   ("c", _Budget(pings=2, star=9), "keepwarm")):
            with self.subTest(name):
                rc, out, clock = _run(lambda: [], budget=budget)
                self.assertEqual((rc, _event(out)), (0, want))
                self.assertEqual(clock.t - T0, 45 * MIN)
                self.assertEqual(budget.charged != [], want == "keepwarm")  # 只有 keepwarm 收費
                self.assertIn(watch.DISPOSAL[want], out)
        # (d)：保溫點前不呼叫預算、不退出（用 decide 直接釘邊界，避免靠時鐘上限的間接失敗）
        probe = _Budget()
        self.assertIsNone(watch.decide([], T0, T0 - 45 * MIN + 1, watch.Cfg(), False,
                                       kw_verdict=lambda: probe.check()[0] or "keepwarm"))
        self.assertEqual(probe.checks, 0)

    def test_cap_with_agents_still_running_is_silent_but_keepwarm_and_idle_still_end(self) -> None:
        """REQ-WP-36 的邊界。WHY：代理還在跑時保溫預算已用完——再為保溫叫醒主控只是白付一次冷讀，
        watch 繼續看管代理（stall／overrun…仍有效）；而 keepwarm（還有預算）與 idle（不適用，例如
        無人窗口 harness 會在背景等待上限殺掉 watch，主控必須先被叫醒）照舊退出。"""
        live = [_agent(last=T0 + 45 * MIN, started=T0 + 45 * MIN)]
        cfg = watch.Cfg(wall_min=9999)
        self.assertIsNone(
            watch.decide(live, T0 + 45 * MIN, T0, cfg, False, kw_verdict=lambda: "cap")
        )
        self.assertEqual(watch.decide(live, T0 + 45 * MIN, T0, cfg, False,
                                      kw_verdict=lambda: "idle")[0], "idle")
        self.assertEqual(watch.decide(live, T0 + 45 * MIN, T0, cfg, False,
                                      kw_verdict=lambda: "keepwarm")[0], "keepwarm")
        # 整條迴圈：cap 時不退出，直到代理停滯（stall）這個實質事件
        budget = _Budget(pings=9, star=9)
        rc, out, _ = _run(lambda: [_agent(last=T0, started=T0)], budget=budget,
                          cfg=watch.Cfg(wall_min=9999, stall_min=60))
        self.assertEqual((rc, _event(out)), (0, "stall"))
        self.assertEqual(budget.checks, 1)  # 錨點沒變 ⇒ cap 結果快取，不每輪重讀逐字稿與帳

    def test_a_ledger_that_cannot_be_charged_ends_as_cap(self) -> None:
        """WHY（與 keepwarm 指令同一原則）：寫不進保溫帳＝沒有計數基礎，繼續叫醒成本無界；停止叫醒
        ＝退回沒有保溫的現況。"""
        rc, out, _ = _run(lambda: [], budget=_Budget(pings=1, star=9, saved=False))
        self.assertEqual((rc, _event(out)), (0, "cap"))

    def test_verdict_trace_carries_the_budget_numbers_for_the_keepwarm_family(self) -> None:
        """WHY：量測端（M-WB／M-K5）從痕跡讀 pings／n*；
        沒有它就只能事後猜每次叫醒花了預算的哪一格。"""
        _run(lambda: [], budget=_Budget(pings=4, star=9))
        row = json.loads((self.tmp / "trace" / "autosdd_session_switch.jsonl").read_text(
            encoding="utf-8").splitlines()[-1])
        self.assertEqual((row["verdict"], row["pings"], row["n_star"]), ("keepwarm", 4, 9))

    def test_event_order_is_pinned(self) -> None:
        """先後次序（quota＞budget＞stall＞overrun＞保溫族）。WHY：同輪多事件時，
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
        self.assertEqual(watch.decide(ag, T0, T0 - 3600, watch.Cfg(wall_min=9999, keepwarm_min=1),
                                      False)[0], "keepwarm")
        self.assertEqual(watch.ORDER, ("handed_over", "quota", "budget", "stall", "overrun",
                                       "resume", "keepwarm", "cap", "idle"))

    def test_every_verdict_exits_rc_zero_and_the_verdict_is_the_last_line(self) -> None:
        """判決後印 ARCH §1.5 對應列、判決一律 rc 0、事件只看末行（DEF-200-622）。WHY：harness
        把背景指令的任何非 0 結束都顯示成「failed」，掌舵者真機把正常的叫醒事件（舊 rc 2～6）
        讀成錯誤；被叫醒的主控沒有上下文，處置要隨判決一起印。反向：事件名全數可由末行分辨
        （rc 不再承載資訊），且模組不再留一張會被誤用的 rc 表。"""
        rc, out, _ = _run(lambda: [_agent(last=T0)], cfg=watch.Cfg(keepwarm_min=999))
        self.assertIn(watch.DISPOSAL["stall"], out)
        self.assertEqual((rc, _event(out)), (0, "stall"))
        self.assertFalse(hasattr(watch, "RC"))
        seen = {_event(_run(*a, **k)[1]) for a, k in (
            ((lambda: [],), {}),
            ((lambda: [],), {"budget": _Budget(pings=9)}),
            ((lambda: [],), {"budget": _Budget(why="off")}),
            ((lambda: [_agent(last=T0)],), {"quota": True}),
            ((lambda: [_agent(last=T0 + 29, ctx=800_000)],), {"cfg": watch.Cfg(ctx_max=700_000)}),
            ((lambda: [_agent(last=T0)],), {"cfg": watch.Cfg(keepwarm_min=999)}))}
        self.assertEqual(seen, {"keepwarm", "cap", "idle", "quota", "budget", "stall"})
        for line in out.splitlines():
            self.assertNotIn("rc=", line)

    def test_verdict_is_traced_with_the_shared_event_name(self) -> None:
        """WHY：sessionctl 不得 import wastecensus（A-8），事件名兩邊各定義——這條防它們漂開。"""
        self.assertEqual(watch.EV_WATCH_VERDICT, supervision.EV_WATCH_VERDICT)
        _run(lambda: [_agent(last=T0)], cfg=watch.Cfg(keepwarm_min=999))
        rows = (self.tmp / "trace" / "autosdd_session_switch.jsonl").read_text(
            encoding="utf-8").splitlines()
        row = json.loads(rows[-1])
        self.assertEqual((row["event"], row["verdict"]), ("watch_verdict", "stall"))
        self.assertNotIn("rc", row)

    def test_watch_module_does_not_import_wastecensus(self) -> None:
        """A-8。WHY：守衛面不依賴量測探針，也避免 engine-bridge 閉包連動。"""
        src = Path(watch.__file__).read_text(encoding="utf-8")
        self.assertNotIn("wastecensus", src.replace("`wastecensus`", "").replace("wastecensus.",
        ""))


class HolderInterplayTests(_Fence):
    """REQ-WP-31：同 sid 只准一個保溫持有者。watch 與 keepwarm
    指令同時掛著＝同一個保溫點被叫醒兩次。"""

    def _live_other(self) -> int:
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        from lib.sessionctl import holder  # noqa: PLC0415
        target = holder.path(SID, write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"pid": proc.pid, "proc_start": holder.start_token(proc.pid)
                                      or ""}), encoding="utf-8")
        return proc.pid

    def test_at_wp_32_watch_takes_the_anchor_and_gives_it_back(self) -> None:
        """AT-WP-32（watch 側）。WHY：watch 持有期間 keepwarm 指令會 skip；watch 結束必須釋放，
        否則下一個保溫持有者永遠拿不到錨（保溫從此失效而不自知）。"""
        from lib.sessionctl import holder  # noqa: PLC0415
        mid: list[bool] = []
        clock = _Clock(on_sleep=lambda c: mid.append(holder.live_other(SID, 1) is not None))
        _run(lambda: [], clock=clock, pid=os.getpid())
        self.assertTrue(mid and all(mid), "watch 執行中，別的行程看得到持有者")
        self.assertFalse(holder.path(SID).exists())

    def test_watch_yields_the_keepwarm_family_while_another_process_holds_the_anchor(self) -> None:
        """AT-WP-35 的 watch 對偶／MU-WP-31。WHY：別的行程（keepwarm 指令）持有時，watch 在保溫點
        不得再叫醒一次（那正是重複叫醒）；持有者結束後 watch 接手，於接手後的下一輪判保溫族。"""
        from lib.sessionctl import holder  # noqa: PLC0415
        self._live_other()
        budget = _Budget()

        def release_late(clock: _Clock) -> None:
            if clock.t >= T0 + 50 * MIN and holder.path(SID).exists():
                holder.path(SID).unlink()
        rc, out, clock = _run(lambda: [], clock=_Clock(on_sleep=release_late), budget=budget)
        self.assertEqual((rc, _event(out)), (0, "keepwarm"))
        self.assertGreaterEqual(clock.t - T0, 50 * MIN)  # 45 分時沒有叫醒，持有者放手後才叫
        self.assertEqual(len(budget.charged), 1)  # 全程只收費一次

    def test_other_events_are_not_suppressed_by_a_foreign_holder(self) -> None:
        """WHY：互斥只管保溫族；代理停滯／額度牆這些實質事件，不因別人持有保溫錨就不報。"""
        self._live_other()
        rc, out, _ = _run(lambda: [_agent(last=T0)], cfg=watch.Cfg(keepwarm_min=999))
        self.assertEqual((rc, _event(out)), (0, "stall"))

    def test_a_dead_or_reused_holder_is_taken_over(self) -> None:
        """AT-WP-32 的接手格。WHY：持有者行程已死、或 pid 被別的行程重用（建立時間不符）時，不接手＝
        保溫錨永遠被鬼佔著，之後每個 watch／keepwarm 都 skip，快取保溫從此失效。"""
        from lib.sessionctl import holder  # noqa: PLC0415
        pid = self._live_other()
        row = json.loads(holder.path(SID).read_text(encoding="utf-8"))
        if row["proc_start"]:  # 取得到建立時間的平台才有「重用」這一格
            holder.path(SID).write_text(json.dumps({"pid": pid, "proc_start": "0"}),
                                        encoding="utf-8")
            self.assertTrue(holder.acquire(SID, os.getpid()))
        holder.path(SID).write_text(json.dumps({"pid": 2_999_999, "proc_start": ""}),
                                    encoding="utf-8")
        self.assertTrue(holder.acquire(SID, os.getpid()))
        holder.release(SID, os.getpid())
        self.assertFalse(holder.path(SID).exists())


class QuotaLatchTests(_Fence):
    """D14／AT-SS-20～23：prepare 帶時 `quota_hit` 每輪都成立，舊版 watch 一掛即 rc 5、重掛照樣
    觸發（2026-11-18 21:26 真機：prepare 帶內監督形同失效）。定案＝同 reset 窗同帶只觸發一次。"""

    def _two_rounds(self, first, second) -> tuple[str, str]:
        """兩次連續掛 watch 各自結束的事件名（原先用 rc 5／6 分辨，判決改一律 rc 0 後看末行）。"""
        cfg = watch.Cfg(wall_min=9999)
        events = []
        for key in (first, second):
            clock = _Clock()
            events.append(_event(_run(lambda c=clock: [_agent(last=c.now(), started=c.now())],
                                      cfg=cfg, clock=clock, quota=key)[1]))
        return events[0], events[1]

    def test_at_ss_20_same_window_same_band_fires_once(self) -> None:
        """WHY：重掛後又立刻 quota，主控就沒有任何辦法在 prepare 帶內監督代理（缺陷本體）。"""
        first, second = self._two_rounds(("WAIT_RESET", "R"), ("WAIT_RESET", "R"))
        self.assertEqual(first, "quota")
        self.assertEqual(second, "keepwarm")  # 第二次不因 quota 結束，改由保溫點結束
        rows = [json.loads(x) for x in (self.tmp / "trace" / "autosdd_session_switch.jsonl")
                .read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(r["event"] == keepwarm.EV_QUOTA_LATCHED for r in rows), 1)

    def test_at_ss_21_band_upgrade_fires_again(self) -> None:
        """WHY（MU-10 閂鎖鍵漏帶級）：prepare→halt 是更嚴重的事，被前一次的閂鎖吞掉＝盲區。"""
        self.assertEqual(self._two_rounds(("WAIT_RESET", "R"), ("HALT_WEEKLY", "R")),
                         ("quota", "quota"))

    def test_a_lower_band_in_the_same_window_stays_latched(self) -> None:
        """WHY：同窗內 halt 已提醒過，讀數抖回 prepare 不該再吵一次（閂鎖記的是該窗最高帶）。"""
        self.assertEqual(self._two_rounds(("HALT_WEEKLY", "R"), ("WAIT_RESET", "R")),
                         ("quota", "keepwarm"))

    def test_at_ss_22_new_reset_window_fires_again(self) -> None:
        """WHY（MU-11 閂鎖鍵漏 reset）：閂鎖作用域＝一個 reset 窗；新窗是新的額度週期。"""
        self.assertEqual(self._two_rounds(("WAIT_RESET", "R"), ("WAIT_RESET", "R+5h")),
                         ("quota", "quota"))

    def test_reset_jitter_across_a_minute_boundary_is_the_same_window(self) -> None:
        """WHY（2026-11-19 00:48／00:54 主控真機）：端點 reset 落在 :59:59.99 一帶，取分鐘後在 03:59
        與 04:00 間跳；字串比對把同窗當新窗，重掛又 rc 5——閂鎖修了等於沒修。"""
        a, b = "2026-11-19T04:00:00+08:00", "2026-11-19T03:59:00+08:00"
        self.assertEqual(self._two_rounds(("WAIT_RESET", a), ("WAIT_RESET", b)),
                         ("quota", "keepwarm"))
        far = "2026-11-19T09:00:00+08:00"  # 反向：真的新窗（差數小時）仍要再觸發
        self.assertEqual(self._two_rounds(("WAIT_RESET", b), ("WAIT_RESET", far))[1], "quota")

    def test_a_bare_true_from_the_seam_is_a_latchable_prepare(self) -> None:
        """WHY：舊縫回 bool；True 視為「無鍵的 prepare」也要受閂鎖管，不然舊呼叫端繞過缺陷修復。"""
        self.assertEqual(self._two_rounds(True, True), ("quota", "keepwarm"))

    def test_at_ss_23_broken_latch_file_still_fires_and_says_so(self) -> None:
        """WHY（MU-12 讀失敗時吞事件）：額度牆是不可逆的事；閂鎖壞了寧可再吵一次，也不靜默吞掉。"""
        path = keepwarm.latch_path(SID)
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf):
            _rc, out, _ = _run(lambda: [_agent(last=T0)], quota=("WAIT_RESET", "R"))
        self.assertEqual(_event(out), "quota")
        self.assertIn("額度閂鎖", buf.getvalue())

    def test_unwritable_latch_still_fires_and_says_so(self) -> None:
        """WHY：寫不進閂鎖＝無法保證「只一次」，但絕不能因此吞掉事件。"""
        (self.tmp / "trace" / "watch").write_text("我是檔案不是目錄", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf):
            _rc, out, _ = _run(lambda: [_agent(last=T0)], quota=("WAIT_RESET", "R"))
        self.assertEqual(_event(out), "quota")
        self.assertIn("額度閂鎖寫不進", buf.getvalue())

    def test_quota_disposal_row_says_a_rehang_will_not_refire(self) -> None:
        """WHY：被叫醒的主控沒有上下文，處置表是它唯一知道「重掛安全」的地方；QVD §4：首句固定為
        「先重算判決」（watch 輸出檔可能已過期）。"""
        self.assertIn("重算", watch.DISPOSAL["quota"])
        self.assertIn("同窗同動作不會再觸發", watch.watch_wake.QUOTA_DISPOSAL["NODISPATCH"])


def _plan(stage: str, n_live: int | None = 1):
    """`qw_plan.Plan` 的完整替身（`plan_lines` 要格式化全部數值欄位）。"""
    from lib.sessionctl import qw_plan  # noqa: PLC0415
    return qw_plan.Plan(stage=stage, d_min=90.0, k=2, v=20.0, limit=57.0, r=53.0, reset=T0 + 5400,
                        ping_pp=1.5, ping_pp_src="measured", n_live=n_live)


class QuotaSeriesLatchTests(_Fence):
    """tools/lib/sessionctl/{watch,watch_wake,keepwarm}.py：**單一序列**閂鎖 `(acct, ACTION, win)`
    （QVD §3.5 C4／C5，v2.1.28 取代 r9 W11d 的兩序列 REQ-QW-75／77；AT-QW-89／91 改斷言，QVD §6）。
    WHY：兩序列兩句並陳正是 E2「短窗 87% 判 prepare 又判 WAIT」自相矛盾的來源；判決只有一個動作。"""

    def _once(self, keys, *, plan=None, anchor=None) -> tuple[str, str]:
        """掛一次 watch（共用同一個閂鎖檔）；回 `(事件名, 輸出全文)`。"""
        clock = _Clock()
        rc, out, _ = _run(lambda c=clock: [_agent(last=c.now(), started=c.now())],
                          cfg=watch.Cfg(wall_min=9999), clock=clock, quota=keys,
                          plan_fn=(lambda _t, p=plan: p) if plan is not None else None)
        self.assertEqual(rc, 0)
        return _event(out), out

    def _events(self, *rounds) -> list[str]:
        return [self._once(keys, plan=plan)[0] for keys, plan in rounds]

    def test_at_qw_89_the_two_series_latch_independently(self) -> None:
        """單一序列（改寫）：PARK 已閂鎖後同窗的 WAIT_RESET（較低動作）不再出聲——不再有「另一條
        序列」可以繞過閂鎖；新 reset 窗＝乾淨起點，照觸發。MU-QV-2（恢復兩序列）⇒ 第二格轉紅。"""
        self.assertEqual(self._events(([("PARK", "R", None)], _plan("close")),
                                      ([("WAIT_RESET", "R", None)], _plan("free"))),
                         ["quota", "keepwarm"])
        self.assertEqual(self._events(([("WAIT_RESET", "R2", None)], None),), ["quota"])

    def test_at_qw_89_same_series_same_or_lower_band_stays_latched(self) -> None:
        """AT-QW-89。WHY：序列內規則不變——同級、降級不重複叫醒。"""
        close, nodis = ("PARK", "R", None), ("NODISPATCH", "R", None)
        self.assertEqual(self._events(([close], _plan("close")), ([close], _plan("close")),
                                      ([nodis], _plan("nodispatch"))),
                         ["quota", "keepwarm", "keepwarm"])
        events = self._events(([("HALT_WEEKLY", "R", None)], _plan("free")),
                              ([("WAIT_RESET", "R", None)], _plan("free")))
        self.assertEqual(events,
                         ["quota", "keepwarm"])

    def test_at_qw_89_raw_halt_still_outranks_raw_prepare(self) -> None:
        """AT-QW-89。WHY：原始讀數序列內 prepare＜halt，升級照樣再觸發。"""
        self.assertEqual(self._events(([("WAIT_RESET", "R", None)], None),
                                      ([("HALT_WEEKLY", "R", None)], None)), ["quota", "quota"])

    def test_at_qw_89_a_v1_latch_file_means_no_latch_and_no_error(self) -> None:
        """AT-QW-89。WHY：舊（單一序列）閂鎖檔讀回＝無閂鎖、fail-open，不得報錯或卡住升級後的新
        路徑。"""
        path = keepwarm.latch_path(SID)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"schema": keepwarm.SCHEMA, "sid": SID, "band": "close",
                                    "reset": "R"}), encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf):
            event, _ = self._once([("PARK", "R", None)], plan=_plan("close"))
        self.assertEqual(event, "quota")
        self.assertNotIn("額度閂鎖", buf.getvalue())
        row = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(row["schema"], keepwarm.QUOTA_LATCH_SCHEMA)
        self.assertEqual((row["action"], row["reset"]), ("PARK", "R"))

    def test_at_qw_90_new_dispatch_retriggers_once_per_increase(self) -> None:
        """AT-QW-90①②④。WHY（MU-QW-58）：閂鎖後主控又派一支代理（N 增）是新的風險，要重新評估；
        N 不增（含連續重掛）不得連發，否則回到每掛必叫的吵。"""
        nodis = ("NODISPATCH", "R", None)
        self.assertEqual(
            self._events(([nodis], _plan("NODISPATCH", 1)), ([nodis], _plan("NODISPATCH", 2)),
                         ([nodis], _plan("NODISPATCH", 2)), ([nodis], _plan("NODISPATCH", 2))),
            ["quota", "quota", "keepwarm", "keepwarm"])
        row = json.loads(keepwarm.latch_path(SID).read_text(encoding="utf-8"))
        self.assertEqual(row["n_latched"], 2)

    def test_at_qw_90_n_increase_without_a_plan_stage_does_not_fire(self) -> None:
        """AT-QW-90③。WHY：stage 未到 nodispatch（free）時 N 增是正常工作，不是額度事件。"""
        nodis = ("NODISPATCH", "R", None)
        self.assertEqual(self._events(([nodis], _plan("NODISPATCH", 1)), ([], _plan("free", 2))),
                         ["quota", "keepwarm"])

    def test_at_qw_90_a_lower_n_does_not_rearm_below_the_latched_count(self) -> None:
        """AT-QW-90 延伸。WHY：N 掉回 1 再升到 2 並非新增派工量（`n_latched` 仍是 2），不再叫醒。"""
        nodis = ("NODISPATCH", "R", None)
        self.assertEqual(
            self._events(([nodis], _plan("NODISPATCH", 2)), ([nodis], _plan("NODISPATCH", 1)),
                         ([nodis], _plan("NODISPATCH", 2))), ["quota", "keepwarm", "keepwarm"])

    def test_at_qw_91_plan_trigger_text_names_the_wall_not_the_raw_reading(self) -> None:
        """AT-QW-91 改寫（QVD C4）：事件文案＝判決行（一個判決、一句話），末行
        `WATCH_VERDICT=quota action=<A> vid=<v> expires_at=<t>`。"""
        line = "QUOTA_VERDICT=NODISPATCH acct=none win=R wk=none cap=0 vid=v1"
        _event_name, out = self._once([("NODISPATCH", "R", None, "v1", "E1", line)],
                                      plan=_plan("nodispatch"))
        self.assertIn(f"quota：{line}", out)
        self.assertIn("WATCH_VERDICT=quota action=NODISPATCH vid=v1 expires_at=E1", out)
        self.assertNotIn("原始讀數已達", out)

    def test_at_qw_91_raw_trigger_text_quotes_the_reading(self) -> None:
        """WAIT_RESET 的處置列不含 park 字樣（AC-QV-05b）。"""
        _event_name, out = self._once([("WAIT_RESET", "R", None, "v2", "E2", "QUOTA_VERDICT=WAIT")])
        how = next(x for x in out.splitlines() if x.startswith("處置："))
        self.assertIn("keepwarm", how)
        self.assertNotIn("park", how.lower())

    def test_at_qw_91_both_sources_are_stated_together(self) -> None:
        """單一序列：多把鍵同時成立只陳述最高動作那一個判決（不再兩句並陳），處置依最高動作。"""
        _event_name, out = self._once([("WAIT_RESET", "R", None, "v1", "E", "LINE-WAIT"),
                                       ("PARK", "R", None, "v2", "E", "LINE-PARK")],
                                      plan=_plan("close"))
        line = next(x for x in out.splitlines() if "quota：" in x)
        self.assertIn("LINE-PARK", line)
        self.assertNotIn("LINE-WAIT", line)
        self.assertIn(watch.watch_wake.CLOSE_STEPS, out)

    def test_a_bare_true_into_decide_does_not_claim_a_raw_reading(self) -> None:
        """AT-QW-91 延伸。WHY：呼叫端沒給來源時，文案不得冒稱「原始讀數已達」。"""
        got = watch.decide([], T0, T0, watch.Cfg(), True)
        self.assertIsNotNone(got)
        self.assertNotIn("原始讀數已達", got[1])


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
        """方向鎖。WHY：主控快取壽命 1 小時、閒置約 55 分鐘 harness 會自動壓縮；保溫點 ≥ 55 分就
        等於沒保溫（醒來時快取已冷或上下文已被砍）。出廠值唯一的家是 ENV_SPEC，常數與它漂開時
        `watch.Cfg` 預設就和 env 解析不一致。"""
        self.assertLess(watch.KEEPWARM_MINUTES, 55)
        self.assertEqual(watch.KEEPWARM_MINUTES, 45)
        self.assertEqual(watch.keepwarm_minutes({}), watch.KEEPWARM_MINUTES)
        spec = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        self.assertEqual(spec[keepwarm.MINUTES_KEY], watch.KEEPWARM_MINUTES)

    def test_keepwarm_env_only_lowers_the_watch_keepwarm_point(self) -> None:
        """WHY：env 只准下修（放寬＝保溫點越過閒置壓縮）；watch 與 keepwarm 指令吃同一個解析。"""
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.assertEqual(watch.keepwarm_minutes({keepwarm.MINUTES_KEY: "30"}), 30)
            self.assertEqual(watch.keepwarm_minutes({keepwarm.MINUTES_KEY: "60"}), 45)

    def test_keepwarm_in_unattended_window_stays_below_harness_ceiling(self) -> None:
        """WHY：無人窗口 harness 會在背景等待上限把行程全停掉；keepwarm 必須先於它醒。"""
        ceiling = unattended_authz.RESUME_BG_WAIT_CEILING_SECONDS / 60
        got = watch.keepwarm_minutes({"AUTOSDD_UNATTENDED": "1"})
        self.assertEqual(got, min(watch.KEEPWARM_MINUTES, ceiling - 5))  # 數字現查常數，不寫死
        with mock.patch.object(unattended_authz, "RESUME_BG_WAIT_CEILING_SECONDS", 600):
            self.assertEqual(watch.keepwarm_minutes({"AUTOSDD_UNATTENDED": "1"}), 5)


class HeartbeatTests(_Fence):
    def test_w10_heartbeat_rewritten_each_round_with_offset(self) -> None:
        """AT-W10。WHY：WP-4B 的憑證判準靠心跳新鮮度分辨「watch 活著」與「卡死」；時間戳不帶 offset
        會在跨時區／DST 時算錯。"""
        seen: list[dict] = []

        def grab(clock: _Clock) -> None:
            seen.append(json.loads(watch.heartbeat_path(SID, 4242).read_text(encoding="utf-8")))

        clock = _Clock(on_sleep=grab)

        def roster():
            return [_agent(last=clock.now(), started=clock.now())]
        # 保溫點 2 分鐘、輪詢 30 秒 ⇒ 前 4 輪（0／30／60／90 秒）寫心跳，第 5 輪到點結束
        rc, _out, _ = _run(roster, cfg=watch.Cfg(keepwarm_min=2, wall_min=9999), clock=clock)
        self.assertEqual(rc, 0)
        self.assertEqual(len(seen), 4)
        stamps = [row["heartbeat_at"] for row in seen]
        self.assertEqual(len(set(stamps)), 4)  # 每輪覆寫（值在變）
        for row in seen:
            self.assertEqual(row["schema"], "autosdd.watch/1")
            self.assertEqual(row["pid"], 4242)
            for key in ("started_at", "heartbeat_at", "keepwarm_at"):
                self.assertIsNotNone(datetime.fromisoformat(row[key]).tzinfo, key)
            self.assertEqual((row["stall_min"], row["wall_min"], row["ctx_max"]), (15, 9999,
                                                                                   700_000))
        self.assertFalse(watch.heartbeat_path(SID, 4242).exists())  # 結束時刪除（只刪自己的）

    def test_heartbeat_path_lives_under_trace_dir_watch(self) -> None:
        """WHY：WP-4B 與 status 讀同一個路徑函式，不各算各的；W6-W2 起檔名帶 pid。"""
        self.assertEqual(watch.heartbeat_path(SID, 7),
                         self.tmp / "trace" / "watch" / f"{SID}.7.json")


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

    def _seed_low_quota(self, pct: float) -> None:
        """隔離額度快取先種一份新鮮讀數：空目錄會讓子行程的 `pace_state` 拿真憑證量真額度
        （2026-11-17 nightly 短窗過門檻 ⇒ quota）。"""
        import quota_meter  # noqa: PLC0415
        now = datetime.now().astimezone()
        (self.tmp / "quota").mkdir(exist_ok=True)
        axis = {"kind": "five_hour", "pct": pct, "via": "test", "resets_at":
                datetime.fromtimestamp(now.timestamp() + 7200).astimezone().isoformat()}
        self.assertTrue(quota_meter.write_cache({"schema": quota_meter.SCHEMA, "axes": [axis],
            "measured_at": now.isoformat(timespec="seconds")}, quota_meter.cache_path()))

    def _cli(self, *extra: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "PYTHONUTF8": "1"}
        return subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"), "watch", "--sid", SID,
             "--projects-dir", str(self.tmp / "projects"), "--poll-sec", "0.2", *extra],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60, check=False)

    def _seed_main_transcript(self, ctx: int) -> None:
        """主控逐字稿最後一筆 usage 記錄在 50 分鐘前 ⇒ 保溫點（錨＋45 分）早已到。"""
        (self.tmp / "projects" / SID).mkdir(parents=True, exist_ok=True)
        at = datetime.now().astimezone().timestamp() - 50 * MIN
        rec = {
            "type": "assistant",
            "timestamp": datetime.fromtimestamp(at).astimezone().isoformat(),
            "message": {
                "id": "m1",
                "usage": {
                    "input_tokens": 1,
                    "cache_read_input_tokens": ctx - 1,
                    "cache_creation_input_tokens": 0,
                    "output_tokens": 7,
                },
            },
        }
        (self.tmp / "projects" / f"{SID}.jsonl").write_text(json.dumps(rec) + "\n",
                                                            encoding="utf-8")

    def test_cli_with_no_agents_ends_at_the_keepwarm_point_not_before(self) -> None:
        """CLI 層（AT-WP-30／31 的子行程對照）。WHY：真跑 `sessionctl.py watch`——驗分派、sid 解析、
        rc 與末行。沒有任何代理也不會因「全部交卷」退出；主控 50 分鐘前說過話 ⇒ 保溫點已到 ⇒
        `keepwarm`、記一次叫醒進共用帳。"""
        self._seed_low_quota(1.0)
        self._seed_main_transcript(400_000)
        proc = self._cli()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(_event(proc.stdout), "keepwarm")
        ledger = json.loads(keepwarm.ledger_path(SID).read_text(encoding="utf-8"))
        self.assertEqual(ledger["pings"], 1)
        left = list(watch.heartbeat_path(SID, 1).parent.glob(f"{SID}.*json"))
        self.assertEqual(left, [])  # 結束清心跳
        from lib.sessionctl import holder  # noqa: PLC0415
        self.assertFalse(holder.path(SID).exists(), "結束時必須釋放保溫錨")

    def test_cli_small_context_ends_as_idle_without_charging(self) -> None:
        """WHY：上下文太小＝重寫便宜，保溫不適用 ⇒ `idle`（不重掛）；不得記一次叫醒。"""
        self._seed_low_quota(1.0)
        self._seed_main_transcript(20_000)
        proc = self._cli()
        self.assertEqual((proc.returncode, _event(proc.stdout)), (0, "idle"))
        self.assertFalse(keepwarm.ledger_path(SID).exists())

    def test_cli_non_keepwarm_verdict_still_exits_rc_zero(self) -> None:
        """DEF-200-622 的真子行程鎖。WHY：舊版 quota 事件 rc 5，harness 把它顯示成「failed」；
        現在事件只看末行、行程 rc 0。種 99% 讀數讓 quota 事件成立（反向＝上一條種 1% 得
        keepwarm）。"""
        self._seed_low_quota(99.0)
        (self.tmp / "projects" / SID).mkdir(parents=True)
        proc = self._cli()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(_event(proc.stdout), "quota")

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
