"""SQLAlchemy ORM 表定義（Phase 6 選配）。

對應 SD_Improving_02.md v1.1 §1.3 / alembic/versions/0001_initial.sql。

⚠️ 此模組需要 sqlalchemy>=2.0：pip install autoclaude[postgres]
   pgvector 向量查詢需額外安裝：pip install autoclaude[postgres,pgvector]
   未安裝時，import 此模組將拋 ImportError；請以 try/except 處理。
"""
from __future__ import annotations

try:
    from sqlalchemy import (
        CheckConstraint,
        Column,
        Float,
        ForeignKey,
        Index,
        Integer,
        Text,
    )
    from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
    from sqlalchemy.orm import DeclarativeBase
    from sqlalchemy.sql import func
except ImportError as exc:
    raise ImportError(
        "PgStateRepository 需 sqlalchemy>=2.0；請執行：pip install autoclaude[postgres]"
    ) from exc

# pgvector 選配：未安裝時 embedding 欄位退化為 None（欄位定義跳過）
_PGVECTOR_AVAILABLE = False
try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import]
    _PGVECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore[assignment,misc]


class Base(DeclarativeBase):
    pass


class PlaybookRun(Base):
    """PlaybookRun ORM 表。

    Note on ``metadata_`` 命名（W4-T15 m-1）：
        欄位 Python 名稱使用結尾底線 ``metadata_``，是為了避免與
        SQLAlchemy ``DeclarativeBase`` 內建保留屬性 ``metadata``
        （MetaData 實例，用於 schema 反射）衝突。實際資料庫欄位名
        透過 ``Column("metadata", ...)`` 仍為 ``metadata``，無需 migration。

        歷史考量：此欄位在 alembic 0001_initial 已建立，重新命名會破壞
        既有資料與 migration 鏈，故維持結尾底線的 Python 命名。
    """
    __tablename__ = "playbook_runs"
    run_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    playbook_id = Column(Text, nullable=False, index=True)
    project = Column(Text, nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(TIMESTAMP(timezone=True))
    status = Column(Text, nullable=False)
    # DEF-101-051：三層 goal_task_id 接線。DB 欄 + FK（fk_runs_goal_task）由 alembic
    # 0010 建立；此處補 ORM 映射使 repository 得以寫入。不在 ORM 宣告 ForeignKey——
    # goal_tasks 非本模組 ORM 模型，FK 於 DB 層強制即可（與 GoalProgressRow 同慣例）。
    goal_task_id = Column(UUID(as_uuid=True), nullable=True)
    # DEF-101-051 / 0017：run 種類判別欄。'three_tier'（來自 goal 分解，必須有
    # goal_task_id）vs 'standalone'（plain playbook，合法無 goal）。CHECK
    # ck_runs_three_tier_has_goal 於 alembic 0017 強制。
    run_kind = Column(Text, nullable=False, server_default="standalone")
    # 命名說明見類別 docstring。
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'escalated', 'halted', 'interrupted')",
            name="ck_playbook_runs_status",
        ),
        CheckConstraint(
            "run_kind IN ('standalone', 'three_tier')",
            name="ck_runs_run_kind",
        ),
        CheckConstraint(
            "run_kind <> 'three_tier' OR goal_task_id IS NOT NULL",
            name="ck_runs_three_tier_has_goal",
        ),
        Index("idx_runs_status", "status"),
    )


class CheckpointRow(Base):
    """Checkpoint ORM 表（PgStateRepository 主要儲存目標）。

    Note on ``saved_at`` 精度（W4-T15 m-3）：
        ``TIMESTAMP(timezone=True)`` （PostgreSQL ``TIMESTAMPTZ``）原生提供
        微秒（μs）精度與 UTC offset，符合多 run / 多時區情境的時序需求。
        對應 migration: ``alembic/versions/0006_checkpoint_saved_at_tz.py``
        （將早期 schema 中可能殘留的 ``TIMESTAMP WITHOUT TIME ZONE`` 一併
        升級為 ``TIMESTAMPTZ``，並補 ``DEFAULT now()``）。
    """
    __tablename__ = "checkpoints"
    checkpoint_id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    run_id = Column(UUID(as_uuid=True), ForeignKey("playbook_runs.run_id"), nullable=False)
    playbook_id = Column(Text, nullable=False)
    step_idx = Column(Integer, nullable=False)
    step_id = Column(Text, nullable=False)
    total_steps = Column(Integer, nullable=False)
    # W4-T15 m-3: TIMESTAMPTZ 提供微秒級精度 + UTC offset
    saved_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    scheduled_resume_at = Column(TIMESTAMP(timezone=True))
    peak_token_pct = Column(Float, nullable=False, server_default="0")
    counters = Column(JSONB, nullable=False, server_default="{}")
    completed_step_log = Column(ARRAY(Text), nullable=False, server_default="{}")
    completed_step_ids = Column(ARRAY(Text), nullable=False, server_default="{}")
    failure_history = Column(JSONB, nullable=False, server_default="[]")
    active_step_attempt = Column(Integer, nullable=False, server_default="0")
    last_correction_prompt = Column(Text, nullable=False, server_default="")
    __table_args__ = (
        # C-6 修復：改為 run_id 唯一索引，允許同一 playbook_id 有多個 run（多次執行）
        Index("idx_ck_run_id", "run_id", unique=True),
    )


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    entry_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    error_class = Column(Text, nullable=False)
    error_signature = Column(Text, nullable=False)
    successful_strategy = Column(Text)
    tried_strategies = Column(ARRAY(Text), nullable=False, server_default="{}")
    step_id = Column(Text, nullable=False)
    outcome = Column(Text, nullable=False)
    recorded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    # pgvector 選配欄位（nullable，向下相容；需安裝 pgvector extension + Python pgvector 套件）
    embedding = (  # type: ignore[assignment]
        Column(Vector(1536), nullable=True) if _PGVECTOR_AVAILABLE else None
    )
    __table_args__ = (
        CheckConstraint("outcome IN ('success', 'escalation')", name="ck_kb_outcome"),
        Index("idx_kb_signature", "error_class", "error_signature"),
    )


