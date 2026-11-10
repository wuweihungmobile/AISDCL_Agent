"""研究來源登記：追蹤來源的輸入閘與登記快照（API 契約 §5A；TCS-ResearchRegistry W-R3、W-R4）。

全部是純函式（沒有網路、沒有檔案、沒有時鐘）：

  1. `check_watch_url`：追蹤來源 URL 的**原樣判定**（不做任何正規化；D-EQA-1：Console 接受集合 ⊆ SI
     接受集合，逐列等於根層 TCS 附錄 D 的 CON 欄）。大寫 host、顯式 `:443`、任何 IP 字面一律拒絕，
     由使用者自行改寫後重送。
  2. `watch_violations`：POST 本文六條輸入閘規則一次全列（`violations[{field,rule,message}]`）。
  3. `build_registry`：登記快照（`registry_text` 與 `registry_sha256`）。**Bridge 是唯一產生者**，
     序列化規則逐字固定（契約 §5A.3）；快照內不放產生時間，也不讀時鐘——時間欄一律來自資料列。
  4. 常數 `REGISTRY_TEXT_MAX_BYTES` 只在本檔定義一處。
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from .fetch.allowlist import builtin_floor

#: 登記快照 `registry_text` 的位元組上限（UTF-8）。
REGISTRY_TEXT_MAX_BYTES = 24576
SCHEMA_REV = 1
WATCH_URL_MAX = 500
WATCH_KINDS = ("changelog", "docs", "release", "blog", "sitemap", "search")
WATCH_LAYERS = ("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY")
EXPAND_MODES = ("links", "sitemap")
EXPAND_KEYS = frozenset({"mode", "prefix", "max"})
POST_KEYS = frozenset({"slug", "url", "kind", "extract", "layer", "expand", "added_by"})

_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
_HOST_RE = re.compile(r"[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?")
_IPV4_LITERAL_RE = re.compile(r"[0-9.]+")
_PREFIX_BAD = re.compile(r"[\s?#\x00-\x1f\x7f]")


class RegistryTooLarge(Exception):
    """快照的 UTF-8 位元組數超過 `REGISTRY_TEXT_MAX_BYTES`。"""

    def __init__(self, size: int) -> None:
        super().__init__(f"registry_text {size} bytes > {REGISTRY_TEXT_MAX_BYTES}")
        self.size = size
        self.limit = REGISTRY_TEXT_MAX_BYTES


# ── 追蹤來源 URL 的原樣判定 ───────────────────────────────────────────────────────────────────
def check_watch_url(url: object) -> str | None:
    """None＝接受；否則回規則名（一律 `invalid_url`）。**不做任何正規化**。

    接受條件（全部原樣）：字串、≤500 字元、`https://` 起頭、全 ASCII 且無空白與控制字元、無 `#`；
    host（第一個 `/` 或 `?` 之前）須合 `[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?`（因此大寫、尾點、
    userinfo、任何顯式埠含 `:443`、方括號 IPv6、全形字元都被擋）；任一 label 為 `xn--` 開頭、
    `localhost` 與 `*.localhost`、IPv4 字面（任何 IP 字面皆拒）一律拒絕。"""
    bad = "invalid_url"
    if not isinstance(url, str) or len(url) > WATCH_URL_MAX or not url.startswith("https://"):
        return bad
    if any(ord(c) <= 0x20 or ord(c) >= 0x7F for c in url) or "#" in url:
        return bad
    rest = url[len("https://"):]
    cut = min((i for i in (rest.find("/"), rest.find("?")) if i >= 0), default=len(rest))
    host = rest[:cut]
    if not _HOST_RE.fullmatch(host):
        return bad
    if any(label.startswith("xn--") for label in host.split(".")):
        return bad
    if host == "localhost" or host.endswith(".localhost"):
        return bad
    if _IPV4_LITERAL_RE.fullmatch(host):
        return bad
    return None


def host_of(url: str) -> str:
    """已通過 `check_watch_url` 的 URL 的 host（原樣、已是小寫）。"""
    rest = url[len("https://"):]
    cut = min((i for i in (rest.find("/"), rest.find("?")) if i >= 0), default=len(rest))
    return rest[:cut]


# ── POST 輸入閘 ──────────────────────────────────────────────────────────────────────────────
def _v(field: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field, "rule": rule, "message": message}


def _expand_violation(expand: object) -> dict[str, str] | None:
    if expand is None:
        return None
    msg = "expand 須缺省（或 null），或為恰含 mode、prefix、max 的物件"
    if not isinstance(expand, dict) or set(expand) != EXPAND_KEYS:
        return _v("expand", "invalid_expand", msg)
    mode, prefix, cap = expand["mode"], expand["prefix"], expand["max"]
    if mode not in EXPAND_MODES:
        return _v("expand", "invalid_expand", "expand.mode 須為 links 或 sitemap")
    if (not isinstance(prefix, str) or not prefix.startswith("/") or len(prefix) > 200
            or _PREFIX_BAD.search(prefix)):
        return _v("expand", "invalid_expand", "expand.prefix 須以 / 起頭、≤200 字元、無空白與 ?#")
    if type(cap) is not int or not 1 <= cap <= 3:
        return _v("expand", "invalid_expand", "expand.max 須為 1～3 的整數")
    return None


def watch_violations(body: Mapping[str, Any]) -> list[dict[str, str]]:
    """六條輸入閘規則（加未知鍵）一次全列；空表＝通過。`added_by` 由路由另驗（人名欄位）。"""
    out: list[dict[str, str]] = []
    out += [_v(k, "unknown_field", f"不收欄位 {k}") for k in sorted(set(body) - POST_KEYS)]
    slug = body.get("slug")
    if not isinstance(slug, str) or not _SLUG_RE.fullmatch(slug):
        out.append(_v("slug", "invalid_slug", "slug 須合 ^[a-z0-9][a-z0-9-]{0,31}$"))
    if check_watch_url(body.get("url")) is not None:
        out.append(_v("url", "invalid_url", "url 須為 https、小寫 host、無埠與 IP 字面與片段"))
    if body.get("kind") not in WATCH_KINDS:
        out.append(_v("kind", "invalid_kind", f"kind 須為 {'｜'.join(WATCH_KINDS)}"))
    if body.get("layer") not in WATCH_LAYERS:
        out.append(_v("layer", "invalid_layer", f"layer 須為 {'｜'.join(WATCH_LAYERS)}"))
    extract = body.get("extract")
    if (not isinstance(extract, str) or not 1 <= len(extract) <= 200
            or any(ord(c) < 0x20 or ord(c) == 0x7F for c in extract)):
        out.append(_v("extract", "invalid_extract", "extract 須為 1～200 字、無控制字元"))
    bad_expand = _expand_violation(body.get("expand"))
    if bad_expand is not None:
        out.append(bad_expand)
    return out


# ── 登記快照 ─────────────────────────────────────────────────────────────────────────────────
def utc_text(value: Any) -> str | None:
    """帶時區的 datetime → UTC、秒精度（微秒截斷）`YYYY-MM-DDTHH:MM:SS+00:00`；None 原樣。"""
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _norm_host(raw: str) -> str:
    return raw.strip().lower().rstrip(".")


def build_registry_hosts(env_fetch: Iterable[str], env_web: Iterable[str],
                         admin_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """`hosts`：只列啟用者；同一 (list_kind, host) 一筆（部署基底有者記 `ENV`、`layer` 為 null，
    否則 `ADMIN` 並帶該條目的 layer）；間隔＝max(內建下限, 同 (list_kind, host) 啟用中 ADMIN 條目
    的值)；依 (host, list_kind) 的 UTF-8 位元組序遞增。"""
    admin: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in admin_rows:
        if row.get("enabled"):
            admin[(str(row["list_kind"]), _norm_host(str(row["host"])))] = row
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for kind, hosts in (("FETCH", env_fetch), ("WEB", env_web)):
        for raw in hosts:
            host = _norm_host(raw)
            entries[(kind, host)] = {"source": "ENV", "layer": None}
    for (kind, host), row in admin.items():
        entries.setdefault((kind, host), {"source": "ADMIN", "layer": row.get("layer")})
    out: list[dict[str, Any]] = []
    for (kind, host), info in entries.items():
        values = [int(admin[(kind, host)]["min_interval_seconds"])] if (kind, host) in admin else []
        out.append({"host": host, "layer": info["layer"], "list_kind": kind,
                    "min_interval_seconds": max([builtin_floor(host, "/"), *values]),
                    "source": info["source"]})
    out.sort(key=lambda e: (e["host"].encode("utf-8"), e["list_kind"].encode("utf-8")))
    return out


def watch_entry(row: Mapping[str, Any]) -> dict[str, Any]:
    """`watch` 的一個元素（恰十一鍵）。"""
    expand = None
    if row.get("expand_mode") is not None:
        expand = {"mode": row["expand_mode"], "prefix": row["expand_prefix"],
                  "max": int(row["expand_max"])}
    return {"id": row["slug"], "url": row["url"], "kind": row["kind"], "extract": row["extract"],
            "layer": row["layer"], "expand": expand, "enabled": bool(row["enabled"]),
            "added_by": row["added_by"], "added_at": utc_text(row["added_at"]),
            "disabled_by": row.get("disabled_by"), "disabled_at": utc_text(row.get("disabled_at"))}


def build_registry(env_fetch: Iterable[str], env_web: Iterable[str],
                   admin_rows: Sequence[Mapping[str, Any]],
                   watch_rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    """回 `(registry_text, registry_sha256)`。超過上限拋 `RegistryTooLarge`（不回部分內容）。"""
    watch = sorted((watch_entry(r) for r in watch_rows), key=lambda w: w["id"].encode("utf-8"))
    snapshot = {"schema_rev": SCHEMA_REV,
                "hosts": build_registry_hosts(env_fetch, env_web, admin_rows), "watch": watch}
    text = json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    raw = text.encode("utf-8")
    if len(raw) > REGISTRY_TEXT_MAX_BYTES:
        raise RegistryTooLarge(len(raw))
    return text, "sha256:" + hashlib.sha256(raw).hexdigest()
