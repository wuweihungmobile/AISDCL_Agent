# SDD_improving_Automation_10 — Phase J 藍圖

**主題**：對抗式自我改進的現實自治（Adversarial & Self-Improving Reality-Grounded SDD）
**目標等級**：L6 → **L7 入口**（判官會主動攻擊、鷹架隨模型能力代謝、規格能自擬修補、艦隊人機介面收斂）
**建立日期**：2026-06-01
**前置基線**：Phase I 完整（ACT-059~072，L6 Trustworthy Scaled Reality-Grounded SDD，pytest 483 綠、TLC SDD_FSM + FLEET_FSM 雙證）
**狀態**：✅ EXECUTED（2026-06-01 完成 ACT-073~080；pytest 575 綠、TLC reachable 39/39、chaos bounded 1.0）。已歸檔。

> 🔴 **編號衝突告示（承 memory `project-phase-h-fork-decision`）**：
> backup 分支若日後 port「M3 Hook Health」原規劃佔用 `ACT-073+` / `Rule 9.22+`。本藍圖 **正式徵用 `ACT-073~080` 與 `Rule 9.22`**；M3 Hook Health 若要 port，必須改配 `ACT-081+` / `Rule 9.23+`，不得再撞號。

---

## 0. 為什麼還需要 Phase J？——對既有設計的誠實剖析

使用者本次提示（Karpathy 式「首席 AI 自動化架構師」）所列的前沿清單，**絕大多數已在 Phase H/I 落地**。先誠實對賬，避免重造輪子：

| 提示要求（Anthropic / OpenAI 思維） | 既有落地（不需重做） |
|--------------------------------------|----------------------|
| 生成與評估分離（GAN 啟發） | ✅ Phase H ACT-046/048：`sdd-evaluator` 獨立 context/worktree，oracle 對 `dev-senior` 不可見 |
| 主觀標準量化 | ✅ Phase G M3 `AmbiguityScorer`（6 維）+ Phase H `output_quality_scorer`（OQS verdict）|
| 評估器實體操作（Playwright/沙箱） | ✅ Phase H ACT-045 `sandbox_runner` + `DockerBackend` 真實容器執行；playwright UI（缺席降級 stub）|
| 動態演進框架、移除鷹架 | ✅ Phase H ACT-054/055 `SCAFFOLD_GC` + `rule_loader` Rule Graduation |
| 單一真實來源、漸進式揭露 | ✅ Phase H ACT-051/052 `governance/RULES_INDEX.md` + `rule_loader.load_for_state()` |
| 運行時可觀測性（LogQL/PromQL） | ✅ Phase H ACT-053 `observability_query.logql_lite/promql_lite`（守 OPEN-10.6 本地唯讀）|
| 不變量防護 + 垃圾回收 | ✅ Rule 9 全鏈 + `spec_monitor`（.tla 4 invariant 合成 runtime assertion）+ `SCAFFOLD_GC` |
| Planner→Generator/Evaluator 合約談判 | ✅ Phase H ACT-049/050 `TEST_CONTRACT_NEGOTIATED`（generator_signed gate）|
| 上下文重置與結構化交接 | ✅ Phase B `stage-compaction` + Phase D Context Governor + `CONTEXT-SNAPSHOT` 恢復鏈 |
| 停機問題 + 人類掌舵者 | ✅ FSM 有界停機 + Phase G M5 TLC 形式化證明 + Phase H ACT-056/057 `steersman_renderer` |

**結論：系統已非 L4，而是 L6。** 本次提示的 self-verification 案例（「Spec 寫錯導致測試永遠不過」）**現況即可優雅停機**（見 CLAUDE.md §9.X 軌跡：TrajectoryPredictor → SPEC_AUDIT → DiagnosticAgent 判 structural → ESCALATION_FINAL → 人工，TLC 已預證必達 terminal）。

