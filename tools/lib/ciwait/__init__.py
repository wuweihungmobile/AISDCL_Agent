"""推送後等 GitHub CI 的專用等待工具。

本體在 `lib/ciwait/core.py`，命令列薄殼在 `tools/ci_wait.py`；落點見根層模組落點 SSOT。

`tools/lib/*` 的同層模組一律以裸名 import（見 `lib/sessionctl/__init__.py`），所以這裡把 `tools/lib`
補進 `sys.path`（只在缺席時 append）；本套件用它取痕跡目錄 SSOT `endurance_env.trace_dir()`。
"""
from __future__ import annotations

import sys
from pathlib import Path

_LIB = str(Path(__file__).resolve().parents[1])
if _LIB not in sys.path:
    sys.path.append(_LIB)
