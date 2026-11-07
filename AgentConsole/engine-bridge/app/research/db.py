"""ResearchDb：研究表（`console.research_*`）的 fail-loud 寫入器與唯讀查詢（ADR-003 D2、D4、D5）。

與既有 `app/db.py` 的 `BridgeDb`（best-effort：DB 掛了只記 log、回 False）相反：這裡的連線與
執行錯誤一律拋 `ResearchDbError`，沒有降級、沒有靜默回傳；本模組的每個 `except` 都轉拋（AST 鎖在
tests/test_research_db.py），也不 import `BridgeDb`。

結構：
  · `ResearchDb.transaction()` 開一個交易（`ResearchTx`）；交易內每條 SQL 都是寫死的字面字串
    （UPDATE 的 SET 欄位寫在字面裡），所以能被靜態掃描、對照 `CONTROLLED_UPDATE_COLUMNS`。
  · 一個「操作」＝一個 DB 交易＝資料列＋`research_events`（單調 `seq`）＋`last_event_seq`，登記在
    `OPS`；操作對崩潰冪等（自然鍵 UNIQUE 或狀態等值：已套用就跳過、也不重複發事件），由 outbox.py 的
    `DurableWriter` 依「檔→outbox→DB 交易→完成標記」驅動；`ResearchDb` 的公開寫入方法
    （`WRITE_METHODS`）是同一組操作的直接呼叫。
  · 寫入器層守衛（D-49.3、D-56 的應用層保證）：`round_no` 連續、EVIDENCE_ITEMS 的 `content` 必填、
    來源查證層級只升不降、缺陷狀態單向、T3 只當線索、Reddit 須先確認條款。
  · 唯讀查詢一律在唯讀交易內跑（`query` 只收 SELECT）。

事件 payload 的鍵一律照 API 契約 §3（camelCase）；DB 不存任何機密。
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

# ── 值域與常數（測試與產品碼共用，TCS §5.1）─────────────────────────────────────────────────
#: 受控可更新欄位表：全部 `UPDATE` 的 SET 欄位必須是對應表此集合的子集（V16～V18 的通用守衛同義）。
CONTROLLED_UPDATE_COLUMNS: dict[str, frozenset[str]] = {
    "research_projects": frozenset({
        "title", "topic", "scope", "scope_rev", "depth_level", "target_scope", "fsm_project",
        "fsm_generation", "flow_step", "flow_phase", "flow_status", "flow_detail",
        "console_project_id", "last_event_seq", "updated_at", "archived_at"}),
    "research_stage_runs": frozenset({
        "status", "tokens_used", "exit_reason", "started_at", "finished_at"}),
    "research_review_defects": frozenset({
        "status", "fixed_in_version_no", "waived_by", "waiver_reason", "resolved_at"}),
    "research_sources": frozenset({"verification"}),
    "research_allowlist_entries": frozenset({"enabled", "disabled_by", "disabled_at"}),
    # P1（V19；與 V16 通用守衛函式的允許清單同義，`test_research_db` 對真庫逐表比對）
    "research_route_decisions": frozenset({
        "status", "failure_step", "finished_at", "repo_url", "published_docs",
        "console_project_id", "impl_fsm_project", "impl_state_dir"}),
    "research_route_steps": frozenset({
        "status", "exit_code", "stdout_tail", "stderr_tail", "finished_at"}),
    # P1 BR-D2（V16 通用守衛函式的允許清單；`test_research_db` 對真庫逐表比對）
    "research_scr": frozenset({
        "status", "prd_to_version_no", "successor_research_id", "impl_fsm_actions", "decided_by",
        "decided_at"}),
    "research_decompositions": frozenset({
        "status", "draft_id", "import_record_id", "tcs_rel_path", "tcs_sha256", "tasks_count",
        "gate_rejection"}),
}
#: append-only：寫入器對這些表沒有任何 UPDATE 或 DELETE（DB 另有守衛作第二道）。
APPEND_ONLY_TABLES = frozenset({
    "research_events", "research_artifacts", "research_fetches", "research_evidence_items",
    "research_prd_versions", "research_review_rounds", "research_review_scores",
    "research_gate_decisions"})
#: 各事件型別的 payload 鍵集合（API 契約 §3；寫入器逐筆驗證，不符＝`event_payload` 守衛拒絕）。
EVENT_PAYLOAD_KEYS: dict[str, frozenset[str]] = {
    "research.step": frozenset({"flowStep", "flowPhase", "flowStatus", "flowDetail"}),
    "research.run": frozenset({"stage", "roundNo", "attempt", "stageRunId", "engineRunId",
                               "status", "tokensUsed"}),
    "research.source": frozenset({"sourceNo", "layer", "tier", "verification", "title", "url",
                                  "fetchOutcome"}),
    "research.evidence": frozenset({"matrixVersion", "evidenceNo", "sourceNo", "claim",
                                    "strength"}),
    "research.prd": frozenset({"versionNo", "semver", "authorKind", "author", "sha256"}),
    "research.review": frozenset({"roundNo", "weightedScore", "minDimensionScore", "passed",
                                  "verdict", "escalated"}),
    "research.review_invalid": frozenset({"stageRunId", "roundNo", "attempt", "reason"}),
    "research.defect": frozenset({"defectNo", "severity", "dimension", "status"}),
    "research.gate": frozenset({"gate", "decision", "decidedBy", "fsmStage", "frozenDigests"}),
    "research.reconcile": frozenset({"consistent", "driftCount"}),
    "research.alert": frozenset({"kind", "detail"}),
    # P1：分流每步與路由終態各一筆（契約 §3；stepNo 0＝路由列本身）
    "research.route": frozenset({"routeId", "stepNo", "step", "status"}),
    # P1 BR-D2：SCR 狀態轉移各一筆（契約 §3；OPEN／APPROVED／APPLIED／REJECTED／SUPERSEDED）
    "research.scr": frozenset({"scrNo", "kind", "status"}),
}
#: 各事件型別在必填鍵之外**可選**的鍵（`research.route` 的補償事件帶 `reason`，D-112）。
EVENT_OPTIONAL_KEYS: dict[str, frozenset[str]] = {
    "research.route": frozenset({"reason"}),
    "research.step": frozenset({"reason"}),    # D-125：`tcs_frozen_correction` 校正事件
}
#: P0 事件型別（Bridge 事件帳）；`research.replay_gap` 是傳輸層訊號、不在其中（API 契約 §3）。
EVENT_TYPES = frozenset(EVENT_PAYLOAD_KEYS)
VERIFICATION_ORDER = {"V1": 1, "V2": 2, "V3": 3}
DEFECT_TRANSITIONS: dict[str, frozenset[str]] = {
    "OPEN": frozenset({"FIXED", "WAIVED", "SUPERSEDED"}),
    "FIXED": frozenset({"REGRESSED"}),
    "REGRESSED": frozenset({"FIXED"}),
    "WAIVED": frozenset(),
    "SUPERSEDED": frozenset(),
}
DEFAULT_THRESHOLD = Decimal("85.00")
DEFAULT_FLOOR_SCORE = 60
INITIAL_FLOW = {"step": "topic", "phase": "INGESTED", "status": "IDLE", "detail": ""}
#: 產品常數：審查權重（維度鍵大寫；PRD §5.1.4）。
REVIEW_WEIGHTS: dict[str, Decimal] = {
    "ARCHITECTURE": Decimal("0.300"), "PRODUCT": Decimal("0.250"), "QA": Decimal("0.250"),
    "SECURITY": Decimal("0.200")}
_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
_REDDIT_RE = re.compile(r"(^|\.)(reddit\.com|redd\.it)$")
_EVIDENCE_REF_RE = re.compile(r"\[(E-\d{3,4})\]")


# ── 錯誤 ───────────────────────────────────────────────────────────────────────────────────
class ResearchDbError(Exception):
    """DB 連線或執行失敗（fail-loud 的唯一出口）。`kind`＝`connect`｜`execute`。"""

    def __init__(self, kind: str, message: str, *, sqlstate: str | None = None) -> None:
        super().__init__(f"{kind}: {message}")
        self.kind = kind
        self.sqlstate = sqlstate


class ResearchConflict(Exception):
    """應用層衝突（呼叫端對映 HTTP 409）：`reason` 與 `details`。不是 DB 故障。"""

    def __init__(self, reason: str, **details: Any) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = details


class ResearchGuardError(Exception):
    """寫入器層守衛拒絕（D-49.3、D-56）：`rule` 是機器可讀碼。呼叫端依 rule 對映 404／422。"""

    def __init__(self, rule: str, message: str = "", **details: Any) -> None:
        super().__init__(f"{rule}: {message}" if message else rule)
        self.rule = rule
        self.details = details


# ── 小工具 ─────────────────────────────────────────────────────────────────────────────────
def utc_now() -> datetime:
    return datetime.now(UTC)


def _dt(value: Any) -> datetime | None:
    """ISO 字串或 datetime → 帶時區的 datetime（無時區視為壞值）；None 原樣。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise ResearchGuardError("bad_timestamp", f"不是 ISO 時間：{value!r}") from exc
    if parsed.tzinfo is None:
        raise ResearchGuardError("bad_timestamp", f"時間必須帶時區：{value!r}")
    return parsed


def _uid(value: Any) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except ValueError as exc:
        raise ResearchGuardError("bad_uuid", f"不是 UUID：{value!r}") from exc


