"""trace_context — trace_id 端對端傳遞（SD_Improving_08 W4 / ADR-SD08-004 §2.3）。

設計原則（**LOC tier 實際適用**：trace_context.py 位於 `autoclaude/utils/` 不在任何 LOC tier patterns，`tools/check_loc_budget.py` 視為 unclassified → ABSOLUTE_LIMIT 750；當前 229 LOC（SD_09 W3 路徑 (b) W3C helper 已落地，仍遠低於 750；`.loc-budget.toml` 顯式 contract tier ≤ 400 雙簽核 override 列 W3 T3-F1b 收尾項）— 詳見 ADR-SD09-004 §3.0 R41 校正）：
  - 使用 `contextvars.ContextVar`，預設值 None；不污染 IBrain / IExecutor Port 簽名
  - `with_trace_id()` context manager 自動還原（reset token），杜絕跨流程污染
  - `run_in_thread_with_context()` 顯式 `copy_context().run()` 包裝（R-SD08-F-1 緩解）
  - EventBus dispatch 時自動 `payload.setdefault("_trace_id", get_trace_id())`

禁止：
  ❌ Plugin 直接 import 本模組（必須走 IObservabilityPort 注入；importlinter Rule 7）
  ❌ 將 trace_id 透過 IBrain / IExecutor 參數傳遞（ContextVar 為唯一傳輸通道）

對應：
  - ADR-SD08-004 §2.3 trace_id 端對端傳遞
  - R-SD08-F-1 daemon thread 邊界斷鏈緩解（PTY NonBlockingStreamReader）
"""
from __future__ import annotations

import os
import threading
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from typing import Callable, Iterator, Optional, TypeVar

# trace_id ContextVar — 預設 None；以 with_trace_id() 設定
trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

_T = TypeVar("_T")


def get_trace_id() -> Optional[str]:
    """取得當前 trace_id；未設定回 None。"""
    return trace_id.get()


@contextmanager
def with_trace_id(tid: Optional[str] = None) -> Iterator[str]:
    """設定 trace_id 並在 context manager 結束時還原（reset token）。

    Args:
        tid: 指定 trace_id；None 時自動產生 uuid4 hex（前 12 字）

    Yields:
        當前 trace_id 字串

    使用模式：
        with with_trace_id() as tid:
            kernel.run(playbook)   # EventBus dispatch 會自動注入此 tid

        with with_trace_id("abc123") as tid:
            ...                   # 顯式指定 tid（測試 / 跨 process 場景）

    重入安全：
        ContextVar.set() 回傳 Token，with 結束時 reset 還原前一狀態。
        多層巢狀 with_trace_id() 會正確還原至外層值（非全域變數）。
    """
    new_id = tid if tid is not None else uuid.uuid4().hex[:12]
    token = trace_id.set(new_id)
    try:
        yield new_id
    finally:
        trace_id.reset(token)


def run_in_thread_with_context(
    fn: Callable[..., _T], *args, **kwargs
) -> _T:
    """以當前 contextvars 快照執行 fn（給 daemon thread 邊界使用）。

    背景：
        Python ContextVar 在 threading.Thread 邊界**不會自動傳播**；
        若 PTY NonBlockingStreamReader 等 daemon thread 在新 thread 內讀 trace_id
        會永遠拿到預設值 None（trace_id 斷鏈）。

    緩解（R-SD08-F-1）：
        `copy_context().run(fn, ...)` 顯式拷貝當前 context 並在 fn 內執行；
        fn 內呼叫 get_trace_id() 可正確取得呼叫端設定的 trace_id。

    使用模式：
        # 在 thread target 內：
        def _reader():
            tid = get_trace_id()  # ← 不包 copy_context() 時為 None

        # 改用本 helper：
        thread = threading.Thread(
            target=lambda: run_in_thread_with_context(_reader)
        )

    注意：
        - 本函式為「同步」執行 fn（在 caller thread 內），不是 spawn thread
        - 真正 spawn thread 時，需在 thread target 內呼叫本函式（見上述模式）
    """
    ctx = copy_context()
    return ctx.run(fn, *args, **kwargs)


