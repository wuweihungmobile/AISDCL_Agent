"""realverify 函式庫判準的單元測試（假逐字稿；**不算 E2E**，E2E 是 realverify run 本身）。

WHY：載具自己的判準寫錯會讓整批 E2E 假綠，所以記錄格式斷言、清理邊界、排程名前綴、
runner rc 對映都要有可失敗的測試。
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TOOLS = Path(__file__).resolve().parents[1]
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from lib.realverify import cases as rv_cases  # noqa: E402
from lib.realverify import ledger, runner, sched  # noqa: E402
from lib.realverify.driver import EnvMissing  # noqa: E402
from lib.realverify.sandbox import (  # noqa: E402
    PROBE_HOOK_SRC,
    Sandbox,
    cleanup_handoff_for,
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
