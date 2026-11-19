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


def _run(roster_fn, *, cfg: watch.Cfg | None = None, clock: _Clock | None = None, quota=False,
         poll: float = 30.0, anchor=None) -> tuple[int, str, _Clock]:
    """`anchor`＝主控最後一筆 usage 記錄的 epoch（`None`＝量不到，退回 watch 啟動時刻）。
    縫一律注入：
    不讓測試去讀真實 `~/.claude/projects` 裡剛好同 sid 的逐字稿（那會讓時鐘假值與真記錄相減）。"""
    clock = clock or _Clock()
    out = io.StringIO()
    rc = watch.run(SID, cfg or watch.Cfg(), now_fn=clock.now, sleep_fn=clock.sleep, poll_sec=poll,
                   roster_fn=roster_fn, end_turn_fn=lambda a: bool(a.get("end_turn")),
                   quota_fn=lambda: quota, anchor_fn=lambda: anchor, out=out, pid=4242)
    return rc, out.getvalue(), clock


def _event(out: str) -> str:
    """末行 `WATCH_VERDICT=<事件> n=…` 的事件名。WHY：判決一律 rc 0（DEF-200-622），只看末行。"""
    last = out.strip().splitlines()[-1]
    assert last.startswith("WATCH_VERDICT="), last
    return last.split()[0].split("=", 1)[1]


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
            json.loads(watch.heartbeat_path(SID).read_text(encoding="utf-8"))))
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
            ((lambda: [_agent(last=T0)],), {"quota": True}),
            ((lambda: [_agent(last=T0 + 29, ctx=800_000)],), {"cfg": watch.Cfg(ctx_max=700_000)}),
            ((lambda: [_agent(last=T0)],), {"cfg": watch.Cfg(keepwarm_min=999)}))}
        self.assertEqual(seen, {"all_done", "quota", "budget", "stall"})
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
        first, second = self._two_rounds(("prepare", "R"), ("prepare", "R"))
        self.assertEqual(first, "quota")
        self.assertEqual(second, "keepwarm")  # 第二次不因 quota 結束，改由保溫點結束
        rows = [json.loads(x) for x in (self.tmp / "trace" / "autosdd_session_switch.jsonl")
                .read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(r["event"] == keepwarm.EV_QUOTA_LATCHED for r in rows), 1)

    def test_at_ss_21_band_upgrade_fires_again(self) -> None:
        """WHY（MU-10 閂鎖鍵漏帶級）：prepare→halt 是更嚴重的事，被前一次的閂鎖吞掉＝盲區。"""
        self.assertEqual(self._two_rounds(("prepare", "R"), ("halt", "R")), ("quota", "quota"))

    def test_a_lower_band_in_the_same_window_stays_latched(self) -> None:
        """WHY：同窗內 halt 已提醒過，讀數抖回 prepare 不該再吵一次（閂鎖記的是該窗最高帶）。"""
        self.assertEqual(self._two_rounds(("halt", "R"), ("prepare", "R")), ("quota", "keepwarm"))

    def test_at_ss_22_new_reset_window_fires_again(self) -> None:
        """WHY（MU-11 閂鎖鍵漏 reset）：閂鎖作用域＝一個 reset 窗；新窗是新的額度週期。"""
        self.assertEqual(self._two_rounds(("prepare", "R"), ("prepare", "R+5h")),
                         ("quota", "quota"))

    def test_reset_jitter_across_a_minute_boundary_is_the_same_window(self) -> None:
        """WHY（2026-11-19 00:48／00:54 主控真機）：端點 reset 落在 :59:59.99 一帶，取分鐘後在 03:59
        與 04:00 間跳；字串比對把同窗當新窗，重掛又 rc 5——閂鎖修了等於沒修。"""
        a, b = "2026-11-19T04:00:00+08:00", "2026-11-19T03:59:00+08:00"
        self.assertEqual(self._two_rounds(("prepare", a), ("prepare", b)), ("quota", "keepwarm"))
        far = "2026-11-19T09:00:00+08:00"  # 反向：真的新窗（差數小時）仍要再觸發
        self.assertEqual(self._two_rounds(("prepare", b), ("prepare", far))[1], "quota")

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
            _rc, out, _ = _run(lambda: [_agent(last=T0)], quota=("prepare", "R"))
        self.assertEqual(_event(out), "quota")
        self.assertIn("額度閂鎖", buf.getvalue())

    def test_unwritable_latch_still_fires_and_says_so(self) -> None:
        """WHY：寫不進閂鎖＝無法保證「只一次」，但絕不能因此吞掉事件。"""
        (self.tmp / "trace" / "watch").write_text("我是檔案不是目錄", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf):
            _rc, out, _ = _run(lambda: [_agent(last=T0)], quota=("prepare", "R"))
        self.assertEqual(_event(out), "quota")
        self.assertIn("額度閂鎖寫不進", buf.getvalue())

    def test_quota_disposal_row_says_a_rehang_will_not_refire(self) -> None:
        """WHY：被叫醒的主控沒有上下文，處置表是它唯一知道「重掛安全」的地方。"""
        self.assertIn("同一 reset 窗同一帶不會再觸發", watch.DISPOSAL["quota"])


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

    def test_cli_non_all_done_verdict_still_exits_rc_zero(self) -> None:
        """DEF-200-622 的真子行程鎖。WHY：舊版 quota 事件 rc 5，harness 把它顯示成「failed」；
        現在事件只看末行、行程 rc 0。種 99% 讀數讓 quota 事件成立（反向＝上一條種 1% 得
        all_done）。"""
        import quota_meter  # noqa: PLC0415
        now = datetime.now().astimezone()
        (self.tmp / "quota").mkdir()
        axis = {"kind": "five_hour", "pct": 99.0, "via": "test", "resets_at":
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
