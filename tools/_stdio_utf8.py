#!/usr/bin/env python3
"""**強制 stdout/stderr 為 UTF-8 的唯一實作**（import 期即生效）。

背景（R4 四方複審 S7 發現）：tools/dev_start.py 先前已因 R3 複審 QA 發現而在模組
載入時加了這段保護——Windows 非 UTF-8 終端（如 zh-TW 預設 cp1252 codepage、或任何
非互動/被導向的 stdout）下印 ⚠️/✅/❌ 等符號會直接 UnicodeEncodeError 崩潰
（DEF-101-069）。tools/check_ntfs_paths.py 與 tools/check_script_parity.py 同樣用
裸 print() 輸出這些符號，卻缺這道保護。

使用：於各腳本最上方（其他 import 之後、任何 print() 之前）加一行：
    import _stdio_utf8  # noqa: F401  （side effect：強制 stdout/stderr 為 UTF-8）

═══════════════════════════════════════════════════════════════════════════════
🔴 R75 去重：本檔是**唯一實作**，`tools/lib/platform_utils.init_utf8_streams` 委派到它
═══════════════════════════════════════════════════════════════════════════════
去重前，同一份知識有**兩個各自宣稱是 SSOT 的家**：本檔的 `reconfigure_stdio_utf8()`
（`.reconfigure()` 就地改、import 期生效）與 `tools/lib/platform_utils.py` 的
`init_utf8_streams()`（`io.TextIOWrapper` 換掉串流、只在 `__main__` 呼叫）。實作／啟用
時機／對測試替身的行為三者皆不同，消費端分屬兩群（本檔 15 支根層 tools／那支 8 支
AutoClaude hook 與工具），**換用另一支會靜默改變行為**，而兩把鎖都只守自己那一支。
R74 的 P0（`sys.stderr` 預設 `errors='backslashreplace'` 讓 hook 中文指引在非 CJK
codepage 降解成 `\\uXXXX` 字面）正好就落在這一層。

🔴 **為什麼實作住這裡、而不是住 `tools/lib/`（R75 第一版做錯、當回合被實測打回）**：
本檔的既有契約**包含「被複製到別處單獨執行」**——`AISDLC_SDD/scripts/tests/`
的 `test_copy_on_evolve.py`／`test_ntfs_length_gate.py` 會把 `tools/check_ntfs_paths.py`
連同本檔複製進一個 tmp 沙箱 repo（**不含 `tools/lib/`**）再以子行程執行。R75 第一版把
實作搬去 `tools/lib/platform_utils.py`、本檔改成 `from platform_utils import …`，於是
沙箱裡 import 期 `ModuleNotFoundError`，6 支測試當場紅（實測歸因：複製到 tmp 再 import
即重現）。
⇒ **可搬遷性是硬約束**：一支「被複製到任意位置仍要能用」的基礎件，不能相依於 repo 佈局。
   能滿足它的方案只有一個——**自我完備的那一支就是 SSOT**，另一支去委派。故本檔：
     · **只依賴 stdlib（`io`／`sys`），一個本地 import 都不准有**；
     · 不讀 `__file__`、不推導 repo 根（那些都是 repo 佈局假設的變體）。
   這兩條由 `tools/tests/test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation`
   釘住（含「複製到 tmp 後以 cp1252 子行程實跑中文不降解」的可搬遷契約鎖）。
"""
from __future__ import annotations

import io
import sys


def reconfigure_stdio_utf8() -> None:
    """把 sys.stdout/stderr 強制為 UTF-8（`errors="replace"`），不分平台。

    R16 訂正（原記於 `platform_utils.init_utf8_streams`，去重後與實作一起搬來這裡）：
    最初曾誤判「POSIX 終端機預設已是 UTF-8，故只需在 Windows 上處理」而加了
    `sys.platform != "win32": return` 守衛——但
    `AutoClaude/tests/tools/hooks/test_hooks_stdin_utf8.py` 的
    `test_enforce_docs_path_blocks_chinese_path_under_cp950` 證明那是錯的：呼叫端可在
    **任何**平台以 `PYTHONIOENCODING=cp950` 覆寫預設值來模擬 zh-TW Windows pipe，此時
    POSIX 上若不強制改，阻斷級 hook 的中文錯誤訊息會被以覆寫編碼寫出而讀成亂碼。
    故本函式對所有平台皆無條件生效。

    手法是去重前兩份實作的**嚴格聯集**（三條分支，缺一即有行為退化）：
      ① 有 `.reconfigure` ⇒ **就地改**。保留串流物件同一性、保留原本的
         `line_buffering`／`write_through`——`io.TextIOWrapper(sys.stdout.buffer, …)`
         一律得到 `line_buffering=False`，對互動終端下的 `tools/dev_start.py` 是可見的
         輸出交錯退化。`OSError`／`ValueError` 一律吞掉（被導向的 stdout 在某些平台
         reconfigure 會失敗，本檔既有契約如此）。
      ② 沒有 `.reconfigure` 但有 `.buffer` ⇒ 包 wrapper。這一路是去重前 8 支
         AutoClaude hook 走的唯一路徑，保留它，故對「非 TextIOWrapper 的 stdout」
         仍有作用。
      ③ 兩者皆無（如測試替身 `io.StringIO`）⇒ 安全 no-op，不拋 AttributeError。

    冪等：重複呼叫無副作用（`platform_utils.init_utf8_streams` 委派時會再呼叫一次）。
    只應在 `__main__` 進入點（或本檔 import 期）生效，避免污染 pytest 的 stdout 擷取。
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:  # pragma: no cover - pythonw 等無 stdio 的執行環境
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
            continue
        buffer = getattr(stream, "buffer", None)
        if buffer is None:
            continue
        try:
            setattr(sys, name, io.TextIOWrapper(buffer, encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001 — 保護性程式碼不得反過來讓呼叫端崩潰
            pass


# 模組載入時就套用（而非留給呼叫端手動呼叫）：涵蓋所有呼叫路徑，包括未經 main()
# 直接呼叫模組內部函式的呼叫端，與 dev_start.py 原本的保護邏輯等價。
reconfigure_stdio_utf8()
