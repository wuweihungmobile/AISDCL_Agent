"""tools/lib/sessionctl/converge.py：硬線（R216 起 85 萬）收斂閘與封存閘。

AT-TW-20～32（PreToolUse 擋 Agent／Task／Workflow、門檻鍵方向鎖）與 Stop 推回（C2；AT-TW-70～77）。
縫：tmp 逐字稿、`env` mapping（`AUTOSDD_HANDOFF_DIR` 指 tmp）、`AUTOSDD_TRACE_DIR` 指 tmp。
"""
from __future__ import annotations

import io
import json
import os
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

from lib.sessionctl import converge, costmodel, handoff, seal, switch  # noqa: E402

SID = "680d8411-58ac-4adb-9e23-521f6a7bb557"
HARD = 850_000
NOW = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
_FULL_MAIN = "\n\n".join(f"{h}\n內容 {i}" for i, h in enumerate(handoff.SECTIONS))


def _assistant(ctx: int, minutes_ago: float = 1.0) -> str:
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    stamp = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return json.dumps({"type": "assistant", "timestamp": stamp.isoformat(),
                       "message": {"id": "m", "usage": usage}})


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="tw-conv-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.slug = self.tmp / "slug"
        self.slug.mkdir()
        self.hdir = self.tmp / "handoff"
        self.hdir.mkdir()
        self.tdir = self.tmp / "traces"
        self.tdir.mkdir()
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tdir),
                                             "AUTOSDD_HANDOFF_DIR": str(self.hdir)})
        patch.start()
        self.addCleanup(patch.stop)
        # park 判準（converge.stop_verdict 尾端）預設會讀真實額度快取：本檔只測收斂閘，圍住它
        carrier = mock.patch("lib.sessionctl.park._has_carrier", return_value=False)
        carrier.start()
        self.addCleanup(carrier.stop)
        # QuotaWall Q4：Stop／PreToolUse 現在先問 `quotawall.plan`（讀真實額度、真行程表）；本檔只測
        # 收斂閘，把額度讀數圍成「量不到」＝stage none（額度牆判準另在
        # test_sessionctl_quotawall_q4）
        quota = mock.patch("lib.sessionctl.qw_wall.default_read", return_value=None)
        quota.start()
        self.addCleanup(quota.stop)

    def main(self, *ctxs: int) -> Path:
        path = self.slug / f"{SID}.jsonl"
        path.write_text("\n".join(_assistant(c) for c in ctxs) + "\n", encoding="utf-8")
        return path

    def package(self, *, finalized: bool, sid: str = SID) -> Path:
        main = _FULL_MAIN if finalized else "\n\n".join(f"{h}\nTODO: 填" for h in handoff.SECTIONS)
        path = self.hdir / f"{sid}_20261114T000000Z.md"
        path.write_text(f"# 交接包 <!-- sessionctl-handoff sid={sid} at=x -->\n\n"
                        f"## 機械層\n\n資料\n\n{handoff.MAIN_MARK}\n\n{main}\n", encoding="utf-8")
        return path

    def pre(self, tool: str, **extra) -> dict:
        return {"hook_event_name": "PreToolUse", "tool_name": tool, "session_id": SID,
                "transcript_path": str(self.slug / f"{SID}.jsonl"), **extra}

    def stop(self, **extra) -> dict:
        return {"hook_event_name": "Stop", "session_id": SID,
                "transcript_path": str(self.slug / f"{SID}.jsonl"), **extra}

    def traces(self) -> list[dict]:
        target = self.tdir / "autosdd_session_switch.jsonl"
        return ([json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]
                if target.exists() else [])


