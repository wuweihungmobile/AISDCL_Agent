# DEF-200-275 史料歸檔：SDD-FSM context/budget 計量表誤差與 ESCALATION 誤觸（沿革原文）

> 本檔是 `docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md`（下稱「主證據檔」）
> 的**史料接收端**——第七輪 Dev-D8 收尾窗口拆出（2026-09-12）。主證據檔動工前已 261,145 bytes，
> 逼近 `tools/check_defect_log_crossref.py::oversize_problems()` 的 262,144 bytes 治理文件體積硬線
> （該硬線＝ Read 工具單次讀取上限，非武斷政策，見主證據檔對 `_LEDGER_FAIL_BYTES` 的說明），
> 若再疊加第七輪追加 A／B 兩節新內容會直接撞線，故把**已凍結、不再變動的純史料節**（各支
> 程式檔/測試檔在某次修復前的原始逐字內容、以及前幾輪「史料搬遷」批次的逐字保全）搬到本檔，
> 主證據檔原位置只留同名標題＋一行指標。
>
> **與主證據檔的關係**：本檔不是獨立故事，是主證據檔的**延伸儲存**——章節標題與主證據檔
> 逐字相同（`tools/tests/` 與 `.claude/hooks/` 內多處指標行寫的正是這些標題，例如
> 「證據檔〈第七輪 史料搬遷（Dev-Trim8）〉」），讀者從主證據檔的「全文移至本檔同名節」
> 指標跳轉過來即可對上正確章節。內容只增不改：日後新一輪若再產生「已凍結的純史料節」，
> 一律比照本輪做法追加到本檔（或體積逼近硬線時再拆 `_Lore_2.md`），不得回頭改動既有章節
> 的逐字內容——那會讓上述指標行失真。
>
> 已現查 `tools/lib/governance_docs.py`／`tools/check_defect_log_crossref.py`：本檔檔名符合
> `_GOVERNANCE_DOC_GLOBS`（`CrossPlatform_*.md`）命名慣例，`unregistered_governance_docs()`
> 會要求登記；`oversize_problems()` 的 262,144 bytes 硬線對所有已登記治理文件一視同仁地適用，
> 同樣綁在本檔上——已登記進 `_GOVERNANCE_DOCS`（見該檔 DEF-200-275 姊妹檔登記處）。本檔本輪
> 移入內容約 115KB，遠低於硬線，暫不需要再拆 `_Lore_2.md`。

## 模組頂端 docstring（原文，D21 前）

```
"""PostToolUse 守衛：Claude Code session 的 context 水位觀測者（本 repo 首見）。

WHY
---
掌舵者連續多輪指名要兩件事：「注意上下文是否超出 90%，進行 /compact，不要爆」與
「注意 Token 限制，適當進行排程再喚醒繼續處理」。四處實查（哪四處、當時各量到什麼，
逐字保全於 `docs/06_quality/CrossPlatform_R91_Scan_Findings.md` §A-1；R91 搬出，理由是
其中的 `claude --version` 讀數已隨版本過期，而過期的量測值住在契約文件裡會被當成常數）
的結論只剩兩句仍在約束今天的行為：**沒有任何既有 hook 在看 context 水位**，以及
**harness 自己的 autocompact 預設開啟**（姿態現查 `--check-autocompact`，見下一節）。

🔴 因此本檔的角色被明確收斂（別讓一個東西假裝能做兩件事）
--------------------------------------------------------
「不要爆」這件事**主要由 harness 的 autocompact 做**，本檔做不到——hook 不能執行
`/compact`，模型也不能自己打 slash 指令。本檔是那條線的**第二道**：
  ① 把「現在幾 %」變成看得見的數字（harness 的 autocompact 不告訴你水位）；
  ② 在 ≥94% 時**真的擋下展開型工具**（見下方〈PreToolUse 阻斷模式〉）——因為
     autocompact 觸發時會丟掉舊訊息，而「丟掉什麼」不由使用者決定；在那之前把
     戰場收斂掉，才是掌舵者要的「不要爆」。
  ③ 產出「可重啟點任務書」骨架，供 token 用完後 `claude -r` 續跑。
harness 那一半的姿態是**可現查的**：`python tools/session_resume_planner.py
--check-autocompact`（autocompact 被關掉時 rc=1）。

🔴 與 SDD `context_ledger` 的分工邊界（**先查過再寫，本檔不是重複造輪子**）
------------------------------------------------------------------------
repo 內確實已有一套帶 90% 門檻的 context 機制（SDD 各版目錄的 `context_ledger_pre/post`，
經 `sdd_hook_router.py` 橋接在根註冊面上）。**它不該被廢、也不該被改**（數十個版目錄、
Copy-on-Evolve 凍結、FSM 有依賴）。本檔與它**量的不是同一個東西**，三點逐項實查過——
估算 vs 實測（ledger 的分子只看 `tool_input`，看不到工具輸出／subagent 回傳／對話本身）／
生效條件不相交（ledger 以 `SDD_ACTIVE_VERSION` 為守衛，純根 session 一行都不跑）／
分母不同（Stage 預算 vs context window）。逐條實查數字與 ledger 的常數表逐字保全於
`docs/06_quality/CrossPlatform_R91_Scan_Findings.md` §A-4（R91 搬出：那是另一支檔的實作
細節，抄在這裡就是同一份知識的第二個家，而只有這一份會過期）。

🔴 這個分工論證的**洞**，照實寫（不粉飾）
------------------------------------------
`SDD_ACTIVE_VERSION` 有設時兩者同時活著，而**兩邊都有一條 90% 線**、分子分母都不同 ⇒
同一時刻兩個百分比會不一樣。處置是**標示而非收編**：每一則訊息都印 `MEASURE_LABEL`；
不讀也不寫 ledger 的檔案（耦合會讓凍結版被拖下水）；不因它存在而讓路。
**未解的那一半**：兩者同時觸發時使用者會連拿兩則語氣相近的告警。本檔不試圖去重
（去重需要跨全部凍結版的協議），僅以標籤讓它們可分辨——已知且已接受的限制，不是漏看。

而「純文件約束對當下的模型零攔阻力」在本 repo 已被實證兩次（`block_bash_on_windows.py`
與 `lint_powershell_command.py` 的立案量測，逐字見 `CrossPlatform_R91_Scan_Findings.md`
§A-2）。水位這件事同型且更嚴重——CLAUDE.md 由 session **開場**載入，而「現在幾 % 了」
是每回合都在變的量，靠模型主動想起來去算它，正是決策負荷第一個擠掉的東西。
```
（其餘〈量測面〉〈context window 判定〉〈行為契約〉〈PreToolUse 阻斷模式〉〈相依規則〉
〈R82／Q2-02 職責邊界〉〈回歸鎖〉段落 D21 後仍原文保留在檔內，未搬出，此處不重複。）

## 〈行為契約〉〈PreToolUse 阻斷模式〉〈相依規則〉〈R82／Q2-02 職責邊界〉原文（D21 前）

```
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
· `< 84%` → exit 0 且**完全靜默**（每次工具呼叫都出聲的守衛會被關掉）。
  🔴 R92 掌舵者裁決：閾值 75／90 → **84／94**，理由見 `WARN_RATIO` 旁的 WHY
  （與額度尺 85／95 刻意錯開；84 在機械 autocompact 點之前、94 是它的失效警報）。
· `>= 84%` → stderr 一行 ＋ **同一段文字送進模型 context**（stdout 的
  `hookSpecificOutput`，發射口＝`platform_utils.emit_to_model`），exit 0。
  🔴 R91 立案：exit 0 下 stderr **不進模型 context**（官方契約：PostToolUse 只有 exit 2
  才回饋 stderr）⇒ 這一整帶（75~90%）模型結構上收不到任何訊號，本輪實測 1h49m／45 turns
  零訊號。stderr 保留不動（人與 log 的可見面），新增的是模型那一半——形態與
  `quota_gate.note_degraded()` 逐字同構（那是本通道在 production 的第一個消費者）。
  逃生口 `AUTOSDD_CONTEXT_SIGNAL_OFF` 只關這半條（退回舊的純 stderr），刻意不與
  `AUTOSDD_CONTEXT_GUARD_OFF`／`AUTOSDD_SENTINEL_OFF` 共用。
  🔴 **這一格說什麼，取決於額度那把尺**（`quota_gate.draining()`，零網路、只讀快取）：
  PRD `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §4.3 的壓縮觸發
  是**三個 AND**，本 hook 原本只實作了第一條（`K_ctx ≥ 75`）。PRD §0 第 1 條把「額度高時
  觸發 `/compact`」列為**阻斷級**（§2：壓縮要模型讀完整段對話再產摘要 ⇒ 顯著推升 U5h）。
  這個缺陷在 R91 之前是**良性的，正因為它壞著**——沒有人聽那則訊息；換上模型通道會讓它
  真的被執行 ⇒ 分流與換通道必須是**同一個** commit，見 `warn_message` 的 WHY。
· `>= 94%` → stderr 強制指引（含 %、used/window 實數、下一步）＋ 呼叫
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

  · 只在 `>= 94%` 且 **window 不是保守下界猜測**時擋（`may_block()`）。分母是猜的
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
「排程器裡三支哨兵，兩支屬於活 5 秒／12 秒的 session」）。額度尺整條住 `quota_gate.py`，本檔對
它只有兩件事：①`main()` 在五道 context 早退**之前**呼叫它一次（撞額度那刻 context 水位
可能只有 ~18%，掛在早退之後的分支一次都不會被執行——那是 SA-B1 判過的死碼）；
②把它需要的四個 hook 端能力注入進去（阻斷名單／閂鎖讀寫／任務書／喚醒武裝）。
兩把尺不共用早退條件、也不共用模組，就是那個設計。既有架構鎖
`test_quota_is_not_wired_into_the_context_blocking_path` 的射程零改變且更容易成立。
```

## `_NEXT_STEP` 上方註解、`spawn_sentinel`／`arm_sentinel`／`spawn_sentinel_gc` 原文（D21 前）

```
#: 84% 那一格的**下一步**，依額度相對 PRD `DRAIN_PERCENT` 的位置三分（`quota_gate.draining()`）。
#:
#: 🔴 立案（R91，PRD 前置條件）：PRD §4.3 的壓縮觸發是**三個 AND**——
#: `K_ctx ≥ CONTEXT_COMPACT_PERCENT`（R92＝84） ∧ `U5h + COMPACT_COST_BUDGET_PP ≤ DRAIN_PERCENT` ∧
#: `距上次壓縮 ≥ COMPACT_MIN_INTERVAL_SECONDS`——而本 hook 原本只實作了第一條，於是它在額度高位照樣
#: 喊 `/compact`。PRD §0 第 1 條把那件事列為 **🔴 阻斷級**，理由在 §2「關鍵釐清」：壓縮
#: 本身要模型讀完整段對話並產生摘要 ⇒ **會顯著推升 U5h**，高位壓縮是反向操作。
#: 本輪之前這個缺陷是**良性的，正因為它壞著**（訊息走沒有讀者的 stderr）；一旦換上模型
#: 通道，它就會**真的被執行** ⇒ 補這一條與換通道必須同一個 commit，否則等於啟動一個
#: 休眠的阻斷級違反。第三條 AND（距上次壓縮的間隔）本 hook 量不到，由「同一門檻本
#: session 只喊一次」的閂鎖近似——**誠實劃界：那是 per (tier, window)，不是 per 時間間隔**。
#: 🔴 第二條 AND 的 3pp 邊際（PRD §6 `COMPACT_COST_BUDGET_PP`）已由 `quota_gate.draining()`
#: 實作（DEF-200-137）：五小時軸 `pct + 邊際 > DRAIN` 亦回 `"yes"`，`(82, 85]` 帶不再勸壓縮。
#: `"unknown"` 不折進 `"no"`：PRD §0 第 6 條明定遙測失效方向為 fail-safe，而「證不出
#: 第二個 AND 成立」與「已證明它成立」是兩件事（同本檔通篇「量不到 ≠ 量到零」的紀律）。

# ───────────────────────── 預防性哨兵的**觸發層**（R79 補洞包；R82／HELM-02 改觸發時機）
# 🔴 SessionStart 只**清閂鎖**（見 `arm_sentinel`），真正註冊延後到 PostToolUse 且要通過
# `tools/lib/sentinel_lifecycle.should_arm()`（回合數＋存活跨度雙門檻）——判準不能寫在
# SessionStart 那一刻，逐字稿那時往往還不存在。為何非預防性不可、三個刻意取捨（detached
# 子行程／逐字稿不存在也照樣武裝／一切例外吞掉）逐字保全於
# `CrossPlatform_R91_Scan_Findings.md` §I-12；立案量測見同檔 §A-6。
def spawn_sentinel(transcript_raw: str, out: str, log: object = None) -> bool:
    """Detached 起 planner 的 `--arm-sentinel`；回「有沒有真的 spawn 出去」。

    🔴 R82／Q2-02 的減法：SessionStart 武裝與額度 95% 喚醒武裝此前是**兩份逐字相同的
    `Popen`**（同一支 planner、同一組旗標、同一個 `creationflags`），差別只有「要不要寫
    boot log」。兩份各自演化的代價已經看得到：R80 修「`DETACHED_PROCESS` 讓視窗回來」
    那一次只改了其中一份。收成一份之後那個漂移在結構上不存在。
    """
    ...
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


def arm_sentinel(payload: dict) -> None:
    """SessionStart：**不再直接武裝**，只把上一輪的武裝閂鎖清掉並留一行痕跡。

    🔴 為什麼還要清閂鎖（不是「什麼都不做就好」）：`claude -r` 續接一個已經下班（6 小時
    閒置自我解除）的 session 時，閂鎖若留著就再也不會重新武裝＝續航被靜默弄丟。清掉之後
    下一次工具呼叫會重新評估，而那時逐字稿早就過門檻 ⇒ 立刻補上。
    boot log 保留：它是「SessionStart 有沒有被叫到」唯一的痕跡，而本輪正是靠它才發現
    有四支短命 session 根本沒觸發過這支 hook（沒有 boot log）。
    """

# 🔴 R84／C3-P4b：`sentinel_lifecycle.gc()` 此前**零自動呼叫端**，殘骸哨兵每 15 分鐘
# 照樣醒來（立案實測全文搬至 docs/06_quality/CrossPlatform_Guard_Line_History.md
# 〈context_budget_guard 立案史彙整〉節）；呼叫點選在 SessionStart＝「後來的人開工」
# 那一刻，也是本函式已經在清閂鎖的地方（同一族的清理，不另開第二個時機）。
#
# 三個刻意的取捨，與 `spawn_sentinel` 逐條同構（同一族的風險，同一組處置）：
#  ① **detached 子行程**（`gc()` 要外呼排程器列舉，同步做＝每次開 session 先卡幾秒）；
#  ② **`keep=(當前 sid,)`**（自己的哨兵不能被自己收掉；`gc()` 內另有一層保護，兩層獨立）；
#  ③ **一切例外吞掉**（P0：hook 誤觸鎖死所有工具；回收失敗最多殘骸多留一輪，不可變故障源）。
def spawn_sentinel_gc(keep_sid: str) -> bool:
    ...
