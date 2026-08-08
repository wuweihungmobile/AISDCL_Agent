# CrossPlatform_R81_Quota_Review — 額度監控四路（research／design／SA／SD）

## §0 這份檔為什麼存在

本檔是 `docs/06_quality/CrossPlatform_R81_Scan_Findings.md` 的**姊妹檔**（拆分理由與對照表
見該檔 §8）。它承載掌舵者訴求 a／b（Token 水位用 % 監控、80% 少派 agent、95% 停止並準備喚醒）
這條主線的全部產出：一路對外調研＋對內盤點、一份 ADR 設計、兩位獨立審查者的 verdict。

🔴 **這是 R81 第一批唯一經過獨立複驗的一路**——其餘五路都只有單一 agent 自陳。
SA 與 SD 逐條實查了 ADR 的每一個可查宣稱，兩人**都**在事實面給了正面評價
（ADR 點名的檔案／函式／常數／行號全部存在且對得上），但**結構面各自抓出 blocking**。

🔴 **ADR 目前是 `Proposed`，不是已核准**：SA 給 REJECT、SD 給 APPROVE_WITH_CONDITIONS，
合計 11 筆 blocking 未收斂前，本檔的任何段落都不得被引用為「已定案的設計」。


## §1 四路一覽

| 角色 | agentId | 產出 | verdict |
|---|---|---|---|
| research:quota | `a601a9532a034b431` | 12 筆 findings | — |
| design:architect | `a903e58aa38d247dd` | ADR-XPLAT-005（17 項核心決策／9 個 step／12 條 open question） | Proposed |
| review:SA（系統分析師） | `a66fef5cb9eab2530` | 7 blocking ＋ 9 non-blocking | **REJECT** |
| review:SD（系統設計師） | `a8f087f3bf99205c8` | 4 blocking ＋ 7 non-blocking | **APPROVE_WITH_CONDITIONS** |

## §2 research:quota — 額度／Token 水位監控的對外調研＋對內盤點（12 筆）

**任務**：回答訴求 a（水位用 %）／b（80% 少派 agent、95% 停止）能不能實作：有沒有可程式化取得**額度水位**的介面。

**agentId**：`a601a9532a034b431`　**筆數**：12（P0 3／P1 5／P2 4／P3 0）

### §2.1 索引

| 本檔 ID | 原始 ID | sev | 標題（逐字） | 檔案:行 | 成本 |
|---|---|---|---|---|---|
| `QTA-S1-01` | S1-01 | P0 | 有辦法：GET /api/oauth/usage 直接回傳 server 算好的額度百分比（訴求 a 的完整解，本輪實測 HTTP 200） | N/A（外部端點；憑證 C:\Users\wuwei\.claude\.credentials.json） | small |
| `QTA-S1-02` | S1-02 | P0 | 全 repo 對「額度水位」零消費者：三套現行機制量的全是 context 水位，沒有一個在量額度 | D:\CursorProject\AISDCL_Agent\.claude\hooks\context_budget_guard.py:194、D:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\utils\token_tracker.py:83 | medium |
| `QTA-S1-03` | S1-03 | P0 | reset 時刻不必再從錯誤訊息猜：endpoint 直接給精確 ISO 時刻，整條 parse_reset_at 觀測鏈可降級為 fallback | D:\CursorProject\AISDCL_Agent\.claude\hooks\context_budget_guard.py:464、D:\CursorProject\AISDCL_Agent\tools\probe\reset_window_distribution.py:1 | medium |
| `QTA-S1-04` | S1-04 | P1 | 同一個 bucket 在兩條通道給的單位不同：event 給 0.3（分數）、REST 給 30.0（百分比），混用會差 100 倍 | N/A（跨通道；claude.exe v2.1.223） | small |
| `QTA-S1-05` | S1-05 | P1 | headless SDK 通道結構上不可靠：rate_limit_event 只在跨警戒門檻時帶 utilization，且本次完全沒吐 five_hour | N/A（claude -p --output-format stream-json；claude.exe v2.1.223） | small |
| `QTA-S1-06` | S1-06 | P1 | statusLine 通道欄位最齊（含 context% 與 quota% 兩軸皆 server 預算好），但 TUI-only，且本機根本沒設定 | C:\Users\wuwei\.claude\settings.json:1 | small |
| `QTA-S1-07` | S1-07 | P1 | 「額度回來了沒」的探測成本可從約 32K tokens 降到零：現行探針花模型呼叫問的問題，endpoint 免費回答 | D:\CursorProject\AISDCL_Agent\tools\session_resume_planner.py:522 | medium |
| `QTA-S1-08` | S1-08 | P2 | OAuth token 4 小時到期：無人看管過夜的取數器會靜默失效，除非實作 refresh | C:\Users\wuwei\.claude\.credentials.json:1 | medium |
| `QTA-S1-09` | S1-09 | P1 | R80 那道「四個分母都湊得出 78%」的謎題是偽命題：UI 的 78% 是 server 算的 percent，本來就不是任何 token 比值 | N/A（對照 CLAUDE.md 與 R80 交棒紀錄） | small |
| `QTA-S1-10` | S1-10 | P2 | 訴求 e 的「每 50 分鐘喚醒一次」不需要：有精確 resets_at 就只排一次；現行 15 分鐘巡邏亦可降頻 | D:\CursorProject\AISDCL_Agent\tools\session_resume_planner.py:306 | small |
| `QTA-S1-11` | S1-11 | P2 | 額度是跨產品共享的帳號級池，且本帳號是 team + 有 per-model 的 weekly_scoped 桶：單看一個數字會誤判 | N/A（endpoint 回傳 + 憑證檔） | medium |
| `QTA-S1-12` | S1-12 | P2 | AutoClaude 的 Token Guard 三槓桿全部掛在 context window 上，且 SDK 的 get_context_usage 結構上不回額度 | D:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\infra\adapters\sdk_executor_adapter.py:243 | large |

### §2.2 逐筆（證據逐字保全）

#### `QTA-S1-01`｜[P0] 有辦法：GET /api/oauth/usage 直接回傳 server 算好的額度百分比（訴求 a 的完整解，本輪實測 HTTP 200）

- **檔案:行**：N/A（外部端點；憑證 C:\Users\wuwei\.claude\.credentials.json）
- **成本**：small

**為何要緊（逐字）**：這一條把訴求 a 從「應該有 API」變成「今天就有，且已實測」。三個關鍵性質正好對上掌舵者的要求：①**是百分比不是固定量**——server 依該帳號的方案自己算 utilization，換帳號/換方案不必改任何常數，正是「啟動帳號不同」那句話要的東西；②**不必推分母**——不需要知道 window 是 200K 還是 1M，也不需要任何 token 累加；③**呼叫本身不是模型推論** ⇒ 不吃額度、不進 5 小時視窗。80%/95% 兩道閘（訴求 b）直接寫成 `five_hour.utilization >= 80 / >= 95` 即可，這是本 repo 目前完全沒有的能力。

**當回合實測證據（逐字保全）**：

```text
當回合真跑（python urllib，Bearer 取自 ~/.claude/.credentials.json 的 claudeAiOauth.accessToken，token 值全程未印出）：
  https://api.anthropic.com/api/oauth/usage -> HTTP 200
BODY 逐字（節錄）：
  {"five_hour":{"utilization":44.0,"resets_at":"2026-08-08T13:39:59.297723+00:00","limit_dollars":null,...},
   "seven_day":{"utilization":30.0,"resets_at":"2026-08-14T21:59:59.297788+00:00",...},
   "seven_day_opus":null,"seven_day_sonnet":null,
   "limits":[{"kind":"session","group":"session","percent":44,"severity":"normal","resets_at":"2026-08-08T13:39:59.297723+00:00","scope":null,"is_active":true},
             {"kind":"weekly_all","group":"weekly","percent":30,"severity":"normal","resets_at":"2026-08-14T21:59:59.297788+00:00","is_active":false},
             {"kind":"weekly_scoped",..."percent":0,..."scope":{"model":{"display_name":"Fable"}}}],
   "spend":{"used":{"amount_minor":0,...},"percent":0,"enabled":false,...},
   "extra_usage":{"is_enabled":false,"spend_limit_reached":false,...}}
端點來源不是猜的，是 claude.exe 內的實作逐字（offset 254890300）：
  `T(`fetchUtilization: GET /api/oauth/usage (attempt ${e})`);let r=await zi.get("/api/oauth/usage",{timeout:5000,headers:{"Content-Type":"application/json"},refreshOAuth:!0})`
```

**建議修法（逐字）**：

```text
新增一支唯讀取數器（例如 tools/probe/quota_utilization.py）：讀 ~/.claude/.credentials.json 的 claudeAiOauth.accessToken → GET https://api.anthropic.com/api/oauth/usage → 回 {five_hour:{utilization,resets_at}, seven_day:{...}, spend, extra_usage}。**取數與決策分離**：這支只回數字與 rc，門檻判定交給既有的 context_budget_guard 同構層。fail-closed：HTTP 非 200 / 欄位缺 / utilization 非數字 一律回「量不到」而不是回 0（本 repo「量不到 ≠ 量到零」既有紀律）。
```

#### `QTA-S1-02`｜[P0] 全 repo 對「額度水位」零消費者：三套現行機制量的全是 context 水位，沒有一個在量額度

- **檔案:行**：D:\CursorProject\AISDCL_Agent\.claude\hooks\context_budget_guard.py:194、D:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\utils\token_tracker.py:83
- **成本**：medium

**為何要緊（逐字）**：這解釋了為什麼 R79/R80 連續兩輪撞額度而所有守衛全數放行、也解釋了記憶檔那句「續航救 session、死的卻是扇出」。掌舵者訴求 b 的 80%/95% 兩道閘，**今天在 repo 裡結構上不可能實作**，因為沒有任何一個量測面看得到那個百分比。這不是門檻調錯，是整個量測面缺一條軸：現有的是「這一次請求塞多滿」，缺的是「這個計費週期燒掉多少」。

**當回合實測證據（逐字保全）**：

```text
Grep 全 repo（排除 AISDLC_SDD_v0.* 凍結面）pattern=`oauth/usage|utilization|five_hour|seven_day|rate_limit_event|used_percentage|statusLine|rate_limits` → **Found 2 files**：`tools\tests\test_context_budget_guard.py`、`AutoClaude\docker-compose.llm.yml`。再對前者取內容：
  854: def test_the_real_incident_is_sixteen_minutes_not_five_hours
  891: def test_five_hours_is_not_a_valid_substitute
＝兩筆都只是測試方法名裡的英文字，**沒有一筆是真的在讀額度欄位** ⇒ production 消費者數為 0。
三套現行機制的分母逐字：
 · context_budget_guard.py:194-195 `USAGE_FIELDS = ("input_tokens","cache_creation_input_tokens","cache_read_input_tokens")`、:307 `CONSERVATIVE_WINDOW = 200_000`、:310 `WIDE_WINDOW = 1_000_000` ⇒ 分母是 **context window**。
 · token_tracker.py:83-87 `_CONTEXT_USAGE_KEYS`、:118-123 `window = max(modelUsage[*].contextWindow)` ⇒ 分母是 **context window**。
 · sdk_executor_adapter.py:243/283 `usage = await _maybe_await(client.get_context_usage())`、`pct = usage.get("percentage")`，:248-249 取 `autoCompactThreshold`／`maxTokens` ⇒ 分母仍是 **context window**。
而 hook 自己的 docstring 也承認這件事（context_budget_guard.py:437-439 逐字）：「context 水位＝單次請求的輸入長度（分母是 window）；額度＝計費週期內的用量上限（分母是方案，harness 不告訴你）… 額度耗盡當下本 session 的水位只有 ~20%，block_verdict 的四道放行條件會全數放行」。
```

**建議修法（逐字）**：

```text
把水位明確拆成**兩軸並存**、各自有自己的門檻與動作，且訊息一律標示是哪一把尺（沿用既有 MEASURE_LABEL 作法，避免「同一份 repo 對同一個數字兩種說法」）：軸一 context（沿用現行 75/90，動作＝compact／停止展開）；軸二 quota（新增 80/95，動作＝少派 agent／停止並寫任務書）。兩軸**不得共用閂鎖、不得互相替代**——這正是 context_budget_guard.py:437 那段 WHY 已經寫下但還沒有人實作的東西。
```

#### `QTA-S1-03`｜[P0] reset 時刻不必再從錯誤訊息猜：endpoint 直接給精確 ISO 時刻，整條 parse_reset_at 觀測鏈可降級為 fallback

- **檔案:行**：D:\CursorProject\AISDCL_Agent\.claude\hooks\context_budget_guard.py:464、D:\CursorProject\AISDCL_Agent\tools\probe\reset_window_distribution.py:1
- **成本**：medium

**為何要緊（逐字）**：CLAUDE.md 現行結論「reset 只能觀測不能算」對『從錯誤訊息回推』這條路是對的，但它被當成了**通則**，於是整輪投資都押在「解析 `resets 9am` 字面 + 猜時區 + 拒絕武裝」這條又脆又貴的路上（R80 還為此被 act 抓到兩個時區翻面的紅）。權威通道存在時，那些問題整組消失：不必解字面、不必猜時區（值自帶 offset）、不必「解不出就拒絕武裝」。更關鍵的是它**在撞線之前就拿得到**——現行鏈條只有撞線後才有訊息可解，而那正是沒有人還在跑指令的時刻。

**當回合實測證據（逐字保全）**：

