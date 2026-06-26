"""_compact_prompt — compact prompt 組裝 SSOT（improving_80 W-80-1 / DEF-78-001 收尾）。

職責（純函式、無 IO、無狀態）：
  - 組裝送給 executor 的 ``/compact`` 提示，含結構化保留策略與可選的 MEMORY ANCHOR
    （task/attempt/成功條件/last_failure/global_goal），確保壓縮後關鍵任務記憶存活。

背景（improving_80 W-80-1）：本函式原住於 ``plugins/token_guard/compactor.py``，但
production Kernel compact 路徑（``core/_token_compactor.perform_compact``）需要它，而 core
不可 import plugin（importlinter Rule 2）。故將此**純函式**上移為 core 共享 SSOT——core 與
plugin 共用單一實作（plugin 端 re-export 保既有 caller 不破），消除 DRY 隱憂、相依方向
plugin→core 合法。``CompactFailureState``/``process_compact_result``（plugin 專用狀態）仍留
``compactor.py``。

設計原則：
  - 純函式：無 IO、無狀態、無 plugin/infra import（維持 core-purity）。
  - 實際 /compact 執行由呼叫端（core ``perform_compact`` 或棄用路徑 mixin）處理。
"""
from __future__ import annotations

from typing import Any, Optional


def build_compact_prompt(
    *,
    task: Optional[Any] = None,
    attempt: int = 0,
    failure_summary: str = "",
    global_goal: Optional[str] = None,
    global_goal_anchor_chars: int = 200,
) -> str:
    """SD_05 W2-1d（improving_80 上移至 core）：compact prompt 構造（純函式，無 IO）。

    task=None 時不附加 anchor，退回基本保留策略 prompt；task 給定時附加
    ``=== MEMORY ANCHOR (MUST SURVIVE COMPRESSION) ===`` 區塊保留任務記憶。
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