```

## `main()` 內 R83 相關大段註解原文（D22 前）

```
        # 🔴 R83：額度軸只在**我們真的推理過的那兩個事件**上動作。少了這一格，接電會順手
        # 把「事件名讀不出來」（壞 payload、未來新增的事件）也當成觀測點——本輪注入實測：
        # 一份沒有 `hook_event_name` 的 payload 會走完整條額度判讀並出聲，而那類 payload
        # 依本檔既有契約應該是「量測暫時不可得 ⇒ 靜默 rc=0」。射程要靠白名單而不是靠
        # 「不是 PreToolUse 就當 PostToolUse」，後者是預設開啟、方向錯的。
        measuring = event in ("PreToolUse", "PostToolUse")
        # 🔴 額度那把尺**必須在這裡**求值，不能往下擺（SA-B1 判過的死碼）。下面五道早退
        # 全是 context 語意，而 `tier_of()` 在低於 WARN_RATIO 時一律回 `None` ⇒ 撞額度那一刻
        # （實測水位只有 ~18~20%）任何掛在 `block_verdict()` 裡的 quota 分支都到不了。
        # 兩把尺不共用早退條件，這一行的位置就是那個設計。
        # 🔴 R83／接電：`blocking and` 這個前綴拿掉了，`event` 改為傳進去。立案是量出來的
        # ——舊條件讓額度那把尺**只在「我要扇出」那一刻**被問一次，而 R83 實測配額 5%→90%
        # 的整段，主 session 派完最後一波之後再也沒呼叫任何扇出型工具（後續全是全樹跑、
        # agent 回傳、大量讀檔）⇒ 本閘從頭到尾一次都沒被叫到。燒額度的是「我自己在做事」
        # 那條路，而 PostToolUse 的 matcher（`Read|Task|Grep|Glob|…|Bash|PowerShell`）
        # **本來就覆蓋**那條路 ⇒ `settings.json` 一個字都不用改，缺的只有這裡的條件與參數。
        # 射程的第二半在 `quota_gate()` 內（PostToolUse 不記派發帳、不擋節流帶），兩邊要一起讀。

            # 🔴 R83／Δ13：**接電引入的新缺陷，必須在同一個 commit 處理。** halt 帶在
            # PostToolUse 會**每一次**回 2 ⇒ 本 hook 在這裡提早 return ⇒ 下面那個
            # `arm_when_earned()` 在整個 halt 期間（一直到 reset）一次都不會執行，
            # context 續航哨兵靜默失去所有武裝機會。而額度那層的喚醒武裝只在 halt 閂鎖
            # **第一次**觸發時試一次、失敗不重試（見 `quota_gate` 的 D2 重排）⇒ 兩層都沒了。
            # 兩層續航是不同的東西（一次性 reset 喚醒 vs 900s 巡邏），不得因為額度那層
            # 說了話就把 context 那層吃掉。`arm_when_earned` 自身有閂鎖與 fail-open。
```

### 未做事項（另案；含掌舵者「誠實劃界 ==> 這個我要如何解決」四項的解法）

1. **Models API 種子值（D26）——需憑證，本輪不可自動化。** `known_model_windows.json` 仍 `refreshed_at=null`（seeded 2026-06-24）。SA 以 claude-api skill 查證：SDK `Anthropic()` 零參數建構子的憑證鏈＝`ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → `ant auth login` profile → …，**不含** Claude Code 自身存在 macOS Keychain 的 OAuth 憑證（兩套憑證體系）[他包回報]。掌舵者照做即可（在 monorepo 根）：
   ```bash
   source .venv/bin/activate && uv pip install anthropic
   export ANTHROPIC_API_KEY=sk-ant-...        # console.anthropic.com → API Keys；要持久化再寫 ~/.zshrc
   cd AISDLC_SDD/AISDLC_SDD_v0.30 && python -m tools.fsm_runtime.refresh_known_model_windows
   git diff -- tools/fsm_runtime/data/known_model_windows.json   # rc 0=已刷新寫檔；2=SDK 未裝；3=API 失敗（無憑證／離線）；4=SDK 太舊；非 0 一律不寫檔
   ```
   刷新後若 `claude-fable-5-1` 等值有變，D14／D21 兩層收斂會自動吃到新值（hook 路徑只讀表、永不打網路）。
2. **Windows 真機驗證——需一台 Windows 機器，mac 上結構性做不到。** 本輪與前幾輪所有修法皆為純函式／跨平台碼，理論一致；但 exec form 載具（`pythonw.exe`）、schtasks 憑證、D22 的 O_EXCL 標記檔在 NTFS、孤兒 `.part.*` 清理的 `psutil` 分支（AISDLC_SDD 未宣告該依賴 ⇒ 實質 no-op）都只在 Windows 上看得到。解法：push 後看 `windows-compat-ci` 結論（`gh run list --workflow=windows-compat-ci.yml --limit 3`），並在有 Windows 機器時跑 `powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows_smoke_local.ps1` 與根 CLAUDE.md〈hook 載具〉的正面現查兩條。
3. **DEF-200-279——本輪以 D18＋D19 收斂（session 分桶＋PENDING 持有者範圔），不是原列「hook 串接 `load_track_state`／`track_id`」那條路。** Architect 判：天真整份拆 track 會讓 R-9.1 重試預算／R-9.5 ESCALATION 斷路器失效（治理倒退）；真正要「刻意並行多條 feature track」的情境，才走 `FSMRuntime.bootstrap(track_id=...)` 接線既有 `state_loader.load_track_state`（`fleet_orchestrator.TrackRegistry` 語意對齊）——**另案**，需先寫範圍界定 mini-ADR（哪些狀態留專案級：`current_state`／`retry_history`／ESCALATION／DONE；哪些下放：整個 `auto_compact_state`）。
4. **DEF-200-280——本輪 D20 兩層皆修**（根層 + v0.30）。殘留：`test_check_hooks_liveness.py` 的 `_REGISTRATION_BASELINE` floor 表未回填 Agent／Workflow（floor-only 棘輪本就允許落後，同 R80 context_budget_guard 列慣例）。
5. `endurance_env.trace_dir()` 在「宣稱唯讀」的路徑仍會 mkdir（Dev-C 只在 `session_resume_planner.py` 內用 `_halt_marker_probe_path()` 繞開）；其它呼叫 `read_halt_marker()`／`trace_dir()` 的唯讀路徑同型風險仍在——建議在 `endurance_env.py` 補「peek，不建目錄」介面。
6. LOC 餘裕：`tools/lib/quota_gate.py` 499/500、`tools/session_resume_planner.py` 750/750——下一輪要動這兩檔先量，不得假設有餘裕。
7. SA-04 只在 cap_exceeded 分支加 `numerator` 鍵；泛用 `save_abort_report()` 其它 category 是否加註需逐一核實欄位語意（Dev-A 刻意不做，避免對不含 token 欄位的 category 講假話）。
8. `SDD_CONTEXT_GOVERNOR.md` 無 ESCALATION 溯源／per-stage cap 可掛載段落（D17／D18 語意未進該檔）；是否補一段跨引用 `SDD_ESCALATION_PROTOCOL.md`／R-9.2 yaml 另案。
9. `TOKEN_BUDGET_CRITICAL` 狀態去留（hook 已不進入、無轉入邊；本輪只把它納入 recovery_hint 訊息一致性）、`AUTO_COMPACT_PENDING` 目標集缺 `INIT` 補邊需碰 TLA——沿第五輪未做事項。
10. P2 的「模型行為層」：hook 已把真實數字寫進 additionalContext／deny reason、Stop hook D15＋D24 對無佐證的「被擋」宣稱出聲（永不阻斷）；「模型是否真的據以行動」結構上無法被 hook 保證（Architect 誠實劃界），只能靠根 CLAUDE.md〈現查指令速查表〉＋事後量測器 `tools/probe/audit_session.py`。

### 修後複審（第一次；Architect／SA／SD／QA 皆 Sonnet 5、唯讀）

| | Architect | SA | SD | QA |
|---|---|---|---|---|
| 主責裁決 | D17 **DEVIATES**／D19 ✓／D20 ✓ | D21 DEVIATES（非阻斷）／D25 **DEVIATES**／SA-04 ✓ | D18 ✓／D19 ✓／D22 ✓／D23 ✓／D24 ✓ | D17～D25 全 ✓（實跑面） |
| P1／P2／P3 | PARTIAL／—／— | —／—／**FIXED** | PARTIAL／—／— | PARTIAL／PARTIAL／PARTIAL |
| overall | REJECT | REJECT | **APPROVE** | REJECT |

阻斷發現三筆（全數在同一輪修掉，見下〈複審修復波〉）：
- **ARCH-R6-01（P1）**：D17 的 provenance 只覆蓋 `record_escalation()`；fsm_runtime.py 另有 4 個函式直呼 `self.transition("ESCALATION")`（`exit_learning_commit` 兩分支／`exit_trajectory_predicted` abort_early／`record_dispatch_rejection`／`exit_autoclaude_delegated` failed），既不寫 provenance 也不 append history ⇒ 新 ESCALATION 會**自信地印出上一次已解除事件的舊溯源**（Architect 合成重現：舊 session 的 TOKEN_BUDGET_CRITICAL 原因被套到 dispatch 拒絕觸發的新 ESCALATION 上，連 `--reason` 都帶錯）。比 D17 前「模糊但不誤導」更糟。[他包回報]
- **SA-F2（P2）**：D25 新寫的 step_4 else 分支門檻寫 ≥0.90 比照 owner 限制；SA 親跑探針：非 owner 92% **完全放行**（只 WARN）、96% 才限制 ⇒ 程式門檻是 CRIT 0.95。Dev-D 自陳依裁決文字寫、未親讀程式碼——複審任務書點名的風險正中。[他包回報]
- **QA-R6-01（P1）**：主控補立的 DEF-200-283 帳本列 1481 bytes > `ROW_MAX_BYTES=700`，讓 `test_check_defect_log_crossref` 多 4 紅（超標列 37>36、超標總量 20808>20027）。主控收尾縮至 677 bytes 後 `Ran 278 tests OK`；超標列 36/36、總量 20027/20027 恰回基線。

非阻斷發現（登記，見〈未做事項〉補列）：SA-F1（D21 六種 fail-open 路徑零 stderr，裁決文字要求一行）；SA-F3（hard_stop 回落敘述「<90%」與程式兩種真實門檻 <85%（PENDING 內，`WARN_RATIO`）／<95%（trigger 被壓抑）皆不符——**第四／五輪既有殘留**，第五輪 SA 曾誤判已同步）；SD-RR-01（`state_loader.save_state()` 併發 `.bak` 輪替可拋 FileNotFoundError，既有 try/except 已吞）；SD-RR-02（Dev-A 回報稱 chaos 舊債「仍紅」，但主控已在其收工後另派單點補修轉綠——回報時序差，非矛盾）；QA-R6-02（PENDING／CRIT 下 Bash 一律放行，與「只准 compact 相關操作」措辭字面不完全對應——第四輪 QA-07 既有設計）。

四方 `git status --short` 皆與開工時逐字相同（零污染）。QA P3 判 PARTIAL 的唯一理由＝subagent 結構上不能呼叫互動式 `/context`（三路徑數字仍逐位元組一致：本 session 當時 `used=343,214／window=967,000／35.5%`）——由掌舵者在收尾回覆後親自對照一次 `/context` 即可關閉。

### 複審修復波（Dev-A2／Dev-D2，皆 Sonnet 5；根層 context_budget_guard 擋下 Workflow 後改逐個派 Agent）

**Dev-A2（ARCH-R6-01）** [他包回報]
- 座標訂正：「唯一寫入函式」宣稱住 `state_loader.py` 的 `FSMState.record_escalation()` 註解（約 L261-266），非 Architect 所寫的 `fsm_runtime.py`；已在正確檔案改為真話（列出現在全部 12 個生產落點，並註明 `transition()` 事後重寫 `decision_trace.from` 的既有副作用）。
- 寫入面：4 個繞過站點改為先 `self.state.record_escalation(reason, rule_id=…, source=…)` 再既有 `self.transition(...)`（保留原轉態行為）：`record_dispatch_rejection`（R-9.19.3／`cost_gate_escalation`）、`exit_trajectory_predicted` abort_early（R-9.15.2／`trajectory_predicted_abort_early`）、`exit_learning_commit` meta_halt（R-9.24.1／R-9.24.2 依 ChurnBounded／GraduationRatchet 動態選／`learning_commit_meta_halt`）、`exit_learning_commit` 人工 rejected（`unknown`／`learning_review_rejected`）、`exit_autoclaude_delegated` failed（`unknown`／`autoclaude_delegated_failed`）。`grep -n 'transition("ESCALATION' fsm_runtime.py` 程式碼零殘留（僅 1 筆說明性註解，主控親查亦為 0）。
- 讀取面：`recovery_hint.py` 新增 `_parse_iso()`／`_entered_escalation_at()`（decision_trace 最後一筆 `to=="ESCALATION"` 時間戳，量不到退回 state 檔 mtime）與 `_STALE_PROVENANCE_GRACE_SECONDS=5`（吸收 record_escalation→transition 同呼叫跨秒）；provenance 早於本次轉入超過容錯窗 ⇒ 印「溯源不可信：現有溯源屬於較早、已解除的事件…」，恢復指令 `--reason` 改通用措辭不帶舊原因。
- 新測試檔 `tools/fsm_runtime/tests/test_escalation_provenance_r6.py`（321 行、11 案：Architect 重現改寫／兩形態靜態鎖／4 函式 provenance 斷言／陳舊防呆正反案）。紅（暫時 revert）`9 failed, 2 passed in 0.29s` → 綠 `11 passed in 0.26s`。
- 收工：`1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 44.91s` rc=0；chaos `34 passed, 1915 deselected in 14.58s` rc=0；TLA／MD sync `10 passed, 1 skipped` rc=0；`transition_rules.py`／`formal/` diff 為空；`governance/` 零 diff。

