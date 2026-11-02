"""對帳（TCS-ResearchToPRD-P0 AC-960-21；PRD §5.1.1；D-56）。

`:reconcile` 只報告、不修復；游標與 FSM 的對映由表驅動（`FLOW_FSM_MAPPING`）；`state.json` 只被
寫出、不被當輸入。專案以資料庫與 FSM 直接播種（同 `test_research_approve.py` 的 Given），
FSM 樹有 `fake` 與 `real` 兩種。
"""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from typing import Any

import pytest

from app.research import layout
from app.research.gates.reconcile import (
    CHECK_IDS,
    FLOW_FSM_MAPPING,
    derive_flow_status,
    flow_fsm_mapping_ok,
)
from app.research.orchestrator import MATRIX_REL, REVIEW_CARD_REL
from tests import test_research_router as router_tests
from tests.test_research_approve import (
    ADMIN,
    BASELINE_REL,
    approve,
    seed_pending,
    seen,
    state_file,
    workspace,
)
from tests.test_research_router import Env, create, project_row, tree_digest

rdb, fake, tree, popen_log = (router_tests.rdb, router_tests.fake, router_tests.tree,
                              router_tests.popen_log)
make_env, env = router_tests.make_env, router_tests.env

ENGINE_BRIDGE = Path(__file__).resolve().parents[1]
AGENT_CONSOLE = ENGINE_BRIDGE.parent
EVENT_TABLES = ("research_events",)


