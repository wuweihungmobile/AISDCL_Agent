#!/usr/bin/env python3
"""每輪收尾的 session 逐字稿稽核器 —— PowerShell 工具面第一個觀測者。

WHY（本輪掃描的立案量測）
--------------------------
「Windows 上常犯低級錯誤」的機械層根因不是紀律不夠：本輪逐字稿實測顯示，
**有觀測者的那條規則違規 1 次且被當場擋下，沒有觀測者的那些規則違規率 20~35%**。
而整個 PowerShell 工具面在本輪之前**零觀測者**——鐵律二（禁裸 cd）、鐵律四
（宣稱先於查證）、以及「在對的 shell 裡現寫一段沒驗過的碼」，這三類的違規面
全部在**指令字串的內容**裡，而那個字串從來不會變成 repo 裡的檔案，於是全庫
所有靜態掃描器結構上都看不見它們。

但它們並非不可觀測：Claude Code 把每一次工具呼叫逐字寫進 session 逐字稿
（PreToolUse payload 的 `transcript_path` 欄就是那份檔案的權威路徑，本輪以
一支拋棄式 dump hook 實測確認）。repo 內此前**零消費者** ⇒ 這把「徹底解法」
從「要改 Claude Code」降級成「寫一支讀 jsonl 的稽核腳本」。本檔就是那支。

🔴 邊界：只能當量測器，不得接成閘門
------------------------------------
逐字稿是 **untracked、機器本地、隨時會被清掉**的資料。所以本檔：
  · **只能當每輪收尾的量測器**——跑一次、把四個數字與宣稱清單記進帳本；
  · **不得接成 push 閘門或 CI 閘門**。別台機器（或清過快取的同一台）上那個
    目錄根本不存在，接成硬閘在結構上恆紅，而恆紅的閘門會被整個關掉，比沒有
    鎖更糟（本 repo 的 ARCH-R59-NB4 判例逐字記載過這件事）。

它自己失效的偵測：**逐支逐字稿**檢查「有記錄、卻一支帶 command 的 shell 呼叫都
抽不到」⇒ fail-loud（rc=1）。掃描面崩塌（目錄搬家／欄位改名／正則失效）不得靜默
通過成「本輪零違規」——那個失效方向看起來正好像「變乾淨了」，比紅更危險。

🔴 為何崩塌判準必須是 per-session（R78 修 SD-03）
--------------------------------------------------
R77 版把這個判準建在**跨 session 合計**的 `shell_calls == 0` 上，而預設用法會把整個
逐字稿目錄（本機實測 51 支／109 MB）一起加總——那是一個**只會單調增長的歷史總量**。
於是「今天格式改了、今天起的每一支都抽不到東西」這個唯一要防的失效，被昨天以前的
四千多筆蓋掉，分支結構上打不出來。它識別了正確的危險方向，卻把判準建在打不到的
地方。改成逐支之後，格式一變，**當天新生的那一支就會讓 rc=1**。
搭配 `--since`／`--latest` 把量測窗縮到本輪那幾支，才是「本輪零違規」該有的分母。

誠實劃界：一支「真的整場沒用過 shell」的逐字稿（純問答／純讀檔）會被判成崩塌訊號。
本機 51 支實測是 0 支，但它是真實的假陽性面。處置是**去看那一支**並在交件寫明理由，
不是把判準關掉——沉默的方向比誤報危險。

🔴 為何計數必須逐工具（R78 修 SD-04）
--------------------------------------
四個形態全部是**PowerShell 工具面**的規則：鐵律二的裸 cd 講的是「PowerShell 工具的
cwd 跨呼叫持續」、`$LASTEXITCODE` 是 PS 概念、「不要寫裸 bash」講的是在 PS 指令裡
寫。R77 版把 Bash 與 PowerShell 兩個工具的指令混在同一個分母裡數，實測訊噪比慘烈：
裸 cd 43︰1820、裸 bash 0︰80（後者 100% 假陽性——在 Bash 工具裡寫 `bash x.sh`
本來就是對的）。更糟的是**方向性偏誤**：Bash 工具已被 `block_bash_on_windows.py`
擋掉 ⇒ 未來輪的 Bash 呼叫歸零 ⇒ 這兩個數字會自己「變好看」，而那不是真的改善。
`COMMAND_PATTERNS` 因此是 `{工具名: {形態: 正則}}` 二維結構，報表逐工具印、
每一列都標明分母是**哪一個工具**的呼叫數。`Bash` 的形態集合刻意是空的：這個工具
本身就是違規（鐵律一），量它的指令內容沒有意義，它只出現在 `bash_tool_attempts`。

判準的性質（誠實劃界）
----------------------
· 四個計數是**字串形態偵測**：量的是「出現過幾次這種寫法」，不是「有幾次真的
  造成了錯誤結果」。數量級可信，**確切值不可被引用成常數**。
· 宣稱對帳是**啟發式**：比對一句宣稱與它前面 N 個 tool_result 的內容有無可佐證
  字樣。它抓得到「完全沒有對應輸出的宣稱」，抓不到「有輸出但輸出被誤讀」。
  列出的每一筆都是**待人工看一眼的線索，不是判決**。

用法
----
    python tools/probe/audit_session.py                 # 本專案全部 session
    python tools/probe/audit_session.py --json
    python tools/probe/audit_session.py --transcript <某支 .jsonl>
    python tools/probe/audit_session.py --since 2026-08-06   # 只掃本輪那幾支
    python tools/probe/audit_session.py --latest 5           # 只掃最近改動的 5 支
    python tools/probe/audit_session.py --latest 5 --exclude-self   # 把自己剔出分母
    python tools/probe/audit_session.py --parity             # 兩端對拍，有分歧即 rc=1

🔴 量測窗會被「量測這件事本身」汙染（R79）
------------------------------------------
`--latest N` 是 **mtime 排序的浮動窗**，而每一支同期跑的 agent 都會在同一個逐字稿目錄
開一支新檔 ⇒ 派愈多 agent，窗裡就愈全是 agent、愈少是掌舵者本人，而 Q4 問的是掌舵者。
本輪實測：同一條指令在一小時內量到三組數字（PowerShell 分母 349→281→182）、rc 由 0
翻成 1，最後窗裡 5 支有 3 支是本輪自己派出去的掃描 agent，真正在做事的那支已被擠出去。
所以：
  · 報表**開頭固定印出量測窗清單**（檔名／mtime／PowerShell 呼叫數／開場白），
    帳本引用任何數字時必須連它一起記，否則下一個人重跑會拿到別的數字。
  · 要排除就用 `--exclude <子字串>`／`--exclude-self`（讀 `CLAUDE_CODE_SESSION_ID`）。
  · 誠實劃界：逐字稿裡**沒有**欄位能自動分辨「掌舵者 session」與「派出去的 agent」
    （`isSidechain`／`entrypoint`／`origin`／`userType`／`promptSource` 本輪逐欄實查，
    兩者取值相同），所以本檔不猜——它只把資訊攤開讓人一眼認得。

「觀測者上線前 vs 上線後」的分期量測（Q4；每輪重跑，確切百分比不得引為常數）——
把界線換成該觀測者落地那個 commit 的 author time（`git log --diff-filter=A --format=%aI
-- <hook 路徑>`），就得到可重跑的三期：

    --until 2026-08-03T16:26:15                              # 兩面皆無觀測者
    --since 2026-08-03T16:26:15 --until 2026-08-07T00:05:53  # 只有 Bash 工具被擋
    --since 2026-08-07T00:05:53                              # PowerShell 面也有觀測者
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from collections import deque
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 🔴 攔截端的**純函式**（遮蔽器與規則①的順序敏感判準）直接向 hook 借，不再抄第二份。
# 依賴方向是 `tools/probe → .claude/hooks`，與 `tools/session_resume_planner.py`
# 同一條理由且不可反向：那支 hook 由 `runpy.run_path` 起、`sys.path` 上既沒有
# `tools/` 也沒有 `.claude/hooks/`，它 import 誰都會在 import 期爆掉，而模組層爆掉
# 會破壞它的 fail-open 契約 ⇒ 它永遠只能是被借的一方。
# 這也是為什麼 `SHARED_PATTERN_SOURCE` 那張表只能留複本（它在 hook 的模組層被用到），
# 而**函式**不必：本檔是 import 的一方，借得到就不該再抄。
# 🔴 這段刻意住在檔案最前面（R79 由下方上移）：規則①的量測端現在就是攔截端那支
# 函式，形態表在定義時就要用得到它。
_HOOK_PATH = _REPO_ROOT / ".claude" / "hooks" / "lint_powershell_command.py"
_hook_spec = importlib.util.spec_from_file_location("_lint_ps_hook", _HOOK_PATH)
_lint_ps_hook = importlib.util.module_from_spec(_hook_spec)
_hook_spec.loader.exec_module(_lint_ps_hook)
mask_regions = _lint_ps_hook.mask_regions

#: 🔴 **事後量測（本檔）與事中攔截（`.claude/hooks/lint_powershell_command.py`）
#: 共用的判準字面**。兩邊各存一份逐字相同的複本，因為那支 hook 由 `runpy.run_path`
#: 起、`sys.path` 上沒有 `tools/`，import 期爆掉會破壞它的 fail-open 契約 ⇒ 它只能是
#: 被抄的一方。代價已經發生過（R77：hook 那份有 `Tee-Object`、本檔那份沒有，兩份零
#: 比對 ⇒ 同一條規則「攔得下、卻量不到」）。既然結構上只能留複本，就把複本的
#: **一致性**變成會轉紅的事件，見 `tools/tests/test_check_hooks_liveness.py` 的
#: `TestHookAndProbeShareOneCriterion`（字面相等 ＋ 行為一致，兩向）。
#:
#: 🔴 修改守則：本字典要與 hook 那份**逐字相同**（連換行位置都相同才好 diff）。
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

def _rc_after_pipe(command: str) -> bool:
    """規則①的量測端＝**攔截端那支函式本身**（R79；不再自寫第二份判準）。

    🔴 為何非借不可：上一版是一條扁平正則 `\\|…[^\\n]*\\n?[^\\n]*LASTEXITCODE`，
    它與攔截端在**兩個相反方向**同時失準，而兩個方向都會污染 Q4 的結論：
      · 低報——`\\n?` 把視窗硬綁在「最多跨一個換行」，於是「管線與 rc 之間隔 ≥1 行」
        的多行指令整類看不見；攔截端的污染則是延續到某句真的重設 rc 為止。多行指令
        在本 repo 極常見 ⇒ 系統性低估，而低估的樣子看起來像「變乾淨了」。
      · 高報——它不切語句、不比位置、不認 rc 重設，於是把根 CLAUDE.md 逐字教的正解
        （先接變數 → 立刻讀 rc → 再用管線篩那個變數）算成違規。**方向是「越遵守規則、
        違規率越高」**，用它做的歸因符號相反。
    借過來之後，這個欄位的語意才真的等於「攔截器會擋的那件事」，兩端也不可能再漂移。
    """
    return bool(_lint_ps_hook._rc_after_pipe(
        mask_regions(command, keep_expandable=False),
        mask_regions(command, keep_expandable=True),
    ))


#: PowerShell 工具面的形態偵測器。鍵即報表欄名。值是 `str -> truthy/falsy` 的**可呼叫**
#: （正則就用它的 `.search`）——規則①借的是攔截端的函式，不是正則，所以型別必須放寬。
#:
#: 🔴 R79 把 `inline-loop` 拆成兩欄，舊欄名**刻意不保留**：實測 latest-5 窗的 30 筆
#: 命中裡有 20 筆是 `| ForEach-Object { $_.Name }` 這種一行投影（慣用管線），與註解
#: 宣稱要抓的「現寫一段沒人驗過的控制流」不是同一種風險。混在同一個分子裡，那個
#: 百分比既不能解讀也不能拿來判斷有沒有變好。舊名沿用新語意才是真正的陷阱（同一個
#: 名字兩種意思），所以直接改名：帳本上的舊 `inline-loop` 數字與新兩欄**不可比較**。
_POWERSHELL_PATTERNS: dict[str, object] = {
    # 讀 rc 時接了管線：pwsh 7.x 提前中斷管線時不更新 $LASTEXITCODE（保留前值），
    # PS 5.1 則寫入 -1 —— 兩個方向都讓 rc 不可信，且「真紅被讀成綠」是其中一種。
    "rc-after-pipe": _rc_after_pipe,
    # 現寫的控制流：沒有任何測試看過這段碼，寫錯了只會表現成「數字怪怪的」。
    "inline-loop-statement": re.compile(
        r"\b(foreach\s*\(|for\s*\(\s*\$)", re.IGNORECASE
    ).search,
    # 慣用管線投影（`| ForEach-Object { … }`／`| % { … }`）。與上一欄分開記：它是
    # PowerShell 的日常寫法，不是「現寫的沒驗過的碼」，而且**沒有攔截端**（見
    # `_INTERCEPTED_KEYS`）⇒ 結構上不可能被壓到 0。
    "pipeline-foreach": re.compile(
        r"\|\s*(ForEach-Object(?![\w-])|%(?=\s|\{|$))", re.IGNORECASE
    ).search,
    # 鐵律二：PowerShell 工具的 cwd 跨呼叫持續，裸 cd 之後的相對路徑全部會找錯地方。
    # 🔴 R78／SD-01：邊界由 `(?:^|;)` 擴成與 hook 同一組「下一個指令從這裡開始」的
    # 入口（`&&`／`||`／`|`／`{`／`(` 之後）。上一版兩邊邊界不同 ⇒ 同一段違規
    # 「攔得下、卻量不到」，正是這兩份複本要被綁在一起的理由。
    "naked-cd": re.compile(
        r"(?:^|[;\n|&{}()])\s*" + SHARED_PATTERN_SOURCE["naked-cd"], re.IGNORECASE
    ).search,
    # 裸 bash：Get-Command bash 解析到 system32 的 WSL 佔位版，且反斜線分隔符被吃掉。
    # 共用字面只到動詞為止（見上）＝這裡只認**指令位置**；「跑的是不是 .sh」交給
    # `_CORROBORATORS`，理由與 hook 同一條：路徑常寫在引號裡，遮蔽面上看不到 `.sh`。
    "bare-bash-sh": re.compile(
        r"(?:^|[;\n|&{}()])\s*" + SHARED_PATTERN_SOURCE["bare-bash-sh"],
        re.IGNORECASE,
    ).search,
}

#: 有**事中攔截端**的形態（＝`lint_powershell_command.py` 真的會擋的那三條）。
#: 其餘只有量測、沒有攔截 ⇒ 它們結構上不可能被壓到 0，報表必須就地標明；否則一個
#: 永遠非零的數字會被讀成「一直沒人處理的違規」，而其實根本沒有人在擋它。
_INTERCEPTED_KEYS = frozenset({"rc-after-pipe", "naked-cd", "bare-bash-sh"})

#: `{工具名: {形態: 正則}}`。逐工具是刻意的——見檔頭〈為何計數必須逐工具〉：
#: 這四個形態全部只約束 PowerShell 工具，混進 Bash 的指令會得到 97.7%／100% 的假陽性，
#: 而且那組數字會隨「Bash 工具被擋掉」自己變好看，方向性偏誤比雜訊更糟。
#: `Bash` 的形態集合刻意留空且**不得刪除這個鍵**：它同時是 `SHELL_TOOLS` 的來源，
#: 少了它 `bash_tool_attempts` 的分母（Bash 帶 command 的呼叫數）就沒人數。
COMMAND_PATTERNS: dict[str, dict[str, re.Pattern[str]]] = {
    "PowerShell": _POWERSHELL_PATTERNS,
    "Bash": {},
}

#: 帶 `command` 欄、會落進本稽核射程的工具（由上表推導，不另立第二個家）。
SHELL_TOOLS = tuple(COMMAND_PATTERNS)

#: 助理訊息裡「我已經驗過了」形態的句子。
CLAIM_RE = re.compile(r"(全綠|已驗證|全部通過|rc\s*=\s*0|\bpassed\b|\bPASS\b)")

#: 佐證字樣。🔴 R79 收窄，理由是實測：上一版在本輪那個窗判出率 **0/72**、全史
#: **17/706（2.4%）**，而報表最後一行的那個 `0` 讀起來就是「這一輪沒有失實宣稱」——
#: 正是本檔自己警告的「看起來變乾淨」方向，比紅更危險，因為沒有人會去追一個 0。
#: 逐句追出讓它放行的字樣：`✅` 18 次、裸 `ok`／`OK` 7 次——一個是純裝飾字元、一個是
#: 英文常用詞，兩者零鑑別力（`ok` 甚至會被中文說明裡的英文字命中）。現在只留下
#: 「真的是某次執行的輸出」才會有的形狀；`OK` 保留但**必須自成一行的行首**
#: （＝unittest 終端那個 OK），這樣散文裡的 ok 不再構成佐證。
EVIDENCE_RE = re.compile(
    r"(rc\s*=\s*0|Exit code:\s*0|\b\d+\s+passed\b|All checks passed|(?m:^OK\b))",
    re.IGNORECASE,
)

#: 宣稱往回看幾個 tool_result。🔴 R79 由 12 改為 3。往回看 12 個再把它們**拼成一坨**
#: 去比對，等於「前面任何一支測試印過 rc=0，之後 12 個回合內的任何宣稱都自動獲得
#: 佐證」——佐證與那句宣稱指的是哪一次執行毫無關聯，條件近乎恆真。
#:
#: 選 3 不是拍腦袋，是對全史 707 句宣稱做過敏感度掃描（新的 `EVIDENCE_RE` 之下）：
#:     window= 1 → 398 判無佐證（56.3%）    window= 6 →  99（14.0%）
#:     window= 2 → 299（42.3%）             window=12 →  34（ 4.8%）
#:     window= 3 → 227（32.1%）
#: 兩端都沒有用：1 會把「連續講兩句、佐證在第一句前面」全部誤判（清單長到沒人看），
#: 12 則回到近乎恆真。3 的量級是「一句宣稱通常指的是它前面那一兩次執行」。
#: 🔴 這個數字是**判準的一部分**，不是常數：報表會把它與分子分母一起印，任何人引用
#: 那個百分比時必須連窗一起引，否則換一個窗就是另一個數字。
#: 誠實劃界：這仍是啟發式，列出的每一筆是**待人工看一眼的線索，不是判決**。
DEFAULT_WINDOW = 3

#: 兩處與攔截器同義的**放行**面。量測器若不跟著放行，同一段指令會「攔截器說沒事、
#: 量測器記一筆違規」——那個差距會直接灌進 Q4 的違規率，而 Q4 是拿來下結論的。
#: （放行不等於消失：豁免另計在 `exempted_calls`，靜默丟掉才是「看起來變乾淨」。）
#: 🔴 這兩個字面**不進 `SHARED_PATTERN_SOURCE`**：那張表是「違規長什麼樣」，
#: 放行條件是另一件事，混進去會讓字面相等鎖的語意變成兩種東西的混合。
#: 它們與 hook 的對應項是否同步，由行為一致鎖（同一批指令兩邊判定必須一致）覆蓋。
#: 🔴 R79：比對面與攔截端一起改成「**只認住在真註解裡**的標記」（見 `_exempt`）。
EXEMPT_RE = re.compile(r"#\s*ps-lint-ok:\s*\S")


def _exempt(command: str) -> bool:
    """行內豁免是否成立——與攔截端同一個判準（同一支遮蔽器、同一個模式）。

    比對的是「註解原樣留、字串照樣遮」那一面：任何在字串裡**引述**這個標記的指令
    （寫文件、寫探針、在訊息裡舉例違規形態）不再一次關掉全部檢查。
    """
    return bool(EXEMPT_RE.search(
        mask_regions(command, keep_expandable=False, keep_comments=True)))
_FIND_GIT_BASH_RE = re.compile(r"Find-GitBash", re.IGNORECASE)

#: `key -> 抑制條件`：命中了、但屬於 repo 明文指定的正解，不計為違規。
_SUPPRESSORS: dict[str, re.Pattern[str]] = {"bare-bash-sh": _FIND_GIT_BASH_RE}

#: `key -> 佐證條件（比對**原文**）`：指令位置從遮蔽過的結構面讀、佐證從原文讀。
#: 為何要拆兩面：`bash "tools/x.sh"` 的路徑住在引號裡，遮蔽面上看不到 `.sh`；而
#: `$doc = "…bash tools/x.sh…"` 在原文上看得到 `bash` 卻不是指令。兩面各取所長。
_CORROBORATORS: dict[str, re.Pattern[str]] = {
    "bare-bash-sh": re.compile(r"\.sh(?![\w])", re.IGNORECASE)
}

def comparison_surfaces(command: str) -> dict[str, str]:
    """`形態 key -> 該餵哪一面給它的偵測器`。

    · **結構面**（引號／here-string／註解全遮）給「指令位置」類的形態：`cd`／`bash`
      寫在字串或註解裡都不是指令，計進去就是純雜訊（R78／SD-02：hook 那邊同一批
      形態實測三條規則全誤擋）。
    · **原文**給 `rc-after-pipe`：R79 起這一欄的偵測器就是攔截端那支函式，它自己要
      同時用到結構面與展開面**比位置**（管線在前還是 rc 在前），所以只能拿到原文。
      上一版在這裡只餵展開面、再由本檔自寫的扁平正則判，那正是兩端判定分歧的來源。
    """
    structural = mask_regions(command, keep_expandable=False)
    return {
        "rc-after-pipe": command,
        "inline-loop-statement": structural,
        "pipeline-foreach": structural,
        "naked-cd": structural,
        "bare-bash-sh": structural,
    }


def project_transcript_dir(repo_root: Path) -> Path:
    """`repo_root` 對應的 Claude Code 逐字稿目錄。

    slug 規則＝把路徑裡每個非英數字元換成 `-`（本機實測：`d:\\CursorProject\\
    AISDCL_Agent` → `d--CursorProject-AISDCL-Agent`）。這是**觀察到的**編碼方式，
    不是官方契約，所以 `--project-dir` 一律可覆寫，而目錄不存在時 fail-loud。
    """
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo_root))
    return Path.home() / ".claude" / "projects" / slug


def iter_records(path: Path):
    """逐行 yield 解析得出的 jsonl 記錄（壞行直接跳過，逐字稿常有半截尾行）。"""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec


def _blocks(rec: dict) -> tuple[str, list]:
    msg = rec.get("message")
    if not isinstance(msg, dict):
        return "", []
    content = msg.get("content")
    return str(msg.get("role") or ""), content if isinstance(content, list) else []


def _result_text(block: dict) -> str:
    """tool_result 區塊的文字內容（content 可能是 str，也可能是區塊清單）。"""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(b.get("text") or "") for b in content if isinstance(b, dict)
        )
    return ""


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？!?\n])", text)
    return [p.strip() for p in parts if p.strip()]


def _user_prompt_text(rec: dict) -> str:
    """user 角色訊息的純文字（可能是 str，也可能是區塊清單）。空字串＝不是人打的話。"""
    msg = rec.get("message")
    if not isinstance(msg, dict) or msg.get("role") != "user":
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text") or "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def detector_hits(command: str, detectors: dict) -> set[str]:
    """一條指令在 `detectors` 底下命中的形態集合（純函式，供對拍與注入自證）。"""
    surfaces = comparison_surfaces(command)
    hits: set[str] = set()
    for key, detect in detectors.items():
        suppressor = _SUPPRESSORS.get(key)
        corroborator = _CORROBORATORS.get(key)
        if (detect(surfaces.get(key, command))
                and (corroborator is None or corroborator.search(command))
                and not (suppressor and suppressor.search(command))):
            hits.add(key)
    return hits


#: 攔截端只透過 stderr 的 hint 對外表示它判了哪一條，所以由 hint 的特徵字反推規則。
#: 這三個字面同時是 `tools/tests/test_check_hooks_liveness.py` 的 `MUST_BLOCK` 在斷言的
#: 「擋了要指出出口」那個 needle ⇒ 改了 hint 會在那邊先紅，本表不會靜默過期。
_HOOK_RULE_BY_HINT: dict[str, str] = {
    "rc-after-pipe": "LASTEXITCODE",
    "naked-cd": "Push-Location",
    "bare-bash-sh": "Find-GitBash",
}


def hook_rules(command: str) -> set[str]:
    """攔截端對這條指令判了哪幾條規則（純函式，供對拍）。"""
    joined = "\n".join(_lint_ps_hook.lint_command(command))
    return {key for key, needle in _HOOK_RULE_BY_HINT.items() if needle in joined}


def parity_divergences(commands) -> list[dict]:
    """攔截端 × 量測端對**同一批真實指令**的判定分歧（`[]`＝沒有分歧）。

    🔴 為何要有這支：R78 宣稱兩端「修之後判定分歧 0 例」，而守那句話的鎖餵的是十來條
    手寫短指令——那組語料裡沒有一條跨三行、沒有一條在管線之後另起一次呼叫，於是它
    **結構上**看不到分歧，永遠是綠的。真實逐字稿上當時的分歧是兩位數。這支讓那個
    宣稱變成可重跑的量測，語料是真的流量而不是自己挑的樣本。

    只比三條「兩端都有」的規則（`_HOOK_RULE_BY_HINT`）：其餘欄位只有量測端，對拍
    無意義。行內豁免兩端一致放行，直接跳過。
    """
    out: list[dict] = []
    for command in commands:
        if _exempt(command):
            continue
        theirs = hook_rules(command)
        mine = detector_hits(command, _POWERSHELL_PATTERNS) & set(_HOOK_RULE_BY_HINT)
        if theirs != mine:
            out.append({"command": command[:400], "hook": sorted(theirs),
                        "probe": sorted(mine)})
    return out


def powershell_commands(paths: list[Path]) -> list[str]:
    """量測窗內出現過的 unique PowerShell 指令（出現序，供對拍用）。"""
    seen: dict[str, None] = {}
    for path in paths:
        for rec in iter_records(path):
            _role, blocks = _blocks(rec)
            for block in blocks:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if block.get("name") != "PowerShell":
                    continue
                inp = block.get("input")
                cmd = inp.get("command") if isinstance(inp, dict) else None
                if isinstance(cmd, str) and cmd:
                    seen.setdefault(cmd, None)
    return list(seen)


def scan_transcript(path: Path, window_size: int = DEFAULT_WINDOW) -> dict:
    """單支逐字稿的量測結果（純資料，報表與 rc 由呼叫端決定）。"""
    counts = {tool: dict.fromkeys(pats, 0) for tool, pats in COMMAND_PATTERNS.items()}
    shell_by_tool = dict.fromkeys(COMMAND_PATTERNS, 0)
    exempted = 0
    tool_totals: dict[str, int] = {}
    records_total = 0
    window: deque[str] = deque(maxlen=max(1, window_size))
    unsupported: list[str] = []
    claims_total = 0
    session_id = ""
    first_prompt = ""

    for rec in iter_records(path):
        records_total += 1
        if not session_id:
            session_id = str(rec.get("sessionId") or "")
        if not first_prompt:
            first_prompt = " ".join(_user_prompt_text(rec).split())[:110]
        role, blocks = _blocks(rec)
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "tool_use":
                name = str(block.get("name") or "")
                tool_totals[name] = tool_totals.get(name, 0) + 1
                inp = block.get("input")
                cmd = inp.get("command") if isinstance(inp, dict) else None
                if name not in COMMAND_PATTERNS or not isinstance(cmd, str) or not cmd:
                    continue
                shell_by_tool[name] += 1
                if _exempt(cmd):
                    exempted += 1  # 攔截器放行的，量測器也放行（但另計，見常數旁註解）
                    continue
                for key in detector_hits(cmd, COMMAND_PATTERNS[name]):
                    counts[name][key] += 1
            elif kind == "tool_result":
                window.append(_result_text(block))
            elif kind == "text" and role == "assistant":
                corpus = "\n".join(window)
                for sentence in _sentences(str(block.get("text") or "")):
                    if not CLAIM_RE.search(sentence):
                        continue
                    claims_total += 1  # 🔴 分母也要記：只印分子時，「CLAIM_RE 自己
                    # 失效」與「真的零違規」長得一模一樣。
                    if not EVIDENCE_RE.search(corpus):
                        unsupported.append(sentence[:200])

    shell_calls = sum(shell_by_tool.values())
    return {
        "transcript": path.name,
        # 🔴 窗的可回查性（R79）：帳本記的每一個數字都必須能指回「是哪幾支、什麼時候、
        # 誰在講話」。`--latest N` 是 mtime 排序的浮動窗，而每一支同期跑的 agent 都會
        # 在同一個目錄開一支新逐字稿 ⇒ 同一條指令隔一小時就給不同答案（本輪實測：
        # 同一條交棒書指令三次量到三組數字、rc 由 0 翻 1）。這三個欄位讓那件事**看得見**。
        "session_id": session_id,
        "first_prompt": first_prompt,
        # 逐字稿最後寫入時間。**時間切片的唯一依據**：Q4 那種「觀測者上線前 vs 上線後」
        # 的比較必須能重跑，把切片留在下游腳本裡就等於下一輪要重寫一次。
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "records": records_total,
        "tool_use_total": sum(tool_totals.values()),
        "by_tool": tool_totals,
        "shell_calls": shell_calls,
        "shell_calls_by_tool": shell_by_tool,
        "exempted_calls": exempted,
        "bash_tool_attempts": tool_totals.get("Bash", 0),
        "patterns": counts,
        # 逐支崩塌訊號（見檔頭〈為何崩塌判準必須是 per-session〉）：**有記錄**卻
        # 一支帶 command 的 shell 呼叫都抽不到。用 `records` 而不是 `tool_use_total`
        # 當前提，是因為「連 tool_use 都認不出來」正是最徹底的那種格式變更——
        # 拿它當前提會讓最該紅的情形自己把判準關掉。
        "collapsed": records_total > 0 and shell_calls == 0,
        "unsupported_claims": unsupported,
        # 分母（命中 CLAIM_RE 的句子總數）。只印分子時，「CLAIM_RE 失效」與「真的
        # 零違規」長得一模一樣，而後者是沒有人會去追的那一種。
        "claims_total": claims_total,
        # 判準的一部分：換一個窗就是另一個數字，所以它必須跟著數字一起走。
        "claim_window": window_size,
    }


def aggregate(results: list[dict]) -> dict:
    """跨 session 合計 —— 帳本要記的數字。**逐工具**，見檔頭 SD-04 那一段。"""
    totals = {tool: dict.fromkeys(pats, 0) for tool, pats in COMMAND_PATTERNS.items()}
    shell_by_tool = dict.fromkeys(COMMAND_PATTERNS, 0)
    bash_attempts = 0
    exempted = 0
    claims = 0
    claims_total = 0
    for res in results:
        bash_attempts += res["bash_tool_attempts"]
        exempted += res["exempted_calls"]
        claims += len(res["unsupported_claims"])
        claims_total += res["claims_total"]
        for tool, value in res["shell_calls_by_tool"].items():
            shell_by_tool[tool] = shell_by_tool.get(tool, 0) + value
        for tool, per_tool in res["patterns"].items():
            for key, value in per_tool.items():
                totals.setdefault(tool, {})[key] = totals.get(tool, {}).get(key, 0) + value
    return {
        "sessions": len(results),
        "shell_calls": sum(shell_by_tool.values()),
        "shell_calls_by_tool": shell_by_tool,
        "exempted_calls": exempted,
        "bash_tool_attempts": bash_attempts,
        "patterns": totals,
        "collapsed_sessions": [r["transcript"] for r in results if r["collapsed"]],
        "unsupported_claim_count": claims,
        "claim_sentences_total": claims_total,
        "claim_window": results[0]["claim_window"] if results else DEFAULT_WINDOW,
        # 窗的定義本身也是資料：帳本引用任何一個數字時必須連它一起記，否則下一個人
        # 重跑會拿到別的數字然後去找一個不存在的原因。
        "window_manifest": [
            {"transcript": r["transcript"], "session_id": r["session_id"],
             "mtime": r["mtime"], "records": r["records"],
             "powershell_calls": r["shell_calls_by_tool"].get("PowerShell", 0),
             "first_prompt": r["first_prompt"]}
            for r in results
        ],
    }


def collapse_verdict(summary: dict) -> str | None:
    """`None`＝掃描面健在；回字串＝掃描面崩塌的理由（純函式，供注入自證）。

    三款，由窄到寬：掃不到檔／**某幾支**抽不到 shell 呼叫／整批合計為零。
    第二款是 R78 補上的那一款，也是唯一一款在預設用法下真的打得到的
    （前一版只有第一、三款，而第三款是歷史總量 ⇒ 結構上不可達，見檔頭 SD-03）。
    """
    if summary["sessions"] == 0:
        return ("掃不到任何 session 逐字稿——目錄不存在／已被清空／`--since`、`--latest` "
                "把窗縮到空。本檔是量測器不是閘門，但『量到零』與『量不到』必須分得開")
    collapsed = summary.get("collapsed_sessions") or []
    if collapsed:
        return (f"有記錄、卻一支帶 command 的 shell 呼叫都抽不到：{collapsed} ⇒ 掃描面"
                "對這幾支崩塌（欄位改名／記錄格式變更／COMMAND_PATTERNS 的工具鍵過期）。"
                "這個失效方向看起來像『變乾淨了』，比紅更危險，故 fail-loud。"
                "若確認那幾支真的整場沒用過 shell（純問答／純讀檔），"
                "用 --transcript／--since／--latest 把量測窗縮到本輪那幾支再跑")
    if summary["shell_calls"] == 0:
        return ("帶 command 的 shell 呼叫數為 0 ⇒ 掃描面崩塌（逐字稿全為空檔？），"
                "不是『本輪零違規』")
    return None


def _print_pattern_block(patterns: dict, shell_by_tool: dict, indent: str) -> None:
    """逐工具印形態計數。**每一列都帶自己的分母**——混用分母正是 SD-04 那一筆。"""
    for tool, per_tool in patterns.items():
        denominator = shell_by_tool.get(tool, 0)
        if not per_tool:
            print(f"{indent}[{tool}] 帶 command 的呼叫 {denominator}"
                  f"（本工具無形態判準：鐵律一已禁用它，工具存在本身即違規）")
            continue
        print(f"{indent}[{tool}] 帶 command 的呼叫 {denominator}（＝以下各列的分母）")
        for key, value in per_tool.items():
            pct = 100.0 * value / denominator if denominator else 0.0
            note = "" if key in _INTERCEPTED_KEYS else "  ← 僅量測，無攔截端"
            print(f"{indent}  {key:22s} {value:5d}  "
                  f"({pct:.1f}% of {tool} calls){note}")


def _print_window_manifest(summary: dict) -> None:
    """🔴 報表**開頭**固定印出「這一次到底量了哪幾支」（R79）。

    為何是必印而不是選項：`--latest N` 的窗由 mtime 排序決定，而每一支同期跑的 agent
    都會在同一個目錄開一支新逐字稿 ⇒ **量測這個動作本身會改變下一次的量測值**。
    本輪實測：同一條交棒書指令在一小時內給出三組數字、rc 由 0 翻成 1，而窗裡最後
    只剩掃描 agent、真正在做事的那支已被擠出去。任何人照著重跑都會拿到與帳本不同的
    數字，然後去找一個不存在的原因。把窗的定義印出來，那件事至少**看得見**。

    誠實劃界：逐字稿裡**沒有**任何欄位能區分「掌舵者的 session」與「派出去的 agent」
    （本輪逐欄實查 `isSidechain`／`entrypoint`／`origin`／`userType`／`promptSource`
    在兩者上取值相同）。所以本函式不做自動分類，只把 `first_prompt` 印出來讓人一眼
    認得；要排除就用 `--exclude` / `--exclude-self`，那是明示而非猜測。
    """
    manifest = summary.get("window_manifest") or []
    print(f"### 量測窗（{len(manifest)} 支；引用任何數字時請連本段一起記）")
    for row in manifest:
        print(f"  · {row['transcript']}  mtime={row['mtime']}  "
              f"記錄={row['records']}  PowerShell={row['powershell_calls']}")
        print(f"      開場白: {row['first_prompt'] or '（無 user 文字訊息）'}")


def _print_report(results: list[dict], summary: dict, max_claims: int) -> None:
    _print_window_manifest(summary)
    for res in results:
        by_tool = res["by_tool"]
        print(f"\n### {res['transcript']}{'  ⚠️ 崩塌訊號' if res['collapsed'] else ''}")
        print(f"  記錄 {res['records']}  tool_use 總數: {res['tool_use_total']}  |  "
              f"Bash={by_tool.get('Bash', 0)}  PowerShell={by_tool.get('PowerShell', 0)}")
        _print_pattern_block(res["patterns"], res["shell_calls_by_tool"], "    ")
        claims = res["unsupported_claims"]
        if claims:
            print(f"  無對應輸出的宣稱: {len(claims)} / {res['claims_total']} 句宣稱"
                  "（啟發式，需人工看一眼）")
            for sentence in claims[:max_claims]:
                print(f"    · {sentence}")
            if len(claims) > max_claims:
                print(f"    …另有 {len(claims) - max_claims} 句（--max-claims 可調）")

    print(f"\n### 合計（{summary['sessions']} 支逐字稿；帳本要記的數字）")
    print("  🔴 逐工具分開記——不同工具的指令不共用分母（見檔頭 SD-04）")
    _print_pattern_block(summary["patterns"], summary["shell_calls_by_tool"], "  ")
    print(f"  Bash 工具嘗試數（鐵律一違規本身）  {summary['bash_tool_attempts']}")
    print(f"  行內豁免而未計形態的呼叫           {summary['exempted_calls']}")
    # 🔴 分子與分母**與窗**一起印：只印分子時，「CLAIM_RE 自己失效（分母崩了）」與
    # 「真的零違規」印出來一模一樣，而後者沒有人會去追；不印窗則換個窗就是另一個數字。
    print(f"  無對應輸出的宣稱                   "
          f"{summary['unsupported_claim_count']} / "
          f"{summary['claim_sentences_total']} 句命中 CLAIM_RE"
          f"（往回看 {summary['claim_window']} 個 tool_result）")
    if summary["collapsed_sessions"]:
        print(f"  ⚠️ 崩塌訊號的逐字稿                {summary['collapsed_sessions']}")


def select_paths(paths: list[Path], since: str | None = None, until: str | None = None,
                 latest: int | None = None,
                 exclude: list[str] | None = None) -> list[Path]:
    """把量測窗縮到「本輪那幾支」。**沒有這個，崩塌判準就只能對著歷史總量說話**。

    `since`／`until` 吃 ISO（`2026-08-07` 或 `2026-08-07T00:05:53`），以檔案 mtime 篩；
    `latest`＝只留最近改動的 N 支；`exclude`＝檔名含任一子字串者剔除。四者可疊加。
    窗篩空時**不吞掉**——回空清單讓 `collapse_verdict` 說「量不到」。

    🔴 `until` 存在的理由不是對稱美感：「觀測者上線**前** vs **後**」這種分期比較
    需要一個右界，沒有它就只能靠下游腳本自己切，而下游腳本下一輪不會有人重跑。
    誠實劃界：mtime 是**最後寫入**時間，跨越分界點的長 session 會整支落在後段。

    🔴 `exclude` 存在的理由（R79）：`latest` 是 mtime 浮動窗，而**量測者自己**與同期
    跑的每一支 agent 都在同一個目錄開新逐字稿 ⇒ 派愈多 agent，窗裡就愈全是 agent、
    愈少是掌舵者本人，而問題問的是掌舵者。剔除**必須是明示的**：逐字稿裡沒有任何欄位
    能可靠地區分兩者（本輪逐欄實查），猜錯的代價是把真正在做事的那支丟掉。
    `exclude` 在 `latest` **之前**套用，否則被剔掉的那幾支仍會先把別人擠出窗外。
    """
    files = [p for p in paths if p.is_file()]
    for needle in exclude or []:
        if needle:
            files = [p for p in files if needle not in p.name]
    if since:
        low = datetime.fromisoformat(since).timestamp()
        files = [p for p in files if p.stat().st_mtime >= low]
    if until:
        high = datetime.fromisoformat(until).timestamp()
        files = [p for p in files if p.stat().st_mtime < high]
    files.sort(key=lambda p: p.stat().st_mtime)
    if latest is not None:
        files = files[-latest:] if latest > 0 else []
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-dir", help="逐字稿目錄（覆寫 slug 推導）")
    parser.add_argument("--transcript", action="append", default=[],
                        help="直接指定一支 .jsonl（可重複）")
    parser.add_argument("--since", help="只掃 mtime >= 此 ISO 時刻的逐字稿"
                                        "（2026-08-07 或 2026-08-07T00:05:53）")
    parser.add_argument("--until", help="只掃 mtime < 此 ISO 時刻的逐字稿"
                                        "（與 --since 併用即『觀測者上線前／後』分期）")
    parser.add_argument("--latest", type=int,
                        help="只掃最近改動的 N 支（每輪量測建議搭配它或 --since）")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help=f"宣稱往回看幾個 tool_result（預設 {DEFAULT_WINDOW}）")
    parser.add_argument("--exclude", action="append", default=[],
                        help="檔名含此子字串的逐字稿不納入量測窗（可重複）；"
                             "在 --latest 之前套用")
    parser.add_argument("--exclude-self", action="store_true",
                        help="剔除**正在跑這支腳本的那個 session**（讀環境變數 "
                             "CLAUDE_CODE_SESSION_ID）。量測者把自己算進分母時，"
                             "跑量測這個動作本身就會改變量測值")
    parser.add_argument("--max-claims", type=int, default=10)
    parser.add_argument("--parity", action="store_true",
                        help="把量測窗裡每一條 unique PowerShell 指令同時餵給攔截端與"
                             "量測端，列出判定分歧（有分歧即 rc=1）")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    exclude = list(args.exclude)
    if args.exclude_self:
        own = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
        if own:
            exclude.append(own)
        else:
            # fail-loud 而不是靜默略過：以為排除了、其實沒排除，正是本旗標要治的病。
            print("⚠️ --exclude-self：環境變數 CLAUDE_CODE_SESSION_ID 是空的 ⇒ "
                  "無法辨識自己這一支，本次未剔除任何東西", file=sys.stderr)

    if args.transcript:
        candidates = [Path(p) for p in args.transcript]
    else:
        base = Path(args.project_dir) if args.project_dir else \
            project_transcript_dir(_REPO_ROOT)
        candidates = sorted(base.glob("*.jsonl")) if base.is_dir() else []

    paths = select_paths(candidates, args.since, args.until, args.latest, exclude)
    results = [scan_transcript(p, args.window) for p in paths]
    summary = aggregate(results)
    verdict = collapse_verdict(summary)

    commands = powershell_commands(paths) if args.parity else []
    divergences = parity_divergences(commands) if args.parity else []
    if args.parity:
        summary["parity_commands"] = len(commands)
        summary["parity_divergences"] = len(divergences)

    if args.as_json:
        payload = {"sessions": results, "summary": summary,
                   "collapse_verdict": verdict}
        if args.parity:
            payload["parity"] = divergences
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_report(results, summary, args.max_claims)
        if args.parity:
            print(f"\n### 攔截端 × 量測端對拍（{len(commands)} 條 unique 指令）")
            print(f"  判定分歧 {len(divergences)} 筆")
            for row in divergences[:args.max_claims]:
                print(f"    · hook={row['hook']} probe={row['probe']}")
                print(f"      {row['command'][:200]}")
        if verdict:
            print(f"\n❌ {verdict}")

    return 1 if (verdict or divergences) else 0


if __name__ == "__main__":
    sys.exit(main())
