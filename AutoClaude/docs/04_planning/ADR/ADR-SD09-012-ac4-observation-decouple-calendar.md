# ADR-SD09-012：AC4 觀察期判準解除「日曆連續」綁定（採用 obs／drift 線上同款 gap-tolerant streak）

> **標題用字說明（2026-08-03 訂正）**：原標題寫「obs/drift **既驗證**的」，易被讀成「兩軌都已達標」——**那是錯的**。
> 精確表述：**obs 與 drift 兩軌線上跑的是同一款 gap-tolerant 判準**，其中 **obs 已達標（42/30, rc=0）**、**drift 未達標（26/30, rc=1，因一筆真紅）**。詳見 §1.1 訂正框與 §2.1。

| 欄位 | 內容 |
|------|------|
| 狀態 | **ACCEPTED — PM 拍板 2026-08-03；判準 code 已於 2026-08-04（R74）落地**（採用 §3.2 gap-tolerant green_streak ＋ §7.1 L-7 staleness 配套）。落地清單與逐項處置見 **§7.1**；落地當回合實測見 **§7.6** |
| 🔴 拍板後訂正 | **2026-08-03 Architect 複審實測證偽「反作弊零改動」**：本方案有**第二處放寬＝證據新鮮度（liveness）**，且**與安全有關**。PM 是在不完整的揭露上拍板的。**方向不變**（gap-tolerant 仍採用），但落地必須加做 **§7.1 L-7 獨立 staleness 判準**。詳見 §1.4 訂正框、§4.3、§7.0 |
| 提案輪 | AutoSDD improving（C 軌 SD_09 W1 觀察期收斂） |
| 編號 | 由主控集中發號（012）。013 已配給 mutation 軌死鎖案，勿混用 |
| supersede | ADR-SD09-008 v0.4「連續 14 天全綠」的**日曆連續語意**（門檻數值 recall 0.95／p95 60ms／σ 0.02 全部不變） |
| 同構先例 | **ADR-SD09-011**（mutation 軌解除日曆綁定）。本 ADR 是同一個病在第二軌的復發，但**藥方不同**——理由見 §3.1 |
| 相關 | M-05 反作弊（同 UTC date 去重）、紀律 #6（採集寬鬆 vs 升級嚴格分軌） |

---

## 1　Context（問題陳述）

### 1.1 定位：AC4 是 SD_09 W1 啟動的**唯一剩餘阻塞項**

SD_09 W1 啟動需三個觀察期同時達標。**2026-08-03T02:57Z 實查（本節數字為此刻重新量測值，見下方訂正框）**：

| 觀察期 | 判準 | 實況 | 狀態 |
|---|---|---|---|
| #1 mutation | unique source_sha256 ≥ 7 | 5/7 | **結構性死鎖 → 已由 ADR-SD09-013 承載放行**（W1 要啟動才能改源碼、改源碼才能達標） |
| #2 **AC4** | 連續 14 日曆天全綠 | **8/14** | **← 本 ADR。W1 入場的唯一無爭議阻塞項** |
| #3 drift_log | 30 天零非 info 事件<br>權威工具＝`tools/drift_log_ga_check.py` | **`green_streak=26 / window=30`**<br>（rc=**1**、`status=observing`） | 🔴 **未達標** — 見下方訂正框。**非 W1 入場阻塞項**（歸屬待 PM 裁定），但 **W5 雙條件**角色不受影響 |

W1 最遲啟動日 **2026-06-26**；今天 **2026-08-03**，已超期 **38 天**。
**#1 已由 ADR-SD09-013 放行；#3 未達標但其是否為 W1 入場條件尚有判準衝突（待 PM 裁定）。就「無爭議的入場阻塞項」而言，AC4 是唯一還壓著 W1 的東西。**

> ### 🔴 訂正框：本表 #3 原寫「早已達標」，**是錯的**（2026-08-03 訂正）
>
> **原文**：「#3 drift_log｜34 筆、`severity_non_info_count` 全 0｜**早已達標**，只是 §8.2 清單沒打勾」。
> **錯誤性質**：把「**真實漂移事件數為零**」（正確）誤推為「**觀察期 #3 判準已通過**」（錯誤）。兩者不等價——
> 判準 `passed` 的定義是 `drift_log_table_exists AND severity_non_info_count == 0`（[`tools/drift_log_snapshot.py`](../../tools/drift_log_snapshot.py) `build_record()`），
> 而 `green_streak` 只要遇到**任何一筆** `passed=false` 就從該筆之後重新起算——**包含採集失敗，不只漂移事件**。
>
> **權威工具當回合實跑**（`AutoClaude/` 下 `../.venv/Scripts/python.exe tools/drift_log_ga_check.py --json`，2026-08-03T02:57Z）：
> ```json
> {"status": "observing", "green_streak": 26, "window": 30, "total_records": 35,
>  "history_path": ".drift_log_history.jsonl",
>  "last_failure_reason": "drift_log_table_exists=False (alembic head 落後)"}
> ```
> `rc=1`。
>
> **原始資料核對**（`.drift_log_history.jsonl` 35 筆，2026-05-21 ~ 2026-08-02 UTC）：
> - `severity_non_info_count` **全 35 筆皆為 0** ⇒ 「真實漂移事件為零」這半句**是對的**；
> - **第 9 筆**（`2026-06-02T18:00:51+00:00`）`drift_log_table_exists: false` / `passed: false` ⇒ **採集失敗**（非漂移事件）打斷 streak；
> - 其後第 10~35 筆全綠 = **26 筆** ⇒ `green_streak=26 < 30`，**不可打勾**。
>
> **錯誤來源**：主控在起草時給了「#3 早已達標」的前提，撰寫者未經權威工具複核即採信。**責任在前提提供者，但錯誤本身必須訂正**——這正是紀律 #17「zero-trust 須雙向：對自己上一段／上游的宣稱也要複核」的適用場景。
>
> **⚠️ 此錯誤具傳染性**：§2.1 對照表把 drift 標為 `PASS 34/30`，同樣是**把總筆數當成 green_streak**。§2.1 已一併訂正。
>
> **⚠️ 連帶影響**：這筆採集失敗即 **R-SD09-A-5 風險的實際發生**，而其緩解措施又要等 W0 G0 ⇒ **同型死鎖第二例（R-SD09-A-5-LOOP）**。處置見 [SD_Improving_09.md §8.3 D-2](../SD_Improving_09.md) 與 [risk_log.md §15](../../05_development/risk_log.md)。**好消息**：alembic head 落後這個根因**現已不存在**（2026-08-03 唯讀實查 `alembic_version = 0018_version_kind_discriminator` = 鏈頭），#3 只需再累積綠紀錄即可自然通過，詳見該處。

### 1.2 拖著的代價不是「多等幾天」，是「等不到」

照現行判準，這台機器達標的期望時間是 **1.5 年～ 89 年**（§2.5 算式）。這不是「再忍耐一下」，是**永遠不會發生**。W1 會無限期停在門外。

### 1.3 根因：判準量到的是使用者的開機作息，不是系統品質

`ac4_progress_check.py` 的達標條件實質是：

```
filter_recent(records, days=14)   # 取滾動 14 日曆天窗（:135-142）
observation_days = len(records)   # 窗內筆數
達標需 observation_days >= 14
```

而 writer 端 `ac4_nightly_collector.append_history()`（:182-212）以 **UTC date 為鍵、同日覆寫**（M-05 反作弊修復）。

兩者相乘 ⇒ **一個 UTC 日最多 1 筆** ⇒ `observation_days = 14` 的**充要條件是「最近 14 個 UTC 日期每一天都有紀錄」**——也就是**零缺口**。任何一天沒開機，就不只是「慢一天」，而是**必須從頭再連滿 14 天**。

這台機器近 75 天活著 52 天（5 月 8／6 月 27／7 月 15／**8 月 2**），且 7/22、7/29、8/1 各有一次冷開機。**判準要求的是這台機器物理上做不到的事。**

### 1.4 為什麼這是缺陷而不是保守

真正想證明的事，從 checker 讀出來只有一件：**RTM feedback 的 p95 延遲穩定在門檻以下**（recall 0.999 恆定、CB open 恆 0，兩者從無波動）。

「14 個日曆天」是在代理**三**件事：
1. **重複量測**（不能只跑一次剛好很順）；
2. **時間跨度**（能看到慢速漂移，σ 守門）；
3. 🔴 **證據新鮮度 / liveness**（**2026-08-03 Architect 複審補列**）——`filter_recent` 是 `evaluate()` 內**唯一參照「現在」的項**（`tools/ac4_progress_check.py:141` `now = datetime.now(tz=utc)`，全檔僅此一處）。它同時在做兩件事：篩出窗內紀錄，**以及讓「達標」這件事對時鐘保持敏感**。

**「連續」不代理任何東西**——這半句仍然成立：缺口不會讓量測失效，第 3 天和第 5 天之間空了兩天，這兩筆仍是兩筆獨立、有時間跨度的證據。要求**相鄰**，只是把「使用者有沒有天天開機」寫進了系統品質的判準。

