"""研究來源單一化：登記快照（TCS-ResearchRegistry AC-965-4；契約 §5A.3）。

AT-965-4-1～4-9、4-E-1、4-E-2。`RDB` 為真 PG：空登記（只建表與守衛、不跑種子 INSERT）與含種子兩種。
"""
from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from app.research import registry as registry_mod
from app.research.fetch.allowlist import build_effective_allowlist, is_public_ip
from app.research.registry import build_registry_hosts
from app.settings import Settings
from tests.research_pg_support import ThrowawayDb
from tests.research_registry_support import (
    ADMIN,
    Rig,
    build_rig,
    fixture_bytes,
    make_registry_db,
)

APP_DIR = Path(registry_mod.__file__).resolve().parents[1]
ROUTER = APP_DIR / "routers" / "research.py"


@pytest.fixture
def seeded() -> Iterator[ThrowawayDb]:
    db = make_registry_db(seed=True)
    try:
        yield db
    finally:
        db.drop()


@pytest.fixture
def empty() -> Iterator[ThrowawayDb]:
    db = make_registry_db(seed=False)
    try:
        yield db
    finally:
        db.drop()


def only_arxiv(make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
               db: ThrowawayDb) -> Rig:
    return build_rig(make_bridge, settings, tmp_path, db,
                     research_fetch_allowlist=("export.arxiv.org",), research_web_allowlist=())


def registry(r: Rig) -> dict[str, Any]:
    resp = r.get("/research/registry")
    assert resp.status_code == 200, resp.text
    return resp.json()


def sql_watch(db: ThrowawayDb, slug: str, url: str, *, added_at: str, extract: str = "摘要",
              kind: str = "blog", layer: str = "INDUSTRY",
              expand: tuple[str, str, int] | None = None,
              disabled: tuple[str, str] | None = None, added_by: str = "t:fixture") -> None:
    db.exec(
        "INSERT INTO console.research_watch_sources (slug, url, kind, extract, layer, "
        "expand_mode, expand_prefix, expand_max, enabled, added_by, added_at, disabled_by, "
        "disabled_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        slug, url, kind, extract, layer, *(expand or (None, None, None)),
        disabled is None, added_by, added_at, *(disabled or (None, None)))


# ── AT-965-4-1 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_1_golden_g_r1_is_byte_for_byte(make_bridge: Callable[..., Any],
                                                 settings: Settings, tmp_path: Path,
                                                 empty: ThrowawayDb) -> None:
    golden = fixture_bytes("golden-r1.json")
    got = registry(only_arxiv(make_bridge, settings, tmp_path, empty))
    assert got["registry_text"].encode("utf-8") == golden and len(golden) == 205
    assert got["registry_sha256"] == (
        "sha256:73123a2bf0275448928199a72895297c77d6af8773ffa14b7cf453d19dc393a3")


# ── AT-965-4-2 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_2_the_snapshot_is_deterministic_and_independent_of_insert_order(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path) -> None:
    rows = [("t-a", "https://www.anthropic.com/a", "2026-11-10T01:00:00+00:00"),
            ("t-b", "https://www.anthropic.com/b", "2026-11-10T02:00:00+00:00"),
            ("t-c", "https://www.anthropic.com/c", "2026-11-10T03:00:00+00:00")]
    hosts = [("www.anthropic.com", "INDUSTRY", 5), ("docs.example.com", "OSS", 7)]
    texts = []
    for order in (1, -1):
        db = make_registry_db(seed=False)
        try:
            for host, layer, interval in hosts[::order]:
                db.exec("INSERT INTO console.research_allowlist_entries (list_kind, host, layer, "
                        "min_interval_seconds, added_by) VALUES ('FETCH', %s, %s, %s, 't:fix')",
                        host, layer, interval)
            for slug, url, at in rows[::order]:
                sql_watch(db, slug, url, added_at=at)
            r = only_arxiv(make_bridge, settings, tmp_path, db)
            first = registry(r)
            assert all(registry(r) == first for _ in range(20)), "連呼 20 次零差異"
            texts.append(first)
        finally:
            db.drop()
    assert texts[0] == texts[1], "兩種插入順序：registry_text 與 registry_sha256 皆相同"