class ConvergeVerdictTest(_Fence):
    """tools/lib/sessionctl/converge.py::converge_verdict：PreToolUse 收斂閘（AT-TW-20～30）。

    R216（掌舵者 2026-11-18 裁決）語意改變，不是放寬：硬線 29 萬→85 萬、不再要求「已出聲」
    （D12／REQ-SS-15）。所以「大於舊門檻、小於新硬線」的上下文從「擋」改成「放」，原本擋的案例
    一律改用新硬線的邊界值，斷言強度不降。"""

    def test_at_tw_20_at_the_hard_line_blocks_with_every_exit(self) -> None:
        """tools/lib/sessionctl/converge.py：ctx=850,000、Agent ⇒ rc 2，訊息給三條出口；
        **沒有任何 `.advised` 閂鎖**也擋（D12：移除「須先出聲」前提）。"""
        self.main(HARD)
        self.assertEqual(list(self.hdir.iterdir()), [], "前提：本案例沒有任何出聲閂鎖")
        rc, text = converge.converge_verdict(self.pre("Agent"), self.env)
        self.assertEqual(rc, 2)
        for needle in ("收斂閘", "上下文 850,000", "硬線 850,000", "handoff --finalize", "--spawn",
                       "/compact（上下文降到門檻下自動解除）",
                       "AUTOSDD_SESSION_SWITCH_MODE=notify（只出聲）",
                       "只擋 Agent／Task／Workflow", "python tools/sessionctl.py handoff --build"):
            self.assertIn(needle, text)

    def test_at_tw_21_one_token_below_the_hard_line_passes(self) -> None:
        """tools/lib/sessionctl/converge.py：849,999 放行、850,000 擋；寫成 `>`
        會把邊界多吃一格。"""
        self.main(HARD - 1)
        # WP-4B：放行時會帶派工附註（FR-W8）⇒ 只判 rc 0，不再要求空字串
        self.assertEqual(converge.converge_verdict(self.pre("Agent"), self.env)[0], 0)
        self.main(HARD)
        self.assertEqual(converge.converge_verdict(self.pre("Agent"), self.env)[0], 2)

    def test_at_tw_22_between_the_old_and_the_new_line_is_never_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：25 萬（舊 R1）、29 萬（舊硬門檻）、60 萬都放行——
        掌舵者原話「本來有些任務就需要 Context 的內文，25 萬就切換是自我閹割功能」。
        舊版「未出聲不擋」的語意已由「不看出聲、只看硬線」取代，這格改釘『大上下文照做事』。"""
        for ctx in (250_000, 290_000, 600_000):
            with self.subTest(ctx=ctx):
                self.main(ctx)
                self.assertEqual(converge.converge_verdict(self.pre("Agent"), self.env)[0], 0)

    def test_at_tw_23_convergence_tools_are_never_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：Read／Edit／PowerShell／Grep／SendMessage／Bash 不擋——
        收斂本身需要它們，擋到無法收斂的守衛會被整個關掉（ctx 在硬線上才有意義）。"""
        self.main(HARD)
        for tool in ("Read", "Edit", "PowerShell", "Grep", "SendMessage", "Bash"):
            with self.subTest(tool):
                self.assertEqual(converge.converge_verdict(self.pre(tool), self.env), (0, ""))

    def test_at_tw_24_all_three_expansion_tools_are_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：Agent／Task／Workflow 一個都不能漏。"""
        self.main(HARD)
        for tool in ("Agent", "Task", "Workflow"):
            with self.subTest(tool):
                self.assertEqual(converge.converge_verdict(self.pre(tool), self.env)[0], 2)

    def test_at_tw_25_unattended_windows_are_never_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：
        無人窗口換 session 由 planner FRESH 路負責，擋＝窗口卡死。"""
        self.main(HARD)
        env = {**self.env, "AUTOSDD_UNATTENDED": "1"}
        self.assertEqual(converge.converge_verdict(self.pre("Agent"), env), (0, ""))

    def test_at_tw_26_notify_and_off_modes_are_the_escape_hatch(self) -> None:
        """tools/lib/sessionctl/converge.py：notify／off ⇒ 放行；auto、缺席、未知值 ⇒ 阻斷。"""
        self.main(HARD)
        for mode, expect in (("notify", 0), ("off", 0), ("auto", 2), ("", 2), ("weird", 2)):
            with self.subTest(mode=mode), redirect_stderr(io.StringIO()):
                env = {**self.env, switch.MODE_KEY: mode}
                self.assertEqual(converge.converge_verdict(self.pre("Agent"), env)[0], expect)

    def test_at_tw_27_unreadable_inputs_fail_open(self) -> None:
        """tools/lib/sessionctl/converge.py：
        逐字稿不存在／無 usage／壞 JSON／無 transcript_path ⇒ 放行。"""
        missing = self.pre("Agent")
        self.assertEqual(converge.converge_verdict(missing, self.env)[0], 0)
        (self.slug / f"{SID}.jsonl").write_text("{{壞 JSON\n", encoding="utf-8")
        self.assertEqual(converge.converge_verdict(missing, self.env)[0], 0)
        (self.slug / f"{SID}.jsonl").write_text(json.dumps({"type": "user"}) + "\n",
                                                encoding="utf-8")
        self.assertEqual(converge.converge_verdict(missing, self.env)[0], 0)
        bare = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": SID}
        self.assertEqual(converge.converge_verdict(bare, self.env)[0], 0)
        got = converge.converge_verdict("不是 dict", self.env)  # type: ignore[arg-type]
        self.assertEqual(got, (0, ""))

    def test_at_tw_28_a_subagents_own_call_is_not_gated(self) -> None:
        """tools/lib/sessionctl/converge.py：
        payload 帶非空 agent_id ⇒ 放行（閘管主控，子代理由 D6 管）。"""
        self.main(HARD)
        self.assertEqual(converge.converge_verdict(self.pre("Agent", agent_id="a9"), self.env),
                         (0, ""))

    def test_at_tw_29_a_block_leaves_a_trace(self) -> None:
        """tools/lib/sessionctl/converge.py：阻斷落 converge_block（sid／ctx／hard／tool）。"""
        self.main(HARD + 50_000)
        converge.converge_verdict(self.pre("Workflow"), self.env)
        rows = [r for r in self.traces() if r["event"] == "converge_block"]
        self.assertEqual([(r["sid"], r["ctx"], r["hard"], r["tool"]) for r in rows],
                         [(SID, HARD + 50_000, HARD, "Workflow")])

    def test_at_tw_30_the_block_has_no_latch_and_lifts_after_a_compaction(self) -> None:
        """tools/lib/sessionctl/converge.py：擋一次後尾端出現 120,000 的新回合 ⇒ 同 payload 放行。
        阻斷若進閂鎖，`/compact` 之後仍被擋。"""
        path = self.main(HARD + 50_000)
        payload = self.pre("Agent")
        self.assertEqual(converge.converge_verdict(payload, self.env)[0], 2)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(_assistant(120_000) + "\n")
        self.assertEqual(converge.converge_verdict(payload, self.env)[0], 0)
        self.assertEqual(sorted(p.name for p in self.hdir.iterdir()), [], "閘不得寫任何閂鎖檔")

    def test_the_hard_ctx_override_only_lowers_it(self) -> None:
        """tools/lib/sessionctl/converge.py：
        `AUTOSDD_SWITCH_HARD_CTX_TOKENS` 調低生效、調高退出廠值。"""
        self.main(250_000)
        low = {**self.env, switch.HARD_CTX_KEY: "200000"}
        self.assertEqual(converge.converge_verdict(self.pre("Agent"), low)[0], 2)
        self.main(HARD - 1)
        high = {**self.env, switch.HARD_CTX_KEY: "900000"}
        with redirect_stderr(io.StringIO()):
            self.assertEqual(converge.converge_verdict(self.pre("Agent"), high)[0], 0)
            self.main(HARD)
            self.assertEqual(converge.converge_verdict(self.pre("Agent"), high)[0], 2)


