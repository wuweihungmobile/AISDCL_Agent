# PRD 修憲草案 — Token 用盡自動喚醒閉環（usage 水位喚醒閉環設計）

> **Status：Adopted**（掌舵者 2026-09-01 技術債總清償循環令 D2 落款生效；獨立四方複審紀錄＝零、
> 由掌舵者直接落款。落款載體＝
> `docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` 修訂表 v2.1.12 列（同日補列），批次序＝
> v2.1.10（配速）→ v2.1.11（ADR-XPLAT-014 五歧異）→ **本批 v2.1.12**。
> 原 Status＝Proposed（待四方同審＋掌舵者落款））。
> 本檔＝設計波四職能產出（Architect／SA／SD／Developer，2026-08-30）的合成草案；
> 檔名刻意不含版號字面、不匹配 `R*_HANDOFF` glob（非交棒書）。
> 量測數字凡標「R111 量測值」者＝設計波當回合實測快照，**落地時一律現查，不得引用為常數**。
> 修憲程序＝PRD 為最高憲法：四方全同意＋掌舵者落款；有爭議之處列 §6 交裁決。

---

## §0 掌舵者需求情境（逐字引錄）

1. 「Token用盡時，為何沒有啟動下一個Reset的喚醒機制，不需要人類介入，這樣才符合開發自動化」（2026-08-29）
2. 「我發現Token有繼續耗用，但是你這個主要Agent沒有起來…這些背後的Agents沒有人統籌，應該會亂做浪費Token」
3. 「MAC沒有成功過，Windows 11有」
4. 「不是應該有usage % 監控機制，當usage接近滿水位，應該就要啟動喚醒機制」
5. 「請將演算法落實在程式機制，不是光光靠模型判斷」
6. 「因為已經剩 8 hr 55 min, 請把我把剩餘All models Resets in 8 hr 55 min 55% 盡量用完」
   （2026-08-29；逐字出處＝`PRD_Amendment_R108_BurnDown_Addendum.md:73`——「reset 前
   盡量用完」情境一併承接，介面劃界見 §2 P-7 附註）

**事實基礎（兩夜 20% 實損）**：夜1（08-29 22:42 撞 429 →喚醒鏈全段成功→續跑窗口全面唯讀
零推進→接班哨兵被誤拆→12.4 分真空）逐時刻證據＝`docs/06_quality/CrossPlatform_R111_Sentinel_Forensics_Mac.md`
§1~§4（✓已落磁碟）；夜2（08-30 04:03 準時喚醒→2.77MB 重放→又唯讀零推進→又自刪；互動
主控未復活：Monitor 60 分上限到期＋halt 期通知投遞失敗不重投）＝掌舵者實測、現為任務書
轉述——**夜2 鑑識落帳為本批落款前置**（§6-7）。唯讀重放 2.24MB（夜1，✓鑑識檔）／2.77MB
（夜2）≈ 一個 session 窗 20% 純耗損（掌舵者實測；R111 量測值，落地時現查）。
句 3 的正確讀法（防修錯層）：mac 的**喚醒鏈機械段全數成功**，死在授權層唯讀（DEF-200-231②，
射程已擴 mac）與 D3 同名 race＋D4 stamp 殘留——「沒有成功過」＝**閉環**沒成功過，不是鏈沒動過。

---

## §1 需求分解（REQ-W1~W7；逐字句 → 可驗收條目）

| 掌舵者逐字 | REQ |
|---|---|
| 句 1（撞線零人工閉環） | REQ-W1（W6/W7 為其成立前提） |
| 句 2（無人統籌亂燒） | REQ-W2＋REQ-W7 |
| 句 3（mac 沒成功過） | REQ-W3 |
| 句 4（usage % 滿水位啟動） | REQ-W4 |
| 句 5（演算法進程式） | REQ-W5（橫切全部） |
| 句 6（reset 前用完） | §2 P-7 附註（清倉×喚醒介面劃界） |

- **REQ-W1 撞線→零人工→reset 後喚醒→真做工閉環**：既有鏈（偵測→改排→探測→選路→spawn）
  兩夜實證全綠；新增 (c) 續跑窗口能寫檔（DEF-200-231②＝acceptEdits，兩平台同一條 argv）、
  (d) 收窗必留推進證據事件 `resume_progress {edits, writes, verdict}`，verdict ∈
  {progressed, nothing_to_do, blocked_authz, blocked_other}——「唯讀空轉」與「真的無事可做」
  痕跡分形、(e) 收窗不得摧毀喚醒鏈（D3/D4）。驗收＝resume log 事件序列逐字齊備＋
  `verdict=progressed` 時該窗逐字稿內 ≥1 筆 Edit/Write tool_result（值域判準）。
