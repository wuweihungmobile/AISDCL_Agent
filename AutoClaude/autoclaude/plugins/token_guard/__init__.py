"""token_guard package — Token / Context 用量保護 Plugin 拆分（SD_06 W2-T2-13）。

拆分理由：
  原 `autoclaude.plugins.token_guard_plugin`（283 行）超過 250 LOC budget。
  依 SD_05 W0 T0-6 設計拆 5 子模組：

  - thresholds.py   — 純函式門檻判斷（動態 compact / halt）
  - compactor.py    — compact prompt 組裝 + 失敗計數狀態
  - git_verifier.py — git diff 驗證修正是否實際套用
  - watcher.py      — token 觀測 + per-step config 解析
  - policy.py       — TokenGuardPlugin 主類（組合上述子模組）

對應：
  - SD_Improving_06.md v1.2 §6.5 AC1-3（`ls token_guard/ | wc -l ≥ 5`）
  - SD_Improving_05.md v2.1 W2 SA-Minor LOC 警示
  - SD_Improving_02.md v1.1 §3.5 表格第 1 列（priority=30）

backward compat：
  `autoclaude.plugins.token_guard_plugin` 仍可 import TokenGuardPlugin
  （改為 shim，re-export 自本 package）。
"""
from .policy import TokenGuardPlugin

__all__ = ["TokenGuardPlugin"]