# ── AT-965-4-3 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_3_hosts_are_enabled_only_deduped_env_first_and_byte_ordered() -> None:
    def row(kind: str, host: str, *, enabled: bool = True, layer: str = "OSS",
            interval: int = 3) -> dict[str, Any]:
        return {"list_kind": kind, "host": host, "layer": layer, "enabled": enabled,
                "min_interval_seconds": interval}

    got = build_registry_hosts(
        ["export.arxiv.org"], ["wiki.example"],
        [row("FETCH", "export.arxiv.org", layer="ACADEMIC"), row("FETCH", "off.example",
                                                                 enabled=False),
         row("FETCH", "both.example"), row("WEB", "both.example", layer="COMMUNITY"),
         row("FETCH", "a-b.com"), row("FETCH", "a.com"), row("FETCH", "a0.com"),
         row("FETCH", "B.com")])
    keys = [(e["host"], e["list_kind"]) for e in got]
    assert ("off.example", "FETCH") not in keys, "停用條目不列"
    assert keys.count(("export.arxiv.org", "FETCH")) == 1
    arxiv = next(e for e in got if e["host"] == "export.arxiv.org")
    assert (arxiv["source"], arxiv["layer"]) == ("ENV", None)
    assert [k for k in keys if k[0] == "both.example"] == [("both.example", "FETCH"),
                                                          ("both.example", "WEB")]
    assert keys == sorted(keys, key=lambda k: (k[0].encode(), k[1].encode()))
    host_order = [h for h, _k in keys if h in {"a-b.com", "a.com", "a0.com", "b.com"}]
    assert host_order == ["a-b.com", "a.com", "a0.com", "b.com"], "- < . < 數字 < 字母；host 小寫"
    assert next(e for e in got if e["host"] == "a.com")["layer"] == "OSS"


# ── AT-965-4-4 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_4_min_interval_is_max_of_the_builtin_floor_and_the_entry() -> None:
    def adm(kind: str, host: str, interval: int) -> dict[str, Any]:
        return {"list_kind": kind, "host": host, "layer": "INDUSTRY", "enabled": True,
                "min_interval_seconds": interval}

    env = ["api.github.com", "export.arxiv.org", "x.example"]
    got = {(e["host"], e["list_kind"]): e["min_interval_seconds"]
           for e in build_registry_hosts(env, [], [
               adm("FETCH", "www.anthropic.com", 5), adm("FETCH", "low.example", 1),
               adm("FETCH", "slow.example", 3600), adm("FETCH", "both.example", 7),
               adm("WEB", "both.example", 2)])}
    assert got[("api.github.com", "FETCH")] == 60
    assert got[("export.arxiv.org", "FETCH")] == 3
    assert got[("x.example", "FETCH")] == 3
    assert got[("www.anthropic.com", "FETCH")] == 5
    assert got[("low.example", "FETCH")] == 3, "低於內建下限取下限"
    assert got[("slow.example", "FETCH")] == 3600
    assert (got[("both.example", "FETCH")], got[("both.example", "WEB")]) == (7, 3)
    effective = build_effective_allowlist(env, [
        adm("FETCH", "www.anthropic.com", 5), adm("FETCH", "low.example", 1),
        adm("FETCH", "slow.example", 3600), adm("FETCH", "both.example", 7)])
    for (host, kind), value in got.items():
        if kind == "FETCH":
            assert effective.interval(host) == value, f"{host}：須等於 EffectiveAllowlist.interval"


