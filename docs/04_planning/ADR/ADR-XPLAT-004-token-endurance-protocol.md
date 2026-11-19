# ADR-XPLAT-004：Token 額度續航協定（quota endurance）

- **狀態**：Accepted（R79）
- **日期**：2026-08-07
- **取代／被取代**：無。與 ADR-XPLAT-001/002/003 無重疊（那三支管跨平台面，本支管 harness 額度）
- **落地物**：`.claude/hooks/context_budget_guard.py`（純判讀）、`tools/session_resume_planner.py`（CLI／編排）、
  `tools/tests/test_context_budget_guard.py`（回歸鎖）。**本協定新增檔案數＝0**（本 ADR 除外）
  > 🔴 **「新增檔案數＝0」是本協定的自我約束，不是 repo 規則——不要把它讀成硬規則。**
  > repo 的硬規則只有 `DEF-101-561③`「禁新增**鎖檔**（`tools/tests/*`），只准合併／刪除」那一條；
  > 「不新增任何檔」是本 ADR 自己選的（理由見 §3 那一列：`tools/` 新增 `*.py` 會同時污染 ruff／
  > LOC 棘輪／`_script_scan_surface` 三個面）。**同輪其他包並未遵守它**（例如新建了
  > `tools/lib/skip_group_policy.py`、`tools/probe/misstep_attribution.py`、
  > `tools/probe/xplat_injection_matrix.py`），那不是違規。
  > **代價要照實記**：R79 四方複審實測，遵守它讓 `tools/session_resume_planner.py` 一度只剩
  > **1 行**餘裕（`guardrail_cli` 那一格）。複審後修復包用**壓縮表達**收回餘裕（長 WHY 由 docstring
  > 改成 `#` 註解——`count_loc` 計 docstring、不計註解行，這是 `AutoClaude/tools/check_loc_budget.py`
  > 自己的 TIER-WARN 指引，內容一字未刪），**沒有調高任何門檻**。
  > 但那只是止血：真正的修法是把續航編排抽成 `tools/session_endurance.py`、planner 退回
  > 「量水位＋產任務書＋CLI 分派」。已具名登記在 `R79_HANDOFF.md` §4.3。
  > 現查餘裕：`& $p "$r\AutoClaude\tools\check_loc_budget.py"`（看 `[ROOT-TOOLS-WARN]` 那一格）

---

## 1. 背景：一個今天真的發生過的事故

2026-08-07 約 09:30，七個 subagent 同時啟動，**16 秒內全數失敗**，逐字：

```
You've hit your session limit · resets 9am (Asia/Taipei)
```

主 session 仍活著（仍能跑工具、寫檔），但**沒有任何機制知道該等多久、也沒有任何機制會在額度回來時把工作接回去**。
SA 量到的等待分布說明浪費在哪：那次撞線在台北 08:44、訊息說 09:00 恢復（**只需等 16 分鐘**），
而下一則成功回覆是 **62 分鐘**後——**46 分鐘純粹在等人**。要自動化收回的就是這 46 分鐘。

既有機制全部不適用，逐項實查：

| 既有物 | 為何接不上 |
| --- | --- |
| AutoClaude Kernel 的 Token Guard（≥80% compact／≥90% checkpoint ＋ `scheduled_resume_at`） | 它守的是**被驅動的那個 CLI 的 PTY**，與 Claude Code session 自己零接線。它的 `time.sleep()` 睡在本 repo 自己的 Python 行程裡，而我們的等待必須發生在 harness 的行程裡 |
| `context_budget_guard.py` 的 75/90 線（R92 訂正：已改 **84/94**，見 ADR-XPLAT-008） | 那是 **context 水位**（分母＝window）。額度耗盡當下水位只有 ~18%，四道放行條件會全數放行 |
| `CronCreate` | `CronList` 標 `[session-only]`。R59 已踩過並寫進 CLAUDE.md |
| `ScheduleWakeup` | `delaySeconds` clamp 到 [60, 3600]；**且它不寫磁碟、沒有可查詢的登錄、沒有 `NextRunTime`** ⇒ 沒有任何憑證，事後無從得知它排到了沒有——與 R59 那次事故同形 |
| CLAUDE.md〈Token 將耗盡時的 SOP〉 | 純散文。本 repo 已反覆實證純文件約束對當下的模型零攔阻力 |

---

## 2. 決策

**額度耗盡時：從錯誤訊息觀測 reset 時刻 → 排一支一次性 `schtasks` → 到點由確定性的 Python 探測 →
通了就續跑／沒通就依新觀測的時刻重排／月度上限就硬停並叫人。等待期間零 token、終端可關、機器可睡。**

### 2.1 reset 時刻**只能觀測，不能算**（本 ADR 最關鍵的一條）

R79 立案量測：全庫 1,180 支逐字稿掃出 **7 個相異** reset 值。
🔴 **R80 重量（母體長大了，結論不變且更強）**：1,579 支逐字稿、**10 個相異值**
（新增 `1:50am` 46 筆、`6:50am` 14 筆、`7:40pm` 2 筆）。**沒有一個落在 5 小時的固定格點上**，而且 15 個
相異撞線 episode 的實際等待窗**沒有一個超過 5 小時**（最長 4.2 小時）⇒ 它是滾動視窗、
錨在該區塊第一次用量。逐筆量測見 §2.7；**這些數字是量測值不是常數，要對照就重跑
`tools/probe/reset_window_distribution.py`**。

因此 `DEFAULT_AT_EXPR = "(Get-Date).AddHours(5)"` 是缺陷：它把一台機器的偶然事實寫成常數（R73 同型）。
更難看見的是它的失效**不會轉紅**——排程會成立、`NextRunTime` 也拿得到、取證規則照樣綠，
只是它**醒在錯的時間**。這是「憑證存在、但憑證不回答那個問題」。

⇒ `parse_reset_at()` 解不出時間時回 `None`，呼叫端一律**拒絕武裝**，
**不准**退回「假設 5 小時」（`relay_problems()` 對 `reset_source` 非觀測值一律判紅）。

### 2.2 S1（session 額度）與 S2（月度支出上限）必須分開

實測計數：`session limit` **151** 筆／`monthly spend limit` **71** 筆（＝32%）。
兩者的字面前綴同為 `You've hit your `，只比對前綴的分類器會把那 71 筆判成可等待
⇒ 排一支永遠不會成功的工作、每次觸發燒一次探測，而真正該做的事（叫人提額）一直沒發生。
這是本協定**最貴的一種誤判**，故 `classify_limit()` 的判讀順序把 spend 排在 session 之前，
且 `LIMIT_UNKNOWN` 一律 fail-closed（不重排）。

### 2.3 分層：只有一層是自動的

| 層 | 機制 | 憑證 | 終端可關？ |
| --- | --- | --- | --- |
| **L0 觸發**（R79 補洞包新增，見 §2.6） | SessionStart hook 自動 `--arm-sentinel` | `NextRunTime` ＋ JSONL 痕跡 | ✅ |
| **L1 武裝**（session 內，一個回合，零等待） | `--arm-endurance` | `NextRunTime` | — |
| **L2 自動**（唯一撐得住的） | `schtasks` ＋ `--resume-tick` | `NextRunTime` ＋ JSONL 痕跡 | ✅ |
| **L3 地板**（永遠成立） | `%TEMP%` 的任務書＋狀態塊，含 `claude -r <sid>` | 檔案本身 | ✅ |

**L3 是進入等待的前置條件**：寫不出任務書就直接放棄並大聲說做不到，不准假裝在等。

### 2.4 狀態只有一個家

續航狀態嵌進**既有的可重啟點任務書**（`%TEMP%\autosdd_resume_plan_<sid>.md`），
用兩行字面 sentinel 夾一段 JSON。一份檔、兩個面：人讀六節、機器讀那一塊。
解析走「找 sentinel → `json.loads`」的子字串掃描，**不解析 markdown**（有人調一個標題不該讓狀態讀不出來）。

「沒有武裝過」與「武裝過但狀態壞了」必須分得開（`has_relay()` vs `parse_relay()`）——
這是「量不到 ≠ 量到零」在狀態檔這一層的形態。

### 2.5 無人看管的那一跑：續跑**預設關閉**

`claude -p -r` 是全自動、沒有人在迴圈裡，而任務書的〈禁止事項〉是散文，對 print 模式的模型一樣零攔阻力。
故：**醒來那一跑預設只做「探測 ＋ 留痕 ＋ 通知」**，真的續跑要在武裝時顯式帶 `--allow-resume`
（該選擇記進狀態塊，事後查得到）。
昂貴的那部分（等 5 小時、知道額度什麼時候回來）兩種模式都完成；被關住的只有最後那個模型回合。

> 🔴 **未解**：`--allow-resume` 開啟時，要不要用 hook 機械擋掉 commit/push？

### 2.6 預防性哨兵：補上**觸發層**（R79 補洞包；本節是對 §2.3 那張分層表的修正）

§2.3 把 L1 武裝寫成「session 內，一個回合，零等待」，讀起來像是已經解決了。**它沒有**——
L1 是**手動**的，而本輪在協定落地的**同一天又撞了一次額度，協定一點作用都沒有**。三層根因：

| 層 | 缺口 | 為什麼 §2.3 那張表看不出來 |
| --- | --- | --- |
| **觸發** | 沒有任何東西會去按 `--arm-endurance` | 那張表只描述「按下去之後會發生什麼」，沒有一欄在問「誰按」 |
| **偵測** | 額度耗盡**不是工具呼叫失敗**，是 API 層失敗 ⇒ PreToolUse／PostToolUse 一次都不會被叫到 | 全 repo 唯一的事中觀測面是 hook，而這件事在 hook 體系裡**沒有觸發點** |
| **形態** | 這是「機制蓋好沒接電」的第三次復發（R77 PKG-GUARD 有前例） | 覆盤只看「功能對不對」，不看「有沒有東西會自動去用它」 |

實測逐字（撞線後補跑 L1）：`rc=1`／「觀測到的 reset 時刻 … 已經過去 … 沒有東西需要等」。
判斷是**對的**——但它暴露了設計缺口：`--arm-endurance` 只在「已撞線且 reset 尚未到」那個很窄的
時間窗裡有用，**而那個窗恰好是沒有人會去用它的時候**。

#### 關鍵洞察（整個哨兵成立的原因）

> **探測是為了知道「額度回來了沒」——那件事只能問伺服器；
> 但要知道「額度撞了沒」根本不用探測——讀逐字稿就行，成本是零。**

這個不對稱讓「還沒撞線就先掛著」變得可行：平時每次醒來只讀檔（零 token），
只有真的撞線那一次才花一次探測（~32K tokens）。對照被否決的 `ScheduleWakeup` 接力
（§3 第一列）：那個方案**每次**醒來都要花一個模型回合（實測 ~20.7 萬 tokens），
所以它才被迫把間隔拉到 50 分鐘——成本結構不同，取值就不同。

#### 哨兵四分支（`sentinel_decide()`，純函式）

| 分支 | 條件 | 動作 | 成本 |
| --- | --- | --- | --- |
| `arm_reset` | 有未處理撞線、reset 尚未到 | 重排到 reset＋skew（`--sentinel-tick`） | 零 token |
| `probe` | 有未處理撞線、reset 已過 | 花一次探測，之後交棒 `--resume-tick` 既有機器 | 一次探測 |
| `patrol` | 無未處理撞線、逐字稿仍在更新 | 重排下一次巡邏 | 零 token |
| `disarm` | 無未處理撞線、逐字稿已靜止 | 自我解除並驗證真的移除 | 零 token |

外加兩個 fail-loud 出口：月度支出上限 ⇒ `escalate`（等待無效）；解不出 reset 時刻 ⇒
`escalate`（**拒絕用猜的重排**，同 §2.1）；狀態塊指的逐字稿不存在 ⇒ `escalate`
（哨兵瞎了與哨兵正常下班必須留下不同的痕跡）。

#### 「未處理」的判準，以及它為什麼可證

🔴 **R80 訂正這一小節的立案理由（本段以下為立案原文，僅作史料保留，不是現行判準）**：
下面那句「理由是可證的」已於同輪被實測推翻，訂正與現行判準見 **§2.8**；本段刻意原文不動，
是因為它是 §2.8 那筆 P0 的**根因原件**，改寫掉就看不出「當初為什麼會這樣寫」。

事件時間戳**嚴格大於**狀態塊裡的 `handled_through`。武裝當下把逐字稿裡最後一筆事件記成
已處理，理由是可證的：**我們此刻跑得動武裝指令，就證明額度是通的** ⇒ 已經在逐字稿裡的
那些撞線必然都已解決。少了這一格，哨兵會每 15 分鐘對同一筆早就結案的撞線探測一次。

#### 兩個閾值都是**量出來的**，不是挑的

- `SENTINEL_INTERVAL_SECONDS = 900`：立案時的依據是「實測那次真實撞線 08:44 撞、訊息逐字
  `resets 9am` ⇒ hit→reset 只有 **16 分鐘**，間隔必須小於它」。
  🔴 **R80 訂正這個依據（結論不變、理由過期）**：以全庫 1,579 支逐字稿重新量測（見 §2.7），
  hit→reset 的最短值是 **0.5 分鐘**、次短 11.4 分鐘，15 個相異撞線 episode 裡有 **4 個 ≤16 分**。
  也就是 900 秒**並不小於已觀測到的最短窗**，原句的字面已不成立。
  但「間隔要小」這個方向仍然對，且後果比原句寫的輕：間隔大於某個窗時，那一次走的是
  `probe` 而不是 `arm_reset` ⇒ **代價是一次探測（~32K tokens），不是失效**。真正被間隔決定
  的量是「reset 之後最壞多久才會有人動作」≈ 一個間隔。詳細取捨與為何**不**改成 50 分鐘見 §2.7。
- `SENTINEL_IDLE_SECONDS = 21600`（6h）：立案理由是「必須大於一個完整額度視窗（5h）」。
  🔴 R80 附註：§2.7 的量測顯示實際等待窗最長只有 **4.2 小時**（253.2 分），所以 6h 對「等額度
  期間不要把自己拆掉」有充裕餘裕；這一格**不動**（餘裕大不是缺陷，而縮小它沒有任何好處）。
  兩者的方向都由 `tools/tests/test_context_budget_guard.py::SentinelDecisionTest` 釘住。

### 2.8 「已處理」必須是**證據**，不是推論（R80 P0；§2.6 那格判準的訂正）

§2.6〈「未處理」的判準，以及它為什麼可證〉逐字寫著：

> 武裝當下把逐字稿裡最後一筆事件記成已處理，理由是可證的：**我們此刻跑得動武裝指令，
> 就證明額度是通的** ⇒ 已經在逐字稿裡的那些撞線必然都已解決。

🔴 **那句「理由是可證的」本身不成立，而它是本輪 P0 的根因。** 武裝走的是
`--arm-sentinel`：一個**純本機 subprocess，零 API 呼叫**。額度早就見底時它照樣跑得動、
照樣把撞線標成已處理。這個推論**恆真且與額度無關** ⇒ 它證明不了任何事。
代價已實際發生（E12）：撞線後 2 分鐘 `handled_through` 就越過了那筆事件，此後每一次
巡邏都「合法地」判 patrol，機制全程正常運作、只是守著一個假前提。

**訂正後的判準（判準 D）**：額度是**帳號層級**的資源，所以「額度在某時刻之後是通的」
唯一的硬證據，是那之後**真的出現過一則成功的 API 回應**——
`type=assistant` ＋ 真 model（非 `<synthetic>`）＋ **有 `message.usage`**。
`usage` 那一格是關鍵：它是伺服器真的計費回來的痕跡，harness 自己合成的錯誤訊息沒有它
（少了這個條件，撞線記錄會自己證明自己已解決）。

三處連動修正，全部落在 `context_budget_guard`（它結構上不能 import 別人 ⇒ 偵測知識的唯一家）：

| 面向 | 舊 | 新 |
| --- | --- | --- |
| 事件來源 | `latest_limit_event`：只掃**主逐字稿**、只取**最後一筆** | `unhandled_limit_event`：主檔＋`<sid>/**/*.jsonl`（subagent），取**最早一筆未處理** |
| 「已處理」 | 與 `handled_through` 比時間戳（來自上面那個假推論） | 與**全域最後一次成功回應**比（判準 D，假陽性實測 0.0%） |
| 存活判準 | 只看主逐字稿 mtime | 取全 session 最新 mtime（扇出時主檔可能很久沒被寫 ⇒ 忙碌 session 會被誤判閒置而**自我解除**）。🔴 R214 訂正：mtime 判準已由 §2.10 取代為對話記錄 timestamp（DEF-200-560；此列為 R80 當時的歷史對照，原文保留） |

**為何取最早而不是最後一筆**：同一次停機裡每個 subagent 都會留一筆，最早那筆才是真正的
撞線時刻（其餘離 reset 更近）；而要拿它的 reset 時刻去排程，取錯就排錯時間。
**為何 `latest_limit_event` 不刪**：它仍是 `--arm-endurance` 手動路徑的來源，且本輪的
回歸鎖拿它當**控制組**（證明新舊判準真的不同，否則測試沒有鑑別力）。

〈存活門檻〉現況照實寫：`SENTINEL_IDLE_SECONDS = 21600`（6h）**是有門檻的**，
本次三筆 patrol 的 idle 為 5,949／6,850／7,750 秒（≤2.15h）⇒ 判「還活著」符合門檻、
**不是**漏設。真正的缺陷是上表第一、二列，不是這個門檻，故本輪**不動它**（§2.6 已論證
它必須大於一個完整額度視窗；實測最長窗 3.6h，6h 有餘裕）。

成本閘：subagent 掃描面以檔案 mtime 24h 為窗（`session_transcripts`）。它是**成本閘不是
判準**——一筆「比全域最後成功回應還新」的事件不可能出現在 24h 沒被寫過的檔裡，而母體
已有 1,500+ 支檔、哨兵每 15 分鐘跑一次。回歸鎖對這個參數帶雙邊斷言。

### 2.7 「五小時要怎麼度過？是不是每 50 分鐘喚醒一次？」（R80；掌舵者提問）

原問題逐字：「Claude Code 同 session、同一個 token 池、單次上限 1 小時，Reset 時間五小時，
要如何度過五小時要考慮，是否可以每 50 分鐘喚醒一次（當然還需要有剩餘 Token 才能做）」。

#### 先推翻問題裡的前提：**沒有「五小時」這回事**

量測器＝`tools/probe/reset_window_distribution.py`（R80 落地。**它本身就是本節的取證規則**：
R79 已判過一次同型失誤——R77 宣稱「每輪重跑分群」卻沒留下可重跑的產物，於是那個要求
結構上做不到、數字被當常數引用了五輪。逐筆輸出是可 diff 的 jsonl，預設落系統暫存）。
母體＝本機 `~/.claude/projects/**/*.jsonl`；撞線指紋與 reset 解析一律沿用
`context_budget_guard` 的既有實作，不另寫判準。**R80 當回合實測**：

| 量 | 值 |
| --- | --- |
| 逐字稿母體 | 1,579 支 |
| harness 合成事件分類 | `quota_session` 152／`quota_spend` 99／`transient` 6／`unknown` 1 |
| session-limit 事件 | 152 筆，**152 筆全部解得出 reset**（解析率 100%） |
| reset 字面相異值 | **10 個**：`1:50am`(46) `3:50am`(4) `4am`(55) `6:50am`(14) `9am`(8) `11pm`(3) `12:20pm`(8) `12:30pm`(6) `6pm`(6) `7:40pm`(2) |
| 相異撞線 episode | **15 個**（以 reset 時刻分群——一次撞線會在 16 秒內讓每個 subagent 各留一筆，最大一群 46 筆） |
| **episode 停機時長**（自最早撞線起算） | **min 0.5 分／median 59.8 分／max 253.2 分（4.2 小時）** |
| 單一觀測者看到的最短窗 | min 0.5 分／median 57.9 分／max 251.1 分 |
| 超過 5 小時的 episode | **0 個** |
| ≤16 分 / ≤50 分 | 4/15 ／ 7/15 |

> 本表含 R80 當天新增的兩個 episode（`resets 1:50am` 與 `resets 6:50am`）。**數字每次重跑都會變**，
> 這正是它必須是腳本而不是散文的原因。

> 🔴 **兩個量必須分開，而它們的方向很容易寫反**（R80 落地時第一版就寫反了，訂正記在
> `episodes()` 的 docstring 裡）：`minutes = reset − hit`，所以**最早**撞的那一筆值**最大**。
> 「這次停機多久」＝取 max（第一個人撞到牆算起）；「一個剛醒來的哨兵最壞只剩多少時間
> 可反應」＝取 min。兩者回答不同問題，混用會讓下面的取捨算錯邊。

> 🔴 §2.1 原記「全庫 **7** 個相異 reset 值」——R80 實測是 **9** 個（新增 `1:50am` 46 筆、
> `7:40pm` 2 筆）。§2.1 的**結論完全不變且更強**：9 個值仍然沒有一個落在 5 小時格點上，
> 而且 episode 級最大等待只有 4.2 小時 ⇒「滾動視窗、只能觀測不能算」再次被證實。
> 這個數字是**量測值不是常數**，每輪重跑即可，不得被引用為常數。

⇒ 「要度過五小時」這個問法本身就是那個被 §2.1 否決掉的固定視窗假設的殘留。
實際要度過的是**一個未知長度的窗：中位數約 60 分鐘、最壞約 4.2 小時、最好 30 秒**。
15 個 episode 裡**沒有一個**超過 5 小時。

#### 再回答「每 50 分鐘喚醒一次」：**不採用**，三個理由都是量出來的

1. **50 分鐘這個數字是別的方案的約束外溢，不是本方案的取捨。** 它來自
   `ScheduleWakeup` 的 `delaySeconds` clamp 上限 3600 秒（§3 第一列）——為了在 1 小時上限
   內留邊際才取 50 分。schtasks **沒有這個上限**，所以把 50 分鐘搬過來是「照抄一個已被否決
   方案的參數」。
2. **它會把最壞死等時間從 15 分鐘放大到 50 分鐘，換不到任何東西。** 巡邏的成本是
   **零 token**（讀一次逐字稿 ＋ 一次 `stat`），所以延長間隔省下的是「排程器喚醒 ＋ 一次
   python 啟動」——這一側沒有需要權衡的量。對照 7/15 個 episode 的窗 ≤50 分鐘：那些窗裡
   50 分鐘的間隔會讓哨兵**整個窗都沒醒過**，額度早就回來了卻沒有人動作。
3. **「還需要有剩餘 Token 才能做」這個顧慮在本方案裡不存在**——而它正是 50 分鐘方案的致命
   傷。`ScheduleWakeup` 每醒一次是一個**模型回合**（實測 ~20.7 萬 tokens），額度斷電期間
   它自己也會被擋 ⇒ 結構上撐不過斷電。哨兵醒來只讀檔，**斷電期間照樣跑得動**，這是它能
   成立的唯一原因（§2.6 的關鍵洞察）。

#### 建議設計（＝現況，加一條可選的收斂）

**維持 900 秒固定間隔巡邏 ＋ 觀測到 reset 後精確重排。** 判準：

- 巡邏零 token ⇒ 間隔只由「reset 後最壞死等時間」單邊決定，愈小愈好；
- 下界由排程器與 python 啟動開銷決定（實測一次巡邏 < 2 秒），900 秒已在極寬鬆的一側；
- **真正消除死等的不是縮短間隔，而是 `arm_reset` 那一支**：一旦看見撞線且 reset 未到，
  它就把下一次觸發**精確排到 reset+120s**，此後與間隔無關。今天 01:40 那次實測走的正是
  這一支（`arm_reset` → reset=01:50 → 01:52 探測），死等 2 分鐘而不是 15 分鐘。
- ⇒ 間隔只影響「從撞線到**第一次看見它**」這段。要把它壓到近零得靠事件驅動，而額度耗盡
  在 hook 體系裡**沒有觸發點**（§2.6 偵測層），所以輪詢是唯一的形狀。

**不建議**的變動（記下來免得下輪重新討論）：把間隔改成自適應（例如「偵測到 session 活躍就
縮短」）。它會讓「哪一次巡邏該發生」變成一個有狀態的判斷，而這條路上每一個有狀態的東西
都已經在 `relay` 狀態塊裡有一份帳；多一個維度換到的是最壞 15 分鐘 → 幾分鐘，而代價是
一個沒有憑證的行為差異。**不值得**。

#### 接電：SessionStart hook（本節的重點，不是那個工具）

**這一次不做成「要人記得去按」的東西**。`.claude/settings.json` 的 `SessionStart` 新增一個
條目，掛同一支 `context_budget_guard.py`（第三個模式，由 `hook_event_name` 分派）。
契約：只在 Windows 動作；`AUTOSDD_SENTINEL_OFF` 一律 no-op；**恆 exit 0、不出聲、不量水位**；
註冊走 **detached 子行程**故不阻塞 session 開場（同步外呼 `powershell.exe` 註冊實測數秒，
每次開 session 都卡是不可接受的代價）。取證沒有因為非同步而消失——`--arm-sentinel` 自己
有 `NextRunTime` 憑證閘，成敗都進稽核 jsonl。

> 🔴 **superseded（2026-09-15 標記，原文不動）**：上段「只在 Windows 動作」與「SessionStart 註冊」兩句已過期——
> R83 落地 launchd 後端（`tools/lib/schedule_backend.py`）後，本條目在 Windows（schtasks）與 macOS（launchd）
> 皆動作、Linux 等無載具 no-op；R82／HELM-02 起 SessionStart 只清上一輪武裝閂鎖＋回收孤兒哨兵，真正武裝
> 延後到 PostToolUse `arm_when_earned()`。現行契約以 `.claude/hooks/context_budget_guard.py` 與
> `.claude/settings.json` 該條目 `_comment` 為準；§2.9 既有 superseded 註記只點名 §2.6 第 4 條與 §7-4，
> 未涵蓋本段，故在此補標。

> 🔴 **`.claude/settings.json` 從此不再是「本協定不動」**（§4 最後一列原本這樣寫，那是對的——
> 在寫下它的時候）。本節是一個**新決策**：額度確實不是 context，但**接電點**只能長在 hook
> 註冊面上，因為那是全 repo 唯一「session 一開就會自動跑」的地方。共用腳本、不共用門檻。

#### 已知限制（照實寫）

1. **首次武裝有一個巡邏間隔的空窗**：SessionStart 之後 15 分鐘內撞線，要等下一次巡邏才
   被看見。代價是延遲、不是漏掉（`handled_through` 不會前進）。
2. **detached 子行程的成敗，SessionStart 那一刻看不到**——只能事後查 jsonl／`Get-ScheduledTask`。
   這是為了不阻塞開場付的價。
3. **每個 session 一支排程工作**；靠 `disarm` 分支回收。若機器在哨兵下班前就關掉，工作會
   留到下次開機補跑（`StartWhenAvailable`）才自我解除。
4. **mac/Linux 完全沒有**：`run_powershell()` 在非 Windows fail-loud，哨兵整條路同樣只在
   Windows 成立（鐵律三：單平台判準不外推）。
5. **`--allow-resume` 的風險未變**（§2.5、§7-5）。哨兵只是讓「等到額度回來」這件事會自己
   發生，最後那個模型回合的授權面一個字都沒放寬。
> `claude --disallowed-tools` 存在（實查 `--help`），但它只能擋整支工具，擋掉 PowerShell 會讓續跑失去意義。
> 本輪**沒有**做這道，故預設關閉是它的替代品。這是已知缺口，不是漏看。

### 2.9 哨兵死於自己的任務書：單檔雙寫者事故與零人工閉環（R95；掌舵者 2026-08-17 立案「Token 用盡時，為何沒有啟動下一個 Reset 的喚醒機制」）

> 本節由唯讀調查包落款（PRD v2.1.5 的設計對應節）。所有「已存在」皆為當回合現查；
> 「修 1～修 4」皆**未實作**，交下一波實作包。§2.6〈已知限制〉第 4 條與 §7-4
> 「mac/Linux 完全沒有」自 R83 落地 launchd 後端（`tools/lib/schedule_backend.py`
> `StartInterval`＋`StartCalendarInterval`，該檔 86-127 行含真機實測）起已過期——
> 依本 ADR 慣例原文不動，在此標記 superseded。
>
> 🔴 **狀態標記（R95 收尾修復包，2026-08-17；依本 ADR 既有 superseded 體例，原文不動）**：上句「『修 1～修 4』皆**未實作**，交下一波實作包」已 stale——修 1～4 已於 R95 同輪由實作波落地，證據＝帳本 DEF-200-146、CrossPlatform_R95_Resume_Strategy_Evidence.md §L-4、CrossPlatform_R95_Pace_Actuator_Evidence.md §7-R95-修4（修4 以 `halt_resets_at` 具名函式實作，形狀與本清單「reset_branch 簽名擴充」不同，理由見該節）。

#### 事故時間線（Asia/Taipei；證據全部為現存痕跡，逐字／檔案:行號）

| 時刻 | 事件 | 證據 |
| --- | --- | --- |
| 08-16 ~22:09 | 哨兵武裝（launchd，900s 巡邏底盤） | resume log `sentinel_armed`，credential 逐字含「launchd gui/501/AutoSDD_Sentinel_48e5e840-…｜launchctl print rc=0（不存在時是 113）｜run interval = 900 seconds〔launchd 回讀，與請求相符〕」 |
| 22:24:58～00:40:00 | 十次巡邏**全數成功讀出狀態塊**、判 patrol | resume log 連續十筆 `sentinel_decided`「無未處理撞線；逐字稿 Ns 前仍有更新」（jsonl 住 `$TMPDIR/autosdd_resume_log_autosdd_resume_plan_48e5e840-….jsonl`） |
| 08-17 00:42 | 額度閘 halt 閂鎖 `halt@extra_usage@None` 首次落鎖；`quota_halt_actions()` 無條件呼叫 `plan_writer` → planner 預設路徑**整檔覆寫任務書骨架，RELAY 狀態塊被砸掉**；且 binding 軸無 reset ⇒ `reset_branch()`=escalate，`waker` 未武裝 | `$TMPDIR/autosdd_quota_latch.json` mtime=08-17 00:42、tiers 含 `halt@extra_usage@None`；`tools/lib/quota_gate.py:836-841`（閂鎖＋動作）、`:643`（`waker` 只在 branch==ARM）；`tools/session_resume_planner.py:1394`（`out.write_text(render_plan(...))` 無條件覆寫；`render_plan` 骨架不含 RELAY 塊） |
| 00:51:09～:11 | 收尾 subagent（`agent-aa8fd5ba…`）撞線死亡；主 session 被 task-notification 喚醒一回合，**該回合自身死於 API 層** ⇒ 主逐字稿寫入合成權威記錄——當晚最後一筆 | 主逐字稿 line 241：`type=assistant`＋`model=<synthetic>`＋逐字「You've hit your session limit · resets 3:50am (Asia/Taipei)」（timestamp 2026-08-16T16:51:11.319Z） |
| 00:55:00 | 第 11 巡醒來——事件落地後 4 分鐘、唯一有機會偵測的一巡——`parse_relay()` 讀不出狀態塊 ⇒ `_abort_and_unregister()` **自我解除排程**，只印一行沒有人收得到的 stderr | launchd log 逐字「❌ 哨兵拒絕動作：任務書／狀態塊讀不出來 已自我解除排程 AutoSDD_Sentinel_48e5e840-…（rc=0）」；`tools/session_resume_planner.py:1268-1274` |
| 03:50 | 額度 reset。**機器上已無任何排程** ⇒ 空轉 | 今晨 `launchctl list` 過濾 AutoSDD_Sentinel_ 零註冊 rc=1；`~/.autosdd/traces/autosdd_sentinel_bootout_AutoSDD_Sentinel_48e5e840-….log` mtime=00:55:02（持久痕跡，證明「查不到」是**自我解除的結果**，不是從未武裝） |
| ~11:30 | 掌舵者手動回來才續上 | armed stamp `autosdd_sentinel_armed_48e5e840-….json` mtime=11:33:44（turns=76、span=48835.9s——PostToolUse `should_arm` 門檻 24 回合/600s 的重新武裝） |

