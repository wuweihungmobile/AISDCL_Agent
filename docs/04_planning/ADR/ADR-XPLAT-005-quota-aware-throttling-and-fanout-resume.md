> **落檔路徑**：`docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md`
> **編號依據**：`docs/04_planning/ADR/` 當回合實查（`Get-ChildItem`），現存最大號＝`ADR-XPLAT-004`，故本支為 **005**。
>
> 🔴 **落檔者的唯一一處逐字改動（照實登記，不做靜默修改）**：原文兩處寫 `cap=2`／`cap=0`（指**扇出併發上限**），與根層鎖 `tools/tests/test_doc_loc_baseline_freshness_r60.py::adr_measurement_problems` 的 LOC 詞彙（`\b(total|baseline|cap|violations)=(\d+)`）字面相撞——該鎖會拿它去比 `check_loc_budget.py --json` 的現查 `cap`（落檔當回合實測 20438）而判 ADR stale（落檔前實跑，兩處皆命中）。已改寫為 `fanout_cap=2`／`fanout_cap=0`，理由：**這本來就不是 LOC 預算**，而 `fanout_cap` 正是本 ADR §2 Step 2 自己給那個函式取的名字（`fanout_cap(pct) → int|None`）。刻意**不掛** `adr-measurement-historical:` 豁免——那個標記的語意是「有輪次歸屬的時代快照」，用在這裡是假話。除此之外，全文逐字保全。

# ADR-XPLAT-005：額度感知節流與扇出級續跑（quota-aware throttling & fan-out resume）

- **狀態**：Proposed（R81）
- **日期**：2026-08-08
- **取代／被取代**：不取代任何 ADR。**修正 ADR-XPLAT-004 的三處**：§2.1「reset 只能觀測不能算」的射程、§2.7「五小時怎麼度過」的答案、以及整支協定「救 session」這個單位選擇。ADR-004 的其餘部分（S1/S2 分流、憑證＝`NextRunTime`、狀態只有一個家、預防性武裝）**全部維持**。
- **回答的訴求**（🔴 **R81 收輪訂正過一次，見下方**）：a（額度水位一律用 %）／b（80% 少派 agent、95% 停止並準備喚醒）／**c（Token 盡量不要用盡，就要停止進行任務，記錄所有狀態）**／d（Token 若用盡時，下一輪 Reset 時要能喚起任務繼續執行）／e（同 session 同 token 池、單次上限 1 小時、reset 五小時，要如何度過；是否每 50 分鐘喚醒一次）／f（搜尋最新前沿 AI Agent 如何設計來參考）
  > 🔴 **R81 SA 一審 B3 的訂正（只訂正真的錯的那一個，並記下核對過程）**：落檔當時 c／d／e／f 的逐字原文在 `docs/` 全層搜尋不到（`Grep` 對 `訴求 [cdef]` 在 `docs/04_planning` 回 No matches found），本 ADR 對這四項的理解是從任務書與 ADR-XPLAT-004 §2.7 **反推**的。收輪時舵手提供了逐字原文（權威），逐字母核對結果：**只有 `c` 是真的錯位**——本 ADR 落檔時把「架構簡潔、分工清楚、不重複模組」當成 c，而那其實是 **Q2**；`d`／`e`／`f` 三項的對應**是對的**（措辭不同、指涉同一件事）。⇒ 本次只改 c，並把 §3 與 §6.4 兩處原本標「訴求 c」的標題改標 **Q2**。**刻意不順手「訂正」d/e/f**：照著一筆有一半不成立的 finding 去改，會製造一筆新的假事實（本 repo 已有「訂正註記逐字引述假話＝製造新假話」的判例）。逐字母核對表見 `docs/06_quality/CrossPlatform_R81_Review.md` §3。
  > 🔴 **c 的真正答案住在哪**：§2.4 的 **95% 閂鎖**那一段（`exit 2` 擋下所有扇出 ＋ 寫可重啟點任務書 ＋ 依額度種類分支）。它落檔時就寫好了，只是掛錯了字母 ⇒ **不是缺答案，是索引錯**。

---

## 1. 背景

### 1.1 一句話說清楚今天的病

**本 repo 有三套水位機制，全部量的是「這一次請求塞多滿」（分母＝context window）；沒有任何一套量得到「這個計費週期燒掉多少」（分母＝方案）。** 於是 R79／R80 連續兩輪撞額度時，每一道守衛都合法放行——撞線那一刻 context 水位只有約 18~20%。

三套機制的分母逐字（調研實查，本輪覆核路徑存在）：

| 機制 | 分母出處 | 逐字 |
| --- | --- | --- |
| `.claude/hooks/context_budget_guard.py` | context window | `:307 CONSERVATIVE_WINDOW = 200_000`／`:310 WIDE_WINDOW = 1_000_000` |
| `AutoClaude/autoclaude/utils/token_tracker.py` | context window | `:118-123 window = max(modelUsage[*].contextWindow)` |
| `AutoClaude/autoclaude/infra/adapters/sdk_executor_adapter.py` | context window | `:248-249 autoCompactThreshold` / `maxTokens` |

而 `context_budget_guard.py:437-439` 自己的 docstring 早就寫下了這個缺口——**知識在文件裡，判準不在程式裡**。這正是本 repo 反覆判過的形態。

### 1.2 R80 驗屍：協定救的**單位**錯了

R80 一輪內撞額度四次，**主迴圈一次都沒死**，死的是扇出（42／55／1 個 subagent）。續航協定的第五段（reset 後續跑）因此結構上永遠不會被觸發，**而且不該觸發**——session 還活著時再起一個 headless 回合只會互相干擾。

⇒ 兩條結論，本 ADR 以它們為地基：
1. **預設動作是 throttle（少派），不是 resume。** 四次撞線全是「扇出開太大」，不是「session 跑太久」。
2. **可續跑的單位要從 session 降到 workflow run**（記 runId 與未完成 agent 集合）。

### 1.3 本輪找到的那把尺

`GET https://api.anthropic.com/api/oauth/usage` 直接回傳 server 算好的 utilization。這把「訴求 a」從「應該有 API」變成「今天就有」。

**本輪 Architect 獨立複驗（第二個觀測者、不同時刻，非引述調研）**——腳本 `<scratchpad>\r81_arch_verify.py`，rc=0：

```
CRED_OK token_len=108 subscriptionType='team'
now       -> 2026-08-08T21:29:04.028488+08:00

=== FULL_HEADERS -> HTTP 200 ===
  five_hour: utilization=56.0 (float) resets_at='2026-08-08T13:40:00.815928+00:00'
  seven_day: utilization=32.0 (float) resets_at='2026-08-14T22:00:00.815956+00:00'
  limit kind='session'      percent=56 (int) severity='normal' is_active=True
  limit kind='weekly_all'   percent=32 (int) severity='normal' is_active=False
  limit kind='weekly_scoped' percent=0 (int) severity='normal' is_active=False
  spend: {'percent': 0, 'severity': 'normal', 'enabled': False}

=== MINIMAL_HEADERS(control) -> HTTP 200 ===
  （同上，數值一致）
```

這一次複驗**新增了五筆調研沒有的事實**，其中三筆直接改變設計：

| 編號 | 事實 | 對設計的影響 |
| --- | --- | --- |
| **A2** | **只帶 `Authorization` + `Content-Type` 也回 200**（對照組）⇒ `anthropic-beta: oauth-2025-04-20` 與 claude-cli 的 User-Agent **不是必要條件** | 關掉調研 honest_gap #3。取數器不必偽裝成 CLI，減一個會隨版本漂移的耦合面 |
| **A3** | **這把尺跑得很快**：21:19 調研讀到 `44.0`，21:29 我讀到 `56.0`（兩點之間 +12pp／10 分鐘） | 快取 TTL 不能長。🔴 **R81 落地訂正：本格原本由這兩點外推出一個每分鐘漂移率，再由它「推導」出 TTL 與餘裕倍數——那個推導已被自己的實作端證偽，故不留著當現行說法**（`context_budget_guard.py` 與 `quota_meter.py` 兩支檔逐字記載：視窗翻頁時 utilization 會**驟降 48pp**，這個量**非單調也非等速**，兩點外推不成立）。上面那兩個讀數仍是真的量測值，能支持的結論只有「它會動、而且動得夠快，快取不能長」這個**方向**，支持不了任何數字。TTL 的現行說法見 §2.4 |
| **A4** | **live payload 有 17 個頂層鍵**，含代號桶 `amber_ladder`／`iguana_necktie`／`nimbus_quill`／`tangelo`／`omelette_promotional`／`seven_day_cowork`／`seven_day_omelette`／`cinder_cove`；而 `claude.exe` 內嵌的名單 `bsb=[...]` 只有 **8** 個 | **禁止寫死桶名清單**。schema 正在長，寫死名單的失明是靜默的（新桶滿了而我們看不到） |
| **A5** | `resets_at` 有次秒級抖動（`13:39:59.297723` vs `13:40:00.815928`，皆 UTC）⇒ 它是「now + 剩餘」算出來的 | 穩定到**分鐘**，但**不得跨呼叫做相等比較**（否則每次都判「reset 變了」而重排） |
| **A6** | 本帳號 `spend.enabled=False`／`extra_usage.user_disabled=True`，但 R80 逐字稿分類出 **99 筆** `quota_spend` | **兩者不一致，未解**。⇒ 本 ADR 不敢用 `spend` 欄位取代既有的字串分類器，兩條並存（見 §2.6） |

