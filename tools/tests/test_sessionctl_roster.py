"""sessionctl 名冊／停止／結局（TCS-SessionCtl AT-SC-66～73、77～80；ADR-XPLAT-004 §2.13.6）。

全用注入縫：假 projects 目錄、假 runner、假 env；不讀真實 `~/.claude`、不起真排程、不砍真行程。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS = _REPO_ROOT / "tools"
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import endurance_env  # noqa: E402
import relay_machine  # noqa: E402
import resume_cost  # noqa: E402
import session_brief  # noqa: E402

import lib.sessionctl as sessionctl_pkg  # noqa: E402
from lib.sessionctl import procstop, roster  # noqa: E402

NOW = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
SID = "d4ed2654-9181-4df1-a6e6-2d712956e23b"
USE = {"input_tokens": 10, "cache_read_input_tokens": 90, "cache_creation_input_tokens": 400,
       "output_tokens": 5}


def _tmp(case: unittest.TestCase) -> Path:
    holder = tempfile.TemporaryDirectory(prefix="sc-roster-")
    case.addCleanup(holder.cleanup)
    return Path(holder.name)


def _line(ts: datetime, usage: dict | None = None, kind: str = "assistant", mid: str = "m") -> str:
    rec: dict = {"type": kind, "timestamp": ts.isoformat()}
    if usage is not None:
        rec["message"] = {"id": mid, "usage": usage}
    return json.dumps(rec)


def make_agent(root: Path, sid: str, aid: str, *, minutes_ago: float, finished=None,
               usage: dict | None = USE, description: str = "審查鏡",
               model: str = "sonnet") -> Path:
    """`<root>/slug/<sid>/subagents/agent-<aid>.{jsonl,meta.json}`；`finished=None`＝無該鍵。"""
    folder = root / "slug" / sid / "subagents"
    folder.mkdir(parents=True, exist_ok=True)
    meta = {"description": description, "model": model}
    if finished is not None:
        meta["finished"] = finished
    (folder / f"agent-{aid}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    last = NOW - timedelta(minutes=minutes_ago)
    lines = [_line(last - timedelta(minutes=5), kind="user"), _line(last, usage, mid="m1")]
    path = folder / f"agent-{aid}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def make_owner(root: Path, sid: str, minutes_ago: float) -> None:
    folder = root / "slug"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{sid}.jsonl").write_text(
        _line(NOW - timedelta(minutes=minutes_ago), USE) + "\n", encoding="utf-8")


class _Res:
    def __init__(self, rc: int = 0, out: str = "") -> None:
        self.returncode, self.stdout, self.stderr = rc, out, ""


def _win_row(pid: int, cmd: str, created: datetime, name: str = "claude.exe") -> dict:
    return {"ProcessId": pid, "ParentProcessId": 1, "Name": name, "CommandLine": cmd,
            "Created": created.astimezone(UTC).isoformat().replace("+00:00", "Z")}


def _ps_text(rows: list[dict]) -> str:
    """同一批 rows 的 POSIX `ps -axo pid=,ppid=,lstart=,command=` 形態（讓測試與平台無關）。"""
    out = []
    for row in rows:
        local = datetime.fromisoformat(row["Created"].replace("Z", "+00:00")).astimezone()
        out.append(f"{row['ProcessId']} {row['ParentProcessId']} "
                   f"{local.strftime('%a %b %d %H:%M:%S %Y')} {row['CommandLine']}")
    return "\n".join(out) + "\n"


def _runner(rows: list[dict] | None, calls: list, list_rc: int = 0, kill_rc: int = 0):
    def run(argv):
        calls.append(list(argv))
        if argv[0] == "powershell.exe":
            return _Res(list_rc, json.dumps(rows or []))
        if argv[0] == "ps":
            return _Res(list_rc, _ps_text(rows or []))
        return _Res(kill_rc)
    return run


def _snap(case: unittest.TestCase, root: Path, **kw) -> dict:
    env = {"AUTOSDD_HANDOFF_DIR": str(_tmp(case))}
    with unittest.mock.patch.object(roster, "_schedules", return_value=[]), \
            unittest.mock.patch.object(roster, "_stale_sentinels", return_value=[]):
        return roster.snapshot(SID, projects_dir=root, now=NOW, env=env, **kw)


class RosterStateTest(unittest.TestCase):
    """三態判準：只列 `finished` 不是 true 者（缺鍵與 false 同義，V-S4）。"""

    def test_at_sc_66_recent_unfinished_agent_is_running(self) -> None:
        """AT-SC-66：meta `finished:false`、最後記錄 2 分鐘前 ⇒ 執行中；並帶上下文與累計。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=2, finished=False)
        agent = _snap(self, root)["agents"][0]
        self.assertEqual((agent["state"], agent["id"], agent["owner_sid"]), ("running", "a1", SID))
        self.assertEqual(agent["ctx_tokens"], 500)  # input＋cache_read＋cache_creation
        self.assertEqual(agent["total_tokens"], 505)  # 另含 output
        self.assertEqual((agent["description"], agent["model"]), ("審查鏡", "sonnet"))

    def test_missing_finished_key_means_unfinished(self) -> None:
        """V-S4：session 被砍時 meta 沒有 `finished` 鍵 ⇒ 與 false 同義，不得當成已結束。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=1, finished=None)
        self.assertEqual([a["state"] for a in _snap(self, root)["agents"]], ["running"])

    def test_at_sc_67_old_unfinished_agent_is_quiet(self) -> None:
        """AT-SC-67：同上、40 分鐘前 ⇒ 安靜（不是執行中）。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=40, finished=False)
        self.assertEqual([a["state"] for a in _snap(self, root)["agents"]], ["quiet"])

    def test_quiet_threshold_follows_roster_quiet_minutes(self) -> None:
        """門檻走 `AUTOSDD_ROSTER_QUIET_MINUTES`（env 注入）：5 分鐘門檻下 7 分鐘前＝安靜。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=7, finished=False)
        env = {"AUTOSDD_HANDOFF_DIR": str(_tmp(self)), "AUTOSDD_ROSTER_QUIET_MINUTES": "5"}
        snap = roster.snapshot(SID, projects_dir=root, now=NOW, env=env)
        self.assertEqual([a["state"] for a in snap["agents"]], ["quiet"])

    def test_at_sc_68_owner_gone_and_no_process_is_residue_not_burning(self) -> None:
        """AT-SC-68：擁有者主逐字稿閒置 > 巡邏間隔、行程列舉無含 sid 者 ⇒ 殘局，說明非燒額度中。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=40, finished=False)
        make_owner(root, SID, minutes_ago=90)
        snap = _snap(self, root, runner=_runner([], []))
        self.assertEqual([a["state"] for a in snap["agents"]], ["residue"])
        self.assertIn("非燒額度中", roster.render_snapshot(snap))

    def test_residue_needs_the_process_listing_and_a_dead_owner(self) -> None:
        """殘局的兩個反例：①有 claude 行程命令列含該 sid（擁有者還活著）⇒ 安靜；②沒給 runner
        （純讀檔、不列舉行程）⇒ 無從證明擁有者已死，一律安靜，不得誤標殘局。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=40, finished=False)
        make_owner(root, SID, minutes_ago=90)
        alive = [_win_row(77, f"claude.exe -r {SID}", NOW)]
        states = [a["state"] for a in _snap(self, root, runner=_runner(alive, []))["agents"]]
        self.assertEqual(states, ["quiet"], "擁有者行程還在 ⇒ 不是殘局")
        self.assertEqual([a["state"] for a in _snap(self, root)["agents"]], ["quiet"])

    def test_at_sc_69_finished_agent_is_not_listed(self) -> None:
        """AT-SC-69：`finished:true` ⇒ 不列、`running()` 也不回。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=1, finished=True)
        self.assertEqual(_snap(self, root)["agents"], [])
        self.assertEqual(roster.running(SID, projects_dir=root, now=NOW), [])

    def test_running_is_pure_file_read_and_filters_state(self) -> None:
        """`running()`（hook 會呼叫）只回 running，且全程不呼叫任何 runner／排程查詢。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=1)
        make_agent(root, SID, "a2", minutes_ago=60)
        with unittest.mock.patch.object(procstop, "list_processes",
                                        side_effect=AssertionError("hook 內不得列舉行程")):
            got = roster.running(SID, projects_dir=root, now=NOW)
        self.assertEqual([a["id"] for a in got], ["a1"])

    def test_agent_context_reads_last_usage_even_for_a_finished_agent(self) -> None:
        """`agent_context`：續已結束的代理一樣整份重讀（E1），所以不看 finished；壞 id 回 None。"""
        root = _tmp(self)
        make_agent(root, SID, "a1", minutes_ago=300, finished=True,
                   usage={"input_tokens": 1, "cache_read_input_tokens": 2,
                          "cache_creation_input_tokens": 3})
        self.assertEqual(roster.agent_context(SID, "a1", projects_dir=root), 6)
        for bad in ("../x", "", "a b"):
            self.assertIsNone(roster.agent_context(SID, bad, projects_dir=root))
        self.assertIsNone(roster.agent_context(SID, "nope", projects_dir=root))

    def test_empty_roster_renders_an_explicit_zero(self) -> None:
        """空名冊印「量到的零」而不是整段消失（status 的『沒有』必須與『沒查』分得開）。"""
        text = roster.render_snapshot(_snap(self, _tmp(self)))
        self.assertIn("背景代理：無（量到的零）", text)
        self.assertIn("未 ack 交接包：無", text)

    def test_unacked_handoffs_are_listed_and_acked_ones_are_not(self) -> None:
        """名冊的未 ack 交接包欄：用 `handoff.ack` 真的寫出的 `<stem>.ack` sidecar（不是手造的
        `<檔名>.md.ack`）；非交接包檔名的 `*.md` 不列。"""
        from lib.sessionctl import handoff  # noqa: PLC0415 — 與 roster 同一個真模組

        folder = _tmp(self)
        first = folder / f"{SID}_20261114T100000Z.md"
        second = folder / f"{SID}_20261114T110000Z.md"
        for pkg in (first, second, folder / "plan.md"):
            pkg.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} -->\n", encoding="utf-8")
        self.assertEqual(handoff.ack(second), 0)
        self.assertEqual(roster._handoffs({"AUTOSDD_HANDOFF_DIR": str(folder)}), [str(first)])


class StopWindowTest(unittest.TestCase):
    """`stop --window`：先驗 pid 身分（命令列含 sid ∧ 建立時刻吻合痕跡）再砍，驗不到不砍。"""

    CMD = f'claude.exe -p --model sonnet -r {SID} "按交接包繼續"'

    def _stop(self, rows, anchors, **kw):
        calls: list = []
        disarmed: list = []
        traces: list = []
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = roster.stop_window(
                SID, runner=_runner(rows, calls, **kw), platform_name="win32", now=NOW,
                anchors=anchors, disarm=lambda sid: disarmed.append(sid) or 0,
                trace=traces.append)
        kills = [c for c in calls if c[0] != "powershell.exe"]
        return rc, kills, disarmed, traces, err.getvalue()

    def test_at_sc_70_verified_window_is_killed_with_absolute_taskkill(self) -> None:
        """AT-SC-70：命令列含 sid、建立時刻吻合 ⇒ `taskkill /T /F /PID`（絕對路徑）被呼叫、
        哨兵解除、痕跡 `window_stopped`（含 pid 與驗證依據）。"""
        rows = [_win_row(4321, self.CMD, NOW)]
        root = _tmp(self)
        with unittest.mock.patch.dict(os.environ, {"SystemRoot": str(root)}):
            rc, kills, disarmed, traces, _err = self._stop(rows, [NOW.timestamp() + 30])
        self.assertEqual(rc, 0)
        self.assertEqual(len(kills), 1, kills)
        self.assertEqual(kills[0][0], str(root / "System32" / "taskkill.exe"))
        self.assertEqual(kills[0][1:], ["/" + f for f in ("T", "F", "PID")] + ["4321"])  # 旗標
        self.assertEqual(disarmed, [SID])
        self.assertEqual((traces[0]["event"], traces[0]["pids"]), ("window_stopped", [4321]))
        self.assertIn("cmdline-sid", traces[0]["basis"])
        self.assertEqual(traces[0]["at"], "2026-11-14T12:00:00+00:00")  # 帶 offset（鐵律三）

    def test_at_sc_71_pid_reuse_created_time_mismatch_is_not_killed(self) -> None:
        """AT-SC-71：命令列含 sid 但建立時刻與痕跡差一小時（pid 重用）⇒ 不砍、rc≠0、列出原因。"""
        rc, kills, disarmed, traces, err = self._stop(
            [_win_row(4321, self.CMD, NOW)], [NOW.timestamp() + 3600])
        self.assertNotEqual(rc, 0)
        self.assertEqual((kills, disarmed, traces), ([], [], []))
        self.assertIn("pid 4321", err)
        self.assertIn("不符", err)

    def test_at_sc_72_created_time_ok_but_no_sid_is_not_killed(self) -> None:
        """AT-SC-72：建立時刻吻合、命令列不含 sid（別人的 claude）⇒ 不砍。"""
        rc, kills, _d, _t, err = self._stop(
            [_win_row(555, 'claude.exe --model haiku "別的視窗"', NOW)], [(NOW.timestamp(), 555)])
        self.assertEqual(kills, [])
        self.assertNotEqual(rc, 0)
        self.assertIn("不含 sid", err)

    def test_at_sc_73_listing_failure_says_cannot_measure_and_does_not_kill(self) -> None:
        """AT-SC-73：列舉行程 rc≠0 ⇒ 不砍、明說「量不到」（量不到≠沒有）。"""
        rc, kills, disarmed, _t, err = self._stop([_win_row(1, self.CMD, NOW)],
                                                  [NOW.timestamp()], list_rc=1)
        self.assertEqual((rc, kills, disarmed), (1, [], []))
        self.assertIn("量不到", err)

    def test_no_trace_anchor_means_identity_unverifiable_so_no_kill(self) -> None:
        """痕跡沒有該 sid 的 spawn 時刻 ⇒ 驗不到身分 ⇒ 不砍（驗不到就不砍）。"""
        rc, kills, _d, _t, err = self._stop([_win_row(9, self.CMD, NOW)], [])
        self.assertEqual((kills, rc != 0), ([], True))
        self.assertIn("沒有 spawn 時刻記錄", err)

    def test_kill_failure_is_rc_one_and_said_not_stopped(self) -> None:
        """身分驗過但 taskkill rc≠0 ⇒ stop_window rc 1（「已停」不得是假的）；痕跡記下 kill_rc。"""
        rc, kills, _d, traces, _e = self._stop(
            [_win_row(4321, self.CMD, NOW)], [NOW.timestamp()], kill_rc=1)
        self.assertEqual((rc, len(kills), traces[0]["kill_rc"]), (1, 1, [1]))

    def test_a_non_claude_process_with_the_sid_in_its_cmdline_is_never_killed(self) -> None:
        """POSIX 列全部行程：命令列含 sid、建立時刻吻合的 tail／編輯器不是 claude ⇒ 不砍。"""
        rows = [_win_row(77, f"tail -f {SID}.jsonl", NOW, name="tail")]
        rc, kills, disarmed, traces, _e = self._stop(rows, [NOW.timestamp()])
        self.assertEqual((rc, kills, disarmed, traces), (0, [], [], []))
        ok, notes = procstop.verify(procstop._parse_windows(json.dumps(rows)), SID,
                                    [NOW.timestamp()])
        self.assertEqual((ok, notes), ([], []))

    def test_trace_anchors_ignore_other_sessions_spawn_records(self) -> None:
        """別的 sid 的 `session_switch_spawned` 不得變成本 sid 的錨點（削弱建立時刻判準）。"""
        tmp, traces = _tmp(self), _tmp(self)
        other = "11111111-2222-3333-4444-555555555555"
        (traces / "x.jsonl").write_text(
            json.dumps({"event": "session_switch_spawned", "session": other,
                        "at": (NOW + timedelta(hours=2)).isoformat()}) + "\n"
            + json.dumps({"event": "session_switch_spawned", "session": SID,
                          "at": NOW.isoformat()}) + "\n", encoding="utf-8")
        self.assertEqual(procstop.trace_anchors(SID, traces, tmp), [NOW.timestamp()])

    def test_nothing_running_is_rc_zero(self) -> None:
        """沒有任何候選行程 ⇒ rc 0（沒有東西要停不是失敗）。"""
        self.assertEqual(self._stop([], [NOW.timestamp()])[:2], (0, []))

    def test_bad_session_id_is_refused_before_any_external_call(self) -> None:
        """sid 含空白／分號等 ⇒ 直接拒絕（rc 2），連行程列舉都不呼叫。"""
        calls: list = []
        with contextlib.redirect_stderr(io.StringIO()):
            rc = roster.stop_window("x; rm -rf /", runner=_runner([], calls), platform_name="win32")
        self.assertEqual((rc, calls), (2, []))

    def test_posix_kills_descendants_leaf_first_with_plain_kill(self) -> None:
        """POSIX：沒有 /T，逐個 `kill -KILL`，先葉後根（`ps` 列出 ppid 才走得到樹）。"""
        calls: list = []
        stamp = datetime.now().astimezone()
        lstart = stamp.strftime("%a %b %d %H:%M:%S %Y")
        out = (f"  100     1 {lstart} claude -p -r {SID} go\n"
               f"  101   100 {lstart} node child\n"
               f"  102   101 {lstart} node grandchild\n"
               f"  200     1 {lstart} claude -r other-session-0000\n")

        def run(argv):
            calls.append(list(argv))
            return _Res(0, out if argv[0] == "ps" else "")

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = roster.stop_window(SID, runner=run, platform_name="linux", now=NOW,
                                    anchors=[stamp.replace(microsecond=0).timestamp()],
                                    disarm=lambda sid: 0, trace=lambda rec: None)
        killed = [c[2] for c in calls if c[0] == "kill"]
        self.assertEqual((rc, killed), (0, ["102", "101", "100"]))

    def test_all_unattended_stops_only_print_mode_windows(self) -> None:
        """`--all-unattended`：只動 `claude -p` 且命令列含 sid 者；互動視窗（無 -p）一律不碰。"""
        other = "11111111-2222-3333-4444-555555555555"
        rows = [_win_row(10, self.CMD, NOW),
                _win_row(11, f"claude.exe -r {other}", NOW)]
        calls: list = []
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = procstop.stop_all_unattended(
                runner=_runner(rows, calls), platform_name="win32",
                anchors=[NOW.timestamp()], disarm=lambda sid: 0, trace=lambda rec: None)
        kills = [c[-1] for c in calls if c[0] != "powershell.exe"]
        self.assertEqual((rc, kills), (0, ["10"]))

    def test_sec1_all_unattended_spares_an_interactive_window_of_the_same_sid(self) -> None:
        """SEC-1（雙駕駛）：同 sid 一個互動（pid 11）、一個無人（pid 10），建立時刻都貼近錨點，
        痕跡也替互動那個記了 pid ⇒ `--all-unattended` 只砍無人那個。"""
        interactive = f"claude.exe -r {SID}"
        rows = [_win_row(10, self.CMD, NOW), _win_row(11, interactive, NOW)]
        calls: list = []
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = procstop.stop_all_unattended(
                runner=_runner(rows, calls), platform_name="win32",
                anchors=[NOW.timestamp(), (NOW.timestamp(), 11)],
                disarm=lambda sid: 0, trace=lambda rec: None)
        self.assertEqual((rc, [c[-1] for c in calls if c[0] != "powershell.exe"]), (0, ["10"]))
        ok, _notes = procstop.verify(procstop._parse_windows(json.dumps(rows)), SID,
                                     [(NOW.timestamp(), 11)])  # 對照：不限 print 時互動那個會中
        self.assertEqual([p["pid"] for p in ok], [11])

    def test_sec2_pid_must_match_the_trace_pid_for_an_interactive_window(self) -> None:
        """SEC-2：命令列含舊 sid、建立時刻貼近、但 pid 與痕跡記的不同（接手的新互動視窗）⇒ 不砍；
        pid 相符才砍；痕跡沒有 pid（只有時刻）⇒ 互動視窗驗不到 ⇒ 不砍。"""
        rows = [_win_row(4242, f"claude.exe -r {SID}", NOW)]
        for anchors, killed in (([(NOW.timestamp(), 9999)], []),
                                ([NOW.timestamp()], []),
                                ([(NOW.timestamp(), 4242)], ["4242"])):
            rc, kills, _d, _t, err = self._stop(rows, anchors)
            self.assertEqual([k[-1] for k in kills], killed, anchors)
            if not killed:
                self.assertNotEqual(rc, 0)
                self.assertIn("不符", err + "沒有 spawn 時刻記錄")

    def test_sec2_a_print_window_with_a_mismatched_trace_pid_is_not_killed(self) -> None:
        """SEC-2：痕跡帶 pid 時，print 模式也要 pid 相符（無 pid 的續跑日誌錨點才放行 print）。"""
        rc, kills, *_rest = self._stop([_win_row(5, self.CMD, NOW)], [(NOW.timestamp(), 9)])
        self.assertEqual((rc != 0, kills), (True, []))

    def test_sec3_a_uuid_prefix_never_matches_a_command_line_by_substring(self) -> None:
        """SEC-3：`status` 只顯示 8 碼；照 8 碼下 `stop --window` 不得子字串命中完整 UUID 視窗。"""
        rows = procstop._parse_windows(json.dumps([_win_row(10, self.CMD, NOW)]))
        anchors = [(NOW.timestamp(), 10)]
        self.assertEqual(procstop.verify(rows, SID[:8], anchors)[0], [])
        self.assertEqual([p["pid"] for p in procstop.verify(rows, SID.upper(), anchors)[0]], [10])

    def test_trace_records_carry_the_pid_of_the_spawn_event(self) -> None:
        """`trace_records`：`session_switch_spawned` 的 pid 帶出來；續跑日誌那種沒有 pid ⇒ None。"""
        tmp, traces = _tmp(self), _tmp(self)
        (tmp / f"autosdd_resume_log_{SID}.jsonl").write_text(json.dumps(
            {"event": "relay_snapshot_before", "at": NOW.isoformat()}) + "\n", encoding="utf-8")
        (traces / "x.jsonl").write_text(json.dumps(
            {"event": "session_switch_spawned", "sid": SID, "pid": 4242,
             "at": NOW.isoformat()}) + "\n", encoding="utf-8")
        self.assertEqual(sorted(procstop.trace_records(SID, traces, tmp), key=lambda r: r[1] or 0),
                         [(NOW.timestamp(), None), (NOW.timestamp(), 4242)])

    def test_trace_anchors_read_spawn_times_from_resume_log_and_trace_dir(self) -> None:
        """痕跡錨點：續跑日誌 `relay_snapshot_before` 與痕跡目錄 `session_switch_spawned`。"""
        tmp, traces = _tmp(self), _tmp(self)
        (tmp / f"autosdd_resume_log_{SID}.jsonl").write_text(json.dumps(
            {"event": "relay_snapshot_before", "at": NOW.isoformat()}) + "\n", encoding="utf-8")
        later = NOW + timedelta(hours=1)
        (traces / "x.jsonl").write_text(
            json.dumps({"event": "session_switch_spawned", "session": SID, "at": later.isoformat()})
            + "\n" + json.dumps({"event": "other", "session": SID, "at": NOW.isoformat()}) + "\n",
            encoding="utf-8")
        self.assertEqual(sorted(procstop.trace_anchors(SID, traces, tmp)),
                         [NOW.timestamp(), later.timestamp()])


class OutcomeAndCostTest(unittest.TestCase):
    """AT-SC-77～80：每窗收窗記結局、banner 游標制、cost 記錄的 pct 前後。"""

    def test_at_sc_77_every_window_outcome_carries_the_new_fields(self) -> None:
        """AT-SC-77：`relay_machine._record_outcome` 對**任何**次態（含非 loud 的 relay_next／
        done／quota_stop）落帳，帶起訖、route、pct 前後、handback 判定。"""
        trace = _tmp(self)
        state = {"session_id": "sid-x", "window_started_at": "2026-11-14T11:00:00+00:00",
                 "route_strategy": "SESSION_RESUME", "pct_before": 40.0, "pct_after": 62.0,
                 "handback_verdict": "written", "handback_path": "hb.md"}
        with unittest.mock.patch.dict(os.environ, {endurance_env.TRACE_DIR_ENV: str(trace)}):
            for next_st in (relay_machine.STATE_RELAY_NEXT, relay_machine.STATE_DONE,
                            relay_machine.STATE_QUOTA_STOP):
                relay_machine._record_outcome(state, next_st, "free", NOW)
        recs = [json.loads(ln) for ln in (trace / endurance_env.UNATTENDED_OUTCOME_NAME)
                .read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["reason"] for r in recs], ["relay_next", "done", "quota_stop"])
        for rec in recs:
            self.assertEqual((rec["started_at"], rec["route"], rec["pct_before"], rec["pct_after"]),
                             ("2026-11-14T11:00:00+00:00", "SESSION_RESUME", 40.0, 62.0))
            self.assertEqual((rec["ended_at"], rec["handback"]),
                             ("2026-11-14T12:00:00+00:00", "hb.md"))

    def test_record_outcome_falls_back_to_the_legacy_signature_and_never_raises(self) -> None:
        """舊簽名（無新欄）時退回舊呼叫；寫檔例外不外洩（落帳不得擋收窗）。"""
        calls: list = []

        def legacy(sid, reason, *, reset_returned, handback_path):
            calls.append((sid, reason, reset_returned, handback_path))
            return True

        with unittest.mock.patch.object(endurance_env, "record_unattended_outcome", legacy):
            relay_machine._record_outcome({"session_id": "s"}, relay_machine.STATE_DONE,
                                          "free", NOW)
        self.assertEqual(calls, [("s", "done", True, "")])

        def boom(*_a, **_k):
            raise OSError("disk")

        with unittest.mock.patch.object(endurance_env, "record_unattended_outcome", boom):
            relay_machine._record_outcome({"session_id": "s"}, relay_machine.STATE_DONE,
                                          "free", NOW)

    def test_at_sc_78_banner_is_read_once_via_the_cursor(self) -> None:
        """AT-SC-78：banner 讀兩次，第二次空（游標制）；SessionStart 簡報把它折成單行接在末尾。"""
        trace = _tmp(self)
        with unittest.mock.patch.dict(os.environ, {endurance_env.TRACE_DIR_ENV: str(trace)}):
            endurance_env.record_unattended_outcome("sid-b", "done", reset_returned=True,
                                                    handback_path="hb.md")
            first = session_brief._outcome_note()
            second = session_brief._outcome_note()
        self.assertIn("上次無人續跑", first)
        self.assertIn("停在 done", first)
        self.assertNotIn("\n", first)
        self.assertEqual(second, "")

    def test_outcome_note_never_raises_and_prints_nothing_when_empty(self) -> None:
        """簡報的 banner 失敗／為空 ⇒ 不印、不拋（簡報失敗不得擋 SessionStart）。"""
        self.assertEqual(session_brief._outcome_note(lambda: ""), "")

        def boom() -> str:
            raise RuntimeError("x")

        self.assertEqual(session_brief._outcome_note(boom), "")
        self.assertEqual(session_brief._outcome_note(lambda: "A\nB"), " A B")

    def test_at_sc_79_cost_record_carries_pct_before_and_after_with_measured_at(self) -> None:
        """AT-SC-79：前後讀數 40／62 ⇒ cost 記錄 `pct_before=40`、`pct_after=62`，各帶量測時刻。"""
        rec = resume_cost.build_record("s", 0, None, pct_before=40, pct_after=62,
                                       pct_before_at="2026-11-14T11:00:00+00:00",
                                       pct_after_at="2026-11-14T11:50:00+00:00")
        self.assertEqual((rec["pct_before"], rec["pct_after"]), (40, 62))
        self.assertEqual((rec["pct_before_at"], rec["pct_after_at"]),
                         ("2026-11-14T11:00:00+00:00", "2026-11-14T11:50:00+00:00"))

    def test_at_sc_80_missing_reading_nulls_both_fields(self) -> None:
        """AT-SC-80：前讀數缺 ⇒ 兩欄皆 None（既有「兩者皆有才填」規則；時刻欄同理）。"""
        rec = resume_cost.build_record("s", 0, None, pct_before=None, pct_after=62,
                                       pct_before_at=None, pct_after_at="t")
        self.assertEqual((rec["pct_before"], rec["pct_after"], rec["pct_after_at"]),
                         (None, None, None))

    def test_unreadable_after_reading_is_recorded_as_none_with_a_said_reason(self) -> None:
        """主控裁決（AT-SC-80 補強）：收窗讀不到新鮮讀數 ⇒ `pct_after` 記 None、附「量不到：…」
        與檢查時刻；兩邊都讀到時沒有備註。不是靜默的 None，也不是猜一個數。"""
        lost = resume_cost.build_record("s", 0, None, pct_before=40, pct_after=None,
                                        recorded_at="2026-11-14T12:00:00+00:00")
        self.assertEqual((lost["pct_before"], lost["pct_after"]), (None, None))
        self.assertTrue(lost["pct_note"].startswith("量不到："), lost["pct_note"])
        self.assertIn("後讀數", lost["pct_note"])
        self.assertEqual(lost["pct_checked_at"], "2026-11-14T12:00:00+00:00")
        both = resume_cost.build_record("s", 0, None, pct_before=40, pct_after=62,
                                        recorded_at="t")
        self.assertEqual((both["pct_note"], both["pct_checked_at"]), (None, None))

    def test_closing_a_window_never_calls_the_network_for_the_reading(self) -> None:
        """讀不到新鮮讀數時**不**為它外呼量測（無人窗口不得多燒額度）：`five_hour_reading` 只碰
        `read_quota`（快取）；碰任何別的屬性（`refresh_*`／`pace_state`）一律當場失敗。"""
        stale = type("S", (), {"axes": (), "measured_at": "", "reason": "stale-cache"})()

        class Gate:
            def read_quota(self, _now):
                return stale

            def __getattr__(self, name):
                raise AssertionError(f"收窗不得碰 quota_gate.{name}（外呼量測）")

        self.assertEqual(resume_cost.five_hour_reading(Gate()), (None, None))

    def test_outcome_record_says_why_the_reading_is_missing(self) -> None:
        """每窗結局檔：前後讀數缺 ⇒ 沒有 `pct_after` 鍵、有 `pct_note`「量不到：…」。"""
        trace = _tmp(self)
        state = {"session_id": "sid-n", "pct_before": 40.0, "pct_after": None}
        with unittest.mock.patch.dict(os.environ, {endurance_env.TRACE_DIR_ENV: str(trace)}):
            relay_machine._record_outcome(state, relay_machine.STATE_DONE, "free", NOW)
        rec = json.loads((trace / endurance_env.UNATTENDED_OUTCOME_NAME)
                         .read_text(encoding="utf-8").splitlines()[0])
        self.assertNotIn("pct_after", rec)
        self.assertTrue(rec["pct_note"].startswith("量不到："), rec)

    def test_record_window_takes_the_readings_from_state(self) -> None:
        """`record_window` 從狀態塊取 `pct_*`（`_run_resume` 前後各讀一次寫進去的那四個鍵）。"""
        path = _tmp(self) / "cost.jsonl"
        state = {"session_id": "s", "relay_seq": 0, "pct_before": 40.0, "pct_after": 62.0,
                 "pct_before_at": "a", "pct_after_at": "b"}
        rec = resume_cost.record_window(state, path)
        self.assertEqual((rec["pct_before"], rec["pct_after"], rec["pct_after_at"]),
                         (40.0, 62.0, "b"))
        self.assertEqual(json.loads(path.read_text(encoding="utf-8").splitlines()[0])["pct_before"],
                         40.0)

    def test_five_hour_reading_reads_cache_only_and_degrades_to_none(self) -> None:
        """`five_hour_reading`：取五小時軸 pct＋量測時刻；快取不可用／例外 ⇒ (None, None)。"""
        axis = type("A", (), {"kind": "five_hour", "pct": 42})()
        gate = type("G", (), {"read_quota": staticmethod(
            lambda now: type("S", (), {"axes": (axis,), "measured_at": "T"})())})
        self.assertEqual(resume_cost.five_hour_reading(gate), (42.0, "T"))
        empty = type("G", (), {"read_quota": staticmethod(
            lambda now: type("S", (), {"axes": (), "measured_at": "T"})())})
        self.assertEqual(resume_cost.five_hour_reading(empty), (None, None))
        self.assertEqual(resume_cost.five_hour_reading(object()), (None, None))

    def test_five_hour_reading_only_takes_the_five_hour_axis(self) -> None:
        """週軸排在前面也不得被記成五小時讀數；只有週軸 ⇒ 量不到（不猜）。"""
        def gate(*kinds):
            axes = tuple(type("A", (), {"kind": k, "pct": p})() for k, p in kinds)
            return type("G", (), {"read_quota": staticmethod(
                lambda now: type("S", (), {"axes": axes, "measured_at": "T"})())})

        self.assertEqual(resume_cost.five_hour_reading(
            gate(("weekly_all", 88), ("session", 12))), (12.0, "T"))
        self.assertEqual(resume_cost.five_hour_reading(gate(("weekly_all", 88))), (None, None))


class PlannerWiringTest(unittest.TestCase):
    """planner 三處薄接線（D2 交接包路徑、D7c 五小時軸前後讀數、D8 `--pace` 一行）的真行為。"""

    @classmethod
    def setUpClass(cls) -> None:
        hooks = str(_TOOLS.parent / ".claude" / "hooks")
        if hooks not in sys.path:
            sys.path.insert(0, hooks)
        import session_resume_planner  # noqa: PLC0415 — 需先有上面的 hook 路徑

        cls.planner = session_resume_planner

    def setUp(self) -> None:
        self.tmp = _tmp(self)
        patcher = unittest.mock.patch.dict(os.environ, {
            endurance_env.HANDBACK_DIR_ENV: str(self.tmp / "hb"),
            endurance_env.HANDOFF_DIR_ENV: str(self.tmp / "ho"),
            endurance_env.TRACE_DIR_ENV: str(self.tmp / "tr")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.plan = self.tmp / "plan.md"
        self.plan.write_text("# 任務書", encoding="utf-8")

    def _route(self, handoff_module):
        # 套件屬性與 sys.modules 兩處一起換：別的測試檔先載入真 handoff 時，套件已有 `handoff`
        # 屬性，`from lib.sessionctl import handoff` 先取屬性、不看 sys.modules（P1-1）。
        with unittest.mock.patch.dict(sys.modules, {"lib.sessionctl.handoff": handoff_module}), \
                unittest.mock.patch.object(sessionctl_pkg, "handoff", handoff_module,
                                           create=True):
            return self.planner.choose_resume_route("claude", "sid-x", None, str(self.plan))

    def test_fresh_route_points_the_prompt_at_the_handoff_package(self) -> None:
        """FRESH（逐字稿缺檔）⇒ 產交接包機械層並把 prompt 改成「按交接包繼續：讀 <路徑>」。"""
        seen: list = []
        package = self.tmp / "pkg.md"
        fake = type("H", (), {"ensure_mechanical": staticmethod(
            lambda sid, transcript, **kw: seen.append((sid, transcript)) or package)})
        route = self._route(fake)
        self.assertEqual(route["strategy"], self.planner.STRATEGY_FRESH)
        self.assertEqual(seen, [("sid-x", None)])
        self.assertIn("按交接包繼續：讀 " + str(package), " ".join(route["argv"]))

    def test_handoff_failure_falls_back_to_the_plan_path(self) -> None:
        """交接包是增益：`ensure_mechanical` 拋例外 ⇒ 選路不得失敗，沿用任務書路徑。"""
        def boom(*_a, **_k):
            raise OSError("disk")

        route = self._route(type("H", (), {"ensure_mechanical": staticmethod(boom)}))
        self.assertEqual(route["strategy"], self.planner.STRATEGY_FRESH)
        self.assertIn("按磁碟任務書繼續", " ".join(route["argv"]))

    def test_run_resume_reads_the_five_hour_axis_before_and_after_spawn(self) -> None:
        """AT-SC-79 的接線：`_run_resume` spawn 前後各讀一次五小時軸（前 40、後 62），各自帶量測
        時刻與本窗起點；落進狀態塊後 `record_window` 寫進成本帳。"""
        readings = iter([(40.0, "T-before"), (62.0, "T-after")])
        transcript = self.tmp / "sid-w.jsonl"
        transcript.write_text('{"type":"assistant"}\n', encoding="utf-8")
        state = {"plan_path": str(self.plan), "session_id": "sid-w", "transcript": str(transcript)}
        done = type("D", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        args = self.planner.build_parser().parse_args(["--probe-command", "claude"])
        with unittest.mock.patch.object(self.planner.resume_cost, "five_hour_reading",
                                        lambda gate, now=None: next(readings)), \
                unittest.mock.patch.object(self.planner.subprocess, "run", lambda *a, **k: done), \
                contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            self.planner._run_resume(args, state, self.tmp / "log.jsonl")
        self.assertEqual((state["pct_before"], state["pct_before_at"]), (40.0, "T-before"))
        self.assertEqual((state["pct_after"], state["pct_after_at"]), (62.0, "T-after"))
        self.assertIsNotNone(datetime.fromisoformat(state["window_started_at"]).tzinfo,
                             "持久化時間必須帶 offset（鐵律三）")
        rec =resume_cost.record_window(state, self.tmp / "cost.jsonl")
        self.assertEqual((rec["pct_before"], rec["pct_after"]), (40.0, 62.0))

    def test_pace_prints_the_model_advice_line(self) -> None:
        """`--pace` 多印一行「模型建議：…」（額度快取不可用時是「量不到」，但這一行必須在）。"""
        transcript = self.tmp / "sid-p.jsonl"
        transcript.write_text('{"type":"assistant"}\n', encoding="utf-8")
        planner = self.planner
        blank = type("S", (), {"axes": (), "reason": "test"})()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()), \
                unittest.mock.patch.object(planner.quota_gate, "pace_report",
                                           lambda **kw: "PACE\n"), \
                unittest.mock.patch.object(planner.quota_gate, "read_quota", lambda now: blank), \
                unittest.mock.patch.object(planner.quota_reconcile, "ledger_gap_line",
                                           lambda: ""), \
                unittest.mock.patch.object(planner.sentinel_lifecycle, "liveness_line",
                                           lambda sid: ""):
            rc = planner.main(["--pace", "--transcript", str(transcript)])
        self.assertEqual(rc, 0)
        self.assertIn("PACE\n模型建議：量不到", out.getvalue())


if __name__ == "__main__":
    unittest.main()