00:42 觸發面歸因：00:22～00:29 其餘三支 subagent 已停筆（`subagents/*.jsonl` mtime），
00:42 唯一活著的是 `agent-aa8fd5ba…`；而 `$TMPDIR` 全部 hook 產物（ctxguard／fanout／
sentinel_armed）均只以主 session id 為鍵、無任何 `agent-*` 鍵 ⇒ subagent 工具呼叫的
hook payload 帶主 session 逐字稿，00:42 覆寫的正是本 session 的任務書。

#### 反事實：整條喚醒鏈當晚是通的，被一次檔案覆寫殺死

逐環現查：① 詞表——`quota_limits._LIMIT_MARKS` 的 `"session limit"` 命中該錯誤字串
（`tools/lib/quota_limits.py:63`）；② 形狀——line 241 正是判準要的 `type=assistant`＋
`model=<synthetic>`（同檔 165-171 行），且 `unhandled_limit_event` 掃主檔＋subagent
（§2.8 判準 D，假陽性 0.0%）；00:55 當下事件之後全域零成功回應 ⇒ 必判未處理；
③ 決策——`sentinel_decide()` 會走 `arm_reset`＝reset+120s skew＝03:52
（`tools/session_resume_planner.py:642-668`）；④ 載具——launchd 已支援
`StartCalendarInterval`（R83-B）；⑤ 選路——`choose_resume_route()` 三態＋
`_run_resume` 的 `claude -p -r`（同檔 1072/1105-1145）。
**缺的不是任何一環的能力，而是哨兵活到 00:55 的資格。**

#### 根因（三層主因＋一層次因）

1. **單檔雙寫者（主因）**：任務書一支檔兩個寫者——哨兵的 RELAY 狀態塊
   （`write_relay()`，替換式、保結構）vs 骨架產生器（planner 預設路徑，整檔覆寫、
   不保 RELAY）。額度閘 halt（`quota_gate.py:839`）與 prepare（`:649-660`）帶的
   `plan_writer`（`.claude/hooks/context_budget_guard.py:680` `write_resume_plan` →
   planner 預設路徑）在哨兵武裝期間觸發即摧毀狀態塊。
2. **讀不出狀態塊＝fail-quiet 自我解除**：`_sentinel_tick` 的 abort 分支只拆排程＋
   寫痕跡＋一行 stderr（launchd job 的 stderr 沒有人收）——不 `escalation.alert`、
   不自癒、不重巡；且三種失效（檔不存在／沒有狀態塊／JSON 壞掉）痕跡同形
   （`_resume_tick` 分得開，`_sentinel_tick` 沒分）。「主 session 活著但帳號級撞線」
   這一格的**唯一**機械物，在最需要它的那 4 分鐘把自己拆掉。
3. **解除後結構上無人 re-arm**：重新武裝依賴該 session 的 PostToolUse
   （`sentinel_lifecycle.maybe_arm`），而撞線後 session 發不出任何工具呼叫。
4. **次因（另案修）**：halt 武裝分支以 binding 單軸決定（`quota_messages.reset_branch`
   75-88 行）——本案 binding=extra_usage、resets_at=None → escalate-only；但
   five_hour 軸 03:50 reset 後工作實際可續（今晨實證：額度快取 session/five_hour 18%）。
   多軸情境下「binding 無 reset ⇒ 只能等人」是假的。

#### 三個候選觸發點的取捨（判準：最少新增件數、最大覆蓋）

| 候選 | 判定 | 理由 |
| --- | --- | --- |
| (a) 哨兵巡邏判準擴充認得 subagent 撞線 | **改形採納**：辨識面已存在（§2.8 判準 D 本來就掃 subagent，本案逐環驗證全通），缺的是**哨兵存活** ⇒ 主修改為「骨架寫入保 RELAY」＋「abort 分支自癒＋fail-loud」。0 新檔、2 個函式 | 反事實節五環現查 |
| (b) PostToolUse／task-notification 層攔截撞線字串當場排程 | **否決** | 結構不可能：撞線是 API 層失敗，那一刻沒有工具事件（§2.6 偵測列的既有結論）；task-notification 抵達後的 assistant 回合自身死於 API 層，PostToolUse 同樣不觸發（本案實證：00:51:10 通知落地後零 hook 事件）。能做的只剩「預測性掛哨」——那就是哨兵本人，不是新觸發點 |
| (c) 主 session halt 閂鎖（`quota_halt_actions`）擴充 | **次要採納**（修 4：多軸 reset 選擇），不能當主觸發 | halt 動作只在「session 還跑得動工具」時可達；本案 00:42 它跑到了，卻因 escalate-only 分支沒武裝；且撞線常發生在最後一次工具呼叫**之後** ⇒ 覆蓋面天生不完整 |

#### 閉環設計（修 1～修 4 合起來才是「零人工」）

```
任一層級撞線（主 session API 回合／Task subagent／workflow agent）
  │ harness 寫合成權威記錄進逐字稿（磁碟；已存在）
  ▼
哨兵巡邏（launchd StartInterval 900s 底盤／schtasks；已存在）
  │ 修1：任務書骨架重寫必保 RELAY 塊 ⇒ 哨兵讀得到自己的狀態（存活）
  │ 修2：狀態塊讀不出 ⇒ 先以 CLI 引數＋任務書檔名重建最小狀態塊、續巡（自癒）；
  │      重建不了才解除，解除必經 escalation.alert(loud=True)；三種失效痕跡分形
  ▼
unhandled_limit_event（判準 D；已存在）→ sentinel_decide=arm_reset（已存在）
  ▼
launchd StartCalendarInterval＝reset+skew（已存在，R83-B）｜Win schtasks -Once（已存在）
  ▼
到點醒來 → probe 一次探測（已存在）→ choose_resume_route 三態（已存在，Pkg-D）
        → claude -p -r <sid>（已存在）
  （修4：halt 武裝分支改取「≥halt 各軸中最早的 reset」，僅全軸皆無 reset 才 escalate-only）
  （修3：武裝／自癒／解除每步落痕跡且出聲——armed stamp、bootout log 已存在，
        缺的是 abort 分支的 alert 接線與派工面可見性）
```

憑證紀律（沿用 §6 與 CLAUDE.md〈反事後諸葛〉）：mac＝`launchctl print gui/501/<label>`
的 rc（不存在＝113）＋ plist 路徑回讀＋ calendar descriptor 回讀（launchd **從不**提供
NextRunTime，rc 才是憑證）；Windows＝`NextRunTime` 非空值。宣稱「已武裝」的每一處都
必須落這兩種憑證之一。

#### 交付下一波實作的工作清單（本包唯讀，僅落款設計）

| # | 改哪支檔 | 鎖的持有面（常數／史料／消費端） | 規模 | 測試要求 |
| --- | --- | --- | --- | --- |
| 修1 | `tools/session_resume_planner.py`（main 預設寫出路徑 :1388-1394：寫骨架前先 `parse_relay` 舊檔，有狀態塊則寫完骨架後 `write_relay` 回填） | 常數 `RELAY_BEGIN/END`、`parse_relay`/`has_relay`/`write_relay` 皆同檔 ⇒ 單包可完成 | ~10-15 行（該檔 guardrail_cli tier 上限 750，新增需以搬史料抵銷） | 紅綠自證：對已含 RELAY 的任務書跑預設路徑 → `parse_relay` 非 None 且 state 逐格保留；紅面＝現行程式必紅 |
| 修2 | 同檔 `_sentinel_tick` :1263-1274（abort 前先嘗試以 `args` 重建最小狀態塊續巡；重建不了才 `_abort_and_unregister`，且該路徑補 `escalation.alert(loud=True)`；三種失效訊息比照 `_resume_tick` 分形） | `escalation.alert` 住 `tools/lib/quota_escalation.py`（消費端已 import）⇒ 單包可完成 | ~20-30 行（同上 LOC 抵銷） | `SentinelDecisionTest` 加分支：狀態塊缺席×逐字稿存在 ⇒ 不得 unregister；alert 有被叫到（注入驗證） |
| 修3 | `tools/session_resume_planner.py` `--pace`/`--check` 輸出面加「哨兵活性」欄（armed stamp vs `launchctl list`/`Get-ScheduledTask` 現查對比，不一致即出聲） | 讀數層 `schedule_backend.select()` 已有查詢原語 ⇒ 單包可完成 | ~15 行 | 斷言不一致時輸出含警語；一致時安靜 |
| 修4 | `tools/lib/quota_messages.py` `reset_branch`（簽名擴充：收全軸、取 ≥halt 中最早可 reset 軸）＋ `tools/lib/quota_gate.py:836-841` 呼叫端＋`binding_resets_at` 消費端 | 🔴 常數（quota_messages）＋消費端（quota_gate、context_budget_guard 訊息）＋測試（test_quota_policy.py）**跨三檔** ⇒ 依鐵律七不得拆給並行包，單包整案 | ~30 行 | 紅面＝本事故重演：binding=extra_usage@None 且 five_hour@+3h ⇒ 必須 arm 而非 escalate；全軸無 reset ⇒ 仍 escalate |

🔴 前置協調：`sentinel_lifecycle.py`／`session_resume_planner.py`／`context_budget_guard.py`
現正由收尾包終驗中——實作波動工前先與收尾窗口對時序，不得並行同檔。

#### 誠實劃界

- 睡著的 Mac 仍不會醒（§2.6 已知限制 4 之後段、CLAUDE.md〈mac 已知邊界〉）：本設計
  交付的仍是「醒著必動作＋失效可偵測」，不是「必然喚醒」。
- 修 1 之後任務書仍是雙寫者（只是兩個寫者都保 RELAY）；徹底解法（狀態塊分檔）動
  `guard.PLAN_PREFIX` 持有面，與 §3「任務書搬家」列同型 ⇒ 列為候選不採。
- 00:42 觸發面歸因依據是排除法＋鍵名普查（上表下方那段），不是直接痕跡（halt 閂鎖
  不記 session 與觸發工具）；修 4 實作時應讓閂鎖多記 `session_id` 與 `tool`，把這種
  歸因從推理變成讀檔。

### 2.10 自願停機後的喚醒：活動判準＝對話記錄；harness 2.1.303 的三種限額記錄（R214；DEF-200-560～562）

2026-10-21 03:55 主控依 harness 寬限提示自願收尾，額度 04:00 回來，哨兵 04:10～07:55 巡邏 16 次全判 `patrol`（「逐字稿 N 秒前仍有更新」），沒有人叫醒它。三根因：

- **RC-A（DEF-200-560，P1）**：「還活著」讀檔案 mtime；harness 閒置時每小時追加無 timestamp 的 `cost-state`／`last-prompt`／`file-history-snapshot`、收尾後寫 `system/away_summary` ⇒ mtime 永遠新。`halt_verdict` 的「兌現時刻後仍有活動 ⇒ 已自行續跑」與 6 小時自我解除同病。
- **RC-B（DEF-200-561，P2）**：repo 根 `.env` 的 `AUTOSDD_RESUME_OFF=1` 讓本機每支哨兵都寫 `allow_resume:false`（額度回來只探測、不續跑），簡報與 `--pace` 都不說。
- **RC-C（DEF-200-562，P2）**：偵測面只認 `type=assistant`＋`<synthetic>` 與 `resets 9am`；寬限提示（user，`usageLimitNote:"wrap_up"`）、切斷通知（system，`continuing automatically at <時刻>`）、續接記錄（`auto-continuation`／`Usage limit reset`／`usageLimitNote:"release"`）都不在偵測面。

**判準**（`tools/lib/transcript_activity.py`）：活動＝**對話記錄**＝`type=assistant`（含 subagent 檔）的 timestamp，或 `type=user` 且 `origin.kind` 為 `human`／`auto-continuation` 者的 timestamp。不算：寬限提示（`isMeta`、無 `origin`）、tool_result 型 user、`type=system`（含 `away_summary`）、`attachment`、無 timestamp 的 `cost-state`／`last-prompt`／`file-history-snapshot`、`queue-operation`。⚠ `isMeta` 不是判準：auto-continuation 自己就是 `isMeta:true`。

**優先序**：真撞線事件 ＞ halt 標記 ＞ 寬限提示（`grace_verdict`）＞ idle。寬限提示通道獨立於既有事件那條路（它沒有 reset 時刻，塞進去會走到「解不出 ⇒ escalate ⇒ 哨兵自拆」）。新 `reset_source` 值 `harness-cutoff-notice`（harness 切斷通知自報的續接時刻，是觀測值不是猜的）登記為 `relay_machine.RESET_SOURCES` 的第 7 格。

**與 harness 自動續接共存**：harness 只在「turn 被切斷且視窗仍開」時自動續接（切斷通知→`Usage limit reset`→`auto-continuation`）；自願收尾不會。⇒ 兌現時刻之後有對話記錄＝已續跑；對話靜止不滿一個巡邏間隔不叫醒（防雙窗）；切斷通知自報的時刻未到 ⇒ `arm_reset` 排到那一刻。寬限提示之後出現續接記錄（`auto-continuation`／`release`／`Usage limit reset`）、或寬限期（`GRACE_ALLOWANCE_SECONDS`，與巡邏間隔同值）之後仍有對話＝已處理。

**落點**：新檔 `tools/lib/transcript_activity.py`（只 import `quota_limits`／`quota_messages`，不被它們、`quota_gate` 或 hook import；消費者＝planner 與測試）。`session_resume_planner.py` 與 `quota_messages.py` 皆已滿載，`quota_limits.py` 被 hook 再匯出，放進去會擴大 hook 的 import 面。逃生口說明（RC-B）住 `session_brief.escape_hatch_note`，簡報與 `--pace` 共用。

**已知邊界**：① harness 自動續接與哨兵探測之間有至多一個巡邏間隔的競態窗；② 寬限期是挑的、不是量出來的（實測收尾 40 s／91 s，無契約值）；③ `continuing automatically at` 無日期無時區（以切斷記錄當下的時刻、`now` 的時區解成下一個未發生者）；④ 寬限提示通道不看 `superseded_by`（他 session 接手）；⑤ harness 於 auto-continuation 之後 9～18 ms 再附一筆 `usageLimitNote:"release"` 記錄（isMeta、無 origin；內文「Earlier usage-limit notes no longer apply」），視為續接訊號、不是提示——`note_at` 只認 `wrap_up`，未知值一律忽略（寧可不叫醒）；此前把它當提示是 P1 誤判（QA 鏡審 F-1，已修）。逐項與真機重放證據見 `docs/06_quality/CrossPlatform_R214_Sentinel_GracefulHalt_Evidence.md`。

### 2.11 雙駕駛：harness 已續接 ⇒ 事件已處理；同 sid 另有駕駛 ⇒ 不 spawn、不續棒（R214；DEF-200-564／565／566／567）

2026-10-21 14:01～14:23（真實 sid `e9f8e2cb-c1fd-4234-8f8a-f1c546529cf1`，非構造痕跡）：harness 2.1.305 於 14:01:35 把被切斷的互動視窗自動續接（`origin.kind=auto-continuation`，9 ms 後附 `usageLimitNote=release`；名目 reset 14:00、實際晚 95 秒），哨兵 14:02:00 醒來（reset＋`RESET_SKEW_SECONDS` 120 s）、對話僅靜止 24 秒，卻判「未處理撞線」走 probe → `SESSION_RESUME`：第一支無頭 leg（14:02～14:09）與互動視窗**共用同一份逐字稿與工作樹**；leg 改了 1 個檔，relay 把它算成進度（`relay_spawned seq=1 files_changed_prev=1`），14:11 又起第二支 leg（～14:23）。兩支 leg 的 PowerShell 全被拒（DEF-200-563）。五小時額度 14:11→14:20 升 18 pp（每支 leg 以 Fable 重載 8～11 MB 逐字稿）。

兩根因（碼位為修前）：
- **RC-D（DEF-200-564）**：`sentinel_decide` 撞線分支不讀對話活性；「已處理」判準 `quota_limits.unhandled_limit_event` 只認事件後**帶 `usage` 的真 model assistant 記錄**，harness 的 auto-continuation／release user 記錄不算 ⇒ 續接後首則回應落檔前（長 turn 可達數分鐘）事件仍判未處理。
- **RC-E（DEF-200-565）**：`relay_machine` 四判準沒有「同 sid 另有駕駛」；`files_changed`（spawn 前後 `git status` 差集）把互動視窗與它的子代理改的檔也算成 leg 的進度 ⇒ 互動視窗越忙 relay 越停不下來；`--resume-tick` 路徑不經 `sentinel_decide`，`_run_resume` spawn 前沒有任何「有人在開車」的閘。

**判準（單一家＝`tools/lib/transcript_activity.py`；各層只取數、不自帶第二份）**

| 層 | 判準 | 落點 |
| --- | --- | --- |
| D2 事件已處理 | harness 續接記錄（`type=user` 且 `origin.kind=auto-continuation` 或 `usageLimitNote=release`）晚於撞線事件 ⇒ 已處理；`recovered_at = max(最後成功回應, 最新續接記錄)`。字面只有一個家＝`quota_limits.RESUME_ORIGIN`／`NOTE_RELEASE`／`is_resume_record`（`transcript_activity` 的對話判準與 `usage_limit_signals` 皆取用，不留複本） | `quota_limits.unhandled_limit_event`／`latest_resume_at` |
| D1 有沒有別的駕駛 | `driver_after(逐字稿, since, now)`＝since 之後、now 之前**第一筆非合成**對話記錄 `{timestamp, kind}`（真 model 的 assistant，或 `origin.kind ∈ {human, auto-continuation}` 的 user；`<synthetic>` 限額記錄本身、tool_result、peer／task-notification、system、attachment 都不算；含近 24 小時的 subagent 檔）。`live_driver(逐字稿, now, 事件)`＝`since` 取「事件時刻」與「一個巡邏間隔前」的較晚者 | `transcript_activity.driver_after`／`live_driver` |
| D3 哨兵 | 撞線分支在月度上限 escalate 之後、reset 判斷**之前**問 `live_driver`；有 ⇒ `patrol`（理由寫明另一駕駛與距撞線秒數）；`driver=None` 時既有五分支逐位元組同行為；痕跡 `sentinel_decided.driver_after` | `planner.sentinel_decide(driver=)`／`transcript_activity.driver_verdict` |
| D5 spawn 前閘 | `_run_resume` 在 A-PRE 之後、spawn 之前問同一個 `live_driver`，**帶錨**（`spawn_anchor`：`state["relay_prev_end"]`〔`settle_window` 排下一窗前寫入、隨狀態塊落盤，另給 2 s 收尾落盤寬容〕與逐字稿現算的未處理撞線事件時刻**兩者取較晚者**（QA 複審 R2：過期的 prev_end 不得遮住較新的撞線）；皆無 ⇒ 近期窗〔寬限／halt 路徑，以及修前武裝、狀態塊沒有 prev_end 的進行中 relay〕；痕跡 `anchor` 帶值與來源）；有 ⇒ 不 spawn、痕跡 `resume_refused_other_driver`、`route_strategy=REFUSE`、`other_driver=true`、回 1（與 A-PRE 同型，`_resume_tick` 現有三元式判 `resume_failed`） | `planner._run_resume` |
| D4 relay 第五判準⓪ | spawn 後同一份逐字稿出現 ≥2 條**鏈頭** ⇒ `state["other_driver"]`；`next_state(other_driver=)` 排在③之前（判定序 ⓪→③→④→②→①），真值表 16→32 格；新次態 `OTHER_DRIVER_STOP`：`relay_stopped why=other_driver`、loud、持久結局 `other_driver`、不續棒、重掛哨兵；`files_changed` 保留但有 other_driver 時不構成進度 | `transcript_activity.chain_heads_after`／`relay_machine.other_driver`／`next_state`／`resolve` |

**與任務書的兩處偏離（理由＝防雙保險反過來造成永不續跑）**
1. D3／D5 的「有人在開車」不是單看「事件之後有記錄」，而是**再加一個巡邏間隔的近期窗**（`HALT_QUIESCE_SECONDS`，與寬限提示「不叫醒」同一把尺）。只看事件之後：使用者撞線後戳了一下死視窗就走，那筆人類記錄永遠在事件之後 ⇒ 哨兵永遠 patrol、reset 後再也不替走掉的人續跑。D5 的 `since` 不採 `state["reset_at"]`（狀態塊的 `reset_at` 可能是上一個視窗的殘值，直接 probe 的路徑上更是空的 ⇒ 殘值會讓每次 spawn 被永久拒絕）。**修復棒二（QA 鏡審 P2-1／P3-1）**：D5 光有近期窗不夠——無頭 leg 與互動視窗寫同一份逐字稿，relay 下一窗在收窗後 `RESET_SKEW_SECONDS`（120 s）起、遠小於一個巡邏間隔，前一棒自己的記錄會被當成另一駕駛（第二棒必被拒並報假的雙駕駛警報；真實事故兩棒間隔 156 s）；首棒撞線前緊貼限額記錄的最後一則真回應同理。故 D5 帶錨（見上表 D5 列；兩錨取較晚者）；退路「now − 窗」只在寬限／halt 路徑，與修前武裝、狀態塊沒有 `relay_prev_end` 的進行中 relay 走到——後者的第二棒仍可能被近期窗誤拒（多拒不多開；下一次武裝即有錨），列為已登記殘留。
2. 鏈頭判準字面修正：任務書寫「`uuid` 不是 spawn 後任何記錄的 `parentUuid`」描述的是鏈**尾**；實測成立的是鏈**頭**＝`parentUuid`（compact 邊界取 `logicalParentUuid`）不指向 spawn 後任何記錄者。compact 邊界的 `parentUuid` 為空，不取 `logicalParentUuid` 會把單一駕駛的 compact 誤算成第二條鏈。

**實測依據（本機逐字稿，唯讀）**：把全部 155 支逐字稿中 `entrypoint=sdk-cli` 的連續段（＝無頭 leg，記錄間隔 ≤300 s 併為一段）逐一算鏈頭——119 段裡 **118 段單駕駛恰 1 條**（最長 5,152 秒；其中 bf8f13ee 含 1 次 compact 邊界，不取 `logicalParentUuid` 會算成 2 條＝把單一駕駛誤判成雙駕駛）、**1 段＝事故 e9f8e2cb 的兩支 leg（間隔不足 300 s 併為一段）恰 2 條**（一條 `sdk-cli`、一條 `cli`；不取 `logicalParentUuid` 為 4 條）。重放探針 `tools/probe/sentinel_decide_replay.py --sid e9f8e2cb-… --now 2026-10-21T14:02:01+08:00`：舊判準 `probe`（花探測＋spawn 第二個駕駛），新判準 `patrol`（D2：事件已被 14:01:35 的續接記錄處理）；把 D2 關掉、只留 D3 閘同樣 `patrol`（理由「撞線後 9772s 已有另一駕駛的對話記錄（auto-continuation）」）——雙保險各自擋得住。逐項輸出見 `docs/06_quality/CrossPlatform_R214_Sentinel_GracefulHalt_Evidence.md`〈八〉。

**〈邊界〉誠實劃界**
- 視窗開著但靜止 ≥ 一個巡邏間隔、人回來才打字的那種雙駕駛仍是 §2.10 設計面接受的風險，本輪不解（D4 只在那支 leg 跑完後停棒，最多重疊一棒）。
- D5 看不到「互動視窗在一個巡邏間隔以上都沒寫任何記錄」（例如單一長工具呼叫）的雙駕駛；D4 事後以鏈頭補。
- `uuid`／`parentUuid`／`logicalParentUuid`／`isSidechain`／`origin.kind` 皆為 harness 2.1.30x 的**實測欄位、不是契約**；任一改名 ⇒ 鏈頭數退回 0／續接記錄不辨識＝退回修前行為（fail-safe 方向：不誤停、不誤判處理）。`entrypoint`（`cli`／`sdk-cli`／`claude-vscode`）亦是實測值，故判準**不讀**它（被否決的「以 entrypoint 分辨互動與無頭」）。
- harness 自動續接時刻與名目 reset 有差（本例 95 秒）；哨兵 `+120 s` skew 剛好晚於它，窗口只有 25 秒——這是 D2 必須存在的原因，不是巧合可以仰賴。
- **`~/.autosdd/context_feed/<sid>.json` 的 `ts`（statusLine 信標，D6）不作第二訊號**。三態實測（本機，唯讀）：busy＝`ts` 與最後一筆 assistant 記錄相差 ≤1 s（14:48:54 對 06:48:54Z）；開著但無對話（本窗 19:07:52 起）＝`ts` 凍結 9 分 32 秒、至 19:17:24 才被背景任務通知事件推動一次（19:17:41 的 task-notification），**事件驅動、不是心跳**；視窗關閉＝凍結在最後一次渲染（d6dfce97 於 05:04:49 後凍結，視窗 07:54 才關，其間兩小時五十分 `ts` 不動）。結論：開著的閒置視窗與已關閉的視窗在信標上分不開，信標證不了「有人活著」，只證「某事件觸發過渲染」——不用，只登記邊界。「idle 10 分鐘」無法由子代理受控構造（主控窗須閒置），以上為自然樣本。
- **D9（DEF-200-566）hook 自動武裝的任務書落點**：hook 的 `write_resume_plan`／`arm_when_earned` 此前用 `tempfile.gettempdir()`，planner CLI 預設與 `reap_plans` 早在 2026-09-05 事故後改住 `endurance_env.plan_dir()`（持久：等額度期間系統暫存會被清）⇒ 同 sid 兩份任務書、排程 Action 各指一份（事故當日 hook 武裝指 `%TEMP%`、主控手動 `--arm-sentinel` 把 Action 改指 `~/.autosdd/plans`）。修法＝甲：hook 以 `from endurance_env import plan_dir` 取同一個家（不留第二份目錄解析；hook raw 行數 1089 不變）；`sentinel_lifecycle.gc` 預設讀 `plan_dir()`（顯式 `tmp_dir` 仍同一格，其餘痕跡仍在系統暫存）；測試圍籬 `fence_enter` 把 `AUTOSDD_PLAN_DIR` 釘進隔離根（`<root>/plans`），免得全套 in-process 的 hook 路徑把 fixture 任務書寫進真實 `~/.autosdd/plans`；`test_the_hook_and_the_cli_arm_the_plan_in_the_same_directory` 釘「兩個入口武裝出來的是同一個檔」。**舊任務書處置**：修前已武裝的 session 在該 session 內仍用 `%TEMP%` 那份（排程 Action 指它）——tick 照常讀它、**不自動搬、不砸**（免得無人回合動檔），只在痕跡 `sentinel_decided.plan_in_temp` 出聲；下一次武裝（新 session 的 hook 武裝，或任何一次 `--arm-sentinel`）以 `-Force` 用新路徑重註冊同名排程，Action 從此指向 `plan_dir()`；`%TEMP%` 舊檔不再被讀、也不被自動收（`reap_plans` 只掃 `plan_dir()`），交系統暫存清理（一次性、量有限）。已知殘留窗：修前武裝的 session 在被重新武裝之前若有人手動 `--arm-sentinel`，同事故形態仍會重現一次（兩份任務書）——量有限、不再擴大。
- **D10（DEF-200-567）任務書 §3 填入**：喚醒 prompt 要 leg「照任務書第 3 節做」，而骨架 §3 只有 `claude -r` 與 TODO（事故兩支 leg 的 handback 都記這件事，只能讀記憶檔自救）。`--arm-sentinel`／`--arm-endurance` 武裝時，同 sid 的 handback（`resume_route.handback_report`）存在且「## 下一步指令」節非空 ⇒ `relay_machine.handback_next_steps` 把該節原文填進 §3 的 TODO 位置（同一份文件、標明來源路徑與 handback mtime，並重申「宣稱不是證據」）；否則 §3 留 TODO（與修前逐字相同），武裝成功時在憑證旁印一行「⚠️ 任務書 §3 仍是 TODO…」；喚醒 prompt（`_RESUME_RULES`，SESSION_RESUME 與 FRESH 兩條路共用的唯一常數）加一句「任務書 §3 為 TODO 時，先讀 handback 與記憶檔〈可重啟點〉再行動」——只有指引、不含任何指令內容（2026-09-07 裁決「不注入 Workflow 續跑提示」仍由 `test_the_resume_prompt_never_names_a_workflow_resume_call` 釘住）。解析邊界：handback 原文若含 relay 狀態塊定界字串（`RELAY_BEGIN`），`parse_relay` 的 `text.find` 會先命中注入處——現 `~/.autosdd/handback/*.md` 命中 0 筆（理論，不加守衛）。骨架（不帶武裝旗標）一律不代填：那是人要填的欄位。

### 2.12 無人窗口是 print 模式：harness 背景等待上限、牆鐘同源、無人窗口能做什麼（R214；DEF-200-574／575；掌舵者 2026-10-31「找出根因避免、檢討架構」）

2026-10-31 11:02～11:32（真實 sid `e4142f11-9540-4830-bd1f-a8188dd9b35a`，非構造痕跡）：哨兵自 `c61e3847` 的 halt 標記於 reset 後喚醒，因該逐字稿 35 MB 超上限走 FRESH_SESSION_WITH_STATE；無頭主 agent 重驗（git／digest／docker／全套）後派兩支 Sonnet QA 鏡（任務書預算 120／150 分鐘）、寫 handback 初版、**收尾回合等完成通知**——在互動視窗這是正確形態。harness 2.1.314 在 print 模式於最後一個回合後只等背景任務 **10 分鐘**，然後把兩支鏡與一支背景 shell 全部停掉並結束行程（stderr 逐字 `Background tasks still running 10m after the last turn (…); stopping them. Set CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 to wait indefinitely.`）。relay 見 `files_changed=0` 判 no_progress（INV4 正確地沒有再 spawn），五小時額度軸 0% → 約 20%、零落地（沒有 commit／push／報告）。同一窗另發現根層全套對 `AUTOSDD_UNATTENDED` 不密閉（七紅，DEF-200-574）：無人窗口連「重驗全套綠」都拿不到，只能靠子行程清變數的隔離跑法自救。