### 1.4 另外兩筆本輪實測的**結構約束**（決定新程式碼住哪）

- **A7**：`tools/session_resume_planner.py` ＝ **749／750**（`guardrail_cli` tier），**餘裕 1 行**。逐字：`[guardrail_cli<=750] tools/session_resume_planner.py: 749 （餘裕 1 行）`。⇒ 它**結構上不能吸收任何新功能**。這不是偏好，是量出來的。
- **A8**：`AutoClaude/tools/check_loc_budget.py` 在**乾淨工作樹**上當回合 **rc=1**：`[ROOT-TOOLS] [guardrail_lib<=400] tools/lib/hook_wiring.py: 407 > 400 (+7)`。這是 R80 留下的既有紅，**不是本 ADR 造成的**，但它是動工前置（見 §7 Step 0）。
- **A9**：`.claude/hooks/` **不在任何 LOC 預算的掃描面內**（`ROOT_TOOLS_ROOT = PROJECT_ROOT.parent / "tools"`，且 `SPECIAL_FILES` 逐列讀過無此檔）⇒ `context_budget_guard.py` 有成長空間。**這既是機會也是風險**（見 §8-8）。

---

## 2. 決策

> **一句話**：把水位拆成**兩條互不替代的軸**——context（分母＝window，沿用 75/90；R92 訂正：已改 **84/94**，見 ADR-XPLAT-008）與 quota（分母＝方案，新增 80/95）；quota 的值**只從 server 拿**、絕不反推；80% 那道**真的擋掉扇出**、95% 那道**真的收斂並依額度種類分三種動作**；可續跑的單位由 session 降到 **workflow run**。

### 2.1 訴求 a：分母怎麼定——**不定，因為不需要**

**答案：本 repo 不再擁有「分母」這個概念。** server 依帳號方案自己算 utilization 並回百分比，所以：

- 換帳號、換方案、換機器 ⇒ **零常數要改**（這正是掌舵者「啟動帳號不同」那句話要的東西）。
- 不必知道 window 是 200K 還是 1M。
- 呼叫本身**不是模型推論** ⇒ 不吃額度、不進 5 小時視窗。

**多點校準：不做，而且要明文停止。** 理由不是「還沒做」，是**那個等式根本不成立**：
- 該池是**跨產品共享**（claude.ai／Desktop／CLI 同一個帳號級池）⇒ 本機逐字稿的 token 加總在結構上不完整。
- 本輪 A3 是這件事的直接證據：**10 分鐘內漲了 12pp**，而同期間本 session 的 usage 遠不足以解釋它。
- 訂閱模式**完全不走**傳統 per-minute token 桶（調研實測：`anthropic-ratelimit-tokens-remaining` 在 `claude.exe` 內 count=**0**）。

⇒ R80 那道「四個候選分母都湊得出 78%」的謎題是**偽命題**：78% 是 server 用 unified 限額桶算好丟回來的值，跟本機 token 加總沒有函數關係。**當某個數字有權威來源時，反推它的口徑是零價值的工作**——這條判準要進 CLAUDE.md。

**拿不到時的 fallback 階梯（四級，最後一級是「不知道」而不是一個數字）**：

| 級 | 來源 | 值的性質 | 動作 |
| --- | --- | --- | --- |
| L1 | `GET /api/oauth/usage` | 權威、0..100、含 `resets_at` | 依門檻階梯 |
| L2 | statusLine 快取檔（互動 TUI 寫的） | **同樣是 server 算好的**，只是管道不同、可能過期 | 依門檻階梯，訊息標示 `stale=<秒>` |
| L3 | **逐字稿撞線偵測**（既有 `unhandled_limit_event`，離線、零 token、永遠可用） | **只給下界**：已撞線且未復原 ⇒ 水位下界 **100%** | 走既有續航鏈 |
| L4 | 全部失效 | **量不到** | **不節流、不 halt**，寫 `degraded` 痕跡並出聲一次（閂鎖） |

🔴 **L4 刻意不填數字。** 這是本 ADR 對設計約束 1 最直接的回應：離線可推得的唯一誠實下界是 L3 的二元判斷（撞了＝100%／沒撞＝未知）。0 與 100 之間的任何值在離線狀態下都是猜的，而猜出來的水位會讓門檻成立、百分比印得出來，只是**它在錯的水位上動作**（R79 判例的同型）。

🔴 **L4 為什麼是「不節流」而不是「節流」**：斷網時自動把併發降到 2，會讓「網路壞了」與「額度真的滿了」**外觀完全相同**，而且是靜默的。既有判例同形——`block_verdict()` 的 `may_block(source)` 逐字：「分母是猜的就不擋——猜錯會在真實 18% 把工具鎖死」。

🔴 **R81 落地訂正（本節此前用「L3 這層地板永遠在」替 L4 不節流辯護，而那句話在寫下時是假的，故不留著當現行說法）**——複審實查的三件事：

| 級 | 落地當時的實況 | R81 收斂後 |
| --- | --- | --- |
| L1 | 有，但**只有快取新鮮時才到得了**：唯一的取數呼叫點在「已經量不到」那條支線上，且 fire-and-forget 不等它 ⇒ 本次仍判量不到 | 扇出路徑上**同步**量一次（有界逾時 4 秒、每 TTL 至多一次），量到才判 |
| L2 | **零 reader**（statusLine 快取從頭到尾沒有任何消費者） | 仍是零 reader。**這一級不存在**，本表不再把它算進階梯——留著會讓「四級」這個數字自己變成假話（要補是另一件事，見 §8） |
| L3 | **零呼叫**：`unhandled_limit_event()` 的消費者只有哨兵與測試，`quota_gate()` 一次都沒叫過它 ⇒ 這層「永遠在」的地板**只存在於本文件裡** | 真的接上（`quota_floor_reading()`）：撞線且未復原 ⇒ 下界 100% ⇒ 落進 halt |
| L4 | 是唯一實際會走到的那一級，於是**「量不到」等於對任意規模的扇出全數放行**（探針實測：快取過期 600s／額度 99% ⇒ 42 次 `Agent` 派發放行 42、擋下 0） | 只有 L1 與 L3 都拿不到證據時才走到，且**方向刻意不改**（見上一段） |

**教訓的形狀**（不是「寫錯一句話」）：這段辯護詞把一個**尚未接線的機制**當成既成事實去替另一個決策背書 ⇒ 兩件事同時看起來有人守，實際上一件都沒有。本 repo 判過的「機制蓋好沒接電」在這裡是**用來論證別的東西**，比單純沒接電更難看見。

### 2.2 單位正規化：入口就做掉（否則差 100 倍）

同一個量在四條通道有**四種寫法**，其中兩種在**同一份 payload 裡**（本輪 A1 新發現）：

| 通道 | 欄位 | 型別／範圍 | 證據 |
| --- | --- | --- | --- |
| REST `/api/oauth/usage` | `five_hour.utilization` | **float 0..100**（`56.0`） | 本輪 A1 |
| 同一份 REST payload | `limits[].percent` | **int 0..100**（`56`） | 本輪 A1 ← 同一次呼叫、兩種型別 |
| headless stream-json | `rate_limit_event.utilization` | **float 0..1**（`0.3`） | 調研 S1-04 |
| statusLine schema | `rate_limits.five_hour.used_percentage` | 0..100（**未實測**，見 §8-1） | 調研 S1-06（二進位自述） |

**決策**：取數層一律正規化成 **0..100 的 float**，**每個 adapter 在自己的入口寫死該通道的單位**，內部只有一種表示。時間一律轉 aware datetime（沿用 R80「不得持久化 naive 本地時間戳」判準）。

**為什麼這條必須有機械物**：`0.3` 拿去比 `80` 永遠不觸發 ⇒ **閘門恆綠**；`30.0` 拿去比 `0.8` 永遠觸發 ⇒ **閘門恆紅**。兩個方向都在「機制蓋好、rc 是 0」的外觀下失效，沒有任何東西會轉紅。這是 R79「量測器符號相反」的同型，只是這次是**倍率**。

### 2.3 桶的列舉：**禁止寫死名單**，且**是三條線不是兩條**

本輪 A4 實測：live payload 17 個頂層鍵，`claude.exe` 內嵌名單只有 8 個 ⇒ schema 正在長。

**判定層只消費 `limits[]` 陣列**（那是 server 自己的「什麼在限制你」投影，也是 UI 那兩格的資料源），取 **`max(percent)`**，並**記錄是哪一個 `kind` 貢獻了 max**。

