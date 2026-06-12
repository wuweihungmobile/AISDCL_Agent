"""EmbeddingWriter — 三層任務寫入路徑 + embedding 接入（SD_Improving_06 W3-T3-20 + T3-21）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-3：寫入路徑三觸發點
      • create_goal_task
      • update_goal_task
      • complete_execution_item
  - SD_Improving_06.md §9.2 PM #9：embedding_status 三態（pending / ok / failed）
    + 背景 retry queue + 5 次告警通道（SLO）
  - SD_Improving_06.md §9.2 PM #11：PII 過濾器套用（W0 ENUM → W3 行為）

設計重點：
  - 同步介面（W3 階段 1）；DB writes 為「先寫業務列 (status=pending) → 嘗試 embed →
    成功則 UPDATE 三欄（embedding_v / model_id / status='ok'）」雙階段；
    embedder 失敗時保留業務列 + 寫 audit + 進入 retry queue（PM #9 最終一致）
  - DB 操作以 callable 注入（SqlExecutor.fetch_one / execute_returning），
    便於以 fake 實作驗證契約；正式環境由 PgStateRepository 或專屬 GoalTaskRepo 提供
  - 寫入前所有可入庫文字皆經 PII filter (T3-23) 過濾後再 embed
  - 告警通道：SLO observer 注入；連續 retry_attempts >= alert_after_attempts 時觸發
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ...core.ports.embedder import (
    EmbedderDimensionMismatchError,
    EmbedderUnavailableError,
)
from ...models.pii_classification import PIIClassification
from .pii_filter import PIIFilter, PIIFilterViolation

logger = logging.getLogger(__name__)


# 三態 SSOT（對應 alembic 0008 ck_kb_embedding_status / 0009 三表 CHECK）
EMBEDDING_STATUS_PENDING = "pending"
EMBEDDING_STATUS_OK = "ok"
EMBEDDING_STATUS_FAILED = "failed"


@dataclass
class EmbeddingWriteResult:
    """單次寫入結果摘要（caller 可記入 audit / drift_log）。"""
    row_id: str
    namespace: str  # goal_tasks / execution_items / knowledge_entries
    embedding_status: str
    embedding_model_id: Optional[str]
    embedding_attempts: int = 0
    alerted: bool = False
    detail: str = ""


@dataclass
class SLOAlert:
    """retry 連續失敗達門檻時的告警事件（供 PM #9 告警通道訂閱）。"""
    row_id: str
    namespace: str
    model_id: Optional[str]
    attempts: int
    last_error: str
    timestamp: float = field(default_factory=lambda: __import__("time").time())


