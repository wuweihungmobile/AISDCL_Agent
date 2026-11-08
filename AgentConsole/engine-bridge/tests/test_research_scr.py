"""SCR 後端：輸入閘、三路（MINOR／MAJOR／HEALING_FAILED）、上限、OPEN 唯一（TCS AT-961-12-*；
PKG-BR-D2）。真 git／真 FSM CLI／拋棄式庫（與分流測試同一組夾具）。

本檔另放 BR-D2 測試共用的助手（`routed`、`inner_to`、`escalate`…），其餘測試檔 import 它。
FSM 的「測試端」呼叫（把內環鍵推到 IMPLEMENTATION 等）直接打框架 CLI 子行程——那是 Given 的佈置，
不是 Bridge 的動作（Bridge 的研究面動詞表不含 `--to IMPLEMENTATION`）。
"""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from app import sdd_cli
from app.errors import ApiError
from app.research import fsm_ops, scr
from tests import research_git_support as rgs
from tests import test_research_router as rt

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
ADMIN = "admin@example.com"


# ── 共用助手（其他 BR-D2 測試檔 import）───────────────────────────────────────────────────────
def cli(renv: rgs.RouteEnv, key: str, state_dir: Path | str, verb: str, *args: str,
        check: bool = True) -> subprocess.CompletedProcess[str]:
    """測試端直接呼叫框架 CLI（與 Bridge 同一組環境與 argv 形狀）。"""
    argv = sdd_cli.build_research_argv(verb, list(args), key)
    env = sdd_cli.build_research_env(os.environ, sdd_root=renv.env.tree,
                                     state_dir=Path(state_dir), project=key)
    proc = subprocess.run(argv, cwd=str(renv.env.tree), env=env, capture_output=True, text=True,
                          encoding="utf-8", check=False)
    if check:
        assert proc.returncode == 0, f"{verb} {args} rc={proc.returncode}: {proc.stderr}"
    return proc


def routed(renv: rgs.RouteEnv, slug: str = "demo", **over: Any) -> tuple[str, dict[str, Any]]:
    """Given：Gate 0 已核准、分流（軌道 A）成功的研究專案；回 `(research_id, 分流列)`。"""
    rid = rgs.seed_gate0(renv, slug)
    resp = rgs.confirm(renv, rid, rgs.body_a(renv, **over))
    assert resp.status_code == 200, resp.text
    route = renv.env.db.active_route(rid)
    assert route is not None
    return rid, route


def inner(renv: rgs.RouteEnv, route: dict[str, Any]) -> fsm_ops.FsmCtx:
    return fsm_ops.FsmCtx(sdd_root=renv.env.tree, state_dir=Path(route["impl_state_dir"]),
                          key=route["impl_fsm_project"])


def outer(renv: rgs.RouteEnv, rid: str) -> fsm_ops.FsmCtx:
    return rt.fsm_ctx_of(renv.env, rid)


def inner_to(renv: rgs.RouteEnv, route: dict[str, Any], target: str) -> None:
    """把內環鍵（SPEC_FROZEN）推到 `target`（Given 的佈置；走框架 CLI）。"""
    key, sdir = route["impl_fsm_project"], route["impl_state_dir"]

    def go(to: str) -> None:
        cli(renv, key, sdir, "transition", "--to", to, "--reason", "given", "--trigger",
            sdk_trigger())

    def gate(name: str, result: str = "PASS", reason: str = "given") -> None:
        cli(renv, key, sdir, "gate", "--gate", name, "--result", result, "--reason", reason)

    go("IMPLEMENTATION")
    if target == "IMPLEMENTATION":
        return
    if target in ("EXECUTION_EVALUATION", "SPEC_AUDIT", "PR_REVIEW"):
        go(target)
    elif target in ("RTM_VERIFY", "RELEASE_READY"):
        go("PR_REVIEW")
        gate("PR_REVIEW")
        if target == "RELEASE_READY":
            gate("RTM_VERIFY")
    else:
        raise AssertionError(f"inner_to 不認得 {target}")
    assert fsm_ops.current_state(inner(renv, route)) == target


def sdk_trigger() -> str:
    return sdd_cli.RESEARCH_TRIGGER


