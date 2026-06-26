"""Kernel 狀態機相關 dataclass（Phase 2）。

包含：
  - StepAction Enum：單一步驟結束後的動作（advance / goto / escalate / halt）
  - StepOutcome：_run_step 的回傳值
  - KernelResult：kernel.run() 的最終回傳
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StepAction(str, Enum):
    ADVANCE = "advance"
    GOTO = "goto"
    ESCALATE = "escalate"
    HALT = "halt"


@dataclass(frozen=True)
class StepOutcome:
    """單一步驟 attempt loop 結束後的決策。"""
    action: StepAction
    goto_idx: Optional[int] = None     # action == GOTO 時的目標
    failure_reason: str = ""
    attempts_used: int = 1
    # improving_78 W-78-1（DEF-78-001）：HALT on token 時帶回觀測到的 token 峰值，
    # 供 kernel.run 組裝 KernelResult.peak_token_pct → AutoResumeService 存 halt checkpoint。
    peak_token_pct: float = 0.0


@dataclass(frozen=True)
class KernelResult:
    """kernel.run() 的最終回傳。

    W0b 欄位（SD_Improving_03 §2.6 / W4-T15 m-10 docstring 補強）：
      ``workflow``                   WorkflowDetector 偵測結果字串（e.g. "aisdlc_sdd"
                                     / "aisdlc" / "auto"）。AutoResumeService 在
                                     映射 KernelResult → PlaybookResult 時保留此欄位，
                                     供 main.py CLI 顯示與後續 audit log 使用。
      ``scheduled_resume_at``        ISO 8601 排程繼續時間字串（含 UTC offset）。
                                     由 TokenGuardPlugin 在達到 halt_threshold_pct
                                     時透過 ResourceRequest 設定；None = 立即停止
                                     或無排程恢復。
      ``evolved_playbook_path``      EvolutionPlugin 完成 Playbook 自演化後產出的
                                     新 YAML 檔絕對路徑；None = 未發生演化。
                                     AutoResumeService 用此值決定下一輪迭代是否
                                     需重載 Playbook。
      ``evolution_fresh_required``   True = 演化後重啟須以 `--fresh` 模式執行
                                     （清空 checkpoint 從頭跑）；False = 可從現有
                                     checkpoint 續跑。由 PlaybookEvolver 決定
                                     （Gap-041 / Gap-048）。
    """
    success: bool
    completed_steps: int
    total_steps: int
    reason: str = ""
    step_log: list[str] = field(default_factory=list)
    completed_step_ids: list[str] = field(default_factory=list)
    halted: bool = False
    escalated: bool = False
    veto_reasons: list[str] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)
    # W0b（SD_03 §2.6）：PlaybookResult 映射缺漏欄位補入；詳見類別 docstring
    workflow: str = ""
    scheduled_resume_at: Optional[str] = None
    evolved_playbook_path: Optional[str] = None
    evolution_fresh_required: bool = False
    # improving_78 W-78-1（DEF-78-001）：token halt 時帶回 halt 發生的步驟索引與觀測峰值，
    # 供 AutoResumeService 以 path-aware 方式存 halt checkpoint（resume 點 = halt_step_idx）。
    halt_step_idx: Optional[int] = None
    peak_token_pct: float = 0.0

    @property
    def halt_for_token(self) -> bool:
        """SD_07 W4-T4-12：原 PlaybookResult.halt_for_token 欄位 backward compat alias。
        既有 caller 與 fixture snapshot key 仍可使用，最終目標統一為 .halted（SD_08 候選）。
        """
        return self.halted

    @classmethod
    def success_(
        cls, completed_steps: int, total_steps: int,
        step_log: list[str], completed_step_ids: list[str],
        contributors: list[str],
    ) -> "KernelResult":
        return cls(
            success=True,
            completed_steps=completed_steps,
            total_steps=total_steps,
            reason="success",
            step_log=step_log,
            completed_step_ids=completed_step_ids,
            contributors=contributors,
        )

    @classmethod
    def vetoed(cls, total_steps: int, reasons: list[str]) -> "KernelResult":
        return cls(
            success=False,
            completed_steps=0,
            total_steps=total_steps,
            reason="vetoed_at_pre_run",
            veto_reasons=reasons,
        )

    @classmethod
    def escalated_(
        cls, completed_steps: int, total_steps: int,
        step_log: list[str], completed_step_ids: list[str],
        reason: str,
    ) -> "KernelResult":
        return cls(
            success=False,
            completed_steps=completed_steps,
            total_steps=total_steps,
            reason=reason,
            step_log=step_log,
            completed_step_ids=completed_step_ids,
            escalated=True,
        )

    @classmethod
    def halted_(
        cls, completed_steps: int, total_steps: int,
        step_log: list[str], completed_step_ids: list[str],
        halt_step_idx: Optional[int] = None,
        peak_token_pct: float = 0.0,
    ) -> "KernelResult":
        return cls(
            success=False,
            completed_steps=completed_steps,
            total_steps=total_steps,
            reason="halted",
            step_log=step_log,
            completed_step_ids=completed_step_ids,
            halted=True,
            halt_step_idx=halt_step_idx,
            peak_token_pct=peak_token_pct,
        )
