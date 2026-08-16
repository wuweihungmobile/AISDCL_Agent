# CrossPlatform R91 — 掃描發現與護欄層重釘證據

> **本檔的資格**（為何它屬於 `_GOVERNANCE_DOCS` 具名治理文件）：它是 R91 兩件事的
> **唯一還能重驗的地方**——①`.claude/hooks/context_budget_guard.py` 依「護欄層史料搬遷」
> 慣例（記憶 `feedback_guard_growth_offset_by_moving_lore`）搬出的模組層史料原文；
> ②「兩個相接的 JSON 物件會不會讓訊息一起消失」那組**真跑實驗**的逐字輸出。
> 兩者都逐節寫出「某段原文現居本檔某節」的座標宣稱（⇒ 指針稽核），且複審者要判
> 「搬出去的是史料還是判準」就得讀完它（⇒ 體積守門）。

---

## §A 由 `.claude/hooks/context_budget_guard.py` 模組 docstring 搬出的史料（逐字保全）

搬遷原則（與 R89／R90 同一句話）：**判準與判準的理由一行都沒搬**，搬的是
「哪一輪發生過什麼／當時量到多少」這一類**輪次史料**，以及**已經過期的量測值**。

### §A-1 「實查四處」的完整清單（原 docstring〈WHY〉節）

> 掌舵者連續多輪指名要兩件事：「注意上下文是否超出 90%，進行 /compact，不要爆」與
> 「注意 Token 限制，適當進行排程再喚醒繼續處理」。實查**四處**：
>
> * 根 `.claude/settings.json`：SessionStart/PreToolUse/PostToolUse 全部條目裡
>   沒有任何一支在看 token 或 context；
> * `AutoClaude` Kernel 的 Token Guard（≥80% `/compact`、≥90% checkpoint ＋
>   `scheduled_resume_at`）活在 **playbook 執行迴圈**裡，對 Claude Code session
>   本身一行都不生效——它守的是被驅動的那個東西，不是驅動者；
> * 根 `CLAUDE.md`〈Token 將耗盡時的「無害暫停 → reset 後重啟」SOP〉是**純人工程序**；
> * 🔴 **第四處＝harness 自己**（R79 補上；R78 版的這段 docstring 逐字寫「實查三處」
>   而漏了它，等於在說「沒人在自動 compact」——與磁碟不符）。實測 `claude --version`
>   ＝2.1.223、`claude --help` 有 `--autocompact <auto|tokens>  Auto-compact window
>   size (auto, or 100k–1M tokens)`；二進位內的開關判定逐字是
>   `if(DISABLE_COMPACT)return!1; if(env.DISABLE_AUTO_COMPACT)return!1;
>   return config("autoCompactEnabled", true)` ⇒ **預設開啟**。

🔴 **搬出理由**：`2.1.223` 是一個**會過期的量測值**（R91 當下實際跑的已是另一個版本），
而過期的量測值住在契約文件裡會被下一個讀者當成常數——本 repo 已為此下過多次判詞
（R73 把一台機器的安裝路徑寫成常數、R79 把 reset 視窗的觀測值寫成常數）。
留在 hook 檔頭的是那四處實查**今天仍在約束行為**的兩句結論。

### §A-2 「純文件約束對當下的模型零攔阻力」的立案量測

> 而「純文件約束對當下的模型零攔阻力」在本 repo 已被實證：`block_bash_on_windows.py`
> 那條規則寫進 CLAUDE.md 之後，同一個回合內仍再犯一次；換成 PreToolUse hook 之後
> 一次嘗試、一次攔下。水位這件事同型且更嚴重——CLAUDE.md 由 session **開場**載入，
> 而「現在幾 % 了」是每回合都在變的量，靠模型主動想起來去算它，正是決策負荷第一個
> 擠掉的東西。姊妹檔 `lint_powershell_command.py` 的立案量測寫得更直白：**有觀測者
> 的規則違規 1 次且被當場擋下，沒有觀測者的規則違規率 20~35%**。context 水位在本檔
> 出現之前是「沒有觀測者」那一類。

### §A-3 R79 重寫 context window 判定時的缺陷實況

> 🔴 context window 判定（R79 重寫——R78 版在本機模型上結構性保證在真 90% 靜默）
>
> R78 版只有兩階（環境變數 → `peak > 200K` 推論 → 保守下界 200K）。它在**掌舵者自己
> 這台機器**上的實測後果，是這支守衛存在的理由被完全抵銷掉：本機 user 層 settings
> 的 `model` 欄是 `opus[1m]`（1,000,000），而守衛拿 200,000 當分母 ⇒ 真實 15%／18% 各
> 誤喊一次 75%／90%，把兩個閂鎖同時燒掉；等 peak 越過 200K、window 翻成 1M 之後，
> **到 99.9% 都不會再出聲**。誤報那一半 `settings.json` 承認過，「誤報會把真報一起吃掉」
> 那一半沒有。兩件事各自要修：分母要對、閂鎖要能重新武裝。

### §A-4 與 SDD `context_ledger` 分工論證的逐條實查數字

> repo 內確實已有一套帶 90% 門檻的 context 機制，而且**已經橋接在根註冊面上**：
> `AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/context_ledger_pre.py`（各版目錄各一份），
> 經根 `.claude/settings.json` 的 `sdd_hook_router.py` 以 `context_ledger_pre`／
> `context_ledger_post` 掛在 PreToolUse／PostToolUse。實查其常數：`WARN_RATIO = 0.85`／
> `AUTO_COMPACT_RATIO = 0.90`／`CRIT_RATIO = 0.95`（95% 發 `permissionDecision=deny`），
> 分母 `MAX_CONTEXT` 來自 `SDD_MAX_CONTEXT`、預設 200000。**它不該被廢、也不該被改**
> （30 個版目錄、Copy-on-Evolve 凍結、FSM 有依賴）。
>
> 本檔與它**量的不是同一個東西**，三點皆逐項實查過：
>
> * ① **估算 vs 實測**：ledger 的分子是 `_estimate_tokens(tool, tool_input)`，
>   委派 `conversation_ledger.estimate_tool_tokens`，回退 `len(text) // 4`。
>   它的輸入**只有 tool_input**——看不到工具**輸出**、subagent 回傳、對話本身、
>   system prompt，而真正把 context 撐爆的正是那些。本檔的分子是逐字稿裡
>   API 自己回報的 `message.usage`，是實測值。
> * ② **生效條件不相交**：router 以 `SDD_ACTIVE_VERSION` 為守衛，未設時
>   PreToolUse／PostToolUse **完全靜默放行**（SessionStart 印一行 dormant 提示）。
>   純 AutoClaude／monorepo 根 session（＝本檔要守的那一種）ledger 一行都不跑。
> * ③ **分母不同**：ledger 的分母是 SDD 專案的 Stage 預算，不是 Claude Code 的
>   context window。兩者同為 200000 是巧合（一個是預設值、一個是保守下界）。

🔴 **搬出理由**：那是**另一支檔的實作細節**（版號、三個常數的字面值、函式名），抄在
hook 檔頭就是同一份知識的第二個家，而只有這一份會過期。留在 hook 的是分工結論與
「標示而非收編」那個處置。

### §A-5 `arm_quota_wakeup` 的 R83／W2-A 沿革（含它在同一輪內就轉假的那兩句）

> 🔴 R83／W2-A 的射程，以及**這一段自己在同一輪內就轉假的那兩句**（原文保留為沿革，
> 照本 repo 體例逐字訂正而不是靜默刪掉）：
> `posix` 這個鍵的語意是「這台機器沒有排程載具」，它現在由 `_has_carrier()` 決定
> ⇒ **mac 上它變成 False**，因為 mac 現在真的武裝得起來（launchd）。**這一句仍然為真。**
> 原文接著寫的是：`tools/lib/quota_gate.py::quota_halt_message` 在 `posix=False and armed`
> 那一支印的取證指令逐字是 `Get-ScheduledTask …`（mac 上不存在），而「那一檔不在本包的
> 授權範圍內…故只在這裡具名登記、**不偷改**：訊息會指錯路」。
> 🔴 **兩句在本輪內都已為假**（複審 SD／FC-1 逐字判過，我複驗）：同一棵工作樹的
> `tools/lib/quota_gate.py` 已由 R83／F2-② 就地訂正——`evidence_hint()` 委派給
> `schedule_backend.select().evidence_hint()`。收斂當回合實跑 `quota_gate.evidence_hint()`
> 在 darwin 上的輸出含 `launchctl print gui/501/<label>`，
> `contains 'Get-ScheduledTask': False`／`contains 'launchctl': True`。
> 留著它的代價不是文字難看：**下一個人會照這段散文去修一個已經修好的東西**，
> 或反過來相信 mac 的取證指引還是壞的。

### §A-6 預防性哨兵觸發時機（R82／HELM-02）的立案量測

> 🔴 R82／HELM-02 訂正本段的**時機**（方向不變、理由不變，改的是「在哪一刻按下去」）：
> 下面整段論證的是「非預防性武裝不可」，那一半今天仍然成立、一個字都沒被推翻。被推翻的是
> 它的實作把「預防性」等同於「SessionStart 就註冊」——掌舵者當場截圖回報排程器裡三支
> `AutoSDD_Sentinel_*`，實測其中兩支屬於**活了 5 秒與 12 秒**的短命 session。
> 延後的代價已界定：一個 8 分鐘就結束的 session 拿不到續航；而它換掉的是
> 「每一支 5 秒探針都留一支每 15 分鐘醒來的排程」。
> 🔴 為什麼判準不能寫在 SessionStart 那一刻：那一刻逐字稿往往還不存在，
> 手上沒有任何可以量的東西；而 payload 欄位分不出主 session 與探針（實測六支短命逐字稿
> 與主 session 結構同形，差別只在規模）。

### §A-7 `PS_UTF8_PRELUDE` 的立案實測與選址理由（R92 由該常數旁註解搬出；〔〕內為搬出時的編者改字，其餘逐字）

> 立案（掌舵者當回合實測，哨兵稽核 jsonl 逐字）：`"next_run_time": "2026/8/9 �U�� 07:14:19"`
> ——`Get-ScheduledTaskInfo` 的 `NextRunTime` 由 `Format-List` 以**當前文化** zh-TW 算繪成
> 「下午」，PS 5.1 把它以主控台 codepage（本機 cp950）寫進 stdout，而 Python 這一側以
> `encoding="utf-8"` 讀 ⇒ 逐位元組降解成 `?`。後果不只難看：那個字串是**取證憑證**
> （`next_run_time`），而降解過的憑證仍然非空 ⇒ 取證規則照樣判綠，只是它記下來的時刻
> 人再也讀不出來。同族問題本 repo 已有 `init_utf8_streams()`（Python 那一側）；這一格是
> **PowerShell 那一側**缺的那一半。
> 放在〔該檔〕而不是各自為政：`session_resume_planner`／`sentinel_lifecycle`／`console_spawn_watch`
> 三個消費者，前兩者已經在向該檔取 `NO_WINDOW`／`quiet_python()`，同一族知識同一個家。

### §A-8 合成記錄（`<synthetic>`）為何整筆退出用量累計（R92 由 `scan_transcript` 內註解搬出；〔〕內為搬出時的編者改字，其餘逐字）

> 🔴 R79：合成記錄整筆退出**用量累計**，不只是退出 model 判定。
> harness 在額度耗盡時寫進逐字稿的那一筆長這樣：`type=assistant`、
> `model=<synthetic>`、`isApiErrorMessage=true`，而它的 `usage` 三欄
> **都在、且都是 0**（全庫實測 135 筆，無一例外）⇒ `used_of()` 依約回 0
> 而不是 None（「欄位在」就算量到），於是 `last` 被它覆寫成 0。
> 後果不是少算一點：水位在**額度耗盡的那一刻**由真值掉成 0.0%、tier 變
> None、守衛整支靜默——而〔硬線〕那一支正是負責寫「可重啟點任務書」的那一
> 條路（`write_resume_plan`）。也就是說最需要任務書的那一刻，恰好是它
> 結構上不會被產生的那一刻。這是「量不到 ≠ 量到零」在**上游**又犯一次：
> 那筆記錄根本不是一次模型呼叫，它的 0 不是用量，是佔位。

---

## §B 「兩個相接的 JSON 物件」真跑實驗（本輪，`DEF-200-135` 的關鍵前提）

**要回答的問題**：`emit_to_model()` 一定要把多則訊息**併成一份** JSON 嗎？還是兩份
相接的物件 CC 也吃得下？這決定了「一行程至多發射一次」是硬約束還是潔癖。

**載具**：臨時專案目錄（`/tmp/r91emit*`，**repo 內零改動**）＋各自的 `--settings`，
hook 以 `python3` exec form 掛上，`claude -p --model haiku` 非互動跑一次。
兩組唯一差別是 `EMIT_N`（印 1 個或 2 個 `hookSpecificOutput` 物件）。

### B-1 第一次量測（`UserPromptSubmit`）——**結果作廢，因為載具本身有混淆**

| 組別 | 印出的物件數 | 模型回覆 |
| :-- | :-- | :-- |
| 單物件 | 1 | `TOKEN=ALPHA` |
| 雙物件 | 2 | `TOKEN=ALPHA` / `TOKEN=BETA`（兩則都收到） |

🔴 **這組不能當結論**：`UserPromptSubmit` 的契約是「**純 stdout 也會被加進 context**」
⇒ 就算 JSON 解析失敗，文字仍會以原樣進去。也就是說這個載具**結構上量不到**
「parse 失敗會不會讓訊息消失」。這正是本 repo 的既有紀律「驗證載具本身要被驗證」。

### B-2 第二次量測（`PostToolUse`＝本案真正的事件）——**這組才算數**

| 組別 | 印出的物件數 | 模型回覆 |
| :-- | :-- | :-- |
| 單物件（控制組） | 1 | `TOKEN=ALPHA` |
| **雙物件（注入組）** | 2 | **`TOKEN=NONE`** |

⇒ **兩個相接的 JSON 物件 ⇒ 兩則訊息一起消失**，而失效外觀（模型沒反應）與
「水位很低所以沒人說話」完全相同。SD 預測為真。

