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
import subprocess
import sys
import tempfile
from datetime import datetime
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

# payload 讀取接上共用層 `tools/lib/platform_utils.py`（R81／SUB-S1-04 的交棒項）：
# 本檔此前自帶一份手抄本，與 SSOT 逐行等價但**沒有任何機械關係** ⇒ 只要有一邊被改，
# 阻斷級守衛就會安靜地與其他 hook 走不同的判定。`_STDIN_OWN_READER_ALLOWED` 當時把
# 本檔具名排除，理由逐字是「R81 包 A 正在改，本包不得動 ⇒ 交棒收尾接上共用層」。
#
# 🔴 與上方「零外部相依」**不衝突**：那條要的是 fail-open 而不是「不准 import」。
# 共用層不可達時（`run_path` 起、`tools/lib` 不在 sys.path）下面的 except 讓它退化成
# `read_payload() -> None`，正好走本檔既有的「讀不出來 → 出聲不阻斷、rc=1」分支；
# 模組層不會爆掉，也不留第二份 JSON 解析實作。形態與 `lint_powershell_command.py`
# 逐字相同（那支是本形態的首個消費者）。
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "lib"))
try:
    from platform_utils import read_payload  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 共用層不可達＝退化，不是崩潰（fail-open 是 P0）
    def read_payload() -> dict | None:  # type: ignore[misc]
        return None

# 額度快取的**檔案契約**（檔名＋schema）與**取數**唯一的家＝`tools/lib/quota_meter.py`。
# 形態與上一格逐字相同（同一條 sys.path、同一種 fail-open）：meter 不可達時本符號為
# `None`，額度軸整條退化成「量不到」＝不節流，而不是崩潰。
try:
    import quota_meter  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 見上
    quota_meter = None  # type: ignore[assignment]

# 跨行程原語（派發帳／TTL 名額／痕跡）唯一的家＝`tools/lib/quota_ledger.py`。同一條
# sys.path、同一種 fail-open：不可達時本符號為 `None`，扇出節流整條退化成「不記帳」。
try:
    import quota_ledger  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 見上
    quota_ledger = None  # type: ignore[assignment]

# 額度**撞線判讀**（`SYNTHETIC_MODEL`／`LIMIT_*`／`classify_limit`／`parse_reset_at`／
# `unhandled_limit_event` …）唯一的家＝`tools/lib/quota_limits.py`。它是 R81 收斂把本檔
# 從 1,730 行壓回棘輪之內的那一次減法：搬走的是一個完整主題（輸入是撞線訊息／逐字稿，
# 輸出是判讀結果），一行都不碰 context 水位與阻斷決策。**為什麼這一格沒有 try/except**
# （與上面兩格刻意不同）見該檔 docstring 最後一段：能力提供者可以降級，判讀原語不行——
# 給它 fallback stub 等於讓同一份字面有第二個家，而且會用錯的答案靜默通過。
# `tools/session_resume_planner.py` 以 `guard.<name>` 取用這些符號 ⇒ 這裡把它們 import
# 回本檔的命名空間，呼叫端與既有回歸鎖一個字都不必改。
from quota_limits import (  # noqa: E402
    LIMIT_SESSION, LIMIT_SPEND, LIMIT_TRANSIENT, LIMIT_UNKNOWN, SYNTHETIC_MODEL,
    classify_limit, declared_zone, latest_limit_event, latest_success_at,
    newest_activity_at, parse_reset_at, session_transcripts, unhandled_limit_event)

#: 🔴 上面那批裡有 10 個在本檔內**一次都不會被呼叫**——它們是純再匯出，消費者是
#: `tools/session_resume_planner.py`（`guard.classify_limit` 這種取法）。這一行讓
#: 「本檔沒有呼叫它」不等於「沒有人用」：刪掉任一個，planner 會在執行期 AttributeError，
#: 而那是排程起的無人看管路徑——最不容易被看見的那一條。順帶讓 lint 說得出話
#: （沒有它，`ruff` 的 F401 會建議把 planner 的相依整批刪掉）。
_REEXPORTED_FOR_PLANNER = (
    LIMIT_SESSION, LIMIT_SPEND, LIMIT_TRANSIENT, LIMIT_UNKNOWN, classify_limit,
    declared_zone, latest_limit_event, latest_success_at, newest_activity_at,
    session_transcripts)

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


# ═══════════════════ 額度水位（訴求 a／b）：**與 context 完全分開的第二把尺**
# 🔴 為什麼是另一條路徑，而不是 `block_verdict()` 裡多一個分支（SA-B1，本包實測複驗）：
# `main()` 在呼叫 `block_verdict()` 之前有**五道早退**，五道全部是 context 語意
# （`transcript_path` 缺／檔不存在／`used is None`／`tier_of(...) is None`），而
# `tier_of` 在 context < 75% 一律回 `None`。撞額度那一刻 context 水位只有 ~18~20%
# ⇒ 掛在那裡的 quota 分支**一次都不會被執行**，那就是本 repo 判過三次的「機制蓋好沒接電」。
# ⇒ 本節的入口 `quota_gate()` 由 `main()` 在**那五道早退之前**呼叫，且它不讀逐字稿、
#   不算 context、不問 `may_block()`。兩把尺共用早退條件就是讓一個東西假裝能做兩件事。
#
# 🔴 既有架構界線**維持不變且被加嚴**：`tools/tests/test_context_budget_guard.py::
# test_quota_is_not_wired_into_the_context_blocking_path` 禁止把逐字稿撞線判讀
# （`classify_limit`／`parse_reset_at`／`latest_limit_event`）接進 `block_verdict()`。
# 本節整段住在 `block_verdict` **之前**、且一個字都沒有動它 ⇒ 那條鎖的射程零改變。
# 本包同時替它補了反向那一半（quota 分支必須**真的**在早退之前求值），見該檔同名類別。
#
# ── 兩道的分工（掌舵者訴求 b 逐字）────────────────────────────────────────
#   80% ⇒ 少派 agent：扇出型工具受**滾動視窗派發預算**節制，超出即 `exit 2`（那次呼叫
#         不會發生）。這是機械的併發下降，不是印一行字給模型看。
#   95% ⇒ 停止並準備喚醒：扇出全擋（cap=0）＋ 一次性閂鎖（寫任務書 → 依 reset 距離分三支）。
QUOTA_THROTTLE_PCT = 80.0
QUOTA_HALT_PCT = 95.0

