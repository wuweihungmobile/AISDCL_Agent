# ADR-SD07-001：LOC Budget 分級政策（取代 250 LOC 一刀切）

| 項目 | 內容 |
|------|------|
| 狀態 | **APPROVED（三方獨立研究 + 共識決議 2026-05-18）** |
| 議題 | 250 LOC 一刀切是否過嚴、是否反致系統複雜度上升？ |
| 提出者 | 使用者（SD_07 啟動前明確要求嚴正探討） |
| 決議者 | Architect / SA / SD 三方獨立研究 + 共識決議 |
| 簽核者 | Architect ✅ / SA ✅ / SD ✅（2026-05-18）|
| 取代 | SD_Improving_02.md v1.1 §3.1 R-3 / M5 「per-file ≤ 250 LOC 一刀切」 |
| 相關文件 | [SD_Improving_07.md](../SD_Improving_07.md) W0 / [tools/check_loc_budget.py](../../../tools/check_loc_budget.py) |

---

## 1. 背景與動機

### 1.1 既有規則

SD_02 / SD_03 微核心化重構期間，設定 **per-file ≤ 250 LOC** 一刀切紅線，目的：
- 避免 god-class（如 SD_04 起點 `_runner_impl.py` 2,236 行）
- 強制 SRP（單一職責）
- 提升可讀性 / 認知負擔可控

### 1.2 觸發本 ADR 的事實

| 事實 | 證據 |
|------|------|
| SD_06 W6 LOC violations=1 | total=13847 > cap=12904（W3 累積尚未消化）|
| **新發現肥胖檔案** | `steps_orchestrator/_impl.py = 736 LOC`（SD_06 W2 拆解未完成）|
| 14 個檔案突破 250 | 涵蓋 orchestrator / adapter / service / contract 各層級 |
| 使用者明確質疑 | 「請確實檢討 250 行是否太嚴苛，反而增加系統複雜度」 |
| 多檔同題 SSOT 漂移 | SD_05 W3 拆 6 子模組後出現 `checkpoint/_phase_handlers.py` 與 `_token_halt.py` 邏輯重疊 |

---

## 2. 實證資料（AutoClaude codebase 2026-05-18）

### 2.1 LOC 分佈統計

```
files:   151
min:     0
median:  84       ← 50% 檔案在 84 行內
p75:     151      ← 75% 檔案在 151 行內
p90:     234      ← 90% 檔案在 234 行內（250 已涵蓋）
p95:     309      ← 95% 檔案在 309 行內
max:     736      ← _impl.py（god-module 殘留）
```

**結論**：250 LOC 涵蓋 ~90% 檔案，對「典型業務邏輯」合理；對 p95+ 的特定層級過嚴。

### 2.2 超 250 LOC 檔案分類（14 個）

| 層級 | 數量 | 範例 | LOC 範圍 |
|------|------|------|---------|
| **Orchestrator / Facade** | 2 | `steps_orchestrator/_impl.py` 736 / `playbook_runner.py` 440 | 440-736 |
| **Repository / Adapter** | 3 | `pg_state_repository.py` 485 / `dual_state_repository.py` 316 / `minimax_client.py` 292 | 292-485 |
| **Service（純邏輯/演算法）** | 5 | `failure_tracker.py` 371 / `embedding_writer.py` 310 / `playbook_evolver.py` 309 / `config_resolver.py` 285 / `auto_resume.py` 258 | 258-371 |
| **Contract / Types / Assembly** | 3 | `hookspec.py` 311 / `types.py` 258 / `wiring.py` 263 | 258-311 |
| **Pure function library** | 1 | `prompt_builder.py` 416 | 416 |

**觀察**：
- Plugin 層全部 ≤ 250（12/12 ✅）
- Orchestrator / Adapter / Service 天然較重（職責本身大）
- 強拆會出現「邏輯橫向切碎、SSOT 漂移」反模式（SD_05 W3 已驗證）

---

## 3. 三方獨立研究

### 3.1 Architect 論點（業界對照 + 認知負擔）

**業界 LOC 政策參考**：

