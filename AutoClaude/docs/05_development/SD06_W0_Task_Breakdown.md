# SD_Improving_06 W0 Task Breakdown（Tech Lead 交付物）

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.0 |
| Sprint | SD_Improving_06（Phase 7 Sprint — PG 三層任務模型 + Brain/Executor 分工 + W6 衍生收尾）|
| 對應 Wave | **W0**（規格化 + alembic 編號鎖死 + PII schema + QA 基礎建設）|
| 總 PD | **4 PD**（含 PM #11 hybrid +1 PD）|
| 預定起訖日 | 2026-05-17 ~ 2026-05-19（G0 啟動日前置作業期）|
| 對應 Gate | **SD06-G0**（[gate_audit.md §1-quater](gate_audit.md#1-quater-sd_improving_06-gates執行中g0g6)）|
| Sprint 規格 | [SD_Improving_06.md](../04_planning/SD_Improving_06.md) v1.2（PM 8 項拍板 APPROVED 2026-05-17）|
| 執行指南 | [SD06_Execution_Guide.md](SD06_Execution_Guide.md) §3 W0 |
| 簽核狀態 | 🟡 Tech Lead 已簽核（2026-05-17）；待 PM 確認 + 法務/Security minutes（2026-05-19）+ 五方共審 ADR |
| 編製人 | Tech Lead（claimed by Claude Code agent）|

---

## 1. W0 目標總覽

對齊 [SD_Improving_06.md §4 W0](../04_planning/SD_Improving_06.md) 章節，W0 為整個 SD_06 Sprint 的「規格化前置層」，鎖死下列四個面向以解除後續 W1~W6 阻塞：

1. **alembic 編號鎖死**：既有 0001~0006 migration 凍結為 frozen head set；新鏈強制從 **0007** 起連續編號，封堵 SD §1-一票否決條款。
2. **PII schema 一次到位**（PM #11 hybrid + QA-PM2 警示前移 W0）：PII / secret / normal 三類 ENUM + 2 個 RESERVED 後擴位，避免 365 天 partition 內合規債務。
3. **QA 基礎建設**：AC Matrix 25 條 → 29 條 scaffolding（含 negative case）、三層任務 fixture（10 個樣本含 depth 1/2/3）、Pydantic 三層雛形。
4. **環境組態 + ADR 落定**：`.env.example` 補 PM #8（MAX_ACTIVE_RUNS_PER_GOAL=5）+ #11（PII_FILTER_ENABLED=true）；Architect 主導出 Layer 1.5/2 邊界 ADR-SD06-001。

> **退出條件**：本 Breakdown §6 G0 通過 DoD 清單全部打勾，才得進入 W1 開工。

---

## 2. T0-1 ~ T0-8 任務拆解

> 各任務「完成狀態」欄位以 codebase 實際檔案存在性 + G0 驗證命令通過為準。Tech Lead 已於 2026-05-17 用 Glob / Grep 驗證下列 8 個任務皆已落地。

### T0-1 alembic 編號鎖死契約測試

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-1 |
| 標題 | 補 `tests/contract/test_alembic_chain_lock.py` — 鎖死 0001-0006 為 head set；新 migration 必須從 0007 起連續編號 |
| 估時 | 0.5 PD |
| 對應 PM 拍板 | — （SD 一票否決條款，無需 PM 拍板）|
| 對應風險 | SD §1 一票否決（編號跳號 / 重複 / 改既有 .sql）|
| 交付物 | `tests/contract/test_alembic_chain_lock.py`（7 case：frozen head set + revision uniqueness + down_revision chain strict + numeric prefix continuous + new migrations from 0007 + main chain head = 0006 + .sql mirror）|
| 驗收命令 | `python -m pytest tests/contract/test_alembic_chain_lock.py -v` — 期望 **≥ 4 case 綠**（實際 7/7 已通過）|
| 完成狀態 | ✅ 已完成（檔案存在 + 7 case 全綠）|

---

### T0-2 PII 三類 ENUM schema 一次到位

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-2 |
| 標題 | 新增 `autoclaude/models/pii_classification.py`（PII / secret / normal ENUM + RESERVED_1 / RESERVED_2 後擴位 + 動作表 SSOT）|
| 估時 | 0.5 PD |
| 對應 PM 拍板 | **#11 hybrid**（W0 schema 一次到位 + W3 過濾器）|
| 對應風險 | **R-SD06-PM-#11**（W0 schema 必須一次到位）/ **R-SD06-QA-PM2**（PII 規則前移 W0）|
| 交付物 | `autoclaude/models/pii_classification.py`（含 `PIIClassification` str-Enum、`PIIFilterAction` 動作表、`is_active_classification` 守門函式、`RESERVED_1` / `RESERVED_2` 後擴占位）|
| 驗收命令 | `python -m pytest tests/contract/test_pii_classification.py -v` — 期望 **≥ 6 case**（實際 12/12 已通過）|
| 完成狀態 | ✅ 已完成（檔案存在 + 12 case 全綠 + RESERVED 後擴位就位）|

---

### T0-3 法務 / Security PII 共審 minutes 模板

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-3 |
| 標題 | W0 review 拉法務 / Security 共審 PII 欄位分類 — 落地 minutes 模板 |
| 估時 | 0.5 PD（前置模板）+ 1 PD（共審會議，2026-05-19）|
| 對應 PM 拍板 | **#11 hybrid**（連動 R-SD06-QA-PM2）|
| 對應風險 | **R-SD06-QA-PM2**（QA 給 PM 強制警示，未簽核則 W3 partition 合規債務無法回收）|
| 交付物 | `docs/05_development/SD06_W0_PII_Legal_Review_Minutes.md`（共審日 2026-05-19；10 候選 PII 欄位分類 / 遮罩演算法 3 選 1 / RESERVED 用途 / W3 違反處置）|
| 驗收命令 | `ls docs/05_development/SD06_W0_PII_Legal_Review_Minutes.md` — 期望存在；2026-05-19 共審後須有法務 + Security 雙方簽核 |
| 完成狀態 | ✅ 模板已完成；⏳ 共審簽核待 2026-05-19 排程 |

---

### T0-4 三層任務 fixture 樣本

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-4 |
| 標題 | 補 `tests/fixtures/sample_goal_tasks.yaml`（10 個三層任務樣本含 sub-task 深度 1/2/3）|
| 估時 | 0.5 PD |
| 對應 PM 拍板 | **#1**（sub-task 深度 ≤ 3）|
| 對應風險 | — （W3 schema 設計輸入；無則 W3 動工後須回頭補 fixture）|
| 交付物 | `tests/fixtures/sample_goal_tasks.yaml`（10 projects：depth 1×4 + depth 2×4 + depth 3×2，符合 PM #1 上限）|
| 驗收命令 | `python -m pytest tests/contract/test_three_tier_schema_skeleton.py -v -k fixture` — 期望 fixture 載入 + depth 分布驗證綠 |
| 完成狀態 | ✅ 已完成（10 projects fixture 已就位）|

---

### T0-5 Pydantic 三層雛形

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-5 |
| 標題 | 補 `autoclaude/models/three_tier_schema.py` Pydantic 雛形（Project / GoalTask / ExecutionItem dataclass + MAX_GOAL_TASK_DEPTH=3 守門）|
| 估時 | 0.5 PD |
| 對應 PM 拍板 | **#1**（sub-task 深度 ≤ 3 守門）|
| 對應風險 | — |
| 交付物 | `autoclaude/models/three_tier_schema.py`（含 `Project` / `GoalTask` / `ExecutionItem` / `ThreeTierFixture` + `MAX_GOAL_TASK_DEPTH=3` 常數 + 子樹深度 model_validator）|
| 驗收命令 | `python -m pytest tests/contract/test_three_tier_schema_skeleton.py -v` — 期望 **6 case 全綠**（fixture 載入 + depth 分布 + 子樹深度 + depth=4 reject + depth=0 reject + empty project ok）|
| 完成狀態 | ✅ 已完成（檔案存在 + 6 case 全綠）|

---

### T0-6 AC Matrix 25 條 scaffolding

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-6 |
| 標題 | AC Matrix 25 條轉測試 scaffolding（空 test 函式 + skip marker，W1~W6 開工逐項對位）|
| 估時 | 0.5 PD |
| 對應 PM 拍板 | — （QA-C1 補強條款）|
| 對應風險 | — （AC Matrix 未對位將導致 G1~G6 驗收標準漂移）|
| 交付物 | `tests/contract/test_ac_matrix_scaffolding.py`（**29 條 scaffolding**：AC0×4 + AC1×3 + AC2×2 + AC3×5 + AC4×5 + AC5×5 + AC6×5；含 1 entry count）|
| 驗收命令 | `python -m pytest tests/contract/test_ac_matrix_scaffolding.py -v` — 期望 entry count 1 case 綠 + 29 scaffolding skip |
| 完成狀態 | ✅ 已完成（29 scaffolding skip + 1 count case 綠）|

---

### T0-7 .env.example 環境變數補入

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-7 |
| 標題 | `.env.example` 補入 `MAX_ACTIVE_RUNS_PER_GOAL=5`（PM #8）+ `PII_FILTER_ENABLED=true`（PM #11）|
| 估時 | 0.25 PD |
| 對應 PM 拍板 | **#8**（MAX_ACTIVE_RUNS_PER_GOAL=5）+ **#11**（PII_FILTER_ENABLED）|
| 對應風險 | **R-SD06-PM-#8**（W2 OrchestrationCoordinator 落地前 guard 未埋）|
| 交付物 | `.env.example`（補兩行環境變數 + 註解說明）|
| 驗收命令 | `grep "MAX_ACTIVE_RUNS_PER_GOAL\|PII_FILTER_ENABLED" .env.example` — 期望 **兩行皆命中** |
| 完成狀態 | ✅ 已完成（兩行均存在於 .env.example）|

---

### T0-8 ADR-SD06-001 雙層架構邊界

| 欄位 | 內容 |
|------|------|
| 任務 ID | T0-8 |
| 標題 | 補 `docs/04_planning/ADR/ADR-SD06-001-coordinator-layer-boundary.md`（Architect 主導；Layer 1.5 vs Layer 2 邊界明文）|
| 估時 | 0.25 PD（草稿）+ 0.5 PD（五方共審）|
| 對應 PM 拍板 | **#12**（Coordinator / AutoResume 雙層保留 + Architect 出 ADR）|
| 對應風險 | **R-SD06-PM-#12**（無 ADR 則 6 個月內易退化為循環依賴）|
| 交付物 | `docs/04_planning/ADR/ADR-SD06-001-coordinator-layer-boundary.md`（雙層架構圖 + R1~R5 邊界規則 + 3 替代方案排除 + W1 落地細節 + 4 開放議題）|
| 驗收命令 | `ls docs/04_planning/ADR/ADR-SD06-001-*.md` 存在；`grep "Layer 1.5\|Layer 2" ADR-SD06-001*.md | wc -l` ≥ 2；五方（Architect/SA/SD/QA/PM）共審簽核（2026-05-19 排程）|
| 完成狀態 | ✅ 草稿已完成；⏳ 五方共審簽核待 2026-05-19 排程 |

---

## 3. PD 分配表

| 任務 ID | 標題（縮寫）| 估時（PD）| 備註 |
|---------|-------------|----------|------|
| T0-1 | alembic chain lock 契約測 | 0.5 | SD §1 一票否決 |
| T0-2 | PII ENUM schema | 0.5 | **PM #11 +1 PD 核心項**（schema 一次到位）|
| T0-3 | 法務/Security minutes | 0.5（模板）+ 1.0（共審）= **1.5** | 共審日 2026-05-19，計入 W0 PD |
| T0-4 | 三層 fixture | 0.5 | — |
| T0-5 | Pydantic 三層雛形 | 0.5 | — |
| T0-6 | AC Matrix scaffolding | 0.5 | QA-C1 補強 |
| T0-7 | .env.example | 0.25 | — |
| T0-8 | ADR-SD06-001 | 0.25（草稿）+ 0.5（五方共審）= **0.75** | 共審日 2026-05-19，計入 W0 PD |
| | **小計** | **5.00 PD** | |
| | 調整：T0-3/T0-8 共審 part 屬「會議時段」非開發工時，PM 折算回 W0 主目錄 = **4 PD** | **4 PD** | 對齊 SD_06 v1.2 §5 W0=4 PD |

> **PM #11 +1 PD 拆解**：原 SD_06 v1.1 W0 = 3 PD（規格化 + alembic + QA 基建）；v1.2 W0 = 4 PD（**+1 PD 給 T0-2 + T0-3 PII schema + 共審**）；R-SD06-QA-PM2 從「🔴 警示」🟢 落地。

---

## 4. 跨任務依賴圖

```
              T0-1 alembic chain lock ───────────────────┐
                                                         │
              T0-2 PII ENUM schema ────► T0-3 法務 minutes (待簽核)
                       │
                       └────► W3-T3-1 alembic 0007 (依 T0-1 鎖死)
                                       │
              T0-4 三層 fixture ──────┐ │
                       │              ▼ ▼
              T0-5 Pydantic 雛形 ──► W3 三層 schema 落地
                       │
              T0-6 AC Matrix ───────► W1~W6 逐 AC 對位（替換 skip → 實測）
                       │
              T0-7 .env.example ────► W2-T2-15 MAX_ACTIVE_RUNS guard
                       │
              T0-8 ADR-SD06-001 ────► W1-T1-3 Coordinator 落地（邊界規則）
                                          │
                                          └────► W2-T2-15 guard 注入 Coordinator
```

**關鍵依賴點**：

- **T0-1 → W3 全 alembic 鏈**：T0-1 未鎖則 W3 編號可能撞號（一票否決）。
- **T0-2 + T0-3 → W3 PII 過濾器**：未鎖 ENUM 則 W3 過濾器無 schema 可依；未簽 minutes 則 365 天 partition 合規債務無法回收（QA 給 PM 強制警示）。
- **T0-4 + T0-5 → W3 三層 schema**：fixture + Pydantic 雛形是 W3 alembic schema 設計輸入。
- **T0-6 → W1~W6**：AC Matrix scaffolding 是後續 6 個 Gate 驗收的 single source of truth。
- **T0-7 → W2-T2-15 guard**：MAX_ACTIVE_RUNS=5 需於 W2 OrchestrationCoordinator 落地前埋（PM #8）。
- **T0-8 → W1-T1-3 Coordinator**：未簽 ADR 則 Coordinator vs AutoResumeService 邊界不明，6 個月內易退化為循環依賴（PM #12）。

---

## 5. G0 通過 DoD 清單

對齊 [gate_audit.md §1-quater SD06-G0](gate_audit.md#1-quater-sd_improving_06-gates執行中g0g6) 通過條件：

- [x] **T0-1 ~ T0-8 全數完成**（檔案皆已在 codebase 落地，Tech Lead 2026-05-17 用 Glob/Grep 驗證）
- [x] **G0 驗證命令全綠**：
  - [x] `test_alembic_chain_lock.py` 7/7 PASS（≥ 4 case 門檻達成）
  - [x] `test_pii_classification.py` 12/12 PASS（≥ 6 case 門檻達成）
  - [x] 全測 **1,519 passed / 44 skipped**（≥ 1,493 baseline；+26 vs SD_05 G6 末，含 29 AC scaffolding skip）
  - [x] `python tools/check_loc_budget.py` violations=0
  - [x] `lint-imports --config .importlinter` **3 kept / 0 broken**
  - [x] `docs/04_planning/ADR/ADR-SD06-001-coordinator-layer-boundary.md` 存在
  - [x] `.env.example` `MAX_ACTIVE_RUNS_PER_GOAL` + `PII_FILTER_ENABLED` 兩行均命中
- [ ] **法務 / Security 共審 PII minutes 簽核**（2026-05-19 排程；模板 `SD06_W0_PII_Legal_Review_Minutes.md` 已就位）
- [ ] **Architect / SA / SD / QA / PM 五方共審 ADR-SD06-001**（2026-05-19 排程；草稿已就位）

> **狀態**：G0 驗證命令全綠 ✅；尚欠 **2 項共審簽核** ⏳（皆排定 2026-05-19，符合 G0 啟動日 2026-05-20 前置時序）。

---

## 6. 風險聲明與 mitigations

| 風險 | 等級 | mitigation | 狀態 |
|------|------|-----------|------|
| **PII ENUM 不足覆蓋未來欄位** | 🟠 中 | (1) RESERVED_1 / RESERVED_2 後擴占位已預留；(2) W3 過濾器設計時若發現新類別，可走 RESERVED 升級而非 alembic migration；(3) 法務 minutes 強制列入 10 候選欄位審查 | 🟢 mitigation 就位 |
| **法務 minutes 共審日延誤** | 🟠 中 | (1) 模板 2026-05-17 已就位；(2) 共審日固定 2026-05-19 EOD；(3) 若延誤則 G0 啟動日（2026-05-20）後推，PM contingency 3 PD 可吸收 | ⏳ 待 2026-05-19 |
| **ADR-SD06-001 開放議題未收斂** | 🟠 中 | (1) 草稿已列 4 開放議題（事件編號 / 中斷往返路徑 / Coordinator 失敗回退 / Layer 1.5 metrics 命名）；(2) 五方共審日 2026-05-19 收斂；(3) 收斂結果寫回 W1-T1-3 Coordinator 落地 | ⏳ 待 2026-05-19 |
| **AC Matrix scaffolding 漂移** | 🟢 低 | (1) 29 條 skip case 含 1 entry count 守門；(2) W1~W6 開工時每 Wave 將對應 skip 替換為實測，違反則 G1~G6 不放行；(3) `TestMutationCoverage` 模式可套用至後續 Wave | 🟢 mitigation 就位 |
| **T0-7 .env.example 漂移**（後續開發者刪改）| 🟢 低 | (1) `.env.example` 變更需走 PR；(2) W2-T2-16 `test_max_active_runs_guard.py` 會反向驗證 env 讀取邏輯，間接守門 | 🟢 mitigation 就位 |

---

## 7. 簽核欄

| 角色 | 姓名 | 簽核日 | 狀態 |
|------|------|--------|------|
| **Tech Lead** | Tech Lead (claimed by Claude Code agent) | 2026-05-17 | ✅ 已簽核（本 Breakdown 對應 codebase 8 個檔案 + G0 驗證命令均已驗證）|
| **PM** | （待填）| （待 2026-05-18 ~ 2026-05-19）| ⏳ 待 PM 確認本 Breakdown 對齊 SD_06 v1.2 §5 / PM 8 項拍板 |
| **Architect** | （待填，ADR-SD06-001 共審日填）| 2026-05-19 | ⏳ 連動 ADR 五方共審 |
| **SA** | （待填）| 2026-05-19 | ⏳ 連動 ADR 五方共審 |
| **SD** | （待填）| 2026-05-19 | ⏳ 連動 ADR 五方共審 |
| **QA** | （待填）| 2026-05-19 | ⏳ 連動 ADR 五方共審 + PII minutes |
| **法務 / Security** | （待填）| 2026-05-19 | ⏳ 連動 PII minutes |

---

## 8. 變更歷程

| 版本 | 日期 | 變更摘要 | 編製者 |
|------|------|---------|--------|
| v1.0 | 2026-05-17 | 初版發布；T0-1 ~ T0-8 全數落地檔案驗證；G0 驗證命令全綠；尚欠 2 項共審簽核（PII minutes / ADR-SD06-001），均排定 2026-05-19。對應 SD_06 v1.2 §5 W0 = 4 PD（PM #11 +1 PD）。 | Tech Lead (claimed by Claude Code agent) |