⇒ 設計後果（已落地）：`tools/lib/platform_utils.py` 的 `emit_to_model()` **只累積、
不輸出**，輸出集中在 `flush_to_model()`，production 只有 `atexit` 一個 flush 站點
（鎖＝`tools/tests/test_context_budget_guard.py::SingleEmitterHasOneFlushSiteTest`）。

### B-3 併入真的會發生（不是假想）

落地後對 hook 做一次真跑（context 80% ＋ 額度快取不可用）：同一個行程裡有**三個**
發言者（`no-credentials-darwin` 降級、`no-cache` 降級、context 75% 提示），stdout 上
恰好一個 JSON 物件、三段文字都在 `additionalContext` 裡。

---

## §C 護欄層重釘（`_GUARD_LINES_REPIN_LOG` 的 R91 列指名的逐檔清單）

<!-- guard-total:R91 --> **本輪護欄層累積淨額＝ 83739 → 84149（+410）** —— 成長面全數落在
`tools/tests/test_context_budget_guard.py`（送達形態鎖／warn 帶取樣與閂鎖兩條／PRD 前置條件
三條／PRD↔band 對映三條／單一 flush 站點三條／逃生口宣告一條，另含 `_run_hook3` 與
`tearDownModule`）。三條合法出口逐條實查後才重釘：

1. **刪死碼＝0**：新增的每一個 helper（`_emitted`／`flush_site_problems`／`_run_hook3`）
   都有實際消費者，實查零孤兒。
2. **搬史料**＝**已用**：本輪把 `.claude/hooks/context_budget_guard.py` 的模組史料搬進
   本檔 §A（六節），該檔 raw 由 **1072 → 1085**（新增功能 ＋ 判準 ＋ 註解淨增 13 行，
   而不是 +40）。🔴 但那是 **hook 那一側**的減法，**不在護欄層行數棘輪的量測面內**
   （棘輪只量 `tools/tests/*.py`）⇒ 它抵銷不了本表的淨額，這一點照實記。
3. **抽共用層**：本輪確實抽了（`platform_utils.emit_to_model`），但抽走的是 **production**
   程式碼不是判準；判準本體（送達形態、PRD 前置條件）留在測試面是正確位置。

**分桶棘輪**：`prose` 4009→**4011**（上限 4119）、`guard_self` **3545**（上限 3545，**餘裕 0**）
——落地後現查值由 QA／R91 複審量入（原文留的是「（見下方實測）」佔位符而下方沒有實測，
那正是本 repo 判過的「佔位符空結果」；量測含複審自己的兩處 docstring 訂正）。新增測試的
docstring 一律參照 `.claude/hooks/context_budget_guard.py`／`tools/lib/platform_utils.py`
（`root_infra`，growth-allowed）或同時參照多棵樹（`mixed`，不進任何 shrink-only 桶），
刻意**不**只講 `tools/tests/`。落地前後各量一次 `measure_shrink_only()`。

**代價側**（款(10)~(12)）：R91 是款(12) 的到期輪 ⇒ 單輪上限已由 2000 下修至 **1600**
並就地重新武裝下一段（`_REPIN_NET_CAP_SCHEDULE` 追加 `(91, 1600)`，
`_REPIN_NET_CAP_DUE_ROUND`／`_REPIN_NET_CAP_DUE_TARGET` 一併前推）。
連升 streak：R89 的 -92 已歸零、R90 +161 為第 1 輪、本輪為第 **2**／2 輪
⇒ **R92 必須出現一次淨額 ≤ 0**，否則款(11) 當場紅。

<!-- guard-total:R91 --> 護欄層累積總量現值 **83739 → 84149（+410）**；逐檔清單即本節。

---

## §J 護欄層重釘（`_GUARD_LINES_REPIN_LOG` 的 R92 列——SD 複審 D3/D2/D4 修復包）

<!-- guard-total:R92 --> **本輪護欄層累積淨額＝ 84149 → 84247（+98，移動樹讀數）** ——
新增 `test_context_budget_guard.py` 的 `CompactBoundaryLatchTest`（D3 三步驟 probe 迴歸鎖）
與 `AutocompactPostureTest` 補三條（D2 first-wins 迴歸／D4 pct-vs-硬線），同批把等量
既有長篇 docstring 史料搬進本檔 §I-13～§I-17（逐字保全，原站點留一行指標）；本表自身
（`test_adr_xplat001_c1c2_lock.py`）也是掃描面成員，追加稽核列使其自身增行。
🔴 **本列數字是移動樹讀數，非靜止樹憑證**：本包全程只編輯 `test_context_budget_guard.py`
與 `test_adr_xplat001_c1c2_lock.py` 兩支，但同一工作階段內至少有一個並行包
（`test_quota_policy.py` 於本包完全未碰的情況下 1934→2025，+91）與本包不明歸屬的外部
因素持續改動 `test_context_budget_guard.py` 本身（本包自身編修量約 +9~+15，實測磁碟值
卻在同一階段內多次上移，最終落在 6880）——本檔在本包工作期間並非靜止樹。連升 streak
（R89 -92／R90 +161／R91 +410）要求的「R92 必須出現一次淨額 ≤ 0」**未能在本輪由本包
單獨滿足**：本包自身淨額原可收斂到 0（已完成的搬史料抵銷即為此），但外部並行增量使
最終磁碟值偏離。依本表既有紀律「重釘一律由收尾包在所有包停工後做一次」，本列僅為現查
快照，最終數字（含「R92 必須淨額 ≤0」是否成立）須由收尾窗口在全部包停工後的靜止樹上
重新現查並覆寫本節兩個標記行。

<!-- guard-total:R92 --> 護欄層累積總量現值 **84149 → 84247（+98，移動樹讀數，待收尾窗口
覆寫）**；逐檔清單即本節。

---

## §D 本輪未做到的事（誠實劃界）

* **`AUTOSDD_GIT_GUARD_OFF`／`AUTOSDD_CLAIM_GUARD_OFF` 仍不在 `quota_policy.ENV_SPEC`**
  ⇒ 它們從 `.env` 到不了（R82／C2 那條路對這兩個逃生口不成立）。本輪的
  `EveryHookEscapeHatchIsDeclaredTest` 射程刻意只涵蓋 `context_budget_guard.py`：
  把那兩個一起納入會製造兩筆今天無人負責的紅，而那種鎖活不過一輪。
* **`.md` 面的 `flush_to_model` 呼叫站點判準只掃 `.claude/hooks/` 與 `tools/lib/`**
  ⇒ 別處（例如 `tools/*.py`）多一個直接呼叫不會紅。今天那些檔一個都不 import 它。
* **閂鎖「每 5 個百分點重新武裝」未做**（與本案正交，且會打紅具名鎖
  `LatchRearmTest::test_the_same_tier_and_window_still_only_fires_once`）。入場券已備妥：
  `WarnBandLatchTest::test_a_single_session_climbing_the_warn_band_speaks_exactly_once`（R92 隨閾值 75/90→84/94 改名，樣本由 76~89 改 84~93；語意不變）
  把現行行為釘成契約，那個提案一落地就必須先讓它轉紅。
* **PostToolUse matcher 擴面未做**：單次觸發實測 ~280 ms，其中掃逐字稿只佔 ~13%，
  ~240 ms 是行程啟動＋import ⇒ 正解是先壓固定成本，不是加工具名。
* **帳本 33 列 R90→R91 的批次改派未逐列複驗真實狀態**（`DEF-200-136`）；該面由仍 open
  的 `DEF-200-106` 承接。

---

## §E R91 結案包：五列的當回合複驗證據

> 本節是 `AutoSDD_Defect_Log.md` 五列結案的**唯一**可重驗載體：那五列受 `ROW_MAX_BYTES`
> 限制（結案前逐列餘裕 13~209 bytes），狀態欄只放得下索引 ⇒ 判「這幾筆結案是不是真的」
> 只能讀本節。全部數字都是本輪當回合真跑的原始輸出，非轉述。

### §DEF-200-126（`fixed@R91`）— 三個只寫不讀的 `_port_*` 已隨 R90 包 C 拆除

該列自書「本列僅立案；包 C 落地回報後由主控裁決是否同輪轉 `fixed`」⇒ 本輪做的就是那次裁決。

* `grep -n "_port_" AutoClaude/autoclaude/execution/playbook_runner.py` → **零命中**
  （立案時三筆 `ctx=Store` 屬性皆在）。落地載體＝commit `982adf4`（R90）。
* 同檔 `:109-113` 現為拆除紀錄，逐字寫「四者**全部只寫不讀**（AST 掃 502 檔，三筆 port
  屬性皆 ctx=Store 零 Load；`._evaluator` 全庫零讀取），已拆除」，並把真正的 executor DI
  指回 Kernel 那條路（`main.py` → `build_kernel(executor=…)`）⇒ 該列點名的**誤導修法**
  這個危害面已不存在。
* `python -m pytest tests/test_gap014_020.py tests/test_gap039_049.py -q` →
  `83 passed in 10.93s`，rc=0。

### §DEF-200-127（`fixed@R91`）— skip reason 的錯誤指路已訂正，patch 層已落地

* `AutoClaude/tests/helpers/fake_pty.py` 存在且**已追蹤**（`git ls-files --error-unmatch`
  rc=0）；`test_gap014_020.py:41`／`test_gap039_049.py:27` 於 module 層 import
  `fake_pty, hermetic_runner`。
* 立案座標 `test_gap014_020.py:103`／`test_gap039_049.py:59` 的 skip reason **已不存在**
  （該兩行現分別是 `_mock_response()` 與 `_write_playbook()`）。兩檔檔頭 `:45-53`／`:30-33`
  改記「11 支在兩平台都跑得到」「斷言零修改」，且逐字指出**該列判定的那句錯誤正解**
  （「make_service 重寫」）住 `tests/helpers/fake_pty.py` 的 docstring ⇒ 錯誤指路已被反向
  登記，不是被抹掉。
* `pytest` 兩檔 → `83 passed in 10.93s`，rc=0。

### §DEF-200-130（`fixed@R91`）— 平台綁定債登記表與真探針皆在，且有牙

該列分流欄自書「已落地」，只因包 E 禁碰帳本才由 R90 收尾窗口代寫成 open。當回合逐項複驗
（`AutoClaude/tests/test_conftest_windows_native_skip_report.py`）：

* `_PLATFORM_BOUND_DEBTS`（`:366`）／真探針 `probe_pgvector_bge_m3_staging()`（`:310`）／
  三態常數 `UNMEASURABLE`（`:277`）皆在；未登記的平台條件即紅（`:511`）、債還完仍留探針
  也紅（`:519`）＝雙邊咬人。
* 注入自證仍在（`test_injection_unmeasurable_is_not_read_as_not_payable`、
  `test_injection_real_probe_reports_unmeasurable_when_the_query_dies`）。
* `python -m pytest tests/test_conftest_windows_native_skip_report.py -q` →
  `23 passed in 3.93s`，rc=0。
* 分流欄留的可裁項（`unmeasurable ⇒ 紅` 是 fail-loud 判斷非實測結論）本輪裁決＝**維持**，
  理由是它與本 repo 通則「量不到 ≠ 量到零」同向；改成放行才需要新證據。

### §DEF-200-010（`fixed@R91`）— act 前置的「先 pull 再 build」已落到磁碟

該列立案時自陳「磁碟上未落任何站點」，分流欄指定的處置就是把解法寫進 act 前置。

* 落地站點＝`ONBOARDING.md` 的 Docker 那一列（act 前置的既有站點，與原有的
  「Apple Silicon 走 QEMU」說明同住一格）：新增「先 `docker pull <基底映像>` 再 `docker build`」
  ＋失敗字面 `DeadlineExceeded` ＋「buildkit 的 deadline 涵蓋拉基底與 RUN 層整段」的因果。
* `useMacWin.md` 只放**指針**、不抄第二份：該檔 `:202` 已對 PG 立過「唯一站點，本檔不重抄，
  避免第二個會漂的家」的判例，本列沿用同一條紀律 ⇒ 分流欄寫的兩個檔都有交代，而知識只有
  一個家。

### §DEF-200-097（`fixed@R91`）— 政策鍵不再被渲染成開關

走該列分流欄二擇一裡的**改結構歸類**（另一條「改渲染分節」需新增區段標題常數與分支，而
`tools/lib/quota_policy.py` 的 `guardrail_lib` LOC 餘裕實測為 0）：

* `AUTOSDD_QUOTA_FANOUT_CAP` 的 `section` 由 `escape` 改 `policy` 並上移到政策區尾；理由逐字
  寫在該處註解：逃生口關掉的是守衛，而本鍵永遠只收緊（`min(cap, override)`，見
  `fanout_cap()`），一個字都關不掉 ⇒ 兩者不同族。
* 連帶訂正同檔 `AUTOSDD_CONTEXT_SIGNAL_OFF` 上方註解的「**第五個**逃生口／上面四個」為
  「**第四個**／上面三個」——不改它，本輪就會在修一句假話的同時製造另一句。
* `.env.example` 依生成器重生（該檔不得手寫，`test_the_disk_copy_is_in_sync` 守著）。
* 當回合實測：`python tools/lib/quota_policy.py --print-env-example` rc=0，該鍵已印在政策區、
  不再夾在兩個 `_OFF` 之間；`python -m pytest tools/tests/test_quota_policy.py -q` →
  `146 passed, 292 subtests passed in 0.37s`，rc=0；
  `python -m pytest tools/tests/test_context_budget_guard.py tools/tests/test_pre_commit_dispatcher_sigpipe.py -q`
  → `400 passed, 8 skipped, 201 subtests passed in 25.08s`，rc=0；AutoClaude 側
  `tests/test_r82_quota_axis_and_shipped_defaults.py` ＋ `tests/contract/test_loc_budget_tiered.py`
  → `128 passed in 2.11s`，rc=0；`python AutoClaude/tools/check_loc_budget.py` rc=0
  （`quota_policy.py` 仍 `loc=400`／budget 400／headroom 0，**未動任何門檻**）。

## §F R92 結案輪：六列逐列實測結案（結案單人窗口）

