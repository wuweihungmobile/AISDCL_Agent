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

R78：三條規則的鑑別力修復（四方複審 SA-01／SD-01／QA-01／SD-02）
--------------------------------------------------------------
上一版三條規則各自被實測穿透，而且**兩個方向都破**：

· **漏擋**：`| select -First 5` 全數放行、`| Select-Object -First 5` 全數擋下
  （12 組別名 vs 全名、其餘字元逐字相同，12/12 不對稱）。`select` 正是「提前結束
  管線」最常見的寫法 ⇒ 這道鎖擋掉的剛好是沒人會寫的那一半。
  同理 `cd` 只認行首（`&&`／`||`／`|`／`{` 之後全逃）、`bash` 只認特定字面
  （`bash.exe` 逃）、rc 讀取只看緊鄰下一句（中間插一句就逃）。
· **誤擋**：`"rc=$LASTEXITCODE" | Out-File` 完全安全卻被硬擋（rc 在管線**之前**
  就展開了，判準卻只看「同一句有沒有同時出現」不看先後）；違規形態只住在
  引號／here-string 內時（寫探針、寫文件、重現缺陷——最常見的正當情境）三條全誤擋。

修法的共同形狀是**先把「不是可執行結構」的區段拿掉，再比對**，而不是把個案
一個一個加進正則。核心是 `mask_regions()` 的兩種遮蔽（見該函式 docstring）：

  · `keep_expandable=False`（structural）＝指令**結構**面：引號字串、here-string、
    註解全部換成等長空白。管線在哪、指令字在哪，只准從這一面讀。
  · `keep_expandable=True`（expandable）＝**變數展開**面：只遮蔽字面量
    （`'…'`／`@'…'@`／註解），保留 `"…"`／`@"…"@`——PowerShell 在那裡面**真的會**
    展開 `$LASTEXITCODE`，所以那是一次真的 rc 讀取。

兩面等長、位置一一對應，於是「管線在第幾個字元、rc 讀在第幾個字元」可以跨面比較——
規則①的先後順序判定就是靠這個，QA-01 的誤擋也是靠這個消掉的。這**不是同一份東西的
兩份複本**：它們對應 PowerShell 的兩種不同語意，合成一面就必然在某個方向上判錯。
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

