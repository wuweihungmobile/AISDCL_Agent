"""分流執行：逐步入庫、失敗停點、重試、衝突、補償、牆鐘（TCS AT-961-4-*；PKG-BR-D1）。

真 git／真 FSM CLI／拋棄式庫；故障注入走兩個測試用縫：`route.STEP_HOOK`（每步副作用前後）與
`route.CLOCK`（假時鐘）。內環鍵建檔需要 B1 補丁（交卷「需主控處理」）。
"""
from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import psycopg
import pytest

from app import fsutil
from app.research import gitops, route
from tests import research_git_support as rgs
from tests import test_research_router as rt

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
ADMIN = "admin@example.com"


@pytest.fixture
def calls() -> Iterator[list[gitops.CallRecord]]:
    log: list[gitops.CallRecord] = []
    gitops.OBSERVERS.append(log.append)
    try:
        yield log
    finally:
        gitops.OBSERVERS.remove(log.append)


def set_cfg(renv: rgs.RouteEnv, **fields: Any) -> None:
    live = renv.env.live
    live.app.state.settings = replace(renv.env.settings, **fields)
    live.app.state.research.cfg = live.app.state.settings


def research_ctx(renv: rgs.RouteEnv) -> Any:
    ctx = renv.env.live.app.state.research
    assert ctx is not None
    return ctx


def route_rows(renv: rgs.RouteEnv, rid: str) -> list[tuple[Any, ...]]:
    return renv.rdb.q("SELECT id::text, status, failure_step, decided_by FROM "
                      "console.research_route_decisions WHERE research_id = %s "
                      "ORDER BY created_at", rid)


def step_rows(renv: rgs.RouteEnv, route_id: str) -> list[tuple[Any, ...]]:
    return renv.rdb.q("SELECT step_no, step, status, argv_redacted, exit_code, stderr_tail, "
                      "started_at, finished_at FROM console.research_route_steps "
                      "WHERE route_id = %s ORDER BY step_no", route_id)


def cursor(renv: rgs.RouteEnv, rid: str) -> tuple[str, str, str, str]:
    row = renv.rdb.one("SELECT flow_step, flow_phase, flow_status, flow_detail FROM "
                       "console.research_projects WHERE id = %s", rid)
    assert row is not None
    return row[0], row[1], row[2], row[3]


def route_events(renv: rgs.RouteEnv, rid: str) -> list[dict[str, Any]]:
    return [e[6] for e in renv.rdb.events(rid) if e[1] == "research.route"]


def seed_route(renv: rgs.RouteEnv, rid: str, status: str, *, step: str | None = None) -> str:
    """直接插入一個分流列（測試端的 Given；表的守衛只擋 UPDATE／DELETE，不擋 INSERT）。"""
    route_id = str(uuid.uuid4())
    renv.rdb.exec(
        "INSERT INTO console.research_route_decisions (id, research_id, track, target_kind, "
        "target_module, target_path, decided_by, status, failure_step) VALUES "
        "(%s, %s, 'A', 'MODULE', 'agentconsole', 'x', 'seed', %s, %s)",
        route_id, rid, status, step)
    return route_id


# ── AT-961-4-1 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_1_success_writes_steps_in_order_then_the_decision_file_and_the_cursor(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    seen: dict[str, Any] = {}

    def watch(phase: str, step: str) -> None:
        if (phase, step) == ("before", "VALIDATE_TARGET"):
            seen["during"] = cursor(renv, rid)
        if (phase, step) == ("before", "GIT_COMMIT"):
            seen["decision_file"] = (Path(renv.env.db.get_project(rid)["workspace_path"])
                                     / route.ROUTE_DECISION_REL).exists()

    route.STEP_HOOK = watch
    try:
        resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    finally:
        route.STEP_HOOK = None
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "SUCCEEDED" and body["flow"] == {
        "step": "build", "phase": "ROUTED", "status": "IDLE", "detail": ""}
    assert seen["during"] == ("route", "ROUTING", "RUNNING", "")
    assert seen["decision_file"] is False, "成功之前不寫 route_decision.json"
    rows = route_rows(renv, rid)
    assert len(rows) == 1 and rows[0][1:3] == ("SUCCEEDED", None) and rows[0][3] == ADMIN
    steps = step_rows(renv, rows[0][0])
    assert [s[0] for s in steps] == list(range(1, 8))
    assert [s[1] for s in steps] == list(route.TRACK_A_STEPS)
    assert all(s[2] == "OK" and s[3] for s in steps)
    assert all(s[7] >= s[6] for s in steps) and all(s[6].tzinfo for s in steps)
    assert [s[4] for s in steps][:3] == [0, 0, None], "子行程步驟有結束碼、Bridge 內步驟為 NULL"
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    text = (ws / route.ROUTE_DECISION_REL).read_text(encoding="utf-8")
    art = renv.rdb.one("SELECT sha256, version FROM console.research_artifacts WHERE kind = "
                       "'ROUTE_DECISION' AND research_id = %s", rid)
    assert art is not None and art[0].strip() == rgs.hashlib.sha256(text.encode()).hexdigest()
    events = route_events(renv, rid)
    route_level = [e["status"] for e in events if e["stepNo"] == 0]
    assert route_level == ["PENDING", "RUNNING", "SUCCEEDED"]
    for number in range(1, 8):
        assert {e["status"] for e in events if e["stepNo"] == number} == {"RUNNING", "OK"}
        assert set(next(e for e in events if e["stepNo"] == number)) == {
            "routeId", "stepNo", "step", "status"}
    seqs = [e[0] for e in renv.rdb.events(rid)]
    assert seqs == list(range(1, len(seqs) + 1)), "事件 seq 連續"