def hex_of(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def reconcile(env: Env, rid: str) -> dict[str, Any]:
    resp = env.post(f"/research/projects/{rid}:reconcile", {})
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def register(env: Env, rid: str, kind: str, rel: str, text: str, version: int = 1) -> None:
    """寫一個檔案並登記成資料庫的產物列（kind＋版本＋sha256）。"""
    written = layout.write_workspace_file(workspace(env, rid), rel, text)
    env.db.apply("artifact.insert", {
        "research_id": rid, "kind": kind, "version": version, "rel_path": rel,
        "sha256": written.sha256, "bytes": written.bytes, "origin": "BRIDGE",
        "created_by": "bridge"})


def reconcile_events(env: Env, rid: str) -> list[dict[str, Any]]:
    return [e for e in env.db.list_events(rid, limit=500)
            if e["event_type"] == "research.reconcile"]


def counts(env: Env) -> dict[str, int]:
    assert env.rdb is not None
    tables = ("research_artifacts", "research_prd_versions", "research_gate_decisions",
              "research_stage_runs", "research_review_rounds", "research_projects")
    return {t: env.rdb.count(t) for t in tables}


def seeded(env: Env, slug: str = "demo") -> tuple[str, str, Path]:
    """已有 PRD（head 草稿）、證據矩陣與審查卡登記列、`issue_scope.json` 的專案。"""
    rid = create(env, slug)["research_id"]
    seed_pending(env, rid)
    register(env, rid, "EVIDENCE_MATRIX", MATRIX_REL, "# 證據矩陣\n\n| E-001 | 來源 |\n")
    register(env, rid, "REVIEW_CARD", REVIEW_CARD_REL, '{"rounds": []}\n')
    return rid, env.db.head_prd(rid)["rel_path"], workspace(env, rid)


# ── AT-960-21-1：六項對帳、漂移、缺檔 ───────────────────────────────────────────────────────
def test_AT_960_21_1_six_checks_report_drift_with_both_digests_and_fix_nothing(env: Env) -> None:
    rid, head_rel, ws = seeded(env)
    first = reconcile(env, rid)
    assert [c["id"] for c in first["checks"]] == list(CHECK_IDS)
    assert first["consistent"] is True and first["driftCount"] == 0
    assert all(c["status"] == "ok" for c in first["checks"])
    assert {c["id"]: c["present"] for c in first["checks"]} == {
        "fsm_flow_mapping": True, "prd_sha256": True, "review_card": True,
        "evidence_matrix": True, "task_decomposition": False, "route_decision": False}
    # 未改時呼叫前後：檔案位元組與 mtime、資料列（事件除外）皆不變；每次呼叫恰追加一筆對帳事件
    files, rows, events = tree_digest(ws), counts(env), len(reconcile_events(env, rid))
    reconcile(env, rid)
    assert tree_digest(ws) == files and counts(env) == rows
    assert len(reconcile_events(env, rid)) == events + 1
    # 逐項人為改檔：改的那項 drift、其餘仍 ok
    for check_id, rel, kind in (("prd_sha256", head_rel, "PRD"),
                                ("evidence_matrix", MATRIX_REL, "EVIDENCE_MATRIX"),
                                ("review_card", REVIEW_CARD_REL, "REVIEW_CARD")):
        original = (ws / rel).read_bytes()
        (ws / rel).write_bytes(original + b"!")
        result = reconcile(env, rid)
        item = next(c for c in result["checks"] if c["id"] == check_id)
        assert item["status"] == "drift" and result["consistent"] is False, check_id
        assert item["drift"] == [{"kind": kind, "path": rel, "expectedSha256": hex_of(original),
                                  "actualSha256": hex_of(original + b"!")}]
        assert result["driftCount"] == 1
        assert all(c["status"] == "ok" for c in result["checks"] if c["id"] != check_id)
        assert (ws / rel).read_bytes() == original + b"!", "Bridge 不修任何一邊"
        (ws / rel).write_bytes(original)
    # 資料庫有列而檔案缺席：一樣是 drift（actualSha256 為 null）
    (ws / MATRIX_REL).unlink()
    missing = next(c for c in reconcile(env, rid)["checks"] if c["id"] == "evidence_matrix")
    assert missing["status"] == "drift" and missing["detail"] == "file_missing"
    assert missing["drift"][0]["actualSha256"] is None and not (ws / MATRIX_REL).exists()
    payloads = [e["payload"] for e in reconcile_events(env, rid)]
    assert all(set(p) >= {"consistent", "driftCount"} for p in payloads) and len(payloads) == 6
    assert [p["consistent"] for p in payloads] == [True, True, False, False, False, False]


# ── AT-960-21-2：游標與 FSM 的對映表（單元）─────────────────────────────────────────────────
LEGAL = {
    ("AGENT_LOAD", "topic", "INGESTED"), ("AGENT_LOAD", "topic", "EVIDENCE_READY"),
    ("SPEC_DRAFTING", "studio", "DRAFTING"), ("SPEC_DRAFTING", "studio", "REVISING"),
    ("SCG_VALIDATION", "studio", "REVIEWING"),
    ("HUMAN_PENDING", "studio", "GATE0_PENDING"), ("HUMAN_PENDING", "studio", "REVISING"),
    ("ESCALATION", "studio", "REVIEWING"), ("ESCALATION", "studio", "REVISING"),
    ("SPEC_FROZEN", "route", "FROZEN"),
}
ILLEGAL = {
    ("ESCALATION", "route", "FROZEN"), ("ESCALATION", "topic", "INGESTED"),
    ("IMPLEMENTATION", "studio", "DRAFTING"), ("IMPLEMENTATION", "studio", "REVIEWING"),
    ("IMPLEMENTATION", "studio", "REVISING"), ("SPEC_FROZEN", "topic", "INGESTED"),
    ("HUMAN_PENDING", "topic", "INGESTED"), ("HUMAN_PENDING", "route", "FROZEN"),
    ("SCG_VALIDATION", "studio", "REVISING"), ("SPEC_DRAFTING", "studio", "REVIEWING"),
    ("AGENT_LOAD", "studio", "DRAFTING"), (None, "topic", "INGESTED"),
    ("NO_SUCH_STATE", "studio", "REVISING"),
}


@pytest.mark.parametrize("fsm_state, step, phase", sorted(LEGAL, key=str))
def test_AT_960_21_2_legal_rows_are_true(fsm_state: str, step: str, phase: str) -> None:
    assert flow_fsm_mapping_ok(fsm_state, step, phase) is True


@pytest.mark.parametrize("fsm_state, step, phase", sorted(ILLEGAL, key=str))
def test_AT_960_21_2_illegal_rows_are_false(fsm_state: str | None, step: str, phase: str) -> None:
    assert flow_fsm_mapping_ok(fsm_state, step, phase) is False


def test_AT_960_21_2_the_table_is_the_whole_rule_and_status_is_derived_not_judged() -> None:
    accepted = {(s, step, phase) for s, by_step in FLOW_FSM_MAPPING.items()
                for step, phases in by_step.items() for phase in phases}
    assert LEGAL <= accepted, "TCS 逐列的合法列都在表內"
    assert not accepted & ILLEGAL, "TCS 逐列的不合列都不在表內"
    # 表驅動：表外的任何組合一律假；`flow_status` 不是輸入（簽名只有三個參數）
    for state in ("INIT", "SPEC_FROZEN", "ESCALATION_FINAL"):
        for step in ("topic", "studio", "route", "bogus"):
            for phase in ("INGESTED", "REVIEWING", "FROZEN", "BOGUS"):
                assert flow_fsm_mapping_ok(state, step, phase) is ((state, step, phase) in accepted)
    # 衍生函式（優先序 ESCALATED > RUNNING > WAITING_HUMAN > IDLE）
    assert derive_flow_status(["RUNNING"], "ESCALATION") == "ESCALATED"
    assert derive_flow_status(["QUEUED"], "HUMAN_PENDING") == "RUNNING"
    assert derive_flow_status(["SUCCEEDED", "FAILED"], "HUMAN_PENDING") == "WAITING_HUMAN"
    assert derive_flow_status([], "SCG_VALIDATION") == "IDLE"
    assert derive_flow_status(["CANCELLED"], None) == "IDLE"


# ── AT-960-21-3：狀態檔讀不動 ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("how", ["corrupt", "missing"])
def test_AT_960_21_3_an_unreadable_state_file_is_not_evaluable_and_never_consistent(
        env: Env, how: str) -> None:
    rid, _head, ws = seeded(env, how)
    target = state_file(env, rid)
    if how == "corrupt":
        target.write_text("current_state: [unclosed\n  - {broken: yaml\n", encoding="utf-8")
    else:
        target.unlink()
    before = target.read_bytes() if target.exists() else None
    result = reconcile(env, rid)
    item = next(c for c in result["checks"] if c["id"] == "fsm_flow_mapping")
    assert (item["status"], item["detail"]) == ("NOT_EVALUABLE", "fsm_state_unreadable")
    assert result["consistent"] is False and result["driftCount"] >= 1
    assert all(c["status"] == "ok" for c in result["checks"] if c["id"] != "fsm_flow_mapping")
    assert (target.read_bytes() if target.exists() else None) == before, "不修改狀態檔"
    assert ws.is_dir()


# ── AT-960-21-4：Gate 0 時點的自動對帳；對帳耗時 ─────────────────────────────────────────────
def test_AT_960_21_4_gate_0_runs_exactly_one_reconcile_and_p95_stays_under_two_seconds(
        env: Env) -> None:
    rid, _head, ws = seeded(env)
    for number in range(2, 21):                       # 共 20 個產物檔：矩陣的歷史版本各一個檔
        register(env, rid, "EVIDENCE_MATRIX", f"00_research/matrix-v{number}.md",
                 f"# 矩陣 v{number}\n", version=number)
    assert len([p for p in ws.rglob("*") if p.is_file()]) >= 20
    assert approve(env, rid, seen(env, rid, BASELINE_REL, MATRIX_REL), approver=ADMIN
                   ).status_code == 200
    assert len(reconcile_events(env, rid)) == 1, "Gate 0 核准流程內恰一筆對帳事件"
    event = reconcile_events(env, rid)[0]
    assert event["payload"]["driftCount"] == 0 and event["occurred_at"] is not None
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        reconcile(env, rid)
        elapsed.append(time.perf_counter() - started)
    p95 = sorted(elapsed)[int(len(elapsed) * 0.95) - 1]
    print(f"AT-960-21-4 reconcile P95={p95:.3f}s max={max(elapsed):.3f}s "
          f"calls={len(elapsed)} files={len([p for p in ws.rglob('*') if p.is_file()])}")
    assert p95 <= 2.0, f"對帳 P95 {p95:.3f}s 超過 2 秒"


def test_AT_960_21_4_p0_has_only_the_gate_0_call_site_for_reconcile() -> None:
    """分流與交付時點屬 P1／P2：P0 的 app 內只有 Gate 0（approve）與手動端點呼叫對帳。"""
    sites = []
    for path in sorted((ENGINE_BRIDGE / "app").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"orchestrator\.reconcile\(|\.reconcile\(", line) and "def " not in line:
                sites.append(f"{path.relative_to(ENGINE_BRIDGE).as_posix()}:{number}")
    assert sorted(s.split(":")[0] for s in sites) == ["app/routers/research.py"] * 2, sites


# ── AT-960-21-5：state.json 只寫出、不讀回 ──────────────────────────────────────────────────
READ_FORMS = {
    ".py": re.compile(r"read_text\(|read_bytes\(|\bopen\(|json\.load"),
    ".java": re.compile(r"Files\.read|readString|readAllBytes|FileReader|readValue|readTree"),
    ".ts": re.compile(r"readFile|readFileSync|JSON\.parse|\bfetch\(|import\(.*state\.json"),
}
READ_FORMS[".tsx"] = READ_FORMS[".ts"]
#: 允許讀 `state.json` 的模組（對帳與診斷顯示）；P0 一個都沒有。
ALLOWED_READERS: frozenset[str] = frozenset()
MENTION = re.compile(r"state\.json|STATE_JSON_REL")


def read_sites(name: str, text: str) -> list[str]:
    """一個檔案內「提到 `state.json` 的行，前後兩行內出現讀取形態」的位置。"""
    pattern = READ_FORMS.get(Path(name).suffix)
    if pattern is None:
        return []
    lines = text.splitlines()
    return [f"{name}:{i + 1}" for i, line in enumerate(lines) if MENTION.search(line)
            and any(pattern.search(x) for x in lines[max(0, i - 2): i + 3])]


def product_sources() -> list[Path]:
    roots = [(ENGINE_BRIDGE / "app", "*.py"),
             (AGENT_CONSOLE / "backend" / "src" / "main", "*.java"),
             (AGENT_CONSOLE / "frontend" / "app", "*.ts*"),
             (AGENT_CONSOLE / "frontend" / "components", "*.ts*"),
             (AGENT_CONSOLE / "frontend" / "lib", "*.ts*")]
    files: list[Path] = []
    for root, glob in roots:
        files += [p for p in root.rglob(glob) if "node_modules" not in p.parts
                  and not re.search(r"\.(test|spec)\.tsx?$", p.name)]
    return files


def test_AT_960_21_5_the_scanner_reports_read_samples_and_its_scope_is_not_empty() -> None:
    samples = {
        "a.py": "p = ws / 'state.json'\ndata = json.loads(p.read_text())\n",
        "b.py": "with open(STATE_JSON_REL) as fh:\n    pass\n",
        "C.java": 'var s = Files.readString(root.resolve("state.json"));\n',
        "d.ts": 'const v = JSON.parse(await readFile("state.json"));\n',
        "e.tsx": 'const r = await fetch("/x/state.json");\n'}
    for name, text in samples.items():
        assert read_sites(name, text), f"負控：{name} 的讀取樣本必須被回報"
    assert read_sites("w.py", "layout.write_workspace_file(ws, STATE_JSON_REL, text)\n") == []
    scanned = product_sources()
    assert len([p for p in scanned if p.suffix == ".py"]) >= 20 and len(scanned) >= 100


def test_AT_960_21_5_no_product_module_reads_state_json_outside_the_whitelist() -> None:
    hits: list[str] = []
    for path in product_sources():
        rel = path.relative_to(AGENT_CONSOLE).as_posix()
        if rel not in ALLOWED_READERS:
            hits += read_sites(rel, path.read_text(encoding="utf-8"))
    assert hits == [], f"state.json 只被寫出、不被當輸入：{hits}"


def test_AT_960_21_5_state_json_is_rewritten_after_a_step_transition_and_after_an_fsm_read(
        env: Env) -> None:
    rid, _head, ws = seeded(env)
    target = ws / layout.STATE_JSON_REL
    assert not target.exists()
    resp = env.post(f"/research/projects/{rid}:return", {"approver": ADMIN, "reason": "補證據"})
    assert resp.status_code == 200, resp.text            # 步驟轉移：HUMAN_PENDING 內游標回 REVISING
    first = target.read_text(encoding="utf-8")
    import json

    doc = json.loads(first)
    assert set(doc) >= {"research_id", "flow", "fsm", "runs", "projected_at"}
    assert doc["research_id"] == rid and set(doc["flow"]) == {"step", "phase", "status"}
    assert (doc["flow"]["step"], doc["flow"]["phase"]) == ("studio", "REVISING")
    assert set(doc["fsm"]) == {"project", "state", "updated_at", "frozen_stages"}
    assert doc["fsm"]["project"] == project_row(env, rid)["fsm_project"]
    assert doc["fsm"]["state"] == "HUMAN_PENDING" and isinstance(doc["runs"], list)
    target.unlink()                                       # 刪掉後一次 FSM 讀取（投影）就重寫出來
    env.live.app.state.research.orchestrator.project_state(rid)
    again = json.loads(target.read_text(encoding="utf-8"))
    assert again["projected_at"] >= doc["projected_at"] and again["flow"] == doc["flow"]
    assert again["fsm"] == doc["fsm"] and again["research_id"] == rid
