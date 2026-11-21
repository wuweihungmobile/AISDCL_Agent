"""openitems：未結項登記簿 OIR（工作推進軸；DES WorkProgress_Axis_Design §3）。
規格＝docs/03_testing/contracts/TCS-WorkProgress-20261119.md。

落點照 docs/02_architecture/Root_Layout_and_Module_Placement.md：函式庫在本套件、入口薄殼
`tools/openitems.py`、測試 `tools/tests/test_openitems_*.py`、協定資料
`docs/06_quality/OpenItems_Protocol/`。

🔴 `tools/lib/*` 的同層共用單檔一律以 `from lib import <名>` 取得；本套件自己以
`lib.openitems.<檔>` 被 import，所以這裡把 `tools/lib` 補進 `sys.path`（只在缺席時 append）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_LIB = str(Path(__file__).resolve().parents[1])
if _LIB not in sys.path:
    sys.path.append(_LIB)
