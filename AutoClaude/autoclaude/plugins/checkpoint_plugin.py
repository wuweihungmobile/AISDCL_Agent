"""checkpoint_plugin — backward compat re-export（SD_Improving_05 W3-2）。

⚠️ DEPRECATED：原 259 行單檔已拆分至 ``autoclaude.plugins.checkpoint`` package。
本檔僅維持原 import 路徑相容；W6 評估後可刪除（屆時 30+ 測試與下游若全部
改為新路徑，可直接 ``rm`` 此檔）。

新代碼請改用：

    from autoclaude.plugins import CheckpointPlugin
    # 或
    from autoclaude.plugins.checkpoint import CheckpointPlugin

對應 §6.3 W6 拔除清單第 8 項（W3 新增）。
"""
from __future__ import annotations

from .checkpoint import CheckpointPlugin

__all__ = ["CheckpointPlugin"]