> #### 🔴 訂正框：初稿「『連續』不代理任何東西」被過度延伸，漏了第 3 項（2026-08-03 Architect 實測證偽）
>
> 初稿只列了兩項代理物，並據此在 §4.3 斷言「唯一放寬的是與安全無關的『缺口零容忍』」。**這個斷言不成立**，因為 §3.2 的改法不只移除「相鄰」，它把 `filter_recent` 整個移出閘門路徑——**連帶把唯一的時鐘參照一起移走了**。
>
> 後果：達標與否退化成**純粹的檔案內容函式**。採集器若無聲死掉（stage crash／schtasks 被停用／jsonl 被鎖住），`green_streak` 會**永遠凍結在最後一個值**，`evaluate()` 從此**永遠回報 `ready=True`**，且沒有任何東西會察覺。
>
> **本輪獨立複跑證實**（記憶體內模擬，未觸碰 `.ac4_history.jsonl`，production code 未改）：
> ```
> 造 14 筆全綠、timestamp 全部落在 2025-08-01 ~ 2025-08-14（距今 354 天）
> 現行判準  evaluate(filter_recent(stale)) -> observation_days=0  ready=False
>                                            reasons=['觀察期未滿（0/14 天）']
> 提案判準  evaluate(stale)                -> observation_days=14 green_streak=14
>                                            status=ready  ready=True  reasons=[]
> ```
> **一年前的死資料，在新判準下回 `ready=True`。**
>
> 這正是本 repo 反覆被咬的形態：`.drift_log_history.jsonl` 2026-06-02 那筆 `drift_log_table_exists=false` 就是**採集失敗**而非漂移事件（§1.1 訂正框）——同族病灶，只是那一軌的判準當場把它抓出來了，而移除時鐘後的 AC4 **抓不出來**。
>
> ⇒ 處置：**不推翻 PM 的拍板方向**（gap-tolerant 仍然是對的，§2.1 的實測依據未被動搖），而是**補完揭露**（§4.3 補列第二處放寬）**＋補一道獨立防線**（§7.1 **L-7** staleness 判準）。**PM 是在不完整的揭露上拍板的，這一點必須訂正，不是可選項。**

**repo 內已有現成反證**（§2.1）：obs 與 drift 兩軌用**同一台機器、同一支 nightly、同一份 M-05 去重**，判準只差在「容不容許缺口」。
**兩軌的 streak 都在大量缺口下持續累積**（obs 容忍 32 個缺口日、drift 容忍 35 個缺口日），其中 **obs 已跨過門檻（42/30，rc=0）**；
而 **AC4 用同一台機器、同樣的紀錄密度，卻卡在 8/14** ——差別只在判準容不容許缺口。

---

## 2　實測數據（本輪當回合實跑，非引述）

環境：Windows 11 真機，`AutoClaude/.venv/Scripts/python.exe`，2026-08-03。

### 2.1 決定性對照：同一台機器，容許缺口的判準讓 streak 一路累積；AC4 卡死

> **🔴 本節原始版本有誤，已於 2026-08-03T02:57Z 以權威工具重新量測訂正。**
> 原表把 drift 標為 `PASS 34/30`——那個 34 是**總筆數**，不是 `green_streak`（真值 26）。drift **未通過**。
> 同一次重測也反映了 2026-08-03 02:00 那輪 nightly（`logs/nightly_2026-08-03_020001.log`）為三軌各 +1 筆，故筆數較初稿 +1。

各軌**呼叫自己的權威 checker 函式**（`_load_history` + `_compute_green_streak`，不自行重算——紀律 #4）：

```
track  records  green_streak/window  verdict     streak 窗跨度        缺口日
obs        42        42 / 30         PASS  rc=0  05-21..08-02  74d      32
drift      35        26 / 30         FAIL  rc=1  06-03..08-02  61d      35   <- 未達標（2026-06-02 採集失敗打斷）
ac4        42         8 / 14         STUCK       （最近 14 日曆天窗內僅 8 筆）
```

**這組數字要讀出的是三件事，不是「兩軌都過了」：**

1. **容缺口的判準在這台機器上確實會累積** —— obs 的 42 連綠橫跨 74 個日曆天、容忍 **32 個缺口日**；drift 的 26 連綠橫跨 61 個日曆天、容忍 **35 個缺口日**。若換成「必須相鄰」，這兩軌都會被打回個位數。**gap-tolerant 這個機制本身，在 production 上是活的、有效的。**
2. **已真正跨過門檻的只有 obs（42/30, rc=0）** —— 這是**唯一**可以說「此判準形式已在本機驗證到達標」的實例。drift **不能**拿來當第二個達標實例。
3. **drift 沒過，恰恰證明這個判準不是橡皮圖章** —— 它沒過的原因**不是缺口**（缺口有 35 天照樣累積），而是**一筆貨真價實的紅**（2026-06-02 採集失敗）。**判準抓到了它，並且正確地把 streak 歸零。** 這是鑑別力的正面證據，不是反面證據。

**AC4 的紀錄筆數（42）與 obs 完全相同、比 drift（35）還多，而 drift 的門檻（30）是 AC4（14）的兩倍以上——AC4 卻是三軌中唯一卡死的。**
三軌的差別只有一個：obs/drift 數「連續的綠**紀錄**」（容缺口），AC4 數「落在 14 個**日曆天**內的紀錄」（零容忍）。

### 2.2 AC4 的 41 筆全綠——換成 obs/drift 判準，兩個月前就該過了

```
total records=41  all-green=True  record-based green_streak=41
-> 第 14 筆連續綠 = 2026-06-07T18:04:32+00:00
-> 依 obs/drift 語意，AC4 應於 2026-06-07 即 READY（距今 57 天）
```

> **量測時點註記（2026-08-03T02:57Z 複核）**：上列輸出為本 ADR **初稿撰寫當下（約 01:06）** 的實跑結果。
> 其後 **02:00 那輪 nightly**（`logs/nightly_2026-08-03_020001.log`）為三軌各再寫入 1 筆，故 `.ac4_history.jsonl` **現為 42 筆**（`wc -l` 實查）。
> **本複核僅重新計數，未重跑上述全史模擬**，因此上方區塊維持初稿原值不動（不以未實跑的數字覆寫已實跑的輸出）。
> 筆數 +1 只會讓結論更強（41 → 42 皆遠超門檻 14），方向不變。

### 2.3 任務 1：每小時觸發一次（一天 24 次／一個月 720 次）會發生什麼

實測（scratchpad 臨時 history，**未污染真實 jsonl**）：

```
EXP-A  空 history + 24 次全綠採集（同一 UTC 日）
       -> records written by 24 runs = 1
       -> observation_days=1, green_streak=1
```

**主控判讀成立**：24 次只留 1 筆。但實測揪出**更嚴重的第二層**：

```
EXP-B  23 次綠(p95=45) 之後 1 次紅(p95=63)  -> 存活紀錄 = RED-last, green_streak=0
EXP-C  1 次紅(p95=63) 之後 23 次綠(p95=45)  -> 存活紀錄 = green22,  green_streak=1
```

去重是 **last-write-wins（位置決定，不是取最差／最好／中位數）**。所以每小時跑 24 次不只是白燒 CPU：
**當天最後一次跑剛好抖一下，前面 23 次好結果全部被丟掉，整天記為紅，streak 歸零。**
提高頻率會**提高**「當天被一次抖動毀掉」的機率——**它是負收益，不是零收益。**

### 2.4 任務 1 補充：720 次的實際產出 ≈ 30 次（效率比 4.2%）

```
measured nightly wall time (2026-07-31 log, 02:00:02 -> 02:07:47) = 7.8 min
1/day  = 30 runs/month : AC4 records <= 30, productive 100.0%, CPU  3.9 h/month
24/day = 720 runs/month: AC4 records <= 30, productive   4.2%, CPU 93.0 h/month, 690 runs wasted
```

- **AC4**：UTC 日上限 1 筆 ⇒ 一個月最多 30 筆，與頻率無關。
- **mutation**：ADR-SD09-011 起按 `source_sha256` 去重 ⇒ 源碼沒改，跑 720 次仍是 1 筆。**與頻率的相關性精確為 0。**
- **obs / drift**：同樣 M-05 同 UTC date 去重 ⇒ 同樣上限 30。
- **其餘 stage**（local-ci-gate / perf / chaos）無累積帳本，純重複。

⇒ **一個月多燒 89 小時的 20 核 CPU，換到的紀錄數是 0 筆。**

### 2.5 任務 3 前提複核：主控的「捕捉率 7/8 已飽和」——結論對，但機制不是這個

我用**實際 nightly log 檔**（比開機事件更直接：它證明「量測真的跑了」）交叉比對，得到與主控不同的中間數，但**強化**了主控的結論：

```
trailing-14-UTC-day window (2026-07-21 .. 2026-08-03)
  nightly runs = 14   distinct LOCAL days = 10   distinct UTC buckets = 7
    UTC 2026-07-22: 2 runs  <-- COLLISION, 1 discarded
    UTC 2026-07-24: 2 runs  <-- COLLISION, 1 discarded
    UTC 2026-07-27: 6 runs  <-- COLLISION, 5 discarded
    UTC 2026-07-28/29/30/08-01: 1 run each
  => 14 runs collapsed into 7 records (7 discarded = 50%)
```

**丟失的 7 筆不是因為機器在睡覺，是因為兩次跑撞進同一個 UTC 桶。** 補跑機制（`StartWhenAvailable`）確實有效——8/1 冷開機後 10:18 補跑，log 在案。

**機制解剖（本輪新發現，§6 R3 列為獨立缺陷）**：本機 UTC+8，`02:00 本地 = 前一天 18:00 UTC`。所以
- 「本地 D 日凌晨 2 點」的 nightly，記在 **UTC D-1** 的桶；
- 「本地 D-1 日傍晚」的臨時跑（10:00–16:00 UTC），記在 **同一個 UTC D-1** 桶。

⇒ **02:00 這個時刻讓排程跑去跟「前一晚的工作跑」搶同一格，而且它比較晚、必定覆蓋掉對方。** 實測驗證：

```
EXP-E  local 2026-07-22 18:35 -> UTC 2026-07-22 10:35 (bucket 07-22)
       local 2026-07-23 02:00 -> UTC 2026-07-22 18:00 (bucket 07-22)   <-- 同桶
       => 兩個本地日、一筆紀錄（後者覆蓋前者）

EXP-D  local 2026-07-15 02:00 -> UTC 2026-07-14 (bucket A)
       local 2026-07-15 10:00 -> UTC 2026-07-15 (bucket B)
       => 同一個本地日、兩筆紀錄
```

