# SDD_improving_Automation_24_WORKFLOW — Phase X 動態自我修正執行工作流

**用途**：詳細執行 [`SDD_improving_Automation_24.md`](SDD_improving_Automation_24.md)（Phase X：具身接地轉向 + 鷹架代謝 genesis + meta⁹ 誠實 horizon）的 **dynamic workflow**——一套「生成 → 評估 → 合約談判 → 修復 → 停機」的自我修正 Agentic 閉環，把藍圖 §6 檢核清單逐項落地並以**客觀守門**（pytest / arch_fitness / QA 抓漏）驗收。
**建立日期**：2026-06-05
**前置**：藍圖 §0~§7 已撰；基線 pytest **1401 passed / 4 skipped**（non-chaos PR gate，commit `0e860cb`）、五軌 TLC 全 No error、`arch_fitness` 15 FF structural fail=0〔含 1 條既有 FF-5 advisory（CLAUDE.md §9 超頁），全量 score=1〕、`next_free`=ACT-156 / R-9.36（本輪**不動**）。
**執行策略（使用者 2026-06-05 拍板）**：**可驗證切片 + push 前讓我看**——本輪只落 FF-16（FSE 路線圖 R16），實跑 pytest 驗收，派 QA agent 抓漏 + FIX agent 修復；完成後給成熟度評估 + diff 摘要，🔴 **使用者確認才 tag/push/merge**。

> 本工作流自身即藍圖 §0 哲學的**自我示範**：它把「停止加塔、開始接地與代謝」這個轉軸決定，用**最小可驗證、走既有 FSE 自我演化通道、不消耗重型 ACT/R 機制**的方式落地——正是 Anthropic「大膽移除冗餘鷹架」在執行紀律上的對應（不為一條架構守門啟動五軌 TLA 重型機制）。

---

## 1. 動態執行狀態機（Generate / Evaluate / Contract-Negotiation）

```
            ┌──────────────────────────────────────────────────────────────┐
            │                  WORKFLOW_FSM（Phase X 執行）                  │
            └──────────────────────────────────────────────────────────────┘

  [PLAN_FROZEN] ──signoff──► [CONTRACT_NEGOTIATION] ──► [GENERATE] ──► [EVALUATE]
       ▲（藍圖 §0~§7 凍結）   （FF-16 開發前先定           （實作 FF-16     （arch_fitness --only FF-16
       │                       測試/驗收契約=Gen↔Eval       + 接 main +     + pytest 子集 + 全量
       │                       對測試標準共識）             +回歸測試）       not-chaos 不回歸守門）
       │                                                                          │
       │                                       ┌──────PASS───────────────────────┤
       │                                       ▼                                  │FAIL
       │                                  [QA_AUDIT]                              ▼
       │                                       │                                [FIX]（依評估器客觀
       │                            ┌─0 issue──┤ issues                          │ 錯誤修，不擴張範圍、
       │                            ▼          ▼                                 │ 不註解測試）
       │                       [VERIFIED]  [FIX_DISPATCH]──► 回 EVALUATE          │
       │                            │                                            │
       │                            ▼                                            │
       │                   [MATURITY_ARCHIVE]──► 🔴 [HUMAN_PUSH_GATE]            │
       │                   （成熟度評估+歸檔）    （使用者確認才 tag/push/merge）  │
       │                                                                         │
       └───retry 觸頂 / Spec 矛盾 / token≥95% ──► [HALT_ESCALATION]（導人類舵手）◄┘
```

### 狀態定義與守門