- **REQ-W2 無主模式（DEF-200-234）**：哨兵巡邏 tick 增分支（不新增第二支排程）；主控死∧
  tasks/ 有活體 ⇒ `orphan_agents_detected` 痕跡＋cap 收斂＋loud 通知；統籌權移交續跑窗口
  （開場任務書機械注入無主活體清單）。誠實劃界：哨兵自己死掉的無人窗口蓋不到（Q6 劃界 (a)）。
- **REQ-W3 mac 閉環對等**：授權面兩平台同一條 argv；憑證面各一條規則（mac＝`launchctl print`
  rc＋plist 回讀，禁用 NextRunTime 鍵名）；D3 mac 版（watchdog 不拆接班者）＋D4 原子清 stamp；
  睡眠劃界照舊（睡著不醒＝已知邊界非 bug）。驗收含一次 mac 真實過夜 E2E（§6-5）。
- **REQ-W4 prepare 帶全鏈預檢**：滿水位監控**已存在**（額度四門檻＋prepare 帶任務書＋
  桌面提醒）；缺的是撞線**之前**驗「整條鏈接起來能走通」——新增預檢 P1~P6（哨兵活性／
  allow_resume／任務書 RELAY 塊／授權面／重放成本／mac 睡眠姿態），零 token、掛既有巡邏
  tick 與 PostToolUse 鉤子，每項留 `resume_preflight {item, rc}` 痕跡。
- **REQ-W5 演算法全落程式**：每格指名機械物；判準收在值域（rc、事件名、bytes、NextRunTime
  值）；「模型醒來後自行判斷要不要繼續」的措辭在新條文中零出現——可不可以做由 argv＋hook
  決定，做什麼才是模型的。
- **REQ-W6 喚醒成本治理**：(a) spawn 前授權 fail-fast（唯讀 ⇒ 禁全量重放）；(b) 成本閘由
  單一 byte 常數（32MiB）改導出式（重放成本 ≤ REPLAY_BUDGET × 額度視窗；值住 ENV_SPEC
  不進 PRD）；(c) `autoclaude_resume_cost_pp` 落帳（PRD §11.3 既有要求、兩夜皆無此值＝
  規格既存實作債）。
- **REQ-W7 通知重投與主控復活語意**：(a) 投遞失敗進持久 notify_queue＋巡邏 tick 重投＋TTL；
  (b) 復活語意＝統籌權移交續跑窗口＋通知與任務書逐字給 `claude -r <sessionId>` 接回指令
  （不承諾復活互動視窗）；(c) 跨 reset 等待禁以 Monitor／ScheduleWakeup 承重（升規範性禁令）。

---

## §2 修憲條文草案 P-1~P-7（逐條：機械物／憑證／失效可偵測）

