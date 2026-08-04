# ADR-SD09-013：解除 W1 入場死鎖 — unique source_sha256 閘門由「入場條件」移為「出場驗收」

| 欄位 | 內容 |
|------|------|
| 狀態 | **ACCEPTED — 2026-08-03 PM（掌舵者）拍板選項 (b)**：「判定這是條件設計缺陷，直接以『kill_rate 7/7 已達標』放行 W1，unique sha 移到 W1 內部驗收」 |
| 提案輪 | AutoSDD improving（C 軌 SD_09 W1 觀察期收斂） |
| 編號 | 由主控集中發號（**013**）。012 已配給 AC4 軌（觀察期 #2），勿混用 |
| supersede | [ADR-SD09-009](ADR-SD09-009-mutmut-suspicious-policy.md) §11.3 line 230 + §11.6「#1 unique sha 為 **W1 入場**條件」的**閘門位置**（門檻數值 ≥ 7 unique sha 完全不變，只改它擺在入場處還是出場處） |
| 同構先例 | [ADR-SD09-011](ADR-SD09-011-mutation-lock-decouple-calendar.md)（同一軌，解除日曆綁定）。本 ADR 處理 011 沒碰到的**第二層病灶：閘門擺錯位置** |
| 姊妹案 | [ADR-SD09-012](ADR-SD09-012-ac4-observation-decouple-calendar.md)（AC4／觀察期 #2）。**本 ADR 不處理 AC4**，見 §7 |
| 相關 | 紀律 #12（unique sha 反作弊）、紀律 #1（stage rc 反映真實）、紀律 #4（驗證鏡子自身要被驗證） |

> ## ⚠️ 這是「放寬一道刻意設下的閘門」，不是修 bug
>
> 本 ADR 把 W1 的入場門檻從「unique source_sha256 ≥ 7」降到「≥ 5（其中 2 筆為 legacy 缺欄位紀錄）」。
> **原本要 7 個相異源碼版本才能進 W1，現在 5 個就進。**
> 這是**風險取捨**，不是缺陷修復。誰承擔、承擔什麼，見 §6。
> 起草期間另發現拍板前提有兩處與磁碟實況不符，訂正見 **§1.4**——那部分才是「訂正」。

---

## 1　Context（問題陳述）

### 1.1 四行死鎖

```
W1 啟動          ← 需要 觀察期 #1 達標
觀察期 #1 達標   ← 需要 tail 7 筆 unique source_sha256 ≥ 7
unique sha 增加  ← 需要 有人改 token_guard plugin 源碼
改 token_guard   ← 依 ADR-SD09-009 §11.6 之敘述，「唯有 W1 active 開發」時才合法發生
⇒ 要啟動才能達標、要達標才能啟動。
```

且 [ADR-SD09-011](ADR-SD09-011-mutation-lock-decouple-calendar.md) §2.1 已把 `append_history` 去重鍵改成 `source_sha256`，
**源碼不動，跑再多次 nightly 也不會多一個 unique sha**——這一軌與執行頻率完全無關，
「再等幾天」「多跑幾輪 nightly」在數學上不可能解開它。

### 1.2 代價已經實際發生

`SD_Improving_09.md` §8.2 + §6 PM 拍板 #6(b) 明載「最遲啟動日 **2026-06-26**」。
今天 **2026-08-03**，**逾期 38 天**，且沒有任何機制偵測到這個 deadline 已被跨過（見 §6.3 殘留缺口）。

### 1.3 一個必須先啟動才能滿足的啟動條件，本身就不是有效的啟動條件

這是本 ADR 的核心判準。啟動條件（entry gate）的功能是「在投入資源前，先確認前提成立」。
若某條件在**未投入資源時物理上無法成立**，它就沒有在做「篩選」——它只是在做「阻擋」。
阻擋不是閘門的目的。這種條件應被重新歸位為**出場驗收**（exit criteria），
因為它真正想確認的事（源碼演進有沒有被 mutation 覆蓋到）只有在做完事之後才有東西可查。

### 1.4 🔴 拍板前提訂正（起草期間 zero-trust 複核發現）

拍板當下對事實的兩項描述，經 2026-08-03 磁碟實查**與實況不符**。誠實紀律要求原樣揭露：

