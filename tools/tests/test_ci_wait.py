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
        self.traces: list[dict] = []

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
        return core.wait(opts, run=self.run, now=self.now, sleep=self.sleep, emit=self.lines.append,
                         trace=self.traces.append)


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

    def test_default_deadline_is_shorter_than_the_main_cache_lifetime(self):
        # WHY：等待若超過主控 1 小時快取壽命，醒來時快取已冷、整包重寫（FR-TW-12）。
        self.assertLess(core.Options(sha=FULL).timeout_min, 60)

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


# 三支真 run（macos-compat-ci，2026-11-24）attempt 1 的 cancelled job：created_at → completed_at。
# 取自 `gh api repos/{owner}/{repo}/actions/runs/<id>/attempts/1/jobs`（唯讀 GET），
# steps／runner_name 同真值。
RECORDED_QUEUE_JOBS = {
    45427135743: ("2026-11-24T15:34:44Z", "2026-11-24T15:49:45Z"),
    45439253352: ("2026-11-24T16:37:16Z", "2026-11-24T16:52:16Z"),
    45456241389: ("2026-11-24T18:08:26Z", "2026-11-24T18:23:26Z"),
}
T_START, T_END = RECORDED_QUEUE_JOBS[45427135743]
T_MID = "2026-11-24T15:40:00Z"


def qjob(created=T_START, completed=T_END, *, conclusion="cancelled",
         steps=None, runner="", branch="main", sha=FULL):
    return {"conclusion": conclusion, "steps": [] if steps is None else steps,
            "runner_name": runner, "created_at": created, "completed_at": completed,
            "head_branch": branch, "head_sha": sha}


def jobs_of(*jobs):
    skipped = qjob(conclusion="skipped", created=T_START, completed=T_START)
    return {"total_count": len(jobs) + 1, "jobs": [*jobs, skipped]}


def verdict_line(w):
    return w.lines[-1]