```text
實測 endpoint 回傳（同 S1-01 那一次 HTTP 200）：
  five_hour.resets_at = "2026-08-08T13:39:59.297723+00:00"（＝本機 2026-08-08T21:39:59+08:00）
  seven_day.resets_at = "2026-08-14T21:59:59.297788+00:00"
當回合本機時間：`now = 2026-08-08T21:19:48.370408+08:00` ⇒ 5 小時視窗**還有 20 分鐘**就 reset，且是秒級精確值。
對照現行實作 context_budget_guard.py:468 逐字：`_RESET_RE = re.compile(r"resets\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.IGNORECASE)`，其上方 :464-467 的 WHY 逐字寫「reset 時刻是滾動視窗、錨在該區塊第一次用量，只能**觀測**不能算」。
另從 stream-json 實測拿到 epoch 形態：`"resetsAt":1786744800` → 2026-08-15T06:00:00+08:00（與 REST 的 seven_day 值一致，僅整點捨入）。
```

**建議修法（逐字）**：

```text
reset 時刻的優先序改為：① endpoint 的 `resets_at`（權威、秒級、撞線前就有）→ ② 逐字稿訊息的 parse_reset_at（保留為離線／無網路 fallback）→ ③ 拒絕武裝（維持不變，禁止退回固定 5 小時）。`reset_source` 新增一個 `endpoint-authoritative` 值並列入 relay_problems 的白名單（session_resume_planner.py:476 那組），與現有 transcript-verbatim 並存。reset_window_distribution.py 保留為歷史語料分析工具，但不再是排程時刻的來源。
```

#### `QTA-S1-04`｜[P1] 同一個 bucket 在兩條通道給的單位不同：event 給 0.3（分數）、REST 給 30.0（百分比），混用會差 100 倍

- **檔案:行**：N/A（跨通道；claude.exe v2.1.223）
- **成本**：small

**為何要緊（逐字）**：這正是本 repo 反覆踩到的形態（R79「量測器指標可能符號相反」的同型，只是這次是**倍率**不是符號）。0.3 拿去比 80 永遠不會觸發 ⇒ 閘門恆綠、看起來完全正常；30.0 拿去比 0.8 則永遠觸發 ⇒ 閘門恆紅。兩個方向都會在「機制蓋好、rc 是 0」的外觀下失效，而且沒有任何東西會轉紅。既然三條通道未來可能都要接（TUI 走 statusLine、headless 走 event、排程走 REST），單位正規化必須是**入口就做掉**的事。

**當回合實測證據（逐字保全）**：

```text
同一台機器、同一分鐘（21:19 +08:00）的兩筆實測：
（A）headless stream-json 逐字：
  {"type":"rate_limit_event","rate_limit_info":{"status":"allowed_warning","resetsAt":1786744800,"rateLimitType":"seven_day","utilization":0.3,"isUsingOverage":false},...}
（B）REST /api/oauth/usage 逐字：
  "seven_day":{"utilization":30.0,"resets_at":"2026-08-14T21:59:59.297788+00:00",...}
同一個 seven_day bucket：(A) 0.3、(B) 30.0 ⇒ (A) 是分數 0..1、(B) 是百分比 0..100。
第三種寫法同時存在於 claude.exe 內嵌的 statusLine schema（offset 255872215 逐字）：`"five_hour": { "used_percentage": number, // Percentage of limit used (0-100), "resets_at": number // Unix epoch seconds }` ⇒ 欄位名也不同（used_percentage vs utilization）。
時間格式同樣三種：epoch 秒（event）／ISO-8601 帶 offset（REST）／epoch 秒（statusLine）。
```

**建議修法（逐字）**：

```text
取數層一律正規化成單一內部表示（建議 0..100 的 float，與 statusLine 的 used_percentage 對齊），並在每個 adapter 的入口寫死該通道的單位；再補一條**紅綠自證**的判準：注入 (A) 形態的 0.3 與 (B) 形態的 30.0，兩者必須產出相同的內部值，任一 adapter 改壞就轉紅。時間一律轉成 aware datetime（沿用 R80 已落地的「不得持久化 naive 本地時間戳」判準）。
```

#### `QTA-S1-05`｜[P1] headless SDK 通道結構上不可靠：rate_limit_event 只在跨警戒門檻時帶 utilization，且本次完全沒吐 five_hour

- **檔案:行**：N/A（claude -p --output-format stream-json；claude.exe v2.1.223）
- **成本**：small

**為何要緊（逐字）**：AutoClaude 是 headless 消費者，這條看起來最順的路（跟著既有 SDK 訊息流走）**恰好是三條裡最不可靠的那一條**：它只在「已經接近上限」時才吐數字，而 80% 預警要的正是「還沒接近時也要知道」；更糟的是它這次漏掉的偏偏是水位最高的那個 bucket。照這條路做出來的監控會在低用量時靜默、在關鍵 bucket 上失明，而外觀與「一切正常」相同。上游已把改善請求關掉（not planned）⇒ 不能等它。

**當回合實測證據（逐字保全）**：

```text
當回合真跑：`claude -p "ok" --model haiku --output-format stream-json --verbose` → **RC=0**、LEN=15146。旗標比對逐字輸出：
  HAS_rate_limits: False
  HAS_five_hour: False
  HAS_rate_limit_event: True
整份輸出裡與額度有關的**只有一筆**，逐字：
  {"type":"rate_limit_event","rate_limit_info":{"status":"allowed_warning",...,"rateLimitType":"seven_day","utilization":0.3,...}}
＝只有 seven_day、沒有 five_hour；而同一刻 REST 顯示 five_hour 已 44%（比 seven_day 的 30% 更高、更接近閘門）。
二進位掃描（claude.exe，280,233,632 bytes）：`rate_limits_snapshot` count=**0**、`SDKRateLimitsSnapshot` count=**0** ⇒ 網路搜尋提到的 SDKRateLimitsSnapshotMessage **在本機這一版不存在**。
上游 issue #50518「expose per-bucket rate-limit utilization to headless SDK consumers」狀態＝**Closed as not planned（stale）**，其描述與本機實測一致：utilization 只在跨門檻時帶、per-bucket 資料只透過 TUI statusLine 出去、headless 拿不到、hooks 也拿不到。
```

**建議修法（逐字）**：

```text
**不要**把 rate_limit_event 當主要取數管道，只把它當「免費的順風訊號」（有就用、沒有不慌），主管道走 S1-01 的 REST。若一定要用它，判準必須寫成「缺 utilization ＝量不到」而非「＝低用量」——後者正是把 fail-open 裝進去。
```

#### `QTA-S1-06`｜[P1] statusLine 通道欄位最齊（含 context% 與 quota% 兩軸皆 server 預算好），但 TUI-only，且本機根本沒設定

- **檔案:行**：C:\Users\wuwei\.claude\settings.json:1
- **成本**：small

**為何要緊（逐字）**：這是唯一一條**同時**給 context 水位與額度水位、且兩者都由 server 預先算好百分比的通道——正好是掌舵者要的兩軸。它的價值不只是顯示：statusLine 腳本每次 render 都會被餵一份 JSON，把它落到一支檔就等於得到一個「零額外成本、隨時可讀」的水位快取（連 S1-01 那次 HTTP 呼叫都省了）。但它**只在互動 TUI 生效**，所以只能當人在看時的那一半，不能當無人看管那一半的地板；兩者要分清楚，否則會蓋出一個「有人看著時很準、沒人看時全盲」的機制——那正是 R80 哨兵整晚失明的同型。

**當回合實測證據（逐字保全）**：

```text
claude.exe v2.1.223 內嵌的 statusLine JSON schema 逐字（offset 255870600~255872900）：
  "context_window": { "total_input_tokens": number, "total_output_tokens": number,
     "context_window_size": number, // Context window size for current model (e.g., 200000)
     "current_usage": {input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens} | null,
     "used_percentage": number | null,      // Pre-calculated: % of context used (0-100), null if no messages yet
     "remaining_percentage": number | null }
  "rate_limits": {   // Optional: Claude.ai subscription usage limits. Only present for subscribers after first API response.
     "five_hour": { "used_percentage": number, // Percentage of limit used (0-100)
                    "resets_at": number },     // Unix epoch seconds when this window resets
     "seven_day": { "used_percentage": number, "resets_at": number } }
本機現況實測：`USER_SETTINGS_HAS_STATUSLINE: False`，user settings 全文只有 model/effortLevel/tui/skipDangerousModePermissionPrompt/preferences，**沒有 statusLine 鍵**；repo 側 Grep `statusLine` 命中 0 個 production 檔（見 S1-02 的 Grep）。
限制來源（issue #50518 逐字）：statusLine 不在 headless SDK 模式下執行。
```

**建議修法（逐字）**：

```text
設一支 statusLine 腳本，職責兩件：①印給人看的一行（含 five_hour%／seven_day%／context%）；②把整份 JSON 原樣寫到一個固定路徑的快取檔（含時間戳）。之後任何本機消費者（hook／排程／AutoClaude）優先讀該快取，過期或不存在才回落到 S1-01 的 REST 呼叫。注意射程誠實劃界：快取只在互動 session 有人在跑時才會更新，**不得**把它當無人看管期間的權威源。
```

#### `QTA-S1-07`｜[P1] 「額度回來了沒」的探測成本可從約 32K tokens 降到零：現行探針花模型呼叫問的問題，endpoint 免費回答

- **檔案:行**：D:\CursorProject\AISDCL_Agent\tools\session_resume_planner.py:522
- **成本**：medium

**為何要緊（逐字）**：這把整條續航協定最貴、也最尷尬的一環拆掉了：現行設計為了知道「額度回來沒」，必須先花掉一塊剛回來的額度（註解自己承認「別把剛回來的額度先吃掉一塊」）。有了免費管道，MAX_PROBE_ATTEMPTS 這種「重試預算」的概念整個不需要存在，哨兵也不必再區分「零 token 巡邏」與「花錢探測」兩種醒法——每次醒來都可以直接讀到精確水位與精確 reset 時刻。

**當回合實測證據（逐字保全）**：

```text
現行實作 session_resume_planner.py:513-543，其 WHY 逐字：「探針必須真的花額度才有鑑別力…成本以 --model haiku ＋ 空 cwd 壓到最低——本檔實測一次 **31,847 tokens／$0.0176**」；實作是 `subprocess.run([claude, "-p", "ok", "--model", model, "--output-format", "json"], ...)`，再由 `guard.classify_limit(text)` 反推。
:281-284 的 MAX_PROBE_ATTEMPTS=5 註解逐字：「上界＝5 × 一次探測…≈ 16 萬 tokens，約等於主 session 醒來一次的 3/4」。
對照本輪實測：`GET /api/oauth/usage` → HTTP 200，回傳 `five_hour.utilization=44.0` 與 `resets_at`，**不是模型推論呼叫** ⇒ 不消耗 5 小時視窗的額度。
同檔 :518 的既有洞察逐字：「探測回答的是『額度回來了沒』，那件事**只能問伺服器**」——本輪找到的正是「問伺服器」的那個免費管道。
```

**建議修法（逐字）**：

```text
probe_quota() 的實作改為先打 endpoint：拿得到 utilization 就用它判定（`< 100 且 severity 正常` ⇒ 額度可用），拿不到（無網路／401／欄位缺）才回落現行的 claude -p 探針。回落路徑保留是必要的——endpoint 也會失效，而 fail-closed 的方向不變。MAX_PROBE_ATTEMPTS 保留給回落路徑。
```

#### `QTA-S1-08`｜[P2] OAuth token 4 小時到期：無人看管過夜的取數器會靜默失效，除非實作 refresh

- **檔案:行**：C:\Users\wuwei\.claude\.credentials.json:1
- **成本**：medium

**為何要緊（逐字）**：5 小時視窗 + 7 天視窗的等待都可能跨過 4 小時，而「無人看管時撐過 reset」正是訴求 d/e 的主場。互動 session 活著時 Claude Code 會自己 refresh 並回寫這支檔（讀檔即可跟上）；但撞額度後整個 session 死掉、排程器獨自醒來那條路上**沒有人在 refresh**，於是取數器會在最需要它的那一夜拿到 401。這與 R80 哨兵失明是同一個形狀：機制在、憑證過期、失效靜默。

**當回合實測證據（逐字保全）**：

```text
當回合實測憑證檔結構（值全部 redact，只印型別與長度）：
  claudeAiOauth: <object>
    accessToken: <str len=108>
    refreshToken: <str len=108>
    expiresAt: <int len=13>
    refreshTokenExpiresAt: <int len=13>
    scopes: ['user:file_upload','user:inference','user:mcp_servers','user:profile','user:sessions:claude_code']
    subscriptionType: team
    rateLimitTier: <str len=21>
  expiresAt -> 2026-08-09T01:19:39.306000+08:00
當回合 now = 2026-08-08T21:19:48+08:00 ⇒ **距到期約 4 小時**。
refresh 管道存在（claude.exe offset 87857500 逐字）：`refresh_token` … `/v1/oauth/token` … `oauth-2025-04-20` … `getToken`／`invalidate`／`refresh`／`backgroundRefresh`；另 offset 99547943 逐字：`firstPartyApi: refreshOAuth failed (...); proceeding with cached token`。
```

**建議修法（逐字）**：

```text
取數器每次呼叫前先比對 expiresAt：未過期就直接用；已過期（或收到 401）則以 refreshToken 打 POST /v1/oauth/token（grant_type=refresh_token）換新 token 並回寫檔案。若不想在本 repo 內處理 refresh token（那是安全面決策，值得單獨拍板），最低限度也要把「token 已過期」與「額度真的沒回來」兩種情況**在痕跡裡分開記**，否則排程器會把認證失敗誤判成額度未恢復而一直等下去。禁止把 token 值寫進任何 log／任務書。
```

#### `QTA-S1-09`｜[P1] R80 那道「四個分母都湊得出 78%」的謎題是偽命題：UI 的 78% 是 server 算的 percent，本來就不是任何 token 比值

- **檔案:行**：N/A（對照 CLAUDE.md 與 R80 交棒紀錄）
- **成本**：small

**為何要緊（逐字）**：R80 花了一輪想從「3,015 筆 usage 加總 ÷ 某個分母 = 78%」反解口徑，四個候選分母都湊得出來 ⇒ 當時的結論是「單一校準點解不開兩個未知數」。真正的原因不是校準點不夠，是**那個等式根本不成立**：78% 是伺服器用 unified 限額桶算好丟回來的 utilization，跟本機逐字稿的 token 加總沒有函數關係（它還跨 claude.ai／Desktop／CLI 共用同一個池）。繼續做多點校準會是純浪費——這是「問題問錯了」而不是「量得不夠準」。

**當回合實測證據（逐字保全）**：

```text
實測 endpoint 的 limits 陣列逐字：`{"kind":"session","group":"session","percent":44,"severity":"normal","resets_at":"2026-08-08T13:39:59.297723+00:00","scope":null,"is_active":true}`——`kind:"session"` 這一筆的 `percent` 就是 UI 上「Current session」那一格；`{"kind":"weekly_all",...,"percent":30,...}` 對應「Current week」。
claude.exe 內的 UI 標題字面（offset 127028421 逐字）：`Current session` … `Current week (all models)`，與該 limits 陣列同一個資料源（offset 260976961 的投影函式 `c$t(n.limits, ...)` 逐字產生 `Current week (${n.scope?.model?.display_name})`）。
該 percent 的上游是 header 家族（offset 254898600 逐字）：`for(let[r,n]of[["five_hour","5h"],["seven_day","7d"],["seven_day_overage_included","7d_oi"],["overage","overage"]]){let o=e.get(`anthropic-ratelimit-unified-${n}-utilization`),i=e.get(`anthropic-ratelimit-unified-${n}-reset`)`。
對照組：`anthropic-ratelimit-tokens-remaining` 在整支 claude.exe 內 count=**0** ⇒ 訂閱模式**完全不走**傳統的每分鐘 token 桶 header。
```

**建議修法（逐字）**：

```text
停止一切以 token 加總反推額度分母的工作（含多點校準的構想），改為直接消費 server 的 percent。CLAUDE.md 該段的結論要改寫：不是「解不開」，是「不需要解——有權威來源」。同時記下這條可重用的判準：**當某個數字有權威來源時，反推它的口徑是零價值的工作**。
```

#### `QTA-S1-10`｜[P2] 訴求 e 的「每 50 分鐘喚醒一次」不需要：有精確 resets_at 就只排一次；現行 15 分鐘巡邏亦可降頻

- **檔案:行**：D:\CursorProject\AISDCL_Agent\tools\session_resume_planner.py:306
- **成本**：small

**為何要緊（逐字）**：掌舵者問的「是否每 50 分鐘喚醒一次」，前提是「不知道什麼時候會 reset，所以只能一直醒來看」。這個前提在 S1-01/S1-03 之後不成立了：知道確切時刻就排在那個時刻（加安全邊際），中間完全不必醒。而 ScheduleWakeup 那條路（1 小時上限、要接力、終端不能關、且沒有憑證）本來就不是 token reset 的方案——現行 repo 已經改用 schtasks 是對的，本輪只是讓它的觸發時刻從「猜」變成「查」。

**當回合實測證據（逐字保全）**：

```text
現行常數 session_resume_planner.py:306 `SENTINEL_INTERVAL_SECONDS = 900`，其 :292-305 WHY 逐字：「間隔決定『reset 之後最壞多久才會有人動作』…為什麼可以取這麼密：每次巡邏是**讀檔，零 token**」；另 CLAUDE.md 工具選型表逐字記載 ScheduleWakeup「單次上限 1 小時…**沒有任何憑證**——不寫磁碟、沒有可查詢的登錄、拿不到 NextRunTime」。
本輪實測拿到的精確值：`five_hour.resets_at = 2026-08-08T13:39:59.297723+00:00`、`seven_day.resets_at = 2026-08-14T21:59:59.297788+00:00`，皆為秒級 ISO 且帶 offset。
離線排程既有取證管道（CLAUDE.md 逐字）：`Get-ScheduledTask -TaskName '<名稱>' | Get-ScheduledTaskInfo | Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime`，憑證是 NextRunTime 這個值而非 rc。
```

**建議修法（逐字）**：

```text
維持 schtasks 單次排程的形狀（含 WakeToRun／StartWhenAvailable／DisallowStartIfOnBatteries=false／StopIfGoingOnBatteries=false 四項與 NextRunTime 取證），只把觸發時刻的來源換成 endpoint 的 resets_at + RESET_SKEW_SECONDS。巡邏間隔可以放寬（因為不再靠巡邏去「發現」撞線），但**不建議在本輪動它**——那是取捨不是純改善，且現行 900 秒的成本是零。
```

#### `QTA-S1-11`｜[P2] 額度是跨產品共享的帳號級池，且本帳號是 team + 有 per-model 的 weekly_scoped 桶：單看一個數字會誤判

- **檔案:行**：N/A（endpoint 回傳 + 憑證檔）
- **成本**：medium

**為何要緊（逐字）**：記憶檔已記載兩條相關教訓——「週額度才是限制因素」與「monthly spend limit 沒有 reset 可等，排程是錯的動作」。這次的資料把兩者統一了：`spend`／`extra_usage.spend_limit_reached` 是與 five_hour／seven_day **平行的另一條軸**，它撞線時等待無效。只盯 five_hour 會在週額度或 spend 上限撞線時完全失明；而只盯 seven_day 會錯過 5 小時視窗（本次 44% > 30%，是更緊的那一個）。另外「跨 claude.ai／Desktop／CLI 共用同一池」代表本機量測本質上不完整——再一次說明必須取 server 的數，不能自己算。

**當回合實測證據（逐字保全）**：

```text
實測 endpoint 回傳的 limits 陣列有**三種 kind**：`session`（percent 44、is_active true）、`weekly_all`（percent 30、is_active false）、`weekly_scoped`（percent 0、scope.model.display_name="Fable"、is_active false）；另有具名的 `seven_day_opus`／`seven_day_sonnet`／`seven_day_oauth_apps` 欄位（本次皆 null）。
`spend` 物件：`{"percent":0,"severity":"normal","enabled":false,...}`；`extra_usage`：`{"is_enabled":false,"user_disabled":true,"spend_limit_reached":false,...}`。
憑證檔實測：`subscriptionType: team`、另有 `rateLimitTier`（值未印）。
claude.exe 內的桶清單逐字（offset 260976961）：`bsb=["five_hour","seven_day","seven_day_oauth_apps","seven_day_opus","seven_day_sonnet","cinder_cove","extra_usage","limits"]`。
```

**建議修法（逐字）**：

```text
門檻判定取**所有 is_active 桶的最大 utilization**（而非只看 five_hour），並把 `spend`／`extra_usage.spend_limit_reached` 走**獨立分支**：它撞線時的動作是「叫人去提額」而不是「排程等 reset」——這與現行 guard.LIMIT_SPEND 的既有判定（session_resume_planner.py:553-556 `月度支出上限——等待無效，只有人去提額才會回來`）語意一致，只是資料來源從錯誤字串換成結構化欄位，可靠得多。
```

#### `QTA-S1-12`｜[P2] AutoClaude 的 Token Guard 三槓桿全部掛在 context window 上，且 SDK 的 get_context_usage 結構上不回額度

- **檔案:行**：D:\CursorProject\AISDCL_Agent\AutoClaude\autoclaude\infra\adapters\sdk_executor_adapter.py:243
- **成本**：large

**為何要緊（逐字）**：掌舵者訴求裡 AutoClaude 是「指揮官」，而它現有的 80%（compact）與 halt 兩道門看起來剛好對得上訴求 b 的 80%/95%——**但它們量的是 context 不是額度**，直接沿用會製造一個名字對、語意錯的閘門，比沒有更危險（會讓人以為額度已經有人守了）。這與 S1-02 是同一個結構性缺口在 AutoClaude 這一側的投影。另外 `auto_resume`／`resume_delay_minutes`／`max_auto_resumes` 這組續跑槓桿已經存在，正好是額度軸落地時可以複用的骨架——缺的只是一個真實的額度訊號源。

**當回合實測證據（逐字保全）**：

```text
sdk_executor_adapter.py 實測命中逐字：
  :11  `get_context_usage().percentage→ token_pct {"pct": ...}`
  :17  `act-first（W-68-1）：執行期以 SDK get_context_usage() 的 maxTokens/autoCompactThreshold`
  :243 `usage = await _maybe_await(client.get_context_usage())`
  :248-249 `threshold = usage.get("autoCompactThreshold")` / `max_tokens = usage.get("maxTokens")`
  :283 `pct = usage.get("percentage") if isinstance(usage, dict) else None`
  :295-297 `SDK get_context_usage 無 percentage 欄，token%% 訊號源未產出（DEF-81-001 SDK 支）；usage keys=%s`
設定面 config.py:139 `compact_threshold_pct: float = Field(default=80.0, ...)`、:133 `halt_threshold_pct 必須 > compact_threshold_pct`；config_resolver.py:39-43 三槓桿 `compact_threshold_pct`／`halt_threshold_pct`／`auto_resume`／`resume_delay_minutes`／`max_auto_resumes`。
PTY 支的回退 token_tracker.py:90-126 `context_pct_from_claude_json`，:118-123 `window = max(modelUsage[*].contextWindow)`，其 docstring 逐字承認：「此為**近似** context%——claude JSON **無**直接的 percentage 欄」。
本 venv 實測未安裝 claude-agent-sdk（site-packages 內 `*claude*` 目錄只有 `autoclaude-0.1.0.dist-info`）。
```

**建議修法（逐字）**：

```text
在 AutoClaude 側新增一條與 context 平行的 quota 訊號源（消費 S1-01 的取數器），並**另立**門檻欄位（例如 quota_throttle_pct=80／quota_halt_pct=95），不要複用 compact_threshold_pct／halt_threshold_pct——同名不同義是本 repo 反覆判過的形態。80% 的動作對應訴求 b 的「少派 Agent」（降扇出並行度），95% 對應「停止並寫任務書」，後者可直接接上既有的 auto_resume／resume_delay_minutes 骨架。這一條**必須等 S1-01 的取數器落地後**才動，否則又是一個沒有電的機制。
```

### §2.3 本路 `verified_commands`（逐字保全）

```text
全部在 Windows 11 / PowerShell 工具（pwsh 7.x）下執行，repo 根 D:\CursorProject\AISDCL_Agent。

1) $v = & claude --version 2>&1; ... Get-ChildItem C:\Users\wuwei\.claude\projects -Directory
   → VERSION: 2.1.223 (Claude Code) / PATH: C:\Users\wuwei\.local\bin\claude.exe（rc 未單獨取，指令成功回傳）

