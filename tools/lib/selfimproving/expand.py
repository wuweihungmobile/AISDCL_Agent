"""SelfImproving 文章展開的確定性選取（AC-SI-30-8；P6）。

能力類別 `ro`：純函式，不連網、不 import `urllib`（相對連結以手寫切分解析）。`sitemap_entries`
與 XML 版 `link_targets` 先以位元組搜尋拒絕含 `<!DOCTYPE`／`<!ENTITY` 者（防實體展開，寧可誤拒），
通過者才經**唯一**的解析縫 `_parse_xml(raw)`（標準庫 `xml.etree.ElementTree`）解析。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET  # noqa: N817
from html.parser import HTMLParser

EXPAND_MAX = 3
XML_LOAD_MAX = 1024 * 1024
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_BASE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*)://([^/?#]*)([^?#]*)")


class ExpandRefused(Exception):
    """XML 含 DOCTYPE／ENTITY 或超過載入上限：解析器不被呼叫（`status=expand-refused`）。"""


class ExpandFailed(Exception):
    """解析失敗（`status=expand-failed`）。"""


def _parse_xml(raw: bytes):
    """全套件唯一的 XML 解析呼叫（測試以 spy 觀測「含 DOCTYPE 時不被呼叫」）。"""
    return ET.fromstring(raw)


_NON_UTF8_BOMS = (b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")
_ENCODING_DECL = re.compile(rb"""^\s*<\?xml[^>]*?encoding\s*=\s*["']([^"']+)["']""", re.I)


def _is_utf8_family(raw: bytes) -> bool:
    """UTF-8 系才放行：位元組搜尋只對 UTF-8／ASCII 有意義，UTF-16／32 會繞過它。"""
    head = raw[:4096]
    if raw.startswith(_NON_UTF8_BOMS) or b"\x00" in head:
        return False
    body = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    m = _ENCODING_DECL.match(body[:4096])
    return m is None or m.group(1).lower() in (b"utf-8", b"us-ascii")


def _checked_root(raw: bytes):
    if not _is_utf8_family(raw):
        raise ExpandRefused("XML 非 UTF-8 系編碼")
    low = raw.lower()
    if len(raw) > XML_LOAD_MAX or b"<!doctype" in low or b"<!entity" in low:
        raise ExpandRefused("XML 含 DOCTYPE／ENTITY 或超過載入上限")
    try:
        return _parse_xml(raw)
    except ET.ParseError as exc:
        raise ExpandFailed("XML 解析失敗") from exc


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _children(el, name: str) -> list:
    return [c for c in el if _local(c.tag) == name]


def sitemap_entries(xml_bytes: bytes) -> list[tuple[str, str | None]]:
    """每個含 `<loc>` 的 `<url>` → (loc, lastmod 或 None)，依文件序。"""
    root = _checked_root(xml_bytes)
    out = []
    for el in root.iter():
        if _local(el.tag) != "url":
            continue
        locs = _children(el, "loc")
        if not locs or not (locs[0].text or "").strip():
            continue
        mods = _children(el, "lastmod")
        out.append((locs[0].text.strip(), (mods[0].text or "").strip() or None if mods else None))
    return out


class _Anchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def _xml_links(raw: bytes) -> list[str]:
    root = _checked_root(raw)
    out = []
    for el in root.iter():
        if _local(el.tag) != "link":
            continue
        if el.get("href") and el.get("rel", "alternate") == "alternate":
            out.append(el.get("href"))
        elif (el.text or "").strip():
            out.append(el.text.strip())
    return out


def link_targets(raw: bytes, ctype: str, base: str) -> list[tuple[str, None]]:
    """`links` 模式：HTML 的 `a[href]`（出現序）或 Atom／RSS 的 `<link>` → 絕對 URL（去 fragment、
    去重；同 host 與 prefix 的限定在 `select`）。"""
    if "xml" in ctype.lower():
        refs = _xml_links(raw)
    else:
        parser = _Anchors()
        parser.feed(raw.decode("utf-8", errors="replace"))
        parser.close()
        refs = parser.hrefs
    out: list[tuple[str, None]] = []
    seen: set[str] = set()
    for ref in refs:
        url = join(base, ref)
        if url and url not in seen:
            seen.add(url)
            out.append((url, None))
    return out


def _dots(path: str) -> str:
    segs: list[str] = []
    parts = path.split("/")
    for i, seg in enumerate(parts):
        if seg == "..":
            if len(segs) > 1:
                segs.pop()
        elif seg != ".":
            segs.append(seg)
        if seg in (".", "..") and i == len(parts) - 1:
            segs.append("")
    return "/".join(segs) or "/"


def join(base: str, ref: str) -> str | None:
    """相對連結以 `base` 解析；去 fragment；非 http(s) 的 scheme（mailto: 等）與空參照回 None。"""
    ref = ref.strip().split("#", 1)[0]
    m = _BASE.match(base)
    if not ref or not m:
        return None
    scheme, auth, path = m.groups()
    if _SCHEME.match(ref):
        return ref if ref.lower().startswith(("https://", "http://")) else None
    if ref.startswith("//"):
        return f"{scheme}:{ref}"
    if ref.startswith("?"):
        return f"{scheme}://{auth}{path or '/'}{ref}"
    if ref.startswith("/"):
        raw_path = ref
    else:
        raw_path = (path.rsplit("/", 1)[0] if "/" in path else "") + "/" + ref
    pure, sep, query = raw_path.partition("?")
    return f"{scheme}://{auth}{_dots(pure)}{sep}{query}"


def _host_path(url: str) -> tuple[str, str] | None:
    m = _BASE.match(url)
    return (m.group(2).lower(), m.group(3) or "/") if m else None


def select(entries, base_url: str, prefix: str, n: int) -> list[str]:
    """同 host（小寫比對）、路徑以 `prefix` 起頭、去重、排除索引自身；依 lastmod 前 10 碼新→舊
    穩定排序（缺者最後、同值保文件序）；取前 `min(n, EXPAND_MAX)`。"""
    base_hp = _host_path(base_url)
    picked: list[tuple[str, str | None]] = []
    seen: set[str] = set()
    for loc, mod in entries:
        url = join(base_url, loc)
        hp = _host_path(url) if url else None
        if not hp or not base_hp or hp[0] != base_hp[0] or not hp[1].startswith(prefix):
            continue
        if url in seen or url == base_url:
            continue
        seen.add(url)
        picked.append((url, mod[:10] if mod else None))
    dated = [p for p in picked if p[1]]
    # 穩定排序：先依 lastmod 遞減（反向鍵避免反轉同值序），缺 lastmod 者接在最後
    dated.sort(key=lambda p: p[1], reverse=True)
    ordered = dated + [p for p in picked if not p[1]]
    return [u for u, _ in ordered[:max(0, min(n, EXPAND_MAX))]]
