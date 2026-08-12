"""HookSpec — Plugin 契約定義（SD_Improving_01.md v1.1 §3.4.1 / SD_Improving_05 W0 T0-1 擴張）。

包含：
  - KernelPhase Enum（27 個 phase：17 原始 + 2 W4-T17/M-11 + 8 SD_05 W0）
  - HookContext（不可變執行上下文）+ per-phase TypedDict payload schemas
  - 10 個 IHookResult（ISP 拆分；4 原始 + 6 SD_05 W0 新增）
  - IHook Protocol（含 priority + subscribed_phases）
  - IResolutionPolicy Protocol（合併策略，DIP 抽出）
  - IMutationStrategy Protocol（Domain Service 的 7 個 strategy）
  - PHASE_RESULT_CONTRACT（每個 phase 限定可回傳的 result 型別；SD_05 W0 補 15 條 → 共 22 phase）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from ..models.playbook import Playbook, PlaybookTask
from ..models.step_mutation import StepMutation


# ──────────────────────────────────────────────────────────────
# 1. KernelPhase（27 phase：17 原始 + 2 W4-T17/M-11 + 8 SD_05 W0）
# ──────────────────────────────────────────────────────────────
class KernelPhase(str, Enum):  # noqa: UP042  # str+Enum 是既有公開 API，改 StrEnum 屬行為面重構、不在 lint 射程
    PRE_RUN = "pre_run"
    POST_RUN = "post_run"
    PRE_STEP = "pre_step"
    POST_STEP = "post_step"
    PRE_ATTEMPT = "pre_attempt"
    POST_ATTEMPT = "post_attempt"
    PRE_EVALUATE = "pre_evaluate"
    POST_EVALUATE = "post_evaluate"
    PRE_CORRECTION = "pre_correction"
    POST_CORRECTION = "post_correction"
    ON_TOKEN_USAGE = "on_token_usage"
    ON_FAILURE = "on_failure"
    ON_SUCCESS = "on_success"
    ON_ESCALATION = "on_escalation"
    ON_EVOLUTION = "on_evolution"
    ON_INTERRUPT = "on_interrupt"
    ON_STATE_TRANSITION = "on_state_transition"
    # W4-T17 / M-11：CheckpointPlugin <-> GotoCounterPlugin 解耦事件
    #   ON_CHECKPOINT_RESTORE      CheckpointPlugin 載入 checkpoint 後廣播；
    #                              GotoCounterPlugin 訂閱以恢復 goto/inject/skip/evolve counters
    #   ON_CHECKPOINT_SAVE_REQUEST CheckpointPlugin save 前廣播；
    #                              GotoCounterPlugin 訂閱回傳當前 counter snapshot
    ON_CHECKPOINT_RESTORE = "on_checkpoint_restore"
    ON_CHECKPOINT_SAVE_REQUEST = "on_checkpoint_save_request"
    # SD_Improving_05 W0 T0-1：新增 8 phase（支撐 W1~W4 mixin 下沉）
    PRE_COMPACT = "pre_compact"
    POST_COMPACT = "post_compact"
    ON_PERSISTENCE_REQUEST = "on_persistence_request"
    ON_ESCALATION_DUMP_REQUEST = "on_escalation_dump_request"
    ON_EVOLUTION_PROPOSE = "on_evolution_propose"
    ON_EVOLUTION_APPLY = "on_evolution_apply"
    ON_AUTO_RESUME_WAKE = "on_auto_resume_wake"
    ON_PROMPT_PREPARED = "on_prompt_prepared"
    # SD_Improving_06 W1 T1-4：OrchestrationCoordinator 6 phase 序
    # 對應 ADR-SD06-001 §2 Layer 1.5 邊界圖 + §6.1 phase 序保證
    #   BEFORE_DECIDE → DECIDE → BEFORE_EXEC → EXEC → ON_EVENT → AFTER_EXEC
    # 違反序時 Coordinator raise PhaseOrderViolation（≥ 12 case 覆蓋；ADR §7.4 QA 條件 1）
    BEFORE_DECIDE = "before_decide"
    DECIDE = "decide"
    BEFORE_EXEC = "before_exec"
    EXEC = "exec"
    ON_EVENT = "on_event"
    AFTER_EXEC = "after_exec"
    # ADR-SD06-001 §6.4：send_interrupt 走 EventBus，由 ExecutorAdapter 訂閱
    ON_INTERRUPT_REQUEST = "on_interrupt_request"


# ──────────────────────────────────────────────────────────────
# 2. Per-phase TypedDict payload schemas（QA 必要修改 #2）
# ──────────────────────────────────────────────────────────────
# 🔴 R85（訴求 2）：此處原有 4 支 TypedDict（TokenUsagePayload／FailurePayload／
# CorrectionPayload／EvolutionPayload），實測**全庫零消費者**（對照組同法量測：
# HookContext 365 refs、KernelPhase 683 refs ⇒ 取數管道本身會命中，0 是真的 0）。
# 它們既沒有被任何 annotation 引用，就不會被任何型別檢查器比對 ⇒ 一旦真實 payload
# 改形狀，這四支不會有任何東西轉紅，只是靜靜地變成假的文件。「沒人看的規格會腐化成
# 假話」正是本 repo 反覆判過的形態，故整段移除而非留著當註解；真實 payload 形狀的
# 唯一真相源是各 phase 的 emit 站點與訂閱它的 plugin。
# 連帶：本檔 TypedDict 的最後一個使用者也隨之消失，typing import 一併收斂。


# ──────────────────────────────────────────────────────────────
# 3. HookContext（不可變執行上下文）
# ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class HookContext:
    """所有 hook 共用的執行上下文，frozen 避免互改。"""
    phase: KernelPhase
    playbook: Playbook
    task: PlaybookTask | None = None
    step_idx: int | None = None
    attempt: int | None = None
    payload: dict = field(default_factory=dict)


# ──────────────────────────────────────────────────────────────
# 4. IHookResult — 10 個獨立 Protocol（ISP 拆分；4 原始 + 6 SD_05 W0）
# ──────────────────────────────────────────────────────────────
@runtime_checkable
class IHookResult(Protocol):
    """所有 hook result 的標記介面。"""
    contributor: str


@dataclass(frozen=True)
class VetoResult:
    """中止當前 phase（如 PreRunValidator block）。"""
    contributor: str
    reason: str


@dataclass(frozen=True)
class PromptInjectionResult:
    """注入 prompt prefix（global_goal / cross_step_hint）。"""
    contributor: str
    prefix: str
    position: str = "top"


@dataclass(frozen=True)
class ResourceRequest:
    """請求 Kernel 執行資源管理動作（compact / halt / escalation）。"""
    contributor: str
    request_compact: bool = False
    request_halt: bool = False
    request_escalation: bool = False
    reason: str = ""


@dataclass(frozen=True)
class MutationProposal:
    """提議步驟突變（MinimaxBrain / EvolutionPlugin）。"""
    contributor: str
    mutation: StepMutation
    rationale: str = ""


# SD_Improving_05 W0 T0-1：6 個新 IHookResult
@dataclass(frozen=True)
class ScheduleResumeResult:
    """AutoResumeService 排程恢復點（ISO 8601 timestamp）。"""
    contributor: str
    scheduled_at: str


@dataclass(frozen=True)
class CounterSnapshotResult:
    """GotoCounterPlugin 回應 ON_CHECKPOINT_SAVE_REQUEST 時的計數器快照。

    snapshot 結構：
      {"goto": {step_id: int}, "inject_before": {...}, "skip_to": {...},
       "step_evolution": {...}, "compact_failure": int}
    """
    contributor: str
    snapshot: dict


@dataclass(frozen=True)
class PersistenceResult:
    """CheckpointPlugin / PlaybookPersistencePlugin 持久化結果。

    SD_05 W0 三方審查 Arch-C2 / SD-C4：新增 `kind` 欄位以避免 ResolutionPolicy
    用 `path.endswith(".mutated.yaml")` 推導 evolved_playbook_path 的脆弱字串耦合。

    kind 合法值：
      - "checkpoint"        ：一般 checkpoint 寫入
      - "evolved_playbook"  ：Playbook 自演化後的新 YAML（觸發 evolved_playbook_path）
      - "escalation_dump"   ：ESCALATION 觸發的 dump（人工接管材料）
      - "interrupt"         ：ESC+F12 / TOKEN_HALT 中斷檢查點
    """
    contributor: str
    path: str
    succeeded: bool
    kind: str = "checkpoint"


@dataclass(frozen=True)
class MutationApplyResult:
    """MutationApplyService 套用後回饋（如是否清除 goal achievement summary）。"""
    contributor: str
    clear_goal_summary: bool = False


@dataclass(frozen=True)
class GoalValidationResult:
    """GoalSynthesisPlugin 驗證 global_goal 達成結果。"""
    contributor: str
    achieved: bool
    reasoning: str = ""


@dataclass(frozen=True)
class EscalationDumpedResult:
    """EvolutionPlugin / CheckpointPlugin 完成 escalation dump 後回傳路徑。"""
    contributor: str
    dump_path: str


# ──────────────────────────────────────────────────────────────
# 5. IHook Protocol（含 priority）
# ──────────────────────────────────────────────────────────────
class IHook(Protocol):
    """Plugin 必須實作的契約。"""
    def name(self) -> str: ...
    def priority(self) -> int: ...
    def subscribed_phases(self) -> list[KernelPhase]: ...
    def on_event(self, ctx: HookContext) -> Any | None: ...


# ──────────────────────────────────────────────────────────────
# 6. PHASE_RESULT_CONTRACT — 每 phase 限定可回傳的 result 型別
# ──────────────────────────────────────────────────────────────
PHASE_RESULT_CONTRACT: dict[KernelPhase, set[type]] = {
    KernelPhase.PRE_RUN:        {VetoResult},
    KernelPhase.PRE_STEP:       {VetoResult},
    KernelPhase.PRE_ATTEMPT:    {PromptInjectionResult, VetoResult},
    KernelPhase.POST_ATTEMPT:   {ResourceRequest, MutationProposal},
    KernelPhase.PRE_CORRECTION: {PromptInjectionResult},
    KernelPhase.POST_CORRECTION: {MutationProposal},
    KernelPhase.ON_TOKEN_USAGE: {ResourceRequest},
    # ON_ESCALATION 為事件廣播，dump 回報歸 ON_ESCALATION_DUMP_REQUEST（避免責任邊界模糊）
    KernelPhase.ON_ESCALATION:  {MutationProposal, ResourceRequest},
    # SD_Improving_05 W0 T0-1：補 7 條既有 phase 契約
    KernelPhase.ON_INTERRUPT:           {PersistenceResult},
    KernelPhase.ON_EVOLUTION:           {MutationProposal, PersistenceResult},
    KernelPhase.ON_FAILURE:             {ResourceRequest, MutationProposal},
    KernelPhase.ON_SUCCESS:             {GoalValidationResult},
    KernelPhase.ON_STATE_TRANSITION:    {PersistenceResult},
    KernelPhase.ON_CHECKPOINT_RESTORE:  {CounterSnapshotResult},
    KernelPhase.ON_CHECKPOINT_SAVE_REQUEST: {CounterSnapshotResult},
    # SD_Improving_05 W0 T0-1：8 個新 phase 對應契約
    KernelPhase.PRE_COMPACT:            {ResourceRequest, VetoResult},
    KernelPhase.POST_COMPACT:           {ResourceRequest},
    KernelPhase.ON_PERSISTENCE_REQUEST: {PersistenceResult},
    KernelPhase.ON_ESCALATION_DUMP_REQUEST: {EscalationDumpedResult, PersistenceResult},
    KernelPhase.ON_EVOLUTION_PROPOSE:   {MutationProposal},
    KernelPhase.ON_EVOLUTION_APPLY:     {MutationApplyResult, PersistenceResult},
    KernelPhase.ON_AUTO_RESUME_WAKE:    {ScheduleResumeResult},
    KernelPhase.ON_PROMPT_PREPARED:     {PromptInjectionResult},
    # SD_Improving_06 W1 T1-4：Coordinator 6 phase 契約
    # 設計原則：phase 序強制性由 Coordinator 內部狀態機保證；契約限定可回傳的 result 型別。
    #   BEFORE_DECIDE：Plugin 可 VetoResult（如 MAX_ACTIVE_RUNS_PER_GOAL guard）或注入 prompt prefix
    #   DECIDE       ：Brain 主導；Plugin 可回 MutationProposal（如建議 step_mutation）
    #   BEFORE_EXEC  ：Plugin 可 VetoResult（如 FastPathPlugin 短路）或 ResourceRequest（compact）
    #   EXEC         ：Executor 主導；不開放 Plugin 直接訂閱（避免 race）
    #   ON_EVENT     ：ExecutionEvent 廣播；Plugin 可 ResourceRequest（如 token_pct > 80 觸發 compact）  # noqa: E501
    #   AFTER_EXEC   ：Plugin 可 MutationProposal / ResourceRequest（如 escalation）
    KernelPhase.BEFORE_DECIDE:          {VetoResult, PromptInjectionResult},
    KernelPhase.DECIDE:                 {MutationProposal},
    KernelPhase.BEFORE_EXEC:            {VetoResult, ResourceRequest},
    KernelPhase.EXEC:                   set(),  # 不開放 Plugin 訂閱（Executor 獨占）
    KernelPhase.ON_EVENT:               {ResourceRequest},
    KernelPhase.AFTER_EXEC:             {MutationProposal, ResourceRequest},
    KernelPhase.ON_INTERRUPT_REQUEST:   set(),  # 廣播事件；ExecutorAdapter 訂閱但不回 result
}


# ──────────────────────────────────────────────────────────────
# 7. IResolutionPolicy（合併策略，DIP 抽出）
# ──────────────────────────────────────────────────────────────
class IResolutionPolicy(Protocol):
    """合併多個 IHookResult 的策略介面。"""
    def merge(
        self,
        phase: KernelPhase,
        results: list[Any],
    ) -> MergedResult:  # noqa: F821 - forward ref to event_bus.MergedResult
        ...


# ──────────────────────────────────────────────────────────────
# 8. IMutationStrategy（Layer 2 Domain Service 的 7 個 strategy）
# ──────────────────────────────────────────────────────────────
class IMutationStrategy(Protocol):
    """每種 StepMutationType 的處理 strategy。"""
    def kind(self) -> str: ...
    def can_handle(self, mutation: StepMutation) -> bool: ...
    def apply(
        self,
        mutation: StepMutation,
        playbook: Playbook,
        current_idx: int,
    ) -> bool:
        """回傳 True 代表成功套用；False 代表拒絕（保持 playbook 不變）。"""
        ...


# ──────────────────────────────────────────────────────────────
# 9. HookContractViolation — fail-fast 例外
# ──────────────────────────────────────────────────────────────
class HookContractViolation(Exception):
    """Plugin 在 phase X 回傳了不合法的 result 型別。"""
