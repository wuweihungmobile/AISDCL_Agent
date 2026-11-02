"""Gate 0 與人工退回（TCS-ResearchToPRD-P0 AC-960-14；ADR-XPLAT-017 §D3；主控裁決 D-72）。

專案以資料庫與 FSM 直接播種到「head 版本有通過審查輪、外環 FSM 在 HUMAN_PENDING」（Given），
然後走真 HTTP 呼叫 `:approve-baseline`／`:return`／`:reconcile`；FSM 樹有 `fake`（假 CLI）與
`real`（真 SDD 樹，`SDD_ROOT` 不在＝TOOL-ABSENCE 跳過）兩種，同一組斷言各跑一次。引擎的 claude
一律是不存在的指令（本檔沒有任何 stage 啟動）。

D-72（approve 的摘要）：只比對前端送來的鍵——不符 422 `digest_mismatch`、一個鍵都沒送 422
`missing_digests`、缺鍵不算錯；四份文件的摘要一律由 `spec-frozen --digest --root` 在凍結當下自工作區
計算並記入凍結記錄。TCS AT-960-14-2／14-3／14-E-2 寫的 409 `spec_digest_changed`、缺鍵 422 因此
依 D-72 改寫（勘誤候選見交卷報告）。
"""
from __future__ import annotations

import hashlib
import threading
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest

from app import sdd_cli
from app.errors import ApiError
from app.research import fsm_ops, layout
from app.research.orchestrator import (
    APPROVE_DOCS,
    BASELINE_REL,
    approve_input_violations,
    digest_problems,
)
from tests import test_research_router as router_tests
from tests.test_research_router import (
    ADMIN,
    ALICE,
    HEAD,
    Env,
    create,
    db_snapshot,
    fsm_ctx_of,
    project_row,
)

rdb, fake, tree, popen_log = (router_tests.rdb, router_tests.fake, router_tests.tree,
                              router_tests.popen_log)
make_env, env = router_tests.make_env, router_tests.env

MATRIX_REL, SCOPE_REL, ADR_REL = APPROVE_DOCS[1], APPROVE_DOCS[2], APPROVE_DOCS[3]
PRD_TEXT = "# PRD\n\n## 1. 背景\n記憶體回收的延遲研究。\n\n## 2. 驗收\nAC-001：P99 低於 10 ms。\n"
MATRIX_TEXT = "# 證據矩陣\n\n| E-001 | 來源 |\n"
ADR_TEXT = "# ADR 草稿\n\n決定：採用分代回收。\n"


def sha(text: str | bytes) -> str:
    raw = text.encode("utf-8") if isinstance(text, str) else text
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def workspace(env: Env, rid: str) -> Path:
    return Path(project_row(env, rid)["workspace_path"])


def state_file(env: Env, rid: str) -> Path:
    row = project_row(env, rid)
    return Path(row["fsm_state_dir"]) / f"FSM-STATE-{row['fsm_project']}.yaml"


def seed_round(env: Env, rid: str, round_no: int, version_no: int, *, passed: bool = True,
               post_human: bool = False) -> None:
    """一個 REVIEW stage run 與它的審查輪（通過輪：gate PASS、計數 0；未通過輪：gate FAIL；
    POST_HUMAN 的通過輪只記資料庫：沒有 gate 結果與計數）。"""
    run_id = str(uuid.uuid4())
    env.db.insert_stage_run(research_id=rid, stage_run_id=run_id, stage="REVIEW",
                            round_no=round_no, requested_by=ALICE, status="SUCCEEDED")
    gate = None if post_human and passed else ("PASS" if passed else "FAIL")
    env.db.insert_review_round(research_id=rid, actor="bridge", round={
        "round_no": round_no, "prd_version_no": version_no,
        "trigger_kind": "POST_HUMAN" if post_human else "MANUAL",
        "precheck_passed": True, "weighted_score": "90.30" if passed else "79.90",
        "min_dimension_score": 70, "passed": passed, "verdict": "PASS" if passed else "REVISE",
        "fsm_gate_result": gate, "fsm_retry_count": None if gate is None else (
            0 if passed else 1),
        "escalated": False, "stage_run_id": run_id,
        "started_at": "2026-11-02T01:00:00+00:00", "finished_at": "2026-11-02T01:01:00+00:00"})