🔴 **刻意不用 `is_active` 篩**：本輪實測 `session`(56%) 為 True、`weekly_all`(32%) 為 False ⇒ 它看起來是「當前最緊的那一個」而不是「這條線有沒有在生效」。**拿一個語意未知的欄位去篩掉一條線，就是在製造一個沒有人看得見的失明面。** 取 max 的錯誤方向是「太早節流」，那是可接受的方向。

🔴 **本 ADR 最重要的一個新發現：額度不是兩條線，是三條，而三條的「等」的語意完全不同。**
ADR-004 §2.2 分了 S1（session）與 S2（spend）兩條。加上權威 endpoint 之後，中間那條浮出來了：

| kind | reset 距離 | 「等」有沒有意義 | 動作 |
| --- | --- | --- | --- |
| `session` / `five_hour` | 中位 ~60 分、實測最長 4.2h（ADR-004 §2.7 量測） | ✅ 有 | 收斂 → 武裝 schtasks 到 `resets_at`+skew → 續跑 |
| **`weekly_all` / `seven_day`** | **最長 7 天**（本輪實測 `2026-08-14T22:00Z`，距當下 6 天） | 🔴 **幾乎沒有** | **不排程**。通知人 ＋ 建議降扇出／切小模型／改做不吃額度的工作 |
| `spend` / `extra_usage.spend_limit_reached` | **沒有 reset** | ❌ 完全沒有 | 只有通知人去提額（沿用既有 `LIMIT_SPEND` 分支） |

**為什麼這是設計洞不是細節**：訴求 b 的「95% ⇒ 停止、準備喚醒」如果套在**週額度 95%**上，會排一支**七天後**才響的 schtasks，而那段期間機器上什麼都不會發生、痕跡卻全綠。那與 R59 事故同形。⇒ **95% 的動作必須先問「是哪一條線」。**

### 2.4 訴求 b：兩道閘的**動作**（不是印字）

#### 門檻與階梯

| quota 水位 | 名稱 | 扇出上限 | 其他動作 |
| --- | --- | --- | --- |
| < 80 | normal | 無上限（＝現況） | 無 |
| 80 ≤ q < 95 | **throttle** | **cap = 2** | 訊息說明還剩多少、哪一條線最緊 |
| q ≥ 95 | **halt** | **cap = 0**（全擋） | 一次性閂鎖：寫任務書 ＋ 依 kind 分支（§2.3）＋ 武裝／通知 |

- **fanout_cap=2 是挑的，不是量出來的——照實寫。** 它的**上界是量出來的**：R80 撞線當下的扇出規模實測為 **42／55／1**，cap 必須遠小於它們。2 落在極寬鬆的一側。**機械物守的是方向不是數值**：cap 必須隨 quota 單調不增，且 q≥95 時**必須恰為 0**（見 §5）。可用環境變數覆寫，覆寫值一樣受方向鎖。
- **TTL = 180 秒——它是「挑的」，沒有推導。** 🔴 **R81 落地訂正（本格原記載由 A3 兩點外推出一個漂移率、再由它算出跨越 80→95 所需分鐘數與餘裕倍數，那條推導鏈已被實作端證偽，故不留著當現行說法）**：第三個量測點顯示這個量在視窗翻頁時**驟降 48pp** ⇒ **非單調、在邊界不連續**，任何兩點外推（以及任何「乘上安全倍數」的變體）都不成立。可以說的只有方向：A3 那兩個讀數證明它動得夠快，所以快取不能長。**重量入口＝`python tools/lib/quota_meter.py --watch <秒>`**（不另開探針檔）——要為 TTL 提出一個有依據的值，得先在那裡量出這個量的分佈，而不是再算一次外推。
  🔴 **R81 同時改變了 TTL 的角色**（與 §2.1 的落地訂正連動）：過期**不再等於「本次放行」**。過期只是「這個值不能用了」，接著會在扇出路徑上**同步**重量一次（有界逾時 4 秒、每 TTL 至多一次）。⇒ 把 TTL 調錯的代價因此從「靜默全放行」降成「多量幾次／少量幾次」，這是刻意把一個猜出來的數字放到後果較輕的位置上。

#### 載體一：互動 session（Claude Code ＋ 舵手模型）

**80% 那道怎麼「真的」少派 agent**：

- **註冊面已經在射程內，不必新增**（本輪 A10 實測）：`.claude/settings.json:128` 的 PreToolUse matcher 已是 `Task|WebFetch|WebSearch|Agent|Workflow`，且 `context_budget_guard.py:292` 的 `BLOCKING_TOOLS` 五個名字一致。**扇出的每一次派發，今天就已經會經過這支 hook。**
- **判定**：hook 讀**快取檔**（純 stdlib json，**零網路**）＋讀**扇出帳**算派發率，超過 cap ⇒ `exit 2`。**那次工具呼叫不會發生**——這是機械的用量速率下降，不是給模型看的一行字。
  🔴 **R81 落地訂正（本格原記載的判定量與實作不符，故不留著當現行說法）**：原設計要數的是「in-flight 併發數」，實作階段量到**那個量在本 harness 上恆讀 ≈0**——`Workflow` 47/47 是「launched in background」，該次呼叫在扇出開始之前就返回、PostToolUse 當場觸發、completed 立刻追平 dispatched ⇒ cap 永遠綁不到。落地版改為 **per-account 滾動視窗的派發率**（`live_dispatches()`，視窗 `FANOUT_WINDOW_SECONDS = 300`，`try` − `undo`）。連帶好處有二：不需要 `completed` ⇒ **不必動 PostToolUse 的註冊面**（下一格連同作廢）；被擋下的呼叫寫 `undo` 沖掉自己的 `try` ⇒ 不會留下永遠等不到 completed 的佔位（原設計自帶的 SA-B6 洩漏）。且它更貼近被限制的資源：**額度是燒用量，不是併發數**。
- **刷新**：🔴 **R81 落地訂正（本格原記載的形態是 fire-and-forget、不等它、本次仍用舊值判定，該形態已被實測證明會製造上面 §2.1 那個全放行缺口，故不留著當現行說法）**。現行：快取拿不到可用值時，**在扇出路徑上同步量一次**（`refresh_quota_blocking()`，逾時 4 秒），量到才判。三個條件同時成立才碰網路——**扇出型工具** ＋ **已經量不到** ＋ **本 TTL 視窗還沒有人量過**（`claim_refresh_slot()`）。代價量過了：端點 RTT 實測 0.33／0.36／0.41 秒。
  原設計那條「網路呼叫永遠不在 hook 的關鍵路徑上」的取捨**被推翻了一半**，誠實劃界：仍然成立的是它真正的射程——收斂型工具（讀檔／寫檔／跑 git）一次都碰不到這條路，所以「給每一次工具呼叫加上網路延遲」那個被否決的形態並沒有回來。不成立的是把它推到「連扇出也不准等」：那換來的是一個安靜的全放行。
- 🔴 **本輪 A12 找到的缺口已隨上一格作廢**：它是「Pre/Post 配對數在飛的扇出」那個設計的前置動作，而該設計沒有落地 ⇒ **PostToolUse 的 matcher 本 ADR 不再要求改動**。原記載把它列為 Step 3 的第一個動作，照著做會去補一個沒有消費者的計數面。
- 🔴 **80% 這道的射程，誠實劃界（R81 實測，三段各自量過）**：擋得到①**主迴圈的派發**、②**被派出去的人再往下派**（subagent 逐字稿內 `PreToolUse:` 命中 136 次 ⇒ 它們自己的每一次工具呼叫都跑本 hook）；**擋不到**③**一個已經啟動的 `Workflow` 在內部生出那 42 個 agent**——那一刻**沒有任何 hook 會被叫到**（`autosdd_sentinel_boot_*.log` 19 支無一支 sid 像 subagent ⇒ SessionStart 對 workflow 內部 agent 一次都沒觸發過）。⇒ 既然一次 `Workflow` 啟動是**事後無法界住**的扇出，節流帶唯一誠實的處置是**不讓它啟動**（`UNBOUNDED_FANOUT_TOOLS = ("Workflow",)`）。這不是「擋不到所以放棄」，是把量到的失明面換成一條擋得住的政策。

**95% 那道怎麼「真的」收斂並武裝**（一次性閂鎖，沿用既有 `announced_latches`）：

