# AutoClaude 核心排程與 Token 治理系統規格說明書 (PRD)

| 文件版本 | 修訂日期 | 狀態 | 核心目標 |
| :---- | :---- | :---- | :---- |
| **v2.1.0 (Revised + Verified)** | 2026-08-14 | Ready for Implementation | 在**遵守** Anthropic 額度限制的前提下，實現零 Token 消耗的額度遙測、可收斂的動態併發配速、以及成本可預期的無損暫停／喚醒 |
| **v2.1.1 (R92 修憲)** | 2026-08-16 | Ready for Implementation | 掌舵者裁決：`CONTEXT_COMPACT_PERCENT` 75→84（§4.3、§6 兩站點），並首次把 context 硬線 94% 入憲（此前僅存在於實作層 `HARD_RATIO`，PRD 未定義）；與額度尺 85/95 錯開保鑑別力。機械 autocompact 設定之取捨見 ADR-XPLAT-008 |
| **v2.1.2（R93 新增）** | 2026-08-16 | Ready for Implementation | 新增 §4.1.4：跨窗攤提的核心指紋隨帳號/方案核心桶集合變化自動分區，解決 `DEF-200-122`（換方案上升跳變污染燃燒率估計）；`DEF-200-114` 的機制本體同輪落地。設計細節見 ADR-XPLAT-009 |
| **v2.1.3（R93 二次訂正）** | 2026-08-16 | Ready for Implementation | 獨立 Architect 複審 REJECT 承接：§4.1.4「同方案換帳號需帳號識別，非本節範圍」與 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md` 實測不符（核心桶集合指紋本身不具身分鑑別力：3 命中 2 假陽性、29% 偽陰性），訂正為已解決——帳號身份訊號（回應標頭雜湊，零額外網路/token/憑證處理）併入核心指紋；補齊「不同方案桶名集合相同」邊界。設計細節見 ADR-XPLAT-009 §6 |
| **v2.1.4（T5 修憲）** | 2026-08-16 | 經掌舵者 2026-08-16 拍板、待四方複審後生效 | 解除 PRD 內部三角衝突（§15.5 紅線 1「不碰未公開端點」↔ 現行唯一取數源即 §4.1.1 T5 ↔ §12「不得讀 OAuth token」為呼叫 T5 的必要前提所必違）：T5 升格為認可主源（零 token、帳號層級權威讀數、R90 四通道實測勝出、失效 fail-safe 降級 cap=4，見 §4.1.1〈T5 升格依據〉）；紅線 1 加收窄豁免（唯讀 GET／單一程式站點 `tools/lib/quota_meter.py`／TTL≥180s 節流／失效降級出聲）；§12 憑證條改為「允許唯讀取用、禁止落痕跡」劃界。§0.6 表與附錄 B-05 的「T5 可整條刪除」保留為 v2.1 核實當時的歷史紀錄，不再是現行規範 |
| **v2.1.5（撞線喚醒閉環修憲）** | 2026-08-17 | 經掌舵者 2026-08-17 立案（「Token 用盡時，為何沒有啟動下一個 Reset 的喚醒機制，不需要人類介入」）、待四方複審後生效 | 新增 §4.5.6：需求層明確化「任一執行層級撞線 → 零人工 → reset 喚醒續跑」，覆蓋面必含 (a) subagent／workflow agent 撞線、(b) **主 session 活著但帳號級撞線**（該回合死於 API 層、hook 體系零觸發點）兩情境；喚醒機制自身失效必須 fail-loud 且可自癒（禁止 fail-quiet 自我解除）；可重啟點任務書的骨架重寫不得摧毀機器可讀狀態塊（單檔雙寫者禁令）。立案證據＝2026-08-16/17 事件（哨兵武裝且巡邏十次全綠，卻在撞線落地後 4 分鐘死於被 halt 動作覆寫的任務書而自我解除，03:50 reset 時機器上零排程，空轉至人工介入；逐字證據與逐環驗證見 ADR-XPLAT-004 §2.9）。設計細節與實作工作清單見 ADR-XPLAT-004 §2.9 |

> **v2.1 的變更**：附錄 B 的事實核對清單已**實際核實完成**（方法見附錄 B 開頭）。核實結果顯示 Claude Code v2.1.x **已內建**本 PRD 原本打算自建的多項能力（原生 worktree 隔離、任務 DAG、排程喚醒、零 Token 用量遙測、併發上限、官方配速門檻）。因此新增 [§15 執行方法論](#15-執行方法論與注意事項v21-新增)，並將建議架構從「大型自建 Daemon」縮減為「薄治理層 + 採用原生能力」。**§15 是實際動工時應遵循的章節**（含動工前置檢查、採用 vs 自建決策矩陣、P0–P5 分階段步驟、12 條紅線注意事項、參數校準方法與交付目錄結構）。

> **v1.0.0 → v2.0.0 修訂性質**：本版並非潤稿，而是修正 v1 中 **3 項架構級邏輯錯誤**、**6 項控制理論缺陷**、**11 項規格缺漏**與若干事實／數值錯誤。完整問題清冊見 [附錄 A](#附錄-av1--v2-問題清冊issue-register)。
>
> **重要前提（v2.1 更新）**：文中 `[需核對]` 標記多數已於附錄 B 完成核實，核實方法為直接檢視 `@anthropic-ai/claude-code` v2.1.232 的官方 npm 發佈內容與原生二進位。**但核實來源是實作內部字串，不是官方文件承諾的公開介面** —— 其中部分為功能旗標或內部識別字，可能隨版本變動。凡標示「內部」者，實作時必須有降級路徑，不可硬依賴。

---

## 目錄

**如果你只讀一章：** 決策者讀 [§0](#0-修訂重點摘要給決策者的-5-分鐘版)；**要動工的人讀 [§15](#15-執行方法論與注意事項v21-新增)**（前置檢查、決策矩陣、P0–P5 步驟、紅線清單、參數校準）。

| 章節 | 內容 | 誰該讀 |
| :---- | :---- | :---- |
| [0. 修訂重點摘要](#0-修訂重點摘要給決策者的-5-分鐘版) | v1 的 12 項主要問題與修正 | 決策者 |
| [0.6 情勢變更](#06-情勢變更cli-已內建的能力v21-核實結果) | **CLI 已內建、不必自建的能力清單** | 決策者、架構 |
| [1. 設計原則](#1-執行摘要與核心設計原則) | 七項原則、非目標 | 全體 |
| [2. 名詞與量測定義](#2-名詞與量測定義v1-缺此章是多數錯誤的根因) | 額度率 vs 上下文佔用率的區分 | 全體（**v1 錯誤根源**） |
| [3. 架構與狀態機](#3-系統架構與狀態機) | 狀態表、進入／離開條件、轉移圖 | 架構、開發 |
| [4. 模組規格](#4-模組規格) | 遙測、配速、壓縮、隔離、喚醒、防休眠、仲裁 | 開發 |
| [4.2.8 配速門檻對齊](#428-與-cli-內建配速門檻對齊v21-核實新增) | `pace_index` 形式與官方參考值 | 開發（**建議主控訊號**） |
| [5. API Key 模式](#5-api-key-模式v1-只提一句實際無法運作) | 正規化層與硬性預算 | 開發（僅 API 模式） |
| [6. 設定檔規範](#6-設定檔規範envexample修訂版) | `.env.example` 全量 + 啟動不變式 | 開發、運維 |
| [7. state.json Schema](#7-狀態資料結構規格statejson-schema-v2) | 治理層持久化結構 | 開發 |
| [8. 例外與邊界條件](#8-例外與邊界條件擴充) | 14 項異常處置 | 開發、測試 |
| [9. 可觀測性](#9-可觀測性v1-完全缺漏) | 指標、日誌、告警 | 運維 |
| [10. 設定遷移對照](#10-v1--v2-設定遷移對照) | v1 → v2 參數變更 | 已有 v1 實作者 |
| [11. 驗收與測試標準](#11-驗收與測試標準改為可量測並解決-v1-的矛盾) | 8 組可量測判準 | 測試 |
| [12. 安全性](#12-安全性v1-完全缺漏) | 憑證、權限、注入、供應鏈 | 全體 |
| [13. 合規聲明](#13-合規聲明v1-缺漏但對本類工具至關重要) | 禁止事項與待確認法務項 | 決策者 |
| [14. 路線圖（已被 §15.4 取代）](#14-實作路線圖建議v1-無此章) | v2.0 舊版規劃，僅供對照 | — |
| **[15. 執行方法論與注意事項](#15-執行方法論與注意事項v21-新增)** | **前置檢查、決策矩陣、最小架構、P0–P5、紅線、校準、目錄結構** | **動工前必讀** |
| [附錄 A：問題清冊](#附錄-av1--v2-問題清冊issue-register) | 43 項 v1 問題逐條對應修正 | 審查者 |
| [附錄 B：事實核對結果](#附錄-b事實核對結果v21-已核實) | 核實方法、12 項已確認、8 項新發現、5 項待人工確認 | 開發（**動工前必讀**） |

---

## 0. 修訂重點摘要（給決策者的 5 分鐘版）

| # | v1 的問題 | 嚴重度 | v2 的修正 |
| :-- | :---- | :---- | :---- |
| 1 | **把「上下文視窗佔用率」與「額度使用率」當成同一個指標**，於額度 90% 時觸發 `/compact` | 🔴 阻斷級 | 兩者拆成獨立的量測軸（`U5h/U7d` vs `K_ctx`）。壓縮由上下文佔用驅動，且**壓縮本身會消耗額度**，故必須在 WARN 階段前完成並預留成本預算 |
| 2 | **週上限（7 天）觸發後仍只休眠到 5 小時視窗重置** | 🔴 阻斷級 | 新增 `LONG_HIBERNATE` 狀態與 OS 排程器交棒機制（最長 7 天，不可靠 in-process sleep 撐過） |
| 3 | **配速公式與狀態機互相矛盾**：驗收標準要求 75% 時收斂到 `C_min`，但公式在該情境可能算出 `C_max` | 🔴 阻斷級 | 引入「狀態併發上限表 `C_cap(state)`」，公式的輸出必須再經狀態上限夾緊 |
| 4 | 無遲滯（hysteresis）、無變化率限制、無停留時間 → 在 70%／85% 邊界會震盪抖動 | 🟠 高 | 加入遲滯帶、±1 變化率限制、最小停留時間、EWMA 平滑、死區 |
| 5 | `V_actual` 冷啟動下限在公式（0.01）與程式碼（0.02）不一致；視窗重置時 `ΔU` 為負會誤判成「零燃燒」而暴衝 | 🟠 高 | 統一為單一常數，並新增「視窗重置偵測」清空歷史緩衝 |
| 6 | 遙測失效時的失效方向未定義（fail-open 會直接爆額度） | 🟠 高 | 明定 **fail-safe**：遙測過期即降級，超時即排空 |
| 7 | 宣稱「無損喚醒不重複消耗 Token」，但 `--resume` 在快取失效後會**全額重讀整段對話** | 🟠 高 | 承認並量化此成本；新增 `RESUME_STRATEGY` 讓大型對話改用「新 Session + state.json 交棒」 |
| 8 | 預設在喚醒指令中使用 `--dangerously-skip-permissions` | 🟠 高（安全） | 改為權限模式 + 工具白名單；旁路模式需顯式開啟並隔離於容器 |
| 9 | 多 Agent 以 `git worktree` 隔離，但合併策略只寫「Fast-Forward」 | 🟡 中 | 新增序列化整合佇列（rebase → 驗證 → FF-only merge），並處理分支已存在、worktree 未提交變更、`.gitignore` 等實務問題 |
| 10 | 同帳號多專案／多 Daemon 會各自以為額度充足 | 🟡 中 | 新增帳號層級配額仲裁鎖與 Token Bucket 分配 |
| 11 | `state.json` 只能記錄單一 worktree／session，與多 Agent 設計衝突；`git_commit_hash` 長度非法；`reset_timestamp` 比 `saved_at` 晚 24 小時（5 小時視窗不可能） | 🟡 中 | Schema 升級為 v2（agents 陣列、原子寫入、校驗欄位），並修正範例數值 |
| 12 | 缺少：可觀測性、安全、ToS 合規、Agent 硬性停止、時鐘漂移、Linux 支援、dry-run、人工覆寫 | 🟡 中 | 新增第 12～15 章與相關設定項 |

### 0.6 情勢變更：CLI 已內建的能力（v2.1 核實結果）

核實後最重要的結論：**本 PRD 有將近一半的模組不需要自建。** Claude Code v2.1.x 已提供對應原生能力，自建版本只會多一份要維護的、且更容易出錯的程式碼。

| PRD 原計畫自建 | CLI 已內建（已核實） | 建議 |
| :---- | :---- | :---- |
| §4.1 遙測引擎（含未公開端點） | statusLine hook 的輸入 JSON 直接含 `rate_limits.five_hour.used_percentage` / `.resets_at`、`rate_limits.seven_day.*`、`subscription_type`、`session.total_cost_usd` | **採用**。原 T5（未公開端點）整條刪除 |
| §9 可觀測性 | `CLAUDE_CODE_ENABLE_TELEMETRY` + OpenTelemetry 匯出，含 `claude_code.token.usage`、`claude_code.cost.usage`、`claude_code.compaction`、`claude_code.subagent.spawn` 等；支援 OTLP 與 **Prometheus exporter** | **採用**。自建指標只補「治理決策」層 |
| §4.4.1 自建 git worktree 管理 | `Agent` 工具的 `isolation: "worktree"`；`EnterWorktree` / `ExitWorktree`（含未提交變更的拒絕保護與 `discard_changes` 二次確認） | **採用**。自建 worktree 腳本刪除 |
| §7 `state.json` 內的 task DAG | `TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` / `TaskStop`，支援 `addBlocks` / `addBlockedBy` / `metadata` / `owner` | **採用**為主，`state.json` 只保留治理層狀態 |
| §4.2 併發致動器（自行管理多個 CLI 行程） | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`、`CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`、`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`、`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | **改為調整設定值**，而非自建行程池（大幅簡化） |
| §4.5.5 OS 排程器交棒 | `CronCreate`（`durable: true` → 寫入 `.claude/scheduled_tasks.json`，跨 session 存活，**7 天後自動過期**）；`ScheduleWakeup`（延遲**夾在 60–3600 秒**） | **混合**：短等待用 `ScheduleWakeup`，跨 5h 用 cron 或 OS 排程；`ScheduleWakeup` 上限 1 小時，**無法單次撐過 5 小時視窗** |
| §4.2 配速門檻（憑猜測） | CLI 內建的「超前燃燒」判準表（見 §4.2.8），提供官方參考值 | **對齊**，不再自訂憑感覺的水位 |
| §4.3 壓縮治理 | 自動壓縮已內建（`CLAUDE_CODE_AUTO_COMPACT_WINDOW`）；`PreCompact` / `PostCompact` hook 存在 | **採用** hook 做壓縮前 checkpoint，不自行下達壓縮指令 |

**新發現、PRD 完全遺漏的維度：**

1. **超額用量（overage / extra usage）**：額度類型除 `five_hour`、`seven_day` 外，還有 `seven_day_opus`、`seven_day_sonnet`、`seven_day_overage_included`、`overage`、`extra_usage`，且有月度支出上限與 `overage-utilization` 概念。**這代表達到訂閱限制後可能可以付費續跑**，治理決策從「凍結」變成「凍結 or 付費續跑」二選一 —— 必須是顯式設定，不能預設替使用者花錢。見 §6 的 `OVERAGE_POLICY`。
2. **額度狀態是枚舉不只是百分比**：`allowed` / `allowed_warning` / `rejected`，配合 `resetsAt` 與 `rateLimitType`。**應以此枚舉為主要狀態訊號**，百分比僅作為配速輸入 —— 比自訂水位可靠得多。🔴 **通道限定（R90 補；語意不變，只補「它住在哪」——附錄 B-13 已寫對，本條與 §15.5 紅線 7 漏寫）**：此枚舉的唯一載體是**模型 API 呼叫的限流回應標頭**（`anthropic-ratelimit-unified-status`）。⇒ 本條只對「本身會發模型請求、因而拿得到那組標頭」的元件成立；**不發模型請求的純觀測型元件結構上取不到它**，對它們而言百分比不是「次要訊號」而是唯一可得訊號。依據＝R90 四通道實測（`/api/oauth/usage` body 與其回應標頭、statusLine stdin、逐字稿，四條皆 0 命中），見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md`。
3. **週額度依模型分軌**：`seven_day_opus`、`seven_day_sonnet` 為獨立額度（Max / Team 方案可見），證實 v2 的「模型降級致動器」方向正確且可實作。
4. **前置條件**：Node.js ≥ 22；CLI 現以各平台原生二進位發佈（含 `linux-x64-musl`、`linux-arm64`、`win32-arm64`）。v2 對 Linux 支援的批評（A-24）成立。

---

## 1. 執行摘要與核心設計原則

### 1.1 背景與痛點（維持 v1 判斷，補充精確定義）

以 Claude Code 進行長時間、多 Agent 自動開發時，額度限制會以三種不同機制生效，**三者需分別治理**：

1. **5 小時使用視窗**：達上限後暫停使用，等待該視窗重置。
2. **每週（7 天）上限**：達上限後最長需等待數天，**無法靠短暫休眠規避**。
3. **每週特定模型上限**（如高階模型另有獨立週額度）。

缺乏外部治理時的具體損害：
- 任務在 Token 耗盡瞬間被截斷 → 程式碼半寫入、Git 工作區髒污、測試狀態不明。
- 固定併發數在額度充裕時吃不滿、在額度告急時瞬間撞 429。
- 缺乏喚醒機制 → 上下文丟失，或喚醒時付出未預期的全額上下文重讀成本。

> `[需核對]` 上述三種限制的**確切名稱、單位、重置語意（固定視窗 vs 滾動視窗）與是否對外暴露 reset timestamp**，必須以官方文件為準。v1 文中「72 小時／7 天」的混用已刪除——「72 小時」並非已知的限制週期。

### 1.2 核心架構原則（新增 3 項）

1. **控制面／執行面分離（Control Plane vs Execution Plane）**
   - **LLM 是執行者（Worker）**：只負責程式碼生成與工具調用。
   - **Daemon 是指揮官（Governor）**：獨立行程，負責遙測、配速、生命週期、狀態保全。Daemon 本身**不得**呼叫任何 LLM。
2. **零 Token 消耗遙測（Zero-Token Telemetry）**
   - 一律透過**本地既有產物**（結構化遙測輸出、對話記錄檔、statusline 回寫）取得用量；**嚴禁**用 Prompt 探測額度。
3. **雙軸額度防護（5h Window ∧ Weekly Cap）**
   - 任何派工決策必須同時通過 5 小時視窗閘門與週上限閘門，取**最保守**者。
4. **狀態無損與優雅退場（Graceful Drain & Lossless Resume）**
   - 階梯式減速 → 排空 → Git 交易保護 → Session 保存 → 精準喚醒。
