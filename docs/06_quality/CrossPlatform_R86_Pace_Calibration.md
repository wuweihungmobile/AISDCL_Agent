# R86 配速最佳化：外部校準基準 ＋ 缺陷 A／B／C 的治法與逐項自證

> **本檔為什麼屬於「具名治理文件」**（＝資格，不是分類）：
> ① 複審者要判「配速演算法現在憑什麼給出那個數字」就得讀完它（⇒ 受體積守門）；
> ② 它逐筆寫出「某個常數／某個判準現居某檔某符號」的宣稱（⇒ 受指針稽核）；
> ③ 它承載 repo 至今**唯一一筆外部獨立校準基準**——那筆基準此前只活在對話裡，而
> R85 教訓 5 逐字判過「做了但不落磁碟＝沒發生」。
> 登記面＝`tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS`（漏登記即 rc=1）。

---

## 一、外部校準基準（掌舵者 2026-08-12 的 CLI 畫面）

訴求 6z 的調研結論是「**查不到任何官方通道**能回答個人訂閱帳號的當前水位＋reset」⇒
本程式的取數正確性在此之前只能自我對帳。掌舵者這次貼出 Claude Code CLI 的真實畫面，
這是第一次有一個**獨立於本程式**的基準可以對。

| 項目 | CLI 畫面 | 程式（由 `axes[]` 算出） | 判定 |
|---|---|---|---|
| session 用量 | `1% used` | `session.pct = 1.0` | ✅ 逐字吻合（**不吃容差**） |
| session reset | `Resets in 1 hr 38 min`（＝98 分） | `resets_at = 2026-08-12T15:00:00Z`；於 21:27（+08:00）讀 ⇒ 93 分 | ✅ 落在容差內 |

**容差＝10 分鐘，理由不是「誤差」而是三個各自有界的錯位之和**（機械物：
`tools/tests/test_quota_policy.py::TestR86WindowRelativeHorizonAndCrossWindowAmortization`
::`test_the_helm_cli_screen_reconciles_with_the_axes_snapshot`，常數
`_CLI_TOLERANCE_MINUTES`）：

1. CLI 畫面與程式**不是同一刻**讀的（掌舵者貼圖與舵手跑指令之間有數分鐘）；
2. CLI 的分鐘數是**截斷顯示**（`1 hr 38 min` 對應 98.0~98.99 分）；
3. 讀取時刻本身只記錄到分。

⇒ 10 分鐘是三者之和的寬鬆上界。**它仍然有鑑別力**：`resets_at` 若真的解錯（差一小時、
差一天、時區當成本地），這一支照樣紅。`pct` 那一列刻意**不給容差**——它是同一個整數。

> 🔴 這一節的機械價值在於「下一輪還驗得到」。此前「取數零誤差」是一句對話裡的話，
> 沒有任何東西會在它變成假話時轉紅。

---

## 二、兩軸換算比 r：唯一的取得方式是觀測（結構上解不出來）

`r` ＝ 短窗 1pp 相當於長窗幾 pp 的倒數（短窗 pp／長窗 pp）。它等於
`limit_7d / limit_5h`，而伺服器把**兩個分母都藏起來**——快取的 `denominator.text` 逐字：
「伺服器未揭露分母（`five_hour.limit_dollars` 為 null）」⇒ 沒有任何算式能在不觀測的
情況下解出它。

### 2.1 本日觀測（同一支載具、同一台機器、零額外探測）

| 時刻（+08:00） | `session`／`five_hour` | `seven_day`／`weekly_all` | 來源 |
|---|---|---|---|
| 21:24 | 1pp | 74pp | 掌舵者 CLI ＋ 舵手 `--pace` 對帳 |
| 22:16 | 16pp | 75pp | 舵手 `--pace` |
| 22:29 | 22pp | 76pp | 本包 `--pace`（快取自動刷新） |
| 22:43 | 32pp | 77pp | 本包 `--pace` |

**點估**：`Δshort/Δlong = (32−1)/(77−74) = 10.3`（舵手以前兩點手算為 15）。
**本程式採用的是下界，不是點估**（`quota_pace.ratio_of`）：兩軸讀數都是整數 pp
⇒ 差值誤差各最多 ±1 ⇒ 真值滿足 `Δshort ≥ 觀測−1`、`Δlong ≤ 觀測+1` ⇒
`r_下界 = (Δshort−1)/(Δlong+1)`。為何取下界：**r 愈大 ⇒ 本窗配額愈大 ⇒ 愈鬆**，
所以保守側就是小 r。

