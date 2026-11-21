"""`tools/lib/wastecensus/`＋`tools/probe/waste_census.py` 的驗收測試（AT-TW-50～59）。

規格＝TCS-TokenWaste-20261114 §2.6；守的是「浪費帳是可重跑、可信的量測」：重寫判準（根）、
M1／M2b／M2c／M2d／M3d 各自的邊界、收斂門檻取值重放、CLI 不污染工作樹、壞行不使探針崩潰、
入口只是薄殼。縫＝tmp 合成逐字稿（`--base`／`base` 參數），不讀真實家目錄、不起外部行程
（CLI 測試只起本探針自己）；時間戳一律帶 offset、檔案 I/O 一律明寫 encoding。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

import guard_line_taxonomy  # noqa: E402
import quota_policy as qp  # noqa: E402

from lib.wastecensus import (  # noqa: E402
    metrics,
    pace_metrics,
    pace_replay,
    reader,
    replay,
    sections_wake,
)

_TZ = timezone(timedelta(hours=8))
_T0 = datetime(2026, 11, 14, 10, 0, 0, tzinfo=_TZ)
_PROBE = _REPO / "tools" / "probe" / "waste_census.py"


def _iso(minutes: float) -> str:
    return (_T0 + timedelta(minutes=minutes)).isoformat()


def _asst(minutes: float, mid: str, *, inp=0, cc=0, cr=0, cc5=0, cc1=0, tools=()) -> dict:
    """一則 assistant 記錄（usage 欄位與真實逐字稿同形）；`tools`＝tool_use 名單。"""
    content = [{"type": "tool_use", "id": f"{mid}-{k}", "name": name, "input": {}}
               for k, name in enumerate(tools)]
    return {
        "type": "assistant", "timestamp": _iso(minutes),
        "message": {
            "id": mid, "model": "claude-test", "content": content,
            "usage": {
                "input_tokens": inp, "cache_creation_input_tokens": cc,
                "cache_read_input_tokens": cr, "output_tokens": 10,
                "cache_creation": {"ephemeral_5m_input_tokens": cc5,
                                   "ephemeral_1h_input_tokens": cc1},
            },
        },
    }


def _user(minutes: float, text: str = "hi") -> dict:
    """沒有 origin 的人類以外使用者文字記錄 ⇒ 起因歸 other_user。"""
    return {"type": "user", "timestamp": _iso(minutes), "message": {"content": text}}


def _write_lines(path: Path, recs: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in recs) + "\n",
                    encoding="utf-8", newline="\n")


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.base = self.tmp / "projects"
        self.base.mkdir()

    def _agent(self, sid: str, aid: str, recs: list, agent_type: str | None = None) -> None:
        _write_lines(self.base / sid / "subagents" / f"agent-{aid}.jsonl", recs)
        if agent_type:
            meta = self.base / sid / "subagents" / f"agent-{aid}.meta.json"
            meta.write_text(json.dumps({"agentType": agent_type}), encoding="utf-8")

    def _main(self, sid: str, recs: list) -> None:
        _write_lines(self.base / f"{sid}.jsonl", recs)

    def _rows(self) -> list[dict]:
        return metrics.rewrites(reader.collect(self.base, 14, None))


class RewriteDetectionTest(_Base):
    """`tools/lib/wastecensus/reader.py`＋`metrics.rewrites`：重寫判準（AT-TW-50、51）。"""

    def test_at_tw_50_a_resumed_cold_subagent_is_one_rewrite_of_its_whole_context(self) -> None:
        """reader.py：交卷後 10 分鐘被續棒、整份重寫 ⇒ 1 件，5m 型、起因 other_user。

        WHY：重寫判準是整個探針的根；歸因或重寫量錯了，M2b／M2c 全部失真。
        """
        self._main("s1", [_asst(0, "m0", cc=1000, cc5=1000)])
        self._agent("s1", "a1", [
            _asst(0, "a0", cc=150_000, cc5=150_000),
            _asst(1, "a1", inp=100, cr=150_000, cc5=0),
            _user(11, "請繼續"),
            _asst(11.2, "a2", cc=150_100, cc5=150_100),
        ])
        rows = [r for r in self._rows() if r["axis"] == "子代理"]
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertEqual((row["tier"], row["cause"]), ("5m", "other_user"))
        self.assertAlmostEqual(row["rewrite_tokens"], 150_000, delta=1000)
        self.assertGreater(row["gap_s"], 600 - 1)

    def test_at_tw_51_m1_counts_only_main_rewrites_idle_over_an_hour_with_big_context(self) -> None:
        """metrics.py::m1：閒置 70 分鐘且 prev_ctx 30 萬 ⇒ 計 1 件；閒置 50 分鐘 ⇒ 計 0。

        WHY：M1 的邊界是 gap>3600 且 prev_ctx>=250,000；放寬邊界會把正常的短閒置也算成浪費。
        """
        for sid, idle in (("long", 70), ("short", 50)):
            self._main(sid, [
                _asst(0, "x0", cc=300_000, cc1=300_000),
                _asst(1, "x1", inp=10, cr=300_000, cc1=0),
                _asst(1 + idle, "x2", cc=300_050, cc1=300_050),
            ])
        got = metrics.m1(self._rows())
        self.assertEqual(got["count"], 1, got)
        self.assertAlmostEqual(got["tokens"], 300_000, delta=1000)


class DispatchMetricTest(unittest.TestCase):
    """`tools/lib/wastecensus/metrics.py`：M2b／M2c／M2d／M3d 的篩選邊界（AT-TW-52～55）。"""

    @staticmethod
    def _row(axis="子代理", cause="other_user", prev_ctx=200_000, gap_s=600.0,
             thread="agent-a", tokens=1000) -> dict:
        return {"kind": "rewrite", "axis": axis, "cause": cause, "prev_ctx": prev_ctx,
                "gap_s": gap_s, "thread": thread, "rewrite_tokens": tokens}

    def test_at_tw_52_m2b_filters_by_the_caller_supplied_limit_not_a_hardcoded_one(self) -> None:
        """metrics.py::m2b：prev_ctx 149,999 不算、150,000 起算；門檻改了指標隨之改。

        WHY：M2b 以續棒門檻為分界，門檻由呼叫端傳（switch.threshold）；寫死會與閘脫鉤。
        """
        rows = [self._row(prev_ctx=149_999), self._row(prev_ctx=150_000, gap_s=3000),
                self._row(prev_ctx=300_000, gap_s=9000), self._row(prev_ctx=200_000),
                self._row(axis="主控"), self._row(cause="tool_result")]
        got = metrics.m2b(rows, 150_000)
        self.assertEqual((got["count"], got["le60min"], got["tokens"]), (3, 2, 3000))
        self.assertEqual(metrics.m2b(rows, 100_000)["count"], 4, "門檻下修，件數必須隨之增加")

    def test_at_tw_53_m2c_groups_by_agent_type_and_counts_gap_below_ttl_apart(self) -> None:
        """metrics.py::m2c：只收 tool_result／通知起因、<=60 分的子代理重寫，按 agentType 分組。

        WHY：分組欄是判斷 1 小時快取型別是否真的消掉長等待重寫的唯一證據；`gap_lt_ttl`
        是 gap<5 分卻重寫的件數（成因不在 TTL，1 小時 TTL 消不掉，免得高估效益）。
        """
        rows = [self._row(cause="tool_result", thread="agent-g1", gap_s=700),
                self._row(cause="task_notification", thread="agent-g2", gap_s=250),
                self._row(cause="tool_result", thread="agent-l1", gap_s=1200),
                self._row(cause="tool_result", thread="agent-x", gap_s=4000),
                self._row(cause="other_user", thread="agent-g1", gap_s=700),
                self._row(axis="主控", cause="tool_result", gap_s=700)]
        types = {"agent-g1": "general-purpose", "agent-g2": "general-purpose",
                 "agent-l1": "long-runner", "agent-x": "long-runner"}
        got = metrics.m2c(rows, types)
        self.assertEqual(got["count"], 3)
        self.assertEqual(got["by_type"], {"general-purpose": 2, "long-runner": 1})
        self.assertEqual(got["gap_lt_ttl"], 1)
        self.assertEqual(metrics.m2c(rows[:1], {})["by_type"], {"unknown": 1})

    def test_at_tw_54_m2d_share_is_over_long_runner_agents_only(self) -> None:
        """metrics.py::m2d：兩個 long-runner，一個有 >6 分回合間隔、一個全程連續 ⇒ 0.5。

        WHY：選錯型別的溢價監看；沒有此欄 long-runner 派錯時純虧而無人知。恰 360 秒不算長等待。
        """
        by_agent = {"agent-l1": [{"gap": None}, {"gap": 400}],
                    "agent-l2": [{"gap": 360}, {"gap": 5}], "agent-g": [{"gap": 9999}]}
        types = {"agent-l1": "long-runner", "agent-l2": "long-runner", "agent-g": "general-purpose"}
        self.assertEqual(metrics.m2d(by_agent, types), {"agents": 2, "zero_wait_share": 0.5})
        self.assertEqual(metrics.m2d(by_agent, {}), {"agents": 0, "zero_wait_share": None})

    def test_at_tw_55_m3d_counts_events_and_tolerates_missing_or_broken_files(self) -> None:
        """metrics.py::m3d：痕跡檔內三種事件的件數；缺檔、壞行回 0 不拋。

        WHY：機制自身的阻斷／逃生使用量只有這一處量測；量不到就無從回頭檢討門檻。
        """
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "autosdd_session_switch.jsonl"
            events = ["resume_gate_block"] * 3 + ["resume_gate_override"] + ["converge_block"] * 2
            body = [json.dumps({"event": e}) for e in events]
            body += ["not json", json.dumps({"event": "other"}), json.dumps([1, 2])]
            trace.write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")
            self.assertEqual(metrics.m3d(trace),
                             {"blocked": 3, "overridden": 1, "converge_blocked": 2})
            self.assertEqual(metrics.m3d(Path(tmp) / "absent.jsonl"),
                             {"blocked": 0, "overridden": 0, "converge_blocked": 0})


class ReplayHardCtxTest(_Base):
    """`tools/lib/wastecensus/replay.py`：收斂硬門檻取值重放（AT-TW-56）。"""

    def test_at_tw_56_replay_reports_room_blocked_dispatches_and_incident(self) -> None:
        """replay.py::replay_hard_ctx：三個 session 的合成重放，逐候選 H 的表與手算一致。

        WHY：門檻取值（Q-A1）必須可重放，否則收斂硬門檻只剩一個魔術數字；事故 session 在
        事故時刻的上下文 >= H 才算「擋得到」，等號邊界要釘住。
        """
        ctxs = [100_000, 260_000, 270_000, 295_000, 310_000]
        s1 = [_asst(i, f"s1-{i}", cr=c, tools=("Agent",) if i in (2, 4) else ())
              for i, c in enumerate(ctxs)]
        s2 = [_asst(i, f"s2-{i}", cr=c) for i, c in enumerate([255_000, 256_000, 257_000])]
        s3 = [_asst(0, "s3-0", cr=300_000), _asst(10, "s3-1", cr=301_000, tools=("Agent",))]
        for sid, recs in (("s1", s1), ("s2", s2), ("s3", s3)):
            self._main(sid, recs)
        table = replay.replay_hard_ctx(
            self.base, 250_000, (280_000, 300_000, 320_000),
            incident_sid="s3", incident_ts=_iso(5))
        by_h = {r["H"]: r for r in table}
        self.assertEqual([r["sessions_reaching_r1"] for r in table], [3, 3, 3])
        self.assertEqual(by_h[280_000]["sessions_reaching_H"], 2)
        self.assertEqual(by_h[280_000]["room_turns_median"], 1.0)
        self.assertEqual(by_h[280_000]["room_turns_p25"], 0)
        self.assertEqual(by_h[300_000]["room_turns_median"], 1.5)
        self.assertEqual(by_h[320_000]["sessions_reaching_H"], 0)
        self.assertIsNone(by_h[320_000]["room_turns_median"])
        self.assertEqual([r["dispatches_after_r1"] for r in table], [3, 3, 3])
        self.assertEqual([r["blocked_dispatches"] for r in table], [2, 1, 0])
        self.assertEqual([r["incident_blocked"] for r in table], [True, True, False])


class CliAndStructureTest(_Base):
    """`tools/probe/waste_census.py`：CLI 不污染工作樹、壞行不崩潰、入口是薄殼（AT-TW-57～59）。"""

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
        return subprocess.run(
            [sys.executable, str(_PROBE), "--base", str(self.base),
             "--trace-file", str(self.tmp / "no-trace.jsonl"),
             "--out", str(self.tmp / "out.jsonl"), *extra],
            capture_output=True, env=env, cwd=str(self.tmp), timeout=120)

    @staticmethod
    def _snapshot() -> dict:
        seen = {}
        roots = [_REPO / "tools" / "probe", _REPO / "tools" / "lib" / "wastecensus"]
        for root in roots:
            for p in root.rglob("*"):
                if p.is_file():
                    st = p.stat()
                    seen[str(p)] = (st.st_size, st.st_mtime_ns)
        seen["<repo-root>"] = sorted(p.name for p in _REPO.iterdir())
        return seen

    def _seed(self) -> None:
        self._main("s1", [_asst(0, "m0", cc=40_000, cc5=40_000),
                          _asst(1, "m1", inp=10, cr=40_000)])

    def test_at_tw_57_cli_prints_the_report_writes_only_jsonl_outside_the_repo(self) -> None:
        """waste_census.py：rc 0、stdout 含 浪費排序／M1／M2b、jsonl 每列有 kind、不寫 repo。

        WHY：探針不接閘門 rc、不污染工作樹；rc 隨指標值改變就會被誤接成閘門。
        """
        self._seed()
        before = self._snapshot()
        proc = self._run()
        out = proc.stdout.decode("utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        for needle in ("浪費排序", "M1", "M2b"):
            self.assertIn(needle, out)
        rows = [json.loads(x) for x in (self.tmp / "out.jsonl").read_text(encoding="utf-8")
                .splitlines()]
        self.assertTrue(rows and all("kind" in r for r in rows))
        self.assertEqual(self._snapshot(), before, "探針不得在 repo 內留下任何檔")

    def test_at_tw_58_broken_or_usage_less_lines_are_skipped_and_counted(self) -> None:
        """reader.py：壞 JSON 行、非物件行、缺 usage 的 assistant 記錄 ⇒ 不拋、計入 skipped_lines。

        WHY：真實逐字稿必有壞行；探針崩潰＝量測不可重放。
        """
        self._main("s1", [_asst(0, "m0", cc=40_000, cc5=40_000), "{broken", json.dumps([1]),
                          {"type": "assistant", "timestamp": _iso(2), "message": {"id": "nu"}},
                          _asst(3, "m3", inp=10, cr=40_000)])
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", "replace"))
        rows = [json.loads(x) for x in (self.tmp / "out.jsonl").read_text(encoding="utf-8")
                .splitlines()]
        summary = next(r for r in rows if r["kind"] == "summary")
        self.assertEqual(summary["skipped_lines"], 2)

    def test_at_tw_59_entry_is_a_thin_shell_and_library_files_stay_in_budget(self) -> None:
        """waste_census.py＋tools/lib/wastecensus/*.py：入口薄殼（<=80 斷言行、無判準函式）。

        WHY：SA 原探針 714 斷言行逼近 750 紅線；判準住 lib、入口只分派，落點規範才守得住。
        每個 lib 檔 <=400 斷言行（guardrail_lib 預算）。
        """
        shell = guard_line_taxonomy.classify_file(_PROBE)
        self.assertLessEqual(shell.assertion, 80)
        text = _PROBE.read_text(encoding="utf-8")
        defs = [ln for ln in text.splitlines() if ln.startswith("def ")]
        self.assertEqual(defs, [], "入口薄殼不得定義判準函式")
        self.assertIn("from lib.wastecensus", text)
        pkg = sorted((_REPO / "tools" / "lib" / "wastecensus").glob("*.py"))
        self.assertGreaterEqual(len(pkg), 9, "套件檔數不應少於拆分後的九支")
        for path in pkg:
            self.assertLessEqual(guard_line_taxonomy.classify_file(path).assertion, 400, path.name)


_INC_LAST = "2026-11-15T19:17:12.620Z"
_INC_RESET = "2026-11-15T20:00:00+00:00"
_INC_HUMAN = "2026-11-16T00:54:03.896Z"
_INC_ASST = "2026-11-16T00:54:22.783Z"


def _burn(ts: str = "2026-11-15T19:16:55Z", five: float = 98.0) -> dict:
    return {"ts": ts, "pct": {"five_hour": five, "session": five},
            "resets_at": {"five_hour": _INC_RESET, "session": _INC_RESET}}


def _a(ts: str, cc: int = 1482) -> dict:
    return {"type": "assistant", "timestamp": ts,
            "message": {"id": ts, "model": "claude-fable-5", "usage": {
                "input_tokens": 2, "cache_read_input_tokens": 217_962,
                "cache_creation_input_tokens": cc, "output_tokens": 5}}}


def _u(ts: str, text: str, kind: str = "human") -> dict:
    return {"type": "user", "timestamp": ts, "origin": {"kind": kind},
            "message": {"role": "user", "content": text}}


class ResumeMetricsTest(_Base):
    """`tools/lib/wastecensus/resume.py`：續航量測 M-R1～M-R4（AT-PK-77～81）。
    WHY：2026-11-15 事故停工到有人回來隔 294 分鐘、重寫 188,230 token；park 上線後要能重跑量出
    這四個數字，沒有量測就無從證明「不再靠人叫醒」。"""

    def _metrics(self, recs: list, burn: list, traces=()):
        from lib.wastecensus import resume
        self._main("s1", recs)
        records = resume.load_records(self.base, 36500)
        stops, unmeasured = resume.find_stops(records, burn, 85.0, list(traces))
        return resume.metrics(stops, records, list(traces)), stops, unmeasured

    def _incident(self, wake: dict) -> list:
        return [_a(_INC_LAST), wake, _a(_INC_ASST, cc=188_230)]

    def test_at_pk_77_incident_fixture(self) -> None:
        """resume.py：事故夾具 ⇒ M-R1≈294.4 分、M-R2＝1（真人 443 字提示，字數判準會漏）、
        M-R3＝188,230 tok≈10.4pp。"""
        got, stops, _un = self._metrics(self._incident(_u(_INC_HUMAN, "請繼續" * 147)), [_burn()])
        self.assertEqual(len(stops), 1)
        self.assertAlmostEqual(got["m_r1"]["median"], 294.4, delta=0.1)
        self.assertEqual(got["m_r2"], 1)
        self.assertEqual((got["m_r3"]["tokens"], got["m_r3"]["pp"]), (188_230, 10.4))

    def test_at_pk_78_machine_wakeups_are_not_a_human(self) -> None:
        """resume.py：spawn 提示／auto-continuation／sdk 起的喚醒 ⇒ M-R2＝0（機器喚醒不算靠人）。"""
        for wake in (_u(_INC_HUMAN, "按交接包繼續：讀 x.md"),
                     _u(_INC_HUMAN, "continue", kind="auto-continuation"),
                     _u(_INC_HUMAN, "go", kind="sdk")):
            with self.subTest(kind=wake["origin"]["kind"]):
                got, _stops, _un = self._metrics(self._incident(wake), [_burn()])
                self.assertEqual(got["m_r2"], 0)
                self.assertEqual(got["m_r1"]["n"], 1)

    def test_at_pk_79_unmeasured_gaps_are_counted_not_dropped(self) -> None:
        """resume.py：間隔夠長但停點前 15 分鐘內沒有 quota_burn 樣本 ⇒ 計入 unmeasured、不進分母
        （不得靜默丟棄：量不到≠沒有停點）。"""
        got, stops, unmeasured = self._metrics(
            self._incident(_u(_INC_HUMAN, "請繼續")), [_burn(ts="2026-11-15T18:00:00Z")])
        self.assertEqual((stops, unmeasured, got["m_r1"]["n"]), ([], 1, 0))

    def test_at_pk_80_stops_without_a_credential_are_listed(self) -> None:
        """resume.py：停點前後 10 分鐘內有 park_armed／park_done ⇒ 有憑證；否則計入「無憑證停點」；
        park_stop_block 件數獨立列出。"""
        recs = self._incident(_u(_INC_HUMAN, "請繼續"))
        armed = [{"event": "park_armed", "at": "2026-11-15T19:15:00+00:00"}]
        blocks = [{"event": "park_stop_block", "at": "2026-11-15T19:17:00+00:00"}] * 3
        with_cred, _s, _u2 = self._metrics(recs, [_burn()], armed + blocks)
        without, _s, _u3 = self._metrics(recs, [_burn()], blocks)
        self.assertEqual(with_cred["m_r4"], {"stop_block": 3, "stops_without_credential": 0})
        self.assertEqual(without["m_r4"], {"stop_block": 3, "stops_without_credential": 1})

    def test_at_c1_park_trace_stop_below_prepare_threshold_is_counted(self) -> None:
        """resume.py：f2260ce7 形態——五小時窗只有 84%（< 準備門檻 85，park 走 --why 路徑）、間隔起點
        附近有 park_armed ⇒ 仍計為停點（reset 取 fire_at）；沒有痕跡的同樣 84% 閒置不計。
        WHY：park 的 --why／--at 路徑結構上永不達門檻，只看百分比會系統性漏算停工停點。"""
        last, wake = "2026-11-16T02:10:35Z", "2026-11-16T05:03:03Z"
        recs = [_a(last), _u(wake, "go", kind="sdk"), _a("2026-11-16T05:03:10Z")]
        burn = [_burn(ts="2026-11-16T02:07:08Z", five=84.0)]
        armed = [{"event": "park_armed", "at": "2026-11-16T10:10:13+08:00",
                  "fire_at": "2026-11-16T13:03:00+08:00"}]
        got, stops, _un = self._metrics(recs, burn, armed)
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["reset"], 1_794_805_380.0)  # 2026-11-16T05:03:00Z
        self.assertEqual(got["m_r4"]["stops_without_credential"], 0)
        plain, stops2, un2 = self._metrics(recs, burn, [])
        self.assertEqual((stops2, un2), ([], 0))

    def test_at_c1_trace_far_from_the_gap_start_does_not_make_a_stop(self) -> None:
        """resume.py：park_armed 離間隔起點超過 TRACE_NEAR_S ⇒ 不算停點（一般閒置不得被痕跡誤收）。
        """
        recs = [_a("2026-11-16T02:10:35Z"), _a("2026-11-16T05:03:03Z")]
        far = [{"event": "park_armed", "at": "2026-11-16T10:40:00+08:00",
                "fire_at": "2026-11-16T13:03:00+08:00"}]
        _got, stops, _un = self._metrics(recs, [_burn(ts="2026-11-16T02:07:08Z", five=84.0)], far)
        self.assertEqual(stops, [])

    def test_at_c1_park_done_without_reset_is_a_stop_but_not_a_wait(self) -> None:
        """resume.py：park_done 沒有 fire_at ⇒ 停點成立（有憑證），但 reset 未知 ⇒ 不進 M-R1 分母。
        """
        recs = [_a("2026-11-16T02:10:35Z"), _a("2026-11-16T05:03:03Z")]
        done = [{"event": "park_done", "at": "2026-11-16T10:10:13+08:00"}]
        got, stops, _un = self._metrics(recs, [], done)
        self.assertEqual(len(stops), 1)
        self.assertIsNone(stops[0]["reset"])
        self.assertEqual((got["m_r1"]["n"], got["m_r4"]["stops_without_credential"]), (0, 0))

    def test_at_pk_81_resume_metrics_cli_coexists_with_replay_and_writes_nothing(self) -> None:
        """waste_census.py：`--replay-hard-ctx` 優先於 `--resume-metrics`（既有行為不變）；單用
        `--resume-metrics` 印 unmeasured 欄，且不在 repo 內留下任何檔。"""
        self._main("s1", self._incident(_u(_INC_HUMAN, "請繼續")))
        burn = self.tmp / "burn.jsonl"
        burn.write_text(json.dumps(_burn()) + "\n", encoding="utf-8")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"}
        before = sorted(p.name for p in _REPO.iterdir())

        def run(*extra):
            return subprocess.run(
                [sys.executable, str(_PROBE), "--base", str(self.base), "--since-days", "36500",
                 "--trace-file", str(self.tmp / "no-trace.jsonl"), "--burn-file", str(burn),
                 *extra],
                capture_output=True, env=env, cwd=str(self.tmp), timeout=120)
        both = run("--replay-hard-ctx", "--resume-metrics")
        self.assertIn("收斂硬門檻重放", both.stdout.decode("utf-8"))
        only = run("--resume-metrics")
        text = only.stdout.decode("utf-8")
        self.assertEqual(only.returncode, 0, only.stderr.decode("utf-8", "replace"))
        self.assertIn("unmeasured=0", text)
        self.assertIn("M-R1", text)
        self.assertEqual(sorted(p.name for p in _REPO.iterdir()), before)


# ---- R217 A7：叫醒量測 M-WB／配速床量測 M-P／M-C1／回放（AT-WP-34／36、AT-QP-56～63）----
# WHY：量測探針若數錯，「叫醒重複已消除」「床沒有擋掉正常工作」的結案宣稱就建立在假數字上；
# 每條測的都是會讓數字說謊的方向（週軸 halt 混進撞牆、窗樣本不足稀釋占比、reset 微秒抖動拆窗…）。
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HOUR = 3600.0


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat()


def jl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    return path


def burn(ts: float, pct: float, reset: float | None, kinds=("five_hour", "session")) -> dict:
    row = {"ts": iso(ts), "pct": {k: pct for k in kinds}}
    if reset is not None:
        row["resets_at"] = {k: iso(reset) for k in kinds}
    return row


class WakeMetricsTest(unittest.TestCase):
    """AT-WP-34：M-WB2＝子代理完成通知後 60 秒內的重複叫醒；M-WB1＝叫醒後主控回合數。"""

    @staticmethod
    def enq(ts: float, tid: str, summary: str) -> dict:
        body = (f"<task-notification>\n<task-id>{tid}</task-id>\n"
                f"<summary>{summary}</summary>\n</task-notification>")
        return {"type": "queue-operation", "operation": "enqueue", "timestamp": iso(ts),
                "content": body}

    @staticmethod
    def prompt(ts: float, tid: str | None) -> dict:
        text = "hi"
        if tid:
            text = f"<task-notification>\n<task-id>{tid}</task-id>\n</task-notification>"
        return {"type": "user", "timestamp": iso(ts), "message": {"role": "user", "content": text},
                "origin": {"kind": "task-notification" if tid else "human"}}

    @staticmethod
    def asst(ts: float, mid: str) -> dict:
        return {"type": "assistant", "timestamp": iso(ts),
                "message": {"id": mid, "model": "m", "usage": {"cache_creation_input_tokens": 1}}}

    def lines(self, rows: list[dict]) -> list[str]:
        return [json.dumps(r, ensure_ascii=False) for r in rows]

    def test_duplicate_wake_within_60s_after_agent_done_is_counted_and_a_late_one_is_not(self):
        t = 1_800_000_000.0
        rows = [self.enq(t, "a1", 'Agent "X" finished'),
                self.enq(t + 15, "w1",
                         'Background command "Supervise X agent" completed (exit code 0)'),
                self.enq(t + 500, "w2",
                         'Background command "Re-arm watch after keepwarm tick" completed'),
                self.enq(t + 20, "c1", 'Background command "Run unit tests" completed')]
        got = sections_wake.m_wb2(sections_wake.parse_events(self.lines(rows)))
        self.assertEqual((got["count"], got["agent_done"]), (1, 1))
        self.assertEqual(got["hits"][0]["tid"], "w1")  # 非叫醒字樣的背景指令不算、60 秒外的不算

    def test_same_task_id_enqueued_twice_is_one_notification(self):
        t = 1_800_000_000.0
        rows = [self.enq(t, "a1", 'Agent "X" finished'),
                self.enq(t + 5, "w1", 'Background command "Supervise" completed'),
                self.enq(t + 6, "w1", 'Background command "Supervise" completed')]
        events = sections_wake.parse_events(self.lines(rows))
        self.assertEqual(sections_wake.m_wb2(events)["count"], 1)

    def test_turns_after_a_wake_stop_at_the_next_prompt_and_duplicate_message_ids_count_once(self):
        t = 1_800_000_000.0
        rows = [self.enq(t, "w1", 'Background command "Re-arm watch" completed'),
                self.prompt(t + 1, "w1"),
                self.asst(t + 2, "m1"), self.asst(t + 2.5, "m1"),  # 串流同一 message 兩筆 ⇒ 1 回合
                self.asst(t + 3, "m2"), self.asst(t + 4, "m3"),
                self.prompt(t + 100, None),
                self.asst(t + 101, "m4")]
        got = sections_wake.m_wb1(sections_wake.parse_events(self.lines(rows)))
        self.assertEqual((got["turns"], got["wakes"], got["undelivered"]), ([3], 1, 0))

    def test_wake_without_a_delivery_record_is_undelivered_not_guessed(self):
        rows = [self.enq(1_800_000_000.0, "w9", 'Background command "Supervise" completed')]
        got = sections_wake.m_wb1(sections_wake.parse_events(self.lines(rows)))
        self.assertEqual((got["measured"], got["undelivered"]), (0, 1))

    def test_cli_wake_metrics_runs_on_a_sandbox_transcript_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = time.time() - 3600
            jl(
                Path(tmp) / "s1.jsonl",
                [
                    self.enq(now, "a1", 'Agent "X" finished'),
                    self.enq(now + 9, "w1", 'Background command "Supervise" done'),
                    self.prompt(now + 10, "w1"),
                    self.asst(now + 11, "m1"),
                ],
            )
            proc = subprocess.run([sys.executable, str(_PROBE), "--base", tmp, "--wake-metrics"],
                                  text=True, capture_output=True, encoding="utf-8", timeout=120,
                                  creationflags=NOWIN, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("M-WB1", proc.stdout)
        self.assertRegex(proc.stdout, r"M-WB2.*：1 件")


class PaceMetricsTest(unittest.TestCase):
    def test_m_p1_counts_only_five_hour_axis_halts_inside_the_range_and_skips_bad_json(self):
        now = 1_800_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for i, (binding, at) in enumerate(
                [
                    ("five_hour", now - 86400),
                    ("five_hour", now - 2 * 86400),
                    ("five_hour", now - 3 * 86400),
                    ("weekly_all", now - 86400),
                    ("five_hour", now - 40 * 86400),
                ]
            ):
                (d / f"halt_{i}.json").write_text(json.dumps({"binding": binding, "at": iso(at)}),
                                                  encoding="utf-8")
            (d / "halt_bad.json").write_text("{not json", encoding="utf-8")
            got = pace_metrics.m_p1(d, 14.0, now)
        self.assertEqual((got["count"], got["skipped"]), (3, 1))
        self.assertAlmostEqual(got["per_week"], round(3 / (14 / 7), 2))

    def test_m_p3_excludes_thin_windows_from_denominator_and_counts_missing_reset(self):
        r_a, r_b, r_c = 1_800_000_000.0, 1_800_000_000.0 + 10 * HOUR, 1_800_000_000.0 + 20 * HOUR
        rows = []
        for r, pcts in ((r_a, (75, 80, 90)), (r_b, (10, 20, 30))):
            start = r - 5 * HOUR
            rows += [burn(start + (i + 1) * 20 * 60, p, r) for i, p in enumerate(pcts)]
        rows += [burn(r_c - 4 * HOUR, 80, r_c), burn(r_c - 3 * HOUR, 85, r_c)]  # C 窗只有 2 樣本
        rows.append(burn(r_a - HOUR, 50, None))  # 缺 resets_at
        got = pace_metrics.m_p3(rows)
        self.assertEqual((got["windows"], got["early_burn"], got["share"], got["skipped"]),
                         (2, 1, 0.5, 1))

    def test_m_p4_takes_last_reads_within_24h_groups_jittered_resets_judges_window(self):
        base = 1_800_000_000.0
        w1, w2, w3 = base, base + 7 * 86400, base + 14 * 86400
        wk = "seven_day_foo"

        def row(ts, pct, reset_iso):
            return {"ts": iso(ts), "pct": {wk: pct}, "resets_at": {wk: reset_iso}}

        rows = [row(w1 - 20 * HOUR, 60, iso(w1 - 0.1)),  # 早的讀數，應被 6 小時前那筆取代
                row(w1 - 6 * HOUR, 95, iso(w1 + 0.1)),  # 抖動 ±0.1s 同組
                row(w2 - 30 * HOUR, 99, iso(w2)),  # 距 reset 30 小時 ⇒ 不計
                row(w3 - 12 * HOUR, 85, iso(w3))]
        got = pace_metrics.m_p4(rows, [])["by_kind"][wk]
        self.assertEqual((got["weeks"], got["median"], got["min"]), (2, 90.0, 85.0))

    def test_m_p4_withdraw_needs_both_a_low_reading_and_a_pace_floor_event_within_24h(self):
        reset = 1_800_000_000.0
        rows = [{"ts": iso(reset - 5 * HOUR), "pct": {"weekly_all": 80},
                 "resets_at": {"weekly_all": iso(reset)}}]
        near = [{"event": "pace_floor", "at": iso(reset - 10 * HOUR)}]
        far = [{"event": "pace_floor", "at": iso(reset - 60 * HOUR)}]
        self.assertEqual(len(pace_metrics.m_p4(rows, near)["withdraw"]), 1)
        self.assertEqual(pace_metrics.m_p4(rows, far)["withdraw"], [])

    def test_m_p7_counts_windows_overlapping_a_rush_stamp_and_empty_input_is_all_zero(self):
        r1, r2 = 1_800_000_000.0, 1_800_000_000.0 + 10 * HOUR
        rows = [burn(r1 - HOUR, 20, r1), burn(r2 - HOUR, 20, r2)]
        events = [
            {"event": "pace_rush_on", "at": iso(r1 - 3 * HOUR), "until": iso(r1 - 2 * HOUR)},
            {"event": "pace_rush_on", "at": iso(r1 - 4 * HOUR), "until": iso(r1 - 3.5 * HOUR)},
        ]
        got = pace_metrics.m_p7(rows, events)
        self.assertEqual((got["windows"], got["rush_windows"], got["share"]), (2, 1, 0.5))
        self.assertEqual(pace_metrics.m_p7([], [])["share"], 0.0)

    def test_m_c1_counts_main_transcript_requests_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            now = time.time() - 600
            msgs = [{"type": "assistant", "timestamp": iso(now), "message": {
                "id": f"m{i}", "model": "m", "usage": {"cache_creation_input_tokens": cc}}}
                for i, cc in enumerate((1000, 2000, 3000, 6000))]
            jl(d / "main.jsonl", msgs)
            (d / "sub").mkdir()
            jl(d / "sub" / "agent.jsonl", [dict(msgs[0], message=dict(msgs[0]["message"], id="x"))])
            got = pace_metrics.m_c1(d, 14.0)
        self.assertEqual((got["n"], got["mean"], got["median"]), (4, 3000.0, 2500.0))

    def test_cli_pace_metrics_with_no_inputs_prints_a_no_data_note_and_rc0(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            proc = subprocess.run(
                [sys.executable, str(_PROBE), "--base", tmp, "--pace-metrics", "--halt-dir", tmp,
                 "--burn-file", str(d / "none.jsonl"), "--pace-file", str(d / "none2.jsonl")],
                text=True, capture_output=True, encoding="utf-8", timeout=120, creationflags=NOWIN,
                check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for key in ("M-P1", "M-P3", "M-P7", "M-C1", "無資料"):
            self.assertIn(key, proc.stdout)


class PaceReplayTest(unittest.TestCase):
    def test_only_the_row_whose_decision_actually_changes_counts_as_a_bed_opening(self):
        reset = 1_800_000_000.0
        rows = [burn(reset - 247 * 60, 38, reset), burn(reset - 247 * 60, 30, reset),
                burn(reset - 30 * 60, 99, reset), burn(reset - 100 * 60, 50, None)]
        got = pace_replay.replay(rows, qp.Policy())
        self.assertEqual((got["rows"], got["opened"], got["skipped"]), (3, 1, 1))
        row = got["table"][0]
        self.assertIsNone(row["cap_without"])
        self.assertIsNotNone(row["cap_with"])
        halt = [{"at": iso(reset - 20 * 60), "reset_at": iso(reset), "binding": "five_hour"}]
        self.assertIsNotNone(pace_replay.hit_windows(got["table"], halt)[0]["earliest_open"])

    def test_cli_replay_runs_offline_on_sandbox_inputs(self):
        reset = time.time() + 3600
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            jl(d / "burn.jsonl", [burn(time.time() - 60, 38, reset + 247 * 60 - 3600)])
            proc = subprocess.run(
                [sys.executable, str(_PROBE), "--base", tmp, "--replay-pace-floor",
                 "--burn-file", str(d / "burn.jsonl"), "--halt-dir", tmp],
                text=True, capture_output=True, encoding="utf-8", timeout=120, creationflags=NOWIN,
                check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("會開床的列數", proc.stdout)


class PackageShapeTest(unittest.TestCase):
    def test_new_modules_stay_within_the_loc_ceiling_and_the_probe_stays_a_thin_shell(self):
        # AT-QP-63：兩模組各 ≤400 行；入口薄殼不得出現任何 def（判準全在套件內）
        for mod in (pace_metrics, pace_replay, sections_wake):
            self.assertLessEqual(
                len(Path(mod.__file__).read_text(encoding="utf-8").splitlines()), 400
            )
        defs = [ln for ln in _PROBE.read_text(encoding="utf-8").splitlines() if "def " in ln]
        self.assertEqual(defs, [], "入口薄殼不得有任何 def")


if __name__ == "__main__":
    unittest.main()