| # | 條文動作（落點） | 機械物 | 憑證 | 它自己死了誰知道 |
|---|---|---|---|---|
| P-1 | §4.5 任務書載體：暫存單寫改「持久目錄為主＋暫存鏡像」，登記 **W-FRESH** 判準（mtime ≥ 撞線時刻−ε ∧ 四段 marker 齊） | 任務書寫入路（planner）＋W-FRESH 純函式 | 檔存在＋W-FRESH 兩綠落痕跡 | 同秒死時任務書缺席 ⇒ W-FRESH 紅 ⇒ 選路不得走摘要路（fallback 保留） |
| P-2 | §4.5 選路優先序增軸：W-FRESH 兩綠 ⇒ FRESH＋任務書（成本 KB 級）；紅 ⇒ SESSION_RESUME fallback；`saved_bytes` 落款 | `choose_resume_route()` 增軸（🔴 動 `ResumeRouteDegradesOneWayTest` 方向鎖＝修憲面，本條即其憲法載體） | `route_chosen strategy=FRESH_PLAN saved_bytes=N` | 事件缺列＝那一步沒走；成本累積值可由掌舵者對帳 |
| P-3 | §4.5.4 後增「喚醒 preflight」節：A-PRE 三格（argv 含 acceptEdits／`AUTOSDD_RESUME_OFF` 未設／prompt 先於變長旗標），任一紅 ⇒ 拒啟動＋rc≠0＋loud | planner spawn 前純本地判準（§3-2） | `resume_authz_preflight_failed` 痕跡＋rc | 判準自身進根層 unittest 紅綠自證；靜態檢防不了執行期形態 ⇒ P-4 雙保險 |
| P-4 | 新增「做工憑證」節：work_receipt（files_changed／驗證 rc；**雙寫**＝prompt 收尾義務＋planner 子行程結束後自量 `git status --porcelain`）＋判準「rc=0 ∧ files_changed=0＝空轉」 | `_run_resume` 後檢＋wake_verdict 三值（§3-1） | `work_receipt files_changed=N` 痕跡＋完成標記檔 | planner 自量那一半不依賴模型合作；標記缺席＝`resume_blocked`（非終態）＋loud |
| P-5 | 新增「接力鏈」節：三布林 AND 續排（任務書有未完項 ∧ 額度 open ∧ 本窗 files_changed>0）⇒ 同 reset 窗內重排下一窗；**零推進即停**＋接力上限 N（雙煞車） | 收窗機械判（§3-3） | 續排憑證＝平台各自（NextRunTime 值／launchctl rc＋plist） | `files_changed=0` ⇒ 停＋escalate(loud)；N 上限擋無限接力；N 取值＝實測（§5-4） |
| P-6 | 新增「無主統籌」節：orphan_scan 三值判準＋偵測即出聲＋cap 收斂；**處置＝不自動終止**（§5-1 掌舵者代決存證） | 哨兵 tick 分支（§3-5） | `orphan_agents_detected` 事件＋補投憑證 | 與哨兵同一條命（Q6 有界失明）；不另立同型單點 |
| P-7 | 告警投遞憑證與補投：alert 每次投遞落 `delivered=true/false`；false 進持久 notify_queue，巡邏 tick 補投、TTL、`notify_redelivered {attempt, rc}` | §3-4 佇列 | 投遞憑證＝通知器 rc（osascript／toast），非「有呼叫過」 | 沒觸發＝queue 檔不長大；條件在＝每巡必再投（≤900s） |

**P-7 附註（句 6 介面劃界）**：清倉模式（BurnDown QB1~QB6 已裁）與喚醒鏈的介面＝
**清倉期撞線 ⇒ 喚醒鏈照常武裝（清倉不豁免哨兵）**；本批只做此劃界句，QB 條文不重述（去重）。

---

## §3 演算法規格（SD 檔規格語意；每項附紅綠自證清單）

### §3-1 哨兵 tick 狀態機修訂（A-1 受阻不進 TERMINAL／A-2 D3 代次／A-3 D4 原子清 stamp／A-4 無主分支）

- **A-1**：resume 臂結局三值 `wake_verdict(rc, canary_hit)` ∈ {worked, blocked, unmeasurable}
  ——憑證＝磁碟事實（canary／完成標記），**rc 不承重**（兩夜形狀＝rc=0＋零做工）。blocked ⇒
  狀態字 `resume_blocked_authz`／`resume_blocked`（與 `resumed` 互異）、不自刪、掛回巡邏＋loud，
  **不進 TERMINAL**（`TERMINAL_STATES` 刻意不加 `resume_blocked`，並補具名負存在測試防「順手補列」；
  `resume_declined`＝終態、人已被 loud 通知）。殭屍上界＝既有 `SENTINEL_IDLE_SECONDS` 自我解除照舊。
- **A-2（D3 代次）**：武裝代次 `arm_gen = f"{epoch_ms}-{pid}"`（毫秒＋pid：同秒雙武裝是實測
  常態，秒級戳分不出「舊我」與「接班者」）；三處同值寫入（armed stamp JSON／狀態塊／排程器
  載體：win＝Action 引數 `--arm-gen`、mac＝plist `EnvironmentVariables.AUTOSDD_ARM_GEN`）。
  一切自我移除先比對「排程器現持代次 == 我的代次」，不等 ⇒ 跳過＋`successor_preserved` 痕跡；
  量不到（None）⇒ 照移除但痕跡記 held=None。mac deferred watchdog 最小實作變體＝
  plist-存在守門（disarm 先刪 plist、接班者必重寫 plist ⇒ `[ ! -f plist ]` 才 bootout）——
  與代次判別同義於「不拆接班者」，實作批擇一並以 T-a4 紅綠釘住。夜1 回放：接班者 23:06:14
  武裝 ⇒ 23:10:33 watchdog 走 skip 臂 ⇒ 12.4 分真空消失。
