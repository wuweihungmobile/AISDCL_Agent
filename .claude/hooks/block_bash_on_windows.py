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
· payload 解析不出工具名（壞 JSON／空 stdin／缺 tool_name）→ exit 2（fail-closed）。
  這個方向對**本檔**是對的，前提是下一段那條配套約束成立。

🔴 本輪訂正：fail-closed 必須配窄 matcher（R77-08）
---------------------------------------------------
上面那條 fail-closed 分支的爆炸半徑，取決於**註冊面的 matcher 圈了哪些工具**。
本檔此前的 matcher 是兩個工具的交替（為滿足另一支測試的全稱約定而放寬），
於是一份解析不出工具名的 payload 會連**子代理派工**一起硬擋，而使用者拿到的
訊息指向一個與那次呼叫無關的原因。同一時間，註冊面的說明文字把這個組合描述成
不會發生——那句描述已被本輪七輸入實測推翻，故一併改寫（措辭刻意不重述它，
樹裡不留假句子）。

處置是**讓兩件事各自回到它真正要的東西**，而不是拆掉 fail-closed：
  · matcher 收窄到本守衛自己那一個工具 ⇒ 退化 payload 的代價回到「擋掉一次 Bash」，
    那正是本守衛的職責範圍；
  · 那條全稱約定改成只約束它真正需要的載體（子代理注入走的那一支 router hook）。
「rc==2 的守衛必須配窄 matcher」現在由
tools/tests/test_check_hooks_liveness.py 機械釘住——把 matcher 再放寬回去即紅，
不靠任何人記得本段文字。

繞道
----
確有必要在 Windows 跑 bash（例如執行一支 .sh）時，正確作法是**在 PowerShell 工具內**
解析出 Git Bash 再呼叫——那是「執行一支 .sh」而非「以 Bash 為載具」，同
tools/git-hooks/pre-push 既有作法。本守衛只攔 Bash **工具**，攔不到也不該攔那條路。

🔴 R73 訂正（DEF-101-778）：本段原本教人寫裸 `bash <script>`，那是**壞掉的指引**——
`Get-Command bash` 在 Windows 上解析到 system32 的 WSL 佔位版（R73 於 5.1 與 7.6.4
兩個引擎各實測一次，兩邊都命中 system32 那支），且反斜線路徑會被吃掉（實測
`/bin/bash: D:CursorProjectAISDCL_Agenttools....sh: No such file or directory`，
注意分隔符全部消失）。同 DEF-101-617/618 的 WSL 佔位版誤解析同源。
**執行規則的機械物不該教壞掉的作法**——它比純文件更權威，讀者會照它做。
正解走 repo 既有 SSOT `tools/lib/Find-GitBash.ps1`（含 system32/WSL 逐段排除），
不要寫死任何磁碟機路徑（本檔會被 commit，寫死對其他 checkout 一律是錯的）。
"""

from __future__ import annotations

import json
import os
import sys

# 🔴 自己的 stderr／stdout 強制 UTF-8（DEF-101-789）。
# 缺這段時發生什麼：`sys.stderr` 的預設 `errors` 是 `backslashreplace`，於是
#   · locale 編碼**表達不了** CJK（en-US Windows／GitHub windows-latest ＝ cp1252）
#     → 整段指引變成 `\\uXXXX` 逃脫字面；
#   · locale 表達得了但不是 UTF-8（zh-TW ＝ cp950）
#     → 讀者端（以 UTF-8 讀取的 Claude Code）拿到亂碼。
# 兩種都讓「阻斷有了、教學沒了」：使用者被 exit 2 硬擋，卻拿不到替代指令——而這支
# hook 存在的唯一理由就是「純文件約束實證無攔阻力」，指引不可讀等於把它砍掉一半。
# 這不只是測試紅：雲端 windows-compat-ci 是**因為使用者真的會看到那串轉義碼**才紅的。
# 姊妹檔 `sdd_hook_router.py` 早就有這段，同目錄兩支 hook 一支守一支不守。
# 為何就地 reconfigure 而不 import `tools/_stdio_utf8`：本檔的 fail-open 契約要求
# 零外部相依（見上方 docstring 的 P0），且 `tools/` 不在 hook 行程的 sys.path 上。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — 見下
        # 這裡刻意比姊妹檔的 `(AttributeError, ValueError, OSError)` 更寬：
        # 那三種涵蓋了「非 TextIOWrapper（測試替身）／串流已關閉」等實際情形，但本檔的
        # fail-open 是 **P0**（hook 崩潰會把所有工具硬鎖死），而**模組層**崩潰發生在
        # main() 的 try 之外、繞得過那道保險。指引印不漂亮遠好過守衛自己變成故障源。
        pass

_GUIDANCE = """🔴 Windows 上已禁用 Bash 工具（根 CLAUDE.md〈Windows 側單一載具原則〉鐵律一）。

