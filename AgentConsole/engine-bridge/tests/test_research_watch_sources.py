"""研究來源單一化：Bridge 追蹤來源端點（TCS-ResearchRegistry AC-965-3；契約 §5A.2）。

AT-965-3-1～3-9、3-E-1。真 PG 夾具（CHECK 與守衛在 DB）：`BRIDGE_TEST_DSN` 未設＝TOOL-ABSENCE skip
（同其他研究 Bridge 測試，由 `research_pg_support` 決定）。追蹤來源列的 `slug` 一律 `t-` 前綴。
"""
from __future__ import annotations

import inspect
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from app.research import registry as registry_mod
from app.research.fetch import allowlist as fetch_allowlist
from app.research.registry import (
    REGISTRY_TEXT_MAX_BYTES,
    RegistryTooLarge,
    build_registry,
    check_watch_url,
)
from app.settings import Settings
from tests.research_pg_support import ThrowawayDb
from tests.research_registry_support import (
    ADMIN,
    HEAD,
    TOKEN,
    Rig,
    appendix_d_rows,
    build_rig,
    make_registry_db,
    watch_body,
)

SEED_HOSTS = ["code.claude.com", "developers.openai.com", "github.com", "www.anthropic.com"]
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


@pytest.fixture
def rdb() -> Iterator[ThrowawayDb]:
    db = make_registry_db(seed=True)
    try:
        yield db
    finally:
        db.drop()


@pytest.fixture
def rig(make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path,
        rdb: ThrowawayDb) -> Rig:
    return build_rig(make_bridge, settings, tmp_path, rdb)


def snapshot_rows(r: Rig) -> list[tuple[Any, ...]]:
    return r.rdb.q("SELECT * FROM console.research_watch_sources ORDER BY slug COLLATE \"C\"")


# ── AT-965-3-1 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_1_post_creates_one_row_and_one_audit_line_without_events(rig: Rig) -> None:
    events, rows = rig.rdb.count("research_events"), rig.rdb.count("research_watch_sources")
    audits = len(rig.audit_lines())
    resp = rig.post("/research/watch-sources", watch_body())
    assert resp.status_code == 201, resp.text
    got = resp.json()
    assert set(got) == {"slug", "url", "host", "kind", "extract", "layer", "expand", "enabled",
                        "host_allowed", "added_by", "added_at", "disabled_by", "disabled_at"}
    assert (got["slug"], got["host"], got["enabled"], got["host_allowed"]) == (
        "t-new-1", "www.anthropic.com", True, True)
    assert got["expand"] == {"mode": "links", "prefix": "/news/", "max": 2}
    assert got["added_by"] == ADMIN and TIME_RE.match(got["added_at"])
    assert got["disabled_by"] is None and got["disabled_at"] is None
    assert rig.rdb.count("research_watch_sources") == rows + 1
    assert rig.rdb.count("research_events") == events, "追蹤來源是全域資源：不寫 research_events"
    new = rig.audit_lines()[audits:]
    assert len(new) == 1
    assert (new[0]["verb"], new[0]["approver"], new[0]["result"]) == ("watch.add", ADMIN, "ok")
    assert TOKEN not in str(new)


# ── AT-965-3-2 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_2_the_six_input_rules_are_listed_at_once_and_nothing_is_written(
        rig: Rig) -> None:
    bad = watch_body("-Bad", url="http://x", kind="rss", extract="", layer="X",
                     expand={"mode": "links", "prefix": "a", "max": 9})
    resp = rig.post("/research/watch-sources", bad)
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    violations = resp.json()["violations"]
    assert all({"field", "rule", "message"} <= set(v) for v in violations)
    assert sorted(v["rule"] for v in violations) == sorted(
        ["invalid_slug", "invalid_url", "invalid_kind", "invalid_layer", "invalid_extract",
         "invalid_expand"]), "六個欄位各一筆、一次全列"
    cases = {
        "expand-missing-max": watch_body("t-c1", expand={"mode": "links", "prefix": "/a/"}),
        "expand-extra-key": watch_body("t-c2", expand={"mode": "links", "prefix": "/a/", "max": 1,
                                                       "extra": 1}),
        "extract-newline": watch_body("t-c3", extract="a\nb"),
        "slug-33": watch_body("a" * 33),
        "unknown-key": {**watch_body("t-c4"), "surprise": 1},
    }
    for label, body in cases.items():
        r = rig.post("/research/watch-sources", body)
        assert (r.status_code, r.json()["reason"]) == (422, "invalid_request"), label
    assert rig.rdb.count("research_watch_sources") == 17, "任何一案 DB 零新增"
    results = [e["result"] for e in rig.audit_lines()]
    assert results.count("rejected:invalid_request") == 6
    ok32 = rig.post("/research/watch-sources", watch_body("a" * 32))
    assert ok32.status_code == 201, "32 字元 slug 合法"


