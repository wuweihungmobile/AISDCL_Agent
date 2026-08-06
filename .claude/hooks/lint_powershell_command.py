#!/usr/bin/env python
"""PreToolUse 守衛：PowerShell 指令字串的**極窄** lint（鐵律二首次有牙）。

WHY
---
本輪逐字稿實測到一組乾淨的對照：**有觀測者的規則違規 1 次且被當場擋下，
沒有觀測者的規則違規率 20~35%**。而整個 PowerShell 工具面在本檔出現之前
**零觀測者**——鐵律二（禁裸 cd）、「讀 rc 不接管線」、「不要寫裸 bash」這三條的
違規面全部在**指令字串的內容**裡，而那個字串從來不會變成 repo 裡的檔案，
於是全庫所有靜態掃描器結構上都看不見它們。差別不在紀律寫得夠不夠嚴厲：
`block_bash_on_windows.py` 那條規則的文字版本實證零攔阻力，換成 hook 之後
一次嘗試、一次攔下。

本檔把同一個手法套到那三條規則上。事後量測的另一半住
`tools/probe/audit_session.py`（讀 session 逐字稿），兩者一前一後。

刻意極窄（這是設計而非偷懶）
----------------------------
只擋三件事，其餘一律放行。理由：**誤報會讓整個機制被關掉**，而被關掉的守衛
比沒有守衛更糟——它會讓人以為那一面有人在看。每一條都另附行內豁免出口
（見 `_EXEMPT_RE`），需要寫出違規形態時（例如撰寫文件或重現缺陷）能就地放行，
不必去動註冊面。

行為契約
--------
· 非 Windows（`os.name != 'nt'`）→ exit 0。mac/Linux 的載具規則不同，
  單平台判準不可無條件外推（本 repo 有同型教訓）。
· `tool_name != 'PowerShell'` → exit 0。射程不得擴大：matcher 若被改寬，
  守衛自己必須認得工具名。
· payload 解析不出工具名／指令 → **exit 1（非阻斷但出聲）**，不是 exit 2。
  理由見下方〈為何退化 payload 不 fail-closed〉。
· 命中任一條 → exit 2 阻斷，stderr 一次列出**全部**命中項（不早退——早退會
  遮蔽後面檢查的訊號，而遮蔽的方向是「看起來變乾淨」，比紅更危險）。
· 任何非預期例外 → exit 0（fail-open）。`.claude/settings.json` 記載過的 P0：
  hook 誤觸 PreToolUse deny 會把**所有**工具硬鎖死，守衛自身絕不可成為故障源。

為何退化 payload 不 fail-closed
--------------------------------
姊妹檔 `block_bash_on_windows.py` 對退化 payload 是 exit 2，那對它是對的：
它的 matcher 只圈自己那一個工具，硬擋的代價就是擋掉那一個工具的一次呼叫。
本檔不同——PowerShell 是這台機器上**唯一的 shell 載具**，對一份根本讀不出
內容的 payload 硬擋它，等於用一個讀不懂的輸入換掉整個工作面。而「送壞 payload
繞過守衛」在這裡不是真實威脅面：payload 由 Claude Code 產生，不由被守的一方
撰寫。真正要防的是**守衛靜默失效**，exit 1 已經滿足——它不阻斷，但會出聲。
這條「rc==2 就必須配窄 matcher」的對應關係由
`tools/tests/test_check_hooks_liveness.py` 機械釘住，不靠本段散文。
"""

from __future__ import annotations

import json
import os
import re
import sys

