"""Stack Exchange：請求網址與 JSON 解析器（社群層；ADR-003 D7）。

社群討論一律是 **T3 線索**（`clue_only=true`，只當搜尋線索、不得被證據項引用）、查證層級 V1
（只見搜尋結果的標題與網址）；定位符是題目頁的 https 連結（`link`，host 是 `stackoverflow.com`
之類，不是 API host，也不會被抓取）。Stack Exchange 的標題與使用者名稱是 HTML 實體編碼過的，
解析時還原成純文字。

節流：官方速率限制頁無法現查（V-R9 殘項，本棒未現查）——`allowlist` 的 3 秒是**保守初值、非事實
宣稱**；回應本文的 `backoff` 欄位（秒）由 `http.body_backoff_seconds` 一律遵守。
壞格式（不是 JSON、沒有 `items` 陣列）＝`PARSE_ERROR` 且不產生來源列；缺欄寫 `未見`。
"""
from __future__ import annotations

import html
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from .http import MISSING, ParseResult, clean_text

LAYER = "COMMUNITY"
HOST = "api.stackexchange.com"
DEFAULT_SITE = "stackoverflow"
API_VERSION = "2.3"
MAX_QUERY_WORDS = 8
_SITE_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,60}$")


def search_url(query: str, *, pagesize: int, site: str = DEFAULT_SITE) -> str:
    """進階搜尋網址（依相關度降冪）。`site` 只收小寫英數、點與連字號；沒有可用的詞丟
    `ValueError`。"""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.#+-]*", query)[:MAX_QUERY_WORDS]
    if not words:
        raise ValueError("Stack Exchange 查詢需要至少一個 ASCII 詞")
    if not _SITE_RE.match(site):
        raise ValueError(f"不合規的 site：{site!r}")
    params = {"order": "desc", "sort": "relevance", "q": " ".join(words), "site": site,
              "pagesize": pagesize}
    return f"https://{HOST}/{API_VERSION}/search/advanced?{urlencode(params)}"


def _plain(value: Any) -> str:
    return clean_text(html.unescape(value)) if isinstance(value, str) else MISSING


def _created(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10**11:
        return datetime.fromtimestamp(value, UTC).date().isoformat()
    return MISSING


def _row(item: dict[str, Any]) -> dict[str, Any] | None:
    link = item.get("link")
    if not isinstance(link, str) or not link.startswith("https://"):
        return None
    owner = item.get("owner")
    tags = item.get("tags")
    return {
        "layer": LAYER, "tier": "T3", "verification": "V1", "anchor_kind": "URL",
        "url": link.strip(), "doi": None, "git_commit": None, "title": _plain(item.get("title")),
        "authors_org": _plain(owner.get("display_name")) if isinstance(owner, dict) else MISSING,
        "published_at": _created(item.get("creation_date")), "source_type": "FORUM",
        "license_spdx": MISSING, "license_note": MISSING, "clue_only": True,
        "external_id": str(item["question_id"]) if isinstance(
            item.get("question_id"), int) else MISSING,
        "score": item["score"] if isinstance(item.get("score"), int) else MISSING,
        "is_answered": item.get("is_answered") is True,
        "answer_count": item["answer_count"] if isinstance(item.get("answer_count"), int)
        else MISSING,
        "tags": [t for t in tags if isinstance(t, str)] if isinstance(tags, list) else []}


def parse(text: str) -> ParseResult:
    """搜尋回應 → 來源列（每個題目一筆，一律 T3 線索）。缺 https 連結的項目略過並說明筆數。"""
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return ParseResult.error(f"不是合法的 JSON：{exc}")
    items = doc.get("items") if isinstance(doc, dict) else None
    if not isinstance(items, list):
        return ParseResult.error("缺 items 陣列（不是 Stack Exchange 的搜尋回應）")
    rows = [_row(it) if isinstance(it, dict) else None for it in items]
    kept = tuple(r for r in rows if r is not None)
    skipped = len(rows) - len(kept)
    return ParseResult(True, kept, f"略過 {skipped} 筆缺 https 連結的項目" if skipped else "")
