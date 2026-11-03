"""由資料列確定性渲染的檔案：`issue_scope.json`、`evidence_matrix.md`、`review_card.json`，
以及 `state.json` 投影（ADR-003 D3）。

三類檔案流向（ADR-003 D3）：agent／人作者的檔案＝檔→驗→DB；**Bridge 作者的檔案＝DB→渲染→檔**
（本模組：`issue_scope.json`、`evidence_matrix.md`、`review_card.json`）；`state.json`＝**匯出、不得
被讀回**——它只被寫出，決定游標或轉移的任何函式都不讀它（機械鎖：`tests/test_research_reconcile.py`
掃描讀取形態，白名單只有對帳與診斷顯示）。

本模組只做純函式（輸入列、輸出文字或字典）；寫檔由 `layout.write_workspace_file` 負責。
`issue_scope.json` 的契約 SSOT 是框架模板 `ISSUE-SCOPE-TEMPLATE.md` 的契約區塊，欄位與驗證
規則逐條對映（模板 §1.1、§1.2）；證據矩陣版式取自 `EVIDENCE-MATRIX-TEMPLATE.md` §4，彙整卡取自
`ADVERSARIAL-REVIEW-CARD-TEMPLATE.md` §7。
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from .gates.aggregate import CONDITION_KEYS
from .gates.evidence import CELL_MAX_CHARS, is_license_unknown, license_pending_numbers
from .gates.schemas import AXIS_BY_LABEL, MISSING_TEXT, REVIEW_PARAMS, SCHEMA_REV

ISSUE_SCOPE_SCHEMA_REV = 1
STATE_SCHEMA_REV = 1

DEPTH_LEVELS: tuple[str, ...] = ("QUICK", "STANDARD", "DEEP")
TARGET_SCOPES: tuple[str, ...] = ("AISDLC_MODULE", "STANDALONE_PROJECT", "UNDECIDED")
LAYER_KEYS: tuple[str, ...] = ("academic", "industry", "oss", "community")
RECENCY_YEARS: tuple[int, ...] = (1, 2, 3)
#: 適用性軸登錄表的中文標籤（模板 EVIDENCE-MATRIX 的 `axis_registry`；順序即預設的全六軸順序）。
AXIS_LABELS: tuple[str, ...] = ("技術可行", "授權相容", "維護風險", "效能邊界", "資安", "成本")
TOPIC_MAX_CHARS = 500
TITLE_MAX_CHARS = 200
_LIST_MAX_ITEMS = 20
_ITEM_MAX_CHARS = 200
_TECH_STACK_MAX_CHARS = 200
_AXIS_MAX_ITEMS = 6
#: `scope`（資料庫 `research_projects.scope` 的形狀）允許的鍵：發起請求的 `scope` 與它逐鍵相同。
SCOPE_KEYS: frozenset[str] = frozenset({
    "layers", "tech_stack", "in_scope", "out_of_scope", "recency_years", "applicability_axes",
    "target_scope_hint"})


def _violation(field: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field, "rule": rule, "message": message}


def _string_list(value: Any, field: str, *, minimum: int, maximum: int,
                 out: list[dict[str, str]]) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        out.append(_violation(field, "invalid_type", f"{field} 須為字串陣列"))
        return []
    if not minimum <= len(value) <= maximum:
        out.append(_violation(field, "invalid_length", f"{field} 須有 {minimum}～{maximum} 項"))
    for index, item in enumerate(value):
        if not item.strip() or len(item) > _ITEM_MAX_CHARS or "\x00" in item:
            out.append(_violation(f"{field}[{index}]", "invalid_item",
                                  f"每項須為 1～{_ITEM_MAX_CHARS} 字、非空白、無 NUL"))
    return list(value)


def normalize_scope(raw: Any) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """驗證並補預設值，回傳 `(正規化的 scope, 違規清單)`（違規非空時 scope 不可用）。

    規則取模板 §1.2：`layers` 四個布林齊備且至少一個為真；`in_scope` 1～20 項；
    `out_of_scope` 0～20 項（預設空）；`tech_stack` 字串 ≤200 字（預設空字串，自由文字、
    不入任何指令）；`target_scope_hint` 取三個列舉值（預設 `UNDECIDED`）；`recency_years`
    取 1、2、3（預設 3）；`applicability_axes` 1～6 項、取自軸登錄表的中文標籤、不重複
    （預設全六軸）；不收未知鍵（模板：無多餘欄位）。"""
    out: list[dict[str, str]] = []
    if not isinstance(raw, Mapping):
        return {}, [_violation("scope", "invalid_type", "scope 須為物件")]
    for key in sorted(set(raw) - SCOPE_KEYS):
        out.append(_violation(f"scope.{key}", "unknown_key", f"不收 scope 的鍵 {key}"))
    layers_raw = raw.get("layers")
    layers: dict[str, bool] = {}
    if not isinstance(layers_raw, Mapping):
        out.append(_violation("scope.layers", "required", "layers 須為含四個布林的物件"))
    else:
        for key in sorted(set(layers_raw) - set(LAYER_KEYS)):
            out.append(_violation(f"scope.layers.{key}", "unknown_key", f"不收 layers 的鍵 {key}"))
        for key in LAYER_KEYS:
            value = layers_raw.get(key)
            if not isinstance(value, bool):
                out.append(_violation(f"scope.layers.{key}", "invalid_type", f"{key} 須為布林"))
            else:
                layers[key] = value
        if len(layers) == len(LAYER_KEYS) and not any(layers.values()):
            out.append(_violation("scope.layers", "at_least_one", "四個層開關至少一個為真"))
    if "in_scope" not in raw:
        out.append(_violation("scope.in_scope", "required", "in_scope 必填（至少一項）"))
        in_scope: list[str] = []
    else:
        in_scope = _string_list(raw["in_scope"], "scope.in_scope", minimum=1,
                                maximum=_LIST_MAX_ITEMS, out=out)
    out_of_scope = _string_list(raw.get("out_of_scope", []), "scope.out_of_scope", minimum=0,
                                maximum=_LIST_MAX_ITEMS, out=out)
    tech_stack = raw.get("tech_stack", "")
    if not isinstance(tech_stack, str) or len(tech_stack) > _TECH_STACK_MAX_CHARS \
            or "\x00" in tech_stack:
        out.append(_violation("scope.tech_stack", "invalid_value",
                              f"tech_stack 須為 ≤{_TECH_STACK_MAX_CHARS} 字的字串（可為空）"))
        tech_stack = ""
    hint = raw.get("target_scope_hint", "UNDECIDED")
    if hint not in TARGET_SCOPES:
        out.append(_violation("scope.target_scope_hint", "invalid_value",
                              f"target_scope_hint 須為 {'｜'.join(TARGET_SCOPES)}"))
    recency = raw.get("recency_years", 3)
    if isinstance(recency, bool) or recency not in RECENCY_YEARS:
        out.append(_violation("scope.recency_years", "invalid_value",
                              "recency_years 須為 1、2 或 3"))
    axes_raw = raw.get("applicability_axes", list(AXIS_LABELS))
    axes = _string_list(axes_raw, "scope.applicability_axes", minimum=1, maximum=_AXIS_MAX_ITEMS,
                        out=out)
    bad_axes = [a for a in axes if a not in AXIS_LABELS]
    if bad_axes:
        out.append(_violation("scope.applicability_axes", "unknown_axis",
                              f"軸標籤須取自登錄表 {list(AXIS_LABELS)}，不合：{bad_axes}"))
    if len(set(axes)) != len(axes):
        out.append(_violation("scope.applicability_axes", "duplicate", "軸標籤不得重複"))
    scope = {
        "layers": {key: layers.get(key, False) for key in LAYER_KEYS},
        "tech_stack": tech_stack,
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
        "recency_years": recency,
        "applicability_axes": axes,
        "target_scope_hint": hint,
    }
    return scope, out


def field_violations(*, title: Any, topic: Any, depth_level: Any) -> list[dict[str, str]]:
    """建立請求的非 scope 欄位：`title` 1～200 字、`topic` 1～500 字且無 NUL、
    `depth_level` 取列舉值。"""
    out: list[dict[str, str]] = []
    if not isinstance(title, str) or not title.strip() or len(title) > TITLE_MAX_CHARS:
        out.append(_violation("title", "invalid_length", f"title 須為 1～{TITLE_MAX_CHARS} 字"))
    if (not isinstance(topic, str) or not topic.strip() or len(topic) > TOPIC_MAX_CHARS
            or "\x00" in topic):
        out.append(_violation("topic", "invalid_length",
                              f"topic 須為 1～{TOPIC_MAX_CHARS} 字且不含 NUL"))
    if depth_level not in DEPTH_LEVELS:
        out.append(_violation("depth_level", "invalid_value",
                              f"depth_level 須為 {'｜'.join(DEPTH_LEVELS)}"))
    return out


def utc_iso(value: datetime | str) -> str:
    """帶時區的時間 → UTC 的 ISO-8601（秒精度，`+00:00`）。naive 時間一律拒絕（模板規定
    必須帶 offset）。統一成 UTC 與秒精度，使「由資料列重新渲染」與「建立當下渲染」的
    位元組相同，不受資料庫連線時區影響。"""
    moment = datetime.fromisoformat(value) if isinstance(value, str) else value
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"時間必須帶時區 offset：{value!r}")
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def render_issue_scope(project: Mapping[str, Any]) -> str:
    """`issue_scope.json` 的確定性渲染：鍵序固定（模板契約區塊的順序）、`ensure_ascii` 為假、
    縮排 2、LF 結尾；同一份列兩次輸出位元組相同。`project` 取資料列的欄位（`scope` 為
    正規化後的形狀）。"""
    scope = project["scope"]
    doc: dict[str, Any] = {
        "schema_rev": ISSUE_SCOPE_SCHEMA_REV,
        "research_id": str(project["research_id"]),
        "rp_no": project["rp_no"],
        "slug": project["slug"],
        "scope_rev": int(project["scope_rev"]),
        "title": project["title"],
        "topic": project["topic"],
        "scope": {
            "in_scope": list(scope["in_scope"]),
            "out_of_scope": list(scope["out_of_scope"]),
            "tech_stack": scope["tech_stack"],
            "target_scope_hint": scope["target_scope_hint"],
        },
        "depth_level": project["depth_level"],
        "layers": {key: bool(scope["layers"][key]) for key in LAYER_KEYS},
        "recency_years": scope["recency_years"],
        "applicability_axes": list(scope["applicability_axes"]),
        "created_by": project["created_by"],
        "created_at": utc_iso(project["created_at"]),
    }
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def build_state_projection(*, research_id: Any, flow: Mapping[str, Any], fsm: Mapping[str, Any],
                           runs: list[Mapping[str, Any]], projected_at: datetime) -> dict[str, Any]:
    """`02_governance/state.json` 的內容（匯出）：`research_id`、`flow`（step、phase、
    status）、`fsm`（project、state、updated_at、frozen_stages）、`runs`、`projected_at`
    （UTC）。純函式：呼叫端自己取得游標、外環 FSM 現況與 stage run 清單；本檔寫出後
    **不被任何程式讀回**。"""
    return {
        "schema_rev": STATE_SCHEMA_REV,
        "research_id": str(research_id),
        "flow": {"step": flow["step"], "phase": flow["phase"], "status": flow["status"]},
        "fsm": {
            "project": fsm.get("project"),
            "state": fsm.get("state"),
            "updated_at": fsm.get("updated_at"),
            "frozen_stages": list(fsm.get("frozen_stages") or []),
        },
        "runs": [dict(run) for run in runs],
        "projected_at": utc_iso(projected_at),
    }


def render_state_json(projection: Mapping[str, Any]) -> str:
    return json.dumps(projection, ensure_ascii=False, indent=2, default=str) + "\n"


# ══ evidence_matrix.md（模板 EVIDENCE-MATRIX §4；DB→渲染→檔）═══════════════════════════════════
MATRIX_SCHEMA_REV = 1
LAYER_LOWER = {"ACADEMIC": "academic", "INDUSTRY": "industry", "OSS": "oss",
               "COMMUNITY": "community"}
SOURCE_HEADERS: tuple[str, ...] = (
    "S-NNN", "標題", "作者機構", "年份", "URL 或 DOI", "類型", "查證層級", "授權條款", "層",
    "來源分級", "被引證據")
ITEM_HEADERS: tuple[str, ...] = (
    "ID", "層", "候選技術", "標題", "出處機構或作者", "年份", "定位符", "來源分級", "查證層級",
    "授權條款", "F1 機制", "F2 證據", "F3 失敗與批評", "F4 風險標籤", "F5 適用性", "F6 限制",
    "抓取紀錄")
COUNTER_HEADERS: tuple[str, ...] = ("證據", "反證搜尋", "結論", "反證來源", "說明")
CLUE_HEADERS: tuple[str, ...] = ("S-NNN", "標題", "URL", "層", "用途")
CLUE_PURPOSE = "只作搜尋線索，不得當證據"
HONEST_SENTENCES: tuple[str, ...] = (
    "WebFetch 是小模型依提問轉述，所有 V2 的數字與陳述都是轉述，PRD 引用前須核對原頁面。",
    "來源表以外的文獻一律視為「未納入」，不是「不存在」。",
    "搜尋引擎找得到的不等於全集，本矩陣不聲稱窮盡。")
UNANCHORED_MARK = " ⚠UNANCHORED"
NOTES_DIR = "00_research/notes"


@dataclass
class RenderedMatrix:
    """`evidence_matrix.md` 的文字，加上超長儲存格搬出的附註檔（相對工作區路徑 → 內容）。"""

    text: str
    notes: dict[str, str] = field(default_factory=dict)


def _cell(value: object) -> str:
    text = str(value)
    if "|" in text or "\n" in text or "\r" in text:
        raise ValueError(f"儲存格不得含管線字元或換行：{text[:40]!r}")
    return text


def _license_cell(spdx: str | None) -> str:
    return MISSING_TEXT if is_license_unknown(spdx) else str(spdx)


def _locator(src: Mapping[str, Any]) -> str:
    text = str(src["url"])
    if src.get("anchor_kind") == "DOI" and src.get("doi"):
        text += f"；doi:{src['doi']}"
    if src.get("anchor_kind") == "COMMIT" and src.get("git_commit"):
        text += f"；commit:{str(src['git_commit'])[:12]}"
    return text


def _year(src: Mapping[str, Any]) -> str:
    published = src.get("published_at")
    return str(published)[:4] if published else MISSING_TEXT


def _row(cells: Sequence[object]) -> str:
    return "| " + " | ".join(_cell(c) for c in cells) + " |"


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    return [_row(headers), "|" + "|".join("---" for _ in headers) + "|",
            *[_row(r) for r in rows]]


def _fetch_cell(refs: Sequence[str], fetch_info: Mapping[str, Mapping[str, Any]],
                unanchored: bool) -> str:
    parts = [f"{ref}@{str((fetch_info.get(ref) or {}).get('raw_sha256') or '')[:12]}"
             for ref in refs]
    text = "、".join(parts) if parts else "無（宣告型）"
    return text + (UNANCHORED_MARK if unanchored else "")


def _applicability_cell(f5: Mapping[str, Any], axes_labels: Sequence[str]) -> str:
    parts = []
    for label in axes_labels:
        cell = f5.get(AXIS_BY_LABEL[label]) or {}
        parts.append(f"{label}:{cell.get('grade', '?')}（{cell.get('reason', '')}）")
    return "；".join(parts)


def _cited_by(source_no: str, items: Sequence[Mapping[str, Any]],
              counters: Sequence[Mapping[str, Any]]) -> str:
    cited = [i["evidence_no"] for i in items if i["source_no"] == source_no]
    cited += [f"{c['evidence_no']}（反證）" for c in counters if c.get("source_no") == source_no]
    return "、".join(cited) if cited else MISSING_TEXT


def render_evidence_matrix(*, version: int, scope_rev: int, axes_labels: Sequence[str],
                           sources: Sequence[Mapping[str, Any]],
                           items: Sequence[Mapping[str, Any]],
                           counters: Sequence[Mapping[str, Any]], bounds: Mapping[str, Any],
                           fetch_info: Mapping[str, Mapping[str, Any]] | None = None
                           ) -> RenderedMatrix:
    """證據矩陣的確定性渲染（同樣輸入兩次輸出位元組相同）。

    `sources`／`items`／`counters`／`bounds` 是 `evidence_items.json` 的形態；`items` 每列另帶
    執行層算出的 `unanchored`（布林）；`fetch_info` 是 `F-NNNN` → `{raw_sha256}`。T3 來源不進
    A 來源表、改列 D 線索區；儲存格超過 600 字元者搬到 `00_research/notes/E-NNN.md`，格內留
    「見 notes/E-NNN.md」。"""
    info = fetch_info or {}
    by_no = {s["source_no"]: s for s in sources}
    lookup = {s["source_no"]: s for s in sources}
    pending = license_pending_numbers(items, lookup)
    unanchored = [i["evidence_no"] for i in items if i.get("unanchored")]
    notes: dict[str, str] = {}
    lines = [
        f"<!-- r2p:evidence_matrix schema_rev={MATRIX_SCHEMA_REV} version={version} -->",
        f"# 證據矩陣（version {version}；scope_rev {scope_rev}）", "",
        f"> 授權待查：{len(pending)} 筆（授權條款為 GPL／AGPL 系或「{MISSING_TEXT}」；"
        f"{'、'.join(pending) if pending else '無'}）",
        f"> UNANCHORED：{len(unanchored)} 筆", "",
        "## A 來源表", ""]
    lines += _table(SOURCE_HEADERS, [
        (s["source_no"], s["title"], s["authors_org"], _year(s), _locator(s), s["source_type"],
         s["verification"], _license_cell(s.get("license_spdx")), LAYER_LOWER[s["layer"]],
         s["tier"], _cited_by(s["source_no"], items, counters))
        for s in sources if s["tier"] != "T3"])
    lines += ["", "## B 證據表", ""]
    rows = []
    for item in items:
        src = by_no[item["source_no"]]
        cells = [
            item["evidence_no"], LAYER_LOWER[src["layer"]], item.get("candidate") or "—",
            src["title"], src["authors_org"], _year(src), _locator(src), src["tier"], item["f7"],
            _license_cell(src.get("license_spdx")), item["f1"], item["f2"], item["f3"],
            "、".join(item.get("f4") or []) or "無",
            _applicability_cell(item["f5"], axes_labels), item["f6"],
            _fetch_cell(src.get("fetch_refs") or [], info, bool(item.get("unanchored")))]
        for column, text in enumerate(cells):
            if len(str(text)) > CELL_MAX_CHARS:
                rel = f"{NOTES_DIR}/{item['evidence_no']}.md"
                notes[rel] = notes.get(rel, f"# {item['evidence_no']} 附註\n") + (
                    f"\n## {ITEM_HEADERS[column]}\n\n{text}\n")
                cells[column] = f"見 notes/{item['evidence_no']}.md"
        rows.append(cells)
    lines += _table(ITEM_HEADERS, rows)
    lines += ["", "## C 反證", ""]
    lines += _table(COUNTER_HEADERS, [
        (c["evidence_no"], c.get("search_id") or "—", c["conclusion"], c.get("source_no") or "—",
         c["note"]) for c in counters])
    lines += ["", "## D 線索區", ""]
    lines += _table(CLUE_HEADERS, [
        (s["source_no"], s["title"], s["url"], LAYER_LOWER[s["layer"]], CLUE_PURPOSE)
        for s in sources if s["tier"] == "T3"])
    lines += ["", "## E 誠實劃界", "", "### 沒查到", ""]
    lines += [f"- {nf['query']}（{nf['date']}）：{nf['result']}"
              for nf in bounds.get("not_found") or []] or ["- 無"]
    lines += ["", "### 只讀摘要或搜尋結果", ""]
    lines += [f"- {no}" for no in bounds.get("summary_only") or []] or ["- 無"]
    lines += ["", "### 沒讀全文", ""]
    lines += [f"- {no}" for no in bounds.get("not_read_fully") or []] or ["- 無"]
    lines += ["", *HONEST_SENTENCES, ""]
    return RenderedMatrix("\n".join(lines), notes)


# ══ review_card.json（模板 ADVERSARIAL-REVIEW-CARD §7；DB→渲染→檔）════════════════════════════
def _iso(value: Any) -> str | None:
    return None if value is None else utc_iso(value)


def _stem(path: str) -> str:
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    return name[:-5] if name.endswith(".yaml") else name


def card_reviewer(score: Mapping[str, Any]) -> dict[str, Any]:
    """`review_scores` 一列 → 卡上 `reviewers[]` 一筆（十一鍵、不含 model）。"""
    return {
        "dimension": score["dimension"], "weight": float(score["weight"]),
        "agent": _stem(score["agent_yaml_path"]), "agent_id": score["agent_id"],
        "agent_yaml_sha256": score["agent_yaml_sha256"],
        "assist_agent_id": score.get("assist_agent_id"),
        "assist_agent_yaml_sha256": score.get("assist_agent_yaml_sha256"),
        "persona_sha256": score["persona_sha256"], "score": int(score["score"]),
        "raw_file": score["raw_rel_path"], "raw_sha256": score["raw_sha256"]}


def card_defect(defect: Mapping[str, Any], semver_by_no: Mapping[int, str]) -> dict[str, Any]:
    """`review_defects` 一列 → 卡上 `defects[]` 一筆（`status` 為目前值；缺陷審查者描述對映
    `description`→`finding`、`prd_anchor`→`anchor`）。"""
    fixed_in = defect.get("fixed_in_version_no")
    waiver = None
    if defect.get("status") == "WAIVED":
        waiver = {"by": defect.get("waived_by"), "reason": defect.get("waiver_reason"),
                  "at": _iso(defect.get("resolved_at"))}
    return {
        "id": defect["defect_no"], "dimension": defect["dimension"],
        "severity": defect["severity"], "code": defect["code"], "anchor": defect["prd_anchor"],
        "finding": defect["description"], "suggestion": defect["suggestion"],
        "evidence_refs": list(defect.get("evidence_refs") or []), "status": defect["status"],
        "resolved_in": semver_by_no.get(int(fixed_in)) if fixed_in is not None else None,
        "waiver": waiver}


def card_round(row: Mapping[str, Any], scores: Sequence[Mapping[str, Any]],
               defects: Sequence[Mapping[str, Any]], *, semver_by_no: Mapping[int, str],
               sha_by_no: Mapping[int, str]) -> dict[str, Any]:
    """審查輪列（含四維分數列與缺陷列）→ 卡上 `rounds[]` 一筆。`precheck` 取輪列的
    `precheck_detail`；`conditions` 由輪列欄位逐項重算（與 DB 的通過旗標 CHECK 同一組條件）。"""
    version_no = int(row["prd_version_no"])
    weighted = row.get("weighted_score")
    minimum = row.get("min_dimension_score")
    detail = row.get("precheck_detail") or {}
    conditions = {
        "precheck_passed": bool(row["precheck_passed"]),
        "weighted_ge_threshold": weighted is not None and Decimal(weighted) >= Decimal(
            row.get("threshold", 85)),
        "all_dimensions_ge_floor": minimum is not None and int(minimum) >= int(
            row.get("floor_score", 60)),
        "no_open_p1": int(row.get("open_p1_count", 0)) == 0}
    assert tuple(conditions) == CONDITION_KEYS
    gate_result = row.get("fsm_gate_result")
    return {
        "round": int(row["round_no"]), "prd_version": semver_by_no.get(version_no),
        "prd_version_no": version_no, "prd_sha256": sha_by_no.get(version_no),
        "params": {"weights": dict(REVIEW_PARAMS["weights"]),
                   "threshold": REVIEW_PARAMS["threshold"],
                   "dimension_floor": REVIEW_PARAMS["dimension_floor"]},
        "precheck": {"passed": bool(detail.get("passed", row["precheck_passed"])),
                     "checks": list(detail.get("checks") or [])},
        "reviewers": [card_reviewer(s) for s in scores],
        "weighted_total": None if weighted is None else Decimal(weighted),
        "min_dimension_score": None if minimum is None else int(minimum),
        "conditions": conditions, "open_p1_count": int(row.get("open_p1_count", 0)),
        "passed": bool(row["passed"]), "verdict": row["verdict"],
        "defects": [card_defect(d, semver_by_no) for d in defects],
        "fsm": {"gate_result": gate_result,
                "retry_count": row.get("fsm_retry_count") if gate_result else None},
        "started_at": _iso(row["started_at"]), "ended_at": _iso(row["finished_at"])}


def build_review_card(research_id: Any, rounds: Sequence[Mapping[str, Any]], *,
                      retry_count: int | None, final_verdict: str) -> dict[str, Any]:
    """彙整卡本體：`retry_count` 取自 FSM `show`／`gate` 的回傳（不自建第二套計數）。"""
    return {"schema_rev": SCHEMA_REV, "research_id": str(research_id),
            "rounds": [dict(r) for r in rounds], "retry_count": retry_count,
            "final_verdict": final_verdict}


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return utc_iso(value)
    return str(value)


def render_review_card(card: Mapping[str, Any]) -> str:
    """`review_card.json` 的確定性渲染（鍵序依建構順序、`ensure_ascii` 為假、縮排 2、LF 結尾）。"""
    return json.dumps(card, ensure_ascii=False, indent=2, default=_json_default) + "\n"
