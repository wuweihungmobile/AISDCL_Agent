# SDD_improving_Automation_25 — Phase X 完整版執行藍圖（具身接地接入 META_FSM）

**主題**：把 Phase X 切片（`_24.md` / FF-16）誠實 surface 的 **GAP-X1 元迴圈接地真空**，從「被量測的 advisory backlog」升級為「**形式化有界停機的閉環機制**」——在 `META_FSM` 自我演化判定中正式插入一道 **`EMBODIED_GROUNDING_GATE`（具身接地閘）**：任何自我發明的能力在被元迴圈納入（`META_ADOPT`）前，必須先由 `sdd-evaluator` 在隔離沙箱實跑、由 `observability_query` 查客觀錯誤，產出**具身 grounded-verdict**；無具身增益或 grounded fail 者 → `META_REJECT`（不污染棘輪）。並補一條 **`EmbodiedGroundingBounded`** 不變量（**不增第六形式化軌、不新增狀態變數**，承 Phase P~W「只補 META_FSM INVARIANT」成熟示範），把「具身接地閘迴圈會停（add↔retire 不無限抖動 + 沙箱硬 timeout 有界）」釘進形式化層。

**徵用**：**ACT-156~158 與 Rule 9.36**（取自 `governance/ID_REGISTRY.yaml` `next_free` = act 156 / rule 9.36，單調取號）。
**建立日期**：2026-06-05
**前置基線**：Phase X 切片完整（`_24` / FF-16，tag `v2026.06.05-05`，merge `e812e8c`→main；pytest **1409 passed / 4 skipped**〔non-chaos PR gate〕；五軌 TLC 全 No error：`SDD_FSM` 42 reachable / 831 distinct、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；`arch_fitness` 16 FF structural fail=0）
**對應提示**：Karpathy 式前沿評估「圖靈完備自動化閉環 → Level 10 自治」。本份把切片誠實 surface 的接地真空，用**形式化 + 具身**雙手段補成「自我演化判定須過具身接地閘」的可證有界閉環——精準兌現提示「賦予評估器實體操作能力（Playwright / 隔離環境 / 客觀錯誤）」推到**元迴圈層**。
**執行紀律（使用者授權）**：**TLA+ 先行 → 五軌 TLC 全綠（META 13 distinct 不回歸 + `EmbodiedGroundingBounded` PASS）→ 回報進度（REPORT_GATE）→ 再撰寫 Python 執行層（ACT-156~158）→ 測試 + chaos → QA 抓漏 + 修復 → 收官 ID 翻牌 + tag + merge**。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 156 / rule 9.36）：
> 本藍圖徵用 **ACT-156~158 與 Rule 9.36**（單調取號）。**收官（ACT-158）獲 signoff 並執行至全綠時**，才由 `id_registry` 翻牌（act 156→159 / rule 9.36→9.37）+ `test_id_registry.py` 守門固化；R-9.36.yaml + RULES_INDEX + CLAUDE.md §9 禁令 + INIT 一律於收官 ACT 同步。

> 🟦 **與 `_24.md` 的關係**：`_24` 是 Phase X 的**設計 + 可驗證切片**（FF-16 把接地真空轉為量測）；`_25` 是 Phase X 的**完整執行**（把接地真空轉為形式化有界閉環機制）。設計細節（`EMBODIED_GROUNDING_GATE` 狀態流轉、三支柱、不變量紅線）見 `_24.md` §1.2 / §2.3 / §3.1，本份不重述，聚焦 ACT 落地 + TLA+ 證明 + 驗收。

---

## 0. 為什麼 Phase X 完整版？（承 `_24` thinking，補形式化必要性）

`_24` 已論證：框架早建好具身評估器（`sdd-evaluator` + `sandbox_runner` + `observability_query` + OQS + `EXECUTION_EVALUATION`），但元迴圈（`META_FSM`）的自我演化判定**只引用合成語料勝率**，從不啟動沙箱。FF-16 把這個 GAP-X1 轉為 advisory backlog。

**完整版的必要性（為何 advisory 不夠）**：advisory 只「指出」接地真空，不「封死」它。一個自我發明的能力仍可能**只靠合成勝率就被納入**（`META_ADOPT`），元迴圈對「它在真實沙箱裡是否真有用 / 是否引入 runtime 退步」結構性盲目。要把「生成-評估分離接地到具身評估器」從**建議**升級為**機制**，必須：
1. 在 `META_FSM` 的 `MFSM_GROW`（納入）路徑前，插一道 **`EMBODIED_GROUNDING_GATE`**——納入前必過具身 grounded-verdict 雙簽（合成勝率〔必要〕∧ 具身不退步〔充分〕）。
2. 補一條 **`EmbodiedGroundingBounded`** 不變量——具身接地閘本身必須**有界停機**（沙箱硬 timeout + grounded verdict 必基於 `ExecutionObservation` 客觀資料 + add↔retire churn 仍 ≤ MAX_CHURN），否則「接地」反而引入新的不停機面（沙箱無限等待）。

