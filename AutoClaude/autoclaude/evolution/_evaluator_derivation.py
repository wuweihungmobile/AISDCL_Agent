"""
共用工具：從完整 evaluator_command 推導 SPLIT_STEP Part A 輕量評估指令。

Gap-026-A（PlaybookEvolver）與 Gap-026-B（MinimaxEvolver）原各自維護一份
100% 重複的 `_derive_part_a_evaluator` 實作（R50 四方審查發現的 SSOT 違反，
P2）：同一個 POSIX-only `{ cmd; } || true` bug 需在兩個檔案分別發現、
分別修復。本模組將邏輯抽成單一共用函式，兩個 Evolver 的
`_derive_part_a_evaluator` staticmethod 皆委派至此，往後只需修一處。
"""
from __future__ import annotations

import base64
import re
import sys


def derive_part_a_evaluator(full_evaluator: str | None) -> str | None:
    """
    從完整 evaluator_command 推導 Part A 輕量評估指令。
    策略：
    - pytest 指令 → 改為 --collect-only（僅確認測試可被收集）
    - 其他指令 → 執行原指令但無條件回傳成功（確保不因 Part A 僅涵蓋一半任務而誤報失敗）
    - 無 evaluator → 回傳 None

    跨平台注意：evaluator.py 以 subprocess.run(shell=True) 執行，Windows 走 cmd.exe、
    POSIX 走 /bin/sh，兩者語法不相容。舊實作 `{ cmd; } || true` 為 POSIX 專屬分組語法，
    cmd.exe 不支援（`{` 會被當成不存在的命令）。改以 `python -c` 包裝：以 base64 編碼
    原指令避開任何引號/特殊字元造成的殼層轉義問題，內部仍以 subprocess.run(shell=True)
    交給平台原生殼執行 cmd 本身（保留原指令可用任意殼語法的彈性），並無條件 sys.exit(0)。

    R51 修正：包裝殼一律用 `sys.executable`（本行程實際執行的 Python 直譯器絕對路徑）
    而非裸字面值 `python`。macOS /usr/bin 與多數現代 Linux distro 預設 PATH 上並無
    `python` 別名（僅有 `python3`），裸字面值在該類環境會以 shell rc=127
    「command not found」收場，打破本函式「非 pytest 指令必須無條件回傳成功」的契約。
    以雙引號包住路徑以相容路徑含空白（如 Windows "Program Files"）。
    """
    if not full_evaluator:
        return None
    cmd = full_evaluator.strip()
    if re.search(r'\bpytest\b', cmd):
        # pytest → 只做 collect-only 確認語法正確
        base = re.sub(r'\s+-[kxvsq]\S*', '', cmd)
        base = re.sub(r'\s+--tb=\S+', '', base)
        return base.split()[0] + " --collect-only"
    payload = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
    python_bin = sys.executable or "python3"
    return (
        f'"{python_bin}" -c "import subprocess, base64, sys; '
        f"subprocess.run(base64.b64decode('{payload}').decode('utf-8'), shell=True); "
        'sys.exit(0)"'
    )