5. **【新增】失效即保守（Fail-Safe, Not Fail-Open）**
   - 任何遙測不可得、逾時、解析失敗、時鐘異常，系統一律往**更保守**的方向收斂（降併發 → 排空 → 凍結），絕不維持或提高併發。
6. **【新增】量測軸分離（Quota ≠ Context）**
   - 「帳號額度使用率」與「單一 Session 上下文佔用率」是兩個獨立變數，各有各的門檻與動作，不得混用（v1 的核心錯誤）。
7. **【新增】合規優先（Compliance by Design）**
   - 本系統的目的是**尊重並平順地貼合**額度限制，而非規避。明確列為非目標：多帳號輪替／共用、憑證共享、任何形式的限流繞過。

### 1.3 非目標（Out of Scope）

- 多帳號輪替或帳號池化以擴大額度。
- 逆向工程／繞過 Anthropic 限流或計費機制。
- 取代 CI/CD；本系統只負責在**開發階段**的自動排程與整合前置作業。
- 為 API Key 模式提供「無上限自動燒錢」；API 模式必須有使用者自訂的硬性預算上限。

---

## 2. 名詞與量測定義（v1 缺此章，是多數錯誤的根因）

| 符號 | 名稱 | 範圍 | 單位 | 資料來源 | 說明 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `U5h` | 5 小時視窗使用率 | **帳號層級**（跨所有 session/專案） | % (0–100) | 遙測引擎 | 決定 WARN／DRAIN／HALT 狀態轉移 |
| `U7d` | 週額度使用率 | **帳號層級** | % (0–100) | 遙測引擎 | 週上限安全閥；亦為 BURSTING 的否決條件 |
| `U7d_model` | 特定模型週額度使用率 | 帳號層級 | % (0–100) | 遙測引擎 | 觸發「模型降級」動作 |
| `T_rem` | 5 小時視窗剩餘分鐘 | 帳號層級 | 分鐘 | `reset_timestamp - now` | 配速分母 |
| `T_rem_7d` | 週額度重置剩餘秒數 | 帳號層級 | 秒 | `weekly_reset_timestamp - now` | `LONG_HIBERNATE` 依據 |
| `K_ctx` | **上下文視窗佔用率** | **單一 Session 層級** | % (0–100) | 對話記錄檔 / statusline | 觸發壓縮的**唯一**依據 |
| `V_safe` | 安全燃燒率 | 帳號層級 | %/分鐘 | 計算值 | 剩餘額度均攤到剩餘時間 |
| `V_actual` | 實測燃燒率（EWMA） | 帳號層級 | %/分鐘 | 計算值 | 平滑後的觀測值 |
| `C(t)` | 當前允許併發 Agent 數 | 系統層級 | 整數 | 計算值 | 控制器輸出 |

**關鍵釐清（v1 錯誤來源）**

- `/compact` 壓縮的是 `K_ctx`（上下文視窗），**不會**降低 `U5h`／`U7d`。
- 壓縮動作本身需要模型讀完整段對話並產生摘要，因此**會顯著推升 `U5h`**。在 `U5h = 90%` 時執行壓縮是反向操作。
- 「額度」是帳號共享資源；「上下文」是每個 session 各自的資源。兩者的門檻不可共用同一組環境變數（v1 的 `TOKEN_COMPACT_PERCENT=90` 已廢除，見 §10 遷移對照表）。

---

## 3. 系統架構與狀態機

### 3.1 架構圖

```
┌───────────────────────────────────────────────────────────────────────┐
│                  AutoClaude Daemon (單一實例，檔案鎖保護)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 1 遙測引擎    │→ │ 2 配速控制器  │→ │ 3 派工/生命週期│  │ 5 可觀測性 │ │
│  │  Telemetry   │  │  Pacing Ctrl │  │  Dispatcher   │  │ Metrics/  │ │
│  │  (零 Token)  │  │  (含遲滯)     │  │  (硬性預算)   │  │ Log/Alert │ │
│  └──────────────┘  └──────────────┘  └──────┬───────┘  └───────────┘ │
│         │                  │                │                         │
│         ▼                  ▼                ▼                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 帳號配額仲裁  │  │ 4 狀態保全與  │  │ 6 Git 整合    │  │ 7 防休眠   │ │
│  │ (跨專案共享)  │  │   喚醒 Resume │  │   佇列        │  │ Keep-Awake│ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └───────────┘ │
└──────────────────────────────┬────────────────────────────────────────┘
                               ▼
        ┌──────────────────────────────────────────────────┐
        │  Claude Code CLI 實例 × C(t)（各綁定獨立 worktree）│
        │  headless 模式 + hooks 回報 + 硬性 turn/時間上限   │
        └──────────────────────────────────────────────────┘
```

### 3.2 狀態機（補上 v1 缺少的進入／離開條件、遲滯、單向鎖存）

| 狀態 | 進入條件 | 離開條件 | `C_cap` | 允許的動作 |
| :---- | :---- | :---- | :---- | :---- |
| `INIT` | 程序啟動 | 環境驗證通過且取得首次遙測 | 0 | 驗證設定不變式、取得帳號基準、掃描殘留 state.json |
| `CRUISING` | `U5h ≤ WARN − HYST` 且週閘門通過 | 任一升級條件成立 | `C_max` | 正常派工 |
| `BURSTING` | 見 §4.4 突刺判準（全部成立） | 任一判準失效 | `C_max` | 全速派工 |
| `THROTTLING` | `U5h ≥ WARN` 或 `U7d ≥ WEEKLY_WARN` 或 遙測過期 | `U5h ≤ WARN − HYST` 且遙測新鮮 | `C_throttle` (1) | 降併發、模型降級、禁止高成本任務類別 |
| `DRAINING` | `U5h ≥ DRAIN` 或 `U7d ≥ WEEKLY_DRAIN` 或 遙測逾時 | **僅能由視窗重置離開（單向鎖存）** | 0 | 停止派新工，允許進行中 Step 收尾（受硬性預算限制） |
| `FREEZING` | `U5h ≥ HALT` 或 排空逾時 或 429 重試耗盡 | 保全完成 | 0 | 寫 state.json（原子）、各 worktree commit、釋放 Agent |
| `WAITING_RESET` | 保全完成且 `T_rem_7d` 未觸發長休眠 | 到達 `reset + buffer` 且遙測確認已重置 | 0 | 分片休眠、保持喚醒、定期驗證 |
| `LONG_HIBERNATE` | `U7d ≥ WEEKLY_HALT` | 到達週重置時間 | 0 | **交棒給 OS 排程器**、釋放防休眠、Daemon 可安全退出 |
| `RESUMING` | 遙測確認額度已重置 | 首個 Agent 成功接手 | 1 | 依 `RESUME_STRATEGY` 喚醒；失敗則退避重試 |
| `HALTED_MANUAL` | 使用者下 `autoclaude pause` | 使用者下 `resume` | 0 | 人工覆寫，優先於一切自動決策 |

**單向鎖存（Latching）設計理由**：`DRAINING` 以上狀態不可因用量讀數小幅回落而退回 `CRUISING`。額度使用率是單調遞增的（在同一視窗內），任何「回落」都代表遙測抖動或視窗重置；前者不該觸發升併發，後者應走正式的重置流程。v1 未定義此點，會導致在 85% 邊界反覆進出排空。

### 3.3 狀態轉移圖

```
 INIT ──► CRUISING ◄────────────► BURSTING
            │  ▲                      │
     U5h≥70 │  │ U5h≤67              │ 判準失效
            ▼  │                      │
        THROTTLING ◄──────────────────┘
            │
     U5h≥85 │ (單向)
            ▼
        DRAINING ──► FREEZING ──┬──► WAITING_RESET ──► RESUMING ──► CRUISING
                                │                          ▲
                     U7d≥90     └──► LONG_HIBERNATE ───────┘
                                       (OS 排程器交棒)

 任一狀態 ──(使用者指令)──► HALTED_MANUAL
 任一狀態 ──(遙測逾時>600s)──► DRAINING
```

---

## 4. 模組規格

### 4.1 遙測引擎（Telemetry Engine）

#### 4.1.1 資料來源分層（v1 的重大缺漏：只寫了未公開端點）

依**可靠性與合規性**排序，實作時必須全部支援並可降級：

| 層級 | 來源 | 可靠性 | 備註 |
| :---- | :---- | :---- | :---- |
| **T1（首選）** | Claude Code 的結構化遙測輸出（OpenTelemetry metrics 匯出至本地 collector） | 高，官方支援 | `[需核對]` 啟用方式與 metric 名稱／attributes。此為零 Token、官方支援的正途 |
| **T2** | 本地對話記錄檔（session transcript，內含每則訊息的 token usage） | 中高 | `[需核對]` 檔案路徑與 schema。可自行加總得到「本機消耗」，但**看不到其他機器／其他專案的消耗** |
| **T3** | statusline hook 回寫：由 CLI 主動呼叫的 statusline 腳本，將取得的 session/用量資訊寫入 Daemon 監看的檔案 | 中 | 注意方向：statusline 是 **CLI 呼叫腳本**，不是 Daemon 去輪詢 CLI（v1 描述方向錯誤） |
| **T4** | 官方用量查詢介面（如 CLI 的用量指令）之程式化解析 | 低（輸出格式可能變動） | 需容錯解析，格式變動時降級而非崩潰 |
| **T5（v2.1.4 升格：認可主源）** | 未公開的 OAuth usage HTTP 端點（唯讀 `GET /api/oauth/usage`） | 中高（未公開介面仍可能變動，故失效降級路徑不可拆除） | v1 列為主要方案、v2 降為選用；**v2.1.4 經掌舵者 2026-08-16 拍板升格為認可主源**（依據見下方〈T5 升格依據〉；使用邊界受 §15.5 紅線 1 豁免條款四條件約束） |

**T5 升格依據（v2.1.4，掌舵者 2026-08-16 拍板、待四方複審後生效）**——四項皆為實測結論，不是偏好：

1. **零 token 成本**：該呼叫不是模型推論，不吃額度、不進 5 小時視窗（`tools/lib/quota_meter.py` 檔內 `USAGE_URL` 註解逐字；R90 探針同一結論）。
2. **帳號層級權威讀數**：server 依帳號方案自己算好 utilization 回百分比，本機不自行推導分母；且回應含**全部**計費軸（R90 實測頂層 17 鍵）。對照 T3 statusLine 只回 five_hour／seven_day 兩軸的 `used_percentage`／`resets_at`，結構上看不到 `spend`／`extra_usage`——正是 §15.1 第 3 項認定「本專案最危險的單一失敗模式」所在的軸（R87 事故：該軸撞頂時 13 個 subagent 全滅、燒 1,319,703 tokens，而訂閱窗還有 37% 餘裕）。
3. **R90 四通道實測勝出**：本機可達四通道（端點 body／同 API 回應標頭／statusLine stdin JSON／逐字稿）逐一量測，唯端點 body 給出全軸讀數；見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md` §一。
4. **失效 fail-safe**：任何失效（斷網／401／schema 變動／無憑證）一律回「量不到」且各有可分辨的失效字面；量不到**不是不設限**——降級 cap=4（`tools/lib/quota_policy.py` 的 `Policy.degraded_cap`），方向保守。

T5 的實作站點唯一（端點知識不得有第二個家）＝`tools/lib/quota_meter.py`。§6 的 `TELEMETRY_ALLOW_UNDOCUMENTED_ENDPOINT=false` 出廠預設與本節升格的整合，留待四方複審一併裁決（v2.1.4 刻意不動 §6，避免修憲生效前先改變執行面預設）。

**關鍵限制（必須寫入文件並告知使用者）**：`U5h`／`U7d` 是**帳號層級**指標。T2/T3 只能觀測本機用量。若同一帳號在其他裝置或 Claude 網頁端使用，本機推估會**低估**真實用量。因此：
- 必須支援「權威來源」（T1/T4/T5）與「本機推估」（T2/T3）的差異偵測；
- 當只有本機推估可用時，強制套用 `LOCAL_ESTIMATE_SAFETY_MARGIN`（預設 15 個百分點）壓低所有門檻。

#### 4.1.2 新鮮度與失效處理（v1 完全缺漏）

```
telemetry_age = now_monotonic − last_successful_poll
  age ≤ POLL_INTERVAL × 3           → 正常
  age >  POLL_INTERVAL × 3 (180s)   → 強制 THROTTLING，發警示
  age >  TELEMETRY_TIMEOUT (600s)   → 強制 DRAINING
  age >  TELEMETRY_TIMEOUT × 2      → 強制 FREEZING（視為額度狀態不明）
```
輪詢自身失敗需採指數退避，避免對來源造成壓力；退避期間**不放寬**任何門檻。

#### 4.1.3 視窗重置偵測

```
若 U5h(t) < U5h(t−Δ) − RESET_DROP_THRESHOLD (預設 20 pp):
    判定為 5 小時視窗已重置
    → 清空燃燒率歷史緩衝
    → V_actual ← V_safe（中性初值，使比率=1，輸出 C_default）
    → 若處於 WAITING_RESET，轉入 RESUMING
```
v1 的 `delta_u = max(0.0, ...)` 會把重置造成的負差值壓成 0，使 `V_actual` 掉到下限、比率暴衝，喚醒後第一個控制週期就直接跳到 `C_max` —— 這是最容易在重置後立刻再撞牆的路徑。

#### 4.1.4 帳號／方案變更偵測（Plan-Change Adaptive Amortization）（R93 新增）

**問題**：§4.2 的跨窗攤提換算比（實作見 ADR-XPLAT-005／R86 校準文件）從歷時
落款差分推估，該落款持久且永不輪替。帳號的容量發生變更時（更換訂閱方案，
或更換同組織下容量不同的帳號），舊方案與新方案的樣本會混在同一個估計池，
導致換算比被錯誤方案的燃燒特性汙染——這個風險**不隨時間自癒**（落款是持久
的，不像快取有 TTL）。

**核心指紋**：以帳號本次讀數中「屬於既有已分類桶名集合（`KNOWN_KINDS`，見
ADR-XPLAT-005/007 既有定義）」的 kind 集合作為指紋。伺服器新推出一個尚未
分類的計費軸（schema 演進）**不算**方案變更；已分類軸的增減（例如訂閱方案
變更導致某個既有額度類型消失或新增）**才算**方案變更訊號。

**適配機制**：每一次落款附帶當時的核心指紋；估計換算比時只採信與**當前**
核心指紋相符的歷史樣本。方案容量無論從大變小或從小變大，只要核心桶集合
因此改變，舊樣本結構上都不會混入新方案的估計池——兩個方向對稱處理，不需要
額外的「哪個方向該不該計入」判斷。

**已知限制**（誠實揭露，非缺失）：

🔴 **R93 二次訂正（獨立 Architect 複審 REJECT 承接，`DEF-200-114`）**：下面第一點
「需要帳號身份識別（涉及憑證處理，非本節範圍）」與實測不符，PRD 與實作已於本輪
一併修正——`docs/06_quality/Quota_R90_CrossAccount_Experiment.md` §2.3-2.4 用
真實 Pro→Team 換帳號資料證明：核心桶集合指紋本身**不具身分鑑別力**（真實換帳號
差異軸與同帳號兩次自然翻動逐字相同，3 命中 2 假陽性；29% 的舊帳號樣本與新帳號
指紋逐字相同，偽陰性，且不限同方案）。帳號身份識別**不涉憑證處理**——
`anthropic-organization-id`／`anthropic-workspace-id` 就在既有取數呼叫的回應
標頭裡，本輪已納入指紋（見 ADR-XPLAT-009 §6 的完整訂正），第一點限制範圍因此
收窄。核心指紋機制（前段〈適配機制〉描述的桶名集合分區）本身**不變**、仍是
安全方向，只是不再單獨承擔「偵測換帳號」的角色。

- ~~同一方案下更換帳號、核心桶集合恰好相同時，本機制與 §4.1.1 既有的帳號層級
  盲區同型，結構上偵測不到，需要帳號身份識別（涉及憑證處理，非本節範圍）。~~
  **本輪已解決**：帳號身份訊號（回應標頭雜湊，零額外網路／token／憑證處理）
  併入核心指紋，同方案換帳號現在可以被拆開。殘餘限制縮小為：同一個
  組織／工作區下方案原地變更、且核心桶集合恰好沒變時仍抓不到（需要伺服器
  揭露方案本身的識別欄位，payload 現況無此欄）。
- **新補齊的邊界**（本節此前漏列，獨立 Architect 複審指出）：不同方案但核心
  桶集合恰好相同時，若對應到不同帳號（組織／工作區不同），本輪的帳號身份
  訊號一併解決；若是同一個組織／工作區下發生，仍是上一點的殘餘情境。
- 快取新鮮度視窗（§4.1.2，180 秒）只判斷時間新鮮度，不判斷帳號/方案身份；
  換帳號後最多 180 秒的窗口內可能仍採信切換前的讀數，下一次量測即自我修正。
- 換方案發生當下已經在執行中的 Agent／扇出工作不受本機制的未來派工決策
  影響，會依原方案／新方案的實際容量自然消耗至結束，這是物理限制而非設計
  疏漏。
- 歷史校準基準（本節之前累積的樣本）在本機制上線的當下因缺乏指紋資訊而
  永久不再參與估計，是刻意的、方向安全的信心度重置，而非資料遺失。
- 帳號身份訊號上線那一刻對既有樣本池同樣是一次性、方向安全的信心度重置
  （既有落款皆無帳號標籤），與上一點同型。
- 帳號身份訊號跨機器／同帳號多工作區的穩定性尚未有一手觀測驗證；方向仍安全
  （過度區分只讓樣本池變小、退回保守估計，不會讓攤提放寬）。

**非目標澄清**（呼應 §1.3）：本機制的目的是被動適配使用者已經自然發生的
合法方案/帳號變更，其估計結果只會讓攤提**更貼近真實情況**（可能更寬鬆也
可能更保守，取決於新方案的實際容量），**不是**協助偵測或切換帳號以規避
額度限制的機制。

### 4.2 配速控制器（Pacing Controller）— 修正後的數學模型

#### 4.2.1 燃燒率估計（加入 EWMA 與統一下限）

```
Δ          = MONITOR_POLL_INTERVAL_SECONDS / 60           # 取樣間隔（分鐘）
v_sample   = max(0, U5h(t) − U5h(t−Δ)) / Δ                # 瞬時值 (%/min)
V_actual   = α · v_sample + (1 − α) · V_actual(t−Δ)        # α = BURN_RATE_EWMA_ALPHA (0.25)
V_eff      = max(V_FLOOR, V_actual)                        # V_FLOOR = 0.02 %/min（單一定義，不再有 0.01/0.02 分歧）
```
`BURNING_RATE_WINDOW_MINUTES=15` 由 EWMA 取代；若保留固定視窗，需明確定義為長度 `window/Δ` 的環形緩衝，且在重置時清空。EWMA 的等效時間常數約為 `Δ·(1/α) = 4 分鐘`（以 60 秒取樣、α=0.25），可藉 α 調整。

#### 4.2.2 安全燃燒率與目標併發

```
U_rem      = max(0, DRAIN_PERCENT − U5h_effective)         # U5h_effective 已含本機推估安全邊際
T_rem      = (reset_timestamp − now) / 60                   # 分鐘

