"""DualStateRepository — both 模式（File 主寫 + PG 影子寫）。

SD_Improving_02.md v1.1 §2.8 Phase 6 補充：
  - storage.mode = "both" 時使用，作為 PG 上線首兩週的灰度驗證
  - 寫入：File 為主來源（強保證），PG 為影子寫（best-effort）
  - 讀取：File 優先；File 缺失時降級至 PG（災難回復場景）
  - 一致性：dual_write_strict = True 時 PG 失敗會 raise；False 僅 warning

SD_06 W5-T5-3 / T5-10（新增）：
  - detect_drift() → DriftReport：以 dataclasses.asdict + state_normalize 全欄比對
  - dual_write_mode = "pg_first" / "file_first"（T5-10）；預設 file_first 保留 v1.x 行為
  - drift_observer hook：可注入 callable(report) 以寫入 drift_log 表（T5-20 PII filter）
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from ...utils.checkpoint_manager import PlaybookCheckpoint
from ..services.state_normalize import diff_normalized
from ._deprecation import warn_load_checkpoint_deprecated

logger = logging.getLogger("autoclaude.infra.repositories.dual")


@dataclass
class DriftReport:
    """SD_06 W5-T5-3：dual-state 全欄 drift 報告。

    對應規格：
      - SD_06 §6.5 AC5-2（full-field drift comparison）
      - alembic 0013_drift_log（持久化 schema）
      - PM #11 hybrid（W5-T5-20）：寫入 drift_log 前必過 PIIFilter
    """
    playbook_id: str
    source_left: str  # 'primary' / 'shadow' / 'file' / 'pg'
    source_right: str
    field_drift: dict[str, dict[str, Any]] = field(default_factory=dict)
    severity: str = "info"  # info / warn / critical
    detected_at: str | None = None
    run_id: str | None = None

    @property
    def has_drift(self) -> bool:
        return bool(self.field_drift)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def apply_pii_filter(self, pii_filter) -> DriftReport:
        """SD_06 W5-T5-20：寫入 drift_log 前必呼叫此方法。

        將 field_drift 內每個 left/right 值經 PIIFilter 處理；SECRET 欄位
        會 raise PIIFilterViolation 中斷寫入。
        """
        import json as _json
        filtered: dict[str, dict[str, Any]] = {}
        for path, side in self.field_drift.items():
            full_path = f"drift_log.field_drift.{path}"
            new_side: dict[str, Any] = {}
            for k, v in side.items():
                text = v if isinstance(v, str) else _json.dumps(v, ensure_ascii=False)
                new_side[k] = pii_filter.filter_text(
                    field_path=full_path, text=text,
                )
            filtered[path] = new_side
        return DriftReport(
            playbook_id=self.playbook_id,
            source_left=self.source_left,
            source_right=self.source_right,
            field_drift=filtered,
            severity=self.severity,
            detected_at=self.detected_at,
            run_id=self.run_id,
        )


class DualMetrics:
    """P1 #5：dual-write / shadow 統計計數器（SRE / Infra metrics hook）。"""

    def __init__(self):
        self.dual_write_success: int = 0
        self.dual_write_failure: int = 0
        self.shadow_drift_detected: int = 0
        self.shadow_load_failure: int = 0
        # T5-10：reconcile queue 計數（PG-first 模式 file 失敗時）
        self.reconcile_queued: int = 0

    def as_dict(self) -> dict:
        return {
            "dual_write_success": self.dual_write_success,
            "dual_write_failure": self.dual_write_failure,
            "shadow_drift_detected": self.shadow_drift_detected,
            "shadow_load_failure": self.shadow_load_failure,
            "reconcile_queued": self.reconcile_queued,
        }


