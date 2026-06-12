"""Alembic env.py（Phase 6 選配）。

依 SD_Improving_02.md v1.1 §1.5 路線 + Phase 6 stakeholder review：
  - 可選擇性安裝：pip install autoclaude[postgres]
  - 環境變數 AUTOCLAUDE_DB_DSN 設定資料庫連線（統一命名，Infra/Security review 要求）
  - 舊變數 AUTOCLAUDE_PG_DSN 保留作 deprecation alias（短期相容）
  - 缺 DSN 時 fail-loud（不再 fallback 至 alembic.ini 明文預設）

使用方式：
  export AUTOCLAUDE_DB_DSN=postgresql://user:pass@localhost:5432/autoclaude?sslmode=require
  alembic upgrade head
"""
from __future__ import annotations

import os
import sys

try:
    from alembic import context
    from sqlalchemy import engine_from_config, pool
except ImportError:
    print(
        "❌ alembic 未安裝。請先執行：pip install autoclaude[postgres]",
        file=sys.stderr,
    )
    sys.exit(1)


config = context.config

# 從環境變數覆寫 sqlalchemy.url（優先 AUTOCLAUDE_DB_DSN，fallback AUTOCLAUDE_PG_DSN）
dsn = os.environ.get("AUTOCLAUDE_DB_DSN") or os.environ.get("AUTOCLAUDE_PG_DSN")
if not dsn:
    print(
        "❌ 缺少 PostgreSQL DSN。請設定環境變數 AUTOCLAUDE_DB_DSN：\n"
        "   export AUTOCLAUDE_DB_DSN=postgresql://user:pass@host:5432/autoclaude?sslmode=require",
        file=sys.stderr,
    )
    sys.exit(2)
# asyncpg 是 async 驅動，alembic 只支援同步連線；strip +asyncpg 改用 psycopg2
import re as _re
dsn = _re.sub(r"\+asyncpg", "", dsn)
config.set_main_option("sqlalchemy.url", dsn)


def run_migrations_offline() -> None:
    """離線模式：產生 SQL 不直接連線。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """線上模式：直接連線並執行。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # SD_09 R56 P0-1e 修復：多個 revision id 長度 > 32（如
        # `0005_fix_checkpoint_unique_run_id` = 33 chars）超過 alembic 預設
        # alembic_version.version_num VARCHAR(32) → fresh DB `alembic upgrade head`
        # 報 psycopg2 StringDataRightTruncation「value too long for character varying(32)」，
        # 導致 CI 每次 fresh container 的全部 PG migration 失敗（pg-contract / pg-e2e-nightly
        # 長期紅，因上游 test job 紅被 skip 而隱藏）。預建寬欄位版表（idempotent；既有 DB
        # 已有此表則 no-op；VARCHAR(128) strictly 更寬零資料風險）。alembic 偵測表已存在即
        # 沿用本表，不再以預設 32 重建。
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(128) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