1. `exit 2` 擋下所有扇出（fanout_cap=0）；
2. 寫可重啟點任務書（既有 `write_resume_plan()`），**任務書內含未完成 run 清單**（§2.5）；
3. 依 §2.3 的 kind 分支：`session` ⇒ detached 外呼 planner 武裝 schtasks；`weekly_*`／`spend` ⇒ **不排程**，只寫任務書＋大聲通知；
   🔴 **R81 落地訂正（本格原記載的喚醒時刻與實作不符）**：原設計是把 schtasks 直接排到 endpoint 的 `resets_at`＋skew。落地版走的是**既有的 `--arm-sentinel`**，喚醒時刻＝**`now + SENTINEL_INTERVAL_SECONDS`（900 秒）**，之後由巡邏在**真的撞線時**依觀測值重排。理由是語意的而非省事：**95% 這一刻還沒撞線**（那正是本 ADR 的重點——不要走到撞線），而 `resets_at` 描述的是「額度什麼時候回來」，把一個**還沒發生的**停機排到那個時刻，等於預設它一定會撞。`--arm-sentinel` 是**唯一**不需要「已觀測 reset 時刻」就能武裝的入口，且巡邏本身零 token。**代價要說清楚**：喚醒點因此不是端點的精確時刻，而是一個 900 秒的巡邏節拍；§2.7 的優先序（權威 → 觀測 → 拒絕武裝）管的是**重排**那一步，不是這一步。
   🔴 **分支由「reset 有多遠」決定，不由桶名決定**（`reset_branch()`，門檻 `RESET_ARM_HORIZON_SECONDS = 6h`）：拿不到／不可解析／naive 無 offset ⇒ `escalate`；> 6h（週線、七天後）⇒ `notify`，**刻意不排程**；≤ 6h ⇒ `arm`。
4. **憑證＝`NextRunTime` 這個值**（不是 rc）——`relay_problems()` 既有的取證閘原封不動生效。

#### 載體二：AutoClaude Playbook

- **新 port（🔴 待建，本 ADR 落地前磁碟上不存在）**：`autoclaude/core/ports/` 下新增 quota_meter.py（`QuotaMeterPort`，預設回「量不到」）。
- **新 adapter（🔴 待建，同上）**：`autoclaude/infra/adapters/` 下新增 file_quota_meter_adapter.py — **讀快取檔，不做網路、不 import harness code**。方向正確：套件依賴的是**檔案契約**，不是 `tools/` 或 `.claude/`（這正是 ADR-004 §4 禁止的方向）。檔不在／過期 ⇒ 回「量不到」。
- **新設定欄位**：`token_guard.quota_throttle_pct = 80` / `token_guard.quota_halt_pct = 95`。
  🔴 **絕對不複用 `compact_threshold_pct`(80) / `halt_threshold_pct`(90)**——它們量的是 context，**數字剛好接近才更危險**：會讓人以為額度已經有人守了。「同名不同義」是本 repo 反覆判過的形態。既有校驗 `halt > compact` 照抄成 `quota_halt > quota_throttle`。
- **80% 的動作＝不派下一個 step**（延後到下一次量測），接在既有的**步驟邊界**（`prompt_dispatcher.py` 已是這個形狀：per-line 觀測、旗標在步驟間生效）。
  🔴 **subagent 層級的節流由互動側那道 hook 代勞，AutoClaude 側不重複實作**——記憶 [[claude-code-quota-and-silent-schtasks]] 已實證 **headless `claude -p` 完整跑本 repo 的 hooks**（SessionStart 與 PreToolUse 兩個探針）。⇒ AutoClaude 驅動的那個 CLI 內部的扇出，會被同一支 `context_budget_guard.py` 擋。**一個機械物守兩個載體**，這是訴求 c 在本 ADR 的具體兌現。
- **95% 的動作＝走既有 halt 路徑**（存 checkpoint ＋ `scheduled_resume_at`），但**恢復時刻改用 endpoint 的 `resets_at`**，取代固定的 `resume_delay_minutes=30`。固定 30 分鐘正是 ADR-004 §2.1 判過的「把偶然事實寫成常數」——實測 episode 窗 min 0.5 分／median 59.8 分／max 253.2 分，30 分鐘對其中任何一段都不對。既有 `auto_resume`／`max_auto_resumes` 骨架直接複用，**一行都不必新寫**。

### 2.5 設計約束 3：可續跑單位由 session 降到 **workflow run**

**帳與狀態要分開**（否則會違反 ADR-004 §2.4「狀態只有一個家」）：

| 面 | 住哪 | 形態 | 理由 |
| --- | --- | --- | --- |
| **派發帳**（telemetry，餵節流） | `%TEMP%\autosdd_quota_dispatch.jsonl` | append-only，一行一次 `try`／`undo` | 與既有 `autosdd_resume_log_*.jsonl` 同一個家族、同一個目錄、同一種取證紀律（沒觸發＝檔案不會長大，是可偵測的） |
| **扇出死者清單**（telemetry，餵續跑） | `%TEMP%\autosdd_fanout_<sid>.json` | 撞線那一刻寫一次的快照 | 「哪個 run、哪幾個 agent 被打死」只在撞線當下查得到（agent 逐字稿跑的當下就在寫），事後重建不出來 |
| **續航狀態**（state） | 既有 relay JSON 區塊（任務書內） | 只在 95% 閂鎖那一刻寫入 `pending_runs` **摘要** | ADR-004 §2.4 不變：狀態仍只有一個家；帳是餵給它的原料，不是第二個狀態家 |

🔴 **R81 落地訂正（本表原記載是「一份帳、兩個消費者」，實作是兩份各自獨立的帳，故不留著當現行說法）**：兩者的**單位不同**，合不起來。派發帳是 **per-account 且不帶 sid**（額度是單一池，per-sid 的帳等於 N 個載體各拿一份 cap）；死者清單**必須** per-sid（要回答的是「這個 session 底下哪幾個 agent 死了」）。硬併成一份，兩個問題都會答錯。

**runId 從哪來、誰去按 `resumeFromRunId`**：

- **記錄**：節流側只記 `try`／`undo`（見上）。續跑側**不靠 Pre/Post 配對**，而是撞線當下由 `snapshot_fanout()` 直接掃 session 目錄：`<sid>/subagents/workflows/<runId>/agent-*.jsonl` 逐支判「是不是停在額度撞線上」。
  🔴 **為什麼不從 hook payload 取 `runId`**（R81 實測）：`runId` 在 PreToolUse 的 payload 裡**拿不到**，且 workflow 的總結檔 `<sid>/workflows/wf_<runId>.json` **只有跑完才寫** ⇒ 撞線當下它不存在。走目錄名是唯一在撞線當下可得的來源，這是該函式刻意不讀那支 json 的原因。
- **誰按**，三種載體誠實劃界：

| 情境 | 誰按 | 今天做得到嗎 |
| --- | --- | --- |
| 有人在的互動 session | 任務書列出未完成 run，**人或舵手模型**照著按 | ✅ 這是唯一今天完整做得到的 |
| 無人看管 | **AutoClaude**（帶目標任務、有 Token Guard 與自演化） | ❌ 需要 §2.4 載體二先落地（今日零落地），**且即使落地了也按不到 `resumeFromRunId`**——它是 same-session only，見 §8-5。無人看管那條路只能「拿死者清單重新派一次新的 run」 |
| headless `claude -p -r` 那一跑 | **不要讓它按** | ❌ 它做不了「該重派哪些」的判斷（記憶 [[unattended-helm-is-autoclaude]]）。它只負責留痕與通知 |

🔴 **這一段有一個必須先實測的前提**：`Workflow` 工具的 payload 裡到底有沒有 run 識別欄位、`resumeFromRunId` 的確切參數名是什麼，**本 ADR 沒有驗過**（唯讀階段不能真跑一個 Workflow）。⇒ Step 0 的第一個動作就是量它；**量不到就只記 `tool_name`＋`description`＋時間戳**（那仍足以讓人手動重派），**不准照著猜的欄位名寫實作**。

### 2.6 額度的三條線與既有分類器：**兩條並存，不互相取代**

既有 `guard.classify_limit()` 讀的是**人類可讀的錯誤字串**；新的 endpoint 給的是**結構化欄位**。直覺會說「換掉舊的」，但本輪 A6 否決了這件事：本帳號 `spend.enabled=False`，而 R80 逐字稿分類出 **99 筆** `quota_spend`。**兩者不一致，成因未解。**

⇒ **決策**：
- **預警**（撞線前）走 endpoint（精確、可分 kind）。
- **事後判讀**（已撞線）仍走 `classify_limit()`（它有 R80 量出來的 0.0% 假陽性紀錄，且離線可用）。
- 兩者**都不准**被對方的沉默當成放行理由。矛盾時記進痕跡並**取較保守的一方**。

### 2.7 reset 時刻：優先序改為「權威 → 觀測 → 拒絕武裝」

ADR-004 §2.1「reset 只能觀測不能算」對**從錯誤訊息回推**這條路仍然完全成立，但它被當成了**通則**，於是整輪投資押在「解析 `resets 9am` 字面 ＋ 猜時區 ＋ 解不出就拒絕武裝」這條又脆又貴的路上（R80 還為此被 act 抓到兩個時區翻面的紅）。

**權威通道存在時，那些問題整組消失**：不必解字面、不必猜時區（值自帶 offset）、而且**在撞線之前就拿得到**——現行鏈條只有撞線**之後**才有訊息可解，而那正是沒有人還在跑指令的時刻。

新優先序：

1. **`endpoint-authoritative`**：endpoint 的 `resets_at`（秒級、帶 offset、撞線前可得）
2. `transcript-verbatim`／`probe-verbatim`：既有字面解析（離線／無網路 fallback，**保留**）
3. **拒絕武裝**（維持不變，**禁止**退回固定 5 小時）

