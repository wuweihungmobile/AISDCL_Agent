"""SCR（Spec Change Request）：輸入閘、三路（MINOR／MAJOR／HEALING_FAILED）與 MINOR 的內環收尾
（ADR-XPLAT-017 D5 與附錄 A；PRD FR-R2P-19；D-103／D-104／D-118；TCS AC-961-12、13）。

三路（`open_*`）：
  · MINOR：驗輸入→OPEN 檢查→現態矩陣預檢（不合 409，零列零 FSM 寫入）→`scr_limit`→寫 `research_scr`
    （OPEN）與游標 `studio／SCR_OPEN`→外環鍵 `transition --to SPEC_DRAFTING`；
  · MAJOR：新研究專案（由呼叫端提供建立函式）＋一列直接 `SUPERSEDED` 的 SCR；舊專案游標只改說明；
  · HEALING_FAILED：只寫一列 OPEN 並回 `resume-from-escalation` 指令組，**零 FSM 寫入動詞**
    （AST 鎖 AC-19-7：本模組內的 `open_healing_failed` 不得呼叫任何 `fsm_ops` 寫入函式）。
`apply_minor`：Gate-0-SCR 核准後的內環序列（現態矩陣見 `matrix_pre`）；每步一筆 `impl_fsm_actions`
`{verb, label, args_redacted, result, rc, at}`；任一步失敗即停、不重試：步驟執行出錯＝`FAILED`
（可由 `:scr-apply` 續做），gate 回傳不是 IMPLEMENTATION＝`BLOCKED`（只有人能解）。**本模組不呼叫
`fsm_ops.approve_baseline`**（Gate 0 的凍結只在 `:approve-baseline`；AST 鎖）。
"""
from __future__ import annotations

import os
import re
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .. import fsutil, sdd_cli
from ..errors import ApiError
from ..sdd_state import ESCALATION_STATES, recovery_commands
from . import fsm_ops, gitops, layout
from . import route as route_mod
from .db import SCR_MINOR_MAX, ResearchDb, utc_now
from .outbox import DurableWriter, Op

REASON_MAX = 500
KINDS: tuple[str, ...] = ("MINOR", "MAJOR")
SOURCE_KINDS: tuple[str, ...] = ("HUMAN", "REVIEW_FINDING", "SCG4", "HEALING_FAILED")
#: 理由分類：中文（契約 API-RP-15）→ DB 碼（V19 CHECK）；DB 碼本身也接受。
REASON_CLASSES: Mapping[str, str] = {
    "PRD 缺漏證據": "EVIDENCE", "AC 模糊": "AC_VAGUE", "需求變更": "REQ_CHANGE",
    "技術不可行": "INFEASIBLE", "其他": "OTHER"}
REASON_CLASS_CODES = frozenset(REASON_CLASSES.values())
SCR_STAGE_PREFIX = "Gate-0-SCR"
#: 內環現態矩陣（IFACE §5.3）：直接 `transition --to SPEC_AUDIT` 起跑的現態、現態本身就是
#: SPEC_AUDIT（略過第一步）、必須先 `gate <現態> FAIL` 退回 IMPLEMENTATION 的現態。
MATRIX_DIRECT: tuple[str, ...] = ("IMPLEMENTATION", "EXECUTION_EVALUATION",
                                  "ADVERSARIAL_EVALUATION", "PR_REVIEW")
MATRIX_AUDIT = "SPEC_AUDIT"
MATRIX_GATE_FIRST: tuple[str, ...] = ("RTM_VERIFY", "RELEASE_READY")
MATRIX_STATES: tuple[str, ...] = (*MATRIX_DIRECT, MATRIX_AUDIT, *MATRIX_GATE_FIRST)
#: 重凍動詞名取 `sdd_cli` 的常數（本檔不內嵌 FSM 寫入動詞的字面；AST 鎖 AT-961-8-6）。
REFREEZE = sdd_cli.RESEARCH_VERB_SPEC_REFREEZE
PR_REVIEW_FAIL_REASON = "SCR-{k}: spec changed; re-implement"
_AC_RE = re.compile(r"(?<![\w-])(AC-[0-9][0-9A-Za-z-]*)(?![\w-])")
_FR_RE = re.compile(r"(?<![\w-])(FR-[A-Z0-9][0-9A-Za-z-]*)(?![\w-])")
EVIDENCE_URL_MAX = 500
_HEADING_NO_RE = re.compile(r"^#{1,6}\s+(\d+(?:\.\d+)*)[.\s、]")
_SECTION_REF_RE = re.compile(r"^§?\s*(\d+(?:\.\d+)*)$")
#: 發佈檔的鏡像時鐘（測試縫：固定時間戳）；預設取 UTC 現在。
NOW: Callable[[], Any] = utc_now