- **A-3（D4）**：所有移除路徑一律走 `remove_and_unlatch()`（移除＋清 armed stamp＋留痕，
  同一原子動作）；修後「stamp 在、工作不在」唯一代表外部刪除或清理失敗（歸因無噪音）。
- **A-4（無主分支）**：`ownerless_verdict(main_idle, agents_idle, unhandled_event)` 三值
  {ownerless, owned, unmeasurable}（量不到 ≠ 無主）；活體判定＝零侵入心跳（harness 逐字稿
  mtime 新鮮度，非裸 pgrep——鐵律六比對面不含自己）；ownerless ⇒ 條件標記＋claim_once 節流
  loud 重投（投遞失敗不終結條件，下一巡 ≤900s 必再投）；條件解除 ⇒ 清標記＋`ownerless_cleared`。
  Phase 2（hook 側機械擋無主活體的展開型工具）本批不做（hook raw-line 餘裕 1，R111 量測值）。

紅綠自證（SD §2 (a) 組，全數新增）：T-a1 blocked 不寫 resumed 不刪排程／T-a2 wake_verdict
三格互異（rc 承重的實作必紅）／T-a3 win 代次跳過＋held==mine 控制組照刪／T-a4 mac 合成夜1
語料（修前 bootout rc=0＝紅、修後 successor-preserved）／T-a5 四臂走完 stamp 皆清／
T-a6 ownerless 三控制組／T-a7 條件在必重投、解除即閉環／T-a8 新事件名與既有詞彙零撞。

### §3-2 C1 授權 preflight（fail-fast 探針）

全量重放**之前**先花一次「零 context、單 turn」極小探針驗 Edit 權：`authz_probe()` 以
nonce 寫 canary 檔為唯一憑證（`--permission-mode acceptEdits`＝與喚醒同一份授權面）；
verdict 三態不塌陷（429/limit 形態＝unmeasurable 走短退避，絕不判 blocked——量不到 ≠ 無權）；
同 reset 窗 claim_once 一次；blocked 四件套＝`authz_probed verdict=blocked` 痕跡＋
`resume_blocked_authz` 狀態字＋loud alert＋哨兵掛回巡邏（不自刪）。誠實劃界：探針是必要
非充分（canary 寫得動 ≠ repo 全落點寫得動；治理面唯讀仍在＝刻意）。另有零 token 靜態層
（Dev ②-A：`claude --help` 驗旗標存在性，CLI 升版漂移第一時間紅）。
紅綠（SD §2 (c) 組）：T-c1 憑證是 canary 不是 rc／T-c2 blocked 後 `_run_resume` spy=0
（耗損解的機械證明）／T-c3 limit 形態＝unmeasurable／T-c4 同窗一次／T-c5 spawn 例外＝
unmeasurable＋痕跡／T-c6 canary 雙向自清。

### §3-3 A2 接力鏈（雙煞車）

收窗時機械判「要不要排下一窗」：`任務書有未完項 ∧ 額度 open ∧ 本窗 work_receipt.files_changed > 0`
三布林 AND ⇒ 同 reset 窗內重排下一支續跑排程；**煞車一**＝`files_changed=0` 零推進即停
（轉 escalate(loud) 叫人，不再燒）；**煞車二**＝接力上限 N 窗（取值＝實測，§5-4）。
把單窗 timeout=3600 的 1h 硬上限變成有界多窗；「亂做浪費 Token」由雙煞車＋P-6 cap 收斂治。
明確不做 A3 互動主控復活（三理由否決照錄＝§5-2）。
紅綠：注入（未完項×額度×files_changed）八格真值表 ⇒ 僅 (T,T,T) 續排；零推進格斷言
escalate 恰一次＋零續排；接力第 N+1 窗必不排（上限紅面）。

### §3-4 通知補投佇列

alert/notify 每次投遞落 `delivered` 布林（憑證＝通知器 rc：mac osascript／Windows toast，
不是「有呼叫過」）；false ⇒ 該則寫入持久目錄（`trace_dir()` 旁、同壽命紀律）notify_queue；
每巡邏 tick 重投，成功或逾 TTL 才出隊；每次重投落 `notify_redelivered {attempt, rc}`（重試
上限 3 次，次數落痕跡）。「halt 期投遞失敗即丟」（DEF-200-236）由此閉合。
紅綠：注入通知器 rc≠0 ⇒ queue 檔長大＋下一 tick 重投；控制組投遞成功 ⇒ queue 不長大；
TTL 逾期出隊留痕。

