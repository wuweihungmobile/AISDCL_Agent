#!/usr/bin/env python3
"""WP-SW REQ-CTL-53／54（TCS-Control §8；AT-CTL-115～122）：ack 之後的「封存後事件」摘要與機械層第 3／4 欄。

WHY（暴露證據）：交接包封存之後發生的事（keepwarm 主載具被殺、帳號切換、舊哨兵崩潰）新主控只能手翻痕跡；
機械層第 4 欄只看 `--points-at HEAD`，`406454ea-…-flk5-halfwork`（stash create 的 commit，不在 HEAD）只活在手寫層。
縫：FS（tmp 痕跡與交接包）、假 job_table、假行程查詢（PROC）、真 git（沙盒倉庫）。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from lib.sessionctl import ackevents, ackhook, handoff_build  # noqa: E402

OWNER = "406454ea-91fc-4481-9c11-b28ed7d9e95f"
OTHER = "4290bf58-a5e9-4e64-b118-e9db87ca2af4"
ACKER = "bbbbbbbb-1111-2222-3333-444444444444"
SEALED = datetime(2026, 11, 26, 23, 47, 36).astimezone()


def _ev(event: str, minutes_after: float, sid: str = OWNER, **kw) -> dict:
    return {"event": event, "at": (SEALED + timedelta(minutes=minutes_after)).isoformat(), "sid": sid, **kw}


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="wpsw-ae-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.traces = self.tmp / "traces"
        self.traces.mkdir()
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.traces)})
        patch.start()
        self.addCleanup(patch.stop)
        self.pkg = self.tmp / f"{OWNER}_20261126T154649Z.md"
        self.pkg.write_text(f"# x <!-- sessionctl-handoff sid={OWNER} at=x -->\n", encoding="utf-8")
        self.pkg.with_suffix(".sealed").write_text(SEALED.isoformat() + "\n", encoding="utf-8")

    def write_trace(self, *rows: dict) -> None:
        with (self.traces / "autosdd_session_switch.jsonl").open("w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)

    def summary(self, **kw) -> str:
        kw.setdefault("proc_fn", lambda _sid: ("alive", 4242))
        kw.setdefault("table", [])
        return ackevents.summary(self.pkg, ACKER, os.environ, **kw)


class SummaryTest(_Fence):
    def test_at_ctl_115_only_owner_after_seal_in_prefix_whitelist_ascending(self) -> None:
        self.write_trace(
            _ev("park_armed", -30),                                  # 封存戳之前 ⇒ 不列
            _ev("keepwarm_verdict", 5, verdict="cap"),
            _ev("account_switch", 60, old="eaf5241f6fe2", new="34cd3507237f"),
            _ev("park_early_probe", 20, reason="unmeasured"),
            _ev("account_switch", 30, sid=OTHER, old="x", new="y"),  # 他 sid ⇒ 不列
            _ev("context_budget_note", 40),                          # 前綴白名單外 ⇒ 不列
            _ev("sentinel_crashed", 90, exc_type="AttributeError"))
        text = self.summary()
        body = text.split("② ")[0]
        self.assertIn("eaf5241f6fe2", body)
        self.assertNotIn("park_armed", body)
        self.assertNotIn("context_budget_note", body)
        self.assertNotIn("old=x", body)
        order = [body.index(w) for w in ("keepwarm_verdict", "park_early_probe", "account_switch", "sentinel_crashed")]
        self.assertEqual(order, sorted(order), "依時間升冪")

    def test_at_ctl_115_over_forty_rows_say_how_many_were_cut(self) -> None:
        self.write_trace(*[_ev("watch_tick", n + 1) for n in range(45)])
        self.assertIn("已截斷 5 列", self.summary())

    def test_at_ctl_116_old_sentinel_state_is_quoted_verbatim_including_empty_values(self) -> None:
        row = {"name": f"AutoSDD_Sentinel_{OWNER}", "sid": OWNER, "state": "Ready", "last_run": "2026-11-28T10:21:52+08:00",
               "last_result": 1, "next_run": ""}
        text = self.summary(table=[row])
        for needle in ("State=Ready", "LastTaskResult=1", "LastRunTime=2026-11-28T10:21:52+08:00", "NextRunTime="):
            self.assertIn(needle, text)
        self.assertNotIn("已排程", text, "空 NextRunTime 不得美化成已排程")
        self.assertIn("量不到：排程器狀態列舉回 None", self.summary(table=None))

    def test_at_ctl_117_old_window_three_states(self) -> None:
        self.assertIn("仍在（pid 4242", self.summary(proc_fn=lambda _s: ("alive", 4242)))
        self.assertIn("已不在", self.summary(proc_fn=lambda _s: ("dead", None)))
        self.assertIn("量不到：身分驗不出", self.summary(proc_fn=lambda _s: ("unknown", "身分驗不出")))
        self.assertIn("量不到：RuntimeError", self.summary(proc_fn=mock.Mock(side_effect=RuntimeError("x"))))

    def test_at_ctl_118_read_only_and_never_fatal_through_the_hook(self) -> None:
        self.write_trace(_ev("park_acked_cancel", 70, acker=ACKER))

        def digest() -> str:
            h = hashlib.sha256()
            for p in sorted(self.tmp.rglob("*"), key=lambda q: q.as_posix()):
                if p.is_file():
                    h.update(p.name.encode() + p.read_bytes())
            return h.hexdigest()

        before = digest()
        text = self.summary()
        self.assertEqual(digest(), before, "summary 只讀")
        self.assertIn("④ 本次 ack 撤銷了", text, "撤 park 的事實出現在摘要④")
        err = io.StringIO()
        with mock.patch.object(ackevents, "summary", side_effect=RuntimeError("boom")), \
                redirect_stderr(err), redirect_stdout(io.StringIO()):
            ackhook.summarize_and_gc(self.pkg, ACKER, os.environ, table=[])
        self.assertIn("不影響接手", err.getvalue())

    def test_at_ctl_118_budget_truncates_instead_of_blocking(self) -> None:
        self.write_trace(*[_ev("watch_tick", n + 1) for n in range(5)])
        with mock.patch.object(ackevents, "ACK_SUMMARY_BUDGET_S", -1.0):
            text = self.summary()
        self.assertIn("逾預算，已截斷", text)

    def test_at_ctl_119_after_handoff_output_and_rc_unchanged(self) -> None:
        """AT-CTL-119：after_handoff 只在 ack 原輸出之後多印；rc 原樣；失敗的 ack 不摘要。"""
        with mock.patch.object(ackhook, "summarize_and_gc") as gc, mock.patch.object(ackhook, "on_ack"):
            self.assertEqual(ackhook.after_handoff(["--ack", str(self.pkg)], 0, {"CLAUDE_CODE_SESSION_ID": ACKER}), 0)
            self.assertEqual(ackhook.after_handoff(["--ack", str(self.pkg)], 1, {}), 1)
        gc.assert_called_once()


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
                         capture_output=True, text=True, encoding="utf-8", check=True, stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return out.stdout.strip()


class MechanicalColumnsTest(unittest.TestCase):
    """AT-CTL-120～122（沙盒真 git 倉庫）。"""

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="wpsw-git-")
        self.addCleanup(holder.cleanup)
        self.repo = Path(holder.name)
        _git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "a.txt").write_text("1", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "c1")
        (self.repo / "a.txt").write_text("2", encoding="utf-8")
        self.stash = _git(self.repo, "stash", "create")  # 真 stash create：commit 不在 HEAD
        (self.repo / "a.txt").write_text("1", encoding="utf-8")  # 工作樹還原回 HEAD 內容（不用毀滅性 git）
        _git(self.repo, "tag", "406454ea-20261126-flk5-halfwork", self.stash)
        _git(self.repo, "tag", "406454ea-x-wip-preserved")
        _git(self.repo, "tag", "dddddddd-20261126-other-halfwork", self.stash)
        _git(self.repo, "tag", "unrelated-tag")

    def runner(self, argv, cwd=None, **_kw):
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", cwd=cwd,
                              stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return proc.returncode, proc.stdout, None

    def test_at_ctl_121_column4_lists_own_halfwork_and_wip_preserved_only(self) -> None:
        head = _git(self.repo, "rev-parse", "HEAD")
        rows, why = handoff_build.owner_tags(self.runner, self.repo, OWNER, head)
        self.assertEqual(why, "")
        joined = "\n".join(rows)
        self.assertIn("406454ea-20261126-flk5-halfwork → " + self.stash[:12], joined)
        self.assertIn("（不在 HEAD）", rows[0] if "halfwork" in rows[0] else rows[1])
        self.assertIn("406454ea-x-wip-preserved", joined)
        self.assertNotIn("dddddddd", joined)
        self.assertNotIn("unrelated", joined)
        _b, _t, tag_text = handoff_build._git_sections(self.runner, self.repo, OWNER)  # noqa: SLF001
        self.assertIn("本 owner 保全標籤：406454ea-20261126-flk5-halfwork", tag_text)
        _b, _t, none_text = handoff_build._git_sections(self.runner, self.repo, "zzzzzzzz-0000")  # noqa: SLF001
        self.assertNotIn("本 owner 保全標籤", none_text, "別的 sid 沒有自己的保全標籤 ⇒ 不加列")
        self.assertIn("406454ea-x-wip-preserved", none_text, "HEAD 上的 wip-preserved 照舊列在原處")
        self.assertEqual(handoff_build.owner_tags(lambda *_a, **_k: (1, "", None), self.repo, OWNER, None)[0], None)
        self.assertIn("量不到", handoff_build._git_sections(lambda *_a, **_k: (1, "", None), self.repo, OWNER)[2])  # noqa: SLF001

    def test_at_ctl_120_worktree_row_present_and_failure_is_localised(self) -> None:
        _b, tree, _t = handoff_build._git_sections(self.runner, self.repo, OWNER)  # noqa: SLF001
        self.assertIn("git worktree list", tree)
        self.assertIn(str(self.repo.name), tree)

        def runner(argv, cwd=None, **kw):
            return (1, "", None) if "worktree" in argv else self.runner(argv, cwd=cwd, **kw)

        _b, tree, tags = handoff_build._git_sections(runner, self.repo, OWNER)  # noqa: SLF001
        self.assertIn("量不到", tree)
        self.assertIn("本 owner 保全標籤", tags, "其餘欄不受影響")

    def test_at_ctl_122_mech_headings_unchanged(self) -> None:
        self.assertEqual(len(handoff_build.MECH_HEADINGS), 13)
        self.assertIn("wip-preserved 標籤", handoff_build.MECH_HEADINGS[3])


if __name__ == "__main__":
    unittest.main()