### 2.2 落款（否則結構上永遠 0 樣本）

快取只存最新一次 ⇒ 沒有落款就沒有差分可算。本輪落地：
`tools/lib/quota_gate.py::record_burn()`／`burn_ledger_path()`，落在**持久目錄**
`~/.autosdd/traces/quota_burn.jsonl`（SSOT＝`tools/lib/endurance_env.py:trace_dir()`，
逃生口 `AUTOSDD_TRACE_DIR`）。**刻意不落 `$TMPDIR`**：R84／ZT-03 已判過系統暫存重開機
即消失，而「事後查不到」不等於「沒發生」。每次 `--pace` append 一列（同一個
`measured_at` 只寫一次）⇒ **查一次就多一個樣本**，而查一次是零 token。

樣本不足時的行為（`quota_pace.estimate_ratio`）：區段數 <3 ⇒ 取 **min**（最緊的那個 r）
並在輸出逐字說「n=1<3 樣本不足 ⇒ 保守取 min」；≥3 ⇒ 取中位數。
🔴 為何不永遠取 min：min 對樣本數單調不增 ⇒ 蒐集愈多資料只會愈來愈緊，最後變成一個
永久生效的煞車，而本 repo 判過「擋到讓人無法工作的守衛會被整個關掉」。

上表 21:24／22:16 兩點另以 repo 內常數 `quota_pace.SEED_OBSERVATIONS` 落款為**先驗**
（provenance 指回本檔）：落款一旦累積出真實區段，兩者會併進同一池。

---

## 三、缺陷 A：`FAR_HORIZON_MINUTES=360` 是絕對分鐘數 ⇒ 兩類軸相反的極端

| 軸 | 窗長 | 360 佔窗長 | 後果 |
|---|---|---|---|
| `five_hour`／`session` | 300 分 | **120%** | 距離最多 300 < 360 ⇒ **far 結構上不可達、永不減速** |
| `seven_day`／`weekly_all` | 10080 分 | **3.6%** | **96.4% 的時間恆為 far** ⇒ 吃恆定 ×0.5，「近 reset 就加速」結構上不可能 |

**治法**（`quota_pace.thresholds()`）：門檻相對於各軸窗長。
`near = 窗長 × (accel_window_minutes / 300)`、`far = 窗長 × 0.5`。

- 參考窗長 300 **不是字面**，由同一條文法解出（`window_minutes("five_hour")`）；掌舵者原句
  「Token 剩 30Min 就 Reset」講的就是那個 5 小時窗 ⇒ 300 分窗上換算回來**仍是 30 分鐘**。
- `far` 取窗長中點：正規化窗上唯一有語意的分界，兩邊同時可達（不是挑一個數字）。

**窗長從哪來**（`quota_pace.window_minutes()`／`windows()`），以及它的失效模式：

1. **文法**（不是桶名清單）：以 `_` 切詞，命中週期詞或「（數量詞＋）單位詞」。
   實測 `five_hour`→300、`seven_day`／`seven_day_opus`→10080、`weekly_all`／`weekly_scoped`→10080。
   🔴 為何不寫一張表：`quota_policy` 檔頭既有紀律禁止寫死桶名清單，而本輪實測
   `schema_keys` 已有 `seven_day_cowork`／`seven_day_oauth_apps`／`seven_day_omelette`／
   `seven_day_opus`／`seven_day_sonnet` 五個桶——**兩列的表對它們整片失明，一條文法全中**。
2. **同 reset 繼承**：文法解不出時，由 `resets_at` **逐字相同**的鄰軸繼承（取最短）。
   依據是資料：今天 `session` 與 `five_hour` 的 `resets_at` 連微秒都一樣
   （`…14:59:59.288259+00:00`）⇒ 它們是同一條底層限制被回報兩次。
   失效模式：相同的**結束時刻**不等於相同的**窗長** ⇒ 取最短（短窗 ⇒ near 門檻更小
   ⇒ 更不容易加速，而加速是唯一會把額度燒掉的方向）。
