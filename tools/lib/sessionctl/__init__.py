"""sessionctl：session 掌控與切換（續跑成本選路、過期 session 不續跑、交接包、名冊、模型建議）。

設計全文＝ADR-XPLAT-004 §2.13；規格＝docs/03_testing/contracts/TCS-SessionCtl-20261113.md。
落點照 docs/02_architecture/Root_Layout_and_Module_Placement.md：函式庫在本套件、入口薄殼
`tools/sessionctl.py`、測試 `tools/tests/test_sessionctl_*.py`。

🔴 `tools/lib/*` 的同層模組一律以**裸名** import（模組身分只有一份，hook／planner／測試
monkeypatch 同一個物件）；套件自己以 `lib.sessionctl.<檔>` 被 import（入口檔 `tools/sessionctl.py`
與本套件同名，裸名 `import sessionctl` 會被入口檔遮住），所以這裡把 `tools/lib` 補進
`sys.path`（只在缺席時 append，不改既有優先序）。
"""
from __future__ import annotations

import sys
from pathlib import Path

_LIB = str(Path(__file__).resolve().parents[1])
if _LIB not in sys.path:
    sys.path.append(_LIB)
