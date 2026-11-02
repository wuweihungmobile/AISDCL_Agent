"""arXiv：請求網址與 Atom 解析器（學術層；ADR-003 D7；AC-R2P-04-6）。

查詢走官方 API（`export.arxiv.org/api/query`，回 `application/atom+xml`）：只收 ASCII 詞並自己組
`all:` 查詢（使用者與 agent 的字串不能把查詢語法的運算子帶進去）。回應的每個 entry 是一個候選來源，
**一律以 https 的 `arxiv.org/abs/<id>` 當定位符**（Atom 的 id 是 http，而 `research_sources.url` 的
CHECK 要求 https）。查證層級：有摘要＝V2（讀過摘要）、沒有摘要＝V1（只見標題與網址）；要到 V3 需另取
`arxiv.org/html/<id>` 的 HTML 全文（`html_url`；無 HTML 版者維持 V2，**不取 PDF**，ADR-003 D7）。

解析器是純函式：輸入文字、輸出 `ParseResult`；壞格式（不是 Atom、不是合法 XML、含 DTD 或實體宣告、
API 以 entry 回報的錯誤）一律 `PARSE_ERROR` 且不產生任何來源列。缺欄寫 `未見`（`MISSING`）。
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode
from xml.etree import ElementTree

from .http import MISSING, ParseResult, clean_text, iso_date

LAYER = "ACADEMIC"
API_HOST = "export.arxiv.org"
SITE_HOST = "arxiv.org"
MAX_QUERY_WORDS = 8
MAX_AUTHORS = 8
_DOI_MAX = 200               # research_sources.doi 欄寬
_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"
#: arXiv 識別碼：新式 `YYMM.NNNN(N)`、舊式 `<主題>/YYMMNNN`，皆可帶 `vN`。
_ARXIV_ID = r"(?:\d{4}\.\d{4,5}|[a-z][A-Za-z.-]*/\d{7})(?:v\d+)?"
_ID_RE = re.compile(rf"^https?://arxiv\.org/abs/(?P<id>{_ARXIV_ID})$")
_SAFE_ID_RE = re.compile(rf"^{_ARXIV_ID}$")


def search_url(query: str, *, max_results: int) -> str:
    """官方 API 的查詢網址：詞以 `AND` 連接的 `all:` 查詢、依相關度排序。沒有可用的 ASCII 詞
    （例如純中文）丟 `ValueError`——arXiv 查不到中文，呼叫端要給英文詞。"""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", query)[:MAX_QUERY_WORDS]
    if not words:
        raise ValueError("arXiv 查詢需要至少一個 ASCII 詞")
    params = {"search_query": " AND ".join(f"all:{w}" for w in words), "start": 0,
              "max_results": max_results, "sortBy": "relevance", "sortOrder": "descending"}
    return f"https://{API_HOST}/api/query?{urlencode(params)}"


def html_url(arxiv_id: str) -> str:
    """V3 用的全文頁（`arxiv.org/html/<id>`）；id 只收 arXiv 識別碼的字元集。"""
    if not _SAFE_ID_RE.match(arxiv_id):
        raise ValueError(f"不是 arXiv 識別碼：{arxiv_id!r}")
    return f"https://{SITE_HOST}/html/{arxiv_id}"


def _child(entry: ElementTree.Element, tag: str, ns: str = _ATOM) -> str | None:
    node = entry.find(f"{ns}{tag}")
    return node.text if node is not None else None


def _entry_row(entry: ElementTree.Element, arxiv_id: str) -> dict[str, Any]:
    abstract = clean_text(_child(entry, "summary"))
    doi = clean_text(_child(entry, "doi", _ARXIV))
    if doi != MISSING and len(doi) > _DOI_MAX:
        doi = MISSING
    names = [clean_text(n.text) for n in entry.findall(f"{_ATOM}author/{_ATOM}name")]
    names = [n for n in names if n != MISSING]
    authors = ", ".join(names[:MAX_AUTHORS]) + (
        f" 等 {len(names)} 位" if len(names) > MAX_AUTHORS else "")
    return {
        "layer": LAYER, "tier": "T1", "verification": "V2" if abstract != MISSING else "V1",
        "anchor_kind": "URL" if doi == MISSING else "DOI",
        "url": f"https://{SITE_HOST}/abs/{arxiv_id}", "doi": doi, "git_commit": None,
        "title": clean_text(_child(entry, "title")), "authors_org": authors or MISSING,
        "published_at": iso_date(_child(entry, "published")), "source_type": "PREPRINT",
        "license_spdx": MISSING, "license_note": MISSING, "clue_only": False,
        "external_id": arxiv_id}


def parse(text: str) -> ParseResult:
    """Atom feed → 來源列（每個 entry 一筆）。沒有 entry 的合法 feed＝零筆（不是錯誤）；缺 id 的
    entry 略過並在 `detail` 說明筆數。"""
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        return ParseResult.error("Atom 含 DTD 或實體宣告，拒絕解析")
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        return ParseResult.error(f"不是合法的 XML：{exc}")
    if root.tag != f"{_ATOM}feed":
        return ParseResult.error(f"根元素不是 Atom feed：{root.tag[:60]}")
    rows: list[dict[str, Any]] = []
    skipped = 0
    for entry in root.findall(f"{_ATOM}entry"):
        entry_id = (_child(entry, "id") or "").strip()
        if "/api/errors" in entry_id:
            reason = clean_text(_child(entry, "summary"))[:200]
            return ParseResult.error(f"arXiv 回報錯誤：{reason}")
        found = _ID_RE.match(entry_id)
        if found is None:
            skipped += 1
            continue
        rows.append(_entry_row(entry, found.group("id")))
    return ParseResult(True, tuple(rows), f"略過 {skipped} 筆缺 id 的項目" if skipped else "")