**Dev-D2（SA-F2／SA-F3／SA-F1）** [他包回報]
- 改前**親跑** SA 探針核實門檻：非 owner 92% 只 WARN 完全放行、96% 才 deny（`CRIT_RATIO=0.95`）；96%→PENDING 後降到 88% 仍 deny、82%（<85% `WARN_RATIO`）才釋放。
- SA-F2：`SDD_CONTEXT_GOVERNOR.md` step_4 else 分支拆成 allow（<0.95 僅 WARN 通知，不受 owner 限制）／deny（≥0.95 比照 owner「只准 compact 工具」），加註探針依據。SA-F3：L70 改成兩種真實門檻並寫入常數名（`context_window.WARN_RATIO`／`CRIT_RATIO`）；L80 摘要表同句由主控訂正。全檔 grep `v0.01`／`cumulative_ratio`／「≥0.90 時比照 owner」／「回落 < 90%」零操作性殘留。
- SA-F1：`context_budget_guard.py` 六種查表 fail-open 路徑各一行 `sys.stderr.write`（含失效種類與路徑；「有子專案無版本目錄」與「LATEST 解析失敗」以 `"找不到任何版本目錄" in str(exc)` 分流）；LOC 淨增 11 行撞 `SPECIAL_FILES` 1089 上限 ⇒ 壓縮 `known_model_windows_path()` docstring 8→2 行、原文搬 `scratchpad/dev-d2/moved_lore.md`（見下方史料搬遷補記），改後 1089 行恰在上限、`special_violations=[]`。測試：四支 fail-open 案加「stderr 非空且含關鍵字」斷言，紅（剝除 stderr）`FAILED (failures=4)` → 綠 `Ran 16 tests OK`；其中 `test_aisdlc_sdd_present_but_no_version_directories_is_fail_open` 原夾具只建空殼目錄、實際命中的是「LATEST 解析失敗」，已補真 `sdd_version.py` 使其如實重現該失效種類。
- 收工：`test_root_guard_known_model_r145 test_context_budget_guard` `Ran 641 tests in 29.359s OK (skipped=10)` rc=0；md／tla sync `10 passed, 1 skipped` rc=0；ruff `All checks passed!`；`check_loc_budget.py --json` 三欄皆空。

**主控親跑（兩包收工後）**：SDD `1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 44.98s` rc=0；chaos `34 passed, 1915 deselected in 14.80s` rc=0；`governance/` 零 diff；`transition("ESCALATION` 程式碼命中 0；ruff 12 檔 `All checks passed!` rc=0；`check_loc_budget.py --json` `total_violation=False special=[] root_tools=[]`；根層八支相關測試模組 `OK (skipped=15)`。

#### 史料搬遷補記（SA-F1 LOC 抵銷：Dev-D2 自 `known_model_windows_path()` docstring 搬出的原文）

`known_model_windows_path()` / `load_known_model_windows()` 六種查表 fail-open 失效路徑
（無 AISDLC_SDD 子專案／有子專案無版本目錄／LATEST 解析失敗／表檔不存在／JSON 損毀／
JSON 形狀不對）此前全靜默、零 stderr 輸出。修復＝各補一行 `sys.stderr.write(...)`。

任務書要求：只准在查表 fail-open 分支加 stderr 輸出，其它一行不動；若加了 stderr 讓
`AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES["../.claude/hooks/
context_budget_guard.py"] = 1089` 棘輪超標（納管當下 headroom 僅 6 行），把等量 docstring
史料搬到本檔，判準（stderr 邏輯）不砍。

實測：六行 stderr 加上必要的 `if`/`except as exc`/`kind =` 輔助邏輯，讓
`known_model_windows_path()` 淨增 9 行、`load_known_model_windows()` 淨增 2 行，共 +11 行
（1083→1094），超過棘輪（1089）5 行。已把 `known_model_windows_path()` 自己的 docstring
（8 行）壓縮為 2 行（原文逐字保留於下），淨省 6 行，最終 1089 行，剛好持平棘輪、不超標。
除這一段 docstring 之外，本檔其餘既有內容（含另一包 Dev-C 在本輪已對本檔做的其他改動）
一律未觸碰。

## `known_model_windows_path()` docstring 原文（搬出前，逐字保留）

```
    """LATEST 版 `known_model_windows.json` 的路徑；解析不到／檔不存在一律 `None`（D21 fail-open）。

    唯一真相源＝`tools/lib/sdd_latest.py`（`resolve_latest_root`，內部再呼叫 `sdd_version.py`
    判定 LATEST）。四種失效都 fail-open、不拋例外：`sdd_latest` 不可達／本機沒有
    `AISDLC_SDD/` 子專案（多數純 AutoClaude 部署的常態，不是錯誤）／LATEST 解析失敗
    （`AssertionError`，`sdd_latest.resolve_latest_root` 的既有契約）／檔案本身不存在。
    """
```

原地保留的精簡版（語意不變，指向本檔）：

```
    """LATEST 版 `known_model_windows.json` 的路徑；解析不到／檔不存在一律 `None`（D21 fail-open；
    四種失效各印一行 stderr，SA-F1 訂正——唯一真相源與失效分類全文見 moved_lore.md）。"""
```

（附註：SA-F1 finding 原文說「四種失效」是 `known_model_windows_path()` 這一層的既有分類
〔`sdd_latest` 不可達／無 AISDLC_SDD 子專案／LATEST 解析失敗／表檔不存在〕；SA 複審黑箱
測試觀察到的「六種失效路徑」把 `load_known_model_windows()` 的 JSON 損毀／JSON 形狀不對
兩種另計。本次實作對六種皆已補 stderr，其中「有子專案無版本目錄」在 `except Exception as
exc` 分支內以訊息內容 `"找不到任何版本目錄" in str(exc)` 與其餘 LATEST 解析失敗區分。）

### 史料搬遷（Dev-Trim；護欄層行數棘輪抵銷：六支測試檔 docstring 敘述原文逐字保全，−87 行）

> 每則被縮短的 docstring 現為「一句 WHY＋裁決編號＋指針本節」；原文如下（來源檔名＋函式名標於各段）。[他包回報]

不做任何改寫。搬遷理由：行數棘輪（連續三輪淨額為正）觸發，測試碼與判準本身
一行未砍，只搬「背景故事／事故經過／審查往來／重複複述的裁決全文」。

---

## tools/tests/test_wake_chain_halt_r278.py

### class HaltMarkerProbePathDoesNotCreateDirectoriesTest（原 docstring）

```
D23 收尾修復：`planner._halt_marker_probe_path()` 是 `--check`（唯讀契約，見
`test_context_budget_guard.py::PlannerCliTest::test_check_prints_usage_and_writes_
nothing`）用來探測 halt 標記存不存在的入口——它本身**不得**觸發
`endurance_env.trace_dir()` 的 `mkdir(parents=True, exist_ok=True)` 副作用，否則
光是「檢查有沒有標記」就會在從沒人寫過標記的機器上憑空長出 `.autosdd/traces` 目錄。
```

### class HaltedBandLineTest（原 docstring）

```
D23（SD-07；DEF-200-275 第六輪）：`quota_messages.halted_band_line()` 純函式——
本 sid 的 halt 標記未過期時印「halted，reset 於 T」，已過期或沒有標記一律 `None`
（呼叫端落回既有判定）。純函式：不讀任何檔，`halt_marker` 由呼叫端已經
`read_halt_marker(sid)` 取得，本測試不碰磁碟。
```

### class PaceReportShortCircuitsDuringHaltTest（原 docstring）

```
D23（SD-07）：`--pace`（`quota_gate.pace_report()`）在本 sid 的 halt 標記未過期時
必須直接短路回「halted」那一行，**不**進 `pace_state()`——後者在快取不可用時可能
補打一次 `/api/oauth/usage`，而 halt 期間不該再花任何一次 API（INV-H3 的殘餘）。
```

### class RelayProblemsCatchesEmptySessionIdTest（原 docstring）

```
D23（SD-08；DEF-200-275 第六輪）：`relay_problems()` 此前只檢查 `session_id`
這個鍵**存在**，不檢查**非空**——一個值為空字串的狀態塊會通過體檢，而
`_sentinel_tick` 拿它餵 `quota_gate.read_halt_marker(sid)`，該函式對假值 sid
直接靜默回 `None`（退化成 idle-based patrol，不會走到 halt 判定那一支）。
```

### class PrepareLatchIsSessionScopedTest（原 docstring）

```
D22（DEF-200-275 第六輪，SD-04）：`quota_prepare_actions()` 的閂鎖鍵此前不含 sid
（`f"prepare@{kind}@{reset[:16]}"`），與 halt 分支修復前同一種缺陷——`quota_latch_path()`
是 machine-wide 單一檔案，同一 reset 視窗內第二個進 prepare 帶（85~95%）的 session
會被第一個 session 的閂鎖誤擋，拿不到自己的 `write_resume_plan()` 任務書骨架
（不是訊息去重問題，是實質少一份任務書）。比照 `HaltLatchIsSessionScopedTest` 同型重現。
```

### test_two_sessions_in_the_same_prepare_window_both_get_their_own_plan（原 docstring）

```
紅端＝修前第二個 sid 撞進「已閂鎖」分支：`plan_writer` 只被叫一次——第二個
session 的任務書骨架永遠不會被寫出來（DEF-200-278 第二輪 §8 item 1）。
```

---

## tools/tests/test_context_budget_guard.py

### class AtomicLatchStorageTest（原 docstring）

```
D22（DEF-200-275 第六輪，SD-05）：`announced_latches`／`remember_latch` 此前是單一
JSON 檔的「整讀→union→整寫」——兩個行程幾乎同時各自 union 後寫回，後寫的會覆蓋先寫的、
遺失先寫入的那個 key（方向安全：多喊一次，不是漏喊；但不精確）。改成每個 key 一個
`O_CREAT|O_EXCL` 建出來的標記檔後，新增一個 key **結構上不可能**碰到既有 key 的儲存
（各自獨立的檔案）——本組用「後寫入的 key 不改動先寫入那個 key 的檔案」直接證明這一點
（這正是舊版「整寫」會違反、新版天生滿足的性質，比重現時序競態更穩定可重跑）。
```

### test_writing_a_second_key_never_touches_the_first_keys_file（原 docstring）

```
紅端＝舊版「整讀→union→整寫」每次 `remember_latch` 都重寫**同一份**檔案，
於是第一個 key 的儲存（整份 state 檔）必然被第二次呼叫改動；新版兩個 key 各自
獨立檔案，寫第二個絕不會碰到第一個的位元組（mtime／內容皆不變）。
```

### QuotaPrepareBandActuallyPreparesTest 迴圈內新增註解（原文）

```
# D22（SD-05）：閂鎖真正的落點已改成 `guard._latch_marker_dir()` 算出來的
# 目錄（每個 key 一個原子標記檔），不再是 `latch.json` 這個檔本身——只清
# 舊檔名會讓上一輪 subTest 的閂鎖繼續生效，第二個事件被誤判成「已喊過」。
```

---

## tools/tests/test_claim_provenance_r86.py

### class TestTheBlockClaimEvidenceWindowIsRecentTurnsOnly（原 docstring）

```
D24（DEF-200-275 第六輪；SD-06 收斂版）：第五個判準的佐證窗口從『全場不分時間』
收斂為『倒數第二則 role=user 訊息之後』（本回合＋前一回合）。立案見 SD-06：舊窗口讓
本場任何時候出現過一次 `kind=`/`band=`/`cap=` 通知，就對**之後所有**『被擋』宣稱整場
靜音——即使那次通知早已跟這次宣稱無關。這裡驗證『兩回合前』的通知不再能替『這一回合』
的赤裸宣稱背書，同時保留『上一回合／這一回合才提一句』的原始合法情境（不能矯枉過正）。
```

### _user_line 靜態方法（原 docstring）

```
一則**真人打字**的 role=user 訊息（非 tool_result 中繼）——D24 拿它當回合邊界。
```

### _notice_line 靜態方法（原 docstring）

```
`context_budget_guard.py` 額度守衛的 `hook_additional_context` 通知形狀
（SD-06 假紅普查逼出來的真實佐證形態之一，見本檔上方 `BLOCK_EVIDENCE_RE` 旁註）。
```

### test_a_notice_inside_the_previous_round_still_silences_it（原 docstring）

```
對照組：通知落在邊界（倒數第二則）之後時，仍要維持原判準的設計動機——
『先被擋、下一回合才提一句』仍要放行，不能因為收斂窗口而矯枉過正。
```

### test_fewer_than_two_user_turns_falls_back_to_whole_transcript（原 docstring）

```
少於兩則真人訊息（含 0／1 則）時沒有『倒數第二則』可切，退回全場——覆蓋既有
4 筆假紅普查案例的形狀（那些合成語料本來就不含任何 role=user 訊息）。
```

---

## tools/tests/test_check_hooks_liveness.py

### test_root_sdd_hook_router_pretooluse_matcher_includes_agent_and_workflow（原 docstring）

```
D20（DEF-200-280／F-ARCH-02）正面斷言：Agent／Workflow 呼叫必須觸發 SDD FSM guardrail。

`_REGISTRATION_BASELINE` 只是下限（floor-only 棘輪）——widening 測試只保證加寬
matcher『不會轉紅』，不保證『真的加了』：`registration_shrink_problems()` 對
`("PreToolUse", ".claude/hooks/sdd_hook_router.py")` 這一列釘的下限本身就沒有
Agent／Workflow（見 `context_budget_guard.py` 那列同樣只釘了加寬前的子集，R80 之後
matcher 本體已加寬但基準表從未回填——這是既有、刻意的慣例，不是本測試要修的東西）。
F-ARCH-02 實測指出：在 monorepo 根開 `claude` 是本任務背景描述的實際工作流，此時只有
根層 `.claude/settings.json` 生效；若那一條轉發 sdd_hook_router→context_ledger_pre 的
PreToolUse matcher 缺 Agent|Workflow，子代理（Agent）／批次編排（Workflow）呼叫會完全
繞過 SDD FSM guardrail（ESCALATION／AUTO_COMPACT_PENDING 等狀態形同虛設）——這是『該擋
沒擋』的鏡像問題（DEF-200-279／SD-01 是『不該擋卻擋』，本項相反）。本測試直接讀取現實
settings.json 內容做正面斷言，不透過棘輪下限迂迴，避免『floor 沒動、matcher 也沒動』
兩者同時發生時仍被誤判為合格。
```

---

## tools/tests/test_root_guard_known_model_r145.py（新檔，全檔本輪）

### 模組 docstring（原文）

```
D21（DEF-200-275 第六輪，SD-09）：根層 `context_budget_guard.py` 補查表收斂階。

WHY（引用 D21，見 scratchpad/dev-c/../r6_decisions.md）
---------------------------------------------------------
第五輪複審 SD-09／QA P2／Architect P2 三方一致指出：SDD 子專案的 `context_window.py`
已有 `_converge_pinned_window()`（D14）把「指定值」與「觀測到的 model 查表值」收斂，
但**根層**的姊妹守衛 `context_budget_guard.py` 完全沒有這一階——遇到指定值與實跑
模型的真實視窗不符時，算出來的 ratio 依然可能與 `/context` 差好幾倍。這支測試釘住
D21 的修法：資料只有一個家（`$V/tools/fsm_runtime/data/known_model_windows.json`，
經 `tools/lib/sdd_latest.py` 解析 LATEST 路徑讀取），根層自己不存第二份查表
（否決「根層另存一份」——DEF-101-778 判例：兩個家只會改一個）；收斂語意與 SDD
`_converge_pinned_window` 逐項相同（只在查表值嚴格小於指定值時收斂）；`--check`
的 window 行必須印得出「有沒有真的查過表」的證據，不論收不收斂（根層此前連查過表
這件事本身都看不見，是 SD-09 殘餘的核心）。

測試鏡射 SDD `test_context_window.py::ConvergePinnedToKnownModelTests` 的三階案例
（haiku 收斂／fable 不收斂但保留釘值／`SDD_MAX_CONTEXT` 無此概念，改測「無 known_models
表」的 fail-open 案）＋「表缺檔 fail-open」案（`known_model_windows_path()` 解析不到）。
```

