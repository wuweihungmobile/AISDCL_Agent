"""SD_Improving_08 W4 / T4-F14：trace_context daemon thread 邊界測試（≥ 3 case）。

涵蓋：
  1. with_trace_id() 基本傳遞 + reset
  2. PTY daemon thread 不斷鏈（copy_context() 顯式包裝；R-SD08-F-1）
  3. 並發 thread isolation：不同 trace_id 不互相污染
  4. 巢狀 with_trace_id() 正確還原至外層值
  5. start_thread_with_context helper 自動拷貝 ctx

對應 ADR-SD08-004 §2.3 / §4 T4-F14。
"""
from __future__ import annotations

import threading
import time

from autoclaude.utils.trace_context import (
    get_trace_id,
    run_in_thread_with_context,
    start_thread_with_context,
    with_trace_id,
)


# ──────────────────────────────────────────────────────────────
# 1. with_trace_id() 基本傳遞 + reset
# ──────────────────────────────────────────────────────────────
def test_with_trace_id_sets_and_resets():
    assert get_trace_id() is None
    with with_trace_id("abc123") as tid:
        assert tid == "abc123"
        assert get_trace_id() == "abc123"
    # 出 with 後還原為 None
    assert get_trace_id() is None


def test_with_trace_id_default_generates_uuid():
    with with_trace_id() as tid:
        assert tid is not None
        assert len(tid) == 12  # uuid4().hex[:12]
        assert get_trace_id() == tid


# ──────────────────────────────────────────────────────────────
# 2. daemon thread 不斷鏈（copy_context() 顯式包裝）
# ──────────────────────────────────────────────────────────────
def test_daemon_thread_preserves_trace_id_with_copy_context():
    captured = {}

    def _target():
        # daemon thread 內讀取 trace_id 必須與 caller 一致
        captured["trace_id"] = get_trace_id()

    with with_trace_id("daemon-trace-001") as tid:
        # ❌ 不包 copy_context() 的 thread 會讀到 None
        # ✅ 改用 start_thread_with_context（內部 copy_context）
        thread = start_thread_with_context(_target, daemon=True)
        thread.join(timeout=2.0)

    assert captured["trace_id"] == "daemon-trace-001"


def test_naked_thread_does_not_propagate_trace_id():
    """確認：不使用 helper 的 raw Thread 確實會斷鏈（R-SD08-F-1 動機）。"""
    captured = {}

    def _target():
        captured["trace_id"] = get_trace_id()

    with with_trace_id("naked-trace") as tid:
        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=2.0)

    # 預期：raw Thread 不繼承 ContextVar（系統行為驗證）
    assert captured["trace_id"] is None


# ──────────────────────────────────────────────────────────────
# 3. 並發 thread isolation
# ──────────────────────────────────────────────────────────────
def test_concurrent_threads_have_isolated_trace_ids():
    results = {}
    barrier = threading.Barrier(3)

    def _worker(tid: str):
        with with_trace_id(tid):
            barrier.wait()  # 確保三個 thread 同時持有各自 trace_id
            time.sleep(0.01)
            results[tid] = get_trace_id()

    threads = [
        threading.Thread(target=_worker, args=(f"tid-{i}",)) for i in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)

    assert results == {"tid-0": "tid-0", "tid-1": "tid-1", "tid-2": "tid-2"}


# ──────────────────────────────────────────────────────────────
# 4. 巢狀 with_trace_id 正確還原
# ──────────────────────────────────────────────────────────────
def test_nested_with_trace_id_restores_outer_value():
    with with_trace_id("outer"):
        assert get_trace_id() == "outer"
        with with_trace_id("inner"):
            assert get_trace_id() == "inner"
        assert get_trace_id() == "outer"  # 內層離開後還原為 outer
    assert get_trace_id() is None


# ──────────────────────────────────────────────────────────────
# 5. run_in_thread_with_context 同步包裝
# ──────────────────────────────────────────────────────────────
def test_run_in_thread_with_context_synchronous_wrap():
    """run_in_thread_with_context 為同步執行（非 spawn thread）。"""

    def _fn(x: int) -> int:
        return x * 2 + (1 if get_trace_id() == "sync" else 0)

    with with_trace_id("sync"):
        result = run_in_thread_with_context(_fn, 5)

    assert result == 11
