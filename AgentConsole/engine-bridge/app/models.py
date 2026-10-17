"""請求／回應模型（照 Engine Bridge API 契約；契約原文見 AgentConsole/docs/02_architecture）。"""
from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

_NO_CONTROL_CHARS = re.compile(r"^[^\x00-\x1f\x7f]+$")


class RunStatus(StrEnum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATUSES = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})
#: 寫進 PG `execution_runs.status` 時只用 PRD 六態（CHECK 約束）：過渡態折回 RUNNING。
DB_STATUS = {
    RunStatus.INITIALIZING: "INITIALIZING",
    RunStatus.RUNNING: "RUNNING",
    RunStatus.PAUSING: "RUNNING",
    RunStatus.PAUSED: "PAUSED",
    RunStatus.CANCELLING: "RUNNING",
    RunStatus.COMPLETED: "COMPLETED",
    RunStatus.FAILED: "FAILED",
    RunStatus.CANCELLED: "CANCELLED",
}


class StrictModel(BaseModel):
    """未知欄位一律 422：引擎自己的 pydantic 預設會把打錯字的欄位靜默丟掉。"""

    model_config = ConfigDict(extra="forbid")


# ── playbook ──────────────────────────────────────────────────────────────────
class PlaybookTaskIn(StrictModel):
    step_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=500)
    prompt: str = Field(min_length=1)
    command: str | None = None
    expected_output_regex: str | None = None
    evaluator_command: str | None = None
    max_retries: int | None = Field(default=None, ge=0, le=20)
    goal_task_id: str | None = None
    # 以下四欄不在契約的最小集合裡，但 /sdd/compile 產出的 PlaybookTask 帶著它們，
    # 要能原樣餵回 POST /runs，所以一併接受（皆為引擎 PlaybookTask 的既有欄位）。
    maintain_context: bool = True
    evaluator_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    spec_digest: str | None = None
    weak_regex: bool = False
    token_guard: dict[str, Any] | None = None

    @field_validator("step_id")
    @classmethod
    def _step_id_is_printable(cls, v: str) -> str:
        if not _NO_CONTROL_CHARS.match(v):
            raise ValueError("step_id 不可含控制字元（會破壞引擎日誌的解析）")
        return v


class GlobalInvariantsIn(StrictModel):
    max_retries_per_step: int = Field(default=3, ge=0, le=20)
    auto_compact_interval: int = Field(default=5, ge=0, le=1000)


class PlaybookIn(StrictModel):
    version: str = "1.0"
    project: str = Field(min_length=1, max_length=200)
    global_goal: str | None = None
    workflow_type: Literal["auto"] = "auto"
    global_invariants: GlobalInvariantsIn = Field(default_factory=GlobalInvariantsIn)
    tasks: list[PlaybookTaskIn] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _unique_ids_and_engine_schema(self) -> PlaybookIn:
        ids = [t.step_id for t in self.tasks]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"step_id 重複：{dupes}")
        # 交給引擎自己的模型再驗一次（例如每步 token_guard 的欄位白名單），免得 run 開始才炸。
        from autoclaude.models.playbook import Playbook

        try:
            Playbook(**self.to_engine_dict())
        except ValidationError as exc:
            raise ValueError(f"引擎的 Playbook 模型拒絕：{exc.errors()[0]['msg']}") from exc
        return self

    def to_engine_dict(self, *, sdd_workflow_path: str | None = None) -> dict[str, Any]:
        """給引擎的 playbook。外部契約不開 `workflow_*`（`workflow_type` 只收 `auto`、
        `extra=forbid`）；有 `sdd` 區塊時由 Bridge **伺服端**傳入已驗證的規格路徑，覆寫成
        `aisdlc_sdd`＋`workflow_path`（D-115-06；ADR-XPLAT-016 §7.3）。"""
        data = self.model_dump(exclude_none=True)
        if sdd_workflow_path is not None:
            data["workflow_type"] = "aisdlc_sdd"
            data["workflow_path"] = sdd_workflow_path
        return data


class SddBlockIn(StrictModel):
    """`POST /autoclaude/runs` 的選填 `sdd` 區塊（與 `playbook` 同層；ADR-XPLAT-016 §7.3）。
    有這個區塊的請求要 `X-Bridge-Token`（它會觸發 FSM 寫入）；內容的清理在權杖檢查之後。"""

    spec_dir: str
    spec_file: str | None = None
    # 原名或淨化後的鍵皆可：Bridge 一律先過 `fsm_names.fsm_component`。
    fsm_project: str = Field(min_length=1, max_length=512)
    root: str | None = None
    approver: str | None = None