def seed_pending(env: Env, rid: str, *, passed: bool = True, fsm: str = "HUMAN_PENDING") -> None:
    """Given：head 版本（人工存的第 1 版）、證據矩陣與 ADR 草稿檔、一個審查輪、FSM 在 `fsm`。"""
    saved = env.put(f"/research/projects/{rid}/prd", {
        "base_version": 0, "content": PRD_TEXT, "author": ALICE})
    assert saved.status_code == 201, saved.text
    ws = workspace(env, rid)
    layout.write_workspace_file(ws, MATRIX_REL, MATRIX_TEXT)
    layout.write_workspace_file(ws, ADR_REL, ADR_TEXT)
    seed_round(env, rid, 1, 1, passed=passed)
    ctx = fsm_ctx_of(env, rid)
    fsm_ops.transition(ctx, to="SPEC_DRAFTING", reason="start drafting")
    fsm_ops.transition(ctx, to="SCG_VALIDATION", reason="ready for review")
    if fsm == "HUMAN_PENDING":
        fsm_ops.gate(ctx, gate="SCG_VALIDATION", result="PASS", reason="review passed")
    env.db.set_cursor(research_id=rid, actor="bridge", flow={
        "step": "studio", "phase": "GATE0_PENDING", "status": "WAITING_HUMAN", "detail": ""})


def seen(env: Env, rid: str, *names: str) -> dict[str, str]:
    """核准人當時看到的摘要（鍵＝契約的相對路徑；值＝`sha256:` 加現檔位元組的雜湊）。"""
    ws = workspace(env, rid)
    head = env.db.head_prd(rid)
    out: dict[str, str] = {}
    for name in names:
        found = layout.file_digest(ws, head["rel_path"] if name == BASELINE_REL else name)
        assert found is not None, name
        out[name] = "sha256:" + found[0]
    return out


def approve(env: Env, rid: str, digests: dict[str, str], *, version: int = 1,
            approver: str = ADMIN, **extra: Any) -> httpx.Response:
    return env.post(f"/research/projects/{rid}:approve-baseline", {
        "prd_version": version, "expected_digests": digests, "approver": approver, **extra})


def decisions(env: Env, rid: str) -> list[dict[str, Any]]:
    return env.db.query("SELECT * FROM {s}.research_gate_decisions WHERE research_id = %s "
                        "ORDER BY decided_at", (rid,))


def baselines(env: Env, rid: str) -> int:
    rows = env.db.query("SELECT count(*) AS n FROM {s}.research_artifacts WHERE research_id = %s "
                        "AND kind = 'PRD_BASELINE'", (rid,))
    return int(rows[0]["n"])


def untouched(env: Env, rid: str, before: dict[str, Any]) -> None:
    """被拒的核准：狀態檔位元組、決定列、基線登記列與基線檔都不變。"""
    assert state_file(env, rid).read_bytes() == before["state"], "FSM 狀態檔位元組不變"
    assert len(decisions(env, rid)) == before["decisions"]
    assert baselines(env, rid) == before["baselines"]
    assert not (workspace(env, rid) / BASELINE_REL).exists(), "基線檔不存在"
    assert db_snapshot(env, rid)[-1] == before["snap"][-1]


def mark(env: Env, rid: str) -> dict[str, Any]:
    return {"state": state_file(env, rid).read_bytes(), "decisions": len(decisions(env, rid)),
            "baselines": baselines(env, rid), "snap": db_snapshot(env, rid)}


def fsm_calls(log: list[list[str]], since: int = 0) -> list[list[str]]:
    """自 `since` 起的 FSM CLI 呼叫，每筆＝動詞與其後的引數。"""
    out = []
    for argv in log[since:]:
        if sdd_cli.CLI_MODULE in argv:
            out.append(argv[argv.index(sdd_cli.CLI_MODULE) + 1:])
    return out


