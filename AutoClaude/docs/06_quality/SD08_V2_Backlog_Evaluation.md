# SD_Improving_07 §5 v2 Backlog 評估報告（SD_08 W1）

| 項目 | 內容 |
|------|------|
| 文件版本 | v1.0（SD_Improving_08 W1-T1-B5 落地） |
| 建立日期 | 2026-05-18 |
| 對應 Wave | SD_08 W1（B 議題群） |
| 對應 PM 拍板 | SD_08 PM #7（議題群優先順序 A→F→D→C→E→B→G→H，B 屬「評估性」優先 4） |
| 對應前置文件 | [SD07_Migration_Guide.md §5](../08_deployment/SD07_Migration_Guide.md) v1.0 / [SD_Improving_08.md §1 / §3 W1](../04_planning/SD_Improving_08.md) v1.0 |
| 維護者 | 專案團隊 |

---

## 1. 目的與範圍

SD_Improving_07 W6 Migration Guide §5 列出三項 SD_08 v2 backlog 非阻塞優化項：

1. `_impl.py` 物理行精簡（wc-l 530 → 邏輯行 ≤ 500，邏輯行已合規）
2. `_runner_internals must not be imported` importlinter contract 拔除（SD_06 §7.2 明示**不**拔除）
3. `prompt_builder.py` 416 LOC 是否拆 package（W0 已 override 至 service tier）

SD_08 W1 對三項各自做出**獨立決議**並落地書面理由，避免後續 Sprint 再次討論。

**決議基準**：
- PM 拍板 SD_08 整體優先順序 G + H 議題群（性能 baseline + PG 前置），B 議題群屬「美學改善」優先 4
- 符合 ADR-SD07-001 分級制 + .loc-budget.toml override 雙簽機制
- 不引入額外風險（架構紅線 ❌1~❌20 不可違反）

---

## 2. 三項決議總表

| # | 項目 | 決議 | 理由摘要 | 對應追蹤 |
|---|------|------|---------|---------|
| 1 | `_impl.py` 物理行精簡 | **(a) 維持現狀（合規）** | wc-l 530 含 docstring/註解/空白；邏輯行 ≤ 500 service tier 達標；.loc-budget.toml override 雙簽明示 | §3 |
| 2 | `_runner_internals` contract 拔除 | **不拔除（永久維護）** | 三層防護（Rule 3 + Rule 6 + grep test）防 god-class 復活；SD_06 §7.2 明示；新建 Anti_Resurrection_Guard.md 文件化 | §4 |
| 3 | `prompt_builder.py` 拆 package | **(a) 維持 .loc-budget.toml override** | 416 LOC 純函式集中可讀性高於分散；ADR-SD07-001 §4.4 已豁免；拆 package 反致呼叫端散亂 | §5 |

**整體影響**：
- 0 行程式碼變動（無拆解 / 無 import 路徑改動 / 無 API 變動）
- 1 份新文件落地（[Runner_Internals_Anti_Resurrection_Guard.md](Runner_Internals_Anti_Resurrection_Guard.md)）
- 0 條 importlinter rule 變動（維持 6 kept）
- 0 條 LOC budget override 變動

---

## 3. 項目 #1 — `_impl.py` 物理行精簡

### 3.1 現況

| 量測項 | 數值 |
|--------|------|
| 物理行 wc-l | **530** |
| 邏輯行（去 docstring + 註解 + 空白後） | **≤ 500** ✅ |
| 對應 ADR-SD07-001 tier | service tier ≤ 500（已合規） |
| .loc-budget.toml override | 已落地（書面理由：「物理 wc-l 530 含 docstring/註解/空白，邏輯行 ≤ 500 service tier 達標」） |
| SD_07 W1 拆解後抽出檔案 | `_escalation_handler.py`（302 LOC）+ `_correction_helpers.py`（185 LOC） |

### 3.2 候選方案

| 方案 | 動作 | PD 預估 | 風險 |
|------|------|---------|------|
| **(a) 維持合規（推薦）** | 不動程式碼；保留 .loc-budget.toml override；列入 SD_09 季度 review | 0 | 無 |
| (b) 拆 `_attempt_loop.py` + `_state_transitions.py` | 進一步抽出 state machine 純函式區塊 | 2 PD | (1) 拆解後呼叫端轉接層增加；(2) 既有 17+ 測試 patch path 改動；(3) 觸及 W4 物理拔除過的 patch path 風險 |