### test_no_aisdlc_sdd_directory_is_fail_open 內註解（原文）

```
# SA-F1（第六輪複審）訂正：此前六種查表 fail-open 失效路徑全靜默、零 stderr——
# 「根層此前連查過表這件事本身都看不見」的 SD-09 殘餘。fail-open 方向不變，但
# 不可再靜默。
```

### test_aisdlc_sdd_present_but_no_version_directories_is_fail_open 內註解（原文）

```
# SA-F1：一個只有空殼、沒有 `scripts/sdd_version.py` 的 AISDLC_SDD 目錄會讓
# subprocess 連腳本都找不到（那是另一種「LATEST 解析失敗」，不是本測試要的
# 「有子專案無版本目錄」）——要真的重現後者，必須放進真的 sdd_version.py，
# 讓它實際跑起來、自己正確回報「找不到任何版本目錄」。
```

以及：

```
# SA-F1：同上——「有子專案無版本目錄」與「無子專案」是不同的失效種類，各自
# 印出的 stderr 訊息必須能分辨是哪一種（不能共用同一句籠統訊息）。
```

### test_corrupt_json_is_fail_open_not_a_crash 內註解（原文）

```
# SA-F1：JSON 損毀與「JSON 形狀不對」是 load_known_model_windows() 自己的兩種
# fail-open（`known_model_windows_path()` 那四種以外的另外兩種）。
```

### class WindowEvidenceOnlyQueriesTableWhenPinnedTests（原 docstring）

```
D21 效能取捨：沒有任何 pin 時 `window_evidence()` 不該去解析 LATEST（`_converge_
pinned_window` 用不到它）——省一次 `sdd_latest` 的 subprocess 解析。用一個一定會失敗的
`root` 探針間接證明：有 pin 時才會嘗試查表（回傳的 known_models 不含表徵值），沒 pin
時完全不觸碰查表路徑（`known_models=={}` 且不影響其餘證據欄位）。
```

### test_no_pin_at_all_yields_empty_known_models 內註解（原文）

```
# 隔離：本場開發環境本身可能已設 AUTOSDD_CONTEXT_WINDOW（供人互動時用）——
# 測試若不清乾淨會讀到真實行程環境，「沒有 pin」這個前提就不成立
# （DEF-200-281 同型教訓：夾具沒隔離會讓斷言測到別的東西）。
```

### test_keeps_pinned_when_table_value_is_larger_for_fable（原 docstring）

```
D21 例句：`967,000〔指定值…；查表 claude-fable-5-1=1,000,000 ≥ 指定值，不收斂〕`
——window 不變，但來源說明必須留下「有查過表」的證據（不是靜默沿用舊來源）。
```

### test_no_known_models_table_is_fail_open_and_silent（原 docstring）

```
表缺檔／解析失敗 fail-open：不收斂，且來源說明不留下「查過表」的字樣
（沒有表可查，不能假裝查過）。
```

---

## tools/tests/test_sentinel_tick_e2e_r145.py（新檔，全檔本輪）

### 模組 docstring（原文）

```
D23（DEF-200-275 第六輪，SD-08／OTHER PARTIAL _sentinel_tick 端到端）：構造合法 relay
狀態塊＋halt marker fixture，monkeypatch `_register_and_record` 為零副作用記錄函式，
直接呼叫 `_sentinel_tick(args)`，斷言 halt 標記真的被消費、decision 正確（`arm_reset`／
`probe`）。

WHY
---
既有測試（`test_context_budget_guard.py` 裡一大批 `_sentinel_tick` 呼叫）覆蓋面其實不小，
但都是「純函式邊界」層級（`sentinel_decide()`／`halt_verdict()` 各自獨立驗證）；沒有一支
是「構造一份磁碟上的 halt 標記 → 直接呼叫 `_sentinel_tick(args)` → 斷言它真的讀到、
真的據以決策」的端到端串接（DEF200278 證據檔第二輪 §8 自陳此為未做事項）。本檔補這一段
缺口：不 mock `quota_gate.read_halt_marker`／`halt_verdict`，只 mock 排程／告警的**副作用**
（`_register_and_record`／`_resume_tick`），讓 halt 標記到 decision 這一段是真的跑過的
程式碼，而不是分別驗證兩段純函式後靠推論黏起來。

隔離：`AUTOSDD_TRACE_DIR`（halt 標記落點）＋`tempfile.gettempdir`（`endurance_log_path`
落點）皆指向本測試專屬暫存目錄；`SDD_ENABLE_RULE_FIRE_TELEMETRY`／
`SDD_ENABLE_RULE_CATCH_TELEMETRY` 未涉及（`_sentinel_tick` 不碰 SDD FSM 治理面）。
```

### _transcript 方法（原 docstring）

```
`mtime`＝None 時用「現在」（session 還活著）；給定值時模擬「最後一次活動
落在那個時刻」——`halt_verdict()` 用它判斷 session 是否已在標記之後自行續跑過
（見 `test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick` 的 WHY）。
```

### _write_plan 方法（原 docstring）

```
合法 relay 狀態塊（`relay_problems()` 必須回空清單，否則走自癒分支，
測的就不是「真的消費了 halt 標記」這件事）。
```

### test_unexpired_halt_marker_drives_arm_reset_and_reaches_register（原 docstring）

```
halt 標記的 reset_at 尚未到 ⇒ decision=arm_reset ⇒ `_sentinel_tick` 必須真的
走到 `_register_and_record()`（不是提早在別的分支短路掉）。
```

### test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick（原 docstring）

```
halt 標記的 reset_at 已過 ⇒ decision=probe ⇒ `_sentinel_tick` 必須交棒給
`_resume_tick()`（既有的探測/重排/終態機器），不是自己另開一條路。
```

### test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick 內註解（原文）

```
# 逐字稿最後活動落在 marker_at **之前**（模擬「halt 之後 session 沒有續跑過」，
# 見 `halt_verdict()` 的「活動晚於標記＝標記過期」防呆）——否則會被判成
# 已自行續跑而落回 idle-based patrol，不是本測試要驗的 probe 分支。
```

### 實測（主控親跑；他包數字皆已標 [他包回報]）

```
# SDD 全套（複審修復波後）
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider
1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 44.98s   rc=0
$ ... -m chaos ...
34 passed, 1915 deselected in 14.80s   rc=0
# 治理 yaml 零污染：git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/ → （空）
# 直呼 transition("ESCALATION 程式碼命中：0（僅 1 筆註解）
# chaos 舊債在乾淨 HEAD fda2903 副本（git worktree add --detach）：1 failed in 0.15s ⇒ 確為既有
# ruff（根層 12 檔＋skip_tag_policy＋governance_docs＋guard_bucket_policy）：All checks passed!
# LOC：python AutoClaude/tools/check_loc_budget.py --json → total_violation=False special=[] root_tools=[]
# 帳本鎖：test_check_defect_log_crossref test_defect_id_reference_integrity → Ran 278 tests OK
#   DEF-200-283 列 677 bytes（≤700）；超標列 36/36、超標總量 20027/20027 恰回基線
# 護欄層行數棘輪：python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
#   淨額 97488→98221 (+0 漂移)；python -m unittest test_adr_xplat001_c1c2_lock → Ran 192 tests OK
# 根層全套（首跑，四包收工後）：前置掃描早退 ⇒ 重釘 _TREE_FILE_FLOORS 56→58／62→63（→64）
# 根層全套（第二跑）：Ran 4157 tests in 778.409s FAILED (failures=6)——6 紅皆收尾項：3 支護欄棘輪、
#   round-label R145 超前帳本、DEF-200-283 未立列、E501 存量債 139→141（Dev-C 用 noqa 想略過的兩行）
#   ⇒ 全數由收尾窗口處理（見〈修法逐檔〉收尾窗口段與 R145 Scan_Findings §3）
```

P3 主控開場實測：`used 99,017／window 967,000／10.2%`＝逐字稿最後一筆 usage 手算；QA 修後複審 `343,214／967,000／35.5%`、SA 迷你複審 `425,134／967,000／44.0%`（window 行帶「查表 claude-fable-5-1=1,000,000 ≥ 指定值，不收斂」證據）——三路徑三個時間點皆逐位元組一致。[他包回報]

### 把握程度（誠實劃界）

- **高把握**：D17（含 ARCH-R6-01 補齊 4 落點＋陳舊溯源防呆）、D18、D19、D20 兩層、D22、D23、D24、D25（含 SA-F2／F3 訂正）皆先紅後綠＋修後複審／迷你複審獨立重現核實；FSM 狀態集／邊／TLA 零改動（`transition_rules.py`／`formal/` diff 為空，TLA／MD sync 綠）。
- **中高把握**：D21 根層查表收斂——語意逐項對齊 SDD `_converge_pinned_window`、六種 fail-open 各一行 stderr（SA 迷你複審逐一貼出）；但查表本身仍是 2026-06-24 種子值（D26），收斂到的「真實值」尚未被 Models API 驗證。
- **P1 的殘餘邊界**：ESCALATION **刻意仍擋**新視窗（R-9.5）；本輪解決的是「擋得有沒有溯源、擋得對不對人、非 owner 會不會被牽連、cap 計數會不會張冠李戴」。掌舵者若日後開新視窗仍被擋，訊息會直接印出「由哪個 session 於何時因何規則寫入、本 session 是否觸發者、一行恢復指令」——照做即可。
- **P2 的結構邊界**：hook 已把真實數字寫進 deny reason／SessionStart／Stop hook 出聲；「模型是否真的據以行動」結構上無法被 hook 保證（Architect 誠實劃界）。
- **P3**：subagent 結構上不能呼叫互動式 `/context`；三路徑數字一致，剩最後一步由掌舵者親自對照 `/context` 一次。
- **護欄層記帳**：本輪 +748 分軌申報——回歸鎖軌 392（結案回歸鎖＋本檔記帳，走 `_REGRESSION_LANE_APPROVED_OVERAGE` 唯一一格）、功能軌 356（兩支新判準能力鎖檔，熄滅款(11)[只升不降] 走 `_REPIN_APPROVED_ROUND_OVERAGE` 第三格、MAX_ENTRIES 2→3 可見上修）；prose 分桶 4182→4512。四方記帳複審 SA／SD／QA APPROVE，Architect 以分類寬度 REJECT 後改為現行分法再複核（R145 Scan_Findings §3.1／§3.2）。往後任何一輪的超額照原判準阻擋；下一次淨減法輪應下修 MAX_ENTRIES 並移除失效列。
- **Windows 未真機驗證**（同前幾輪）。

#### 收尾最終親跑（四方記帳複審全 APPROVE、所有編修定案後）

```
$ python tools/run_root_unittests.py
Ran 4157 tests in 790.649s
OK (skipped=46)                                   rc=0
$ cd AISDLC_SDD/AISDLC_SDD_v0.30 && SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q -p no:cacheprovider
1907 passed, 8 skipped, 34 deselected, 14 subtests passed in 46.97s   rc=0
$ ... -m chaos ...
34 passed, 1915 deselected in 15.33s              rc=0
$ python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines | head -1
# 淨額 98236→98236 (+0)
$ git status --short -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/   → （空）
```
護欄層淨額定案 97488→98236（+748＝回歸鎖軌 392＋功能軌 356），四方記帳複審 SA／SD／QA APPROVE、Architect REJECT→修正 392／356 分法→APPROVE（R145 Scan_Findings §3.1／§3.2）。ONBOARDING §7 表② 指紋以樹外乾淨 venv（`onboarding_clean_venv`，Python 3.11.15，`psycopg2` absent）回填。

## 第七輪 史料搬遷（Dev-A7；context_budget_guard.py 原文逐字保全）

D27（修復包 Dev-A7）：四方複審 Architect finding ARCH-A4-01 判定 D21「`window_evidence()`
只在至少一階有指定值時才查表」這個效能捷徑本身就是缺陷根因——沒有釘值的機器上分母因此
少了 SDD `context_window.py` 8 階分母鏈的第⑥階（以 model id 查表），與 SDD 側對同一份
逐字稿算出不同答案（差可達 5 倍）。裁決：推翻 D21，`.claude/hooks/context_budget_guard.py`
無條件補齊 ⑥ 查表階；效能代價改由 `tools/lib/sdd_latest.py` 的
`resolve_latest_root_fast()`（importlib 熱路徑，不起第二個 python 行程）＋
`context_budget_guard.py` 的 per-session 快取檔（`_known_table_cache_path()`，住
`_latch_marker_dir()` 同一目錄）兩層吸收。

`context_budget_guard.py` 受 `AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES`
raw-line 棘輪管（本輪上限 1089，零餘裕）。本輪新增的查表階／per-session 快取／文件同步
需要淨新增的行數，依既有慣例（R91 起同型搬法）用「搬史料」抵銷：把該檔內以下幾段純敘事
的歷史註解／docstring 原文逐字保全於此，檔內只留一行指標。以下逐段列出**修改前的原文**
（來源：本輪 Dev-A7 修改前的 HEAD＝commit e90ee11）：

**① 模組 docstring〈context window 判定〉節，D21 之前只有 5 階（現改為對齊 SDD
8 階分母鏈編號，見檔內〈context window 判定〉）：**

```
🔴 context window 判定（R79 重寫；當時的缺陷實況＝`CrossPlatform_R91_Scan_Findings.md`
§A-3——一句話：分母猜小只是早喊，猜大會讓守衛在真 90% 結構性靜默）
--------------------------------------------------------------------------------
方向是不對稱的：
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
```

**② 模組 docstring〈R82／Q2-02 職責邊界〉節：**

```
🔴 R82／Q2-02：本檔的**職責邊界**——只剩一把尺（context 水位），額度尺整條住
`quota_gate.py`；本檔對它只有兩件事：①`main()` 在 context 早退之前呼叫它一次
（撞額度那刻 context 水位可能只有 ~18%，掛在早退之後的分支一次都到不了）；
②注入四個 hook 端能力（阻斷名單／閂鎖讀寫／任務書／喚醒武裝）。兩把尺不共用早退
條件、也不共用模組（`test_quota_is_not_wired_into_the_context_blocking_path` 釘住）。
```

**③ `sdd_latest` import 旁的 D21 註記：**

```
# D21（SD-09／DEF-200-275 第六輪）：LATEST 版本路徑解析唯一真相源＝`tools/lib/sdd_latest.py`
# （query 查表資料的家＝`$V/tools/fsm_runtime/data/known_model_windows.json`，
# 見 `known_model_windows_path()`）。同一套 fail-open：不可達時本符號為 `None`，
# 查表收斂整條退化成「查不到，不收斂」——與這個階段本身的方向一致（不收斂只是不精確，
# 不是不安全；被否決的作法是在根層另存一份查表，見該函式 docstring）。
```

**④ `_KNOWN_MODEL_WINDOWS_REL` 旁的 D21 註記：**

```
#: D21：查表資料相對 LATEST 版根目錄的路徑（資料只有一個家——SDD 子專案自己那份，
#: 見 `known_model_windows_path()` 的 WHY；D21 否決「根層另存一份」）。
```

**⑤ `window_evidence()` 內的 D21「只在有 pin 才查表」捷徑（本輪推翻的那段本體）：**

