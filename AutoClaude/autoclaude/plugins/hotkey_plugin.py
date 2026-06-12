"""HotkeyPlugin — 取代 PlaybookRunner 內 `if self._hotkey.triggered` 散在 3 處的檢查。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 8 列（priority=10）
  - SD_Improving_02.md v1.1 §2.5 W5 #2（低測試耦合度）

訂閱 phase：
  - PRE_STEP      → 步驟開始前檢查 ESC+F12 是否被按下
  - PRE_ATTEMPT   → 每次 attempt 前檢查
  - 觸發時回傳 VetoResult，中止當前 phase 並由 Kernel 結束 Playbook
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase, VetoResult


class HotkeyPlugin:
    """ESC+F12 全域中斷熱鍵 Plugin。"""

    PRIORITY = 10  # 系統級 veto / 中斷檢查（01 v1.1 §3.4.2）

    def __init__(self, hotkey_handler: Any):
        """
        Args:
            hotkey_handler: 任何擁有 `.triggered` 屬性的物件
                            （HotkeyHandler 或測試用 Mock）
        """
        self._hotkey = hotkey_handler

    def name(self) -> str:
        return "hotkey"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.PRE_STEP, KernelPhase.PRE_ATTEMPT]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if not getattr(self._hotkey, "triggered", False):
            return None

        # 中斷被觸發 → veto 當前 phase
        step_id = ctx.task.step_id if ctx.task is not None else "N/A"
        return VetoResult(
            contributor=self.name(),
            reason=f"ESC+F12 中斷觸發於 {ctx.phase.value}（step={step_id}）",
        )
