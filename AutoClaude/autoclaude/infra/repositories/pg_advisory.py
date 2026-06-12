"""SD_Improving_06 W4-T4-3 — pg_advisory_xact_lock helper（psycopg2）。

對應規格：
  - SD_Improving_06.md §4 W4-2 / W3-14（alembic 0012 try_acquire_import_lock）
  - tests/integration/test_advisory_lock_concurrent.py
  - tests/contract/test_alembic_0012_advisory_lock.py（已就位 W3）

行為：
  - try_acquire_import_lock(conn, playbook_id) → bool（呼叫 PG 內建 function）
  - has_active_import_for(conn, playbook_id) → bool
  - 鎖鍵 = hashtext(playbook_id)，XACT scope，事務結束自動釋放

紅線：本模組 **不可** import autoclaude.core 任何模組（infra 為 outer layer，可被 core 注入）。
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)


def try_acquire_import_lock(conn, playbook_id: str) -> bool:
    """呼叫 alembic 0012 註冊的 try_acquire_import_lock(text) → bool。

    Args:
        conn: psycopg2 connection（需在 active transaction 內，鎖才會持有至 commit）
        playbook_id: Playbook 唯一識別字串（CLI 以 Path.stem 或自訂 ID）

    Returns:
        True  → 取得鎖（可繼續 import）
        False → 已被其他 transaction 持有（caller 應 enqueue 或 skip）
    """
    with conn.cursor() as cur:
        cur.execute("SELECT try_acquire_import_lock(%s)", (playbook_id,))
        row = cur.fetchone()
    return bool(row[0]) if row else False


def has_active_import_for(conn, playbook_id: str) -> bool:
    """檢測是否已有 pending / running 的 yaml_import_jobs。"""
    with conn.cursor() as cur:
        cur.execute("SELECT has_active_import_for(%s)", (playbook_id,))
        row = cur.fetchone()
    return bool(row[0]) if row else False


@contextmanager
def import_lock_scope(conn, playbook_id: str) -> Iterator[bool]:
    """Context manager：取得 advisory lock；with 區塊結束時隨 transaction 釋放。

    Usage:
        with conn:  # 開啟 transaction
            with import_lock_scope(conn, playbook_id) as acquired:
                if not acquired:
                    raise RuntimeError(f"playbook {playbook_id} 鎖被持有")
                # ... do import ...

    若 caller 未開 transaction（autocommit），鎖會立即釋放。
    """
    acquired = try_acquire_import_lock(conn, playbook_id)
    try:
        yield acquired
    finally:
        # XACT 自動釋放；保留 finally 區塊以便日後加診斷
        if not acquired:
            logger.debug("import_lock_scope: 鎖未取得（playbook_id=%s）", playbook_id)


__all__ = [
    "try_acquire_import_lock",
    "has_active_import_for",
    "import_lock_scope",
]