# ── AT-961-4-2 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_2_a_failure_stops_the_run_keeps_the_rows_and_marks_the_cursor(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv, base_ref="no-such-ref"))
    assert (resp.status_code, resp.json()["reason"]) == (502, "route_step_failed")
    details = resp.json()["details"]
    assert details["failure_step"] == "GIT_SWITCH" and details["route_id"] and details["steps"]
    rows = route_rows(renv, rid)
    assert rows[0][1:3] == ("FAILED", "GIT_SWITCH")
    steps = {s[1]: s for s in step_rows(renv, rows[0][0])}
    assert set(steps) == {"VALIDATE_TARGET", "GIT_SWITCH"}, "其後步驟不產生列"
    assert steps["VALIDATE_TARGET"][2] == "OK" and steps["GIT_SWITCH"][2] == "FAILED"
    assert steps["GIT_SWITCH"][4] not in (None, 0) and steps["GIT_SWITCH"][5]
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    assert not (ws / route.ROUTE_DECISION_REL).exists()
    assert cursor(renv, rid) == ("route", "ROUTING", "FAILED", "GIT_SWITCH")
    kinds = {e[1] for e in renv.rdb.events(rid)}
    assert "research.route" in kinds and not [e for e in renv.rdb.events(rid)
                                              if e[1] == "research.alert"]
    assert [e["status"] for e in route_events(renv, rid) if e["stepNo"] == 0][-1] == "FAILED"


# ── AT-961-4-3 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_3_a_retry_redoes_only_the_failed_step_and_a_changed_input_is_409(
        renv: rgs.RouteEnv, calls: list[gitops.CallRecord]) -> None:
    rid = rgs.seed_gate0(renv)
    project = renv.console_project("keep")
    body = rgs.body_a(renv, base_ref="no-such-ref", console_project_id=project)
    assert renv.env.post(f"/research/projects/{rid}:route", body).status_code == 502
    route_id = route_rows(renv, rid)[0][0]
    first = step_rows(renv, route_id)[0]
    rgs.git(renv.repo, "branch", "no-such-ref")
    changed = renv.env.post(f"/research/projects/{rid}:route", {
        **body, "base_ref": "main", "retry": True})
    assert (changed.status_code, changed.json()["reason"]) == (409, "route_conflict")
    assert changed.json()["details"]["reason"] == "inputs_changed"
    assert len(step_rows(renv, route_id)) == 2
    calls.clear()
    ok = renv.env.post(f"/research/projects/{rid}:route", {**body, "retry": True})
    assert ok.status_code == 200, ok.text
    rows = route_rows(renv, rid)
    assert len(rows) == 1 and rows[0][0] == route_id and rows[0][1:3] == ("SUCCEEDED", None)
    steps = step_rows(renv, route_id)
    assert steps[0] == first, "VALIDATE_TARGET 列位元組不變"
    assert [s[1] for s in steps] == list(route.TRACK_A_STEPS)
    assert not [c for c in calls if "--show-toplevel" in c.argv], "VALIDATE_TARGET 不重做"
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    assert (ws / route.ROUTE_DECISION_REL).exists()