| 拍板時的描述 | 實查結果 | 出處（本輪真跑） |
|---|---|---|
| 「unique sha 5/7，**卡住**」 | 數字對（5 個相異 sha + 2 筆 legacy 缺欄位），但**權威閘門 `should_lock()` 早已回 `True`**：`MAX_BACKWARD_COMPAT_MISSING=2` 允許 2 筆 R2 P0-5 修復前的 legacy 紀錄，`min_non_none = 7-2 = 5`，實測 non-None=5 且全 unique → 通過 | `should_lock(history,'token_guard')` → `(True, 0.7071428571428572)` |
| （隱含）baseline 尚未鎖定 | **baseline 早在 2026-07-22 就已實際鎖定**，值 `token_guard = 0.7071`，且已 commit（`3c612ad`） | `logs/nightly_2026-07-22_183551.log:261` `::notice::token_guard baseline locked at 70.71%`；`.mutation_baseline.toml` |
| 「kill_rate 76.51%」 | 76.51% 是 R37/R39 的**歷史快照**，非現值。現行 tail 7 的**最小值是 70.71%**（仍 > 68% effective threshold，結論不變，但數字要用真的） | `.mutation_history.jsonl` tail7 kill_rate = 0.745 / 0.745 / 0.7517 / 0.7651 / 0.7625 / 0.7174 / **0.7071** |
| 「idle 期源碼凍結不達標」（§11.6，2026-05-29 寫下） | **已過期**。token_guard 源碼在 W1 未啟動期間自然演進出 4 個新 sha（improving_68/79/80/84 + R 輪跨平台修復；`git log -- autoclaude/plugins/token_guard/` 見 `02cc073` 06-25、`318c965`/`ad334c2` 06-26、`a16e591` 06-27、`f356348` 07-10） | `git log --format="%h %ad" -- autoclaude/plugins/token_guard/` |

**訂正後的問題重述**：死鎖**不在程式碼層**（`should_lock` 已放行、baseline 已鎖），
而在**文件層與載體層**——三處對同一個條件寫了**三個不同的門檻**：

| 判準所在 | 門檻 | 現值 | 結論 |
|---|---|---|---|
| `tools/mutation_baseline_lock.py::should_lock`（**權威實作**，Execution Guide §0.1 明指由它實作） | non-None sha 全 unique 且 ≥ `7 - MAX_BACKWARD_COMPAT_MISSING` = 5 | 5/5 | ✅ **PASS（已鎖 baseline）** |
| `SD_Improving_09.md` §8.1/§8.2 + `SD09_Execution_Guide.md` §0.1（**文件字面**） | 「tail 7 筆 unique source_sha256 **≥ 7**」 | 5 | ❌ 擋住 → ✅ **本 ADR L-1/L-2 已改述** |
| `tools/run_local_nightly.ps1` `$G0_MUTATION_UNIQUE_SHA_TARGET = 7`（**nightly G0 判定活載體**） | unique-sha ≥ 7 | 5 | ❌ 擋住 → ✅ **已消除（R71 G-1，L-3 落地）**：常數已刪，改由 `Get-MutationLockGate` 向 `should_lock` 現場提問 |

所以（在本 ADR 起草當下）真正擋著 W1 的是**文件與 nightly 載體，不是閘門邏輯**。

> ✅ **2026-08-03 複核：三處分歧已全部消除。** 文件字面由本 ADR §3.3 L-1/L-2 改述；
> nightly 載體由 R71 G-1 拔除自算門檻。**現在三處都指向同一個權威源 `should_lock`，不再有第二套門檻。**
這使得本 ADR 的性質是**「一半放寬、一半訂正」**：
- 對「文件字面 7」與「nightly counter 7」而言 → **確實是放寬**（7 → 5）；
- 對「權威實作 `should_lock`」而言 → **不是放寬**，是讓文件與載體追上早已通過的實作。

兩面都要說，只講其中一面就是把放寬包裝成修 bug。

---

## 2　為什麼原設計會長成這樣（它當時在防什麼）

**不是當初的人考慮不周。** §11.3 line 231 + §11.6 的原始論證讀下來，防護意圖清晰且正當：