# ══ 輸入閘 ═══════════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class FrozenPrd:
    """凍結 PRD 的章節編號與 AC 編號集合（`affected_sections` 的查核對象）。"""

    sections: frozenset[str]
    acs: frozenset[str]
    #: 文內所有 `FR-…` 編號（與 AC 同一條解析路徑；追溯表 `frTotal` 與 PR 標題的 FR 數同源）。
    frs: frozenset[str] = frozenset()


def parse_frozen_prd(text: str) -> FrozenPrd:
    """章節＝`## 5`、`### 5.2 …` 這類標題的編號（連同其上層，例如 `5.2` 蘊含 `5`）；AC＝文內所有
    `AC-…` 編號（與 QA 維度 `ac_total` 同一個詞彙）。"""
    sections: set[str] = set()
    for line in text.splitlines():
        match = _HEADING_NO_RE.match(line)
        if match:
            parts = match.group(1).split(".")
            sections.update(".".join(parts[:i]) for i in range(1, len(parts) + 1))
    return FrozenPrd(frozenset(sections), frozenset(_AC_RE.findall(text)),
                     frozenset(_FR_RE.findall(text)))


def _v(field_name: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field_name, "rule": rule, "message": message}


def normalize_reason_class(value: object) -> str | None:
    """中文分類或 DB 碼 → DB 碼；不合法＝None。"""
    if isinstance(value, str):
        if value in REASON_CLASS_CODES:
            return value
        return REASON_CLASSES.get(value)
    return None


def validate_request(body: Mapping[str, Any], frozen: FrozenPrd) -> list[dict[str, str]]:
    """AC-19-5：逐項違規（`violations[]`；零寫入零 FSM）。`reason` 非空且 ≤500 字、分類在五值、
    受影響章節與 AC 存在於凍結 PRD；`kind`／`source_kind` 值域亦在此驗（Bridge 回 422）。"""
    found: list[dict[str, str]] = []
    if body.get("kind") not in KINDS:
        found.append(_v("kind", "kind_invalid", f"kind 須為 {'｜'.join(KINDS)}"))
    if body.get("source_kind") not in SOURCE_KINDS:
        found.append(_v("source_kind", "source_kind_invalid",
                        f"source_kind 須為 {'｜'.join(SOURCE_KINDS)}"))
    reason = body.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        found.append(_v("reason", "reason_empty", "reason 不可為空"))
    elif len(reason) > REASON_MAX:
        found.append(_v("reason", "reason_too_long", f"reason 不得超過 {REASON_MAX} 字"))
    if normalize_reason_class(body.get("reason_class", "OTHER")) is None:
        found.append(_v("reason_class", "reason_class_invalid",
                        "reason_class 須為 EVIDENCE｜AC_VAGUE｜REQ_CHANGE｜INFEASIBLE｜OTHER"
                        "（或其中文名）"))
    url = body.get("evidence_url")
    if url is not None:                       # 選填；https 限定、至多 500 字元（V21 CHECK 同義）
        if not isinstance(url, str) or not url.startswith("https://"):
            found.append(_v("evidence_url", "evidence_not_https",
                            "evidence_url 須以 https:// 起頭"))
        if isinstance(url, str) and len(url) > EVIDENCE_URL_MAX:
            found.append(_v("evidence_url", "evidence_too_long",
                            f"evidence_url 不得超過 {EVIDENCE_URL_MAX} 字元"))
    sections = body.get("affected_sections", [])
    if not isinstance(sections, list) or not all(isinstance(s, str) for s in sections):
        found.append(_v("affected_sections", "affected_invalid", "須為字串清單"))
        return found
    for index, ref in enumerate(sections):
        if not _known_ref(ref, frozen):
            found.append(_v(f"affected_sections[{index}]", "affected_unknown",
                            f"凍結 PRD 沒有 {ref!r}"))
    return found