實作面：`relay_problems()` 的 `reset_source` 白名單（`planner:476-477`，現為 `("transcript-verbatim", "probe-verbatim", "operator")`）加入 `"endpoint-authoritative"`。
🔴 **A5 的推論**：`resets_at` 跨呼叫有次秒級抖動 ⇒ **比較與去重一律以「截到分鐘」為準**，不得做字串相等比較，否則每次巡邏都會判「reset 變了」而無謂重排。

`tools/probe/reset_window_distribution.py` **保留**為歷史語料分析工具（ADR-004 §2.7 的取證規則靠它），但**不再是排程時刻的來源**。

### 2.8 訴求 e：五小時怎麼度過？是不是每 50 分鐘喚醒一次？

**建議：不採用「每 50 分鐘喚醒」；巡邏維持 900 秒；而且——這個問題的正確答案是「不要走到需要度過五小時」。**

**① 先推翻前提（ADR-004 §2.7 已量，本輪不重量、直接引用）**：沒有「五小時」這回事。15 個相異撞線 episode 的實際停機：**min 0.5 分／median 59.8 分／max 253.2 分（4.2 小時）**，**超過 5 小時者 0 個**。要度過的是一個**未知長度的窗**。

**② 「每 50 分鐘」不採用，四個理由（前三個是 ADR-004 §2.7 的，第四個是本輪新增）**：

1. **50 這個數字是別的方案的約束外溢**——來自 `ScheduleWakeup` 的 `delaySeconds` clamp 上限 3600 秒。schtasks 沒有這個上限，照抄等於照抄一個已被否決方案的參數。
2. **它把最壞死等從 15 分放大到 50 分，換不到任何東西**——巡邏是**零 token**（讀一次逐字稿＋一次 `stat`），這一側沒有需要權衡的量。且 15 個 episode 裡 **7 個窗 ≤50 分鐘** ⇒ 50 分鐘間隔會讓那 7 個窗**整個沒醒過**。
3. **「還需要有剩餘 Token 才能做」這個顧慮正是 50 分鐘方案的致命傷**——`ScheduleWakeup` 每醒一次是一個模型回合（實測 ~20.7 萬 tokens），額度斷電期間它自己也會被擋，**結構上撐不過斷電**。哨兵醒來只讀檔，斷電期間照樣跑得動。
4. **🔴 本輪新增**：有了 endpoint 的**精確 `resets_at`（撞線前就拿得到）**，「一直醒來看看好了沒」這個行為的理由消失了。巡邏的角色從「發現 reset」降級為「順手刷新快取 ＋ 兜底發現撞線」，而撞線本身現在可以**在發生之前**被預測（水位 ≥95% 時已經在武裝了）。

**③ 本 ADR 對訴求 e 最重要的回答**：問題預設了「會撞線，然後要等」。有了 80%／95% 兩道，正確目標是**根本不要撞到 100%**——在 95% 主動收斂並武裝到一個**已知時刻**，把「被動等一個未知長度的窗」換成「主動停手、等一個查得到的時刻」。**降低撞線頻率的價值遠大於縮短等待。**

**④ 巡邏這件事本輪的唯一變動**：每次巡邏**順手刷新 quota 快取**（多一次 HTTP，仍是零 token）。這讓 `AUTOSDD_SENTINEL_OFF` 關掉哨兵時，快取新鮮度也一起降級——**必須在訊息裡說出來**，否則會出現「哨兵關了但水位看起來還很新」的假綠。

### 2.9 訴求 d：無人看管撐過 reset

ADR-004 的 L0~L3 分層**全部維持**，本 ADR 只換三個零件：

| 零件 | 舊 | 新 | 收益 |
| --- | --- | --- | --- |
| 觸發時刻來源 | 撞線後解析錯誤字串 | **撞線前**的 `resets_at`（§2.7） | 不必猜時區；不必等撞線才有資訊 |
| 「額度回來了沒」 | `claude -p` 探針，**實測 31,847 tokens／次** | **先打 endpoint（零 token）**，失敗才回落探針 | 探測預算上界 5×31,847≈16 萬 tokens 幾乎歸零 |
| 預設動作 | resume（救 session） | **throttle（救扇出）**；resume 降為 `session` kind 的第二動作 | 對上 R80 驗屍：主迴圈從不死 |

🔴 **回落路徑必須保留**：endpoint 也會失效（401／斷網／改版），fail-closed 的方向不變。`MAX_PROBE_ATTEMPTS` 留給回落路徑。

🔴 **OAuth token 4 小時到期是這條路的真實單點失效**（調研 S1-08；本輪覆核：`expiresAt -> 2026-08-09T01:19:39+08:00`，距當回合約 **3.8 小時**）。互動 session 活著時 Claude Code 會自己 refresh 並回寫該檔；但**撞線後 session 死掉、排程器獨自醒來那條路上沒有人在 refresh**。⇒ 見 §7 Step 8 與 §8-4：**最低限度必須把「token 過期」與「額度真的沒回來」在痕跡裡分開記**，否則排程器會把認證失敗誤判成額度未恢復而一直等下去——那與 R80 哨兵整晚失明是同一個形狀。

### 2.10 訴求 f：前沿 Agent 框架怎麼做

🔴 **誠實劃界**：調研只做了一次概略搜尋（honest_gap #9），**沒有逐一讀原始碼或官方文件**。以下只寫**從本輪量測直接推得的結構結論**，不寫二手轉述。

**唯一但關鍵的結論：業界主流的「指數退避 ＋ 抖動」在本場景結構上是錯的工具。**

- 那些框架處理的是 **per-request 429**（伺服器說「你現在太快」）⇒ 退避重試是對的：等一下再送就會過。
- 本 repo 面對的是 **per-account 週期額度**（伺服器說「你這個計費週期用完了」）⇒ **退避無效**：等 30 秒、60 秒、120 秒都一樣滿，只是把探測預算燒光。
- 這不是猜的：訂閱模式**完全不走**傳統 token 桶（`anthropic-ratelimit-tokens-remaining` 在 `claude.exe` 內 count=**0**，走的是 `anthropic-ratelimit-unified-{5h,7d,...}-utilization` 這一族）。
- ⇒ 正確的工具組是：**①事前節流（降用量速率）＋ ②等一個已知時刻（不是等一個退避序列）＋ ③工作單位級的續跑（checkpoint/resume）**。其中 ③ 與 LangGraph 那類的 checkpoint 續跑同型，而 ①② 是訂閱制特有的、業界通用模式裡沒有的。

⇒ **具體建議**：不要為了「向業界看齊」引入退避重試層。真的要補功課，補在 ③（工作單位級 checkpoint 的粒度與冪等性），那才是我們比業界弱的地方。**這一段是背景不是決策依據**（見 §8-9）。

---

## 3. 架構歸屬：新東西住哪、哪些該合併（**Q2**，非訴求 c——見檔頭訂正）

### 3.1 決策表

| 職責 | 住哪 | 新增／既有 | 為什麼是這裡 |
| --- | --- | --- | --- |
| **取數 ＋ 單位正規化 ＋ 快取寫入**（唯一會碰網路的地方） | **`tools/lib/quota_meter.py`（新，tier `guardrail_lib` ≤400）** | 新 | 見 §3.2 |
| **判讀**（門檻階梯、cap 判定、扇出帳解析）——純函式、零網路 | `.claude/hooks/context_budget_guard.py` | 既有 | 逐字稿掃描與撞線判讀已經在那裡；它**只能被 import、不能 import**（`runpy.run_path` 起、`sys.path` 不含 `tools/`）⇒ 判讀知識反過來寫會有兩個家。且本輪 A9 實測它不在任何 LOC 預算面內，有空間 |
| **互動側動作**（deny／閂鎖／起 detached） | 同上 | 既有 | 註冊面已在射程（A10），不必新增條目 |
| **排程／續跑編排**（武裝、`NextRunTime` 取證、探測回落） | `tools/session_resume_planner.py` | 既有，**淨行數必須 ≤ 0** | A7 實測餘裕 **1 行**。⇒ 見 §3.3 |
| **AutoClaude 消費** | `core/ports/` 下 quota_meter.py ＋ `infra/adapters/` 下 file_quota_meter_adapter.py | 🔴 **待建**（2 支，走 Plugin/Port SOP） | 套件依賴**檔案契約**不依賴 harness code，方向與 ADR-004 §4 一致 |
| **快取寫入器（免費的那一個）** | `~/.claude/statusline_quota.py`（使用者層，非 repo） | 新（可選） | 互動 TUI 每次 render 都會餵它一份 JSON ⇒ 零額外成本的水位快取。**射程誠實劃界：只在有人跑互動 session 時更新，不得當無人看管期間的權威源** |

### 3.2 為什麼**不得不**新開 `tools/lib/quota_meter.py`（三個結構理由，都是量出來的）

本 repo 判過「護欄層自我增殖是最大缺陷來源」，所以新開檔要辯護。三個理由：

