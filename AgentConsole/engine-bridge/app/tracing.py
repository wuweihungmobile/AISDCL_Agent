"""traceId 貫穿 console-api → Bridge（契約 v1.2 §3.1.1、§0.4 第 6 點；NFR-9.4-04、QA O-11）。

console-api 對 Bridge 的**每個請求**都帶標頭 `X-Trace-Id`。這支純 ASGI 中介層：
  ① 讀請求標頭——缺漏或格式不合時自產 uuid4；
  ② 回應一律回帶同名標頭（SSE 串流的回應也是：標頭在 `http.response.start` 加，與本文無關）；
  ③ 把值放進 contextvar `trace_id_var`，`logsetup` 的日誌 filter 讀它，讓每一行日誌都有 `trace_id`。

為什麼是純 ASGI 而不是 `BaseHTTPMiddleware`：後者會把下游放進另一個 task、並緩衝串流回應，
SSE 事件串流與 contextvar 的傳遞都會壞掉。

「格式不合」的判準：1～64 個字元、只含英數與 `.`、`_`、`-`、首字元為英數。值會原樣寫進每一行日誌，
所以空白、換行、控制字元一律拒收（否則呼叫端可以偽造整行日誌）；console-api 送的是 UUID，必然合格。
"""
from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

TRACE_HEADER = "X-Trace-Id"
#: 沒有請求上下文的日誌行（啟動、關閉、與請求無關的背景執行緒）所帶的值（契約 §3.1.1）。
NO_TRACE = "-"

trace_id_var: ContextVar[str] = ContextVar("bridge_trace_id", default=NO_TRACE)

_TRACE_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}")
_TRACE_HEADER_LOWER = TRACE_HEADER.lower().encode("ascii")


def new_trace_id() -> str:
    return str(uuid.uuid4())


def normalize_trace_id(raw: str | None) -> str:
    """合格就原樣回傳（去前後空白後）；缺漏或不合格＝自產 uuid4。"""
    candidate = (raw or "").strip()
    return candidate if _TRACE_RE.fullmatch(candidate) else new_trace_id()


def trace_id_from_headers(headers: Iterable[tuple[bytes, bytes]]) -> str:
    """ASGI 的標頭名一律小寫；重複出現時取第一個。"""
    for name, value in headers:
        if name == _TRACE_HEADER_LOWER:
            return normalize_trace_id(value.decode("latin-1"))
    return new_trace_id()


class TraceIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":                  # lifespan、websocket 不是請求，原樣放行
            await self.app(scope, receive, send)
            return
        trace_id = trace_id_from_headers(scope.get("headers") or [])
        token = trace_id_var.set(trace_id)

        async def send_with_trace(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [(name, value) for name, value in message.get("headers", [])
                           if name.lower() != _TRACE_HEADER_LOWER]
                headers.append((_TRACE_HEADER_LOWER, trace_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace)
        finally:
            trace_id_var.reset(token)