# ── AT-961-4-4 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_4_a_failure_never_cleans_up_what_already_exists(
        renv: rgs.RouteEnv, calls: list[gitops.CallRecord],
        monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv)
    real = fsutil.write_text_atomic

    def flaky(path: Path, text: str) -> None:
        if path.name.endswith("_PRD.md"):
            raise OSError("injected")
        real(path, text)

    monkeypatch.setattr(fsutil, "write_text_atomic", flaky)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert (resp.status_code, resp.json()["details"]["failure_step"]) == (502, "PUBLISH_DOCS")
    assert "git worktree remove" in resp.json()["details"]["cleanup_hint"]
    branch = f"feature/issue-{str(renv.env.db.get_project(rid)['rp_no']).removeprefix('RP-')}"
    assert branch in rgs.git(renv.repo, "branch", "--list")
    assert len(list(renv.worktrees.iterdir())) == 1
    flat = [" ".join(c.argv) for c in calls]
    for banned in ("clean", "stash", "reset", "worktree remove", "branch -D", "checkout --"):
        assert not [f for f in flat if banned in f], banned
    assert route_rows(renv, rid)[0][1] == "FAILED", "COMPENSATED 只由補償通知寫入"


# ── AT-961-4-5 ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("status", ["PENDING", "RUNNING", "SUCCEEDED"])
def test_AT_961_4_5_an_active_route_blocks_a_second_one_with_zero_side_effects(
        renv: rgs.RouteEnv, status: str) -> None:
    rid = rgs.seed_gate0(renv)
    existing = seed_route(renv, rid, status)
    before = {t: renv.rdb.count(t) for t in ("research_route_decisions", "research_route_steps",
                                             "research_events")}
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert (resp.status_code, resp.json()["reason"]) == (409, "route_conflict")
    assert resp.json()["details"] == {"route_id": existing, "status": status}
    assert {t: renv.rdb.count(t) for t in before} == before
    assert not list(renv.worktrees.iterdir())


def test_AT_961_4_5_a_failed_route_needs_an_explicit_retry(renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    seed_route(renv, rid, "FAILED", step="GIT_SWITCH")
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert (resp.status_code, resp.json()["reason"]) == (409, "route_conflict")
    assert resp.json()["details"]["reason"] == "retry_required"


# ── AT-961-4-6 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_6_two_admins_confirming_at_once_produce_one_route_and_one_worktree(
        renv: rgs.RouteEnv, calls: list[gitops.CallRecord]) -> None:
    rid = rgs.seed_gate0(renv)
    results: list[int] = []

    def post(approver: str) -> None:
        body = {**rgs.body_a(renv, approver=approver),
                "console_project_id": renv.console_project(approver.split("@")[0])}
        results.append(renv.env.post(f"/research/projects/{rid}:route", body).status_code)

    threads = [threading.Thread(target=post, args=(a,)) for a in ("a1@example.com",
                                                                  "a2@example.com")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [200, 409], results
    assert len(route_rows(renv, rid)) == 1
    assert len([c for c in calls if "worktree" in c.argv and "add" in c.argv]) == 1
    with pytest.raises(psycopg.errors.UniqueViolation):                  # 部分唯一索引是最後防線
        seed_route(renv, rid, "PENDING")


# ── AT-961-4-7 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_7_an_interrupted_run_is_reaped_and_the_retry_resumes_idempotently(
        renv: rgs.RouteEnv, calls: list[gitops.CallRecord]) -> None:
    rid = rgs.seed_gate0(renv)
    project = renv.console_project("keep")
    body = rgs.body_a(renv, console_project_id=project)

    def crash(phase: str, step: str) -> None:
        if (phase, step) == ("after", "GIT_SWITCH"):
            raise RuntimeError("injected crash after the side effect")

    route.STEP_HOOK = crash
    try:
        interrupted = renv.env.post(f"/research/projects/{rid}:route", body)
    finally:
        route.STEP_HOOK = None
    assert interrupted.status_code == 500
    route_id = route_rows(renv, rid)[0][0]
    steps = {s[1]: s[2] for s in step_rows(renv, route_id)}
    assert steps["GIT_SWITCH"] == "RUNNING", "副作用之前已先以 RUNNING 入庫"
    assert route_rows(renv, rid)[0][1] == "RUNNING"
    ctx = research_ctx(renv)
    assert route.reap_route_orphans(ctx.db, ctx.writer) == [route_id]
    steps = {s[1]: s for s in step_rows(renv, route_id)}
    assert steps["GIT_SWITCH"][2] == "FAILED" and steps["GIT_SWITCH"][5] == "interrupted"
    assert route_rows(renv, rid)[0][1:3] == ("FAILED", "GIT_SWITCH")
    assert cursor(renv, rid) == ("route", "ROUTING", "FAILED", "GIT_SWITCH")
    assert route.reap_route_orphans(ctx.db, ctx.writer) == [], "回收冪等"
    calls.clear()
    retried = renv.env.post(f"/research/projects/{rid}:route", {**body, "retry": True})
    assert retried.status_code == 200, retried.text
    assert not [c for c in calls if "worktree" in c.argv and "add" in c.argv], "不重複建立"
    assert route_rows(renv, rid)[0][1] == "SUCCEEDED"


