"""realverify 函式庫判準的單元測試（假逐字稿；**不算 E2E**，E2E 是 realverify run 本身）。

WHY：載具自己的判準寫錯會讓整批 E2E 假綠，所以記錄格式斷言、清理邊界、排程名前綴、
runner rc 對映都要有可失敗的測試。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib.realverify import cases as rv_cases  # noqa: E402
from lib.realverify import interactive, ledger, runner, sched  # noqa: E402
from lib.realverify.driver import EnvMissing, _kill_tree  # noqa: E402
from lib.realverify.sandbox import (  # noqa: E402
    PROBE_HOOK_SRC,
    Sandbox,
    cleanup_handoff_for,
    main_checkout_root,
    slug_of,
)
from lib.realverify.transcript import Transcript, find_transcript  # noqa: E402

SID = "11111111-2222-3333-4444-555555555555"

_MODULE_PATCHES: list = []


def setUpModule():
    """本檔的測試都不得碰真環境：租約帳指到 tmp、行程列舉／快照／開頭重放換成空殼（真快照與真重放在
    `test_realverify_se_*.py` 以假家目錄驗；這裡只驗載具本身的行為）。"""
    from lib.realverify import leases, leases_discover, leases_undo  # noqa: PLC0415
    tmp = tempfile.TemporaryDirectory()
    _MODULE_PATCHES.append(tmp)
    for p in (mock.patch.object(leases, "LEASE_DIR", Path(tmp.name) / "leases"),
              mock.patch.object(leases_undo, "list_procs", return_value=[]),
              mock.patch.object(runner, "_take", return_value=None),
              mock.patch.object(leases_discover, "preflight", return_value=([], {}))):
        p.start()
        _MODULE_PATCHES.append(p)


def tearDownModule():
    for p in reversed(_MODULE_PATCHES):
        p.stop() if hasattr(p, "stop") else p.cleanup()
    _MODULE_PATCHES.clear()


def _write_transcript(d: Path, recs: list[dict]) -> Path:
    p = d / f"{SID}.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    return p


RECS = [
    {"type": "user", "timestamp": "2026-11-18T00:00:00.000Z"},
    {"attachment": {"type": "hook_blocking_error", "hookEvent": "Stop",
                    "blockingError": {"blockingError": "請先 --finalize", "command": "x"}},
     "type": "attachment"},
    {"attachment": {"type": "hook_system_message", "hookEvent": "Stop", "content": "看管中"},
     "type": "attachment"},
    {"type": "system", "subtype": "informational", "level": "warning", "preventContinuation": True,
     "content": "UserPromptSubmit operation blocked by hook:\nR\n\nOriginal prompt: x"},
    {"type": "system", "subtype": "stop_hook_summary", "hookErrors": ["e"],
     "hookInfos": [{"command": "c"}]},
    {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-11-18T01:00:00.000Z"},
]


class TranscriptAssertionsTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tr = Transcript(_write_transcript(Path(self._td.name), RECS))

    def test_blocking_error_matches_event_and_text(self):
        self.assertTrue(self.tr.has_blocking_error("Stop", "--finalize"))
        self.assertFalse(self.tr.has_blocking_error("Stop", "不存在的字"))  # 內容比對要真的能失敗
        self.assertFalse(self.tr.has_blocking_error("PreToolUse", ""))  # 事件名要真的比對

    def test_system_message_and_ups_block(self):
        self.assertTrue(self.tr.has_system_message("Stop", "看管中"))
        self.assertFalse(self.tr.has_system_message("SessionStart", "看管中"))
        self.assertTrue(self.tr.user_prompt_blocked())
        self.assertFalse(self.tr.user_prompt_blocked("沒這字"))

    def test_ups_block_needs_prevent_continuation_and_prefix(self):
        recs = [dict(RECS[3], preventContinuation=False), dict(RECS[3], content="其他資訊")]
        with tempfile.TemporaryDirectory() as d:
            tr = Transcript(_write_transcript(Path(d), recs))
            self.assertFalse(tr.user_prompt_blocked())

    def test_compact_boundary_after(self):
        self.assertTrue(self.tr.has_compact_boundary_after())
        self.assertTrue(self.tr.has_compact_boundary_after("2026-11-18T00:30:00Z"))
        self.assertFalse(self.tr.has_compact_boundary_after("2026-11-18T02:00:00Z"))

    def test_coords_use_one_based_line_numbers(self):
        r = self.tr.hook_blocking_errors("Stop")[0]
        self.assertEqual(self.tr.coords(r), f"{SID[:8]}:2")

    def test_find_transcript_by_sid_and_garbage_lines_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            sub = Path(d) / "slug"
            sub.mkdir()
            p = sub / f"{SID}.jsonl"
            p.write_text("not json\n" + json.dumps(RECS[0]) + "\n", encoding="utf-8")
            self.assertEqual(find_transcript(SID, Path(d)), p)
            self.assertEqual(len(Transcript(p).recs), 1)
            self.assertIsNone(find_transcript("00000000-0000-0000-0000-000000000000", Path(d)))


class SandboxTest(unittest.TestCase):
    def test_slug_matches_claude_code_rule(self):
        got = slug_of(r"C:\Users\a b\T_1")  # platform-ok: 純字串轉換
        self.assertEqual(got, "C--Users-a-b-T-1")

    def test_handoff_cleanup_only_touches_own_sid_and_rejects_short_sid(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            mine = [base / f"{SID}_20261118T000000Z.md", base / f"{SID}_20261118T000000Z.sealed"]
            other = base / "99999999-2222-3333-4444-555555555555_x.md"
            for p in [*mine, other]:
                p.write_text("x", encoding="utf-8")
            gone = cleanup_handoff_for(SID, base)
            self.assertEqual(sorted(gone), sorted(p.name for p in mine))
            self.assertTrue(other.exists())  # 別人的絕不刪
            with self.assertRaises(ValueError):
                cleanup_handoff_for(SID[:8], base)  # 前綴會誤傷，直接拒絕

    def test_create_and_cleanup_roundtrip_leaves_nothing(self):
        sb = Sandbox.create()
        root = sb.root
        self.assertTrue((root / ".git").is_dir())
        self.assertTrue((root / ".claude" / "rv_probe_hook.py").is_file())
        sb.add_probe_hooks()
        s = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["hooks"]), {"SessionStart", "UserPromptSubmit", "Stop"})
        repo = str(Path(__file__).resolve().parents[2])
        self.assertFalse(str(root).startswith(repo))  # 沙盒必須在 repo 外
        notes = sb.cleanup()
        self.assertFalse(root.exists(), notes)

    def test_repo_hook_entry_is_absolute_not_launcher(self):
        sb = Sandbox.create(probe_hook=False)
        self.addCleanup(sb.cleanup)
        sb.add_repo_hook("Stop", ".claude/hooks/check_claim_provenance.py")
        entry = sb.settings["hooks"]["Stop"][0]["hooks"][0]
        self.assertTrue(Path(entry["args"][0]).is_absolute())
        self.assertNotIn("_hook_launcher", json.dumps(entry))  # 沙盒中啟動器必 fail-open 假綠
        with self.assertRaises(FileNotFoundError):
            sb.add_repo_hook("Stop", ".claude/hooks/nope.py")

    def test_env_drops_parent_session_vars(self):
        with mock.patch.dict("os.environ", {"CLAUDECODE": "1"}):  # 離開時還原原值，不是 pop
            sb = Sandbox(root=Path(tempfile.gettempdir()))
            self.assertNotIn("CLAUDECODE", sb.env())
            self.assertEqual(sb.env()["AUTOSDD_SENTINEL_OFF"], "1")

    def test_probe_hook_source_compiles(self):
        compile(PROBE_HOOK_SRC, "rv_probe_hook.py", "exec")


class SchedNamingTest(unittest.TestCase):
    def test_every_name_carries_the_rv_prefix(self):
        self.assertEqual(sched.rv_name("x"), "AutoSDD_RV_x")
        self.assertEqual(sched.rv_name("AutoSDD_RV_y"), "AutoSDD_RV_y")

    def test_lock_is_exclusive_and_released(self):
        with sched.sched_lock(timeout_s=2):
            self.assertTrue(sched.LOCK_PATH.exists())
            with self.assertRaises(TimeoutError), sched.sched_lock(timeout_s=1):
                pass
        self.assertFalse(sched.LOCK_PATH.exists())


class RunnerTest(unittest.TestCase):
    def _case(self, cid, fn, long=False):
        return rv_cases.Case(cid, "fake", fn, (), long, False)

    def test_pass_fail_env_map_to_rc_0_1_2_and_never_skip_green(self):
        def ok(ctx):
            ctx.evidence("e1")

        def bad(ctx):
            ctx.check(False, "boom")

        def env(ctx):
            raise EnvMissing("no claude")

        with tempfile.TemporaryDirectory() as d:
            led = Path(d) / "L.md"
            self.assertEqual(runner.run("t", [self._case("RV-T-ok", ok)], ledger_path=led), 0)
            both = [self._case("RV-T-ok", ok), self._case("RV-T-bad", bad)]
            self.assertEqual(runner.run("t", both, ledger_path=led), 1)
            self.assertEqual(runner.run("t", [self._case("RV-T-env", env)], ledger_path=led), 2)
            rows = [x for x in led.read_text(encoding="utf-8").splitlines() if x.startswith("| 20")]
            self.assertEqual(len(rows), 3)  # 每次 run 追加一列
            self.assertIn("RV-T-bad", rows[1])

    def test_unexpected_exception_is_a_failure_not_a_skip(self):
        def crash(ctx):
            raise KeyError("x")

        self.assertEqual(runner.run_case(self._case("RV-T-crash", crash)).status, "fail")

    def test_select_excludes_long_unless_asked(self):
        reg = {"A": self._case("A", None), "B": self._case("B", None, long=True)}
        short = runner.select(reg, case_id=None, family="fake", all_=False, long=False)
        self.assertEqual([c.id for c in short], ["A"])
        full = runner.select(reg, case_id=None, family="fake", all_=False, long=True)
        self.assertEqual(len(full), 2)
        self.assertEqual(runner.select(reg, case_id="ZZ", family=None, all_=False, long=False), [])

    def test_ledger_header_written_once_and_pipes_escaped(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "L.md"
            ledger.append_row("a|b", "pass", 1, [], ["x"], 1.0, p)
            ledger.append_row("c", "fail", 2, ["RV-1"], [], 2.0, p)
            txt = p.read_text(encoding="utf-8")
            self.assertEqual(txt.count("# RealVerify 結果帳本"), 1)
            self.assertIn("a\\|b", txt)


def _kept_to(d: str):
    """把失敗證據的持久目錄指到測試暫存（不污染真 `~/.autosdd/realverify_kept`）。"""
    return mock.patch.object(rv_cases, "kept_dir", lambda: Path(d))


class FailureEvidenceIsKeptTest(unittest.TestCase):
    """tools/lib/realverify/runner.py＋sandbox.py：失敗時沙盒逐字稿與 hook 輸出在清理前被保留。

    WHY（R216 複審 P3-c）：RV-C4 低頻逾時 291 秒，沙盒逐字稿隨清理一起刪掉，根因再也查不到。
    證據只在失敗時留；通過的案例照舊清乾淨（不累積殘留）。"""

    def _failing_case(self, fail: bool):
        def fn(ctx):
            sb = ctx.sandbox()
            (sb.root / "hook_events.jsonl").write_text('{"ev":"Stop"}\n', encoding="utf-8")
            (sb.root / "debug_abc123.log").write_text("dbg", encoding="utf-8")
            tdir = Path.home() / ".claude" / "projects" / slug_of(sb.root)
            tdir.mkdir(parents=True, exist_ok=True)
            (tdir / f"{sb.sid}.jsonl").write_text('{"type":"user"}\n', encoding="utf-8")
            self.sb_root = sb.root
            ctx.check(not fail, "boom")
        return rv_cases.Case("RV-T-keep", "fake", fn, (), False, False)

    def test_a_failed_case_keeps_transcript_and_hook_output_a_passing_one_keeps_nothing(self):
        with tempfile.TemporaryDirectory() as d, _kept_to(d):
            ok = runner.run_case(self._failing_case(False))
            self.assertEqual(ok.status, "pass")
            self.assertEqual(list(Path(d).iterdir()), [], "通過的案例不得留證據")
            bad = runner.run_case(self._failing_case(True))
            self.assertEqual(bad.status, "fail")
            kept = [p for p in Path(d).iterdir() if p.name.startswith("RV-T-keep_")]
            self.assertEqual(len(kept), 1)
            self.assertIn(str(kept[0]), bad.detail, "失敗訊息必須印出保留路徑")
            self.assertTrue(any(str(kept[0]) in e for e in bad.evidence), "保留路徑要進帳本證據")
            box = next(kept[0].iterdir())
            names = {p.name for p in box.rglob("*") if p.is_file()}
            self.assertTrue({"hook_events.jsonl", "debug_abc123.log"} <= names, names)
            self.assertTrue(any(n.endswith(".jsonl") and n != "hook_events.jsonl" for n in names),
                            f"逐字稿沒被保留：{names}")
        self.assertFalse(self.sb_root.exists(), "保留證據後沙盒仍必須清掉")

    def test_env_missing_keeps_nothing(self):
        def fn(ctx):
            ctx.sandbox()
            raise EnvMissing("no claude")
        with tempfile.TemporaryDirectory() as d, _kept_to(d):
            out = runner.run_case(rv_cases.Case("RV-T-env2", "fake", fn, (), False, False))
            self.assertEqual(out.status, "env")
            self.assertEqual(list(Path(d).iterdir()), [])


class TimeoutKillsTheWholeTreeTest(unittest.TestCase):
    """tools/lib/realverify/driver.py::_kill_tree：逾時要連子行程樹一起砍。

    WHY（R216 複審 P3-c）：RV-C4 逾時時 claude 派生的背景行程活下來、握著沙盒目錄 ⇒ 清理報 RESIDUE。
    只砍本體（舊 `proc.kill()`）時，子行程的心跳檔會繼續更新。POSIX 沒有零依賴的等價做法，
    只斷言本體已死；樹的斷言限 Windows（誠實劃界，不是 skip）。"""

    def test_parent_and_child_both_stop_writing(self):
        with tempfile.TemporaryDirectory() as d:
            beat = Path(d) / "beat"
            child = ("import time,sys\nwhile True:\n"
                     f" open(r'{beat}','w').write(str(time.time())); time.sleep(0.1)\n")
            parent = ("import subprocess,sys,time\n"
                      f"subprocess.Popen([sys.executable,'-c',{child!r}])\ntime.sleep(60)\n")
            proc = subprocess.Popen([sys.executable, "-c", parent])
            for _ in range(100):  # 等子行程第一次心跳（最多 10 秒）
                if beat.exists():
                    break
                time.sleep(0.1)
            self.assertTrue(beat.exists(), "前提：子行程已在寫心跳")
            _kill_tree(proc)
            proc.wait(timeout=10)
            self.assertIsNotNone(proc.poll())
            if sys.platform == "win32":
                time.sleep(0.5)
                first = beat.stat().st_mtime
                time.sleep(0.8)
                self.assertEqual(beat.stat().st_mtime, first, "子行程仍在寫心跳＝只砍了本體")


class R217SandboxCleanupTest(unittest.TestCase):
    """R217 DEF-03（REQ-WP-44／AT-WP-47／AT-WP-48／MU-WP-08）：沙盒逐字稿目錄不再殘留。

    成因（P6）：舊 cleanup 只殺本體、`rmtree(ignore_errors=True)` 吞掉錯誤，而 claude 的子孫行程在
    cleanup
    之後還在寫逐字稿 ⇒ 目錄 mtime 晚於案例結束。修法＝先砍樹、等退出、再刪並**驗證**，刪不掉就回報
    RESIDUE（runner 已把 RESIDUE 判 fail）。路徑用 tmp 圍起來，不碰真實 `~/.claude/projects`。"""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.projects = Path(self._td.name) / "projects"
        self.projects.mkdir()
        patcher = mock.patch("lib.realverify.sandbox.projects_dir", lambda: self.projects)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _sandbox_with_transcripts(self) -> tuple[Sandbox, Path]:
        sb = Sandbox.create()
        folder = self.projects / slug_of(sb.root)
        folder.mkdir()
        (folder / f"{sb.sid}.jsonl").write_text("{}\n", encoding="utf-8")
        return sb, folder

    def test_at_wp_47_a_failed_transcript_dir_removal_is_reported_not_swallowed(self):
        """假 rmtree 對逐字稿目錄失敗 ⇒ cleanup 回報 `RESIDUE transcript-dir`（舊版 ignore_errors
        靜默）。"""
        sb, folder = self._sandbox_with_transcripts()
        real = shutil.rmtree

        def flaky(path, *a, **kw):
            if Path(path) == folder:
                raise PermissionError("假的：被占用")
            return real(path, *a, **kw)
        with mock.patch("lib.realverify.sandbox.shutil.rmtree", flaky), \
                mock.patch("lib.realverify.sandbox.time.sleep", lambda s: None):
            notes = sb.cleanup()
        self.assertTrue(any(n.startswith("RESIDUE transcript-dir") and "PermissionError" in n
                            for n in notes), notes)
        self.assertFalse(sb.root.exists(), "沙盒根照常刪掉；殘留只回報逐字稿目錄那一個")
        shutil.rmtree(folder)

    def test_a_leftover_process_still_writing_is_killed_before_the_directory_is_removed(self):
        """成因重現：沙盒的行程樹仍在往逐字稿目錄寫 ⇒ cleanup 先砍樹、等退出，目錄才刪得乾淨。"""
        sb, folder = self._sandbox_with_transcripts()
        child = ("import time,sys\nwhile True:\n"
                 f" open(r'{folder / 'late.jsonl'}','a').write('x'); time.sleep(0.05)\n")
        parent = ("import subprocess,sys,time\n"
                  f"subprocess.Popen([sys.executable,'-c',{child!r}])\ntime.sleep(60)\n")
        proc = subprocess.Popen(
            [sys.executable, "-c", parent], cwd=str(sb.root),
            start_new_session=(sys.platform != "win32"),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        sb.procs.append(proc)
        for _ in range(100):
            if (folder / "late.jsonl").exists():
                break
            time.sleep(0.1)
        self.assertTrue((folder / "late.jsonl").exists(), "前提：子孫行程已在寫逐字稿")
        notes = sb.cleanup()
        self.assertFalse(any(n.startswith("RESIDUE") for n in notes), notes)
        self.assertFalse(folder.exists() or sb.root.exists())
        self.assertIsNotNone(proc.poll())

    def test_a_process_that_will_not_die_is_reported_as_residue(self):
        """行程退不出去（假 Popen）⇒ RESIDUE process，案例不得判綠。"""
        sb, folder = self._sandbox_with_transcripts()

        class Stubborn:
            pid = 4242

            def poll(self):
                return None

            def kill(self):
                return None

            def wait(self, timeout=None):
                raise subprocess.TimeoutExpired("x", timeout)
        sb.procs.append(Stubborn())
        with mock.patch("lib.realverify.sandbox.kill_tree", lambda p: None):
            notes = sb.cleanup()
        self.assertTrue(any(n.startswith("RESIDUE process pid 4242") for n in notes), notes)
        self.assertFalse(folder.exists())

    def test_at_wp_48_sweep_keeps_live_roots_and_registry_cwd_and_removes_true_orphans(self):
        """sweep：沙盒根存在 ⇒ 留；根不存在 ∧ 無登記檔 cwd ⇒ 刪；根不存在但登記檔 cwd 指向它 ⇒ 留；
        名稱
        不含前綴的別的專案目錄絕不碰；`--dry-run` 只列不刪。"""
        tmp_root = Path(self._td.name) / "tmp"
        tmp_root.mkdir()
        sessions = Path(self._td.name) / "sessions"
        sessions.mkdir()
        alive_root = tmp_root / "AutoSDD_RV_sbx_alive1"
        alive_root.mkdir()
        gone = tmp_root / "AutoSDD_RV_sbx_gone01"
        used = tmp_root / "AutoSDD_RV_sbx_used01"
        orphan2 = tmp_root / "AutoSDD_RV_sbx_gone02"
        for p in (alive_root, gone, used, orphan2):
            (self.projects / slug_of(p)).mkdir()
        other = self.projects / "C--Users-me-Projects-real"
        other.mkdir()
        (sessions / "7.json").write_text(json.dumps({"pid": 7, "cwd": str(used)}), encoding="utf-8")
        from lib.realverify.sandbox import sweep_orphans  # noqa: PLC0415

        dry = sweep_orphans(projects=self.projects, sessions=sessions, tmp_root=tmp_root,
                            dry_run=True)
        self.assertEqual(sorted(dry["removed"]), sorted(slug_of(p) for p in (gone, orphan2)))
        self.assertTrue((self.projects / slug_of(gone)).exists(), "dry-run 不刪")
        res = sweep_orphans(projects=self.projects, sessions=sessions, tmp_root=tmp_root)
        self.assertEqual(sorted(res["removed"]), sorted(slug_of(p) for p in (gone, orphan2)))
        self.assertEqual(sorted(n for n, _w in res["kept"]),
                         sorted(slug_of(p) for p in (alive_root, used)))
        self.assertTrue((self.projects / slug_of(alive_root)).exists())
        self.assertTrue((self.projects / slug_of(used)).exists())
        self.assertTrue(other.exists(), "別的專案絕不碰")
        self.assertFalse((self.projects / slug_of(gone)).exists())

    def test_the_oldwin_prefix_is_written_to_the_sandbox_own_trace_dir(self):
        """REQ-WP-101：沙盒前綴是資料檔（`traces/oldwin/task_prefix`），不是環境變數；
        與真機前綴不同。"""
        sb = Sandbox.create()
        self.addCleanup(sb.cleanup)
        prefix = sb.oldwin_prefix()
        self.assertTrue(prefix.startswith("AutoSDD_OldWinCloseSbx_") and prefix.endswith("_"))
        self.assertNotEqual(prefix, "AutoSDD_OldWinClose_")
        self.assertEqual((sb.root / "traces" / "oldwin" / "task_prefix").read_text(encoding="utf-8")
                         .strip(), prefix)


class MainCheckoutRootTest(unittest.TestCase):
    """tools/lib/realverify/sandbox.py::main_checkout_root：worktree 內回主 checkout，否則回自己。

    WHY：RV-C3 的事故逐字稿母體住主 checkout 的專案目錄；在 worktree 跑時 slug 對不上而誤判紅。"""

    def test_worktree_resolves_to_the_main_checkout_and_plain_repo_to_itself(self):
        with tempfile.TemporaryDirectory() as d:
            main, wt = Path(d).resolve() / "main", Path(d).resolve() / "wt"
            main.mkdir()
            git = ["git", "-c", "user.email=a@b.c", "-c", "user.name=t"]
            for argv in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "x"],
                         ["worktree", "add", "-q", str(wt)]):
                subprocess.run([*git, "-C", str(main), *argv], check=True, capture_output=True)
            self.assertEqual(main_checkout_root(main), main)
            self.assertEqual(main_checkout_root(wt), main)
            subprocess.run([*git, "-C", str(main), "worktree", "remove", str(wt)],
                           check=True, capture_output=True)


class RegistryTest(unittest.TestCase):
    def test_discovered_cases_are_all_listed_in_protocol_json(self):
        reg = rv_cases.discover()
        proto = runner.load_protocol().get("cases", {})
        self.assertTrue(reg, "自動發現不到任何案例")
        missing = sorted(set(reg) - set(proto))
        self.assertEqual(missing, [], "已實作案例必須登記在 cases.json")
        for cid, c in reg.items():
            self.assertEqual(proto[cid]["family"], c.family, cid)

    def test_duplicate_case_id_is_rejected(self):
        rv_cases.discover()
        with self.assertRaises(ValueError):
            rv_cases.case("RV-L1", "hooks")(lambda ctx: None)


class InteractiveWindowEntryLockTest(unittest.TestCase):
    """tools/lib/realverify/interactive.py：開互動視窗只准經唯一入口（R217 F5）。

    WHY（2026-11-20 10:4x 掌舵者真機回報）：沙盒是 `git init` 新 repo＝新信任鍵，互動 claude 必跳
    信任框；繞過入口的開窗寫法就是事故形態。掃描結果必須與 `UNMIGRATED` 完全相等（新繞過紅、
    改好沒刪列也紅），runner 對 `UNMIGRATED` 判 ENV 不執行。"""

    RED = {
        "a.py::direct_console": (
            "def direct_console(ctx):\n    subprocess.Popen(['x'], creationflags="
            "subprocess.CREATE_NEW_CONSOLE)\n"
        ),
        "a.py::getattr_console": "def getattr_console(ctx):\n    f = getattr(subprocess, "
        "'CREATE_NEW_CONSOLE', 0)\n",
        "a.py::flag_literal": "def flag_literal(ctx):\n    run(['x'], creationflags=0x10)\n",
        "a.py::cli_spawn": "def cli_spawn(ctx):\n    run_cli(sb, 'handoff', '--spawn', p)\n",
        "a.py::lib_spawn": "def lib_spawn(ctx):\n    handoff.spawn(p)\n",
        "a.py::resume": "def resume(ctx):\n    park_cli.spawn_resume(sid)\n",
        "a.py::bare_claude": "def bare_claude(ctx):\n    exe = find_claude()\n"
        "    subprocess.Popen([exe, '--model', 'haiku', 'hi'])\n",
        "a.py::literal_claude": (
            "def literal_claude(ctx):\n    subprocess.Popen(['claude', 'hi'])\n"
        ),
        "a.py::_helper": "def _helper(sb):\n    subprocess.Popen(['claude', 'hi'])\n",
        "a.py::uses_helper": "def uses_helper(ctx):\n    _helper(ctx.sandbox())\n",
    }
    GREEN = (
        "def ok_p(ctx):\n    exe = find_claude()\n    subprocess.Popen([exe, '-p', 'hi'])\n"
        "def ok_ver(ctx):\n    subprocess.run([real_claude(), '--version'])\n"
        "def ok_ps(ctx):\n    exe = 'powershell.exe'\n    subprocess.run([exe, '-NoProfile'])\n"
        "def ok_entry(ctx):\n    sb = interactive.trusted_sandbox(ctx)\n"
        "    run_cli(sb, 'handoff', '--spawn', p)\n"
        "def _h2(sb):\n    open_it(['claude', 'x'], creationflags=CREATE_NEW_CONSOLE)\n"
        "def ok_via_helper(ctx):\n    sb = trusted_sandbox(ctx)\n    _h2(sb)\n"
        "def ok_needle(ctx):\n    for needle in ('--spawn', '--fire'):\n        pass\n"
    )

    def test_scan_of_the_real_tree_equals_the_unmigrated_list(self):
        found = interactive.find_bypasses(interactive.realverify_sources())
        self.assertEqual(set(found), set(interactive.UNMIGRATED),
                         f"繞過入口的開窗寫法與 UNMIGRATED 不一致：{found}")

    def test_red_forms_are_caught_and_green_forms_are_not(self):
        with tempfile.TemporaryDirectory() as d:
            red, green = Path(d) / "a.py", Path(d) / "b.py"
            red.write_text("".join(self.RED.values()), encoding="utf-8")
            green.write_text(self.GREEN, encoding="utf-8")
            found = interactive.find_bypasses([red, green])
        self.assertEqual(set(found), set(self.RED), found)
        self.assertEqual(found["a.py::uses_helper"], ["經 _helper()"])

    def test_runner_refuses_an_unmigrated_case_without_running_it(self):
        ran: list[int] = []

        def rv_fake(ctx):
            ran.append(1)

        c = rv_cases.Case("RV-ZZ1", "x", rv_fake)
        key = f"{rv_fake.__module__.rsplit('.', 1)[-1]}.py::rv_fake"
        with mock.patch.object(interactive, "UNMIGRATED", frozenset({key})):
            out = runner.run_case(c)
        self.assertEqual((out.status, ran), ("env", []))
        self.assertIn("信任框", out.detail)
        self.assertEqual(runner.run_case(c).status, "pass")  # 不在名單就照常跑


class TrustGateTest(unittest.TestCase):
    """interactive.trusted_sandbox：確認不了「不跳信任框」就拒絕（ENV），絕不建出可開窗的沙盒。

    WHY：入口若在未信任時放行，開出的視窗就停在信任框——正是要根治的事故。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.host = self.tmp / "host"
        self.cfg = self.tmp / "claude.json"
        self.probed: list[Path] = []

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _trust(self, key: str, value=True):
        self.cfg.write_text(json.dumps({"projects": {key: {"hasTrustDialogAccepted": value}}}),
                            encoding="utf-8")

    def _prober(self, verdict):
        def p(cwd):
            self.probed.append(Path(cwd))
            return verdict, "fake"
        return p

    def _worktrees(self) -> str:
        return subprocess.run(["git", "-C", str(self.host), "worktree", "list", "--porcelain"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace").stdout

    def test_config_key_forms(self):
        key = interactive.host_key(self.host)
        self._trust(key)
        self.assertTrue(interactive.trusted_in_config(self.host, self.cfg))
        if sys.platform == "win32":
            self._trust(key.replace("/", "\\").lower())
            self.assertTrue(interactive.trusted_in_config(self.host, self.cfg))
        self._trust(key, value=False)
        self.assertFalse(interactive.trusted_in_config(self.host, self.cfg))
        self._trust(interactive.host_key(self.tmp))  # 父目錄信任不算（巢狀 repo）
        self.assertFalse(interactive.trusted_in_config(self.host, self.cfg))
        self.cfg.write_text("{broken", encoding="utf-8")
        self.assertFalse(interactive.trusted_in_config(self.host, self.cfg))
        self.assertFalse(interactive.trusted_in_config(self.host, self.tmp / "missing.json"))

    def test_debug_log_classification_fails_closed(self):
        self.assertEqual(interactive.classify_debug(f"x\n{interactive.READY_MARK}\n"), "ready")
        self.assertEqual(interactive.classify_debug(interactive.UNTRUSTED_MARK), "untrusted")
        self.assertEqual(interactive.classify_debug("[STARTUP] Running showSetupScreens()"),
                         "unknown")

    def test_untrusted_host_is_refused_before_any_sandbox_or_probe(self):
        with self.assertRaises(interactive.NotTrusted) as cm:
            interactive.trusted_sandbox(host=self.host, claude_json=self.cfg,
                                        prober=self._prober("ready"))
        self.assertIsInstance(cm.exception, EnvMissing)  # runner 判 ENV，不是綠
        self.assertEqual(self.probed, [])
        self.assertEqual(self._worktrees().count("worktree "), 1, "未信任時不得加任何 worktree")
        self.assertIn(interactive.host_key(self.host), str(cm.exception))  # 告訴人要信任哪把鍵

    def test_probe_not_ready_refuses_and_leaves_no_worktree(self):
        interactive.ensure_host(self.host)
        self._trust(interactive.host_key(self.host))
        with self.assertRaises(interactive.NotTrusted):
            interactive.trusted_sandbox(host=self.host, claude_json=self.cfg,
                                        prober=self._prober("unknown"))
        self.assertEqual(len(self.probed), 1)
        self.assertFalse(self.probed[0].exists(), "拒絕後沙盒目錄應已清掉")
        self.assertNotIn(str(self.probed[0]).replace("\\", "/").lower(),
                         self._worktrees().replace("\\", "/").lower())

    def test_ready_builds_a_host_worktree_sandbox_and_cleans_it(self):
        interactive.ensure_host(self.host)
        self._trust(interactive.host_key(self.host))
        sb = interactive.trusted_sandbox(host=self.host, claude_json=self.cfg,
                                         prober=self._prober("ready"))
        try:
            self.assertEqual(self.probed, [sb.root])  # 探針跑在沙盒本身
            common = subprocess.run(
                [
                    "git",
                    "-C",
                    str(sb.root),
                    "rev-parse",
                    "--path-format=absolute",
                    "--git-common-dir",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            ).stdout
            self.assertEqual(Path(common.strip()).resolve(), (self.host / ".git").resolve())
            self.assertTrue((sb.root / ".claude" / "settings.json").is_file())
            interactive.assert_trusted(sb)
            with self.assertRaises(ValueError):
                interactive.open_window(sb, ["-p", "x"])
        finally:
            notes = sb.cleanup()
        self.assertFalse([n for n in notes if n.startswith("RESIDUE")], notes)
        self.assertFalse(sb.root.exists())
        self.assertNotIn(sb.root.name.lower(), self._worktrees().lower())

    def test_plain_sandbox_cannot_open_a_window(self):
        with self.assertRaises(interactive.NotTrusted):
            interactive.open_window(Sandbox(root=self.tmp), ["hi"])


if __name__ == "__main__":
    unittest.main()
