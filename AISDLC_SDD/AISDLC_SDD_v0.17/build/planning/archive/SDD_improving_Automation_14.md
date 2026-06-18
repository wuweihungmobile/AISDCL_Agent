# SDD_improving_Automation_14 — Phase N 藍圖

**主題**：全域組合最佳化 + NP-hard 搜尋形式化停機（Global Composition Optimization with Bounded-Search Formal Halting）
**目標等級**：L10 完整奠基（組合級一致，Phase M）→ **L10 完整（組合級最優）** —— 不只證「N 意圖組合**一致**」，更證「在一致排程中找**全域最優**」，且形式化證明這個 **NP-hard 最佳化搜尋本身有界停機**（永不指數爆炸無限搜尋）。
**建立日期**：2026-06-03
**前置基線**：Phase M 完整（ACT-097~104 / R-9.25，pytest 885 綠、COMPOSITION_FSM No error 21 distinct、四軌 TLC No error）。
**OPEN-M.7 裁決**：✅ 使用者 2026-06-03 拍板 **暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary）續列 horizon；Phase N 全力推**不需放寬、純離線/形式化**的 L10 完整。
**狀態**：✅ **EXECUTED 2026-06-03（L10 完整：組合級最優 + NP-hard 搜尋形式化停機達成）** — 使用者 signoff（OPEN-M.7 暫不放寬沙箱 + OPEN-N 全採建議預設值），ACT-105~110 全部完成。**驗收：pytest 912 passed / 7 skipped（Phase M 885 → +27 Phase N）；OPTIMIZATION_FSM TLC No error（12 distinct，5 safety + EventuallyScheduled liveness）+ 離線 BFS reachable=5/5；五軌 TLC 全 No error 不回歸（SDD_FSM 308 / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）；chaos 29 passed（含 OPT_SEARCH_STORM，100 輪 bounded_ratio=1.0）；單軌 OPT_* 零洩漏（Rule 9.26.2 隔離成立）。** QA/Architect 抓漏稽核：BLOCKER 0 / MAJOR 0，4 MINOR（write_report 落盤、lower_bound 死碼、gap 語意、escalated 耦合）已全數修復並重驗。

> 🔴 **編號徵用**（承 `governance/ID_REGISTRY.yaml` `next_free`）：徵用 **ACT-105~110 與 Rule 9.26**（前緣 act=105 / rule=9.26）。收官（ACT-109）翻牌 + `test_id_registry.py` 守門。

---

## 0. 缺口（grep 證零實作）

Phase M 的 `COMPOSITION_FSM` + `intent_composer` 證了組合**一致性**（衝突解或升級，`RenegotiationBounded`），`composition_blast_analyzer` 建議序列化，`value_planner` 逐意圖 ROI 排序。**但無任何元件做「全域最優排程」**：給定 N 個一致意圖，在「高 blast 意圖不可同批並行 + 批量 ≤ K」約束下，找**最少批次/最低總成本**的全域排程——這是 NP-hard（圖著色/裝箱型），naive 搜尋指數爆炸。更關鍵：**無形式化證明這個最佳化搜尋本身會停機**。

| 缺口 | grep 證據（`tools/`） |
|---|---|
| **PN-1** 全域組合最優 + NP-hard 搜尋形式化停機：缺 bounded branch-and-bound 最佳化器 + 證 SearchBounded/EventuallyScheduled 的獨立 `OPTIMIZATION_FSM` | `composition_optimizer\|OPTIMIZATION_FSM\|branch_and_bound\|optimization_halt\|objective_scorer` **零命中** |

---

## 1. Agentic 閉環狀態機設計（Phase N 增量）

對單軌 `SDD_FSM` **零表面積**（維持 42/42）。最佳化層比照 META/COMPOSITION_FSM 採**獨立命名空間** `OPTIMIZATION_FSM`，不污染單軌。