# ── AT-965-3-3 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_3_check_watch_url_equals_the_con_column_of_appendix_d() -> None:
    rows = appendix_d_rows()
    assert len(rows) == 42
    for url, si, con in rows:
        got = check_watch_url(url)
        assert (got is None) == con, f"{url!r}：CON={con} 但 check_watch_url 回 {got!r}"
        if not con:
            assert got == "invalid_url", url
        assert not (con and not si), f"{url!r}：Console 接受而 SI 拒絕（接受集合須 ⊆ SI）"
        assert check_watch_url(url) == got, "純函式：同輸入同輸出"
    assert len("https://x.example/") == 18
    assert check_watch_url("https://x.example/" + "a" * 483) == "invalid_url", "501 字元"
    assert check_watch_url("https://x.example/" + "a" * 482) is None, "500 字元"
    assert check_watch_url("https://example.org/a\x01b") == "invalid_url", "控制字元"
    assert check_watch_url(None) == "invalid_url"


# ── AT-965-3-4 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_4_a_host_must_be_in_the_effective_allowlist(rig: Rig) -> None:
    rig.add_host("blog.example.com", kind="WEB")
    off = rig.add_host("off.example.com")
    patched = rig.patch(f"/research/allowlist/{off['id']}",
                        {"enabled": False, "disabled_by": ADMIN})
    assert patched.status_code == 200
    hosts = ["export.arxiv.org", "www.anthropic.com", "blog.example.com", "off.example.com",
             "unknown.example.com"]
    got = []
    for i, host in enumerate(hosts):
        resp = rig.post("/research/watch-sources",
                        watch_body(f"t-h{i}", url=f"https://{host}/x", expand=None))
        got.append((resp.status_code, resp.json().get("reason"), resp.json()))
    assert [g[0] for g in got] == [201, 201, 201, 422, 422], got
    assert all(g[2]["host_allowed"] is True for g in got[:3])
    for status, reason, body in got[3:]:
        assert (status, reason) == (422, "host_not_allowed")
    assert [g[2]["details"]["host"] for g in got[3:]] == ["off.example.com", "unknown.example.com"]
    assert rig.rdb.count("research_watch_sources") == 17 + 3
    both = rig.post("/research/watch-sources", watch_body("t-both", url="https://unknown.example.com/x",
                                                          kind="rss"))
    assert both.json()["reason"] == "invalid_request", "同時違規只回 invalid_request"


# ── AT-965-3-5 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_5_a_slug_is_never_reused_and_there_is_no_delete(rig: Rig) -> None:
    again = rig.post("/research/watch-sources", watch_body("cc-releases"))
    assert (again.status_code, again.json()["reason"]) == (409, "watch_source_exists")
    assert again.json()["details"] == {"slug": "cc-releases"}
    assert rig.post("/research/watch-sources", watch_body("t-gone")).status_code == 201
    assert rig.patch("/research/watch-sources/t-gone",
                     {"enabled": False, "disabled_by": ADMIN}).status_code == 200
    reuse = rig.post("/research/watch-sources", watch_body("t-gone"))
    assert (reuse.status_code, reuse.json()["reason"]) == (409, "watch_source_exists")
    assert rig.rdb.count("research_watch_sources") == 18
    for method in ("DELETE", "PUT", "POST"):
        gone = rig.client.request(method, "/research/watch-sources/t-gone", headers=HEAD)
        assert gone.status_code == 405, f"{method} 應為 405（路由表只有 GET 以外的 PATCH）"
    assert rig.rdb.count("research_watch_sources") == 18


# ── AT-965-3-6 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_6_patch_only_takes_enabled_and_reenabling_clears_the_disable_fields(
        rig: Rig) -> None:
    events = rig.rdb.count("research_events")
    created = rig.post("/research/watch-sources", watch_body("t-a")).json()
    path = "/research/watch-sources/t-a"
    assert rig.patch(path, {"enabled": False}).status_code == 422, "停用須帶 disabled_by"
    off = rig.patch(path, {"enabled": False, "disabled_by": ADMIN})
    assert off.status_code == 200
    assert off.json()["enabled"] is False and off.json()["disabled_by"] == ADMIN
    assert TIME_RE.match(off.json()["disabled_at"])
    assert rig.patch(path, {"enabled": False, "url": "https://x"}).status_code == 422
    on = rig.patch(path, {"enabled": True})
    assert on.status_code == 200
    assert on.json() == created, "重新啟用：停用欄清空、其餘欄位與停用前逐值相同"
    rig.patch(path, {"enabled": False, "disabled_by": ADMIN})
    entry = next(e for e in rig.get("/research/allowlist").json()["items"]
                 if e["host"] == "www.anthropic.com" and e["source"] == "ADMIN")
    assert rig.patch(f"/research/allowlist/{entry['id']}",
                     {"enabled": False, "disabled_by": ADMIN}).status_code == 200
    blocked = rig.patch(path, {"enabled": True})
    assert (blocked.status_code, blocked.json()["reason"]) == (422, "host_not_allowed")
    missing = rig.patch("/research/watch-sources/t-nope", {"enabled": True})
    assert (missing.status_code, missing.json()["reason"]) == (404, "research_not_found")
    assert missing.json()["details"] == {"slug": "t-nope"}
    assert rig.patch("/research/watch-sources/Bad_Slug", {"enabled": True}).status_code == 404
    assert rig.rdb.count("research_events") == events


