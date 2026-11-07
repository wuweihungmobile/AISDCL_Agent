"""外環／內環 FSM 鍵的驅動（ADR-XPLAT-017 D1、D2、D4、D6、§4；TCS AC-960-13）。

兩把鍵（D1）：外環 `research-<slug>[-g<N>]`（狀態目錄在研究工作區
`build/reports/fsm`）、內環 `<sub>-<slug>`（P1 起）。本模組是研究面對 FSM 的
**唯一**驅動：每一次寫入都經 `sdd_cli` 的研究面入口（`run_research_verb`；
動詞白名單、固定環境、20 秒逾時、`(狀態目錄, 鍵)` 互斥鎖），Bridge 不開寫任何
FSM 狀態檔（機械鎖：`tests/test_research_ast_locks.py`）。狀態只用「直接讀」
確認（`sdd_state.read_state`，唯讀、罩同一把鎖）。

三條通則：
  · **預檢＋事後讀驗**（`transition`、`gate`）：`transition` 是舊 CLI 契約
    （成功只印一行文字、非法轉態是 traceback），所以先讀現態、對鏡像邊表預檢
    （起子行程之前拒絕非法轉態），再呼叫，最後讀回現態與目標比對；
    不符回 502，不靜默成功。
  · **以回傳為準、不自建計數**：`gate` 的 `next_state`／`retry_count`／
    `escalated` 全取自 CLI 的 JSON；本模組沒有任何 retry 計數變數。壞輸出
    （非 JSON、缺鍵、與結果矛盾）一律 502。
  · **唯一建檔點**：`create_key` 是整個研究套件裡唯一以「不帶 `--must-exist`」
    呼叫 `show` 的地方；呼叫者只有專案初始化與換世代（ADR-XPLAT-017 D2 的第三個
    呼叫點 `:route` 屬 P1）。

HUMAN_PENDING 守則（D-50）刻意**不**放在這裡：`gate` 在此是忠實的包裝（測試要靠它
證明框架在 HUMAN_PENDING 下 PASS 會以 rc 1 結束）；「現態為 HUMAN_PENDING 時不呼叫
`gate … PASS`」的守衛住在呼叫端（審查判定處），並由 AST 鎖釘住。核准（Gate 0）也
只在 HTTP 處理函式內呼叫 `approve_baseline`。
"""
from __future__ import annotations

import os
import platform
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import sdd_cli
from ..errors import ApiError
from ..sdd_state import (
    ESCALATION_STATES,
    load_state,
    read_state,
    readable_state_file,
    recovery_commands,
)
from ..security import AuditLog, is_within
from ..tracing import trace_id_var
from .layout import sanitization_failed
from .settings import NOT_EVALUABLE

#: Gate 0 的 Stage 名（`spec-frozen --stage`）。
GATE0_STAGE = "Gate-0"
#: 外環鍵初始化要走到的狀態（INIT→SCENARIO_DETECT→AGENT_LOAD）。
INIT_PATH: tuple[str, ...] = ("SCENARIO_DETECT", "AGENT_LOAD")
#: `gate` FAIL 耗盡後的現態集合（外環鍵的環境關閉自動恢復，正常只會是 ESCALATION）。
_ESCALATED_STATES = ESCALATION_STATES | {"AUTO_RECOVERY_ATTEMPT"}
#: `gate … PASS` 的下一態（鏡像 `next_state_on_gate_pass`；`gate` 回傳與它矛盾＝502）。
_PASS_NEXT: dict[str, str] = {
    "SCG_VALIDATION": "HUMAN_PENDING", "PR_REVIEW": "RTM_VERIFY", "RTM_VERIFY": "RELEASE_READY",
    "RELEASE_READY": "RELEASE",
}

