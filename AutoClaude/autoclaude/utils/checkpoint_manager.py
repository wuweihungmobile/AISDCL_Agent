"""
Playbook 執行檢查點管理器。

⚠️ Phase 5 起 deprecated（@deprecated v2.0）：
   請使用 autoclaude.infra.repositories.FileStateRepository（IStateRepository 後端）
   或 InMemoryStateRepository（測試夾具）。
   保留此 alias 以維持 PlaybookRunner 內部呼叫與既有測試耦合（193 處 runner._private_*）。

職責：
  - 在 token 達到限制時儲存目前進度（step_idx、已完成步驟日誌、token 狀態）
  - 下次啟動時自動讀取並從斷點繼續
  - 支援「排程繼續時間」：儲存 scheduled_resume_at，讓 PlaybookRunner 知道何時喚醒
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .logger import _sanitize_log_filename
from .resume_clock import seconds_until as resume_clock_seconds_until

logger = logging.getLogger("autoclaude.utils.checkpoint")

_CHECKPOINT_SUFFIX = ".checkpoint.json"


@dataclass
class PlaybookCheckpoint:
    playbook_path: str               # 原始 playbook YAML 絕對/相對路徑
    step_idx: int                    # 下次執行從哪個 step 開始（0-based）
    step_id: str                     # 對應的 step_id（方便人類閱讀）
    total_steps: int
    project: str = ""
    completed_step_log: list[str] = field(default_factory=list)
    peak_token_pct: float = 0.0      # 觸發儲存時的 token 使用百分比
    saved_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    scheduled_resume_at: str | None = None  # ISO 8601，None = 立即可繼續
    # Gap-007-A：跨 TOKEN_HALT / ESC+F12 的 FailureTracker 持久化
    failure_history: list[dict] = field(default_factory=list)  # 序列化的 AttemptRecord 列表
    active_step_attempt: int = 0                               # 中斷時的 attempt 編號
    last_correction_prompt: str = ""                           # 最後一次 Minimax 修正指令
    # Gap-041：演化後重啟時跳過的已完成步驟 ID 清單
    completed_step_ids: list[str] = field(default_factory=list)
    # Gap-042：跨 TOKEN_HALT 的突變計數器持久化（防止跨 Session 超出上限）
    goto_counter: dict = field(default_factory=dict)
    inject_before_counter: dict = field(default_factory=dict)
    skip_to_counter: dict = field(default_factory=dict)
    # Gap-048：per-step 演化次數追蹤（防止跨 TOKEN_HALT / ESC+F12 後超出上限）
    step_evolution_counter: dict = field(default_factory=dict)
    # SD_06 W5-T5-7：三層任務模型對應的 run_id（可由 PgStateRepository 寫回）
    #   - yaml_only / both 模式：可為 None（不依賴 PG）
    #   - db_only 模式：對應 playbook_runs.run_id（PgStateRepository._ensure_run_id 維護）
    run_id: str | None = None
    # SD_06 W5-T5-7：所屬 goal_task_id（三層任務模型；可為 None 表示舊 playbook）
    goal_task_id: str | None = None
    # AutoSDD_improving_01 §1.2（W5）：SDD 治理狀態（additive，比照 Gap-007-A 模式）。
    # dict 內 schema 由 SddGovernancePlugin 維護：
    #   { "scg_gate": "SCG-3", "fsm_state": "IMPLEMENTATION",
    #     "contract_violations": [{"step_id":..., "at_id":..., "ts":...}],
    #     "spec_digest": "sha256:..." }   # 規格凍結指紋，防 drift
    # 舊 checkpoint 反序列化 → default_factory 補空 dict，零遷移破壞。
    sdd_governance: dict = field(default_factory=dict)
    # F-B1/F-B2（ADR-AGT-004）：AlertLadder 階梯計數 + CorrectionVerifier streak。
    # 結構 {step_id: {"warning": int, "hint": int, "no_improve_streak": int}}。
    # additive：舊 checkpoint 反序列化 → default_factory 補空 dict，零遷移破壞。
    alert_ladder: dict = field(default_factory=dict)
    # 🔴 R100 P2-C（PRD §8-4 ②／§7 `checksum_sha256`）：磁碟完整性欄位。
    # 空字串＝**舊檔沒有這一欄**（legacy，驗不了；誠實劃界，不得當成「驗過了」）。
    # 為什麼需要它：`os.replace` 只保證「換名是原子的」，不保證**內容已落地**——
    # 斷電（正是本項要防的情境）時 rename 可能先落地而 page cache 未落地
    # ⇒ 得到一個「檔在、JSON 截斷」的 checkpoint。而截斷的 JSON 在修法前會被
    # `except Exception: return None` 吃掉，與「沒有 checkpoint」外觀完全相同。
    checksum_sha256: str = ""
    # R100 P2-C（PRD §6.2 R-6.2-1）：待整合佇列。**住既有結構、不新開一個檔**
    # （一份檔一個寫者，同 §4.5.6 R-4.5.6-3）。每一項 {"agent_id","branch","status"}，
    # status 的枚舉唯一定義在 execution/boot_self_check.py::QUEUE_STATUSES。
    integration_queue: list[dict] = field(default_factory=list)


CHECKSUM_FIELD = "checksum_sha256"


def checkpoint_digest(payload: dict) -> str:
    # 除 `checksum_sha256` 本欄之外的序列化內容的 SHA-256（PRD §7 逐字定義）。
    # `sort_keys=True`＝對欄位順序不敏感：dataclass 加欄位／json 重排都不該讓舊檔轉腐。
    body = {k: v for k, v in payload.items() if k != CHECKSUM_FIELD}
    blob = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class CheckpointManager:
    """
    ⚠️ Deprecated（v2.0 將移除）：請改用 FileStateRepository。

    W1b（SD_03 §3.1）：反向委派至 FileStateRepository。
    保留既有 API（save / load / clear / schedule_resume / checkpoint_path / exists /
    seconds_until_resume）以維持 Frozen Surface 相容性（193 處測試耦合）。

    啟用 DeprecationWarning：設定環境變數 AUTOCLAUDE_DEPRECATION_WARN=1。
    """

    def __init__(
        self,
        checkpoint_dir: str = "checkpoints",
        *,
        repository=None,
        id_resolver=None,
    ):
        """初始化 CheckpointManager。

        Args:
            checkpoint_dir: checkpoint 檔案存放目錄
            repository: 可選的 StateRepository 實例（預設 FileStateRepository）
            id_resolver: 可選的 callable(path: str) -> str 用於計算 playbook_id
                         T8（SD_04 §3 / M-2）：未提供時預設使用 Path.stem，
                         與舊行為相容；可注入 canonical_playbook_id 以在
                         不同 storage.mode 下取得對應 ID
        """
        import os  # noqa: E401
        import warnings
        if os.environ.get("AUTOCLAUDE_DEPRECATION_WARN") == "1":
            warnings.warn(
                "CheckpointManager is deprecated; use FileStateRepository directly.",
                DeprecationWarning,
                stacklevel=2,
            )
        self._dir = Path(checkpoint_dir)
        if repository is not None:
            self._repo = repository
        else:
            # 延遲 import 避免頂層循環依賴（file_state_repository → PlaybookCheckpoint）
            from ..infra.repositories.file_state_repository import (
                FileStateRepository,  # noqa: PLC0415
            )
            self._repo = FileStateRepository(checkpoint_dir)
        # T8 / Dev-6：可注入 ID 策略；未指定時委派至 canonical_playbook_id("yaml_only")
        # 作為單一真相來源（SSOT）。yaml_only 模式回傳 Path.stem，行為與舊版一致。
        if id_resolver is not None:
            self._id_resolver = id_resolver
        else:
            from ..infra.repositories.factory import canonical_playbook_id  # noqa: PLC0415
            self._id_resolver = lambda p: canonical_playbook_id(p, "yaml_only")

    def _to_id(self, playbook_path: str) -> str:
        """T8：改為 instance method 以支援注入式 id_resolver。"""
        return self._id_resolver(playbook_path)

    def checkpoint_path(self, playbook_path: str) -> Path:
        # DEF-101-390（R48）：與 save()/load()/clear() 委派的 FileStateRepository._path()
        # 同款淨化（SSOT _sanitize_log_filename），避免 checkpoint_path()/exists() 算出的
        # 檔名與實際寫入磁碟的檔名不一致（保留裝置名/路徑穿越字元場景會分歧）。
        sanitized_id = _sanitize_log_filename(self._to_id(playbook_path))
        return self._dir / f"{sanitized_id}{_CHECKPOINT_SUFFIX}"

    def exists(self, playbook_path: str) -> bool:
        return self.checkpoint_path(playbook_path).exists()

    def save(self, checkpoint: PlaybookCheckpoint, playbook_path: str) -> None:
        """符合 StateRepositoryPort 契約：回傳 None。"""
        self._repo.save_checkpoint(self._to_id(playbook_path), checkpoint)

    def load(self, playbook_path: str) -> PlaybookCheckpoint | None:
        return self._repo.load_checkpoint(self._to_id(playbook_path))

    def clear(self, playbook_path: str) -> None:
        self._repo.clear_checkpoint(self._to_id(playbook_path))

    def schedule_resume(
        self,
        checkpoint: PlaybookCheckpoint,
        delay_minutes: int,
    ) -> datetime:
        """
        設定 checkpoint.scheduled_resume_at 為 now + delay_minutes。

        Backward compat：直接 mutate 傳入的 checkpoint（呼叫端之後呼叫 save()）。
        """
        resume_at = datetime.now() + timedelta(minutes=delay_minutes)
        checkpoint.scheduled_resume_at = resume_at.isoformat(timespec="seconds")
        logger.info("排程繼續執行: %s", resume_at.strftime("%Y-%m-%d %H:%M:%S"))
        return resume_at

    # R81（HLM-S1-02）：委派 SSOT（見 utils/resume_clock.py）。此處原本自帶一份
    # 只算得了 naive 的複本——這是同一份邏輯的第三個家。
    @staticmethod
    def seconds_until_resume(checkpoint: PlaybookCheckpoint) -> float:
        """回傳距 scheduled_resume_at 的剩餘秒數；已過期或未設定則回傳 0.0。"""
        return resume_clock_seconds_until(checkpoint.scheduled_resume_at)
