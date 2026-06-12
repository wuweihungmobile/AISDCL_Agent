from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class GlobalInvariants(BaseModel):
    max_retries_per_step: int = 3
    auto_compact_interval: int = 5  # 0 = disabled


class ContextNegotiation(BaseModel):
    prompt: str = ""
    expected_keyword: str = ""


class PlaybookTask(BaseModel):
    step_id: str
    name: str
    prompt: str
    command: Optional[str] = None           # mock CLI 模式使用（非 Claude Code 模式）
    expected_output_regex: Optional[str] = None
    evaluator_command: Optional[str] = None
    max_retries: Optional[int] = None       # None → use global_invariants value
    maintain_context: bool = True           # True → pass --continue to claude
    evaluator_timeout_seconds: int = 120
    # SD_Improving_05 W2 (M-7)：per-step token_guard override
    # 為 dict（非 TokenGuardConfig）以保 YAML backward compat：既有 Playbook YAML
    # 不需修改即可載入；解析時由 TokenGuardPlugin.resolve_per_step_cfg() 套用至 global
    # 優先序：task.token_guard > AppConfig.token_guard
    # （W3 審查 SA-C3 已修正：原 docstring 寫三層含 playbook.global_invariants 層，
    #  但實作僅 task vs global 兩層；如需 playbook 層 override 屬 W3+ 範圍）
    # SD_05 W2 SD-M2 / Arch-M2：field validator 攔截 typo 欄位名（如 compact_threshold
    # 漏 _pct），避免 resolve_per_step_cfg 才報錯導致 Debug 困難
    token_guard: Optional[dict] = None

    @field_validator("token_guard")
    @classmethod
    def _validate_token_guard_keys(cls, v: Optional[dict]) -> Optional[dict]:
        """SD_05 W2 SD-M2：以 TokenGuardConfig 模型 fields 為白名單檢查 typo。"""
        if not v:
            return v
        from ..utils.config import TokenGuardConfig  # noqa: PLC0415（避免循環 import）
        allowed = set(TokenGuardConfig.model_fields.keys())
        unknown = set(v.keys()) - allowed
        if unknown:
            raise ValueError(
                f"PlaybookTask.token_guard 含未知欄位 {sorted(unknown)}；"
                f"合法欄位（TokenGuardConfig）：{sorted(allowed)}"
            )
        return v


class EvolutionMetadata(BaseModel):
    """Gap-024-A：演化版 Playbook 的元資料，重載後可恢復 mutation_log。"""
    generation: int = 0
    mutation_log: list[str] = Field(default_factory=list)
    escalated_step_ids: list[str] = Field(default_factory=list)


class Playbook(BaseModel):
    version: str = "1.0"
    project: str
    global_goal: Optional[str] = None      # Gap-011-A: 自治系統總目標，供 Minimax 決策對齊
    workflow_type: str = "auto"             # auto | aisdlc | aisdlc_sdd
    workflow_path: Optional[str] = None
    global_invariants: GlobalInvariants = Field(default_factory=GlobalInvariants)
    context_negotiation: Optional[ContextNegotiation] = None
    evolution_metadata: Optional[EvolutionMetadata] = None  # Gap-024-A: 演化元資料（重載後恢復 mutation_log）
    tasks: list[PlaybookTask]