class QueueTimeoutTest(unittest.TestCase):
    """tools/lib/ciwait/core.py 的排隊逾時自動重跑（REQ-AP-CI-01）：
    只對「cancelled ∧ 零步驟 ∧ runner 未指派 ∧ 14.5～16 分」重跑、次數有上限，
    其餘一律照舊 fail（真紅不得被吸收成綠）。"""

    def test_classify_recorded_attempts(self):
        """AC-CI-01a：三支真 run 命中；有步驟／14 分／16.5 分／有 runner／較新 run 不命中。"""
        for rid, (c, e) in RECORDED_QUEUE_JOBS.items():
            self.assertEqual(core.classify_attempt(jobs_of(qjob(c, e))), "queue_timeout", rid)
        misses = [
            qjob(steps=[{"name": "x"}]), qjob(completed="2026-11-24T15:48:44Z"),
            qjob(completed="2026-11-24T15:51:14Z"), qjob(runner="GitHub Actions 7"),
            qjob(conclusion="failure")]
        for job in misses:
            self.assertEqual(core.classify_attempt(jobs_of(job)), "other", job)
        self.assertEqual(core.classify_attempt(jobs_of(qjob()), newer_run=True), "other")
        for junk in (None, {}, "x", {"jobs": "x"}, [None], {"jobs": [qjob(created="bad")]}):
            self.assertEqual(core.classify_attempt(junk), "other", junk)

    def test_newer_run_on_same_ref_inside_the_window_is_concurrency_not_queue(self):
        job = qjob()
        inside = [{"databaseId": 9, "headSha": OTHER, "createdAt": T_MID}]
        outside = [{"databaseId": 9, "headSha": OTHER, "createdAt": "2026-11-24T16:40:00Z"},
                   {"databaseId": 8, "headSha": FULL, "createdAt": T_MID}]

        def runner(data):
            return lambda argv: (0, json.dumps(data), "")
        self.assertTrue(core.has_newer_run(job, runner(inside)))
        self.assertFalse(core.has_newer_run(job, runner(outside)), "窗外或同 SHA 的 run 不算")
        self.assertTrue(core.has_newer_run(job, lambda argv: (1, "", "boom")), "查不到＝保守當有")

    def _world(self, listing, jobs=None, *, rerun_rc=0, newer=()):
        """路由假世界：`gh run list --commit` 依序回 listing；`gh api` 回 jobs；
        `--branch` 回 newer。"""
        w = _World()
        w.reruns: list[list[str]] = []
        script = list(listing)
        base_run = w.run
        jobs = jobs or jobs_of(qjob())

        def run(argv):
            if argv[:2] == ["gh", "api"]:
                w.gh_calls.append(argv)
                return 0, json.dumps(jobs), ""
            if argv[:3] == ["gh", "run", "rerun"]:
                w.reruns.append(argv)
                return rerun_rc, "", "denied" if rerun_rc else ""
            if "--branch" in argv:
                return 0, json.dumps(list(newer)), ""
            if argv[:3] == ["gh", "run", "list"]:
                step = script.pop(0) if len(script) > 1 else script[0]
                return 0, json.dumps(step), ""
            return base_run(argv)
        w.run = run
        return w

    @staticmethod
    def _q(attempt, status="completed", conclusion="cancelled"):
        return [{**r("macos-compat-ci", status, conclusion, rid=45427135743),
                 "attempt": attempt}]

    def test_rerun_and_exhaustion(self):
        """AC-CI-01b：命中 ⇒ `gh run rerun <id> --failed` 並繼續等，末行
        `pass rerun=queue_timeout×1`；第 3 次排隊逾時 ⇒ `fail reason=queue_timeout_exhausted`
        rc 1，且只重跑過 2 次。"""
        q = self._q
        w = self._world([q(1), q(2, "in_progress", None), q(2, conclusion="success")])
        self.assertEqual(w.wait(interval_sec=30), core.EXIT_PASS)
        self.assertEqual(w.reruns, [["gh", "run", "rerun", "45427135743", "--failed"]])
        self.assertTrue(verdict_line(w).startswith(
            "CI_WAIT_VERDICT=pass rerun=queue_timeout×1 sha="), verdict_line(w))
        self.assertEqual(len(w.traces), 1)
        self.assertEqual((w.traces[0]["event"], w.traces[0]["run"], w.traces[0]["attempt"]),
                         ("ci_queue_timeout", 45427135743, 1))
        self.assertAlmostEqual(w.traces[0]["minutes"], 15.02, places=1)
        w = self._world([q(1), q(2), q(3)])
        self.assertEqual(w.wait(interval_sec=30), core.EXIT_FAIL)
        self.assertEqual(len(w.reruns), core.QUEUE_RERUN_MAX)
        self.assertTrue(verdict_line(w).startswith(
            "CI_WAIT_VERDICT=fail reason=queue_timeout_exhausted sha="), verdict_line(w))

    def test_stale_listing_right_after_rerun_does_not_rerun_twice(self):
        """rerun 後 GitHub 可能仍短暫列出同一 attempt 的 cancelled；同 (run, attempt) 不得
        重跑第二次。"""
        q = self._q
        w = self._world([q(1), q(1), q(1), q(2, conclusion="success")])
        self.assertEqual(w.wait(interval_sec=30), core.EXIT_PASS)
        self.assertEqual(len(w.reruns), 1)

    def test_real_failures_are_never_absorbed_into_a_rerun(self):
        """有步驟的 cancelled（真取消）、failure、「排隊逾時＋真失敗」並存、同 ref 有較新 run：
        一律 fail 且 0 次重跑。"""
        w = self._world([self._q(1)], jobs_of(qjob(steps=[{"name": "checkout"}])))
        self.assertEqual(w.wait(), core.EXIT_FAIL)
        self.assertEqual(w.reruns, [])
        self.assertEqual(verdict_line(w), f"CI_WAIT_VERDICT=fail sha={FULL} runs=1")
        w = self._world([self._q(1, conclusion="failure")])
        self.assertEqual(w.wait(), core.EXIT_FAIL)
        self.assertEqual(w.reruns, [])
        mixed = self._q(1) + [r("other-wf", conclusion="failure", rid=2)]
        w = self._world([mixed])
        self.assertEqual(w.wait(), core.EXIT_FAIL)
        self.assertEqual(w.reruns, [])
        newer = [{"databaseId": 9, "headSha": OTHER, "createdAt": T_MID}]
        w = self._world([self._q(1)], newer=newer)
        self.assertEqual(w.wait(), core.EXIT_FAIL, "同 ref 較新 run＝concurrency 自取消")
        self.assertEqual(w.reruns, [])

    def test_rerun_command_failure_degrades_to_plain_fail(self):
        w = self._world([self._q(1)], rerun_rc=1)
        self.assertEqual(w.wait(), core.EXIT_FAIL)
        self.assertTrue(verdict_line(w).startswith(f"CI_WAIT_VERDICT=fail sha={FULL}"))
        self.assertEqual(w.traces, [], "重跑沒成功就不落命中痕跡")

    def test_default_trace_lands_in_the_trace_dir(self):
        import os
        import tempfile
        row = {"event": "ci_queue_timeout", "run": 1, "attempt": 1, "minutes": 15.0}
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": td}):
            core._trace_default(row)
            text = (Path(td) / "autosdd_ci_queue.jsonl").read_text(encoding="utf-8")
        self.assertEqual(json.loads(text.splitlines()[0])["event"], "ci_queue_timeout")


