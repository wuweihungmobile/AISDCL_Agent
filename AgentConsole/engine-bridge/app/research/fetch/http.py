"""研究抓取的 HTTP 客戶端：釘 IP、逐跳重驗、有界讀取、對來源的禮貌（ADR-003 D7；NFR-R2P-02／03）。

`FetchClient.fetch(url, layer=…)` 是整個 Bridge 唯一的研究外呼入口，流程（每一跳）：
  1. `check_research_url`（`allowlist.py`）：精確 host、僅 https、僅 443、拒尾點、**解析一次**且
     全部位址皆為全域公網位址——任何一關不過就拒絕並留一筆 `DENIED_*` 紀錄，**零連線**。
  2. 以**已驗證的 IP** 連線（`PIN_MODE`，V-R4 結論見下）：請求網址的 host 換成 IP，`Host` 標頭與
     TLS SNI（httpx 的 `sni_hostname` 請求擴充）仍是原 hostname，所以憑證照原 hostname 驗證，而
     DNS 第二次回答什麼都影響不了連線（rebinding 防線）。`follow_redirects=False`；每跳新連線、
     不重用（同一 IP 後面可能是不同 hostname，重用連線會讓 TLS 身分混淆）。
  3. 重導（301／302／303／307／308）不自動跟隨：下一跳從第 1 關重來，最多 `MAX_REDIRECTS` 跳，
     超過判 `HTTP_ERROR`；每一跳各留一筆紀錄；Authorization 只在目標 host 是 `api.github.com`
     的那一跳才帶。
  4. 有界讀取：文字類 content-type、回應上限 `max_bytes`（含解壓後；壓縮炸彈由有上限的 inflate
     擋）、牆鐘 `timeout_seconds`；超界一律失敗、**不截斷**；非文字（PDF／二進位）拒收。
  5. 禮貌（`HostThrottle`）：同一節流群組兩次請求至少相隔有效 `min_interval_seconds`（從上一個
     請求**結束**起算）、同一時刻至多一條連線（arXiv 的規定）、遵守 `Retry-After`／
     `X-RateLimit-*`／Stack Exchange 的 `backoff`（取較嚴者）；429 記 `RATE_LIMITED`，退避後
     同一跳最多再試一次。

V-R4 結論（`PIN_MODE`）：**可行**，採 `pinned_ip_sni`。依據＝httpx 0.28.1／httpcore 的
`sni_hostname` 請求擴充（TLS `server_hostname`）加明設的 `Host` 標頭；測試以本機 TCP 假伺服器在
線路上讀到 ClientHello 的 SNI＝原 hostname、對端位址＝釘住的位址（`test_research_fetch_security.py`
的 AT_960_8_3 線路層案例）。不需要退回「解析後比對 IP 非私網」。

時間與睡眠一律可注入（`clock`／`epoch`／`sleeper`）：測試用假時鐘，不真的等待。GitHub 權杖只存在
`FetchClient` 內，只以 Authorization 標頭送出；進入紀錄、日誌與錯誤訊息的文字都先遮蔽它。
"""
from __future__ import annotations

import codecs
import hashlib
import json
import logging
import re
import socket
import threading
import time
import uuid
import zlib
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from dataclasses import replace as _clone
from datetime import date
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlsplit

import httpx

from ...security import AuditLog
from ...settings import RESEARCH_DEFAULT_FETCH_MAX_BYTES, RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS
from ...tracing import trace_id_var
from .allowlist import (
    DENIED_ALLOWLIST,
    DENIED_PRIVATE_IP,
    GITHUB_HOST,
    HTTP_ERROR,
    LAYERS,
    EffectiveAllowlist,
    Resolver,
    UrlCheck,
    build_effective_allowlist,
    check_research_url,
    db_safe_text,
    stored_url,
    throttle_group,
)

if TYPE_CHECKING:
    from ...settings import Settings

logger = logging.getLogger("bridge.research.fetch")

# ── 常數（測試與產品碼共用，TCS §5.1）─────────────────────────────────────────────────────────
OK = "OK"
TIMEOUT = "TIMEOUT"
TOO_LARGE = "TOO_LARGE"
PARSE_ERROR = "PARSE_ERROR"
RATE_LIMITED = "RATE_LIMITED"
#: `research_fetches.outcome` 的列舉（V17 的 CHECK；測試逐值對拍 DDL）。
OUTCOMES = (OK, DENIED_ALLOWLIST, DENIED_PRIVATE_IP, HTTP_ERROR, TIMEOUT, TOO_LARGE, PARSE_ERROR,
            RATE_LIMITED)