class HardCtxThresholdTest(unittest.TestCase):
    """tools/lib/sessionctl/switch.py：`HARD_CTX_KEY` 的出廠值與方向鎖（AT-TW-31／32）。"""

    def test_at_tw_31_overrides_are_downward_only_and_pathological_values_fall_back(self) -> None:
        """tools/lib/sessionctl/switch.py：200,000／400,000 生效；900,000、abc、-1
        退出廠值並出聲。"""
        for raw, expect, loud in (("200000", 200_000, False), ("400000", 400_000, False),
                                  ("900000", HARD, True), ("abc", HARD, True), ("-1", HARD, True)):
            with self.subTest(raw=raw), redirect_stderr(io.StringIO()) as err:
                got = switch.threshold(switch.HARD_CTX_KEY, {switch.HARD_CTX_KEY: raw})
                self.assertEqual(got[0], expect)
                self.assertEqual(bool(err.getvalue()), loud)

    def test_at_tw_32_factory_is_pinned_downward_only_and_below_the_autocompact_point(self) -> None:
        """tools/lib/sessionctl/switch.py：出廠值＝850,000、在 `_DOWNWARD_ONLY`、嚴格小於觀測到的
        流程內 autocompact 最小點（881,938）——硬線若不在它之前，autocompact 會搶先把上下文
        砍到 1～2 萬（比交接包更失真，設計 X-2）；ENV_SPEC 宣告列不得消失；R1 已退役（無出廠值）
        。"""
        got = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        self.assertIn(switch.HARD_CTX_KEY, got)
        self.assertEqual(got[switch.HARD_CTX_KEY], 850_000)
        self.assertLess(got[switch.HARD_CTX_KEY], costmodel.OBSERVED_AUTOCOMPACT_MIN)
        self.assertIn(switch.HARD_CTX_KEY, switch._DOWNWARD_ONLY)
        self.assertIsNone(got[switch.R1_KEY], "R1 已退役：出廠值必須移除，不得復活成第二條換窗線")


