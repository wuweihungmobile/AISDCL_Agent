"""Semantic Scholar：請求網址與 JSON 解析器（學術層；ADR-003 D7；AC-R2P-04-6）。

P0 不使用 API 金鑰（F-R2P-105），所以節流下限取「未帶金鑰」的 3 秒（`allowlist.builtin_floor`）。
回應 `data[]` 的每個 paper 是一個候選來源：url 取 paper 的 `url`（必須 https，否則以 paperId 組
`semanticscholar.org/paper/<id>`）；有 DOI 就以 DOI 為錨（`anchor_kind=DOI`）。查證層級：有摘要
＝V2，沒有摘要＝V1。`venue` 非空視為已發表（`PAPER`），否則 `PREPRINT`。
缺欄寫 `未見`；壞格式（不是 JSON、沒有 `data` 陣列）＝`PARSE_ERROR` 且不產生任何來源列。
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlencode

from .http import MISSING, ParseResult, clean_text, iso_date

LAYER = "ACADEMIC"
HOST = "api.semanticscholar.org"
FIELDS = "title,url,abstract,year,authors,venue,publicationDate,externalIds,citationCount"
MAX_QUERY_WORDS = 8
MAX_AUTHORS = 8
_DOI_MAX = 200               # research_sources.doi 欄寬
_PAPER_ID_RE = re.compile(r"^[0-9a-f]{40}$")


def search_url(query: str, *, limit: int) -> str:
    """paper 搜尋網址（純文字關鍵詞；沒有可用的詞丟 `ValueError`）。"""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.-]*", query)[:MAX_QUERY_WORDS]
    if not words:
        raise ValueError("Semantic Scholar 查詢需要至少一個 ASCII 詞")
    params = {"query": " ".join(words), "limit": limit, "fields": FIELDS}
    return f"https://{HOST}/graph/v1/paper/search?{urlencode(params)}"


def _int_or_missing(value: Any) -> int | str:
    return value if isinstance(value, int) and not isinstance(value, bool) else MISSING


def _row(paper: dict[str, Any]) -> dict[str, Any] | None:
    url, paper_id = paper.get("url"), paper.get("paperId")
    if isinstance(url, str) and url.startswith("https://"):
        link = url.strip()
    elif isinstance(paper_id, str) and _PAPER_ID_RE.match(paper_id):
        link = f"https://www.semanticscholar.org/paper/{paper_id}"
    else:
        return None
    external = paper.get("externalIds")
    doi = clean_text(external.get("DOI")) if isinstance(external, dict) else MISSING
    if doi != MISSING and len(doi) > _DOI_MAX:
        doi = MISSING
    authors_raw = paper.get("authors")
    names = [clean_text(a.get("name")) for a in authors_raw if isinstance(a, dict)] if isinstance(
        authors_raw, list) else []
    names = [n for n in names if n != MISSING]
    authors = ", ".join(names[:MAX_AUTHORS]) + (
        f" 等 {len(names)} 位" if len(names) > MAX_AUTHORS else "")
    return {
        "layer": LAYER, "tier": "T1",
        "verification": "V2" if clean_text(paper.get("abstract")) != MISSING else "V1",
        "anchor_kind": "URL" if doi == MISSING else "DOI", "url": link, "doi": doi,
        "git_commit": None, "title": clean_text(paper.get("title")),
        "authors_org": authors or MISSING, "published_at": iso_date(paper.get("publicationDate")),
        "source_type": "PAPER" if clean_text(paper.get("venue")) != MISSING else "PREPRINT",
        "license_spdx": MISSING, "license_note": MISSING, "clue_only": False,
        "external_id": paper_id if isinstance(paper_id, str) else MISSING,
        "year": _int_or_missing(paper.get("year")),
        "citation_count": _int_or_missing(paper.get("citationCount"))}


def parse(text: str) -> ParseResult:
    """搜尋回應 → 來源列（每個 paper 一筆）。缺可用網址的 paper 略過並在 `detail` 說明筆數。"""
    try:
        doc = json.loads(text)
    except ValueError as exc:
        return ParseResult.error(f"不是合法的 JSON：{exc}")
    data = doc.get("data") if isinstance(doc, dict) else None
    if not isinstance(data, list):
        return ParseResult.error("缺 data 陣列（不是 Semantic Scholar 的搜尋回應）")
    rows = [_row(p) if isinstance(p, dict) else None for p in data]
    kept = tuple(r for r in rows if r is not None)
    skipped = len(rows) - len(kept)
    return ParseResult(True, kept, f"略過 {skipped} 筆缺可用網址的項目" if skipped else "")