def start_thread_with_context(
    target: Callable[..., None],
    *,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    daemon: bool = True,
    name: Optional[str] = None,
) -> threading.Thread:
    """建立並啟動帶 contextvars 拷貝的 Thread（R-SD08-F-1 一站式 API）。

    用於需要在 daemon thread 內保留 trace_id 的場景（如 PTY stream reader）。

    關鍵實作（R-SD08-F-1 緩解）：
        `copy_context()` 必須在 **caller thread** 執行（即本函式內），而非
        thread target 內。因為 ContextVar 是 thread-local：在新 thread 內呼叫
        copy_context() 只會拿到新 thread 自己的空 context，無法回溯 caller。

    Args:
        target: thread 目標函式
        args / kwargs: 傳給 target 的參數
        daemon: 是否設為 daemon thread（預設 True）
        name: thread 名稱

    Returns:
        已 start() 的 Thread 物件
    """
    kw = kwargs or {}
    # 關鍵：在 caller thread 拷貝當前 context，再把 ctx.run 包進 target
    ctx = copy_context()

    def _wrapped() -> None:
        ctx.run(target, *args, **kw)

    thread = threading.Thread(target=_wrapped, daemon=daemon, name=name)
    thread.start()
    return thread


def to_traceparent_header(tid: str, span_id: str | None = None, flags: str = "01") -> str:
    """組裝 W3C TraceContext `traceparent` header（SD_09 W3 T3-F1b / ADR-SD09-004 §2.3）。

    格式：`<version>-<trace-id>-<parent-id>-<trace-flags>`
        version: 固定 "00"
        trace-id: 32 hex chars（lowercase；不足左補 0；超出截 32）
        parent-id (span-id): 16 hex chars（None 時自動產生 uuid4.hex[:16]）
        trace-flags: 2 hex chars（"01" = sampled，預設）

    Args:
        tid: trace_id（任意字串；自動正規化為 32 lowercase hex）
        span_id: parent span_id（None 自動產生）
        flags: trace flags（預設 "01" sampled）

    Returns:
        W3C traceparent header 字串
    """
    normalized = "".join(c for c in tid.lower() if c in "0123456789abcdef")
    if len(normalized) < 32:
        normalized = normalized.rjust(32, "0")
    elif len(normalized) > 32:
        normalized = normalized[:32]
    sp = span_id if span_id is not None else uuid.uuid4().hex[:16]
    sp_normalized = "".join(c for c in sp.lower() if c in "0123456789abcdef")
    if len(sp_normalized) < 16:
        sp_normalized = sp_normalized.rjust(16, "0")
    elif len(sp_normalized) > 16:
        sp_normalized = sp_normalized[:16]
    return f"00-{normalized}-{sp_normalized}-{flags}"


def from_traceparent_header(header: str) -> str | None:
    """解析 W3C TraceContext `traceparent` header 取回 trace_id（SD_09 W3 T3-F1b）。

    格式驗證：`<version>-<trace-id 32hex>-<parent-id 16hex>-<trace-flags 2hex>`。
    不符合即回 None（不丟例外，呼叫端可 fallback）。

    Args:
        header: W3C traceparent header 字串

    Returns:
        trace_id（32 lowercase hex）；解析失敗回 None
    """
    if not header:
        return None
    parts = header.split("-")
    if len(parts) != 4:
        return None
    version, tid, sp, flags = parts
    if version != "00":
        return None
    if len(tid) != 32 or not all(c in "0123456789abcdef" for c in tid.lower()):
        return None
    if len(sp) != 16 or not all(c in "0123456789abcdef" for c in sp.lower()):
        return None
    if len(flags) != 2 or not all(c in "0123456789abcdef" for c in flags.lower()):
        return None
    return tid.lower()


def propagate_to_subprocess_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Inject current trace_id into subprocess env dict (W3C TraceContext compatible).

    SD_09 W3 T3-F1b 落地（ADR-SD09-004 §2.3 路徑 b W3C TraceContext finalized）：
      - 寫入 W3C 標準 env key `TRACEPARENT`（`00-<32hex>-<16hex>-<flags>`）
      - 同步寫入 `AUTOCLAUDE_TRACE_ID`（路徑 a 過渡兼容；SD_10 OTel 過渡後可移除）
      - 若 caller env 已含 TRACEPARENT 不覆蓋（§2.4 caller env override 處理）

    Args:
        env: 來源 env dict；None 時拷貝 os.environ

    Returns:
        新 env dict（pure function，不 mutate caller 輸入）
    """
    result = dict(env) if env is not None else dict(os.environ)
    tid = get_trace_id()
    if tid:
        result["AUTOCLAUDE_TRACE_ID"] = tid
        # caller 已設 TRACEPARENT 時不覆蓋（W3C distributed tracing semantics）
        if "TRACEPARENT" not in result:
            result["TRACEPARENT"] = to_traceparent_header(tid)
    return result


__all__ = [
    "trace_id",
    "get_trace_id",
    "with_trace_id",
    "run_in_thread_with_context",
    "start_thread_with_context",
    "propagate_to_subprocess_env",
    "to_traceparent_header",
    "from_traceparent_header",
]
