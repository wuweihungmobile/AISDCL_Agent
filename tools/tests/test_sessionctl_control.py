"""tools/lib/sessionctl/control.py：控制態單一謂詞與 A4（冷叫醒閘／封存閘不再矛盾）。

W1（DES `Control_Handover_Design.md` §3～§4；TCS-Control AT-CTL-01～17、83、84）。
WHY：A4（P1）——65389f03 逐字稿中，封存閘判「封存後有工作＝封存失效」，冷叫醒閘卻把「已封存、
未交棒、主控仍工作」當已交棒、叫人 TaskStop 在飛代理與其監督 watch；兩閘矛盾。本檔證明兩閘共讀
`control.sealed_effective` 的四值，且夾具內含舊實作 oracle（證明夾具真能觸發舊 bug，DES §18 三問）。
縫：tmp 逐字稿、`env` mapping（`AUTOSDD_HANDOFF_DIR` 指 tmp）、`AUTOSDD_TRACE_DIR` 指 tmp。
"""
from __future__ import annotations

import itertools
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

import transcript_activity as ta  # noqa: E402

from lib.sessionctl import control, converge, handoff, seal, supervise, switch  # noqa: E402

SID = "0a4b1c2d-aaaa-bbbb-cccc-dddddddddddd"
HARD = 850_000
_FULL_MAIN = "\n\n".join(f"{h}\n內容 {i}" for i, h in enumerate(handoff.SECTIONS))
WATCH_SHELL = {"id": "w1", "type": "shell", "status": "running",
               "command": "python tools/sessionctl.py watch --sid x"}
KEEPWARM_SHELL = {"id": "k1", "type": "shell", "status": "running",
                  "command": "python tools/sessionctl.py keepwarm --sid x"}
CI_SHELL = {"id": "c1", "type": "shell", "status": "running",
            "command": "python tools/ci_wait.py --commit abc"}
AGENT = {"id": "a1", "type": "subagent", "status": "running"}
EDIT = ("Edit", {"type": "tool_use", "input": {}}, 2)  # 戳後的一次改檔＝封存失效


def _call(name: str, command: str | None = None) -> dict:
    data = {} if command is None else {"command": command}
    return {"type": "tool_use", "name": name, "input": data}


def _ts(minutes_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="ctl-w1-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.hdir, self.tdir = self.tmp / "handoff", self.tmp / "traces"
        self.hdir.mkdir()
        self.tdir.mkdir()
        self.transcript = self.tmp / f"{SID}.jsonl"
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tdir),
                                             "AUTOSDD_HANDOFF_DIR": str(self.hdir)})
        patch.start()
        self.addCleanup(patch.stop)
        carrier = mock.patch("lib.sessionctl.park._has_carrier", return_value=False)
        carrier.start()
        self.addCleanup(carrier.stop)

    def write_transcript(self, ctx: int = HARD, work: list[tuple[str, dict, float]] = ()) -> Path:
        usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
                 "cache_creation_input_tokens": 0, "output_tokens": 7}
        rows = [{"type": "assistant", "timestamp": _ts(30), "message": {"id": "m", "usage": usage}}]
        for name, block, minutes_ago in work:
            rows.append({"type": "assistant", "timestamp": _ts(minutes_ago),
                         "message": {"content": [dict(block, name=name)]}})
        self.transcript.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return self.transcript

    def package(self, *, finalized: bool = True) -> Path:
        main = _FULL_MAIN if finalized else "\n\n".join(f"{h}\nTODO: 填" for h in handoff.SECTIONS)
        path = self.hdir / f"{SID}_20261122T000000Z.md"
        path.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n\n"
                        f"## 機械層\n\n資料\n\n{handoff.MAIN_MARK}\n\n{main}\n", encoding="utf-8")
        return path

    def stamp(self, path: Path, text: str | None = None, minutes_ago: float = 10.0) -> None:
        path.with_suffix(".sealed").write_text((text or _ts(minutes_ago)) + "\n", encoding="utf-8")

    def stop(self, tasks=None, **extra) -> dict:
        payload = {"hook_event_name": "Stop", "session_id": SID,
                   "transcript_path": str(self.transcript), **extra}
        if tasks is not None:
            payload["background_tasks"] = tasks
        return payload

    def traces(self) -> list[dict]:
        target = self.tdir / "autosdd_session_switch.jsonl"
        return ([json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]
                if target.exists() else [])


