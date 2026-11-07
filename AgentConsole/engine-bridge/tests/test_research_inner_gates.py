"""內環 SCG-4／SCG-5／SCG-6 登錄 `:gates`（TCS AT-962-3-*；PKG-BR-P2）。

真 FSM CLI、暫存狀態目錄、真 git／假 gh／拋棄式庫（P1 分流測試的同一組夾具 `renv`）；內環鍵由
分流的採納序列建出，再用框架 CLI 把它推到各現態（Given 的佈置，不是 Bridge 的動作）。缺 `SDD_ROOT`
或 `BRIDGE_TEST_DSN`＝`TOOL-ABSENCE` skip（SCG-4 證據須 0 skipped）。

本檔另放 P2 其餘測試檔共用的助手（`RtmFixture`、`rtm`、`verbs`、`post_gate`、`gate_rows`、
`back_to`、`seed_run`…），它們 import 本檔。
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest

from app import sdd_cli
from app.research import fsm_ops, inner_gates
from app.research.db import EVENT_PAYLOAD_KEYS
from app.routers import research_deliver
from tests import research_git_support as rgs
from tests import test_research_router as rt
from tests.test_research_scr import (
    ADMIN,
    cli,
    cursor,
    inner,
    inner_to,
    post_scr,
    routed,
    scr_rows,
    sdk_trigger,
)
from tests.test_research_scr_fsm import CHANGED_PRD, outer_loop, trace_tail

make_env = rt.make_env
route_db, real_tree, renv, fake_gh = rgs.route_db, rgs.real_tree, rgs.renv, rgs.fake_gh
GATE_ROWS_SQL = (
    "SELECT gate, decision, decided_by, fsm_project, fsm_state_after, reason, audit_trace_id, "
    "details FROM console.research_gate_decisions WHERE research_id = %s AND "
    "gate IN ('SCG4', 'SCG5', 'SCG6') ORDER BY decided_at, id")


# ── 共用助手 ──────────────────────────────────────────────────────────────────────────────────
class RtmFixture:
    """假的 RTM 報告目錄：`checkpoint_dir_for` 被換成它（同引擎寫的 RTM-COVERAGE 檔形狀）。"""

    def __init__(self, root: Path) -> None:
        self.dir = root

    def write(self, *, fully: bool = True, pct: float = 100.0) -> None:
        folder = self.dir / "rtm"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "RTM-COVERAGE-demo.yaml").write_text(
            "scenario: greenfield\nspec_digest: abc\nsummary:\n  passed_at: 10\n  total_at: 10\n"
            f"  at_coverage_pct: 100.0\n  covered_ac: 3\n  total_ac: 3\n  ac_coverage_pct: {pct}\n"
            f"  fully_covered: {'true' if fully else 'false'}\n", encoding="utf-8", newline="\n")

    def remove(self) -> None:
        (self.dir / "rtm" / "RTM-COVERAGE-demo.yaml").unlink(missing_ok=True)


@pytest.fixture
def rtm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> RtmFixture:
    holder = RtmFixture(tmp_path / "chk")
    holder.write()
    monkeypatch.setattr(research_deliver, "checkpoint_dir_for", lambda request, run_id: holder.dir)
    return holder


class VerbLog(list[tuple[str, tuple[str, ...]]]):
    def writes(self) -> list[tuple[str, tuple[str, ...]]]:
        return [v for v in self if v[0] != "show"]

    def verbs(self) -> list[str]:
        return [v[0] for v in self.writes()]


@pytest.fixture
def verbs(monkeypatch: pytest.MonkeyPatch) -> VerbLog:
    """每次 FSM 研究面動詞呼叫（動詞名與 argv）；呼叫照常執行。"""
    log = VerbLog()
    real = sdd_cli.run_research_verb

    def wrapper(verb: str, args: Any, *a: Any, **k: Any) -> Any:
        log.append((verb, tuple(args)))
        return real(verb, args, *a, **k)

    monkeypatch.setattr(sdd_cli, "run_research_verb", wrapper)
    return log


def gate_body(gate: str = "PR_REVIEW", result: str = "PASS", **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "decision_id": str(uuid.uuid4()), "gate": gate, "result": result,
        "reason": f"審查結論 {uuid.uuid4().hex[:8]}", "review_report_ref": None,
        "reviewer_independent": True, "approver": ADMIN, "run_id": str(uuid.uuid4()),
        "requested_by": ADMIN}
    body.update(over)
    return body


def post_gate(renv: rgs.RouteEnv, rid: str, gate: str = "PR_REVIEW", result: str = "PASS",
              **over: Any) -> Any:
    return renv.env.post(f"/research/projects/{rid}:gates", gate_body(gate, result, **over))


def gate_rows(renv: rgs.RouteEnv, rid: str) -> list[tuple[Any, ...]]:
    return renv.rdb.q(GATE_ROWS_SQL, rid)


def back_to(renv: rgs.RouteEnv, route: dict[str, Any], target: str) -> None:
    """內環鍵自 IMPLEMENTATION 經框架 CLI 回到 `target`（PR_REVIEW／RTM_VERIFY／RELEASE_READY）。"""
    key, sdir = route["impl_fsm_project"], route["impl_state_dir"]
    cli(renv, key, sdir, "transition", "--to", "PR_REVIEW", "--reason", "given", "--trigger",
        sdk_trigger())
    if target == "PR_REVIEW":
        return
    cli(renv, key, sdir, "gate", "--gate", "PR_REVIEW", "--result", "PASS", "--reason", "given")
    if target == "RELEASE_READY":
        cli(renv, key, sdir, "gate", "--gate", "RTM_VERIFY", "--result", "PASS", "--reason",
            "given")


def inner_state(renv: rgs.RouteEnv, route: dict[str, Any]) -> str:
    return fsm_ops.current_state(inner(renv, route))


def state_bytes(route: dict[str, Any]) -> bytes:
    return (Path(route["impl_state_dir"]) / f"FSM-STATE-{route['impl_fsm_project']}.yaml"
            ).read_bytes()


def events_of(renv: rgs.RouteEnv, rid: str, kind: str) -> list[dict[str, Any]]:
    return [e[6] for e in renv.rdb.events(rid) if e[1] == kind]


def blocking_context(renv: rgs.RouteEnv) -> Any:
    return renv.env.live.app.state.research


def run_until_escalated(renv: rgs.RouteEnv, rid: str, route: dict[str, Any], gate: str,
                        start: str, *, at_start: bool = True) -> list[dict[str, Any]]:
    """反覆登錄 FAIL（理由各異）直到引擎回 ESCALATION；回每次的回應本文。FAIL 後內環鍵回
    IMPLEMENTATION，下一輪先用框架 CLI 回到 `start`（RTM_VERIFY／RELEASE_READY 時）。"""
    seen: list[dict[str, Any]] = []
    for attempt in range(12):
        if gate != "PR_REVIEW" and (attempt or not at_start):
            back_to(renv, route, start)
        resp = post_gate(renv, rid, gate, "FAIL", reason=f"{uuid.uuid4().hex} {uuid.uuid4().hex}")
        assert resp.status_code == 200, resp.text
        seen.append(resp.json())
        if resp.json()["escalated"] or resp.json()["next_state"] != "IMPLEMENTATION":
            return seen
    raise AssertionError("12 次 FAIL 仍未升級：預算常數異常")


# ── AT-962-3-1：SCG-4 登錄序列與人工等價序列 ─────────────────────────────────────────────────────
def test_AT_962_3_1_scg4_runs_transition_then_gate_and_equals_the_manual_trace(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    verbs.clear()
    resp = post_gate(renv, rid, "PR_REVIEW", "PASS")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert (body["gate"], body["result"], body["fsm_state_before"], body["next_state"],
            body["escalated"]) == ("PR_REVIEW", "PASS", "IMPLEMENTATION", "RTM_VERIFY", False)
    assert body["gate_decision_id"] and set(body["flow"]) == {"step", "phase", "status", "detail"}
    assert [(v, a[a.index("--to") + 1] if v == "transition" else a[a.index("--gate") + 1])
            for v, a in verbs.writes()] == [("transition", "PR_REVIEW"), ("gate", "PR_REVIEW")]
    transition_args = verbs.writes()[0][1]
    assert transition_args[transition_args.index("--trigger") + 1] == "research_bridge"
    assert "SCG-4 registration; research=" in transition_args[transition_args.index("--reason") + 1]
    bridge_trace = trace_tail(inner(renv, route), 2)
    assert "SCG-4 registration; research=" in json.dumps(
        fsm_ops.show(inner(renv, route))["decision_trace"][-2], ensure_ascii=False)
    rid2, route2 = routed(renv, "demo2")                         # 人工等價序列：同一份 CLI
    inner_to(renv, route2, "IMPLEMENTATION")
    key, sdir = route2["impl_fsm_project"], route2["impl_state_dir"]
    cli(renv, key, sdir, "transition", "--to", "PR_REVIEW", "--reason", "manual", "--trigger",
        sdk_trigger())
    cli(renv, key, sdir, "gate", "--gate", "PR_REVIEW", "--result", "PASS", "--reason", "manual")
    assert bridge_trace == trace_tail(inner(renv, route2), 2)
    assert rid2


# ── AT-962-3-2：PR_REVIEW 現態矩陣 ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("state", ["IMPLEMENTATION", "EXECUTION_EVALUATION",
                                   "ADVERSARIAL_EVALUATION", "PR_REVIEW"])
def test_AT_962_3_2_pr_review_transitions_first_except_when_already_in_pr_review(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog, monkeypatch: pytest.MonkeyPatch,
        state: str) -> None:
    rid, route = routed(renv, f"m-{state.lower().replace('_', '-')[:8]}")
    inner_to(renv, route, "IMPLEMENTATION" if state == "ADVERSARIAL_EVALUATION" else state)
    verbs.clear()
    if state == "ADVERSARIAL_EVALUATION":
        # 研究面入口到不了這個現態（框架 CLI 的內環動詞表不收）：讓前兩次讀回報它、之後讀真值
        real, calls = fsm_ops.read_current, {"n": 0}

        def fake(ctx: fsm_ops.FsmCtx) -> dict[str, Any]:
            calls["n"] += 1
            return {"current_state": state} if calls["n"] <= 2 else real(ctx)

        monkeypatch.setattr(fsm_ops, "read_current", fake)
    resp = post_gate(renv, rid, "PR_REVIEW", "PASS")
    assert resp.status_code == 200, f"{state}: {resp.text}"
    assert resp.json()["fsm_state_before"] == state and resp.json()["next_state"] == "RTM_VERIFY"
    expected = ["gate"] if state == "PR_REVIEW" else ["transition", "gate"]
    assert verbs.verbs() == expected, state


# ── AT-962-3-3：PR_REVIEW FAIL 與預算邊界（以引擎回傳為準）─────────────────────────
def test_AT_962_3_3_pr_review_fail_returns_to_implementation_until_the_engine_escalates(
        renv: rgs.RouteEnv, rtm: RtmFixture) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    seen = run_until_escalated(renv, rid, route, "PR_REVIEW", "PR_REVIEW")
    assert len(seen) >= 2, "預算不會只有一次"
    for body in seen[:-1]:
        assert body["next_state"] == "IMPLEMENTATION" and body["escalated"] is False
    last = seen[-1]
    assert last["next_state"].startswith("ESCALATION") and last["escalated"] is True
    assert cursor(renv, rid)[2] == "ESCALATED"
    assert any(p["kind"] == "ESCALATED" for p in events_of(renv, rid, "research.alert"))
    again = post_gate(renv, rid, "PR_REVIEW", "FAIL", reason="beyond the limit")
    assert (again.status_code, again.json()["reason"]) == (409, "fsm_state_conflict")


# ── AT-962-3-4：SCG-5 ───────────────────────────────────────────────────────────────────────────
def test_AT_962_3_4_rtm_verify_pass_reaches_release_ready_with_a_single_literal_gate(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "RTM_VERIFY")
    verbs.clear()
    resp = post_gate(renv, rid, "RTM_VERIFY", "PASS")
    assert resp.status_code == 200 and resp.json()["next_state"] == "RELEASE_READY", resp.text
    assert verbs.verbs() == ["gate"] and verbs.writes()[0][1][1] == "RTM_VERIFY"


def test_AT_962_3_4_rtm_verify_fail_returns_to_implementation_until_the_engine_escalates(
        renv: rgs.RouteEnv, rtm: RtmFixture) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "RTM_VERIFY")
    seen = run_until_escalated(renv, rid, route, "RTM_VERIFY", "RTM_VERIFY")
    for body in seen[:-1]:
        assert body["next_state"] == "IMPLEMENTATION"
    assert seen[-1]["escalated"] is True and seen[-1]["next_state"].startswith("ESCALATION")


# ── AT-962-3-5：SCG-6（RELEASE_READY FAIL）────────────────────────────────────────────────────
def test_AT_962_3_5_release_ready_fail_registers_scg6_with_ci_red(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "RELEASE_READY")
    verbs.clear()
    resp = post_gate(renv, rid, "RELEASE_READY", "FAIL", reason="雲端 CI 紅")
    assert resp.status_code == 200 and resp.json()["next_state"] == "IMPLEMENTATION", resp.text
    assert verbs.verbs() == ["gate"]
    args = verbs.writes()[0][1]
    assert args[args.index("--gate") + 1] == "RELEASE_READY" and "FAIL" in args
    assert args[args.index("--reason") + 1] == "雲端 CI 紅"
    row = gate_rows(renv, rid)[-1]
    assert (row[0], row[1], row[5]) == ("SCG6", "REJECTED", "雲端 CI 紅")
    assert row[7]["ci_red"] is True and "[" not in row[5]
    seen = run_until_escalated(renv, rid, route, "RELEASE_READY", "RELEASE_READY",
                               at_start=False)
    assert seen[-1]["escalated"] is True


# ── AT-962-3-6：決定列映射 ──────────────────────────────────────────────────────────────────────
def test_AT_962_3_6_decision_rows_map_gate_and_result_and_carry_details(
        renv: rgs.RouteEnv, rtm: RtmFixture) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    assert post_gate(renv, rid, "PR_REVIEW", "FAIL", reason="缺測試").status_code == 200
    back_to(renv, route, "PR_REVIEW")
    ok = post_gate(renv, rid, "PR_REVIEW", "PASS", reason="修好了", review_report_ref="docs/r.md")
    assert ok.status_code == 200, ok.text
    assert post_gate(renv, rid, "RTM_VERIFY", "FAIL", reason="覆蓋不足").status_code == 200
    back_to(renv, route, "RTM_VERIFY")
    assert post_gate(renv, rid, "RTM_VERIFY", "PASS", reason="全覆蓋").status_code == 200
    assert post_gate(renv, rid, "RELEASE_READY", "FAIL", reason="CI 紅").status_code == 200
    rows = gate_rows(renv, rid)
    assert [(r[0], r[1]) for r in rows] == [
        ("SCG4", "REJECTED"), ("SCG4", "APPROVED"), ("SCG5", "REJECTED"), ("SCG5", "APPROVED"),
        ("SCG6", "REJECTED")]
    assert rows[1][7] == {"reviewer_independent": True, "review_report_ref": "docs/r.md"}
    assert rows[0][7] == {"reviewer_independent": True, "review_report_ref": None}
    assert rows[4][7] == {"reviewer_independent": True, "review_report_ref": None, "ci_red": True}
    assert {r[2] for r in rows} == {ADMIN} and {r[3] for r in rows} == {route["impl_fsm_project"]}
    assert [r[5] for r in rows] == ["缺測試", "修好了", "覆蓋不足", "全覆蓋", "CI 紅"]
    assert rows[1][4] == "RTM_VERIFY" and rows[3][4] == "RELEASE_READY"
    assert all(r[6] is None or isinstance(r[6], str) for r in rows)
    gate_events = events_of(renv, rid, "research.gate")
    assert all(set(p) == EVENT_PAYLOAD_KEYS["research.gate"] for p in gate_events)
    assert {p["gate"] for p in gate_events} >= {"SCG4", "SCG5", "SCG6"}


# ── AT-962-3-7：RTM 零信任重驗 ──────────────────────────────────────────────────────────────────
def unmet_of(resp: Any) -> list[str]:
    return list(resp.json()["details"]["unmet"])


def test_AT_962_3_7_pr_review_needs_a_fully_covered_report(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    before, verbs_before = state_bytes(route), len(verbs)
    rtm.write(fully=False)
    for setup in ("not-full", "missing"):
        if setup == "missing":
            rtm.remove()
        resp = post_gate(renv, rid, "PR_REVIEW", "PASS")
        assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict"), setup
        assert unmet_of(resp) == ["rtm_below_100"], setup
    assert gate_rows(renv, rid) == [] and state_bytes(route) == before
    assert len(verbs) == verbs_before, "零 FSM 寫入"
    rtm.write(fully=True)
    assert post_gate(renv, rid, "PR_REVIEW", "PASS").status_code == 200


@pytest.mark.parametrize("pct", [99.99, 99.0, 0.0])
def test_AT_962_3_7_rtm_verify_needs_exactly_one_hundred_percent(
        renv: rgs.RouteEnv, rtm: RtmFixture, pct: float) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "RTM_VERIFY")
    rtm.write(fully=True, pct=pct)
    resp = post_gate(renv, rid, "RTM_VERIFY", "PASS")
    assert resp.status_code == 409 and unmet_of(resp) == ["rtm_below_100"], resp.text
    assert gate_rows(renv, rid) == [] and inner_state(renv, route) == "RTM_VERIFY"
    rtm.remove()
    assert post_gate(renv, rid, "RTM_VERIFY", "PASS").status_code == 409
    rtm.write(pct=100)
    assert post_gate(renv, rid, "RTM_VERIFY", "PASS").status_code == 200


# ── AT-962-3-8：冪等 ────────────────────────────────────────────────────────────────────────────
def test_AT_962_3_8_a_repeated_decision_id_returns_the_same_row_without_new_writes(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    body = gate_body("PR_REVIEW", "PASS")
    first = renv.env.post(f"/research/projects/{rid}:gates", body)
    assert first.status_code == 200, first.text
    calls, rows, events = len(verbs), gate_rows(renv, rid), len(renv.rdb.events(rid))
    second = renv.env.post(f"/research/projects/{rid}:gates", body)
    assert second.status_code == 200
    assert second.json()["gate_decision_id"] == first.json()["gate_decision_id"]
    assert len(verbs) == calls and gate_rows(renv, rid) == rows
    assert len(renv.rdb.events(rid)) == events


# ── AT-962-3-9：與 SCR 共存 ─────────────────────────────────────────────────────────────────────
def test_AT_962_3_9_an_open_scr_blocks_gates_and_the_scr_sequence_writes_no_scg4_row(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    assert post_scr(renv, rid).status_code == 202
    verbs.clear()
    resp = post_gate(renv, rid, "PR_REVIEW", "PASS")
    assert (resp.status_code, resp.json()["reason"]) == (409, "scr_open")
    assert verbs.writes() == [] and gate_rows(renv, rid) == []
    rid2, route2 = routed(renv, "demo2")
    inner_to(renv, route2, "IMPLEMENTATION")
    assert post_scr(renv, rid2).status_code == 202
    assert outer_loop(renv, rid2, CHANGED_PRD).status_code == 200
    assert scr_rows(renv, rid2)[0][2] == "APPLIED"
    assert gate_rows(renv, rid2) == [], "SCR 序列內部的 gate PR_REVIEW FAIL 不寫 SCG4 列"


# ── AT-962-3-E-1：矩陣外的現態 ──────────────────────────────────────────────────────────────────
OUTSIDE = ["INIT", "SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING", "SCG_VALIDATION",
           "HUMAN_PENDING", "SPEC_FROZEN", "SPEC_AUDIT", "RELEASE", "ESCALATION",
           "ESCALATION_FINAL"]


def test_AT_962_3_E_1_every_state_outside_the_matrix_is_409_with_zero_writes(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog,
        monkeypatch: pytest.MonkeyPatch) -> None:
    rid, _route = routed(renv)
    verbs.clear()
    events = len(renv.rdb.events(rid))
    for state in OUTSIDE:
        monkeypatch.setattr(fsm_ops, "read_current", lambda ctx, s=state: {"current_state": s})
        for gate in inner_gates.GATES:
            result = "FAIL" if gate == "RELEASE_READY" else "PASS"
            resp = post_gate(renv, rid, gate, result)
            assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict"), (
                state, gate)
            assert resp.json()["details"]["current_state"] == state
    for state, gate in (("IMPLEMENTATION", "RTM_VERIFY"), ("RTM_VERIFY", "PR_REVIEW"),
                        ("PR_REVIEW", "RELEASE_READY")):
        monkeypatch.setattr(fsm_ops, "read_current", lambda ctx, s=state: {"current_state": s})
        resp = post_gate(renv, rid, gate, "FAIL" if gate == "RELEASE_READY" else "PASS")
        assert resp.status_code == 409 and resp.json()["details"]["current_state"] == state
    assert verbs.writes() == [] and gate_rows(renv, rid) == []
    assert len(renv.rdb.events(rid)) == events


# ── AT-962-3-E-2：沒有 SUCCEEDED 分流 ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("status", [None, "PENDING", "FAILED", "COMPENSATED"])
def test_AT_962_3_E_2_without_a_succeeded_route_the_answer_is_route_not_succeeded(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog, status: str | None) -> None:
    rid = rgs.seed_gate0(renv, f"nr-{(status or 'none').lower()}")
    if status is not None:
        renv.rdb.exec(
            "INSERT INTO console.research_route_decisions (research_id, track, target_kind, "
            "target_module, target_path, status, decided_by) VALUES (%s, 'A', 'MODULE', "
            "'agentconsole', 'x', %s, 'seed')", rid, status)
    verbs.clear()
    resp = post_gate(renv, rid, "PR_REVIEW", "PASS")
    assert (resp.status_code, resp.json()["reason"]) == (409, "fsm_state_conflict")
    assert resp.json()["details"]["cause"] == "route_not_succeeded"
    assert verbs.writes() == [] and gate_rows(renv, rid) == []


# ── AT-962-3-E-3：組合與欄位邊界（純函式）───────────────────────────────────────────────────────
def rules_of(**over: Any) -> list[tuple[str, str]]:
    body = gate_body(**over)
    return [(v["field"], v["rule"]) for v in inner_gates.validate_request(body)]


def test_AT_962_3_E_3_validate_request_reports_each_field() -> None:
    assert rules_of(gate="RELEASE_READY", result="PASS") == [("result", "release_pass_via_tag")]
    assert rules_of(gate="RELEASE_READY", result="FAIL") == []
    assert rules_of(result="FAIL", reason="") == [("reason", "reason_required")]
    assert rules_of(result="FAIL", reason="x" * 501) == [("reason", "reason_too_long")]
    assert rules_of(result="FAIL", reason="x" * 500) == []
    assert rules_of(result="PASS", reason="") == []
    assert rules_of(review_report_ref="r" * 301) == [("review_report_ref", "report_ref_too_long")]
    assert rules_of(review_report_ref="r" * 300) == []
    assert rules_of(gate="X") == [("gate", "gate_invalid")]
    assert rules_of(result="MAYBE") == [("result", "result_invalid")]
    assert rules_of(gate="X", result="Y", reason="x" * 501) == [
        ("gate", "gate_invalid"), ("result", "result_invalid"), ("reason", "reason_too_long")]
    assert rules_of(reviewer_independent=False) == [
        ("reviewer_independent", "reviewer_independence_required")]


def test_AT_962_3_E_3_the_endpoint_answers_422_invalid_request_with_the_violations(
        renv: rgs.RouteEnv, rtm: RtmFixture) -> None:
    rid = rgs.seed_gate0(renv, "bad-input")
    resp = post_gate(renv, rid, "RELEASE_READY", "PASS")
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    assert resp.json()["violations"][0]["rule"] == "release_pass_via_tag"
    assert post_gate(renv, rid, decision_id="not-a-uuid").status_code == 422


# ── AT-962-3-E-4：approver 不合 ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("approver", ["", "a\nb", "x" * 101, "bridge", None])
def test_AT_962_3_E_4_a_bad_approver_is_422_and_calls_no_fsm_verb(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog, approver: Any) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    verbs.clear()
    resp = post_gate(renv, rid, "PR_REVIEW", "PASS", approver=approver)
    assert (resp.status_code, resp.json()["reason"]) == (422, "invalid_request")
    assert verbs.writes() == [] and gate_rows(renv, rid) == []
    assert post_gate(renv, rid, "PR_REVIEW", "PASS", approver="alice@example.com"
                     ).status_code == 200


# ── AT-962-3-E-5：FSM 在前、DB 在後 ─────────────────────────────────────────────────────────────
def test_AT_962_3_E_5_a_blocked_db_answers_503_and_the_replay_writes_the_row_once(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog,
        monkeypatch: pytest.MonkeyPatch) -> None:
    rid, route = routed(renv)
    inner_to(renv, route, "IMPLEMENTATION")
    verbs.clear()
    real_gate = fsm_ops.gate

    def gate_then_block(*a: Any, **k: Any) -> Any:
        result = real_gate(*a, **k)
        renv.rdb.block()                       # FSM 已前進；之後的 DB 寫入一律失敗
        return result

    monkeypatch.setattr(fsm_ops, "gate", gate_then_block)
    try:
        resp = post_gate(renv, rid, "PR_REVIEW", "PASS")
    finally:
        renv.rdb.unblock()
    assert (resp.status_code, resp.json()["reason"]) == (503, "db_blocked")
    assert verbs.verbs() == ["transition", "gate"], "FSM 只呼叫一次"
    writer = blocking_context(renv).writer
    pending = [op for op in writer.outbox.pending() if op.kind == "gate.decision"]
    assert len(pending) == 1
    assert gate_rows(renv, rid) == []
    report = writer.replay()
    assert not report.rejected
    assert len(gate_rows(renv, rid)) == 1 and verbs.verbs() == ["transition", "gate"]
    writer.replay()
    assert len(gate_rows(renv, rid)) == 1, "重放冪等"
    assert pending[0].payload["decision_id"]


# ── AT-962-3-E-6：漂移先於現態與 RTM 前置 ───────────────────────────────────────────────────────
def frozen_prd(route: dict[str, Any]) -> Path:
    """分流時發佈到目標根的凍結 PRD（內環 Stage-1 採納的那份）。"""
    return next((Path(route["target_path"]) / "docs" / "01_requirements").glob("*_PRD.md"))


@pytest.mark.parametrize("gate", ["PR_REVIEW", "RTM_VERIFY", "RELEASE_READY"])
def test_AT_962_3_E_6_drifted_frozen_files_block_every_gate_with_422_digest_mismatch(
        renv: rgs.RouteEnv, rtm: RtmFixture, verbs: VerbLog, gate: str) -> None:
    rid, route = routed(renv, f"dr-{gate.lower().replace('_', '-')[:5]}")
    inner_to(renv, route, {"PR_REVIEW": "IMPLEMENTATION", "RTM_VERIFY": "RTM_VERIFY",
                           "RELEASE_READY": "RELEASE_READY"}[gate])
    target = frozen_prd(route)
    original = target.read_bytes()
    target.write_bytes(original + b"\n<!-- drift -->\n")
    verbs.clear()
    events = len(renv.rdb.events(rid))
    for mismatch_state in (False, True):          # 第二輪：現態也不合，仍回 422（漂移先中）
        resp = post_gate(renv, rid, gate, "FAIL" if gate == "RELEASE_READY" else "PASS")
        assert (resp.status_code, resp.json()["reason"]) == (422, "digest_mismatch"), mismatch_state
        drift = resp.json()["details"]["drift"]
        assert drift and set(drift[0]) == {"path", "expected_sha256", "actual_sha256"}
        assert drift[0]["path"].startswith("docs/01_requirements/") and drift[0]["path"].endswith(
            "_PRD.md")
        if not mismatch_state:
            other = "RTM_VERIFY" if gate == "PR_REVIEW" else "PR_REVIEW"
            resp2 = post_gate(renv, rid, other, "PASS")
            assert resp2.status_code == 422 and resp2.json()["reason"] == "digest_mismatch"
    assert verbs.writes() == [] and gate_rows(renv, rid) == []
    assert len(renv.rdb.events(rid)) == events
    assert target.read_bytes() == original + b"\n<!-- drift -->\n", "Bridge 不改凍結檔"
