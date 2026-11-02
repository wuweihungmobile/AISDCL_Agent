"""研究寫入器與 outbox（`app/research/db.py`、`outbox.py`）。

TCS-ResearchToPRD-P0-20261102：AT-960-2-4（fail-loud）、2-5（斷線 BLOCKED_DB 與 outbox 重放）、
2-6（持久化順序與中斷）、6-7（受控可更新表）。DB 型測試用 `tests/research_pg_support.py` 的
拋棄式資料庫（`BRIDGE_TEST_DSN` 未設＝`pytest.skip("TOOL-ABSENCE: BRIDGE_TEST_DSN 不存在")`）。
2-4 的連線替身測試與 AST 掃描不需要資料庫，永遠跑。
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
import pytest

from app import fsutil
from app.research import db as db_module
from app.research import layout
from app.research.db import (
    APPEND_ONLY_TABLES,
    CONTROLLED_UPDATE_COLUMNS,
    WRITE_METHODS,
    ResearchConflict,
    ResearchDb,
    ResearchDbError,
    ResearchGuardError,
)
from app.research.outbox import DbBlocked, DurableWriter, FileRef, FileWrite, Op, Outbox
from tests.research_pg_support import ThrowawayDb, make_research_db

APP_DIR = Path(db_module.__file__).resolve().parents[1]
RESEARCH_DIR = Path(db_module.__file__).resolve().parent
ISO = "2026-11-02T01:02:03+00:00"
ALICE, ADMIN = "alice@example.com", "admin@example.com"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Ids:
    research: str = field(default_factory=lambda: str(uuid.uuid4()))
    run: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = field(default_factory=lambda: str(uuid.uuid4()))
    round: str = field(default_factory=lambda: str(uuid.uuid4()))
    defect: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision: str = field(default_factory=lambda: str(uuid.uuid4()))
    abandon: str = field(default_factory=lambda: str(uuid.uuid4()))
    entry: str = field(default_factory=lambda: str(uuid.uuid4()))


def project_payload(ids: Ids, ws: str = "/ws/demo", scope_sha: str | None = None) -> dict[str, Any]:
    return dict(
        research_id=ids.research, slug="demo", title="Demo", topic="一個研究議題",
        scope={"layers": {"academic": True}}, workspace_path=ws, fsm_project="research-demo",
        fsm_state_dir=f"{ws}/build/reports/fsm", created_by=ALICE,
        issue_scope={"rel_path": layout.ISSUE_SCOPE_REL, "sha256": scope_sha or sha("scope"),
                     "bytes": 5})


def sample_calls(ids: Ids) -> list[tuple[str, dict[str, Any]]]:
    """每個公開寫入方法各一組合法呼叫，依相依順序（每個都應 `applied`）。"""
    rid, prd = ids.research, "# PRD v0.1\n見 [E-001]\n"
    items = json.dumps({"schema_rev": 1, "items": []})
    flow = {"step": "studio", "phase": "RESEARCHING", "status": "RUNNING", "detail": ""}
    return [
        ("allocate_rp_no", {}),
        ("create_project", project_payload(ids)),
        ("set_cursor", dict(research_id=rid, actor="bridge", flow=flow)),
        ("insert_stage_run", dict(
            research_id=rid, stage_run_id=ids.run, stage="RESEARCH", requested_by=ALICE,
            status="RUNNING", playbook_sha256=sha("playbook"), config_sha256=sha("config"),
            prompt_manifest=[{"role": "research"}], allowlist_snapshot=["arxiv.org"])),
        ("update_stage_run", dict(stage_run_id=ids.run, status="SUCCEEDED", tokens_used=42,
                                  exit_reason="", finished_at=ISO, actor="bridge")),
        ("insert_artifact", dict(
            research_id=rid, kind="EVIDENCE_MATRIX", version=1,
            rel_path="00_research/evidence_matrix.md", sha256=sha("matrix"), bytes=6,
            origin="BRIDGE", created_by="bridge")),
        ("save_prd", dict(
            research_id=rid, version_no=1, author_kind="HUMAN", author=ALICE, content=prd,
            rel_path="01_specs/PRD-v0.1.0-draft.md", sha256=sha(prd), bytes=len(prd.encode()),
            change_summary="首版",
            flow={"step": "studio", "phase": "DRAFTING", "status": "IDLE", "detail": ""})),
        ("insert_source", dict(research_id=rid, actor="bridge", fetch_outcome="OK", source={
            "id": ids.source, "source_no": "S-001", "layer": "ACADEMIC", "tier": "T1",
            "verification": "V1", "anchor_kind": "URL", "url": "https://arxiv.org/abs/2401.00001",
            "title": "A paper"})),
        ("upgrade_source_verification", dict(source_id=ids.source, verification="V2",
                                             actor="bridge")),
        ("insert_fetch", dict(research_id=rid, fetch={
            "source_id": ids.source, "stage_run_id": ids.run, "layer": "ACADEMIC",
            "fetch_method": "API", "observed_by": "BRIDGE", "host": "arxiv.org",
            "url": "https://arxiv.org/abs/2401.00001", "outcome": "OK", "http_status": 200})),
        ("record_evidence", dict(
            research_id=rid, matrix_version=1, actor="bridge", stage_run_id=ids.run,
            artifact={"rel_path": "00_research/evidence_items.json", "sha256": sha(items),
                      "bytes": len(items.encode()), "content": items, "created_by": "bridge"},
            items=[{"evidence_no": "E-001", "source_no": "S-001", "claim": "一個論點",
                    "f1_mechanism": "機制", "f2_evidence": "證據", "f3_critique": "批判",
                    "f5_applicability": {"技術可行": "A"}, "f6_limits": "限制",
                    "f7_verification": "V2", "strength": "MEDIUM"}])),
        ("insert_review_round", dict(
            research_id=rid, actor="bridge",
            round={"id": ids.round, "round_no": 1, "prd_version_no": 1, "trigger_kind": "AUTO",
                   "precheck_passed": True, "weighted_score": "79.90", "min_dimension_score": 70,
                   "passed": False, "verdict": "REVISE", "fsm_gate_result": "FAIL",
                   "fsm_retry_count": 1, "stage_run_id": ids.run, "started_at": ISO,
                   "finished_at": "2026-11-02T01:03:03+00:00"},
            scores=[{"dimension": "ARCHITECTURE", "score": 78, "agent_id": "sd-architect",
                     "agent_yaml_path": "agent/core/05.sd-architect-zh.yaml",
                     "agent_yaml_sha256": sha("agent"), "persona_sha256": sha("persona"),
                     "raw_rel_path": "02_governance/review-1-architecture.json",
                     "raw_sha256": sha("raw")}],
            defects=[{"id": ids.defect, "defect_no": "D-1-001", "dimension": "QA",
                      "severity": "P2", "code": "AC_UNTESTABLE", "description": "AC 無法驗證"}])),
        ("update_defect", dict(defect_id=ids.defect, status="FIXED", fixed_in_version_no=2,
                               actor="bridge")),
        ("record_gate_decision", dict(
            research_id=rid, decision_id=ids.decision, gate="GATE0", decision="CHANGES",
            decided_by=ALICE, fsm_project="research-demo", fsm_state_after="HUMAN_PENDING",
            reason="補充證據")),
        ("abandon_fsm_key", dict(
            research_id=rid, decision_id=ids.abandon, decided_by=ALICE, reason="重新來過",
            old_fsm_project="research-demo", new_fsm_project="research-demo-g2",
            new_generation=2, fsm_state_after="ESCALATION")),
        ("append_event", dict(research_id=rid, event_type="research.alert", actor="bridge",
                              payload={"kind": "ESCALATED", "detail": "三輪未過"})),
        ("archive_project", dict(research_id=rid, actor=ALICE)),
        ("restore_project", dict(research_id=rid, actor=ALICE)),
        ("add_allowlist_entry", dict(entry_id=ids.entry, list_kind="FETCH",
                                     host="docs.example.com", layer="INDUSTRY", added_by=ADMIN)),
        ("set_allowlist_enabled", dict(entry_id=ids.entry, enabled=False, disabled_by=ADMIN)),
    ]


@pytest.fixture
def rdb() -> Iterator[ThrowawayDb]:
    db = make_research_db()
    try:
        yield db
    finally:
        db.drop()


def test_the_sample_calls_cover_every_public_write_method_exactly_once() -> None:
    names = [name for name, _p in sample_calls(Ids())]
    assert len(names) == len(set(names)) and set(names) == set(WRITE_METHODS)
    assert all(callable(getattr(ResearchDb, n)) for n in WRITE_METHODS)
    assert set(db_module.METHOD_KINDS.values()) == set(db_module.OPS), "方法與操作登記表一一對應"


# ══ AT-960-2-4：fail-loud ═════════════════════════════════════════════════════════════════════
class FailingConnect:
    def __call__(self) -> Any:
        raise psycopg.OperationalError("injected connect failure")


class _FailingCursor:
    rowcount = 0

    def __enter__(self) -> _FailingCursor:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def execute(self, text: str, params: Any = ()) -> None:
        raise psycopg.errors.UndefinedTable("injected sql failure")


class FailingSqlConnection:
    read_only = False

    def __enter__(self) -> FailingSqlConnection:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def cursor(self, **kwargs: Any) -> _FailingCursor:
        return _FailingCursor()


@pytest.mark.parametrize("method", list(WRITE_METHODS))
def test_AT_960_2_4_a_failed_connection_makes_every_write_method_raise(method: str) -> None:
    payload = dict(sample_calls(Ids()))[method]
    db = ResearchDb(None, connect=FailingConnect())
    with pytest.raises(ResearchDbError) as caught:
        getattr(db, method)(**payload)
    assert caught.value.kind == "connect", method


@pytest.mark.parametrize("method", list(WRITE_METHODS))
def test_AT_960_2_4_a_failed_statement_makes_every_write_method_raise(method: str) -> None:
    payload = dict(sample_calls(Ids()))[method]
    db = ResearchDb(None, connect=FailingSqlConnection)
    with pytest.raises(ResearchDbError) as caught:
        getattr(db, method)(**payload)
    assert caught.value.kind == "execute", method


def test_AT_960_2_4_the_read_side_is_fail_loud_too() -> None:
    for connect, kind in ((FailingConnect(), "connect"), (FailingSqlConnection, "execute")):
        db = ResearchDb(None, connect=connect)
        for call in (lambda d=db: d.get_project(uuid.uuid4()), lambda d=db: d.list_allowlist(),
                     lambda d=db: d.list_events(uuid.uuid4()), lambda d=db: d.ping()):
            with pytest.raises(ResearchDbError) as caught:
                call()
            assert caught.value.kind == kind


def test_AT_960_2_4_the_source_has_no_swallowing_except_and_no_bridgedb_import() -> None:
    tree = ast.parse((RESEARCH_DIR / "db.py").read_text(encoding="utf-8"))
    handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
    assert handlers, "鎖要有標的：db.py 有轉換錯誤的 except"
    for handler in handlers:
        assert handler.type is not None, f"line {handler.lineno}: 不准裸 except"
        assert any(isinstance(n, ast.Raise) for n in ast.walk(handler)), \
            f"line {handler.lineno}: except 區塊必須 raise 或轉拋（不准吞錯）"
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom | ast.Import)
                for a in n.names}
    modules = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "BridgeDb" not in imported, "不 import 既有的 best-effort BridgeDb"
    assert not {"db", "app.db"} & modules, "不 import 既有的 app/db.py"


def test_AT_960_2_4_a_statement_that_fails_midway_rolls_the_whole_operation_back(
        rdb: ThrowawayDb) -> None:
    ids, db = Ids(), ResearchDb(rdb.dsn)
    calls = dict(sample_calls(ids))
    for name in ("create_project", "insert_stage_run", "save_prd"):
        db.apply(db_module.METHOD_KINDS[name], calls[name])
    before = (db.get_project(ids.research)["last_event_seq"], rdb.count("research_events"))
    bad = calls["insert_review_round"]
    bad["scores"] = [{**bad["scores"][0], "score": 150}]     # 輪列已寫入後，分數列違反 CHECK
    with pytest.raises(ResearchDbError) as caught:
        db.insert_review_round(**bad)
    assert caught.value.kind == "execute" and caught.value.sqlstate == "23514"
    assert rdb.count("research_review_rounds") == 0 and rdb.count("research_review_scores") == 0
    assert (db.get_project(ids.research)["last_event_seq"],
            rdb.count("research_events")) == before, "整個操作回滾：事件序號不留洞"


# ══ AT-960-6-7：受控可更新表 ═══════════════════════════════════════════════════════════════
_UPDATE_RE = re.compile(r"UPDATE\s+\{s\}\.(\w+)\s+SET\s+(.+?)\s+WHERE", re.IGNORECASE | re.DOTALL)
_ASSIGN_RE = re.compile(r"(?:^|,)\s*(\w+)\s*=")
_SQL_SOURCES = ("db.py", "outbox.py")


def _string_constants(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
            and isinstance(n.value, str)]


def _update_statements() -> list[tuple[str, set[str]]]:
    found: list[tuple[str, set[str]]] = []
    for name in _SQL_SOURCES:
        for text in _string_constants(RESEARCH_DIR / name):
            matches = _UPDATE_RE.findall(text)
            assert len(re.findall(r"\bUPDATE\s+\{s\}\.\w+", text)) == len(matches), \
                f"{name}: UPDATE 語句不合固定形態（UPDATE {{s}}.<表> SET … WHERE …）：{text[:80]}"
            found += [(table, set(_ASSIGN_RE.findall(clause))) for table, clause in matches]
    return found


def test_AT_960_6_7_every_update_sets_only_controlled_columns_of_a_controlled_table() -> None:
    statements = _update_statements()
    assert {t for t, _c in statements} == set(CONTROLLED_UPDATE_COLUMNS), "鎖要有標的：五張受控表"
    for table, columns in statements:
        assert table in CONTROLLED_UPDATE_COLUMNS, f"UPDATE 了非受控表 {table}"
        assert columns <= CONTROLLED_UPDATE_COLUMNS[table], \
            f"{table} 的 SET 含表外欄位：{sorted(columns - CONTROLLED_UPDATE_COLUMNS[table])}"
        assert table not in APPEND_ONLY_TABLES
    all_set = {c for _t, cols in statements for c in cols}
    assert not all_set & {"playbook_sha256", "config_sha256", "prompt_manifest",
                          "allowlist_snapshot"}, "stage run 的編譯結果欄只出現在 INSERT（D-56）"
    for name in _SQL_SOURCES:
        for text in _string_constants(RESEARCH_DIR / name):
            assert not re.search(r"\bDELETE\s+FROM\b", text, re.IGNORECASE), "寫入器沒有 DELETE"
    assert {t for t, _c in statements} <= set(CONTROLLED_UPDATE_COLUMNS)


def test_AT_960_6_7_the_constant_table_mirrors_the_ddl_guard_lists(rdb: ThrowawayDb) -> None:
    """DB 通用守衛函式的允許清單（V16 `research_controlled_update_guard`）與常數表一致。"""
    source = rdb.one("SELECT pg_get_functiondef('console.research_controlled_update_guard'"
                     "::regproc)")[0]
    for table, columns in CONTROLLED_UPDATE_COLUMNS.items():
        match = re.search(rf"WHEN '{table}' THEN ARRAY\[(.*?)\]", source, re.DOTALL)
        assert match, table
        assert set(re.findall(r"'(\w+)'", match.group(1))) == columns, table


def _run_samples(db_dsn: str, ids: Ids) -> dict[str, list[str]]:
    seen: dict[str, list[str]] = {}
    current: list[str] = []
    db = ResearchDb(db_dsn, statement_hook=lambda text, _p: seen[current[0]].append(text))
    for name, payload in sample_calls(ids):
        current[:] = [name]
        seen[name] = []
        result = getattr(db, name)(**payload)
        assert result["applied"] is True, f"{name} 應該真的套用：{result}"
    return seen


def test_AT_960_6_7_each_update_method_writes_an_event_in_the_same_transaction_and_allowlist_none(
        rdb: ThrowawayDb) -> None:
    ids = Ids()
    seen = _run_samples(rdb.dsn, ids)
    event_insert = "INSERT INTO {s}.research_events"
    for name in ("set_cursor", "archive_project", "restore_project", "abandon_fsm_key",
                 "update_stage_run", "update_defect", "upgrade_source_verification"):
        statements = seen[name]
        assert any(s.startswith("UPDATE {s}.") for s in statements), name
        assert any(s.startswith(event_insert) for s in statements), \
            f"{name}：含 UPDATE 的方法，交易內必含一筆 research_events 的 INSERT"
    round_statements = seen["insert_review_round"]
    round_insert = "INSERT INTO {s}.research_review_rounds"
    assert len([s for s in round_statements if s.startswith(round_insert)]) == 1
    assert not [s for s in round_statements if "research_review_rounds" in s and s.startswith(
        ("UPDATE", "DELETE"))], "輪列只以單一 INSERT 寫入、沒有 UPDATE／DELETE（D-57）"
    assert any(s.startswith(event_insert) for s in round_statements)
    for name in ("add_allowlist_entry", "set_allowlist_enabled"):
        assert not any(event_insert in s for s in seen[name]), f"{name} 不寫 research_events"
    row = rdb.one("SELECT added_by, disabled_by, enabled FROM console.research_allowlist_entries")
    assert row == (ADMIN, ADMIN, False), "added_by／disabled_by 取自傳入的 JWT subject"
    assert rdb.count("research_review_rounds") == 1


def test_AT_960_6_7_source_verification_only_goes_up(rdb: ThrowawayDb) -> None:
    ids, db = Ids(), ResearchDb(rdb.dsn)
    db.create_project(**project_payload(ids))

    def source(no: str, level: str) -> str:
        sid = str(uuid.uuid4())
        db.insert_source(research_id=ids.research, actor="bridge", source={
            "id": sid, "source_no": no, "layer": "ACADEMIC", "tier": "T1", "verification": level,
            "anchor_kind": "URL", "url": f"https://example.org/{no}", "title": no})
        return sid

    def level(sid: str) -> str:
        return rdb.one("SELECT verification FROM console.research_sources WHERE id = %s", sid)[0]

    for no, start, end in (("S-001", "V1", "V2"), ("S-002", "V1", "V3"), ("S-003", "V2", "V3")):
        sid = source(no, start)
        db.upgrade_source_verification(source_id=sid, verification=end, actor="bridge")
        assert level(sid) == end, f"升級 {start}→{end} 應成功"
    for no, start, end in (("S-004", "V3", "V2"), ("S-005", "V3", "V1"), ("S-006", "V2", "V1")):
        sid = source(no, start)
        with pytest.raises(ResearchGuardError) as caught:
            db.upgrade_source_verification(source_id=sid, verification=end, actor="bridge")
        assert caught.value.rule == "verification_downgrade", f"降級 {start}→{end} 必須被拒"
        assert level(sid) == start, "DB 列不變"
        with pytest.raises(psycopg.errors.IntegrityConstraintViolation):    # 第二道：DB 觸發器
            rdb.exec("UPDATE console.research_sources SET verification = %s WHERE id = %s",
                     end, sid)


def test_AT_960_6_7_the_database_guards_agree_with_the_writer(rdb: ThrowawayDb) -> None:
    ids = Ids()
    _run_samples(rdb.dsn, ids)
    for statement in (
            "UPDATE console.research_stage_runs SET playbook_sha256 = repeat('a', 64)",
            "UPDATE console.research_review_rounds SET passed = FALSE",
            "UPDATE console.research_events SET step = 'x'",
            "DELETE FROM console.research_projects"):
        with pytest.raises(psycopg.errors.IntegrityConstraintViolation):
            rdb.exec(statement)


# ── 審查輪號連續（D-61：DB 不擋跳號、由寫入器保證；也是 AT-960-12-8 的寫入器側負控）──────────
def seeded_round_one(rdb: ThrowawayDb) -> tuple[ResearchDb, Ids, dict[str, dict[str, Any]]]:
    ids, db = Ids(), ResearchDb(rdb.dsn)
    calls = dict(sample_calls(ids))
    for name in ("create_project", "insert_stage_run", "save_prd", "insert_review_round"):
        db.apply(db_module.METHOD_KINDS[name], calls[name])
    return db, ids, calls


def next_round(db: ResearchDb, ids: Ids, round_no: int) -> dict[str, Any]:
    """一個合法的未通過輪（無分數與缺陷列），綁一個新建的 REVIEW stage run。"""
    run_id = str(uuid.uuid4())
    db.insert_stage_run(research_id=ids.research, stage_run_id=run_id, stage="REVIEW",
                        round_no=round_no, requested_by=ALICE, status="SUCCEEDED")
    return {"id": str(uuid.uuid4()), "round_no": round_no, "prd_version_no": 1,
            "trigger_kind": "AUTO", "precheck_passed": True, "weighted_score": "79.90",
            "min_dimension_score": 70, "passed": False, "verdict": "REVISE",
            "fsm_gate_result": "FAIL", "fsm_retry_count": 1, "stage_run_id": run_id,
            "started_at": ISO, "finished_at": ISO}


def review_counts(rdb: ThrowawayDb) -> tuple[int, ...]:
    return tuple(rdb.count(t) for t in ("research_review_rounds", "research_review_scores",
                                         "research_review_defects", "research_events"))


def test_AT_960_6_7_a_review_round_that_skips_a_number_is_refused_and_writes_nothing(
        rdb: ThrowawayDb) -> None:
    db, ids, _calls = seeded_round_one(rdb)
    skipped = next_round(db, ids, 3)
    before = review_counts(rdb)
    with pytest.raises(ResearchGuardError) as caught:
        db.insert_review_round(research_id=ids.research, actor="bridge", round=skipped)
    assert caught.value.rule == "round_no_gap"
    assert caught.value.details == {"expected": 2, "got": 3}
    assert review_counts(rdb) == before, "被拒的輪不寫任何列（輪、分數、缺陷、事件）"
    second = db.insert_review_round(research_id=ids.research, actor="bridge",
                                    round=next_round(db, ids, 2))
    assert (second["applied"], second["round_no"]) == (True, 2), "連續的下一輪照常可寫"
    third = db.insert_review_round(research_id=ids.research, actor="bridge", round=skipped)
    assert (third["applied"], third["round_no"]) == (True, 3), "補上 2 之後，3 才合法"


def test_AT_960_6_7_replaying_a_round_is_idempotent_and_a_second_round_with_its_number_conflicts(
        rdb: ThrowawayDb) -> None:
    db, ids, calls = seeded_round_one(rdb)
    before = review_counts(rdb)
    replay = db.insert_review_round(**calls["insert_review_round"])
    assert (replay["applied"], replay["round_no"]) == (False, 1)
    assert review_counts(rdb) == before, "重放同一輪不新增任何列"
    clash = {**calls["insert_review_round"]["round"], "id": str(uuid.uuid4())}
    with pytest.raises(ResearchConflict) as caught:
        db.insert_review_round(research_id=ids.research, actor="bridge", round=clash)
    assert (caught.value.reason, caught.value.details) == ("review_round_conflict",
                                                           {"roundNo": 1})
    assert review_counts(rdb) == before


# ══ AT-960-2-5：斷線 → BLOCKED_DB＋research.alert → 復原後 outbox 重放 ═════════════════════════
def make_writer(rdb: ThrowawayDb, tmp_path: Path, after_step: Any = None) -> DurableWriter:
    return DurableWriter(ResearchDb(rdb.dsn), Outbox(tmp_path / ".outbox" / "outbox.jsonl"),
                         after_step=after_step)


def project_op(ids: Ids, ws: Path) -> tuple[Op, list[FileWrite]]:
    text = json.dumps({"schema_rev": 1, "slug": "demo"}, ensure_ascii=False, indent=2) + "\n"
    rel = layout.ISSUE_SCOPE_REL
    payload = project_payload(ids, str(ws), scope_sha=layout.sha256_text(text))
    payload["issue_scope"]["bytes"] = len(text.encode("utf-8"))
    op = Op("project.create", ids.research, payload,
            files=(FileRef(str(ws), rel, layout.sha256_text(text)),))
    return op, [FileWrite(ws, rel, text)]


def prd_op(ids: Ids, ws: Path, version_no: int = 1) -> tuple[Op, list[FileWrite]]:
    text = f"# PRD v0.{version_no}\n見 [E-001]\n"
    rel = f"01_specs/PRD-v0.{version_no}.0-draft.md"
    digest = layout.sha256_text(text)
    op = Op("prd.save", ids.research, dict(
        research_id=ids.research, version_no=version_no, author_kind="HUMAN", author=ALICE,
        content=text, rel_path=rel, sha256=digest, bytes=len(text.encode("utf-8")),
        change_summary="存新版"), files=(FileRef(str(ws), rel, digest),))
    return op, [FileWrite(ws, rel, text)]


def persist(writer: DurableWriter, built: tuple[Op, list[FileWrite]]) -> dict[str, Any]:
    op, writes = built
    return writer.persist(op, writes=writes)


def seqs(rdb: ThrowawayDb, ids: Ids) -> list[int]:
    return [r[0] for r in rdb.events(ids.research)]


def test_AT_960_2_5_a_db_outage_blocks_the_stage_run_and_replay_loses_and_duplicates_nothing(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    ids, ws = Ids(), tmp_path / "ws" / "demo"
    writer = make_writer(rdb, tmp_path)
    persist(writer, project_op(ids, ws))
    writer.persist(Op("stage_run.insert", ids.research, dict(
        research_id=ids.research, stage_run_id=ids.run, stage="RESEARCH", requested_by=ALICE,
        status="RUNNING")))
    rdb.block()
    evidence = dict(source_no="S-001")
    ops = [Op("source.insert", ids.research, dict(research_id=ids.research, actor="bridge", source={
        "source_no": "S-001", "layer": "ACADEMIC", "tier": "T1", "verification": "V1",
        "anchor_kind": "URL", "url": "https://arxiv.org/abs/1", "title": "t"},
        stage_run_id=ids.run)),
        Op("evidence.record", ids.research, dict(
            research_id=ids.research, matrix_version=1, actor="bridge", stage_run_id=ids.run,
            artifact={"rel_path": "00_research/evidence_items.json", "sha256": sha("e"),
                      "bytes": 1, "content": "{}", "created_by": "bridge"},
            items=[{"evidence_no": "E-001", **evidence, "claim": "c", "f1_mechanism": "m",
                    "f2_evidence": "e", "f3_critique": "k", "f5_applicability": {"x": "A"},
                    "f6_limits": "l", "f7_verification": "V1"}]))]
    for op in ops:                                       # 斷線期間：每個寫入都失敗、但留在 outbox
        with pytest.raises(DbBlocked):
            writer.persist(op)
    pending = writer.outbox.pending()
    assert [o.kind for o in pending] == ["source.insert", "stage_run.update", "event.append",
                                         "evidence.record"]
    blocked = [o for o in pending if o.kind == "stage_run.update"]
    alerts = [o for o in pending if o.kind == "event.append"]
    assert len(blocked) == 1 and blocked[0].payload["status"] == "BLOCKED_DB", \
        "同一個 stage run 的 BLOCKED_DB 只排一次"
    assert len(alerts) == 1 and alerts[0].payload["payload"]["kind"] == "BLOCKED_DB"
    rdb.unblock()
    first = writer.replay()
    assert first.blocked is None and not first.rejected and len(first.applied) == len(pending)
    assert rdb.one("SELECT status FROM console.research_stage_runs WHERE id = %s",
                   ids.run)[0] == "BLOCKED_DB", "以 outbox 暫存的終態為準，恢復後可見"
    assert seqs(rdb, ids) == list(range(1, len(seqs(rdb, ids)) + 1)), "seq 連續、無缺漏、無重複"
    alert_rows = [r for r in rdb.events(ids.research) if r[1] == "research.alert"]
    assert len(alert_rows) == 1 and alert_rows[0][6]["kind"] == "BLOCKED_DB"
    def snapshot() -> tuple[Any, ...]:
        return (seqs(rdb, ids), rdb.count("research_sources"), rdb.count("research_artifacts"))

    before = snapshot()
    second = writer.replay()
    assert second.applied == [] and second.already_applied == [] and not writer.has_pending()
    assert snapshot() == before, "第二次重放不新增任何列"


def test_AT_960_2_5_a_poison_record_is_rejected_and_does_not_block_the_queue(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    ids, ws = Ids(), tmp_path / "ws" / "demo"
    writer = make_writer(rdb, tmp_path)
    persist(writer, project_op(ids, ws))
    clash = Ids()                                       # 另一個專案用了已占用的 slug
    op, writes = project_op(clash, tmp_path / "ws" / "other")
    with pytest.raises(db_module.ResearchConflict) as caught:
        writer.persist(op, writes=writes)
    assert caught.value.reason == "slug_in_use"
    assert not writer.has_pending(), "衝突的記錄標 rejected、不堵住佇列"
    done = [r for r in writer.outbox.read_all() if r.get("rejected")]
    assert [r["rejected"] for r in done] == ["slug_in_use"]


# ══ AT-960-2-6：持久化順序（檔→outbox→DB 交易→標完成）與四個中斷點 ═════════════════════════════
class Crash(BaseException):
    """模擬行程在某一步之後被殺（BaseException：不被 `except Exception` 吞掉）。"""


def crash_after(kind: str, step: str) -> Any:
    def hook(done_step: str, op: Op) -> None:
        if done_step == step and op.kind == kind:
            raise Crash(f"{kind} after {step}")
    return hook


BUILDERS = {"project.create": project_op, "prd.save": prd_op}
FILE_OF = {"project.create": layout.ISSUE_SCOPE_REL, "prd.save": "01_specs/PRD-v0.1.0-draft.md"}


def row_exists(rdb: ThrowawayDb, kind: str, ids: Ids) -> bool:
    if kind == "project.create":
        return rdb.count("research_projects", "id = %s", ids.research) == 1
    return rdb.count("research_prd_versions", "research_id = %s", ids.research) == 1


@pytest.mark.parametrize("kind", list(BUILDERS))
def test_AT_960_2_6_the_call_order_is_file_then_outbox_then_db_then_done(
        kind: str, rdb: ThrowawayDb, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ids, ws = Ids(), tmp_path / "ws" / "demo"
    writer = make_writer(rdb, tmp_path)
    if kind == "prd.save":
        persist(writer, project_op(ids, ws))
    order: list[str] = []

    def wrap(owner: Any, attr: str, label: str) -> None:
        original = getattr(owner, attr)

        def recorded(*args: Any, **kwargs: Any) -> Any:
            order.append(label)
            return original(*args, **kwargs)

        monkeypatch.setattr(owner, attr, recorded)

    wrap(fsutil, "write_text_atomic", "file")
    wrap(Outbox, "append", "outbox")
    wrap(ResearchDb, "apply", "db")
    wrap(Outbox, "mark_done", "done")
    persist(writer, BUILDERS[kind](ids, ws))
    assert order == ["file", "outbox", "db", "done"]


#: 中斷在某步之後 → (檔在, 重放前列在, 重放前待處理記錄數, 重放後列在)
_AFTER_CRASH = {"file": (True, False, 0, False), "outbox": (True, False, 1, True),
                "db": (True, True, 1, True), "done": (True, True, 0, True)}


@pytest.mark.parametrize("step", list(_AFTER_CRASH))
@pytest.mark.parametrize("kind", list(BUILDERS))
def test_AT_960_2_6_a_crash_after_any_step_never_leaves_a_row_without_its_file(
        kind: str, step: str, rdb: ThrowawayDb, tmp_path: Path) -> None:
    ids, ws = Ids(), tmp_path / "ws" / "demo"
    if kind == "prd.save":
        persist(make_writer(rdb, tmp_path), project_op(ids, ws))
    with pytest.raises(Crash):
        persist(make_writer(rdb, tmp_path, after_step=crash_after(kind, step)),
                BUILDERS[kind](ids, ws))
    file_in, row_before, pending, row_after = _AFTER_CRASH[step]
    assert (ws / FILE_OF[kind]).is_file() is file_in
    assert row_exists(rdb, kind, ids) is row_before
    assert not (row_exists(rdb, kind, ids) and not (ws / FILE_OF[kind]).is_file()), "有列無檔"
    restarted = make_writer(rdb, tmp_path)                       # 重啟：新的寫入器、同一個 outbox
    assert len(restarted.outbox.pending()) == pending
    events_before = seqs(rdb, ids)
    report = restarted.replay()
    assert row_exists(rdb, kind, ids) is row_after
    assert (ws / FILE_OF[kind]).is_file() is file_in
    assert not restarted.has_pending()
    if step == "db":                                             # 已套用未標完成：只補標、不重複寫
        assert len(report.already_applied) == 1 and report.applied == []
        assert seqs(rdb, ids) == events_before
    if step == "outbox":
        assert len(report.applied) == 1
    assert seqs(rdb, ids) == list(range(1, len(seqs(rdb, ids)) + 1)), "事件序號連續、不重複"
    assert make_writer(rdb, tmp_path).replay().applied == [], "再重放一次什麼都不變"


def test_AT_960_2_6_a_record_whose_file_vanished_is_rejected_not_applied(
        rdb: ThrowawayDb, tmp_path: Path) -> None:
    ids, ws = Ids(), tmp_path / "ws" / "demo"
    with pytest.raises(Crash):
        persist(make_writer(rdb, tmp_path, after_step=crash_after("project.create", "outbox")),
                project_op(ids, ws))
    (ws / FILE_OF["project.create"]).unlink()                    # 檔案在重放前被人刪掉
    report = make_writer(rdb, tmp_path).replay()
    assert report.rejected and report.rejected[0][1] == "file_missing" and report.applied == []
    assert not row_exists(rdb, "project.create", ids), "絕不先有列、後有檔"


def _flagged_dirent_calls(tree: ast.AST) -> list[int]:
    hits: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        attr, owner = node.func.attr, node.func.value
        owner_id = owner.id if isinstance(owner, ast.Name) else ""
        if (attr == "rename" or (attr == "replace" and (owner_id == "os" or len(node.args) == 1))
                or (attr == "move" and owner_id == "shutil")):
            hits.append(node.lineno)
    return hits


def test_AT_960_2_6_the_research_package_adds_no_directory_entry_primitive() -> None:
    assert _flagged_dirent_calls(ast.parse("os.replace(a, b)")) == [1]
    assert _flagged_dirent_calls(ast.parse("shutil.move(a, b)")) == [1]
    assert _flagged_dirent_calls(ast.parse("p.rename(q)")) == [1]
    assert _flagged_dirent_calls(ast.parse("p.replace(q)")) == [1]
    assert _flagged_dirent_calls(ast.parse('text.replace("a", "b")')) == []
    files = sorted(RESEARCH_DIR.rglob("*.py"))
    assert files
    offenders = {f.name: _flagged_dirent_calls(ast.parse(f.read_text(encoding="utf-8")))
                 for f in files}
    assert {n: h for n, h in offenders.items() if h} == {}, \
        "app/research/** 內 os.replace／rename／shutil.move／Path.replace 呼叫數須為 0"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PKG-BR-C 附加（append-only；上方既有測試一字未動）：AT-960-9-E-1、12-5、12-9。
# 這三個 AT 要活 Bridge＋引擎＋假 claude 的整條 stage 流程，夾具與流程助手住在
# `test_research_orchestrator.py`、播種助手住在 `test_research_approve.py`，這裡只引用。
# ══════════════════════════════════════════════════════════════════════════════════════════════
from tests import test_research_approve as _approve  # noqa: E402  （附加區：引用共用助手）
from tests import test_research_orchestrator as _orch  # noqa: E402
from tests import test_research_router as _router  # noqa: E402

tree, scripted, rig = _orch.tree, _orch.scripted, _orch.rig
popen_log, make_env, env = _router.popen_log, _router.make_env, _router.env


def _rows(db: ResearchDb, sql: str, *params: Any) -> list[dict[str, Any]]:
    return db.query(sql, params)


# ── AT-960-9-E-1：抓取、來源、證據、PRD 版本與登記列的入庫欄位 ───────────────────────────────────
def test_AT_960_9_E_1_ingested_rows_are_complete_and_equal_the_files(
        make_bridge: Any, settings: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        tree: Path, rdb: ThrowawayDb) -> None:
    script = _orch.custom_script(tmp_path, lambda steps: None)
    declared = json.loads((tmp_path / "scripts" / "content" / "evidence_items.json").read_text(
        encoding="utf-8"))
    declared["search_log"].append({
        "id": "Q-009", "layer": "INDUSTRY", "tool": "WebFetch", "at": "2026-11-02T10:30:00+08:00",
        "query": "https://Example.org/blog/example-post", "result_urls": []})
    (tmp_path / "scripts" / "content" / "evidence_items.json").write_text(
        json.dumps(declared, ensure_ascii=False), encoding="utf-8")
    live = _orch.build_rig(make_bridge, settings, tmp_path, monkeypatch, tree, rdb, script=script)
    rid = _orch.create(live)
    _orch.run_stage(live, rid, "research")
    ws = Path(_orch.project(live, rid)["workspace_path"])
    fetches = _rows(live.db, "SELECT * FROM {s}.research_fetches WHERE research_id = %s "
                    "ORDER BY fetch_no", rid)
    numbers = [f["fetch_no"] for f in fetches]
    assert all(re.fullmatch(r"F-\d{4,}", n) for n in numbers)
    assert [int(n[2:]) for n in numbers] == list(range(1, len(numbers) + 1)), "單調、無重複"
    bridge = [f for f in fetches if f["observed_by"] == "BRIDGE"]
    agent = [f for f in fetches if f["observed_by"] == "AGENT_DECLARED"]
    assert bridge and len(agent) == len(declared["search_log"]) == 9
    for row in bridge:
        assert row["layer"] and row["outcome"] and row["stage_run_id"] and row["fetched_at"]
        if row["outcome"] == "OK":
            raw = ws / row["raw_rel_path"]
            assert row["raw_sha256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
            assert row["raw_bytes"] == len(raw.read_bytes())
        else:
            assert row["raw_sha256"] is None, "失敗或被拒的列沒有原文雜湊"
    for entry, row in zip(declared["search_log"], agent, strict=True):
        assert row["search_no"] == int(entry["id"][2:]) and row["query_text"] == entry["query"]
        assert list(row["result_urls"]) == entry["result_urls"]
        if entry["tool"] == "WebFetch":
            assert (row["fetch_method"], row["url"], row["host"]) == (
                "WEB_FETCH", entry["query"], "example.org")
        else:
            assert (row["fetch_method"], row["url"], row["host"]) == ("WEB_SEARCH", None, None)
    items = {i["evidence_no"]: i for i in declared["items"]}
    stored = _rows(live.db, "SELECT * FROM {s}.research_evidence_items WHERE research_id = %s",
                   rid)
    assert {r["evidence_no"] for r in stored} == set(items)
    for row in stored:
        item = items[row["evidence_no"]]
        assert (row["candidate"], row["scope_rev"], row["strength"]) == (
            item["candidate"], declared["scope_rev"], item["strength"])
        assert (row["claim"], row["f1_mechanism"], row["f2_evidence"], row["f3_critique"],
                row["f6_limits"], row["f7_verification"]) == (
            item["claim"], item["f1"], item["f2"], item["f3"], item["f6"], item["f7"])
        assert list(row["f4_risk_tags"]) == item["f4"] and row["unanchored"] is False
    registered = _rows(live.db, "SELECT * FROM {s}.research_artifacts WHERE research_id = %s AND "
                       "kind = 'EVIDENCE_ITEMS'", rid)
    assert len(registered) == 1
    file_bytes = (ws / "00_research" / "evidence_items.json").read_bytes()
    assert registered[0]["content"].encode("utf-8") == file_bytes
    assert registered[0]["sha256"] == hashlib.sha256(file_bytes).hexdigest()
    # 對照組：content 為 NULL 的登記嘗試入庫被拒，整次入庫不寫任何證據列與登記列
    before = (rdb.count("research_evidence_items"), rdb.count("research_artifacts"))
    with pytest.raises((ResearchGuardError, ResearchDbError)):
        live.db.record_evidence(
            research_id=rid, matrix_version=2, actor="bridge", stage_run_id=None,
            artifact={"rel_path": "00_research/evidence_items.json", "sha256": sha("x"),
                      "bytes": 1, "content": None, "created_by": "bridge"},
            items=[{"evidence_no": "E-900", "source_no": "S-001", "claim": "x", "f1_mechanism": "x",
                    "f2_evidence": "x", "f3_critique": "x", "f5_applicability": {},
                    "f6_limits": "x", "f7_verification": "V2", "strength": "MEDIUM"}])
    assert (rdb.count("research_evidence_items"), rdb.count("research_artifacts")) == before
    # PRD：每次寫入新增一列、sha256 等於 01_specs 對應檔案；舊列不可改
    for version, text in ((1, "# PRD 一\n"), (2, "# PRD 二\n")):
        saved = live.put(f"/research/projects/{rid}/prd", {
            "base_version": version - 1, "content": text, "author": ALICE})
        assert saved.status_code == 201, saved.text
    versions = _rows(live.db, "SELECT * FROM {s}.research_prd_versions WHERE research_id = %s "
                     "ORDER BY version_no", rid)
    assert [v["version_no"] for v in versions] == [1, 2], "每次寫入各新增一列"
    for row in versions:
        assert row["sha256"] == hashlib.sha256((ws / row["rel_path"]).read_bytes()).hexdigest()
    with pytest.raises(psycopg.errors.Error):
        rdb.exec("UPDATE console.research_prd_versions SET content = 'x' WHERE research_id = %s",
                 rid)


# ── AT-960-12-5：輪與缺陷入庫、審查卡逐欄相等、缺陷只依單向表轉移 ─────────────────────────────────
DEFECT_STATES = ("OPEN", "FIXED", "WAIVED", "SUPERSEDED", "REGRESSED")
ALLOWED_DEFECT_MOVES = {("OPEN", "FIXED"), ("OPEN", "WAIVED"), ("OPEN", "SUPERSEDED"),
                        ("FIXED", "REGRESSED"), ("REGRESSED", "FIXED")}


def _add_round_docs(script: str, round_no: int, prd_text: str, docs: dict[str, Any]) -> None:
    """為劇本加一輪審查：四份維度 JSON 由呼叫端給（可事先改缺陷），這裡只補 round 與 prd_sha256。"""
    path = Path(script)
    digest = hashlib.sha256(prd_text.encode("utf-8")).hexdigest()
    plan = json.loads(path.read_text(encoding="utf-8"))
    for dimension in _orch.DIMS:
        data = {**docs[dimension], "round": round_no, "prd_sha256": digest}
        rel = f"content/r{round_no}-{dimension}.json"
        (path.parent / rel).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        plan["steps"].append({"role": f"review-{dimension}", "round": round_no, "writes": [{
            "path": f"02_governance/reviews/round-{round_no}/{dimension}.json", "from": rel}]})
    path.write_text(json.dumps(plan), encoding="utf-8")


def test_AT_960_12_5_defect_status_moves_only_along_the_one_way_table() -> None:
    from app.research.gates.review_card import is_allowed_transition, next_defect_status

    for old in DEFECT_STATES:
        for new in DEFECT_STATES:
            allowed = (old, new) in ALLOWED_DEFECT_MOVES
            assert is_allowed_transition(old, new) is allowed, (old, new)
            if new != "WAIVED":
                if allowed:
                    assert next_defect_status(old, new) == new
                else:
                    with pytest.raises(ValueError):
                        next_defect_status(old, new)
    assert next_defect_status("OPEN", "WAIVED", waived_by=ALICE, waiver_reason="接受風險") == (
        "WAIVED")
    for by, reason in ((None, "x"), (ALICE, ""), (ALICE, "  ")):
        with pytest.raises(ValueError):
            next_defect_status("OPEN", "WAIVED", waived_by=by, waiver_reason=reason)


def test_AT_960_12_5_three_rounds_agree_with_the_card_and_a_reraised_defect_regresses(
        scripted: tuple[Any, str]) -> None:
    from decimal import Decimal

    from app.research.gates.review_card import validate_review_card

    live, script = scripted
    base = {dim: json.loads((_orch.SCRIPTS / "content" / "reviews" / "common" / "round-1" /
                             f"{dim}.json").read_text(encoding="utf-8")) for dim in _orch.DIMS}
    fixed_one = {**base, "qa": {**base["qa"], "defects": base["qa"]["defects"][1:]}}
    target = base["qa"]["defects"][0]                      # 第 2 輪不再提出、第 3 輪再度提出
    for number, docs in ((1, base), (2, fixed_one), (3, base)):
        _add_round_docs(script, number, _orch.PRD_V1, docs)
    rid = _orch.create(live)
    _orch.to_draft(live, rid)

    def defect_state() -> dict[str, Any]:
        """第 1 輪提出的那一列（每輪的發現各自成列；舊列的 status 依後續輪次轉移）。"""
        found = _rows(live.db, "SELECT d.* FROM {s}.research_review_defects d JOIN "
                      "{s}.research_review_rounds r ON r.id = d.round_id WHERE r.research_id = %s "
                      "AND r.round_no = 1 AND d.code = %s AND d.prd_anchor = %s", rid,
                      target["code"], target["prd_anchor"])
        assert len(found) == 1 and found[0]["defect_no"].startswith("D-1-")
        return found[0]

    _orch.run_stage(live, rid, "review")
    assert defect_state()["status"] == "OPEN"
    _orch.run_stage(live, rid, "revise")
    _orch.run_stage(live, rid, "review")
    after_two = defect_state()
    assert after_two["status"] == "FIXED" and after_two["resolved_at"] is not None
    assert after_two["fixed_in_version_no"] == _orch.rounds(live, rid)[1]["prd_version_no"]
    _orch.run_stage(live, rid, "revise")
    _orch.run_stage(live, rid, "review")
    assert defect_state()["status"] == "REGRESSED", "已 FIXED 的缺陷再度被提出＝REGRESSED"
    rounds = _orch.rounds(live, rid)
    assert [r["verdict"] for r in rounds] == ["REVISE", "REVISE", "ESCALATE"]
    ws = Path(_orch.project(live, rid)["workspace_path"])
    card = json.loads((ws / "02_governance" / "review_card.json").read_text(encoding="utf-8"))
    problems = validate_review_card(card)
    assert problems == [], [(p.rule, p.path, p.message) for p in problems]
    assert card["final_verdict"] == "ESCALATED" and len(card["rounds"]) == 3
    versions = {v["version_no"]: v for v in _rows(
        live.db, "SELECT version_no, semver, sha256 FROM {s}.research_prd_versions "
        "WHERE research_id = %s", rid)}
    last_no = 0
    for row, entry in zip(rounds, card["rounds"], strict=True):
        scores = _rows(live.db, "SELECT dimension, score FROM {s}.research_review_scores "
                       "WHERE round_id = %s", row["id"])
        assert {s["dimension"]: s["score"] for s in scores} == {
            r["dimension"]: r["score"] for r in entry["reviewers"]}
        assert Decimal(str(entry["weighted_total"])) == row["weighted_score"]
        assert entry["round"] == row["round_no"] and entry["passed"] == row["passed"]
        assert entry["prd_version_no"] == row["prd_version_no"] >= last_no, "輪與輪不遞減"
        last_no = entry["prd_version_no"]
        assert entry["prd_version"] == versions[row["prd_version_no"]]["semver"]
        assert entry["prd_sha256"] == versions[row["prd_version_no"]]["sha256"]
        assert set(entry["fsm"]) == {"gate_result", "retry_count"}
        assert (entry["fsm"]["gate_result"] == "PASS") == bool(row["passed"])
        assert [c["id"] for c in entry["precheck"]["checks"]] == [
            "SLV-001", "SLV-002", "SLV-003", "AMBIGUITY"]
        assert "dimension_floor" in entry["params"]
        for reviewer in entry["reviewers"]:
            assert set(reviewer) == {
                "dimension", "weight", "agent", "agent_id", "agent_yaml_sha256",
                "assist_agent_id", "assist_agent_yaml_sha256", "persona_sha256", "score",
                "raw_file", "raw_sha256"}
            assert (reviewer["assist_agent_id"] is not None) == (
                reviewer["dimension"] == "SECURITY"), "只有 SECURITY 有 assist"
        stored = _rows(live.db, "SELECT * FROM {s}.research_review_defects WHERE round_id = %s "
                       "ORDER BY defect_no", row["id"])
        assert len(stored) == len(entry["defects"])
    shown = {d["id"]: d for r in card["rounds"] for d in r["defects"]}
    for row in _rows(live.db, "SELECT d.* FROM {s}.research_review_defects d JOIN "
                     "{s}.research_review_rounds r ON r.id = d.round_id WHERE r.research_id = %s",
                     rid):
        card_row = shown[row["defect_no"]]
        assert (card_row["dimension"], card_row["severity"], card_row["code"],
                card_row["anchor"], card_row["finding"], card_row["status"]) == (
            row["dimension"], row["severity"], row["code"], row["prd_anchor"],
            row["description"], row["status"])


# ── AT-960-12-9：審查結果的寫入順序與崩潰冪等（D-58）─────────────────────────────────────────
def _journal_entry_for(round_no: int, rid: str, run_id: str, *, passed: bool,
                       trigger: str = "AUTO", intent: str | None) -> dict[str, Any]:
    from app.research.gates.schemas import DIMENSIONS, RUBRIC_REGISTRY

    score = 90 if passed else 80
    return {
        "v": 1, "research_id": rid, "round_no": round_no, "stage_run_id": run_id, "done": False,
        "trigger_kind": trigger, "prd_version_no": 1, "prd_text_sha256": sha("prd"),
        "precheck": {"passed": True, "checks": [
            {"id": i, "passed": True, "detail": ""} for i in
            ("SLV-001", "SLV-002", "SLV-003", "AMBIGUITY")]},
        "precheck_passed": True, "open_p1_count": 0,
        "scores": [{
            "dimension": d, "score": score, "agent_id": RUBRIC_REGISTRY[d]["agent_id"],
            "assist_agent_id": None, "assist_agent_yaml_sha256": None,
            "agent_yaml_path": RUBRIC_REGISTRY[d]["agent_file"], "agent_yaml_sha256": sha("yaml"),
            "persona_sha256": sha("persona"), "summary": "摘要", "stage_run_id": run_id,
            "raw_rel_path": f"02_governance/reviews/round-{round_no}/{d.lower()}.json",
            "raw_sha256": sha(f"{round_no}{d}")} for d in DIMENSIONS],
        "defects": [{"defect_no": f"D-{round_no}-001", "dimension": "QA", "severity": "P3",
                     "code": "QA-TRACEABILITY-01", "prd_anchor": "§14", "description": "追蹤鏈不全",
                     "suggestion": "補齊", "evidence_refs": []}],
        "weighted_score": f"{score}.00", "min_dimension_score": score, "passed": passed,
        "gate_intent": intent,
        "gate_reason": f"R2P review round {round_no} (stage_run {run_id})",
        "fsm_generation": 1, "started_at": ISO, "finished_at": ISO}


def _stage_journal(orch: Any, rid: str, entry: dict[str, Any]) -> None:
    """為崩潰重放播種：REVIEW stage run（外鍵）與落在磁碟上、尚未標完成的輪結果。"""
    orch.db.insert_stage_run(research_id=rid, stage_run_id=entry["stage_run_id"], stage="REVIEW",
                             round_no=entry["round_no"], requested_by=ALICE, status="SUCCEEDED")
    orch.journal.write(entry)


def _history(ctx: Any) -> list[Any]:
    from app.research import fsm_ops

    retry = (fsm_ops.show(ctx).get("retry_history") or {}).get("SCG_VALIDATION") or {}
    return list(retry.get("history") or [])


def _review_events(env: Any, rid: str) -> int:
    return len(_rows(env.db, "SELECT 1 FROM {s}.research_events WHERE research_id = %s AND "
                     "event_type = 'research.review'", rid))


def _orchestrator(env: Any) -> Any:
    return env.live.app.state.research.orchestrator


def _gate_calls(log: list[list[str]], since: int) -> int:
    return [c[0] for c in _approve.fsm_calls(log, since)].count("gate")


def test_AT_960_12_9_the_round_result_is_on_disk_before_gate_and_one_transaction_follows(
        scripted: tuple[Any, str], monkeypatch: pytest.MonkeyPatch) -> None:
    from app.research import fsm_ops

    live, script = scripted
    rid, _ = _orch.ready_for_round_two(live, script)
    path = live.orch.journal.directory / f"r-{rid}-2.json"
    seen: list[dict[str, Any]] = []
    real_gate = fsm_ops.gate

    def spy(ctx: Any, **kw: Any) -> Any:
        seen.append(json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {})
        return real_gate(ctx, **kw)

    monkeypatch.setattr(fsm_ops, "gate", spy)
    _orch.run_stage(live, rid, "review")
    assert len(seen) == 1, "gate 恰呼叫一次"
    pre = seen[0]
    assert {"scores", "defects", "prd_version_no", "trigger_kind", "weighted_score"} <= set(pre)
    assert len(pre["scores"]) == 4 and pre["done"] is False
    assert not {"fsm_gate_result", "fsm_retry_count", "verdict"} & set(pre), (
        "gate 呼叫瞬間磁碟上的結果還沒有 FSM 回報的欄位")
    row = _orch.rounds(live, rid)[1]
    assert (row["fsm_gate_result"], row["fsm_retry_count"], row["verdict"]) == ("FAIL", 2, "REVISE")
    assert json.loads(path.read_text(encoding="utf-8"))["done"] is True
    counts = (live.rdb.count("research_review_scores"), live.rdb.count("research_review_defects"),
              len(_orch.events(live, rid, "research.review")))
    assert counts[0] == 8 and counts[2] == 2


def test_AT_960_12_9_case_a_gate_already_called_replay_only_fills_the_db(
        env: Any, popen_log: list[list[str]]) -> None:
    from app.research import fsm_ops

    rid = _router.create(env)["research_id"]
    _approve.seed_pending(env, rid, passed=False, fsm="SCG_VALIDATION")
    run_id = str(uuid.uuid4())
    entry = _journal_entry_for(2, rid, run_id, passed=False, intent="FAIL")
    _stage_journal(_orchestrator(env), rid, entry)
    ctx = _router.fsm_ctx_of(env, rid)
    fsm_ops.gate(ctx, gate="SCG_VALIDATION", result="FAIL", reason=entry["gate_reason"])
    history, events = len(_history(ctx)), _review_events(env, rid)
    since = len(popen_log)
    for _ in range(2):                                   # 重放兩次
        _orchestrator(env).reap_orphans()
    assert _gate_calls(popen_log, since) == 0, "gate 已呼叫過：重放不再呼叫"
    assert len(_history(ctx)) == history == 1
    rows = _rows(env.db, "SELECT * FROM {s}.research_review_rounds WHERE research_id = %s AND "
                 "round_no = 2", rid)
    assert len(rows) == 1 and rows[0]["fsm_gate_result"] == "FAIL"
    assert rows[0]["fsm_retry_count"] == 1
    assert env.rdb.count("research_review_scores") == 4, "四維分數各恰一列"
    assert _review_events(env, rid) == events + 1, "research.review 事件恰一筆"


def test_AT_960_12_9_case_b_gate_not_yet_called_replay_calls_it_exactly_once_then_writes(
        env: Any, popen_log: list[list[str]]) -> None:
    rid = _router.create(env)["research_id"]
    _approve.seed_pending(env, rid, passed=False, fsm="SCG_VALIDATION")
    entry = _journal_entry_for(2, rid, str(uuid.uuid4()), passed=False, intent="FAIL")
    _stage_journal(_orchestrator(env), rid, entry)
    ctx = _router.fsm_ctx_of(env, rid)
    before = len(_history(ctx))
    since = len(popen_log)
    for _ in range(2):
        _orchestrator(env).reap_orphans()
    assert _gate_calls(popen_log, since) == 1, "重放先呼叫 gate 恰一次（第二次重放不再呼叫）"
    assert len(_history(ctx)) == before + 1, "未通過：retry_history 恰加一筆"
    rows = _rows(env.db, "SELECT * FROM {s}.research_review_rounds WHERE research_id = %s AND "
                 "round_no = 2", rid)
    assert len(rows) == 1 and rows[0]["fsm_retry_count"] == 1
    assert json.loads((_orchestrator(env).journal.directory / f"r-{rid}-2.json").read_text(
        encoding="utf-8"))["done"] is True


def test_AT_960_12_9_case_c_a_post_human_pass_is_never_given_a_gate_pass_on_replay(
        env: Any, popen_log: list[list[str]]) -> None:
    from app.research import fsm_ops

    rid = _router.create(env)["research_id"]
    _approve.seed_pending(env, rid)                      # FSM 在 HUMAN_PENDING、第 1 輪已通過
    entry = _journal_entry_for(2, rid, str(uuid.uuid4()), passed=True, trigger="POST_HUMAN",
                               intent=None)
    _stage_journal(_orchestrator(env), rid, entry)
    ctx = _router.fsm_ctx_of(env, rid)
    trace = len(fsm_ops.show(ctx)["decision_trace"])
    since = len(popen_log)
    for _ in range(2):
        _orchestrator(env).reap_orphans()
    assert _gate_calls(popen_log, since) == 0, "POST_HUMAN 通過輪依設計不呼叫 gate"
    assert fsm_ops.current_state(ctx) == "HUMAN_PENDING"
    assert len(fsm_ops.show(ctx)["decision_trace"]) == trace
    rows = _rows(env.db, "SELECT * FROM {s}.research_review_rounds WHERE research_id = %s AND "
                 "round_no = 2", rid)
    assert len(rows) == 1 and rows[0]["passed"] is True
    assert (rows[0]["fsm_gate_result"], rows[0]["fsm_retry_count"]) == (None, None)
    assert rows[0]["trigger_kind"] == "POST_HUMAN"


# ── AT-960-2-5（stage 實跑那一半）：stage 中途資料庫寫入失敗 → BLOCKED_DB＋alert → 復原重放 ──────
def test_AT_960_2_5_a_db_outage_during_a_stage_blocks_the_run_and_replay_is_exact(
        make_bridge: Any, settings: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        tree: Path, rdb: ThrowawayDb) -> None:
    class Outage:
        armed = False

        def __call__(self, text: str, _params: Any) -> None:
            if self.armed and text.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                raise psycopg.errors.InternalError_("injected: database connection closed")

    outage = Outage()
    script = _orch.custom_script(tmp_path, lambda steps: None)
    live = _orch.build_rig(make_bridge, settings, tmp_path, monkeypatch, tree, rdb,
                           script=script, hook=outage)
    rid = _orch.create(live)
    _orch.patch_step(script, "research", 0, delay=4)
    _orch.run_stage(live, rid, "research", wait=False)
    _orch.wait_until(lambda: any(r["status"] == "RUNNING" for r in _orch.runs_of(
        live, rid, "RESEARCH")) and live.trace.is_file()
        and "research" in live.trace.read_text(encoding="utf-8"))
    outage.armed = True                                     # stage 中途：後續寫入全部失敗
    assert live.orch.join(rid, 120)
    run = _orch.runs_of(live, rid, "RESEARCH")[0]
    assert run["status"] == "RUNNING", "阻塞期間資料庫沒被更新；終態暫存在 outbox"
    pending = live.orch.writer.outbox.pending()
    staged = {(op.kind, op.payload.get("status") or op.payload.get("event_type")) for op in pending}
    assert ("stage_run.update", "BLOCKED_DB") in staged
    alert = next(op for op in pending if op.kind == "event.append"
                 and op.payload["event_type"] == "research.alert")
    assert alert.payload["payload"]["kind"] == "BLOCKED_DB"
    outage.armed = False                                    # 恢復資料庫、重放兩次
    live.orch.writer.replay()
    assert _orch.runs_of(live, rid, "RESEARCH")[0]["status"] == "BLOCKED_DB"
    events = live.db.list_events(rid, limit=500)
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1)), "seq 自 1 起連續"
    assert [e["payload"].get("kind") for e in events if e["event_type"] == "research.alert"] == [
        "BLOCKED_DB"]
    before = (rdb.count("research_events"), rdb.count("research_stage_runs"),
              rdb.count("research_evidence_items"))
    live.orch.writer.replay()
    assert (rdb.count("research_events"), rdb.count("research_stage_runs"),
            rdb.count("research_evidence_items")) == before, "第二次重放不新增任何列"
    assert not live.orch.writer.outbox.pending(), "重放完成後 outbox 沒有待處理記錄"