_FAKE_GH_SITE = '''
"""sitecustomize 注入真 ci_wait 行程：攔 gh 呼叫，重放錄製的真實 JSON 形狀。"""
import json, os, subprocess
_real = subprocess.run
_state = {"lists": 0}
_SHA = os.environ["FAKE_SHA"]
_LOG = os.environ["FAKE_LOG"]
_T0, _T1 = "2026-11-24T15:34:44Z", "2026-11-24T15:49:45Z"

def _job(conclusion, end):
    return {"conclusion": conclusion, "steps": [], "runner_name": "",
            "head_branch": "main", "head_sha": _SHA, "created_at": _T0, "completed_at": end}

def _jobs():
    return {"total_count": 2, "jobs": [_job("cancelled", _T1), _job("skipped", _T0)]}

def _done(argv, out="", rc=0, err=""):
    return subprocess.CompletedProcess(argv, rc, out, err)

def _fake(argv, *a, **kw):
    if argv and argv[0] == "gh":
        with open(_LOG, "a", encoding="utf-8") as fh:
            fh.write(" ".join(argv) + "\\n")
        if argv[1:3] == ["run", "list"] and "--commit" in argv:
            _state["lists"] += 1
            done = _state["lists"] >= 3
            row = {"databaseId": 45427135743, "workflowName": "macos-compat-ci",
                   "headSha": _SHA, "status": "completed", "attempt": 2 if done else 1,
                   "conclusion": "success" if done else "cancelled"}
            return _done(argv, json.dumps([row]))
        if argv[1] == "api":
            return _done(argv, json.dumps(_jobs()))
        if argv[1:3] == ["run", "list"]:
            return _done(argv, "[]")
        if argv[1:3] == ["run", "rerun"]:
            return _done(argv)
        return _done(argv, rc=1, err="unexpected gh call")
    return _real(argv, *a, **kw)

subprocess.run = _fake
'''


class QueueTimeoutRealProcessTest(unittest.TestCase):
    """E2E-AP-CI-01：真 `tools/ci_wait.py` 行程（真 git rev-parse、真 default_runner、
    真 argparse），gh 呼叫由 sitecustomize 重放錄製形狀；不碰真 GitHub、不做任何寫操作。"""

    def test_real_process_reruns_once_then_passes(self):
        import os
        import tempfile
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             encoding="utf-8", cwd=_REPO_ROOT, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as td:
            Path(td, "sitecustomize.py").write_text(_FAKE_GH_SITE, encoding="utf-8")
            log = Path(td, "gh.log")
            env = {**os.environ, "PYTHONPATH": td, "FAKE_SHA": sha, "FAKE_LOG": str(log),
                   "PYTHONUTF8": "1", "AUTOSDD_TRACE_DIR": td}
            proc = subprocess.run(
                [sys.executable, str(_REPO_ROOT / "tools" / "ci_wait.py"), "--commit", "HEAD",
                 "--interval-sec", "0.05", "--timeout-min", "2"],
                capture_output=True, encoding="utf-8", env=env, cwd=_REPO_ROOT,
                timeout=120, check=False)
            calls = log.read_text(encoding="utf-8").splitlines()
            trace = Path(td, "autosdd_ci_queue.jsonl").read_text(encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        last = proc.stdout.strip().splitlines()[-1]
        self.assertTrue(last.startswith("CI_WAIT_VERDICT=pass rerun=queue_timeout×1 sha="), last)
        reruns = [c for c in calls if " rerun " in c]
        self.assertEqual(reruns, ["gh run rerun 45427135743 --failed"])
        self.assertIn('"event": "ci_queue_timeout"', trace)


if __name__ == "__main__":
    unittest.main()
