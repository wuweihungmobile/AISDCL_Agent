#!/usr/bin/env python3
"""dev_start 薄殼 wrapper 退化守門（四方複審 S20，Architect 自評 P2 finding）。

背景：tools/dev_start.py 是本 repo 目前唯一貫徹「薄殼 + Python 核心」模式的
範例 —— tools/dev_start.sh / tools/dev_start.ps1 依其自身 docstring 只做
「選直譯器 → 轉呼叫核心（dev_start.py）→ 視需要啟用 venv」三件事，業務邏輯
全部收斂在 dev_start.py，兩份腳本刻意不互相對照（無 check_script_parity.py
那種雙軌對等機制，因為根本沒有第二套獨立實作要對）。integration_gate /
local_ci_gate 等既有腳本各自用 .sh + .ps1 完整雙寫業務邏輯，是本 repo 既有的
技術債（見根層 docs/06_quality/AutoSDD_Defect_Log.md DEF-101-068 (b)(c)），
分階段收斂是後續獨立的架構工作，不在本檔範圍內。

本檔只守護「已經薄殼化」的 dev_start 對子不再退化回去長業務邏輯 —— 純機械
回歸防護，不是通用 lint：
  1. 行數上限（MAX_LINES）：長業務邏輯幾乎必然先讓行數膨脹。
  2. 業務邏輯樣板關鍵字黑名單：迴圈 / 結構化資料解析等 wrapper 本不該有的樣板。
兩者皆已核對「不會誤中兩份 wrapper 現有內容」（含既有註解／教學文字）。

執行：python tools/check_wrapper_thinness.py
測試：tools/tests/test_check_wrapper_thinness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _stdio_utf8  # noqa: E402,F401  # Windows 非 UTF-8 終端 print(✅/❌) 防崩潰保護

ROOT = Path(__file__).resolve().parent.parent

# 目前 dev_start.sh=78 行、dev_start.ps1=75 行；上限抓 100 行，留自然增長空間
# （新增註解／錯誤訊息），但長出整段新邏輯（迴圈本體、多層業務判斷）時仍會
# 及早示警，不必等到肉眼才發現走鐘。
MAX_LINES = 100

# 業務邏輯樣板關鍵字：出現即代表 wrapper 正在做「選直譯器/轉呼叫/啟用 venv」
# 以外的事 —— 這些字串一旦出現在 dev_start.sh/.ps1，幾乎必然代表邏輯正從
# dev_start.py 外溢回 wrapper（迭代式業務邏輯、結構化資料解析、繞過核心的
# 內嵌邏輯）。逐條皆已核對現有內容不會誤中（含教學用途的 echo/Write-Host
# 文字），新增關鍵字前請比照辦理，避免假警報淹沒真訊號。
_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "tools/dev_start.sh": (
        "while ",       # 迴圈：wrapper 不該有迭代式業務邏輯
        "for ",         # 迴圈（bash for）：同上，與 .ps1 側 foreach ( 對稱收錄
        "for(",         # C-style for 無空格寫法（2026-07-16 四方複審 SD 發現第三輪
                         # 繞過：`for((i=0;i<3;i++))` 的 "for" 緊接 "((" 無空格，"for "
                         # 完全不命中；與 "for " 並收使有無空格皆可攔）
        "jq ",          # JSON 解析（外部工具）
        "python -c",    # 內嵌 Python 業務邏輯，應改為呼叫 dev_start.py 本體
        "python3 -c",   # 同上，版本前綴不同的常見等義寫法（獨立複審發現：原本
                         # 只收 "python -c"，"python3 -c" 不是其子字串，完全繞過）
    ),
    "tools/dev_start.ps1": (
        "ConvertFrom-Json",  # JSON 解析
        "ConvertTo-Json",
        "[System.Text.Json",  # .NET JSON 反序列化（2026-07-16 四方複審 SD 發現第三輪
                               # 繞過：`[System.Text.Json.JsonSerializer]::Deserialize(...)`
                               # 語意等同 ConvertFrom-Json/ConvertTo-Json 但完全不含這兩個
                               # cmdlet 字串）
        "foreach (",         # 迴圈
        "foreach(",          # 無空格寫法（2026-07-16 四方複審 SD 發現第三輪繞過：
                              # `foreach($x in $y){...}` 不含 "foreach ("）
        "while (",
        "for (",             # C-style 迴圈：與 foreach ( 是不同拼法，需各自收錄
                              # （獨立複審發現：原本漏收，"for (" 不是 "foreach (" 的子字串）
        "ForEach-Object",     # 管線 cmdlet 迭代（含業務邏輯常見寫法），語意等同迴圈
                              # （獨立複審發現：原本漏收，別名 "%" 因過於通用會誤中一般
                              # 內容故不收錄，僅收明確的 cmdlet 全名）
        ".ForEach(",          # 陣列 .ForEach() 方法（2026-07-16 四方複審 SD 發現第三輪
                              # 繞過：`(1,2,3).ForEach({...})` 是陣列型別方法而非
                              # ForEach-Object cmdlet，語意等同迴圈但完全不含該字串）
    ),
}


def check_wrapper_thinness() -> list[str]:
    """回傳違規訊息清單；空清單＝全部通過。"""
    problems: list[str] = []
    for rel, forbidden in _FORBIDDEN.items():
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}：檔案不存在（wrapper 被移除或改名？）")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        line_count = len(text.splitlines())
        if line_count > MAX_LINES:
            problems.append(
                f"{rel}：{line_count} 行超過薄殼上限 {MAX_LINES} 行 —— "
                f"業務邏輯應收斂進 tools/dev_start.py，不應長在 wrapper 內"
            )
        for keyword in forbidden:
            if keyword in text:
                problems.append(
                    f"{rel}：出現禁止樣板關鍵字 {keyword!r} —— 疑似業務邏輯"
                    f"外溢回 wrapper，請移至 tools/dev_start.py"
                )
    return problems


def main() -> int:
    problems = check_wrapper_thinness()
    if not problems:
        print("✅ dev_start wrapper 薄殼守門通過（.sh/.ps1 行數與樣板關鍵字皆正常）")
        return 0
    print("❌ dev_start wrapper 薄殼守門失敗：")
    for p in problems:
        print(f"  - {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
