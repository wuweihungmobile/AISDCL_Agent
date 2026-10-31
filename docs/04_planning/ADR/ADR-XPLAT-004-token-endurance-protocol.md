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
8. **無人窗口的產出率沒有機械帳**（§2.12 起登記）：每窗的 `resumed.bg_ceiling_kill`、handback 四節齊備
   與否、燒掉的 pp 數，今天仍只能人工從 `autosdd_resume_log_*.jsonl`／`autosdd_resume_cost.jsonl`／
   `autosdd_unattended_outcome.jsonl` 三處對讀。要不要接成 `--pace` 的一欄，等 §2.12 修法後累積 ≥5 窗
   再決定（2026-10-31 起算；此前 5 窗 DONE 1）。
9. **無人窗口的主控模型**＝Sonnet（掌舵者 2026-10-31 互動選項裁決「改 Sonnet」；`env.shared`
   `AUTOSDD_MODEL_HELMSMAN=sonnet`，只管無人喚醒窗口，互動視窗主控不受影響）。理由：無人窗口的
   工作面＝重驗、跑全套、派唯讀 QA 鏡、寫 handback，Sonnet 可勝任、單窗固定成本約為 Fable 的五分
   之一；風險有界（守衛硬擋 commit／push、治理檔唯讀）。再開症狀：連續兩窗 handback 四節不齊或
   把任務書誤讀成可 commit——屆時回頭看第 8 項的產出率帳再裁。