def jsonable(value: Any) -> Any:
    """資料列轉 JSON 友善值（UUID／時間／Decimal 轉字串；遞迴）。"""
    if isinstance(value, Mapping):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(v) for v in value]
    if isinstance(value, uuid.UUID | Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def evidence_refs_of(content: str) -> list[str]:
    """PRD 內 `[E-NNN]` 引用（去重、依字典序）。"""
    return sorted(set(_EVIDENCE_REF_RE.findall(content)))


def semver_of(version_no: int, kind: str = "DRAFT") -> str:
    """草稿 `v0.<n>.0-draft`；基線 `v1.0.0`（PRD §5.1.9）。"""
    return "v1.0.0" if kind == "BASELINE" else f"v0.{version_no}.0-draft"


# ── 固定 SQL（`{s}` 是已驗證的 schema 識別字；值一律走 %s 參數）──────────────────────────────────
_SQL_LOCK_PROJECT = ("SELECT id, slug, flow_step, flow_phase, flow_status, flow_detail, "
                     "fsm_project, fsm_generation, archived_at FROM {s}.research_projects "
                     "WHERE id = %s FOR UPDATE")
_SQL_BUMP_SEQ = ("UPDATE {s}.research_projects SET last_event_seq = last_event_seq + 1, "
                 "updated_at = NOW() WHERE id = %s RETURNING last_event_seq, flow_step")
_SQL_INSERT_EVENT = (
    "INSERT INTO {s}.research_events (research_id, seq, event_type, step, actor, ref_kind, "
    "ref_id, payload, occurred_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))")
_SQL_EVENT_EXISTS = ("SELECT 1 AS hit FROM {s}.research_events WHERE research_id = %s AND "
                     "event_type = %s AND ref_kind = %s AND ref_id = %s")
_SQL_ALLOCATE_RP_NO = "SELECT {s}.research_next_rp_no() AS rp_no"
_SQL_INSERT_PROJECT = (
    "INSERT INTO {s}.research_projects (id, rp_no, slug, title, topic, scope, depth_level, "
    "target_scope, workspace_path, fsm_project, fsm_state_dir, flow_step, flow_phase, "
    "flow_status, flow_detail, created_by, created_at, parent_research_id) VALUES (%s, "
    "COALESCE(%s, {s}.research_next_rp_no()), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
    "%s, %s, COALESCE(%s, NOW()), %s) RETURNING rp_no")
_SQL_UPDATE_CURSOR = (
    "UPDATE {s}.research_projects SET flow_step = %s, flow_phase = %s, flow_status = %s, "
    "flow_detail = %s, updated_at = NOW() WHERE id = %s")
_SQL_UPDATE_ARCHIVE = ("UPDATE {s}.research_projects SET archived_at = %s, updated_at = NOW() "
                       "WHERE id = %s")
_SQL_UPDATE_GENERATION = (
    "UPDATE {s}.research_projects SET fsm_generation = %s, fsm_project = %s, flow_step = %s, "
    "flow_phase = %s, flow_status = %s, flow_detail = %s, updated_at = NOW() WHERE id = %s")
_SQL_INSERT_ARTIFACT = (
    "INSERT INTO {s}.research_artifacts (research_id, kind, version, rel_path, sha256, bytes, "
    "origin, content, stage_run_id, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (research_id, kind, version) DO NOTHING RETURNING id")
_SQL_ARTIFACT_SHA = ("SELECT sha256 FROM {s}.research_artifacts WHERE research_id = %s AND "
                     "kind = %s AND version = %s")
_SQL_HEAD_PRD = ("SELECT COALESCE(MAX(version_no), 0) AS head FROM {s}.research_prd_versions "
                 "WHERE research_id = %s")
_SQL_PRD_EXISTS = ("SELECT version_no, semver, sha256 FROM {s}.research_prd_versions "
                   "WHERE research_id = %s AND version_no = %s")
_SQL_INSERT_PRD = (
    "INSERT INTO {s}.research_prd_versions (research_id, version_no, semver, kind, author_kind, "
    "author, parent_version_no, content, rel_path, sha256, bytes, evidence_refs, change_summary, "
    "stage_run_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
_SQL_INSERT_STAGE_RUN = (
    "INSERT INTO {s}.research_stage_runs (id, research_id, stage, round_no, attempt, scope_rev, "
    "status, playbook_sha256, config_sha256, prompt_manifest, allowlist_snapshot, requested_by) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING "
    "RETURNING id")
_SQL_LOCK_STAGE_RUN = (
    "SELECT research_id, stage, round_no, attempt, status, tokens_used, exit_reason, started_at, "
    "finished_at FROM {s}.research_stage_runs WHERE id = %s FOR UPDATE")
_SQL_UPDATE_STAGE_RUN = (
    "UPDATE {s}.research_stage_runs SET status = %s, tokens_used = %s, exit_reason = %s, "
    "started_at = %s, finished_at = %s WHERE id = %s")
_SQL_ROUND_HEAD = ("SELECT COALESCE(MAX(round_no), 0) AS head FROM {s}.research_review_rounds "
                   "WHERE research_id = %s")
_SQL_ROUND_EXISTS = ("SELECT id FROM {s}.research_review_rounds WHERE research_id = %s AND "
                     "round_no = %s")
_SQL_INSERT_ROUND = (
    "INSERT INTO {s}.research_review_rounds (id, research_id, round_no, fsm_generation, "
    "prd_version_no, trigger_kind, precheck_passed, precheck_detail, weighted_score, threshold, "
    "floor_score, min_dimension_score, open_p1_count, passed, verdict, fsm_gate_result, "
    "fsm_retry_count, escalated, stage_run_id, started_at, finished_at) VALUES (%s, %s, %s, %s, "
    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
_SQL_INSERT_SCORE = (
    "INSERT INTO {s}.research_review_scores (round_id, dimension, weight, score, agent_id, "
    "assist_agent_id, assist_agent_yaml_sha256, agent_yaml_path, agent_yaml_sha256, "
    "persona_sha256, summary, raw_rel_path, raw_sha256, stage_run_id) VALUES (%s, %s, %s, %s, "
    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
_SQL_INSERT_DEFECT = (
    "INSERT INTO {s}.research_review_defects (id, round_id, defect_no, dimension, severity, "
    "code, prd_anchor, description, suggestion, evidence_refs) VALUES (%s, %s, %s, %s, %s, %s, "
    "%s, %s, %s, %s)")
_SQL_LOCK_DEFECT = ("SELECT d.id, d.status, r.research_id, d.defect_no, d.severity, d.dimension "
                    "FROM {s}.research_review_defects d JOIN {s}.research_review_rounds r "
                    "ON r.id = d.round_id WHERE d.id = %s FOR UPDATE OF d")
_SQL_UPDATE_DEFECT = (
    "UPDATE {s}.research_review_defects SET status = %s, fixed_in_version_no = %s, "
    "waived_by = %s, waiver_reason = %s, resolved_at = %s WHERE id = %s")
_SQL_DECISION_EXISTS = "SELECT 1 AS hit FROM {s}.research_gate_decisions WHERE id = %s"
_SQL_INSERT_DECISION = (
    "INSERT INTO {s}.research_gate_decisions (id, research_id, gate, decision, decided_by, "
    "decided_at, prd_version_no, review_round_no, fsm_project, fsm_stage, fsm_state_after, "
    "frozen_digests, reason, audit_trace_id) VALUES (%s, %s, %s, %s, %s, COALESCE(%s, NOW()), "
    "%s, %s, %s, %s, %s, %s, %s, %s)")
_SQL_INSERT_SOURCE = (
    "INSERT INTO {s}.research_sources (id, research_id, source_no, layer, tier, verification, "
    "anchor_kind, url, doi, git_commit, title, authors_org, published_at, source_type, "
    "license_spdx, license_note, clue_only, first_fetched_at) VALUES (%s, %s, %s, %s, %s, %s, "
    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW())) "
    "ON CONFLICT (research_id, source_no) DO NOTHING RETURNING id")
_SQL_LOCK_SOURCE = ("SELECT id, research_id, source_no, layer, tier, verification, title, url "
                    "FROM {s}.research_sources WHERE id = %s FOR UPDATE")
_SQL_SOURCE_BY_NO = "SELECT id FROM {s}.research_sources WHERE research_id = %s AND source_no = %s"
_SQL_UPDATE_SOURCE = "UPDATE {s}.research_sources SET verification = %s WHERE id = %s"
_SQL_FETCH_HEAD = ("SELECT COALESCE(MAX(substr(fetch_no, 3)::int), 0) AS head FROM "
                   "{s}.research_fetches WHERE research_id = %s")
_SQL_INSERT_FETCH = (
    "INSERT INTO {s}.research_fetches (id, research_id, source_id, stage_run_id, layer, fetch_no, "
    "fetch_method, observed_by, search_no, result_urls, host, url, query_text, http_status, "
    "outcome, raw_rel_path, raw_sha256, raw_bytes, duration_ms) VALUES (%s, %s, %s, %s, %s, %s, "
    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING "
    "RETURNING fetch_no")
_SQL_INSERT_ITEM = (
    "INSERT INTO {s}.research_evidence_items (research_id, matrix_version, scope_rev, "
    "evidence_no, source_id, candidate, claim, f1_mechanism, f2_evidence, f3_critique, "
    "f4_risk_tags, f5_applicability, f6_limits, f7_verification, strength, unanchored) VALUES "
    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
_SQL_INSERT_ALLOWLIST = (
    "INSERT INTO {s}.research_allowlist_entries (id, list_kind, host, layer, purpose, tos_note, "
    "min_interval_seconds, tos_acknowledged, added_by) VALUES (COALESCE(%s, gen_random_uuid()), "
    "%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id")
_SQL_LOCK_ALLOWLIST = ("SELECT id, list_kind, host, enabled FROM {s}.research_allowlist_entries "
                       "WHERE id = %s FOR UPDATE")
_SQL_UPDATE_ALLOWLIST_ON = ("UPDATE {s}.research_allowlist_entries SET enabled = %s WHERE "
                            "id = %s")
_SQL_UPDATE_ALLOWLIST_OFF = (
    "UPDATE {s}.research_allowlist_entries SET enabled = %s, disabled_by = %s, "
    "disabled_at = NOW() WHERE id = %s")


# ── 交易 ───────────────────────────────────────────────────────────────────────────────────
StatementHook = Callable[[str, Sequence[Any]], None]


class ResearchTx:
    """一個交易內的語句執行者。SQL 一律經 `run`／`rows`／`one`，可被 `statement_hook` 記錄。"""

    def __init__(self, conn: Any, ident: str, hook: StatementHook | None) -> None:
        self._conn = conn
        self._ident = ident
        self._hook = hook

    def _execute(self, text: str, params: Sequence[Any], *, fetch: str) -> Any:
        if self._hook is not None:
            self._hook(text, params)
        with self._conn.cursor(row_factory=dict_row) as cur:
            cur.execute(text.replace("{s}", self._ident), params)
            if fetch == "all":
                return cur.fetchall()
            if fetch == "one":
                return cur.fetchone()
            return cur.rowcount

    def run(self, text: str, params: Sequence[Any] = ()) -> int:
        return int(self._execute(text, params, fetch="none"))

    def rows(self, text: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        return list(self._execute(text, params, fetch="all"))

    def one(self, text: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        return self._execute(text, params, fetch="one")

    # ── 事件帳 ────────────────────────────────────────────────────────────────────────────
    def append_event(self, research_id: Any, event_type: str, payload: Mapping[str, Any], *,
                     actor: str, step: str | None = None, ref_kind: str | None = None,
                     ref_id: Any = None, occurred_at: Any = None) -> int:
        """配 `seq`（專案列 `last_event_seq`＋1，同交易；回滾不留洞）並寫事件列。"""
        if event_type not in EVENT_TYPES:
            raise ResearchGuardError("event_type", f"不在 P0 事件型別內：{event_type!r}")
        required = EVENT_PAYLOAD_KEYS[event_type]
        allowed = required | EVENT_OPTIONAL_KEYS.get(event_type, frozenset())
        if not required <= set(payload) <= allowed:
            raise ResearchGuardError(
                "event_payload", f"{event_type} 的 payload 鍵須為 "
                f"{sorted(required)}（可另帶 {sorted(allowed - required)}），收到 "
                f"{sorted(payload)}")
        if not actor or len(actor) > 100:
            raise ResearchGuardError("actor", "actor 須為 1 至 100 字")
        bumped = self.one(_SQL_BUMP_SEQ, (research_id,))
        if bumped is None:
            raise ResearchGuardError("project_not_found", str(research_id))
        seq = int(bumped["last_event_seq"])
        self.run(_SQL_INSERT_EVENT, (research_id, seq, event_type, step or bumped["flow_step"],
                                     actor, ref_kind, ref_id, Jsonb(dict(payload)),
                                     _dt(occurred_at)))
        return seq

    def lock_project(self, research_id: Any) -> dict[str, Any]:
        row = self.one(_SQL_LOCK_PROJECT, (research_id,))
        if row is None:
            raise ResearchGuardError("project_not_found", str(research_id))
        return row


# ── 事件 payload（API 契約 §3；camelCase）──────────────────────────────────────────────────────
def step_payload(flow: Mapping[str, Any]) -> dict[str, Any]:
    return {"flowStep": flow["step"], "flowPhase": flow["phase"], "flowStatus": flow["status"],
            "flowDetail": flow.get("detail", "")}


def _flow_of(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"step": row["flow_step"], "phase": row["flow_phase"], "status": row["flow_status"],
            "detail": row["flow_detail"]}


def _check_flow(flow: Mapping[str, Any]) -> dict[str, Any]:
    missing = [k for k in ("step", "phase", "status") if not flow.get(k)]
    if missing:
        raise ResearchGuardError("flow", f"游標缺欄位：{missing}")
    return {"step": flow["step"], "phase": flow["phase"], "status": flow["status"],
            "detail": str(flow.get("detail", ""))[:300]}


def _set_cursor(tx: ResearchTx, research_id: Any, current: Mapping[str, Any],
                flow: Mapping[str, Any], actor: str, occurred_at: Any) -> int | None:
    """游標與現值不同才 UPDATE，並同交易發 `research.step`；回 seq（沒變回 None）。"""
    new = _check_flow(flow)
    if new == _flow_of(current):
        return None
    tx.run(_SQL_UPDATE_CURSOR, (new["step"], new["phase"], new["status"], new["detail"],
                                research_id))
    return tx.append_event(research_id, "research.step", step_payload(new), actor=actor,
                           step=new["step"], occurred_at=occurred_at)


# ── 操作（一個操作＝一個交易；`p` 是 JSON 友善的 payload）───────────────────────────────────────
def _register_artifact(tx: ResearchTx, rid: Any, *, kind: str, version: int, rel_path: str,
                       sha256: str, size: int, origin: str, content: str | None,
                       stage_run_id: Any, created_by: str) -> bool:
    """檔案登記列（append-only）。同 (研究, kind, 版) 已存在：位元組相同＝重放跳過（回 False），
    不同＝`artifact_version_conflict`（不是冪等重放、不得靜默吞掉）。"""
    if kind == "EVIDENCE_ITEMS" and not content:
        raise ResearchGuardError("evidence_items_content_required",
                                 "kind=EVIDENCE_ITEMS 的登記列 content 必填")
    row = tx.one(_SQL_INSERT_ARTIFACT, (
        rid, kind, version, rel_path, sha256, size, origin, content,
        _uid(stage_run_id) if stage_run_id else None, created_by))
    if row is not None:
        return True
    existing = tx.one(_SQL_ARTIFACT_SHA, (rid, kind, version))
    if existing is not None and existing["sha256"] != sha256:
        raise ResearchConflict("artifact_version_conflict", kind=kind, version=version)
    return False


def _op_project_create(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """建專案列＋ISSUE_SCOPE 登記列（可省）＋`research.step`（seq 1）。已存在（同 id）＝跳過。"""
    rid = _uid(p["research_id"])
    existing = tx.one("SELECT rp_no FROM {s}.research_projects WHERE id = %s", (rid,))
    if existing is not None:
        return {"applied": False, "rp_no": existing["rp_no"]}
    if tx.one("SELECT 1 AS hit FROM {s}.research_projects WHERE slug = %s AND archived_at IS NULL",
              (p["slug"],)) is not None:
        raise ResearchConflict("slug_in_use", slug=p["slug"])
    flow = _check_flow(p.get("flow") or INITIAL_FLOW)
    try:
        row = tx.one(_SQL_INSERT_PROJECT, (
            rid, p.get("rp_no"), p["slug"], p["title"], p["topic"],
            Jsonb(dict(p.get("scope") or {})), p.get("depth_level", "STANDARD"),
            p.get("target_scope", "UNDECIDED"), p["workspace_path"], p["fsm_project"],
            p["fsm_state_dir"], flow["step"], flow["phase"], flow["status"], flow["detail"],
            p["created_by"], _dt(p.get("created_at")),
            _uid(p["parent_research_id"]) if p.get("parent_research_id") else None))
    except psycopg.errors.UniqueViolation as exc:      # 並發建立同 slug：部分唯一索引兜底
        raise ResearchConflict("slug_in_use", slug=p["slug"]) from exc
    assert row is not None
    scope_file = p.get("issue_scope")
    if scope_file:
        _register_artifact(tx, rid, kind="ISSUE_SCOPE", version=1, rel_path=scope_file["rel_path"],
                           sha256=scope_file["sha256"], size=scope_file["bytes"], origin="BRIDGE",
                           content=None, stage_run_id=None, created_by=p["created_by"])
    seq = tx.append_event(rid, "research.step", step_payload(flow), actor=p["created_by"],
                          step=flow["step"], occurred_at=p.get("occurred_at"))
    return {"applied": True, "rp_no": row["rp_no"], "seq": seq}


def _op_allocate_rp_no(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """預先配一個顯示編號 `RP-NNNN`（`issue_scope.json` 要先寫檔、檔內含編號，所以得在建列之前取）。

    序號只前進、不回頭：之後沒用上的編號是空洞，不會重號（單調、UNIQUE）。"""
    row = tx.one(_SQL_ALLOCATE_RP_NO)
    assert row is not None
    return {"applied": True, "rp_no": row["rp_no"]}


def _op_set_cursor(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """游標更新（`research.step` 同交易）。與現值相同＝跳過。"""
    rid = _uid(p["research_id"])
    seq = _set_cursor(tx, rid, tx.lock_project(rid), p["flow"], p["actor"], p.get("occurred_at"))
    return {"applied": seq is not None, "seq": seq}


def _op_archive(tx: ResearchTx, p: Mapping[str, Any], *, archive: bool) -> dict[str, Any]:
    """封存（軟刪除）或復原；事件 `research.step` 帶不變的游標。狀態已是目標＝跳過。"""
    rid = _uid(p["research_id"])
    row = tx.lock_project(rid)
    if (row["archived_at"] is not None) == archive:
        return {"applied": False}
    if not archive and tx.one(
            "SELECT 1 AS hit FROM {s}.research_projects WHERE slug = %s AND archived_at IS NULL "
            "AND id <> %s", (row["slug"], rid)) is not None:
        raise ResearchConflict("slug_in_use", slug=row["slug"])
    tx.run(_SQL_UPDATE_ARCHIVE, (utc_now() if archive else None, rid))
    seq = tx.append_event(rid, "research.step", step_payload(_flow_of(row)), actor=p["actor"],
                          occurred_at=p.get("occurred_at"))
    return {"applied": True, "seq": seq}


def _op_archive_project(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    return _op_archive(tx, p, archive=True)


def _op_restore_project(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    return _op_archive(tx, p, archive=False)


def _insert_decision(tx: ResearchTx, rid: Any, d: Mapping[str, Any]) -> bool:
    """決定列（append-only）；同 id 已存在回 False。"""
    did = _uid(d["decision_id"])
    if tx.one(_SQL_DECISION_EXISTS, (did,)) is not None:
        return False
    tx.run(_SQL_INSERT_DECISION, (
        did, rid, d["gate"], d["decision"], d["decided_by"], _dt(d.get("decided_at")),
        d.get("prd_version_no"), d.get("review_round_no"), d["fsm_project"], d.get("fsm_stage"),
        d.get("fsm_state_after"), Jsonb(dict(d.get("frozen_digests") or {})),
        d.get("reason", ""), d.get("audit_trace_id")))
    return True


def _gate_event(tx: ResearchTx, rid: Any, d: Mapping[str, Any]) -> int:
    return tx.append_event(rid, "research.gate", {
        "gate": d["gate"], "decision": d["decision"], "decidedBy": d["decided_by"],
        "fsmStage": d.get("fsm_stage"), "frozenDigests": dict(d.get("frozen_digests") or {})},
        actor=d["decided_by"], ref_kind="gate_decision", ref_id=_uid(d["decision_id"]),
        occurred_at=d.get("decided_at"))


def _op_gate_decision(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """人工決定列＋`research.gate`＋（選填）游標更新，同一交易。同 `decision_id` 已存在＝跳過。"""
    rid = _uid(p["research_id"])
    row = tx.lock_project(rid)
    if not _insert_decision(tx, rid, p):
        return {"applied": False, "decision_id": str(p["decision_id"])}
    seq = _gate_event(tx, rid, p)
    if p.get("flow"):
        _set_cursor(tx, rid, row, p["flow"], p["decided_by"], p.get("decided_at"))
    return {"applied": True, "decision_id": str(p["decision_id"]), "seq": seq}


def _op_abandon_fsm_key(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """換世代（D-60、D-64）：放棄舊外環鍵、改指新鍵，單一交易；舊鍵留 ESCALATION、輪列原封不動。

    寫決定列（ABANDON_KEY／ABANDONED）、`fsm_generation`＋1、`fsm_project` 改新鍵、游標改為
    REVISING／IDLE，事件 `research.gate` 與 `research.step`。同 `decision_id` 已存在＝跳過。"""
    rid = _uid(p["research_id"])
    row = tx.lock_project(rid)
    decision = {**p, "gate": "ABANDON_KEY", "decision": "ABANDONED",
                "fsm_project": p["old_fsm_project"], "fsm_stage": None}
    if not _insert_decision(tx, rid, decision):
        return {"applied": False, "decision_id": str(p["decision_id"])}
    flow = _check_flow(p.get("flow") or {"step": row["flow_step"], "phase": "REVISING",
                                         "status": "IDLE", "detail": ""})
    tx.run(_SQL_UPDATE_GENERATION, (p["new_generation"], p["new_fsm_project"], flow["step"],
                                    flow["phase"], flow["status"], flow["detail"], rid))
    gate_seq = _gate_event(tx, rid, decision)
    step_seq = tx.append_event(rid, "research.step", step_payload(flow), actor=p["decided_by"],
                               step=flow["step"], occurred_at=p.get("decided_at"))
    return {"applied": True, "decision_id": str(p["decision_id"]), "seq": step_seq,
            "gate_seq": gate_seq}


def _insert_prd(tx: ResearchTx, rid: Any, p: Mapping[str, Any], head: int) -> None:
    kind, content = p.get("kind", "DRAFT"), p["content"]
    version_no = int(p["version_no"])
    tx.run(_SQL_INSERT_PRD, (
        rid, version_no, p.get("semver") or semver_of(version_no, kind), kind, p["author_kind"],
        p["author"], head or None, content, p["rel_path"], p["sha256"], p["bytes"],
        p.get("evidence_refs") or evidence_refs_of(content), p.get("change_summary", "")[:500],
        _uid(p["stage_run_id"]) if p.get("stage_run_id") else None))
    _register_artifact(tx, rid, kind="PRD_BASELINE" if kind == "BASELINE" else "PRD_DRAFT",
                       version=version_no, rel_path=p["rel_path"], sha256=p["sha256"],
                       size=p["bytes"], origin=p["author_kind"], content=None,
                       stage_run_id=p.get("stage_run_id"), created_by=p["author"])


def _op_save_prd(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """存 PRD 新版（樂觀鎖）：`version_no` 必須是 head＋1，否則 `prd_version_conflict`。

    寫版本列、檔案登記列、（選填）游標更新與 `research.prd` 事件，同一交易。同版已存在＝跳過。"""
    rid = _uid(p["research_id"])
    row = tx.lock_project(rid)
    version_no = int(p["version_no"])
    head_row = tx.one(_SQL_HEAD_PRD, (rid,))
    head = int(head_row["head"]) if head_row else 0
    existing = tx.one(_SQL_PRD_EXISTS, (rid, version_no))
    if existing is not None:
        if existing["sha256"] != p["sha256"]:       # 同版號、不同內容：不是重放
            raise ResearchConflict("prd_version_conflict", headVersion=head)
        return {"applied": False, "version_no": version_no, "sha256": existing["sha256"]}
    if version_no != head + 1:
        raise ResearchConflict("prd_version_conflict", headVersion=head)
    _insert_prd(tx, rid, p, head)
    seq = tx.append_event(rid, "research.prd", {
        "versionNo": version_no, "semver": p.get("semver") or semver_of(version_no, p.get(
            "kind", "DRAFT")), "authorKind": p["author_kind"], "author": p["author"],
        "sha256": p["sha256"]}, actor=p["author"], occurred_at=p.get("occurred_at"))
    if p.get("flow"):
        _set_cursor(tx, rid, row, p["flow"], p["author"], p.get("occurred_at"))
    return {"applied": True, "version_no": version_no, "seq": seq}


def _stage_run_payload(rid: Any, row: Mapping[str, Any], run_id: Any) -> dict[str, Any]:
    return {"stage": row["stage"], "roundNo": row["round_no"], "attempt": row["attempt"],
            "stageRunId": str(run_id), "engineRunId": str(run_id), "status": row["status"],
            "tokensUsed": row["tokens_used"]}


def _op_insert_stage_run(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """建 stage run 列（編譯結果欄一次寫入、之後唯讀）＋`research.run`。同 id 已存在＝跳過。"""
    rid, run_id = _uid(p["research_id"]), _uid(p["stage_run_id"])
    tx.lock_project(rid)
    try:
        row = tx.one(_SQL_INSERT_STAGE_RUN, (
            run_id, rid, p["stage"], p.get("round_no", 0), p.get("attempt", 1),
            p.get("scope_rev", 1), p.get("status", "QUEUED"), p.get("playbook_sha256"),
            p.get("config_sha256"), Jsonb(list(p.get("prompt_manifest") or [])),
            Jsonb(list(p.get("allowlist_snapshot") or [])), p["requested_by"]))
    except psycopg.errors.UniqueViolation as exc:      # 同專案已有進行中的 stage run（D-61）
        raise ResearchConflict("stage_conflict") from exc
    if row is None:
        return {"applied": False}
    seq = tx.append_event(rid, "research.run", _stage_run_payload(rid, {
        "stage": p["stage"], "round_no": p.get("round_no", 0), "attempt": p.get("attempt", 1),
        "status": p.get("status", "QUEUED"), "tokens_used": 0}, run_id),
        actor=p["requested_by"], ref_kind="stage_run", ref_id=run_id,
        occurred_at=p.get("occurred_at"))
    return {"applied": True, "seq": seq}


def _op_update_stage_run(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """stage run 的狀態、token、結束理由、起訖時間（受控欄位）＋`research.run`。沒變＝跳過。"""
    run_id = _uid(p["stage_run_id"])
    row = tx.one(_SQL_LOCK_STAGE_RUN, (run_id,))
    if row is None:
        raise ResearchGuardError("stage_run_not_found", str(run_id))
    new = {"status": p.get("status", row["status"]),
           "tokens_used": p.get("tokens_used", row["tokens_used"]),
           "exit_reason": p.get("exit_reason", row["exit_reason"]),
           "started_at": _dt(p.get("started_at")) or row["started_at"],
           "finished_at": _dt(p.get("finished_at")) or row["finished_at"]}
    if all(new[k] == row[k] for k in new):
        return {"applied": False}
    tx.run(_SQL_UPDATE_STAGE_RUN, (new["status"], new["tokens_used"], new["exit_reason"],
                                   new["started_at"], new["finished_at"], run_id))
    rid = row["research_id"]
    seq = tx.append_event(rid, "research.run", _stage_run_payload(rid, {**row, **new}, run_id),
                          actor=p["actor"], ref_kind="stage_run", ref_id=run_id,
                          occurred_at=p.get("occurred_at"))
    return {"applied": True, "seq": seq}


def _op_insert_artifact(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """檔案登記列（append-only）。EVIDENCE_ITEMS 的 `content` 必填（D-56；DB 不擋、由這裡驗）。"""
    rid = _uid(p["research_id"])
    tx.lock_project(rid)
    inserted = _register_artifact(
        tx, rid, kind=p["kind"], version=p["version"], rel_path=p["rel_path"],
        sha256=p["sha256"], size=p["bytes"], origin=p["origin"], content=p.get("content"),
        stage_run_id=p.get("stage_run_id"), created_by=p["created_by"])
    return {"applied": inserted}


def _op_insert_review_round(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """審查輪列＋四維分數＋缺陷列＋`research.review`（＋每個缺陷一筆 `research.defect`），一次寫入。

    輪列 append-only，寫入器沒有任何 UPDATE／DELETE；`round_no` 必須是已完成輪數＋1（連續，D-61）。
    同輪號已存在＝跳過（重放冪等）。"""
    rid, r = _uid(p["research_id"]), p["round"]
    tx.lock_project(rid)
    round_no = int(r["round_no"])
    existing = tx.one(_SQL_ROUND_EXISTS, (rid, round_no))
    if existing is not None:
        if r.get("id") and str(existing["id"]) != str(_uid(r["id"])):     # 同輪號、不同輪：不是重放
            raise ResearchConflict("review_round_conflict", roundNo=round_no)
        return {"applied": False, "round_no": round_no}
    head_row = tx.one(_SQL_ROUND_HEAD, (rid,))
    head = int(head_row["head"]) if head_row else 0
    if round_no != head + 1:
        raise ResearchGuardError("round_no_gap", f"輪號須為 {head + 1}，收到 {round_no}",
                                 expected=head + 1, got=round_no)
    round_id = _uid(r.get("id") or uuid.uuid4())
    tx.run(_SQL_INSERT_ROUND, (
        round_id, rid, round_no, r.get("fsm_generation", 1), r["prd_version_no"],
        r["trigger_kind"], r["precheck_passed"], Jsonb(dict(r.get("precheck_detail") or {})),
        r.get("weighted_score"), r.get("threshold", DEFAULT_THRESHOLD),
        r.get("floor_score", DEFAULT_FLOOR_SCORE), r.get("min_dimension_score"),
        r.get("open_p1_count", 0), r["passed"], r["verdict"], r.get("fsm_gate_result"),
        r.get("fsm_retry_count"), r.get("escalated", False), _uid(r["stage_run_id"]),
        _dt(r["started_at"]), _dt(r["finished_at"])))
    for s in p.get("scores") or []:
        tx.run(_SQL_INSERT_SCORE, (
            round_id, s["dimension"], s.get("weight", REVIEW_WEIGHTS.get(s["dimension"])),
            s["score"], s["agent_id"], s.get("assist_agent_id"),
            s.get("assist_agent_yaml_sha256"), s["agent_yaml_path"], s["agent_yaml_sha256"],
            s["persona_sha256"], s.get("summary", ""), s["raw_rel_path"], s["raw_sha256"],
            _uid(s["stage_run_id"]) if s.get("stage_run_id") else None))
    for d in p.get("defects") or []:
        tx.run(_SQL_INSERT_DEFECT, (
            _uid(d.get("id") or uuid.uuid4()), round_id, d["defect_no"], d["dimension"],
            d["severity"], d["code"], d.get("prd_anchor", ""), d["description"],
            d.get("suggestion", ""), list(d.get("evidence_refs") or [])))
    score = r.get("weighted_score")
    seq = tx.append_event(rid, "research.review", {
        "roundNo": round_no, "weightedScore": None if score is None else float(score),
        "minDimensionScore": r.get("min_dimension_score"),
        "passed": r["passed"], "verdict": r["verdict"], "escalated": r.get("escalated", False)},
        actor=p["actor"], ref_kind="review_round", ref_id=round_id,
        occurred_at=r.get("finished_at"))
    for d in p.get("defects") or []:
        tx.append_event(rid, "research.defect", {
            "defectNo": d["defect_no"], "severity": d["severity"], "dimension": d["dimension"],
            "status": "OPEN"}, actor=p["actor"], ref_kind="review_round", ref_id=round_id,
            occurred_at=r.get("finished_at"))
    return {"applied": True, "round_no": round_no, "round_id": str(round_id), "seq": seq}


def _op_update_defect(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """缺陷狀態單向轉移（審查卡模板 §5.3）＋`research.defect`。狀態沒變＝跳過。"""
    defect_id = _uid(p["defect_id"])
    row = tx.one(_SQL_LOCK_DEFECT, (defect_id,))
    if row is None:
        raise ResearchGuardError("defect_not_found", str(defect_id))
    status = p["status"]
    if status == row["status"]:
        return {"applied": False}
    if status not in DEFECT_TRANSITIONS.get(row["status"], frozenset()):
        raise ResearchGuardError("defect_transition", f"{row['status']} 不得轉為 {status}")
    if status == "WAIVED" and not (p.get("waived_by") and p.get("waiver_reason")):
        raise ResearchGuardError("waiver_required", "WAIVED 須附 waived_by 與 waiver_reason")
    resolved = _dt(p.get("resolved_at")) or (utc_now() if status in (
        "FIXED", "WAIVED", "SUPERSEDED") else None)
    tx.run(_SQL_UPDATE_DEFECT, (status, p.get("fixed_in_version_no"), p.get("waived_by"),
                                p.get("waiver_reason"), resolved, defect_id))
    seq = tx.append_event(row["research_id"], "research.defect", {
        "defectNo": row["defect_no"], "severity": row["severity"],
        "dimension": row["dimension"], "status": status}, actor=p["actor"],
        ref_kind="defect", ref_id=defect_id, occurred_at=p.get("occurred_at"))
    return {"applied": True, "seq": seq}


def _source_event(tx: ResearchTx, rid: Any, s: Mapping[str, Any], actor: str,
                  fetch_outcome: str | None, occurred_at: Any = None) -> int:
    return tx.append_event(rid, "research.source", {
        "sourceNo": s["source_no"], "layer": s["layer"], "tier": s["tier"],
        "verification": s["verification"], "title": s["title"], "url": s["url"],
        "fetchOutcome": fetch_outcome}, actor=actor, ref_kind="source",
        ref_id=_uid(s["id"]) if s.get("id") else None, occurred_at=occurred_at)


def _insert_source(tx: ResearchTx, rid: Any, s: Mapping[str, Any]) -> uuid.UUID | None:
    """來源列；T3 強制 `clue_only`（SOP S2:58）。同 (研究, source_no) 已存在回 None。"""
    if s["tier"] == "T3" and not s.get("clue_only"):
        raise ResearchGuardError("t3_clue_only", "T3 來源只當線索（clue_only 必須為真）")
    source_id = _uid(s.get("id") or uuid.uuid4())
    row = tx.one(_SQL_INSERT_SOURCE, (
        source_id, rid, s["source_no"], s["layer"], s["tier"], s["verification"],
        s["anchor_kind"], s["url"], s.get("doi"), s.get("git_commit"), s["title"],
        s.get("authors_org", ""), s.get("published_at"), s.get("source_type", "OTHER"),
        s.get("license_spdx"), s.get("license_note", ""), bool(s.get("clue_only", False)),
        _dt(s.get("first_fetched_at"))))
    return source_id if row is not None else None


def _op_insert_source(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """來源列＋`research.source`。同來源編號已存在＝跳過。"""
    rid = _uid(p["research_id"])
    tx.lock_project(rid)
    source_id = _insert_source(tx, rid, p["source"])
    if source_id is None:
        return {"applied": False}
    seq = _source_event(tx, rid, {**p["source"], "id": source_id}, p["actor"],
                        p.get("fetch_outcome"), p.get("occurred_at"))
    return {"applied": True, "source_id": str(source_id), "seq": seq}


def _op_upgrade_source(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """查證層級只升不降（V1<V2<V3；寫入器拒降級，DB 觸發器為第二道）＋`research.source`。"""
    source_id = _uid(p["source_id"])
    row = tx.one(_SQL_LOCK_SOURCE, (source_id,))
    if row is None:
        raise ResearchGuardError("source_not_found", str(source_id))
    new = p["verification"]
    if new not in VERIFICATION_ORDER:
        raise ResearchGuardError("verification_value", f"不是 V1／V2／V3：{new!r}")
    if VERIFICATION_ORDER[new] < VERIFICATION_ORDER[row["verification"]]:
        raise ResearchGuardError("verification_downgrade",
                                 f"{row['verification']} 不得降為 {new}")
    if new == row["verification"]:
        return {"applied": False}
    tx.run(_SQL_UPDATE_SOURCE, (new, source_id))
    seq = _source_event(tx, row["research_id"], {**row, "verification": new}, p["actor"], None,
                        p.get("occurred_at"))
    return {"applied": True, "seq": seq}


def _op_insert_fetch(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """抓取紀錄（含被拒；append-only）。`fetch_no` 由寫入器於同交易 max＋1 配號。同 id＝跳過。"""
    rid = _uid(p["research_id"])
    tx.lock_project(rid)
    f = p["fetch"]
    head_row = tx.one(_SQL_FETCH_HEAD, (rid,))
    fetch_no = f"F-{(int(head_row['head']) if head_row else 0) + 1:04d}"
    row = tx.one(_SQL_INSERT_FETCH, (
        _uid(f.get("id") or uuid.uuid4()), rid, _uid(f["source_id"]) if f.get("source_id") else
        None, _uid(f["stage_run_id"]) if f.get("stage_run_id") else None, f["layer"], fetch_no,
        f["fetch_method"], f["observed_by"], f.get("search_no"),
        Jsonb(list(f.get("result_urls") or [])), f.get("host"), f.get("url"),
        f.get("query_text"), f.get("http_status"), f["outcome"], f.get("raw_rel_path"),
        f.get("raw_sha256"), f.get("raw_bytes"), f.get("duration_ms")))
    return {"applied": row is not None, "fetch_no": row["fetch_no"] if row else None}


def _op_record_evidence(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """證據矩陣一版：EVIDENCE_ITEMS 登記列（content 必填）＋新來源＋證據列＋事件，同一交易。

    同 (研究, matrix_version) 的登記列已存在＝整筆跳過。證據列的 `source_no` 對到既有來源。"""
    rid, version = _uid(p["research_id"]), int(p["matrix_version"])
    tx.lock_project(rid)
    art = p["artifact"]
    if not _register_artifact(
            tx, rid, kind="EVIDENCE_ITEMS", version=version, rel_path=art["rel_path"],
            sha256=art["sha256"], size=art["bytes"], origin=art.get("origin", "AGENT"),
            content=art.get("content"), stage_run_id=p.get("stage_run_id"),
            created_by=art["created_by"]):
        return {"applied": False}
    for s in p.get("sources") or []:
        source_id = _insert_source(tx, rid, s)
        if source_id is not None:
            _source_event(tx, rid, {**s, "id": source_id}, p["actor"], s.get("fetch_outcome"))
    for item in p.get("items") or []:
        src = tx.one(_SQL_SOURCE_BY_NO, (rid, item["source_no"]))
        if src is None:
            raise ResearchGuardError("evidence_source_missing", item["source_no"])
        tx.run(_SQL_INSERT_ITEM, (
            rid, version, p.get("scope_rev", 1), item["evidence_no"], src["id"],
            item.get("candidate"), item["claim"], item["f1_mechanism"], item["f2_evidence"],
            item["f3_critique"], list(item.get("f4_risk_tags") or []),
            Jsonb(dict(item["f5_applicability"])), item["f6_limits"], item["f7_verification"],
            item.get("strength", "WEAK"), bool(item.get("unanchored", False))))
        tx.append_event(rid, "research.evidence", {
            "matrixVersion": version, "evidenceNo": item["evidence_no"],
            "sourceNo": item["source_no"], "claim": item["claim"],
            "strength": item.get("strength", "WEAK")}, actor=p["actor"],
            ref_kind="evidence", ref_id=None)
    return {"applied": True, "matrix_version": version}


def _op_append_event(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """單獨追加事件（alert、reconcile、review_invalid…）。給了 `ref_kind`＋`ref_id` 就以它去重。"""
    rid = _uid(p["research_id"])
    ref_id = _uid(p["ref_id"]) if p.get("ref_id") else None
    if ref_id is not None and p.get("ref_kind") and tx.one(_SQL_EVENT_EXISTS, (
            rid, p["event_type"], p["ref_kind"], ref_id)) is not None:
        return {"applied": False}
    seq = tx.append_event(rid, p["event_type"], p.get("payload") or {}, actor=p["actor"],
                          step=p.get("step"), ref_kind=p.get("ref_kind"), ref_id=ref_id,
                          occurred_at=p.get("occurred_at"))
    return {"applied": True, "seq": seq}


def _op_add_allowlist(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """ADMIN 新增 allowlist 條目（D-17）。全域資源：**不寫 research_events**（D-52）。

    Reddit 須先確認條款（`terms_ack_required`）；同 (list_kind, host) 已存在＝
    `allowlist_exists`。"""
    host = str(p["host"]).lower()
    if _REDDIT_RE.search(host) and not p.get("tos_acknowledged"):
        raise ResearchGuardError("terms_ack_required", "Reddit 須先確認條款")
    interval = int(p.get("min_interval_seconds", 3))
    if not 1 <= interval <= 3600:
        raise ResearchGuardError("min_interval_range", "min_interval_seconds 須為 1 至 3600")
    try:
        row = tx.one(_SQL_INSERT_ALLOWLIST, (
            _uid(p["entry_id"]) if p.get("entry_id") else None, p["list_kind"], host, p["layer"],
            p.get("purpose", "")[:200], p.get("tos_note", ""), interval,
            bool(p.get("tos_acknowledged", False)), p["added_by"]))
    except psycopg.errors.UniqueViolation as exc:
        raise ResearchConflict("allowlist_exists", host=host) from exc
    assert row is not None
    return {"applied": True, "entry_id": str(row["id"])}


def _op_set_allowlist_enabled(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """停用／重新啟用（只改 enabled 與停用欄；不可刪）。不寫 research_events（D-52）。"""
    entry_id = _uid(p["entry_id"])
    row = tx.one(_SQL_LOCK_ALLOWLIST, (entry_id,))
    if row is None:
        raise ResearchGuardError("allowlist_not_found", str(entry_id))
    enabled = bool(p["enabled"])
    if enabled == row["enabled"]:
        return {"applied": False}
    if enabled:
        tx.run(_SQL_UPDATE_ALLOWLIST_ON, (True, entry_id))
    else:
        tx.run(_SQL_UPDATE_ALLOWLIST_OFF, (False, p["disabled_by"], entry_id))
    return {"applied": True}


# ── P1 分流操作（V19；Bridge 是 research_route_decisions／research_route_steps 的唯一寫入者）──────
#: 分流的步驟名（V19 CHECK 的十一個值；軌道 A 與 B 各用其中一部分，順序見 `route.py`）。
ROUTE_STEP_NAMES: tuple[str, ...] = (
    "VALIDATE_TARGET", "GIT_SWITCH", "SCAFFOLD_FILES", "GIT_INIT", "GIT_COMMIT", "GH_REPO_CREATE",
    "PUBLISH_DOCS", "COPY_WORKSPACE", "REGISTER_STUB", "IMPL_KEY_INIT", "BASELINE_ADOPT")
#: 分流列的 `status` 值域（V19 CHECK）；進行中＝部分唯一索引 `ux_research_route_active` 涵蓋的三值。
ROUTE_ACTIVE_STATUSES = ("PENDING", "RUNNING", "SUCCEEDED")
ROUTE_FLOW_RUNNING = {"step": "route", "phase": "ROUTING", "status": "RUNNING", "detail": ""}
ROUTE_FLOW_DONE = {"step": "build", "phase": "ROUTED", "status": "IDLE", "detail": ""}
_SQL_ROUTE_LOCK = ("SELECT id, research_id, status, failure_step FROM "
                   "{s}.research_route_decisions WHERE id = %s FOR UPDATE")
_SQL_INSERT_ROUTE = (
    "INSERT INTO {s}.research_route_decisions (id, research_id, track, target_kind, "
    "target_module, target_path, git_branch, base_ref, repo_visibility, stack_template, "
    "console_project_id, scope_differs_reason, decided_by, created_at) VALUES (%s, %s, %s, %s, "
    "%s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW())) ON CONFLICT (id) DO NOTHING "
    "RETURNING id")
_SQL_UPDATE_ROUTE_STATUS = "UPDATE {s}.research_route_decisions SET status = %s WHERE id = %s"
_SQL_UPDATE_ROUTE_FINISH = (
    "UPDATE {s}.research_route_decisions SET status = %s, failure_step = %s, finished_at = %s, "
    "published_docs = %s, repo_url = %s WHERE id = %s")
_SQL_UPDATE_ROUTE_IMPL = ("UPDATE {s}.research_route_decisions SET impl_fsm_project = %s, "
                          "impl_state_dir = %s WHERE id = %s")
_SQL_UPDATE_PROJECT_CONSOLE = ("UPDATE {s}.research_projects SET console_project_id = %s, "
                               "updated_at = NOW() WHERE id = %s")
_SQL_STEP_LOCK = ("SELECT status, exit_code, stdout_tail, stderr_tail FROM "
                  "{s}.research_route_steps WHERE route_id = %s AND step_no = %s FOR UPDATE")
_SQL_INSERT_STEP = (
    "INSERT INTO {s}.research_route_steps (route_id, step_no, step, status, argv_redacted, "
    "exit_code, stdout_tail, stderr_tail, started_at, finished_at) VALUES (%s, %s, %s, %s, %s, "
    "%s, %s, %s, COALESCE(%s, NOW()), %s) ON CONFLICT (route_id, step_no) DO NOTHING "
    "RETURNING step_no")
_SQL_UPDATE_STEP = ("UPDATE {s}.research_route_steps SET status = %s, exit_code = %s, "
                    "stdout_tail = %s, stderr_tail = %s, finished_at = %s WHERE route_id = %s "
                    "AND step_no = %s")
_SQL_OPEN_STEPS = ("SELECT step_no, step FROM {s}.research_route_steps WHERE route_id = %s AND "
                   "status = 'RUNNING' ORDER BY step_no FOR UPDATE")
_SQL_LAST_STEP = ("SELECT step FROM {s}.research_route_steps WHERE route_id = %s "
                  "ORDER BY step_no DESC LIMIT 1")


def _route_event(tx: ResearchTx, rid: Any, route_id: Any, step_no: int, step: str, status: str,
                 *, actor: str, stamp: str, reason: str | None = None) -> int | None:
    """`research.route` 事件（契約 §3）；路由 id、步號、狀態、時間戳相同者只寫一次（重放冪等）。"""
    ref = uuid.uuid5(uuid.NAMESPACE_URL, f"route:{route_id}:{step_no}:{status}:{stamp}")
    if tx.one(_SQL_EVENT_EXISTS, (rid, "research.route", "route", ref)) is not None:
        return None
    payload: dict[str, Any] = {"routeId": str(route_id), "stepNo": step_no, "step": step,
                               "status": status}
    if reason is not None:
        payload["reason"] = reason
    return tx.append_event(rid, "research.route", payload, actor=actor, ref_kind="route",
                           ref_id=ref)


def _op_route_create(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """建分流列（`PENDING`）＋`research.route`。每研究專案至多一個 PENDING／RUNNING／SUCCEEDED
    （部分唯一索引）：違反＝`route_conflict`；`console_project_id` 指向不存在的專案＝
    `console_project_not_found`（外鍵由 DB 擋，這裡轉成結構化錯誤）。同 id 已存在＝跳過。"""
    rid, route_id = _uid(p["research_id"]), _uid(p["route_id"])
    tx.lock_project(rid)
    if tx.one(_SQL_ROUTE_LOCK, (route_id,)) is not None:
        return {"applied": False}
    try:
        row = tx.one(_SQL_INSERT_ROUTE, (
            route_id, rid, p["track"], p["target_kind"], p.get("target_module"), p["target_path"],
            p.get("git_branch"), p.get("base_ref"), p.get("repo_visibility"),
            p.get("stack_template"), _uid(p["console_project_id"]) if p.get(
                "console_project_id") else None, p.get("scope_differs_reason"), p["decided_by"],
            _dt(p.get("created_at"))))
    except psycopg.errors.UniqueViolation as exc:
        raise ResearchConflict("route_conflict", reason="route_active") from exc
    except psycopg.errors.ForeignKeyViolation as exc:
        raise ResearchGuardError("console_project_not_found", str(p.get("console_project_id"))
                                 ) from exc
    assert row is not None
    seq = _route_event(tx, rid, route_id, 0, "ROUTE", "PENDING", actor=p["decided_by"],
                       stamp=str(p.get("created_at") or ""))
    return {"applied": True, "seq": seq}


def _op_route_start(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """`PENDING`／`FAILED` → `RUNNING`（重試沿用同列）；同交易把游標寫成 `route／ROUTING／RUNNING`。
    已是 `RUNNING`＝跳過；其他狀態＝`route_conflict`。"""
    rid, route_id = _uid(p["research_id"]), _uid(p["route_id"])
    project = tx.lock_project(rid)
    row = tx.one(_SQL_ROUTE_LOCK, (route_id,))
    if row is None:
        raise ResearchGuardError("route_not_found", str(route_id))
    if row["status"] == "RUNNING":
        return {"applied": False}
    if row["status"] not in ("PENDING", "FAILED"):
        raise ResearchConflict("route_conflict", status=row["status"])
    tx.run(_SQL_UPDATE_ROUTE_STATUS, ("RUNNING", route_id))
    _route_event(tx, rid, route_id, 0, "ROUTE", "RUNNING", actor=p["actor"],
                 stamp=str(p.get("occurred_at") or ""))
    _set_cursor(tx, rid, project, ROUTE_FLOW_RUNNING, p["actor"], p.get("occurred_at"))
    return {"applied": True}


def _op_route_step(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """步驟列（先 `RUNNING`、副作用做完再改 `OK`／`FAILED`；DB 先於副作用）＋`research.route`。
    列已存在時只更新受控欄位（狀態、結束碼、尾端文字、結束時間）——重試失敗步驟沿用同列。"""
    rid, route_id, step_no = _uid(p["research_id"]), _uid(p["route_id"]), int(p["step_no"])
    tx.lock_project(rid)
    if p["step"] not in ROUTE_STEP_NAMES:
        raise ResearchGuardError("route_step", f"未知的分流步驟 {p['step']!r}")
    existing = tx.one(_SQL_STEP_LOCK, (route_id, step_no))
    finished = _dt(p.get("finished_at"))
    if existing is None:
        tx.one(_SQL_INSERT_STEP, (
            route_id, step_no, p["step"], p["status"], str(p.get("argv_redacted", "")),
            p.get("exit_code"), str(p.get("stdout_tail", ""))[-2000:],
            str(p.get("stderr_tail", ""))[-2000:], _dt(p.get("started_at")), finished))
        applied = True
    else:
        new = (p["status"], p.get("exit_code"), str(p.get("stdout_tail", ""))[-2000:],
               str(p.get("stderr_tail", ""))[-2000:])
        applied = new != (existing["status"], existing["exit_code"], existing["stdout_tail"],
                          existing["stderr_tail"])
        if applied:
            tx.run(_SQL_UPDATE_STEP, (*new, finished, route_id, step_no))
    seq = _route_event(tx, rid, route_id, step_no, p["step"], p["status"], actor=p["actor"],
                       stamp=str(p.get("finished_at") or p.get("started_at") or ""))
    return {"applied": applied, "seq": seq}


def _op_route_bind_impl(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """內環鍵建好之後寫 `impl_fsm_project`／`impl_state_dir`（失敗前這兩欄一律為 NULL）。"""
    route_id = _uid(p["route_id"])
    if tx.one(_SQL_ROUTE_LOCK, (route_id,)) is None:
        raise ResearchGuardError("route_not_found", str(route_id))
    tx.run(_SQL_UPDATE_ROUTE_IMPL, (p["impl_fsm_project"], p["impl_state_dir"], route_id))
    return {"applied": True}


def _op_route_finish(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """分流終態（`SUCCEEDED`／`FAILED`）＋游標＋`research.route`，同一交易。成功：游標
    `build／ROUTED／IDLE`、`failure_step` 清為 NULL、回填專案列的 `console_project_id`；失敗：游標
    `route／ROUTING／FAILED` 且 `flow_detail` 為失敗步驟名（D-105）。已是該終態＝跳過。"""
    rid, route_id = _uid(p["research_id"]), _uid(p["route_id"])
    project = tx.lock_project(rid)
    row = tx.one(_SQL_ROUTE_LOCK, (route_id,))
    if row is None:
        raise ResearchGuardError("route_not_found", str(route_id))
    status = p["status"]
    if status not in ("SUCCEEDED", "FAILED"):
        raise ResearchGuardError("route_status", f"終態只准 SUCCEEDED／FAILED：{status!r}")
    if row["status"] == status:
        return {"applied": False}
    failure = p.get("failure_step") if status == "FAILED" else None
    tx.run(_SQL_UPDATE_ROUTE_FINISH, (
        status, failure, _dt(p.get("finished_at")) or utc_now(),
        Jsonb(dict(p.get("published_docs") or {})), p.get("repo_url"), route_id))
    if status == "SUCCEEDED":
        if p.get("console_project_id"):
            try:
                tx.run(_SQL_UPDATE_PROJECT_CONSOLE, (_uid(p["console_project_id"]), rid))
            except psycopg.errors.UniqueViolation as exc:
                raise ResearchConflict("route_conflict", reason="console_project_bound") from exc
        flow = ROUTE_FLOW_DONE
    else:
        flow = {"step": "route", "phase": "ROUTING", "status": "FAILED",
                "detail": str(failure or "")}
    stamp = str(p.get("finished_at") or "")
    seq = _route_event(tx, rid, route_id, 0, "ROUTE", status, actor=p["actor"], stamp=stamp)
    _set_cursor(tx, rid, project, flow, p["actor"], p.get("occurred_at"))
    return {"applied": True, "seq": seq}


def _op_route_compensate(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """console-api 補償完 Console 專案列後的通知：只有 `FAILED` 的列才改 `COMPENSATED`（D-112）。
    游標不動；不做任何 FSM 或檔案動作。重放（列已是 `COMPENSATED` 且事件已寫）＝跳過。"""
    rid, route_id = _uid(p["research_id"]), _uid(p["route_id"])
    tx.lock_project(rid)
    row = tx.one(_SQL_ROUTE_LOCK, (route_id,))
    if row is None:
        raise ResearchGuardError("route_not_found", str(route_id))
    stamp = str(p.get("occurred_at") or "")
    ref = uuid.uuid5(uuid.NAMESPACE_URL, f"route:{route_id}:0:COMPENSATED:{stamp}")
    if row["status"] == "COMPENSATED" and tx.one(
            _SQL_EVENT_EXISTS, (rid, "research.route", "route", ref)) is not None:
        return {"applied": False}
    if row["status"] != "FAILED":
        raise ResearchConflict("route_conflict", status=row["status"])
    tx.run(_SQL_UPDATE_ROUTE_STATUS, ("COMPENSATED", route_id))
    seq = _route_event(tx, rid, route_id, 0, "ROUTE", "COMPENSATED", actor=p["actor"],
                       stamp=stamp, reason=str(p.get("reason", ""))[:500])
    return {"applied": True, "seq": seq}


def _op_route_reap(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """孤兒回收（Bridge 重啟時）：卡在 `PENDING`／`RUNNING` 的分流列＝上一個行程被中斷；把仍在
    `RUNNING` 的步驟列標 `FAILED`（`stderr_tail` 為 `interrupted`）、分流列標 `FAILED` 並寫游標
    `route／ROUTING／FAILED`，專案才不會因部分唯一索引永遠無法重試。"""
    rid, route_id = _uid(p["research_id"]), _uid(p["route_id"])
    project = tx.lock_project(rid)
    row = tx.one(_SQL_ROUTE_LOCK, (route_id,))
    if row is None or row["status"] not in ("PENDING", "RUNNING"):
        return {"applied": False}
    now = utc_now()
    opened = tx.rows(_SQL_OPEN_STEPS, (route_id,))
    for step in opened:
        tx.run(_SQL_UPDATE_STEP, ("FAILED", None, "", "interrupted", now, route_id,
                                  step["step_no"]))
        _route_event(tx, rid, route_id, int(step["step_no"]), step["step"], "FAILED",
                     actor=p["actor"], stamp=now.isoformat())
    last = tx.one(_SQL_LAST_STEP, (route_id,))
    failure = (opened[0]["step"] if opened else (last["step"] if last else "VALIDATE_TARGET"))
    tx.run(_SQL_UPDATE_ROUTE_FINISH, ("FAILED", failure, now, Jsonb({}), None, route_id))
    _route_event(tx, rid, route_id, 0, "ROUTE", "FAILED", actor=p["actor"],
                 stamp=now.isoformat())
    _set_cursor(tx, rid, project, {"step": "route", "phase": "ROUTING", "status": "FAILED",
                                   "detail": failure}, p["actor"], now)
    return {"applied": True, "failure_step": failure}


# ── P1 BR-D2：SCR、拆解、TCS 的操作（D-103／D-104／D-110／D-113／D-116）──────────────────────────
#: 同一研究專案內 kind=MINOR 且 status 為 OPEN／APPROVED／APPLIED 的 SCR 上限（D-104 保守計）。
SCR_MINOR_MAX = 2
SCR_LIVE_STATUSES = ("OPEN", "APPROVED", "APPLIED")
#: 已簽核或待簽核而可被 PRD 變更標 STALE 的拆解狀態。
DECOMP_STALEABLE = ("DRAFTED", "SCG_PASSED", "FROZEN", "SIGNED_OFF")
_SQL_SCR_LOCK = "SELECT * FROM {s}.research_scr WHERE id = %s FOR UPDATE"
_SQL_SCR_OPEN = ("SELECT id, scr_no, kind FROM {s}.research_scr WHERE research_id = %s AND "
                 "status = 'OPEN'")
_SQL_SCR_MINOR_USED = (
    "SELECT count(*) AS n FROM {s}.research_scr WHERE research_id = %s AND kind = 'MINOR' AND "
    "status IN ('OPEN', 'APPROVED', 'APPLIED')")
_SQL_SCR_NEXT = ("SELECT COALESCE(MAX(scr_no), 0) + 1 AS n FROM {s}.research_scr "
                 "WHERE research_id = %s")
_SQL_INSERT_SCR = (
    "INSERT INTO {s}.research_scr (id, research_id, scr_no, kind, source_kind, reason, "
    "reason_class, affected_sections, status, prd_from_version_no, successor_research_id, "
    "requested_by, requested_at, decided_by, decided_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, "
    "%s, %s, %s, %s, COALESCE(%s, NOW()), %s, %s)")
_SQL_UPDATE_SCR = (
    "UPDATE {s}.research_scr SET status = %s, prd_to_version_no = %s, impl_fsm_actions = %s, "
    "decided_by = %s, decided_at = %s WHERE id = %s")
_SQL_STALE_DECOMPS = (
    "UPDATE {s}.research_decompositions SET status = 'STALE' WHERE research_id = %s AND "
    "status IN ('DRAFTED', 'SCG_PASSED', 'FROZEN', 'SIGNED_OFF') AND "
    "prd_sha256 IS DISTINCT FROM %s")
_SQL_DECOMP_LOCK = "SELECT * FROM {s}.research_decompositions WHERE id = %s FOR UPDATE"
_SQL_INSERT_DECOMP = (
    "INSERT INTO {s}.research_decompositions (id, research_id, path, draft_id, tcs_rel_path, "
    "tcs_sha256, prd_sha256, tasks_count, gate_rejection, status, created_by, created_at) "
    "VALUES (%s, %s, 'C', %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))")
_SQL_SIGNOFF_DECOMP = ("UPDATE {s}.research_decompositions SET status = 'SIGNED_OFF', "
                       "import_record_id = %s WHERE id = %s")
_SQL_TCS_DECOMP = ("UPDATE {s}.research_decompositions SET tcs_rel_path = %s, tcs_sha256 = %s "
                   "WHERE id = %s")


def _scr_event(tx: ResearchTx, rid: Any, scr_id: Any, scr_no: int, kind: str, status: str, *,
               actor: str, stamp: str = "") -> int | None:
    ref = uuid.uuid5(uuid.NAMESPACE_URL, f"scr:{scr_id}:{status}:{stamp}")
    if tx.one(_SQL_EVENT_EXISTS, (rid, "research.scr", "scr", ref)) is not None:
        return None
    return tx.append_event(rid, "research.scr", {"scrNo": scr_no, "kind": kind, "status": status},
                           actor=actor, ref_kind="scr", ref_id=ref)


def _snapshot_event(tx: ResearchTx, rid: Any, actor: str, ref_key: str) -> int | None:
    """拆解與 TCS 沒有自己的事件型別：以 `research.step` 游標快照表達（IFACE §1.4）。"""
    row = tx.lock_project(rid)
    ref = uuid.uuid5(uuid.NAMESPACE_URL, f"snapshot:{ref_key}")
    if tx.one(_SQL_EVENT_EXISTS, (rid, "research.step", "snapshot", ref)) is not None:
        return None
    return tx.append_event(rid, "research.step", step_payload(_flow_of(row)), actor=actor,
                           ref_kind="snapshot", ref_id=ref)


def _op_scr_open(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """寫 `research_scr`（OPEN）＋`research.scr`＋（選填）游標。同 `scr_id` 已存在＝跳過；同專案已有
    OPEN＝`scr_open`；MINOR 在 OPEN／APPROVED／APPLIED 已有 `SCR_MINOR_MAX` 筆＝`scr_limit`。"""
    rid, scr_id = _uid(p["research_id"]), _uid(p["scr_id"])
    row = tx.lock_project(rid)
    existing = tx.one(_SQL_SCR_LOCK, (scr_id,))
    if existing is not None:
        return {"applied": False, "scr_no": existing["scr_no"]}
    opened = tx.one(_SQL_SCR_OPEN, (rid,))
    if opened is not None:
        raise ResearchConflict("scr_open", scr_no=opened["scr_no"], kind=opened["kind"])
    if p["kind"] == "MINOR":
        used = int((tx.one(_SQL_SCR_MINOR_USED, (rid,)) or {"n": 0})["n"])
        if used >= SCR_MINOR_MAX:
            raise ResearchConflict("scr_limit", limit=SCR_MINOR_MAX, used=used, hint="改 MAJOR")
    scr_no = int((tx.one(_SQL_SCR_NEXT, (rid,)) or {"n": 1})["n"])
    head = tx.one(_SQL_HEAD_PRD, (rid,))
    tx.run(_SQL_INSERT_SCR, (
        scr_id, rid, scr_no, p["kind"], p["source_kind"], p["reason"],
        p.get("reason_class", "OTHER"), list(p.get("affected_sections") or []), "OPEN",
        int(head["head"]) if head and head["head"] else None, None, p["requested_by"],
        _dt(p.get("requested_at")), None, None))
    seq = _scr_event(tx, rid, scr_id, scr_no, p["kind"], "OPEN", actor=p["requested_by"])
    if p.get("flow"):
        _set_cursor(tx, rid, row, p["flow"], p["requested_by"], p.get("requested_at"))
    return {"applied": True, "scr_no": scr_no, "seq": seq}


def _op_scr_major(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """MAJOR：一筆直接是 `SUPERSEDED` 的列（`successor_research_id` 為新專案；新專案已先建好）＋
    `research.scr`＋舊專案游標只改 `flow_detail`（「已被 RP-NNNN 取代」；step／phase 不動）。"""
    rid, scr_id = _uid(p["research_id"]), _uid(p["scr_id"])
    row = tx.lock_project(rid)
    existing = tx.one(_SQL_SCR_LOCK, (scr_id,))
    if existing is not None:
        return {"applied": False, "scr_no": existing["scr_no"]}
    opened = tx.one(_SQL_SCR_OPEN, (rid,))
    if opened is not None:
        raise ResearchConflict("scr_open", scr_no=opened["scr_no"], kind=opened["kind"])
    scr_no = int((tx.one(_SQL_SCR_NEXT, (rid,)) or {"n": 1})["n"])
    head = tx.one(_SQL_HEAD_PRD, (rid,))
    now = _dt(p.get("requested_at")) or utc_now()
    try:
        tx.run(_SQL_INSERT_SCR, (
            scr_id, rid, scr_no, "MAJOR", p["source_kind"], p["reason"],
            p.get("reason_class", "OTHER"), list(p.get("affected_sections") or []), "SUPERSEDED",
            int(head["head"]) if head and head["head"] else None, _uid(p["successor_research_id"]),
            p["requested_by"], now, p["requested_by"], now))
    except psycopg.errors.ForeignKeyViolation as exc:
        raise ResearchGuardError("successor_not_found", str(p["successor_research_id"])) from exc
    seq = _scr_event(tx, rid, scr_id, scr_no, "MAJOR", "SUPERSEDED", actor=p["requested_by"])
    flow = {**_flow_of(row), "detail": str(p.get("detail", ""))[:300]}
    _set_cursor(tx, rid, row, flow, p["requested_by"], now)
    return {"applied": True, "scr_no": scr_no, "seq": seq}


def _stale_decompositions(tx: ResearchTx, rid: Any, current_sha: str | None) -> int:
    return tx.run(_SQL_STALE_DECOMPS, (rid, current_sha))


def _op_scr_update(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """SCR 列的受控更新（狀態、`prd_to_version_no`、`impl_fsm_actions`、決定人時間；皆在 V16 允許
    清單）。狀態有變才發 `research.scr`；`stale_prd_sha256` 有給時把摘要不同的拆解同交易標 STALE；
    `flow` 有給時同交易寫游標。值與現況相同＝跳過（重放冪等）。"""
    rid, scr_id = _uid(p["research_id"]), _uid(p["scr_id"])
    row = tx.lock_project(rid)
    current = tx.one(_SQL_SCR_LOCK, (scr_id,))
    if current is None or str(current["research_id"]) != str(rid):
        raise ResearchGuardError("scr_not_found", str(scr_id))
    status = p.get("status", current["status"])
    new = (status, p.get("prd_to_version_no", current["prd_to_version_no"]),
           Jsonb(list(p["impl_fsm_actions"])) if "impl_fsm_actions" in p else Jsonb(
               current["impl_fsm_actions"]),
           p.get("decided_by", current["decided_by"]),
           _dt(p["decided_at"]) if p.get("decided_at") else current["decided_at"], scr_id)
    changed = (status != current["status"]
               or new[1] != current["prd_to_version_no"]
               or "impl_fsm_actions" in p and list(p["impl_fsm_actions"]) != list(
                   current["impl_fsm_actions"] or [])
               or new[3] != current["decided_by"] or new[4] != current["decided_at"])
    seq = None
    if changed:
        tx.run(_SQL_UPDATE_SCR, new)
        if status != current["status"]:
            seq = _scr_event(tx, rid, scr_id, int(current["scr_no"]), current["kind"], status,
                             actor=p["actor"], stamp=str(p.get("decided_at") or ""))
    staled = 0
    if p.get("stale_prd_sha256"):
        staled = _stale_decompositions(tx, rid, str(p["stale_prd_sha256"]))
    if p.get("flow"):
        _set_cursor(tx, rid, row, p["flow"], p["actor"], p.get("decided_at"))
    return {"applied": changed, "seq": seq, "staled": staled}


def _op_decomp_create(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """拆解列（DRAFTED 或 REJECTED）＋（成功時）`TASK_DECOMPOSITION` 登記列（版本遞增）＋游標快照。
    重拆＝新列、舊列不動（D-110：承接 `tcs_*` 由呼叫端帶入）。同 id 已存在＝跳過。"""
    rid, did = _uid(p["research_id"]), _uid(p["decomposition_id"])
    tx.lock_project(rid)
    if tx.one(_SQL_DECOMP_LOCK, (did,)) is not None:
        return {"applied": False}
    tx.run(_SQL_INSERT_DECOMP, (
        did, rid, p.get("draft_id"), p.get("tcs_rel_path"), p.get("tcs_sha256"),
        p.get("prd_sha256"), int(p.get("tasks_count", 0)), p.get("gate_rejection"),
        p.get("status", "DRAFTED"), p["created_by"], _dt(p.get("created_at"))))
    art = p.get("artifact")
    if art:
        _register_artifact(tx, rid, kind="TASK_DECOMPOSITION", version=int(art["version"]),
                           rel_path=art["rel_path"], sha256=art["sha256"], size=int(art["bytes"]),
                           origin="BRIDGE", content=art["content"], stage_run_id=None,
                           created_by=p["created_by"])
    seq = _snapshot_event(tx, rid, p["created_by"], f"decomp:{did}:created")
    return {"applied": True, "seq": seq}


def _op_decomp_signoff(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """簽核（D-113 單一寫入時點）：`status=SIGNED_OFF`＋`import_record_id`（同交易）＋新版
    `TASK_DECOMPOSITION` 登記列（含 waivers 與簽核資訊）＋游標快照。已簽核且同一 import 記錄＝跳過；
    列非 DRAFTED／SCG_PASSED＝`fsm_state_conflict`（`details.status`）。"""
    rid, did = _uid(p["research_id"]), _uid(p["decomposition_id"])
    tx.lock_project(rid)
    row = tx.one(_SQL_DECOMP_LOCK, (did,))
    if row is None or str(row["research_id"]) != str(rid):
        raise ResearchGuardError("decomposition_not_found", str(did))
    if row["status"] == "SIGNED_OFF" and str(row["import_record_id"]) == str(
            p["import_record_id"]):
        return {"applied": False}
    if row["status"] not in ("DRAFTED", "SCG_PASSED"):
        raise ResearchConflict("fsm_state_conflict", status=row["status"])
    try:
        tx.run(_SQL_SIGNOFF_DECOMP, (_uid(p["import_record_id"]), did))
    except psycopg.errors.ForeignKeyViolation as exc:
        raise ResearchGuardError("import_record_not_found", str(p["import_record_id"])) from exc
    art = p["artifact"]
    _register_artifact(tx, rid, kind="TASK_DECOMPOSITION", version=int(art["version"]),
                       rel_path=art["rel_path"], sha256=art["sha256"], size=int(art["bytes"]),
                       origin="BRIDGE", content=art["content"], stage_run_id=None,
                       created_by=p["approver"])
    seq = _snapshot_event(tx, rid, p["approver"], f"decomp:{did}:signoff")
    return {"applied": True, "seq": seq}


def _op_decomp_stale(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """PRD 凍結摘要改變後，把摘要不同的拆解標 STALE（`prd_sha256` 不動、簽核事實保留）。"""
    rid = _uid(p["research_id"])
    tx.lock_project(rid)
    return {"applied": True, "staled": _stale_decompositions(tx, rid, str(p["prd_sha256"]))}


def _op_tcs_publish(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """TCS 草擬通過後的登記（D-109／D-110）：`TCS` 登記列（內容相同者不重複登記）＋最近一筆拆解列的
    `tcs_rel_path`／`tcs_sha256`＋游標 `build／TCS_PENDING`＋事件，同一交易。"""
    rid, did = _uid(p["research_id"]), _uid(p["decomposition_id"])
    row = tx.lock_project(rid)
    decomp = tx.one(_SQL_DECOMP_LOCK, (did,))
    if decomp is None or str(decomp["research_id"]) != str(rid):
        raise ResearchGuardError("decomposition_not_found", str(did))
    art = p["artifact"]
    same = tx.one("SELECT 1 AS hit FROM {s}.research_artifacts WHERE research_id = %s AND "
                  "kind = 'TCS' AND sha256 = %s", (rid, art["sha256"]))
    if same is None:
        _register_artifact(tx, rid, kind="TCS", version=int(art["version"]),
                           rel_path=art["rel_path"], sha256=art["sha256"], size=int(art["bytes"]),
                           origin="AGENT", content=None, stage_run_id=p.get("stage_run_id"),
                           created_by=p["actor"])
    tx.run(_SQL_TCS_DECOMP, (art["rel_path"], art["sha256"], did))
    if p.get("flow"):
        _set_cursor(tx, rid, row, p["flow"], p["actor"], p.get("occurred_at"))
    seq = _snapshot_event(tx, rid, p["actor"], f"tcs:{did}:{art['sha256']}")
    return {"applied": True, "seq": seq}


def _op_tcs_correct_cursor(tx: ResearchTx, p: Mapping[str, Any]) -> dict[str, Any]:
    """D-125：`build／TCS_PENDING` 且內環 Stage-2 已凍結時，同交易把游標校正為 `build／ROUTED／IDLE`
    並記 `research.step`（payload 另帶選填鍵 `reason=tcs_frozen_correction`）。游標已不是
    `TCS_PENDING`＝跳過（冪等）。"""
    rid = _uid(p["research_id"])
    row = tx.lock_project(rid)
    if (row["flow_step"], row["flow_phase"]) != ("build", "TCS_PENDING"):
        return {"applied": False}
    flow = {"step": "build", "phase": "ROUTED", "status": "IDLE", "detail": ""}
    ref = uuid.uuid5(uuid.NAMESPACE_URL, f"tcs_frozen_correction:{rid}:{p['stage2_digest']}")
    tx.run(_SQL_UPDATE_CURSOR, (flow["step"], flow["phase"], flow["status"], flow["detail"], rid))
    seq = tx.append_event(rid, "research.step",
                          {**step_payload(flow), "reason": "tcs_frozen_correction"},
                          actor=p["actor"], step="build", ref_kind="tcs_frozen_correction",
                          ref_id=ref)
    return {"applied": True, "seq": seq, "reason": "tcs_frozen_correction"}


#: P1 BR-D2 的操作登記表（與 `ROUTE_OPS` 同理：不新增公開寫入方法，只經 `DurableWriter.persist`
#: 與 `ResearchDb.apply(kind, …)` 呼叫）。
P1_OPS: dict[str, Callable[[ResearchTx, Mapping[str, Any]], dict[str, Any]]] = {
    "scr.open": _op_scr_open,
    "scr.major": _op_scr_major,
    "scr.update": _op_scr_update,
    "decomp.create": _op_decomp_create,
    "decomp.signoff": _op_decomp_signoff,
    "decomp.stale": _op_decomp_stale,
    "tcs.publish": _op_tcs_publish,
    "tcs.correct_cursor": _op_tcs_correct_cursor,
}


#: P1 分流的操作登記表。刻意與 `OPS`／`METHOD_KINDS` 分開：後兩者與 P0 的「公開寫入方法一一對應、
#: 逐方法實跑」鎖綁定（`tests/test_research_db.py`），P1 的分流操作只經 `DurableWriter.persist`
#: 與 `ResearchDb.apply(kind, …)` 呼叫，不新增公開寫入方法。
ROUTE_OPS: dict[str, Callable[[ResearchTx, Mapping[str, Any]], dict[str, Any]]] = {
    "route.create": _op_route_create,
    "route.start": _op_route_start,
    "route.step": _op_route_step,
    "route.bind_impl": _op_route_bind_impl,
    "route.finish": _op_route_finish,
    "route.compensate": _op_route_compensate,
    "route.reap": _op_route_reap,
}


Op = Callable[[ResearchTx, Mapping[str, Any]], dict[str, Any]]
#: 操作登記表（kind → 函式）。outbox 記錄的 `kind` 就是這裡的鍵。
OPS: dict[str, Op] = {
    "project.allocate_rp_no": _op_allocate_rp_no,
    "project.create": _op_project_create,
    "project.cursor": _op_set_cursor,
    "project.archive": _op_archive_project,
    "project.restore": _op_restore_project,
    "project.abandon_key": _op_abandon_fsm_key,
    "gate.decision": _op_gate_decision,
    "prd.save": _op_save_prd,
    "stage_run.insert": _op_insert_stage_run,
    "stage_run.update": _op_update_stage_run,
    "artifact.insert": _op_insert_artifact,
    "review.round": _op_insert_review_round,
    "defect.update": _op_update_defect,
    "source.insert": _op_insert_source,
    "source.upgrade": _op_upgrade_source,
    "fetch.insert": _op_insert_fetch,
    "evidence.record": _op_record_evidence,
    "event.append": _op_append_event,
    "allowlist.add": _op_add_allowlist,
    "allowlist.set_enabled": _op_set_allowlist_enabled,
}
#: `ResearchDb` 的公開寫入方法 → 操作種類（與 `OPS` 一一對應；AT-960-2-4／6-7 逐一實跑）。
METHOD_KINDS: dict[str, str] = {
    "allocate_rp_no": "project.allocate_rp_no",
    "create_project": "project.create", "set_cursor": "project.cursor",
    "archive_project": "project.archive", "restore_project": "project.restore",
    "abandon_fsm_key": "project.abandon_key", "record_gate_decision": "gate.decision",
    "save_prd": "prd.save", "insert_stage_run": "stage_run.insert",
    "update_stage_run": "stage_run.update", "insert_artifact": "artifact.insert",
    "insert_review_round": "review.round", "update_defect": "defect.update",
    "insert_source": "source.insert", "upgrade_source_verification": "source.upgrade",
    "insert_fetch": "fetch.insert", "record_evidence": "evidence.record",
    "append_event": "event.append", "add_allowlist_entry": "allowlist.add",
    "set_allowlist_enabled": "allowlist.set_enabled"}
WRITE_METHODS: tuple[str, ...] = tuple(METHOD_KINDS)


class ResearchDb:
    """研究表寫入器。每個公開寫入方法＝一個 DB 交易；任何連線或執行錯誤都拋 `ResearchDbError`。"""

    def __init__(self, dsn: str | None, schema: str = "console", *,
                 connect: Callable[[], Any] | None = None, connect_timeout: int = 3,
                 statement_hook: StatementHook | None = None) -> None:
        if not _SCHEMA_RE.fullmatch(schema):
            raise ValueError(f"不合規的 schema 名：{schema!r}")
        if connect is None and not dsn:
            raise ValueError("ResearchDb 需要 DSN 或 connect 工廠")
        self._ident = f'"{schema}"'
        self._connect = connect or (lambda: psycopg.connect(dsn, connect_timeout=connect_timeout))
        self._hook = statement_hook

    @contextmanager
    def transaction(self, *, read_only: bool = False) -> Iterator[ResearchTx]:
        try:
            conn = self._connect()
        except psycopg.Error as exc:
            raise ResearchDbError("connect", str(exc), sqlstate=exc.sqlstate) from exc
        try:
            with conn:
                if read_only:
                    conn.read_only = True
                yield ResearchTx(conn, self._ident, self._hook)
        except psycopg.Error as exc:
            raise ResearchDbError("execute", str(exc), sqlstate=exc.sqlstate) from exc

    def apply(self, kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """跑一個登記的操作（一個交易）；outbox 重放與公開寫入方法都走這裡。"""
        fn = OPS.get(kind) or ROUTE_OPS.get(kind) or P1_OPS.get(kind)
        if fn is None:
            raise ResearchGuardError("unknown_op", f"未登記的操作：{kind!r}")
        with self.transaction() as tx:
            return fn(tx, payload)

    # ── 公開寫入方法（payload 欄位見對應的 `_op_*` 函式）─────────────────────────────────────
    def allocate_rp_no(self, **p: Any) -> dict[str, Any]:
        return self.apply("project.allocate_rp_no", p)

    def create_project(self, **p: Any) -> dict[str, Any]:
        return self.apply("project.create", p)

    def set_cursor(self, **p: Any) -> dict[str, Any]:
        return self.apply("project.cursor", p)

    def archive_project(self, **p: Any) -> dict[str, Any]:
        return self.apply("project.archive", p)

    def restore_project(self, **p: Any) -> dict[str, Any]:
        return self.apply("project.restore", p)

    def abandon_fsm_key(self, **p: Any) -> dict[str, Any]:
        return self.apply("project.abandon_key", p)

    def record_gate_decision(self, **p: Any) -> dict[str, Any]:
        return self.apply("gate.decision", p)

    def save_prd(self, **p: Any) -> dict[str, Any]:
        return self.apply("prd.save", p)

    def insert_stage_run(self, **p: Any) -> dict[str, Any]:
        return self.apply("stage_run.insert", p)

    def update_stage_run(self, **p: Any) -> dict[str, Any]:
        return self.apply("stage_run.update", p)

    def insert_artifact(self, **p: Any) -> dict[str, Any]:
        return self.apply("artifact.insert", p)

    def insert_review_round(self, **p: Any) -> dict[str, Any]:
        return self.apply("review.round", p)

    def update_defect(self, **p: Any) -> dict[str, Any]:
        return self.apply("defect.update", p)

    def insert_source(self, **p: Any) -> dict[str, Any]:
        return self.apply("source.insert", p)

    def upgrade_source_verification(self, **p: Any) -> dict[str, Any]:
        return self.apply("source.upgrade", p)

    def insert_fetch(self, **p: Any) -> dict[str, Any]:
        return self.apply("fetch.insert", p)

    def record_evidence(self, **p: Any) -> dict[str, Any]:
        return self.apply("evidence.record", p)

    def append_event(self, **p: Any) -> dict[str, Any]:
        return self.apply("event.append", p)

    def add_allowlist_entry(self, **p: Any) -> dict[str, Any]:
        return self.apply("allowlist.add", p)

    def set_allowlist_enabled(self, **p: Any) -> dict[str, Any]:
        return self.apply("allowlist.set_enabled", p)

    # ── 唯讀查詢（唯讀交易；任何寫入形態語句會被 PostgreSQL 拒絕）─────────────────────────────
    def query(self, text: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        """一條 SELECT（或 WITH … SELECT）；`{s}` 是 schema 佔位。回資料列（dict）。"""
        if not re.match(r"^\s*(SELECT|WITH)\b", text, re.IGNORECASE):
            raise ResearchGuardError("query_not_select", "query 只收 SELECT")
        with self.transaction(read_only=True) as tx:
            return tx.rows(text, params)

    def ping(self) -> bool:
        return bool(self.query("SELECT 1 AS ok"))

    def get_project(self, research_id: Any) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM {s}.research_projects WHERE id = %s",
                          (_uid(research_id),))
        return rows[0] if rows else None

    def find_active_project(self, slug: str) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM {s}.research_projects WHERE slug = %s AND "
                          "archived_at IS NULL", (slug,))
        return rows[0] if rows else None

    def head_prd(self, research_id: Any) -> dict[str, Any] | None:
        rows = self.query(
            "SELECT version_no, semver, kind, author_kind, author, sha256, bytes, rel_path "
            "FROM {s}.research_prd_versions WHERE research_id = %s "
            "ORDER BY version_no DESC LIMIT 1", (_uid(research_id),))
        return rows[0] if rows else None

    def review_state(self, research_id: Any) -> dict[str, Any]:
        """已完成評估的輪數與最近一輪（前置條件判斷用）。"""
        rows = self.query(
            "SELECT round_no, passed, verdict, escalated, fsm_gate_result, trigger_kind, "
            "prd_version_no FROM {s}.research_review_rounds WHERE research_id = %s "
            "ORDER BY round_no", (_uid(research_id),))
        return {"completed": len(rows), "last": rows[-1] if rows else None}

    def active_stage_run(self, research_id: Any) -> dict[str, Any] | None:
        rows = self.query(
            "SELECT id, stage, round_no, attempt, status FROM {s}.research_stage_runs "
            "WHERE research_id = %s AND status IN ('QUEUED', 'RUNNING')", (_uid(research_id),))
        return rows[0] if rows else None

    def count_active_stage_runs(self) -> int:
        """全站進行中（QUEUED／RUNNING）的 stage run 數；狀態集合與 `active_stage_run` 相同，
        供並行上限（`BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS`）判斷。"""
        rows = self.query("SELECT count(*) AS n FROM {s}.research_stage_runs "
                          "WHERE status IN ('QUEUED', 'RUNNING')")
        return int(rows[0]["n"])

    # ── P1 分流的唯讀查詢 ─────────────────────────────────────────────────────────────────
    def get_route(self, route_id: Any) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM {s}.research_route_decisions WHERE id = %s",
                          (_uid(route_id),))
        return rows[0] if rows else None

    def latest_route(self, research_id: Any) -> dict[str, Any] | None:
        """該研究專案最近一筆分流列（任何狀態；`created_at` 新者優先）。"""
        rows = self.query(
            "SELECT * FROM {s}.research_route_decisions WHERE research_id = %s "
            "ORDER BY created_at DESC LIMIT 1", (_uid(research_id),))
        return rows[0] if rows else None

    def active_route(self, research_id: Any) -> dict[str, Any] | None:
        """PENDING／RUNNING／SUCCEEDED 的分流列（部分唯一索引保證至多一筆）。"""
        rows = self.query(
            "SELECT * FROM {s}.research_route_decisions WHERE research_id = %s AND status IN "
            "('PENDING', 'RUNNING', 'SUCCEEDED')", (_uid(research_id),))
        return rows[0] if rows else None

    def route_steps(self, route_id: Any) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM {s}.research_route_steps WHERE route_id = %s "
                          "ORDER BY step_no", (_uid(route_id),))

    def unfinished_routes(self) -> list[dict[str, Any]]:
        """全站卡在 PENDING／RUNNING 的分流列（孤兒回收用）。"""
        return self.query("SELECT id, research_id, status FROM {s}.research_route_decisions "
                          "WHERE status IN ('PENDING', 'RUNNING') ORDER BY created_at")

    # ── P1 BR-D2 的唯讀查詢 ───────────────────────────────────────────────────────────────
    def open_scr(self, research_id: Any) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM {s}.research_scr WHERE research_id = %s AND "
                          "status = 'OPEN'", (_uid(research_id),))
        return rows[0] if rows else None

    def get_scr(self, research_id: Any, scr_no: int) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM {s}.research_scr WHERE research_id = %s AND scr_no = %s",
                          (_uid(research_id), scr_no))
        return rows[0] if rows else None

    def list_scr(self, research_id: Any) -> list[dict[str, Any]]:
        return self.query("SELECT * FROM {s}.research_scr WHERE research_id = %s ORDER BY scr_no",
                          (_uid(research_id),))

    def latest_decomposition(self, research_id: Any) -> dict[str, Any] | None:
        """最近一筆拆解列（任何狀態；`created_at` 新者優先）。"""
        rows = self.query("SELECT * FROM {s}.research_decompositions WHERE research_id = %s "
                          "ORDER BY created_at DESC, id DESC LIMIT 1", (_uid(research_id),))
        return rows[0] if rows else None

    def get_decomposition(self, decomposition_id: Any) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM {s}.research_decompositions WHERE id = %s",
                          (_uid(decomposition_id),))
        return rows[0] if rows else None

    def latest_artifact(self, research_id: Any, kind: str) -> dict[str, Any] | None:
        rows = self.query(
            "SELECT version, rel_path, sha256, bytes, content FROM {s}.research_artifacts "
            "WHERE research_id = %s AND kind = %s ORDER BY version DESC LIMIT 1",
            (_uid(research_id), kind))
        return rows[0] if rows else None

    def latest_artifact_version(self, research_id: Any, kind: str) -> int:
        rows = self.query("SELECT COALESCE(MAX(version), 0) AS head FROM "
                          "{s}.research_artifacts WHERE research_id = %s AND kind = %s",
                          (_uid(research_id), kind))
        return int(rows[0]["head"])

    def gate0_digests(self, research_id: Any) -> dict[str, str] | None:
        """最近一筆 Gate 0 核准的凍結摘要（路徑 → 十六進位 sha256；沒有核准回 None）。"""
        rows = self.query(
            "SELECT id, frozen_digests FROM {s}.research_gate_decisions WHERE research_id = %s "
            "AND gate = 'GATE0' AND decision = 'APPROVED' ORDER BY decided_at DESC LIMIT 1",
            (_uid(research_id),))
        if not rows:
            return None
        return {str(k): str(v).removeprefix("sha256:")
                for k, v in (rows[0]["frozen_digests"] or {}).items()}

    def gate0_decision_id(self, research_id: Any) -> str | None:
        rows = self.query(
            "SELECT id FROM {s}.research_gate_decisions WHERE research_id = %s AND gate = 'GATE0' "
            "AND decision = 'APPROVED' ORDER BY decided_at DESC LIMIT 1", (_uid(research_id),))
        return str(rows[0]["id"]) if rows else None

    def list_events(self, research_id: Any, *, after_seq: int = 0,
                    limit: int = 100) -> list[dict[str, Any]]:
        return self.query(
            "SELECT seq, event_type, step, actor, ref_kind, ref_id, payload, occurred_at "
            "FROM {s}.research_events WHERE research_id = %s AND seq > %s ORDER BY seq LIMIT %s",
            (_uid(research_id), after_seq, min(max(limit, 1), 501)))

    def list_allowlist(self) -> list[dict[str, Any]]:
        return self.query(
            "SELECT id, list_kind, host, layer, purpose, tos_note, min_interval_seconds, "
            "enabled, tos_acknowledged, added_by, added_at, disabled_by, disabled_at "
            "FROM {s}.research_allowlist_entries ORDER BY list_kind, host")