def _known_ref(ref: str, frozen: FrozenPrd) -> bool:
    """`5.2`、`§5.2`、`AC-003-2`、`§5.2/AC-003-2`（兩段都須存在）。"""
    parts = [p.strip() for p in ref.split("/") if p.strip()]
    if not parts:
        return False
    for part in parts:
        match = _SECTION_REF_RE.match(part)
        if match:
            if match.group(1) not in frozen.sections:
                return False
        elif part not in frozen.acs:
            return False
    return True


# ══ 執行脈絡 ═════════════════════════════════════════════════════════════════════════════════
@dataclass
class ScrEnv:
    """SCR 操作需要的部署事實與寫入器。`git` 為 None＝用預設（唯一 git 出口 `gitops`）。"""

    cfg: Any
    db: ResearchDb
    writer: DurableWriter
    audit: Any = None
    git: gitops.Gitops | None = None

    def gitops(self) -> gitops.Gitops:
        return self.git or gitops.Gitops(scaffold_root=self.cfg.research_scaffold_root,
                                         worktree_root=self.cfg.worktree_root)


def _conflict(cause: str, **details: Any) -> ApiError:
    return fsm_ops.conflict("fsm_state_conflict", cause=cause, **details)


def inner_ctx(env: ScrEnv, route: Mapping[str, Any], actor: str | None) -> fsm_ops.FsmCtx:
    return fsm_ops.FsmCtx(sdd_root=env.cfg.sdd_root, state_dir=Path(route["impl_state_dir"]),
                          key=str(route["impl_fsm_project"]), audit=env.audit, actor=actor)


def succeeded_route(env: ScrEnv, rid: str) -> dict[str, Any]:
    route = env.db.active_route(rid)
    if (route is None or route["status"] != "SUCCEEDED" or not route.get("impl_fsm_project")
            or not route.get("impl_state_dir")):
        raise _conflict("no_route")
    return route


def matrix_pre(state: str) -> str | None:
    """內環現態 → 起跑前置：`transition(SPEC_AUDIT)`、`gate(<現態>,FAIL)`、`""`（略過）；不在矩陣＝
    None。直接起跑的現態另以鏡像邊表核對（沒有第二套狀態機）。"""
    if state in MATRIX_DIRECT and fsm_ops.edge_allowed(state, "SPEC_AUDIT"):
        return "transition(SPEC_AUDIT)"
    if state == MATRIX_AUDIT:
        return ""
    if state in MATRIX_GATE_FIRST:
        return f"gate({state},FAIL)"
    return None


def check_approver(raw: object) -> str:
    """核准人驗證（研究面入口的唯一家在 `sdd_cli`；路由層經這支助手取用，不直接引用）。"""
    return sdd_cli.validate_research_approver(raw)


def guard_inner_start(db: ResearchDb, research_id: str, intent: str = "start") -> None:
    """內環啟動守門（AC-19-3；console-api 啟動入口的 409 另由其前置守衛驗）：有 OPEN 的 SCR 時，
    「恢復舊 run」與「啟動新 run」一律 409 `scr_open`；純讀、零 FSM 寫入。"""
    if intent not in ("start", "resume"):
        raise ValueError("intent 須為 start 或 resume")
    opened = db.open_scr(research_id)
    if opened is not None:
        raise ApiError(409, "scr_open", details={"scr_no": opened["scr_no"], "intent": intent})


