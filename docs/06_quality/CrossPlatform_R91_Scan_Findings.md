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

## §D 本輪未做到的事（誠實劃界）

* **`AUTOSDD_GIT_GUARD_OFF`／`AUTOSDD_CLAIM_GUARD_OFF` 仍不在 `quota_policy.ENV_SPEC`**
  ⇒ 它們從 `.env` 到不了（R82／C2 那條路對這兩個逃生口不成立）。本輪的
  `EveryHookEscapeHatchIsDeclaredTest` 射程刻意只涵蓋 `context_budget_guard.py`：
  把那兩個一起納入會製造兩筆今天無人負責的紅，而那種鎖活不過一輪。
* **`.md` 面的 `flush_to_model` 呼叫站點判準只掃 `.claude/hooks/` 與 `tools/lib/`**
  ⇒ 別處（例如 `tools/*.py`）多一個直接呼叫不會紅。今天那些檔一個都不 import 它。
* **閂鎖「每 5 個百分點重新武裝」未做**（與本案正交，且會打紅具名鎖
  `LatchRearmTest::test_the_same_tier_and_window_still_only_fires_once`）。入場券已備妥：
  `WarnBandLatchTest::test_a_single_session_climbing_76_to_89_speaks_exactly_once`
  把現行行為釘成契約，那個提案一落地就必須先讓它轉紅。
* **PostToolUse matcher 擴面未做**：單次觸發實測 ~280 ms，其中掃逐字稿只佔 ~13%，
  ~240 ms 是行程啟動＋import ⇒ 正解是先壓固定成本，不是加工具名。
* **帳本 33 列 R90→R91 的批次改派未逐列複驗真實狀態**（`DEF-200-136`）；該面由仍 open
  的 `DEF-200-106` 承接。