3. **兩者都解不出**（今天：`session` 單軸情境、`nimbus_quill`、`spend`）⇒ **不偽造窗長**，
   退回既有的兩個絕對門檻。

### 🔴 這一項對任務書的部分不從（附理由與實測）

任務書要求「未知一律走保守側（＝當成 far／減速）」。本包**沒有照字面做**，三條理由：

1. **生產面零差別**：live 快取 7 軸裡兩者都解不出的只有 `nimbus_quill`／`spend`，
   而這兩軸的 `resets_at` 本來就是 `null` ⇒ 早已是 `AXIS_NONE`（×0.5）。
2. **它會反向推翻 R84／SA-01 才治好的缺陷**：`session` 在**單軸**情境下窗長不明
   （沒有同 reset 的鄰軸），強制 far 會讓掌舵者錨點①「剩 30 分鐘就 reset、還有 100%
   沒用 ⇒ 多派」在那一軸永遠少派一半——那正是 SA-01 的病。
3. **保守的正確定義是「不得比今天更鬆」**，不是「一律更緊」。這一條已做成機械保證
   （下一節的夾層），而不是宣稱。

**向後相容**：`AUTOSDD_QUOTA_FAR_HORIZON_MINUTES`／`AUTOSDD_QUOTA_ACCEL_WINDOW_MINUTES`
兩個既有 env 鍵一格都沒有消失，它們現在有**兩個**活消費者——窗長不明時是門檻本身，
窗長已知時是「不准比它更鬆」的那道夾層。`.env`／`.env.example` 一個字都不必改。

---

## 四、缺陷 B：瞬時 `pct` 單獨看沒有意義

`quota_pace.lead_pp()`＝`pct − 100 × elapsed`，其中
`elapsed = 1 − 距reset ÷ 窗長`（夾在 `[0,1]`）。三態（`burn_step()`）：

| 條件 | 動作 | 為何不對稱 |
|---|---|---|
| `lead > 0`（超前線性預算） | 減速，**任何幅度都算** | 減速猜錯只是慢一點 |
| `lead ≤ −anchor邊際` | 允許加速 | 加速猜錯會**爆額度** |
| 其他／算不出 | 不動 | 未知不製造新的放行 |

### 4.1 「窗起點＝reset − 窗長」對滾動視窗是否成立（實測劃界，不是假設）

R79 已實測 reset 是**滾動視窗、錨在該區塊第一次用量**。若 `reset = anchor + 窗長` 逐秒
成立，則「窗起點＝reset − 窗長」**恰好精確**。本輪的實測**否證了逐秒版本**：

> 今天 `five_hour` 的 `resets_at` 是 `…14:59:59.288259+00:00`，`seven_day` 是
> `…17:59:59.288281+00:00`——**兩個不同窗長的軸，秒數尾巴同為 `:59:59`**。
> 兩個獨立的「第一次用量」不可能都恰好落在 `:59:59` ⇒ 伺服器另有**小時級 snap**。

⇒ 成立的只有**小時精度**版本，偏差上界 1 小時。偏差**方向**：若 snap 是向上取整（今天的
觀測支持這一向），則 `elapsed` 被**低估** ⇒ `lead` 被高估 ⇒ 偏向減速＝安全側。但 snap 的
方向本身未經證實（R79 逐字稿另有 `3:50am`／`12:20pm` 這種分鐘級字面）⇒ **放行側**留最壞
1 小時的邊際、**煞車側不留**（`quota_pace.anchor_margin_pp()`：300 分窗 ⇒ 20pp、
10080 分窗 ⇒ 0.6pp、窗長未知 ⇒ 100pp＝這一側結構上不可達）。

### 4.2 方向鎖（本輪最重要的一道判準）

`quota_pace.effective_horizon()`：

- 有「省」的證據 ⇒ 相對門檻直接生效（**可以**比絕對門檻鬆——這正是週軸 96.4% 恆 far 的解）；
- 沒有證據（含窗長不明）⇒ 與絕對門檻取**較緊**者 ⇒ 結構上不可能比今天鬆；
- 超前 ⇒ 再與 `far` 取較緊者。