def escalate(renv: rgs.RouteEnv, route: dict[str, Any]) -> None:
    """把內環鍵（已在 IMPLEMENTATION）推進 ESCALATION：PR_REVIEW 連續 FAIL（理由各異，避免『同模式』
    改走 SPEC_AUDIT）。"""
    key, sdir = route["impl_fsm_project"], route["impl_state_dir"]
    for i in range(1, 9):
        state = fsm_ops.current_state(inner(renv, route))
        if state.startswith("ESCALATION"):
            return
        if state == "IMPLEMENTATION":
            cli(renv, key, sdir, "transition", "--to", "PR_REVIEW", "--reason", f"given-{i}",
                "--trigger", sdk_trigger())
        cli(renv, key, sdir, "gate", "--gate", "PR_REVIEW", "--result", "FAIL", "--reason",
            f"distinct failure number {i} with unique text {uuid.uuid4().hex}")
    assert fsm_ops.current_state(inner(renv, route)).startswith("ESCALATION")


def scr_body(**over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "kind": "MINOR", "source_kind": "HUMAN", "reason": "AC 太模糊需要補充",
        "reason_class": "AC_VAGUE", "affected_sections": ["2", "AC-001"], "requested_by": ADMIN}
    body.update(over)
    return body


def post_scr(renv: rgs.RouteEnv, rid: str, **over: Any) -> Any:
    return renv.env.post(f"/research/projects/{rid}:scr", scr_body(**over))


def scr_rows(renv: rgs.RouteEnv, rid: str) -> list[tuple[Any, ...]]:
    return renv.rdb.q("SELECT scr_no, kind, status, source_kind, reason_class, requested_by, "
                      "successor_research_id::text, impl_fsm_actions FROM console.research_scr "
                      "WHERE research_id = %s ORDER BY scr_no", rid)


def cursor(renv: rgs.RouteEnv, rid: str) -> tuple[str, str, str, str]:
    row = renv.rdb.one("SELECT flow_step, flow_phase, flow_status, flow_detail FROM "
                       "console.research_projects WHERE id = %s", rid)
    assert row is not None
    return row[0], row[1], row[2], row[3]


def file_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def seed_scr(renv: rgs.RouteEnv, rid: str, kind: str, status: str, scr_no: int) -> None:
    renv.rdb.exec(
        "INSERT INTO console.research_scr (research_id, scr_no, kind, source_kind, reason, "
        "status, requested_by) VALUES (%s, %s, %s, 'HUMAN', 'seed', %s, 'seed')",
        rid, scr_no, kind, status)


# ── AT-961-12-2：輸入閘（純函式）──────────────────────────────────────────────────────────────
FROZEN = scr.parse_frozen_prd(rgs.PRD_PLACEMENT)


def rules(body: dict[str, Any]) -> list[str]:
    return [v["rule"] for v in scr.validate_request(body, FROZEN)]


def test_AT_961_12_2_the_input_gate_reports_each_violation_as_its_own_entry() -> None:
    assert rules(scr_body()) == []
    assert rules(scr_body(reason="")) == ["reason_empty"]
    assert rules(scr_body(reason="x" * 501)) == ["reason_too_long"]
    assert rules(scr_body(reason="x")) == [] and rules(scr_body(reason="x" * 500)) == []
    assert rules(scr_body(reason_class="BUG")) == ["reason_class_invalid"]
    assert rules(scr_body(affected_sections=["99"])) == ["affected_unknown"]
    assert rules(scr_body(affected_sections=["AC-999"])) == ["affected_unknown"]
    assert rules(scr_body(reason="", reason_class="BUG", affected_sections=["99"])) == [
        "reason_empty", "reason_class_invalid", "affected_unknown"]
    assert rules(scr_body(kind="MEDIUM")) == ["kind_invalid"]
    assert rules(scr_body(source_kind="OTHER")) == ["source_kind_invalid"]
    assert rules(scr_body(reason_class="AC 模糊")) == [], "中文分類也接受"
    assert rules(scr_body(affected_sections=["§2", "2/AC-001"])) == []