1. **planner 塞不下**（A7：749／750，餘裕 1 行）。這是硬牆，不是偏好。
2. **不能放進 hook 的主路徑**：`context_budget_guard.py` 在**每一次** PostToolUse／PreToolUse 都會跑。把 HTTP 呼叫放進去等於給每一次工具呼叫加上網路延遲；而該檔自己記載過 P0——「hook 誤觸 deny 會把所有工具硬鎖死」。**取數（會失敗、會慢、會逾時）與判讀（必須快、必須確定性）的失效模式不同，必須分開。**
3. **AutoClaude 需要同一把尺，但不能 import 上面任何一個**（ADR-004 §4：套件不得依賴 harness 內臟）。⇒ 兩邊都只能透過**檔案契約**消費，而那個檔案需要一個寫入者。

🔴 **代價照實記**：這一支會讓護欄層 raw-line 淨額為正 ⇒ 依 `improving_104` §4 的「款(9)」讓步條款，**必須**在重釘列標 `[非淨減法輪]` ＋ 指名一份具名 `.md` 當逐檔清單的家，且該輪 **Q2 一律判未達成**。這不是可以繞過的，是本 ADR 自己要承擔的帳。

### 3.3 planner 淨行數必須 ≤ 0：怎麼做到

需要動 planner 的只有三處，全部可以做到零成長甚至負成長：

- `relay_problems()` 白名單加一個字串 ⇒ **同一行內加**，+0 行。
- `probe_quota()` 先打 endpoint ⇒ **改成先呼叫 `guard` 裡的一個新純函式判讀快取**，planner 側是**改一個呼叫**不是加分支，+0 或 −N。
  - 🔴 **R81 收斂：這一項至今 `未做`，而且在被 SD 點出來之前，repo 內沒有任何一處標注它未做**（對照 M10／M11 都誠實標了「🔴 待建」）。現況實測：`tools/session_resume_planner.py` 全檔 **零** `quota_meter` 引用，`probe_quota()` 仍以 `claude -p` 花約 **31,847 tokens** 問「額度回來了沒」。⇒「快取過期是常態」這件事只被 B1 收斂縮小（同步刷新那一格），**沒有被消除**。
  - **為什麼本輪仍不做**（照實寫，不是忘了）：① planner 實測 **749／750**，而這個改動要落地的是「先讀快取、讀不到才付費探測」的分支，一行塞不下；本 ADR 自己的解鎖程序是「先做 `tools/session_endurance.py` 抽離」，那是一個獨立包。② 它改的是**無人看管**的續航決策路徑（判錯的代價是白燒一次主 session），該路徑目前沒有端到端載具可驗。⇒ 承接輪次：**R82**（帳本 `DEF-101-990`）。呼叫點本身也已就地留註記，見 `probe_quota()` 上方。
- `sentinel_decide` 的 reset 來源優先序 ⇒ **整個做在 `guard` 側**（該函式本來就住在 guard），planner 側零改動。

⇒ **驗收判準**：`python AutoClaude/tools/check_loc_budget.py` 對 `tools/session_resume_planner.py` 印出的行數 **≤ 749**。做不到就**先做 ADR-004 已登記的抽離**（`tools/session_endurance.py`，R79_HANDOFF §4.3），**不准調高門檻**。

### 3.4 哪些該刪／該停

| 東西 | 處置 | 理由 |
| --- | --- | --- |
| 「從 token 加總反推額度分母」的一切工作（含多點校準構想） | **明文停止**，並改寫 CLAUDE.md 該段結論 | §2.1。不是「解不開」，是**不需要解**。繼續做是純浪費 |
| `DEFAULT_AT_EXPR = "(Get-Date).AddHours(5)"`（planner:278） | 檢查是否仍有活消費者；有就刪 | ADR-004 §2.1 已判它是缺陷，權威 `resets_at` 落地後它連 fallback 的資格都沒有 |
| `AutoClaude` 的 `resume_delay_minutes=30` 作為**額度**恢復延遲 | 保留欄位（它對別的用途仍有意義），但額度路徑改用 `resets_at` | §2.4 載體二 |
| `latest_limit_event()` | **不刪** | ADR-004 §2.8 已判：它是 `--arm-endurance` 手動路徑的來源，且是回歸鎖的控制組 |

---

## 4. 被否決的方案

| 方案 | 出處 | 否決理由（每條都有量測或既有判例） |
| --- | --- | --- |
| **從 token 加總反推分母 ＋ 多點校準** | R80 原定方向 | 等式不成立：池是跨產品共享；訂閱模式不走 token 桶（`anthropic-ratelimit-tokens-remaining` count=0）；本輪 A3 實測 10 分鐘漂 12pp，本 session usage 解釋不了。**校準點再多也解不開一個不存在的函數關係** |
| **以 headless `rate_limit_event` 當主要取數管道** | 「跟著既有 SDK 訊息流走」的直覺 | 調研 S1-05 實測：它**只在跨警戒門檻時**帶 utilization，而 80% 預警要的正是「還沒接近時也要知道」；且那一次**完全沒吐 five_hour**（水位最高的那個桶）。上游 issue #50518 **Closed as not planned**。⇒ 只當「免費順風訊號」，缺欄位一律判「量不到」而非「低用量」 |
| **statusLine 當唯一管道** | 欄位最齊、最省 | **TUI-only**（issue #50518 逐字：不在 headless SDK 模式下執行）⇒ 無人看管期間全盲。會蓋出「有人看著時很準、沒人看時全盲」的機制，正是 R80 哨兵整晚失明的同型。**保留為快取寫入器，不當權威源** |
| **複用 AutoClaude 的 `compact_threshold_pct`(80)／`halt_threshold_pct`(90)** | 數字剛好對得上 | 它們量的是 **context**。**數字接近才更危險**：會讓人以為額度已經有人守了，比沒有機制更糟。「同名不同義」本 repo 已反覆判過 |
| **新開 `tools/quota/` 三支檔** | 直覺分層 | 同 ADR-004 §3：護欄層自我增殖是本 repo 最大缺陷來源。全部功能塞得進「一支新 lib ＋ 兩支既有檔」，且塞的位置有結構理由（§3.2） |
| **把取數塞進 `session_resume_planner.py`** | 「不新增檔案」的慣性 | **實測**餘裕 1 行（A7）。ADR-004 自己也記載過遵守「零新增檔」讓該檔一度只剩 1 行的代價 |
| **把 HTTP 呼叫放進 hook 主路徑** | 最少的移動零件 | 每次工具呼叫加網路延遲；且該檔記載過 P0「hook 誤觸 deny 會把所有工具硬鎖死」。取數與判讀的失效模式不同，必須分開 |
| **每 50 分鐘喚醒一次** | 掌舵者提問 | §2.8 四個理由 |
| **量不到 quota 時自動節流（保守側）** | 「保守比較安全」 | 斷網 ⇒ 併發歸零、靜默、外觀與「額度真的滿了」相同。既有判例同形：`may_block()` 逐字「分母是猜的就不擋」 |
| **用 endpoint 的 `spend` 欄位取代 `classify_limit()`** | 結構化比字串可靠 | 本輪 A6：本帳號 `spend.enabled=False`，而 R80 逐字稿有 99 筆 `quota_spend`。**兩者不一致、成因未解** ⇒ 兩條並存，取較保守的一方 |
| **引入指數退避重試層（向業界看齊）** | 訴求 f 的直覺答案 | §2.10：那是 per-request 429 的工具，對 per-account 週期額度**結構上無效**，只會把探測預算燒光 |
| **OTEL 推送管道** | 調研 honest_gap #6 | **不是否決，是未評估**。`OTEL_METRICS_EXPORTER` 二進位命中 14 次、`claude_code.token.usage` 2 次，可能是唯一「不必自己輪詢」的推送式管道。列入 §9 |

---

## 5. 機械物（每個決策指名一個會轉紅的東西）

> 🔴 **硬約束**：`DEF-101-561③` 禁止新增鎖檔（`tools/tests/*` 只准合併／刪除）⇒ **所有新判準一律併入既有檔**，主要是 `tools/tests/test_context_budget_guard.py`（本 ADR 的主場）與 `tools/tests/test_platform_neutral_paths.py`。

