"""SCR MINOR 的內環收尾序列：真 FSM CLI、暫存狀態目錄、現態矩陣、核准即套用與 `:scr-apply`
重試（TCS AT-961-13-*；PKG-BR-D2）。

需要真框架樹（`SDD_ROOT`）：缺＝`TOOL-ABSENCE` skip（SCG-4 證據須 0 skipped）。每個矩陣列各跑一次
完整序列；外環的「起草→審查 PASS→gate」以資料庫夾具＋真 FSM 動詞佈置（審查 stage 本身是 P0 的事）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app import fsutil, sdd_cli
from app.errors import ApiError
from app.research import fsm_ops, scr
from tests import research_git_support as rgs
from tests import test_research_approve as ap
from tests import test_research_router as rt
from tests.test_research_scr import (
    ADMIN,
    cli,
    cursor,
    escalate,
    inner,
    inner_to,
    outer,
    post_scr,
    routed,
    scr_rows,
)

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
CHANGED_PRD = rgs.PRD_PLACEMENT.replace("分流測試用 PRD。", "SCR 之後的新版 PRD。")
CHANGED_SCOPE_PRD = CHANGED_PRD.replace("AgentConsole", "AutoClaude")
PRE_LABELS = {"transition(SPEC_AUDIT)": ["transition(SPEC_AUDIT)"], "SPEC_AUDIT": [],
              "gate(RTM_VERIFY,FAIL)": ["gate(RTM_VERIFY,FAIL)"],
              "gate(RELEASE_READY,FAIL)": ["gate(RELEASE_READY,FAIL)"]}
TAIL = ["publish", "spec-refreeze", "transition(PR_REVIEW)", "gate(PR_REVIEW,FAIL)"]


def outer_loop(renv: rgs.RouteEnv, rid: str, prd: str, **extra: Any) -> Any:
    """SCR 之後外環的起草→審查 PASS→gate（資料庫夾具＋真 FSM 動詞），最後 `:approve-baseline`。"""
    env = renv.env
    head = env.db.head_prd(rid)
    saved = env.put(f"/research/projects/{rid}/prd", {
        "base_version": head["version_no"], "content": prd, "author": rt.ALICE})
    assert saved.status_code == 201, saved.text
    version = saved.json()["version_no"]
    rounds = env.db.review_state(rid)["completed"]
    ap.seed_round(env, rid, rounds + 1, version)
    ctx = outer(renv, rid)
    fsm_ops.transition(ctx, to="SCG_VALIDATION", reason="ready for review")
    fsm_ops.gate(ctx, gate="SCG_VALIDATION", result="PASS", reason="review passed")
    return ap.approve(env, rid, ap.seen(env, rid, ap.BASELINE_REL), version=version, **extra)


def actions(renv: rgs.RouteEnv, rid: str) -> list[dict[str, Any]]:
    return list(scr_rows(renv, rid)[0][7])


def labels(renv: rgs.RouteEnv, rid: str) -> list[str]:
    return [a["label"] for a in actions(renv, rid)]


def at_state(renv: rgs.RouteEnv, slug: str, state: str) -> tuple[str, dict[str, Any]]:
    rid, route = routed(renv, slug)
    if state == "RTM_VERIFY_FIRST_FAIL":
        raise AssertionError("內部用法錯誤")
    inner_to(renv, route, state)
    return rid, route


# ── AT-961-13-1／13-2／13-3：現態矩陣 × 序列（每列實跑一次）─────────────────────────────────────
MATRIX = [
    ("IMPLEMENTATION", ["transition(SPEC_AUDIT)", *TAIL]),
    ("EXECUTION_EVALUATION", ["transition(SPEC_AUDIT)", *TAIL]),
    ("PR_REVIEW", ["transition(SPEC_AUDIT)", *TAIL]),
    ("SPEC_AUDIT", TAIL),
    # 框架的重凍只准在 SPEC_AUDIT：gate 退回 IMPLEMENTATION 之後仍要先 transition SPEC_AUDIT
    ("RTM_VERIFY", ["gate(RTM_VERIFY,FAIL)", "transition(SPEC_AUDIT)", *TAIL]),
    ("RELEASE_READY", ["gate(RELEASE_READY,FAIL)", "transition(SPEC_AUDIT)", *TAIL]),
]


@pytest.mark.parametrize(("state", "expected"), MATRIX, ids=[m[0] for m in MATRIX])
def test_AT_961_13_2_each_matrix_row_runs_its_sequence_and_ends_in_implementation(
        renv: rgs.RouteEnv, state: str, expected: list[str]) -> None:
    rid, route = at_state(renv, "demo", state)
    assert post_scr(renv, rid).status_code == 202
    resp = outer_loop(renv, rid, CHANGED_PRD)
    assert resp.status_code == 200, resp.text
    assert resp.json()["scr_apply"] == {"status": "APPLIED", "detail": ""}
    assert resp.json()["stage"] == "Gate-0-SCR1"
    assert labels(renv, rid) == expected
    assert all(a["rc"] == 0 and a["at"] and a["verb"] for a in actions(renv, rid))
    assert fsm_ops.current_state(inner(renv, route)) == "IMPLEMENTATION"
    assert scr_rows(renv, rid)[0][2] == "APPLIED"
    assert cursor(renv, rid) == ("build", "ROUTED", "IDLE", "")
    published = Path(route["target_path"]) / "docs" / "01_requirements" / "demo_PRD.md"
    assert published.read_text(encoding="utf-8") == CHANGED_PRD
    worktree = Path(route["target_path"]).parent
    assert rgs.git(worktree, "log", "-1", "--format=%s").startswith("docs: 發佈")


# ── AT-961-13-1：序列與人工等價序列的 decision_trace diff ───────────────────────────────────
def trace_tail(ctx: fsm_ops.FsmCtx, count: int) -> list[tuple[Any, Any, Any]]:
    trace = fsm_ops.show(ctx)["decision_trace"][-count:]
    return [(t.get("from") or t.get("from_state"), t.get("to") or t.get("to_state"),
             t.get("trigger")) for t in trace]


def test_AT_961_13_1_the_bridge_sequence_equals_the_manual_equivalent_decision_trace(
        renv: rgs.RouteEnv) -> None:
    rid, route = at_state(renv, "demo", "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    assert outer_loop(renv, rid, CHANGED_PRD).status_code == 200
    bridge_trace = trace_tail(inner(renv, route), 3)
    # 人工等價序列：另一個專案、同一份 CLI、同樣的指令（ADR-XPLAT-017 附錄 A）
    rid2, route2 = at_state(renv, "demo2", "IMPLEMENTATION")
    key, sdir = route2["impl_fsm_project"], route2["impl_state_dir"]
    root = route2["target_path"]
    doc = "docs/01_requirements/demo2_PRD.md"
    cli(renv, key, sdir, "transition", "--to", "SPEC_AUDIT", "--reason", "manual",
        "--trigger", sdd_cli.RESEARCH_TRIGGER)
    cli(renv, key, sdir, "spec-refreeze", "--doc", doc, "--root", root, "--reason", "manual",
        "--approver", ADMIN)
    cli(renv, key, sdir, "transition", "--to", "PR_REVIEW", "--reason", "manual", "--trigger",
        sdd_cli.RESEARCH_TRIGGER)
    cli(renv, key, sdir, "gate", "--gate", "PR_REVIEW", "--result", "FAIL", "--reason",
        "manual")
    manual_trace = trace_tail(inner(renv, route2), 3)
    assert bridge_trace == manual_trace, (bridge_trace, manual_trace)
    assert [t[:2] for t in bridge_trace][-1][1] == "IMPLEMENTATION"
    # 外環：SCR 的 Gate-0-SCR 核准把外環鍵帶回 SPEC_FROZEN
    assert fsm_ops.current_state(outer(renv, rid)) == "SPEC_FROZEN"
    assert rid2


# ── AT-961-13-3：gate 退回不是 IMPLEMENTATION＝BLOCKED，不重試 ─────────────────────────────────
def test_AT_961_13_3_a_gate_that_escalates_blocks_the_sequence_without_retry(
        renv: rgs.RouteEnv) -> None:
    rid, route = at_state(renv, "demo", "RTM_VERIFY")
    key, sdir = route["impl_fsm_project"], route["impl_state_dir"]
    cli(renv, key, sdir, "gate", "--gate", "RTM_VERIFY", "--result", "FAIL", "--reason", "pre-1")
    cli(renv, key, sdir, "transition", "--to", "PR_REVIEW", "--reason", "g", "--trigger",
        sdd_cli.RESEARCH_TRIGGER)
    cli(renv, key, sdir, "gate", "--gate", "PR_REVIEW", "--result", "PASS", "--reason", "g")
    assert fsm_ops.current_state(inner(renv, route)) == "RTM_VERIFY"
    assert post_scr(renv, rid).status_code == 202
    resp = outer_loop(renv, rid, CHANGED_PRD)
    assert resp.status_code == 200, resp.text
    out = resp.json()["scr_apply"]
    assert out["status"] == "BLOCKED" and out["detail"].startswith("gate(RTM_VERIFY,FAIL)")
    assert labels(renv, rid) == ["gate(RTM_VERIFY,FAIL)"]
    assert actions(renv, rid)[0]["blocked"] is True
    assert scr_rows(renv, rid)[0][2] == "APPROVED"
    flow = cursor(renv, rid)
    assert flow[3].startswith("scr_blocked:ESCALATION"), flow
    published = Path(route["target_path"]) / "docs" / "01_requirements" / "demo_PRD.md"
    assert published.read_text(encoding="utf-8") != CHANGED_PRD, "BLOCKED 之後不發佈"


# ── AT-961-13-4：現態不在矩陣＝409，零寫入 ────────────────────────────────────────────────────
def test_AT_961_13_4_a_state_outside_the_matrix_is_409_and_writes_nothing(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)                       # 內環鍵剛採納完：SPEC_FROZEN（不在矩陣）
    state_file = Path(route["impl_state_dir"]) / f"FSM-STATE-{route['impl_fsm_project']}.yaml"
    before = state_file.read_bytes()
    resp = post_scr(renv, rid)
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert resp.json()["details"]["current_state"] == "SPEC_FROZEN"
    assert scr_rows(renv, rid) == [] and state_file.read_bytes() == before
    assert fsm_ops.current_state(outer(renv, rid)) == "SPEC_FROZEN"


def test_AT_961_13_4_an_escalated_inner_key_is_refused_for_a_normal_minor_scr(
        renv: rgs.RouteEnv) -> None:
    rid, route = at_state(renv, "demo", "IMPLEMENTATION")
    escalate(renv, route)
    resp = post_scr(renv, rid)
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert scr_rows(renv, rid) == []


def test_AT_961_13_4_apply_minor_itself_refuses_a_state_outside_the_matrix(
        renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv)
    env = scr.ScrEnv(cfg=renv.env.settings, db=renv.env.db, writer=renv.env.live.app.state
                     .research.writer)
    row = renv.env.db.get_project(rid)
    base = scr.Baseline(rel="01_specs/PRD-v1.1.0.md", sha256="0" * 64, text="x",
                        from_version_no=1, to_version_no=3, semver="v1.1.0",
                        gate_decision_id="d")
    with pytest.raises(ApiError) as caught:
        scr.apply_minor(env, row, {"id": "00000000-0000-0000-0000-000000000000", "scr_no": 1,
                                   "impl_fsm_actions": []}, approver=ADMIN, base=base)
    assert caught.value.status_code == 409


# ── AT-961-13-6：版本號、決定列、舊版保留、拆解標 STALE ────────────────────────────────────────
@pytest.mark.parametrize(("bump", "semver"), [(None, "v1.1.0"), ("MAJOR", "v2.0.0")])
def test_AT_961_13_6_new_baseline_version_and_the_old_one_is_kept(
        renv: rgs.RouteEnv, bump: str | None, semver: str) -> None:
    rid, route = at_state(renv, "demo", "IMPLEMENTATION")
    renv.rdb.exec(
        "INSERT INTO console.research_decompositions (research_id, path, prd_sha256, "
        "tasks_count, status, created_by) VALUES (%s, 'C', %s, 1, 'SIGNED_OFF', 'seed')", rid,
        "a" * 64)
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    old = (ws / "01_specs" / "PRD-v1.0.0.md").read_bytes()
    old_decisions = renv.rdb.q("SELECT id::text, fsm_stage FROM console.research_gate_decisions "
                               "WHERE research_id = %s ORDER BY decided_at", rid)
    assert post_scr(renv, rid).status_code == 202
    extra = {"version_bump": bump} if bump else {}
    resp = outer_loop(renv, rid, CHANGED_PRD, **extra)
    assert resp.status_code == 200, resp.text
    assert (ws / "01_specs" / f"PRD-{semver}.md").read_text(encoding="utf-8") == CHANGED_PRD
    assert (ws / "01_specs" / "PRD-v1.0.0.md").read_bytes() == old, "舊凍結版保留"
    decisions = renv.rdb.q("SELECT id::text, fsm_stage FROM console.research_gate_decisions "
                           "WHERE research_id = %s AND decision = 'APPROVED' ORDER BY decided_at",
                           rid)
    assert decisions[: len(old_decisions)] == old_decisions and decisions[-1][1] == "Gate-0-SCR1"
    row = renv.rdb.one("SELECT status, prd_from_version_no, prd_to_version_no FROM "
                       "console.research_scr WHERE research_id = %s", rid)
    assert row is not None and row[0] == "APPLIED" and row[1] and row[2] > row[1]
    assert renv.rdb.one("SELECT semver FROM console.research_prd_versions WHERE research_id = %s "
                        "ORDER BY version_no DESC LIMIT 1", rid) == (semver,)
    assert renv.rdb.q("SELECT status FROM console.research_decompositions WHERE research_id = %s",
                      rid) == [("STALE",)]
    assert route


def test_AT_961_13_6_version_bump_without_an_open_scr_is_rejected(renv: rgs.RouteEnv) -> None:
    rid = rgs.seed_gate0(renv, approve=False)
    resp = ap.approve(renv.env, rid, ap.seen(renv.env, rid, ap.BASELINE_REL),
                      version_bump="MAJOR")
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    assert fsm_ops.current_state(outer(renv, rid)) == "HUMAN_PENDING"


# ── AT-961-13-7：游標 ─────────────────────────────────────────────────────────────────────
def test_AT_961_13_7_cursor_goes_to_scr_open_then_back_to_build_or_route(
        renv: rgs.RouteEnv) -> None:
    rid, _route = at_state(renv, "demo", "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    assert cursor(renv, rid)[:2] == ("studio", "SCR_OPEN")
    assert outer_loop(renv, rid, CHANGED_PRD).status_code == 200
    assert cursor(renv, rid)[:2] == ("build", "ROUTED")
    steps = [e[6]["flowPhase"] for e in renv.rdb.events(rid) if e[1] == "research.step"]
    assert "SCR_OPEN" in steps and steps[-1] == "ROUTED"


def test_AT_961_13_7_a_changed_target_scope_returns_to_the_route_step(
        renv: rgs.RouteEnv) -> None:
    rid, _route = at_state(renv, "demo", "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    assert outer_loop(renv, rid, CHANGED_SCOPE_PRD).status_code == 200
    assert cursor(renv, rid)[:2] == ("route", "FROZEN")


# ── AT-961-13-8：發佈順序與失敗 ───────────────────────────────────────────────────────────
def test_AT_961_13_8_publishing_happens_after_spec_audit_and_before_the_refreeze(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid, route = at_state(renv, "demo", "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    log: list[str] = []
    real_transition, real_refreeze, real_write = (
        fsm_ops.transition, fsm_ops.spec_refreeze, fsutil.write_text_atomic)

    def transition(ctx: Any, *, to: str, reason: str) -> str:
        if ctx.key == route["impl_fsm_project"]:
            log.append(f"transition:{to}")
        return real_transition(ctx, to=to, reason=reason)

    def refreeze(ctx: Any, **kw: Any) -> Any:
        log.append("refreeze")
        return real_refreeze(ctx, **kw)

    def write(path: Any, text: str) -> Any:
        if str(path).endswith("demo_PRD.md"):
            log.append("publish")
        return real_write(path, text)

    monkeypatch.setattr(fsm_ops, "transition", transition)
    monkeypatch.setattr(fsm_ops, "spec_refreeze", refreeze)
    monkeypatch.setattr(fsutil, "write_text_atomic", write)
    assert outer_loop(renv, rid, CHANGED_PRD).status_code == 200
    seq = [x for x in log if x in ("transition:SPEC_AUDIT", "publish", "refreeze",
                                   "transition:PR_REVIEW")]
    assert seq == ["transition:SPEC_AUDIT", "publish", "refreeze", "transition:PR_REVIEW"]


def test_AT_961_13_8_a_publish_failure_stops_before_the_refreeze_and_leaves_no_half_file(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid, route = at_state(renv, "demo", "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    real_write = fsutil.write_text_atomic
    target = Path(route["target_path"]) / "docs" / "01_requirements" / "demo_PRD.md"
    before = target.read_bytes()

    def write(path: Any, text: str) -> Any:
        if str(path) == str(target):
            raise PermissionError("read-only destination")
        return real_write(path, text)

    monkeypatch.setattr(fsutil, "write_text_atomic", write)
    resp = outer_loop(renv, rid, CHANGED_PRD)
    assert resp.status_code == 200
    assert resp.json()["scr_apply"]["status"] == "FAILED"
    acts = actions(renv, rid)
    assert [a["label"] for a in acts] == ["transition(SPEC_AUDIT)", "publish"]
    assert acts[-1]["rc"] != 0 and "PermissionError" in acts[-1]["result"]
    assert target.read_bytes() == before, "無半寫檔"
    assert fsm_ops.current_state(inner(renv, route)) == "SPEC_AUDIT"


# ── AT-961-13-E-2／E-3：任一步失敗即停；核准即套用失敗不留空窗，:scr-apply 冪等重試 ──────
def test_AT_961_13_E_3_apply_failure_leaves_the_scr_approved_and_scr_apply_retries_idempotently(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid, route = at_state(renv, "demo", "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    real = fsm_ops.spec_refreeze
    calls = {"n": 0}

    def flaky(ctx: Any, **kw: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ApiError(502, "sdd_cli_failed", detail="injected")
        return real(ctx, **kw)

    monkeypatch.setattr(fsm_ops, "spec_refreeze", flaky)
    resp = outer_loop(renv, rid, CHANGED_PRD)
    assert resp.status_code == 200, resp.text
    assert resp.json()["scr_apply"]["status"] == "FAILED"
    assert scr_rows(renv, rid)[0][2] == "APPROVED"
    assert fsm_ops.current_state(outer(renv, rid)) == "SPEC_FROZEN"
    assert labels(renv, rid) == ["transition(SPEC_AUDIT)", "publish", "spec-refreeze"]
    assert actions(renv, rid)[-1]["rc"] != 0
    assert cursor(renv, rid)[2:] == ("FAILED", "scr_apply_failed:spec-refreeze")
    retry = renv.env.post(f"/research/projects/{rid}:scr-apply", {"scr_no": 1, "approver": ADMIN})
    assert retry.status_code == 200 and retry.json()["status"] == "APPLIED", retry.text
    assert labels(renv, rid) == ["transition(SPEC_AUDIT)", "publish", "spec-refreeze",
                                 "spec-refreeze", "transition(PR_REVIEW)", "gate(PR_REVIEW,FAIL)"]
    assert fsm_ops.current_state(inner(renv, route)) == "IMPLEMENTATION"
    assert cursor(renv, rid)[:2] == ("build", "ROUTED")
    seen: list[str] = []
    real_run = sdd_cli.run_research_verb
    monkeypatch.setattr(sdd_cli, "run_research_verb",
                        lambda verb, *a, **k: (seen.append(verb), real_run(verb, *a, **k))[1])
    again = renv.env.post(f"/research/projects/{rid}:scr-apply", {"scr_no": 1, "approver": ADMIN})
    assert again.status_code == 200 and again.json()["status"] == "APPLIED"
    assert seen == [], "第二次重試冪等：零 FSM 呼叫"


def test_AT_961_13_E_3_scr_apply_requires_an_approved_minor_scr(renv: rgs.RouteEnv) -> None:
    rid, _route = at_state(renv, "demo", "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202            # 仍是 OPEN，尚未核准
    resp = renv.env.post(f"/research/projects/{rid}:scr-apply", {"scr_no": 1, "approver": ADMIN})
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    missing = renv.env.post(f"/research/projects/{rid}:scr-apply", {"scr_no": 9, "approver": ADMIN})
    assert missing.status_code == 404
    bad = renv.env.post(f"/research/projects/{rid}:scr-apply", {"scr_no": 1, "approver": "bridge"})
    assert bad.status_code == 422


def test_AT_961_13_E_2_every_failing_position_stops_the_sequence_there(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """純函式級（不起真 FSM）：把 FSM 動詞換成記錄並在第 k 次呼叫失敗，k＝1、2、3。"""
    rid, route = routed(renv)
    row = renv.env.db.get_project(rid)
    env = scr.ScrEnv(cfg=renv.env.settings, db=renv.env.db,
                     writer=renv.env.live.app.state.research.writer)
    body = rgs.PRD_PLACEMENT
    for k in (1, 2, 3):
        called: list[str] = []

        def make(name: str, k: int = k, called: list[str] = called) -> Any:
            def fn(*_a: Any, **_kw: Any) -> Any:
                called.append(name)
                if len(called) == k:
                    raise ApiError(502, "sdd_cli_failed", detail="injected")
                return {"next_state": "IMPLEMENTATION"} if name == "gate" else "ok"
            return fn

        monkeypatch.setattr(fsm_ops, "current_state", lambda _c: "IMPLEMENTATION")
        monkeypatch.setattr(fsm_ops, "transition", make("transition"))
        monkeypatch.setattr(fsm_ops, "spec_refreeze", make("refreeze"))
        monkeypatch.setattr(fsm_ops, "gate", make("gate"))
        monkeypatch.setattr(scr, "_publish", lambda *_a, **_k: "publish")
        record = {"id": f"00000000-0000-0000-0000-00000000000{k}", "scr_no": k,
                  "impl_fsm_actions": []}
        base = scr.Baseline(rel="01_specs/PRD-v1.1.0.md", sha256="0" * 64, text=body,
                            from_version_no=1, to_version_no=3, semver="v1.1.0",
                            gate_decision_id="d")
        persisted: list[Any] = []
        monkeypatch.setattr(scr, "_persist_actions",
                            lambda _e, _r, _s, acts, **_k: persisted.append(list(acts)))
        out = scr.apply_minor(env, row, record, approver=ADMIN, base=base)
        expected_len = {1: 1, 2: 3, 3: 4}[k]          # 失敗位置之後零呼叫；發佈步驟也計一筆
        assert out.status == "FAILED" and len(called) == k
        assert len(out.actions) == expected_len and out.actions[-1]["rc"] != 0
        assert len(persisted[-1]) == expected_len
    assert route and json.dumps({})
