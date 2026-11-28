"""W4b：ack 後撤原 session 的 park（Control_Handover D-CT-12、REQ-CTL-47、AT-CTL-85、MU-CTL-44／49）
與被切代理三處出聲接線（REQ-CTL-20、AT-CTL-39／40）。

受測模組：`tools/lib/sessionctl/ackhook.py`（`on_ack`、`after_handoff`）、
`tools/lib/sessionctl/park_cli.py::cancel_marker`、`tools/lib/sessionctl/cutvoice.py`
（`stop_text`／`watch_text`／`brief_text`）與 `roster.stop_message`、`watch.run`、
`briefline.orphan_line` 的呼叫點。全用 tmp 居所與假排程後端；不碰真排程器、真 `~/.claude`。
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from test_sessionctl_park import FakeBackend  # noqa: E402

from lib.sessionctl import (  # noqa: E402
    ackhook,
    agentbrief,
    briefline,
    cutvoice,
    handoff,
    park,
    park_cli,
    roster,
    watch,
)

OWNER = "798a7bf1-a991-4a08-8ab8-d0736296f823"
ACKER = "bbbbbbbb-1111-2222-3333-444444444444"
LABEL = "AutoSDD_RV_sbx_HandoffSpawn_798a7bf1_202611152002"
SOURCE_DIR = _REPO_ROOT / "tools" / "lib" / "sessionctl"


def _marker(status: str = "armed", sid: str = OWNER) -> dict:
    now = datetime(2026, 11, 23, 8, 0, 0, tzinfo=UTC)
    fire = now + timedelta(hours=3)
    return {"schema": park.SCHEMA, "sid": sid, "route": park.ROUTE_H, "status": status,
            "parked_at": now.isoformat(), "reset_at": (now + timedelta(hours=2)).isoformat(),
            "fire_at": fire.isoformat(), "valid_until": (fire + timedelta(hours=1)).isoformat(),
            "axis": {"kind": "five_hour", "pct": 98.0}, "pkg": None, "why": None,
            "jobs": [{"label": LABEL, "role": "primary", "fire_at": fire.isoformat(),
                      "credential": "NextRunTime = 2026-11-23 11:00:00（排程器自報）"}],
            "reason": "測試", "outcome": None}


class AckFenceTestCase(unittest.TestCase):
    """tmp 居所＋假排程後端；`self.pkg` 是 OWNER 的交接包。"""

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="w4b-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.hdir = self.tmp / "handoff"
        self.hdir.mkdir()
        patch = mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tmp / "traces"), "AUTOSDD_HANDOFF_DIR": str(self.hdir)})
        patch.start()
        self.addCleanup(patch.stop)
        (self.tmp / "traces").mkdir()
        self.backend = FakeBackend()
        self.backend.jobs.add(LABEL)
        self.S = {"backend": self.backend}
        # WP-SW REQ-CTL-53／58：`after_handoff` 現在會在 ack 之後列舉真排程器並 GC 舊哨兵殘骸；本檔測的是
        # park 撤銷（on_ack），不得讓單元測試碰真排程器（真殘骸 `AutoSDD_Sentinel_*` 是證據，不准拆）。
        # 摘要／GC 另由 test_sessionctl_ackevents／test_sessionctl_sentgc 以假後端釘住。
        self.summarize = mock.patch.object(ackhook, "summarize_and_gc")
        self.summarize_mock = self.summarize.start()
        self.addCleanup(self.summarize.stop)
        self.pkg = self.hdir / f"{OWNER}_20261123T080000Z.md"
        self.pkg.write_text(f"# 交接包 <!-- sessionctl-handoff sid={OWNER} at=x -->\n",
                            encoding="utf-8")

    def arm(self, status: str = "armed") -> None:
        ok, msg = park.write_marker(_marker(status))
        self.assertTrue(ok, msg)

    def on_ack(self, acker: str = ACKER) -> str:
        with mock.patch("sys.stdout", new_callable=io.StringIO):
            return ackhook.on_ack(self.pkg, acker, {}, self.S)

    def disarms(self) -> list:
        return [c for c in self.backend.calls if c[0] == "disarm"]


class OnAckTest(AckFenceTestCase):
    """tools/lib/sessionctl/ackhook.py::on_ack（AT-CTL-85）。"""

    def test_other_session_ack_cancels_the_armed_park_and_tears_the_backup_down(self) -> None:
        """擁有者≠acker 且 armed ⇒ 標記 cancelled、outcome.event=acked、備援排程被拆（MU-CTL-49：
        只改標記不拆排程會在這裡紅）。"""
        self.arm()
        self.assertEqual(self.on_ack(), "cancelled")
        marker = park.read_marker(OWNER)
        self.assertEqual((marker["status"], marker["outcome"]["event"]), ("cancelled", "acked"))
        self.assertEqual(self.disarms(), [("disarm", LABEL)])
        self.assertNotIn(LABEL, self.backend.jobs)

    def test_self_resume_does_not_cancel(self) -> None:
        """擁有者＝acker（自續跑）⇒ 不撤（MU-CTL-44：自續跑也撤會在這裡紅）。"""
        self.arm()
        self.assertEqual(self.on_ack(acker=OWNER), "self")
        self.assertEqual(park.read_marker(OWNER)["status"], "armed")
        self.assertEqual(self.disarms(), [])

    def test_no_marker_or_non_armed_marker_is_a_silent_noop(self) -> None:
        """無標記／已 cancelled／已 fired ⇒ 無動作（冪等）、不碰排程器。"""
        self.assertEqual(self.on_ack(), "noop")
        for status in ("cancelled", "fired"):
            with self.subTest(status=status):
                self.arm(status)
                self.assertEqual(self.on_ack(), "noop")
                self.assertEqual(park.read_marker(OWNER)["status"], status)
        self.assertEqual(self.disarms(), [])

    def test_second_ack_of_the_same_package_does_not_cancel_again(self) -> None:
        """同一包二次 ack ⇒ 第二次是 noop，排程器只被拆一次。"""
        self.arm()
        self.assertEqual(self.on_ack(), "cancelled")
        self.assertEqual(self.on_ack(), "noop")
        self.assertEqual(len(self.disarms()), 1)

    def test_teardown_failure_keeps_the_marker_armed_and_reports_failed(self) -> None:
        """拆不掉（量不到不宣稱已移除）⇒ failed、標記維持 armed；不拋（ack 已成功）。"""
        self.arm()
        self.backend.disarm_rc = 1
        with mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(self.on_ack(), "failed")
        self.assertEqual(park.read_marker(OWNER)["status"], "armed")

    def test_exceptions_never_escape(self) -> None:
        """任何例外 ⇒ failed、不拋，ack 的 rc 不受影響。"""
        with mock.patch.object(park, "read_marker", side_effect=RuntimeError("x")), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(self.on_ack(), "failed")

    def test_ackhook_has_no_scheduler_primitives(self) -> None:
        """原始碼掃描（AST，不看文件字串）：ackhook.py 不 import／引用 schtasks／launchctl／
        subprocess 等排程器原語——拆除只經 park_cli。"""
        tree = ast.parse((SOURCE_DIR / "ackhook.py").read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        for word in ("schtasks", "launchctl", "subprocess", "schedule_backend"):
            self.assertNotIn(word, names)

class CancelMarkerTest(AckFenceTestCase):
    """tools/lib/sessionctl/park_cli.py::cancel_marker：`park --cancel` 與 ack 共用的核心。"""

    def test_default_event_is_cancel_and_cli_path_is_unchanged(self) -> None:
        self.arm()
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(park_cli.cancel_marker(OWNER, self.S), 0)
        self.assertIn("park 已取消", out.getvalue())
        self.assertEqual(park.read_marker(OWNER)["outcome"]["event"], "cancel")

    def test_no_marker_prints_and_returns_zero(self) -> None:
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(park_cli.cancel_marker(OWNER, self.S), 0)
        self.assertIn("無 park 標記", out.getvalue())


class AfterHandoffTest(AckFenceTestCase):
    """tools/lib/sessionctl/ackhook.py::after_handoff：`tools/sessionctl.py handoff` 分支的掛點。"""

    def test_successful_ack_triggers_cancel_and_returns_the_original_rc(self) -> None:
        self.arm()
        env = {"CLAUDE_CODE_SESSION_ID": ACKER}
        with mock.patch.object(park_cli, "_backend", return_value=self.backend), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(ackhook.after_handoff(["--ack", str(self.pkg)], 0, env), 0)
        self.assertEqual(park.read_marker(OWNER)["status"], "cancelled")

    def test_equals_form_is_understood(self) -> None:
        self.arm()
        env = {"CLAUDE_CODE_SESSION_ID": ACKER}
        with mock.patch.object(park_cli, "_backend", return_value=self.backend), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            ackhook.after_handoff([f"--ack={self.pkg}"], 0, env)
        self.assertEqual(park.read_marker(OWNER)["status"], "cancelled")

    def test_failed_ack_or_other_verbs_do_not_touch_park(self) -> None:
        self.arm()
        env = {"CLAUDE_CODE_SESSION_ID": ACKER}
        self.assertEqual(ackhook.after_handoff(["--ack", str(self.pkg)], 1, env), 1)
        self.assertEqual(ackhook.after_handoff(["--list"], 0, env), 0)
        self.assertEqual(ackhook.after_handoff(["--ack"], 0, env), 0)
        self.assertEqual(park.read_marker(OWNER)["status"], "armed")
        self.summarize_mock.assert_not_called()

    def test_wpsw_a_successful_ack_runs_the_summary_and_gc_after_the_cancel(self) -> None:
        """WP-SW：ack 成功（rc 0）才摘要＋GC，且在撤 park 之後（摘要④要看得到撤銷事實）；rc 原樣。"""
        self.arm()
        env = {"CLAUDE_CODE_SESSION_ID": ACKER}
        with mock.patch.object(park_cli, "_backend", return_value=self.backend), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(ackhook.after_handoff(["--ack", str(self.pkg)], 0, env), 0)
        self.summarize_mock.assert_called_once()
        self.assertEqual(self.summarize_mock.call_args.args[:2], (str(self.pkg), ACKER))
        self.assertEqual(park.read_marker(OWNER)["status"], "cancelled", "摘要在撤 park 之後才跑")

    def test_sessionctl_entry_wires_the_hook_in_one_line(self) -> None:
        """`tools/sessionctl.py` 的 handoff 分支呼叫 `ackhook.after_handoff`。"""
        text = (_REPO_ROOT / "tools" / "sessionctl.py").read_text(encoding="utf-8")
        self.assertEqual(sum(1 for ln in text.splitlines() if "ackhook.after_handoff" in ln), 1)


# ───────────────────────────────────────────────────────── 被切出聲（REQ-CTL-20）
def _jsonl(path: Path, recs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                    encoding="utf-8", newline="\n")


def _iso(minutes_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def _task() -> dict:
    return {"type": "user", "timestamp": _iso(180),
            "message": {"role": "user", "content": "任務書X"}}


def _cut() -> dict:
    return {"type": "assistant", "timestamp": _iso(120), "apiError": "usage_limit_reached",
            "message": {"model": "<synthetic>", "content": [
                {"type": "text", "text": "You've hit your 5-hour limit"}]}}


def _alive() -> dict:
    return {"type": "assistant", "timestamp": _iso(1), "message": {
        "model": "sonnet", "usage": {"input_tokens": 1, "cache_read_input_tokens": 9,
                                     "cache_creation_input_tokens": 0},
        "content": [{"type": "text", "text": "還在跑"}]}}


class CutVoiceTestCase(unittest.TestCase):
    """tools/lib/sessionctl/cutvoice.py：三處出聲同一份文字、Stop 一次性。"""

    SID = "cccccccc-1111-2222-3333-444444444444"

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="w4b-cut-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.proj = self.tmp / "proj"
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.tmp / "traces")})
        patch.start()
        self.addCleanup(patch.stop)
        (self.tmp / "traces").mkdir()
        _jsonl(self.proj / f"{self.SID}.jsonl", [_task()])

    def agent(self, aid: str, recs: list[dict]) -> None:
        folder = self.proj / self.SID / "subagents"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"agent-{aid}.meta.json").write_text(
            json.dumps({"description": f"代理 {aid}", "model": "sonnet"}), encoding="utf-8")
        _jsonl(folder / f"agent-{aid}.jsonl", recs)
        old = datetime.now().timestamp() - 7200  # 靜默已久（名冊判 quiet，不是 running）
        os.utime(folder / f"agent-{aid}.jsonl", (old, old))

    def payload(self) -> dict:
        return {"hook_event_name": "Stop", "session_id": self.SID,
                "transcript_path": str(self.proj / f"{self.SID}.jsonl")}


class StopVoiceTest(CutVoiceTestCase):
    """tools/lib/sessionctl/roster.py::stop_message ＋ cutvoice.stop_text（AT-CTL-39）。"""

    def test_cut_agent_is_listed_once_per_sid(self) -> None:
        self.agent("cutx", [_task(), _cut()])
        first = roster.stop_message(self.payload())
        self.assertIn("cut（usage_limit）", first)
        self.assertIn("cutx", first)
        self.assertIn("不自動重派", first)
        self.assertEqual(roster.stop_message(self.payload()), "")  # 已提示過 ⇒ 不重複

    def test_a_new_cut_is_announced_but_the_old_one_is_not_repeated(self) -> None:
        self.agent("cut1", [_task(), _cut()])
        roster.stop_message(self.payload())
        self.agent("cut2", [_task(), _cut()])
        text = roster.stop_message(self.payload())
        self.assertIn("cut2", text)
        self.assertNotIn("cut1", text)

    def test_no_cut_leaves_existing_output_verbatim(self) -> None:
        """無被切 ⇒ stop_message 與舊判準（`_running_text`）逐字相同（含空字串）。"""
        self.assertEqual(roster.stop_message(self.payload()), "")
        self.agent("live", [_task(), _alive()])
        self.assertEqual(roster.stop_message(self.payload()),
                         roster._running_text(self.payload()))

    def test_bad_payload_is_fail_open(self) -> None:
        self.assertEqual(cutvoice.stop_text({}), "")
        self.assertEqual(cutvoice.stop_text({"session_id": "../x"}), "")


class WatchAndBriefVoiceTest(CutVoiceTestCase):
    """watch.run 判決處置字尾與 briefline.orphan_line 的被切列（AT-CTL-40）。"""

    def test_watch_verdict_carries_the_cut_list_before_the_last_line(self) -> None:
        self.agent("cutw", [_task(), _cut()])
        row = {"id": "cutw", "owner_sid": self.SID, "description": "代理 cutw", "model": "sonnet",
               "state": "quiet", "ctx_tokens": 10, "last_at": _iso(120), "end_turn": True}
        clock = {"t": datetime.now().timestamp()}
        out = io.StringIO()
        rc = watch.run(self.SID, watch.Cfg(), now_fn=lambda: clock["t"],
                       sleep_fn=lambda s: clock.__setitem__("t", clock["t"] + s),
                       roster_fn=lambda: [dict(row)], end_turn_fn=lambda a: True,
                       quota_fn=lambda: False, anchor_fn=lambda: None, out=out, pid=4243,
                       projects_dir=self.proj, read_quota=lambda _n: None,
                       refresh=lambda _n: (_ for _ in ()).throw(RuntimeError("x")))
        self.assertEqual(rc, 0)
        lines = out.getvalue().strip().splitlines()
        self.assertTrue(lines[-1].startswith("WATCH_VERDICT="), lines[-1])
        self.assertIn("cut（usage_limit）", out.getvalue())

    def test_session_start_announces_the_cut_agent_list(self) -> None:
        other = "dddddddd-1111-2222-3333-444444444444"
        folder = self.proj / other / "subagents"
        folder.mkdir(parents=True)
        (folder / "agent-cuts.meta.json").write_text(
            json.dumps({"description": "切斷的", "model": "sonnet"}), encoding="utf-8")
        _jsonl(folder / "agent-cuts.jsonl", [_task(), _cut()])
        rows = [{"id": "cuts", "owner_sid": other, "description": "切斷的", "model": "sonnet",
                 "state": "quiet", "ctx_tokens": 10, "last_at": _iso(60)}]
        with mock.patch.object(roster, "_agent_path",
                               return_value=folder / "agent-cuts.jsonl"):
            text = briefline.orphan_line(self.SID, {}, agents_fn=lambda _e: rows)
        self.assertIn("其中 1 支被額度切斷", text)
        self.assertIn("cut（usage_limit）", text)

    def test_three_sites_share_one_text_function(self) -> None:
        """原始碼掃描：三個呼叫點各自只呼叫 cutvoice；`render_cut` 只在 cutvoice 出現（同一函式）。
        """
        want = {"roster.py": "cutvoice.stop_text", "watch.py": "cutvoice.watch_text",
                "briefline.py": "cutvoice.brief_text"}
        for name, call in want.items():
            lines = (SOURCE_DIR / name).read_text(encoding="utf-8").splitlines()
            self.assertEqual(sum(1 for ln in lines if call in ln), 1, name)
            self.assertEqual([ln for ln in lines if "render_cut(" in ln], [], name)
        tree = ast.parse((SOURCE_DIR / "cutvoice.py").read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "render_cut"]
        self.assertEqual(len(calls), 3)  # stop_text／watch_text／brief_text 各一處，同一函式
        self.assertTrue(callable(agentbrief.render_cut))

    def test_handoff_module_is_untouched_by_ack_hook(self) -> None:
        """`handoff.ack` 仍只寫 `.ack`；撤 park 掛在入口、不在 handoff.py（行數牆）。"""
        lines = (SOURCE_DIR / "handoff.py").read_text(encoding="utf-8").splitlines()
        self.assertEqual([ln for ln in lines if "ackhook" in ln], [])
        self.assertTrue(callable(handoff.ack))


if __name__ == "__main__":
    unittest.main()
