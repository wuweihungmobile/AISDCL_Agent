"""compactor.py — compact prompt 組裝 + 連續失敗計數（SD_06 W2-T2-13）。

對應 SD_05 W2 公開 API：
  - build_compact_prompt (W2-1d，純函式無 IO)
  - process_compact_result (M-2 SSOT 雙寫拔除)
  - CompactFailureState (取代直接 attr 存取)

設計原則：
  - 純函式或封閉小狀態；plugin 不持有 infra（PTY 執行由 mixin._execute_prompt 進行）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CompactFailureState:
    """compact 連續失敗計數 SSOT（取代 plugin._compact_failure_count 直存）。"""
    count: int = 0
    critical_threshold: int = 2

    def record_failure(self) -> int:
        self.count += 1
        return self.count

    def reset(self) -> None:
        self.count = 0

    def is_critical(self) -> bool:
        return self.count >= self.critical_threshold


def build_compact_prompt(
    *,
    task: Optional[Any] = None,
    attempt: int = 0,
    failure_summary: str = "",
    global_goal: Optional[str] = None,
    global_goal_anchor_chars: int = 200,
) -> str:
    """SD_05 W2-1d：抽出 compact prompt 構造（純函式，無 IO）。

    對齊 mixin `_send_compact` 內 anchor + prompt 組裝邏輯。實際 PTY 執行由
    呼叫端透過 ExecutorPort / mixin._execute_prompt 處理（avoid plugin 持有 infra）。
    """
    anchor = ""
    if task is not None:
        anchor = (
            "\n=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===\n"
            f"[ACTIVE_TASK] {task.step_id}: {task.name}\n"
            f"[ATTEMPT] {attempt + 1}\n"
        )
        if getattr(task, "expected_output_regex", None):
            anchor += f"[SUCCESS_CONDITION] output must match: {task.expected_output_regex}\n"
        if failure_summary:
            last_err = failure_summary.split("\n")[-1][:120]
            anchor += f"[LAST_FAILURE] {last_err}\n"
        if global_goal:
            _brief = global_goal[:global_goal_anchor_chars] + (
                "…" if len(global_goal) > global_goal_anchor_chars else ""
            )
            anchor += f"[GLOBAL_GOAL] {_brief}\n"
        anchor += "=== END ANCHOR ===\n"

    compact_prompt = (
        "/compact\n"
        "請在壓縮時優先保留：\n"
        "1. 目前正在實作的檔案清單與關鍵函式名稱\n"
        "2. 測試案例的名稱與期望行為\n"
        "3. 最近一次的錯誤訊息（精確的 SyntaxError / AssertionError 位置）\n"
        "可以丟棄：完整的 stdout log、已完成步驟的詳細操作記錄。"
        f"{anchor}"
    )
    if failure_summary:
        compact_prompt += f"\n\n重要：壓縮後必須記住以下當前失敗背景：\n{failure_summary}\n"
    return compact_prompt


def process_compact_result(
    *, state: CompactFailureState, triggered_compact: bool,
) -> bool:
    """SD_05 W2-1d + M-2：compact 後處理 — SSOT 維護於 state。

    回傳：True = compact 成功；False = 連續失敗達上限（caller 須 HALT）。
    """
    if triggered_compact:
        state.record_failure()
        if state.is_critical():
            return False
    else:
        state.reset()
    return True
