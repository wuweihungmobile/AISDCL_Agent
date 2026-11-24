"""完成閘與周邊（A5；TCS-WorkProgress REQ-WP-09／15／20～22／24／26／58、
AT-WP-03／21～28／57／58／77、
E2E-WP-06（Stop 推回面）／45／49／55 的 hook 子行程面、MU-WP-01／07／15／16）。

WHY：第七類停＝主控說「做完了」、OIR 卻還有沒人驅動的未結項。測的是會讓閘說謊的方向：
判決跟著措辭走、
第二次 Stop 還推、只讀回合被推、OIR 壞掉卻把整個 Stop 阻斷、閘逐列開子行程拖慢到 hook 逾時、
驅動器自己的帳本寫入擋住 spawn／SI 巡邏、純保溫 shell 蓋掉半路停工判準。縫：真檔案系統（暫存根）、
真 hook 子行程（沙盒樹＋junction 指向真 tools）、真 git 工作樹；時鐘以參數注入。

hook 檔 `.claude/hooks/*` 由主控親套 diff；套用前以環境變數 `OPENITEMS_A5_HOOK_DIR`
指向套用後的副本樹
（含 `.claude/hooks/`）。兩者都沒接線時 hook 子行程測試以明確訊息 skip——不是通過。
"""

from __future__ import annotations

import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.openitems import gate, ledger, params  # noqa: E402
from lib.selfimproving import sched  # noqa: E402
from lib.sessionctl import handoff, midwork  # noqa: E402

TZ = timezone(timedelta(hours=8))
SRC = "docs/03_testing/contracts/TCS-WorkProgress-20261119.md:277"
#: Stop 的額度停工推回讀真機額度快取（與本測試無關、隨時變）⇒ 關掉，只留被測的出聲分支。
ISOLATE = {"AUTOSDD_PARK_GUARD_OFF": "1", "AUTOSDD_KEEPWARM_OFF": "1"}


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="oi_gate_"))
    dest = root / params.PARAMS_REL
    dest.parent.mkdir(parents=True)
    shutil.copyfile(_REPO / params.PARAMS_REL, dest)
    return root


def add(root: Path, *rows: dict) -> list[dict]:
    """經真的追加路徑（schema 驗證＋鎖）寫事件；`ts` 缺則補現在。"""
    with mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(root / "_trace")}):
        return ledger.append(root, lambda _events: list(rows))


def open_row(i: int, kind: str = "auto", **kw) -> dict:
    base = {
        "ev": "open",
        "id": f"OI-20261119-{i:03d}",
        "by": "human",
        "title": f"項目{i}",
        "source": SRC,
        "scope": "r217",
        "kind": kind,
        "check": {"realverify": "RV-L1"},
    }
    if kind == "human":
        base.pop("check")
        base["why_not_auto"] = "只有掌舵者能目視確認"
    base.update(kw)
    return base


def drive_row(i: int, seq: int, minutes_ahead: int = 60) -> dict:
    at = (datetime.now(TZ) + timedelta(minutes=minutes_ahead)).isoformat(timespec="seconds")
    return {
        "ev": "drive",
        "id": f"OI-20261119-{i:03d}",
        "by": "driver:t",
        "task": f"AutoSDD_OpenItem_{i}",
        "credential": "NextRunTime=x",
        "at": at,
    }