#: V-R4 結論：`pinned_ip_sni`（連已驗證 IP、Host 與 SNI 為原 hostname）｜`resolve_then_check`。
PIN_MODE = "pinned_ip_sni"
MAX_REDIRECTS = 3
#: 文字類 content-type（初值；NFR-R2P-03-2）。其餘一律拒收（PDF／二進位）。
TEXT_CONTENT_TYPES = frozenset({
    "text/html", "text/plain", "text/markdown", "application/json", "application/atom+xml"})
USER_AGENT = "AISDLC-AgentConsole-Research/1.0 (Bridge research fetcher; rate-limited, read-only)"
FETCH_METHOD = "API"            # Bridge 自己的 HTTP GET（WEB_* 方法只屬 agent 宣告的 Web 層）
OBSERVED_BY = "BRIDGE"
RAW_DIR_REL = "00_research/raw"
#: 限流訊號要求等待超過這個秒數時不睡眠、也不連線（直接記 `RATE_LIMITED`，視窗過了才再連）。
MAX_RATE_WAIT_SECONDS = 300.0
#: 429 沒有任何限流訊號時的退避秒數下限。
DEFAULT_BACKOFF_SECONDS = 10.0
#: 解析到多個公網位址時最多嘗試幾個（連線失敗才換下一個；全部都是驗證過的位址）。
MAX_CONNECT_ADDRESSES = 3
CHUNK_BYTES = 65_536
MISSING = "未見"
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_REDACTED = "[REDACTED]"

#: `research_sources` 的可入庫欄位（V17 DDL 的描述欄；不含 id、source_no、first_fetched_at）。
SOURCE_COLUMNS = ("layer", "tier", "verification", "anchor_kind", "url", "doi", "git_commit",
                  "title", "authors_org", "published_at", "source_type", "license_spdx",
                  "license_note", "clue_only")
#: 這些欄位在 DB 是可為 NULL 的型別欄（DATE／帶 CHECK 的 VARCHAR）：缺值入庫時 `未見` 轉 NULL。
_NULLABLE_COLUMNS = ("doi", "git_commit", "published_at", "license_spdx")


def system_resolver(host: str) -> list[str]:
    """正式解析器：系統 `getaddrinfo`（回全部位址、去重保序）。測試一律注入假解析器。"""
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


# ── 資料形狀 ────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class FetchRecord:
    """一筆抓取紀錄＝`research_fetches` 的一列（含被拒者與重導的每一跳；`to_db()` 即入庫形狀）。

    `raw_text` 是落地的原文（純文字、已遮蔽權杖）；`raw_sha256`／`raw_bytes` 是它 UTF-8 位元組的
    摘要與長度（原文檔 `00_research/raw/<sha12>.txt` 的內容恰好就是它）。`detail` 是給人看的原因，
    DDL 沒有對應欄位，不入庫。"""

    layer: str
    url: str
    host: str
    outcome: str
    http_status: int | None = None
    raw_text: str | None = None
    raw_sha256: str | None = None
    raw_bytes: int | None = None
    duration_ms: int | None = None
    query_text: str | None = None
    detail: str = ""
    source_id: str | None = None
    stage_run_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    fetch_method: str = FETCH_METHOD
    observed_by: str = OBSERVED_BY

    @property
    def raw_rel_path(self) -> str | None:
        return f"{RAW_DIR_REL}/{self.raw_sha256[:12]}.txt" if self.raw_sha256 else None

    def to_db(self) -> dict[str, Any]:
        """`ResearchDb.insert_fetch(research_id=…, fetch=<這個>)` 的 `fetch` 引數。"""
        return {
            "id": self.id, "source_id": self.source_id, "stage_run_id": self.stage_run_id,
            "layer": self.layer, "fetch_method": self.fetch_method, "observed_by": self.observed_by,
            "host": self.host, "url": self.url, "query_text": self.query_text,
            "http_status": self.http_status, "outcome": self.outcome,
            "raw_rel_path": self.raw_rel_path, "raw_sha256": self.raw_sha256,
            "raw_bytes": self.raw_bytes, "duration_ms": self.duration_ms}


