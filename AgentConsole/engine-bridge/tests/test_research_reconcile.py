"""對帳（TCS-ResearchToPRD-P0 AC-960-21；PRD §5.1.1；D-56）。

`:reconcile` 只報告、不修復；游標與 FSM 的對映由表驅動（`FLOW_FSM_MAPPING`）；`state.json` 只被
寫出、不被當輸入。專案以資料庫與 FSM 直接播種（同 `test_research_approve.py` 的 Given），
FSM 樹有 `fake` 與 `real` 兩種。
"""
from __future__ import annotations

import hashlib
import itertools
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
    mapping_check,
    prd_save_cursor,
)
from app.research.orchestrator import MATRIX_REL, REVIEW_CARD_REL
from tests import test_research_router as router_tests
from tests.test_research_approve import (
    ADMIN,
    ADR_REL,
    BASELINE_REL,
    PRD_TEXT,
    SCOPE_REL,
    approve,
    seed_pending,
    seen,
    state_file,
    workspace,
)
from tests.test_research_router import ALICE, Env, create, project_row, tree_digest

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
    ("AGENT_LOAD", "studio", "REVISING"),       # 換世代（D-60）之後：新鍵 AGENT_LOAD、PRD 修訂中
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
    # 表驅動：表外的任何組合一律假；`flow_status` 不是輸入（只有 D-77 的 FAILED 一個例外，
    # 見下一個測試）
    for state in ("INIT", "SPEC_FROZEN", "ESCALATION_FINAL"):
        for step in ("topic", "studio", "route", "bogus"):
            for phase in ("INGESTED", "REVIEWING", "FROZEN", "BOGUS"):
                assert flow_fsm_mapping_ok(state, step, phase) is ((state, step, phase) in accepted)
    # 衍生函式（優先序 ESCALATED > RUNNING > FAILED > WAITING_HUMAN > IDLE；FAILED 由呼叫端明說）
    assert derive_flow_status(["RUNNING"], "ESCALATION") == "ESCALATED"
    assert derive_flow_status(["QUEUED"], "HUMAN_PENDING") == "RUNNING"
    assert derive_flow_status(["SUCCEEDED", "FAILED"], "HUMAN_PENDING") == "WAITING_HUMAN"
    assert derive_flow_status([], "SCG_VALIDATION") == "IDLE"
    assert derive_flow_status(["CANCELLED"], None) == "IDLE"
    assert derive_flow_status([], "HUMAN_PENDING", last_run_failed=True) == "FAILED"


def test_D_77_a_failed_cursor_is_legal_for_every_fsm_state_in_the_table_and_only_those() -> None:
    """D-77：`flow_status=FAILED` 的游標對表內的每個 FSM 現態都合法（失敗時相態退回穩定相態，不必與
    已被推進的 FSM 對得上）；表外現態與讀不到（None）照舊不合法；其他狀態值不享有這個待遇。"""
    for state in FLOW_FSM_MAPPING:
        for step, phase in (("topic", "INGESTED"), ("studio", "DRAFTING"), ("route", "FROZEN"),
                            ("studio", "NO_SUCH_PHASE")):
            assert flow_fsm_mapping_ok(state, step, phase, "FAILED") is True, (state, step, phase)
    assert flow_fsm_mapping_ok("NO_SUCH_STATE", "topic", "INGESTED", "FAILED") is False
    assert flow_fsm_mapping_ok(None, "topic", "INGESTED", "FAILED") is False
    for status in ("IDLE", "RUNNING", "WAITING_HUMAN", "BLOCKED", "ESCALATED", "CANCELLED", None):
        assert flow_fsm_mapping_ok("SCG_VALIDATION", "studio", "DRAFTING", status) is False, status
        assert flow_fsm_mapping_ok("SCG_VALIDATION", "studio", "REVIEWING", status) is True
    drift = mapping_check("SCG_VALIDATION", "studio", "DRAFTING", readable=True)
    assert drift["status"] == "drift" and drift["drift"][0]["kind"] == "FSM_FLOW"
    assert mapping_check("SCG_VALIDATION", "studio", "DRAFTING", readable=True,
                         flow_status="FAILED")["status"] == "ok"
    unreadable = mapping_check("SCG_VALIDATION", "studio", "DRAFTING", readable=False,
                               flow_status="FAILED")
    assert unreadable["status"] == "NOT_EVALUABLE", "量不到仍不得 false-green"