#: 🔴 **事中攔截（本檔）與事後量測（`tools/probe/audit_session.py`）共用的判準字面**。
#: 兩邊各存一份**逐字相同**的複本——理由與上面 `_stdio_utf8` 那一處同源：本檔由
#: `runpy.run_path` 起、`sys.path` 上既沒有 `tools/` 也沒有 `.claude/hooks/`，import 期
#: 爆掉正是 fail-open 契約絕不能發生的事，所以本檔只能是「被抄的那一份」，不能 import。
#:
#: 代價是真的發生過：R77 交付時，本檔的 cmdlet 清單有 `Tee-Object` 而探針那份沒有，
#: 兩份零比對 ⇒ 同一條規則「攔得下、卻量不到」。既然結構上只能留複本，那就把複本的
#: **一致性**變成會轉紅的事件：`tools/tests/test_check_hooks_liveness.py` 的
#: `TestHookAndProbeShareOneCriterion` 兩向釘住——① 兩份字典字面相等；
#: ② 同一批指令字串餵進兩邊，判定必須一致（後者連「不經由本字典的第二份複本」也抓得到）。
SHARED_PATTERN_SOURCE: dict[str, str] = {
    # 管線接進這些 cmdlet 之後再讀 rc，才算命中（不是看到任何 `|` 都算）。
    # 🔴 R78／SA-01：**內建別名與全名同列**。上一版只列全名，實測 12 組「別名 vs
    # 全名、其餘字元逐字相同」的配對 **12/12 不對稱**（`| select -First 5` 放行、
    # `| Select-Object -First 5` 擋下）——而 `select` 正是「提前結束管線」最常見的
    # 寫法，等於這道鎖擋掉的剛好是沒人會寫的那一半。每個別名自帶右邊界
    # `(?![\w-])` 以免吃到 `selection`／`sortable`；`%` 與 `?` 另用 `(?=\s|\{|$)`，
    # 避免誤傷 `$_ % 2` 那類真正的運算子用法。
    "pipe-cmdlets": (
        r"(?:Select-Object|Select-String|Out-\w+|Format-\w+|Sort-Object"
        r"|Measure-Object|ForEach-Object|Where-Object|Tee-Object"
        r"|head|tail|findstr)(?![\w-])"
        r"|(?:select|sls|sort|measure|foreach|where|ft|fl|oh|tee)(?![\w-])"
        r"|[%?](?=\s|\{|$)"
    ),
    # 裸 cd／Set-Location 的**動詞面**（不含錨點——兩邊各自接自己的邊界）。
    # 🔴 R78／SD-01：補上 `chdir`／`sl` 兩個內建別名；並**移除 `(?!-)`**——
    # `Set-Location -Path X` 與 `cd X` 是同一件事，上一版只因為下一個字元是 `-`
    # 就整條放行＝一步就繞過。
    # 🔴 R79：參數改成**可選**。上一版尾巴硬性要求 `\s+\S`（至少一個參數），於是
    # **不帶參數**的 `cd`／`sl`／`chdir`／`Set-Location` 整條放行——而那一種在
    # PowerShell 語意上是切到 $HOME，鐵律二要防的「cwd 跨呼叫持續、之後每個相對路徑
    # 都找錯地方」在它身上只會更嚴重（後續全部相對路徑一次全錯）。規則自己要求了
    # 一個它不需要的東西。尾巴改成「有參數，或這一句到此為止（`;`／換行／管線／
    # 鏈接／區塊結尾／字串結尾）」。
    "naked-cd": r"(cd|chdir|sl|Set-Location)(?![\w-])(?:\s+\S|\s*(?=[;\n|&)}]|$))",
    # 裸 bash 的**指令字面**（`bash` / `bash.exe`）。刻意只到動詞為止：「跑的是不是
    # .sh」由兩邊各自補上（hook 要在遮蔽過的結構面找指令位置、回原文找 `.sh`，探針
    # 則就地把兩者接成一條），見各自的組裝處。
    # 🔴 R78／SD-01：上一版只認 `bash` 字面，`bash.exe` 一步就繞過。
    "bare-bash-sh": r"bash(?:\.exe)?(?![\w.-])",
}

#: 兩邊共用的字面之外，本檔自己的**邊界**。上一版三條規則的邊界各有一個一步繞過口：
#: cd 只認 `^`（`&&`／`||`／`|`／`{` 之後全逃）、bash 只認裸字面。統一改成「語句／
#: 管線／鏈接／區塊起頭」這個集合——它們是 PowerShell 裡「下一個指令從這裡開始」的
#: 全部入口，比逐個補個案穩。
_CMD_START = r"(?:^|[;\n|&{}()])\s*"