#: 鏡像邊表：研究面的 `transition --to` 值域內、各來源態的合法目標。是框架 `_HAPPY_PATH` 的**子集**
#: （只列研究面會用到的邊）；`tests/test_research_fsm_ops.py` 在 `SDD_ROOT` 存在時逐邊對拍，框架改邊
#: 時對拍會紅，不靠人記得同步。`HUMAN_PENDING` 的目標只有基線採納路徑（內環鍵，來源只能是
#: SCG_VALIDATION）。
MIRROR_EDGES: dict[str, frozenset[str]] = {
    "INIT": frozenset({"SCENARIO_DETECT"}),
    "SCENARIO_DETECT": frozenset({"AGENT_LOAD"}),
    "AGENT_LOAD": frozenset({"SPEC_DRAFTING"}),
    "SPEC_DRAFTING": frozenset({"SCG_VALIDATION"}),
    "SCG_VALIDATION": frozenset({"SPEC_DRAFTING", "HUMAN_PENDING"}),
    "HUMAN_PENDING": frozenset({"SPEC_REGRESSION_CHECK"}),
    "SPEC_FROZEN": frozenset({"SPEC_DRAFTING"}),
    "IMPLEMENTATION": frozenset({"PR_REVIEW", "SPEC_AUDIT"}),
    "EXECUTION_EVALUATION": frozenset({"PR_REVIEW", "SPEC_AUDIT"}),
    "ADVERSARIAL_EVALUATION": frozenset({"PR_REVIEW", "SPEC_AUDIT"}),
    "PR_REVIEW": frozenset({"SPEC_AUDIT"}),
    "SPEC_AUDIT": frozenset({"PR_REVIEW"}),
    "RELEASE_READY": frozenset({"RELEASE"}),
}


@dataclass(frozen=True)
class FsmCtx:
    """一把 FSM 鍵的執行脈絡：框架樹、狀態目錄（絕對路徑）、鍵，以及稽核用的物件與人。"""

    sdd_root: Path | None
    state_dir: Path
    key: str
    audit: AuditLog | None = None
    #: 稽核欄位 `approver` 的值（JWT subject 或 `bridge`）；只進稽核，不是權限來源。
    actor: str | None = None

    @property
    def outer(self) -> bool:
        return sdd_cli.is_outer_key(self.key)


def edge_allowed(src: str, dst: str) -> bool:
    return dst in MIRROR_EDGES.get(src, frozenset())


def _violation(field: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field, "rule": rule, "message": message}


def key_violations(key: object, *, inner: bool = False) -> list[dict[str, str]]:
    if inner:
        if not isinstance(key, str) or not sdd_cli.is_inner_key(key):
            return [_violation("fsm_project", "invalid_key",
                               "內環鍵須符合 ^[a-z][a-z0-9-]{1,99}$ 且不是外環鍵形態")]
        return []
    if not isinstance(key, str) or not sdd_cli.is_outer_key(key):
        return [_violation("fsm_project", "invalid_key",
                           "外環鍵須符合 ^research-[a-z0-9][a-z0-9-]{0,29}(-g[0-9]+)?$")]
    return []


def state_dir_violations(state_dir: Path, allowed_roots: Iterable[Path]) -> list[dict[str, str]]:
    """狀態目錄須是絕對路徑、在允許根之下、且以 `build/reports/fsm` 結尾（框架 adapter 以「向上找
    含 `build/reports/fsm` 的目錄」定位狀態檔，目錄形態不對＝日後讀不到）。"""
    out: list[dict[str, str]] = []
    if not state_dir.is_absolute():
        out.append(_violation("state_dir", "not_absolute", "狀態目錄須是絕對路徑"))
        return out
    if tuple(part.lower() for part in state_dir.parts[-3:]) != ("build", "reports", "fsm"):
        out.append(_violation("state_dir", "bad_suffix", "狀態目錄須以 build/reports/fsm 結尾"))
    if not any(is_within(state_dir, root) for root in allowed_roots):
        out.append(_violation("state_dir", "outside_allowed_roots", "狀態目錄不在允許的根目錄之下"))
    return out


def conflict(reason: str, **details: Any) -> ApiError:
    """研究面的 409：欄位放在 `details` 物件（`details.current_state`、`details.recovery`…）。"""
    return ApiError(409, reason, details=details)


