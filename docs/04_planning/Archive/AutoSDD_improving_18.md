# AutoSDD_improving_18 — B 軌「鷹架代謝」L4→L5 信號：規則命中遙測接入 FSM 主迴圈

> **輪次**：N=18｜**日期**：2026-06-16｜**驅動器**：軌道①（整合迭代，範本唯一驅動器）
> **本輪柱位**：**B 柱（手腳 AISLDC_SDD）**——對齊北極星第 2 點「AI SDD 自動化閉環」。
> **下一份**：AutoSDD_improving_19（按需，待舵手 signoff）。
> **凍結來源 signoff**：🔴 人工確認方向「主推 B 軌；閉合 GAP-X2 遙測迴圈」。

---

## 1. 本輪定位與輸入繼承

### 1.1 對偶閉環延續（improving_16→17→18）
| 輪 | 接入 | 面向 |
|----|------|------|
| 16 | `propose_slv_from_fpl` 接 LEARNING_COMMIT 主迴圈 | 規則自演化「**增**」（自動提議新增規則） |
| 17 | `scaffold_gc.run_gc` 接 `enter_scaffold_gc` 主迴圈 | 鷹架代謝「**減/決策側**」（GC 自動提議退役） |
| **18** | **`record_fire` on-watch 記帳接 `transition()` 主迴圈** | 鷹架代謝「**減/遙測側**」（fire_count 真實累積） |

### 1.2 上輪繼承（improving_17）
- **已完成 W 項**：W-17-1（run_gc 接主迴圈）、W-17-2（scaffold_gc_stats）——階段一 zero-trust 複核**真實存在且 8 case 覆蓋**。
- **上輪遺留 / 本輪標的**：DEF-17-001（P3, open/routed）——代謝閉環「半接」：`run_gc` 接了但 `record_fire` 在 FSM 主迴圈零自動呼叫致 39 規則 `fire_count=0`，GC 恆產零提議。DEF-17-001 原文明列下游待辦：「把 `record_fire` 規則命中記帳接入 FSM 規則執行/守門點，使 scaffold_roi 累積真實 runtime 資料」。**本輪即執行此下游 W 項。**

### 1.3 缺陷帳本 open/routed 處置計畫
| DEF | 本輪處置 |
|-----|---------|
| DEF-17-001 | **本輪閉合 fire 側**（W-18-1/2）；殘留 catch 側轉記 DEF-18-001 |
| DEF-01-007（cc-switch 環境）| 非程式可修，本輪不觸（B 軌不涉整合層 A/B）|
| DEF-01-009（plugin 250 watch）| AutoClaude 側，本輪零擴充不觸發 |
| DEF-12-002（hook `::` 誤攔）| 共享 infra 小修，本輪不觸（守 scope）|
| DEF-15-001 深層 routed（模板寄居 runtime 目錄）| 大版重構，本輪不觸 |

### 1.4 三軸成熟度現級（階段一實測，zero-trust）
| 軸 | 現級 | 本輪變更 |
|----|------|---------|
| C 引擎（AutoClaude）| L4（萌 L5）| 無（B 軌未動 AutoClaude）|
| A 協作（橋接）| L4 信號 | 無 |
| **B 流程（SDD 代謝）**| **L4→L5 信號**（本輪續推）| 接 fire 遙測主迴圈（L5 能力，flag 預設 OFF）|

`L_合體 = min(A,B,C)` → 仍 **L4**（B 取 L5 能力但 flag 預設 OFF＝運行仍 L4，未虛報躍升）。

---

## 2. 增量設計（SCG-0~3 載體）

### 2.1 「fire（命中）」語意決策（SCG-1 介面凍結前置判斷題）
框架偵察揭露：`record_fire` 機制完整但「何時記 fire」語意從未定義。本輪採**確定性、與框架既有「規則依狀態 lazy-load」模型同構**的定義：