**根因（三層，皆結構性）**
1. spawn 環境從未設 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`；§2.5 與 `resume_route` 檔頭的「三層界住」（`max_spawns`＋1 小時牆鐘＋INV4）從未把 harness 自己的上限算進去，而它比我們的牆鐘短六倍。
2. 牆鐘 `timeout=3600` 與任務書給 QA 鏡的 120～150 分鐘預算自相矛盾：即使 harness 不殺，第 60 分鐘 `subprocess.run` 也會砍——同一個「續航救 session、死的是扇出」形態（memory `endurance-saves-session-but-fanout-dies`）。
3. 進度判準 `files_changed>0` 對無人窗口**合法能做的事**（唯讀 QA、測試證據、handback）結構上為 0：INV4 的停是對的，但痕跡上與「主 agent 沒起來」分不開，修法會被導向錯的地方。

**決策**
- 常數**單一家** `tools/lib/unattended_authz.py`：`RESUME_BG_WAIT_CEILING_SECONDS`＝4 h（注入 spawn 環境，harness 自己有序收掉）、`RESUME_HARD_WALL_SECONDS`＝4.5 h（planner `subprocess.run` 的外層硬牆，只在 harness 自己掛死時動用）、`schedule_backend.DEFER_WAIT_CAP_SECONDS`＝硬牆＋300 s（macOS 延後 bootout 上界）。三者方向鎖＝`test_context_budget_guard.py::PrintModeBgCeilingTest`、`test_mac_endurance_r83.py::…outlives_the_longest_thing…`（planner 的 timeout 必須是具名常數的參照、不是字面）。數值 WHY：QA 鏡 150 分鐘＋主 agent 前後各約 15 分鐘 ≈ 3 h，取 4 h 留裕度、仍短於一個五小時額度窗（額度耗盡由額度守衛與哨兵管，牆鐘只防掛死）。
- 喚醒 prompt（`_RESUME_RULES`，兩路共用）把預算講給醒來的主 agent：本回合是 print 模式、harness 最多再等 N 分鐘、派棒總預算必須小於它、每棒邊做邊把成果寫進 handback 目錄（被殺時成果不歸零）、等待期間不自造輪詢迴圈。
- 叫人的理由點名成因：spawn stderr 帶 harness 標記 ⇒ `state["harness_bg_kill"]`、痕跡 `resumed.bg_ceiling_kill`／`relay_stopped.harness_bg_kill`、AUTOSDD_ATTENTION.md 的理由附 `relay_machine.HARNESS_KILL_NOTE`（`stop_reason()` 純函式）。
- 全套姿態圍籬（DEF-200-574）：runner 在 `console_orphan_census.wrap` 之內、`leak_fence` 之外包 `unattended_authz.posture_fence`（剝 `AUTOSDD_UNATTENDED`、worker 子行程同享、結束還原）；`ProbeOpennessIsAPositiveVerdictTest.setUp`／`_probe()` 與 `SiTestCase._STRIP` 自釘。鎖＝`test_run_root_unittests.py::UnattendedPostureFenceTest`、同檔兩道 AST 接線鎖不變。
- **刻意不改**：INV4（一次沒進度就停——無人窗口沒有「下一窗再來一次」的理由，人回來看 handback）；`files_changed` 判準（唯讀工作不算進度是保守方向，改寬會讓 relay 多燒一窗）；模型角色（主控 fable／子代理 sonnet；**無人窗口主控是否降為 Sonnet**＝掌舵者裁決事項，見 §7 第 9 項）。

**被否決**：(a) `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0` 無限等——掛死的子代理會讓 tick 行程卡到硬牆才死，而硬牆是 `TerminateProcess`、扇出與 shell 孤兒無人收；有限上限讓 harness 自己有序收。(b) 牆鐘拉到整個五小時窗——牆鐘不是額度煞車，額度煞車在額度守衛；牆鐘只防掛死。(c) 要主 agent 在 print 模式用前景輪詢等棒——鐵律六禁止的形態，且 PowerShell 工具單次上限 10 分鐘。(d) 關掉自動 spawn 只留巡邏——掌舵者 2026-10-31 明示「完成續跑機制、不是拆掉；Token 監控不能壞」。(e) 把常數塞進 `resume_route`／`schedule_backend` 其一再互相 import——`schedule_backend` 在 hook import 面上，拖進 `resume_route` 會把 `model_roles`／`quota_*` 一起拉進 hook；`unattended_authz` 是兩支 hook 已在用的葉模組，零新增 import 面。

**量測（本次事故，非估計）**：五小時軸 11:02 0% → 11:46 21%（本互動窗自己約 2 pp）；無人 spawn 歷史 5 窗（2026-10-21 起）：DONE 1、no_progress 2（含本事故）、other_driver 1（DEF-200-573）、另 1 窗 no_progress（10-21 haiku 窗）。修法後要盯的是**產出率**，不是發現率——見 §7 第 8 項。

---

### 2.13 session 掌控與切換（sessionctl）：續跑成本選路、過期 session 不續跑、交接包、背景代理名冊、模型平衡（2026-11-14；第一、二段皆已落地；DEF-200-580～584）

> 量測值一律現查（`python tools/lib/quota_policy.py --print-env-example`），本節只寫判準、資料來源與方向。
> 🔴 **落地狀態是本節的第一張表；各段落若與表下方〈第二段實作事實（§2.13.13）〉有差異，以 §2.13.13 為準（它寫的是實作，不是設計）。**

| 決策 | 內容 | 狀態 | 證據座標 |
|---|---|---|---|
| D2 | 無人選路量續跑成本（R1～R3）而非檔案大小 | 已落地（2026-11-14）；**R1／R3 自 v2.1.22 起退役、改 F4 成本選路，見 §2.19** | `tools/lib/sessionctl/switch.py`；`tools/tests/test_sessionctl_switch.py`（RouteTest、ThresholdTest）；AT-SC-01～18 |
| D3 | 過期 session 不續跑（SUPERSEDED），`sentinel_decide`＋`_resume_tick` 兩處接線、`reap_verdict` 一致 | 已落地（2026-11-14） | 同上（SupersededTest、E2ReplayTest、ReapSupersededTest、SupersedingSinceTest 皆在 `tools/tests/test_sessionctl_switch.py`）；`tools/tests/test_context_budget_guard.py`（SentinelDecisionTest、SentinelReapVerdictTest）；AT-SC-19～33 |
| 圍籬修正 | 洩漏圍籬不把活著的互動 session 合法武裝的哨兵判成洩漏（§2.13.11） | 已落地（2026-11-14） | `tools/lib/sentinel_lifecycle.py::leak_fence`；`LeakFenceTest` |
| D4 | 交接包（機械層＋主控層、公告／ack／過期） | 已落地（2026-11-14） | `tools/lib/sessionctl/handoff.py`、`tools/lib/sessionctl/handoff_build.py`；`tools/tests/test_sessionctl_handoff.py`；AT-SC-34～49 |
| D5 | 三條切換路（無人／互動自動／手動）、洗環境 | 已落地（2026-11-14；FRESH prompt 的 `handoff_path` 縫已由 planner 接線） | `tools/lib/sessionctl/handoff.py`（`spawn`、`washed_env`、`advise_once`）；`tools/sessionctl.py`；AT-SC-50～60 |
| D6 | SendMessage 續棒成本閘 | 已落地（2026-11-14；門檻鍵 `AUTOSDD_RESUME_AGENT_TOKENS` 由 `roster.resume_gate` 消費） | `tools/lib/sessionctl/roster.py`；`.claude/hooks/sessionctl_guard.py`；`tools/tests/test_sessionctl_hooks.py`；AT-SC-61～65 |
| D7 | 名冊、`sessionctl status`／`stop`、Stop 出聲、無人窗口結局、`pct_before`／`pct_after` | 已落地（2026-11-14） | `tools/lib/sessionctl/roster.py`、`tools/lib/sessionctl/procstop.py`；`tools/tests/test_sessionctl_roster.py`；AT-SC-66～80 |
| D8 | 模型平衡建議（`--pace` 一行） | 已落地（2026-11-14） | `tools/lib/sessionctl/modelmix.py`；`tools/tests/test_sessionctl_modelmix.py`；AT-SC-81～84 |
| hook 面 | 新增 `sessionctl_guard.py`、`context_budget_guard` 加 `switch_advice` 呼叫 | 已落地（2026-11-14；`.claude/` 由主控親套） | `.claude/hooks/sessionctl_guard.py`；`tools/tests/test_sessionctl_hooks.py::GuardRegistrationTest`；AT-SC-85～88 |
| watch／監督（R3） | `sessionctl watch` 背景監督程序（交卷／停滯／超時／額度／保溫叫醒）、監督憑證與 Stop 監督閘、PreToolUse 派工附註、`status` 監督一行 | 已落地（2026-11-17，未提交；真機待做）→ §2.18 D1 | `tools/lib/sessionctl/watch.py`、`supervise.py`；`tools/tests/test_sessionctl_watch.py`、`test_sessionctl_supervise.py`；FR-W1～W9、FR-S4、AT-W* |
| 封存／轉送（R3） | `--finalize` 升級為封存（`.sealed`＋prompts sidecar）、封存閘、已交棒判準、冷窗轉送與已交棒告知（`UserPromptSubmit`） | 已落地（2026-11-17，`7c38492c`；V-F1 第一步 PASS、第二步暴露 DEF-200-609 已修、待重測，見 §2.18.3）→ §2.18 D2～D4 | `tools/lib/sessionctl/seal.py`、`forward.py`；`.claude/hooks/sessionctl_guard.py`、`.claude/settings.json`；`tools/tests/test_sessionctl_seal.py`、`test_sessionctl_forward.py`；AT-S*、AT-F1～F8 |

第二段的承接帳本列 DEF-200-584 已結案；入口薄殼 `tools/sessionctl.py` 與 hook 皆已落地。🔴 互動視窗是否把 Stop 的 `systemMessage` 顯示給人、以及 TCS §3 的真機驗證 V1～V8，仍待主控真機目視，未驗。

### 2.13.0 立案與暴露證據（守衛面准入：三取一皆成立）

| 代號 | 證據 | 類別 |
|---|---|---|
| E1 | sid `d4ed2654-9181-4df1-a6e6-2d712956e23b`：事件檔 `%TEMP%\autosdd_resume_log_autosdd_resume_plan_d4ed2654-….jsonl` 2026-11-13T07:32:03 `route_chosen`＝SESSION_RESUME，理由「逐字稿 20,518,438B ≤ 上限 33,554,432B」；`~/.autosdd/traces/autosdd_resume_cost.jsonl` 同 sid 第一回合 `cache_creation_input_tokens`＝138,811；其後無人窗口以 SendMessage 續棒 40～60 萬 token 的舊子代理 44 分鐘，08:16 `relay_stopped` why=band，五小時窗 95～98%。掌舵者原話（逐字稿第 7846 行）「有背景Subagent執行, 沒有被掌控! 這是嚴重問題」 | 掌舵者真機回報＋非構造性逐字稿 |
| E2 | `AutoSDD_Sentinel_f1522ddb-bdcf-4104-bb81-614c1118fa9d` 自 11/9 起 state=`waiting`、`allow_resume: true`、NextRunTime 2026/11/15 02:02；逐字稿 29,652,867B、ctx 556,777；其間多個更新 session 已做完後續工作。若不處理，11/15 會無人續跑一個四天前的 session。主控已 `--remove-schtasks` 手動拆除 | 非構造性實況 |
| E3 | 掌舵者原話「盡量避免Fable Usage已經快100% Weekly Limit All Model Usage還剩很多」；`--pace` 20:27:47→20:39:45：five_hour 40→62、weekly_all 61→64、weekly_scoped(Fable) 9→14 | 掌舵者真機回報 |

結構性根因（三條，各對一個決策群）：
- **G-cost**：無人選路量「檔案位元組」而非「續跑成本」（上下文 token、壓縮次數、上一次續跑寫了多少快取），20 MB 逐字稿≈60 萬 token 仍判 RESUME（D2）。
- **G-stale**：哨兵 `waiting` 是唯一「永不收」的狀態（`sentinel_lifecycle.REAPABLE_WHEN_IDLE` 刻意不含它），而 `sentinel_decide` 的撞線分支優先於 `superseded_by`（DEF-200-532 只接在 halt 標記上）⇒ 撞線等待中的舊 session，即使人早已在別的 session 接手，reset 一到仍會被 probe→resume（D3）。
- **G-blind**：背景代理與無人窗口沒有名冊、沒有停止手段、沒有「本回合結束時還有誰在跑」的出口；續棒舊代理沒有成本閘（D6、D7）。

### 2.13.1 落點（單一家）

> 現況（2026-11-14，第二段落地後）：`tools/lib/sessionctl/` 含 `__init__`、`switch`、`handoff`、`handoff_build`、`roster`、`procstop`、`modelmix`，入口 `tools/sessionctl.py`，hook `.claude/hooks/sessionctl_guard.py`；`ENV_SPEC` 八個鍵（`AUTOSDD_SWITCH_R1_CTX_TOKENS`、`AUTOSDD_SWITCH_R2_COMPACTIONS`、`AUTOSDD_SWITCH_R3_CACHE_CREATION_TOKENS`、`AUTOSDD_STALE_SESSION_HOURS`、`AUTOSDD_RESUME_AGENT_TOKENS`、`AUTOSDD_HANDOFF_TTL_HOURS`、`AUTOSDD_ROSTER_QUIET_MINUTES`、`AUTOSDD_SESSION_SWITCH_MODE`）的消費端皆已接上。`choose_resume_route` 判定核心已自 `session_resume_planner.py` 搬進 `switch.py`，planner 留同名委派（LOC 748→725）。

| 元件 | 路徑 | 職責 | 不准做 |
|---|---|---|---|
| 選路與過期判準 | `tools/lib/sessionctl/switch.py` | `fresh_reasons()`（R1～R4）、`superseded_by()`（D3 判準唯一的家）、`stale_verdict()`（哨兵／續航用的判決字典） | 不 spawn；以純函式＋讀檔為主，只有兩處寫入：handback 目錄解析的冪等 mkdir、SUPERSEDED 命中後的處置（`settle_superseded`／`write_superseded_handback`：狀態塊、handback；由 planner 的哨兵與續航兩處呼叫）——以 `switch.py` 檔頭自述為準 |
| 交接包 | tools/lib/sessionctl/handoff.py | 機械層產生、主控層驗證（finalize）、公告／ack／過期、洗環境、互動 spawn | 不判「該不該切」（那是 switch） |
| 名冊與停止 | tools/lib/sessionctl/roster.py | 子代理三態、無人窗口、排程彙整；`stop` 的 pid 身分驗證與砍樹 | 不停視窗內子代理（harness 才做得到） |
| 模型建議 | tools/lib/sessionctl/modelmix.py | 兩條週軸的「用量比÷時間流逝比」→ 一行建議 | 不改任何派工參數（只出聲） |
| 入口薄殼 | tools/sessionctl.py | argparse → 上列函式；`from lib.sessionctl import …`（`selfimproving.py` 先例，避開與同名入口檔的 import 撞名） | 不含判準 |
| 門檻 | `tools/lib/quota_policy_env.py::ENV_SPEC` 新增三鍵＋`STALE_SESSION_HOURS`、`RESUME_AGENT_TOKENS`、`AUTOSDD_SESSION_SWITCH_MODE` | 經 `--print-env-example` 現查、`env.shared` 可覆寫 | 本節不寫數字以外的第二份預設值 |

既有檔只准「薄呼叫」：`session_resume_planner.py`（guardrail_cli，現查餘裕 ≈2 LOC ⇒ 先把 `choose_resume_route` 的判定核心搬進 `switch.py`、planner 留同名委派，騰出空間）、`quota_gate.py`（hub，餘裕 0 ⇒ 不碰）、`context_budget_guard.py`（SPECIAL_FILES raw-line 棘輪，餘裕 0 ⇒ 盡量不碰，見 §2.13.8）。

### 2.13.2 D2 無人選路：量「續跑成本」不量檔案大小（已落地）

**判準**（任一成立 ⇒ FRESH；理由字串逐條列出命中者，皆不成立 ⇒ RESUME）：

| 規則 | 資料來源（讀檔、零 token） | 預設門檻 | 缺值時 |
|---|---|---|---|
| R1 上下文 | 優先 `~/.autosdd/context_feed/<sid>.json`（`context_budget_guard.read_context_feed`）；缺席退逐字稿最後一筆 assistant usage（`context_budget_guard.scan_transcript` 的 `used`）；兩者皆缺才以位元組÷經驗比值估並在理由標 `estimated` | `ctx_tokens ≥ 250,000` | 三者皆不可得 ⇒ R1 不成立（量不到≠超標），但理由字串寫「R1 量不到」 |
| R2 壓縮次數 | 逐字稿 `compact_boundary` 計數（`context_budget_guard.compact_boundary_count`，**不用** `autosdd_compact_events.jsonl`：後者只記 hook 有跑到的那幾次，會少算） | `≥ 2` | 讀不動 ⇒ 0 |
| R3 上次續跑成本 | `~/.autosdd/traces/autosdd_resume_cost.jsonl` 同 sid 最近一筆 `cache_creation_input_tokens` | `≥ 100,000` | 無記錄 ⇒ 不成立 |
| R4 既有 | `fresh_why()`：sid 缺席／逐字稿缺檔／空檔／`size > RESUME_MAX_TRANSCRIPT`；`weekly_why()` 週軸 converge | 不變 | 不變 |

> 🔴 **v2.1.22 註記（R216，見 §2.19）**：上表 R1（25 萬）與 R3（上次續跑寫入 10 萬）**已退役**（掌舵者 2026-11-18：「專注在不要讓 Cache 過期」）；R1 的換窗職責由硬線 `AUTOSDD_SWITCH_HARD_CTX_TOKENS` 承接、R3 由 F4 成本選路取代（快取已冷才判）；R2 保留。本節 R1／R3 的文字與數字保留作決策史料，不再是現行判準。

- **方向鎖**：三個門檻只准下修（具名測試以「現值 ≤ 出廠值」釘住出廠值，env 覆寫若大於出廠值 ⇒ 退出廠值並出聲，同 `_transcript_cap()` 的病態值處理）。方向理由：放寬＝退回 E1。
- **fail 方向**：選路的降級只准 RESUME→FRESH（既有方向鎖不變）。量不到一律「不觸發該條」而非「觸發 FRESH」——FRESH 的代價是丟上下文，量不到不應單方面造成資訊損失；但 E1 型輸入（context_feed 不在、逐字稿可讀）R1 經 `scan_transcript` 仍量得到，回歸鎖以 E1 真實數值釘住。
- FRESH prompt 追加兩條硬規則（字面鎖）：①不得以 SendMessage 續任何舊 session 的代理，一律派新代理＋短任務書；②第一個動作＝重驗 `git status`／HEAD 與交接包內一切「已通過」宣稱。並改指向**交接包**（§2.13.4），任務書仍在 `--add-dir`（第二段已接線：planner 的 FRESH 路先呼叫 `handoff.ensure_mechanical` 取得交接包路徑再傳入 `handoff_path` 縫）。
- 互動視窗（第二段 D4／D5，已落地，實作細節見 §2.13.13）同一組 R1～R3（R4 不適用）由 PostToolUse 判定、**一個 session 只出聲一次**（閂鎖鍵 `switch_advised`，住 `state_path(sid)` 的既有閂鎖機制）：出聲同時產生交接包機械層（§2.13.4），訊息附交接包絕對路徑與 `python tools/sessionctl.py handoff --finalize` / `--spawn` 兩行指令。
- **不調 autocompact 門檻**（90% 不動）：見 §2.13.9 X1。

**實作事實（2026-11-14 落地；與上文有差異處以此為準）**

- `fresh_reasons()` 回傳 `(命中, 量不到說明)` 二元組而非單一清單：AT-SC-10 要求「R1 不成立但理由含『R1 量不到』」，命中與說明必須可分；`choose_resume_route` 的理由字串兩者皆列。
- R2 以逐字稿 `compact_boundary` 計數；R3 以新增的唯讀函式 `resume_cost.last_cost()` 取同 sid 最近一筆。
- R1～R3 與 `RESUME_AGENT_TOKENS` 的方向鎖：覆寫值大於出廠值 ⇒ 退出廠值並 stderr 一行；`STALE_SESSION_HOURS` 刻意不納入方向鎖（調小更積極拆哨兵、調大更晚拆，兩向都有風險；主控裁決 7）。
- FRESH prompt 加入兩條硬規則字面（`FRESH_HARD_RULES`）；`handoff_path` 參數縫已在，傳 None 時沿用任務書路徑、給了才改為「按交接包繼續：讀 <路徑>…」（第二段已由 planner 接線）。
- **裁決（主控，2026-11-14）：R1 位元組估計比值 40 B/token 接受為出廠值。** 兩個實測點：E1＝20,518,438 B／約 60 萬 token ≈ 34 B/token；E2＝29,652,867 B／ctx 556,777 ≈ 53 B/token。取 40 介於兩者之間、偏保守（少估一點）。該值**只在 feed 與逐字稿 usage 皆缺時使用**，理由字串一律標 `estimated`；它是量測值，不是真值，要重量由 `tools/probe/` 現查，不當常數寫進其他文件。

### 2.13.3 D3 過期 session 不續跑（SUPERSEDED；已落地）

**判準唯一的家**＝`switch.superseded_by(project_dir, own_sid, own_last_epoch, now)`：
1. `own_idle = now − own_last_epoch ≥ STALE_SESSION_HOURS`（預設 24h；`own_last_epoch`＝`transcript_activity.newest_conversation_at`，對話記錄而非 mtime，DEF-200-560 同尺）；
2. 同專案逐字稿目錄**直下**另有 `stem ≠ own_sid` 的逐字稿，於 `own_last_epoch` 之後累積到 `sentinel_lifecycle_arm.should_arm` 的門檻（≥24 回合且 ≥600s；同一把「算不算真的工作」的尺，`claude -p ok` 不會被當成接手）。
實作＝把現有 `superseding_session(project_dir, own_sid, halt_marker)` 的 `since` 來源抽成參數（`since_epoch`），halt 版變成它的一行包裝 ⇒ 兩個用途同一份掃描碼。

**接線（兩處，兩處都要，缺一即 E2 重演）**：
- `sentinel_decide`：新增最高優先分支（在撞線事件分支**之前**；月度支出上限 `LIMIT_SPEND` 仍先 escalate——錢的事人才能解）：`superseded` ⇒ `{"action": "disarm", "superseded_by": sid, "clear_halt": True, reason}`。理由：E2 的哨兵正處於 `arm_reset`→`waiting`，醒來時撞線事件仍「未處理」，若 SUPERSEDED 排在撞線分支之後，它永遠輪不到。
- `_resume_tick`（`-Once` 續航排程與 relay 下一窗直接進這裡，不經 `sentinel_decide`）：在 `probe_quota` 之前呼叫同一個判準，命中 ⇒ `_abort_and_unregister(…, event="superseded")`。
- 兩處命中時一律：自我解除排程、狀態塊寫 `superseded`（新增終態，加入 `TERMINAL_STATES`）、痕跡 `sentinel_superseded`、寫一份 handback（`resume_route.handback_report(sid)`，`## 做了什麼`＝「判定已被 <sid8> 接手，未續跑」、`## 下一步指令`＝`claude -r <sid>` 手動續的指令），由既有 `announce_handbacks` 在下次 SessionStart 出聲。**不叫桌面告警**（這是正常下班，不是故障）。
- **整週無人仍續航**：條件 2 不成立（沒有更新的 session）⇒ 照舊撞線分支，行為逐位元組不變。
- **`reap_verdict` 一致性（不得兩個家）**：GC 呼叫端對 `waiting` 的哨兵先算 `switch.superseded_by(...)`，把結果以新關鍵字參數 `superseded: bool` 傳入；`reap_verdict` 只在 ⑥ 加一條「`superseded` ⇒ 收」，判準本身不重寫。`waiting` 且未 superseded ⇒ 仍不收（原紀律不變）。
- **fail 方向**：fail-closed 往「續航」那側（量不到 ⇒ 不判 SUPERSEDED）。理由同 `superseding_session` 檔頭：判 SUPERSEDED 的後果是拆排程（不可逆），量不到≠已接手。代價誠實寫：讀不到其他逐字稿時 E2 仍會重演——由 `sessionctl status` 的「過期哨兵」欄出聲兜底（§2.13.6）。

**實作事實（2026-11-14 落地）**

- `switch.superseded_by／stale_for／stale_verdict／settle_superseded／write_superseded_handback／own_last_at` 是判準與處置的單一家；`sentinel_lifecycle_arm.superseding_since()` 抽出 `since` 參數，`superseding_session`（halt 版）變成它的包裝，兩個用途同一份掃描碼。
- `sentinel_decide` 新增關鍵字參數 `stale`：分支位於「有未處理撞線事件」區塊內、`LIMIT_SPEND` 之後、driver／reset 判斷之前（月度支出上限仍先 escalate）。`_resume_tick` 在 `reset_not_reached`／probe 之前也套用同一判準（reset 未到也先拆，因判準與 reset 無關）。
- 命中處置：狀態塊 `superseded`（`TERMINAL_STATES` 新增）、清 halt、拆排程、痕跡 `sentinel_superseded`、handback `<sid>_superseded.md`（四 marker 齊，含 `claude -r`；檔名刻意不蓋掉同 sid 的續跑 handback）。`reap_verdict(superseded=)` 與 `gc` 只對 `waiting` 計算，判準經 `planner.switch.stale_for`，沒有第二個家。
- **裁決（主控，2026-11-14）：沒有撞線事件的過期 session 照既有閒置解除路徑處理，狀態為 `disarmed`，不另標 `superseded`、不寫 handback。** 理由：無撞線事件時沒有任何「該續跑而被攔下」的決定需要記錄，既有 idle disarm 與 grace→probe→`_resume_tick`（該處接線攔下）結果等價；若要無事件也標 `superseded`，須把分支提到最頂層並自帶 `LIMIT_SPEND` 豁免，擴大射程而無暴露證據（守衛面准入）。
- 痕跡 `sentinel_superseded` 與 handback 在 `announce_handbacks` 的標題措辭（「無頭續跑窗口的交接檔」）對它略不貼切，未改（hook 路徑，屬守衛面，無暴露證據不動）。

### 2.13.4 D4 交接包（`~/.autosdd/handoff/<sid>_<UTC 時戳>.md`；已落地）

目錄解析沿 `endurance_env` 的 durable-dir 模式新增 `HANDOFF_DIR_ENV="AUTOSDD_HANDOFF_DIR"`、`HANDOFF_HOME_PARTS=(".autosdd","handoff")`、`handoff_dir_status()`（唯讀時退系統暫存，同 handback），並登記進 `sentinel_lifecycle.CACHE_FENCE_ENV` 圍籬（測試隔離根）。

**機械層**（程式產生、零 token、必在；每欄缺值寫「量不到：<原因>」而非省略——欄位齊全本身是測試斷言）：
| 欄 | 來源 |
|---|---|
| 來源 sid、產生時刻（`datetime.now().astimezone().isoformat()`，帶 offset；鐵律三 naive 時間戳判準） | payload／`CLAUDE_CODE_SESSION_ID` |
| repo 根、branch、HEAD、領先／落後、`git status --short`（前 40 行＋總數）、`*-wip-preserved` 標籤 | `git -c core.quotepath=false …`（`tools/lib/git_paths.py` 慣例；CREATE_NO_WINDOW） |
| 最後 K（預設 3）則**真人**提示原文 | 判準＝`transcript_activity` 的 `_origin_kind(record)=="human"`（新增公開函式 `human_prompts(path, k)`，不開第二家）；排除 tool_result、`isMeta`、auto-continuation、子代理逐字稿、`<command-…>`／`<system-reminder>` 注入；每則上限 2,000 字 |
| 最後兩則 assistant 收尾文字（純 text block） | 同上 |
| 子代理名冊快照 | `roster.snapshot(sid)`（§2.13.6） |
| `AutoSDD_*`／`AutoClaude_*` 排程與 NextRunTime | `schedule_backend.select().list_jobs` ＋ 既有 NextRunTime 取數（憑證＝值） |
| 額度各軸＋量測時刻 | `quota_gate.read_quota(now)`（只讀快取） |
| 舊 session scratchpad 檔案清單（標記 `*BRIEF*`、`RESTART_POINT*`、`HB_*`） | `%TEMP%\claude\<hash>\<sid>\scratchpad`（Windows；POSIX `$TMPDIR/claude/...`）——路徑樣式量不到時寫「量不到」 |
| 逐字稿絕對路徑 | `harness_feed.pick_transcript` |

**主控層**（模型寫）：六個固定標題 `## 已驗證`／`## 未完成`／`## 下一步確切指令`／`## 禁止事項`／`## 已代決事項與 WHY`／`## 待掌舵者決定`。`handoff --finalize` 驗：前四節非空、全檔無 `TODO:`、標題比對走 `resume_route.heading_hit`（允許後綴）；不過 ⇒ rc≠0 並列缺項。猝死時沒有主控層 ⇒ 機械層照樣成立，接班提示逐字含「主控層缺席，先以機械層＋逐字稿尾段重建」。

**公告而非搶占**：未 ack 且未過期（`HANDOFF_TTL_HOURS`，預設 72h）的交接包在同 repo 任何新 session 的 SessionStart 出聲（≤3 行＋路徑）；ack＝`<檔>.ack` sidecar（與 handback 的 `.ack` 同形），**只由** `sessionctl handoff --ack <路徑>` 寫。與 `announce_handbacks` 的差異（刻意）：handback 出聲即 ack（一次性通知），交接包要顯式 ack（接班憑證）——共用出聲／sidecar 寫法，不共用 ack 時機。不做認領鎖（X3）。過期者不再出聲，但 `sessionctl status` 仍列出。

### 2.13.5 D5 三條切換路（同一份交接包；已落地）

| 路 | 觸發 | 動作 | 平台 |
|---|---|---|---|
| 無人 | 哨兵／續航判 FRESH | `resume_route.fresh_argv(claude, prompt, add_dir)`，prompt＝「讀 <交接包> 接續」＋兩條硬規則；`--add-dir` 增交接目錄 | 雙平台（既有載具） |
| 互動自動 | PostToolUse R1～R3 出聲 → 主控到可重啟點 → `handoff --finalize` → `--spawn` | spawn 前置（任一不成立 rc≠0 拒絕）：①finalize 已過；②工作樹乾淨或 HEAD 上有 `*-wip-preserved` 標籤；③`roster` 本 session 無「執行中」代理。通過 ⇒ 洗環境、另起可見互動視窗 `claude "<短提示>"`（cwd＝repo 根）、解除本 session 哨兵、痕跡 `session_switch_spawned`（pid＋建立時刻） | Windows 實作；macOS／Linux＝`notify`（印手動指令），不寫未驗證載具 |
| 手動 | 掌舵者 `/clear` 或自開視窗 | 靠 §2.13.4 公告 | 雙平台 |

- `AUTOSDD_SESSION_SWITCH_MODE`＝`auto`（預設）／`notify`（只出聲＋產機械層，`--spawn` 拒絕並印手動指令）／`off`（PostToolUse 不出聲、不產檔；`--spawn` 拒絕；手動 `handoff` 指令仍可用）。
- **洗環境**＝`handoff.washed_env(environ)` 純函式：移除 `CLAUDECODE`、所有 `CLAUDE_CODE_*`、`CLAUDE_PROJECT_DIR`、`AUTOSDD_UNATTENDED`、`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`（新 harness 會從 settings 重新套 env）；保留其餘。**不能共用** `resume_route.spawn_env()`：它是「疊加」語意（`{**os.environ, …}`），而這裡要「移除」——兩者正交，共用會讓其中一個語意被偷改。
- **舊 session 的義務**：spawn 成功後舊 session 不得再動工作樹（同 sid 雙駕駛之外的「同工作樹雙駕駛」）；`--spawn` 印出的最後一行逐字要求主控本回合收尾。機械兜底＝新 session 的活動會讓舊 session 在 24h 後被 D3 判 SUPERSEDED。

### 2.13.6 D6 續棒成本閘、D7 名冊與掌控（已落地）

**名冊資料源**（純讀檔，零 token；F3）：`~/.claude/projects/<slug>/<sid>/subagents/agent-<id>.meta.json`（`description`、`model`、`requestShape`、`finished`）＋同名 `.jsonl`（最後記錄時刻、最後一筆 assistant usage、累計 usage）。三態：
- **執行中**：`finished != true` 且最後記錄 < `ROSTER_QUIET_MINUTES`（預設 10）前；
- **安靜**：`finished != true` 且超過；
- **殘局**（brief 稱「孤兒」）：`finished != true` 且擁有者 session 已不在（擁有者逐字稿最後對話記錄 ≥ 巡邏間隔且無 `claude` 行程命令列含該 sid）。🔴 誠實劃界：子代理跑在擁有者行程內，擁有者死了它也死了——「孤兒」實為**未收尾的記錄**，不是還在燒額度的東西；名冊這樣標，不讓人誤以為能去砍它。
- 上下文＝最後一筆 assistant usage 的 `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`（`context_budget_guard.used_of` 同式；以參數注入，`session_brief` 先例，不從 lib 反向 import hook）。

