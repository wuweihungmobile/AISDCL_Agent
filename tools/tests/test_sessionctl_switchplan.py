"""tools/lib/sessionctl/switchplan.py（決策表）、switchfacts.py（事實）
與 watch／advise／switch-plan 掛點。

W5（Control_Handover DES §7；TCS-Control AT-CTL-41～55、86）。
WHY：換不換 session 的判準原本散在封存閘、park 停工閘、保溫閘與轉送條件 10，沒有一處能回答「此刻整體
上該做什麼」；本檔證明 `decide` 是這些閘的**嚴格超集**——現行會推的地方它一定給對應動作，差異只在
文件列出的四處（排空後換／防抖／換帳號 ⇒ 快取視為已冷／提前恢復）；並證明新增的 pending／switch_due
只改提示、不新增任何推回，R2 session 零新增推回。縫：tmp 逐字稿與包目錄、
`AUTOSDD_TRACE_DIR` 指 tmp、時鐘注入；不碰真實 `~/.claude`、`~/.autosdd`。
"""
from __future__ import annotations

import ast
import io
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import sentinel_lifecycle as SL  # noqa: E402  # 模組級圍籬原語（watch 會寫額度快取）

from lib.sessionctl import (  # noqa: E402
    control,
    costmodel,
    handoff,
    park,
    seal,
    statuscmd,
    switch,
    switchfacts,
    switchplan,
    watch,
)
from lib.sessionctl.switchplan import Action, Inputs, Quota  # noqa: E402

_MODULE_FENCES: list[dict] = []
SID = "5a1b2c3d-aaaa-bbbb-cccc-dddddddddddd"
OTHER = "9f9f9f9f-aaaa-bbbb-cccc-eeeeeeeeeeee"
HARD = switch.threshold(switch.HARD_CTX_KEY, {})[0]
R2 = switch.threshold(switch.R2_KEY, {})[0]
# F4 臨界之上、硬線之下的上下文（從 costmodel 現查，不寫死數字）
BIG = int(costmodel.fresh_ctx_threshold() * 1.5)
SMALL = int(costmodel.fresh_ctx_threshold() * 0.5)
_FULL_MAIN = "\n\n".join(f"{h}\n內容 {i}" for i, h in enumerate(handoff.SECTIONS))
NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def setUpModule() -> None:
    _MODULE_FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_MODULE_FENCES.pop())