2) Grep 工具 pattern=`five_hour|used_percentage|seven_day` path=C:\Users\wuwei\.claude\projects\d--CursorProject-AISDCL-Agent output_mode=count
   → Found 31 total occurrences across 20 files

3) $hits = Select-String -Path C:\Users\wuwei\.local\bin\claude.exe -Pattern 'five_hour','used_percentage','seven_day','rate_limits' -AllMatches -Encoding ascii
   → SIZE: 280233632  MTIME: 08/07/2026 00:51:11 / BINARY_HITS: 37

4) & 'D:\...\.venv\Scripts\python.exe' <scratchpad>\probe_binary.py
   → 取出 five_hour(43)/used_percentage(11)/seven_day(110)/rate_limits(20)/resets_at(27) 各命中點的前後文

5) & 'D:\...\.venv\Scripts\python.exe' <scratchpad>\probe2.py
   → 取出 statusLine 內嵌 schema 全文（offset 255870600~255872900）、utilization header 迴圈（254898600）、fetchUtilization 實作（254890300）
   → 計數：/api/oauth/usage=4、anthropic-ratelimit-unified=69、anthropic-ratelimit-tokens-remaining=0、claude_code.token.usage=2、OTEL_METRICS_EXPORTER=14、rate_limits_available=3

6) & 'D:\...\.venv\Scripts\python.exe' <scratchpad>\probe3.py
   → rate_limits_snapshot=0、SDKRateLimitsSnapshot=0、rate_limit_event=10、rateLimitType=42、subscription_type=8
   → 取出 Zod schema（272843760）與 rate_limits 投影實作（260976961）

7) $out = & claude -p "ok" --model haiku --output-format stream-json --verbose 2>&1; $rc = $LASTEXITCODE
   → RC=0 / LEN=15146 / HAS_rate_limits: False / HAS_five_hour: False / HAS_rate_limit_event: True
   （注意：實際 cwd 是 repo 根，故該次呼叫有載入本 repo 全部 hooks 與 CLAUDE.md）

8) Select-String -Path <scratchpad>\emptycwd\stream.json -Pattern 'rate_limit' -AllMatches
   → {"type":"rate_limit_event","rate_limit_info":{"status":"allowed_warning","resetsAt":1786744800,"rateLimitType":"seven_day","utilization":0.3,"isUsingOverage":false},...}

9) & 'D:\...\.venv\Scripts\python.exe' <scratchpad>\r81_quota_agent_probe_uniq.py
   → epoch 1786744800 -> 2026-08-15T06:00:00+08:00；now = 2026-08-08T21:19:48+08:00
   → 憑證檔鍵結構（值 redact）：accessToken/refreshToken/expiresAt/refreshTokenExpiresAt/scopes/subscriptionType=team/rateLimitTier；expiresAt -> 2026-08-09T01:19:39+08:00
   → GET https://api.anthropic.com/api/oauth/usage -> HTTP 200，body 含 five_hour.utilization=44.0 / seven_day.utilization=30.0 / limits[] / spend / extra_usage
   → 回應**沒有**任何 ratelimit 相關 header（我逐一過濾 header 名含 ratelimit/unified，印出為空）

10) & 'D:\...\.venv\Scripts\python.exe' <scratchpad>\r81_refresh_probe_uniq.py
   → oauth/token=19、/v1/oauth=14、refreshOAuth=24、grant_type=82；取出 /v1/oauth/token + refresh_token + backgroundRefresh 的前後文

11) Grep 工具 pattern=`oauth/usage|utilization|five_hour|seven_day|rate_limit_event|used_percentage|statusLine|rate_limits` path=repo 根 glob=`!**/AISDLC_SDD_v0.*/**`
   → Found 2 files（tools\tests\test_context_budget_guard.py、AutoClaude\docker-compose.llm.yml）
12) Grep 同 pattern 對 test_context_budget_guard.py 取內容
   → 只有 :854 / :891 兩個測試方法名含 "five_hours" 英文字 ⇒ 零 production 消費者

13) Read 工具：tools/session_resume_planner.py（1-739 行）、.claude/hooks/context_budget_guard.py（1-839 行）、tools/probe/reset_window_distribution.py（全 183 行）、AutoClaude/autoclaude/utils/token_tracker.py（全 184 行）
14) Grep 工具：AutoClaude/autoclaude 內 token_guard/compact/context_window 等；AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py 內 usage/max_tokens/rate_limit/percent
15) Get-ChildItem .venv\Lib\site-packages -Filter '*claude*' → 只有 autoclaude-0.1.0.dist-info（無 claude-agent-sdk）
16) Get-Content C:\Users\wuwei\.claude\settings.json → USER_SETTINGS_HAS_STATUSLINE: False

WebSearch/WebFetch：Claude Code SDK usage API、statusLine rate_limits、Agent SDK python 參考頁、issue #50518（Closed as not planned）、5 小時/週視窗官方說明、其他 Agent 框架節流設計。
```

### §2.4 本路 `honest_gaps`（逐字保全）

```text
誠實劃界——以下**沒有**實測，不得當成已驗證：