# ══ 三路 ═════════════════════════════════════════════════════════════════════════════════════
def check_open_preconditions(env: ScrEnv, row: Mapping[str, Any], kind: str, source_kind: str
                             ) -> dict[str, Any] | None:
    """OPEN 檢查→現態矩陣預檢→`scr_limit`；全部唯讀，任何一關不過都零列零 FSM 寫入。回內環分流列
    （MAJOR 不需要，回 None）。"""
    rid = str(row["id"])
    guard_inner_start(env.db, rid)
    route: dict[str, Any] | None = None
    if kind == "MINOR":
        route = succeeded_route(env, rid)
        ifctx = inner_ctx(env, route, None)
        state = fsm_ops.read_current(ifctx)
        current = state.get("current_state")
        if source_kind == "HEALING_FAILED":
            if current not in ESCALATION_STATES:
                raise _conflict("not_escalated", current_state=current)
        else:
            outer = fsm_ops.read_current(_outer(env, row))
            if fsm_ops.is_escalated(outer):
                raise fsm_ops.escalated_error(_outer(env, row), outer)
            if outer.get("current_state") != "SPEC_FROZEN":
                raise _conflict("outer_not_frozen", current_state=outer.get("current_state"),
                                expected_state="SPEC_FROZEN")
            if not isinstance(current, str) or matrix_pre(current) is None:
                raise _conflict("inner_state_not_in_matrix", current_state=current)
        used = env.db.query(
            "SELECT count(*) AS n FROM {s}.research_scr WHERE research_id = %s AND kind = 'MINOR' "
            "AND status IN ('OPEN', 'APPROVED', 'APPLIED')", (rid,))[0]["n"]
        if int(used) >= SCR_MINOR_MAX:
            raise ApiError(409, "scr_limit", details={
                "limit": SCR_MINOR_MAX, "used": int(used), "hint": "改 MAJOR"})
    return route


def _outer(env: ScrEnv, row: Mapping[str, Any], actor: str | None = None) -> fsm_ops.FsmCtx:
    return fsm_ops.FsmCtx(sdd_root=env.cfg.sdd_root, state_dir=Path(row["fsm_state_dir"]),
                          key=str(row["fsm_project"]), audit=env.audit, actor=actor)


def _open_payload(rid: str, body: Mapping[str, Any], requested_by: str) -> dict[str, Any]:
    return {"research_id": rid, "scr_id": str(uuid.uuid4()), "kind": body["kind"],
            "source_kind": body["source_kind"], "reason": body["reason"],
            "reason_class": normalize_reason_class(body.get("reason_class", "OTHER")),
            "affected_sections": list(body.get("affected_sections") or []),
            "evidence_url": body.get("evidence_url"),
            "requested_by": requested_by, "requested_at": NOW().isoformat()}


def open_minor(env: ScrEnv, row: Mapping[str, Any], body: Mapping[str, Any], requested_by: str
               ) -> dict[str, Any]:
    """MINOR（非 HEALING_FAILED）：寫列與游標，再把外環鍵退回 SPEC_DRAFTING。轉態失敗＝SCR 標
    REJECTED（不留一筆永遠 OPEN、外環卻沒動的列）並把錯誤原樣拋出。"""
    rid = str(row["id"])
    payload = {**_open_payload(rid, body, requested_by),
               "flow": {"step": "studio", "phase": "SCR_OPEN", "status": "IDLE", "detail": ""}}
    result = env.writer.persist(Op("scr.open", rid, payload))
    scr_no = int(result["scr_no"])
    reason = f"進入 Stage {SCR_STAGE_PREFIX}{scr_no}: {str(body['reason'])[:120]}"
    try:
        fsm_ops.transition(_outer(env, row, requested_by), to="SPEC_DRAFTING", reason=reason)
    except ApiError:
        env.writer.persist(Op("scr.update", rid, {
            "research_id": rid, "scr_id": payload["scr_id"], "status": "REJECTED",
            "decided_by": "bridge", "decided_at": NOW().isoformat(), "actor": "bridge",
            "flow": {"step": row["flow_step"], "phase": row["flow_phase"],
                     "status": row["flow_status"], "detail": row["flow_detail"]}}))
        raise
    return {"scr_no": scr_no, "status": "OPEN"}


def open_healing_failed(env: ScrEnv, row: Mapping[str, Any], body: Mapping[str, Any],
                        route: Mapping[str, Any], requested_by: str) -> dict[str, Any]:
    """HEALING_FAILED：只寫一列 OPEN 並回恢復指令組；**不呼叫任何 FSM 寫入動詞**（只有人能
    `resume-from-escalation`；它不在 `RESEARCH_VERBS`）。"""
    rid = str(row["id"])
    payload = _open_payload(rid, body, requested_by)
    result = env.writer.persist(Op("scr.open", rid, payload))
    ifctx = inner_ctx(env, route, None)
    state = fsm_ops.read_current(ifctx)
    root = env.cfg.sdd_root if env.cfg.sdd_root is not None else Path()
    recovery = recovery_commands(dict(state), sdd_root=root, fsm_dir=ifctx.state_dir,
                                 key=ifctx.key)
    return {"scr_no": int(result["scr_no"]), "status": "OPEN", "recovery": recovery}