# 重置臨界處理（v1 用 max(1, ...) 會製造假暴衝）
若 T_rem < T_MIN_MINUTES (2):
    → 不派新工，進入短暫 hold，等待重置事件
V_safe     = U_rem / max(T_MIN_MINUTES, T_rem)

C_raw      = floor(C_default × V_safe / V_eff)
C_target   = clamp(C_raw, C_min, C_cap(state))              # ← v1 缺少狀態上限，是驗收矛盾的根源
```

#### 4.2.3 閘門與致動器優先序（先否決、後配速）

決策順序固定，任一步命中即短路：

```
1. HALTED_MANUAL                         → C = 0
2. 遙測狀態不明（見 §4.1.2）              → C = 0 或 1（依 FAIL_SAFE_MODE）
3. U7d ≥ WEEKLY_HALT_PERCENT             → C = 0，狀態 = LONG_HIBERNATE
4. U5h ≥ HALT_PERCENT                    → C = 0，狀態 = FREEZING
5. U5h ≥ DRAIN_PERCENT                   → C = 0，狀態 = DRAINING
6. U7d ≥ WEEKLY_DRAIN_PERCENT            → C = min(C_target, 1)
7. U7d_model ≥ MODEL_DOWNGRADE_PERCENT   → 模型降級（見下），併發不變
8. 其他                                   → C = C_target
```

**致動器不只有「併發數」**（v1 只有一個致動器，控制力不足）：

| 致動器 | 效果 | 觸發時機 |
| :---- | :---- | :---- |
| 併發 Agent 數 `C(t)` | 線性影響燃燒率 | 全程 |
| **模型層級降級** | 高階模型的額度消耗率遠高於中階模型，降級的節流效果通常大於減併發 | `THROTTLING` 或 `U7d_model` 超標 |
| **任務類別過濾** | 暫停「大規模重構」「全庫檢索」等高成本類別，只放行小型任務 | `THROTTLING` 起 |
| **Agent 硬性預算** | 單一 Step 的 turn 數／時間／估計 token 上限，防止單一 Agent 在 `DRAINING` 期間衝破 `HALT` | 全程，`DRAINING` 期間收緊 |

> `[需核對]` 模型降級的具體旗標，以及訂閱制方案是否已內建自動降級行為（若已內建，本模組應以「不牴觸」為原則，僅在更早的水位主動降級）。

#### 4.2.4 平穩性機制（v1 完全缺漏，是實務上最會出事的部分）

```
# (a) 遲滯帶：避免在門檻附近抖動
進入 THROTTLING: U5h ≥ WARN
離開 THROTTLING: U5h ≤ WARN − WATERMARK_HYSTERESIS_PP (3)

# (b) 死區：微小變化不動作
若 |C_target − C_current| < 1  → 不變更

# (c) 變化率限制（slew rate）：每個控制週期最多變動 ±1
C_next = clamp(C_target, C_current − 1, C_current + 1)
  例外：升級到 DRAINING/FREEZING 時允許直接歸零（安全方向不限速）

# (d) 最小停留時間：避免控制器比任務生命週期還快
若 (now − last_change) < MIN_DWELL_SECONDS (300)  → 不變更（僅適用於「增加」方向）

# (e) 控制週期 vs 死時間
CONTROL_INTERVAL_SECONDS 應 ≥ 2× 單一 Step 的中位執行時間，
否則控制器會對尚未反映在用量上的決策重複反應（積分飽和）。
```

#### 4.2.5 突刺（BURSTING）判準 — v1 未定義且有觀念錯誤

v1 的「額度即將過期，全力拉滿」隱含「未用完的 5 小時額度會浪費」的假設。但**週上限是更長期的約束**：在 5 小時視窗末端暴衝，等於提前燒掉週額度，可能換來數天停權。因此突刺必須被週額度否決：

```
BURSTING 需全部成立：
  T_rem ≤ BURST_WINDOW_MINUTES (30)
  U5h   ≤ BURST_MAX_U5H_PERCENT (60)
  U7d   ≤ BURST_WEEKLY_GUARD_PERCENT (60)      ← v1 缺此條，是最危險的缺漏
  U7d 的線性預算進度 ≥ 當前 U7d（即本週尚未超支）
  待派工佇列非空且任務為可中斷型（不可中斷的長任務不得在視窗末端啟動）
  ENABLE_BURSTING = true
