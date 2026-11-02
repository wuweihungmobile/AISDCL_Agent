"""抓取器的四個解析器與請求網址（TCS AT-960-8-6；PRD AC-R2P-04-6）。

黃金夾具（`tests/fixtures/research/fetch/`）：arXiv Atom、Semantic Scholar JSON、GitHub repo JSON、
Stack Exchange JSON 各有黃金回應、缺欄版、壞格式版；黃金輸出（`*.expected.json`）是人讀過、手寫的
期望值，不是拿解析器自己的輸出回灌。解析器輸出的是「觀測形態」的 `research_sources` 列：缺欄寫
`未見`（不是空字串、也不省略），壞格式＝`PARSE_ERROR` 且不產生任何來源列。
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable, Iterator
from dataclasses import replace as clone
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from app.research.db import ResearchDb
from app.research.fetch import (
    MISSING,
    arxiv,
    check_research_url,
    github,
    land_raw,
    semantic_scholar,
    stackexchange,
    task_for,
    to_db_source_row,
)
from app.research.fetch.allowlist import ENV_MIN_INTERVALS
from app.research.fetch.http import SOURCE_COLUMNS, ParseResult
from tests.research_net_support import (
    FakeResolver,
    forbid_external_network,
    make_rig,
    text_reply,
)
from tests.research_pg_support import ThrowawayDb, make_research_db

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "research" / "fetch"
NOW = datetime(2026, 11, 2, tzinfo=UTC)
ALICE = "alice@example.com"


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    forbid_external_network(monkeypatch)


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def expected(name: str) -> list[dict[str, Any]]:
    return json.loads(fixture_text(name))


def github_parse(text: str) -> ParseResult:
    heads = {"example-org/example-lib": fixture_text("github_head_golden.json")}
    return github.parse(text, heads=heads, now=NOW)


def github_parse_without_heads(text: str) -> ParseResult:
    return github.parse(text, now=NOW)


#: 來源 → (解析函式, 黃金、缺欄、壞格式三份夾具的檔名)
SOURCES: dict[str, tuple[Callable[[str], ParseResult], tuple[str, str, str]]] = {
    "arxiv": (arxiv.parse, ("arxiv_golden", "arxiv_missing", "arxiv_malformed")),
    "semantic_scholar": (semantic_scholar.parse, (
        "semantic_scholar_golden", "semantic_scholar_missing", "semantic_scholar_malformed")),
    "github": (github_parse, ("github_golden", "github_missing", "github_malformed")),
    "stackexchange": (stackexchange.parse, (
        "stackexchange_golden", "stackexchange_missing", "stackexchange_malformed")),
}
EXTENSION = {"arxiv": "xml"}


def paths(source: str) -> tuple[str, str, str]:
    ext = EXTENSION.get(source, "json")
    return tuple(f"{stem}.{ext}" for stem in SOURCES[source][1])  # type: ignore[return-value]


# ══ AT-960-8-6：黃金、缺欄、壞格式 ═══════════════════════════════════════════════════════════════
@pytest.mark.parametrize("source", list(SOURCES))
def test_AT_960_8_6_the_golden_response_matches_the_golden_json_field_by_field(
        source: str) -> None:
    parse, (golden, _missing, _bad) = SOURCES[source][0], SOURCES[source][1]
    result = parse(fixture_text(paths(source)[0]))
    assert result.ok and result.detail == ""
    assert list(result.sources) == expected(f"{golden}.expected.json"), source
    for row in result.sources:
        assert [k for k in row if k in SOURCE_COLUMNS] == list(SOURCE_COLUMNS), \
            "輸出列含 research_sources 的全部描述欄、順序固定"


@pytest.mark.parametrize("source", list(SOURCES))
def test_AT_960_8_6_missing_fields_read_as_unseen_not_empty_and_not_omitted(source: str) -> None:
    parse, (_golden, missing, _bad) = SOURCES[source][0], SOURCES[source][1]
    result = parse(fixture_text(paths(source)[1]))
    assert result.ok and result.sources, source
    assert list(result.sources) == expected(f"{missing}.expected.json"), source
    for row in result.sources:
        assert set(SOURCE_COLUMNS) <= set(row), f"{source}：缺欄不得省略"
        assert [k for k, v in row.items() if v == ""] == [], f"{source}：缺欄不得是空字串"
        assert MISSING in row.values(), f"{source}：缺欄夾具必須真的有『未見』的欄位"
    assert result.detail, f"{source}：略過的項目要在 detail 說明"


@pytest.mark.parametrize("source", list(SOURCES))
def test_AT_960_8_6_a_malformed_response_is_a_parse_error_and_yields_no_source_rows(
        source: str) -> None:
    parse = SOURCES[source][0]
    result = parse(fixture_text(paths(source)[2]))
    assert (result.ok, result.sources) == (False, ())
    assert result.detail, "PARSE_ERROR 要說明原因"


MALFORMED_INLINE: list[tuple[str, Callable[[str], ParseResult], str]] = [
    ("arxiv：空字串", arxiv.parse, ""),
    ("arxiv：根元素不是 feed", arxiv.parse, "<html><body>503</body></html>"),
    ("arxiv：含 DTD", arxiv.parse, '<!DOCTYPE feed [<!ENTITY x "y">]><feed xmlns='
                                  '"http://www.w3.org/2005/Atom"/>'),
    ("arxiv：含實體宣告", arxiv.parse, '<feed xmlns="http://www.w3.org/2005/Atom">'
                                     '<!ENTITY lol "lol"></feed>'),
    ("arxiv：API 以 entry 回報錯誤", arxiv.parse, (
        '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#x'
        '</id><title>Error</title><summary>incorrect id format</summary></entry></feed>')),
    ("semantic_scholar：空字串", semantic_scholar.parse, ""),
    ("semantic_scholar：沒有 data", semantic_scholar.parse, '{"total": 0}'),
    ("semantic_scholar：data 不是陣列", semantic_scholar.parse, '{"data": "oops"}'),
    ("semantic_scholar：頂層是陣列", semantic_scholar.parse, "[]"),
    ("github：空字串", github.parse, ""),
    ("github：頂層是陣列", github.parse, "[]"),
    ("github：items 不是陣列", github.parse, '{"items": "x"}'),
    ("github：既非搜尋回應也非 repo", github.parse, '{"message": "Bad credentials"}'),
    ("stackexchange：空字串", stackexchange.parse, ""),
    ("stackexchange：沒有 items", stackexchange.parse, '{"error_id": 502}'),
    ("stackexchange：items 不是陣列", stackexchange.parse, '{"items": 5}'),
]


@pytest.mark.parametrize(("label", "parse", "text"), [
    pytest.param(label, parse, text, id=label) for label, parse, text in MALFORMED_INLINE])
def test_AT_960_8_6_each_malformed_shape_is_a_parse_error(
        label: str, parse: Callable[[str], ParseResult], text: str) -> None:
    result = parse(text)
    assert (result.ok, result.sources) == (False, ()), label
    assert result.detail, label


def test_AT_960_8_6_a_valid_response_with_zero_results_is_not_an_error() -> None:
    empty_atom = '<feed xmlns="http://www.w3.org/2005/Atom"><title>none</title></feed>'
    for parse, text in ((arxiv.parse, empty_atom), (semantic_scholar.parse, '{"data": []}'),
                        (github.parse, '{"items": []}'), (stackexchange.parse, '{"items": []}')):
        result = parse(text)
        assert (result.ok, result.sources, result.detail) == (True, (), "")


def test_AT_960_8_6_a_single_repo_object_parses_like_one_search_item() -> None:
    item = json.loads(fixture_text("github_golden.json"))["items"][0]
    single = github.parse(json.dumps(item), now=NOW)
    in_search = github.parse(fixture_text("github_golden.json"), now=NOW)
    assert single.ok and list(single.sources) == [in_search.sources[0]]


# ── 開源層的四個欄位與可參數化的門檻 ───────────────────────────────────────────────────────────
def test_AT_960_8_6_every_oss_row_carries_stars_push_time_license_and_the_head_commit() -> None:
    rows = github_parse(fixture_text("github_golden.json")).sources
    for row in rows:
        assert {"stars", "pushed_at", "license_spdx", "default_branch", "git_commit"} <= set(row)
    lib, old = rows
    assert (lib["stars"], lib["pushed_at"], lib["license_spdx"]) == (
        1234, "2026-10-20T08:30:00Z", "Apache-2.0")
    assert lib["git_commit"] == "0123456789abcdef0123456789abcdef01234567"
    assert (lib["anchor_kind"], lib["verification"]) == ("COMMIT", "V3"), "commit sha 是定位符之一"
    assert old["license_spdx"] == MISSING and old["git_commit"] == MISSING, "取不到＝未見"
    assert (old["anchor_kind"], old["verification"]) == ("URL", "V2")


def test_AT_960_8_6_the_star_and_activity_thresholds_are_parameters_with_documented_defaults(
) -> None:
    assert (github.GITHUB_MIN_STARS, github.GITHUB_ACTIVE_DAYS) == (50, 365), \
        "初值（未校準）；改初值要改這裡與 PRD"
    text = fixture_text("github_golden.json")
    default = [r["qualifies"] for r in github.parse(text, now=NOW).sources]
    assert default == [True, False]
    strict = github.parse(text, now=NOW, min_stars=5000).sources
    assert [r["qualifies"] for r in strict] == [False, False], "星數門檻可調"
    lax = github.parse(text, now=NOW, min_stars=1, active_days=10_000).sources
    assert [r["qualifies"] for r in lax] == [True, False], "封存的 repo 不論門檻都不算活躍"
    stale = github.parse(text, now=datetime(2028, 1, 1, tzinfo=UTC)).sources
    assert [r["qualifies"] for r in stale] == [False, False], "活躍天數以 now 為準"


@pytest.mark.parametrize(("payload", "sha"), [
    (fixture_text("github_head_golden.json"), "0123456789abcdef0123456789abcdef01234567"),
    ('{"commit": {"sha": "ABCDEF0123456789ABCDEF0123456789ABCDEF01"}}', None),
    ('{"commit": {"sha": "short"}}', None), ('{"commit": null}', None), ("[]", None),
    ("not json", None), ("", None)])
def test_AT_960_8_6_head_commit_must_be_a_40_char_lowercase_hex(
        payload: str, sha: str | None) -> None:
    assert github.parse_head(payload) == sha


# ── 原文 sha256 與位元組數、落地檔 ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("source", list(SOURCES))
def test_AT_960_8_6_raw_sha256_and_byte_count_equal_the_fetch_record_and_the_landed_file(
        source: str, tmp_path: Path) -> None:
    name = paths(source)[0]
    body = (FIXTURES / name).read_bytes()
    host = {"arxiv": "export.arxiv.org", "semantic_scholar": "api.semanticscholar.org",
            "github": "api.github.com", "stackexchange": "api.stackexchange.com"}[source]
    ctype = "application/atom+xml" if source == "arxiv" else "application/json"
    rig = make_rig(lambda call: text_reply(body, ctype))
    result = rig.client.fetch(f"https://{host}/x", layer="ACADEMIC")
    record = result.terminal
    assert result.ok and record.outcome == "OK"
    assert (record.raw_sha256, record.raw_bytes) == (hashlib.sha256(body).hexdigest(), len(body))
    assert record.to_db()["raw_sha256"] == record.raw_sha256
    landed = land_raw(tmp_path, record)
    assert landed is not None and landed.rel == record.raw_rel_path
    assert record.raw_rel_path == f"00_research/raw/{record.raw_sha256[:12]}.txt"
    on_disk = (tmp_path / record.raw_rel_path).read_bytes()
    assert (hashlib.sha256(on_disk).hexdigest(), len(on_disk)) == (record.raw_sha256,
                                                                   record.raw_bytes)
    again = land_raw(tmp_path, record)
    assert again is not None and again.written is False, "內容以雜湊定址：已存在就不重寫"
    assert land_raw(tmp_path, clone(record, raw_text=None, raw_sha256=None)) is None


# ── 輸出形狀＝research_sources 的真實 CHECK（DB；無 DSN＝TOOL-ABSENCE 跳過）─────────────────────
@pytest.fixture
def rdb() -> Iterator[ThrowawayDb]:
    db = make_research_db()
    try:
        yield db
    finally:
        db.drop()


def test_AT_960_8_6_every_parsed_row_is_insertable_under_the_research_sources_checks(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    store = ResearchDb(rdb.dsn)
    rid = str(uuid.uuid4())
    store.create_project(
        research_id=rid, slug="parsers", title="t", topic="t", workspace_path=str(tmp_path),
        fsm_project="research-parsers", fsm_state_dir=str(tmp_path / "fsm"), created_by=ALICE)
    seen = 0
    for source in SOURCES:
        for name in paths(source)[:2]:
            for row in SOURCES[source][0](fixture_text(name)).sources:
                db_row = to_db_source_row(row)
                if db_row["published_at"] is not None:
                    db_row["published_at"] = date.fromisoformat(db_row["published_at"])
                seen += 1
                store.insert_source(research_id=rid, actor=ALICE, source={
                    **db_row, "source_no": f"S-{seen:03d}", "source_type": row["source_type"]})
    assert seen == 12 and rdb.count("research_sources", "research_id = %s", rid) == seen
    kinds = rdb.q("SELECT anchor_kind, count(*) FROM console.research_sources "
                  "GROUP BY 1 ORDER BY 1")
    assert [k for k, _n in kinds] == ["COMMIT", "DOI", "URL"]
    t3 = rdb.q("SELECT bool_and(clue_only) FROM console.research_sources WHERE tier = 'T3'")
    assert t3 == [(True,)], "Stack Exchange 一律 T3 線索"


def test_AT_960_8_6_nullable_columns_turn_unseen_into_null_and_text_columns_keep_it() -> None:
    row = to_db_source_row(arxiv.parse(fixture_text("arxiv_missing.xml")).sources[0])
    assert (row["doi"], row["published_at"], row["license_spdx"], row["git_commit"]) == (
        None, None, None, None)
    assert (row["title"], row["authors_org"], row["license_note"]) == (MISSING,) * 3
    assert set(row) == set(SOURCE_COLUMNS), "只留可入庫的欄位（附加欄不入庫）"


# ══ 請求網址 ═══════════════════════════════════════════════════════════════════════════════════
ALL_HOSTS = tuple(ENV_MIN_INTERVALS)
BUILDERS: dict[str, Callable[[str], str]] = {
    "arxiv": lambda q: arxiv.search_url(q, max_results=7),
    "semantic_scholar": lambda q: semantic_scholar.search_url(q, limit=7),
    "github": lambda q: github.search_url(q, per_page=7),
    "stackexchange": lambda q: stackexchange.search_url(q, pagesize=7),
}


@pytest.mark.parametrize("kind", list(BUILDERS))
def test_AT_960_8_6_every_search_url_passes_the_research_url_gate(kind: str) -> None:
    url = BUILDERS[kind]("garbage collection persistent-memory")
    check = check_research_url(url, ALL_HOSTS, FakeResolver())
    assert check.ok, (kind, url, check)
    assert "7" in url.split("?", 1)[1]
    assert task_for(kind, "garbage collection", limit=7).url.startswith("https://")


@pytest.mark.parametrize("kind", list(BUILDERS))
def test_AT_960_8_6_a_query_without_an_ascii_word_is_refused(kind: str) -> None:
    for query in ("", "   ", "記憶體回收", "!!! ??? ;;;"):
        with pytest.raises(ValueError):
            BUILDERS[kind](query)


def test_AT_960_8_6_arxiv_queries_cannot_smuggle_query_syntax_in() -> None:
    url = arxiv.search_url('x ANDNOT y" OR all:evil; ti:z (a)', max_results=3)
    params = parse_qs(urlsplit(url).query)
    assert params["search_query"], url
    terms = params["search_query"][0].split(" AND ")
    assert terms and all(re.fullmatch(r"all:[A-Za-z0-9-]+", t) for t in terms), terms
    assert {k: v for k, v in params.items() if k != "search_query"} == {
        "start": ["0"], "max_results": ["3"], "sortBy": ["relevance"],
        "sortOrder": ["descending"]}


def test_AT_960_8_6_html_and_head_urls_only_accept_well_formed_identifiers() -> None:
    assert arxiv.html_url("2401.00001v2") == "https://arxiv.org/html/2401.00001v2"
    assert arxiv.html_url("cs/0112017v1") == "https://arxiv.org/html/cs/0112017v1"
    for bad in ("", "../x", "a b", "a?b", "a#b"):
        with pytest.raises(ValueError):
            arxiv.html_url(bad)
    assert github.head_url("example-org/example-lib", "feature/x y") == (
        "https://api.github.com/repos/example-org/example-lib/branches/feature%2Fx%20y")
    for bad_name, branch in (("noslash", "main"), ("a/b/c", "main"), ("a/../b", "main"),
                             ("a/b", "  ")):
        with pytest.raises(ValueError):
            github.head_url(bad_name, branch)
    with pytest.raises(ValueError):
        task_for("nope", "x", limit=1)
    with pytest.raises(ValueError):
        stackexchange.search_url("x", pagesize=1, site="Stack Overflow")
