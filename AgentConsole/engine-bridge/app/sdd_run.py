"""SDD 批次的建立前預檢、委派的 FSM 寫入與終態同步（ADR-XPLAT-016 §6.3③、§7.3、§10）。

Bridge 是委派與談判狀態的**唯一同步者**（D-115-04）：AutoClaude 與 SDD 互不 import，狀態經由
Bridge 呼叫 FSMRuntime CLI（`sdd_cli.run_verb`）。本模組是 `runner.py` 的 SDD 側手臂，只放「這一
批次該對 FSM 做什麼」的邏輯；對映表與判定本身是 `sdd_sync` 的純函式。

建立流程順序（§10.2；`runner.RunManager._create` 照這個順序呼叫）：
  1 唯讀預檢（路徑閘→規格與凍結→三點摘要→FSM 狀態）→ 4xx，零副作用
  2 取得 advisory lock（既有）
  3 FSM 寫入（`execute_delegation`；在 `_materialize` 之前，失敗時才不留半成品 run 目錄）
  4 `_materialize`（既有）；例外⇒補償 `delegate-exit done`
  5 start／spawn（既有）；spawn 失敗⇒補償 `delegate-exit done`
  6 終態：狀態事件先發布，之後（`handle.lock` 之外）才呼叫 exit（CLI 最壞 20 秒，不該卡住
  `snapshot()`）
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from . import sdd_adapter, security, spec_digest
from .errors import ApiError, fsm_state_conflict, spec_digest_changed, unprocessable
from .fsm_names import fsm_component
from .models import PlaybookIn, SddBlockIn
from .sdd_cli import (
    VERB_DELEGATE_ENTER,
    VERB_DELEGATE_EXIT,
    VERB_NEGOTIATE_ENTER,
    VERB_NEGOTIATE_EXIT,
    delegate_enter_args,
    delegate_exit_args,
    negotiate_enter_args,
    negotiate_exit_args,
    run_verb,
    state_guard,
)
from .sdd_state import delegation_ref, frozen_digest_of, read_state, state_dir_of
from .sdd_sync import (
    APPROVER_DEFAULT,
    PREFLIGHT_EXPECTED_STATES,
    PREFLIGHT_STEPS,
    DelegationVerdict,
    RunFacts,
    clean_approver,
    conflict_fields,
    judge_delegation,
    playbook_ref,
    reason_delegate_enter,
    reason_exit_reclaimed,
    reason_negotiate_enter,
    reason_negotiate_exit,
)
from .settings import Settings
from .tracing import trace_id_var

logger = logging.getLogger("bridge.sdd_run")

#: `resume`／`restore` 時 FSM 的合法現況（其餘含 ESCALATION 一律 409 並不 spawn）。
CONTINUE_EXPECTED_STATES = ["AUTOCLAUDE_DELEGATED", "IMPLEMENTATION"]


@dataclass(frozen=True)
class SddContext:
    """一個 SDD 批次的已驗證路徑與身分（存進 `RunRecord.sdd`；除 approver 與 fsm_project 外不含任
    何機密）。"""

    spec_dir: Path
    spec_file: Path | None
    fsm_project: str
    root: Path
    state_dir: Path
    approver: str

    @property
    def workflow_path(self) -> Path:
        """注入引擎 playbook 的 `workflow_path`＝已驗證的 realpath（有 spec_file 用檔、否則用目
        錄；§8.3）。"""
        return self.spec_file if self.spec_file is not None else self.spec_dir

    @property
    def state_key(self) -> str:
        """回收點比對用的狀態目錄鍵（Windows 不分大小寫：normcase）。"""
        return os.path.normcase(str(self.state_dir))

    def record(self) -> dict[str, Any]:
        return {
            "spec_dir": str(self.spec_dir),
            "spec_file": str(self.spec_file) if self.spec_file is not None else None,
            "fsm_project": self.fsm_project, "root": str(self.root),
            "state_dir": str(self.state_dir), "approver": self.approver, "sync": None}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> SddContext:
        spec_file = data.get("spec_file")
        return cls(
            spec_dir=Path(data["spec_dir"]), spec_file=Path(spec_file) if spec_file else None,
            fsm_project=data["fsm_project"], root=Path(data["root"]),
            state_dir=Path(data["state_dir"]), approver=data.get("approver") or APPROVER_DEFAULT)


@dataclass(frozen=True)
class SddPrecheck:
    ctx: SddContext
    spec: Any
    digest_status: str
    spec_rel: str
    warnings: list[dict[str, Any]]


# ── 1 預檢：路徑閘（§7.3）───────────────────────────────────────────────────────────────────
def build_context(settings: Settings, block: SddBlockIn, exec_path: Path) -> SddContext:
    """`sdd` 區塊 → 已驗證的 `SddContext`。路徑一律過 `BRIDGE_ALLOWED_PATH_ROOTS`（realpath）；
    `spec_dir` 必須在 `root` 之下（否則 422 `sdd_block_invalid`）；`spec_file` 單獨不存在＝422
    `spec_not_found`（同 `/sdd/compile`），其餘路徑形狀不合＝422 `sanitization_failed`；
    `fsm_project` 原名或淨化後的鍵皆可，一律先過 `fsm_component`；`approver` 的清理規則見
    `sdd_sync.clean_approver`（省略＝`console`）。"""
    roots = settings.allowed_path_roots
    violations: list[dict[str, Any]] = []
    root, found = security.check_path(
        block.root if block.root is not None else str(exec_path), roots, field="sdd.root")
    violations += found
    spec_dir, found = security.check_path(block.spec_dir, roots, field="sdd.spec_dir")
    violations += found
    spec_file: Path | None = None
    spec_missing: str | None = None
    if spec_dir is not None and block.spec_file is not None:
        spec_file, found = security.check_spec_file(spec_dir, block.spec_file,
                                                    field="sdd.spec_file")
        if len(found) == 1 and found[0]["rule"] == "not_found":
            spec_missing = found[0]["message"]     # 與 /sdd/compile 同一個對映（契約 §3.1.4 (e)）
        else:
            violations += found
    if not block.fsm_project.strip():
        violations.append({"field": "sdd.fsm_project", "rule": "empty",
                           "message": "sdd.fsm_project 不可為空白"})
    if violations or root is None or spec_dir is None:
        raise unprocessable(violations)
    if spec_missing is not None:
        raise ApiError(422, "spec_not_found", detail=spec_missing)
    if not security.is_within(spec_dir, root):
        raise ApiError(422, "sdd_block_invalid",
                       detail=f"sdd.spec_dir 必須在 sdd.root 之下：{spec_dir} 不在 {root} 之下")
    return SddContext(spec_dir=spec_dir, spec_file=spec_file,
                      fsm_project=fsm_component(block.fsm_project), root=root,
                      state_dir=state_dir_of(root), approver=clean_approver(block.approver))


# ── 預檢：規格與凍結、三點摘要（§6.3③）─────────────────────────────────────────────────────────
def _spec_rel(ctx: SddContext, spec_path: str | Path | None) -> str:
    """規格檔相對專案根的 POSIX 路徑（談判 reason 的 `oracle=`、`--contract-ref`；摘要鍵同一
    形）。"""
    if spec_path is None:
        return ""
    target = Path(spec_path).resolve()
    try:
        return target.relative_to(ctx.root).as_posix()
    except ValueError:
        return Path(os.path.relpath(target, ctx.root)).as_posix()


def _digest_conflict(exc: Exception, ctx: SddContext) -> ApiError:
    """adapter 的 `SpecDigestMismatchError`（凍結 vs 現檔）→ 409，並盡量補上 `doc`／兩個摘要（只有
    `spec_file`已知時才補：沒有它就不知道 adapter 選了哪一份）。補不到的鍵省略。"""
    doc = frozen = current = None
    if ctx.spec_file is not None:
        doc = _spec_rel(ctx, ctx.spec_file)
        try:
            current = spec_digest.file_digest(ctx.spec_file)
            frozen = frozen_digest_of(read_state(ctx.state_dir, ctx.fsm_project)[1], ctx.spec_file)
        except (OSError, ValueError, ApiError):
            pass
    return spec_digest_changed("frozen_vs_file", doc=doc, frozen_digest=frozen,
                               current_digest=current, message=str(exc))


def load_spec_checked(ctx: SddContext) -> Any:
    """adapter `load_spec`（凍結＝現檔），例外對映成 §6.3 的 HTTP 錯誤。"""
    adapter = sdd_adapter.build_adapter(ctx.fsm_project)
    try:
        return sdd_adapter.load_spec(adapter, ctx.spec_dir, ctx.spec_file)
    except (RuntimeError, ValueError, OSError) as exc:
        if sdd_adapter.is_digest_mismatch(exc):
            raise _digest_conflict(exc, ctx) from exc
        sdd_adapter.raise_for_spec_error(exc)
        raise                                                       # 到不了：上一行必丟


def check_task_digests(ctx: SddContext, spec: Any, task_digests: list[str | None]) -> None:
    """三點摘要的後兩點：匯入時（各任務的 `spec_digest`）必須恰為現檔摘要這一個值。
    任務缺摘要＝Backend 匯入沒存（bug）→ 422 `sdd_block_invalid`；不等＝409 `spec_digest_changed`
    （`pair=import_vs_file`）。凍結 vs 現檔那一點由 adapter 的 `SpecDigestMismatchError` 負責。"""
    if not task_digests or any(d is None for d in task_digests):
        raise ApiError(422, "sdd_block_invalid",
                       detail="含 sdd 區塊的 playbook，每個任務都必須帶匯入時的 spec_digest")
    distinct = sorted({d for d in task_digests if d is not None})
    if distinct != [spec.digest]:
        stale = next(d for d in distinct if d != spec.digest)
        frozen = None
        try:
            frozen = frozen_digest_of(read_state(ctx.state_dir, ctx.fsm_project)[1],
                                      Path(spec.spec_path))
        except (OSError, ValueError, ApiError):
            pass
        raise spec_digest_changed("import_vs_file", doc=_spec_rel(ctx, spec.spec_path),
                                  frozen_digest=frozen, import_digest=stale,
                                  current_digest=spec.digest)


def precheck_spec(ctx: SddContext, playbook: PlaybookIn) -> SddPrecheck:
    spec = load_spec_checked(ctx)
    check_task_digests(ctx, spec, [t.spec_digest for t in playbook.tasks])
    return _precheck_result(ctx, spec)


def _precheck_result(ctx: SddContext, spec: Any) -> SddPrecheck:
    status = sdd_adapter.frozen_digest_status(spec)
    warnings: list[dict[str, Any]] = []
    if status == "absent":
        warnings.append({
            "code": "sdd_frozen_digest_absent",
            "detail": "FSM 狀態檔沒有這份規格的凍結摘要（舊狀態檔或凍結時沒帶 --digest）：只比對"
                      "「匯入時＝現檔」，無法證明現檔就是凍結的那一版"})
    return SddPrecheck(ctx=ctx, spec=spec, digest_status=status,
                       spec_rel=_spec_rel(ctx, spec.spec_path), warnings=warnings)


# ── FSM 現況 → 要做什麼（§10.2 預檢表、§10.3 回收點）─────────────────────────────────────────────
@dataclass(frozen=True)
class DelegationPlan:
    current_state: str
    verbs: tuple[str, ...] = ()
    verdict: DelegationVerdict | None = None        # 現況是 AUTOCLAUDE_DELEGATED 時的判定

    @property
    def own(self) -> bool:
        return self.verdict is not None and self.verdict.action == "own"

    @property
    def reclaim(self) -> bool:
        return self.verdict is not None and self.verdict.action == "reclaim"


def plan_delegation(state: dict[str, Any], *, ctx: SddContext, run_id: str, mode: str,
                    lookup: Callable[[str], RunFacts | None]) -> DelegationPlan:
    """純判定（不寫任何東西）：丟 409 `fsm_state_conflict` 或回傳該依序呼叫的動詞。

    `mode="create"`：IMPLEMENTATION→enter；TEST_CONTRACT_NEGOTIATED→exit agreed＋enter（上次 enter
    後 exit 前中斷的自癒）；SPEC_FROZEN→negotiate-enter＋exit agreed＋enter（首次批次）；
    AUTOCLAUDE_DELEGATED→回收點。
    `mode="continue"`（`resume`／`restore`）：只有 DELEGATED（本 run 的委派直接續；別的 run 走回收
    點）與IMPLEMENTATION（enter 重進）；其餘含 ESCALATION 一律 409，不 spawn。"""
    current = state.get("current_state")
    if current == "AUTOCLAUDE_DELEGATED":
        verdict = judge_delegation(
            delegation_ref(state), new_run_id=run_id, state_dir=ctx.state_key,
            fsm_project=ctx.fsm_project, lookup=lookup)
        if verdict.action == "conflict":
            raise fsm_state_conflict(current, sub_reason=verdict.sub_reason,
                                     **conflict_fields(verdict))
        if verdict.action == "own":
            return DelegationPlan(current, (), verdict)
        return DelegationPlan(current, (VERB_DELEGATE_EXIT, VERB_DELEGATE_ENTER), verdict)
    steps = PREFLIGHT_STEPS.get(current) if isinstance(current, str) else None
    if mode == "continue" and current != "IMPLEMENTATION":
        steps = None
    if steps is None:
        raise fsm_state_conflict(
            current, expected_state=(PREFLIGHT_EXPECTED_STATES if mode == "create"
                                     else CONTINUE_EXPECTED_STATES))
    return DelegationPlan(current, steps)


def read_snapshot(ctx: SddContext) -> dict[str, Any]:
    """唯讀讀取 FSM 現況（`state_guard` 內）：沒有狀態檔＝404 `fsm_not_found`（Bridge 不 init）。"""
    with state_guard(ctx.state_dir, ctx.fsm_project):
        return read_state(ctx.state_dir, ctx.fsm_project)[1]


# ── 3 FSM 寫入（在 `state_guard` 內重讀、重判、再寫；呼叫端已持有 advisory lock） ───────────────
def execute_delegation(ctx: SddContext, run_id: str, *, mode: str, sdd_root: Path | None,
                       audit: Any, lookup: Callable[[str], RunFacts | None],
                       spec_rel: str = "", digest: str = "") -> dict[str, Any]:
    """依預檢表對 FSM 做寫入。回傳 `{entered, reclaimed, negotiated, current_state}`：
    `entered`＝本次呼叫完成了 `delegate-enter`（之後任何失敗都要補償 `delegate-exit done`）。
    CLI 失敗＝丟 ApiError（rc 對映見 `sdd_cli`）；回收的兩步之間 `delegate-enter` 失敗⇒FSM 停在
    IMPLEMENTATION（無委派），呼叫端回 409／5xx 並不 spawn，下次建立從常態進入，不需人工。"""
    outcome: dict[str, Any] = {"entered": False, "reclaimed": None, "negotiated": False}

    def call(verb: str, args: list[str]) -> dict[str, Any]:
        return run_verb(verb, args, sdd_root=sdd_root, state_dir=ctx.state_dir,
                        project=ctx.fsm_project, audit=audit, approver=ctx.approver,
                        context={"run_id": run_id})

    with state_guard(ctx.state_dir, ctx.fsm_project):
        _, state = read_state(ctx.state_dir, ctx.fsm_project)
        plan = plan_delegation(state, ctx=ctx, run_id=run_id, mode=mode, lookup=lookup)
        outcome["current_state"] = plan.current_state
        for verb in plan.verbs:
            if verb == VERB_NEGOTIATE_ENTER:
                call(verb, negotiate_enter_args(
                    reason=reason_negotiate_enter(ctx.approver, run_id),
                    contract_ref=spec_rel or None))
            elif verb == VERB_NEGOTIATE_EXIT:
                call(verb, negotiate_exit_args(
                    reason=reason_negotiate_exit(ctx.approver, spec_rel, digest)))
                outcome["negotiated"] = True
            elif verb == VERB_DELEGATE_EXIT:                    # 回收點：舊委派交還控制權
                verdict = plan.verdict
                assert verdict is not None
                call(verb, delegate_exit_args(
                    decision="done",
                    reason=reason_exit_reclaimed(
                        verdict.old_run_id or "", verdict.old_status, run_id)))
                outcome["reclaimed"] = {"old_run_id": verdict.old_run_id,
                                        "old_status": verdict.old_status}
                if audit is not None:
                    audit.record("sdd_write", verb="reclaim", project=ctx.fsm_project,
                                 approver=ctx.approver, result="ok", run_id=run_id,
                                 old_run_id=verdict.old_run_id, old_status=verdict.old_status,
                                 trace_id=trace_id_var.get())
            elif verb == VERB_DELEGATE_ENTER:
                call(verb, delegate_enter_args(reason=reason_delegate_enter(run_id),
                                               playbook_ref=playbook_ref(run_id)))
                outcome["entered"] = True
    return outcome


def exit_delegation(ctx: SddContext, run_id: str, *, decision: str, reason: str,
                    sdd_root: Path | None, audit: Any) -> dict[str, Any]:
    """`delegate-exit`（`done`｜`failed`）：補償、終態同步與回收共用。在 `state_guard` 內單次呼
    叫。"""
    with state_guard(ctx.state_dir, ctx.fsm_project):
        return run_verb(VERB_DELEGATE_EXIT, delegate_exit_args(decision=decision, reason=reason),
                        sdd_root=sdd_root, state_dir=ctx.state_dir, project=ctx.fsm_project,
                        audit=audit, approver=ctx.approver, context={"run_id": run_id})


def playbook_task_digests(playbook_path: Path) -> list[str | None]:
    """工作區已存的 `playbook.yaml` 各任務的 `spec_digest`（`resume`／`restore` 重驗用：匯入時存下
    的值）。"""
    try:
        doc = yaml.safe_load(playbook_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ApiError(422, "sdd_block_invalid",
                       detail=f"讀不回 run 的 playbook.yaml（{type(exc).__name__}）") from exc
    tasks = doc.get("tasks") if isinstance(doc, dict) else None
    return [t.get("spec_digest") if isinstance(t, dict) else None for t in (tasks or [])]


def revalidate(ctx: SddContext, playbook_path: Path) -> SddPrecheck:
    """`resume`／`restore` 的重驗（§6.3③）：重跑 `load_spec`（凍結＝現檔）並比對任務摘要。"""
    spec = load_spec_checked(ctx)
    check_task_digests(ctx, spec, playbook_task_digests(playbook_path))
    return _precheck_result(ctx, spec)