夾在 **label** 而不是 cap，因為 `_cap_for`／`_rec_for` 對視野檔位是單調的
（near 2.0 > mid 1.0 > far/none 0.5）⇒ 夾住 label 等於夾住 cap 與 rec，而消費端
（`_pace_of`／`describe`／`AxisReading.horizon`）一行都不必改。

---

## 五、缺陷 C（舵手 R86 立案，最高優先）：跨窗攤提

**病**：`cap` 是**併發度**旋鈕（速率），週配額是**總量**限制；降 `cap` 只讓同一批工作花
更久，總消耗不變（串行化甚至更貴）⇒ 用 `cap` 保護週配額是用錯旋鈕。而「短窗還很空」
**不等於**可以衝——本窗真正的上限是**它分攤到的長窗配額**。

**算式**（`quota_pace.amortize()`；速率軸＝最短窗、總量軸＝最長窗，**由窗長導出、不由桶名**）：

```
剩餘長窗配額 = 100 − 長窗pct
剩餘窗數     = 長窗距reset分鐘 ÷ 短窗窗長        (夾在 ≥1)
每窗配額     = 剩餘長窗配額 ÷ 剩餘窗數            (長窗刻度)
本窗配額     = min(100, 每窗配額 × r)             (短窗刻度)
本窗餘裕     = 本窗配額 − 短窗pct
```

### 5.1 與舵手手算的逐項對帳（他的輸入：長窗剩 25pp、距 reset 3.15 天、r=15、短窗已用 16pp）

| 中間量 | 舵手手算 | 程式 | 判定 |
|---|---|---|---|
| 剩餘窗數 | 15.1 | **15.12** | ✅ |
| 每窗配額 | 1.66pp | **1.65pp** | ✅ |
| 本窗配額（短窗刻度） | 25% | **24.8pp** | ✅ |
| 本窗餘裕 | ≈+9pp | **+8.8pp** | ✅ |

⇒ **舵手手算全部正確，無須駁回**。實跑指令與 rc 見 §七。

### 5.2 它怎麼進到決策：**只會收緊，永不放寬**

`quota_pace.band_inputs()` 把速率軸餵給 `pct_band` 的水位換成
`max(原始pct, min(halt−1, 100 × 原始pct ÷ 本窗配額))`。三道邊界：

- `本窗配額 ≤ 100` ⇒ `100×pct/配額 ≥ pct` ⇒ **結構上不可能放寬**，連 `r` 被設成 1e6 也不行；
- 上界封在 `halt − 1` ⇒ **推導值永不觸發停止派發**（halt 只由伺服器給的真實水位開火）；
- 下界是原始 pct ⇒ 已在 halt 帶的軸不會被這一格放寬回 prepare。

**已知副作用（誠實揭露）**：速率軸的 band 現在可能落到 `prepare`，若它同時成為
`binding`，hook 的「準備下一次 reset」儀式（寫可重啟點任務書、一個 reset 視窗一次）
會因**推導值**觸發。判讀上這是對的（「本窗已超出攤提配額 ⇒ 準備等下一個窗」），
但它是一個會寫檔的行為變更，故在此具名。

### 5.3 輸出必須說出因果（掌舵者不滿的直接原因）

`--pace` 第三行（`quota_pace.explain()`）實跑輸出：

```
攤提：kind=weekly_all 剩 23pp／距 reset 4513 分鐘 ÷ 15.0 個 kind=session 窗 = 每窗 1.53pp
      ×r=7.5（n=1<3 樣本不足 ⇒ 保守取 min）⇒ 本窗配額 11.5pp；
      kind=session 已用 32pp 剩 13 分鐘 ⇒ 本窗餘裕 -20.5pp
```

一行內回答了「為什麼空著也不能衝」。刻意**一個 `%` 都不出現、全用 `pp`**：① pp 才是這些
量的正確單位（它們是配額與差值）；② M7 判準逐個掃 `%` 並要求每一個都自帶 `kind=` 與剩餘
分鐘，用 pp 讓判準的射程與本行的語意不互相扭曲。

---

## 五之二、配速**檔案契約**的寫入端（跨包：Dev 包持有讀取端）

引擎（`autoclaude/`）**不准** import 根層護欄層——`.importlinter` 的 `no-harness-import`
契約 ⇒ 「根層算 cap、引擎用 cap」唯一的傳遞方式是檔案契約。寫入端＝
`tools/lib/pace_contract.py`（本輪落地），掛在 `pace_report()` 內。