# ── AT-965-3-7 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_7_disabling_a_domain_leaves_the_rows_alone_and_flips_host_allowed(
        rig: Rig) -> None:
    for slug in ("t-a", "t-b", "t-c"):
        assert rig.post("/research/watch-sources", watch_body(slug)).status_code == 201
    entry = next(e for e in rig.get("/research/allowlist").json()["items"]
                 if e["host"] == "www.anthropic.com" and e["source"] == "ADMIN")
    before = snapshot_rows(rig)
    assert rig.patch(f"/research/allowlist/{entry['id']}",
                     {"enabled": False, "disabled_by": ADMIN}).status_code == 200
    items = {i["slug"]: i for i in rig.get("/research/watch-sources").json()["items"]}
    assert all(items[s]["enabled"] is True and items[s]["host_allowed"] is False
               for s in ("t-a", "t-b", "t-c"))
    assert snapshot_rows(rig) == before, "追蹤來源表零 UPDATE"
    assert rig.patch(f"/research/allowlist/{entry['id']}", {"enabled": True}).status_code == 200
    items = {i["slug"]: i for i in rig.get("/research/watch-sources").json()["items"]}
    assert all(items[s]["host_allowed"] is True for s in ("t-a", "t-b", "t-c"))
    assert snapshot_rows(rig) == before


# ── AT-965-3-8 ────────────────────────────────────────────────────────────────────────────────
def _row(slug: str, extract: str) -> dict[str, Any]:
    from datetime import UTC, datetime

    return {"slug": slug, "url": "https://export.arxiv.org/a", "kind": "blog", "extract": extract,
            "layer": "ACADEMIC", "expand_mode": None, "expand_prefix": None, "expand_max": None,
            "enabled": True, "added_by": ADMIN, "added_at": datetime.now(UTC),
            "disabled_by": None, "disabled_at": None}


