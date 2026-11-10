"""SelfImproving 外聯：對研究來源抓原始位元組（P1 R58；P6 改為 `fetch_chain`）。

能力類別 `net`：整個套件**唯一** import `urllib`／`http`／`socket`／`ssl` 的檔。
`fetch_chain` 只准 https:443、不帶任何認證標頭、`Accept-Encoding: identity`、DNS 解析一次且全部位址須公網、以驗證過的 IP 連線
（SNI／Host 為原主機名）、重導向逐跳重驗（至多 5 跳）、每條請求鏈的牆鐘與位元組有界（超界即中止、
不截斷）。失敗原因為封閉集合：timeout、http-status、too-large、non-text、encoding、redirect-refused、
blocked、private-ip、network。
"""

from __future__ import annotations

import http.client
import io
import socket
import ssl
import time
import urllib.parse
from dataclasses import dataclass

from . import netguard

USER_AGENT = "selfimproving-research/1"
MAX_REDIRECTS = 5
_TEXT_TYPES = {"application/json", "application/xml", "application/atom+xml",
               "application/rss+xml", "application/xhtml+xml"}
_REDIRECT_STATUS = (301, 302, 303, 307, 308)
_CHUNK = 8192


class FetchError(Exception):
    """該來源抓取失敗：`reason` 為封閉集合之一，`detail` 為補充（例如狀態碼）。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason} {detail}".strip())
        self.reason, self.detail = reason, detail


@dataclass
class Fetched:
    raw: bytes
    status: int
    ctype: str = ""


class _DeadlineRaw(io.RawIOBase):
    """回應讀取的最底層：**每一次**向 socket 取位元組之前都依整個來源的剩餘期限重設逾時，期限已過
    即拋 `TimeoutError`。狀態列、標頭、分塊大小行、trailer 行與本文走同一個出口，慢滴回應（每次
    只來一點、永遠不超過單次逾時）也無法把牆鐘拖過期限（R58 (d)）。"""

    def __init__(self, sock, deadline: float, clock=time.monotonic) -> None:
        super().__init__()
        self._sock, self._deadline, self._clock = sock, deadline, clock

    def readable(self) -> bool:
        return True

    def readinto(self, buf) -> int:
        left = self._deadline - self._clock()
        if left <= 0:
            raise TimeoutError("牆鐘期限已到")
        self._sock.settimeout(left)
        return self._sock.recv_into(buf)


class _DeadlineSock:
    """只換掉 `makefile`（回應讀取走 `_DeadlineRaw`）；其餘（送出、關閉）委派給底層 socket。"""

    def __init__(self, sock, deadline: float, clock=time.monotonic) -> None:
        self._sock, self._deadline, self._clock = sock, deadline, clock

    def makefile(self, *_args, **_kwargs):
        return io.BufferedReader(_DeadlineRaw(self._sock, self._deadline, self._clock), _CHUNK)

    def __getattr__(self, name):
        return getattr(self._sock, name)


def _read_body(resp, max_bytes: int) -> bytes:
    """讀本文：逾時由 `_DeadlineRaw` 在每次讀取時強制；這裡只管位元組上界。"""
    length = resp.headers.get("Content-Length", "")
    if length.isascii() and length.isdigit() and int(length) > max_bytes:
        raise FetchError("too-large", f"Content-Length {length} > {max_bytes}")
    buf = bytearray()
    for chunk in iter(lambda: resp.read1(_CHUNK), b""):
        buf += chunk
        if len(buf) > max_bytes:
            raise FetchError("too-large", f"超過 {max_bytes} 位元組")
    return bytes(buf)


# ── P6：登記鏡像驅動的安全請求鏈（AC-SI-30-7；DNS 一次、釘 IP、SNI／Host＝原主機名）──────────
_CHARSETS = ("utf-8", "utf8", "us-ascii", "ascii")


def _resolve(host: str) -> list[str]:
    """預設解析縫：`getaddrinfo` 的全部位址（去重、保序）；測試以 `RESOLVER` 注入。"""
    infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(i[4][0]) for i in infos))


def _connect(ip: str, port: int, server_hostname: str, deadline: float):
    """預設連線縫：對**驗證過的 IP** 建 TCP，TLS 的 SNI 與憑證主機名驗證用原主機名。"""
    sock = socket.create_connection((ip, port), timeout=max(deadline - time.monotonic(), 0.001))
    try:
        return ssl.create_default_context().wrap_socket(sock, server_hostname=server_hostname)
    except BaseException:
        sock.close()
        raise


RESOLVER = _resolve
CONNECTOR = _connect


def _target_of(cur: str, loc: str, hosts, hops: int) -> str:
    """重導目標逐跳重驗：跳數、字面形態、host ∈ 有效網域；失敗＝`redirect-refused`（不連線）。"""
    try:
        target = urllib.parse.urljoin(cur, loc)
    except ValueError as exc:
        raise FetchError("redirect-refused", "Location 無法解析") from exc
    hp = netguard.split_host(target)
    if (hops > MAX_REDIRECTS or netguard.url_shape_problems(target) or hp is None
            or hp[0].lower() not in hosts):
        raise FetchError("redirect-refused", target)
    return target


def _request_bytes(host: str, path: str) -> bytes:
    return (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {USER_AGENT}\r\n"
            "Accept-Encoding: identity\r\nConnection: close\r\n\r\n").encode("ascii")


def _checked_body(resp, max_bytes: int) -> bytes:
    if not 200 <= resp.status < 300:
        raise FetchError("http-status", str(resp.status))
    if (resp.headers.get("Content-Encoding") or "identity").strip().lower() != "identity":
        raise FetchError("encoding", "Content-Encoding")
    head = resp.headers.get("Content-Type") or ""
    ctype = head.split(";")[0].strip().lower()
    if not (ctype.startswith("text/") or ctype in _TEXT_TYPES):
        raise FetchError("non-text", ctype or "缺 Content-Type")
    for part in head.split(";")[1:]:
        key, _, val = part.partition("=")
        if key.strip().lower() == "charset" and val.strip().strip('"').lower() not in _CHARSETS:
            raise FetchError("encoding", val.strip())
    return _read_body(resp, max_bytes)


def fetch_chain(url: str, *, hosts, timeout: float, max_bytes: int, resolver=None,
                connector=None, clock=time.monotonic) -> Fetched:
    """一條請求鏈（一次 GET 加其全部重導向）；牆鐘 ≤ `timeout`、位元組 ≤ `max_bytes`。
    每一跳：字面形態 → host ∈ `hosts`（`blocked`）→ 解析一次、全部位址須公網（`private-ip`）→ 以
    驗證過的 IP 連線、`Host` 與 SNI 用原主機名。失敗拋 `FetchError`（封閉集合）。"""
    resolver, connector = resolver or RESOLVER, connector or CONNECTOR
    deadline = clock() + timeout
    cur, hops = url, 0
    for _ in range(MAX_REDIRECTS + 2):  # 初始請求加至多 5 跳（第 6 跳於 `_target_of` 拒絕）
        if deadline - clock() <= 0:
            raise FetchError("timeout")
        if netguard.url_shape_problems(cur):
            raise FetchError("network", "url 形態不合")
        host, port = netguard.split_host(cur)
        host = host.lower()
        if host not in hosts:
            raise FetchError("blocked", host)
        try:
            addrs = resolver(host)
        except (OSError, ValueError) as exc:
            raise FetchError("network", "解析失敗") from exc
        if not addrs:
            raise FetchError("network", "解析無位址")
        if not all(netguard.is_public_ip(a) for a in addrs):
            raise FetchError("private-ip", host)
        parts = urllib.parse.urlsplit(cur)
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        try:
            conn = connector(addrs[0], 443, host, deadline)
        except TimeoutError as exc:
            raise FetchError("timeout") from exc
        except (OSError, ValueError) as exc:
            raise FetchError("network", "連線失敗") from exc
        try:
            conn.sendall(_request_bytes(host, path))
            resp = http.client.HTTPResponse(_DeadlineSock(conn, deadline, clock))
            resp.begin()
            loc = resp.headers.get("Location")
            if resp.status in _REDIRECT_STATUS and loc:
                hops += 1
                cur = _target_of(cur, loc, hosts, hops)
                continue
            return Fetched(_checked_body(resp, max_bytes), resp.status,
                           (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower())
        except TimeoutError as exc:
            raise FetchError("timeout") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise FetchError("network") from exc
        finally:
            conn.close()
    raise FetchError("redirect-refused", "重導向跳數超過上限")