def _ts(minutes_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def _inp(**kw) -> Inputs:
    base = {"hard": HARD, "r2": R2, "ctx": SMALL}
    return Inputs(**{**base, **kw})


# ───────────────────────────────────────────────────────── 決策表（AT-CTL-41、42、45、46）
class DecideTableTest(unittest.TestCase):
    """DES §7.2 每一列（G0、G1、W、D、H、F、F′、K、Z）至少一個輸入向量。"""

    def check(self, got, action: str, reason: str) -> None:
        self.assertEqual((got.action, got.reason.split("+")[0].split("(")[0]), (action, reason),
                         msg=str(got))

    def test_every_row_of_the_table_has_a_vector(self) -> None:
        rows = [
            (_inp(unattended=True, ctx=HARD), Action.STAY, "gate"),
            (_inp(mode="off", ctx=HARD), Action.STAY, "gate"),
            (_inp(handed_over=True, ctx=HARD), Action.STAY, "handed_over"),
            (_inp(quota=Quota(stage="close", wait_min=60)), Action.PARK_UNTIL, "wall"),
            (_inp(quota=Quota(stage="wall", wait_min=60)), Action.PARK_UNTIL, "wall"),
            (_inp(quota=Quota(short_pct=90, prepare_pct=85, wait_min=60)), Action.PARK_UNTIL,
             "prepare_no_credential"),
            (_inp(since_takeover_min=5), Action.STAY, "debounce"),
            (_inp(ctx=HARD, agents=0), Action.SWITCH_NOW, "hard"),
            (_inp(ctx=HARD, agents=2), Action.SWITCH_AFTER_DRAIN, "hard_drain"),
            (_inp(ctx=BIG, cache="cold", sealed=control.SEAL_EFFECTIVE), Action.SWITCH_NOW,
             "cold_fresh"),
            (_inp(ctx=BIG, cache="cold", sealed=control.SEAL_NONE), Action.STAY, "cold_unsealed"),
            (_inp(keepwarm_ok=True), Action.STAY, "keepwarm"),
            (_inp(), Action.STAY, "ok"),
        ]
        for inputs, action, reason in rows:
            with self.subTest(reason=reason, inputs=inputs):
                self.check(switchplan.decide(inputs), action, reason)

    def test_unmeasured_context_never_triggers_h_or_f(self) -> None:
        """量不到上下文偏續跑：FRESH 的代價是丟上下文（DES §7.2 邊界）。"""
        for cache in ("hot", "cold"):
            got = switchplan.decide(_inp(ctx=None, cache=cache, sealed=control.SEAL_EFFECTIVE))
            self.check(got, Action.STAY, "ok")
        self.check(switchplan.decide(_inp(ctx=None, hard=None)), Action.STAY, "ok")

    def test_the_order_is_first_match_wins(self) -> None:
        wall = Quota(stage="close", wait_min=30)
        # G1 先於 H；W 先於 D 與 H；D 先於 H；W 先於 G1 之後的一切但不先於 G0／G1
        self.check(switchplan.decide(_inp(handed_over=True, ctx=HARD, quota=wall)),
                   Action.STAY, "handed_over")
        self.check(switchplan.decide(_inp(since_takeover_min=3, quota=wall)),
                   Action.PARK_UNTIL, "wall")
        self.check(switchplan.decide(_inp(since_takeover_min=3, ctx=HARD)), Action.STAY, "debounce")
        self.check(switchplan.decide(_inp(ctx=HARD, quota=wall)), Action.PARK_UNTIL, "wall")
        self.check(switchplan.decide(_inp(ctx=HARD, unattended=True, quota=wall)),
                   Action.STAY, "gate")

    def test_wall_target_and_taskstop_first(self) -> None:
        weekly = _inp(quota=Quota(stage="close", target_axis="weekly", wait_min=60))
        self.assertEqual(switchplan.decide(weekly).action, Action.PARK_POLL)
        far = _inp(quota=Quota(stage="close", wait_min=7 * 60))
        self.assertEqual(switchplan.decide(far).action, Action.PARK_POLL)
        busy = switchplan.decide(_inp(agents=2, quota=Quota(stage="close", wait_min=60)))
        self.assertIn("taskstop_first", busy.reason)
        covered = Quota(short_pct=99, prepare_pct=85, credential=True, wait_min=60)
        self.check(switchplan.decide(_inp(quota=covered)), Action.STAY, "ok")  # 已有續航憑證
        notify = switchplan.decide(_inp(mode="notify", quota=Quota(stage="close", wait_min=60)))
        self.assertIn("(notify)", notify.reason)  # notify 只出聲，判準不變

    def test_debounce_boundary_and_non_takeover(self) -> None:
        """AT-CTL-45：29 ⇒ STAY(debounce)；31 ⇒ H 正常；W 不受限；非接手者（None）不受限。"""
        self.check(switchplan.decide(_inp(ctx=HARD, since_takeover_min=29)),
                   Action.STAY, "debounce")
        self.check(switchplan.decide(_inp(ctx=HARD, since_takeover_min=31)),
                   Action.SWITCH_NOW, "hard")
        self.check(switchplan.decide(_inp(ctx=HARD, since_takeover_min=None)),
                   Action.SWITCH_NOW, "hard")
        self.assertEqual(switchplan.DEBOUNCE_MIN, 30)

    def test_account_change_only_turns_cache_cold(self) -> None:
        """AT-CTL-46：換帳號只把 cache 視為 cold；與 False 相比差異僅限 F／F′ 兩列。"""
        vectors = itertools.product((SMALL, BIG, HARD), (0, 2), ("hot", "cold", "unknown"),
                                    (control.SEAL_NONE, control.SEAL_EFFECTIVE,
                                     control.SEAL_INVALIDATED, control.SEAL_UNREADABLE))
        diffs = set()
        for ctx, agents, cache, sealed in vectors:
            plain = switchplan.decide(_inp(ctx=ctx, agents=agents, cache=cache, sealed=sealed))
            moved = switchplan.decide(_inp(ctx=ctx, agents=agents, cache=cache, sealed=sealed,
                                           account_changed=True))
            if (plain.action, plain.reason) != (moved.action, moved.reason):
                diffs.add(moved.reason.split("(")[0])
        self.assertEqual(diffs, {"cold_fresh", "cold_unsealed"})

    def test_r2_only_sets_prefer_fresh(self) -> None:
        """AT-CTL-44：R2 命中只設旗標，動作不變；選路點（`switch.fresh_reasons`、`park.fire_route`）
        見該旗標一律 FRESH。"""
        base = switchplan.decide(_inp(compactions=R2 - 1))
        hit = switchplan.decide(_inp(compactions=R2))
        self.assertEqual((base.action, base.reason), (hit.action, hit.reason))
        self.assertFalse(base.flags.prefer_fresh)
        self.assertTrue(hit.flags.prefer_fresh)
        guard = SimpleNamespace(read_context_feed=lambda *_a: {"used": SMALL},
                                scan_transcript=lambda *_a: (SMALL, 0, 0),
                                compact_boundary_count=lambda _p: R2)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            path.write_text("{}\n", encoding="utf-8")
            hits, _ = switch.fresh_reasons(SID, path, 10, guard=guard, env={})
        self.assertTrue(any("R2" in h for h in hits))
        self.assertEqual(park.fire_route(SMALL, False, {}, prefer_fresh=True)[0], park.FIRE_FRESH)
        self.assertEqual(park.fire_route(SMALL, False, {})[0], park.FIRE_RESUME)

    def test_k_row_sets_the_keepwarm_flag_and_keeps_prefer_fresh(self) -> None:
        got = switchplan.decide(_inp(keepwarm_ok=True, compactions=R2))
        self.assertTrue(got.flags.keepwarm and got.flags.prefer_fresh)


# ───────────────────────────────────────────────────────── 與現行三閘＋F4 的一致性（AT-CTL-47）
class _GateFence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="ctl-w5-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.hdir, self.tdir = self.tmp / "handoff", self.tmp / "traces"
        for d in (self.hdir, self.tdir):
            d.mkdir()
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tdir),
                                               "AUTOSDD_HANDOFF_DIR": str(self.hdir)})
        patcher.start()
        self.addCleanup(patcher.stop)
        carrier = mock.patch("lib.sessionctl.park._has_carrier", return_value=False)
        carrier.start()
        self.addCleanup(carrier.stop)
        self.transcript = self.tmp / f"{SID}.jsonl"

    def write_transcript(self, ctx: int, *, work_after_stamp: bool = False,
                         compactions: int = 0) -> Path:
        usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
                 "cache_creation_input_tokens": 0, "output_tokens": 7}
        rows = [{"type": "assistant", "timestamp": _ts(30), "message": {"id": "m", "usage": usage}}]
        rows += [{"type": "system", "subtype": "compact_boundary", "timestamp": _ts(29)}
                 for _ in range(compactions)]
        if work_after_stamp:
            rows.append({"type": "assistant", "timestamp": _ts(1), "message": {"content": [
                {"type": "tool_use", "name": "Edit", "input": {}}]}})
        self.transcript.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return self.transcript

    def package(self, *, stamp: str | None = None, acker: str | None = None) -> Path:
        path = self.hdir / f"{SID}_20261124T000000Z.md"
        path.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n\n"
                        f"## 機械層\n\n資料\n\n{handoff.MAIN_MARK}\n\n{_FULL_MAIN}\n",
                        encoding="utf-8")
        if stamp is not None:
            path.with_suffix(".sealed").write_text(stamp + "\n", encoding="utf-8")
        if acker is not None:
            path.with_suffix(".ack").write_text(f"acked {_ts(5)} sid={acker}\n", encoding="utf-8")
        return path


