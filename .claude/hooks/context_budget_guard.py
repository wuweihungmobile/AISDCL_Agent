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

相依規則（R82／Q2-01 訂正：此前寫「本檔只用 stdlib」，而下面幾行就 import 了四支 tools/lib）
------------------------------------------------------------------------------------
①能力提供者（quota_gate／platform_utils）一律 try/except，不可達時該軸退化成「量不到」；
②判讀原語（quota_limits）hard import，給 stub 等於讓同一份字面有第二個家；
③`tools/lib/*` **只准裸名 import**——`from lib import X` 會讓同一份原始碼在同一行程裡
有兩個模組物件（`ModuleIdentityIsSingleTest` 在守）。反向依賴仍允許：planner import 本檔。

🔴 R82／Q2-02：本檔的**職責邊界**（額度軸已經不在這裡了）
--------------------------------------------------------
本檔只剩一把尺——**context 水位**：量它、判 window、越線時出聲／擋展開型工具／寫任務書，
外加哨兵武裝的**觸發面**（R82／HELM-02 起：SessionStart 只清閂鎖，真正註冊延後到
PostToolUse 且要通過 `tools/lib/sentinel_lifecycle` 的雙門檻——立案是掌舵者當場截圖的
「排程器裡三支哨兵，兩支屬於活 5 秒／12 秒的 session」）。**額度水位那把尺整條住 `tools/lib/quota_gate.py`**，本檔對
它只有兩件事：①`main()` 在五道 context 早退**之前**呼叫它一次（撞額度那刻 context 水位
可能只有 ~18%，掛在早退之後的分支一次都不會被執行——那是 SA-B1 判過的死碼）；
②把它需要的四個 hook 端能力注入進去（阻斷名單／閂鎖讀寫／任務書／喚醒武裝）。
兩把尺不共用早退條件、也不共用模組，就是那個設計。既有架構鎖
`test_quota_is_not_wired_into_the_context_blocking_path` 的射程零改變且更容易成立。

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

# 額度水位節流閘（80/95 兩道）整條的家＝`tools/lib/quota_gate.py`（R82／Q2-02）。搬走的
# 是一個完整主題：輸入是額度快取／逐字稿撞線，輸出是「這次扇出准不准」，與 context 水位
# 零交集。形態與上一格逐字相同（同一條 sys.path、同一種 fail-open）：不可達時本符號為
# `None`，額度軸整條退化成「量不到」＝不節流，而**不會**把 context 阻斷也一起帶走
# ——那是拆分的硬安全條件（見該檔檔頭），不是風格偏好。
try:
    import quota_gate  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 見上
    quota_gate = None  # type: ignore[assignment]

# 哨兵的**生命週期判準**（值不值得一支 schtasks、什麼時候收）整條的家＝
# `tools/lib/sentinel_lifecycle.py`。形態同上一格：不可達時本符號為 `None`，
# 武裝整條退化成「不武裝」——那個方向安全（少一層續航保護），反過來（不可達就無條件
# 武裝）才是 R82 之前那個會在排程器裡增生的形狀。
try:
    import sentinel_lifecycle  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 見上
    sentinel_lifecycle = None  # type: ignore[assignment]

# 排程**載具**（schtasks／launchd／沒有）唯一的家＝`tools/lib/schedule_backend.py`。
# 形態同上一格（同一條 sys.path、同一種 fail-open）：不可達時本符號為 `None`，
# `_has_carrier()` 回 False ⇒ 武裝整條退化成「不武裝」，方向與上一格一致（少一層續航
# 保護，而不是無條件武裝）。
# 🔴 R83／W2-A：本檔此前用 `os.name != "nt"` 在**四個**武裝站點各判一次平台，於是
# 「mac 上有沒有排程載具」這個問題有四個答案的家；補 mac 支援時只要漏改一個，那一臂
# 就會靜默失明（而失明的表徵與「這台機器本來就沒有載具」完全相同）。現在四個站點一律
# 問 `_has_carrier()`，而它只是把問題轉給那個唯一的提問點。
try:
    import schedule_backend  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001 — 見上
    schedule_backend = None  # type: ignore[assignment]


def _has_carrier() -> bool:
    """這台機器上有沒有排程載具（Windows schtasks／macOS launchd）。"""
    return schedule_backend is not None and schedule_backend.has_carrier()