| 事項 | 決定 |
|---|---|
| 路徑／schema | `<tempdir>/autosdd_pace.json`／`autosdd.pace/1`（兩邊字面由判準逐字比對） |
| `measured_at` | 一律搬 `QuotaState.measured_at`＝**額度被量到**的時刻，**不是** `now` |
| `cap` 映射 | `None`（不設限）⇒ `max_fanout`；halt ⇒ `0`。**不得寫 `None`** |
| 失敗處理 | fail-soft：寫不進去只在 stderr 說一次，`--pace` 的 rc 與輸出都不變 |
| 原子性 | 暫存檔（檔名帶 pid，多包並行不互相覆寫）→ `os.replace`，包在 `except OSError` |

🔴 **`measured_at` 那一格是本檔最容易寫錯、且寫錯完全靜默的地方**：契約可能「拿 30 分鐘
前的舊快取、現在算、立刻寫檔」⇒ mtime 全新、量測很舊，而那個組合的外觀與「剛量到」
完全相同。所以新鮮度必須讀 payload 的 `measured_at`，不准讀 mtime。

🔴 **兩個字面必然有兩個家**（一個在引擎、一個在寫入端，而兩邊結構上不准互相 import）
⇒ 那個縫由判準縫起來：`quota_criteria.contract_literal_problems()`（消費端＝
`test_quota_policy.py::TestR86ThePaceContractWriterMatchesTheEngineReader`）。沒有它，
改掉任一邊 ⇒ 寫入者寫一份沒有人讀的檔，而**失敗表徵與成功完全相同**。

實跑（`--pace` 後的契約檔全文）：

```json
{"schema": "autosdd.pace/1", "cap": 2, "band": "converge",
 "measured_at": "2026-08-12T23:02:43+08:00", "source": "cache",
 "headroom_pct": 16.0, "headroom_pct_per_hour": 0.214,
 "binding_kind": "seven_day", "recommended_fanout": 1}
```

### 五之二之一、同一族資料上的**三個 TTL**：為什麼它們不同（此前一處都沒寫）

| TTL | 值 | 家 | 它在回答什麼問題 |
|---|---|---|---|
| harness 額度快取 | **180s** | `quota_gate.QUOTA_CACHE_TTL_SECONDS` | 「這個**水位讀數**還能不能用來做**節流決策**」 |
| 配速契約 | **900s** | `file_quota_meter.PACE_TTL_SECONDS` | 「這個**已算好的 cap** 還能不能用來限**併發度**」 |
| 引擎原始量測 | **1800s** | `file_quota_meter.DEFAULT_TTL_SECONDS` | 「這份**原始快取**還能不能被引擎當事實讀」 |

三者不同**不是漂移，是三個不同的問題**，而它們之間有一條**結構性不變式**：

```
180s  <  900s  <  1800s
 ↑        ↑        ↑
 決策用的讀數最短    衍生物（cap）壽命不得超過它的輸入（原始快取）
```

- **180 < 900**：節流決策要對「當下」負責（水位在爆發期一分鐘可以動十幾 pp，實測本輪
  52 分鐘動了 15pp），所以拿來擋工具呼叫的那個讀數必須最新；而 cap 是一個**上限**，
  它過期的後果只是「限得比實際需要更緊或更鬆一格」，不是擋錯一次呼叫。
- **900 < 1800**：`PACE_TTL < DEFAULT_TTL` 是 Dev 包上鎖的不變式（`TestPaceTtlIsBoundedByItsInput`，
  只准調小）——**衍生物的壽命不得超過它的輸入**。反過來就會出現「契約還被當有效，
  而它是從一份已經被判為過期的原始快取算出來的」。
- 三者都**不是**旋鈕：`PACE_TTL` 刻意沒有 env 鍵（開成旋鈕等於允許有人放寬它，而放寬
  要有證據）；`QUOTA_CACHE_TTL_SECONDS` 的來源該檔自陳「就是挑的」，重量入口是
  `python tools/lib/quota_meter.py --watch <秒>`。

🔴 **同一族的第四個數字是 `PACE_FUTURE_SKEW_SECONDS`（60s）**，它不是 TTL 而是**負向**
容忍（契約的 `measured_at` 比現在晚一點時仍收）——時鐘微調不該讓契約整份失效。