1. **statusLine 通道完全沒有實跑過**。S1-06 的欄位表是從 claude.exe 內嵌的 schema 文字讀出來的（那是它自己的說明文件，不是我觀測到的 payload）。要驗必須寫一支 statusLine 腳本並改 settings.json，本階段唯讀故未做。所以「statusLine 真的會送出 rate_limits」目前是**該版二進位的自述**，不是實測。

2. **/api/oauth/usage 只成功呼叫過一次，且只在額度充裕（five_hour 44%）時**。未驗證的有：逼近 100% 時 severity／欄位會不會變形；撞線後（HTTP 429 或 session 已死）它還回不回得動——而「撞線後還能不能取數」正是續航鏈最關鍵的那一格。也沒做連續呼叫的壓力測試，**不知道這個端點自己有沒有速率限制**。

3. **anthropic-beta / User-Agent header 是否必要，沒有做對照組**。我一次就帶齊了 `anthropic-beta: oauth-2025-04-20` 與 claude-cli 的 User-Agent，所以不知道拿掉會不會照樣 200。若之後有人只抄一半而失敗，成因會落在這裡。

4. **token refresh 流程完全沒跑過**。S1-08 的 `/v1/oauth/token` + `grant_type=refresh_token` 是從二進位字串讀到的端點與參數名，**沒有實際換過一次 token**，也沒驗證回寫檔案的格式。這條是 P2 但它決定了無人看管過夜能不能成立。

5. **claude-agent-sdk 未安裝在本 venv**，所以 `SDKRateLimitsSnapshotMessage`／`RateLimitInfo` 這兩個型別本機無從驗證。網路搜尋說它存在、issue #50518 說沒有、本機 claude.exe 掃 `rate_limits_snapshot` 得 0 ——**三個來源互相矛盾**，我以本機二進位為準（因為那是真正會跑的東西），但這代表「別的機器／別的 SDK 版本可能有」這個可能性我沒排除。另外我也**沒有確認 AutoClaude production 到底走 SDK 支還是 PTY 支**，只讀了 adapter 原始碼。

6. **OTEL 通道沒查**。`OTEL_METRICS_EXPORTER` 在二進位命中 14 次、`claude_code.token.usage` 命中 2 次，這可能是第四條取數管道（而且可能是唯一「不必自己輪詢」的推送式管道），本輪完全沒展開。這是我認為最值得下一步補的空白。

7. **`rate_limit_event` 只觀測到一筆樣本**。「utilization 只在跨警戒門檻時出現」這句話我是引 issue #50518 的說法 + 本次 status 剛好是 `allowed_warning` 來佐證的，**沒有在低用量狀態下跑對照組**去證明它真的會消失。方向我有信心，但這一條的證據強度低於其他各條。

8. **單位換算（0.3 vs 30.0）是兩次不同呼叫的比對**，中間相隔數十秒。雖然同一個 bucket 差 100 倍不可能是真實變動，但嚴格說我沒有在同一瞬間同時取兩個通道。

9. 訴求 f（前沿 Agent 框架怎麼做）只做了一次概略搜尋，得到的是「LangGraph 有 checkpoint 續跑、OpenAI 側普遍是指數退避加抖動」這種層級的答案，**沒有逐一讀它們的原始碼或官方文件**，不足以支撐設計決策，只能當背景。

10. 本輪跑了一次 `claude -p`（第 7 項），它在 repo 根執行 ⇒ 載入了全部 hooks，**可能因此多武裝了一支 AutoSDD_Sentinel_* 排程工作**（SessionStart hook 會無條件武裝，見 session_resume_planner.py:643-651 的已知設計問題）。我沒有去查證也沒有清理。
```

## §3 ADR-XPLAT-005 與兩位獨立審查者

ADR 全文另居 `docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md`；
本節只留核心決策、實作步驟、開放問題，以及 SA／SD 兩份 verdict 的逐筆 blocking。

### §3.1 ADR-XPLAT-005 的核心決策（17 項，逐字保全）

**D01**

```text
訴求 a 的答案是「本 repo 不再擁有分母這個概念」——GET /api/oauth/usage 由 server 依帳號方案算好 utilization 回傳百分比，換帳號換機器零常數要改。本輪 Architect 獨立複驗 HTTP 200（21:29 +08:00，five_hour=56.0 / seven_day=32.0），且做了調研沒做的 header 對照組：只帶 Authorization + Content-Type 也回 200 ⇒ anthropic-beta 與 claude-cli User-Agent 都不是必要條件（關掉調研 honest_gap #3）。
```

**D02**

```text
明文停止「從 token 加總反推額度分母 + 多點校準」的一切工作。理由不是還沒做，是等式根本不成立：池跨 claude.ai/Desktop/CLI 共享、訂閱模式不走 token 桶（anthropic-ratelimit-tokens-remaining count=0）、且本輪實測 10 分鐘內水位漲 12pp（44.0→56.0）而本 session usage 解釋不了。新判準入 CLAUDE.md：當某個數字有權威來源時，反推它的口徑是零價值的工作。
```

**D03**

```text
拿不到權威值時的 fallback 是四級階梯，最後一級是「不知道」而不是一個數字：endpoint → statusLine 快取 → 逐字稿撞線偵測（只給下界：撞了＝100%）→ 量不到。L4 刻意不填數字，且刻意「不節流」——斷網時自動降併發會讓網路壞掉與額度滿了外觀完全相同且靜默，同既有 may_block(source)「分母是猜的就不擋」判例。逐字稿那層地板永遠在，meter 全死時仍抓得到真撞線。
```

> 🔴 **D03 已被複審推翻一半，本區塊是「當初決定了什麼」的史料，不是現行說法。** 上面那段的**級數**與**最後一句**都與落地實作不符：實作只有 **2 級**（L1 endpoint、L4 量不到）——L2（statusLine 快取）**零 reader**、L3（逐字稿撞線偵測）在 `quota_gate()` 裡**零呼叫**，而最後那句正是拿 L3 去替 L4 不節流辯護。淨效果是**「量不到」＝對任意規模的扇出全數放行**，而「量不到」是常態（快取一過期就是它）：探針實測快取過期 600s／額度 99% 時，42 次 `Agent` 派發放行 42、擋下 0。
>
> **現行說法（R81 收斂後）＝ADR-XPLAT-005 §2.1 的落地訂正表**：L1 改成在扇出路徑上**同步**量一次（有界逾時 4 秒、每 TTL 至多一次）；L3 真的接上（`quota_floor_reading()`）；L2 這一級**不存在**，因此不再被算進階梯——「四級」這個數字本身就是當初那半句假話的一部分。L4 的**方向**（不節流）維持不變，理由未被推翻。

**D04**

```text
額度不是兩條線是三條，這是本 ADR 最重要的新發現。ADR-004 只分 session 與 spend；權威 endpoint 讓中間那條浮出來：weekly_all/seven_day 的 reset 在最長 7 天後（本輪實測距當下 6 天）⇒「等」幾乎沒有意義。95% 的動作必須先問是哪一條線，否則會排一支七天後才響的 schtasks 而痕跡全綠（R59 事故同形）。
```

**D05**

```text
單位正規化必須在入口做掉，且它是本 ADR 唯一能抓到「差 100 倍」的地方。同一個量有四種寫法，其中兩種在同一份 payload 裡（本輪新發現：five_hour.utilization 是 float 56.0、limits[].percent 是 int 56），另有 stream-json 的 0..1 分數與 statusLine 的 used_percentage。0.3 比 80 恆綠、30.0 比 0.8 恆紅，兩個方向都在 rc=0 的外觀下失效。
```

**D06**

```text
禁止寫死桶名清單。本輪實測 live payload 有 17 個頂層鍵含代號桶（amber_ladder / iguana_necktie / nimbus_quill / tangelo / omelette_promotional / seven_day_cowork / seven_day_omelette / cinder_cove），而 claude.exe 內嵌名單只有 8 個 ⇒ schema 正在長，寫死名單的失明是靜默的。判定只消費 limits[] 取 max(percent)，且刻意不用 is_active 篩（它的語意未知：session 56% 為 True、weekly_all 32% 為 False）。
```

**D07**

```text
80% 那道「真的降併發」的機械物已經在射程內，不必新增註冊面：settings.json:128 的 PreToolUse matcher 已是 Task|WebFetch|WebSearch|Agent|Workflow（本輪實測），扇出的每一次派發今天就會經過那支 hook。判定讀快取檔（零網路）+ 扇出帳算 in-flight，超過 cap 就 exit 2 ⇒ 那次工具呼叫不會發生。cap=2 是挑的、上界是量出來的（R80 撞線當下扇出 42/55/1），機械物守方向不守數值：cap 隨 quota 單調不增、q≥95 必須恰為 0。
```

**D08**

```text
本輪找到一個會讓節流器永久失效的具體缺口：PostToolUse 的 matcher（settings.json:217）是 Read|Task|Grep|Glob|WebFetch|WebSearch|Bash|PowerShell，沒有 Agent 與 Workflow ⇒ Pre/Post 配對數 in-flight 時計數器只增不減、永久過度節流，而外觀像「額度一直很高」。機械物 M5 把 Post matcher 釘成 Pre matcher 的超集，分母現查 settings.json 不寫死。
```

**D09**

```text
可續跑單位由 session 降到 workflow run，且帳與狀態要分開才不違反 ADR-004 §2.4：扇出帳是 append-only 的 %TEMP%\autosdd_fanout_<sid>.jsonl（與既有 autosdd_resume_log_*.jsonl 同家族），續航狀態仍只有 relay JSON 一個家、只在 95% 閂鎖那一刻寫入 pending_runs 摘要。未完成 = dispatched − completed，與 80% 節流用同一個計數器（一份帳兩個消費者，不重複模組）。
```

**D10**

```text
Workflow 的 runId / resumeFromRunId 欄位名本 ADR 沒有驗過（唯讀階段不能真跑），所以 Step 0 第一個動作就是量它；量不到就退回只記 tool 名+描述+時間戳（仍足以人工重派），不准照猜的欄位名寫實作。
```

**D11**

```text
reset 時刻優先序改為 endpoint-authoritative → transcript-verbatim/probe-verbatim → 拒絕武裝。ADR-004 §2.1「只能觀測不能算」對「從錯誤訊息回推」仍成立，但它被當成通則，害整輪押在解字面+猜時區的脆路上（R80 為此被 act 抓到兩個時區翻面的紅）。權威值撞線前就拿得到，這才是關鍵。另：resets_at 跨呼叫有次秒級抖動（13:39:59.29 vs 13:40:00.81）⇒ 比較一律截到分鐘，禁字串相等比較。
```

**D12**

```text
「額度回來了沒」的探測成本從 31,847 tokens/次 降到零：先打 endpoint（不是模型推論呼叫），失敗才回落 claude -p 探針。回落路徑必須保留、MAX_PROBE_ATTEMPTS 留給它，fail-closed 方向不變。
```

**D13**

```text
訴求 e：不採用每 50 分鐘喚醒、巡邏維持 900 秒。ADR-004 §2.7 三個理由（50 分是 ScheduleWakeup delaySeconds clamp 外溢的假需求／放大死等且巡邏是零 token／ScheduleWakeup 每醒一次是 20.7 萬 token 的模型回合撐不過斷電）加本輪第四個：有了撞線前就拿得到的精確 resets_at，「一直醒來看好了沒」的理由消失。最重要的回答是——正確目標是根本不要撞到 100%，把「被動等一個未知長度的窗」換成「95% 主動停手、等一個查得到的時刻」。
```

**D14**

```text
新程式碼住哪有三個量出來的結構理由，不是偏好：①session_resume_planner.py 實測 749/750 只剩 1 行餘裕，塞不下；②不能放進 hook 主路徑（每次工具呼叫加網路延遲，且該檔記載過「hook 誤觸 deny 會把所有工具硬鎖死」的 P0）；③AutoClaude 需要同一把尺但不能 import 那兩者（ADR-004 §4 禁止套件依賴 harness 內臟）。⇒ 取數層新開 tools/lib/quota_meter.py（≤400），判讀進 context_budget_guard.py（本輪實測它不在任何 LOC 預算面內），動作留在既有三個家，AutoClaude 透過檔案契約消費。
```

**D15**

```text
AutoClaude 側絕不複用 compact_threshold_pct(80)/halt_threshold_pct(90)，另立 quota_throttle_pct/quota_halt_pct。數字剛好接近才更危險——會讓人以為額度已經有人守了。且 AutoClaude 側不重複實作 subagent 節流：headless claude -p 完整跑本 repo 的 hooks（記憶已兩探針實證）⇒ 它驅動的 CLI 內部扇出會被同一支 hook 擋，一個機械物守兩個載體。95% 走既有 halt+checkpoint 骨架，只把恢復時刻由固定 resume_delay_minutes=30 換成 endpoint 的 resets_at。
```

**D16**

```text
訴求 f 的結構結論：業界主流的指數退避+抖動在本場景是錯的工具。那是 per-request 429 的解法（等一下再送就會過），本 repo 面對的是 per-account 週期額度（退避無效，只會燒光探測預算）。正確工具組是事前節流 + 等一個已知時刻 + 工作單位級續跑。誠實劃界：這是從本輪量測推得的，不是讀了那些框架原始碼得出的。
```

**D17**

```text
端點的 spend 欄位不取代既有 classify_limit()：本輪實測本帳號 spend.enabled=False，而 R80 逐字稿分類出 99 筆 quota_spend，兩者不一致且成因未解 ⇒ 兩條並存，矛盾時取較保守的一方。這是權宜不是設計。
```

### §3.2 實作步驟（9 個 step，逐字保全）

```text
[step]
Step 0（前置，不含任何本 ADR 的功能）：①收掉繼承的紅——tools/lib/hook_wiring.py 實測 407 > 400（+7），依既有紀律「先拆職責/抽共用模組」處理，不准調高門檻；②實測 Workflow 工具的 payload 到底有沒有 run 識別欄位、resumeFromRunId 的確切參數名——真跑一個最小 Workflow 並看 PreToolUse/PostToolUse 收到的 JSON；③清點並清理調研那次 claude -p 可能留下的多餘 AutoSDD_Sentinel_* 工作。三件事都做完才動 Step 1。

[files]
tools/lib/hook_wiring.py；（量測用）scratchpad 的一次性腳本；Get-ScheduledTask 查詢

