from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class MinimaxConfig(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.minimax.chat/v1/text/chatcompletion_v2"
    model: str = "MiniMax-Text-01"
    timeout_seconds: int = 30
    enable_kernel_brain: bool = False
    # DEF-01-008：是否把 MinimaxBrainAdapter 注入 PlaybookKernel + SddGovernancePlugin。
    # 預設 False＝production 維持 brain=None（無 Minimax 逐步 correction、無 escalation 諮詢，
    # 零退化）。設 True 啟用後：kernel.decide_correction 生效（改寫 prompt + step mutation）
    # 且 Minimax API 故障將觸發 ESCALATION（見 docs/04_planning/AutoSDD_improving_03.md §2.1）
    # —— operator 須知悉行為差異。


class ClaudeConfig(BaseModel):
    command: str = "claude"
    extra_args: list[str] = Field(default_factory=lambda: ["--yes"])
    continue_flag: str = "--continue"   # 傳遞給 claude 以維持對話脈絡
    encoding: str = "utf-8"


class LoopConfig(BaseModel):
    max_iterations: int = 20
    completion_pattern: str = r"執行完畢[,，]\s*報告如下"
    auth_patterns: list[str] = Field(
        default_factory=lambda: [
            r"Do you want to proceed\?",
            r"\(y/n\)",
            r"Press Enter to continue",
            r"Allow this action\?",
        ]
    )
    auth_response: str = "y\n"
    poll_interval_seconds: float = 0.2


class PlaybookConfig(BaseModel):
    step_timeout_seconds: int = 600        # 每個步驟的最大等待時間
    evaluator_timeout_seconds: int = 120   # evaluator_command 的最大執行時間
    global_goal_anchor_chars: int = Field(default=400, ge=100, le=1000)
    # Gap-013-H：/compact MEMORY ANCHOR 中 [GLOBAL_GOAL] 最大字元數（100~1000，預設 400）
    max_evolutions: int = Field(default=3, ge=1, le=10)
    # Gap-020：自動演化最大次數（1~10，預設 3）
    require_evolution_signoff: bool = False
    # DEF-13-004（L5 signoff 守界）：是否在自動重載演化版 Playbook 前要求人工 signoff。
    # 預設 False＝維持 Gap-012-D Level 5 自動重載（零退化）。設 True 後，每次演化重載前
    # 須經注入的 evolution_approver 核可（回傳 True）才放行；approver 缺失或拒絕 → fail-closed
    # 停機不重載並留審計痕（對齊 goal_decomposer signoff 硬閘 + MinimaxConfig.enable_kernel_brain
    # flag-gate 雙前例）。
    enable_rtm_feedback: bool = False
    # AutoSDD_improving_27 W1（A 軌 RTM 反饋迴圈）：是否在 ON_ESCALATION 演化提議時，
    # 讀回上次 RTM coverage 報告把 gap 摘要附 proposal.rationale 作**諮詢**輸入。
    # 預設 False＝EvolutionPlugin 行為與現況完全相同（零退化）。設 True 後僅增補
    # rationale 文字（不改 mutation 決策、不自動套用 RTM/SPEC）；演化仍走
    # require_evolution_signoff + max_evolutions 硬閘（對齊「RTM/SPEC-PATCH 絕不
    # 自動套用」紅線 + enable_kernel_brain flag-gate 前例）。
    goal_synthesis_enabled: bool = True
    # Gap-014：是否啟用 DONE 前的全局目標驗證（預設啟用）
    global_goal_brief_chars: int = Field(default=150, ge=50, le=500)
    # Gap-015：非首個步驟的精簡 global_goal 字元數（50~500，預設 150）
    conditional_evaluator_timeout_seconds: int = 5
    # Gap-038：CONDITIONAL 突變的 condition_evaluator 執行超時秒數（預設 5 秒）
    max_goto_per_step: int = 3
    # Gap-049：GOTO_STEP 每個目標步驟的最大跳轉次數（預設 3，可配置以支援複雜 TDD 場景）
    enable_translation_auto_propose: bool = True
    # AutoSDD_improving_60 W-60-4（A 軌 A→L5 轉譯策略元學習活體化）：是否於 POST_RUN
    # 自跨 session RTM coverage history 元學習出「轉譯改進候選」並自動提議（proposed）。
    # 預設 True＝**活體**（鏡像 B 軌 SLV 自動提議 default-ON；env
    # AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE=0/false/no/off opt-out 還原零退化）。
    # 🔴 紅線：proposals 純諮詢供人工 review，絕不自動改 SddToPlaybookAdapter 轉譯行為
    # （apply=人工 signoff 守界，對齊 RTM/SPEC-PATCH「絕不自動套用」）。非 SDD playbook
    # 全程 no-op。
    translation_max_proposals_per_run: int = Field(default=3, ge=0, le=20)
    # 每次 POST_RUN 最多新提議數（有界硬閘，0~20，預設 3；超限截斷不重試）。
    translation_min_weak_runs: int = Field(default=2, ge=1, le=20)
    # AutoSDD_improving_61（A→L5 加固）：第二信號 weak_regex 的提議門檻——同一 AT
    # 跨 session 轉譯為 weak_regex 達此 run 數即提議（與 min_failing_runs 獨立降噪，
    # 預設 2；1~20）。weak_regex＝Gherkin 無法編出強斷言而 fallback，反映轉譯保真度
    # 弱點，與「執行失敗」正交。提議仍恆 proposed（apply=人工 signoff，不變）。


class TokenGuardConfig(BaseModel):
    """Token / Context 用量保護設定。

    SD_06 W5-T5-12 加強 invariants：
      - halt_threshold_pct 必須 > compact_threshold_pct（既有 M-3/X-3）
      - resume_delay_minutes ≥ 0（避免負延遲）
      - max_auto_resumes ≥ 1（避免 0 次自動恢復產生 dead config）
    """
    enabled: bool = True
    # 觸發 /compact 的 context 使用百分比門檻（應低於 halt_threshold_pct）
    compact_threshold_pct: float = Field(default=80.0, ge=0.0, le=100.0)
    # 觸發儲存檢查點並暫停的 context 使用百分比門檻
    halt_threshold_pct: float = Field(default=90.0, ge=0.0, le=100.0)
    # 儲存檢查點後等待多少分鐘再自動繼續（0 = 立即繼續）
    resume_delay_minutes: int = Field(default=30, ge=0, le=1440)
    # True = 等待後自動繼續；False = 儲存檢查點後退出，讓人類決定何時重啟
    auto_resume: bool = True
    # 單次 playbook 執行中最多允許多少次自動恢復（防止無限迴圈）
    max_auto_resumes: int = Field(default=10, ge=1, le=100)
    # 從 Claude Code 輸出中偵測 context 使用率的 regex patterns
    # T7（SD_04 §3 / M-4）：補強 Claude Code 實際輸出格式涵蓋率
    #   - 原 4 個：%context、context%、N/M tokens、[CONTEXT_USAGE: N%]
    #   - 新 3 個：Context window N / M tokens、[STATS: usage N%]、Token usage: N tokens / max M
    context_patterns: list[str] = Field(
        default_factory=lambda: [
            r"(\d+(?:\.\d+)?)\s*%\s*(?:context|token)",
            r"(?:context|token)\w*[\s:]+(\d+(?:\.\d+)?)\s*%",
            r"(\d+)\s*/\s*(\d+)\s*tokens?",
            r"\[CONTEXT_USAGE:\s*(\d+(?:\.\d+)?)%\]",
            # 新增：Claude Code "Context window: N / M tokens" 格式
            r"Context window:\s*(\d+)\s*/\s*(\d+)\s*tokens",
            # 新增：[STATS: usage N%] 簡短標記
            r"\[STATS:\s*usage\s*(\d+(?:\.\d+)?)\s*%\]",
            # 新增：Token usage: N tokens / max M
            r"Token usage:\s*(\d+)\s*tokens\s*/\s*max\s*(\d+)",
        ]
    )

    @model_validator(mode="after")
    def halt_greater_than_compact(self) -> TokenGuardConfig:
        """M-3/X-3 防呆：halt 門檻必須高於 compact 門檻。"""
        if self.halt_threshold_pct <= self.compact_threshold_pct:
            raise ValueError(
                f"halt_threshold_pct({self.halt_threshold_pct}%) 必須 > "
                f"compact_threshold_pct({self.compact_threshold_pct}%)"
            )
        return self

    @field_validator("context_patterns")
    @classmethod
    def validate_regex(cls, v: list[str]) -> list[str]:
        """M-3 防呆：驗證每個 context_patterns 項目都是合法 regex。

        SA-4 修正：加上 re.IGNORECASE 旗標以與 token_tracker.build_patterns()
        的執行時編譯語意一致（避免「validator 通過但執行時行為不同」陷阱）。
        """
        for pattern in v:
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"無效 regex pattern '{pattern}': {exc}") from exc
        return v