```python
    # D21：只在至少一階有指定值時才查表——沒有任何 pin 時 `_converge_pinned_window` 用
    # 不到它（收斂只發生在②③④階），提早跳過能省一次 `sdd_latest` 的 LATEST 解析
    # （內部再呼叫一次 `git`，逐次工具呼叫都付這個代價並不便宜）。
    known_models: dict[str, int] = {}
    if (_positive_int(env_raw) or _positive_int(cc_window_raw)
            or _positive_int(settings_window)):
        known_models = load_known_model_windows(known_model_windows_path())
```

**⑥ `scan_transcript()` docstring 的效能三段省法全文：**

```
    刻意**逐行覆寫 last** 而不是整檔 `json.loads` 後排序：逐字稿是會長到數十 MB
    的 append-only 檔，而本檔每次工具呼叫都會跑一次。三段省法：
      ① 以 `"usage"` 子字串預篩，絕大多數行連 `json.loads` 都不進；
      ② 記憶體 O(1)（只留 last 與 max）；
      ③ 壞行直接跳過——逐字稿常有半截尾行（正在寫入時被讀到），一行壞掉不得
         讓整支守衛崩潰（同 `tools/probe/audit_session.py::iter_records` 的既有判斷）。
    歷來最大值是 window 下界推論的唯一輸入，所以必須整檔看過，不能只看尾巴。
```

**⑦ `latch_key()` docstring 全文：**

```
    """閂鎖鍵＝(門檻, 分母, compact 週期)。

    分母必須進鍵，這是 R79 修的半個缺陷（誤報吃掉真正的那一次）。`epoch` 是
    R92／D3 補的第二個盲區：同一 (tier, window) 內「compact 成功 → 真的再次越線」
    此前不會重新武裝。`epoch`＝`compact_boundary_count()`，同一次 compact 週期內
    不變 ⇒ one-shot 語意零改變；跨過一次真 compact 才前進，鍵才因此不同。
    完整立案敘事見證據檔 §I-3／§I-10。
    """
```

**⑧ `remember_latch()` docstring 全文：**

```
    """把 key 記進去（D22／SD-05：`O_CREAT|O_EXCL` 原子建檔，取代舊版整讀→union→整寫——
    後者兩個行程幾乎同時各自 union 後寫回會遺失先寫入的那個 key，方向安全但不精確；
    每個 key 一個檔天生不衝突，同 key 競爭時輸的那邊 `O_EXCL` 失敗即安靜跳過）。
    寫失敗（含已存在）一律吞掉，不得升級為守衛失敗——最壞情況是下次再喊一次。"""
```

**⑨ `write_resume_plan()` docstring 全文：**

```
    """呼叫 `tools/session_resume_planner.py` 產出任務書骨架；回傳路徑（失敗回空字串）。

    走 subprocess 而不是 import：本檔的零相依契約（見模組 docstring）不允許 import
    repo 內任何模組，而 `tools/` 根本不在 hook 行程的 `sys.path` 上。子行程的
    stdout/stderr 明確宣告 UTF-8（`encoding=`／`errors=`），避免 zh-TW cp950 下
    讀子行程輸出時炸 UnicodeDecodeError。任何失敗一律吞掉——任務書寫不出來時，
    使用者仍該拿到那段強制指引。
    """
```

**⑩ `spawn_sentinel()` 上方的觸發層總覽註記：**

```
# ───────────────────────── 預防性哨兵的**觸發層**（R79 補洞包；R82／HELM-02 改觸發時機；
# SessionStart 只清閂鎖，真正註冊延後到 PostToolUse 且要通過 `sentinel_lifecycle.should_arm()`
# 雙門檻——三個刻意取捨與立案量測全文搬 moved_lore.md／`CrossPlatform_R91_Scan_Findings.md` §I-12）。
```

**⑪ `spawn_sentinel_gc()` 上方的 R84／C3-P4b 註記：**

```
# 🔴 R84／C3-P4b：`sentinel_lifecycle.gc()` 此前零自動呼叫端，殘骸哨兵每 15 分鐘照樣醒來
# （全文搬 moved_lore.md／`CrossPlatform_Guard_Line_History.md`）。三個取捨與 `spawn_sentinel`
# 逐條同構：detached 子行程／`keep=(當前 sid,)` 自己的哨兵不能被自己收掉／一切例外吞掉。
```

**⑫ `arm_when_earned()` docstring 全文：**

```
    """PostToolUse：夠格才武裝。回理由字串（呼叫端不讀，留給測試與未來的痕跡）。

    一切例外吞掉：`.claude/settings.json` 的 description 記載過 P0（hook 誤觸會把所有
    工具硬鎖死），而武裝失敗最多是少一層保護，絕不可反過來變成故障源。
    """
```

**⑬ `arm_quota_wakeup()` docstring 全文（含 R83／W2-A 沿革指標）：**

```
    """額度 95%／`arm` 分支的喚醒武裝；回 `{armed, sentinel_off, posix}` 給訊息用。

    🔴 平台判斷與逃生口刻意留在 hook 這一側：`tools/lib/quota_gate.py` 只讀這份回報，
    自己不去問 `os.name`、也不去讀哨兵的環境變數——那會讓同一份平台知識有第二個家。
    🔴 `armed` 是**真的 spawn 出去了**，不是「我走到了那個分支」：舊實作把兩者混同
    （Popen 拋例外時照樣回報 armed），而那正是本 repo 反覆判過的「真紅讀成綠」。
    憑證仍是 planner 自己的取證閘（`relay_problems()` 禁止在兩個憑證鍵皆空時把狀態寫成
    armed），本函式一行都沒有動它，只當消費者。

    🔴 射程：`posix` 這個鍵的語意是「這台機器沒有排程載具」，由 `_has_carrier()` 決定
    ⇒ mac 上為 False（launchd 真的武裝得起來）。取證指令的唯一的家＝各後端的
    `evidence_hint()`（`tools/lib/schedule_backend.py`）；本函式只回報三個布林，一行取證
    字串都不產。R83／W2-A 那段「訊息會指錯路」的沿革（含它在同一輪內就轉假的經過與
    darwin 實測輸出）逐字保全於 `CrossPlatform_R91_Scan_Findings.md` §A-5。
    """
```

上述十三段搬出後，檔內原文改寫為對齊 D27 新行為＋精簡版 WHY（各自留一行指標指回本節或
`moved_lore.md`／`CrossPlatform_R91_Scan_Findings.md` 原引用），語意不變、只是把「歷史
沿革的完整敘事」搬出主檔。逐字比對見本輪 commit 的 diff（`.claude/hooks/
context_budget_guard.py`）。

### 效能量測（Dev-A7 實測，2026-09-12）

payload：`PreToolUse` ／`tool_name=Read`／假逐字稿 1 筆 assistant usage（50,000 tokens，
model=`claude-fable-5-1`）／`AUTOSDD_SENTINEL_OFF=1`／`env -u AUTOSDD_CONTEXT_WINDOW`，
`python3 <hook> < payload.json` 跑 10 次量中位數：

| 版本 | 中位數 | 說明 |
|------|--------|------|
| OLD（D21，`git show HEAD:...` 唯讀取出） | 76.40 ms | 無 pin 時不查表 |
| D27 僅套 `resolve_latest_root_fast()`（無 per-session 快取） | 111.58 ms | Δ+35.18ms，超過 30ms 門檻——`git ls-files` 本身即耗 ~24-32ms，`resolve_latest_root_fast()` 每次都重跑 |
| D27 完整版（`resolve_latest_root_fast()` ＋ per-session 快取） | 77.92 ms | Δ+1.28ms（10 次裡只有第 1 次冷啟動吃到 ~35ms，第 2～10 次快取命中，落回與 OLD 統計不可分辨） |

結論：per-session 快取是必要的第二層——單靠 importlib 熱路徑（省掉多開一個 python 行程）
仍不足以把 `git ls-files` 本身的 I/O 成本壓到 30ms 門檻以下；快取把這個成本攤提成
「每個 session 只付一次」，與 hook 實際的呼叫模式（同一 session 內每次工具呼叫都觸發）
相符。

## 第七輪 史料搬遷（Dev-Trim7；護欄層原文逐字保全）

> DEF-200-275 第七輪：package A／B 對 `test_context_window_parity.py`／
> `test_context_budget_guard.py`／`test_root_guard_known_model_r145.py` 的合法新增
> 使護欄層行數棘輪（`_FROZEN_GUARD_LINES` 總量 98236）與分桶棘輪（`prose` 桶 4512）雙雙
> 轉紅（98373／4528）。本節不做任何改寫、不重釘任何棘輪常數：測試碼與判準本身一行未砍，
> 只搬「背景故事／事故經過／歷史沿革／方法論選擇的完整敘事」，原處各留一句 WHY＋本節指標。
> 每則標明來源檔案與符號名，原文如下（不做任何改寫，逐字保全）。

---

## tools/tests/test_platform_utils_dedup.py

### `<module>` 模組頂端 docstring（原文）

```
tools/lib/platform_utils.py 收斂止血鎖（R16 架構最佳化 — Architect 建議 A/E）。

背景：`_init_utf8_streams()` 曾被複製貼上到至少 8 個檔案，其中 6 份漏了
`sys.platform != "win32"` 守衛、2 份有。8 個呼叫點已收斂為統一 import
`tools/lib/platform_utils.init_utf8_streams`——但收斂當下誤判「有守衛的 2 份
才是正確版本」，實際上 `test_hooks_stdin_utf8.py` 證明「無條件包裝（原本
6 份的行為）」才是正確版本：呼叫端可在任何平台以 `PYTHONIOENCODING` 覆寫
編碼，POSIX 上不強制重新包裝會讓阻斷級 hook 的中文錯誤訊息讀成亂碼。
本測試機械鎖住兩件事：
  1. `platform_utils` 模組本身提供的 API 存在且行為正確（兩平台皆包裝 / 三態標籤）。
  2. 8 個已知呼叫點不再各自定義 `_init_utf8_streams()`（防未來復發第 9 份複製貼上）。

R66 追加（ADR-XPLAT-002 §5 Phase 2-C 驗收判準③ 補齊，DEF-101-629）：Phase 2-C／
2-D 把 10 份消費者各自的 LATEST 版本解析／凍結版本 regex 樣板收斂進
`tools/lib/sdd_latest.py`（`DEF-101-624`）之後，ADR 原始驗收判準③「任一消費者
改回自帶 `_latest_root` ⇒ dedup 鎖須紅」指定的手法正是「擴充本檔既有的
`_scan_repo_py_for(pattern)` 機制」，但落地當下未真正補上（僅補了 `DEF-101-627`
的模組自身行為回歸鎖，未補「消費者不得復發自帶定義」這道鎖）。本輪比照既有
`_EXTRA_DEF_RES` 做法，補上 `resolve_latest_name`／`resolve_latest_root`／
`exclude_frozen_sdd_versions` 三個函式的 repo-wide 唯一定義鎖。

R70 訂正兩件事（`DEF-101-751` 實質／`DEF-101-752` 元層級，兩者由同一個事故顯形）：

**① 不變量本身錯了（`DEF-101-751`）**：R17 的鎖寫的是「全 repo 只有一個定義點」，
但 R69 的 `ADR-XPLAT-003` 讓 `AutoClaude/autoclaude/utils/platform_caps.py` 也必須
定義 `is_windows()`／`is_macos()`——`autoclaude` 是**可獨立 pip 安裝**的套件
（`AutoClaude/pyproject.toml`，hatchling 預設只打包 `AutoClaude/autoclaude/`），
根層 `tools/lib/` 不在 wheel 內，脫離 monorepo checkout 後 import 必然失敗。
這與 `DEF-101-295`（R33 Architect 裁決，見 `autoclaude/utils/logger.py` 檔內註解）
是**同一條結構事實**、同一個既有解法：**跨孤島各留一份 ＋ 以鎖釘住其一致性**。
故本檔的不變量改寫為「**每一個相依孤島內，各 helper 只准有一個定義點**」——
不是把 `platform_caps.py` 加進白名單（那是把鎖改鬆），而是把「孤島」這個真正的
邊界寫進斷言：任一島內出現第二個定義點、或某島出現它不該有的 helper，皆須紅。
孤島邊界不是說法而是**結構事實**，由 `test_autoclaude_package_island_cannot_reach_root_tools_lib`
機械證明（該島若哪天真的搆得到根層 SSOT，兩島就該合併、本檔的雙 SSOT 宣告同時失效）。

**② 掃描面 fail-open（`DEF-101-752`，本輪更有價值的一筆）**：本檔原本用
`git ls-files "*.py"` 當掃描面 ⇒ **未追蹤（untracked）的 .py 天然不可見**。
`platform_caps.py` 在 R69 全程都是 untracked，於是上述①的衝突躲過了**四輪四方
複審**與收尾者多次 `run_root_unittests.py` 全套實跑（皆 `Ran 1581 … OK`），
直到 `git add -A` 讓它變成 tracked 的**那一刻**才在 pre-push 顯形。
掃描面現改為 **tracked ∪ untracked-not-ignored**（`git ls-files` ＋
`git ls-files -o --exclude-standard`）——排除 venv/快取的效果原本就靠 `.gitignore`，
`--exclude-standard` 一樣排除得掉。盲區已封由
`TestScanSurfaceCoversUntrackedFiles` 以真實 untracked 探針證明
（修前的 tracked-only 掃描面看不到它／修後看得到且判紅）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
```

---

## tools/tests/test_no_invalid_escape_sequences.py

### `<module>` 模組頂端 docstring（原文）