# 自己的 stdout/stderr 強制 UTF-8。缺這段時：locale 表達不了 CJK（en-US Windows
# ＝cp1252）→ 整段指引變 `\uXXXX` 逃脫字面；locale 表達得了但非 UTF-8（zh-TW
# ＝cp950）→ 讀者端亂碼。兩種都讓「阻斷有了、教學沒了」，而這支 hook 存在的
# 唯一理由就是純文件約束無攔阻力，指引不可讀等於把它砍掉一半。
# 例外一律吞掉且比姊妹檔更寬：**模組層**崩潰發生在 main() 的 try 之外、繞得過
# 那道保險，而 fail-open 在這裡是 P0。
#
# 🔴 為何是「就地重做一次」而不是 import repo 既有的唯一實作（`tools/_stdio_utf8.py`）：
# hook 由 `.claude/settings.json` 的 shim 以 `runpy.run_path(...)` 起，而 `run_path`
# **不會**把腳本所在目錄加進 `sys.path`。本輪就地實測該 shim 內的 `sys.path[:3]`：
#   ['', '<python>\\python311.zip', '<python>\\DLLs']
# ⇒ `sys.path[0]` 是 cwd（repo 根），`tools/` 與 `.claude/hooks/` 兩者都不在路徑上，
# `import _stdio_utf8` 與 import 同目錄姊妹模組**都會在 import 期爆掉**——而模組層爆掉
# 正是本檔絕不能發生的那件事。這也是姊妹檔 `block_bash_on_windows.py` 的既有結論。
# 三者相乘（註冊表要求 hook 自帶 UTF-8 保護 × fail-open 要求零外部相依 × run_path 不
# 供路徑）使這一處複本是**結構上被逼出來的**，故在去重棘輪的基線表上具名登記。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — 見上
        pass

#: 本守衛只認這一個工具名（本輪以拋棄式 dump hook 實測 PreToolUse payload 確認）。
OWN_TOOL = "PowerShell"

#: 行內豁免：`# ps-lint-ok: <WHY>`。WHY 必填（空白理由不算豁免），讓「刻意這樣寫」
#: 與「沒注意」分得開。體例對齊 repo 既有的那幾種行尾豁免標記——但**刻意不在註解裡
#: 寫出它們的字面**：那些標記各自帶 stale 掃描器，被引用到的那一行會被判成「登記了
#: 豁免卻沒有被壓下的違規」而轉紅（本輪實測撞過一次，兩道鎖的合法動作互為違規）。
_EXEMPT_RE = re.compile(r"#\s*ps-lint-ok:\s*\S")

#: 管線接進這些 cmdlet 之後再讀 rc，才算命中（不是看到任何 `|` 都算）。
_PIPE_INTO_RE = re.compile(
    r"\|\s*(Select-Object|Select-String|Out-\w+|Format-\w+|Sort-Object"
    r"|Measure-Object|ForEach-Object|Where-Object|Tee-Object|head|tail|findstr)",
    re.IGNORECASE,
)
_RC_READ_RE = re.compile(r"\$LASTEXITCODE", re.IGNORECASE)
_NAKED_CD_RE = re.compile(r"^\s*(cd|Set-Location)\b\s+(?!-)", re.IGNORECASE)
_BARE_BASH_RE = re.compile(r"(?<![\w/\\'\"-])bash\s+[^\n]*\.sh")
_FIND_GIT_BASH_RE = re.compile(r"Find-GitBash", re.IGNORECASE)

_RC_HINT = (
    "🔴 讀 rc 不要接管線。pwsh 7.x 提前中斷管線時**不更新** $LASTEXITCODE（保留前一個值，"
    "真 rc=3 可能讀成 0＝真紅被讀成綠）；PS 5.1 則寫入 -1；加 2>&1 又會翻轉。"
    "沒有方向可以憑記憶——就是不要接。\n"
    "  出口：& <exe> <args>; \"rc=$LASTEXITCODE\"   ← rc 自成一句，前面那一句不接任何管線\n"
    "  要篩輸出就先落檔或分兩次呼叫；要一支固定 rc 語意的載具走 tools/probe/。"
)
_CD_HINT = (
    "🔴 禁裸 cd／Set-Location（鐵律二）。PowerShell 工具的 cwd **會跨呼叫持續**，"
    "裸 cd 之後的每一個相對路徑都會找錯地方（曾單輪因此失誤 3 次，其中一次誤判成「檔案不存在」）。\n"
    "  出口：一律用絕對路徑；真的要切目錄就 Push-Location <絕對路徑>; …; Pop-Location"
    "（同一次呼叫內成對，不遺留狀態）。"
)
_BASH_HINT = (
    "🔴 不要寫裸 bash <script>.sh。Get-Command bash 會解析到 system32 的 WSL 佔位版，"
    "且反斜線路徑的分隔符會被整批吃掉（雙引擎各實測過一次）。\n"
    "  出口：. \"$(git rev-parse --show-toplevel)/tools/lib/Find-GitBash.ps1\"; "
    "& (Find-GitBash) -n '<正斜線腳本路徑>'"
)
_FOOTER = (
    "\n（刻意極窄：本守衛只擋這三件事。真的需要寫出該形態時，在指令內加行內豁免 "
    "`# ps-lint-ok: <理由>` 即放行——誤報讓機制被關掉比漏擋更糟。"
    "回歸鎖：tools/tests/test_check_hooks_liveness.py）"
)