### §3-5 stamp-vs-launchctl 自癒（L-a 擴面，PostToolUse 順帶）

`maybe_arm()` latched 臂改 `heal_latched()`：毫秒級 in-flight 判別（`ARM_GRACE_MS` 內不動作，
防誤殺剛武裝者——秒級戳在「SessionStart 清閂→PostToolUse 立刻武裝→下一呼叫立刻查」序列上
必假紅）＋claim_once 節流現查排程器＋三態（[]→清 stamp＋respawn；[task]→alive；None→
unmeasurable 不動作）；respawn 失敗＝loud＋stamp 已清（下一呼叫走正常武裝路＝自癒的自癒）。
紅綠（SD §2 (d) 組）：T-d1 剛武裝不得判死／T-d2 三態注入／T-d3 節流計數=1／T-d4 respawn
失敗不留 stale stamp／T-d5 舊格式 stamp mtime 兜底。

---

## §4 落地排程與代碼落點（Developer 檔；LOC 皆 R111 量測值，動工前現查）

| 批 | 輪次 | 內容 | 前置 |
|---|---|---|---|
| 批0 ⓿ 抽共用模組 | R112-a | planner 749/750（headroom=1）⇒ 選路家族抽 `tools/lib/resume_route.py`（純搬遷零行為變；ADR-014 §7.0 已裁硬前置） | 無；🔴 單人窗口 |
| 批1 D 止血 | R112-b | D1 狀態字不說謊（`resume_declined`／`resume_blocked` 新字面）＋D2 loud alert＋D3 雙平台接班守門＋D4 三臂原子清 stamp＋C11' `allow_resume` 欄＋`sentinel_lifecycle.py:128` 文案分載（08-16 形狀≠R111 形狀） | 無（可與批0同窗） |
| 批2 授權面 | R113-a | 兩路 argv 帶 acceptEdits＋B4 `permission_mode` 痕跡欄＋C1 preflight＋完成標記憑證 | 批0；Q7 已執行 |
| 批3 時刻階梯 | R113-b | L0~L4＋F1~F3＋刪 `DEFAULT_AT_EXPR`（ADR-014 §2 原樣承接） | 批0 |
| 批4 L-a 自癒 | R113-c | §3-5（`sentinel_lifecycle_arm.py` headroom 326；hook 呼叫端零增量） | 無（與批3並行，持有面不相交） |
| 批5 成本面 | R114-a | (i) `route_chosen` 補 `transcript_bytes`/`cap_bytes` 欄（先行不待裁）；(ii) 選路改軸＝P-2（**修憲通過後**才動 `ResumeRouteDegradesOneWayTest` 方向鎖） | (ii) gated on 本批落款＋231②＋C1 先行（§5-3） |
| 批6 無主模式 | R114-b | §3-1 A-4＋§3-3 接力鏈＋§3-4 佇列（DEF-200-234/235/236） | 量測面照 §3-1 A-4（零侵入心跳） |
| 批7 修憲落款 | 依序 | 本檔 → PRD 修訂表（四方＋掌舵者） | v2.1.9＋v2.1.10 合併同審 → v2.1.11 之後 |

代碼落點（實讀座標，R111 量測值）：planner `:1306-1315`（三臂）／`:1155-1202`（`_run_resume`）／
`:1120-1143`（選路）／`:660-691`（`sentinel_decide` 增 `peers_active` 輸入）／`:287`（刪
`DEFAULT_AT_EXPR`）；`sentinel_lifecycle.py:54`（TERMINAL_STATES 加 `resume_declined`，
`resume_blocked` 刻意不加）＋`:128`（文案）；`sentinel_lifecycle_arm.py:161-186`（latched 臂）；
`schedule_backend.py:734-753`（mac watchdog 守門）＋`:529-548`（disarm）。LOC 硬約束：
planner ≤+10（胖身體全下 lib）；`schedule_backend.py` 360/400 為最緊一格（超線先搬史料抵銷）；
`context_budget_guard.py` raw 1088/1089 **零增量鐵則**。既有測試地圖與方向鎖盤點＝設計波
Dev 檔 ③ 節（`ResumeRouteDegradesOneWayTest`＝批5(ii) 正面衝突點，未修憲前動它＝違規）。
回退單元＝批（每批單一 commit，`git revert` 一步回滾）；失手方向一律偏「留」不偏「拆」。