```
非法轉義序列（`W605` / `SyntaxWarning: invalid escape sequence`）機械鎖
（R60 QA-R60-05 的結構性那一半）。

WHY（為何非得有這道鎖）：
  R60 在 `AutoClaude/tools/local_ci_gate.py`（本機 CI 閘門**唯一核心**）的 docstring
  引述 Windows 路徑時引入 `\l`，Python 3.11 只印 DeprecationWarning、**3.12 起升為
  SyntaxWarning、CPython 已宣告未來版本改為 SyntaxError**（屆時該檔無法 import）。
  當時三道閘門全綠：AutoClaude 的 ruff `select` 不含 `W`（已於同輪補上），而**根層
  `tools/` 與 AISDLC_SDD 樹完全沒有任何 ruff 閘門**，所以這一整類在本 repo 過去只能
  靠人眼。QA-R60-05 判為 blocking 的正是這個結構面：不是那一個 `\l`，而是
  「這一類在閘門上看不見」。
  同輪 Pkg-4 自己就對 `tools/tests/test_extras_quoting_zsh_safety.py` 的同款缺陷寫過
  「建議由該檔擁有者改成 raw string」——建議在同一輪內沒有承接者，正是「沒有機械物
  就等於沒發生」的教科書例子。

判準：對 `_SCAN_ROOTS` 下每一支 `.py` 做 `compile()`，收集 `invalid escape sequence`
  警告。命中且不在 `_KNOWN_DEBT` 名冊內 → 紅。
  （本 docstring 刻意不寫出三引號字面——寫了會提前結束自己，本檔第一版即因此
  `SyntaxError: invalid character`，屬「示範壞形態的文件會反咬自己」的同族陷阱。）

🔴 修法（**首選＝把該處反斜線改寫成 `\\`**，次選才是整串改 raw）：
  R60 Pkg-P3 回收存量債時實測發現「一律改 raw 前綴」這個處置**不是**零語意變更，
  原名冊三筆的 WHY 都寫錯了方向：raw 化會讓同一 docstring 內**既有的合法轉義**
  一併改變 rendered 內容——`test_ps51_compat.py` 有 8 處 `\\`（本意是顯示單一反斜線
  的正則，raw 後會變成顯示兩個，**文件反而變錯**）、`test_nightly_interpreter_determinism.py`
  有 2 處、`test_extras_quoting_zsh_safety.py` 甚至有一個合法的 `\t`（rendered 是真
  TAB）。三檔實測 `ast.get_docstring()` 皆 `differs_if_made_raw=True`。
  反之「把該處反斜線加倍」對**非法**轉義是恆等變換（Python 對非法轉義原樣保留
  反斜線），R60 實測三檔 rendered docstring 的 len 與 sha256 前後完全相同——這也正是
  `ruff --select W605` 自己給的 `help: Add backslash to escape sequence` 與 `--fix` 行為。
  只有在該字串內**沒有**任何合法轉義時，raw 化才等價。

🔴 判準邊界（誠實劃界）：
  - **掃描面刻意不含 `AISDLC_SDD/AISDLC_SDD_v0.01`~`v0.29`**（29 個凍結版）：依
    Copy-on-Evolve 政策那些樹不改，掃出來只能長出 29 份永久豁免。實測（R60）：全 repo
    5,451 支 `.py` 掃完為 6.8 秒、命中仍是同樣這 3 支；縮到現行掃描面是 832 支／0.7 秒
    且**命中集合完全相同**——即縮面沒有損失鑑別力，只省時間。若哪天凍結版真的長出這
    類問題，它也不在本鎖負責的範圍（該由凍結版豁免家族處理）。
  - 只驗「非法轉義」這一類，不是完整的 ruff `W`。AutoClaude 樹另有 ruff `W`
    （`AutoClaude/pyproject.toml`，R60 補入）作為更全面的第二層；本鎖是**跨樹**那一層。
  - `compile()` 只做語法層編譯、**不執行**任何模組，無 import 副作用。

名冊紀律（防「豁免變永久」）：`_KNOWN_DEBT` 為既有存量債（皆非本輪引入），每筆須帶
  WHY；並有 stale 自檢——某筆已修好卻留在名冊 ⇒ 紅，強制回收。這是刻意避開 R60
  `_PENDING_MIGRATION_SITES` 的坑（無 stale 自檢的 pending 名單永遠不會退場）。

  🔴 **名冊現為空**（R60 Pkg-P3 全數回收，見上）。原本登記的 3 筆是「**無承接輪次的
  backlog**」——只是把待辦從缺陷帳本搬進程式碼裡的名冊，正是本輪硬規則② 要治的形態，
  而三筆的修法都只是加倍反斜線（零 rendered 變更），沒有任何延後的理由。
  名冊機制**保留**（未來仍可能有真的需要凍結的存量債），但空名冊會讓 stale／WHY 兩支
  自檢變成恆真斷言，故另立 `test_stale_detector_reports_a_synthetic_stale_entry` 與
  `test_why_detector_reports_a_synthetic_empty_why` 兩支**合成自證**，讓名冊機制在
  零條目時仍有鑑別力（同本檔既有的 `test_detector_catches_a_synthetic_offender` 慣例）。

執行：python tools/run_root_unittests.py
      python -m unittest tools.tests.test_no_invalid_escape_sequences -v
```

---

## tools/tests/test_doc_env_prefix_platform_parity_r60.py

### `<module>` 模組頂端 docstring WHY 段（原文）

```
WHY（為何非得有這道鎖）：
  PowerShell **沒有** `VAR=value <指令>` 這種行內環境變數前綴語法。照抄 bash 形態的
  Windows 使用者拿到的是 `The term 'PYTHONUTF8=1' is not recognized as the name of a
  cmdlet...`（本機 Windows PowerShell 5.1 實測），而且錯誤訊息完全不指向真正的原因，
  看起來像「lint-imports 沒裝」。設環境變數須寫 `$env:VAR=值; <指令>`。
  這個家族已**三度復發、四個站點**，每次都靠人工逐份補：
    - R57：`ONBOARDING.md` §7 補齊；
    - R59（DEF-101-513）：根 `CLAUDE.md` §測試/Lint、`docs/AISDLC_Agent_UserGuide.md`
      §1.4 補齊——但同一份修復**漏掉** `AutoClaude/README.md`；
    - R60 Scan-D D-02：`AutoClaude/README.md` 的 `PYTHONUTF8=1 lint-imports` 仍是
      bash 單邊，且整份 README 的 `$env:` 出現 **0 次**（不是「對照隔太遠」而是
      「完全沒有」）。
  該家族在 R60 之前**零機械鎖**（實查：全 repo 沒有任何檢查器碰過這個形狀），所以
  「下一份新文件又只寫 bash 形態」是必然而非偶然。本測試把它升為機械守門。
```

---

## tools/tests/test_gha_action_versions.py

### `<module>` 模組頂端 docstring【B/C 兩節取捨】段（原文）

```
【B 節為何不用 pyyaml】根層 `tools/`＋`tools/tests/` 全數 stdlib-only，
`root-infra-ci.yml` 的 root-infra job 沒有 `setup-python`、也沒有任何
`pip install` 步驟（實查該檔可證），引入 pyyaml 會替根層閘門新增一個此前不存在
的外部相依。故 B 節自帶一個**縮限用途**的縮排掃描器 `parse_shell_distribution()`，
並以下列實測建立等價性證據：

  已實測涵蓋：本 repo 根層 11 支 workflow 中，7 支（aisdlc-sdd-arch-fitness /
  aisdlc-sdd-artifact-cleanup / aisdlc-sdd-drift-daily / aisdlc-sdd-fsm-chaos-nightly
  / macos-compat-ci / root-infra-ci / windows-compat-ci）以本掃描器與
  `yaml.safe_load` 逐 job 比對 `runs-on` 與 run-step shell 分佈，結果**全部相等**。
  已知不涵蓋（掃描器主動 raise、不做靜默猜測）：帶 `defaults:` 區塊的檔案
  （aisdlc-sdd-ci / autoclaude-ci / autoclaude-mutation-on-change /
  autoclaude-pg-e2e-on-label 共 4 支）——本鎖只服務 windows-compat-ci.yml，
  而該檔檔頭自述「全檔無 workflow 層／job 層 defaults:」，因此把 `defaults:`
  的出現直接當成「快照前提已被推翻」而 fail-loud。
  未窮舉：非本 repo 的任意 YAML 寫法（流式對映 `{...}`、錨點/別名、`- run: |`
  以外的區塊純量寫法、tab 縮排等）一律不保證——掃描器對認不得的形狀是
  raise 而非猜測，故失效方向是紅燈不是綠燈。

【C 節為何**可以**用 pyyaml（與 B 節不同調，這是有據的差別不是矛盾）】上段
「根層全數 stdlib-only」寫於 R57；R68 之後該前提已由 repo 自己推翻並改成受管
相依——`tools/run_root_unittests.py` 的 `_THIRD_PARTY_PREREQS` 明列
`("yaml", "pyyaml")`，且由三道機械物看守：runner 開場 fail-fast、下限失敗訊息
歸因、以及 `test_run_root_unittests.py::CiPrereqInstallLockTest`（凡在 CI 跑本
runner 的 job 都必須先裝清單裡每一個 pip 名）。實查三個消費者皆已安裝：
`root-infra-ci.yml:396`、`windows-compat-ci.yml`／`macos-compat-ci.yml` 的
「tools/tests 第三方相依」步驟；本機 pre-push 走 `.venv`（AutoClaude runtime
本就相依 pyyaml）。C 節要判的是「run 本體」這個**值**，縮排掃描器對區塊純量的
續行、`|`／`>`／`|-` 變體、行內註解各有一套規則，自寫近似只會多一個新的失明
面——B 節當時付不起的相依成本，今天已經是既成事實，故不重複造輪。
B 節維持原樣（不改動既有綠鎖）。
```

---

## tools/tests/test_sanitize_component_frozen_sdd_versions_lock.py

### `<module>` 模組頂端 docstring（原文，僅保留執行段未動）

```
背景：R44 對 `AISDLC_SDD_v0.01`～`v0.29` 共 29 個凍結基線版本的 7 支
`tools/fsm_runtime/` 檔案（`hub_sync.py`／`production_monitor.py`／`hub_merge.py`／
`spec_patch_proposer.py`／`production_to_fpl.py`／`sandbox_runner.py`／
`counterfactual_replay.py`）逐版套用「呼叫該版本既有 `_sanitize_component()`」的
P0 路徑穿越修復（`rule_id`/`nfr_id`/`ac_id`/`fpl_id`/`divergence_kind`/`app_id`
等使用者可控字串未經淨化即組進檔案路徑 f-string，可逃出預期目錄讀到任意檔案）。
本輪由使用者明確核准、破例打破 Copy-on-Evolve 鐵律對 29 份凍結快照原地補丁
（見 `docs/06_quality/AutoSDD_Defect_Log.md::DEF-101-357`）。

Architect 二審發現：這 203 處改動（29 版 × 7 檔）完全沒有任何常駐測試鎖住——
每版 `tools/fsm_runtime/tests/` 目錄本身沒有對應測試（那些測試只存在於 v0.30/
LATEST），且既有 repo-wide 掃描（`tools/tests/test_windowsapps_guard_*.py`）
只涵蓋 WindowsApps python 可用性判斷、不涵蓋這個路徑穿越修復類別。若未來任一
版任一檔被意外還原（順手重構／merge 衝突誤解／另一支自動化腳本覆寫），目前
沒有任何測試會抓到。本檔補上對稱的 repo-wide 靜態鎖。

方法論選擇（**刻意不**直接搬 v0.30 端既有的
`test_sanitize_component_call_site_lock.py` 泛用 AST 掃描邏輯，而是改用逐檔
「已知淨化呼叫式必須存在」的正向斷言）：

  逐項理由（不搬 v0.30 泛用 AST 掃描的兩個實測盲點、bug-injection 的固定基線 SHA
  錨定、正向斷言對 7 支檔案的鑑別力驗證）原文逐字＝
  `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。

方法論邊界（誠實記載）：
  - 本檢查只驗證『已知淨化呼叫式的字面文字仍存在於檔案中（非注釋內）』，非
    真正的資料流/AST 語意驗證——若該呼叫式被複製到一個完全無關、不影響組
    檔名路徑的死碼分支，本鎖仍會判定通過（誤判為安全）。這類『刻意規避』手法
    需要真正的控制流分析才能封閉，比照 WindowsApps 鎖與
    `test_sanitize_component_call_site_lock.py` 既有記載的同級方法論邊界，
    此為已知限制而非本檔涵蓋範圍。
  - 只掃描凍結版本（`AISDLC_SDD_v0.01`～目前 LATEST 之前所有版本，動態排除
    LATEST——LATEST 由 `test_sanitize_component_call_site_lock.py` 用不同機制
    〔泛用 AST 掃描 + `_ADDITIONAL_RISKY_NAMES` 委派 wrapper 名單〕獨立守護，
    兩者分工互補，不重複亦不遺漏）。

R66 追加（Review round 1 QA 發現，DEF-101-627）：`tools/lib/sdd_latest.py`
（R66 新增，DEF-101-624）當時只做手動 bug-injection 驗證、未落成任何測試檔的
永久斷言。本應為它新增專屬 `tools/tests/test_sdd_latest.py`，但 `DEF-101-561③`
棘輪（`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet`）
自 R61 起要求 `tools/tests/` 擴充既有檔、或先合併／刪除等量舊物再加
（🔴 R78 ARCH-03 訂正：R66 當時量的是**檔數**、語意是「禁止新增」；R77 起改量逐檔
行數的**淨額**，新增檔案本身不違規，淨額上升才違規）
——故把本檔自己呼叫端（`_frozen_version_dirs`）的 `.fullmatch()` call-site 鎖
＋ `exclude_frozen_sdd_versions` 的過濾語意併入本檔（本檔是原始兩個肇事呼叫端
之一，且已 import `sdd_latest`）；`FROZEN_VERSION_DIR_RE` 本身的 `.fullmatch()`
行為回歸鎖與 `resolve_latest_name`/`resolve_latest_root` 覆蓋併入姊妹檔
`test_component_sanitizer_shared_layer_lock.py`（見該檔同款追加段）。
```

---

## tools/tests/test_doc_loc_baseline_freshness_r60.py

### `parse_cloud_fields`（原 docstring）

```
錨尾解析成 `({欄位: 值}, 問題清單)`；同一欄位出現 ≥2 次一律 **fail-loud**。

🔴 WHY fail-loud 而不是沿用「取最後一個」：錨是**單獨一行**、機器欄位與人讀散文
同住那一行，於是散文裡一個 `pending=<sha>…` 字樣就會**靜默覆蓋**真正的欄位值，
判準拿帶省略號的字串去比 sha ⇒ 假紅，而錯誤訊息印著一個看起來正確的值
（被自己咬到的那次逐字＝R89 收尾證據檔）。

這與根 CLAUDE.md 那條「已橋接的 hook 名稱不得與射程字樣同行」是**同一個病**：逐行
substring 判準遇上同一行的散文。那邊的解是把文件寫成可精確判定，這邊的解是讓歧義
**當場 fail-loud**——兩者都不是「把判準放寬」。少了這一條，下一個在錨上寫說明文字的
人會再踩一次，而症狀是一個指著正確值卻說它不對的假紅（最難查的那種）。
```

### `TestR74CloudCiStatusIsRecorded.test_the_deadlock_scenario_no_longer_forces_a_fabricated_check`（原 docstring）

```
🔴 死結回歸鎖（端到端）：舵手 2026-08-05 實測的那個狀態必須可以合法通過。

場景逐字重現：本輪改了測試樹 → `--write --with-slow` 把 `measured-at` 推到
比 `checked-at` 更新的一天 → 舊判準在此判紅，而唯一的解紅操作是編造一次查核。
本測試斷言：**同一份文件**在誠實宣告 pending 之後 rc 面全綠，且**沒有任何欄位
被改成當天／HEAD**（`checked-at` 與 `head-sha` 逐字保持原值）。
```

---

## tools/tests/test_block_destructive_git_r83.py

### `TestTheRelaxationOpensNoNewHoles.test_the_filesystem_root_contains_the_project_too`（原 docstring）

```
🔴 反向包含的**邊界格**，獨立驗證輪實測出來的漏擋（不是想像的形態）。

它躲得過上一支測試的機制、以及當時 `cd / && git clean -fdx` 被放行的實測，
逐字＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。