> 帳本列受 `ROW_MAX_BYTES=700`（四列貼線、兩列在超長豁免內），狀態欄只放結案字＋索引；
> 各列的**原狀態欄逐字**與當回合實測憑證住本節。體例沿 §E（R91 結案包）。
> 本輪刻意**不新增帳本列**（新增列會把帳本時鐘推進到 R92，使數十列「承接輪次：R91」
> 的未結列當場過期而必須整批改派——那正是 `DEF-200-106` 記載的改派稅）。

### §F-059 `DEF-200-059` → closed-by-decision@R92

**原狀態欄（逐字）**：`open（承接輪次：**R91**；**改派**：` DEF-200-020 `承接輪次：**R89**）`

**結案理由**：主線（mac 闔蓋期間不會被喚醒）＝掌舵者已裁決的**已知邊界**，非待修缺陷——
根 `CLAUDE.md`〈額度耗盡〉節 R84／SA-05 段逐字載明「launchd 只在機器醒著時補跑錯過的一輪；
Windows `WakeToRun` 的對等物住在 `pmset repeat`、需 sudo、**本專案刻意不碰**（改動掌舵者
機器的電源行為已被否決）」，且「失效可偵測」交付物有機械物
`tools/tests/test_mac_endurance_r83.py::MacSleepPostureIsSaidOutLoudTest`（現查 :1512）。
分流欄兩項皆已由 R84 同輪落地：①回收臂自動觸發＝`.claude/hooks/context_budget_guard.py:777`
`spawn_sentinel_gc(sid)`（R84／C3-P4b，:785 起載明「gc() 此前零自動呼叫端」的立案與修法）；
②孤兒哨兵 `AutoSDD_Sentinel_s` 根因＝單元測試同行程走真 `spawn_sentinel`，已由 R84／C3-P4c
`tools/tests/test_context_budget_guard.py::setUpModule` 釘 `AUTOSDD_SENTINEL_OFF`（in-process
半邊）＋ `_isolated_env(real_scheduler=False)`（子行程半邊）根治。

**當回合實測**：`launchctl list | grep AutoSDD_Sentinel_` → 僅 1 筆
`AutoSDD_Sentinel_51c46404-7cc2-419e-a492-1400b39ce66a`（＝本 session 由 SessionStart 合法
武裝的哨兵），無任何 `_s` 孤兒；`python -m pytest tools/tests/test_context_budget_guard.py -q`
→ `367 passed, 8 skipped, 146 subtests passed in 17.80s`，rc=0（🔴 R93 訂正：該數字是
§F 落地當回合的量測值，隨後續輪次（R92 guard 修復＋容量自適應攤提）持續新增測試，
現查同指令為 `386 passed, 8 skipped, 146 subtests passed`，rc=0——本列宣稱本身不受
測試總數變動影響，數字僅供還原「當回合確實親跑過」，不得引用為現況）。

### §F-070 `DEF-200-070` → closed-by-decision@R92

**原狀態欄（逐字）**：`open（承接輪次：**R91**；**改派**：` DEF-200-045 `承接輪次：**R89**）`

**結案理由**：①「該掛的沒掛」確認無觀測點——該確認本身即本列的交付物，已成為根 `CLAUDE.md`
鐵律六的誠實劃界正文（現查 :355「本族另一半真的沒有觀測點：Monitor 掛沒掛、harness 的完成
通知在講哪一個行程，都不在任何指令字串裡、也永不變成 repo 內的檔案…攔截器接得住『寫出壞
形態』，接不住『該掛的沒掛』」），並由掌舵者 2026-08-11 總則（掛不掛得上事件源是**派工前**
就要決定的事）給出政策解；rc-管線 Bash 側缺口另有活載體 `DEF-200-086`（未結）。
②「`shell=True` 靜態掃描回 0 命中＝假的安心」那一半，分流欄指定的方向（執行期契約）已由
R85 落地：`AutoClaude/autoclaude/execution/evaluator.py:120` `portability_note()`（執行期
診斷）＋ `AutoClaude/tests/execution/test_shell_portability_contract_r85.py`（兩執行面射程
普查＋以真實 playbook 為母體的假紅普查；根 `CLAUDE.md` 鐵律三表 `shell=True` 列同輪訂正）。

**當回合實測**：`ls AutoClaude/tests/execution/test_shell_portability_contract_r85.py` 存在；
`grep -rn "def portability_note" AutoClaude/autoclaude/` → `execution/evaluator.py:120`。

### §F-114 `DEF-200-114` → fixed@R89

**原狀態欄（逐字）**：`open（承接輪次：**R91**）`

**結案理由**：分流欄把本列的義務明文收斂為「只訂正假 docstring；修法須動取數層需第三方
複審」。訂正已於 R89 完成且自我指認——`tools/lib/quota_meter.py` `account_posture()` docstring
現查逐字：「🔴 R89 訂正本段此前的一句假話（`DEF-200-114`）…它宣稱這個指紋的『用途是偵測
方案變更（組合變了 ⇒ 歷史標定／燃燒率作廢重學）』，而那件事一行都沒有實作」，並誠實劃界
「本輪刻意不修：修法要動 record_burn／burn_ratio＝配速取數層…需第三方複審」。
機制缺口（方案指紋變更 ⇒ 燃燒率作廢）的活載體＝`DEF-200-122`（未結，其分流欄逐字載明
「未把『軸集合／方案指紋變更』列為燃燒率作廢事件 ⇒ 屬憲法缺口，須走修憲程序」）。
「沒人看」那一半亦已改善：`tools/lib/quota_gate.py:665` `posture_line()` 每次 `--pace`
都印出方案指紋（派工前置行）。

**當回合實測**：`grep -n "plan_fingerprint" tools/lib/quota_meter.py` → :497／:516／:525；
`grep -n "plan_fingerprint" tools/lib/quota_gate.py` → :665（消費端）。

### §F-135 `DEF-200-135` → fixed@R91

**原狀態欄（逐字）**：`open（承接輪次：**R92**）：已修＝模型通道＋三態分流；未修＝§4.3 的 3pp 邊際 → DEF-200-137`

**結案理由**：本列自書的「已修」半邊當回合逐站驗實——單一發射器
`tools/lib/platform_utils.py:221` `emit_to_model()`；hook 端接線
`.claude/hooks/context_budget_guard.py:196`（import）／:1056（發射）；三態分流
`quota_gate.draining()`（`tools/lib/quota_gate.py:373`）由 :896／:1050 消費。
「未修」半邊（PRD §4.3 第二 AND 的 `COMPACT_COST_BUDGET_PP` 3pp 邊際）**全額**由
`DEF-200-137`（未結，R91 QA 複審立列）承載，本列不再持有任何未結義務。

**當回合實測**：`python -m pytest tools/tests/test_context_budget_guard.py -q` →
`367 passed, 8 skipped, 146 subtests passed in 17.80s`，rc=0（🔴 R93 訂正：同 §F-059，
該數字為當回合量測值，現查同指令為 `386 passed, 8 skipped, 146 subtests passed`，
rc=0，本列宣稱不受影響）。

### §F-238 `DEF-101-238` → closed-by-decision@R92

**原狀態欄（逐字，含跳脫管線）**：

> open（R55 部分收斂）｜🔴 R60 round 2 補《格式定義》合法首詞（原首詞非合法值，原文完整接於後）：**R55 部分收斂**：四方複審發現此收斂債已從「2 份」擴散為「5 份」（新增 `goal_freeze_gate.py`／`tools/three_tier_to_playbook.py` 兩處呼叫端各自重複宣告黑名單字面值，且彼此註解互相宣稱超集關係卻零機械驗證）。已新增 `AutoClaude/autoclaude/utils/shell_deny_chars.py` 作為 `BASE_DENY_CHARS` SSOT，改造 `sdd_to_playbook_adapter.py`／`goal_freeze_gate.py`／`tools/three_tier_to_playbook.py` 三處為 `BASE_DENY_CHARS \|` `{專屬追加字元}` 顯式聯集寫法（逐字元集合比對確認零行為變更）；**刻意不動**本列原始記載的 `execution/mutation_applier/_conditional.py`／`core/services/mutation/_conditional_evaluator.py`（CONDITIONAL 家族，白名單 regex 為主、非純黑名單機制，與本次收斂的「spec-fragment 消毒家族」執行語意不同，見 fixDescription 完整理由），故本列描述的原始缺口本身**仍 open**，僅記錄收斂範圍已擴大到的姊妹缺口已由 R55 處理完成（見 DEF-101-429）

**原分流欄（逐字）**：`下一輪一併收斂兩份白名單字元集，避免未來各自演化出更大分歧`

**結案理由**：本列的分流目標（收斂兩份 CONDITIONAL 白名單字元集）已被 R85 以**明文裁決
否決**——`AutoClaude/autoclaude/utils/shell_deny_chars.py` 檔頭現查逐字：「刻意不收斂範圍：
兩支 CONDITIONAL 白名單 regex。執行語意確實不同（shell=True 原生殼 vs shell=False+shlex.split），
故 R85 複查後**維持不收斂**」；根 `CLAUDE.md` 鐵律三表 `shell=True` 列同輪判例逐字「改白名單
語意——它是 Gap-046 資安過濾器，放寬括號＝開資安洞、收緊 test＝把資安閘變平台閘，兩軸一起壞」。
「避免未來各自演化出更大分歧」的目標改以**命名區辨**達成：兩支同名 `_SAFE_COND_PATTERN` 已
改名 `_SHELL_TRUE_COND_WHITELIST`（`execution/mutation_applier/_conditional.py:25`）／
`_SHELL_FALSE_COND_WHITELIST`（`core/services/mutation/_conditional_evaluator.py:28`），
同名不同義（「順手收斂」的誘因）已被移除。真正同源的 deny-chars 族早於 R55 收斂為
`BASE_DENY_CHARS` SSOT ＋ 機械鎖 `AutoClaude/tests/test_shell_deny_chars_parity.py`（存在，
當回合 `ls` 實查）。殘餘（安全姿態傾斜：shell=True 側較寬鬆且無黑名單、`!` 之差 SD 於 R16
已判非安全漏洞；tests/test_gap039_049.py 的字面副本無比對機械物）已逐字登記於該 SSOT 檔頭
②③段——未來任何人動這兩支 regex 都必經那個檔頭。

**當回合實測**：`grep -rn "_SHELL_TRUE_COND_WHITELIST\|_SAFE_COND_PATTERN" AutoClaude/autoclaude/`
→ `_SAFE_COND_PATTERN` 僅存於 shell_deny_chars.py 檔頭史料（:12），兩支改名後常數各居其檔；
`ls AutoClaude/tests/test_shell_deny_chars_parity.py` → 存在。

### §F-392 `DEF-101-392` → closed-by-decision@R92

**原狀態欄（逐字）**：

> open（watch item；本輪僅記錄 Architect 評估結論供人工擇期決策，未修改任何 Copy-on-Evolve 相關程式碼或政策文件；Architect 同時提出的次要建議——①將「共用抽層＋parity 鎖」正式列入 `CrossPlatform_Scan_Dimensions.md` 作為新增跨語言/跨版本重複邏輯的預設路徑、②`tools/dev_start.py`〔1772 行單檔〕仿既有薄殼模式拆分子模組——優先度較低，一併留待未來輪視需要評估，本輪不動手）。**R49 四方複審（Architect／SA／SD／QA 四方各自獨立重新查證）**：重讀 `ci-gate.sh` 第 57～71 行確認僅 `FROZEN_BASELINE=v0.01` + 動態解析 LATEST 雙軌，中間 28 份凍結版本仍不在官方閘門機械掃描範圍，未發現任何改變既有結論的新事證；兩項次要建議（`CrossPlatform_Scan_Dimensions.md` 補記共用抽層/parity 鎖、`tools/dev_start.py` 拆分子模組）複核仍未落地、確認屬既有低優先度 backlog 之自然延續、非回歸，維持 open watch item 原判，續交人工/PM 擇期決策）  🔴 R82 吸收 DEF-101-401（該列自述為本列的補記非新缺陷）：其論點＝凍結版數單調遞增，決策基期只會更貴不會更便宜，建議升級為「即排入正式 ADR 議程」。已回寫本列；DEF-101-401 依「同源事項單一載體」結案（closed-by-decision@R82），本列為唯一活載體

**結案理由**：本列唯一待決事項＝「Copy-on-Evolve 政策本身需要人工／PM 決策」。該決策已發生
且有兩個可查證落點：①**掌舵者 R84 裁決**——`AISDLC_SDD/CLAUDE.md` 現查 :16 逐字「兩份權威源
不一致時，一個必定是假的；本輪依掌舵者裁決收斂到『原地改 LATEST』」（根 `CLAUDE.md`〈路徑
陷阱〉節同輪訂正：LATEST 可原地改、中間歷史版不可改、CoE **只**在需要保留可回歸對照快照時
開新版）。這直接移除「凍結版本數隨框架演化線性增長」的根因（每次改動開新版）——當回合實測
`ls -d AISDLC_SDD/AISDLC_SDD_v0.* | wc -l` → **30**，與本列立案時（R48／30 支）及
ADR-XPLAT-001（R60 實測 30）逐字同值＝增長已停 20+ 輪。②**正式 ADR 已存在**——
`docs/04_planning/ADR/ADR-XPLAT-001-copy-on-evolve-frozen-baseline-backport.md`（狀態
Accepted）把三次破例判例＋回補分診規則固化為可執行判準（「提高逐版例外回補的機械化程度」
＝本列狀態欄列舉的三個候選方向之一，已落地）。次要建議①②各有後續載體：②（dev_start 拆分）
＝`DEF-101-398`（未結，R81 已升為必修）。註：ADR-XPLAT-001 表頭「政策層的重新評估仍掛在
DEF-101-392／401」書於 R60，早於 R84 裁決；本節即該句的下游訂正（401 已於 R82 結案）。

**當回合實測**：`ls -d AISDLC_SDD/AISDLC_SDD_v0.* | wc -l` → 30；
`grep -n "掌舵者裁決" AISDLC_SDD/CLAUDE.md` → :16；`head` ADR-XPLAT-001 → 狀態 Accepted。

## §G R92 掌舵者八項裁決——第一階段結案（單人窗口執行）