_PIPE_INTO_RE = re.compile(
    r"\|\s*(" + SHARED_PATTERN_SOURCE["pipe-cmdlets"] + r")", re.IGNORECASE
)
_RC_READ_RE = re.compile(r"\$LASTEXITCODE", re.IGNORECASE)
#: 「rc 已被重新建立」——**真的發起了一次呼叫**。用途見 `_rc_after_pipe()`：
#: 截斷管線造成的污染會**一直延續**，但 hint 教的正解 `& <exe> <args>; "rc=$LASTEXITCODE"`
#: 本來就會重設 rc，不該被前面某一句的管線牽連。
#:
#: 🔴 R79：上一版把「重設」判太寬，而寬的方向正是這條規則存在的唯一理由的反面
#: （放行一條會讓真 rc=7 被讀成 0 的指令）。兩個口子都是「提到」而非「執行」：
#:   · 呼叫運算子的左邊界只排除 `&` 與英數字 ⇒ `2>&1`／`1>&2` 的那個 `&`（左邊是 `>`）
#:     被當成呼叫。`2>&1` 在最近 12 支逐字稿的 547 條 unique 指令裡佔約一半，觸發面極大。
#:   · `.exe` 出現在**任何位置**都算 ⇒ `Get-Command python.exe`、`Test-Path …\cmd.exe`
#:     這種只是把路徑當資料的語句被當成執行。
#: pwsh 7.6.4 真機實測：這三種語句一個都沒有重設 `$LASTEXITCODE`（前值原樣保留）。
#: 修法是把兩個口子各自收到「命令位置」上：
#:   ① 呼叫運算子的左邊界加上 `>`，把重導向合併排除；
#:   ② `.exe`／`.cmd`／`.bat` 只在**語句的第一個 token** 才算數（`_NATIVE_HEAD_RE`）——
#:      那才是「這一句在跑一支外部執行檔」，寫在參數位置的同一個字面只是資料。
#: 仍然刻意窄：裸原生指令（`git status` 這種不帶 `&`、不帶副檔名者）**不算**重設，
#: 於是判定偏向擋。這個方向是刻意的——「同一個指令字串裡既有截斷管線又要讀 rc」
#: 本身就是這條規則要消滅的混寫，而行內豁免是它的出口。
#: 誠實劃界：偏向擋的代價已在真實語料上量過（見 `tools/tests/test_check_hooks_liveness.py`
#: 的 `TestLintPowerShellHookBehaviour` 兩向表），不是靠推測。
_RC_RESET_RE = re.compile(r"(?<![&\w>])&(?!&)\s*\S", re.IGNORECASE)
#: 語句**開頭**就是一支外部執行檔（`python.exe a.py`／`<venv>/bin/tool.cmd`）＝真的在跑東西。
#: 錨在開頭是關鍵：`Get-Command python.exe` 的第一個 token 是 cmdlet，`.exe` 只是參數。
_NATIVE_HEAD_RE = re.compile(r"^\s*[^\s;|&]*\.(?:exe|cmd|bat)(?![\w])", re.IGNORECASE)


def _statement_resets_rc(statement: str) -> bool:
    """這一句是否真的重新發起了一次呼叫（⇒ `$LASTEXITCODE` 被重寫）。

    純函式、吃**一句**（不是整條指令）：`.exe` 的「必須在開頭」這個條件只有在語句
    邊界上才判得準，用 `search(..., pos, endpos)` 是判不到的（`^` 不會錨在 `pos`）。
    """
    return bool(_RC_RESET_RE.search(statement) or _NATIVE_HEAD_RE.search(statement))
_NAKED_CD_RE = re.compile(
    _CMD_START + SHARED_PATTERN_SOURCE["naked-cd"], re.IGNORECASE
)
_BARE_BASH_RE = re.compile(
    _CMD_START + SHARED_PATTERN_SOURCE["bare-bash-sh"], re.IGNORECASE
)
#: 規則③的佐證面：真的在跑一支 `.sh`。刻意**對原文**比對而不是對遮蔽面——
#: `bash "tools/x.sh"` 的路徑住在引號裡，遮蔽面上看不到 `.sh`。指令位置從結構面讀
#: （所以 `$doc = 'bash x.sh'` 不會命中）、佐證從原文讀（所以引號路徑不會逃）。
_SH_SCRIPT_RE = re.compile(r"\.sh(?![\w])", re.IGNORECASE)
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
#: 🔴 出口寫在**第一行**（R78／SA-01 附帶）：上一版把它放在頁尾，第一次撞到的人
#: 先讀到的是三段責備、最後才看到出口——而「窄守衛必須有出口」正是本檔的設計前提，
#: 出口看不見等於沒有。
_HEADER = (
    "🔴 需要就地寫出這個形態？在指令內加行內豁免 `# ps-lint-ok: <理由>`（理由必填）"
    "即放行——寫文件／寫探針／重現缺陷本來就會寫出違規形態，那不是違規。\n"
    "以下是本次命中的項目：\n\n"
)
_FOOTER = (
    "\n（刻意極窄：本守衛只擋這三件事，其餘一律放行——誤報讓機制被整個關掉，"
    "比漏擋更糟。回歸鎖：tools/tests/test_check_hooks_liveness.py）"
)