判準本身刻意不寫死 `/`：用 `os.path.abspath(os.sep)` 取當前平台的根
（Windows 上是磁碟機根），否則這支鎖在另一個平台上量的是別的東西。
```

---

## tools/tests/test_smoke_ci_sync.py

### `TestSmokeCiSync.test_bash_n_scan_surface_matches_root_infra_ci`（原 docstring）

```
`root-infra-ci.yml` 第 1 道（bash -n）與 `macos_smoke_local.sh` [1/7] 是兩份
手寫實作、兩者自述「同一份 git ls-files 清單、同一套判準」，但此前零機械互鎖
（立案的三種實測漂移＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`）。
凡「兩份硬編實作互稱鏡射」本 repo 一律建鎖（同
test_root_infra_parity 的 CI↔pre-push 守門清單鎖），故機械斷言三件事：
  1. 兩處 `git ls-files` 的 pathspec 樣式集合逐字相同；
  2. 兩處的兩段下限釘選值（active .sh／無副檔名 git-hooks）逐字相同；
  3. 兩處都以 `sdd_version.py` SSOT 解析 LATEST 做凍結版排除（DEF-101-133：
     禁止任一方內嵌第二份版本 regex，否則 Copy-on-Evolve 建新版時兩邊分歧）。
```

---

## tools/tests/test_skip_discoverability_r83.py

### `TestPgSkipRemedyStaysDiscoverable`（class，原 docstring）

```
「大量 skipped 的最大宗解法＝一行 docker 指令」必須留在使用者找得到的地方。

Rule 9：本類守的是**可發現性**這個意圖，不是某段文字的排版。大量 skip 的最大宗成因
就是「容器沒起來」，而這件事在 R83 之前於兩份 onboarding 文件裡一個字都找不到
（立案的兩組實測 skip 數＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`）。
這兩份文件是掌舵者實際會讀的入口，拿掉這段＝缺陷復發。
```

---

## tools/tests/test_ntfs_trailing_space_device_name.py

### `TestArchivedIterationDocRefsResolve`（class，原 docstring）

```
R72 資料層：歸檔後，根層 `docs/` 對四件套的引用必須仍解析得到。

掃描面與 `TestRootDocsPathRefsAreCaseExact` 同（根層 `docs/` 的 .md），
但問的是**另一個問題**：那道鎖三分法裡「上層與 lowercase 索引皆不中」的那一支
是**刻意放行**的（避免死連結偵測變噪音來源），於是搬檔造成的斷鏈對它完全隱形。
本類把「四件套」這個**檔名形態明確、轉址規則明確**的子集從那個縫裡撿回來守。
```

---

## tools/tests/test_dev_start_ps1_lastexitcode.py

### `<module>` 模組頂端 docstring（原文，僅覆蓋清單與執行段未動）

```
tools/dev_start 兩支殼（.ps1 / .sh）的「被 source 時 rc 語意」回歸鎖。

# 第一部分（原始職責）：tools/dev_start.ps1 dot-source 失敗分支 $LASTEXITCODE（DEF-101-304）

`tools/dev_start.ps1` 的 `.NOTES` 明載「dot-source 呼叫端判斷成功/失敗請讀
$LASTEXITCODE，不要用 $?」，但早期失敗分支（找不到 repo 根／找不到 Python
直譯器）在 dot-source 情境下只執行裸 `return`，未對 `$LASTEXITCODE` 賦值——
呼叫前的殘值（可能是 0）會被誤判為成功。對等的 `tools/dev_start.sh` 用
`return 1` 正確傳遞失敗，兩邊在 exit code 語意上不對稱（R35 Scan-A 發現）。

本測試只驗證「找不到 Python 直譯器」這條分支（PATH 清空即可穩定觸發，
不依賴 Windows PATHEXT／`.cmd` 解析語意，pwsh 在 macOS/Linux/Windows 上
dot-source 與 `$LASTEXITCODE` 的語言層行為一致，故不比照
`test_bootstrap_ps1.py` 的 `_windows_pwsh_available()` 額外限定真 Windows）。

# 第二部分（R67-C17 併入）：tools/dev_start.sh 的 zsh／bash 實跑載具

**為何併進本檔而不新開一支**：`DEF-101-561③`（由
`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 機械強制）要求
「把新判準擴充進既有鎖檔」（🔴 R78 ARCH-03 訂正：R67 當時它量的是**檔數**、語意是
「禁止新增」；R77 起改量逐檔行數的**淨額**，新增檔案本身不違規）。而本檔正是 dev_start
兩支殼「被 source／dot-source 時如何傳 rc」的既有鎖檔——上面第一部分的緣起，逐字就是
「對等的 `tools/dev_start.sh` 用 `return 1` 正確傳遞失敗」這句**從未被機械驗證過**的
對照宣稱。第二部分把那句話變成真跑出來的事實，是同一條軸上的補完，不是雜物。

**缺口本體（R67-C17）**：`source tools/dev_start.sh` 是 ONBOARDING §2.1 教使用者每天
開工敲的第一道指令，而 macOS 自 Catalina 起預設 shell 就是 **zsh**。該檔有真正的 zsh
專屬程式碼路徑：`ZSH_EVAL_CONTEXT` 判定是否被 source、`${(%):-%x}` 取當前檔案路徑
（`zsh -c` 下 `$0` 是 "zsh"，不可靠）。R67 全庫普查實測：這條分支在整個自動化層的唯一
執行者是 `.github/workflows/macos-compat-ci.yml` 的一個 step，而該 workflow 因 CI 帳務
停擺（DEF-101-081）多輪未真正執行 ⇒ **使用者最常走的開工入口，全 repo 零活體驗證**。
`bash -n` / `zsh -n` 只做語法解析，執行不到這條分支（本機實測兩者皆 rc=0）。

🔴 **第二部分的斷言「結構」是重點，不只是斷言內容**（R67-C17 附帶發現的直接修復）：
macOS compat-CI 那個 step 的形狀是「`zsh -c 'source dev_start.sh; <斷言>'`」——把斷言
寫在同一個 shell 的 source 之後。R67 注入實測證明該形狀對它**本來要抓的主要故障模式
結構性失明**：一旦 sourced 偵測壞掉（`_ds_sourced=0`），dev_start.sh 會落到檔尾
`exit "$_ds_rc"`，**直接殺掉整個 `zsh -c`**，後面所有斷言一行都不執行、rc 仍為 0 全綠
（實測：注入後 CI 形狀 rc=0、`ASSERTION_LINE_REACHED` 從未印出）。故本檔改用**行程外側
通道**：把證物寫進 source 之後的一個重導向檔，再於 Python 端檢查。「斷言被跳過」因此
變成「證物檔不存在」＝當場紅，而不是靜默通過。
```

---

## tools/tests/test_windowsapps_guard_bash_parity.py

### `<module>` 模組頂端 docstring（原文，僅結構清單①②未動）

```
背景：`tools/lib/WindowsAppsGuard.ps1::Test-IsRealPython`（R37 抽出）與
`bootstrap_core.py::_is_windows_apps_stub`（Python 側）皆只涵蓋各自語言的
呼叫端，repo 內另有多支 tracked bash 腳本（含 `tools/git-hooks/pre-push` 這個
每次 push 都會實際執行的 dispatcher 本體）各自用裸 `command -v python`／
`command -v python3` 判斷可用性，從未排除 Windows Store App Execution Alias
空殼——Git Bash on Windows 會繼承 Windows PATH，同樣會命中
`%LOCALAPPDATA%\Microsoft\WindowsApps` 底下系統自動註冊的空殼
`python.exe`/`python3.exe`（`command -v` 判定為「存在」，實際執行只會跳出
Microsoft Store 安裝提示，對 `pre-push` 這類阻斷式 hook 而言即為掛起）。

`_has_ssot_guard`（判斷一段 `.sh` 內文是否已正確接上共用 guard）沿革：R46 一審
只判斷「兩關鍵字是否曾出現在文字中」，QA 二審 bug-injection 揪出可被「no-op
前綴＋尾隨註解」／「一般尾隨註解」／「純文字提及」三種手法繞過，改為
`_strip_bash_comment`（剝離不在引號內的 `#` 註解）+ `_SOURCE`/`_CALL` 陳述式位置
錨定正則（`_has_real_source_statement`／`_has_real_call_statement`）；Architect
三審再揪出兩者排除純訊息輸出指令行（`_PRINT_COMMAND_RE`）的保護不對稱並補齊；
`TestHasSsotGuardBypassResistance` 對這三種繞過手法各自構造專屬回歸測試。

方法論邊界（誠實記載，非本檔涵蓋範圍——R46 QA 三審 bug-injection 揪出，比照
`AISDLC_SDD/scripts/component_sanitizer_callsite_scan.py` 同款 Rule 2 比例原則
不強修的先例）：`_has_ssot_guard` 是逐行文字掃描 + 位置錨定正則，不是真正的
bash 語法解析，因此對下列兩種刻意構造的偽裝手法無鑑別力：
  - heredoc（`cat <<'EOF' ... EOF`）內把兩個關鍵字包成「使用範例」說明文字，
    真正選 `PY` 的邏輯改用裸 `command -v python`——逐行掃描看不出 heredoc
    邊界，會把說明文字誤判為真陳述式。
  - 把 `is_real_python_candidate` 包進一個語法正確、但整檔從未被呼叫的死
    函式裡（source 行是真的）——本檔不做可達性分析，無法分辨「定義了」與
    「真的被呼叫到」。
  這兩種繞過會讓 `_has_ssot_guard` 誤判為已收斂，但風險有界：對已知白名單
  呼叫端（`_CALLER_FILES`），`test_no_raw_unguarded_python_check_remains`
  是另一支**不依賴** `_has_ssot_guard` 的獨立安全網（直接對這些檔案做裸
  `command -v python >/dev/null` 字面值 regex 比對），不受此限制影響；只有
  repo-wide 防增生掃描（`test_repo_wide_scan_finds_no_unmigrated_sh_scripts`／
  `test_repo_wide_scan_finds_no_zero_guard_python_calls`，鎖定「未知的新檔案」）
  對這兩種刻意構造的偽裝手法會失明。徹底解決需要真正的 bash 語法解析（含
  heredoc 邊界追蹤與基本可達性分析），複雜度遠超本檔工具定位，留待出現真實
  呼叫點再評估。
```

---

上述十三段搬出後，各檔原地依 Dev-Trim 紀律留「一句 WHY＋指針本節」（各自措辭見對應
檔案現況），語意不變，只是把「歷史沿革／背景敘事／方法論選擇的完整說明」搬出主檔；
任何判準、斷言、常數值、字串字面、豁免 token 皆未動。逐字比對見本輪 commit 的 diff。

🔴 誠實劃界（收尾窗口待辦）：本包（Dev-Trim7）依任務書明文「不准重釘任何棘輪常數／
不准動 `_GUARD_LINES_REPIN_LOG`」，故上列搬遷完成後，`tools/tests/test_adr_xplat001_
c1c2_lock.py` 的逐檔漂移判準（`guard_line_problems()` 款(6)）會把本包編修過的 12 支
檔（連同 package A／B 已造成、本包到工前就已存在的 3 支：`test_context_budget_guard.py`／
`test_context_window_parity.py`／`test_root_guard_known_model_r145.py`）一併列為
「基準值與磁碟不符」——這是 `drift_tolerance=0` 設計下，任何未經正式 `--print-guard-lines`
重釘的行數變動皆會觸發的必然結果，不是本包新引入的判準缺陷。收尾單人窗口需在本輪
所有並行包停工後，執行 `python tools/tests/test_adr_xplat001_c1c2_lock.py
--print-guard-lines` 並在 `_GUARD_LINES_REPIN_LOG` 補上本輪（R146？現查現存最大輪號＋1）
一列，方能讓 `test_the_line_ratchet_took_over_and_has_teeth`／
`test_ratchet_is_independent_of_git_state` 轉綠。

## 第七輪 史料搬遷（Dev-S8b；context_budget_guard.py 原文逐字保全）

D32b（總架構師 D32b 裁決，修 D32 審查發現 A5-LOC-BUDGET）：`.claude/hooks/
context_budget_guard.py` 因 D32（status line 進料）＋本輪 D27 查表階兩次新增，
`SPECIAL_FILES` raw-line 棘輪（1089）破線到 1147。手法同 Dev-A7（見上一節）：
①消除一處重複讀檔（A4-REDUNDANT-FEED-READ——`window_evidence()` 與
`cross_check_note()` 此前各自呼叫一次 `read_context_feed()`，`main()` 改為只讀
一次、以 `feed=` 參數／引數往下傳）；②把純敘事的沿革與展開版 WHY 段落原文逐字
搬到本節，檔內只留一行指標，每個函式仍保留一句判準 WHY。以下逐段列出**修改前的
原文**（來源：本輪 Dev-S8b 動工前的工作樹，起點＝commit 9e185d1 之後、含 D32
harness 進料在內的既有未提交狀態）：

**① 模組 docstring〈WHY〉〈context window 判定〉〈行為契約〉三節整段（判定順序
numbered list 與展開版 WHY 敘事）：**

```
WHY（沿革全文搬 scratchpad/dev-c/moved_lore.md；與 SDD `context_ledger` 的分工、
兩者同時觸發的殘餘限制、純文件約束對模型的攔阻力先例，皆見該檔）——一句話：把
harness 自己的 autocompact（姿態現查 `--check-autocompact`）之外，模型自己看得見
「現在幾 %」，並在 ≥94% 真的擋下展開型工具、產出可重啟點任務書供 `claude -r` 續跑。

量測面：hook payload 帶 `transcript_path`（本 session 逐字稿）。每筆 `type ==
"assistant"` 的 `message.usage` 下，**當前 context 佔用 ＝ input_tokens ＋
cache_creation_input_tokens ＋ cache_read_input_tokens**（`output_tokens` 不算：
下一回合才以 input 形式回到 context，重複計會高估）。

🔴 context window 判定（沿革＝R79／D21／D27，全文搬 `CrossPlatform_DEF200275_
Context_Metering_Evidence.md`〈第七輪〉：分母猜小只是早喊，猜大會讓守衛在真 90%
結構性靜默——方向不對稱是本節排序的唯一理由）
--------------------------------------------------------------------------------
判定順序（先可證、後推斷，來源字串原樣印給使用者；編號沿用 SDD `context_window.py`
的分母鏈——該檔獨有 ①`SDD_MAX_CONTEXT`，本檔沒有）：
  ⓪ **status line 進料**（D32／`tools/statusline_context_feed.py`）：harness 自己
     回報的 `context_window.context_window_size`，優先於一切釘值——它是唯一不靠猜、
     也不靠人手動釘值的來源（見 `read_context_feed()`／`resolve_window()` WHY）。
  ② `AUTOSDD_CONTEXT_WINDOW`：本檔旗標＝**指定值**（會與 ⑥ 查表值收斂）。
  ③④ `CLAUDE_CODE_AUTO_COMPACT_WINDOW`／settings `autoCompactWindow`＝**harness
     自己的 window 旋鈕**。同 ⑥ 收斂。
  ⑤ settings `model` 欄帶 `1m` 標記 ⇒ 1,000,000，帶交叉否決（見 `window_from_model()`）。
  ⑥ **以 model id 查表**（D27／ARCH-A4-01；`known_model_window()`）：表值＝Models
     API `max_input_tokens`。②③④以外**無條件**查表（D21 的「只在有 pin 時才查」
     捷徑經四方複審判定即缺陷根因，全文見證據檔）。
  ⑦ 本 session 歷來 `used` 曾超過 200,000 ⇒ window 必然大於 200K，取 1,000,000。
  ⑧ 其餘一律 200,000（保守下界）。