### 3.3 決議：**(a) 維持合規**

**理由**：
1. **合規優先**：邏輯行 ≤ 500 已達 service tier 上限，.loc-budget.toml override 已雙簽明示（書面理由完整）
2. **PM 優先順序**：B 議題群屬「美學改善」優先 4；本 Sprint 主軸為 G + H（性能 baseline + PG 前置），不應消耗 2 PD 於非阻塞拆解
3. **回歸風險**：W4 才剛物理拔除 5 處 patch path（`_consecutive_compact_failures` / `_prepend_global_goal_brief` / `PlaybookResult`），再次拆解可能觸發新一輪 patch path 遷移
4. **量測一致性**：物理 wc-l > 邏輯行屬正常現象（docstring + inline 註解佔比約 5~6%），非真實 god-class 徵兆
5. **絕對紅線 750 仍有充足緩衝**：當前 530 距絕對紅線 220 行，新增功能尚有空間

### 3.4 後續追蹤

- 列入 [.loc-budget.toml](../../.loc-budget.toml) `[overrides]` 段（已落地）
- SD_09 季度 review 時重新評估（如 W4 P1 增強 / W5 H 議題群有新增程式碼導致逼近 750，需提前評估）
- 任何後續 Sprint 修改 `_impl.py` 必須同步重跑 `python tools/check_loc_budget.py`

---

## 4. 項目 #2 — `_runner_internals` contract 拔除

### 4.1 現況

| 量測項 | 狀態 |
|--------|------|
| `autoclaude/execution/_runner_internals.py` 物理檔案 | **不存在**（SD_06 W6 物理刪除 2026-05-18） |
| importlinter Rule 3 `runner-internals-isolation` | 仍 KEPT（防復活柵欄） |
| importlinter Rule 6 `runner-no-checkpoint-logic` | 仍 KEPT（SD_07 W5 新增） |
| `tests/contract/test_runner_no_checkpoint_logic.py` | 3 case 全綠（grep-based 防護） |
| SD_06 §7.2 明示 | 「**不會**於 SD_07/SD_08 移除」 |

### 4.2 候選方案

| 方案 | 動作 | 風險 |
|------|------|------|
| **不拔除（推薦）** | 維持 Rule 3 + Rule 6 + grep test 三層防護；新建文件化（本 SD_08 W1 動作） | 無 |
| 拔除 | 移除 Rule 3 + Rule 6 + grep test | **🔴 高風險** — 失去防 god-class 復活的三層柵欄；未來新人重建 `_runner_internals.py` 並寫入 mixin logic 將無工具阻擋；違反 SD_06 §7.2 明示 |

### 4.3 決議：**不拔除（永久維護）**

**理由**：
1. **SD_06 §7.2 明示書面限制**：「本 contract 持續維護，**不會**於 SD_07/SD_08 移除」
2. **三層防護互補**：Rule 3 防 import 圖違規 / Rule 6 防 checkpoint internal API 直接呼叫 / grep test 防 copy-paste — 三者缺一不可
3. **0 維護成本**：檔案不存在時 grep test 永遠回 0，importlinter 規則對空 target 也不會 false positive
4. **未來幾何成本高**：6~12 個月後新人若重建同名檔案並引入 god-class，回滾代價 >> 維護防護柵欄成本
5. **本決議落地形式**：新建 [Runner_Internals_Anti_Resurrection_Guard.md](Runner_Internals_Anti_Resurrection_Guard.md) v1.0 — 文件化三層防護全景 + 「絕對不可移除」清單，避免後續 Sprint 誤判拔除

### 4.4 後續追蹤

- [Runner_Internals_Anti_Resurrection_Guard.md](Runner_Internals_Anti_Resurrection_Guard.md) v1.0 已落地（SD_08 W1-T1-B3 交付）
- 任何後續 Sprint 提出拔除 Rule 3 / Rule 6 / grep test 的 PR，須在 PR description 引用 Anti_Resurrection_Guard.md §3 並由 Architect + QA 雙簽
- importlinter / pytest 任一觸發 broken 即觸發 [SD08_Execution_Guide.md §5 緊急停止與回退協議](../05_development/SD08_Execution_Guide.md)

---

## 5. 項目 #3 — `prompt_builder.py` 416 LOC 拆 package

### 5.1 現況

