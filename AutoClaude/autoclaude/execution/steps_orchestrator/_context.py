"""steps_orchestrator.py — _run_steps 執行狀態載體（SD_06 W2-T2-1 / W5-T5-1）。

對應：
  - SD_Improving_06.md v1.2 §4 W2 / §6.5 AC1-1（_runner_internals.py LOC W2 末 ≤ 80）
  - SD_Improving_06.md v1.2 §6.5 AC1-2（strategy 模組各 ≤ 250 LOC）
  - SD06_Execution_Guide.md W2 T2-1：ExecutionContext dataclass
  - SD06_Execution_Guide.md W5 T5-1：ExecutionContext 擴張 run_id / goal_task_id
    / token_usage_history + to_dict() / from_dict() round-trip 支援（AC5-1）

階段：
  - T2-1（done）：ExecutionContext dataclass
  - T2-2（done）：主體下沉為 _impl.py 的 run_steps_impl 自由函式；當初預留的
    StepsOrchestrator skeleton 類別始終零呼叫端，已移除（死碼）
  - W5-T5-1（current）：擴張 round-trip 能力以支援 dual_state drift 全欄比對

設計原則：
  - ExecutionContext 為純資料載體（dataclass），於 _run_steps 與 strategy 模組間傳遞
  - 不可序列化欄位（step_trackers / resume_checkpoint）標為 transient，to_dict 自動跳過
  - 不直接 import plugin 內部子模組（透過 runner.<plugin> 取公開 API）
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any

from ...infra.services.state_normalize import normalize_value

if TYPE_CHECKING:
    from ..types import PlaybookResult  # noqa: F401  TYPE_CHECKING
    from ..utils.checkpoint_manager import PlaybookCheckpoint
    from .failure_tracker import FailureTracker


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
    cross_step_hint: str | None = None

    # ── W5-T5-1 新增：三層任務模型對應 ID（run_id / goal_task_id）──
    run_id: str | None = None
    goal_task_id: str | None = None

    # ── W5-T5-1 新增：Token 使用率歷史（用於恢復後 /compact 決策）──
    token_usage_history: list[dict] = field(default_factory=list)

    # ── transient（不參與 round-trip / drift 比對） ─
    step_trackers: dict[str, FailureTracker] = field(
        default_factory=dict, metadata=_TRANSIENT_META,
    )
    resume_checkpoint: PlaybookCheckpoint | None = field(
        default=None, metadata=_TRANSIENT_META,
    )

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
    def from_dict(cls, data: dict[str, Any]) -> ExecutionContext:
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