即 **UTC 桶的邊界在本地 08:00**，與「一天一筆」的直覺完全錯位：同一個本地日可以進兩筆，兩個本地日可能只進一筆。

### 2.6 任務 3 結論：加 trigger 救不了 AC4（反事實模擬）

假設在每個「機器活著的本地日」09:00 再加跑一次（logon trigger）：

```
filled now             : 07-22,07-24,07-27,07-28,07-29,07-30,08-01           ->  7/14
filled + logon trigger : + 07-23,07-25,07-31                                 -> 10/14
STILL EMPTY            : 07-21, 07-26, 08-02, 08-03  (機器根本沒開，任何 trigger 都無效)
```

**7 → 10，仍然不是 14。** 而且這 +3 是靠**鑽 UTC 邊界的漏洞**拿到的（同一本地日塞兩桶，§2.5 EXP-D），等於偷偷把「14 天跨度」砍半——**是漏洞，不是特性**。

⇒ **無論加多少 trigger，都無法讓「機器關機的那幾天」長出紀錄。判準不改，AC4 就是解不開。**

### 2.7 任務 3 真正的發現：R69 的修復從來沒被套到線上任務

`-Status` 唯讀實查（2026-08-03）：

```
=== AutoClaude_Nightly ===
  LogonType=S4U  ExecTimeLimit=PT72H  MultipleInstancesPolicy=IgnoreNew   <-- 應為 PT4H / StopExisting
=== AutoClaude_WindowsSmoke ===
  LogonType=Interactive  ExecTimeLimit=PT72H  MultipleInstancesPolicy=IgnoreNew  <-- 三項全錯
```

`tools/install_windows_nightly.ps1` 的**原始碼是對的**（R69 已補 `-Principal S4U`／`-ExecutionTimeLimit 4h`／`Set-MultipleInstancesStopExisting`），但**沒有人以系統管理員身分重跑過它**，所以線上任務仍是舊設定。

這正好解釋 8/2 那個空桶：

```
logs/nightly_2026-08-01_101807.log   started 2026-08-01 10:18, ended 2026-08-02 21:54  (35.6 h)
```

該實例被睡眠凍住 35.6 小時，在 PT72H 額度內存活 ⇒ 8/2 02:00 的觸發被 `IgnoreNew` 直接丟棄 ⇒ **UTC 08-02 零紀錄**。套上 PT4H + StopExisting 後這個洞會關上。

### 2.8 為什麼使用者以為「早就過了」——log 真的這樣印

```
[2026-08-02 21:54:03][INFO] END observation progress: ... ac4=41/14 (delta=1; stage=0) ...
```

**`ac4=41/14`** ——分子是整檔列數（41），分母是門檻（14）。任何人讀到都會判定「超標三倍、早就過了」。實際閘門看的是滾動 14 日曆天窗，是 **7/14**。

此缺陷 R69 已在 `run_local_nightly.ps1` 修掉（`Get-Ac4Gate` 取真實滾動窗，:1275-1279），但**最近一次跑完的 nightly 是 8/1 那輪，用的還是舊格式**，所以使用者手上最新的 log 仍寫著 `41/14`。**這是「測試應該過了吧」這個印象的直接來源，不是誤記。**

---

## 3　Decision（決策）

### 3.1 先講清楚：本 ADR **不**照抄 ADR-SD09-011 的藥方

011 對 mutation 軌的解法是「去重鍵 UTC date → `source_sha256`」。**這帖藥不能直接搬到 AC4**，理由是兩軌的量測性質相反：

| | mutation kill_rate | AC4 p95 latency |
|---|---|---|
| 確定性 | **確定性**：同 sha 同測試，結果必然相同 | **隨機**：同 sha 每次跑都不同（實測 44.21 ~ 55.86ms） |
| 同 sha 重跑的資訊量 | **零**（故按 sha 去重是對的） | **正的**（每次都是一個新的獨立樣本） |
| 適合的去重鍵 | source_sha256 | **不能用 sha**——會把真正獨立的樣本丟掉 |

⇒ 對 AC4 而言，「按 sha 去重」反而會**削弱**證據強度。**同構的是病（日曆綁定），不是藥。**

### 3.2 採納：obs/drift 既有且已驗證的 gap-tolerant streak

**核心改動只有一處——把「落在最近 14 個日曆天內」換成「連續 14 筆綠紀錄」：**

```
現行： observation_days = len(filter_recent(records, days=14)) >= 14   # 零缺口才可能成立
改為： green_streak     = 連續綠紀錄數（自尾端往前，遇紅中斷）        >= 14
```

**為什麼這是最強的方案（優於題目給的 (a)~(d) 四個候選）：**

1. **反作弊零改動**——UTC-date 去重（M-05）**原封不動保留**。不需要為「放寬」辯護，因為根本沒放寬。題目候選 (a)(b) 都要新造一套「量測條件指紋」去重鍵，那是新的攻擊面、也是新的漂移點。
2. **時間跨度自動保住**——因為 M-05 保證「一個 UTC 日最多 1 筆」，所以「14 筆」**在數學上蘊含「≥ 14 個不同的 UTC 日期」**，跨度一天都沒少。**唯一被移除的就是「這 14 天必須相鄰」。**
3. **不是新發明，是 repo 內已在同一台機器上運行中的判準形式**（**本項於 2026-08-03 訂正後重寫，論證仍成立——理由如下**）：
   - **形式已在 production 運行**：obs 與 drift 兩支 checker 用的就是同一顆 `_compute_green_streak`（自尾端往前數連續綠、遇紅中斷、不做任何日曆過濾）。
   - **「容缺口仍能累積」已被實測**：obs 42 連綠橫跨 74 天／容忍 32 缺口日；drift 26 連綠橫跨 61 天／容忍 35 缺口日（§2.1）。
   - **「能跨過門檻」已被實測**：**obs 42/30、rc=0**。這是達標實例。
   - **「不是橡皮圖章」也已被實測**：**drift 26/30、rc=1** —— 它**沒過**，而且沒過的原因是一筆真紅（採集失敗），不是缺口。**同一顆函式一邊放行 obs、一邊擋下 drift，鑑別力當場可見。**

   ⚠️ **誠實界定**：初稿在此寫「obs 與 drift **兩軌都達標**」是錯的（見 §2.1 訂正框）。**真正達標的只有 obs 一軌。**
   但論證**不依賴「兩軌都達標」**——它依賴的是「**這個判準形式在本機是活的、會累積、能跨門檻、且擋得住真紅**」，這四點在訂正後的數據上**逐條都還站得住**，其中第四點（鑑別力）反而是**訂正後才拿到的證據**，初稿的錯誤版本反而看不到。
   Rule 7：兩個模式衝突時選比較有實測的那個——訂正後仍是 gap-tolerant 這一側有實測。
4. **實作面幾乎零風險**——`ac4_progress_check.py` 已經有 `_compute_green_streak_from_tail(records, _is_green)`，且已在算 `green_streak`（現值 7）。改的是**達標條件用哪個變數**，不是新增演算法。

### 3.3 具體改動（三處，signoff 後才動）

| # | 位置 | 改動 |
|---|---|---|
| ① | `ac4_progress_check.py::evaluate` | 達標條件由 `n < OBSERVATION_DAYS` → `green_streak < OBSERVATION_REQUIRED_RUNS`。`filter_recent` **不再用於閘門**（改為讀全史）；`observation_days` 欄位保留但降為**資訊欄**（避免破壞既有 JSON 消費者） |
| ② | 同上 | `recall_sigma` 改由「最近 14 筆計數紀錄」計算（現行是「14 日曆天窗內紀錄」）。σ 的統計內容不變，只是取樣集合從「日曆窗」換成「最近 N 筆」——**這一項才是真正的漂移守門，必須保留** |
| ③ | `ac4_nightly_collector.py` | **零改動。** M-05 去重原樣保留 |

`OBSERVATION_DAYS = 14` 的**數值不變**，只改計量單位：從「日曆天」變「綠紀錄筆數」（與 011 §2.3「只改 7 的計量單位」同精神）。建議同時更名為 `OBSERVATION_REQUIRED_RUNS` 並保留舊名別名，避免名稱繼續誤導。

### 3.4 立即效果（若 signoff 通過）—— 已用真實歷史記憶體內模擬驗證

新舊判準對同一份 `.ac4_history.jsonl`（**42 筆**）的實跑對照（**production code 未修改**，
提案規則僅在記憶體中以既有的 `_compute_green_streak_from_tail(rows, _is_green)` 模擬）。
**本區塊已於 2026-08-03 Architect 複審輪重跑，對齊 02:00 nightly 寫入後之現值**（初稿為 41 筆／7 天）：

```
total records = 42
CURRENT  rule: {'status': 'observing', 'observation_days': 8, 'green_streak': 8,
                'ready_for_labeled_pr': False}
          reasons: ['觀察期未滿（8/14 天）']
PROPOSED rule: green_streak=42/14  recall_sigma(last14)=0.0000<=0.02 -> ready=True

sanity: every record green? True | distinct UTC dates for last 14 counted = 14
```

三件事同時被這段輸出證實：
1. **AC4 當場 ready**（42 ≥ 14），不需要再等任何一天；
2. **σ 守門仍然通過且仍在守**（0.0000 ≤ 0.02）——漂移偵測沒有被繞過；
3. **時間跨度確實保住**——被計入的最近 14 筆落在 **14 個不同的 UTC 日期**上（§4.1 的推論得到實測確認，不是紙上推導）。