class _Env(unittest.TestCase):
    def setUp(self) -> None:
        self.root = make_root()
        patcher = mock.patch.dict(
            os.environ,
            {"AUTOSDD_TRACE_DIR": str(self.root / "_trace"), "CLAUDE_PROJECT_DIR": str(self.root)},
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("AUTOSDD_UNATTENDED", None)
        self.addCleanup(shutil.rmtree, self.root, True)


class StopVerdictTest(_Env):
    def test_AT_WP_03_verdict_follows_state_not_wording(self):
        """甲：回覆說沒有剩下要做的事＋1 undriven⇒推回；乙：回覆說接下來要做 X＋全 driven⇒不推；
        對調文字判決不變。"""
        add(self.root, open_row(1))
        undriven = gate.load_state(self.root)
        add(self.root, drive_row(1, 2))
        driven = gate.load_state(self.root)
        for text in ("沒有剩下要做的事，全部完成。", "接下來我要做 X。"):
            payload = {"last_assistant_message": text}
            self.assertIn(
                "OI-20261119-001", gate.stop_verdict(undriven, payload, {}, evidence=True)
            )
            self.assertEqual(gate.stop_verdict(driven, payload, {}, evidence=True), "")

    def test_AT_WP_21_second_stop_passes(self):
        add(self.root, open_row(1))
        st = gate.load_state(self.root)
        self.assertEqual(gate.stop_verdict(st, {"stop_hook_active": True}, {}, evidence=True), "")

    def test_AT_WP_22_unattended_passes(self):
        add(self.root, open_row(1))
        st = gate.load_state(self.root)
        self.assertEqual(gate.stop_verdict(st, {}, {"AUTOSDD_UNATTENDED": "1"}, evidence=True), "")

    def test_AT_WP_23_no_evidence_passes(self):
        add(self.root, open_row(1))
        self.assertEqual(gate.stop_verdict(gate.load_state(self.root), {}, {}, evidence=False), "")

    def test_message_lists_five_and_three_exits(self):
        add(self.root, *[open_row(i) for i in range(1, 8)])
        text = gate.stop_verdict(gate.load_state(self.root), {}, {}, evidence=True)
        self.assertLessEqual(len(text.splitlines()), 8)
        self.assertEqual(sum("OI-20261119-" in ln for ln in text.splitlines()), 5)
        self.assertIn("另 2 項", text)
        for exit_ in ("openitems.py drive", "convert", "AskUserQuestion"):
            self.assertIn(exit_, text)

    def test_AT_WP_28_unreadable_ledger_fails_open_with_stderr(self):
        ledger_dir = params.ledger_path(self.root)
        ledger_dir.mkdir(parents=True)  # 讀檔必失敗（路徑是目錄）
        err = io.StringIO()
        with redirect_stderr(err):
            st = gate.load_state(self.root)
        self.assertIsNone(st)
        self.assertIn("OIR 讀取失敗", err.getvalue())
        self.assertEqual(gate.stop_verdict(st, {}, {}, evidence=True), "")

    def test_AT_WP_57_fifty_rows_zero_subprocess_under_two_seconds(self):
        add(self.root, *[open_row(i) for i in range(1, 51)])
        add(self.root, *[drive_row(i, 0, 60 if i <= 25 else -120) for i in range(1, 51)])
        spawned: list[object] = []
        real = subprocess.Popen

        def counting(*a, **k):
            spawned.append(a)
            return real(*a, **k)

        t0 = time.monotonic()
        with mock.patch.object(subprocess, "Popen", counting):
            st = gate.load_state(self.root)
            gate.stop_verdict(st, {}, {}, evidence=True)
        self.assertEqual(spawned, [], "完成閘判準期間不得開任何子行程")
        self.assertLess(time.monotonic() - t0, 2.0)
        self.assertEqual(len(st.undriven), 25, "觸發後 25 列未接上 start ⇒ undriven")


class MarkerAndNoteTest(_Env):
    def test_AT_WP_27_marker_makes_keepwarm_yield(self):
        self.assertFalse(gate.keepwarm_yields("sbx", gate.load_state(self.root)))
        gate.mark_pushed("sbx")
        self.assertTrue((self.root / "_trace" / "openitems" / "sbx.gate").is_file())
        self.assertTrue(gate.keepwarm_yields("sbx", gate.load_state(self.root)))
        self.assertFalse(gate.keepwarm_yields("other", gate.load_state(self.root)))

    def test_keepwarm_yields_when_ledger_has_undriven_even_without_marker(self):
        add(self.root, open_row(1))
        self.assertTrue(gate.keepwarm_yields("fresh", gate.load_state(self.root)))

    def test_stale_marker_does_not_yield(self):
        gate.mark_pushed("sbx")
        marker = self.root / "_trace" / "openitems" / "sbx.gate"
        old = time.time() - gate.MARKER_FRESH_SECONDS - 60
        os.utime(marker, (old, old))
        self.assertFalse(gate.keepwarm_yields("sbx", gate.load_state(self.root)))

    def test_REQ_WP_15_human_list_caps_and_labels_k1(self):
        rows = [open_row(i, "human") for i in range(1, 9)] + [open_row(9, "k1", why_not_auto=None)]
        rows[-1].pop("check", None)
        rows[-1].pop("why_not_auto")
        add(self.root, *rows)
        lines = gate.human_lines(gate.load_state(self.root))
        self.assertEqual(len(lines), 8)  # 7 項＋「另 k 項」
        self.assertEqual(lines[-1], "另 2 項")
        # k1 是第 9 個（開立最晚）⇒ 落在「另 2 項」內；單獨驗標記
        add(self.root, open_row(10, "k1"))  # 另一個 k1 仍排在最後
        st = gate.load_state(self.root)
        st.human_cap = 20
        self.assertTrue(any("須掌舵者親打" in ln for ln in gate.human_lines(st)))

    def test_REQ_WP_15_cap_note_once_per_session(self):
        add(self.root, *[open_row(i, "human") for i in range(1, 9)])
        st = gate.load_state(self.root)
        first = gate.cap_note(st, "sbx")
        self.assertIn("8 項", first)
        self.assertEqual(gate.cap_note(st, "sbx"), "")
        self.assertIn("8 項", gate.cap_note(st, "another"))

    def test_cap_note_silent_when_within_cap(self):
        add(self.root, *[open_row(i, "human") for i in range(1, 4)])
        self.assertEqual(gate.cap_note(gate.load_state(self.root), "sbx"), "")


class MidworkKeepwarmExclusionTest(unittest.TestCase):
    def _payload(self, *tasks):
        return {"background_tasks": list(tasks)}

    def test_AT_WP_25_keepwarm_shell_does_not_count_as_background_work(self):
        keep = {
            "type": "shell",
            "status": "running",
            "command": "python tools/sessionctl.py keepwarm --sid abc",
        }
        self.assertTrue(
            midwork.background_idle(self._payload(keep))
        )  # MU-WP-01：不排除就會是 False

    def test_AT_WP_26_agent_plus_watch_is_not_idle(self):
        agent = {"type": "agent", "status": "running", "command": ""}
        watch = {
            "type": "shell",
            "status": "running",
            "command": "python tools/sessionctl.py watch --sid abc --stall-min 20",
        }
        self.assertFalse(midwork.background_idle(self._payload(agent, watch)))

    def test_ordinary_shell_still_counts(self):
        shell = {
            "type": "shell",
            "status": "running",
            "command": "python tools/ci_wait.py --commit x",
        }
        self.assertFalse(midwork.background_idle(self._payload(shell)))

    def test_missing_field_stays_not_idle(self):
        self.assertFalse(midwork.background_idle({}))


def _rmtree(path: Path) -> None:
    """含 `git init` 產物的暫存根：.git 內的物件檔唯讀，Windows 上 `ignore_errors` 會留下殘骸。"""

    def _force(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=_force)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "maintenance.auto=false", "-c", "gc.auto=0", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        timeout=60,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


class DriverOwnedSurfaceTest(unittest.TestCase):
    """AT-WP-58／E2E-WP-49（沙盒真 git 工作樹）：驅動器自有面只被兩個消費端排除。受測：
    `tools/lib/openitems/gate.py`、`tools/lib/sessionctl/owned.py`。"""

    OIR = "docs/06_quality/OpenItems_Event_Ledger.jsonl"
    RV = "docs/06_quality/RealVerify_Result_Ledger.md"

    def setUp(self) -> None:
        self.repo = make_root()
        self.addCleanup(_rmtree, self.repo)
        for rel in (self.OIR, self.RV, "tools/x.py"):
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("a\n", encoding="utf-8")
        _git(self.repo, "init", "-q")
        _git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
        _git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
        for rel in (self.OIR, self.RV):
            with (self.repo / rel).open("a", encoding="utf-8") as fh:
                fh.write("b\n")

    def test_AT_WP_58_a_only_driver_ledgers_dirty(self):
        self.assertTrue(handoff._auto_owned(f" M {self.OIR}", self.repo))
        self.assertTrue(handoff._auto_owned(f" M {self.RV}", self.repo))
        self.assertEqual(sched.dirty_paths(self.repo), [])  # (d)

    def test_AT_WP_58_b_other_file_refused_by_both(self):
        (self.repo / "tools/x.py").write_text("changed\n", encoding="utf-8")
        self.assertFalse(handoff._auto_owned(" M tools/x.py", self.repo))
        self.assertEqual(sched.dirty_paths(self.repo), ["tools/x.py"])

    def test_AT_WP_58_c_unreadable_params_means_no_exclusion(self):
        (self.repo / params.PARAMS_REL).unlink()
        self.assertFalse(handoff._auto_owned(f" M {self.OIR}", self.repo))
        dirty = sched.dirty_paths(self.repo)
        self.assertIn(self.OIR, dirty)
        self.assertIn(self.RV, dirty)

    def test_si_own_prefixes_do_not_absorb_driver_ledgers(self):
        """REQ-WP-09：驅動器自有面不併入 SI 的 OWN_PREFIXES（SI 提交白名單語意不變）。"""
        self.assertFalse(
            any(self.OIR.startswith(p) or self.RV.startswith(p) for p in sched.OWN_PREFIXES)
        )

    def test_mixed_rename_line_needs_both_ends_owned(self):
        self.assertFalse(handoff._auto_owned(f"R  {self.OIR} -> tools/x.py", self.repo))


# ───────────────────────────────────────────── hook 子行程（真 Stop payload）
def _hook_tree() -> Path | None:
    """含 `.claude/hooks/{check_pending_handoff,sessionctl_guard}.py` 且已接線完成閘的樹；沒有回
    None。"""
    candidates = (
        [Path(os.environ["OPENITEMS_A5_HOOK_DIR"])]
        if os.environ.get("OPENITEMS_A5_HOOK_DIR")
        else []
    )
    candidates.append(_REPO)
    for base in candidates:
        hook = base / ".claude" / "hooks" / "check_pending_handoff.py"
        if hook.is_file() and "openitems" in hook.read_text(encoding="utf-8"):
            return base
    return None


def _link(target: Path, link: Path) -> None:
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
            timeout=60,
        )
    else:
        os.symlink(target, link, target_is_directory=True)