> 掌舵者對 R92 回報的八項待裁決全數拍板（前四項使用者選定、後四項授權主控代決）。
> 本階段只改既有列狀態與必要小執行，不落新帳本列、不推時鐘；各列原文逐字照錄於此。

### §G-101-243 `DEF-101-243` → fixed@R92

**原狀態欄（逐字）**：

> open（QA 二審明確判定非阻斷，記事存證排入下一輪 backlog；四方複審 Architect/SA/SD/QA 對 R18 其餘修復之獨立覆核皆確認有效）；**R22 校正**：①③經核實已 fixed@R19（見 DEF-101-244③⑤：`test_min_pass_equals_actual_step_count`、`test_win32_returns_none_without_spawning`），QA 一審 bug-injection 複驗①之語意鎖確實有鑑別力。②（README badge／CLAUDE.md 日期機械新鮮度鎖）複核後確認仍未建，維持 open，非本輪 scope ｜🔴 R81 改派，承接輪次：**R82**（本輪做不完：② 的二擇一〔補日期新鮮度告警／刪掉沒人維護的 badge〕是取捨決策，不由帳本包代決）

**原分流欄（逐字；因含殘留待辦字樣，隨結案瘦身為指針）**：

> ①排下輪：仿 `test_known_consumers_detected()`手法，替 `$MinPass` 數值本身補一條「等於步驟數」的語意鎖；②排下輪：評估是否比照 pytest 基線模式（`check_pytest_baseline_sites.py`）替這兩個日期欄位加機械新鮮度告警；③排下輪：補一個 `mock.patch.object(sys, "platform", "win32")` 的獨立測試案例

**裁決與理由**：裁決＝**刪 badge**。①③早於 R19 修畢（R22 校正核實，具名鎖 `test_smoke_ci_sync.py:354 test_min_pass_equals_actual_step_count`／`test_dev_start.py:3027`）。②的兩個標的：`AutoClaude/README.md:11` 的 sprint-verified badge（日期停在 2026-07-22，全 repo 零機械引用，當回合 grep 實查空集合）本輪已刪；`AutoClaude/CLAUDE.md` 檔尾人工日期欄已不存在——檔尾為機械生成 `<!-- ARCH_SNAPSHOT_END -->`，新鮮度由 `AutoClaude/tools/hooks/claude_md_freshness.py`（Stop hook）與 CI `claude-md-budget` job 機械守。

**當回合實測**：刪除前 `grep -n sprint-verified AutoClaude/README.md` → :11 命中；刪除後 → 零命中（見下方逐列驗證）。
🔴 **E-04 追記（同輪 Architect 複審，依同一裁決方向）**：同檔第二顆假 badge
`import--linter-8 kept` 亦已刪——`.importlinter` 實有 9 條 `name =`（根 CLAUDE.md R82 段
同載 9），badge 寫死 8＝已過期；依掌舵者「刪無人維護 badge」裁決與「條數指向 SSOT、不複寫
數字」政策，刪除而非改 9。刪後 `grep -c "import--linter" AutoClaude/README.md` → 0。

### §G-101-336 `DEF-101-336` → closed-by-decision@R92

**原狀態欄（逐字）**：

> open（如實記載此矛盾，不回填 DEF-101-056 原文，比照帳本「只增不刪」政策；是否需要為凍結版新增「禁止 commit」機械鎖列 R41 backlog 評估） 🔴 **R60 改派（round 1 QA-R60-04【1】／Scan-G G-02）**：本欄「…列 R41 backlog 評估」指向 19 輪前且全帳本家族零改派＝孤兒（判準同 `DEF-101-333`）。R60 round 2 實查該鎖仍不存在：`grep -rln "禁止 commit\|禁止提交\|forbid.*commit" --include=*.py --include=*.sh --include=*.ps1 --include=*.yml .` 排除凍結樹後 **REAL_RC=1（零命中）**。**改派為：未指派 backlog**。解鎖條件：先決定政策（凍結版是否要有機械禁改鎖），再落實作——歷輪已三次經使用者核准打破 Copy-on-Evolve（R44／R45／R46），故該鎖**不可寫成無條件硬擋**，須留「使用者核准例外」通道。見 DEF-101-555（現居 archive_33）。 ｜🔴 R81 改派，承接輪次：**R82**（本輪做不完：凍結版禁改鎖**不可**寫成無條件硬擋〔歷來三次例外皆經明文核准〕，須先拍板「使用者核准例外」通道的形態）

**裁決與理由**：裁決＝**不建凍結版禁改機械鎖，劃界結案**。理由（可查證）：①凍結面已有守——ci-gate 兩軌（凍結基線 v0.01＋LATEST，`AISDLC_SDD/scripts/ci-gate.sh`）＋`tools/lib/hook_wiring.py::FROZEN_SHELL_FORM_MAX`（凍結 settings 面「上升＝有人改了凍結面」即紅）＋`tools/tests/test_component_sanitizer_shared_layer_lock.py`（30 版行為級一致性）；②把禁改鎖接進 pre-commit deny 面有既有 P0 判例（根 `.claude/settings.json` 記載過「hook 誤觸 deny 會把所有工具硬鎖死」）；③歷來三次破例皆經使用者核准，例外通道已由 ADR-XPLAT-001（Accepted）的逐案人工 signoff＋EVOLUTION_LOG 制度化。本列的記事存證本體（DEF-101-056 記載矛盾）原文保留於現象欄不動。

**當回合實測**：上述三個機械物當回合皆以 grep／ls 實查存在。

### §G-101-795 `DEF-101-795` → closed-by-decision@R92

**原狀態欄（逐字）**：

> **partial@R74**（承接輪次：**R75**）｜🔴 承接輪次 **R79**（改派沿革見 `DEF-101-878`）。R79 逐項處置：解鎖條件 (a)（E3＝排程設定漂移歸零）**已達成**——`DEF-101-794` 本輪結案、`check_scheduled_task_drift.py` rc=0；(c) 只在裁定退場時才觸發。**剩餘只有 (b)：由 PM 明文二擇一（退場／降頻）**，屬需掌舵者拍板類，agent 不得代決。原狀態欄全文與 R79 查證見 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-795` 節

**裁決與理由**：裁決＝**AutoClaude_WindowsSmoke 排程留任**（原列剩餘唯一事項＝PM 二擇一）。附帶義務：下次 Windows session 以 `Get-ScheduledTask | Get-ScheduledTaskInfo` 驗排程健康度（憑證＝NextRunTime 值，非 rc；根 CLAUDE.md 取證規則）。

**當回合實測**：解鎖條件 (a)（E3 排程漂移歸零）R79 已達成（`DEF-101-794` 結案、`check_scheduled_task_drift.py` rc=0，原狀態欄載明）；(b) 即本裁決；(c) 僅退場時觸發、不適用。

### §G-101-798 `DEF-101-798` → closed-by-decision@R92

**原狀態欄（逐字）**：

> **partial@R74**（承接輪次：**R75**）｜🔴 承接輪次 **R79**（改派沿革見 `DEF-101-878`）。R79 判定＝**分流到「需掌舵者拍板」，不再列入一般 backlog**：把那 4 支橋進根層＝改變**每一個**根 session 的 PreToolUse deny 面，而該檔自記過「hook 誤觸 deny 會把所有工具硬鎖死」的 P0 ⇒ 這是政策決定不是實作待辦。R79 復驗：根 `.claude/settings.json` 對那 4 個檔名 grep 零命中，仍未橋接。逐支風險評估與拍板後的執行順序見 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-798` 節 ｜🔴 R81 就地訂正＋改派，承接輪次 **R82**：本列「鐵律三的 8 項觸發清單只有 4 項有掃描器」那半邊**今日為假**——根 CLAUDE.md 該表已擴到十餘列且多數具名機械物，R80 另把「自陳沒人守的宣稱必須通過證偽探針」做成 `TestIronLaw3NoMechanismClaimsAreFalsifiable`。仍為真的半邊＝4 支 hook 未橋接（當回合逐字串比對根 `.claude/settings.json` 皆 False），屬需掌舵者拍板類

**裁決與理由**：裁決＝**4 支 AutoClaude hook（enforce_docs_path/loc_budget_check/check_lang/claude_md_freshness）不橋進根層，維持劃界**。理由（可查證）：①橋接會改變每一個根 session 的 PreToolUse deny 面，而 P0 判例（hook 誤觸 deny 全工具硬鎖死）已載於根 `.claude/settings.json`；②劃界已成文——根 CLAUDE.md〈兩專案共通的工程紀律〉R74/R75/R79 訂正段逐行載明「僅 AutoClaude 子專案 session 生效」；③雙向機械鎖已在：`tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR74RootClaudeMdHookClaimsMatchRegistration`（宣稱↔註冊雙向）＋`::TestR79EveryRegisteredHookIsNamedInClaudeMd`（註冊而未提名即紅）。原列其餘項（鐵律機械物盤點）已由鐵律三覆蓋率棘輪（`TestR74IronLawMechanismAccounting`）承載。

**當回合實測**：兩支具名鎖當回合 grep 實查存在；根 CLAUDE.md 對應段落逐字在檔。

### §G-101-268 `DEF-101-268` → closed-by-decision@R92

**原狀態欄（逐字）**：

> open（記事存證，R25 三審發現；不影響本輪任何修復項目的正確性判定） ｜🔴 R81 改派，承接輪次：**R82**（本輪做不完：repo-wide 停寫 bytecode 屬需掌舵者拍板類——`tools/sync_onboarding_baselines.py:1088` 明文記載加了會量到不同的數字）  🔴 R82 吸收 DEF-101-296（同一根因、同一組三選一拍板選項）：該列 baseline 2/40 fail 與 PYTHONDONTWRITEBYTECODE=1 後 0/40 的對照數據，是本列根因假說的量測佐證。

**原分流欄（逐字；因含殘留待辦字樣，隨結案瘦身為指針）**：

> 是否要 repo-wide 設定 `PYTHONDONTWRITEBYTECODE=1`（或等效：`conftest.py` 設 `sys.dont_write_bytecode = True`）消除此類位元碼快取競態，涉及「測試執行速度 vs 可靠性」的取捨與是否影響其他既有工具鏈（如 `bootstrap_core.py` 的 pyc 快取假設），需要人工決策，不當場動；下一輪可評估是否要做，或先觀察此假紅是否在正常（非四方並行複審）的日常開發/CI 流程下也會出現

**裁決與理由**：裁決＝**維持現狀，不設 repo-wide PYTHONDONTWRITEBYTECODE**。理由（可查證）：①hook 每次工具呼叫都跑，`.pyc` 是它們的延遲緩解器，停寫的代價由每一次互動付；②`__pycache__/` 已在根與 AutoClaude 兩份 `.gitignore`（:8／:2，當回合 grep 實查），不會入庫；③原列自述「純測試執行環境層面的間歇性噪訊，不影響任何修復項目的正確性判定」（P4）；④`tools/sync_onboarding_baselines.py:1088` 記載停寫會量到不同的基線數字＝改動的影響面超出其收益。R82 吸收的 DEF-101-296 同一根因同此裁決。

**當回合實測**：`grep -n __pycache__ .gitignore AutoClaude/.gitignore` → `:8`／`:2` 命中。

### §G-101-802 `DEF-101-802` → closed-by-decision@R92

**原狀態欄（逐字）**：

