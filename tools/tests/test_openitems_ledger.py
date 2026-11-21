"""tools/lib/openitems 的帳本、fold 與動詞（A1；TCS-WorkProgress REQ-WP-01／02／03／06／07／16／27、
AT-WP-01／02／04／08／09／18／50／51／66、E2E-WP-43／50 的帳本面）。

WHY：OIR 是「還有什麼沒做完」的唯一資料面，完成閘與驅動器都信它。所以測的是會讓它說謊的方向：
壞行拖垮整本帳、兩行程撞號、觸發後把空 NextRunTime 當有效、attempt 之後的空窗永遠算 driven、
AskUserQuestion 的回答被當成掌舵者結案。縫：真檔案系統（暫存根）、真子行程（CLI 與並行配號）、
真逐字稿格式夾具；時鐘以參數注入（fold 純函式），不 monkeypatch 被測物。
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.openitems import evidence, fold, ledger, params, verbs  # noqa: E402

CLI = _REPO / "tools" / "openitems.py"
TZ = timezone(timedelta(hours=8))
T0 = datetime(2026, 11, 19, 12, 0, tzinfo=TZ)
SRC = "docs/03_testing/contracts/TCS-WorkProgress-20261119.md:277"
CHECK = {"realverify": "RV-L1"}


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="oi_root_"))
    dest = root / params.PARAMS_REL
    dest.parent.mkdir(parents=True)
    shutil.copyfile(_REPO / params.PARAMS_REL, dest)
    return root


def cli_env(root: Path) -> dict:
    env = dict(os.environ)
    env["AUTOSDD_TRACE_DIR"] = str(root / "_trace")  # 鎖檔圍到沙盒，不碰真家目錄
    return env


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), "--root", str(root), *args], text=True,
                          capture_output=True, encoding="utf-8", env=cli_env(root), timeout=120,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)


def ev(seq: int, evname: str, minutes: float, id_: str = "OI-20261119-001", **kw) -> dict:
    out = {"seq": seq, "ev": evname, "id": id_, "by": "driver:t",
           "ts": (T0 + timedelta(minutes=minutes)).isoformat(timespec="seconds")}
    out.update(kw)
    return out


def opened(**kw) -> dict:
    base = {"title": "t", "source": SRC, "scope": "r217", "kind": "auto", "check": CHECK}
    base.update(kw)
    return ev(1, "open", 0, **base)


class FoldTest(unittest.TestCase):
    P: dict = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls.P = json.loads((_REPO / params.PARAMS_REL).read_text(encoding="utf-8"))

    def state(self, events, now_min, sched=None) -> dict:
        got = fold.fold(events, self.P, T0 + timedelta(minutes=now_min), sched)
        return got.items["OI-20261119-001"]

    def test_out_of_order_events_fold_by_ts_then_seq(self):
        # WHY：兩個寫入者的行序不保證等於時間序；fold 必須以 (ts, seq) 排序（REQ-WP-01）。
        # 帳本檔裡 close 排在 open 前面一行，但 ts 較晚 ⇒ 仍是 closed。
        events = [ev(1, "close", 10, evidence="x"), ev(2, "open", 0, title="t", source=SRC,
                                                        scope="s", kind="auto", check=CHECK)]
        self.assertEqual(self.state(events, 20)["state"], "closed")

    def test_reverse_variant_close_before_open_in_time_is_orphan(self):
        events = [ev(1, "open", 10, title="t", source=SRC, scope="s", kind="auto", check=CHECK),
                  ev(2, "close", 0, evidence="x")]
        got = fold.fold(events, self.P, T0 + timedelta(minutes=20))
        self.assertEqual(got.items["OI-20261119-001"]["state"], "open")
        self.assertEqual(got.orphans, 1)

    def test_before_trigger_scheduler_presence_decides(self):
        # AT-WP-04：觸發前看排程工作存在（快取）；快取過期／讀不到（None）依帳本視為有效。
        d = ev(2, "drive", 1, task="AutoSDD_OpenItem_x", credential="c",
               at=(T0 + timedelta(minutes=60)).isoformat())
        for sched, undriven in ((lambda _t: False, True), (lambda _t: True, False),
                                (lambda _t: None, False)):
            with self.subTest(sched=sched("x")):
                self.assertEqual(self.state([opened(), d], 5, sched)["undriven"], undriven)

    def _drive(self, at_min: float = 10, seq: int = 2) -> dict:
        return ev(seq, "drive", 1, task="T", credential="c",
                  at=(T0 + timedelta(minutes=at_min)).isoformat())

    def test_after_trigger_without_start_uses_start_grace_not_nextruntime(self):
        # AT-WP-50 (a)(b)：at+14 分無 start 仍有效、at+16 分 undriven；sched 回「工作還在」
        # （等同 NextRunTime 為空但工作存在）也不能讓它有效——判準不讀 NextRunTime（MU-WP-12）。
        alive = lambda _t: True  # noqa: E731
        self.assertFalse(self.state([opened(), self._drive()], 10 + 14, alive)["undriven"])
        late = self.state([opened(), self._drive()], 10 + 16, alive)
        self.assertTrue(late["undriven"])
        self.assertEqual(late["undriven_reason"], "never_started")

    def test_started_run_is_bounded_by_budget_and_crash_becomes_undriven(self):
        # AT-WP-50 (c)(d)：有 start、budget=30；start 後 20 分有效、31 分 undriven（崩潰）
        start = ev(3, "start", 10, drive_seq=2, pid=1, proc_start="x", budget_minutes=30)
        events = [opened(), self._drive(), start]
        self.assertFalse(self.state(events, 30)["undriven"])
        self.assertTrue(self.state(events, 41)["undriven"])

    def test_start_for_a_superseded_drive_does_not_vouch_for_the_new_one(self):
        # 反向變體：start 對的是舊 drive（seq 2），新 drive（seq 4）自己沒 start ⇒ 不被舊 start 背書
        start = ev(3, "start", 10, drive_seq=2, pid=1, proc_start="x", budget_minutes=300)
        events = [opened(), self._drive(), start, self._drive(at_min=20, seq=4)]
        self.assertEqual(self.state(events, 20 + 16)["undriven_reason"], "never_started")

    def _attempt(self, result: str, at_min: float, seq: int = 4, **kw) -> dict:
        return ev(seq, "attempt", at_min, n=kw.pop("n", 1), result=result, drive_seq=2, **kw)

    def test_attempt_gap_is_undriven_after_followup_grace(self):
        # AT-WP-66：attempt 之後沒有後續事件，只給 followup_grace（15 分）；之後必須 undriven。
        # MU-WP-17（把「有 attempt」一律判 driven）會讓 (b)(d)(e) 全部變 driven。
        start = ev(3, "start", 10, drive_seq=2, pid=1, proc_start="x", budget_minutes=300)
        base = [opened(), self._drive(), start]
        fail = base + [self._attempt("fail", 20)]
        self.assertFalse(self.state(fail, 20 + 10)["undriven"])  # (a)
        self.assertTrue(self.state(fail, 20 + 16)["undriven"])  # (b)
        self.assertTrue(self.state(base + [self._attempt("pass", 20)], 36)["undriven"])  # (d)
        self.assertTrue(self.state(base + [self._attempt("fail", 20, n=2)], 36)["undriven"])  # (e)

    def test_new_drive_after_deferred_attempt_is_driven_again(self):
        # AT-WP-66 (f)
        start = ev(3, "start", 10, drive_seq=2, pid=1, proc_start="x", budget_minutes=30)
        events = [opened(), self._drive(), start,
                  self._attempt("deferred", 20, reason="quota"), self._drive(at_min=400, seq=5)]
        self.assertFalse(self.state(events, 200, lambda _t: True)["undriven"])

    def test_only_interactive_deferrals_count_and_only_fail_counts_attempts(self):
        # AT-WP-69／MU-WP-18：quota／busy／window_cap 不計 deferrals；deferred 不消耗 attempts
        events = [opened(), self._drive()]
        seq = 3
        for reason in ("quota", "window_cap", "busy", "interactive", "interactive"):
            events.append(self._attempt("deferred", 20, seq=seq, reason=reason))
            seq += 1
        item = self.state(events, 21)
        self.assertEqual((item["deferrals"], item["attempts"]), (2, 0))

    def test_escalated_and_listed_count_as_driven_not_undriven(self):
        # REQ-WP-03：escalated／listed 自帶驅動器（人工清單），不算 undriven
        listed = [ev(1, "open", 0, title="t", source=SRC, scope="s", kind="human",
                     why_not_auto="需要掌舵者目視")]
        self.assertFalse(self.state(listed, 99)["undriven"])
        esc = [opened(), ev(2, "escalate", 1, reason="x")]
        self.assertEqual(self.state(esc, 99)["state"], "escalated")
        self.assertFalse(self.state(esc, 99)["undriven"])

    def test_open_without_drive_is_undriven(self):
        self.assertTrue(self.state([opened()], 1)["undriven"])

    def test_convert_human_to_auto_restarts_the_item(self):
        events = [ev(1, "open", 0, title="t", source=SRC, scope="s", kind="human",
                     why_not_auto="需要掌舵者目視"),
                  ev(2, "convert", 1, kind="auto", why="找到機驗法", check=CHECK)]
        item = self.state(events, 5)
        self.assertEqual((item["state"], item["kind"], item["undriven"]), ("open", "auto", True))

    def test_closed_is_terminal(self):
        events = [opened(), ev(2, "close", 1, evidence="e"), ev(3, "escalate", 2, reason="x")]
        self.assertEqual(self.state(events, 5)["state"], "closed")


class SchemaAndLedgerTest(unittest.TestCase):
    """受測：`tools/lib/openitems/ledger.py` 的事件 schema 與追加路徑。"""
    def setUp(self) -> None:
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.params = params.load(self.root)

    def good_open(self, **kw) -> dict:
        base = {"ev": "open", "id": "OI-20261119-001", "by": "human", "title": "t", "source": SRC,
                "scope": "s", "kind": "auto", "check": CHECK, "ts": T0.isoformat()}
        base.update(kw)
        return base

    def test_schema_rejects_missing_required_fields_per_kind(self):
        # AT-WP-02：human 缺 why_not_auto（或太短）／observe 缺 due／kind 不在四型
        self.assertEqual(ledger.event_problems(self.good_open(), self.params), [])
        bad = (self.good_open(kind="human"), self.good_open(kind="human", why_not_auto="太短"),
               self.good_open(kind="observe"), self.good_open(kind="weird"),
               self.good_open(check=None), self.good_open(check={"argv": ["x"], "pass": "nope"}))
        for event in bad:
            with self.subTest(event=event.get("kind"), check=event.get("check")):
                self.assertTrue(ledger.event_problems(event, self.params))
        self.assertEqual(ledger.event_problems(self.good_open(
            kind="human", why_not_auto="須掌舵者目視畫面"), self.params), [])

    def test_source_whitelist_blocks_coverage_gap_style_sources(self):
        # AT-WP-08：source 指向 README.md（或路徑穿越）⇒ 拒收；白名單內座標放行
        for src in ("README.md", "docs/03_testing/contracts/../../../README.md", "/etc/passwd"):
            with self.subTest(src=src):
                self.assertTrue(ledger.event_problems(self.good_open(source=src), self.params))
        self.assertEqual(ledger.event_problems(self.good_open(source=SRC), self.params), [])

    def test_read_skips_bad_lines_and_counts_them(self):
        # AT-WP-01：壞 JSON、缺共通欄、ev 不認得都算壞行；好行的 seq＝檔內行號
        path = params.ledger_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        good = json.dumps(self.good_open(), ensure_ascii=False)
        path.write_text("\n".join([good, "{not json", json.dumps({"ev": "open"}),
                                   json.dumps(self.good_open(ev="bogus")), good]) + "\n",
                        encoding="utf-8")
        events, bad = ledger.read_events(path)
        self.assertEqual((len(events), bad, [e["seq"] for e in events]), (2, 3, [1, 5]))

    def test_next_id_is_max_of_the_day_plus_one(self):
        day = T0
        evs = [{"id": "OI-20261119-007"}, {"id": "OI-20261118-099"}, {"id": "OI-20261119-002"}]
        self.assertEqual(ledger.next_id(evs, day), "OI-20261119-008")
        self.assertEqual(ledger.next_id([], day), "OI-20261119-001")

    def _pin_trace_dir(self) -> None:
        """鎖檔圍到沙盒；以整份環境快照還原（pop 會清掉原本就有的鍵，DEF-200-464）。"""
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.root / "_trace")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_threaded_open_never_collides(self):
        # AT-WP-09：兩執行緒各 open 20 次 ⇒ 40 個互不相同且連號的 id（寫入鎖內配號，REQ-WP-07）
        self._pin_trace_dir()

        def worker() -> None:
            for _ in range(20):
                ledger.append(self.root, lambda evs: [{
                    "ev": "open", "id": ledger.next_id(evs), "by": "human", "title": "t",
                    "source": SRC, "scope": "s", "kind": "auto", "check": CHECK}])

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        events, bad = ledger.read_events(params.ledger_path(self.root))
        ids = sorted(e["id"] for e in events)
        self.assertEqual(bad, 0)
        self.assertEqual(len(set(ids)), 40)
        self.assertEqual(ids[-1][-3:], "040")

    def test_batch_with_one_invalid_event_writes_nothing(self):
        # 全有或全無：同一批裡只要一個事件不合，整批不寫（反向：全合則全寫）
        self._pin_trace_dir()
        good ={"ev": "open", "id": "OI-20261119-001", "by": "human", "title": "t",
                "source": SRC, "scope": "s", "kind": "auto", "check": CHECK}
        with self.assertRaises(ledger.Reject):
            ledger.append(self.root, lambda _e: [good, {**good, "id": "OI-20261119-002",
                                                        "source": "README.md"}])
        self.assertFalse(params.ledger_path(self.root).exists())
        self.assertEqual(len(ledger.append(self.root, lambda _e: [good])), 1)

    def test_torn_last_line_does_not_swallow_the_next_event(self):
        self._pin_trace_dir()
        path = params.ledger_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'{"ev":"open","id":"OI-2026')  # 撕裂：沒有 LF
        ledger.append(self.root, lambda evs: [{
            "ev": "open", "id": ledger.next_id(evs), "by": "human", "title": "t", "source": SRC,
            "scope": "s", "kind": "auto", "check": CHECK}])
        events, bad = ledger.read_events(path)
        self.assertEqual((len(events), bad), (1, 1))


class CliTest(unittest.TestCase):
    """受測：`tools/openitems.py` 與 `tools/lib/openitems/verbs.py` 的動詞。"""
    def setUp(self) -> None:
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.ledger = params.ledger_path(self.root)

    def rows(self) -> int:
        return len(self.ledger.read_text(encoding="utf-8").splitlines()) if self.ledger.exists() \
            else 0

    def open_auto(self, **kw) -> subprocess.CompletedProcess:
        return run_cli(self.root, "open", "--title", "驗 L1", "--source", SRC, "--scope", "r217",
                       "--kind", kw.get("kind", "auto"), "--check", json.dumps(CHECK),
                       "--by", "sid:test")

    def test_invalid_opens_are_rejected_rc2_and_ledger_unchanged(self):
        # E2E-WP-50（沙盒、真 CLI）：human 缺 why_not_auto、observe 缺 due、source=README.md
        # ⇒ 三者 rc 2、行數不變
        cases = (("--kind", "human", "--source", SRC), ("--kind", "observe", "--source", SRC),
                 ("--kind", "auto", "--source", "README.md"))
        for kind_flag, kind, src_flag, src in cases:
            args = ["open", "--title", "t", "--scope", "s", "--check", json.dumps(CHECK),
                    kind_flag, kind, src_flag, src, "--by", "human"]
            with self.subTest(kind=kind, src=src):
                self.assertEqual(run_cli(self.root, *args).returncode, 2)
        self.assertEqual(self.rows(), 0)

    def test_open_list_roundtrip_and_undriven_filter(self):
        first = self.open_auto()
        self.assertEqual(first.returncode, 0, first.stderr)
        listed = run_cli(self.root, "list", "--undriven")
        self.assertIn("OI-", listed.stdout)
        self.assertRegex(listed.stdout.splitlines()[-1],
                         r"OPENITEMS_LIST total=1 undriven=1 bad=0")

    def test_two_real_processes_open_concurrently_get_distinct_consecutive_ids(self):
        # E2E-WP-43 的帳本面：兩個真行程各連開 8 列（單元層取 8 求快；E2E 取 20 由 A6 載具重跑）
        def spawn() -> subprocess.Popen:
            return subprocess.Popen([sys.executable, "-c", _LOOP, str(self.root)],
                                    env=cli_env(self.root), stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, encoding="utf-8")

        procs = [spawn(), spawn()]
        outs = [p.communicate(timeout=240) for p in procs]
        self.assertEqual([p.returncode for p in procs], [0, 0], outs)
        events, bad = ledger.read_events(self.ledger)
        ids = sorted(e["id"] for e in events)
        self.assertEqual((bad, len(ids), len(set(ids))), (0, 16, 16))
        self.assertEqual(ids, [f"{ids[0][:-3]}{n:03d}" for n in range(int(ids[0][-3:]), 17)])

    def test_bad_line_is_reported_by_list_tail(self):
        self.open_auto()
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write("{broken\n")
        self.assertIn("bad=1", run_cli(self.root, "list").stdout.splitlines()[-1])

    def test_close_auto_requires_check_to_hold(self):
        # 反向變體：RealVerify 帳沒有晚於 open 的 pass 列 ⇒ close rc 1、不寫 close；
        # 帳裡有 ⇒ rc 0 並引該列
        item = self.open_auto().stdout.split()[1]
        before = self.rows()
        self.assertEqual(run_cli(self.root, "close", item, "--by", "sid:t").returncode, 1)
        self.assertEqual(self.rows(), before)
        rv = self.root / evidence.RV_LEDGER_REL
        rv.parent.mkdir(parents=True, exist_ok=True)
        stamp = (datetime.now(UTC) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rv.write_text("| 時間（UTC） | 選取 | 結果 | n | 失敗案例 | 證據座標／備註 | 秒數 |\n"
                      "|---|---|---|---|---|---|---|\n"
                      f"| {stamp} | RV-L1 | pass | 1 | - | x | 3 |\n", encoding="utf-8")
        done = run_cli(self.root, "close", item, "--by", "sid:t")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(f"RealVerify_Result_Ledger.md {stamp} RV-L1",
                      self.ledger.read_text(encoding="utf-8"))
        self.assertEqual(run_cli(self.root, "check", "--id", item).returncode, 0)


_LOOP = (
    "import subprocess,sys\n"
    f"cli={str(CLI)!r}\n"
    "for _ in range(8):\n"
    "    r=subprocess.run([sys.executable,cli,'--root',sys.argv[1],'open','--title','t','--source',"
    f"{SRC!r},'--scope','s','--kind','auto','--check',{json.dumps(json.dumps(CHECK))},"
    "'--by','human'],capture_output=True,text=True)\n"
    "    sys.exit(r.returncode) if r.returncode else None\n"
)


class HumanProofTest(unittest.TestCase):
    """REQ-WP-16／AT-WP-18／E2E-WP-44 的函式庫面：夾具＝真逐字稿的記錄形狀。"""

    SID = "aaaaaaaa-0000-4000-8000-000000000001"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="oi_proj_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        proj = self.tmp / "slug"
        proj.mkdir()
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "問你"}]}},
            {"type": "user", "origin": {"kind": "human"},
             "message": {"content": "核准，這項我目視過了"}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t",
                                                      "content": "User has answered: yes"}]}},
            {"type": "user", "isMeta": True, "origin": {"kind": "human"},
             "message": {"content": "meta"}},
            {"type": "user", "origin": {"kind": "human"},
             "message": {"content": "<system-reminder>注入</system-reminder>"}},
        ]
        (proj / f"{self.SID}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in lines) + "\n", encoding="utf-8")

    def proof(self, text: str) -> tuple[bool, str]:
        return evidence.human_proof(text, self.tmp)

    def test_only_a_real_typed_human_line_is_accepted(self):
        # AT-WP-18／E2E-WP-44：真人打字座標 ⇒ 成立；AskUserQuestion 的 tool_result、isMeta、
        # harness 注入、assistant 行、不存在的行、不存在的 sid ⇒ 全部不成立
        self.assertTrue(self.proof(f"{self.SID} L2")[0])
        for coord in (f"{self.SID} L3", f"{self.SID} L4", f"{self.SID} L5", f"{self.SID} L1",
                      f"{self.SID} L99", "ffffffff-0000-4000-8000-000000000009 L2", "亂寫", ""):
            with self.subTest(coord=coord):
                self.assertFalse(self.proof(coord)[0])

    def test_cli_close_human_item_needs_by_human_and_valid_proof(self):
        root = make_root()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        out = run_cli(root, "open", "--title", "目視", "--source", SRC, "--scope", "s",
                      "--kind", "k1", "--by", "sid:t")
        self.assertEqual(out.returncode, 0, out.stderr)
        item = out.stdout.split()[1]
        proj = str(self.tmp)

        def close(by: str, coord: str) -> int:
            return run_cli(root, "close", item, "--by", by, "--evidence", coord,
                           "--projects-dir", proj).returncode

        self.assertEqual(close("human", f"{self.SID} L3"), 2)  # AskUserQuestion 座標
        self.assertEqual(close("sid:x", f"{self.SID} L2"), 2)  # --by 不是 human
        self.assertEqual(close("human", f"{self.SID} L2"), 0)
        self.assertIn(f"{self.SID} L2", params.ledger_path(root).read_text(encoding="utf-8"))
        self.assertEqual(close("human", f"{self.SID} L2"), 2)  # 已 closed 不可再結


class VerbsInProcessTest(unittest.TestCase):
    def test_missing_params_file_is_env_error_rc3(self):
        empty = Path(tempfile.mkdtemp(prefix="oi_empty_"))
        self.addCleanup(shutil.rmtree, empty, ignore_errors=True)
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            self.assertEqual(verbs.main(["--root", str(empty), "list"]), 3)
        self.assertIn("params.json", err.getvalue())


if __name__ == "__main__":
    unittest.main()