def mask_regions(command: str, *, keep_expandable: bool,
                 keep_comments: bool = False) -> str:
    """把「不是可執行結構」的區段換成**等長**空白：引號字串、here-string、註解。

    等長是關鍵：遮蔽後與原字串**位置一一對應**，兩種遮蔽版本因此可以互相比位置
    （規則①要同時知道「管線在第幾個字元」與「rc 讀在第幾個字元」）。換行刻意保留，
    語句切割才不會被遮蔽改變。

    兩種遮蔽對應 PowerShell 的兩種語意，**不是同一份東西的兩份複本**：

    · `keep_expandable=False`（結構面）：`'…'`／`"…"`／`@'…'@`／`@"…"@`／`#…`／
      `<#…#>` 全遮。裡面的 `|`／`cd`／`bash` 都不是指令結構，上一版對它們一律誤擋
      （SD-02 實測三條規則全中），而那撞的是最常見的正當情境：寫探針、寫文件、
      重現缺陷。
    · `keep_expandable=True`（展開面）：只遮字面量（`'…'`／`@'…'@`／註解），保留
      `"…"`／`@"…"@`——PowerShell 在那裡面**真的會**展開 `$LASTEXITCODE`，
      `"rc=$LASTEXITCODE"` 是一次貨真價實的 rc 讀取。合成一面就必然在某個方向判錯：
      全遮則規則①的正典案例整個消失（漏擋），全不遮則 SD-02 回來（誤擋）。

    `keep_comments=True`（R79 新增，只有行內豁免偵測在用）：註解**原樣保留**、字串
    照樣遮。用途見 `lint_command()` 的豁免那一段——它要的正是「這個標記住在真註解裡
    還是住在字串裡」，而那件事只有這一面分得開。掃描器仍然是**先看到 `#` 就跳到行尾**，
    所以註解裡的撇號（`don't`）不會被誤判成字串起頭，這正是舊版比對原文的那個理由。

    這仍然不是 parser（不處理子運算式巢狀、不管 escape 以外的引號規則）；它只需要
    分得出「這段字元會被當成指令」還是「會被當成資料」。切錯的代價由行內豁免承擔。
    """
    out = list(command)
    length = len(command)

    def blank(start: int, end: int) -> None:
        for index in range(start, min(end, length)):
            if out[index] != "\n":
                out[index] = " "

    cursor = 0
    while cursor < length:
        head = command[cursor:cursor + 2]

        if head in ("@'", '@"'):  # here-string：結尾必須是行首的 '@ ／ "@
            quote = head[1]
            close = command.find("\n" + quote + "@", cursor + 2)
            end = length if close < 0 else close + 3
            if not (keep_expandable and quote == '"'):
                blank(cursor, end)
            cursor = end
            continue

        if head == "<#":  # 區塊註解
            close = command.find("#>", cursor + 2)
            end = length if close < 0 else close + 2
            if not keep_comments:
                blank(cursor, end)
            cursor = end
            continue

        char = command[cursor]

        # 行註解：`#` 只有在 token 起頭才起註解（`a#b` 是一個 token）。
        if char == "#" and (cursor == 0 or command[cursor - 1] in " \t\r\n;|&({"):
            close = command.find("\n", cursor)
            end = length if close < 0 else close
            if not keep_comments:
                blank(cursor, end)
            cursor = end
            continue

        if char in "'\"":
            scan = cursor + 1
            while scan < length:
                if char == '"' and command[scan] == "`":  # 反引號 escape
                    scan += 2
                    continue
                if command[scan] == char:
                    if scan + 1 < length and command[scan + 1] == char:  # '' ／ ""
                        scan += 2
                        continue
                    break
                scan += 1
            end = min(scan + 1, length)
            if not (keep_expandable and char == '"'):
                blank(cursor, end)
            cursor = end
            continue

        cursor += 1

    return "".join(out)


def statement_spans(masked: str) -> list[tuple[int, int]]:
    """語句（`;` 與換行分隔）在**原字串座標系**上的 `[start, end)` 清單。

    回位置而不是回切片：規則①要把「結構面找到的管線位置」與「展開面找到的 rc
    位置」放在同一把尺上比大小，切片會讓兩面的座標對不起來。
    """
    spans: list[tuple[int, int]] = []
    start = 0
    for separator in re.finditer(r"[;\n]", masked):
        spans.append((start, separator.start()))
        start = separator.end()
    spans.append((start, len(masked)))
    return spans


