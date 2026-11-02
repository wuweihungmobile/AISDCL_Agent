"""抓取器的安全與禮貌（TCS AT-960-8-1～8-5、8-7、8-E-1、8-E-3；PRD NFR-R2P-02／03；V-R4、V-R9）。

hermetic：沒有任何測試連真外部端點。假連線層（`FakeTransport`）收到的 `request.url.host` 就是被釘住
的 IP，連同 Host 標頭與 SNI 一起記錄；假解析器記錄解析次數；假時鐘讓睡眠不真的等待。唯一碰到真 TCP
的是 V-R4 的線路層案例：`socket.create_connection` 被改道到本機假伺服器，真的 httpx 傳輸層在線路上走
一遍、本機伺服器讀到 TLS ClientHello 的 SNI。DB 型案例用拋棄式資料庫（`BRIDGE_TEST_DSN` 缺＝
TOOL-ABSENCE 跳過）。
"""
from __future__ import annotations

import ast
import gzip
import inspect
import json
import logging
import re
import socket
import subprocess
import threading
import uuid
import zlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from email.utils import formatdate
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.research.db import ResearchDb, ResearchDbError
from app.research.fetch import (
    DEPTH_LIMITS,
    ENV_MIN_INTERVALS,
    OUTCOMES,
    PIN_MODE,
    UNPARSED_HOST,
    EffectiveAllowlist,
    FetchTask,
    HostThrottle,
    arxiv,
    build_effective_allowlist,
    builtin_floor,
    check_research_url,
    effective_limits,
    github,
    land_raw,
    plan_fetches,
    run_prefetch,
    semantic_scholar,
    stackexchange,
)
from app.research.fetch import http as fetch_http
from app.research.fetch.allowlist import DEFAULT_ENV_MIN_INTERVAL, db_safe_text, stored_url
from app.research.fetch.http import (
    DENIED_ALLOWLIST,
    DENIED_PRIVATE_IP,
    MAX_RATE_WAIT_SECONDS,
    MAX_REDIRECTS,
    USER_AGENT,
    body_backoff_seconds,
    signal_wait_seconds,
)
from app.security import AuditLog, check_outbound_url
from app.settings import RESEARCH_DEFAULT_FETCH_MAX_BYTES, RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS
from tests.research_net_support import (
    PUBLIC_IP,
    Call,
    ClientHelloProbe,
    FakeResolver,
    Reply,
    forbid_external_network,
    json_reply,
    make_rig,
    route_connections,
    text_reply,
)
from tests.research_pg_support import MIGRATION_DIR, ThrowawayDb, make_research_db

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "research" / "fetch"
HOSTS = tuple(ENV_MIN_INTERVALS)
ALICE = "alice@example.com"
LIMIT = RESEARCH_DEFAULT_FETCH_MAX_BYTES
SENTINEL = "ghp_SENTINEL"


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    forbid_external_network(monkeypatch)


@pytest.fixture
def rdb() -> Iterator[ThrowawayDb]:
    db = make_research_db()
    try:
        yield db
    finally:
        db.drop()


def make_project(rdb: ThrowawayDb, tmp_path: Path) -> tuple[ResearchDb, str]:
    store, rid = ResearchDb(rdb.dsn), str(uuid.uuid4())
    store.create_project(
        research_id=rid, slug="fetch-sec", title="t", topic="t", workspace_path=str(tmp_path),
        fsm_project="research-fetch-sec", fsm_state_dir=str(tmp_path / "fsm"), created_by=ALICE)
    return store, rid


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def admin_entry(host: str, interval: int = 3, *, enabled: bool = True) -> dict[str, Any]:
    return {"list_kind": "FETCH", "host": host, "enabled": enabled, "layer": "INDUSTRY",
            "min_interval_seconds": interval}


# ══ AT-960-8-1：精確 host、僅 https、解析不出 host 的紀錄 ══════════════════════════════════════
#: (url, 通過?, 入庫的 host)——host 欄：可解析者為主機名、解析不出者為保留字
FORMS: list[tuple[str, bool, str]] = [
    ("http://export.arxiv.org/x", False, "export.arxiv.org"),
    ("https://export.arxiv.org.evil.com/", False, "export.arxiv.org.evil.com"),
    ("https://evilarxiv.org/", False, "evilarxiv.org"),
    ("https://user@export.arxiv.org/", False, "export.arxiv.org"),
    ("https://export.arxiv.org:8443/", False, "export.arxiv.org"),
    ("https://EXPORT.ARXIV.ORG/", True, "export.arxiv.org"),
    ("https://export.arxiv.org./", False, "export.arxiv.org"),
    ("https://xn--export-arxiv-x.org/", False, UNPARSED_HOST),
    ("https://api.github.com/repos/a/b", True, "api.github.com"),
    ("file:///etc/passwd", False, UNPARSED_HOST),
    ("", False, UNPARSED_HOST),
    ("https://export.arxiv.org\\@evil.com/", False, UNPARSED_HOST),
    ("file:///" + "a" * 600, False, UNPARSED_HOST),
    ("https://reddit.com/", False, "reddit.com"),
]
#: 只有這三種形態是既有的 `check_outbound_url` 放行、包裝層才拒絕的
WRAPPER_ONLY = {"http://export.arxiv.org/x", "https://export.arxiv.org:8443/",
                "https://export.arxiv.org./"}


FORM_PARAMS = [pytest.param(*form, id=f"form{n:02d}") for n, form in enumerate(FORMS, 1)]


@pytest.mark.parametrize(("url", "allowed", "_host"), FORM_PARAMS)
def test_AT_960_8_1_only_normalised_arxiv_and_github_https_forms_pass(
        url: str, allowed: bool, _host: str) -> None:
    verdict = check_research_url(url, HOSTS, FakeResolver())
    assert verdict.ok is allowed, (url[:60], verdict)
    assert (verdict.outcome is None) == allowed
    if not allowed:
        assert verdict.outcome == DENIED_ALLOWLIST, "各基底主機皆解析為公網：拒絕不是私網判準造成的"


@pytest.mark.parametrize(("url", "_allowed", "_host"), FORM_PARAMS)
def test_AT_960_8_1_the_wrapper_differs_from_the_wrapped_function_only_on_three_forms(
        url: str, _allowed: bool, _host: str) -> None:
    wrapped = check_outbound_url(url, HOSTS)[0]
    ours = check_research_url(url, HOSTS, FakeResolver()).ok
    if url in WRAPPER_ONLY:
        assert (wrapped, ours) == (True, False), \
            "既有函式放行 http、任意埠與尾點；研究包裝層必須拒絕（不做正規化放行）"
    else:
        assert wrapped == ours, "其餘形態兩者的放行與拒絕一致"


