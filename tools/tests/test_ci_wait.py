"""推送後等 CI 工具 `tools/lib/ciwait/core.py` 與入口 `tools/ci_wait.py` 的行為鎖。

立案事故（sid 680d8411，2026-11-14）：手寫輪詢用短 SHA 查 `gh run list` 得 `[]` 且 rc=0，結束條件
永不成立，CI 全綠後主控仍閒置 78 分鐘。本檔每條測試守的是「結束條件由值決定、不由 rc 決定」
與「迴圈自帶截止時間」；外部指令、時鐘、睡眠全部注入，不外呼、不真睡。
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from lib.ciwait import core  # noqa: E402

FULL = "43b4b0f9" + "a" * 32
OTHER = "deadbeef" + "b" * 32


class _World:
    """假的外部世界：假時鐘（睡眠推進它）＋可程式化的 git／gh 回應。"""

    def __init__(self, script=None, gh_exc=None):
        self.t = datetime(2026, 11, 14, 20, 52, tzinfo=UTC)
        # 每次 gh 查詢依序回的 runs（list）或 Exception／None＝gh 失敗
        self.script = list(script or [])
        self.gh_exc = gh_exc
        self.gh_calls: list[list[str]] = []
        self.git_calls: list[list[str]] = []
        self.lines: list[str] = []

    def now(self):
        return self.t

    def sleep(self, sec):
        self.t += timedelta(seconds=sec)

    def run(self, argv):
        if argv[0] == "git":
            self.git_calls.append(argv)
            return 0, FULL + "\n", ""
        self.gh_calls.append(argv)
        if self.gh_exc:
            raise self.gh_exc
        last = self.script[0] if self.script else []
        step = self.script.pop(0) if len(self.script) > 1 else last
        if step is None:
            return 1, "", "HTTP 401"
        return 0, json.dumps(step), ""

    def wait(self, **kw):
        opts = core.Options(sha=FULL, **kw)
        return core.wait(opts, run=self.run, now=self.now, sleep=self.sleep, emit=self.lines.append)


def r(name, status="completed", conclusion="success", rid=1, sha=FULL):
    return {"databaseId": rid, "workflowName": name, "status": status,
            "conclusion": conclusion, "headSha": sha}


class ExitCodeTest(unittest.TestCase):
    def test_four_exit_codes_are_distinct_and_last_line_names_the_verdict(self):
        """四種結果的 rc 互不相同；最後一行恆為 `CI_WAIT_VERDICT=`（呼叫端只讀這一行就夠）。"""
        cases = {
            core.EXIT_PASS: ([[r("a"), r("b")]], "pass"),
            core.EXIT_FAIL: ([[r("a"), r("b", conclusion="failure")]], "fail"),
            core.EXIT_TIMEOUT: ([[r("a"), r("b", "in_progress", None)]], "timeout"),
            core.EXIT_NO_RUNS: ([[]], "no-runs"),
        }
        seen = {}
        for want, (script, verdict) in cases.items():
            w = _World(script)
            rc = w.wait(timeout_min=10, interval_sec=60, grace_min=2)
            seen[rc] = w.lines[-1]
            self.assertEqual(rc, want, verdict)
            want = f"CI_WAIT_VERDICT={verdict} sha={FULL} runs={len(script[0])}"
            self.assertEqual(w.lines[-1], want)
        self.assertEqual(sorted(seen), [0, 1, 2, 3])

    def test_skipped_and_neutral_count_as_pass_but_cancelled_does_not(self):
        """GitHub 把 skipped／neutral 當通過；cancelled 是失敗（否則取消的 run 會被讀成綠）。"""
        w = _World([[r("a", conclusion="skipped"), r("b", conclusion="neutral", rid=2)]])
        self.assertEqual(w.wait(), core.EXIT_PASS)
        w = _World([[r("a", conclusion="cancelled")]])
        self.assertEqual(w.wait(), core.EXIT_FAIL)
        self.assertIn("gh run view 1 --log-failed", w.lines[-2])

    def test_waits_while_pending_then_passes(self):
        """前幾輪還有 in_progress ⇒ 繼續等、每輪睡 interval，最終全過回 0；每輪都印心跳。"""
        w = _World([[r("a", "in_progress", None)], [r("a", "in_progress", None)], [r("a")]])
        self.assertEqual(w.wait(interval_sec=30), core.EXIT_PASS)
        self.assertEqual(len(w.gh_calls), 3)
        self.assertEqual(len([ln for ln in w.lines if "完成" in ln]), 3)
        self.assertTrue(all(ln.startswith("[2026-11-14T") and "+00:00]" in ln
                            for ln in w.lines[:-1]), "心跳帶 offset 的時間戳")


class IncidentShapesTest(unittest.TestCase):
    def test_short_sha_is_resolved_to_full_sha_before_gh_is_asked(self):
        """事故形狀一：`gh run list --commit <短 SHA>` 回 `[]` 且 rc=0。短 SHA 進來必須先經
        `git rev-parse` 解成完整 SHA，gh 只准看到完整 SHA。"""
        calls: list[list[str]] = []

        def run(argv):
            calls.append(argv)
            return 0, FULL + "\n", ""

        sha, err = core.resolve_sha("43b4b0f9", run)
        self.assertEqual((sha, err), (FULL, ""))
        self.assertEqual(calls[0][:3], ["git", "rev-parse", "--verify"])
        self.assertEqual(calls[0][3], "43b4b0f9^{commit}")
        w = _World([[r("a")]])
        w.wait()
        self.assertEqual(w.gh_calls[0][w.gh_calls[0].index("--commit") + 1], FULL)

    def test_zero_runs_after_grace_ends_as_no_runs_instead_of_waiting_forever(self):
        """事故形狀二：查詢 rc=0 但永遠 0 支 run。超過 grace 即 no-runs 結束，遠早於 timeout。"""
        w = _World([[]])
        rc = w.wait(timeout_min=40, interval_sec=60, grace_min=5)
        self.assertEqual(rc, core.EXIT_NO_RUNS)
        self.assertIn("查不到任何 run", w.lines[-2])
        self.assertLess((w.t - datetime(2026, 11, 14, 20, 52, tzinfo=UTC)).total_seconds(), 7 * 60)

    def test_unresolvable_rev_is_exit_3(self):
        sha, err = core.resolve_sha("nope", lambda argv: (128, "", "fatal: bad revision"))
        self.assertIsNone(sha)
        self.assertIn("解不出提交", err)
        sha, err = core.resolve_sha("--upload-pack=x", lambda argv: (0, FULL, ""))
        self.assertIsNone(sha)
        buf = io.StringIO()
        sys.path.insert(0, str(_REPO_ROOT / "tools"))
        import ci_wait  # 薄殼
        with mock.patch.object(core, "default_runner", lambda argv: (128, "", "bad")), \
                redirect_stdout(buf):
            self.assertEqual(ci_wait.main(["--commit", "nope"]), core.EXIT_NO_RUNS)
        self.assertIn("CI_WAIT_VERDICT=no-runs", buf.getvalue())


class EntryPointTest(unittest.TestCase):
    def test_entry_point_passes_the_resolved_full_sha_to_wait(self):
        """入口把 `--commit <短 SHA>` 解成完整 SHA 才交給 wait（事故一在入口層的鎖）。"""
        import ci_wait
        got = {}

        def fake_wait(opts, **kw):
            got["sha"] = opts.sha
            return core.EXIT_PASS

        with mock.patch.object(core, "default_runner", lambda argv: (0, FULL + "\n", "")), \
                mock.patch.object(core, "wait", fake_wait):
            self.assertEqual(ci_wait.main(["--commit", "43b4b0f9"]), core.EXIT_PASS)
        self.assertEqual(got["sha"], FULL)


class RobustnessTest(unittest.TestCase):
    def test_timeout_is_a_hard_cap_and_lists_the_running_workflows(self):
        w = _World([[r("a"), r("slow", "in_progress", None, rid=2)]])
        rc = w.wait(timeout_min=3, interval_sec=60)
        self.assertEqual(rc, core.EXIT_TIMEOUT)
        self.assertIn("slow", w.lines[-2])
        started = datetime(2026, 11, 14, 20, 52, tzinfo=UTC)
        self.assertLessEqual((w.t - started).total_seconds(), 3 * 60)

    def test_foreign_head_sha_rows_are_dropped_even_if_gh_returned_them(self):
        """不相信 gh 的過濾：headSha 不等於完整 SHA 的筆一律丟掉（否則別筆提交的綠燈會混入）。"""
        w = _World([[r("a", sha=OTHER), r("b")]])
        self.assertEqual(w.wait(), core.EXIT_PASS)
        self.assertEqual(w.lines[-1], f"CI_WAIT_VERDICT=pass sha={FULL} runs=1")

    def test_rerun_takes_the_latest_run_per_workflow(self):
        """同一 workflow 重跑：先失敗後成功 ⇒ 以較新（databaseId 大）的那筆為準。"""
        w = _World([[r("a", conclusion="failure", rid=1), r("a", conclusion="success", rid=9)]])
        self.assertEqual(w.wait(), core.EXIT_PASS)
        w = _World([[r("a", conclusion="success", rid=1), r("a", conclusion="failure", rid=9)]])
        self.assertEqual(w.wait(), core.EXIT_FAIL)

    def test_missing_gh_is_exit_3_immediately_without_retry(self):
        w = _World([[]], gh_exc=FileNotFoundError("gh"))
        self.assertEqual(w.wait(), core.EXIT_NO_RUNS)
        self.assertEqual(len(w.gh_calls), 1)
        self.assertIn("找不到 gh", w.lines[-2])

    def test_persistent_query_failure_gives_up_after_the_named_limit(self):
        """gh 未登入（rc≠0）是永久性的：連續 N 次失敗就結束，不得無限重試。"""
        w = _World([None])
        self.assertEqual(w.wait(timeout_min=999), core.EXIT_NO_RUNS)
        self.assertEqual(len(w.gh_calls), core.MAX_CONSECUTIVE_QUERY_FAILURES)

    def test_a_transient_failure_resets_the_counter(self):
        w = _World([None, None, [r("a", "in_progress", None)], None, [r("a")]])
        self.assertEqual(w.wait(), core.EXIT_PASS)

    def test_non_json_output_is_a_query_failure_not_a_crash(self):
        runs, err, fatal = core.query_runs(FULL, lambda argv: (0, "<html>", ""))
        self.assertIsNone(runs)
        self.assertFalse(fatal)
        self.assertIn("不是 JSON", err)
        runs, err, _ = core.query_runs(FULL, lambda argv: (0, '{"a": 1}', ""))
        self.assertIsNone(runs)

    def test_expect_requires_at_least_n_runs_and_workflow_filter_requires_each_name(self):
        w = _World([[r("a")]])
        self.assertEqual(w.wait(expect=2, grace_min=1, interval_sec=30), core.EXIT_NO_RUNS)
        self.assertIn("--expect", w.lines[-2])
        w = _World([[r("a"), r("b", conclusion="failure", rid=2)]])
        self.assertEqual(w.wait(workflows=("a",)), core.EXIT_PASS, "沒被點名的 b 不算")
        w = _World([[r("a")]])
        self.assertEqual(w.wait(workflows=("a", "ghost"), grace_min=1, interval_sec=30),
                         core.EXIT_NO_RUNS)
        self.assertIn("ghost", w.lines[-2])


class RealRunnerTest(unittest.TestCase):
    def test_default_runner_decodes_utf8_and_spawns_without_a_console_window(self):
        """default_runner 用 argv list、UTF-8、no-window 旗標（跨平台紀律）；不外呼真指令。"""
        with mock.patch.object(subprocess, "run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, "ok", "")
            self.assertEqual(core.default_runner(["gh", "x"]), (0, "ok", ""))
        kw = m.call_args.kwargs
        self.assertEqual(kw["encoding"], "utf-8")
        self.assertFalse(kw["shell"])
        self.assertEqual(kw["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0))


if __name__ == "__main__":
    unittest.main()