---

## §5 掌舵者已代決事項存證（依最高原則代決，四方同審時可推翻）

1. **orphan 處置＝偵測＋出聲＋cap 收斂，不自動終止**——終止權（殺別人的工作）不下放給
   無人看管行程，留掌舵者明示裁決；裁決前機械預設＝偵測＋loud＋落痕跡＋cap 收斂到
   `cap_prepare` 語意以下（沿 §4.1.5 fail-safe 判例）。
2. **「主控復活」語意＝統籌權移交 headless 接力窗口＋通知附 `claude -r <sessionId>` 接回
   指令**。A3（互動主控復活）三理由否決照錄：(i) wexpect pty spawn 掛住＝DEF-101-913 既載
   未解；(ii) 人不在時「互動 session」就是一個沒有 timeout 的 headless，風險面更大而憑證面
   更弱（無 `-p` 的結構化收尾）；(iii) mac 需 osascript 開 Terminal＝新增平台專屬移動零件，
   且它自己死了無人知。
3. **C2 摘要續跑（P-2 選路改軸）納入本批**，gated on 231②＋C1 先行——231②＋C1 落地後
   即使仍走全量重放，那 20% 至少換到真做工；改軸落地必隨本批修憲同批動方向鎖。
4. **N（接力上限）與 REPLAY_BUDGET 取值＝實測，禁憑空**——一窗平均可完成工作量與重放
   成本分佈量測後定值，值住 ENV_SPEC 不進 PRD（R-4.5.10-3 判例）；`ARM_GRACE_MS`／
   `AUTHZ_PROBE_TIMEOUT_SECONDS`／ownerless 三常數同此紀律（名字與家先登記＝§2 P-6 表尾）。

---

## §6 開放問題殘餘（未被 §5 覆蓋者；交四方複審／掌舵者）

1. **任務書雙寫（P-1）的持有面**：`~/.autosdd/` 已是 traces 持久家；任務書搬入是否與
   `AUTOSDD_TRACE_DIR` 逃生口共用 SSOT（`tools/lib/endurance_env.py`）＝實作批確認。
2. **決策痕跡雙寫**：哨兵四分支決策事件現只住系統暫存（重開機即失）——死亡決策類事件
   是否雙寫 `trace_dir()`（成本＝多一個寫點，SD 權衡）。
3. **是否同時收緊 `AUTOSDD_RESUME_MAX_TRANSCRIPT_BYTES` 出廠值**（32MiB）：P-2 導出式
   成本閘落地後該常數的角色（絕對上限 vs 退場）。
4. **無主活體偵測母體的假紅普查**：零侵入心跳（jsonl mtime）落地前照紀律跑
   `shell_command_corpus --corpus transcripts` 型普查，K 分鐘閾值以量測定。
5. **mac 真實過夜 E2E 由誰排、何時排**（REQ-W3 驗收 3 的證據；排程本身照〈反事後諸葛〉附憑證）。
6. **修憲批堆疊**：v2.1.12 與 v2.1.11 是否合併同審（R110 已判「未生效修憲不疊層」——
   五層堆疊風險；本批依裁決鏈排在 v2.1.11 之後）。
7. **夜2 鑑識落帳**（本批落款前置）：§0 的夜2 事實（04:03、2.77MB、Monitor 到期、通知不重投）
   現為任務書轉述——落款前須補進 `CrossPlatform_R111_Sentinel_Forensics_Mac.md`（增 §5 夜2 節）
   成為可引用證據，否則 v2.1.12 引用不存在的出處（「宣稱先於查證」形態）。
8. **夜2 兩新缺口已立帳**（本批完成）：Monitor 60 分上限到期無人接手＝**DEF-200-235**；
   halt 期通知投遞失敗不重投＝**DEF-200-236**（皆 `docs/06_quality/AutoSDD_Defect_Log.md`，
   發現情境欄零輪號體例、open（未指派）＋解鎖條件指向本檔 §3/§5 設計）。
9. **wake 做工憑證與 authz 探針部分重疊**：探針測「能不能」、憑證測「有沒有」——設計建議
   兩者都要；若掌舵者裁「探針已足」可裁掉 post-run 憑證半格換簡單性。
10. **ownerless Phase 2**（無主期機械擋活體的展開型工具）需 hook 側減法先行：是否為
    `context_budget_guard.py` 開一輪 ⓿ 型瘦身（raw-line 餘裕 1，R111 量測值）。
