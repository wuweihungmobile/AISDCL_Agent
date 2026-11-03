"""`evidence_items.json` 的確定性驗證、強度函式、數字錨定與定位符去重（模板 EVIDENCE-MATRIX §2、
§3）。

agent（`research-analyst`）只寫可機驗的 JSON；本模組是驗證端（`gate_cli evidence` 與入庫前各跑一
次）。
驗證規則是模板 §2.3 的 16 條，違規的 `rule` 取 `R1`～`R16`：

  R1 結構　R2 編號　R3 錨定　R4 URL 出處　R5 分級　R6 V3 條件　R7 證據項綁定　R8 欄位完整
  R9 儲存格紀律　R10 數字登錄　R11 反證　R12 強度　R13 無孤兒來源　R14 誠實劃界　R15 增補只增不改
  R16 雜湊與抓取 id 原樣抄寫

`UNANCHORED` 由執行層計算（`compute_unanchored`），研究者不寫：JSON 帶 `unanchored` 鍵或在 `f4` 寫
`UNANCHORED` 一律被拒（R1／R8）。本模組**不**用 `urllib`（能力登記：網址解析只准在 `fetch/`），
網址正規化用
自己的 regex。
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .schemas import (
    AXIS_REGISTRY,
    LAYERS,
    MISSING_TEXT,
    RISK_TAG_REGISTRY,
    SCHEMA_REV,
    Violation,
    axis_ids,
    has_line_break,
    is_int,
    parse_offset_datetime,
)

CELL_MAX_CHARS = 600                      # 儲存格上限（初值、未校準；超長搬 notes/E-NNN.md）
MIN_EVIDENCE_ROWS = 3                     # 證據列下限（初值、未校準；PRD §5.1.1）
#: 模板範例的議題檔雜湊哨兵（全 0 結尾 1）：只在部署明確指定替身 claude 時接受（見
#: `EvidenceContext`）。
TEMPLATE_SENTINEL_SHA256 = "0" * 63 + "1"

TIERS = ("T1", "T2", "T3")
VERIFICATIONS = ("V1", "V2", "V3")
ANCHOR_KINDS = ("URL", "DOI", "COMMIT")
SOURCE_TYPES = ("PAPER", "PREPRINT", "ENG_BLOG", "WHITEPAPER", "PATENT", "REPO", "ISSUE_PR",
                "FORUM", "DOC", "OTHER")
GRADES = ("A", "M", "N")
STRENGTHS = ("CANDIDATE", "WEAK", "MEDIUM", "STRONG")
CONCLUSIONS = ("WEAKEN", "LIMIT", "IRRELEVANT", "NOT_FOUND", "NOT_SEARCHED")
SEARCH_TOOLS = ("WebSearch", "WebFetch")
#: 風險標籤中會把強度封頂在 MEDIUM 的三個（模板 §3.3 封頂列）。
CAPPING_TAGS = frozenset({"IMM", "SELF", "SCOPE"})
#: 授權「未見」的寫法（D-80；比對一律大小寫不敏感、先修剪空白）：空字串、agent 依模板「查不到寫
#: UNKNOWN」的值、模板的「未見」。`None`（DB 的 NULL）另判。
_LICENSE_UNKNOWN_FORMS = frozenset({"", "unknown", MISSING_TEXT})
#: SPDX 複合表達式的連接詞：以空白或括號與前後分隔的 `OR`／`AND`／`WITH`；`GPL-3.0-or-later` 的
#: `-or-` 是識別碼的一部分（前後是連字號），不算。
_COMPOSITE_LICENSE_RE = re.compile(r"(?:^|[\s()])(?:OR|AND|WITH)(?:[\s()]|$)", re.IGNORECASE)
#: GPL／AGPL 系（AC-R2P-05-5）。字界 `\b` 使 `LGPL` 不命中（`GPL` 前面是字母）：LGPL 是已知授權。
_GPL_FAMILY_RE = re.compile(r"\bA?GPL", re.IGNORECASE)

_NO_RE = {"Q": re.compile(r"^Q-\d{3,4}$"), "S": re.compile(r"^S-\d{3,4}$"),
          "E": re.compile(r"^E-\d{3,4}$")}
_FETCH_NO_RE = re.compile(r"^F-\d{4,}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TOP_KEYS = frozenset({"schema_rev", "issue_scope_sha256", "scope_rev", "search_log", "sources",
                       "items", "counter_evidence", "honest_bounds"})
_SEARCH_KEYS = frozenset({"id", "layer", "tool", "query", "at", "result_urls"})
_SOURCE_KEYS = frozenset({"source_no", "layer", "tier", "verification", "anchor_kind", "url", "doi",
                          "git_commit", "title", "authors_org", "published_at", "source_type",
                          "license_spdx", "license_note", "clue_only", "fetch_refs"})
_ITEM_KEYS = frozenset({"evidence_no", "source_no", "scope_rev", "candidate", "claim", "f1", "f2",
                        "f3", "f4", "f5", "f6", "f7", "strength"})
_COUNTER_KEYS = frozenset({"evidence_no", "search_id", "conclusion", "source_no", "note"})
_BOUNDS_KEYS = frozenset({"not_found", "summary_only", "not_read_fully"})
_NOT_FOUND_KEYS = frozenset({"query", "date", "result"})
_TEXT_FIELDS_ITEM = ("claim", "f1", "f2", "f3", "f6")


@dataclass(frozen=True)
class EvidenceContext:
    """驗證的外部輸入（皆由任務書／Bridge 提供，研究者無從自算）。

    `issue_scope`：議題檔物件（取 `applicability_axes` 與 `scope_rev`）；
    `issue_scope_sha256`：現行議題檔的換行正規化雜湊；`accept_template_sentinel`：研究劇本模式
    （`MOCK_CLAUDE_RESEARCH_SCRIPT` 取值去除空白後非空；orchestrator 兩處以此設值）時，模板範例的
    哨兵雜湊也算過——劇本是靜態檔、算不出含 `created_at` 的真雜湊，真 claude 的輸出仍須逐位元等於
    任務書給的值；
    `fetch_index`：`F-NNNN` → 抓取列摘要；`previous`：前一版 `evidence_items.json`（增補模式）。"""

    issue_scope: Mapping[str, Any] | None = None
    issue_scope_sha256: str | None = None
    accept_template_sentinel: bool = False
    fetch_index: Mapping[str, Mapping[str, Any]] | None = None
    previous: Mapping[str, Any] | None = None


@dataclass
class _Check:
    out: list[Violation] = field(default_factory=list)

    def bad(self, rule: str, path: str, message: str) -> None:
        self.out.append(Violation(rule, path, message))


# ══ strength 函式（模板 §3.3）═══════════════════════════════════════════════════════════════
def strength(tier: str, f7: str, f4: Iterable[str], conclusion: str) -> str:
    """先依來源分級與查證層級取基準，再依反證結論與風險標籤調整（只降不升）。

    基準：`f7=V1`→CANDIDATE；T1 且 V3→STRONG；（T1 且 V2）或（T2 且 V3）→MEDIUM；T2 且 V2→WEAK；
    反證 WEAKEN 降一級（CANDIDATE 不再降）；NOT_FOUND／NOT_SEARCHED 上限 MEDIUM；LIMIT／IRRELEVANT
    不變；`f4` 含 IMM、SELF 或 SCOPE 其一上限 MEDIUM（只含 LOCK、DEP、LIC、SEC、COMP 不封頂）。"""
    if f7 == "V1" or tier not in ("T1", "T2"):
        return "CANDIDATE"
    base = {("T1", "V3"): "STRONG", ("T1", "V2"): "MEDIUM", ("T2", "V3"): "MEDIUM",
            ("T2", "V2"): "WEAK"}.get((tier, f7))
    if base is None:
        return "CANDIDATE"
    level, medium = STRENGTHS.index(base), STRENGTHS.index("MEDIUM")
    if conclusion == "WEAKEN":
        level = max(0, level - 1)
    elif conclusion in ("NOT_FOUND", "NOT_SEARCHED"):
        level = min(level, medium)
    if CAPPING_TAGS & set(f4):
        level = min(level, medium)
    return STRENGTHS[level]


# ══ 驗證（16 條）═══════════════════════════════════════════════════════════════════════════
def validate_evidence_items(doc: Any, ctx: EvidenceContext | None = None) -> list[Violation]:
    """對 `evidence_items.json` 跑全部規則，回違規清單（空＝合格）。

    結構錯到無法繼續時只回結構違規。"""
    ctx = ctx or EvidenceContext()
    check = _Check()
    if not isinstance(doc, Mapping):
        return [Violation("R1", "$", "evidence_items.json 須為 JSON 物件")]
    _check_top(doc, ctx, check)
    sections = _typed_sections(doc, check)
    if sections is None:
        return check.out
    search_log, sources, items, counters = sections
    _check_search_log(search_log, check)
    _check_sources(sources, search_log, ctx, check)
    _check_items(items, sources, ctx, check)
    _check_counter(counters, items, sources, search_log, doc.get("honest_bounds"), check)
    _check_orphans(sources, items, counters, check)
    _check_bounds(doc.get("honest_bounds"), sources, check)
    _check_cells(doc, check)
    _check_supplement(doc, ctx, check)
    return check.out


def _typed_sections(doc: Mapping[str, Any], check: _Check
                    ) -> tuple[list[Any], list[Any], list[Any], list[Any]] | None:
    ok = True
    parts: list[list[Any]] = []
    for key in ("search_log", "sources", "items", "counter_evidence"):
        value = doc.get(key)
        if not isinstance(value, list) or any(not isinstance(i, Mapping) for i in value):
            check.bad("R1", key, f"{key} 須為物件陣列")
            ok = False
        parts.append(value if isinstance(value, list) else [])
    if not isinstance(doc.get("honest_bounds"), Mapping):
        check.bad("R1", "honest_bounds", "honest_bounds 須為物件")
        ok = False
    return (parts[0], parts[1], parts[2], parts[3]) if ok else None


def _exact_keys(obj: Mapping[str, Any], expected: frozenset[str], path: str, check: _Check) -> None:
    for key in sorted(set(obj) - expected):
        extra = "（UNANCHORED 由執行層計算，研究者不寫）" if key == "unanchored" else ""
        check.bad("R1", f"{path}.{key}", f"多餘的欄位 {key}{extra}")
    for key in sorted(expected - set(obj)):
        check.bad("R1", f"{path}.{key}", f"缺必填欄位 {key}")


def _check_top(doc: Mapping[str, Any], ctx: EvidenceContext, check: _Check) -> None:
    _exact_keys(doc, _TOP_KEYS, "$", check)
    if doc.get("schema_rev") != SCHEMA_REV or not is_int(doc.get("schema_rev")):
        check.bad("R1", "schema_rev", f"schema_rev 須為 {SCHEMA_REV}")
    if not is_int(doc.get("scope_rev")) or doc["scope_rev"] < 1:
        check.bad("R1", "scope_rev", "scope_rev 須為 ≥1 的整數")
    elif ctx.issue_scope is not None and ctx.issue_scope.get("scope_rev") != doc["scope_rev"]:
        check.bad("R16", "scope_rev",
                  f"scope_rev 須等於現行議題檔的 {ctx.issue_scope.get('scope_rev')}")
    value = doc.get("issue_scope_sha256")
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        check.bad("R16", "issue_scope_sha256", "issue_scope_sha256 須為 64 位小寫 hex")
    elif ctx.issue_scope_sha256 is not None and value != ctx.issue_scope_sha256 and not (
            ctx.accept_template_sentinel and value == TEMPLATE_SENTINEL_SHA256):
        check.bad("R16", "issue_scope_sha256", "須逐位元等於任務書給的現行議題檔雜湊（原樣抄寫）")


def _check_no(value: Any, kind: str, path: str, seen: set[str], check: _Check) -> None:
    if not isinstance(value, str) or not _NO_RE[kind].fullmatch(value):
        check.bad("R2", path, f"編號須為 {kind}-NNN（3～4 位數字）：{value!r}")
    elif value in seen:
        check.bad("R2", path, f"編號重複：{value}")
    elif isinstance(value, str):
        seen.add(value)


def _check_search_log(search_log: list[Any], check: _Check) -> None:
    seen: set[str] = set()
    for i, entry in enumerate(search_log):
        path = f"search_log[{i}]"
        _exact_keys(entry, _SEARCH_KEYS, path, check)
        _check_no(entry.get("id"), "Q", f"{path}.id", seen, check)
        if entry.get("layer") not in LAYERS:
            check.bad("R1", f"{path}.layer", f"layer 須為 {'｜'.join(LAYERS)}")
        if entry.get("tool") not in SEARCH_TOOLS:
            check.bad("R1", f"{path}.tool", f"tool 須為 {'｜'.join(SEARCH_TOOLS)}")
        if not isinstance(entry.get("query"), str) or not entry.get("query"):
            check.bad("R1", f"{path}.query", "query 須為非空字串")
        if parse_offset_datetime(entry.get("at")) is None:
            check.bad("R1", f"{path}.at", "at 須為帶時區 offset 的 ISO-8601")
        urls = entry.get("result_urls")
        if not isinstance(urls, list) or any(
                not isinstance(u, str) or not u.startswith("https://") for u in urls):
            check.bad("R1", f"{path}.result_urls", "result_urls 須為 https 字串陣列（可空）")


def _check_sources(sources: list[Any], search_log: list[Any], ctx: EvidenceContext,
                   check: _Check) -> None:
    seen: set[str] = set()
    listed = {u for e in search_log for u in (e.get("result_urls") or []) if isinstance(u, str)}
    listed |= {e["query"] for e in search_log if e.get("tool") == "WebFetch"
               and isinstance(e.get("query"), str)}
    for i, src in enumerate(sources):
        path = f"sources[{i}]"
        _exact_keys(src, _SOURCE_KEYS, path, check)
        _check_no(src.get("source_no"), "S", f"{path}.source_no", seen, check)
        _check_source_fields(src, path, check)
        refs = src.get("fetch_refs")
        refs = refs if isinstance(refs, list) else []
        url = src.get("url")
        if isinstance(url, str) and url not in listed and not refs:
            check.bad("R4", f"{path}.url",
                      "來源網址須出現在某筆 search_log 的 result_urls，或該來源的 fetch_refs 非空")
        _check_fetch_refs(refs, path, ctx, check)
        _check_tier(src, path, check)
        if src.get("verification") == "V3" and not refs:
            check.bad("R6", f"{path}.verification", "verification=V3 須有非空的 fetch_refs")


def _check_source_fields(src: Mapping[str, Any], path: str, check: _Check) -> None:
    if src.get("layer") not in LAYERS:
        check.bad("R1", f"{path}.layer", f"layer 須為 {'｜'.join(LAYERS)}")
    if src.get("source_type") not in SOURCE_TYPES:
        check.bad("R1", f"{path}.source_type", f"source_type 須為 {'｜'.join(SOURCE_TYPES)}")
    for key in ("title", "authors_org", "license_note"):
        if not isinstance(src.get(key), str) or not src.get(key):
            check.bad("R8", f"{path}.{key}", f"{key} 須為非空字串（缺資訊寫「{MISSING_TEXT}」）")
    published = src.get("published_at")
    if published is not None and not (isinstance(published, str) and _DATE_RE.fullmatch(published)):
        check.bad("R1", f"{path}.published_at", "published_at 須為 YYYY-MM-DD 或 null")
    spdx = src.get("license_spdx")
    if spdx is not None and (not isinstance(spdx, str) or not spdx):
        check.bad("R1", f"{path}.license_spdx", "license_spdx 須為 SPDX 字串或 null")
    if src.get("source_type") == "REPO" and spdx is None:
        check.bad("R8", f"{path}.license_spdx", "開源 repo 必填 license_spdx（查不到寫 UNKNOWN）")
    if not isinstance(src.get("clue_only"), bool):
        check.bad("R1", f"{path}.clue_only", "clue_only 須為布林")
    url = src.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        check.bad("R3", f"{path}.url", "來源網址須為 https://")
    kind = src.get("anchor_kind")
    if kind not in ANCHOR_KINDS:
        check.bad("R3", f"{path}.anchor_kind", f"anchor_kind 須為 {'｜'.join(ANCHOR_KINDS)}")
    doi, commit = src.get("doi"), src.get("git_commit")
    if kind == "DOI" and not (isinstance(doi, str) and doi):
        check.bad("R3", f"{path}.doi", "anchor_kind=DOI 時 doi 須非空")
    if kind == "COMMIT" and not (isinstance(commit, str) and _COMMIT_RE.fullmatch(commit)):
        check.bad("R3", f"{path}.git_commit", "anchor_kind=COMMIT 時 git_commit 須為 40 位小寫 hex")
    if commit is not None and not (isinstance(commit, str) and _COMMIT_RE.fullmatch(commit)):
        check.bad("R3", f"{path}.git_commit", "git_commit 須為 40 位小寫 hex 或 null")


def _check_fetch_refs(refs: list[Any], path: str, ctx: EvidenceContext, check: _Check) -> None:
    for j, ref in enumerate(refs):
        where = f"{path}.fetch_refs[{j}]"
        if not isinstance(ref, str) or not _FETCH_NO_RE.fullmatch(ref):
            check.bad("R16", where, f"抓取紀錄編號須為 F-NNNN：{ref!r}")
        elif ctx.fetch_index is not None:
            row = ctx.fetch_index.get(ref)
            if row is None:
                check.bad("R16", where, f"{ref} 不是本專案的抓取紀錄")
            elif row.get("observed_by") != "BRIDGE" or row.get("outcome") != "OK":
                check.bad("R16", where, f"{ref} 必須是 Bridge 觀測且 outcome 為 OK 的抓取列")


def _check_tier(src: Mapping[str, Any], path: str, check: _Check) -> None:
    tier, clue = src.get("tier"), src.get("clue_only")
    if tier not in TIERS:
        check.bad("R5", f"{path}.tier", f"tier 須為 {'｜'.join(TIERS)}")
    elif isinstance(clue, bool):
        if tier == "T3" and not clue:
            check.bad("R5", f"{path}.clue_only", "tier=T3 須 clue_only=true（只當搜尋線索）")
        if tier in ("T1", "T2") and clue:
            check.bad("R5", f"{path}.clue_only", f"tier={tier} 須 clue_only=false")
    if src.get("verification") not in VERIFICATIONS:
        check.bad("R5", f"{path}.verification",
                  f"verification 須為 {'｜'.join(VERIFICATIONS)}（V0 憑記憶不得列入）")


def _check_items(items: list[Any], sources: list[Any], ctx: EvidenceContext,
                 check: _Check) -> None:
    by_no = {s.get("source_no"): s for s in sources}
    axes = _expected_axes(ctx)
    seen: set[str] = set()
    for i, item in enumerate(items):
        path = f"items[{i}]"
        _exact_keys(item, _ITEM_KEYS, path, check)
        _check_no(item.get("evidence_no"), "E", f"{path}.evidence_no", seen, check)
        if not is_int(item.get("scope_rev")) or item["scope_rev"] < 1:
            check.bad("R1", f"{path}.scope_rev", "scope_rev 須為 ≥1 的整數")
        cand = item.get("candidate")
        if cand is not None and (not isinstance(cand, str) or not cand):
            check.bad("R1", f"{path}.candidate", "candidate 須為候選技術名或 null")
        for key in _TEXT_FIELDS_ITEM:
            if not isinstance(item.get(key), str) or not item.get(key).strip():
                check.bad("R8", f"{path}.{key}",
                          f"{key} 須為非空字串（缺資訊寫「{MISSING_TEXT}」）")
        _check_f4(item.get("f4"), path, check)
        _check_f5(item.get("f5"), axes, path, check)
        src = by_no.get(item.get("source_no"))
        if src is None:
            check.bad("R7", f"{path}.source_no", f"來源 {item.get('source_no')!r} 不存在於 sources")
        else:
            if src.get("clue_only") is True or src.get("tier") == "T3":
                check.bad("R5", f"{path}.source_no",
                          f"證據項不得引用 T3／clue_only 來源（{item.get('source_no')}）")
            f7, verification = item.get("f7"), src.get("verification")
            if f7 not in VERIFICATIONS:
                check.bad("R7", f"{path}.f7", f"f7 須為 {'｜'.join(VERIFICATIONS)}")
            elif verification in VERIFICATIONS and VERIFICATIONS.index(f7) > VERIFICATIONS.index(
                    verification):
                check.bad("R7", f"{path}.f7", f"f7={f7} 不得高於來源的 verification={verification}")
        if item.get("strength") not in STRENGTHS:
            check.bad("R12", f"{path}.strength", f"strength 須為 {'｜'.join(STRENGTHS)}")


def _expected_axes(ctx: EvidenceContext) -> frozenset[str]:
    if ctx.issue_scope is None:
        return frozenset(AXIS_REGISTRY)
    labels = ctx.issue_scope.get("applicability_axes")
    return frozenset(axis_ids(labels if isinstance(labels, list) else []))


def _check_f4(value: Any, path: str, check: _Check) -> None:
    if not isinstance(value, list) or any(not isinstance(t, str) for t in value):
        check.bad("R8", f"{path}.f4", "f4 須為風險標籤字串陣列（可空）")
        return
    for tag in value:
        if tag not in RISK_TAG_REGISTRY:
            hint = ""
            if tag == "UNANCHORED":
                hint = "（UNANCHORED 由執行層計算，不是模板登錄的風險標籤）"
            check.bad("R8", f"{path}.f4", f"風險標籤 {tag!r} 不在登錄表內{hint}")


def _check_f5(value: Any, axes: frozenset[str], path: str, check: _Check) -> None:
    if not isinstance(value, Mapping):
        check.bad("R8", f"{path}.f5", "f5 須為以軸 id 為鍵的物件")
        return
    if set(value) != set(axes):
        check.bad("R8", f"{path}.f5",
                  f"f5 的鍵須恰等於議題軸集合 {sorted(axes)}，收到 {sorted(value)}")
    for axis, cell in value.items():
        if not isinstance(cell, Mapping) or set(cell) != {"grade", "reason"}:
            check.bad("R8", f"{path}.f5.{axis}", "每軸須為 {grade, reason}")
        elif cell.get("grade") not in GRADES or not isinstance(cell.get("reason"), str) or not (
                cell.get("reason") or "").strip():
            check.bad("R8", f"{path}.f5.{axis}", f"grade 須為 {'｜'.join(GRADES)} 且 reason 非空")


def _check_counter(counters: list[Any], items: list[Any], sources: list[Any],
                   search_log: list[Any], bounds: Any, check: _Check) -> None:
    item_nos = [i.get("evidence_no") for i in items]
    source_nos = {s.get("source_no") for s in sources}
    queries = {e.get("id"): e.get("query") for e in search_log}
    not_found = {nf.get("query") for nf in (bounds or {}).get("not_found", [])
                 if isinstance(nf, Mapping)} if isinstance(bounds, Mapping) else set()
    per_item: dict[Any, int] = {}
    by_item = {i.get("evidence_no"): i for i in items}
    src_by_no = {s.get("source_no"): s for s in sources}
    for j, entry in enumerate(counters):
        path = f"counter_evidence[{j}]"
        _exact_keys(entry, _COUNTER_KEYS, path, check)
        no = entry.get("evidence_no")
        per_item[no] = per_item.get(no, 0) + 1
        if no not in item_nos:
            check.bad("R11", f"{path}.evidence_no", f"反證指向不存在的證據項 {no!r}")
        _check_counter_rules(entry, path, source_nos, queries, not_found, check)
        item, src = by_item.get(no), src_by_no.get(by_item.get(no, {}).get("source_no"))
        conclusion = entry.get("conclusion")
        if item is not None and src is not None and conclusion in CONCLUSIONS and isinstance(
                item.get("f4"), list) and item.get("strength") in STRENGTHS:
            want = strength(str(src.get("tier")), str(item.get("f7")), item["f4"], conclusion)
            if item["strength"] != want:
                check.bad("R12", f"items[{item_nos.index(no)}].strength",
                          f"strength 須等於函式值 {want}（收到 {item['strength']}）")
    for no in item_nos:
        if per_item.get(no, 0) != 1:
            check.bad("R11", "counter_evidence",
                      f"證據項 {no} 須恰有一筆反證（現有 {per_item.get(no, 0)}）")


def _check_counter_rules(entry: Mapping[str, Any], path: str, source_nos: set[Any],
                         queries: Mapping[Any, Any], not_found: set[Any], check: _Check) -> None:
    conclusion, search_id = entry.get("conclusion"), entry.get("search_id")
    if conclusion not in CONCLUSIONS:
        check.bad("R11", f"{path}.conclusion", f"conclusion 須為 {'｜'.join(CONCLUSIONS)}")
        return
    if not isinstance(entry.get("note"), str) or not entry.get("note"):
        check.bad("R11", f"{path}.note", "note 須為非空字串")
    if search_id is not None and search_id not in queries:
        check.bad("R11", f"{path}.search_id", f"search_id {search_id!r} 不在 search_log")
    if conclusion == "NOT_FOUND":
        if search_id is None:
            check.bad("R11", f"{path}.search_id", "NOT_FOUND 必附 search_id")
        elif queries.get(search_id) not in not_found:
            check.bad("R11", f"{path}.search_id",
                      "NOT_FOUND 的搜尋字串必須同時出現在 honest_bounds.not_found")
    if conclusion == "NOT_SEARCHED" and search_id is not None:
        check.bad("R11", f"{path}.search_id", "NOT_SEARCHED 不得附 search_id")
    if conclusion in ("WEAKEN", "LIMIT", "IRRELEVANT") and entry.get("source_no") not in source_nos:
        check.bad("R11", f"{path}.source_no", f"{conclusion} 必附存在於 sources 的 source_no")


def _check_orphans(sources: list[Any], items: list[Any], counters: list[Any],
                   check: _Check) -> None:
    cited = {i.get("source_no") for i in items} | {c.get("source_no") for c in counters}
    for i, src in enumerate(sources):
        if src.get("clue_only") is False and src.get("source_no") not in cited:
            check.bad("R13", f"sources[{i}]",
                      f"非線索來源 {src.get('source_no')} 沒有被任何證據項或反證引用")


def _check_bounds(bounds: Any, sources: list[Any], check: _Check) -> None:
    if not isinstance(bounds, Mapping):
        return
    _exact_keys(bounds, _BOUNDS_KEYS, "honest_bounds", check)
    for j, nf in enumerate(bounds.get("not_found") or []):
        if not isinstance(nf, Mapping) or set(nf) != _NOT_FOUND_KEYS or any(
                not isinstance(nf.get(k), str) or not nf.get(k) for k in _NOT_FOUND_KEYS):
            check.bad("R14", f"honest_bounds.not_found[{j}]", "須為 {query, date, result} 非空字串")
    for key in ("summary_only", "not_read_fully"):
        value = bounds.get(key)
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            check.bad("R14", f"honest_bounds.{key}", f"{key} 須為來源編號陣列")
    summary = set(bounds.get("summary_only") or []) if isinstance(
        bounds.get("summary_only"), list) else set()
    unread = set(bounds.get("not_read_fully") or []) if isinstance(
        bounds.get("not_read_fully"), list) else set()
    for src in sources:
        no, verification = src.get("source_no"), src.get("verification")
        if verification in ("V1", "V2") and no not in summary:
            check.bad("R14", "honest_bounds.summary_only", f"summary_only 須涵蓋 V1／V2 來源 {no}")
        if verification in ("V1", "V2") and no not in unread:
            check.bad("R14", "honest_bounds.not_read_fully",
                      f"not_read_fully 須涵蓋非 V3 來源 {no}")


def _iter_strings(value: Any, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for key, sub in value.items():
            yield from _iter_strings(sub, f"{path}.{key}")
    elif isinstance(value, list):
        for index, sub in enumerate(value):
            yield from _iter_strings(sub, f"{path}[{index}]")


def _check_cells(doc: Mapping[str, Any], check: _Check) -> None:
    """R9：所有文字欄位不得含管線字元與換行，每欄 ≤600 字元（超長改指向 notes/E-NNN.md）。"""
    for key in ("search_log", "sources", "items", "counter_evidence", "honest_bounds"):
        for path, text in _iter_strings(doc.get(key), key):
            if "|" in text:
                check.bad("R9", path, "文字欄位不得含管線字元 |")
            if has_line_break(text):
                check.bad("R9", path, "文字欄位不得含換行")
            if len(text) > CELL_MAX_CHARS:
                check.bad("R9", path,
                          f"超過 {CELL_MAX_CHARS} 字元：改以「見 notes/E-NNN.md」指向附註檔")


def _check_supplement(doc: Mapping[str, Any], ctx: EvidenceContext, check: _Check) -> None:
    """R15：有前一版時，新版逐位元保留其全部 sources、items、search_log；編號延續；只准新增。"""
    prev = ctx.previous
    if prev is None:
        return
    for key, id_key in (("sources", "source_no"), ("items", "evidence_no"), ("search_log", "id")):
        old = [e for e in (prev.get(key) or []) if isinstance(e, Mapping)]
        new = [e for e in (doc.get(key) or []) if isinstance(e, Mapping)]
        new_by_id = {e.get(id_key): e for e in new}
        for entry in old:
            now = new_by_id.get(entry.get(id_key))
            if now is None:
                check.bad("R15", key, f"增補只增不改：前一版的 {entry.get(id_key)} 被刪除")
            elif now != entry:
                check.bad("R15", f"{key}.{entry.get(id_key)}",
                          f"增補只增不改：前一版的 {entry.get(id_key)} 內容被改動")
        old_nos = [_number_of(e.get(id_key)) for e in old]
        floor = max([n for n in old_nos if n is not None], default=0)
        old_ids = {e.get(id_key) for e in old}
        for entry in new:
            number = _number_of(entry.get(id_key))
            if entry.get(id_key) not in old_ids and number is not None and number <= floor:
                check.bad("R15", f"{key}.{entry.get(id_key)}",
                          f"增補只增不改：新編號須延續（須大於前一版最大號 {floor}）")


def _number_of(identifier: Any) -> int | None:
    match = re.search(r"-(\d+)$", identifier) if isinstance(identifier, str) else None
    return int(match.group(1)) if match else None


# ══ 授權待查（模板 §4.1 統計行；資安審查輸入）═══════════════════════════════════════════════════
def is_license_unknown(license_spdx: str | None) -> bool:
    """授權條款「未見」：`null`、空白、`UNKNOWN`、`未見`（大小寫不敏感）。矩陣的授權欄把這些一律渲染成
    `未見`（D-70），「授權待查」計數也以它為首要判準，兩處共用這一個函式。"""
    return license_spdx is None or license_spdx.strip().casefold() in _LICENSE_UNKNOWN_FORMS


def is_license_pending(license_spdx: str | None) -> bool:
    """授權待查（D-80；矩陣頁頂計數與資安審查輸入；前端 `isLicensePending` 與它對拍同一張期望表
    `tests/fixtures/research/license_pending_cases.json`）：
      · 授權為「未見」（見 `is_license_unknown`）＝待查；
      · 含 `OR`／`AND`／`WITH` 的複合表達式＝知道授權、要人判，原樣顯示、**不**待查（即使有 GPL）；
      · 其餘依 GPL／AGPL 系判（`\\bA?GPL`）；LGPL 等已知授權不待查。"""
    if is_license_unknown(license_spdx):
        return True
    text = str(license_spdx).strip()
    if _COMPOSITE_LICENSE_RE.search(text):
        return False
    return _GPL_FAMILY_RE.search(text) is not None


def license_pending_numbers(items: Sequence[Mapping[str, Any]],
                            sources: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """授權待查的證據編號（依 E 編號序）；`sources` 以 `source_no` 為鍵。"""
    return [i["evidence_no"] for i in items
            if is_license_pending((sources.get(i["source_no"]) or {}).get("license_spdx"))]


# ══ F2 數字錨定（模板 §2.3 規則 10；由執行層計算）══════════════════════════════════════════════
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _normalize_numeric_text(text: str) -> str:
    """字面與正規化比對用：移除千分位逗號、數字與單位間空白、小數尾端的零。"""
    squeezed = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    squeezed = re.sub(r"(?<=\d)\s+(?=[%A-Za-z])", "", squeezed)
    return re.sub(r"(\d+\.\d*?)0+(?![\d])", lambda m: m.group(1).rstrip("."), squeezed)


def number_tokens(f2: str) -> list[str]:
    """`f2` 內的數字 token（已正規化；去重保序）。"""
    seen: dict[str, None] = {}
    for match in _NUMBER_RE.finditer(_normalize_numeric_text(f2)):
        seen.setdefault(match.group(0), None)
    return list(seen)


def compute_unanchored(f2: str, f7: str, raw_texts: Sequence[str]) -> bool:
    """F2 的數字 token 有任何一個在抓取原文中（字面或正規化後）找不到＝`UNANCHORED`。V1 列與沒有
    抓取原文的宣告型列不比對（回 False）。"""
    if f7 == "V1" or not raw_texts:
        return False
    haystack = _normalize_numeric_text("\n".join(raw_texts))
    for token in number_tokens(f2):
        if re.search(rf"(?<![\d.]){re.escape(token)}(?!\d)", haystack) is None:
            return True
    return False


# ══ 定位符正規化與去重（模板 §4；AC-R2P-05-6）════════════════════════════════════════════════
_TRACKING_PARAMS = re.compile(r"^(utm_[a-z]+|fbclid|gclid|mc_cid|mc_eid|igshid|ref_src)$", re.I)
_URL_RE = re.compile(r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*)://(?P<host>[^/?#]*)(?P<path>[^?#]*)"
                     r"(?:\?(?P<query>[^#]*))?(?:#.*)?$")


def normalize_locator(url: str | None = None, doi: str | None = None) -> str:
    """定位符的正規形：DOI 小寫（有 DOI 優先）；URL 去追蹤參數與 fragment、去尾斜線、scheme 與
    host 小寫、其餘參數依字典序。不是網址的字串原樣回傳（去頭尾空白）。"""
    if doi:
        return "doi:" + doi.strip().lower()
    text = (url or "").strip()
    match = _URL_RE.match(text)
    if match is None:
        return text
    path = match.group("path").rstrip("/") or ""
    params = [p for p in (match.group("query") or "").split("&")
              if p and not _TRACKING_PARAMS.match(p.split("=", 1)[0])]
    query = "?" + "&".join(sorted(params)) if params else ""
    return f"{match.group('scheme').lower()}://{match.group('host').lower()}{path}{query}"


def dedupe_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """依定位符正規形合併重複列：保留先到者（其編號 `id` 不變），`ref_count` 記合計；路徑不同者
    仍獨立。輸入列取 `url` 與（選）`doi`。"""
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = normalize_locator(row.get("url"), row.get("doi"))
        if key in merged:
            merged[key]["ref_count"] += 1
        else:
            merged[key] = {**row, "ref_count": 1}
    return list(merged.values())