### 五之二之二、`stale-cache` 的訊息（Dev 包挖出、本輪修在本檔）

**病不在判準**（過期 ⇒ 保守，是對的），**在訊息**：畫面印「額度量不到」，而事實是
「資料在、只是超過 180 秒」——**這兩者要求 operator 做不同的事**（前者去查網路／憑證，
後者只要重量一次），而 `_blank()` 當時把 `source` 與 `reason` 綁成同一個字面，那兩個數字
（age／TTL）結構上到不了畫面。修法是把兩者解耦：`source` 仍是穩定的短分類字面
（降級痕跡的檔名與相等鎖都吃它），`reason` 帶人看的那一句。實測：

```
source = stale-cache
describe: 額度量不到（reason=stale-cache（資料在，但已 900s > TTL 180s ⇒ 重量一次即可，
          不是取數壞掉））⇒ cap=4 recommended=4 band=unmeasured binding=-
```

---

## 五之三、一筆值得記下的分桶陷阱（本輪真的踩到並修掉）

在 `tools/tests/*.py` 的註解裡寫出 `docs/06_quality/<檔名>` 這個**路徑**，會讓分桶普查把
**整塊**（頂層 class／def）歸進 shrink-only 的 `prose` 桶——本輪實測兩處引用讓該桶由
4464 → **4525（+61）**，而那 61 行守的是沙箱隔離與 cap 階梯，**與散文無關**。
修法：引用具名證據檔時只寫檔名、不寫目錄前綴（token 不以 `docs/` 開頭即不計入）。
修後實測回到 **4464＝基線**。⇒ 這是「引用一份文件」這個無害動作的隱性成本，記在這裡
是因為下一個要在護欄層引用證據檔的人一定會再踩一次。

---

## 六、本輪**沒有**做的事（誠實劃界，全部列入交棒）

1. **沒有拿掉 `far×0.5`。** 舵手指出攤提一旦存在，`far` 的角色該從「乘法懲罰」降為
   「蒸發急迫度」，方向與 `far×0.5` 相反——同意那個方向，但**拿掉一個煞車是放寬**，
   而放寬要有證據；本輪 per-agent 燃燒率樣本 n 極小。
2. **沒有做旋鈕語意分離的下半場**（cap 只由短窗決定、長窗改為「本輪派幾包」的總量閘）。
   今天 `cap=2` 仍來自長窗 `converge×far`；攤提算出的短窗上限是 4。要讓 cap 只由短窗
   決定＝一個 2 倍的放寬，需要 per-agent 燃燒率校準才有證據。
3. **per-agent 燃燒率算不出來**：它＝`Δpct ÷ (Δ分鐘 × 併發數)`，而併發數此前沒有落款。
   本輪已把 `live`（`live_dispatches()`）寫進每一列落款 ⇒ **下一輪算得出來**。
4. **新的四個門檻沒有 env 旋鈕**（`_MID_FRAC`／`_ANCHOR_MINUTES`／`_ROBUST_SEGMENTS`／
   `_ROLLOVER_EPS`，家在 `quota_pace`）。原因是硬約束：`quota_policy.py` 的 LOC tier
   餘裕只有 4 行（實測 396/400），而每個旋鈕要 3 行（`Policy` 欄位 ＋ `ENV_SPEC` 兩行）。
   要參數化須先把 env 層拆出 `quota_policy.py`（另案）。前三個之中，`_MID_FRAC` 與
   `_ANCHOR_MINUTES` 有推導依據（中點／1 小時 snap 上界），另兩個是挑的。
5. **`r` 的估計對「當時在跑幾個 agent」不敏感**：同一個 `Δshort/Δlong` 在 1 個 agent 與
   5 個 agent 下相同（它量的是兩個分母的比值，不是速率）⇒ 這一項不是缺口；缺口在第 3 條。
6. **注入自證的一個已知空白**：把方向鎖夾層拿掉時，「窗長不明＝逐格等於 R85 版」那一支
   仍然綠（實測）。那不是漏洞——該支測的是窗長不明的路徑，夾層對它是恆等；夾層本身由
   `test_acceleration_never_happens_without_evidence_of_thrift` 守（拿掉即紅，實測）。
