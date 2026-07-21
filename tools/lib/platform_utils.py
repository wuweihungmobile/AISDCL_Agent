#!/usr/bin/env python3
"""集中式平台判斷模組（monorepo 根層共用，AutoClaude 與 AISDLC_SDD 兩側皆可用）。

收斂背景：`_init_utf8_streams()` 曾被複製貼上到至少 8 個檔案，其中 6 份漏了
`sys.platform != "win32"` 守衛，在 macOS/Linux 上也會無條件把 sys.stdout/stderr
換成新的 TextIOWrapper——POSIX 終端機預設已是 UTF-8，重新包裝除了改變
buffering 行為（TextIOWrapper 預設非 line-buffered）、丟棄原始 stream 物件外
沒有任何好處，是純粹的行為分歧風險。本模組以「有守衛」版本為唯一正確實作。

只依賴 stdlib：供 AutoClaude/tools/hooks/ 下的 hook 腳本以
`sys.path.insert(0, str(repo_root / "tools" / "lib"))` 方式 import——hook 腳本
執行環境不保證能 import 完整 autoclaude 套件，僅假設 stdlib + repo 根目錄可達。
"""
from __future__ import annotations

import io
import sys


def is_windows() -> bool:
    return sys.platform == "win32"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_posix() -> bool:
    return sys.platform != "win32"


def os_label() -> str:
    """三態標籤：windows/mac/linux（同 tools/dev_start.py 的 `_now_label()`）。"""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def init_utf8_streams() -> None:
    """把 sys.stdout/stderr 重新包裝為強制 UTF-8，不分平台。

    R16 訂正：本函式最初收斂時誤判「POSIX 終端機預設已是 UTF-8，故只需在
    Windows 上包裝」，加了 `sys.platform != "win32": return` 守衛——但
    `tests/tools/hooks/test_hooks_stdin_utf8.py::test_enforce_docs_path_blocks_chinese_path_under_cp950`
    證明這是錯的：呼叫端可在任何平台以 `PYTHONIOENCODING=cp950`（或其他非 UTF-8
    編碼）覆寫預設值來模擬 zh-TW Windows pipe，此時 POSIX 上若不重新包裝，
    hook 阻斷訊息裡的中文路徑會被以覆寫編碼寫出、造成解碼方讀到亂碼——對
    「阻斷級守門的錯誤訊息必須保真」這個安全相關情境而言是真實回歸，不是
    理論風險。故本函式對所有平台皆無條件包裝（恢復八份複製貼上版本中原本
    6 份的行為，即 R16 收斂前的多數版本；當初被當作「正確」沿用的少數
    2 份守衛版本才是例外）。

    只應在 `__main__` 進入點呼叫，避免污染 pytest 對 stdout/stderr 的擷取。
    """
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass
