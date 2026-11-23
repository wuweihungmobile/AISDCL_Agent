"""tools/lib/sessionctl/keepwarm.py：主控快取保溫（R216；TCS-SessionSwitch-CostModel AT-SS-02、
10～19）。

目標（掌舵者 2026-11-18「專注在不要讓Cache過期!」）：主控無背景工作、人離開時，在快取（1 小時）
與閒置
自動壓縮（約 55 分）之前叫醒一次只讀快取。縫：假時鐘／tmp 逐字稿／`env` mapping／
`AUTOSDD_TRACE_DIR` 與 `AUTOSDD_HANDOFF_DIR` 圍到暫存；不開任何測試用環境變數、不 monkeypatch
被測模組
（唯一的 mock 是把 park 的排程載具探測關掉，與 test_sessionctl_converge 同一條圍籬）。
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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_policy_env  # noqa: E402

from lib.sessionctl import converge, holder, keepwarm, midwork, switch, watch  # noqa: E402

SID = "5b0c2f6e-7a41-4c1d-9d0e-3a52c1d8e911"
T0 = datetime(2026, 11, 18, 12, 0, 0, tzinfo=UTC).timestamp()
MIN = 60.0
HOOK = _REPO_ROOT / ".claude" / "hooks" / "sessionctl_guard.py"


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def _asst(epoch: float, ctx: int = 400_000, **extra) -> dict:
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    return {"type": "assistant", "timestamp": _iso(epoch),
            "message": {"id": f"m{epoch}", "usage": usage}, **extra}


def _human(epoch: float, text: str = "請繼續") -> dict:
    return {"type": "user", "timestamp": _iso(epoch), "origin": {"kind": "human"},
            "message": {"role": "user", "content": text}}


def _no_refresh(_now):
    raise RuntimeError("測試：補量端點不可用")


class _Clock:
    """假時鐘：`sleep` 讓時間前進；`on_sleep` 可在每輪睡眠時動逐字稿。"""

    def __init__(self, start: float, on_sleep=None) -> None:
        self.t, self.on_sleep, self.sleeps = start, on_sleep, 0

    def now(self) -> float:
        return self.t

    def sleep(self, sec: float) -> None:
        self.sleeps += 1
        if self.sleeps > 10_000:
            raise AssertionError("keepwarm 迴圈未終止（假時鐘已睡 10,000 輪）")
        if self.on_sleep:
            self.on_sleep(self)
        self.t += sec


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="kw-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.slug, self.hdir, self.tdir = (self.tmp / n for n in ("slug", "handoff", "traces"))
        for folder in (self.slug, self.hdir, self.tdir):
            folder.mkdir()
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tdir),
                                             "AUTOSDD_HANDOFF_DIR": str(self.hdir)})
        patch.start()
        self.addCleanup(patch.stop)
        for key in ("AUTOSDD_UNATTENDED", keepwarm.OFF_ENV, keepwarm.MINUTES_KEY,
                    switch.MODE_KEY):
            os.environ.pop(key, None)
        carrier = mock.patch("lib.sessionctl.park._has_carrier", return_value=False)
        carrier.start()
        self.addCleanup(carrier.stop)
        self.path = self.slug / f"{SID}.jsonl"

    def write(self, *records: dict) -> Path:
        self.path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        return self.path

    def append(self, *records: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(json.dumps(r) for r in records) + "\n")

    def run_kw(self, clock: _Clock, *, env=None, t_kw: float = 45, **seams) -> tuple[int, str]:
        """額度讀數縫預設＝量不到（⇒ 無目標＝periodic，R216 行為）；補量縫預設拋例外。不讓測試
        去讀這台機器的真額度快取或打真端點。"""
        out = io.StringIO()
        seams.setdefault("read_quota", lambda _now: None)
        seams.setdefault("refresh", _no_refresh)
        rc = keepwarm.run(SID, self.path, t_kw_min=t_kw, env={**self.env, **(env or {})},
                          now_fn=clock.now, sleep_fn=clock.sleep, poll_sec=60.0, out=out, **seams)
        return rc, out.getvalue()

    def ledger(self, pings: int, human: str = "") -> None:
        path = keepwarm.ledger_path(SID, write=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema": keepwarm.SCHEMA, "pings": pings, "human": human}),
                        encoding="utf-8")

    def stop(self, **extra) -> dict:
        return {"hook_event_name": "Stop", "session_id": SID, "transcript_path": str(self.path),
                **extra}

    def package(self, *, acked: bool) -> None:
        """已封存的交接包（`.sealed`）；`acked` 再加 `.ack` ＝已交棒。"""
        pkg = self.hdir / f"{SID}_20261118T000000Z.md"
        pkg.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n", encoding="utf-8")
        pkg.with_suffix(".sealed").write_text(datetime.now(UTC).isoformat() + "\n",
                                              encoding="utf-8")
        if acked:
            pkg.with_suffix(".ack").write_text("ok", encoding="utf-8")

    def traces(self) -> list[dict]:
        target = self.tdir / "autosdd_session_switch.jsonl"
        return ([json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]
                if target.exists() else [])

    def reset_state(self) -> None:
        """清交接包、park 標記、保溫帳：逐情形隔離（subTest 之間不得互相污染判準輸入）。"""
        for folder in (self.hdir, self.tdir / "park", self.tdir / "keepwarm"):
            if folder.is_dir():
                for item in folder.iterdir():
                    item.unlink()


class CostAndConfigTest(_Base):
    def test_at_ss_02_n_star_matches_the_f1_ski_rental_table(self) -> None:
        """AT-SS-02（MU-01／02）。WHY：n*＝floor(放冷重寫價 W_CC1·c ÷ 每次保溫價 2·W_CR·c＋P_FIX)；
        用 5m 層寫價 1.25 或漏乘 2（只算一回合讀取）都會得到別的數，保溫次數就不再是損益平衡點。"""
        self.assertEqual([keepwarm.n_star(c) for c in (400_000, 150_000, 30_000)], [9, 8, 5])
        self.assertEqual(keepwarm.n_star(0), 0)

    def test_t_kw_is_45_and_env_only_lowers_it_with_a_floor_of_15(self) -> None:
        """WHY：45 分＝早於閒置約 55 分的自動壓縮；放寬（>45）就越過那條線、壓太低（<15）每小時
        叫醒四次以上、保溫成本反而超過所避免的重寫。出廠值唯一的家是 ENV_SPEC。"""
        spec = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        self.assertEqual(spec[keepwarm.MINUTES_KEY], keepwarm.DEFAULT_MINUTES)
        self.assertEqual(keepwarm.t_kw_minutes({}), 45)
        buf = io.StringIO()
        with redirect_stderr(buf):
            got = [keepwarm.t_kw_minutes({keepwarm.MINUTES_KEY: v})
                   for v in ("30", "60", "10", "x")]
        self.assertEqual(got, [30, 45, 15, 45])
        self.assertIn("只准下修", buf.getvalue())
        self.assertIn("下限", buf.getvalue())


class AnchorTest(_Base):
    def test_anchor_is_the_last_assistant_record_with_usage(self) -> None:
        """AT-SS-10。WHY：快取是從最後一次真的打 API 起算；之後的 user／system／無 usage
        記錄不續命。"""
        self.write(_asst(T0), _asst(T0 + 5 * MIN),
                   {"type": "user", "timestamp": _iso(T0 + 9 * MIN), "message": {"content": "x"}},
                   {"type": "system", "timestamp": _iso(T0 + 9 * MIN)})
        self.assertEqual(keepwarm.anchor(self.path), T0 + 5 * MIN)
        self.assertEqual(keepwarm.deadline(self.path, 45), T0 + 50 * MIN)

    def test_anchor_skips_synthetic_and_sidechain_records(self) -> None:
        """WHY：`<synthetic>`（harness 補的零用量記錄）與子代理側鏈不是主控打過的 API，拿它們當錨點
        會把保溫點推遲、讓主控快取先冷。"""
        synth = _asst(T0 + 20 * MIN)
        synth["message"]["model"] = "<synthetic>"
        self.write(_asst(T0), synth, _asst(T0 + 30 * MIN, isSidechain=True))
        self.assertEqual(keepwarm.anchor(self.path), T0)

    def test_anchor_is_none_without_any_usage_record_or_file(self) -> None:
        """WHY：量不到就是量不到——呼叫端據此 skip／退回舊錨，不得拿 mtime 或現在時刻湊一個。"""
        self.write({"type": "user", "timestamp": _iso(T0), "message": {"content": "x"}})
        self.assertIsNone(keepwarm.anchor(self.path))
        self.assertIsNone(keepwarm.anchor(None))
        self.assertIsNone(keepwarm.anchor(self.tmp / "nope.jsonl"))


class RunTest(_Base):
    def test_at_ss_10_fires_exactly_at_anchor_plus_45_minutes(self) -> None:
        """AT-SS-10（MU-06 截止 45→55）。WHY：指令啟動於最後記錄後 10 分鐘，截止仍是記錄＋45 分；
        44:59 不得提早叫醒（白花一次保溫價），45:00 一到就要醒（再晚就進入閒置壓縮的風險帶）。"""
        self.write(_asst(T0))
        clock = _Clock(T0 + 10 * MIN)
        rc, out = self.run_kw(clock)
        self.assertEqual(rc, 0)  # DEF-200-622：判決一律 rc 0，harness 才不會把 ping 顯示成 failed
        self.assertEqual(clock.t - T0, 45 * MIN)
        lines = out.splitlines()
        self.assertEqual(lines[-1], "KEEPWARM_VERDICT=ping k=1 n=9")
        self.assertEqual(lines[-2], f"處置：{keepwarm.DISPOSAL['ping']}")  # 處置列在判決行之前
        ledger = json.loads(keepwarm.ledger_path(SID).read_text(encoding="utf-8"))
        self.assertEqual(ledger["pings"], 1)

    def test_at_ss_11_new_record_pushes_the_deadline_back(self) -> None:
        """AT-SS-11（MU-05 錨 started_at）。WHY：人回來工作時主控又打了 API，快取等於剛續命；若仍在
        原截止叫醒，就是白付一次保溫價。截止必須跟著最後一筆記錄走，不是跟著指令啟動時刻。"""
        self.write(_asst(T0))
        woke: list[float] = []

        def on_sleep(clock: _Clock) -> None:
            if not woke and clock.t >= T0 + 30 * MIN:
                woke.append(clock.t)
                self.append(_asst(clock.t))

        clock = _Clock(T0 + 1 * MIN, on_sleep=on_sleep)
        rc, out = self.run_kw(clock)
        self.assertEqual((rc, out.splitlines()[-1].split()[0]), (0, "KEEPWARM_VERDICT=ping"))
        self.assertEqual(clock.t, woke[0] + 45 * MIN)  # 不是 T0+45

    def test_at_ss_12_last_ping_is_cap_and_says_dont_rehang(self) -> None:
        """AT-SS-12。WHY：ski-rental 到損益點（n*）就收手——再保溫比放冷重寫更貴；處置列必須叫主控
        「不重掛」，否則它會照 ping 的慣性一直掛下去、成本無界。"""
        self.write(_asst(T0))
        self.ledger(pings=8)  # n*(400,000)＝9
        rc, out = self.run_kw(_Clock(T0 + 44 * MIN))
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[-1], "KEEPWARM_VERDICT=cap k=9")
        self.assertIn("不重掛", keepwarm.DISPOSAL["cap"])
        self.assertFalse(hasattr(keepwarm, "RC"), "不再留一張會被誤用的 rc 表")

    def test_a_ledger_already_at_the_cap_ends_without_waiting(self) -> None:
        """WHY：被誤重掛時不得再常駐一小時才說「已達上限」——立刻 cap，省下一個空等的背景任務。"""
        self.write(_asst(T0))
        self.ledger(pings=9)
        clock = _Clock(T0 + 1 * MIN)
        rc, out = self.run_kw(clock)
        self.assertEqual((rc, clock.sleeps, out.splitlines()[-1]),
                         (0, 0, "KEEPWARM_VERDICT=cap k=9"))

    def test_at_ss_13_real_prompt_resets_pings_but_machine_notifications_do_not(self) -> None:
        """AT-SS-13（MU-07）。WHY：人回來並說話＝新的一輪閒置，保溫帳從零算；但
        `<task-notification>`
        是機器注入，歸零它會讓背景任務一直通知就永遠達不到 cap（成本無界）。"""
        self.write(_asst(T0), _human(T0 + 1 * MIN, "第一句"), _asst(T0 + 2 * MIN))
        mark = keepwarm.human_mark(self.path)
        self.assertTrue(mark.endswith("|2"))
        self.ledger(pings=3, human=mark)
        self.append(_human(T0 + 3 * MIN, "<task-notification>done</task-notification>"),
                    _asst(T0 + 4 * MIN))
        self.assertEqual(keepwarm.load_ledger(SID, self.path)["pings"], 3)  # 機器注入不歸零
        self.append(_human(T0 + 5 * MIN, "我回來了"), _asst(T0 + 6 * MIN))
        self.assertEqual(keepwarm.load_ledger(SID, self.path)["pings"], 0)  # 真人提示歸零
        rc, out = self.run_kw(_Clock(T0 + 6 * MIN))
        self.assertEqual((rc, out.splitlines()[-1]), (0, "KEEPWARM_VERDICT=ping k=1 n=9"))

    def test_at_ss_14_every_skip_condition_ends_at_once_with_its_reason(self) -> None:
        """AT-SS-14（REQ-QW-20 改：不再有 park 一格）。WHY：不掛的情形必須立刻 rc 0 結束（不得常駐
        一個永遠不會有用的背景任務）：無人窗口（print 模式背景上限會殺掉它）、模式非 auto、
        AUTOSDD_KEEPWARM_OFF、已交棒、上下文太小（重寫便宜）；park 標記有效不再是不掛的理由——
        park 只是備援，主載具照掛（見 test_sessionctl_keepwarm_q2.py）。"""
        for name, env, ctx, setup in (
                ("unattended", {"AUTOSDD_UNATTENDED": "1"}, 400_000, None),
                ("mode", {switch.MODE_KEY: "notify"}, 400_000, None),
                ("off", {keepwarm.OFF_ENV: "1"}, 400_000, None),
                ("handed_over", {}, 400_000, lambda: self.package(acked=True)),
                ("small_ctx", {}, 20_000, None)):
            with self.subTest(name):
                self.reset_state()
                self.write(_asst(T0, ctx=ctx))
                if setup:
                    setup()
                clock = _Clock(T0 + 1 * MIN)
                rc, out = self.run_kw(clock, env=env)
                self.assertEqual((rc, clock.sleeps), (0, 0))
                self.assertEqual(out.splitlines()[-1], f"KEEPWARM_VERDICT=skip reason={name}")

    def test_a_sealed_but_not_handed_over_session_is_still_kept_warm(self) -> None:
        """WHY（MU-08 的另一面）：只封存、在等掌舵者的 session 正是最該保溫的——封存不等於不掛。"""
        self.write(_asst(T0))
        self.package(acked=False)
        self.assertEqual(keepwarm.skip_reason(SID, self.env, ctx=400_000), "")

    def test_a_self_resumed_session_is_kept_warm_but_a_real_hand_over_is_not(self) -> None:
        """R216 QA P2-1（掌舵者主軸「不要讓 Cache 過期」）：park RESUME／自己 `--ack` 回到原 session
        後，保溫不得因 handed_over 失效。三格：自己 sid 的 ack ⇒ 保溫；別的 sid 的 ack ⇒ 跳過
        （真交棒，反向變體）；續跑標記（`seal.mark_resumed`）清掉自己 sid 的 ack ⇒ 保溫；
        舊格式 ack（無從分辨）不被續跑標記抹掉，仍保守視為別人接手（R216 複審 P3-a）。"""
        from lib.sessionctl import seal  # noqa: PLC0415
        self.write(_asst(T0))
        self.package(acked=False)
        pkg = next(self.hdir.glob("*.md"))
        for text, want in ((f"acked x sid={SID}", ""), ("acked x sid=other-sid", "handed_over")):
            with self.subTest(text=text):
                pkg.with_suffix(".ack").write_text(text, encoding="utf-8")
                self.assertEqual(keepwarm.skip_reason(SID, self.env, ctx=400_000), want)
        pkg.with_suffix(".ack").write_text("acked x", encoding="utf-8")  # 舊格式＝本機殘留形態
        self.assertEqual(keepwarm.skip_reason(SID, self.env, ctx=400_000), "handed_over")
        self.assertTrue(seal.mark_resumed(pkg))
        self.assertTrue(pkg.with_suffix(".ack").exists(), "舊格式 ack 無從分辨，續跑標記不得抹掉")
        pkg.with_suffix(".ack").write_text(f"acked x sid={SID}", encoding="utf-8")
        self.assertTrue(seal.mark_resumed(pkg))
        self.assertEqual(keepwarm.skip_reason(SID, self.env, ctx=400_000), "")

    def test_p3_1_the_same_reset_window_boundary_is_pinned(self) -> None:
        """P3-1（QA 突變 M12／M13 存活）：reset 觀測值抖動容差＝300 秒、含邊界。300 秒＝同窗、
        301 秒＝新窗、3600 秒＝新窗（視窗以小時計，容差不可大到把真的新窗吃掉）。WHY：`<=` 改 `<`
        或 300 改 3600 都不會被任何其他測試看見，卻會讓 watch 重掛立刻再 rc 5 或漏報真新窗。"""
        base = "2026-11-19T04:00:00+00:00"
        for delta, same in ((0, True), (299, True), (300, True), (301, False), (3600, False),
                            (-300, True), (-301, False)):
            other = (datetime.fromisoformat(base) + timedelta(seconds=delta)).isoformat()
            self.assertEqual(keepwarm._same_reset(base, other), same, delta)
        self.assertFalse(keepwarm._same_reset(base, "壞掉的時刻"), "解析失敗＝照觸發")
        self.assertTrue(keepwarm._same_reset("壞", "壞"), "字面相同即同窗")
        self.assertEqual(keepwarm.RESET_JITTER_SECONDS, 300)

    def test_a_ledger_that_cannot_be_written_ends_as_cap_and_says_so(self) -> None:
        """WHY：寫不進保溫帳就沒有 n* 的計數基礎；繼續保溫＝成本無界，停止保溫＝退回沒有保溫的現況
        （失效往少花走，PRD §1.2 原則 5）。"""
        self.write(_asst(T0))
        (self.tdir / "keepwarm").write_text("我是檔案不是目錄", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc, out = self.run_kw(_Clock(T0 + 44 * MIN))
        self.assertEqual(rc, 0)
        self.assertEqual(out.splitlines()[-1], "KEEPWARM_VERDICT=cap k=9")
        self.assertIn("保溫帳寫不進", buf.getvalue())

    def test_a_broken_ledger_reads_as_zero_and_says_so(self) -> None:
        """WHY：壞檔不得讓指令崩潰（崩潰＝沒人叫醒主控＝快取過期）；當零並出聲。"""
        self.write(_asst(T0))
        path = keepwarm.ledger_path(SID, write=True)
        path.parent.mkdir(parents=True)
        path.write_text("{壞", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stderr(buf):
            self.assertEqual(keepwarm.read_ledger(SID)["pings"], 0)
        self.assertIn("保溫帳", buf.getvalue())

    def test_the_verdict_is_traced_with_the_shared_event_name(self) -> None:
        """WHY：sessionctl 不得 import wastecensus，事件名兩邊各定義——量測端（M-K5）靠它入帳。"""
        self.assertEqual(keepwarm.EV_VERDICT, "keepwarm_verdict")
        self.write(_asst(T0))
        self.run_kw(_Clock(T0 + 44 * MIN))
        row = self.traces()[-1]
        self.assertEqual((row["event"], row["verdict"], row["k"]), ("keepwarm_verdict", "ping", 1))
        self.assertNotIn("rc", row)


class WakeBudgetTest(_Base):
    """R217 WP-A4（REQ-WP-31／32／34；AT-WP-32／33／35）：watch 與 keepwarm 指令共用保溫錨與保溫帳，
    同一 sid 不會被兩個行程各叫醒一次（M-WB2：舊 session 14 天 21 次重複叫醒）。"""

    def _foreign_holder(self, *, start: str | None = None) -> int:
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        target = holder.path(SID, write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        stamp = holder.start_token(proc.pid) or "" if start is None else start
        target.write_text(json.dumps({"pid": proc.pid, "proc_start": stamp}), encoding="utf-8")
        return proc.pid

    def _watch(self, clock: _Clock) -> tuple[int, str]:
        """真 `WakeBudget`（讀同一份逐字稿與保溫帳）＋無代理的名冊，證明共用的是同一本帳。"""
        out = io.StringIO()
        rc = watch.run(SID, watch.Cfg(), now_fn=clock.now, sleep_fn=clock.sleep, poll_sec=60.0,
                       roster_fn=lambda: [], quota_fn=lambda: False, out=out, pid=4242,
                       projects_dir=str(self.slug), read_quota=lambda _now: None,
                       refresh=_no_refresh)
        return rc, out.getvalue()

    def test_at_wp_32_a_live_holder_makes_the_second_keepwarm_skip_with_rc_zero(self) -> None:
        """AT-WP-32／AT-WP-35／MU-WP-31。WHY：同 sid 已有保溫持有者（watch 或另一個 keepwarm）
        在叫醒時，
        第二個行程再等到截止叫醒＝同一個保溫點叫醒主控兩次；它必須立刻、rc 0（DEF-200-622：
        正常判決不得顯示成 failed）、不睡、不碰保溫帳地結束。"""
        self.write(_asst(T0))
        self._foreign_holder()
        clock = _Clock(T0 + 1 * MIN)
        rc, out = self.run_kw(clock)
        self.assertEqual((rc, clock.sleeps), (0, 0))
        self.assertEqual(out.splitlines()[-1], "KEEPWARM_VERDICT=skip reason=holder_running")
        self.assertFalse(keepwarm.ledger_path(SID).exists())

    def test_a_dead_or_pid_reused_holder_is_taken_over_and_released_at_the_end(self) -> None:
        """AT-WP-32 的接手格。WHY：持有者行程已死、或 pid 被別的行程重用（建立時間不符）＝鬼佔著；
        不接手
        ＝之後每個保溫都 skip、快取保溫從此失效。結束時必須釋放，下一個持有者才拿得到錨。"""
        self.write(_asst(T0))
        cases = [("dead", lambda: (holder.path(SID, write=True).parent.mkdir(
            parents=True, exist_ok=True), holder.path(SID, write=True).write_text(
                json.dumps({"pid": 2_999_999, "proc_start": ""}), encoding="utf-8")))]
        if holder.start_token(os.getpid()):  # 取得到建立時間的平台才有「重用」這一格
            cases.append(("reused", lambda: self._foreign_holder(start="0")))
        for name, setup in cases:
            with self.subTest(name):
                self.reset_state()
                setup()
                rc, out = self.run_kw(_Clock(T0 + 44 * MIN))
                self.assertEqual((rc, out.splitlines()[-1]), (0, "KEEPWARM_VERDICT=ping k=1 n=9"))
                self.assertFalse(holder.path(SID).exists(), "結束必須釋放保溫錨")

    def test_the_holder_is_released_even_when_the_run_ends_as_skip_or_cap(self) -> None:
        """WHY：任何結局都釋放，不只 ping（finally）；漏釋放＝下一次保溫被自己留下的鬼擋住。"""
        self.write(_asst(T0))
        self.ledger(pings=8)
        self.run_kw(_Clock(T0 + 44 * MIN))  # 第 9 次＝cap
        self.assertFalse(holder.path(SID).exists())

    def test_at_wp_33_watch_and_keepwarm_share_one_ping_ledger(self) -> None:
        """AT-WP-33／MU-WP-32。WHY：watch 的 keepwarm 事件收一次費，之後 keepwarm 指令看到的是
        同一本帳——各算各的，預算上限 n* 就會被繞過（兩邊各叫 n* 次）。帳預置 n*−1：watch 叫醒一次
        （仍是 `keepwarm`，因為叫醒當下還有預算），帳達 n* ⇒ keepwarm 指令立即印 cap、不睡。"""
        self.write(_asst(T0))
        self.ledger(pings=8)  # n*(400,000)＝9
        rc, out = self._watch(_Clock(T0 + 1 * MIN))
        self.assertEqual((rc, out.splitlines()[-1]), (0, "WATCH_VERDICT=keepwarm n=0"))
        self.assertEqual(json.loads(keepwarm.ledger_path(SID).read_text(encoding="utf-8"))["pings"],
                         9)
        clock = _Clock(T0 + 46 * MIN)
        rc, out = self.run_kw(clock)
        self.assertEqual((rc, clock.sleeps, out.splitlines()[-1]),
                         (0, 0, "KEEPWARM_VERDICT=cap k=9"))

    def test_watch_at_the_cap_ends_as_cap_uncharged_and_idle_when_not_applicable(self) -> None:
        """AT-WP-37 的真帳版（MU-WP-11）。WHY：全部交卷後 watch 帳已達上限 ⇒ cap、不再收費；保溫
        不適用（此處用 AUTOSDD_KEEPWARM_OFF）⇒ idle；兩者都讓行程結束（不是永遠掛著）。"""
        self.write(_asst(T0))
        self.ledger(pings=9)
        rc, out = self._watch(_Clock(T0 + 1 * MIN))
        self.assertEqual((rc, out.splitlines()[-1]), (0, "WATCH_VERDICT=cap n=0"))
        self.assertIn("不重掛", out)
        self.assertEqual(json.loads(keepwarm.ledger_path(SID).read_text(encoding="utf-8"))["pings"],
                         9)
        self.reset_state()
        with mock.patch.dict(os.environ, {keepwarm.OFF_ENV: "1"}):
            rc, out = self._watch(_Clock(T0 + 1 * MIN))
        self.assertEqual((rc, out.splitlines()[-1]), (0, "WATCH_VERDICT=idle n=0"))

    def test_at_wp_34_the_ping_row_says_rehang_the_same_command_and_make_no_judgement(self) -> None:
        """AT-WP-34。WHY：被叫醒的主控沒有上下文，處置列是它唯一知道
        「什麼都不用判、重掛同一指令、結束回合」的地方；
        少了這句，它會跑 status、讀名冊、寫一大段分析＝一叫三回合（M-WB1）。keepwarm
        指令與 watch 的 keepwarm 列同一句。"""
        phrase = "重掛同一指令並結束回合，不做任何判斷"
        self.assertIn(phrase, keepwarm.DISPOSAL["ping"])
        self.assertIn(phrase, watch.DISPOSAL["keepwarm"])
        self.write(_asst(T0))
        _rc, out = self.run_kw(_Clock(T0 + 44 * MIN))
        self.assertIn(phrase, out)


class StopGateTest(_Base):
    def test_at_ss_15_pushes_back_once_when_nothing_would_wake_the_session(self) -> None:
        """AT-SS-15。WHY：結束回合後沒有任何背景工作會叫醒主控＝快取會冷、閒置 55 分還會被壓縮；
        推回要把指令（含 sid）與次數交代清楚，第二次 Stop（stop_hook_active）放行。"""
        self.write(_asst(T0 + 100 * MIN, ctx=400_000))
        for tasks in ([], [{"id": "b1", "type": "shell", "status": "completed"}]):
            with self.subTest(tasks=tasks):
                text = keepwarm.stop_verdict(self.stop(background_tasks=tasks), self.env)
                self.assertIn("sessionctl.py keepwarm", text)
                self.assertIn(f"--sid {SID}", text)
                self.assertIn("最多 9 次", text)
        self.assertEqual(keepwarm.stop_verdict(self.stop(background_tasks=[],
                                                         stop_hook_active=True), self.env), "")
        self.assertIn("keepwarm_stop_block", [r["event"] for r in self.traces()])

    def test_at_ss_16_any_running_background_task_means_the_session_has_a_waker(self) -> None:
        """AT-SS-16（MU-09）。WHY：有 running 背景任務（watch／keepwarm／等 CI…）它一結束就會叫醒
        主控，這時再推回＝重複掛、白花錢；舊 harness 沒有 background_tasks 欄＝量不到＝不判。"""
        self.write(_asst(T0, ctx=400_000))
        running = {"id": "b1", "type": "shell", "status": "running", "command": "x"}
        self.assertEqual(keepwarm.stop_verdict(self.stop(background_tasks=[running]), self.env), "")
        self.assertEqual(keepwarm.stop_verdict(self.stop(), self.env), "")

    def test_the_gate_is_silent_when_the_ledger_is_at_the_cap_or_the_case_is_skipped(self) -> None:
        """WHY：pings ≥ n* 時再推回＝叫它掛一個馬上 cap 的任務；不掛的情形（無人／已交棒／小上下文）
        同理，推回只會製造空轉。"""
        self.write(_asst(T0, ctx=400_000))
        self.ledger(pings=9)
        payload = self.stop(background_tasks=[])
        self.assertEqual(keepwarm.stop_verdict(payload, self.env), "")
        self.ledger(pings=0)
        self.assertNotEqual(keepwarm.stop_verdict(payload, self.env), "")
        self.assertEqual(
            keepwarm.stop_verdict(payload, {**self.env, "AUTOSDD_UNATTENDED": "1"}), "")
        self.assertEqual(keepwarm.stop_verdict(payload, {**self.env, keepwarm.OFF_ENV: "1"}), "")
        self.package(acked=True)
        self.assertEqual(keepwarm.stop_verdict(payload, self.env), "")
        self.reset_state()  # 上面已交棒的包清掉，單獨驗「上下文太小」這一個條件
        self.write(_asst(T0, ctx=20_000))
        self.assertEqual(keepwarm.stop_verdict(self.stop(background_tasks=[]), self.env), "")

    def test_at_ss_17_seal_gate_comes_before_the_keepwarm_gate_in_one_message(self) -> None:
        """AT-SS-17。WHY：大上下文又沒封存時兩閘都成立——合併成一則（每回合至多一次推回），次序
        封存→保溫：先把資訊交代進交接包，再談閒置時怎麼保溫。R216：「大」＝過硬線 850,000
        （掌舵者裁決不設軟線，原稿的 60 萬已不在封存線上）。"""
        self.write(_asst(T0, ctx=900_000))
        text = converge.stop_verdict(self.stop(background_tasks=[]), self.env)
        self.assertIn("封存閘", text)
        self.assertIn("保溫閘", text)
        self.assertLess(text.index("封存閘"), text.index("保溫閘"))

    def test_at_ss_18_wake_gate_exempts_keepwarm_only_when_sealed_but_not_handed_over(self) -> None:
        """AT-SS-18（MU-08）。WHY：只封存、在等掌舵者時，keepwarm 的叫醒讀的是熱快取，不該被冷叫醒閘
        要求 TaskStop；已交棒（spawn／ack）後任何背景任務醒來都是整份重寫，豁免套到這裡就是
        把冷叫醒閘（DEF-200-588）拆了。豁免只認 keepwarm 指令，別的 shell 照舊。"""
        self.write(_asst(T0, ctx=200_000))
        kw = {"id": "b1", "type": "shell", "status": "running",
              "command": f"python tools/sessionctl.py keepwarm --sid {SID}"}
        other = {"id": "b2", "type": "shell", "status": "running", "command": "pytest -q"}
        self.package(acked=False)
        self.assertEqual(converge.stop_verdict(self.stop(background_tasks=[kw]), self.env), "")
        self.assertIn("冷叫醒閘", converge.stop_verdict(self.stop(background_tasks=[kw, other]),
                                                      self.env))
        self.package(acked=True)
        text = converge.stop_verdict(self.stop(background_tasks=[kw]), self.env)
        self.assertIn("冷叫醒閘", text)
        self.assertIn("1 個", text)

    def test_at_ss_19_a_running_keepwarm_is_not_an_event_source_for_the_midwork_judge(self) -> None:
        """AT-SS-19 → R217 REQ-WP-22／AT-WP-25（取代原斷言）。WHY：keepwarm 只叫醒主控「ping
        保溫」、
        不做任何工作；主控說要接著做事卻只剩保溫 shell ⇒ 仍是半路停工（2026-11-19 事故：保溫 shell
        掩蓋了判準）。原斷言（保溫 shell 算事件源）被 R217 凍結規格明文推翻；判準單一家＝
        `roster.is_supervision_shell`。"""
        running = {"id": "b1", "type": "shell", "status": "running",
                   "command": "python tools/sessionctl.py keepwarm --sid x"}
        self.assertTrue(midwork.background_idle({"background_tasks": [running]}))
        self.assertTrue(midwork.background_idle({"background_tasks": []}))
        self.assertTrue(keepwarm.is_keepwarm_task(running))
        self.assertFalse(keepwarm.is_keepwarm_task(dict(running, command="python watch")))
        self.assertFalse(keepwarm.is_keepwarm_task(dict(running, type="subagent")))
        # PowerShell 形態：腳本路徑後帶引號（DEF-200-615 同族）；字面子字串比對會漏
        quoted = dict(running, command="& 'py.exe' 'tools\\sessionctl.py' keepwarm --sid x")
        self.assertTrue(keepwarm.is_keepwarm_task(quoted))


def _hook(payload: dict, env_extra: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items()
           if k not in ("AUTOSDD_UNATTENDED", "AUTOSDD_SESSIONCTL_GUARD_OFF", keepwarm.OFF_ENV)}
    env.update({"PYTHONUTF8": "1", "AUTOSDD_PARK_GUARD_OFF": "1", **env_extra})
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, encoding="utf-8", errors="replace", timeout=60,
                          check=False, cwd=str(_REPO_ROOT), env=env)


class ProcessLevelTest(_Base):
    """真行程：最終路徑的 hook 與 `tools/sessionctl.py keepwarm`（不經模組縫）。"""

    def test_the_real_stop_hook_emits_the_keepwarm_block(self) -> None:
        """E2E-SS-06 的單元層對照。WHY：判準合成在 `converge.stop_verdict`，hook 檔本身不需改動；
        這條用真 hook 子行程證明 Stop payload 進去、`decision:block`＋保溫閘文字出來（hook 套用
        前後都要綠）。"""
        self.write(_asst(T0, ctx=400_000))
        # WHY：hook 內「完成閘讓路」讀 `CLAUDE_PROJECT_DIR` 下的真 OIR 帳本；帳本有 undriven 項
        # 就讓路、保溫閘靜默（CI 簽出的已提交帳本即如此）。指到空目錄＝讀不到＝不讓路，
        # 測試才不隨 repo 帳本內容與平台的行程存活判準漂移。
        iso = {"AUTOSDD_TRACE_DIR": str(self.tdir), "AUTOSDD_HANDOFF_DIR": str(self.hdir),
               "CLAUDE_PROJECT_DIR": str(self.tdir)}
        proc = _hook(self.stop(background_tasks=[]), iso)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["decision"], "block")
        self.assertIn("保溫閘", doc["reason"])
        quiet = _hook(self.stop(background_tasks=[{"id": "b", "type": "shell",
                                                   "status": "running"}]), iso)
        self.assertNotIn("保溫閘", quiet.stdout)

    def test_the_cli_pings_for_real_once_the_anchor_is_old_enough(self) -> None:
        """CLI 層。WHY：子行程真跑 `sessionctl.py keepwarm`——驗分派、sid／projects-dir 解析、`--min`
        （實測用的正式參數）、rc 6 與末行。逐字稿最後記錄是 3 分鐘前、`--min 1` ⇒ 立即到期。"""
        self.write(_asst(datetime.now(UTC).timestamp() - 3 * MIN))
        env = {**os.environ, "PYTHONUTF8": "1", "AUTOSDD_TRACE_DIR": str(self.tdir),
               "AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        proc = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"), "keepwarm", "--sid", SID,
             "--projects-dir", str(self.slug), "--min", "1", "--poll-sec", "0.2"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)  # DEF-200-622：ping 不得再是 rc 6
        self.assertEqual(proc.stdout.strip().splitlines()[-1], "KEEPWARM_VERDICT=ping k=1 n=9")
        self.assertIn("低於建議下限", proc.stderr)  # --min < 15 出聲

    def test_the_cli_refuses_to_raise_the_cutoff_and_needs_a_sid(self) -> None:
        """WHY：`--min` 只准下修（放寬就越過閒置壓縮線）；沒有 sid 不得亂猜保溫哪個 session。"""
        self.write(_asst(T0))
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
        env.update({"PYTHONUTF8": "1", "AUTOSDD_TRACE_DIR": str(self.tdir),
                    keepwarm.OFF_ENV: "1"})
        cli = [sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"), "keepwarm"]
        proc = subprocess.run([*cli, "--sid", SID, "--projects-dir", str(self.slug),
                               "--min", "100"],
                              capture_output=True, text=True, encoding="utf-8", env=env,
                              timeout=60, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("只准下修", proc.stderr)
        self.assertIn("skip reason=off", proc.stdout)
        bare = subprocess.run(cli, capture_output=True, text=True, encoding="utf-8", env=env,
                              timeout=60, check=False)
        self.assertEqual(bare.returncode, 2)


if __name__ == "__main__":
    unittest.main()
