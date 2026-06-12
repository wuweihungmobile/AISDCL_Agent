"""token_guard_plugin — backward-compat shim（SD_06 W2-T2-13）。

DEPRECATED：實作已搬至 `autoclaude.plugins.token_guard` package（5 子模組）：
  - thresholds / compactor / git_verifier / watcher / policy

保留本模組以維持既有 30+ 測試 patch path：
  `patch("autoclaude.plugins.token_guard_plugin.TokenGuardPlugin.X")`。

新程式碼請直接使用：
  from autoclaude.plugins.token_guard import TokenGuardPlugin

對應：
  - SD_Improving_06.md v1.2 §6.5 AC1-3
  - SD_Improving_05.md v2.1 W2 SA-Minor LOC 警示
"""
from __future__ import annotations

from .token_guard import TokenGuardPlugin

__all__ = ["TokenGuardPlugin"]