[mechanism]
AutoClaude/tools/check_loc_budget.py 必須回 rc=0（今天是 rc=1）；Workflow 欄位的量測結果要落成一份具名證據（貼進 improving_105 或缺陷帳本具名證據檔），不得只留在對話裡

[risk]
hook_wiring.py 是 R80 剛落地的 hook 佈線唯一真相源，動它會牽動 8 個解析器與 check_hooks_liveness；拆錯會讓形態鎖 A~F 失去鑑別力。Workflow 若量不到 run 識別欄位，Step 5 的續跑要退回「只記 tool 名+描述+時間戳」——這是預期內的退路，不是失敗
```

```text
[step]
Step 1：新增 tools/lib/quota_meter.py（唯讀取數器 + 單位正規化 + 快取寫入）。讀 ~/.claude/.credentials.json 的 claudeAiOauth.accessToken → GET https://api.anthropic.com/api/oauth/usage → 正規化成 0..100 float、aware datetime → 寫快取檔（含 measured_at / source / denominator 說明欄）。只帶 Authorization + Content-Type（本輪對照組已證 anthropic-beta 與 User-Agent 非必要）。fail-closed：非 200 / 欄位缺 / 型別非數字 一律回「量不到」而不是 0。桶列舉只消費 limits[] 取 max(percent) 並記錄 kind，禁止寫死桶名。另提供 --json / --watch（--watch 是漂移率的重量入口，不另開探針檔）。token 值全程不得寫進任何輸出。

[files]
tools/lib/quota_meter.py（新，tier guardrail_lib ≤400）

[mechanism]
tools/tests/test_context_budget_guard.py::QuotaUnitNormalizationTest（四種形態必須產出相同內部值 + 反向自證）、::QuotaUnmeasurableTest（四種失效輸入都必須回 None 不是 0.0）、::QuotaBucketEnumerationTest（注入含未知代號桶的 payload 必須照樣算得出 max，且斷言原始碼裡沒有寫死的桶名 tuple）；LOC 由 check_loc_budget.py 的 guardrail_lib≤400 守

[risk]
①護欄層 raw-line 淨額為正 ⇒ 必須走 improving_104 §4 款(9) 登記手續（標 [非淨減法輪] + 指名逐檔清單的 .md），且該輪 Q2 一律判未達成——這是本 ADR 自己要承擔的帳，不可繞過。②憑證處理若寫錯會把 token 印進 log，這是安全事故；測試必須含「輸出裡不得出現 token 前綴」的斷言。③400 行放不下時的正解是拆職責，不是調高門檻
```

```text
[step]
Step 2：在 .claude/hooks/context_budget_guard.py 新增 quota 軸的純判讀（零網路、只讀快取檔）：quota_of(cache) → (pct, kind, stale_seconds, source)；quota_tier_of(pct) → normal/throttle/halt；fanout_cap(pct) → int|None。沿用既有 MEASURE_LABEL 紀律，訊息一律標示是哪一把尺（context 還是 quota），避免同一份 repo 對同一個數字兩種說法。快取超過 TTL(180s) 時 fire-and-forget 起 detached 刷新器（沿用既有 quiet_python() + NO_WINDOW，同 arm_sentinel 形態），不等它、本次仍用舊值判定。

[files]
.claude/hooks/context_budget_guard.py（既有；本輪實測不在任何 LOC 預算面內）

[mechanism]
tools/tests/test_context_budget_guard.py::FanoutCapLadderTest（cap 對 quota 單調不增；q>=95 ⇒ cap == 0 嚴格斷言；環境變數覆寫值同受方向鎖）、::SentinelOffDegradesFreshnessTest（AUTOSDD_SENTINEL_OFF 下訊息必須帶 stale= 標記）

[risk]
①這支 hook 在每一次工具呼叫都會跑，任何未捕捉例外都會擴大爆炸半徑——既有 fail-open 的 try/except 必須維持（該檔記載過「hook 誤觸 deny 會把所有工具硬鎖死」的 P0）。②TTL=180s 是「量出來的上界（1.2pp/min ⇒ 12.5 分鐘跨完 80→95）內挑的值」，必須在註解裡誠實標成挑的，並指名 --watch 為重量入口。③.claude/hooks/ 沒有 LOC 棘輪 ⇒ 這裡是無棘輪的成長面，本步驟要自我節制
```

```text
[step]
Step 3：扇出帳 + 80% 併發閘（真的擋）。①先把 .claude/settings.json 的 PostToolUse matcher 補上 Agent|Workflow（今天缺這兩個，會讓計數器只增不減）；②PreToolUse 記 dispatched、PostToolUse 記 completed 到 %TEMP%\autosdd_fanout_<sid>.jsonl（append-only，帶時間戳，逾 15 分鐘的 dispatched 視為過期以自癒洩漏）；③block_verdict() 新增 quota 分支：quota tier=throttle 且 in-flight >= cap ⇒ exit 2 並印出「還剩多少、哪一條線最緊、建議改序列跑」。

[files]
.claude/settings.json（PostToolUse matcher）；.claude/hooks/context_budget_guard.py（帳的讀寫 + block_verdict 分支）

[mechanism]
tools/tests/test_context_budget_guard.py::FanoutLedgerPairingTest（PostToolUse matcher 必須是 PreToolUse matcher 的超集，分母現查 settings.json 不寫死）、擴充既有 ::PreToolUseBlockTest（quota>=80 且 in-flight>=cap ⇒ exit 2；且必須有 quota=50 的放行對照組）；tools/check_hooks_liveness.py 的形態鎖 A~F 守 settings.json 改動後仍是 exec form 且跨平台配對完整

[risk]
①改 settings.json 是改 deny 面，該檔記載過的 P0 就在這裡；改完必須用 claude -p --debug hooks 實證 hook 仍會跑（不閃窗不算驗收通過，正負兩面要一起看）。②PostToolUse 在 subagent 被打死時不會觸發 ⇒ 計數器洩漏向上、過度節流；靠 15 分鐘 TTL 自癒，這是已知限制必須寫進註解，失效方向（過度節流、且訊息會印出來所以可見）要明說。③只測「擋得住」不測「不亂擋」的鎖沒有鑑別力，對照組是硬要求
```

```text
[step]
Step 4：95% 閂鎖動作（依 kind 三分支）。cap=0 全擋；一次性閂鎖（沿用既有 announced_latches）做三件事：①寫可重啟點任務書（既有 write_resume_plan()），內含未完成 run 清單；②依 kind 分支——session ⇒ detached 外呼 planner 武裝 schtasks 到 endpoint 的 resets_at + RESET_SKEW_SECONDS；weekly_* ⇒ 不排程、只寫任務書 + 大聲通知（建議降扇出/切小模型/改做不吃額度的工作）；spend ⇒ 不排程、escalate 叫人去提額；③印收斂指引。憑證一律是 NextRunTime 這個值。

[files]
.claude/hooks/context_budget_guard.py（閂鎖與分支）；tools/session_resume_planner.py（只換觸發時刻來源，淨行數必須 ≤ 0）

[mechanism]
tools/tests/test_context_budget_guard.py::QuotaKindBranchTest（session 允許排程／weekly_* 禁止排程，斷言不會產生 schtasks 動作／spend 禁止排程且必須 escalate）；既有 relay_problems() + next_run_time() 空字串判紅（憑證閘）；AutoClaude/tools/check_loc_budget.py 守 planner ≤ 749

[risk]
①planner 只有 1 行餘裕，任何不小心的分支都會破線；正解是把邏輯做在 guard 側（sentinel_decide 本來就住那裡），planner 側只改呼叫參數。做不到就必須先做 ADR-004 已登記的 tools/session_endurance.py 抽離，不准調高門檻。②weekly_* 那一支若寫成無條件排程，會排一支七天後才響的工作而所有痕跡全綠——這是本 ADR 最貴的誤判，M6 就是為它立的。③閂鎖若沒做好會每次工具呼叫都寫一次任務書
```

```text
[step]
Step 5：reset 來源優先序 + 探測成本歸零。①relay_problems() 的 reset_source 白名單加入 endpoint-authoritative（同一行內加，+0 行）；②probe_quota() 改為先讀 quota 快取判定（額度可用 ⇒ 直接回 open=True，零 token），拿不到才回落現行 claude -p 探針（MAX_PROBE_ATTEMPTS 留給回落路徑）；③sentinel_decide 的 reset 時刻優先序做在 guard 側；④resets_at 的比較與去重一律截到分鐘（本輪實測有次秒級抖動）。

[files]
tools/session_resume_planner.py（白名單一行 + 呼叫改寫，淨行數 ≤ 0）；.claude/hooks/context_budget_guard.py（優先序與截分鐘比較）

[mechanism]
tools/tests/test_context_budget_guard.py::ResetSourcePriorityTest（endpoint-authoritative 進白名單；猜的來源仍必須被判紅；注入次秒抖動的兩個值必須判「相同」）；既有 SentinelDecisionTest 的四分支注入必須全綠

[risk]
①最大風險是「趁機把拒絕武裝那條放寬」——那是 ADR-004 最關鍵的一條，測試必須同時斷言「猜的來源仍被判紅」。②若做了字串相等比較，每次巡邏都會判 reset 變了而無謂重排（靜默的資源浪費，痕跡看起來正常）。③回落路徑不准刪：撞線後 endpoint 還回不回得動是本 ADR 最關鍵的未驗格
```

```text
[step]
Step 6：AutoClaude 側落地。①core/ports/quota_meter.py 新增 QuotaMeterPort（預設回「量不到」）；②infra/adapters/file_quota_meter_adapter.py 讀快取檔（不做網路、不 import harness code）；③utils/config.py 新增 token_guard.quota_throttle_pct=80 / quota_halt_pct=95 兩個獨立欄位（絕不複用 compact/halt），校驗 quota_halt > quota_throttle；④接在既有步驟邊界（prompt_dispatcher 的形狀）：>=80 不派下一個 step、>=95 走既有 halt+checkpoint 並把恢復時刻由 resume_delay_minutes 換成 endpoint 的 resets_at。subagent 層節流不重複實作（由互動側 hook 代勞，headless claude -p 跑本 repo hooks 已實證）。

[files]
AutoClaude/autoclaude/core/ports/quota_meter.py（新）、AutoClaude/autoclaude/infra/adapters/file_quota_meter_adapter.py（新）、AutoClaude/autoclaude/utils/config.py、AutoClaude/autoclaude/utils/config_resolver.py、AutoClaude/autoclaude/execution/prompt_dispatcher.py 或 halt_handler.py、AutoClaude/tests/ 既有測試檔

[mechanism]
既有 .importlinter 8 條 contract（adapter 不得 import tools/ 或 .claude/）；AutoClaude/tests 既有 config 測試擴充：斷言 quota_halt_pct > quota_throttle_pct，且斷言 quota 兩欄與 context 兩欄不共用預設物件；既有 check_loc_budget 的 tier 分級（port ≤400 contract / adapter ≤400）

[risk]
①最大風險是有人「順手」把 quota 門檻指向 context 門檻（數字剛好 80 對得上）⇒ 同名不同義，比沒有機制更危險，M10 就是為它立的。②本 venv 未安裝 claude-agent-sdk，且沒確認 production 走 SDK 支還是 PTY 支 ⇒ 接線位置要先實測確認。③本步驟必須等 Step 1 的取數器落地，否則又是一個沒有電的機制（本 repo 已判過三次「機制蓋好沒接電」）
```

```text
[step]
Step 7（可選，不影響主線）：statusLine 快取寫入器。在 ~/.claude/settings.json 設一支 statusLine 腳本，職責兩件：①印給人看的一行（five_hour% / seven_day% / context%）；②把整份 JSON 原樣寫到 quota 快取的同一個路徑（含時間戳、source=statusline）。之後本機消費者優先讀快取、過期才回落 REST。

[files]
~/.claude/settings.json（使用者層，非 repo）；~/.claude/statusline_quota.py（使用者層）

[mechanism]
無 repo 內機械物（它在使用者層，不在 repo 掃描面）⇒ 這一步的驗收只能靠當回合實跑並貼輸出；且必須在 quota_meter 的 source 欄位分辨 statusline 與 endpoint 兩種來源，讓「快取只在有人跑互動 session 時更新」這件事在資料裡看得見

[risk]
①statusLine 真的會不會送出 rate_limits 完全未實測（欄位表來自 claude.exe 的自述），這一步可能整個做不成——所以標可選、主線走 REST。②射程誠實劃界：它只在互動 TUI 更新，絕不得當無人看管期間的權威源，否則會蓋出「有人看著時很準、沒人看時全盲」的機制（R80 哨兵整晚失明的同型）
```

```text
[step]
Step 8（需掌舵者拍板，本輪只做最低限度）：OAuth token 4 小時到期。最低限度＝取數器每次呼叫前比對 expiresAt，並把「token 已過期/401」與「額度真的沒回來」在痕跡裡分成兩個不同的事件名，否則排程器會把認證失敗誤判成額度未恢復而一直等下去。完整解（以 refreshToken 打 POST /v1/oauth/token 換新 token 並回寫檔案）是安全決策，需拍板後才做。

[files]
tools/lib/quota_meter.py（僅過期判定與痕跡分流）；（拍板後）同檔的 refresh 實作

[mechanism]
tools/tests/test_context_budget_guard.py::QuotaUnmeasurableTest 擴充：token 過期與 HTTP 401 必須產出與「額度未恢復」不同的 kind，且兩者都不得回一個百分比；並斷言任何輸出（含痕跡）不含 token 值的前綴

