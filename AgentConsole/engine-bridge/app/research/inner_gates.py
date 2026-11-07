"""內環 SCG-4／SCG-5／SCG-6 登錄與 RELEASE 轉態（ResearchToPRD P2；TCS AC-962-3、5；IFACE §2）。

`register` 是 `POST /research/projects/{id}:gates` 的本體，序列（持專案鎖）：冪等查詢→OPEN SCR 守門→
內環鍵現態→現態矩陣（矩陣外＝409，零 FSM 寫入、零 DB 列）→RTM 零信任重驗→FSM 動詞（以引擎回傳的
`next_state` 為準，本模組不自算任何重試預算）→決定列（經既有 `gate.decision` 操作；FSM 在前、
DB 在後，DB 阻塞時決定列留在 outbox、恢復後重放，不重複呼叫 FSM）。

AST 鎖（`tests/test_research_ast_locks.py`）：`fsm_ops.gate(...)` 的 `gate=` 必須是字面常數、各在
一個分支內，不得以變數分派；本模組只呼叫 `fsm_ops.gate` 與 `fsm_ops.transition`（不凍結、不核准、
不建檔）。`release_transition` 是整個研究面唯一發出 `--to RELEASE` 的地方（交付模組零 FSM 寫入）。
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import sdd_cli
from ..errors import ApiError
from ..tracing import trace_id_var
from . import fsm_ops, scr
from .db import ResearchDb, utc_now
from .outbox import DurableWriter, Op

GATES: tuple[str, ...] = ("PR_REVIEW", "RTM_VERIFY", "RELEASE_READY")
RESULTS: tuple[str, ...] = ("PASS", "FAIL")
REASON_MAX = 500
REPORT_REF_MAX = 300
#: 決定列的 gate 欄值（V21 CHECK 含 SCG6）。
GATE_ROW: dict[str, str] = {"PR_REVIEW": "SCG4", "RTM_VERIFY": "SCG5", "RELEASE_READY": "SCG6"}
#: PR_REVIEW 可從這些內環現態登錄（前三者先 `transition --to PR_REVIEW`）。
PR_REVIEW_STATES: tuple[str, ...] = ("IMPLEMENTATION", "EXECUTION_EVALUATION",
                                     "ADVERSARIAL_EVALUATION", "PR_REVIEW")
ALLOWED_STATES: dict[str, tuple[str, ...]] = {
    "PR_REVIEW": PR_REVIEW_STATES, "RTM_VERIFY": ("RTM_VERIFY",),
    "RELEASE_READY": ("RELEASE_READY",)}
RTM_BELOW_100 = "rtm_below_100"


def _v(field: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field, "rule": rule, "message": message}


def validate_request(body: Mapping[str, Any]) -> list[dict[str, str]]:
    """純函式：逐欄違規（`violations[]`）。`(RELEASE_READY, PASS)` 一律不收（PASS 走 `:tag`）。"""
    found: list[dict[str, str]] = []
    gate, result = body.get("gate"), body.get("result")
    if gate not in GATES:
        found.append(_v("gate", "gate_invalid", f"gate 須為 {'｜'.join(GATES)}"))
    if result not in RESULTS:
        found.append(_v("result", "result_invalid", f"result 須為 {'｜'.join(RESULTS)}"))
    elif gate == "RELEASE_READY" and result == "PASS":
        found.append(_v("result", "release_pass_via_tag", "RELEASE_READY 的 PASS 只經 :tag"))
    reason = body.get("reason")
    if reason is not None and not isinstance(reason, str):
        found.append(_v("reason", "reason_invalid", "reason 須為字串"))
    elif result == "FAIL" and not (reason or "").strip():
        found.append(_v("reason", "reason_required", "FAIL 必須附理由"))
    elif isinstance(reason, str) and len(reason) > REASON_MAX:
        found.append(_v("reason", "reason_too_long", f"reason 不得超過 {REASON_MAX} 字"))
    ref = body.get("review_report_ref")
    if ref is not None and (not isinstance(ref, str) or len(ref) > REPORT_REF_MAX):
        found.append(_v("review_report_ref", "report_ref_too_long",
                        f"review_report_ref 須為至多 {REPORT_REF_MAX} 字的字串"))
    if gate == "PR_REVIEW" and body.get("reviewer_independent") is not True:
        found.append(_v("reviewer_independent", "reviewer_independence_required",
                        "PR_REVIEW 須聲明審查者獨立（reviewer_independent 為 true）"))
    return found


@dataclass
class GateEnv:
    """登錄所需的部署事實與注入點。`rtm_report(run_id)` 回報告（找不到丟 `ApiError`）；
    `project_state(rid)` 重衍生 state 投影（可為 None）。"""

    cfg: Any
    db: ResearchDb
    writer: DurableWriter
    audit: Any = None
    rtm_report: Callable[[str], Mapping[str, Any]] | None = None
    project_state: Callable[[str], None] | None = None


def inner_route(db: ResearchDb, rid: str) -> dict[str, Any]:
    """內環鍵所在的 SUCCEEDED 分流列；沒有＝409 `fsm_state_conflict`（`route_not_succeeded`）。"""
    route = db.active_route(rid)
    if (route is None or route["status"] != "SUCCEEDED" or not route.get("impl_fsm_project")
            or not route.get("impl_state_dir")):
        raise ApiError(409, "fsm_state_conflict", details={"cause": "route_not_succeeded"})
    return route


def inner_fsm(env: GateEnv, route: Mapping[str, Any], actor: str | None) -> fsm_ops.FsmCtx:
    return fsm_ops.FsmCtx(sdd_root=env.cfg.sdd_root, state_dir=Path(route["impl_state_dir"]),
                          key=str(route["impl_fsm_project"]), audit=env.audit, actor=actor)


def rtm_unmet(env: GateEnv, gate: str, run_id: str | None) -> list[str]:
    """零信任重驗：PR_REVIEW 要 `fully_covered`、RTM_VERIFY 要 `ac.pct == 100`（99.99 不得通過）；
    報告讀不到＝不足。其餘 gate 不看 RTM。"""
    if gate not in ("PR_REVIEW", "RTM_VERIFY"):
        return []
    if env.rtm_report is None or not run_id:
        return [RTM_BELOW_100]
    try:
        report = env.rtm_report(run_id)
    except ApiError:
        return [RTM_BELOW_100]
    if gate == "PR_REVIEW":
        ok = report.get("fully_covered") is True
    else:
        pct = (report.get("ac") or {}).get("pct")
        ok = isinstance(pct, int | float) and not isinstance(pct, bool) and pct == 100
    return [] if ok else [RTM_BELOW_100]


def _replay_response(found: Mapping[str, Any]) -> dict[str, Any]:
    nxt = found.get("fsm_state_after")
    return {"gate_decision_id": str(found["id"]), "gate": _gate_of_row(str(found["gate"])),
            "result": "PASS" if found["decision"] == "APPROVED" else "FAIL",
            "fsm_state_before": None, "next_state": nxt,
            "escalated": isinstance(nxt, str) and nxt.startswith("ESCALATION"), "replayed": True}


def _gate_of_row(row_gate: str) -> str:
    return next((g for g, r in GATE_ROW.items() if r == row_gate), row_gate)


def register(env: GateEnv, row: Mapping[str, Any], body: Mapping[str, Any]) -> dict[str, Any]:
    """登錄一次內環閘決定；回應鍵 `gate_decision_id、gate、result、fsm_state_before、next_state、
    escalated`（`flow` 由路由層補）。"""
    rid = str(row["id"])
    approver = sdd_cli.validate_research_approver(body.get("approver"))
    gate, result = str(body["gate"]), str(body["result"])
    reason = str(body.get("reason") or "")
    decision_id = str(body["decision_id"])
    with env.writer.project_lock(rid):
        found = env.db.get_gate_decision(decision_id)
        if found is not None and str(found["research_id"]) == rid:
            return _replay_response(found)
        scr.guard_inner_start(env.db, rid)
        route = inner_route(env.db, rid)
        fctx = inner_fsm(env, route, approver)
        before = str(fsm_ops.read_current(fctx).get("current_state"))
        if before not in ALLOWED_STATES[gate]:
            raise fsm_ops.conflict("fsm_state_conflict", current_state=before, gate=gate)
        if result == "PASS":
            unmet = rtm_unmet(env, gate, body.get("run_id"))
            if unmet:
                raise fsm_ops.conflict("fsm_state_conflict", current_state=before, unmet=unmet)
        fsm_reason = reason.strip() or f"{GATE_ROW[gate]} registration {result}"
        if gate == "PR_REVIEW":
            if before != "PR_REVIEW":
                fsm_ops.transition(fctx, to="PR_REVIEW",
                                   reason=f"SCG-4 registration; research={row['rp_no']}")
            outcome = fsm_ops.gate(fctx, gate="PR_REVIEW", result=result, reason=fsm_reason)
        elif gate == "RTM_VERIFY":
            outcome = fsm_ops.gate(fctx, gate="RTM_VERIFY", result=result, reason=fsm_reason)
        else:
            outcome = fsm_ops.gate(fctx, gate="RELEASE_READY", result=result, reason=fsm_reason)
        next_state = str(outcome["next_state"])
        escalated = next_state.startswith("ESCALATION")
        details: dict[str, Any] = {
            "reviewer_independent": bool(body.get("reviewer_independent")),
            "review_report_ref": body.get("review_report_ref")}
        if gate == "RELEASE_READY":
            details["ci_red"] = True
        status = "ESCALATED" if escalated else (
            "IDLE" if row["flow_status"] == "ESCALATED" else row["flow_status"])
        env.writer.persist(Op("gate.decision", rid, dict(
            research_id=rid, decision_id=decision_id, gate=GATE_ROW[gate],
            decision="APPROVED" if result == "PASS" else "REJECTED", decided_by=approver,
            decided_at=utc_now().isoformat(), prd_version_no=None, review_round_no=None,
            fsm_project=str(route["impl_fsm_project"]), fsm_stage=None,
            fsm_state_after=next_state, frozen_digests={}, reason=reason,
            audit_trace_id=trace_id_var.get(), details=details,
            flow={"step": row["flow_step"], "phase": row["flow_phase"], "status": status,
                  "detail": ""})))
        if escalated:
            env.writer.persist(Op("event.append", rid, {
                "research_id": rid, "event_type": "research.alert", "actor": approver,
                "payload": {"kind": "ESCALATED", "detail": f"{gate} {result} → {next_state}"},
                "ref_kind": "gate_decision", "ref_id": decision_id}))
        if env.project_state is not None:
            env.project_state(rid)
    return {"gate_decision_id": decision_id, "gate": gate, "result": result,
            "fsm_state_before": before, "next_state": next_state, "escalated": escalated}


def release_transition(env: GateEnv, row: Mapping[str, Any], tag_name: str,
                       approver: str) -> str:
    """`transition --to RELEASE`（整個研究面唯一處）；FSM 已是 RELEASE 時略過（零寫入）。回現態。"""
    route = inner_route(env.db, str(row["id"]))
    fctx = inner_fsm(env, route, approver)
    with env.writer.project_lock(str(row["id"])):
        current = fsm_ops.current_state(fctx)
        if current == "RELEASE":
            return current
        return fsm_ops.transition(fctx, to="RELEASE",
                                  reason=f"release tag {tag_name}; research={row['rp_no']}")
