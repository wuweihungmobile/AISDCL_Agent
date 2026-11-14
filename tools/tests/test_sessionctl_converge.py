"""tools/lib/sessionctl/converge.py 與 handoff.is_advised：出聲之後的收斂閘。

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
from test_sessionctl_handoff import FakeRoster, FakeRunner, _quota  # noqa: E402

from lib.sessionctl import converge, handoff, switch  # noqa: E402

SID = "680d8411-58ac-4adb-9e23-521f6a7bb557"
HARD = 290_000
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

    def main(self, *ctxs: int) -> Path:
        path = self.slug / f"{SID}.jsonl"
        path.write_text("\n".join(_assistant(c) for c in ctxs) + "\n", encoding="utf-8")
        return path

    def advise(self) -> None:
        (self.hdir / f"{SID}.advised").write_text(NOW.isoformat(), encoding="utf-8")

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
    """tools/lib/sessionctl/converge.py::converge_verdict：PreToolUse 收斂閘（AT-TW-20～30）。"""

    def test_at_tw_20_advised_and_at_the_hard_ctx_blocks_with_every_exit(self) -> None:
        """tools/lib/sessionctl/converge.py：已出聲、ctx=290,000、Agent ⇒ rc 2，訊息給三條出口。"""
        self.main(HARD)
        self.advise()
        rc, text = converge.converge_verdict(self.pre("Agent"), self.env)
        self.assertEqual(rc, 2)
        for needle in ("收斂閘", "上下文 290,000", "門檻 290,000", "handoff --finalize", "--spawn",
                       "/compact（上下文降到門檻下自動解除）",
                       "AUTOSDD_SESSION_SWITCH_MODE=notify（只出聲）",
                       "只擋 Agent／Task／Workflow", "python tools/sessionctl.py handoff --build"):
            self.assertIn(needle, text)

    def test_at_tw_21_one_token_below_the_hard_ctx_passes(self) -> None:
        """tools/lib/sessionctl/converge.py：289,999 放行；寫成 `>` 會讓事故 sid 的 293,672 之外的
        邊界再被吃掉一格。"""
        self.main(HARD - 1)
        self.advise()
        self.assertEqual(converge.converge_verdict(self.pre("Agent"), self.env), (0, ""))

    def test_at_tw_22_not_yet_advised_is_never_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：沒被告知就被擋＝不公平，出聲在先是閘的前提。"""
        self.main(400_000)
        self.assertEqual(converge.converge_verdict(self.pre("Agent"), self.env), (0, ""))

    def test_at_tw_23_convergence_tools_are_never_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：Read／Edit／PowerShell／Grep／SendMessage／Bash 不擋——
        收斂本身需要它們，擋到無法收斂的守衛會被整個關掉。"""
        self.main(400_000)
        self.advise()
        for tool in ("Read", "Edit", "PowerShell", "Grep", "SendMessage", "Bash"):
            with self.subTest(tool):
                self.assertEqual(converge.converge_verdict(self.pre(tool), self.env), (0, ""))

    def test_at_tw_24_all_three_expansion_tools_are_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：Agent／Task／Workflow 一個都不能漏。"""
        self.main(400_000)
        self.advise()
        for tool in ("Agent", "Task", "Workflow"):
            with self.subTest(tool):
                self.assertEqual(converge.converge_verdict(self.pre(tool), self.env)[0], 2)

    def test_at_tw_25_unattended_windows_are_never_blocked(self) -> None:
        """tools/lib/sessionctl/converge.py：
        無人窗口換 session 由 planner FRESH 路負責，擋＝窗口卡死。"""
        self.main(400_000)
        self.advise()
        env = {**self.env, "AUTOSDD_UNATTENDED": "1"}
        self.assertEqual(converge.converge_verdict(self.pre("Agent"), env), (0, ""))

    def test_at_tw_26_notify_and_off_modes_are_the_escape_hatch(self) -> None:
        """tools/lib/sessionctl/converge.py：notify／off ⇒ 放行；auto、缺席、未知值 ⇒ 阻斷。"""
        self.main(400_000)
        self.advise()
        for mode, expect in (("notify", 0), ("off", 0), ("auto", 2), ("", 2), ("weird", 2)):
            with self.subTest(mode=mode), redirect_stderr(io.StringIO()):
                env = {**self.env, switch.MODE_KEY: mode}
                self.assertEqual(converge.converge_verdict(self.pre("Agent"), env)[0], expect)

    def test_at_tw_27_unreadable_inputs_fail_open(self) -> None:
        """tools/lib/sessionctl/converge.py：
        逐字稿不存在／無 usage／壞 JSON／無 transcript_path ⇒ 放行。"""
        self.advise()
        missing = self.pre("Agent")
        self.assertEqual(converge.converge_verdict(missing, self.env), (0, ""))
        (self.slug / f"{SID}.jsonl").write_text("{{壞 JSON\n", encoding="utf-8")
        self.assertEqual(converge.converge_verdict(missing, self.env), (0, ""))
        (self.slug / f"{SID}.jsonl").write_text(json.dumps({"type": "user"}) + "\n",
                                                encoding="utf-8")
        self.assertEqual(converge.converge_verdict(missing, self.env), (0, ""))
        bare = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": SID}
        self.assertEqual(converge.converge_verdict(bare, self.env), (0, ""))
        got = converge.converge_verdict("不是 dict", self.env)  # type: ignore[arg-type]
        self.assertEqual(got, (0, ""))

    def test_at_tw_28_a_subagents_own_call_is_not_gated(self) -> None:
        """tools/lib/sessionctl/converge.py：
        payload 帶非空 agent_id ⇒ 放行（閘管主控，子代理由 D6 管）。"""
        self.main(400_000)
        self.advise()
        self.assertEqual(converge.converge_verdict(self.pre("Agent", agent_id="a9"), self.env),
                         (0, ""))

    def test_at_tw_29_a_block_leaves_a_trace(self) -> None:
        """tools/lib/sessionctl/converge.py：阻斷落 converge_block（sid／ctx／hard／tool）。"""
        self.main(400_000)
        self.advise()
        converge.converge_verdict(self.pre("Workflow"), self.env)
        rows = [r for r in self.traces() if r["event"] == "converge_block"]
        self.assertEqual([(r["sid"], r["ctx"], r["hard"], r["tool"]) for r in rows],
                         [(SID, 400_000, HARD, "Workflow")])

    def test_at_tw_30_the_block_has_no_latch_and_lifts_after_a_compaction(self) -> None:
        """tools/lib/sessionctl/converge.py：擋一次後尾端出現 120,000 的新回合 ⇒ 同 payload 放行。
        阻斷若進閂鎖，`/compact` 之後仍被擋。"""
        path = self.main(400_000)
        self.advise()
        payload = self.pre("Agent")
        self.assertEqual(converge.converge_verdict(payload, self.env)[0], 2)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(_assistant(120_000) + "\n")
        self.assertEqual(converge.converge_verdict(payload, self.env), (0, ""))
        self.assertEqual(sorted(p.name for p in self.hdir.iterdir()), [f"{SID}.advised"])

    def test_the_hard_ctx_override_only_lowers_it(self) -> None:
        """tools/lib/sessionctl/converge.py：
        `AUTOSDD_SWITCH_HARD_CTX_TOKENS` 調低生效、調高退出廠值。"""
        self.main(250_000)
        self.advise()
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
        """tools/lib/sessionctl/switch.py：200,000 生效；400,000、abc、-1 退出廠值並出聲。"""
        for raw, expect, loud in (("200000", 200_000, False), ("400000", HARD, True),
                                  ("abc", HARD, True), ("-1", HARD, True)):
            with self.subTest(raw=raw), redirect_stderr(io.StringIO()) as err:
                got = switch.threshold(switch.HARD_CTX_KEY, {switch.HARD_CTX_KEY: raw})
                self.assertEqual(got[0], expect)
                self.assertEqual(bool(err.getvalue()), loud)

    def test_at_tw_32_factory_is_capped_pinned_downward_only_and_above_r1(self) -> None:
        """tools/lib/sessionctl/switch.py：出廠值 ≤ 290,000、在 `_DOWNWARD_ONLY`、嚴格大於 R1 出廠值
        （否則出聲前就擋）；ENV_SPEC 宣告列不得消失。"""
        got = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        self.assertIn(switch.HARD_CTX_KEY, got)
        self.assertLessEqual(got[switch.HARD_CTX_KEY], 290_000)
        self.assertIn(switch.HARD_CTX_KEY, switch._DOWNWARD_ONLY)
        self.assertGreater(got[switch.HARD_CTX_KEY], got[switch.R1_KEY])


