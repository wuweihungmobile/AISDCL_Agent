"""SelfImproving P6 安全抓取、文章展開與純文字的驗收測試（TCS-SelfImproving-P6 NF 檔）。

受測模組：`tools/lib/selfimproving/netguard.py`、`fetch.py`、`expand.py`、`htmltext.py`、
`research.py`、
`patrolrun.py`。方法名含 AT 底線形；網路一律走 `px.net`（`fetch.RESOLVER`／`CONNECTOR` 兩個縫），
`socket.socket.connect` 被注入 `AssertionError`，測試不得真連網。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p6_fixtures as px

from lib.selfimproving import expand, htmltext, netguard, patrolrun, research
from lib.selfimproving import fetch as si_fetch

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "tools/lib/selfimproving"
FIX = Path(__file__).resolve().parent / "fixtures/selfimproving"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
P_RESEARCH, P_BLOG, P_R = "/research/", "/blog/", "/r/"  # URL 路徑前綴（非檔案系統路徑）
ANY_HOSTS = {"a.example.org", "b.example.org", "c.example.org", "www.x.org"}


def setUpModule() -> None:
    fx.setup("si_nf_")


def tearDownModule() -> None:
    fx.teardown()


def sitemap(*entries) -> bytes:
    rows = "".join(f"<url><loc>{loc}</loc>" + (f"<lastmod>{mod}</lastmod>" if mod else "")
                   + "</url>" for loc, mod in entries)
    return f'<?xml version="1.0"?><urlset xmlns="{NS}">{rows}</urlset>'.encode()


def watch(ident, url, *, expand_=None, kind="docs", enabled=True) -> dict:
    return {"added_at": "2026-11-10T00:00:00+00:00", "added_by": "t", "disabled_at": None,
            "disabled_by": None, "enabled": enabled, "expand": expand_, "extract": "x",
            "id": ident, "kind": kind, "layer": "INDUSTRY", "url": url}


def mirror_of(*watches) -> str:
    hosts = sorted({w["url"].split("/")[2] for w in watches})
    rows = [{"host": h, "layer": "INDUSTRY", "list_kind": "FETCH", "min_interval_seconds": 5,
             "source": "ADMIN"} for h in hosts]
    return px.registry_text(rows, sorted(watches, key=lambda w: w["id"]))


def text_resp(body: bytes, ctype="text/plain; charset=utf-8", **kw) -> dict:
    return px.response(ctype=ctype, body=body, **kw)


class NfCase(fx.SiTestCase):
    """NF 共用：一次 `research --fetch` 的封裝與已開運轉的合成 repo。"""

    def setUp(self) -> None:
        super().setUp()
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": px.KEY})
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, watches, table, *, extra=(), run=1, clock=None, **netkw):
        repo = px.repo(mirror=mirror_of(*watches), extra=list(extra))
        return repo, *self.rerun(repo, table, run=run, clock=clock, **netkw)

    def rerun(self, repo, table, *, run=1, clock=None, **netkw):
        with px.net(table, **netkw) as n, \
                mock.patch.object(research, "CLOCK", clock or research.CLOCK):
            rc, out, _ = self.M(repo, "research", "--fetch", "--run", fx.rid(run))
        return rc, out, n

    def scans(self, repo):
        return [e for e in fx.EV(repo) if e["kind"] == "research.scan"]


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


class TestDigest(NfCase):
    """tools/lib/selfimproving/research.py 與 fetch.py 的增量 digest（AC-SI-30-3）。"""

    def test_AT_630_3_1_changed_flags_and_landing(self):
        ws = [watch("a", "https://a.example.org/x"), watch("b", "https://b.example.org/x"),
              watch("c", "https://c.example.org/x")]
        bodies = {"a": b"same", "b": b"new-b", "c": b"fresh"}
        table = {(f"{i}.example.org", "/x"): text_resp(bodies[i]) for i in bodies}
        sha = lambda b: "sha256:" + hashlib.sha256(b).hexdigest()  # noqa: E731
        prior = fx.ev("research.scan", by="researcher", run=fx.rid(1), fetched_at=px.TIME,
                      registry_seq=1, registry_sha256=px.sha_of(mirror_of(*ws).encode()),
                      sources=[{"id": "a", "sha256": sha(b"same"), "bytes": 4, "changed": True,
                                "http_status": 200},
                               {"id": "b", "sha256": sha(b"old-b"), "bytes": 5, "changed": True,
                                "http_status": 200}])
        repo, rc, out, _ = self.scan(
            ws, table, run=2, extra=[prior, fx.ev("run.close", run=fx.rid(1), no_event=True),
                                     fx.run_open_ev(2)])
        self.assertEqual(rc, 0, out)
        ev = self.scans(repo)[-1]
        self.assertEqual([(s["id"], s["changed"]) for s in ev["sources"]],
                         [("a", False), ("b", True), ("c", True)])
        folder = self.home / "research" / "b"
        sha12 = hashlib.sha256(b"new-b").hexdigest()[:12]
        self.assertEqual((folder / f"{sha12}.txt").read_bytes(), b"new-b")
        self.assertEqual((folder / "latest").read_bytes(), sha12.encode())

    def test_AT_630_3_E_1_failure_matrix(self):
        reasons = {
            "http-status": text_resp(b"x", ) | {"status": 500},
            "too-large": text_resp(b"x" * 600000),
            "non-text": text_resp(b"x", ctype="image/png"),
            "encoding": text_resp(b"x", headers={"Content-Encoding": "gzip"}),
        }
        cases = [(k, {("bad.example.org", "/x"): v}, {}) for k, v in reasons.items()]
        cases.append(("encoding", {("bad.example.org", "/x"): text_resp(
            b"x", ctype="text/plain; charset=big5")}, {}))
        cases.append(("timeout", {}, {"errors": {"bad.example.org": TimeoutError()}}))
        cases.append(("network", {}, {"errors": {"bad.example.org": OSError("x")}}))
        for reason, table, kw in cases:
            ws = [watch("bad", "https://bad.example.org/x"),
                  watch("good", "https://good.example.org/x")]
            table = {**table, ("good.example.org", "/x"): text_resp(b"ok")}
            repo, rc, out, _ = self.scan(ws, table, **kw)
            self.assertEqual(rc, 2, (reason, out))
            self.assertIn(f"source bad FAIL {reason}", out)
            self.assertEqual([s["id"] for s in self.scans(repo)[0]["sources"]], ["good"])
            self.assertIn("obs-draft:", out)
        ws = [watch("bad", "https://bad.example.org/x")]
        repo, rc, out, _ = self.scan(ws, {("bad.example.org", "/x"): px.response(500)})
        self.assertEqual((rc, self.scans(repo)), (1, []))

    def test_AT_630_3_E_2_scan_wall_clock(self):
        ws = [watch(i, f"https://{i}.example.org/x") for i in "abc"]
        table = {(f"{i}.example.org", "/x"): text_resp(b"ok") for i in "abc"}
        clock = FakeClock()
        with mock.patch.object(research, "SCAN_WALL_SECONDS", 10):
            repo, rc, out, _ = self.scan(ws, table, clock=clock,
                                         on_connect=lambda: clock.advance(6))
        self.assertEqual(rc, 2, out)
        self.assertEqual([s["id"] for s in self.scans(repo)[0]["sources"]], ["a", "b"])
        self.assertIn("source c FAIL timeout", out)

    def test_AT_630_3_E_4_chain_wall_clock(self):
        t = 20  # research_timeout_seconds（真協定值）
        redirects = {("www.x.org", "/a"): px.response(302, {"Location": "/b"}),
                     ("www.x.org", "/b"): px.response(302, {"Location": "/c"}),
                     ("www.x.org", "/c"): px.response(302, {"Location": "/d"}),
                     ("www.x.org", "/d"): text_resp(b"done")}
        for step, want in ((0.4 * t, "timeout"), (0.1 * t, None)):
            clock = FakeClock()
            repo = px.repo(mirror=mirror_of(watch("w", "https://www.x.org/a")))
            px.set_params(repo, research_timeout_seconds=t)
            with px.net(redirects, on_connect=lambda: clock.advance(step)), \
                    mock.patch.object(research, "CLOCK", clock):
                rc, out, _ = self.M(repo, "research", "--fetch", "--run", fx.rid(1))
            if want:
                self.assertIn(f"FAIL {want}", out)
            else:
                self.assertEqual(rc, 0, out)

    def test_AT_630_3_E_5_json_shape_and_zero_success(self):
        ws = [watch("bad", "https://bad.example.org/x"),
              watch("good", "https://good.example.org/x")]
        table = {("good.example.org", "/x"): text_resp(b"ok"),
                 ("bad.example.org", "/x"): px.response(500)}
        repo = px.repo(mirror=mirror_of(*ws))
        with px.net(table):
            rc, out, _ = self.M(repo, "research", "--fetch", "--run", fx.rid(1), "--json")
        obj = json.loads(out)
        self.assertEqual(rc, 2)
        self.assertEqual({"ok", "kind", "seq", "run", "rc", "sources", "failed", "obs_drafts"},
                         set(obj) - {"id"})
        self.assertEqual((obj["ok"], obj["rc"], obj["failed"][0]["id"]), (True, 2, "bad"))
        repo = px.repo(mirror=mirror_of(ws[0]))
        with px.net(table):
            rc, out, _ = self.M(repo, "research", "--fetch", "--run", fx.rid(1), "--json")
        obj = json.loads(out)
        self.assertEqual((rc, obj["ok"], [c["code"] for c in obj["codes"]]),
                         (1, False, ["ZERO-SUCCESS"]))
        self.assertEqual(self.scans(repo), [])

    def test_AT_630_3_E_6_fetch_runs_outside_the_ledger_lock(self):
        from lib import apply_lock

        from lib.selfimproving import evwrite
        repo = px.repo(mirror=mirror_of(watch("a", "https://a.example.org/x")))
        held = []

        def probe():  # 抓取期間（連線時）能取得事件帳本寫入鎖＝抓取不持鎖
            lock = evwrite.lock_path_for(self.home, repo / fx.EVL)
            with apply_lock.acquire(lock, 1, 300):
                held.append(True)
        rc, out, _ = self.rerun(repo, {("a.example.org", "/x"): text_resp(b"ok")},
                                on_connect=probe)
        self.assertEqual((rc, held), (0, [True]), out)

    def test_AT_630_3_E_3_redirect_downgrade_and_http_source(self):
        for loc in ("http://www.x.org/b", "https://www.x.org:8443/b"):
            table = {("www.x.org", "/a"): px.response(302, {"Location": loc})}
            repo, rc, out, n = self.scan([watch("w", "https://www.x.org/a")], table)
            self.assertIn("redirect-refused", out)
            self.assertEqual(len(n.connects), 1)
        repo = px.repo(mirror=mirror_of(watch("w", "http://www.x.org/a")))
        rc, out, n = self.rerun(repo, {})
        self.assertIn("REG-WATCH-URL", fx.codes_of(out))
        self.assertEqual(n.connects, [])


class TestSafety(NfCase):
    """tools/lib/selfimproving/netguard.py 與 fetch.py 的安全閘（AC-SI-30-7）。"""

    def chain(self, url, table, **kw):
        with px.net(table, **kw) as n:
            try:
                return si_fetch.fetch_chain(url, hosts=kw.get("hosts") or ANY_HOSTS,
                                            timeout=20, max_bytes=524288), n
            except si_fetch.FetchError as exc:
                return exc, n

    def test_AT_630_7_1_public_ip_table(self):
        for line in px.APPX_A.split("\n")[:-1]:
            addr, want = line.split("\t")
            self.assertEqual(netguard.is_public_ip(addr), want == "T", repr(addr))

    def test_AT_630_7_2_parity_table_hash(self):
        self.assertEqual(hashlib.sha256(px.APPX_A.encode("utf-8")).hexdigest(), px.APPX_SHA["A"])
        self.assertEqual(len(px.APPX_A.encode("utf-8")), 441)

    def test_AT_630_7_E_1_literal_rules_precede_dns(self):
        bad = ["http://www.x.org/", "https://www.x.org:8443/", "https://www.x.org./",
               "https://u@www.x.org/", "https:///x", "https://xn--e1afmkfd.example/",
               "https://１２７.0.0.1/"]
        for url in bad:
            self.assertTrue(netguard.url_shape_problems(url), url)
            got, n = self.chain(url, {})
            self.assertIsInstance(got, si_fetch.FetchError, url)
            self.assertEqual(n.resolved, [], url)
        self.assertEqual(netguard.url_shape_problems("https://www.x.org:443/"), [])

    def test_AT_630_7_E_2_every_address_must_be_public(self):
        ok = {("www.x.org", "/"): text_resp(b"ok")}
        for addrs, reason in (([px.PUBLIC_IP, "10.0.0.1"], "private-ip"), ([], "network"),
                              (["::ffff:127.0.0.1"], "private-ip")):
            got, n = self.chain("https://www.x.org/", ok, addrs={"www.x.org": addrs})
            self.assertEqual(got.reason, reason, addrs)
            self.assertEqual(n.connects, [])
        got, n = self.chain("https://www.x.org/", ok)
        self.assertEqual((got.status, n.resolved), (200, ["www.x.org"]))
        redir = {("www.x.org", "/"): px.response(302, {"Location": "/b"}),
                 ("www.x.org", "/b"): text_resp(b"ok")}
        got, n = self.chain("https://www.x.org/", redir)
        self.assertEqual(n.resolved, ["www.x.org", "www.x.org"])

    def test_AT_630_7_3_connects_to_validated_ip_with_original_name(self):
        got, n = self.chain("https://www.x.org/p?q=1", {("www.x.org", "/p?q=1"): text_resp(b"ok")})
        self.assertEqual(n.connects, [(px.PUBLIC_IP, 443, "www.x.org")])
        self.assertEqual(n.requests[0]["host"], "www.x.org")
        self.assertEqual(got.raw, b"ok")

    def test_AT_630_7_E_3_redirect_targets_are_rechecked(self):
        for i, loc in enumerate(("https://evil.example.net/", "https://10.0.0.1/",
                                 "http://www.x.org/b", "https://www.x.org:8443/b")):
            got, n = self.chain("https://www.x.org/", {
                ("www.x.org", "/"): px.response(302, {"Location": loc})})
            self.assertEqual(got.reason, "redirect-refused", loc)
            self.assertEqual(len(n.connects), 1, loc)
        table = {("www.x.org", f"/{i}"): px.response(302, {"Location": f"/{i + 1}"})
                 for i in range(8)}
        got, n = self.chain("https://www.x.org/0", table)
        self.assertEqual(got.reason, "redirect-refused")
        self.assertEqual(len(n.connects), 6)  # 初始請求加 5 跳，第 6 跳不連線
        ok = {("www.x.org", "/"): px.response(302, {"Location": "https://www.x.org/b"}),
              ("www.x.org", "/b"): text_resp(b"ok")}
        self.assertEqual(self.chain("https://www.x.org/", ok)[0].raw, b"ok")

    def test_AT_630_7_E_4_only_fetch_imports_network_modules(self):
        tree = ast.parse((PKG / "netguard.py").read_text(encoding="utf-8"))
        names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                 for a in n.names}
        names |= {n.module.split(".")[0] for n in ast.walk(tree)
                  if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
        self.assertEqual(names - {"__future__"}, {"ipaddress", "re"})
        for path in sorted(PKG.glob("*.py")):
            mods = set()
            for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(n, ast.Import):
                    mods |= {a.name.split(".")[0] for a in n.names}
                elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                    mods.add(n.module.split(".")[0])
            if mods & {"socket", "ssl", "http", "urllib"}:
                self.assertEqual(path.name, "fetch.py")


class TestExpand(NfCase):
    """tools/lib/selfimproving/expand.py 與 research.py 的文章展開（AC-SI-30-8）。"""

    BASE = "https://www.anthropic.com/sitemap.xml"

    def test_AT_630_8_1_sitemap_selection(self):
        xml = sitemap(("https://www.anthropic.com/research/old", "2025-01-01"),
                      ("https://www.anthropic.com/research/new", "2026-05-01T10:00:00Z"),
                      ("https://www.anthropic.com/research/nodate", None),
                      ("https://www.anthropic.com/research/tie-a", "2026-05-01"),
                      ("https://other.example.org/research/x", "2027-01-01"),
                      ("https://www.anthropic.com/news/x", "2027-01-01"),
                      ("https://www.anthropic.com/research/old", "2025-01-01"),
                      (self.BASE, "2028-01-01"), ("https://www.anthropic.com/research/tie-b",
                                                  "2026-05-01"))
        got = expand.select(expand.sitemap_entries(xml), self.BASE, P_RESEARCH, 3)
        self.assertEqual(got, ["https://www.anthropic.com/research/new",
                               "https://www.anthropic.com/research/tie-a",
                               "https://www.anthropic.com/research/tie-b"])
        short = sitemap(("https://www.anthropic.com/research/nodate", None),
                        ("https://www.anthropic.com/research/old", "2025-01-01"))
        self.assertEqual(expand.select(expand.sitemap_entries(short), self.BASE, P_RESEARCH, 9),
                         ["https://www.anthropic.com/research/old",
                          "https://www.anthropic.com/research/nodate"])  # 缺 lastmod 者最後
        self.assertEqual(expand.select(expand.sitemap_entries(xml), self.BASE, P_RESEARCH, 1),
                         ["https://www.anthropic.com/research/new"])

    def test_AT_630_8_2_links_mode(self):
        base = "https://www.x.org/blog/index.html"
        html = (b'<a href="post1.html#top">1</a><a href="../blog/post2.html">2</a>'
                b'<a href="mailto:a@b.c">m</a><a href="/blog/post1.html">dup</a>'
                b'<a href="https://other.example.org/blog/z">o</a><a href="#only">f</a>')
        got = expand.select(expand.link_targets(html, "text/html", base), base, P_BLOG, 9)
        self.assertEqual(got, ["https://www.x.org/blog/post1.html",
                               "https://www.x.org/blog/post2.html"])
        atom = (b'<feed xmlns="http://www.w3.org/2005/Atom"><link rel="alternate" '
                b'href="/blog/a"/><link rel="self" href="/feed"/><entry><link rel="alternate" '
                b'href="/blog/b"/></entry></feed>')
        rss = b"<rss><channel><item><link>https://www.x.org/blog/c</link></item></channel></rss>"
        self.assertEqual(expand.select(expand.link_targets(atom, "application/atom+xml", base),
                                       base, P_BLOG, 9),
                         ["https://www.x.org/blog/a", "https://www.x.org/blog/b"])
        self.assertEqual(expand.select(expand.link_targets(rss, "application/rss+xml", base),
                                       base, P_BLOG, 9), ["https://www.x.org/blog/c"])

    def test_AT_630_8_E_1_doctype_never_reaches_the_parser(self):
        bomb = (b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "' + b"A" * 100 + b'">]>'
                b"<urlset><url><loc>https://www.x.org/a</loc></url></urlset>")
        cdata = (b'<urlset><url><loc><![CDATA[<!DOCTYPE x>]]></loc></url></urlset>')
        for raw in (bomb, cdata, b"x" * (expand.XML_LOAD_MAX + 1)):
            with mock.patch.object(expand, "_parse_xml", wraps=expand._parse_xml) as spy:
                with self.assertRaises(expand.ExpandRefused):
                    expand.sitemap_entries(raw)
            self.assertEqual(spy.call_count, 0)
        with mock.patch.object(expand, "_parse_xml", wraps=expand._parse_xml) as spy:
            expand.sitemap_entries(sitemap(("https://www.x.org/a", None)))
        self.assertGreaterEqual(spy.call_count, 1)
        ws = [watch("anthro", "https://www.x.org/s.xml",
                    expand_={"mode": "sitemap", "prefix": "/", "max": 3}, kind="sitemap")]
        repo, rc, out, _ = self.scan(ws, {("www.x.org", "/s.xml"): text_resp(
            bomb, ctype="application/xml")})
        self.assertEqual(rc, 0, out)
        raw = (self.home / "research/_scans" / f"{fx.rid(1)}.json").read_bytes()
        self.assertEqual(json.loads(raw)["items"], [{"source": "anthro",
                                                      "status": "expand-refused"}])

    def _site(self, extra_ws=()):
        ws = [watch("site", "https://www.x.org/sitemap.xml", kind="sitemap",
                    expand_={"mode": "sitemap", "prefix": P_R, "max": 3})]
        smap = sitemap(*((f"https://www.x.org/r/{n}", f"2026-01-0{i}")
                         for i, n in enumerate("abc", 1)))
        html = b"<html><head><title>t</title></head><body><p>Hello world</p></body></html>"
        table = {("www.x.org", "/sitemap.xml"): text_resp(smap, ctype="application/xml"),
                 **{("www.x.org", f"/r/{n}"): text_resp(html, ctype="text/html") for n in "abc"}}
        return ws, table, html

    def test_AT_630_8_3_integration_articles_and_details(self):
        ws, table, html = self._site()
        repo = px.repo(mirror=mirror_of(*ws))
        addrs = {"www.x.org": [[px.PUBLIC_IP], [px.PUBLIC_IP], ["10.0.0.1"], [px.PUBLIC_IP]]}
        rc, out, _ = self.rerun(repo, table, addrs=addrs)
        self.assertEqual(rc, 2, out)
        ev = self.scans(repo)[0]
        sha12 = hashlib.sha256(html).hexdigest()[:12]
        arts = sorted((self.home / "research/site/articles").glob("*.txt"))
        self.assertEqual({p.name for p in arts}, {f"{sha12}.txt", f"{sha12}.plain.txt"})
        raw = (self.home / "research/_scans" / f"{fx.rid(1)}.json").read_bytes()
        items = json.loads(raw)["items"]
        self.assertEqual(len(items), 3)
        self.assertEqual([i["status"] for i in items], ["ok", "private-ip", "ok"])
        self.assertEqual(ev["articles_n"], 3)
        self.assertEqual(ev["articles_sha256"], px.sha_of(raw))
        self.assertNotIn("https://www.x.org/r/", json.dumps(ev))

    def test_AT_630_8_4_event_size_does_not_grow_with_details(self):
        ev = {"seq": 12345, "t": px.TIME, "kind": "research.scan", "by": "researcher",
              "run": "RUN-SI-999", "fetched_at": px.TIME, "registry_seq": 12345,
              "registry_sha256": "sha256:" + "c" * 64, "articles_n": 30,
              "articles_sha256": "sha256:" + "f" * 64,
              "sources": [{"id": "a" * 32, "sha256": "sha256:" + "d" * 64, "bytes": 524288,
                           "changed": False, "http_status": 200} for _ in range(10)]}
        def size() -> int:
            return len(json.dumps(ev, ensure_ascii=False, separators=(",", ":")).encode())
        self.assertEqual(size(), 2119)
        big = [{"source": "a", "url": "https://x.org/" + "u" * 2034, "rank": i + 1,
                "status": "ok"} for i in range(30)]
        research._write_items(self.home, "RUN-SI-999", big)
        self.assertEqual(size(), 2119)
        self.assertLessEqual(size(), 4096)

    def test_AT_630_8_5_expansion_runs_on_every_scan(self):
        ws, table, html = self._site()
        repo = px.repo(mirror=mirror_of(*ws))
        self.assertEqual(self.rerun(repo, table)[0], 0)
        first = json.loads((self.home / "research/_scans" / f"{fx.rid(1)}.json").read_bytes())
        self.assertTrue(all(i["changed"] for i in first["items"]))
        fx.append_events(repo, [fx.ev("run.close", run=fx.rid(1), no_event=True),
                                fx.run_open_ev(2)])
        table[("www.x.org", "/r/b")] = text_resp(b"<p>changed</p>", ctype="text/html")
        table[("www.x.org", "/r/c")] = px.response(500)
        rc, out, n = self.rerun(repo, table, run=2)
        self.assertEqual(rc, 2, out)
        second = json.loads((self.home / "research/_scans" / f"{fx.rid(2)}.json").read_bytes())
        self.assertEqual([(i["url"][-1], i["status"], i.get("changed")) for i in second["items"]],
                         [("c", "http-status", None), ("b", "ok", True), ("a", "ok", False)])
        self.assertEqual(len([r for r in n.requests if r["path"].startswith(P_R)]), 3)
        # 上次明細被改一字 ⇒ 全部 changed=true
        fx.append_events(repo, [fx.ev("run.close", run=fx.rid(2), no_event=True),
                                fx.run_open_ev(3)])
        path = self.home / "research/_scans" / f"{fx.rid(2)}.json"
        path.write_bytes(path.read_bytes().replace(b"changed", b"chonged", 1))
        table[("www.x.org", "/r/c")] = text_resp(html, ctype="text/html")
        self.rerun(repo, table, run=3)
        third = json.loads((self.home / "research/_scans" / f"{fx.rid(3)}.json").read_bytes())
        self.assertTrue(all(i["changed"] for i in third["items"]))

    def test_AT_630_8_E_2_article_keys_validation(self):
        base = {"seq": 3, "t": px.TIME, "kind": "research.scan", "by": "researcher",
                "run": fx.rid(1), "fetched_at": px.TIME,
                "sources": [{"id": "a", "sha256": "sha256:" + "d" * 64, "bytes": 1,
                             "changed": True, "http_status": 200}]}
        from lib.selfimproving import events as si_events
        sha = "sha256:" + "f" * 64
        new = {"registry_seq": 1, "registry_sha256": sha}
        for extra in ({**new, "articles_n": 100, "articles_sha256": sha},
                      {**new, "articles_n": 3},
                      {"sources_sha256": sha, "articles_n": 3, "articles_sha256": sha}):
            self.assertTrue(si_events.validate({**base, **extra}), extra)
        self.assertEqual(si_events.sound([{**base, **new, "articles_n": 3,
                                           "articles_sha256": sha}]), [{**base, **new,
                                                                        "articles_n": 3,
                                                                        "articles_sha256": sha}])


class TestHtmlText(unittest.TestCase):
    """tools/lib/selfimproving/htmltext.py（AC-SI-30-9）。"""

    def test_AT_630_9_1_golden(self):
        raw = (FIX / "html_golden.html").read_bytes()
        self.assertEqual(htmltext.to_plain(raw), (FIX / "html_golden.txt").read_bytes())
        text = (FIX / "html_golden.txt").read_text(encoding="utf-8")
        for gone in ("隱藏的標題", "不該出現", "無腳本提示", "巢狀", "圖形文字", "模板內容"):
            self.assertFalse(any(gone in ln for ln in text.split("\n")), gone)

    def test_AT_630_9_2_deterministic_across_hash_seeds(self):
        raw = (FIX / "html_golden.html").read_bytes()
        want = hashlib.sha256(htmltext.to_plain(raw)).hexdigest()
        code = ("import hashlib,sys;sys.path.insert(0,sys.argv[1]);"
                "from lib.selfimproving import htmltext;"
                "print(hashlib.sha256(htmltext.to_plain(open(sys.argv[2],'rb').read()))"
                ".hexdigest())")
        for seed in ("1", "4242"):
            res = subprocess.run(
                [sys.executable, "-I", "-c", code, str(ROOT / "tools"),
                 str(FIX / "html_golden.html")],
                capture_output=True, encoding="utf-8", check=True,
                env={**os.environ, "PYTHONHASHSEED": seed})
            self.assertEqual(res.stdout.strip(), want)
        self.assertLessEqual(len(htmltext.to_plain(raw)), len(raw))

    def test_AT_630_9_E_1_empty_and_script_only(self):
        self.assertEqual(htmltext.to_plain(b""), b"")
        self.assertEqual(htmltext.to_plain(b"<script>x</script>"), b"")
        self.assertEqual(htmltext.to_plain(b"<p>a</p>"), b"a\n")
        out = htmltext.to_plain("<p>你好</p>\n\n\n<p>世界</p>".encode())
        self.assertTrue(out.endswith(b"\n") and not out.endswith(b"\n\n"))


class TestStaging(NfCase):
    """tools/lib/selfimproving/patrolrun.py 的複製擴及旁檔與文章（AC-SI-30-10）。"""

    def _stage_fixture(self):
        sha = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
        home = self.home
        src_html, art_html, art_txt = b"<p>index</p>", b"<p>art</p>", b"plain-article"
        (home / "research/idx").mkdir(parents=True, exist_ok=True)
        (home / "research/idx/articles").mkdir(parents=True, exist_ok=True)
        s12 = sha(src_html)[:12]
        (home / f"research/idx/{s12}.txt").write_bytes(src_html)
        (home / f"research/idx/{s12}.plain.txt").write_bytes(b"index\n")
        a12, t12 = sha(art_html)[:12], sha(art_txt)[:12]
        (home / f"research/idx/articles/{a12}.txt").write_bytes(art_html)
        (home / f"research/idx/articles/{a12}.plain.txt").write_bytes(b"art\n")
        (home / f"research/idx/articles/{t12}.txt").write_bytes(art_txt)
        items = [{"source": "idx", "url": "https://x/a", "rank": 1,
                  "sha256": "sha256:" + sha(art_html), "bytes": 1,
                  "plain_sha256": "sha256:" + sha(b"art\n"), "changed": True, "status": "ok"},
                 {"source": "idx", "url": "https://x/t", "rank": 2,
                  "sha256": "sha256:" + sha(art_txt),
                  "bytes": 1, "plain_sha256": None, "changed": True, "status": "ok"},
                 {"source": "idx", "url": "https://x/u", "rank": 3, "sha256": "sha256:" + "0" * 64,
                  "bytes": 1, "plain_sha256": None, "changed": False, "status": "ok"}]
        raw_items = (json.dumps({"schema_rev": 1, "run": fx.rid(1), "items": items},
                                ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        (home / "research/_scans").mkdir(exist_ok=True)
        (home / f"research/_scans/{fx.rid(1)}.json").write_bytes(raw_items)
        scan = {"seq": 3, "t": px.TIME, "kind": "research.scan", "by": "researcher",
                "run": fx.rid(1), "fetched_at": px.TIME, "registry_seq": 1,
                "registry_sha256": "sha256:" + "c" * 64, "articles_n": 3,
                "articles_sha256": px.sha_of(raw_items),
                "sources": [{"id": "idx", "sha256": "sha256:" + sha(src_html), "bytes": 12,
                             "changed": True, "http_status": 200}]}
        events = fx.compose([fx.run_open_ev(1)], "0" * 40, [2]) + [scan]
        return events, (s12, a12, t12)

    def test_AT_630_10_1_stage_copies_sidecars_and_changed_articles(self):
        events, (s12, a12, t12) = self._stage_fixture()
        tdir = self.home / "patrol" / fx.rid(1)
        patrolrun.stage_sources(events, fx.rid(1), tdir)
        got = sorted(p.name for p in (tdir / "research").iterdir())
        self.assertEqual(got, sorted([f"{s12}.txt", f"{s12}.plain.txt", f"{a12}.plain.txt",
                                      f"{t12}.txt"]))
        for p in (tdir / "research").iterdir():
            self.assertTrue(any(p.read_bytes() == q.read_bytes()
                                for q in (self.home / "research").rglob(p.name)))
        listed = patrolrun._research_text(events, fx.rid(1), tdir)[1]
        self.assertEqual(sorted(Path(f).name for f in listed), got)
        self.assertTrue(all(f.startswith(str(tdir / "research")) for f in listed))

    def test_AT_630_10_E_1_mismatch_and_copy_failure_do_not_spawn(self):
        events, _ = self._stage_fixture()
        ctx = types.SimpleNamespace(si=self.home, load=lambda: events,
                                    verb=lambda *a, **k: (1, "", ""), log=lambda *a, **k: None)
        path = self.home / "research/_scans" / f"{fx.rid(1)}.json"
        path.write_bytes(path.read_bytes().replace(b"changed", b"chonged", 1))
        got = patrolrun.launch(ctx, fx.rid(1), trigger="f", due_at=px.TIME)
        self.assertEqual(got, ("failed", "sources-scans-mismatch"))
        events, _ = self._stage_fixture()
        ctx.load = lambda: events
        with mock.patch.object(Path, "write_bytes", side_effect=OSError("唯讀")):
            got = patrolrun.launch(ctx, fx.rid(1), trigger="f", due_at=px.TIME)
        self.assertEqual(got, ("failed", "sources-copy-failed: OSError"))
        self.assertFalse((self.home / "patrol" / fx.rid(1) / "research").exists())


if __name__ == "__main__":
    unittest.main()