def open_major(env: ScrEnv, row: Mapping[str, Any], body: Mapping[str, Any], requested_by: str,
               create_successor: Callable[[Mapping[str, Any], int], Mapping[str, Any]]
               ) -> dict[str, Any]:
    """MAJOR：先建新研究專案（`create_successor(舊列, scr_no)`→`{research_id, rp_no}`），再寫一列
    直接 `SUPERSEDED` 的 SCR（`successor_research_id`）與舊專案游標說明「已被 RP-NNNN 取代」。
    舊專案的內外環 FSM 鍵一律不動（不呼叫任何動詞、不 TERMINATED）。"""
    rid = str(row["id"])
    next_no = 1 + max([int(r["scr_no"]) for r in env.db.list_scr(rid)] or [0])
    created = create_successor(row, next_no)
    payload = {**_open_payload(rid, body, requested_by),
               "successor_research_id": str(created["research_id"]),
               "detail": f"已被 {created['rp_no']} 取代"}
    result = env.writer.persist(Op("scr.major", rid, payload))
    return {"scr_no": int(result["scr_no"]), "status": "SUPERSEDED",
            "successor_research_id": str(created["research_id"])}


# ══ MINOR 的套用 ═════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Baseline:
    """Gate-0-SCR 核准後的新基線（發佈與重凍的輸入）。"""

    rel: str                    # 工作區內的新基線檔（`01_specs/PRD-v1.<n>.0.md`）
    sha256: str
    text: str
    from_version_no: int | None
    to_version_no: int
    semver: str
    gate_decision_id: str
    scope_changed: bool = False


@dataclass
class ApplyResult:
    status: str                         # APPLIED｜FAILED｜BLOCKED
    detail: str = ""
    actions: list[dict[str, Any]] = field(default_factory=list)
    flow: dict[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "detail": self.detail}


def publish_rel(row: Mapping[str, Any], route: Mapping[str, Any]) -> str:
    """目標根內的發佈路徑＝分流時發佈（與採納）的那個 PRD 路徑（軌道 A：`docs/01_requirements/
    <slug>_PRD.md`；軌道 B：工作區副本內的基線檔）——重凍的 `--doc` 就是它。"""
    if route["track"] == "A":
        return f"docs/01_requirements/{row['slug']}_PRD.md"
    from . import scaffold

    return f"{scaffold.WORKSPACE_COPY_ROOT}/{row['slug']}/{route_mod.BASELINE_REL}"


def module_of_text(text: str) -> str | None:
    """PRD 文字內「模組落點表」的預設落點目標（同 `route.default_target_module`，吃文字）。"""
    table: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            inside = "模組落點表" in line
            continue
        if inside or "模組落點表" in line:
            table.append(line)
    joined = "\n".join(table)
    hits = [(joined.find(word), module) for word, module in route_mod._PLACEMENT_KEYWORDS
            if word in joined]
    return min(hits)[1] if hits else None


def _entry(label: str, verb: str, args: str, ok: bool, result: str) -> dict[str, Any]:
    return {"verb": verb, "label": label, "args_redacted": args, "result": result,
            "rc": 0 if ok else 1, "at": NOW().isoformat()}


