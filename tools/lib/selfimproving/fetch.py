"""SelfImproving 外聯：對單一研究來源抓原始位元組（TCS-SelfImproving-P1 R58）。

能力類別 `net`：整個套件**唯一** import `urllib`／`http`／`socket`／`ssl` 的檔。只准 http／https、
不帶任何認證標頭、`Accept-Encoding: identity`、重導向手動處理（至多 5 跳；目標 `hostname:port` 須在
允許集合、scheme 不得改變）、整個來源的牆鐘與位元組有界（超界即中止、不截斷）。
失敗原因為封閉集合：timeout、http-status、too-large、non-text、encoding、redirect-refused、network。
"""

from __future__ import annotations

import http.client
import socket
import time
import urllib.parse
from dataclasses import dataclass

from .sources import Policy, parse_url

USER_AGENT = "selfimproving-research/1"
MAX_REDIRECTS = 5
_TEXT_TYPES = {"application/json", "application/xml", "application/atom+xml",
               "application/rss+xml", "application/xhtml+xml"}
_REDIRECT_STATUS = (301, 302, 303, 307, 308)
_CHUNK = 8192
_DEFAULT_PORT = {"http": 80, "https": 443}


class FetchError(Exception):
    """該來源抓取失敗：`reason` 為封閉集合之一，`detail` 為補充（例如狀態碼）。"""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason} {detail}".strip())
        self.reason, self.detail = reason, detail


@dataclass
class Fetched:
    raw: bytes
    status: int


def host_port(url: str) -> str:
    scheme, host, _, port, _ = parse_url(url)
    return f"{host}:{port if port is not None else _DEFAULT_PORT.get(scheme, 0)}"


def check_redirect(from_url: str, to_url: str, allowed_hosts) -> str | None:
    """逐跳判定：可放行回 None，否則回 `redirect-refused`。scheme 須為 http／https 且不得改變
    （https 降 http 是降級；跨 scheme 一律拒，保守）；目標 `hostname:port` 須在允許集合。"""
    s_from, s_to = parse_url(from_url)[0], parse_url(to_url)[0]
    if s_to not in ("http", "https") or s_from != s_to:
        return "redirect-refused"
    return None if host_port(to_url) in allowed_hosts else "redirect-refused"


def _reason(exc: BaseException) -> str:
    """等回應逾時才是 timeout，其餘一律 network（建連線與送出請求階段的錯誤由 `_open` 直接歸
    network；Windows 對無人監聽的本機埠要約 2 秒才回拒絕，不能因此誤判為逾時）。"""
    return "timeout" if isinstance(exc, (socket.timeout, TimeoutError)) else "network"


def _read_body(conn, resp, deadline: float, max_bytes: int) -> bytes:
    """讀本文：每次讀取前依剩餘期限重設 socket 逾時、只做一次 `read1`——慢滴回應（每次只來一點）
    也無法把牆鐘拖過整個來源的期限。"""
    length = resp.headers.get("Content-Length", "")
    if length.isdigit() and int(length) > max_bytes:
        raise FetchError("too-large", f"Content-Length {length} > {max_bytes}")
    buf = bytearray()
    while (left := deadline - time.monotonic()) > 0:
        conn.sock.settimeout(left)
        chunk = resp.read1(_CHUNK)
        if not chunk:
            return bytes(buf)
        buf += chunk
        if len(buf) > max_bytes:
            raise FetchError("too-large", f"超過 {max_bytes} 位元組")
    raise FetchError("timeout")


def _conn_class(scheme: str):
    """`will_close` 的回應會在 `getresponse` 內自動關掉連線物件的 socket 參照，之後就無法依剩餘
    期限重設逾時；故把 `close` 延後、改由 `shut` 明確收尾。"""
    base = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection

    class Conn(base):
        def close(self) -> None:  # noqa: D401  # getresponse 的自動關閉改成什麼都不做
            return None

        def shut(self) -> None:
            base.close(self)

    return Conn


def _open(url: str, timeout: float):
    """對單一 URL 送 GET（不帶認證、不走代理、`Connection: close`）；回 (連線, 回應)。
    建連線與送出請求的錯誤一律 network；等回應逾時才是 timeout。"""
    parts = urllib.parse.urlsplit(url)
    conn = _conn_class(parts.scheme)(parts.hostname, parts.port, timeout=timeout)
    try:
        conn.request("GET", (parts.path or "/") + (f"?{parts.query}" if parts.query else ""),
                     headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity",
                              "Connection": "close"})
    except (OSError, http.client.HTTPException) as exc:
        conn.shut()
        raise FetchError("network") from exc
    try:
        return conn, conn.getresponse()
    except (OSError, http.client.HTTPException) as exc:
        conn.shut()
        raise FetchError(_reason(exc)) from exc


def fetch_source(url: str, *, policy: Policy, timeout: float, max_bytes: int,
                 allowed_hosts) -> Fetched:
    """抓單一來源（含全部重導向跳）的原始位元組；失敗拋 FetchError。"""
    scheme = parse_url(url)[0]
    if scheme != "https" and not (scheme == "http" and policy.allow_http):
        raise FetchError("network", f"scheme {scheme!r} 不被政策允許")
    deadline = time.monotonic() + timeout
    cur, hops = url, 0
    for _ in range(MAX_REDIRECTS + 2):  # 初始請求加至多 5 跳重導向
        left = deadline - time.monotonic()
        if left <= 0:
            raise FetchError("timeout")
        conn, resp = _open(cur, left)
        try:
            status = resp.status
            loc = resp.headers.get("Location")
            if status in _REDIRECT_STATUS and loc:
                hops += 1
                target = urllib.parse.urljoin(cur, loc)
                if hops > MAX_REDIRECTS or check_redirect(cur, target, allowed_hosts):
                    raise FetchError("redirect-refused", target)
                cur = target
                continue
            if not 200 <= status < 300:
                raise FetchError("http-status", str(status))
            enc = (resp.headers.get("Content-Encoding") or "identity").strip().lower()
            if enc != "identity":
                raise FetchError("encoding", enc)
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if not (ctype.startswith("text/") or ctype in _TEXT_TYPES):
                raise FetchError("non-text", ctype or "缺 Content-Type")
            return Fetched(_read_body(conn, resp, deadline, max_bytes), status)
        except TimeoutError as exc:
            raise FetchError("timeout") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise FetchError("network") from exc
        finally:
            conn.shut()
    raise FetchError("redirect-refused", "重導向跳數超過上限")