def _old_wake_package(sid, env=None, transcript=None):
    """舊實作 oracle（A4 病灶）：只要最新包 live 且有 `.sealed` 就算「已封存」，不看封存後工作。"""
    done = seal.handed_over(sid, env)
    if done is not None:
        return done
    row = seal.latest_package(sid, env)
    return Path(row["path"]) if row and row["state"] == "live" \
        and seal.sealed_path(row["path"]).exists() else None


def _old_wakeable(tasks):
    """舊 `_finalized_wake` 的任務過濾 oracle：未交棒時只豁免 keepwarm，代理與 watch 都被列入。"""
    return [t for t in tasks if not (t.get("type") == "shell" and re.search(
        r"sessionctl\.py[\"']?\s+keepwarm\b", str(t.get("command") or "")))]


class SealedEffectiveTest(_Fence):
    """tools/lib/sessionctl/control.py::sealed_effective：四值（AT-CTL-01／02／03／05／83）。"""

    def verdict(self, minutes_ago: float = 10.0, **work) -> str:
        return control.sealed_effective(_ts(minutes_ago), self.transcript)

    def test_no_work_after_the_stamp_is_effective(self) -> None:
        """AT-CTL-01：戳後逐字稿無 tool_use ⇒ effective。"""
        self.write_transcript()
        self.assertEqual(self.verdict(), "effective")

    def test_each_kind_of_work_after_the_stamp_invalidates(self) -> None:
        """AT-CTL-02：戳後 Agent／Task／SendMessage／Edit／Write／非監督 PowerShell ⇒ invalidated
        （派工不算監督：MU-CTL-02 把 Agent 加進監督集合會使這幾格轉紅）。"""
        cases = [("Agent", {}), ("Task", {}), ("SendMessage", {}), ("Edit", {}), ("Write", {}),
                 ("PowerShell", {"input": {"command": "git commit -m x"}}),
                 ("mcp__x__y", {})]
        for name, block in cases:
            with self.subTest(name=name):
                self.write_transcript(work=[(name, {"type": "tool_use", **block}, 2)])
                self.assertEqual(self.verdict(), "invalidated")

    def test_supervision_calls_and_reads_keep_the_seal_effective(self) -> None:
        """AT-CTL-03：戳後只有監督呼叫（park／keepwarm／watch／status／handoff、TaskStop、
        AskUserQuestion、對 keepwarm 輸出檔的 Get-Content），混 Read／Grep／Glob ⇒ 仍 effective
        （MU-CTL-03：把 park／keepwarm 動詞移出監督集合 ⇒ 轉 invalidated，本測試紅）。"""
        def shell(cmd):
            return "PowerShell", {"type": "tool_use", "input": {"command": cmd}}, 3

        work = [shell("python tools/sessionctl.py park --why x"),
                shell("python tools/sessionctl.py keepwarm --sid s > kw.txt 2>&1"),
                shell("python tools/sessionctl.py watch --sid s --stall-min 20"),
                shell("python tools/sessionctl.py status"),
                shell("python tools/sessionctl.py handoff --finalize p.md"),
                shell("gc out\\keepwarm_out.txt | Select-Object -Last 3"),
                ("TaskStop", {"type": "tool_use", "input": {}}, 3),
                ("AskUserQuestion", {"type": "tool_use", "input": {}}, 3),
                ("Read", {"type": "tool_use", "input": {}}, 3),
                ("Grep", {"type": "tool_use", "input": {}}, 3)]
        self.write_transcript(work=work)
        self.assertEqual(self.verdict(), "effective")

    def test_none_unreadable_are_distinguished_before_the_transcript_matters(self) -> None:
        """AT-CTL-05／83：戳 None ⇒ none（即使逐字稿不存在）；戳壞或逐字稿讀不到 ⇒ unreadable。
        MU-CTL-43：把 none 當 unreadable 會讓從未封存的 session 不再被封存閘推回。"""
        gone = self.tmp / "nope.jsonl"
        self.assertEqual(control.sealed_effective(None, gone), "none")
        self.assertEqual(control.sealed_effective(None, None), "none")
        self.write_transcript()
        self.assertEqual(control.sealed_effective("not-a-time", self.transcript), "unreadable")
        self.assertEqual(control.sealed_effective(_ts(5), gone), "unreadable")
        self.assertEqual(control.sealed_effective(_ts(5), None), "unreadable")
        self.assertEqual(control.sealed_effective(_ts(5), self.tmp), "unreadable", "目錄不是檔")

    def test_worked_since_without_ignore_is_byte_for_byte_unchanged(self) -> None:
        """AT-CTL-07：不給 ignore ⇒ 行為與舊簽章逐字相同（監督呼叫在舊語意仍算工作）；
        給 ignore ⇒ 只排除該回真的區塊，其餘照算。"""
        self.write_transcript(work=[("TaskStop", {"type": "tool_use", "input": {}}, 2)])
        since = _ts(10)
        self.assertTrue(ta.worked_since(self.transcript, since))
        self.assertTrue(ta.worked_since(self.transcript, since, ignore=None))
        skip = control.is_supervision_call
        self.assertFalse(ta.worked_since(self.transcript, since, ignore=skip))
        self.write_transcript(work=[("TaskStop", {"type": "tool_use", "input": {}}, 2),
                                    ("Edit", {"type": "tool_use", "input": {}}, 1)])
        self.assertTrue(ta.worked_since(self.transcript, since, ignore=control.is_supervision_call))


