"""tools/lib/sessionctl/qw_guard.py、qw_prompt.py、qw_cli.py、converge.py、midwork.py、forward.py：
R218 QuotaWall Q4（含 W11a）守衛接線的驗收測試（TCS-QuotaWall AT-QW-15～19、22、30～32、53、55、
67、68、70、83、84、96；MU-QW-35、52、53）。

縫：假時鐘（`now`）、`read_quota`／`live_fn`／`ledger`／`carrier_fn` 注入、tmp 痕跡目錄；
不開任何測試用環境變數。本檔只用判準入口（`converge.*`、`qw_guard.*`、`midwork.background_idle`）；
兩支 hook 的接線（子行程）見真行程 smoke 與 test_sessionctl_hooks。
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

import quota_policy  # noqa: E402

from lib.sessionctl import (  # noqa: E402
    converge,
    forward,
    midwork,
    park,
    qw_calc,
    qw_cli,
    qw_guard,
    qw_latch,
    qw_plan,
    qw_prompt,
    qw_schema,
    ruling_io,
)

SID = "6c1d2e3f-8a41-4c1d-9d0e-3a52c1d8e911"
OTHER = "0b9a8c7d-1111-4222-8333-444455556666"
NOW = datetime.now(UTC).replace(microsecond=0)
HARD = 850_000


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def _state(pct: float, reset_min: float = 150):
    axes = (quota_policy.Axis("five_hour", pct, _iso(NOW.timestamp() + reset_min * 60)),)
    return quota_policy.QuotaState(axes, _iso(NOW.timestamp()), "test")


def _reader(state):
    return lambda _now: state


def _live(n: int):
    return lambda _sid, _transcript: (n, True)


def _write_transcript(path: Path, ctx: int) -> Path:
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    row = {"type": "assistant", "timestamp": _iso(NOW.timestamp() - 600),
           "message": {"id": "m1", "usage": usage}}
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return path


KEEPWARM_SHELL = {"id": "b1", "type": "shell", "status": "running",
                  "command": f"python tools/sessionctl.py keepwarm --sid {SID}"}


class _Base(unittest.TestCase):
    """tmp 痕跡／交接包目錄＋tmp 逐字稿（c＝20 萬）；額度讀數與在飛數一律由測試明給。"""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="qw-q4-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tmp / "trace"),
                                               "AUTOSDD_HANDOFF_DIR": str(self.tmp / "handoff")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ("AUTOSDD_UNATTENDED", "AUTOSDD_QUOTAWALL_OFF", "AUTOSDD_SESSION_SWITCH_MODE",
                    "AUTOSDD_PARK_GUARD_OFF", "AUTOSDD_KEEPWARM_OFF",
                    "AUTOSDD_SESSIONCTL_GUARD_OFF"):
            os.environ.pop(key, None)
        self.transcript = _write_transcript(self.tmp / f"{SID}.jsonl", 200_000)

    def seams(self, pct: float, reset_min: float = 150, *, n: int = 0, ledger=None) -> dict:
        return {"now": NOW, "read_quota": _reader(_state(pct, reset_min)), "live_fn": _live(n),
                "ledger": ledger if ledger is not None else {}, "carrier_fn": lambda: True}

    def pre(self, tool: str = "Agent", **extra) -> dict:
        return {"hook_event_name": "PreToolUse", "tool_name": tool, "session_id": SID,
                "transcript_path": str(self.transcript), **extra}

    def stop(self, tasks=None, **extra) -> dict:
        payload = {"hook_event_name": "Stop", "session_id": SID,
                   "transcript_path": str(self.transcript), **extra}
        if tasks is not None:
            payload["background_tasks"] = tasks
        return payload

    def events(self) -> list[str]:
        path = self.tmp / "trace" / "autosdd_session_switch.jsonl"
        if not path.is_file():
            return []
        return [json.loads(x).get("event") for x in path.read_text(encoding="utf-8").splitlines()]


# ═══════════════════════════════════════════════════════════ PreToolUse 擋派（W11a）
class PreToolWiringTest(_Base):
    """tools/lib/sessionctl/converge.py::converge_verdict → qw_guard.pretool（AT-QW-15、16、17、
    83；MU-QW-52）。"""

    def verdict(self, pct, tool="Agent", env=None, **extra):
        payload_keys = ("agent_id", "tool_input")
        payload = self.pre(tool, **{k: v for k, v in extra.items() if k in payload_keys})
        return converge.converge_verdict(payload, env or {}, **self.seams(
            pct, **{k: v for k, v in extra.items() if k in ("n", "ledger", "reset_min")}))

    def test_at_qw_83_block_text_and_boundaries(self) -> None:
        """QVD §3.5 C2（WP-QV 改寫；AT-QW-83／15／16／14／17、MU-QW-52 被取代）：額度牆的 PreToolUse
        擋派分支**退役**——判決第 3、4 列已涵蓋 stage close／wall／nodispatch，致動器只留派工閘 C1
        （`quota_gate(rule=…)`，見 `test_sessionctl_qv.ConsumerTest`）。
        本接線對任何讀數、工具、模式、
        逃生語一律不擋、不出「額度牆（PreToolUse）」字樣、不記 override。"""
        for r in (13, 12.5, 7.5):
            for tool in ("Agent", "Task", "Workflow", "Read"):
                with self.subTest(r=r, tool=tool):
                    rc, msg = self.verdict(100 - r, tool)
                    self.assertEqual(rc, 0)
                    self.assertNotIn("額度牆（PreToolUse）", msg)
        for env in ({}, {"AUTOSDD_SESSION_SWITCH_MODE": "notify"}, {"AUTOSDD_QUOTAWALL_OFF": "1"}):
            with self.subTest(env=env):
                self.assertNotIn("額度牆", self.verdict(93, env=env)[1])
        ok = {"prompt": "續派理由：補最後一個測試檔案\n其餘內容"}
        self.assertEqual(self.verdict(92.5, tool_input=ok)[0], 0)
        self.assertNotIn("quotawall_override", self.events())

    def test_at_qw_17_convergence_gate_wins_with_one_line_summary(self) -> None:
        """收斂閘照舊（與額度判決無關）：上下文達硬線 ⇒ rc 2「收斂閘」；額度牆摘要隨擋派分支退役。
        """
        self.transcript = _write_transcript(self.tmp / f"{SID}.jsonl", HARD)
        rc, msg = self.verdict(99)
        self.assertEqual(rc, 2)
        self.assertIn("收斂閘", msg)
        self.assertNotIn("額度牆（PreToolUse）", msg)


class OrderLockTest(_Base):
    """tools/lib/sessionctl/converge.py＋qw_calc.ping_pp_eff：W11a 的順序鎖——乾淨樣本門檻先於
    擋派接線（REQ-QW-71；AT-QW-84、96；MU-QW-53）。"""

    POLLUTED = {"schema": "autosdd.keepwarm/2",
                "ping_costs": [{"pp": 6.0, "clean": False}]}

    def run_case(self, pct, ctx, *, n=0, ledger=None):
        self.transcript = _write_transcript(self.tmp / f"{SID}.jsonl", ctx)
        seams = self.seams(pct, 204, n=n, ledger=ledger if ledger is not None else self.POLLUTED)
        rc, msg = converge.converge_verdict(self.pre("Agent"), {}, **seams)
        plan = qw_plan.plan(SID, self.transcript, {}, NOW, read_quota=seams["read_quota"],
                            live_fn=seams["live_fn"], ledger=seams["ledger"])
        return rc, msg, plan

    def test_at_qw_84_polluted_sample_does_not_block_the_1216_scenario(self) -> None:
        """12:16 重放（ctx 289,728、讀數 47、reset＋204 分、保溫帳 `[6.0]` 且 clean＝false）：
        污染樣本不採用 ⇒ stage free、rc 0、來源不是 measured。"""
        rc, _msg, plan = self.run_case(47, 289_728)
        self.assertEqual((rc, plan.stage), (0, "free"))
        self.assertNotEqual(plan.ping_pp_src, "measured")

    def test_at_qw_96_the_1220_incident_replay_at_54_percent(self) -> None:
        """12:20 事故回歸（讀數 54、N＝0、保溫帳 `[6.0]`）：新規則下放行；在飛 3 支（12:16 的
        N＝3）依 W11c① 可進 nodispatch，但不得是 close。"""
        rc, _msg, plan = self.run_case(54, 289_728, n=0)
        self.assertEqual((rc, plan.stage), (0, "free"))
        _rc3, _msg3, plan3 = self.run_case(53, 289_728, n=3)
        self.assertNotEqual(plan3.stage, "close")

    def test_mu_qw_52_53_dropping_the_clean_gate_flips_the_same_input_to_a_block(self) -> None:
        """MU-QW-53：把乾淨樣本門檻拿掉（n＝1 即採用量測、離群不丟棄）而保留 hook 接線 ⇒ 同一
        輸入變 rc 2（污染值被當成真成本）。證明本檔的綠來自門檻、不是巧合。"""
        mutated = {"schema": "autosdd.keepwarm/2", "ping_costs": [{"pp": 6.0, "clean": True}]}
        with (mock.patch.object(qw_calc, "MIN_CLEAN_SAMPLES", 1),
              mock.patch.object(qw_calc, "OUTLIER_X", 1000)):
            rc, _msg, plan = self.run_case(47, 289_728, ledger=mutated)
            seams = self.seams(47, 204, ledger=mutated)
            r = ruling_io.current(SID, self.transcript, {}, NOW, read_quota=seams["read_quota"],
                                  plan=plan).ruling
        self.assertEqual(plan.ping_pp_src, "measured")
        # WP-QV（QVD C2）：擋派改由判決驅動（C1）；污染值被當真成本 ⇒ 計畫收緊 ⇒ 判決不再 CONTINUE
        self.assertNotEqual(plan.stage, "free")
        self.assertNotEqual(r.action, "CONTINUE")
        self.assertEqual(rc, 0, "converge 的額度牆擋派已退役，擋派只在 C1")


# ═══════════════════════════════════════════════════════════ Stop 側
def _marker(pkg: Path, wake_min: float = 120) -> dict:
    now = NOW.timestamp()
    return {"schema": park.SCHEMA, "sid": SID, "route": park.ROUTE_H, "status": "armed",
            "parked_at": NOW.isoformat(), "reset_at": None, "fire_at": NOW.isoformat(),
            "valid_until": (NOW + timedelta(hours=4)).isoformat(), "pkg": str(pkg),
            "jobs": [{"label": "AutoSDD_HandoffSpawn_6c1d2e3f_x", "role": "primary",
                      "fire_at": NOW.isoformat(), "credential": "NextRunTime = x"}],
            "reason": "測試", "outcome": None,
            **qw_schema.marker_extra(now + wake_min * 60, "reset", now + wake_min * 60 + 600,
                                     False, None)}


class StopSideTest(_Base):
    """tools/lib/sessionctl/converge.py::stop_verdict → qw_guard（AT-QW-18、19、22、30、32、67、
    68、70）。"""

    def setUp(self) -> None:
        super().setUp()
        self.pkg = self.tmp / "handoff" / f"{SID}_20261123T000000Z.md"
        self.pkg.parent.mkdir(parents=True, exist_ok=True)
        self.pkg.write_text("x", encoding="utf-8")

    def verdict(self, payload, pct, reset_min=150, *, env=None, raw_env=None, **kw) -> str:
        return converge.stop_verdict(payload, env or {}, raw_env=raw_env,
                                     **self.seams(pct, reset_min, **kw))

    def with_park(self, marker=None):
        marker = marker or _marker(self.pkg)
        return (mock.patch.object(park, "read_marker", return_value=marker),
                mock.patch.object(park, "credential_ok", return_value=(True, "ok")))

    def test_at_qw_19_wall_mutes_every_pushback(self) -> None:
        """WHY：牆中（讀數 100）任何推回都只會燒冷重寫——整體回 ""，落 `quotawall_stop_muted`；
        靜音分類 `wall` 與 `quota`／"" 互斥。"""
        self.assertEqual(self.verdict(self.stop(tasks=[]), 100), "")
        self.assertIn("quotawall_stop_muted", self.events())
        self.assertEqual(qw_guard.mute(self.stop(), {}, **self.seams(100)), "wall")
        self.assertEqual(qw_guard.mute(self.stop(), {}, **self.seams(93)), "quota")  # close
        self.assertEqual(qw_guard.mute(self.stop(), {}, **self.seams(90)), "quota")  # nodispatch
        self.assertEqual(qw_guard.mute(self.stop(), {}, **self.seams(50)), "")

    def test_at_qw_22_inflight_close_asks_taskstop_before_any_finalize(self) -> None:
        """D-D WHY：close 且代理在飛 ⇒ 先 TaskStop 全部在飛代理再結束回合；訊息不得要求先封存
        （封存後在飛代理會被冷叫醒閘叫去殺，兩閘互斥）。MU-QW-19：次序改反必紅。"""
        agent = {"id": "a1", "type": "subagent", "status": "running"}
        why = self.verdict(self.stop(tasks=[agent]), 93)
        self.assertIn("TaskStop", why)
        self.assertNotIn("finalize", why)
        calm = self.verdict(self.stop(tasks=[agent]), 50)  # free：額度牆不推（監督閘另算）
        self.assertNotIn("額度牆", calm)
        self.assertNotIn("TaskStop 全部", calm)

    def test_at_qw_32_idle_close_lists_only_the_missing_steps(self) -> None:
        """close 閒置：無 park 無 keepwarm 列五步；有 park 無 keepwarm 只列 keepwarm；
        兩者皆有不推。"""
        why = self.verdict(self.stop(tasks=[]), 93)
        for step in ("handoff --build", "--finalize", "sessionctl.py park", "keepwarm --sid"):
            self.assertIn(step, why)
        pk = self.with_park()
        with pk[0], pk[1], mock.patch.object(qw_plan, "_pkg_live", return_value=True):
            only_kw = self.verdict(self.stop(tasks=[]), 93)
            self.assertIn("keepwarm --sid", only_kw)
            self.assertNotIn("--finalize", only_kw)
        live = {"pid": 1, **qw_schema.holder_extra(NOW.timestamp() + 3600, "chain", "reset")}
        with (pk[0], pk[1], mock.patch.object(qw_plan, "_pkg_live", return_value=True),
              mock.patch("lib.sessionctl.holder.read", return_value=live),
              mock.patch("lib.sessionctl.holder.is_live", return_value=True)):
            self.assertEqual(self.verdict(self.stop(tasks=[KEEPWARM_SHELL]), 93), "")

    def test_at_qw_68_nodispatch_and_free_do_not_push_park_none_keeps_the_old_gate(self) -> None:
        """QVD C2／C7（WP-QV 改寫；S-16 的「校準後 free 不推」被單一判決取代）：閒置側只在判決
        `PARK｜HALT_WEEKLY` 時落到 park 判準——讀數 60 ⇒ CONTINUE 不推；讀數 88（原始 ≥ prepare、
        150 分後 reset）⇒ 判決 PARK ⇒ 交 park；量不到 ⇒ 判決 CONTINUE（降級）⇒ 不推、也不呼叫。"""
        with mock.patch.object(park, "stop_verdict", return_value="LEGACY-PARK") as legacy:
            self.assertNotIn("LEGACY-PARK", self.verdict(self.stop(tasks=[KEEPWARM_SHELL]), 60))
            self.assertEqual(legacy.call_count, 0)
            blind = converge.stop_verdict(
                self.stop(tasks=[KEEPWARM_SHELL]), {}, now=NOW, read_quota=_reader(None),
                live_fn=_live(0), ledger={}, carrier_fn=lambda: True)
            self.assertNotIn("LEGACY-PARK", blind)
            self.assertEqual(legacy.call_count, 0)
            self.assertIn("LEGACY-PARK", self.verdict(self.stop(tasks=[KEEPWARM_SHELL]), 88))

    def test_at_qw_18_and_67_primary_gate(self) -> None:
        """§6.3：armed park ∧ 沒有 running 的 keepwarm／watch ⇒ 推一次（含 `keepwarm --sid`、
        `KEEPWARM_PLAN`）；有 running keepwarm ⇒ 不推；`off` 用 hook 行程原始環境判：OIR 注入的
        `AUTOSDD_KEEPWARM_OFF` 不算（照推），使用者自己設的才算（MU-QW-33）。"""
        pk = self.with_park()
        injected = {"AUTOSDD_KEEPWARM_OFF": "1"}
        with pk[0], pk[1]:
            why = self.verdict(self.stop(tasks=[]), 60)
            for needle in ("keepwarm --sid", "KEEPWARM_PLAN", "run_in_background", "PARK_VERDICT"):
                self.assertIn(needle, why)
            self.assertEqual(self.verdict(self.stop(tasks=[KEEPWARM_SHELL]), 60), "")
            self.assertIn("主載具閘", self.verdict(self.stop(tasks=[]), 60, env=injected,
                                                   raw_env={}))
            self.assertEqual(self.verdict(self.stop(tasks=[]), 60, env=injected, raw_env=injected),
                             "")

    def test_at_qw_30_stop_hook_active_never_pushes(self) -> None:
        """迴圈煞車：第二次 Stop（`stop_hook_active`）一律放行，額度類也不例外。"""
        self.assertEqual(self.verdict(self.stop(tasks=[], stop_hook_active=True), 93), "")

    def test_at_qw_70_primary_carrier_pushes_once_per_window_then_says_so(self) -> None:
        """S-18：close、無 park、running keepwarm＋holder 活且 mode＝chain：同一 (sid, 短窗視窗)
        只推一次——reset 觀測值漂移 ±5／＋70 分不算換窗；讀數已降（91）才算新窗再推一次；其後
        Stop 回 systemMessage「備援缺席」。MU-QW-40：閂鎖以 reset 精確值當鍵必紅。"""
        row = {"pid": 1, **qw_schema.holder_extra(NOW.timestamp() + 3600, "chain", "reset")}
        tasks = [KEEPWARM_SHELL]

        def at(pct, reset_min):
            payload = self.stop(tasks=tasks)
            return (self.verdict(payload, pct, reset_min),
                    converge.stop_notice(payload, {}, **self.seams(pct, reset_min)))

        with (mock.patch("lib.sessionctl.holder.read", return_value=row),
              mock.patch("lib.sessionctl.holder.is_live", return_value=True)):
            first, _ = at(94, 150)
            self.assertIn("收尾還缺", first)
            self.assertNotIn("keepwarm --sid", first)  # 主載具已在跑，只缺 park
            for pct, reset_min in ((94, 155), (95, 145), (95, 220)):
                with self.subTest(pct=pct, reset_min=reset_min):
                    why, notice = at(pct, reset_min)
                    self.assertEqual(why, "")
                    self.assertIn("備援缺席", notice)
            again, _ = at(91, 300)  # 讀數已降 ⇒ 新視窗 ⇒ 再推一次
            self.assertIn("收尾還缺", again)
            self.assertIn("quotawall_backup_absent", self.events())

    def test_at_qw_70_latch_unwritable_never_loses_the_push(self) -> None:
        """閂鎖讀寫失敗 ⇒ 視為未推（寧可多推一次，不漏推）。"""
        row = {"pid": 1, **qw_schema.holder_extra(NOW.timestamp() + 3600, "chain", "reset")}
        with (mock.patch("lib.sessionctl.holder.read", return_value=row),
              mock.patch("lib.sessionctl.holder.is_live", return_value=True),
              mock.patch.object(qw_latch, "_write", return_value=False)):
            for _ in range(2):
                self.assertIn("收尾還缺", self.verdict(self.stop(tasks=[KEEPWARM_SHELL]), 94))


# ═══════════════════════════════════════════════════════════ midwork（S-18）
class MidworkPrimaryTest(_Base):
    """tools/lib/sessionctl/midwork.py::background_idle：帶目標主載具＝會叫醒主控續工的事件源
    （AT-QW-70；MU-QW-35）。"""

    def holder(self, mode="chain", wake_min=60):
        # midwork 用真實 now 判 wake_at 是否在未來，所以這裡的時刻相對真實當下
        row = {"pid": 1, **qw_schema.holder_extra(datetime.now().timestamp() + wake_min * 60,
                                                  mode, "reset")}
        return (mock.patch("lib.sessionctl.holder.read", return_value=row),
                mock.patch("lib.sessionctl.holder.is_live", return_value=True))

    def payload(self, tasks):
        return {"session_id": SID, "background_tasks": tasks}

    def test_targeted_primary_is_not_idle_but_periodic_and_no_holder_still_are(self) -> None:
        """chain／single ⇒ 不是閒置（半路停工不判）；periodic 只保溫不續工 ⇒ 維持排除（舊行為）；
        wake_at 已過 ⇒ 不算。"""
        for mode, idle in (("chain", False), ("single", False), ("periodic", True)):
            with self.subTest(mode=mode):
                a, b = self.holder(mode)
                with a, b:
                    self.assertIs(midwork.background_idle(self.payload([KEEPWARM_SHELL])), idle)
        a, b = self.holder("chain", wake_min=-5)
        with a, b:
            self.assertTrue(midwork.background_idle(self.payload([KEEPWARM_SHELL])))

    def test_race_grace_is_granted_once_per_background_task_id(self) -> None:
        """QA3 P3-7：holder 尚未寫入但有 running 的本 sid keepwarm shell ⇒ 同一背景任務 id 只寬限
        一次 Stop（第二次起照舊判；寫不進閂鎖也不得長期壓住推回）。"""
        with mock.patch("lib.sessionctl.holder.read", return_value=None):
            payload = self.payload([KEEPWARM_SHELL])
            self.assertFalse(midwork.background_idle(payload))
            self.assertTrue(midwork.background_idle(payload))
            other = dict(KEEPWARM_SHELL, id="b2")
            self.assertFalse(midwork.background_idle(self.payload([other])))

    def test_any_real_background_work_or_missing_field_keeps_the_old_semantics(self) -> None:
        """一般背景工作在跑 ⇒ 不是閒置；欄位缺席（舊 harness）⇒ 不判；沒有任何 running ⇒ 閒置。"""
        sub = {"id": "a1", "type": "subagent", "status": "running"}
        self.assertFalse(midwork.background_idle(self.payload([sub])))
        self.assertFalse(midwork.background_idle({"session_id": SID}))
        self.assertTrue(midwork.background_idle(self.payload([])))


# ═══════════════════════════════════════════════════════════ UserPromptSubmit
class ForwardStayAndFailureNoticeTest(_Base):
    """tools/lib/sessionctl/forward.py＋qw_prompt.py：留在本窗記續跑（REQ-QW-40；AT-QW-51）與 park
    失敗提示（REQ-QW-35；AT-QW-53）。"""

    def payload(self, prompt="繼續"):
        return {"hook_event_name": "UserPromptSubmit", "session_id": SID, "prompt": prompt,
                "prompt_id": "abcdef0123", "transcript_path": str(self.transcript)}

    def failed_marker(self, sid=OTHER, at=None):
        at = at or (NOW - timedelta(minutes=5)).isoformat()
        marker = _marker(self.tmp / "p.md")
        marker.update({"sid": sid, "status": "failed", "pkg": None,
                       "outcome": {"at": at, "attempts": [
                           {"route": "RESUME", "attempted": True, "rc": 3},
                           {"route": "FRESH", "attempted": False, "reason": "dirty"}]}})
        ok, why = park.write_marker(marker)
        self.assertTrue(ok, why)

    def test_at_qw_53_a_failure_is_injected_once_into_the_next_human_prompt(self) -> None:
        """WHY：park 到點失敗鏈全數失敗時沒有人知道（2026-11-20 22:42）；必達管道＝人眼必經的入口。
        同一個失敗只注入一次（systemMessage＋additionalContext 都有）；機器注入的提示不算。"""
        self.failed_marker()
        machine = forward.hook_output(self.payload("<task-notification>x</task-notification>"), {})
        self.assertIsNone(machine)
        first = forward.hook_output(self.payload(), {}, now=NOW)
        self.assertIsNotNone(first)
        for text in (first["systemMessage"], first["hookSpecificOutput"]["additionalContext"]):
            self.assertIn("park 到點續航失敗", text)
            self.assertIn("RESUME(rc=3)", text)
            self.assertIn("FRESH(dirty)", text)
        self.assertIsNone(forward.hook_output(self.payload(), {}, now=NOW))  # 同一失敗不重說
        self.failed_marker(at=NOW.isoformat())  # 新的失敗 ⇒ 再說一次
        self.assertIsNotNone(forward.hook_output(self.payload(), {}, now=NOW))

    def test_notice_is_silent_when_off_unattended_or_the_failure_is_old(self) -> None:
        """無人窗口／守衛關閉／模式 off／失敗早於有效期 ⇒ 不出聲；提示壞了不得擋住打字。"""
        self.failed_marker()
        for env in ({"AUTOSDD_UNATTENDED": "1"}, {"AUTOSDD_SESSIONCTL_GUARD_OFF": "1"},
                    {"AUTOSDD_SESSION_SWITCH_MODE": "off"}):
            with self.subTest(env=env):
                self.assertEqual(qw_prompt.failure_notice(self.payload(), env, now=NOW), "")
        self.assertEqual(qw_prompt.failure_notice(
            self.payload(), {}, now=NOW + timedelta(days=park.AT_MAX_SECONDS // 86400 + 1)), "")
        with mock.patch.object(qw_prompt, "failed_markers", side_effect=RuntimeError("x")):
            self.assertEqual(qw_prompt.failure_notice(self.payload(), {}, now=NOW), "")

    def test_at_qw_51_staying_in_this_window_records_the_resume(self) -> None:
        """WHY：留在本窗（快取熱／`f4_resume_cheaper`／`留：`）的原主人就是自續跑；不記 `.resumed`
        的話封存閘與冷叫醒閘仍把它當「已封存待交棒」推回（MU-QW-20）。"""
        for prompt, cache in (("留：先回答我", {"cold": True}), ("短追問", {"cold": False})):
            with self.subTest(prompt=prompt):
                pkg = self.tmp / "handoff" / f"{SID}_20261123T000000Z.md"
                pkg.parent.mkdir(parents=True, exist_ok=True)
                head = f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n\n## 主控層\n"
                pkg.write_text(head, encoding="utf-8")
                pkg.with_suffix(".sealed").write_text(NOW.isoformat() + "\n", encoding="utf-8")
                pkg.with_suffix(".resumed").unlink(missing_ok=True)
                forward.prompt_verdict(self.payload(prompt), os.environ, now=NOW,
                                       cache=lambda p, n, c=cache: c, crons=lambda sid: False)
                self.assertTrue(pkg.with_suffix(".resumed").exists())
                self.assertFalse(pkg.with_suffix(".sealed").exists())


# ═══════════════════════════════════════════════════════════ 動詞與 status 列
class VerbAndStatusTest(_Base):
    """tools/lib/sessionctl/qw_cli.py：`sessionctl quotawall` 與 status 憑證列（AT-QW-55；
    E2E-QW-01、25 的單元前身）。"""

    def run_cli(self, argv, env=None, **seams) -> tuple[int, str]:
        out = io.StringIO()
        seams = {"now": NOW, "read_quota": _reader(_state(93)), "live_fn": _live(0),
                 "ledger": {}, **seams}
        rc = qw_cli.cli(argv, env if env is not None else {}, out=out, **seams)
        return rc, out.getvalue()

    def test_verb_prints_plan_lines_and_target_with_rc0(self) -> None:
        """c＝20 萬、D＝150、R＝7 ⇒ close；末行含 `QUOTAWALL_PLAN=stage=close`；另有
        `QUOTAWALL_TARGET=`（close ⇒ 來源 reset）。唯讀，rc 0。"""
        with mock.patch("lib.sessionctl.keepwarm.find_transcript", return_value=self.transcript):
            rc, text = self.run_cli(["--sid", SID])
        self.assertEqual(rc, 0)
        self.assertIn("QUOTAWALL_PLAN=stage=close", text)
        self.assertIn("calibrated=", text)
        self.assertRegex(text, r"QUOTAWALL_TARGET=\S+ source=reset")

    def test_unattended_prints_none_and_missing_sid_is_a_usage_error(self) -> None:
        """E2E-QW-25：無人窗口 ⇒ `stage=none reason=unattended`；缺 sid ⇒ rc 2。"""
        with mock.patch("lib.sessionctl.keepwarm.find_transcript", return_value=self.transcript):
            rc, text = self.run_cli(["--sid", SID], env={"AUTOSDD_UNATTENDED": "1"})
        self.assertEqual(rc, 0)
        self.assertIn("stage=none reason=unattended", text)
        self.assertEqual(self.run_cli([], env={})[0], 2)

    def test_status_lines_are_three_rows_and_absent_is_said_aloud(self) -> None:
        """AT-QW-55：缺席照實印 `absent`；三列次序 primary／backup／sentinel。"""
        with (mock.patch("lib.sessionctl.holder.read", return_value=None),
              mock.patch("lib.sessionctl.park_status.sentinel_line",
                         return_value="sentinel: absent")):
            lines = qw_cli.status_lines(SID)
        self.assertEqual([x.split(":")[0] for x in lines], ["primary", "backup", "sentinel"])
        self.assertEqual(lines[0], "primary: absent")


if __name__ == "__main__":
    unittest.main()