這不是「放水放過」——它反映的是**已經累積了 42 筆綠證據**這個事實，比門檻要求的 14 筆多出兩倍。

> 🔴 **但這段輸出證實不了第四件事**：它**沒有**證明「採集停擺時判準會擋下來」。
> 上面這份 history 恰好是新鮮的（最新一筆為昨日），所以看不出差異。
> 把同一份資料的 timestamp 整批往前推一年，提案判準**照樣回 `ready=True`**（§1.4 訂正框實測）。
> ⇒ **本節的綠燈只證明「已累積的真證據夠多」，不證明「判準還有 liveness」。** 後者由 §7.1 **L-7** 負責。

---

## 4　反作弊論證（硬要求，逐項回答）

### 4.1 同一個 sha、同一組條件重跑，為什麼不會被重複計數

**因為 M-05 的 UTC-date 去重完全沒動。** 一個 UTC 日內不論跑 1 次或 720 次，`append_history` 只留 1 筆（§2.3 EXP-A 實測：24 次 → 1 筆）。
⇒ 累滿 14 筆的**下限仍是 14 個不同的 UTC 日期**，與現行判準的證據密度**完全相同**。

### 4.2 有沒有辦法在一小時內灌滿 14 筆？——**沒有**

這正是本方案優於題目候選 (a)~(d) 的地方。(a)(c)(d) 都把去重鍵換成某種「證據指紋」，於是「一小時內灌滿 14 筆」在它們底下是**做得到**的，才需要去辯論那算特性還是漏洞。

本方案不需要這場辯論：**M-05 在，一小時內物理上只能產生 1 筆。**

至於題目提示的那個統計論點——「對 p95 這種統計量，14 次獨立 run 本來就不弱於 14 個日曆天」——我的判定是：

- **對「p95 是否穩定低於門檻」這個問題：論點成立。** 14 次獨立抽樣估計分位數，與分散在 14 天抽 14 次，統計效力相同甚至更好（少了日間 nuisance factor 的混淆）。
- **對「p95 會不會隨時間慢慢劣化」這個問題：論點不成立。** 熱累積、磁碟填充、相依套件更新這類漂移，只有時間跨度看得到；一小時內的 14 次完全看不到。而 checker 裡的 `recall σ_14d` 守門**就是**衝著漂移來的。

⇒ 所以**時間跨度必須保留**，而本方案靠「M-05 不動」免費保住了它。**論點成立的那一半我採用（所以敢移除「連續」），不成立的那一半我不採用（所以不移除「跨度」）。**

### 4.3 強度對照

| 防護目標 | 現行機制 | 本方案 | 強度 |
|---|---|---|---|
| 同日重跑刷筆數 | UTC-date 去重（M-05） | **完全相同**（未改動） | **相同** |
| 要求時間跨度 | 14 筆落在 14 日曆天內 | 14 筆 × 每 UTC 日上限 1 筆 ⇒ ≥ 14 個不同日期 | **相同** |
| 要求連續無缺口 | 有 | **移除** | **第一處放寬——它不防任何攻擊，只防「使用者天天開機」** |
| 🔴 **證據新鮮度 / liveness** | **14 筆須落在最近 14 個日曆天內**（`filter_recent` 隱含 recency：紀錄一舊，窗內筆數自動掉下去） | **無**（`filter_recent` 退出閘門路徑後，`evaluate()` 內再無任何「現在」的參照） | 🔴 **這是第二處放寬，且與安全有關** — 採集器無聲死掉時 `green_streak` 永久凍結、`ready` 永久為 `True`。實測：一年前的舊資料回 `ready=True`（§1.4 訂正框）。**必須由 L-7 獨立 staleness 判準補回** |
| 一次抖動誤判 | 該日最後一次跑決定全天（§2.3 last-write-wins） | 同（未改動） | 相同 |
| 漂移偵測 | recall σ over 14 日曆天窗 | recall σ over 最近 14 筆 | **相同**（樣本數相同、跨度相同） |
| 人工最終閘 | PM signoff | PM signoff | **不變** |

**本方案放寬了兩處**：
1. **「缺口零容忍」** —— 與安全無關，這是本 ADR 刻意要拿掉的東西；
2. 🔴 **「證據新鮮度」** —— **與安全有關，是非預期的連帶損失**。移除 `filter_recent` 的動機是拿掉「相鄰」，但它同時是 `evaluate()` 唯一的時鐘參照，所以連 recency 一起被移走了。

> ⚠️ **本節初稿寫的是「本方案唯一放寬的，是與安全無關的『缺口零容忍』」——該句為假，已於 2026-08-03 依 Architect 實測訂正。**
> **PM 於 2026-08-03 拍板時看到的是那個不完整的版本**（§7.0 拍板紀錄「反作弊零改動」一列同步加註）。
> 拍板**方向**（gap-tolerant）不受影響——§2.1 的實測依據未被動搖；但**放寬幅度的揭露**必須補完，且落地時**必須連 L-7 一起做**，否則就是拿掉一道防線而不補。

---

## 5　Migration（既有 42 筆歷史怎麼處理）

比照 ADR-SD09-011 §4 的方案 A 精神，但**本案更簡單——不需要任何資料遷移**：

- 去重鍵沒改 ⇒ jsonl schema 沒改 ⇒ **既有 42 筆原樣可用，不需壓縮、不需備份、不需 `--migrate` 旗標。**
- 這是「藥方不同」帶來的額外好處：011 因為換了去重鍵，才必須做一次性壓縮並備份 `.pre_sd09_010.bak`。

**唯一要處理的是「誠實性檢查」**：改判準後 AC4 立刻 ready（§3.4）。必須確認這不是「假鎖定」：

**2026-08-03 全 42 筆逐欄複跑**（欄名以 jsonl 實際 key 為準——初稿寫的 `cb_open` 在檔內**不存在**，真實欄名是 `circuit_breaker_open_count`；`ac4_progress_check.py:185/210/256` 讀的也是後者）：

```
records=42  distinct_utc_dates=42  span_days=74
all status==pass: True
p95 range: [44.21, 55.86]
all recall>=0.95: True | circuit_breaker_open_count: Counter({'0': 42})
```

- 42 筆全部 `status=pass`、`recall ≥ 0.95`、`circuit_breaker_open_count=0`、`p95 ∈ [44.21, 55.86] < 60ms`；
- 42 筆分佈在 **42 個不同 UTC 日期**、跨度 **74 天**。

⇒ **證據是真的，且遠超門檻要求。不是放水。**

⚠️ **但「證據是真的」只回答了「過去累積的夠不夠」，沒回答「將來採集停了會怎樣」。**
後者是 §1.4 訂正框揭露的 liveness 缺口，由 **L-7** 負責，**不在本節的誠實性檢查射程內**。

建議 signoff 時一併確認：是否要在切換當下印一行 `[MIGRATION]` 取證（記錄切換**當下**的舊口徑 `observation_days/14` 與新口徑 `green_streak/14`，**不寫死數字**——本 ADR 起草期間該對數字已由 `7/14 → 41/14` 變成 `8/14 → 42/14`，寫死必過期），供日後稽核。

---

## 6　Consequences / 風險

### 正面
- AC4 解除死鎖，W1 可啟動（超期 38 天止血）。
- 判準從「量使用者作息」回到「量系統品質」。
- 三軌（AC4／obs／drift）判準語意統一，少一個認知負擔與漂移點。
- 零資料遷移、**去重反作弊機制零改動** ⇒ 資料層落地風險極低。
  ⚠️ **不等於「整體零風險」**：liveness 是被連帶移除的（§4.3 第二處放寬），**風險由 L-7 承接**。

### 風險 / 待驗

- **R1｜`filter_recent` 退出閘門路徑後可能變成 dead code。** 須確認其他呼叫站（含 `run_local_nightly.ps1` 的 `Get-Ac4Gate`）；若無人使用則明確標註或移除，不留半死函式。**`Get-Ac4Gate` 目前解析的正是滾動窗語意，改判準後必須同步**，否則 nightly log 又會印出與閘門不一致的數字（§2.8 同型缺陷復發）。
  🔴 **2026-08-03 補充（此風險比初稿寫的嚴重一級）**：`filter_recent` **不只是「窗口過濾器」，它是 `evaluate()` 唯一的時鐘**（`:141`，全檔唯一 `datetime.now()`）。
  把它當成單純的 dead-code 清理來處理，就會在毫無警覺的情況下把 liveness 一起刪掉。**處置一律走 L-7，不得只做「標註／移除」了事。**
- **R5｜🔴（本輪新增，最高優先）採集停擺時判準永久假綠。** 見 §1.4 訂正框實測（一年前資料 → `ready=True`）。**緩解＝L-7；未落地 L-7 前不得只落地 L-1。**
- **R2｜既有測試會紅。** `tests/tools/test_ac4_progress_check.py` 與 `tests/contract/test_ac4_progress_check.py` 都鎖了現行語意，須同步更新並做受控突變驗牙（注入退化→必紅／還原→必綠）。
- **R3｜（獨立缺陷，本 ADR 不修，僅登記）UTC 桶邊界與本地日錯位。** §2.5 實測：02:00 本地的排程跑會記進**前一個** UTC 日，並覆蓋掉前一晚的工作跑（實測窗內 14 跑 → 7 筆，50% 被丟）。這同時是
  - 一個**證據流失**問題（合法量測被覆蓋），與
  - 一個**漏洞**（同一本地日可塞進兩個 UTC 桶，§2.6）。

  可選解法：去重鍵 UTC date → 本地 date；或把排程時刻移離本地 08:00 邊界。**兩者都動到反作弊鍵，屬 ADR 級，請於 signoff 時裁示要不要另開一輪處理。本輪刻意不動。**