def _run(ctx: FsmCtx, verb: str, args: Sequence[str], *, create: bool = False,
         approver: str | None = None, inner_create: bool = False) -> dict[str, Any]:
    return sdd_cli.run_research_verb(
        verb, args, sdd_root=ctx.sdd_root, state_dir=ctx.state_dir, project=ctx.key,
        create=create, audit=ctx.audit, approver=approver if approver is not None else ctx.actor,
        inner_create=inner_create)


def _bad(ctx: FsmCtx, verb: str, problem: str) -> ApiError:
    """壞輸出或讀回不符：記一筆稽核（決策與原因，不含環境與權杖）並回 502 `sdd_cli_failed`。"""
    if ctx.audit is not None:
        ctx.audit.record("sdd_cli", verb=verb, project=ctx.key, approver=ctx.actor,
                         result=f"rejected:{problem}", rc=None, trace_id=trace_id_var.get())
    return ApiError(502, "sdd_cli_failed", detail=f"{verb}: {problem}")


# ── 唯讀（直接讀狀態檔；與寫入共用同一把 (狀態目錄, 鍵) 鎖）────────────────────────────────────
def read_current(ctx: FsmCtx) -> dict[str, Any]:
    """狀態檔的 `fsm_state` 節點；缺檔 404 `fsm_not_found`、壞檔 422 `fsm_state_unreadable`。"""
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        return read_state(ctx.state_dir, ctx.key)[1]


def current_state(ctx: FsmCtx) -> str:
    state = read_current(ctx)
    value = state.get("current_state")
    if not isinstance(value, str):
        raise ApiError(422, "fsm_state_unreadable", detail="current_state is not a string")
    return value


def snapshot(ctx: FsmCtx) -> dict[str, Any]:
    """`state.json` 投影用的 FSM 片段；讀不動時回 `NOT-EVALUABLE`，不拋例外（投影不得拖垮流程）。"""
    try:
        state = read_current(ctx)
    except ApiError:
        return {"project": ctx.key, "state": NOT_EVALUABLE, "updated_at": None,
                "frozen_stages": []}
    return {"project": ctx.key, "state": state.get("current_state"),
            "updated_at": state.get("updated_at"),
            "frozen_stages": list(state.get("frozen_stages") or [])}


_CONTAINER_MARKER = Path("/.dockerenv")
_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,252}$")


def in_container() -> bool:
    """Bridge 是否跑在容器內（Linux Docker 在根目錄放 `/.dockerenv`；主機上的 Bridge 一律否）。"""
    return _CONTAINER_MARKER.is_file()


def host_enter_command(*, container: bool, hostname: str | None) -> str | None:
    """容器內的 Bridge：`recovery.powershell`／`posix` 的路徑是**容器內**路徑（框架樹、狀態目錄都在
    容器裡），主機上的人直接貼會找不到；這是主機 PowerShell 進入該容器的指令（容器的主機名預設就是
    容器 ID，`docker exec` 認得），進去後再貼 `posix` 那一行（INT-14 ④）。不在容器內、或主機名
    不是合法的容器識別字＝None（不寫一個猜出來的指令）。"""
    if not container or not hostname or not _HOSTNAME_RE.match(hostname):
        return None
    return f"docker exec -it {hostname} sh"


def escalated_error(ctx: FsmCtx, state: Mapping[str, Any]) -> ApiError:
    """409 `escalated`：ESCALATION 類現態下自動修訂與新審查一律被擋，`details.recovery` 帶可複製的
    恢復指令（target、powershell、posix；容器內另帶 `host_powershell`，見 `host_enter_command`）。
    恢復只有人能做，這裡不提供恢復動詞。"""
    root = ctx.sdd_root if ctx.sdd_root is not None else Path()
    recovery = recovery_commands(dict(state), sdd_root=root, fsm_dir=ctx.state_dir, key=ctx.key)
    entry = host_enter_command(container=in_container(),
                               hostname=os.environ.get("HOSTNAME") or platform.node())
    if entry is not None:
        recovery = {**recovery, "host_powershell": entry}
    return conflict("escalated", current_state=state.get("current_state"), recovery=recovery)


def is_escalated(state: Mapping[str, Any]) -> bool:
    current = state.get("current_state")
    return isinstance(current, str) and current in ESCALATION_STATES