class PlaybookVersion(Base):
    __tablename__ = "playbook_versions"
    version_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    original_playbook_id = Column(Text, nullable=False)
    generation = Column(Integer, nullable=False)
    yaml_content = Column(Text, nullable=False)
    mutation_log = Column(ARRAY(Text), nullable=False, server_default="{}")
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("playbook_versions.version_id"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        Index("idx_pv_playbook", "original_playbook_id", "generation"),
    )


class DriftLogRow(Base):
    """SD_06 W5-T5-5：DualStateRepository drift 紀錄 ORM。

    對應 alembic 0013_drift_log：partition by month（detected_at），
    365 天 TTL；PK = (drift_id, detected_at)。
    """
    __tablename__ = "drift_log"
    drift_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    detected_at = Column(
        TIMESTAMP(timezone=True), primary_key=True, nullable=False, server_default=func.now(),
    )
    run_id = Column(UUID(as_uuid=True), nullable=True)
    playbook_id = Column(Text, nullable=False)
    source_left = Column(Text, nullable=False)
    source_right = Column(Text, nullable=False)
    field_drift = Column(JSONB, nullable=False)
    severity = Column(Text, nullable=False, server_default="warn")
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolver = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warn', 'critical')",
            name="ck_drift_severity",
        ),
        Index("idx_drift_log_playbook", "playbook_id", "detected_at"),
    )


class ConfigAuditLogRow(Base):
    """SD_06 W5-T5-16：ConfigResolver 設定變更稽核 ORM。

    對應 alembic 0014_config_audit_log。
    """
    __tablename__ = "config_audit_log"
    audit_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    changed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    user_id = Column(UUID(as_uuid=True), nullable=True)
    layer = Column(Text, nullable=False)  # global / workflow / step / runtime
    field_path = Column(Text, nullable=False)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    action = Column(Text, nullable=False, server_default="update")
    reason = Column(Text, nullable=True)
    __table_args__ = (
        CheckConstraint(
            "layer IN ('global', 'workflow', 'step', 'runtime')",
            name="ck_config_audit_layer",
        ),
        CheckConstraint(
            "action IN ('insert', 'update', 'delete', 'reject')",
            name="ck_config_audit_action",
        ),
        Index("idx_config_audit_field", "field_path", "changed_at"),
    )


class KbMetricRow(Base):
    """F-C3 / ADR-SD09-006 §2.3：KB metrics 跨 session 快照 ORM。

    對應 alembic 0016_agt_phase1_memory（append-only；[start, end) 半開區間）。
    """
    __tablename__ = "kb_metrics"
    metric_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    metric_name = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    window_start_at = Column(TIMESTAMP(timezone=True), nullable=False)
    window_end_at = Column(TIMESTAMP(timezone=True), nullable=False)
    run_id = Column(UUID(as_uuid=True), nullable=True)
    tags = Column(JSONB, nullable=True, server_default="{}")
    recorded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        Index("idx_kb_metrics_name_window", "metric_name", "window_end_at"),
    )


class UserPreferenceRow(Base):
    """F-C1 / ADR-AGT-003 L3：使用者偏好 ORM（UPSERT by (scope, key)）。

    對應 alembic 0016_agt_phase1_memory。
    """
    __tablename__ = "user_preferences"
    scope = Column(Text, primary_key=True)
    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class GoalProgressRow(Base):
    """F-C2 / ADR-AGT-003 L4：目標進度 ledger ORM（append-only）。

    對應 alembic 0016_agt_phase1_memory。
    """
    __tablename__ = "goal_progress"
    progress_id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid(),
    )
    goal_task_id = Column(Text, nullable=False)
    playbook_id = Column(Text, nullable=True)
    run_id = Column(UUID(as_uuid=True), nullable=True)
    completed_features = Column(JSONB, nullable=False, server_default="[]")
    progress_pct = Column(Float, nullable=True)
    recorded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        Index("idx_goal_progress_goal", "goal_task_id", "recorded_at"),
    )