| 來源 | 建議 / 規則 | 適用 |
|------|------------|------|
| **Linux Kernel coding style** | 函式 ≤ 24 行（推薦）、80 col 寬；無明文檔案上限 | C 大型專案 |
| **Google C++ Style Guide** | 函式 ≤ 40 行（推薦）；無明文檔案上限 | C++ 大型專案 |
| **Robert C. Martin (Clean Code)** | 函式 ≤ 20 行；類別 200-500 行為理想；超 500 警訊 | OOP 通則 |
| **Java Effective Practice** | 類別 ≤ 750；超過建議拆分 | Spring 等大型框架 |
| **Python community (PEP 8 / Flake8 預設)** | 函式無上限；檔案約 ≤ 1000 為實務上限 | Python 通用 |
| **Microsoft .NET FxCop** | 類別 1500 / 方法 70（警告線）| 大型企業專案 |
| **SonarQube 預設（Python）** | 檔案 ≤ 750（一般建議）、≤ 1500（最大）| 通用 SaaS |

**核心觀察**：
1. **業界共識：函式行數比檔案行數更重要**（函式 ≤ 20-40 行，檔案 ≤ 500-750）
2. **250 LOC 為小型專案 / Plugin 入口的合理上限**，但對 Service / Orchestrator 偏嚴
3. **認知負擔研究**：人類短時記憶 7±2 chunk，一個 1080p 顯示器約 50-80 行可見；超過 ~250 行需要捲動超過 3 次，但對單一職責清晰的檔案影響不大

**Architect 立場**：
- ✅ 同意取消 250 一刀切
- ✅ 採分級制：依**職責性質**而非「程式長度」決定 budget
- ⚠️ 須以**圈複雜度（cyclomatic complexity）+ 函式行數**為輔助判準，不能只看檔案總行數
- ❌ 反對「無上限」——必須有最高紅線（建議 750 LOC）防止 god-class 復活

### 3.2 SA 論點（職責分類 + AutoClaude 實證）

**SA 核心觀察**：
1. 拆得太碎反致 **SSOT 多源**（SD_05 W3 checkpoint package 6 子模組已出現邊界漂移）
2. **強拆 Service / Orchestrator**只能橫向切碎，函式間反需更多參數傳遞，引入隱含耦合
3. **AutoClaude 14 個超 250 檔案**經人工審視，職責清晰、無重複，**強行拆分將降低可讀性**

**SA 提案分級**：

| 分類 | 建議 budget | 理由 |
|------|------------|------|
| **資料 / dataclass / Pydantic model** | ≤ 150 | 結構單純，多即過度 |
| **Plugin entry (公開 API)** | ≤ 250 | 對外契約，必須清晰簡潔 |
| **純函數庫 / Strategy** | ≤ 300 | 多個獨立純函數可共處 |
| **Adapter / Repository** | ≤ 400 | 對接外部系統，CRUD + 異常處理天然較重 |
| **Service / Orchestrator** | ≤ 500 | 業務邏輯編排，過嚴反致 SSOT 漂移 |
| **Contract / Types / Assembly（hookspec / wiring）** | ≤ 400 | 集中宣告比分散更清晰 |
| **絕對紅線（任何層級）** | ≤ 750 | 防 god-class 復活 |
| **測試檔** | 不設上限 | 測試完整性優先 |

**SA 立場**：
- ✅ 同意取消 250 一刀切
- ✅ 採職責分級
- ✅ 純函式庫例外（`prompt_builder.py` 416 行為合理）
- ⚠️ 須補**圈複雜度警戒線**（單函式 ≤ 10，整檔平均 ≤ 5）

### 3.3 SD 論點（CI 可執行性 + 既有累積消化）

**SD 核心觀察**：
1. SD_03 ~ SD_06 累積 14 個超 250 檔案，**多數為刻意設計**（如 hookspec 311 集中宣告）
2. `tools/check_loc_budget.py` 目前為「總 LOC 對 cap」二元判定，缺乏 per-file 警示
3. 若改分級制，必須**同步升級工具**，否則 CI 仍會誤警

**SD 提案執行細節**：

| 工具升級 | 目的 |
|---------|------|
| `tools/check_loc_budget.py` 加 per-file 分級表 | 每檔依層級判定 budget |
| `.loc-budget.toml` 配置檔（per-file override）| 純函式庫 / Adapter 個別豁免 |
| `radon cc` 圈複雜度 nightly | 補助判準（≤ 10 函式 / 平均 ≤ 5）|
| `tests/contract/test_loc_budget_tiered.py` | CI 守門 |

**SD 立場**：
- ✅ 同意取消 250 一刀切
- ✅ 採 SA 分級提案
- ⚠️ 嚴格要求 **W0 同步升級 `check_loc_budget.py` + 補 contract test**，否則 CI 失守

---

## 4. 三方共識決議

### 4.1 採納方案

**取消 250 LOC 一刀切，改採「分級 LOC budget + 圈複雜度輔助 + 絕對紅線 750」**

