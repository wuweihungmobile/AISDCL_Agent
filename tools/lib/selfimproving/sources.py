"""SelfImproving 研究來源表：載入、驗證、現役篩選與雜湊（TCS-SelfImproving-P1 R43、R42 (c)）。

`validate_table` 是 `check` 的 `research.sources` 與 `research --fetch` 預檢共用的唯一驗證函式。
只驗字串形態（不做 DNS 解析、不證明 URL 可達）；本檔屬 `ro` 類，不 import 任何網路模組，
URL 以手寫切分判 scheme／userinfo／host。
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass

from .events import SRC_ID_RE

SOURCES_REL = "docs/06_quality/SelfImproving_Protocol/research_sources.json"
_KINDS = ("changelog", "docs", "release", "blog")
_ENTRY_KEYS = {"id", "url", "kind", "extract", "added_by", "retired"}
_REQUIRED = ("id", "url", "kind", "extract", "added_by")
_PRIVATE_NETS = tuple(ipaddress.ip_network(n) for n in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
    "::1/128", "fe80::/10", "fc00::/7"))
_LOOPBACK = (ipaddress.ip_network("127.0.0.0/8"), ipaddress.ip_network("::1/128"))


@dataclass(frozen=True)
class Policy:
    allow_http: bool
    allow_loopback: bool


DEFAULT_POLICY = Policy(allow_http=False, allow_loopback=False)


def sha256_lf(raw: bytes) -> str:
    """`sha256:` 接 CRLF 換 LF 後位元組的 sha256（`sources_sha256` 一律此算法）。"""
    return "sha256:" + hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def parse_url(url: str) -> tuple[str, str, str, int | None, bool]:
    """回（scheme 小寫, host 小寫, 完整 authority, port 或 None, 有 userinfo）；手寫切分。"""
    scheme, sep, rest = url.partition("://")
    if not sep:
        return "", "", "", None, False
    authority = re.split(r"[/?#]", rest, maxsplit=1)[0]
    userinfo = "@" in authority
    hostport = authority.rsplit("@", 1)[-1]
    port = None
    if hostport.startswith("["):
        host, _, tail = hostport[1:].partition("]")
        tail = tail.lstrip(":")
    else:
        host, _, tail = hostport.partition(":")
    if tail.isdigit():
        port = int(tail)
    return scheme.lower(), host.split("%")[0].lower(), authority, port, userinfo


def _is_private(host: str, policy: Policy) -> bool:
    if host == "localhost" or host.endswith(".localhost"):
        return not policy.allow_loopback
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    cands = [ip] + ([ip.ipv4_mapped] if getattr(ip, "ipv4_mapped", None) else [])
    for cand in cands:
        if policy.allow_loopback and any(cand in net for net in _LOOPBACK):
            continue
        if any(cand in net for net in _PRIVATE_NETS):
            return True
    return False


def _url_problems(url: str, subject: str, policy: Policy) -> list[tuple[str, str, str]]:
    out = []
    low = url.lower()
    if not (low.startswith("https://") or (policy.allow_http and low.startswith("http://"))):
        out.append(("SRC-URL-SCHEME", subject, "url 須以 https:// 起頭"))
    _, host, _, _, userinfo = parse_url(url)
    if userinfo:
        out.append(("SRC-URL-USERINFO", subject, "url 的 authority 含 userinfo（@）"))
    if not host or _is_private(host, policy):
        out.append(("SRC-URL-HOST", subject, f"host {host!r} 為空、localhost 或私網／loopback"))
    return out


def _format_problems(raw: bytes) -> list[tuple[str, str, str]]:
    out = []
    if raw.startswith(b"\xef\xbb\xbf"):
        out.append(("SRC-FILE-FORMAT", "-", "有 BOM"))
    if b"\r" in raw:
        out.append(("SRC-FILE-FORMAT", "-", "含 CR（換行須為 LF）"))
    if not raw.endswith(b"\n"):
        out.append(("SRC-FILE-FORMAT", "-", "結尾無換行"))
    return out


def load_table(raw: bytes) -> dict | None:
    """來源表的 JSON 物件；不是 UTF-8 JSON 物件回 None。"""
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _entry_problems(i: int, e, policy: Policy) -> list[tuple[str, str, str]]:
    if not isinstance(e, dict):
        return [("SRC-SCHEMA", f"sources[{i}]", "元素不是物件")]
    ident = e.get("id")
    sub = ident if isinstance(ident, str) and ident else f"sources[{i}]"
    out = [("SRC-SCHEMA", sub, f"表外鍵 {k}") for k in sorted(set(e) - _ENTRY_KEYS)]
    miss = [k for k in _REQUIRED if not (isinstance(e.get(k), str) and e[k].strip())]
    out += [("SRC-FIELD-MISSING", sub, f"必備鍵缺或空：{k}") for k in miss]
    if isinstance(ident, str) and ident and not SRC_ID_RE.match(ident):
        out.append(("SRC-ID-FORMAT", sub, "id 不合 ^[a-z0-9][a-z0-9-]{0,31}$"))
    return out


def validate_table(raw: bytes, policy: Policy) -> list[tuple[str, str, str]]:
    """來源表驗證：回〔碼, subject, detail〕串列（空＝合格）；碼序依 TCS R43。"""
    out = _format_problems(raw)
    obj = load_table(raw)
    if obj is None:
        return out + [("SRC-FILE-FORMAT", "-", "不是 UTF-8 JSON 物件")]
    srcs = obj.get("sources")
    if obj.get("schema_rev") != 1 or isinstance(obj.get("schema_rev"), bool):
        out.append(("SRC-SCHEMA", "-", "schema_rev 缺或不是 1"))
    if not isinstance(srcs, list):
        return out + [("SRC-SCHEMA", "-", "頂層缺 sources 或不是陣列")]
    out += [("SRC-SCHEMA", "-", f"頂層表外鍵 {k}") for k in sorted(set(obj) - {"schema_rev",
                                                                                "sources"})]
    entries = list(enumerate(srcs))
    for i, e in entries:
        out += _entry_problems(i, e, policy)
    ids = [e.get("id") for _, e in entries if isinstance(e, dict) and isinstance(e.get("id"), str)]
    seen: set[str] = set()
    for ident in ids:
        if ident in seen:
            out.append(("SRC-ID-DUP", ident, "id 重複"))
        seen.add(ident)
    for a, b in zip(ids, ids[1:]):
        if a != b and a.encode("utf-8") > b.encode("utf-8"):
            out.append(("SRC-ORDER", b, f"未依 id 的位元組序遞增（{a} 之後）"))
    for i, e in entries:
        if not isinstance(e, dict):
            continue
        sub = e["id"] if isinstance(e.get("id"), str) and e["id"] else f"sources[{i}]"
        if isinstance(e.get("kind"), str) and e["kind"] and e["kind"] not in _KINDS:
            out.append(("SRC-KIND", sub, f"kind 不在 {list(_KINDS)}"))
        if "retired" in e and e["retired"] is not True:
            out.append(("SRC-RETIRED-TYPE", sub, "retired 只准 JSON true"))
        if isinstance(e.get("url"), str) and e["url"]:
            out += _url_problems(e["url"], sub, policy)
    return out


def entries_of(raw: bytes) -> list[dict]:
    """來源表的元素（合法物件者）；讀不到回空串列。"""
    obj = load_table(raw)
    srcs = obj.get("sources") if obj else None
    return [e for e in srcs if isinstance(e, dict)] if isinstance(srcs, list) else []


def all_ids(raw: bytes) -> set[str]:
    return {e["id"] for e in entries_of(raw) if isinstance(e.get("id"), str)}


def ids_or_none(raw: bytes | None) -> set[str] | None:
    """全部 id（含 retired）；來源表不存在或無法解析回 None。"""
    return None if raw is None or load_table(raw) is None else all_ids(raw)


def active_entries(raw: bytes) -> list[dict]:
    return [e for e in entries_of(raw) if e.get("retired") is not True]