class SupervisionCallTest(unittest.TestCase):
    """tools/lib/sessionctl/control.py::is_supervision_call：文法表（AT-CTL-06）。"""

    def test_table(self) -> None:
        sc = "python tools/sessionctl.py"
        rows = [
            (_call("TaskOutput"), True), (_call("BashOutput"), True), (_call("TaskStop"), True),
            (_call("AskUserQuestion"), True), (_call("Edit"), False), (_call("Agent"), False),
            (_call("PowerShell", f"{sc} handoff --spawn p.md"), True),
            (_call("PowerShell", f"{sc} park --status; {sc} status"), True),
            (_call("PowerShell", f"{sc} status; git commit -m x"), False),
            (_call("PowerShell", f"{sc} status && git push"), False),
            (_call("Bash", f"{sc} watch --sid s\n{sc} status"), True),
            (_call("PowerShell", f"{sc} watch --sid s\ngit commit -m x"), False),
            (_call("PowerShell", "gc out\\keepwarm_out.txt | Select-Object -Last 3"), True),
            (_call("PowerShell", "Get-Content out\\keepwarm_out.txt | Select-String x"), True),
            (_call("PowerShell", "Get-Content src\\app.py"), False),
            (_call("PowerShell", "gc out\\watch.txt | Remove-Item"), False),
            (_call("PowerShell", "python tools/ci_wait.py --commit abc"), False),
            (_call("PowerShell", "& 'py.exe' 'r\\tools\\sessionctl.py' watch --sid s"), True),
            (_call("PowerShell", "git commit -m 'sessionctl.py watch'"), False),
            (_call("PowerShell"), False), (_call("PowerShell", ""), False),
            ({"type": "tool_use", "name": "PowerShell", "input": {"command": 7}}, False),
            ({"type": "tool_use", "name": "PowerShell", "input": "x"}, False),
            ("not a dict", False), (None, False),
        ]
        for block, want in rows:
            with self.subTest(block=block):
                self.assertIs(control.is_supervision_call(block), want)

    def test_worked_since_is_called_only_from_control_inside_sessionctl(self) -> None:
        """AT-CTL-04：`tools/lib/sessionctl/*.py` 除 `control.py` 外不得呼叫 `worked_since(`
        （單一謂詞；MU-CTL-06：converge 直接呼叫即紅）。逐行掃描，不做整檔缺席斷言。"""
        offenders = []
        for path in sorted((_REPO_ROOT / "tools" / "lib" / "sessionctl").glob("*.py")):
            if path.name == "control.py":
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"\bworked_since\(", line):
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(offenders, [])