> **partial@R79** ｜🔴 承接輪次 **R79**（改派沿革見 `DEF-101-878`）。三項各自定案：**① 明文關閉**——回填對象（§4.3.1 逐輪手抄登記表）已由 `ADR-XPLAT-002:637` 的 R75 裁決廢除，同節 `:672` 另明文「本節此後不再新增表列」⇒ 回填是對一個已廢除的機制補資料，依本列自書的二擇一出口以「明文放棄回填」定案；**③ 已做完**——§8 尚開著的 7 列逐列處置已成表；**剩餘只有 ②**（UEP 階梯末階需 PM signoff 而 §8.1 仍是空表），屬需掌舵者拍板類。逐條見 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-802` 節

**裁決與理由**：裁決＝**UEP 階梯末階必須掌舵者 signoff，明文化為政策**（非缺陷）。①③已由 R79 定案（原狀態欄載明：①明文放棄回填——回填對象已由 ADR-XPLAT-002:637 的 R75 裁決廢除；③交棒表 7 列逐列處置已成表）；②本輪明文化——政策文字寫入 `docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md` §4.1 階梯表下（R92 裁決段），載明「末階 ≤4 唯一路徑 Phase 2-B 須掌舵者 signoff，空的 §8.1 回執容器＝未通過，此為政策而非結構缺陷；等價替代判準（不需 signoff 的 §4.1 替代路徑）維持可用」。政策住 docs/ 側、護欄層 .py 零行數變動。

**當回合實測**：ADR-XPLAT-002 §4.1 R92 段當回合寫入（見該檔）；護欄層 numstat 零變動。

### §G-200-067 `DEF-200-067` → closed-by-decision@R92

**原狀態欄（逐字）**：

> open（承接輪次：**R91**）

**裁決與理由**：裁決＝**明文放棄 ps 兩鎖（test_ps51_compat.py／test_ps_engine_ssot.py）合併**。理由（可查證）：①R84 實測判例——合併後刪檔引發全樹十餘支測試轉紅、且消除需 git rm（並行輪禁 git 操作），已固化為根 CLAUDE.md 鐵律三「跨檔參照稅」段與鐵律七；②合併成品只存在於 R84 的 scratchpad（session 專屬目錄，已消失），重做需重付全部成本而收益只是檔案數−1；③兩支鎖現況各自為綠（本 session 全套根層 unittest 該兩檔零 FAIL）。②（_FROZEN_GUARD_LINES 重釘）已由 R84 之後各輪收尾兌現（`_GUARD_LINES_REPIN_LOG` 有後續列）；③（跨檔參照稅）已固化為鐵律七。

**當回合實測**：`ls tools/tests/test_ps_engine_ssot.py tools/tests/test_ps51_compat.py` → 兩檔皆在；本 session 全套 `Ran 3361 tests` 中該兩檔零失敗列。

### §G-101-764 `DEF-101-764` → fixed@R92

**原狀態欄（逐字）**：

> open（承接輪次：未指派）——本包**刻意不動程式碼**（射程限帳本），且新判準對存量的命中量未量測，盲上會製造一次性大量紅燈。**解鎖條件（三項齊備才算修完）**：(a) 把 (B) 的 7 處站點改號為 `DEF-101-763`；**或**由主控改採相反指派（`759` 給站點多的 (B)、`763` 給 (A) 的 2 處，只需改 2 處）——兩種都合法但**必須擇一、且程式碼與帳本要一致**，屬需人工決策項，本包不代決；(b) 新增機械判準「原始碼引用的 `DEF-\d+-\d+` 必須在帳本家族（主檔 ∪ archive）解析得到」，掃描面用 **tracked ∪ untracked-not-ignored**（`DEF-101-752` 判例；否則新檔天然隱形，而本輪這四筆正是新檔）；(c) 該判準須以**注入探針**雙向驗紅綠（引一個不存在的 ID 必紅／移除必綠），不得只證綠（`DEF-101-750` 判例：新造的鎖若不當場注入，很可能是假鎖）。**誠實劃界（不補的殘餘，記在此處以免下輪誤以為已覆蓋）**：「同一 ID 指涉兩個不同缺陷」在語意上機械抓不到，(b) 只能抓「引用了不存在的 ID」；本次之所以連撞號都被抓到，是因為兩筆**都**不在帳本裡——若其中一方已入帳，(b) 只會對另一方說話，撞號本身仍會靜默通過 ｜🔴 R81 改派，承接輪次：**R82**（本輪做不完：(a) 撞號的改號方向是人工決策，帳本包不代決；(b) 為 `_CROSSREF_TARGETS` 加原始碼掃描面要動 `check_defect_log_crossref.py` 的掃描面。並就地追加訂正：本列「四筆全程未入帳」今日為假，已由 archive_51 消解）

**裁決與理由**：裁決＝**改引用面較小的那一號**。當回合全庫實測：`DEF-101-759` 引用共 20 站點，其中 (A) pyenv-shim 語意 12 站（`test_dev_start.py` 8＋`WindowsAppsGuard.ps1` 3＋`test_smoke_ci_sync.py` 1）、(B) 心跳解析語意 8 站（`baseline_origin.py` 3＋`test_doc_loc_baseline_freshness_r60.py` 5）；`DEF-101-763` 程式碼引用 0。帳本側 `archive_51` 的 759 列描述 (A)、763 列描述 (B) ⇒ 唯一一致解＝(B) 的 8 站點改號 759→763（同時是較小引用面）。三項解鎖條件：(a) 本輪已執行（8 站點全改，逐站同行改值零 LOC 變動）；(b) 機械判準已存在——`tools/tests/test_defect_id_reference_integrity.py::test_every_referenced_defect_id_exists_in_ledger_family`（掃描面含 untracked-not-ignored，見該檔）；(c) 該檔自帶紅綠自證測試（`test_scan_surface_is_not_silently_empty` 等）。誠實劃界照原列：`DEF-200-*` 家族引用完整性缺口由 `DEF-200-015`（未結）承載；「同一 ID 指涉兩缺陷」語意層仍機械抓不到（原列已載明）。

**當回合實測**：改號後 `grep -rn "DEF-101-759" tools/lib/baseline_origin.py tools/tests/test_doc_loc_baseline_freshness_r60.py` → 0 命中；763 引用 8 站（見下方逐列驗證）。

### §G 附註（Q-4，記錄即可、不開帳本列）

官方 settings.md 提及的 `DISABLE_AUTO_COMPACT` 在 env-vars.md 頁 0 命中（R92 設計包
WebFetch 兩頁實查[設計包回報]；本機 2.1.233 binary 內該字串存在）＝**上游文件互不一致**，
屬上游文件債、本 repo 無行為缺口（`autocompact_posture()` 兩個 kill env 都認，本節上方
控制組實測第 1 站即列出兩名）。不開未結列的理由：那不是本 repo 能修的債，開列只會讓
未結存量倒退。

## §H R92 改派稅：27 列未結列承接輪次 **R91 → R93**（時鐘推進的連帶義務）

**成因**：`DEF-200-138`（R92 首列）落地推進帳本時鐘至 R92。當下未結列帶「承接輪次：R91」
者實為 **29** 列：其中 **27** 列被硬規則② 當場判孤兒（本節主批）；另 **2** 列
（`DEF-200-012`／`053`）因狀態欄既有「改派」字樣滿足規則② 而逃過本批，由「改派／回執出口
新鮮度」鎖（`test_check_defect_log_crossref.py` 的 freshness 判準）於同輪 Architect 複審
（E-01）抓回，依同一慣例就地改派 R93（byte-中性，615B／688B 前後相等）。**終態＝29/29 皆
已改派 R93**，修復後 `pytest tools/tests/test_check_defect_log_crossref.py -q` →
`210 passed, 42 subtests passed in 3.11s` rc=0。**手法**＝沿 R86 先例
（`CrossPlatform_R86_Ledger_Reassign_Evidence.md` §1，`DEF-200-106` 立案）：就地把狀態欄的
承接輪號字面由 `**R91**` 改寫為 `**R93**`——選字面改寫而非追加附記的理由是**量出來的**：
27 列中 8 列餘裕 ≤9 bytes（`DEF-200-023` 餘裕 0），連最短附記都放不下，而 R91→R93 逐列
byte-中性（逐列改前後 bytes 斷言相等，見執行紀錄）。**共同理由（逐列相同）**：R91 是結案輪
（只結案不修新缺陷）、R92 是結案與裁決執行輪，兩輪的射程皆不含這些列的修復工作。
**逐列清單（原值一律 R91、新值一律 R93，各列僅狀態欄一處 token）**：
DEF-200-015／023／042／043／063／065／075／084／086／090／096／101／106／115／116／117／
118／121／122／124／125／128／129／131／132／133／134（共 27 列）。
**誠實劃界（照抄 R86 §3 的未關缺口）**：「就地改寫輪號」對硬規則② 與「追加」完全等價、
今天仍無任何機械物會對這條路徑說話；「到期未處置即升級」機械物仍未建（`DEF-200-106` 未結、
本次已隨批改派至 R93）。

---

## §I 由 `tools/tests/test_context_budget_guard.py` 搬出的測試層史料（R92 逐字保全）

> R92 補 D-02 回歸組（`AutocompactPostureTest`）時，依「護欄層淨額 ≤ 0」在同一支檔內
> 搬出等量敘事史料；各條在原站點留有一行指標。逐字如下，內容一字未刪。

### §B-4（補於 §B 之後）——M1 送達形態鎖的立案敘事（原 `ContextWarnReachesTheModelTest` docstring）

> 🔴 M1 送達形態鎖：`.claude/hooks/context_budget_guard.py` 的 75% 分支此前是
> `stderr + exit 0`，而官方契約下 exit 0 的 stderr **不進模型 context**
> ⇒ 模型在 75~90% 這一整帶結構上收不到訊號（本輪立案實測 1h49m／45 turns 零訊號）。
> 本組守兩件事，兩件都是**實測過的失效面**，不是形式：
> ① 送出的 `hookEventName` 必須**逐字等於 payload 的 `hook_event_name`**。刻意不釘死
> `"PostToolUse"`——那正是 R83／D3 已被推翻的假設（不符時 CC 直接把整個
> `additionalContext` 丟掉，失效外觀與「水位很低」相同）。
> ② 兩軸同時開火時，stdout 必須是**單一**合法 JSON 且兩段文字都在裡面。這一條不是
> 推論：本輪以臨時專案目錄實跑對照（PostToolUse hook，單物件 vs 兩個相接物件），
> 單物件 ⇒ 模型回 `TOKEN=ALPHA`；**兩個相接物件 ⇒ 模型回 `TOKEN=NONE`（兩則一起
> 消失）**。逐字輸出見本檔 §B。

### §I-1 `_isolated_env` 的隔離立案（原 helper docstring）

> 🔴 `USERPROFILE`／`HOME`／`HOMEPATH` 一起改指到 `tmp` 是 R79 補的隔離（不是裝飾）：
> window 判定新增了「settings 鏈的 `model` 欄帶 1m 標記 ⇒ 1,000,000」這一階，而
> 本機 `~/.claude/settings.json` 的 `model` 實測就是 `opus[1m]` ⇒ 沒有這道隔離時，
> 下面每一條餵 190,000 期待 95% 的 e2e 會在**開發者自己的機器上**變成 19% 而靜默，
> 在別人的機器上又是綠的。測試讀到誰的設定，必須由測試自己決定。
> `TMPDIR`／`TEMP`／`TMP` 同理：閂鎖 state 檔住在那裡，不隔離的話測試互相污染，
> 而污染的方向正好是「看起來通過」。
> `CLAUDE_PROJECT_DIR` 反而必須指向**真的 repo 根**：hook 要靠它找到
> `tools/session_resume_planner.py` 去產任務書骨架。

### §I-2 反「事後諸葛」判準的第一版踩坑（原 `test_it_never_claims_a_schedule_was_created` docstring）

> 🔴 判準的邊界（誠實劃界，第一版就踩到）：最初寫的是 `assertNotIn("已排程")`，
> 當場紅——因為那三個字也出現在**禁令**裡（「才准宣稱『已排程』」）。裸子字串
> 分不出「宣稱」與「禁止宣稱」，而放寬成「只要有免責聲明就算過」等於沒有判準。
> 改成**列舉完成式片語**：抓得到「把沒發生的事寫成發生了」，抓不到換句話說的
> 同義宣稱——那半邊仍是人審責任，此處不宣稱涵蓋。

### §I-3 閂鎖鍵漏分母的 R78 事故（原 `test_a_corrected_window_re_arms_the_hard_tier` docstring）

> R78 版閂鎖鍵只有 tier：拿 200,000 當分母誤喊一次 hard 之後，等 peak 越過
> 200,000、分母翻成 1,000,000、真的到 90% 時，**閂鎖還鎖著** ⇒ 唯一該出聲的
> 那一次被前面那次誤報吃掉，從此到 99.9% 全靜默。

### §I-4 window 五階判定的立案實測（原 `WindowSourceOrderTest` class docstring）

> 立案實測（掌舵者自己的機器）：user 層 settings 的 `model` 是 `opus[1m]`＝1,000,000，
> 而 R78 版守衛拿 200,000 當分母 ⇒ 真實 15%／18% 各誤喊一次，之後到 99.9% 全靜默。
> 「分母錯五倍」不是精度問題，是讓整支守衛在它唯一要防的那一刻失聲。

### §I-5 M2 原稿的同 session 假綠（原 `WarnBandLatchTest` class docstring）

> 原稿把 76/80/85/89 四個樣本寫在同一個 session 裡——它們同 tier 同 window ⇒ 同一把
> 閂鎖鑰匙，同 session 跑必然只有第一個出聲；那樣的測試在換 session 時是假綠。
> （R92 起樣本改 84/87/90/93，語意不變。）

### §I-6 「每 5pp 重新武裝」提案的評估（原 climbing 測試 docstring）

> 為什麼這是刻意的：每次工具呼叫都出聲的守衛會被整個關掉，那是本 repo 反覆判過的
> 形態。代價也照實記——模型若無視那一喊，本帶不會再喊第二次（「每 5 個百分點重新
> 武裝」的提案已被評估，它會打紅 `LatchRearmTest::
> test_the_same_tier_and_window_still_only_fires_once`，與本案正交，另輪處理）。
> 本條就是那個提案的**入場券**：它一落地就必須先讓這一條轉紅。

### §I-7 PRD 前置條件的完整立案（原 `WarnGuidanceFollowsTheQuotaBandTest` class docstring）

> 🔴 PRD 前置條件（本變更**不可省**的那一半）：PRD §4.3 的壓縮觸發是三個 AND，
> 而 `.claude/hooks/context_budget_guard.py` 原本只實作了 `K_ctx ≥ 75`。PRD §0 第 1 條
> 把「額度高時觸發 `/compact`」列為 🔴 阻斷級（§2：壓縮要模型讀完整段對話再產摘要 ⇒
> 顯著推升 U5h）。這個缺陷在換通道之前是**良性的，正因為沒有人聽那則訊息**；
> 一旦訊息真的進得了模型 context，它就會被執行 ⇒ 兩件事必須同一個 commit。

### §I-8 e2e fixture 種額度快取的完整 WHY（原兩個 `setUp` 註解）

> 🔴 本類量的是 **context** 那把尺，而額度那把尺也跑在 PostToolUse 上 ⇒ 不種快取時
> 額度軸會在這裡回報「量不到」並出聲，三條「必須完全靜默」當場紅，而**紅的原因與被測
> 性質無關**（成因是 fixture 把 `HOME` 指到沙箱，不是 production 狀態；實測讀數＝R89
> 收尾證據檔）。種一份 free 帶健康快取把被測世界收斂回「額度正常時，低 context 必須
> 靜默」；斷言一個字都沒放寬（`err == ""` 仍逐字成立，額度軸若誤出聲照樣紅）。
> 🔴 R81 收斂：種一份**新鮮且健康**的額度快取。本類量的是 context 那把尺，而
> 額度那把尺現在會在「量不到」時出聲（SD-B2 的修法本體）——沙箱裡沒有憑證檔
> ⇒ 不種的話每一條 `Task` e2e 都會多收到一行額度降級告警，而下面好幾條的判準是
> `stderr == ""`。用「關掉額度守衛」來擺平會讓這幾條連帶失去對額度誤擋的鑑別力，
> 所以這裡是把額度**量得到而且很寬鬆**，不是把它關掉。

### §I-9 matcher 計數面的 R80 訂正與 production 佐證（原 matcher 測試 docstring）

> 🔴 R80 訂正計數面（**條目數 ≠ 註冊數**）：exec form 之後，每個邏輯 hook 佔
> **兩個條目**——「Windows 載具（pythonw.exe）」與「POSIX 載具（帶 shebang 的
> 啟動器）」各一，各平台恰好一條 spawn 得起來、另一條必定失敗，而 CC 對 spawn
> 失敗是 **fail-open**（只記一行 ERROR、工具照跑）。所以那**不是重複註冊、也
> 不會雙跑**；production 實測佐證：一次 Bash 呼叫命中兩個 PreToolUse block，
> `EFTYPE`（POSIX 半邊）出現 2 次，而 `Hook denied tool use for Bash` 只有 **1** 次。
> 🔴 反過來說，把其中一條刪掉才是真缺陷：那會讓該 hook 在**另一個平台**整支
> 消失，而且因為 fail-open，不會有任何東西轉紅（`tools/lib/hook_wiring.py` 的
> 判準 E 就是為這件事存在的）。

### §I-10 `compact_boundary_count` 的完整立案（R92／D3，SD 複審 P1，由該函式 docstring 搬出）

> 🔴 R92／D3（SD 複審 P1）：這是 harness **免費**寫進逐字稿的訊號（`compactMetadata`
> 含 `preTokens`／`postTokens`，本機兩份真實逐字稿實測共 9 筆），`scan_transcript()`
> 完全沒讀過它。少了它，`latch_key` 只認 (tier, window) ⇒「compact 成功 → 同一
> window 內真的再次越線」整個週期不會重新武裝（SD 三步驟 probe 親證：STEP3 同一
> session 再爬回 HARD，rc=0 且 stdout/stderr 全空）。用法見 `latch_key` 的 WHY。
> 獨立成一支函式而不併進 `scan_transcript`：後者的三元組回傳值已有多個呼叫端
> （`session_resume_planner.measure`／多支測試）逕行三元解包，插入第四個值會
> 在同一批改動裡連帶波及那些呼叫端；本函式與它共用同一種壞行處置紀律
> （逐行預篩、壞行跳過、`OSError` 回 0）但各自獨立掃描，互不相依。
>
> 真實記錄形狀（本機逐字稿實測）：`{"type": "system", "subtype": "compact_boundary",
> "content": "Conversation compacted", "compactMetadata": {"trigger": "manual",
> "preTokens": 827814, "durationMs": 161398, ..., "postTokens": 11205,
> "cumulativeDroppedTokens": 816609}}`。

### §I-11 `BLOCKING_TOOLS` 的 R80 立案（原常數旁 `#:` 註解，由 D3/D2 補洞包搬出）

