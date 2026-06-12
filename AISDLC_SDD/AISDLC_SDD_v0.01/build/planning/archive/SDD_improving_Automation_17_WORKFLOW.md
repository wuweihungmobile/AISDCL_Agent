# SDD_improving_Automation_17_WORKFLOW — Phase Q 動態自我修正執行工作流

**用途**：詳細執行 [`SDD_improving_Automation_17.md`](SDD_improving_Automation_17.md)（Phase Q：價值維度自我擴充 meta-meta 層）的 **dynamic workflow**——一套「生成 → 評估 → 合約談判 → 修復 → 停機」的自我修正 Agentic 閉環，把藍圖 §6 檢核清單逐項落地並以**客觀守門**（pytest / 五軌 TLC / chaos / QA 抓漏）驗收。
**建立日期**：2026-06-04
**前置**：藍圖 §0~§6 已撰；基線確認 pytest 1040 passed / 4 skipped、META_FSM TLC 13 distinct No error。

> 本工作流自身即藍圖 §1 哲學的**自我示範**：把「Planner 宏觀規格擴展 → Generator/Evaluator 微觀合約談判」分層、把「停機問題」用客觀守門封死、把「人類舵手」保留在 SCG/QA 確認點。

---

## 1. 動態執行狀態機（Generate / Evaluate / Contract-Negotiation）

```
            ┌──────────────────────────────────────────────────────────────┐
            │                     WORKFLOW_FSM（Phase Q 執行）                │
            └──────────────────────────────────────────────────────────────┘

  [PLAN_FROZEN] ──signoff──► [CONTRACT_NEGOTIATION] ──► [GENERATE] ──► [EVALUATE]
       ▲（藍圖凍結）              （每 ACT 開發前先定         （寫程式碼/      （pytest +
       │                          測試/驗收標準=合約）        測試/形式化/     TLC + chaos
       │                                                      治理/語料）      客觀守門）
       │                                                                          │
       │                                              ┌──────PASS────────────────┤
       │                                              ▼                           │FAIL
       │                                        [NEXT_ACT?]                       ▼
       │                                         ├─yes─► 回 CONTRACT_NEGOTIATION   [FIX]
       │                                         └─no──► [QA_AUDIT]                 │（依評估器
       │                                                    │                       │ 客觀錯誤
       │                                          ┌─0 issue─┤                       │ 修，不擴張
       │                                          ▼         │ issues                │ 範圍）
       │                                     [VERIFIED]      ▼                       │
       │                                          │      [FIX_DISPATCH]──► 回 EVALUATE
       │                                          ▼
       │                                   [TAG_PUSH_MERGE]
       │
       └───retry 觸頂 / Spec 矛盾 / token≥95% ──► [HALT_ESCALATION]（導人類舵手，絕不無限重試）
```

### 狀態定義與守門

| 狀態 | 動作 | 離開條件（客觀） | 對應藍圖 |
|------|------|------------------|---------|
| `PLAN_FROZEN` | 藍圖 §0~§6 凍結，待人工 signoff | 人工 signoff（🔴 Human gate） | §0~§6 |
| `CONTRACT_NEGOTIATION` | 開發**前**先寫該 ACT 的測試/驗收標準（= Generator↔Evaluator 對「測試標準」達成共識） | 該 ACT 的 fixture/斷言契約落定 | §3.1 各 ACT「驗收」 |
| `GENERATE` | 實作該 ACT（Python 模組 / 測試 / 形式化 / 治理 / 凍結語料） | 該 ACT 檔案寫完 | §3.1 |
| `EVALUATE` | 跑客觀守門：`pytest`（相關子集）+（ACT-125/128）五軌 TLC + chaos | 全綠 → PASS；否則 FAIL | §3.1 驗收 |
| `FIX` | **依評估器的客觀錯誤**修（不擴張範圍、不註解測試） | 重跑 EVALUATE | Rule 4 開發-測試循環 |
| `QA_AUDIT` | 派 Architect/SA/SD/QA 專家 agent 抓漏（文件 + 技術） | 0 issue → VERIFIED；有 issue → FIX_DISPATCH | 使用者指令 |
| `FIX_DISPATCH` | 派 agent 修復所有 QA issue（文件問題 + 技術問題全修） | 回 EVALUATE 全綠 | 使用者指令 |
| `VERIFIED` | 全 ACT + QA 全綠、1040→新基線不回歸 | → TAG_PUSH_MERGE | §6 |
| `TAG_PUSH_MERGE` | 日期 timestamp tag + push + Merge main | 完成 | 使用者指令 |
| `HALT_ESCALATION` | 停機求援（導人類補工具/環境/修 Spec） | 等人工（🔴 絕不自動恢復） | §5 / Rule 9.5 |