class ColdWakeA4Test(_Fence):
    """tools/lib/sessionctl/converge.py::_finalized_wake 與 seal.wake_package：A4 修法
    （AT-CTL-08～16；REQ-CTL-02／03／07）。"""

    def spawned(self, path: Path) -> None:
        switch.trace("session_switch_spawned", handoff=str(path), sid=SID, ok=True, pid=1)

    def sealed_then_dispatched(self) -> Path:
        """65389f03 2253～2335 行形狀：封存 → 戳後 Agent 派工（含監督呼叫）→ 在飛 2 代理＋watch。"""
        pkg = self.package()
        self.stamp(pkg, minutes_ago=20)
        self.write_transcript(work=[
            ("PowerShell", {"type": "tool_use",
                            "input": {"command": "python tools/sessionctl.py park --why x"}}, 15),
            ("Agent", {"type": "tool_use", "input": {}}, 10),
            ("Agent", {"type": "tool_use", "input": {}}, 9),
            ("PowerShell", {"type": "tool_use",
                            "input": {"command": "python tools/sessionctl.py watch --sid s"}}, 8)])
        return pkg

    def test_old_oracle_fires_on_the_fixture_and_the_new_gate_does_not(self) -> None:
        """AT-CTL-08（MU-CTL-01）：同一夾具，舊 oracle 回「有包」＝夾具真能觸發 A4；新閘回 ""。
        用 oracle 換掉 `seal.wake_package` 後，`_finalized_wake` 必須重現舊 bug（推 TaskStop）。"""
        self.sealed_then_dispatched()
        tasks = [AGENT, dict(AGENT, id="a2"), WATCH_SHELL]
        self.assertIsNotNone(_old_wake_package(SID, self.env), "前提：舊 oracle 把它當已封存")
        with mock.patch.object(seal, "wake_package", _old_wake_package), \
                mock.patch.object(control, "wakeable_tasks", _old_wakeable):
            self.assertIn("TaskStop", converge._finalized_wake(self.stop(tasks), self.env))
        def blocks() -> int:
            return len([r for r in self.traces() if r["event"] == "finalized_wake_block"])

        self.assertEqual(blocks(), 1, "oracle 那一次落了痕跡")
        self.assertEqual(converge._finalized_wake(self.stop(tasks), self.env), "")
        self.assertEqual(blocks(), 1, "新閘沒有再落痕跡")

    def test_the_65389f03_shape_through_the_full_stop_chain_is_silent(self) -> None:
        """AT-CTL-09：2 支 running 代理＋1 支 watch shell（有監督憑證）⇒ `converge.stop_verdict` ""
        （第二次形狀＝重封存後再派，同法）。"""
        self.sealed_then_dispatched()
        tasks = [AGENT, dict(AGENT, id="a2"), WATCH_SHELL]
        self.assertEqual(converge.stop_verdict(self.stop(tasks), self.env), "")
        pkg = next(self.hdir.glob("*.md"))
        self.stamp(pkg, minutes_ago=7)  # 重封存（再 finalize）
        self.write_transcript(work=[("Agent", {"type": "tool_use", "input": {}}, 3)])
        self.assertEqual(converge.stop_verdict(self.stop(tasks), self.env), "")

    def test_sealed_effective_pushes_only_non_supervision_non_agent_shells(self) -> None:
        """AT-CTL-10／16：封存有效、無在飛代理 ⇒ 只列 ci_wait 等 shell；keepwarm、watch 皆豁免。"""
        pkg = self.package()
        self.write_transcript()
        self.stamp(pkg)
        why = converge._finalized_wake(self.stop([CI_SHELL, KEEPWARM_SHELL, WATCH_SHELL]), self.env)
        self.assertIn("冷叫醒閘", why)
        self.assertIn("1 個", why, "只計 ci_wait 一個")
        for exempt in ([KEEPWARM_SHELL], [WATCH_SHELL], [KEEPWARM_SHELL, WATCH_SHELL]):
            self.assertEqual(converge._finalized_wake(self.stop(exempt), self.env), "", exempt)

    def test_sealed_effective_with_agents_leaves_them_to_the_supervision_gate(self) -> None:
        """AT-CTL-11（MU-CTL-07）：封存有效＋在飛代理＋watch 憑證有效 ⇒ ""；無憑證 ⇒ 冷叫醒閘 ""、
        合成輸出＝監督閘「掛 watch」，且不含 TaskStop 指令（兩閘互斥）。"""
        pkg = self.package()
        self.write_transcript()
        self.stamp(pkg)
        self.assertEqual(converge.stop_verdict(self.stop([AGENT, WATCH_SHELL]), self.env), "")
        self.assertEqual(converge._finalized_wake(self.stop([AGENT]), self.env), "")
        out = converge.stop_verdict(self.stop([AGENT]), self.env)
        self.assertIn("監督閘", out)
        self.assertIn("sessionctl.py watch", out)
        self.assertNotIn("TaskStop", out.replace("先 TaskStop 那個 watch", ""))

    def test_a_real_hand_over_still_stops_everything_but_a_self_resume_does_not(self) -> None:
        """AT-CTL-13（MU-CTL-08）：別 sid ack／spawn ⇒ 全部在飛任務（代理與 watch shell 也列）；
        原主人自續跑（`.resumed`）⇒ 不算交棒、不推。"""
        pkg = self.package()
        self.write_transcript()
        self.stamp(pkg)
        pkg.with_suffix(".ack").write_text("acked x sid=newcomer\n", encoding="utf-8")
        why = converge._finalized_wake(self.stop([AGENT, WATCH_SHELL, KEEPWARM_SHELL]), self.env)
        self.assertIn("冷叫醒閘", why)
        self.assertIn("3 個", why)
        pkg.with_suffix(".ack").unlink()
        seal.mark_resumed(pkg)  # 原主人自續跑：封存作廢、無交棒痕跡
        self.assertEqual(converge._finalized_wake(self.stop([CI_SHELL, AGENT]), self.env), "")
        self.stamp(pkg)  # 再封存（包回 live）後別人 spawn 了它
        pkg.with_suffix(".resumed").unlink()
        self.spawned(pkg)
        self.assertIn("冷叫醒閘", converge._finalized_wake(self.stop([AGENT]), self.env))

    def test_wake_package_requires_a_transcript_for_the_sealed_branch(self) -> None:
        """AT-CTL-15：無 transcript ⇒ 封存分支回 None；已交棒分支同舊。掃描鎖：本檔以 `effective`
        取得封存分支結果的呼叫一律帶 transcript。"""
        pkg = self.package()
        self.write_transcript()
        self.stamp(pkg)
        self.assertIsNone(seal.wake_package(SID, self.env))
        self.assertEqual(seal.wake_package(SID, self.env, self.transcript), pkg)
        self.spawned(pkg)
        self.assertEqual(seal.wake_package(SID, self.env), pkg)

    def test_the_128_state_product_never_emits_taskstop_and_watch_together(self) -> None:
        """AT-CTL-12（REQ-CTL-07、MU-CTL-07／08）：在飛代理 0／1 × 監督憑證有／無 × 封存四值 ×
        已交棒 是／否 × 背景 shell 無／ci_wait／watch／keepwarm ＝ 128 態；任一態 `stop_verdict`
        不同時含 TaskStop 指令與「掛 watch」指令；已交棒∧在飛代理 ⇒ 只有 TaskStop。"""
        shells = {"none": [], "ci": [CI_SHELL], "watch": [WATCH_SHELL],
                  "keepwarm": [KEEPWARM_SHELL]}
        seen = 0
        for agents, cred, seal_kind, handed, shell in itertools.product(
                (0, 1), (True, False), ("none", "unreadable", "effective", "invalidated"),
                (False, True), shells):
            with self.subTest(agents=agents, cred=cred, seal=seal_kind, handed=handed, shell=shell):
                for stale in self.hdir.glob("*"):
                    stale.unlink()
                self.package()
                pkg = next(self.hdir.glob("*.md"))
                self.write_transcript(work=[EDIT] if seal_kind == "invalidated" else [])
                if seal_kind != "none":
                    self.stamp(pkg, text="garbage" if seal_kind == "unreadable" else None)
                if handed:
                    self.spawned(pkg)
                tasks = ([AGENT] if agents else []) + shells[shell]
                verdict = supervise.VALID if cred else supervise.NONE
                with mock.patch("lib.sessionctl.supervise.credential", return_value=verdict):
                    out = converge.stop_verdict(self.stop(tasks), self.env)
                self.traces()  # 痕跡檔跨態累積，不影響判決
                has_stop = "冷叫醒閘" in out
                has_watch = "監督閘" in out
                self.assertFalse(has_stop and has_watch, out)
                if handed and agents:
                    self.assertTrue(has_stop and not has_watch, out)
                seen += 1
        self.assertEqual(seen, 128)