# ── 寫入（全部經 sdd_cli.run_research_verb）──────────────────────────────────────────────────
def create_key(ctx: FsmCtx, *, allowed_roots: Iterable[Path], inner: bool = False) -> str:
    """**唯一建檔點**：`show` 不帶 `--must-exist`，缺檔時框架 CLI 依模板建出 INIT 狀態檔。

    呼叫者（P0）只有專案初始化（`POST /research/projects`；重試初始化沿用同一流程）與 `:reinit` 的
    換世代模式。鍵或目錄不合規＝422 `sanitization_failed`；建檔前檔案已存在＝409
    `fsm_state_conflict`（`details.cause=key_exists`）；建後讀回不是 INIT＝502。回傳 `"INIT"`。"""
    violations = key_violations(ctx.key, inner=inner) + state_dir_violations(
        ctx.state_dir, allowed_roots)
    if violations:
        raise sanitization_failed(violations)
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        existing = readable_state_file(ctx.state_dir, ctx.key)
        if existing is not None:
            try:
                current: Any = load_state(existing).get("current_state")
            except ApiError:
                current = None
            raise conflict("fsm_state_conflict", current_state=current, cause="key_exists")
        _run(ctx, sdd_cli.RESEARCH_VERB_SHOW, [], create=True, inner_create=inner)
        after = current_state(ctx)
    if after != "INIT":
        raise _bad(ctx, sdd_cli.RESEARCH_VERB_SHOW, f"created state is {after!r}, expected INIT")
    return after


def show(ctx: FsmCtx) -> dict[str, Any]:
    """CLI `show --must-exist` 的 `fsm_state` 節點（框架自己的載入器讀出的樣子）。"""
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        payload = _run(ctx, sdd_cli.RESEARCH_VERB_SHOW, [])
    state = payload.get("fsm_state")
    if not isinstance(state, dict):
        raise _bad(ctx, sdd_cli.RESEARCH_VERB_SHOW, "output has no fsm_state object")
    return state


def transition(ctx: FsmCtx, *, to: str, reason: str) -> str:
    """預檢（現態→目標在鏡像邊表內，否則在起子行程之前 409）→呼叫→讀回比對（不符 502）。"""
    args = sdd_cli.research_transition_args(to=to, reason=reason)
    sdd_cli.check_research_allowed(sdd_cli.RESEARCH_VERB_TRANSITION, args, key=ctx.key)
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        before = current_state(ctx)
        if not edge_allowed(before, to):
            raise conflict("fsm_state_conflict", current_state=before, target=to,
                           cause="transition_not_allowed")
        payload = _run(ctx, sdd_cli.RESEARCH_VERB_TRANSITION, args)
        after = current_state(ctx)
    if payload.get("current_state") != to or after != to:
        raise _bad(ctx, sdd_cli.RESEARCH_VERB_TRANSITION,
                   f"requested {to!r} but the cli reported {payload.get('current_state')!r} and "
                   f"the state file reads {after!r}")
    return after


def gate_payload_problem(gate: str, result: str, payload: Any) -> str | None:
    """`gate` 回傳的健檢（純函式）：形狀、回聲、與結果矛盾的 `next_state`。合格回 None。"""
    if not isinstance(payload, dict):
        return "output is not an object"
    verdict = result.upper()
    for key in ("gate", "result", "next_state"):
        if key not in payload:
            return f"output lacks {key!r}"
    if payload["gate"] != gate or str(payload["result"]).upper() != verdict:
        return "output echoes a different gate or result than the one requested"
    nxt = payload["next_state"]
    if not isinstance(nxt, str):
        return "next_state is not a string"
    escalated = payload.get("escalated")
    if escalated is not None and not isinstance(escalated, bool):
        return "escalated is not a boolean"
    if verdict == "PASS":
        if escalated or nxt != _PASS_NEXT.get(gate):
            return f"a PASS on {gate} cannot end in {nxt!r}"
        return None
    count = payload.get("retry_count")
    if "retry_count" not in payload:
        return "a FAIL output lacks 'retry_count'"
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        return "retry_count is not a positive integer"
    if bool(escalated) != (nxt in _ESCALATED_STATES):
        return f"escalated={bool(escalated)} contradicts next_state={nxt!r}"
    return None