# 額度**撞線判讀**（`SYNTHETIC_MODEL`／`LIMIT_*`／`classify_limit`／`parse_reset_at`／
# `unhandled_limit_event` …）唯一的家＝`tools/lib/quota_limits.py`。它是 R81 收斂把本檔
# 從 1,730 行壓回棘輪之內的那一次減法：搬走的是一個完整主題（輸入是撞線訊息／逐字稿，
# 輸出是判讀結果），一行都不碰 context 水位與阻斷決策。**為什麼這一格沒有 try/except**
# （與上面兩格刻意不同）見該檔 docstring 最後一段：能力提供者可以降級，判讀原語不行——
# 給它 fallback stub 等於讓同一份字面有第二個家，而且會用錯的答案靜默通過。
# `tools/session_resume_planner.py` 以 `guard.<name>` 取用這些符號 ⇒ 這裡把它們 import
# 回本檔的命名空間，呼叫端與既有回歸鎖一個字都不必改。
# 🔴 下面 10 個在本檔內一次都不會被呼叫：它們是給 planner 的純再匯出（`guard.
# classify_limit` 這種取法），刪掉任一個 planner 會在無人看管的排程路徑上 AttributeError。
# R82（Q2-01）刪掉了此前替它們背書的 15 行 tuple 常數——它零消費者（全 repo 只命中定義
# 那一行），真正在做事的只有 lint 那一半，而那件事下一行的 F401 抑制一個字就說得完。
from quota_limits import (  # noqa: E402,F401
    LIMIT_SESSION, LIMIT_SPEND, LIMIT_TRANSIENT, LIMIT_UNKNOWN, SYNTHETIC_MODEL,
    classify_limit, declared_zone, latest_limit_event, latest_success_at,
    newest_activity_at, parse_reset_at, session_transcripts, unhandled_limit_event)

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

#: 無 console 父行程下 spawn 子行程的**防彈窗**兩層防線（`NO_WINDOW` 旗標 ＋
#: `quiet_python()` 載具）唯一的家＝`tools/lib/win_spawn.py`（R84／C8 的減法）。
#: 搬走的理由與 `quota_limits` 那一格逐字同構：那是一個完整主題，且本檔此前是它的家
#: 而 lib 反過來 import hook（方向倒了，`quota_meter.py` 因此留過第二份字面）。
#: **刻意沒有 try/except**（同 `quota_limits` 判例）：原語不能有 fallback stub，
#: 給 `NO_WINDOW` 一個 `0` 的備援等於在 Windows 上用錯的答案靜默通過（旗標沒帶、
#: 視窗照彈）。`session_resume_planner` 以 `guard.NO_WINDOW`／`guard.quiet_python()`
#: 取用 ⇒ 這裡 import 回本檔命名空間，呼叫端與既有回歸鎖一個字都不必改。
from win_spawn import NO_WINDOW, quiet_python  # noqa: E402,F401

#: 🔴 送進 `powershell.exe`（5.1）的每一段腳本都要以這一行開頭。
#: 立案（掌舵者當回合實測，哨兵稽核 jsonl 逐字）：`"next_run_time": "2026/8/9 �U�� 07:14:19"`
#: ——`Get-ScheduledTaskInfo` 的 `NextRunTime` 由 `Format-List` 以**當前文化** zh-TW 算繪成
#: 「下午」，PS 5.1 把它以主控台 codepage（本機 cp950）寫進 stdout，而 Python 這一側以
#: `encoding="utf-8"` 讀 ⇒ 逐位元組降解成 `?`。後果不只難看：那個字串是**取證憑證**
#: （`next_run_time`），而降解過的憑證仍然非空 ⇒ 取證規則照樣判綠，只是它記下來的時刻
#: 人再也讀不出來。同族問題本 repo 已有 `init_utf8_streams()`（Python 那一側）；這一格是
#: **PowerShell 那一側**缺的那一半。
#: 放在本檔而不是各自為政：`session_resume_planner`／`sentinel_lifecycle`／`console_spawn_watch`
#: 三個消費者，前兩者已經在向本檔取 `NO_WINDOW`／`quiet_python()`，同一族知識同一個家。
PS_UTF8_PRELUDE = ("$OutputEncoding = [Console]::OutputEncoding = "
                   "[Text.UTF8Encoding]::new($false)\n")

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


