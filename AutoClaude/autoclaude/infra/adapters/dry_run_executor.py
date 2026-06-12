"""DryRunExecutor — 測試用 IExecutor，不啟動真實 CLI。

依 PlaybookTask.expected_output_regex 合成輸出（regex escape 去除），
等同 _runner_impl.py dry_run 路徑的行為。

用途：
  - tests/equivalence/test_kernel_snapshot.py — Kernel Stage A 等價測試
  - 任何需要 fake 執行但不想啟動 PTY 的整合測試
"""
from __future__ import annotations

import re
from typing import Optional

from ...core.ports.executor import (
    ExecutionEvent,
    ExecutionEventCallback,
    ExecutionEventKind,
    ExecutionOutput,
)


class DryRunExecutor:
    """IExecutor 實作：回傳與 expected_output_regex 匹配的合成文字。

    初始化時傳入 step_id → keyword 映射（step_outputs）。
    若該 step_id 無對應 keyword，預設回傳 "dry-run-pass"。
    """

    def __init__(self, step_outputs: Optional[dict[str, str]] = None):
        self._outputs: dict[str, str] = step_outputs or {}
        # SD_Improving_06 W1 T1-2：interrupt 旗標
        self._interrupt_requested: bool = False

    @staticmethod
    def keyword_from_regex(regex: Optional[str]) -> str:
        """從 expected_output_regex 提取可匹配的文字（去除 regex escape）。"""
        if not regex:
            return "dry-run-pass"
        return re.sub(r"\\(.)", r"\1", regex)

    def send_interrupt(self, reason: str = "") -> bool:
        """測試夾具：標記旗標，下次 execute 立即回 completed=False。"""
        self._interrupt_requested = True
        return True

    def execute(
        self,
        prompt: str,
        *,
        maintain_context: bool = True,
        timeout: int = 600,
        label: str = "",
        on_event: Optional[ExecutionEventCallback] = None,
    ) -> ExecutionOutput:
        # SD_Improving_06 W1 T1-2：interrupt 短路
        if self._interrupt_requested:
            self._interrupt_requested = False
            if on_event is not None:
                try:
                    on_event(ExecutionEvent(
                        kind=ExecutionEventKind.COMPLETION,
                        payload={"exit_code": 1, "completed": False, "text_len": 0},
                        sequence=1,
                    ))
                except Exception:
                    pass
            return ExecutionOutput(text="", exit_code=1, completed=False)

        keyword = self._outputs.get(label, "dry-run-pass")
        text = f"[dry-run] {keyword}"
        if on_event is not None:
            try:
                on_event(ExecutionEvent(
                    kind=ExecutionEventKind.COMPLETION,
                    payload={"exit_code": 0, "completed": True, "text_len": len(text)},
                    sequence=1,
                ))
            except Exception:
                pass
        return ExecutionOutput(text=text)
