"""抓取器測試的假設施（TCS-ResearchToPRD-P0-20261102 §5.2、§5.3；PKG-BR-B）。

hermetic：任何測試都不連真外部端點。這裡提供：
  · `FakeClock`／`FakeResolver`：假時鐘（睡眠只前進時鐘、不真的等）與假 DNS 解析器（記錄解析
    次數，可依序回不同答案，用來造 DNS rebinding）；
  · `FakeTransport`（＋`Reply`、`Call`、`ChunkStream`）：假連線層——`httpx.BaseTransport`，記錄
    每次連線的目標 IP、Host 標頭、SNI、路徑與同時連線數，依腳本回 `Reply`（狀態、標頭、本文、
    時鐘前進、例外）。它收到的 `request.url.host` 就是被釘住的 IP，所以「連線目標恰為首次驗證
    的 IP」可直接斷言；
  · `ClientHelloProbe`：本機 TCP 假伺服器，在線路上讀第一個 TLS record 解出 SNI（不完成握手；
    V-R4）；
  · `route_connections`：把對公網位址的 `socket.create_connection` 改道到本機（讓**真的** httpx
    傳輸層與真的 `FetchClient` 在線路上走一遍，而不連任何外部位址）；
  · `forbid_external_network`：hermetic 守衛——任何 Python 層的 DNS 解析、對非 loopback 的
    `connect` 一律當場失敗（psycopg 走 libpq，不受影響）；
  · `Rig`／`make_rig`：把上述組成一個可用的 `FetchClient`。
"""
from __future__ import annotations

import ipaddress
import socket
import struct
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from app.research.fetch import EffectiveAllowlist, FetchClient, build_effective_allowlist
from app.research.fetch.allowlist import ENV_MIN_INTERVALS
from app.research.fetch.http import HostThrottle

PUBLIC_IP = "93.184.216.34"
CHUNK = 65_536


# ── 假時鐘與假解析器 ───────────────────────────────────────────────────────────────────────
class FakeClock:
    """單調時鐘（`__call__`）與牆鐘（`epoch`）共用一條時間線；`sleep` 只前進時間並留記錄。"""

    def __init__(self, start: float = 1_000.0, epoch_start: float = 1_700_000_000.0) -> None:
        self.now, self._start, self._epoch0 = start, start, epoch_start
        self.sleeps: list[float] = []
        self._lock = threading.Lock()

    def __call__(self) -> float:
        with self._lock:
            return self.now

    def epoch(self) -> float:
        with self._lock:
            return self._epoch0 + (self.now - self._start)

    def advance(self, seconds: float) -> None:
        with self._lock:
            self.now += seconds

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.sleeps.append(seconds)
            self.now += seconds


class FakeResolver:
    """假 DNS：`answers`（host → 位址清單）；`sequence` 給了就依序回答（不論 host，最後一個答案
    重複），用來造「驗證時公網、第二次解析私網」。`calls` 記錄每次解析的 host。"""

    def __init__(self, answers: Mapping[str, Sequence[str]] | None = None,
                 default: Sequence[str] = (PUBLIC_IP,),
                 sequence: Sequence[Sequence[str]] | None = None) -> None:
        self.answers = {k: list(v) for k, v in (answers or {}).items()}
        self.default, self.sequence = list(default), [list(s) for s in (sequence or [])]
        self.calls: list[str] = []

    def __call__(self, host: str) -> list[str]:
        self.calls.append(host)
        if self.sequence:
            return list(self.sequence[min(len(self.calls), len(self.sequence)) - 1])
        return list(self.answers.get(host, self.default))


# ── 假連線層 ────────────────────────────────────────────────────────────────────────────────
@dataclass
class Call:
    """假連線層收到的一次連線。`ip`＝請求網址的 host（被釘住的位址）；`host_header`／`sni` 是原
    hostname；`authorization` 是 Authorization 標頭值（供檢查權杖只送給 GitHub）。"""

    n: int
    ip: str
    port: int | None
    scheme: str
    host_header: str
    sni: str | None
    path: str
    headers: dict[str, str]
    at: float = 0.0                      # 收到請求當下的假時鐘讀數（量節流間隔用）

    @property
    def authorization(self) -> str | None:
        return self.headers.get("authorization")