### 2.1 它防的是「用重跑刷數字」

`should_lock` 要求「連續 7 次達標」。若不加任何約束，開發者（或一個急著過閘的 agent）
只要對**同一份源碼**連跑 7 次 nightly，就能湊滿 7 筆達標紀錄鎖定 baseline——
但這 7 次量的是同一件事，**零新資訊**。紀律 #12 因此要求 tail 7 筆必須是 7 個**相異源碼版本**：
「達標」必須代表「這 7 個版本的測試品質都被驗過」，而不是「我把同一個版本測了 7 遍」。
這個意圖無可挑剔，是 mutation testing 作為品質訊號的根本前提。

### 2.2 它也防的是「刻意 churn 衝 sha」

§11.3 line 231 明文禁止「為衝 unique sha 刻意 churn／修改 token_guard 源碼」。
理由同樣正當：若允許無意義改動來製造新 sha，7 個相異版本就退化成 7 次無意義提交，
反作弊被繞過，且會誘發「為過閘而動生產碼」這種最壞的工程行為。

### 2.3 死鎖是這兩個正當意圖交會處的副作用

把 §2.1（要真實源碼演進）與 §2.2（禁人工製造源碼演進）擺在一起，
剩下的合法來源就只有「正常開發活動改到 token_guard」。
而 §11.6（2026-05-29 R47 audit）在當時的觀測下——token_guard 自 2026-05-27 起 sha 凍結在 `20940e1b`——
下了一個**當時為真的經驗判斷**：「唯有 W1 active 開發才會改到它」。
這句話被寫進文件後，就從「觀測」升格成了「條件」：
**入場條件被綁定到只有入場之後才會發生的活動上**。

⚠️ 值得記下的是：§11.6 那個經驗判斷**後來被事實推翻**（§1.4 第 4 列——W1 沒啟動，源碼照樣演進出 4 個新 sha）。
所以死鎖在**現實中比文件描述的弱**（它是「慢到收不斂」而非「絕對不可能」：
05-26 至 08-01 共 70 天累積 5 個 unique sha ≈ 每 14 天 1 個，再湊 2 個約需 1 個月），
但**在文件與 nightly 載體的判定裡它是硬的**——這兩處不看現實，只看數字 5 < 7。

**結論**：原設計的防護目標正當，實作也正確；問題出在**閘門位置**，不在閘門強度。

---

## 3　Decision（決策）

採 PM 拍板 **(b)**。

### 3.1 W1 入場條件（entry gate）— 重新定義

觀察期 #1 對 W1 的放行判準，**改為以下兩項且僅此兩項**：

| # | 判準 | 判定方式（權威源） | 現況（2026-08-03 實測） |
|---|---|---|---|
| E-1 | tail 7 筆 kill_rate **全部 ≥ 68% effective threshold**（= target 0.75 − TOLERANCE 0.05 − EXTRA_TOLERANCE 0.02） | `.mutation_history.jsonl` tail 7 | ✅ 全過，最小值 **0.7071** |
| E-2 | `mutation_baseline_lock.should_lock()` 回 `True` 且 `.mutation_baseline.toml` 已寫入 token_guard baseline | 該函式回傳值 + baseline 檔 | ✅ `(True, 0.7071…)`；baseline `0.7071`，鎖定於 2026-07-22 |

**E-1/E-2 皆已達標 ⇒ 觀察期 #1 不再阻塞 W1。**

### 3.2 unique source_sha256 ≥ 7 — 移為 W1 出場驗收（exit criteria）

原入場條件「tail 7 筆 unique source_sha256 ≥ 7」**門檻數值不變**，位置改為 **W1 的 DoD 之一**：

> **X-1（W1 出場）**：W1 收尾時，`.mutation_history.jsonl` 中 token_guard 的 tail 7 筆必須含
> **≥ 7 個相異 `source_sha256`**，且該 7 筆 kill_rate 全部 ≥ 68% effective threshold。
> 判定一律呼叫 `tools/mutation_baseline_lock.py`，**不得手算、不得放寬 `MAX_BACKWARD_COMPAT_MISSING`**。

