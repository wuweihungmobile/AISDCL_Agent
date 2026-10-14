"""EventStore：每個 run 一個 append-only 的 events.jsonl ＋ 記憶體環，seq 單調遞增。

SSE 斷線重播（PRD §7.1.7，at-least-once）的基礎：
  · 每筆事件 `{"seq","ts","event",…payload}` 立即 flush 進 JSONL（崩潰也不丟已確認的事件）。
  · `replay(after, limit)` 先看記憶體環；游標比環還舊時退回掃檔（Bridge 重啟後也成立）。
  · SSE 端以 `add_waiter` 註冊 asyncio.Event，append 時用 `call_soon_threadsafe` 喚醒——
    事件由引擎監督執行緒產生，SSE 迴圈在事件迴圈裡，兩者不能直接共用 Event。

Windows 行為＝檔案以 `newline="\\n"` 寫入（不轉 CRLF），控制代碼在 close() 時釋放，
本模組從不改名／刪除 events.jsonl，所以「開著的檔不能被改名」的限制碰不到它。
"""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import threading
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

logger = logging.getLogger("bridge.events")

EVENT_TYPES = ("log", "status", "step", "token", "review-request", "alert")


class EventStore:
    def __init__(self, path: Path, *, ring_size: int = 5000):
        self._path = path
        self._ring: deque[dict[str, Any]] = deque(maxlen=ring_size)
        self._lock = threading.Lock()
        self._fh: TextIO | None = None
        self._last_seq = 0
        self._waiters: dict[int, tuple[asyncio.AbstractEventLoop, asyncio.Event]] = {}
        self._waiter_ids = itertools.count(1)
        self._load_existing()

    # ── 載入既有檔（Bridge 重啟後延續 seq）────────────────────────────────────
    def _load_existing(self) -> None:
        if not self._path.is_file():
            return
        with self._path.open(encoding="utf-8") as fh:
            for raw in fh:
                event = _parse_line(raw)
                if event is None:
                    continue          # 崩潰留下的截斷行：略過，seq 以讀到的最大值為準
                self._ring.append(event)
                self._last_seq = max(self._last_seq, event["seq"])

    @property
    def last_seq(self) -> int:
        with self._lock:
            return self._last_seq

    # ── 寫入 ─────────────────────────────────────────────────────────────────
    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        """附加一筆事件，回傳含 seq／ts／event 的完整封包。payload 不得覆寫這三個保留鍵。"""
        if event not in EVENT_TYPES:
            raise ValueError(f"未知的事件類型 {event!r}；契約只有 {EVENT_TYPES}")
        with self._lock:
            self._last_seq += 1
            envelope = {
                "seq": self._last_seq,
                "ts": datetime.now(UTC).isoformat(),
                "event": event,
                **{k: v for k, v in payload.items() if k not in ("seq", "ts", "event")},
            }
            self._write(json.dumps(envelope, ensure_ascii=False, separators=(",", ":")))
            self._ring.append(envelope)
            waiters = list(self._waiters.values())
        for loop, signal_event in waiters:
            try:
                loop.call_soon_threadsafe(signal_event.set)
            except RuntimeError:      # 該事件迴圈已關閉（SSE 連線已斷）：忽略
                pass
        return envelope

    def _write(self, line: str) -> None:
        try:
            if self._fh is None:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._fh = self._path.open("a", encoding="utf-8", newline="\n")
            self._fh.write(line + "\n")
            self._fh.flush()
        except OSError as exc:
            # 磁碟問題不得讓引擎監督崩潰：記憶體環仍有資料、SSE 照常；但要大聲說。
            logger.error("events.jsonl 寫入失敗（%s）：%s", self._path, exc)

    def close(self) -> None:
        with self._lock:
            if self._fh is not None:
                try:
                    self._fh.close()
                except OSError:
                    pass
                self._fh = None

    # ── 讀取 ─────────────────────────────────────────────────────────────────
    def replay(self, after: int = 0, limit: int | None = None) -> list[dict[str, Any]]:
        """回傳 seq > after 的事件（升冪）。after 比記憶體環還舊時改掃檔。"""
        cap = limit if limit and limit > 0 else None
        with self._lock:
            first_in_ring = self._ring[0]["seq"] if self._ring else self._last_seq + 1
            if after + 1 >= first_in_ring:
                tail = (e for e in self._ring if e["seq"] > after)
                return list(itertools.islice(tail, cap))
        return self._read_file(after, cap)

    def _read_file(self, after: int, cap: int | None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not self._path.is_file():
            return out
        with self._path.open(encoding="utf-8") as fh:
            for raw in fh:
                event = _parse_line(raw)
                if event is None or event["seq"] <= after:
                    continue
                out.append(event)
                if cap is not None and len(out) >= cap:
                    break
        return out

    # ── SSE 喚醒 ─────────────────────────────────────────────────────────────
    def add_waiter(self, loop: asyncio.AbstractEventLoop, signal_event: asyncio.Event) -> int:
        with self._lock:
            token = next(self._waiter_ids)
            self._waiters[token] = (loop, signal_event)
            return token

    def remove_waiter(self, token: int) -> None:
        with self._lock:
            self._waiters.pop(token, None)


def _parse_line(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, dict) or not isinstance(event.get("seq"), int):
        return None
    return event


def to_sse_data(event: dict[str, Any]) -> dict[str, Any]:
    """SSE `data:` 的 JSON：契約形狀是 {seq,ts,…欄位}，事件名已在 `event:` 行，不重複。"""
    return {k: v for k, v in event.items() if k != "event"}