def publish_text(env: ScrEnv, row: Mapping[str, Any], route: Mapping[str, Any], rel: str,
                 text: str, sha256: str, *, kind: str | None = None) -> str:
    """把 `text` 原子寫到目標根的 `rel`＋sha256 驗證；軌道 A 另以明列路徑 `add`＋`commit`（`gitops`
    唯一出口；訊息模板取自 `gitops.commit_message`）。SCR 的 PRD 重發佈與 TCS 發佈共用。"""
    exec_path = Path(route["target_path"])
    target = exec_path / rel
    fsutil.write_text_atomic(target, text)
    if layout.sha256_bytes(target.read_bytes()) != sha256:
        raise ValueError("發佈後的位元組與預期摘要不符")
    if route["track"] != "A":
        return f"publish {rel}"
    git = env.gitops()
    top = git.git(["rev-parse", "--show-toplevel"], cwd=exec_path)
    if top.returncode != 0:
        raise ValueError(f"git rev-parse --show-toplevel rc={top.returncode}")
    worktree = Path(top.stdout.strip()).resolve()
    rel_in_tree = Path(os.path.relpath(target.resolve(), worktree)).as_posix()
    added = git.git(["add", "--", rel_in_tree], cwd=worktree)
    if added.returncode != 0:
        raise ValueError(f"git add rc={added.returncode}")
    if git.git(["status", "--porcelain"], cwd=worktree).stdout.strip():
        message = gitops.commit_message(kind or SCR_COMMIT_KIND, str(row["rp_no"]), sha256[:12])
        done = git.git(["commit", "-m", message], cwd=worktree)
        if done.returncode != 0:
            raise ValueError(f"git commit rc={done.returncode}")
    return f"publish {rel}"


def _publish(env: ScrEnv, row: Mapping[str, Any], route: Mapping[str, Any], base: Baseline
             ) -> str:
    return publish_text(env, row, route, publish_rel(row, route), base.text, base.sha256)

#: SCR 發佈的 commit 訊息模板種類（`gitops.commit_message`；D-134 第 7 條）。
SCR_COMMIT_KIND = "scr"


def _persist_actions(env: ScrEnv, rid: str, scr: Mapping[str, Any],
                     actions: Sequence[Mapping[str, Any]], **extra: Any) -> None:
    env.writer.persist(Op("scr.update", rid, {
        "research_id": rid, "scr_id": str(scr["id"]),
        "impl_fsm_actions": [dict(a) for a in actions], "actor": "bridge", **extra}))


def _blocked_flow(next_state: str) -> dict[str, str]:
    escalated = ESCALATION_STATES | {"AUTO_RECOVERY_ATTEMPT"}
    status = "ESCALATED" if next_state in escalated else "FAILED"
    return {"step": "studio", "phase": "SCR_OPEN", "status": status,
            "detail": f"scr_blocked:{next_state}"[:300]}