@dataclass(frozen=True)
class FetchResult:
    """一次 `fetch()` 的結果：`records` 依序是每一跳／每次嘗試的紀錄；`terminal`（最後一筆）就是
    起點 URL 的終態結果（成功時帶原文）。"""

    url: str
    records: tuple[FetchRecord, ...]

    @property
    def terminal(self) -> FetchRecord:
        return self.records[-1]

    @property
    def ok(self) -> bool:
        return self.terminal.outcome == OK and self.terminal.raw_text is not None

    @property
    def text(self) -> str | None:
        return self.terminal.raw_text if self.ok else None


@dataclass(frozen=True)
class ParseResult:
    """四個解析器的共同輸出。`ok` 為假＝壞格式（`PARSE_ERROR`），此時**不產生任何來源列**。
    `sources` 的每一筆是「觀測形態」的來源列：`SOURCE_COLUMNS` 全在，適用但缺值的描述欄寫 `未見`、
    不適用的欄寫 None，另帶各來源專屬的附加欄（如 stars）；入庫前以 `to_db_source_row` 轉換。"""

    ok: bool
    sources: tuple[dict[str, Any], ...] = ()
    detail: str = ""

    @classmethod
    def error(cls, detail: str) -> ParseResult:
        return cls(False, (), detail)


def clean_text(value: Any) -> str:
    """解析器的文字欄消毒：非字串或清空後為空＝`未見`；控制字元與連續空白收成單一空格。"""
    if not isinstance(value, str):
        return MISSING
    printable = "".join(ch if ch.isprintable() or ch.isspace() else " " for ch in value)
    return " ".join(printable.split()) or MISSING


def iso_date(value: Any) -> str:
    """`YYYY-MM-DD` 開頭且是真實存在的日期才回該 10 字元，否則 `未見`（DATE 欄不接受壞值）。"""
    if isinstance(value, str) and re.match(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            return MISSING
    return MISSING


def to_db_source_row(obs: Mapping[str, Any]) -> dict[str, Any]:
    """觀測形態 → `research_sources` 可入庫形態：只留 `SOURCE_COLUMNS`；可為 NULL 的型別欄
    （doi、git_commit、published_at、license_spdx）的 `未見` 轉 None，其餘文字欄保留 `未見`。"""
    row = {col: obs.get(col) for col in SOURCE_COLUMNS}
    for col in _NULLABLE_COLUMNS:
        if row[col] == MISSING:
            row[col] = None
    return row


# ── 對來源的禮貌 ────────────────────────────────────────────────────────────────────────────
class RateWindowClosed(Exception):
    """限流視窗還要等很久（超過 `MAX_RATE_WAIT_SECONDS`）：不睡眠、不連線。"""

    def __init__(self, wait: float) -> None:
        super().__init__(f"限流視窗尚未重置，還需 {wait:.0f} 秒")
        self.wait = wait


class HostThrottle:
    """節流群組的時間線與互斥：同一群組同一時刻至多一個請求在跑（arXiv 的單一連線規定；對其他
    host 也無害），兩次請求至少相隔 `interval`（從上一個請求結束起算）。`defer` 登記限流訊號要求的
    額外等待。時鐘與睡眠可注入。"""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep,
                 max_wait: float = MAX_RATE_WAIT_SECONDS) -> None:
        self._clock, self._sleeper, self._max_wait = clock, sleeper, max_wait
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}
        self._next_at: dict[str, float] = {}
        self._blocked_until: dict[str, float] = {}

    @contextmanager
    def slot(self, group: str, interval: float) -> Iterator[None]:
        with self._guard:
            lock = self._locks.setdefault(group, threading.Lock())
        with lock:
            now = self._clock()
            blocked = self._blocked_until.get(group, 0.0) - now
            if blocked > self._max_wait:
                raise RateWindowClosed(blocked)
            wait = max(self._next_at.get(group, 0.0), self._blocked_until.get(group, 0.0)) - now
            if wait > 0:
                self._sleeper(wait)
            try:
                yield
            finally:
                with self._guard:
                    self._next_at[group] = max(self._next_at.get(group, 0.0),
                                               self._clock() + interval)

    def defer(self, group: str, seconds: float) -> None:
        with self._guard:
            self._blocked_until[group] = max(self._blocked_until.get(group, 0.0),
                                             self._clock() + max(seconds, 0.0))


