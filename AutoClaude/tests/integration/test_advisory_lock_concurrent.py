"""SD_Improving_06 W4-T4-7 — pg_advisory advisory lock 並發 import 整合測試。

對應規格：
  - SD_Improving_06.md §4 W4-2（pg_advisory_xact_lock(hash(playbook_id))）
  - SD06_Execution_Guide.md §3 W4 T4-7

涵蓋面：
  T1 模組 API 表面（無需 DB）：try_acquire_import_lock / has_active_import_for / import_lock_scope
  T2 並發鎖（DB-bound）：兩 conn 同 playbook_id → 第二取鎖必為 False
  T3 鎖在 commit 後釋放（DB-bound）
  T4 不同 playbook_id 互不影響（DB-bound）
  T5 has_active_import_for(): 沒有 active job → False
  T6 import_lock_scope context manager 行為

DB 測試遵循 contract test 慣例：未設定 AUTOCLAUDE_DB_DSN/AUTOCLAUDE_TEST_PG_DSN 時 skip。
"""
from __future__ import annotations

import os
import re

import pytest

from autoclaude.infra.repositories.pg_advisory import (
    has_active_import_for,
    import_lock_scope,
    try_acquire_import_lock,
)

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


# ──────────────────────────────────────────────────────────────
# T1 模組 API 表面（不依賴 DB）
# ──────────────────────────────────────────────────────────────
class TestAdvisoryLockAPI:
    """無 DSN 也能驗證的純函式 API。"""

    def test_try_acquire_signature_callable(self):
        assert callable(try_acquire_import_lock)

    def test_has_active_signature_callable(self):
        assert callable(has_active_import_for)

    def test_import_lock_scope_is_context_manager(self):
        # 用 fake conn 驗證 context manager 至少進入 finally
        class _FakeCur:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, *a, **kw): self._row = (True,)
            def fetchone(self): return self._row

        class _FakeConn:
            def cursor(self): return _FakeCur()

        with import_lock_scope(_FakeConn(), "demo") as acquired:
            assert acquired is True


# ──────────────────────────────────────────────────────────────
# T2~T6 DB-bound（需 DSN）
# ──────────────────────────────────────────────────────────────
pytestmark_db = pytest.mark.skipif(
    _DSN is None,
    reason="需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑並發 advisory lock 測試",
)


def _new_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    c = psycopg2.connect(_DSN)
    c.autocommit = False
    return c


@pytestmark_db
class TestAdvisoryLockConcurrent:
    """alembic 0012 try_acquire_import_lock 並發語意。"""

    def test_second_acquire_returns_false(self):
        c1 = _new_conn()
        c2 = _new_conn()
        try:
            assert try_acquire_import_lock(c1, "concurrent-test-A")
            # 第二 conn 嘗試取相同 lock_key → False
            assert try_acquire_import_lock(c2, "concurrent-test-A") is False
        finally:
            c1.rollback(); c1.close()
            c2.rollback(); c2.close()

    def test_lock_released_after_commit(self):
        c1 = _new_conn()
        c2 = _new_conn()
        try:
            assert try_acquire_import_lock(c1, "concurrent-test-B")
            c1.commit()
            # commit 後鎖釋放，c2 可取得
            assert try_acquire_import_lock(c2, "concurrent-test-B") is True
            c2.commit()
        finally:
            c1.close(); c2.close()

    def test_different_playbook_ids_independent(self):
        c1 = _new_conn()
        c2 = _new_conn()
        try:
            assert try_acquire_import_lock(c1, "concurrent-test-C")
            assert try_acquire_import_lock(c2, "concurrent-test-D") is True
        finally:
            c1.rollback(); c1.close()
            c2.rollback(); c2.close()

    def test_has_active_import_for_no_job(self):
        c = _new_conn()
        try:
            assert has_active_import_for(c, "no-such-playbook-zzz") is False
        finally:
            c.rollback(); c.close()

    def test_import_lock_scope_db(self):
        c = _new_conn()
        try:
            with import_lock_scope(c, "concurrent-test-E") as acquired:
                assert acquired is True
            c.commit()
        finally:
            c.close()