# ── AT-965-4-5 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_5_watch_lists_every_row_with_normalized_times_and_expand_shape(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        empty: ThrowawayDb) -> None:
    base = "https://export.arxiv.org/"
    sql_watch(empty, "t-expand", base + "e", added_at="2026-11-10T01:02:03.123456+00:00",
              expand=("links", "/x/", 2))
    sql_watch(empty, "t-off", base + "o", added_at="2026-11-10T09:00:00+08:00",
              disabled=("t:fix", "2026-11-10T10:00:00.9+08:00"))
    sql_watch(empty, "t-plain", base + "p", added_at="2026-11-10T00:00:00+00:00")
    sql_watch(empty, "t-back", base + "b", added_at="2026-11-10T00:00:00+00:00",
              disabled=("t:fix", "2026-11-10T01:00:00+00:00"))
    empty.exec("UPDATE console.research_watch_sources SET enabled = TRUE, disabled_by = NULL, "
               "disabled_at = NULL WHERE slug = 't-back'")
    snap = registry(only_arxiv(make_bridge, settings, tmp_path, empty))
    parsed = json.loads(snap["registry_text"])
    watch = parsed["watch"]
    assert [w["id"] for w in watch] == ["t-back", "t-expand", "t-off", "t-plain"]
    assert all(len(w) == 11 for w in watch)
    by_id = {w["id"]: w for w in watch}
    assert by_id["t-expand"]["expand"] == {"max": 2, "mode": "links", "prefix": "/x/"}
    assert by_id["t-plain"]["expand"] is None
    assert by_id["t-expand"]["added_at"] == "2026-11-10T01:02:03+00:00", "微秒截斷"
    assert by_id["t-off"]["added_at"] == "2026-11-10T01:00:00+00:00", "+08:00 換算成 UTC"
    assert by_id["t-off"]["disabled_at"] == "2026-11-10T02:00:00+00:00"
    assert by_id["t-off"]["enabled"] is False and by_id["t-plain"]["enabled"] is True
    plain, back = dict(by_id["t-plain"]), dict(by_id["t-back"])
    for key in ("id", "url"):
        plain.pop(key), back.pop(key)
    assert plain == back, "重新啟用列與從未停用的同形列內容一致"
    assert back["disabled_by"] is None and back["disabled_at"] is None


# ── AT-965-4-6 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_6_domain_and_source_toggles_round_trip_the_digest(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        seeded: ThrowawayDb) -> None:
    r = build_rig(make_bridge, settings, tmp_path, seeded)
    d0 = registry(r)
    entry = next(e for e in r.get("/research/allowlist").json()["items"]
                 if e["host"] == "github.com" and e["source"] == "ADMIN")
    path = f"/research/allowlist/{entry['id']}"
    assert r.patch(path, {"enabled": False, "disabled_by": ADMIN}).status_code == 200
    d1 = registry(r)
    hosts0 = {h["host"] for h in json.loads(d0["registry_text"])["hosts"]}
    hosts1 = {h["host"] for h in json.loads(d1["registry_text"])["hosts"]}
    assert hosts0 - hosts1 == {"github.com"}
    assert json.loads(d0["registry_text"])["watch"] == json.loads(d1["registry_text"])["watch"]
    assert r.patch(path, {"enabled": True}).status_code == 200
    d2 = registry(r)
    assert d2 == d0
    assert r.patch("/research/watch-sources/cc-releases",
                   {"enabled": False, "disabled_by": ADMIN}).status_code == 200
    d3 = registry(r)
    row = next(w for w in json.loads(d3["registry_text"])["watch"] if w["id"] == "cc-releases")
    assert row["enabled"] is False and d3 != d0
    assert r.patch("/research/watch-sources/cc-releases", {"enabled": True}).status_code == 200
    d4 = registry(r)
    assert d4 == d0, "重新啟用清空停用欄：快照回到原內容"
    assert len({d0["registry_sha256"], d1["registry_sha256"], d3["registry_sha256"]}) == 3


# ── AT-965-4-7 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_7_sha_formula_and_byte_hygiene(make_bridge: Callable[..., Any],
                                                 settings: Settings, tmp_path: Path,
                                                 seeded: ThrowawayDb) -> None:
    got = registry(build_rig(make_bridge, settings, tmp_path, seeded))
    assert set(got) == {"registry_text", "registry_sha256"}
    text = got["registry_text"]
    raw = text.encode("utf-8")
    assert got["registry_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert text.endswith("}\n") and not text.endswith("\n\n")
    assert "\r" not in text and not text.startswith("﻿")
    assert "最新 3 篇研究文章的全文（逐字）" in text and "\\u" not in text, "非 ASCII 原樣、不跳脫"
    assert set(json.loads(text)) == {"schema_rev", "hosts", "watch"}