# ───────────────────────── 預防性哨兵的**觸發層**（R79 補洞包；R82／HELM-02 改觸發時機）
# 🔴 R82／HELM-02 訂正本段的**時機**（方向不變、理由不變，改的是「在哪一刻按下去」）：
# 下面整段論證的是「非預防性武裝不可」，那一半今天仍然成立、一個字都沒被推翻。被推翻的是
# 它的實作把「預防性」等同於「SessionStart 就註冊」——掌舵者當場截圖回報排程器裡三支
# `AutoSDD_Sentinel_*`，實測其中兩支屬於**活了 5 秒與 12 秒**的短命 session。
# 現行形狀：SessionStart 只**清閂鎖**（見 `arm_sentinel`），真正的註冊延後到 PostToolUse
# 且要通過 `tools/lib/sentinel_lifecycle.should_arm()`（回合數＋存活跨度雙門檻，門檻取值
# 是量出來的，見該檔 docstring）。延後的代價已界定：一個 8 分鐘就結束的 session 拿不到
# 續航；而它換掉的是「每一支 5 秒探針都留一支每 15 分鐘醒來的排程」。
# 🔴 為什麼判準不能寫在 SessionStart 那一刻：見取捨②——那一刻逐字稿往往還不存在，
# 手上沒有任何可以量的東西；而 payload 欄位分不出主 session 與探針（實測六支短命逐字稿
# 與主 session 結構同形，差別只在規模）。
#
# 🔴 為什麼非得預防性不可（不是「順手掛一下」）：
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
def spawn_sentinel(transcript_raw: str, out: str, log: object = None) -> bool:
    """Detached 起 planner 的 `--arm-sentinel`；回「有沒有真的 spawn 出去」。

    🔴 R82／Q2-02 的減法：SessionStart 武裝與額度 95% 喚醒武裝此前是**兩份逐字相同的
    `Popen`**（同一支 planner、同一組旗標、同一個 `creationflags`），差別只有「要不要寫
    boot log」。兩份各自演化的代價已經看得到：R80 修「`DETACHED_PROCESS` 讓視窗回來」
    那一次只改了其中一份。收成一份之後那個漂移在結構上不存在。
    """
    planner = repo_root() / "tools" / "session_resume_planner.py"
    if not _has_carrier() or not planner.is_file() or not transcript_raw or not out:
        return False
    try:
        subprocess.Popen(  # noqa: S603 — 參數全是本檔算出來的路徑，無 shell
            [quiet_python(), str(planner), "--transcript", transcript_raw,
             "--out", out, "--arm-sentinel"],
            stdout=log if log is not None else subprocess.DEVNULL,
            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            # 🔴 R80：舊寫法帶了 `DETACHED_PROCESS`，而它在**本 venv 的 trampoline 載具**
            # 上會讓視窗回來（矩陣見 NO_WINDOW 第二列：`DET` 與 `DET|CNW` 兩格皆「可見」）
            # ——上面取捨①宣稱的「不彈視窗」在寫下的當回合就不成立，且失效是靜默的
            # （旗標有設、視窗照彈）。**不要把這句讀成「DETACHED 會抵銷 CNW」**：那是本檔
            # 第一版的過度一般化，真直譯器那一列 `DET|CNW` 是 0，翻面的是載具不是旗標語意。
            # 取捨①要的「不同步等它跑完」由「不呼叫 wait()」提供，與旗標無關；子行程活過
            # 父行程退場這件事也已實測不需要 DETACHED_PROCESS（父死 8 秒後子仍寫出痕跡）。
            creationflags=NO_WINDOW)
    except Exception:  # noqa: BLE001 — 見上方取捨③：武裝失敗不得反過來變成故障源
        return False
    return True