@dataclass
class Reply:
    """腳本對一次連線的回應。`advance`＝回應前讓假時鐘前進幾秒（造逾時）；`chunk_advance`＝每讀
    一個 chunk 前進幾秒（造慢速本文）；`raises`＝改丟這個例外（造連線層逾時等）。"""

    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    advance: float = 0.0
    chunk_advance: float = 0.0
    raises: Exception | None = None


def json_reply(text: str, *, status: int = 200, **headers: str) -> Reply:
    return Reply(status, {"content-type": "application/json; charset=utf-8", **headers},
                 text.encode("utf-8"))


def text_reply(body: bytes | str, content_type: str, *, status: int = 200,
               **headers: str) -> Reply:
    data = body.encode("utf-8") if isinstance(body, str) else body
    return Reply(status, {"content-type": content_type, **headers}, data)


class ChunkStream(httpx.SyncByteStream):
    """串流本文（`httpx.Response(stream=…)`）：逐 chunk 吐出，`close()` 時登記連線結束。"""

    def __init__(self, body: bytes, on_chunk: Callable[[], None], on_close: Callable[[], None]):
        self._body, self._on_chunk, self._on_close = body, on_chunk, on_close
        self._closed = False

    def __iter__(self) -> Iterator[bytes]:
        for start in range(0, len(self._body), CHUNK):
            self._on_chunk()
            yield self._body[start:start + CHUNK]

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._on_close()


class FakeTransport(httpx.BaseTransport):
    """記錄並回放：`script(call) -> Reply`。`hold` 是每個連線在假伺服器裡逗留的**真實**秒數（極短，
    只用來讓並行請求有機會重疊，好讓「同時最多一條連線」的斷言有意義）。"""

    def __init__(self, script: Callable[[Call], Reply], clock: FakeClock | None = None,
                 hold: float = 0.0) -> None:
        self.script, self.clock, self.hold = script, clock, hold
        self.calls: list[Call] = []
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            call = Call(len(self.calls), request.url.host, request.url.port, request.url.scheme,
                        request.headers.get("host", ""), request.extensions.get("sni_hostname"),
                        request.url.raw_path.decode("ascii"),
                        {k.lower(): v for k, v in request.headers.items()},
                        self.clock() if self.clock is not None else 0.0)
            self.calls.append(call)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            reply = self.script(call)
            if self.hold:
                time.sleep(self.hold)
            if self.clock is not None and reply.advance:
                self.clock.advance(reply.advance)
            if reply.raises is not None:
                raise reply.raises
        except BaseException:
            self._leave()
            raise
        tick = (lambda: self.clock.advance(reply.chunk_advance)) if (
            self.clock is not None and reply.chunk_advance) else (lambda: None)
        return httpx.Response(reply.status, headers=reply.headers,
                              stream=ChunkStream(reply.body, tick, self._leave))

    def _leave(self) -> None:
        with self._lock:
            self.active -= 1

    # `httpx.Client.close()` 會關傳輸層；假的沒有資源要放
    def close(self) -> None:  # noqa: D401
        return None


# ── 組裝 ────────────────────────────────────────────────────────────────────────────────────
@dataclass
class Rig:
    client: FetchClient
    clock: FakeClock
    resolver: FakeResolver
    transport: FakeTransport

    @property
    def calls(self) -> list[Call]:
        return self.transport.calls


def make_rig(script: Callable[[Call], Reply] | None = None, *,
             allowlist: EffectiveAllowlist | None = None,
             resolver: FakeResolver | None = None, hold: float = 0.0,
             throttle: HostThrottle | None = None, **client_kw: Any) -> Rig:
    """假時鐘＋假解析器＋假連線層的 `FetchClient`。`script` 缺省＝一律 404。"""
    clock = FakeClock()
    fake_dns = resolver or FakeResolver()
    transport = FakeTransport(script or (lambda call: Reply(404)), clock, hold)
    client = FetchClient(
        allowlist=allowlist or build_effective_allowlist(ENV_MIN_INTERVALS), resolver=fake_dns,
        transport_factory=lambda: transport, clock=clock, epoch=clock.epoch, sleeper=clock.sleep,
        throttle=throttle, **client_kw)
    return Rig(client, clock, fake_dns, transport)


