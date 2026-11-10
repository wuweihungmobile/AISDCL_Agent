"""SelfImproving P6 研究來源登記的驗收測試（TCS-SelfImproving-P6 RG 檔）。

受測模組：`tools/lib/selfimproving/registry.py`、`regwrite.py`、`research.py`（預檢）、
`evspec6.py`、
`evcheck.py`、`status.py`、`sched.py`、`patrol.py`。方法名含 AT 底線形；網路一律走 `px.net`，
測試不得真連網；合成 repo 於 tmp 目錄。
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import types
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p6_fixtures as px

from lib.selfimproving import consoleaudit, evwrite, patrol, registry, regwrite, sched, status
from lib.selfimproving import events as si_events
from lib.selfimproving import evspec6, issuemap, params
from lib.selfimproving import sources as si_sources
from lib.selfimproving import writeverbs as wv

ROOT = Path(__file__).resolve().parents[2]
ARXIV = next(w for w in px.golden_obj()["watch"] if w["id"] == "arxiv-agents")["url"]
ARXIV_PATH = "/" + ARXIV.split("/", 3)[3]
SITEMAP = (b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           b"</urlset>")


def setUpModule() -> None:
    fx.setup("si_rg_")


def tearDownModule() -> None:
    fx.teardown()


def golden_table() -> dict:
    return {("www.anthropic.com", "/sitemap.xml"): px.response(ctype="application/xml",
                                                              body=SITEMAP),
            ("export.arxiv.org", ARXIV_PATH): px.response(ctype="application/atom+xml",
                                                          body=b"<feed/>")}


def raw_of(repo: Path, rel: str):
    p = repo / rel
    return p.read_bytes() if p.is_file() else None


class RgCase(fx.SiTestCase):
    """RG 共用：金鑰環與 `registry-ingest`／`research --fetch` 的封裝。"""

    def setUp(self) -> None:
        super().setUp()
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": px.KEY})
        patcher.start()
        self.addCleanup(patcher.stop)

    def ingest(self, repo, ref=px.REF, *extra):
        return self.M(repo, "registry-ingest", "--carrier", "console", "--audit-ref", ref, *extra)

    def fetch(self, repo, table=None, **kw):
        with px.net(golden_table() if table is None else table, **kw) as n:
            rc, out, err = self.M(repo, "research", "--fetch", "--run", fx.rid(1))
        return rc, out, n

    def audit(self, **kw) -> str:
        return px.write_audit(self.home, **kw)

    def snapshot(self, repo):
        return raw_of(repo, px.MIRROR_REL), raw_of(repo, fx.EVL)

    def blank(self) -> Path:
        return px.repo(mirror=None, bound=False, run_open=False)


class TestPrecheck(RgCase):
    """tools/lib/selfimproving/research.py 預檢（AC-SI-30-2、30-5）。"""

    def test_AT_630_2_1_scan_binds_registry_event(self):
        repo = px.repo()
        rc, out, _ = self.fetch(repo)
        self.assertEqual(rc, 0, out)
        scans = [e for e in fx.EV(repo) if e["kind"] == "research.scan"]
        self.assertEqual(len(scans), 1)
        reg = next(e for e in fx.EV(repo) if e["kind"] == "research.registry")
        self.assertEqual((scans[0]["registry_seq"], scans[0]["registry_sha256"]),
                         (reg["seq"], reg["registry_sha256"]))
        self.assertNotIn("sources_sha256", scans[0])

    def test_AT_630_2_E_1_precheck_rejections_send_no_request(self):
        mid = px.mutate(lambda o: o["watch"][0].update(enabled=True, disabled_at=None,
                                                        disabled_by=None))
        many = px.mutate(lambda o: o["watch"].extend(
            {**o["watch"][2], "id": f"z{i:02d}", "enabled": True} for i in range(10)))
        none_on = px.mutate(lambda o: [w.update(enabled=False) for w in o["watch"]])
        spaced = px.repo()
        fx.putb(spaced, px.MIRROR_REL, json.dumps(
            px.golden_obj(), ensure_ascii=False, indent=4, sort_keys=True).encode() + b"\n")
        cases = [
            ("RUN-NOT-OPEN", px.repo(run_open=False)),
            ("RESEARCH-ALREADY", px.repo(extra=[fx.skip_ev(1)])),
            ("REGISTRY-ABSENT", px.repo(mirror=None)),
            ("REG-NORMAL", spaced),
            ("REGISTRY-UNBOUND", px.repo(bound=False)),
            ("FETCH-MAX", px.repo(mirror=many)),
            ("ZERO-SUCCESS", px.repo(mirror=none_on)),
        ]
        self.assertTrue(mid)
        for code, repo in cases:
            before = raw_of(repo, fx.EVL)
            rc, out, n = self.fetch(repo)
            self.assertEqual(rc, 1, (code, out))
            self.assertIn(code, fx.codes_of(out), out)
            self.assertIn("obs-draft:", out)
            self.assertEqual((n.connects, n.resolved), ([], []), code)
            self.assertEqual(raw_of(repo, fx.EVL), before, code)
        other = px.repo(mirror=px.mutate(lambda o: o["watch"][1].update(extract="另一個合法內容")),
                        bound=False)
        fx.append_events(other, [px.reg_event(px.APPX_B)])
        _, out, _ = self.fetch(other)
        self.assertIn("REGISTRY-UNBOUND", fx.codes_of(out))

    def test_AT_630_2_E_2_uncommitted_mirror_is_fine_and_old_table_not_read(self):
        repo = px.repo()
        fx.putb(repo, si_sources.SOURCES_REL, b"garbage")
        rc, out, _ = self.fetch(repo)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("SOURCES-UNCOMMITTED", out)

    def test_AT_630_2_E_3_host_outside_hosts_is_blocked(self):
        text = px.mutate(lambda o: o["hosts"].pop(0))  # 停用 export.arxiv.org
        repo = px.repo(mirror=text)
        rc, out, n = self.fetch(repo)
        self.assertEqual(rc, 2, out)
        self.assertEqual([r["host"] for r in n.requests], ["www.anthropic.com"])
        self.assertIn("FAIL blocked", out)
        scan = next(e for e in fx.EV(repo) if e["kind"] == "research.scan")
        self.assertEqual([s["id"] for s in scan["sources"]], ["anthropic-research"])
        self.assertIn("obs-draft:", out)

    def test_AT_630_2_E_4_registry_swapped_during_fetch(self):
        repo = px.repo()
        other = px.mutate(lambda o: o["watch"][1].update(extract="換了內容"))

        def hook():
            fx.putb(repo, px.MIRROR_REL, other.encode("utf-8"))
            fx.append_events(repo, [px.reg_event(other, ref=px.new_ref())])
        with mock.patch("lib.selfimproving.research.PAUSE_HOOK", hook):
            rc, out, _ = self.fetch(repo)
        self.assertEqual(rc, 1, out)
        self.assertIn("REGISTRY-CHANGED", fx.codes_of(out))
        self.assertEqual([e for e in fx.EV(repo) if e["kind"] == "research.scan"], [])

    def test_AT_630_5_1_only_enabled_sources_count_toward_the_limit(self):
        def add(o, n_on, n_off):
            base = o["watch"][2]
            o["watch"] = [w for w in o["watch"] if w["enabled"] is False]
            o["watch"] += [{**base, "id": f"e{i:02d}", "enabled": True} for i in range(n_on)]
            o["watch"] += [{**base, "id": f"f{i:02d}", "enabled": False} for i in range(n_off)]
            o["watch"].sort(key=lambda w: w["id"])
        ten = px.mutate(lambda o: add(o, 10, 5))
        eleven = px.mutate(lambda o: add(o, 11, 0))
        for text, want in ((ten, None), (eleven, "FETCH-MAX")):
            repo = px.repo(mirror=text)
            rc, out, _ = self.fetch(repo, table={})
            if want:
                self.assertIn(want, fx.codes_of(out), out)
            else:
                self.assertNotIn("FETCH-MAX", out)
        cap = json.loads((ROOT / "docs/06_quality/SelfImproving_Protocol/params.json"
                          ).read_text(encoding="utf-8"))
        self.assertEqual(cap["research_fetch_max"], 10)


class TestCandidateSource(RgCase):
    """tools/lib/selfimproving/registry.py 與 check.py 的候選來源解析（AC-SI-30-4）。"""

    ROW = [fx.obs_id(11), "2026-10-20 01:00", "情境", "症狀", "tools/lib/selfimproving/fresh.py:1",
           "bug", "P3", "open"]

    def row_check(self, src: str):
        marks = f"面=流程;來源=代理;回報者=研究者;外部衍生=是;src={src}"
        old = {"schema_rev": 1, "sources": [
            {"id": "old-live", "url": "https://example.com/", "kind": "docs", "extract": "x",
             "added_by": "T1"}]}
        repo = fx.make_p1_repo(fx.new_dir("rr"), sources=json.dumps(old) + "\n",
                               extra_obs=[[*self.ROW, marks]])
        fx.putb(repo, px.MIRROR_REL, px.APPX_B.encode("utf-8"))
        return self.F(self.check(repo), "row.markers")

    def test_AT_630_4_1_src_resolves_against_mirror_and_old_table(self):
        for ok in ("anthropic-engineering", "old-live", "arxiv-agents"):  # 停用／舊表／啟用
            self.assertEqual({s for s, _ in self.row_check(ok)} & {fx.obs_id(11)}, set(), ok)
        self.assertEqual(self.row_check("nope"), {(fx.obs_id(11), "SRC-UNKNOWN")})


class TestFingerprint(unittest.TestCase):
    """tools/lib/selfimproving/params.py 指紋排除（AC-SI-30-6）。"""

    def test_AT_630_6_1_mirror_and_old_table_do_not_change_the_fingerprint(self):
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp(prefix="si_fp_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        src = ROOT / "docs/06_quality/SelfImproving_Protocol"
        dst = tmp / "docs/06_quality/SelfImproving_Protocol"
        shutil.copytree(src, dst)

        def fp() -> str:
            meta = json.loads((dst / "params.json").read_text(encoding="utf-8"))
            return params.fingerprint(tmp, meta)[0]
        base = fp()
        (dst / "research_registry.json").write_bytes(px.APPX_B.encode("utf-8"))
        (dst / "research_sources.json").write_bytes(b"{}\n")
        self.assertEqual(fp(), base)
        for name in ("params.json", "metrics.md"):
            (dst / name).write_bytes((dst / name).read_bytes() + b"\n")
            self.assertNotEqual(fp(), base, name)
            (dst / name).write_bytes((src / name).read_bytes())
        self.assertEqual(params.FINGERPRINT_EXCLUDED,
                         frozenset({"research_sources.json", "research_registry.json"}))
        self.assertEqual(params.CHECK_RULES_REV, 6)


class TestIngestOrder(RgCase):
    """tools/lib/selfimproving/regwrite.py 驗證順序（AC-SI-45-1）。"""

    def put(self, name, raw: bytes) -> None:
        p = self.home / "console_audit" / f"{name}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)

    def test_AT_645_1_1_golden_ingests(self):
        repo = self.blank()
        self.audit()
        rc, out, err = self.ingest(repo, px.REF, "--by", "patrol")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(raw_of(repo, px.MIRROR_REL), px.APPX_B.encode("utf-8"))

    def test_AT_645_1_E_1_code_order_table(self):
        late = px.reg_event(when="2026-11-11T00:00:00+08:00", ref=px.new_ref())
        many = "x" * (registry.REGISTRY_TEXT_MAX + 1)
        outer_none = json.loads(px.audit_bytes())
        outer_none.pop("kind")
        pad = lambda n: {"padding": "x" * n}  # noqa: E731
        base = len(px.audit_bytes(outer=pad(0)))
        cases = [
            ("AUDIT-FILE-MISSING", None, False),
            ("AUDIT-SCHEMA", json.dumps(outer_none).encode() + b"\n", False),
            ("AUDIT-BODY-INVALID", px.audit_bytes(outer={"body": "not json"}), False),
            ("AUDIT-REF-MISMATCH", px.audit_bytes(ref=px.new_ref()), False),
            ("AUDIT-KIND-MISMATCH", px.audit_bytes(kind="obs-add"), False),
            ("ROLE-NOT-ADMIN", px.audit_bytes(role="VIEWER"), False),
            ("AUDIT-TIME-FORMAT", px.audit_bytes(when="2026-11-10T01:00:00Z"), False),
            ("AUDIT-MAC-MISMATCH", px.audit_bytes(mac="0" * 64), False),
            ("AUDIT-REF-REUSED", px.audit_bytes(), True),
            ("AUDIT-BODY-INVALID", px.audit_bytes(body_extra={"extra": 1}), False),
            ("AUDIT-BODY-INVALID", px.audit_bytes(body_drop=("registry_text",)), False),
            ("AUDIT-BODY-INVALID", px.audit_bytes(sha="sha256:xyz"), False),
            ("REGISTRY-TOO-LARGE", px.audit_bytes(text=many), False),
            ("AUDIT-FILE-TOO-LARGE", px.audit_bytes(
                outer=pad(registry.AUDIT_FILE_MAX + 1 - base)), False),
            ("REGISTRY-SHA-MISMATCH", px.audit_bytes(sha="sha256:" + "0" * 64), False),
            ("REG-WATCH-KIND", px.audit_bytes(text=px.mutate(
                lambda o: o["watch"][1].update(kind="rss"))), False),
            ("REG-STALE", px.audit_bytes(), "late"),
        ]
        for code, raw, special in cases:
            repo = px.repo(mirror=None, bound=False, run_open=False,
                           extra=[px.reg_event(ref=px.REF)] if special is True else
                           [late] if special == "late" else [])
            if raw is not None:
                self.put(px.REF, raw)
            else:
                (self.home / "console_audit" / f"{px.REF}.json").unlink(missing_ok=True)
            before = self.snapshot(repo)
            rc, out, _ = self.ingest(repo)
            self.assertEqual(rc, 1, (code, out))
            self.assertEqual(fx.codes_of(out), {code}, (code, out))
            self.assertIn("obs-draft:", out)
            self.assertEqual(self.snapshot(repo), before, code)
        repo = self.blank()
        self.put(px.REF, px.audit_bytes(key=px.KEY))
        with mock.patch.dict(os.environ, {"AUTOSDD_SI_AUDIT_KEY": ""}):
            _, out, _ = self.ingest(repo)
        self.assertIn("AUDIT-KEY-MISSING", fx.codes_of(out))

    def test_AT_645_1_2_validate_variant_table(self):
        def one(fn):
            return sorted({c for c, _, _ in registry.validate(px.mutate(fn).encode("utf-8"))})

        def watch(**kw):
            return lambda o: o["watch"][1].update(**kw)
        raw = px.APPX_B.encode("utf-8")
        table = [
            (b"\xef\xbb\xbf" + raw, "REG-FILE-FORMAT"), (raw.replace(b"\n", b"\r\n"),
                                                         "REG-FILE-FORMAT"),
            (raw.rstrip(b"\n"), "REG-FILE-FORMAT"), (b"[]\n", "REG-FILE-FORMAT"),
            (raw.replace(b'"schema_rev": 1', b'"schema_rev": true'), "REG-SCHEMA"),
            (raw.replace(b'  "schema_rev": 1,\n', b""), "REG-SCHEMA"),
            (json.dumps(json.loads(raw), indent=4, sort_keys=True).encode() + b"\n", "REG-NORMAL"),
        ]
        for data, code in table:
            self.assertEqual([c for c, _, _ in registry.validate(data)][:1], [code], code)
        cases = [
            (lambda o: o["hosts"][0].update(host="EXAMPLE.org"), "REG-HOST-FORMAT"),
            (lambda o: o["hosts"][0].update(host="a.org."), "REG-HOST-FORMAT"),
            (lambda o: o["hosts"][0].update(list_kind="X"), "REG-HOST-FORMAT"),
            (lambda o: o["hosts"][0].update(source="Y"), "REG-HOST-FORMAT"),
            (lambda o: o["hosts"][0].update(layer="Z"), "REG-HOST-FORMAT"),
            (lambda o: o["hosts"][0].update(min_interval_seconds=0), "REG-HOST-FORMAT"),
            (lambda o: o["hosts"][0].update(min_interval_seconds=True), "REG-HOST-FORMAT"),
            (lambda o: o["hosts"].append(dict(o["hosts"][1])), "REG-HOST-DUP"),
            (lambda o: o["hosts"].reverse(), "REG-HOST-ORDER"),
            (watch(id="Upper"), "REG-WATCH-ID"), (watch(id="a" * 33), "REG-WATCH-ID"),
            (lambda o: o["watch"].append(dict(o["watch"][2])), "REG-WATCH-DUP"),
            (lambda o: o["watch"].reverse(), "REG-WATCH-ORDER"),
            (watch(kind="rss"), "REG-WATCH-KIND"),
            (watch(url="http://www.anthropic.com/x"), "REG-WATCH-URL"),
            (watch(url="https://www.anthropic.com:8443/x"), "REG-WATCH-URL"),
            (watch(url="https://www.anthropic.com./x"), "REG-WATCH-URL"),
            (watch(url="https://u@www.anthropic.com/x"), "REG-WATCH-URL"),
            (watch(url="https://127.0.0.1/x"), "REG-WATCH-URL"),
            (watch(url="https://xn--e1afmkfd.example/"), "REG-WATCH-URL"),
            (watch(url="https://a.example/" + "x" * 2049), "REG-WATCH-URL"),
            (watch(extract=""), "REG-WATCH-FIELD"), (watch(extract="x" * 201), "REG-WATCH-FIELD"),
            (watch(extract="a\x07b"), "REG-WATCH-FIELD"), (watch(enabled="yes"), "REG-WATCH-FIELD"),
            (watch(added_at="2026-11-10T00:00:00Z"), "REG-WATCH-TIME"),
            (watch(added_at="2026-11-10T00:00:00+08:00"), "REG-WATCH-TIME"),
            (watch(expand={"max": 4, "mode": "sitemap", "prefix": "/r/"}), "REG-WATCH-EXPAND"),
            (watch(expand={"max": 1, "mode": "x", "prefix": "/r/"}), "REG-WATCH-EXPAND"),
            (watch(expand={"max": 1, "mode": "links", "prefix": "research"}), "REG-WATCH-EXPAND"),
            (watch(expand={"max": 1, "mode": "links", "prefix": "/r/", "x": 1}),
             "REG-WATCH-EXPAND"),
        ]
        for fn, code in cases:
            self.assertEqual(one(fn), [code], code)
        self.assertEqual(one(lambda o: (o.update(hosts=[]), o.update(watch=[]))), [])
        self.assertEqual(one(lambda o: o["hosts"].pop(0)), [])  # 啟用來源的 host 不在 hosts：不判

    def test_AT_645_1_3_golden_matches_appendix_b_bytes(self):
        raw = px.APPX_B.encode("utf-8")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), px.APPX_SHA["B"])
        self.assertEqual(len(raw), 2039)
        self.assertEqual(registry.validate(raw), [])
        obj = json.loads(px.APPX_B)
        self.assertEqual(px.registry_text(obj["hosts"], obj["watch"]), px.APPX_B)
        by_id = {w["id"]: w for w in obj["watch"]}
        mig = "migration:V24（"
        eng = by_id["anthropic-engineering"]
        self.assertEqual(eng["added_by"], mig + "SI research_sources.json 匯入）")
        self.assertEqual(eng["disabled_by"], mig + "以 anthropic-research 取代）")
        self.assertEqual(by_id["anthropic-research"]["added_by"], mig + "研究來源單一化種子）")
        self.assertEqual(by_id["arxiv-agents"]["added_by"], mig + "研究來源單一化種子）")
        stamp = "2026-11-10T00:00:00+00:00"
        self.assertEqual({w["added_at"] for w in obj["watch"]}, {stamp})
        self.assertEqual(by_id["anthropic-engineering"]["disabled_at"], stamp)
        self.assertEqual([(h["host"], h["source"], h["min_interval_seconds"])
                          for h in obj["hosts"]],
                         [("export.arxiv.org", "ENV", 3), ("www.anthropic.com", "ADMIN", 5)])
        old = {e["id"]: e for e in si_sources.entries_of(
            (ROOT / si_sources.SOURCES_REL).read_bytes())}
        self.assertEqual(by_id["anthropic-engineering"]["extract"],
                         old["anthropic-engineering"]["extract"])

    def test_AT_645_1_6_url_parity_table(self):
        raw = px.APPX_D.encode("utf-8")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), px.APPX_SHA["D"])
        rows = [ln.split("\t") for ln in px.APPX_D.split("\n") if ln]
        self.assertGreaterEqual(len(rows), 17)
        for url, si, con in rows:
            codes = [c for c, _, _ in registry.validate(
                px.mutate(lambda o: o["watch"][1].update(url=url)).encode("utf-8"))]
            self.assertEqual("REG-WATCH-URL" not in codes, si == "T", url)
            self.assertTrue(con != "T" or si == "T", f"Console ⊆ SI 違反：{url}")

    def test_AT_645_1_7_seed_urls_all_valid(self):
        rows = [ln.split("\t") for ln in px.APPX_D.split("\n") if ln][-17:]
        self.assertEqual(len(rows), 17)
        for url, si, con in rows:
            self.assertEqual((si, con), ("T", "T"), url)
            text = px.mutate(lambda o: o["watch"][1].update(url=url))
            self.assertEqual(registry.validate(text.encode("utf-8")), [], url)

    def test_AT_645_1_8_g_s1_matches_regenerated_bytes(self):
        path = ROOT / px.G_S1_REL
        self.assertTrue(path.is_file(), "G-S1 黃金檔不存在")
        self.assertEqual(path.read_bytes(), px.g_s1_bytes())
        self.assertEqual(hashlib.sha256(px.APPX_C.encode("utf-8")).hexdigest(), px.APPX_SHA["C"])

    def test_AT_645_1_9_monotonic_audit_time(self):
        repo = self.blank()
        a = px.new_ref()
        self.audit(ref=a, when="2026-11-10T09:00:00+08:00")
        self.assertEqual(self.ingest(repo, a)[0], 0)
        b = px.new_ref()
        self.audit(ref=b, when="2026-11-10T08:59:00+08:00")
        before = self.snapshot(repo)
        rc, out, _ = self.ingest(repo, b)
        self.assertEqual((rc, fx.codes_of(out)), (1, {"REG-STALE"}), out)
        self.assertEqual(self.snapshot(repo), before)
        self.assertTrue((self.home / "console_audit" / f"{b}.json").is_file())
        c = px.new_ref()
        self.audit(ref=c, when="2026-11-10T09:00:00+08:00")
        self.assertEqual(self.ingest(repo, c)[0], 0)
        d = px.new_ref()
        self.audit(ref=d, when="2026-11-10T01:30:00+00:00")  # 絕對時刻較晚（09:30+08:00）
        self.assertEqual(self.ingest(repo, d)[0], 0)

    def test_AT_645_1_4_size_constants_and_boundaries(self):
        self.assertEqual((registry.REGISTRY_TEXT_MAX, registry.AUDIT_FILE_MAX), (24576, 65536))
        exact = self._exact()
        self.assertEqual(len(exact.encode()), registry.REGISTRY_TEXT_MAX)
        self.assertEqual(registry.validate(exact.encode()), [])
        repo = self.blank()
        self.audit(text=exact)
        self.assertEqual(self.ingest(repo)[0], 0)
        over = self.blank()
        self.audit(text=exact + " ")
        before = self.snapshot(over)
        _, out, _ = self.ingest(over)
        self.assertEqual(fx.codes_of(out), {"REGISTRY-TOO-LARGE"})
        self.assertEqual(self.snapshot(over), before)  # 不截斷、零寫入
        # 稽核外層檔：恰 65,536 位元組通過大小關卡（落到後續判準）、65,537 即拒收
        base = len(px.audit_bytes(outer={"padding": ""}))
        for size, want in ((registry.AUDIT_FILE_MAX, "AUDIT-SCHEMA"),
                           (registry.AUDIT_FILE_MAX + 1, "AUDIT-FILE-TOO-LARGE")):
            raw = px.audit_bytes(outer={"padding": "x" * (size - base)})
            self.assertEqual(len(raw), size)
            fresh = self.blank()
            (self.home / "console_audit").mkdir(parents=True, exist_ok=True)
            (self.home / "console_audit" / f"{px.REF}.json").write_bytes(raw)
            self.assertEqual(fx.codes_of(self.ingest(fresh)[1]), {want})

    def _exact(self) -> str:
        """恰 24,576 位元組的合格鏡像：停用來源以 200 字元 extract 湊近，最後一筆補差。"""
        obj = px.golden_obj()
        base = obj["watch"][2]
        def make(n: int, lens: list[int]) -> str:
            watch = [{**base, "id": f"p{i:03d}", "enabled": False, "extract": "x" * lens[i]}
                     for i in range(n)]
            return px.registry_text(obj["hosts"], watch)
        for n in range(2, 300):
            lo = len(make(n, [1] * n).encode())
            if lo <= registry.REGISTRY_TEXT_MAX <= len(make(n, [200] * n).encode()):
                extra, lens = registry.REGISTRY_TEXT_MAX - lo, [1] * n
                for i in range(n):  # 把差額分攤到各筆（每筆至多再加 199 個字元）
                    lens[i] += min(extra, 199)
                    extra -= min(extra, 199)
                return make(n, lens)
        raise AssertionError("湊不出恰 24,576 位元組的樣本")

    def test_AT_645_1_5_g_s1_ingests_to_the_golden_mirror(self):
        repo = self.blank()
        path = self.home / "console_audit" / f"{px.REF}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / px.G_S1_REL).read_bytes())
        outer = json.loads(path.read_bytes())
        self.assertEqual(list(outer), ["schema_rev", "kind", "audit_ref", "subject", "body",
                                       "key_id", "mac"])
        body = json.loads(outer["body"])
        self.assertEqual(list(body), ["schema_rev", "audit_ref", "kind", "user", "role", "time",
                                      "registry_text", "registry_sha256"])
        self.assertEqual(consoleaudit.verify(path, [px.KEY.encode()]).body["kind"], "src-registry")
        self.assertEqual(self.ingest(repo)[0], 0)
        self.assertEqual(raw_of(repo, px.MIRROR_REL), px.APPX_B.encode("utf-8"))
        raw = path.read_bytes()
        self.assertTrue(raw.endswith(b"\n") and not raw.endswith(b"\n\n"))
        self.assertNotIn(b"\\u", raw)


class TestIngestAtomic(RgCase):
    """tools/lib/selfimproving/regwrite.py 原子入帳與冪等（AC-SI-45-2）。"""

    def test_AT_645_2_1_event_fields(self):
        repo = self.blank()
        self.audit()
        rc, out, _ = self.ingest(repo, px.REF, "--by", "patrol")
        self.assertEqual(rc, 0, out)
        self.assertIn("watch=3/2 hosts=2", out)
        ev = next(e for e in fx.EV(repo) if e["kind"] == "research.registry")
        want = {"audit_ref": px.REF, "carrier": "console", "decider": "admin", "by": "patrol",
                "audit_time": px.TIME, "registry_sha256": px.sha_of(px.APPX_B.encode()),
                "hosts_n": 2, "watch_n": 3, "watch_on": 2, "changed": True, "seq": 1}
        self.assertEqual({k: ev[k] for k in want}, want)
        self.assertEqual(ev["audit_sha256"], px.sha_of(px.g_s1_bytes()))
        self.assertEqual(ev["key_id"], consoleaudit.key_id_of(px.KEY.encode()))

    def test_AT_645_2_2_unchanged_content_does_not_rewrite(self):
        repo = self.blank()
        self.audit()
        self.ingest(repo)
        again = px.new_ref()
        self.audit(ref=again, when="2026-11-10T10:00:00+08:00")
        with mock.patch("os.replace", side_effect=AssertionError("不得換檔")) as rep:
            rc, out, _ = self.ingest(repo, again)
        self.assertEqual((rc, rep.call_count), (0, 0), out)
        self.assertFalse(fx.EV(repo)[-1]["changed"])
        pend = status.console_pending(si_events.load_sound_events(repo / fx.EVL))
        self.assertEqual(pend["count"], 0)

    def test_AT_645_2_E_1_event_failure_restores_mirror(self):
        orig = wv.params_for
        small = lambda r, *k: {**orig(r, *k), "event_max_bytes": 100}  # noqa: E731
        for old in (None, px.mutate(lambda o: o["watch"][1].update(extract="舊"))):
            repo = px.repo(mirror=old, bound=False, run_open=False)
            self.audit()
            before = self.snapshot(repo)
            with mock.patch.object(wv, "params_for", small):
                rc, out, _ = self.ingest(repo)
            self.assertEqual(rc, 1, out)
            self.assertIn("EVENT-BYTES-OVER", fx.codes_of(out))
            self.assertEqual(self.snapshot(repo), before)

    def test_AT_645_2_E_2_replace_failure_is_a_clean_reject(self):
        repo = self.blank()
        self.audit()
        with mock.patch("os.replace", side_effect=PermissionError("x")):
            rc, out, _ = self.ingest(repo)
        self.assertEqual((rc, fx.codes_of(out)), (1, {"LEDGER-WRITE-FAILED"}), out)
        self.assertEqual(list(repo.joinpath(px.MIRROR_REL).parent.glob("*.tmp")), [])
        self.assertEqual(fx.EV(repo), [])

    def test_AT_645_2_E_3_ref_reused_inside_the_lock(self):
        repo = self.blank()
        self.audit()

        def hook():
            fx.append_events(repo, [px.reg_event()])
        with mock.patch.object(regwrite, "PAUSE_HOOK", hook):
            rc, out, _ = self.ingest(repo)
        self.assertEqual((rc, fx.codes_of(out)), (1, {"AUDIT-REF-REUSED"}), out)
        self.assertIsNone(raw_of(repo, px.MIRROR_REL))
        self.assertEqual(len(fx.EV(repo)), 1)

    def test_AT_645_2_E_4_crash_window_self_heals(self):
        repo = px.repo(bound=False)
        rc, out, _ = self.fetch(repo)
        self.assertIn("REGISTRY-UNBOUND", fx.codes_of(out))
        self.audit()
        self.assertEqual(self.ingest(repo)[0], 0)
        rc, out, _ = self.fetch(repo)
        self.assertEqual(rc, 0, out)


class TestCheckBinding(RgCase):
    """tools/lib/selfimproving/evcheck.py 鏡像綁定（AC-SI-45-3）。"""

    def test_AT_645_3_1_ingested_repo_checks_green(self):
        repo = self.blank()
        self.audit()
        self.ingest(repo)
        res = self.check(repo)
        self.assertEqual(len(res["items"]), 35)
        for item in ("research.sources", "events.research", "events.prop_files"):
            self.assertEqual(res["_item"][item]["status"], "PASS", res["_item"][item])

    def test_AT_645_3_E_1_unbound_mirror_variants(self):
        edited = px.repo()
        fx.putb(edited, px.MIRROR_REL, px.mutate(
            lambda o: o["watch"][1].update(extract="手改一字")).encode("utf-8"))
        only_mirror = px.repo(bound=False)
        only_event = px.repo()
        (only_event / px.MIRROR_REL).unlink()
        for repo in (edited, only_mirror, only_event):
            it = self.check(repo)["_item"]["events.research"]
            self.assertEqual(it["status"], "FAIL", it)
            self.assertIn("REGISTRY-UNBOUND", {f["code"] for f in it["findings"]})
        none = px.repo(mirror=None)
        fx.write_events(none, [fx.run_open_ev(1)])
        it = self.check(none)["_item"]["events.research"]
        self.assertEqual(it["status"], "NE")
        self.assertFalse(it["blocking"])

    def test_AT_645_3_E_2_new_scan_event_binding(self):
        def scan(**kw):
            src = [{"id": "arxiv-agents", "sha256": "sha256:" + "1" * 64, "bytes": 5,
                    "changed": True, "http_status": 200}]
            return fx.ev("research.scan", by="researcher", run=fx.rid(1), sources=src,
                         fetched_at=px.TIME, **kw)
        sha = px.sha_of(px.APPX_B.encode())
        for tweak, code in ((dict(registry_seq=9, registry_sha256=sha), "SCAN-REGISTRY-MISMATCH"),
                            (dict(registry_seq=1, registry_sha256="sha256:" + "2" * 64),
                             "SCAN-REGISTRY-MISMATCH"),
                            (dict(registry_seq=99, registry_sha256=sha), "SCAN-REGISTRY-MISMATCH")):
            repo = px.repo(run_open=False, extra=[fx.run_open_ev(1), scan(**tweak)])
            it = self.check(repo)["_item"]["events.research"]
            self.assertIn(code, {f["code"] for f in it["findings"]}, tweak)
        ok = px.repo(run_open=False, extra=[fx.run_open_ev(1),
                                            scan(registry_seq=1, registry_sha256=sha)])
        self.assertNotIn("SCAN-REGISTRY-MISMATCH", json.dumps(self.check(ok)["_item"]))
        bad = scan(registry_seq=1, registry_sha256=sha)
        bad["sources"][0]["id"] = "nope"
        repo = px.repo(run_open=False, extra=[fx.run_open_ev(1), bad])
        it = self.check(repo)["_item"]["events.research"]
        self.assertIn("SRC-UNKNOWN", {f["code"] for f in it["findings"]})

    def test_AT_645_3_2_known_ids_are_used_by_both_call_sites(self):
        import inspect

        from lib.selfimproving import check as si_check
        from lib.selfimproving import fourqparse
        for mod in (si_check, fourqparse):
            src = inspect.getsource(mod).replace("si_registry", "registry")
            self.assertIn("registry.known_ids", src)
        repo = px.repo()
        old = {"schema_rev": 1, "sources": [
            {"id": "old-one", "url": "https://example.com/", "kind": "docs", "extract": "x",
             "added_by": "T1", "retired": True}]}
        fx.putb(repo, si_sources.SOURCES_REL, (json.dumps(old) + "\n").encode("utf-8"))
        ids = registry.known_ids(repo)
        self.assertGreaterEqual(ids, {"anthropic-engineering", "arxiv-agents", "old-one"})
        self.assertIsNone(registry.known_ids(fx.new_dir("empty")))


class TestPatrol(RgCase):
    """tools/lib/selfimproving/patrol.py 與 unattended.py（AC-SI-45-4）。"""

    def test_AT_645_4_1_ingest_argv_and_pending(self):
        ctx = types.SimpleNamespace(si=self.home)
        ref = px.new_ref()
        self.assertEqual(patrol._ingest_argv(ctx, "src-registry", ref),
                         ["registry-ingest", "--carrier", "console", "--audit-ref", ref,
                          "--by", "patrol"])
        repo = self.blank()
        px.write_audit(self.home, ref=ref)
        pend = status.console_pending([])
        self.assertEqual([i["kind"] for i in pend["items"]], ["src-registry"])
        argv = patrol._ingest_argv(ctx, "src-registry", ref)
        rc, out, err = self.M(repo, *argv)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(status.console_pending(
            si_events.load_sound_events(repo / fx.EVL))["count"], 0)

    def test_AT_645_4_E_1_registry_ingest_is_c_class(self):
        from lib.selfimproving import unattended
        self.assertIn("registry-ingest", unattended.C_CLASS)
        self.assertIn("backtest", unattended.C_CLASS)
        repo = self.blank()
        self.audit()
        with mock.patch.dict(os.environ, {"AUTOSDD_UNATTENDED": "1"}):
            rc, out, _ = self.ingest(repo)
        self.assertEqual((rc, fx.codes_of(out)), (1, {"UNATTENDED-REFUSED"}), out)
        self.assertEqual(self.ingest(repo)[0], 0)

    def test_AT_645_4_E_2_rejection_draft_is_logged_once(self):
        # 同 audit_ref＋同碼只記一次的規則由 patrol.ingest 的 `ctx.logged` 承擔（既有 AT-440-*）；
        # 本檔只驗新 kind 走同一條路：MAC 被改的稽核檔入帳被拒且檔案保留。
        repo = self.blank()
        self.audit(mac="0" * 64)
        for _ in range(2):
            rc, out, _ = self.ingest(repo)
            self.assertEqual((rc, fx.codes_of(out)), (1, {"AUDIT-MAC-MISMATCH"}))
        self.assertTrue((self.home / "console_audit" / f"{px.REF}.json").is_file())
        self.assertEqual(patrol.patrolrun.first_code(out, ""), "AUDIT-MAC-MISMATCH")


class TestDirty(unittest.TestCase):
    """tools/lib/selfimproving/sched.py 自有路徑（AC-SI-45-5）。"""

    def test_AT_645_5_1_own_paths_are_not_dirty(self):
        repo = fx.p1_base()
        for rel in (px.MIRROR_REL, "docs/06_quality/SelfImproving_Backtest/results.jsonl"):
            fx.putb(repo, rel, b"x\n")
        self.assertEqual(sched.dirty_paths(repo), [])
        fx.putb(repo, "tools/x.py", b"x = 1\n")
        self.assertEqual(sched.dirty_paths(repo), ["tools/x.py"])


class TestFrozenOldTable(RgCase):
    """research_sources.json 凍結（AC-SI-45-6）。"""

    def test_AT_645_6_1_old_table_is_frozen(self):
        raw = (ROOT / si_sources.SOURCES_REL).read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(len(raw), 5226)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "6201d066799e7f13c18053f3474f6883fddd8091baf0ab24e3a4b1c0d348e26f")

    def test_AT_645_6_2_active_paths_do_not_read_the_old_table(self):
        repo = px.repo()
        (repo / si_sources.SOURCES_REL).unlink(missing_ok=True)
        self.assertEqual(self.fetch(repo)[0], 0)
        fx.putb(repo, si_sources.SOURCES_REL, b"garbage")
        it = self.check(repo)["_item"]["research.sources"]
        self.assertIn("SRC-FILE-FORMAT", {f["code"] for f in it["findings"]})
        blank = self.blank()
        self.audit()
        fx.putb(blank, si_sources.SOURCES_REL, b"garbage")
        self.assertEqual(self.ingest(blank)[0], 0)

    def _old_scan_repo(self, *, sha=None):
        repo = fx.p1_base()
        entry = {"id": "a-typo", "url": "https://example.com/d", "kind": "docs", "extract": "x",
                 "added_by": "T1"}
        raw = (json.dumps({"schema_rev": 1, "sources": [entry]}, ensure_ascii=False, indent=2)
               + "\n").encode("utf-8")
        fx.putb(repo, si_sources.SOURCES_REL, raw)
        fx.commit_all(repo, "sources", when="2020-01-01T00:00:00+00:00")
        src = [{"id": "a-typo", "sha256": "sha256:" + "3" * 64, "bytes": 3, "changed": True,
                "http_status": 200}]
        fx.write_events(repo, [fx.run_open_ev(1), fx.ev(
            "research.scan", by="researcher", run=fx.rid(1), sources=src,
            sources_sha256=sha or si_sources.sha256_lf(raw), fetched_at=px.TIME)])
        return repo

    def test_AT_645_6_3_deleting_the_old_table_silences_history_checks(self):
        repo = self._old_scan_repo()
        it = self.check(repo)["_item"]["events.research"]
        self.assertEqual([f["code"] for f in it["findings"] if f["level"] == "fail"], [])
        subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=false", "rm", "-q", "-f",
                        si_sources.SOURCES_REL], check=True, encoding="utf-8",
                       env={**os.environ, **fx.hermetic()})
        codes = {f["code"] for f in self.check(repo)["_item"]["events.research"]["findings"]}
        self.assertIn("SOURCE-UNAVAILABLE", codes)
        self.assertNotIn("SOURCES-SHA-MISMATCH", codes)

    def test_AT_645_6_4_old_sha_is_still_checked_new_format_is_not(self):
        repo = self._old_scan_repo(sha="sha256:" + "9" * 64)
        codes = {f["code"] for f in self.check(repo)["_item"]["events.research"]["findings"]}
        self.assertIn("SOURCES-SHA-MISMATCH", codes)
        sha = px.sha_of(px.APPX_B.encode())
        new = px.repo(run_open=False, extra=[fx.run_open_ev(1), fx.ev(
            "research.scan", by="researcher", run=fx.rid(1), fetched_at=px.TIME,
            sources=[{"id": "arxiv-agents", "sha256": "sha256:" + "1" * 64, "bytes": 1,
                      "changed": True, "http_status": 200}], registry_seq=1, registry_sha256=sha)])
        codes = {f["code"] for f in self.check(new)["_item"]["events.research"]["findings"]}
        self.assertNotIn("SOURCES-SHA-MISMATCH", codes)


class TestEventSpec(unittest.TestCase):
    """tools/lib/selfimproving/evspec6.py 與 events.py（AC-SI-45-7）。"""

    def _backtest(self, **kw):
        base = {"seq": 2, "t": px.TIME, "kind": "backtest.result", "by": "main",
                "batch": "BT-001", "cases_version": 1, "cases_sha256": "sha256:" + "a" * 64,
                "seed": 7, "k": 5, "n": 5, "unanswered": 0, "contaminated": 0, "hit1": 1,
                "hit3": 2, "hit5": 3, "prec_pm": 300, "rec_pm": 400, "ledger_line": 1,
                "row_sha256": "sha256:" + "b" * 64}
        return {**base, **kw}

    def _scan(self, **kw):
        base = {"seq": 3, "t": px.TIME, "kind": "research.scan", "by": "researcher",
                "run": fx.rid(1), "fetched_at": px.TIME, "registry_seq": 1,
                "registry_sha256": "sha256:" + "c" * 64,
                "sources": [{"id": "a", "sha256": "sha256:" + "d" * 64, "bytes": 1,
                             "changed": True, "http_status": 200}]}
        return {**base, **kw}

    def _reg(self, **kw):
        return {**{"seq": 1, "t": px.TIME}, **px.reg_event(), **kw}

    def test_AT_645_7_1_vocabulary_and_valid_events(self):
        self.assertEqual(len(si_events.KINDS), 27)
        self.assertEqual(set(issuemap.EVENT_LABELS), set(si_events.KINDS))
        for ev in (self._reg(), self._backtest(), self._scan()):
            self.assertEqual(si_events.validate(ev), [], ev["kind"])
        self.assertTrue(hasattr(si_events, "KINDS") and hasattr(si_events, "valid_t"))

    def test_AT_645_7_E_1_invalid_variants(self):
        bad = [self._reg(watch_on=9), self._reg(carrier="x"), self._reg(audit_ref="zz"),
               self._reg(extra=1), {k: v for k, v in self._reg().items() if k != "audit_ref"},
               self._scan(sources_sha256="sha256:" + "e" * 64),
               {k: v for k, v in self._scan().items() if k not in ("registry_seq",
                                                                  "registry_sha256")},
               self._scan(articles_n=3),
               self._scan(articles_n=100, articles_sha256="sha256:" + "f" * 64),
               self._backtest(hit1=3, hit3=2), self._backtest(k=11), self._backtest(batch="B1"),
               self._backtest(seed=-1), self._backtest(prec_pm=1001)]
        for ev in bad:
            self.assertTrue(si_events.validate(ev), ev)
        self.assertEqual(si_events.sound(bad), [])
        self.assertEqual(evspec6.proof_backtest_codes("回測分數"), ["PROOF-BACKTEST"])

    def test_AT_645_7_2_worst_case_line_lengths(self):
        def size(o):
            return len(json.dumps(o, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        t25 = "2026-11-10T09:00:00+08:00"
        reg = {"seq": 12345, "t": t25, "kind": "research.registry", "by": "b" * 32,
               "audit_ref": px.REF, "audit_sha256": "sha256:" + "a" * 64, "key_id": "abcdef01",
               "decider": "d" * 64, "carrier": "console", "audit_time": t25,
               "registry_sha256": "sha256:" + "a" * 64, "hosts_n": 999, "watch_n": 999,
               "watch_on": 999, "changed": False}
        self.assertEqual(si_events.validate(reg), [])
        self.assertEqual(size(reg), 561)
        bt = self._backtest(seq=12345, t=t25, by="b" * 32, batch="BT-123456", cases_version=999,
                            seed=2147483647, k=10, n=10, unanswered=10, contaminated=10,
                            hit1=10, hit3=10, hit5=10, prec_pm=1000, rec_pm=1000,
                            ledger_line=123456)
        self.assertEqual(si_events.validate(bt), [])
        self.assertEqual(size(bt), 472)
        srcs = [{"id": "a" * 32, "sha256": "sha256:" + "d" * 64, "bytes": 524288,
                 "changed": False, "http_status": 200} for _ in range(10)]
        scan = self._scan(seq=12345, t=t25, run="RUN-SI-999", fetched_at=t25, registry_seq=12345,
                          sources=srcs, articles_n=30, articles_sha256="sha256:" + "f" * 64)
        self.assertEqual(si_events.validate(scan), [])
        self.assertEqual(size(scan), 2119)
        self.assertLessEqual(2119, 4096)
        with self.assertRaises(evwrite.Reject) as cm:
            evwrite._append_locked(Path(os.devnull), lambda s: {"kind": "run.close", "by": "main",
                                                                "run": fx.rid(1), "no_event": True},
                                   100)
        self.assertEqual(cm.exception.codes[0][0], "EVENT-BYTES-OVER")


class TestStatus(RgCase):
    """tools/lib/selfimproving/status.py（AC-SI-45-8）。"""

    def test_AT_645_8_1_registry_keys(self):
        repo = self.blank()
        rc, out, _ = self.M(repo, "status", "--json")
        obj = json.loads(out)
        self.assertEqual((obj["research_fetch_max"], obj["research_registry"]), (10, None))
        keys = list(obj)
        self.assertEqual(keys[17:19], ["research_fetch_max", "research_registry"])
        self.audit()
        self.ingest(repo)
        obj = json.loads(self.M(repo, "status", "--json")[1])
        ev = fx.EV(repo)[-1]
        self.assertEqual(obj["research_registry"], {
            "seq": ev["seq"], "audit_ref": ev["audit_ref"],
            "registry_sha256": ev["registry_sha256"], "watch_enabled": ev["watch_on"]})
        ref2 = px.new_ref()
        self.audit(ref=ref2, when="2026-11-10T10:00:00+08:00", text=px.mutate(
            lambda o: o["watch"][1].update(extract="新")))
        self.ingest(repo, ref2)
        self.assertEqual(json.loads(self.M(repo, "status", "--json")[1])[
            "research_registry"]["audit_ref"], ref2)
        text = self.M(repo, "status")[1]
        self.assertIn("research_fetch_max: 10", text)
        self.assertIn("research_registry: seq=", text)
        export = json.loads(self.M(repo, "export", "--kind", "status", "--json")[1])
        item = export["items"][0]
        self.assertEqual(item["research_fetch_max"], 10)
        self.assertEqual(item["research_registry"]["audit_ref"], ref2)

    def test_AT_645_8_E_1_invalid_cap_and_incomplete_event(self):
        repo = self.blank()
        p = repo / "docs/06_quality/SelfImproving_Protocol/params.json"
        obj = json.loads(p.read_text(encoding="utf-8"))
        for bad in (0, "10"):
            obj["research_fetch_max"] = bad
            p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            val = status.registry_value([], obj)
            self.assertIsNone(val["research_fetch_max"])
        ev = {"seq": 1, "t": px.TIME, **{k: v for k, v in px.reg_event().items()
                                          if k != "registry_sha256"}}
        self.assertEqual(si_events.sound([ev]), [])
        self.assertIsNone(status.registry_value(si_events.sound([ev]), {})["research_registry"])


class TestNoRegression(RgCase):
    """tools/lib/selfimproving/params.py 與 SOP 判準（AC-P6-090-2、090-3；RR 側）。"""

    def test_AT_690_2_1_params_json_is_untouched(self):
        raw = (ROOT / "docs/06_quality/SelfImproving_Protocol/params.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "594494910f77f029060aa1b0f79767f1f74927331a81a14a14dc24ca86398e9c")
        self.assertEqual(len(params.PARAM_SPECS), 44)
        self.assertEqual(params.CHECK_RULES_REV, 6)
        self.assertEqual(self.check(ROOT)["_item"]["params.globs"]["status"], "PASS")

    def test_AT_690_3_2_sop_criteria_pass_and_have_teeth(self):
        import _selfimproving_p5_fixtures as p5

        from lib.selfimproving import patrolbrief
        sop = (ROOT / "docs/05_development/SelfImproving_Operations_SOP.md").read_text(
            encoding="utf-8")
        self.assertEqual(patrolbrief.template_problems(sop), [])
        self.assertEqual(fx.sop_problems(sop), [])
        self.assertEqual(p5.sop_p5_problems(sop), [])
        sec = p5.section(sop, "研究者")
        self.assertIn("SOP-P5-RESEARCHER-CHANGED", p5.sop_p5_problems(
            sop.replace(sec, sec.replace("research_registry.json", "research_sources.json", 1))))
        i, j = sop.index("## 反事實回測"), sop.index("## 無人運轉任務書範本")
        head = "## 無人運轉任務書範本\n"
        rest = (sop[:i] + sop[j:]).replace(head, head + sop[i:j], 1)  # 新節落進範本節之內
        self.assertNotEqual(patrolbrief.template_of(rest), patrolbrief.template_of(sop))
        self.assertTrue(patrolbrief.template_problems(rest))


if __name__ == "__main__":
    unittest.main()