def gate(ctx: FsmCtx, *, gate: str, result: str, reason: str) -> dict[str, Any]:
    """呼叫 `gate`，**以 CLI 回傳為準**（`next_state`／`retry_count`／`escalated`
    原樣採用）；輸出壞形狀或與讀回的現態不符＝502（不改任何游標、不標 PASS）。"""
    args = sdd_cli.research_gate_args(gate=gate, result=result, reason=reason)
    sdd_cli.check_research_allowed(sdd_cli.RESEARCH_VERB_GATE, args, key=ctx.key)
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        payload = _run(ctx, sdd_cli.RESEARCH_VERB_GATE, args)
        problem = gate_payload_problem(gate, result, payload)
        if problem is None:
            after = current_state(ctx)
            if after != payload["next_state"]:
                problem = f"the state file reads {after!r} but the cli reported next_state " \
                          f"{payload['next_state']!r}"
    if problem is not None:
        raise _bad(ctx, sdd_cli.RESEARCH_VERB_GATE, problem)
    return payload


def spec_frozen(ctx: FsmCtx, *, stage: str, docs: Sequence[str], root: str, reason: str,
                approver: str) -> dict[str, Any]:
    """`spec-frozen --digest --json`：回傳 CLI 的結果（含 `spec_doc_digests`）；
    現態不是 SPEC_FROZEN 或缺摘要＝502。核准人在 `sdd_cli.research_freeze_args`
    內驗證並組進 argv。"""
    args = sdd_cli.research_freeze_args(stage=stage, docs=docs, root=root, reason=reason,
                                        approver=approver)
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        payload = _run(ctx, sdd_cli.RESEARCH_VERB_SPEC_FROZEN, args, approver=approver)
        after = current_state(ctx)
    if after != "SPEC_FROZEN" or not isinstance(payload.get("spec_doc_digests"), dict):
        raise _bad(ctx, sdd_cli.RESEARCH_VERB_SPEC_FROZEN,
                   f"state is {after!r} or the result lacks spec_doc_digests")
    return payload


def approve_baseline(ctx: FsmCtx, *, docs: Sequence[str], root: str, reason: str,
                     approver: str) -> dict[str, Any]:
    """Gate 0 的凍結（`spec-frozen --stage Gate-0`；不要求 TCS）。**唯一的呼叫者是 HTTP 處理函式**
    `POST /research/projects/{id}:approve-baseline`（W-R4：核准只准真人；orchestrator、排程、
    `gate_cli`、啟動鉤子皆不得引用它，機械鎖見 `tests/test_research_ast_locks.py`）。"""
    return spec_frozen(ctx, stage=GATE0_STAGE, docs=docs, root=root, reason=reason,
                       approver=approver)


def spec_refreeze(ctx: FsmCtx, *, docs: Sequence[str], root: str, reason: str,
                  approver: str) -> dict[str, Any]:
    """`spec-refreeze`（僅 SCR 用，P1）：只追加一筆重記條目，不轉態。"""
    args = sdd_cli.research_refreeze_args(docs=docs, root=root, reason=reason, approver=approver)
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        return _run(ctx, sdd_cli.RESEARCH_VERB_SPEC_REFREEZE, args, approver=approver)


def bring_to_agent_load(ctx: FsmCtx) -> str:
    """把外環鍵走到 AGENT_LOAD（INIT→SCENARIO_DETECT→AGENT_LOAD）；冪等：已在 AGENT_LOAD 或更後面
    就不動，只補走尚未走完的前置。回傳現態。"""
    with sdd_cli.state_guard(ctx.state_dir, ctx.key):
        current = current_state(ctx)
        for target in INIT_PATH:
            if current == "INIT" and target == "SCENARIO_DETECT":
                current = transition(ctx, to=target, reason="research workspace initialised")
            elif current == "SCENARIO_DETECT" and target == "AGENT_LOAD":
                current = transition(ctx, to=target, reason="research workspace initialised")
        return current