| # | 決策 | 機械物（併入既有檔） | 壞掉時什麼會紅 |
| --- | --- | --- | --- |
| M1 | **單位正規化**（§2.2） | `test_context_budget_guard.py::QuotaUnitNormalizationTest` — 注入四種形態（`utilization=56.0`／`percent=56`／`utilization=0.3`／`used_percentage=56`），**必須產出相同內部值**；並含一組**反向自證**（故意把 0..1 通道當 0..100 讀 ⇒ 必須紅） | 任一 adapter 的單位寫反。**這是唯一能抓到「差 100 倍」的東西**——它不會自己冒出來，兩個方向都是靜默的 |
| M2 | **量不到 ≠ 量到零**（§2.1 L4） | `test_context_budget_guard.py::QuotaUnmeasurableTest` — HTTP 非 200／欄位缺／型別非數字／快取過期且刷新失敗，四種輸入**都必須**回 `None`（不是 `0.0`），且 cap 判定必須**不節流**、必須寫 degraded 痕跡 | 有人把「量不到」寫成 0（＝永遠正常，靜默失明）或寫成 100（＝永遠 halt） |
| M3 | **cap 階梯的方向**（§2.4） | `test_context_budget_guard.py::FanoutCapLadderTest` — cap 對 quota **單調不增**；`q>=95 ⇒ cap == 0` 嚴格斷言；環境變數覆寫值同受方向鎖 | 有人把 cap 調成隨水位上升，或讓 95% 那道還放行一個 |
| M4 | **80% 真的擋得到扇出**（§2.4） | 擴充既有 `test_context_budget_guard.py::PreToolUseBlockTest` — 沿用 R80 已落地的 `blocking_reach_problems()` 判準（圈到的名字須與**實測 tool_use 名稱**有非空交集），加測「quota≥80 且 in-flight≥cap ⇒ `exit 2`」 | matcher 或 `BLOCKING_TOOLS` 又寫成不存在的名字（R80 的 `DEF-101-970` 實測命中 0 次）；或 deny 分支根本走不到 |
| M5 | **派發帳不得永久膨脹、且是 per-account 的一份**（§2.4／§2.5） | `test_context_budget_guard.py::FanoutLedgerTest` — ①K 次被擋（K > cap）之後預算必須完好（`undo` 沖掉自己的 `try`）；②視窗一滾就歸零；③**帳檔名不得帶 session id**（讀原始碼斷言）；④壞掉的帳讀成 0 而不是讀成「擋住」 | 有人把被擋下的呼叫留成永久佔位 ⇒ 計數器只增不減 ⇒ 永久過度節流（且外觀像「額度一直很緊」）；或把帳改成 per-sid ⇒ N 個載體各拿一份 cap，等於沒有界住帳號層級的燒用量 |
| M6 | **三條線走不同分支**（§2.3） | `test_context_budget_guard.py::QuotaKindBranchTest` — `session` ⇒ 允許排程；**`weekly_*` ⇒ 禁止排程**（斷言不會產生 schtasks 動作）；`spend` ⇒ 禁止排程且必須 escalate | 有人把「95% ⇒ 排程等 reset」寫成無條件 ⇒ 週額度時排一支七天後才響的工作、痕跡全綠 |
| M7 | **桶名不得寫死**（§2.3 / A4） | `test_context_budget_guard.py::QuotaBucketUnionTest` — 注入一份**含未知代號桶**的 payload，判定必須照樣算得出 max 且不拋例外；斷言原始碼裡**沒有**寫死的桶名；並加測 SA-B3 的**聯集**方向（一個有真值卻不在 `limits[]` 裡的桶必須贏得過 `max(limits[].percent)`） | 有人為了「清楚」列了 8 個桶名 ⇒ 新桶滿了而我們看不到（靜默）；或只讀 `limits[]` ⇒ 代號桶先滿時讀到低值而**永不節流**，且沒有東西轉紅 |
| M8 | **reset 來源優先序**（§2.7） | 🔴 **部分未落地，照實記**。已落地：`test_context_budget_guard.py::RelayStateTest` — 猜的來源（`assumed-5h`）必須被判紅、白名單三個觀測值必須放行；`test_context_budget_guard.py::QuotaKindBranchTest` — 拿不到／不可解析／**naive 無 offset** 的 `resets_at` 一律 `escalate`（不得被當成時刻）。**未落地**：`endpoint-authoritative` 尚未進 `relay_problems()` 的白名單（`session_resume_planner.py:477-478` 現查仍是三個值），「截到分鐘去重」也還沒有判準 | 有人趁機把「拒絕武裝」那條放寬。⚠️ **未落地的那半是活的陷阱**：今天把 `reset_source` 寫成 `endpoint-authoritative` 會**被判紅**（不在白名單裡）⇒ 誰要落地 §2.7 就必須同時改 planner 白名單與 `RelayStateTest`，只改一邊會當場紅 |
| M9 | **planner 零成長**（§3.3） | 既有 `AutoClaude/tools/check_loc_budget.py`（已在 pre-push／CI） | planner 超過 749 行 |
| M10 | **AutoClaude 門檻另立**（§2.4 載體二） | 🔴 **未落地**（連同它要守的東西一起）：`AutoClaude/tests/` 既有 config 測試擴充 — 斷言 `quota_halt_pct > quota_throttle_pct`，且**斷言 quota 兩欄與 context 兩欄不是同一個物件／不共用預設** | 尚無可紅之處：載體二本身未落地（現查全庫無 `quota_throttle_pct`）。本列是**待辦不是現況**，落地載體二時必須同時落地它與 M11 |
| M11 | **AutoClaude 不反向依賴 harness** | 🔴 **無機械物**（本格原記載指名的是既有 `.importlinter`，而它**結構上看不到這個方向**，故不留著當現行說法）：該檔 `root_packages = autoclaude` 只有一個根，八條 contract 的 `forbidden_modules` **無一提及** `tools` 或 `.claude`（現查零命中，`lint-imports` 自報「Analyzed 205 files」全在 `autoclaude` 內）。⇒ adapter 寫 `import tools.lib.quota_meter` 會被當成**套件外的 external import**，八條全部照樣 KEPT。**假機械物比沒有機械物更糟**：它會讓下一個人以為這個方向有人守 | 沒有東西會紅。⚠️ 今天這一格是**空的**但尚無危害面——§2.4 載體二整段未落地（現查 `quota_throttle_pct`／`QuotaMeterPort`／`file_quota_meter_adapter` 全庫零命中）。要落地載體二就必須**同時**補這道判準（把 `tools`／`.claude` 加進 `.importlinter` 的 root_packages 與 forbidden_modules，或改用一支 AST 掃描器） |
| M12 | **憑證仍是 `NextRunTime` 的值** | 既有 `relay_problems()` ＋ `next_run_time()` 空字串判紅 | 有人用 rc 當憑證（`Get-ScheduledTask` 對不存在的工作回 rc=0） |
| M13 | **哨兵關掉時快取也會過期，且說得出來** | 兩支既有判準各守一半：`test_context_budget_guard.py::QuotaStaleCacheTest` — 超過 TTL 的舊值**不得**被採信為 normal（降級為「量不到」`source=stale-cache`，**連 96% 都不例外**），並含「新鮮的照用」控制組；`test_context_budget_guard.py::QuotaKindBranchTest::test_each_branch_says_something_different` — `AUTOSDD_SENTINEL_OFF` 造成的「沒武裝」訊息必須與其餘四種**互不相同** | 出現「哨兵關了但水位看起來還很新」的假綠；或「沒排程」與「排不了」長得一模一樣 |
| M14 | **文件宣稱 ↔ 實際註冊** | 既有 `test_doc_loc_baseline_freshness_r60.py::TestR74RootClaudeMdHookClaimsMatchRegistration` ＋ `TestR79EveryRegisteredHookIsNamedInClaudeMd` | CLAUDE.md 改寫時把新增／改動的 hook 條目寫錯 |

---

## 6. 驗收判準

> 每一條都要**當回合真跑並貼輸出**；貼不出來就寫「未驗證」。（CLAUDE.md〈反事後諸葛〉＋ Nightly 取證紀律 #3）

### 6.1 訴求 a（水位用 %）

- `python tools/lib/quota_meter.py --json` → rc=0，印出 `{"pct": <0..100 float>, "kind": "<session|weekly_all|...>", "resets_at": "<ISO+offset>", "source": "endpoint", "measured_at": "<ISO+offset>"}`。
- **口徑要說得出來**：輸出必須含 `denominator: "server-computed plan utilization (no local denominator)"` 這種明文欄位——「說得出它取的是哪一種計費口徑」是判準逐字要求的。
- 斷網重跑 → rc≠0 且印「量不到」，**不得**印任何百分比。

### 6.2 訴求 b（兩道閘的動作**真的發生**）

- **80%**：注入 quota=85 ＋ in-flight=2 的合成狀態，真的呼叫一次 `Task` → **工具沒有執行**（`PreToolUse:... hook error` 或 exit 2 的實際輸出）。
  🔴 **這一條的鑑別力來自反向對照**：同一次也要跑 quota=50 的對照組 ⇒ **必須放行**。只測「擋得住」不測「不亂擋」的鎖沒有鑑別力。
- **95%**：注入 quota=96 ＋ kind=session → ①扇出全擋；②任務書落磁碟（貼絕對路徑與前三行）；③`Get-ScheduledTask ... | Get-ScheduledTaskInfo | Select NextRunTime` 印得出**非空的時間值**。
  🔴 **R81 落地訂正（本條原記載的期望值與實作不符）**：原文要求該值對齊 endpoint 的 `resets_at`。落地版走 `--arm-sentinel` ⇒ 期望值是 **`now + 900s`**（見 §2.4 該格的訂正）。**判準的實質沒有變**：憑證仍是 `NextRunTime` 這個**值**（不是 rc），只是它該長什麼樣換了。
