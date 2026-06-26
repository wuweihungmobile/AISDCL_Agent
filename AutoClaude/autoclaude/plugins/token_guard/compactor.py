"""compactor.py — compact 連續失敗計數 + compact prompt 組裝 re-export（SD_06 W2-T2-13）。

對應 SD_05 W2 公開 API：
  - build_compact_prompt (W2-1d，純函式無 IO；improving_80 W-80-1 上移至
    ``autoclaude.core._compact_prompt``，本檔 re-export 保既有 caller 不破，使 core
    compact 路徑與 plugin 共用單一 SSOT)
  - process_compact_result (M-2 SSOT 雙寫拔除)
  - CompactFailureState (取代直接 attr 存取)

設計原則：
  - 純函式或封閉小狀態；plugin 不持有 infra（PTY 執行由 mixin._execute_prompt 進行）
"""
from __future__ import annotations

from dataclasses import dataclass

# improving_80 W-80-1：build_compact_prompt 上移至 core 共享 SSOT；此處 re-export 保
# 既有 caller（policy.py / 4 測試檔）`from ...compactor import build_compact_prompt` 不破。
from autoclaude.core._compact_prompt import build_compact_prompt  # noqa: F401


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