```
另需檢查：若 `T_rem ≤ 預估 Step 執行時間`，則新 Step 極可能跨越重置點被截斷 —— 應延後派工至重置後，而非搶跑。

#### 4.2.6 參考實作（修正版）

```python
"""AutoClaude 配速控制器 — 參考實作（v2）

與 v1 的差異：
  1. 加入狀態併發上限 C_cap(state)（修正驗收矛盾）
  2. 加入週額度閘門
  3. EWMA 平滑 + 單一 V_FLOOR 常數
  4. 視窗重置偵測（不再把負差值壓成 0）
  5. 變化率限制、死區、最小停留時間
  6. 遙測新鮮度 fail-safe
  7. 使用 monotonic 計時，wall clock 僅用於絕對重置時間
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    INIT = "INIT"
    CRUISING = "CRUISING"
    BURSTING = "BURSTING"
    THROTTLING = "THROTTLING"
    DRAINING = "DRAINING"
    FREEZING = "FREEZING"
    WAITING_RESET = "WAITING_RESET"
    LONG_HIBERNATE = "LONG_HIBERNATE"
    RESUMING = "RESUMING"
    HALTED_MANUAL = "HALTED_MANUAL"


V_FLOOR = 0.02          # %/min，冷啟動與除零防護的唯一定義
T_MIN_MINUTES = 2.0     # 重置臨界保護


@dataclass
class Telemetry:
    u5h: float                    # 帳號 5h 使用率 %
    u7d: float                    # 帳號週使用率 %
    u7d_model: float              # 高階模型週使用率 %
    reset_timestamp: float        # 5h 視窗重置（wall clock, epoch 秒）
    weekly_reset_timestamp: float | None
    fetched_at_monotonic: float
    source_tier: str              # "T1".."T5"
    is_local_estimate: bool       # 僅本機推估 → 需套用安全邊際


@dataclass
class Config:
    warn_percent: float = 70.0
    drain_percent: float = 85.0
    halt_percent: float = 95.0
    weekly_warn_percent: float = 70.0
    weekly_drain_percent: float = 80.0
    weekly_halt_percent: float = 90.0
    model_downgrade_percent: float = 50.0
    c_min: int = 1
    c_default: int = 2
    c_max: int = 5
    c_throttle: int = 1
    ewma_alpha: float = 0.25
    hysteresis_pp: float = 3.0
    min_dwell_seconds: float = 300.0
    poll_interval_seconds: float = 60.0
    telemetry_timeout_seconds: float = 600.0
    local_estimate_margin_pp: float = 15.0
    enable_bursting: bool = True
    burst_window_minutes: float = 30.0
    burst_max_u5h: float = 60.0
    burst_weekly_guard: float = 60.0
    fail_safe_concurrency: int = 0   # 0 = 立即排空；1 = 保留一個 Agent


@dataclass
class ControllerState:
    state: State = State.INIT
    concurrency: int = 0
    v_actual: float | None = None
    last_u5h: float | None = None
    last_change_monotonic: float = field(default_factory=time.monotonic)
    latched_drain: bool = False      # DRAINING 以上為單向鎖存


C_CAP = {
    State.INIT: 0,
    State.CRUISING: None,            # None → 用 c_max
    State.BURSTING: None,
    State.THROTTLING: "throttle",
    State.DRAINING: 0,
    State.FREEZING: 0,
    State.WAITING_RESET: 0,
    State.LONG_HIBERNATE: 0,
    State.RESUMING: 1,
    State.HALTED_MANUAL: 0,
}


def _cap_for(state: State, cfg: Config) -> int:
    cap = C_CAP[state]
    if cap is None:
        return cfg.c_max
    if cap == "throttle":
        return cfg.c_throttle
    return int(cap)


def update_burn_rate(cs: ControllerState, u5h: float, cfg: Config,
                     reset_detected: bool, v_safe_hint: float) -> float:
    """回傳平滑後的有效燃燒率 (%/min)。"""
    if reset_detected or cs.last_u5h is None:
        # 中性初值：使 v_safe / v_eff == 1，輸出 c_default，避免重置後暴衝
        cs.v_actual = max(V_FLOOR, v_safe_hint)
        cs.last_u5h = u5h
        return cs.v_actual

    delta_min = cfg.poll_interval_seconds / 60.0
    v_sample = max(0.0, u5h - cs.last_u5h) / max(delta_min, 1e-9)
    prev = cs.v_actual if cs.v_actual is not None else v_sample
    cs.v_actual = cfg.ewma_alpha * v_sample + (1 - cfg.ewma_alpha) * prev
    cs.last_u5h = u5h
    return max(V_FLOOR, cs.v_actual)


def decide(tel: Telemetry | None, cs: ControllerState, cfg: Config,
           now_monotonic: float, now_wall: float,
           queue_has_work: bool, manual_pause: bool,
           reset_detected: bool = False) -> tuple[State, int, str]:
    """回傳 (下一狀態, 允許併發數, 決策理由)。純函式，便於單元測試。"""

    # ── 閘門 1：人工覆寫優先於一切 ──
    if manual_pause:
        return State.HALTED_MANUAL, 0, "manual_pause"

    # ── 閘門 2：遙測新鮮度（fail-safe，絕不 fail-open）──
    if tel is None:
        return State.DRAINING, cfg.fail_safe_concurrency, "telemetry_unavailable"
    age = now_monotonic - tel.fetched_at_monotonic
    if age > cfg.telemetry_timeout_seconds * 2:
        return State.FREEZING, 0, f"telemetry_stale_critical:{age:.0f}s"
    if age > cfg.telemetry_timeout_seconds:
        return State.DRAINING, 0, f"telemetry_stale:{age:.0f}s"

    # 本機推估 → 悲觀化讀數
    margin = cfg.local_estimate_margin_pp if tel.is_local_estimate else 0.0
    u5h = min(100.0, tel.u5h + margin)
    u7d = min(100.0, tel.u7d + margin)

    stale_soft = age > cfg.poll_interval_seconds * 3

    # ── 閘門 3：週上限（最長 7 天，無法靠短休眠解決）──
    if u7d >= cfg.weekly_halt_percent:
        cs.latched_drain = True
        return State.LONG_HIBERNATE, 0, f"weekly_halt:{u7d:.1f}%"

    # ── 閘門 4/5：5 小時視窗硬水位 ──
    if u5h >= cfg.halt_percent:
        cs.latched_drain = True
        return State.FREEZING, 0, f"u5h_halt:{u5h:.1f}%"
    if u5h >= cfg.drain_percent or cs.latched_drain:
        cs.latched_drain = True
        return State.DRAINING, 0, f"u5h_drain:{u5h:.1f}%"

    # ── 配速計算 ──
    t_rem_min = (tel.reset_timestamp - now_wall) / 60.0
    if t_rem_min < T_MIN_MINUTES:
        return cs.state, 0, "reset_imminent_hold"

    u_rem = max(0.0, cfg.drain_percent - u5h)
    v_safe = u_rem / max(T_MIN_MINUTES, t_rem_min)
    v_eff = update_burn_rate(cs, u5h, cfg, reset_detected, v_safe)

    # ── 狀態判定（含遲滯與週額度警戒）──
    if u5h >= cfg.warn_percent or u7d >= cfg.weekly_warn_percent or stale_soft:
        next_state = State.THROTTLING
        reason = "throttle"
    elif cs.state == State.THROTTLING and u5h > cfg.warn_percent - cfg.hysteresis_pp:
        next_state = State.THROTTLING          # 遲滯：尚未跌破退出門檻
        reason = "throttle_hysteresis"
    elif (cfg.enable_bursting and queue_has_work
          and t_rem_min <= cfg.burst_window_minutes
          and u5h <= cfg.burst_max_u5h
          and u7d <= cfg.burst_weekly_guard):
        next_state = State.BURSTING
        reason = "burst"
    else:
        next_state = State.CRUISING
        reason = "cruise"

    # ── 目標併發 → 狀態上限 → 平穩性機制 ──
    c_raw = math.floor(cfg.c_default * (v_safe / v_eff))
    c_target = max(cfg.c_min, min(c_raw, _cap_for(next_state, cfg)))

    # 週額度排空警戒：壓到 1
    if u7d >= cfg.weekly_drain_percent:
        c_target = min(c_target, 1)
        reason += "+weekly_drain"

    c_next = c_target
    if c_target > cs.concurrency:
        # 只有「增加」方向受停留時間與變化率限制；「減少」不限速
        if now_monotonic - cs.last_change_monotonic < cfg.min_dwell_seconds:
            c_next = cs.concurrency
            reason += "+dwell_hold"
        else:
            c_next = min(c_target, cs.concurrency + 1)
    elif c_target < cs.concurrency:
        c_next = max(c_target, cs.concurrency - 1)

    return next_state, c_next, (
        f"{reason} u5h={u5h:.1f} u7d={u7d:.1f} t_rem={t_rem_min:.0f}m "
        f"v_safe={v_safe:.3f} v_eff={v_eff:.3f} c_raw={c_raw} c={c_next}"
    )
```

#### 4.2.7 情境試算驗證表（修正版）

v1 的四個情境算術正確，但**未反映狀態上限與變化率限制**，故第 3 列與驗收標準第 3 條矛盾。以下為修正後（假設 `C_current` 已達穩態、停留時間已滿足）：

| # | 情境 | `U5h` | `U7d` | `T_rem` | `U_rem` | `V_safe` | `V_eff` | `C_raw` | 狀態 | `C_cap` | **最終 C** | 決策說明 |
| :-- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | 視窗將重置、額度多、**週額度健康** | 20% | 40% | 30m | 65 | 2.167 | 0.20 | 21 | `BURSTING` | 5 | **5** | 允許突刺（但受 ±1 變化率限制，需數個週期爬升） |
| 1b | 同上，但**週額度已 75%** | 20% | 75% | 30m | 65 | 2.167 | 0.20 | 21 | `THROTTLING` | 1 | **1** | **v1 會誤判為衝刺 →** 週額度否決 |
| 2 | 標準巡航 | 40% | 45% | 150m | 45 | 0.300 | 0.30 | 2 | `CRUISING` | 5 | **2** | 燃燒率符合預算 |
| 3 | 燃燒過快 | 65% | 50% | 180m | 20 | 0.111 | 0.60 | 0 | `CRUISING` | 5 | **1** | `C_raw=0` 被 `C_min` 抬升到 1 |
| 3b | **驗收標準指定情境**：75% | 75% | 50% | 240m | 10 | 0.042 | 0.30 | 0 | `THROTTLING` | **1** | **1** | v1 公式在 `T_rem` 較短時可能算出 >1；v2 由 `C_cap` 保證為 1 |
| 4 | 達排空線 | 86% | 50% | 60m | 0 | 0 | 0.40 | 0 | `DRAINING` | 0 | **0** | 單向鎖存，不再回退 |
| 5 | **視窗剛重置** | 2% | 52% | 298m | 83 | 0.279 | 0.279（中性初值） | 2 | `RESUMING`→`CRUISING` | 1→5 | **1→2** | v1 會因 `V_actual` 觸底而直接跳 `C_max` |
| 6 | **遙測中斷 11 分鐘** | (舊值 30%) | — | — | — | — | — | — | `DRAINING` | 0 | **0** | v1 未定義，會沿用舊讀數繼續派工 |
| 7 | 週上限 92% | 30% | 92% | 200m | 55 | 0.275 | 0.20 | 2 | `LONG_HIBERNATE` | 0 | **0** | v1 只會休眠到 5h 重置，醒來立刻再撞牆 |

#### 4.2.8 與 CLI 內建配速門檻對齊（v2.1 核實新增）

核實發現 CLI 內部帶有一組「超前燃燒」判準，其結構是 **利用率 vs 視窗已流逝比例**：

| 額度類型 | 視窗長度 | 內建判準（利用率 / 已流逝時間比） | 換算配速指數 |
| :---- | :---- | :---- | :---- |
| `five_hour` | 18,000 秒（5 小時） | 0.90 / 0.72 | 1.25 |
| `seven_day` | 604,800 秒（7 天） | 0.75 / 0.60 · 0.50 / 0.35 · 0.25 / 0.15 | 1.25 · 1.43 · 1.67 |

這驗證了 v2 的 `V_safe` 觀念，並可寫成更簡潔的等價形式：

```
elapsed_frac = 1 − T_rem / WINDOW_MINUTES
pace_index   = utilization / max(ε, elapsed_frac)
  pace_index ≈ 1  → 正好照預算燃燒
  pace_index > 1  → 超前燃燒（會提前用完）
  pace_index < 1  → 落後（額度用不完）
```
`C(t) = clamp(floor(C_default / pace_index), C_min, C_cap(state))` 與 §4.2.2 的 `V_safe / V_eff` 形式數學上同源，但**不需要估計瞬時燃燒率**，因而完全免除冷啟動、EWMA 調參與視窗重置誤判的問題。**建議實作採用 `pace_index` 為主控訊號，`V_eff` 僅作為輔助診斷指標。**

**對 v2 預設值的兩點重要修正：**

1. **週額度必須用配速判準，不能用絕對水位。** v2 設 `WEEKLY_WARN_PERCENT=70` 太晚了 —— 依內建判準，週額度在流逝 15% 時利用率就不該超過 25%。若照 v2 的絕對水位治理，週三就可能燒到 70%，剩下四天全在 `LONG_HIBERNATE`。**改為配速門檻**：`WEEKLY_PACE_CEILING_THROTTLE=1.25`（超過即 `THROTTLING`）、`WEEKLY_PACE_CEILING_DRAIN=1.50`（併發壓到 1）。對應設定見 §6 第 4 節。
2. **5 小時視窗可以比 v2 更寬鬆。** 內建判準到 0.90/0.72 才示警，而 v2 在 70% 就開始節流。在**週額度配速健康**的前提下，`TOKEN_WARN_PERCENT` 可放寬到 80（並設 `FIVE_HOUR_PACE_CEILING=1.25`），把 5 小時視窗吃得更滿（反正它會重置）。真正需要嚴管的是週額度 —— 這與 v2 §4.2.5 的論證一致，現在有了實作證據。

> **注意**：上述內建數值取自 v2.1.232 的實作字串，屬**內部**啟發式，非公開契約。應作為「校準參考」而非硬編碼依賴；實作時放在設定檔中，並以 §15.7 的觀測資料再校準。

### 4.3 上下文壓縮策略（v1 邏輯錯誤，本節整體重寫）

**原則**：壓縮由 `K_ctx`（上下文佔用率）驅動，且必須在**額度尚有餘裕時**執行。

```
壓縮觸發條件（AND）：
  K_ctx ≥ CONTEXT_COMPACT_PERCENT (84)        # 單一 session 的上下文佔用
                                              # ↑ R92 修憲（v2.1.1）：75 → 84；同輪首次把 context 硬線 94% 入憲
                                              #   （實作層 HARD_RATIO 0.90 → 0.94，PRD 此前未定義硬線）。
                                              #   與額度尺 85/95 錯開以保鑑別力（R92 掌舵者裁決）。
                                              #   注意：機械 autocompact（PCT=90）的分母是 auto-compact window，
                                              #   官方未公開其與模型全窗的比例 ⇒「84 早於壓縮點」不可證，
                                              #   方向安全（至多提早壓縮），詳 ADR-XPLAT-008 §4。
  U5h + COMPACT_COST_BUDGET_PP ≤ DRAIN_PERCENT # 壓縮本身要燒額度，須先確認燒得起
  距上次壓縮 ≥ COMPACT_MIN_INTERVAL_SECONDS   # 防止反覆壓縮

若 K_ctx 已高但額度不足以支付壓縮成本：
  → 不壓縮，直接走 FREEZING 路徑
  → 理由：state.json 才是耐久記憶體，上下文不是。犧牲上下文、保留額度，
          是比「花掉最後 5% 額度做壓縮然後沒額度繼續」更好的選擇。
```

`COMPACT_COST_BUDGET_PP` 需以實測校準（壓縮一次的額度成本 ≈ 完整上下文的一次讀取 + 摘要輸出）。建議初值 3 個百分點，並在執行後回寫實測值做自適應。

> `[需核對]` (a) CLI 是否已內建自動壓縮及其觸發點；(b) 在非互動（headless）模式下能否由外部觸發壓縮；(c) 是否有 pre-compact 類的 hook 可讓 Daemon 在壓縮前先寫 checkpoint。若 (b) 不可行，本模組應改為「在 `K_ctx` 超標時主動結束該 Step 並以新 session 交棒」，而非嘗試遠端下達壓縮指令 —— v1 假設 Daemon 可任意觸發 `/compact`，此假設需驗證。

### 4.4 多 Agent 隔離與整合（v1 過於簡略）

#### 4.4.1 Worktree 建立（修正實務問題）

```bash
# v1: git worktree add .autoclaude/worktrees/agent-<ID> -b feature/agent-<ID>
#     問題：分支已存在時失敗；worktree 目錄在 repo 內未被忽略；無基準點鎖定

BASE_SHA=$(git rev-parse HEAD)                 # 明確鎖定基準，避免各 Agent 基準不一
BRANCH="autoclaude/agent-${AGENT_ID}-${RUN_ID}" # 含 RUN_ID 保證唯一
git worktree add -B "$BRANCH" \
  ".autoclaude/worktrees/agent-${AGENT_ID}" "$BASE_SHA"
```
- `.autoclaude/` 必須加入 `.gitignore`（且 `worktrees/` 不得被 Agent 的檔案掃描納入上下文，否則會重複讀入他人程式碼並浪費 token）。
- 啟動前檢查 `git worktree prune`，清理上次異常退出的殘留。
- 每個 Agent 的 CLI 實例必須以其 worktree 為工作目錄，並限制檔案寫入範圍在該目錄內。

#### 4.4.2 整合佇列（v1 的「Fast-Forward 合併」不可行）

多 Agent 並行時各分支必然分歧，FF 只在「無其他分支已合併」時成立。修正為序列化整合佇列：

```
對每個完成的 Agent 分支，Daemon 依序（單執行緒、持有整合鎖）執行：
  1. git fetch/更新 integration 分支
  2. git rebase integration <agent-branch>          # 衝突 → 標記 CONFLICT，交人工或重派
  3. 執行驗證閘門（lint / build / unit test）        # 失敗 → 退回佇列，不合併
  4. git merge --ff-only <agent-branch>            # rebase 後 FF 必然成立
  5. git worktree remove + 刪除分支
衝突策略：CONFLICT_POLICY = ABORT | RETRY_WITH_AGENT | HUMAN_REVIEW（預設 HUMAN_REVIEW）
```
**重要**：步驟 2 的衝突解決若交由 Agent 處理，會消耗額度 —— 必須納入配速預算，且在 `DRAINING` 以上狀態禁止啟動衝突解決任務。

#### 4.4.3 Agent 硬性預算（v1 缺漏）

`DRAINING` 狀態「允許進行中的 Step 收尾」是危險的開放式承諾：一個大型 Step 可能在收尾期間把 `U5h` 從 85% 推到 100%。必須有硬性上限：

```
每個 Step 啟動時設定：
  MAX_STEP_TURNS            (預設 40)      # CLI 的最大回合數旗標
  MAX_STEP_WALL_SECONDS     (預設 900)
  MAX_STEP_QUOTA_PP         (預設 5)       # 該 Step 允許推升的 U5h 百分點
DRAINING 狀態下上述值乘以 DRAIN_BUDGET_FACTOR (0.5)
超出任一上限 → 優雅終止（SIGINT → 等待 → SIGTERM → SIGKILL），
               並將該 Step 標記為 PARTIAL 寫入 state.json
```
> `[需核對]` 最大回合數旗標名稱、以及 headless 模式下訊號處理是否會正確落盤對話記錄。

### 4.5 狀態保全與喚醒（Lossless Resume）— 修正成本假設

#### 4.5.1 凍結流程

```
[U5h ≥ HALT] 
   │
   ├─► 1. 停止派工，向所有 Agent 發出優雅終止
   ├─► 2. 每個 worktree 各自 commit（不是只有一個！）
   │        git -C <wt> add -A
   │        git -C <wt> commit -m "autoclaude: checkpoint (pre-reset) [skip ci]"
   │        允許空提交失敗（無變更時跳過）
   ├─► 3. 收集每個 Agent 的 session_id / 分支 / SHA / 未完成檔案
   ├─► 4. 原子寫入 state.json（tmp → fsync → rename）
   ├─► 5. 驗證：重新讀取並校驗 schema + checksum
   ├─► 6. 釋放 Agent 行程，啟動防休眠（僅在需等待 < MAX_INPROCESS_WAIT 時）
   └─► 7. 狀態 → WAITING_RESET 或 LONG_HIBERNATE
```
**所有凍結動作皆為零 Token 操作**（git、檔案 I/O），可安全在 95% 執行。這是把壓縮移出此路徑的另一個理由。

#### 4.5.2 休眠等待（修正 v1 的單次長 sleep）

```
target_wall = reset_timestamp + RESET_BUFFER_SECONDS
while True:
    remaining = target_wall − now_wall()
    if remaining <= 0: break
    sleep(min(remaining, SLEEP_SLICE_SECONDS))       # 分片，預設 30s
    # 偵測系統睡眠／NTP 跳躍：monotonic 與 wall clock 增量差 > CLOCK_JUMP_TOLERANCE (120s)
    if clock_jump_detected(): re-poll telemetry, 重算 target_wall
    if received_signal(): 優雅退出（state.json 已落盤，可安全重啟）
```
理由：單次 `sleep(5h)` 無法回應訊號、無法修正時鐘漂移、機器睡著後醒來會嚴重超時或早醒。

#### 4.5.3 重置驗證與喚醒

```
1. 重新輪詢遙測，確認 U5h 已顯著下降（< RESET_CONFIRM_PERCENT，預設 10）
2. 未確認 → 以 full-jitter 退避重試（30s 起，上限 300s，最多 10 次），
            仍失敗 → 回到 WAITING_RESET 並延長等待（後端重置漂移）
3. 確認後 → 依 RESUME_STRATEGY 喚醒（見 4.5.4）
4. 以 C=1 起步，成功接手後才交還配速控制器（避免喚醒瞬間齊發撞牆）
```

#### 4.5.4 喚醒策略 — v1 的成本盲點

> **v1 的核心誤解**：「同一 Session 續接 = 不重複消耗 Token」。實際上，續接一段長對話時，模型必須重新讀入完整歷史；提示快取（prompt cache）的存活時間遠短於 5 小時，休眠後必然是**快取未命中**，因此喚醒的第一個請求會產生**全額輸入 token 費用**。對話越長，喚醒越貴 —— 而喚醒的時機正好是額度剛重置、最該省著用的時候。

因此提供三種策略：

| 策略 | 做法 | 喚醒成本 | 上下文保真度 | 適用 |
| :---- | :---- | :---- | :---- | :---- |
| `SESSION_RESUME` | 續接原 session | 高（≈ 完整歷史一次重讀） | 最高 | 對話短、任務高度依賴細節脈絡 |
| `FRESH_SESSION_WITH_STATE` | 新 session，開場給 state.json + 必要檔案清單 | 低（僅摘要 + 少量檔案） | 中（依賴 state.json 品質） | 對話長、步驟邊界清楚 |
| `AUTO`（**預設**） | 依對話規模自動選擇 | — | — | 一般情況 |

```
AUTO 判準：
  估計對話 token 數 ≤ RESUME_MAX_TRANSCRIPT_TOKENS (60000)  → SESSION_RESUME
  否則 → FRESH_SESSION_WITH_STATE
另：若 U7d 已高於 weekly_warn，一律採 FRESH_SESSION_WITH_STATE（省額度優先）
```

喚醒指令（**移除 v1 的 `--dangerously-skip-permissions` 預設**）：

```bash
# 建議形式（旗標與權限模式名稱 [需核對]）
claude --resume "<SESSION_ID>" \
       --permission-mode acceptEdits \
       --allowed-tools "Read,Edit,Write,Bash(npm test:*),Bash(git status)" \
       --max-turns 40 \
       -p "額度已重置。請讀取 .autoclaude/state.json，從 interrupted_step 繼續執行；
           先確認工作區狀態與測試結果，再繼續未完成項目。"
```
安全說明見 §13。**只有**在容器／VM 等隔離環境且使用者明確設定 `ALLOW_PERMISSION_BYPASS=true` 時，才可使用完全跳過權限的旗標。

#### 4.5.5 長休眠（`LONG_HIBERNATE`）— v1 完全缺漏

週上限觸發時等待期可達 7 天，不能用 in-process sleep 或防休眠硬撐（電力／穩定性／使用者體驗皆不可接受）：

```
若 T_rem_7d > MAX_INPROCESS_WAIT_SECONDS (預設 7200):
  1. 完成凍結流程（state.json 落盤）
  2. 向 OS 排程器註冊一次性喚醒任務：
       macOS   : launchd plist (StartCalendarInterval) 
       Windows : schtasks /create /sc once /st <time>
       Linux   : systemd-run --on-calendar / systemd timer
  3. 釋放防休眠，Daemon 退出（狀態完全在磁碟上）
  4. 排程時間到 → Daemon 重啟 → INIT 掃描 state.json → 驗證額度 → RESUMING
若 weekly_reset_timestamp 不可得：
  → 保守推估（依帳號起算日或最近觀測到的重置點），並在到期前每 30 分鐘輪詢一次確認
```

#### 4.5.6 撞線喚醒閉環的覆蓋面與失效紀律（v2.1.5 新增；立案證據＝2026-08-16/17 事件）

**立案事實（證據鏈全文見 ADR-XPLAT-004 §2.9）**：2026-08-16 深夜，喚醒機制的每一環能力都已存在
（撞線偵測判準 D、`sentinel_decide` 四分支、launchd `StartCalendarInterval`、`choose_resume_route`
三態選路），哨兵當晚亦已武裝並成功巡邏十次；但 00:42 額度 halt 動作把「可重啟點任務書」整檔覆寫成
不含機器可讀狀態塊的骨架，00:51 subagent 撞線（逐字「You've hit your session limit · resets 3:50am
(Asia/Taipei)」）落入主逐字稿、主 session 自己的回合同時死於 API 層，00:55 哨兵因「狀態塊讀不出來」
**靜默自我解除**，03:50 reset 時機器上零排程，空轉至次日人工介入。⇒ 失效的不是任何單環能力，
而是機制間的**互相摧毀**與失效時的**靜默**。故本節立以下需求（均為規範性要求）：

**R-4.5.6-1（覆蓋面）** 撞線偵測與喚醒續跑必須覆蓋三個執行層級：主 session API 回合、Task subagent、
workflow agent。判準以逐字稿合成權威記錄（`type=assistant` ＋ `model=<synthetic>`）為形狀、以
「事件之後全域有無成功 API 回應」為已處理證據（即現行判準 D），掃描面必含主逐字稿與其
`subagents/` 整棵子樹。

**R-4.5.6-2（主 session 活著但帳號級撞線）** 此情境下該回合死於 API 層、hook 體系零觸發點
（PreToolUse／PostToolUse 皆不會被叫到，session 事後也發不出任何工具呼叫）⇒ 逐字稿巡邏哨兵是
**唯一**事中機械物。因此哨兵自身的可用性即本情境的全部可用性：哨兵任何 fail-quiet 形態
（含自我解除、痕跡不分形、stderr 無人收）都等同本情境整格失效，一律按 P0 處理。

**R-4.5.6-3（單檔雙寫者禁令）** 任何寫入「可重啟點任務書」的路徑（骨架產生、prepare/halt 帶動作、
武裝、重排）**不得**摧毀該檔既有的機器可讀狀態塊（RELAY 塊）。驗收（機械）：對已含狀態塊的任務書
執行骨架重寫後，`parse_relay()` 非 None 且既有 state 逐格保留；此判準必須有紅面（在修正落地前的
實作上必紅）。

**R-4.5.6-4（失效必出聲、先自癒後解除）** 哨兵讀不出狀態塊時：(a) 必須先嘗試以呼叫端引數與任務書
檔名重建最小狀態塊並續巡（自癒）；(b) 重建不能才允許解除，且解除必經桌面級告警
（`escalation.alert(loud=True)` 等級，不得只印 stderr）；(c) 「檔不存在／無狀態塊／JSON 壞掉」三種
失效與「正常下班」的痕跡必須分形可稽核。

**R-4.5.6-5（halt 武裝的多軸裁決）** halt 閂鎖的喚醒武裝分支不得只看 binding 單軸：當 binding 軸無
reset（extra_usage／spend）但存在其他 ≥halt 且有 reset 的軸時，必須以「最早可 reset 軸」武裝喚醒；
僅當全軸皆無 reset 才允許 escalate-only。（立案反例：本事件 binding=extra_usage@None ⇒ escalate-only
未武裝，而 five_hour 軸 03:50 reset 後工作實際可續。）

**R-4.5.6-6（憑證紀律）** 「已武裝」宣稱一律附排程器自報憑證：Windows＝`NextRunTime` 非空值；
macOS＝`launchctl print gui/<uid>/<label>` 的 rc（不存在＝113）＋ plist 路徑回讀（launchd 不提供
NextRunTime，rc 才是憑證）。無憑證即不得宣稱，違者按 §15.5 紅線「排程也是一種 PASS 聲稱」處理。

**驗收判準（全部可機械查證）**：

| # | 判準 | 查證方式 |
| :---- | :---- | :---- |
| A1 | 含狀態塊的任務書經任何骨架重寫路徑後狀態塊存活 | 單元測試（紅綠自證，R-4.5.6-3） |
| A2 | 哨兵於「狀態塊缺席×逐字稿存在」輸入下不得 unregister，且告警注入點被呼叫 | 單元測試（R-4.5.6-4） |
| A3 | binding 無 reset ＋他軸有 reset ⇒ halt 分支回 arm；全軸無 reset ⇒ escalate | 單元測試（R-4.5.6-5） |
| A4 | 本事件重演劇本（撞線記錄落逐字稿 → 下一巡）產出 `arm_reset` 且武裝憑證非空 | 整合測試以真實逐字稿片段注入（R-4.5.6-1/2/6） |
| A5 | 巡邏／武裝／自癒／解除各步在痕跡檔留下**互異**事件名 | 痕跡 jsonl 斷言（R-4.5.6-4c） |

#### 4.5.7 主控閒置盲區與預防性水位提醒（v2.1.6 新增；掌舵者定級 P0「會破產的嚴重 BUG」，
立案＝`DEF-200-148`，2026-08-16/17 收尾包＋修復包兩次實證）

**立案事實**：08-16 收尾包與 08-17 修復包各撞線一次，兩次皆為「subagent 背景耗至 session 38%
期間主控零喚醒」——§4.5.6 修好的是「哨兵撞線後怎麼正確武裝續跑」，本節修的是**更早一步**：
撞線那一刻**之前**，主控完全不知道水位已逼近，而撞線那一刻**通知能不能送達**也未受保障。三個
結構洞（均為規範性要求）：

**R-4.5.7-1（主控閒置盲區）** `.claude/hooks/context_budget_guard.py` 的水位量測只掛在
PostToolUse／PreToolUse（見根 CLAUDE.md〈機械守衛總表〉），主控在等待 subagent 回覆期間**零工具
呼叫** ⇒ 該窗口內水位機制結構上不會被觸發。修法：既有哨兵巡邏（`tools/session_resume_planner.py
--arm-sentinel` 武裝的 schtasks／launchd 排程，`tools/lib/sentinel_lifecycle.py` 為巡邏邏輯本體）
於每次巡邏時，除既有「逐字稿有沒有撞線」判準外，**新增**一項：讀主逐字稿最後一筆
`type=assistant`／`type=tool_use` 事件的時間戳，與巡邏當下時刻相減；超過閒置門檻
（建議與巡邏間隔同量級，現查 `tools/lib/quota_policy.py --print-env-example`，不寫死於本 PRD）
且該 session 仍為 active（無 `Stop` 事件）時，判定為「主控閒置中」，進入 R-4.5.7-2 的水位查核。

**R-4.5.7-2（預防性水位提醒）** 現行 `sentinel_decide()` 四分支只認「逐字稿已出現撞線字樣」
（見 §4.5.6 R-4.5.6-2），對「水位正在逼近但尚未撞線」零觀測。修法：哨兵巡邏（含 R-4.5.7-1 判定
為閒置的巡邏）額外讀一次額度快取（`tools/lib/quota_meter.py` 既有讀法，同 `--pace` 的資料源），
若任一節流軸進入 prepare 帶（85~95%，門檻沿用 `tools/lib/quota_policy.py` 既有三段式定義，見根
CLAUDE.md〈三段式水位〉）且尚未進入 halt，發出一則「即將撞線」的預防性提醒（走 R-4.5.7-3 的通知
通道），**不**觸發 §4.5.6 的重啟任務書骨架寫入——任務書骨架仍只在真正撞線（halt）時產生，避免
提醒與重啟兩種語意的任務書互相覆寫（同 R-4.5.6-3 單檔雙寫者禁令的精神）。

**R-4.5.7-3（通知到達保障）** R-4.5.6-2 已指出「主 session 活著但帳號級撞線」時 hook 體系零觸發
點；本節補上通知**送達**面的保障——撞線與 R-4.5.7-2 預防性提醒兩種通知，一律走**不消耗額度**
的通道（桌面通知 `escalation.alert(loud=True)`／Windows Toast／macOS 通知中心，既有機制見
`autoclaude/utils/notifier.py`），不得只依賴「寫回逐字稿等主控下次工具呼叫時讀到」——若主控自己
也同時在額度限制內，它可能永遠不會有下一次工具呼叫去讀那則訊息。桌面通知不佔用 API 額度，故此
通道在「主控與哨兵同時撞線」的最壞情境下仍然成立。

**驗收判準（全部可機械查證；未實作者標明狀態，見下方施工狀態段）**：

| # | 判準 | 查證方式 | 狀態 |
| :---- | :---- | :---- | :---- |
| B1 | 巡邏讀出主逐字稿最後事件時間戳並算出閒置秒數 | 單元測試（合成逐字稿注入不同時間戳） | 規格已定，實作待 R98 |
| B2 | 閒置且水位進入 prepare 帶時發出預防性提醒、且不寫任務書骨架 | 單元測試（紅綠自證：R-4.5.7-2 分支開關） | 規格已定，實作待 R98 |
| B3 | 預防性提醒與撞線提醒皆走桌面通知通道，且不依賴主控下一次工具呼叫 | 整合測試（mock 通知器，斷言呼叫發生於巡邏行程而非 hook 行程） | 規格已定，實作待 R98 |

**🔴 施工狀態（誠實記載，不得曖昧）**：本節（v2.1.6）於本輪只完成**規格化**——三個結構洞的
機制設計已具體化到「掛哪支既有腳本、讀哪個既有資料源、走哪個既有通知通道」的層級，但**尚未落地
程式碼與回歸鎖**。R96 開場時誤稱「即辦」（見 `DEF-200-148` 原始修復方向欄，已訂正），實際完整
實作（三條 R-4.5.7-x ＋ B1~B3 三支測試）承接 **R98**。

### 4.6 跨平台防休眠（修正 v1 的技術細節）

| 平台 | 實作 | v1 的問題與修正 |
| :---- | :---- | :---- |
| **macOS** | `caffeinate -i -m -w <DAEMON_PID>` | v1 用 `-s`：**`-s` 僅在接電源時有效，電池模式下機器仍會睡**。改用 `-i`（防閒置睡眠）+ `-m`（防硬碟睡眠），並以 `-w <PID>` 綁定 Daemon 生命週期，避免 Daemon 崩潰後 caffeinate 變孤兒程序永久阻止睡眠。不使用 `-d`（依需求允許螢幕關閉；v1 註解列出 `-d` 與其宣稱目標矛盾） |
| **Windows** | `SetThreadExecutionState(ES_CONTINUOUS \| ES_SYSTEM_REQUIRED)` | v1 的三個問題：(a) 此 API 是**執行緒層級**，若在短命執行緒中呼叫，執行緒結束即失效 → 必須在長駐主執行緒呼叫並保持存活；(b) `ES_AWAYMODE_REQUIRED` 是給媒體播放場景，一般背景運算不宜使用，且在 Modern Standby (S0ix) 機器上行為不同；(c) 未定義還原：退出時必須呼叫 `SetThreadExecutionState(ES_CONTINUOUS)` 清除 |
| **Linux** | `systemd-inhibit --what=idle:sleep --who=autoclaude --why="token wait" <cmd>` | v1 **完全未支援 Linux**（但 Claude Code 支援 Linux／WSL） |
| **驗證** | macOS `pmset -g assertions`；Windows `powercfg /requests`；Linux `systemd-inhibit --list` | v1 無驗證手段。防休眠是否生效必須可觀測，並寫入啟動自檢 |

補充：防休眠**只用於短等待**（`< MAX_INPROCESS_WAIT_SECONDS`）；長等待改用 §4.5.5 的排程器交棒。另需處理「防休眠失效、機器仍睡著」的情況：醒來後偵測時鐘跳躍 → 重新輪詢遙測 → 若已過重置點則直接進入 `RESUMING`。

### 4.7 帳號配額仲裁（v1 缺漏的多實例問題）

額度是**帳號層級**資源，但 Daemon 是**專案層級**行程。同帳號同時跑兩個專案時，兩個 Daemon 各自看到「還有 60% 可用」，合起來就會超燒。

```
仲裁機制：
  ~/.autoclaude/accounts/<account_fingerprint>/     # fingerprint 為帳號識別的雜湊，不存明文憑證
    ├── quota.lock          # 檔案鎖，序列化配額決策
    ├── telemetry.json      # 共享的權威遙測快取（含 fetched_at）
    └── leases/<daemon_id>.json   # 各 Daemon 的併發租約（含到期時間）

分配規則：
  總可用併發 C_account 由讀取共享遙測後統一計算
  各 Daemon 依 lease 取得配額，lease 有 TTL（預設 120s），過期自動回收
  無法取得鎖 → 視為遙測不可得 → fail-safe 降級
單機單專案時此機制近乎零成本（無競爭）。
```
另需 Daemon 單實例鎖：`.autoclaude/daemon.lock`（含 PID 與啟動時間，偵測陳舊鎖）。

---

## 5. API Key 模式（v1 只提一句，實際無法運作）

v1 的配速演算法完全建立在「百分比 + 重置時間」之上，但 API Key 模式沒有這兩者。必須有正規化層：

| 項目 | OAUTH 模式 | API_KEY 模式 |
| :---- | :---- | :---- |
| 使用率 | 原生百分比 | `U := max(已用預算/預算上限, 觀測 TPM/TPM 上限)` × 100 |
| 「重置時間」 | 視窗重置時間戳 | **使用者定義的預算週期**（`API_BUDGET_PERIOD=DAILY\|WEEKLY\|MONTHLY`）的結束時間 |
| 硬性上限 | 平台強制 | `API_BUDGET_HARD_USD`（**必填**，無預設值，未設定則拒絕啟動） |
| 限流訊號 | 429 | 429 + 回應標頭中的剩餘配額／重試建議 `[需核對標頭名稱]` |
| 成本計算 | 不適用 | 需依模型單價表計算；單價表需可設定且標註更新日期 |

**安全要求**：API 模式下 `TOKEN_HALT_PERCENT` 對應的是「花光使用者自訂預算」，而非平台限制。達 HALT 後**不得**自動在下個週期繼續（避免無人看管的持續支出），需 `API_AUTO_CONTINUE_NEXT_PERIOD=false`（預設）。

---

## 6. 設定檔規範（.env.example，修訂版）

```dotenv
# ==============================================================================
# AutoClaude Token & Agent Dispatch Configuration  (schema v2)
# 不變式由啟動自檢驗證，違反則拒絕啟動（見 §6.1）
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. 帳號與認證
# ------------------------------------------------------------------------------
AUTOCLAUDE_AUTH_MODE=OAUTH                  # OAUTH | API_KEY
AUTOCLAUDE_ACCOUNT_TYPE=MAX                 # 僅作為預設值提示；實際額度一律以遙測為準
                                            # （v1 隱含以帳號等級推算額度，不可靠）

# ------------------------------------------------------------------------------
# 2. 遙測來源（依序嘗試，全部失敗則 fail-safe）
# ------------------------------------------------------------------------------
TELEMETRY_SOURCE_ORDER=OTEL,TRANSCRIPT,STATUSLINE,CLI_USAGE
TELEMETRY_ALLOW_UNDOCUMENTED_ENDPOINT=false # v1 的主要方案，v2 降為選用（風險自負）
MONITOR_POLL_INTERVAL_SECONDS=60
TELEMETRY_TIMEOUT_SECONDS=600               # 超時 → 強制 DRAINING
LOCAL_ESTIMATE_SAFETY_MARGIN_PP=15          # 僅有本機推估時，所有水位悲觀化的百分點

# ------------------------------------------------------------------------------
# 3. 額度水位（5 小時視窗，單位 %）
#    不變式：0 < WARN < DRAIN < HALT <= 100  且  HALT - DRAIN >= 5
# ------------------------------------------------------------------------------
TOKEN_WARN_PERCENT=70                       # → THROTTLING
TOKEN_DRAIN_PERCENT=85                      # → DRAINING（單向鎖存）
TOKEN_HALT_PERCENT=95                       # → FREEZING
WATERMARK_HYSTERESIS_PP=3                   # 【新增】遲滯帶，防抖動

# ------------------------------------------------------------------------------
# 4. 週額度安全閥
#    不變式：WEEKLY_WARN < WEEKLY_DRAIN < WEEKLY_HALT
# ------------------------------------------------------------------------------
ENABLE_WEEKLY_LIMIT_GUARD=true
WEEKLY_HALT_PERCENT=90                      # → LONG_HIBERNATE（絕對上限仍需保留）
MODEL_DOWNGRADE_PERCENT=50                  # 高階模型週額度達此值 → 降級

# 【v2.1 修正】週額度改以「配速指數」治理，不用絕對水位。
# 理由見 §4.2.8：依 CLI 內建判準，週視窗流逝 15% 時利用率就不該超過 25%，
# 用絕對水位（如 70%）會太晚，導致週三燒完、後四天全在等。
PACING_MODE=PACE_INDEX                      # PACE_INDEX（建議）| ABSOLUTE_WATERMARK（v2.0 舊行為）
WEEKLY_PACE_CEILING_THROTTLE=1.25           # pace_index 超過 → THROTTLING
WEEKLY_PACE_CEILING_DRAIN=1.50              # pace_index 超過 → 併發壓到 1
FIVE_HOUR_PACE_CEILING=1.25                 # 5h 視窗的配速上限（對齊內建判準 0.9/0.72）
PACE_MIN_UTILIZATION=0.05                   # 利用率低於此值時不套用配速判準（避免視窗開頭誤判）

# 保留為 ABSOLUTE_WATERMARK 模式的後備門檻（PACING_MODE=PACE_INDEX 時僅作為硬上限）
WEEKLY_WARN_PERCENT=70
WEEKLY_DRAIN_PERCENT=80

# ------------------------------------------------------------------------------
# 4b. 超額用量治理（v2.1 新增 — v1/v2.0 完全遺漏的維度）
#     核實發現額度類型含 overage / extra_usage / seven_day_overage_included，
#     且有月度支出上限。若帳號已啟用付費超額，達訂閱限制後可能「不停止而開始計費」，
#     使凍結邏輯永不觸發卻默默產生帳單。這是本系統最危險的單一失敗模式。
# ------------------------------------------------------------------------------
OVERAGE_POLICY=FREEZE                       # FREEZE（預設，絕不動用超額）| ALLOW_WITH_CAP
OVERAGE_HARD_CAP_USD=                       # OVERAGE_POLICY=ALLOW_WITH_CAP 時必填，無預設
OVERAGE_ALERT_ON_FIRST_USE=true             # 一旦偵測到 overage 類額度被動用即告警
OVERAGE_MONTHLY_UTILIZATION_HALT=80         # 月度超額利用率達此值 → 強制 FREEZE

# ------------------------------------------------------------------------------
# 5. 上下文管理（與額度水位「無關」，v1 混用是錯誤的）
# ------------------------------------------------------------------------------
CONTEXT_COMPACT_PERCENT=84                  # 【新增】單一 session 上下文佔用率（R92 掌舵者裁決 75→84：與額度尺 85/95 錯開以保鑑別力）
COMPACT_COST_BUDGET_PP=3                    # 【新增】一次壓縮預估消耗的額度百分點
COMPACT_MIN_INTERVAL_SECONDS=1800           # 【新增】
# 已廢除：TOKEN_COMPACT_PERCENT（語意錯誤，見 §10 遷移對照）

# ------------------------------------------------------------------------------
# 6. 動態併發
# ------------------------------------------------------------------------------
AGENT_MIN_CONCURRENCY=1
AGENT_DEFAULT_CONCURRENCY=2
AGENT_MAX_CONCURRENCY=5                     # 亦受 CPU/RAM 與平台併發限制夾緊
AGENT_THROTTLE_CONCURRENCY=1                # 【新增】THROTTLING 狀態上限
BURN_RATE_EWMA_ALPHA=0.25                   # 【新增】取代固定 15 分鐘視窗
CONTROL_INTERVAL_SECONDS=120                # 【新增】控制週期（應 ≥ 2× Step 中位時間）
CONCURRENCY_MIN_DWELL_SECONDS=300           # 【新增】升併發的最小停留時間
FAIL_SAFE_CONCURRENCY=0                     # 【新增】遙測不可得時的併發（0 或 1）

# ------------------------------------------------------------------------------
# 7. 突刺（BURSTING）
# ------------------------------------------------------------------------------
ENABLE_BURSTING=true
BURST_WINDOW_MINUTES=30
BURST_MAX_U5H_PERCENT=60                    # 【新增】
BURST_WEEKLY_GUARD_PERCENT=60               # 【新增】v1 缺此閘門 → 會提前燒光週額度

# ------------------------------------------------------------------------------
# 8. Agent 硬性預算（v1 缺漏）
# ------------------------------------------------------------------------------
MAX_STEP_TURNS=40
MAX_STEP_WALL_SECONDS=900
MAX_STEP_QUOTA_PP=5
DRAIN_BUDGET_FACTOR=0.5
AGENT_TERMINATION_GRACE_SECONDS=30

# ------------------------------------------------------------------------------
# 9. 重置、休眠與喚醒
# ------------------------------------------------------------------------------
RESET_BUFFER_SECONDS=30
RESET_CONFIRM_PERCENT=10                    # 【新增】喚醒前確認 U5h 已低於此值
SLEEP_SLICE_SECONDS=30                      # 【新增】分片休眠（可回應訊號）
CLOCK_JUMP_TOLERANCE_SECONDS=120            # 【新增】偵測系統睡眠/NTP 跳躍
MAX_INPROCESS_WAIT_SECONDS=7200             # 【新增】超過則交棒 OS 排程器
RESUME_STRATEGY=AUTO                        # 【新增】AUTO|SESSION_RESUME|FRESH_SESSION_WITH_STATE
RESUME_MAX_TRANSCRIPT_TOKENS=60000          # 【新增】AUTO 的切換門檻

# ------------------------------------------------------------------------------
# 10. 防休眠
# ------------------------------------------------------------------------------
OS_KEEP_AWAKE_DRIVER=AUTO                   # AUTO|MACOS_CAFFEINATE|WIN32_API|LINUX_SYSTEMD|NONE
KEEP_AWAKE_ALLOW_DISPLAY_SLEEP=true
KEEP_AWAKE_VERIFY_ON_START=true             # 【新增】啟動自檢是否真的生效

# ------------------------------------------------------------------------------
# 11. Git 與整合
# ------------------------------------------------------------------------------
ENABLE_WORKTREE_ISOLATION=true
AUTOCLAUDE_WORKTREE_DIR=.autoclaude/worktrees
INTEGRATION_BRANCH=autoclaude/integration    # 【新增】不直接動 main
CONFLICT_POLICY=HUMAN_REVIEW                 # 【新增】ABORT|RETRY_WITH_AGENT|HUMAN_REVIEW
INTEGRATION_VERIFY_CMD="npm run lint && npm test"  # 【新增】合併前閘門

# ------------------------------------------------------------------------------
# 12. 狀態持久化
# ------------------------------------------------------------------------------
AUTOCLAUDE_STATE_FILE=.autoclaude/state.json
AUTOCLAUDE_CHECKPOINT_DIR=.autoclaude/checkpoints
STATE_WRITE_MODE=ATOMIC                      # 【新增】tmp → fsync → rename
STATE_RETAIN_VERSIONS=5                      # 【新增】保留歷史版本供人工回溯

# ------------------------------------------------------------------------------
# 13. 安全（v1 缺此整段）
# ------------------------------------------------------------------------------
ALLOW_PERMISSION_BYPASS=false                # 【新增】true 僅限隔離容器
AGENT_PERMISSION_MODE=acceptEdits            # 【需核對旗標名稱】
AGENT_ALLOWED_TOOLS="Read,Edit,Write,Bash(npm test:*),Bash(git status)"
REDACT_SECRETS_IN_LOGS=true                  # 【新增】

# ------------------------------------------------------------------------------
# 14. 可觀測性與運維
# ------------------------------------------------------------------------------
LOG_LEVEL=INFO
LOG_FILE=.autoclaude/logs/daemon.log
METRICS_EXPORT=PROMETHEUS_TEXTFILE           # NONE|PROMETHEUS_TEXTFILE|OTLP
ALERT_WEBHOOK_URL=                           # 【新增】狀態升級/凍結/衝突時通知
DRY_RUN=false                                # 【新增】只決策不派工，用於調參
AUTOCLAUDE_DAEMON_LOCK=.autoclaude/daemon.lock

# ------------------------------------------------------------------------------
# 15. API_KEY 模式專用（AUTH_MODE=API_KEY 時必填）
# ------------------------------------------------------------------------------
API_BUDGET_PERIOD=DAILY                      # 【新增】DAILY|WEEKLY|MONTHLY
API_BUDGET_HARD_USD=                         # 【新增】必填，無預設
API_AUTO_CONTINUE_NEXT_PERIOD=false          # 【新增】
```

### 6.1 啟動自檢不變式（v1 缺漏，必須實作）

```
1.  0 < WARN < DRAIN < HALT ≤ 100  且  HALT − DRAIN ≥ 5
2.  WEEKLY_WARN < WEEKLY_DRAIN < WEEKLY_HALT ≤ 100
3.  1 ≤ C_min ≤ C_default ≤ C_max  且  C_throttle ≥ C_min
4.  WATERMARK_HYSTERESIS_PP < (DRAIN − WARN)
5.  CONTROL_INTERVAL_SECONDS ≥ MONITOR_POLL_INTERVAL_SECONDS
6.  COMPACT_COST_BUDGET_PP < (DRAIN − WARN)
7.  AUTH_MODE=API_KEY → API_BUDGET_HARD_USD 必須有值
7b. OVERAGE_POLICY=ALLOW_WITH_CAP → OVERAGE_HARD_CAP_USD 必須有值，否則拒絕啟動
7c. PACING_MODE=PACE_INDEX → 各 PACE_CEILING 需滿足 THROTTLE < DRAIN 且均 > 1.0
8.  ALLOW_PERMISSION_BYPASS=true → 必須偵測到容器/VM 環境，否則拒絕啟動
9.  Git repo 存在、工作區乾淨或已確認、.autoclaude/ 已在 .gitignore
10. 至少一個遙測來源可用；防休眠驅動可用（若需要）
違反 → 明確錯誤訊息 + 非零退出碼；不得以預設值靜默帶過
```

---

## 7. 狀態資料結構規格（state.json schema v2）

修正 v1 的問題：單一 worktree/session 欄位（與多 Agent 矛盾）、非法 SHA 長度、`reset_timestamp` 與 `saved_at` 相距 24 小時（5 小時視窗不可能）、缺少校驗與續作指令的安全問題。

```json
{
  "schema_version": "2.0.0",
  "checksum_sha256": "<除本欄位外之序列化內容的 SHA-256，用於偵測半寫入>",
  "saved_at": "2026-08-14T10:52:00+08:00",
  "saved_at_epoch": 1786675920,
  "reason": "U5H_HALT_REACHED",
  "reason_detail": "u5h=95.2 >= halt=95.0",
  "daemon": {
    "daemon_id": "d-7f3a91",
    "pid": 48213,
    "version": "2.0.0",
    "host": "macbook-pro-dev",
    "project_root": "/Users/dev/orders-api",
    "dry_run": false
  },
  "quota_snapshot": {
    "auth_mode": "OAUTH",
    "telemetry_source": "T1_OTEL",
    "is_local_estimate": false,
    "u5h_percent": 95.2,
    "u7d_percent": 68.4,
    "u7d_high_tier_model_percent": 41.0,
    "reset_at": "2026-08-14T13:00:00+08:00",
    "reset_timestamp": 1786683600,
    "weekly_reset_at": "2026-08-18T09:00:00+08:00",
    "weekly_reset_timestamp": 1787014800,
    "observed_burn_rate_pct_per_min": 0.42
  },
  "agents": [
    {
      "agent_id": "agent-1",
      "session_id": "6f1c9d84-2b7e-4a03-9c51-8ad30f6b2e77",
      "model": "<實際使用的模型識別字串>",
      "worktree_path": ".autoclaude/worktrees/agent-1",
      "git_branch": "autoclaude/agent-1-r0042",
      "base_sha": "3c1e77a95b40d2f8ae61c04b9d7f2513ab8e6c90",
      "checkpoint_sha": "a8f3b4c91023d8e9f0c7b21d4e5a6f7089c3d1b2",
      "working_tree_clean": true,
      "context_utilization_percent": 62.5,
      "transcript_estimated_tokens": 48210,
      "termination": "GRACEFUL",
      "assigned_step": 3
    }
  ],
  "task_state": {
    "task_id": "TASK-2026-088",
    "dag": {
      "nodes": [
        { "step": 1, "title": "DB Schema Migration",            "deps": [] },
        { "step": 2, "title": "Implement Repository",            "deps": [1] },
        { "step": 3, "title": "Build REST Controller & Tests",   "deps": [2] },
        { "step": 4, "title": "E2E Integration Test",            "deps": [3] },
        { "step": 5, "title": "Update API Docs",                 "deps": [3] }
      ]
    },
    "total_steps": 5,
    "completed_steps": [
      { "step": 1, "status": "COMPLETED", "completed_at": "2026-08-14T09:14:00+08:00", "quota_cost_pp": 8.1 },
      { "step": 2, "status": "COMPLETED", "completed_at": "2026-08-14T10:02:00+08:00", "quota_cost_pp": 12.4 }
    ],
    "interrupted_steps": [
      {
        "step": 3,
        "status": "PAUSED_AT_QUOTA_LIMIT",
        "agent_id": "agent-1",
        "progress_note": "controller 骨架與 3/8 單元測試已完成；剩餘測試未撰寫",
        "files_modified": ["src/controllers/order.controller.ts"],
        "files_pending": ["test/order.controller.spec.ts"],
        "verification_status": "TESTS_NOT_RUN",
        "quota_cost_pp_so_far": 21.7
      }
    ],
    "remaining_steps": [4, 5],
    "blocked_steps": []
  },
  "resume_plan": {
    "strategy": "AUTO_RESOLVED_TO_SESSION_RESUME",
    "strategy_reason": "transcript_tokens=48210 <= threshold=60000",
    "not_before": "2026-08-14T13:00:30+08:00",
    "prompt": "額度已重置。請讀取 .autoclaude/state.json，從 interrupted_steps 繼續；先執行 npm test 確認現況，再補齊 test/order.controller.spec.ts。",
    "permission_mode": "acceptEdits",
    "allowed_tools": ["Read", "Edit", "Write", "Bash(npm test:*)"],
    "max_turns": 40,
    "retry_count": 0,
    "max_retries": 5
  },
  "integration_queue": [
    { "agent_id": "agent-1", "branch": "autoclaude/agent-1-r0042", "status": "PENDING_VERIFY" }
  ]
}
```

**Schema 設計要點**
- `resume_plan` 只存**參數**，不存可直接執行的完整 shell 命令字串。v1 把 `resumption_command` 存成完整命令（含引號內的中文提示）會有 shell 注入與引號轉義風險，且讓 state.json 從資料變成可執行碼。
- `agents` 為陣列；每個 Agent 有自己的 session、分支、checkpoint。
- 記錄 `quota_cost_pp`：累積實際成本資料，可用於「Step 額度預算」的自適應校準。
- `checksum_sha256` + 原子寫入：防止在凍結途中斷電造成半寫入而無法恢復。
- SHA 使用完整 40 字元十六進位（v1 的 16 字元非法）。
- 時間同時提供 ISO 8601（含時區）與 epoch，且兩者必須一致（v1 範例不一致）。

---

## 8. 例外與邊界條件（擴充）

| # | 異常事件 | 觸發情境 | 防禦機制 |
| :-- | :---- | :---- | :---- |
| 1 | **非預期 429** | 遙測落後於真實用量，或其他裝置同時消耗 | 優先**遵循回應中的重試建議標頭**；無標頭時採 full jitter 退避：`sleep = rand(0, min(300, 10·2^n))`，最多 5 次。v1 的固定 10/30/90s 無 jitter，多 Agent 同時撞牆會同步重試造成雷群。重試耗盡 → `FREEZING`。**且必須把 429 視為遙測低估的證據**，將 `U5h` 推估值上修 |
| 2 | **重置時間漂移** | 後端重置延遲 | 醒來後確認 `U5h < RESET_CONFIRM_PERCENT`；未達則退避重試（30s→300s，最多 10 次），仍未達則延長等待並告警 |
| 3 | **Git index.lock 殘留** | 中斷時 git 操作未完成 | 檢查鎖檔 **mtime 與持有 PID 是否存活**；僅清理確認陳舊者。v1 的「清理陳舊鎖」若無存活檢查，可能刪掉正在使用的鎖而毀損 repo |
| 4 | **斷電／強制重啟** | — | `INIT` 掃描 state.json + checksum 驗證；提供 `autoclaude resume` 與 `--force-fresh`。若 checksum 失敗 → 回退到 `STATE_RETAIN_VERSIONS` 中最近的有效版本 |
| 5 | **【新增】機器在等待中睡著** | 防休眠失效 / Modern Standby | 醒來偵測時鐘跳躍 → 立即重新輪詢 → 若已過重置點直接 `RESUMING`；記錄防休眠失效事件並告警 |
| 6 | **【新增】遙測來源永久失效** | 未公開端點被移除、記錄檔格式變更 | 依 `TELEMETRY_SOURCE_ORDER` 降級；全部失效 → `DRAINING` + 告警，**絕不**猜測用量繼續派工 |
| 7 | **【新增】同帳號多 Daemon 超燒** | 兩個專案同時跑 | §4.7 帳號配額仲裁鎖 + 租約 |
| 8 | **【新增】Worktree 有未提交變更且無法提交** | 檔案權限、pre-commit hook 失敗 | 依序嘗試：`commit --no-verify` → `git stash` → 產生 patch 檔存入 checkpoints 目錄；三者皆失敗 → 標記 `DIRTY_UNSAVED` 並在 state.json 中明確警示，禁止自動喚醒（需人工確認） |
| 9 | **【新增】Agent 無回應／卡死** | 等待外部指令、無限循環 | 硬性預算逾時 → 優雅終止序列；連續 `N` 次卡死同一 Step → 標記 `NEEDS_HUMAN` |
| 10 | **【新增】喚醒後上下文已不可用** | session 記錄被清理、CLI 升級不相容 | 自動降級為 `FRESH_SESSION_WITH_STATE`；此為 `SESSION_RESUME` 的必備退路（v1 無退路） |
| 11 | **【新增】整合驗證失敗** | 測試在合併前不通過 | 退回佇列並記錄；`CONFLICT_POLICY` 決定是否派 Agent 修復（並計入額度預算） |
| 12 | **【新增】Prompt injection** | Agent 讀入 repo 中含惡意指令的檔案／依賴 | 工具白名單 + 寫入範圍限制在 worktree + 禁止未經確認的網路存取；Daemon 對 Agent 產出的「狀態回報」做 schema 驗證，不直接信任自然語言 |
| 13 | **【新增】CLI 版本升級破壞相容性** | 旗標／輸出格式改變 | 啟動時記錄 CLI 版本並比對已驗證清單；未知版本 → 進入 `DRY_RUN` 並要求人工確認 |
| 14 | **【新增】磁碟空間不足** | worktrees 與記錄檔累積 | 啟動與凍結前檢查可用空間；不足則清理已合併 worktree 並告警 |

---

## 9. 可觀測性（v1 完全缺漏）

**必要指標**（供事後調參與事故分析）

| 指標 | 型別 | 用途 |
| :---- | :---- | :---- |
| `autoclaude_u5h_percent` / `autoclaude_u7d_percent` | gauge | 額度趨勢 |
| `autoclaude_burn_rate_pct_per_min{kind="safe\|actual"}` | gauge | 配速器是否貼合預算 |
| `autoclaude_concurrency{kind="target\|actual"}` | gauge | 控制器行為 |
| `autoclaude_state` | gauge (enum) | 狀態滯留時間分析 |
| `autoclaude_state_transitions_total{from,to,reason}` | counter | 抖動偵測（同一組 from/to 高頻 → 遲滯參數不足） |
| `autoclaude_telemetry_age_seconds{source}` | gauge | 遙測健康度 |
| `autoclaude_step_quota_cost_pp` | histogram | 校準 `MAX_STEP_QUOTA_PP` |
| `autoclaude_resume_cost_pp` | histogram | 量化喚醒成本，驗證 `RESUME_STRATEGY` 門檻 |
| `autoclaude_429_total` | counter | 遙測低估的直接證據 |
| `autoclaude_freeze_duration_seconds` | histogram | 等待時間佔比（效率指標） |
| `autoclaude_integration_outcome_total{result}` | counter | 合併成功率／衝突率 |

**結構化日誌**：每次決策輸出一行 JSON（含所有輸入變數與決策理由），使任一決策皆可重現。**憑證與 token 一律遮蔽**。

**告警**：狀態升級至 `DRAINING` 以上、`LONG_HIBERNATE`、遙測全失效、`DIRTY_UNSAVED`、`NEEDS_HUMAN`、429 突增。

---

## 10. v1 → v2 設定遷移對照

| v1 設定 | v2 處置 | 說明 |
| :---- | :---- | :---- |
| `TOKEN_COMPACT_PERCENT=90` | **廢除** → `CONTEXT_COMPACT_PERCENT` | 語意由「額度 %」改為「上下文佔用 %」，兩者不可互換 |
| `WEEKLY_LIMIT_HALT_PERCENT` | 更名 `WEEKLY_HALT_PERCENT`，並新增 WARN/DRAIN 兩級 | v1 只有單一硬停，缺少漸進收斂 |
| `BURNING_RATE_WINDOW_MINUTES=15` | 保留但預設不使用；改由 `BURN_RATE_EWMA_ALPHA` 控制 | 固定視窗在重置時會產生假訊號 |
| `OS_KEEP_AWAKE_DRIVER=MACOS_CAFFEINATE` | 預設改 `AUTO`，新增 `LINUX_SYSTEMD` | 硬編碼平台會使 Linux/WSL 使用者無防護 |
| `AUTOCLAUDE_ACCOUNT_TYPE` | 保留為提示性欄位 | 不得用於推算額度上限；一律以遙測為準 |
| `resumption_command`（state.json） | 改為結構化 `resume_plan` | 避免 shell 注入與轉義問題 |

**升級程序**：Daemon 讀到 `schema_version: "1.0.0"` 的 state.json 時，執行一次性遷移（補齊 `agents` 陣列、重算 checksum、清除 `resumption_command`），備份原檔至 `checkpoints/`。

---

## 11. 驗收與測試標準（改為可量測，並解決 v1 的矛盾）

### 11.1 零 Token 遙測驗證
- **方法**：啟動 Daemon 於純遙測模式（`DRY_RUN=true`）連續運行 6 小時，不派任何工。
- **判準**：期間 `U5h` 相對於獨立取得的權威用量讀數，增量為 **0**；本機對話記錄檔的 token 加總無新增。
- 若啟用了未公開端點，額外驗證：關閉該端點後系統能自動降級且不中斷。【v2.1.4 指針（R95 修復包補注，納入殘留面清單）：「若啟用了」的措辭寫於 T5 仍為選用時；v2.1.4 起 T5 已升格認可主源（§4.1.1），本條驗證項自此**必做**而非條件式——降級行為即紅線 1 豁免條件 (d)】

### 11.2 配速控制器（以模擬器測試，不燒真實額度）
必須提供**離線模擬器**（餵入合成的 `U5h/U7d/T_rem` 時間序列），對 §4.2.7 的 7 個情境做斷言。額外性質測試：
- **無抖動**：在 `U5h` 於 68%–72% 之間隨機遊走 60 個控制週期，`THROTTLING ⇄ CRUISING` 轉移次數 ≤ 3。
- **無暴衝**：任何單一控制週期的併發增量 ≤ 1。
- **重置後不暴衝**：視窗重置事件後第一個週期的併發 ≤ `C_default`。
- **收斂性**：模擬固定燃燒率下，併發在 10 個週期內收斂並穩定（不再變動）。
- **驗收標準 3b（v1 的矛盾點）**：`U5h = 75%` 時併發必定為 `AGENT_THROTTLE_CONCURRENCY`，**由 `C_cap` 保證，不依賴公式湊巧**。
- **fail-safe**：注入遙測中斷 11 分鐘 → 併發歸零；注入 429 → 用量推估上修且退避有 jitter。

### 11.3 凍結與喚醒
- 人工注入 95% 訊號，斷言：**5 秒內**完成所有 worktree 的 checkpoint 與 state.json 原子寫入，且 `git status` 在每個 worktree 皆為 clean。
- 在 state.json 寫入過程中 `kill -9` → 重啟後能以 checksum 偵測損壞並回退到上一有效版本。
- 喚醒後斷言：接續的是正確的 `interrupted_step`，且**記錄本次喚醒的實際額度成本**（`autoclaude_resume_cost_pp`）。此為 v1 未驗證的關鍵成本項。
- `SESSION_RESUME` 不可用時（刪除 session 記錄）能自動降級為 `FRESH_SESSION_WITH_STATE` 並完成任務。

### 11.4 週上限與長休眠
- 注入 `U7d = 92%` → 斷言進入 `LONG_HIBERNATE`、成功註冊 OS 排程任務、Daemon 退出、排程時間到能自行重啟並恢復。
- 斷言：週上限觸發時**不會**只休眠到 5 小時重置（v1 的缺陷）。

### 11.5 防休眠
- macOS（電池與接電源**兩種**情境）、Windows 11（含 Modern Standby 機型）、Linux：5 小時無操作掛機。
- 判準：`pmset -g assertions` / `powercfg /requests` / `systemd-inhibit --list` 顯示預期的 assertion；主機未進入睡眠；螢幕依設定關閉；Daemon 計時誤差 < 60 秒；Daemon 被 kill 後 assertion 在 10 秒內自動解除（無孤兒 caffeinate）。

### 11.6 多 Agent 隔離與整合
- 3 個 Agent 同時修改**有重疊 import 的相鄰模組**，斷言：無檔案互相覆蓋；整合佇列序列化執行；至少一次衝突能正確走 `CONFLICT_POLICY`；所有 worktree 最終被清理（`git worktree list` 無殘留）。

### 11.7 多實例配額
- 同帳號同時啟動兩個專案的 Daemon，斷言：兩者併發總和不超過單一 Daemon 情境的上限；`U5h` 燃燒率不超過 `V_safe` 的 1.2 倍。

### 11.8 端到端（長時測）
- 24 小時連續運行，跨越至少 4 次 5 小時視窗重置。判準：0 次非預期任務截斷、0 次髒污工作區、`U7d` 未觸及 `WEEKLY_HALT`、有效工作時間佔比（非等待時間 / 總時間）達成設定目標。

---

## 12. 安全性（v1 完全缺漏）

| 面向 | 要求 |
| :---- | :---- |
| **憑證** | 【v2.1.4 劃界修正】允許**唯讀**本機憑證存放處（`~/.claude/.credentials.json`；macOS 為 login Keychain）取得 OAuth token，**僅限**作為呼叫 §4.1.1 T5 認可主源的必要前提，token 唯一去處＝該次請求的 `Authorization` 標頭；除此之外 Daemon 不得複製、轉發或記錄 OAuth token／API key 明文——token **禁止**寫入任何痕跡檔／日誌／快取／任務書。帳號識別一律使用不可逆雜湊。共享遙測快取只存用量數字，不存憑證 |
| **權限旗標** | 預設**不使用**完全跳過權限的旗標。改用權限模式 + 工具白名單。`ALLOW_PERMISSION_BYPASS=true` 需通過容器／VM 環境偵測才允許 |
| **寫入範圍** | 每個 Agent 只能寫入自己的 worktree；禁止寫入 `.git/`、`.env`、`~/.ssh`、`.autoclaude/state.json` |
| **Prompt injection** | repo 內容與第三方依賴皆視為不可信輸入。Agent 的狀態回報必須通過 schema 驗證後才寫入 state.json；不得讓 Agent 直接改寫 Daemon 的控制參數 |
| **命令執行** | 整合驗證命令來自設定檔而非 Agent 產出；state.json 不含可執行命令字串 |
| **日誌** | `REDACT_SECRETS_IN_LOGS=true`；對常見金鑰樣式做遮蔽 |
| **供應鏈** | Agent 不得在無人確認下新增依賴或執行 `postinstall`；建議整合驗證階段跑於離線／受限網路 |

---

## 13. 合規聲明（v1 缺漏，但對本類工具至關重要）

本系統的設計目標是**在額度限制內平順地運作**，並在達限時安全暫停。明確禁止並不予實作：

- 多帳號輪替、帳號池化、憑證共享，以規避單帳號限制。
- 任何形式的限流／計費繞過、請求偽裝。
- 對未公開介面的高頻探測（選用的 T5 來源必須遵守輪詢間隔且失敗即降級）。【v2.1.4 指針（R95 修復包補注，納入殘留面清單）：「選用的」三字寫於升格前；v2.1.4 起 T5 為認可主源（§4.1.1、§15.5 紅線 1 豁免四條件），「遵守輪詢間隔（TTL≥180s）且失敗即降級」的約束原文不變且已機械化】

`[需核對]` 實作前應確認：使用條款對「自動化使用」「未公開端點存取」的規定，以及訂閱制方案是否允許長時間無人看管的自動化運行。此為**上線前的必要檢核項**，非技術問題。

---

## 14. 實作路線圖（建議，v1 無此章）

> **v2.1 註**：本章為 v2.0 基於「大型自建 Daemon」假設所寫的路線圖。核實後建議架構已大幅縮減，**請以 [§15.4](#154-分階段執行步驟) 的階段規劃為準**；本章保留作為對照。

| 階段 | 範圍 | 出場條件 |
| :---- | :---- | :---- |
| **P0 觀測** | 遙測引擎（T1/T2）+ 可觀測性 + `DRY_RUN` | 能連續 24h 正確記錄 `U5h/U7d`，零 token 消耗；取得真實燃燒率分布以校準參數 |
| **P1 保全** | 凍結 / state.json v2 / 分片休眠 / 喚醒（單 Agent） | 通過 11.3；能自動跨越 5 小時視窗重置完成一個長任務 |
| **P2 配速** | 配速控制器 + 離線模擬器 + 平穩性機制 | 通過 11.2 全部性質測試 |
| **P3 並行** | Worktree 隔離 + 整合佇列 + 硬性預算 | 通過 11.6 |
| **P4 韌性** | 週上限長休眠 + 多實例仲裁 + 防休眠三平台 | 通過 11.4、11.5、11.7 |
| **P5 硬化** | 安全、API_KEY 模式、遷移工具 | 通過 11.8 與 §12 檢核 |

**強烈建議**：P0 必須先於 P2。v1 的配速參數（`C_default=2`、水位 70/85/95、15 分鐘視窗）**沒有經驗依據**；在取得真實燃燒率分布前，這些數字只是猜測。P0 的觀測資料應回頭校準所有預設值。

---

## 15. 執行方法論與注意事項（v2.1 新增）

> **本章回答：「v2 是否已完整涵蓋 v1？只執行 v2 即可嗎？」**
>
> **是。** v2 是 v1 的嚴格超集 —— v1 的七個章節（執行摘要、架構與狀態機、五個功能模組、`.env`、`state.json`、邊界條件、驗收標準）全部保留並擴充，沒有任何 v1 內容被刪除而未被取代。**只需執行 v2.1，v1 僅作為變更歷程存檔。**
>
> 唯一需要注意的**語意變更**：v1 的 `TOKEN_COMPACT_PERCENT=90` 在 v2 被廢除而非改名 —— 因為它的定義本身是錯的（見 §2）。若已有依此撰寫的程式碼，必須改寫而非改參數名。完整對照見 [§10](#10-v1--v2-設定遷移對照)。

### 15.1 動工前置檢查（15 分鐘，必做）

```bash
node --version                      # 必須 ≥ 22.0.0
claude --version                    # 記錄版本，寫入 README；本文核實基準為 2.1.232
git --version && git worktree list  # 確認 worktree 可用
```
另外必須人工確認三件本文無法代為驗證的事：

1. **方案類型與額度分軌**：執行 `/usage`，記下實際看到的額度項目（是否有「Current week (Sonnet only)」等分軌）。**不同方案看到的項目不同**，治理邏輯要依實際看到的來寫。
2. **使用條款**：確認方案允許長時間、無人看管的自動化運行。這是**法務問題不是技術問題**，且是唯一可能讓整個專案作廢的風險項。
3. **超額用量設定**：確認帳號目前是否啟用付費超額。若啟用，達到訂閱限制時**不會停止而會開始計費** —— 這會讓「凍結等待」邏輯永遠不觸發，卻默默產生帳單。**這是本專案最危險的單一失敗模式。**

### 15.2 「先採用、後自建」決策矩陣

每個模組動工前先問這三題，依序：

```
Q1. CLI 是否已有原生能力？（查 §0.6 表格 / sdk-tools.d.ts / --help）
      有 → 採用，只寫轉接層。停。
Q2. 是否能用 hook + settings.json 達成？（不需要常駐行程）
      能 → 用 hook。停。
Q3. 是否真的需要一個常駐 Daemon？
      需要的唯一正當理由：跨 session、跨專案的「帳號層級」決策。
      其餘一律不需要。
```
依此矩陣，**真正必須自建的只有四項**：

| 必建模組 | 為何無法用原生能力取代 | 規模估計 |
| :---- | :---- | :---- |
| 治理決策器（配速 + 狀態機） | 原生只有「示警」，沒有「依配速自動調整併發與模型」的決策邏輯 | ~400 行 + 測試 |
| 帳號層級配額仲裁（§4.7） | 額度是帳號共享，CLI 只看得到自己那個 session | ~150 行 |
| 跨 5 小時視窗的長等待與交棒（§4.5.5） | `ScheduleWakeup` 上限 3600 秒，撐不過 5 小時視窗 | ~200 行 |
| 治理層狀態持久化（縮減版 `state.json`） | 任務 DAG 交給原生 Task 工具後，只需存治理狀態 | ~100 行 |

其餘（worktree、任務 DAG、遙測、可觀測性、壓縮、子代理併發上限）**全部採用原生能力**。v2.0 規劃的自建規模因此縮減約 60%。

### 15.3 建議的最小可行架構（修訂後）

```
┌─────────────────────────────────────────────────────────────┐
│ statusLine hook (CLI 主動呼叫，零 Token)                     │
│   讀 stdin JSON → 抽出 rate_limits.* → 寫 governance.json    │
│   → 印出狀態列文字（順便給人看）                              │
└───────────────────────┬─────────────────────────────────────┘
                        │ 檔案（含 mtime 作為新鮮度）
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 治理決策器 (輕量常駐行程，或由 hook 觸發的無狀態函式)          │
│   讀 governance.json + 帳號仲裁鎖                             │
│   → 算 pace_index → 決定 (併發上限, 模型, 是否放行)            │
│   → 寫 .claude/settings.local.json 的 env 區塊                │
│      與 .autoclaude/governance-decision.json                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ PreToolUse hook (閘門)                                       │
│   Agent 工具被呼叫時 → 讀決策 → 超出配額則拒絕並回傳原因       │
│   這是「不派新工」最可靠的實作點：在工具層攔截，而非管行程     │
└─────────────────────────────────────────────────────────────┘
        ＋ PreCompact hook：壓縮前寫 checkpoint
        ＋ Stop / SubagentStop hook：回收 worktree、更新治理狀態
        ＋ OTel → Prometheus：所有指標
```
**關鍵洞察**：v2.0 假設治理層必須「管理多個 CLI 行程」。但用 `PreToolUse` hook 在 `Agent` 工具層攔截，加上調整 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`，就能達到同樣的併發控制，**且不需要行程池、不需要 worktree 管理、不需要訊號處理**。這是本次核實帶來最大的簡化。

### 15.4 分階段執行步驟

每階段都是**可獨立交付、可獨立回滾**的，且順序不可調換。

#### P0 — 觀測（1–2 天）｜先量測，不控制
- 寫 statusLine 腳本：讀 stdin、抽 `rate_limits.five_hour.used_percentage` / `.resets_at` / `seven_day.*`、附加 `fetched_at`，原子寫入 `.autoclaude/governance.json`，並印出精簡狀態列。
- 開啟 `CLAUDE_CODE_ENABLE_TELEMETRY` + Prometheus exporter，接一個本地 Grafana。
- **正常使用 2–3 天，什麼都不控制。**
- **出場條件**：能畫出「利用率 vs 時間」曲線，並回答：一次典型 Step 燒掉多少百分點？週額度平均一天燒幾 %？`pace_index` 的實際分布長什麼樣？
- ⚠️ **不要跳過這階段直接做 P2。** v1 的所有參數（70/85/95、`C_default=2`、15 分鐘）都是猜的；P0 的資料是把它們變成有根據的唯一途徑。

#### P1 — 保全（2–3 天）｜先能安全停，再談能跑多快
- `PreCompact` hook 寫 checkpoint；`Stop` hook 更新治理狀態。
- 縮減版 `state.json`（原子寫入 + checksum）。
- 分片休眠 + 重置確認 + `ScheduleWakeup`／cron 交棒。
- **出場條件**：手動注入高水位訊號，能在 5 秒內落盤且工作區乾淨；重置後能自動接續；`kill -9` 途中能偵測損壞並回退。
- ⚠️ 這階段就要決定 `RESUME_STRATEGY`，並**實測**喚醒的實際額度成本（§11.3）。這個數字會影響後續所有設計。

#### P2 — 配速（2–3 天）｜先離線模擬，再上線
- **先寫離線模擬器**，餵合成時間序列，跑完 §11.2 的全部性質測試。
- 決策器改用 `pace_index`（§4.2.8），用 P0 的資料校準門檻。
- 以 `DRY_RUN=true` 上線一週：只決策、只記錄、不真的限制。比對「若當時照決策執行，結果會如何」。
- **出場條件**：DRY_RUN 一週內決策無震盪（狀態轉移次數合理）、無會導致撞牆的漏放。
- ⚠️ **絕對不要在真實額度上調參**。每次調參要驗證都得等 5 小時，一週只能做十幾次實驗；模擬器一分鐘做幾千次。

#### P3 — 閘門（1–2 天）｜開始真的限制
- `PreToolUse` hook 攔截 `Agent` 工具 + 動態調整 `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`。
- 模型降級致動器（依 `seven_day_opus` / `seven_day_sonnet` 分軌）。
- 改用原生 `isolation: "worktree"`，**不要自建 worktree 腳本**。
- **出場條件**：§11.6 通過；拒絕派工時 Agent 收到清楚的原因而非莫名失敗。

#### P4 — 韌性（2–3 天）
- 帳號層級仲裁鎖、週額度長休眠、三平台防休眠、`OVERAGE_POLICY`。
- **出場條件**：§11.4／11.5／11.7 通過。

#### P5 — 硬化（2 天）
- 安全（§12）、設定不變式自檢（§6.1）、CLI 版本相容性檢查、告警。
- **出場條件**：§11.8 的 24 小時端到端測試通過。

### 15.5 執行注意事項（紅線清單）

1. **不要碰未公開的 HTTP 端點。** 🔴 **唯一豁免（v2.1.4 修憲，掌舵者 2026-08-16 拍板、待四方複審後生效）**：§4.1.1 T5 之唯讀 `GET /api/oauth/usage`，且必須**同時**滿足四條件，缺一即回到禁令本身：(a) **僅限唯讀 GET**，不得對該端點發任何寫入型請求；(b) **端點知識只准有一個程式站點**＝`tools/lib/quota_meter.py`（`USAGE_URL` 常數；不得出現第二個家，現查：全庫 `.py` 內完整 URL 字面僅該檔一處，其餘命中皆為指向該常數的註解與文件）；(c) **TTL≥180 秒節流**（現行 `tools/lib/quota_gate.py` 的 `QUOTA_CACHE_TTL_SECONDS=180`，每 TTL 視窗至多補量一次）；(d) **端點失效時必須降級出聲**（回「量不到」＋降級 cap，見 §4.1.1〈T5 升格依據〉第 4 項），**禁止重試轟炸**。豁免範圍外的未公開端點依然全面禁止。本條原文「statusLine 已提供你需要的一切」經 R90 實測證偽——statusLine 只回 five_hour／seven_day 兩軸，看不到 R87 事故軸 `spend`／`extra_usage`（見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md`）；原文不再是現行規範，保留於版本歷史。
2. **超額用量必須是顯式的 opt-in。** 預設 `OVERAGE_POLICY=FREEZE`。一個「自動繞過限制繼續跑」的系統，配上啟用的付費超額，等於自動花錢機器。
3. **`ScheduleWakeup` 的延遲被夾在 60–3600 秒。** 別以為傳 18000 就會睡 5 小時 —— 它會被靜默夾成 3600，然後你的系統會提早 4 小時醒來、看到還在限流、可能陷入迴圈。
4. **`CronCreate` 的 durable 任務 7 天後自動過期。** 不能當成永久排程。
5. **不要在真實額度上調參**（見 P2）。
6. **失效方向永遠往保守。** 讀不到治理狀態、檔案過期、鎖搶不到 → 一律當成「額度不明」而降級，絕不「先跑再說」。
7. **以 `status` 枚舉為主，百分比為輔。** `rejected` / `allowed_warning` 是平台給的權威判斷；自訂百分比水位只是預測。兩者衝突時信前者。🔴 **通道限定（R90 補；語意不變，只補「它住在哪」——附錄 B-13 已寫對，本條與 §0.6 新發現 2 漏寫）**：枚舉只隨**模型 API 呼叫的限流回應標頭** `anthropic-ratelimit-unified-status` 回來，四條本機可達通道（`/api/oauth/usage` body、同一支 API 的回應標頭、statusLine stdin JSON、逐字稿）R90 實測**全部 0 命中**。⇒ 不發模型請求的元件**沒有「兩者」可衝突**，照本條字面寫出的枚舉分支會是一段永遠走不到的死碼；那種元件的正確作法是把百分比當唯一訊號並在痕跡裡說出「枚舉不可得」，而不是留一個恆假的判斷。依據見 `docs/06_quality/Quota_R90_CrossAccount_Experiment.md`。
8. **本機推估看不到其他裝置的用量。** 若你同時在別的機器或網頁端用同一帳號，statusLine 的讀數不一定同步。務必保留 §4.1.1 的安全邊際，並把 429 當成「推估偏低」的證據。
9. **`--dangerously-skip-permissions` 不要當預設。** 用 `--permission-mode` 加工具白名單。若真的需要旁路，關在容器裡。
10. **不要讓 Agent 修改治理層的設定或狀態檔。** `PreToolUse` hook 要把 `.autoclaude/`、`.claude/settings*.json` 列為禁寫。否則一個「幫我把併發調高」的合理請求就能拆掉整套治理。
11. **記錄 CLI 版本並訂閱其變更。** 本文的核實基準是 2.1.232；內部識別字與旗標會變。升級後先跑 `DRY_RUN` 再放行。
12. **憑證不要進日誌、不要進 `state.json`、不要進遙測標籤。**

### 15.6 常見失敗模式與預防

| 失敗模式 | 徵兆 | 預防 |
| :---- | :---- | :---- |
| 重置後立刻再撞牆 | 每個視窗開頭 20 分鐘就燒掉 40% | 重置後以 `C_min` 起步爬升（§4.5.3）；`pace_index` 天然免疫此問題 |
| 週三就把週額度燒完 | 前三天正常、後四天全在等 | 週額度用配速門檻而非絕對水位（§4.2.8 修正 1） |
| 併發在邊界抖動 | 狀態轉移計數暴增、吞吐反而下降 | 遲滯 + 死區 + 停留時間（§4.2.4） |
| 靜默計費 | 沒觸發過凍結，但帳單出現 | `OVERAGE_POLICY=FREEZE` + 對 `overage` 類額度告警 |
| 喚醒比工作還貴 | `resume_cost_pp` 接近單一 Step 成本 | 量測它（§11.3），超標就切 `FRESH_SESSION_WITH_STATE` |
| 工作區髒污累積 | worktree 越來越多、合併衝突變常態 | 原生 `ExitWorktree` 的未提交變更保護 + 序列化整合佇列（§4.4.2） |
| 治理層被 Agent 改掉 | 參數莫名變寬 | 禁寫清單（紅線 10） |

### 15.7 參數校準方法（用資料取代猜測）

P0 收完資料後，依序推導、不要憑感覺設定：

```
1. 從 claude_code.token.usage 與利用率曲線，算出「單一 Step 的百分點成本」分布
      → MAX_STEP_QUOTA_PP = P95(step_cost_pp) × 1.2
2. 從 5 小時視窗內的實際 Step 數，算出可持續併發
      → C_default = floor(0.85 × 100 / (P50(step_cost_pp) × steps_per_hour × 5))
3. 從 pace_index 的歷史分布，取超前燃燒的容忍點
      → PACE_CEILING = P75(pace_index)，並以 §4.2.8 的 1.25 為上界參考
4. 從一週的日燒率，算出週預算
      → 若日燒率 × 7 > 90%，則系統本質上就是週額度受限，
        應優先投資「模型降級」與「任務篩選」，而非提高併發
5. 從實測喚醒成本
      → RESUME_MAX_TRANSCRIPT_TOKENS = 使 resume_cost_pp ≤ MAX_STEP_QUOTA_PP 的門檻
```
**第 4 點是最重要的**：多數使用者的真正瓶頸是週額度，不是 5 小時視窗。如果 P0 資料顯示如此，那麼「動態併發配速」的價值遠低於「少用高階模型 + 只做值得做的任務」—— 這會改變整個專案的優先序，甚至可能讓 P3 之後的工作變得不必要。**讓資料決定要不要繼續蓋。**

### 15.8 交付物與目錄結構

```
專案根目錄/
├── .claude/
│   ├── settings.json              # 版控：hooks、permissions、statusLine
│   ├── settings.local.json        # 不版控：治理器動態寫入的 env 區塊
│   └── scheduled_tasks.json       # CLI 管理，不手改
├── .autoclaude/                   # 全部加入 .gitignore
│   ├── governance.json            # statusLine 寫入的額度快照
│   ├── governance-decision.json   # 決策器輸出（給 PreToolUse hook 讀）
│   ├── state.json                 # 治理層狀態（縮減版）
│   ├── checkpoints/
│   ├── logs/
│   └── daemon.lock
├── hooks/
│   ├── statusline.sh              # P0
│   ├── pre_tool_use.py            # P3 閘門
│   ├── pre_compact.py             # P1 checkpoint
│   └── stop.py                    # P1 狀態更新
├── governor/
│   ├── decide.py                  # 純函式決策器（§4.2.6）
│   ├── simulate.py                # 離線模擬器（P2 先寫這個）
│   ├── telemetry.py
│   └── arbiter.py                 # 帳號層級仲裁
├── tests/
│   └── test_decide.py             # §11.2 的性質測試
├── .env.example                   # §6
└── README.md                      # 記錄 CLI 核實版本與前置條件
```
`~/.autoclaude/accounts/<fingerprint>/` 放跨專案共享的仲裁鎖與遙測快取。

---

## 附錄 A：v1 → v2 問題清冊（Issue Register）

| ID | 章節 | 類型 | 嚴重度 | v1 的問題 | v2 修正位置 |
| :-- | :---- | :---- | :---- | :---- | :---- |
| A-01 | 3.1 / 4 | 邏輯錯誤 | 🔴 | 混用「額度使用率」與「上下文佔用率」；在額度 90% 觸發壓縮，而壓縮本身會消耗額度 | §2、§4.3 |
| A-02 | 3.4 | 邏輯錯誤 | 🔴 | 週上限觸發後仍只休眠至 5 小時重置，醒來立即再撞牆 | §4.5.5 |
| A-03 | 3.2 vs 7 | 內部矛盾 | 🔴 | 驗收要求 75% 收斂至 `C_min`，但公式無此保證 | §4.2.2、§4.2.7(3b) |
| A-04 | 3.2 | 控制缺陷 | 🟠 | 無遲滯 → 70%/85% 邊界抖動 | §4.2.4(a) |
| A-05 | 3.2 | 控制缺陷 | 🟠 | 無變化率限制 → 併發可從 1 直跳 5 | §4.2.4(c) |
| A-06 | 3.2 | 控制缺陷 | 🟠 | 無最小停留時間／死區 → 控制器快於任務生命週期 | §4.2.4(b)(d)(e) |
| A-07 | 3.2.2 | 數值不一致 | 🟠 | 公式用 `max(0.01,…)`、程式碼用 `max(0.02,…)` | §4.2.1（單一 `V_FLOOR`） |
| A-08 | 3.2.2 | 邏輯錯誤 | 🟠 | `delta_u = max(0, …)` 使視窗重置的負差值被壓為 0 → `V_actual` 觸底 → 重置後立刻暴衝至 `C_max` | §4.1.3、§4.2.6 |
| A-09 | 3.2 | 邏輯錯誤 | 🟠 | `T_rem = max(1, …)` 在重置前一分鐘製造巨大 `V_safe` 假暴衝 | §4.2.2（`T_MIN_MINUTES` hold） |
| A-10 | 3.2 / 3.1 | 缺漏 | 🟠 | 突刺無週額度否決條件；隱含「未用額度會浪費」的錯誤假設 | §4.2.5、§4.2.7(1b) |
| A-11 | 3.1 | 缺漏 | 🟠 | 未定義遙測失效時的失效方向（fail-open 會爆額度） | §4.1.2、§1.2(5) |
| A-12 | 3.4 | 成本錯誤 | 🟠 | 宣稱同 session 續接不重複消耗 token；實際上快取失效後會全額重讀 | §4.5.4 |
| A-13 | 3.4 | 安全 | 🟠 | 預設使用完全跳過權限的旗標 | §4.5.4、§12 |
| A-14 | 3.1 | 事實風險 | 🟠 | 把未公開 OAuth usage 端點列為主要遙測方案，無降級路徑 | §4.1.1（分層 T1–T5） |
| A-15 | 3.1 | 事實錯誤 | 🟡 | 「Statusline 探針」方向反了（statusline 由 CLI 呼叫腳本，非 Daemon 輪詢 CLI） | §4.1.1(T3) |
| A-16 | 1.1 | 事實錯誤 | 🟡 | 「72 小時 / 7 天每週上限」中的「72 小時」並非已知限制週期 | §1.1（刪除） |
| A-17 | 3.1 | 缺漏 | 🟡 | `U5h` 是帳號層級指標，但未說明本機推估看不到其他裝置用量 | §4.1.1（安全邊際） |
| A-18 | 3.3 | 缺漏 | 🟡 | 「Fast-Forward 合併」在多分支分歧時不成立 | §4.4.2（整合佇列） |
| A-19 | 3.3 | 實務缺陷 | 🟡 | `worktree add -b` 分支已存在則失敗；未鎖定基準 SHA；未處理 `.gitignore` 與 prune | §4.4.1 |
| A-20 | 3.4 | 缺漏 | 🟡 | 只 commit 一個 worktree，與多 Agent 設計矛盾 | §4.5.1、§7 |
| A-21 | 2 / 3 | 缺漏 | 🟡 | `DRAINING` 允許「收尾」但無硬性上限，收尾可衝破 `HALT` | §4.4.3 |
| A-22 | 3.5 | 技術錯誤 | 🟡 | `caffeinate -s` 僅在接電源時有效；未綁定 PID（孤兒程序風險）；註解中的 `-d` 與需求矛盾 | §4.6 |
| A-23 | 3.5 | 技術錯誤 | 🟡 | `SetThreadExecutionState` 是執行緒層級，短命執行緒呼叫即失效；`ES_AWAYMODE_REQUIRED` 用途不符；未還原 | §4.6 |
| A-24 | 3.5 | 缺漏 | 🟡 | 完全未支援 Linux / WSL | §4.6 |
| A-25 | 3.4 | 實作缺陷 | 🟡 | 單次長 sleep 無法回應訊號、無法修正時鐘漂移與系統睡眠 | §4.5.2 |
| A-26 | 5 | 資料錯誤 | 🟡 | `reset_timestamp` 比 `saved_at` 晚 **24 小時**（5 小時視窗不可能） | §7（修正為 +2h08m） |
| A-27 | 5 | 資料錯誤 | 🟡 | `git_commit_hash` 為 16 字元，非合法 Git SHA 長度 | §7（40 字元） |
| A-28 | 5 | 安全 | 🟡 | `resumption_command` 存完整 shell 命令 → 注入與轉義風險 | §7（結構化 `resume_plan`） |
| A-29 | 5 | 缺漏 | 🟡 | 無 checksum／原子寫入／版本保留 → 凍結途中斷電即無法恢復 | §7、§8(4) |
| A-30 | 6 | 缺漏 | 🟡 | 429 退避無 jitter，多 Agent 會同步重試（雷群） | §8(1) |
| A-31 | 6 | 缺漏 | 🟡 | 清理 index.lock 未檢查持有 PID 是否存活 | §8(3) |
| A-32 | — | 缺漏 | 🟡 | 同帳號多專案／多 Daemon 會各自超燒 | §4.7 |
| A-33 | 3.1 | 缺漏 | 🟡 | API_KEY 模式提及 TPM/RPM/餘額，但演算法完全以 % 為基礎，無法運作；且無硬性預算上限 | §5 |
| A-34 | 4 | 缺漏 | 🟡 | 無設定不變式驗證（如 WARN<DRAIN<HALT） | §6.1 |
| A-35 | — | 缺漏 | 🟡 | 無可觀測性、日誌、告警、dry-run、人工覆寫 | §9、§6(14) |
| A-36 | — | 缺漏 | 🟡 | 無安全章節（憑證、寫入範圍、prompt injection、供應鏈） | §12 |
| A-37 | — | 缺漏 | 🟡 | 無合規／ToS 章節與非目標宣告 | §1.3、§13 |
| A-38 | 3.2 | 設計限制 | 🟡 | 只有「併發數」單一致動器，控制力不足（模型層級對燃燒率影響更大） | §4.2.3 |
| A-39 | 7 | 不可測 | 🟡 | 「不得產生任何 token 費用」未定義量測方法 | §11.1 |
| A-40 | 2 | 缺漏 | 🟡 | 狀態機無進入／離開條件、無優先序、`BURSTING` 與 `CRUISING` 百分比區間重疊 | §3.2 |
| A-41 | 3.4 | 缺漏 | 🟡 | `SESSION_RESUME` 無失敗退路（session 記錄不存在時） | §8(10) |
| A-42 | — | 缺漏 | 🟢 | 參數（70/85/95、`C_default=2`、15 分鐘）無經驗依據 | §14（P0 先觀測後調參） |
| A-43 | 全篇 | 文件品質 | 🟢 | Google Docs 匯出殘留（`1\.`、`5h`、`> *` 混排、逐行反引號 ASCII 圖、LaTeX 在多數 Markdown 渲染器不顯示） | 全篇改用標準 Markdown + 程式碼區塊 |

嚴重度：🔴 阻斷級（照 v1 實作會造成系統性失效）／🟠 高（會導致額度超燒、成本失控或安全風險）／🟡 中（缺漏或實務缺陷）／🟢 低（品質與可維護性）

---

## 附錄 B：事實核對結果（v2.1 已核實）

### B.0 核實方法與其限制

**官方文件網域在本次作業環境中不可存取**（`docs.claude.com`、`docs.anthropic.com`、`code.claude.com` 皆回傳 `403 host_not_allowed`）。改採替代路徑：

1. 從 npm registry 取得 `@anthropic-ai/claude-code` 的發佈中介資料（最新 `2.1.232`，另有 `stable = 2.1.223`）。
2. 下載官方發佈的 wrapper 套件，取得 `package.json`、`README.md`、`sdk-tools.d.ts`（**內建工具的完整 TypeScript 介面定義**，官方隨套件發佈）。
3. 下載對應平台的原生二進位套件（`claude-code-linux-x64`，解壓後 323 MB），對其做字串比對，驗證環境變數、CLI 旗標、遙測指標名稱、額度欄位與 HTTP 標頭。

**這個方法的限制必須明講：**

- `sdk-tools.d.ts` 是官方隨套件發佈的介面定義，可信度高。
- 二進位字串則是**實作內部細節**：其中可能包含未啟用的功能旗標、內部識別字、測試用途字串。**看到字串不等於該功能對使用者可用、也不等於它是穩定契約。**
- 本核實**無法**驗證任何非技術事項（使用條款、方案定價、額度實際數值）。
- 核實基準版本為 **2.1.232**；升級後應重跑核實。

### B.1 已核實項目

| # | 原待核對項目 | 結果 | 核實內容 | 對 PRD 的影響 |
| :-- | :---- | :---- | :---- | :---- |
| B-01 | 5 小時視窗語意 | ✅ | 額度類型 `five_hour`，`windowSeconds = 18000`；有 `resets_at` / `resetsAt` 欄位可讀 | 配速與休眠邏輯成立；重置時間可取得，無需推估 |
| B-02 | 週額度與模型分軌 | ✅ | `seven_day`（`windowSeconds = 604800`）、`seven_day_opus`、`seven_day_sonnet`、`seven_day_overage_included`；UI 標題為「Current session」「Current week (all models)」「Current week (Sonnet only)」，後者於 max / team 方案顯示 | 週閘門與模型降級致動器**確認可實作**；分軌額度是 v2 未預期的細節 |
| B-03 | 官方遙測機制 | ✅ | `CLAUDE_CODE_ENABLE_TELEMETRY`；完整 OTLP 環境變數族；**含 `OTEL_EXPORTER_PROMETHEUS_HOST/PORT`**；指標含 `claude_code.token.usage`、`claude_code.cost.usage`、`claude_code.compaction`、`claude_code.subagent.spawn`、`claude_code.llm_request`、`claude_code.hook`、`claude_code.tool.execution`、`claude_code.active_time.total` 等 | §9 可觀測性**大部分免費取得**；T1 為首選確認正確 |
| B-04 | 對話記錄檔路徑與格式 | ✅ | `~/.claude/projects/<sanitized-cwd>/*.jsonl`，每行一個 JSON 物件；工具呼叫出現在 `assistant` 訊息的 `message.content[]` | T2 遙測與上下文估算可實作 |
| B-05 | statusLine 輸入結構 | ✅ **關鍵** | stdin JSON 含 `rate_limits.five_hour.used_percentage`、`.resets_at`、`rate_limits.seven_day.*`、`rate_limits.model_scoped`、`rate_limits_available`、`subscription_type`、`session.total_cost_usd` / `.total_api_duration_ms` / `.model_usage` / `.total_lines_added`；二進位內含 jq 範例腳本 | **這是零 Token 遙測的正解**。T5（未公開端點）可完全刪除 |
| B-06 | 用量查詢指令 | ⚠️ 部分 | `/usage` 存在且有「非互動模式的格式化成本摘要」；另有 `/usage-credits`、`/status`、`/model`、`/compact` | 可用但格式非契約；優先用 B-05 |
| B-07 | 壓縮觸發與 hook | ✅ | 自動壓縮相關：`CLAUDE_CODE_AUTO_COMPACT_WINDOW`、`CLAUDE_CODE_COLD_COMPACT`、`CLAUDE_CODE_DISABLE_PRECOMPACT_SKIP`；hook 事件含 **`PreCompact` 與 `PostCompact`** | §4.3 的擔憂成立：**不需自行下達壓縮指令**，改用 hook 在壓縮前寫 checkpoint |
| B-08 | `--resume` 行為 | ⚠️ 部分 | `--resume`、`--continue`、`--session-id`、**`--fork-session`** 皆存在；另有 `CLAUDE_CODE_RESUME_TOKEN_THRESHOLD`、`CLAUDE_CODE_RESUME_INTERRUPTED_TURN`、`CLAUDE_CODE_RESUME_PROMPT`、`CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` | 旗標確認；**但「續接是否重新計費完整歷史」仍需實測**（§11.3 已納入量測）。`--fork-session` 是 v2 未考慮的選項：可在不變更原 session 的前提下續接 |
| B-09 | 權限模式與工具白名單 | ✅ | 權限模式：`default`、`plan`、`acceptEdits`、`bypassPermissions`、`dontAsk`、`auto`；旗標 `--permission-mode`、`--allowed-tools`（亦接受 `--allowedTools`）、`--disallowedTools`、`--dangerously-skip-permissions`；子代理繼承父 session 的權限模式，agent 定義的 frontmatter 可覆寫 | §12 的建議可直接實作；`dontAsk` / `auto` 是 v2 未知的中間選項，值得評估 |
| B-10 | 硬性預算旗標 | ✅ | `--max-turns`、`CLAUDE_CODE_MAX_TURNS`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS`、`CLAUDE_CODE_MAX_CONTEXT_TOKENS`、`CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS`、`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` | §4.4.3 可實作，且顆粒度比 v2 設想的更細 |
| B-11 | 模型選擇與降級 | ✅ | `--model`；`Agent` 工具的 `model` 欄位可取 `"sonnet" \| "opus" \| "haiku" \| "fable"`；`CLAUDE_CODE_SUBAGENT_MODEL`；`/model` 指令 | 模型降級致動器**確認可實作**，且可針對個別子代理 |
| B-12 | 提示快取存活時間 | ❌ 未能核實 | 二進位中未找到明確的 TTL 值 | §4.5.4 的成本論述**改以實測為依據**（§11.3），不依賴假設值 |
| B-13 | 限流標頭 | ✅ | `retry-after`；**`anthropic-ratelimit-unified-status`、`-reset`、`-representative-claim`、`-fallback`、`-grace-status`、`-upgrade-paths`、`-overage-status`、`-overage-utilization`、`-overage-reset`、`-overage-period`、`-overage-period-monthly-utilization`**；狀態枚舉 `allowed` / `allowed_warning` / `rejected` | §8(1) 可實作且**應優先信任 `status` 枚舉**而非自訂百分比水位 |
| B-14 | 併發上限 | ✅ | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`（超出時錯誤訊息明示「請使用者調高此變數」）、`CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`、`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`、`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | **併發致動器改為調整設定值**，不需自建行程池 —— 本次核實帶來的最大簡化 |
| B-15 | 模型計價 | ❌ 未能核實 | 二進位不含價目表 | §5 的成本計算需以官方定價頁為來源，且價目表必須可設定 |
| B-16 | 使用條款 | ❌ 無法核實 | 屬法務事項，非技術可驗證 | **仍為上線前必要檢核項**（§15.1 第 2 點） |
| B-17 | 套件與前置條件 | ✅ | `@anthropic-ai/claude-code`，**Node.js ≥ 22**；現以各平台原生二進位發佈（`darwin-arm64/x64`、`linux-x64/arm64` 含 `-musl` 與 `-android`、`win32-x64/arm64`）；安裝後不常駐 Node 行程 | **Linux 支援確認**（A-24 成立）；PRD 應新增前置條件章節（已補於 §15.1） |

### B.2 核實中發現的、原清單未列的重要事實

| # | 發現 | 為何重要 |
| :-- | :---- | :---- |
| B-18 | **超額用量維度**：額度類型含 `overage`、`extra_usage`、`seven_day_overage_included`；標頭含 `-overage-utilization`、`-overage-period-monthly-utilization`、`-overage-disabled-reason`；訊息提及月度支出上限與 `/usage-credits` | 達訂閱限制後**可能付費續跑而非停止**。這讓「凍結等待」邏輯可能永不觸發卻默默計費 —— PRD 完全遺漏，且是最危險的失敗模式 |
| B-19 | **CLI 內建配速判準**：`five_hour` → `{utilization: 0.9, timePct: 0.72}`；`seven_day` → `{0.75, 0.6}`、`{0.5, 0.35}`、`{0.25, 0.15}` | 驗證 `V_safe` 觀念，並提供官方參考值。導出更穩健的 `pace_index` 形式（§4.2.8），可完全免除燃燒率估計的冷啟動與調參問題 |
| B-20 | **原生 worktree 隔離**：`Agent` 工具 `isolation: "worktree" \| "remote"`；`EnterWorktree` / `ExitWorktree`（`action: keep \| remove`，未提交變更時拒絕並要求 `discard_changes: true`）；`worktree.bgIsolation` 設定 | §4.4.1 的自建腳本不需要了；原生版本的未提交變更保護正是 §8(8) 想解決的問題 |
| B-21 | **原生任務 DAG**：`TaskCreate` / `TaskUpdate` / `TaskList` / `TaskGet` / `TaskStop` / `TaskOutput`，支援 `addBlocks` / `addBlockedBy` / `owner` / `metadata` / 狀態 `pending \| in_progress \| completed \| deleted` | §7 的 `task_state.dag` 可交給原生工具，`state.json` 縮減為純治理狀態 |
| B-22 | **原生排程**：`CronCreate`（5 欄位 cron、`recurring`、`durable` → `.claude/scheduled_tasks.json` 跨 session 存活、**7 天後自動過期**）、`CronList`、`CronDelete`；`ScheduleWakeup`（**`delaySeconds` 被夾在 [60, 3600]**，含 `wasClamped` 回報） | §4.5.5 部分可用原生。但 `ScheduleWakeup` 上限 1 小時，**單次無法撐過 5 小時視窗** —— 若誤以為可以，系統會提早 4 小時醒來 |
| B-23 | **`Monitor` 工具**：以 shell 命令或 WebSocket 持續監看，每行 stdout 為一事件，`persistent` 可存活整個 session | 遙測攝取的另一條路徑，可能免除獨立輪詢行程 |
| B-24 | **完整 hook 事件集**：`PreToolUse`、`PostToolUse`、`PreCompact`、`PostCompact`、`SessionStart`、`SessionEnd`、`Stop`、`SubagentStop`、`Notification`、`UserPromptSubmit` | 使 §15.3 的「hook 為主、Daemon 為輔」架構成為可能 —— 治理閘門放在 `PreToolUse` 比管理行程可靠得多 |
| B-25 | 其他相關環境變數：`CLAUDE_CODE_RATE_LIMIT_TIER`、`CLAUDE_CODE_IDLE_TOKEN_THRESHOLD`、`CLAUDE_CODE_TOTAL_TOKENS_REMINDER_BUDGET`、`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`、`CLAUDE_CODE_ENABLE_TOKEN_USAGE_ATTACHMENT` | 可能提供更直接的治理槓桿，值得逐一試驗（屬**內部**，需驗證） |

### B.3 仍待人工確認（本次無法核實）

| # | 項目 | 建議做法 |
| :-- | :---- | :---- |
| 1 | 使用條款對長時間無人看管自動化的規定 | 閱讀條款；必要時聯繫 Anthropic。**這是唯一可能讓專案作廢的風險項** |
| 2 | 帳號是否已啟用付費超額、月度支出上限為何 | 執行 `/usage`、`/usage-credits` 並檢視帳號設定 |
| 3 | 續接長對話的實際額度成本 | 依 §11.3 實測，這是無法從程式碼推導的數字 |
| 4 | 提示快取 TTL、模型定價 | 查官方文件（下方連結） |
| 5 | 各方案實際可見的額度分軌項目 | 在目標帳號上執行 `/usage` 並記錄 |

### B.4 文件入口（已更新）

原清單中的 `docs.anthropic.com/en/docs/claude-code/...` 路徑已過期。核實發現官方 README 現指向：

- **Claude Code 文件**：`https://code.claude.com/docs/en/overview`
- **資料使用政策**：`https://code.claude.com/docs/en/data-usage`
- **Claude Code 首頁**：`https://claude.com/product/claude-code`
- **商業使用條款**：`https://www.anthropic.com/legal/commercial-terms`
- **Claude API 文件**：`https://docs.claude.com/en/api/overview`
- **問題回報**：`https://github.com/anthropics/claude-code/issues`

---

*文件結束。*

*v2.1 修訂原則：能核實的就核實並註明來源與版本；不能核實的就明說不能，不用推測填空。已內建的能力優先採用，自建範圍壓到最小。所有控制迴路必須可離線模擬與斷言，所有失效路徑往保守方向收斂。*