- **R4｜本 ADR 屬判準級語意變更**，須 PM signoff（§7）。

### Rejected alternatives

- **維持現狀**：期望達標 1.5~89 年（§2.5），等同永不達標。否決。
- **提高觸發頻率（每小時／24 次一天）**：實測產出 0 筆、CPU +89 h/月，且 last-write-wins 使抖動風險上升（§2.3、§2.4）。**負收益，明確否決。**
- **候選 (a)/(c)/(d)「量測條件指紋」去重鍵**：需新造指紋、開啟「一小時灌滿 14 筆」的辯論、需資料遷移，且**沒有任何一項比本方案多解決一個問題**。否決。
- **照抄 011 的 source_sha256 去重**：對隨機量測會丟掉真正獨立的樣本（§3.1）。否決。
- **降低門檻 14 → N**：治標，仍綁日曆連續，機器一關機照樣重來。否決。

---

## 7　✅ SIGNOFF 紀錄（PM 已拍板）＋ 🔴 落地清單（尚未實作）

### 7.0 PM 拍板紀錄

| 項目 | 內容 |
|---|---|
| **拍板日** | **2026-08-03** |
| **拍板者** | PM／掌舵者 |
| **採用方案** | **§3.2 gap-tolerant green_streak** —— 以「連續 14 **筆**綠紀錄」取代「14 筆須落在 14 個**連續日曆天**」 |
| **門檻數值** | **維持 14**（只改計量單位：日曆天 → 綠紀錄筆數） |
| **反作弊** | **去重機制零改動** —— M-05 的 UTC-date 去重原封不動保留。因每 UTC 日上限 1 筆，「14 筆」數學上仍蘊含「≥ 14 個不同 UTC 日期」，**時間跨度一天沒少**；移除的是「必須相鄰」。<br>🔴 **2026-08-03 訂正：拍板當下所依據的「反作弊零改動／唯一放寬與安全無關」表述不完整。** 實測另有**第二處放寬＝證據新鮮度（liveness）**：`filter_recent` 退出閘門後，`evaluate()` 再無時鐘參照，採集器無聲死掉時會**永遠回報 ready=True**（§1.4 訂正框、§4.3 強度對照表）。**方向不改**（gap-tolerant 仍採用），但**落地必須連 §7.1 L-7 獨立 staleness 判準一起做**，否則等於淨拆一道防線 |
| **拍板依據實測** | 套用後 `green_streak=42/14`、`recall_sigma=0.0000 ≤ 0.02`、`ready=True`（§3.4 記憶體內模擬，production code 未改；**2026-08-03 重跑值**，拍板當下為 41/14） |
| 🔴 **落地狀態** | ✅ **LANDED — 2026-08-04（R74）**。`tools/ac4_progress_check.py` L-1~L-5 ＋ L-7 全數落地；`tools/run_local_nightly.ps1` L-6 同輪同步；兩支測試檔更新並附雙向鑑別力取證。落地當回合實測見 §7.6。🔴 **L-7 判準已於 R75 修正**（staleness 取樣改「最後一筆真量測」、未來時間戳改 `clock_anomaly` fail-closed、新增「認證前窗內須有指標變異」必要條件，並分離 `caveats`／`reasons`）——現行判準見 L-7 末「R75 同步」小節，R75 重驗仍為 `ready`（見 §7.6）。🔴 **「已達標」這句宣稱的證據不可攜**：觀察期紀錄 `AutoClaude/.ac4_history.jsonl` 為 untracked、只存在於產出它的那台機器上 ⇒ 讀本列與 §7.6 的數字前先讀 §7.6 的 **provenance 揭露**段（該段同時載明「本輪不改此設計」的理由與承接觸發點） |

> **拍板與落地為何分兩輪（史料，已結束）**：拍板輪刻意不動 code，因為判準變更必須配
> 「注入退化→必紅／還原→必綠」的雙向鑑別力驗證，而 `run_local_nightly.ps1` 當時由他人持有。
> 落地輪（R74）已把兩件事一起做完：判準改動與測試鎖同輪落地，且鎖的鑑別力以受控突變當回合實證
> （§7.6）。**本節自此為交接完成紀錄，不再是待辦單。**

### 7.1 🔴 精確落地清單（交下一輪執行）

> **📌 行號引用政策（2026-08-03 實測教訓）**：本節對 `tools/ac4_progress_check.py` 的行號為 **2026-08-03T02:57Z 實查值**（該檔本輪無人改動，可信）。
> 對 `tools/run_local_nightly.ps1` **一律只給函式／錨點名稱、不給行號** —— 該檔**正被其他輪次同時編修**（本輪實測：`mtime 2026-08-03 11:01:24`，行數由 1,345 → **1,546**，`Get-Ac4Gate` 由 489 位移至 **549**）。**對移動中的檔案寫死行號，等於寫進一個必定過期的引用。**

#### L-1　`tools/ac4_progress_check.py::main()`（實查行號 **406-408**）

```python
records = load_history(args.history)
recent = filter_recent(records)                      # ← 閘門不再吃這個
report = evaluate(recent, tolerant_p95_ms=...)       # ← 改傳全史 records
```
- **改法**：`evaluate()` 收**全史** `records`；`filter_recent()` 的結果降為**資訊欄**用途。
- ⚠️ **`filter_recent()` 不可直接刪** —— 見 L-4 的 `observation_days` 語意衝突；它仍要供資訊欄計算。

#### L-2　`tools/ac4_progress_check.py::evaluate()`（實查行號 **354-357**）

```python
elif n < OBSERVATION_DAYS:                                       # ← 移除此分支（n 將變成全史長度）
    reasons.append(f"觀察期未滿（{n}/{OBSERVATION_DAYS} 天）")
elif green_streak < OBSERVATION_DAYS:                            # ← 保留，成為唯一閘門
    reasons.append(f"連續全綠不足（{green_streak}/{OBSERVATION_DAYS} 天）")
```
- **改法**：刪除 `n < OBSERVATION_DAYS` 分支；`green_streak < OBSERVATION_DAYS` 成為**唯一**達標閘門。
- 文案「天」→「筆」（`連續全綠不足（{green_streak}/{N} 筆）`），避免單位繼續誤導。
- 常數建議更名 `OBSERVATION_DAYS` → `OBSERVATION_REQUIRED_RUNS`，**保留舊名為別名**（`OBSERVATION_DAYS = OBSERVATION_REQUIRED_RUNS`）以免打斷既有 import。

#### L-3　`recall_sigma` 取樣集合（實查行號 **334-338**）

```python
recalls = [r["recall_at_10"] for r in records if r.get("recall_at_10") is not None]
```
- 全史傳入後這行會變成**對 42 筆算 σ**，等於偷偷放大取樣窗、削弱漂移守門。
- **改法**：改為 `records[-OBSERVATION_REQUIRED_RUNS:]` 切片後再取 recall，**維持「最近 14 筆」**。
- 🔴 **這是本次落地最容易漏掉、且會靜默削弱反漂移的一處。**

#### L-4　🔴 **`observation_days` 語意衝突（最大地雷，必須先決策）**

`evaluate()` 內 `n = len(records)`（實查行號 **307**）直接成為輸出欄 `observation_days`（實查 **366**）。改傳全史後 `observation_days` 會從 **8 變成 42**。**下游有兩個真實消費者**：

| 消費者 | 錨點（不給行號，理由見上方政策框） | 讀取欄位 | 改判準後的後果 |
|---|---|---|---|
| `run_local_nightly.ps1::Get-Ac4Gate` | `$result.Days = [int]$parsed.observation_days` | `observation_days` | `END observation progress:` 進度行會印成 `ac4=42/14 rolling-window-days` |
| `run_local_nightly.ps1` G0 **四軌**判定 detail（R71 G-3 後為 mutation／ac4／obs_ga／drift 四軌） | `$ac4Numerator`（`[G0-READY]`／`[G0-NOT-READY]` 行） | 同上 | `[G0-*]` 行同樣印 42/14 |
| `run_local_nightly.ps1` F2 區塊 | `Log "[F2 OK] AC4 觀察期 #2 累計中 … days=$($ac4Json.observation_days)"` | 同上 | `days=` 一併失真 |

⇒ **若不處理，會精準復刻 §2.8 那個「`ac4=41/14` 看起來超標三倍」的假達標誤導** —— 而 §2.8 正是 R69 剛修好的缺陷。**同型缺陷復發，且是我們自己造成的。**

**建議處置（擇一，須於落地輪拍板）**：
- **(a)【建議】語意凍結**：`observation_days` **維持原義**＝`len(filter_recent(records))`（滾動窗計數，資訊欄），另加**新欄** `green_streak_required` / `gate_basis="green_streak"`，`Get-Ac4Gate` 改讀 `green_streak`。**下游零破壞、語意不漂移。**
- (b) 重新定義 `observation_days` 為全史筆數，並**同步**修改 `Get-Ac4Gate` 與進度行文案（`rolling-window-days` → `green-streak-runs`）。**需與 `run_local_nightly.ps1` 持有者協調。**

#### L-5　`all_true_skip` 判定範圍（實查行號 **331**）

`all(r.get("status") == "skip" for r in records)` 改吃全史後語意由「窗內全 skip」變成「**史上全 skip**」。實務上只在冷啟動期成立，但**屬語意變更，須在落地輪明示並補一個 case**。

#### L-6　`run_local_nightly.ps1` 同步（**本輪射程外，需主控協調**）

三個錨點：`function Get-Ac4Gate` ＋ `END observation progress:` 進度行 ＋ `[G0-READY]`／`[G0-NOT-READY]` detail 行。依 L-4 選 (a) 則改動極小（`Get-Ac4Gate` 改讀 `green_streak`）；另需認得 L-7 新增的 `status='stale'`。

