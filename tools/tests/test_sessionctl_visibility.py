"""sessionctl 控制態可見性（W3；TCS-Control AT-CTL-18／19／23～29、MU-CTL-12／13、REQ-CTL-11～16）。

受測模組：`tools/lib/sessionctl/rosterscope.py`、`controlfacts.py`、`briefline.py`、`statuscmd.py`、
`control.py`（`status_line`／`segment_text`）、`roster.py`（範圍）、
`tools/statusline_context_feed.py`、`tools/sessionctl.py`（status）。全用注入縫與 tmp 居所；
真子行程 smoke 只讀、不建排程、不開視窗。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS = _REPO_ROOT / "tools"
sys.path.insert(0, str(_TOOLS))
sys.path.insert(0, str(_TOOLS / "lib"))

import sandbox_scope  # noqa: E402

import statusline_context_feed as feed  # noqa: E402
from lib.sessionctl import (  # noqa: E402
    briefline,
    control,
    controlfacts,
    holder,
    qw_schema,
    roster,
    rosterscope,
)

SID = "814608d1-c56d-4b1f-9303-6b2dbff9b0d0"
OTHER = "a1b2c3d4-0000-1111-2222-333333333333"
SBX_SLUG = "C--Users-x-AppData-Local-Temp-" + sandbox_scope.SLUG_FRAGMENT + "vi8s6abz"
SBX_LITERAL = "AutoSDD-RV-sbx-"  # 僅供原始碼掃描斷言用；產品碼不得出現此字面


def _iso(minutes_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


class _Fence(unittest.TestCase):
    """tmp 居所：projects、trace、handoff 全圍到 tmp，不讀寫真實 `~/.claude`、`~/.autosdd`。"""

    def setUp(self) -> None:
        holder_dir = tempfile.TemporaryDirectory(prefix="ctl-w3-")
        self.addCleanup(holder_dir.cleanup)
        self.tmp = Path(holder_dir.name)
        self.projects = self.tmp / ".claude" / "projects"
        self.trace, self.hdir = self.tmp / "traces", self.tmp / "handoff"
        for folder in (self.projects, self.trace, self.hdir):
            folder.mkdir(parents=True)
        self.env_over = {"AUTOSDD_TRACE_DIR": str(self.trace),
                         "AUTOSDD_HANDOFF_DIR": str(self.hdir),
                         "CLAUDE_CONFIG_DIR": str(self.tmp / ".claude"),
                         "AUTOSDD_CONTEXT_FEED_DIR": str(self.tmp / "feed")}
        patch = mock.patch.dict(os.environ, self.env_over)
        patch.start()
        self.addCleanup(patch.stop)
        self.repo = rosterscope.repo_slug()

    def agent(self, slug: str, owner: str, aid: str, *, minutes_ago: float = 120,
              finished: bool | None = None) -> Path:
        folder = self.projects / slug / owner / "subagents"
        folder.mkdir(parents=True, exist_ok=True)
        meta = {"description": f"代理 {aid}", "model": "sonnet"}
        if finished is not None:
            meta["finished"] = finished
        (folder / f"agent-{aid}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
        rows = [{"type": "user", "timestamp": _iso(minutes_ago + 5)},
                {"type": "assistant", "timestamp": _iso(minutes_ago),
                 "message": {"id": "m", "usage": {"input_tokens": 1, "cache_read_input_tokens": 9,
                                                  "cache_creation_input_tokens": 0}}}]
        path = folder / f"agent-{aid}.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return path

    def main_transcript(self, slug: str, sid: str) -> Path:
        path = self.projects / slug / f"{sid}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"type": "user", "timestamp": _iso(1)}) + "\n", encoding="utf-8")
        return path

    def heartbeat(self, sid: str, *, pid: int | None = None, age_s: float = 5,
                  keepwarm_in_min: float = 40) -> None:
        folder = self.trace / "watch"
        folder.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        row = {"schema": "autosdd.watch/1", "pid": pid or os.getpid(),
               "started_at": (now - timedelta(minutes=3)).isoformat(),
               "heartbeat_at": (now - timedelta(seconds=age_s)).isoformat(),
               "keepwarm_at": (now + timedelta(minutes=keepwarm_in_min)).isoformat(),
               "stall_min": 20, "wall_min": 60, "ctx_max": 1}
        (folder / f"{sid}.json").write_text(json.dumps(row), encoding="utf-8")


class RosterScopeTest(_Fence):
    """tools/lib/sessionctl/rosterscope.py：名冊預設只本 repo、沙盒不污染（AT-CTL-23／24／26）。"""

    def build(self) -> None:
        self.agent(self.repo, OTHER, "real1")
        self.agent(SBX_SLUG, OTHER, "sbxwaiter")
        self.agent("D--some-other-project", OTHER, "foreign")

    def test_at_ctl_23_scope_dirs_default_is_repo_only(self) -> None:
        self.build()
        got = {p.parent.parent.name for _o, p in rosterscope.scope_dirs(self.projects, None)}
        self.assertEqual(got, {self.repo})
        everything = {p.parent.parent.name
                      for _o, p in rosterscope.scope_dirs(self.projects, None, True)}
        self.assertEqual(everything, {self.repo, SBX_SLUG, "D--some-other-project"})

    def test_at_ctl_23_sid_behaviour_is_unchanged(self) -> None:
        self.build()
        for flag in (False, True):  # 給 sid ⇒ 不看 all_projects，沙盒 slug 下的該 sid 照舊找得到
            got = {p.parent.parent.name for _o, p in rosterscope.scope_dirs(
                self.projects, OTHER, flag)}
            self.assertEqual(got, {self.repo, SBX_SLUG, "D--some-other-project"})

    def test_at_ctl_23_slug_directory_itself_is_accepted(self) -> None:
        self.build()
        got = list(rosterscope.scope_dirs(self.projects / self.repo, None))
        self.assertEqual([o for o, _p in got], [OTHER])

    def test_at_ctl_24_26_status_default_hides_sandbox_and_all_projects_marks_it(self) -> None:
        self.build()
        default = roster.snapshot(None, projects_dir=self.projects, env=self.env_over, full=False)
        self.assertEqual([a["id"] for a in default["agents"]], ["real1"])
        self.assertEqual(default["others"], 2)
        text = roster.render_snapshot(default)
        self.assertNotIn("sbxwaiter", text)
        self.assertIn("另有 2 支代理在其他專案／沙盒，--all-projects 查看", text)
        full = roster.snapshot(None, projects_dir=self.projects, env=self.env_over, full=False,
                               all_projects=True)
        self.assertEqual(sorted(a["id"] for a in full["agents"]), ["foreign", "real1", "sbxwaiter"])
        self.assertEqual(full["others"], 0)
        self.assertEqual({a["id"]: a["sandbox"] for a in full["agents"]},
                         {"real1": False, "sbxwaiter": True, "foreign": False})
        self.assertIn("[沙盒] sbxwaiter", roster.render_snapshot(full))
        # 差集一致：預設列的 + 另有 N ＝ --all-projects 列的
        self.assertEqual(len(default["agents"]) + default["others"], len(full["agents"]))

    def test_negative_control_real_repo_residue_is_still_listed(self) -> None:
        """MU-CTL-12 負控：本 repo 的真專案殘局預設仍列（範圍不是「全藏起來」）。"""
        self.agent(self.repo, OTHER, "residue1", minutes_ago=300)
        snap = roster.snapshot(None, projects_dir=self.projects, env=self.env_over, full=False)
        self.assertEqual([a["id"] for a in snap["agents"]], ["residue1"])
        self.assertEqual(snap["others"], 0)

    def test_is_sandbox_slug_uses_the_sandbox_scope_constant(self) -> None:
        self.assertTrue(rosterscope.is_sandbox_slug(SBX_SLUG))
        self.assertFalse(rosterscope.is_sandbox_slug(self.repo))
        self.assertFalse(rosterscope.is_sandbox_slug(None))

    def test_at_ctl_25_no_second_pattern_literal_in_product_code(self) -> None:
        """MU-CTL-13：四支產品檔不寫沙盒 slug 字面，只取 sandbox_scope 常數。"""
        for name in ("rosterscope.py", "controlfacts.py", "briefline.py", "statuscmd.py"):
            lines = (_TOOLS / "lib" / "sessionctl" / name).read_text(encoding="utf-8").splitlines()
            hits = [n for n, line in enumerate(lines, 1) if SBX_LITERAL in line]
            self.assertEqual(hits, [], name)
        src = (_TOOLS / "lib" / "sessionctl" / "rosterscope.py").read_text(encoding="utf-8")
        self.assertTrue(any("sandbox_scope.SLUG_FRAGMENT" in line for line in src.splitlines()))


class StatusLineTest(unittest.TestCase):
    """tools/lib/sessionctl/control.py::status_line：`control:` 一行逐字格式（AT-CTL-19）。"""

    def test_at_ctl_19_example_line_verbatim(self) -> None:
        state = control.classify(control.Facts(
            sid="814608d1-c56d-4b1f-9303-6b2dbff9b0d0", agents_running=2, supervision="valid",
            supervision_source="heartbeat", supervision_pid=18340, supervision_hb_age=40,
            next_wake="2026-11-22T15:30:00+08:00", next_wake_carrier="keepwarm", sealed="none"))
        self.assertEqual(
            control.status_line(state),
            "control: sid=814608d1 agents=2(running) watch=valid(pid 18340, hb 40s) "
            "next_wake=15:30(keepwarm) sealed=none handed_over=no pending_switch=no park=none")

    def test_at_ctl_19_unmeasured_fields_print_question_mark(self) -> None:
        line = control.status_line(control.classify(control.Facts(sid="abc")))
        self.assertEqual(line, "control: sid=abc agents=0(running) watch=none next_wake=? "
                               "sealed=none handed_over=no pending_switch=no park=none")

    def test_at_ctl_19_other_cells(self) -> None:
        state = control.classify(control.Facts(
            sid="s", agents_running=1, agents_quiet=2, agents_cut=({"id": "a", "kind": "residue"},),
            supervision="stuck", supervision_source="payload", sealed="effective",
            handed_over="p.md", pending_switch={"reason": "hard", "since": "t"},
            park={"status": "armed"}, unacked_pkg="pkg_1.md"))
        line = control.status_line(state)
        for part in ("agents=1(running)+2(quiet)+1(cut)", "watch=stuck(source payload)",
                     "sealed=effective", "handed_over=yes", "pending_switch=yes(hard)",
                     "park=armed", "unacked_pkg=pkg_1.md"):
            self.assertIn(part, line)


class SegmentTextTest(unittest.TestCase):
    """tools/lib/sessionctl/control.py::segment_text 與 `ui_line`（AT-CTL-28）。"""

    def seg(self, **facts) -> str:
        return control.segment_text(control.classify(control.Facts(sid="s", **facts)))

    def test_at_ctl_28_table(self) -> None:
        cut = ({"id": "a", "kind": "usage_limit"},)
        table = [
            ({}, ""),
            ({"agents_running": 2, "supervision": "valid"}, "ctl: 2 agents watch ok"),
            ({"agents_running": 1, "supervision": "valid"}, "ctl: 1 agent watch ok"),
            ({"agents_running": 2}, "ctl: 2 agents NO WATCH"),
            ({"agents_running": 2, "supervision": "stuck"}, "ctl: 2 agents NO WATCH"),
            ({"agents_quiet": 1}, "ctl: 1 agent NO WATCH"),
            ({"agents_cut": cut}, "ctl: 1 agent CUT"),
            ({"sealed": "effective"}, "ctl: sealed"),
            ({"sealed": "invalidated"}, ""),
            ({"sealed": "none"}, ""),
            ({"handed_over": "p.md", "agents_running": 3}, "ctl: HANDED-OVER"),
            ({"pending_switch": {"reason": "hard", "since": "t"}}, "ctl: switch pending"),
            ({"agents_running": 2, "supervision": "valid", "sealed": "effective"},
             "ctl: 2 agents watch ok; sealed"),
        ]
        for facts, want in table:
            with self.subTest(facts=facts):
                got = self.seg(**facts)
                self.assertEqual(got, want)
                self.assertTrue(got.isascii())

    def test_ui_line_is_byte_identical_without_a_segment(self) -> None:
        payload = {"session_id": "s", "model": {"display_name": "Opus"},
                   "context_window": {"used_percentage": 12.0, "context_window_size": 1000000,
                                      "current_usage": {"input_tokens": 1000}}}
        base = feed.ui_line(payload)
        self.assertEqual(feed.ui_line(payload, control=lambda _p: ""), base)
        self.assertEqual(feed.ui_line(payload, control=lambda _p: "ctl: sealed"),
                         base + " | ctl: sealed")
        none_payload = {"session_id": "s", "context_window": {}}
        self.assertEqual(feed.ui_line(none_payload, control=lambda _p: "ctl: x"),
                         feed.ui_line(none_payload) + " | ctl: x")

    def test_ctl_segment_without_session_id_is_empty(self) -> None:
        self.assertEqual(feed.ctl_segment({}), "")
        self.assertEqual(feed.ctl_segment({"session_id": "  "}), "")


class SegmentCacheTest(_Fence):
    """tools/lib/sessionctl/controlfacts.py::segment：快取、時限、例外、缺逐字稿（AT-CTL-28）。"""

    def test_cache_hit_within_ten_seconds_and_refresh_after(self) -> None:
        calls: list[int] = []

        def compute(_sid: str, _payload) -> str:
            calls.append(1)
            return f"ctl: call {len(calls)}"
        now = time.time()
        self.assertEqual(controlfacts.segment(SID, None, now=now, compute=compute), "ctl: call 1")
        again = controlfacts.segment(SID, None, now=now + 9, compute=compute)
        self.assertEqual(again, "ctl: call 1")
        self.assertEqual(len(calls), 1)
        later = controlfacts.segment(SID, None, now=now + 11, compute=compute)
        self.assertEqual(later, "ctl: call 2")

    def test_empty_result_is_cached_too(self) -> None:
        calls: list[int] = []
        now = time.time()

        def compute(_s: str, _p) -> str:
            calls.append(1)
            return ""
        self.assertEqual(controlfacts.segment(SID, None, now=now, compute=compute), "")
        self.assertEqual(controlfacts.segment(SID, None, now=now + 1, compute=compute), "")
        self.assertEqual(len(calls), 1)

    def test_exception_and_timeout_return_empty_and_are_not_cached(self) -> None:
        def boom(_s: str, _p) -> str:
            raise RuntimeError("x")

        def slow(_s: str, _p) -> str:
            time.sleep(0.6)
            return "ctl: late"
        self.assertEqual(controlfacts.segment(SID, None, compute=boom), "")
        started = time.monotonic()
        self.assertEqual(controlfacts.segment(SID, None, compute=slow, timeout=0.05), "")
        self.assertLess(time.monotonic() - started, 0.5)
        # 例外／逾時都沒有寫快取：換一個正常 compute 立刻拿到值
        self.assertEqual(controlfacts.segment(SID, None, compute=lambda _s, _p: "ctl: sealed"),
                         "ctl: sealed")

    def test_at_ctl_29_missing_session_id_or_bad_sid_is_empty(self) -> None:
        for bad in (None, "", "  ", "../escape", 5):
            self.assertEqual(controlfacts.segment(bad, None, compute=lambda _s, _p: "ctl: x"), "")

    def test_at_ctl_29_missing_transcript_path_degrades_without_error(self) -> None:
        seen: list[dict] = []

        def compute(_s: str, payload) -> str:
            seen.append(dict(payload))
            return "ctl: sealed"
        self.assertEqual(controlfacts.segment(SID, None, compute=compute), "ctl: sealed")
        self.assertEqual(seen, [{"session_id": SID}])
        real = controlfacts.segment(OTHER, None)  # 真取數：沒有任何東西 ⇒ 空字串，不拋
        self.assertEqual(real, "")


class ControlFactsTest(_Fence):
    """tools/lib/sessionctl/controlfacts.py::control_state：憑證取自心跳／holder（AT-CTL-18）。"""

    def payload(self, **extra) -> dict:
        tr = self.main_transcript(self.repo, SID)
        return {"session_id": SID, "transcript_path": str(tr), **extra}

    def test_at_ctl_18_credentials_come_from_heartbeat_not_from_words(self) -> None:
        self.agent(self.repo, SID, "live1", minutes_ago=1, finished=False)
        pkg = self.hdir / f"{SID}_20261122T000000Z.md"
        pkg.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n\n"
                       "主控層：已掛 watch，監督中，下次叫醒 15:30。\n", encoding="utf-8")
        state = controlfacts.control_state(self.payload(), SID, self.env_over)
        self.assertEqual((state.agents_running, state.supervision), (1, "none"))
        self.assertIsNone(state.supervision_pid)
        self.heartbeat(SID, age_s=40)
        state = controlfacts.control_state(self.payload(), SID, self.env_over)
        self.assertEqual((state.supervision, state.supervision_source, state.supervision_pid),
                         ("valid", "heartbeat", os.getpid()))
        self.assertGreaterEqual(state.supervision_hb_age, 40)
        self.assertEqual(state.next_wake_carrier, "watch")

    def test_dead_pid_and_stale_heartbeat_are_not_valid(self) -> None:
        self.agent(self.repo, SID, "live1", minutes_ago=1, finished=False)
        self.heartbeat(SID, pid=2_147_483_000)
        state = controlfacts.control_state(self.payload(), SID, self.env_over)
        self.assertNotEqual(state.supervision, "valid")
        self.heartbeat(SID, age_s=900)
        self.assertNotEqual(controlfacts.control_state(
            self.payload(), SID, self.env_over).supervision, "valid")

    def test_payload_background_tasks_is_the_primary_proof(self) -> None:
        watch = {"id": "w", "type": "shell", "status": "running",
                 "command": "python tools/sessionctl.py watch --sid x"}
        agent = {"id": "a1", "type": "subagent", "status": "running"}
        state = controlfacts.control_state(
            self.payload(background_tasks=[agent, watch]), SID, self.env_over)
        self.assertEqual((state.agents_running, state.supervision, state.supervision_source),
                         (1, "valid", "payload"))
        bare = controlfacts.control_state(
            self.payload(background_tasks=[agent]), SID, self.env_over)
        self.assertEqual((bare.agents_running, bare.supervision), (1, "none"))

    def test_next_wake_takes_the_earliest_live_carrier(self) -> None:
        self.heartbeat(SID, keepwarm_in_min=40)
        wake = datetime.now(UTC) + timedelta(minutes=10)
        with mock.patch.object(holder, "acquire", wraps=holder.acquire):
            self.assertTrue(holder.acquire(SID, os.getpid(), extra=qw_schema.holder_extra(
                wake.timestamp(), "chain", "reset")))
        state = controlfacts.control_state(self.payload(), SID, self.env_over)
        self.assertEqual(state.next_wake_carrier, "keepwarm")
        self.assertEqual(qw_schema.parse_epoch(state.next_wake), qw_schema.parse_epoch(
            qw_schema.iso(wake.timestamp())))

    def test_everything_missing_is_conservative_not_guessed(self) -> None:
        state = controlfacts.control_state({}, "no-such-session", self.env_over)
        self.assertEqual((state.agents_running, state.supervision, state.next_wake, state.sealed,
                          state.handed_over, state.pending_switch, state.park, state.wall),
                         (0, "none", None, "none", None, None, None, False))


class BrieflineTest(_Fence):
    """tools/lib/sessionctl/briefline.py：SessionStart 殘局公告，沙盒不公告（AT-CTL-27）。"""

    def line(self, sid: str | None = SID) -> str:
        return briefline.orphan_line(sid, self.env_over)

    def test_at_ctl_27_repo_orphan_is_announced(self) -> None:
        self.agent(self.repo, OTHER, "orphan1", minutes_ago=300)
        text = self.line()
        self.assertTrue(text.startswith(" "))
        self.assertIn("1 支背景代理未收尾", text)
        self.assertIn("python tools/sessionctl.py status", text)
        self.assertIn("不假設 claude -r 能接回", text)

    def test_at_ctl_27_sandbox_only_orphan_is_silent(self) -> None:
        self.agent(SBX_SLUG, OTHER, "rv_waiter", minutes_ago=300)
        self.assertEqual(self.line(), "")

    def test_at_ctl_27_nothing_is_empty_and_own_session_is_not_orphan(self) -> None:
        self.assertEqual(self.line(), "")
        self.agent(self.repo, SID, "mine", minutes_ago=300)
        self.assertEqual(self.line(), "")  # 擁有者就是本 session：不是上一個 session 的殘局
        self.agent(self.repo, OTHER, "running_elsewhere", minutes_ago=1)
        self.assertEqual(self.line(), "")  # 別的視窗正在跑的不是殘局

    def test_expired_orphans_are_not_announced(self) -> None:
        self.agent(self.repo, OTHER, "ancient", minutes_ago=60 * 30)
        self.assertEqual(self.line(), "")

    def test_cut_agents_are_counted_when_the_roster_carries_the_kind(self) -> None:
        rows = [{"state": "quiet", "owner_sid": OTHER, "kind": "usage_limit"},
                {"state": "residue", "owner_sid": OTHER}]
        text = briefline.orphan_line(SID, {}, agents_fn=lambda _e: rows)
        self.assertIn("2 支背景代理未收尾", text)
        self.assertIn("其中 1 支被額度切斷", text)

    def test_exception_is_empty(self) -> None:
        def boom(_env):
            raise RuntimeError("x")
        self.assertEqual(briefline.orphan_line(SID, {}, agents_fn=boom), "")

    def test_join_and_lines_compose(self) -> None:
        self.assertEqual(briefline.join(["", " a", "", " b"]), " a b")


class RealProcessSmokeTest(_Fence):
    """tools/sessionctl.py status 與 tools/statusline_context_feed.py 真子行程（tmp 居所）。"""

    def run_py(self, script: str, *args: str, stdin: str | None = None,
               extra_env: dict | None = None) -> subprocess.CompletedProcess:
        env = {**os.environ, **self.env_over, "PYTHONUTF8": "1", **(extra_env or {})}
        env.pop("CLAUDE_CODE_SESSION_ID", None)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, str(_TOOLS / script), *args], input=stdin,
                              capture_output=True, text=True, encoding="utf-8", env=env,
                              timeout=120, check=False)

    def test_status_default_lists_repo_only_and_all_projects_lists_both(self) -> None:
        self.agent(self.repo, OTHER, "real1")
        self.agent(SBX_SLUG, OTHER, "sbxwaiter")
        sid_env = {"CLAUDE_CODE_SESSION_ID": SID}
        default = self.run_py("sessionctl.py", "status", extra_env=sid_env)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertIn("real1", default.stdout)
        self.assertNotIn("sbxwaiter", default.stdout)
        self.assertIn("另有 1 支代理在其他專案／沙盒，--all-projects 查看", default.stdout)
        first = default.stdout.splitlines()[0]
        self.assertTrue(first.startswith("control: sid=814608d1"), first)  # 控制行在名冊之前
        full = self.run_py("sessionctl.py", "status", "--all-projects", extra_env=sid_env)
        self.assertEqual(full.returncode, 0, full.stderr)
        self.assertIn("real1", full.stdout)
        self.assertIn("[沙盒] sbxwaiter", full.stdout)

    def test_status_json_carries_the_control_object(self) -> None:
        self.agent(self.repo, SID, "mine", minutes_ago=1, finished=False)
        out = self.run_py("sessionctl.py", "status", "--json", "--session", SID)
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual(data["control"]["sid"], SID)
        self.assertEqual(data["control"]["agents_running"], 1)
        self.assertIn("others", data)

    def test_status_without_a_session_id_says_it_cannot_tell(self) -> None:
        out = self.run_py("sessionctl.py", "status")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("control: 無法判斷", out.stdout)

    def test_statusline_prints_no_watch_then_watch_ok_from_a_real_heartbeat(self) -> None:
        tr = self.main_transcript(self.repo, SID)
        self.agent(self.repo, SID, "live1", minutes_ago=1, finished=False)
        payload = {"session_id": SID, "transcript_path": str(tr), "model": {"display_name": "Opus"},
                   "context_window": {"used_percentage": 11, "context_window_size": 1000000,
                                      "current_usage": {"input_tokens": 5}}}
        out = self.run_py("statusline_context_feed.py", stdin=json.dumps(payload))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("ctl: 1 agent NO WATCH", out.stdout)
        self.assertTrue(out.stdout.startswith("ctx 11%"), out.stdout)
        # 另一個 session：有真心跳（pid 活著、新鮮）⇒ watch ok
        tr2 = self.main_transcript(self.repo, OTHER)
        self.agent(self.repo, OTHER, "live2", minutes_ago=1, finished=False)
        self.heartbeat(OTHER)
        payload.update(session_id=OTHER, transcript_path=str(tr2))
        out2 = self.run_py("statusline_context_feed.py", stdin=json.dumps(payload))
        self.assertIn("ctl: 1 agent watch ok", out2.stdout)

    def test_statusline_without_any_state_is_unchanged(self) -> None:
        payload = {"session_id": "fresh-session", "model": {"display_name": "Opus"},
                   "context_window": {"used_percentage": 11, "context_window_size": 1000000,
                                      "current_usage": {"input_tokens": 5}}}
        out = self.run_py("statusline_context_feed.py", stdin=json.dumps(payload))
        self.assertEqual(out.stdout.strip(), feed.ui_line(payload))
        self.assertNotIn("ctl:", out.stdout)


if __name__ == "__main__":
    unittest.main()
