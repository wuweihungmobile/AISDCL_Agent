#!/usr/bin/env python3
"""`refresh_nightly_anchor.py` 回歸鎖（ONBOARDING 表③ nightly 錨的機械回填）。
執行：cd tools/tests && python -m unittest test_refresh_nightly_anchor"""
from __future__ import annotations

import datetime
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import refresh_nightly_anchor as RNA  # noqa: E402

_NOW = datetime.datetime(2026, 10, 8, 12, tzinfo=datetime.UTC)
_SHA = "ab" * 20
#: a／b＝兩個排程 fail-open job；c＝三個誘餌（非排程／非 fail-open／有排程 if 卻無 fail-open）。
_WF = {
    "a.yml": "jobs:\n  ja:\n    name: Job A（深度）\n    if: github.event_name == 'schedule'\n"
             "    continue-on-error: true\n",
    "b.yml": "jobs:\n  jb:\n    name: \"Job B\"  # 引號＋註解\n"
             "    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'\n"
             "    continue-on-error: true  # 非阻斷\n",
    "c.yml": "jobs:\n  push-only:\n    continue-on-error: true\n  label-only:\n    name: L\n"
             "    if: github.event.label.name == 'x'\n    continue-on-error: true\n  alert:\n"
             "    if: always() && github.event_name == 'schedule'\n    runs-on: x\n",
}


def _run(i, created, event="schedule", conclusion="success", status="completed"):
    return {"databaseId": i, "headSha": _SHA, "conclusion": conclusion, "createdAt": created,
            "event": event, "status": status}


def _jobs(*pairs):  # pairs：(name, conclusion)
    return json.dumps({"jobs": [{"name": n, "conclusion": c} for n, c in pairs]})


_TABLE = {  # a 的 schedule 較早、b 的較晚；a 另有更舊的 dispatch
    ("a.yml", "schedule"): json.dumps([_run(101101, "2026-10-05T14:26:01Z")]),
    ("a.yml", "workflow_dispatch"): json.dumps(
        [_run(100100, "2026-09-26T02:37:29Z", "workflow_dispatch")]),
    ("b.yml", "schedule"): json.dumps([_run(201201, "2026-10-05T15:59:48Z")]),
    ("b.yml", "workflow_dispatch"): "[]",
    ("view", "101101"): _jobs(("Job A（深度）", "success"), ("other", "neutral")),
    ("view", "201201"): _jobs(("Job B", "success")),
}
_ONB = (  # 最小的表③-b ＋錨（舊值：run 111111、2026-09-01）
    "intro\n> | job id | workflow | 結論 | run id ／ commit | 判讀 |\n> |---|---|---|---|---|\n"
    "> | `old` | a.yml | ✅ success | `111111` ／ `00000000` | stale |\ntail\n"
    f"> <!-- cloud-ci-status: checked-at=2026-09-21T00:44:53+08:00 head-sha={_SHA} red=none "
    "nightly-red=none nightly-run=111111 nightly-checked-at=2026-09-01T00:00:00+00:00 ／ x -->\n")


def _gh(table, calls=None):
    """依 argv 回固定 JSON 並記錄呼叫（供「只打唯讀指令」斷言）。"""
    def call(args):
        if calls is not None:
            calls.append(list(args))
        if list(args[:2]) == ["run", "list"]:
            return table[(args[args.index("--workflow") + 1], args[args.index("--event") + 1])]
        return table[("view", str(args[2]))]
    return call


def _main(*argv, **kw):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = RNA.main(list(argv), **kw)
    return rc, out.getvalue(), err.getvalue()


