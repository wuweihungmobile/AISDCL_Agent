#!/usr/bin/env python3
"""共用 stdout/stderr UTF-8 reconfigure（避免 Windows 非 UTF-8 終端 emoji 崩潰）。

背景（R4 四方複審 S7 發現）：tools/dev_start.py 先前已因 R3 複審 QA 發現而在模組
載入時加了這段保護——Windows 非 UTF-8 終端（如 zh-TW 預設 cp1252 codepage、或任何
非互動/被導向的 stdout）下印 ⚠️/✅/❌ 等符號會直接 UnicodeEncodeError 崩潰
（DEF-101-069）。tools/check_ntfs_paths.py 與 tools/check_script_parity.py 同樣用
裸 print() 輸出這些符號，卻缺這道保護；兩者原本只在 ubuntu-latest／macos-latest
（皆預設 UTF-8 locale）上跑過，從未觸發過，但兩者已於 windows-compat-ci.yml 的
windows-smoke job 接上實際執行（見該檔 R4 段落），在 windows-latest 預設 codepage
非 UTF-8 且未設 PYTHONUTF8/PYTHONIOENCODING 的前提下，幾乎必然重演同款崩潰。

本模組把該段保護收斂為單一 helper，供 dev_start.py / check_ntfs_paths.py /
check_script_parity.py 三支根層 CLI 工具共用 import，避免第三次複製貼上同一段
程式碼。

使用：於各腳本最上方（其他 import 之後、任何 print() 之前）加一行：
    import _stdio_utf8  # noqa: F401  （side effect：reconfigure stdout/stderr）
"""
from __future__ import annotations

import sys


def reconfigure_stdio_utf8() -> None:
    """把 stdout/stderr 重設為 UTF-8, errors="replace"（不支援 reconfigure 的串流
    如測試用 io.StringIO 會被 hasattr 守門跳過，零副作用）。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


# 模組載入時就套用（而非留給呼叫端手動呼叫）：涵蓋所有呼叫路徑，包括未經 main()
# 直接呼叫模組內部函式的呼叫端（例如未來的 import 使用者），與 dev_start.py 原本
# 的保護邏輯等價。
reconfigure_stdio_utf8()