class ConsistencyWithTheCurrentGatesTest(_GateFence):
    """AT-CTL-47：≥500 個合成輸入向量逐一比對；現行會推處 ⇒ `decide` 給對應動作。"""

    SEALED = {control.SEAL_NONE: None, control.SEAL_EFFECTIVE: "ok",
              control.SEAL_INVALIDATED: "work", control.SEAL_UNREADABLE: "bad"}

    def _build(self, sealed: str, handed: bool, ctx: int) -> dict:
        for old in self.hdir.iterdir():
            old.unlink()
        kind = self.SEALED[sealed]
        stamp = {"ok": _ts(10), "work": _ts(10), "bad": "壞掉的戳"}.get(kind)
        if kind is not None or handed:
            self.package(stamp=stamp, acker=OTHER if handed else None)
        self.write_transcript(ctx, work_after_stamp=kind == "work")
        return {"session_id": SID, "transcript_path": str(self.transcript),
                "hook_event_name": "Stop"}

    def test_h_row_never_misses_a_push_of_the_seal_gate(self) -> None:
        n = pushes = 0
        for ctx, agents, sealed, mode, unattended, handed in itertools.product(
                (None, SMALL, HARD - 1, HARD), (0, 1), self.SEALED, ("auto", "notify", "off"),
                (False, True), (False, True)):
            payload = self._build(sealed, handed, ctx or SMALL)
            payload["background_tasks"] = [{"id": "a", "type": "subagent", "status": "running"}
                                           ] * agents
            env = {**self.env, "AUTOSDD_SESSION_SWITCH_MODE": mode,
                   **({"AUTOSDD_UNATTENDED": "1"} if unattended else {})}
            pushed = bool(seal.stop_verdict(payload, env))
            got = switchplan.decide(Inputs(
                ctx=ctx, hard=HARD, agents=agents, mode=mode, unattended=unattended,
                sealed=sealed, handed_over=handed, env=env))
            n += 1
            if pushed:
                pushes += 1
                with self.subTest(ctx=ctx, agents=agents, sealed=sealed, mode=mode):
                    self.assertEqual((got.action, got.reason), (Action.SWITCH_NOW, "hard"))
        self.assertGreaterEqual(n, 380)
        self.assertGreater(pushes, 0)  # 夾具確實觸發了現行閘（不是全程沒推）

    def test_w_row_never_misses_a_push_of_the_park_gate(self) -> None:
        now = datetime.now().astimezone()
        reset = (now + timedelta(hours=2)).isoformat()
        policy = SimpleNamespace(prepare_pct=85.0, halt_pct=100.0)
        n = pushes = 0
        for pct, cred, mode, unattended, agents in itertools.product(
                (10.0, 90.0, 99.0), (False, True), ("auto", "notify", "off"), (False, True),
                (0, 2)):
            axes = (SimpleNamespace(kind="five_hour", pct=pct, resets_at=reset),)
            state = SimpleNamespace(axes=axes, source="t", reason="")
            env = {"AUTOSDD_SESSION_SWITCH_MODE": mode,
                   **({"AUTOSDD_UNATTENDED": "1"} if unattended else {})}
            with mock.patch("lib.sessionctl.park.credential_ok", return_value=(cred, "x")):
                pushed = bool(park.stop_verdict(
                    {"session_id": SID}, env, now=now, read_quota=lambda _n, s=state: s,
                    policy_fn=lambda: policy, carrier_fn=lambda: True,
                    spawned_fn=lambda _s, _e: False))
            got = switchplan.decide(Inputs(
                agents=agents, mode=mode, unattended=unattended, env=env,
                quota=Quota(short_pct=pct, prepare_pct=85.0, credential=cred, wait_min=120)))
            n += 1
            if pushed:
                pushes += 1
                with self.subTest(pct=pct, cred=cred, mode=mode, agents=agents):
                    self.assertIn(got.action, (Action.PARK_UNTIL, Action.PARK_POLL))
        self.assertGreaterEqual(n, 70)
        self.assertGreater(pushes, 0)

    def test_f_row_equals_the_f4_cost_judgement_with_a_carrier(self) -> None:
        n = 0
        for ctx, cache, sealed, changed in itertools.product(
                (None, SMALL, BIG, HARD - 1), ("hot", "cold", "unknown"), self.SEALED,
                (False, True)):
            got = switchplan.decide(Inputs(ctx=ctx, hard=HARD, cache=cache, sealed=sealed,
                                           account_changed=changed))
            cold = cache == "cold" or changed
            cheaper = costmodel.fresh_is_cheaper(ctx, cold=cold)
            n += 1
            expect = ("cold_fresh" if sealed == control.SEAL_EFFECTIVE else "cold_unsealed"
                      ) if cheaper else "ok"
            self.assertEqual(got.reason, expect, msg=f"{ctx} {cache} {sealed} {changed}")
        self.assertGreaterEqual(n, 90)

    def test_total_vector_count_reaches_the_spec_floor(self) -> None:
        h = 4 * 2 * 4 * 3 * 2 * 2   # ctx × agents × sealed × mode × unattended × handed
        w = 3 * 2 * 3 * 2 * 2       # pct × cred × mode × unattended × agents
        f = 4 * 3 * 4 * 2           # ctx × cache × sealed × account
        self.assertGreaterEqual(h + w + f, 500)


# ───────────────────────────────────────────────────────── pending（AT-CTL-43、50、86）
class PendingTest(_GateFence):
    def setUp(self) -> None:
        super().setUp()
        self.base = self.tdir / "switch"

    def pending(self, **kw):
        args = {"ctx": HARD, "hard": HARD, "sealed": control.SEAL_NONE, "handed_over": False}
        return switchplan.read_pending(SID, base=self.base, **{**args, **kw})

    def test_h_with_agents_creates_one_idempotent_hard_marker(self) -> None:
        self.assertIsNone(switchplan.ensure_pending(SID, ctx=HARD, hard=HARD, agents=0,
                                                    base=self.base))
        first = switchplan.ensure_pending(SID, ctx=HARD, hard=HARD, agents=2, now=NOW,
                                          base=self.base)
        self.assertEqual(set(first), {"reason", "since", "ctx"})
        self.assertEqual(first["reason"], "hard")
        later = switchplan.ensure_pending(SID, ctx=HARD + 5, hard=HARD, agents=2,
                                          now=NOW + timedelta(minutes=9), base=self.base)
        self.assertEqual(later["since"], first["since"])  # 已有檔不覆寫 since
        events = [r["event"] for r in self._traces()]
        self.assertEqual(events.count(control.EV_PENDING_SET), 1)

    def test_drain_deadline_upgrades_the_text_only(self) -> None:
        """AT-CTL-43：29 分仍 AFTER_DRAIN；31 分 ⇒ SWITCH_NOW(drain_overdue, taskstop_first)。"""
        row = switchplan.ensure_pending(SID, ctx=HARD, hard=HARD, agents=1, now=NOW, base=self.base)
        for minutes, action, reason in ((29, Action.SWITCH_AFTER_DRAIN, "hard_drain"),
                                        (31, Action.SWITCH_NOW, "drain_overdue+taskstop_first")):
            age = switchplan.age_min(row, NOW + timedelta(minutes=minutes))
            got = switchplan.decide(_inp(ctx=HARD, agents=1, pending_age_min=age))
            self.assertEqual((got.action, got.reason), (action, reason))
        self.assertEqual(switchplan.DRAIN_MAX_MIN, 30)

    def test_r2_never_writes_pending(self) -> None:
        """R2 命中而 ctx < hard ⇒ 不寫檔；decide＝STAY＋prefer_fresh。"""
        self.assertIsNone(switchplan.ensure_pending(SID, ctx=SMALL, hard=HARD, agents=3,
                                                    base=self.base))
        self.assertFalse((self.base / f"{SID}.pending").exists())
        got = switchplan.decide(_inp(ctx=SMALL, compactions=R2 + 3, agents=3))
        self.assertEqual((got.action, got.flags.prefer_fresh), (Action.STAY, True))

    def test_invalidation_matrix(self) -> None:
        """AT-CTL-50：effective／handed_over／（ctx 量得到且 < hard）作廢並落 cleared；
        invalidated／none／unreadable 與 ctx 量不到不作廢。"""
        keep = [{"sealed": control.SEAL_INVALIDATED}, {"sealed": control.SEAL_NONE},
                {"sealed": control.SEAL_UNREADABLE}, {"ctx": None}, {}]
        drop = [{"sealed": control.SEAL_EFFECTIVE, "why": "sealed"},
                {"handed_over": True, "why": "handed_over"},
                {"ctx": SMALL, "why": "compacted"}]
        for kw in keep:
            with self.subTest(keep=kw):
                switchplan.ensure_pending(SID, ctx=HARD, hard=HARD, agents=1, base=self.base)
                self.assertIsNotNone(self.pending(**kw))
                (self.base / f"{SID}.pending").unlink()
        for kw in drop:
            with self.subTest(drop=kw):
                why = kw.pop("why")
                switchplan.ensure_pending(SID, ctx=HARD, hard=HARD, agents=1, base=self.base)
                self.assertIsNone(self.pending(**kw))
                self.assertEqual(self._traces()[-1]["event"], control.EV_PENDING_CLEARED)
                self.assertEqual(self._traces()[-1]["why"], why)
                self.assertFalse((self.base / f"{SID}.pending").exists())
        # 作廢後 ctx 回到 ≥ hard 且有在飛代理 ⇒ 建新標記（新 since）
        again = switchplan.ensure_pending(SID, ctx=HARD, hard=HARD, agents=1,
                                          now=NOW + timedelta(hours=1), base=self.base)
        self.assertEqual(again["since"], (NOW + timedelta(hours=1)).astimezone().isoformat())

    def test_the_latch_does_not_swallow_a_hard_pending(self) -> None:
        """AT-CTL-86：先 R2 出聲（`.advised` 已寫），之後越過硬線 ∧ 有在飛代理 ⇒ pending 仍建立；
        兩個呼叫點（watch 輪詢＝`pending_state`、`control_state`）任一先到皆建立同一標記。"""
        self.write_transcript(SMALL, compactions=R2)
        guard = SimpleNamespace(read_context_feed=lambda *_a: {"used": SMALL},
                                scan_transcript=lambda *_a: (SMALL, 0, 0),
                                compact_boundary_count=lambda _p: R2)
        with self.mechanical():
            text = handoff.advise_once(SID, self.transcript, guard=guard, env=self.env,
                                       base=self.hdir)
        self.assertIn("R2", text)
        self.assertTrue((self.hdir / f"{SID}.advised").exists())
        self.assertFalse((self.base / f"{SID}.pending").exists())  # advise_once 不寫 pending
        self.write_transcript(HARD)
        got = switchfacts.pending_state(SID, self.transcript, 2, self.env, base=self.base)
        self.assertEqual(got["reason"], "hard")
        pending = json.loads((self.base / f"{SID}.pending").read_text(encoding="utf-8"))
        self.assertEqual(pending["reason"], "hard")

    def test_advise_once_traces_every_voice_and_only_once_per_reason(self) -> None:
        """AT-CTL-49：每次出聲落 `switch_advise`（sid、reason、ctx、k、mode）；
        同 sid 第二次不再出聲。"""
        self.write_transcript(HARD)
        guard = SimpleNamespace(read_context_feed=lambda *_a: {"used": HARD},
                                scan_transcript=lambda *_a: (HARD, 0, 0),
                                compact_boundary_count=lambda _p: 0)
        with self.mechanical():
            first = handoff.advise_once(SID, self.transcript, guard=guard, env=self.env,
                                        base=self.hdir)
            second = handoff.advise_once(SID, self.transcript, guard=guard, env=self.env,
                                         base=self.hdir)
        self.assertTrue(first)
        self.assertEqual(second, "")
        rows = [r for r in self._traces() if r["event"] == control.EV_SWITCH_ADVISE]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["sid"], rows[0]["reason"], rows[0]["ctx"], rows[0]["mode"]),
                         (SID, "hard", HARD, "auto"))
        self.assertFalse((self.base / f"{SID}.pending").exists())

    def mechanical(self):
        """機械層產生是另一個功能（有自己的測試）；這裡只要 `advise_once` 的出聲與痕跡。"""
        return mock.patch.object(handoff, "ensure_mechanical",
                                 return_value=self.hdir / f"{SID}_20261124T000000Z.md")

    def _traces(self) -> list[dict]:
        target = self.tdir / "autosdd_session_switch.jsonl"
        return ([json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]
                if target.exists() else [])