> #: PreToolUse 模式會擋下的「展開型」工具。刻意不含 Read／Edit／PowerShell：
> #: 收斂（讀檔、寫任務書、跑 git）必須還做得到，否則守衛會被整個關掉。
> #:
> #: 🔴 **R80：這一組名字在本 harness 上的命中面原本是 0**（掃描 S7-02 實測：8,106 次
> #: `tool_use` 裡 `Task`／`WebFetch`／`WebSearch` 出現 **0 次**）。本 harness 派子代理叫
> #: `Agent`、批次編排叫 `Workflow` ⇒ 阻斷臂蓋好了但一次都不會被觸發，而 R79 為它新增的
> #: 那道鎖只把「matcher ↔ 本常數」釘成**相等**，保證的是「兩個都寫錯時也一致」——鑑別力
> #: 的方向錯了（同 R77「鎖無鑑別力」那一桶）。修法是兩件事一起做：把真的會出現的名字補
> #: 進來，並補一條**有效性**判準（本常數必須與最近若干支逐字稿的 `tool_use` 名稱集合有
> #: 非空交集，見 `blocking_reach_problems`），讓「圈了一組永遠不出現的工具名」當場轉紅。
> #:
> #: `Task`／`WebFetch`／`WebSearch` **保留不刪**：它們是 Claude Code 上游的標準工具名，
> #: 換一個 harness 就會回來，刪掉只是把同一個缺口移到另一台機器上。

### §I-12 預防性哨兵觸發層的立案與三個取捨（原區塊註解，由 D3/D2 補洞包搬出）

> 🔴 現行形狀（R82／HELM-02 改的是「在哪一刻按下去」，不是方向）：SessionStart 只**清閂鎖**
> （見 `arm_sentinel`），真正的註冊延後到 PostToolUse 且要通過
> `tools/lib/sentinel_lifecycle.should_arm()`（回合數＋存活跨度雙門檻）。延後的代價已界定：
> 一個 8 分鐘就結束的 session 拿不到續航；換掉的是「每一支 5 秒探針都留一支排程」。
> 判準不能寫在 SessionStart 那一刻：見取捨②——那一刻逐字稿往往還不存在。
>
> 🔴 為什麼非得預防性不可（不是「順手掛一下」）：
> `tools/session_resume_planner.py --arm-endurance` 是**手動**武裝的，而額度耗盡那一刻
> 是 16 秒內全部 subagent 瞬間掛掉——那個時間點沒有任何人會去跑一行指令。更根本的是
> **額度耗盡在 Claude Code 的 hook 體系裡沒有任何觸發點**：它是 API 層的失敗，不是工具
> 呼叫失敗 ⇒ PreToolUse／PostToolUse 都不會被叫到，本檔那兩個模式一次都不會醒來。
> ⇒ 唯一可行的形狀是**預防性武裝**：趁還能跑指令的時候先掛好，之後由 OS 排程器（不是
> 這個 session、不是這個模型）去輪詢。SessionStart 是「還能跑指令的最早時刻」。
> 這也是本 repo 已判過三次的同一個病的解藥：R77「PKG-GUARD 機制蓋好沒接電」——機制做完
> 了但沒有任何東西會自動去按它。純文件約束（「開工前記得武裝」）對當下的模型零攔阻力。
>
> 三個刻意的取捨：
>  ① **detached 子行程**，不同步等它跑完。註冊一支 schtasks 要外呼 powershell.exe，
>     實測數秒；同步做等於每次開 session 都先卡幾秒。取證不因此消失——`--arm-sentinel`
>     自己有 `NextRunTime` 憑證閘，成敗都寫進稽核 jsonl 與下面這支 boot log。
>  ② **逐字稿檔案不存在也照樣武裝**。SessionStart 那一刻檔案往往還沒被建立；planner
>     對這個入口特別放行（見該檔 `--arm-sentinel` 的 WHY），只把路徑記進狀態塊。
>  ③ **一切例外吞掉**。`.claude/settings.json` 的 description 記載過 P0：hook 誤觸會把
>     所有工具硬鎖死。武裝失敗最多是少一層保護，絕不可反過來變成故障源。

### §I-13 `effective` 欄位的完整立案（R92／D2，SD 複審 P1 附帶項，由 `autocompact_posture` 上方註解搬出）

> 🔴 為何這一格必須是**現查**而不是文件裡的一句話：R78 的 hook docstring 逐字寫
> 「實查三處，這兩件事在這一層零機械物」，三處裡沒有一處是 Claude Code 自己——
> 於是我們花了一輪做偵測器，卻沒人去查那件事本來有沒有內建解。答案是有，而且
> **預設就開著**。這個函式讓「開著沒」變成每次都能重跑的量測，不是一次性的結論。
> 🔴 R92（Q-1→D2 兩輪演化，SD 複審 P1 附帶項訂正）：Q-1 補了 settings 鏈但取**保守
> 合併**（任一層 false 即報關閉），SD 親驗 `guard.settings_value(key, guard.settings_
> chain())` 這個既有原語就能算出官方 first-wins 的**真正**有效值（現場測回 True）——
> 保守合併與它不一致時，`enabled` 會在「更高優先層已把它蓋回 true」的情境誤報關閉，
> 下游只讀 rc 會誤判成「確定關閉」。`effective` 才是 CC 真正會用的值：kill env 最高
> 優先；否則 first-wins 走 `settings_chain()`（`~/.claude.json` **不在**這個精度序內
> ——官方 settings.md 明載它是 OAuth／MCP／專案狀態的另一個檔，不屬 settings 階層，
> 故 `configured` 只降級為稽核資訊，不再參與判定）。`layer_off` 同理降級為稽核資訊。

### §I-14 R92 補洞包（D3/D2/D4 迴歸鎖）由測試 docstring 搬出的史料，逐字保全

> **`test_the_action_uses_a_no_console_interpreter` 的完整立案（R79 續修＋R80 訂正）**：
>
> 🔴 R79 續修的回歸鎖（掌舵者當場回報：哨兵每 15 分鐘彈一個 console 視窗）。
> 鎖的是**載具**而不是只鎖 LogonType，理由是射程：S4U 註冊需要提權，而哨兵的
> 主要武裝路徑（SessionStart hook）一律非提權——本輪真機實測 `Register-ScheduledTask
> ... -LogonType S4U` 在非提權下回「存取被拒」且工作根本沒建立。在那條路上唯一
> 還成立的「不彈視窗」保證就是載具：`python.exe` 是 console 子系統、Interactive
> 下必定配一個視窗；`pythonw.exe` 是同一個直譯器的 GUI 子系統版本，不配置 console。
>
> 🔴 R80 訂正判準（act 在 Linux 容器實跑抓到的紅；本機 Windows 結構上看不見）：
> 原判準逐字斷言字面 `pythonw.exe`，而 POSIX 上根本沒有 `pythonw`——
> `guard.quiet_python()` 在那裡依約回 `sys.executable`，於是這條在容器裡必紅
> （逐字：`'pythonw.exe' not found in '... -Execute '/opt/.../bin/python3' ...'`）。
> 這正是鐵律三「這在另一個平台是什麼值」，而它被寫成了一個平台常數。
> 改法不是加平台守衛（那會多一個 skip 站點、也讓 POSIX 上零判準），而是把問題
> 換成兩平台同一條：Action 的載具必須是「本 repo 唯一那支不配置 console 的解析器」
> ——即 `guard.quiet_python()`，而不是某個字面。三格判準各自獨立：
>   ① 產生的腳本裡真的用了那個值（行為面，兩平台皆成立）；
>   ② 來源面：planner 必須呼叫那支唯一真相源，不得自己算一份（同一份知識三個家
>      正是 R80 收掉的缺陷之一）——這一格讓「改回 `sys.executable`」在 POSIX 上
>      （兩者恰好同值、行為面看不出來）照樣紅；
>   ③ Windows 上那支解析器必須真的解析到 `pythonw.exe`（缺陷本體所在的平台）。
> `if os.name == "nt"` 是平台條件斷言、不是 skip 站點：本條在兩個平台都會跑、
> 都有判準，只是第三格的斷言只在 Windows 上有意義。

### §I-15 `detached_conflict_problems` 的完整立案（原函式 docstring）

> 🔴 R80 訂正本條的理由（原文逐字宣稱「`DETACHED_PROCESS` 會把 `CREATE_NO_WINDOW`
> 抵銷掉」，那句話同輪已被重量證偽，故不複述它——本 repo 判過「訂正註記逐字引述假話
> ＝製造新假話」，而這一段假話原本就住在未來工程師唯一會讀到的那段文字裡：紅燈訊息）。
>
> 真正成立的理由是**載具效應，不是旗標語意**。重量矩陣（pythonw 當無 console 父行程、
> 子行程自報 `GetConsoleWindow()`；`0`＝沒有 console）：
>   · 真直譯器（base `python.exe`）那一列，`DET|CNW` 是 0 ⇒ 旗標本身沒有互斥。
>   · 本 repo 的 venv 由 uv 建立（`pyvenv.cfg` 有 `uv = 0.8.22`），其 `python.exe`
>     是 trampoline（274,712 bytes vs 真直譯器 103,192 bytes）：它 re-spawn 真的
>     直譯器，而不把 creationflags 轉傳下去 ⇒ 穿過它時 `DET|CNW` 才翻成「可見」。
>   · `CNW` 與 `NEWGRP|CNW` 是唯二在四種載具上全部為 0 的組合。
> ⇒ 本規則守的是「在本 repo 的載具上這個組合實測會彈視窗」，不是「這兩個旗標語意
> 互斥」。要脫離父行程請用 `CREATE_NEW_PROCESS_GROUP`。
>
> 射程誠實劃界：上述重現依賴「venv 由 uv 建立」。走 `python -m venv` 回退路徑的 venv
> 是否同樣翻面，未驗——所以這條是本 repo 的載具規則，不得寫成平台常數。

### §I-16 六段被 D3/D2/D4 迴歸鎖包順手壓縮的既有長篇 docstring，逐字保全