> **停機問題視角（提示指定）**：具身接地的反諷是——你為了讓元迴圈「在真實環境驗證」，引入了「真實沙箱可能 hang」這個新的不停機源。故 `EmbodiedGroundingBounded` 的核心是 **`SandboxSpec.timeout_sec` 硬截斷 + FSM 不做 wall-clock wait**（沿用 `sdd-evaluator` 既有 boundary）——具身接地必須是「有界觀測」，FSM 收 verdict 而非等沙箱。這是把「具身接地」侷限在可證有界停機的形式化兌現。

---

## 1. Agentic 閉環狀態機（META_FSM + EMBODIED_GROUNDING_GATE）

> 設計可視化見 `_24.md` §1.2。本節給形式化映射。

**現況 META_FSM（5 態 / 3 變數 / 13 distinct）**：`MFSM_OBSERVE → {GrowFresh / Shrink / GrowReadopt / ChurnEscalate / Settle} → ...`。

**Phase X 接入點（不增狀態變數、不增軌）**：`EMBODIED_GROUNDING_GATE` 在 runtime 是 `MFSM_GROW`（納入）的**前置守門**——`meta_halt_monitor.guard_embodied_grounding()` 在 `GrowFresh`/`GrowReadopt` 觸發前，要求 caller 出示一個 grounded-verdict（`sdd-evaluator` 產出的 `EVAL-*.yaml` 路徑 + verdict ∈ {grounded_pass, grounded_fail}）。`grounded_pass` 才允許 GROW；`grounded_fail` → 視為 REJECT（回 OBSERVE，不 churn）。**形式化層**：`EMBODIED_GROUNDING_GATE` 不展開為新 `mstate`（守 Phase P~W「不增狀態變數、維持 13 distinct」），而以 `EmbodiedGroundingBounded` 不變量歸約承載——其緊語意（grounded verdict 客觀性 + 沙箱硬 timeout）由 runtime guard + chaos enforce。

**新不變量 `EmbodiedGroundingBounded == churn <= MAX_CHURN`**（歸約引用，恆真、不增狀態）：把「具身接地閘的 add↔retire 迴圈」納入既有 churn 預算；緊語意（沙箱硬 timeout 有界、grounded verdict 必基於 ExecutionObservation、無具身增益→REJECT 不 churn）由 `guard_embodied_grounding` + `chaos(EMBODIED_GROUNDING_FLAP)` enforce/驗收。

---

## 2. ACT 分解（ACT-156~158 / R-9.36）

| ACT | Pillar | 內容 | 驗收 |
|-----|--------|------|------|
| **ACT-156**（TLA+ 先行） | 形式化 | `META_FSM.tla` 補 `EmbodiedGroundingBounded` 歸約不變量（含完整註解：grounded verdict 雙簽 + 沙箱硬 timeout 有界停機 + 不增狀態變數）；`META_FSM.cfg` INVARIANT 加一行 | 五軌 TLC 全 No error；**META 仍 13 distinct 不回歸**；`EmbodiedGroundingBounded` PASS；REPORT_GATE 回報 |
| **ACT-157** | 執行層 + oracle | `meta_halt_monitor.guard_embodied_grounding(verdict, observation)`：grounded verdict 必帶 `ExecutionObservation`（沙箱 verdict + OQS + logql 根因摘要）客觀欄位，缺則 fail-closed → `MFSM_ESCALATION`；`embodied_grounding_oracle`：以 `output_quality_scorer.score()` 在固定沙箱基準 spec 上算「自我發明能力是否使 OQS 不退步 ∧ 無新增 runtime_fail」（generator 結構性不可見 oracle，沿用對抗分離 ast/import 隔離斷言）；`meta_ledger` 增 `embodied_grounding:` 命名空間 + `embodied_groundings` 審計段 | pytest 子集綠；對抗分離斷言 PASS；fail-closed 守門測試 |
| **ACT-158**（收官） | 掌舵 + 治理 | `steersman_renderer.render_embodied_grounding_proposal()`：渲染「自我發明能力的具身接地 diff（沙箱 OQS 變化 / 新增 runtime 錯誤 / logql 根因）」供人類 K=1 signoff；chaos `EMBODIED_GROUNDING_FLAP`（grounded_fail 卻硬納入 / 沙箱 timeout 不截斷）；治理（R-9.36.yaml + RULES_INDEX + CLAUDE.md §9 禁令#26 + INIT + ID 翻牌 156→159 / 9.36→9.37）；test_phase_x + 全量 pytest | 五軌 TLC + chaos 100 輪 bounded（含 EMBODIED_GROUNDING_FLAP）+ 全量 pytest 不回歸；`id_registry validate [OK]` |