[risk]
①refresh 流程從未實跑過，端點與參數名是從二進位字串讀到的 ⇒ 直接實作有很高機率失敗。②這一步決定「無人看管過夜」能不能成立（本輪覆核 expiresAt 距當下約 3.8 小時，5 小時窗與 7 天窗的等待都會跨過它）——所以最低限度那一半必須做，不能因為完整解要拍板就整步跳過。③禁止把 token 值寫進任何 log／任務書／痕跡，這是硬紅線
```

### §3.3 ADR 自陳的開放問題（12 條，逐字保全）

**Q01**

```text
🔴 最關鍵的未驗格：撞線後（HTTP 429 或 session 已死）/api/oauth/usage 還回不回得動？本輪兩次成功呼叫都在額度充裕時（44% / 56%）。這一格決定整條續航鏈能不能靠 endpoint 站住——回落路徑（claude -p 探針）在它被驗證之前絕對不能刪。可行的量法：下次真撞線時由哨兵那一跑順手打一次並記進痕跡（零成本、不需要製造撞線）。
```

**Q02**

```text
端點自己有沒有速率限制？本輪兩次呼叫相隔約 1 秒皆 200，是弱證據。900 秒巡邏 + 180 秒 TTL 的呼叫頻率是估的，不是量出來安全的。若它有限制而我們踩到，失效方向是「量不到」（fail-closed，可接受），但會靜默降級成 L4。
```

**Q03**

```text
本帳號 spend.enabled=False / extra_usage.user_disabled=True，而 R80 逐字稿分類出 99 筆 quota_spend——兩者不一致，成因未解。是 classify_limit() 假陽性，還是那 99 筆來自帳號狀態不同的時期，還是 spend 與 monthly spend limit 根本是兩回事？在解開之前，兩條分類器只能並存（§2.6），這是權宜不是設計。
```

**Q04**

```text
Workflow 工具的 payload 裡到底有沒有 run 識別欄位、resumeFromRunId 的確切參數名是什麼？本 ADR 唯讀階段量不到，Step 0 必須先量。量不到就退回「只記 tool 名+描述+時間戳」——那仍足以人工重派，但自動 resumeFromRunId 就做不成。
```

**Q05**

```text
OTEL 推送管道完全沒查（OTEL_METRICS_EXPORTER 二進位命中 14 次、claude_code.token.usage 2 次）。它可能是唯一「不必自己輪詢」的推送式管道 ⇒ 若成立，Step 1 的輪詢設計與 TTL 取捨整組可以簡化。調研自評這是最值得下一步補的空白。
```

**Q06**

```text
statusLine 真的會送出 rate_limits 嗎？§2.2 與 §3.1 那兩列的欄位表是 claude.exe 內嵌 schema 的自述，不是觀測到的 payload。Step 7 因此標為可選；若它不成立，「零額外成本的水位快取」這個收益就不存在。
```

**Q07**

```text
refresh token 該不該由本 repo 的程式碼持有並使用？這是安全決策不是工程決策，需要掌舵者拍板。無論怎麼決，禁止把 token 值寫進任何 log／任務書／痕跡。
```

**Q08**

```text
.claude/hooks/ 該不該納入 LOC 棘輪？本輪實測它不在 check_loc_budget 的任何掃描面內（ROOT_TOOLS_ROOT 只覆蓋 tools/，SPECIAL_FILES 逐列讀過無此檔）。本 ADR 把判讀往那裡加，等於利用一個沒有棘輪的成長面——誠實的代價，不是免費午餐。
```

**Q09**

```text
cap=2 與 TTL=180s 都是「量出來的上界內挑的值」。上界站得住（扇出 42/55/1；漂移 1.2pp/min），但中間那個值沒有量測依據。要不要花一輪去量「cap 多少時完成率最高」？我的建議是不要——那需要製造撞線才量得到，成本遠高於收益，方向鎖（單調不增、q≥95 必為 0）已經守住了會出事的那一半。
```

**Q10**

```text
訴求 c / d / e / f 的逐字原文，我在 docs/ 全層搜尋不到（只有 a / b 在 improving_104 §1 有家）。本 ADR 對它們的理解是從任務書與 ADR-004 §2.7 反推的。若與掌舵者原話不符，以原話為準——這一段本身就是「宣稱先於查證」那一桶的預防。
```

**Q11**

```text
訴求 f 只有結構結論（退避重試在 per-account 週期額度上結構性無效），沒有讀過那些框架的原始碼或官方文件。若要據以做更細的設計決策，需要補真正的功課；本 ADR 只把它當背景。
```

**Q12**

```text
本輪繼承了一個與本 ADR 無關的紅：tools/lib/hook_wiring.py 407 > 400（+7），使 check_loc_budget.py 在乾淨工作樹上 rc=1。它會讓 §6.4 的 rc=0 判準在 Step 0 之前不可能成立。另：調研第 7 項在 repo 根跑過一次 claude -p，可能多武裝了一支 AutoSDD_Sentinel_*，未查證也未清理。
```

### §3.4 review:SA｜系統分析師（SA）｜verdict = **REJECT**

**summary（逐字保全）**：

```text
獨立實查了 ADR 的每一個可查宣稱。**好消息**：取數管道真的可重跑（我在 21:45/21:46 獨立打了兩次，HTTP 200），A5（resets_at 次秒抖動）、A7（planner 749/750 餘裕 1 行，逐字相符）、A8（hook_wiring.py 407>400、rc=1）、A9（ROOT_TOOLS_ROOT 只覆蓋 tools/）、A10（settings.json:128）、A12（settings.json:217 缺 Agent|Workflow）全部逐字屬實，ADR 編號 005 也對。誠實劃界的段落寫得比多數輪次好。

**壞消息是六筆結構性的**，其中三筆直接讓主交付物失效：

① **最致命：quota 阻斷分支結構上到不了**。`main()` 在呼叫 `block_verdict()` 之前有五道 context 早退，其中 `tier_of` 在 context <75% 回 None、`main():1145-1146` 當場 return 0。而 R80 驗屍自己的核心事實是「撞額度那一刻 context 只有 ~18~20%」⇒ Step 3 說的「block_verdict() 新增 quota 分支」在**這支 ADR 唯一存在理由的那個場景裡是死碼**。這是本 repo 判過三次的「機制蓋好沒接電」第四次復發，而且 M4 若不注入「低 context × 高 quota」就會恆綠。

② **量測器讀錯了它賴以存在的 payload**。ADR 只讀了 `utilization`/`resets_at`/`limits[]`。我把整份 payload 攤開後發現：(a) `five_hour` 的鍵是 `limit_dollars/used_dollars/remaining_dollars/utilization/resets_at`——**分母是 API 自己命名的**，§2.1「本 repo 不再擁有分母這個概念」與 §6.1 要求寫死的 `denominator: "no local denominator"` 是把未查證的話寫成常數（R73 判例）；(b) `nimbus_quill` 帶**真值** `utilization=0.0` 卻**不在** `limits[]` 裡（limits 只有 session/weekly_all/weekly_scoped）⇒ §2.3「只消費 limits[]」本身就是一個寫死的投影，對它結構上失明，而 M7 照樣全綠——正是 M7 宣稱要防的靜默失明。

③ **1.2pp/min 這個推導出 TTL 的率被我的第三個量測點推翻**。ADR：44.0@21:19→56.0@21:29。我：**8.0@21:45→9.0@21:46**，且 `five_hour.resets_at` 由 13:40Z 跳到 18:40Z（正好 +5h）⇒ 視窗在 21:40 翻頁、utilization **跌了 48pp**。這個量非單調、在視窗邊界不連續，兩點率不可外推，「80→95 要 12.5 分鐘所以 180s 有 4 倍餘裕」沒有依據。

另三筆：cap 綁在 per-transcript 的 sid 上而額度是 per-account（N 個併發跑各拿 cap=2，根本沒有界住帳號燒用量，卻宣稱「一個機械物守兩個載體」）；deny 路徑會漏記 in-flight 造成**自我增強的永久節流**；mac 上 95% 那道靜默什麼都不做而 M6 照樣綠。

順帶：open question 3（spend vs 99 筆 quota_spend）我的量測基本解開了——`extra_usage.credits_ever_enabled=True` 且 `user_disabled=True`，`spend` 是「加購額度」池不是方案上限，所以那是**時期不同**而非分類器假陽性，不必永久並存兩條。`is_active` 語意也不再未知：兩次觀測都落在 max 那一條上。
```

#### §3.4.1 blocking（7 筆，逐字保全）

##### `SA-B1`

```text
[issue]
quota 阻斷分支放在 block_verdict() 內，而該函式在「低 context × 高 quota」——也就是本 ADR 唯一存在理由的那個場景——結構上到不了。Step 3 只寫「block_verdict() 新增 quota 分支」，那會是死碼。這是本 repo 判過三次的「機制蓋好沒接電」第四次復發。

[evidence]
Read .claude/hooks/context_budget_guard.py:1132-1149 逐字：`blocking = event == "PreToolUse"` 之後有五道早退，全部是 context 語意：
  :1134-1135 `if not isinstance(raw_path, str) or not raw_path.strip(): return 0`
  :1137-1138 `if not transcript.is_file(): return 0`
  :1141-1142 `used, peak, model = scan_transcript(...)` / `if used is None: return 0`
  :1144-1146 `tier = tier_of(used, window)` / `if tier is None: return 0`
  :1148-1149 `if blocking: return block_verdict(payload, used, window, source, tier)`  ← 只有走到這裡才會呼叫
同檔 :835-844 `def tier_of(...) -> str | None:` … `if ratio >= HARD_RATIO: return TIER_HARD` / `if ratio >= WARN_RATIO: return TIER_WARN` / `return None` ⇒ context <75% 一律 None。
而 ADR §1.1 自己引用的 R80 事實是「撞線那一刻 context 水位只有約 18~20%」⇒ tier is None ⇒ main() 在 :1146 return 0，block_verdict() 一次都不會被呼叫。
即使到得了，block_verdict 內還有兩道 context 閘：:1177 `if tier != TIER_HARD: return 0`、:1179-1180 `if not may_block(source): return 0`。

[required_change]
Step 3 必須明文改寫 main() 的控制流：quota 軸的判定要在一條**不經過 `used is None` / `tier_of` / `may_block`** 的獨立路徑上求值（context 與 quota 是兩把尺，早退條件不可共用）。M4 必須新增一組注入：合成逐字稿 used/window ≈ 0.18（context tier 為 None）× quota=85 × in-flight≥cap ⇒ **必須 exit 2**；並附「先注入看它紅、再實作看它綠」的兩次 rc。沒有這條低-context 注入，M4 在真實故障場景下恆綠。
```

##### `SA-B2`

```text
[issue]
§2.1「本 repo 不再擁有分母這個概念」與 §6.1 強制輸出的固定字串 `denominator: "server-computed plan utilization (no local denominator)"` 是未查證的宣稱寫成常數。API 自己就把分母命名出來了。ADR 從頭到尾沒有讀過 five_hour 的子鍵。

[evidence]
我當回合實跑（scratchpad/sa_verify_buckets.py，.venv python，21:46:37 +08:00，HTTP 200）攤開頂層桶：
  five_hour:
      utilization = 9.0
      resets_at = '2026-08-08T18:40:00.110843+00:00'
      limit_dollars = None
      used_dollars = None
      remaining_dollars = None
⇒ schema 是**美元計價**（limit_dollars 就是分母），本 team 帳號恰好為 None，但「這個帳號現在是 null」不等於「分母這個概念不存在」。ADR 的 A1/A4 只列了 utilization / resets_at / limits[] / 17 個頂層鍵，從未列出這三個 *_dollars 欄位 ⇒ 「口徑說得清楚」這件事在 ADR 內並未成立。

[required_change]
①§6.1 的 `denominator` 欄改為**從 payload 推導**而非寫死：`limit_dollars`/`used_dollars` 非 null 時原樣回報（並標明單位為美元），為 null 時回報「伺服器未揭露分母」——不得輸出一句對所有帳號都宣稱為真的散文。②§2.1 的措辭由「不再擁有分母」改成「分母由 server 持有，本機不再自行推導」（結論〔換帳號零常數要改〕不變，理由要對）。③加一條交叉核對：兩個 dollars 欄皆非 null 時斷言 `utilization ≈ used/limit*100`，讓 utilization 壞掉/過期變成**可偵測**而非靜默採信。
```

##### `SA-B3`

```text
[issue]
§2.3「判定層只消費 limits[] 取 max(percent)」本身就是一個寫死的投影，對「有真值但不在 limits[] 裡」的桶結構上失明——而 M7 只斷言「原始碼沒有寫死桶名 tuple」「未知桶不拋例外」，這種失明它抓不到，會恆綠。這與 ADR 自己的 A4 立論（schema 正在長、寫死名單的失明是靜默的）自相矛盾。

[evidence]
同一次實跑輸出：
  --- 所有『有值』的桶（dict 型）---
  five_hour: utilization = 9.0
  nimbus_quill: utilization = 0.0   ← 代號桶，帶真值
  seven_day: utilization = 34.0
  --- limits[] 涵蓋了哪些 kind ---
  kinds = ['session', 'weekly_all', 'weekly_scoped']
  --- 有值的桶 vs limits[] ---
  有 utilization 值的頂層桶 = ['five_hour', 'nimbus_quill', 'seven_day']
⇒ `nimbus_quill` 有 utilization 實值卻**沒有**對應的 limits[] 條目。若未來是它（或另一個代號桶）先滿，取 max(limits[].percent) 會讀到一個低值而永不節流，且沒有任何東西轉紅。

[required_change]
判定改為對**兩個來源的聯集**取 max：`limits[].percent` ∪ 每一個 `utilization` 為數字的頂層 dict（桶名一律動態列舉，不寫死）。M7 必須加一組注入：構造一份 payload，讓一個**不在 limits[] 裡的代號桶**成為最大值，斷言 meter 回傳的就是那個值與那個 kind；不加這條，M7 對本缺陷零鑑別力。
```

##### `SA-B4`

```text
[issue]
A3 的「1.2pp/min」是同一個視窗內兩點算出來的率，被 §2.4 當成推導 TTL=180s 的唯一依據。我的第三個量測點顯示這個量非單調、且在視窗邊界不連續 ⇒ 該推導不成立。加上 hook 是拿**過期快取值**做判定（fire-and-forget 刷新，本次仍用舊值），一次爆量扇出可能在一個 TTL 內把 80→95→100 全部跨完。

[evidence]
ADR A3：44.0@21:19 → 56.0@21:29（+12pp/10min）。
我當回合兩次獨立實跑：
  now -> 2026-08-08T21:45:17 ... five_hour: utilization=8.0 resets_at='2026-08-08T18:40:00.330810+00:00'
  now -> 2026-08-08T21:46:37 ... five_hour: utilization=9.0 resets_at='2026-08-08T18:40:00.110843+00:00'
對照 ADR 那次的 resets_at='2026-08-08T13:40:00.815928+00:00'
⇒ 視窗於 21:40(+08:00)=13:40Z 翻頁，resets_at 前進**正好 5 小時**，utilization 由 56.0 掉到 8.0（−48pp／約 16 分鐘）。同時 8.0→9.0 發生在 80 秒內（≈0.75pp/min）而我幾乎沒在跑東西 ⇒ 率完全取決於當下在做什麼，不是常數。