# ── INT-05：人工存 PRD 之後的游標（純函式表）──────────────────────────────────────────────────
SAVE_CURSOR_TABLE = [
    # (FSM 現態, 現在的 step, phase) → 存稿後的 (step, phase)
    ("AGENT_LOAD", "topic", "INGESTED", ("topic", "INGESTED")),             # 研究步驟：保持
    ("AGENT_LOAD", "topic", "EVIDENCE_READY", ("topic", "EVIDENCE_READY")),
    ("AGENT_LOAD", "studio", "REVISING", ("studio", "REVISING")),           # 換世代之後：保持
    ("SPEC_DRAFTING", "studio", "DRAFTING", ("studio", "DRAFTING")),
    ("SPEC_DRAFTING", "studio", "REVISING", ("studio", "REVISING")),        # 合法就保持
    ("SPEC_DRAFTING", "studio", "REVIEWING", ("studio", "DRAFTING")),       # 不合法：DRAFTING 優先
    ("SPEC_DRAFTING", "topic", "EVIDENCE_READY", ("studio", "DRAFTING")),
    ("SCG_VALIDATION", "studio", "REVIEWING", ("studio", "REVIEWING")),
    ("SCG_VALIDATION", "studio", "DRAFTING", ("studio", "REVIEWING")),      # 只有 REVIEWING 合法
    ("HUMAN_PENDING", "studio", "GATE0_PENDING", ("studio", "REVISING")),   # 不再等 Gate 0
    ("HUMAN_PENDING", "studio", "REVISING", ("studio", "REVISING")),
    ("HUMAN_PENDING", "studio", "DRAFTING", ("studio", "REVISING")),        # DRAFTING 不合法
    ("SPEC_REGRESSION_CHECK", "studio", "GATE0_PENDING", ("studio", "REVISING")),
    ("ESCALATION", "studio", "REVIEWING", ("studio", "REVIEWING")),
    ("ESCALATION", "studio", "DRAFTING", ("studio", "REVISING")),
    ("NO_SUCH_STATE", "studio", "DRAFTING", ("studio", "DRAFTING")),        # 查無該態：不改
    (None, "topic", "INGESTED", ("topic", "INGESTED")),                      # FSM 讀不到：不改
    (None, "studio", "GATE0_PENDING", ("studio", "REVISING")),          # 僅「不再等 Gate 0」照降
]


@pytest.mark.parametrize("fsm_state, step, phase, expected", SAVE_CURSOR_TABLE)
def test_INT_05_a_human_save_lands_on_a_phase_the_fsm_state_allows(
        fsm_state: str | None, step: str, phase: str, expected: tuple[str, str]) -> None:
    got = prd_save_cursor(fsm_state, step, phase)
    assert got == expected
    if fsm_state in FLOW_FSM_MAPPING:               # 表內現態：結果一律合法（不固定寫 DRAFTING）
        assert flow_fsm_mapping_ok(fsm_state, *got) is True


def test_INT_05_a_human_save_while_waiting_for_gate_0_leaves_the_reconcile_consistent(
        env: Env) -> None:
    """HUMAN_PENDING 下 `PUT prd`（人在 Gate 0 前改稿）之後，游標是該態的合法對映（REVISING，不是對
    HUMAN_PENDING 不合法的 DRAFTING），`:reconcile` 仍是 `consistent: true`、零漂移。"""
    rid, _head, _ws = seeded(env)
    assert reconcile(env, rid)["consistent"] is True
    head = env.db.head_prd(rid)
    assert head is not None
    saved = env.put(f"/research/projects/{rid}/prd", {
        "base_version": int(head["version_no"]), "content": PRD_TEXT + "\n改了一行。\n",
        "author": ALICE})
    assert saved.status_code == 201, saved.text
    row = project_row(env, rid)
    assert (row["flow_step"], row["flow_phase"], row["flow_status"]) == (
        "studio", "REVISING", "WAITING_HUMAN")
    result = reconcile(env, rid)
    assert (result["consistent"], result["driftCount"]) == (True, 0), result


# ── INT-10：凍結的四份文件，每檔一個漂移列、kind 依檔、不重複計入 ─────────────────────────────────
FROZEN_KINDS = {BASELINE_REL: "PRD", MATRIX_REL: "EVIDENCE_MATRIX", SCOPE_REL: "ISSUE_SCOPE",
                ADR_REL: "ADR_DRAFT"}