7. **帳本列沒有落地**（`AutoSDD_Defect_Log.md`）：帳本的「當前輪」是由「發現情境」欄
   **現查**推得，寫入本輪第一列會把時鐘從 R85 推進到 R86 ⇒ 一整批承接輪次為 R85／R80 的
   未結列當場違反硬規則②。**實測**（`<scratchpad>/ledger_clock_probe.py`，不動 tracked 檔：
   把帳本複製到 scratchpad、追加一列 R86、再 monkeypatch `_DEFECT_LOG`）：

   | 帳本 | `check_defect_log_crossref` rc | 推得的當前輪 | 孤兒承接輪次 |
   |---|---|---|---|
   | 原帳本（對照組） | **0** | R85 | 0 筆 |
   | 追加一列 R86 | **1** | R86 | **29 筆** |

   ⇒ 那是**收尾單人窗口**的動作（鐵律七：常數／史料／消費端不同持有面）。本包只落地
   治理登記面（`governance_docs.py`，實測 rc=0、37 份皆已登記）。

8. **`far` 在窗的最前段幾乎恆真**（本輪實測看到的新形狀，非缺陷）：窗剛翻頁時
   `elapsed≈0`，任何用量都「超前線性預算」⇒ `burn-ahead` ⇒ `far`。實測 `five_hour` 2%＠
   剩 295 分（lead=+0.3pp）即判 far。方向是**收緊**故無害（free 帶的 cap 本來就是 None），
   但它讓 `mid` 在窗前段幾乎不可達。要治它需要「線性預算」以外的基準（例：本窗攤提配額
   的線性化），屬第 2 條的下游。

9. **配速契約寫入者已落地，但刷新頻率仰賴人**：`--pace` 每次呼叫寫一次
   （`tools/lib/pace_contract.py`），而引擎側 TTL 是 900s ⇒ 沒人查 `--pace` 時契約會過期，
   引擎走保守地板並出聲（Dev 包已上鎖的行為，不是靜默）。把寫入掛進 PreToolUse hook 的
   同一條路可讓它自動保鮮，但那會在每次工具呼叫寫一次檔，且 `quota_gate.py` 的 LOC 餘裕
   實測只剩 2 行 ⇒ 交棒。

10. **契約的 `headroom_pct` 用的是引擎 port docstring 的語意**（halt 水位 − 最緊那軸的
    水位，非負），**不是**本輪 `amortize()` 算的跨窗餘裕（帶正負號）。兩者不可互換：把
    帶負號的量寫進一個宣告為非負的欄位是靜默的語意漂移。統一要動 port 那份 docstring，
    而它在 Dev 包的持有面內 ⇒ 交棒。

---

## 七、逐項自證（當回合真跑的指令與 rc）

```
# 四項自證（缺陷 A／B／C ＋ 今天真實快取的假紅普查 ＋ 舵手手算對帳）
AUTOSDD_TRACE_DIR=<scratchpad>/tr .venv/bin/python <scratchpad>/selfproof.py     rc=0
```

| 自證 | R85 版（對照組，程式重建） | R86 版 | 判定 |
|---|---|---|---|
| A：pct=50、剩 200 分、`five_hour` vs `seven_day` | `mid`／`mid`（**相同**） | `far` cap=4／`near` cap=16（**不同**） | ✅ |
| B：`seven_day` pct=74、已過 20% vs 90% | cap=2／cap=2（**相同**） | cap=2／cap=8（**不同**；lead +54 vs −16） | ✅ |
| C：短窗讀數固定、長窗剩 2 窗 vs 30 窗 | cap=None／cap=None（**相同**） | 餘裕 +47.5pp cap=None／−34.2pp cap=2 | ✅ |

**假紅普查（真實快取，7 軸逐軸）**。🔴 這是**移動的量測值不是常數**：本輪三小時內快取自然
刷新過四次（短窗翻頁一次），下表是收工那一刻（`now=2026-08-12T23:25:59+08:00`，r=7.5）：

