"""
非阻塞 stdout 讀取器。
Windows 不支援 select() 在 pipe 上，因此用背景 Thread + Queue 實作。
主迴圈呼叫 readline(timeout) 永遠不會卡死。

SD_08 W4 / R-SD08-F-1：daemon thread 邊界以 copy_context().run() 顯式包裝，
                       確保 trace_id 在 PTY 邊界不斷鏈（ADR-SD08-004 §2.3）。
"""
from __future__ import annotations
import queue
import threading
from contextvars import copy_context
from typing import IO, Optional


class NonBlockingStreamReader:
    _SENTINEL = object()

    def __init__(self, stream: IO[bytes]):
        self._stream = stream
        self._queue: queue.Queue = queue.Queue()
        # SD_08 W4 / R-SD08-F-1：以 copy_context() 拷貝呼叫端 contextvars
        # 至 daemon thread；thread 內呼叫 get_trace_id() 可正確讀取 trace_id
        ctx = copy_context()
        self._thread = threading.Thread(
            target=lambda: ctx.run(self._reader),
            daemon=True,
            name="autoclaude.stream_reader",
        )
        self._thread.start()

    def _reader(self) -> None:
        try:
            for line in iter(self._stream.readline, b""):
                self._queue.put(line)
        finally:
            self._queue.put(self._SENTINEL)

    def readline(self, timeout: float = 0.2) -> Optional[bytes]:
        """回傳一行，若 timeout 內無資料回傳 b''，EOF 回傳 None。"""
        try:
            item = self._queue.get(timeout=timeout)
            if item is self._SENTINEL:
                return None
            return item
        except queue.Empty:
            return b""

    def close(self, timeout: float = 1.0) -> None:
        """等待背景讀取執行緒結束（daemon thread，無法強制中斷）。"""
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()