# ── AT-960-14-1：核准成功（D-72：前端現況的兩鍵）───────────────────────────────────────────────
def test_AT_960_14_1_approval_freezes_four_docs_and_the_record_equals_show(env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    digests = seen(env, rid, BASELINE_REL, MATRIX_REL)          # 前端現況：只送 PRD 與證據矩陣兩鍵
    resp = approve(env, rid, digests, approver="alice@example.com")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "Gate-0" and body["fsm_state"] == "SPEC_FROZEN"
    assert body["gate_decision_id"]
    ctx = fsm_ctx_of(env, rid)
    shown = fsm_ops.show(ctx)
    frozen = shown["frozen_stages"][-1]
    assert frozen["stage"] == "Gate-0" and sorted(frozen["spec_docs"]) == sorted(APPROVE_DOCS)
    assert fsm_ops.current_state(ctx) == "SPEC_FROZEN"
    rows = decisions(env, rid)
    assert len(rows) == 1
    row = rows[0]
    assert (row["decision"], row["decided_by"], row["prd_version_no"]) == (
        "APPROVED", "alice@example.com", 1)
    assert row["fsm_stage"] == "Gate-0" and row["fsm_state_after"] == "SPEC_FROZEN"
    assert row["audit_trace_id"] and str(row["id"]) == body["gate_decision_id"]
    # 四檔摘要全部記入凍結記錄：決定列、回應、`show` 逐位元相同；值恰為現檔的雜湊
    assert dict(row["frozen_digests"]) == dict(frozen["spec_doc_digests"]) == body[
        "spec_doc_digests"]
    ws = workspace(env, rid)
    assert set(row["frozen_digests"]) == set(APPROVE_DOCS)
    for rel in APPROVE_DOCS:
        assert row["frozen_digests"][rel] == sha((ws / rel).read_bytes()), rel
    assert (ws / BASELINE_REL).read_bytes() == PRD_TEXT.encode("utf-8")
    flow = project_row(env, rid)
    assert (flow["flow_step"], flow["flow_phase"]) == ("route", "FROZEN")
    assert baselines(env, rid) == 1


def test_D_72_four_keys_or_the_head_path_alias_are_accepted_and_all_four_digests_recorded(
        env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    head_rel = env.db.head_prd(rid)["rel_path"]
    digests = seen(env, rid, BASELINE_REL, MATRIX_REL, SCOPE_REL, ADR_REL)
    digests[head_rel] = digests.pop(BASELINE_REL)                # PRD 以 head 草稿路徑表示
    resp = approve(env, rid, digests)
    assert resp.status_code == 200, resp.text
    assert set(resp.json()["spec_doc_digests"]) == set(APPROVE_DOCS)


# ── D-72 專屬：不符、零鍵、缺鍵 ───────────────────────────────────────────────────────────────
def test_D_72_a_mismatching_key_is_422_digest_mismatch_with_the_current_value_and_freezes_nothing(
        env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    digests = seen(env, rid, BASELINE_REL, MATRIX_REL)
    changed = MATRIX_TEXT + "核准後被改動\n"
    layout.write_workspace_file(workspace(env, rid), MATRIX_REL, changed)
    before = mark(env, rid)
    resp = approve(env, rid, digests)
    assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch")
    files = resp.json()["details"]["files"]
    assert [f["key"] for f in files] == [MATRIX_REL]
    assert files[0]["expected"] == digests[MATRIX_REL] and files[0]["current"] == sha(changed)
    untouched(env, rid, before)


def test_D_72_zero_keys_is_422_missing_digests_and_missing_keys_are_not_an_error(env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    before = mark(env, rid)
    resp = approve(env, rid, {})
    assert (resp.status_code, resp.json()["reason"]) == (422, "missing_digests")
    assert resp.json()["details"]["accepted_keys"] == list(APPROVE_DOCS)
    untouched(env, rid, before)
    one = approve(env, rid, seen(env, rid, ADR_REL))             # 只送一鍵：其餘由 Bridge 自行計算
    assert one.status_code == 200, one.text
    assert set(one.json()["spec_doc_digests"]) == set(APPROVE_DOCS)


def test_D_72_a_key_outside_the_four_docs_or_for_a_missing_file_counts_as_a_mismatch(
        env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    ws = workspace(env, rid)
    (ws / ADR_REL).unlink()
    digests = {**seen(env, rid, BASELINE_REL), ADR_REL: sha(ADR_TEXT),
               "02_governance/other.md": sha("x")}
    before = mark(env, rid)
    resp = approve(env, rid, digests)
    assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch")
    files = {f["key"]: f["current"] for f in resp.json()["details"]["files"]}
    assert files == {ADR_REL: None, "02_governance/other.md": None}
    untouched(env, rid, before)


# ── AT-960-14-2：檢查序先中者定案 ─────────────────────────────────────────────────────────────
def test_AT_960_14_2_the_first_unmet_check_wins_and_nothing_is_written(env: Env) -> None:
    # （一）head 版本沒有審查輪：先中 review_not_passed（即使摘要也不符）
    rid = create(env, "one")["research_id"]
    seed_pending(env, rid, passed=False)
    before = mark(env, rid)
    bad = {BASELINE_REL: sha("不是現檔")}
    resp = approve(env, rid, bad)
    assert (resp.status_code, resp.json()["reason"]) == (409, "review_not_passed")
    untouched(env, rid, before)
    # （二）通過輪屬舊版：人工存第 2 版後，核准第 1 版或第 2 版都不成立
    rid2 = create(env, "two")["research_id"]
    seed_pending(env, rid2)
    saved = env.put(f"/research/projects/{rid2}/prd", {
        "base_version": 1, "content": PRD_TEXT + "\n第二版\n", "author": ALICE})
    assert saved.status_code == 201, saved.text
    before2 = mark(env, rid2)
    for version in (1, 2):
        resp = approve(env, rid2, seen(env, rid2, BASELINE_REL), version=version)
        assert (resp.status_code, resp.json()["reason"]) == (409, "review_not_passed"), version
    untouched(env, rid2, before2)
    # （三）摘要不符且 FSM 不在 HUMAN_PENDING：先中摘要（順序固定：權杖、審查、摘要、FSM）
    rid3 = create(env, "three")["research_id"]
    seed_pending(env, rid3, fsm="SCG_VALIDATION")
    digests = seen(env, rid3, BASELINE_REL, MATRIX_REL)
    layout.write_workspace_file(workspace(env, rid3), MATRIX_REL, MATRIX_TEXT + "改\n")
    before3 = mark(env, rid3)
    resp = approve(env, rid3, digests)
    assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch")
    untouched(env, rid3, before3)
    # （四）摘要相符、FSM 不在 HUMAN_PENDING：fsm_state_conflict 帶 expected_state
    layout.write_workspace_file(workspace(env, rid3), MATRIX_REL, MATRIX_TEXT)
    resp = approve(env, rid3, seen(env, rid3, BASELINE_REL, MATRIX_REL))
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert resp.json()["details"]["expected_state"] == "HUMAN_PENDING"
    assert resp.json()["details"]["current_state"] == "SCG_VALIDATION"
    untouched(env, rid3, before3)
    # （五）FSM 在 ESCALATION：escalated（帶恢復指令）
    rid4 = create(env, "four")["research_id"]
    seed_pending(env, rid4, fsm="SCG_VALIDATION")
    ctx = fsm_ctx_of(env, rid4)
    router_tests.fail_to_escalation(ctx)
    before4 = mark(env, rid4)
    resp = approve(env, rid4, seen(env, rid4, BASELINE_REL))
    assert (resp.status_code, resp.json()["reason"]) == (409, "escalated")
    assert {"target", "powershell", "posix"} <= set(resp.json()["details"]["recovery"])
    untouched(env, rid4, before4)


# ── AT-960-14-3：核准輸入驗證（單元）─────────────────────────────────────────────────────────
def test_AT_960_14_3_approver_names_and_reserved_words() -> None:
    for bad in ("", "bridge", "agent", "system", "Agent", "x" * 101, "a b", "a+b", "-rf"):
        with pytest.raises(ApiError) as info:
            sdd_cli.validate_research_approver(bad)
        assert info.value.status_code == 422, repr(bad)
    for good in ("alice@example.com", "ops_01"):
        assert sdd_cli.validate_research_approver(good) == good


def test_AT_960_14_3_digest_keys_values_and_reason_are_validated_by_shape_only() -> None:
    ok = sha("x")
    assert approve_input_violations({}, None) == []                # 缺鍵不算形狀錯（D-72）
    assert approve_input_violations({ADR_REL: ok}, "r" * 500) == []
    rules = {(v["field"], v["rule"]) for v in approve_input_violations(
        {"/etc/passwd": ok, "C:/x/y.md": ok, "a/../b.md": ok, MATRIX_REL: "sha256:xyz",
         SCOPE_REL: "SHA256:" + "0" * 64}, "r" * 501)}
    assert rules == {("expected_digests", "invalid_path"), ("expected_digests", "invalid_digest"),
                     ("reason", "invalid_length")}
    paths = [v["message"] for v in approve_input_violations(
        {"/etc/passwd": ok, "C:/x/y.md": ok, "a/../b.md": ok}, None)]
    assert len(paths) == 3


def test_AT_960_14_3_digest_problems_compares_only_the_keys_that_were_sent() -> None:
    actual = {BASELINE_REL: "a" * 64, MATRIX_REL: "b" * 64, ADR_REL: "c" * 64}
    head = "01_specs/PRD-v0.3.0-draft.md"
    assert digest_problems({}, actual, head) == (
        "missing_digests", {"accepted_keys": list(APPROVE_DOCS)})
    assert digest_problems({BASELINE_REL: "sha256:" + "a" * 64}, actual, head) is None
    assert digest_problems({head: "sha256:" + "a" * 64, MATRIX_REL: "sha256:" + "b" * 64},
                           actual, head) is None                    # PRD 可用 head 草稿路徑
    zero, other = "sha256:" + "0" * 64, "sha256:" + "d" * 64
    reason, details = digest_problems(
        {BASELINE_REL: "sha256:" + "a" * 64, MATRIX_REL: zero, SCOPE_REL: other},
        actual, head) or ("", {})
    assert reason == "digest_mismatch"
    assert details["files"] == [
        {"key": MATRIX_REL, "expected": zero, "current": "sha256:" + "b" * 64},
        {"key": SCOPE_REL, "expected": other, "current": None}]


# ── AT-960-14-5：人工退回（框架 SOP 第 5 列）───────────────────────────────────────────────
def test_AT_960_14_5_returns_share_the_three_try_budget_and_the_third_escalates(
        env: Env, popen_log: list[list[str]]) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    ctx = fsm_ctx_of(env, rid)
    empty = env.post(f"/research/projects/{rid}:return", {"approver": ADMIN, "reason": ""})
    assert empty.status_code == 422
    assert fsm_ops.current_state(ctx) == "HUMAN_PENDING"
    mark_at = len(popen_log)
    first = env.post(f"/research/projects/{rid}:return", {
        "approver": ADMIN, "reason": "人工審查：AC-003 無可測 Then"})
    assert first.status_code == 200, first.text
    assert (first.json()["fsm_retry_count"], first.json()["escalated"]) == (1, False)
    gate = [c for c in fsm_calls(popen_log, mark_at) if c[0] == "gate"]
    assert len(gate) == 1
    argv = gate[0]
    assert argv[argv.index("--gate") + 1] == "SCG_VALIDATION"
    assert argv[argv.index("--result") + 1] == "FAIL"
    assert argv[argv.index("--reason") + 1].startswith("人工審查：AC-003")
    assert not any(c[0] == "transition" and "SPEC_DRAFTING" in c for c in fsm_calls(
        popen_log, mark_at)), "沒有 transition --to SPEC_DRAFTING"
    shown = fsm_ops.show(ctx)
    assert shown["current_state"] == "HUMAN_PENDING"
    assert shown["retry_history"]["SCG_VALIDATION"]["current_count"] == 1
    assert shown["decision_trace"][-1]["trigger"] == "gate_fail_blocked"
    row = decisions(env, rid)[0]
    assert row["decision"] == "CHANGES" and row["reason"].startswith("人工審查：AC-003")
    flow = project_row(env, rid)
    assert (flow["flow_phase"], flow["flow_step"]) == ("REVISING", "studio")
    # 第 2 次：人工 PUT 新版與重審通過（POST_HUMAN 只記 DB）使游標回 GATE0_PENDING 後再退回
    saved = env.put(f"/research/projects/{rid}/prd", {
        "base_version": 1, "content": PRD_TEXT + "\n補 AC\n", "author": ALICE})
    assert saved.status_code == 201, saved.text
    env.db.set_cursor(research_id=rid, actor="bridge", flow={
        "step": "studio", "phase": "GATE0_PENDING", "status": "WAITING_HUMAN", "detail": ""})
    second = env.post(f"/research/projects/{rid}:return", {"approver": ADMIN, "reason": "再補證據"})
    assert second.status_code == 200 and second.json()["fsm_retry_count"] == 2
    assert fsm_ops.current_state(ctx) == "HUMAN_PENDING"
    assert fsm_ops.show(ctx)["retry_history"]["SCG_VALIDATION"]["current_count"] == 2
    seed_round(env, rid, 2, 2, post_human=True)                 # 新版重審通過：只記資料庫
    third = env.post(f"/research/projects/{rid}:return", {"approver": ADMIN, "reason": "仍不足"})
    assert third.status_code == 200 and third.json()["escalated"] is True
    assert fsm_ops.current_state(ctx) == "ESCALATION"
    assert project_row(env, rid)["flow_status"] == "ESCALATED"
    after = approve(env, rid, seen(env, rid, BASELINE_REL), version=2)
    assert (after.status_code, after.json()["reason"]) == (409, "escalated")
    assert [d["decision"] for d in decisions(env, rid)] == ["CHANGES"] * 3


def test_AT_960_14_5_a_return_after_gate_0_is_409_spec_frozen(env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    assert approve(env, rid, seen(env, rid, BASELINE_REL)).status_code == 200
    resp = env.post(f"/research/projects/{rid}:return", {"approver": ADMIN, "reason": "太晚了"})
    assert (resp.status_code, resp.json()["reason"]) == (409, "spec_frozen")


# ── AT-960-14-6：並發核准 ───────────────────────────────────────────────────────────────────
def test_AT_960_14_6_two_concurrent_approvals_one_wins_and_the_other_is_409(env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    digests = seen(env, rid, BASELINE_REL, MATRIX_REL)
    results: list[httpx.Response] = []
    barrier = threading.Barrier(2)

    def go(approver: str) -> None:
        barrier.wait()
        results.append(httpx.post(
            f"{env.live.base_url}/research/projects/{rid}:approve-baseline", headers=HEAD,
            json={"prd_version": 1, "expected_digests": digests, "approver": approver},
            timeout=60))

    threads = [threading.Thread(target=go, args=(a,)) for a in (ADMIN, "bob@example.com")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(90)
    assert sorted(r.status_code for r in results) == [200, 409]
    loser = next(r for r in results if r.status_code == 409)
    assert loser.json()["reason"] == "fsm_state_conflict"
    assert len(decisions(env, rid)) == 1 and baselines(env, rid) == 1
    frozen = fsm_ops.show(fsm_ctx_of(env, rid))["frozen_stages"]
    assert [f["stage"] for f in frozen] == ["Gate-0"], "凍結記錄只有一筆"


# ── AT-960-14-7：有重試史才先走 SPEC_REGRESSION_CHECK ─────────────────────────────────────
def test_AT_960_14_7_the_regression_check_state_is_visited_only_when_show_reports_retries(
        env: Env, popen_log: list[list[str]]) -> None:
    alpha, beta = create(env, "alpha")["research_id"], create(env, "beta")["research_id"]
    for rid in (alpha, beta):
        seed_pending(env, rid)
    for reason in ("人工審查：AC 不明確", "人工審查：證據不足"):
        assert env.post(f"/research/projects/{alpha}:return", {
            "approver": ADMIN, "reason": reason}).status_code == 200
    ctx = fsm_ctx_of(env, alpha)
    assert fsm_ops.show(ctx)["retry_history"]["SCG_VALIDATION"]["current_count"] == 2
    for rid, retried in ((alpha, True), (beta, False)):
        at = len(popen_log)
        resp = approve(env, rid, seen(env, rid, BASELINE_REL))
        assert resp.status_code == 200, resp.text
        calls = fsm_calls(popen_log, at)
        until = calls[:[c[0] for c in calls].index("spec-frozen") + 1]
        names = [c[0] for c in until]
        assert names[-1] == "spec-frozen" and "show" in names
        assert until[-1][until[-1].index("--stage") + 1] == "Gate-0"
        regression = [c for c in until if c[0] == "transition"]
        if retried:
            assert len(regression) == 1
            argv = regression[0]
            assert argv[argv.index("--to") + 1] == "SPEC_REGRESSION_CHECK"
            reason = argv[argv.index("--reason") + 1]
            assert "defects handled" in reason and "2 human requests" in reason
        else:
            assert regression == [], "沒有重試史：不經 SPEC_REGRESSION_CHECK"
        shown = fsm_ops.show(fsm_ctx_of(env, rid))
        assert shown["current_state"] == "SPEC_FROZEN"
        assert shown["frozen_stages"][-1]["stage"] == "Gate-0"


# ── AT-960-14-9：凍結後一律 409 spec_frozen；凍結檔被外部改動由對帳顯示 ───────────────────────
def test_AT_960_14_9_after_gate_0_writes_are_409_and_reconcile_shows_external_drift(
        env: Env) -> None:
    rid = create(env)["research_id"]
    seed_pending(env, rid)
    assert approve(env, rid, seen(env, rid, BASELINE_REL, MATRIX_REL)).status_code == 200
    expected_sha = decisions(env, rid)[0]["frozen_digests"][BASELINE_REL]
    snap = db_snapshot(env, rid)
    put = env.put(f"/research/projects/{rid}/prd", {
        "base_version": 1, "content": PRD_TEXT + "x\n", "author": ALICE})
    assert (put.status_code, put.json()["reason"]) == (409, "spec_frozen")
    for stage in ("revise", "iterate", "review"):
        resp = env.post(f"/research/projects/{rid}/stages/{stage}:start", {"requested_by": ALICE})
        assert (resp.status_code, resp.json()["reason"]) == (409, "spec_frozen"), stage
    assert db_snapshot(env, rid) == snap, "被拒的請求零寫入"
    target = workspace(env, rid) / BASELINE_REL
    target.write_bytes(target.read_bytes() + b"!")              # 外部改動一個位元組
    result = env.post(f"/research/projects/{rid}:reconcile", {}).json()
    prd = next(c for c in result["checks"] if c["id"] == "prd_sha256")
    assert prd["status"] == "drift" and result["consistent"] is False
    entry = next(d for d in prd["drift"] if d["path"] == BASELINE_REL)
    assert entry["expectedSha256"] == expected_sha.removeprefix("sha256:")
    assert entry["actualSha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert target.read_bytes().endswith(b"!"), "Bridge 不自動修正任何一邊"


# ── AT-960-14-E-2：核准後的自動對帳 ────────────────────────────────────────────────────────
def test_AT_960_14_E_2_gate_0_runs_one_automatic_reconcile_and_a_prior_edit_blocks_it(
        env: Env) -> None:
    rid = create(env, "clean")["research_id"]
    seed_pending(env, rid)
    before = [e["seq"] for e in env.db.list_events(rid, limit=500)]
    assert approve(env, rid, seen(env, rid, BASELINE_REL)).status_code == 200
    events = env.db.list_events(rid, limit=500)
    recon = [e for e in events if e["event_type"] == "research.reconcile"]
    assert len(recon) == 1
    assert recon[0]["payload"]["consistent"] is True and recon[0]["payload"]["driftCount"] == 0
    seqs = [e["seq"] for e in events]
    assert seqs == list(range(1, len(seqs) + 1)) and len(seqs) > len(before)
    # 人為先改檔再核准：先被 digest_mismatch 擋下，不產生對帳事件
    other = create(env, "dirty")["research_id"]
    seed_pending(env, other)
    digests = seen(env, other, BASELINE_REL, SCOPE_REL)
    scope = workspace(env, other) / SCOPE_REL
    scope.write_bytes(scope.read_bytes() + b"\n")
    resp = approve(env, other, digests)
    assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch")
    assert [e for e in env.db.list_events(other, limit=500)
            if e["event_type"] == "research.reconcile"] == []


def test_AT_960_14_8_gate_0_never_goes_through_the_freeze_router() -> None:
    """`:approve-baseline` 是 Gate 0 的唯一載具：`routers/sdd.py` 不引用它（AT-960-14-8 的判定
    是既有整檔 `tests/test_sdd_freeze.py` 全綠且該路由檔零改動；這裡只釘 approve 不經 :freeze）。"""
    text = (Path(__file__).resolve().parents[1] / "app" / "routers" / "sdd.py").read_text(
        encoding="utf-8")
    assert "approve_baseline" not in text and "Gate-0" not in text
