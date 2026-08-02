from __future__ import annotations

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
    command: str | None = None           # mock CLI 模式使用（非 Claude Code 模式）
    expected_output_regex: str | None = None
    evaluator_command: str | None = None
    max_retries: int | None = None       # None → use global_invariants value
    maintain_context: bool = True           # True → pass --continue to claude
    evaluator_timeout_seconds: int = 120
    # AutoSDD_improving_56 W-56-2（DEF-56-001）：SDD 規格溯源指紋（完整 "sha256:..."）。
    # A 軌正向橋接 SddToPlaybookAdapter.compile_tasks 填入 spec.digest（權威全值），
    # 供逆向橋接 RtmWritebackPlugin 以結構化欄消費（取代脆弱的 prompt 正則反解 +
    # 8 字元截斷）。Optional 預設 None → YAML/checkpoint 向後相容；非 SDD task 留 None。
    spec_digest: str | None = None
    # AutoSDD_improving_94 W-94-1：三層任務模型分組鍵。A 軌 PRD→playbook 橋接時，
    # tools/three_tier_to_playbook.py 攤平 three_tier_schema.Project（專案→目標→任務）
    # 為扁平 tasks[] 時，每 task 填入其所屬 GoalTask.goal_task_id，使攤平後仍能標記
    # 「此任務屬哪個目標」，並與既有 PlaybookCheckpoint.goal_task_id（SD_06 W5）/
    # GoalProgressLedger（鍵 goal_task_id）跨 run 進度彙總對齊。Optional 預設 None →
    # YAML/checkpoint 向後相容；非三層來源 / 扁平 playbook 留 None（runner 不消費此欄）。
    goal_task_id: str | None = None
    # SD_Improving_05 W2 (M-7)：per-step token_guard override
    # 為 dict（非 TokenGuardConfig）以保 YAML backward compat：既有 Playbook YAML
    # 不需修改即可載入；解析時由 TokenGuardPlugin.resolve_per_step_cfg() 套用至 global
    # AutoSDD_improving_61 W-61-1：weak_regex 轉譯保真度旗標（第二元學習信號）。
    # 沿用 spec_digest 先例：A 軌正向橋接 SddToPlaybookAdapter.compile_tasks 填入
    # SpecContract.weak_regex（Gherkin 無法編出強斷言 regex 而 fallback 標記），供逆向
    # 橋接 PlaybookToRtmAdapter 收集為 RtmCoverageReport.weak_regex_at_ids，餵入轉譯
    # 元學習（select_proposals）作與「執行失敗」正交的第二信號。預設 False → YAML/
    # checkpoint 向後相容；非 SDD / 強 regex task 留 False。
    weak_regex: bool = False
    # 優先序：task.token_guard > AppConfig.token_guard
    # （W3 審查 SA-C3 已修正：原 docstring 寫三層含 playbook.global_invariants 層，
    #  但實作僅 task vs global 兩層；如需 playbook 層 override 屬 W3+ 範圍）
    # SD_05 W2 SD-M2 / Arch-M2：field validator 攔截 typo 欄位名（如 compact_threshold
    # 漏 _pct），避免 resolve_per_step_cfg 才報錯導致 Debug 困難
    token_guard: dict | None = None

    @field_validator("token_guard")
    @classmethod
    def _validate_token_guard_keys(cls, v: dict | None) -> dict | None:
        """SD_05 W2 SD-M2：以 TokenGuardConfig 模型 fields 為白名單檢查 typo。"""
        if not v:
            return v
        from ..utils.config import TokenGuardConfig  # noqa: PLC0415  (R69: 避免循環 import)
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
    global_goal: str | None = None      # Gap-011-A: 自治系統總目標，供 Minimax 決策對齊
    workflow_type: str = "auto"             # auto | aisdlc | aisdlc_sdd
    workflow_path: str | None = None
    global_invariants: GlobalInvariants = Field(default_factory=GlobalInvariants)
    context_negotiation: ContextNegotiation | None = None
    evolution_metadata: EvolutionMetadata | None = None  # Gap-024-A: 演化元資料（重載後恢復 mutation_log）  # noqa: E501
    tasks: list[PlaybookTask]