**D6 閘**（PreToolUse／`SendMessage`）：解析 `tool_input` 的目標（欄位名待沙盒驗，V-S2）→ 本 session `subagents/agent-<id>.meta.json`；上下文 ≥ `RESUME_AGENT_TOKENS`（150,000）⇒ 互動：stderr＋`additionalContext` 出聲、rc 0；`AUTOSDD_UNATTENDED` 有設 ⇒ exit 2 阻斷，訊息「改派新代理＋短任務書（handback／交卷檔路徑）」。解析不到目標／檔讀不動 ⇒ 放行（fail-open：誤擋只差一步的代理代價可能更高；E1 那種長代理在名冊裡一定解析得到）。

**D7 指令**：`sessionctl status`（唯讀）列：子代理（三態）、無人窗口（pid、sid、起訖、路線、花費百分點、handback 路徑）、`AutoSDD_*` 排程與 NextRunTime、**過期哨兵**（`waiting` 且 D3 判準成立者，§2.13.3 兜底）、未 ack 交接包。`sessionctl stop --window <sid>｜--all-unattended`：
1. 列舉候選行程（Windows：`Get-CimInstance Win32_Process` 取 `ProcessId,CreationDate,CommandLine`，經 `console_orphan_census` 既有的外呼形態；POSIX：`ps -o pid=,lstart=,args=`）；
2. **身分驗證**：命令列含該 sid（RESUME 的 `-r <sid>`、FRESH／互動 spawn 的 prompt 內交接或 handback 路徑含 sid）**且**建立時刻與痕跡記錄（`resumed`／`session_switch_spawned` 前後 120s 內）相符，且痕跡帶 pid 者 pid 相符（無 pid 的續跑日誌錨點只認 print 模式行程；`--all-unattended` 另限 print 模式；§2.13.13）；任一不符 ⇒ 不砍、rc≠0、印候選讓人判斷；
3. 砍樹：Windows `taskkill /T /F /PID`（絕對路徑 `%SystemRoot%\System32\taskkill.exe`，`selfimproving/runner._taskkill_exe` 同法——建議抽 tools/lib/proctree.py 共用，見 WORK_PACKAGES (f)）；POSIX `killpg`；
4. 解除該 sid 哨兵、痕跡 `window_stopped`（pid、驗證依據、rc）。
- 視窗內（互動或無人）的子代理只能由擁有者用 TaskStop 停：本工具不提供（誠實劃界）。

**可見性三處**：
(a) Stop：本回合結束時本 session 仍有「執行中」代理 ⇒ 輸出 JSON `systemMessage`「本回合結束時仍有 N 支背景代理在跑：<描述/模型/上下文>」（rc 0、不阻斷）。🔴 用 `systemMessage` 而非裸 stderr：exit 0 的 stderr 不顯示給人（見 WORK_PACKAGES (f)-1）。
(b) 無人窗口結局：單一家＝`endurance_env.record_unattended_outcome` ＋ `unattended_outcome_banner`（游標制，已讀即不再出聲）。本節把記錄時機由「relay 停下」擴為「每一窗收窗」（`relay_machine.settle_window` 內），欄位補 `started_at`、`ended_at`、`route`、`pct_before`、`pct_after`、`handback`；SessionStart 簡報（`session_brief.sessionstart_brief`）多接一次 banner。互動視窗 PostToolUse 不另開出口（banner 游標已保證「一次」；SessionStart 之後才發生的無人窗口由 Stop／`--pace` 的 banner 補）。
(c) `resume_cost.jsonl` 的 `pct_before`／`pct_after`：`_run_resume` spawn 前後各讀一次 `quota_gate.read_quota` 的 five_hour 軸，傳入既有 `build_record(pct_before=, pct_after=)`（兩者皆有才填的既有規則不變）。

### 2.13.7 D8 模型平衡建議（只出聲；已落地）

`modelmix.advice(axes, now)`：對 `weekly_all` 與模型專屬週軸（`weekly_scoped`，依 `context_budget_guard.model_family` 比對主控家族）各算 `ratio = pct/100 ÷ elapsed`，`elapsed = 1 − (resets_at − now)/7d`（夾在 [0.05,1]；`resets_at` 缺 ⇒ 該軸不判）。
- 專屬軸 ratio − 全模型軸 ratio ≥ 0.15 ⇒「Fable 超前：多外派、主控只做判斷／派工／親驗」；
- 全模型軸較超前 ≥ 0.15 ⇒「全模型超前：子代理降級（Opus→Sonnet→Haiku）、短任務書、禁續棒；判斷性工作主控可自做」；
- 兩軸 ratio 皆 < 0.8 ⇒「兩軸皆寬：深度審查可用 Opus」；其餘 ⇒「平衡」。
接線：`--pace` 多印一行（planner `--pace` 分支一行；`quota_gate` 不動）。選模型準則寫進根 `CLAUDE.md`〈派工模型〉：Haiku＝機械查找清點；Sonnet＝實作／測試／規格／QA 鏡（預設）；Opus＝架構、安全審查、疑難根因；主控只做判斷、派工、親驗。

### 2.13.8 hook 面最小化、跨平台、與既有機制的關係（已落地）

- **hook 面**：新增一支 `.claude/hooks/sessionctl_guard.py`（Stop、PreToolUse／`SendMessage` 兩個低頻事件；exec form、`_hook_launcher`、不 spawn 子行程）；SessionStart 與 PostToolUse 不新增註冊——SessionStart 經 `session_brief.sessionstart_brief` 與 `sentinel_lifecycle.announce_handbacks` 內部延伸（hook 檔零行），PostToolUse 在 `context_budget_guard.arm_when_earned` 呼叫點旁加一行 `switch_advice(...)` 呼叫（SPECIAL_FILES 棘輪已由 1089 重釘為實際行數，理由見缺陷帳本 DEF-200-584 與 `LOC_Budget_Ratchet_History.md`）。理由：PostToolUse 每次工具呼叫都起一個行程，第二支常駐 hook 的成本是 Windows 上每次 ~100ms 級的 python 啟動。
- **鐵律三觸發清單**：`$env:*`（洗環境：Windows 環境變數大小寫不敏感 ⇒ 比對一律 `upper()`）；路徑分隔符（`Path` 組裝）；console 編碼（git／CIM 輸出 `encoding="utf-8", errors="replace"`，PowerShell 外呼前置 UTF-8 prelude）；行尾（交接包寫入 `newline="\n"`）；naive 時間戳（全部 `astimezone()`）；外部執行檔 argv（`taskkill`／`powershell.exe`／`pwsh`／`ps` 皆在 `sys.platform` 守衛內，`TestForeignExecutableArgvIsGuarded`）；`Win32_Process.CreationDate` 是 CIM datetime（含 UTC 偏移分鐘數）需專門解析；macOS `ps lstart` 本地時間無 offset ⇒ 只用於相等比對不持久化。
- **單一家關係**：哨兵五分支＋SUPERSEDED 共用 `sentinel_decide`（不另開決策器）；雙駕駛判準仍是 `transcript_activity.live_driver`（D3 不取代它：雙駕駛＝同 sid、一個巡邏間隔內；SUPERSEDED＝他 sid、24h 尺度）；handback 公告沿 `announce_handbacks`；扇出帳（`quota_escalation.fanout_path`）不變，名冊不寫扇出帳；precompact 骨架（`precompact_restart_point`）仍是「壓縮前」的骨架，交接包是「換 session」的載體——交接包機械層把最近一份 precompact 骨架路徑列為一欄（不複寫其內容）。

### 2.13.9 已否決方案

| 代號 | 方案 | 否決理由 |
|---|---|---|
| X1 | 調低 autocompact 門檻（90%→更低）來減少重送 | 連動三段水位與 `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 的多把鎖；沒有「提醒不夠用」的暴露證據；E1 是無人選路錯，不是壓縮晚 |
| X2 | 互動視窗由 hook 直接自動關閉舊視窗、自動開新視窗 | hook 沒有關閉 harness 的能力；自動開窗不經主控到可重啟點＝半套 edit 交棒，違反〈可重啟點四條件〉 |
| X3 | 交接包「先到先得」認領鎖 | 無關 session（掌舵者另開的別件工作）會搶走；公告＋顯式 ack 已足夠 |
| X4（2026-11-15 改寫，見 §2.14.2 決策 1） | SendMessage 閘在互動視窗一律阻斷 | 原否決理由是代理只差一步時逼重做代價可能更高。改寫為：**熱續放行、冷續且大上下文互動也阻斷**——熱時快取仍有效、續棒便宜；冷時續棒等於整包重寫，與重派新代理同價卻帶著舊上下文，互動也阻斷，並留逃生口 `續棒理由：<WHY>`。無人窗口不論冷熱照舊阻斷 |
| X5 | 新增 SubagentStart／SubagentStop hook 建名冊 | F3 已證名冊可純讀檔導出；多一組事件註冊＝多一組 fail-open 盲區與文件宣稱鎖 |
| X6 | 共用 `resume_route.spawn_env()` 做互動 spawn 洗環境 | 疊加 vs 移除語意正交（§2.13.5） |
| X7 | SUPERSEDED 只接在 halt 標記（DEF-200-532 現況） | E2 的哨兵沒有 halt 標記、處在撞線 `waiting`，撞線分支優先 ⇒ 永遠輪不到 |

### 2.13.10 誠實劃界

- 無人窗口內的子代理、互動視窗的子代理：本設計只能**看見**，停止只有擁有者 TaskStop 或砍整個無人窗口行程樹。
- 互動自動切換只在 Windows 實作；macOS 為 notify。睡著的機器不在射程（同 §2.7）。
- R1 的估計值（位元組÷比值）只在 feed 與逐字稿 usage 皆缺時用，且標 `estimated`；比值是量測值，由 `tools/probe/`（現查）重量，不寫成常數以外的第二份。
- D3 讀不到其他 session 逐字稿時不判 SUPERSEDED（續航優先）。
- `meta.json.finished` 在 session 猝死時的值未驗（V-S4）；若猝死時為 `false`，名冊會把它標成「殘局」——這是正確的標法，不是誤報。

### 2.13.11 洩漏圍籬假陽性（已落地）

**事故**：`~/.autosdd/traces/autosdd_leak_fence.jsonl` 2026-11-13T20:48:35 一筆 `rc: 0, fence_rc: 1`——全套測試期間新開的互動 session 的 SessionStart／PostToolUse 合法武裝了自己的哨兵 `AutoSDD_Sentinel_<sid>`，圍籬以「跑前跑後排程差集」判洩漏，把發起該次全套的互動 session 自己的哨兵判成洩漏，全套被判紅而無任何程式碼問題。

**修法**：`sentinel_lifecycle.leak_fence(run, projects_dir=None)`：差集內的哨兵 job 若其 sid 對應的**真實**逐字稿在圍籬起點之後有對話記錄（判準沿用 `transcript_activity`，新增 `sessions_active_since`，不開第二家）⇒ 視為活著的真 session 合法武裝：只出聲、不判死，痕跡新增欄位 `live_session_jobs` 標明。測試種下的假 job（沒有真實逐字稿活動，或活動在圍籬起點之前）照舊判死。正負向鎖＝`LeakFenceTest`。

**fail 方向**：讀不到逐字稿目錄 ⇒ 沿用舊行為（判洩漏），不放寬；代價是讀不到時假陽性仍可能重現，由痕跡檔的 `fence_rc` 與 `live_session_jobs` 兩欄事後可辨。

### 2.13.12 暴露證據與已接受的劃界（第一段）

- 暴露證據三取一皆成立：E1、E3 為掌舵者真機回報，E2 與圍籬事故為非構造性實況（見 §2.13.0）；第二段各項的暴露證據同表，實作時各自再附。
- 第一段已修缺陷：DEF-200-580（E1）、581（E2）、582（圍籬）；第一波推送守門的跨平台成因另立 DEF-200-583；第二段承接 DEF-200-584（已結案）。
- 第一段的假設與界線：R1 的估計值只在量不到時用且標 `estimated`（見 §2.13.2 裁決）；SUPERSEDED 讀不到其他逐字稿時不判（續航優先，§2.13.3）；無撞線事件的過期 session 走既有閒置解除路徑（§2.13.3 裁決）。

### 2.13.13 第二段實作事實（2026-11-14 落地；與上文設計有差異處以此為準）

- **runner 統一簽章**：`handoff` 內 git／排程查詢／互動 spawn 共用同一縫 `runner(argv, *, cwd=None, env=None, creationflags=0, wait=True) -> (rc, stdout, pid)`（`wait=False` 回 `(0, "", pid)`）；`procstop` 的縫是另一慣例 `run(argv) -> CompletedProcess`，兩者不跨呼叫，維持分立。測試縫（`base`、`roster_mod`、`quota_fn`、`temp_root`、`alive`、`sleep`、`disarm` 等選填關鍵字）只供測試注入。
- **`advise_once` 兩個閂**：`<handoff 目錄>/<sid>.advised`（一個 session 只出聲一次）與 `<sid>.checked`（評估節流 60 秒，因 R2 要掃整份逐字稿，PostToolUse 不能每次都付）。R1～R3 全不成立時**不產交接包**，只留節流戳（它不是交接包）。`AUTOSDD_SESSION_SWITCH_MODE=off` 時不出聲不產檔，`notify` 只出聲並產機械層、`--spawn` 拒絕。
- **交接包格式**：首行 `# 交接包 <!-- sessionctl-handoff sid=… at=… -->`；`## 機械層`（`### n 標題` 共 11 欄，真人與 assistant 引文逐行前綴 `> `，免得引文內的 `## 已驗證` 被當成標題）＋`## 主控層`（六個固定標題，骨架每節一行 `TODO:`）。`finalize` 只在主控層內找標題與 `TODO:`，剛產生的骨架不會過。「過期」＝檔案 mtime 距現在超過 `HANDOFF_TTL_HOURS`；`list_handoffs` 只認檔名形態 `<sid>_<YYYYMMDDTHHMMSSZ>.md`（避免把 handback 的 `*.md` 當交接包），目錄決策唯讀（`_read_bases`：主居所存在且可寫＝它，否則系統暫存；二選一、不併讀、不為了讀而 mkdir）。
- **`procstop.py` 拆檔**：行程列舉（Windows CIM／POSIX `ps`）、身分驗證、砍樹、解除哨兵、落 `window_stopped` 住 `tools/lib/sessionctl/procstop.py`（安全敏感，且避免 `roster.py` 破 400 行）。身分驗證＝命令列含 sid **且**建立時刻吻合痕跡錨點（±120 秒）；驗不到一律不砍。錨點來源＝續跑日誌 `relay_snapshot_before.at` 與持久痕跡目錄中 `session_switch_spawned` 事件。
- **spawn 痕跡欄位**：`<trace_dir>/autosdd_session_switch.jsonl` 事件 `session_switch_spawned`，欄位 `pid`、`sid`、`handoff`、`spawned_at`、`new_transcripts`、`ok`，另有 `at`＝spawn 當下（首選錨點；先前取等完逐字稿之後的時刻會讓 stop 的時刻比對失準，已改）。注意 stop 的 sid＝舊 session sid（新視窗命令列含交接包路徑內的舊 sid）。
- **名冊與整合修正**：`roster._handoffs` 原查 `<檔名>.md.ack` 而 `handoff.ack` 寫 `<stem>.ack`，已 ack 的包會被永遠當成未接手；改為呼叫 `handoff.list_handoffs`（只取 live）。`snapshot` 另有 `full` 關鍵字（`running()` 只讀逐字稿尾端 256 KB）；殘局只在給了 `runner` 的 `snapshot` 判（需列舉行程），hook 路徑永不判殘局；巡邏間隔常數 `OWNER_IDLE_SECONDS=900` 是量測值不是真值；`projects_dir` 接受 `~/.claude/projects` 根或 slug 目錄。
- **`pct_after` 讀不到記空值並附原因、不外呼量測**：`_run_resume` 前後各讀一次五小時軸，只讀額度快取（`read_quota`），無人窗口跑過快取 TTL 時多半讀不到；此時兩欄記空值，成本帳新增 `pct_note`（「量不到：前／後讀數（…）」）與 `pct_checked_at`（檢查時刻；量不到就沒有額度量測時刻），結局檔 `record_unattended_outcome(pct_note=)`；測試以 `__getattr__` 炸掉任何非 `read_quota` 的呼叫，釘住「絕不外呼」。要補後讀數須用會連網的 `pace_state`，有外呼風險，未做。
- **每窗收窗落結局**：`relay_machine._record_outcome` 在每一窗收窗（含非 loud 的 `quota_stop`）都記一筆結局，欄位含 `started_at`、`ended_at`、`route`、`pct_before`、`pct_after`、`handback`；舊鎖（斷言「quota_stop 不記結局」）因此改名為 `test_quota_stop_records_a_quiet_outcome`（設計改變，見 §2.13.6 (b)）。`record_unattended_outcome(handback=…)` 與 `handback_path` 寫入的 `handback` 欄同名，後者被前者覆寫，兩處傳同一路徑所以 `handback_verdict` 不入結局檔（已知劃界）。
- **hook 接線**：`switch_advice(payload, transcript)` 在 `main()` 的 `if not blocking:` 區塊、`arm_when_earned` 下一行呼叫，lazy import `lib.sessionctl.handoff`，例外一律吞掉；`sessionctl_guard.py` 只認 `Stop`（輸出 `systemMessage`、rc 0、永不 block）與 `PreToolUse` 的 `SendMessage`（rc 0 出聲／rc 2 阻斷），`AUTOSDD_SESSIONCTL_GUARD_OFF` 有設即 no-op。互動 PreToolUse 出聲同時寫 stderr 與 `additionalContext`。
- **第二段獨立 QA 後的修正（2026-11-14）**：①`roster.stop_message` 的狀態過濾原只套在子代理上，`background_tasks` 內已結束（`status` 非 `running`）的 shell 仍被計入「另有 N 個背景 shell」，改為子代理與 shell 同一個 `live` 篩選；②`relay_machine._record_outcome` 的結局字面查表改 `.get(next_st, str(next_st))`，日後新增狀態未補表時降級成狀態名、不拋 `KeyError` 拖垮收窗；③`stop_window` 砍失敗回 rc 1（砍不掉＝呼叫端必須知道，與 §2.13.6 一致）與 `five_hour_reading` 只認五小時軸兩點，實作本就正確，QA 發現的是**鎖缺口**，已補測試並以手動破壞驗證會轉紅；④`procstop.verify` 的 `is_claude` 守門（POSIX `ps` 列全部行程，命令列含 sid 的 tail／編輯器不是 claude 不得砍）與 `trace_anchors` 只收本 sid 的 spawn 時刻，同樣補鎖。安全語意沒有放寬：驗不到身分就不砍。
- **第二段獨立安全審查後的收緊（2026-11-14；審查結論 CONDITIONAL，P1×1／P2×3，皆在函式庫層修、未動 `.claude/`）**：①**無人模式不出聲、不 spawn（SEC-6）**：`AUTOSDD_UNATTENDED` 有設時 `advise_once` 回空字串（不設 `.advised`，同 sid 之後的互動視窗仍能被提醒）、`spawn` 與 CLI `--spawn` 一律回 rc 1 並說「無人窗口不開互動視窗」、不外呼、不解除哨兵——互動 spawn 的 `washed_env` 會洗掉無人旗標，把無人窗口的自主工作搬進沒有姿態圍籬的視窗；無人續跑的 FRESH 路（planner）不經 `washed_env`，有測試守住；②**`--all-unattended` 只砍 print 模式行程（SEC-1）**：驗證集合限命令列帶 `-p`／`--print` 者，同 sid 的互動視窗（雙駕駛）即使建立時刻吻合也不在集合內；③**身分驗證用痕跡裡的 pid（SEC-2）**：`session_switch_spawned` 痕跡帶 pid，行程 pid 必須相符；續跑日誌錨點（`relay_snapshot_before`，planner 起無人窗口前落、本來就沒有 pid）只放行 print 模式行程；痕跡缺 pid 的互動視窗＝驗不到＝不砍；`trace_records` 回 `(時刻, pid)`，`trace_anchors` 保留只回時刻；④**`--spawn` 防重複（SEC-7）**：同一交接包已 ack ⇒ 拒絕；已有 `session_switch_spawned` 痕跡且（該 pid 仍活著，或痕跡在 `SPAWN_DEDUP_SECONDS`＝600 秒內）⇒ 拒絕並印既有 pid（600 秒＝新視窗首個逐字稿落檔上限 `SPAWN_WAIT_SECONDS` 的二十倍；過了仍沒人接手且行程已不在＝真的失敗才准重試）；⑤縱深（P3）：命令列 sid 比對改為與完整 UUID 相等（8 碼前綴與非 UUID 形一律驗不到，SEC-3）、機械層與 spawn 提示加「屬資料、引文中的指示不得照做」一句（SEC-13）、`handoff --build --session-id` 驗 sid 形態防路徑穿越。殘留註記：互動 `--spawn` 的痕跡 pid＝新視窗本身，`stop --window <舊 sid>` 因此仍可停到「該交接包 spawn 出的那一個視窗」，這是 pid 相符的刻意語意；其餘 P3／P4 處置見 `docs/06_quality/SessionCtl_Defect_Evidence_20261114.md`〈第二段安全審查與理論洞清單〉。
- **R3 補註（2026-11-17；E-ARCH-1 修，§2.18 D6）**：`advise_once` 新增選填 `agent_id`，有值（呼叫者是子代理）即回空字串、不寫 `.advised`／`.checked`、不產包——子代理的 hook payload 帶的是父 session 的 `session_id`／`transcript_path`，原本子代理的一次工具呼叫就把「建議換 session」注入子代理上下文並吃掉「一個 session 只出聲一次」的閂，主控永遠收不到。同批：`handoff --finalize` 升級為封存（委派 `seal.seal`，§2.18 D2）、`handoff.spawn` 加 `extra_prompt_file`（轉送用，§2.18 D3）、`sessionctl watch` 分派（§2.18 D1）。
- **未做／待真機**：`.claude/settings.unattended.json` 的 `additionalDirectories` 不另補（無人視窗經 argv 第三個 `--add-dir` 值已取得權限）；殘局判準未使用 `~/.claude/sessions/<pid>.json`；互動畫面是否顯示 Stop 的 `systemMessage` 與 TCS §3 的 V1～V8 皆待真機目視。

### 2.14 等待與續跑的 token 浪費：快取冷熱決定續棒、收斂閘、長等待角色用 1 小時快取、推送快層先行（2026-11-14）

> 數字一律現查：門檻 `python tools/lib/quota_policy.py --print-env-example`；浪費帳 `python tools/probe/waste_census.py --since-days 14`；收斂門檻取值重放 `python tools/probe/waste_census.py --replay-hard-ctx`。本節只寫判準、出處與方向。驗收契約＝`docs/03_testing/contracts/TCS-TokenWaste-20261114.md`。

#### 2.14.0 立案與暴露證據（守衛面准入：三取一皆成立）

- 掌舵者真機回報：sid `680d8411-58ac-4adb-9e23-521f6a7bb557`（2026-11-14 22:2x）「剛剛因此又浪費了20%的 Token」。逐字稿：19:21:09 已出聲建議換 session，其後同 session 續做 3.7 小時；20:52 掛背景輪詢後閒置 78 分，22:10 回來整份重寫約 26 萬 token。
- 非構造性逐字稿（浪費帳探針，近 14 天）：子代理在 5 分鐘快取失效後被續棒重寫，是全部可歸類浪費中最大的一類（`other_user` 起因、上下文 ≥ `AUTOSDD_RESUME_AGENT_TOKENS` 共 141 件、合計約 68M tok 在快取已冷時被續）；子代理自己前景輪詢後重寫次之；主控閒置逾 1 小時的重寫再次之。座標見 TCS §6 E-1～E-6。

#### 2.14.1 平台事實（官方文件；他機以同版號重查）

- Claude Code 訂閱制在方案額度內：主對話快取 1 小時、子代理等「其餘請求」5 分鐘；兩者可分別設定（`promptCacheTtl`／`subagentPromptCacheTtl`、對應環境變數，或子代理 frontmatter `experimental.cacheTtl`），1 小時的寫入單價較高（https://code.claude.com/docs/en/prompt-caching.md）。
- 每次命中快取會重設計時器；閒置超過壽命，下一個請求整份重算。續棒的子代理只有在壽命內才讀得到原本的快取（同上，及 https://code.claude.com/docs/en/sub-agents.md）。
- 平台沒有延後或合併完成通知的設定；外部行程叫醒互動視窗沒有文件依據。

#### 2.14.2 決策

1. **續棒看快取冷熱（取代 §2.13.9 X4 的「互動只出聲」）**：SendMessage 的目標代理「冷」＝最後一筆 **assistant** 記錄距今 ≥ 它實際使用的快取壽命減 30 秒安全邊際（壽命由其逐字稿尾端 usage 的 `cache_creation.ephemeral_1h_input_tokens` 是否大於 0 判 1 小時或 5 分；缺欄＝5 分；tool_result 記錄不重設計時器，故不以「任何記錄」起算）。冷 ∧ 上下文 ≥ `AUTOSDD_RESUME_AGENT_TOKENS` ⇒ **互動與無人皆阻斷**，要求改派新代理＋短任務書（指向交卷檔）。熱 ⇒ 互動放行且**不出聲**。互動逃生口＝訊息本文 `續棒理由：<WHY>`（全形冒號、理由 ≥ 8 字；落痕跡 `resume_gate_override`；`AUTOSDD_UNATTENDED` 有設時無效）。**無人窗口不放寬**：上下文 ≥ 門檻一律照 §2.13.6 阻斷，不論冷熱（E1 的現場是無人窗口，熱放行只適用互動）。X4 的原否決理由（只差一步的代理）由「熱續放行＋逃生口」承接。
2. **收斂閘**：本 session 已被提醒換 session（`<handoff>/<sid>.advised` 存在）且主控上下文 ≥ `AUTOSDD_SWITCH_HARD_CTX_TOKENS` ⇒ PreToolUse 擋 `Agent`／`Task`／`Workflow`；讀、改、跑測試、等交卷、SendMessage 不擋。出口：代理交卷後 `handoff --finalize` → `--spawn`，或 `/compact`（上下文降到門檻下自動解除，阻斷不進閂鎖）。`AUTOSDD_SESSION_SWITCH_MODE=notify|off` 與無人窗口不擋；阻斷事件落痕跡 `converge_block`。門檻出廠值取自探針重放（TCS §7）：**290,000，只准下修，且須嚴格大於 R1**。🔴 **v2.1.22 起（§2.19 D1）**：「須先出聲」前置取消、R1 退役、硬線出廠改 850,000（低於 autocompact 最小點 881,938）；本條 290,000 與「須大於 R1」為史料。
3. **長等待角色用 1 小時快取（條件項）**：任務書含預期超過 4 分鐘的指令（全套、E2E、Docker、CI 等待）的棒，派 `subagent_type: long-runner`（long-runner 定義檔（.claude/agents/ 下，尚未進 repo）：`model: sonnet`、`experimental.cacheTtl: 1h`、不寫 `tools`）；其餘維持預設。**真機驗證（TCS §3 V-T1～V-T3：1 小時寫入真的出現、自訂型別仍收到根 CLAUDE.md、等待後讀回 ≥90%）全數通過才落地**，任一不過即刪該檔並把本條改寫為「已驗證不可行」。全域把子代理改 1 小時經實測淨虧，否決（X8）。
4. **等待自帶截止且短於主控快取壽命**：互動主控的 CI 等待（`tools/ci_wait.py`）預設逾時短於主控快取壽命（現值 40 分，主控壽命 1 小時；以 `tools/tests/test_ci_wait.py` 的一測釘住不得 ≥ 60）；逾時醒來若未完成且上下文已達換 session 門檻，下一步是交接換手（§2.13.4／§2.13.5），不是再掛一次等待。
5. **推送快層先行**：`tools/git-hooks/pre-push` 在啟動任何 leg 之前先跑快層（十一支守門＋`ruff check tools/ .claude/hooks/` 與其後兩道），快層**全部跑完**後任一紅即停：不啟動慢層、不啟動子專案 leg、不開背景並行，印出紅的那一道與「修完再推」。慢層內部維持「失敗累積進 rc、不中斷其他 leg」。取捨（Rule 7）：該紀律的目的是一次看到所有紅，但快層紅時推送必被擋、慢層結果不會被用到，累積只換來等待；故只在「快→慢」之間短路，快層內部與慢層內部照舊累積。

6. **回合結束推回（C2；原條件項，主控裁決 O-1 升入第一期）**：🔴 **已由 §2.18 D2 取代（R3，2026-11-17）**：Stop 推回改為「封存閘」——不再要求「已被提醒＋達硬門檻＋無已 finalize 的 live 包」，改為無在飛代理 ∧ 主控上下文 ≥ R1（直接量逐字稿；**v2.1.22 起改為 ≥ 硬線 HARD，R1 退役，見 §2.19 D1**）∧ 尚未交棒 ∧ 封存無效；`converge._converge_stop` 已刪、痕跡 `converge_stop_block` 改 `seal_stop_block`；「已 finalize」判準升級為「已封存（`.sealed`）／已交棒」，並補上 E-HD-1（包被 ack 後舊判準失明）。以下為原決策文字，保留作史料：Stop 事件是主控結束回合、即將閒置的唯一時點。本 session 已出聲 ∧ 主控上下文 ≥ `AUTOSDD_SWITCH_HARD_CTX_TOKENS` ∧ 無執行中背景代理（背景 shell 不算）∧ 無已 finalize 的 live 交接包 ∧ `stop_hook_active` 為假 ∧ 非無人窗口 ∧ 模式為 auto ⇒ `sessionctl_guard.py` 的 Stop 分支輸出 `decision:block` 推回一次，reason 給確切下一步（補交接包主控層 → `handoff --finalize` → `--spawn`，或 `/compact`，或改 notify）；第二次 Stop 一律放行，每回合至多一個額外回合，不寫閂鎖。判準與收斂閘共用同一份 `_gate`，兩者不會漂移；與 `check_pending_handoff.py` 疊加最壞兩個額外回合、不死鎖（兩支各自至多推一次、都吃同一個 `stop_hook_active`）。痕跡 `converge_stop_block`。真機驗證 V-C2 待主控。

#### 2.14.3 設計取捨與落點

- 判準住 `tools/lib/sessionctl/cachestate.py`（冷熱，純函式）與 `converge.py`（收斂閘）；`roster.resume_gate` 改寫、`switch.py` 新增 `HARD_CTX_KEY` 與 `trace()`（痕跡寫入單一家，`handoff._trace` 委派它）、`handoff.is_advised` 唯讀查閂鎖；hook `sessionctl_guard.py` 在同一條 PreToolUse 條目上把 matcher 由 `SendMessage` 擴為 `SendMessage|Agent|Task|Workflow`，Stop 分支加推回（決策 6）。不放進 `context_budget_guard.block_verdict`：該檔 SPECIAL_FILES 棘輪餘裕 0，且其 `tier_of()` 以視窗比例早退（1M 視窗下 29 萬只有 29%），放進去要改早退順序，爆炸半徑大於新增一個 matcher。
- 浪費帳探針入 repo：入口薄殼 `tools/probe/waste_census.py`、判準在 `tools/lib/wastecensus/`（SA 原檔 714 斷言行逼近 750 紅線，加指標必破，故成套件）。新指標 M2b（冷續件數）、M2c（長等待重寫，按代理型別分組）、M2d（`long-runner` 零長等待占比）、M3d（阻斷／逃生／收斂阻斷次數）。
- 痕跡：`~/.autosdd/traces/autosdd_session_switch.jsonl` 新事件 `resume_gate_block`、`resume_gate_override`、`converge_block`、`converge_stop_block`（逃生口 `AUTOSDD_TRACE_DIR`）。