# ── 線路層：TLS ClientHello 的 SNI ────────────────────────────────────────────────────────────
def parse_sni(data: bytes) -> str | None:
    """從第一個 TLS record（ClientHello）解出 server_name 擴充的主機名；不是 ClientHello 回
    None。"""
    if len(data) < 48 or data[0] != 0x16 or data[5] != 0x01:
        return None
    pos = 5 + 4 + 2 + 32                              # record 標頭、握手標頭、版本、random
    pos += 1 + data[pos]                              # session id
    pos += 2 + struct.unpack("!H", data[pos:pos + 2])[0]    # cipher suites
    pos += 1 + data[pos]                              # compression methods
    end = pos + 2 + struct.unpack("!H", data[pos:pos + 2])[0]
    pos += 2
    while pos + 4 <= end:
        kind, size = struct.unpack("!HH", data[pos:pos + 4])
        pos += 4
        if kind == 0:                                 # server_name
            name_len = struct.unpack("!H", data[pos + 3:pos + 5])[0]
            return data[pos + 5:pos + 5 + name_len].decode("ascii")
        pos += size
    return None


class ClientHelloProbe:
    """本機單次 TCP 假伺服器：收下一條連線、讀 ClientHello、記錄對端與 SNI、立刻關閉。"""

    def __init__(self) -> None:
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self._sock.settimeout(10)
        self.port: int = self._sock.getsockname()[1]
        self.peer: tuple[str, int] | None = None
        self.sni: str | None = None
        self.hello_seen = False
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def _serve(self) -> None:
        try:
            conn, self.peer = self._sock.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(5)
            try:
                data = conn.recv(16_384)
            except OSError:
                return
            self.hello_seen = bool(data)
            self.sni = parse_sni(data)

    def __enter__(self) -> ClientHelloProbe:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._thread.join(10)
        self._sock.close()


def route_connections(monkeypatch: pytest.MonkeyPatch, target: tuple[str, int]
                      ) -> list[tuple[str, int]]:
    """把 `socket.create_connection` 改道到 `target`（本機），並回傳**原本要連**的位址清單。真的
    httpx／httpcore 傳輸層照常運作，但不會碰任何外部位址。"""
    wanted: list[tuple[str, int]] = []
    real = socket.create_connection

    def routed(address: tuple[str, int], *args: Any, **kwargs: Any) -> socket.socket:
        wanted.append((address[0], address[1]))
        return real(target, *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", routed)
    return wanted


# ── hermetic 守衛 ───────────────────────────────────────────────────────────────────────────
_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})


def _is_ip_literal(host: object) -> bool:
    try:
        ipaddress.ip_address(str(host).split("%", 1)[0])
    except ValueError:
        return False
    return True


def forbid_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Python 層對**名稱**的 DNS 解析一律失敗（loopback 名稱與 IP 字面值照常放行，因為它們不查
    DNS）；對非 loopback 位址的 `connect` 一律失敗。（`route_connections` 把連線改道到 loopback
    之後才會走到 `connect`，所以不受影響。）"""
    real_getaddrinfo = socket.getaddrinfo

    def no_dns(host: Any, *args: Any, **kwargs: Any) -> Any:
        if host in _LOOPBACK or _is_ip_literal(host):
            return real_getaddrinfo(host, *args, **kwargs)
        raise AssertionError(f"hermetic：測試不得做 DNS 解析 {host!r}")

    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def guard(sock: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOOPBACK:
            raise AssertionError(f"hermetic：測試不得連外部位址 {address!r}")

    def connect(self: socket.socket, address: Any) -> None:
        guard(self, address)
        return real_connect(self, address)

    def connect_ex(self: socket.socket, address: Any) -> int:
        guard(self, address)
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