因此 Phase J 的價值**不在重述已解決問題**，而在用同一前沿視角，挖出 L6 仍真實存在的 **4 個結構性缺口**（已用 grep 證實零實作）：

| # | 缺口（用提示自身視角挖出） | grep 證據 |
|---|---------------------------|-----------|
| **PJ-1** | **判官只會「判」不會「攻」**——GAN 缺了 discriminator 的對抗半邊。OQS 是被動 oracle，從不主動生成反例 / fuzz / property-based / metamorphic 攻擊去「弄壞」生成碼。 | `adversar\|fuzz\|property.based\|metamorphic\|counterexample` 在 fsm_runtime **零命中**（`mutation` 命中皆為 chaos 故障注入，非測試變異）|
| **PJ-2** | **鷹架代謝看不見模型能力**——提示明言「框架應隨底層模型能力提升而動態演進」。`SCAFFOLD_GC` 只看 catch/fire ROI，從不量測「底層模型變強了 → 鷹架 X 已多餘」。無模型能力基準。 | `capability\|benchmark\|competence\|envelope\|OOD` 僅命中 steersman/attention/chaos benchmark，**無模型能力基準** |
| **PJ-3** | **診斷得出卻不會自擬修補**——重複 `spec_defect` verdict 時，`steersman_renderer` 只會「請 sa-analyst 提供修正 AC」，從不草擬具體 **spec diff**。`production_to_fpl`/`slv_generator` 只產 FPL/SLV，不產 FRD/AC 補丁。 | `spec.patch\|patch_propos\|spec_diff\|propose_spec` 全 repo **零命中** |
| **PJ-4** | **艦隊把人逼成瓶頸**——M5 N 軌並行，`attention_budget` 雖去重+DIGEST，但 N 軌同時 HUMAN_PENDING 時，仍是「N 個獨立問題丟給人」，無「一個問題解鎖 N 軌」的跨軌決策聚合。掌舵者在規模下退化為「點擊工」。 | `attention_budget.route` 為單事件 severity 路由，無跨軌 decision aggregation |

---

## 1. Agentic 閉環狀態機設計（Phase J 增量）

Phase J 在已證明的單軌 SDD_FSM 上 **新增 3 個狀態**（1 gatekeep + 2 observation），並在艦隊協調層（FLEET_FSM）擴充 1 個聚合動作。所有新狀態 **必須三源同步**（`transition_rules._HAPPY_PATH` ↔ `formal/SDD_FSM.tla` ↔ `SDD_FSM_ENGINE.md`，守 Rule 9.18.1）。

### 1.1 新增狀態總覽

| 狀態 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|-------|
| `ADVERSARIAL_EVALUATION` | **gatekeep** | `EXECUTION_EVALUATION`（verdict=pass 後） | pass→`PR_REVIEW` / counterexample→`IMPLEMENTATION` / spec_gap→`SPEC_AUDIT` | 是（有界 budget）|
| `CAPABILITY_BENCHMARK` | observation | `{SCAFFOLD_GC, MEMORY_CONSOLIDATION}` | done→resume_state | 否 |
| `SPEC_PATCH_PROPOSAL` | observation | `{SPEC_AUDIT, ESCALATION}`（spec_defect 重複時） | drafted→`HUMAN_PENDING` / nodraft→resume_state | 否 |

> **競爭/合流選位說明**：`ADVERSARIAL_EVALUATION` 緊接在 `EXECUTION_EVALUATION` 之後（執行接地通過 ≠ 規格滿足，二者正交）——「能跑起來」與「擋不擋得住攻擊」是兩個獨立 verdict，比照 Phase I `SANDBOX_HARDENING_GATE → EXECUTION_EVALUATION` 的串接哲學。

### 1.2 ADVERSARIAL_EVALUATION 有界停機契約（最關鍵）