def arm_sentinel(payload: dict) -> None:
    """SessionStart：**不再直接武裝**，只把上一輪的武裝閂鎖清掉並留一行痕跡。

    🔴 為什麼還要清閂鎖（不是「什麼都不做就好」）：`claude -r` 續接一個已經下班（6 小時
    閒置自我解除）的 session 時，閂鎖若留著就再也不會重新武裝＝續航被靜默弄丟。清掉之後
    下一次工具呼叫會重新評估，而那時逐字稿早就過門檻 ⇒ 立刻補上。
    boot log 保留：它是「SessionStart 有沒有被叫到」唯一的痕跡，而本輪正是靠它才發現
    有四支短命 session 根本沒觸發過這支 hook（沒有 boot log）。
    """
    if not _has_carrier() or os.environ.get(SENTINEL_OFF_ENV):
        return  # 沒有排程載具就沒有續航可言（見 `_has_carrier`）；人要關就關得掉
    raw = payload.get("transcript_path")
    if not isinstance(raw, str) or not raw.strip():
        return
    sid = session_id_of(Path(raw))
    if sentinel_lifecycle is not None:
        sentinel_lifecycle.clear_arm_latch(sid)
    swept = spawn_sentinel_gc(sid)
    with (Path(tempfile.gettempdir()) / f"autosdd_sentinel_boot_{sid}.log").open(
            "a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"\n=== session-start {datetime.now().isoformat(timespec='seconds')}"
                     " （閂鎖已清；武裝延後到累積夠工作量的那一刻）"
                     f"｜孤兒回收 spawn={swept} ===\n")