def test_INT_10_each_frozen_file_is_one_drift_with_its_own_kind_and_is_never_counted_twice(
        env: Env) -> None:
    rid, _head, ws = seeded(env)
    assert approve(env, rid, seen(env, rid, BASELINE_REL, MATRIX_REL),
                   approver=ADMIN).status_code == 200
    clean = reconcile(env, rid)
    assert (clean["consistent"], clean["driftCount"]) == (True, 0), clean
    combos = [(rel,) for rel in FROZEN_KINDS] + list(itertools.combinations(FROZEN_KINDS, 2))
    for combo in combos:
        original = {rel: (ws / rel).read_bytes() for rel in combo}
        for rel in combo:
            (ws / rel).write_bytes(original[rel] + b"!")
        result = reconcile(env, rid)
        checks = {c["id"]: c for c in result["checks"]}
        found = sorted((d["kind"], d["path"]) for c in result["checks"] for d in c["drift"])
        assert found == sorted((FROZEN_KINDS[rel], rel) for rel in combo), combo
        assert result["driftCount"] == len(combo) and result["consistent"] is False, (
            combo, result["driftCount"])
        assert sorted(d["path"] for d in checks["prd_sha256"]["drift"]) == sorted(
            rel for rel in combo if rel != MATRIX_REL), "矩陣不在 prd_sha256 重複計入"
        assert (checks["evidence_matrix"]["status"] == "drift") is (MATRIX_REL in combo), combo
        for rel in combo:
            (ws / rel).write_bytes(original[rel])
    assert reconcile(env, rid)["driftCount"] == 0, "還原後回到零漂移"


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
    """對帳的呼叫點只住 `routers/research.py`：Gate 0（approve）、手動端點，加 P1 的分流時點助手
    `reconcile_at_route`（AC-961-20；只增呼叫點，檔案不變）。"""
    sites = []
    for path in sorted((ENGINE_BRIDGE / "app").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"orchestrator\.reconcile\(|\.reconcile\(", line) and "def " not in line:
                sites.append(f"{path.relative_to(ENGINE_BRIDGE).as_posix()}:{number}")
    assert sorted(s.split(":")[0] for s in sites) == ["app/routers/research.py"] * 3, sites


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


# ══ P1 BR-D2：route_decision／task_decomposition 兩項、對映表、TCS 凍結後校正（AC-961-20、25）══
from app.research.gates.reconcile import (  # noqa: E402
    PENDING_CORRECTION,
    flow_fsm_mapping_verdict,
)
from tests import research_git_support as rgs  # noqa: E402
from tests.test_decompose import step as brain_step  # noqa: E402
from tests.test_research_decompose import (  # noqa: E402
    FakeBrain,
    post_decompose,
    use_brain,
)
from tests.test_research_scr import cli, inner, routed  # noqa: E402

route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
P1_RESEARCH_FILES = ("02_governance/route_decision.json", "03_execution/task_decomposition.json")


def checks_of(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in result["checks"]}


def p1_reconcile(renv: rgs.RouteEnv, rid: str) -> dict[str, Any]:
    resp = renv.env.post(f"/research/projects/{rid}:reconcile", {})
    assert resp.status_code == 200, resp.text
    return dict(resp.json())


def p1_workspace(renv: rgs.RouteEnv, rid: str) -> Path:
    return Path(renv.env.db.get_project(rid)["workspace_path"])


def test_AT_961_20_3_the_mapping_table_has_the_p1_db_cursor_values_and_a_third_state() -> None:
    def verdict(fsm: str, step_: str, phase: str, stage2: bool = False) -> str:
        return flow_fsm_mapping_verdict(fsm, step_, phase, stage2_frozen=stage2)

    for step_, phase in (("route", "FROZEN"), ("route", "ROUTING"), ("build", "ROUTED"),
                         ("build", "TCS_DRAFTING"), ("build", "TCS_PENDING"),
                         ("studio", "SCR_OPEN")):
        assert verdict("SPEC_FROZEN", step_, phase) == "ok", (step_, phase)
    assert verdict("SPEC_FROZEN", "build", "TCS_PENDING", True) == PENDING_CORRECTION
    assert verdict("SPEC_FROZEN", "build", "ROUTED", True) == "ok"
    for step_, phase in (("studio", "DRAFTING"), ("topic", "INGESTED"),
                         ("build", "BUILD_READY"), ("build", "PAUSED")):
        assert verdict("SPEC_FROZEN", step_, phase) == "drift", (step_, phase)
    for fsm in ("SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING"):
        assert verdict(fsm, "studio", "SCR_OPEN") == "ok", fsm
    assert verdict("ESCALATION", "route", "FROZEN") == "drift"
    assert verdict("SPEC_DRAFTING", "route", "FROZEN") == "drift"
    assert "BUILD_READY" not in {p for m in FLOW_FSM_MAPPING.values() for ps in m.values()
                                 for p in ps} and "PAUSED" not in str(FLOW_FSM_MAPPING)
    assert flow_fsm_mapping_ok("SPEC_FROZEN", "route", "FROZEN")      # P0 既有結果不變
    check = mapping_check("SPEC_FROZEN", "build", "TCS_PENDING", readable=True,
                          stage2_frozen=True)
    assert check["status"] == PENDING_CORRECTION and check["drift"] == []