QUOTA_NORMAL = "normal"
QUOTA_THROTTLE = "throttle"
QUOTA_HALT = "halt"
#: 🔴 第四個狀態，刻意與 `normal` **分開**：「量不到」與「量到 0」混同正是本檔通篇在防的
#: fail-open 形狀。兩者在**行為**上都不節流（見下方 L4 的 WHY），但在**訊息與痕跡**上必須
#: 分得開，否則「網路壞了」與「額度很寬鬆」外觀完全相同。
QUOTA_UNMEASURABLE = "unmeasurable"

#: 節流帶的扇出預算：每個滾動視窗最多幾次派發。
#: 🔴 **這個數字是挑的，不是量出來的**——照實寫。它的**上界**才是量出來的：R80 撞線當下
#: 的扇出規模實測 42／55／1，cap 必須遠小於它們，2 落在極寬鬆的一側。
#: 機械物守的是**方向不是數值**：cap 必須隨 quota 單調不增，且 q≥95 時必須恰為 0。
THROTTLE_FANOUT_CAP = 2
#: 滾動視窗長度。同樣是挑的：它決定「節流帶裡每小時最多派幾個」（2/5min ≈ 24/hr）。
#: 取滾動視窗而不是併發計數，理由是結構性的，見 `live_dispatches` 上方那段。
FANOUT_WINDOW_SECONDS = 300
#: 快取新鮮度上限。🔴 **不是**由「1.2pp/min 線性外推」推導的——那個推導已被第三個量測點
#: 證偽（視窗翻頁時 utilization 會**驟降** 48pp，這個量非單調、在邊界不連續）。它就是挑的，
#: 重量入口＝`python tools/lib/quota_meter.py --watch <秒>`，不另開探針檔。
QUOTA_CACHE_TTL_SECONDS = 180
#: 同步刷新的逾時上界（R81 收斂新增，見 `refresh_quota_blocking`）。取 4 秒的依據是量出來的
#: ——端點 RTT 本包當回合三次實測 0.33／0.36／0.41 秒，4 秒約 10 倍餘裕；逾時的正確方向是
#: 「量不到」而不是「慢慢等」，因為這一格**在 hook 的關鍵路徑上**（那是本輪刻意的取捨）。
QUOTA_SYNC_TIMEOUT_SECONDS = 4
#: reset 多遠以內才值得「排程等它」。5 小時視窗最遠 5h、週視窗最遠 7 天，中間這個
#: 缺口大到不需要精確：取 6 小時。方向鎖守的是「七天後才 reset 的線不得被排程」。
RESET_ARM_HORIZON_SECONDS = 6 * 3600

#: 額度守衛的**第三個**逃生口。刻意不沿用 `GUARD_OFF_ENV`／`SENTINEL_OFF_ENV`：三者關掉的
#: 是三件不同的事（context 阻斷／續航哨兵／額度節流），共用一個開關會讓「我只是想暫時
#: 別被擋」順手把另外兩層一起關掉，而那件事沒有人會注意到（同 `SENTINEL_OFF_ENV` 的 WHY）。
QUOTA_OFF_ENV = "AUTOSDD_QUOTA_GUARD_OFF"
#: 節流帶的 cap 覆寫（一樣受方向鎖：halt 帶恆為 0，覆寫不到）。
QUOTA_CAP_ENV = "AUTOSDD_QUOTA_FANOUT_CAP"

#: 🔴 **本包量到的失明面，寫成政策而不是寫成藉口**（SD-B1）。本包當回合實測：
#:  · `Workflow` 的 tool_result **47/47** 是「launched in background」⇒ 那次工具呼叫在
#:    內部 agent 生出來**之前**就結束了；
#:  · `%TEMP%` 的 `autosdd_sentinel_boot_*.log` 19 支，**沒有一支**的 sid 長得像 subagent
#:    ⇒ SessionStart hook 對 workflow 內部 agent **一次都沒有觸發過**；
#:  · 但 subagent 逐字稿裡 `PreToolUse:` 命中 136 次（Bash 105／PowerShell 25／Read 6）
#:    ⇒ 那些 agent **自己的每一次工具呼叫**都會跑本 hook。
#: 合起來的結論：我們攔得到「派發」與「被派出去的人再往下派」，但攔不到「一個已經啟動的
#: workflow 在內部生出 42 個 agent」那一刻——**那一刻沒有任何 hook 會被叫到**。
#: ⇒ 既然一次 `Workflow` 啟動是一個**事後無法界住**的扇出，節流帶唯一誠實的處置就是
#: 不讓它啟動。這不是「擋不到所以放棄」，是把量到的失明面換成一條擋得住的政策。
UNBOUNDED_FANOUT_TOOLS = ("Workflow",)