class TestRefreshNightlyAnchor(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = self.wd = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name, body in _WF.items():
            (self.wd / name).write_text(body, encoding="utf-8", newline="\n")
        self.onb = self.dir / "onb.md"
        self.onb.write_bytes(_ONB.encode("utf-8"))
        self.pairs = RNA.scheduled_fail_open_jobs(self.wd)
        self.samples = self._fetch()
        self.kw = {"now": _NOW, "onboarding": self.onb, "workflows_dir": self.wd}
        self.fresh = RNA.rewrite_onboarding(_ONB, self.samples)

    def _fetch(self, **override):
        table = {**_TABLE, **{tuple(k.split("|")): v for k, v in override.items()}}
        return RNA.fetch_samples(self.pairs, self.wd, _gh(table))

    def _problems(self, text, now=_NOW):
        return " ".join(RNA.anchor_problems(text, now, self.pairs))

    def test_render_is_a_pure_function_of_the_github_state(self) -> None:
        """輸出只由 GitHub 狀態決定：換本機時鐘結果逐位元相同，否則兩台機器每週衝突。"""
        other = self.dir / "other.md"
        other.write_bytes(_ONB.encode("utf-8"))
        later = {**self.kw, "onboarding": other, "now": _NOW + datetime.timedelta(days=2)}
        gh = _gh(_TABLE, calls := [])
        rcs = (_main("--write", gh=gh, **self.kw)[0], _main("--write", gh=gh, **later)[0])
        self.assertEqual((rcs, self.onb.read_bytes()), ((0, 0), other.read_bytes()))
        self.assertTrue(all(c[:2] in (["run", "list"], ["run", "view"]) for c in calls))

    def test_checked_at_is_the_earlier_run_in_utc_plus_00_00_form(self) -> None:
        """取兩支取樣 run 中較早者，+00:00 形態；b 較早且 id 較大＝擋「取第一個」「只比 id」。"""
        a = RNA.anchor_from(self.samples)
        self.assertEqual((a.run, a.checked, a.red), (101101, "2026-10-05T14:26:01+00:00", "none"))
        early = json.dumps([_run(201201, "2026-10-01T00:00:00Z")])
        b = RNA.anchor_from(self._fetch(**{"b.yml|schedule": early}))
        self.assertEqual((b.run, b.checked), (201201, "2026-10-01T00:00:00+00:00"))

    def test_the_newer_event_wins_and_only_completed_runs_count(self) -> None:
        """兩事件取較新者（dispatch run 也算），只取 completed；兩事件皆空 fail-loud。"""
        newer = json.dumps([_run(150150, "2026-10-06T00:00:00Z", "workflow_dispatch"),
                            _run(160160, "2026-10-07T00:00:00Z", status="in_progress")])
        got = self._fetch(**{"a.yml|workflow_dispatch": newer,
                             "view|150150": _jobs(("Job A（深度）", "success"))})
        self.assertEqual({s.wf: s.run.id for s in got}["a.yml"], 150150)
        with self.assertRaisesRegex(RNA.EvidenceError, "沒有任何 completed"):
            self._fetch(**{"a.yml|schedule": "[]", "a.yml|workflow_dispatch": "[]"})

    def test_red_is_the_non_success_subset_or_none(self) -> None:
        """nightly-red 是結論非 success（含 skipped）的 `<wf>:<job id>` 子集；全綠才是 none。"""
        bad = {"view|101101": _jobs(("Job A（深度）", "failure"))}
        self.assertEqual(RNA.anchor_from(self._fetch(**bad)).red, "a.yml:ja")
        both = self._fetch(**bad, **{"view|201201": _jobs(("Job B", "cancelled"))})
        self.assertEqual(RNA.anchor_from(both).red, "a.yml:ja,b.yml:jb")
        skip = _jobs(("Job A（深度）", "skipped"))  # 與 4 位數字分行（基線數字站點鎖）
        self.assertEqual(RNA.anchor_from(self._fetch(**{"view|101101": skip})).red, "a.yml:ja")

    def test_the_judgement_cell_is_the_fixed_sentence(self) -> None:
        """判讀欄是工具產生的固定句型、零人工散文；用 golden 字串釘住版面。"""
        golden = ("> | `ja` | a.yml | ✅ success | `101101` ／ `abababab` | schedule run（建立 "
                  "2026-10-05T14:26:01+00:00）；run 層 success；job 層「Job A（深度）」success |")
        self.assertEqual(RNA.render_rows(self.samples)[0], golden)
        red = self._fetch(**{"view|101101": _jobs(("Job A（深度）", "failure"))})
        self.assertIn("| 🔴 failure |", RNA.render_rows(red)[0])
        self.assertIn("「x｜y」", RNA.render_rows([self.samples[0]._replace(display="x|y")])[0])

    def test_rows_follow_the_schedule_gated_fail_open_set(self) -> None:
        """列集合＝排程放行的 fail-open 子集；集合長大時列自動變多；誘餌不入列。"""
        self.assertEqual(len(RNA.cloud_fail_open_jobs(self.wd)), 4)
        self.assertEqual(self.pairs, ["a.yml:ja", "b.yml:jb"])
        (self.wd / "d.yml").write_text(_WF["a.yml"].replace("ja:", "jd:"), encoding="utf-8")
        self.assertEqual(len(RNA.scheduled_fail_open_jobs(self.wd)), 3)
        live = RNA.scheduled_fail_open_jobs(RNA.WORKFLOWS_DIR)
        self.assertEqual(set(live), {"macos-compat-ci.yml:macos-nightly-full",
                                     "windows-compat-ci.yml:windows-nightly-full"})
        self.assertLessEqual(set(live), set(RNA.cloud_fail_open_jobs(RNA.WORKFLOWS_DIR)))

    def test_only_the_three_nightly_fields_and_the_table_rows_change(self) -> None:
        """錨行其餘欄位與散文逐字不動；只動三個 nightly 值與表③-b 的列。"""
        body = [[re.sub(r" nightly-[a-z-]+=\S+", "", ln) for ln in t.split("\n")
                 if not ln.startswith("> | `")] for t in (_ONB, self.fresh)]
        self.assertEqual(*body)
        fields, probs = RNA._anchor_fields(self.fresh)
        a = RNA.anchor_from(self.samples)
        got = (fields["nightly-red"], fields["nightly-run"], fields["nightly-checked-at"])
        self.assertEqual((got, probs), ((a.red, str(a.run), a.checked), []))

    def test_write_is_lf_only_and_idempotent(self) -> None:
        """bytes 層 LF、冪等：第二次零寫入並印「無變更」（避免每晚 diff 噪音與 CRLF 汙染）。"""
        self.assertEqual(_main("--write", gh=_gh(_TABLE), **self.kw)[0], 0)
        first = self.onb.read_bytes()
        rc, out, _ = _main("--write", gh=_gh(_TABLE), **self.kw)
        self.assertEqual((rc, self.onb.read_bytes(), b"\r" in first, "無變更" in out),
                         (0, first, False, True))

    def test_write_self_check_fails_after_writing_a_stale_anchor(self) -> None:
        """A6 寫後自檢：取樣 run 已逾 14 天 ⇒ 檔案照寫、rc 1、訊息含「天前」。"""
        late = {**self.kw, "now": _NOW + datetime.timedelta(days=15)}
        rc, _, err = _main("--write", gh=_gh(_TABLE), **late)
        wrote = self.onb.read_bytes() == self.fresh.encode("utf-8")
        self.assertEqual((rc, "天前" in err, wrote), (1, True, True))

    def test_check_head_tells_commit_when_the_tree_is_fresh(self) -> None:
        """HEAD 舊、工作樹新 ⇒ 指路 commit（A7 兩型訊息之一）。"""
        self.onb.write_bytes(self.fresh.encode("utf-8"))
        rc, _, err = _main("--check-head", head_reader=lambda: _ONB, **self.kw)
        self.assertEqual((rc, "git add ONBOARDING" in err), (1, True))

    def test_check_head_tells_write_when_both_are_stale(self) -> None:
        """HEAD、工作樹皆舊 ⇒ 指路 `--write`（A7 兩型訊息之二）。"""
        rc, _, err = _main("--check-head", head_reader=lambda: _ONB, **self.kw)
        self.assertEqual((rc, "--write" in err, "git add" in err), (1, True, False))

    def test_check_and_check_head_are_green_on_a_fresh_anchor(self) -> None:
        """對照組：新鮮錨兩模式皆綠；`--check` 對舊錨紅（否則上兩支只是全都判紅）。"""
        self.assertEqual(_main("--check", **self.kw)[0], 1)
        self.onb.write_bytes(self.fresh.encode("utf-8"))
        rcs = (_main("--check", **self.kw)[0],
               _main("--check-head", head_reader=lambda: self.fresh, **self.kw)[0])
        self.assertEqual(rcs, (0, 0))

    def test_every_evidence_failure_is_rc3_and_writes_nothing(self) -> None:
        """取證失敗＝fail-loud：rc 3、零寫入（A6）。"""
        def fake(rc=0, err=""):
            return mock.Mock(return_value=subprocess.CompletedProcess([], rc, "[]", err))

        boom = {OSError(): "無法啟動", subprocess.TimeoutExpired("gh", 30): "逾時"}
        cases = {"找不到 gh": {"which": lambda _n: None}, "未登入": {"runner": fake(4)},
                 "boom": {"runner": fake(1, "boom")}}
        cases.update({want: {"runner": mock.Mock(side_effect=e)} for e, want in boom.items()})
        for want, kw in cases.items():
            with self.subTest(want), self.assertRaisesRegex(RNA.EvidenceError, want):
                RNA.run_gh(["x"], **{"which": lambda _n: "gh", **kw})
        self.assertEqual(RNA.run_gh(["x"], which=lambda _n: "gh", runner=fake()), "[]")
        git = {"which": lambda _n: "git", "runner": fake(128, "fatal: bad revision")}
        with self.assertRaisesRegex(RNA.EvidenceError, "無法讀取 HEAD.*fatal"):
            RNA.git_show_head(**git)
        bad = {"非 JSON": {("a.yml", "schedule"): "not json"},
               "缺欄位": {("b.yml", "schedule"): json.dumps([{"databaseId": 1}])},
               "無顯示名": {("view", "101101"): _jobs(("other", "success"))},
               "兩事件皆空": {("a.yml", "schedule"): "[]", ("a.yml", "workflow_dispatch"): "[]"}}
        before = self.onb.read_bytes()
        for name, override in bad.items():
            rc, _, err = _main("--write", gh=_gh({**_TABLE, **override}), **self.kw)
            self.assertEqual((rc, self.onb.read_bytes()), (3, before), name)

    def test_subprocess_call_contract_is_pinned_on_the_injected_runner(self) -> None:
        """子行程編碼鎖看不到注入式呼叫，這支就是它的替代鎖：utf-8／逾時／stdin／cwd／無 shell。"""
        run = mock.Mock(return_value=subprocess.CompletedProcess([], 0, "[]", ""))
        RNA.run_gh(["x"], which=lambda _n: "gh-bin", runner=run)
        run.assert_called_once_with(["gh-bin", "x"], cwd=str(RNA.REPO), stdin=subprocess.DEVNULL,
                                    capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", timeout=RNA.GH_TIMEOUT_S)

    def test_job_display_name_forms(self) -> None:
        """job id→顯示名的各種寫法逐一釘住：無 name 回 job id、運算式不猜、對得上真 workflow。"""
        def doc(line):
            return f"jobs:\n  j:\n{line}    runs-on: x\n"
        forms = {"    name: Plain\n": "Plain", "    name: \"Q\"\n": "Q", "    name: 'S'\n": "S",
                 "    name: T  # c\n": "T", "": "j", "    name: \"A # B\"\n": "A # B"}
        for line, want in forms.items():
            self.assertEqual(RNA.job_display_name(doc(line), "j"), want)
        for text, job in ((doc("    name: ${{ matrix.x }}\n"), "j"), (doc(""), "nope")):
            with self.assertRaises(RNA.EvidenceError):
                RNA.job_display_name(text, job)
        real = (RNA.WORKFLOWS_DIR / "windows-compat-ci.yml").read_text(encoding="utf-8")
        self.assertEqual(RNA.job_display_name(real, "windows-nightly-full"),
                         "Windows nightly full suite（深度回歸，非阻斷）")

    def test_the_offline_gate_rejects_each_bad_anchor_shape(self) -> None:
        """離線判準逐款有牙：id 綁表③-b 列／ISO＋時區／過期邊界／未來／紅集合。"""
        stamp = datetime.datetime.fromisoformat("2026-10-05T14:26:01+00:00")
        fr = self.fresh
        bad = {"不在表③-b": fr.replace("nightly-run=101101", "nightly-run=999999"),
               "沒有時區": fr.replace("14:26:01+00:00 ／", "14:26:01 ／"),
               "不在排程 fail-open 集合": fr.replace("nightly-red=none", "nightly-red=x.yml:y"),
               "不一致": fr.replace("nightly-red=none", "nightly-red=a.yml:ja"),
               "出現 ≥2 次": fr.replace("／ x", "nightly-run=5 ／ x"),
               "不是合法 ISO8601": fr.replace("2026-10-05T14:26:01+00:00 ／", "banana ／"),
               "形態不合法": fr.replace("nightly-run=101101", "nightly-run=12"),
               "錨缺": fr.replace(" nightly-red=none", ""),
               "沒有任何資料列": "\n".join(x for x in fr.split("\n") if not x.startswith("> | `")),
               "不合格式": fr.replace("`101101` ／ `abababab`", "`1` ／ `abababab`")}
        for want, text in bad.items():
            self.assertIn(want, self._problems(text), want)
        self.assertEqual(RNA.anchor_problems(self.fresh, _NOW, self.pairs), [])
        days = datetime.timedelta
        self.assertEqual(self._problems(self.fresh, stamp + days(days=14, hours=1)), "")
        self.assertIn("天前", self._problems(self.fresh, stamp + days(days=15)))
        self.assertIn("在未來", self._problems(self.fresh, stamp - days(days=2)))

    def test_offline_verdicts_agree_with_the_ci_judge_and_share_one_home(self) -> None:
        """工具判準與 CI 判準不得各說各話；常數與掃描函式單一居所（章程 A3）。"""
        import test_doc_loc_baseline_freshness_r60 as ci  # noqa: PLC0415
        self.assertIs(ci.cloud_fail_open_jobs, RNA.cloud_fail_open_jobs)
        self.assertEqual(ci._NIGHTLY_MAX_AGE_DAYS, RNA.NIGHTLY_MAX_AGE_DAYS)
        theirs = (ci._NIGHTLY_RUN_FIELD, ci._NIGHTLY_CHECKED_FIELD, ci._NIGHTLY_RED_CLEAN,
                  ci._NIGHTLY_RED_SEP)
        self.assertEqual(theirs, (RNA.FIELD_RUN, RNA.FIELD_CHECKED, RNA.RED_NONE, RNA.RED_SEP))
        for stamp in ("2026-10-05T14:26:01+00:00", "2026-08-01T00:00:00+00:00",
                      "2026-10-05T14:26:01", "2026-10-20T00:00:00+00:00"):
            fields = {"nightly-run": "101101", "nightly-red": "none", "nightly-checked-at": stamp}
            judge = ci.cloud_nightly_red_problems(fields, ci._WORKFLOWS_DIR, "101101", _NOW)
            self.assertEqual(bool(judge), bool(RNA._stamp_problems(stamp, _NOW)), stamp)

    def test_layout_errors_are_rc1_and_name_the_missing_piece(self) -> None:
        """ONBOARDING 版面壞掉＝rc 1 並點名缺什麼，不得靜默寫壞。"""
        cases = {"命中 0 次": _ONB.replace("cloud-ci-status:", "x:"),
                 "命中 2 次": _ONB + _ONB.splitlines()[-1] + "\n",
                 "找不到表③-b 表頭": _ONB.replace("> | job id | workflow |", "> | x |"),
                 "`nightly-run=`": _ONB.replace("nightly-run=111111", ""),
                 "CR": _ONB.replace("\ntail", "\r\ntail")}
        for want, text in cases.items():
            self.onb.write_bytes(text.encode("utf-8"))
            rc, _, err = _main("--write", gh=_gh(_TABLE), **self.kw)
            self.assertEqual((rc, self.onb.read_bytes()), (1, text.encode("utf-8")), want)
            self.assertIn(want, err)

    def test_unknown_flags_exit_2_before_any_io_and_help_exits_0(self) -> None:
        """未知旗標／模式互斥 rc 2 且先於任何 I/O；`--help` rc 0。"""
        sink = io.StringIO()
        with redirect_stderr(sink), redirect_stdout(sink):
            codes = [RNA.cli(a) for a in (["--bogus"], ["--write", "--check"], ["--help"], ["-h"])]
        self.assertEqual((codes, "--check-head" in sink.getvalue()), ([2, 2, 0, 0], True))


if __name__ == "__main__":
    unittest.main()