⚠️ **該檔本輪由他人持有且正在變動中**（2026-08-03 實測 mtime `11:37`、行數 **1,611**；ADR 初稿當下為 1,546、更早為 1,345）。
**切勿與 D-4（§8.3 deadline 逾期偵測）的改動在同一輪各改各的** —— 兩者都動這支檔，會衝突。
落地前**必須重新 grep 錨點**，不可沿用任何歷史行號。

> ✅ **參考範本已存在**：R71 已把該檔的 mutation／obs／drift 三軌改成「向權威工具現場提問」的形狀
> （`Get-MutationLockGate` → `should_lock`、`Get-DriftGaPass`／`Get-ObsGaPass` → `--json` + rc↔status 一致性檢查，三態 `Ok/Pass/Error`）。
> **AC4 軌照同一形狀改即可**，不需重新設計。

#### L-7　🔴 **`evaluate()` 增設獨立的 staleness 判準（補回被連帶移除的 liveness）**

> **為何非做不可**：L-1 把 `filter_recent()` 移出閘門路徑，而它是 `evaluate()` **唯一參照「現在」的項**
> （`tools/ac4_progress_check.py:141`，全檔僅此一處 `datetime.now()`）。移走後達標退化為**純檔案內容函式**：
> 採集器無聲死掉 → `green_streak` 永久凍結 → `ready` 永久為 `True`，**且無人會察覺**。
> 實測：一年前的舊資料在提案判準下回 `ready=True`（§1.4 訂正框）。
> **L-7 不是可選加強，是 L-1 的配套。少了它，本 ADR 就是「拿掉一道防線而不補」。**

- **改法（R74 提案原文，取樣集合已於 R75 收窄 ⇒ 現行判準見本節末「R75 同步」）**：
  `evaluate()` 內新增一道**與 green_streak 無關的獨立判準**——
  取最新一筆的 timestamp，若距今 > `STALENESS_MAX_DAYS` 則 `status='stale'`、`ready=False`、
  並在 `reasons` 寫出「證據過期／採集可能已停擺」。
- **N 的取法（🔴 別重蹈日曆綁定）**：建議 `STALENESS_MAX_DAYS = 30 ~ 42`（＝ window 14 的 **2~3 倍**）。
  **理由**：這台機器 8 月只活 2 天（§2.5/§2.6 實測，近 75 天活 52 天、7/22、7/29、8/1 各一次冷開機）。
  N 取太小（例如 14）等於把剛拆掉的「機器要天天開機」換個名字裝回來，**AC4 會再次卡死**。
  N 的職責只有一個：**區分「使用者放了個長假」與「採集器死了」**，不是重新量作息。
- **判準要獨立**：`stale` 必須是**獨立分支**，不可寫成 `green_streak` 的修正項——
  green_streak 反映「證據夠不夠」，staleness 反映「證據還算不算數」，兩者混在一起就會重演本次「一個變數兼兩個職責」的病。
- **落地輪必做的雙向取證**：把 `.ac4_history.jsonl` 複製一份到 scratchpad、timestamp 整批減 400 天 →
  **必須 `status='stale'`、`ready=False`（紅）**；改回原值 → **必須 `ready=True`（綠）**。**兩次輸出都要貼。**
- **測試鎖**：`tests/tools/test_ac4_progress_check.py` 補 ≥ 3 case（新鮮／剛好在 N 邊界／超過 N）；
  `tests/contract/` 補 `status='stale'` 的 schema case。
- ⚠️ **`stale` 是新的 status 值**，`Get-Ac4Gate` 與 `[G0-*]` 判定需一併認得它（併入 L-6 一起做，**不可只認 `ready`**——
  否則 nightly 會把 stale 印成單純的 not-ready，人看不出「是採集死了」還是「還在累積」）。

##### 🔴 L-7 的 R75 同步（現行判準；本小節與 `tools/ac4_progress_check.py` 實查一致）

R74 版 L-7 只堵住「**沒有新列**」那一半，而本 ADR 記載 L-7 要防的是「`ready` 永久凍結」。
R75 三項變更（前兩項是修判準的取樣與邊界、第三項是**新增一條收緊條件**，不是放寬）：

1. **staleness 量的是「最後一筆真量測」，不是「最後一筆紀錄」**（`_is_measurement()`＝
   `status != "skip"`；`pass`／`fail` 都算量測，只有 `skip` 不算）。
   **理由**：PG／Docker 不可用時採集器**每晚照樣寫入一筆帶當日 timestamp 的 `status="skip"`**
   （`run_local_nightly` 另建 `.docker_skip_streak` 計數器，證明這是常態而非邊角）。而 `skip`
   對 `green_streak` 是中性（不累計也不中斷）、對舊 staleness 卻算一筆新列 ⇒ **streak 凍在
   達標值、staleness 恆保新鮮 ⇒ `ready` 永久為真且無人察覺**——正是 L-7 立判準時逐字要防的
   狀態，換了個入口重演。一句話：**量「有沒有新紀錄」量到的是採集器心跳，量「有沒有新量測」
   量到的才是證據新鮮度。**
   `skip` 對 `green_streak` **維持中性不動**（不碰 P0-02 的三態 sentinel）——職責分離。
2. **負值（未來時間戳）不得夾成 0**：改報新欄 `clock_anomaly=True` 並 **fail-closed 判 stale**。
   夾負值會讓時鐘偏移／手改檔案的資料恆為「距今 0 天」＝永久新鮮，採集器死掉也不轉 stale，
   而本判準自陳是「必要條件、不是加分項」。
3. **新增：認證前必須看到「重新量測過」的痕跡**（收緊）。`green_streak` 已達標時，若窗內
   有 ≥2 筆可比量測卻**任一指標都沒有出現變異**，一律不 ready。擋的是 stuck writer／每晚
   複製上一筆——那種資料上 `recall σ = 0` 不構成反漂移證據（σ 讀 0 是「沒變」而不是「驗過
   了」）。⚠️ 判準內容本身**不改**：recall 對固定語料＋固定索引是確定性量測，σ=0 是正常
   讀數，其鑑別力是**前瞻的**；故改的是「把這件事講出來」＋補一條 liveness 必要條件。

**新增可讀欄位**（皆為資訊欄／診斷用，非閘門，除 `clock_anomaly` 參與 fail-closed）：
`measured_records`（全史真量測筆數）、`record_staleness_days`（最後一筆**任何**紀錄距今天數
——與 `staleness_days` 的**落差**即診斷依據：兩者接近 ⇒ 採集器死了、修排程／載具；record 很新
而 staleness 很舊 ⇒ 採集器活著但量測沒發生、修 PG／Docker）、`clock_anomaly`、
`recall_distinct_values`／`p95_distinct_values`／`metric_variance_observed`／
`recall_sigma_discriminating`（σ 這把尺的輸入有沒有在動）、以及 **`caveats`**。

🔴 **`caveats` 與 `reasons` 刻意分離、不得合併**：`reasons` ＝「不可升級的原因」（有它就
不 ready）；`caveats` ＝「ready 成立，但成立得有保留」。混成一個清單會產出「`ready=True`
卻列著一堆原因」那種讀不懂的輸出；而只塞進 JSON 深處不印出來，就會讓 `reasons=[]` 被讀成
「毫無保留就達標」。⇒ 上游消費者（`Get-Ac4Gate`／`[G0-*]`）判 gate 一律只看 `reasons`／
`ready`，`caveats` 與 `clock_anomaly` 是**要印給人看**的，別當成 not-ready 訊號。

### 7.2 會打到的既有測試鎖

| 測試檔 | 實查行數 | 預期衝擊 |
|---|---|---|
| `tests/tools/test_ac4_progress_check.py` | 287 行 | 鎖「觀察期未滿（n/14 天）」文案與 `n < OBSERVATION_DAYS` 語意的 case 會紅；σ 取樣改切片後，餵 > 14 筆的 case 期望值需重算 |
| `tests/contract/test_ac4_progress_check.py` | 235 行 | 鎖 JSON schema／欄位語意。若採 L-4 **(a)** 則多為**新增**欄位（相容）；採 **(b)** 則 `observation_days` 語意鎖必須改寫 |

> **落地輪必做（不可省）**：對 `green_streak` 閘門做**受控突變驗牙**——
> 於 `.ac4_history.jsonl` 尾端注入一筆 `status=fail` / `p95_ms=63` 使 `green_streak` 歸零 → **必須 `ready=False`（紅）**；
> 還原 → **必須 `ready=True`（綠）**。**兩次輸出都要貼進落地報告**。
> 沒有這道雙向取證，就等於「把門檻改鬆了，但沒有任何證據證明它還關得起來」。

### 7.3 遷移成本：**零**

- 去重鍵未改 ⇒ jsonl schema 未改 ⇒ **既有 42 筆原樣可用**；不需壓縮、不需備份、不需 `--migrate` 旗標。
- 對照 ADR-SD09-011：該案換了去重鍵，才必須做一次性壓縮並備份 `.pre_sd09_010.bak`。**本案沒有這個負擔。**

### 7.4 落地 DoD

1. L-1 ~ L-5 全數落地；L-4 先拍板 (a)/(b)。
1b. 🔴 **L-7 staleness 判準必須與 L-1 同輪落地** —— L-1 移走 `evaluate()` 唯一的時鐘參照，L-7 是它的配套而非加分項。**只做 L-1 不做 L-7 = 淨拆一道防線，DoD 不得判過。**
2. L-6 與 `run_local_nightly.ps1` 持有者協調後同步（防 §2.8 假達標復發；並須認得 `status='stale'`）。
3. 兩支測試檔更新 + **受控突變雙向取證（注入必紅／還原必綠，兩次輸出都貼）**，含 **L-7 的 staleness 雙向取證**（timestamp 整批推舊 → 必紅；還原 → 必綠）。
4. 零退化（pytest ≥ 基線、lint-imports 8 kept、LOC 0）。
5. 切換當下印一行 `[MIGRATION]` 取證（記錄切換前後 `green_streak`／`ready`），供日後稽核。
6. 文件：本 §7.0 落地狀態改為 **LANDED**（附 commit）＋ ADR-SD09-008 §v0.4 補 supersede 註記。