```
EXECUTION_EVALUATION(verdict=pass)
  → ADVERSARIAL_EVALUATION(budget=ADVERSARIAL_ROUND_N)
     ├─ 全 N 輪攻擊無破 → verdict=robust → PR_REVIEW
     ├─ 找到 runtime 反例（崩潰/斷言失敗，但 spec 自洽）→ counterexample → IMPLEMENTATION（計入 retry budget）
     └─ 找到 spec 反例（生成碼符合 AC 卻違反隱含 invariant / metamorphic 關係）→ spec_gap → SPEC_AUDIT
```

- **有界性**：攻擊輪數硬上限 `ADVERSARIAL_ROUND_N`（預設 8，env `SDD_ADVERSARIAL_ROUNDS` 覆寫，clamp [1,16]）；每輪攻擊本身在 hermetic 沙箱（沿用 Phase I `evaluate_hermetic` + `SecurityProfile`，`--network none`/`--cap-drop ALL`）。攻擊跑完即停，**絕不無限生成反例**。
- **去隨機**：counterexample 須在 `FLAKY_RERUN_N` 內穩定重現才採信；FLAKY 反例隔離、不計分、不進 retry（沿用 Rule 9.21.1）。
- **防判官放水**：對抗強度（攻擊種類權重）凍結於 `ADVERSARIAL_PROFILE_VERSION`，調整須 bump 版本（比照 OQS `SCORER_VERSION`，守 Rule 9.21.4 精神——判官不可自我放鬆門檻）。

### 1.3 典型軌跡（含 Phase J 改善後的 self-verification 案例）

```
SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED(generator_signed) → IMPLEMENTATION
  → SANDBOX_HARDENING_GATE(pass) → EXECUTION_EVALUATION(verdict=pass)
  → [J-1] ADVERSARIAL_EVALUATION：property-based 攻擊發現「AC 自洽但違反 metamorphic 關係 f(2x)≠2·f(x)」
     → verdict=spec_gap → SPEC_AUDIT
  → SLV 偵 AC vs INV 矛盾 → ESCALATION(reason=spec_conflict)
  → DiagnosticAgent 判 category=structural（不可 auto-recover, Rule 9.14.3）
  → [J-3] spec_defect 重複 ≥2 次 → SPEC_PATCH_PROPOSAL
     → spec_patch_proposer 產出 docs/01_requirements/SPEC-PATCH-{AC}-{date}.md（具體 AC diff + 反例證據）
     → HUMAN_PENDING（人工只需 approve/reject 一個 diff，不需從零重寫 AC）
  → 人工 approve → SPEC_DRAFTING（套用 patch）→ 重新凍結
  → [M5] TLC 已預證此路徑必達 terminal，無 deadlock
```

**對比 L6 現況**：L6 在此案例只會丟「retry exhausted / 請 sa-analyst 修 AC」給人工；Phase J 讓系統**自擬補丁 + 附反例證據**，人類維持「審核掌舵者」高度而非「從零編碼者」——精準對應提示「確保人類維持設計環境掌舵者高度」。

---

## 2. 環境建構與記憶體管理策略（Phase J 增量）

### 2.1 對抗語料與判官版本治理
- `knowledge/adversarial-patterns/`（新增）：對稱於 `failure-patterns/`(FPL) 與 `skill-patterns/`(SPL)，存放 `ADV-*.yaml` 攻擊模式（property/metamorphic/fuzz seed）。初始僅 `ADV-INDEX.md`，由 `adversarial_synthesizer` 於 `MEMORY_CONSOLIDATION` 動態結晶（≥3 次成功破防的攻擊 → proposed ADV 草案，**禁自動 verified**，比照 SPL）。
- 漸進式揭露：ADV 規則經 `rule_loader.load_for_state("ADVERSARIAL_EVALUATION")` 狀態感知 lazy load，不汙染 eager 地圖。