def apply_minor(env: ScrEnv, row: Mapping[str, Any], scr: Mapping[str, Any], *, approver: str,
                base: Baseline) -> ApplyResult:
    """內環收尾序列（ADR-017 附錄 A）。`scr.impl_fsm_actions` 已有成功步驟者不重做（重試冪等）；
    現態不在矩陣（且尚未做任何步驟）＝409 `fsm_state_conflict`、零 FSM 寫入、零發佈。"""
    rid = str(row["id"])
    route = succeeded_route(env, rid)
    fctx = inner_ctx(env, route, approver)
    actions: list[dict[str, Any]] = [dict(a) for a in (scr.get("impl_fsm_actions") or [])]
    done = {a["label"] for a in actions if a.get("rc") == 0 and not a.get("blocked")}
    k = int(scr["scr_no"])
    steps: list[tuple[str, str, str, Callable[[], str]]] = []
    state = fsm_ops.current_state(fctx)
    if not done and matrix_pre(state) is None:
        raise _conflict("inner_state_not_in_matrix", current_state=state)
    audit_label = "transition(SPEC_AUDIT)"

    def audit() -> str:
        return fsm_ops.transition(
            fctx, to="SPEC_AUDIT", reason=f"SCR-{k}: PRD changed; audit before re-implement")

    if state in MATRIX_GATE_FIRST and not done:
        gate_name = state
        steps.append((f"gate({gate_name},FAIL)", "gate", f"--gate {gate_name} --result FAIL",
                      lambda: str(fsm_ops.gate(
                          fctx, gate=gate_name, result="FAIL",
                          reason=f"SCR-{k}: spec changed; return to IMPLEMENTATION"
                          )["next_state"])))
    # 框架的重凍只准在 SPEC_AUDIT／RELEASE_READY／RELEASE 現態：gate 退回 IMPLEMENTATION 之後與直接
    # 起跑的現態一樣，都要先 `transition SPEC_AUDIT`（IFACE §5.3 共同序列漏列；見交卷勘誤）
    if (state != MATRIX_AUDIT and REFREEZE not in done and audit_label not in done
            and (state in MATRIX_DIRECT or state in MATRIX_GATE_FIRST)):
        steps.append((audit_label, "transition", "--to SPEC_AUDIT", audit))
    old_version = base.from_version_no if base.from_version_no is not None else "?"
    refreeze_reason = (f"SCR-{k}: PRD {old_version}→{base.to_version_no}; "
                       f"gate_decision {base.gate_decision_id}")[:500]
    rel = publish_rel(row, route)
    steps += [
        ("publish", "publish", f"--doc {rel}", lambda: _publish(env, row, route, base)),
        (REFREEZE, REFREEZE, f"--doc {rel}", lambda: str(fsm_ops.spec_refreeze(
            fctx, docs=[rel], root=str(Path(route["target_path"])), reason=refreeze_reason,
            approver=approver))),
        ("transition(PR_REVIEW)", "transition", "--to PR_REVIEW", lambda: fsm_ops.transition(
            fctx, to="PR_REVIEW", reason=f"SCR-{k}: re-implement after spec change")),
        ("gate(PR_REVIEW,FAIL)", "gate", "--gate PR_REVIEW --result FAIL", lambda: str(
            fsm_ops.gate(fctx, gate="PR_REVIEW", result="FAIL",
                         reason=PR_REVIEW_FAIL_REASON.format(k=k))["next_state"])),
    ]
    for label, verb, args, run in steps:
        if label in done:
            continue
        try:
            result = run()
        except (ApiError, OSError, ValueError) as exc:
            reason = exc.body.get("reason") if isinstance(exc, ApiError) else type(exc).__name__
            actions.append(_entry(label, verb, args, False, f"failed:{reason}"))
            _persist_actions(env, rid, scr, actions)
            return ApplyResult("FAILED", f"{label}: {reason}", actions, {
                "step": "studio", "phase": "SCR_OPEN", "status": "FAILED",
                "detail": f"scr_apply_failed:{label}"[:300]})
        entry = _entry(label, verb, args, True, f"ok:{result}")
        actions.append(entry)
        if verb == "gate" and result != "IMPLEMENTATION":
            entry["blocked"] = True
            _persist_actions(env, rid, scr, actions)
            return ApplyResult("BLOCKED", f"{label}: next_state={result}", actions,
                               _blocked_flow(result))
        _persist_actions(env, rid, scr, actions)
    flow = ({"step": "route", "phase": "FROZEN", "status": "IDLE", "detail": ""}
            if base.scope_changed else
            {"step": "build", "phase": "ROUTED", "status": "IDLE", "detail": ""})
    env.writer.persist(Op("scr.update", rid, {
        "research_id": rid, "scr_id": str(scr["id"]), "status": "APPLIED",
        "decided_by": approver, "decided_at": NOW().isoformat(), "actor": approver,
        "flow": flow, "stale_prd_sha256": base.sha256}))
    return ApplyResult("APPLIED", "", actions, flow)


def record_failure_cursor(env: ScrEnv, rid: str, result: ApplyResult, actor: str) -> None:
    """套用失敗或被擋時游標寫明原因（SCR 本身停在 APPROVED；D-118）。"""
    if result.flow is not None and result.status != "APPLIED":
        env.writer.persist(Op("project.cursor", rid, {
            "research_id": rid, "actor": actor, "flow": result.flow}))


def baseline_from_db(env: ScrEnv, row: Mapping[str, Any], scr: Mapping[str, Any]) -> Baseline:
    """`:scr-apply` 重試時從 DB 與工作區重建核准當下的新基線（版本列、檔案、決定 id）。"""
    rid = str(row["id"])
    to_no = scr.get("prd_to_version_no")
    if to_no is None:
        raise _conflict("scr_not_approved", scr_status=scr["status"])
    version = env.db.query(
        "SELECT rel_path, sha256 FROM {s}.research_prd_versions WHERE research_id = %s AND "
        "version_no = %s", (rid, int(to_no)))
    decision = env.db.gate0_decision_id(rid)
    if not version or decision is None:
        raise _conflict("baseline_missing")
    rel = str(version[0]["rel_path"])
    text = layout.safe_join(Path(row["workspace_path"]), rel).read_text(encoding="utf-8")
    old = route_mod.BASELINE_REL
    old_path = layout.safe_join(Path(row["workspace_path"]), old)
    changed = (module_of_text(old_path.read_text(encoding="utf-8")) != module_of_text(text)
               if old_path.is_file() else False)
    return Baseline(rel=rel, sha256=str(version[0]["sha256"]), text=text,
                    from_version_no=scr.get("prd_from_version_no"), to_version_no=int(to_no),
                    semver=rel.removeprefix("01_specs/PRD-").removesuffix(".md"),
                    gate_decision_id=decision, scope_changed=changed)