[required_change]
①刪掉「以 1.2pp/min 推得 12.5 分鐘、180s 留 4 倍餘裕」這段推導，改寫成「TTL 是挑的、上界未經量測」，並保留 `--watch` 為重量入口（§2.4 已半寫，要寫滿）。②程式與註解不得假設 utilization 單調遞增（視窗翻頁會使它驟降），去重／比較邏輯要能吃到下降。③補一條 staleness 判準：`stale > TTL` 時不得直接採信舊值判為 normal，須降級到 L4 或帶安全邊際上調，並以注入自證（快取值 78 + stale 超 TTL ⇒ 不得判 normal）。
```

##### `SA-B5`

```text
[issue]
cap 綁在 per-transcript 的 session id 上，而額度是 per-account 的單一池 ⇒ 這個節流器**沒有界住帳號層級的燒用量**。§2.4 宣稱「一個機械物守兩個載體」在 binary 層面成立，但**預算不共用**：AutoClaude 驅動的 headless CLI 是另一個 session、另一份帳、另一個 cap=2。

[evidence]
ADR §2.5 定的帳路徑為 `%TEMP%\autosdd_fanout_<sid>.jsonl`。實查 context_budget_guard.py:847-853 `def session_id_of(transcript: Path) -> str:` 逐字「逐字稿檔名（去副檔名）即 session id」。同檔 :617-621 逐字記載 subagent 逐字稿的佈局：「subagent 落在 `<sid>/subagents/*.jsonl` 與 `<sid>/subagents/workflows/<wf>/*.jsonl`」⇒ 每個 subagent／每一次 headless 跑都有**自己的 transcript ⇒ 自己的 sid ⇒ 自己的帳檔 ⇒ 自己的 cap=2**。N 個併發載體 ⇒ 帳號層級同時在飛 2N，而 quota 只有一個池。

[required_change]
二擇一並在 ADR 內明寫：(a) 帳改為**帳號層級單一檔**（或判定時聚合同目錄下所有 sibling 帳檔）後才可宣稱 cap 界住燒用量；或 (b) 把 §2.4「一個機械物守兩個載體」的宣稱**縮小射程**為「每個 session 各自不超過 cap」，並在 §8 已知限制明列「總併發＝cap × 併發 session 數，未受界」。無論哪一種，M3/M5 要有一條注入涵蓋「兩份 sid 帳同時存在」的情形。
```

##### `SA-B6`

```text
[issue]
Step 3 沒有定義「記 dispatched」與「跑 verdict」的先後。若先記後判，每一次被擋下的呼叫都會留下一筆有 dispatched、永遠不會有 completed 的記錄（PostToolUse 對被 deny 的工具不會觸發）⇒ 節流期間 in-flight 單調上升，一旦到 cap 就**永遠回不來**，即使 quota 已經掉回 50。15 分鐘 TTL 自癒救不了，因為新的 deny 持續把它重新墊高。失效方向是永久過度節流，而外觀是「額度好像一直很緊」。

[evidence]
ADR Step 3 逐字：「②PreToolUse 記 dispatched、PostToolUse 記 completed 到 %TEMP%\autosdd_fanout_<sid>.jsonl（append-only，帶時間戳，逾 15 分鐘的 dispatched 視為過期以自癒洩漏）；③block_verdict() 新增 quota 分支：quota tier=throttle 且 in-flight >= cap ⇒ exit 2」——順序未定義，且 ADR 自己已承認同方向的第二個洩漏源（Step 3 risk ②「PostToolUse 在 subagent 被打死時不會觸發 ⇒ 計數器洩漏向上」）。兩個洩漏源同向疊加。

[required_change]
明文規定 **dispatched 只在放行路徑上記錄**（verdict 之後、回 0 之前），deny 路徑一行都不寫。並補一條紅綠注入：連續 K 次被擋（K > cap）之後把 quota 降到 50，下一次呼叫**必須放行**——這條若不寫，B6 這個失效在任何合成測試下都看不出來。
```

##### `SA-B7`

```text
[issue]
mac/Linux 上 95% 那道會靜默什麼都不做：schtasks 只在 Windows 成立，而武裝入口本身就有 `os.name != "nt"` 早退。§8-10 用散文承認了，但 M6 是合成注入 ⇒ 在 mac 上照樣全綠。違反本 repo 的「明說做不到而不是靜默缺席」（鐵律三）。

[evidence]
實查 context_budget_guard.py:1001-1003：
  def arm_sentinel(payload: dict) -> None:
      ...
      if os.name != "nt" or os.environ.get(SENTINEL_OFF_ENV):
（同檔 :274 亦有 `if os.name != "nt":`）⇒ 非 Windows 一律 return，不武裝、不出聲。
ADR §8-10 逐字承認「mac/Linux 完全沒有…schtasks 那一半只在 Windows 成立」，但 M6 的判準是「session ⇒ 允許排程／weekly_* ⇒ 禁止排程」的合成注入，不含平台維度 ⇒ 在 mac 上「不排程」與「排不了」外觀相同、判準皆綠。

[required_change]
①95% 閂鎖在非 Windows 必須輸出一則明確訊息（例如「本平台無排程載具，已寫任務書但**沒有**武裝任何喚醒，請自行處理」），不得沿用與 weekly_* 分支相同的「不排程」靜默路徑。②M6 加一組以 `force_os_name="posix"` 強制的注入（`tools/tests/test_check_hooks_liveness.py` 既有 `_run_lint_hook(..., force_os_name=...)` 手法可直接沿用），斷言該訊息存在、且它與 weekly_* 分支的訊息**不同字串**。
```

#### §3.4.2 non-blocking（9 筆，逐字保全）

**SA-N01**

```text
【已複驗屬實，可直接引用】ADR 編號：`Get-ChildItem docs/04_planning/ADR/` 回四支，最大 ADR-XPLAT-004 ⇒ 005 正確。A7 逐字相符：`[guardrail_cli<=750] tools/session_resume_planner.py: 749 （餘裕 1 行）`。A8 逐字相符且 rc=1：`[guardrail_lib<=400] tools/lib/hook_wiring.py: 407 > 400 (+7)`。A9 相符：`ROOT_TOOLS_ROOT = PROJECT_ROOT.parent / "tools"`（:268），SPECIAL_FILES 無 .claude 條目。A10 相符：settings.json:128 matcher = `Task|WebFetch|WebSearch|Agent|Workflow`，且 guard :292 `BLOCKING_TOOLS = ("Task", "WebFetch", "WebSearch", "Agent", "Workflow")` 一致。A12 相符：settings.json:217 = `Read|Task|Grep|Glob|WebFetch|WebSearch|Bash|PowerShell`，確實缺 Agent/Workflow。§1.1 引的 guard:437-439 docstring 逐字屬實。may_block 引文逐字屬實（:1179-1180）。
```

**SA-N02**

```text
【A5 已獨立證實，§2.7 截到分鐘的規則是對的】我兩次呼叫的 five_hour/seven_day 次秒部分成對出現（第一次 .330810/.330834，第二次 .110843/.110871）⇒ 確實是「now + 剩餘」算出來的，跨呼叫做字串相等比較必然每次判「reset 變了」。這條可以從「推論」升級為「已複驗」。
```

**SA-N03**

```text
【open question 3 基本可以結案，不必永久並存兩條分類器】我的實跑顯示 `extra_usage = {'is_enabled': False, 'user_disabled': True, 'spend_limit_reached': False, 'credits_ever_enabled': True, ...}`，且 `spend.disclaimer = 'Usage credits cover you when you hit your plan limits...'`、`spend.can_purchase_credits: False`。⇒ `spend` 指的是**加購額度池**，不是方案上限；`credits_ever_enabled=True` 表示這個帳號**曾經**開過而現在關掉。所以 A6 的「spend.enabled=False 卻有 99 筆 quota_spend」最可能是**時期不同**（那 99 筆來自credits 還開著的時期），不是 classify_limit() 假陽性。建議把 §2.6 從「權宜、成因未解」改成「已定位為時期差異」，並把「兩條並存」的理由改成「離線可用性」這個真正站得住的理由，而不是「矛盾未解」。
```

**SA-N04**

```text
【is_active 語意不再未知，§2.3 的 hedge 可以拿掉（決策不變）】ADR 觀測：session 56% → True、weekly_all 32% → False。我的觀測是鏡像：session 8% → False、weekly_all 34% → True。兩次都是 True 落在**較大**的那一條 ⇒ 它標的是「當前最緊的那一條」。這反而支持「取 max」等價於「取 is_active 那一條」，§2.3「不用 is_active 篩」的決定仍然正確（取 max 更穩健），但可以把「語意未知、拿它去篩會製造失明面」改寫成「已兩次觀測到它追蹤 max，故取 max 與它一致且不依賴該欄語意」。
```

**SA-N05**

```text
【§2.8「沒有五小時這回事」在有了權威源之後需要重寫】ADR-004 的結論是從**逐字稿 reset 字面**推得的；權威 endpoint 顯示 five_hour.resets_at 由 13:40:00Z 前進到 18:40:00Z，**正好 +5 小時**，是一個乾淨的格點。ADR 手上已經有這個管道卻沒去驗這件事。§2.8 的實質結論（實際停機分佈 min 0.5/median 59.8/max 253.2 分、不必每 50 分鐘醒）不受影響、仍然成立，但「沒有五小時這回事」這句話應改為「停機長度不等於視窗長度」——視窗本身是 5 小時且格點可查。
```

**SA-N06**

```text
【§8-4 的 token 到期宣稱已複驗屬實，且比 ADR 寫的更緊】我實測 `expiresAt -> 2026-08-09T01:19:39+08:00 | hours_left = 3.57`（ADR 寫約 3.8 小時，同一天稍早）。scopes = ['user:file_upload','user:inference','user:mcp_servers','user:profile','user:sessions:claude_code'] —— 沒有任何一個看起來是 offline/refresh 用途，Step 8 的完整解（自行打 /v1/oauth/token 換 token）風險比 ADR 估的更高，建議 Step 8 只做「最低限度」那一半，完整解不要排進本輪。
```

**SA-N07**

```text
【小瑕疵：line cite 漂移】§1.1 引 `AutoClaude/autoclaude/utils/token_tracker.py:118-123 window = max(modelUsage[*].contextWindow)`。實查該字串在 **:97**（docstring），`contextWindow` 的實際讀取在 **:121**。射程內、結論不變，但引用區間不精確。本 repo 已判過「以寫死行號指認站點」的問題（R77 訂正根 CLAUDE.md 的 hook 橋接站點），建議改引符號名而非行號。
```

**SA-N08**

```text
【M5 可行性已確認，不是障礙】我一度擔心 settings.json:216 註記的 `TestHookRegistrationScopeIsShrinkOnly` 會擋下「把 PostToolUse matcher 加寬」。實查 tools/tests/test_check_hooks_liveness.py:1927-2000：`registration_shrink_problems()` 只報 baseline 有而現況缺的工具（加寬不會產生 missing），`test_baseline_covers_every_current_registration` 的鍵是 (event, script) 配對而非 matcher 字面 ⇒ 對既有的 (PostToolUse, context_budget_guard.py) 條目加寬 matcher 合法、不需動 baseline。Step 3 的第一個動作可以照做。
```

**SA-N09**

```text
【建議補一條 ADR 沒想到的機械物】B2/B3 這兩筆的共同形態是「meter 只讀了 payload 的一小塊，而沒讀到的那塊正好推翻了設計前提」。建議 M7 之外再加一條**schema 漂移偵測**：取數器記錄本次 payload 的頂層鍵集合，與上次比對，出現新鍵／既有桶由 null 變成有值時寫進痕跡並出聲一次。本輪光是 ADR 那次（17 鍵）到我這次（同 17 鍵但 nimbus_quill 由 ADR 描述的『代號桶』變成帶真值的 dict）就已經看得到差異，這個面是會動的。
```

### §3.5 review:SD｜系統設計師（SD）｜verdict = **APPROVE_WITH_CONDITIONS**

**summary（逐字保全）**：

```text
事實面品質很高：ADR 點名的每一個檔案、函式、常數、行號我都逐一實查，**全部存在且對得上**（planner 749/750 餘裕 1 行、hook_wiring 407>400 使 check_loc_budget 今天 rc=1、PreToolUse matcher 已含 Agent|Workflow、PostToolUse 缺這兩個名字——四筆逐字複驗為真）。三個核心洞見（權威 endpoint 取代反推分母、額度是三條線不是兩條、單位正規化是唯一抓得到差 100 倍的地方）站得住，我沒有異議。

但**訴求 b 的核心機制在今天的 harness 上結構性失明**，這是必須先修的一筆。我實測 47/47 次 Workflow 的 tool_result 都是「Workflow launched in background」——也就是說 Workflow 這個工具呼叫**在扇出開始之前就結束了**，PostToolUse 當場觸發。ADR §1.2 自己記載 R80 四次撞線死的是 42／55／1 個 subagent，而那些 subagent 正是在背景 workflow 內部長出來的。用「dispatched − completed」在主 session 的 Pre/PostToolUse 邊界算 in-flight，對這個形狀恆讀到 ≈0 ⇒ cap=2 永遠不會綁到。更深一層：帳是 `autosdd_fanout_<sid>.jsonl`（**per-session**），而額度是 **per-account**；我在 %TEMP% 數到 20 個相異 session id 各自持有自己的狀態檔 ⇒ 就算每個 workflow agent 都跑 hook，每個也只看得到自己那一份帳。這正是本 repo 判過三次的「機制蓋好沒接電」，而且外觀會是全綠。

另外三筆：M11 宣稱 .importlinter 會攔 adapter 反向 import harness，但該檔對 `tools`／`.claude` **零命中**，8 條 contract 全是 autoclaude 內部分層 ⇒ 假機械物；8 個新測試類別全落在 `tools/tests/`，而 TestGuardLayerRatchet 逐字要求該層**淨行數只准往下**，ADR 只為 quota_meter.py 登記了款(9)（那是另一道 per-file 判準）⇒ §6.5 的 rc=0 在設計上不可達；runId 只出現在 tool_result、不在 tool_use input，所以 §2.5「PreToolUse 記 payload 裡的 run 識別」對 launch 情境不成立，而 resumeFromRunId 的 same-session 限制在 §8 那 12 條已知限制裡一條都沒提到。