### 4.2 分級 budget 表（SD_07 W0 起生效）

| # | 分類 | LOC budget | 對應目錄 / 識別 |
|---|------|-----------|----------------|
| 1 | 資料 / dataclass / Pydantic model | **≤ 150** | `autoclaude/models/` / `autoclaude/core/ports/*.py`（Protocol-only）|
| 2 | Plugin entry（公開 API）| **≤ 250** | `autoclaude/plugins/*_plugin.py`（檔名以 `_plugin.py` 結尾或 package 內 `plugin.py`）|
| 3 | 純函數庫 / Strategy | **≤ 300** | `autoclaude/core/services/mutation/`（`_simple_mutations.py` / `_conditional.py` 等）/ `autoclaude/decision/prompt_builder.py` |
| 4 | Adapter / Repository | **≤ 400** | `autoclaude/infra/adapters/` / `autoclaude/infra/repositories/` |
| 5 | Service / Orchestrator / 編排層 | **≤ 500** | `autoclaude/core/services/` / `autoclaude/execution/steps_orchestrator/_impl.py` / `autoclaude/execution/playbook_runner.py` |
| 6 | Contract / Types / Assembly | **≤ 400** | `autoclaude/core/hookspec.py` / `autoclaude/core/wiring.py` / `autoclaude/execution/types.py` |
| 7 | **絕對紅線（任何層級）** | **≤ 750** | 全域上限 |
| 8 | 測試檔 | **不設上限** | `tests/**/*.py` |
| 9 | **工具自動化腳本（PowerShell / Bash）** | **≤ 750（advisory）** | `tools/**/*.ps1`, `tools/**/*.sh`、`tools/**/*.bash` |

> **歸類優先順序**（W6 補述）：**目錄分類 > 檔名 pattern > 預設 strategy tier**。範例：`steps_orchestrator/_escalation_handler.py` 302 LOC 雖 ≤ strategy 300 略超，但因目錄屬 `steps_orchestrator/`（service tier ≤ 500）合規。新增子模組時請依「所在目錄」優先判定 tier，再評估檔名 pattern；無法歸類時 fallback 至 strategy（≤ 300）。

> **工具腳本 tier 說明（v1.1，SD_09 W3 Round 50 audit P2-R48-2 補）**：`tools/run_local_nightly.ps1`（707 LOC）等 nightly orchestration 腳本天然較重（6 stage × 16 條取證紀律 inline 強制），歸 service tier（≤ 500）會誤判，但仍須受**絕對紅線 ≤ 750** 約束（防 god-script）。因此新增 tier #9「工具自動化腳本 ≤ 750」。**口徑為 advisory**：`tools/check_loc_budget.py` 目前僅 `rglob("*.py")` 掃描 Python 應用碼，**不掃 ps1/sh**（CI 不阻斷），由 reviewer 對照本 tier 人工把關；若未來腳本逼近 750 應拆函式庫（dot-source `.psm1` module）。run_local_nightly.ps1=707 ≤ 750 **合規**。

### 4.3 圈複雜度輔助判準（nightly，非阻塞）

- 單函式圈複雜度 ≤ 10（`radon cc -s -a` 警示）
- 整檔平均圈複雜度 ≤ 5
- 違反僅 nightly 警告，**不阻塞 PR**（避免 false positive 卡住開發）

### 4.4 既有 14 檔處理對照

| 檔案 | 現狀 LOC | 適用分級 | 新 budget | 狀態 |
|------|---------|---------|----------|------|
| `steps_orchestrator/_impl.py` | 736 | Orchestrator | ≤ 500 | ⚠️ **仍超標 236 LOC** → SD_07 W1 必拆 |
| `pg_state_repository.py` | 485 | Adapter | ≤ 400 | ⚠️ **超標 85 LOC** → SD_07 W1 / W5 評估 |
| `playbook_runner.py` | 440 | Orchestrator | ≤ 500 | ✅ **通過** |
| `prompt_builder.py` | 416 | 純函數庫 | ≤ 300 | ⚠️ **超標 116 LOC** → SD_07 W1 / W5 評估 |
| `failure_tracker.py` | 371 | Service | ≤ 500 | ✅ **通過** |
| `dual_state_repository.py` | 316 | Adapter | ≤ 400 | ✅ **通過** |
| `hookspec.py` | 311 | Contract | ≤ 400 | ✅ **通過** |
| `embedding_writer.py` | 310 | Service | ≤ 500 | ✅ **通過** |
| `playbook_evolver.py` | 309 | Service | ≤ 500 | ✅ **通過** |
| `minimax_client.py` | 292 | Adapter | ≤ 400 | ✅ **通過** |
| `config_resolver.py` | 285 | Service | ≤ 500 | ✅ **通過** |
| `wiring.py` | 263 | Assembly | ≤ 400 | ✅ **通過** |
| `types.py` | 258 | Contract | ≤ 400 | ✅ **通過** |
| `auto_resume.py` | 258 | Service | ≤ 500 | ✅ **通過** |