> **X-2（W1 出場，反作弊等價保留）**：X-1 所依據的每一個新增 `source_sha256`，
> 必須可對應到 W1 期間**一筆有實質內容的 token_guard 變更 commit**
> （功能／測試接線／缺陷修復皆可；**純格式、純註解、無語意變更的 churn 不算**）。
> 對應關係寫入 W1 收尾報告，逐 sha 列出 commit SHA 與該次變更的一句話說明。

### 3.3 三處判準同步對齊（落地項）

§1.4 揭露的三處門檻分歧必須一併消除，否則 W1 仍會被 nightly 載體擋住：

| # | 位置 | 動作 | 本輪狀態 |
|---|---|---|---|
| L-1 | `SD_Improving_09.md` §8.1 表 / §8.2 清單 / §6 拍板表 | 入場改述為 E-1+E-2；≥7 unique sha 標記為 W1 出場 | ✅ 本輪已改 |
| L-2 | `SD09_Execution_Guide.md` §0.1（SSOT） | 同步；註明 013 生效 | ✅ 本輪已改 |
| L-3 | `tools/run_local_nightly.ps1` 的 `$G0_MUTATION_UNIQUE_SHA_TARGET = 7` 與其 G0 mutation 判定 | 入場判定改對齊 `should_lock`（或直接呼叫它），`unique-sha n/7` 保留為**進度顯示**不作入場判定 | ✅ **已落地（R71 G-1）** — 2026-08-03 複核實查：`$G0_MUTATION_UNIQUE_SHA_TARGET` 常數**已自該檔刪除**（全檔 grep 零命中），改由新函式 **`Get-MutationLockGate`** 以 `-c` 探測碼直接呼叫 `mutation_baseline_lock.should_lock(history, module)`；`$mutVerdict` 只取權威回傳的 `locked` 布林，`tail unique-sha n/7` 降為併印的進度顯示。取不到值時印 `unavailable` 並 fail-closed，**明文禁止退回本檔自算的數字**（該檔註解原話：「退回就是把剛拔掉的第二套門檻裝回去」）|

---

## 4　反作弊如何不被削弱（硬要求）

原 unique sha 閘門的唯一職責是**反作弊**（§2.1/§2.2）。移位後該防護必須等價存在。逐項對照：

| 防護目標 | 原機制（入場處） | 新機制（出場處 X-1/X-2） | 強度 |
|---|---|---|---|
| 同 commit 重跑騙鎖 | tail 7 筆 unique sha ≥ 7 | **同一條，門檻數值不變**，只是在 W1 結束時查 | **相同** |
| 要求真實源碼演進 | 綁 7 個相異 sha | 綁 7 個相異 sha **且每個 sha 要對應一筆實質變更 commit**（X-2） | **更強**（原設計只查 sha 相異，不查該 sha 從哪來） |
| 禁刻意 churn 衝 sha | §11.3 line 231 文字禁令，**無取證載體** | X-2 要求逐 sha 列 commit + 一句話說明，寫入 W1 收尾報告 | **更強**（從口頭禁令變成可稽核產物） |
| 單日抖動 / flaky 誤鎖 | ±2pp tolerance + `compute_consistency_warning` | 不變 | **相同** |
| 人工最終閘 | PM signoff | PM signoff（W1 出場） | **不變** |

### 4.1 為什麼放在出場處一樣有效、甚至更合理

1. **入場處查它，查的是「上一段時間有沒有人碰過 token_guard」**——那是在查別人的歷史，
   與「W1 這一輪做得好不好」沒有因果關係。它篩不出任何與 W1 品質相關的資訊。
2. **出場處查它，查的是「W1 這一輪改了 token_guard 的那些版本，mutation 有沒有全部跟上」**——
   這正是這個閘門真正想確認的事。W1 的工作內容本來就會改 token_guard（B 議題群 mutation pilot），
   所以出場時 tail 7 自然會被 W1 產生的新 sha 填滿；此時檢查才是在檢查 W1 自己的產出。
3. **X-2 補上了原設計缺的一塊**：原本「禁 churn」只是文字禁令，沒有任何載體會去查
   「這個新 sha 到底是真改動還是湊數」。移到出場處後，因為 W1 的 commit 都在同一個 Wave 內、
   有 Wave 報告可承載，逐 sha 對應 commit 才變得可稽核。**反作弊實際上是被加強的。**
