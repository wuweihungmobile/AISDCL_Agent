"""拆解橋：逐 US 呼叫既有 `DecomposeService`、確定性綁定 AC、覆蓋對映、簽核與 stale（TCS
AT-961-10-*；PKG-BR-D2）。Brain 以 FakeBrain 替身（hermetic；不連網、不用 `MINIMAX_*`）。
"""
from __future__ import annotations

import ast
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from autoclaude.models.decision import DecompositionDecision, DecompositionStep

from app import sdd_cli
from app.decompose import DecomposeService, DraftStore
from app.research import decompose_plan
from tests import research_git_support as rgs
from tests import test_research_router as rt
from tests.test_decompose import FakeBrain, step
from tests.test_research_scr import ADMIN, cursor

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
FIXTURE = Path(__file__).parent / "fixtures" / "research" / "decompose" / "prd_three_us.md"
PRD = FIXTURE.read_text(encoding="utf-8")
ACS = ["AC-001-1", "AC-001-2", "AC-002-1", "AC-003-1", "AC-003-2"]


def use_brain(renv: rgs.RouteEnv, brain: FakeBrain, tmp: Path) -> FakeBrain:
    """把活 Bridge 的拆解服務換成吃 `brain` 的那一個（服務在 lifespan 建、之後每個請求才讀）。"""
    app = renv.env.live.app
    app.state.decompose = DecomposeService(
        renv.env.settings, app.state.audit, DraftStore(tmp / "_drafts"),
        brain_factory=lambda _cfg: brain)
    return brain


def decomposable(renv: rgs.RouteEnv, brain: FakeBrain) -> str:
    rid = rgs.seed_gate0(renv, prd=PRD)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 200, resp.text
    use_brain(renv, brain, renv.tmp)
    return rid


def post_decompose(renv: rgs.RouteEnv, rid: str, **scope: Any) -> Any:
    body: dict[str, Any] = {"requested_by": ADMIN}
    if scope:
        body["scope"] = scope
    return renv.env.post(f"/research/projects/{rid}:decompose", body)


def rows(renv: rgs.RouteEnv, rid: str) -> list[tuple[Any, ...]]:
    return renv.rdb.q("SELECT id::text, path, status, draft_id, prd_sha256, tasks_count, "
                      "gate_rejection, tcs_rel_path, tcs_sha256, import_record_id::text "
                      "FROM console.research_decompositions WHERE research_id = %s "
                      "ORDER BY created_at, id", rid)


def workspace(renv: rgs.RouteEnv, rid: str) -> Path:
    return Path(renv.env.db.get_project(rid)["workspace_path"])


def import_record(renv: rgs.RouteEnv) -> str:
    row = renv.rdb.one("INSERT INTO console.import_records (source_type, source_content) "
                       "VALUES ('BRD', 'x') RETURNING id")
    assert row is not None
    return str(row[0])


def brain3() -> FakeBrain:
    return FakeBrain([step(1), step(2, ["S01"])])


# ── AT-961-10-3：覆蓋對映（純函式）──────────────────────────────────────────────────────────
def test_AT_961_10_3_coverage_lists_uncovered_unknown_and_ignores_duplicates() -> None:
    def task(*acs: str) -> dict[str, Any]:
        return {"covers_ac": list(acs)}

    wanted = [f"AC-00{i}" for i in range(1, 6)]
    assert decompose_plan.coverage(wanted, [task(*wanted)]) == {
        "total": 5, "covered": 5, "uncovered": [], "unknown_ac": []}
    assert decompose_plan.coverage(wanted, [task("AC-001", "AC-002", "AC-003")])[
        "uncovered"] == ["AC-004", "AC-005"]
    assert decompose_plan.coverage(wanted, [task("AC-001", "AC-999")])["unknown_ac"] == [
        "AC-999"]
    assert decompose_plan.coverage(wanted, [task("AC-001"), task("AC-001")])["covered"] == 1
    assert decompose_plan.coverage(wanted, [task()])["uncovered"] == wanted