| kind | pct | 剩分鐘 | 舊 horizon/cap/rec | 新 horizon/cap/rec | 更寬鬆？ |
|---|---|---|---|---|---|
| session | 17.0 | 274 | mid / None / 8 | far / **1** / 1 | no（收緊） |
| weekly_all | 80.0 | 4474 | far / 2 / 1 | far / 2 / 1 | no（不變） |
| weekly_scoped | 0.0 | – | none / None / 4 | none / None / 4 | no |
| five_hour | 17.0 | 274 | mid / None / 8 | far / **1** / 1 | no（收緊） |
| seven_day | 80.0 | 4474 | far / 2 / 1 | far / 2 / 1 | no（不變） |
| nimbus_quill | 0.0 | – | none / None / 4 | none / None / 4 | no |
| spend | 0.0 | – | none / None / 4 | none / None / 4 | no |

⇒ **逐軸更寬鬆的筆數 = 0**；全域 `cap` 舊 2 → 新 **1**、`binding` 由 `seven_day` 變成
`five_hour`。攤提實跑：`長窗剩 20pp ÷ 14.9 窗 = 每窗 1.34pp ×r=7.5 ⇒ 本窗配額 10.1pp；
已用 17pp ⇒ 本窗餘裕 −6.9pp`。也就是說「短窗只用了 17%、還有 274 分鐘」這個看起來很寬鬆
的畫面，在攤提之後是**超出本窗配額 6.9pp** ⇒ 收緊到 1。這正是缺陷 C 要治的那個誤讀。

早一小時（`22:45`，短窗 32%＠剩 14 分）的同一份普查同樣是 **0 筆更寬鬆**，全域 cap 2 → 2。
兩次都與舵手的判讀一致：週軸超前 ⇒ **不該**更寬鬆，而實測確實沒有。

**合成注入紅綠自證**（`<scratchpad>/redproof.py`，rc=0）：

| 注入 | 應該紅的判準 | 實測 |
|---|---|---|
| 拿掉「無證據不得比絕對門檻鬆」夾層 | 方向鎖 | **RED** ✅ |
| 攤提改成可以調低水位 | 單向鎖 | **RED** ✅ |
| 窗長文法恆回 `None`（＝缺陷 A 原狀） | 缺陷 A／缺陷 C | **RED**／**RED** ✅ |
| 全部復原 | 三者 | GREEN ✅ |

**回歸**：

```
cd tools/tests && ../../.venv/bin/python -m unittest test_quota_policy -q     rc=0  (Ran 127)
cd tools/tests && ../../.venv/bin/python -m unittest test_context_budget_guard  rc=0  (Ran 357, skipped=8)
.venv/bin/python AutoClaude/tools/check_loc_budget.py --json                   root_tools_violations=[]
```

**判準搬家（護欄層行數面的淨減法）**：`tools/tests/test_quota_policy.py` 的判準本體
（M2／M5／M7／M10 四族 ＋ 本輪 R86 三缺陷的對照組與掃描網格）全數搬進
`tools/lib/quota_criteria.py`，測試檔只留「呼叫判準 ＋ 斷言」。兩個理由同時成立：
① 那些函式一個都不依賴 unittest（是對源碼／讀數的純判定）；② `tools/tests/*.py` 受護欄層
行數棘輪管而 `tools/lib/` 不在那個面內。**鑑別力不得下降是硬約束，已重跑驗證**——搬家後
的注入結果與搬家前**逐字相同**（①RED ②RED ③RED/RED，復原後全 GREEN）。

淨行數（`wc -l`，對 `test_adr_xplat001_c1c2_lock.py` 凍結表的基線）：

| 檔 | 凍結基線 | 收工 | 淨額 |
|---|---|---|---|
| `test_quota_policy.py` | 1657 | 1619 | **−38** |
| `test_context_budget_guard.py` | 6354 | 6379 | **+25** |
| 合計 | | | **−13** |

R85 版的既有 117 支測試**一支都沒有改**（新增 10 支）——那就是向後相容的機械證明。
唯一改動的既有斷言是 `test_context_budget_guard.py::ThrottleBandSaysHowLongItLastsTest`
::`test_the_cap_ladder_now_moves_with_the_reset_distance` 的**中間取樣點**（1 小時 → 20
小時）：對一個 7 天窗來說「1 小時前」與「10 分鐘前」是同一件事（都 <0.6% 窗長），
它們此前被讀成兩格只因門檻是絕對分鐘數——那正是缺陷 A。斷言、方向、halt 那一格一字未改，
三格仍嚴格遞減（4 > 2 > 1，實測）。
