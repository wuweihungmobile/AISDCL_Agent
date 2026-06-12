"""DefaultResolutionPolicy + MergedResult — 從 event_bus.py 抽出（SD_Improving_05 W0 SD-C2 / Arch-C1）。

對應 SD_Improving_01.md v1.1 §3.4.2，DIP 抽出。

職責：
  - MergedResult：多個 IHookResult 合併後的視圖（11 個欄位含 W0 擴 7）
  - DefaultResolutionPolicy：v1.1 預設合併策略（明文 6 條決定性規則 + SD_05 W0 6 個新 result）

抽檔原因：event_bus.py 因 W0 新增 trace_id / escalate / kind 路由 / 衝突偵測 / try-finally
邏輯後 LOC 達 246 > 200 budget；按 SD_05 §5 紅線 #4「LOC 超 250 必拆 package」精神
（EventBus 子預算為 200），DIP 抽出 policy 為合理拆法。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .hookspec import (
    CounterSnapshotResult,
    EscalationDumpedResult,
    GoalValidationResult,
    HookContractViolation,
    KernelPhase,
    MutationApplyResult,
    MutationProposal,
    PersistenceResult,
    PromptInjectionResult,
    ResourceRequest,
    ScheduleResumeResult,
    VetoResult,
)


@dataclass(frozen=True)
class MergedResult:
    veto: bool = False
    veto_reasons: list[str] = field(default_factory=list)
    accumulated_prefix: str = ""
    request_compact: bool = False
    request_halt: bool = False
    request_escalation: bool = False
    request_mutation: Optional[Any] = None
    contributors: list[str] = field(default_factory=list)
    # SD_Improving_05 W0 T0-1：擴 7 欄支撐 W3/W4 下沉
    scheduled_resume_at: Optional[str] = None
    evolved_playbook_path: Optional[str] = None
    evolution_metadata: dict = field(default_factory=dict)
    counter_diff: dict = field(default_factory=dict)
    persistence_paths: list[str] = field(default_factory=list)
    goal_achieved: Optional[bool] = None
    escalation_dump_path: Optional[str] = None


class DefaultResolutionPolicy:
    """v1.1 預設合併策略 + SD_05 W0 6 個新 result 處理。"""

    def merge(self, phase: KernelPhase, results: list[Any]) -> MergedResult:
        results = sorted(
            results,
            key=lambda r: (
                getattr(r, "_priority", 50),
                getattr(r, "_register_idx", 0),
            ),
        )

        veto = False
        veto_reasons: list[str] = []
        prefix_parts: list[str] = []
        request_compact = False
        request_halt = False
        request_escalation = False
        request_mutation: Optional[Any] = None
        contributors: list[str] = []
        scheduled_resume_at: Optional[str] = None
        counter_diff: dict = {}
        persistence_paths: list[str] = []
        goal_achieved: Optional[bool] = None
        escalation_dump_path: Optional[str] = None
        evolved_playbook_path: Optional[str] = None
        evolution_metadata: dict = {}

        for r in results:
            contributors.append(r.contributor)
            if isinstance(r, VetoResult):
                veto = True
                veto_reasons.append(f"[{r.contributor}] {r.reason}")
            elif isinstance(r, PromptInjectionResult):
                prefix_parts.append(r.prefix)
            elif isinstance(r, ResourceRequest):
                request_compact = request_compact or r.request_compact
                request_halt = request_halt or r.request_halt
                request_escalation = request_escalation or r.request_escalation
            elif isinstance(r, MutationProposal):
                if request_mutation is None:
                    request_mutation = r.mutation
            elif isinstance(r, ScheduleResumeResult):
                if scheduled_resume_at is None:
                    scheduled_resume_at = r.scheduled_at
            elif isinstance(r, CounterSnapshotResult):
                # SD_05 W0 Arch-M1 / SD-M6：同 key 不同值 fail-fast
                for k, v in r.snapshot.items():
                    if k in counter_diff and counter_diff[k] != v:
                        raise HookContractViolation(
                            f"CounterSnapshotResult key '{k}' 由 multi plugin emit 且值不一致："
                            f"existing={counter_diff[k]!r}, new={v!r}（contributor={r.contributor}）"
                        )
                    counter_diff[k] = v
            elif isinstance(r, PersistenceResult):
                if r.succeeded:
                    persistence_paths.append(r.path)
                # SD_05 W0 Arch-C2 / SD-C4：依 kind 而非字串嗅探
                if r.kind == "evolved_playbook" and evolved_playbook_path is None:
                    evolved_playbook_path = r.path
                elif r.kind == "escalation_dump" and escalation_dump_path is None:
                    escalation_dump_path = r.path
            elif isinstance(r, MutationApplyResult):
                evolution_metadata["clear_goal_summary"] = r.clear_goal_summary
            elif isinstance(r, GoalValidationResult):
                if goal_achieved is None:
                    goal_achieved = r.achieved
                if r.reasoning:
                    evolution_metadata.setdefault("goal_reasoning", r.reasoning)
            elif isinstance(r, EscalationDumpedResult):
                if escalation_dump_path is None:
                    escalation_dump_path = r.dump_path

        return MergedResult(
            veto=veto,
            veto_reasons=veto_reasons,
            accumulated_prefix="".join(prefix_parts),
            request_compact=request_compact,
            request_halt=request_halt,
            request_escalation=request_escalation,
            request_mutation=request_mutation,
            contributors=contributors,
            scheduled_resume_at=scheduled_resume_at,
            evolved_playbook_path=evolved_playbook_path,
            evolution_metadata=evolution_metadata,
            counter_diff=counter_diff,
            persistence_paths=persistence_paths,
            goal_achieved=goal_achieved,
            escalation_dump_path=escalation_dump_path,
        )
