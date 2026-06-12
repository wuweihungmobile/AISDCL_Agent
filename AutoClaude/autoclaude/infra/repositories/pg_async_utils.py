"""pg_async_utils — PG repository 共用 asyncio 包裝工具（Phase 6 C-4/X-5 修復）。

供 PgStateRepository / PgMemoryStore / PgPlaybookRepository 共用，
避免在各 repository 重複定義 _run_async() / _make_retry()。

修復問題：裸 asyncio.run() 在 FastAPI / aiohttp 等已有 running event loop 的
環境會拋 RuntimeError("This event loop is already running.")。
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging

logger = logging.getLogger("autoclaude.infra.repositories.pg")

# C-B 修復：分離 sqlalchemy 與 tenacity 的 import，避免 OperationalError = Exception 陷阱
_SQLALCHEMY_AVAILABLE = False
_TENACITY_AVAILABLE = False

try:
    from sqlalchemy.exc import OperationalError
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    class OperationalError(Exception):  # type: ignore[misc]
        """Sentinel：僅作型別佔位，sqlalchemy 未安裝時此例外永遠不會被拋出。"""

try:
    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )
    _TENACITY_AVAILABLE = True
except ImportError:
    pass


def _run_async(coro):
    """asyncio.run() 相容包裝，支援 FastAPI / aiohttp 等已有 running loop 的環境。

    - 無 running loop（CLI / pytest）：直接 asyncio.run()
    - 有 running loop（async framework）：新建 thread 內執行 asyncio.run()

    M-C：thread-pool .result() 加 timeout=300（5 分鐘），防止無限阻塞。
    線程資源由 `with` 語句保證清理（包含例外分支）。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=300)


def _log_before_sleep(retry_state) -> None:
    """W4-T15 m-7：tenacity retry before_sleep callback，記錄每次重試的細節。

    tenacity 內建 `before_sleep_log()` 在某些版本 API 不一致，
    自訂 callback 統一輸出格式（attempt N / sleep Xs / exception type）。
    """
    fn_name = getattr(retry_state.fn, "__qualname__", repr(retry_state.fn))
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    sleep_s = getattr(retry_state.next_action, "sleep", None)
    logger.warning(
        "PG retry | fn=%s | attempt=%d | sleep=%.2fs | exc=%s: %s",
        fn_name,
        retry_state.attempt_number,
        float(sleep_s) if sleep_s is not None else 0.0,
        type(exc).__name__ if exc else "None",
        str(exc) if exc else "",
    )


def _make_retry():
    """建立 tenacity retry decorator（OperationalError max 3, exponential backoff）。

    前提：sqlalchemy 與 tenacity 都必須安裝才啟用 retry 邏輯。
    任一未安裝時回傳 noop decorator。

    W4-T15 m-7：加 before_sleep=_log_before_sleep 記錄重試訊息（WARNING 等級）。
    """
    if not _TENACITY_AVAILABLE or not _SQLALCHEMY_AVAILABLE:
        def _noop(fn):
            return fn
        return _noop
    return retry(
        retry=retry_if_exception_type(OperationalError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=0.5, max=4),
        reraise=True,
        before_sleep=_log_before_sleep,
    )