> **`test_the_repo_side_cmd_exe_source_...`（cmd.exe 行為鎖）**：
> 🔴 實測歸因出來的 repo 側 `cmd.exe` 來源，釘成行為鎖。本輪 17 分鐘量測窗
> （`tools/probe/console_spawn_watch.py`）抓到 3 筆 `cmd.exe`，父行程一律是
> `python -m pytest tests/ -q`，子命令列是 `cmd.exe /c "pytest tests -k …"`／
> `cmd.exe /c "python -c …"`——那正是 `execution/evaluator.py` 與
> `mutation_applier/_conditional.py` 的 `shell=True` 在 Windows 上的形狀
> （`shell=True` ⇒ `cmd.exe /c`）。父行程沒有 console 時（schtasks 的 pythonw、
> GUI 啟動器），每一個 playbook 步驟就是一個黑框。判準是行為不是字面：直接載入
> `platform_caps.py`（純 stdlib，可獨立載入）、模擬兩個平台各呼叫一次。字面判準
> 會被一個等價改寫繞過，而這一格的失效方向是「黑框回來了」——而黑框回來時沒有
> 任何測試會轉紅，只有使用者看得到。
>
> **`test_a_session_that_never_wrote_a_transcript_disarms_in_silence`（HELM-01 本體）**：
> 🔴 HELM-01 本體（使用者 2026-08-09 三度回報的模態彈窗，真凶就是這一格）。
> SessionStart 無條件武裝哨兵，而開了沒做事就結束的 session 根本不會產生
> `.jsonl`（R82 開場實查：那支逐字稿在整個 `~/.claude/projects` 遞迴搜尋零命中，
> 不是路徑解析 bug）。舊實作在 `transcript.is_file()` 為 False 時硬編 `escalate`
> ——理由逐字寫著「哨兵已瞎，自我解除並叫人」，於是一個正常結束的 session 換來
> 一個杵十分鐘的模態對話框。設計把「session 沒留下逐字稿」與「哨兵失明」混為
> 一談，而前者是常態。本條釘住四件事：靜默（不敲人）、不留紙、排程仍要收掉
> （不留過期事實）、以及理由句子仍與「正常下班」分得開——後者正是當初把它做成
> fail-loud 的唯一正當理由，收斂時不得連它一起丟掉。
>
> **`test_the_frame_is_a_function_of_the_message_and_now_only`（reset_at 框架核心判準）**：
> 🔴 核心判準（兩平台都有牙）：`reset_at` 的框架只能來自①訊息自報的時區，或
> ②`now` 的時區——絕不能來自這台機器的時鐘。優先序在兩個平台上會走到不同的
> 那一格，所以期望值也照著算，而不是寫死一個數字：有 tz 資料庫（Linux／macOS
> 容器）⇒ 三格都該是 `Asia/Taipei`；沒有（Windows，本機實測
> `ZoneInfoNotFoundError`，且不得為此新增 `tzdata` 相依）⇒ 每一格該是該格
> `now` 的時區。注入自證：把 `sentinel_decide` 裡的
> `local_time(event["timestamp"], now.tzinfo)` 改回
> `local_time(event["timestamp"])`（＝讀機器時區），本機（UTC+8）的 UTC 那一格
> 會由 `09:00+00:00` 變回 `09:00+08:00` ⇒ 當場紅。這就是 act 在 UTC 容器抓到、
> 而本機結構上看不見的那個缺陷。
>
> **`test_a_stale_handled_through_does_not_swallow_a_newer_breach`（R80 保留舊介面相容性）**：
> 🔴 R80 訂正：這是一支「保留舊介面」的相容性測試，不是現行語意的判準。原
> docstring 逐字保留了那句已被本輪判定為假的立案理由（「武裝當下把現存最後一筆
> 記成已處理，因為我們此刻跑得動武裝指令就證明額度是通的」）。武裝是純本機
> subprocess、零 API 呼叫，證明不了額度——那句話正是哨兵整晚失明的 P0 根因，
> 而它同輪只在 planner 的一處被改掉、在這裡原文留著 ⇒ 讀這支測試的人會拿到已被
> 推翻的規格，而綠燈替那句假話背書。同一份知識三個家只改一個，是本 repo 的頭號
> 病。現行語意：`handled_through` 已降為稽核欄位，`_sentinel_tick` 一律傳空字串
> ⇒ 本條走的是 production 走不到的那條分支，它「不可能因為業務邏輯改變而失敗」
> （Rule 9）。留著它只為了兩件事：①舊狀態塊仍帶該欄位、讀得回來時語意不得漂移；
> ②若有人把它改回「唯一的已處理判準」，這支的斷言仍描述它該有的行為。真正守
> 現行語意的判準在 `UnhandledLimitDetectionTest`（事件晚於全域最後一次成功 API
> 回應 ⇒ 未處理；早於 ⇒ 已處理），那一組才是接在 production 路徑上的。
>
> **`test_the_patrol_interval_bounds_the_post_reset_dead_time`（巡邏間隔 R80 訂正）**：
> 🔴 R80 訂正：這一條原名／原文宣稱「間隔小於最短觀測窗」，那句話已被證偽。
> 原文的依據是單一事件（08:44 撞、`resets 9am` ⇒ 16 分鐘）。R80 以全庫 1,433 支
> 逐字稿重量（`tools/probe/reset_window_distribution.py`，14 個相異 episode）：
> 最短窗是 0.5 分鐘，4/14 個 episode ≤16 分 ⇒ 900 秒並不小於最短觀測窗，
> 原本的測試名是一句假話。留著一句假話比沒有測試更糟（本 repo 反覆判過的形態），
> 所以這裡改成釘住那個真正成立的性質。真正的性質：間隔決定「reset 之後最壞多久
> 才會有人動作」。窗比間隔短時，那一次走的是 `probe` 而不是 `arm_reset` ⇒ 代價
> 是一次探測（~32K tokens），不是失效。故判準是上界＋shrink-only 方向：調大即紅
> （死等變長），調小照樣綠（巡邏零 token，這一側沒有需要權衡的量）。取捨全文見
> ADR-XPLAT-004 §2.7。
>
> **`test_the_variadic_add_dir_does_not_swallow_the_prompt`（--add-dir 吞 prompt）**：
> 🔴 R80 端到端實測踩到的真缺陷，不是理論風險。`--add-dir <directories...>` 的值
> 是變長的：把它排在 prompt 前面時，它會把 prompt 也吃進去當成一個目錄 ⇒ `claude`
> 認為這一跑根本沒有 prompt。實測逐字 `Error: No deferred tool marker found in
> the resumed session. …Provide a prompt to continue the conversation.`（rc=1、
> stdout 全空）；把 prompt 移到前面同一條指令 rc=0。失效方式最惡劣的地方：五段
> 流程與稽核痕跡全都是綠的——woken／probed／resumed 三筆齊備、`quota_open=true`、
> 排程也被正確收掉，只有那一跑什麼都沒做。所以這一條鎖的是 argv 的順序，而順序
> 在既有的「有沒有帶這個旗標」判準下是隱形的。

### §I-17 `_pin_sentinel_off` 的完整立案（R84／C3-P4c＋SA84-01，由該函式 docstring 搬出）

> 🔴 R84／C3-P4c：整個測試模組**一律不准碰真的排程器**（in-process 那一半）。
>
> 立案是實測到的：本機 `launchctl list` 長期掛著一支 `AutoSDD_Sentinel_s`，每 15 分鐘
> 醒來一次；Windows 上那就是掌舵者看到的黑框。逐步歸因（在 `LaunchdBackend.arm` 插探針
> 實跑本模組）指到 `QuotaGateIsWiredToTheBurnPathTest
> ::test_the_halt_side_effects_run_exactly_once_per_reset_window`——它以**同行程**呼叫
> `_gate()`，走真的 `quota_halt_actions` → `guard.arm_quota_wakeup` → `spawn_sentinel`，
> 於是在開發者自己的機器上註冊了一支 launchd job，session 結束後永遠沒有人來收。
> 探針逐字：`TMPDIR` 是真的那個、`AUTOSDD_SENTINEL_OFF` 為 `None`。
>
> 🔴 為什麼 `_isolated_env` 治不了它：那支 helper 造的是**子行程**的環境，而這一條走的是
> 同行程呼叫 ⇒ 兩者結構上不相交。子行程那一半由 `_isolated_env(real_scheduler=False)`
> 負責（預設值），本函式負責同行程那一半；兩層合起來才是「本模組不留移動零件」。
> 沿用既有逃生口而不新開測試專用旗標：它已經是「不要武裝」的唯一真相源。
>
> 🔴 R84／SA84-01 訂正 pin 的**生命週期歸屬**：第一版把還原動作交給
> `unittest.addModuleCleanup`，而那個堆疊是**載具**的，不是本模組的——本檔自己有一支
> 測試（見 `_run_nested_suite` 的 WHY）會起巢狀 runner 跑同模組的測試，那個 suite 收尾
> 時觸發 module fixture teardown ⇒ `doModuleCleanups()` 把還原動作**提前 flush**，pin
> 當場消失。後果不是「一支測試紅」，而是**在那之後本模組就沒有這道保護了**。
> ⇒ 捕捉原值只做一次（`_SENTINEL_PIN_CAPTURED`）：巢狀 runner 會再叫一次本函式，
> 那時 pin 已經是 `"1"`，再捕捉一次就會把 `"1"` 記成「原值」而永久留在行程環境裡。

### §I-18 `MeterFailureShapesTest` 的完整立案（原類別 docstring，收尾窗口為 R92 LOC 淨額搬出）