| 狀態 | 動作 | 離開條件（客觀） | 對應藍圖 |
|------|------|------------------|---------|
| `PLAN_FROZEN` | 藍圖 §0~§7 凍結，待人工 signoff | 人工 signoff（🔴，使用者已給「兩者並陳 + 可驗證切片」拍板） | §0~§7 |
| `CONTRACT_NEGOTIATION` | 開發**前**先寫 FF-16 的測試/驗收契約（Gen↔Eval 對「FF-16 該守什麼、合成 fail 案例長怎樣」達成共識） | FF-16 測試斷言契約落定 | §4 驗收 |
| `GENERATE` | 實作 `check_ff16_*` + 接 `main()`/`--only`/docstring + 回歸測試 | 檔案寫完 | §4 |
| `EVALUATE` | 跑客觀守門：`arch_fitness --only FF-16` + `pytest tests/test_arch_fitness.py` + 全量 `pytest -m "not chaos"` 不回歸 | 全綠 → PASS；否則 FAIL | §4 / §6 |
| `FIX` | **依客觀錯誤**修（不擴張範圍、不註解測試） | 重跑 EVALUATE | Rule 4 |
| `QA_AUDIT` | 派 Architect/SA/SD/QA 專家 agent 抓漏（文件 + 技術） | 0 issue → VERIFIED；有 issue → FIX_DISPATCH | 使用者指令 |
| `FIX_DISPATCH` | 派 agent 修復全部 QA issue（文件 + 技術全修） | 回 EVALUATE 全綠 | 使用者指令 |
| `VERIFIED` | FF-16 + QA 全綠、1401→新基線不回歸 | → MATURITY_ARCHIVE | §6 |
| `MATURITY_ARCHIVE` | 成熟度評估 + 文件歸檔（_24 / _24_WORKFLOW → archive/）+ diff 摘要 | 產出評估與摘要 | 使用者指令 1+2 |
| `HUMAN_PUSH_GATE` | 🔴 **使用者確認才** tag(`v2026.06.05-XX`)+push+Merge main | 使用者輸入「確認 push」 | 使用者指令 3（拍板「push 前讓我看」） |
| `HALT_ESCALATION` | 停機求援（導人類補工具/環境/修藍圖驗收標準） | 等人工（🔴 絕不自動恢復） | §5 / Rule 9.5 |

---

## 2. 停機問題防護（Halting Guardrails）— 絕不無限重試

本工作流自身受與被建構系統**同一套**有界停機紀律約束：

| 守門 | 上限 | 觸頂行為 |
|------|------|---------|
| 單一 FF-16 FIX 重試 | ≤ 3 次同型失敗 | → `HALT_ESCALATION`，導人類「補缺失工具/環境/修驗收標準」 |
| QA→FIX 循環 | ≤ 3 輪 | 第 3 輪仍有 issue → 升級人工裁決 |
| Token 預算 | ≥ 95% | 產 Context Snapshot、停機（Rule 9.2） |
| 驗收契約矛盾偵測 | FF-16 驗收契約自相矛盾（測試永不可能綠） | → `HALT_ESCALATION`，請人類修藍圖 §4 驗收標準，**不硬刻測試假綠** |

> **Self-Verification 對齊（藍圖 §5）**：若 FF-16 的驗收契約本身寫錯（例如要求「dangling 模組引用應 structural pass」這種矛盾標準），EVALUATE 會持續 FAIL；FIX 重試觸頂後**不**降級成「註解掉測試」，而是 `HALT_ESCALATION` 導人類修正——人類維持設計環境舵手高度。

---

## 3. 漸進式揭露與上下文管理（Context Degradation 防護）

- **隔離量測**：FF-16 為唯讀、確定性、無網路、無副作用的架構守門，EVALUATE 一律以 `arch_fitness`/`pytest` 的**機器輸出**為準（可觀測性接地），不靠主觀「看起來對了」。
- **結構化交接**：每完成一步（GENERATE / EVALUATE / QA_AUDIT），更新藍圖 §6 檢核清單勾選 + 本工作流狀態，作為跨步驟結構化記憶錨點。
- **客觀證據優先**：QA_AUDIT 的判定以 agent 回傳的具體 finding（檔案:行號 + 類別）為準。

---

## 4. 執行序（依藍圖 §4/§6）

1. **CONTRACT_NEGOTIATION**：定 FF-16 測試契約——合成 fail 案例（dangling 模組引用 / 缺 FSM 狀態）、clean pass、repo structural 守門、advisory surface GAP-X1/X2 的斷言。
2. **GENERATE**：實作 `check_ff16_embodied_evaluator_grounding`（structural (A) + advisory (B)）→ 接 `main()` dispatch + `--only FF-16` + 更新 docstring（15→16 FF）+ 退出碼說明 → 寫 +7 回歸測試。
3. **EVALUATE**：`arch_fitness --only FF-16`（structural pass + advisory 誠實 surface）→ `pytest tools/fsm_runtime/tests/test_arch_fitness.py`（全綠 81）→ `pytest -m "not chaos"`（1401→**1408**，0 回歸）→ `arch_fitness` 全量（16 FF structural fail=0；全量 score=3 含既有 FF-5 + FF-16×2 GAP advisory）。
4. **QA_AUDIT**：派專家 agent 抓漏（文件 + 技術）。
5. **FIX_DISPATCH**：派 agent 修復全部 issue → 回 EVALUATE 全綠 → VERIFIED。
6. **MATURITY_ARCHIVE**：成熟度評估（L 量表對賬）+ 文件歸檔（_24 / _24_WORKFLOW → `build/planning/archive/`，但**保留至 push 後再 git mv**，避免歸檔與待審 diff 混淆）+ diff 摘要。
7. **HUMAN_PUSH_GATE**：🔴 給使用者成熟度評估 + diff 摘要 → 等「確認 push」→ tag `v2026.06.05-XX` + push + Merge main。

