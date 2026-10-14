"""DB 模式的狀態鏡射（BRIDGE_DB_DSN 有設才啟用；沒設＝純檔案模式，本模組不會被載入）。

寫入分工（COMMON_CONTEXT／PRD §0.2.2）：console-api 只在建立 run 時寫
`id, project_id, run_number, autonomy_level, scope, token_budget, dag, started_at`；Bridge 擁有
`status, subprocess_pid, bridge_instance, advisory_lock_key, total_tokens_used, completed_at`
以及 `execution_steps`、`checkpoints` 兩表的**所有**寫入。後端對這些欄位只讀。

⚠ 九張表住在 `console` schema（掌舵者決策：AutoClaude 自己的 alembic 已在 public 建了同名的
`checkpoints` 等表）。所有 SQL 一律用 schema 限定名，schema 名由 BRIDGE_DB_SCHEMA 決定，
且一律以 `psycopg.sql.Identifier` 引用（永遠不做字串插值）。advisory lock 不是表，不受影響。

全部是 best-effort：DB 掛了／列不存在／FK 不成立都只記 log 並回 False，不讓監督執行緒崩潰；
連線失敗後 5 秒內不再嘗試（斷路），避免每則事件都卡一次連線逾時。
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool, PoolTimeout

logger = logging.getLogger("bridge.db")

#: Bridge 唯一可更新的 execution_runs 欄位。
RUN_COLUMNS = frozenset({
    "status", "subprocess_pid", "bridge_instance", "advisory_lock_key",
    "total_tokens_used", "completed_at",
})
_BREAKER_SECONDS = 5.0


class BridgeDb:
    def __init__(self, dsn: str, schema: str):
        self._schema = schema
        self._pool = ConnectionPool(dsn, min_size=1, max_size=4, open=False, timeout=3,
                                    kwargs={"connect_timeout": 3})
        self._down_until = 0.0
        self._breaker_lock = threading.Lock()

    # ── 生命週期 ─────────────────────────────────────────────────────────────
    def open(self) -> None:
        self._pool.open(wait=False)

    def close(self) -> None:
        self._pool.close()

    # ── 內部 ─────────────────────────────────────────────────────────────────
    def _t(self, table: str) -> sql.Composed:
        return sql.SQL("{}.{}").format(sql.Identifier(self._schema), sql.Identifier(table))

    def _run(self, label: str, fn: Any) -> Any:
        if time.monotonic() < self._down_until:
            return None
        try:
            with self._pool.connection(timeout=3) as conn:
                return fn(conn)
        except (psycopg.OperationalError, PoolTimeout) as exc:
            with self._breaker_lock:
                self._down_until = time.monotonic() + _BREAKER_SECONDS
            logger.warning("DB 不可用（%s）：%s——%s 秒內不再嘗試", label, exc, _BREAKER_SECONDS)
        except psycopg.Error as exc:
            logger.error("DB 寫入失敗（%s）：%s", label, exc)
        return None

    # ── API ──────────────────────────────────────────────────────────────────
    def ping(self) -> bool:
        self._down_until = 0.0
        return self._run("ping", lambda c: c.execute("SELECT 1").fetchone()) is not None

    def schema_ready(self) -> bool:
        """三張表都存在（後端 Flyway 已跑過）。只是診斷用——不存在時各寫入會各自跳過。"""
        def check(conn: psycopg.Connection) -> bool:
            return all(
                conn.execute("SELECT to_regclass(%s)", (f"{self._schema}.{t}",)).fetchone()[0]
                for t in ("execution_runs", "execution_steps", "checkpoints"))
        return bool(self._run("schema_ready", check))

    def update_run(self, run_id: str, **fields: Any) -> bool:
        bad = set(fields) - RUN_COLUMNS
        if bad:
            raise ValueError(f"Bridge 不可寫入 execution_runs 的欄位：{sorted(bad)}")
        if not fields:
            return False
        assignments = sql.SQL(", ").join(
            sql.SQL("{} = %s").format(sql.Identifier(k)) for k in fields)
        query = sql.SQL("UPDATE {} SET {} WHERE id = %s").format(
            self._t("execution_runs"), assignments)

        def do(conn: psycopg.Connection) -> bool:
            return conn.execute(query, [*fields.values(), uuid.UUID(run_id)]).rowcount > 0

        updated = self._run(f"update_run {run_id}", do)
        if updated is False:
            logger.info("execution_runs 列不存在（run_id=%s），跳過狀態鏡射", run_id)
        return bool(updated)

    def insert_step(self, *, run_id: str, task_id: str | None, step_number: int, action: str,
                    status: str, input_data: dict[str, Any] | None = None,
                    output: str | None = None, tokens_used: int | None = None,
                    error_message: str | None = None) -> bool:
        """task_id 不是 UUID（playbook 沒帶 goal_task_id）就不寫 DB、只留事件。"""
        try:
            task_uuid = uuid.UUID(task_id) if task_id else None
        except ValueError:
            task_uuid = None
        if task_uuid is None:
            return False
        query = sql.SQL(
            "INSERT INTO {} (id, run_id, task_id, step_number, action, status, input, output, "
            "tokens_used, error_message) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        ).format(self._t("execution_steps"))

        def do(conn: psycopg.Connection) -> bool:
            conn.execute(query, (
                uuid.uuid4(), uuid.UUID(run_id), task_uuid, step_number, action[:500], status,
                Jsonb(input_data) if input_data is not None else None, output, tokens_used,
                error_message))
            return True

        return bool(self._run(f"insert_step {run_id}#{step_number}", do))

    def insert_checkpoint(self, *, run_id: str, checkpoint_id: str, name: str,
                          state_snapshot: dict[str, Any], created_at: datetime,
                          is_automatic: bool) -> bool:
        query = sql.SQL(
            "INSERT INTO {} (id, run_id, name, state_snapshot, created_at, is_automatic) "
            "VALUES (%s, %s, %s, %s, %s, %s)").format(self._t("checkpoints"))

        def do(conn: psycopg.Connection) -> bool:
            conn.execute(query, (uuid.UUID(checkpoint_id), uuid.UUID(run_id), name[:200],
                                 Jsonb(state_snapshot), created_at, is_automatic))
            return True

        return bool(self._run(f"insert_checkpoint {run_id}", do))

    def find_lock_holder(self, db_key: int) -> str | None:
        query = sql.SQL(
            "SELECT id FROM {} WHERE advisory_lock_key = %s "
            "AND status IN ('INITIALIZING','RUNNING','PAUSED') ORDER BY started_at DESC LIMIT 1"
        ).format(self._t("execution_runs"))

        def do(conn: psycopg.Connection) -> str | None:
            row = conn.execute(query, (db_key,)).fetchone()
            return str(row[0]) if row else None

        return self._run("find_lock_holder", do)