#: 行程內共用的節流時間線：研究 run 一個接一個建新的 `FetchClient`，arXiv 的「每 3 秒一個請求」限制
#: 卻是對同一操作者的全部請求，所以正式路徑（`FetchClient.from_settings`）一律共用這一條。
SHARED_THROTTLE = HostThrottle()


def _retry_after_seconds(value: str, epoch_now: float) -> float | None:
    text = value.strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    try:
        return max(parsedate_to_datetime(text).timestamp() - epoch_now, 0.0)
    except (TypeError, ValueError, IndexError):
        return None


def signal_wait_seconds(headers: Mapping[str, str], epoch_now: float) -> float | None:
    """回應標頭的限流訊號要求等待幾秒（取較嚴者；沒有訊號回 None）：`Retry-After`（秒數或 HTTP
    日期）與「`X-RateLimit-Remaining` 為 0 時的 `X-RateLimit-Reset`」（GitHub 為 epoch 秒；小於
    10^9 的值視為相對秒數）。`headers` 須是不分大小寫的映射（httpx.Headers）。"""
    waits: list[float] = []
    retry_after = headers.get("retry-after")
    if retry_after:
        parsed = _retry_after_seconds(retry_after, epoch_now)
        if parsed is not None:
            waits.append(parsed)
    remaining, reset = headers.get("x-ratelimit-remaining"), headers.get("x-ratelimit-reset")
    if remaining is not None and remaining.strip() == "0" and reset:
        try:
            value = float(reset.strip())
        except ValueError:
            value = -1.0
        if value >= 0:
            waits.append(max(value - epoch_now, 0.0) if value >= 1e9 else value)
    return max(waits) if waits else None


def body_backoff_seconds(text: str) -> float | None:
    """Stack Exchange 把限流要求放在 JSON 本文的頂層 `backoff`（秒）。非 JSON 或沒有該欄回 None。"""
    if '"backoff"' not in text:
        return None
    try:
        value = json.loads(text).get("backoff")
    except (ValueError, AttributeError):
        return None
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


# ── 有界讀取 ────────────────────────────────────────────────────────────────────────────────
class _TooLarge(Exception):
    pass


class _BodyTimeout(Exception):
    pass


class _BadBody(Exception):
    pass


class _Inflater:
    """有上限的 gzip／deflate 解壓：每次只允許再吐出「剩餘額度加一位元組」，多出的那一個位元組就是
    超界證據（壓縮炸彈在這裡被擋，不會先在記憶體展開）。"""

    def __init__(self, encoding: str) -> None:
        self._inflater = zlib.decompressobj(zlib.MAX_WBITS | (16 if encoding == "gzip" else 0))

    def feed(self, data: bytes, room: int) -> bytes:
        try:
            out = self._inflater.decompress(data, room + 1)
        except zlib.error as exc:
            raise _BadBody(f"壓縮內容損毀（{exc}）") from exc
        if self._inflater.unconsumed_tail:
            raise _TooLarge
        return out

    def finish(self) -> None:
        if not self._inflater.eof:
            raise _BadBody("壓縮內容不完整（串流提前結束）")


def _media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def decode_text(body: bytes, content_type: str) -> str:
    """位元組 → 文字：charset 取 content-type 的宣告（不認得就 UTF-8），非法位元組以替代字元取代
    （不丟例外）；UTF-8 BOM 去掉，免得 JSON 解析失敗。"""
    charset = "utf-8"
    found = re.search(r"charset\s*=\s*\"?([A-Za-z0-9_.:-]+)", content_type, re.IGNORECASE)
    if found:
        try:
            charset = codecs.lookup(found.group(1)).name
        except LookupError:
            charset = "utf-8"
    if charset == "utf-8" and body.startswith(b"\xef\xbb\xbf"):
        charset = "utf-8-sig"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:              # 例如宣告成 zlib 這類不是文字編碼的 codec
        return body.decode("utf-8", errors="replace")


# ── 客戶端 ──────────────────────────────────────────────────────────────────────────────────
def _default_transport() -> httpx.BaseTransport:
    return httpx.HTTPTransport(limits=httpx.Limits(max_keepalive_connections=0), retries=0)


@dataclass(frozen=True)
class _Req:
    """一次請求的脈絡（單跳）：網址、已通過的檢查、層、查詢字串、節流群組與有效間隔。"""

    url: str
    check: UrlCheck
    layer: str
    query_text: str | None
    group: str
    interval: int

    @property
    def host(self) -> str:
        return self.check.host