class StopVerdictTest(_Fence):
    """tools/lib/sessionctl/converge.py::stop_verdict＋seal.stop_verdict：封存閘（Stop，WP-3）。

    舊「收斂閘（Stop）」＝出聲 ∧ ≥ 硬門檻 ∧ 無 live 已 finalize 包；新語意＝N ≥ 硬線（R216
    起取代 R1＝25 萬；直接量逐字稿，
    不看 `.advised`）∧ 未交棒 ∧ 封存無效（AT-S1／S2／S6、A-1、E-HD-1）。"""

    def ready(self, ctx: int = HARD) -> None:
        self.main(ctx)

    def seal_it(self, path: Path, minutes_ago: float = 5.0) -> str:
        stamp = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
        path.with_suffix(".sealed").write_text(stamp + "\n", encoding="utf-8")
        return stamp

    def tool_use(self, name: str, minutes_ago: float) -> None:
        stamp = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
        row = {"type": "assistant", "timestamp": stamp,
               "message": {"content": [{"type": "tool_use", "name": name, "input": {}}]}}
        with (self.slug / f"{SID}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    def spawned(self, path: Path) -> None:
        switch.trace("session_switch_spawned", handoff=str(path), sid=SID, ok=True, pid=1)

    def test_at_s6_the_ff1000ed_shape_pushes_back_without_any_advised_latch(self) -> None:
        """AT-S6 seal.stop_verdict：sid ff1000ed 形態（包停在機械層、主控層全 TODO、沒有
        `.advised`）
        ——必須推回；舊閘要求出聲在先＋硬門檻，這個形態整個漏掉。R216：原事故 N=266,687 已不在
        換窗線上（25 萬不再推回，見 test_at_s0），所以改用硬線上的 916,687 重放同一形態。
        訊息給確切指令、封存後兩條路、不必重抄；落 seal_stop_block（原因＝未封存）。"""
        self.main(HARD + 66_687)
        draft = self.package(finalized=False)
        why = converge.stop_verdict(self.stop(), self.env)
        for needle in ("封存閘（Stop）", "916,687", str(draft), "handoff --finalize", "--spawn",
                       "結束回合即可", "不必重抄", "只推回這一次"):
            self.assertIn(needle, why)
        row = [r for r in self.traces() if r["event"] == "seal_stop_block"]
        self.assertEqual([(r["sid"], r["ctx"], r["hard"], r["reason"]) for r in row],
                         [(SID, 916_687, HARD, "未封存")])

    def test_at_s0_work_between_the_old_line_and_the_hard_line_is_never_pushed_back(self) -> None:
        """R216／AT-SS-40：25 萬（舊 R1）、26.7 萬（事故 ff1000ed）、53.4 萬（設計曾提的軟線）、
        849,999 的 Stop 都不推回封存——掌舵者裁決只留硬線；舊 R1 的突變（門檻還是 25 萬）必紅。
        反向對照：850,000 推回（test_at_s1 已釘邊界）。"""
        for ctx in (250_000, 266_687, 534_000, HARD - 1):
            with self.subTest(ctx=ctx):
                self.main(ctx)
                self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")
                self.assertEqual([r for r in self.traces() if r["event"] == "seal_stop_block"], [])

    def test_no_package_at_all_says_build_first(self) -> None:
        """seal.stop_verdict：沒有任何包 ⇒ 推回，指令先 `--build`；原因＝無包。"""
        self.ready()
        why = converge.stop_verdict(self.stop(), self.env)
        self.assertIn("--build", why)
        self.assertEqual([r["reason"] for r in self.traces() if r["event"] == "seal_stop_block"],
                         ["無包"])

    def test_at_s1_each_of_the_four_conditions_releases_and_the_fifth_blocks(self) -> None:
        """AT-S1：N < 硬線／封存有效／有在飛代理／已交棒，各自單獨成立都放行；四者皆不成立 ⇒ 推回。
        少任何一格放行，掌舵者就會在對應情境被誤推回；多放行一格，就是封存空窗重現。"""
        self.main(HARD - 1)
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")  # N < 硬線（邊界 `>=`）
        self.main(HARD)
        agent = {"id": "a1", "type": "subagent", "status": "running"}  # 無包：在飛代理 ⇒ 放行
        # WP-4B：在飛代理＋沒有監督憑證會被監督閘推回，所以這格帶有效憑證（watch shell）
        # 才測「封存閘放行」
        watch_shell = {"id": "w1", "type": "shell", "status": "running",
                       "command": "python tools/sessionctl.py watch"}
        self.assertEqual(converge.stop_verdict(
            self.stop(background_tasks=[agent, watch_shell]), self.env), "")
        self.assertNotEqual(converge.stop_verdict(self.stop(), self.env), "")  # 恰等於硬線 ⇒ 推回
        pkg = self.package(finalized=True)
        self.assertNotEqual(converge.stop_verdict(self.stop(), self.env), "")  # 寫完≠封存
        self.seal_it(pkg)
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")  # 封存有效
        pkg.with_suffix(".sealed").unlink()  # 拿掉封存 ⇒ 回到推回
        self.assertNotEqual(converge.stop_verdict(self.stop(), self.env), "")
        self.spawned(pkg)  # 已交棒（已寫完 ∧ spawn 痕跡）
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")

    def test_a1_reading_after_the_seal_does_not_invalidate_but_work_does(self) -> None:
        """A-1：封存後主控只有 Read／Grep／Glob（回答追問）⇒ 不推回；封存後一次 Edit 或
        PowerShell ⇒ 推回，原因＝封存後有工作。拿掉唯讀集合或把封存改成永遠有效，兩半各紅一個。"""
        self.ready()
        pkg = self.package(finalized=True)
        self.seal_it(pkg, minutes_ago=10)
        for name in ("Read", "Grep", "Glob"):
            self.tool_use(name, 2)
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")
        self.tool_use("Edit", 1)
        self.assertIn("封存閘", converge.stop_verdict(self.stop(), self.env))
        self.assertEqual([r["reason"] for r in self.traces() if r["event"] == "seal_stop_block"],
                         ["封存後有工作"])
        self.main(HARD)  # 換成只含 PowerShell 的一份
        self.tool_use("PowerShell", 1)
        self.assertIn("封存閘", converge.stop_verdict(self.stop(), self.env))

    def test_at_s2_seal_gate_and_park_merge_into_one_reason(self) -> None:
        """AT-S2：封存閘與 park 同時成立 ⇒ 一則合併 reason（先封存再 park），兩件事都講到；
        不是先到先贏。各自單獨成立只出各自那一個。"""
        self.ready(HARD)
        parked = "額度停工守衛（Stop）：PARK-REASON"
        # WP-QV（QVD C2／C7）：閒置側先看判決；判決 PARK 才落到 park 判準（不讀真額度）
        snap = mock.Mock(plan=mock.Mock(stage="free"), ruling=mock.Mock(action="PARK"))
        self.enterContext(mock.patch("lib.sessionctl.qw_verdict.snapshot", return_value=snap))
        with mock.patch("lib.sessionctl.park.stop_verdict", return_value=parked):
            both = converge.stop_verdict(self.stop(), self.env)
        self.assertIn("封存閘（Stop）", both)
        self.assertIn(parked, both)
        self.assertLess(both.index("封存閘"), both.index("PARK-REASON"))
        with mock.patch("lib.sessionctl.park.stop_verdict", return_value=parked):
            self.main(HARD - 1)  # 只剩 park
            self.assertEqual(converge.stop_verdict(self.stop(), self.env), parked)
        self.main(HARD)  # 只剩封存閘（park 無憑證載具 ⇒ ""）
        only = converge.stop_verdict(self.stop(), self.env)
        self.assertIn("封存閘", only)
        self.assertNotIn("PARK-REASON", only)

    def test_e_hd_1_handed_over_session_is_not_pushed_back_but_a_wake_task_is(self) -> None:
        """E-HD-1（2026-11-16 20:45 sid 70f1bbb5 真機）：finalize → spawn 痕跡 → ack 之後，Stop
        不得推回（舊 `_latest_live` 只認 live，包一 ack 就「尚無交接包」）；同狀態加一個 running
        背景任務 ⇒ 冷叫醒閘照樣推回（舊版對已 ack 的包失明）；PreToolUse 訊息說「已交棒」、
        不再叫它 build。"""
        self.main(HARD + 6_818)
        pkg = self.package(finalized=True)
        self.spawned(pkg)
        pkg.with_suffix(".ack").write_text("acked x\n", encoding="utf-8")
        self.assertEqual(handoff.list_handoffs(None, None, self.env)[-1]["state"], "acked")
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")
        shell = {"id": "b1", "type": "shell", "status": "running"}
        self.assertIn("冷叫醒閘", converge.stop_verdict(self.stop(background_tasks=[shell]),
                                                    self.env))
        rc, text = converge.converge_verdict(self.pre("Agent"), self.env)
        self.assertEqual(rc, 2)
        self.assertIn("已交棒", text)
        self.assertIn(str(pkg), text)
        self.assertNotIn("尚無交接包", text)

    def test_handed_over_needs_a_written_package_and_a_hand_off_signal(self) -> None:
        """seal.handed_over：寫完但沒 ack／spawn ⇒ 否；spawn 了但主控層仍 TODO ⇒ 否（半成品不算）；
        他人的 spawn 痕跡不算。"""
        pkg = self.package(finalized=True)
        self.assertIsNone(seal.handed_over(SID, self.env))
        switch.trace("session_switch_spawned", handoff=str(self.hdir / "other.md"), ok=True)
        self.assertIsNone(seal.handed_over(SID, self.env))
        self.spawned(pkg)
        self.assertEqual(seal.handed_over(SID, self.env), pkg)
        self.package(finalized=False)  # 同檔覆寫成半成品
        self.assertIsNone(seal.handed_over(SID, self.env))

    def test_at_tw_71_a_second_stop_is_never_pushed_back(self) -> None:
        """tools/lib/sessionctl/converge.py：stop_hook_active 為真 ⇒ 放行（每回合至多一個額外回合）
        。"""
        self.ready()
        self.assertEqual(converge.stop_verdict(self.stop(stop_hook_active=True), self.env), "")
        self.assertEqual(self.traces(), [])

    def test_at_tw_72_running_background_agents_suppress_the_pushback(self) -> None:
        """tools/lib/sessionctl/converge.py：有執行中背景代理 ⇒ 不推回（既有 Stop 出聲照舊）；背景
        shell 不算代理，仍推回；已結束的代理不算。"""
        self.ready()
        agent = {"id": "a1", "type": "subagent", "status": "running"}
        # WP-4B：無憑證的在飛代理改由監督閘推回（另見 test_sessionctl_supervise）；本格測封存閘讓路
        watch_shell = {"id": "w1", "type": "shell", "status": "running",
                       "command": "python tools/sessionctl.py watch"}
        self.assertEqual(converge.stop_verdict(
            self.stop(background_tasks=[agent, watch_shell]), self.env), "")
        shell = {"id": "b1", "type": "shell", "status": "running"}
        done = {"id": "a2", "type": "subagent", "status": "completed"}
        self.assertNotEqual(converge.stop_verdict(self.stop(background_tasks=[shell, done]),
                                                  self.env), "")

    def test_at_tw_72b_without_the_payload_field_the_file_roster_decides(self) -> None:
        """tools/lib/sessionctl/converge.py：payload 缺 background_tasks
        時讀檔名冊（執行中＝最近有記錄）。"""
        self.ready()
        folder = self.slug / SID / "subagents"
        folder.mkdir(parents=True)
        (folder / "agent-a1.jsonl").write_text(_assistant(5000, 0.2) + "\n", encoding="utf-8")
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")

    def test_at_tw_74_unattended_notify_off_and_broken_payloads_are_noops(self) -> None:
        """tools/lib/sessionctl/converge.py：無人、notify、off ⇒ 不推回；壞 payload、缺逐字稿、
        無 transcript_path ⇒ 放行（fail-open），不拋。"""
        self.ready()
        for extra in ({"AUTOSDD_UNATTENDED": "1"}, {switch.MODE_KEY: "notify"},
                      {switch.MODE_KEY: "off"}):
            with self.subTest(extra):
                self.assertEqual(converge.stop_verdict(self.stop(), {**self.env, **extra}), "")
        self.assertEqual(converge.stop_verdict({"hook_event_name": "Stop"}, self.env), "")
        self.assertEqual(converge.stop_verdict("x", self.env), "")  # type: ignore[arg-type]
        gone = {"hook_event_name": "Stop", "session_id": SID,
                "transcript_path": str(self.slug / "nope.jsonl")}
        self.assertEqual(converge.stop_verdict(gone, self.env), "")

    def test_at_tw_77_pushback_lifts_after_the_context_comes_down(self) -> None:
        """tools/lib/sessionctl/converge.py：不寫閂鎖——`/compact` 後同一 Stop 不再推回。"""
        path = self.main(HARD + 50_000)
        self.assertNotEqual(converge.stop_verdict(self.stop(), self.env), "")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(_assistant(100_000) + "\n")
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")
    def test_def_200_588_finalized_package_with_a_running_task_is_pushed_back(self) -> None:
        """AT-TW-79 tools/lib/sessionctl/converge.py::_finalized_wake：事故 sid eb1cb524（11-15）——
        交接後留著等 CI 的背景 shell，它結束時把 26.8 萬上下文的舊 session 冷叫醒、整份重寫。
        已 finalize ∧ 有執行中背景任務 ⇒ 推回並要求 TaskStop；不需出聲、不看硬門檻
        （事故當時在門檻之下）。這條放行＝交棒後的 session 還會自己醒來燒額度。"""
        self.main(HARD - 20_000)  # 硬線之下、也沒出過聲（封存閘不成立；冷叫醒閘不看上下文）
        self.seal_it(self.package(finalized=True))  # `--finalize`＝封存（E-CW-1：純寫完不算）
        shell = {"id": "b1", "type": "shell", "status": "running"}
        why = converge.stop_verdict(self.stop(background_tasks=shell), self.env)
        for needle in ("冷叫醒閘", "TaskStop", "1 個", "只推回這一次"):
            self.assertIn(needle, why)
        # 額度牆的「量不到」痕跡（Q4：Stop 先問 quotawall）不是閘的決定，不算進斷言面
        self.assertEqual([r["event"] for r in self.traces()
                          if r["event"] != "quotawall_unmeasured"], ["finalized_wake_block"])
        # A4（DES §4.2）：封存有效、未交棒時在飛代理交監督閘看管，冷叫醒閘不再叫人殺它
        # （舊斷言「代理也被推 TaskStop」正是 A4 病灶；遷移＝語意改變、不是放寬）
        agent = {"id": "a1", "type": "subagent", "status": "running"}
        verdict = converge.stop_verdict(self.stop(background_tasks=[agent]), self.env)
        self.assertNotIn("冷叫醒閘", verdict)
        self.assertIn("監督閘", verdict)

    def test_def_200_588_the_wake_gate_stays_silent_when_nothing_can_wake_it(self) -> None:
        """AT-TW-80 tools/lib/sessionctl/converge.py::_finalized_wake：假紅面（N < 硬線，
        封存閘不介入）——任務已結束、沒有
        finalize 包（平常掛著等 CI 是正當用法）、他人的包、第二次 Stop、無人、off、
        payload 沒有該欄，一律不推回。"""
        self.main(HARD - 50_000)
        shell = {"id": "b1", "type": "shell", "status": "running"}
        self.assertEqual(converge.stop_verdict(self.stop(background_tasks=[shell]), self.env), "")
        self.package(finalized=True, sid="other-sid")
        self.assertEqual(converge.stop_verdict(self.stop(background_tasks=[shell]), self.env), "")
        self.seal_it(self.package(finalized=True))  # 已封存：下列各格放行全靠各自那一個條件
        done = {"id": "b2", "type": "shell", "status": "completed"}
        # 任務已結束／清單為空＝冷叫醒閘不成立；但「已封存、沒有任何背景任務、人離開後快取會冷」正是
        # R216 保溫閘的對象，所以只判它不是冷叫醒閘（保溫閘自己的判準在 test_sessionctl_keepwarm）
        for payload in (self.stop(background_tasks=[done]), self.stop(background_tasks=[])):
            with self.subTest(payload=payload):
                self.assertNotIn("冷叫醒閘", converge.stop_verdict(payload, self.env))
        for payload, extra in ((self.stop(), {}),
                               (self.stop(background_tasks=[shell], stop_hook_active=True), {}),
                               (self.stop(background_tasks=[shell]), {"AUTOSDD_UNATTENDED": "1"}),
                               (self.stop(background_tasks=[shell]), {switch.MODE_KEY: "off"})):
            with self.subTest(payload=payload, extra=extra):
                self.assertEqual(converge.stop_verdict(payload, {**self.env, **extra}), "")

    def test_e_cw_1_a_written_but_unsealed_package_does_not_arm_the_wake_gate(self) -> None:
        """E-CW-1（2026-11-17 約 09:10 sid e4f80b15 真機）：主控在 WP-5 仍在飛時先寫完主控層（未
        `--finalize`、無 `.sealed`、未 spawn），結束回合就被冷叫醒閘推回、要它 TaskStop 做到一半的
        代理。「先備包、等代理交卷親驗後再封存」是合理路徑：純寫完 ⇒ 冷叫醒閘不成立（在飛代理改由
        監督閘看管）；封存後同一狀態 ⇒ 冷叫醒閘成立。把前提退回「寫完即算」，第一半就紅。"""
        self.main(HARD - 50_000)
        pkg = self.package(finalized=True)
        agent = {"id": "a1", "type": "subagent", "status": "running"}
        transcript = self.slug / f"{SID}.jsonl"
        self.assertIsNone(seal.wake_package(SID, self.env, transcript))
        why = converge.stop_verdict(self.stop(background_tasks=[agent]), self.env)
        self.assertNotIn("冷叫醒閘", why)
        self.assertIn("監督閘", why)
        self.seal_it(pkg)
        # 遷移（AT-CTL-15）：補傳逐字稿夾具（封存戳之後無工作）；省略 transcript ⇒ 封存分支 None
        self.assertEqual(seal.wake_package(SID, self.env, transcript), pkg)
        self.assertIsNone(seal.wake_package(SID, self.env))
        shell = {"id": "b1", "type": "shell", "status": "running"}
        self.assertIn("冷叫醒閘", converge.stop_verdict(self.stop(background_tasks=[shell]),
                                                    self.env))
        self.assertNotIn("冷叫醒閘", converge.stop_verdict(self.stop(background_tasks=[agent]),
                                                       self.env))

    def test_p2_1_a_self_resumed_session_is_never_told_it_was_handed_over(self) -> None:
        """R216 QA P2-1（暴露證據：sid 31ea79d4 自續跑後 Stop 冷叫醒閘推回兩次）：同 sid 自己 ack
        ／park RESUME 標記之後，冷叫醒閘不推（背景 shell 與在飛代理都不被叫去 TaskStop）、PreToolUse
        收斂閘不說「已交棒，請到新視窗」。反向變體：別的 sid ack 照推、照說已交棒。"""
        self.main(HARD + 1_000)
        pkg = self.package(finalized=True)
        self.seal_it(pkg)
        shell = {"id": "b1", "type": "shell", "status": "running"}
        agent = {"id": "a1", "type": "subagent", "status": "running"}
        pkg.with_suffix(".ack").write_text(f"acked x sid={SID}\n", encoding="utf-8")
        for tasks in ([shell], [agent]):
            self.assertNotIn("冷叫醒閘", converge.stop_verdict(self.stop(background_tasks=tasks),
                                                           self.env), tasks)
        text = converge.converge_verdict(self.pre("Agent"), self.env)[1]
        self.assertNotIn("已交棒", text)
        seal.mark_resumed(pkg)  # park RESUME 走這條：作廢封存
        self.assertNotIn("冷叫醒閘", converge.stop_verdict(self.stop(background_tasks=[shell]),
                                                       self.env))
        pkg.with_suffix(".ack").write_text("acked x sid=newcomer\n", encoding="utf-8")
        self.seal_it(pkg)
        pkg.with_suffix(".resumed").unlink()
        self.assertIn("冷叫醒閘", converge.stop_verdict(self.stop(background_tasks=[shell]),
                                                    self.env))
        self.assertIn("已交棒", converge.converge_verdict(self.pre("Agent"), self.env)[1])


if __name__ == "__main__":
    unittest.main()
