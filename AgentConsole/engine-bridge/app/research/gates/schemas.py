"""契約常數、登錄表與 `issue_scope.json` 的驗證（框架模板是 SSOT；D-43）。

本檔的常數是框架三份模板契約區塊（`<!-- r2p:contract=… -->`）的**逐值鏡像**：軸登錄表、風險標籤
登錄表、
審查參數、rubric 登錄表。Bridge 不在執行期讀框架模板（框架樹可能唯讀、版本會演進），所以對拍由
`tests/test_research_schema_parity.py` 承擔：模板一改、對拍就紅，不靠人記得同步。

違規一律回 `Violation(rule, path, message)`：`rule` 是機器可讀的規則編號（證據 `R1`～`R16`、預檢
`P0-1`～`P0-9`、審查 `V1`…），`path` 是 JSON 路徑或行號——`gate_cli` 把它們逐行印到 stderr。
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

SCHEMA_REV = 1
DIMENSIONS: tuple[str, ...] = ("ARCHITECTURE", "PRODUCT", "QA", "SECURITY")
LAYERS: tuple[str, ...] = ("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY")
MISSING_TEXT = "未見"          # 缺資訊的固定字樣（模板 §2.3 規則 8、§4.3）

#: 適用性軸登錄表（模板 EVIDENCE-MATRIX §3.1；`f5` 的鍵 → 中文標籤）。
AXIS_REGISTRY: Mapping[str, str] = MappingProxyType({
    "technical": "技術可行", "license": "授權相容", "maintenance": "維護風險",
    "performance": "效能邊界", "security": "資安", "cost": "成本"})
AXIS_BY_LABEL: Mapping[str, str] = MappingProxyType({v: k for k, v in AXIS_REGISTRY.items()})
#: 風險標籤登錄表（模板 §3.2；`f4` 只准取這些鍵，`UNANCHORED` 不是其中之一）。
RISK_TAG_REGISTRY: Mapping[str, str] = MappingProxyType({
    "LOCK": "供應商或生態鎖定", "IMM": "不成熟（預印本、單一作者、無 venue、進行中）",
    "SELF": "自述成果、未見獨立重現", "SCOPE": "外推風險（單一基準、小模型、構造資料）",
    "DEP": "相依與維護風險（維護者少、停更、重大 issue 長期未決）",
    "LIC": "授權風險（強 copyleft、授權未見、限制商用）", "SEC": "安全風險（已知漏洞、供應鏈）",
    "COMP": "合規或資料保護風險"})

#: 審查參數（模板 ADVERSARIAL-REVIEW-CARD §2.1；產品常數、不提供 UI 修改）。
REVIEW_WEIGHTS: Mapping[str, float] = MappingProxyType({
    "ARCHITECTURE": 0.30, "PRODUCT": 0.25, "QA": 0.25, "SECURITY": 0.20})
#: 整數權重（W100＝30A＋25P＋25Q＋20S）；與 `REVIEW_WEIGHTS` 同源（逐值相乘 100）。
W100_WEIGHTS: Mapping[str, int] = MappingProxyType({
    "ARCHITECTURE": 30, "PRODUCT": 25, "QA": 25, "SECURITY": 20})
REVIEW_THRESHOLD = 85
DIMENSION_FLOOR = 60
#: 每輪參數快照（`review_card.json` 的 `params`；也是本模組對外的唯一形狀）。
REVIEW_PARAMS: Mapping[str, Any] = MappingProxyType({
    "weights": dict(REVIEW_WEIGHTS), "threshold": REVIEW_THRESHOLD,
    "dimension_floor": DIMENSION_FLOOR})
#: 審查預算＝FSM `SCG_VALIDATION` 的重試上限（第 3 次 FAIL＝ESCALATION；ADR-XPLAT-017 D6）。
SCG_RETRY_LIMIT = 3

#: rubric 登錄表（模板 §4.3）：維度 → 審查者與評分項目。
RUBRIC_REGISTRY: Mapping[str, Mapping[str, Any]] = MappingProxyType({
    "ARCHITECTURE": MappingProxyType({
        "agent_id": "sd-architect", "agent_file": "agent/core/05.sd-architect-zh.yaml",
        "assist_agent_id": None, "assist_agent_file": None, "weight": 0.30,
        "defect_prefix": "ARCH",
        "items": ("coupling", "dependency_risk", "performance_bounds", "data_interface",
                  "evidence_fit")}),
    "PRODUCT": MappingProxyType({
        "agent_id": "pm-po", "agent_file": "agent/core/03.pm-po-agent-zh.yaml",
        "assist_agent_id": None, "assist_agent_file": None, "weight": 0.25,
        "defect_prefix": "PROD",
        "items": ("business_value", "metric_measurability", "scope_discipline", "prioritization",
                  "evidence_grounding")}),
    "QA": MappingProxyType({
        "agent_id": "qa-tester", "agent_file": "agent/core/07.qa-tester-zh.yaml",
        "assist_agent_id": None, "assist_agent_file": None, "weight": 0.25,
        "defect_prefix": "QA",
        "items": ("us_ambiguity", "gwt_automatable", "edge_case_coverage", "traceability",
                  "nfr_testability")}),
    "SECURITY": MappingProxyType({
        "agent_id": "security-engineer",
        "agent_file": "agent/specialized/security-engineer-zh.yaml",
        "assist_agent_id": "compliance-officer",
        "assist_agent_file": "agent/specialized/compliance-officer-zh.yaml", "weight": 0.20,
        "defect_prefix": "SEC",
        "items": ("license_conflict", "secret_handling", "injection_risk", "authn_authz",
                  "external_content_safety")})})
RUBRIC_ITEM_MAX = 20

# ── 議題檔（模板 ISSUE-SCOPE §1）─────────────────────────────────────────────────────────────
DEPTH_LEVELS: tuple[str, ...] = ("QUICK", "STANDARD", "DEEP")
TARGET_SCOPES: tuple[str, ...] = ("AISDLC_MODULE", "STANDALONE_PROJECT", "UNDECIDED")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,29}$")
_RP_NO_RE = re.compile(r"^RP-(\d{4,}|LOCAL)$")
_ISSUE_TOP_KEYS = frozenset({
    "schema_rev", "research_id", "rp_no", "slug", "scope_rev", "title", "topic", "scope",
    "depth_level", "layers", "recency_years", "applicability_axes", "created_by", "created_at"})
_ISSUE_SCOPE_KEYS = frozenset({"in_scope", "out_of_scope", "tech_stack", "target_scope_hint"})
_LAYER_FLAGS: tuple[str, ...] = ("academic", "industry", "oss", "community")


@dataclass(frozen=True)
class Violation:
    """一條違規：`rule` 是規則編號、`path` 是 JSON 路徑（或預檢的行號）、`message` 是人讀說明。"""

    rule: str
    path: str
    message: str

    def format(self) -> str:
        return f"[{self.rule}] {self.path}: {self.message}"


def violation_lines(violations: Sequence[Violation]) -> list[str]:
    return [v.format() for v in violations]


def is_int(value: Any) -> bool:
    """JSON 整數（排除 bool——Python 的 `True` 是 int 的子類）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def has_line_break(text: str) -> bool:
    return "\n" in text or "\r" in text