class EmbeddingWriter:
    """三層任務 + KB 寫入路徑統一入口。

    Args:
        embedder: IEmbedder（推薦傳 DualEmbedderRouter，支援自動 fallback）
        sql_executor: 提供 ``execute(sql, params) -> Any`` / ``fetch_one(sql, params)`` 介面
        pii_filter: PII 過濾器；若 None 則以預設 default classification 建立
        alert_after_attempts: 連續 retry 失敗達此值即觸發 SLO Alert（PM #9 預設 5）
        alert_observer: Callable[[SLOAlert], None]；可注入到 notifier / log / event bus
        clock: time source（測試友善）
    """

    def __init__(
        self,
        *,
        embedder,
        sql_executor,
        pii_filter: Optional[PIIFilter] = None,
        alert_after_attempts: int = 5,
        alert_observer: Optional[Callable[[SLOAlert], None]] = None,
        clock: Callable[[], float] = None,
    ) -> None:
        self.embedder = embedder
        self.sql = sql_executor
        self.pii_filter = pii_filter or PIIFilter()
        self.alert_after_attempts = max(1, int(alert_after_attempts))
        self.alert_observer = alert_observer
        self._clock = clock or __import__("time").time

    # ── 三大寫入路徑 ─────────────────────────────────────────────

    def create_goal_task(
        self,
        *,
        goal_task_id: str,
        project_id: str,
        parent_id: Optional[str],
        title: str,
        description: str = "",
        depth: int = 1,
        priority: int = 3,
        config_snapshot: Optional[dict] = None,
    ) -> EmbeddingWriteResult:
        """寫入 goal_tasks + 同步 embedding（AC4-3 寫入觸發點 1/3）。"""
        clean_title = self._filter_text("goal_tasks.title", title, PIIClassification.NORMAL)
        clean_desc = self._filter_text("goal_tasks.description", description, PIIClassification.NORMAL)
        text_to_embed = f"{clean_title}\n{clean_desc}".strip()
        # 1. 先寫業務列（status=pending）
        self.sql.execute(
            """
            INSERT INTO goal_tasks
              (goal_task_id, project_id, parent_id, title, description,
               depth, priority, status, config_snapshot, embedding_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, 'pending')
            """,
            (
                goal_task_id, project_id, parent_id, clean_title, clean_desc,
                depth, priority,
                (config_snapshot or {}),
            ),
        )
        # 2. 嘗試 embed + 同步寫入
        return self._embed_and_update(
            namespace="goal_tasks",
            row_id=goal_task_id,
            text=text_to_embed,
            update_sql=(
                "UPDATE goal_tasks SET embedding_v=%s, embedding_model_id=%s, "
                "embedding_status='ok', embedding_attempts=embedding_attempts+1 "
                "WHERE goal_task_id=%s"
            ),
            failure_sql=(
                "UPDATE goal_tasks SET embedding_status='failed', "
                "embedding_attempts=embedding_attempts+1 WHERE goal_task_id=%s"
            ),
        )

    def update_goal_task(
        self,
        *,
        goal_task_id: str,
        new_title: Optional[str] = None,
        new_description: Optional[str] = None,
    ) -> EmbeddingWriteResult:
        """更新 goal_tasks 並重 embed（AC4-3 觸發點 2/3）。"""
        # 取當前文字 + 套用變更
        row = self.sql.fetch_one(
            "SELECT title, description FROM goal_tasks WHERE goal_task_id=%s",
            (goal_task_id,),
        )
        if not row:
            raise ValueError(f"goal_task_id={goal_task_id} 不存在")
        title = self._filter_text(
            "goal_tasks.title",
            new_title if new_title is not None else row["title"],
            PIIClassification.NORMAL,
        )
        desc = self._filter_text(
            "goal_tasks.description",
            new_description if new_description is not None else (row["description"] or ""),
            PIIClassification.NORMAL,
        )
        self.sql.execute(
            "UPDATE goal_tasks SET title=%s, description=%s, embedding_status='pending' "
            "WHERE goal_task_id=%s",
            (title, desc, goal_task_id),
        )
        return self._embed_and_update(
            namespace="goal_tasks",
            row_id=goal_task_id,
            text=f"{title}\n{desc}".strip(),
            update_sql=(
                "UPDATE goal_tasks SET embedding_v=%s, embedding_model_id=%s, "
                "embedding_status='ok', embedding_attempts=embedding_attempts+1 "
                "WHERE goal_task_id=%s"
            ),
            failure_sql=(
                "UPDATE goal_tasks SET embedding_status='failed', "
                "embedding_attempts=embedding_attempts+1 WHERE goal_task_id=%s"
            ),
        )

    def complete_execution_item(
        self,
        *,
        exec_id: str,
        result_summary: str,
        actual_minutes: Optional[int] = None,
    ) -> EmbeddingWriteResult:
        """完成 execution_items + 寫 embedding（AC4-3 觸發點 3/3）。"""
        clean = self._filter_text("execution_items.result", result_summary, PIIClassification.NORMAL)
        self.sql.execute(
            "UPDATE execution_items SET status='ok', actual_minutes=%s, "
            "result=%s, embedding_status='pending' WHERE exec_id=%s",
            (actual_minutes, {"summary": clean}, exec_id),
        )
        return self._embed_and_update(
            namespace="execution_items",
            row_id=exec_id,
            text=clean,
            update_sql=(
                "UPDATE execution_items SET embedding_v=%s, embedding_model_id=%s, "
                "embedding_status='ok', embedding_attempts=embedding_attempts+1 "
                "WHERE exec_id=%s"
            ),
            failure_sql=(
                "UPDATE execution_items SET embedding_status='failed', "
                "embedding_attempts=embedding_attempts+1 WHERE exec_id=%s"
            ),
        )

    # ── 內部：embed + UPDATE / 失敗 + retry queue ─────────────────

    def _embed_and_update(
        self,
        *,
        namespace: str,
        row_id: str,
        text: str,
        update_sql: str,
        failure_sql: str,
    ) -> EmbeddingWriteResult:
        try:
            vec = self.embedder.embed_one(text) if text else None
        except (EmbedderUnavailableError, EmbedderDimensionMismatchError, ValueError) as exc:
            return self._handle_failure(
                namespace=namespace,
                row_id=row_id,
                failure_sql=failure_sql,
                error=exc,
            )
        if not vec:
            # 空文字 → 留 pending（不算失敗，下次 update 觸發再 embed）
            return EmbeddingWriteResult(
                row_id=row_id,
                namespace=namespace,
                embedding_status=EMBEDDING_STATUS_PENDING,
                embedding_model_id=None,
                detail="empty text, postponed",
            )
        self.sql.execute(update_sql, (vec, self.embedder.model_id, row_id))
        return EmbeddingWriteResult(
            row_id=row_id,
            namespace=namespace,
            embedding_status=EMBEDDING_STATUS_OK,
            embedding_model_id=self.embedder.model_id,
            embedding_attempts=1,
        )

    def _handle_failure(
        self,
        *,
        namespace: str,
        row_id: str,
        failure_sql: str,
        error: Exception,
    ) -> EmbeddingWriteResult:
        self.sql.execute(failure_sql, (row_id,))
        # 讀取累積 attempts 觸發 SLO alert
        attempts_row = self.sql.fetch_one(
            f"SELECT embedding_attempts FROM {namespace} WHERE "
            + ("goal_task_id" if namespace == "goal_tasks" else
               "exec_id" if namespace == "execution_items" else
               "entry_id") + "=%s",
            (row_id,),
        )
        attempts = int((attempts_row or {}).get("embedding_attempts", 1))
        alerted = attempts >= self.alert_after_attempts
        if alerted and self.alert_observer:
            self.alert_observer(SLOAlert(
                row_id=row_id,
                namespace=namespace,
                model_id=getattr(self.embedder, "model_id", None),
                attempts=attempts,
                last_error=f"{type(error).__name__}: {error}",
            ))
        return EmbeddingWriteResult(
            row_id=row_id,
            namespace=namespace,
            embedding_status=EMBEDDING_STATUS_FAILED,
            embedding_model_id=None,
            embedding_attempts=attempts,
            alerted=alerted,
            detail=f"{type(error).__name__}: {error}",
        )

    # ── PII 過濾 ────────────────────────────────────────────────

    def _filter_text(
        self,
        field_path: str,
        text: str,
        default_class: PIIClassification,
    ) -> str:
        if not text:
            return text
        try:
            return self.pii_filter.filter_text(
                field_path=field_path,
                text=text,
                classification=default_class,
            )
        except PIIFilterViolation:
            logger.error("PII filter blocked write at %s", field_path)
            raise