class AlertLadderConfig(BaseModel):
    """F-B1 / ADR-AGT-004：漸進式告警階梯（WARNING→HINT→ESCALATE）。

    enabled 預設 on（2026-06-13 SCG-6 人工 waiver：koalawu 拍板提前轉正，免 7 天
    soak；deviation 紀錄見 AutoClaude_Improving_012.md §5 Phase 2 與 Phase3 NextAction）。
    可於 config 設 enabled=False 還原為與既有行為 byte-level 一致之控制流。
    """
    enabled: bool = True
    # F-B2：同 error signature 無改善連續 N 次即提前升級（穿透剩餘階梯）
    no_improve_escalate_threshold: int = Field(default=2, ge=1, le=5)


class NotificationConfig(BaseModel):
    enabled: bool = True
    webhook_url: str | None = None


class ToolInvocationConfig(BaseModel):
    """F-A2 / ADR-AGT-001：工具自主使用安全閘。

    預設 deny（凍結計畫 §4 風險緩解）：enabled=False 全拒；即使 True，allowlist
    為空仍全拒。allowlist 為 domain（web_search/http_request 比對 target 之 host）
    或通道名（send_message）。flag-off 時不發出任何外部 I/O，零行為變更。
    """
    enabled: bool = False
    allowlist: list[str] = Field(default_factory=list)