4. **時序上更嚴**：出場檢查發生在 baseline 已鎖之後，若 W1 期間源碼演進未被 mutation 覆蓋到，
   X-1 會直接擋住 W1 出場——比入場處擋住「還沒開始做的 W1」有意義得多。

### 4.2 明確不變更的紅線

- `should_lock()` 邏輯、`CONSECUTIVE_RUNS=7`、`TOLERANCE=0.05`、`EXTRA_TOLERANCE=0.02`、
  `MAX_BACKWARD_COMPAT_MISSING=2` — **一律不動**。本 ADR 不改任何一行 `tools/` 程式碼。
- 紀律 #12「禁為衝 sha 人工 churn token_guard 源碼」— **完全保留並升級為可稽核（X-2）**。
- ADR-SD09-009 §11.5 的三條紅線（不改 `calc_kill_rate` / `should_lock` / `thresholds.py`）— 不變。

---

## 5　殘餘風險與回退

### 5.1 若 W1 結束時 unique sha 仍不足 7

明確處置階梯（**不得默默放行**）：

| 情境 | 處置 |
|---|---|
| **(a) W1 有實質改動 token_guard，但 tail 7 的 unique sha 只到 6** | W1 **conditional pass**：產出 `SD09_W1_MutationCoverage_Gap.md`（列出實際 sha 數、缺口原因、已覆蓋的 commit 清單），由 PM 簽字後放行 G1；缺口以 **W2 出場條件**接續（W2 出場時 tail 7 必須 ≥ 7 unique sha，無條件） |
| **(b) W1 根本沒改到 token_guard**（B 議題群改跑 GoalSynthesis，TG 依 ADR-SD09-002 §2.1 退出 nightly 改週 baseline） | 回到 **R-SD08-PM-#3 既有 fall-back**：TokenGuard pilot 整體延 SD_10 接續，X-1/X-2 隨之移交 SD_10；W1 不因此被擋。**此路徑須在 W1 收尾報告明寫「X-1 未驗，已移交 SD_10」，禁止標記為通過** |
| **(c) W1 期間 kill_rate 跌破 68% effective threshold** | 與本 ADR 無關，走既有 R-SD09-B-1 / ADR-SD09-002 §3 fall-back（< 60% baseline → 產 Report + backlog，延 SD_10） |

### 5.2 回退本 ADR

本 ADR 不改程式碼，回退成本 = 把 §3.3 的三處文件／載體改述改回「入場 ≥ 7 unique sha」。
觸發回退的條件：W1 期間發現「以 5 個 sha 為基礎鎖定的 baseline 0.7071」明顯失真
（例：`compute_consistency_warning` 對同 sha 多 run 報出 > ±2pp 的 variance，
代表這 5 個版本的量測本身不穩），則應回退並要求補足 7 個 sha 後重鎖。

### 5.3 已知殘留缺口

- ✅ **L-3 已落地（R71 G-1，2026-08-03 複核實查）**：`$G0_MUTATION_UNIQUE_SHA_TARGET` 常數已自
  `run_local_nightly.ps1` 刪除，mutation 軌的 G0 判定改由 `Get-MutationLockGate` 向
  `mutation_baseline_lock.should_lock` **現場提問**。
  ⚠️ **原文「在 L-3 落地前，G0 放行是人工決策，不是機器判定」現已為假，且會直接誤導 PM** —— 該句已刪除。
  **現況：mutation 軌的 G0 判定是機器判定，判定值 100% 來自權威 `should_lock`，本檔不再持有第二套門檻。**
  （惟 **G0 整體放行仍需 PM 拍板** —— 那是設計上的人工閘，與「判定是否機器化」是兩回事，勿混為一談。）
- 🟡 **deadline 逾期無偵測（仍未解）**：§6 PM #6(b) 的「最遲 2026-06-26」被跨過 38 天而無任何告警。
  本 ADR 不新增 deadline 監控機制（屬另案）。**規格已於
  [SD_Improving_09.md §8.3 D-4](../SD_Improving_09.md) 交付（掛進 nightly 收尾、WARN 不進 rc、三 case 測試鎖），
  但實作尚未落地** —— 這是本 ADR 相關殘留缺口中**唯一還開著的一項**。