class RunCreateIn(StrictModel):
    run_id: UUID
    project: str = Field(min_length=1, max_length=200)
    execution_path: str
    playbook: PlaybookIn
    config_overrides: dict[str, Any] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)
    fresh: bool = False
    sdd: SddBlockIn | None = None


class RestoreIn(StrictModel):
    checkpoint_id: str
    # 選填：Bridge 重啟後請求層 env（可能含機密、從不落盤）遺失時由呼叫端重新提供。
    env: dict[str, str] = Field(default_factory=dict)


class ControlIn(StrictModel):
    """`:resume` 的選填 body（同 RestoreIn.env 的用途）。"""

    env: dict[str, str] = Field(default_factory=dict)


# ── decompose／sdd ────────────────────────────────────────────────────────────
class DecomposeIn(StrictModel):
    goal: str
    context: str = ""
    project: str = Field(default="decomposed-goal", min_length=1, max_length=200)
    max_steps: int = Field(default=24, ge=1)          # 超過 24 一律夾到 24（引擎：可下調不可上調）
    config_overrides: dict[str, Any] = Field(default_factory=dict)


class ApproveIn(StrictModel):
    approver: str = ""


class SddCompileIn(StrictModel):
    spec_dir: str
    # v1.5：同一目錄有多份 TCS 時指定要編譯的那份（相對 spec_dir；有給時 adapter 只讀這一份）。
    spec_file: str | None = None
    # v1.5：凍結閘只認 `FSM-STATE-<fsm_project>.yaml`（原名或淨化後的鍵皆可；省略＝不指定）。
    fsm_project: str | None = Field(default=None, max_length=512)


class SddFreezeIn(StrictModel):
    """`POST /sdd/fsm/{project}:freeze` 的 body（唯一的 FSM 寫入動詞；ADR-XPLAT-016 §4.3、§6.3①）。
    approver／reason 的內容規則（1～100／1～500 字、無控制字元、approver 不含 `;`）由路由在權杖檢
    查後套 `sdd_sync.clean_*`，違反＝422 `sdd_invalid_argument`；這裡只管形狀。"""

    root: str
    stage: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{1,64}$")
    docs: list[str] = Field(min_length=1, max_length=20)
    approver: str
    reason: str
    # 核准人當時看到的摘要（相對 root 的 POSIX 路徑 → `sha256:<hex>`）：與現檔比對，不符＝409。
    expected_digests: dict[str, str] | None = None


# ── 回應 ──────────────────────────────────────────────────────────────────────
class RunCreatedOut(BaseModel):
    run_id: str
    status: str
    pid: int | None
    workspace: str
    bridge_instance: str
    # v1.5：放行但值得出聲的事（例如 `sdd_frozen_digest_absent`）。沒有 `sdd` 的請求恆為空陣列。
    warnings: list[dict[str, Any]] = Field(default_factory=list)


class StatusAckOut(BaseModel):
    status: str


class ResourcesOut(BaseModel):
    """引擎行程樹的資源取樣（契約 v1.3 §3.1.2）。不含 pid、命令列、環境變數。"""

    cpu_percent: float         # 整機正規化（總和 ÷ 邏輯核心數）、0.0～100.0、小數 1 位
    rss_bytes: int             # 行程樹各行程 RSS 的總和（共用頁重複計入，是上界估計）
    process_count: int         # 取樣當下仍存活（取樣成功）的行程數，含根
    sampled_at: str            # ISO-8601 含 offset（Bridge 一律 UTC `+00:00`）


class RunStateOut(BaseModel):
    run_id: str
    status: str
    pid: int | None
    started_at: str | None
    completed_at: str | None
    exit_code: int | None
    current_step: str | None
    completed_steps: int
    total_steps: int
    tokens_used: int
    last_event_seq: int
    # 契約以外的補充欄位（向後相容：只增不減）
    reason: str = ""
    project: str = ""
    execution_path: str = ""
    bridge_instance: str = ""
    current_step_number: int | None = None
    attempt: int = 0
    # v1.3（D-12）：引擎行程樹不存活（尚未 spawn、PAUSED、終態）、還沒有第一筆樣本、或最近一筆
    # 超過 15 秒沒更新時為 null。
    resources: ResourcesOut | None = None


class CheckpointOut(BaseModel):
    checkpoint_id: str
    name: str
    created_at: str
    step_idx: int
    step_id: str
    is_automatic: bool