**14 檔處理結果**：12 個合規 + 3 個需 SD_07 W1 拆解（_impl.py / pg_state / prompt_builder）

### 4.5 預期效益

| 效益 | 量化 |
|------|------|
| 14 個既有「違規」檔案 | 12 個立即合規（無需強拆）|
| 工程師認知負擔 | 不再為「過 250 必拆」而橫向切碎邏輯 |
| SSOT 漂移風險 | 大幅降低（拆得太碎反致多源）|
| 拆解品質 | 集中於真正需要拆的 god-class（_impl.py 736）|
| CI 維護成本 | 工具升級一次性，後續穩定 |

---

## 5. 工具升級規範（W0 必交付）

### 5.1 `tools/check_loc_budget.py` 升級

```python
LOC_TIERS = {
    "data":           {"budget": 150, "patterns": ["autoclaude/models/", "autoclaude/core/ports/"]},
    "plugin_entry":   {"budget": 250, "patterns": ["autoclaude/plugins/*_plugin.py", "autoclaude/plugins/*/plugin.py"]},
    "strategy":       {"budget": 300, "patterns": ["autoclaude/core/services/mutation/", "autoclaude/decision/prompt_builder.py"]},
    "adapter":        {"budget": 400, "patterns": ["autoclaude/infra/adapters/", "autoclaude/infra/repositories/"]},
    "service":        {"budget": 500, "patterns": ["autoclaude/core/services/", "autoclaude/execution/steps_orchestrator/", "autoclaude/execution/playbook_runner.py"]},
    "contract":       {"budget": 400, "patterns": ["autoclaude/core/hookspec.py", "autoclaude/core/wiring.py", "autoclaude/execution/types.py"]},
    "absolute_limit": {"budget": 750, "patterns": ["*"]},  # global hard cap
}
```

### 5.2 `.loc-budget.toml`（per-file 例外配置）

```toml
[overrides]
# 純函數庫例外（多獨立函數可共處）
"autoclaude/decision/prompt_builder.py" = { tier = "service", reason = "纯函式集中，拆散反致呼叫端散亂" }

# 後續可視需要添加
```

### 5.3 `tests/contract/test_loc_budget_tiered.py`（≥ 6 case）

```python
def test_data_tier_budget_enforced(): ...
def test_plugin_entry_tier_budget_enforced(): ...
def test_strategy_tier_budget_enforced(): ...
def test_adapter_tier_budget_enforced(): ...
def test_service_tier_budget_enforced(): ...
def test_absolute_limit_750_enforced(): ...
```

---

## 6. 紅線與例外處理

### 6.1 絕對紅線

- ❌ 任何層級不得超 **750 LOC**
- ❌ 已分級檔案不得跨層級遊走（不可把 Service 標為「Orchestrator」避規）
- ❌ `.loc-budget.toml` overrides 必須附**書面理由**（PR description 註記）+ Architect / SD 雙簽

### 6.2 例外申請流程

1. 在 `.loc-budget.toml` 加入 override 條目
2. PR description 附理由（≥ 1 段說明為何拆分反致問題）
3. Architect + SD 雙簽（PR review）
4. 例外條目每季 review（避免長期積累）

#### 6.2.1 物理 wc-l 與邏輯行差異判定（W6 補述）

當檔案物理 `wc -l` 略超 budget 但邏輯行（剔除空白 / docstring / 註解）符合時，採以下判定原則：

- **若邏輯行 ≤ budget**：視為合規，但**必須在 `.loc-budget.toml` 補 override 條目 + 書面理由**（明示「物理 wc-l X 行 vs 邏輯行 ≤ Y 行」差異），避免後續 reviewer / 自動化工具誤判。
- **若邏輯行 > budget**：必須拆解，不得以「docstring 多」為由豁免。
- **`tools/check_loc_budget.py` 預設口徑**：採邏輯行（`count_loc` 已 skip 空白與註解 line）；override 不改變口徑，僅明示理由。