改用 **PowerShell 工具**：
  · 跑 python  → & '<repo 根>\\.venv\\Scripts\\python.exe' <絕對路徑腳本>
    （<repo 根> 現查：$env:CLAUDE_PROJECT_DIR，或 git rev-parse --show-toplevel。
      本檔刻意不寫死任何磁碟機路徑——它會被 commit 進 repo，對其他 checkout 一律是錯的指引，
      且 tools/tests/test_platform_neutral_paths.py 會逐行掃描並判紅）
  · 跑 .sh     → . '<repo 根>/tools/lib/Find-GitBash.ps1'; & (Find-GitBash) '<正斜線腳本路徑>'
    （🔴 **不要**寫裸 `bash <script>`：`Get-Command bash` 會解析到 system32 的 WSL
      佔位版，且反斜線路徑的分隔符會被整批吃掉——R73 雙引擎各實測一次。
      Find-GitBash 是 repo 既有 SSOT，內含 system32/WSL 逐段排除）
  · 讀檔／搜尋／算行數 → 用 Read／Grep 工具，不經 shell
                        （編碼邊界雙向都會給出假數字，R71 兩次實證）
  · 切目錄     → Push-Location <絕對路徑>; …; Pop-Location（同一次呼叫內成對）

避免 && 與 ||：用 `;` 或 `A; if ($?) { B }`。
（🔴 R73 訂正：本行原本把理由綁在「互動載具的 PowerShell 版本不支援這兩個運算子」上。
  互動載具升到 PowerShell 7 之後那個理由對讀者為假——7.x 支援它們——於是整條建議
  看起來已過期而會被忽略。真正的理由與互動載具是哪一版無關：**生產路徑（schtasks
  兩支 job 的 Action）跑的是 powershell.exe＝5.1**，在那裡 `&&` 是 parse error。
  判準要綁生產引擎，不要綁你手上這個 session 剛好是哪一版。
  本段措辭刻意不逐字重述那句已為假的話——樹裡不留假句子，否則下一個人 grep 到它
  會以為那是現行說法，且 tools/tests/test_check_hooks_liveness.py 會判紅。）
"""


def main() -> int:
    try:
        if os.name != "nt":
            return 0  # mac/Linux 上 bash 是正確載具，不誤傷

        # 走 **bytes 端**再以 UTF-8+replace 解碼，不用 `json.load(sys.stdin)`：
        # zh-TW Windows 的 pipe 預設編碼是 cp950，文字端 read 遇到含中文的 UTF-8
        # payload 會拋 UnicodeDecodeError。本檔的 fail-closed 讓那個例外表現成
        # 「阻斷」而非崩潰，所以它不會被看見——一支**阻斷級**守衛靜默改變行為，
        # 比崩潰更難察覺。三支姊妹 hook 都早有這道防線，唯獨 fail-closed 的這支沒有。
        try:
            buffer = getattr(sys.stdin, "buffer", None)
            raw = (buffer.read().decode("utf-8", "replace") if buffer is not None
                   else sys.stdin.read())
            payload = json.loads((raw or "").strip() or "{}")
            if not isinstance(payload, dict):
                payload = {}
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