### 7.6 ✅ 落地實測（2026-08-04 R74 當回合真跑，非引述）

**落地前後（同一份 `.ac4_history.jsonl`，43 筆，production code 真改）**：

```
BEFORE  status=observing  observation_days=9  green_streak=9   ready=false  rc=0
        reasons=['觀察期未滿（9/14 天）']
AFTER   status=ready      observation_days=9  green_streak=43  ready=true   rc=0
        [MIGRATION] gate_basis=green_streak：新口徑 43/14 筆；舊口徑 9/14 rolling-window-days（資訊欄）
        staleness_days=0/30   total_records=43   recall_sigma=0.0
```

⇒ **AC4 觀察期即刻達標。** 卡住 W1 的不是資料量（證據多出門檻 3 倍），是拍板結果沒進 code。

🔴 **provenance 揭露（R75 補；沿用 `ONBOARDING.md` §7／§8 對 nightly 心跳檔既有的措辭體例，
刻意不自創第三種寫法）**：上面這組數字的證據檔是 `AutoClaude/.ac4_history.jsonl`，它被
`AutoClaude/.gitignore` 排除（實查：`git check-ignore -v` 命中該檔、
`git ls-files --error-unmatch` rc=1＝未追蹤）⇒ **這份紀錄 untracked，只存在於產出它的那台
機器上**（＝跑 nightly 採集的那台 Windows 11 真機）。因此：
- **不得**據此推論「任何一台 checkout 都能複現 `green_streak=43`」；
- **不得**在另一台機器上把「本機算不到那個 streak」讀成「觀察期未達標」或「採集停擺」。
  缺檔時的行為已驗為 fail-open（`status=observing`／`ready=false`／rc=0，不會假紅），
  所以在別台機器上跑這支 checker 得到的是**「這台機器沒有證據」，不是「證據不存在」**
  ——與 `DEF-101-148`「本機副作用類宣稱綁定該機器」同性質。
- 引用本節數字時一律連同「哪台機器、什麼時候」一起引，或改為現查
  （`python AutoClaude/tools/ac4_progress_check.py`）。把它當成 ADR 的常數就會重演
  `ADR-XPLAT-002` §4.3.1 已記載過的「量測 → 寫進文件 → 之後失真」。

**這個「達標證據不可攜」的設計要不要改？R75 判斷：揭露必做（即本段），設計本輪不改。**
- **改成 tracked 的代價高於收益**：這是每台機器**各自 append** 的量測流，nightly 每跑一輪就
  多一筆 ⇒ 納入版控後每天都讓工作樹變髒（而排程 job 沒有人在旁邊 commit），多機並用時
  幾乎每一行都會衝突；且它的反作弊語意（尾端往前數連續綠、遇紅中斷）建立在「單一機器的
  時序流」上，合併過的檔算出來的 streak 沒有定義。
- **雲端重建也不是現成的**：雲端側沒有等價的每日採集鏈；同型前例是 `mutation-history`
  artifact 受 GitHub retention 上限限制（見根層 `ONBOARDING.md` §9 該列，並已註明本機
  nightly 與雲端是兩個互不同步的累積點）。要讓雲端能重建觀察期證據，等於新開一條採集＋
  保存鏈，屬獨立標的、需授權，不是順手可做的事。
- **一個真正便宜的改法（讓 `ac4_progress_check.py` 自己印一行 provenance：主機名 ＋ 該檔
  untracked 的事實）本輪未做，但已有承接者**。原因不是難度，是它的 stdout 有三個既有錨點被
  `AutoClaude/tools/run_local_nightly.ps1` 的 `Get-Ac4Gate` 解析，而該檔本輪由另一個修復包
  持有 ⇒ 同輪由兩邊各自動輸出面會製造互踩型假紅。
  **承接：`run_local_nightly.ps1` 的持有者已收到轉達**，正評估上游面要不要多讀 R75 新增的
  `caveats`／`clock_anomaly`；provenance 行併入該次輸出面調整一起做（同一支解析器只動一次）。
  ⚠️ 若該次評估決定不動輸出面，本點即回到「無承接者」狀態，屆時必須在此就地改寫成
  **承接輪次：未指派** ＋ 觸發點，不得留著一句已經不成立的「已有承接者」。
⇒ 處置與 nightly 心跳檔一致（`ONBOARDING.md` §8 R12 段：跨機限制如實揭露，不強求可攜）。

🔴 **R75 判準修正後的重驗（R75 當回合真跑 `python AutoClaude/tools/ac4_progress_check.py`，
rc=0）——上面 R74 的達標宣稱在新判準下仍然站得住，但要多揭露一件事**：

```
status=ready   green_streak=44/14   measured_records=44/44   staleness_days=0/30
record_staleness_days=0   total_records=44   ready_for_labeled_pr=True
tolerant_streak=44 (p95 < 60ms)     observation_streak=1 (p95 < 50ms)
recall_sigma=0.0 (recall distinct=1, p95 distinct=14, discriminating=False)
```

- **L-7 的 R75 收窄沒有讓 AC4 退回 not-ready**：`measured_records` 與 `total_records` 相等
  ⇒ 全史每一筆都是真量測、沒有 `skip` 混充新鮮度，最新一筆就在今天（`staleness_days=0`，
  且 `record_staleness_days` 與它相等＝採集器與量測同步活著）。R75 的新收緊條件也放行
  （`p95 distinct=14`＝窗內每晚的量測值都在動，不是 stuck writer）。
- 🔴 **但「達標」的組成必須講清楚：`ready` 完全由 60ms tolerant 軌成立，50ms 觀察軌並未達標**
  （`observation_streak=1/14`）。這一點目前只出現在工具的 `caveats` 裡，本 ADR 補記於此：
  讀「AC4 觀察期已達標」時**不得**推論「p95 已穩定落在 50ms 觀察目標之內」——那是兩條不同
  的軌（升級門檻 60ms 見 `ADR-SD09-008` §v0.4 ACCEPTED；50ms 是向上相容的觀察指標，
  不影響 `ready`）。同理 `recall_sigma=0.0` 是「recall 沒變」而不是「反漂移驗過了」
  （`recall distinct=1`、`discriminating=False`），該尺的鑑別力是前瞻的。
- ⇒ 本段三個數字（`44`／`1`／`0.0`）與上方 provenance 揭露同一紀律：它們是**那台機器、
  那個時點**的量測值，引用時連同機器與時點一起引，或改為現查。

**雙向鑑別力取證（scratchpad 副本，真實 jsonl 未觸碰）**：

```
FRESH          rc=0 status=ready     green_streak=43/14 staleness_days=0   ready=True
RED-INJECTED   rc=0 status=observing green_streak=0/14  staleness_days=0   ready=False
               reasons=['連續全綠不足（0/14 筆）']          <- 尾端注入 p95_ms=63
STALE(-400d)   rc=1 status=stale     green_streak=43/14 staleness_days=400 ready=False
               reasons=['證據過期（最新一筆距今 400 天 > 30 天），採集可能已停擺']
```

**STALE 那一列是 L-7 的關鍵證據**：`green_streak` **仍然是 43**（綠證據本身照樣足夠），
卻被獨立的新鮮度判準擋下——這正是 §1.4 訂正框實測「一年前死資料回 ready=True」的反面。
若少了 L-7，這一列會回 `ready=True`。

**測試鎖驗牙（受控突變於 production code）**：把 `is_stale` 的判定改成恆假 →
`tests/tools`（2 case）＋`tests/contract`（1 case）當場紅；還原 → 39 passed / rc=0。

**L-4 決策：採 (a) 語意凍結。** `observation_days` 維持滾動窗計數（實測仍為 9，未變成 43），
另加新欄 `gate_basis` / `green_streak_required` / `staleness_days` / `staleness_max_days` / `total_records`。
下游三個消費者零破壞，且不製造第二個 §2.8 假達標。
**S4 決策：`STALENESS_MAX_DAYS = 30`**（＝§7.5 建議值；取 14 會重蹈日曆綁定）。

### 7.5 仍待 PM 裁示（本 ADR 未決）

| # | 決策項 | 建議 |
|---|---|---|
| S3 | R3（UTC 桶錯位，§2.5）本輪處理還是另開一輪？ | **建議另開一輪**（動到反作弊鍵，不與本案混同） |
| L-4 | `observation_days` 取 (a) 語意凍結 還是 (b) 重定義？ | **建議 (a)** —— 下游零破壞，且不製造第二個 §2.8 |
| **S4**（🔴 本輪新增） | **L-7 的 `STALENESS_MAX_DAYS` 取值** | **建議 30**（＝ window 14 的約 2 倍）。取 42（3 倍）更寬容、取 14 會重蹈日曆綁定。**此項需 PM 拍板，因為它決定「多久沒採集才算採集死了」——本質是風險胃納，不是技術參數** |
| **S5**（🔴 本輪新增） | 是否確認「在不完整揭露下作出的拍板」仍然有效？ | **建議：方向維持有效，但 §7.0 的 DoD 加掛 L-7 為必要條件**（本 ADR 已如此記載）。若 PM 認為 liveness 缺口足以改變決策，應在 L-1 落地前提出 |

---

## 8　任務 3：觸發器評估（結論：**不加頻率 trigger**；真正要做的是把 R69 套上線）