**範例（SD_07 W4 已落實）**：
- `steps_orchestrator/_impl.py` 物理 wc-l 530，邏輯行 ≤ 500（含 docstring/註解/空白約 30 行）→ `.loc-budget.toml` override 標 `tier = "service"` + 理由「物理 wc-l 530 含 docstring/註解/空白，邏輯行 ≤ 500 service tier 達標」。

### 6.3 總量 baseline 重新校準程序（R56 補訂）

**緣起（治理缺口）**：§6.1/§6.2 只規範 **per-file** tier budget 與其 override，
`tools/check_loc_budget.py` 另有一道**總量 cap**（`total ≤ baseline × 1.20`，baseline 存於
`AutoClaude/.loc_baseline`），而本 ADR 自 v1.0 起從未訂立該 baseline 的重新校準程序。
後果在 2026-07 跨平台複審 R52~R55 具體發生：總量連續多輪貼齊 cap（R52 一度 20451 > 20438 破線、
R53 = cap、R55 = cap−1），兩項已確認的真實缺陷（DEF-101-422／DEF-101-432）因「改了會破總量硬閘」
而被延後不修——**護欄實質阻擋了修復，卻沒有任何正規出口可走**。

**判準前提（R56 訂正宣稱與行為的矛盾）**：總量 cap 在實作上與 tier/absolute 違規**同級阻塞**
（`check_loc_budget.py` 的 `has_violation` 含 `total_violation`，`return 1`），並非工具 docstring
舊述的「sanity check」。本輪已同步訂正該 docstring 用詞；`--update` 旗標**刻意不接線**任何自動化
閘門（CI／git hooks／local_ci_gate 皆零引用，經 R56 grep 實證），僅供本節核准後由人工執行，
**後人勿誤判為漏接線**。

1. **觸發條件**（滿足任一）
   - 已破線：`total > cap`（CI 硬阻擋，必須處理）
   - 連續 2 輪 `total ≥ cap − 10`（餘裕耗盡的預警帶）。**R56 round 5 起機械化**：
     `check_loc_budget.py` 的 `TOTAL_WARN_MARGIN`（＝上式的 10；兩處數字的一致性由
     `tests/contract/test_loc_budget_tiered.py::test_total_warn_margin_matches_adr_sd07_001_section_6_3`
     自本節正文抽取比對後機械鎖定，**非人工同步**）在此區間
     印 **非阻塞** `[WARN]`（rc 不變），`--json` 報表另出 `total_warn_band` 布林欄。
     本條訂立當下工具尚無此訊號，R53(=cap)／R55(=cap−1) 兩次全靠審查員逐字讀輸出才發現，
     故補上機械偵測；「連續 2 輪」的輪次判定仍屬人工（本工具無跨輪狀態）。
2. **必要證據**（附於 PR description）
   - `python tools/check_loc_budget.py --json` 報表（含 `total_warn_band`）
   - **成長歸因**：增量落在哪些 tier／哪些檔案，並逐項判定是否屬死碼、重複實作、或真實新功能
3. **順位原則（先減後調，不可跳過）**
   - 第一順位：刪死碼／收斂重複實作。**R56 實例**：`autoclaude/execution/types.py` 移除兩支零呼叫端
     死碼（內含 R52 已修 POSIX-only 字面值的未修複本），**刪去 81 個邏輯行**（總量 20437 → 20356），
     使 cap（20438）之下的可用餘裕自 **1 行擴大為 82 行**，當輪即解除封鎖、無需動 baseline。
     （R56 round 5 訂正：原文「一次釋出 82 行餘裕」易被讀成「刪了 82 行」——刪的是 81 行，
     82 是刪後的餘裕總額，兩者差 1 正是刪除前僅存的那 1 行餘裕。）
   - 第二順位：以零／負增行手法完成修復（如將跨平台提示併入既有邏輯行的行尾註解，見 DEF-101-432 修法）。
   - 第三順位：確認增量為不可壓縮的真實功能後，才依本節調升 baseline。
   - ❌ **禁止**為了騰出額度而精簡「記錄 WHY 的既有註解」——本 repo 的跨輪防回歸倚賴
     `RNN 修正：…` 系列註解（見 R53 DEF-101-416 裁定）。
4. **核准層級與留痕**（比照 §6.2）
   - Architect + SD 雙簽
   - PR description 書面理由（含上述證據與順位原則的逐項排除說明）
   - 執行 `python tools/check_loc_budget.py --update` 後，`.loc_baseline` 的變更須與該 PR 同 commit

