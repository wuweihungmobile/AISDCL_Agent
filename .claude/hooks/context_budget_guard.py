#!/usr/bin/env python
"""PostToolUse 守衛：Claude Code session 的 context 水位觀測者（本 repo 首見）。

WHY
---
掌舵者連續多輪指名要兩件事：「注意上下文是否超出 90%，進行 /compact，不要爆」與
「注意 Token 限制，適當進行排程再喚醒繼續處理」。實查**四處**：

  · 根 `.claude/settings.json`：SessionStart/PreToolUse/PostToolUse 全部條目裡
    沒有任何一支在看 token 或 context；
  · `AutoClaude` Kernel 的 Token Guard（≥80% `/compact`、≥90% checkpoint ＋
    `scheduled_resume_at`）活在 **playbook 執行迴圈**裡，對 Claude Code session
    本身一行都不生效——它守的是被驅動的那個東西，不是驅動者；
  · 根 `CLAUDE.md`〈Token 將耗盡時的「無害暫停 → reset 後重啟」SOP〉是**純人工程序**；
  · 🔴 **第四處＝harness 自己**（R79 補上；R78 版的這段 docstring 逐字寫「實查三處」
    而漏了它，等於在說「沒人在自動 compact」——與磁碟不符）。實測 `claude --version`
    ＝2.1.223、`claude --help` 有 `--autocompact <auto|tokens>  Auto-compact window
    size (auto, or 100k–1M tokens)`；二進位內的開關判定逐字是
    `if(DISABLE_COMPACT)return!1; if(env.DISABLE_AUTO_COMPACT)return!1;
    return config("autoCompactEnabled", true)` ⇒ **預設開啟**。

🔴 因此本檔的角色被明確收斂（別讓一個東西假裝能做兩件事）
--------------------------------------------------------
「不要爆」這件事**主要由 harness 的 autocompact 做**，本檔做不到——hook 不能執行
`/compact`，模型也不能自己打 slash 指令。本檔是那條線的**第二道**：
  ① 把「現在幾 %」變成看得見的數字（harness 的 autocompact 不告訴你水位）；
  ② 在 ≥90% 時**真的擋下展開型工具**（見下方〈PreToolUse 阻斷模式〉）——因為
     autocompact 觸發時會丟掉舊訊息，而「丟掉什麼」不由使用者決定；在那之前把
     戰場收斂掉，才是掌舵者要的「不要爆」。
  ③ 產出「可重啟點任務書」骨架，供 token 用完後 `claude -r` 續跑。
harness 那一半的姿態是**可現查的**：`python tools/session_resume_planner.py
--check-autocompact`（autocompact 被關掉時 rc=1）。

🔴 與 SDD `context_ledger` 的分工邊界（**先查過再寫，本檔不是重複造輪子**）
------------------------------------------------------------------------
repo 內確實已有一套帶 90% 門檻的 context 機制，而且**已經橋接在根註冊面上**：
`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/context_ledger_pre.py`（各版目錄各一份），
經根 `.claude/settings.json` 的 `sdd_hook_router.py` 以 `context_ledger_pre`／
`context_ledger_post` 掛在 PreToolUse／PostToolUse。實查其常數：`WARN_RATIO = 0.85`／
`AUTO_COMPACT_RATIO = 0.90`／`CRIT_RATIO = 0.95`（95% 發 `permissionDecision=deny`），
分母 `MAX_CONTEXT` 來自 `SDD_MAX_CONTEXT`、預設 200000。**它不該被廢、也不該被改**
（30 個版目錄、Copy-on-Evolve 凍結、FSM 有依賴）。

本檔與它**量的不是同一個東西**，三點皆逐項實查過：
  ① **估算 vs 實測**：ledger 的分子是 `_estimate_tokens(tool, tool_input)`，
     委派 `conversation_ledger.estimate_tool_tokens`，回退 `len(text) // 4`。
     它的輸入**只有 tool_input**——看不到工具**輸出**、subagent 回傳、對話本身、
     system prompt，而真正把 context 撐爆的正是那些。本檔的分子是逐字稿裡
     API 自己回報的 `message.usage`，是實測值。
  ② **生效條件不相交**：router 以 `SDD_ACTIVE_VERSION` 為守衛，未設時
     PreToolUse／PostToolUse **完全靜默放行**（SessionStart 印一行 dormant 提示）。
     純 AutoClaude／monorepo 根 session（＝本檔要守的那一種）ledger 一行都不跑。
  ③ **分母不同**：ledger 的分母是 SDD 專案的 Stage 預算，不是 Claude Code 的
     context window。兩者同為 200000 是巧合（一個是預設值、一個是保守下界）。

🔴 這個分工論證的**洞**，照實寫（不粉飾）
------------------------------------------
`SDD_ACTIVE_VERSION` 有設時兩者同時活著，而**兩邊都有一條 90% 線**。它們的分子分母
都不同，所以同一時刻的兩個百分比會**不一樣**——「同一份 repo 對同一個數字兩種說法」
正是本 repo 反覆判過的缺陷形態。本檔採取的處置是**標示而非收編**：
  · 每一則訊息都印出 `MEASURE_LABEL`，讓讀者一眼分得出這是哪一把尺量的；
  · 不去讀、也不去寫 ledger 的檔案（耦合會讓凍結版被拖下水）；
  · 不因 ledger 存在而讓路——它結構上看不到讓 context 爆掉的那部分。
**未解的那一半**：兩者同時觸發時使用者會連拿兩則語氣相近的告警。本檔不試圖去重
（去重需要跨 30 個凍結版的協議），僅以標籤讓它們可分辨。這一段是已知且已接受的
限制，不是漏看。

而「純文件約束對當下的模型零攔阻力」在本 repo 已被實證：`block_bash_on_windows.py`
那條規則寫進 CLAUDE.md 之後，同一個回合內仍再犯一次；換成 PreToolUse hook 之後
一次嘗試、一次攔下。水位這件事同型且更嚴重——CLAUDE.md 由 session **開場**載入，
而「現在幾 % 了」是每回合都在變的量，靠模型主動想起來去算它，正是決策負荷第一個
擠掉的東西。姊妹檔 `lint_powershell_command.py` 的立案量測寫得更直白：**有觀測者
的規則違規 1 次且被當場擋下，沒有觀測者的規則違規率 20~35%**。context 水位在本檔
出現之前是「沒有觀測者」那一類。

量測面（本輪實測確認，不是推測）
--------------------------------
Claude Code 的 hook payload 帶 `transcript_path`，指向本 session 的 jsonl。該檔每筆
`type == "assistant"` 的記錄在 `message.usage` 下有四個計數欄。**當前 context 佔用
＝ `input_tokens` ＋ `cache_creation_input_tokens` ＋ `cache_read_input_tokens`**
（`output_tokens` 不算：它是這一則回覆吐出來的量，下一回合才會以 input 的形式回到
context 裡，重複計會高估）。

🔴 context window 判定（R79 重寫——R78 版在本機模型上結構性保證在真 90% 靜默）
--------------------------------------------------------------------------------
R78 版只有兩階（環境變數 → `peak > 200K` 推論 → 保守下界 200K）。它在**掌舵者自己
這台機器**上的實測後果，是這支守衛存在的理由被完全抵銷掉：本機 user 層 settings
的 `model` 欄是 `opus[1m]`（1,000,000），而守衛拿 200,000 當分母 ⇒ 真實 15%／18% 各
誤喊一次 75%／90%，把兩個閂鎖同時燒掉；等 peak 越過 200K、window 翻成 1M 之後，
**到 99.9% 都不會再出聲**。誤報那一半 `settings.json` 承認過，「誤報會把真報一起吃掉」
那一半沒有。兩件事各自要修：分母要對（本段）、閂鎖要能重新武裝（見〈行為契約〉）。

方向仍是不對稱的，這一點沒變：
  · 猜小（實際 1M、當成 200K）⇒ 提早喊。成本＝一次多餘的 `/compact`。
  · 猜大（實際 200K、當成 1M）⇒ 到 90% 才喊時真實水位已是 450%，**根本喊不到**。
判定順序（先可證、後推斷；**每一階的來源字串都會原樣印進使用者看到的訊息**，
讓讀者知道分母是被指定的還是被推斷的——把推斷寫成已知是本 repo 的既有缺陷形態）：
  ① `AUTOSDD_CONTEXT_WINDOW`：本檔自己的旗標，最高優先＝**指定值**。
  ② `CLAUDE_CODE_AUTO_COMPACT_WINDOW`（環境變數）／`autoCompactWindow`（settings
     鏈：`.claude/settings.local.json` → `.claude/settings.json` → `~/.claude/
     settings.json`）＝**harness 自己的 window 旋鈕**。有設就用它——那正是 CC 用來
     決定何時 autocompact 的那個數，本檔的分母與它一致才不會出現「同一份 repo 對
     同一個數字兩種說法」。二進位內的 schema 逐字：`autoCompactWindow: number().
     int().min(1e5).max(1e6)`，且大於模型上限時由 CC 自己 capped，方向安全。
  ③ settings 鏈的 `model` 欄帶 `1m` 標記（本機實測 `opus[1m]`）⇒ 1,000,000。
     🔴 這一階刻意帶**交叉否決**：逐字稿裡實際跑過的 `message.model` 若與該 hint
     不同族（例：設定寫 opus、實際 `--model sonnet`），這一階**放棄發言**往下一階
     走。少了這道否決，一次 `--model` 覆寫就會讓分母偏大＝往危險方向錯。
  ④ 本 session 歷來 `used` 曾超過 200,000 ⇒ window **必然**大於 200K（可證的下界）；
     但「所以它是 1,000,000」不是證出來的，是在已知變體裡取下一檔，故標為推斷。
  ⑤ 其餘一律 200,000（保守下界）。這個方向只會早喊，安全。
🔴 **⑤ 這一階不得用來硬擋**（見〈PreToolUse 阻斷模式〉）：它是「我不知道」的委婉說法，
拿一個猜出來的分母去硬鎖工具，就是把本輪要修的那個缺陷換個方向再犯一次。

行為契約（PostToolUse＝觀測模式）
--------------------------------
· payload 讀不出來（壞 JSON／空 stdin）→ stderr 一行 ＋ **exit 1**（出聲但不阻斷）。
  🔴 為何不是靜默 exit 0：`tools/tests/test_check_hooks_liveness.py` 的
  `degraded_payload_verdict` 判過——讀不懂輸入時放行，等於讓「送壞 payload」成為
  讓守衛整支消失的免費手段，而且失效時沒有人看得見。同一支判準也說「rc==1＝出聲
  但不阻斷，爆炸半徑為零，合法」，所以這裡取 1 而不是 2。
· 沒有 `transcript_path`／檔案不存在／掃不到任何 usage → exit 0 靜默。這與上一條
  是**不同**的事：那是「輸入壞掉」，這是「量測暫時不可得」（session 剛開場一定會
  走到這裡）。把兩者混同就會變成每次呼叫都出聲的守衛，然後整支被關掉。
· `< 75%` → exit 0 且**完全靜默**（每次工具呼叫都出聲的守衛會被關掉）。
· `>= 75%` → stderr 一行建議 `/compact`，exit 0。
· `>= 90%` → stderr 強制指引（含 %、used/window 實數、下一步）＋ 呼叫
  `tools/session_resume_planner.py` 寫出「可重啟點任務書」骨架 ＋ **exit 2**。
  PostToolUse 的 exit 2 會把 stderr 回饋給模型，這正是要的效果；它**不**阻斷已經
  完成的那次工具呼叫（與 PreToolUse 的 exit 2 語意不同，別混淆）。
· **同一門檻＋同一 window 只喊一次**（state 檔在系統暫存，檔名帶 session id）。
  🔴 閂鎖鍵含 window 是 R79 修的那半個缺陷：R78 版只以 tier 為鍵，於是「用 200K
  當分母誤喊一次 90%」之後，等分母修正成 1M、真的到 90% 時**閂鎖還鎖著** ⇒ 該喊
  的那一次被前面那次誤報吃掉。分母一變就重新武裝，對 200K session 零行為改變。
  代價仍明說：模型若無視同一組（門檻, window）的那一喊，本檔不會再喊第二次。

🔴 PreToolUse 阻斷模式（R79 新增——把「不要爆」從散文變成真的擋得下來的東西）
----------------------------------------------------------------------------
R78 版的鏈條是「印一段話 → 模型自己記得去 compact」，而「純文件約束對當下的模型零
攔阻力」在本 repo 已被實證兩次（`block_bash_on_windows.py` 的立案就是這樣來的）。
故同一支腳本另有一個由 payload 的 `hook_event_name` 分派的模式：

  · 只在 `>= 90%` 且 **window 不是保守下界猜測**時擋（`may_block()`）。分母是猜的
    就只出聲不擋——否則今天這個缺陷（1M session 被當成 200K）會直接變成「真實 18%
    就把工具鎖死」，比原缺陷更糟。
  · 只擋**展開型**工具（`BLOCKING_TOOLS`；R80 起含本 harness 真正在用的 `Agent`／
    `Workflow`，見該常數旁的 WHY），註冊面的 matcher 與它逐名對齊。
    Read／Edit／PowerShell 一律放行——根 CLAUDE.md 那句是
    「此後只做收斂，不做展開」，而收斂本身需要讀檔、寫任務書、跑 git。**擋到讓人
    無法收斂的守衛會被整個關掉**，那是本 repo 反覆判過的形態。
  · **不進閂鎖**：擋一次就放行的東西不是阻斷。它會一直擋到水位掉下來為止，而
    `/compact` 之後 used 會真的掉 ⇒ 自動解除，不需要任何人來關掉它。
  · 人為逃生口：環境變數 `AUTOSDD_CONTEXT_GUARD_OFF=1` 一律放行（供人在守衛誤判時
    自救；模型改不到 hook 行程的環境）。這是對 P0 的第二道保險，不是給模型的後門。
· **任何非預期例外 → exit 0（fail-open）**。`.claude/settings.json` 的 description
  記載過 P0：hook 誤觸會把所有工具硬鎖死。守衛自身絕不可成為故障源。

零外部相依（與兩支姊妹 hook 同一組理由，非偷懶）
------------------------------------------------
hook 由 `.claude/settings.json` 的 shim 以 `runpy.run_path(...)` 起，而 `run_path`
**不會**把腳本所在目錄加進 `sys.path`；`tools/` 也不在路徑上。⇒ 本檔只用 stdlib，
UTF-8 串流手術就地重做一次。反向依賴是允許的：`tools/session_resume_planner.py`
**import 本檔**取用下面這幾支純函式，讓「怎麼算水位」只有一個家（本 repo 對
「同一份知識住兩個家」有反覆的判例，其中一次就長在專門防它的那一節自己身上）。

回歸鎖：`tools/tests/test_context_budget_guard.py`（合成 jsonl 注入，逐條驗紅）。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zoneinfo
from datetime import datetime, timedelta
from pathlib import Path

# 自己的 stdout/stderr 強制 UTF-8。缺這段時：locale 表達不了 CJK（en-US Windows
# ＝cp1252）→ 整段指引變 `\uXXXX` 逃脫字面；locale 表達得了但非 UTF-8（zh-TW
# ＝cp950）→ 讀者端亂碼。兩種都讓「提醒有了、指引沒了」，而本檔存在的唯一理由
# 就是純文件約束無攔阻力，指引不可讀等於把它砍掉一半。
# 例外一律吞掉且刻意比 stdlib 慣例更寬：**模組層**崩潰發生在 main() 的 try 之外、
# 繞得過那道保險，而 fail-open 在這裡是 P0。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001 — 見上
        pass

#: 佔用當前 context 的三個 usage 欄。`output_tokens` 刻意不在內，理由見模組 docstring。
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")

#: 硬指定 context window 的環境變數（最高優先；唯一不含猜測的來源）。
WINDOW_ENV = "AUTOSDD_CONTEXT_WINDOW"

#: Claude Code 自己的 window 旋鈕（環境變數版）。二進位內與 `autoCompactWindow`
#: 設定鍵同一條判定鏈；有設就代表使用者已經替 harness 釘死了那個數字。
CC_WINDOW_ENV = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
#: 同上的 settings 鍵。schema 逐字：`number().int().min(1e5).max(1e6)`。
CC_WINDOW_KEY = "autoCompactWindow"
#: settings 的模型欄。本機實測值 `opus[1m]`。
CC_MODEL_KEY = "model"
#: 逐字稿裡不代表真實模型的佔位值（本機實測會出現，混進交叉否決會誤殺）。
SYNTHETIC_MODEL = "<synthetic>"

#: 人為逃生口：守衛誤判時讓人一鍵放行（模型改不到 hook 行程的環境）。
GUARD_OFF_ENV = "AUTOSDD_CONTEXT_GUARD_OFF"

#: 哨兵的獨立逃生口。刻意**不**沿用上面那一個：兩者關掉的是不同的東西（一個是
#: context 阻斷、一個是額度續航），共用一個開關會讓「我只是想暫時別被擋」順手把
#: 續航保護一起關掉，而那件事沒有人會注意到。
SENTINEL_OFF_ENV = "AUTOSDD_SENTINEL_OFF"

#: 🔴 R80：在**無 console 的父行程**下 spawn console 子行程時必帶的 creationflags。
#:
#: 立案（掌舵者當場回報「哨兵每 15 分鐘彈一個視窗」，R79 只治了排程 Action 那一層）：
#: hook 行程與 schtasks 的 `pythonw.exe` 都**沒有 console**，而 `python.exe`／
#: `powershell.exe`／`claude.exe` 全是 console 子系統應用 ⇒ Windows 必定替子行程新配置
#: 一個 console，那就是跳到使用者臉上的那個視窗。
#:
#: 🔴 **R80 訂正本段（我自己的第一版在這裡寫了一句過度一般化的假話，照實留下訂正）**。
#: 第一版逐字宣稱「`DETACHED_PROCESS` 會把 `CREATE_NO_WINDOW` 抵銷掉」，依據是一張**只用
#: venv 的 `python.exe` 當子行程**量出來的表。複驗者指出本 venv 由 **uv** 建立
#: （`pyvenv.cfg` 有 `uv = 0.8.22`），其 `python.exe` 是 **trampoline**（274,712 bytes，
#: 對照真直譯器 103,192 bytes）：它會 re-spawn 真的直譯器，而**不把 creationflags 傳下去**
#: ⇒ 那張表量到的是 trampoline 的行為，不是旗標語意。
#:
#: 重量後的完整矩陣（pythonw 當無 console 父行程；子行程自報 `GetConsoleWindow()`／
#: `IsWindowVisible`。`0`＝沒有 console＝不會有視窗）：
#:
#:   子行程載具            none    CNW   DET|CNW   DET    NEWGRP|CNW   NEWGRP
#:   base python.exe      可見     0       0        0         0        可見
#:   venv python.exe      可見     0     可見      可見        0        可見   ← trampoline
#:   base pythonw.exe       0      0       0        0         0          0
#:   venv pythonw.exe       0      0       0        0         0          0
#:
#: 三個結論，方向都與第一版不同：
#:  ① `DET|CNW` 在**真直譯器**上是好的，只有穿過 trampoline 時才翻面 ⇒ 那句「抵銷」是
#:     載具效應，不是旗標語意。**射程誠實劃界**：本重現依賴「venv 由 uv 建立」；走
#:     `python -m venv` 回退路徑的 venv 是否同樣翻面，**未驗**。不得寫成平台常數。
#:  ② `CNW` 與 `NEWGRP|CNW` 是**唯二在四種載具上全部為 0** 的組合 ⇒ 本常數取後者。
#:  ③ **pythonw 那兩列全 0，與旗標無關** ⇒ 載具本身就足以抑制視窗。
#: ⇒ 故本檔採**兩層各自獨立成立**（缺一層仍安全）：載具走 `quiet_python()`、旗標走本常數。
#: 六組的 stderr／rc 都完整回得來 ⇒ 抑制視窗不以可觀測性為代價。
#:
#: 為什麼用 `CREATE_NEW_PROCESS_GROUP` 而不是 `DETACHED_PROCESS`：舊寫法想要的是「子行程
#: 不受父行程生死牽連」。實測那件事**不需要** `DETACHED_PROCESS`——本常數的組合下，父行程
#: （pythonw）退場後 8 秒，子行程仍自己把痕跡檔寫了出來（父死 02:02:50、子寫檔 02:02:58）。
#: `CREATE_NEW_PROCESS_GROUP` 保留了真正有用的那一半（Ctrl-C／Ctrl-Break 不會沿著父行程的
#: 行程群組傳進來），而且它在 trampoline 上不像 `DETACHED_PROCESS` 那樣翻面。
#:
#: `getattr` 而不是直接取屬性：這三個常數在 POSIX 的 `subprocess` 上**不存在**（鐵律三
#: 「這在另一個平台是什麼值」）。取 0 ＝不加任何旗標，正是 POSIX 上正確的值。
NO_WINDOW = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
             | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def quiet_python() -> str:
    """回本檔 spawn 子行程該用的直譯器路徑——**兩層防線的第二層**。

    上表第三、四列：`pythonw.exe`（GUI 子系統）在**全部六種旗標組合下**都是 0，
    連 trampoline 那一列也是 ⇒ 換掉載具這件事本身就足以抑制視窗，與旗標無關。
    故本函式與 `NO_WINDOW` **各自獨立成立**：任一層被未來的人改掉，另一層仍撐得住。

    🔴 為什麼是 `with_name` 而不是靠 PATH：實測本機**兩個 session 的 `python` 解析到不同
    東西**（互動 session → venv；schtasks 起的 headless → pyenv shim，後者沒有
    `pythonw.exe`）。取「與當前直譯器同目錄」才與 session 怎麼被啟動無關。
    找不到就退回 `sys.executable`——少一層防線，不是壞掉（旗標那層仍在）。
    """
    if os.name != "nt":
        return sys.executable  # POSIX 沒有 console 這回事，也沒有 pythonw（鐵律三）
    quiet = Path(sys.executable).with_name("pythonw.exe")
    return str(quiet) if quiet.is_file() else sys.executable

#: PreToolUse 模式會擋下的「展開型」工具。刻意不含 Read／Edit／PowerShell：
#: 收斂（讀檔、寫任務書、跑 git）必須還做得到，否則守衛會被整個關掉。
#:
#: 🔴 **R80：這一組名字在本 harness 上的命中面原本是 0**（掃描 S7-02 實測：8,106 次
#: `tool_use` 裡 `Task`／`WebFetch`／`WebSearch` 出現 **0 次**）。本 harness 派子代理叫
#: `Agent`、批次編排叫 `Workflow` ⇒ 阻斷臂蓋好了但一次都不會被觸發，而 R79 為它新增的
#: 那道鎖只把「matcher ↔ 本常數」釘成**相等**，保證的是「兩個都寫錯時也一致」——鑑別力
#: 的方向錯了（同 R77「鎖無鑑別力」那一桶）。修法是兩件事一起做：把真的會出現的名字補
#: 進來，並補一條**有效性**判準（本常數必須與最近若干支逐字稿的 `tool_use` 名稱集合有
#: 非空交集，見 `blocking_reach_problems`），讓「圈了一組永遠不出現的工具名」當場轉紅。
#:
#: `Task`／`WebFetch`／`WebSearch` **保留不刪**：它們是 Claude Code 上游的標準工具名，
#: 換一個 harness 就會回來，刪掉只是把同一個缺口移到另一台機器上。
BLOCKING_TOOLS = ("Task", "WebFetch", "WebSearch", "Agent", "Workflow")


def blocking_reach_problems(blocking: tuple[str, ...], observed: set[str]) -> list[str]:
    """阻斷臂的**有效性**判準（純函式）：圈到的名字必須真的會出現。回空 list ＝合格。

    `observed`＝實測逐字稿裡出現過的 `tool_use` 名稱集合。空集合時**不判**——那代表
    「這台機器上量不到」，不代表「命中面是 0」，而「量不到 ≠ 量到零」是本檔通篇的紀律。
    """
    if not observed or set(blocking) & observed:
        return []
    return [f"BLOCKING_TOOLS={blocking} 與實測出現過的工具名毫無交集"
            f"（實測看到 {len(observed)} 種）⇒ 阻斷臂命中面為 0，蓋好了但永遠不會觸發"]

#: 保守下界。實際是 1M 時只會早喊，方向安全。
CONSERVATIVE_WINDOW = 200_000
#: 已知的下一檔變體。觀測到 used > CONSERVATIVE_WINDOW 只證明「大於 200K」，
#: 取這個值是在已知變體裡選，不是證出來的——訊息必須標成推斷。
WIDE_WINDOW = 1_000_000

WARN_RATIO = 0.75
HARD_RATIO = 0.90

TIER_WARN = "warn"
TIER_HARD = "hard"

SOURCE_PINNED = f"指定值（環境變數 {WINDOW_ENV}）"
SOURCE_PINNED_CC_ENV = f"指定值（Claude Code 自己的 {CC_WINDOW_ENV}）"
SOURCE_PINNED_CC_SETTING = f"指定值（Claude Code settings 的 {CC_WINDOW_KEY}）"
SOURCE_MODEL_MARKER = (
    f"推斷值（settings 的 {CC_MODEL_KEY} 欄帶 1m 標記 ⇒ {WIDE_WINDOW:,}；"
    "已與逐字稿實際跑過的 model 交叉核對同族，非單方面採信設定）"
)
SOURCE_INFERRED_WIDE = (
    f"推斷值（本 session 曾觀測到 used > {CONSERVATIVE_WINDOW:,} ⇒ window 必然大於它；"
    f"取 {WIDE_WINDOW:,} 是在已知變體裡選下一檔，**不是**證出來的值）"
)
SOURCE_INFERRED_FLOOR = (
    f"推斷值・保守下界（未觀測到超過 {CONSERVATIVE_WINDOW:,} 的用量。"
    f"若實際是 {WIDE_WINDOW:,} 只會提早喊，方向安全；要精確就設 {WINDOW_ENV}）"
)

#: 每一則訊息都要帶的「這是哪一把尺」標籤。理由見模組 docstring 的〈洞〉那一段：
#: SDD `context_ledger` 也有一條 90% 線，兩邊的分子分母都不同，同一時刻會給出不同的
#: 百分比。不標示的話，讀者拿到兩個數字會以為其中一個壞了。
MEASURE_LABEL = "session 實測"

#: SDD 情境專屬的補充手法。**只在 `SDD_ACTIVE_VERSION` 有設時才印**——裸 `/compact`
#: 與「先產 Stage Summary 再壓縮」是兩種東西，後者綁 SDD 的 FSM 閉環，無條件推薦
#: 會讓純 AutoClaude session 收到一條它根本執行不了的指引。
SDD_STAGE_HINT = (
    "     （本 session 有設 SDD_ACTIVE_VERSION ⇒ 別裸 compact：先走 `stage-compaction`"
    " skill 產 Stage Summary 再壓縮，否則 FSM 閉環與已凍結文件的脈絡會一起掉。）\n"
)

#: state 檔前綴。放系統暫存而非 repo 內：逐字稿是機器本地資料，且 repo 內不得有
#: 可寫暫存目錄（`tools/tests/test_platform_neutral_paths.py` 有專屬判準）。
STATE_PREFIX = "autosdd_ctxguard_"
PLAN_PREFIX = "autosdd_resume_plan_"


def used_of(usage: object) -> int | None:
    """單筆 `message.usage` 的當前 context 佔用；`None`＝這筆不是可用的 usage。

    刻意只認 `int`（`bool` 也排除——它是 `int` 子類，混進來會讓 `True` 算成 1）：
    欄位缺一律當 0，但整筆一個欄位都沒有時回 `None`，讓「量到零」與「量不到」
    分得開。這兩者混同正是本 repo 反覆踩到的 fail-open 形狀。
    """
    if not isinstance(usage, dict):
        return None
    total = 0
    seen = False
    for field in USAGE_FIELDS:
        value = usage.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            total += value
            seen = True
    return total if seen else None


def scan_usage(path: Path) -> tuple[int | None, int]:
    """`scan_transcript` 的前兩格。既有呼叫端與回歸鎖用的仍是這個窄介面。"""
    last, peak, _model = scan_transcript(path)
    return last, peak


def scan_transcript(path: Path) -> tuple[int | None, int, str | None]:
    """逐行掃 jsonl，回 `(最後一筆 used, 歷來最大 used, 最後一個實際跑過的 model)`。

    model 一起掃出來是為了 window 判定的**交叉否決**（見 `window_from_model`），
    而且它必須與 usage 同一趟掃完——逐字稿會長到數十 MB，本檔每次工具呼叫都會跑。
    `<synthetic>` 這類佔位值不採計：它認不出家族，留著只會稀釋否決的鑑別力。

    刻意**逐行覆寫 last** 而不是整檔 `json.loads` 後排序：逐字稿是會長到數十 MB
    的 append-only 檔，而本檔每次工具呼叫都會跑一次。三段省法：
      ① 以 `"usage"` 子字串預篩，絕大多數行連 `json.loads` 都不進；
      ② 記憶體 O(1)（只留 last 與 max）；
      ③ 壞行直接跳過——逐字稿常有半截尾行（正在寫入時被讀到），一行壞掉不得
         讓整支守衛崩潰（同 `tools/probe/audit_session.py::iter_records` 的既有判斷）。
    歷來最大值是 window 下界推論的唯一輸入，所以必須整檔看過，不能只看尾巴。
    """
    last: int | None = None
    peak = 0
    model: str | None = None
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"usage"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if not isinstance(message, dict):
                    continue
                seen_model = message.get("model")
                if seen_model == SYNTHETIC_MODEL:
                    # 🔴 R79：合成記錄整筆退出**用量累計**，不只是退出 model 判定。
                    # harness 在額度耗盡時寫進逐字稿的那一筆長這樣：`type=assistant`、
                    # `model=<synthetic>`、`isApiErrorMessage=true`，而它的 `usage` 三欄
                    # **都在、且都是 0**（全庫實測 135 筆，無一例外）⇒ `used_of()` 依約回 0
                    # 而不是 None（「欄位在」就算量到），於是 `last` 被它覆寫成 0。
                    # 後果不是少算一點：水位在**額度耗盡的那一刻**由真值掉成 0.0%、tier 變
                    # None、守衛整支靜默——而 90% 那一支正是負責寫「可重啟點任務書」的那一
                    # 條路（`write_resume_plan`）。也就是說最需要任務書的那一刻，恰好是它
                    # 結構上不會被產生的那一刻。這是「量不到 ≠ 量到零」在**上游**又犯一次：
                    # 那筆記錄根本不是一次模型呼叫，它的 0 不是用量，是佔位。
                    continue
                if isinstance(seen_model, str):
                    model = seen_model
                value = used_of(message.get("usage"))
                if value is None:
                    continue
                last = value
                peak = max(peak, value)
    except OSError:
        return None, 0, None
    return last, peak, model


# ─────────────────────────── 額度事件（**與 context 水位是兩件事**，見下方 WHY）
# 🔴 這一段刻意**不接**任何阻斷行為，也不共用上面那條 75/90 的線。
# context 水位＝單次請求的輸入長度（分母是 window）；額度＝計費週期內的用量上限
# （分母是方案，harness 不告訴你）。兩者混為一談是本題最常見的錯誤，而它今天就會出錯：
# 額度耗盡當下本 session 的水位只有 ~20%，`block_verdict` 的四道放行條件會全數放行。
# 本段只提供**純函式的判讀**，由 `tools/session_resume_planner.py` 這個 CLI 消費者去決策。
# 住在這裡而不是住在 planner，是因為「怎麼掃逐字稿」的實作已經在本檔（`scan_transcript`），
# 而 planner 已經 import 本檔；反過來寫會讓逐字稿掃描這份知識有兩個家。

#: 可等待——session 額度，錯誤訊息自帶 reset 時刻。
LIMIT_SESSION = "quota_session"
#: 🔴 **不可等待**——月度支出上限，等到天荒地老都不會自己回來，只有人去提額才行。
#: 全庫實測：`session limit` 151 筆／`monthly spend limit` 71 筆（＝32%）。兩者的字面
#: 前綴都是 `You've hit your `，只認前綴的分類器會把那 71 筆判成可等待，然後排一支
#: 永遠不會成功的工作、每次觸發燒一次探測額度、而真正該做的事（叫人提額）一直沒發生。
LIMIT_SPEND = "quota_spend"
#: 伺服器暫時性錯誤，秒級退避即可，不進續航流程。
LIMIT_TRANSIENT = "transient"
#: 認不出來。**一律當不可等待處理**（fail-closed）：寧可叫人，也不要排一支永遠不成的工作。
LIMIT_UNKNOWN = "unknown"

#: 判讀順序即優先序。spend 必須排在 session 前面——見 `LIMIT_SPEND` 的 WHY。
_LIMIT_MARKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (LIMIT_SPEND, ("monthly spend limit",)),
    (LIMIT_SESSION, ("session limit", "usage limit", "rate limit")),
    (LIMIT_TRANSIENT, ("overloaded", "internal server error", "stalled mid-stream",
                       "connection closed", "api error")),
)

#: `resets 9am` ／ `resets 12:20pm` 兩種格式都要吃。全庫實測到 7 個相異 reset 值
#: （`3:50am` `4am` `9am` `11pm` `12:20pm` `12:30pm` `6pm`），**沒有一個落在 5 小時的
#: 固定格點上** ⇒ reset 時刻是滾動視窗、錨在該區塊第一次用量，只能**觀測**不能算。
#: 這就是 `session_resume_planner.DEFAULT_AT_EXPR` 那個 `AddHours(5)` 是缺陷的證據。
_RESET_RE = re.compile(r"resets\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)

#: 訊息自報的 IANA 時區，例：`… resets 9am (Asia/Taipei)`。全庫語料實測**每一筆**
#: session limit 訊息都帶這個括號，所以「9am 是哪個時區的 9am」是**資料自己回答的**，
#: 不需要去問機器。
_ZONE_RE = re.compile(r"\(([A-Za-z]+(?:/[A-Za-z0-9_+-]+)+)\)")


def declared_zone(text: object):
    """訊息自報的時區物件；`None`＝沒寫、或這台機器沒有 tz 資料庫可以解析它。

    🔴 **R80 立案（act 在 Linux 容器抓到、Windows 本機結構上看不見的兩個紅）**：
    `sentinel_decide` 的兩支分支判定實測在 UTC 容器與 UTC+8 本機**翻面**
    （`arm_reset` vs `probe`）。根因是 `resets 9am` 這個牆上時刻**沒有被綁在任何時區
    上**：舊實作拿機器的本地時區去解它，於是同一份語料在不同機器上是不同的絕對時刻。
    訊息括號裡就寫著答案，只是沒有人去讀。

    🔴 誠實劃界（本函式會回 `None` 的第二種情況，不粉飾）：`zoneinfo` 需要 tz 資料庫。
    Linux／macOS 由系統提供；**Windows 沒有**，且本 repo 不得為此新增相依
    （`tzdata` 是 PyPI 套件）。本機實測 `ZoneInfo("Asia/Taipei")` →
    `ZoneInfoNotFoundError` ⇒ 這條路在 Windows 上回 `None`，呼叫端退回「`now` 的時區」。
    那個退路在實務上是對的（訊息本來就是 harness 在**同一台機器**上以本地時區算繪的），
    但它不是機器無關的——所以退路成立與否會被 `parse_reset_at` 的呼叫端看見，
    而不是藏起來。
    """
    match = _ZONE_RE.search(str(text or ""))
    if match is None:
        return None
    try:
        return zoneinfo.ZoneInfo(match.group(1))
    except Exception:  # noqa: BLE001 — 無 tz 資料庫／未知地名一律退回呼叫端的框架
        return None


def classify_limit(text: object) -> str:
    """把一則錯誤訊息分成四類之一。純函式，零 I/O。

    `LIMIT_UNKNOWN` 是 fail-closed 的那一側：認不出來時呼叫端**不得**排程等待。
    這與本檔其他地方「量不到就閉嘴」同一個方向——不確定時不要做有後果的事。
    """
    low = str(text or "").lower()
    for kind, marks in _LIMIT_MARKS:
        if any(mark in low for mark in marks):
            return kind
    return LIMIT_UNKNOWN


def parse_reset_at(text: object, now: datetime) -> datetime | None:
    """從 `resets <hh[:mm]><am|pm>` 解出**下一個尚未發生的**該時刻；`None`＝解不出來。

    🔴 「下一個尚未發生」不是文青措辭，是唯一正確的規則：那個字串**不帶日期也不帶年**。
    天真地解成「今天的 9am」在下午跑會得到一個**已經過去**的時刻 ⇒ 觸發時刻算成負值 ⇒
    立刻探測、立刻再撞、把剛回來的額度再吃光。實測值裡已經有 `11pm` 與 `3:50am`，
    跨午夜這條路徑真的會走到。

    `None` 時呼叫端**不准**退回「假設 5 小時」——那是猜的，猜出來的時刻拿去排程會得到
    一個「憑證存在、但憑證不回答那個問題」的假綠（排程成立了，只是醒在錯的時間）。

    🔴 **R80：回傳值一律帶 offset（aware），且時區框架有明確的優先序**——
    ① 訊息自報的時區（`declared_zone`，機器無關）；② `now` 自己的時區；
    ③ `now` 是 naive 時先補上機器本地時區。
    ③ 那一格是「讓時刻一律帶 offset」的最後一道：naive 的牆上時刻被 `isoformat()`
    持久化之後就再也分不出它是哪個框架的，讀回來相減會在 DST 跳點上整整差 3600 秒。
    """
    match = _RESET_RE.search(str(text or ""))
    if match is None:
        return None
    hour, minute, meridiem = int(match.group(1)), int(match.group(2) or 0), match.group(3)
    if not (1 <= hour <= 12) or not (0 <= minute <= 59):
        return None
    hour = hour % 12 + (12 if meridiem.lower() == "pm" else 0)
    if now.tzinfo is None:
        now = now.astimezone()
    now = now.astimezone(declared_zone(text) or now.tzinfo)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def latest_limit_event(path: Path) -> dict | None:
    """逐字稿裡**最後一筆**額度／錯誤事件；`None`＝這支逐字稿沒有。

    指紋是 `type=assistant` ＋ `message.model == "<synthetic>"`（全庫 135 筆皆然）。
    刻意只認這個形狀而不是「訊息裡有 limit 字樣」：同一句話會被 `queue-operation`／
    `user`／`attachment` 等記錄各複述一次（實測同一次撞線在 4 種記錄型別各留一份），
    只有 assistant 合成記錄那一筆是 harness 自己寫的權威版本，其餘是回音。
    """
    found: dict | None = None
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if SYNTHETIC_MODEL not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if not isinstance(message, dict) or message.get("model") != SYNTHETIC_MODEL:
                    continue
                content = message.get("content")
                text = ""
                if isinstance(content, list):
                    text = " ".join(str(part.get("text") or "") for part in content
                                    if isinstance(part, dict))
                elif isinstance(content, str):
                    text = content
                found = {"text": text.strip(),
                         "timestamp": str(record.get("timestamp") or ""),
                         "kind": classify_limit(text)}
    except OSError:
        return None
    return found


# ───────────────── R80 P0：哨兵整晚失明的真正成因，與「已處理」的可證判準
# 事故（掌舵者實證）：2026-08-08 02:00~06:50 真的撞線、兩個修復 agent 與 9 個 verify
# agent 全部死在 `You've hit your session limit · resets 6:50am`，而哨兵那三次巡邏
# （08:37／08:52／09:07）**每一次都判「無未處理撞線」**。
#
# 🔴 三個候選歸因，只有第三個經得起實查（前兩個是推測，當回合逐一證偽）：
#  ① 「主逐字稿裡沒有那個字串」——**證偽**。Grep 實證主逐字稿含 `resets 6:50am`，
#     而且其中 3 筆正是 `type=assistant` ＋ `model=<synthetic>` 的權威形狀。
#  ② 「偵測面沒有涵蓋 subagent」——**成立但不是主因**。同 session 下 263 支 subagent
#     逐字稿中有 109 支抓得到限額事件；擴面是對的，但擴了也救不了本次。
#  ③ **真正的主因：`handled_through` 的立案理由是一句假話。** `_arm_sentinel` 把武裝
#     當下的最後一筆事件記為「已處理」，理由逐字是「我們此刻跑得動這支指令，就證明
#     額度是通的」。**那個推論不成立**——武裝是一個**純本機 subprocess，零 API 呼叫**，
#     額度早就見底時它照樣跑得動、照樣把撞線標成已處理。實證：狀態塊
#     `handled_through = 2026-08-07T18:38:56.348Z`，而那次撞線的事件是
#     `18:36:53.465Z`／`18:36:58.074Z` ⇒ **撞線發生兩分鐘後就被標記成「已解決」**，
#     此後每一次巡邏都合法地判 patrol。機制全程「正常運作」，只是守著一個假前提。
#
# 🔴 正解：把「已處理」從**推論**換成**可證的證據**——額度是帳號層級的資源，所以
# 「額度在某時刻之後是通的」的唯一硬證據，就是那之後**真的有一則成功的 API 回應**
# （`type=assistant` ＋ 真 model ＋ 有 `message.usage`）。這件事寫在逐字稿裡，讀檔
# 即可、**成本為零**，與哨兵「巡邏不花 token」的前提相容。
#
# 誤判率是**量出來的，不是挑的**（掃描面擴大必然放大假陽性，故先量再定判準）：
#   判準 B（擴面、只看每支檔最後一筆、無復原證據）  → 假陽性 14.8%（224/1513 支檔）
#   判準 C（擴面＋**同檔**復原證據）                 → 假陽性 **81.3%**（209/257）
#     ⇒ **被自己的量測否決**，而且成因是結構性的：被額度打死的 subagent 在它自己的
#       檔裡永遠不會再有下一則成功回應（它死了）⇒ 同檔證據對 subagent 恆為 False。
#   判準 D（擴面＋**全域**復原證據）                 → 假陽性 **0.0%**（0/257）✅
# 鑑別力反證（同一支量測腳本，把觀測時點倒推到停機進行中的 18:40:00Z）：判準 D 當時
# 會抓到 **4 筆** `quota_session`／`resets 6:50am` ⇒ 它不是靠「全部判已處理」拿到 0%。
def session_transcripts(transcript: Path, max_age_seconds: float = 86400.0,
                        now: float | None = None) -> list[Path]:
    """本 session 的主逐字稿 ＋ 它底下的 subagent 逐字稿（近期修改過的）。

    佈局是**觀察到的**（非官方契約，故 fail-soft）：`<sid>.jsonl` 旁有一個同名目錄
    `<sid>/`，subagent 落在 `<sid>/subagents/*.jsonl` 與
    `<sid>/subagents/workflows/<wf>/*.jsonl`。這裡用 `rglob` 收整棵，不寫死那兩層——
    多一層 workflow 目錄就漏掉一批，正是本次失明的形態之一。

    `max_age_seconds` 是**成本閘**不是判準：一筆「比全域最後成功回應還新」的事件不可能
    出現在很久沒被寫過的檔裡，而哨兵每 15 分鐘跑一次、母體已有 1,500+ 支檔。預設 24h
    遠大於一個額度視窗（實測最長 3.6h），所以它不會把真的未處理事件濾掉。
    """
    now = now if now is not None else time.time()
    found = [transcript] if transcript.is_file() else []
    folder = transcript.with_suffix("")
    if folder.is_dir():
        for path in folder.rglob("*.jsonl"):
            try:
                if now - path.stat().st_mtime <= max_age_seconds:
                    found.append(path)
            except OSError:
                continue
    return found


def _assistant_records(path: Path):
    """該檔裡的 assistant 記錄 `(timestamp, message)`。壞行跳過（逐字稿常有半截尾行）。"""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"assistant"' not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict) or record.get("type") != "assistant":
                    continue
                message = record.get("message")
                if isinstance(message, dict):
                    yield str(record.get("timestamp") or ""), message
    except OSError:
        return


def latest_success_at(paths: list[Path]) -> str:
    """這批逐字稿裡**最後一次成功 API 回應**的 ISO 時間戳（沒有就回空字串）。

    「成功」＝ `type=assistant` ＋ **真的 model**（不是 `<synthetic>`）＋ 有 `message.usage`。
    `usage` 是關鍵：那是伺服器真的計費回來的證據，harness 自己合成的錯誤訊息沒有它。

    這一個字串就是「額度在何時之前確定是通的」的硬證據，取代了原本那句**假的**推論
    （「我跑得動武裝指令 ⇒ 額度是通的」——武裝零 API 呼叫，證明不了任何事）。
    """
    best = ""
    for path in paths:
        for stamp, message in _assistant_records(path):
            if (stamp > best and message.get("model") != SYNTHETIC_MODEL
                    and message.get("model") and isinstance(message.get("usage"), dict)):
                best = stamp
    return best


def unhandled_limit_event(transcript: Path, max_age_seconds: float = 86400.0,
                          now: float | None = None) -> dict | None:
    """**還沒被解決的**限額事件裡最早的那一筆；`None`＝沒有（正常情況）。

    判準 D：事件的時間戳 > 全域最後一次成功回應 ⇒ 那之後 API 再也沒通過 ⇒ 未處理。
    取**最早**一筆而不是最後一筆，是因為要拿它的 reset 時刻去排程——同一次停機裡
    每個 subagent 都會留一筆，最早那筆才是真正的撞線時刻（其餘離 reset 更近）。

    🔴 為何不沿用 `latest_limit_event`：那支只看**最後一筆**，而本次事故裡主逐字稿的
    最後一筆是 `quota_spend`（月度上限），把更早、仍未解決的 `quota_session` 整個蓋掉。

    🔴 **R80 補洞（P0 修復自己引入的反向缺陷）**：第一版把**任何**沒有後續成功回應的
    `<synthetic>` 記錄都登記成候選，而 `<synthetic>` 是 harness 對**所有**合成訊息的
    共同標記——`API Error`、`[Request interrupted by user]` 都長這樣。於是一個以中斷
    或一次 API 錯誤收尾的 session（那是常態，不是例外）會被判成「未處理的撞線」，
    走到 `sentinel_decide` 解不出 reset ⇒ `escalate` ⇒ **哨兵把自己刪掉**。
    舊病是「該醒不醒」，新病是「不該死卻自我刪除」，兩者同樣靜默：痕跡只多一行
    `sentinel_escalate`，而 `Get-ScheduledTask` 查不到那支工作，與「正常下班」外觀相同。
    註解裡那個 0.0% 假陽性是**單一時點對 257 支檔的橫斷面**量測，量不到「session 以
    一則 API 錯誤／中斷收尾」這個**縱向**情境 ⇒ 它背書不了這條路徑。
    修法是把 kind 篩選提前到登記候選那一步：只有真的額度類（`LIMIT_SESSION`／
    `LIMIT_SPEND`）才算撞線，`transient`／`unknown` 一律略過。**這不是把 fail-closed
    翻成 fail-open**——被略過的那些本來就不是額度事件，對它們「什麼都不做」才是正解。
    """
    paths = session_transcripts(transcript, max_age_seconds, now)
    if not paths:
        return None
    recovered_at = latest_success_at(paths)
    best: dict | None = None
    for path in paths:
        for stamp, message in _assistant_records(path):
            if message.get("model") != SYNTHETIC_MODEL or not stamp > recovered_at:
                continue
            content = message.get("content")
            text = (content if isinstance(content, str) else
                    " ".join(str(part.get("text") or "") for part in content or []
                             if isinstance(part, dict))).strip()
            kind = classify_limit(text)
            if kind not in (LIMIT_SESSION, LIMIT_SPEND):
                continue
            if best is None or stamp < best["timestamp"]:
                best = {"text": text, "timestamp": stamp, "kind": kind,
                        "source": path.name, "recovered_at": recovered_at}
    return best


def newest_activity_at(paths: list[Path]) -> float:
    """這批逐字稿裡最新的 mtime（給存活判準用）；空清單回 0.0。

    🔴 為何不只看主逐字稿：扇出模式下主逐字稿可能好一陣子沒被寫，而 subagent 正在狂跑
    ⇒ 只看主檔會把一個很忙的 session 誤判成閒置，而閒置到門檻就會**自我解除**。
    """
    stamps = []
    for path in paths:
        try:
            stamps.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(stamps) if stamps else 0.0


def _positive_int(raw: object) -> int:
    """能讀成正整數就回它，否則回 0。壞值一律 0——0 會讓 `tier_of` 永遠沉默，
    所以它**不得**被當成 window 採用，只能是「這個來源說不出話」的表示。"""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return 0
    return value if value > 0 else 0


def carries_wide_marker(model: object) -> bool:
    """model 字串是否帶 1M context 標記（`opus[1m]`／`…-1m`）。

    刻意只認這兩種寫法而不做模糊比對：`claude-opus-4-1` 這種尾碼帶 1 的模型名一旦
    被誤判成 1M，分母就會偏大＝往「到 90% 才喊時真實水位已 450%」的危險方向錯。
    """
    text = str(model or "").strip().lower()
    return "[1m]" in text or text.endswith("-1m")


def model_family(model: object) -> str:
    """取 model 字串裡的家族字（`opus[1m]` → `opus`；`claude-opus-5` → `opus`）。

    只用來做**交叉否決**（設定寫的與逐字稿實際跑的是不是同一族），不用來判 window。
    回空字串＝認不出來 ⇒ 呼叫端一律當「無法否決」處理（不敢否決就不否決）。
    """
    text = str(model or "").strip().lower()
    for family in ("opus", "sonnet", "haiku", "fable"):
        if family in text:
            return family
    return ""


def window_from_model(hint: object, observed: object = None) -> int | None:
    """設定層 model 欄推出的 window；`None`＝這一階說不出話（往下一階走）。

    交叉否決：`observed`（逐字稿裡實際跑過的 model）認得出家族、且與 `hint` 的家族
    不同 ⇒ 放棄。少了它，一次 `claude --model sonnet` 覆寫就會讓分母偏大五倍。
    `<synthetic>` 這類佔位值認不出家族，會落在「無法否決」那一側，不誤殺。
    """
    if not carries_wide_marker(hint):
        return None
    want, got = model_family(hint), model_family(observed)
    if want and got and want != got:
        return None
    return WIDE_WINDOW


def resolve_window(
    peak_used: int,
    env_raw: str | None = None,
    *,
    cc_window_raw: object = None,
    settings_window: object = None,
    model_hint: object = None,
    observed_model: object = None,
) -> tuple[int, str]:
    """`(window, 來源說明)`。純函式——紅綠由注入自證，不讀環境／不讀檔（呼叫端傳入）。

    順序即優先序（詳細理由見模組 docstring 的〈context window 判定〉）：
    本檔旗標 → harness 自己的旋鈕（環境變數／settings）→ model 標記（帶交叉否決）
    → 可證的下界推論 → 保守值。來源說明會原樣印進使用者看到的訊息，所以它**必須**
    分得出「指定」與「推斷」；把推斷寫成已知是本 repo 的既有缺陷形態，不是文風問題。

    前兩個參數維持位置引數：既有呼叫端（`tools/session_resume_planner.py` 與回歸鎖）
    不必改就仍是對的，新增的證據來源一律 keyword-only。
    """
    for raw, source in (
        (env_raw, SOURCE_PINNED),
        (cc_window_raw, SOURCE_PINNED_CC_ENV),
        (settings_window, SOURCE_PINNED_CC_SETTING),
    ):
        if raw is None:
            continue
        pinned = _positive_int(raw)
        if pinned > 0:
            return pinned, source
    from_model = window_from_model(model_hint, observed_model)
    if from_model is not None:
        return from_model, SOURCE_MODEL_MARKER
    if peak_used > CONSERVATIVE_WINDOW:
        return WIDE_WINDOW, SOURCE_INFERRED_WIDE
    return CONSERVATIVE_WINDOW, SOURCE_INFERRED_FLOOR


def may_block(source: str) -> bool:
    """這個 window 來源夠不夠格用來**硬擋**工具。

    只有保守下界（＝「我不知道，先給個安全的小數字」）不夠格：拿猜出來的分母去鎖
    工具，正是本輪要修的那個缺陷換個方向再犯一次（1M session 會在真實 18% 被鎖死）。
    `SOURCE_INFERRED_WIDE` 夠格——它猜大的方向只會讓阻斷**晚**發生，不會誤擋。
    """
    return source != SOURCE_INFERRED_FLOOR


def tier_of(used: int, window: int) -> str | None:
    """`None`／`TIER_WARN`／`TIER_HARD`。window 非正數一律 `None`（不對零做除法）。"""
    if window <= 0:
        return None
    ratio = used / window
    if ratio >= HARD_RATIO:
        return TIER_HARD
    if ratio >= WARN_RATIO:
        return TIER_WARN
    return None


def session_id_of(transcript: Path) -> str:
    """逐字稿檔名（去副檔名）即 session id；非英數字元一律換成 `-`。

    清洗不是裝飾：這個字串會變成暫存檔名的一部分，未清洗的路徑分隔符會讓
    state 檔寫到別的目錄去（或在 Windows 上直接寫檔失敗）。
    """
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in transcript.stem)


def state_path(session_id: str, tmp_dir: str | None = None) -> Path:
    return Path(tmp_dir or tempfile.gettempdir()) / f"{STATE_PREFIX}{session_id}.json"


def latch_key(tier: str, window: int) -> str:
    """閂鎖鍵＝(門檻, 分母)。

    🔴 分母必須進鍵，這是 R79 修的半個缺陷：R78 版只以 tier 為鍵，於是「拿 200K 當
    分母在真實 18% 誤喊一次 90%」之後，等分母修正成 1,000,000、真的到 90% 時閂鎖
    **還鎖著** ⇒ 唯一該出聲的那一次被前面那次誤報吃掉。分母一變就重新武裝；分母
    沒變的 session（例：真的 200K）行為完全不變。
    """
    return f"{tier}@{window}"


def announced_latches(state: Path) -> set[str]:
    """已喊過的 (門檻, 分母) 集合。讀不出來一律回空集合（寧可多喊一次，也不要靜默失聲）。"""
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    tiers = data.get("tiers") if isinstance(data, dict) else None
    return {str(t) for t in tiers} if isinstance(tiers, list) else set()


def remember_latch(state: Path, key: str) -> None:
    """把 (門檻, 分母) 記進 state 檔。寫失敗不得升級為守衛失敗——最壞情況是下次再喊一次。"""
    tiers = sorted(announced_latches(state) | {key})
    try:
        state.write_text(
            json.dumps({"tiers": tiers}, ensure_ascii=False),
            encoding="utf-8",
            newline="\n",
        )
    except OSError:
        pass


def repo_root() -> Path:
    """monorepo 根。`CLAUDE_PROJECT_DIR` 由 Claude Code 注入，缺席時以本檔位置推。

    以檔案位置為主要依據（`.claude/hooks/<本檔>` ⇒ 上溯兩層）而不是 cwd：cwd 由
    註冊面的 shim 決定，那是別人的實作細節，被改掉時本檔不該跟著壞。
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        candidate = Path(env)
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def settings_chain(root: Path | None = None) -> list[Path]:
    """Claude Code settings 檔，**由高優先到低優先**。

    刻意不含 enterprise policy 層：那一層的路徑隨 OS 而異、且本檔讀它也沒有意義
    （它只會讓分母更小＝更早喊，而更早喊本來就是安全方向）。誠實劃界：`--settings`
    旗標與 `/model` 的 session 內覆寫本檔看不到，這也正是 `window_from_model` 要用
    逐字稿實跑 model 做交叉否決的原因。
    """
    base = root or repo_root()
    return [
        base / ".claude" / "settings.local.json",
        base / ".claude" / "settings.json",
        Path(os.path.expanduser("~")) / ".claude" / "settings.json",
    ]


