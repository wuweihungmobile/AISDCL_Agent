"""由資料列確定性渲染的檔案：`issue_scope.json`，以及 `state.json` 投影（ADR-003 D3）。

三類檔案流向（ADR-003 D3）：agent／人作者的檔案＝檔→驗→DB；**Bridge 作者的檔案＝DB→渲染→檔**
（本模組：`issue_scope.json`）；`state.json`＝**匯出、不得被讀回**——它只被寫出，決定游標或轉移的任何
函式都不讀它（機械鎖：`tests/test_research_reconcile.py` 掃描讀取形態，白名單只有對帳與診斷顯示）。

本模組只做純函式（輸入列、輸出文字或字典）；寫檔由 `layout.write_workspace_file` 負責。
`issue_scope.json` 的契約 SSOT 是框架模板 `ISSUE-SCOPE-TEMPLATE.md` 的契約區塊，欄位與驗證
規則逐條對映（模板 §1.1、§1.2）。
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

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