class SealGateAndTableTest(_Fence):
    """tools/lib/sessionctl/seal.py::stop_verdict：封存閘吃謂詞（AT-CTL-14／83／84）。"""

    def test_gate_behaviour_per_state(self) -> None:
        """AT-CTL-14：ctx≥硬線、無在飛代理——封存後只有 park／keepwarm 呼叫 ⇒ 不推；封存後 Edit
        ⇒ 推（why=封存後有工作）；unreadable ⇒ 不推；none ⇒ 照推「未封存」（MU-CTL-43／04／05）。"""
        pkg = self.package()
        self.write_transcript(work=[("PowerShell", {"type": "tool_use", "input": {
            "command": "python tools/sessionctl.py park --why x"}}, 2)])
        self.stamp(pkg, minutes_ago=10)
        self.assertEqual(seal.stop_verdict(self.stop(), self.env), "")
        self.write_transcript(work=[("Edit", {"type": "tool_use", "input": {}}, 2)])
        self.assertIn("封存閘", seal.stop_verdict(self.stop(), self.env))
        self.stamp(pkg, text="garbage")
        self.assertEqual(seal.stop_verdict(self.stop(), self.env), "")
        pkg.with_suffix(".sealed").unlink()
        self.assertIn("封存閘", seal.stop_verdict(self.stop(), self.env))
        reasons = [r["reason"] for r in self.traces() if r["event"] == "seal_stop_block"]
        self.assertEqual(reasons, ["封存後有工作", "未封存"])

    def test_never_sealed_with_a_missing_package_or_transcript_pushes_as_before(self) -> None:
        """AT-CTL-83：none ∧ ctx≥硬線 ∧ 未交棒 ∧ 無在飛代理 ⇒ 推；冷叫醒閘對 none 不推。"""
        pkg = self.package()
        self.write_transcript()
        self.assertEqual(control.sealed_effective(seal._stamp(pkg), self.transcript), "none")
        self.assertIn("封存閘", seal.stop_verdict(self.stop(), self.env))
        self.assertEqual([r["reason"] for r in self.traces() if r["event"] == "seal_stop_block"],
                         ["未封存"])
        self.assertEqual(converge._finalized_wake(self.stop([CI_SHELL]), self.env), "")

    def test_four_values_by_consumers_table(self) -> None:
        """AT-CTL-84（W1 可達的三個消費端：封存閘、冷叫醒閘、`ControlState.sealed` 顯示名；
        pending 作廢與決策表 F／F′ 住 W5 `switchplan`，屆時同表補格）。DES §3.2 表逐格。"""
        expect = {  # 值 → (封存閘推?, 冷叫醒閘對 ci shell 推?, ControlState.sealed)
            "none": (True, False, "none"), "unreadable": (False, False, "unknown"),
            "effective": (False, True, "effective"), "invalidated": (True, False, "ineffective")}
        for kind, (gate, wake, shown) in expect.items():
            with self.subTest(kind=kind):
                for stale in self.hdir.glob("*"):
                    stale.unlink()
                pkg = self.package()
                self.write_transcript(work=[EDIT] if kind == "invalidated" else [])
                if kind != "none":
                    self.stamp(pkg, text="garbage" if kind == "unreadable" else None)
                self.assertEqual(bool(seal.stop_verdict(self.stop(), self.env)), gate)
                woke = converge._finalized_wake(self.stop([CI_SHELL]), self.env)
                self.assertEqual(bool(woke), wake)
                raw = seal.effective(pkg, self.transcript)
                self.assertEqual(control.classify(control.Facts(sid=SID, sealed=raw)).sealed, shown)