def _unlink(link: Path) -> None:
    try:
        os.rmdir(link) if os.name == "nt" else os.unlink(link)  # 只拆連結本身，絕不 rmtree 穿過它
    except OSError:
        pass


class HookProcessTest(_Env):
    """真 hook 子行程吃 Stop payload＋沙盒 OIR（E2E-WP-06 推回面、E2E-WP-45、
    E2E-WP-55 的 hook 面）。
    真 `claude -p` 載具的完整變體歸 A6（RV-WP 案例）；
    這裡驗被測入口：真 hook 行程的 stdout 與 rc。"""

    def setUp(self) -> None:
        super().setUp()
        base = _hook_tree()
        # A5 hook 已套用：未接線＝缺陷（紅），不再靜默跳過（跳過＝未驗證，不是通過）
        self.assertIsNotNone(base, "完成閘尚未接線到 .claude/hooks")
        self.tree = Path(tempfile.mkdtemp(prefix="oi_hooktree_"))
        self.addCleanup(shutil.rmtree, self.tree, True)
        (self.tree / ".claude").mkdir()
        shutil.copytree(base / ".claude" / "hooks", self.tree / ".claude" / "hooks")
        self.link = self.tree / "tools"
        _link(_REPO / "tools", self.link)
        self.addCleanup(_unlink, self.link)
        self.transcript = self.root / "t.jsonl"
        rows = [
            {
                "type": "user",
                "origin": {"kind": "human"},
                "message": {"role": "user", "content": "請做事"},
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "name": "Write", "input": {}}],
                },
            },
        ]
        self.transcript.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    def run_hook(self, name: str, payload: dict, extra_env: dict | None = None):
        env = dict(os.environ)
        env.update(extra_env or {})
        return subprocess.run(
            [sys.executable, str(self.tree / ".claude" / "hooks" / name)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            encoding="utf-8",
            env=env,
            timeout=60,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def stop_payload(self, text: str = "全部完成，沒有剩下要做的事。", **kw) -> dict:
        base = {
            "hook_event_name": "Stop",
            "session_id": "sbxsid",
            "transcript_path": str(self.transcript),
            "cwd": str(self.root),
            "last_assistant_message": text,
            "stop_hook_active": False,
        }
        base.update(kw)
        return base

    def test_pushes_once_then_passes_then_quiet_after_drive(self):
        add(self.root, open_row(1))
        first = self.run_hook("check_pending_handoff.py", self.stop_payload())
        self.assertEqual(first.returncode, 0, first.stderr)
        doc = json.loads(first.stdout)
        self.assertEqual(doc["decision"], "block")
        self.assertIn("OI-20261119-001", doc["reason"])
        self.assertTrue((self.root / "_trace" / "openitems" / "sbxsid.gate").is_file())
        second = self.run_hook("check_pending_handoff.py", self.stop_payload(stop_hook_active=True))
        self.assertEqual((second.returncode, second.stdout.strip()), (0, ""))
        add(self.root, drive_row(1, 2))
        third = self.run_hook("check_pending_handoff.py", self.stop_payload())
        self.assertEqual((third.returncode, third.stdout.strip()), (0, ""))

    def test_read_only_turn_is_not_pushed(self):
        add(self.root, open_row(1))
        rows = [
            {
                "type": "user",
                "origin": {"kind": "human"},
                "message": {"role": "user", "content": "問"},
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "tool_use", "name": "Read", "input": {}}],
                },
            },
        ]
        self.transcript.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        out = self.run_hook("check_pending_handoff.py", self.stop_payload(cwd=str(self.tree)))
        self.assertEqual((out.returncode, out.stdout.strip()), (0, ""))

    def test_unattended_is_noop(self):
        add(self.root, open_row(1))
        out = self.run_hook(
            "check_pending_handoff.py", self.stop_payload(), {"AUTOSDD_UNATTENDED": "1"}
        )
        self.assertEqual((out.returncode, out.stdout.strip()), (0, ""))

    def test_E2E_WP_55_attempt_without_followup_is_pushed(self):
        add(self.root, open_row(1))
        past = (datetime.now(TZ) - timedelta(minutes=20)).isoformat(timespec="seconds")
        add(
            self.root,
            {**drive_row(1, 2, -60)},
            {
                "ev": "attempt",
                "id": "OI-20261119-001",
                "by": "driver:t",
                "n": 1,
                "result": "fail",
                "drive_seq": 2,
                "ts": past,
            },
        )
        out = self.run_hook("check_pending_handoff.py", self.stop_payload())
        self.assertEqual(json.loads(out.stdout)["decision"], "block")

    def test_E2E_WP_45_unreadable_oir_passes_with_stderr(self):
        params.ledger_path(self.root).mkdir(parents=True)
        out = self.run_hook("check_pending_handoff.py", self.stop_payload())
        self.assertEqual((out.returncode, out.stdout.strip()), (0, ""))
        self.assertIn("OIR 讀取失敗", out.stderr)

    def test_AT_WP_24_all_three_judgments_merge_into_one_message(self):
        add(self.root, open_row(1))
        text = "接下來我要做 X。這個決定待掌舵者決定。"
        out = self.run_hook(
            "check_pending_handoff.py", self.stop_payload(text, background_tasks=[])
        )
        reason = json.loads(out.stdout)["reason"]
        positions = [reason.find(k) for k in ("接下來還要做事", "散文留給掌舵者", "完成閘")]
        self.assertTrue(all(p >= 0 for p in positions), reason)
        self.assertEqual(positions, sorted(positions), "段落次序 半路停工→散文交棒→完成閘")

    def test_AT_WP_77_notice_voiced_once_by_whichever_hook_comes_first(self):
        from lib.sessionctl import oldwin  # noqa: PLC0415

        oldwin.notice("sbxsid", "已關閉舊視窗 pid=4242（sid abcd1234）")
        first = self.run_hook(
            "sessionctl_guard.py",
            {"hook_event_name": "UserPromptSubmit", "session_id": "sbxsid", "prompt": "hi"},
        )
        self.assertIn("pid=4242", first.stdout)
        second = self.run_hook(
            "sessionctl_guard.py",
            {"hook_event_name": "Stop", "session_id": "sbxsid", "stop_hook_active": False},
            ISOLATE,
        )
        self.assertNotIn("pid=4242", second.stdout)

    def test_guard_stop_voices_notice_when_it_comes_first(self):
        from lib.sessionctl import oldwin  # noqa: PLC0415

        oldwin.notice("sbxsid", "已關閉舊視窗 pid=777（sid abcd1234）")
        out = self.run_hook(
            "sessionctl_guard.py",
            {"hook_event_name": "Stop", "session_id": "sbxsid", "stop_hook_active": False},
            ISOLATE,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("pid=777", out.stdout)


class SessionBriefTest(_Env):
    def test_REQ_WP_15_brief_lines_come_from_oir(self):
        import session_brief_oi as session_brief  # noqa: PLC0415

        add(self.root, open_row(1, "human"))
        self.assertIn("OI-20261119-001", session_brief.openitems_line())

    def test_brief_silent_without_human_rows(self):
        import session_brief_oi as session_brief  # noqa: PLC0415

        self.assertEqual(session_brief.openitems_line(), "")

    def test_AT_WP_77_brief_voices_notice_then_marks_read(self):
        import session_brief_oi as session_brief  # noqa: PLC0415

        from lib.sessionctl import oldwin  # noqa: PLC0415

        oldwin.notice("sidA", "已關閉舊視窗 pid=99（sid 11112222）")
        self.assertIn("pid=99", session_brief.oldwin_line("sidA"))
        self.assertNotIn("pid=99", session_brief.oldwin_line("sidA"))


if __name__ == "__main__":
    unittest.main()
