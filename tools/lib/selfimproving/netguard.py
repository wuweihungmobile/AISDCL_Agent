"""SelfImproving 抓取的位址與 URL 形態判準（AC-SI-30-7；P6）。

能力類別 `ro`：純函式，只 import `ipaddress`、`re`（**不 import `socket`**：DNS 只在 `fetch.py`）。
`is_public_ip` 與 Console Bridge 的 `allowlist.py::is_public_ip` 逐判準對拍（TCS-P6 附錄 A）；
`url_shape_problems` 對 TCS-P6 附錄 D 的 `SI` 欄逐列求值（Console 的接受集合 ⊆ 本判準）。
"""

from __future__ import annotations

import ipaddress
import re

URL_MAX = 2048
_AUTH_END = re.compile(r"[/?#]")


def is_public_ip(address: str) -> bool:
    """全域公網單播位址。scope id 先剝；IPv4-mapped IPv6 先還原；解析不了視為非公網。
    `is_global` 不排除多播與 site-local，故另擋。"""
    try:
        parsed = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    ip = getattr(parsed, "ipv4_mapped", None) or parsed
    return bool(ip.is_global and not ip.is_multicast and not ip.is_reserved
                and not getattr(ip, "is_site_local", False))


def _bad_chars(text: str) -> bool:
    return any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in text)


def split_host(url: str) -> tuple[str, str] | None:
    """（host 原樣, 埠文字或空字串）；不是 `://` 形態、含 userinfo 回 None。不做任何正規化。"""
    _, sep, rest = url.partition("://")
    if not sep:
        return None
    authority = _AUTH_END.split(rest, maxsplit=1)[0]
    if "@" in authority:
        return None
    if authority.startswith("["):
        host, _, tail = authority[1:].partition("]")
        return host, tail[1:] if tail.startswith(":") else ("\0" if tail else "")
    host, _, port = authority.partition(":")
    return host, port


def url_shape_problems(url: str) -> list[str]:
    """字面形態問題（空＝合格；不做 DNS）：https、無 userinfo、host 非空且 ASCII 無 `xn--` label、
    非 localhost／`*.localhost`、IP 字面須為公網、無尾點、埠缺省或 443、無 `#`、無空白與控制字元、
    長度 ≤2048。"""
    out: list[str] = []
    if not isinstance(url, str) or len(url) > URL_MAX:
        return ["url 非字串或長度 > 2048"]
    if not url.lower().startswith("https://"):
        out.append("url 須以 https:// 起頭")
    if "#" in url or _bad_chars(url):
        out.append("url 含 #、空白或控制字元")
    if "@" in re.split(r"[/?#]", url.partition("://")[2], maxsplit=1)[0]:
        out.append("url 的 authority 含 userinfo")
    hp = split_host(url)
    if hp is None:
        return out or ["url 無法剖析"]
    host, port = hp
    low = host.lower()
    if not host or any(ord(c) > 127 for c in host):
        out.append("host 為空或含非 ASCII 字元")
    elif any(lbl.startswith("xn--") for lbl in low.split(".")):
        out.append("host 含 IDNA（xn--）label")
    elif low == "localhost" or low.endswith(".localhost"):
        out.append("host 為 localhost")
    elif low.endswith("."):
        out.append("host 以 . 結尾")
    else:
        try:
            ipaddress.ip_address(host.split("%", 1)[0])
        except ValueError:
            pass
        else:
            if not is_public_ip(host):
                out.append("host 為非公網 IP 字面")
    if port not in ("", "443"):
        out.append("埠只准缺省或 443")
    return out