### 2.2 模型能力帳本（Capability Ledger）
- `build/state/capability-ledger.yaml`（新增，`file_lock.py` 保護）：記錄每次 `CAPABILITY_BENCHMARK` 的 `{benchmark_id, model_id, score, ts}`，rolling 窗口。
- 鷹架代謝判據升級：`scaffold_gc` 除既有 catch/fire ROI 外，新增 **capability-delta 訊號**——當某鷹架對應能力的 benchmark 連續 K 次滿分且該鷹架 fire/catch≈0，標記 `graduation_candidate(reason=capability_surpassed)`，仍 **必經 `rule_loader.set_maturity(reviewed_by=...)` 人工 gate**（守 Rule 9.20.5，永不自動退役）。

### 2.3 Prompt / 上下文
- Phase J 不新增常駐 eager prompt；對抗攻擊的 prompt 由 `sdd-evaluator` 在隔離 context 持有，oracle 與攻擊向量對 `dev-senior` 維持不可見（延續 Phase H 生成-評估分離，防過擬合）。
- Spec-patch 草案以 Markdown diff 形式落地 `docs/`（AI 可直接推理格式，守 OpenAI 智慧體可讀性）。

---

## 3. 終極優化藍圖：ACT 執行項（ACT-073~080）

### Pillar A — 對抗判官（PJ-1）

#### ACT-073 — Adversarial Test Synthesizer
- **檔案**：`tools/fsm_runtime/adversarial_synthesizer.py`
- **設計**：rule-based v1（零 LLM 成本預設，比照 G/H/I 慣例），4 類攻擊：
  1. `property_based`：從 AC 抽取可檢性質（單調性/冪等性/邊界），生成違反輸入。
  2. `metamorphic`：建立輸入變換關係（f(2x) vs 2f(x)、排序不變性），偵測關係破壞。
  3. `fuzz`：型別感知邊界 fuzz（空集合/極值/Unicode/NaN）。
  4. `mutation_guided`：對生成碼做語意保持變異，檢測「測試是否真能抓 bug」（弱 oracle 偵測）。
- **去隨機**：所有反例經 `evaluate_hermetic` `FLAKY_RERUN_N` 共識，FLAKY 隔離。
- **驗收**：30 fixture（15 robust 程式 + 15 含植入缺陷）；對植入缺陷的偵出率 ≥ 80%、對 robust 程式的誤報率 < 15%。

#### ACT-074 — ADVERSARIAL_EVALUATION 狀態接線
- **檔案**：`fsm_runtime.py`（`enter_adversarial_evaluation` / `exit_adversarial_evaluation`）、`transition_rules._HAPPY_PATH`、`formal/SDD_FSM.tla`、`SDD_FSM_ENGINE.md`
- **入口收緊**：僅接受 `EXECUTION_EVALUATION` 且其 verdict==pass。
- **出口**：robust→PR_REVIEW / counterexample→IMPLEMENTATION（計 retry）/ spec_gap→SPEC_AUDIT。
- **DiagnosticAgent**：新增 sub_type `adversarial_counterexample`（transient，可 1-shot auto-recovery）vs `adversarial_spec_gap`（structural，不可 auto-recover）。
- **驗收**：三源同步測試綠；TLC `SDD_FSM` 重跑 reachable 36→39（+3 態）= 100%、4 safety invariant + EventuallyTerminal + ObservationsTransient 全 PASS。

### Pillar B — 能力代謝（PJ-2）

#### ACT-075 — Capability Benchmark Harness
- **檔案**：`tools/fsm_runtime/capability_benchmark.py` + `build/state/capability-ledger.yaml`
- **設計**：一組凍結的小型確定性任務（對應每個鷹架想防的失敗類），跑當前模型、量測通過率。純離線、可重現、零外網。
- **驗收**：12 tests；ledger atomic write + file_lock；同輸入重跑分數穩定。