> **FSM 經 `transition()` 進入狀態 `dst` 時，`load_for_state(dst)` 命中的每條規則被「行使（on-watch）」一次 → `record_fire(rule_id, caught=False)`。**

理由：(1) 框架本就以 `load_for_state` 表「該狀態守望的規則」；(2) 確定性、可測；(3) caught=False＝守望計數，與 catch（真攔到問題）語意分離。

### 2.2 W 項與介面 delta（SCG-2/3）
**W-18-1**：`record_fire` on-watch 遙測接入 `transition()` 主迴圈（flag-gated、fail-closed）。
- `rule_loader.py` 新增 `record_state_fires(state, *, caught=False, rules_dir=None) -> List[str]`：單次 `load_all`、對命中規則（`"*"∈trigger_states ∨ state∈trigger_states ∧ maturity≠deprecated`）一次性增 `fire_count` 各寫一次。LOC：+~20 行（資料層函式，遠低於分級上限）。
- `fsm_runtime.py`：module 常數 `_RULE_FIRE_TELEMETRY_ENV` + `_rule_fire_telemetry_enabled()`（鏡像三前例）；`transition()` 於 `save_state` **後** flag-gated `try: rule_loader.record_state_fires(dst) except: pass`（+~9 行）。

**W-18-2**：`rule_fire_telemetry_stats()` 純讀 L5 信號 + XAI 安全證書。
- 自 `load_all` 獨立重算 fire 分佈；`fire_ladder` 降冪（fire 最高＝行使最多 critical path）；`retirement_eligible`（fire≥`GRADUATION_MIN_FIRES` ∧ catch=0）；`safety_certificate`（`auto_retire=False` + **`catch_side_wired=False` 誠實揭露**）。LOC：+~50 行（service 方法，遠低於上限）。

### 2.3 `.importlinter` 契約影響分析
- 本輪僅在 `tools/fsm_runtime/` 內新增函式/方法，無新增跨層 import；`rule_loader`/`fsm_runtime` 既有相依關係不變。AISDLC_SDD 側以 `arch_fitness` 守門（ci-gate 內），實測 structural fail=0。AutoClaude `.importlinter` 8 kept / 0 broken（本輪未動 AutoClaude）。

### 2.4 checkpoint additive 欄位需求
- 無新增 PlaybookCheckpoint 欄位（SDD 框架側非 AutoClaude DAL）。`fire_count` 增量寫入 rule YAML 內**既有的** `scaffold_roi` runtime 欄位（ACT-054 設計），additive、零 schema 變更。

### 2.5 <Architecture_Design_Review>（寫實質 Python 前已輸出）
1. **架構純潔性**：無 God-object；`transition()` 加 flag-gated try/except side-effect，批次記帳歸資料層 `rule_loader`，Thin Facade 維持。
2. **持久化相容**：`fire_count` additive 寫入既有 `scaffold_roi`，與規則邏輯（spec/trigger_states/severity 凍結）分離；零 schema 變更。
3. **安全防護網**：本輪無「從文件生成指令」路徑，不涉 CONDITIONAL；`record_state_fires` 僅讀寫既有 rule YAML（file_lock + atomic 既有機制）。
4. **對外 I/O 安全**：本輪**無**新增 `ToolInvocationPort` 外呼路徑，N/A。
5. **TLA/TLC**：純在既有 `transition()` 加非轉態 side-effect，零新 reachable 邊/狀態宇宙變更/`*.tla` 改動 → Rule 9.18.1 免五軌 TLC，以逐位元零差異佐證。
6. **零退化**：flag 預設 OFF＝`transition()` 行為逐字同 v0.08。

---

## 3. 實作與雙重驗證（SCG-4）

### 3.1 落地檔案（v0.09，Copy-on-Evolve 自 v0.08）
| 檔案 | 變更 |
|------|------|
| `tools/fsm_runtime/rule_loader.py` | +`record_state_fires`（record_fire 後）|
| `tools/fsm_runtime/fsm_runtime.py` | +`_RULE_FIRE_TELEMETRY_ENV`/`_rule_fire_telemetry_enabled`；`transition()` flag-gated 記帳；+`rule_fire_telemetry_stats` |
| `tools/fsm_runtime/tests/test_rule_fire_telemetry_wiring.py` | +8 case（新檔）|

