"""steps_orchestrator.py — _run_steps 拆解承接模組（SD_06 W2-T2-1 / T2-2 / W5-T5-1）。

對應：
  - SD_Improving_06.md v1.2 §4 W2 / §6.5 AC1-1（_runner_internals.py LOC W2 末 ≤ 80）
  - SD_Improving_06.md v1.2 §6.5 AC1-2（strategy 模組各 ≤ 250 LOC）
  - SD06_Execution_Guide.md W2 T2-1：ExecutionContext dataclass + steps_orchestrator skeleton
  - SD06_Execution_Guide.md W5 T5-1：ExecutionContext 擴張 run_id / goal_task_id
    / token_usage_history + to_dict() / from_dict() round-trip 支援（AC5-1）

階段：
  - T2-1（done）：ExecutionContext dataclass + StepsOrchestrator skeleton（≤ 250 LOC）
  - T2-2（next session）：_run_steps 840 行主體下沉（每搬 50 行立即跑全測）
  - W5-T5-1（current）：擴張 round-trip 能力以支援 dual_state drift 全欄比對

設計原則：
  - ExecutionContext 為純資料載體（dataclass），於 _run_steps 與 strategy 模組間傳遞
  - 不可序列化欄位（step_trackers / resume_checkpoint）標為 transient，to_dict 自動跳過
  - 不直接 import plugin 內部子模組（透過 runner.<plugin> 取公開 API）
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any, Optional

from ...infra.services.state_normalize import normalize_value

if TYPE_CHECKING:
    from ..models.playbook import Playbook, PlaybookTask
    from ..utils.checkpoint_manager import PlaybookCheckpoint
    from ..types import PlaybookResult  # noqa: F401  TYPE_CHECKING
    from .failure_tracker import FailureTracker
    from .workflow_detector import WorkflowType


_TRANSIENT_META = {"transient": True}


@dataclass
class ExecutionContext:
    """_run_steps 執行迴圈中所需的可變狀態快照（W2-T2-1 + W5-T5-1）。

    可序列化欄位用於 dual_state drift 全欄比對與 round-trip property test；
    transient 欄位（step_trackers / resume_checkpoint）於 to_dict() 自動跳過。
    """
    # ── 步驟進度 ─────────────────────────────────────
    step_idx: int = 0
    prev_step_idx: int = -1
    is_first_prompt: bool = True

    # ── 日誌與紀錄 ───────────────────────────────────
    step_log: list[str] = field(default_factory=list)
    mutation_log: list[str] = field(default_factory=list)

    # ── 跨步驟狀態 ───────────────────────────────────
    completed_step_ids: set[str] = field(default_factory=set)
    skip_completed_ids: set[str] = field(default_factory=set)

    # ── Goal Synthesis ──────────────────────────────
    goal_synthesis_injected: bool = False

    # ── 跨步驟污染警告（注入到下一個 prompt 前綴） ──
    cross_step_hint: Optional[str] = None

    # ── W5-T5-1 新增：三層任務模型對應 ID（run_id / goal_task_id）──
    run_id: Optional[str] = None
    goal_task_id: Optional[str] = None

    # ── W5-T5-1 新增：Token 使用率歷史（用於恢復後 /compact 決策）──
    token_usage_history: list[dict] = field(default_factory=list)

    # ── transient（不參與 round-trip / drift 比對） ─
    step_trackers: dict[str, "FailureTracker"] = field(
        default_factory=dict, metadata=_TRANSIENT_META,
    )
    resume_checkpoint: Optional["PlaybookCheckpoint"] = field(
        default=None, metadata=_TRANSIENT_META,
    )

    def advance_step(self) -> None:
        """前進至下一步（保留前一 step_idx 供 GOTO 偵測）。"""
        self.prev_step_idx = self.step_idx
        self.step_idx += 1

    def mark_completed(self, step_id: str) -> None:
        self.completed_step_ids.add(step_id)

    def is_already_completed(self, step_id: str) -> bool:
        return step_id in self.skip_completed_ids

    # ── W5-T5-1：round-trip 支援 ────────────────────
    def to_dict(self) -> dict[str, Any]:
        """正規化為純資料 dict（跳過 transient 欄位）。

        所有值經 normalize_value 處理（datetime → ISO UTC / UUID → str /
        Enum → value / set → 排序 list），供 drift_log 與 round-trip 使用。
        """
        out: dict[str, Any] = {}
        for f in fields(self):
            if f.metadata.get("transient"):
                continue
            out[f.name] = normalize_value(getattr(self, f.name))
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionContext":
        """從 to_dict() 結果還原。

        - completed_step_ids / skip_completed_ids 還原為 set
        - 其他欄位直接 mapping；transient 欄位採 default
        - 未知欄位忽略（前向相容）
        """
        known = {f.name for f in fields(cls) if not f.metadata.get("transient")}
        kwargs: dict[str, Any] = {}
        for k, v in (data or {}).items():
            if k not in known:
                continue
            if k in ("completed_step_ids", "skip_completed_ids"):
                kwargs[k] = set(v or [])
            elif k in ("step_log", "mutation_log", "token_usage_history"):
                kwargs[k] = list(v or [])
            else:
                kwargs[k] = v
        return cls(**kwargs)


class StepsOrchestrator:
    """_run_steps 拆解承接類別（SD_06 W2-T2-1 skeleton）。

    階段 1（T2-1 current）：僅 ExecutionContext + skeleton class，未開始下沉
    階段 2（T2-2 next session）：逐 50 行下沉 _run_steps 主體

    使用方式（T2-2 完成後）：
        ctx = ExecutionContext(...)
        orchestrator = StepsOrchestrator(runner=self, ctx=ctx)
        result = orchestrator.run(playbook, playbook_path, ...)
    """

    def __init__(self, runner, ctx: ExecutionContext):
        self._runner = runner
        self._ctx = ctx

    @property
    def ctx(self) -> ExecutionContext:
        return self._ctx

    @property
    def runner(self):
        return self._runner

    def initialize_counters_from_checkpoint(
        self, resume_checkpoint: Optional["PlaybookCheckpoint"],
    ) -> None:
        """SD_05 W1 Step-1：將 4 counter 從 checkpoint 還原至 GotoCounterPlugin。

        T2-2 將從 _run_steps 抽出至本方法；目前 _run_steps 仍直接呼叫
        `self._goto_counter_plugin.restore(...)`，本方法為下沉預留 API。
        """
        from ..models.counter_snapshot import CounterSnapshot
        if resume_checkpoint:
            self._runner._goto_counter_plugin.restore(CounterSnapshot(
                goto_counter=dict(resume_checkpoint.goto_counter),
                inject_before_counter=dict(resume_checkpoint.inject_before_counter),
                skip_to_counter=dict(resume_checkpoint.skip_to_counter),
                step_evolution_counter=dict(resume_checkpoint.step_evolution_counter),
            ))
        else:
            self._runner._goto_counter_plugin.restore(CounterSnapshot())

    def skip_if_already_completed(self, task: "PlaybookTask") -> bool:
        """若 task.step_id 已在 skip_completed_ids 中 → 標記 step_log 並回 True。

        T2-2 將從 _run_steps 抽出對應分支至本方法。
        """
        if self._ctx.is_already_completed(task.step_id):
            self._ctx.step_log.append(
                f"[RESUMED] {task.step_id}（Gap-041：演化前已完成，跳過）"
            )
            return True
        return False