def statements(command: str) -> list[str]:
    """把指令切成語句（`;` 與換行）。刻意不解析引號——本檔是 lint 不是 parser，
    切錯的代價由行內豁免出口承擔。"""
    return [s for s in re.split(r"[;\n]", command)]


def lint_command(command: str) -> list[str]:
    """回傳命中的違規訊息清單（空 list＝放行）。純函式，紅綠由注入自證。

    **不早退**：三條檢查全部跑完再一次回報。早退會讓第二、三條的訊號被第一條
    遮蔽，而遮蔽的方向是「看起來變乾淨」。
    """
    if _EXEMPT_RE.search(command):
        return []

    hits: list[str] = []
    parts = statements(command)

    # ① 管線 × 讀 rc：同一句、或前一句管線後一句讀 rc。
    for index, part in enumerate(parts):
        pipes_here = bool(_PIPE_INTO_RE.search(part))
        if not pipes_here:
            continue
        following = parts[index + 1] if index + 1 < len(parts) else ""
        if _RC_READ_RE.search(part) or _RC_READ_RE.search(following):
            hits.append(_RC_HINT)
            break

    # ② 裸 cd／Set-Location（Push-Location／Pop-Location 不在此列）。
    if any(_NAKED_CD_RE.search(part) for part in parts):
        hits.append(_CD_HINT)

    # ③ 裸 bash + .sh（已走 Find-GitBash SSOT 者放行）。
    if _BARE_BASH_RE.search(command) and not _FIND_GIT_BASH_RE.search(command):
        hits.append(_BASH_HINT)

    return hits


def read_payload() -> dict | None:
    """讀 stdin 的 hook payload；`None`＝退化（讀不出來）。

    走 **bytes 端**再以 UTF-8+replace 解碼：zh-TW Windows 的 pipe 預設 cp950，
    裸文字端 read 遇到含中文的 UTF-8 payload 會拋 UnicodeDecodeError，讓阻斷級
    hook 靜默失效。姊妹 hook 早有這道防線，本檔照抄同一形態。
    """
    try:
        buffer = getattr(sys.stdin, "buffer", None)
        raw = (buffer.read().decode("utf-8", "replace") if buffer is not None
               else sys.stdin.read())
    except Exception:  # noqa: BLE001 — 讀不到就是退化，不是崩潰
        return None
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def main() -> int:
    try:
        if os.name != "nt":
            return 0  # 非 Windows 的載具規則不同，不誤傷

        payload = read_payload()
        if payload is None:
            sys.stderr.write(
                "[lint_powershell_command] payload 讀不出來（壞 JSON／空 stdin）⇒ "
                "本次不 lint。刻意不阻斷：硬擋唯一的 shell 載具，代價遠大於漏掉一次 lint；"
                "但也不靜默——守衛失效必須看得見。\n"
            )
            return 1

        tool = str(payload.get("tool_name") or "")
        if tool != OWN_TOOL:
            if tool:
                return 0  # 射程不得擴大
            sys.stderr.write(
                "[lint_powershell_command] payload 沒有 tool_name ⇒ 無法判定射程，本次不 lint。\n"
            )
            return 1

        tool_input = payload.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str) or not command.strip():
            sys.stderr.write(
                "[lint_powershell_command] PowerShell payload 沒有 command 字串 ⇒ 本次不 lint。\n"
            )
            return 1

        hits = lint_command(command)
        if not hits:
            return 0
        sys.stderr.write("\n\n".join(hits) + _FOOTER + "\n")
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring 的 P0
        return 0


if __name__ == "__main__":
    sys.exit(main())