def parse_offset_datetime(value: Any) -> datetime | None:
    """ISO-8601 且必須帶時區 offset；不合回 None（naive 時間字串不合法）。"""
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None and moment.utcoffset() is not None else None


def axis_ids(labels: Sequence[str]) -> list[str]:
    """議題的 `applicability_axes`（中文標籤）→ `f5` 的鍵（軸 id）。

    不認得的標籤略過（由議題驗證擋）。"""
    return [AXIS_BY_LABEL[label] for label in labels if label in AXIS_BY_LABEL]


def validate_issue_scope(doc: Any) -> list[Violation]:
    """議題檔的確定性驗證（模板 §1.2）：必填、型別、列舉、無多餘欄位、層開關至少一個為真、軸取自
    登錄表、
    `created_at` 帶 offset。"""
    out: list[Violation] = []

    def bad(path: str, rule: str, message: str) -> None:
        out.append(Violation(rule, path, message))

    if not isinstance(doc, Mapping):
        return [Violation("S1", "$", "議題檔須為 JSON 物件")]
    for key in sorted(set(doc) - _ISSUE_TOP_KEYS):
        bad(key, "S1", f"多餘的頂層欄位 {key}")
    for key in sorted(_ISSUE_TOP_KEYS - set(doc)):
        bad(key, "S1", f"缺必填欄位 {key}")
    if doc.get("schema_rev") != SCHEMA_REV or not is_int(doc.get("schema_rev")):
        bad("schema_rev", "S1", f"schema_rev 須為 {SCHEMA_REV}")
    if not isinstance(doc.get("research_id"), str) or not doc.get("research_id"):
        bad("research_id", "S1", "research_id 須為非空字串")
    if not isinstance(doc.get("slug"), str) or not _SLUG_RE.fullmatch(doc["slug"]):
        bad("slug", "S2", "slug 須符合 ^[a-z0-9][a-z0-9-]{0,29}$")
    if not isinstance(doc.get("rp_no"), str) or not _RP_NO_RE.fullmatch(doc["rp_no"]):
        bad("rp_no", "S2", "rp_no 須為 RP-NNNN（至少 4 位數字）或 RP-LOCAL")
    if not is_int(doc.get("scope_rev")) or doc["scope_rev"] < 1:
        bad("scope_rev", "S1", "scope_rev 須為 ≥1 的整數")
    title = doc.get("title")
    if not isinstance(title, str) or not 1 <= len(title) <= 200:
        bad("title", "S2", "title 須為 1～200 字")
    topic = doc.get("topic")
    if not isinstance(topic, str) or not 1 <= len(topic) <= 500:
        bad("topic", "S5", "topic 須為 1～500 字")
    _check_scope_block(doc.get("scope"), bad)
    if doc.get("depth_level") not in DEPTH_LEVELS:
        bad("depth_level", "S3", f"depth_level 須為 {'｜'.join(DEPTH_LEVELS)}")
    _check_layers(doc.get("layers"), bad)
    if not is_int(doc.get("recency_years")) or doc["recency_years"] not in (1, 2, 3):
        bad("recency_years", "S3", "recency_years 須為 1、2 或 3")
    _check_axes(doc.get("applicability_axes"), bad)
    if not isinstance(doc.get("created_by"), str) or not doc.get("created_by"):
        bad("created_by", "S1", "created_by 須為非空字串")
    if parse_offset_datetime(doc.get("created_at")) is None:
        bad("created_at", "S5", "created_at 須為帶時區 offset 的 ISO-8601")
    return out