def _rc_after_pipe(structural: str, expandable: str) -> bool:
    """規則①：**先後順序**與**跨語句污染**都算數。

    上一版兩個方向都錯：
    · 漏擋（SD-01）——只看「緊鄰的下一句」（`parts[index + 1]`），中間插任何一句
      就逃出視窗，而 `$x = 1` 這種句子根本不會重設 `$LASTEXITCODE`，rc 照樣是髒的。
      改成污染會**一直延續**到某一句真的重新發起呼叫（`_RC_RESET_RE`）為止。
    · 誤擋（QA-01）——`"rc=$LASTEXITCODE" | Out-File` 是先展開變數再進管線，
      rc 讀取發生在任何管線中斷**之前**，完全安全卻被硬擋，因為判準只問「同一句
      有沒有同時出現」不問先後。改成比位置：rc 在管線**之後**才算命中。

    🔴 R79：污染的**解除**條件改由 `_statement_resets_rc()` 判（吃一句、不吃座標）。
    上一版把「提到一支 exe」與「`2>&1` 裡的 `&`」都當成呼叫，於是一句話就能把污染
    旗標清掉——而清掉之後放行的，正是這條規則唯一要防的那件事。
    """
    contaminated = False
    for start, end in statement_spans(structural):
        pipe = _PIPE_INTO_RE.search(structural, start, end)
        pipe_pos = pipe.start() if pipe else -1
        for read in _RC_READ_RE.finditer(expandable[start:end]):
            if contaminated or (pipe_pos >= 0 and start + read.start() > pipe_pos):
                return True
        if pipe_pos >= 0:
            contaminated = True
        elif _statement_resets_rc(structural[start:end]):
            contaminated = False
    return False


def lint_command(command: str) -> list[str]:
    """回傳命中的違規訊息清單（空 list＝放行）。純函式，紅綠由注入自證。

    **不早退**：三條檢查全部跑完再一次回報。早退會讓第二、三條的訊號被第一條
    遮蔽，而遮蔽的方向是「看起來變乾淨」。
    """
    # 豁免只認**住在真註解裡**的標記（`keep_comments=True`：註解原樣留、字串照樣遮）。
    # 🔴 R79：上一版比對原文，於是任何在字串裡「提到」這個標記的指令——寫文件、
    # 寫探針、在訊息裡引述違規形態——會一次關掉全部三條檢查，且不留任何痕跡。
    # 舊版選擇比對原文的理由（豁免理由本來就可能含撇號，例如「don't」；先遮蔽再找
    # 會把那半行當成未閉合字串吞掉，讓合法豁免靜默失效＝誤擋方向）**仍然成立且已被
    # 保住**：遮蔽器是先看到 `#` 就跳到行尾，註解內的撇號從頭到尾不會被當成字串起頭。
    # 所以這不是拿誤擋換漏擋，是兩邊都拿到。
    if _EXEMPT_RE.search(mask_regions(command, keep_expandable=False,
                                      keep_comments=True)):
        return []

    structural = mask_regions(command, keep_expandable=False)
    expandable = mask_regions(command, keep_expandable=True)

    hits: list[str] = []

    # ① 管線 × 讀 rc（順序敏感 ＋ 跨語句污染）。
    if _rc_after_pipe(structural, expandable):
        hits.append(_RC_HINT)

    # ② 裸 cd／Set-Location（Push-Location／Pop-Location 不在此列）。
    if _NAKED_CD_RE.search(structural):
        hits.append(_CD_HINT)

    # ③ 裸 bash 跑 .sh（已走 Find-GitBash SSOT 者放行）。指令位置看結構面、
    #    `.sh` 佐證看原文，理由見 `_SH_SCRIPT_RE`。
    if (_BARE_BASH_RE.search(structural)
            and _SH_SCRIPT_RE.search(command)
            and not _FIND_GIT_BASH_RE.search(command)):
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
        sys.stderr.write(_HEADER + "\n\n".join(hits) + _FOOTER + "\n")
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring 的 P0
        return 0


if __name__ == "__main__":
    sys.exit(main())
