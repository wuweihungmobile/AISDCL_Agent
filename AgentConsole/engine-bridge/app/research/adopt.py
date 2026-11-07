"""內環鍵建立與 Stage-1 基線採納（PRD AC-R2P-11-7；ADR-XPLAT-017 D2；D-126；TCS AC-961-7）。

分流成功之前的最後兩步（`IMPL_KEY_INIT`、`BASELINE_ADOPT`）都在這裡：Bridge 於目標根以 `show`
（不帶 `--must-exist`）建出內環鍵的狀態檔，再走 `SCENARIO_DETECT → AGENT_LOAD → SPEC_DRAFTING →
SCG_VALIDATION → HUMAN_PENDING`（共五次 `transition`，理由皆以 `baseline adoption` 起頭並載明 SCG 已
在外環鍵通過與外環決定 id），最後 `spec-frozen --stage Stage-1`。**採納不走 `gate`**（D-45：SCG 已在
外環鍵通過，內環鍵不重跑）。

單一函式、單一 Stage（D-126）：`adopt_baseline` 是整個研究面唯一在內環鍵建檔、也是外環 Gate 0 之外
唯一呼叫 `spec_frozen` 的地方；AST 鎖 C2 的白名單只收這一個函式、且限 `stage="Stage-1"`。
`stage` 參數把序列切成 `init`（只建檔）與 `adopt`（轉態＋凍結）兩段，供分流的兩個步驟各呼叫一次；
`all` 兩段一起做（測試與獨立使用）。

冪等：每一步先讀現態（`fsm_ops.current_state`），已達目標就略過，所以中斷後重跑只補沒做完的；現態
不在採納路徑上（例如已在 IMPLEMENTATION）＝409 `fsm_state_conflict`、零寫入。本模組不直接
存取框架的 FSM 執行期與狀態檔（寫入一律經 `fsm_ops`／`sdd_cli`）。
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import sdd_cli
from ..errors import ApiError
from ..sdd_state import readable_state_file
from ..security import AuditLog
from . import fsm_ops

#: 採納路徑（INIT 之後的五個轉態）；順序即呼叫序。
ADOPTION_PATH: tuple[str, ...] = (
    "SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING", "SCG_VALIDATION", "HUMAN_PENDING")
_ORDER: tuple[str, ...] = ("INIT", *ADOPTION_PATH)
#: 採納凍結的 Stage 名（內環鍵只准 Stage-1；`sdd_cli.INNER_FREEZE_STAGES`）。
ADOPTION_STAGE = "Stage-1"
STAGES = ("init", "adopt", "all")


@dataclass(frozen=True)
class AdoptCtx:
    """一次採納的輸入。`root` 是目標根（`--root`）、`prd_rel` 是已發佈 PRD 相對 `root` 的 POSIX
    路徑（`--doc`）；`outer_key`、`gate_decision_id`、`prd_sha256` 只進理由字串（可稽核的出處）。"""

    sdd_root: Path | None
    state_dir: Path
    key: str
    root: Path
    prd_rel: str
    outer_key: str
    gate_decision_id: str
    prd_sha256: str
    approver: str
    allowed_roots: Sequence[Path]
    audit: AuditLog | None = None


def adoption_reason(ctx: AdoptCtx) -> str:
    """五次 `transition` 共用的同一句理由（須以 `baseline adoption` 起頭；`sdd_cli` 白名單）。"""
    return (f"baseline adoption; SCG 已在外環鍵 {ctx.outer_key} 通過: "
            f"gate_decision {ctx.gate_decision_id}")


def _frozen_stage_names(state: dict[str, Any]) -> list[str]:
    return [str(item.get("stage")) for item in (state.get("frozen_stages") or [])
            if isinstance(item, dict)]


def adopt_baseline(ctx: AdoptCtx, *, stage: str = "all") -> dict[str, Any]:
    """建內環鍵（`stage` 為 `init`／`all`）並採納基線（`adopt`／`all`）。回傳
    `{"created": bool, "transitions": [目標態…], "frozen": bool, "state": 現態,
    "spec_doc_digests": {…}｜None}`；失敗拋 `ApiError`（呼叫端標步驟 `FAILED`）。"""
    if stage not in STAGES:
        raise ValueError(f"stage 須為 {STAGES}")
    if sdd_cli.is_outer_key(ctx.key):                 # 只用於內環鍵（AST 鎖 C2 要求這個守衛存在）
        raise ValueError("adopt_baseline 只用於內環鍵；外環鍵的凍結只走 :approve-baseline")
    fctx = fsm_ops.FsmCtx(sdd_root=ctx.sdd_root, state_dir=ctx.state_dir, key=ctx.key,
                          audit=ctx.audit, actor=ctx.approver)
    out: dict[str, Any] = {"created": False, "transitions": [], "frozen": False,
                           "spec_doc_digests": None}
    exists = readable_state_file(ctx.state_dir, ctx.key) is not None
    if stage in ("init", "all") and not exists:
        fsm_ops.create_key(fctx, allowed_roots=ctx.allowed_roots, inner=True)
        out["created"], exists = True, True
    if stage == "init":
        out["state"] = fsm_ops.current_state(fctx)
        return out
    if not exists:
        raise fsm_ops.conflict("fsm_state_conflict", current_state=None, cause="key_missing")
    state = fsm_ops.read_current(fctx)
    current = str(state.get("current_state"))
    if current == "SPEC_FROZEN" and ADOPTION_STAGE in _frozen_stage_names(state):
        out.update(state=current, frozen=True)           # 已採納：零 FSM 寫入、冪等成功
        return out
    if current not in _ORDER:
        raise fsm_ops.conflict("fsm_state_conflict", current_state=current,
                               cause="not_on_adoption_path")
    reason = adoption_reason(ctx)
    for target in _ORDER[_ORDER.index(current) + 1:]:
        fsm_ops.transition(fctx, to=target, reason=reason)
        out["transitions"].append(target)
    frozen = fsm_ops.spec_frozen(
        fctx, stage="Stage-1", docs=[ctx.prd_rel], root=str(ctx.root), approver=ctx.approver,
        reason=(f"Stage-1 baseline adoption: gate_decision {ctx.gate_decision_id}; "
                f"PRD sha256 {ctx.prd_sha256}")[:500])
    digests = dict(frozen["spec_doc_digests"])
    got = str(digests.get(ctx.prd_rel, "")).removeprefix("sha256:")
    if got != ctx.prd_sha256:
        raise ApiError(502, "sdd_cli_failed",
                       detail=f"內環 Stage-1 的 PRD 摘要 {got!r} 不等於外環 Gate 0 凍結摘要")
    out.update(state="SPEC_FROZEN", frozen=True, spec_doc_digests=digests)
    return out