def test_AT_961_20_1_route_decision_is_compared_with_its_registered_sha(
        renv: rgs.RouteEnv) -> None:
    other = rgs.seed_gate0(renv, "plain")
    assert checks_of(p1_reconcile(renv, other))["route_decision"] == {
        "id": "route_decision", "status": "ok", "present": False, "detail": "", "drift": []}
    rid, _route = routed(renv)
    result = p1_reconcile(renv, rid)
    assert checks_of(result)["route_decision"]["status"] == "ok"
    assert checks_of(result)["route_decision"]["present"] is True and result["consistent"]
    assert [c["id"] for c in result["checks"]] == list(CHECK_IDS), "對帳項名與順序以 CHECK_IDS 為準"
    path = p1_workspace(renv, rid) / P1_RESEARCH_FILES[0]
    original = path.read_bytes()
    path.write_bytes(original + b" ")
    drift = checks_of(p1_reconcile(renv, rid))["route_decision"]
    assert drift["status"] == "drift" and drift["drift"][0]["kind"] == "ROUTE_DECISION"
    assert drift["drift"][0]["actualSha256"] != drift["drift"][0]["expectedSha256"]
    path.write_bytes(original)
    path.unlink()
    gone = checks_of(p1_reconcile(renv, rid))["route_decision"]
    assert gone["status"] == "drift" and gone["drift"][0]["actualSha256"] is None
    events = [e for e in renv.rdb.events(rid) if e[1] == "research.reconcile"]
    assert len(events) == 5, "Gate 0 一筆＋分流成功時點一筆（AC-961-20-4）＋本測試三次手動各一筆"


