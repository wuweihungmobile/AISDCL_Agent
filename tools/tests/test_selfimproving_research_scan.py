"""SelfImproving P1 研究掃描與模組體檢的驗收測試（TCS-P1 RS 檔：AT-130、AT-131 系列）。

方法名含 AT 底線形。合成 repo 於 tmp 目錄；P6 的抓取測試一律走
`_selfimproving_p6_fixtures.net` 的注入縫。

P6 的 `research --fetch` 改讀 Console 登記鏡像、只收 https:443、DNS 一次並釘 IP；舊表與 loopback
http 夾具的抓取路徑已退役，舊表凍結為史料（TCS-SelfImproving-P6 §2、AC-SI-45-6）。
舊 AT（本檔已移除）→ 取代它的 P6 AT（TCS-SelfImproving-P6）：
- AT-130-2-1 → AT-630-2-E-2、AT-645-3-1（鏡像未提交也通過預檢）
- AT-130-2-E-1 → AT-645-1-2、AT-630-2-E-1（驗證變體表、預檢碼序零請求）
- AT-130-2-E-2 → AT-645-6-3、AT-645-6-4、AT-630-2-1（舊事件回查照舊、新格式綁事件）
- AT-130-2-E-3 → AT-630-7-E-3、AT-630-3-E-3（重導向逐跳重驗）
- AT-130-2-E-4 → AT-645-6-4（提交時刻比對只屬舊格式）
- AT-130-2-E-5～E-9 → AT-630-7-E-1、AT-645-1-6、AT-645-1-7（附錄 D 逐列）
- AT-130-3-1 → AT-630-3-1；AT-130-3-E-1 → AT-630-3-E-1
- AT-130-3-E-2 → AT-630-3-E-1、AT-630-3-E-5（全失敗 rc 1、JSON 形狀）
- AT-130-3-E-3 → AT-630-3-E-6（抓取在鎖外）、AT-630-2-E-4
- AT-130-3-E-4 → AT-630-2-E-1、AT-630-3-E-1（零成功）
- AT-130-5-1、E-1 → AT-630-5-1、AT-630-3-E-1（too-large）、AT-630-3-E-4
- AT-130-5-E-2、E-3 → AT-630-3-E-2、AT-630-3-E-4（整次與請求鏈牆鐘）
- AT-230-2-E-2 → AT-630-7-E-1、AT-630-7-E-2（壞 host 零連線）
舊 `fetch_source` 已無產品呼叫點，連同 `_open`、`_conn_class` 一併自 `fetch.py` 移除。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p6_fixtures as px
from _selfimproving_fixtures import (
    EVL,
    LEDGER,
    SRC_REL,
    SiTestCase,
    ev,
    obs_id,
    rid,
    serve,
    write_table,
)

from lib.selfimproving import defs as si_defs
from lib.selfimproving import fetch as si_fetch
from lib.selfimproving import git as si_git
from lib.selfimproving import scan as si_scan
from lib.selfimproving import sources as si_sources

TOOLS = fx.TOOLS
TEXT = {"Content-Type": "text/plain; charset=utf-8"}
P_BIG = "9" * max(5000, sys.get_int_max_str_digits() + 1)


def setUpModule() -> None:
    fx.setup("si_rs_")


def tearDownModule() -> None:
    fx.teardown()


def ledger_bytes(repo: Path):
    p = repo / EVL
    return p.read_bytes() if p.is_file() else None


class FakeSock:
    """只有 settimeout／recv_into 的假 socket；讀取層若改呼叫別的方法即 AttributeError 而紅。"""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def settimeout(self, value) -> None:
        self.calls.append(("settimeout", value))

    def recv_into(self, buf) -> int:
        self.calls.append(("recv_into", len(buf)))
        buf[:5] = b"hello"
        return 5


def raw_table(url: str) -> bytes:
    entry = {"id": "a-typo", "url": url, "kind": "docs", "extract": "標題", "added_by": "T1"}
    return (
        json.dumps({"schema_rev": 1, "sources": [entry]}, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")


def norm_time(text: str) -> str:
    return re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} [+-]\d{2}:\d{2}", "<T>", text)


class ResearchCase(SiTestCase):
    """研究掃描測試的共用輔助：一個只 run-open（尚無研究事件）的 repo 與本機伺服器。"""

    def open_only(self, repo: Path, n: int = 1) -> list[str]:
        out = []
        for _ in range(n):
            text = self.cli_ok(
                repo, "run-open", "--trigger", "a", "--coord", "tools/a.py:1", "--by", "main"
            )
            out.append(re.search(r"id=(\S+)", text).group(1))
        return out

    def serving(self, routes: dict):
        srv = serve(routes)
        self.addCleanup(srv.close)
        return srv

    def fetch_repo(self, srv, entries, *, retired=(), runs: int = 1, commit=True):
        repo = fx.p1_base()
        self.open_only(repo, runs)
        write_table(repo, srv, entries, retired=retired, commit=commit)
        return repo

    def zero_success(self, rc, out):
        """零來源成功的拒收：來源行在前、`reject` 行與碼在後（所以不是 `rejected` 的形態）。"""
        self.assertEqual((rc, fx.codes_of(out)), (1, {"ZERO-SUCCESS"}), out)
        self.assertIn("obs-draft:", out.split("\n"))

    def fetch(self, repo, run=None, *extra):
        with fx.relaxed():
            return self.M(repo, "research", "--fetch", "--run", run or rid(1), *extra)

    def scan_events(self, repo):
        return [e for e in fx.EV(repo) if e["kind"] == "research.scan"]


class TestResearchEvents(ResearchCase):
    def test_AT_130_1_1_research_event_required(self):
        repo = fx.p1_base()
        run = self.open_only(repo)[0]
        args = ["prop-new", "--run", run, *fx.good_prop_args(repo, "P")]
        rc, out, _ = self.M(repo, *args)
        self.rejected(rc, out, {"RESEARCH-MISSING"})
        self.cli_ok(
            repo, "research", "--skip", "--run", run, "--reason", "offline", "--note", "離線驗證"
        )
        self.cli_ok(repo, *args)
        cases = {
            "a": [fx.run_open_ev(1), fx.prop_ev(124, 1)],
            "b": [fx.run_open_ev(1), fx.prop_ev(124, 1), fx.skip_ev(1)],
            "c": [fx.run_open_ev(1), fx.skip_ev(1), fx.skip_ev(1)],
            "d": [fx.run_open_ev(1)],
            "e": [fx.run_open_ev(1), fx.skip_ev(1), fx.prop_ev(124, 1)],
        }
        want = {
            "a": {(rid(1), "RESEARCH-MISSING")},
            "b": {(rid(1), "RESEARCH-ORDER")},
            "c": {(rid(1), "RESEARCH-MULTIPLE")},
            "d": set(),
            "e": set(),
        }
        for key, events in cases.items():
            r = fx.p1_base()
            fx.write_events(r, events)
            res = self.check(r)
            carrier = {("-", "CARRIER-NOT-ESTABLISHED")}  # P6 AC-SI-45-3：各例皆有
            self.assertEqual(self.F(res, "events.research") - carrier, want[key], key)
            if key in ("d", "e"):  # P6（AC-SI-45-3）：無鏡像無事件＝nonblocking NE，別無 finding
                codes = [f["code"] for f in res["_item"]["events.research"]["findings"]]
                self.assertEqual((self.S(res, "events.research"), codes),
                                 ("NE", ["CARRIER-NOT-ESTABLISHED"]), key)
            if key == "c":
                detail = res["_item"]["events.research"]["findings"][0]["detail"]
                self.assertTrue("2" in detail and "3" in detail, detail)

    def test_AT_130_1_E_1_skip_reasons_and_rejections(self):
        repo = fx.p1_base()
        runs = self.open_only(repo, 4)
        self.cli_ok(repo, "run-close", "--run", runs[3], "--by", "main")
        snap0, n0 = fx.snap(repo), len(fx.EV(repo))
        sid = fx.UUID
        self.assertEqual(
            self.M(
                repo,
                "research",
                "--skip",
                "--run",
                runs[0],
                "--reason",
                "quota-band",
                "--band",
                "high",
                "--note",
                "額度帶非 free",
            )[1],
            f"ok research.skip seq={n0 + 1} run={runs[0]} reason=quota-band\n",
        )
        self.cli_ok(
            repo,
            "research",
            "--skip",
            "--run",
            runs[1],
            "--reason",
            "helmsman",
            "--sid",
            sid,
            "--line",
            "12",
            "--note",
            "掌舵者明示免掃",
        )
        self.cli_ok(
            repo, "research", "--skip", "--run", runs[2], "--reason", "offline", "--note", "離線"
        )
        events = fx.EV(repo)[n0:]
        self.assertTrue(all(e["by"] == "main" for e in events))
        self.assertEqual(
            [list(e)[4:] for e in events],
            [
                ["run", "reason", "note", "band"],
                ["run", "reason", "note", "sid", "line"],
                ["run", "reason", "note"],
            ],
        )
        self.assertEqual(events[1]["line"], 12)
        base = ["research", "--skip", "--run", runs[0]]
        usage = [
            ["--reason", "bogus", "--note", "x"],
            ["--reason", "offline", "--note", ""],
            ["--reason", "offline", "--note", "x" * 121],
            ["--reason", "offline", "--note", "a\nb"],
            ["--reason", "quota-band", "--note", "x"],
            ["--reason", "quota-band", "--note", "x", "--band", "free"],
            ["--reason", "quota-band", "--note", "x", "--band", "Free"],
            ["--reason", "helmsman", "--note", "x", "--line", "3"],
            ["--reason", "helmsman", "--note", "x", "--sid", sid],
            ["--reason", "helmsman", "--note", "x", "--sid", "not-a-uuid", "--line", "3"],
            ["--reason", "helmsman", "--note", "x", "--sid", sid, "--line", "0"],
            ["--reason", "helmsman", "--note", "x", "--sid", sid, "--line", "abc"],
            ["--reason", "offline", "--note", "x", "--band", "high"],
        ]
        for extra in usage:
            with self.subTest(extra=extra):
                self.usage_error(*self.M(repo, *base, *extra), msg=str(extra))
        self.usage_error(*self.M(repo, "research", "--run", runs[0]))
        self.usage_error(*self.M(repo, "research", "--fetch", "--skip", "--run", runs[0]))
        n1 = len(fx.EV(repo))
        for run, code in (
            (runs[0], "RESEARCH-ALREADY"),
            (runs[3], "RUN-NOT-OPEN"),
            (rid(900 + 4), "RUN-NOT-OPEN"),
        ):
            rc, out, _ = self.M(
                repo, "research", "--skip", "--run", run, "--reason", "offline", "--note", "x"
            )
            self.rejected(rc, out, {code})
            self.draft_ok(repo, out)
        self.assertEqual(len(fx.EV(repo)), n1)
        res = self.check(repo)
        # P2 R98：QUOTE warn 移除；helmsman 免掃改由座標回查（逐字稿取不到＝nonblocking NE）
        found = self.F(res, "events.research")
        self.assertNotIn(("-", "QUOTE-VERIFIER-NOT-ESTABLISHED"), found)
        self.assertEqual({c for _, c in found},  # P6 加 CARRIER-NOT-ESTABLISHED（AC-SI-45-3）
                         {"TRANSCRIPT-UNAVAILABLE", "CARRIER-NOT-ESTABLISHED"})
        self.assertEqual((res["overall"], res["_rc"]), ("PASS", 0))
        self.assertTrue(snap0 and n0)


class TestSourceTable(ResearchCase):
    def good_entry(self, **kw):
        e = {
            "id": "a-src",
            "url": "https://example.com/x.md",
            "kind": "docs",
            "extract": "讀",
            "added_by": "T1",
        }
        e.update(kw)
        return e

    def raw(self, obj=None, **kw):
        obj = obj if obj is not None else {"schema_rev": 1, "sources": [self.good_entry(**kw)]}
        return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    def table_of(self, urls):
        entries = [self.good_entry(id=f"s{i}", url=u) for i, u in enumerate(urls)]
        return self.raw({"schema_rev": 1, "sources": entries})

    def test_AT_230_2_1_ascii_hosts_are_accepted(self):
        urls = ["https://example.org/a", "https://docs.example.co.uk/b",
                "https://a-b.example.net/c", "https://example.org:8443/d",
                "https://axn--b.example/e", "https://xn-b.example/f", "https://EXAMPLE.ORG/g"]
        got = si_sources.validate_table(self.table_of(urls), si_sources.DEFAULT_POLICY)
        self.assertEqual([x for x in got if x[0] == "SRC-URL-HOST"], [])
        real = fx.REAL_PARAMS.parent / "research_sources.json"
        if real.is_file():
            self.assertEqual(si_sources.validate_table(real.read_bytes(),
                                                       si_sources.DEFAULT_POLICY), [])

    def test_AT_230_2_E_1_non_ascii_hosts_are_rejected(self):
        bad = ["https://１２７.0.0.1/x", "https://ｅｘａｍｐｌｅ.org/", "https://example。org/x",
               "https://例え.jp/", "https://xn--e1afmkfd.xn--p1ai/", "https://XN--abc.example/",
               "https://a.Xn--b.example/", "https://sub.xn--x.example.org/"]
        with mock.patch("socket.getaddrinfo", side_effect=AssertionError("連線")), \
                mock.patch("socket.create_connection", side_effect=AssertionError("連線")):
            for url in bad:
                with self.subTest(url):
                    raw = self.table_of([url, "https://example.org/ok"])
                    got = si_sources.validate_table(raw, si_sources.DEFAULT_POLICY)
                    self.assertEqual({(c, s) for c, s, _ in got}, {("SRC-URL-HOST", "s0")})
                    self.assertTrue(any("非 ASCII 或 IDNA 形態" in d for _, _, d in got))
        repo = fx.p1_base()
        fx.put(repo, fx.SRC_REL, self.table_of([bad[0]]).decode("utf-8"))
        res = self.check(repo)
        self.assertEqual(self.S(res, "research.sources"), "FAIL")
        self.assertIn(("s0", "SRC-URL-HOST"), self.F(res, "research.sources"))
        self.assertEqual(res["_rc"], 1)


class TestSourcesHistory(ResearchCase):
    @staticmethod
    def scan_event(run, table_sha, t, ids=("s-live",)):
        srcs = [
            {"id": i, "sha256": fx.H(9), "bytes": 3, "changed": True, "http_status": 200}
            for i in ids
        ]
        return ev(
            "research.scan",
            "researcher",
            run=rid(run),
            sources=srcs,
            sources_sha256=table_sha,
            fetched_at=t,
            t=t,
        )


class TestFetching(ResearchCase):

    def test_AT_130_3_E_5_content_type_allowlist_is_pinned(self):
        """受測 `tools/lib/selfimproving/fetch.py`：可接受的 Content-Type 集合逐一釘住。"""
        ok = (
            "text/plain",
            "text/html; charset=utf-8",
            "application/json",
            "application/xml",
            "application/atom+xml",
            "application/rss+xml",
            "application/xhtml+xml",
        )
        bad = (
            "application/octet-stream",
            "image/png",
            "application/pdf",
            "application/x-ndjson",
            "application/javascript",
        )
        def call(ctype):  # P6：改走 `fetch_chain` 與 `px.net` 注入縫（舊 `fetch_source` 已移除）
            table = {("www.x.org", "/t"): px.response(ctype=ctype, body=b"12345")}
            with px.net(table):
                return si_fetch.fetch_chain("https://www.x.org/t", hosts={"www.x.org"},
                                            timeout=5, max_bytes=1000)

        for ctype in ok:
            got = call(ctype)
            self.assertEqual((got.status, got.raw), (200, b"12345"), ctype)
        for ctype in bad:
            with self.assertRaises(si_fetch.FetchError, msg=ctype) as cm:
                call(ctype)
            self.assertEqual((cm.exception.reason, cm.exception.detail), ("non-text", ctype))


class TestResearcherRows(ResearchCase):
    ROW = [
        obs_id(11),
        "2026-10-20 01:00",
        "情境",
        "症狀",
        "tools/lib/selfimproving/fresh.py:1",
        "bug",
        "P3",
        "open",
        "",
    ]

    def table(self):
        return (
            json.dumps(
                {
                    "schema_rev": 1,
                    "sources": [
                        {
                            "id": "cc-note",
                            "url": "https://example.com/a.md",
                            "kind": "docs",
                            "extract": "讀",
                            "added_by": "T1",
                        }
                    ],
                },
                indent=2,
            )
            + "\n"
        )

    def repo_with_row(self, marks, commit_row=False):
        row = [*self.ROW[:8], marks]
        repo = fx.make_p1_repo(
            fx.new_dir("rr"), sources=self.table(), extra_obs=[row] if commit_row else ()
        )
        if not commit_row:
            fx.put(repo, LEDGER, fx.read(repo, LEDGER).rstrip("\n") + "\n" + fx.line(row) + "\n")
        return repo

    def test_AT_130_4_1_researcher_candidate_accepted(self):
        marks = "面=流程;來源=代理;回報者=研究者;外部衍生=是;src=cc-note"
        repo = self.repo_with_row(marks, commit_row=True)
        res = self.check(repo)
        for item in ("row.provenance", "row.markers"):
            self.assertEqual({s for s, _ in self.F(res, item)} & {obs_id(11)}, set())
        run = self.open_run(repo)
        self.cli_ok(
            repo,
            "prop-new",
            "--run",
            run,
            *fx.good_prop_args(repo, "D", sources=[obs_id(11), obs_id(1)]),
        )
        self.assertEqual(fx.EV(repo)[-1]["sources"], [obs_id(11), obs_id(1)])

    def test_AT_130_4_E_1_researcher_chain_rejections(self):
        base = "面=流程;來源=代理;"
        res = self.check(self.repo_with_row(base + "回報者=研究者;src=cc-note"))
        self.assertEqual(self.F(res, "row.provenance"), {(obs_id(11), "RESEARCHER-NOT-EXTERNAL")})
        res = self.check(self.repo_with_row(base + "回報者=研究者;外部衍生=是"))
        self.assertEqual(self.F(res, "row.provenance"), {(obs_id(11), "RESEARCHER-NO-SRC")})
        res = self.check(self.repo_with_row(base + "回報者=研究者;外部衍生=是;src=zz-unknown"))
        self.assertEqual(self.F(res, "row.markers"), {(obs_id(11), "SRC-UNKNOWN")})
        repo = self.repo_with_row(base + "回報者=研究者;外部衍生=是;src=cc-note", commit_row=True)
        run = self.open_run(repo)
        snap0 = fx.snap(repo)
        md = fx.memory_dir(fx.new_dir("mem"))
        for cls in ("M", "P", "R", "D"):
            over = dict(sources=[obs_id(11)])
            if cls == "M":
                over.update(memory_dir=md, body=fx.body_md("M", source_obs=obs_id(11)))
            rc, out, _ = self.M(
                repo, "prop-new", "--run", run, *fx.good_prop_args(repo, cls, **over)
            )
            self.rejected(rc, out, {"NO-INTERNAL-SOURCE"}, cls)
            self.draft_ok(repo, out, cls)
        self.assertEqual(fx.snap(repo), snap0)


class TestBudgetsAndFingerprint(ResearchCase):
    """受測：`tools/lib/selfimproving/fetch.py`／`research.py`（抓取預算與來源表指紋）。"""

    def table_url_repo(self, url: str) -> Path:
        repo = fx.p1_base()
        self.open_only(repo)
        fx.putb(repo, SRC_REL, raw_table(url))
        fx.commit_all(repo, "sources")
        return repo

    def test_AT_130_5_E_4_deadline_reader_contract_and_race(self):
        """受測 `tools/lib/selfimproving/fetch.py`：`_DeadlineRaw` 期限已過不碰 socket。"""
        for label, delta in (("past", -1.0), ("now", None)):
            sock = FakeSock()
            deadline = time.monotonic() + delta if delta is not None else time.monotonic()
            with self.assertRaises(TimeoutError, msg=label):
                si_fetch._DeadlineRaw(sock, deadline).readinto(bytearray(16))
            self.assertEqual(sock.calls, [], label)
        sock, buf = FakeSock(), bytearray(16)
        self.assertEqual(si_fetch._DeadlineRaw(sock, time.monotonic() + 5.0).readinto(buf), 5)
        self.assertEqual(bytes(buf[:5]), b"hello")
        self.assertEqual([c[0] for c in sock.calls], ["settimeout", "recv_into"])
        self.assertTrue(0 < sock.calls[0][1] <= 5.0, sock.calls)
        # 滴流／停滯的牆鐘：改由 AT-630-3-E-4（請求鏈牆鐘）以偽時鐘驗，見檔頂對照表

    def test_AT_130_5_E_5_unparsable_content_length_counts_as_absent(self):
        """受測 `tools/lib/selfimproving/fetch.py`：無法解析的 Content-Length 視同未提供。"""
        def get(content_length: str, body: bytes):
            table = {("www.x.org", "/p"): px.response(
                headers={"Content-Length": content_length}, body=body)}
            with px.net(table):
                return si_fetch.fetch_chain("https://www.x.org/p", hosts={"www.x.org"},
                                            timeout=2, max_bytes=100)

        for length in ("²", "¹", "5²", "abc", "5"):  # 無法解析的 Content-Length 視同未提供
            got = get(length, b"hello")
            self.assertEqual((got.raw, got.status), (b"hello", 200), length)
        with self.assertRaises(si_fetch.FetchError) as cm:
            get("²", b"b" * 101)
        self.assertEqual(cm.exception.reason, "too-large")

    def test_AT_130_6_1_sources_excluded_from_fingerprint(self):
        repo = fx.p1_base()
        f0 = self.check(repo)["fingerprint"]
        table = {
            "schema_rev": 1,
            "sources": [
                {
                    "id": "a-src",
                    "url": "https://example.com/x.md",
                    "kind": "docs",
                    "extract": "讀",
                    "added_by": "T1",
                }
            ],
        }
        fx.put(repo, SRC_REL, json.dumps(table, indent=2) + "\n")
        self.assertEqual(self.check(repo)["fingerprint"], f0)
        table["sources"][0]["extract"] = "改過"
        fx.put(repo, SRC_REL, json.dumps(table, indent=2) + "\n")
        res = self.check(repo)
        self.assertEqual(res["fingerprint"], f0)

    def test_AT_130_6_E_1_other_protocol_files_change_fingerprint(self):
        base = fx.p1_base()
        f0 = self.check(base)["fingerprint"]
        proto = "docs/06_quality/SelfImproving_Protocol"

        def variant(fn):
            repo = fx.new_dir("fp")
            shutil.copytree(base, repo)
            fn(repo)
            return self.check(repo)["fingerprint"]

        cases = {
            "a": lambda r: fx.set_params(r, max_new_entries=4),
            "b": lambda r: fx.put(r, f"{proto}/metrics.md", "metrics 改一個字\n"),
            "c": lambda r: fx.put(r, f"{proto}/extra.json", "{}\n"),
            "d": lambda r: fx.put(r, f"{proto}/sub/research_sources.json", "{}\n"),
            "e": lambda r: fx.set_params(r, metrics_rev=2),
        }
        for key, fn in cases.items():
            self.assertNotEqual(variant(fn), f0, key)


STATUS_CORPUS = [
    ("open", "open"),
    ("open（workaround-applied）", "open"),
    ("partial（只修了一半）", "open"),
    ("workaround", "open"),
    ("修復後open尚待驗證", "open"),
    ("open；後續 fixed", "open"),
    ("fixed@abc1234", "fixed"),
    ("fixed", "fixed"),
    ("fixed；後續 open", "fixed"),
    ("wontfix", "wontfix"),
    ("closed-by-decision", "closed-by-decision"),
    ("no_action_needed", "closed-by-decision"),
    ("no action needed", "closed-by-decision"),
    ("routed：外部", "routed"),
    ("reopened", None),
    ("unfixed", None),
    ("Fixed", None),
    ("", None),
    ("deferred；再開症狀：x", None),
]
DEF_HDR7 = fx.DEF_HDR


class ScanCase(SiTestCase):
    def scan_repo(self, quiet: bool = False) -> Path:
        ta = (datetime.now().astimezone() - timedelta(days=1)).replace(microsecond=0)
        utc = ta.astimezone(UTC)
        d0, dm1 = utc.strftime("%Y-%m-%d"), (utc - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = [
            (fx.def_id(11), d0, "P2", "open", "tools/a11.py:1"),
            (fx.def_id(12), d0, "P1", "open（workaround-applied）", "tools/a12.py:1"),
            (fx.def_id(13), d0, "P3", "open", "tools/a13.py:1"),
            (fx.def_id(14), d0, "P2", "fixed@abc1234", "tools/a14.py:1"),
            (fx.def_id(15), dm1, "P2", "open", "tools/a15.py:1"),
        ]
        events = [
            fx.run_open_ev(1),
            ev("run.close", "main", run=rid(1), no_event=True, t=ta.isoformat(timespec="seconds")),
        ]
        repo = fx.make_p1_repo(fx.new_dir("sc"), defs=rows[2:] if quiet else rows, events=events)
        if not quiet:
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            plan = [
                ("K1", ["AutoClaude/x.py", "AutoClaude/y.py"]),
                ("K2", ["AISDLC_SDD/z.md"]),
                ("K3", ["tools/lib/selfimproving/w.py"]),
                ("K4", ["tools/other.py", "AgentConsole/c.ts"]),
                ("K5", ["docs/06_quality/SelfImproving_Foo.md"]),
            ]
            for name, files in plan:
                for f in files:
                    fx.put(repo, f, name + "\n")
                fx.commit_all(repo, name, when=now)
        return repo

    def scan_json(self, repo, *extra):
        rc, out, err = self.M(repo, "scan", "--json", *extra)
        self.assertEqual(rc, 0, out + err)
        return json.loads(out)


class TestScan(ScanCase):
    def test_AT_131_1_1_scan_is_pure(self):
        repo = self.scan_repo()
        snap0, head0 = fx.snap(repo), fx.head(repo)
        sentinel = self.home / "sentinel.txt"
        sentinel.write_bytes(b"s")
        home0 = (fx.tree_files(self.home), sentinel.read_bytes())
        popen_calls, run_kwargs = [], []
        real_popen, real_run = subprocess.Popen, subprocess.run

        class Rec(real_popen):
            def __init__(self, args, *a, **kw):
                popen_calls.append((list(args), kw))
                super().__init__(args, *a, **kw)

        def run(args, *a, **kw):
            run_kwargs.append(kw)
            return real_run(args, *a, **kw)

        with (
            mock.patch.object(socket.socket, "connect", side_effect=AssertionError("連線")),
            mock.patch.object(subprocess, "Popen", Rec),
            mock.patch.object(subprocess, "run", run),
        ):
            rc1, out1, _ = self.M(repo, "scan")
            rc2, out2, _ = self.M(repo, "scan", "--json")
            with mock.patch.dict(
                os.environ,
                {"GIT_DIR": str(fx.new_dir("elsewhere")), "GIT_INDEX_FILE": str(fx.new_dir("idx"))},
            ):
                rc3, out3, _ = self.M(repo, "scan", "--json")
        self.assertEqual((rc1, rc2, rc3), (0, 0, 0))
        self.assertEqual((fx.snap(repo), fx.head(repo)), (snap0, head0))
        self.assertEqual((fx.tree_files(self.home), sentinel.read_bytes()), home0)
        self.assertTrue(popen_calls)
        resolved = str(repo.resolve())
        for argv, kw in popen_calls:
            self.assertEqual(argv[:3], [si_git.resolve_git(os.environ), "-C", resolved])
            env = kw["env"]
            self.assertFalse({"GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"} & set(env))
            self.assertEqual(env["GIT_OPTIONAL_LOCKS"], "0")
        self.assertTrue(all("timeout" in k and "encoding" in k for k in run_kwargs))
        self.assertEqual(norm_time(out2), norm_time(out3))
        rc, out, _ = self.run_main(["scan", "--help"])
        self.assertEqual(rc, 0)
        flags = set(re.findall(r"(?m)^\s+(?:-\w, )?(--[a-z]+)", out))
        self.assertEqual(flags, {"--json", "--since", "--repo", "--help"})
        self.assertTrue(out1)

    def test_AT_131_1_E_1_scan_flags(self):
        repo = self.scan_repo()
        snap0 = fx.snap(repo)
        today = datetime.now().strftime("%Y-%m-%d")
        plain = fx.new_dir("plain")
        plain.write_bytes(b"x")
        calls = [
            ["--count", "5"],
            ["--limit", "5"],
            ["--date", today],
            ["--schedule", "daily"],
            ["--since", today],
            ["--since", "yesterday"],
            ["--since", "HEAD~1"],
            ["--since", "3"],
            ["--since", "0" * 40],
        ]
        for extra in calls:
            self.usage_error(*self.M(repo, "scan", *extra), msg=str(extra))
        self.usage_error(*self.run_main(["scan", "--repo", str(plain)]))
        rc, out, err = self.M(repo, "scan", "--since", fx.head(repo)[:7])
        self.assertEqual(rc, 0, err)
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_131_2_1_candidate_rows(self):
        repo = self.scan_repo()
        snap0 = fx.snap(repo)
        res = self.scan_json(repo)
        by_src = {
            "defects": [c for c in res["candidates"] if c["bucket"] == "defects"],
            "obs": [c for c in res["candidates"] if c["bucket"] != "defects"],
        }
        self.assertEqual(
            sorted(re.search(r"DEF-\d+-\d+", c["row"]).group(0) for c in by_src["defects"]),
            [fx.def_id(11), fx.def_id(12)],
        )
        self.assertEqual(
            sorted(c["bucket"] for c in by_src["obs"]),
            sorted(["AutoClaude", "AISDLC_SDD", "SelfImproving", "根層", "AgentConsole"]),
        )
        rows = [c["row"] for c in res["candidates"]]
        for i, (cand, row) in enumerate(zip(res["candidates"], rows, strict=True)):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            self.assertEqual(len(cells), 9)
            self.assertLessEqual(len(row.encode("utf-8")), 700)
            self.assertEqual(cells[0], obs_id(11 + i))
            # P2 R103：模組桶候選列是計數資訊（process／P4／decided：僅計數）；缺陷候選列維持原樣
            want = (("bug", "P3", "open") if cand["bucket"] == "defects"
                    else ("process", "P4", "decided：僅計數"))
            self.assertEqual(
                (cells[2], cells[5], cells[6], cells[7], cells[8]),
                ("si scan（自動草稿）", *want, "面=流程;來源=工具;回報者=scan"),
            )
        self.assertTrue(all(re.search(r"commit [0-9a-f]{12}", c["row"]) for c in by_src["obs"]))
        copy = fx.new_dir("cp")
        shutil.copytree(repo, copy)
        fx.put(copy, LEDGER, fx.read(copy, LEDGER).rstrip("\n") + "\n" + "\n".join(rows) + "\n")
        chk = self.check(copy)
        ids = {obs_id(11 + i) for i in range(len(rows))}
        bad = [
            (i["id"], f["code"])
            for i in chk["items"]
            for f in i["findings"]
            if f["subject"] in ids and f["code"] != "REOPEN-CANDIDATE"
        ]
        self.assertEqual(bad, [])
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_131_2_E_3_commit_at_anchor_is_outside_the_window(self):
        """受測 `tools/lib/selfimproving/scan.py`：committer 時間恰等於起算時刻者不計入窗。"""
        repo = self.scan_repo(quiet=True)
        ta = datetime.fromisoformat(
            next(e for e in fx.EV(repo) if e["kind"] == "run.close")["t"]
        )
        fx.put(repo, "AutoClaude/x.py", "K1\n")
        fx.commit_all(repo, "K1", when=ta.isoformat(timespec="seconds"))
        fx.put(repo, "AISDLC_SDD/z.md", "K2\n")
        k2 = fx.commit_all(
            repo, "K2", when=(ta + timedelta(seconds=1)).isoformat(timespec="seconds")
        )
        snap0 = fx.snap(repo)
        res = self.scan_json(repo)
        self.assertEqual(res["anchor"]["kind"], "run.close")
        self.assertEqual(datetime.fromisoformat(res["anchor"]["time"]), ta)
        self.assertEqual(res["buckets"], {"AISDLC_SDD": 1})
        (cand,) = res["candidates"]
        self.assertEqual(cand["bucket"], "AISDLC_SDD")
        self.assertIn(f"commit {k2[:12]}", cand["row"])
        self.assertEqual(fx.snap(repo), snap0)

    def test_AT_131_2_E_1_row_cap_and_header(self):
        repo = self.scan_repo(quiet=True)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        for i in range(40):
            fx.put(repo, f"AutoClaude/{'d' * 28}/{'f' * 20}_{i:02d}.py", "x\n")
        fx.commit_all(repo, "many", when=now)
        res = self.scan_json(repo)
        row = next(c["row"] for c in res["candidates"] if c["bucket"] == "AutoClaude")
        self.assertLessEqual(len(row.encode("utf-8")), 700)
        self.assertRegex(row, r"commit [0-9a-f]{12}")
        copy = fx.new_dir("cp")
        shutil.copytree(repo, copy)
        fx.put(copy, LEDGER, fx.read(copy, LEDGER).rstrip("\n") + "\n" + row + "\n")
        chk = self.check(copy)
        rid_ = row.split("|")[1].strip()
        self.assertEqual(
            [
                (i["id"], f["code"])
                for i in chk["items"]
                for f in i["findings"]
                if f["subject"] == rid_ and f["code"] != "REOPEN-CANDIDATE"
            ],
            [],
        )
        repo2 = self.scan_repo(quiet=True)
        fx.put(repo2, fx.DEFLOG, "| ID | 狀態 |\n|---|---|\n| " + fx.def_id(1) + " | open |\n")
        res = self.scan_json(repo2)
        src = next(s for s in res["sources"] if s["id"] == "defects")
        self.assertEqual((src["status"], src["reason"]), ("unavailable", "ledger-header"))
        self.assertGreaterEqual(res["unavailable_count"], 1)
        self.assertIn("source defects 量不到：ledger-header", self.M(repo2, "scan")[1])

    def test_AT_131_2_E_2_defs_differential(self):
        import check_defect_log_crossref as cdl

        for text, expected in STATUS_CORPUS:
            self.assertEqual(si_defs.classify_status(text), cdl._classify(text), text)
            self.assertEqual(si_defs.classify_status(text), expected, text)
        d = fx.def_id

        def table(rows, header=DEF_HDR7):
            body = "\n".join(fx.line(r) for r in rows)
            return (
                (header + "\n|---|---|---|---|---|---|---|\n" + body + "\n")
                if header
                else body + "\n"
            )

        def row(n, status, evidence="x", extra=""):
            return [d(n), "2026-09-01", "夾具", evidence + extra, "P2", "-", status]

        ledgers = {
            "a": table(
                [row(1, "open"), row(2, "fixed@abc1234"), row(3, "wontfix"), row(4, "routed：外部")]
            ),
            "b": table([row(1, "open"), row(1, "fixed@abc1234")]),
            "c": table([row(1, "open", "x", " | 多一欄")]),
            "d": table([row(1, " ")]),
            "e": table([row(1, "open")], header=None),
        }
        expect = {
            "a": {d(1): "open", d(2): "fixed", d(3): "wontfix", d(4): "routed"},
            "b": {d(1): "fixed"},
            "c": {d(1): None},
            "d": {d(1): None},
            "e": {},
        }
        tmp = fx.new_dir("dl")
        tmp.mkdir()
        for key, text in ledgers.items():
            path = tmp / f"{key}.md"
            path.write_bytes(text.encode("utf-8"))
            with mock.patch.object(cdl, "_DEFECT_LOG", path):
                theirs = cdl._load_ledger_status()
            self.assertEqual(si_defs.load_ledger_status(path), theirs, key)
            self.assertEqual(theirs, expect[key], key)

    def test_AT_131_3_1_zero_candidates(self):
        repo = self.scan_repo(quiet=True)
        rc, out, err = self.M(repo, "scan")
        self.assertEqual(rc, 0, err)
        lines = out.strip().split("\n")
        self.assertEqual(
            [ln.split(" ")[1] for ln in lines[:5]],
            ["defects", "observations", "event_ledger", "build_reports", "probe_outputs"],
        )
        # P2 R103：只計數、未解析內容的三個來源改「計 N 筆（未解析內容）」
        want = [r"^source defects 讀到 \d+ 筆$", r"^source observations 計 \d+ 筆（未解析內容）$",
                r"^source event_ledger 讀到 \d+ 筆$",
                r"^source build_reports 計 \d+ 筆（未解析內容）$",
                r"^source probe_outputs 計 \d+ 筆（未解析內容）$"]
        self.assertTrue(all(re.match(rx, ln) for rx, ln in zip(want, lines[:5], strict=True)),
                        lines)
        self.assertEqual(lines[5:], ["無事件"])
        res = self.scan_json(repo)
        self.assertEqual(
            (res["status"], res["unavailable_count"], res["candidates"]), ("no-event", 0, [])
        )
        self.assertTrue(all(s["status"] == "read" for s in res["sources"]))
        self.assertEqual(res["anchor"]["kind"], "run.close")
        for text in (out, json.dumps(res, ensure_ascii=False)):
            self.assertFalse(any(w in text for w in ("通過", "達標", "綠")))

    def test_AT_131_3_E_1_unavailable_sources(self):
        def line_of(out, sid):
            return next(ln for ln in out.split("\n") if ln.startswith(f"source {sid} "))

        def run(repo):
            rc, out, err = self.M(repo, "scan")
            self.assertEqual(rc, 0, err)
            self.assertFalse(any(w in out for w in ("通過", "達標", "綠")))
            return out

        repo = self.scan_repo(quiet=True)
        (repo / EVL).unlink()
        out = run(repo)
        self.assertEqual(line_of(out, "defects"), "source defects 量不到：anchor-unavailable")
        self.assertEqual(
            line_of(out, "observations"), "source observations 量不到：anchor-unavailable"
        )
        self.assertEqual(
            line_of(out, "event_ledger"), "source event_ledger 量不到：carrier-not-established"
        )
        self.assertTrue(out.strip().endswith("無事件（3 個來源量不到）"))
        repo = self.scan_repo(quiet=True)
        (repo / fx.DEFLOG).unlink()
        out = run(repo)
        self.assertEqual(line_of(out, "defects"), "source defects 量不到：ledger-missing")
        self.assertTrue(out.strip().endswith("無事件（1 個來源量不到）"))
        repo = self.scan_repo(quiet=True)
        fx.put(repo, fx.DEFLOG, "| ID | 狀態 |\n|---|---|\n")
        out = run(repo)
        self.assertEqual(line_of(out, "defects"), "source defects 量不到：ledger-header")
        repo = self.scan_repo(quiet=True)
        nogit = fx.new_dir("nogit")
        shutil.copytree(repo, nogit, ignore=shutil.ignore_patterns(".git"))
        out = run(nogit)
        self.assertEqual(
            line_of(out, "observations"), "source observations 量不到：git-unavailable"
        )
        repo = self.scan_repo(quiet=True)
        (repo / "build/reports/pytest.log").unlink()
        out = run(repo)
        self.assertEqual(line_of(out, "build_reports"), "source build_reports 量不到：no-artifacts")
        self.assertTrue(out.strip().endswith("無事件（1 個來源量不到）"))
        repo = self.scan_repo(quiet=True)
        (repo / "docs/06_quality/misstep_attribution_demo.jsonl").unlink()
        out = run(repo)
        self.assertEqual(line_of(out, "probe_outputs"), "source probe_outputs 量不到：no-artifacts")
        repo = self.scan_repo()
        (repo / "build/reports/pytest.log").unlink()
        out = run(repo)
        m = re.search(r"候選 (\d+) 筆", out)
        self.assertTrue(m and int(m.group(1)) >= 1)
        self.assertEqual(line_of(out, "build_reports"), "source build_reports 量不到：no-artifacts")

    def test_AT_131_4_1_bucket_order(self):
        b = si_scan.bucket_of
        for p in (
            "tools/lib/selfimproving/check.py",
            "tools/selfimproving.py",
            "tools/probe/selfimproving_measure.py",
            "tools/tests/test_selfimproving_check.py",
            "docs/06_quality/SelfImproving_Observation_Ledger.md",
            "docs/05_development/SelfImproving_Operations_SOP.md",
        ):
            self.assertEqual(b(p), "SelfImproving", p)
        self.assertEqual(b("AutoClaude/autoclaude/main.py"), "AutoClaude")
        self.assertEqual(b("AutoClaude/docs/SelfImproving_note.md"), "AutoClaude")
        self.assertEqual(b("AISDLC_SDD/FRAMEWORK_STATUS.md"), "AISDLC_SDD")
        self.assertEqual(b("AgentConsole/CLAUDE.md"), "AgentConsole")
        for p in (
            "tools/other.py",
            "tools/tests/test_root_module_layout.py",
            "docs/06_quality/AutoSDD_Defect_Log.md",
            "CLAUDE.md",
        ):
            self.assertEqual(b(p), "根層", p)

    def test_AT_131_4_E_1_bucket_edges(self):
        for p in ("/etc/x.md", "../x.md", "docs/../x.md", "", "X" + ":/x.md"):
            self.assertEqual(si_scan.bucket_of(p), "未分類", p)
        repo = self.scan_repo(quiet=True)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        fx.put(repo, "AutoClaude/a.py", "x\n")
        fx.put(repo, "tools/other.py", "x\n")
        fx.commit_all(repo, "both", when=now)
        res = self.scan_json(repo)
        self.assertEqual(res["buckets"], {"AutoClaude": 1, "根層": 1})


def _real_text() -> str:
    return fx.REAL_SOP.read_bytes().decode("utf-8").replace("\r\n", "\n")


class TestResearcherAndTemplateArticles(SiTestCase):
    def test_AT_130_4_2_researcher_section(self):
        text = _real_text()
        frags = [f for k, f in fx.FRAGMENTS if k == "研究者"]
        self.assertEqual(len(frags), 12)
        sec = fx.sop_section(text, "研究者")
        self.assertTrue(all(f in sec for f in frags))
        for frag in frags:
            copy = fx.remove_in_section(text, "研究者", frag)
            probs = fx.sop_problems(copy)
            self.assertTrue(probs and frag in " ".join(probs), frag)

    def test_AT_131_5_1_template_matches_prd(self):
        text = _real_text()
        prd = fx.REAL_PRD.read_bytes().decode("utf-8").replace("\r\n", "\n")
        tmpl = fx._tmpl(fx.sop_section(text, "歸因者"))
        self.assertTrue(tmpl)
        need = [
            "AutoClaude",
            "AISDLC_SDD",
            "AgentConsole",
            "根層",
            "SelfImproving",
            "Read／Grep／Glob／PowerShell",
            "唯讀",
            "不得 Write／Edit",
            "git status --porcelain",
            "文字交卷",
            "流程摩擦",
            "不並行扇出",
            "零遞迴",
        ]
        self.assertTrue(all(n in tmpl for n in need), [n for n in need if n not in tmpl])
        entry = fx.prd_entry_fragments(prd)
        self.assertGreaterEqual(len(entry), 10)
        self.assertTrue(all(f in tmpl for f in entry), [f for f in entry if f not in tmpl])

    def test_AT_131_5_E_1_template_criteria_and_tree_state(self):
        text = _real_text()
        prd = fx.REAL_PRD.read_bytes().decode("utf-8").replace("\r\n", "\n")
        need = [
            "AutoClaude",
            "AISDLC_SDD",
            "AgentConsole",
            "根層",
            "SelfImproving",
            "Read／Grep／Glob／PowerShell",
            "唯讀",
            "不得 Write／Edit",
            "git status --porcelain",
            "文字交卷",
            "流程摩擦",
            "不並行扇出",
            "零遞迴",
        ]
        for frag in [*need, *fx.prd_entry_fragments(prd)]:
            copy = fx.remove_in_section(text, "歸因者", frag, "模組體檢")
            probs = fx.sop_problems(copy, prd)
            self.assertTrue(probs and frag in " ".join(probs), frag)
        repo = fx.p1_base()
        before = fx.tree_state(repo)
        self.assertEqual(fx.tree_state(repo), before)
        fx.put(repo, "untracked_new.txt", "x\n")
        self.assertNotEqual(fx.tree_state(repo), before)
        repo = fx.p1_base()
        fx.put(repo, "docs/notes/demo.md", "改過\n")
        self.assertNotEqual(fx.tree_state(repo), before if False else fx.tree_state(fx.p1_base()))
        repo = fx.p1_base()
        fx.put(repo, "docs/notes/tiny.md", "x\n")
        fx.commit_all(repo, "new commit")
        self.assertNotEqual(fx.tree_state(repo), fx.tree_state(fx.p1_base()))
        repo = fx.p1_base()
        before = fx.tree_state(repo)
        fx.put(repo, "ignored/secret.txt", "x\n")
        self.assertEqual(fx.tree_state(repo), before)


class TestScanP2(ScanCase):
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    def _candidates(self, repo):
        obj = self.scan_json(repo)
        return obj, [c["row"] for c in obj["candidates"]]

    def test_AT_240_10_1_informational_drafts(self):
        repo = self.scan_repo()
        rc, text, err = self.M(repo, "scan")
        self.assertEqual(rc, 0, err)
        for sid in ("observations", "build_reports", "probe_outputs"):
            self.assertRegex(text, rf"source {sid} 計 \d+ 筆（未解析內容）")
        self.assertRegex(text, r"source defects 讀到 \d+ 筆")
        obj, rows = self._candidates(repo)
        self.assertEqual(obj["status"], "candidates")
        self.assertEqual(sorted({k for s in obj["sources"] for k in s}),
                         sorted({k for s in self.scan_json(repo)["sources"] for k in s}))
        module_rows = [c["row"] for c in obj["candidates"] if c["bucket"] != "defects"]
        defect_rows = [c["row"] for c in obj["candidates"] if c["bucket"] == "defects"]
        self.assertTrue(module_rows)
        for row in module_rows:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            self.assertEqual((cells[5], cells[6], cells[7]), ("process", "P4", "decided：僅計數"))
            self.assertEqual(cells[8], "面=流程;來源=工具;回報者=scan")
        for row in defect_rows:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            self.assertEqual((cells[5], cells[6], cells[7]), ("bug", "P3", "open"))
        copy = fx.new_dir("scancopy")
        shutil.copytree(repo, copy)
        ledger = fx.read(copy, "docs/06_quality/SelfImproving_Observation_Ledger.md")
        fx.put(copy, "docs/06_quality/SelfImproving_Observation_Ledger.md",
               ledger.rstrip("\n") + "\n" + "\n".join(rows) + "\n")
        res = self.check(copy)
        for item in ("row.required", "row.enums", "row.markers", "row.provenance", "row.bytes",
                     "row.coordinates", "row.control_chars", "ledger.time_tz"):
            self.assertEqual(self.S(res, item), "PASS", (item, self.F(res, item)))

    def test_AT_240_10_E_1_defaults_unchanged(self):
        repo = self.scan_repo(quiet=True)
        rc, out, _ = self.M(repo, "scan")
        self.assertEqual(rc, 0)
        self.assertEqual(self.scan_json(repo)["status"], "no-event")
        self.assertTrue(out.strip().split("\n")[-1].startswith("無事件"))
        rc, out, _ = self.M(repo, "run-close", "--run", fx.rid(900 + 3), "--by", "main")
        self.assertEqual(rc, 1)
        row = out.split("obs-draft:\n")[1].strip()
        cells = [c.strip() for c in row.strip("|").split("|")]
        self.assertEqual(cells[5:8], ["bug", "P3", "open"])


class TestP6BadHost(ResearchCase):
    """受測：`tools/lib/selfimproving/registry.py`、`research.py`（壞 host 的零連線；P6 版）。"""

    def test_AT_230_2_E_2_bad_host_means_zero_connections(self):
        # P2 TCS 的 AT-230-2-E-2：壞 host 一律在連線前被擋。P6 版＝鏡像內的壞 URL 於預檢以
        # REG-WATCH-URL 整次拒收，`px.net` 的解析與連線次數皆為 0（對應 TCS-P6 AT-630-7-E-1）。
        bad = ["https://xn--e1afmkfd.example/x", "https://例え.jp/x", "https://127.0.0.1/x",
               "https://localhost/x", "https://example.org./x", "https://u@example.org/x"]
        for url in bad:
            repo = px.repo(mirror=px.mutate(lambda o: o["watch"][1].update(url=url)))
            with px.net({}) as n:
                rc, out, _ = self.M(repo, "research", "--fetch", "--run", rid(1))
            self.assertEqual(rc, 1, url)
            self.assertIn("REG-WATCH-URL", fx.codes_of(out), url)
            self.assertEqual((n.resolved, n.connects), ([], []), url)


if __name__ == "__main__":
    unittest.main()
