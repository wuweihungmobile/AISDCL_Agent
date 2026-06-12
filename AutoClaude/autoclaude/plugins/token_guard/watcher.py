"""watcher.py — token 觀測 + per-step config 解析（SD_06 W2-T2-13）。

對應 SD_05 W2 公開 API：
  - observe_token_line (W2-1e，純函式)
  - resolve_per_step_cfg (W2-4 M-7，per-step token_guard override)
"""
from __future__ import annotations

from typing import Any, Optional

from ...utils.config import TokenGuardConfig


def observe_token_line(
    *,
    pct: Optional[float],
    peak_pct: float,
    triggered_compact: bool,
    triggered_halt: bool,
    cfg: TokenGuardConfig,
) -> tuple[float, bool, bool]:
    """SD_05 W2-1e：吸收 `_execute_prompt` 中的 token watch 邏輯（純函式）。

    參數：
      - pct: extract_context_pct 解析出的 context %（可能 None）
      - peak_pct / triggered_compact / triggered_halt: 當前累積狀態
      - cfg: TokenGuardConfig 提供 halt / compact 門檻

    回傳：(new_peak_pct, new_triggered_compact, new_triggered_halt)
    """
    if pct is None or pct <= peak_pct:
        return peak_pct, triggered_compact, triggered_halt
    new_peak = pct
    new_halt = triggered_halt
    new_compact = triggered_compact
    if pct >= cfg.halt_threshold_pct:
        new_halt = True
    elif pct >= cfg.compact_threshold_pct:
        new_compact = True
    return new_peak, new_compact, new_halt


def resolve_per_step_cfg(
    *, global_cfg: TokenGuardConfig, task: Optional[Any] = None,
) -> TokenGuardConfig:
    """SD_05 W2-4 (M-7)：per-step token_guard override 解析。

    優先序：task.token_guard > global_cfg

    若 task.token_guard 為 dict，將其欄位疊加至 global 並驗證；確保 60+ 現有
    YAML（無 token_guard 欄位）行為不變。
    """
    if task is None:
        return global_cfg
    override = getattr(task, "token_guard", None)
    if not override or not isinstance(override, dict):
        return global_cfg
    merged_data = global_cfg.model_dump()
    merged_data.update(override)
    return TokenGuardConfig(**merged_data)