### 1.1 OPTIMIZATION_FSM 有界搜尋停機契約（L10 完整奠基石）
```
（最佳化搜尋層，狀態變數 = {ostate, expanded（已展開節點數）, found（是否已找到可行排程）}）
OPT_OBSERVE → OPT_EXPAND（展開節點，expanded++，可能 found→1）⇄ OPT_PRUNE（界限剪枝後續搜）
  ├─ found=1 → OPT_SCHEDULED（產出最優/best-so-far 排程）
  ├─ expanded≥MAX_NODES 且 found=1 → OPT_SCHEDULED（預算耗盡，回 best-so-far + gap）
  └─ expanded≥MAX_NODES 且 found=0 → OPT_ESCALATION（預算內找不到可行排程，人工：放寬預算/拆問題）
```
- **5 safety**：`TypeOK`、`SearchBounded`（expanded ≤ MAX_NODES，永不超預算）、`ScheduledImpliesFound`（OPT_SCHEDULED ⟹ found=1，不無中生有排程）、`EscalationExhausted`（OPT_ESCALATION ⟹ expanded=MAX_NODES ∧ found=0，非過早）、`StableIsFixpoint`（OPT_SCHEDULED 吸收；OPT_ESCALATION ∉ 不動點）。
- **liveness `EventuallyScheduled`**：公平性下必抵 {OPT_SCHEDULED, OPT_ESCALATION}（`expanded` 單調遞增且有界 → well-founded 下降 → 永不無限搜尋）。
- `optimization_halt_monitor`：runtime 守門，node 展開預算 `SDD_OPT_NODE_BUDGET`（clamp[8,4096]，預設 256）；超限導 OPT_ESCALATION。

### 1.2 最佳化器（runtime, bounded branch-and-bound）
`composition_optimizer`：圖著色型最佳化——意圖為頂點，「共享高 blast 節點」為邊（不可同批），批量 ≤ K，**最小化總成本**（批次數 + 批內殘餘 blast）。bounded B&B：node 預算上限、admissible 下界剪枝、deterministic 展開序；回 `schedule + nodes_expanded + optimal(bool) + gap`。預算內無可行解 → escalate。**advisory：只推薦排程，絕不自動 commit**（最終仍經 `BACKLOG_PRIORITIZED` 人工 signoff，守 Rule 8 / 9.23.2 / 9.25.1）。

### 1.3 全域目標評分（凍結版本）
`composition_objective_scorer`：成本 = `batch_count × BATCH_W + intra_batch_blast × BLAST_W − total_value × VALUE_W`（凍結 `OBJECTIVE_PROFILE_VERSION`，調權重須 bump）。純函式、deterministic、advisory。

---

## 2. 環境/記憶體（守 OpenAI 漸進式揭露 + OPEN-10.6）
- `tools/fsm_runtime/formal/OPTIMIZATION_FSM.tla` + `.cfg`（獨立命名空間）。
- `build/reports/optimization/OPT-SCHEDULE-{date}.md`（最優排程 + gap + 證據，餵 steersman；advisory）。
- 不新增常駐 eager prompt；搜尋在隔離邏輯內、結論才回主線。全產物純文字、無外網（守 OPEN-10.6）。

---

## 3. ACT 執行項（ACT-105~110）
- **ACT-105** `composition_objective_scorer.py`（全域目標，凍結版本）+ 測試。
- **ACT-106** `composition_optimizer.py`（bounded B&B：SearchBounded + optimal/gap + escalate）+ 測試（含已知最優小 fixture、預算有界、deterministic、infeasible→escalate）。
- **ACT-107** `formal/OPTIMIZATION_FSM.tla/.cfg` + `optimization_halt_monitor.py` + `tlc_runner` 擴充 + 離線 BFS 測試（reachable=5/5 + 每態可達 terminal + 雙源狀態一致 + cfg 宣告）+ opt-in TLC。
- **ACT-108** 整合：`steersman_renderer.render_optimal_schedule`（advisory）+ 排程推薦（不自動 commit）+ 測試。
- **ACT-109** 治理：`R-9.26` yaml + `RULES_INDEX` + 根 `CLAUDE.md §9` 禁令#16 + 速查列 + `AISDLC_SDD_INIT.md` 禁止事項 + `ID_REGISTRY` 翻牌（act 105→111 / rule 9.26→9.27）+ `test_id_registry.py` 前緣斷言 + Phase N ownership 測試。
- **ACT-110** `chaos_runner` 新增 `OPT_SEARCH_STORM` 故障型（巨大搜尋空間驗 SearchBounded→OPT_ESCALATION 有界）+ test_chaos + pytest 全綠 + 五軌 TLC（SDD/META/FLEET/COMPOSITION/OPTIMIZATION）No error 不回歸。