class ClassifyTest(unittest.TestCase):
    """tools/lib/sessionctl/control.py::classify：事實→ControlState 純合成（AT-CTL-17）。"""

    def test_table(self) -> None:
        full = control.classify(control.Facts(
            sid="s", agents_running=2, agents_quiet=1,
            agents_cut=({"id": "a", "kind": "residue"}, {"id": "b", "kind": "bogus"}, "x"),
            supervision="valid", supervision_source="payload",
            next_wake="2026-11-22T15:30:00+08:00",
            next_wake_carrier="keepwarm", sealed="effective", handed_over="p.md",
            pending_switch={"reason": "hard", "since": "t"}, wall=True,
            park={"status": "armed"}, unacked_pkg="q.md"))
        self.assertEqual((full.agents_running, full.agents_quiet, full.supervision,
                          full.supervision_source, full.next_wake_carrier, full.sealed,
                          full.handed_over, full.wall, full.unacked_pkg),
                         (2, 1, "valid", "payload", "keepwarm", "effective", "p.md", True, "q.md"))
        self.assertEqual(full.agents_cut, [{"id": "a", "kind": "residue"}])
        self.assertEqual(full.pending_switch, {"reason": "hard", "since": "t"})
        bare = control.classify(control.Facts(
            sid="s", agents_running=-3, supervision="weird", supervision_source="payload",
            next_wake=None, next_wake_carrier="keepwarm", sealed="???",
            pending_switch={"reason": "x"}))
        self.assertEqual((bare.agents_running, bare.supervision, bare.supervision_source,
                          bare.next_wake_carrier, bare.sealed, bare.pending_switch, bare.park),
                         (0, "none", None, None, "unknown", None, None))
        for raw, shown in (("none", "none"), ("unreadable", "unknown"),
                           ("effective", "effective"), ("invalidated", "ineffective")):
            self.assertEqual(control.classify(control.Facts(sid="s", sealed=raw)).sealed, shown)


if __name__ == "__main__":
    unittest.main()