# 🔴 R84／C3-P4b：`sentinel_lifecycle.gc()` 此前**零自動呼叫端**——它只從 `main()` 的
# CLI 走得到，而那條路要有人記得去跑。後果實測得到：本機留著一支 session 早就結束的
# `AutoSDD_Sentinel_*`，每 15 分鐘照樣醒來一次（掌舵者看到的黑框就是它）。收拾別人的
# 殘骸這件事**只能由後來的人做**（哨兵自己那一支若卡在讀不出狀態，見 `_sentinel_tick`
# 的 abort 分支），所以呼叫點選在 SessionStart：那正好是「後來的人開工」的那一刻，
# 也是本函式已經在清閂鎖的地方（同一族的清理，不另開第二個時機）。
#
# 三個刻意的取捨，與 `spawn_sentinel` 逐條同構（同一族的風險，同一組處置）：
#  ① **detached 子行程**：`gc()` 要列舉排程器（外呼 `launchctl`／`schtasks`），同步做等於
#     每次開 session 先卡幾秒。
#  ② **`keep=(當前 sid,)`**：本 session 自己的哨兵絕不能被自己收掉。`gc()` 內另有一層
#     「最新 session」保護，這一層是顯式的那一份——兩層獨立成立。
#  ③ **一切例外吞掉**：`.claude/settings.json` 記載過的 P0（hook 誤觸會把所有工具硬鎖死）。
#     回收失敗最多是殘骸多留一輪，絕不可反過來變成故障源。
def spawn_sentinel_gc(keep_sid: str) -> bool:
    """Detached 起 `sentinel_lifecycle --gc --apply`；回「有沒有真的 spawn 出去」。"""
    lifecycle = repo_root() / "tools" / "lib" / "sentinel_lifecycle.py"
    if not _has_carrier() or not lifecycle.is_file() or not keep_sid:
        return False
    try:
        subprocess.Popen(  # noqa: S603 — 參數全是本檔算出來的路徑／本 session 的 id
            # 🔴 沒有 `--gc` 這個旗標：回收**就是**這支 CLI 的唯一動作（`main()` 無子指令）。
            # 多送一個不存在的旗標會讓 argparse 直接 rc=2 而什麼都不收，且因為 stdout 全丟
            # DEVNULL，那個失敗**完全靜默**——正是本輪在治的那一族。
            [quiet_python(), str(lifecycle), "--apply", "--keep", keep_sid],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except Exception:  # noqa: BLE001 — 見上方取捨③
        return False
    return True


def arm_when_earned(transcript: Path) -> str:
    """PostToolUse：夠格才武裝。回理由字串（呼叫端不讀，留給測試與未來的痕跡）。

    一切例外吞掉：`.claude/settings.json` 的 description 記載過 P0（hook 誤觸會把所有
    工具硬鎖死），而武裝失敗最多是少一層保護，絕不可反過來變成故障源。
    """
    if (not _has_carrier() or os.environ.get(SENTINEL_OFF_ENV)
            or sentinel_lifecycle is None):
        return "disabled"
    sid = session_id_of(transcript)
    try:
        return sentinel_lifecycle.maybe_arm(
            transcript, sid, spawn=spawn_sentinel,
            plan_path=str(Path(tempfile.gettempdir()) / f"{PLAN_PREFIX}{sid}.md"))
    except Exception:  # noqa: BLE001 — 見上
        return "error"


def arm_quota_wakeup(transcript: Path | None, plan: str) -> dict:
    """額度 95%／`arm` 分支的喚醒武裝；回 `{armed, sentinel_off, posix}` 給訊息用。

    🔴 平台判斷與逃生口刻意留在 hook 這一側：`tools/lib/quota_gate.py` 只讀這份回報，
    自己不去問 `os.name`、也不去讀哨兵的環境變數——那會讓同一份平台知識有第二個家。
    🔴 `armed` 是**真的 spawn 出去了**，不是「我走到了那個分支」：舊實作把兩者混同
    （Popen 拋例外時照樣回報 armed），而那正是本 repo 反覆判過的「真紅讀成綠」。
    憑證仍是 planner 自己的取證閘（`relay_problems()` 禁止在兩個憑證鍵皆空時把狀態寫成
    armed），本函式一行都沒有動它，只當消費者。

    🔴 R83／W2-A 的射程，以及**這一段自己在同一輪內就轉假的那兩句**（原文保留為沿革，
    照本 repo 體例逐字訂正而不是靜默刪掉）：
    `posix` 這個鍵的語意是「這台機器沒有排程載具」，它現在由 `_has_carrier()` 決定
    ⇒ **mac 上它變成 False**，因為 mac 現在真的武裝得起來（launchd）。**這一句仍然為真。**
    原文接著寫的是：`tools/lib/quota_gate.py::quota_halt_message` 在 `posix=False and armed`
    那一支印的取證指令逐字是 `Get-ScheduledTask …`（mac 上不存在），而「那一檔不在本包的
    授權範圍內…故只在這裡具名登記、**不偷改**：訊息會指錯路」。
    🔴 **兩句在本輪內都已為假**（複審 SD／FC-1 逐字判過，我複驗）：同一棵工作樹的
    `tools/lib/quota_gate.py` 已由 R83／F2-② 就地訂正——`evidence_hint()` 委派給
    `schedule_backend.select().evidence_hint()`。收斂當回合實跑 `quota_gate.evidence_hint()`
    在 darwin 上的輸出含 `launchctl print gui/501/<label>`，
    `contains 'Get-ScheduledTask': False`／`contains 'launchctl': True`。
    留著它的代價不是文字難看：**下一個人會照這段散文去修一個已經修好的東西**，
    或反過來相信 mac 的取證指引還是壞的（與 R74 訂正文自己成假話、R80「`.py` 行尾那格
    自陳沒人守而其實有鎖」同一族）。
    ⇒ 現行事實：取證指令的唯一的家＝各後端的 `evidence_hint()`（`tools/lib/schedule_backend.py`）。
    本函式只回報 `armed`／`sentinel_off`／`posix` 三個布林，一行取證字串都不產。
    """
    if not _has_carrier():
        return {"armed": False, "sentinel_off": False, "posix": True}
    if os.environ.get(SENTINEL_OFF_ENV):
        return {"armed": False, "sentinel_off": True, "posix": False}
    return {"armed": transcript is not None and spawn_sentinel(str(transcript), plan),
            "sentinel_off": False, "posix": False}


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
        # 🔴 R82／C2：`.env` 裡的逃生口必須真的算數。本檔的三個開關（`GUARD_OFF_ENV`／
        # `SENTINEL_OFF_ENV` 兩處）與 `quota_gate` 的那一個此前全讀 `os.environ` ⇒ 使用者
        # 照 `.env.example` 抄一份 `.env` 把守衛關掉，守衛照擋，而「關掉了」與「沒關掉」
        # 外觀完全相同。這一行把 `.env` 裡**我們自己宣告過的鍵**（`ENV_SPEC` 白名單，
        # 不是整份檔——`.env` 也放機密，整份灌進 env 會隨 Popen 繼承到子行程）填成行程級
        # 預設，缺席才填 ⇒ 真環境變數仍然贏。放在 `main()` 而不是模組層：模組層副作用會
        # 讓「import 本檔的測試」被開發機上的 `.env` 影響。
        # 回歸鎖：`tools/tests/test_context_budget_guard.py::EnvFileReachesEveryEscapeHatchTest`。
        if quota_gate is not None:
            quota_gate.apply_env_defaults(os.environ)
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
            # 這一支不量水位、不出聲、恆 exit 0：它只負責把上一輪的武裝閂鎖清掉
            # （R82／HELM-02：真正的武裝已延後到 PostToolUse，見 `arm_when_earned`）。
            arm_sentinel(payload)
            return 0
        blocking = event == "PreToolUse"
        # 🔴 R83：額度軸只在**我們真的推理過的那兩個事件**上動作。少了這一格，接電會順手
        # 把「事件名讀不出來」（壞 payload、未來新增的事件）也當成觀測點——本輪注入實測：
        # 一份沒有 `hook_event_name` 的 payload 會走完整條額度判讀並出聲，而那類 payload
        # 依本檔既有契約應該是「量測暫時不可得 ⇒ 靜默 rc=0」。射程要靠白名單而不是靠
        # 「不是 PreToolUse 就當 PostToolUse」，後者是預設開啟、方向錯的。
        measuring = event in ("PreToolUse", "PostToolUse")
        # 🔴 額度那把尺**必須在這裡**求值，不能往下擺（SA-B1 判過的死碼）。下面五道早退
        # 全是 context 語意，而 `tier_of()` 在 context <75% 一律回 `None` ⇒ 撞額度那一刻
        # （實測水位只有 ~18~20%）任何掛在 `block_verdict()` 裡的 quota 分支都到不了。
        # 兩把尺不共用早退條件，這一行的位置就是那個設計。
        # 🔴 R83／接電：`blocking and` 這個前綴拿掉了，`event` 改為傳進去。立案是量出來的
        # ——舊條件讓額度那把尺**只在「我要扇出」那一刻**被問一次，而 R83 實測配額 5%→90%
        # 的整段，主 session 派完最後一波之後再也沒呼叫任何扇出型工具（後續全是全樹跑、
        # agent 回傳、大量讀檔）⇒ 本閘從頭到尾一次都沒被叫到。燒額度的是「我自己在做事」
        # 那條路，而 PostToolUse 的 matcher（`Read|Task|Grep|Glob|…|Bash|PowerShell`）
        # **本來就覆蓋**那條路 ⇒ `settings.json` 一個字都不用改，缺的只有這裡的條件與參數。
        # 射程的第二半在 `quota_gate()` 內（PostToolUse 不記派發帳、不擋節流帶），兩邊要一起讀。
        if measuring and quota_gate is not None and (quota_stop := quota_gate.quota_gate(
                payload, blocking=BLOCKING_TOOLS, latch_read=announced_latches,
                latch_write=remember_latch, plan_writer=write_resume_plan,
                waker=arm_quota_wakeup, event=event)):
            # 🔴 R83／Δ13：**接電引入的新缺陷，必須在同一個 commit 處理。** halt 帶在
            # PostToolUse 會**每一次**回 2 ⇒ 本 hook 在這裡提早 return ⇒ 下面那個
            # `arm_when_earned()` 在整個 halt 期間（一直到 reset）一次都不會執行，
            # context 續航哨兵靜默失去所有武裝機會。而額度那層的喚醒武裝只在 halt 閂鎖
            # **第一次**觸發時試一次、失敗不重試（見 `quota_gate` 的 D2 重排）⇒ 兩層都沒了。
            # 兩層續航是不同的東西（一次性 reset 喚醒 vs 900s 巡邏），不得因為額度那層
            # 說了話就把 context 那層吃掉。`arm_when_earned` 自身有閂鎖與 fail-open。
            raw = payload.get("transcript_path")
            if not blocking and isinstance(raw, str) and Path(raw).is_file():
                arm_when_earned(Path(raw))
            return quota_stop
        raw_path = payload.get("transcript_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return 0  # 量測暫時不可得 ≠ 輸入壞掉，見模組 docstring 的行為契約
        transcript = Path(raw_path)
        if not transcript.is_file():
            return 0
        # 🔴 哨兵武裝掛在這裡（不是 SessionStart，理由見 `arm_when_earned` 上方那段），而且
        # **必須在下面五道 context 早退之前**：`tier_of()` 在水位 <75% 一律回 `None`，掛在
        # 後面等於永遠不會被執行（同 SA-B1 判過的死碼形狀，只是換一把尺）。閂鎖已設時它只
        # 做一次 `Path.exists()`，所以放在每次工具呼叫都會經過的路徑上是付得起的。
        if not blocking:
            arm_when_earned(transcript)

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