---

## 6　誠實揭露：放寬幅度、承擔者、風險

### 6.1 放寬了多少（具體數字）

| 面向 | 原本 | 現在 | 差額 |
|---|---|---|---|
| W1 入場所需 unique `source_sha256` 數（**文件字面／nightly G0 counter**；後者已於 R71 G-1 拔除，現直接問 `should_lock`） | **7** | **5**（另含 2 筆 2026-05-20/21 legacy 缺欄位紀錄） | **−2 個相異源碼版本** |
| W1 入場所需 unique sha 數（**權威實作 `should_lock`**） | 5（`7 − MAX_BACKWARD_COMPAT_MISSING`） | 5 | **0（無變化）** |
| kill_rate 門檻 | 68% effective | 68% effective | **0（不變）** |
| 連續達標筆數 `CONSECUTIVE_RUNS` | 7 | 7 | **0（不變）** |
| unique sha ≥ 7 這道閘 | 入場處 | **移至出場處，門檻數值不變，並加 X-2 commit 對應要求** | 位置改變，強度不減 |

一句話：**原本要 7 個相異源碼版本才能進 W1，現在 5 個就進；那 2 個的差額移到 W1 出場時補齊並額外附上 commit 佐證。**

### 6.2 誰承擔風險、風險是什麼

- **承擔者**：PM（掌舵者）。2026-08-03 拍板 (b)，本 ADR 為該拍板的承載文件。
- **風險內容**：token_guard baseline `0.7071` 是以「5 個相異源碼版本 + 2 筆 legacy 紀錄」為證據基礎鎖定的，
  比原設計要求的 7 個版本少 2 個。若這 5 個版本恰好在測試覆蓋特性上同質
  （例：都沒觸及 `compactor` 或 `git_verifier` 子模組），則 baseline 可能高估或低估真實水位，
  W1 之後以此 baseline 做回歸判定會帶著這個偏差。
- **風險等級評估**：🟡 中低。理由：(1) 這 5 個 sha 橫跨 2026-05-26 ~ 2026-08-01 共 70 天、
  來自 4 次獨立的功能性變更（improving_68/79/80/84）+ 1 次跨平台修復，同質性風險低；
  (2) 那 2 筆 legacy 紀錄的寬容是 R2 P0-5 修復前的既有設計（`MAX_BACKWARD_COMPAT_MISSING=2`，
  R21 Architect 已從 `ceil(N/2)=4` 收緊到 5），不是本 ADR 新開的口子；
  (3) baseline 鎖在 tail 7 的**最小值** 0.7071（最保守取值），非平均或最大值。
- **不承擔的風險**：本 ADR **不**為觀察期 #2（AC4）、#3（drift_log）的任何放行背書，見 §7。

### 6.3 這不是「修 bug」

本 ADR 沒有修復任何缺陷。`should_lock` 一直是對的、baseline 一直鎖得對、反作弊一直有效。
本 ADR 做的是**兩件事**：
1. **一個治理放寬**（§6.1）：把入場門檻由 7 降到 5，風險由 PM 承擔；
2. **一個事實訂正**（§1.4）：讓文件與 nightly 載體追上「baseline 早在 2026-07-22 就鎖了」這個實況。

把 (2) 拿來當作 (1) 的正當性來源、或反過來把 (1) 說成 (2) 的一部分，都是包裝。兩者分開陳述。

---

## 7　此決策不涵蓋什麼

明確聲明射程邊界，避免被引用時擴權：

- ❌ **不處理觀察期 #2（AC4 labeled PR，2026-08-03 實測 8/14）**。AC4 的日曆連續判準問題由
  [ADR-SD09-012](ADR-SD09-012-ac4-observation-decouple-calendar.md) 承載，該 ADR 已於 **2026-08-03 由 PM 拍板轉 ACCEPTED**
  （採 gap-tolerant green_streak；**判準 code 尚未落地**，且拍板後經 Architect 實測補列「證據新鮮度」為第二處放寬，須加做 L-7 staleness 判準）。
  本 ADR 生效**不代表** AC4 獲得任何放行。
