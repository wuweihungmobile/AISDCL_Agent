"""CheckpointPlugin package（SD_Improving_05 W3-2 拆 package）。

由 ``checkpoint_plugin.py`` 拆分而來：259 行單檔 + W3 新增 4 公開方法（~120 行）
合計約 380 行已超過 250 行 LOC 預算 → 必須拆 package。

子模組設計（每 ≤ 80 行）：
  - plugin.py       主類 CheckpointPlugin + on_event 分派 + 公開 API
  - _builder.py     _build_checkpoint（從 EventBus / counter snapshot 取資料）
  - _interrupt.py   save_interrupt_checkpoint（ESC+F12 中斷 W3-1c）
  - _token_halt.py  handle_token_halt（TOKEN_HALT 流程 W3-1b）
  - _evolution.py   save_evolution_resume_checkpoint（演化後 W3-1a）
  - _escalation.py  save_escalation_dump（ESCALATION dump W3-1d）

對外 import 路徑維持 ``from autoclaude.plugins import CheckpointPlugin``；
舊路徑 ``autoclaude.plugins.checkpoint_plugin`` 為 backward compat re-export。
"""
from __future__ import annotations

from .plugin import CheckpointPlugin

__all__ = ["CheckpointPlugin"]