#### 2.14.4 已否決

| 代號 | 方案 | 理由 |
|---|---|---|
| X8 | 全域子代理 1 小時快取 | 浪費帳實測：多付的寫入溢價（約 0.75×全部子代理寫入量）與省下的 ≤60 分重寫相抵後為負（約 −3M～−13M 單位）；且續棒冷閘上線後更不划算 |
| X9 | 子代理以 5 分鐘內短輪詢保溫 | 屬定時喚醒保溫（任務書禁止）；平台的等價物是 1 小時快取 |
| X10 | 通知批次化／純確認回合阻斷 | 平台無此機制；喚醒那一回合的讀已經付了，阻斷只會多付一回合；改由收斂閘壓上下文上界 |
| X11 | 通用背景等待登記＋外部巡邏叫醒 | 叫醒互動視窗無文件依據；正解是每個等待自帶截止（決策 4） |
| X12 | 單支耗量預估閘 | 無預測器，誤攔不可回測；接續成本已由決策 1 封頂 |
| X13 | 另寫推送預檢工具 | 第二個家；快層本來就在 pre-push 裡，改順序即可 |
| X14 | 收斂閘門檻設在 R1 | 大多數主控回合都在 R1 以上，會逼人關守衛 |
| X15 | 無人窗口也「熱續放行」 | 放寬 §2.13.6 既有阻斷；E1 現場即無人窗口 |

#### 2.14.5 誠實劃界

- **收斂閘對事故本身不介入**：以派工事件重放事故 session，19:21:07 出聲後到 22:12:38 之間沒有任何 `Agent`／`Task`／`Workflow` 呼叫（事故的 78 分鐘是背景 `PowerShell` 輪詢加結束回合）。收斂閘壓住的是出聲後的**派工**與其上下文成長；事故形態本身由決策 4（等待自己會結束）與 Stop 時點的推回（決策 6，已升入第一期）處理。
- 🔴 v2.1.22 起「出聲後」前置取消、硬線出廠 850,000（§2.19 D1），以下為史料。出聲後多數 session 的後續派工都會被擋（重放：首次 ≥R1 後 202 次派工，門檻 290,000 時 174 次落在 ≥門檻）。這是設計意圖，也是守衛被整個關掉的最大風險；以痕跡 `converge_block` 與逃生口使用量監看，過高即回頭檢討（不是放寬方向鎖，而是檢討出聲條件）。
- 純讀、改、跑測試的連續小工作不被收斂閘與 Stop 推回擋（O-1 已接受的缺口）；以痕跡 `converge_block`／`converge_stop_block` 與逃生口使用量監看。
- 決策 3 依賴自訂子代理仍收到根 CLAUDE.md 與 1 小時寫入真的生效，兩者皆以真機驗證為前提；驗不過即撤回該檔。
- 主控在真人離開時閒置超過一小時的重寫沒有機械解；收斂閘只壓住單件代價的上界。
- **冷叫醒閘（DEF-200-588，2026-11-15 補；R3 修訂：E-HD-1 起包不分 live／acked 狀態、E-CW-1 起前提為「已封存（`.sealed`）／已 spawn／已 ack」，只寫完主控層不算，見 §2.18 D2）**：交接包已 finalize 的 session 若還掛著執行中的背景任務，任務結束時 harness 會把它叫醒；重寫發生在模型能反應之前，所以唯一擋得住的時點是交接後結束回合那一刻。`converge._finalized_wake` 在 Stop 時推回一次、要求 TaskStop（不看出聲、不看硬門檻；payload 沒有 `background_tasks` 欄就不判）。立案證據＝sid `eb1cb524` 於 2026-11-15 08:34:57 +08:00 的一筆 `cache_creation_input_tokens=235445`（電腦喚醒後等 CI 的背景行程結束，叫醒上下文 26.8 萬、已交棒的 session；五小時窗一次 13pp）。同案修掉接線順序：原 hook 先出聲就返回，只有背景 shell 在跑時判準層要推回、hook 卻只印一句話放行；改為先判推回、沒有才出聲。劃界：沒有交接包的 session 掛背景等待仍放行（平常等 CI 的正當用法，靠等待自帶截止時間小於快取壽命保護）；電腦睡眠會讓這個保護失效，此時代價上界由收斂閘的上下文門檻壓住。
- 額度百分比在逐字稿裡量不到；所有省下的量是公開價格比換算的推估，用來排序，不是額度承諾。
- 冷熱判準的 30 秒安全邊際是量測偏差補償（hook 判斷時刻早於實際請求時刻；探針實見一筆 299.995 秒間隔仍整份重寫），不是調參旋鈕，不開環境變數。

### 2.15 額度配速與快取保全：窗內配速床、趕工戳記、主控保溫的有條件裁定（2026-11-15；第一期＝配速床＋趕工戳記＋量測；保溫實作屬第二期）

> 數字一律現查：門檻與兩個配速床常數 `python tools/lib/quota_policy.py --print-env-example`；`--pace` 現況 `python tools/session_resume_planner.py --pace`；配速指標 `python tools/probe/waste_census.py --pace-metrics`（第一期落地後）。本節只寫判準、出處、方向與撤回門檻。驗收契約＝`docs/03_testing/contracts/TCS-TokenWaste-20261114.md` §10。
> 係數口徑：下列 pp＝五小時窗百分點（Fable 自軸，除非註明）。換算係數取 SA 兩個乾淨區間聯立（寫 5.5e-5、讀 1.7e-6、出 1.4e-4 pp／token），**樣本 n＝2、寫讀比可落 10～60**；本節每個結論都對「悲觀比 10」再驗一次，驗不過的標「不穩健」。所有省下的量是換算推估，用來排序與定門檻，不是額度承諾。

#### 2.15.0 立案與暴露證據（守衛面准入：三取一皆成立；`quota_gate.py`、`quota_policy.py` 皆在守衛面清單內）

掌舵者原話（2026-11-15 00:1x，sid `eb1cb524-de09-4ad5-a068-69fa180dc64b`）：「要解決LLM Cache消失的問題, 導致下次啟動會浪費很多Token……當Token一小時就用完時, 再次啟動就會有Cache消失浪費Token問題……是否需要保留5%~10%進行慢速工作或只與MML做簡易對話, 維持Cache, 等下一個五小時在繼續正常作業 2. 若沒有需要趕工, 將Token盡量維持分配五小時進行作業!」

1. **掌舵者真機回報**：同 sid 原話如上；主控親驗同 sid 2026-11-14 23:03 五小時窗 8%、2026-11-15 00:1x 56%（約 70 分鐘用掉 48pp，全是並行派工）。
2. **非構造性逐字稿**：sid `04b38d83` 2026-11-13T13:22:57Z `apiError:"usage_limit_reached"`、`status:"rejected"`、usage 全 0；halt 標記（binding＝five_hour）近 14 天 5 件（11-07 17:13、11-13 04:43、11-14 00:49、11-14 22:44 等；SA Q5），等待 15／47／164／167／191 分鐘。
3. **真實輸出**：本棒鏈 sid `ff7d69c4-aa33-4ced-bbf0-cbd780a539cd` 約 2026-11-15 08:56 的 gate 輸出 `kind=five_hour 43% … band=free horizon=far cap=None note=burn-ahead`＝已判超前、致動器零煞車；同 sid 08:51:17 的 `--pace`：weekly_scoped(Fable) 78%、剩 8467 分鐘、攤提 r=4.3（n=84）⇒ 每個五小時窗只配 3.4pp、本窗已用 38pp、餘裕 −34.6pp，而輸出寫「長窗自軸未達 converge ⇒ 出聲不收緊」。

#### 2.15.1 平台事實與資料來源（查閱日期 2026-11-15）

| 代號 | 事實（原文要點） | 出處 | 讀取者／可信度 |
|---|---|---|---|
| P1 | 主對話（互動回合、非互動 `-p`、Agent SDK）在訂閱額度內快取 **1 小時**；子代理、workflow、fork、compaction、session title 為 5 分鐘 | https://code.claude.com/docs/en/prompt-caching.md | Architect 親讀，SD 未覆核；高 |
| P2 | 每次命中快取會重設計時器 | 同上 | 同上 |
| P3 | `resume` 保留原 session 的系統提示並讀回仍在壽命內的前綴；**互動與 `-p` 的工具集是否相同文件未載** | 同上 | 同上；互動／`-p` 一致性＝待真機驗證 |
| P4 | 閒置超過壽命後的 `/compact`，摘要請求把整份歷史當未快取輸入重算（冷 `/compact` 最貴） | 同上 | 同上 |
| P5 | 閒置的 1 小時快取 session，Claude Code 可能自行壓縮（`idleCompaction`，v2.1.290 起可關） | 同上 | 同上；與保溫的交互＝待真機驗證（V-K3） |
| P6 | `/usage` 有「Prompt cache (main)」行；statusline 有 `prompt_cache` 物件（v2.1.251 起，likely cause v2.1.260 起） | 同上 | 同上；細節頁未讀 |
| P7 | 換模型、換 effort（Fable 5.1 起例外）、fast mode、非 deferred 的 MCP 增減、升級 Claude Code 皆失效；改 CLAUDE.md 中途不失效也不生效；nested CLAUDE.md 與 `paths:` rules 按需載入 | 同上 | 同上 |
| P8 | 循序 session 只有啟動時 git status 快照相同才共享前綴 | 同上 | 同上；與 SA 實測「新 session 讀約 3.26 萬＝系統層」一致 |
| S1 | 達上限時 harness 先注入 wrap_up 寬限，其後請求被拒、usage 全 0、拒絕請求不寫快取也不耗額度；此帳號 `overageDisabledReason:"out_of_credits"` 無超額緩衝 | 逐字稿 sid `04b38d83` 2026-11-13T13:22:50Z～13:22:57Z | SA 實證；高 |
| S2 | `claude -p -r` 在 TTL 內可命中：e9f8e2cb relay_seq 0（冷續）cache 寫 863,852；relay_seq 1（10 分後）寫 13,713／讀 143,329 | `autosdd_resume_cost.jsonl` | SA 實證；n＝1 組 |
| S3 | API 層快取：層級 tools→system→messages；改工具定義使其下全部失效 | https://platform.claude.com/docs/en/build-with-claude/prompt-caching | SA 親讀；高 |
| 補1 | 牌價倍數（相對基礎輸入價）：5 分鐘寫入 ×1.25、1 小時寫入 ×2，各模型皆同；**快取讀取因模型而異**——Fable 5.x／Mythos 5.x ×0.025、Opus 5.5 與 Sonnet 5.5 ×0.05、Haiku 5.5 與其餘模型 ×0.1 | https://platform.claude.com/docs/en/about-claude/pricing ；寫入倍數另見 https://platform.claude.com/docs/en/build-with-claude/prompt-caching 原文 | 主控派查閱棒 2026-11-15 補讀；寫入倍數為原文、讀取倍數由表內單價自除，抓取工具回傳未與原始 HTML 逐字比對；中高 |
| 補2 | 覆核 P1：訂閱額度內主對話預設 1 小時（API 金鑰／雲端／超額 credits 為 5 分鐘）；子代理即使在訂閱下也是 5 分鐘，**但可自行選較長的壽命** | https://code.claude.com/docs/en/prompt-caching | 同上；與 Architect 親讀一致＝兩次獨立讀取 |
| 補3 | 預設壽命 5 分鐘、每次使用刷新；壽命自「寫入或讀取該筆的請求開始」起算，不是回應結束 | https://platform.claude.com/docs/en/build-with-claude/prompt-caching | 同上；原文 |
| 補4 | 官方降低用量建議（任務間 `/clear`、自訂壓縮指示、Sonnet 做多數工作、冗長操作外派子代理、hook 先濾輸出、CLAUDE.md 目標 200 行內、閒置時的提示建議／回顧／閒置壓縮可關）；`/usage` 的「Prompt cache (main)」行顯示冷熱與壽命 | https://code.claude.com/docs/en/costs | 同上；原文 |
| 補5 | **快取讀取 token 如何折算進訂閱的五小時窗與週額度：文件未載**（費用頁只說方案內用量不以金額計） | 同 補4、補1 | 同上；待真機回歸量測 |

**對損益表的影響（2026-11-15 補讀後）**：SA／Architect 先前口述的「讀取 ×0.1」只對 Haiku 成立；主控（Fable）的牌價讀取是 ×0.025，牌價上冷重寫（×2）對保溫讀取的比是 80 比 1、不是 20 比 1。§2.15.2 的損益表以本帳號逐字稿回歸出的「每 token 佔五小時窗百分點」為準、不以牌價推算（補5：折算方式文件未載），故表內數字不改；牌價只作方向佐證——「等待 ≤5 小時時保溫勝過冷重寫」的結論方向不變且餘裕更大。補2 的「子代理可選較長壽命」是 §2.14.4 X9 之外的新選項，列入第二期前置評估，本期不動。

**仍未讀到**：settings-reference 的 `idleCompaction` 與 statusline 頁細節、changelog 2026-08-15～11-06 區段（只讀到 2.1.319～2.1.325，其中無快取壽命變更條目）、Anthropic 工程部落格與相關論文（未搜尋）。依賴這些頁的結論（statusline 是否帶 rate limit 欄位、idle compaction 觸發條件）維持「待真機驗證」或「未查證」，第二期動工前先讀。查閱受阻的成因＝唯讀網路查閱與派代理共用同一個扇出上限（本輪兩個 session 共 5 筆以上真實阻斷）；修法會動守衛面，另成一批、立案與修復同一個 commit。

#### 2.15.2 決策

**D1　窗內配速床（pace floor）：把「超前」由出聲變成 cap 的煞車力**

缺口（讀程式確認）：`quota_pace.burn_step` 判超前只把該軸視野夾到 far（乘數 0.5），而 free 帶（<50%）`_base_cap=None`，`None×0.5` 仍是 `None` ⇒ **超前在 free 帶對 cap 零煞車力**（上列證據 3）；攤提 `band_inputs` 只在長窗自軸達 converge 才收緊（2026-08-16 掌舵者「use-it-or-lose-it」裁決），週軸 <70% 時五小時窗完全不攤平。

機制：只抬高餵給 `pct_band` 的水位、永不調低。

- 允許線 `allowed(t) ＝ 100 × elapsed_frac ＋ B`，`B ＝ pace_burst_pp`（出廠 20，窗初容許一波並行派工）；`elapsed_frac ＝ 1 − 剩餘分鐘／窗長`（與 `quota_pace.lead_pp` 同一算式，不另寫第二份）。
- `over ＝ pct − allowed`：`over ≤ 0` ⇒ 不動；`0 < over ≤ S` ⇒ 餵入水位至少 `converge_pct`；`over > S` ⇒ 至少 `prepare_pct`；`S ＝ pace_step_pp`（出廠 10）；上界 `halt_pct − 1`（推導值永不觸發 halt，同攤提）。
- 只作用在**最短窗軸**（由 `quota_pace.windows()` 的窗長導出，不認桶名；`session` 與 `five_hour` 同窗長者各自以自己的水位算）。
- 動作＝既有致動器：水位抬進 converge／prepare 帶後，`quota_gate` 的 300 秒扇出 cap（rc 2 擋 `Agent`／`Task`／`Workflow`；`WebFetch`／`WebSearch` 自 §2.16 起不進此帳）自然收緊；**零新致動器**。主控自己的呼叫不受 cap 管（那是 §2.15 之外的成本題，見 D4／分期表）。
- 免套用（回原值，逐位元等於無本功能）：① 趕工戳記有效；② 任一更長窗軸距 reset 的分鐘數**小於**短窗剩餘分鐘（長窗在本短窗內就翻頁⇒用掉不留；等於不免）；③ 窗長或距離不明（`lead_pp` 回 `None` 的同一組前置）；④ 清倉授權（`quota_burndown`）對該軸 `hold` 為真（SD 補：清倉＝操作者明示要把剩餘額度用盡，配速床不得與之相抗）。別家模型的 model-scoped 軸（`_amort_skip` 遮罩）既不算短窗也不算免套用②的長窗。
- 與 2026-08-16 裁決相容：`B＝20` 時允許線在已過 80% 窗長（300 分窗的第 240 分鐘）起 ≥100 ⇒ 床自動消失，短窗剩餘額度照樣可在窗尾用完；床改變的是**速率**、不是總量。

例算（五小時窗＝300 分、預設 B＝20／S＝10／converge 70／prepare 85；cap 為 `quota_policy._cap_for` 現值：converge×far＝2、prepare×far＝1）：

| 情境（已用／剩餘分鐘） | 允許線 | over | 餵入水位 | 預期 cap | 出處 |
|---|---|---|---|---|---|
| 38pp／247 分（已過 53 分） | 37.7 | +0.3 | ≥70（converge） | 2 | 2026-11-15 08:51 `--pace` 實測點 |
| 43pp／244 分 | 38.7 | +4.3 | converge | 2（今天印 `cap=None`） | 同日 08:56 gate 輸出 |
| 48pp／230 分（已過 70 分） | 43.3 | +4.7 | converge | 2 | 2026-11-14 夜「70 分鐘 48pp」形態 |
| 60pp／210 分（已過 90 分） | 50.0 | +10.0 | converge（邊界：`over＝S` 不進 prepare） | 2 | 邊界例 |
| 61pp／210 分 | 50.0 | +11.0 | ≥85（prepare） | 1 | 邊界例 |
| 99pp／30 分（已過 270 分） | 110 | −11 | 原值 | 不動 | use-it-or-lose-it |

**D2　趕工戳記 `sessionctl rush`：自帶到期的人工宣告，只關配速床**

- 形態＝有效期戳記，不是環境變數（X23）。`python tools/sessionctl.py rush --hours <H> --why "<WHY≥8字>"` 寫戳記檔（`endurance_env.trace_dir()/quota_rush.json`，持久目錄，跟 `quota_burndown` 的落款同一個家）；`--off` 撤銷；`--status` 查。到期即失效（讀取端判斷，無常駐程式）。
- 有效期上限 5 小時（`H` 須 `0 < H ≤ 5`）；超過、非數字、`why` 去頭尾空白後少於 8 字，或 `AUTOSDD_UNATTENDED` 有設 ⇒ 拒絕（rc 2）。讀取端對無人窗口同樣一律忽略戳記（無人窗口無人可宣告趕工；較緊的方向），**不分載體**：`overlay()` 在 `AUTOSDD_UNATTENDED` 有設時連手設的 `AUTOSDD_QUOTA_PACE_RUSH_UNTIL` 一併移除。讀取端對 `why` 去頭尾空白後不足 8 字的戳記也視為無戳記（與寫入端同一條下限）；讀取位置＝寫入端此刻會落腳的那一處（`endurance_env.trace_dir_peek()`，與 `trace_dir()` 同判準、不 mkdir），主居所健康時不併讀系統暫存（2026-11-15 安全審查 P3-1～P3-3 修復）。
- **射程只有配速床**：既有四道門檻、攤提、halt、cap 階梯一律照舊 ⇒ 不放寬任何既有門檻。誰能開：掌舵者明示或任務書宣告「趕工」時由主控執行，`why` 引座標。
- 承載（SD 對 Architect 稿的修正，見 §2.15.3）：戳記由 `quota_gate.policy_env()` 的出口疊成 `AUTOSDD_QUOTA_PACE_RUSH_UNTIL`（epoch 秒；自帶到期；hook 每次觸發重讀 ⇒ 開了戳記後**已在跑的其他 session 下一次呼叫即生效**，不必重啟），經 `load_policy` 進 `Policy.pace_rush_until`；`decide()` 以 `now` 判有效。所有走 `policy_env()` 的消費端（gate、`--pace`、簡報、無人巡邏）因此看到同一個 cap，不會出現「同一件事兩個數」。
- 痕跡：`pace_rush_on`／`pace_rush_off` 與配速床抬水位的 `pace_floor` 落同一個檔 `autosdd_pace_floor.jsonl`（持久痕跡目錄），供 M-P4／M-P7 取數。

**D3　與「週額度常態用到 100%」（掌舵者 2026-11-07 指令）如何同時成立**

- 換算：同一次 `--pace`（2026-11-15T08:51:17+08:00，sid `ff7d69c4`）Fable 週軸剩 22pp、剩 8467 分鐘、r＝4.3（n＝84）⇒ 一個滿 100pp 的五小時窗約等於週軸 23pp ⇒ **週額度只夠約 4.3 個滿窗**。窗多、週少：把五小時窗攤平不會讓週額度用不完，真正稀缺的是 Fable 週軸，不是五小時窗。
- 床只改速率不改總量（見 D1 末條）；週軸在短窗內翻頁時免套用（免②）；掌舵者宣告趕工時全關。
- 護欄指標 M-P4 持續量週軸 reset 前的最後讀數；基線與撤回條件見 §2.15.7。**任一週低於基線且該週 reset 前 24 小時內有 `pace_floor` 落款 ⇒ 撤 D1**（週用滿是上位目標）。

**D4　保溫（keep-warm）裁定：主控在條件內有條件推翻 X9；子代理維持否決；實作屬第二期**

損益（Fable 主控、1 小時快取、每 50 分保溫一次；K＝⌈T／50⌉；c＝單次保溫、W＝冷重寫、S＝交接開新 session；中心係數／悲觀比 10）：

| 上下文 N | c（pp） | 等 3 小時（K＝4） | 冷重寫 W | 交接開新 S | 保溫勝過重寫的 K* 上限（中心／悲觀） |
|---|---|---|---|---|---|
| 10 萬 | 0.18 | 0.7 | 5.5 | 5.7 | 31／10 |
| 20 萬 | 0.35 | 1.4 | 11.0 | 6.2 | 31／10 |
| 30 萬 | 0.52 | 2.1 | 16.5 | 6.7 | 32／10 |

撞牆等待實測 5 件（15／47／164／167／191 分）⇒ K≤4，**悲觀比下仍 ≤10 ⇒「≤5 小時等待時保溫勝過冷重寫」穩健**。保溫 vs 交接：N≥20 萬時 S≈6～7pp 一次付清，之後每次呼叫少讀 (N−11 萬)×1.7e-6 ⇒ 30 萬時約 13 次回本、25 萬約 25 次、20 萬約 39 次（悲觀比約 ×2.4；SA 同表另以 27 次計 20 萬，口徑差在讀取係數取整，兩者皆 n＝2 聯立）。

決策表（純函式 `keepwarm_verdict(N, 預期等待 T, 是否有下一步)` 的契約；第二期實作；6 萬下界與表格取值為判斷值、不穩健，以回放校）：

| N ＼ 等待 T | ≤55 分 | 55 分～3 小時 | 3～5 小時 | >5 小時／未知 |
|---|---|---|---|---|
| <6 萬 | 無動作 | 放棄 | 放棄 | 放棄 |
| 6 萬～R1(25 萬)，有下一步 | 無動作 | 保溫 | 保溫 | 保溫至 K_max＝6 後放棄 |
| 6 萬～R1，無下一步 | 無動作 | 放棄 | 放棄 | 放棄 |
| ≥R1 | 無動作 | 交接 | 交接 | 交接 |

- 情境一（五小時窗提前用完等 reset）：`five_hour ≥ 100−R`（保溫保留 **R＝5pp**，只作用在 five_hour 軸、不碰週軸 halt，`HALT_PCT=100` 的週額度用滿目標不受影響）∧ 距 reset ≥55 分 ∧ N<R1 ⇒ 停工後保溫（每 50 分一次至 reset）；N≥R1 ⇒ 牆前預先交接；距 reset <55 分 ⇒ 無動作（1 小時 TTL 覆蓋）；**撞到 100% 才想保溫不可行**（S1：被拒請求不讀不寫）⇒ 保溫必須在牆前預留。5pp 夠用的依據：K≤4×c≤0.45＝1.8pp，×2 誤差＝3.6≤5；保留 10pp 多留 5pp 純浪費（X17）。
- 情境二（主控閒置等人／等背景任務）：背景任務不保溫，維持 §2.14.2 決策 4（等待自帶截止 40 分 <60；**在飛背景子代理期間的保溫見 §2.18 D1**——`sessionctl watch` 的 keepwarm 把決策 4 套到無法自帶截止的子代理上）；等人且 N<R1 且有明確下一步 ⇒ 回合結束前排保溫，上限 K_max＝6（約 5 小時），人回來即自然停止（6×0.45＝2.7pp 低於 W 的悲觀上限）；等人且 N≥R1 ⇒ 交接；無下一步 ⇒ 放棄（讓它過期，0 成本）。
- **誰發保溫請求**：互動視窗＝本 session 自己的 `ScheduleWakeup`（50 分）——同行程、同系統提示、同工具表，前綴相同是結構保證（P2）；外部 `claude -p -r` 只用於無人窗口（本就是 `-p`；S2＋P1），互動視窗不用（X16）。保溫回合固定字面：「保溫回合：不做任何工作，重排下一次 ScheduleWakeup（50 分）後結束」，輸出 ≤50 token。
- 與 X9 的關係：§2.14.4 X9 否決的是「子代理以 5 分鐘內短輪詢保溫」（每小時 12 次、屬定時喚醒保溫），**維持不變**；本決策是**主控（1 小時桶）在上列條件內的保溫**，推翻 X9 對主控的適用範圍，不推翻對子代理的否決。前置真機驗證 V-K1～V-K4（TCS §10.7）全數通過前不得實作；任一不過 ⇒ 本決策改寫為「已驗證不可行」。

**D5　量測：補指標，不新增只出聲的提醒**

原定第一期補量測 M-P1、M-P3、M-P4、M-P7、M-C1（`waste_census` 套件新增配速指標模組）與 AC-7 回放（`--replay-pace-floor`）；**實作回填（2026-11-15）：兩者本期未做，改列後續期**（見 §2.15.5 實作狀態回填）；M-P2、M-P5、M-P6 的分子要等第二期保溫上線才有，第一期以既有 M1（主控閒置逾 1 小時重寫）作 M-P2 代理指標。定義與基線見 §2.15.7。

#### 2.15.3 設計取捨與落點

- 判準住新檔 `tools/lib/quota_pace_floor.py`（純函式、零 I/O、Python 3.9 可載入，同 `quota_pace` 的相容紀律）；趕工戳記與痕跡住新檔 `tools/lib/quota_rush.py`（含 `cli`）；`tools/sessionctl.py` 只加分派 `rush`。兩檔皆在已登記的扁平家族 `tools/lib/quota_*.py`（Root_Layout §3 額度守衛列），不另成套件。
- **對 Architect 稿的三處以程式為準的修正**：(a) `quota_pace.py` 現為 371／400 斷言行（餘裕 29），配速床＋說明行約 50 行放不進 ⇒ 判準獨立成檔，`quota_pace.resolve()` **不動**，由 `quota_policy.axes_of` 在 `resolve()` 之後以 `quota_pace_floor.apply` 後處理（無循環匯入）；(b) Architect 稿的 `decide(..., rush=False)` 逐呼叫端透傳，但 `decide()` 的生產消費端有八處以上（`quota_gate` 四處、`quota_messages`、`session_brief` 兩處、`quota_escalation`、`relay_machine`、`selfimproving`…），逐點改會漏、且 `quota_gate.py` 是 hub tier（500／500，餘裕 0）⇒ 改以 `Policy.pace_rush_until` 承載、由 `policy_env()` 出口一次疊入（見 D2）；(c) 戳記檔放持久痕跡目錄（`endurance_env.trace_dir()`，與 `quota_burndown` 落款同家，沙箱可由 `AUTOSDD_TRACE_DIR` 圍籬）而非 `~/.autosdd/quota_rush.json`，避免測試讀到開發機真實戳記。
- **`draining()` 不吃配速床**（`decide(..., pace_floor=False)`）：PRD §4.3 的 DRAIN 判準是原始 U5h 對 DRAIN 線；床把水位抬進 prepare 帶後 `band ∈ DRAINING_BANDS` 會讓「不得壓縮」在水位 55pp（已過 60 分、允許線 40）時就成立，與 context 守衛要求壓縮相衝（TCS §10 AT-QP-37）。`compact_margin_breached` 本來就讀 `axis.pct` 原值，不受影響。
- **床抬到 prepare 帶的副作用**：`quota_gate.quota_prepare_actions` 掛在 `band == PREPARE`（寫可重啟點任務書，一個 reset 視窗只做一次）；床把水位抬進 prepare 時同樣會觸發（攤提抬水位今天已是同一路徑）。列入 §2.15.6 劃界與 M-P 監看，不另設旁路。
- `quota_gate.py` 淨行數須 ≤0：現餘裕 0，需要新增的接線約 3～4 行（匯入 `quota_rush`／`quota_pace_floor`、gate 路徑一行落款、`pace_report` 一段）——Developer 動工前先抽出等量程式（候選：halt 標記三函式、`pace_state`＋`settled_quota`），同 commit 重釘 hub 棘輪，**不得調高 hub 預算**。
- 回放（**後續期，未落地**）：`--replay-pace-floor` 以 `quota_burn.jsonl` 每列（需帶 `resets_at`）重建 `QuotaState` 各算一次有床／無床的 cap，輸出「床會開的列數」與五件撞牆窗各自最早開床時刻；不設通過數字，交 QA 判讀。

#### 2.15.4 已否決（續 §2.14.4 的 X8～X15；F3＝X9、F14＝X8 沿用不另編）

| 代號 | 方案 | 理由 |
|---|---|---|
| X16 | 互動視窗由外部排程 `claude -p -r <sid>` 保溫 | 互動行程不會看到 `-p` 追加的回合 ⇒ 同一逐字稿兩條鏈頭（§2.11 的 OTHER_DRIVER 判準會誤觸）；互動與 `-p` 工具集是否相同文件未載；同行程 `ScheduleWakeup` 是結構保證 |
| X17 | 額度保留 10%（掌舵者提案的上緣） | 實測等待 K≤4×c≤0.45＝1.8pp，×2 誤差仍 <5；多留 5pp 純浪費；5% 夠 |
| X18 | 換 session 門檻改成「pp／回合」 | 逐字稿量不到每請求 pp（落款 691 筆／2.5 月）；閘門輸入必須逐請求可量；pp 模型只用來**選** token 門檻的值 |
| X19 | 撞牆後才保溫、或等 harness 寬限再做 | 100% 後請求被拒（S1）；wrap_up 寬限只夠收尾 |
| X20 | 第一期就以 `updatedInput` 自動改派工模型 | 平台行為未驗證；阻斷形態可做但暴露證據不足，移第二期（`model_hint` 仍只建議） |
| X21 | 以 `pace_ceiling` 驅動攤平 | 它只改 horizon，free 帶 cap=None 時零煞車（D1 缺口） |
| X22 | 用 sleep／延後派工攤平 | 屬等待壞形態（鐵律六）；cap＋阻斷是既有致動器 |
| X23 | 趕工用環境變數 | 改 env 要重啟、易忘關；戳記自帶到期、可稽核 |
| X24 | 配速床也套長窗（週） | 週已有攤提；套上會與「週用滿」直接衝突 |
| X25 | CLAUDE.md 改 `@import` 拆檔瘦身 | import 在載入時展開，token 不變 |
| X26 | fork 子代理共用父快取 | fork 跑主控模型、`model` 覆寫被忽略（根 CLAUDE.md 已禁） |
| X27 | 快取冷時仍以 `/compact` 當收斂出口 | P4：冷 compact 整份 uncached 重算加摘要輸出，比交接貴；出口文字改「只給交接」屬第二期（C-5） |