#### ACT-076 — Capability-Driven Scaffold Graduation + CAPABILITY_BENCHMARK 觀測態
- **檔案**：`scaffold_gc.py`（擴充）、`rule_loader.py`（`propose_graduation(reason=capability_surpassed)`）、FSM 三源（`CAPABILITY_BENCHMARK` observation）
- **規則**：capability-delta 僅「建議」退役 → **人工 `set_maturity(reviewed_by=)` gate**，永不自動退役 active 規則（守 Rule 9.20.5 / RuleOverwriteProtected）。
- **驗收**：10 tests；非阻塞、transient、有離開 transition；TLC 同步。

#### ACT-077 — Competence Envelope / OOD Early-Halt（advisory）
- **檔案**：`tools/fsm_runtime/competence_envelope.py`
- **設計**：以 `pattern_matcher.is_same_pattern` 比對當前任務 vs FPL/SPL/ADV 語料分佈；相似度低於 `OOD_THRESHOLD`（預設 0.3）→ 標記 `out_of_competence`（advisory），建議 SCG-0 早期 escalation。**不新增 FSM 狀態**（比照 AmbiguityScorer，做為 gate pre-check 餵入既有 escalation），降低 FSM 表面積。
- **守則**：advisory only（守 Rule 9.11.3 精神），不自動阻塞；人工確認才升級。
- **驗收**：15 tests；20 fixture（10 in-distribution + 10 OOD）分類準確率 ≥ 75%。

### Pillar C — 規格自癒（PJ-3）

#### ACT-078 — Spec-Patch Proposer + SPEC_PATCH_PROPOSAL 觀測態
- **檔案**：`tools/fsm_runtime/spec_patch_proposer.py`、FSM 三源（`SPEC_PATCH_PROPOSAL` observation）、模板 `docs_template/sdd/requirements/SPEC-PATCH-TEMPLATE.md`
- **設計**：spec_defect verdict 重複 ≥2 次（沿用 `pattern_matcher` 語意同模式）→ 進 `SPEC_PATCH_PROPOSAL`：
  - 蒐集反例證據（來自 ADVERSARIAL_EVALUATION / SLV / EXECUTION_EVALUATION）。
  - 產出 `docs/01_requirements/SPEC-PATCH-{AC}-{date}.md`：具體 AC before/after diff + 反例 + 影響面（RTM 受影響 TC）。
  - 出口固定 → `HUMAN_PENDING`（人類只 approve/reject diff）。
- **嚴格守則**：
  - **絕不自動套用** spec patch（守 Rule 8 人工確認 + Rule 9.21.9 advisory）；草案 `trust_level: proposed`、`source: spec_defect-auto-generated`。
  - IMPLEMENTATION 期間此狀態本身不寫 docs/01~03（由 HUMAN_PENDING 後的 SPEC_DRAFTING 套用，守 Phase D hook 約束）。
  - 同一 AC 的 SPEC-PATCH 全 session ≤ 2 次，超限直升 ESCALATION（防 patch 抖動）。
- **驗收**：18 tests；patch 產出含 before/after/反例三段；重複限流測試綠；TLC 同步、非阻塞 transient。

### Pillar D — 艦隊人機介面（PJ-4）

#### ACT-079 — Fleet Decision Aggregator（協調層，不污染單軌 FSM）
- **檔案**：`fleet_orchestrator.py`（擴充 `aggregate_pending`）+ `attention_budget.py`（擴充跨軌聚類）
- **設計**：N 軌同時 HUMAN_PENDING 時，以 `pattern_matcher` 對「待決問題」聚類；同根因問題合併為 **一個 decision request**，標註「approve 此項將解鎖 K 軌」。產出 `build/reports/fleet/DECISION-DIGEST-{date}.md`。
- **硬白名單**：P0/structural 問題永不折疊（守 Rule 9.21.10）。
- **形式化**：此為協調層（FLEET_FSM 之上），**不塞進單軌 SDD_FSM.tla**；若引入新等待狀態則在 `FLEET_FSM.tla` 證明 `AllEventuallyDone` 不回歸（無 symmetry 的 `FLEET_FSM_LIVENESS.cfg`，守 Rule 9.21.13）。
- **驗收**：12 tests；N=5 軌同根因聚合為 1 問題；P0 不折疊測試綠。