---

## 5. 驗收契約（客觀、可機器判定）

| 守門 | 客觀通過條件 |
|------|-------------|
| `arch_fitness --only FF-16` | structural pass（`sandbox_runner`/`output_quality_scorer`/`observability_query`/`scaffold_gc` 四模組 + `EXECUTION_EVALUATION`/`SCAFFOLD_GC` 兩狀態皆解析）；advisory 誠實 surface GAP-X1（元迴圈零引用具身工具鏈）/ GAP-X2（GC 0-fire） |
| 回歸測試 | `tools/fsm_runtime/tests/test_arch_fitness.py` +7 全綠：①模組缺失 → structural fail（合成）②缺 FSM 狀態 → structural fail（合成）③agent 缺失 → structural fail（合成）④repo structural 綠燈鎖（真 repo 0 dangling + ff16-ok）⑤meta-loop ungrounded → advisory ⑥grounded → 無 advisory ⑦GC fired → 無 advisory |
| 不回歸 | `pytest -m "not chaos"`：1401→**1408** passed / 4 skip 不變 / 0 回歸 |
| arch_fitness 全量 | 16 FF structural fail=0（FF-16 advisory 不計入 structural；全量 score=3 = 既有 FF-5 + FF-16×2 GAP advisory，鏡像 FF-2/9/13 漸進哲學） |
| QA 抓漏 | 獨立專家 agent 0 BLOCKER；所有文件問題 + 技術問題全修 |
| ID 一致性 | `python -m tools.fsm_runtime.id_registry validate` → `[OK]`；`next_free` **維持** ACT-156 / R-9.36（本輪不消耗） |

> 任一守門 FAIL → 回對應 FIX 狀態；**全部綠**才進 MATURITY_ARCHIVE → 🔴 HUMAN_PUSH_GATE。

---

## 6. Claude Code CLI / 工具對照（當前正確用法）

| 意圖 | ✅ 正確（當前 CLI / 工具） |
|------|---------------------------|
| 跑 FF-16 單檢 | `python -m tools.arch_fitness.arch_fitness --only FF-16` |
| 全量 fitness（structural fail → exit 2） | `python -m tools.arch_fitness.arch_fitness --strict` |
| 回歸測試 | `python -m pytest tools/fsm_runtime/tests/test_arch_fitness.py -q` |
| 不回歸全量 | `python -m pytest -m "not chaos" -q` |
| ID 一致性 | `python -m tools.fsm_runtime.id_registry validate` |
| QA 抓漏 / FIX | Agent 工具派遣 Architect/SA/SD/QA 專家（本 harness）+ Skill（sdd-review / spec-compliance-check / code-review） |

---

## 7. 與既有 FSE 自我演化通道的整合

FF-16 是 `workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md` 路線圖的 **R16**，沿用 R1~R15（FF-1~FF-15）完全相同的落地形態：唯讀 fitness function + 回歸測試 + 自動流入 `arch-fitness.yml`（PR-advisory + nightly-strict）。**這是框架自身 §0 自陳根因「治理規則本身的熵增無收斂閘」的解法通道**——本輪用它把「具身評估器晾置 + GC 從未行使」這兩個漂移盲區，轉為被量測、被回歸守門的不變量。

> 完整版 Phase X（`EMBODIED_GROUNDING_GATE` 接進 META_FSM 自我演化判定 + `EmbodiedGroundingBounded` 不變量 + ACT-156~158 / R-9.36）列下一輪 EXECUTING 候選，需走重型 ACT/R/五軌 TLA 機制，待本輪 signoff 後另開藍圖。