四筆都可修（多半是誠實劃界＋換記錄點），ADR 的地基不必動，所以我給條件通過而不是打回。
```

#### §3.5.1 blocking（4 筆，逐字保全）

##### `SD-SD-B1`

```text
[issue]
80% 併發閘對「真正造成撞線的那種扇出」結構上失明：Workflow 工具在扇出開始前就返回，in-flight 計數恆讀 ≈0，cap=2 永遠不會綁到。且扇出帳是 per-session 而額度是 per-account，兩者單位不匹配。ADR 卻把它斷言成「這是機械的併發下降，不是給模型看的一行字」。

[evidence]
實測逐字稿（40 支、13,914 行，~/.claude/projects/d--CursorProject-AISDCL-Agent/）：①Workflow 的 tool_result **47/47** 皆為 `Workflow launched in background. Task ID: w9kp0o1pe` ⇒ 該 tool call 在內部 agent 生成前就完成，PostToolUse 當場觸發、completed 立刻追平 dispatched。②tool_use 名稱分佈：Agent=127、Workflow=51、Task/WebFetch/WebSearch=0（證實 ADR 對名稱的判斷為真，但也證實 51 次 Workflow 的內部扇出從未以 tool_use 形式經過主 session）。③ADR §1.2 自陳撞線時死的是 42／55／1 個 subagent，即 workflow 內部扇出。④ADR §2.5 逐字把帳定在 `%TEMP%\autosdd_fanout_<sid>.jsonl`（per-session），而 `Get-ChildItem $env:TEMP -Filter autosdd_*` 回 93 檔、**20 個相異 session id**，每個 session 各自持有狀態檔 ⇒ 沒有任何一份帳看得到全帳號併發。

[required_change]
二選一，不得含糊：(a) 把計數單位對齊被限制的資源——帳改成**帳號級單一檔**（非 per-sid，需處理跨行程並行 append 與讀取競態），並找到能觀測 workflow 內部 agent 生滅的面（若今天不存在，就明說做不到）；或 (b) 誠實收窄 §2.4 與 key_decisions 的宣稱為「只擋主迴圈直接派的 Agent 與 Workflow 的**啟動**，對 workflow 內部扇出無效」，把它列進 §8 已知限制，並停止使用「扇出的每一次派發今天就已經會經過這支 hook」這句話。另請補上：42 個 Agent 在同一則 assistant message 內平行派發時，PreToolUse 平行觸發、JSONL 讀寫無鎖，可能全部讀到 in-flight<cap 而全數放行——這一點 ADR 完全沒提。
```

##### `SD-SD-B2`

```text
[issue]
M11 是假機械物：ADR 宣稱既有 .importlinter 8 條 contract 會在「adapter 去 import tools/ 或 .claude/」時轉紅，實際上沒有任何一條守這件事。

[evidence]
`Select-String -LiteralPath AutoClaude\.importlinter -Pattern 'tools|\.claude|root_package'` 只回一筆：`12: root_packages =`——全檔對 `tools`／`.claude` **零命中**。8 條 contract 逐條為 plugin 互不 import／core 不依賴 execution+infra／_runner_internals／Brain↔Executor 雙向／checkpoint 內部模組／utils.observability／IKbMetricStore，全部是 autoclaude 套件**內部**分層。import-linter 的 forbidden contract 必須明文列出 forbidden module，且相依圖只建在 root_packages 上 ⇒ `import tools.lib.quota_meter` 這種對外部頂層套件的 import 不在圖內，不會被任何 contract 攔下。這正是根 CLAUDE.md 反覆判過的「檔案在、判準在、測試全綠，但守的是別的東西」。

[required_change]
要嘛補一條真判準（例如在 AutoClaude/tests 既有檔內加 AST 掃描：`autoclaude/**` 的 import 名單不得出現 `tools` / `.claude`，含 importlib 動態字串），要嘛把 M11 那一列的機械物欄誠實改成「無機械物」。兩者皆可，但不得留著現在這個宣稱——它會讓下一輪的人以為這個方向已經有人守。
```

##### `SD-SD-B3`

```text
[issue]
8 個新測試類別全落在 tools/tests/，而該層有「淨行數只准往下」的棘輪；ADR 只為 tools/lib/quota_meter.py 登記了款(9)（那是另一道 per-file tier 判準），導致 §6.5 的 rc=0 驗收在設計上不可達。

[evidence]
`tools/tests/test_adr_xplat001_c1c2_lock.py:2385 class TestGuardLayerRatchet` docstring 逐字：「(d) 護欄層棘輪：`tools/tests/` 這一層的**淨行數**只准往下走（`DEF-101-561③`）」；同檔 :647 `_GUARD_DIR_REL = "tools/tests"`、:678「`tools/tests/` 的鎖檔支數只准往下」、:2866「`TestGuardLayerRatchet` 的護欄層棘輪要求 `tools/tests/` 的**淨行數**不得上升」。ADR 要新增 M1/M2/M3/M5/M6/M7/M8/M13 共 8 個測試類別＋M4 兩處擴充，全部併入 `tools/tests/test_context_budget_guard.py` ⇒ 該層淨行數必然大幅上升。而 ADR §3.2 的款(9) 登記只針對 `tools/lib/quota_meter.py`（那由 check_loc_budget 的 guardrail_lib≤400 per-file tier 管，與本棘輪是兩道不同的判準），§7 紀律 3 又明文「不准調高任何門檻／棘輪」。

[required_change]
在 §3.2／§7 明文把 `tools/tests/` 的淨行數成長一併納入 improving_104 §4 款(9) 的登記手續（理由欄標 `[非淨減法輪]` ＋ 指名一份具名 .md 當逐檔清單的家，並接受該輪 Q2 判未達成），或在同一次變更內指出等量以上的刪除來源。順帶訂正 §5 開頭與 §7 紀律 2 對 DEF-101-561③ 的描述：現行語意已由 R78 ARCH-03 改成「淨行數不得上升」，不再是「只准合併／刪除、禁止新增鎖檔」（同檔 :68 逐字）。
```

##### `SD-SD-B4`

```text
[issue]
§2.5 的 runId 記錄點選錯（PreToolUse 拿不到 runId），且 resumeFromRunId 的 same-session 限制在整份 ADR 完全沒有被承認。

[evidence]
實測：`resumeFromRunId` 在 tool_use **input** 只出現 10 次，且全是舵手手動續跑那幾次；runId 字面（`wf_5a686145-dc4`／`wf_30f62ddc-705` 等）出現在 **tool_result** 內（tool_result 命中 runId/TaskID 共 337 次）⇒ 一個新啟動的 workflow，其 runId 在 PreToolUse 觸發的那一刻**還不存在**。而 ADR §2.5 逐字寫「PreToolUse 記 `dispatched`（含 tool 名、payload 裡的 run 識別、時間戳）」——這對 launch 情境不成立，只對 resume 情境成立。另：審查任務書指出 resumeFromRunId 是同 session only，而 ADR §8 的 12 條已知限制、open_questions 的 12 條，**沒有任何一條**提到這個限制；§2.5 的表格反而把互動情境標成「✅ 這是唯一今天完整做得到的」，並把 pending_runs 摘要寫進「可重啟點任務書」——那份任務書的消費者正是 session 死後 `claude -r` 的那一跑。

[required_change]
①把 runId 的記錄點從 PreToolUse 改到 PostToolUse（那是唯一拿得到 runId 的地方），並據此重寫 §2.5 與 Step 3；②在 §8 新增一條已知限制，明文寫出 resumeFromRunId 的 same-session 邊界，並說明 session 死亡後 pending_runs 只能供**人工**重派、自動 resume 不成立；③Step 0 的量測項要改寫——`resumeFromRunId` 這個參數名今天就量得到（我已量到），真正待量的是「跨 session 還能不能用」與「Task ID(`w9kp0o1pe`) 與 runId(`wf_...`) 兩個識別的關係」。
```

#### §3.5.2 non-blocking（7 筆，逐字保全）

**SD-N01**

```text
事實面複驗全數為真，這點值得記下：A7（`[guardrail_cli<=750] tools/session_resume_planner.py: 749 （餘裕 1 行）`）、A8（`[guardrail_lib<=400] tools/lib/hook_wiring.py: 407 > 400 (+7)`，整支 check_loc_budget.py 今天 rc=1）、A10（settings.json:128 matcher 逐字 `Task|WebFetch|WebSearch|Agent|Workflow`）、A12（settings.json:217 逐字 `Read|Task|Grep|Glob|WebFetch|WebSearch|Bash|PowerShell`，確實缺 Agent|Workflow）——四筆皆與 ADR 所述逐字相符。ADR 編號 005 也正確（ADR 目錄現存最大號＝004）。
```

**SD-N02**

```text
ADR 點名的每一個符號都存在且行號對得上：context_budget_guard.py 的 NO_WINDOW:258、quiet_python:262、BLOCKING_TOOLS:292、blocking_reach_problems:295、CONSERVATIVE_WINDOW:307、WIDE_WINDOW:310、MEASURE_LABEL:337、classify_limit:502、latest_limit_event:546、unhandled_limit_event:679、may_block:825、announced_latches:871、write_resume_plan:947、arm_sentinel:1001、block_verdict:1169；planner 的 DEFAULT_AT_EXPR:278、MAX_PROBE_ATTEMPTS:284、RESET_SKEW_SECONDS:287、next_run_time:415、relay_problems:458、probe_quota:522、sentinel_decide:608。沒有任何一個是點名不存在的東西。
```

**SD-N03**

```text
reset_source 白名單複驗為 `("transcript-verbatim", "probe-verbatim", "operator")`（planner:476-477），與 ADR 所述一致。但 §3.3 宣稱加入 `endpoint-authoritative` 是「同一行內加，+0 行」有風險：該 tuple 已經 wrap 成兩行，再加一個 26 字元的字串很可能被 ruff 的行長判準逼出第三行 ⇒ planner 從 749 破 750。ADR 有給 fallback（先做 ADR-004 已登記的 session_endurance.py 抽離），但別把 +0 當定論，動工時實測。
```

**SD-N04**

```text
一道 ADR 沒提到但方向無害的鎖：Step 3 要擴大 PostToolUse matcher，而 test_check_hooks_liveness.py:1900 的 registration_shrink_problems 只在射程**縮小**時報紅（:1915-1916 對 `"*"` 直接 continue，:1917 只算 `pinned - got`）⇒ 擴大 matcher 不會轉紅，Step 3 安全。順帶一提 _REGISTRATION_BASELINE:1888 目前把 PreToolUse 的 context_budget_guard 釘在 `{Task, WebFetch, WebSearch}`，磁碟上已擴成五個名字，屬合法擴大。
```

**SD-N05**

```text
Step 6 的接線點比 ADR 想的更現成，值得重新評估工作量：AutoClaude 已有整個 `autoclaude/plugins/token_guard/` 套件（thresholds.py／policy.py／watcher.py）與 `core/services/auto_resume.py`、`_auto_resume_metrics.py`、`plugins/checkpoint/_token_halt.py`、`execution/halt_handler.py`、`execution/prompt_dispatcher.py`，全部含 compact_threshold_pct／halt_threshold_pct／resume_delay_minutes／max_auto_resumes 的既有實作（26 支檔命中）。ADR 只提到 config.py 與 prompt_dispatcher/halt_handler，沒提 token_guard 這個現成套件——那裡很可能就是 quota 軸最自然的家，也可能讓 M10「兩組門檻不共用預設物件」更容易做到。
```

**SD-N06**

```text
我同意 ADR 自評「撞線後 endpoint 還回不回得動」是最關鍵的未驗格（§8-2）。補一個可行且零成本的量法：不必製造撞線，在哨兵那一跑順手打一次並把 HTTP 狀態碼寫進 %TEMP%\autosdd_resume_log_*.jsonl，下次真撞線時痕跡自己會有答案。這與 ADR open_questions 第 1 條的建議一致。
```

**SD-N07**

```text
誠實劃界做得好、值得保留的部分：§2.10 對訴求 f 明說「只有結構結論、沒讀原始碼」；§8 的 12 條與 open_questions 的 12 條涵蓋了 statusLine 未實跑、token refresh 從未跑過、spend.enabled=False 與 99 筆 quota_spend 的矛盾、cap=2 與 TTL=180s 是「量出來的上界內挑的值」。這些自陳我逐條看過，沒有發現粉飾。我未獨立重打 /api/oauth/usage（那是 Architect 的取證面），所以對 §1.3 那幾個數字我不做背書也不做否定。
```

## §8 姊妹檔對照表（`DEF-101-587` 體例）

`docs/06_quality/` 的具名治理文件受體積守門（fail 262,144 bytes ／ warn 245,760 bytes，
上限來源＝Read 工具單次讀取上限，與缺陷帳本是同一條物理界線）。R81 第一批的輸出量
超過單檔容量（第一版實測 253,373 bytes，已越 warn 線），故拆成**三份姊妹檔**，
三份**都**登記進 `tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS`。
本檔＝`docs/06_quality/CrossPlatform_R81_Quota_Review.md`。

| 檔 | 承載 |
|---|---|
| `docs/06_quality/CrossPlatform_R81_Scan_Findings.md`（入口） | §0 誠實劃界／§1 九路全景／§2 scan:xplat 7 筆／§3 scan:subtraction 8 筆／§4 scan:skipped 12 筆／§5 scan:autoclaude-helm 10 筆 |
| `docs/06_quality/CrossPlatform_R81_Quota_Review.md` | §2 research:quota 12 筆／§3 ADR-XPLAT-005 的核心決策・實作步驟・開放問題／SA 與 SD 兩份 verdict 的逐筆 blocking 與 non-blocking |
| `docs/06_quality/CrossPlatform_R81_Ledger_Triage.md` | scan:ledger 的 34 筆未結列四類分流（A 已修好只差狀態欄／B 前提不成立／C 本輪做得完／D 本輪做不完須改派） |
| `docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md` | ADR 全文（狀態 `Proposed`；SA 給 REJECT、SD 給 APPROVE_WITH_CONDITIONS，11 筆 blocking 未收斂前不得視為已核准） |

## §9 這三份檔為何屬於「具名治理文件」

兩項義務同時成立，與 `CrossPlatform_R80_Scan_Findings.md` 的資格相同：

1. **體積守門**——複審者要判「R81 還有哪些缺口開著」就得讀完它，所以它承擔與缺陷帳本
   同等的可讀性義務；
2. **指針稽核**——它逐筆寫出「某發現的座標在某檔某行」的宣稱，而那些宣稱會過期。