### 收官

#### ACT-080 — Phase J 形式化重證 + 全綠驗收
- **三源同步**：3 新 SDD_FSM 狀態（ADVERSARIAL_EVALUATION / CAPABILITY_BENCHMARK / SPEC_PATCH_PROPOSAL）入 `SDD_FSM.tla` 對應 HappyStates/ObservationStates 集合 + `_HAPPY_PATH` + MD。
- **TLC**：`SDD_FSM` reachable 36→39 = 100%；safety 4 invariant + `EventuallyTerminal` + `ObservationsTransient` 全 PASS（ADVERSARIAL_EVALUATION 為 gatekeep，須確保不引入新非 terminal cycle——其 budget 有界即為論證關鍵）。`FLEET_FSM` `LockMutex`/`NoPartialHold`/`AllEventuallyDone` 不回歸。
- **Chaos**：100 輪（新增 `ADVERSARIAL_FLAKY` 故障型）bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：目標 **≈ 580 passed**（483 + 約 97：J-1 30 / J-2 22 / J-3 33 / J-4 12）。

---

## 4. 防護規則新增（CLAUDE.md §9.22 Phase J）

> 待執行完成後，將下列子規則正式寫入 CLAUDE.md §9.22（此處為草案，供 SCG-0 審視）。

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.22.1 對抗有界 | ACT-073/074 | `ADVERSARIAL_EVALUATION` 攻擊輪數硬上限 `SDD_ADVERSARIAL_ROUNDS`（clamp[1,16]）；FLAKY 反例不計分不進 retry |
| 9.22.2 判官不自我放水 | ACT-073 | 對抗強度權重凍結於 `ADVERSARIAL_PROFILE_VERSION`，變更須 bump 版本（比照 SCORER_VERSION）|
| 9.22.3 能力代謝人工 gate | ACT-076 | capability-delta 僅「建議」退役；退役 active 規則必經 `set_maturity(reviewed_by=)`，永不自動 |
| 9.22.4 OOD advisory-only | ACT-077 | `out_of_competence` 不自動阻塞，僅建議早 escalation；人工確認才升級 |
| 9.22.5 spec patch 絕不自動套用 | ACT-078 | `SPEC_PATCH_PROPOSAL` 只產 `proposed` 草案 → HUMAN_PENDING；同 AC ≤2 次，超限 ESCALATION |
| 9.22.6 艦隊聚合不折疊 P0 | ACT-079 | 跨軌 decision aggregation 對 P0/structural 永不合併/折疊 |
| 9.22.7 三源 + 雙形式化同步 | ACT-074/076/078/080 | 3 新單軌狀態同步 `SDD_FSM.tla`；艦隊聚合若加等待態同步 `FLEET_FSM.tla` liveness |

### ❌ Phase J 新增禁止行為（草案）
- 對抗判官把 FLAKY 反例當真實 counterexample 丟進 IMPLEMENTATION retry（破 9.22.1）
- 調整對抗強度權重不 bump `ADVERSARIAL_PROFILE_VERSION`（破 9.22.2，判官自我放水）
- capability-delta 訊號自動退役 active 鷹架而不經 `reviewed_by`（破 9.22.3 / RuleOverwriteProtected）
- 讓 `out_of_competence` advisory 自動阻塞 SCG（破 9.22.4）
- `spec_patch_proposer` 自動套用 patch 改 FRD/AC 而不經 HUMAN_PENDING（破 9.22.5 / Rule 8）
- 跨軌 aggregator 折疊 P0/structural decision（破 9.22.6）
- 新增 3 態不同步 `SDD_FSM.tla` / 艦隊等待態不重證 `FLEET_FSM` liveness（破 9.22.7 / Rule 9.18.1）
- 把 `ADVERSARIAL_EVALUATION`（gatekeep）誤列為 observation 或放入 Terminals（破有界 gatekeep 契約）

