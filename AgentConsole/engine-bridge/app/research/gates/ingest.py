"""證據入庫的確定性規劃（純函式；ADR-003 D3；AC-R2P-05-1／05-3／05-10）。

agent 寫的 `evidence_items.json` 是憑證（檔→驗→DB）：orchestrator 在行程內以與 evaluator
同一批純函式再驗一次後，由本模組把它整理成要入庫的列、`evidence_matrix.md` 的渲染輸入與
`.evidence_index.json`（供草擬預檢 P0-7 與審查者引用檢查用）。UNANCHORED 由執行層計算：
F2 的數字在抓取原文比對不到者為真，V1 列與沒有抓取原文的宣告型列不比對。
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .evidence import MIN_EVIDENCE_ROWS, compute_unanchored, license_pending_numbers

UNPARSED_HOST = "(unparsed)"
_HOST_RE = re.compile(r"^https://([A-Za-z0-9.-]{1,253})(?::\d+)?(?:[/?#]|$)")
_SOURCE_DB_KEYS = ("source_no", "layer", "tier", "verification", "anchor_kind", "url", "doi",
                   "git_commit", "title", "authors_org", "published_at", "source_type",
                   "license_spdx", "license_note", "clue_only")


@dataclass
class IngestPlan:
    """一版證據的入庫規劃。`items_rendered` 是 `evidence_items.json` 形態再加 `unanchored`。"""

    matrix_version: int
    scope_rev: int
    sources: list[dict[str, Any]] = field(default_factory=list)
    items: list[dict[str, Any]] = field(default_factory=list)
    items_rendered: list[dict[str, Any]] = field(default_factory=list)
    index: dict[str, Any] = field(default_factory=dict)
    searches: list[dict[str, Any]] = field(default_factory=list)
    qualifying: int = 0
    license_pending: list[str] = field(default_factory=list)
    unanchored: list[str] = field(default_factory=list)

    @property
    def enough(self) -> bool:
        """證據列下限：至少 `MIN_EVIDENCE_ROWS` 列層級 V2 以上、非 UNANCHORED、非 clue_only。"""
        return self.qualifying >= MIN_EVIDENCE_ROWS


def _host_of(url: str) -> str:
    match = _HOST_RE.match(url)
    return match.group(1).lower() if match else UNPARSED_HOST


def _number(identifier: object) -> int:
    """`Q-NNN` 的數字部分（驗證通過的檔案必有）。"""
    match = re.search(r"(\d+)$", str(identifier))
    return int(match.group(1)) if match else 0


def _search_row(entry: Mapping[str, Any]) -> dict[str, Any]:
    """agent 宣告的一筆搜尋或抓取紀錄 → `research_fetches` 列（`AGENT_DECLARED`：Bridge
    觀測不到，只認宣告）。"""
    declared = {"layer": entry["layer"], "observed_by": "AGENT_DECLARED",
                "search_no": _number(entry["id"]),
                "result_urls": list(entry.get("result_urls") or []),
                "query_text": entry["query"], "outcome": "OK"}
    if entry["tool"] == "WebFetch":
        url = str(entry["query"])
        return {**declared, "fetch_method": "WEB_FETCH", "url": url, "host": _host_of(url)}
    return {**declared, "fetch_method": "WEB_SEARCH", "url": None, "host": None}


def plan_ingest(doc: Mapping[str, Any], *, matrix_version: int,
                raw_text_of: Callable[[str], str | None],
                known_search_nos: Sequence[int] = ()) -> IngestPlan:
    """整理一版（已驗證的）`evidence_items.json`。`raw_text_of(F-NNNN)` 回該抓取列的原文（沒有回
    None）；`known_search_nos`＝先前版本已入庫的搜尋編號（增補模式只入庫新增的）。"""
    plan = IngestPlan(matrix_version=matrix_version, scope_rev=int(doc["scope_rev"]))
    by_no = {s["source_no"]: s for s in doc["sources"]}
    for src in doc["sources"]:
        row = {key: src.get(key) for key in _SOURCE_DB_KEYS}
        row["fetch_outcome"] = "OK" if src.get("fetch_refs") else None
        plan.sources.append(row)
    for item in doc["items"]:
        src = by_no[item["source_no"]]
        texts = [t for ref in src.get("fetch_refs") or [] if (t := raw_text_of(ref)) is not None]
        flagged = compute_unanchored(item["f2"], item["f7"], texts)
        plan.items.append({
            "evidence_no": item["evidence_no"], "source_no": item["source_no"],
            "candidate": item.get("candidate"), "claim": item["claim"],
            "f1_mechanism": item["f1"], "f2_evidence": item["f2"], "f3_critique": item["f3"],
            "f4_risk_tags": list(item["f4"]), "f5_applicability": dict(item["f5"]),
            "f6_limits": item["f6"], "f7_verification": item["f7"], "strength": item["strength"],
            "unanchored": flagged})
        plan.items_rendered.append({**item, "unanchored": flagged})
        plan.index.setdefault("rows", {})[item["evidence_no"]] = {
            "f7": item["f7"], "strength": item["strength"], "unanchored": flagged,
            "source_no": item["source_no"]}
        if flagged:
            plan.unanchored.append(item["evidence_no"])
        if item["f7"] in ("V2", "V3") and not src.get("clue_only") and not flagged:
            plan.qualifying += 1
    plan.index.setdefault("rows", {})
    plan.license_pending = license_pending_numbers(doc["items"], by_no)
    known = set(known_search_nos)
    plan.searches = [_search_row(e) for e in doc["search_log"] if _number(e["id"]) not in known]
    return plan
