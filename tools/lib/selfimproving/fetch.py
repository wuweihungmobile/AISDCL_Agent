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
import urllib.error
import urllib.parse
import urllib.request
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401  # 關掉自動跟隨，改手動把關
        return None


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
    """建連線與送出請求階段的任何錯誤（含連線逾時）一律是 network；等回應或讀本文逾時才是 timeout
    （urllib 把前者包成 URLError、後者以原始 TimeoutError 傳出；Windows 對無人監聽的本機埠要約
    2 秒才回拒絕，不能因此誤判為逾時）。"""
    return "timeout" if isinstance(exc, (socket.timeout, TimeoutError)) \
        and not isinstance(exc, urllib.error.URLError) else "network"


def _read_body(resp, deadline: float, max_bytes: int) -> bytes:
    length = resp.headers.get("Content-Length", "")
    if length.isdigit() and int(length) > max_bytes:
        raise FetchError("too-large", f"Content-Length {length} > {max_bytes}")
    buf = bytearray()
    for chunk in iter(lambda: resp.read(_CHUNK), b""):
        if time.monotonic() > deadline:
            raise FetchError("timeout")
        buf += chunk
        if len(buf) > max_bytes:
            raise FetchError("too-large", f"超過 {max_bytes} 位元組")
    return bytes(buf)


def fetch_source(url: str, *, policy: Policy, timeout: float, max_bytes: int,
                 allowed_hosts) -> Fetched:
    """抓單一來源（含全部重導向跳）的原始位元組；失敗拋 FetchError。"""
    scheme = parse_url(url)[0]
    if scheme != "https" and not (scheme == "http" and policy.allow_http):
        raise FetchError("network", f"scheme {scheme!r} 不被政策允許")
    deadline = time.monotonic() + timeout
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
    cur, hops = url, 0
    for _ in range(MAX_REDIRECTS + 2):  # 初始請求加至多 5 跳重導向
        left = deadline - time.monotonic()
        if left <= 0:
            raise FetchError("timeout")
        req = urllib.request.Request(cur, headers={"User-Agent": USER_AGENT,
                                                   "Accept-Encoding": "identity"})
        try:
            resp = opener.open(req, timeout=left)
        except urllib.error.HTTPError as exc:
            resp = exc
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            raise FetchError(_reason(exc)) from exc
        try:
            status = resp.status if hasattr(resp, "status") else resp.code
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
            return Fetched(_read_body(resp, deadline, max_bytes), status)
        except TimeoutError as exc:
            raise FetchError("timeout") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise FetchError("network") from exc
        finally:
            resp.close()
    raise FetchError("redirect-refused", "重導向跳數超過上限")
