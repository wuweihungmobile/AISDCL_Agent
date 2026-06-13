"""IToolInvocation — 工具自主使用 Port（F-A2 / ADR-AGT-001）。

Improving_012 Phase 3（SCG-1 凍結於 SRD_AGT_Phase3_Autonomy.md §1.1）：
  - 單一入口 invoke(ToolRequest) -> ToolResult；kind ∈ {web_search, http_request, send_message}
  - 安全閘為 adapter 責任：預設 deny（config.tool_invocation.enabled=False）+ allowlist
    比對；放行/拒絕皆寫審計 log（經 IObservabilityPort）
  - send_message 僅延伸既有 notification 通道（不開放任意外部端點）
  - 安全閘為純本地判定（domain 比對），不呼叫 Brain

設計原則（data tier ≤ 150）：純 Protocol + frozen dataclass，零實作、零外部依賴。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolRequest:
    """工具呼叫請求（不可變）。

    kind:    "web_search" | "http_request" | "send_message"
    target:  URL / domain / 通道名（allowlist 比對對象）
    payload: 查詢字串 / body / 訊息內容
    """

    kind: str
    target: str
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    """工具呼叫結果（不可變）。

    allowed:  是否通過 allowlist 安全閘
    ok:       實際呼叫成功與否（allowed=False 時恆為 False）
    data:     回傳資料 / 拒絕原因
    audit_id: 審計 log 關聯鍵
    """

    allowed: bool
    ok: bool
    data: dict = field(default_factory=dict)
    audit_id: str = ""


@runtime_checkable
class IToolInvocation(Protocol):
    """工具自主使用抽象（A 能力，F-A2）。"""

    def invoke(self, request: ToolRequest) -> ToolResult:
        """經安全閘呼叫工具；不在 allowlist 即 allowed=False 且不發出任何外部 I/O。"""


__all__ = ["IToolInvocation", "ToolRequest", "ToolResult"]