# ───────────────────────────────────────── watch switch_due（AT-CTL-51）與封存閘不變（AT-CTL-52）
class WatchSwitchDueTest(_GateFence):
    def run_watch(self, rosters: list[list[dict]], ctx: int) -> tuple[int, str]:
        self.write_transcript(ctx)
        feed = iter(rosters)
        last = {"v": rosters[-1]}
        t = {"now": 1_800_000_000.0}

        def roster_fn():
            last["v"] = next(feed, rosters[-1])
            return [dict(a) for a in last["v"]]

        def sleep(sec):
            t["now"] += sec
            if t["now"] > 1_800_000_000.0 + 3 * 3600:
                raise AssertionError("watch 未終止")

        out = io.StringIO()
        rc = watch.run(SID, watch.Cfg(), now_fn=lambda: t["now"], sleep_fn=sleep, poll_sec=30.0,
                       roster_fn=roster_fn, end_turn_fn=lambda a: True, quota_fn=lambda: False,
                       anchor_fn=lambda: None, out=out, pid=4242, projects_dir=str(self.tmp),
                       read_quota=lambda _n: None,
                       refresh=lambda _n: (_ for _ in ()).throw(RuntimeError("x")),
                       env=self.env)
        return rc, out.getvalue()

    AGENT = {"id": "a1", "model": "sonnet", "description": "t", "last_at": None,
             "started_at": None, "ctx_tokens": 10}

    def test_pending_plus_all_agents_done_ends_with_switch_due(self) -> None:
        rc, out = self.run_watch([[self.AGENT], []], HARD)
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip().splitlines()[-1].split()[0], "WATCH_VERDICT=switch_due")
        self.assertIn("finalize", out)
        self.assertIn("spawn", out)
        events = [json.loads(x)["event"] for x in
                  (self.tdir / "autosdd_session_switch.jsonl")
                  .read_text(encoding="utf-8").splitlines()]
        self.assertIn(control.EV_PENDING_SET, events)
        self.assertIn(control.EV_PENDING_DUE, events)

    def test_without_pending_the_old_verdicts_are_untouched(self) -> None:
        """無 pending（ctx < hard）⇒ 代理交卷後 watch 照舊不因此結束
        （沒有 all_done，REQ-WP-30）。"""
        _rc, out = self.run_watch([[self.AGENT], []], SMALL)
        verdict = out.strip().splitlines()[-1].split()[0]
        self.assertIn(verdict, ("WATCH_VERDICT=keepwarm", "WATCH_VERDICT=cap",
                                "WATCH_VERDICT=idle"))  # 照舊只等保溫族，沒有 all_done
        self.assertFalse((self.tdir / "switch" / f"{SID}.pending").exists())

    def test_overdue_pending_adds_a_suffix_to_any_verdict(self) -> None:
        old = {"reason": "hard", "since": (NOW - timedelta(minutes=45)).isoformat(), "ctx": HARD}
        text = switchplan.on_verdict(SID, "stall", old, 2, now=NOW)
        self.assertIn("待換已逾", text)
        self.assertEqual(switchplan.on_verdict(SID, "stall", old, 0, now=NOW), "")
        self.assertEqual(switchplan.on_verdict(SID, "stall", None, 2, now=NOW), "")

    def test_merge_beats_idle_and_keepwarm_but_not_real_events(self) -> None:
        fam = watch.KEEPWARM_FAMILY
        self.assertEqual(switchplan.merge(None, "d", fam)[0], "switch_due")
        self.assertEqual(switchplan.merge(("keepwarm", "x"), "d", fam)[0], "switch_due")
        for real in ("quota", "budget", "stall", "overrun", "handed_over"):
            self.assertEqual(switchplan.merge((real, "x"), "d", fam)[0], real)
        self.assertEqual(switchplan.merge(("stall", "x"), None, fam), ("stall", "x"))