def check_applicable(scr: Mapping[str, Any]) -> None:
    """`:scr-apply` 的前置：SCR 須為 `APPROVED`、且是 MINOR（其餘 409 `fsm_state_conflict`）。"""
    if scr["status"] != "APPROVED" or scr["kind"] != "MINOR":
        raise _conflict("scr_not_approved", scr_status=scr["status"], kind=scr["kind"])


def scr_awaiting_approval(db: ResearchDb, research_id: str) -> dict[str, Any] | None:
    """`:approve-baseline` 偵測到的 SCR：OPEN、MINOR、非 HEALING_FAILED（那一路不走外環重凍）。"""
    found = db.open_scr(research_id)
    healing = found is not None and found["source_kind"] == "HEALING_FAILED"
    if found is not None and found["kind"] == "MINOR" and not healing:
        return found
    return None


def apply_and_record(env: ScrEnv, row: Mapping[str, Any], scr: Mapping[str, Any], *,
                     approver: str, base: Baseline) -> ApplyResult:
    """`apply_minor`＋失敗游標。呼叫端：`approve_and_apply`（核准即套用）與 `:scr-apply`（重試）。
    套用前的 409（現態不在矩陣、沒有分流）轉成 `FAILED`——外環已凍結、SCR 停在 APPROVED，不可讓核准
    回應變成 409（那會謊稱核准沒發生）。"""
    rid = str(row["id"])
    try:
        result = apply_minor(env, row, scr, approver=approver, base=base)
    except ApiError as exc:
        details = exc.body.get("details") or {}
        cause = details.get("cause") or exc.body.get("reason")
        result = ApplyResult("FAILED", f"{cause}", [], {
            "step": "studio", "phase": "SCR_OPEN", "status": "FAILED",
            "detail": f"scr_apply_failed:{cause}"[:300]})
    record_failure_cursor(env, rid, result, approver)
    return result


def approve_and_apply(env: ScrEnv, row: Mapping[str, Any], scr: Mapping[str, Any], *,
                      approver: str, text: str, sha256: str, to_version_no: int, semver: str,
                      rel: str, decision_id: str) -> dict[str, Any]:
    """Gate-0-SCR 凍結成功之後（同一個請求內）：SCR→`APPROVED`，再跑內環序列（D-103）。回
    `{status, detail}`（`APPLIED｜FAILED｜BLOCKED`）。失敗時 SCR 停在 APPROVED，可重試。"""
    rid = str(row["id"])
    env.writer.persist(Op("scr.update", rid, {
        "research_id": rid, "scr_id": str(scr["id"]), "status": "APPROVED",
        "prd_to_version_no": to_version_no, "decided_by": approver,
        "decided_at": NOW().isoformat(), "actor": approver}))
    from_no = scr.get("prd_from_version_no")
    old = env.db.query("SELECT rel_path FROM {s}.research_prd_versions WHERE research_id = %s "
                       "AND version_no = %s", (rid, from_no)) if from_no else []
    old_rel = str(old[0]["rel_path"]) if old else route_mod.BASELINE_REL
    try:
        old_text = layout.safe_join(Path(row["workspace_path"]), old_rel).read_text(
            encoding="utf-8")
    except OSError:
        old_text = ""
    base = Baseline(rel=rel, sha256=sha256, text=text, from_version_no=from_no,
                    to_version_no=to_version_no, semver=semver, gate_decision_id=decision_id,
                    scope_changed=bool(old_text) and module_of_text(old_text) != module_of_text(
                        text))
    fresh = env.db.get_scr(rid, int(scr["scr_no"])) or dict(scr)
    return apply_and_record(env, row, fresh, approver=approver, base=base).as_dict()