---

## 7. 與既有規則的取代關係

| 既有規則 | 處理 |
|---------|------|
| SD_Improving_02.md §3.1 R-3 「per-file ≤ 250 LOC」 | **本 ADR 取代**（SD_07 W0 起生效）|
| SD_Improving_05.md §5 紅線 #4 「超 250 必拆 package」 | **修訂為**：超分級 budget 必拆 |
| SD_Improving_06.md §7 紅線 #4 同上 | **同步修訂** |
| 各 sprint 內 LOC 檢查命令（`wc -l ... ≤ 250`）| **改為**：`python tools/check_loc_budget.py`（分級驗證）|

---

## 8. 風險與緩解

| 風險 | 緩解 |
|------|------|
| 分級判定錯誤導致 false positive | `.loc-budget.toml` overrides + Architect/SD 雙簽 |
| 工程師濫用分級（標錯層級避規）| code review 必查 + 季度 audit |
| 既有違規檔誤判通過 | W0 重新校準時逐檔人工 audit |
| nightly 圈複雜度警告氾濫 | 僅警告不阻塞；逐步消化 |
| 政策回退（決定改回 250）| ADR 版本控制 + git tag `loc-policy-v1`（250 一刀切）方便回溯 |

---

## 9. 決議

**Architect / SA / SD 三方共識：採納分級 LOC budget 政策（§4.2）**

| 決議項 | 結論 |
|--------|------|
| 取消 250 一刀切？ | ✅ 取消 |
| 採分級制？ | ✅ 採納（§4.2 表格）|
| 設絕對紅線？ | ✅ 設 750 LOC 全域上限 |
| 圈複雜度輔助？ | ✅ nightly 警告，不阻塞 PR |
| 工具升級時機？ | ✅ SD_07 W0 必交付 |
| 既有 14 檔處理？ | ✅ 12 立即合規 + 3 個（_impl.py / pg_state / prompt_builder）SD_07 W1 評估 |
| 例外申請流程？ | ✅ `.loc-budget.toml` + 雙簽 |

---

## 10. 簽核

| 角色 | 簽核 | 立場 | 日期 |
|------|------|------|------|
| Architect | ✅ APPROVED | 業界對照支持分級制；同意 750 絕對紅線 + 圈複雜度輔助 | 2026-05-18 |
| SA | ✅ APPROVED | 職責分類與 AutoClaude 實證一致；強拆 Service 反致 SSOT 漂移 | 2026-05-18 |
| SD | ✅ APPROVED | 工具升級可執行；要求 W0 同步交付 `check_loc_budget.py` + contract test | 2026-05-18 |
| QA | ✅ APPROVED | SD_07 W0~W6 各 Gate 四方審議已核准；AC-LOC-1 量測門檻通過（W0 26 case 全綠 / W1~W6 violations=0 維持）| 2026-05-18 |
| PM | ✅ APPROVED（形式核准）| 三方已共識；對應 risk_log R-SD07-1-2 + gate_audit SD07-G0 PM 簽核同步生效 | 2026-05-18 |

---

## 11. 版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | 三方獨立研究 + 共識決議：取消 250 一刀切，改採分級 budget（資料 ≤ 150 / Plugin entry ≤ 250 / Strategy ≤ 300 / Adapter ≤ 400 / Service ≤ 500 / Contract ≤ 400 / 絕對紅線 ≤ 750），圈複雜度 nightly 輔助；14 個既有違規檔 12 個立即合規 + 3 個 SD_07 W1 評估 |
| v1.1 | 2026-06-01 | SD_09 W3 Round 50 audit P2-R48-2：新增 tier #9「工具自動化腳本（PowerShell/Bash）≤ 750 advisory」，解決 `run_local_nightly.ps1`（707 LOC）無 tier 歸類之治理缺口；明示 `check_loc_budget.py` 僅掃 `*.py`，ps1/sh 為 reviewer 人工把關（CI 不阻斷）。Architect/SA/SD/QA 四方一致：advisory tier 不破壞既有 .py CI gate，與絕對紅線 750 哲學一致 |

---

**對應參考文件**：
- [SD_Improving_07.md](../SD_Improving_07.md) W0 — 工具升級交付
- [tools/check_loc_budget.py](../../../tools/check_loc_budget.py) — 升級目標
- [SD_Improving_02.md](../SD_Improving_02.md) §3.1 — 既有 250 規則（被取代）
- [SD_Improving_06.md](../SD_Improving_06.md) §7 紅線 #4 — 修訂目標
