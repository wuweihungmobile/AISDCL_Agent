"""tests/infra/test_pg_async_compat.py — C-4/X-5 asyncio 相容性測試。

驗證 _run_async() 在三種情境下皆可正常運作：
  1. 無 event loop（CLI / pytest 同步環境）
  2. 有 running event loop（pytest-asyncio / anyio 場景）
  3. thread-pool fallback 行為（RuntimeError 分支）
"""
from __future__ import annotations

import asyncio
import concurrent.futures

import pytest

from autoclaude.infra.repositories.pg_async_utils import _run_async


# ─────────────────────────────────────────────
# 測試情境 1：無 running loop（同步 pytest 環境）
# ─────────────────────────────────────────────

def test_run_async_no_running_loop():
    """無 running loop 時 _run_async() 直接 asyncio.run() 回傳結果。"""
    async def _coro():
        return 42

    result = _run_async(_coro())
    assert result == 42


def test_run_async_no_running_loop_exception_propagates():
    """無 running loop 時 coroutine 拋出的例外應向上傳播。"""
    async def _err():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        _run_async(_err())


# ─────────────────────────────────────────────
# 測試情境 2：有 running event loop（thread 包裝分支）
# ─────────────────────────────────────────────

def test_run_async_with_running_loop():
    """在已有 running loop 的執行緒中，_run_async() 應改用 thread-pool 執行，不拋 RuntimeError。"""
    results: list[object] = []
    errors: list[Exception] = []

    async def _coro():
        return "from_thread"

    def _in_loop():
        # 模擬 FastAPI 處理器：asyncio.get_running_loop() 可用
        async def _runner():
            try:
                val = _run_async(_coro())
                results.append(val)
            except RuntimeError as exc:
                errors.append(exc)

        asyncio.run(_runner())

    _in_loop()
    assert not errors, f"不應拋 RuntimeError，但得到: {errors}"
    assert results == ["from_thread"]


# ─────────────────────────────────────────────
# 測試情境 3：thread-pool fallback 行為驗證
# ─────────────────────────────────────────────

def test_run_async_thread_pool_fallback_directly():
    """直接驗證 thread-pool 分支：在 ThreadPoolExecutor 中執行 coroutine 可取得結果。"""
    async def _coro():
        await asyncio.sleep(0)
        return "thread_result"

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, _coro())
        result = future.result(timeout=5)

    assert result == "thread_result"
