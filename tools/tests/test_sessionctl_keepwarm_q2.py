"""tools/lib/sessionctl/kw_run.py（含 kw_wake／kw_ledger／watch_wake）：R218 QuotaWall Q2 主載具
（TCS-QuotaWall REQ-QW-20～29、65、66；AT-QW-21、23～28、35、63、65、75、78～81；
 MU-QW-29、47～51）。

縫：假時鐘、隨時鐘變化的短窗讀數（`_Quota`）、`refresh` 補量縫、tmp 逐字稿／痕跡／交接包目錄；
不開任何測試用環境變數、不 monkeypatch 被測判準。`work_mark` 的「監督」文法只認
`control.is_supervision_call`（單一家），這裡不另寫指令正則。
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_policy  # noqa: E402

from lib.sessionctl import (  # noqa: E402
    holder,
    keepwarm,
    kw_ledger,
    park,
    qw_schema,
    seal,
    switch,
    watch,
)

SID = "7d2e3f40-9b52-4d2e-8e1f-4b63d2e9f022"
T0 = datetime(2026, 11, 22, 12, 0, 0, tzinfo=UTC).timestamp()
MIN = 60.0
SKEW = 120.0  # quota_messages.HALT_RESET_SKEW_SECONDS（s＝2 分）


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def _asst(epoch: float, ctx: int = 300_000, tools=()) -> dict:
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    blocks = [{"type": "tool_use", "id": f"t{i}", "name": n, "input": inp}
              for i, (n, inp) in enumerate(tools)]
    return {"type": "assistant", "timestamp": _iso(epoch),
            "message": {"id": f"m{epoch}", "usage": usage, "content": blocks}}


def _ps(command: str) -> tuple[str, dict]:
    return "PowerShell", {"command": command}


def _no_refresh(_now):
    raise RuntimeError("測試：補量端點不可用")


class _Clock:
    def __init__(self, start: float, on_sleep=None) -> None:
        self.t, self.on_sleep, self.sleeps = start, on_sleep, 0

    def now(self) -> float:
        return self.t

    def sleep(self, sec: float) -> None:
        self.sleeps += 1
        if self.sleeps > 20_000:
            raise AssertionError("keepwarm 迴圈未終止（假時鐘已睡 20,000 輪）")
        if self.on_sleep:
            self.on_sleep(self)
        self.t += sec


class _Quota:
    """隨時鐘變化的短窗讀數：`fn(epoch)`→`(pct, reset_epoch)`｜None；讀數時刻＝現在（不陳舊）。"""

    def __init__(self, fn, age: float = 0.0) -> None:
        self.fn, self.age, self.reads = fn, age, 0

    def read(self, now: datetime):
        self.reads += 1
        got = self.fn(now.timestamp())
        if got is None:
            return None
        pct, reset = got
        axes = (quota_policy.Axis("five_hour", pct, _iso(reset)),)
        return quota_policy.QuotaState(axes, _iso(now.timestamp() - self.age), "test")


def _const(pct: float, reset: float) -> _Quota:
    return _Quota(lambda _t: (pct, reset))


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="kwq2-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.slug, self.hdir, self.tdir = (self.tmp / n for n in ("slug", "handoff", "traces"))
        for folder in (self.slug, self.hdir, self.tdir):
            folder.mkdir()
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tdir),
                                             "AUTOSDD_HANDOFF_DIR": str(self.hdir)})
        patch.start()
        self.addCleanup(patch.stop)
        for key in ("AUTOSDD_UNATTENDED", keepwarm.OFF_ENV, keepwarm.MINUTES_KEY,
                    switch.MODE_KEY):
            os.environ.pop(key, None)
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        self.path = self.slug / f"{SID}.jsonl"

    def write(self, *records: dict) -> None:
        self.path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    def append(self, *records: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(json.dumps(r) for r in records) + "\n")

    def run_kw(self, clock: _Clock, quota: _Quota | None = None, *, platform_name="win32",
               **seams) -> tuple[int, str]:
        out = io.StringIO()
        quota = quota or _Quota(lambda _t: None)
        rc = keepwarm.run(SID, self.path, t_kw_min=45, env=self.env, now_fn=clock.now,
                          sleep_fn=clock.sleep, poll_sec=60.0, out=out, read_quota=quota.read,
                          refresh=_no_refresh, platform_name=platform_name, **seams)
        return rc, out.getvalue()

    def traces(self, event: str | None = None) -> list[dict]:
        target = self.tdir / "autosdd_session_switch.jsonl"
        rows = ([json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]
                if target.exists() else [])
        return [r for r in rows if event is None or r.get("event") == event]

    def ledger(self) -> dict:
        return json.loads(keepwarm.ledger_path(SID).read_text(encoding="utf-8"))

    def package(self, *, acked: bool) -> Path:
        pkg = self.hdir / f"{SID}_20261122T000000Z.md"
        pkg.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n", encoding="utf-8")
        pkg.with_suffix(".sealed").write_text(datetime.now(UTC).isoformat() + "\n",
                                              encoding="utf-8")
        if acked:
            pkg.with_suffix(".ack").write_text("acked x sid=other-sid", encoding="utf-8")
        return pkg


def _verdict(out: str) -> str:
    return out.strip().splitlines()[-1]


def _plan_line(out: str) -> dict:
    line = next(x for x in out.splitlines() if x.startswith("KEEPWARM_PLAN"))
    return dict(re.findall(r"(\w+)=(\S+)", line))


# ═══════════════════════════════════════════════════════════════ 模式與首行
class PlanLineTest(_Base):
    """tools/lib/sessionctl/kw_run.py：首行 `KEEPWARM_PLAN`、holder 列三欄（AT-QW-23、28）。"""

    def test_chain_single_periodic_first_line_and_holder_row(self) -> None:
        """REQ-QW-28。WHY：首行是 D-K 憑證（主控要把它貼進回覆）、holder 列是 S-18 主載具憑證；
        兩者的 mode／wake_at／target_source 不一致，守衛就會把活的主載具當成沒有。"""
        reset = T0 + 100 * MIN
        for name, quota, want in (
                ("chain", _const(93, reset), ("chain", "reset", "on")),
                ("single", _const(99.5, reset), ("single", "reset", "on")),
                ("periodic", _const(40, reset), ("periodic", "none", "off"))):
            with self.subTest(name):
                self.write(_asst(T0))
                seen: list[dict | None] = []
                clock = _Clock(T0 + 1 * MIN, on_sleep=lambda c: seen.append(holder.read(SID)))
                _rc, out = self.run_kw(clock, quota)
                plan = _plan_line(out)
                self.assertEqual((plan["mode"], plan["target_source"], plan["early"]), want)
                self.assertTrue(out.splitlines()[0].startswith("KEEPWARM_PLAN"), "必須是首行")
                row = qw_schema.holder_wake(seen[0])
                self.assertEqual((row.mode, row.target_source), (want[0], want[1]))
                if name != "periodic":  # 目標＝reset＋s，而且 wake_at 欄與首行同值
                    self.assertEqual(row.wake_at, reset + SKEW)
                    self.assertEqual(plan["wake_at"], qw_schema.iso(reset + SKEW))
                self.assertIsNone(holder.read(SID), "結束必須釋放保溫錨")

    def test_chain_k_and_first_ping_follow_the_future_schedule_only(self) -> None:
        """REQ-QW-23／65、S-24。WHY：chain 只算未來還要付的 k 次；即使帳上已有 6 次歷史 ping，也不
        得因此改成 single 或 cap（歷史是沉沒成本）。第一個叫醒是錨點＋45 分的付費 ping，
        不是目標。"""
        reset = T0 + 100 * MIN
        self.write(_asst(T0))
        kw_ledger.record_ping(SID, 6, 300_000, 9, kw_ledger.human_mark(self.path),
                              work=kw_ledger.work_mark(self.path))
        clock = _Clock(T0 + 1 * MIN)
        _rc, out = self.run_kw(clock, _const(93, reset))
        plan = _plan_line(out)
        self.assertEqual((plan["mode"], plan["k"]), ("chain", "2"))
        self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=ping k=7 n=9")
        self.assertEqual(clock.t, T0 + 45 * MIN)

    def test_no_park_skip_and_marker_does_not_stop_the_carrier(self) -> None:
        """REQ-QW-20、AT-QW-75。WHY：park 只是備援；armed 標記不得讓主載具不掛（舊行為＝park 一格
        ＝每次保溫回合被要求 park、park 又讓保溫不掛，兩者互鎖）。來源 `park`、標記
        `primary_source=reset` ⇒ `early=on`；`at` ⇒ `early=off`。"""
        pkg = self.package(acked=False)
        target = T0 + 3 * 3600
        for source, early in (("reset", "on"), ("at", "off")):
            with self.subTest(source):
                self.write(_asst(T0))
                marker = {"schema": park.SCHEMA, "sid": SID, "route": park.ROUTE_DONE,
                          "status": "armed", "parked_at": datetime.now(UTC).isoformat(),
                          "valid_until": (datetime.now(UTC) + timedelta(hours=9)).isoformat(),
                          "why": "測試：還有剩餘工作", "jobs": [], "pkg": str(pkg),
                          **qw_schema.marker_extra(target, source, target + 600, False, None)}
                self.assertTrue(park.write_marker(marker)[0])
                _rc, out = self.run_kw(_Clock(T0 + 1 * MIN), _const(40, target - SKEW))
                plan = _plan_line(out)
                self.assertEqual((plan["target_source"], plan["early"]), ("park", early))
                self.assertEqual(plan["wake_at"], qw_schema.iso(target))
                self.assertNotIn("reason=park", out)


class SingleHopTest(_Base):
    """tools/lib/sessionctl/kw_run.py：付不起時退成單跳（AT-QW-21、MU-QW-47）。"""

    def test_unaffordable_or_small_context_goes_single_with_zero_pings(self) -> None:
        """REQ-QW-21。WHY：不得不掛——沒預算付費保溫時仍要在 reset 後叫醒主控（單跳到目標），否則
        牆後沒人叫它（22:42 事故的缺口）。付費次數 0、末跳恰在目標。"""
        reset = T0 + 100 * MIN
        for name, ctx, quota in (("unaffordable", 300_000, _const(99.5, reset)),
                                 ("small_ctx", 20_000, _const(96, reset))):
            with self.subTest(name):
                self.write(_asst(T0, ctx=ctx))
                clock = _Clock(T0 + 1 * MIN)
                _rc, out = self.run_kw(clock, quota)
                self.assertEqual(_plan_line(out)["mode"], "single")
                self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=resume")
                self.assertAlmostEqual(clock.t, reset + SKEW, delta=60)
                self.assertEqual(self.traces("keepwarm_ping_cost"), [])
                self.assertEqual(self.ledger()["pings"], 0)


class ResumeTest(_Base):
    """tools/lib/sessionctl/kw_run.py：到目標＝resume，並記原主人續跑（AT-QW-27、AT-QW-52）。"""

    def test_resume_row_exists_and_marks_the_owner_session_resumed(self) -> None:
        """REQ-QW-27、DES §8 觸發 1。WHY：原主人在原窗續工＝沒有交棒；不記 `.resumed`，
        封存戳會留著，
        冷叫醒閘之後仍叫它 TaskStop 在飛代理（22:54 誤推）。已交棒者另一條（見下）不得記。"""
        pkg = self.package(acked=False)
        self.write(_asst(T0))
        _rc, out = self.run_kw(_Clock(T0 + 1 * MIN), _const(99.5, T0 + 100 * MIN))
        self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=resume")
        self.assertIn(f"處置：{keepwarm.DISPOSAL['resume']}", out)
        self.assertTrue(seal.resumed_path(pkg).exists())
        self.assertFalse(seal.sealed_path(pkg).exists(), "封存已作廢")

    def test_a_handed_over_package_stops_the_carrier_without_resuming(self) -> None:
        """REQ-QW-42、AT-QW-63、MU-QW-29。WHY：備援已在別的 session 接手後，舊窗的 keepwarm 若晚醒
        還 resume＝兩個視窗同時動同一棵工作樹；叫醒時刻先重判交棒，已交棒 ⇒ `handed_over`、
        不 ping、不記 `.resumed`。"""
        self.write(_asst(T0))
        holder_box: list[Path] = []

        def hand_over(clock: _Clock) -> None:
            if clock.t >= T0 + 30 * MIN and not holder_box:
                holder_box.append(self.package(acked=True))
        clock = _Clock(T0 + 1 * MIN, on_sleep=hand_over)
        _rc, out = self.run_kw(clock, _const(40, T0 + 400 * MIN))
        self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=handed_over")
        self.assertIn(keepwarm.DISPOSAL["handed_over"], out)
        self.assertFalse(seal.resumed_path(holder_box[0]).exists())
        self.assertFalse(keepwarm.ledger_path(SID).exists(), "不計 pings")


# ═══════════════════════════════════════════════════════════════ 牆、defer、提前重置
class WallAndDeferTest(_Base):
    """tools/lib/sessionctl/kw_wake.py：牆內不結束、defer、提前重置（AT-QW-24～26）。"""

    def test_a_wake_inside_the_wall_is_deferred_and_never_pings(self) -> None:
        """REQ-QW-24。WHY：保溫在牆內醒＝一次 429（T923／T926）。讀數 100 ⇒ 目標延到 reset＋s，
        牆內零 ping、不記帳。"""
        reset = T0 + 40 * MIN
        quota = _Quota(lambda t: (100, reset) if t < reset else (20, reset + 300 * MIN))
        self.write(_asst(T0))
        clock = _Clock(T0 + 1 * MIN)
        _rc, out = self.run_kw(clock, quota)
        self.assertEqual(_plan_line(out)["mode"], "single")
        self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=resume")
        self.assertGreaterEqual(clock.t, reset + SKEW)
        self.assertEqual([r for r in self.traces("keepwarm_verdict")
                          if r["verdict"] == "ping"], [])
        self.assertEqual(self.traces("keepwarm_early_reset"), [], "準時到新窗不算提前")

    def test_at_the_target_a_still_full_window_defers_to_the_new_reset(self) -> None:
        """REQ-QW-26。WHY：reset 的觀測值會晚（伺服器重估）。到目標時讀數仍 100 且回報新的未來
        reset ⇒ 延到新 reset＋s（`KEEPWARM_DEFER`、痕跡 `keepwarm_defer`、holder 列同步改寫）；
        不得自行推算，也不得照舊目標叫醒（又是一次 429）。"""
        reset = T0 + 100 * MIN
        later = reset + 40 * MIN
        quota = _Quota(lambda t: (99.5, reset) if t < reset + SKEW else
                       ((100, later) if t < later + SKEW else (20, later + 300 * MIN)))
        self.write(_asst(T0))
        rows: list = []
        clock = _Clock(T0 + 1 * MIN, on_sleep=lambda c: rows.append(holder.read(SID)))
        _rc, out = self.run_kw(clock, quota)
        self.assertIn("KEEPWARM_DEFER", out)
        self.assertEqual(len(self.traces("keepwarm_defer")), 1)
        self.assertGreaterEqual(clock.t, later + SKEW)
        wakes = {qw_schema.holder_wake(r).wake_at for r in rows if r}
        self.assertEqual(wakes, {reset + SKEW, later + SKEW}, "defer 後 holder 的 wake_at 跟著改")
        self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=resume")

    def test_reading_unmeasurable_at_the_target_resumes_on_the_original_target(self) -> None:
        """REQ-QW-26（讀不到那格）。WHY：PRD §4.5.10 不猜時刻——讀不到就照原目標叫醒。"""
        reset = T0 + 100 * MIN
        quota = _Quota(lambda t: (99.5, reset) if t < reset else None)
        self.write(_asst(T0))
        clock = _Clock(T0 + 1 * MIN)
        _rc, out = self.run_kw(clock, quota)
        self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=resume")
        self.assertEqual(self.traces("keepwarm_defer"), [])
        self.assertAlmostEqual(clock.t, reset + SKEW, delta=60)

    def test_early_reset_resumes_at_once_without_paying_the_ping(self) -> None:
        """REQ-QW-26、AT-QW-25④⑥、AT-QW-75。WHY：reset 比估計早（11-21 實證）。ping 時刻讀到 reset
        晚於參照且讀數已降 ⇒ 立即 resume、該時刻不 ping、帳歸零、痕跡 `keepwarm_early_reset`；
        反例：reset 變晚但讀數沒降（只是估早了）⇒ 照常 ping。"""
        reset = T0 + 100 * MIN
        fresh = _Quota(lambda t: (93, reset) if t < T0 + 40 * MIN else (20, reset + 300 * MIN))
        self.write(_asst(T0))
        clock = _Clock(T0 + 1 * MIN)
        _rc, out = self.run_kw(clock, fresh)
        self.assertEqual(_verdict(out), "KEEPWARM_VERDICT=resume")
        self.assertAlmostEqual(clock.t, T0 + 45 * MIN, delta=60)
        self.assertEqual(len(self.traces("keepwarm_early_reset")), 1)
        self.assertEqual(self.ledger()["pings"], 0)
        # 反例：讀數 95（≥ 參照 93）、reset 變晚 ⇒ 不是提前重置
        self.reset_traces()
        slip = _Quota(lambda t: (93, reset) if t < T0 + 40 * MIN else (95, reset + 70 * MIN))
        self.write(_asst(T0))
        _rc, out = self.run_kw(_Clock(T0 + 1 * MIN), slip)
        self.assertTrue(_verdict(out).startswith("KEEPWARM_VERDICT=ping"), out)
        self.assertEqual(self.traces("keepwarm_early_reset"), [])

    def test_park_at_marker_turns_the_early_check_off(self) -> None:
        """AT-QW-75⑦。WHY：`park --at` 是掌舵者指定的時刻，不是 reset；用 reset 的提前判準去提早
        叫醒＝違背指定時刻。`early=off` 時同樣的讀數照常 ping。"""
        pkg = self.package(acked=False)
        target = T0 + 3 * 3600
        marker = {"schema": park.SCHEMA, "sid": SID, "route": park.ROUTE_DONE, "status": "armed",
                  "parked_at": datetime.now(UTC).isoformat(),
                  "valid_until": (datetime.now(UTC) + timedelta(hours=9)).isoformat(),
                  "why": "測試：指定時刻續工", "jobs": [], "pkg": str(pkg),
                  **qw_schema.marker_extra(target, "at", target + 600, False, None)}
        self.assertTrue(park.write_marker(marker)[0])
        quota = _Quota(lambda t: (93, target - SKEW) if t < T0 + 40 * MIN
                       else (20, target + 300 * MIN))
        self.write(_asst(T0))
        _rc, out = self.run_kw(_Clock(T0 + 1 * MIN), quota)
        self.assertEqual(_plan_line(out)["early"], "off")
        self.assertTrue(_verdict(out).startswith("KEEPWARM_VERDICT=ping"), out)

    def reset_traces(self) -> None:
        for item in self.tdir.glob("autosdd_session_switch.jsonl"):
            item.unlink()


class PollingTest(_Base):
    """tools/lib/sessionctl/kw_run.py：牆鐘輪詢與 darwin 心跳（AT-QW-26、AT-QW-65）。"""

    def test_a_frozen_process_ends_within_one_poll_after_the_deadline(self) -> None:
        """REQ-QW-25。WHY：機器睡眠／行程被凍結跨過截止（睡了 40 分鐘）後，必須下一輪就結束；
        單次長 sleep 會在恢復後再睡滿原剩餘時間。每次 sleep 參數 ≤ 60。"""
        sleeps: list[float] = []
        froze = {"done": False}
        self.write(_asst(T0))
        clock = _Clock(T0 + 1 * MIN)

        def freezing_sleep(sec: float) -> None:
            sleeps.append(sec)
            clock.sleep(sec)
            if clock.t >= T0 + 20 * MIN and not froze["done"]:
                froze["done"] = True
                clock.t += 40 * MIN  # 跨過 T0+45 的截止

        out = io.StringIO()
        keepwarm.run(SID, self.path, t_kw_min=45, env=self.env, now_fn=clock.now,
                     sleep_fn=freezing_sleep, poll_sec=60.0, out=out,
                     read_quota=lambda _n: None, refresh=_no_refresh)
        self.assertLessEqual(max(sleeps), 60.0)
        self.assertTrue(_verdict(out.getvalue()).startswith("KEEPWARM_VERDICT=ping"))
        self.assertLessEqual(clock.t, T0 + 20 * MIN + 40 * MIN + 61, "恢復後至多一輪就結束")
    def test_darwin_prints_a_heartbeat_and_marks_backup_absent(self) -> None:
        """REQ-QW-38（keepwarm 側）。WHY：macOS 記憶體壓力下閒置 ≥30 分的背景指令會被收（CARC）；
        心跳每 ≤10 分印一行（零 token）。非 win32 沒有自動開窗備援，首行如實印 `backup=absent`。"""
        self.write(_asst(T0))
        _rc, out = self.run_kw(_Clock(T0 + 1 * MIN), _const(40, T0 + 400 * MIN),
                               platform_name="darwin")
        self.assertGreaterEqual(out.count("KEEPWARM_HEARTBEAT"), 2)
        self.assertIn("backup=absent(platform)", out.splitlines()[0])
        _rc, out = self.run_kw(_Clock(T0 + 1 * MIN), _const(40, T0 + 400 * MIN),
                               platform_name="win32")
        self.assertNotIn("KEEPWARM_HEARTBEAT", out)
        self.assertNotIn("backup=absent", out)


# ═══════════════════════════════════════════════════════════════ 保溫帳歸零與 Δ
class WorkMarkTest(_Base):
    """tools/lib/sessionctl/kw_ledger.py：主控真工作記錄的歸零標記（AT-QW-79；MU-QW-51）。"""

    def _seed(self, pings: int = 6) -> None:
        self.write(_asst(T0))
        kw_ledger.record_ping(SID, pings, 300_000, 9, kw_ledger.human_mark(self.path),
                              work=kw_ledger.work_mark(self.path))

    def _pings_after(self, *records: dict) -> int:
        self._seed()
        self.append(*records)
        return kw_ledger.load_ledger(SID, self.path)["pings"]

    def test_real_work_zeroes_the_ledger_but_supervision_calls_do_not(self) -> None:
        """REQ-QW-65。WHY：讀 keepwarm 輸出並重掛的回合若歸零，periodic 的 cap 永遠不觸發＝無限
        付費（QA5 P2-2）。監督文法只認 `control.is_supervision_call`；解析不出的指令算真工作。"""
        out = "keepwarm_out.txt"
        rehang = f"python tools/sessionctl.py keepwarm --sid {SID}"
        cases = (
            ("edit", [_asst(T0 + 60, tools=[("Edit", {"file_path": "x"})])], 0),
            ("rehang_x3", [_asst(T0 + 60 + i, tools=[_ps(rehang)]) for i in range(3)], 6),
            ("read_then_rehang", [_asst(T0 + 60, tools=[
                ("Read", {"file_path": out}), _ps(f"Get-Content {out} -Tail 5 ; {rehang}")])], 6),
            ("taskoutput_status", [_asst(T0 + 60, tools=[
                ("TaskOutput", {"task_id": "b1"}),
                _ps("python tools/sessionctl.py status")])], 6),
            ("git_add_after_read", [_asst(T0 + 60, tools=[_ps(f"Get-Content {out} ; git add -u")])],
             0),
            ("unparsable", [_asst(T0 + 60, tools=[_ps("echo 'unclosed")])], 0),
        )
        for name, records, want in cases:
            with self.subTest(name):
                self.assertEqual(self._pings_after(*records), want)

    def test_auto_continuation_zeroes_the_ledger(self) -> None:
        """AT-QW-79①。WHY：harness 自動續接開了新回合＝窗口翻新，帳歸零。"""
        import quota_limits  # noqa: PLC0415
        resume = {"type": "user", "timestamp": _iso(T0 + 60),
                  "origin": {"kind": quota_limits.RESUME_ORIGIN},
                  "message": {"role": "user", "content": "continue"}}
        self.assertEqual(self._pings_after(resume), 0)

    def test_periodic_caps_after_n_star_rehang_cycles_even_when_each_turn_reads_the_output(
            self) -> None:
        """AT-QW-81、REQ-QW-23。WHY：periodic 無目標時 cap 是成本上界；每回合「讀輸出＋重掛」不得
        使帳歸零。n*－1 次 ping 之後的第 n* 次叫醒判 cap，帳不因讀輸出而歸零。"""
        self.write(_asst(T0))
        rehang = f"python tools/sessionctl.py keepwarm --sid {SID}"
        star = keepwarm.n_star(300_000)
        epoch = T0
        for i in range(star - 1):  # 第 n* 次叫醒本身就是 cap（既有語意：k ≥ n* ⇒ cap）
            _rc, out = self.run_kw(_Clock(epoch + 1 * MIN))
            self.assertEqual(_verdict(out), f"KEEPWARM_VERDICT=ping k={i + 1} n={star}", i)
            epoch += 46 * MIN
            self.append(_asst(epoch, tools=[("Read", {"file_path": "keepwarm_out.txt"}),
                                            _ps(f"Get-Content keepwarm_out.txt ; {rehang}")]))
        _rc, out = self.run_kw(_Clock(epoch + 1 * MIN))
        self.assertEqual(_verdict(out), f"KEEPWARM_VERDICT=cap k={star}")


class PingCostTest(_Base):
    """tools/lib/sessionctl/kw_wake.py：ping 實測 Δ（AT-QW-80；MU-QW-49／50）。"""

    def _two_pings(self, first: float, second: float, *, reset2: float | None = None,
                   between=()) -> dict:
        reset = T0 + 400 * MIN
        self.write(_asst(T0, ctx=200_000))
        _rc, out = self.run_kw(_Clock(T0 + 1 * MIN), _const(first, reset))
        self.assertTrue(_verdict(out).startswith("KEEPWARM_VERDICT=ping"), out)
        self.append(*between, _asst(T0 + 46 * MIN, ctx=200_000))
        _rc, out = self.run_kw(_Clock(T0 + 47 * MIN), _const(second, reset2 or reset))
        self.assertTrue(_verdict(out).startswith("KEEPWARM_VERDICT=ping"), out)
        return self.ledger()

    def test_the_delta_between_adjacent_pings_is_recorded_and_raises_the_plan(self) -> None:
        """REQ-QW-66①。WHY：未校準的每次保溫成本是縮放推估；實測 Δ 取大才能在上線到校準之間自行
        收斂。Δ＝相鄰兩次 ping 叫醒的讀數差（重掛啟動時不量）。"""
        row = self._two_pings(80, 83)
        self.assertEqual(qw_schema.ping_costs(row), [3.0])
        self.assertEqual(len(self.traces("keepwarm_ping_cost")), 1)
        from lib.sessionctl import qw_plan  # noqa: PLC0415
        plan = qw_plan.plan(SID, self.path, {}, datetime.fromtimestamp(T0 + 48 * MIN, UTC),
                            read_quota=_const(83, T0 + 400 * MIN).read, refresh=_no_refresh)
        self.assertEqual((plan.ping_pp, plan.ping_pp_src, plan.calibrated),
                         (3.0, "measured", False))

    def test_unreliable_intervals_are_not_recorded(self) -> None:
        """REQ-QW-66③～⑦。WHY：區間內有真工作、換窗、讀數反降的 Δ 不是保溫成本，記了會把
        ping_pp 墊歪（只抬不降）。"""
        edit = _asst(T0 + 20 * MIN, ctx=200_000, tools=[("Edit", {"file_path": "x"})])
        for name, kw in (("work_between", {"between": (edit,)}),
                         ("new_window", {"reset2": T0 + 400 * MIN + 120 * MIN}),
                         ("reading_dropped", {"second": 79})):
            with self.subTest(name):
                self.setUp()
                args = {"first": 80, "second": 83, **kw}
                row = self._two_pings(args.pop("first"), args.pop("second"), **args)
                self.assertEqual(qw_schema.ping_costs(row), [])
                self.assertEqual(self.traces("keepwarm_ping_cost"), [])

    def test_only_the_latest_five_costs_are_kept(self) -> None:
        """AT-QW-80⑧。WHY：帳只留最近 5 筆，計畫取近 3 筆平均；無界成長會讓舊值壓住新情況。"""
        costs: list[float] = []
        for delta in range(1, 8):
            costs = qw_schema.append_cost(costs, float(delta))
        self.assertEqual(costs, [3.0, 4.0, 5.0, 6.0, 7.0])
        self.assertEqual(qw_schema.measured_mean(costs), 6.0)


class WatchWallTest(unittest.TestCase):
    """tools/lib/sessionctl/watch_wake.py：四級帶級與處置（REQ-QW-17／18；AT-QW-33）。"""

    def test_bands_rank_prepare_below_nodispatch_below_close_below_halt(self) -> None:
        """WHY：同窗內只有「更嚴重」才再觸發一次（閂鎖看級別）。"""
        rank = keepwarm._BANDS
        self.assertEqual(sorted(rank, key=rank.get), ["prepare", "nodispatch", "close", "halt"])

    def test_dispositions_per_stage_never_say_wait_for_agents_to_finish(self) -> None:
        """REQ-QW-17。WHY：nodispatch／close 時「代理快完成 ⇒ 重掛」會把主控帶回舊流程（派不完、
        收不了尾）；close 必須列 TaskStop→封存→park→keepwarm，nodispatch 只說不派新代理。"""
        from lib.sessionctl import watch_wake  # noqa: PLC0415
        for band in ("nodispatch", "close", "halt"):
            self.assertNotIn("快完成", watch_wake.quota_disposal(band))
        for word in ("TaskStop", "finalize", "park", "keepwarm"):
            self.assertIn(word, watch_wake.quota_disposal("close"))
        self.assertIn("不再派新代理", watch_wake.quota_disposal("nodispatch"))
        self.assertIsNone(watch_wake.quota_disposal("prepare"))


class WatchCarrierTest(_Base):
    """tools/lib/sessionctl/watch_wake.py：watch 持錨與 keepwarm 同一份 schedule（AT-QW-35）。"""

    def _watch(self, clock: _Clock, quota: _Quota, **seams) -> tuple[int, str]:
        out = io.StringIO()
        rc = watch.run(SID, watch.Cfg(), now_fn=clock.now, sleep_fn=clock.sleep, poll_sec=60.0,
                       roster_fn=lambda: [], quota_fn=lambda: None, out=out, pid=os.getpid(),
                       projects_dir=str(self.tmp), read_quota=quota.read, refresh=_no_refresh,
                       env=self.env, **seams)
        return rc, out.getvalue()

    def _transcript(self) -> None:
        (self.tmp / SID).mkdir(exist_ok=True)
        (self.tmp / f"{SID}.jsonl").write_text(json.dumps(_asst(T0)) + "\n", encoding="utf-8")

    def test_watch_and_keepwarm_wake_at_the_same_times_for_the_same_input(self) -> None:
        """REQ-QW-29、AT-QW-35。WHY：watch 持有保溫錨時若另算一套排程，主控會在兩個不同的時刻被叫
        醒（或在該叫醒時沒被叫醒）。同輸入：第一個叫醒時刻相同。"""
        reset = T0 + 100 * MIN
        self._transcript()
        self.path = self.tmp / f"{SID}.jsonl"
        kw_clock = _Clock(T0 + 1 * MIN)
        self.run_kw(kw_clock, _const(93, reset))
        w_clock = _Clock(T0 + 1 * MIN)
        _rc, out = self._watch(w_clock, _const(93, reset))
        self.assertEqual(out.strip().splitlines()[-1].split()[0], "WATCH_VERDICT=keepwarm")
        self.assertEqual(w_clock.t, kw_clock.t)

    def test_watch_resume_at_target_and_wall_is_silent(self) -> None:
        """REQ-QW-18／29。WHY：單跳到目標時 watch 判 `resume`（主控該接著做事）；牆中 watch 不判任何
        事件、不記保溫帳，只寫心跳（牆內叫醒＝429）。"""
        reset = T0 + 100 * MIN
        self._transcript()
        clock = _Clock(T0 + 1 * MIN)
        _rc, out = self._watch(clock, _const(99.5, reset))
        self.assertEqual(out.strip().splitlines()[-1].split()[0], "WATCH_VERDICT=resume")
        self.assertIn(keepwarm.DISPOSAL["resume"], out)
        self.assertAlmostEqual(clock.t, reset + SKEW, delta=60)
        # 牆中：整段時間都在牆內 ⇒ 到 reset＋s 之前沒有任何事件
        wall = _Quota(lambda t: (100, T0 + 200 * MIN) if t < T0 + 200 * MIN
                      else (20, T0 + 500 * MIN))
        self._transcript()
        clock = _Clock(T0 + 1 * MIN)
        _rc, out = self._watch(clock, wall)
        self.assertGreaterEqual(clock.t, T0 + 200 * MIN)
        self.assertEqual([r for r in self.traces("watch_verdict")
                          if r["verdict"] in ("keepwarm", "cap")], [])


if __name__ == "__main__":
    unittest.main()
