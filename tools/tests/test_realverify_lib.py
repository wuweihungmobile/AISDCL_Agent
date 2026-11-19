"""realverify 函式庫判準的單元測試（假逐字稿；**不算 E2E**，E2E 是 realverify run 本身）。

WHY：載具自己的判準寫錯會讓整批 E2E 假綠，所以記錄格式斷言、清理邊界、排程名前綴、
runner rc 對映都要有可失敗的測試。
"""

from __future__ import annotations

import json
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
from lib.realverify import ledger, runner, sched  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