### 8.1 為什麼不加

主控原始假設是「02:00 對會被關機數週的筆電是最差選擇，應加開機／登入／閒置 trigger」。**實測後這個前提要修正**：

1. **補跑機制已經在工作**——`StartWhenAvailable=True` 實測有效（8/1 冷開機 → 10:18 自動補跑，log 在案）。「機器醒著卻沒跑」不是主要失分點。
2. **失分點是 UTC 桶碰撞，不是漏跑**——窗內 14 次跑只留 7 筆，丟掉的 7 筆全是「撞同一桶被覆蓋」（§2.5）。加 trigger 只會製造更多撞桶的跑。
3. **加了也到不了 14**——反事實模擬 7 → 10/14，剩下 4 天機器根本沒開（§2.6）。而且那 +3 是鑽 UTC 邊界漏洞換來的。
4. **每小時觸發是負收益**——720 次產出 ≤ 30 筆（4.2%）、多燒 89 h/月 CPU，且 last-write-wins 讓「最後一次抖動毀掉整天」的機率提高 24 倍（§2.3、§2.4）。
5. **與 `MultipleInstances` 兩種取值都不相容**：
   - `IgnoreNew`（目前線上值）：一個凍住的實例會把後續所有觸發全部吃掉（8/1 那輪 35.6 h，直接吃掉 8/2 一整天）。
   - `StopExisting`（R69 目標值）：每小時觸發會**砍掉正在跑的那輪**；nightly 正常 7.8 分鐘沒事，但只要有一輪變慢（8/1 那輪 35.6 h），就會變成「每小時砍一次、永遠跑不完」。

⇒ **依主控指示「找不到就誠實說這一項不值得做」——這一項不值得做。故本輪對 `tools/install_windows_nightly.ps1` 零改動**（該檔原始碼在 R69 後已經是正確的，見 §8.2）。

### 8.2 真正該做的：把 R69 已經寫好的修復套到線上任務

線上三項設定仍是舊值（§2.7 實查），而 installer 原始碼**早已修好**——差的只是**沒人以系統管理員身分重跑過它**。

**使用者要跑的精確指令（需「以系統管理員身分執行」開 PowerShell）：**

```powershell
# 1) 套用（會先 Unregister 再 Register，冪等）
powershell -ExecutionPolicy Bypass -File D:\CursorProject\AISDCL_Agent\tools\install_windows_nightly.ps1

# 2) 驗證憑證（三項必須變成 S4U / PT4H / StopExisting）
powershell -ExecutionPolicy Bypass -File D:\CursorProject\AISDCL_Agent\tools\install_windows_nightly.ps1 -Status
```

預期落差修正：

| 任務 | 欄位 | 現況（實測） | 執行後應為 |
|---|---|---|---|
| AutoClaude_Nightly | ExecutionTimeLimit | PT72H | **PT4H** |
| AutoClaude_Nightly | MultipleInstancesPolicy | IgnoreNew | **StopExisting** |
| AutoClaude_WindowsSmoke | LogonType | **Interactive** | **S4U** |
| AutoClaude_WindowsSmoke | ExecutionTimeLimit | PT72H | **PT4H** |
| AutoClaude_WindowsSmoke | MultipleInstancesPolicy | IgnoreNew | **StopExisting** |

這修的是 8/2 那個空桶的真正成因（凍住的實例吃掉隔日觸發），**且不需要任何判準變更**。

> ⚠️ 本 agent 無提權，`Set-ScheduledTask` 實測 Access denied，故上述為**未執行**的交付指令，不是已驗證結果。

### 8.3 mac 側對等物（**未實測**，僅設計說明）

mac 側由 `tools/install_mac_nightly.sh` 產 launchd plist，現況已有：

- `StartCalendarInterval` 02:00 —— 對應 Windows `-Daily -At '02:00'`；
- `RunAtLoad` —— 對應 Windows `StartWhenAvailable`（開機／登入載入時補跑）。

若未來 signoff 決定要加 trigger，mac 對等作法：

| 語意 | Windows | macOS launchd |
|---|---|---|
| 開機後延遲觸發 | `-AtStartup` + Delay | `RunAtLoad`（已有）；延遲需腳本內 `sleep` 或 `StartInterval` 配合 |
| 登入後觸發 | `-AtLogOn` + Delay | `RunAtLoad`（LaunchAgent 於登入時載入，語意天然涵蓋） |
| 閒置時觸發 | `IdleTrigger`（需 CIM `MSFT_TaskIdleTrigger`，`New-ScheduledTaskTrigger` 表達不出） | **launchd 無對等物**——需自行以 `ioreg`/`HIDIdleTime` 輪詢，屬額外造輪子 |
| 睡眠喚醒 | `WakeToRun` | launchd 無對等；須 `pmset schedule wake` 另行設定 |

⇒ **閒置與喚醒兩項在 mac 側沒有原生對等物**，這也是不建議往 trigger 方向加碼的一個附帶理由（雙平台對稱紀律下，Windows 加了 mac 就補不齊，會製造新的不對稱缺口）。本節結論**未在 mac 真機驗證**。

---

## 9　任務 4：nightly 平行化評估（結論：**不該平行化**）

### 9.1 實測各 stage 耗時（`logs/nightly_2026-07-31_020002.log`，非估算）

| stage | elapsed | 佔比 |
|---|---|---|
| local-ci-gate full | 00:02:35.688 | 33% |
| Docker-PG-bring-up | 00:00:00.781 | — |
| **mutation-test (Docker/Linux mutmut)** | **00:04:04.873** | **53%** |
| pg-e2e + AC4 collector | 00:00:14.718 | 3% |
| perf-baseline | 00:00:02.080 | — |
| drift_log-scan | 00:00:00.460 | — |
| observability-snapshot | 00:00:00.634 | — |
| sdd-fsm-chaos | 00:00:44.710 | 10% |
| Cleanup | 00:00:00.015 | — |
| **總計（02:00:02 → 02:07:47）** | **00:07:45** | |

### 9.2 相依關係

- `Docker-PG-bring-up` → `pg-e2e`（硬相依：PG 要先起來）。
- `pg-e2e` → AC4 collector（同 stage 內，collector 吃 pg-e2e 的 junit XML）。
- 其餘 stage（local-ci-gate／mutation／perf／drift／obs／chaos）**彼此無資料相依**，理論上可並行。

### 9.3 為什麼仍然不該並行 —— 三個理由，任一項就足以否決

**理由 1｜perf 量測會被污染，而且這是 repo 已經踩過的坑。**
`perf-baseline` 跑的是 sub-ms 量級的量測，7/31 那輪實測 `token_halt_roundtrip: 0.6ms → 0.9ms (+45.5%)`，靠 `abs_delta=0.271ms < 0.5ms` 的絕對值兜底才判 PASS。**在這個量級上，旁邊跑 mutation（Docker + 滿載編譯測試）必然把數字打爛。** 記憶檔已記載同型事故：「Nightly perf 載具偽陽性——agent PowerShell 跑 nightly perf 膨脹 ~30%」。並行化會把這個偶發偽陽性變成**每晚必然**。

**理由 2｜並行會重演「並行突變互踩假紅」。**
記憶檔 `parallel-mutation-audit-collision` 明載：mutation stage 會**就地改 tracked 生產碼**，與同時跑全套測試的 stage 互踩 → 假紅，已重演三次（DEF-67-001／improving_74／R25 四方複審），另有 pytest `__pycache__` 位元碼快取寫入競態（DEF-101-268）。`local-ci-gate`（跑 pytest 全套）與 `mutation`（改源碼跑 mutmut）**正是那對會互踩的組合**，而它們合計佔 86% 的時間——想省時間就一定得並行這兩支，也就一定會踩。

**理由 3｜省不到有意義的時間，而時間根本不是瓶頸。**
理想並行後下限 = max(2m36, 4m05, 45s) ≈ **4m05**，比 7m45 省 3m40。但 nightly 在 02:00 無人值守跑，**沒有任何人在等這 3 分 40 秒**。真正的瓶頸是 §2 全篇在講的：**判準要求機器連續 14 天開機**——省 3 分鐘對此毫無幫助。**拿「必然的量測污染 + 已重演三次的假紅」去換一個沒人在等的 3 分鐘，是明確的負向交易。**

### 9.4 「該用算力但沒用」的地方 —— 有，但不在並行

以下三項是**在單一 stage 內部**加大覆蓋，不引入跨 stage 干擾，方向正確：

| 項目 | 現況 | 建議 | 風險 |
|---|---|---|---|
| mutation 模組範圍 | 只跑 `token_guard` 單模組（pilot 範圍） | 20 核有餘裕，可擴到多模組 | 已有 ADR-SD09-002「mutation 多模組擴展」在管，**照該 ADR 走，不在本 ADR 決策** |
| chaos sweep 輪數 | `bounded=100/100`，43 秒 | 提高到 500~1000 輪，仍在分鐘級 | 低。與 perf 不同 stage，不影響延遲量測 |
| pytest 平行 | `local-ci-gate` 未見 `-n auto` | **不建議**——`pytest-randomly` 未啟用、順序由 collection 決定，開 `-n auto` 會改變執行順序並引入既有測試未驗證過的並行假設 | 中高。且它與 mutation 互踩的既有紀錄（理由 2）正是同一類問題 |

**優先順序建議：chaos 輪數（低風險、直接吃滿閒置算力）> mutation 多模組（依既有 ADR）> pytest 並行（不建議）。**

### 9.5 結論

**不該並行。** 對 perf 這種 sub-ms 量測，「跑得慢但乾淨」就是對的；20 核的正確用法是**在單一 stage 內加大取樣與覆蓋**（chaos 輪數、mutation 模組數），不是把互相污染的 stage 塞在一起搶核心。