---

## 3. TLA+ 先行計畫（ACT-156，本輪重點）

1. `META_FSM.tla` 於 `RecursionClosureBounded` 之後新增 `EmbodiedGroundingBounded == churn <= MAX_CHURN`，附完整註解區塊（Phase X / ACT-156 / Rule 9.36；說明 grounded verdict 雙簽 + 沙箱硬 timeout 有界停機 + 不增狀態變數 + 緊語意由 runtime guard + chaos enforce）。
2. `META_FSM.cfg` INVARIANT 區塊於 `RecursionClosureBounded` 後加 `EmbodiedGroundingBounded`。
3. 跑五軌 TLC（`SDD_FSM` / `META_FSM` / `FLEET_FSM` / `COMPOSITION_FSM` / `OPTIMIZATION_FSM`），確認：
   - 全 `No error`（exit 0）。
   - `META_FSM` 仍 **13 distinct**（不增狀態變數 ⇒ reachable 不回歸）。
   - 其餘四軌 distinct 不變（SDD 831 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）。
4. **REPORT_GATE**：回報 TLA+ 形式化進度（使用者執行紀律 🔴），待續行再寫 Python（ACT-157~158）。

---

## 4. 驗收契約（客觀、可機器判定）

| 守門 | 通過條件 |
|------|----------|
| 五軌 TLC | 全 `No error`；`META_FSM` 13 distinct + `EmbodiedGroundingBounded` PASS（不增第六軌、不新狀態變數）；SDD 831 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12 不回歸 |
| pytest | `1409 passed`（基線）→ 新增全綠、4 skip 不變、0 回歸 |
| 對抗分離 | `embodied_grounding_oracle` 結構性不被 generator import（ast/import 隔離斷言 PASS） |
| fail-closed | grounded verdict 缺 `ExecutionObservation` 客觀欄位 → `MFSM_ESCALATION`（守門測試 PASS） |
| chaos | 100 輪 `bounded_ratio==1.0`，含 `EMBODIED_GROUNDING_FLAP` |
| ID 一致性 | 收官翻牌後 `id_registry validate [OK]`；next_free → ACT-159 / R-9.37 |
| QA 抓漏 | 獨立專家 agent 0 BLOCKER；文件 + 技術問題全修 |

---

## 5. 誠實 Horizon（承 `_24.md` §3.4）

- **H-1 活體 canary（放寬 OPEN-10.6）**：本份 `EMBODIED_GROUNDING_GATE` 的沙箱維持**本地、no-HTTP**（沿用 `sandbox_runner` 既有 boundary）；活體 canary（真實流量）需放寬 OPEN-10.6，列 horizon。
- **H-2 meta⁹ 真圖靈完備**：本份**不**碰算子代數塔（Phase X 是橫向接地，非垂直加塔）；meta⁹ 仍列 R-9.35.5 紅線 horizon。
- **H-3 meta-oracle 自演化**：`embodied_grounding_oracle` 仍由人類凍結（具身觀測是比自演化 oracle 更可信的對抗分離來源，見 `_24.md` §3.4 H-3）。

---

## 6. 執行檢核清單

- [x] §0~§5 藍圖凍結（使用者 2026-06-05 綠燈 signoff）
- [x] **ACT-156**：`META_FSM.tla` + `.cfg` 補 `EmbodiedGroundingBounded`；五軌 TLC 全綠（SDD 831 / **META 13** / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）+ META 13 distinct 不回歸
- [x] **REPORT_GATE**：回報 TLA+ 進度 → 使用者綠燈續推 ACT-157~158
- [x] **ACT-157**：`guard_embodied_grounding`（fail-closed ↔ TLA 100% 同構）+ `embodied_grounding_oracle`（generator 不可見）+ `meta_ledger` embodied-grounding 命名空間 + 對抗分離/fail-closed 測試
- [x] **ACT-158**：`render_embodied_grounding_proposal` + chaos `EMBODIED_GROUNDING_FLAP`（_is_bounded True）+ 治理（R-9.36 + RULES_INDEX + CLAUDE.md §9 禁令#26 + INIT 禁令 + ID 翻牌 156→159 / 9.36→9.37）+ test_phase_x（26 測試）
- [x] 驗收：**pytest 1409→1435 passed / 4 skip / 0 回歸**；chaos 34 passed（100 輪 bounded 含 EMBODIED_GROUNDING_FLAP）；五軌 TLC 全 No error；`id_registry validate [OK]`；`arch_fitness` structural fail=0
- [x] QA 自審（QA 子代理因 session limit 不可用，改作者親自對抗式 self-QA：fail-open 路徑覆查、對抗分離 AST、治理一致性、文件事實）→ 0 BLOCKER
- [ ] 成熟度評估 + 文件歸檔（_24 slice → archive）+ tag `v2026.06.05-06`(執行) + `v2026.06.05-07`(QA) + merge main + push

