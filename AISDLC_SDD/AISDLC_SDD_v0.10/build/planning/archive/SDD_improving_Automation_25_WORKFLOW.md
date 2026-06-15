# SDD_improving_Automation_25_WORKFLOW — Phase X 完整版動態自我修正執行工作流

**用途**：詳細執行 [`SDD_improving_Automation_25.md`](SDD_improving_Automation_25.md)（Phase X 完整版：具身接地接入 META_FSM + `EmbodiedGroundingBounded`）的 **dynamic workflow**——「生成 → 評估 → 合約談判 → 修復 → 停機」的自我修正 Agentic 閉環，以客觀守門（五軌 TLC / pytest / chaos / QA 抓漏）驗收。
**建立日期**：2026-06-05
**前置**：ACT-156（TLA+ 先行）✅ 完成——`META_FSM` 補 `EmbodiedGroundingBounded`，五軌 TLC 全 No error（META 13 distinct 不回歸），全量 pytest 1409 passed。使用者於 REPORT_GATE 綠燈續推 ACT-157~158。
**執行策略**：使用者授權**一路到底**（ACT-157~158 → 測試 + chaos → QA 抓漏 + 修復 → 收官 tag `v2026.06.05-06`/`-07` + merge main + 最終報告）。**品質硬要求：`guard_embodied_grounding` 的 Fail-closed 與 TLA+ `EmbodiedGroundingBounded` 定義 100% 同構。**

---

## 1. 動態執行狀態機

```
  [TLA_DONE✅] ─► [CONTRACT_NEGOTIATION] ─► [GENERATE] ─► [EVALUATE] ─► [QA_AUDIT] ─► [FIX_DISPATCH] ─► [COLLECT]
   (ACT-156      (每 ACT 開發前先定         (寫 guard/      (pytest +    (派專家      (派 agent       (ID 翻牌 +
    五軌綠)        測試/驗收=Gen↔Eval         oracle/ledger/  五軌 TLC +   agent 抓漏   修全部 issue    R-9.36 治理 +
                   對 Fail-closed 共識)       steersman/chaos) chaos 守門)   文件+技術)    回 EVALUATE)     tag+merge)
                                                                  │FAIL                              │
                                                                  ▼                                  ▼
                                                                [FIX]──► 回 EVALUATE         [HUMAN_PUSH=已授權自動]
                                                          retry≤3 觸頂 → [HALT_ESCALATION]
```

| 狀態 | 動作 | 離開條件（客觀） |
|------|------|------------------|
| `CONTRACT_NEGOTIATION` | 開發前先定 ACT-157/158 測試契約（Fail-closed 缺 ExecutionObservation→ESCALATION；對抗分離 oracle 不被 generator import；chaos 雙故障型） | 斷言契約落定 |
| `GENERATE` | ACT-157：`guard_embodied_grounding` + `embodied_grounding_oracle` + `meta_ledger` 命名空間；ACT-158：steersman + chaos `EMBODIED_GROUNDING_FLAP` + 治理 | 檔案寫完 |
| `EVALUATE` | `pytest`（子集→全量）+ 五軌 TLC（不回歸）+ chaos 100 輪 bounded | 全綠→PASS；否則 FAIL |
| `FIX` | 依客觀錯誤修（不擴張範圍、不註解測試） | 重跑 EVALUATE |
| `QA_AUDIT` | 派 Architect/SA/SD/QA 專家 agent 抓漏（文件+技術；專查 Fail-closed↔TLA 同構） | 0 issue→COLLECT；有→FIX_DISPATCH |
| `FIX_DISPATCH` | 派 agent 修全部 issue（文件+技術全修） | 回 EVALUATE 全綠 |
| `COLLECT` | ID 翻牌 156→159 / 9.36→9.37 + R-9.36.yaml + RULES_INDEX + CLAUDE.md §9 禁令#26 + INIT + 歸檔 _24/_24_WORKFLOW → archive + tag v2026.06.05-06/07 + merge main + push | 完成→最終報告 |
| `HALT_ESCALATION` | retry≤3 觸頂 / Spec 矛盾 / token≥95% → 停機導人類 | 等人工 |

