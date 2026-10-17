"""SDD 委派同步的純函式（ADR-XPLAT-016 §4.4、§5.2、§10）：輸入清理、reason 組字、終態對映、預檢
表、回收點判定。

全部是無 IO 的純函式：對映表因此可以不起任何子行程就窮舉單測（ADR §10.1 末段的建議）。
🔴 `delegate-exit --decision done` 的語意是「委派交還控制權、未升級」，**不是「成功」**
（D-115-15）：run 成敗由後續閘門（SCG-4 審查、RTM 面板）判，FSM 不替它背書；所以完成與使用者取消都
是 `done`，只有引擎升級型失敗是 `failed`（進阻塞態 ESCALATION，恢復留在 SDD session）；基礎設施故
障（額度停機、異常結束、被訊號終止、Bridge 關閉、孤兒）一律**不動**——不得映成阻塞態。
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .errors import ApiError
from .models import TERMINAL_STATUSES, RunStatus

APPROVER_DEFAULT = "console"
APPROVER_MAX = 100
REASON_MAX = 500
DETAIL_MAX = 200
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
RUN_REF_PREFIX = "run:"

#: 活躍 run（D-115-15 列的 RUNNING／PAUSED 是其中兩種；過渡態隨時可能繼續寫，一併視為活躍）。
ACTIVE_RUN_STATUSES = frozenset({
    RunStatus.INITIALIZING.value, RunStatus.RUNNING.value, RunStatus.PAUSING.value,
    RunStatus.PAUSED.value, RunStatus.CANCELLING.value})
TERMINAL_RUN_STATUSES = frozenset(s.value for s in TERMINAL_STATUSES)


# ── 輸入清理（§4.4）：不靜默截斷、不替換，違反即 422 `sdd_invalid_argument` ──────────────────────
def _invalid(field: str, rule: str, detail: str) -> ApiError:
    return ApiError(422, "sdd_invalid_argument", field=field, rule=rule, detail=detail)


def clean_approver(raw: str | None) -> str:
    """簽核人：1～100 字、無控制字元、不含 `;`（讓 `console-… approver=<a>; …` 可無歧義解析）、不
    含前後空白。省略（None）＝`console`（服務身分，稽核上一眼可辨不是具名人，不假裝有人簽）。"""
    if raw is None:
        return APPROVER_DEFAULT
    if not raw.strip():
        raise _invalid("approver", "empty", "approver 不可為空白")
    if raw != raw.strip():
        raise _invalid("approver", "surrounding_whitespace", "approver 不可有前後空白")
    if len(raw) > APPROVER_MAX:
        raise _invalid("approver", "too_long", f"approver 最多 {APPROVER_MAX} 字元")
    if _CONTROL.search(raw):
        raise _invalid("approver", "control_chars", "approver 不可含控制字元")
    if ";" in raw:
        raise _invalid("approver", "semicolon", "approver 不可含 ;（它是 reason 欄位的分隔符）")
    return raw


def clean_user_reason(raw: str) -> str:
    """使用者理由：去前後空白後 1～500 字、無控制字元（含換行）。回傳去空白後的值。"""
    text = raw.strip()
    if not text:
        raise _invalid("reason", "empty", "reason 不可為空白")
    if len(text) > REASON_MAX:
        raise _invalid("reason", "too_long", f"reason 最多 {REASON_MAX} 字元（不會被截斷）")
    if _CONTROL.search(text):
        raise _invalid("reason", "control_chars", "reason 不可含控制字元（含換行）")
    return text


def one_line(text: str, limit: int = DETAIL_MAX) -> str:
    """引擎升級訊息入 reason：取前 limit 字、換行與控制字元換成空格。"""
    return _CONTROL.sub(" ", text)[:limit]


# ── 六種固定 reason 組字（§4.4）：`console-` 開頭、`key=value` 以 `; ` 分隔 ──────────────────────
def reason_freeze(approver: str, user_reason: str) -> str:
    return f"console-freeze approver={approver}; reason={user_reason}"


def reason_negotiate_enter(approver: str, run_id: str) -> str:
    return f"console-signoff approver={approver}; run={run_id}"


def reason_negotiate_exit(approver: str, oracle_rel: str, digest: str) -> str:
    """§5.2 C-2：內容綁定與誠實條款寫進憑證本身——稽核者讀到「人簽了這份 oracle，且獨立性條款未滿
    足」。"""
    return (f"console-signoff approver={approver}; oracle={oracle_rel}@{digest}; "
            "basis=import-draft-signoff; r9.20.3=not-satisfied")


def reason_delegate_enter(run_id: str) -> str:
    return f"console-run run={run_id} START"


def reason_exit_completed(run_id: str) -> str:
    return f"console-run run={run_id} COMPLETED"


def reason_exit_cancelled(run_id: str) -> str:
    return f"console-run run={run_id} CANCELLED"


def reason_exit_reclaimed(old_run_id: str, old_status: str | None, new_run_id: str) -> str:
    return (f"console-run run={old_run_id} RECLAIMED old_status={old_status or 'missing'} "
            f"by={new_run_id}")


def reason_exit_spawn_failed(run_id: str) -> str:
    return f"console-run run={run_id} SPAWN-FAILED delegation not started"


def reason_exit_failed(run_id: str, step_id: str | None, detail: str) -> str:
    return f"console-run run={run_id} ENGINE-ESCALATION step={step_id or '-'}: {one_line(detail)}"


def playbook_ref(run_id: str) -> str:
    """`delegate-enter --playbook-ref`：`run:<run_id>`（與文件路徑型的 `spec_refs` 可區分；回收只
    認這個形態）。"""
    return f"{RUN_REF_PREFIX}{run_id}"


def default_stage(frozen_count: int) -> str:
    """`:freeze` 請求省略 `stage` 時的預設階段名：`Stage-<n>`，n＝已凍結筆數＋1。"""
    return f"Stage-{frozen_count + 1}"


# ── 終態對映（§10.1）──────────────────────────────────────────────────────────────────────
def terminal_decision(status: str, *, escalation: str = "", stop_requested: bool = False,
                      shutting_down: bool = False, orphan: bool = False) -> str | None:
    """run 終態 → 對 FSM 的動作：`"done"`｜`"failed"`｜`None`（不動）。

    COMPLETED→done；CANCELLED（使用者取消、非孤兒）→done；FAILED 且為**引擎升級型**（`escalation`
    非空；D-115-10：只有這一型）→failed；其餘——額度停機、引擎異常、被訊號終止、spawn 失敗、Bridge
    關閉、孤兒（不論被標成 FAILED 或 CANCELLED）、PAUSED 與其他非終態——一律 None（留給 §10.3 的回
    收點）。
    `stop_requested` 只在「取消與升級同時發生」的邊界上有意義：FAILED 且 `shutting_down` 是 Bridge
    關閉。"""
    if orphan or shutting_down:
        return None
    if status == RunStatus.COMPLETED.value:
        return "done"
    if status == RunStatus.CANCELLED.value:
        return "done"
    if status == RunStatus.FAILED.value and escalation and not stop_requested:
        return "failed"
    return None


# ── 預檢表（§10.2）──────────────────────────────────────────────────────────────────────────
#: FSM 現況 → 要依序呼叫的 CLI 動詞。AUTOCLAUDE_DELEGATED 不在表內：它走回收點
#: （`judge_delegation`）。
PREFLIGHT_STEPS: Mapping[str, tuple[str, ...]] = {
    "IMPLEMENTATION": ("delegate-enter",),
    # 上次 enter 後 exit 前中斷的自癒
    "TEST_CONTRACT_NEGOTIATED": ("negotiate-exit", "delegate-enter"),
    "SPEC_FROZEN": ("negotiate-enter", "negotiate-exit", "delegate-enter"),  # 首次批次
}
#: 409 `fsm_state_conflict` 的 `expected_state`（其餘狀態含 HUMAN_PENDING、ESCALATION 一律衝突）。
PREFLIGHT_EXPECTED_STATES = ["IMPLEMENTATION", "SPEC_FROZEN"]


@dataclass(frozen=True)
class RunFacts:
    """回收點判定要的、關於「被 playbook_ref 引用的那個 run」的事實。"""

    status: str
    state_dir: str | None
    fsm_project: str | None


@dataclass(frozen=True)
class DelegationVerdict:
    action: str                            # "own"｜"reclaim"｜"conflict"
    old_run_id: str | None = None
    old_status: str | None = None          # reclaim：舊終態，或 "missing"（查無此 run）
    sub_reason: str | None = None          # conflict：foreign_delegation｜None（活躍 run）
    run_id: str | None = None
    run_status: str | None = None


def judge_delegation(ref: str | None, *, new_run_id: str, state_dir: str, fsm_project: str,
                     lookup: Callable[[str], RunFacts | None]) -> DelegationVerdict:
    """FSM 在 AUTOCLAUDE_DELEGATED 時，新批次（或 `resume`／`restore`）該怎麼辦（§10.3 五條，依
    序）：

      0. `ref`＝本 run（`run:<本 id>`）→ "own"：自己的委派，直接續（只有 resume／restore 會走到）。
      1. `ref` 缺或不以 `run:` 開頭（外來委派：人在 SDD session 進入的）→
        conflict(foreign_delegation)，Bridge 不碰。
      2. 解出的 run 在 Bridge 登錄查無 → reclaim（old_status＝missing）。
      3. 該 run 的 `state_dir`／`fsm_project` 與本次不同 → conflict(foreign_delegation)（別的 FSM
        專案的 run，
         不是我們能判斷的）。
      4. 該 run 活躍 → conflict（帶 run_id、run_status）。
      5. 該 run 終態 → reclaim。
    🔴 判斷只在 `current_state=AUTOCLAUDE_DELEGATED` 時才讀 `ref`：FSM 檔的 tracking 在 exit 後不
    清除。
    """
    if ref == playbook_ref(new_run_id):
        return DelegationVerdict("own")
    if not ref or not ref.startswith(RUN_REF_PREFIX):
        return DelegationVerdict("conflict", sub_reason="foreign_delegation")
    old_id = ref[len(RUN_REF_PREFIX):]
    facts = lookup(old_id)
    if facts is None:
        return DelegationVerdict("reclaim", old_run_id=old_id, old_status="missing")
    if facts.state_dir != state_dir or facts.fsm_project != fsm_project:
        return DelegationVerdict("conflict", sub_reason="foreign_delegation")
    if facts.status in ACTIVE_RUN_STATUSES:
        return DelegationVerdict("conflict", run_id=old_id, run_status=facts.status)
    return DelegationVerdict("reclaim", old_run_id=old_id, old_status=facts.status)


def conflict_fields(verdict: DelegationVerdict) -> dict[str, Any]:
    """`fsm_state_conflict` 的附加欄位（頂層與 `detail` 共用）。"""
    extra: dict[str, Any] = {}
    if verdict.run_id is not None:
        extra["run_id"] = verdict.run_id
    if verdict.run_status is not None:
        extra["run_status"] = verdict.run_status
    return extra