### 3.2 測試矩陣（RTM，SCG-5）
| # | 測試函式 | 驗證意圖（Rule 9：為何重要）| W 項 |
|---|---------|---------------------------|------|
| 1 | `test_flag_off_transition_records_no_fire` | flag OFF＝零退化（fire_count 全程 0）| W-18-1 |
| 2 | `test_flag_off_explicit_zero_is_sole_switch` | flag '0' 亦零退化（flag 唯一開關）| W-18-1 |
| 3 | `test_flag_on_transition_records_on_watch_fire` | flag ON 命中規則記 fire + **選擇性**（非命中狀態不記）| W-18-1 |
| 4 | `test_flag_on_fire_count_accumulates_persisted` | 多次轉態 fire_count **累積且持久化**（閉合 fire_count=0）| W-18-1 |
| 5 | `test_telemetry_failure_fail_closed` | 記帳失敗 **fail-closed**：轉態仍完成不回滾 | W-18-1 |
| 6 | `test_red_line_telemetry_never_set_maturity` | **R-9.20 #11 紅線**：遙測全程零 set_maturity | W-18-1 |
| 7 | `test_telemetry_stats_robust_and_certificate` | stats 度量穩健 + 證書 **誠實揭露 catch_side_wired=False** | W-18-2 |
| 8 | `test_telemetry_stats_ladder_and_eligible` | fire_ladder 降冪 + retirement_eligible（fire≥門檻∧catch=0）| W-18-2 |

實測：**8 passed**（`pytest test_rule_fire_telemetry_wiring.py -q`）。

---

## 4. CI 平價收斂（階段四，全項實測，floor 以上輪實測為準）

| 檢查 | 命令 | 通過條件（floor）| 本輪實測 |
|------|------|-----------------|---------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥3112 / 0 failed | **3112 passed / 122 skipped / 0 failed** ✅ |
| 架構契約 | `lint-imports` | 全 kept | **8 kept / 0 broken** ✅ |
| LOC 分級 | `check_loc_budget.py` | 全過 | **violations=0**（17794/20438）✅ |
| Snapshot | `snapshot_sync.py --check` | 新鮮 | **OK** ✅ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | not-chaos 全綠 + arch_fitness exit<2 | **exit 0；v0.01:1478 / v0.09:1534 / scripts/tests:25；arch_fitness advisory(3) structural fail=0** ✅ |
| 五軌 TLC | （僅 FSM 變更時）| N/A | **免**（transition_rules.py + 5 *.tla 對 v0.08 逐位元 ZERO-DIFF）✅ |

> v0.09 全套 not-chaos = **1534 passed / 4 skipped**（v0.08 1526 + 8，只增不減）。
> arch_fitness FF-16 GAP-X2 advisory 仍亮（flag OFF 預設 + 無 SCAFFOLD-ROI 報告產出）＝**誠實的 L4 邊界**：本輪加 fire 遙測**能力**，但預設 OFF＝運行仍 L4，未自動產報告清 advisory。

---

## 5. 誠實揭露與成熟度校準（Rule 12）
- **閉合**：DEF-17-001 點名的 `fire_count=0` 根因（fire 側）。
- **殘留**：catch 側（`caught=True` 何時觸發之 FSM 契約未定義）→ 新立 **DEF-18-001**（P3, routed）；生產啟用退役前須先定義 catch 契約。stats 證書以 `catch_side_wired=False` 程式內誠實揭露。
- **成熟度**：交付 B 軸「L5 遙測累積能力 + 證據」；flag 預設 OFF＝運行仍 L4，**不虛報運行已達 L5、不躍報 `L_合體`**（維持 L4 信號邊界）。