# ── AT-961-4-8 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_8_token_and_approver_rules_and_the_audit_trail(
        renv: rgs.RouteEnv, caplog: pytest.LogCaptureFixture) -> None:
    rid = rgs.seed_gate0(renv)
    caplog.set_level(logging.INFO)
    body = {**rgs.body_a(renv), "console_project_id": renv.console_project("c")}
    url = f"/research/projects/{rid}:route"
    assert renv.env.post(url, body, headers=None).status_code == 403
    assert renv.env.post(url, body, headers={"X-Bridge-Token": "wrong"}).status_code == 403
    for bad in ("", "bridge", "agent", "system", "x" * 101, "a b"):
        resp = renv.env.post(url, {**body, "approver": bad})
        assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request"), bad
    assert renv.env.post(f"/research/projects/{rid}:route-preview", rgs.body_a(renv),
                         headers=None).status_code == 403
    assert rgs.preview(renv, rid, rgs.body_a(renv)).status_code == 200
    audit = [r.getMessage() for r in caplog.records if r.name == "bridge.audit"
             and '"research_write"' in r.getMessage()]
    verbs = {m.split('"verb": "')[1].split('"')[0] for m in audit}
    assert {"route", "route-preview"} <= verbs
    assert not [m for m in audit if rt.TOKEN in m], "稽核不含權杖值"
    set_cfg(renv, research_write_token=None)
    off = renv.env.post(url, body)
    assert (off.status_code, off.json()["reason"]) == (503, "research_write_disabled")