# ── AT-965-4-8 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_8_too_large_is_422_without_partial_content_and_no_dsn_is_503(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        seeded: ThrowawayDb, monkeypatch: pytest.MonkeyPatch) -> None:
    r = build_rig(make_bridge, settings, tmp_path, seeded)
    monkeypatch.setattr(registry_mod, "REGISTRY_TEXT_MAX_BYTES", 100)
    resp = r.get("/research/registry")
    assert (resp.status_code, resp.json()["reason"]) == (422, "registry_too_large")
    details = resp.json()["details"]
    assert details["what"] == "registry_text" and details["limit"] == 100 and details["size"] > 100
    assert "registry_text" not in {k for k in resp.json() if k != "details"}
    nodsn = build_rig(make_bridge, settings, tmp_path, None)
    off = nodsn.get("/research/registry")
    assert (off.status_code, off.json()["reason"]) == (503, "research_requires_db")


# ── AT-965-4-9 ────────────────────────────────────────────────────────────────────────────────
FORBIDDEN_CALLS = {"datetime.now", "datetime.utcnow", "time.time", "time.monotonic", "uuid.uuid1",
                   "uuid.uuid4", "utc_now", "random.random", "random.randint", "random.choice"}


def dotted(node: ast.expr) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def clock_hits(tree: ast.AST) -> list[str]:
    return [dotted(n.func) for n in ast.walk(tree)
            if isinstance(n, ast.Call) and dotted(n.func) in FORBIDDEN_CALLS]


def test_AT_965_4_9_the_snapshot_path_never_reads_a_clock() -> None:
    registry_tree = ast.parse(Path(registry_mod.__file__).read_text(encoding="utf-8"))
    router_tree = ast.parse(ROUTER.read_text(encoding="utf-8"))
    handler = next(n for n in ast.walk(router_tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "get_registry")
    functions = [n for n in ast.walk(registry_tree) if isinstance(n, ast.FunctionDef)]
    assert len(functions) >= 5, "掃描範圍非空"
    assert clock_hits(registry_tree) == []
    assert clock_hits(handler) == []
    sample = ast.parse("def f():\n    return datetime.now()\n")
    assert clock_hits(sample) == ["datetime.now"], "負控：掃描器抓得到時鐘呼叫"


# ── AT-965-4-E-1 ──────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_E_1_is_public_ip_matches_appendix_a_row_by_row() -> None:
    raw = fixture_bytes("appendix-a.txt")
    text = raw.decode("utf-8")
    assert text.endswith("\n")
    lines = text.split("\n")[:-1]
    assert len(lines) == 34
    assert sum(1 for ln in lines if ln.endswith("\tT")) == 6
    assert sum(1 for ln in lines if ln.endswith("\tF")) == 28
    assert "\tF" in lines, "含空字串位址列"
    for line in lines:
        address, flag = line.rsplit("\t", 1)
        assert is_public_ip(address) is (flag == "T"), f"{address!r} 應為 {flag}"


# ── AT-965-4-E-2 ──────────────────────────────────────────────────────────────────────────────
def test_AT_965_4_E_2_appendix_b_rows_produce_the_appendix_b_bytes(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        empty: ThrowawayDb) -> None:
    raw = fixture_bytes("appendix-b.json")
    golden = json.loads(raw.decode("utf-8"))
    admin = next(h for h in golden["hosts"] if h["source"] == "ADMIN")
    empty.exec("INSERT INTO console.research_allowlist_entries (list_kind, host, layer, "
               "min_interval_seconds, added_by) VALUES (%s, %s, %s, %s, 't:fix')",
               admin["list_kind"], admin["host"], admin["layer"], admin["min_interval_seconds"])
    for w in golden["watch"]:
        expand = (w["expand"]["mode"], w["expand"]["prefix"], w["expand"]["max"]) \
            if w["expand"] else None
        disabled = (w["disabled_by"], w["disabled_at"]) if not w["enabled"] else None
        sql_watch(empty, w["id"], w["url"], added_at=w["added_at"], extract=w["extract"],
                  kind=w["kind"], layer=w["layer"], expand=expand, disabled=disabled,
                  added_by=w["added_by"])
    got = registry(only_arxiv(make_bridge, settings, tmp_path, empty))
    assert got["registry_text"].encode("utf-8") == raw and len(raw) == 2039
    assert got["registry_sha256"] == (
        "sha256:147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8")
    added_by = {w["id"]: w["added_by"] for w in golden["watch"]}
    assert added_by == {
        "anthropic-engineering": "migration:V24（SI research_sources.json 匯入）",
        "anthropic-research": "migration:V24（研究來源單一化種子）",
        "arxiv-agents": "migration:V24（研究來源單一化種子）"}