#### 2.15.5 分期

| 期 | 內容 | 前置驗證（不依賴者標「無」） |
|---|---|---|
| 第一期（一支開發棒、一個五小時窗；**已落地＝D1、D2、文件與連動面**；D5 量測與 AC-7 回放未做，順延至後續期） | D1 配速床、D2 趕工戳記、D5 量測（M-P1／P3／P4／P7、M-C1、AC-7 回放）、文件與連動面 | 無（不依賴未驗證的平台行為）；真機 V-P1～V-P5（TCS §10.6） |
| 第二期 | 保溫致動（`keepwarm_verdict`＋ScheduleWakeup 50 分，R＝5pp 的 five_hour 專屬停工線）；牆前預先交接＋reset 時一次性 `handoff --spawn`（**已由 §2.17 落地**）；R1 下修（25 萬→20 萬；以 `--replay-hard-ctx` 回放「首次 ≥20 萬後的主控呼叫數」中位 >95 為條件）；冷時只給交接出口（C-5）；模型降級阻斷（opus／fable 在 converge 以上被擋、行內理由逃生；另需暴露證據，無則登記理論洞）；statusline 每請求取樣；扇出 cap 外加同時在跑代理數上限（第一期上線 7 天後 M-P1 未改善才做） | V-K1～V-K4（保溫）、V-S1（schtasks 開互動視窗）、V-M1（statusline 欄位）；動 `.claude/` 須主控親套 |
| 第三期 | 無人窗口 `claude -p -r` 保溫；C-4 開場瘦身（根 CLAUDE.md 82.6 KB→約 45～50 KB，估算非量測；獨立 SDD 鍵）；C-1 主控模型切換自動化（Fable 週軸收緊且超前時主控改 Sonnet，「Fable 當用則用」偏好衝突，待掌舵者以互動選項裁定） | V-U1（同 sid 連續兩次 `-p -r` 間隔 50 分仍命中，且與哨兵雙駕駛判準共存不誤判）、V-C4（子代理與 `-p` 是否收到 rules 與 skill 描述） |

後續期的細項本節只登記前置與方向，**本期不寫 AT**。

**實作狀態回填（2026-11-15，依實作事實改規格；WHY＝規格不得宣稱磁碟上不存在的東西）**：第一期實際落地 D1 配速床（`quota_pace_floor`）、D2 趕工戳記（`quota_rush`，經 `sessionctl rush`）、為騰出 hub 餘裕自 `quota_gate` 抽出的 `quota_halt_marker`（原稿未列、gate 以單行 re-export）。**未落地、順延後續期**：D5 的配速指標與回放模組（TCS §10 的 AT-QP-56～63）。實作與原稿的六處差異：
1. 免套用的「短窗」加上界（最長 1440 分鐘，**含等號**：恰 1440 分仍算短窗、1441 分起不算；AT-QP-17c 釘住邊界）：只剩週軸時 session 無鄰軸可繼承窗長，最短窗軸會變週軸，床會對週軸生效、違反 X24 與「週用滿」；AT-QP-17b 釘住。
2. AT-QP-19 的數字改 55／70（窗 200）：原稿 40／60 算不出 70／85。
3. AT-QP-38 原稿「既有 M7 判準對全文綠」於改前即不成立（`pace_report` 第一行本無 `kind=`）；改為只對本期新增的床段與 describe 句判 M7（AT-QP-70）。
4. `log_floor` 一次決策只落一列（取超線最多的軸）。
5. ~~`Decision.pace` 的 hold 固定為空~~（2026-11-15 安全審查 P3-4 修復：`decide()` 帶 burndown 時以 `burndown.masks()` 的 hold 傳入 `_floors`，`pace` 與實際餵入水位同源，hold 軸報 `exempt-hold`、不再誤落 `pace_floor` 列污染 M-P4 撤回分子；回歸鎖＝`test_quota_rush.py::ReviewP3HardeningTest::test_p3_4_*`）；`burndown.apply` 內部呼叫 `axes_of` 仍預設套床（生產無 `pace_floor=False` 搭 `burndown` 的組合）。
6. AT-QP-55 的站點表登記 11 個檔（含三支探針模擬器與 doctor 的直接 `load_policy`）。
另：趕工戳記讀取端改走唯讀路徑查找（不得在 `--check` 時憑空建立痕跡目錄），回歸鎖＝`ReadSideCreatesNothingTest`。

#### 2.15.6 誠實劃界

- 床與趕工戳記是**判斷值**：`B＝20`、`S＝10` 未量測，只准下修；第一期以回放（AC-7）與 M-P7 校正。M-P7 過高（>50% 窗有趕工戳記）代表床太緊，處置是檢討判準，不是放寬方向鎖。
- 換算係數 n＝2、寫讀比可落 10～60；Sonnet／Opus 係數量不到，D4 的表只適用 Fable 主控。落款稀疏（691 筆／2.5 月）是換算率與曲線的最大誤差源，上線後若有 statusline 取樣才能收斂到 ±5%（V-M1）。
- 配速床只管**扇出**（cap）；主控自己的呼叫（本窗 5.5k 新增寫入／呼叫、0.4～0.75pp／呼叫）不受 cap 管，真正的省量要靠 C-1／C-4／C-6（第二、三期與慣例），本期不宣稱解決。
- 「床擋過派工」的證據＝`pace_floor` 落款存在（床抬過水位、cap 因而比無床時更緊），不證明某一次派工因此被拒；M-P4 的撤回條件以此為近似。
- 床抬到 prepare 帶會觸發 `quota_prepare_actions`（任務書落盤，視窗內只做一次）；若觀察期內該副作用過於頻繁，檢討的是 S（`pace_step_pp`）的取值，不是在 prepare 帶開旁路。
- 趕工戳記與 `AUTOSDD_QUOTA_PACE_RUSH_UNTIL` 載體**不具防偽性質**（同 `quota_burndown` 的誠實聲明）：只讓事後可稽核、失效可偵測；手設該環境變數等同趕工至該時刻，仍受 5 小時上限約束。
- `ScheduleWakeup` 沒有任何憑證（不寫磁碟、無登錄），保溫的失效是靜默的；第二期以 M-P5（保溫請求命中率，逐字稿事後量）與 V-K1 的「喚醒間隔≈50 分」判準補這個洞。
- 理論洞（P4，登記不修；DEF-200-591 審查所列，無暴露證據）：`quota_policy_env._parse_env_number` 不判 NaN；互動窗口內子代理也能發戳記（設計自承只可稽核）；子代理 PreToolUse payload 是否必帶 `agent_id` 未真機驗證。
- 第二期前置真機驗證**全數未做**；statusline 欄位、idle compaction 觸發條件、價格比皆「未讀到」，不得據以宣稱。

#### 2.15.7 指標、基線與撤回門檻（觀察期：2 個完整週額度週期＝14 天；第 7 天中期檢查只看回退判定；評估法＝中斷時間序列＋逐列回放，n 小時不做 A/B）

| 指標 | 定義與資料來源 | 基線（含樣本與不確定度） | 改善判定 | 撤回判定 |
|---|---|---|---|---|
| M-P1 撞牆次數 | halt 標記（binding 為五小時窗軸，窗長以文法判）件數／週 | 2.5／週（14 天 5 件，SA Q5；n 小） | 連 2 週 ≤1／週 | ≥基線 |
| M-P2 牆後冷重寫 | 第一期以既有 M1（主控閒置逾 1 小時重寫）作代理；起因＝額度牆的細分待第二期 | 13 件（SA；起因判讀為 SA 腳本，未入 repo） | −50% | 不降 |
| M-P3 窗內早燒 | 窗前 40% 時間內水位 ≥70 的窗占比（`quota_burn.jsonl`，需帶 `resets_at`、窗內 ≥3 樣本） | 28 個可辨窗中 1 個＋2 個撞牆窗（落款稀疏） | 降為 0 | — |
| **M-P4 週用滿（護欄）** | 週軸 reset 前最後讀數（`quota_burn.jsonl`，末列距 reset ≤24 小時者；以窗長 ≥10080 分的軸、reset 時刻取整到小時分組） | **weekly_all：9 週、中位 90、範圍 72～98**；weekly_scoped 同 9 週中位 83、範圍 43～96（SD 本棒自 790 列、2026-08-19～11-15 現算；末列常在 reset 前數小時，**低估偏差**；reset 時刻在不同週漂移） | 不低於基線中位（不退化線 90；目標 95） | 任一週低於 90 **且** 該週 reset 前 24 小時內有 `pace_floor` 落款 ⇒ 撤 D1 |
| M-P5 保溫命中（第二期） | 保溫請求 read／(read＋creation)（逐字稿） | 無 | ≥0.95 | <0.8 ⇒ 撤保溫 |
| M-P6 保溫成本（第二期） | 保溫實耗 pp 對預測 | 無 | 實耗 ≤2×預測 | >保留 R ⇒ 撤 |
| M-P7 趕工使用率 | 有趕工戳記的窗占比（`autosdd_pace_floor.jsonl` 的 on 事件與 `until`） | 0（本功能新） | — | >50% ⇒ 床太緊，回頭校判準 |
| M-C1 主控每呼叫新增寫入 | 主控 sid 平均 `cache_creation`／請求（逐字稿） | 本窗 5.5k（SA 單窗） | ≤2.5k | — |

證偽前提：上線後若 statusline 取樣可得，重算換算係數；寫讀比落在 10～60 以外，D4 的表全部重算。

### 2.16 網頁讀取不進派發帳（2026-11-15；DEF-200-590）

- **暴露證據**（真實逐字稿）：subagent `agent-a4e1e457bf095f721.jsonl` 第 155／156／167 筆、`agent-aaf1e558ab98a0469.jsonl` 第 127 筆，`PreToolUse:WebFetch hook error` ⇒ 逐字「`band=converge … cap=2 … 每 300s 最多 2 次扇出，本視窗已用 2 次 ⇒ WebFetch 本次不執行`」（binding=`weekly_scoped` 78%）。查閱型子代理連讀兩頁即被擋。
- **成因**：`quota_gate.quota_gate()` 對 `BLOCKING_TOOLS` 全員一視同仁——`WebFetch`／`WebSearch` 與 `Agent`／`Task` 共用同一本派發帳（`claim_dispatch`）與同一個 `cap`。派發帳的設計前提（§2.6／ADR-XPLAT-005）是「一次派發＝生出一個會持續燒額度的 agent」；網頁讀取不生出任何 agent、單次成本是一頁文字，不屬於該前提。後果雙向：網頁讀取吃光 cap 名額 ⇒ 擋住真正的 `Agent` 派發；`Agent` 派發吃光名額 ⇒ 擋住查閱。
- **決策**：新增 `quota_gate.WEB_READ_TOOLS = ("WebFetch", "WebSearch")`；PreToolUse 於派發邊緣對它們**不記帳、不比 cap**（`decision.cap > 0` 時直接放行）。零新環境變數、零新逃生口、不放寬任何門檻。
- **保護不變弱（三處仍擋）**：① halt 帶（≥ `halt_pct`）在豁免之前就 rc=2 返回，網頁類照擋；② `cap <= 0`（量不到而持久沿用 0 的遲滯）不豁免，落回派發帳照擋；③ context 尺的高水位阻斷走 `context_budget_guard.BLOCKING_TOOLS`（本修不動，仍含網頁類）。`Agent`／`Task`／`Workflow` 行為逐字不變。
- **已否決**：另開第二本網頁專用帳與第二個 cap（多一組門檻與環境變數，而網頁讀取本身不生出併發，計數無對象）。
- **劃界**：網頁讀取的 token 成本仍落在本 session 的 context 與額度，由 context 尺與額度 halt 帶節制；本節只修「被當成派人」。
- 回歸鎖：`tools/tests/test_context_budget_guard.py::WebReadsAreNotDispatchesTest`。

### 2.17 額度自願停工的續航（park）：停工必掛憑證、到點由新 session 帶交接包接手、Stop 守衛只看短窗原始讀數（2026-11-16；DEF-200-594～596；已實作，真機驗證待做）

> 數字一律現查：額度門檻 `python tools/lib/quota_policy.py --print-env-example`；續航量測 `python tools/probe/waste_census.py --resume-metrics --since-days 14`；park 現況 `python tools/sessionctl.py park --status`。本節只寫判準、出處、方向與撤回門檻。驗收契約＝`docs/03_testing/contracts/TCS-SessionPark-20261116.md`（下稱 TCS）。**本輪只做 H 路**；同 session 背景等待者（W 路）列為否決案 X38。

#### 2.17.0 立案與暴露證據（守衛面准入：三取一皆成立；`session_resume_planner.py`、`tools/lib/sessionctl/**`、`.claude/hooks/check_pending_handoff.py` 皆在守衛面清單內）

1. **掌舵者真機回報**：sid `798a7bf1-a991-4a08-8ab8-d0736296f823`，2026-11-16 08:54（+08:00）「為何又停在這理要我下指令繼續做呢?」。
2. **非構造性逐字稿**（座標＝`~/.claude/projects/<repo slug>/798a7bf1-….jsonl` 的行號）：
   - 行 634（2026-11-15T19:17:12.620Z＝03:17 +08:00）最後一則 assistant：「…五小時額度已到 98%（約 04:00 重置），這一窗先停在這裡…」；usage input 2／cache_read 217,962／cache_creation 1,482（上下文約 219,446）。
   - 行 635 `stop_hook_summary`：三支 Stop hook 都跑了，無輸出、未阻斷。
   - 行 637（2026-11-16T00:54:03.896Z＝08:54，`origin.kind=human`，443 字）：掌舵者回來。行 640（00:54:22.783Z）第一個回合 cache_creation 188,230／cache_read 32,748（只命中系統層，約 10.4pp）。
   - 04:00 reset 到 08:54 之間沒有任何 assistant 記錄＝**閒置約 294 分鐘**；`quota_burn.jsonl` 該窗 `resets_at.five_hour` 為 2026-11-15T20:00Z（＝04:00 +08:00）。
3. **真實輸出（墊高現象）**：五小時軸原始 23%、剩 43 分，加上 `seven_day`／`weekly_scoped(Fable)` 各 78%、剩 8467 分、攤提比 4.3 ⇒ `Decision.per_axis` 的五小時軸 `band=prepare`、`note=burn-thrifty+amortized`（`Axis.pct` 仍為 23.0）。照 `Decision.band` 判，每一回合都會被推回（見 D2、否決 X32）。

成因鏈：準備帶訊息叫主控「收斂到可重啟點」，而能讓哨兵接手的 halt 標記在 `AUTOSDD_QUOTA_HALT_PCT=100` 下要到 100% 才寫 ⇒ 從 prepare 帶停工到真正撞線之間是無人區；哨兵只認撞線、寬限提示、halt 標記、idle，這一場三者皆無而判 `patrol`（要靜止滿 6 小時才解除，任何分支都不續跑）；`check_pending_handoff.py` 詞表只收「您」字系列，漏掉「仍由你決定」；另一項暴露：停工訊息把人導向「在冷掉的 21.9 萬上下文舊視窗說一聲繼續」。

#### 2.17.1 平台事實（查閱日期 2026-11-16）

| 代號 | 事實 | 出處 |
|---|---|---|
| Q1 | `autoContinueAtUsageLimit` 只在「用量上限在任務進行中擋下 Claude」時等待並續接；`quota_auto_resume_fired／stale／disabled` 為 Notification（v2.1.234 起）；睡眠逾約 30 分改等 Enter | https://code.claude.com/docs/en/interactive-mode（§2.10 已引同源） |
| Q2 | `ScheduleWakeup` 1 分～1 小時、只用於自訂步調 `/loop`；無憑證 | https://code.claude.com/docs/en/tools-reference；根 CLAUDE.md〈工具選型〉 |
| Q3 | 主控快取 1 小時、子代理 5 分鐘；每次命中重設計時器 | https://code.claude.com/docs/en/prompt-caching；§2.15.1 |
| Q7 | Windows 排程工作的 `S4U` 登入類型落在 session 0（無桌面）；`Interactive` 只在使用者登入時跑 | `session_resume_planner._SCHTASKS_PRINCIPAL` 註解；官方 Task Scheduler 語意 |
| Q8 | launchd 不報 next-run；睡著的 Mac 不被喚醒 | `schedule_backend.py` 檔頭〈誠實劃界〉（本 repo 真機實測） |

`ScheduleWakeup` 在用量等待期間觸發時保留或丟棄＝查不到，本節不依賴它（X29）。

#### 2.17.2 決策（實作座標：`tools/lib/sessionctl/park.py`、`park_cli.py`）

**D1　`park`：停工是一個有型別的狀態轉移。** 因額度停工前必跑 `python tools/sessionctl.py park`。流程順序是契約（測試以呼叫序列斷言）：政策閘 → 讀 reset → 交接包 `finalize`＋`spawn_preflight` 預演 → 取代舊標記（先撤舊排程並驗證）→ 登記一次性排程取憑證 → 寫標記（寫失敗即回滾排程）。純函式 `park_route(wait_s, *, unattended, mode, carrier_ok)` 只回 `H`／`REFUSE`：無人窗口、模式非 `auto`、無排程載具、reset 量不到（不假設 5 小時，§2.1）皆 `REFUSE`，其餘一律 `H`。`park --done --why "<≥8 字>"` 是「沒有剩餘工作」的唯一豁免；`park --cancel` 撤排程；`park --status [--verify]` 現況；`park --at <ISO> --why …` 供週額度等明示停工（須帶 offset、在未來、上限 8 天）。成功時多印一行：「park 已掛好：到點（…）若這個 session 沒有人在動，就由新 session 帶交接包接手。現在可以結束回合；不要請人回這個視窗接手。」

**D2　Stop 判準 `park.stop_verdict`（純函式；接在 `converge.stop_verdict` 尾端：`_converge_stop(...) or _park_stop(...)`，`sessionctl_guard.py` 行為零改動）。** 全部成立才推回一次（`decision:block`）：① 非 `stop_hook_active`、非 `AUTOSDD_UNATTENDED`、`AUTOSDD_SESSION_SWITCH_MODE=auto`、`AUTOSDD_PARK_GUARD_OFF` 未設、`schedule_backend.has_carrier()` 為真；② **只看短窗軸**（`session`／`five_hour`／`5h`，或由窗長導出為 300 分者；模型分軸與 FALLBACK 不算），週軸一律不算——週額度常態用到 100%（掌舵者 2026-11-07），以週軸判會每回合推回；③ 🔴 **用原始讀數**：該軸 `Axis.pct`（`quota_gate.pace_state` 回的伺服器原值，須為有限 int／float、排除 bool）≥ `Policy.prepare_pct` 且 `resets_at` 為帶 offset 的未來時刻；**不得**用 `Decision.band`、`AxisReading.band`、`decide()` 的任何輸出——它們吃過攤提（`quota_pace.resolve`）與配速床（`quota_pace_floor.apply`）墊高後的水位（證據 3：原始 23% 的軸 band＝prepare）。唯一入口是 `park.prepare_hits`；先例＝`quota_gate.compact_margin_breached` 與 §2.15.3 `draining()` 都讀 `axis.pct` 原值；④ 沒有有效續航憑證（D4）；⑤ 本 session 沒有已 `--spawn` 的交接包（`handed_off`，既有換 session 路徑已處理）。量不到（`axes==()`、快取過期、reset 不明）＝不判（fail-open，落痕跡 `park_verdict_unmeasured`）。前一步不成立即回 `""`，不做後面的 I/O；任何例外放行（P0）。標記壞掉＝無憑證（fail-closed，推回至多一次，與例外放行是兩回事）。**不變式**：推回的前提必能被 `park` 滿足——Stop 守衛 no-op 的條件（無人、模式非 auto、無載具）與 `park` 的拒絕條件同源。

**D3　選路只剩一條可走（W 路否決，見 X38）。** `wait_s`＝距**觸發時刻**（reset＋`HALT_RESET_SKEW_SECONDS`＝120 秒，向後取整到分鐘；`--at` 則取整後即為該時刻）的秒數，只用於說明文字；`park_route` 不讀上下文、不讀快取壽命。

**D3b　未達準備門檻的自願停工：`park --why "<WHY≥8字>"`（2026-11-16 真機補，sid f2260ce7）。** 主控在短窗 84% 判斷「下一棒約 20pp、這一窗放不下」要停工，`park` 自動選路卻因未達準備門檻回 rc 4（痕跡 `park_refused` 兩列，2026-11-16T10:09 +08:00），只剩手打 `--at`。「放不下」是相對下一棒大小的判斷，不是固定門檻 ⇒ 沒有短窗軸達標但帶合格 `--why` 時，reset 取短窗軸的**觀測值**（`park.measured_short`：短窗軸 ∧ 有限讀數 ∧ reset 在未來，取最大值），其餘流程（交接包 finalize、spawn 前置預演、憑證、標記）逐字相同，`why` 寫進標記。短窗 reset 量不到時即使帶 why 仍 rc 4（不假設 5 小時）。**Stop 推回門檻不動**（D2 仍只走 `prepare_hits`）：放寬的是主控「可以停」的出口，不是守衛「必須停」的判準。驗收＝TCS AT-PK-46b。

**D4　續航憑證是「值」，不是宣稱。** 憑證寫在 park 標記（`endurance_env.trace_dir()/park/<sid>.json`，schema `autosdd.park/1`；讀取端走 `trace_dir_peek()`、不 mkdir、結構異常一律當無憑證，同 `quota_rush`；寫入端與讀取端共用同一份 `marker_problem` 驗證）。有效憑證兩種：`H`＝標記 `status=armed`、未過 `valid_until`（＝觸發時刻＋900 秒）、且 primary job 的排程憑證字串非空（Windows＝`NextRunTime` 的值；macOS＝`launchctl print` rc＋descriptor 回讀，憑證是 rc 不是時間值）；`DONE`＝`--done` 戳記未過期（有效到最早短窗 reset，上限 5 小時；無人窗口無效）。Stop 判準只讀檔、不 spawn、不打排程器（Stop 逾時 15 秒）；`park --status --verify` 才現場向排程器取證。排程憑證取不到（含 rc=0 但無值）⇒ `park` rc 1、不寫標記、落 `park_arm_failed`，stderr 明說「本工具不會說它已排程」。

**D5　順序與回滾。** H 路：前置 → 登記主排程取憑證 → 寫標記；標記寫失敗即 `disarm` 並以 `list_jobs` 驗證不在（量不到不宣稱已移除），落 `park_arm_failed`。`park` 要求交接包已 finalize 且 `spawn_preflight` 通過（工作樹乾淨或有 `*-wip-preserved` 標籤、無執行中代理）——**登記前**就失敗，不等到點才失敗，rc 2 並列缺項。同 sid 第二次 `park` 取代舊標記：舊排程先撤並驗證（`--done` 亦然）；任一失敗即不登記新的。排程標籤 `AutoSDD_HandoffSpawn_<sid8>_<YYYYMMDDHHMM>`（含觸發分鐘，避免對正在跑的自己 bootout，DEF-200-526 的形狀）。

**D6　到點動作＝`park --fire`（排程的 job 本體），先查「有人在動」才 spawn。** 判準依序：標記不屬於本 job 或已不是 `armed` ⇒ 跳過（`reason=cancelled|not_armed`）；無人窗口 ⇒ 拒絕（rc 4）；交接包已 ack ⇒ 跳過（`acked`）；交接包不在或已過期 ⇒ 跳過（`expired`）；`transcript_activity.live_driver(舊逐字稿, now)`（一個巡邏間隔 900 秒內有非合成對話記錄；**對話記錄判活，不是檔案 mtime**，DEF-200-560）非空 ⇒ 跳過（`live_driver`）；其餘呼叫既有 `handoff.spawn(pkg)`（其前置與 SEC-6／SEC-7 照舊）。成功＝標記 `fired`、`disarm` 自己；失敗＝標記 `failed`、寫一份 handback（`resume_route.handback_report`，下次 SessionStart 的 `announce_handbacks` 出聲）、`disarm` 自己。跳過一律落 `handoff_spawn_skipped`、標記 `skipped`、自拆。**不新增 `handoff --spawn --if-idle` 旗標**（X35）：檢查屬於 job 本體，`handoff.spawn` 語意零改動；`handoff.py` 只加一個公開預演函式 `spawn_preflight`。

**D7　哨兵讓路。** `sentinel_decide` 多一個選配參數 `park`：標記為 `armed`、`route=H`、現在 ≤ `valid_until`（觸發時刻＋900 秒）⇒ 回既有的 `patrol`（理由字面標明讓路）；`LIMIT_SPEND` 事件仍先 `escalate`；無標記或已過窗＝逐位元組同舊行為，action 集合仍恰為五個。`_sentinel_tick` 以 `park=sessionctl_park.read_marker(sid)` 傳入。成因：最後一則訊息本身撞線時，哨兵的 `arm_reset` 與 park 的排程會在同一個 reset 時刻各起一個駕駛——新 session 寫的是**另一份**逐字稿，哨兵的 `driver` 判準看不到它。

**D8　準備帶訊息與詞表。** `quota_prepare_message` 拿掉寫死的「（85~95%）」字面（門檻值已由同則訊息的 `describe()` 逐軸印出），「下一步」加「若要因額度停工：先跑 `python tools/sessionctl.py park`；不要叫人回這個視窗說繼續」。`check_pending_handoff.HANDOFF_RE` 補「你」字系列，**最終詞表只收**：待你、留給你、交給你、交由你、由你決定、你來決定、需要你、需你、你裁決。「請你」「等你」**不收**：真實面普查（`python tools/probe/handoff_census.py`，214 回合命中 14）顯示收入時造成 3 回合假紅（事後敘述，不是交棒）；不收後該 3 回合假紅消失。這兩件是順手修；根治靠 D2（結構判準，不看措辭）。

**D9　逃生口與零新門檻變數。** `AUTOSDD_PARK_GUARD_OFF`：只關 Stop 推回（讀自 hook 行程環境，模型碰不到）；`park --done --why`：行內可稽核豁免，無人窗口無效；`AUTOSDD_SESSION_SWITCH_MODE=notify|off`：park 一律 REFUSE、Stop 判準 no-op。`YIELD_GRACE_SECONDS`（900 秒，與 `quota_messages.HALT_QUIESCE_SECONDS` 同值並由 parity 測試釘住）、`MIN_WHY_CHARS`（8）、`DONE_MAX_SECONDS`（5 小時）、`AT_MAX_SECONDS`（8 天）為 `park.py` 內的具名常數、不開環境變數。

#### 2.17.3 換手判準是成本，不是容量百分比（回答「上下文才 24%，為什麼要換」）

快取成本與帳戶額度都**按 token 計**，與「佔該模型 1M 視窗的幾 %」無關；上下文 21.9 萬在 1M 視窗只佔約 22%，但冷喚醒時要整份重寫 21.9 萬 token。判準（係數取 §2.15 本帳號回歸：寫 5.5e-5、讀 1.7e-6 pp／token，n＝2；結論以**比值**表達）：

1. **冷喚醒（等待超過快取壽命，或沒有任何東西準時喚醒）**：舊 session 付 `N × w`（N＝上下文 token）；新 session 付 `N₀ × w`（N₀＝新 session 起步上下文，實測基線 92,522，見 `waste_census --fresh-baseline-ctx`；§2.15.2 表列 S≈5.7～6.7pp）。**換手划算 ⇔ N > N₀**——與視窗大小、與 w 的數值無關。本案 N＝219,446 ⇒ 舊 session 冷喚醒約 12.1pp（實付 188,230 token ≈ 10.4pp），新 session 約 5～6pp。
2. **這是「24% 為什麼要換」的答案**：不是因為 24% 很高，而是因為**舊 session 的喚醒保證不了是熱的**——實際發生的是沒有任何東西喚醒、人在 294 分鐘後回來＝冷。H 路把「喚醒」放到 OS 排程（獨立於視窗與行程），新 session 起步就是熱的 N₀。
3. **每回合熱讀**：留在大上下文的每次呼叫多付 `(N − N₀) × r`；§2.15.2 表：30 萬約 13 次呼叫回本。

**R1 絕對門檻（250,000）本輪不改。**（🔴 v2.1.22 註記：R1 已於 R216 退役、25 萬不再是換窗線，見 §2.19 D1；本段與下修討論為史料。） 理由：① park 本身就是成本判準的落地點，**不依賴 R1 出聲**（本案未出聲：R1 要 25 萬、停工時 21.9 萬）；② §2.15.5 第二期的下修條件「首次 ≥20 萬後的主控呼叫數中位 >95」，該統計 `waste_census --replay-hard-ctx` **不產出**（它的 `room_med` 是 R1 到硬門檻之間的回合數；以 R1＝200,000、H＝230,000／250,000／290,000 重放：reach_H＝15／14／12、room_med＝7／10.5／18.0，與條件無關）⇒ 條件**未能判定**，不得據以下修；③ R1 下修與 park 互不依賴，併一個 commit 只會擴大爆炸半徑。要下修時先補該統計（`wastecensus` 新指標），再依 §2.15.5 走。

#### 2.17.4 設計取捨與落點

- 判準與標記住 `tools/lib/sessionctl/park.py`（純函式＋標記讀寫＋`stop_verdict`）；CLI、job 本體、排程編排住 `park_cli.py`（皆在既有套件，Root_Layout §3 sessionctl 列已補 `park`、`park_cli`；不另成模組）。`tools/sessionctl.py` 只加分派 `park`。
- **排程原語不進 park*.py**：`CarrierPrimitivesHaveOneHomeTest` 規定排程器原語只能住宣告過的家。一次性工作的註冊住 `tools/lib/engine_resume_job.py`，新增公開的 `arm_oneshot(label, argv, cwd, fire, *, interactive)`；Windows 另需 `-LogonType Interactive` 的 Principal（Q7：S4U 在 session 0，開不出使用者看得見的互動視窗），故 `_arm_schtasks` 加 `interactive` 參數、預設值逐位元組同舊腳本；`interactive=True` 的腳本不含 S4U 也不含 fallback 分支。macOS 沿用 LaunchAgent（gui 網域＝互動）。
- Stop 接線：`converge.stop_verdict` 尾端；與 `_finalized_wake`（冷叫醒閘）互斥：交接包已 `--spawn` 則 park 不判（D2⑤），H 路要求 finalize 後 TaskStop 全部背景任務（§2.13.5）。
- 痕跡（`autosdd_session_switch.jsonl`，`switch.trace` 單一家）：`park_armed`、`park_refused`、`park_arm_failed`、`park_done`、`park_cancelled`、`park_stop_block`、`park_verdict_unmeasured`、`park_job_start`、`handoff_spawn_skipped`（欄 `reason`＝`live_driver|acked|expired|cancelled|not_armed`）、`park_spawned`、`park_spawn_failed`。
- `quota_gate.py`（hub）**不動**；其餘連動檔：`quota_messages.py`（+1 行）、`session_resume_planner.py`（+2 行）、`tools/lib/wastecensus/resume.py`（新，`report.py` 加旗標）。
- 既有測試的圍籬：`converge.stop_verdict` 尾端會呼叫 park 判準（預設讀 `quota_gate.pace_state`，快取缺時可能補量一次＝真網路），故 `test_sessionctl_converge.py::_Fence` 以 `mock.patch("lib.sessionctl.park._has_carrier", return_value=False)` 圍住、`test_sessionctl_hooks.py` 子行程 env 帶 `AUTOSDD_PARK_GUARD_OFF=1`。

#### 2.17.5 已否決（續 §2.15.4 的 X16～X27；本節 X28～X38）