#: 派發帳。🔴 **刻意不帶 session id**（SA-B5／SD-B1）：額度是 per-account 的單一池，而
#: 每個 subagent／每一次 headless 跑都有自己的 sid ⇒ per-sid 的帳等於 N 個載體各拿一份
#: cap，根本沒有界住帳號層級的燒用量。一個帳號、一份帳。
#: 🔴 R81 收斂：它現在是**一個目錄**（一次派發＝一個目錄項），不再是一個 JSONL 檔。
#: 換形態的理由是量出來的，見 `tools/lib/quota_ledger.py` 的 docstring（舊形態在 8 行程
#: × 40 筆的 barrier 探針下實測掉 30.9%、且撕行被靜默丟棄）。
FANOUT_LEDGER_NAME = "autosdd_quota_dispatch.d"
#: 降級痕跡（B2：「量不到」不得是靜默的）。per-account，同上不帶 sid。
QUOTA_TRACE_NAME = "autosdd_quota_degraded.jsonl"
#: 降級出聲的 per-source 閂鎖檔前綴。用 TTL 名額而不是 state 檔：後者是 read-modify-write，
#: 在 42 個平行 hook 下自己就會掉紀錄（＝本輪 B1 那個病的縮小版）。
DEGRADED_STAMP_PREFIX = "autosdd_quota_degraded_"
#: 95% 閂鎖的家（同樣 per-account）。
QUOTA_LATCH_NAME = "autosdd_quota_latch.json"

QUOTA_BRANCH_ARM = "arm"
QUOTA_BRANCH_NOTIFY = "notify"
QUOTA_BRANCH_ESCALATE = "escalate"


def quota_tier_of(pct: float | None) -> str:
    """水位 → 四個狀態之一。`pct is None` ⇒ `unmeasurable`（**不是** normal）。"""
    if pct is None:
        return QUOTA_UNMEASURABLE
    if pct >= QUOTA_HALT_PCT:
        return QUOTA_HALT
    if pct >= QUOTA_THROTTLE_PCT:
        return QUOTA_THROTTLE
    return QUOTA_NORMAL


def fanout_cap(pct: float | None) -> int | None:
    """該水位下每個滾動視窗准許幾次扇出派發。`None`＝不設限（normal／量不到）。"""
    tier = quota_tier_of(pct)
    if tier == QUOTA_HALT:
        return 0  # 🔴 這一格不吃任何覆寫：95% 那道的語意就是「停止」
    if tier != QUOTA_THROTTLE:
        return None
    raw = os.environ.get(QUOTA_CAP_ENV)
    try:
        override = int(str(raw)) if raw is not None else None
    except ValueError:
        override = None
    # 🔴 R81 收斂訂正本行原本的註解（不逐字複述當現行說法）：它宣稱覆寫「不得讓節流帶
    # 比 normal 寬鬆」，而 normal ＝ `None` ＝**不設限** ⇒ 那句話對任何有限的覆寫值都
    # 恆真，是一句空話；實作端也確實沒有上界（`max(0, override)`）。
    # 真正成立的不變量只有一條，而它是刻意的：**覆寫只能低到 0，不能低到負數**（負數會
    # 與 halt 的「恰為 0」混淆）；至於把它調大——那是**給人的逃生口**，語意與
    # `AUTOSDD_QUOTA_GUARD_OFF=1`（整條關掉）同級，只是粒度細一點。模型改不到 hook
    # 行程的環境，所以它不是模型的後門。halt 帶不吃任何覆寫（上面那一格已經 return）。
    return THROTTLE_FANOUT_CAP if override is None else max(0, override)


def quota_cache_path() -> Path:
    """`tools/lib/quota_meter.py` 寫的那一份。

    🔴 R81 收斂（Architect-B2）：**檔名與 schema 都不在本檔了**。此前這兩個字面在
    meter（唯一寫者）、本檔（唯一讀者）、測試檔各有一份**互不相關**的複本，而所有既有
    快取測試都傳明確 `path` 給 `read_quota()` ⇒ 「hook 讀的正好是 meter 寫的那一支」
    這個**生產綁定零覆蓋**：改掉 meter 的 `CACHE_NAME`，meter 寫新檔、hook 讀不到 →
    `pct=None` → 永遠不節流，而全套測試照綠。改成委派之後那個 desync 結構上不存在。
    meter 不可達時刻意回**目錄**本身（讀出來必是 OSError）⇒ 額度軸整條退化成「量不到」。
    """
    return (quota_meter.cache_path() if quota_meter is not None
            else Path(tempfile.gettempdir()))


def quota_schema() -> str:
    """快取 schema 字串；唯一的家在 meter。meter 不可達時回 `""`（⇒ 每份快取都判無效）。"""
    return quota_meter.SCHEMA if quota_meter is not None else ""


def fanout_ledger_path() -> Path:
    return Path(tempfile.gettempdir()) / FANOUT_LEDGER_NAME


def quota_latch_path() -> Path:
    return Path(tempfile.gettempdir()) / QUOTA_LATCH_NAME


