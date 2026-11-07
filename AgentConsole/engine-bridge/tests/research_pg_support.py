"""研究表測試的 PostgreSQL 支援（TCS-ResearchToPRD-P0-20261102 §2 的 `RDB`；ADR-003 D2）。

`make_research_db()`：在 `BRIDGE_TEST_DSN` 所指的伺服器上建一個**拋棄式資料庫**
（名稱 `r2p_bra_<隨機>`），依數值序套用 backend 的 Flyway 檔 `V1`～`V20`（直接讀真檔，不另抄
一份），交出該庫的 DSN；測完 `drop()`。絕不連真 `aisdlc` 資料庫、絕不碰名稱不帶本前綴的庫。

`BRIDGE_TEST_DSN` 未設＝`pytest.skip("TOOL-ABSENCE: BRIDGE_TEST_DSN 不存在")`（TCS §2 的
skip 規則；SCG-4 要求兩個環境都在場、0 skipped 重跑）。`block()`／`unblock()` 模擬「資料庫
斷線」：禁止新連線並踢掉既有連線，用來驗 BLOCKED_DB 與 outbox 重放（AT-960-2-5）。
"""
from __future__ import annotations

import os
import re
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.conninfo import conninfo_to_dict, make_conninfo

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_DIR = (REPO_ROOT / "AgentConsole" / "backend" / "src" / "main" / "resources" / "db"
                 / "migration")
DB_NAME_PREFIX = "r2p_bra_"
LAST_VERSION = 20
_FILE_RE = re.compile(r"^V(\d+)__.+\.sql$")


#: 匯入時就讀（conftest 的 autouse 夾具會在每個測試前移除所有 `BRIDGE_*` 環境變數，
#: 既有 `test_db_integration.py` 同此作法）。
BRIDGE_TEST_DSN: str | None = os.environ.get("BRIDGE_TEST_DSN") or None


def bridge_test_dsn() -> str | None:
    return BRIDGE_TEST_DSN


def require_test_dsn() -> str:
    dsn = bridge_test_dsn()
    if dsn is None:
        pytest.skip("TOOL-ABSENCE: BRIDGE_TEST_DSN 不存在")
    return dsn


def migration_files(last: int = LAST_VERSION) -> list[Path]:
    """`V1`～`V<last>` 的 Flyway 檔，依版本數值序（不是字典序：V10 在 V2 之後）。"""
    found: dict[int, Path] = {}
    for path in MIGRATION_DIR.iterdir():
        match = _FILE_RE.match(path.name)
        if match and int(match.group(1)) <= last:
            found[int(match.group(1))] = path
    missing = [n for n in range(1, last + 1) if n not in found]
    assert not missing, f"Flyway 檔缺版本 {missing}（{MIGRATION_DIR}）"
    return [found[n] for n in sorted(found)]


def _with_dbname(dsn: str, name: str) -> str:
    return make_conninfo(**{**conninfo_to_dict(dsn), "dbname": name})


@dataclass
class ThrowawayDb:
    """一個拋棄式資料庫：`dsn` 指向它、`admin_dsn` 指向伺服器上建庫用的維護庫。"""

    name: str
    dsn: str
    admin_dsn: str

    # ── 查詢與執行（每次一條 autocommit 連線，與被測寫入器的連線互不干擾）────────────────────
    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.dsn, autocommit=True, connect_timeout=5) as conn:
            yield conn

    def q(self, query: str, *params: Any) -> list[tuple[Any, ...]]:
        with self.connect() as conn:
            return conn.execute(query, params or None).fetchall()

    def one(self, query: str, *params: Any) -> tuple[Any, ...] | None:
        rows = self.q(query, *params)
        return rows[0] if rows else None

    def exec(self, query: str, *params: Any) -> None:
        with self.connect() as conn:
            conn.execute(query, params or None)

    def count(self, table: str, where: str = "TRUE", *params: Any) -> int:
        row = self.one(f"SELECT count(*) FROM console.{table} WHERE {where}", *params)
        return int(row[0]) if row else 0

    def events(self, research_id: Any) -> list[tuple[Any, ...]]:
        return self.q("SELECT seq, event_type, step, actor, ref_kind, ref_id, payload "
                      "FROM console.research_events WHERE research_id = %s ORDER BY seq",
                      research_id)

    # ── 模擬斷線 ─────────────────────────────────────────────────────────────────────────────
    def block(self) -> None:
        """禁止新連線並踢掉既有連線：之後的寫入一律連線失敗。"""
        with psycopg.connect(self.admin_dsn, autocommit=True) as admin:
            admin.execute(f'ALTER DATABASE "{self.name}" WITH ALLOW_CONNECTIONS false')
            admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                          "WHERE datname = %s AND pid <> pg_backend_pid()", (self.name,))

    def unblock(self) -> None:
        with psycopg.connect(self.admin_dsn, autocommit=True) as admin:
            admin.execute(f'ALTER DATABASE "{self.name}" WITH ALLOW_CONNECTIONS true')

    def drop(self) -> None:
        assert self.name.startswith(DB_NAME_PREFIX), "只准 DROP 本支援建的拋棄式資料庫"
        with psycopg.connect(self.admin_dsn, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{self.name}" WITH (FORCE)')


def make_research_db(last: int = LAST_VERSION) -> ThrowawayDb:
    """建拋棄式庫並套用 V1～V<last>。呼叫端負責 `drop()`（fixture 的 finally）。"""
    admin_dsn = require_test_dsn()
    name = f"{DB_NAME_PREFIX}{secrets.token_hex(6)}"
    db = ThrowawayDb(name=name, dsn=_with_dbname(admin_dsn, name), admin_dsn=admin_dsn)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        with psycopg.connect(db.dsn, autocommit=True) as conn:
            # backend 的 Flyway 設定 `default-schema: console`：遷移檔不帶 schema 的名稱落在它
            conn.execute("CREATE SCHEMA IF NOT EXISTS console")
            conn.execute("SET search_path TO console")
            for path in migration_files(last):
                conn.execute(path.read_text(encoding="utf-8"))
    except BaseException:
        db.drop()
        raise
    return db


def stale_databases() -> list[str]:
    """伺服器上殘留的本支援拋棄式庫（行程被殺才會有；交卷前現查應為空）。"""
    with psycopg.connect(require_test_dsn(), autocommit=True) as admin:
        rows = admin.execute("SELECT datname FROM pg_database WHERE datname LIKE %s ORDER BY 1",
                             (DB_NAME_PREFIX + "%",)).fetchall()
    return [r[0] for r in rows]