🔴 **⑧ 不得用來硬擋**（見〈PreToolUse 阻斷模式〉）；其餘各階皆夠格。

行為契約（PostToolUse＝觀測模式；沿革搬 moved_lore.md）
------------------------------------------------------------------
· payload 讀不出來 → stderr 一行 ＋ **exit 1**（出聲不阻斷，見 `degraded_payload_verdict`）。
· 量不到 usage → exit 0 靜默（「量不到」≠「輸入壞掉」，混同會讓守衛被整支關掉）。
· `< 84%` 靜默；`>= 84%` stderr ＋ 送進模型 context（`emit_to_model`，逃生口
  `AUTOSDD_CONTEXT_SIGNAL_OFF`），內容依額度尺 `quota_gate.draining()` 三分。
· `>= 94%` stderr 強制指引 ＋ 寫任務書 ＋ **exit 2**。
· **同一門檻＋同一 window 只喊一次**（`latch_key` 含 window／epoch）。
```

**② UTF-8 reconfigure 段：**

```
# 自己的 stdout/stderr 強制 UTF-8。缺這段時：locale 表達不了 CJK（en-US Windows
# ＝cp1252）→ 整段指引變 `\uXXXX` 逃脫字面；locale 表達得了但非 UTF-8（zh-TW
# ＝cp950）→ 讀者端亂碼。兩種都讓「提醒有了、指引沒了」，而本檔存在的唯一理由
# 就是純文件約束無攔阻力，指引不可讀等於把它砍掉一半。
# 例外一律吞掉且刻意比 stdlib 慣例更寬：**模組層**崩潰發生在 main() 的 try 之外、
# 繞得過那道保險，而 fail-open 在這裡是 P0。
```

**③ `platform_utils` 能力提供者段：**

```
# payload 讀取接上共用層 `tools/lib/platform_utils.py`（R81／SUB-S1-04 的交棒項；
# 手抄本漂移立案史搬至 CrossPlatform_Guard_Line_History.md〈context_budget_guard 立案史彙整〉節）。
# 🔴 與上方「零外部相依」**不衝突**：那條要的是 fail-open 而不是「不准 import」。
# 共用層不可達時（`run_path` 起、`tools/lib` 不在 sys.path）下面的 except 讓它退化成
# `read_payload() -> None`，正好走本檔既有的「讀不出來 → 出聲不阻斷、rc=1」分支；
# 模組層不會爆掉，也不留第二份 JSON 解析實作（形態同 `lint_powershell_command.py`）。
```

**④ `quota_gate` 能力提供者段：**

```
# 額度水位節流閘（80/95 兩道）整條的家＝`tools/lib/quota_gate.py`（R82／Q2-02）。搬走的
# 是一個完整主題：輸入是額度快取／逐字稿撞線，輸出是「這次扇出准不准」，與 context 水位
# 零交集。形態與上一格逐字相同（同一條 sys.path、同一種 fail-open）：不可達時本符號為
# `None`，額度軸整條退化成「量不到」＝不節流，而**不會**把 context 阻斷也一起帶走
# ——那是拆分的硬安全條件（見該檔檔頭），不是風格偏好。
```

**⑤ `sentinel_lifecycle` 能力提供者段：**

```
# 哨兵的**生命週期判準**（值不值得一支 schtasks、什麼時候收）整條的家＝
# `tools/lib/sentinel_lifecycle.py`。形態同上一格：不可達時本符號為 `None`，
# 武裝整條退化成「不武裝」——那個方向安全（少一層續航保護），反過來（不可達就無條件
# 武裝）才是 R82 之前那個會在排程器裡增生的形狀。
```

**⑥ `schedule_backend` 能力提供者段：**

```
# 排程**載具**（schtasks／launchd／沒有）唯一的家＝`tools/lib/schedule_backend.py`。
# 形態同上一格（同一條 sys.path、同一種 fail-open）：不可達時本符號為 `None`，
# `_has_carrier()` 回 False ⇒ 武裝整條退化成「不武裝」，方向與上一格一致（少一層續航
# 保護，而不是無條件武裝）。
# 🔴 R83／W2-A：本檔此前用 `os.name != "nt"` 在**四個**武裝站點各判一次平台，於是
# 「mac 上有沒有排程載具」這個問題有四個答案的家；補 mac 支援時只要漏改一個，那一臂
# 就會靜默失明（而失明的表徵與「這台機器本來就沒有載具」完全相同）。現在四個站點一律
# 問 `_has_carrier()`，而它只是把問題轉給那個唯一的提問點。
```

**⑦ `sdd_latest` 能力提供者段：**

```
# LATEST 版本路徑解析唯一真相源＝`tools/lib/sdd_latest.py`（查表資料的家＝
# `$V/tools/fsm_runtime/data/known_model_windows.json`，見 `known_model_windows_
# path()`）。同一套 fail-open：不可達時本符號為 `None`，查表整條退化成「查不到」。
```

**⑧ `quota_limits` hard import 段：**

```
# 額度**撞線判讀**唯一的家＝`tools/lib/quota_limits.py`。刻意 hard import（與上面能力
# 提供者不同）：判讀原語給 fallback stub 等於讓同一份字面有第二個家、用錯答案靜默通過。
# 下面 11 個在本檔內一次都不會被呼叫，是給 `tools/session_resume_planner.py`（`guard.
# <name>` 取用）的純再匯出——刪任一個都會在無人看管的排程路徑上 AttributeError。
```

**⑨ `NO_WINDOW`／`quiet_python` 段：**

```
#: 無 console 父行程下 spawn 子行程的**防彈窗**兩層防線（`NO_WINDOW` 旗標 ＋
#: `quiet_python()` 載具）唯一的家＝`tools/lib/win_spawn.py`（R84／C8 的減法）。
#: 搬走的理由與 `quota_limits` 那一格逐字同構：那是一個完整主題，且本檔此前是它的家
#: 而 lib 反過來 import hook（方向倒了，`quota_meter.py` 因此留過第二份字面）。
#: **刻意沒有 try/except**（同 `quota_limits` 判例）：原語不能有 fallback stub，
#: 給 `NO_WINDOW` 一個 `0` 的備援等於在 Windows 上用錯的答案靜默通過（旗標沒帶、
#: 視窗照彈）。`session_resume_planner` 以 `guard.NO_WINDOW`／`guard.quiet_python()`
#: 取用 ⇒ 這裡 import 回本檔命名空間，呼叫端與既有回歸鎖一個字都不必改。
```

**⑩ `PS_UTF8_PRELUDE` 段：**

```
#: 🔴 送進 `powershell.exe`（5.1）的每一段腳本都要以這一行開頭——PS 5.1 以主控台
#: codepage（zh-TW＝cp950）寫 stdout、Python 這一側以 UTF-8 讀 ⇒ 取證憑證
#: （`next_run_time`）逐位元組降解卻仍非空＝取證規則照樣判綠。立案實測（哨兵稽核
#: jsonl 逐字）與「三個消費者為何同住本檔」的選址理由逐字保全於
#: `CrossPlatform_R91_Scan_Findings.md` §A-7（R92 搬出）。
```

**⑪ `compact_boundary_count()` docstring 全文：**

```
    """本 session 逐字稿裡 `type=="system" and subtype=="compact_boundary"` 的累計次數。

    🔴 R92／D3（SD 複審 P1）：harness 免費寫進逐字稿、`scan_transcript()` 此前沒讀過的
    「已 compact 幾次」訊號，`latch_key` 靠它重新武裝。獨立成一支函式而非併入
    `scan_transcript`（後者三元組回傳值已有多個三元解包呼叫端）。完整立案敘事與
    `compactMetadata` 欄位形狀見證據檔 §I-10（R92 搬出）。
    """
```

**⑫ `used_of()` docstring 全文：**

```
    """單筆 `message.usage` 的當前 context 佔用；`None`＝這筆不是可用的 usage。

    刻意只認 `int`（`bool` 也排除——它是 `int` 子類，混進來會讓 `True` 算成 1）：
    欄位缺一律當 0，但整筆一個欄位都沒有時回 `None`，讓「量到零」與「量不到」
    分得開。這兩者混同正是本 repo 反覆踩到的 fail-open 形狀。
    """
```

**⑬ `scan_transcript()` docstring 全文：**

```
    """逐行掃 jsonl，回 `(最後一筆 used, 歷來最大 used, 最後一個實際跑過的 model)`。

    model 一起掃出來是為了 window 判定的**交叉否決**（見 `window_from_model`），
    而且它必須與 usage 同一趟掃完——逐字稿會長到數十 MB，本檔每次工具呼叫都會跑。
    `<synthetic>` 這類佔位值不採計：它認不出家族，留著只會稀釋否決的鑑別力。

    刻意**逐行覆寫 last** 而不是整檔 `json.loads` 後排序（append-only 檔會長到數十
    MB，每次工具呼叫都跑一次）：①`"usage"` 子字串預篩省掉多數 `json.loads`；
    ②記憶體 O(1)；③壞行直接跳過（半截尾行不得讓整支守衛崩潰）。歷來最大值是
    window 下界推論的唯一輸入，必須整檔看過，不能只看尾巴。"""
```

**⑭ `model_family()` docstring 全文：**

```
    """取 model 字串裡的家族字（`opus[1m]` → `opus`；`claude-opus-5` → `opus`）。

    只用來做**交叉否決**（設定寫的與逐字稿實際跑的是不是同一族），不用來判 window。
    回空字串＝認不出來 ⇒ 呼叫端一律當「無法否決」處理（不敢否決就不否決）。
    """
```

**⑮ `window_from_model()` docstring 全文：**

```
    """設定層 model 欄推出的 window；`None`＝這一階說不出話（往下一階走）。

    交叉否決：`observed`（逐字稿裡實際跑過的 model）認得出家族、且與 `hint` 的家族
    不同 ⇒ 放棄。少了它，一次 `claude --model sonnet` 覆寫就會讓分母偏大五倍。
    `<synthetic>` 這類佔位值認不出家族，會落在「無法否決」那一側，不誤殺。
    """
```

**⑯ `session_id_of()` docstring 全文：**

```
    """逐字稿檔名（去副檔名）即 session id；非英數字元一律換成 `-`。

    清洗不是裝飾：這個字串會變成暫存檔名的一部分，未清洗的路徑分隔符會讓
    state 檔寫到別的目錄去（或在 Windows 上直接寫檔失敗）。
    """
```

**⑰ `repo_root()` docstring 全文：**

```
    """monorepo 根。`CLAUDE_PROJECT_DIR` 由 Claude Code 注入，缺席時以本檔位置推。

    以檔案位置為主要依據（`.claude/hooks/<本檔>` ⇒ 上溯兩層）而不是 cwd：cwd 由
    註冊面的 shim 決定，那是別人的實作細節，被改掉時本檔不該跟著壞。
    """
```

**⑱ `settings_chain()` docstring 全文：**

```
    """Claude Code settings 檔，**由高優先到低優先**。

    刻意不含 enterprise policy 層：那一層的路徑隨 OS 而異、且本檔讀它也沒有意義
    （它只會讓分母更小＝更早喊，而更早喊本來就是安全方向）。誠實劃界：`--settings`
    旗標與 `/model` 的 session 內覆寫本檔看不到，這也正是 `window_from_model` 要用
    逐字稿實跑 model 做交叉否決的原因。
    """
```

上述十八段搬出後，檔內原文改寫為精簡版 WHY（各自留一行指標指回本節），語意不變、
只是把「歷史沿革／展開版敘事」搬出主檔；每個函式／模組仍保留至少一句判準 WHY，
不是淨刪除。逐字比對見本輪 commit 的 diff（`.claude/hooks/context_budget_guard.py`）。

同批 Dev-S8b 修復（D32b-1a／A4-REDUNDANT-FEED-READ；非史料搬遷，是行為修復）：
`main()` 此前對同一次工具呼叫會呼叫 `read_context_feed()` 兩次——一次在
`window_evidence()` 內部（供分母判定），一次在 `cross_check_note()` 內部（供分子
交叉比對）。修復後 `main()` 只讀一次，`window_evidence()`／`cross_check_note()`
改為接受呼叫端傳入的 `feed` 字典（缺席時仍各自讀一次，向後相容既有呼叫端如
`tools/session_resume_planner.py`／SDD `context_window.py` 的既有呼叫形態不必改）。
`tools/lib/harness_feed.py`（新檔）承接同型修復到 `tools/session_resume_planner.py`
的 `measure()`。

同批 D32b-3（`read_context_feed()` 的 `reason` 真的被消費）：`cross_check_note()`
在 feed 未採用時把 `reason` 印出來（沒有 feed 檔本身也拆成獨立 reason「無 feed
（statusLine 未設定或本 session 尚無 assistant 訊息）」，不再與「壞 JSON」共用同一句
「feed 不存在或壞 JSON」）；`tools/lib/harness_feed.check_lines()` 把同一份判準
帶進 `--check`；SDD `context_window.Measurement` 新增 `harness_reason` 欄位，
`session_start.py` 的 `[SDD-CTX]` 量測行附上這句話。

效能量測：本輪修復不改變 I/O 次數的數量級（消除的是「同一次工具呼叫內的重複讀
同一個 feed 檔」，屬常數級微優化），故不重跑 Dev-A7 已完成的 10 次中位數量測。


---

## 第七輪 史料搬遷（Dev-Trim8；護欄層行數搬史料抵銷）

DEF-200-275 第七輪：合法新增使護欄層行數棘輪轉紅（98211→98730，+519）。本包在 15 支
`tools/tests/*.py`（`test_archive_defect_log.py`／`test_run_root_unittests.py`／
`test_windowsapps_guard_cross_consistency.py`／`test_check_script_parity.py`／
`test_check_wrapper_thinness.py`／`test_bash32_compat.py`／
`test_subprocess_encoding_hygiene.py`／`test_ps_engine_ssot.py`／
`test_install_windows_nightly.py`／`test_pre_commit_dispatcher_sigpipe.py`／
`test_windows_forbidden_filename_parity.py`／`test_find_git_bash_parity.py`／
`test_workflow_permission_concurrency_lock.py`／`test_bash_probe_spec_contract.py`／
`test_negative_existence_claims_r82.py`）把「事故經過／輪次沿革／方法論選擇」的完整
敘事濃縮為一句 WHY＋本節指標，判準／斷言／常數／字面值皆未動；淨減 ~628 行。

🔴 誠實劃界：本檔動工前已 259893 bytes（逼近 `oversize_problems()` 262144 上限，
餘裕僅約 2KB），結構上容不下逐字原文複本，故不在此重貼；逐字原文請對上列各檔用
`git log -p` 現查。逐檔漂移待收尾窗口以 `--print-guard-lines` 重釘。
