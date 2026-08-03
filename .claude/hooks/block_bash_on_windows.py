#!/usr/bin/env python
"""PreToolUse 守衛：Windows 上禁用 Bash 工具（根 CLAUDE.md〈Windows 側單一載具原則〉鐵律一）。

WHY
---
R71（Windows 真機輪）逐筆歸因 8 筆操作失誤，**5 筆源於同時操作兩個 shell 載具**：
每下一個指令都要先決定「用哪個 shell／什麼編碼／哪種路徑格式／cwd 在哪／這支腳本
拒不拒絕這個載具」，而被這些決策擠掉的注意力，正是「查權威源再宣稱」那類紀律失守
的原因——所以連平台無關的錯，密度也在 Windows 側偏高。

掌舵者 2026-08-03 直接指令：「只使用 PowerShell 5.1, 不用 Git Bash」。

**為何需要機械物而不是文件**：規則寫進根 CLAUDE.md 之後，同一個回合內仍再犯一次
（用 Bash 跑 awk/python 算行數）。CLAUDE.md 由 session **開場**載入，session 中途訂立
的規則對「當下的模型」只能靠主動記得，而主動記得正是上述決策負荷會擠掉的東西。
掌舵者兩度指出「你還是沒有遵守」後，改以 PreToolUse 阻斷落實。

實證的兩起事故（皆為編碼邊界，方向相反）：
  · Git Bash `grep` 讀 CP950 的 PowerShell 輸出 → 命中 0 → **誤判「沒有失敗行」**
  · `windows_smoke_local.ps1` 經 Git Bash 呼叫 → 被 MSYS 守衛擋下 rc=1（DEF-101-511 刻意設計）

行為
----
· Windows（os.name == 'nt'）收到 Bash 工具呼叫 → exit 2 阻斷，stderr 給替代指引。
· 其他平台 → exit 0 放行。**mac/Linux 上 bash 才是正確載具，本守衛不得誤傷**
  （本 repo 雙平台對稱紀律：單平台規則不可無條件套到另一平台，DEF-101-766 即此類教訓）。
· 任何非預期例外 → exit 0（fail-open）。理由見 .claude/settings.json description 記載的
  P0：hook 誤觸 PreToolUse deny 會把**所有**工具硬鎖死，守衛自身絕不可成為那種故障源。

繞道
----
確有必要在 Windows 跑 bash（例如執行一支 .sh）時，正確作法是**在 PowerShell 工具內**
呼叫 `bash <script>`——那是「執行一支 .sh」而非「以 Bash 為載具」，同
tools/git-hooks/pre-push 既有作法。本守衛只攔 Bash **工具**，攔不到也不該攔那條路。
"""

from __future__ import annotations

import json
import os
import sys

_GUIDANCE = """🔴 Windows 上已禁用 Bash 工具（根 CLAUDE.md〈Windows 側單一載具原則〉鐵律一）。

改用 **PowerShell 工具**：
  · 跑 python  → & '<repo 根>\\.venv\\Scripts\\python.exe' <絕對路徑腳本>
    （<repo 根> 現查：$env:CLAUDE_PROJECT_DIR，或 git rev-parse --show-toplevel。
      本檔刻意不寫死任何磁碟機路徑——它會被 commit 進 repo，對其他 checkout 一律是錯的指引，
      且 tools/tests/test_platform_neutral_paths.py 會逐行掃描並判紅）
  · 跑 .sh     → bash <script>        （在 PowerShell 內呼叫，這不算以 Bash 為載具）
  · 讀檔／搜尋／算行數 → 用 Read／Grep 工具，不經 shell
                        （編碼邊界雙向都會給出假數字，R71 兩次實證）
  · 切目錄     → Push-Location <絕對路徑>; …; Pop-Location（同一次呼叫內成對）

PowerShell 5.1 沒有 && 與 ||：用 `;` 或 `A; if ($?) { B }`。
"""


def main() -> int:
    try:
        if os.name != "nt":
            return 0  # mac/Linux 上 bash 是正確載具，不誤傷

        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}

        tool = str(payload.get("tool_name") or "")
        # matcher 已限定 Bash，這裡再確認一次：matcher 若被改寬，守衛不應擴大射程
        if tool and tool != "Bash":
            return 0

        sys.stderr.write(_GUIDANCE)
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring
        return 0


if __name__ == "__main__":
    sys.exit(main())