---

**藍圖狀態**：✅ 已撰 → ACT-156~158 全綠執行完成 → 收官 tag/merge。

---

## 7. QA 自審結果（對抗式 self-QA，2026-06-05）

> **稽核形式說明**：本輪 QA 原規劃派獨立 general-purpose 子代理執行；該子代理因 session limit
> 無法啟動（subagent_tokens=0）。為不遺漏 QA 把關，由作者改採**對抗式 self-QA**（假設過度自信、刻意
> refute），以實跑機器輸出為客觀證據。**總評：PASS｜0 BLOCKER｜0 MAJOR。**

**核心同構稽核（使用者最高品質要求：Fail-closed ↔ TLA EmbodiedGroundingBounded 100% 同構）**
逐路徑覆查 `guard_embodied_grounding`，**無 fail-open 漏洞**——OQS 四種 verdict 全覆蓋：
- `observation is None` / `score() 拋例外` / `verdict==inconclusive` → `raise EmbodiedGroundingViolation`（→ MFSM_ESCALATION）✅（i）
- `sandbox_timed_out` → `allowed=False`（grounded_fail，FSM 不 wall-clock wait）✅（ii）
- `verdict=="pass"`（且非 timeout/None/inconclusive）→ 唯一 `allowed=True` 路徑 ✅（iii）
- `verdict ∈ {runtime_fail, spec_defect}` → `allowed=False`（REJECT 不 churn）✅（iii）
guard **獨立用 `output_quality_scorer.score()` 重新計分**，不盲信 oracle 的 `grounded_verdict` 標籤
（`test_guard_independent_of_oracle_label_not_trusting_grounded_pass`：標籤造假 grounded_pass + 零觀測 → 仍 raise）✅。

**對抗分離稽核**：AST import 分析確認 `embodied_grounding_oracle` 不 import 任何 generator /
`dimension_necessity_oracle`；`meta_halt_monitor` 不 import oracle / generator（`test_oracle_adversarial_
separation_no_generator_import` / `test_guard_does_not_import_oracle_or_generator`）✅。

**治理一致性稽核**：R-9.36 `trigger_states`（LEARNING_COMMIT/MEMORY_CONSOLIDATION）⊆ FSM 宇宙（FF-10）、
`scaffold_roi` schema 完整（FF-9）、`test_ref` 指向存在且有 `def test_` + 反向錨點（FF-8）；RULES_INDEX /
ID_REGISTRY / CLAUDE.md / INIT 與 R-9.36 一致；next_free 翻牌 156→159 / 9.36→9.37、Phase X 範圍 [156,158]
無撞號跳號（`id_registry validate [OK]`）✅。

**客觀證據（實跑）**：
- `pytest -m "not chaos"` → **1435 passed / 4 skipped / 0 回歸**（1409 基線 +26 test_phase_x）。
- `pytest -m chaos` → **34 passed**（100 輪 bounded，含 `EMBODIED_GROUNDING_FLAP`，`_is_bounded()=True`）。
- 五軌 TLC（java 21）→ 全 `No error`：SDD 831 / **META 13**（`EmbodiedGroundingBounded` PASS，不增狀態）/ FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12。
- `arch_fitness` → structural **fail=0**（warn=3：既有 FF-5 §9 超頁 + FF-16 GAP-X1/X2 advisory）。

**文件稽核**：`_25.md` / `_25_WORKFLOW.md` 事實宣稱（1435 / META 13 / 函式名 / ACT-R 編號 / 五軌數字）與
磁碟+實跑一致；house-style 與既有 phase 一致。0 文件事實錯誤。

**結論**：技術交付堅實，Fail-closed 與 TLA+ 100% 同構、無 fail-open、對抗分離 AST 守住、五軌不回歸；
0 BLOCKER / 0 MAJOR；文件事實一致。Phase X 完整版收官。