# ── AT-961-4-9 ─────────────────────────────────────────────────────────────────────────────
def test_AT_961_4_9_compensation_marks_only_a_failed_route_and_frees_the_project(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    failed = rgs.confirm(renv, rid, rgs.body_a(renv, base_ref="no-such-ref"))
    assert failed.status_code == 502
    route_id = route_rows(renv, rid)[0][0]
    cursor_before = cursor(renv, rid)
    url = f"/research/projects/{rid}:route-compensated"
    base = {"route_id": route_id, "requested_by": "console@example.com"}
    assert renv.env.post(url, {**base, "reason": "x"}, headers=None).status_code == 403
    for reason, status in (("", 422), ("y" * 501, 422), ("   ", 422)):
        assert renv.env.post(url, {**base, "reason": reason}).status_code == status, reason
    ok = renv.env.post(url, {**base, "reason": "補償：專案列已封存"})
    assert ok.status_code == 200 and ok.json() == {"route_id": route_id, "status": "COMPENSATED"}
    assert route_rows(renv, rid)[0][1] == "COMPENSATED"
    assert cursor(renv, rid) == cursor_before, "游標不動"
    last = [e for e in route_events(renv, rid) if e["status"] == "COMPENSATED"]
    assert last and last[0]["reason"] == "補償：專案列已封存"
    again = renv.env.post(url, {**base, "reason": "x"})
    assert (again.status_code, again.json()["reason"]) == (409, "route_conflict")
    assert again.json()["details"]["status"] == "COMPENSATED"
    assert renv.env.post(url, {**base, "route_id": str(uuid.uuid4()), "reason": "x"}
                         ).status_code == 404
    retried = rgs.confirm(renv, rid, rgs.body_a(renv, base_ref="main"))
    assert retried.status_code == 200, retried.text
    rows = route_rows(renv, rid)
    assert [r[1] for r in rows] == ["COMPENSATED", "SUCCEEDED"] and rows[0][0] != rows[1][0]
    max_ok = renv.env.post(url, {**base, "route_id": seed_route(renv, rgs.seed_gate0(
        renv, "other"), "FAILED", step="GIT_SWITCH"), "reason": "z" * 500})
    assert max_ok.status_code == 404, "route_id 不屬於這個專案＝404"


@pytest.mark.parametrize("status", ["RUNNING", "SUCCEEDED"])
def test_AT_961_4_9_a_route_that_is_not_failed_is_409(renv: rgs.RouteEnv, status: str) -> None:
    rid = rgs.seed_gate0(renv)
    route_id = seed_route(renv, rid, status)
    resp = renv.env.post(f"/research/projects/{rid}:route-compensated", {
        "route_id": route_id, "requested_by": "console@example.com", "reason": "x"})
    assert (resp.status_code, resp.json()["reason"]) == (409, "route_conflict")
    assert resp.json()["details"]["status"] == status
    assert route_rows(renv, rid)[0][1] == status


# ── AT-961-4-E-1 ───────────────────────────────────────────────────────────────────────────
def test_AT_961_4_E_1_blocked_writes_wait_in_the_outbox_and_replay_is_idempotent(
        renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv)
    gate = {"on": True}

    def block(phase: str, step: str) -> None:
        if gate["on"] and (phase, step) == ("before", "GIT_SWITCH"):
            gate["on"] = False
            renv.rdb.block()

    route.STEP_HOOK = block
    try:
        resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    finally:
        route.STEP_HOOK = None
        renv.rdb.unblock()
    assert (resp.status_code, resp.json()["reason"]) == (503, "db_blocked")
    ctx = research_ctx(renv)
    assert ctx.writer.has_pending(rid)
    assert route_rows(renv, rid)[0][1] == "RUNNING", "阻塞期間路由列不顯示終態"
    first = ctx.writer.replay()
    assert not first.rejected and first.blocked is None
    # D-128：重放完成那一刻游標已校正——路由列 SUCCEEDED、游標不殘留 BLOCKED_DB
    cur = cursor(renv, rid)
    assert (route_rows(renv, rid)[0][1], cur[:3]) == ("RUNNING", ("route", "ROUTING", "RUNNING"))
    assert cur[2] != "BLOCKED_DB"
    assert not ctx.writer.has_pending(rid)
    snapshot = (renv.rdb.count("research_route_steps"), renv.rdb.count("research_events"))
    second = ctx.writer.replay()
    assert not second.applied
    assert (renv.rdb.count("research_route_steps"), renv.rdb.count("research_events")) == snapshot
    seqs = [e[0] for e in renv.rdb.events(rid)]
    assert seqs == list(range(1, len(seqs) + 1)), "事件 seq 連續無缺漏"


def test_AT_961_4_E_1_a_late_block_leaves_the_final_ops_queued_and_replay_settles_the_cursor(
        renv: rgs.RouteEnv) -> None:
    """D-128 校正點：最後一步之後才斷線，收尾操作（路由列 SUCCEEDED、游標 build／ROUTED）留在
    outbox；重放完成的同一交易重新衍生游標，路由列與游標一致、不殘留 BLOCKED_DB。"""
    rid = rgs.seed_gate0(renv)
    ctx = research_ctx(renv)
    gate = {"on": True}

    def block(step: str, op: Any) -> None:     # 收尾的 route.finish(SUCCEEDED) 寫入 outbox 之後斷線
        if (gate["on"] and step == "outbox" and op.kind == "route.finish"
                and op.payload.get("status") == "SUCCEEDED"):
            gate["on"] = False
            renv.rdb.block()

    ctx.writer._after = block                  # DurableWriter 的四步後中斷注入點（測試專用）
    try:
        resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    finally:
        ctx.writer._after = None
        renv.rdb.unblock()
    assert (resp.status_code, resp.json()["reason"]) == (503, "db_blocked")
    assert ctx.writer.has_pending(rid)
    assert route_rows(renv, rid)[0][1] != "SUCCEEDED" and cursor(renv, rid)[1] != "ROUTED"
    first = ctx.writer.replay()
    assert not first.rejected and first.blocked is None and first.applied
    assert route_rows(renv, rid)[0][1] == "SUCCEEDED"
    assert cursor(renv, rid)[:3] == ("build", "ROUTED", "IDLE")
    snapshot = (renv.rdb.count("research_route_steps"), renv.rdb.count("research_events"),
                cursor(renv, rid))
    second = ctx.writer.replay()
    assert not second.applied
    assert (renv.rdb.count("research_route_steps"), renv.rdb.count("research_events"),
            cursor(renv, rid)) == snapshot
    seqs = [e[0] for e in renv.rdb.events(rid)]
    assert seqs == list(range(1, len(seqs) + 1)), "事件 seq 連續無缺漏"


@pytest.mark.parametrize(("stale", "expected"), [("RUNNING", "IDLE"), ("FAILED", "FAILED")])
def test_AT_961_4_E_1_replay_rederives_a_stale_status_but_never_washes_out_failed(
        renv: rgs.RouteEnv, stale: str, expected: str) -> None:
    """D-128 的校正本身：沒有進行中的 stage run 與分流列時，過期的 RUNNING 衍生回 IDLE；已寫下的
    FAILED 不被重放洗掉（只有後續成功收尾才把它衍生掉）。"""
    from app.research.outbox import DbBlocked
    rid = rgs.seed_gate0(renv)
    flow = {"step": "build", "phase": "ROUTED", "status": stale, "detail": "keep"}
    ctx = research_ctx(renv)
    renv.rdb.block()
    try:
        with pytest.raises(DbBlocked):
            ctx.writer.persist(route.Op("project.cursor", rid, {
                "research_id": rid, "actor": "bridge", "flow": flow}))
    finally:
        renv.rdb.unblock()
    assert ctx.writer.has_pending(rid)
    assert ctx.writer.replay().applied
    assert cursor(renv, rid) == ("build", "ROUTED", expected, "keep")
    assert not ctx.writer.has_pending(rid)


# ── AT-961-4-E-2／E-3：牆鐘════════════════════════════════════════════════════════════════════
class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.parametrize(("elapsed", "timeout", "ok"), [
    (299, 300, True), (300, 300, False), (301, 300, False), (298, 299, True),
    (299, 299, False), (300, 301, True)])
def test_AT_961_4_E_2_the_wall_clock_boundary_moves_with_the_setting(
        renv: rgs.RouteEnv, calls: list[gitops.CallRecord], monkeypatch: pytest.MonkeyPatch,
        elapsed: int, timeout: int, ok: bool) -> None:
    rid = rgs.seed_gate0(renv)
    set_cfg(renv, research_route_timeout_seconds=timeout)
    clock = FakeClock()
    monkeypatch.setattr(route, "CLOCK", clock)

    def tick(phase: str, step: str) -> None:
        if (phase, step) == ("after", "GIT_SWITCH"):
            clock.now += elapsed

    monkeypatch.setattr(route, "STEP_HOOK", tick)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    if ok:
        assert resp.status_code == 200, resp.text
        return
    assert (resp.status_code, resp.json()["reason"]) == (502, "route_step_failed")
    assert resp.json()["details"]["reason"] == "route_timeout"
    assert resp.json()["details"]["failure_step"] == "PUBLISH_DOCS"
    before = len(calls)
    assert route_rows(renv, rid)[0][1:3] == ("FAILED", "PUBLISH_DOCS")
    assert cursor(renv, rid) == ("route", "ROUTING", "FAILED", "PUBLISH_DOCS")
    assert len(calls) == before, "逾時後不再啟動任何新步驟"
    monkeypatch.setattr(route, "STEP_HOOK", None)
    retry = renv.env.post(f"/research/projects/{rid}:route", {
        **rgs.body_a(renv), "console_project_id": renv.rdb.one(
            "SELECT console_project_id::text FROM console.research_route_decisions")[0],
        "retry": True})
    assert retry.status_code == 200, "逾時後可 retry 續做"


def test_AT_961_4_E_3_a_timeout_keeps_the_finished_steps_and_their_side_effects(
        renv: rgs.RouteEnv, calls: list[gitops.CallRecord],
        monkeypatch: pytest.MonkeyPatch) -> None:
    rid = rgs.seed_gate0(renv)
    clock = FakeClock()
    monkeypatch.setattr(route, "CLOCK", clock)
    monkeypatch.setattr(route, "STEP_HOOK", lambda phase, step: setattr(
        clock, "now", clock.now + 400) if (phase, step) == ("after", "GIT_SWITCH") else None)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv))
    assert resp.status_code == 502
    steps = {s[1]: s[2] for s in step_rows(renv, route_rows(renv, rid)[0][0])}
    assert steps["VALIDATE_TARGET"] == "OK" and steps["GIT_SWITCH"] == "OK"
    assert len(list(renv.worktrees.iterdir())) == 1
    flat = [" ".join(c.argv) for c in calls]
    for banned in ("clean", "stash", "reset", "worktree remove", "branch -D"):
        assert not [f for f in flat if banned in f], banned
    assert 330 > renv.env.settings.research_route_timeout_seconds == 300