class IsAdvisedTest(_Fence):
    """tools/lib/sessionctl/handoff.py::is_advised：與 `advise_once` 寫入端同目錄決策。"""

    class Guard:
        def read_context_feed(self, _sid, _x):
            return {"used": 10**6}

        def scan_transcript(self, _t):
            return (None,)

        def compact_boundary_count(self, _t):
            return 0

    def test_is_advised_reads_the_same_directory_advise_once_writes(self) -> None:
        """tools/lib/sessionctl/handoff.py：
        HANDOFF_DIR 指向 tmp 時，advise_once 寫、is_advised 讀同一處。"""
        transcript = self.main(10)
        self.assertFalse(handoff.is_advised(SID, env=self.env))
        text = handoff.advise_once(SID, transcript, guard=self.Guard(), env=self.env, now=NOW,
                                   runner=FakeRunner(), roster_mod=FakeRoster(), quota_fn=_quota,
                                   temp_root=self.tmp / "none")
        self.assertIn("--spawn", text)
        self.assertTrue(handoff.is_advised(SID, env=self.env))

    def test_is_advised_is_read_only_and_rejects_unsafe_session_ids(self) -> None:
        """tools/lib/sessionctl/handoff.py：
        不 mkdir（讀取端不為讀而建目錄）；sid 含路徑字元 ⇒ False。"""
        gone = self.tmp / "never-created"
        self.assertFalse(handoff.is_advised(SID, env={"AUTOSDD_HANDOFF_DIR": str(gone)}))
        self.assertFalse(gone.exists())
        self.advise()
        for bad in ("../x", "", "a/b"):
            self.assertFalse(handoff.is_advised(bad, env=self.env))

    def test_an_explicit_base_wins_over_the_environment(self) -> None:
        """tools/lib/sessionctl/handoff.py：給了 base 就只看它。"""
        other = self.tmp / "other"
        other.mkdir()
        (other / f"{SID}.advised").write_text("x", encoding="utf-8")
        self.assertTrue(handoff.is_advised(SID, base=other, env=self.env))
        self.assertFalse(handoff.is_advised(SID, env=self.env))