@dataclass(frozen=True)
class _Hop:
    """單次請求的結果：紀錄、可跟隨的下一個網址（只有重導且 outcome 為 OK 時才有）。"""

    record: FetchRecord
    next_url: str | None = None


class FetchClient:
    """見模組說明。`allowlist` 是這個 stage run 的有效清單；`resolver`／`transport_factory`／
    `clock`／`epoch`／`sleeper` 皆可注入（測試用假的）；`github_token` 只用於 `api.github.com`。"""

    def __init__(self, *, allowlist: EffectiveAllowlist, resolver: Resolver = system_resolver,
                 max_bytes: int = RESEARCH_DEFAULT_FETCH_MAX_BYTES,
                 timeout_seconds: float = RESEARCH_DEFAULT_FETCH_TIMEOUT_SECONDS,
                 github_token: str | None = None,
                 transport_factory: Callable[[], httpx.BaseTransport] = _default_transport,
                 clock: Callable[[], float] = time.monotonic,
                 epoch: Callable[[], float] = time.time,
                 sleeper: Callable[[float], None] = time.sleep,
                 throttle: HostThrottle | None = None, audit: AuditLog | None = None,
                 user_agent: str = USER_AGENT) -> None:
        self._allowlist, self._resolver = allowlist, resolver
        self._max_bytes, self._timeout = max_bytes, timeout_seconds
        self._token = (github_token or "").strip() or None
        self._transport_factory = transport_factory
        self._clock, self._epoch = clock, epoch
        self._throttle = throttle or HostThrottle(clock=clock, sleeper=sleeper)
        self._audit, self._user_agent = audit, user_agent

    @classmethod
    def from_settings(cls, cfg: Settings, *, allowlist: EffectiveAllowlist | None = None,
                      **kwargs: Any) -> FetchClient:
        """依 `Settings` 建客戶端：回應上限與逾時取自 `BRIDGE_RESEARCH_FETCH_*`；清單缺省＝基底；
        節流時間線缺省共用行程內的 `SHARED_THROTTLE`。"""
        kwargs.setdefault("throttle", SHARED_THROTTLE)
        return cls(allowlist=allowlist or build_effective_allowlist(cfg.research_fetch_allowlist),
                   max_bytes=cfg.research_fetch_max_bytes,
                   timeout_seconds=cfg.research_fetch_timeout_seconds, **kwargs)

    @property
    def throttle(self) -> HostThrottle:
        return self._throttle

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    # ── 公開入口 ──────────────────────────────────────────────────────────────────────────
    def fetch(self, url: str, *, layer: str, query_text: str | None = None) -> FetchResult:
        """對 `url` 發一次研究抓取（含重導的每一跳）。每種失敗都是一筆帶 outcome 的紀錄、不丟例外；
        只有呼叫端的程式錯誤（`layer` 不在列舉內）丟 `ValueError`，免得壞值等到入庫才撞 CHECK。"""
        if layer not in LAYERS:
            raise ValueError(f"layer 須為 {'、'.join(LAYERS)}：{layer!r}")
        query_text = db_safe_text(query_text) if query_text is not None else None
        records: list[FetchRecord] = []
        current, followed = url, 0
        while True:
            check = check_research_url(current, self._allowlist.hosts, self._resolver)
            if not check.ok:
                records.append(self._denied(layer, current, check, query_text))
                break
            req = self._req(current, check, layer, query_text)
            hops = self._attempts(req)
            records += [h.record for h in hops[:-1]]
            last = hops[-1]
            if last.next_url is not None and followed >= MAX_REDIRECTS:
                records.append(_clone(
                    last.record, outcome=HTTP_ERROR,
                    detail=f"超過 {MAX_REDIRECTS} 跳重導，不再跟隨（重導不自動跟隨，每跳重驗）"))
                break
            records.append(last.record)
            if last.next_url is None:
                break
            current, followed = last.next_url, followed + 1
        for record in records:
            self._audit_record(record)
        return FetchResult(url, tuple(records))

    # ── 單跳：節流、連線、判定 ────────────────────────────────────────────────────────────
    def _req(self, url: str, check: UrlCheck, layer: str, query_text: str | None) -> _Req:
        host = check.host
        authenticated = bool(self._token) and host == GITHUB_HOST
        interval = self._allowlist.interval(host, urlsplit(url).path or "/",
                                            authenticated=authenticated)
        return _Req(url, check, layer, query_text, throttle_group(host), interval)

    def _attempts(self, req: _Req) -> list[_Hop]:
        """一跳的全部嘗試：429（或帶限流訊號的 403）退避後同一跳最多再試一次，不重試風暴。"""
        hops = [self._request(req)]
        first = hops[0].record
        if first.outcome == RATE_LIMITED and first.http_status is not None:
            retry = self._request(req)                 # 退避由節流槽等待完成（過長則不連線）
            if retry.record.http_status is not None:
                hops.append(retry)
        return hops

    def _request(self, req: _Req) -> _Hop:
        try:
            with self._throttle.slot(req.group, req.interval):
                started = self._clock()
                hop = self._exchange(req, started)
                return _Hop(_clone(hop.record, duration_ms=int((self._clock() - started) * 1000)),
                            hop.next_url)
        except RateWindowClosed as exc:
            return _Hop(FetchRecord(req.layer, db_safe_text(req.url), req.host, RATE_LIMITED,
                                    query_text=req.query_text, detail=f"{exc}；本次不連線"))

    def _exchange(self, req: _Req, started: float) -> _Hop:
        """連線並判定回應；任何失敗（含逾時、傳輸錯誤）都轉成帶 outcome 的紀錄。"""
        try:
            with self._open(req) as response:
                return self._judge(req, response, started)
        except httpx.TimeoutException:
            return self._hop(req, TIMEOUT, detail=f"連線或讀取逾時（上限 {self._timeout:g} 秒）")
        except httpx.HTTPError as exc:
            message = self._redact(str(exc))[:160]        # 先遮蔽再截斷：權杖不會被截成殘片
            return self._hop(req, HTTP_ERROR, detail=f"傳輸錯誤：{type(exc).__name__}：{message}")

    def _judge(self, req: _Req, response: httpx.Response, started: float) -> _Hop:
        status, headers = response.status_code, response.headers
        wait = signal_wait_seconds(headers, self._epoch())
        if wait is not None:
            self._throttle.defer(req.group, wait)
        if status in _REDIRECT_STATUSES:
            location = (headers.get("location") or "").strip()
            if not location:
                return self._hop(req, HTTP_ERROR, status, detail=f"HTTP {status} 重導缺 Location")
            try:
                target = urljoin(req.url, location)
            except ValueError:               # 例如 `http://[::1` 這類無法解析的網址
                return self._hop(req, HTTP_ERROR, status,
                                 detail=f"HTTP {status} 的 Location 無法解析")
            return self._hop(req, OK, status, detail=f"重導至 {stored_url(target)}",
                             next_url=target)
        if status == 429 or (status == 403 and wait is not None):
            if wait is None:
                self._throttle.defer(req.group, max(float(req.interval), DEFAULT_BACKOFF_SECONDS))
            return self._hop(req, RATE_LIMITED, status, detail="來源回報限流，退避後最多再試一次")
        if not 200 <= status < 300:
            return self._hop(req, HTTP_ERROR, status, detail=f"HTTP {status}")
        content_type = headers.get("content-type", "")
        media = _media_type(content_type)
        if media not in TEXT_CONTENT_TYPES:
            return self._hop(req, PARSE_ERROR, status,
                             detail=f"非文字回應（Content-Type：{media or '缺'}），拒收不落地")
        declared = headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            return self._hop(req, TOO_LARGE, status,
                             detail=f"Content-Length {declared} 超過上限 {self._max_bytes}")
        try:
            body = self._read_body(response, started)
        except _TooLarge:
            return self._hop(req, TOO_LARGE, status,
                             detail=f"回應超過上限 {self._max_bytes} 位元組，不截斷")
        except _BodyTimeout:
            return self._hop(req, TIMEOUT, status,
                             detail=f"讀取逾時（牆鐘上限 {self._timeout:g} 秒）")
        except _BadBody as exc:
            return self._hop(req, PARSE_ERROR, status, detail=str(exc))
        except httpx.TimeoutException:
            return self._hop(req, TIMEOUT, status, detail=f"讀取逾時（上限 {self._timeout:g} 秒）")
        except httpx.HTTPError as exc:
            return self._hop(req, HTTP_ERROR, status, detail=f"讀取錯誤：{type(exc).__name__}")
        text = self._redact(decode_text(body, content_type))
        if len(text.encode("utf-8")) > self._max_bytes:
            return self._hop(req, TOO_LARGE, status,
                             detail=f"解碼後超過上限 {self._max_bytes} 位元組")
        backoff = body_backoff_seconds(text)
        if backoff is not None:
            self._throttle.defer(req.group, backoff)
        return self._hop(req, OK, status, text=text)

    def _hop(self, req: _Req, outcome: str, status: int | None = None, *, detail: str = "",
             text: str | None = None, next_url: str | None = None) -> _Hop:
        encoded = text.encode("utf-8") if text is not None else None
        return _Hop(FetchRecord(
            req.layer, db_safe_text(req.url), req.host, outcome, http_status=status, raw_text=text,
            raw_sha256=hashlib.sha256(encoded).hexdigest() if encoded is not None else None,
            raw_bytes=len(encoded) if encoded is not None else None, query_text=req.query_text,
            detail=self._redact(detail)), next_url)

    # ── 連線與讀取 ────────────────────────────────────────────────────────────────────────
    @contextmanager
    def _open(self, req: _Req) -> Iterator[httpx.Response]:
        """以已驗證的位址連線（`pinned_ip_sni`）；只在連線失敗時才換下一個已驗證位址。回應在離開
        區塊時關閉，連同它的 Client（每跳新連線、不重用）。"""
        parts = urlsplit(req.url)
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        headers = {
            "Host": req.host, "User-Agent": self._user_agent, "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, application/atom+xml, text/html, text/plain, */*;q=0.1",
            "Connection": "close"}
        if req.host == GITHUB_HOST:
            headers["Accept"] = "application/vnd.github+json"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
        last: httpx.HTTPError | None = None
        for address in req.check.addresses[:MAX_CONNECT_ADDRESSES]:
            bare = address.split("%", 1)[0]
            literal = f"[{bare}]" if ":" in bare else bare
            client = httpx.Client(transport=self._transport_factory(), follow_redirects=False,
                                  timeout=httpx.Timeout(self._timeout), trust_env=False)
            try:
                request = client.build_request("GET", f"https://{literal}{target}", headers=headers,
                                               extensions={"sni_hostname": req.host})
                response = client.send(request, stream=True)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                client.close()
                last = exc
                continue
            except BaseException:
                client.close()
                raise
            try:
                yield response
            finally:
                response.close()
                client.close()
            return
        assert last is not None
        raise last

    def _read_body(self, response: httpx.Response, started: float) -> bytes:
        encoding = response.headers.get("content-encoding", "").strip().lower()
        if encoding in ("", "identity"):
            inflater = None
        elif encoding in ("gzip", "deflate"):
            inflater = _Inflater(encoding)
        else:
            raise _BadBody(f"不支援的 Content-Encoding：{encoding[:40]}")
        out, wire = bytearray(), 0
        for chunk in response.iter_raw(CHUNK_BYTES):
            if self._clock() - started > self._timeout:
                raise _BodyTimeout
            wire += len(chunk)
            if wire > self._max_bytes:
                raise _TooLarge
            out += chunk if inflater is None else inflater.feed(chunk, self._max_bytes - len(out))
            if len(out) > self._max_bytes:
                raise _TooLarge
        if self._clock() - started > self._timeout:       # 空本文或最後一塊之後才超時也算
            raise _BodyTimeout
        if inflater is not None:
            inflater.finish()
        return bytes(out)

    # ── 紀錄與審計 ────────────────────────────────────────────────────────────────────────
    def _denied(self, layer: str, url: str, check: UrlCheck, query_text: str | None) -> FetchRecord:
        detail = f"{check.reason}：{check.detail}" if check.detail else check.reason
        return FetchRecord(layer, stored_url(url), check.host, check.outcome or DENIED_ALLOWLIST,
                           query_text=query_text, detail=detail)

    def _redact(self, text: str) -> str:
        return text.replace(self._token, _REDACTED) if self._token and text else text

    def _audit_record(self, record: FetchRecord) -> None:
        """每次外呼寫 Bridge 審計 log（NFR-R2P-03-5）：只記 host、outcome、狀態碼、trace_id，不記
        URL 與任何標頭。"""
        logger.info("research fetch host=%s outcome=%s status=%s", record.host, record.outcome,
                    record.http_status)
        if self._audit is not None:
            self._audit.record("research_fetch", layer=record.layer, host=record.host,
                               outcome=record.outcome, http_status=record.http_status,
                               trace_id=trace_id_var.get())