| 量測項 | 數值 |
|--------|------|
| 物理行 wc-l | **416** |
| 對應 tier（預設） | strategy tier ≤ 300（**超 116 行**） |
| .loc-budget.toml override | 已落地至 service tier（書面理由：「純函式集中可讀性高於分散；ADR §4.4 已豁免（SD_07 W1/W5 評估）」） |
| 公開純函式數量 | 集中多個獨立純函數於同檔（correction / compact / global_goal 三類） |
| 對應 ADR | ADR-SD07-001 §4.4 純函式庫例外條款 |

### 5.2 候選方案

| 方案 | 動作 | PD 預估 | 風險 |
|------|------|---------|------|
| **(a) 維持 .loc-budget.toml override（推薦）** | 不動程式碼；保留 service tier override（已落地） | 0 | 無 |
| (b) 拆 `_correction.py` + `_compact.py` + `_global_goal.py` 三檔 | 按函式類別拆 sub-module | 1.5 PD | (1) 既有 13+ 呼叫端 import 路徑改動；(2) 純函式分散後呼叫端散亂；(3) 跨檔 helper 重複定義或 transitive import 增加 |

### 5.3 決議：**(a) 維持 .loc-budget.toml override**

**理由**：
1. **ADR-SD07-001 §4.4 明示**：「純函式庫例外（多個獨立純函數可共處；拆散反致呼叫端散亂）」— prompt_builder.py 完全符合此例外
2. **可讀性實測**：416 行純函式集中於同檔，閱讀者可一次理解全局（correction / compact / global_goal 三類交互關係明確）；拆散後跨檔 jump 反致認知負擔上升
3. **PM 優先順序**：B 議題群屬「美學改善」優先 4，不應消耗 1.5 PD 於非阻塞拆解
4. **絕對紅線 750 仍有充足緩衝**：當前 416 距絕對紅線 334 行
5. **override 已雙簽**：.loc-budget.toml 書面理由已落地，CI 不會 false positive

### 5.4 後續追蹤

- 維持 [.loc-budget.toml](../../.loc-budget.toml) `[overrides]` 段（已落地）
- SD_09 季度 review 時重新評估（如新增函式逼近 600 行，需重新討論拆 package）
- 任何後續 Sprint 修改 `prompt_builder.py` 必須同步重跑 `python tools/check_loc_budget.py`

---

## 6. G1 驗證對應

對應 [SD08_Execution_Guide.md §3 W1 G1 驗證](../05_development/SD08_Execution_Guide.md)：

| G1 驗證項 | 期望 | 對應本文件 |
|----------|------|----------|
| `ls docs/06_quality/Runner_Internals_Anti_Resurrection_Guard.md` | 存在 | §4.4 後續追蹤已落地 |
| `ls docs/06_quality/SD08_V2_Backlog_Evaluation.md` | 存在 | 本文件 |
| `PYTHONUTF8=1 lint-imports --config .importlinter` | 6 kept / 0 broken | §4 不拔除確認維持 |
| `python tools/check_loc_budget.py` | violations=0 | §3 + §5 維持 override 確認維持 |
| `python -m pytest tests/ -q --tb=no \| tail -3` | ≥ 2,015 passed（持平 W0） | 0 程式碼變動，預估持平 2,028 |

---

## 7. 對應參考文件

- [SD07_Migration_Guide.md §5](../08_deployment/SD07_Migration_Guide.md) v1.0 — v2 backlog 三項原始登錄
- [SD_Improving_08.md §1 / §3 W1](../04_planning/SD_Improving_08.md) v1.0 — Sprint 規劃
- [SD08_Execution_Guide.md §3 W1](../05_development/SD08_Execution_Guide.md) v1.0 — 執行協議
- [Runner_Internals_Anti_Resurrection_Guard.md](Runner_Internals_Anti_Resurrection_Guard.md) v1.0 — 項目 #2 配套文件
- [ADR-SD07-001-loc-policy.md](../04_planning/ADR/ADR-SD07-001-loc-policy.md) v1.0 — LOC 分級政策 + §4.4 純函式庫例外條款
- [.loc-budget.toml](../../.loc-budget.toml) — 兩條 override 落地位置
- [.importlinter](../../.importlinter) — Rule 3 / Rule 6 配置

---

## 8. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | 首版落地 — SD_Improving_08 W1-T1-B5 三項決議：(1) `_impl.py` 維持合規 / (2) `_runner_internals` contract 不拔除（配套 Anti_Resurrection_Guard.md）/ (3) `prompt_builder.py` 維持 override |