class StopVerdictTest(_Fence):
    """tools/lib/sessionctl/converge.py::stop_verdict：Stop 時推回一次（AT-TW-70～77）。"""

    def ready(self, ctx: int = 300_000) -> None:
        self.main(ctx)
        self.advise()

    def test_at_tw_70_advised_over_hard_no_agents_no_finalized_package_pushes_back(self) -> None:
        """tools/lib/sessionctl/converge.py：
        事故形態（出聲＋大上下文＋無代理＋無 finalize 包）⇒ 推回，
        訊息給確切下一步；落 converge_stop_block 痕跡。"""
        self.ready()
        why = converge.stop_verdict(self.stop(), self.env)
        for needle in ("收斂閘（Stop）", "300,000", "handoff --finalize", "--spawn", "/compact",
                       "只推回這一次"):
            self.assertIn(needle, why)
        self.assertEqual([r["event"] for r in self.traces()], ["converge_stop_block"])

    def test_at_tw_71_a_second_stop_is_never_pushed_back(self) -> None:
        """tools/lib/sessionctl/converge.py：
        stop_hook_active 為真 ⇒ 放行（每回合至多一個額外回合）。"""
        self.ready()
        self.assertEqual(converge.stop_verdict(self.stop(stop_hook_active=True), self.env), "")
        self.assertEqual(self.traces(), [])

    def test_at_tw_72_running_background_agents_suppress_the_pushback(self) -> None:
        """tools/lib/sessionctl/converge.py：
        有執行中背景代理 ⇒ 不推回（既有 Stop 出聲照舊）；背景 shell
        不算代理，仍推回；已結束的代理不算。"""
        self.ready()
        agent = {"id": "a1", "type": "subagent", "status": "running"}
        self.assertEqual(converge.stop_verdict(self.stop(background_tasks=[agent]), self.env), "")
        shell = {"id": "b1", "type": "shell", "status": "running"}
        done = {"id": "a2", "type": "subagent", "status": "completed"}
        self.assertNotEqual(converge.stop_verdict(self.stop(background_tasks=[shell, done]),
                                                  self.env), "")

    def test_at_tw_72b_without_the_payload_field_the_file_roster_decides(self) -> None:
        """tools/lib/sessionctl/converge.py：
        payload 缺 background_tasks 時讀檔名冊（執行中＝最近有記錄）。"""
        self.ready()
        folder = self.slug / SID / "subagents"
        folder.mkdir(parents=True)
        (folder / "agent-a1.jsonl").write_text(_assistant(5000, 0.2) + "\n", encoding="utf-8")
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")

    def test_at_tw_73_a_finalized_package_lets_the_turn_end(self) -> None:
        """tools/lib/sessionctl/converge.py：
        已 finalize 的交接包 ⇒ 放行；只有骨架（含 TODO）仍推回，
        且訊息指向那個包。他人的包不算。"""
        self.ready()
        self.package(finalized=False, sid="other-sid")
        self.assertNotEqual(converge.stop_verdict(self.stop(), self.env), "")
        draft = self.package(finalized=False)
        self.assertIn(str(draft), converge.stop_verdict(self.stop(), self.env))
        self.package(finalized=True)  # 同檔名覆寫成 finalize 版
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")

    def test_at_tw_74_unattended_notify_and_off_are_noops(self) -> None:
        """tools/lib/sessionctl/converge.py：無人、notify、off ⇒ 不推回。"""
        self.ready()
        for extra in ({"AUTOSDD_UNATTENDED": "1"}, {switch.MODE_KEY: "notify"},
                      {switch.MODE_KEY: "off"}):
            with self.subTest(extra):
                self.assertEqual(converge.stop_verdict(self.stop(), {**self.env, **extra}), "")

    def test_at_tw_75_not_advised_or_below_the_hard_ctx_never_pushes_back(self) -> None:
        """tools/lib/sessionctl/converge.py：沒出過聲、或 289,999 ⇒ 放行（出聲在先；邊界 `>=`）。"""
        self.main(400_000)
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")
        self.main(HARD - 1)
        self.advise()
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")
        self.main(HARD)
        self.assertNotEqual(converge.stop_verdict(self.stop(), self.env), "")

    def test_at_tw_76_unreadable_inputs_fail_open(self) -> None:
        """tools/lib/sessionctl/converge.py：缺逐字稿／無 transcript_path／非 dict ⇒ 放行，不拋。"""
        self.advise()
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")
        self.assertEqual(converge.stop_verdict({"hook_event_name": "Stop"}, self.env), "")
        self.assertEqual(converge.stop_verdict("x", self.env), "")  # type: ignore[arg-type]

    def test_at_tw_77_pushback_lifts_after_the_context_comes_down(self) -> None:
        """tools/lib/sessionctl/converge.py：不寫閂鎖——`/compact` 後同一 Stop 不再推回。"""
        path = self.main(300_000)
        self.advise()
        self.assertNotEqual(converge.stop_verdict(self.stop(), self.env), "")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(_assistant(100_000) + "\n")
        self.assertEqual(converge.stop_verdict(self.stop(), self.env), "")


if __name__ == "__main__":
    unittest.main()