---

## 2. 停機問題防護（Halting Guardrails）— 絕不無限重試

本工作流自身受與被建構系統**同一套**有界停機紀律約束：

| 守門 | 上限 | 觸頂行為 |
|------|------|---------|
| 單 ACT FIX 重試 | ≤ 3 次同型失敗 | → `HALT_ESCALATION`，導人類「補缺失工具/環境/修 Spec」 |
| QA→FIX 循環 | ≤ 3 輪 | 第 3 輪仍有 issue → 升級人工裁決 |
| Token 預算 | ≥ 95% | 產 Context Snapshot、停機（Rule 9.2） |
| Spec 矛盾偵測 | 任一 ACT 驗收契約自相矛盾（測試永不可能綠） | → `HALT_ESCALATION`，請人類修藍圖驗收標準，**不硬刻測試假綠** |

> **Self-Verification 對齊（藍圖 §5）**：若某 ACT 的「驗收契約」本身寫錯（例如要求「噪音軸應被採納」這種矛盾標準），EVALUATE 會持續 FAIL；FIX 重試觸頂後**不**降級成「註解掉測試」，而是 `HALT_ESCALATION` 導人類修正驗收標準——人類維持「設計環境舵手」高度，而非被降級成修碼員。

---

## 3. 漸進式揭露與上下文管理（Context Degradation 防護）

- **每 ACT 隔離**：CONTRACT_NEGOTIATION 只載入該 ACT 需要的範本（Phase P 對應元件）+ 藍圖該 ACT 段落；不一次載入全部。
- **客觀證據優先**：EVALUATE 的判定一律以 `pytest`/`tlc_runner`/`chaos_runner` 的**機器輸出**為準（可觀測性接地），不靠主觀「看起來對了」。
- **結構化交接**：每完成一個 Pillar（A/B/C/D），更新藍圖 §6 檢核清單勾選 + 本工作流狀態，作為跨步驟的結構化記憶錨點。

---

## 4. 執行序（依 §3.2 依賴圖）

1. **Pillar A**：ACT-123（registry）→ CONTRACT_NEGOTIATION（寫 test_phase_q ACT-123 段）→ GENERATE → EVALUATE（pytest 子集綠）
2. **Pillar B**：ACT-124（necessity oracle + DIM 語料）→ 同上循環
3. **Pillar C**：ACT-125（meta_ledger/monitor + META_FSM.tla/.cfg）→ EVALUATE（pytest + **META_FSM TLC 13 distinct 重證**）
4. **Pillar D**：ACT-126（steersman）→ EVALUATE
5. **收官**：ACT-127（治理 + ID 翻牌）→ ACT-128（**五軌 TLC + chaos 100 輪 + 全量 pytest 不回歸**）
6. **QA_AUDIT**：派專家 agent 抓漏（文件 + 技術）
7. **FIX_DISPATCH**：派 agent 修復全部 issue → 回 EVALUATE 全綠 → VERIFIED
8. **TAG_PUSH_MERGE**：`v2026.06.04-0X`（執行）+ `v2026.06.04-0Y`（QA 稽核）→ push + Merge main

---

## 5. 驗收契約（客觀、可機器判定）

| 守門 | 客觀通過條件 |
|------|-------------|
| pytest | `1040 passed`（基線）→ 新增 ~30~40 全綠、4 skip 不變、0 回歸 |
| 五軌 TLC | `SDD_FSM`/`META_FSM`(13 distinct)/`FLEET_FSM`/`COMPOSITION_FSM`/`OPTIMIZATION_FSM` 全 `No error`（不增第六軌） |
| chaos | 100 輪 `bounded_ratio==1.0`、`avg_tokens < 20000`，含 `DIMENSION_GOODHART_FLAP` + `DIMENSION_EXPLOSION_FLAP` |
| ID 一致性 | `python -m tools.fsm_runtime.id_registry validate` → `[OK]`；next_free 翻 ACT-129 / R-9.30 |
| QA 抓漏 | 獨立專家 agent 0 BLOCKER；所有文件問題 + 技術問題全修 |

> 任一守門 FAIL → 回對應 FIX 狀態；**全部綠**才進 TAG_PUSH_MERGE。
