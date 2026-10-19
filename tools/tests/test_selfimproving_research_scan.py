"""SelfImproving P1 研究掃描與模組體檢的驗收測試（TCS-P1 RS 檔：AT-130、AT-131 系列）。

方法名含 AT 底線形。網路測試只用本機 loopback HTTP 夾具（不連外網）；合成 repo 於 tmp 目錄。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
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

from lib import apply_lock
from lib.selfimproving import defs as si_defs
from lib.selfimproving import evwrite
from lib.selfimproving import fetch as si_fetch
from lib.selfimproving import scan as si_scan
from lib.selfimproving import sources as si_sources

TOOLS = fx.TOOLS
TEXT = {"Content-Type": "text/plain; charset=utf-8"}


def setUpModule() -> None:
    fx.setup("si_rs_")


def tearDownModule() -> None:
    fx.teardown()


def ledger_bytes(repo: Path):
    p = repo / EVL
    return p.read_bytes() if p.is_file() else None


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
            self.assertEqual(self.F(res, "events.research"), want[key], key)
            if key in ("d", "e"):
                self.assertEqual(
                    (self.S(res, "events.research"), res["_item"]["events.research"]["findings"]),
                    ("PASS", []),
                    key,
                )
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
        self.assertEqual(self.F(res, "events.research"), {("-", "QUOTE-VERIFIER-NOT-ESTABLISHED")})
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

    def test_AT_130_2_E_1_table_codes_and_preflight(self):
        policy = si_sources.DEFAULT_POLICY
        self.assertEqual(si_sources.validate_table(self.raw(), policy), [])

        def first(raw):
            return [c for c, _, _ in si_sources.validate_table(raw, policy)]

        good = self.raw()
        e = self.good_entry
        hosts = [
            "localhost",
            "127.0.0.1",
            "10.0.0.1",
            "172.16.0.1",
            "192.168.0.1",
            "169.254.0.1",
            "[::1]",
            "[fe80::1]",
            "[fc00::1]",
            "[::ffff:10.0.0.1]",
        ]
        cases = [
            (b"\xef\xbb\xbf" + good, "SRC-FILE-FORMAT"),
            (good.replace(b"\n", b"\r\n"), "SRC-FILE-FORMAT"),
            (good.rstrip(b"\n"), "SRC-FILE-FORMAT"),
            (b"[1]\n", "SRC-FILE-FORMAT"),
            (self.raw({"schema_rev": 2, "sources": [e()]}), "SRC-SCHEMA"),
            (self.raw({"schema_rev": 1}), "SRC-SCHEMA"),
            (self.raw({"schema_rev": 1, "sources": [e(extra=1)]}), "SRC-SCHEMA"),
            (
                self.raw(
                    {"schema_rev": 1, "sources": [{k: v for k, v in e().items() if k != "extract"}]}
                ),
                "SRC-FIELD-MISSING",
            ),
            (self.raw(id="Src-A"), "SRC-ID-FORMAT"),
            (self.raw({"schema_rev": 1, "sources": [e(), e()]}), "SRC-ID-DUP"),
            (self.raw({"schema_rev": 1, "sources": [e(id="b-src"), e(id="a-src")]}), "SRC-ORDER"),
            (self.raw(kind="news"), "SRC-KIND"),
            (self.raw(retired="yes"), "SRC-RETIRED-TYPE"),
            (self.raw(url="http://example.com/x.md"), "SRC-URL-SCHEME"),
            (self.raw(url="https://user:pw@example.com/x.md"), "SRC-URL-USERINFO"),
            *[(self.raw(url=f"https://{h}/x.md"), "SRC-URL-HOST") for h in hosts],
        ]
        for raw, code in cases:
            with self.subTest(code=code, raw=raw[:60]):
                self.assertEqual(first(raw)[0], code)
        self.assertEqual(first(self.raw(url="http://example.com/x.md")), ["SRC-URL-SCHEME"])
        self.assertEqual(first(self.raw(id="Src-A")), ["SRC-ID-FORMAT"])
        srv = self.serving({f"/s{i}": (200, TEXT, b"ok") for i in range(9)})
        entries = [(f"s{i}", f"/s{i}") for i in range(9)]

        def prep(table=None, commit=True, runs=1):
            repo = fx.p1_base()
            self.open_only(repo, runs)
            if table is not None:
                fx.putb(repo, SRC_REL, table)
                if commit:
                    fx.commit_all(repo, "t")
            return repo

        def reject(repo, code, run=None):
            n = len(srv.requests)
            before = ledger_bytes(repo)
            with fx.relaxed():
                rc, out, _ = self.M(repo, "research", "--fetch", "--run", run or rid(1))
            self.rejected(rc, out, None)
            self.assertIn(code, fx.codes_of(out))
            self.assertEqual((len(srv.requests), ledger_bytes(repo)), (n, before))
            self.assertEqual(sum(1 for ln in out.split("\n") if ln.startswith("| OBS")), 1)
            self.draft_ok(repo, out)

        reject(prep(), "SOURCES-ABSENT")
        reject(prep(b"\xef\xbb\xbf" + good), "SRC-FILE-FORMAT")
        nine = fx.table_bytes(srv, entries)
        reject(prep(nine), "FETCH-MAX")
        reject(
            prep(fx.table_bytes(srv, entries, retired=[f"s{i}" for i in range(9)])), "ZERO-SUCCESS"
        )
        repo = prep(good)
        fx.putb(repo, SRC_REL, self.raw(extract="改過"))
        reject(repo, "SOURCES-UNCOMMITTED")
        reject(prep(good, commit=False), "SOURCES-UNCOMMITTED")
        reject(prep(good), "RUN-NOT-OPEN", run=rid(901))
        repo = prep(good)
        self.cli_ok(
            repo, "research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "x"
        )
        reject(repo, "RESEARCH-ALREADY")
        repo = prep(fx.table_bytes(srv, entries, retired=["s7", "s8"]))
        rc, out, err = self.fetch(repo)
        self.assertEqual(rc, 0, out + err)
        two = [(f"s{i}", f"/s{i}") for i in range(2)]
        repo = prep(fx.table_bytes(srv, two))
        fx.putb(repo, SRC_REL, fx.table_bytes(srv, two).replace(b"\n", b"\r\n"))
        rc, out, err = self.fetch(repo)
        self.assertEqual(rc, 0, out + err)
        repo = prep(fx.table_bytes(srv, two))
        nogit = fx.new_dir("nogit")
        shutil.copytree(repo, nogit, ignore=shutil.ignore_patterns(".git"))
        rc, out, err = self.fetch(nogit)
        self.assertEqual(rc, 0, out + err)
        self.assertIn("ne sources-commit-check git-unavailable", out)
        nogit2 = fx.new_dir("nogit")
        shutil.copytree(repo, nogit2, ignore=shutil.ignore_patterns(".git"))
        with fx.relaxed():
            rc, out, _ = self.M(nogit2, "research", "--fetch", "--run", rid(1), "--json")
        self.assertEqual(rc, 0, out)
        self.assertIn(
            {"field": "sources-commit-check", "reason": "git-unavailable"}, json.loads(out)["ne"]
        )


class TestSourcesHistory(ResearchCase):
    def scan_event(self, run, table_sha, t, ids=("s-live",)):
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

    def test_AT_130_2_E_2_sources_sha_against_history(self):
        b = (datetime.now().astimezone() - timedelta(days=10)).replace(microsecond=0)
        t1, t2, t3, t4 = (b + timedelta(days=d) for d in range(4))
        iso = lambda d: d.isoformat(timespec="seconds")  # noqa: E731
        v1 = {
            "schema_rev": 1,
            "sources": [
                {
                    "id": "s-live",
                    "url": "https://example.com/a.md",
                    "kind": "docs",
                    "extract": "讀",
                    "added_by": "T1",
                },
                {
                    "id": "s-old",
                    "url": "https://example.com/b.md",
                    "kind": "docs",
                    "extract": "讀",
                    "added_by": "T1",
                    "retired": True,
                },
            ],
        }
        v2 = {
            "schema_rev": 1,
            "sources": [
                *v1["sources"],
                {
                    "id": "s-new",
                    "url": "https://example.com/c.md",
                    "kind": "docs",
                    "extract": "讀",
                    "added_by": "T1",
                },
            ],
        }

        def dump(o):
            return (json.dumps(o, ensure_ascii=False, indent=2) + "\n").encode()

        h1 = fx.sha(dump(v1))

        def build(extra=None):
            repo = fx.p1_base()
            fx.putb(repo, SRC_REL, dump(v1))
            fx.commit_all(repo, "C1", when=iso(t1))
            events = [
                fx.run_open_ev(1),
                self.scan_event(1, h1, iso(t2)),
                fx.run_open_ev(2),
                self.scan_event(2, h1, iso(t4)),
            ]
            events += extra or []
            fx.write_events(repo, events)
            fx.putb(repo, SRC_REL, dump(v2))
            fx.commit_all(repo, "C2", when=iso(t3))
            return repo

        res = self.check(build())
        self.assertEqual(self.F(res, "events.research"), {("seq=4", "SOURCES-SHA-MISMATCH")})
        repo = fx.p1_base()
        fx.putb(repo, SRC_REL, dump(v1))
        fx.commit_all(repo, "C1", when=iso(t1))
        fx.write_events(
            repo, [fx.run_open_ev(1), self.scan_event(1, h1, iso(t1 - timedelta(days=1)))]
        )
        self.assertIn(
            ("seq=2", "SOURCES-SHA-MISMATCH"), self.F(self.check(repo), "events.research")
        )
        extra = [
            fx.run_open_ev(3),
            self.scan_event(3, fx.sha(dump(v2)), iso(t4), ids=("zz-unknown",)),
            fx.run_open_ev(4),
            self.scan_event(4, fx.sha(dump(v2)), iso(t4), ids=("s-old",)),
        ]
        res = self.check(build(extra))
        found = self.F(res, "events.research")
        self.assertIn(("seq=6 zz-unknown", "SRC-UNKNOWN"), found)
        self.assertFalse([s for s, c in found if "s-old" in s])
        repo = build()
        fx.putb(repo, SRC_REL, dump({**v2, "sources": v2["sources"][:1]}))
        self.assertEqual(
            self.F(self.check(repo), "events.research"), {("seq=4", "SOURCES-SHA-MISMATCH")}
        )
        nogit = fx.new_dir("nogit")
        shutil.copytree(build(), nogit, ignore=shutil.ignore_patterns(".git"))
        item = self.check(nogit)["_item"]["events.research"]
        self.assertEqual((item["status"], item["blocking"]), ("NE", False))
        self.assertEqual(
            [(f["subject"], f["code"]) for f in item["findings"]],
            [("-", "SOURCES-HISTORY-NOT-ESTABLISHED")],
        )
        repo = build()
        (repo / SRC_REL).unlink()
        item = self.check(repo)["_item"]["events.research"]
        self.assertEqual(
            (item["status"], item["blocking"], item["findings"][0]["code"]),
            ("NE", True, "SOURCE-UNAVAILABLE"),
        )

    def test_AT_130_2_E_3_redirect_guard(self):
        srv = self.serving({})
        other = self.serving({"/ok": (200, TEXT, b"x")})
        p = srv.port
        routes = {
            "/ok": (200, TEXT, b"ok"),
            "/to-ok": (302, {"Location": srv.url("/ok")}, b""),
            "/to-localhost": (302, {"Location": f"http://localhost:{p}/ok"}, b""),
            "/to-otherport": (302, {"Location": other.url("/ok")}, b""),
            "/to-ftp": (302, {"Location": "ftp://127.0.0.1/x"}, b""),
            "/to-file": (302, {"Location": "file:///x"}, b""),
        }
        for i in range(5):
            routes[f"/c{i}"] = (302, {"Location": srv.url(f"/c{i + 1}")}, b"")
        routes["/c5"] = (200, TEXT, b"end")
        for i in range(6):
            routes[f"/d{i}"] = (302, {"Location": srv.url(f"/d{i + 1}")}, b"")
        routes["/d6"] = (200, TEXT, b"end")
        srv.routes.update(routes)
        for path, ok in (
            ("/to-ok", True),
            ("/to-localhost", False),
            ("/to-otherport", False),
            ("/to-ftp", False),
            ("/to-file", False),
            ("/c0", True),
            ("/d0", False),
        ):
            repo = fx.p1_base()
            self.open_only(repo)
            write_table(repo, srv, [("s1", path)])
            before = ledger_bytes(repo)
            rc, out, err = self.fetch(repo)
            if ok:
                self.assertEqual(rc, 0, (path, out, err))
                self.assertIn("source s1 ok", out)
            else:
                self.assertEqual(rc, 1, (path, out))
                self.assertIn("source s1 FAIL redirect-refused", out)
                self.assertEqual(ledger_bytes(repo), before)
        allowed = {"example.com:443"}
        cr = si_fetch.check_redirect
        self.assertIsNone(cr("https://example.com/a", "https://example.com/b", allowed))
        for src, dst, hosts in (
            ("https://example.com/a", "http://example.com/b", allowed),
            ("http://example.com/a", "https://example.com/b", {"example.com:80"}),
            ("https://example.com/a", "https://other.example.org/b", allowed),
            ("https://example.com/a", "ftp://example.com/b", allowed),
            ("https://example.com/a", "file:///b", allowed),
        ):
            self.assertEqual(cr(src, dst, hosts), "redirect-refused", dst)


class TestFetching(ResearchCase):
    def test_AT_130_2_1_compliant_committed_table_passes_preflight(self):
        srv = self.serving({})
        srv.routes.update(
            {
                "/a": (200, TEXT, b"A"),
                "/b": (302, {"Location": srv.url("/b2")}, b""),
                "/b2": (200, TEXT, b"B"),
                "/unlisted": (200, TEXT, b"U"),
            }
        )
        repo = self.fetch_repo(srv, [("src-a", "/a"), ("src-b", "/b")])
        rc, out, err = self.fetch(repo)
        self.assertEqual(rc, 0, out + err)
        want = ["/" + name for name in ("a", "b", "b2")]
        self.assertEqual([r["path"] for r in srv.requests], want)
        self.assertEqual(srv.max_inflight, 1)
        (event,) = self.scan_events(repo)
        self.assertEqual([s["id"] for s in event["sources"]], ["src-a", "src-b"])
        with fx.relaxed():
            res = self.check(repo)
        self.assertEqual(self.S(res, "research.sources"), "PASS")
        self.assertEqual(self.S(res, "events.research"), "PASS")

    def test_AT_130_3_1_fetch_raw_bytes_and_changed(self):
        a = bytes(range(97, 123)) * 40
        a = a[:1000]
        routes = {
            "/a": (200, TEXT, a),
            "/b": (200, {"Content-Type": "application/json"}, b'{"v": 1}'),
            "/c": (200, {"Content-Type": "application/atom+xml"}, b"<feed/>"),
        }
        srv = self.serving(routes)
        repo = fx.p1_base()
        runs = self.open_only(repo, 3)
        table = write_table(repo, srv, [("s-a", "/a"), ("s-b", "/b"), ("s-c", "/c")])
        rc, out, err = self.fetch(repo, runs[0])
        self.assertEqual(rc, 0, out + err)
        lines = out.strip().split("\n")
        self.assertEqual(len(lines), 4)
        for line, ident, body in zip(
            lines, ("s-a", "s-b", "s-c"), (a, routes["/b"][2], routes["/c"][2])
        ):
            digest = hashlib.sha256(body).hexdigest()
            self.assertEqual(
                line, f"source {ident} ok sha256={digest[:12]} bytes={len(body)} changed=true"
            )
        self.assertRegex(lines[3], rf"^ok research\.scan seq=\d+ run={runs[0]}$")
        e = self.scan_events(repo)[0]
        self.assertEqual(
            list(e)[:8],
            ["seq", "t", "kind", "by", "run", "sources", "sources_sha256", "fetched_at"],
        )
        self.assertEqual(e["by"], "researcher")
        self.assertTrue(
            all(
                list(s) == ["id", "sha256", "bytes", "changed", "http_status"] for s in e["sources"]
            )
        )
        self.assertNotIn("url", json.dumps(e))
        self.assertEqual(
            e["sources_sha256"],
            "sha256:" + hashlib.sha256(table.replace(b"\r\n", b"\n")).hexdigest(),
        )
        self.assertIsNotNone(datetime.fromisoformat(e["fetched_at"]).utcoffset())
        for s, body in zip(e["sources"], (a, routes["/b"][2], routes["/c"][2])):
            self.assertEqual(s["sha256"], "sha256:" + hashlib.sha256(body).hexdigest())
            folder = self.home / "research" / s["id"]
            sha12 = s["sha256"].split(":")[1][:12]
            self.assertEqual((folder / f"{sha12}.txt").read_bytes(), body)
            self.assertEqual((folder / "latest").read_bytes(), sha12.encode())
        self.fetch(repo, runs[1])
        routes["/b"] = (200, {"Content-Type": "application/json"}, b'{"v": 2}')
        self.fetch(repo, runs[2])
        e2, e3 = self.scan_events(repo)[1:]
        self.assertEqual([s["changed"] for s in e2["sources"]], [False, False, False])
        self.assertEqual([s["changed"] for s in e3["sources"]], [False, True, False])
        for r in srv.requests:
            h = r["headers"]
            self.assertEqual(
                (h["user-agent"], h["accept-encoding"]), ("selfimproving-research/1", "identity")
            )
            self.assertFalse({"cookie", "authorization", "proxy-authorization"} & set(h))
        self.assertEqual(srv.max_inflight, 1)
        order = ["/" + name for name in "abc"]
        self.assertEqual([r["path"] for r in srv.requests[:3]], order)

    def test_AT_130_3_E_1_failure_matrix(self):
        dead = socket.socket()
        dead.bind(("127.0.0.1", 0))
        dead_port = dead.getsockname()[1]
        dead.close()
        routes = {
            "/s-ok": (200, TEXT, b"o" * 100),
            "/s-edge": (200, TEXT, b"e" * 1000),
            "/s-big": (200, TEXT, b"b" * 1001),
            "/s-404": (404, TEXT, b"no"),
            "/s-500": (500, TEXT, b"no"),
            "/s-bin": (200, {"Content-Type": "image/png"}, b"x"),
            "/s-noct": (200, {}, b"x"),
            "/s-gz": (200, {**TEXT, "Content-Encoding": "gzip"}, b"x"),
            "/s-slow": (200, TEXT, b"x", {"delay": 3}),
        }
        srv = self.serving(routes)

        def setup():
            repo = fx.p1_base()
            self.open_only(repo)
            fx.set_params(
                repo, research_fetch_max=20, research_bytes_max=1000, research_timeout_seconds=1
            )
            entries = [(k.lstrip("/"), k) for k in routes] + [("s-refused", "/dead")]
            raw = fx.table_bytes(srv, entries).replace(
                srv.url("/dead").encode(), f"http://127.0.0.1:{dead_port}/x".encode()
            )
            fx.putb(repo, SRC_REL, raw)
            fx.commit_all(repo, "t")
            return repo

        repo = setup()
        rc, out, err = self.fetch(repo)
        self.assertEqual(rc, 2, out + err)
        reasons = dict(re.findall(r"(?m)^source (\S+) FAIL (\S+)", out))
        self.assertEqual(
            reasons,
            {
                "s-404": "http-status",
                "s-500": "http-status",
                "s-big": "too-large",
                "s-bin": "non-text",
                "s-noct": "non-text",
                "s-gz": "encoding",
                "s-slow": "timeout",
                "s-refused": "network",
            },
        )
        self.assertIn("source s-404 FAIL http-status 404", out)
        self.assertIn("source s-500 FAIL http-status 500", out)
        self.assertIn("source s-edge ok", out)
        e = self.scan_events(repo)[0]
        self.assertEqual([s["id"] for s in e["sources"]], ["s-edge", "s-ok"])
        rows = out.split("obs-draft:\n")[1].strip().split("\n")
        self.assertEqual(len(rows), 8)
        for row in rows:
            self.assertIn("rc=2", row)
        self.draft_ok(repo, "obs-draft:\n" + "\n".join(rows) + "\n")
        repo2 = setup()
        rc, out, err = self.fetch(repo2, rid(1), "--json")
        obj = json.loads(out)
        self.assertEqual((rc, len(obj["failed"])), (2, 8))
        self.assertTrue(all(list(f) == ["id", "reason", "detail"] for f in obj["failed"]))

    def test_AT_130_3_E_2_zero_success_and_json_shape(self):
        srv = self.serving(
            {
                "/a": (404, TEXT, b"no"),
                "/b": (404, TEXT, b"no"),
                "/ok1": (200, TEXT, b"1"),
                "/ok2": (200, TEXT, b"2"),
                "/ok3": (200, TEXT, b"3"),
            }
        )
        repo = self.fetch_repo(srv, [("a", "/a"), ("b", "/b")])
        before = ledger_bytes(repo)
        rc, out, err = self.fetch(repo)
        self.assertEqual(rc, 1, out + err)
        self.assertEqual(ledger_bytes(repo), before)
        self.assertEqual(len(re.findall(r"(?m)^source \S+ FAIL", out)), 2)
        self.assertIn("obs-draft:", out)
        self.cli_ok(
            repo, "research", "--skip", "--run", rid(1), "--reason", "offline", "--note", "離線驗證"
        )
        repo = self.fetch_repo(srv, [("a", "/ok1"), ("b", "/ok2"), ("c", "/ok3")])
        fx.set_params(repo, event_max_bytes=200)
        before = ledger_bytes(repo)
        rc, out, err = self.fetch(repo)
        self.assertEqual(rc, 1, out + err)
        self.assertIn("EVENT-BYTES-OVER", fx.codes_of(out))
        self.assertEqual(ledger_bytes(repo), before)
        for ident in "abc":
            folder = self.home / "research" / ident
            self.assertTrue((folder / "latest").is_file(), ident)
        repo = self.fetch_repo(srv, [("a", "/ok1"), ("b", "/ok2")])
        rc, out, err = self.fetch(repo, rid(1), "--json")
        self.assertEqual(rc, 0, out + err)
        obj = json.loads(out)
        self.assertEqual(
            list(obj),
            ["ok", "kind", "seq", "id", "run", "rc", "sources", "failed", "obs_drafts", "ne"],
        )
        self.assertEqual(
            (obj["kind"], obj["id"], obj["failed"], obj["obs_drafts"]),
            ("research.scan", None, [], []),
        )

    def test_AT_130_3_E_3_fetch_outside_lock(self):
        for scenario in (1, 2, 3, 4):
            hold = threading.Event()
            srv = self.serving({"/hold": (200, TEXT, b"held", {"hold": hold})})
            repo = fx.p1_base()
            self.open_only(repo)
            write_table(repo, srv, [("s-hold", "/hold")])
            ledger = repo / EVL
            lock = evwrite.lock_path_for(self.home, ledger)
            result: list = []

            def work():
                buf, err = __import__("io").StringIO(), __import__("io").StringIO()
                with redirect_stdout(buf), redirect_stderr(err):
                    import selfimproving

                    rc = selfimproving.main(
                        ["research", "--fetch", "--run", rid(1), "--repo", str(repo)]
                    )
                result.append((rc, buf.getvalue()))

            with fx.relaxed():
                t = threading.Thread(target=work)
                t.start()
                hold_path = "/" + "hold"
                self.assertTrue(srv.arrived(hold_path).wait(15))
                n0 = len(fx.EV(repo))
                if scenario == 1:
                    t0 = time.monotonic()
                    with apply_lock.acquire(lock, 2, 300):
                        pass
                    self.assertLess(time.monotonic() - t0, 2)
                elif scenario == 2:
                    evwrite.append_event(
                        ledger,
                        lock,
                        lambda s: {
                            "kind": "research.skip",
                            "by": "main",
                            "run": rid(1),
                            "reason": "offline",
                            "note": "測試插入",
                        },
                    )
                elif scenario == 3:
                    evwrite.append_event(
                        ledger,
                        lock,
                        lambda s: {
                            "kind": "run.close",
                            "by": "main",
                            "run": rid(1),
                            "no_event": True,
                        },
                    )
                else:
                    other = self.serving({})
                    write_table(
                        repo, other, [("s-hold", "/hold"), ("s-zzz", "/x")], retired=["s-zzz"]
                    )
                hold.set()
                t.join(30)
            rc, out = result[0]
            kinds = [e["kind"] for e in fx.EV(repo)[n0:]]
            if scenario == 1:
                self.assertEqual((rc, kinds), (0, ["research.scan"]))
            else:
                self.assertEqual(rc, 1, out)
                want = {2: "RESEARCH-ALREADY", 3: "RUN-NOT-OPEN", 4: "SOURCES-CHANGED"}[scenario]
                self.assertIn(want, fx.codes_of(out))
                self.assertNotIn("research.scan", kinds)
                self.assertEqual(kinds, {2: ["research.skip"], 3: ["run.close"], 4: []}[scenario])


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

    def test_AT_130_5_1_budget_boundaries_pass(self):
        body = b"x" * 500
        srv = self.serving(
            {
                "/a": (200, TEXT, body),
                "/b": (200, TEXT, body),
                "/late": (200, TEXT, body, {"delay": 0.3}),
            }
        )
        repo = fx.p1_base()
        self.open_only(repo)
        fx.set_params(
            repo, research_fetch_max=3, research_bytes_max=500, research_timeout_seconds=2
        )
        write_table(repo, srv, [("a", "/a"), ("b", "/b"), ("c", "/late")])
        rc, out, err = self.fetch(repo)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(len(re.findall(r"(?m)^source \S+ ok", out)), 3)
        net = {"socket", "urllib", "http", "ssl", "ftplib", "smtplib", "asyncio", "requests"}
        importers = set()
        for path in (TOOLS / "lib" / "selfimproving").glob("*.py"):
            tree = ast.parse(path.read_bytes().decode("utf-8"))
            for node in ast.walk(tree):
                mods = (
                    [a.name.split(".")[0] for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module.split(".")[0]]
                    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
                    else []
                )
                if net & set(mods):
                    importers.add(path.name)
        self.assertEqual(importers, {"fetch.py"})

    def test_AT_130_5_E_1_budget_overruns(self):
        srv = self.serving({f"/p{i}": (200, TEXT, b"ok") for i in range(6)})
        srv.routes["/big"] = (200, TEXT, b"b" * 501)
        srv.routes["/slow"] = (200, TEXT, b"x", {"delay": 3})

        def setup(entries, retired=(), **prm):
            repo = fx.p1_base()
            self.open_only(repo)
            fx.set_params(
                repo,
                research_fetch_max=3,
                research_bytes_max=500,
                research_timeout_seconds=1,
                **prm,
            )
            write_table(repo, srv, entries, retired=retired)
            return repo

        repo = setup([(f"s{i}", f"/p{i}") for i in range(4)])
        n, before = len(srv.requests), ledger_bytes(repo)
        rc, out, _ = self.fetch(repo)
        self.rejected(rc, out, {"FETCH-MAX"})
        self.assertEqual((len(srv.requests), ledger_bytes(repo)), (n, before))
        repo = setup([(f"s{i}", f"/p{i}") for i in range(5)], retired=["s3", "s4"])
        n = len(srv.requests)
        rc, out, err = self.fetch(repo)
        self.assertEqual((rc, len(srv.requests) - n), (0, 3), out + err)
        repo = setup([("big", "/big")])
        rc, out, _ = self.fetch(repo)
        self.assertEqual(rc, 1)
        self.assertIn("source big FAIL too-large", out)
        self.assertFalse((self.home / "research" / "big").exists())
        repo = setup([("slow", "/slow")])
        rc, out, _ = self.fetch(repo)
        self.assertEqual(rc, 1)
        self.assertIn("source slow FAIL timeout", out)
        for key in ("research_fetch_max", "research_bytes_max", "research_timeout_seconds"):
            repo = setup([("s0", "/p0")])
            fx.set_params(repo, **{key: KeyError})
            n = len(srv.requests)
            rc, out, err = self.fetch(repo)
            self.usage_error(rc, out, err)
            self.assertIn(key, err)
            self.assertEqual(len(srv.requests), n)

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
            self.assertEqual(argv[:3], ["git", "-C", resolved])
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
        for i, row in enumerate(rows):
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            self.assertEqual(len(cells), 9)
            self.assertLessEqual(len(row.encode("utf-8")), 700)
            self.assertEqual(cells[0], obs_id(11 + i))
            self.assertEqual(
                (cells[2], cells[5], cells[6], cells[7], cells[8]),
                ("si scan（自動草稿）", "bug", "P3", "open", "面=流程;來源=工具;回報者=scan"),
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
        self.assertTrue(all(re.match(r"^source \S+ 讀到 \d+ 筆$", ln) for ln in lines[:5]), lines)
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