> #### ✅ 2026-08-04（R74）裁定：drift 軌的「入場歸屬」在 PM 裁示前一律 fail-closed
>
> **問題**：本節下一條把 #3 的入場歸屬記為「待 PM 裁定」，而**活載體**
> （`run_local_nightly.ps1`）早已把 drift 併入 `[G0-READY]` 的 AND 條件。文件與實作
> 對同一件事給出兩個答案，兩邊各自都是綠的 —— 沒有任何機械物會發現這個分岔。
>
> **裁定（以實作為權威，fail-closed）**，三條理由：
> 1. **放寬一道閘門需要決策，維持它不需要。** 而這個歸屬**尚未有人裁定**。把「還沒人決定」
>    當成「所以不算阻塞」來放行，是把沉默讀成許可 —— 錯誤方向不可逆。
> 2. **`[G0-READY]` 的語意是「SD_09 W0 四軌全數達標」**，不是「W1 入場許可」。把 drift
>    移出 AND，這行字就不再對應它自己的名字。
> 3. **drift 現在沒過的原因是一筆真紅**（2026-06-02 採集失敗打斷 streak），不是缺口 ——
>    它是判準有鑑別力的正面證據。為了讓燈變綠而把唯一擋著的真紅移出 AND，等於拆燈。
>
> **PM 若要放寬**：明確裁示「#3 非 W1 入場條件」，並同時指定它在 W5 雙條件中的角色，
> 再改 `run_local_nightly.ps1` 的四軌 AND。**在那之前，nightly 會繼續把它算作阻塞項，
> 且 log 逐輪印出「W1 入場歸屬待 PM 裁示」讓這個未決狀態在現場可見**（不必去讀 ADR 才知道）。

- ❌ **不處理觀察期 #3（drift_log 30 天零事件）**。實查結果為 **未達標**
  （`drift_log_ga_check.py` → **`green_streak=26 < window=30`**，2026-06-02 一筆採集失敗打斷 streak；2026-08-03 複核值，
  初稿寫 25 是 02:00 nightly 寫入第 35 筆前的舊值）。
  ✅ **「該工具零 production caller」已不成立**（R71 G-3 已把它接進 nightly 收尾）—— 原文已訂正，詳見 `SD_Improving_09.md` §8.1 表下方註記。
  ⚠️ ADR-SD09-012 §1.1 表格所載「#3 早已達標」為**誤述**，該 ADR 已自行訂正；應以本節與實跑輸出為準。
- ❌ **不改任何 `tools/` 程式碼**（含 `mutation_baseline_lock.py`、`run_local_nightly.ps1`、
  `ac4_progress_check.py`）。§3.3 L-3 起草當下為待協調落地項，**已由 R71 G-1 另輪落地**（非本 ADR 自行執行，射程邊界未被突破）。
- ❌ **不放寬紀律 #12**。X-2 反而收緊了它的取證要求。
- ❌ **不涵蓋 GoalSynthesisPlugin / OrchestrationCoordinator 的 mutation pilot 判準**
  （ADR-SD09-002 §2.5 各自的目標與鎖定條件不變）。

---

## 8　取證附錄（2026-08-03 本輪真跑，repo HEAD `fd860ab`）

```
$ .venv/Scripts/python.exe -c "<載入 tools/mutation_baseline_lock.py 對 .mutation_history.jsonl 求值>"
total token_guard records = 7
CONSECUTIVE_RUNS = 7 | TARGETS = {'token_guard': 0.75, ...} | TOLERANCE = 0.05
  | EXTRA_TOLERANCE = 0.02 | MAX_BACKWARD_COMPAT_MISSING = 2
effective threshold = 0.6799999999999999
tail7 shas = [None, None, '5208cff397beecc5', '20940e1b903dc19d', '4af78567437894af',
              '55013d0a916f814e', '5a44cbba2d95ce2f']
non-None = 5 | unique non-None = 5
tail7 kill_rates = [0.745, 0.745, 0.7517, 0.7651, 0.7625, 0.7174, 0.7071]
SHOULD_LOCK = (True, 0.7071428571428572)
```