- **95% ＋ kind=weekly_all** → ①扇出全擋；②任務書落磁碟；③**排程器上不得多出任何工作**（前後 `Get-ScheduledTask` 計數相同）。

### 6.3 訴求 d/e（續航）

- `python tools/session_resume_planner.py --check` rc=0；`--verify-schtasks` 取到 `NextRunTime` 的**值**。
- 痕跡：`Get-ChildItem $env:TEMP\autosdd_resume_log_*.jsonl` 有新行；quota 取數的每一次都留 `source`／`pct`／`stale`。
- **探測成本歸零的證據**：走 endpoint 那條路的一次 tick，逐字稿**不得**新增任何 assistant 回應（＝零 token）。

### 6.4 Q2（架構簡潔／分工清楚／不重複模組；本節原標「訴求 c」，見檔頭訂正）

> 🔴 **訴求 c（Token 盡量不要用盡就停止並記錄所有狀態）的驗收判準在 §6.2 的 95% 那一條**，
> 不在本節——它要驗的是「停止」與「記錄」兩個動作真的發生，不是架構歸屬。

- `python AutoClaude/tools/check_loc_budget.py`：`tools/session_resume_planner.py` **≤ 749**；`tools/lib/quota_meter.py` **≤ 400**；且 §7 Step 0 已把繼承的 `hook_wiring.py` 紅收掉 ⇒ **rc=0**。
- `PYTHONUTF8=1 lint-imports`（AutoClaude 樹）8 kept / 0 broken。
- `python tools/check_hooks_liveness.py` rc=0（settings.json 改動後形態鎖仍綠）。

### 6.5 全域

- `python tools/run_root_unittests.py` rc=0；AutoClaude 樹 `python -m pytest tests/ -q` rc=0。
- 每一支新判準都要有**注入紅綠自證**（先注入壞值看它紅，再修回看它綠），並在收輪報告貼兩次 rc。

---

## 7. 實作步驟

見結構化輸出的 `implementation_steps`（每一步含檔案、機械物、風險）。此處只記**三條跨步驟的紀律**：

1. **每一步都是「先讓判準紅、再讓它綠」**。先寫會紅的注入，再寫實作。
2. **不准新增 `tools/tests/*` 檔案**（`DEF-101-561③`），一律併入既有測試檔。
3. **不准調高任何門檻／棘輪／體積上限**。護欄層淨額為正時走 `improving_104` §4 款(9) 的登記手續（標 `[非淨減法輪]` ＋ 指名逐檔清單的 `.md`），並接受該輪 Q2 判未達成。

---

## 8. 已知限制（照實寫，不粉飾）

1. **statusLine 通道從未實跑過。** §2.2 那一列的欄位表是 `claude.exe` **內嵌 schema 的自述**，不是觀測到的 payload。「statusLine 真的會送出 `rate_limits`」目前**未經證實**。⇒ Step 7 標為可選，且它失敗不影響主線（主線走 REST）。
2. **🔴 最關鍵的一格沒驗：撞線後 endpoint 還回不回得動。** 本輪兩次成功呼叫都在額度充裕時（44%／56%）。**「撞線後還能不能取數」正是續航鏈最關鍵的一格**，而它未驗。逼近 100% 時 `severity` 會不會變形、會不會回 429，全部未知。⇒ 回落路徑（`claude -p` 探針）**不准刪**。
3. **端點自己有沒有速率限制不知道。** 本輪兩次呼叫相隔約 1 秒皆 200（弱證據），沒做壓力測試。900 秒巡邏 ＋ 180 秒 TTL 的呼叫頻率**是估的**，不是量出來安全的。
4. **token refresh 流程完全沒跑過。** `/v1/oauth/token` ＋ `grant_type=refresh_token` 是從二進位字串讀到的端點與參數名，**沒有實際換過一次 token**，也沒驗證回寫格式。本輪覆核到期時刻距當下約 3.8 小時 ⇒ **無人看管過夜這條路今天是斷的**。
5. **🔴 `resumeFromRunId` 是 same-session only ⇒ 續跑鏈今天在跨 session 那一段是斷的**（§2.5；R81 已量，取代本條原記載的「欄位名未實測」）。三件事分開講：
   - **`resumeFromRunId` 只在同一個 session 內有效**（Workflow 工具說明逐字如此，已向掌舵者確認）。⇒ 額度撞線把 session 打死之後，**排程器醒來的那一跑按不了它**——那正是 §2.5 表格裡「無人看管」與「headless `claude -p -r`」兩列真正的阻塞理由，比原文寫的「需要載體二先落地」更硬：**即使載體二落地了，跨 session 重派仍然不是按這個按鈕**。今天做得到的只有「有人在的互動 session」那一列。
   - **`runId` 在 PreToolUse 的 payload 裡拿不到**。⇒ 實作改為撞線當下掃 session 目錄取 run 識別（`snapshot_fanout()`，見 §2.5），這是繞過而不是解決。
   - ⇒ **跨 session 的扇出重派今天沒有機械路徑**，只有「把死者清單寫給人／寫給 AutoClaude，由它重新派一次新的 run」。死者清單（`autosdd_fanout_<sid>.json`）因此是**給人讀的交棒單**，不是可以直接回放的 handle。**不要把它寫成「自動 resume 已經做到了」。**
6. **`spend.enabled=False` 與 99 筆 `quota_spend` 的矛盾未解**（A6）。⇒ §2.6 兩條分類器並存，這是**權宜不是設計**。
7. **`claude-agent-sdk` 未安裝在本 venv** ⇒ `SDKRateLimitsSnapshotMessage`／`RateLimitInfo` 本機無從驗證；網路搜尋／issue #50518／本機二進位掃描**三個來源互相矛盾**，本 ADR 以本機二進位為準（那是真正會跑的東西），但沒排除「別的機器／別的 SDK 版本可能有」。**也沒確認 AutoClaude production 走 SDK 支還是 PTY 支**，只讀了 adapter 原始碼。
8. **`.claude/hooks/` 不在任何 LOC 預算面內**（A9）。本 ADR 把判讀往那裡加，等於利用一個**沒有棘輪的成長面**。這是誠實的代價，不是免費午餐 ⇒ §9 列入「該不該把 `.claude/hooks/` 納入 LOC 棘輪」。
9. **訴求 f 只有結構結論，沒有實證比較。** §2.10 的「退避是錯的工具」是從本輪量測推得的，**不是**讀了那些框架原始碼得出的。不足以支撐更細的設計決策。
10. **mac/Linux 完全沒有**（沿用 ADR-004 §7-4）：schtasks 那一半只在 Windows 成立；`quota_meter.py` 本身是純 Python 跨平台，但它的**消費端**（哨兵、武裝）不是。鐵律三：單平台判準不外推，**明說做不到**而不是靜默缺席。
11. ~~**本輪繼承了一個紅**（A8）：`tools/lib/hook_wiring.py` 超出 `guardrail_lib` 上限。~~ ✅ **R81 已收（本條不再是現行限制）**：Step 0 做掉之後 `python AutoClaude/tools/check_loc_budget.py` 現查 **rc=0**，該檔已不在超標清單上。清單上僅存的一列是 `tools/session_resume_planner.py` 749/750（餘裕 1 行，本 ADR 刻意零改動、只當消費者——見 §3.3 與 M9）。
12. **本輪跑過的東西可能留下副作用**：調研第 7 項在 repo 根跑過一次 `claude -p` ⇒ SessionStart hook 會**無條件**武裝一支 `AutoSDD_Sentinel_*`（planner:643-651 已登記的設計問題）。**未查證也未清理。**

---

## 9. 待拍板／待補（不在本 ADR 射程）

1. **OTEL 推送管道**（`OTEL_METRICS_EXPORTER` × 14、`claude_code.token.usage` × 2）——可能是唯一「不必自己輪詢」的管道。調研 honest_gap #6 自評為「最值得下一步補的空白」。
2. **`.claude/hooks/` 是否納入 LOC 棘輪**（§8-8）。
3. **refresh token 的安全面**：要不要讓本 repo 的程式碼持有並使用 refresh token 換 access token？這是**安全決策，需要掌舵者拍板**，不是 agent 可代決。**無論怎麼決，禁止把 token 值寫進任何 log／任務書／痕跡。**
4. **`sentinel_task_name` 的堆積問題**（planner:643-651，ADR-004 已登記未修）：每個 headless session 一支哨兵。加上本 ADR 的 quota 刷新後，多餘的哨兵會多打不必要的 HTTP。
5. **`--allow-resume` 的機械護欄**（ADR-004 §7-5 未變）。
6. **CLAUDE.md 要改的段落**：〈額度耗盡：為什麼只能預防性武裝〉需加「權威取數管道已存在」；〈鐵律三〉對照表要新增 quota 軸那一列；並刪掉「多點校準」的殘留指引。**這一段本身受 M14 兩支既有鎖管轄。**