class SealGateTriggerIsUnchangedTest(_GateFence):
    """AT-CTL-52：封存閘的觸發條件不因 pending 而變；R2 session 零新增推回。"""

    def payload(self, agents: int = 0) -> dict:
        return {"session_id": SID, "transcript_path": str(self.transcript),
                "background_tasks": [{"id": "a", "type": "subagent", "status": "running"}] * agents}

    def test_pending_is_not_a_push_condition(self) -> None:
        self.write_transcript(SMALL)
        switchplan.ensure_pending(SID, ctx=HARD, hard=HARD, agents=1, base=self.tdir / "switch")
        self.assertEqual(seal.stop_verdict(self.payload(), self.env), "")  # ctx<hard ⇒ 不推

    def test_push_matrix_equals_the_documented_condition(self) -> None:
        self.write_transcript(HARD)
        self.assertTrue(seal.stop_verdict(self.payload(), self.env))  # none ⇒ 推
        self.assertEqual(seal.stop_verdict(self.payload(1), self.env), "")  # 在飛代理 ⇒ 不推
        self.package(stamp=_ts(10))
        self.assertEqual(seal.stop_verdict(self.payload(), self.env), "")  # effective ⇒ 不推
        self.write_transcript(HARD, work_after_stamp=True)
        self.assertIn("封存後有工作", seal.stop_verdict(self.payload(), self.env))  # invalidated
        self.assertEqual(seal.stop_verdict({**self.payload(), "stop_hook_active": True},
                                           self.env), "")

    def test_r2_sessions_get_zero_new_pushes(self) -> None:
        """重放 8 個 R2 session 固定夾具：ctx < hard、K ≥ r2 ⇒ 全程零推回。"""
        for k in range(R2, R2 + 8):
            self.write_transcript(SMALL + k, compactions=k)
            with self.subTest(k=k):
                self.assertEqual(seal.stop_verdict(self.payload(), self.env), "")
                self.assertEqual(seal.stop_verdict(self.payload(2), self.env), "")