def _aware(raw: object) -> datetime | None:
    """ISO 字串 → aware datetime；解不出來回 `None`。"""
    # 🔴 aware 是硬要求（R80 判準「naive 本地時間戳不得被持久化」）：naive 相減跨 DST
    # 會靜默差 3600 秒。本機時區不實施 DST ⇒ 這個缺陷在本機結構上重現不了。
    try:
        moment = datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo is not None else None


def read_quota(now: datetime, path: Path | None = None) -> dict:
    """讀快取並判新鮮度。回 `{pct, kind, resets_at, stale, source}`；`pct is None`＝量不到。"""
    blank = {"pct": None, "kind": "", "resets_at": None, "stale": None, "source": "no-cache"}
    try:
        data = json.loads((path or quota_cache_path()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return blank
    if not isinstance(data, dict):
        return dict(blank, source="bad-cache")
    if data.get("schema") != quota_schema():
        # 🔴 「schema 升版了」與「根本沒有快取」是兩件事，而它們在 R81 之前共用 `no-cache`
        # 這一個字面 ⇒ 痕跡讀起來一樣。schema 升版是**會發生**的（meter 自己記載過端點
        # 的頂層鍵正在長），而它的正確處置是去看 meter，不是去看網路。
        return dict(blank, source="schema-mismatch")
    pct, measured = data.get("pct"), _aware(data.get("measured_at"))
    if isinstance(pct, bool) or not isinstance(pct, (int, float)) or measured is None:
        return dict(blank, source="bad-cache")
    stale = (now - measured).total_seconds()
    reading = {"pct": float(pct), "kind": str(data.get("kind") or ""),
               "resets_at": data.get("resets_at"), "stale": stale, "source": "cache"}
    if stale > QUOTA_CACHE_TTL_SECONDS:
        # 🔴 SA-B4：過期的舊值**不得直接被採信為 normal**。這個量非單調（視窗翻頁會驟降）
        # 也非等速（率完全取決於當下在做什麼），所以「上調一個安全邊際」同樣是猜。
        # ⇒ 降級到 L4「量不到」：行為上不節流，但**狀態字與訊息說得出來它為什麼不節流**。
        # 🔴 R81 收斂：上一句在 R81 之前是**假的**——狀態字有（`source`），訊息一個字都
        # 沒有（SD-B2 四支注入探針實測 rc=0／stderr 0 bytes／零痕跡）。出聲那一半現在
        # 真的存在了，落點是 `note_degraded()`，由 `quota_gate()` 在 L4 分支呼叫。
        return dict(reading, pct=None, source="stale-cache")
    return reading


def reset_branch(resets_at: object, now: datetime) -> str:
    """95% 那道該做什麼：`arm`（排程等它）／`notify`（等沒有意義）／`escalate`（沒有 reset）。"""
    # 🔴 分支由**資料**決定，不由桶名決定（禁止寫死桶名清單：live payload 當回合 17 個
    # 頂層鍵，`claude.exe` 內嵌名單只有 8 個 ⇒ schema 正在長）。三條線的差別本來就是
    # 「reset 有多遠」：five_hour ≤5h、weekly 最長 7 天、spend **根本沒有 reset**。
    # 這一條是設計洞不是細節：把「95% ⇒ 排程等 reset」寫成無條件，會在週額度上排一支
    # 七天後才響的工作，而痕跡全綠——那與 R59 事故同形。
    moment = _aware(resets_at)
    if moment is None:
        return QUOTA_BRANCH_ESCALATE
    delta = (moment - now).total_seconds()
    return QUOTA_BRANCH_NOTIFY if delta > RESET_ARM_HORIZON_SECONDS else QUOTA_BRANCH_ARM


# 🔴 為什麼是「滾動視窗的派發率」而不是「in-flight 併發數」（SD-B1 的正面答覆）：
# 用 PreToolUse 記 dispatched、PostToolUse 記 completed 去算 in-flight，在這個 harness 上
# **恆讀 ≈0**——`Workflow` 47/47 是「launched in background」，那次呼叫在扇出開始前就結束、
# PostToolUse 當場觸發、completed 立刻追平 dispatched ⇒ cap 永遠綁不到。
# 而且那個形狀還自帶一個 SA-B6 的洩漏：被擋下的呼叫留下永遠不會有 completed 的 dispatched
# ⇒ 計數器只增不減、永久過度節流，外觀卻像「額度一直很緊」。
# 改記派發率之後兩個病一起消失：不需要 completed（不必動 PostToolUse 的註冊面）、
# 視窗一滾就自癒。而且**它更貼近被限制的資源**：額度是燒用量，不是併發數。
def claim_dispatch(root: Path, now: datetime) -> Path | None:
    """記一筆派發，回自己那一個目錄項。委派共用層，本檔不留第二份實作。"""
    return (quota_ledger.claim_dispatch(root, now.timestamp())
            if quota_ledger is not None else None)


def release_dispatch(entry: Path | None) -> bool:
    """把自己那一筆撤掉（`unlink` 自己 `O_EXCL` 建出來的目錄項，不是第二次 append）。"""
    return quota_ledger.release_dispatch(entry) if quota_ledger is not None else False


def live_dispatches(root: Path, now: datetime, window: int = FANOUT_WINDOW_SECONDS) -> int:
    """視窗內還算數的派發數。讀不到一律回 0（量不到 ≠ 節流）。

    🔴 R81 收斂（SD-B1 required_change ②）：**讀不懂的目錄項要出聲，不得靜默跳過**。
    舊版對解析失敗的行 `except ValueError: continue`，於是撕行被丟掉、帳目變小，
    而變小的方向正好是「看起來還有預算」——一個只會往放行方向錯的計數器。
    """
    if quota_ledger is None:
        return 0
    floor = now.timestamp() - window
    live, unreadable = quota_ledger.count_dispatches(root, floor)
    if unreadable:
        note_degraded("ledger-unreadable", f"派發帳裡有 {unreadable} 個讀不懂的目錄項")
    quota_ledger.prune_dispatches(root, floor)
    return live


def claim_refresh_slot() -> bool:
    """本 TTL 視窗內還沒有人量過 ⇒ 佔住這個位子回 `True`。這是**成本節流器**。

    用一支獨立的嘗試痕跡（不是快取本身）當節流器，因為要記的是「試過了」不是「成功了」：
    端點掛掉時不會寫快取 ⇒ 沒有這一格，每一次扇出呼叫都會再去打一次端點。

    🔴 R81 收斂（SD-B3）：舊實作是 check-then-act，零原子性 ⇒ 16 個壁鐘 barrier 對齊的
    行程實測 **CLAIM=16 SKIP=0**（設計意圖 1），也就是這個成本節流器在它唯一要治的
    情境下完全失效。原子性住在共用層的 `claim_once()`（`O_CREAT|O_EXCL`）。
    """
    if quota_ledger is None:
        return False
    mark = Path(tempfile.gettempdir()) / "autosdd_quota_refresh.stamp"
    return quota_ledger.claim_once(mark, QUOTA_CACHE_TTL_SECONDS)


def quota_trace_path() -> Path:
    return Path(tempfile.gettempdir()) / QUOTA_TRACE_NAME


def degraded_stamp_path(source: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in source)
    return Path(tempfile.gettempdir()) / f"{DEGRADED_STAMP_PREFIX}{safe}.stamp"


def note_degraded(source: str, detail: str) -> None:
    """額度軸降級時**出一次聲 ＋ 留一行痕跡**。這是 B2 的修法本體。

    🔴 立案（SD-B2 四支注入探針，落地前實測全部 rc=0／stderr 0 bytes／零痕跡）：
    `quota_gate()` 在 `pct is None` 且無地板時直接 `return 0`，**而且是在
    `quota_tier_of()` 被呼叫之前** ⇒ `QUOTA_UNMEASURABLE` 這個狀態字在 production
    一次都到不了（全 repo 只出現在常數定義／`quota_tier_of`／測試三處）。
    後果：token 過期、斷網、schema 升版、meter import 失敗，四種情況與「額度很健康」
    外觀完全一致 ⇒ B3／B4 都變成不可偵測。

    出聲帶 per-source TTL 閂鎖（不是每次都吵）：每次工具呼叫都出聲的守衛會被整個關掉，
    那是本 repo 反覆判過的形態。閂鎖用的是**原子的** `claim_once()`——42 個平行 hook
    同時降級時恰好一個說話，而不是 42 個一起說（或因為 state 檔互踩而說得沒有規律）。
    """
    if quota_ledger is None:
        return
    if not quota_ledger.claim_once(degraded_stamp_path(source), QUOTA_CACHE_TTL_SECONDS):
        return
    trace = quota_trace_path()
    quota_ledger.append_record(trace, {
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": source, "detail": detail, "pid": os.getpid(),
        "state": QUOTA_UNMEASURABLE})
    sys.stderr.write(
        f"⚠️  額度水位**量不到**（source={source}）⇒ 本次不節流，扇出照常放行。\n"
        f"   這不是「額度很寬鬆」：{detail}。\n"
        f"   現查：`python tools/lib/quota_meter.py --json`（失敗時會印 reason）；"
        f"痕跡：{trace}\n"
        f"   （同一個 source 每 {QUOTA_CACHE_TTL_SECONDS} 秒只說一次）\n")


def refresh_quota_blocking(timeout: int = QUOTA_SYNC_TIMEOUT_SECONDS) -> bool:
    """**同步**量一次並寫進 `quota_cache_path()`；回「有沒有拿到新讀數」。

    🔴 R81 收斂（Architect-B1）**推翻了本節原本那條「網路呼叫永遠不在 hook 的關鍵路徑
    上」的設計取捨**，理由照實記下（不逐字複述原說法當現行說法）：舊形態是快取過期時
    fire-and-forget 起一支刷新器、**本次仍用舊值判定**，而舊值被 `read_quota()` 正確地
    降級成「量不到」⇒ 淨效果是**過期就對任意規模的扇出全數放行**（複審探針實測：快取
    過期 600s／額度 99% 時，42 次 `Agent` 派發放行 42、擋下 0）。
    而「過期」是常態不是罕見：唯一的刷新呼叫點就在這條「已經量不到」的支線上、
    哨兵巡邏一次都不刷快取、TTL 又只有 180 秒 ⇒ 任何 ≥3 分鐘的非扇出工作之後，
    下一波扇出整批通過（本機佐證：刷新痕跡與快取 `measured_at` 之間 69 分鐘零自動刷新）。

    代價量過了，不是猜的：端點 RTT 實測 **0.33／0.36／0.41 秒**（本包當回合三次），
    逾時上界 4 秒；且它**只在扇出型工具**上、每 TTL 至多一次（`claim_refresh_slot`）
    ⇒ 不是「給每一次工具呼叫加上網路延遲」那個被否決的形態。收斂型工具（讀檔、寫檔、
    跑 git）在上游 `tool not in BLOCKING_TOOLS` 就返回了，一次都碰不到這裡。
    """
    if quota_meter is None:
        note_degraded("meter-missing", "取數器 import 不到（共用層不可達）")
        return False
    try:
        # 🔴 R81 收斂（SD-B2/B4）：走 `measure_detail` 而不是 `measure`。舊版把失效理由
        # 丟掉，四種失效在這裡外觀相同 ⇒ 連要寫進痕跡的東西都不存在。
        reading, reason = quota_meter.measure_detail(timeout)
        if reading is None:
            note_degraded(reason, "同步取數失敗（本 TTL 視窗唯一的一次嘗試）")
            return False
        return quota_meter.write_cache(reading, quota_cache_path())
    except Exception:  # noqa: BLE001 — 取數失敗最多是仍然量不到，不得變成故障源
        note_degraded("meter-crashed", "取數器自己拋了例外（已吞掉，不阻斷）")
        return False


def quota_floor_reading(payload: dict, now: datetime) -> dict | None:
    """L3 地板：逐字稿裡有**未復原**的撞線 ⇒ 水位下界 100%。`None`＝連地板都沒有。

    🔴 R81 收斂（Architect-B1 的另一半）：ADR-XPLAT-005 §2.1 與 Quota_Review D03 都用
    「逐字稿那層地板永遠在」替 L4 不節流辯護，而實作端 `quota_gate()` **一次都沒有呼叫過**
    `unhandled_limit_event()`（它的消費者只有哨兵與測試）⇒ 那層地板當時只存在於文件裡。
    這裡把它真的接上：離線、零 token、不依賴網路，正是 meter 全死時唯一還算數的證據。
    """
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    if transcript is None or not transcript.is_file():
        return None
    event = unhandled_limit_event(transcript)
    if event is None:
        return None
    reset = parse_reset_at(event.get("text"), now)
    return {"pct": 100.0, "kind": str(event.get("kind") or ""), "stale": None,
            "resets_at": reset.isoformat() if reset else None, "source": "transcript-floor"}


def arm_quota_wakeup(transcript: Path, plan: str) -> None:
    """95%／`arm` 分支：把喚醒掛上去（detached）。憑證＝planner 自己的 `NextRunTime` 閘。"""
    # 走既有的 `--arm-sentinel`：它是**唯一**不需要「已觀測 reset 時刻」就能武裝的入口，
    # 而 95% 這一刻**還沒撞線**（這正是本包的重點：不要走到撞線）。planner 內建的取證閘
    # （`relay_problems()` 禁止在 `next_run_time` 為空時把狀態寫成 armed）原封不動生效。
    # 🔴 planner 實測 749／750 行（餘裕 1 行）⇒ 本包**一行都沒有動它**，只當消費者。
    planner = repo_root() / "tools" / "session_resume_planner.py"
    if os.name != "nt" or not planner.is_file() or not plan:
        return
    try:
        subprocess.Popen(  # noqa: S603 — 同上
            [quiet_python(), str(planner), "--transcript", str(transcript),
             "--out", plan, "--arm-sentinel"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except Exception:  # noqa: BLE001 — 見上
        pass


def quota_halt_actions(payload: dict, reading: dict, now: datetime) -> dict:
    """95% 閂鎖那一刻真的做的事。回稽核欄位（給訊息與測試讀）。"""
    branch = reset_branch(reading.get("resets_at"), now)
    raw = payload.get("transcript_path")
    transcript = Path(raw) if isinstance(raw, str) and raw.strip() else None
    plan = write_resume_plan(transcript) if transcript and transcript.is_file() else ""
    # 🔴 哨兵的既有逃生口在這裡也算數：`AUTOSDD_SENTINEL_OFF` 的語意就是「不要替我武裝
    # 任何喚醒」。關掉時**必須在訊息裡說出來**——「關掉了所以沒武裝」與「武裝了」外觀
    # 相同就是假綠（同 M13「哨兵關掉時快取也會過期，且說得出來」的形狀）。
    off = bool(os.environ.get(SENTINEL_OFF_ENV))
    armed = (branch == QUOTA_BRANCH_ARM and os.name == "nt"
             and transcript is not None and not off)
    if armed:
        arm_quota_wakeup(transcript, plan)
    return {"branch": branch, "plan": plan, "armed": armed, "sentinel_off": off,
            "posix": os.name != "nt", "kind": reading.get("kind", "")}


def quota_halt_message(reading: dict, act: dict) -> str:
    """95% 的一次性訊息。三支分支**字串必須不同**，否則「不排程」與「排不了」外觀相同。"""
    head = (f"🔴 額度水位 {reading['pct']:.1f}%（≥{QUOTA_HALT_PCT:.0f}%，最緊的一條＝"
            f"{act['kind'] or '未知'}）⇒ **停止派發**：所有扇出型工具本次一律不執行。\n"
            f"   任務書：{act['plan'] or '（寫不出來——逐字稿路徑不可得）'}\n")
    if act["posix"]:
        # 🔴 SA-B7：mac/Linux 上武裝入口本身就有 `os.name != 'nt'` 早退 ⇒ 若沿用
        # weekly 那支「不排程」的靜默路徑，「不排程」與「排不了」會長得一模一樣。
        return head + ("   ⚠️ 本平台**沒有排程載具**（schtasks 只在 Windows 成立）"
                       "⇒ 已寫任務書，但**沒有武裝任何喚醒**。mac/Linux 請自行以 "
                       "launchd／cron 掛，或留在這裡等人回來。\n")
    if act["branch"] == QUOTA_BRANCH_ARM and act["armed"]:
        return head + (f"   ✅ 已武裝喚醒（reset 在 {reading['resets_at']}）。憑證是 "
                       "`NextRunTime` 這個**值**，不是 rc：\n"
                       "      Get-ScheduledTask | Where-Object TaskName -like "
                       "'AutoSDD_Sentinel_*' | Get-ScheduledTaskInfo\n")
    if act["branch"] == QUOTA_BRANCH_ARM:
        return head + ("   ⚠️ 這一條的 reset 近在眼前、本來該武裝喚醒，但**這次沒有武裝**："
                       + ("哨兵逃生口 " + SENTINEL_OFF_ENV + " 有設。\n" if act["sentinel_off"]
                          else "拿不到逐字稿路徑 ⇒ 沒有可以掛的任務書。\n"))
    if act["branch"] == QUOTA_BRANCH_NOTIFY:
        return head + (f"   🔴 這一條的 reset 在 {reading['resets_at']}（**遠超 "
                       f"{RESET_ARM_HORIZON_SECONDS // 3600} 小時**）⇒ 「等」幾乎沒有意義，"
                       "本次**刻意不排程**（排一支七天後才響的工作而痕跡全綠＝R59 事故同形）。"
                       "改做不吃額度的工作，或降扇出／切小模型。\n")
    return head + ("   🔴 這一條**沒有 reset 可以等**（例：月度支出上限）⇒ 排程是錯的動作。"
                   "只有人去提額才會回來：https://claude.ai/settings/usage\n")


def throttle_horizon_line(reading: dict, now: datetime) -> str:
    """節流帶要說出「這道限制會套多久」。🔴 R81 收斂（SD 非 blocking ①）。

    halt 帶用 `reset_branch()` 分得出 arm／notify／escalate，**throttle 帶完全不分** ⇒
    週額度越 80% 時 cap 會連續套用好幾天，與 five_hour 80%（最多 5 小時）代價差一個
    數量級，而訊息裡讀不出差別。本行**只把差別說出來，不動 cap 的階梯**：那個階梯的
    數值是掌舵者訂的政策（80 少派／95 停止），要按 reset 距離分檔是政策決定不是實作
    細節，已登記進缺陷帳本交由下一輪承接（輪號寫在帳本，不寫進程式碼檔——程式碼裡的
    輪號會超前帳本時鐘，`check_defect_log_crossref` 有專屬判準）。
    """
    branch = reset_branch(reading.get("resets_at"), now)
    if branch == QUOTA_BRANCH_ESCALATE:
        return ("   ⏳ 這一條**沒有 reset 可以等**（例：月度支出上限）⇒ 這道節流不會自己"
                "解除，只有人去提額：https://claude.ai/settings/usage\n")
    if branch == QUOTA_BRANCH_NOTIFY:
        return (f"   ⏳ 這一條的 reset 在 {reading.get('resets_at')}（**遠超 "
                f"{RESET_ARM_HORIZON_SECONDS // 3600} 小時**）⇒ 這道節流會**連續套用好"
                "幾天**，不是等一下就好。改做不吃額度的工作，或降扇出／切小模型。\n")
    return (f"   ⏳ 這一條的 reset 在 {reading.get('resets_at')}（{RESET_ARM_HORIZON_SECONDS // 3600}"
            " 小時內）⇒ 這道節流很快就會自己解除。\n")


def quota_throttle_message(reading: dict, tool: str, cap: int, live: int,
                           now: datetime) -> str:
    if tool in UNBOUNDED_FANOUT_TOOLS:
        return (f"⚠️  額度水位 {reading['pct']:.1f}%（≥{QUOTA_THROTTLE_PCT:.0f}%，最緊的一條＝"
                f"{reading['kind'] or '未知'}）⇒ `{tool}` 本次不執行。\n"
                "   理由不是「太多」而是「數不到」：一次 Workflow 啟動會在背景生出未知數量的"
                "agent，而那一刻**沒有任何 hook 會被叫到**（本包實測：tool_result 47/47 是"
                "「launched in background」）⇒ 事後界不住。節流帶請改逐個派 `Agent`"
                f"（每 {FANOUT_WINDOW_SECONDS}s 最多 {cap} 個）。\n"
                + throttle_horizon_line(reading, now))
    return (f"⚠️  額度水位 {reading['pct']:.1f}%（≥{QUOTA_THROTTLE_PCT:.0f}%，最緊的一條＝"
            f"{reading['kind'] or '未知'}）⇒ 少派 agent：每 {FANOUT_WINDOW_SECONDS}s 最多 "
            f"{cap} 次扇出，本視窗已用 {live} 次 ⇒ `{tool}` 本次不執行。\n"
            "   等一下再派，或改做不需要扇出的收斂工作（讀檔／寫檔／跑測試都沒有被擋）。\n"
            + throttle_horizon_line(reading, now)
            + f"   逃生口：設 {QUOTA_OFF_ENV}=1（關掉整條額度節流）或 {QUOTA_CAP_ENV}=<n>。\n")


def quota_gate(payload: dict) -> int:
    """額度軸的**獨立**判定入口。回 0＝放行、2＝擋下。不讀 context、不碰網路。"""
    if os.environ.get(QUOTA_OFF_ENV):
        return 0
    tool = str(payload.get("tool_name") or "")
    if tool not in BLOCKING_TOOLS:
        return 0  # 收斂（讀檔、寫任務書、跑 git）永遠不受額度節流影響
    now = datetime.now().astimezone()
    reading = read_quota(now)
    if reading["pct"] is None and claim_refresh_slot():
        # 🔴 唯一會碰網路的一格，三個條件同時成立才到得了：扇出型工具 ＋ 已經量不到 ＋
        # 本 TTL 視窗還沒有人量過。理由與實測代價見 `refresh_quota_blocking` 的 WHY。
        refresh_quota_blocking()
        now = datetime.now().astimezone()
        reading = read_quota(now)
    if reading["pct"] is None:
        floor = quota_floor_reading(payload, now)
        if floor is None:
            # L4：**真的**量不到（同步量過了、也沒有未復原的撞線）才不節流。斷網時自動把
            # 併發降到 2 會讓「網路壞了」與「額度真的滿了」外觀完全相同且靜默——同
            # `may_block()` 既有判例「分母是猜的就不擋」。
            # 🔴 但**不節流 ≠ 不出聲**（SD-B2）：這條路在 R81 之前是零 stderr、零痕跡，
            # 與「額度很健康」外觀一模一樣，於是 B3／B4 全部變成不可偵測。
            note_degraded(str(reading.get("source") or "unknown"),
                          "取數失敗，且逐字稿裡沒有未復原的撞線可以當地板"
                          f"（狀態＝{quota_tier_of(None)}）")
            return 0
        reading = floor  # L3 地板：撞線且未復原 ⇒ 下界 100% ⇒ 落進 halt
    tier = quota_tier_of(reading["pct"])
    if tier == QUOTA_NORMAL:
        return 0
    if tier == QUOTA_HALT:
        latch = quota_latch_path()
        # 閂鎖鍵帶 (kind, reset 分鐘)：新的視窗＝重新武裝一次。截到分鐘是因為 `resets_at`
        # 有次秒級抖動（它是 now+剩餘算出來的），字串相等比較會每次都判「reset 變了」。
        key = f"halt@{reading['kind']}@{str(reading['resets_at'])[:16]}"
        if key not in announced_latches(latch):
            remember_latch(latch, key)
            sys.stderr.write(quota_halt_message(
                reading, quota_halt_actions(payload, reading, now)))
        else:
            sys.stderr.write(f"🔴 額度 {reading['pct']:.1f}% ≥ {QUOTA_HALT_PCT:.0f}%"
                             f"：`{tool}` 仍然不執行（閂鎖已觸發過，任務書已在磁碟上）。\n")
        return 2
    cap = fanout_cap(reading["pct"]) or 0
    if tool in UNBOUNDED_FANOUT_TOOLS:
        sys.stderr.write(quota_throttle_message(reading, tool, cap, 0, now))
        return 2
    root = fanout_ledger_path()
    # 🔴 先記帳再數（含自己這一筆），而不是先數再記：42 個 `Agent` 在同一則 assistant
    # message 裡平行派發時 PreToolUse 是平行觸發的 ⇒ 先數再記會讓它們全部讀到 live<cap
    # 而全數放行。先記再數之後，**目錄項的建立順序**替我們排了序，後到的看得到前面的。
    #
    # 🔴 R81 收斂訂正本段原本那句「極端競態下可能全部讀到超額而全數擋下——那是安全方向，
    # 且 `undo` 會把預算還回去」（不逐字複述當現行說法）：後半句實測不成立。舊實作的
    # `undo` 是**第二次 append**，而 append 在 Windows 上跨行程不是原子的 ⇒ 20 個平行
    # Agent 的探針量到 `try=20 undo=17`（各應為 20），`live_dispatches()` 讀回 3、cap=2，
    # 於是接著單獨派 1 個 Agent（遠低於 cap）**被幽靈計數擋下**（rc=2）。也就是說「安全
    # 方向」那句話掩蓋掉的正是 SA-B6 要治的永久過度節流，只是換了成因復發。
    # 現在記帳與撤銷各自是**一次原子的目錄項變動**（建立／刪除自己那一個），兩個方向的
    # 掉帳都不存在——實測見 `tools/lib/quota_ledger.py` docstring 的三組 barrier 探針。
    entry = claim_dispatch(root, now)
    live = live_dispatches(root, now)
    if live <= cap:
        return 0
    # 🔴 SA-B6：被擋下的呼叫**不得**在帳上留下永久佔位，否則節流期間計數器只增不減，
    # 一旦到 cap 就永遠回不來（即使 quota 已經掉回 50），而失效方向是永久過度節流、
    # 外觀像「額度好像一直很緊」。
    release_dispatch(entry)
    sys.stderr.write(quota_throttle_message(reading, tool, cap, live - 1, now))
    return 2


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
        # 🔴 額度那把尺**必須在這裡**求值，不能往下擺（SA-B1 判過的死碼）。下面五道早退
        # 全是 context 語意，而 `tier_of()` 在 context <75% 一律回 `None` ⇒ 撞額度那一刻
        # （實測水位只有 ~18~20%）任何掛在 `block_verdict()` 裡的 quota 分支都到不了。
        # 兩把尺不共用早退條件，這一行的位置就是那個設計。
        if blocking and (quota_stop := quota_gate(payload)):
            return quota_stop
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
