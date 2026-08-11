"""ToolInvocationAdapter — IToolInvocation 安全閘實作（F-A2 / ADR-AGT-001）。

對應 SRD_AGT_Phase3_Autonomy.md §1.2：
  1. 預設 deny：config.tool_invocation.enabled=False 全拒；即使 True，allowlist 空亦全拒。
  2. allowlist 比對：web_search/http_request 比對 target 之 host（domain）；不在 allowlist
     → ToolResult(allowed=False) + 審計 log，不發出任何外部 I/O。
  3. 審計：放行與拒絕皆經 IObservabilityPort.record_event 寫一筆（kind/target/allowed/audit_id）。
  4. send_message：僅延伸既有 notification 通道（utils.notifier.notify，notification_plugin 同源），
     不開放任意外部端點、不 import notification plugin（SRD §0 精化：EventBus 為 phase-based
     非通用訊息匯流排，改委派 notifier 達成同一原意）。
  5. web_search/http_request：預設 no-op stub（不做真實網路 I/O；安全閘為本 adapter 核心價值）；
     真實 I/O handler 可由建構式注入（保留擴充點）。
  6. 安全閘為純本地判定（host 比對），不呼叫 Brain。

設計原則（adapter tier ≤ 400）。
"""
from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping
from urllib.parse import urlparse

from ...core.ports.observability import IObservabilityPort, NullObservability
from ...core.ports.tool_invocation import ToolRequest, ToolResult
from ...utils.notifier import notify

_KNOWN_KINDS = frozenset({"web_search", "http_request", "send_message"})

# 真實 I/O handler 型別：放行後執行，回傳 (ok, data)
_Handler = Callable[[ToolRequest], "tuple[bool, dict]"]


class ToolInvocationAdapter:
    """IToolInvocation 安全閘 adapter（預設 deny + allowlist + 審計）。"""

    def __init__(
        self,
        enabled: bool = False,
        allowlist: list[str] | None = None,
        observability: IObservabilityPort | None = None,
        notifier: Callable[..., None] | None = None,
        handlers: Mapping[str, _Handler] | None = None,
        notification_enabled: bool = True,
    ):
        # 防 Mock truthy：嚴格 is True（比照 alert_ladder.py:39）
        self._enabled = enabled is True
        self._allowlist = [a.strip().lower() for a in (allowlist or []) if a and a.strip()]
        self._obs = observability or NullObservability()
        self._notify = notifier or notify
        # 🔴 R84（W9 交棒）：`notify()` 的 `enabled` 預設 True ⇒ 此前 `self._notify(title, message)`
        # 漏傳它，本 adapter 這條路徑**結構上無視 `config.notification.enabled`**。今天沒被看見
        # 只因上一層預設 deny（`tool_invocation.enabled=False`）把它整條遮住——遮住不等於修好，
        # 開啟工具閘的那一刻兩個開關就會各說各話（使用者關掉通知，工具仍彈窗）。
        # 預設保持 True＝維持既有呼叫端（未指定者）的行為不變；wiring 一律注入 cfg 值。
        self._notification_enabled = notification_enabled is True
        self._handlers = dict(handlers or {})

    # ──────────────────────────────────────────────
    # IToolInvocation
    # ──────────────────────────────────────────────
    def invoke(self, request: ToolRequest) -> ToolResult:
        audit_id = uuid.uuid4().hex[:12]
        allowed = self._is_allowed(request)
        # 審計：放行與拒絕皆落筆（紀律：可稽核）
        self._obs.record_event(
            "tool_invocation",
            {
                "kind": request.kind,
                "target": request.target,
                "allowed": allowed,
                "audit_id": audit_id,
            },
        )
        if not allowed:
            return ToolResult(
                allowed=False,
                ok=False,
                data={"reason": "denied_by_allowlist"},
                audit_id=audit_id,
            )
        # 放行 → 分派
        if request.kind == "send_message":
            ok = self._send_message(request)
            return ToolResult(allowed=True, ok=ok, data={"sent": ok}, audit_id=audit_id)
        # web_search / http_request：注入 handler 優先，否則預設 no-op stub
        handler = self._handlers.get(request.kind)
        if handler is not None:
            ok, data = handler(request)
            return ToolResult(allowed=True, ok=ok, data=data, audit_id=audit_id)
        return ToolResult(
            allowed=True, ok=False, data={"stub": True}, audit_id=audit_id
        )

    # ──────────────────────────────────────────────
    # 安全閘（純本地，不呼叫 Brain）
    # ──────────────────────────────────────────────
    def _is_allowed(self, request: ToolRequest) -> bool:
        if not self._enabled:
            return False
        if not self._allowlist:
            return False
        if request.kind not in _KNOWN_KINDS:
            return False
        token = self._match_token(request)
        if not token:
            return False
        # 精確命中或子域命中（host 結尾於 .allow 項）
        return any(
            token == allow or token.endswith("." + allow) for allow in self._allowlist
        )

    @staticmethod
    def _match_token(request: ToolRequest) -> str:
        """取得 allowlist 比對對象：web/http 用 URL host；send_message 用通道名。"""
        target = (request.target or "").strip().lower()
        if request.kind in ("web_search", "http_request"):
            parsed = urlparse(target if "//" in target else "//" + target)
            return parsed.hostname or ""
        return target  # send_message：通道名整串比對

    def _send_message(self, request: ToolRequest) -> bool:
        """延伸既有 notification 通道（notification_plugin 同源 utils.notifier.notify）。"""
        payload = request.payload or {}
        title = str(payload.get("title", "AutoClaude — 工具訊息"))
        message = str(payload.get("message", request.target))
        try:
            self._notify(title, message, enabled=self._notification_enabled)
            return True
        except Exception:
            return False


__all__ = ["ToolInvocationAdapter"]