def settings_value(key: str, paths: list[Path] | None = None) -> object:
    """settings 鏈裡第一個有這個鍵的值；沒有就 `None`。任何讀檔／解析失敗一律跳過。"""
    for path in paths if paths is not None else settings_chain():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get(key) is not None:
            return data[key]
    return None


def window_evidence(observed_model: str | None) -> dict:
    """把 `resolve_window` 需要的四個證據來源一次收齊（I/O 都在這裡，判定仍是純函式）。"""
    return {
        "env_raw": os.environ.get(WINDOW_ENV),
        "cc_window_raw": os.environ.get(CC_WINDOW_ENV),
        "settings_window": settings_value(CC_WINDOW_KEY),
        "model_hint": settings_value(CC_MODEL_KEY),
        "observed_model": observed_model,
    }


def write_resume_plan(transcript: Path) -> str:
    """呼叫 `tools/session_resume_planner.py` 產出任務書骨架；回傳路徑（失敗回空字串）。

    走 subprocess 而不是 import：本檔的零相依契約（見模組 docstring）不允許 import
    repo 內任何模組，而 `tools/` 根本不在 hook 行程的 `sys.path` 上。子行程的
    stdout/stderr 明確宣告 UTF-8（`encoding=`／`errors=`），避免 zh-TW cp950 下
    讀子行程輸出時炸 UnicodeDecodeError。任何失敗一律吞掉——任務書寫不出來時，
    使用者仍該拿到那段強制指引。
    """
    planner = repo_root() / "tools" / "session_resume_planner.py"
    if not planner.is_file():
        return ""
    out = Path(tempfile.gettempdir()) / f"{PLAN_PREFIX}{session_id_of(transcript)}.md"
    try:
        subprocess.run(
            [quiet_python(), str(planner), "--transcript", str(transcript),
             "--out", str(out)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            # 15s 遠大於實測（planner 對 1.18 MiB 逐字稿 < 1s），但**必須小於註冊面
            # 的 `timeout`**：CC 若先砍掉本 hook，那段強制指引就一個字都印不出來
            # ——為了寫任務書而弄丟指引，方向剛好相反。建議註冊 timeout 取 30。
            timeout=15,
            check=False,
            # 本 hook 行程沒有 console，而 planner 是 console 子系統的 python.exe
            # ⇒ 不帶這個旗標時每次越過 90% 都會彈一個視窗（見 NO_WINDOW 的實測表）。
            creationflags=NO_WINDOW,
        )
    except Exception:  # noqa: BLE001 — 診斷輔助不得反過來變成守衛的故障源
        return ""
    return str(out) if out.is_file() else ""


# ───────────────────────── SessionStart：預防性哨兵的**觸發層**（R79 補洞包）
# 🔴 為什麼非得長在這裡不可（不是「順手掛一下」）：
# `tools/session_resume_planner.py --arm-endurance` 是**手動**武裝的，而額度耗盡那一刻
# 是 16 秒內全部 subagent 瞬間掛掉——那個時間點沒有任何人會去跑一行指令。更根本的是
# **額度耗盡在 Claude Code 的 hook 體系裡沒有任何觸發點**：它是 API 層的失敗，不是工具
# 呼叫失敗 ⇒ PreToolUse／PostToolUse 都不會被叫到，本檔那兩個模式一次都不會醒來。
# ⇒ 唯一可行的形狀是**預防性武裝**：趁還能跑指令的時候先掛好，之後由 OS 排程器（不是
# 這個 session、不是這個模型）去輪詢。SessionStart 是「還能跑指令的最早時刻」。
# 這也是本 repo 已判過三次的同一個病的解藥：R77「PKG-GUARD 機制蓋好沒接電」——機制做完
# 了但沒有任何東西會自動去按它。純文件約束（「開工前記得武裝」）對當下的模型零攔阻力。
#
# 三個刻意的取捨：
#  ① **detached 子行程**，不同步等它跑完。註冊一支 schtasks 要外呼 powershell.exe，
#     實測數秒；同步做等於每次開 session 都先卡幾秒。取證不因此消失——`--arm-sentinel`
#     自己有 `NextRunTime` 憑證閘，成敗都寫進稽核 jsonl 與下面這支 boot log。
#  ② **逐字稿檔案不存在也照樣武裝**。SessionStart 那一刻檔案往往還沒被建立；planner
#     對這個入口特別放行（見該檔 `--arm-sentinel` 的 WHY），只把路徑記進狀態塊。
#  ③ **一切例外吞掉**。`.claude/settings.json` 的 description 記載過 P0：hook 誤觸會把
#     所有工具硬鎖死。武裝失敗最多是少一層保護，絕不可反過來變成故障源。
def arm_sentinel(payload: dict) -> None:
    """SessionStart：把預防性哨兵掛上去（背景、非阻塞、失敗一律靜默）。"""
    if os.name != "nt" or os.environ.get(SENTINEL_OFF_ENV):
        return  # schtasks 只在 Windows 成立（鐵律三）；人要關就關得掉
    raw = payload.get("transcript_path")
    planner = repo_root() / "tools" / "session_resume_planner.py"
    if not isinstance(raw, str) or not raw.strip() or not planner.is_file():
        return
    tmp = Path(tempfile.gettempdir())
    sid = session_id_of(Path(raw))
    with (tmp / f"autosdd_sentinel_boot_{sid}.log").open(
            "a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"\n=== arm {datetime.now().isoformat(timespec='seconds')} ===\n")
        handle.flush()
        subprocess.Popen(  # noqa: S603 — 參數全是本檔算出來的路徑，無 shell
            [quiet_python(), str(planner), "--transcript", raw,
             "--out", str(tmp / f"{PLAN_PREFIX}{sid}.md"), "--arm-sentinel"],
            stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            # 🔴 R80：舊寫法帶了 `DETACHED_PROCESS`，而它在**本 venv 的 trampoline 載具**
            # 上會讓視窗回來（矩陣見 NO_WINDOW 第二列：`DET` 與 `DET|CNW` 兩格皆「可見」）
            # ——上面取捨①宣稱的「不彈視窗」在寫下的當回合就不成立，且失效是靜默的
            # （旗標有設、視窗照彈）。**不要把這句讀成「DETACHED 會抵銷 CNW」**：那是本檔
            # 第一版的過度一般化，真直譯器那一列 `DET|CNW` 是 0，翻面的是載具不是旗標語意。
            # 取捨①要的「不同步等它跑完」由「不呼叫 wait()」提供，與旗標無關；子行程活過
            # 父行程退場這件事也已實測不需要 DETACHED_PROCESS（父死 8 秒後子仍寫出痕跡）。
            creationflags=NO_WINDOW)


def _headline(used: int, window: int, source: str) -> str:
    return (f"{used / window:.1%}"
            f"（{MEASURE_LABEL}：used {used:,} / window {window:,}〔{source}〕）")


def warn_message(used: int, window: int, source: str) -> str:
    return (
        f"⚠️  context 水位 {_headline(used, window, source)}——已越過 75%。\n"
        "   建議現在跑 `/compact`（根 CLAUDE.md〈Token 將耗盡時的無害暫停〉三段式水位："
        "~75% compact、~90% 停止開新戰場、撞上限才重啟）。此時仍可開新工作。\n"
        f"   要精確判定分母就設 {WINDOW_ENV}；本行的 window 來源已標在括號裡。\n"
        "   （同一門檻本 session 只喊這一次）\n"
    )


def hard_message(used: int, window: int, source: str, plan: str,
                 sdd_active: bool = False) -> str:
    plan_line = (
        f"  3. 「可重啟點」任務書骨架已寫到：{plan}\n"
        "     🔴 裡面帶 `TODO:` 的欄位本守衛**不會**替你填——它不知道你驗過什麼。\n"
        if plan else
        "  3. 任務書：`python tools/session_resume_planner.py`（本次自動產生失敗，請手動跑）\n"
    )
    return (
        f"🔴 context 水位 {_headline(used, window, source)}——已越過 90% 硬線。\n"
        "   此後**只做收斂，不做展開**（根 CLAUDE.md〈Token 將耗盡時的「無害暫停 →"
        " reset 後重啟」SOP〉）：\n"
        "  1. 立刻 `/compact`。\n"
        f"{SDD_STAGE_HINT if sdd_active else ''}"
        "  2. 把工作樹收到「可重啟點」四條件：① 已 commit 且閘門全綠，或"
        " `git stash create` ＋ `git tag <輪次>-wip-preserved`（絕不留半套 edit 就走）；"
        "② 任務書落在**磁碟**（對話會被 compact、session 會換）；③ 任務書含四項"
        "（已驗證什麼＋實測數字與 rc／還沒做什麼／下一步的確切指令／禁止事項）；"
        "④ 重啟後第一件事是**重驗**，不採信任務書裡任何「已通過」宣稱。\n"
        f"{plan_line}"
        "  4. 撞上限後重啟：`claude -r <sessionId>`（session id 見上面那份任務書）。\n"
        "     🔴 **不要**用 `CronCreate`——`CronList` 對它的標記是 `[session-only]`，"
        "session 關掉就沒了，不是離線排程。要離線排程只有 `schtasks` 一條路，且\n"
        "     宣稱「已排程」的**同一則回覆**必須附排程器自己回報的 `NextRunTime` 實測"
        "輸出（根 CLAUDE.md〈反「事後諸葛」取證規則〉）；貼不出來就只能說「我做不到」。\n"
        "  （同一門檻本 session 只喊這一次——這是刻意的：每次工具呼叫都 exit 2 的守衛"
        "會被整個關掉。回歸鎖 tools/tests/test_context_budget_guard.py）\n"
    )


def block_message(used: int, window: int, source: str, tool: str) -> str:
    """PreToolUse 阻斷訊息。必須逐字給出下一步，否則擋下來只是製造挫折。"""
    return (
        f"🔴 context 水位 {_headline(used, window, source)}——已越過 90% 硬線，"
        f"`{tool}` 這類**展開型**工具已被擋下。\n"
        "   根 CLAUDE.md〈Token 將耗盡時的「無害暫停 → reset 後重啟」SOP〉：此後"
        "**只做收斂，不做展開**。Read／Edit／PowerShell 仍然放行，收斂做得完。\n"
        "   下一步（照順序做）：\n"
        "  1. `/compact`（本 session 的 harness autocompact 姿態現查："
        "`python tools/session_resume_planner.py --check-autocompact`）。\n"
        "     compact 之後 used 會真的掉下來，本阻斷**自動解除**，不需要任何人去關它。\n"
        "  2. 把工作樹收到「可重啟點」：已 commit 且閘門全綠，或 `git stash create`"
        " ＋ `git tag <輪次>-wip-preserved`。絕不留半套 edit 就走。\n"
        "  3. 任務書：`python tools/session_resume_planner.py`（含重啟指令）。\n"
        f"   誤判時的逃生口（給人用，不是給模型用）：設 {GUARD_OFF_ENV}=1 一律放行；"
        f"分母不對就設 {WINDOW_ENV}=<真實 window>。本次分母來源已標在上面括號裡。\n"
    )


def read_payload() -> dict | None:
    """讀 stdin 的 hook payload；`None`＝退化（讀不出來）。

    走 **bytes 端**再以 UTF-8+replace 解碼：zh-TW Windows 的 pipe 預設 cp950，
    裸文字端 read 遇到含中文的 UTF-8 payload 會拋 UnicodeDecodeError。三支姊妹
    hook 都有這道防線，本檔照抄同一形態。
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
        payload = read_payload()
        if payload is None:
            # 退化 payload：出聲但不阻斷（rc=1）。靜默放行會讓「送壞 payload」成為
            # 讓守衛整支消失的免費手段，且失效時沒有人看得見（判準見模組 docstring）。
            sys.stderr.write(
                "⚠️  context 水位守衛讀不出 hook payload（壞 JSON 或空 stdin）"
                "——本次不做任何量測。守衛沒有靜默失效，但它這一次確實沒看到東西。\n"
            )
            return 1
        event = str(payload.get("hook_event_name") or "")
        if event == "SessionStart":
            # 這一支不量水位、不出聲、恆 exit 0：它只負責「把哨兵接上電」。
            arm_sentinel(payload)
            return 0
        blocking = event == "PreToolUse"
        raw_path = payload.get("transcript_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return 0  # 量測暫時不可得 ≠ 輸入壞掉，見模組 docstring 的行為契約
        transcript = Path(raw_path)
        if not transcript.is_file():
            return 0

        used, peak, model = scan_transcript(transcript)
        if used is None:
            return 0  # 掃不到任何 usage：量不到 ≠ 量到零，不做任何宣稱
        window, source = resolve_window(peak, **window_evidence(model))
        tier = tier_of(used, window)
        if tier is None:
            return 0

        if blocking:
            return block_verdict(payload, used, window, source, tier)

        state = state_path(session_id_of(transcript))
        key = latch_key(tier, window)
        if key in announced_latches(state):
            return 0
        remember_latch(state, key)

        if tier == TIER_WARN:
            sys.stderr.write(warn_message(used, window, source))
            return 0
        sys.stderr.write(hard_message(
            used, window, source, write_resume_plan(transcript),
            sdd_active=bool(os.environ.get("SDD_ACTIVE_VERSION")),
        ))
        return 2
    except Exception:  # noqa: BLE001 — fail-open 是刻意的，見模組 docstring 的 P0
        return 0


def block_verdict(payload: dict, used: int, window: int, source: str, tier: str) -> int:
    """PreToolUse 模式的判定。四道放行條件缺一，才會真的擋。

    刻意抽成獨立函式：阻斷是本檔唯一有爆炸半徑的行為，它的每一個放行條件都要能被
    逐條注入驗紅，而不是埋在 `main()` 的 try 裡跟量測邏輯混在一起。
    """
    if os.environ.get(GUARD_OFF_ENV):
        return 0  # 人為逃生口（對 P0 的第二道保險）
    if tier != TIER_HARD:
        return 0
    if not may_block(source):
        return 0  # 分母是猜的就不擋——猜錯會在真實 18% 把工具鎖死
    tool = str(payload.get("tool_name") or "")
    if tool not in BLOCKING_TOOLS:
        return 0  # 註冊面的 matcher 被改寬時的第二道限縮（同 block_bash_on_windows）
    sys.stderr.write(block_message(used, window, source, tool))
    return 2


if __name__ == "__main__":
    sys.exit(main())
