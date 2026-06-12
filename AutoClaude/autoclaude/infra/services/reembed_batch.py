"""ReEmbedBatchJob — 背景重 embed 作業（SD_Improving_06 W3-T3-22）。

對應規格：
  - SD_Improving_06.md §9.2 PM #10：再 embed 採「背景 batch + 7 天 SLA」
  - alembic 0008 idx_kb_embedding_status partial index（WHERE != 'ok'）
  - 同樣 partial index 在 0009 goal_tasks / execution_items 三表皆建立

掃描策略：
  - 三表（knowledge_entries / goal_tasks / execution_items）逐一執行
  - WHERE embedding_status IN ('pending', 'failed')
    AND (updated_at IS NULL OR updated_at <= now() - INTERVAL '__SLA__')
    -> 預設 SLA = 7 天
  - LIMIT batch_size（預設 200），用 LIMIT + OFFSET 分頁
  - 每筆 attempts++；達 alert_after_attempts 觸發 SLO（與 EmbeddingWriter 同 observer）

呼叫端：tools/reembed_worker.py（W4+）或單元測試。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from ...core.ports.embedder import EmbedderError
from .embedding_writer import SLOAlert

logger = logging.getLogger(__name__)


NAMESPACE_TABLES: dict[str, tuple[str, str]] = {
    "knowledge_entries": ("entry_id", "content"),
    "goal_tasks":        ("goal_task_id", "title || E'\\n' || COALESCE(description, '')"),
    "execution_items":   ("exec_id", "COALESCE(result->>'summary', action)"),
}


@dataclass
class ReEmbedReport:
    """單次掃描的彙整結果（供 CLI / 監控顯示）。"""
    namespace: str
    scanned: int = 0
    succeeded: int = 0
    failed: int = 0
    alerted: int = 0


class ReEmbedBatchJob:
    """掃描 embedding_status != 'ok' 的列並重新 embed。"""

    def __init__(
        self,
        *,
        embedder,
        sql_executor,
        sla_days: int = 7,
        batch_size: int = 200,
        alert_after_attempts: int = 5,
        alert_observer: Optional[Callable[[SLOAlert], None]] = None,
    ) -> None:
        self.embedder = embedder
        self.sql = sql_executor
        self.sla_days = max(1, int(sla_days))
        self.batch_size = max(1, int(batch_size))
        self.alert_after_attempts = max(1, int(alert_after_attempts))
        self.alert_observer = alert_observer

    def run_once(self, namespace: str) -> ReEmbedReport:
        if namespace not in NAMESPACE_TABLES:
            raise ValueError(f"unsupported namespace: {namespace}")
        pk_col, text_expr = NAMESPACE_TABLES[namespace]
        report = ReEmbedReport(namespace=namespace)
        rows = self.sql.fetch_all(
            f"""
            SELECT {pk_col} AS row_id, {text_expr} AS payload_text, embedding_attempts
            FROM {namespace}
            WHERE embedding_status IN ('pending', 'failed')
              AND (updated_at IS NULL OR updated_at <= now() - INTERVAL '{self.sla_days} days')
            ORDER BY embedding_attempts ASC, updated_at ASC NULLS FIRST
            LIMIT %s
            """,
            (self.batch_size,),
        )
        for row in rows or []:
            report.scanned += 1
            row_id = row["row_id"]
            text = row["payload_text"] or ""
            attempts = int(row["embedding_attempts"] or 0) + 1
            if not text.strip():
                self.sql.execute(
                    f"UPDATE {namespace} SET embedding_attempts=%s WHERE {pk_col}=%s",
                    (attempts, row_id),
                )
                continue
            try:
                vec = self.embedder.embed_one(text)
            except (EmbedderError, ValueError) as exc:
                report.failed += 1
                self.sql.execute(
                    f"UPDATE {namespace} SET embedding_status='failed', "
                    f"embedding_attempts=%s WHERE {pk_col}=%s",
                    (attempts, row_id),
                )
                if attempts >= self.alert_after_attempts:
                    report.alerted += 1
                    if self.alert_observer:
                        self.alert_observer(SLOAlert(
                            row_id=str(row_id),
                            namespace=namespace,
                            model_id=getattr(self.embedder, "model_id", None),
                            attempts=attempts,
                            last_error=f"{type(exc).__name__}: {exc}",
                        ))
                continue
            self.sql.execute(
                f"UPDATE {namespace} SET embedding_v=%s, embedding_model_id=%s, "
                f"embedding_status='ok', embedding_attempts=%s WHERE {pk_col}=%s",
                (vec, self.embedder.model_id, attempts, row_id),
            )
            report.succeeded += 1
        logger.info(
            "ReEmbedBatchJob namespace=%s scanned=%d ok=%d fail=%d alerted=%d",
            namespace, report.scanned, report.succeeded, report.failed, report.alerted,
        )
        return report

    def run_all(self) -> list[ReEmbedReport]:
        return [self.run_once(ns) for ns in NAMESPACE_TABLES.keys()]