---

## 2. 停機問題防護（絕不無限重試）

| 守門 | 上限 | 觸頂 |
|------|------|------|
| 單 ACT FIX 重試 | ≤3 同型失敗 | → HALT_ESCALATION |
| QA→FIX 循環 | ≤3 輪 | 升級人工裁決 |
| Token | ≥95% | Context Snapshot 停機（Rule 9.2） |
| chaos | 100 輪須 bounded_ratio==1.0 | 否則 FAIL，不放寬 TERMINAL_STATES 假綠 |

---

## 3. Fail-closed ↔ TLA+ 100% 同構契約（品質硬要求）

| TLA+ `EmbodiedGroundingBounded` 語意 | Python `guard_embodied_grounding` 同構實作 | 守門測試 |
|---|---|---|
| grounded verdict 必基於 `ExecutionObservation` 客觀資料 | verdict 缺 ExecutionObservation 必要客觀欄位（sandbox verdict + OQS + 根因）→ `EmbodiedGroundingViolation` → `MFSM_ESCALATION` | `test_embodied_grounding_fail_closed_missing_observation` |
| 沙箱硬 timeout 截斷、FSM 不 wall-clock wait | 收 verdict（已含 timeout 結果）而非等沙箱；timeout=runtime_fail/grounded_fail | `test_embodied_grounding_sandbox_timeout_is_grounded_fail` |
| grounded_fail / 無具身增益 → REJECT 不 churn | `grounded_pass` 才允許 GROW；否則回 OBSERVE 不增 churn | `test_embodied_grounding_fail_rejects_no_churn` |
| oracle 對 generator 不可見（對抗分離） | `embodied_grounding_oracle` 結構性不被 generator import（ast/import 隔離斷言） | `test_embodied_grounding_oracle_adversarial_separation` |
| churn ≤ MAX_CHURN（add↔retire 有界） | `embodied-grounding:` 命名空間共用既有 churn 預算 | chaos `EMBODIED_GROUNDING_FLAP` |

---

## 4. 執行序

1. **ACT-157**：CONTRACT_NEGOTIATION（寫 test_phase_x ACT-157 段）→ GENERATE（`guard_embodied_grounding` + `embodied_grounding_oracle` + `meta_ledger`）→ EVALUATE（pytest 子集 + 對抗分離/fail-closed 守門綠）
2. **ACT-158**：GENERATE（steersman + chaos `EMBODIED_GROUNDING_FLAP` + 治理 R-9.36 + RULES_INDEX + CLAUDE.md §9 禁令#26 + INIT + ID 翻牌）→ EVALUATE（五軌 TLC + chaos 100 輪 + 全量 pytest 不回歸）
3. **QA_AUDIT**：派專家 agent 抓漏（專查 Fail-closed↔TLA 同構 + 文件事實）
4. **FIX_DISPATCH**：派 agent 修全部 issue → 回 EVALUATE 全綠
5. **COLLECT**：歸檔 _24/_24_WORKFLOW → archive；tag `v2026.06.05-06`(執行)+`-07`(QA)；merge main；push origin；最終報告

---

## 5. 驗收契約（客觀、可機器判定）

| 守門 | 通過條件 |
|------|----------|
| pytest | `1409 passed` → **1435 passed**（+26 test_phase_x）、4 skip 不變、0 回歸 |
| 五軌 TLC | 全 No error；META 13 distinct + `EmbodiedGroundingBounded` PASS；SDD 831/FLEET 7/COMPOSITION 21/OPTIMIZATION 12 不回歸 |
| Fail-closed↔TLA 同構 | §3 五條對照測試全綠 |
| 對抗分離 | `embodied_grounding_oracle` ast/import 隔離斷言 PASS |
| chaos | 100 輪 bounded_ratio==1.0，含 `EMBODIED_GROUNDING_FLAP` |
| ID 一致性 | `id_registry validate [OK]`；next_free → ACT-159 / R-9.37 |
| QA 抓漏 | 獨立專家 agent 0 BLOCKER；文件+技術全修 |