---

## 4. 防護規則 R-9.26（草案）
| 子規則 | 約束 |
|---|---|
| 9.26.1 搜尋有界（SearchBounded） | node 展開 ≤ `SDD_OPT_NODE_BUDGET`（clamp[8,4096]，預設 256）；超限→OPT_ESCALATION，絕不指數無限搜尋 |
| 9.26.2 OPTIMIZATION_FSM 獨立形式化 | `OPTIMIZATION_FSM.tla` 自有命名空間，不併入單軌；5 safety + EventuallyScheduled No error + 離線 BFS reachable=N/N；單軌 SDD_FSM 維持 42、META/FLEET/COMPOSITION 不回歸 |
| 9.26.3 排程 advisory + 不自我裁決 | `composition_optimizer` 只推薦排程，**絕不自動 commit、繞過 `BACKLOG_PRIORITIZED` 人工 signoff**（守 Rule 8 / 9.23.2） |
| 9.26.4 目標評分不自我放水 | `composition_objective_scorer` 凍結 `OBJECTIVE_PROFILE_VERSION`，調權重須 bump；只算成本不改 spec、不阻塞 SCG |
| 9.26.5 最優性誠實 | OPT_SCHEDULED 須回報 `optimal(bool)` 與 `gap`；預算耗盡只能宣稱 best-so-far + gap，不得謊報 proven-optimal |

---

## 5. Self-Verification（Spec/排程無解 → 不可無限搜尋）
極端案例：給一組「任兩意圖皆共享高 blast 節點」且 K 過小 → 無可行著色。Phase N：B&B 展開至 `SDD_OPT_NODE_BUDGET` 仍 found=0 → `SearchBounded` 觸頂 → `OPT_ESCALATION`，導人類（放寬 K / 拆問題 / 接受序列化），**絕不指數無限搜尋燒 token**。形式化 `EventuallyScheduled` 數學保證必停。人類舵手升至「審全域排程最優界限與最優性 gap」。

---

## 6. Horizon（本份不做）
- **L9 完整（活體 canary）**：OPEN-M.7 已裁決暫不放寬 OPEN-10.6，續列 horizon，待真實生產整合需求再評。
- **元最佳化形式化**：未來若最佳化器本身可學習調參，需把該學習迴圈納入 META_FSM ChurnBounded（承既有元停機基座）。

## 7. OPEN-N（已隨 signoff 採建議預設）
| ID | 議題 | 建議（已採） |
|---|---|---|
| OPEN-N.1 | 徵用 ACT-105~110 / R-9.26 | ✅ 確認，收官翻牌 |
| OPEN-N.2 | `SDD_OPT_NODE_BUDGET` 預設 256 / 批量 K 預設 3 | ✅ env 可調，執行時校準 |
| OPEN-N.3 | 最佳化器 v1 限 rule-based B&B（零 LLM）| ✅ 守 G~M 慣例；LLM 啟發式留 v2 |
| OPEN-N.4 | 是否放寬 OPEN-10.6（L9 完整）| ❌ 暫不（承 OPEN-M.7） |

**等級目標**：L10 完整奠基（組合一致）→ **L10 完整（組合最優 + NP-hard 搜尋形式化停機）**。
**形式化承諾**：`OPTIMIZATION_FSM` 5 safety + `EventuallyScheduled` No error + 離線 BFS reachable=N/N；五軌 TLC 全 No error 不回歸；chaos（含 `OPT_SEARCH_STORM`）bounded_ratio=1.0。
**前置 SCG**：✅ SCG-0 PASSED（2026-06-03 使用者 signoff、OPEN-M.7=暫不放寬、OPEN-N 全採建議預設）。