---

## 5. Self-Verification Protocol（內部模擬：Spec 寫錯 → 測試永不過）

| 階段 | L6 現況行為 | Phase J 強化後行為 |
|------|------------|--------------------|
| 偵測 | EXECUTION_EVALUATION verdict=pass（碼能跑），但隱含 invariant 未被 AC 涵蓋 → 漏網直到 PR_REVIEW retry | **ADVERSARIAL_EVALUATION metamorphic 攻擊當場抓出** spec_gap |
| 中斷 | TrajectoryPredictor 2 信號 → SPEC_AUDIT → SLV 偵矛盾 → ESCALATION → structural → ESCALATION_FINAL | 同左，**但多一層提前攔截**（對抗判官在 PR 前就轉 SPEC_AUDIT，省 retry）|
| 引導人類 | steersman：「retry exhausted，請 sa-analyst 提供修正 AC」（人類從零重寫）| **SPEC_PATCH_PROPOSAL 自擬 AC diff + 反例證據** → 人類只 approve/reject（掌舵者高度）|
| 有界性 | TLC 已證必達 terminal | 對抗輪數 budget 有界 + patch ≤2 次限流，TLC 重證無新 cycle |
| Token | 不浪費（早停）| **更省**（PR 前攔截 + 人類一次修對，免去多輪 PR_REVIEW）|

✅ **模擬通過**：系統能透過（新的對抗）Evaluator 發現 spec 異常，優雅中斷，並**自擬修補草案**引導人類介入，而非無限重試。人類維持「設計環境掌舵者」高度——這正是提示的終極驗收標準。

---

## 6. 執行順序與里程碑

```
M-J1 對抗判官：ACT-073 → ACT-074（FSM+TLC）   ── 先做，價值最高（補 GAN 缺半）
M-J2 規格自癒：ACT-078                          ── 緊接，直接放大 M-J1 的人機價值
M-J3 能力代謝：ACT-075 → ACT-076 → ACT-077      ── 中期，長線維護槓桿
M-J4 艦隊介面：ACT-079                           ── 規模化後才有壓力，可延後
M-J5 收官：ACT-080（三源 + 雙形式化 + chaos + pytest 全綠）
```

**每個 M-Jx 完成即跑該層 pytest + 必要時 TLC，絕不累積**（守 Rule 4 開發-編譯-測試循環）。

---

## 7. 待人工決策（OPEN-J）

| ID | 議題 | 建議預設 |
|----|------|---------|
| OPEN-J.1 | 對抗判官 v1 是否限 rule-based（零成本）抑或允許 LLM 攻擊生成？ | ✅ **RESOLVED 2026-06-01**：rule-based v1（守 G/H/I 慣例）；LLM 留 v2 並更新成本 gate |
| OPEN-J.2 | `SDD_ADVERSARIAL_ROUNDS` 預設值（8）是否合適？ | 預設 8，env 可調 [1,16]（執行時可再校準）|
| OPEN-J.3 | spec patch 是否允許多檔 diff（FRD+RTM 同改）抑或單檔？ | 預設單 AC 範圍，跨檔影響只「標註」不自動改 |
| OPEN-J.4 | 編號徵用 ACT-073~080 / Rule 9.22 是否確認（排擠 M3 Hook Health）？ | ✅ **RESOLVED 2026-06-01**：確認徵用；M3 Hook Health 改配 ACT-081+/Rule 9.23+ |

---

**藍圖等級目標**：L6 → **L7 入口 — Adversarial & Self-Improving Reality-Grounded SDD**（判官主動對抗 + 能力感知鷹架代謝 + 規格自癒 + 艦隊人機收斂）
**前置 SCG**：本藍圖須通過 SCG-0（需求凍結）人工審視後，方可逐 ACT 執行。