| 代號 | 方案 | 理由 |
|---|---|---|
| X28 | 哨兵新增「自願停工」分支，到點 `claude -p -r` 續跑 | 與開著的互動視窗形成雙駕駛（§2.11；X16 已否決同型）；整份冷寫（S2 實證 863,852）；無人窗口牆鐘上限（§2.12） |
| X29 | harness 原生 `autoContinueAtUsageLimit`／`ScheduleWakeup` 當自願停工解 | 射程不涵蓋自願停工（Q1）；`ScheduleWakeup` 無憑證且上限 1 小時（Q2） |
| X30 | 禁止自願停工、硬撞 100% 交給 harness 續接 | 撞線時刻不可控、寬限只夠收尾（半套工作）、連續自動續接三次後 harness 停下問人、大上下文仍在舊 session 冷續 |
| X31 | 只補 `check_pending_handoff` 的「你」字詞表 | 該守衛判「把決定留給人」；「自己停工、等人說繼續」不是決定，是第五類停——補詞表是打地鼠；詞表只作順手修（D8） |
| X32 | Stop 判準吃 `Decision.band`／`per_axis[].band` | 它們是攤提與配速床墊高後的水位：原始 23% 的五小時軸 band＝prepare（§2.17.0 證據 3）⇒ 每回合推回；判準必須讀 `Axis.pct` 原值（D2） |
| X33 | 以語意詞表／`TodoWrite` 狀態／工作樹髒否猜「有未完成工作」 | 無可靠機械來源（模型未必用 TodoWrite；乾淨工作樹不代表做完）⇒ 預設視為有，唯一豁免＝`park --done --why`（可稽核） |
| X34 | 重用 halt 標記，或把 `HALT_PCT` 降到 85 | 改 halt 語意與 DEF-200-281 自檢；與「週額度用到 100%」（掌舵者 2026-11-07）直接衝突 |
| X35 | 新增 `handoff --spawn --if-idle` 旗標 | 「有人在動」檢查屬於排程 job 本體；加旗標會改 `handoff.spawn` 語意與 `handoff.py` 的 LOC 餘裕 |
| X36 | 一次性排程沿用 planner 的 S4U Principal | S4U 落 session 0，`CREATE_NEW_CONSOLE` 的視窗看不見＝「已 spawn、使用者沒有視窗」（假綠）；改 Interactive，代價見 §2.17.6 |
| X37 | 以下修 R1 取代 park | 不涵蓋「上下文小、等待長」的情況；§2.15.5 下修條件未能判定（§2.17.3） |
| X38 | **W 路**：同 session 起一支會等到 reset 才結束的背景等待者（含心跳檔、兜底 H 排程、`--wait-until`），小上下文短等待時由它叫醒舊 session | ① **無暴露證據**：事故（21.9 萬 token、43 分鐘）本來就走 H，W 沒有任何一件真實暴露；守衛面准入規則＝沒有暴露證據不加碼。② 等待者存活超過 40 分**未驗**：唯一實證過的背景等待是 `ci_wait` 預設 40 分。③ 兜底排程與已醒的舊 session 並存有**雙駕駛風險**（只靠 900 秒對話記錄判活擋，主控靜止超過 900 秒即可能並存）。**再開條件**：M-R3 顯示「小上下文、短等待」的換手成本成為主要浪費（即該類停點的恢復首回合成本顯著高於 H 路的新 session 起步成本）；再開須先驗背景等待存活與雙駕駛判準，並補暴露證據。 |

#### 2.17.6 誠實劃界

- **Windows 互動排程只在使用者已登入時跑**（Interactive 登入類型）；登出或關機時 `StartWhenAvailable` 讓它在下次可用時補跑，補跑晚多久＝M-R1 會看見的量。鎖屏、睡眠後喚醒（`WakeToRun` 需 RTCWAKE）屬可用。要完全無人在場的恢復走既有哨兵／無人窗口 FRESH 路，不在本節射程。`_arm_schtasks(interactive=True)` 無 fallback：使用者未登入互動 session 註冊會直接失敗（符合「不得悄悄退回 S4U」），RDP 斷線情境待真機驗證。
- **macOS**：憑證是 `launchctl print` rc＋descriptor 回讀，**不是**時間值；睡著的 Mac 不被喚醒（`pmset -g custom` 現查、不得寫成常數）；`StartCalendarInterval` 的 `print` 回讀形態在 `engine_resume_job` 內只有合成輸出驗過（真機未驗）。
- **`park --done` 到 reset 前一律有效**：同一窗內若掌舵者又給了新工作，Stop 判準不會再推回；以 `park` 重跑覆蓋標記補救。此洞無法由 M-R4 看見（沒有 block 事件），列入理論洞、無暴露證據（登記不修）。
- **週軸以天計的停工不在 Stop 判準內**（D2②）；需要時以 `park --at <ISO> --why …` 明示（上限 8 天）。
- Stop 判準讀的是快取（`pace_state`，每 TTL 至多補量一次）；快取過期且補量失敗＝不判（`park_verdict_unmeasured`），代價是漏推一次。
- `park_cli._cmd_fire` 以 `--session-id` 明示找舊 session 逐字稿（排程器環境無 `CLAUDE_CODE_SESSION_ID`）；真排程啟動時的 cwd／`CLAUDE_PROJECT_DIR` 差異待真機驗證。
- 成本數字沿用 §2.15 的 n＝2 係數與 N₀ 基線 92,522（量自 sid `680d8411` 的單一事例），用於排序與定門檻，不是額度承諾。
- 真機驗證（TCS §3）：V-PK2 的 ①②⑤ 已於 2026-11-16 由第一次真實停工驗到（sid f2260ce7 於 10:10 `park`、13:03:00 排程開出 sid ff1000ed 接手）；V-PK2 ③④⑥、V-PK3、V-PK4 仍**待真機**，未驗不得寫成已驗。
- **狀態列仍只顯示容量百分比，沒有「現在冷重寫要花多少額度」**（問題總表 B5）：本輪不做。換手的機械判準已不靠人讀狀態列（R1～R3、收斂閘、park 皆由程式判），狀態列加成本欄只改善「掌舵者看得懂為什麼換」；成本估計要用 §2.15 的 n＝2 係數，樣本太少，先印在畫面上會被當成承諾。登記於觀察帳 OBS-SI-417，再開條件＝M-R3 累積 n ≥ 5 後係數可校準。

#### 2.17.7 指標、上線前基線與撤回門檻（觀察期：2 個完整週額度週期＝14 天；評估法＝逐列回放，n 小時不做 A/B；入口 `python tools/probe/waste_census.py --resume-metrics --since-days 14`，判準在 `tools/lib/wastecensus/resume.py`）

「額度停點」＝專案內相鄰兩筆對話記錄間隔 ≥ 30 分鐘，且間隔起點前 15 分鐘內的 `quota_burn.jsonl` 樣本顯示短窗軸（`five_hour`／`session`）`pct ≥ prepare` 且 `resets_at` 在起點之後；取不到樣本者另計 `unmeasured`（不得靜默丟棄）。

| 指標 | 定義 | 改善判定 | 撤回／檢討 |
|---|---|---|---|
| M-R1 reset 後閒置 | 停點的 reset 到同專案下一筆 assistant 記錄的分鐘數 | 中位 ≤ 20 且 P90 ≤ 60 | 上線後兩週不降 ⇒ 檢討排程時刻與 Interactive 登入前提 |
| M-R2 靠人恢復 | 結構判準：停點後 reset 起的**第一筆對話記錄**為真人提示（非 `origin.kind=sdk`／`auto-continuation`）且文字不以機器提示前綴（`按交接包繼續：`、`按磁碟任務書繼續：`）開頭 | 14 天 0 件 | ≥1 ⇒ 逐件看為何沒有憑證（M-R4）。不採「第一筆真人訊息 ≤30 字」判準：對事故事例為偽（行 637 共 443 字、`origin=human`） |
| M-R3 恢復首回合成本 | 該記錄之後第一個 assistant 回合的 `cache_creation_input_tokens` 與 ×5.5e-5 的 pp | H 中位 ≤ 45k；任一件 >100k 即紅 | 任一件 >100k ⇒ 回頭檢查 H 的 spawn 前置；同時是 X38 再開條件的觀察量 |
| M-R4 停工無憑證 | `park_stop_block` 件數 ＋ 回放：停點起點前後 10 分鐘內無 `park_armed`／`park_done` 痕跡者 | 逐週降到 0 | `park --done` 使用率 >50% ⇒ 判準太緊；`park_stop_block` 逃生口使用率 >50% ⇒ 同 |

**上線前基線**（主控 2026-11-16 親跑 `python tools/probe/waste_census.py --resume-metrics --since-days 14`；事故 sid `798a7bf1` 含在內）：額度停點 6 個、`unmeasured` 55；M-R1 n=3，中位 274.9 分鐘、P90 294.4 分鐘；M-R2 1 件；M-R3 589,565 token（約 32.4pp，係數 5.5e-5）；M-R4 `park_stop_block` 0 件、無憑證停點 6 個（park 上線前自然全無憑證）。n 小，只作方向，不作統計宣稱。

撤回條件：`OTHER_DRIVER_STOP` 或「有人在動卻 spawn」≥1 件 ⇒ 停用 H 排程路、回頭檢查 `live_driver` 判準與錨；`handoff_spawn_skipped` 的 `live_driver` 比例異常高（>30%）⇒ 檢討排程時刻。收斂判準：連續 2 個週額度週期 M-R1 與 M-R3 不回升。

#### 2.17.8 與既有章節的關係

- §2.11（雙駕駛）：D6 沿用 `live_driver`；D7 補哨兵在 park 窗內讓路；park 不新增 spawn 駕駛以外的駕駛。
- §2.13（sessionctl）：交接包、`handoff.spawn` 的前置與 SEC-6／SEC-7 全數沿用；冷叫醒閘（DEF-200-588）互斥由 D2⑤ 與 finalize 後 TaskStop 保證。
- §2.14：Stop 推回與既有兩支各至多一次、同吃 `stop_hook_active`，最壞多兩三個回合、不死鎖；收斂閘先判（`_converge_stop(...) or _park_stop(...)`）。
- §2.15：**本節即 §2.15.5 第二期「牆前預先交接＋reset 時一次性 `handoff --spawn`」的落地**（V-S1 的「schtasks 開互動視窗」＝TCS V-PK2）；保溫（`keepwarm_verdict`）與 R1 下修仍屬第二期、不在本節。D2 的原始讀數判準與 §2.15.3「`draining()` 不吃配速床」同源。
- §2.10／§2.6：halt 標記語意不動；park 標記是另一份檔，哨兵只讀它做讓路判斷。

### 2.18 背景代理監督、封存閘、冷窗轉送與半路停工（R3；2026-11-16～17；已實作，真機驗證待做）

> 設計全文與證據在 R3 輪 ARCH／PLAN（session scratchpad 的 `ARCH.md`、`PLAN.md`；§1 監督、§2 封存／轉送、§7 否決 X39～X46、§8 誠實劃界）。**實作與 ARCH 牴觸處從本節與程式**（PLAN〈P3 裁決〉A-1～A-8、E-CW-1）。數字一律現查：門檻 `python tools/lib/quota_policy.py --print-env-example`、量測 `python tools/probe/waste_census.py --supervision-metrics --since-days 14`。驗收契約＝`docs/03_testing/contracts/TCS-SessionCtl-20261113.md` 的 FR-W／FR-S／FR-F 與 AT-W／AT-S／AT-F 各列。

#### 2.18.0 立案與暴露證據（守衛面准入：三取一皆成立；`tools/lib/sessionctl/**`、`.claude/hooks/**` 皆在守衛面清單內）

- **掌舵者真機回報**：2026-11-16 20:15 sid `70f1bbb5-bed3-40a6-a826-8f3b0988d55d` 首則真人提示（背景子代理沒人掌控、換 session 接續漏事）；2026-11-17 08:22 sid `16496139-2bf1-43a1-bb3d-5b6650fa8273` 的「請繼續完成任務! 應該又浪費Token了, 請改善這個問題!」（E-MID-1）。
- **非構造性逐字稿**（R3 普查，21 天）：背景子代理在飛而主控結束回合、沒人看管的區間 655 筆／169.0 小時（M-W1）；≥60 分閒置後被背景通知或交卷叫醒的冷重寫 22 次／約 691 萬 token（M-W2）；冷舊視窗被真人提示整份重寫 15 次／約 485 萬 token（M-F1）；ff1000ed 形態——上下文 266,687、包停在機械層、未達硬門檻而無人推回（封存空窗）。
- **本輪自撞（dogfooding，皆非構造）**：E-ARCH-1（子代理的工具呼叫吃掉主控的換 session 提醒）、E-HD-1（2026-11-16 20:45 舊視窗真機：包被 ack 後 Stop 仍被推回叫它重 build）、E-CW-1（2026-11-17 09:10：只寫完主控層、未封存即被冷叫醒閘推回）、E-TR-1／REV S1（測試寫真實痕跡檔與 `%TEMP%\AUTOSDD_ATTENTION.md`）。

#### 2.18.1 決策

- **D1 監督（`watch.py`、`supervise.py`）**：派出背景子代理的同一回合，主控掛 `python tools/sessionctl.py watch`（`run_in_background`、輸出導檔）——它是 harness 追蹤的背景 shell，結束即以 task-notification 叫醒主控，是文件有依據的「主控閒置時叫醒它」載具（本節否決所有外部行程叫醒方案）。輪詢純讀檔、零 token；第一個成立的事件即印判決與處置表對應列、末行 `WATCH_VERDICT=<事件>` 並以表定 rc 結束。事件先後＝quota ＞ budget ＞ stall ＞ overrun ＞ all_done ＞ keepwarm。門檻三鍵（stall 下限、單支牆鐘、單支上下文只准下修）在 `quota_policy_env.ENV_SPEC`／`switch.py`；**keepwarm 原為常數、不開 env**（🔴 v2.1.22 起保溫點＝主控最後一筆帶 usage 的 assistant 記錄＋`AUTOSDD_KEEPWARM_MINUTES`〔出廠 45、只准下修〕，見 §2.19 D3；無人窗口取 harness 背景等待上限減餘裕）。stall 不判「最後一筆為 end_turn」的代理（它在等自己的背景 shell）。quota 重用 `park.prepare_hits`（原始讀數，不吃配速床墊高）。**憑證**：主證＝Stop payload `background_tasks` 內 running 的 `sessionctl.py watch` shell（harness 自己作證「它結束會叫醒我」），副證＝心跳檔新鮮（判卡死）；payload 無該欄的舊 harness 退回 pid＋心跳；例外一律視為有效（fail-open）。**監督閘**（Stop）：有在飛子代理 ∧ 憑證非有效 ⇒ 推回一次並指路 watch（背景 shell／workflow／monitor 不觸發）；有效時改出「看管中」字樣；PreToolUse（Agent／Task）放行時沒有新鮮心跳附一行提醒。`sessionctl status` 多一行「監督」（只能用心跳副證）。
- **D2 封存閘（`seal.py`；取代 `converge._converge_stop`）**：Stop 時無在飛代理 ∧ 主控上下文 ≥ R1（直接量逐字稿，不依賴 `.advised` 閂鎖；🔴 v2.1.22 起門檻改硬線 HARD、R1 退役，見 §2.19 D1）∧ 尚未交棒 ∧ 封存無效 ⇒ 推回一次，要求寫主控層後 `handoff --finalize`。**`--finalize` 升級為封存**：主控層驗不過 ⇒ rc≠0、什麼都不寫；通過 ⇒ 重建機械層（主控層原文逐字保留）→ 全部真人提示全文寫 `<包 stem>.prompts.md` → 最後才寫 `<包 stem>.sealed`。**封存效期（裁決 A-1）**：封存有效 ⇔ 封存戳之後主逐字稿沒有「工作」（主控非唯讀 tool_use；唯讀集合 Read／Grep／Glob，判準 `transcript_activity.worked_since`），否則 ≥R1 的熱快取短追問會每回合被推回。**已交棒判準（E-HD-1；`seal.handed_over`，單一家）**：最新包已寫完 ∧〔已 ack ∨ 痕跡有該包的 `session_switch_spawned`〕——包一被 ack 就變 `acked`，舊判準只認 `live` 會讓已交棒的 session 被當成沒交棒；封存閘對已交棒放行，PreToolUse 收斂閘對已交棒 session 仍擋派工但訊息改為「已交棒，請到新視窗」。**冷叫醒閘前提（E-CW-1；`seal.wake_package`）**：已交棒，或「`.sealed` 存在且包仍 live」；只寫完主控層不算——代理仍在飛時先備好包、等交卷親驗才封存是合理路徑，不該被叫去砍代理。Stop 兩組以「有無在飛子代理」互斥：有 ⇒ 冷叫醒閘優先、其次監督閘；無 ⇒ 冷叫醒閘優先，否則封存閘與 park 合併成一則（先封存再 park；v2.1.22 起再加保溫閘，次序 封存→park→保溫，見 §2.19 D3）。
- **D3 轉送（`forward.py`；hook 只有 `UserPromptSubmit` 分支，零判準）**：路徑一（冷窗轉送）——最新包 live、已封存、尚未 spawn，且本 session 快取已冷（`cachestate`）∧ 提示可轉送（`transcript_activity.is_forwardable_prompt`；機器注入前綴永不擋、`<pasted_content` 長貼可轉；裁決 A-6 把「交接包收錄用 `is_machine_prompt`」與「轉送用 `is_forwardable_prompt`」拆開，後者判不出來不轉）∧ 非 `留：` 前綴 ∧ 沒有 `session_crons`（Stop 時記錄；讀不到＝當作有 ⇒ 不轉送）∧ Windows ∧ 模式 auto ∧ spawn 前置 OK ⇒ 補寫 sidecar（裁決 A-2，封存後才打的真人提示不漏）→ 原文逐字落檔 → `handoff.spawn(extra_prompt_file=, wait_seconds=)` → `decision:block` 擋下舊窗該則並說明；spawn 失敗、行程未見、落檔失敗一律放行、原文檔保留。路徑二（已交棒告知，M-F3 改判）——包已 spawn／ack 的舊窗收到真人提示 ⇒ 新視窗活著且 auto 時擋下並說「本視窗已交棒」、存原文；否則放行並附一行現況。**不上鎖**：`留：` 前綴永遠放行。**熱快取不轉送**（留原地較便宜）。成本條件由「已封存」蘊含（封存門檻 R1 遠大於新 session 起步成本），不另設門檻。
- **D4 交接包第二版**：封存時重建機械層與 prompts sidecar（全文、不截斷；超過字數上限時保留第一則與最後若干則全文、中段只列索引）；新 session 起步提示指向兩檔；`handoff.spawn` 新增選填 `extra_prompt_file`。
- **D5 半路停工（第六類停；`midwork.py`、`check_pending_handoff.py`）**：最後一則回覆自述「接下來還要做事」（進行式詞表；引號內、緊鄰否定、他人負責、假設句、含合法換手標記者不算）∧ Stop payload 有 `background_tasks` 欄位且沒有任何 running 項 ∧ 狀態佐證（本回合有非唯讀工具，或工作樹髒）⇒ 推回一次，句內給三條出路（現在就做、封存＋spawn／park、AskUserQuestion）。欄位缺席（舊 harness）不判。
- **D6 E-ARCH-1 修**：`handoff.advise_once(agent_id=)` 有值即回空、不寫任何檔；`context_budget_guard` 呼叫點傳 `payload.get("agent_id")`（同行數，SPECIAL_FILES 餘裕 0 故不增行）。
- **D7 量測**：`waste_census --resume-metrics` 的停點判準收痕跡停點（`park_armed`／`park_done`；修「漏算 park 停點」，f2260ce7 重現）；`--supervision-metrics` 新增 M-W1～W4、M-F1～F3、M-S1～S3（`tools/lib/wastecensus/supervision.py`、`supervision_load.py`）。裁決 A-8：`tools/lib/sessionctl/` 不得 import `wastecensus`，痕跡事件名在 sessionctl 各檔自訂具名常數，由測試斷言與 `supervision.py` 的 `EV_*` 相等。裁決 A-3：不為測試開 env 鉤，時鐘、門檻、名冊一律參數注入。

#### 2.18.2 已否決（續 §2.17.5 的 X28～X38；本節 X39～X46，理由全文見 ARCH §7）

| 代號 | 方案 | 理由（摘要） |
|---|---|---|
| X39 | 監督憑證以自寫 pid／心跳檔為主證 | 證明不了「結束會叫醒我」（別的終端手跑也有 pid、心跳）；payload `background_tasks` 是 harness 作證 |
| X40 | 新增 SubagentStart／SubagentStop hook 登記截止時間 | 名冊純讀檔已有 `started_at`；多一組註冊＝多一組 fail-open 盲區與文件鎖 |
| X41 | 以 `ScheduleWakeup`／`CronCreate` 當監督叫醒 | 無憑證、session-only、會觸發 UserPromptSubmit 且與人打字不可分（干擾轉送） |
| X42 | 從最後一則回覆自動抽出主控層 | 收尾回覆無固定結構，抽不出「下一步確切指令」「禁止事項」 |
| X43 | 轉送只注入提醒（additionalContext）不擋 | 冷重寫在模型讀到提醒前已付；省 0 |
| X44 | 官方跨 session 訊息／`notify_when_idle` 做轉送或補問 | 未實測；接收端會開新回合並觸發 UserPromptSubmit、受 hold／refuse 與 dialogExpiry 限制；不能當承重牆，列第二期補強 |
| X45 | 已交棒舊 session 打字一律上鎖 | 原判無暴露證據（TH-1）；**M-F3 人工判讀後改判有暴露證據（2026-11-15 sid e66f716f，交棒後 2.7～7.4 分鐘內舊窗被打 4 句），改為「告知、不上鎖」（D3 路徑二）**；上鎖仍否決（誤擋比多付快取更糟） |
| X46 | 監督閘只出聲不推回 | 現況就是只出聲：出聲後仍有大量無看管點與數百小時；出聲對閒置中的主控無作用 |

保留但改造：`_converge_stop` 刪除（被封存閘取代，非否決）。

#### 2.18.3 誠實劃界

- watch 卡死不結束（TH-2）：主控閒置期間無人發現，只能在下一次 Stop 抓到；迴圈只有讀檔與 sleep、每條路徑都有截止（測試守，並含「迴圈未終止」斷言的 `_Clock.MAX_SLEEPS`）。
- 機器睡眠：keepwarm 在睡眠後失效，醒來那一下是冷的（同 §2.14.5）。關視窗／Ctrl+C／`/clear`／撞額度時子代理與 watch 的命運文件未載；撞額度不經 Stop。
- `background_tasks[].status` 值域只見 `running`；「在陣列裡＝進行中」是假設，缺 status 視為 running。interim 交卷時 `meta.finished` 未實測（V-W4）。
- 轉送依「冷」判，冷熱由逐字稿最後一筆 assistant usage 時刻推定（±30 秒邊際）；ADR P5 `idleCompaction` 可能改變快取狀態（V-W3）。圖片提示不轉送、冷重寫照付；轉送只在 Windows 開窗，macOS／Linux 只注入提醒。
- 跨 session 訊息、排程提示在 UserPromptSubmit 上與人打字不可分：靠機器注入前綴與 `session_crons` 記錄兩道；無標籤純文字的跨 session 訊息會被當成人打的字（TH-6），但仍需「已封存＋冷」才轉送、原文必落檔。實測（REV Q2 真實語料重放 75 逐字稿 1,630 筆）判假者中像真人 0。
- **V-F1 真機目視（2026-11-18）**：
  - 第一步「已交棒告知」＝**PASS**（08:29:59，`claude -r 7f29adfb…` 叫回已交棒舊 session 打一句）：畫面顯示「UserPromptSubmit operation blocked by hook」＋完整理由＋`Original prompt`；轉送檔原文逐字一致（11 字、SHA-256 相符）；痕跡 `forward_handed_over outcome=block`。⇒ **互動畫面會顯示 UserPromptSubmit 的 block 理由**，不必降為 notify。
  - 第二步「冷窗轉送」＝**FAIL → 已修（DEF-200-609）**（09:46:35，封存＋冷的 sid `85bcbec8` 打一句）：快取判冷，但 spawn 前置以「工作樹 3 行未提交」擋下（痕跡 `forward_pass cond=8`）；那 3 行是封存後 03:00 SI 巡邏自動寫入的帳本，巡邏每天寫 ⇒ 轉送實務上永遠開不了窗。且條件 8 的原因只進模型 context，畫面空白。修法：spawn 前置排除 SI 自有寫入面（SSOT＝`selfimproving.sched.OWN_PREFIXES`，混有非 SI 檔、改名出自有面、引號化路徑一律照舊拒絕）；條件 7／8 放行另帶 `systemMessage`。修後第二步待重測。
  - Stop 的 `systemMessage`／block 理由（V-W2）仍待目視。
- **理論洞 REV F10 不修**：`handoff --spawn` 與 `park_cli` 只做純驗證、不要求 `.sealed`；漏跑 `--finalize` 而直接 spawn／park 時，冷叫醒閘失明、I-4 封存被跳過。WHY 不修：**無暴露證據**（SOP 兩條路都先 `--finalize`；E-CW-1 只在偏離 SOP 時露出），依守衛面准入「量、不挖」登記證據檔〈理論洞清單〉、不同輪修；再開條件＝真實語料出現一例。其餘理論洞（TH-3 workflow／monitor 型監督、TH-4 環境變數差異入包、TH-5 scratchpad 被清、TH-6 無標籤跨 session 訊息、REV F4～F9／F11、auto-continuation 被標成掌舵者原文、P6H F5 watch 監督憑證以命令列子字串比對 sid，遇帶引號或含空白的路徑寫法可能落空）同登記、同理由。
- 名冊認 TaskStop（DEF-200-606）只讀擁有者主逐字稿尾端 256 KB：killed 通知若早於該窗，代理在名冊上仍顯示為「殘局（未收尾記錄，非燒額度中）」，要等 10 分安靜門檻才不擋 `park`／`--spawn`；2026-11-18 `sessionctl status` 實見 `a51fe52e56c8ed299` 一例（只影響顯示，不燒額度），無阻斷暴露 ⇒ 登記不修。
- 測試寫真實家目錄／暫存（E-TR-1、REV S1）已逐檔圍住；同族新測試須圍 `AUTOSDD_TRACE_DIR` 與 `tempfile.tempdir`；會寫額度快取（`quota_meter.write_cache`）或以子行程量額度的測試另須接模組級圍籬並預種讀數，不得讓子行程以真憑證量真額度（DEF-200-607；`test_run_root_unittests.py::TestWriterModulesDeclareTheModuleFence` 機械守寫端清單）。
- 成本數字沿用 §2.15 的 n＝2 係數與起步底盤中位，只作排序與定門檻，不是額度承諾。

#### 2.18.4 指標、基線與撤回門檻（觀察期 14 天＝2 個週額度週期；入口 `python tools/probe/waste_census.py --supervision-metrics --since-days 14`，判準在 `tools/lib/wastecensus/supervision.py`；基線量於 2026-11-17、21 天窗，只作方向）

| 指標 | 基線 | 目標 | 撤回／檢討 |
|---|---|---|---|
| M-W1 無看管 | 655 筆／169.0 時 | ≤1 時／14 天 | — |
| M-W2 背景叫醒冷重寫 | 22 次／約 691 萬 token | ≤2 次 | watch 有效期間仍發生 ⇒ 查 V-W3 |
| M-W3 監督推回率 | 新 | 逐週降 | >50% 派工波 ⇒ 改提醒字樣 |
| M-W4 誤醒 | 新 | — | >50% ⇒ 調 stall／overrun 門檻 |
| M-F1 冷真人重寫 | 15 次／約 485 萬 token | ≤2 次 | — |
| M-F2 轉送失敗／`留：` 使用 | 新 | 失敗 <10% | `留：` >30% ⇒ 降 notify |
| M-F3 交棒後舊窗真人提示 | 9 次 spawn 中 1 個 sid 命中 4 件 | 轉為告知後歸零 | 仍出現 ⇒ 檢討告知字樣 |
| M-S1 無封存包的回合結束（上下文 ≥ R1 的回合結束點） | 4／21 | 0 | 推回後仍未封存 >30% ⇒ 檢討 |
| M-S2 手貼接續（互動 session 以手貼提示接續） | 12／28 | ≤10% | — |
| M-S3 包過時（機械層落後 session 末筆的分鐘數） | P50 44.2 分、最大 442.4 分 | ≤5 分 | — |
| 硬撤回 | — | — | 任一「轉送吞掉自動回合結果」或「同工作樹雙駕駛」⇒ 轉送預設降 notify、回本 ADR |

#### 2.18.5 與既有章節的關係

- §2.13：本節 D1（監督）、D3（轉送）為同一份交接包與 `handoff.spawn` 的延伸；`advise_once` 加 `agent_id` 守衛見 §2.13.13 補註。
- §2.14：決策 6（回合結束推回）已由本節 D2 取代；決策 2 收斂閘（PreToolUse）保留，對已交棒 session 的訊息改寫；冷叫醒閘（§2.14.5）前提由 E-CW-1 收緊為「已封存／已交棒」。決策 4（等待自帶截止且短於主控快取壽命）套到子代理即 D1 的 keepwarm。
- §2.15：D4「背景任務不保溫」之外，在飛代理期間的保溫見本節 D1；不做「等人時保溫」（仍屬第二期）。
- §2.17：park 判準不動；Stop 上封存閘與 park 同時成立時合併成一則（先封存再 park）。

#### 2.18.6 實作補註：DEF-200-611（2026-11-18；暴露證據＝sid `85bcbec8` 第 1244 行 `compact_boundary` 與 `autosdd_session_switch.jsonl` 09:46:35 `forward_pass cond 8`）

- **D-1 快取冷熱看得到壓縮**：壓縮請求本身重寫快取，閒置壓縮後逐字稿最後一筆 assistant usage 已是壓縮前。`cachestate.cache_state` 現在認 `system/compact_boundary`：其時刻晚於最後一筆 assistant ⇒ 計時起點改為壓縮時刻（回傳多一鍵 `compacted: true`）；`roster._scan` 於壓縮後尚無新 usage 時 `ctx_tokens=0`（記錄只帶 `preTokens`、無壓縮後值，拿不到視為小）。消費端（`forward` 條件 5／上下文顯示、`converge`／`seal` 的 R1 判準、`resume_gate`）全經這兩處，語意一致；壓縮後出現新 assistant 則以新值為準。
- **D-2a 視窗標示**：交棒開出的新視窗命令列含舊 sid。`status` 以痕跡 `session_switch_spawned` 的 `pid`（＋行程建立時刻與 spawn 時刻差 ≤ 60 秒，擋 pid 重用）辨識，字樣改「交棒開出的新視窗：pid X（來源 sid8）」。**D-2b**：`handoff --spawn` 成功與 `--ack` 成功輸出加「舊視窗可以關閉」提醒；刻意不自動關窗（命令列辨識會命中新視窗）。
- **D-3 殘局壽命**：`roster.RESIDUE_MAX_AGE_SECONDS`＝24 小時；最後記錄超過它的殘局預設 `status` 不列，`status --all` 才列。
- **D-4 結論**：`status` 的「排程」欄只列名稱（`schedule_backend.list_jobs`），NextRunTime 只在 `park --status --verify`／`--verify-schtasks` 才查，屬設計（唯讀、零外呼）；未改。

### 2.19 換 session 改依快取成本：專注不讓快取過期（R216；2026-11-18～19；已實作，真機驗證見 RealVerify 帳本）

> 設計全文＝`docs/02_architecture/SessionSwitch_CostModel_Design.md`（下稱 DES；**§11 開頭的掌舵者裁決段優先於全文**）；驗收契約＝`docs/03_testing/contracts/TCS-SessionSwitch-CostModel-20261118.md`；上游需求＝PRD v2.1 修訂表 v2.1.22 列（§16.5 (i) 修憲）。數字一律現查：`python tools/lib/quota_policy.py --print-env-example`、量測 `python tools/probe/waste_census.py --since-days 14`。