# ───────────────────────────────────────────────────────── switch-plan 動詞（AT-CTL-53）
class SwitchPlanCliTest(_GateFence):
    def test_the_verb_is_read_only_and_always_rc0(self) -> None:
        self.write_transcript(HARD)
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = statuscmd.switch_plan_cli(["--sid", SID], env=self.env)
        text = buf.getvalue()
        self.assertEqual(rc, 0)
        for token in ("Inputs:", "Decision:", "reason:", "carrier:", "credential:"):
            self.assertIn(token, text)
        self.assertIn("量不到", text)  # 量不到的輸入標明（since_takeover_min 等）
        self.assertRegex(text.strip().splitlines()[-1], r"^SWITCH_PLAN=\w+ reason=")

    def test_json_form_parses_and_has_no_env(self) -> None:
        self.write_transcript(SMALL)
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = statuscmd.switch_plan_cli(["--sid", SID, "--json"], env=self.env)
        body = json.loads(buf.getvalue())
        self.assertEqual(rc, 0)
        self.assertEqual(set(body), {"inputs", "decision"})
        self.assertNotIn("env", body["inputs"])
        self.assertIn("action", body["decision"])

    def test_missing_sid_is_rc2_not_a_guess(self) -> None:
        with mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(statuscmd.switch_plan_cli([], env={}), 2)

    def test_real_process_smoke(self) -> None:
        """真行程（E2E 形態）：`python tools/sessionctl.py switch-plan --json`
        在 tmp 圍籬下 rc 0。"""
        self.write_transcript(SMALL)
        env = {**os.environ, "AUTOSDD_TRACE_DIR": str(self.tdir),
               "AUTOSDD_HANDOFF_DIR": str(self.hdir), "CLAUDE_CODE_SESSION_ID": SID}
        env.pop("AUTOSDD_UNATTENDED", None)
        done = subprocess.run([sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"),
                               "switch-plan", "--json"], capture_output=True, text=True,
                              encoding="utf-8", env=env, timeout=120, cwd=str(self.tmp))
        self.assertEqual(done.returncode, 0, msg=done.stderr)
        body = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(body["decision"]["action"], Action.STAY)


# ───────────────────────────────────────────────── 負向與原始碼掃描（AT-CTL-48、54、55、73）
_SESSIONCTL = _REPO_ROOT / "tools" / "lib" / "sessionctl"


def _imported_names(path: Path) -> set[str]:
    """該檔 import 進來的每個模組／名稱（`import a.b`、`from . import x`、`from a import b`）。"""
    names: set[str] = set()
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            for a in n.names:
                names.update(a.name.split("."))
        elif isinstance(n, ast.ImportFrom):
            names.update((n.module or "").split("."))
            names.update(a.name for a in n.names)
    return names - {""}


class StaticScansTest(unittest.TestCase):
    def test_switchplan_module_constants_are_exactly_two(self) -> None:
        """AT-CTL-48：模組常數恰為 {DEBOUNCE_MIN, DRAIN_MAX_MIN}；無數值化 ctx 門檻字面。"""
        tree = ast.parse((_SESSIONCTL / "switchplan.py").read_text(encoding="utf-8"))
        names = {t.id for n in tree.body if isinstance(n, ast.Assign) for t in n.targets
                 if isinstance(t, ast.Name) and re.fullmatch(r"[A-Z][A-Z0-9_]*", t.id)}
        self.assertEqual(names, {"DEBOUNCE_MIN", "DRAIN_MAX_MIN"})
        text = (_SESSIONCTL / "switchplan.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b\d{3}[_,]?\d{3}\b", text))  # 沒有 300000／850,000 這類字面
        imports = {m for m in re.findall(r"^from \. import (.+)$", text, re.M)}
        self.assertEqual(imports, {"control, costmodel, switch"})

    def test_no_hook_or_decision_path_calls_spawn(self) -> None:
        """AT-CTL-54：hook 不代主控 finalize／spawn（TH-1）；說明文字字串不算。"""
        files = list((_REPO_ROOT / ".claude" / "hooks").glob("*.py")) + [
            _SESSIONCTL / n for n in ("switchplan.py", "controlfacts.py", "control.py",
                                      "switchfacts.py")]
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
            with self.subTest(path=path.name):
                self.assertEqual([c for c in calls if c.split(".")[-1] == "spawn"], [],
                                 msg=f"{path.name} 呼叫 spawn")

    def test_seal_does_not_import_switchplan_and_stop_path_has_no_ensure_pending(self) -> None:
        """AT-CTL-86 末句：`seal.py` 不 import `switchplan`；
        封存閘 Stop 路徑不呼叫 `ensure_pending`。"""
        for name in ("seal.py", "converge.py"):
            tree = ast.parse((_SESSIONCTL / name).read_text(encoding="utf-8"))
            calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
            self.assertEqual([c for c in calls if c.split(".")[-1] == "ensure_pending"], [],
                             msg=f"{name} 呼叫 ensure_pending")
        self.assertEqual(_imported_names(_SESSIONCTL / "seal.py") & {"switchplan"}, set())

    def test_event_names_are_one_set_and_disjoint_from_quotawall(self) -> None:
        """AT-CTL-73：新痕跡事件名集中在 `control.CTL_EVENTS`，與 QW 的事件名集合不相交。"""
        qw_events = set()
        for path in _SESSIONCTL.glob("qw_*.py"):
            text = path.read_text(encoding="utf-8")
            qw_events |= set(re.findall(r'\bEV_\w+\s*=\s*"([a-z_]+)"', text))
            qw_events |= set(re.findall(r'switch\.trace\(\s*"([a-z_]+)"', text))
        self.assertTrue(qw_events)  # 夾具有效：真的讀到 QW 的事件名
        self.assertEqual(len(control.CTL_EVENTS), len(set(control.CTL_EVENTS)))
        self.assertFalse(set(control.CTL_EVENTS) & qw_events)
        from lib.sessionctl import parkprobe  # noqa: PLC0415

        self.assertEqual({parkprobe.EV_PROBE, parkprobe.EV_RECOVERED},
                         {control.EV_PARK_EARLY_PROBE, control.EV_PARK_EARLY_RECOVERED})