def test_AT_961_20_1_field_level_route_drift_is_reported_without_touching_either_side(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    renv.rdb.exec("UPDATE console.research_projects SET updated_at = updated_at WHERE id = %s",
                  rid)
    before = tree_digest(p1_workspace(renv, rid))
    counts = {t: renv.rdb.count(t) for t in ("research_artifacts", "research_route_steps",
                                             "research_route_decisions", "research_scr",
                                             "research_decompositions")}
    result = p1_reconcile(renv, rid)
    assert result["consistent"] is True
    after = tree_digest(p1_workspace(renv, rid))
    assert {k: v for k, v in after.items() if not k.endswith("state.json")} == {
        k: v for k, v in before.items() if not k.endswith("state.json")}
    assert counts == {t: renv.rdb.count(t) for t in counts}
    assert route


def test_AT_961_20_2_task_decomposition_is_compared_with_its_registered_sha(
        renv: rgs.RouteEnv) -> None:
    from tests.test_research_decompose import PRD

    rid = rgs.seed_gate0(renv, prd=PRD)
    assert rgs.confirm(renv, rid, rgs.body_a(renv)).status_code == 200
    use_brain(renv, FakeBrain([brain_step(1), brain_step(2, ["S01"])]), renv.tmp)
    assert checks_of(p1_reconcile(renv, rid))["task_decomposition"]["present"] is False
    assert post_decompose(renv, rid).status_code == 200
    ok = checks_of(p1_reconcile(renv, rid))["task_decomposition"]
    assert ok["status"] == "ok" and ok["present"] is True
    path = p1_workspace(renv, rid) / P1_RESEARCH_FILES[1]
    original = path.read_bytes()
    path.write_bytes(original + b"\n")
    drift = checks_of(p1_reconcile(renv, rid))["task_decomposition"]
    assert drift["status"] == "drift" and drift["drift"][0]["kind"] == "TASK_DECOMPOSITION"
    path.write_bytes(original)
    renv.rdb.exec("UPDATE console.research_decompositions SET status = 'STALE' WHERE "
                  "research_id = %s", rid)
    assert checks_of(p1_reconcile(renv, rid))["task_decomposition"]["status"] == "ok", \
        "stale 不是 drift"
    path.unlink()
    assert checks_of(p1_reconcile(renv, rid))["task_decomposition"]["status"] == "drift"


def freeze_stage2(renv: rgs.RouteEnv, route: dict[str, Any]) -> None:
    """Given：內環鍵走完 Stage-2 並凍結（走框架 CLI，等同既有 `:freeze` 的結果）。"""
    key, sdir, root = route["impl_fsm_project"], route["impl_state_dir"], route["target_path"]
    rel = "docs/03_testing/contracts/TCS-demo-20261107.md"
    target = Path(root) / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# TCS\n", encoding="utf-8", newline="\n")
    trigger = ["--trigger", "research_bridge"]
    cli(renv, key, sdir, "transition", "--to", "SPEC_DRAFTING", "--reason", "stage-2", *trigger)
    cli(renv, key, sdir, "transition", "--to", "SCG_VALIDATION", "--reason", "stage-2", *trigger)
    cli(renv, key, sdir, "transition", "--to", "HUMAN_PENDING", "--reason", "tcs gate: x",
        *trigger)
    cli(renv, key, sdir, "spec-frozen", "--stage", "Stage-2", "--doc", rel, "--digest", "--root",
        root, "--reason", "tcs frozen", "--approver", ADMIN, "--json")


def to_tcs_pending(renv: rgs.RouteEnv, rid: str) -> None:
    renv.env.db.set_cursor(research_id=rid, actor="bridge", flow={
        "step": "build", "phase": "TCS_PENDING", "status": "IDLE", "detail": ""})


def test_AT_961_25_2_reconcile_corrects_a_tcs_pending_cursor_once_stage_2_is_frozen(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    freeze_stage2(renv, route)
    to_tcs_pending(renv, rid)
    before = len(renv.rdb.events(rid))
    first = p1_reconcile(renv, rid)
    mapping = checks_of(first)["fsm_flow_mapping"]
    assert mapping["status"] == PENDING_CORRECTION and mapping["drift"] == []
    assert first["consistent"] is True and first["driftCount"] == 0
    assert renv.rdb.one("SELECT flow_step, flow_phase, flow_status FROM "
                        "console.research_projects WHERE id = %s", rid) == (
        "build", "ROUTED", "IDLE")
    steps = [e for e in renv.rdb.events(rid)[before:] if e[1] == "research.step"]
    assert len(steps) == 1 and steps[0][6]["reason"] == "tcs_frozen_correction"
    assert steps[0][6]["flowPhase"] == "ROUTED"
    again = p1_reconcile(renv, rid)
    assert checks_of(again)["fsm_flow_mapping"]["status"] == "ok"
    later = [e for e in renv.rdb.events(rid)[before:] if e[1] == "research.step"]
    assert len(later) == 1, "第二次：無新校正事件（冪等）"
    assert fsm_state_file_untouched(route)


def fsm_state_file_untouched(route: dict[str, Any]) -> bool:
    return (Path(route["impl_state_dir"]) / f"FSM-STATE-{route['impl_fsm_project']}.yaml"
            ).is_file()


def test_AT_961_25_E_1_an_unfrozen_stage_2_is_never_corrected(renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    to_tcs_pending(renv, rid)
    cli(renv, route["impl_fsm_project"], route["impl_state_dir"], "transition", "--to",
        "SPEC_DRAFTING", "--reason", "stage-2", "--trigger", "research_bridge")
    for state in ("SPEC_DRAFTING", "HUMAN_PENDING"):
        if state == "HUMAN_PENDING":
            for to, reason in (("SCG_VALIDATION", "x"), ("HUMAN_PENDING", "tcs gate: x")):
                cli(renv, route["impl_fsm_project"], route["impl_state_dir"], "transition",
                    "--to", to, "--reason", reason, "--trigger", "research_bridge")
        assert inner(renv, route)
        steps_before = len([e for e in renv.rdb.events(rid) if e[1] == "research.step"])
        result = p1_reconcile(renv, rid)
        assert checks_of(result)["fsm_flow_mapping"]["status"] == "ok", state
        assert renv.rdb.one("SELECT flow_phase FROM console.research_projects WHERE id = %s",
                            rid) == ("TCS_PENDING",)
        assert len([e for e in renv.rdb.events(rid) if e[1] == "research.step"]) == steps_before


def test_AT_961_20_4_the_route_time_reconcile_helper_adds_exactly_one_event(
        renv: rgs.RouteEnv) -> None:
    from app.routers.research import reconcile_at_route

    rid, _route = routed(renv)
    ctx = renv.env.live.app.state.research
    before = len([e for e in renv.rdb.events(rid) if e[1] == "research.reconcile"])
    result = reconcile_at_route(ctx, rid)
    events = [e for e in renv.rdb.events(rid) if e[1] == "research.reconcile"]
    assert len(events) == before + 1
    assert result["consistent"] is True and events[-1][6] == {"consistent": True,
                                                                "driftCount": 0}


def test_AT_961_20_4_the_route_flow_itself_runs_one_automatic_reconcile(
        renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv)
    events = [e for e in renv.rdb.events(rid) if e[1] == "research.reconcile"]
    assert len(events) == 2, "Gate 0 時點一筆（P0）加分流成功時點一筆"