#### 2.19.0 立案與暴露證據

- **掌舵者原話（2026-11-18）**：「請檢討context 25萬就切換Session的合理性, 是否應該專注在不要讓Cache過期! … 是否變成自我閹割功能, 本末倒置!」，再指令三連「專注在不要讓Cache過期!」。
- **非構造性逐字稿**（DES §1.3～§1.4，14 天母體）：快取過期後整份重寫才是浪費主因（子代理 189 件／8,046 萬 token、主控 36 件／1,101 萬 token）；主控閒置約 55 分鐘時 harness 會自動壓縮大上下文（17 次自動壓縮中 9 次發生在閒置 54.6～56.5 分之後、壓縮後只剩 1.2 萬～2.2 萬）；子代理前景等待超過 5 分鐘（77 件長等待重寫）；真機缺陷：`sessionctl watch` 在 prepare 帶一掛就 rc 5（主控 2026-11-18 21:26 實證）。

#### 2.19.1 決策（掌舵者裁決後的落地版；與 DES §4.4 軟線／hold 草案牴觸處從本節）

- **D1 只留硬線，不設軟線、不做 hold**（掌舵者 D-1＝③、D-2）：換 session 的上下文線只剩 `AUTOSDD_SWITCH_HARD_CTX_TOKENS`（出廠值現查；低於觀測到的流程內 autocompact 最小點 881,938，只准下修）。到線 ⇒ PreToolUse 擋 `Agent`／`Task`／`Workflow`、Stop 封存閘推回、PostToolUse 出聲；**不再要求「已出聲」**（舊收斂閘的前置）。25 萬固定換手（原 R1）與「上次續跑寫入 ≥10 萬 ⇒ FRESH」（原 R3）**退役**：`AUTOSDD_SWITCH_R1_CTX_TOKENS`／`..._R3_CACHE_CREATION_TOKENS` 出廠值移除，有設值只出聲「已退役」、不生效、不拋（舊 `.env` 不壞）。R2（壓縮 ≥2 次 ⇒ 續跑改 FRESH）保留——它是品質訊號。
- **D2 F4 成本選路（取代 R1／R3，只在快取已冷後判）**：`costmodel.fresh_is_cheaper`＝`W_CC1·c > F·(1+q)`（`W_CC1`＝2.0；F、q 出廠值現查 `AUTOSDD_SWITCH_FRESH_COST_UNITS`／`AUTOSDD_SWITCH_CONTEXT_VALUE_Q`；`q`＝失去上下文的品質損失係數、治理決定）。快取仍熱 ⇒ 不判（讀價必小於 F）；量不到 ⇒ 當熱（FRESH 的代價是丟上下文）。消費端：無人續跑選路 `switch.fresh_reasons`、UserPromptSubmit 冷窗轉送（`forward.py` 條件 10：冷但續跑較便宜 ⇒ 留原視窗並顯示原因）。`handoff.advise_once` 的出聲判準走硬線（`fresh_reasons(advise=True)`），與快取冷熱無關。
- **D3 主控保溫 `sessionctl keepwarm`（`keepwarm.py`）**：截止＝主控**最後一筆帶 usage 的 assistant 記錄**＋`T_kw`（`AUTOSDD_KEEPWARM_MINUTES`，出廠 45、只准下修、下限 15；不是任何程序的啟動時刻）；末行 `KEEPWARM_VERDICT=ping|cap|skip`（rc 6／7／0）。保溫帳 `trace_dir()/keepwarm/<sid>.json` 記 `pings`，真人提示一出現歸零；上限 `n*` 依 F1（ski-rental，約 9～10 次）。不掛的情形：無人窗口、模式非 auto、`AUTOSDD_KEEPWARM_OFF`、已交棒、park 標記有效、上下文低於 `AUTOSDD_KEEPWARM_MIN_CTX_TOKENS`。**Stop 保溫閘**（`converge` 合成，次序 封存→park→保溫）：無任何 running 背景任務 ∧ 非不掛情形 ∧ `pings < n*` ⇒ 推回一次。**冷叫醒閘**：已交棒照舊全停；只封存、在等掌舵者 ⇒ `sessionctl.py keepwarm` shell 豁免（`seal.handed_over` 判）。`watch` 的保溫點改用同一錨點函式。
- **D4 watch 額度閂鎖**：quota 事件以 `(sid, reset 分鐘, 帶級)` 為鍵寫 `trace_dir()/watch/<sid>.quota.json`，同窗同帶只觸發一次；帶升級（prepare→halt）或 reset 改變再觸發；閂鎖讀寫失敗一律觸發＋stderr 出聲（失效往保守）。reset 時刻抖動（讀數在分鐘邊界來回 ±1 分）由 `keepwarm._same_reset` 吸收：字面相同或差 ≤300 秒視為同窗（DEF-200-614）。否決 `--ack-quota`（DES §4.3）。
- **D5 子代理長等待 `runlong`／`waitfor`＋長前景閘（`longwait.py`）**：子代理快取壽命 5 分鐘。`runlong --out <檔> -- <argv…>` 背景跑、結束原子寫 `<檔>.done`；`waitfor --done <檔>.done --max-sec S` 前景至多等 S 秒（預設 240，**上限 255**）：完成 rc 0＋尾端 40 行＋`WAITFOR_VERDICT=done rc=<子行程 rc>`、未完成 rc 3 `pending`、參數錯 rc 2。**上限取 255 而非 270 的 WHY**：waitfor 自己是前景呼叫，等 270 秒需要 timeout > 270000，會被長前景閘自己擋住。**長前景閘**（PreToolUse，`.claude/hooks/sessionctl_guard.py`；`.claude/settings.json` matcher 含 PowerShell／Bash）：呼叫帶 `agent_id`（子代理；主控 1 小時快取不判）∧ 工具 PowerShell／Bash ∧ 非背景 ∧ `timeout > 270000` ⇒ rc 2 指路 runlong／waitfor；行內 `# keepwarm-ok: <WHY>` 豁免（`AUTOSDD_UNATTENDED` 下無效）；解析不到一律放行。依據：工具預設 timeout 120 秒，要等超過 5 分鐘必須顯式設大 timeout，判準精確。
- **D6 park 到點選路（階段 3，R216 WP-F；已實作）**：park job 到點（`park --fire`，查過沒人在動之後）不再一律 spawn 新 session——`park.fire_route(held, cold)` 與 D2 同一條判準：上下文量不到 ⇒ FRESH（`claude -r` 需要讀得到逐字稿，沿用已封存交接包這條既有路）；快取仍熱 ⇒ RESUME；快取已冷 ⇒ `costmodel.fresh_is_cheaper` 命中 FRESH、否則 RESUME。RESUME＝`park_cli.spawn_resume`：另開互動視窗 `claude -r <原 sid> <提示>`（提示帶交接包路徑供參考＋`FRESH_HARD_RULES`），成功憑證＝行程活著**且**原逐字稿變大（或專案目錄出現新檔），否則照實非零；**失敗不自動退回 spawn**（行程可能已起，雙開＝同一棵工作樹雙駕駛），標記 failed＋handback 寫明走的是哪條路。痕跡：`park_route`（route／why／ctx）、`park_resumed`／`park_resume_failed`、`session_resume_spawned`；FRESH 路沿用 `park_spawned`／`park_spawn_failed`。哨兵讓路（`park.yields`）不分路線；RESUME 不 disarm 哨兵（同一個 session 繼續）。- **D7 同一個 session 自己續跑不算交棒（R216 QA 退件 P2-1，DEF-200-617）**：交接包語意＝「這個 session 交給別人」。舊判準只看 `.ack` 存在，原主人經 park RESUME（`spawn_resume`）、`claude -r` 或自己 `--ack` 回來後 `seal.handed_over` 恆真 ⇒ keepwarm 判 `handed_over` 失效（直接違背本節主軸）、冷叫醒閘對在飛代理／背景 shell 誤推 TaskStop、封存閘失效、每則提示被注入「已交棒」。成因＝**沒記下「接手者是誰」**，所以修在資料與單一判準家，不在各消費者各打補丁：①`handoff.ack` 在 `.ack` 記下接手者 sid（`acked <時刻> sid=<sid>`，取自 `CLAUDE_CODE_SESSION_ID`）；接手者＝包的原主人 ⇒ 不寫 `.ack`，改 `seal.mark_resumed`：寫 `<包 stem>.resumed`（包狀態 `resumed`，不再被公告、不是 `live`）、刪 `.sealed`（封存是對「當時」的交代，續跑後失效；上下文再長到硬線會由封存閘推去重封存，`seal()` 寫戳時清 `.resumed`）、只清**自己 sid** 的 `.ack`（別的 sid 與舊格式〔無 sid〕的 `.ack` 一律保留；**舊格式不自動遷移**——見本條末〈舊格式取捨〉）。②`spawn_resume` 憑證成立後同樣呼叫 `mark_resumed`。③`handed_over` 改為「別的 sid 的 ack ∨ 該包的 spawn 痕跡」（舊格式無 sid 的 `.ack` 無從分辨 ⇒ 保守視為別人接手）；`wake_package`（冷叫醒閘）、keepwarm 的 skip、收斂閘訊息、forward 附註全經它，故消費端零改動。④`announce` 對自己的包改提示「你是原主人在續跑，直接續做、不要當成別人的包去接手」（hook 傳 payload `session_id`；缺則讀環境變數）。⑤原則：spawn 痕跡仍是真交棒（新視窗真的開過），不因續跑標記消失。真機證據＝RealVerify `RV-C4`（甲：同 sid 自續跑 ⇒ 冷叫醒閘不推、keepwarm 照 ping；乙＝對照：別的 sid ack ⇒ 照推、keepwarm skip）。**舊格式取捨（R216 複審 P3-a）**：舊格式 `.ack`（e7645e25 以前寫的，沒記 sid）無從分辨是誰寫的。`mark_resumed` 與 `handed_over` 必須對同一種 ack 給同一個答案——兩處判準一致＝保留並保守視為別人接手；否則「先被別的 session 舊格式 ack、原主人再自續跑」會刪掉真交棒的證據而被判未交棒＝雙駕駛。為何不自動遷移：①舊格式是**封閉集合**（新 ack 一律帶 sid，不會再產生）；②本機 19 份舊格式 `.ack` 皆為早已完成的真交棒（交接包原主人是舊 session，接手者另開視窗），唯一的自 ack 案例（sid 31ea79d4）已由「原主人 `--ack`」轉成 `.resumed`；③沒有可靠的機器判別依據（`.ack` 檔頭時間 vs `.sealed` 都擋不住「別人先 ack」）。代價＝極罕見的「舊格式 ack 的包，其原主人要接回」不會自動接回；處置＝原主人 `handoff --ack` 時印出舊 `.ack` 路徑與「確認沒有別的視窗在動同一棵工作樹後手動刪除」，由人在確認後做，不靠猜。回歸＝`test_sessionctl_seal.py::SelfResumeTest::test_mark_resumed_clears_only_the_owners_own_ack`（含 `handed_over` 一致性斷言）、`test_sessionctl_handoff.py::…test_owner_ack_over_a_legacy_ack_keeps_it_and_says_so`、`test_sessionctl_keepwarm.py::…self_resumed…`。

#### 2.19.2 對 §2.13／§2.14／§2.18 的修正（就地註記指向本節）

§2.13.2 D2 判準表的 R1／R3 列、§2.14.2 決策 2（收斂閘的「已出聲」前置與「290,000／須大於 R1」）、決策 6 與 §2.18.1 D2／§2.18.5 的「達 R1」、§2.17.3／§2.15.5 的 R1 下修討論，一律已被 D1／D2 取代；各處就地加註「v2.1.22 起見 §2.19」，原決策文字保留作史料。

#### 2.19.3 誠實劃界

- 保溫（D3）與長等待分段（D5）的真機效果（`-p` 模式快取層是否 1 小時、互動主控閒置 3 小時回來 `cache_read ≥ 0.9×`）仍待 V-SS1～V-SS4 與 E2E-SS-04／08；RealVerify 帳本已入帳者以帳本為準，未入帳＝未結。
- 閒置約 55 分自動壓縮為 harness 行為，保溫 45 分截止擋在它前面，但機器睡眠時失效（醒來那一下是冷的，同 §2.14.5）。
- 保溫回合會消耗 token，但不是遙測、也不探測額度（PRD §1.2 原則 2 的就地註記）；成本以 `waste_census --switch-metrics` 的 M-K5 入帳。
- F、q、`P_FIX` 為量測／治理值，不當常數。**量測端（R216 WP-G）已實作**：`python tools/probe/waste_census.py --switch-metrics`（M-K1～M-K6）、`--replay-switch`（重現 DES §7 全表：P1 保溫／P3 F4 選路／P4b 軟線掃描〔史料〕／S1 冷續棒／S2 分段等待）、`--calibrate-switch`（F、B、N_lo、P_fix 建議值＋`autosdd_resume_cost.jsonl` 驗 F4 前提）；判準在 `tools/lib/wastecensus/sections_keep.py`、I/O 在 `keep_load.py`，母體可存快照 JSON（`--dump-population`／`--population`，CI 無真逐字稿時用）。當日對帳：M-K1 21 件／7,362,729 tok、M-K2 9 次、M-K3 77 件／31,263,469 tok、M-K4 146 件／70,155,830 tok、P1 14,725,458→7,069,932（保溫 86 次）、S2 39,079,336→6,017,201，皆與 DES §7 逐位相符；P3／P4b／S1 差異＝母體多一支交接包開場 session（F 中位 480,734→467,949，n 23→24）與 `annotate.units` 對「分層未標」寫入記 1.25 而 DES 腳本記 2.0（F_a 差 6 單位），已逐項核過。M-K5 的 P_fix 目前只有 waitfor／少量 keepwarm 回合的實測，keepwarm 痕跡 0 筆＝尚無資料（不是好消息）。
- 🔴 **仍未結（不得宣稱已驗）**：E2E-SS-05（上線 14 天後 M-K2＝0；`--switch-metrics` 已能量，等時間）；park RESUME 路「到點真的開出 `claude -r` 互動視窗並續寫原逐字稿」（受 folder trust 限制且禁開窗；選路、痕跡、失敗 handback 已由真排程＋真行程驗，RealVerify RV-PR1／PR2，開窗那一步待掌舵者目視 V-SS5）。
- 立案缺陷：DEF-200-613（watch 額度條件一掛上即觸發）、DEF-200-614（reset 抖動閂鎖）、DEF-200-615（監督憑證字面子字串比對落空；§2.18.3 的 P6H F5 理論洞由此轉實例並已修）、DEF-200-612（缺真機自驗載具）、DEF-200-617（自續跑被判已交棒，D7）、DEF-200-618（reset 抖動邊界無測試釘住）；座標見缺陷帳本。

## 3. 被否決的方案（各記為何否決）

| 方案 | 出處 | 否決理由 |
| --- | --- | --- |
| **`ScheduleWakeup` 鏈式接力 6 棒** | 原始需求的預設想法 | ① 主 session 醒一次約 20.7 萬 token（成本正比於自己的 context，且會隨 session 長大），6 棒 ≈ 124 萬；外部探針是**常數 31,847**（本輪實測）。② 醒來那一棒本身就是一次模型請求，額度斷電期間它自己也會被擋，而 runtime 的 keepalive 補救常數實查為 **1** ⇒ **結構上撐不過一次完整的 5 小時斷電**。③ **它沒有任何憑證**，事後無從得知排到了沒有。④ schtasks 沒有 1 小時上限 ⇒ 「接力」整個是 `delaySeconds` 上限外溢出來的**假需求** |
| **session 內 `run_in_background` 守望行程** | Architect | 仍然要求終端開著（與接力同一個死穴）；`run_in_background` 是否受 600000ms 上限砍掉**未驗**，而被砍時很可能是靜默的＝看起來像「排了但沒觸發」，正是 R59 那個事故的形狀；且行程 exit 後的回訪仍需要一個模型回合，那個回合可能自己被額度擋下 |
| **新增 `tools/endurance/` 三支檔** | SA | 本 repo 最大缺陷來源是護欄層自我增殖；`test_check_wrapper_thinness.py` 明載往 `tools/` 新增 `*.py` 會同時污染 ruff／LOC 棘輪／`_script_scan_surface`。全部功能塞得進既有兩支檔，且塞的位置有結構理由（見 §4） |
| **`.claude/loop.md` 接力棒** | SD | 接力已否決 ⇒ 它沒有消費者。且它是掌舵者日常 `/loop` 讀的**同一個檔**，寫進去會污染日常行為；25,000 bytes 上限還是**靜默截斷** |
| **長壽 canary session 壓低探針成本** | SA | 美元便宜（$0.0176 → $0.0036，本輪兩支探針實測）但多一個長期存活的移動零件。token 成本兩者相同（~32K），而預算上界是用 token 算的 ⇒ 收益不值那個複雜度。**記為已知可選優化** |
| **任務書改落 `%LOCALAPPDATA%`** | Architect／SD 皆提 | `%TEMP%` 被清掉確實是靜默的單點失效，但搬家會動到 `guard.PLAN_PREFIX`／`write_resume_plan()`／既有測試。**真正的修法不是搬家而是讓失效變大聲**：註冊時把「任務書不存在就中止」寫進 Action 自己（任務書不存在時，沒有人讀得到寫在它裡面的規則）。搬家列為候選 |

---

## 4. 為何住在這兩支檔（職責歸屬）

- **不放 `AutoClaude/autoclaude/`**：那是會出貨的套件，受 8 條 import-linter contract 與 LOC 分級管。
  續航要摸的是 harness 內臟（`~/.claude/projects/**/*.jsonl`、`claude -p -r`、schtasks），
  放進去等於「被驅動的引擎反過來依賴驅動它的 harness」，方向倒轉。
- **純判讀放 `context_budget_guard.py`**：逐字稿掃描的實作已經在那裡（`scan_transcript`），
  而 planner 已經 import 它。反過來寫會讓「怎麼掃逐字稿」有兩個家。
  該 hook 由 `runpy.run_path` 起、`sys.path` 不含 `tools/` ⇒ 它**只能被 import，不能 import**，
  既有依賴方向 `tools/ → .claude/hooks/` 只能維持。
- **CLI／編排放 `session_resume_planner.py`**：`run_powershell()`（顯式外呼 5.1）、
  `schtasks_script()`、`next_run_time()` 取證閘都已在那裡。續航是「這個 session 快不能工作了怎麼辦」
  的**另一半**（context 爆掉 vs 額度用完），拆新檔就是製造第二個家。
- **`.claude/` 只提供事件，不承載邏輯**（這一條沒變，SessionStart 條目也只是叫回 planner）。
  🔴 **下一句已被 §2.6 取代，別照它推論**：本列原本斷言本協定完全不動 `.claude/settings.json`。
  R79 補洞包新增了一個 SessionStart 條目——理由不是「額度變成 context 了」（兩者仍是兩件事、
  門檻仍各自獨立），而是**接電點只能長在 hook 註冊面上**：那是全 repo 唯一「session 一開就會
  自動跑」的地方，而沒有接電的協定本輪已實證等於沒有。原句與其論證保留在下方以存脈絡：
  **本協定**（R79 補洞包之前）不新增任何 `.claude/settings.json` 條目——
  額度不是 context，把額度掛上那支守衛會讓它變成「一個東西假裝能做兩件事」。
  > 🔴 **R79 四方複審訂正射程**：本列原本寫「**本輪**不動 `.claude/settings.json`」，而同一個工作樹裡
  > 該檔實測 **+11／−0 行**——那是**同輪 context 水位包**新增的 PreToolUse 條目
  > （matcher `Task|WebFetch|WebSearch`，掛同一支 `context_budget_guard.py` 的阻斷模式），
  > 屬**另一個決策**（context 水位 ≥90% 擋展開型工具），不是本協定的一部分。
  > 兩者共用腳本、由 payload 的 `hook_event_name` 分派，但立案理由與門檻各自獨立。
  > 「本輪」與「本協定」在多包並行的一輪裡不是同一個範圍，**ADR 只能替自己說話**。
  > （R92 訂正：上段的 context 硬線 90% 已改 **94%**，matcher 亦已含 Agent|Workflow——見 ADR-XPLAT-008。）
  > 現查：`git -C "$r" diff --numstat -- .claude/settings.json`

### 與 AutoClaude Token Guard 的關係：另立一套

判準是「**改一個值，是不是兩邊都得改？**」——不是「看起來像不像」。
門檻階梯（80/90 vs 75/90）歷來各自設定、從沒有人需要同時改；
（R92 訂正：context 側那一組現為 **84/94**，見 ADR-XPLAT-008——本段判準不受影響，R92 那次也只改了一邊。）
`seconds_until_resume()` 吃 ISO 字串、睡在本 repo 的 Python 行程裡，而本協定的輸入是**人類可讀的錯誤字串**、
等待發生在 harness 的行程裡。共用要嘛讓套件依賴 harness 內臟、要嘛讓根治理層被子專案的 LOC/import 契約綁住。
Copy-on-Evolve 管的是**知識（事實）**不是**形狀（模式）**：事實只能有一個家，
「從目標時刻算等待 → 睡 → 從持久化的點續跑」是模式，在兩個 runtime 基質上各自出現不是缺陷。

---

## 5. 實測證據（E1~E8＝R79 當回合真跑；E9~E11＝R80 當回合真跑）

| # | 命題 | 實測 |
| --- | --- | --- |
| E1 | `DEF-101-089`「`CLAUDECODE=1` 巢狀 spawn 必死結」 | **對 `claude -p` 這條 subprocess 路證偽**。繼承 `CLAUDECODE=1` 外呼 `claude -p` → **rc=0、3.36s**（第三次獨立複驗）。<br>🔴 **R79 收輪收窄射程**（原文只寫「證偽」，是全稱的）：同輪另跑了樹上真正在用的**另一條** spawn 路（`wexpect` pty，11 支測試的 skip 判準所依賴的那一條），結論**相反**——`PtyWrapper.start()` 三次都沒回返（180／180／45s）、`claude.exe` 從未被啟動，且**剝除 `CLAUDECODE` 的對照組行為完全相同**。⇒ 證偽**不遞移**：`CLAUDECODE` 是巢狀環境的可靠標記、不是成因；本協定只依賴 subprocess 這一路，故 E1 對本協定成立。逐次量測見 `docs/06_quality/CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-913` 節 |
| E2 | `claude -p -r <sid>` 真的接回同一支 session 並帶 context | **成立**。回傳 `session_id` 與傳入**完全相同**；續問「上一則你回了哪個字」答對 `PONG`（rc=0、3.01s） |
| E3 | 探測成本 | 冷探針 **31,847** tokens／$0.0176；`-p -r` 暖續跑 31,922 tokens／**$0.0036**（cache read） |
| E4 | reset 只能觀測 | R79：全庫 7 個相異值，無一落在 5 小時格點。**R80 重量：10 個相異值、15 個 episode 最長等待 4.2 小時、超過 5 小時者 0 個**（§2.7） |
| E9 | **續跑那一跑真的做得了事**（R80） | **修前結構上做不到、修後成立**。修前：Action 的 `WorkingDirectory` 為空字串 ⇒ cwd＝`C:\Windows\System32` ⇒ 那一跑自陳「本 session 允許的工作目錄只有 `C:\WINDOWS\system32`」、連任務書都讀不到。修後同一條路端到端：`woken 02:24:06 → probed rc=0 quota_open=true → resumed rc=0`，那一跑自報 `CWD=D:\CursorProject\AISDCL_Agent` 並成功讀出任務書第 1 行 |
| E10 | **`--add-dir` 是變長參數會吃掉 prompt**（R80） | **實測**。`--add-dir <dir> <prompt>` → rc=1、stdout 全空、逐字 `Error: No deferred tool marker found in the resumed session…Provide a prompt to continue the conversation.`；`<prompt> --add-dir <dir>` → rc=0。**五段稽核痕跡在前者全綠**（woken/probed/resumed 齊備、排程正確收掉），只有那一跑什麼都沒做 |
| E11 | **彈窗的根因是「載具 × 旗標」兩層，不是單一旗標語意**（R80，**含一次自我訂正**） | 第一版結論「`DETACHED_PROCESS` 會抵銷 `CREATE_NO_WINDOW`」**被自己的複量推翻**——那張表只用 venv 的 `python.exe` 當子行程，而本 venv 由 **uv** 建立（`pyvenv.cfg` 有 `uv = 0.8.22`），其 `python.exe` 是 **trampoline**（274,712 B vs 真直譯器 103,192 B），會 re-spawn 真直譯器且**不傳 creationflags**。四載具 × 六旗標完整矩陣（`0`＝無 console）：`base python.exe` 僅 `none`／`NEWGRP` 可見；**`venv python.exe` 的 `DET\|CNW` 與 `DET` 翻成可見**；`base/venv pythonw.exe` **六組全 0**。⇒ ①「抵銷」是**載具效應**不是旗標語意；②`CNW` 與 `NEWGRP\|CNW` 是唯二在四載具全 0 者；③pythonw 單靠載具即足夠。**射程誠實劃界：本重現依賴「venv 由 uv 建立」，`python -m venv` 回退路徑未驗，不得寫成平台常數。** 另實測 `CNW\|NEWGRP` 下子行程**活過父行程退場**（父死 02:02:50、子寫檔 02:02:58）⇒ `DETACHED_PROCESS` 非「脫離父行程」的必要條件 |
| E12 | **哨兵整晚失明的真正成因＝「已處理」是推論不是證據**（R80 P0） | **實證**。2026-08-08 02:00~06:50 真撞線（2 個修復 agent ＋ 9 個 verify agent 全死於 `resets 6:50am`），哨兵 08:37／08:52／09:07 三次巡邏**全判「無未處理撞線」**。三個候選歸因逐一實查：①「主逐字稿沒有那字串」**證偽**（Grep 實證有，且 3 筆為權威 `<synthetic>` 形狀）；②「偵測面缺 subagent」**成立但非主因**（263 支 subagent 中 109 支抓得到）；③**主因**＝`handled_through` 的立案理由「我此刻跑得動武裝指令 ⇒ 額度是通的」**是假話**（武裝是零 API 呼叫的本機 subprocess）。狀態塊實測 `handled_through=2026-08-07T18:38:56Z` 而撞線事件在 `18:36:53Z` ⇒ **撞線後 2 分鐘就被標成已解決** |
| E13 | **新判準的誤判率是量出來的**（R80 D 段） | 同母體（1,513 支逐字稿／257 筆事件）四個判準對拍：現行 A（只掃主檔最後一筆）→ 本次事故回 `quota_spend`，把更早未解決的 `quota_session` 蓋掉；B（擴面、無復原證據）→ 假陽性 **14.8%**；C（擴面＋**同檔**復原證據）→ 假陽性 **81.3%**，**被自己的量測否決**且成因結構性（被打死的 subagent 在自己檔裡永遠不會再有成功回應）；**D（擴面＋全域復原證據）→ 假陽性 0.0%（0/257）**。鑑別力反證：把觀測時點倒推到停機進行中的 `18:40:00Z`，判準 D 當時會抓到 **4 筆** `quota_session`／`resets 6:50am` ⇒ 0% 不是靠「全部判已處理」換來的 |
| E5 | S1/S2 比例 | 151 : 71 |
| E6 | 水位計在撞線當刻讀 0% | **重現並修復**。135 筆合成記錄 usage 三欄全 0；修復後同一支逐字稿 used＝178,616（17.9%） |
| E7 | schtasks 端到端 | 見 §6 |
| E8 | 註冊當前使用者的工作不需提權 | 成立（本輪四次註冊全部在非提權 session 完成） |

---

## 6. 取證規則（本 ADR 對 CLAUDE.md〈反事後諸葛〉的補充）

**憑證是 `NextRunTime` 這個「值」，不是指令的 rc**——`Get-ScheduledTask` 對不存在的工作回 **rc=0**（非終止錯誤），
只讀 rc 會是假綠。`next_run_time()` 靠空字串把它判紅，`relay_problems()` 則禁止在 `next_run_time` 為空時
把狀態寫成 `armed`／`waiting`。

第二道是**痕跡**：每一次醒來 append 一行 JSONL，且**第一行必須在讀任何東西之前就寫**
（讓「觸發了但早期失敗」與「根本沒觸發」分得開）。
🔴 這一條在本輪端到端實測中自己出過錯：痕跡的鍵原本用 session id，而開場那一行寫得出來時
session id 還躺在沒讀的狀態塊裡 ⇒ 痕跡分裂成兩個檔，早期失敗那一行剛好落在沒人看的那一個。
鍵已改為**任務書路徑**，並由 `test_the_audit_trail_has_exactly_one_home` 釘住。

---

## 7. 已知限制（照實寫，不粉飾）

1. **醒來那一跑的 hook 攔截面未驗**：headless `claude -p` 是否跑本 repo 的 PreToolUse／PostToolUse hook，
   本輪沒有驗。若不跑，最無人看管的那一跑會是全 repo 唯一沒有護欄的地方。
   ——這正是 `--allow-resume` 預設關閉的第二個理由。
2. **`retry-is-probe` 未量測**：「有真工作待跑就直接重試它、失敗成本趨近零」是推論；
   無法構造一次真的額度耗盡來量它，故**沒有**實作，探測一律走 `--probe-quota`。
3. **`%TEMP%` 是地板的單點失效**，且失效是靜默的。已用「Action 自帶存在性檢查」把它變成大聲，
   但沒有搬家。
4. **mac/Linux 無對等物**：`run_powershell()` 在非 Windows 明文 fail-loud。
   L2 要 launchd／cron 才有對等物，本輪**明說做不到**而不是靜默缺席（鐵律三）。
5. **`--allow-resume` 開啟時沒有機械護欄**（見 §2.5）。
6. **探測預算上界 5 × 31,847 ≈ 16 萬 tokens**。`MAX_PROBE_ATTEMPTS = 5` 是挑的、不是量出來的。
7. **醒來後可能二次撞線**：reset 是滾動視窗，醒來只要一動就重新起算。
   故任務書第 3 節的第一條恆為「重驗＋收斂」，不是「繼續展開」。
8. **無人窗口的產出率帳**（§2.12 起登記；2026-10-31 晚補機械物）：每窗的 `resumed.bg_ceiling_kill`、
   handback 四節齊備與否、燒掉的 pp 數原本只能人工從 `autosdd_resume_log_*.jsonl`／`autosdd_resume_cost.jsonl`／
   `autosdd_unattended_outcome.jsonl` 三處對讀；現由 `python tools/probe/unattended_yield.py`（唯讀、零 token、
   不接閘門 rc）把三處依 session 對起來，每個結局印一列並彙總。**要不要接成 `--pace` 的一欄**仍等 §2.12
   修法後累積 ≥5 窗（探針末行自報是否達門檻）再決定（2026-10-31 起算；此前 5 窗 DONE 1）。
9. **無人窗口的主控模型**＝Sonnet（掌舵者 2026-10-31 互動選項裁決「改 Sonnet」；`env.shared`
   `AUTOSDD_MODEL_HELMSMAN=sonnet`，只管無人喚醒窗口，互動視窗主控不受影響）。理由：無人窗口的
   工作面＝重驗、跑全套、派唯讀 QA 鏡、寫 handback，Sonnet 可勝任、單窗固定成本約為 Fable 的五分
   之一；風險有界（守衛硬擋 commit／push、治理檔唯讀）。再開症狀：連續兩窗 handback 四節不齊或
   把任務書誤讀成可 commit——屆時回頭看第 8 項的產出率帳再裁。