> 🔴 SD-B4：`fetch_usage()` 分得出 401 與斷網，而它唯一的呼叫端把 status 丟掉了。
>
> `quota_meter` 檔頭 §S1-08 逐字要求「401 與『額度真的沒回來』必須在痕跡裡分得開」，
> 理由是 OAuth token 4 小時到期、而無人看管那條路上沒有人在 refresh ⇒ 混在一起會讓
> 排程器把認證失敗誤判成額度未恢復而一直等下去（R80 哨兵整晚失明同形）。
> 落地前實測：憑證讀不到 → `None`；HTTP 401（真連線、0.30s）→ `None`。**同一個答案。**
>
> 輪次考古（原文逐字）＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`；現行劃界：
> `tools/lib/quota_meter.py` 的憑證來源走**雙欄矩陣**（`_CRED_COLUMNS`），兩平台皆可跑。
>
> 🔴 **上一段的輪號本身被獨立驗證者訂正過一次（R83／PD 複驗，此段留為判例）**：它原本
> 把訂正與 mac 真機實測都署名 **R82**，而 R82 收輪 commit（`7975140`）裡這支檔的同一段
> 逐字寫著「**我手上沒有 mac 真機**…」，
> （原話全文：「…非 Windows 的憑證來源未驗，已登記交由下一輪承接」）
> 且 `_CRED_COLUMNS`／`_cred_kwargs`／`_FAKE_TOKEN` 在該 commit 內 grep 命中皆為 **0**
> ⇒ 雙欄矩陣與真機實測**都是 R83 的產出**，署名 R82 是把「還沒驗」講成「上一輪驗過了」。
> 最難看見的一點：`quota_meter.KEYCHAIN_SERVICE` 上方在 R82 就留了一句預先警告，逐字寫
> 「改寫成 R82 就把『還沒在 mac 上驗過』講成『本輪驗過了』，那正是本段在防的假宣稱」
> ——而它預言的事在**下一輪**就真的發生了，只是發生在**另一支檔**，於是那個警告的射程
> （它只寫在 quota_meter 那一行的括號裡）看不到這裡。守輪號的既有鎖
> （`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`）判準是 `> current_round()`
> ⇒ **落後方向零覆蓋**，把 R83 的工作署名 R82 一行都不會紅（QA／F-5 同一筆）。

### §I-19 `ZSentinelPinOutlivesEveryNestedRunnerTest` 的完整立案（原類別 docstring，同上搬出）

> 🔴 R84／SA84-01：把「同行程不准碰真排程器」這條 pin 的**順序不變式**寫成顯式斷言。
>
> `SentinelArmingCriterionTest::test_this_module_never_reaches_the_real_scheduler`
> 也斷言同一件事，但它落在哪裡是**運氣**：兩種載具對**類別**的排序規則不同——unittest
> 依類名字母序（`SentinelArmingCriterionTest` 的 `S` 早於 `TraceIsolationTest` 的 `T`
> ⇒ 那支守衛跑在巢狀 runner 之前，量到的是「還沒被沖掉」的狀態），pytest 依**定義
> 順序**（`TraceIsolationTest` 定義在前 ⇒ 它先跑，pin 當場消失，那支守衛才紅）。
> 本類的兩個座標刻意同時滿足兩種規則：類名以 `Z` 開頭、定義位置緊接在
> `TraceIsolationTest` 之後 ⇒ 不論誰跑，這一格都真的落在巢狀 runner 的下游。
>
> 🔴 **方法名也是判準的一部分**：兩種載具對**方法**都是字母序（本輪實測，不是查文件
> 得來的）。下面那支紅端自證會在 `finally` 裡把 pin 補回去，所以「pin 還在不在」這一
> 格必須排在它**之前**才量得到真東西——第一版把它取名 `test_the_pin_...`（`t` > `r`）
> ⇒ 在拿掉修法的紅端演練裡它照樣是綠的（實測），也就是那一格當時什麼都沒守。
> 現名 `test_after_the_nested_runner_the_pin_is_still_up` 以 test_after_ 起頭正是為了
> 這件事，改名等於改判準。

### §I-20 `QuotaDegradationIsAudibleTest` 的完整立案（原類別 docstring，同上搬出）

> 🔴 SD-B2：額度軸「量不到」時**完全靜默**，`QUOTA_UNMEASURABLE` 在 production 是死碼。
>
> 落地前實測（同一支注入探針，四種失效各注入一次；控制組在第一列）：
>     (a) 99% 快取 ＋ meter 正常          → rc=2  stderr 173b   痕跡 —
>     (b) meter 不可達                    → rc=0  stderr **0b**  痕跡 **無**
>     (c) schema 被 bump                  → rc=0  stderr **0b**  痕跡 **無**
>     (d) 快取過期 600s                   → rc=0  stderr **0b**  痕跡 **無**
>     (e) 完全沒有快取                    → rc=0  stderr **0b**  痕跡 **無**
> 根因：`quota_gate()` 在 `pct is None` 且無地板時直接 `return 0`，**而且是在
> `quota_tier_of()` 被呼叫之前** ⇒ 全 repo `QUOTA_UNMEASURABLE` 只出現在常數定義／
> `quota_tier_of`／測試三處，production 一次都到不了。四種失效與「額度很健康」外觀
> 完全一致 ⇒ B3／B4 都變成不可偵測。
>
> 🔴 本類**兩個方向都鎖**：量不到要出聲（前幾條），量得到就不准吵（最後兩條）。
> 只鎖前者的話，下一個人用「每次都印一行」滿足它，而每次都出聲的守衛會被整個關掉。

### §I-21 `test_the_cap_ladder_now_moves_with_the_reset_distance` 的完整立案（原方法 docstring，同上搬出）

> 🔴 R82 具名改寫（本條的 R81 版斷言的正是本輪要拆掉的性質）。
>
> R81 版是另一個名字（**刻意不逐字反引號寫出**，理由同上一條：那支 test 已不存在，
> 指名它會被幽靈符號鎖判紅，而讀者會以為它還在），逐字宣告「本輪刻意**沒有**改階梯：
> 訊息變了、政策沒變」，並把 85% 釘死成一個與 reset 距離無關的常數。
> 本輪的整件事就是把那個「無關」拿掉（訴求 6b）：同一個 85%，reset 在 1 小時後
> 與在 5 天後拿到的 cap 必須不同，且方向是「近的比較寬鬆」。
> halt 帶仍然恰為 0（那一格沒有變，也不吃 horizon 乘數）。
>
> 🔴 **R86 只動中間那一個取樣點（1 小時 → 20 小時），斷言與方向一字未改**：對一個
> **7 天**窗來說「1 小時前」與「10 分鐘前」是同一件事（都 <0.6% 窗長），它們此前被
> 讀成兩格只因門檻是絕對分鐘數——那正是缺陷 A。逐項實測與辯護見具名證據檔
> `CrossPlatform_R86_Pace_Calibration.md` §七末段（同上：刻意不寫目錄前綴）。

### §I-22 `test_the_darwin_reason_really_reaches_measure_detail` 的完整立案（原方法 docstring，同上搬出）

> 接線（判定層綠不代表接上了電——本 repo『機制蓋好沒接電』已三度復發）。
>
> 🔴 R83／F2-③ 改寫載具：原版把 `meter.access_token` 換成替身、並改寫
> `meter.sys.platform`。那個形態在本輪的重構下**失去了鑑別力**——平台分支收斂進
> `_fetch_token()` 之後，`access_token` 不再在 `measure_detail` 的路徑上，於是替身
> 換了也不影響結果（實測：本測試當場紅在 `http-401`，因為它其實走到了真網路）。
> 改走兩個**生產注入點**（`platform`／`runner`）：不改任何模組狀態、走的就是
> production 那條路，而且順帶不再需要碰 `meter.sys`。
> 🔴 輪號訂正（原文寫「R82 就為此加的」）：`access_token(platform, runner)` 那一組
> 確實是 R82 加的，但本斷言走的是 **`measure_detail(timeout, platform, runner)`**
> ——它在 R82 收輪 commit 內的簽章只有 `timeout` 一個參數（`_fetch_token` 那時整支
> 還不存在）⇒ 這裡用到的那兩個注入點是 R83 加的。同一組名字掛在兩支函式上，
> 署名錯的代價是下一個人會去 R82 的 diff 裡找一個不在那裡的東西。

### §I-23 `test_the_hook_no_longer_arms_on_session_start` 的完整立案（原方法 docstring，同上搬出）

> 成因面：SessionStart 那條路上不得再有 spawn（那就是增生的來源）。
>
> 以 AST 掃 hook 的 `arm_sentinel`：它**不得呼叫** `spawn_sentinel`。
> 比對靜態結構而不是行為，是因為行為那一半在非 Windows 上恆早退＝測不到（本 repo
> 判過的「單平台判準」形狀），而這個性質在任何平台都該成立。
>
> 🔴 R84／C3-P4b 把判準由「unparse 之後的**子字串**比對」換成「**被呼叫的函式名**
> 逐一相等比對」——不是放寬，是把假紅拿掉。子字串比對會把任何**名字以它為前綴**
> 的別的函式一起判紅（本輪的 `spawn_sentinel_gc`：它做的是相反的事——收掉別人留下
> 的孤兒哨兵，正是 SessionStart 該做的清理）。而「名字長得像」與「真的在武裝」是
> 兩件事，鎖只能守後者。判準同時**變嚴**了一面：舊寫法對 `x = spawn_sentinel`
> 這種不呼叫、只取參照再由別處呼叫的繞法也只是碰巧命中，新寫法把「取名字」與
> 「呼叫」分開看，落點明確。

### §I-24 R92 收尾窗口的護欄層行數棘輪最終重釘（本節本身的立案）

`_GUARD_LINES_REPIN_LOG` 的 R92 草稿列自陳「本列僅為現查快照…最終數字須由收尾窗口
在全部包停工後的靜止樹上重新現查並覆寫本列」。收尾窗口現查真實狀態：
`test_context_budget_guard.py` HEAD=6795→D3/D2/D4 落地後 6880（+85）。R92 之前連續
兩輪淨額為正（R90:+161／R91:+410，`連升 streak 第 2／2 ⇒ R92 必須淨額 ≤ 0`，R91 列
原文明載），故 R92 的 +98（85 業務增長 +13 log 列自身開銷）必須以搬史料抵銷至 ≤0——
本節（§I-18~§I-23）即該抵銷動作：六段共 98 行純敘事 docstring
（`MeterFailureShapesTest`／`ZSentinelPinOutlivesEveryNestedRunnerTest`／
`QuotaDegradationIsAudibleTest`／`test_the_cap_ladder_now_moves_with_the_reset_distance`
／`test_the_darwin_reason_really_reaches_measure_detail`／
`test_the_hook_no_longer_arms_on_session_start`）逐字保全於上方 §I-18~§I-23，原站點各
改為一行指標，R92 最終定案淨額 **-7**（帳本重釘：84149→84142）。

🔴 **收尾途中發現樹並非真的靜止**（誠實記載，見 §I-25 補記）：容量自適應攤提工作
（`DEF-200-122`／`DEF-200-114`／`ADR-XPLAT-009`，全程使用 R93 標籤，帳本首列
`DEF-200-139` 落地即推進時鐘至 R93）在收尾窗口動工期間**仍在延伸**——不只
`test_quota_policy.py` 的 `TestR93PlanChangeAdaptiveAmortization`（8 支測試，HEAD
1934→2025，+91），另有後續追加的 `TestR93AccountKeyIsDerivedFromExistingResponseHeaders`
（4 支測試，+43，解 `DEF-200-122` 已知限制①同方案換帳號）與
`test_context_budget_guard.py` 內對應的 5 支接線測試（+78，扣除 R92 offset 後）。
此工作全數歸屬 R93（與 R92 SD 複審修復包是兩條獨立工作線），R93 最終定案淨額
**+244**（帳本重釘：84142→84386；78+134+32，末項為本表自身編修的迭代成本，逐次
量測見 §I-25）。streak 因 R92 淨額 -7 已歸零 ⇒ R93 為第 1／2 輪。

### §I-25 收尾窗口的「樹並非靜止」逐次量測記錄（誠實劃界）

任務書假設「兩條並行工作線（R92 guard 修復＋容量自適應設計工作流）都已停工」，收尾
窗口動工後**連續多次量測顯示這個前提在動工當下並不成立**——第三個來源（容量自適應
攤提的延伸工作，account-key 部分）仍在落地。逐次 `wc -l` 現查（同一 session 內）：

| 時刻 | `test_context_budget_guard.py` | `test_quota_policy.py` | 備註 |
|---|---|---|---|
| 收尾窗口開場 | 6795（HEAD） | 1934（HEAD） | R91 收筆基準 |
| 第一次現查（D3/D2/D4 落地後） | 6880 | 1934 | print-guard-lines 首次診斷 |
| 六段搬移完成 | 6788 | 2025 | R92 offset 完成、R93 首估 |
| 第二次現查 | 6796 | 2025 | ctx_guard 又 +8 |
| 第三次現查 | 6800 | 2068 | quota_policy 又 +43（account-key 出現） |
| 第四次現查 | 6864 | 2068 | ctx_guard 又 +64（account-key 接線測試） |
| 第五次現查（5s 後） | 6866 | 2068 | +2 |
| 第六次現查（8s 後） | 6866 | 2068 | 穩定 |
| 第七次現查（10s 後） | 6866 | 2068 | 穩定，採為終值 |

穩定後終值：`test_context_budget_guard.py`=6866（HEAD 起 +71＝-92 抵銷 +85 D3/D2/D4
+78 account-key 接線）、`test_quota_policy.py`=2068（HEAD 起 +134＝91 分區過濾 +43
account-key）。`test_adr_xplat001_c1c2_lock.py` 自身因本次重釘（列內容＋字典值＋
理由欄壓縮以滿足款(6) 字元上限＋本節多次迭代）由 HEAD 5445 增至 5458（+13，含本表
自我編修的既有現象，逐次修正過程留在 git 工作樹編修歷史）。**本節存在的理由**：
收尾窗口若在樹仍在變動時定案數字，會重演 `DEF-101-993`／R92 草稿列已寫過的同一種
錯——本表因此改用「連續三次靜止檢查（不同間隔）皆得相同讀數」為定案判準，而非
單次量測。

<!-- guard-total:R93 --> **本輪護欄層累積淨額＝ 84142 → 84367（+225）** —— 成長面
＝容量自適應攤提落地（`test_quota_policy.py` +134、`test_context_budget_guard.py`
account-key 部分 +78）加上本表自身編修（+13）。詳見 §I-24／§I-25。

<!-- guard-total:R93 --> 護欄層累積總量現值 **84142 → 84367（+225）**；逐項立案即
本節 §I-24／§I-25。

## §J R94 收尾：`DEF-200-114` 二次訂正 + 帳本時鐘 R93→R94

四方複審（Architect／SA／SD／QA，含兩輪 REJECT→修復→複驗）對容量自適應攤提機制
（`account_key` 訊號採納）全數 APPROVE。收尾窗口依 ADR-XPLAT-009 §7「R94／SA-2
訂正」區塊的草稿執行帳本更新——**逐字草稿換算 1762 bytes，遠超 `ROW_MAX_BYTES=700`
且 `DEF-200-114` 不在 `OVERSIZE_ROW_GRANDFATHERED` 豁免清單**，故不逐字貼入，改為
本節逐字保全＋帳本狀態欄索引化（同 §F/§G 既有手法）。

### §J-1 `DEF-200-114` 狀態欄二次訂正（逐字保全，取自 ADR-XPLAT-009 §7）

> fixed@R89：詳§F-114 ｜R93 二次訂正（Architect REJECT 承接，取代上一版本
> 欄位判讀）：R89 版「機制本體已由 ADR-XPLAT-009 §2.2 core_signature 落地
> （獨立指紋，非同一欄）」已被 `docs/06_quality/
> Quota_R90_CrossAccount_Experiment.md` §2.2-2.4 的真實 Pro→Team 換帳號
> 資料證偽——單靠 `KNOWN_KINDS` 桶名集合對「同方案換帳號」偽陰性 29%
> （10/35，不限同方案）、對「同帳號自然翻動」偽陽性 2/3。正解已改採
> `account_key = sha256(anthropic-organization-id:anthropic-workspace-id)
> [:12]`（`quota_meter.account_key_of()`，取自 `fetch_usage()` 既有回應
> 標頭，零額外網路／token、不涉憑證處理），已解決「同方案換帳號」與
> 「不同方案桶名集合恰好相同」兩個盲區，桶名分區保留為互補訊號（非取代）。
> 殘餘限制：同一 org/workspace 下方案原地變更且桶名集合恰好不變時仍抓
> 不到（ADR-XPLAT-009 §6 第 1 點；下游 `band_inputs()` floor 不變式保證
> 此殘餘盲區最壞只讓攤提偏保守，不會放寬）。R94：`account_key` 量不到
> （`state.usable()` 為真但 `account_key is None`）此前零觀測性的退化
> 路徑已補 `note_degraded()`（ADR §6 第 2 點／§4）。詳見 ADR-XPLAT-009
> §2.2／§6／§4；交叉引用 DEF-200-122／§6

**當回合實測**：`grep -n "def account_key_of" tools/lib/quota_meter.py` → :620；
`grep -n "def note_degraded" tools/lib/quota_gate.py` → :526；三支 D1 命名回歸鎖
（`test_core_signature_reports_degraded_when_usable_but_account_key_is_missing`／
`test_core_signature_stays_silent_when_account_key_is_present`／
`test_core_signature_does_not_double_report_an_unusable_state`）→
`3 passed, 394 deselected in 0.11s`。

### §J-2 `DEF-200-140`（新列，R94 首列）：D1 發現——account_key 退化路徑零觀測性

獨立 SD 複審（阻塞項）指出：`account_key_of()` 量不到（標頭缺席）時
`core_signature()` 退回裸桶名指紋這件事此前**完全靜默**——`state.usable()` 為真
（量測本身成功）卻 `account_key is None` 時無任何觀測痕跡，而這正是
`Quota_R90_CrossAccount_Experiment.md` §2.2 已實測「29%（10/35）跨方案指紋逐字
相同」那個碰撞面會真實命中的路徑。修法：比照既有六種退化路徑（stale-cache／
schema-mismatch／no-credentials／ledger-unreadable／meter-crashed／
policy-invalid）同一套接上 `note_degraded()`，`usable()==False` 或
`account_key` 齊全時皆不得誤觸發（避免雙重通報或掩蓋既有 unusable 通報）。

### §J-3 時鐘推進的連帶檢查依據

`DEF-200-139`（R93 首列）落地後現查 `current_round()=93`；本節 `DEF-200-140`
落地後現查為 **94**（見下方終驗逐字輸出）。時鐘推進前，`--unresolved-count`
與孤兒稽核逐字輸出見帳本主檔改派紀錄；`DEF-200-128` 之處置見帳本狀態欄。

### §J-4 R94 改派稅：27 列未結列承接輪次 **R93 → R94**

`DEF-200-140`（R94 首列）落地推進帳本時鐘至 R94，硬規則② 使所有「承接輪次：R93」
的未結列當場過期（crossref 實測孤兒 27 筆，與 ADR-XPLAT-009 §7 現查值一致）。手法
沿 R86/R92 先例：就地把狀態欄承接輪號字面由 `**R93**` 改寫為 `**R94**`，逐列
byte-中性。**逐列清單**：DEF-200-015／023／042／043／063／065／075／084／086／090／
096／101／106／115／116／117／118／121／124／125／128／129／131／132／133／134／137
（共 27 列）。

**`DEF-200-128` 專項評估（依任務書指示不假結）**：現查「治本」出口——`治本＝「待驗
清單」須附可重跑腳本，不得只列 ID`——尚無通用可重跑腳本落地；現有的
`_reassign_escape_rows()`／`_REASSIGN_FRESHNESS_FROM` 機制（`test_check_defect_log_
crossref.py`）只解決「改派出口新鮮度」這一個子類，非泛用「待驗清單」樣板，且該
機制本身住在測試檔而非可獨立呼叫的 CLI。狀態欄自述「那 6 筆的立即損害本輪已修；
未修的是『清單無可重跑載體』」在 R94 現查下仍為真——治本項尚未落地，故**改派而非
結案**，隨其餘 26 列一併轉 R94。

<!-- guard-total:R94 --> **本輪護欄層累積淨額＝ 84367 → 84406（+39）** —— 成長面
＝D1（account_key 缺席退化路徑補 `note_degraded()`，test_context_budget_guard.py
+34）加上本表自身編修（+5）。streak 第 2／2 輪，R95 起若再正淨額需搬史料抵銷。

<!-- guard-total:R94 --> 護欄層累積總量現值 **84367 → 84406（+39）**；逐項立案即
本節 §J。