class StorageConfig(BaseModel):
    """Phase 6：State / Playbook backend 三段開關（SD_Improving_02.md v1.1 §2.8）。

    模式語義：
      - yaml_only（預設）：所有 Playbook 從 .yaml 載入；checkpoints 寫入 file backend。
                          無 PostgreSQL 依賴，零部署成本，與 v1.x 相容。
      - both：              Playbook 雙源讀（yaml 優先，DB 兜底）；checkpoints 雙寫（File + PG），
                          讀取以 File 為主、PG 為災難回復來源。適合 PG 上線首兩週的灰度驗證。
      - db_only：          Playbook 與 checkpoints 完全使用 PG backend；yaml 僅供匯入。
                          需 PostgreSQL 運行 + AUTOCLAUDE_DB_DSN 環境變數。
    """
    mode: Literal["yaml_only", "both", "db_only"] = "yaml_only"
    # PostgreSQL DSN（asyncpg 格式）；db_only / both 模式必填，可被 AUTOCLAUDE_DB_DSN 覆寫
    db_dsn: str | None = None
    # both 模式下，dual-write 失敗時是否阻斷主寫（False = 僅紀錄 warning，不影響使用者）
    dual_write_strict: bool = False
    # both 模式下，dual-read 不一致時的解決策略（"yaml_wins" / "db_wins" / "fail_loud"）
    dual_read_resolution: Literal["yaml_wins", "db_wins", "fail_loud"] = "yaml_wins"

    @model_validator(mode="after")
    def db_dsn_required_for_pg(self) -> StorageConfig:
        """X-3 防呆：db_only / both 模式必須提供 db_dsn 或環境變數。"""
        if self.mode in ("both", "db_only"):
            has_dsn = bool(self.db_dsn)
            has_env = bool(
                os.environ.get("AUTOCLAUDE_DB_DSN") or os.environ.get("AUTOCLAUDE_PG_DSN")
            )
            if not has_dsn and not has_env:
                raise ValueError(
                    f"storage.mode='{self.mode}' 需要 db_dsn 或環境變數 "
                    "AUTOCLAUDE_DB_DSN / AUTOCLAUDE_PG_DSN"
                )
        return self


class ExecutorConfig(BaseModel):
    """improving_68 W-68-3：執行器後端切換（PtyExecutor / SdkExecutorAdapter 並存）。

    backend="pty"（預設）→ 既有 PtyExecutor，零行為變更；現有測試與 production
    完全不受影響。backend="sdk" 為 opt-in，啟用以 Claude Agent SDK（JSON-over-stdio）
    驅動 Claude Code（需 `pip install autoclaude[sdk]`）。

    permission_mode：傳給 SDK 的權限模式（spike 證實安全值為 "default"，非 acceptEdits）。
    model：SDK 模型覆寫（None＝SDK 預設）。
    act-first 門檻（halt_pct / max_tokens / autocompact_threshold）由 adapter 於執行期
    從 SDK get_context_usage() 即時取得，無需在此設定（見 W-68-1 verify_act_first_ordering）。
    """
    backend: Literal["pty", "sdk"] = "pty"
    permission_mode: Literal[
        "default", "acceptEdits", "plan", "bypassPermissions", "dontAsk", "auto"
    ] = "default"
    model: str | None = None


class AppConfig(BaseModel):
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    minimax: MinimaxConfig = Field(default_factory=MinimaxConfig)
    loop: LoopConfig = Field(default_factory=LoopConfig)
    playbook: PlaybookConfig = Field(default_factory=PlaybookConfig)
    token_guard: TokenGuardConfig = Field(default_factory=TokenGuardConfig)
    alert_ladder: AlertLadderConfig = Field(default_factory=AlertLadderConfig)
    notification: NotificationConfig = Field(default_factory=NotificationConfig)
    tool_invocation: ToolInvocationConfig = Field(default_factory=ToolInvocationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    log_dir: str = "logs"
    backup_dir: str = "backups"
    scripts_dir: str = "scripts"
    checkpoint_dir: str = "checkpoints"
    # 工作流程自動偵測的搜尋路徑清單（依序嘗試，找到即回傳）
    # 空列表 → 僅以 CWD 作為最後備援
    workflow_search_paths: list[str] = Field(default_factory=list)
    # F-C1 / ADR-AGT-003 L3：啟動時 seed 至 IPreferenceStore（global scope）
    # 寫入為冪等 last-wins；config 為使用者期望值的 SSOT 來源之一
    preferences: dict[str, str] = Field(default_factory=dict)


def load_config(path: str = "config.yaml") -> AppConfig:
    p = Path(path)
    if not p.exists():
        return AppConfig()
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return AppConfig.model_validate(raw)