```
$ cat .mutation_baseline.toml
[scores]
token_guard = 0.7071          # commit 3c612ad（2026-07-22）

$ grep -n "baseline locked" logs/nightly_2026-07-22_183551.log
261:::notice::token_guard baseline locked at 70.71%

$ grep -n "baseline locked" logs/nightly_2026-08-01_101807.log
375:::notice::token_guard baseline locked at 70.71%
```

```
$ .venv/Scripts/python.exe tools/drift_log_ga_check.py --json      # 供 §7 引用
{"status": "observing", "green_streak": 26, "window": 30, "total_records": 35,
 "last_failure_reason": "drift_log_table_exists=False (alembic head 落後)"}   # rc=1

$ .venv/Scripts/python.exe tools/ac4_progress_check.py --json      # 供 §7 引用
{"status": "observing", "observation_days": 8, "green_streak": 8,
 "ready_for_labeled_pr": false, "reasons": ["觀察期未滿（8/14 天）"]}
```

> **量測時點註記（2026-08-03 複審輪重跑）**：上列 drift／ac4 兩段為**複審輪當回合實跑值**。
> 本 ADR 初稿撰於 02:00 nightly 之前，當時為 `drift 25/30, total 34` 與 `ac4 7/14`；
> 該輪 nightly（`logs/nightly_2026-08-03_020001.log`）為各軌寫入 1 筆，故均 +1。
> `last_failure_reason` 仍顯示舊訊息屬**正常**——該欄描述的是歷史上打斷 streak 的那一筆（2026-06-02），不是現況。
> 上方 mutation 區塊（`SHOULD_LOCK` / tail7 / baseline）**未受影響**：mutation 軌按 `source_sha256` 去重，源碼未動則不增筆。

---

## 9　DoD（本 ADR 的落地驗收）

1. ✅ `SD_Improving_09.md` §6 新增拍板列、§8.1 表與 §8.2 清單改述（L-1）。
2. ✅ `SD09_Execution_Guide.md` §0.1 同步（L-2，SSOT 一致性）。
3. ✅ `gate_audit.md` §1-septies 補簽核紀錄（含取證）。
4. ✅ `risk_log.md` §15 補／更新對應風險列。
5. ✅ `run_local_nightly.ps1` `$G0_MUTATION_UNIQUE_SHA_TARGET` 對齊（L-3）— **已落地（R71 G-1，2026-08-03 複核實查）**：常數已刪除，改由 `Get-MutationLockGate` 呼叫 `should_lock` 現場提問。
6. ⬜ W1 收尾時驗 X-1 + X-2，結果寫入 W1 收尾報告與 `gate_audit.md` SD09-G1 列。

---

**版本紀錄**
- **v1.0（ACCEPTED）2026-08-03** — PM 拍板 (b) 承載；含 §1.4 拍板前提訂正（baseline 早已於 2026-07-22 鎖定、
  §11.6「idle 凍結」敘述已被事實推翻）、§4 反作弊等價性對照 + X-2 新增取證要求、
  §6 放寬幅度誠實揭露、§7 射程邊界（不涵蓋 AC4／drift_log）。commit SHA 待主控填。
- **v1.1（收尾訂正）2026-08-03** — **L-3 已落地，全文據實改寫**：R71 G-1 已自 `run_local_nightly.ps1`
  刪除 `$G0_MUTATION_UNIQUE_SHA_TARGET`，改以 `Get-MutationLockGate` 呼叫 `should_lock` 現場提問
  （§1.4 三處分歧表／§3.3 L-3／§5.3／§9 item 5 全數由 ⛔ 改 ✅）。
  **刪除已成假的「在 L-3 落地前，G0 放行是人工決策，不是機器判定」一句**（該句會直接誤導 PM）。
  §7 射程邊界同步：ADR-SD09-012 已轉 ACCEPTED（非 PROPOSED）、drift `green_streak` 25→**26**、
  「`drift_log_ga_check.py` 零 production caller」已不成立（R71 G-3 接入 nightly）。
  §8 取證附錄 drift／ac4 兩段重跑對齊 02:00 nightly 後之值（drift 25/34 → **26/35**；ac4 7 → **8**）。
  **仍開著的殘留＝deadline 逾期無偵測（D-4，規格已交付、實作未落地）。**