def _insert(r: Rig, row: dict[str, Any]) -> None:
    r.rdb.exec(
        "INSERT INTO console.research_watch_sources (slug, url, kind, extract, layer, added_by) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        row["slug"], row["url"], row["kind"], row["extract"], row["layer"], row["added_by"])


def _size(r: Rig, extra: list[dict[str, Any]]) -> int:
    try:
        text, _sha = build_registry(r.settings.research_fetch_allowlist,
                                    r.settings.research_web_allowlist, r.db.list_allowlist(),
                                    [*r.db.list_watch_sources(), *extra])
    except RegistryTooLarge as exc:            # 超界時 builder 拋例外並帶實際位元組數
        return exc.size
    return len(text.encode("utf-8"))


def test_AT_965_3_8_the_size_gate_counts_bytes_and_rejects_before_writing(
        make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path) -> None:
    db = make_registry_db(seed=False)
    try:
        r = build_rig(make_bridge, settings, tmp_path, db)
        probe = _row("t-last", "x")
        gap = REGISTRY_TEXT_MAX_BYTES - _size(r, [probe])
        index = 0
        # 先以直寫 SQL 把表填到「候選列 extract 恰 1+gap 個 ASCII 字時快照恰為 24576 位元組」：
        # 一列（extract 1 字）使快照增加 `one` 位元組、extract 每多一個 ASCII 字多 1 位元組；
        # 候選列的 extract 可在 1～200 字之間吸收最後 0～199 位元組的餘量。
        while gap > 199:
            one = _size(r, [_row(f"t-f{index:03d}", "y"), probe]) - _size(r, [probe])
            if gap > one + 398:
                k = 200
                if gap - (one + 199) < one:           # 避免落進「剩餘量介於 199 與 one 之間」的死角
                    k = gap - 2 * one + 1
            else:
                assert gap >= one, f"夾具無法精準逼近上限（剩 {gap}、一列至少 {one}）"
                k = min(200, gap - one + 1)
            _insert(r, _row(f"t-f{index:03d}", "y" * k))
            index += 1
            gap = REGISTRY_TEXT_MAX_BYTES - _size(r, [probe])
        assert 0 <= gap <= 199, f"夾具未能逼近上限：{gap}"
        before = r.rdb.count("research_watch_sources")
        base = {"url": "https://export.arxiv.org/a", "expand": None, "layer": "ACADEMIC"}
        over = r.post("/research/watch-sources",
                      watch_body("t-last", extract="x" * (gap + 2), **base))
        assert over.status_code == 422 and over.json()["reason"] == "registry_too_large"
        assert over.json()["details"] == {"what": "registry_text", "limit": 24576, "size": 24577}
        wide = r.post("/research/watch-sources",
                      watch_body("t-last", extract="中" + "x" * gap, **base))
        assert wide.status_code == 422, "多位元組字元算位元組不算字元（1 字元＝3 位元組）"
        assert wide.json()["details"]["size"] == 24578
        assert r.rdb.count("research_watch_sources") == before, "被拒時 DB 零新增"
        fits = r.post("/research/watch-sources",
                      watch_body("t-last", extract="x" * (gap + 1), **base))
        assert fits.status_code == 201, fits.text
        text = r.get("/research/registry").json()["registry_text"]
        assert len(text.encode("utf-8")) == REGISTRY_TEXT_MAX_BYTES == 24576
    finally:
        db.drop()
    source = Path(registry_mod.__file__).read_text(encoding="utf-8")
    assert source.count("REGISTRY_TEXT_MAX_BYTES = ") == 1, "常數只在 registry.py 定義一處"


# ── AT-965-3-9 ────────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_9_the_list_is_in_byte_order_and_the_gates_are_the_documented_ones(
        rig: Rig, make_bridge: Callable[..., Any], settings: Settings, tmp_path: Path) -> None:
    for slug in ("aa", "a0", "a-b"):
        _insert(rig, _row(slug, "x"))
    items = rig.get("/research/watch-sources")
    assert items.status_code == 200
    slugs = [i["slug"] for i in items.json()["items"]]
    assert len(slugs) == 20 and slugs == sorted(slugs, key=lambda s: s.encode("utf-8"))
    assert slugs[:3] == ["a-b", "a0", "aa"], "COLLATE \"C\" 位元組序：- < 數字 < 字母"
    assert any(i["enabled"] is False for i in items.json()["items"]), "含停用列"
    # 無權杖可讀；寫入的權杖三態
    assert rig.client.get("/research/watch-sources").status_code == 200
    for label, headers in (("missing", None), ("wrong", {"X-Bridge-Token": TOKEN + "x"})):
        resp = rig.client.post("/research/watch-sources", json=watch_body("t-z"), headers=headers)
        assert (resp.status_code, resp.json()["reason"]) == (403, "research_write_forbidden"), label
    unset = build_rig(make_bridge, settings, tmp_path, rig.rdb, research_write_token=None)
    resp = unset.client.post("/research/watch-sources", json=watch_body("t-z"), headers=HEAD)
    assert (resp.status_code, resp.json()["reason"]) == (503, "research_write_disabled")
    nodsn = build_rig(make_bridge, settings, tmp_path, None)
    for method, path, body in (("GET", "/research/watch-sources", None),
                               ("POST", "/research/watch-sources", watch_body("t-z"))):
        resp = nodsn.client.request(method, path, json=body, headers=HEAD)
        assert (resp.status_code, resp.json()["reason"]) == (503, "research_requires_db")
    assert "dsn" not in str(items.json()).lower() and TOKEN not in str(items.json())


# ── AT-965-3-E-1 ──────────────────────────────────────────────────────────────────────────────
def test_AT_965_3_E_1_the_r2p_allowlist_endpoints_are_unchanged(rig: Rig) -> None:
    got = rig.get("/research/allowlist").json()
    assert set(got) == {"items", "effective"}
    assert got["effective"]["FETCH"] == [*rig.settings.research_fetch_allowlist, *SEED_HOSTS]
    assert got["effective"]["WEB"] == []
    added = rig.add_host("docs.example.com")
    assert set(added) == {"id", "list_kind", "host", "layer", "purpose", "tos_note",
                          "min_interval_seconds", "enabled", "tos_acknowledged", "added_by",
                          "added_at", "disabled_by", "disabled_at", "source"}
    off = rig.patch(f"/research/allowlist/{added['id']}", {"enabled": False, "disabled_by": ADMIN})
    assert off.status_code == 200 and off.json()["enabled"] is False
    assert str(inspect.signature(fetch_allowlist.check_research_url)) == (
        "(url: 'Any', allowlist: 'Iterable[str]', resolver: 'Resolver') -> 'UrlCheck'")
    assert str(inspect.signature(fetch_allowlist.build_effective_allowlist)) == (
        "(env_hosts: 'Iterable[str]', admin_entries: 'Iterable[Mapping[str, Any]]' = ()) -> "
        "'EffectiveAllowlist'")