class FactsTest(_GateFence):
    """switchfacts／controlfacts：事實取自既有真相源；pending 進 `ControlState` 與 statusLine。"""

    def test_account_changed_needs_both_sides_and_a_difference(self) -> None:
        """AT-CTL-87（W5 面）：標記 `parked_account` 與當下 `account_key` 皆非空且不同才為真；
        任一側 None（含舊標記無此欄、無標記）⇒ 假；當下值取自同一次 `_pace_state` 讀數。"""
        now = datetime.now().astimezone()
        reads: list[int] = []

        def state(key):
            def read(_now):
                reads.append(1)
                return SimpleNamespace(account_key=key, axes=())
            return read

        def marker(**extra):
            return {"sid": SID, "status": "armed", **extra}

        cases = [({"parked_account": "A"}, "B", True), ({"parked_account": "A"}, "A", False),
                 ({"parked_account": "A"}, None, False), ({"parked_account": None}, "B", False),
                 ({}, "B", False)]
        for extra, now_key, want in cases:
            with self.subTest(extra=extra, now_key=now_key):
                with mock.patch("lib.sessionctl.park.read_marker", return_value=marker(**extra)):
                    got = switchfacts.account_changed(SID, now, {"state": state(now_key)})
                self.assertEqual(got, want)
        with mock.patch("lib.sessionctl.park.read_marker", return_value=None):
            reads.clear()
            self.assertFalse(switchfacts.account_changed(SID, now, {"state": state("B")}))
            self.assertEqual(reads, [])  # 無 park 標記 ⇒ 不讀額度（基準只存在於標記）

    def test_control_state_carries_the_pending_marker_into_the_status_line(self) -> None:
        """惰性建立：`control_state` 是 `ensure_pending` 的第二個呼叫點；statusLine 區段出現
        `switch pending`。"""
        from lib.sessionctl import controlfacts  # noqa: PLC0415

        self.write_transcript(HARD)
        payload = {"session_id": SID, "transcript_path": str(self.transcript),
                   "background_tasks": [{"id": "a", "type": "subagent", "status": "running"}]}
        state = controlfacts.control_state(payload, SID, self.env)
        self.assertEqual(state.pending_switch["reason"], "hard")
        self.assertIn("switch pending", control.segment_text(state))
        self.assertIn("pending_switch=yes(hard)", control.status_line(state))
        quiet = controlfacts.control_state({**payload, "background_tasks": []}, SID, self.env)
        # 標記已存在；代理交卷不作廢（只有封存／交棒／壓縮）
        self.assertIsNotNone(quiet.pending_switch)

    def test_watch_duplicate_is_traced_next_to_the_verdict(self) -> None:
        from lib.sessionctl import watchlock  # noqa: PLC0415

        with mock.patch.object(watchlock, "acquire", return_value=False):
            out = io.StringIO()
            rc = watch.run(SID, watch.Cfg(), now_fn=lambda: 1.0, sleep_fn=lambda _s: None,
                           roster_fn=lambda: [], out=out, pid=1, projects_dir=str(self.tmp))
        self.assertEqual(rc, 0)
        rows = [json.loads(x)["event"] for x in
                (self.tdir / "autosdd_session_switch.jsonl")
                .read_text(encoding="utf-8").splitlines()]
        self.assertIn(control.EV_WATCH_DUPLICATE, rows)

    def test_takeover_minutes_come_from_the_ack_stamp_of_this_sid(self) -> None:
        pkg = self.package(acker=SID)
        got = switchfacts.takeover_min(SID, self.env, datetime.now().astimezone())
        self.assertIsNotNone(got)
        self.assertLess(got, 60)  # `.ack` 寫在 5 分鐘前
        self.assertIsNone(switchfacts.takeover_min(OTHER, self.env, datetime.now().astimezone()))
        pkg.with_suffix(".ack").unlink()
        self.assertIsNone(switchfacts.takeover_min(SID, self.env, datetime.now().astimezone()))


class RenderCutHasNoExecutableCallsTest(unittest.TestCase):
    def test_agentbrief_never_launches_anything(self) -> None:
        """AT-CTL-55：被切清單只含文字與指標；`agentbrief.py` 沒有 subprocess／claude 啟動。"""
        text = (_SESSIONCTL / "agentbrief.py").read_text(encoding="utf-8")
        self.assertEqual(_imported_names(_SESSIONCTL / "agentbrief.py") & {"subprocess"}, set())
        self.assertIsNone(re.search(r"Popen|os\.system|spawn\(", text))


if __name__ == "__main__":
    unittest.main()
