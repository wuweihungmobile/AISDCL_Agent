"""SddGovernancePlugin — SDD 治理橫切層（plugin_entry tier ≤250 LOC）。

對應 AutoSDD_improving_01.md §4（W6）。PRIORITY=45：token_guard(30)/anchor(35)/
persistence(40) 之後、PRE_ATTEMPT tie-breaker 群(50) 之前——閘門先於快速路徑。

phase 對應（zero-trust 實測修正）：計畫 §4.1 引用之 POST_EVALUATE / ON_ESCALATION
為合法 KernelPhase 枚舉但 kernel 現況**不派發**（kernel.py 實際派發
PRE_RUN/PRE_STEP/PRE_ATTEMPT/POST_ATTEMPT/ON_SUCCESS/ON_FAILURE/POST_STEP/POST_RUN）。
本 plugin 同時訂閱兩組：計畫指定 phase（向前相容、未來 kernel 派發即生效）+
實際派發 phase（真實行為載體）。偏差已記入 AutoSDD_Defect_Log（DEF-01-006）。

相依（constructor 注入 ports，禁 import infra）：
  IBrain.decide_escalation       違反 ≥N 次時諮詢升級決策（advisory）
  IObservabilityPort             sdd.scg_gate_pass/fail counter + 違反事件（contract #7）
  ISpecSource                    PRE_RUN 載入凍結規格（digest 防 drift）
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.hookspec import (
    CounterSnapshotResult,
    HookContext,
    KernelPhase,
    VetoResult,
)
from ..core.ports.observability import IObservabilityPort, NullObservability
from ..core.ports.spec_source import ISpecSource, SddSpec, SpecNotFrozenError

logger = logging.getLogger("autoclaude.plugins.sdd_governance")

_SDD_WORKFLOWS = frozenset({"aisdlc", "aisdlc_sdd"})
_GATE_ORDER = ("SCG-0", "SCG-1", "SCG-2", "SCG-3", "SCG-4", "SCG-5", "SCG-6")


class SddGovernancePlugin:
    """SCG 閘門守門 + 契約違反記帳 + spec digest 防 drift + checkpoint 掛載。"""

    PRIORITY = 45

    def __init__(
        self,
        brain: Any | None = None,
        observability: IObservabilityPort | None = None,
        spec_source: ISpecSource | None = None,
        *,
        escalation_threshold: int = 3,  # 鏡像 SCG-4「同模式 3 次 → SPEC_AUDIT」
    ):
        self._brain = brain
        self._obs = observability or NullObservability()
        self._spec_source = spec_source
        self._threshold = escalation_threshold
        self._active = False
        self._spec: SddSpec | None = None
        self._gate_of_step: dict[str, str] = {}
        self._at_of_step: dict[str, str] = {}
        self._state: dict = {"scg_gate": None, "fsm_state": None,
                             "contract_violations": [], "spec_digest": None}

    def name(self) -> str:
        return "sdd_governance"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [
            KernelPhase.PRE_RUN,
            KernelPhase.PRE_ATTEMPT,
            KernelPhase.POST_ATTEMPT,            # 實際派發：per-attempt 失敗記帳
            KernelPhase.ON_SUCCESS,              # 實際派發：違反清除 + drift 巡檢
            KernelPhase.ON_FAILURE,              # 實際派發：步驟竭盡 → 升級諮詢
            KernelPhase.POST_EVALUATE,           # 計畫指定（kernel 現況不派發）
            KernelPhase.ON_ESCALATION,           # 計畫指定（kernel 現況不派發）
            KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,
            KernelPhase.ON_CHECKPOINT_RESTORE,
        ]

    def on_event(self, ctx: HookContext) -> Any | None:
        phase = ctx.phase
        if phase == KernelPhase.PRE_RUN:
            return self._on_pre_run(ctx)
        if not self._active:
            return None
        if phase == KernelPhase.PRE_ATTEMPT:
            return self._on_pre_attempt(ctx)
        if phase in (KernelPhase.POST_ATTEMPT, KernelPhase.POST_EVALUATE):
            return self._on_post_attempt(ctx)
        if phase == KernelPhase.ON_SUCCESS:
            return self._on_success(ctx)
        if phase in (KernelPhase.ON_FAILURE, KernelPhase.ON_ESCALATION):
            return self._on_failure(ctx)
        if phase == KernelPhase.ON_CHECKPOINT_SAVE_REQUEST:
            return CounterSnapshotResult(
                contributor=self.name(),
                snapshot={"sdd_governance": self.snapshot()},
            )
        if phase == KernelPhase.ON_CHECKPOINT_RESTORE:
            self._on_checkpoint_restore(ctx)
        return None

    # ── 公開 API ────────────────────────────────────────────────
    def snapshot(self) -> dict:
        return {
            "scg_gate": self._state["scg_gate"],
            "fsm_state": self._state["fsm_state"],
            "contract_violations": [dict(v) for v in self._state["contract_violations"]],
            "spec_digest": self._state["spec_digest"],
        }

    def restore(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        self._state["scg_gate"] = data.get("scg_gate")
        self._state["fsm_state"] = data.get("fsm_state")
        self._state["contract_violations"] = [
            dict(v) for v in data.get("contract_violations", [])]
        restored = data.get("spec_digest")
        if (restored and self._state["spec_digest"]
                and restored != self._state["spec_digest"]):
            # 切版 / 規格變動後 resume → advisory（§6 遷移規則 5c），非 hard fail
            self._obs.record_event("sdd.spec_digest_mismatch", {
                "checkpoint_digest": restored,
                "loaded_digest": self._state["spec_digest"]})
        elif restored:
            self._state["spec_digest"] = restored

    # ── phase handlers ─────────────────────────────────────────
    def _on_pre_run(self, ctx: HookContext) -> VetoResult | None:
        self._active = ctx.playbook.workflow_type in _SDD_WORKFLOWS
        if not self._active or self._spec_source is None:
            return None
        spec_dir = ctx.playbook.workflow_path
        if not spec_dir:
            self._obs.record_event("sdd.spec_dir_missing",
                                   {"project": ctx.playbook.project})
            return None  # 無規格來源 → 治理降級為記帳-only，不阻斷
        try:
            self._spec = self._spec_source.load_spec(spec_dir)
        except SpecNotFrozenError as exc:
            self._obs.emit_counter("sdd.scg_gate_fail", tags={"gate": "SPEC_FROZEN"})
            return VetoResult(contributor=self.name(),
                              reason=f"SDD-VIOLATION[SPEC_NOT_FROZEN] {exc}")
        self._state["spec_digest"] = self._spec.digest
        self._state["fsm_state"] = "IMPLEMENTATION"
        for c in self._spec.contracts:
            step_id = f"sdd-{self._spec.scenario}-{c.at_id.lower()}"
            self._gate_of_step[step_id] = c.scg_gate
            self._at_of_step[step_id] = c.at_id
        self._obs.emit_counter("sdd.scg_gate_pass", tags={"gate": "SPEC_FROZEN"})
        return None

    def _on_pre_attempt(self, ctx: HookContext) -> VetoResult | None:
        if ctx.task is None:
            return None
        gate = self._gate_of_step.get(ctx.task.step_id)
        if gate is None:
            return None  # 非 SDD 編譯步驟，不守門
        blocked = self._lower_gates_with_open_violations(gate)
        if blocked:
            at_id = self._at_of_step.get(ctx.task.step_id, ctx.task.step_id)
            self._obs.emit_counter("sdd.scg_gate_fail", tags={"gate": gate})
            return VetoResult(
                contributor=self.name(),
                reason=(f"SDD-VIOLATION[{at_id}] 越閘存取：{gate} 步驟不得在 "
                        f"{sorted(blocked)} 仍有未解違反時執行"),
            )
        self._state["scg_gate"] = gate
        return None

    def _on_post_attempt(self, ctx: HookContext) -> None:
        payload = ctx.payload or {}
        if ctx.task is None or not payload.get("failure_reason"):
            return
        if ctx.task.step_id not in self._gate_of_step:
            return
        self._record_violation(ctx.task.step_id, payload.get("failure_reason", ""))
        self._check_drift()

    def _on_success(self, ctx: HookContext) -> None:
        if ctx.task is not None:
            sid = ctx.task.step_id
            self._state["contract_violations"] = [
                v for v in self._state["contract_violations"]
                if v.get("step_id") != sid]
        self._check_drift()

    def _on_failure(self, ctx: HookContext) -> None:
        if ctx.task is None or ctx.task.step_id not in self._gate_of_step:
            return
        sid = ctx.task.step_id
        count = sum(1 for v in self._state["contract_violations"]
                    if v.get("step_id") == sid)
        if count < self._threshold or self._brain is None:
            return
        try:  # 升級諮詢屬 advisory；Brain 故障不得拖垮既有 escalation 鏈
            self._brain.decide_escalation(
                task=ctx.task,
                failure_history=[v for v in self._state["contract_violations"]
                                 if v.get("step_id") == sid],
                convergence_trend="sdd_contract_violation",
                global_goal=ctx.playbook.global_goal,
            )
            self._obs.record_event("sdd.escalation_consult",
                                   {"step_id": sid, "violations": count})
        except Exception as exc:  # noqa: BLE001 — fallback 走既有 PlaybookEvolver 鏈
            logger.warning("sdd_governance: decide_escalation 失敗（fallback 既有鏈）: %s", exc)

    def _on_checkpoint_restore(self, ctx: HookContext) -> None:
        cp = (ctx.payload or {}).get("checkpoint")
        gov = getattr(cp, "sdd_governance", None)
        if gov:
            self.restore(gov)

    # ── 內部 helpers ───────────────────────────────────────────
    def _record_violation(self, step_id: str, reason: str) -> None:
        at_id = self._at_of_step.get(step_id, step_id)
        entry = {"step_id": step_id, "at_id": at_id,
                 "reason": reason[:200],
                 "ts": datetime.now().isoformat(timespec="seconds")}
        self._state["contract_violations"].append(entry)
        self._obs.record_event("sdd.contract_violation", entry)

    def _lower_gates_with_open_violations(self, gate: str) -> set[str]:
        try:
            gate_rank = _GATE_ORDER.index(gate)
        except ValueError:
            return set()
        open_gates = {self._gate_of_step.get(v.get("step_id", ""), "")
                      for v in self._state["contract_violations"]}
        return {g for g in open_gates
                if g in _GATE_ORDER and _GATE_ORDER.index(g) < gate_rank}

    def _check_drift(self) -> None:
        """spec digest 防 drift（advisory，非阻塞）——規格檔在執行中被改動。"""
        if self._spec is None:
            return
        path = Path(self._spec.spec_path)
        if not path.is_file():
            return
        digest = "sha256:" + hashlib.sha256(
            path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        if digest != self._spec.digest:
            self._obs.record_event("sdd.spec_drift", {
                "spec_path": str(path), "frozen_digest": self._spec.digest,
                "current_digest": digest})