class DualStateRepository:
    """同時操作 File 主後端與 PG 影子後端的 IStateRepository 包裝。

    SD_06 W5-T5-3 / T5-10 升級重點：
      - detect_drift(): dataclasses.asdict + state_normalize 全欄比對
      - dual_write_mode='pg_first': PG 主寫 + File 影子寫（PG 失敗 raise；File 失敗排入 reconcile）
      - drift_observer hook：fail_loud / 主動偵測時呼叫，供 audit log 寫入
    """

    def __init__(
        self,
        primary,                      # FileStateRepository
        shadow,                       # PgStateRepository
        *,
        strict: bool = False,
        read_resolution: str = "yaml_wins",  # yaml_wins / db_wins / fail_loud
        dual_write_mode: str = "file_first",  # T5-10：file_first（v1.x）/ pg_first
        drift_observer: Callable[[DriftReport], None] | None = None,
        reconcile_queue: list[tuple[str, PlaybookCheckpoint]] | None = None,
    ):
        self._primary = primary
        self._shadow = shadow
        self._strict = strict
        self._read_resolution = read_resolution
        self._dual_write_mode = dual_write_mode
        self._drift_observer = drift_observer
        # T5-10：reconcile queue 用於 PG-first 模式下 File 寫入失敗時延遲補寫
        self._reconcile_queue: list[tuple[str, PlaybookCheckpoint]] = (
            reconcile_queue if reconcile_queue is not None else []
        )
        self.metrics = DualMetrics()

    # ──────────────────────────────────────────────
    def state_bytes(self, playbook_id: str) -> int:
        """轉發給 File 主端：`both` 模式**真的**在本機磁碟留 state.json。

        🔴 本類別逐一手寫委派、沒有 `__getattr__` 萬用轉發 ⇒ 主端新增的公開方法**不會**
        自動出現在這裡。漏轉發的失效形態是靜默的：呼叫端的鴨子型別探測拿不到方法就退回
        0，於是 `both` 模式的空間預估恆少算一份 state.json ×（1＋保留份數）——那正是
        `DEF-200-264` 立案要修的病灶，只是換到這一層再犯一次（本輪 Architect 鏡實查發現）。
        """
        getter = getattr(self._primary, "state_bytes", None)
        return getter(playbook_id) if getter is not None else 0

    def save_checkpoint(self, playbook_id: str, checkpoint: PlaybookCheckpoint) -> None:
        if self._dual_write_mode == "pg_first":
            self._save_pg_first(playbook_id, checkpoint)
        else:
            self._save_file_first(playbook_id, checkpoint)

    def _save_file_first(self, playbook_id: str, checkpoint: PlaybookCheckpoint) -> None:
        """既有行為：File 主寫，PG 影子寫。"""
        self._primary.save_checkpoint(playbook_id, checkpoint)
        try:
            self._shadow.save_checkpoint(playbook_id, checkpoint)
            self.metrics.dual_write_success += 1
        except Exception as exc:
            self.metrics.dual_write_failure += 1
            logger.warning("DualStateRepository | shadow PG 寫入失敗（%s）: %s", playbook_id, exc)
            if self._strict:
                raise

    def _save_pg_first(self, playbook_id: str, checkpoint: PlaybookCheckpoint) -> None:
        """T5-10：PG 主寫，File 影子寫；File 失敗排入 reconcile queue。"""
        self._shadow.save_checkpoint(playbook_id, checkpoint)
        try:
            self._primary.save_checkpoint(playbook_id, checkpoint)
            self.metrics.dual_write_success += 1
        except Exception as exc:
            self.metrics.dual_write_failure += 1
            self._reconcile_queue.append((playbook_id, checkpoint))
            self.metrics.reconcile_queued += 1
            logger.warning(
                "DualStateRepository | file 寫入失敗排入 reconcile queue（%s）: %s",
                playbook_id, exc,
            )
            if self._strict:
                raise

    def load_checkpoint(self, playbook_id: str) -> PlaybookCheckpoint | None:
        """⚠️ Deprecated（SD_06 W5-T5-8）：請改用 load_latest_by_playbook。"""
        warn_load_checkpoint_deprecated()
        return self.load_latest_by_playbook(playbook_id)

    def load_latest_by_playbook(
        self, playbook_id: str,
    ) -> PlaybookCheckpoint | None:
        """SD_06 W5-T5-7：載入 playbook_id 最新 checkpoint，含 drift detection。

        對 primary backend 採新 API 優先；未實作時 fallback 至舊 load_checkpoint
        以維持 mock-based test backward compat（W5 過渡期）。
        """
        primary_cp = self._load_primary_latest(playbook_id)
        if self._read_resolution == "yaml_wins":
            return primary_cp or self._safe_shadow_load(playbook_id)
        if self._read_resolution == "db_wins":
            return self._safe_shadow_load(playbook_id) or primary_cp
        # fail_loud：兩端都讀，全欄比對；不一致則 raise + 通知 drift_observer
        shadow_cp = self._safe_shadow_load(playbook_id)
        if primary_cp and shadow_cp:
            report = self.detect_drift(playbook_id, primary_cp, shadow_cp)
            if report.has_drift:
                self.metrics.shadow_drift_detected += 1
                if self._drift_observer is not None:
                    try:
                        self._drift_observer(report)
                    except Exception as exc:  # pragma: no cover
                        logger.warning("drift_observer 失敗: %s", exc)
                raise RuntimeError(
                    f"DualStateRepository drift detected (playbook_id={playbook_id}): "
                    f"{list(report.field_drift.keys())}"
                )
        return primary_cp or shadow_cp

    def load_by_run_id(self, run_id: str) -> PlaybookCheckpoint | None:
        """SD_06 W5-T5-7：以 run_id 查詢 checkpoint。

        策略：primary 優先（File 遍歷），找不到再嘗試 shadow（PG indexed）。
        """
        if not run_id:
            return None
        cp = None
        if hasattr(self._primary, "load_by_run_id"):
            cp = self._primary.load_by_run_id(run_id)
        if cp is None and hasattr(self._shadow, "load_by_run_id"):
            try:
                cp = self._shadow.load_by_run_id(run_id)
            except Exception as exc:
                logger.warning(
                    "DualStateRepository | shadow load_by_run_id 失敗: %s", exc,
                )
        return cp

    def clear_checkpoint(self, playbook_id: str) -> None:
        self._primary.clear_checkpoint(playbook_id)
        try:
            self._shadow.clear_checkpoint(playbook_id)
        except Exception as exc:
            logger.warning("DualStateRepository | shadow PG clear 失敗: %s", exc)
            if self._strict:
                raise

    def schedule_resume(self, playbook_id: str, delay_minutes: int) -> datetime:
        # 主 backend 為權威；影子 backend best-effort 同步
        resume_at = self._primary.schedule_resume(playbook_id, delay_minutes)
        try:
            self._shadow.schedule_resume(playbook_id, delay_minutes)
        except Exception as exc:
            logger.warning("DualStateRepository | shadow schedule_resume 失敗: %s", exc)
        return resume_at

    # ──────────────────────────────────────────────
    # T5-3：全欄 drift 偵測（取代僅比對 step_idx 的舊行為）
    # ──────────────────────────────────────────────
    def detect_drift(
        self,
        playbook_id: str,
        left_cp: PlaybookCheckpoint,
        right_cp: PlaybookCheckpoint,
        *,
        source_left: str = "primary",
        source_right: str = "shadow",
    ) -> DriftReport:
        """以 dataclasses.asdict() 全欄比對兩個 checkpoint 並回傳 DriftReport。

        所有值經 state_normalize.diff_normalized() 處理，確保 datetime/UUID/Enum
        的等價比對不會偽 drift。
        """
        left_d = asdict(left_cp)
        right_d = asdict(right_cp)
        drift = diff_normalized(left_d, right_d)
        # severity 衡量：step_idx / total_steps / completed_step_ids 任一不同 → critical
        critical_fields = {"step_idx", "total_steps", "completed_step_ids"}
        severity = (
            "critical" if drift.keys() & critical_fields
            else ("warn" if drift else "info")
        )
        return DriftReport(
            playbook_id=playbook_id,
            source_left=source_left,
            source_right=source_right,
            field_drift=drift,
            severity=severity,
        )

    # ──────────────────────────────────────────────
    # T5-10：reconcile queue API
    # ──────────────────────────────────────────────
    @property
    def reconcile_queue(self) -> list[tuple[str, PlaybookCheckpoint]]:
        """T5-10：PG-first 模式下，File 寫入失敗的待補寫佇列。"""
        return self._reconcile_queue

    def drain_reconcile_queue(self) -> int:
        """嘗試將 reconcile queue 中的待補寫項目寫入 File；回傳成功數量。"""
        succeeded = 0
        remaining: list[tuple[str, PlaybookCheckpoint]] = []
        for pid, cp in self._reconcile_queue:
            try:
                self._primary.save_checkpoint(pid, cp)
                succeeded += 1
            except Exception as exc:
                logger.warning("reconcile | %s 補寫仍失敗: %s", pid, exc)
                remaining.append((pid, cp))
        self._reconcile_queue[:] = remaining
        return succeeded

    # ──────────────────────────────────────────────
    def _load_primary_latest(self, playbook_id: str) -> PlaybookCheckpoint | None:
        """W5 過渡：仍呼叫舊 load_checkpoint；三個 backend 已內部委派至
        load_latest_by_playbook，因此行為等價且維持 mock 相容。
        """
        return self._primary.load_checkpoint(playbook_id)

    def _safe_shadow_load(self, playbook_id: str) -> PlaybookCheckpoint | None:
        try:
            return self._shadow.load_checkpoint(playbook_id)
        except Exception as exc:
            self.metrics.shadow_load_failure += 1
            logger.warning("DualStateRepository | shadow PG 讀取失敗: %s", exc)
            return None