def test_AT_960_8_1_denied_calls_are_recorded_in_the_database_with_the_documented_columns(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    store, rid = make_project(rdb, tmp_path)
    rig = make_rig(lambda call: json_reply("{}"))
    expected_rows = []
    for url, allowed, host in FORMS:
        result = rig.client.fetch(url, layer="ACADEMIC")
        if allowed:
            assert result.terminal.outcome == "OK", url
            continue
        assert [r.outcome for r in result.records] == [DENIED_ALLOWLIST], url[:60]
        store.insert_fetch(research_id=rid, fetch=result.terminal.to_db())
        expected_rows.append((host, url[:500]))
    assert rig.calls and all(c.host_header in ("export.arxiv.org", "api.github.com")
                             for c in rig.calls), "被拒的形態一個連線都沒有"
    rows = rdb.q("SELECT host, url, outcome, http_status, layer, fetch_method, observed_by, "
                 "fetch_no FROM console.research_fetches WHERE research_id = %s ORDER BY fetch_no",
                 rid)
    assert [(r[0], r[1]) for r in rows] == expected_rows and len(rows) == 12
    assert {(r[2], r[3], r[4], r[5], r[6]) for r in rows} == {
        (DENIED_ALLOWLIST, None, "ACADEMIC", "API", "BRIDGE")}
    by_url = {r[1]: r[0] for r in rows}
    assert by_url[""] == UNPARSED_HOST, "空字串入庫為空字串（不是 NULL），host 為保留字"
    long_row = next(r for r in rows if r[1].startswith("file:///a"))
    assert (long_row[0], len(long_row[1]), long_row[1]) == (
        UNPARSED_HOST, 500, "file:///" + "a" * 492)
    assert by_url["https://reddit.com/"] == "reddit.com" and by_url[
        "http://export.arxiv.org/x"] == "export.arxiv.org"


def test_AT_960_8_1_the_reserved_host_is_what_makes_the_database_accept_an_unparsed_call(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    assert UNPARSED_HOST == "(unparsed)" and len(UNPARSED_HOST) == 10
    store, rid = make_project(rdb, tmp_path)
    base = {"layer": "ACADEMIC", "fetch_method": "API", "observed_by": "BRIDGE", "url": "x",
            "outcome": DENIED_ALLOWLIST}
    for bad_host in ("", None):                      # 空字串與 NULL 都會被 CHECK 擋下
        with pytest.raises(ResearchDbError) as caught:
            store.insert_fetch(research_id=rid, fetch={**base, "host": bad_host})
        assert caught.value.sqlstate == "23514", repr(bad_host)
    store.insert_fetch(research_id=rid, fetch={**base, "host": UNPARSED_HOST})
    assert rdb.count("research_fetches") == 1


def test_AT_960_8_1_the_two_allowlists_do_not_pollute_each_other() -> None:
    model = ["api.minimaxi.com", "localhost"]
    before = [check_outbound_url(u, model) for u in (
        "https://api.minimaxi.com/v1", "https://export.arxiv.org/x", "http://localhost/x")]
    assert [b[0] for b in before] == [True, False, True]
    research = HOSTS + ("docs.example.com",)
    assert check_research_url("https://docs.example.com/p", research, FakeResolver()).ok
    assert not check_research_url("https://docs.example.com/p", HOSTS, FakeResolver()).ok
    assert not check_research_url("https://api.minimaxi.com/v1", research, FakeResolver()).ok
    assert [check_outbound_url(u, model) for u in (
        "https://api.minimaxi.com/v1", "https://export.arxiv.org/x", "http://localhost/x")
            ] == before, "研究清單的變動不影響既有函式對模型端點清單的判定"
    assert [p for p in inspect.signature(check_outbound_url).parameters] == ["url", "allowlist"]


def test_AT_960_8_1_a_layer_outside_the_enumeration_is_a_caller_error_not_a_late_check_failure(
) -> None:
    rig = make_rig()
    for layer in ("academic", "", "WEB", None):
        with pytest.raises(ValueError, match="layer"):
            rig.client.fetch("https://export.arxiv.org/x", layer=layer)       # type: ignore[arg-type]
    assert rig.calls == [] and rig.resolver.calls == []
    record = rig.client.fetch("https://reddit.com/", layer="COMMUNITY",
                              query_text="a\x00b").terminal
    assert record.query_text == "a\\x00b", "查詢字串（TEXT 欄）的 NUL 也先消毒"


def test_AT_960_8_1_unsafe_characters_in_a_denied_url_cannot_break_the_database_write(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    store, rid = make_project(rdb, tmp_path)
    rig = make_rig()
    for url in ("https://export.arxiv.org/a\x00b", "https://x.example/\ud800z", "x" * 3000,
                "https://" + "h" * 300 + ".example/"):
        result = rig.client.fetch(url, layer="OSS")
        record = result.terminal
        assert record.outcome == DENIED_ALLOWLIST and "\x00" not in record.url
        assert len(record.url) <= 500 and len(record.host) <= 255
        store.insert_fetch(research_id=rid, fetch=record.to_db())
    assert rdb.count("research_fetches") == 4
    assert db_safe_text("a\x00b\ud800") == "a\\x00b\\ud800"
    assert stored_url(None) == "" and stored_url(5) == ""


# ══ AT-960-8-2：私網、loopback、link-local 及編碼形態 ═══════════════════════════════════════════
NON_PUBLIC = ["127.0.0.1", "10.1.2.3", "172.16.0.5", "172.31.255.255", "192.168.1.1",
              "169.254.169.254", "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1", "0.0.0.0"]


@pytest.mark.parametrize("address", NON_PUBLIC)
def test_AT_960_8_2_a_host_that_resolves_to_a_non_public_address_is_denied_without_connecting(
        address: str) -> None:
    rig = make_rig(resolver=FakeResolver(default=[address]))
    result = rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
    assert [r.outcome for r in result.records] == [DENIED_PRIVATE_IP], address
    assert result.terminal.http_status is None and result.terminal.raw_text is None
    assert rig.calls == [], "假連線層的 connect 呼叫次數為 0"
    assert rig.resolver.calls == ["export.arxiv.org"]


@pytest.mark.parametrize("address", [
    "100.64.0.1", "192.0.2.1", "198.18.0.1", "198.51.100.7", "203.0.113.9", "224.0.0.1",
    "240.0.0.1", "255.255.255.255", "2001:db8::1", "ff02::1", "::", "fec0::1"])
def test_AT_960_8_2_every_other_non_global_range_is_denied_too(address: str) -> None:
    """判準是「全域公網位址」而不是「不在私網清單」：CGNAT、文件用、基準測試、多播、保留段一律拒。"""
    rig = make_rig(resolver=FakeResolver(default=[address]))
    result = rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
    assert [r.outcome for r in result.records] == [DENIED_PRIVATE_IP], address
    assert rig.calls == []


@pytest.mark.parametrize("encoded", ["2130706433", "0x7f000001", "127.1"])
def test_AT_960_8_2_encoded_loopback_hosts_are_denied_with_a_record_and_no_connection(
        encoded: str) -> None:
    rig = make_rig()
    result = rig.client.fetch(f"https://{encoded}/x", layer="ACADEMIC")
    assert len(result.records) == 1
    assert result.terminal.outcome in (DENIED_ALLOWLIST, DENIED_PRIVATE_IP)
    assert rig.calls == [] and rig.resolver.calls == []


@pytest.mark.parametrize("encoded", ["2130706433", "0x7f000001", "127.1"])
def test_AT_960_8_2_an_encoded_literal_an_admin_allowlisted_still_fails_the_address_check(
        encoded: str) -> None:
    rig = make_rig(allowlist=build_effective_allowlist(HOSTS, [admin_entry(encoded)]),
                   resolver=FakeResolver({encoded: ["127.0.0.1"]}))
    result = rig.client.fetch(f"https://{encoded}/x", layer="ACADEMIC")
    assert [r.outcome for r in result.records] == [DENIED_PRIVATE_IP] and rig.calls == []


@pytest.mark.parametrize("address", ["172.15.255.255", "172.32.0.1", PUBLIC_IP,
                                     "2606:4700:4700::1111"])
def test_AT_960_8_2_addresses_just_outside_the_private_ranges_are_not_over_blocked(
        address: str) -> None:
    rig = make_rig(lambda call: json_reply("{}"), resolver=FakeResolver(default=[address]))
    result = rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
    assert result.ok and [c.ip for c in rig.calls] == [address]


def test_AT_960_8_2_one_non_public_answer_among_public_ones_denies_the_whole_host() -> None:
    rig = make_rig(resolver=FakeResolver(default=[PUBLIC_IP, "10.0.0.1"]))
    result = rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
    assert result.terminal.outcome == DENIED_PRIVATE_IP and rig.calls == []


def test_AT_960_8_2_a_dns_failure_is_a_recorded_http_error_without_a_connection() -> None:
    def boom(host: str) -> list[str]:
        raise socket.gaierror("fake: name or service not known")

    for resolver in (boom, lambda host: []):
        rig = make_rig(resolver=resolver)                       # type: ignore[arg-type]
        result = rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
        assert [r.outcome for r in result.records] == ["HTTP_ERROR"] and rig.calls == []
        assert "dns_failure" in result.terminal.detail


# ══ AT-960-8-3：DNS rebinding 與 V-R4 ═══════════════════════════════════════════════════════════
def test_AT_960_8_3_the_connection_goes_only_to_the_first_validated_address() -> None:
    assert PIN_MODE in ("pinned_ip_sni", "resolve_then_check")
    resolver = FakeResolver(sequence=[[PUBLIC_IP], ["127.0.0.1"]])
    rig = make_rig(lambda call: json_reply('{"a": 1}'), resolver=resolver)
    result = rig.client.fetch("https://export.arxiv.org/api/query?q=1", layer="ACADEMIC")
    assert result.ok and len(rig.calls) == 1
    call = rig.calls[0]
    assert resolver.calls == ["export.arxiv.org"], "全程只解析一次：第二次回答（私網）根本沒被問到"
    assert call.ip == PUBLIC_IP and call.ip != "127.0.0.1"
    if PIN_MODE == "pinned_ip_sni":
        assert (call.host_header, call.sni) == ("export.arxiv.org", "export.arxiv.org")
        assert (call.scheme, call.port) == ("https", None), "443（URL 的預設埠）"
    else:
        assert call.host_header == "export.arxiv.org"


def test_AT_960_8_3_a_private_first_answer_is_denied_with_zero_connections() -> None:
    rig = make_rig(resolver=FakeResolver(sequence=[["127.0.0.1"], [PUBLIC_IP]]))
    result = rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
    assert result.terminal.outcome == DENIED_PRIVATE_IP and rig.calls == []


def test_AT_960_8_3_redirects_are_never_followed_automatically() -> None:
    tree = ast.parse(inspect.getsource(fetch_http))
    flags = [kw.value.value for node in ast.walk(tree) if isinstance(node, ast.Call)
             for kw in node.keywords if kw.arg == "follow_redirects"
             and isinstance(kw.value, ast.Constant)]
    assert flags and set(flags) == {False}, "follow_redirects 為 false，且沒有任何 True"
    rig = make_rig(lambda call: Reply(302, {"location": "https://arxiv.org/next"}))
    result = rig.client.fetch("https://export.arxiv.org/a", layer="ACADEMIC")
    assert len(result.records) == MAX_REDIRECTS + 1 and len(rig.calls) == MAX_REDIRECTS + 1


def test_AT_960_8_3_v_r4_the_pinned_ip_and_the_original_sni_are_what_actually_go_on_the_wire(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """V-R4 證據：真的 httpx 傳輸層＋真的 `FetchClient`，連線被改道到本機假伺服器；伺服器讀到的
    ClientHello 的 SNI 是原 hostname，而 httpx 原本要連的目標恰是被釘住的 IP 與 443。"""
    resolver = FakeResolver(sequence=[[PUBLIC_IP], ["127.0.0.1"]])
    with ClientHelloProbe() as probe:
        wanted = route_connections(monkeypatch, ("127.0.0.1", probe.port))
        client = fetch_http.FetchClient(
            allowlist=build_effective_allowlist(HOSTS), resolver=resolver)
        result = client.fetch("https://export.arxiv.org/api/query?search_query=x", layer="ACADEMIC")
    assert wanted == [(PUBLIC_IP, 443)], "連線目標恰為首次驗證的 IP（埠 443）"
    assert probe.hello_seen and probe.sni == "export.arxiv.org", \
        "TLS SNI 是原 hostname（不是 IP，也不是第二次解析的 127.0.0.1）"
    assert probe.peer is not None and probe.peer[0] == "127.0.0.1"
    assert resolver.calls == ["export.arxiv.org"]
    assert result.terminal.outcome == "HTTP_ERROR", "假伺服器不完成握手：失敗記成一筆紀錄、不丟例外"


def test_AT_960_8_3_v_r4_without_the_sni_extension_an_ip_url_sends_no_hostname(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """對照組：沒有 `sni_hostname` 擴充時，連 IP 的 TLS 不帶任何 server_name——所以擴充是必要的。"""
    with ClientHelloProbe() as probe:
        route_connections(monkeypatch, ("127.0.0.1", probe.port))
        with httpx.Client(transport=httpx.HTTPTransport(), trust_env=False) as client, \
                pytest.raises(httpx.HTTPError):
            client.get(f"https://{PUBLIC_IP}/x", headers={"Host": "export.arxiv.org"})
    assert probe.hello_seen and probe.sni is None


# ══ AT-960-8-4：重導不自動跟隨、逐跳重驗 ═══════════════════════════════════════════════════════
def redirect_to(location: str, status: int = 302) -> Reply:
    return Reply(status, {"location": location})


def chain(routes: dict[str, Reply]) -> Callable[[Call], Reply]:
    return lambda call: routes.get(call.path, Reply(404))


def test_AT_960_8_4_allowed_hops_each_leave_a_record_and_the_terminal_result_is_the_origin_s(
) -> None:
    rig = make_rig(chain({
        "/a": redirect_to("https://arxiv.org/b"), "/b": redirect_to("/c", 301),
        "/c": json_reply('{"done": true}')}))
    result = rig.client.fetch("https://export.arxiv.org/a", layer="ACADEMIC")
    assert [(r.url, r.outcome, r.http_status) for r in result.records] == [
        ("https://export.arxiv.org/a", "OK", 302), ("https://arxiv.org/b", "OK", 301),
        ("https://arxiv.org/c", "OK", 200)]
    assert result.url == "https://export.arxiv.org/a" and result.ok
    assert result.terminal is result.records[-1] and result.text == '{"done": true}'
    assert [c.host_header for c in rig.calls] == ["export.arxiv.org", "arxiv.org", "arxiv.org"]
    assert rig.resolver.calls == ["export.arxiv.org", "arxiv.org", "arxiv.org"], "每跳重驗"
    assert [r.raw_text for r in result.records[:2]] == [None, None], "重導跳不落地任何本文"


def test_AT_960_8_4_a_hop_outside_the_allowlist_is_denied_before_connecting() -> None:
    rig = make_rig(chain({"/a": redirect_to("https://evil.example.com/steal")}))
    result = rig.client.fetch("https://export.arxiv.org/a", layer="ACADEMIC")
    assert [r.outcome for r in result.records] == ["OK", DENIED_ALLOWLIST]
    assert result.terminal.host == "evil.example.com" and not result.ok
    assert len(rig.calls) == 1, "到 allowlist 外者在連線前拒絕"


def test_AT_960_8_4_a_hop_that_resolves_to_a_private_address_is_denied_before_connecting() -> None:
    allowlist = build_effective_allowlist(HOSTS, [admin_entry("internal.example.com")])
    resolver = FakeResolver({"internal.example.com": ["10.0.0.5"]})
    rig = make_rig(chain({"/a": redirect_to("https://internal.example.com/x")}),
                   allowlist=allowlist, resolver=resolver)
    result = rig.client.fetch("https://export.arxiv.org/a", layer="ACADEMIC")
    assert [r.outcome for r in result.records] == ["OK", DENIED_PRIVATE_IP]
    assert len(rig.calls) == 1


def test_AT_960_8_4_downgrades_and_odd_ports_are_refused_at_the_redirect_hop_too() -> None:
    for target in ("http://arxiv.org/b", "https://arxiv.org:8443/b", "https://arxiv.org./b",
                   "file:///etc/passwd", "//evil.example.com/b"):
        rig = make_rig(chain({"/a": redirect_to(target)}))
        result = rig.client.fetch("https://export.arxiv.org/a", layer="ACADEMIC")
        assert result.terminal.outcome == DENIED_ALLOWLIST and len(rig.calls) == 1, target


def test_AT_960_8_4_more_than_three_hops_is_an_http_error_with_an_explanation() -> None:
    rig = make_rig(lambda call: redirect_to("https://arxiv.org/loop"))
    result = rig.client.fetch("https://export.arxiv.org/loop", layer="ACADEMIC")
    assert len(rig.calls) == MAX_REDIRECTS + 1, "最多跟 3 跳（4 個請求）"
    assert [r.outcome for r in result.records] == ["OK"] * MAX_REDIRECTS + ["HTTP_ERROR"]
    assert "3 跳" in result.terminal.detail and not result.ok
    assert result.terminal.http_status == 302


def test_AT_960_8_4_exactly_three_hops_still_succeeds() -> None:
    rig = make_rig(chain({"/0": redirect_to("/1"), "/1": redirect_to("/2"),
                          "/2": redirect_to("/3"), "/3": json_reply("{}")}))
    result = rig.client.fetch("https://export.arxiv.org/0", layer="ACADEMIC")
    assert result.ok and len(result.records) == 4 and len(rig.calls) == 4


def test_AT_960_8_4_a_redirect_without_a_usable_location_header_is_an_http_error() -> None:
    for reply in (Reply(302), Reply(302, {"location": "   "}),
                  Reply(302, {"location": "http://[::1"})):
        rig = make_rig(lambda call, r=reply: r)
        result = rig.client.fetch("https://export.arxiv.org/a", layer="ACADEMIC")
        assert [r.outcome for r in result.records] == ["HTTP_ERROR"], reply.headers
        assert "location" in result.terminal.detail.lower() and len(rig.calls) == 1


# ══ AT-960-8-5：失敗各記各的、不截斷、其餘來源續跑、全失敗才 no_evidence ═════════════════════════
SOURCE_PATHS = {
    "timeout": Reply(200, {"content-type": "text/html"}, b"<p>slow</p>", advance=21),
    "http500": Reply(500, {"content-type": "text/plain"}, b"boom"),
    "http404": Reply(404, {"content-type": "text/plain"}, b"nope"),
    "toolarge": Reply(200, {"content-type": "text/plain"}, b"a" * (LIMIT + 1)),
    "pdf": Reply(200, {"content-type": "application/pdf"}, b"%PDF-1.7 binary"),
    "binary": Reply(200, {"content-type": "application/octet-stream"}, b"\x00\x01\x02"),
    "html": Reply(200, {"content-type": "text/html; charset=utf-8"},
                  "<html><body>正常的 HTML</body></html>".encode()),
    "atom": Reply(200, {"content-type": "application/atom+xml"}, fixture_bytes("arxiv_golden.xml")),
}


def test_AT_960_8_5_each_failure_kind_is_recorded_on_its_own_and_nothing_is_truncated(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    store, rid = make_project(rdb, tmp_path)
    rig = make_rig(lambda call: SOURCE_PATHS[call.path.strip("/")])
    workspace = tmp_path / "ws"
    results = {name: rig.client.fetch(f"https://arxiv.org/{name}", layer="ACADEMIC")
               for name in SOURCE_PATHS}
    got = {name: (r.terminal.outcome, r.terminal.http_status) for name, r in results.items()}
    assert got == {"timeout": ("TIMEOUT", 200), "http500": ("HTTP_ERROR", 500),
                   "http404": ("HTTP_ERROR", 404), "toolarge": ("TOO_LARGE", 200),
                   "pdf": ("PARSE_ERROR", 200), "binary": ("PARSE_ERROR", 200),
                   "html": ("OK", 200), "atom": ("OK", 200)}
    for name in ("pdf", "binary"):
        assert "非文字" in results[name].terminal.detail, name
    assert "不截斷" in results["toolarge"].terminal.detail
    for name, result in results.items():
        record = result.terminal
        store.insert_fetch(research_id=rid, fetch=record.to_db())
        if record.outcome == "OK":
            landed = land_raw(workspace, record)
            assert landed is not None
            assert (workspace / record.raw_rel_path).read_bytes() == SOURCE_PATHS[name].body
        else:
            raw = (record.raw_text, record.raw_sha256, record.raw_bytes)
            assert raw == (None, None, None), name
            assert land_raw(workspace, record) is None
    raw_files = sorted(p.name for p in (workspace / "00_research" / "raw").glob("*"))
    assert len(raw_files) == 2 and all(re.fullmatch(r"[0-9a-f]{12}\.txt", n) for n in raw_files)
    rows = rdb.q("SELECT outcome, http_status, raw_sha256, raw_bytes FROM console.research_fetches "
                 "WHERE research_id = %s ORDER BY fetch_no", rid)
    assert [(r[0], r[1]) for r in rows] == [
        ("TIMEOUT", 200), ("HTTP_ERROR", 500), ("HTTP_ERROR", 404), ("TOO_LARGE", 200),
        ("PARSE_ERROR", 200), ("PARSE_ERROR", 200), ("OK", 200), ("OK", 200)]
    assert [r[2] is not None for r in rows] == [False] * 6 + [True] * 2, "只有成功的才有原文摘要"
    assert [r[3] for r in rows[6:]] == [len(SOURCE_PATHS["html"].body),
                                       len(SOURCE_PATHS["atom"].body)]


def test_AT_960_8_5_the_size_limit_is_the_configured_value_and_the_boundary_is_exact() -> None:
    assert LIMIT == 5_242_880 and RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS == 20.0
    for size, outcome in ((LIMIT, "OK"), (LIMIT + 1, "TOO_LARGE")):
        rig = make_rig(lambda call, n=size: text_reply(b"a" * n, "text/plain"))
        assert rig.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal.outcome == outcome
    small = make_rig(lambda call: text_reply(b"abcdef", "text/plain"), max_bytes=5)
    assert small.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal.outcome == (
        "TOO_LARGE"), "上限讀設定值（max_bytes）"
    declared = make_rig(lambda call: Reply(200, {"content-type": "text/plain",
                                                 "content-length": str(LIMIT + 1)}, b"a"))
    record = declared.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal
    assert record.outcome == "TOO_LARGE" and "Content-Length" in record.detail


def test_AT_960_8_5_a_slow_body_and_a_late_empty_body_both_time_out_on_the_fake_clock() -> None:
    slow = make_rig(lambda call: Reply(200, {"content-type": "text/plain"},
                                       b"a" * (3 * 65_536), chunk_advance=8.0))
    assert slow.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal.outcome == "TIMEOUT"
    late = make_rig(lambda call: Reply(200, {"content-type": "text/plain"}, b"", advance=25))
    assert late.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal.outcome == "TIMEOUT"
    raising = make_rig(lambda call: Reply(raises=httpx.ReadTimeout("fake")))
    result = raising.client.fetch("https://arxiv.org/x", layer="ACADEMIC")
    assert (result.terminal.outcome, result.terminal.http_status) == ("TIMEOUT", None)
    refused = make_rig(lambda call: Reply(raises=httpx.ConnectError("fake refused")))
    assert refused.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal.outcome == (
        "HTTP_ERROR")


def encoded_reply(body: bytes, encoding: str) -> Reply:
    return Reply(200, {"content-type": "application/json", "content-encoding": encoding}, body)


def test_AT_960_8_5_compressed_bodies_are_bounded_after_decompression() -> None:
    bomb = gzip.compress(b"0" * (LIMIT * 4))                   # 幾 KB 的壓縮炸彈
    assert len(bomb) < 100_000
    cases = {
        "gzip ok": (encoded_reply(gzip.compress(b'{"a": 1}'), "gzip"), "OK"),
        "deflate ok": (encoded_reply(zlib.compress(b'{"a": 1}'), "deflate"), "OK"),
        "gzip bomb": (encoded_reply(bomb, "gzip"), "TOO_LARGE"),
        "gzip corrupt": (encoded_reply(b"not gzip at all", "gzip"), "PARSE_ERROR"),
        "gzip truncated": (encoded_reply(gzip.compress(b'{"a": 1}')[:-6], "gzip"), "PARSE_ERROR"),
        "brotli unsupported": (encoded_reply(b"x", "br"), "PARSE_ERROR"),
    }
    for label, (reply, outcome) in cases.items():
        rig = make_rig(lambda call, r=reply: r)
        record = rig.client.fetch("https://api.stackexchange.com/x", layer="COMMUNITY").terminal
        assert record.outcome == outcome, (label, record.detail)
    exact = make_rig(lambda call: encoded_reply(gzip.compress(b"a" * 64), "gzip"), max_bytes=64)
    over = make_rig(lambda call: encoded_reply(gzip.compress(b"a" * 65), "gzip"), max_bytes=64)
    assert exact.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal.outcome == "OK"
    assert over.client.fetch("https://arxiv.org/x", layer="ACADEMIC").terminal.outcome == (
        "TOO_LARGE")


def test_AT_960_8_5_text_decoding_follows_the_declared_charset_and_never_raises() -> None:
    cases = [("utf-8; ", "中文".encode(), "中文"), ("big5", "中文".encode("big5"), "中文"),
             ("nonsense-charset", b"abc", "abc"), ("zlib", b"abc", "abc")]
    for charset, body, text in cases:
        rig = make_rig(lambda call, b=body, c=charset: text_reply(
            b, f"text/plain; charset={c}"))
        assert rig.client.fetch("https://arxiv.org/x", layer="ACADEMIC").text == text, charset
    bom = make_rig(lambda call: text_reply(b"\xef\xbb\xbf{}", "application/json"))
    assert bom.client.fetch("https://arxiv.org/x", layer="ACADEMIC").text == "{}"
    invalid = make_rig(lambda call: text_reply(b"a\xffb", "text/plain"))
    assert invalid.client.fetch("https://arxiv.org/x", layer="ACADEMIC").text == "a�b"
    assert fetch_http.decode_text(b"x", "") == "x"


def routed_script(table: dict[str, Reply]) -> Callable[[Call], Reply]:
    return lambda call: table.get(call.path.split("?")[0], Reply(404))


def test_AT_960_8_5_other_sources_keep_running_and_only_all_failed_means_no_evidence() -> None:
    golden = text_reply(fixture_bytes("semantic_scholar_golden.json"), "application/json")
    rig = make_rig(routed_script({
        "/graph/v1/paper/search": golden,
        "/api/query": Reply(500, {"content-type": "text/plain"}, b"down"),
        "/search/repositories": Reply(200, {"content-type": "application/pdf"}, b"%PDF"),
        "/2.3/search/advanced": Reply(raises=httpx.ReadTimeout("slow"))}))
    tasks = [FetchTask("arxiv", "ACADEMIC", arxiv.search_url("gc", max_results=5)),
             FetchTask("semantic_scholar", "ACADEMIC", semantic_scholar.search_url("gc", limit=5)),
             FetchTask("github", "OSS", github.search_url("gc", per_page=5)),
             FetchTask("stackexchange", "COMMUNITY", stackexchange.search_url("gc", pagesize=5))]
    batch = run_prefetch(rig.client, tasks, depth_level="QUICK")
    assert batch.planned == 4
    assert [r.outcome for r in batch.failures] == ["HTTP_ERROR", "PARSE_ERROR", "TIMEOUT"]
    assert len(batch.sources) == 2 and {b.task.kind for b in batch.sources} == {"semantic_scholar"}
    assert not batch.all_failed and not batch.no_sources and batch.exit_reason is None
    assert len(rig.calls) == 4, "第一個失敗不影響其餘來源"
    failed = make_rig(lambda call: Reply(500))
    none = run_prefetch(failed.client, tasks, depth_level="QUICK")
    assert none.all_failed and none.no_sources and none.exit_reason == "no_evidence"
    assert none.sources == [] and len(none.failures) == 4 == len(none.records)


def test_AT_960_8_5_a_good_fetch_in_a_bad_format_is_a_parse_error_and_not_a_source() -> None:
    rig = make_rig(lambda call: text_reply("<html>not atom</html>", "application/atom+xml"))
    task = FetchTask("arxiv", "ACADEMIC", arxiv.search_url("gc", max_results=5))
    batch = run_prefetch(rig.client, [task], depth_level="QUICK")
    assert batch.sources == [] and batch.all_failed
    assert [r.outcome for r in batch.records] == ["PARSE_ERROR"]
    assert batch.records[0].raw_text is not None, "抓取成功：原文仍保留供稽核"
    assert "Atom" in batch.records[0].detail


def test_AT_960_8_5_outcome_vocabulary_equals_the_ddl_check_constraint() -> None:
    ddl = (MIGRATION_DIR / "V17__research_evidence.sql").read_text(encoding="utf-8")
    block = re.search(r"outcome VARCHAR\(18\) NOT NULL CHECK \(outcome IN \((.*?)\)\)", ddl,
                      re.DOTALL)
    assert block is not None
    assert tuple(re.findall(r"'([A-Z_]+)'", block.group(1))) == OUTCOMES


def test_AT_960_8_5_the_fetch_constants_are_pinned_to_the_documented_initial_values() -> None:
    """TCS §5.1：抓取常數（含「初值、未校準」者）以常數登記並以測試釘住；改值要連同規格一起改。"""
    assert fetch_http.TEXT_CONTENT_TYPES == frozenset({
        "text/html", "text/plain", "text/markdown", "application/json", "application/atom+xml"})
    assert MAX_REDIRECTS == 3 and PIN_MODE == "pinned_ip_sni"
    assert (RESEARCH_DEFAULT_FETCH_MAX_BYTES, RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS) == (
        5_242_880, 20.0)
    assert (fetch_http.FETCH_METHOD, fetch_http.OBSERVED_BY) == ("API", "BRIDGE"), \
        "Bridge 自己的 HTTP GET：WEB_* 與 AGENT_DECLARED 只屬 agent 宣告的 Web 層"
    assert fetch_http.RAW_DIR_REL == "00_research/raw"
    assert (fetch_http.MAX_RATE_WAIT_SECONDS, fetch_http.DEFAULT_BACKOFF_SECONDS) == (300.0, 10.0)


# ══ AT-960-8-7：速率禮貌 ═════════════════════════════════════════════════════════════════════
def gaps(rig: Any) -> list[float]:
    return [b.at - a.at for a, b in zip(rig.calls, rig.calls[1:], strict=False)]


def test_AT_960_8_7_default_effective_intervals_equal_the_v_r9_values() -> None:
    default = build_effective_allowlist(HOSTS)
    assert dict(ENV_MIN_INTERVALS) == {
        "export.arxiv.org": 3, "arxiv.org": 3, "api.semanticscholar.org": 3,
        "api.github.com": 60, "api.stackexchange.com": 3}
    for host in ("export.arxiv.org", "arxiv.org", "api.semanticscholar.org",
                 "api.stackexchange.com"):
        assert [default.interval(host, p, authenticated=a) for p in ("/", "/x/y")
                for a in (False, True)] == [3, 3, 3, 3], host
    github_table = {(path, auth): default.interval("api.github.com", path, authenticated=auth)
                    for path in ("/repos/a/b", "/search/repositories", "/search/code")
                    for auth in (False, True)}
    assert github_table == {
        ("/repos/a/b", False): 60, ("/repos/a/b", True): 1,
        ("/search/repositories", False): 6, ("/search/repositories", True): 2,
        ("/search/code", False): 6, ("/search/code", True): 6}
    assert DEFAULT_ENV_MIN_INTERVAL == 3
    for host, value in ENV_MIN_INTERVALS.items():
        assert builtin_floor(host, "/", authenticated=False) == value, \
            "路由輸出的基底值與抓取層的下限是同一份常數"
    assert builtin_floor("docs.example.com") == DEFAULT_ENV_MIN_INTERVAL


def test_AT_960_8_7_stack_exchange_interval_is_a_conservative_initial_value_not_a_fact() -> None:
    """V-R9 殘項：Stack Exchange 官方頁本棒未現查，3 秒是保守初值（非事實宣稱）；註記必須留在
    原始碼裡，免得日後有人把它讀成官方數值。"""
    package = Path(fetch_http.__file__).parent
    allowlist_source = (package / "allowlist.py").read_text(encoding="utf-8")
    assert "非事實宣稱" in allowlist_source and "Stack Exchange" in allowlist_source
    stack_source = (package / "stackexchange.py").read_text(encoding="utf-8")
    assert "未現查" in stack_source and "非事實" in stack_source
    assert ENV_MIN_INTERVALS["api.stackexchange.com"] == 3


def test_AT_960_8_7_requests_to_one_host_are_spaced_by_its_effective_interval() -> None:
    rig = make_rig(lambda call: json_reply("{}"))
    for _ in range(3):
        assert rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC").ok
    assert gaps(rig) == [3.0, 3.0] and rig.clock.sleeps == [3.0, 3.0]
    other = make_rig(lambda call: json_reply("{}"))
    for host in ("export.arxiv.org", "arxiv.org", "export.arxiv.org"):
        assert other.client.fetch(f"https://{host}/x", layer="ACADEMIC").ok
    assert gaps(other) == [3.0, 3.0], "arXiv 兩個 host 同屬一個操作者：共用一條時間線"
    mixed = make_rig(lambda call: json_reply("{}"))
    for host in ("export.arxiv.org", "api.semanticscholar.org", "api.stackexchange.com"):
        assert mixed.client.fetch(f"https://{host}/x", layer="ACADEMIC").ok
    assert mixed.clock.sleeps == [], "不同來源各有各的時間線，互不等待"


def test_AT_960_8_7_clients_built_from_settings_share_one_throttle_timeline(
        settings: Any) -> None:
    from dataclasses import replace as clone
    first = fetch_http.FetchClient.from_settings(settings)
    second = fetch_http.FetchClient.from_settings(clone(
        settings, research_fetch_max_bytes=123, research_fetch_timeout_seconds=7.5))
    assert first.throttle is second.throttle is fetch_http.SHARED_THROTTLE, \
        "研究 run 一個接一個建新客戶端，arXiv 的間隔限制仍要跨 run 成立"
    assert (first.max_bytes, first.timeout_seconds) == (RESEARCH_DEFAULT_FETCH_MAX_BYTES, 20.0)
    assert (second.max_bytes, second.timeout_seconds) == (123, 7.5), "上限與逾時取自 Settings"
    own = fetch_http.FetchClient.from_settings(settings, throttle=HostThrottle())
    assert own.throttle is not fetch_http.SHARED_THROTTLE, "測試可注入自己的時間線"
    direct = make_rig().client
    assert direct.throttle is not fetch_http.SHARED_THROTTLE, "直接建構的客戶端各有各的"


def test_AT_960_8_7_the_interval_is_measured_from_the_end_of_the_previous_request() -> None:
    rig = make_rig(lambda call: Reply(200, {"content-type": "application/json"}, b"{}",
                                      advance=2.0))
    for _ in range(2):
        rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
    assert rig.clock.sleeps == [3.0], "請求本身花了 2 秒，間隔仍從它結束起算 3 秒"
    assert rig.calls[1].at - rig.calls[0].at == 5.0


def test_AT_960_8_7_github_intervals_depend_on_the_token_and_the_endpoint() -> None:
    search = "/search/repositories?q=x"
    expected = {("/repos/a/b", None): 60.0, ("/repos/a/b", SENTINEL): 1.0,
                (search, None): 6.0, (search, SENTINEL): 2.0,
                ("/search/code?q=x", None): 6.0, ("/search/code?q=x", SENTINEL): 6.0}
    for (path, token), interval in expected.items():
        rig = make_rig(lambda call: json_reply("{}"), github_token=token)
        for _ in range(2):
            assert rig.client.fetch(f"https://api.github.com{path}", layer="OSS").ok
        assert rig.clock.sleeps == [interval], (path, token)


def test_AT_960_8_7_an_admin_entry_can_only_lengthen_the_interval() -> None:
    for entry_value, effective in ((1, 3.0), (3, 3.0), (10, 10.0)):
        allowlist = build_effective_allowlist(HOSTS, [admin_entry("export.arxiv.org", entry_value)])
        assert allowlist.interval("export.arxiv.org") == effective
        rig = make_rig(lambda call: json_reply("{}"), allowlist=allowlist)
        for _ in range(2):
            rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
        assert rig.clock.sleeps == [effective], entry_value
    off = admin_entry("export.arxiv.org", 90, enabled=False)
    assert build_effective_allowlist(HOSTS, [off]).interval("export.arxiv.org") == 3, \
        "停用的條目不貢獻值"
    unknown = build_effective_allowlist(HOSTS, [admin_entry("docs.example.com", 1)])
    assert unknown.interval("docs.example.com") == DEFAULT_ENV_MIN_INTERVAL
    assert build_effective_allowlist(HOSTS, [admin_entry("docs.example.com", 30)]).interval(
        "docs.example.com") == 30
    github_admin = build_effective_allowlist(HOSTS, [admin_entry("api.github.com", 20)])
    assert github_admin.interval("api.github.com", "/repos/a/b", authenticated=True) == 20
    assert github_admin.interval("api.github.com", "/repos/a/b") == 60


def signal_rig(headers: Callable[[float], dict[str, str]], body: str = "{}",
               host: str = "export.arxiv.org") -> tuple[Any, list[float]]:
    holder: dict[str, Any] = {}
    answers = iter([lambda: json_reply(body, **headers(holder["rig"].clock.epoch())),
                    lambda: json_reply("{}")])
    rig = make_rig(lambda call: next(answers)())
    holder["rig"] = rig
    for _ in range(2):
        assert rig.client.fetch(f"https://{host}/x", layer="ACADEMIC").ok
    return rig, rig.clock.sleeps


def test_AT_960_8_7_the_stricter_of_the_rate_limit_signals_wins() -> None:
    _, sleeps = signal_rig(lambda now: {"Retry-After": "30"})
    assert sleeps == [30.0], "Retry-After 比內建間隔嚴"
    _, sleeps = signal_rig(lambda now: {"X-RateLimit-Remaining": "0",
                                        "X-RateLimit-Reset": str(int(now + 45))})
    assert sleeps == [45.0], "X-RateLimit-Reset（epoch）"
    _, sleeps = signal_rig(lambda now: {"Retry-After": "30", "X-RateLimit-Remaining": "0",
                                        "X-RateLimit-Reset": str(int(now + 45))})
    assert sleeps == [45.0], "兩個訊號並存取較嚴者"
    _, sleeps = signal_rig(lambda now: {"Retry-After": "50", "X-RateLimit-Remaining": "0",
                                        "X-RateLimit-Reset": str(int(now + 45))})
    assert sleeps == [50.0]
    _, sleeps = signal_rig(lambda now: {"X-RateLimit-Remaining": "7",
                                        "X-RateLimit-Reset": str(int(now + 999))})
    assert sleeps == [3.0], "還有額度時 X-RateLimit-Reset 不構成等待"
    _, sleeps = signal_rig(lambda now: {"Retry-After": "1"})
    assert sleeps == [3.0], "訊號比內建間隔寬時仍取內建間隔"
    _, sleeps = signal_rig(lambda now: {"Retry-After": formatdate(now + 20, usegmt=True)})
    assert sleeps == [pytest.approx(20.0, abs=1.0)], "HTTP 日期形態"
    _, sleeps = signal_rig(lambda now: {}, body='{"items": [], "backoff": 12}',
                           host="api.stackexchange.com")
    assert sleeps == [12.0], "Stack Exchange 的 backoff 欄位"


def test_AT_960_8_7_signal_parsers_ignore_what_they_cannot_read() -> None:
    headers = httpx.Headers
    assert signal_wait_seconds(headers({"retry-after": "soon"}), 1e9) is None
    assert signal_wait_seconds(headers({"x-ratelimit-remaining": "0", "x-ratelimit-reset": "x"}),
                               1e9) is None
    assert signal_wait_seconds(headers({"x-ratelimit-remaining": "0",
                                        "x-ratelimit-reset": "12"}), 1.7e9) == 12.0
    assert signal_wait_seconds(headers({"retry-after": "-5"}), 1e9) is None
    assert signal_wait_seconds(headers({}), 1e9) is None
    for text in ("", "not json", "[1]", '{"backoff": "x"}', '{"backoff": true}', '{"a": 1}'):
        assert body_backoff_seconds(text) is None, text
    assert body_backoff_seconds('{"backoff": 5}') == 5.0


def test_AT_960_8_7_a_429_is_rate_limited_retried_once_after_backing_off_and_never_stormed(
) -> None:
    rig = make_rig(lambda call: Reply(429, {"retry-after": "30"}))
    result = rig.client.fetch("https://api.semanticscholar.org/x", layer="ACADEMIC")
    assert [r.outcome for r in result.records] == ["RATE_LIMITED", "RATE_LIMITED"]
    assert len(rig.calls) == 2, "最多再試一次，不重試風暴"
    assert rig.clock.sleeps == [30.0] and gaps(rig) == [30.0]
    assert all(r.http_status == 429 for r in result.records) and not result.ok
    recovers = iter([Reply(429, {"retry-after": "7"}), json_reply('{"ok": 1}')])
    rig2 = make_rig(lambda call: next(recovers))
    result2 = rig2.client.fetch("https://api.semanticscholar.org/x", layer="ACADEMIC")
    assert [r.outcome for r in result2.records] == ["RATE_LIMITED", "OK"] and result2.ok
    assert rig2.clock.sleeps == [7.0]
    bare = make_rig(lambda call: Reply(429))
    bare.client.fetch("https://api.semanticscholar.org/x", layer="ACADEMIC")
    assert bare.clock.sleeps == [10.0], "沒有任何訊號時退避下限 10 秒"
    forbidden = make_rig(lambda call: Reply(403, {"retry-after": "20"}))
    limited = forbidden.client.fetch("https://api.github.com/x", layer="OSS")
    assert limited.terminal.outcome == "RATE_LIMITED", "GitHub 的次級限制回 403＋Retry-After"
    plain = make_rig(lambda call: Reply(403))
    assert plain.client.fetch("https://api.github.com/x", layer="OSS").terminal.outcome == (
        "HTTP_ERROR"), "沒有限流訊號的 403 只是 HTTP 錯誤"


def test_AT_960_8_7_a_rate_window_longer_than_the_cap_is_not_slept_through() -> None:
    rig = make_rig(lambda call: Reply(200, {"content-type": "application/json",
                                            "retry-after": "3600"}, b"{}"))
    assert rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC").ok
    again = rig.client.fetch("https://export.arxiv.org/x", layer="ACADEMIC")
    assert [r.outcome for r in again.records] == ["RATE_LIMITED"]
    assert again.terminal.http_status is None and len(rig.calls) == 1, "視窗沒過：不連線"
    assert rig.clock.sleeps == [] and MAX_RATE_WAIT_SECONDS == 300.0
    assert "不連線" in again.terminal.detail


def test_AT_960_8_7_every_request_carries_the_named_user_agent() -> None:
    rig = make_rig(lambda call: json_reply("{}"))
    for host in HOSTS:
        rig.client.fetch(f"https://{host}/x", layer="ACADEMIC")
    assert {c.headers["user-agent"] for c in rig.calls} == {USER_AGENT}
    assert USER_AGENT.startswith("AISDLC-AgentConsole-Research/") and "httpx" not in USER_AGENT
    assert all(c.headers["accept-encoding"] == "gzip, deflate" and c.headers["connection"] == (
        "close") for c in rig.calls)


@contextmanager
def barrier_threads(rig: Any, urls: list[str]) -> Iterator[list[Any]]:
    results: list[Any] = []
    start = threading.Barrier(len(urls))

    def work(url: str) -> None:
        start.wait(5)
        results.append(rig.client.fetch(url, layer="ACADEMIC"))

    threads = [threading.Thread(target=work, args=(u,)) for u in urls]
    for t in threads:
        t.start()
    for t in threads:
        t.join(20)
    yield results


class UnlockedThrottle(HostThrottle):
    """對照組：沒有互斥與節流的節流槽。"""

    @contextmanager
    def slot(self, group: str, interval: float) -> Iterator[None]:
        yield


def test_AT_960_8_7_arxiv_allows_at_most_one_connection_at_a_time() -> None:
    urls = ["https://export.arxiv.org/a", "https://export.arxiv.org/b",
            "https://arxiv.org/c", "https://arxiv.org/d"]
    control = make_rig(lambda call: json_reply("{}"), hold=0.3, throttle=UnlockedThrottle())
    with barrier_threads(control, urls) as done:
        pass
    assert len(done) == 4 and control.transport.max_active >= 2, \
        "對照組：沒有互斥時假連線層看得到重疊，所以下面的 1 不是偶然"
    rig = make_rig(lambda call: json_reply("{}"), hold=0.05)
    with barrier_threads(rig, urls) as done:
        pass
    assert len(done) == 4 and all(r.ok for r in done)
    assert rig.transport.max_active == 1, "第二個請求待第一個完成才連線"
    times = sorted(c.at for c in rig.calls)
    assert all(b - a >= 3.0 for a, b in zip(times, times[1:], strict=False)), times


# ══ AT-960-8-E-1：GitHub 權杖只在抓取行程內 ═══════════════════════════════════════════════════
def test_AT_960_8_E_1_the_token_goes_out_only_as_an_authorization_header_to_github(
        monkeypatch: pytest.MonkeyPatch) -> None:
    def no_spawn(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("抓取不得起任何子行程")

    monkeypatch.setattr(subprocess, "Popen", no_spawn)
    rig = make_rig(chain({
        "/repos/a/b": json_reply('{"ok": 1}'), "/hop": redirect_to("https://arxiv.org/x"),
        "/x": json_reply("{}")}), github_token=f"  {SENTINEL}  ")
    rig.client.fetch("https://api.github.com/repos/a/b", layer="OSS")
    rig.client.fetch("https://api.github.com/hop", layer="OSS")
    auth = [(c.host_header, c.authorization) for c in rig.calls]
    bearer = f"Bearer {SENTINEL}"
    assert auth == [("api.github.com", bearer), ("api.github.com", bearer),
                    ("arxiv.org", None)], "重導到別的 host 的那一跳不帶權杖"
    assert all(c.headers["accept"] == "application/vnd.github+json"
               for c in rig.calls if c.host_header == "api.github.com")
    assert SENTINEL not in repr(rig.client)


def test_AT_960_8_E_1_the_token_is_masked_everywhere_a_reflecting_server_could_put_it(
        rdb: ThrowawayDb, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    store, rid = make_project(rdb, tmp_path)
    audit_path = tmp_path / "_audit.jsonl"
    caplog.set_level(logging.DEBUG)

    def reflect(call: Call) -> Reply:
        echo = call.authorization or ""
        if call.path == "/err":
            return Reply(raises=httpx.ConnectError(f"proxy rejected: {echo}"))
        if call.path == "/401":
            return json_reply(f'{{"message": "Bad credentials", "echo": "{echo}"}}', status=401)
        if call.path == "/split":
            return Reply(raises=httpx.ConnectError("x" * 150 + echo))
        return json_reply(f'{{"echo": "{echo}", "token": "{SENTINEL}"}}')

    rig = make_rig(reflect, github_token=SENTINEL, audit=AuditLog(audit_path))
    records = []
    for path in ("/ok", "/401", "/err", "/split"):
        records += rig.client.fetch(f"https://api.github.com{path}", layer="OSS").records
    workspace = tmp_path / "ws"
    for record in records:
        store.insert_fetch(research_id=rid, fetch=record.to_db())
        land_raw(workspace, record)
    assert [r.outcome for r in records] == ["OK", "HTTP_ERROR", "HTTP_ERROR", "HTTP_ERROR"]
    surfaces = {
        "records": json.dumps([vars(r) for r in records], ensure_ascii=False, default=str),
        "to_db": json.dumps([r.to_db() for r in records], ensure_ascii=False, default=str),
        "audit": audit_path.read_text(encoding="utf-8"),
        "logs": caplog.text,
        "files": "\n".join(p.read_text(encoding="utf-8") for p in workspace.rglob("*.txt")),
        "db": json.dumps(rdb.q("SELECT row_to_json(f)::text FROM console.research_fetches f"),
                         ensure_ascii=False),
        "events": json.dumps(rdb.q("SELECT payload::text FROM console.research_events")),
    }
    for name, text in surfaces.items():
        assert SENTINEL not in text, f"權杖出現在 {name}"
        assert "ghp_" not in text, f"權杖的殘片出現在 {name}"
    assert "[REDACTED]" in surfaces["records"], "被遮蔽而不是被丟掉"
    assert "research fetch" in caplog.text and audit_path.read_text(encoding="utf-8")


# ══ AT-960-8-E-3：深度上界 ═════════════════════════════════════════════════════════════════
def candidates(per_layer: int, layers: tuple[str, ...] = ("ACADEMIC", "OSS", "COMMUNITY")
               ) -> list[FetchTask]:
    return [FetchTask("arxiv" if layer == "ACADEMIC" else "github", layer,
                      f"https://api.github.com/{layer.lower()}/{n}")
            for layer in layers for n in range(per_layer)]


@pytest.mark.parametrize(("depth", "per_layer", "total"), [
    ("QUICK", 5, 15), ("STANDARD", 10, 30), ("DEEP", 20, 60)])
def test_AT_960_8_E_3_each_depth_level_caps_sources_per_layer_and_fetches_per_run(
        depth: str, per_layer: int, total: int) -> None:
    assert (DEPTH_LIMITS[depth].per_layer, DEPTH_LIMITS[depth].total) == (per_layer, total)
    plan = plan_fetches(candidates(per_layer + 3), effective_limits(depth))
    by_layer = {layer: sum(1 for t in plan.accepted if t.layer == layer)
                for layer in ("ACADEMIC", "OSS", "COMMUNITY")}
    assert by_layer == {"ACADEMIC": per_layer, "OSS": per_layer, "COMMUNITY": per_layer}
    assert len(plan.accepted) == total and len(plan.skipped) == 9
    assert {s.limit for s in plan.skipped} == {"per_layer"}
    assert all(s.to_payload()["reason"] == "skipped:over_limit" for s in plan.skipped)
    assert "skipped:over_limit" not in OUTCOMES, "不佔 research_fetches 的 outcome 列舉"
    assert plan.skipped[0].to_payload() == {
        "reason": "skipped:over_limit", "layer": "ACADEMIC", "kind": "arxiv",
        "url": f"https://api.github.com/academic/{per_layer}", "limit": "per_layer"}


def test_AT_960_8_E_3_the_run_wide_cap_binds_when_more_layers_compete() -> None:
    layers = ("ACADEMIC", "OSS", "COMMUNITY", "INDUSTRY")
    plan = plan_fetches(candidates(5, layers), effective_limits("QUICK"))
    assert len(plan.accepted) == 15 and len(plan.skipped) == 5
    assert {s.limit for s in plan.skipped} == {"total"} and {s.layer for s in plan.skipped} == {
        "INDUSTRY"}
    assert len(plan_fetches(candidates(2), effective_limits("QUICK")).skipped) == 0


def test_AT_960_8_E_3_a_request_can_only_lower_the_limits_never_raise_them() -> None:
    assert effective_limits("STANDARD", 50, 500) == effective_limits("STANDARD")
    assert (effective_limits("STANDARD", 3, 7).per_layer, effective_limits("STANDARD", 3, 7).total
            ) == (3, 7)
    assert effective_limits("DEEP", None, 12).per_layer == 20
    assert effective_limits("QUICK", 0, 0).total == 0
    plan = plan_fetches(candidates(8), effective_limits("STANDARD", 3, 100))
    assert len(plan.accepted) == 9 and all(
        sum(1 for t in plan.accepted if t.layer == layer) == 3
        for layer in ("ACADEMIC", "OSS", "COMMUNITY"))
    for bad in (-1, True, 1.5, "3"):
        with pytest.raises(ValueError):
            effective_limits("QUICK", bad)                   # type: ignore[arg-type]
    with pytest.raises(ValueError):
        effective_limits("EXTREME")


def test_AT_960_8_E_3_run_prefetch_never_fetches_more_than_the_cap_and_records_the_skips(
) -> None:
    rig = make_rig(lambda call: Reply(404))
    tasks = [FetchTask("arxiv", "ACADEMIC", arxiv.search_url(f"term{n}", max_results=5))
             for n in range(8)]
    batch = run_prefetch(rig.client, tasks, depth_level="QUICK", requested_per_layer=3)
    assert len(rig.calls) == 3 and batch.planned == 3 and len(batch.skipped) == 5
    assert [s.limit for s in batch.skipped] == ["per_layer"] * 5
    deeper = make_rig(lambda call: Reply(404))
    many = [FetchTask("arxiv" if n % 2 else "github", "ACADEMIC" if n % 2 else "OSS",
                      arxiv.search_url("x", max_results=1) if n % 2 else github.search_url(
                          "x", per_page=1)) for n in range(40)]
    run_prefetch(deeper.client, many, depth_level="QUICK", requested_total=4)
    assert len(deeper.calls) == 4


# ══ run_prefetch 的升級抓取（arXiv HTML 升 V3、GitHub 預設分支 HEAD）══════════════════════════════
def upgrade_script(call: Call) -> Reply:
    if call.path.startswith("/api/query"):
        return text_reply(fixture_bytes("arxiv_golden.xml"), "application/atom+xml")
    if call.path == "/html/2401.00001v2":
        return text_reply("<html>full text</html>", "text/html")
    if call.path.startswith("/search/repositories"):
        return text_reply(fixture_bytes("github_golden.json"), "application/json")
    if call.path == "/repos/example-org/example-lib/branches/main":
        return text_reply(fixture_bytes("github_head_golden.json"), "application/json")
    return Reply(404)


NOW = datetime(2026, 11, 2, tzinfo=UTC)         # GitHub 活躍判準的基準（不隨測試執行日漂移）


def test_run_prefetch_upgrades_arxiv_to_v3_and_github_to_a_commit_anchor() -> None:
    rig = make_rig(upgrade_script)
    tasks = [FetchTask("arxiv", "ACADEMIC", arxiv.search_url("gc", max_results=5)),
             FetchTask("github", "OSS", github.search_url("gc", per_page=5))]
    batch = run_prefetch(rig.client, tasks, depth_level="QUICK", now=NOW)
    by_url = {b.source["url"]: b for b in batch.sources}
    first = by_url["https://arxiv.org/abs/2401.00001v2"]
    second = by_url["https://arxiv.org/abs/cs/0112017v1"]
    assert first.source["verification"] == "V3" and second.source["verification"] == "V2", \
        "有 HTML 全文才 V3；沒有 HTML 版者維持 V2（不取 PDF）"
    lib = by_url["https://github.com/example-org/example-lib"]
    old = by_url["https://github.com/old-user/old-tool"]
    assert (lib.source["anchor_kind"], lib.source["verification"]) == ("COMMIT", "V3")
    assert lib.source["git_commit"] == "0123456789abcdef0123456789abcdef01234567"
    assert old.source["git_commit"] == "未見", "不達標的 repo 不花抓取次數"
    upgraded = first.records[-1]
    assert upgraded.url == "https://arxiv.org/html/2401.00001v2" and upgraded.source_id == first.id
    assert upgraded in batch.records and len(first.records) == 2
    assert len(second.records) == 1, "沒有 HTML 版：升級抓取失敗，來源仍只有列表那一筆證據"
    paths = [c.path for c in rig.calls]
    assert not any("pdf" in p for p in paths) and len(paths) == 5, paths
    assert batch.no_sources is False and batch.skipped == []


def test_run_prefetch_stops_upgrading_when_the_run_budget_is_used_up() -> None:
    rig = make_rig(upgrade_script)
    tasks = [FetchTask("arxiv", "ACADEMIC", arxiv.search_url("gc", max_results=5))]
    batch = run_prefetch(rig.client, tasks, depth_level="QUICK", requested_total=2)
    assert len(rig.calls) == 2, "1 次列表＋1 次升級；第二個候選的升級用不到額度"
    assert [s.limit for s in batch.skipped] == ["total"]
    plain = make_rig(upgrade_script)
    run_prefetch(plain.client, tasks, depth_level="QUICK", enrich=False)
    assert len(plain.calls) == 1


def test_run_prefetch_a_failed_upgrade_keeps_the_source_at_its_listing_level() -> None:
    rig = make_rig(lambda call: upgrade_script(call) if call.path.startswith("/api/query")
                   else Reply(404))
    batch = run_prefetch(rig.client, [FetchTask(
        "arxiv", "ACADEMIC", arxiv.search_url("gc", max_results=5))], depth_level="QUICK")
    assert {b.source["verification"] for b in batch.sources} == {"V2"}
    assert [r.outcome for r in batch.records] == ["OK", "HTTP_ERROR", "HTTP_ERROR"]
    broken = make_rig(lambda call: text_reply('{"commit": null}', "application/json")
                      if "/branches/" in call.path else upgrade_script(call))
    got = run_prefetch(broken.client, [FetchTask(
        "github", "OSS", github.search_url("gc", per_page=5))], depth_level="QUICK", now=NOW)
    lib = next(b for b in got.sources if b.source["title"] == "example-org/example-lib")
    assert lib.source["git_commit"] == "未見" and lib.source["verification"] == "V2"
    assert got.records[-1].outcome == "PARSE_ERROR" and "sha" in got.records[-1].detail


def test_run_prefetch_trims_each_layer_to_the_per_layer_cap_and_records_the_overflow() -> None:
    rig = make_rig(upgrade_script)
    batch = run_prefetch(rig.client, [FetchTask(
        "arxiv", "ACADEMIC", arxiv.search_url("gc", max_results=5))], depth_level="QUICK",
        requested_per_layer=1, enrich=False)
    assert [b.source["url"] for b in batch.sources] == ["https://arxiv.org/abs/2401.00001v2"]
    assert [(s.limit, s.url) for s in batch.skipped] == [
        ("per_layer", "https://arxiv.org/abs/cs/0112017v1")]


def test_effective_allowlist_shape_and_snapshot() -> None:
    allowlist = build_effective_allowlist(
        ["Export.Arxiv.Org.", "bad host", "arxiv.org"],
        [admin_entry("Docs.Example.com.", 7), admin_entry("off.example.com", enabled=False),
         {"list_kind": "WEB", "host": "web.example.com", "enabled": True,
          "min_interval_seconds": 5}])
    assert isinstance(allowlist, EffectiveAllowlist)
    assert allowlist.hosts == ("export.arxiv.org", "arxiv.org", "docs.example.com")
    assert allowlist.snapshot() == [
        {"host": "export.arxiv.org", "list_kind": "FETCH", "source": "ENV", "layer": None,
         "min_interval_seconds": 3},
        {"host": "arxiv.org", "list_kind": "FETCH", "source": "ENV", "layer": None,
         "min_interval_seconds": 3},
        {"host": "docs.example.com", "list_kind": "FETCH", "source": "ADMIN", "layer": "INDUSTRY",
         "min_interval_seconds": 7}]