def test_the_prd_parser_counts_ac_headings_and_binds_each_story() -> None:
    prd = decompose_plan.parse_prd(PRD)
    assert list(prd.acs) == ACS
    assert [(s.us_id, s.acs) for s in prd.stories] == [
        ("US-001", ("AC-001-1", "AC-001-2")), ("US-002", ("AC-002-1",)),
        ("US-003", ("AC-003-1", "AC-003-2"))]
    assert [b.key for b in decompose_plan.plan_batches(prd, "us")] == [
        "US-001", "US-002", "US-003"]
    goal = decompose_plan.plan_batches(prd, "goal")
    assert [(b.key, b.us_ids) for b in goal] == [
        ("F-001", ("US-001", "US-002")), ("F-002", ("US-003",))]
    assert goal[0].acs == ("AC-001-1", "AC-001-2", "AC-002-1")
    assert decompose_plan.plan_batches(prd, "all")[0].acs == tuple(ACS)
    assert [b.key for b in decompose_plan.plan_batches(prd, "us", ["US-002"])] == ["US-002"]


# ── AT-961-10-1：觸發拆解 ────────────────────────────────────────────────────────────────────
def test_AT_961_10_1_decompose_binds_covers_ac_deterministically_and_writes_r8(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    brain = brain3()
    rid = decomposable(renv, brain)
    seen: list[str] = []
    real = sdd_cli.run_research_verb
    monkeypatch.setattr(sdd_cli, "run_research_verb",
                        lambda verb, *a, **k: (seen.append(verb), real(verb, *a, **k))[1])
    before_cursor = cursor(renv, rid)
    resp = post_decompose(renv, rid)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "DRAFTED" and body["tasks_count"] == 6
    assert body["coverage"] == {"total": 5, "covered": 5, "uncovered": [], "unknown_ac": []}
    assert len(brain.calls) == 3, "逐 US 各呼叫一次"
    assert "AC-001-1" in brain.calls[0][1] and "AC-003-2" in brain.calls[2][1]
    [row] = rows(renv, rid)
    assert row[1:3] == ("C", "DRAFTED") and row[5] == 6 and row[6] is None
    assert row[0] == body["decomposition_id"] and row[3]
    digests = renv.env.db.gate0_digests(rid) or {}
    assert row[4] == digests["01_specs/PRD-v1.0.0.md"], "prd_sha256＝凍結摘要中的 PRD 項"
    ws = workspace(renv, rid)
    text = (ws / "03_execution" / "task_decomposition.json").read_text(encoding="utf-8")
    doc = json.loads(text)
    assert doc["signed_off"] is False and doc["prd_sha256"] == row[4]
    assert doc["coverage"] == {"total": 5, "covered": 5, "uncovered": []}, "D-133 頂層 coverage"
    assert [g["goal_id"] for g in doc["goals"]] == ["G-1", "G-2", "G-3"]
    assert len(doc["draft_ids"]) == 3 and doc["draft_ids"][0] == row[3]
    by_us = {t["covers_us"][0]: t["covers_ac"] for g in doc["goals"] for t in g["tasks"]}
    assert by_us == {"US-001": ["AC-001-1", "AC-001-2"], "US-002": ["AC-002-1"],
                     "US-003": ["AC-003-1", "AC-003-2"]}
    art = renv.rdb.one("SELECT sha256, version, content FROM console.research_artifacts WHERE "
                       "research_id = %s AND kind = 'TASK_DECOMPOSITION'", rid)
    assert art is not None and art[0].strip() == decompose_plan.layout.sha256_text(text)
    assert art[1] == 1 and art[2] == text
    assert cursor(renv, rid) == before_cursor == ("build", "ROUTED", "IDLE", "")
    assert [v for v in seen if v] == [], "拆解不呼叫任何 FSM 動詞"
    snap = [e for e in renv.rdb.events(rid) if e[1] == "research.step"][-1]
    assert snap[6]["flowPhase"] == "ROUTED"


# ── AT-961-10-2：三道有界閘 ──────────────────────────────────────────────────────────────────
GATE_CASES = [
    ("max_steps", [step(i) for i in range(1, 26)]),
    ("cycle", [step(1, ["S02"]), step(2, ["S01"])]),
    ("empty_prompt", [step(1), step(2, ["S01"], prompt="")]),
    ("brain_failed", None),
]


@pytest.mark.parametrize(("gate", "steps"), GATE_CASES, ids=[c[0] for c in GATE_CASES])
def test_AT_961_10_2_a_failed_gate_is_a_structured_422_and_a_rejected_row(
        renv: rgs.RouteEnv, gate: str, steps: list[DecompositionStep] | None) -> None:
    rid = decomposable(renv, FakeBrain(steps))
    resp = post_decompose(renv, rid)
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    violation = resp.json()["violations"][0]
    assert violation["rule"] == gate and violation["detail"] is not None
    [row] = rows(renv, rid)
    assert row[2] == "REJECTED" and row[6] == gate and row[5] == 0
    assert not (workspace(renv, rid) / "03_execution" / "task_decomposition.json").exists()
    assert renv.rdb.count("research_artifacts", "kind = 'TASK_DECOMPOSITION'") == 0
    assert cursor(renv, rid)[:2] == ("build", "ROUTED")


def test_AT_961_10_2_brain_unsupported_is_reported_with_its_own_gate(
        renv: rgs.RouteEnv) -> None:
    rid = decomposable(renv, FakeBrain([step(1)], supports=False))
    resp = post_decompose(renv, rid)
    assert resp.status_code == 422 and resp.json()["violations"][0]["rule"] == "brain_unsupported"


def test_AT_961_10_2_exactly_24_steps_pass(renv: rgs.RouteEnv) -> None:
    steps = [step(1)] + [step(i, [f"S{i - 1:02d}"]) for i in range(2, 25)]
    rid = decomposable(renv, FakeBrain(steps))
    assert post_decompose(renv, rid, by="all").status_code == 200


def test_AT_961_10_2_preconditions_are_409_without_writes(renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv, prd=PRD)                      # 尚未分流
    use_brain(renv, brain3(), renv.tmp)
    resp = post_decompose(renv, rid)
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert rows(renv, rid) == []


# ── AT-961-10-8：按 Goal 分批 ────────────────────────────────────────────────────────────────
def test_AT_961_10_8_a_whole_prd_over_24_steps_is_rejected_but_per_goal_batches_pass(
        renv: rgs.RouteEnv) -> None:
    class PerCall(FakeBrain):
        """整份 PRD 單次回 60 步（逾 24）；其餘每批回 20 步。"""

        def __init__(self) -> None:
            super().__init__(None)

        def decide_decomposition(self, *, goal: str, context: str = "") -> Any:
            self.calls.append((goal, context))
            count = 60 if "整份 PRD" in context else 20
            return DecompositionDecision(steps=[step(i) for i in range(1, count + 1)],
                                         reasoning="x")
    rid = decomposable(renv, PerCall())
    whole = post_decompose(renv, rid, by="all")
    assert whole.status_code == 422 and whole.json()["violations"][0]["rule"] == "max_steps"
    batched = post_decompose(renv, rid, by="goal")
    assert batched.status_code == 200, batched.text
    assert batched.json()["tasks_count"] == 40, "兩個 Feature 各 20 步、合併後可超過 24"
    assert batched.json()["coverage"]["uncovered"] == []


# ── AT-961-10-4：簽核 ────────────────────────────────────────────────────────────────────────
def signoff(renv: rgs.RouteEnv, rid: str, did: str, **over: Any) -> Any:
    # imported_tasks_count（D-143(3)）：夾具預設＝該拆解列的 tasks_count
    # （console-api 落成數與 JSON task 數同源）
    landed = next(r[5] for r in rows(renv, rid) if r[0] == did)
    body: dict[str, Any] = {"decomposition_id": did, "import_record_id": import_record(renv),
                            "console_project_id": str(uuid.uuid4()), "approver": ADMIN,
                            "imported_tasks_count": landed}
    body.update(over)
    return renv.env.post(f"/research/projects/{rid}:decomposition-signoff", body)


def partial_decomposition(renv: rgs.RouteEnv) -> tuple[str, str]:
    """只拆一個 US（by us、us_ids=[US-001]）：AC-002-1、AC-003-1、AC-003-2 三個未覆蓋。"""
    rid = decomposable(renv, brain3())
    resp = post_decompose(renv, rid, us_ids=["US-001"])
    assert resp.status_code == 200 and resp.json()["coverage"]["uncovered"] == [
        "AC-002-1", "AC-003-1", "AC-003-2"]
    return rid, resp.json()["decomposition_id"]


def test_AT_961_10_4_uncovered_acs_need_valid_waivers_before_signoff(
        renv: rgs.RouteEnv) -> None:
    rid, did = partial_decomposition(renv)
    miss = signoff(renv, rid, did)
    assert (miss.status_code, miss.json()["reason"]) == (422, "invalid_request")
    assert {v["ac"] for v in miss.json()["violations"]} == {"AC-002-1", "AC-003-1", "AC-003-2"}
    assert rows(renv, rid)[0][2] == "DRAFTED"
    waive = [{"ac": ac, "reason": "人工豁免"} for ac in ("AC-002-1", "AC-003-1")]
    partly = signoff(renv, rid, did, waivers=waive)
    assert [v["ac"] for v in partly.json()["violations"]] == ["AC-003-2"]
    bad_reason = signoff(renv, rid, did, waivers=[*waive, {"ac": "AC-003-2", "reason": ""}])
    assert bad_reason.status_code == 422
    too_long = signoff(renv, rid, did, waivers=[*waive, {"ac": "AC-003-2", "reason": "x" * 501}])
    assert too_long.status_code == 422
    covered = signoff(renv, rid, did, waivers=[*waive, {"ac": "AC-001-1", "reason": "不需要"}])
    assert covered.status_code == 422 and covered.json()["violations"][0]["rule"] == (
        "waiver_ac_invalid")
    assert rows(renv, rid)[0][2] == "DRAFTED"
    ok = signoff(renv, rid, did, waivers=[*waive, {"ac": "AC-003-2", "reason": "x" * 500}])
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "SIGNED_OFF" and len(ok.json()["artifact_sha256"]) == 64
    [row] = rows(renv, rid)
    assert row[2] == "SIGNED_OFF" and row[9]
    doc = json.loads((workspace(renv, rid) / "03_execution" / "task_decomposition.json"
                      ).read_text(encoding="utf-8"))
    assert doc["signed_off"] is True and doc["signed_off_by"] == ADMIN and doc["signed_off_at"]
    assert [w["ac"] for w in doc["waivers"]] == ["AC-002-1", "AC-003-1", "AC-003-2"]
    assert all(w["by"] == ADMIN and w["at"] for w in doc["waivers"])
    art = renv.rdb.q("SELECT version, sha256 FROM console.research_artifacts WHERE research_id "
                     "= %s AND kind = 'TASK_DECOMPOSITION' ORDER BY version", rid)
    assert [a[0] for a in art] == [1, 2] and art[1][1].strip() == ok.json()["artifact_sha256"]
    again = signoff(renv, rid, did)
    assert (again.status_code, again.json()["reason"]) == (409, "fsm_state_conflict")
    assert again.json()["details"]["status"] == "SIGNED_OFF"


def test_AT_961_10_4_a_stale_prd_digest_is_409_and_approver_is_validated(
        renv: rgs.RouteEnv) -> None:
    rid, did = partial_decomposition(renv)
    bad = signoff(renv, rid, did, approver="bridge")
    assert bad.status_code == 422
    renv.rdb.exec("UPDATE console.research_decompositions SET status = 'DRAFTED' WHERE id = %s",
                  did)
    ws_sha = rows(renv, rid)[0][4]
    assert ws_sha
    # 摘要改變（以新的 Gate 決定列模擬）：拆解的 prd_sha256 不再等於現凍結摘要
    renv.rdb.exec(
        "INSERT INTO console.research_gate_decisions (research_id, gate, decision, decided_by, "
        "decided_at, fsm_project, fsm_stage, frozen_digests, reason) SELECT research_id, gate, "
        "decision, decided_by, now() + interval '1 minute', fsm_project, 'Gate-0-SCR1', "
        "jsonb_build_object("
        "'01_specs/PRD-v1.0.0.md', %s::text), '' FROM console.research_gate_decisions "
        "WHERE research_id = %s LIMIT 1", "sha256:" + "b" * 64, rid)
    stale = signoff(renv, rid, did, waivers=[{"ac": a, "reason": "r"} for a in (
        "AC-002-1", "AC-003-1", "AC-003-2")])
    assert (stale.status_code, stale.json()["reason"]) == (409, "decomposition_stale")
    assert rows(renv, rid)[0][2] == "DRAFTED"


# ── D-133：簽核對同一個 import 記錄冪等（不同記錄才 409）──────────────────────────────────────
def test_D_133_signoff_with_the_same_import_record_is_idempotent(renv: rgs.RouteEnv) -> None:
    rid, did = partial_decomposition(renv)
    waive = [{"ac": a, "reason": "r"} for a in ("AC-002-1", "AC-003-1", "AC-003-2")]
    record = import_record(renv)
    first = signoff(renv, rid, did, waivers=waive, import_record_id=record)
    assert first.status_code == 200, first.text
    events = len(renv.rdb.events(rid))
    versions = renv.rdb.count("research_artifacts", "kind = 'TASK_DECOMPOSITION'")
    again = signoff(renv, rid, did, waivers=waive, import_record_id=record)
    assert again.status_code == 200 and again.json() == first.json()
    assert len(renv.rdb.events(rid)) == events, "不重發事件"
    assert renv.rdb.count("research_artifacts", "kind = 'TASK_DECOMPOSITION'") == versions
    other = signoff(renv, rid, did, waivers=waive)            # 另一個 import 記錄
    assert (other.status_code, other.json()["reason"]) == (409, "fsm_state_conflict")


# ── AT-961-10-5、10-6、10-7：stale、對帳、重拆 ──────────────────────────────────────────────
def test_AT_961_10_5_mark_stale_keeps_the_signed_off_facts(renv: rgs.RouteEnv) -> None:
    rid, did = partial_decomposition(renv)
    ok = signoff(renv, rid, did, waivers=[{"ac": a, "reason": "r"} for a in (
        "AC-002-1", "AC-003-1", "AC-003-2")])
    assert ok.status_code == 200
    env = decompose_plan.DecomposeEnv(renv.env.db, renv.env.live.app.state.research.writer,
                                      renv.env.live.app.state.decompose)
    assert decompose_plan.mark_stale(env, rid) == 0, "摘要沒變＝不標"
    renv.rdb.exec(
        "INSERT INTO console.research_gate_decisions (research_id, gate, decision, decided_by, "
        "decided_at, fsm_project, fsm_stage, frozen_digests, reason) VALUES (%s, 'GATE0', "
        "'APPROVED', 'x', now() + interval '1 minute', 'k', 'Gate-0-SCR1', "
        "jsonb_build_object('01_specs/PRD-v1.1.0.md', %s::text), '')",
        rid, "sha256:" + "c" * 64)
    assert decompose_plan.mark_stale(env, rid) == 1
    [row] = rows(renv, rid)
    assert row[2] == "STALE" and row[4] != "c" * 64, "prd_sha256 不動（歷史）"
    doc = json.loads((workspace(renv, rid) / "03_execution" / "task_decomposition.json"
                      ).read_text(encoding="utf-8"))
    assert doc["signed_off"] is True and doc["signed_off_by"] == ADMIN
    assert decompose_plan.is_stale({"status": "STALE", "prd_sha256": "a"}, None)
    assert decompose_plan.is_stale({"status": "DRAFTED", "prd_sha256": "a"}, "b")
    assert not decompose_plan.is_stale({"status": "DRAFTED", "prd_sha256": "a"}, "a")


def test_AT_961_10_7_redecompose_is_a_new_row_that_inherits_the_tcs_columns(
        renv: rgs.RouteEnv) -> None:
    rid = decomposable(renv, brain3())
    first = post_decompose(renv, rid).json()["decomposition_id"]
    renv.rdb.exec("UPDATE console.research_decompositions SET tcs_rel_path = 'docs/x.md', "
                  "tcs_sha256 = %s WHERE id = %s", "d" * 64, first)
    second = post_decompose(renv, rid).json()["decomposition_id"]
    assert first != second
    old, new = rows(renv, rid)
    assert old[0] == first and old[2] == "DRAFTED", "甲版列不被改動"
    assert (new[7], new[8]) == ("docs/x.md", "d" * 64), "乙列承接 tcs 欄（D-110）"
    versions = renv.rdb.q("SELECT version FROM console.research_artifacts WHERE research_id = "
                          "%s AND kind = 'TASK_DECOMPOSITION' ORDER BY version", rid)
    assert versions == [(1,), (2,)]
    for statement in ("UPDATE console.research_decompositions SET prd_sha256 = %s WHERE id = %s",):
        with pytest.raises(Exception, match="research"):
            renv.rdb.exec(statement, "e" * 64, first)
    with pytest.raises(Exception, match="research"):
        renv.rdb.exec("DELETE FROM console.research_decompositions WHERE id = %s", first)


# ── AT-961-10-E-1：planner 不得繞過人工 signoff ────────────────────────────────────────────
def test_AT_961_10_E_1_no_code_path_writes_a_literal_true_signed_off() -> None:
    src = Path(decompose_plan.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if (isinstance(key, ast.Constant) and key.value == "signed_off"
                        and isinstance(value, ast.Constant)):
                    assert value.value is False, "字面真值的 signed_off 賦值必須為 0 處"


def test_decomposition_documents_are_never_signed_off_when_built_by_the_planner() -> None:
    doc = decompose_plan.build_document(research_ref="RP-0001", version=1, prd_semver="v1.0.0",
                                        prd_sha256="a" * 64, goals=[], draft_ids=[])
    assert doc["signed_off"] is False and doc["signed_off_by"] is None
    assert doc["waivers"] == [] and doc["limits"] == {"max_steps_per_goal": 24}


def test_signoff_rejects_a_missing_or_malformed_imported_tasks_count(renv: rgs.RouteEnv) -> None:
    rid, did = partial_decomposition(renv)
    waive = [{"ac": a, "reason": "r"} for a in ("AC-002-1", "AC-003-1", "AC-003-2")]
    for bad in (None, -1, "2", 1.5, True):
        resp = signoff(renv, rid, did, waivers=waive, imported_tasks_count=bad)
        assert resp.status_code == 422, (bad, resp.text)
        assert resp.json()["reason"] == "invalid_request"
        assert resp.json()["violations"][0]["field"] == "imported_tasks_count", bad
    assert rows(renv, rid)[0][2] == "DRAFTED", "被拒＝零寫入"


# ── AT-961-10-6：DB 與檔案逐欄相等（Bridge 側可驗的部分）────────────────────────────────────────
def test_AT_961_10_6_file_sha_row_count_and_json_task_count_agree_and_drift_is_reported_only(
        renv: rgs.RouteEnv) -> None:
    """三方相等（檔 sha＝登記列＝JSON task 數），並（D-143(3)）簽核本文的 `imported_tasks_count`
    （console-api 匯入落成的正式 tasks 數）記進簽核版 artifact 與回應，
    且與 `tasks_count`、JSON task 數相等。
    不相等時的處置 TCS 未定（勘誤候選），這裡不自定 reason。"""
    import hashlib
    rid, did = partial_decomposition(renv)
    [pre] = rows(renv, rid)
    target = workspace(renv, rid) / "03_execution" / "task_decomposition.json"
    # F-14：傳入值由測試自己獨立解析 JSON 的 task 數得出（不取自 DB 列、不取自回應），
    # 三者相等才有鑑別力；不再自證式地拿 tasks_count 比自己
    pre_doc = json.loads(target.read_bytes().decode("utf-8"))
    json_tasks_in = sum(len(g.get("tasks", [])) for g in pre_doc["goals"])
    assert json_tasks_in > 0
    ok = signoff(renv, rid, did, imported_tasks_count=json_tasks_in, waivers=[
        {"ac": a, "reason": "r"} for a in ("AC-002-1", "AC-003-1", "AC-003-2")])
    assert ok.status_code == 200, ok.text
    assert ok.json()["imported_tasks_count"] == json_tasks_in == pre[5]
    raw = target.read_bytes()
    registered = renv.rdb.one(
        "SELECT sha256 FROM console.research_artifacts WHERE research_id = %s AND "
        "kind = 'TASK_DECOMPOSITION' ORDER BY version DESC LIMIT 1", rid)
    assert registered is not None and registered[0].strip() == hashlib.sha256(raw).hexdigest()
    doc = json.loads(raw.decode("utf-8"))
    json_tasks = sum(len(goal.get("tasks", [])) for goal in doc["goals"])
    [row] = rows(renv, rid)
    assert row[5] == json_tasks and row[2] == "SIGNED_OFF" and row[9], "tasks_count＝JSON task 數"
    assert doc["imported_tasks_count"] == json_tasks == row[5], "tasks_count == imported"
    checks = {c["id"]: c for c in renv.env.post(
        f"/research/projects/{rid}:reconcile", {}).json()["checks"]}
    assert checks["task_decomposition"]["status"] == "ok"
    target.write_bytes(raw + b" ")                       # 改檔一位元組
    drifted = {c["id"]: c for c in renv.env.post(
        f"/research/projects/{rid}:reconcile", {}).json()["checks"]}["task_decomposition"]
    assert drifted["status"] == "drift"
    [entry] = drifted["drift"]
    assert entry["kind"] == "TASK_DECOMPOSITION" and entry["path"].endswith(
        "task_decomposition.json")
    assert entry["expectedSha256"] == hashlib.sha256(raw).hexdigest()
    assert entry["actualSha256"] == hashlib.sha256(raw + b" ").hexdigest()
    assert target.read_bytes() == raw + b" ", "Bridge 不自動修正任何一邊"
    assert rows(renv, rid) == [row]


def test_AT_961_10_6_unequal_imported_count_is_recorded_as_given_not_corrected(
        renv: rgs.RouteEnv) -> None:
    """負控：傳入的 `imported_tasks_count` 與 JSON task 數不同 ⇒ Bridge 仍 200，
    artifact 如實記傳入值，`tasks_count` 不被改寫（如實記錄、不自動修正）。
    不相等的處置待勘誤：由對帳 `task_decomposition` 項回報（TCS 未定）。"""
    rid, did = partial_decomposition(renv)
    [pre] = rows(renv, rid)
    target = workspace(renv, rid) / "03_execution" / "task_decomposition.json"
    pre_doc = json.loads(target.read_bytes().decode("utf-8"))
    json_tasks = sum(len(g.get("tasks", [])) for g in pre_doc["goals"])
    odd = json_tasks + 7
    ok = signoff(renv, rid, did, imported_tasks_count=odd, waivers=[
        {"ac": a, "reason": "r"} for a in ("AC-002-1", "AC-003-1", "AC-003-2")])
    assert ok.status_code == 200, ok.text
    assert ok.json()["imported_tasks_count"] == odd != json_tasks
    doc = json.loads(target.read_bytes().decode("utf-8"))
    assert doc["imported_tasks_count"] == odd, "如實記傳入值"
    assert sum(len(g.get("tasks", [])) for g in doc["goals"]) == json_tasks
    [row] = rows(renv, rid)
    assert row[5] == pre[5] == json_tasks, "tasks_count 不被改寫"