def _check_scope_block(scope: Any, bad: Any) -> None:
    if not isinstance(scope, Mapping):
        bad("scope", "S1", "scope 須為物件")
        return
    for key in sorted(set(scope) - _ISSUE_SCOPE_KEYS):
        bad(f"scope.{key}", "S1", f"多餘的欄位 scope.{key}")
    for key in sorted(_ISSUE_SCOPE_KEYS - set(scope)):
        bad(f"scope.{key}", "S1", f"缺必填欄位 scope.{key}")
    in_scope = scope.get("in_scope")
    if not isinstance(in_scope, list) or not in_scope or any(
            not isinstance(i, str) for i in in_scope):
        bad("scope.in_scope", "S5", "in_scope 須為至少一項的字串陣列")
    out_of_scope = scope.get("out_of_scope")
    if not isinstance(out_of_scope, list) or any(not isinstance(i, str) for i in out_of_scope):
        bad("scope.out_of_scope", "S1", "out_of_scope 須為字串陣列（可為空）")
    tech = scope.get("tech_stack")
    if not isinstance(tech, str) or len(tech) > 200:
        bad("scope.tech_stack", "S3", "tech_stack 須為 ≤200 字的字串（可為空）")
    if scope.get("target_scope_hint") not in TARGET_SCOPES:
        bad("scope.target_scope_hint", "S3", f"須為 {'｜'.join(TARGET_SCOPES)}")


def _check_layers(layers: Any, bad: Any) -> None:
    if not isinstance(layers, Mapping):
        bad("layers", "S1", "layers 須為含四個布林的物件")
        return
    for key in sorted(set(layers) - set(_LAYER_FLAGS)):
        bad(f"layers.{key}", "S1", f"多餘的欄位 layers.{key}")
    flags = []
    for key in _LAYER_FLAGS:
        if not isinstance(layers.get(key), bool):
            bad(f"layers.{key}", "S1", f"layers.{key} 須為布林")
        else:
            flags.append(layers[key])
    if len(flags) == len(_LAYER_FLAGS) and not any(flags):
        bad("layers", "S3", "四個層開關至少一個為 true")


def _check_axes(axes: Any, bad: Any) -> None:
    if not isinstance(axes, list) or not 1 <= len(axes) <= 6:
        bad("applicability_axes", "S4", "applicability_axes 須為 1～6 項")
        return
    unknown = [a for a in axes if a not in AXIS_BY_LABEL]
    if unknown:
        bad("applicability_axes", "S4", f"軸標籤須取自登錄表，不合：{unknown}")
    if len(set(map(str, axes))) != len(axes):
        bad("applicability_axes", "S4", "軸標籤不得重複")
