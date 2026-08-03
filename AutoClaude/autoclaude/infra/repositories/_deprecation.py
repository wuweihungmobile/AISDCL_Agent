"""四個 state repository 後端共用的 deprecation shim（SD_06 W5-T5-8）。"""
from __future__ import annotations

import os
import warnings

# 原本 dual / file / in_memory / pg 四支各自帶一份**逐字相同**的 8 行區塊
# （複製貼上而非介面多型），改動一處就得記得改四處。收斂為本自由函式。
_LOAD_CHECKPOINT_MSG = (
    "load_checkpoint(playbook_id) is deprecated since SD_06 W5; "
    "use load_latest_by_playbook(playbook_id) instead."
)


def warn_load_checkpoint_deprecated() -> None:
    # 預設關閉、由 env 啟用（SD_Improving_03 W1b：CI 於 W4 才開 strict）。
    # stacklevel=3 而非原地的 2：多了本函式這一層，3 才會指回 load_checkpoint 的
    # **呼叫端**（即原本 stacklevel=2 所指的同一個 frame）。
    if os.environ.get("AUTOCLAUDE_DEPRECATION_WARN") == "1":
        warnings.warn(_LOAD_CHECKPOINT_MSG, DeprecationWarning, stacklevel=3)