def test_AT_961_12_2_endpoint_violations_leave_no_rows_no_fsm_calls_no_cursor_change(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    before = (cursor(renv, rid), file_bytes(Path(route["impl_state_dir"]) / (
        f"FSM-STATE-{route['impl_fsm_project']}.yaml")))
    seen: list[str] = []
    real = sdd_cli.run_research_verb
    monkeypatch.setattr(sdd_cli, "run_research_verb",
                        lambda verb, *a, **k: (seen.append(verb), real(verb, *a, **k))[1])
    resp = post_scr(renv, rid, reason="", reason_class="BUG", affected_sections=["99"])
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    assert [v["rule"] for v in resp.json()["violations"]] == [
        "reason_empty", "reason_class_invalid", "affected_unknown"]
    assert scr_rows(renv, rid) == [] and not [v for v in seen if v != "show"]
    after = (cursor(renv, rid), file_bytes(Path(route["impl_state_dir"]) / (
        f"FSM-STATE-{route['impl_fsm_project']}.yaml")))
    assert before == after


# ── AT-961-12-1、12-3、12-7、12-E-1：MINOR ───────────────────────────────────────────────────
def test_AT_961_12_1_minor_opens_a_row_moves_the_outer_key_and_keeps_the_frozen_prd(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    ws = Path(renv.env.db.get_project(rid)["workspace_path"])
    prd = (ws / "01_specs" / "PRD-v1.0.0.md").read_bytes()
    digests = renv.rdb.one("SELECT frozen_digests FROM console.research_gate_decisions "
                           "WHERE research_id = %s", rid)
    inner_before = file_bytes(Path(route["impl_state_dir"]) / (
        f"FSM-STATE-{route['impl_fsm_project']}.yaml"))
    resp = post_scr(renv, rid)
    assert resp.status_code == 202, resp.text
    assert resp.json() == {"scr_no": 1, "status": "OPEN"}
    rows = scr_rows(renv, rid)
    assert len(rows) == 1 and rows[0][1:6] == ("MINOR", "OPEN", "HUMAN", "AC_VAGUE", ADMIN)
    assert fsm_ops.current_state(outer(renv, rid)) == "SPEC_DRAFTING"
    trace = fsm_ops.show(outer(renv, rid))["decision_trace"][-1]
    assert "進入 Stage Gate-0-SCR1" in json.dumps(trace, ensure_ascii=False)
    assert fsm_ops.current_state(inner(renv, route)) == "IMPLEMENTATION", "內環鍵現態不變"
    assert file_bytes(Path(route["impl_state_dir"]) / (
        f"FSM-STATE-{route['impl_fsm_project']}.yaml")) == inner_before
    assert (ws / "01_specs" / "PRD-v1.0.0.md").read_bytes() == prd
    assert renv.rdb.one("SELECT frozen_digests FROM console.research_gate_decisions "
                        "WHERE research_id = %s", rid) == digests
    assert cursor(renv, rid)[:2] == ("studio", "SCR_OPEN")
    kinds = [e[1] for e in renv.rdb.events(rid)]
    assert "research.scr" in kinds and kinds[-1] in ("research.step", "research.scr")
    payload = next(e[6] for e in renv.rdb.events(rid) if e[1] == "research.scr")
    assert payload == {"scrNo": 1, "kind": "MINOR", "status": "OPEN"}


def test_AT_961_12_3_an_open_scr_blocks_both_resume_and_start_and_touches_nothing(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    state_file = Path(route["impl_state_dir"]) / f"FSM-STATE-{route['impl_fsm_project']}.yaml"
    before = file_bytes(state_file)
    for intent in ("resume", "start"):
        with pytest.raises(Exception) as caught:
            scr.guard_inner_start(renv.env.db, rid, intent)
        assert caught.value.status_code == 409 and caught.value.body["reason"] == "scr_open"
    assert file_bytes(state_file) == before
    assert scr_rows(renv, rid)[0][2] == "OPEN"


def test_AT_961_12_E_2_outer_transition_failure_marks_the_scr_rejected_and_restores_the_cursor(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """open_minor 的補償（F-09；TCS 無此條，勘誤候選 AT-961-12-E-2）：外環轉態失敗 ⇒ SCR 列標
    REJECTED（不留永遠 OPEN 的列）、游標還原為開 SCR 之前、錯誤原樣拋出、槽位釋出可再開。"""
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    before = cursor(renv, rid)
    real = fsm_ops.transition

    def broken(*args: Any, **kwargs: Any) -> str:
        raise ApiError(502, "fsm_cli_failed")
    monkeypatch.setattr(fsm_ops, "transition", broken)
    resp = post_scr(renv, rid)
    assert resp.status_code == 502, resp.text
    [row] = scr_rows(renv, rid)
    assert row[2] == "REJECTED", "補償：不留一筆永遠 OPEN 的 SCR"
    assert cursor(renv, rid) == before, "游標還原"
    monkeypatch.setattr(fsm_ops, "transition", real)
    assert post_scr(renv, rid).status_code == 202, "REJECTED 釋出槽位，可再開"


def test_AT_961_12_7_only_one_open_scr_per_project_and_a_closed_one_frees_the_slot(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    for kind in ("MINOR", "MAJOR"):
        resp = post_scr(renv, rid, kind=kind)
        assert (resp.status_code, resp.json()["reason"]) == (409, "scr_open")
    assert len(scr_rows(renv, rid)) == 1
    renv.rdb.exec("UPDATE console.research_scr SET status = 'APPLIED' WHERE research_id = %s",
                  rid)
    resp = post_scr(renv, rid, kind="MAJOR")
    assert resp.status_code == 202, resp.text


def test_AT_961_12_E_1_no_running_run_is_not_an_error(renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    assert renv.env.db.active_stage_run(rid) is None
    assert post_scr(renv, rid).status_code == 202


# ── AT-961-12-4：上限 ──────────────────────────────────────────────────────────────────────
def test_AT_961_12_4_the_minor_limit_counts_open_approved_applied_only(
        renv: rgs.RouteEnv) -> None:
    assert scr.SCR_MINOR_MAX == 2
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    seed_scr(renv, rid, "MINOR", "APPLIED", 1)
    seed_scr(renv, rid, "MINOR", "APPROVED", 2)
    resp = post_scr(renv, rid)
    assert (resp.status_code, resp.json()["reason"]) == (409, "scr_limit")
    assert resp.json()["details"] == {"limit": 2, "used": 2, "hint": "改 MAJOR"}
    assert len(scr_rows(renv, rid)) == 2
    renv.rdb.exec("UPDATE console.research_scr SET status = 'REJECTED' WHERE research_id = %s "
                  "AND scr_no = 2", rid)
    assert post_scr(renv, rid).status_code == 202, "REJECTED 不佔額度"


def test_AT_961_12_4_major_is_not_limited(renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    seed_scr(renv, rid, "MINOR", "APPLIED", 1)
    seed_scr(renv, rid, "MINOR", "APPLIED", 2)
    resp = post_scr(renv, rid, kind="MAJOR", affected_sections=[])
    assert resp.status_code == 202, resp.text


# ── AT-961-12-5：MAJOR ─────────────────────────────────────────────────────────────────────
def test_AT_961_12_5_major_creates_a_successor_project_and_leaves_the_old_keys_alone(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    old_cursor = cursor(renv, rid)
    old_inner = file_bytes(Path(route["impl_state_dir"]) / (
        f"FSM-STATE-{route['impl_fsm_project']}.yaml"))
    resp = post_scr(renv, rid, kind="MAJOR", reason_class="EVIDENCE", affected_sections=[])
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "SUPERSEDED" and body["scr_no"] == 1
    new = renv.env.db.get_project(body["successor_research_id"])
    assert new is not None
    assert (str(new["parent_research_id"]), new["slug"], new["fsm_project"]) == (
        rid, "demo-scr1", "research-demo-scr1")
    assert (new["flow_step"], new["flow_phase"]) == ("topic", "INGESTED")
    assert fsm_ops.current_state(rt.fsm_ctx_of(renv.env, new["id"])) == "AGENT_LOAD"
    rows = scr_rows(renv, rid)
    assert rows[0][1:3] == ("MAJOR", "SUPERSEDED") and rows[0][6] == str(new["id"])
    now = cursor(renv, rid)
    assert now[:2] == old_cursor[:2] and now[3] == f"已被 {new['rp_no']} 取代"
    assert file_bytes(Path(route["impl_state_dir"]) / (
        f"FSM-STATE-{route['impl_fsm_project']}.yaml")) == old_inner
    assert fsm_ops.current_state(outer(renv, rid)) == "SPEC_FROZEN"


# ── D-136：MAJOR 後繼 slug 確定性截斷（不再有 successor_slug_invalid）──────────────────────────
LONG_SLUG = "abcdefghij" * 2 + "abcdefg"      # 27 字：加 "-scr1" 後逾 30 字上限


def test_D_136_a_27_char_slug_is_truncated_deterministically_for_the_major_successor(
        renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv, LONG_SLUG)
    resp = post_scr(renv, rid, kind="MAJOR", reason_class="EVIDENCE", affected_sections=[])
    assert resp.status_code == 202, resp.text
    new = renv.env.db.get_project(resp.json()["successor_research_id"])
    assert new is not None
    assert new["slug"] == LONG_SLUG[:25] + "-scr1" and len(new["slug"]) == 30
    assert "successor_slug_invalid" not in resp.text


def test_D_136_a_trailing_dash_left_by_the_cut_is_stripped(renv: rgs.RouteEnv) -> None:
    old = "abcdefghij" * 2 + "abcd-xyz"             # 第 25 字落在 `-` 上
    rid, _route = routed(renv, old)
    resp = post_scr(renv, rid, kind="MAJOR", reason_class="EVIDENCE", affected_sections=[])
    assert resp.status_code == 202, resp.text
    new = renv.env.db.get_project(resp.json()["successor_research_id"])
    assert new is not None and new["slug"] == "abcdefghijabcdefghijabcd-scr1"


def test_D_136_a_truncated_slug_that_collides_is_409_slug_in_use_and_writes_nothing(
        renv: rgs.RouteEnv) -> None:
    rid, _route = routed(renv, LONG_SLUG)
    clash = LONG_SLUG[:25] + "-scr1"
    rgs.seed_gate0(renv, clash)
    before = scr_rows(renv, rid)
    resp = post_scr(renv, rid, kind="MAJOR", reason_class="EVIDENCE", affected_sections=[])
    assert (resp.status_code, resp.json()["reason"]) == (409, "slug_in_use")
    assert scr_rows(renv, rid) == before


# ── AT-961-12-6：HEALING_FAILED ─────────────────────────────────────────────────────────────
def test_AT_961_12_6_healing_failed_returns_a_recovery_command_and_writes_no_fsm_verb(
        renv: rgs.RouteEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    escalate(renv, route)
    seen: list[str] = []
    real = sdd_cli.run_research_verb
    monkeypatch.setattr(sdd_cli, "run_research_verb",
                        lambda verb, *a, **k: (seen.append(verb), real(verb, *a, **k))[1])
    resp = post_scr(renv, rid, source_kind="HEALING_FAILED")
    assert resp.status_code == 200, resp.text
    recovery = resp.json()["recovery"]
    assert recovery["target"] == "SPEC_DRAFTING"
    for shell in ("powershell", "posix"):
        assert "resume-from-escalation" in recovery[shell]
        assert "--to SPEC_DRAFTING" in recovery[shell]
        assert route["impl_fsm_project"] in recovery[shell]
    assert [v for v in seen if v != "show"] == []
    rows = scr_rows(renv, rid)
    assert rows[0][2:4] == ("OPEN", "HEALING_FAILED")
    assert "resume-from-escalation" not in sdd_cli.RESEARCH_VERBS
    assert fsm_ops.current_state(inner(renv, route)).startswith("ESCALATION")


def test_AT_961_12_6_healing_failed_is_refused_when_the_inner_key_is_not_escalated(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    resp = post_scr(renv, rid, source_kind="HEALING_FAILED")
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert scr_rows(renv, rid) == []


def test_matrix_pre_is_table_driven_from_the_mirror_edges() -> None:
    expected: dict[str, str | None] = {
        "IMPLEMENTATION": "transition(SPEC_AUDIT)", "EXECUTION_EVALUATION":
        "transition(SPEC_AUDIT)", "ADVERSARIAL_EVALUATION": "transition(SPEC_AUDIT)",
        "PR_REVIEW": "transition(SPEC_AUDIT)", "SPEC_AUDIT": "",
        "RTM_VERIFY": "gate(RTM_VERIFY,FAIL)", "RELEASE_READY": "gate(RELEASE_READY,FAIL)"}
    for state, pre in expected.items():
        assert scr.matrix_pre(state) == pre, state
    for state in ("INIT", "AGENT_LOAD", "SPEC_DRAFTING", "SPEC_FROZEN", "ESCALATION",
                  "ESCALATION_FINAL", "AUTO_RECOVERY_ATTEMPT", "RELEASE", "HUMAN_PENDING"):
        assert scr.matrix_pre(state) is None, state


_unused: Callable[..., Any] | None = None


# ══ P2（PKG-BR-P2；AT-962-15-7、15-8）：`evidence_url`。以下 append-only，P1 既有 AT 零改動 ═══════
def evidence_row(renv: rgs.RouteEnv, rid: str) -> tuple[Any, ...]:
    row = renv.rdb.one("SELECT evidence_url, reason FROM console.research_scr "
                       "WHERE research_id = %s", rid)
    assert row is not None
    return row


def test_AT_962_15_7_the_scr_endpoint_stores_a_valid_evidence_url_verbatim(
        renv: rgs.RouteEnv) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    for bad, rule in (("http://ci.example.com/run/1", "evidence_not_https"),
                      ("https://x.example.com/" + "a" * 500, "evidence_too_long")):
        resp = post_scr(renv, rid, evidence_url=bad)
        assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
        assert [v["rule"] for v in resp.json()["violations"]] == [rule]
    assert scr_rows(renv, rid) == []
    good = "https://ci.example.com/run/1?x=1"
    resp = post_scr(renv, rid, evidence_url=good)
    assert resp.status_code == 202, resp.text
    assert evidence_row(renv, rid) == (good, scr_body()["reason"]), "reason 與輸入逐字相同"
    other, route2 = routed(renv, "other")
    inner_to(renv, route2, "IMPLEMENTATION")
    assert post_scr(renv, other).status_code == 202
    assert evidence_row(renv, other)[0] is None


def test_AT_962_15_8_the_scr_open_insert_lists_evidence_url_and_matches_its_parameters(
        renv: rgs.RouteEnv) -> None:
    import re

    from app.research import db as db_module

    sql = db_module._SQL_INSERT_SCR
    columns = [c.strip() for c in re.search(r"\(([^)]*)\) VALUES", sql).group(1).split(",")]
    values = sql.split("VALUES", 1)[1]
    assert "evidence_url" in columns and columns[-1] == "evidence_url"
    assert values.count("%s") == len(columns)
    rid = rgs.seed_gate0(renv, "ev-unit")
    url = "https://ci.example.com/x"
    renv.env.db.apply("scr.open", {
        "research_id": rid, "scr_id": str(uuid.uuid4()), "kind": "MAJOR", "source_kind": "HUMAN",
        "reason": "r", "requested_by": ADMIN, "evidence_url": url})
    assert evidence_row(renv, rid)[0] == url


# ── D-168：「受影響章節」兩端對拍（前端 scrSectionOptions 與 Bridge parse_frozen_prd 同一份夾具）──
SECTION_CASES = Path(__file__).resolve().parent / "fixtures" / "research" / (
    "scr_section_options_cases.json")


def test_section_options_fixture_matches_parse_frozen_prd() -> None:
    case = json.loads(SECTION_CASES.read_text(encoding="utf-8"))
    parsed = scr.parse_frozen_prd(case["prd"])
    assert parsed.sections == frozenset(case["bridgeSections"])
    assert parsed.acs == frozenset(case["acs"])
    # 前端選項值（標題自身編號＋AC）必須全被 Bridge 接受；佔位 AC-NNN-Y 與標題全文不被接受
    for value in [*case["headingSections"], *case["acs"]]:
        assert scr.validate_request(
            {"kind": "MINOR", "source_kind": "HUMAN", "reason": "r",
             "affected_sections": [value]}, parsed) == [], value
    for bad in ("AC-NNN-Y", "1. 專案願景與目標"):
        assert scr.validate_request(
            {"kind": "MINOR", "source_kind": "HUMAN", "reason": "r",
             "affected_sections": [bad]}, parsed), bad
