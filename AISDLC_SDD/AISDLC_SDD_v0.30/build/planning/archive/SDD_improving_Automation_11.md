# SDD_improving_Automation_11 — Phase K 藍圖

**主題**：意圖驅動的生成式規劃 + 辯證消歧 + 因果接地（Intent-Driven Generative Planning & Dialectic-Grounded SDD）
**目標等級**：L7 → **L8 入口**（人類交付「意圖/價值目標」而非「凍結規格」；系統自主分解規格 DAG、辯證消歧、因果定位；舵手高度從「AC 作者/審查者」升至「意圖/組合決策者」）
**建立日期**：2026-06-02
**前置基線**：Phase J 完整（ACT-073~080，L7 入口 Adversarial & Self-Improving Reality-Grounded SDD，pytest 575 綠、TLC `SDD_FSM` reachable 39/39、chaos bounded 1.0）
**狀態**：✅ **EXECUTED 2026-06-02（L7→L8 入口達成）** — M-K1（ACT-081/082）、M-K2（ACT-083/084）、M-K3（ACT-085/086）、M-K4（ACT-087/088 收官：R-9.23 active + ID_REGISTRY 翻牌 + CLAUDE §9.23）全部完成。驗收：**pytest 781 passed / 4 skipped 綠（含後續 chaos 兩故障型 + 離線可達性測試，及 QA 審計補強：disambiguation 落盤 / intent 結晶 / localizer 接 PBS-DRIFT 等 18 項測試；歷史里程碑當時為 740）、TLC reachable 39→41、chaos 100 輪 bounded 1.0/avg 1639 tokens（含 `INTENT_DECOMPOSE_STORM`/`DEBATE_FLAKY` 兩 Phase-K 故障型，達藍圖字面）**。里程碑標籤 v2026.06.02-02~06。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（同 [SDD_improving_Automation_10.md](../archive/SDD_improving_Automation_10.md) 之提示，本份為 L7→L8 續推）

> 🔴 **編號徵用告示（承 memory `project-phase-j-blueprint` / `project-phase-h-fork-decision`）**：
> Phase J 記憶明示「續推 L7 時從 **ACT-081+/Rule 9.23+** 起編」。本藍圖正式徵用 **ACT-081~088 與 Rule 9.23**。
> 與 Phase H fork 記錄之「M3 Hook Health 改配 ACT-081+」存在**號段衝突**：M3 Hook Health 為 backup 分支、已停滯歸檔（非正典主線）；本藍圖為主線 L8 續推，依 Phase J 指示優先徵用。
> M3 Hook Health 若日後復活，一律從 `next_free` 取號（現 **ACT-089+ / Rule 9.24+**），不預留、不撞號。
> ✅ **已由 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml) + `test_id_registry.py` pytest 守門固化**，撞號由 CI 自動攔截。詳見 §7 OPEN-K.1。

---

## 0. 為什麼還需要 Phase K？——對既有設計的誠實剖析（含 `<thinking>`）

<thinking>
本次提示是一份要求「驗證圖靈完備自動化閉環、並進化為 Level 10 自治」的 Karpathy 式評估。第一步不是設計，而是**誠實對賬**——這套系統不是白紙，而是已走過 Phase A~J、自稱 L7 入口的成熟框架。盲目套用提示的前沿清單會重造輪子；真正的工程價值在於用提示的同一視角，挖出 L7 仍真實存在、且 grep 可證零實作的**新**結構性缺口。

【一、提示前沿清單 × 既有落地對賬】（沿用藍圖 10 §0 結論，本份再次確認仍成立）
- 生成與評估分離（GAN 啟發）→ ✅ Phase H `sdd-evaluator` 獨立 context/worktree + Phase J `adversarial_synthesizer` 主動攻擊半邊。
- 主觀標準量化 → ✅ Phase G M3 `AmbiguityScorer`（6 維）+ Phase H `output_quality_scorer`（OQS）。
- 評估器實體操作（Playwright/沙箱）→ ✅ Phase H `sandbox_runner` + Phase I `evaluate_hermetic`（`--network none`/`--cap-drop ALL`）。
- 動態演進框架、移除鷹架 → ✅ Phase H `SCAFFOLD_GC` + Phase J 能力感知 graduation（capability-delta）。
- 單一真實來源、漸進式揭露 → ✅ `governance/RULES_INDEX.md` + `rule_loader.load_for_state()`。
- 運行時可觀測性（LogQL/PromQL）→ ✅ Phase H `observability_query.logql_lite/promql_lite`（本地唯讀）。
- 不變量 + 垃圾回收 → ✅ Rule 9 全鏈 + `spec_monitor`（.tla 4 invariant 合成 runtime assertion）+ `SCAFFOLD_GC`。
- Planner→Generator/Evaluator 合約談判 → ⚠️ **只完成微觀半邊**（`TEST_CONTRACT_NEGOTIATED`）；**宏觀半邊缺席**（見下）。
- 上下文重置與結構化交接 → ✅ `stage-compaction` + Context Governor + `CONTEXT-SNAPSHOT` 恢復鏈。
- 停機問題 + 人類掌舵者 → ✅ FSM 有界停機 + TLC 形式化證明 + `steersman_renderer` + Phase J `spec_patch_proposer`。

結論：**系統確已是 L7，而非提示預設的「L4 待救」。** 提示的 self-verification 案例（Spec 寫錯→測試永不過）在 L7 現況即可優雅停機。所以 Phase K 不能重述，必須挖新缺口。

【二、用提示三個指定漏洞視角，逐一往 L7 深處挖】

(A) 狀態轉換——「Planner 宏觀規格擴展 → Generator/Evaluator 微觀合約談判」分層機制。
我讀 `value_planner.py` 的 docstring 原文：「value model 只排序不裁決」、「BacklogCandidate.business_value 由人工/PM 給定」。也就是說系統的「規劃」只會對**人類已寫好的候選清單排 ROI**，從不會把一句「做功能 X」的**意圖自主分解成規格 DAG**。提示要的兩層談判，微觀半邊（Dev/QA 對 test oracle 簽署 = `TEST_CONTRACT_NEGOTIATED`）已落地，**宏觀半邊（意圖→規格擴展）整個缺席**。grep `decompos|spec_tree|spec_dag|goal_decompos|spec_planner` 在 fsm_runtime **零命中**。這是 L7→L8 最大的 autonomy 落差：L7 的人類仍須逐 Stage 手寫凍結規格；L8 的人類只交付意圖，系統自動長出規格樹。→ **PK-1**。

(B) 生成-評估分離只套在「碼」，沒套在「規格語義」。
Phase J 的對抗判官攻擊的是**生成碼**（property/metamorphic/fuzz）。但「規格本身被兩種人讀出兩種意思」這種**詮釋歧義**，目前只有 `AmbiguityScorer` 用**單視角啟發式**評分——它沒有「讓兩個隔離 agent 對同一條 AC 各自推一種詮釋、再量化分歧」的對抗辯證。這正是 Anthropic debate/constitutional 路線套到規格端：把「生成與評估分離」從 code 推廣到 **spec interpretation**。grep `debate|dialectic|two_sided|interpret_conflict` **零命中**。單視角 scorer 會漏掉「字面清晰、但兩種合理詮釋互斥」的歧義（scorer 看不到第二種詮釋）。→ **PK-2**。

(C) 絕對運行時可觀測性——暴露了訊號，卻沒閉合「訊號→規格根因」的推理。
`observability_query` 把 LogQL/PromQL 暴露給 AI，`DiagnosticAgent` 會分類 escalation 的 sub_type，但「這個 production drift / adversarial counterexample **到底是哪一條 AC/FRD 寫錯造成的**」仍由 `sa-analyst` 人工判定（Phase E M3 明列 sa-analyst 為漂移採納決策方）。系統有 RTM（AC↔TC↔FRD 追溯）+ decision_trace（決策證據鏈）這兩張現成的圖，卻沒人把它們當**因果圖**做自動 blast-radius / spec localization。grep `causal|blast_radius|localiz|root_cause|provenance` **零命中**。這讓 `spec_patch_proposer`（Phase J）雖能自擬補丁，卻仍需人類先「指出該補哪條 AC」——舵手又被拉回低空。→ **PK-3**。

【三、上下文衰減（Context Degradation）視角覆查】
Phase K 新增的意圖分解會產生一棵可能很大的 spec-DAG，有上下文膨脹風險。設計上必須：DAG 以 `build/state/spec-dag-*.yaml` **落盤**而非常駐 context（漸進式揭露），分解本身有節點硬上限，且分解完即交 `stage-compaction`。辯證消歧的兩條詮釋在隔離 context 持有、結論才回主線。→ 不引入新的脈絡焦慮。

【四、停機問題（Halting）視角覆查——這是不可退讓的紅線】
新增的「自主分解」與「辯證」天生有發散風險（無限細分、無限辯論）。所以 PK-1 的 `INTENT_DECOMPOSITION` 必為**有界 gatekeep**（分解深度/節點硬上限、DAG 必 acyclic、太模糊→`HUMAN_PENDING`）；PK-2 的 `SPEC_DEBATE` 必為**有界 observation**（輪數 clamp、transient、必有離開 transition）；PK-3 為純 advisory **不新增狀態**。兩個新狀態都要進 `SDD_FSM.tla` 重證 `EventuallyTerminal` + `ObservationsTransient`，reachable 39→41 仍 100%。**人類始終是規格 DAG 與詮釋分歧的最終 signoff**——舵手高度不降反升（從審 AC → 審意圖分解與詮釋）。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性）：意圖分解、辯證結論、因果定位三者全部落地為 **Markdown / YAML 可推理產物**（spec-DAG、disambiguation request、localization report），不藏在 prompt 裡。
- Anthropic（對抗 / 動態演進）：把「生成-評估分離」與「對抗」從 code 端**往上游推到 spec 端**（辯證 = 規格端的判官對抗），並把鷹架代謝的視角從「規則 ROI」擴到「人類意圖層」。

→ Phase K 主題定為「意圖驅動的生成式規劃 + 辯證消歧 + 因果接地」，目標 **L7 → L8 入口**。L9/L10 的「主動生產實驗 / 組合級自治 / 自我改進元迴圈形式化停機」列為 §3.4 horizon，本份不實作（受 OPEN-10.6 本地唯讀 / 無 HTTP 決策約束）。
</thinking>

本次提示所列前沿清單，**絕大多數已在 Phase H/I/J 落地**（對賬見上 thinking 一節）。Phase K 的價值不在重述，而在用提示自身視角挖出 L7 仍真實存在、grep 證零實作的 **3 個結構性缺口**：

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（fsm_runtime） |
|---|------------------------------|--------------------------|
| **PK-1** | **規劃只有微觀、沒有宏觀**——提示要的「Planner 宏觀規格擴展 → G/E 微觀合約談判」分層，只完成微觀半邊（`TEST_CONTRACT_NEGOTIATED`）。`value_planner` 只對**人類給定**的候選排 ROI（docstring 自承「只排序不裁決」、`business_value` 人工給定），無「意圖→規格 DAG」自主分解。 | `decompos\|spec_tree\|spec_dag\|goal_decompos\|spec_planner` **零命中** |
| **PK-2** | **對抗只攻碼、不攻規格語義**——生成-評估分離套在生成碼（Phase J 對抗判官），卻沒套到**規格詮釋**。`AmbiguityScorer` 是單視角啟發式，看不到「字面清晰但兩種合理詮釋互斥」的歧義。缺辯證式（兩隔離 agent 對立詮釋 + 分歧量化）消歧。 | `debate\|dialectic\|two_sided\|interpret_conflict` **零命中** |
| **PK-3** | **暴露訊號卻不自動推因到規格節點**——`observability_query` 暴露 LogQL/PromQL、`DiagnosticAgent` 分類 escalation，但「哪條 AC/FRD 造成此 drift/counterexample」仍由 sa-analyst 手動定位。RTM + decision_trace 兩張現成圖未被當因果圖做 blast-radius / spec localization。 | `causal\|blast_radius\|localiz\|root_cause\|provenance` **零命中** |

**三缺口的共同主軸**：L7 的人類仍站在「逐 Stage 手寫凍結規格 + 手動指認規格根因」的高度；Phase K 把人類抬到「交付意圖、審分解 DAG、審詮釋分歧、審已定位的補丁」的高度——這正是 L8「Intent-Driven Autonomy」的定義，也精準補上提示要求的宏觀 Planner 半邊。

---

## 1. Agentic 閉環狀態機設計（Phase K 增量）

Phase K 在已證明的單軌 `SDD_FSM` 上 **新增 2 個狀態**（1 gatekeep + 1 observation），PK-3 為 advisory 模組**不新增狀態**（比照 `competence_envelope` / `AmbiguityScorer`，降低 FSM 表面積）。所有新狀態 **必須三源同步**（`transition_rules._HAPPY_PATH` ↔ `formal/SDD_FSM.tla` ↔ `SDD_FSM_ENGINE.md`，守 Rule 9.18.1）。

### 1.1 新增狀態總覽

| 狀態 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|-------|
| `INTENT_DECOMPOSITION` | **gatekeep**（有界） | `AGENT_LOAD`（在 `BACKLOG_PRIORITIZED` 之前） | decomposed→`BACKLOG_PRIORITIZED` / underspecified→`HUMAN_PENDING` | 是（有界 budget） |
| `SPEC_DEBATE` | observation（advisory, transient） | `SCG_VALIDATION`（SCG-0 子步，AmbiguityScorer 命中邊界帶時） | consensus→resume `SCG_VALIDATION` / divergence→`HUMAN_PENDING` | 否 |

> **選位說明**：
> - `INTENT_DECOMPOSITION` 緊接 `AGENT_LOAD`、落在既有 `BACKLOG_PRIORITIZED`（Phase I `value_planner` 人工 signoff 閘）之前——它**餵料**給 value_planner，補上「候選清單從哪來」的宏觀半邊。既有 happy-path `AGENT_LOAD → BACKLOG_PRIORITIZED → SPEC_DRAFTING` 完全向後相容（加法式新增一條 `AGENT_LOAD → INTENT_DECOMPOSITION` 邊）。
> - `SPEC_DEBATE` 是 `AmbiguityScorer` 的**對抗升級**：scorer 評分落在「不清晰也不算嚴重」的邊界帶（near-threshold）時，才觸發辯證；明確清晰或明確模糊者不進辯證（省 token）。它是 SCG-0 的 pre-freeze 消歧閘，與 Phase J 的 code 端 `ADVERSARIAL_EVALUATION`（pre-PR 消缺陷閘）對稱。

### 1.2 INTENT_DECOMPOSITION 有界停機契約（最關鍵）

```
AGENT_LOAD（情境已載入 + 人類交付 high-level intent 文件）
  → INTENT_DECOMPOSITION（budget = SDD_INTENT_MAX_NODES，預設 32，clamp[4,128]）
     ├─ 成功分解成 acyclic spec-DAG → decomposed → BACKLOG_PRIORITIZED
     │     （value_planner 對自動產出的候選節點排 ROI → 人工 signoff 選最高 ROI → SPEC_DRAFTING）
     └─ 意圖過模糊 / 分解觸頂仍無法收斂 → underspecified → HUMAN_PENDING
           （要求人類補充意圖，不自行臆測 — 守 Rule 8）
```

- **有界性**：分解節點數硬上限 `SDD_INTENT_MAX_NODES`（clamp[4,128]）；分解迭代硬上限；產出 DAG **必 acyclic**（拓樸檢查，偵測環即拒絕、轉 `HUMAN_PENDING`）。分解觸頂即停，**絕不無限細分**。
- **不自我裁決**：自動產出的候選只是「建議排序入口」，**最高 ROI 仍經 `BACKLOG_PRIORITIZED` 人工 signoff**（沿用 `value_planner` 哲學與 Rule 8）；planner 永不自選目標直接執行。
- **可觀測落盤**：DAG 寫 `build/state/spec-dag-{date}.yaml`（`file_lock.py` 保護），不常駐 context（守漸進式揭露 + 防上下文衰減）。

### 1.3 SPEC_DEBATE 有界辯證契約

```
SCG_VALIDATION（SCG-0）→ AmbiguityScorer 評分落 near-threshold band [θ_low, θ_high]
  → SPEC_DEBATE（rounds = SDD_SPEC_DEBATE_ROUNDS，預設 4，clamp[1,8]）
     ├─ 兩隔離詮釋收斂（divergence < D_thresh）→ consensus → 回 SCG_VALIDATION 續跑
     └─ 兩隔離詮釋分歧（divergence ≥ D_thresh）→ HUMAN_PENDING
           （附「詮釋 A vs 詮釋 B + 該 AC + 分歧證據」disambiguation request，人類裁決）
```

- **生成-評估分離**：兩條詮釋 pass 在**隔離 context** 各自推導，彼此 oracle-blind（延續 Phase H 分離哲學，防單一視角過擬合）。
- **有界 + 不自我放水**：輪數硬上限 clamp；辯證強度（攻擊性詮釋的偏置權重）凍結於 `SPEC_DEBATE_PROFILE_VERSION`，調整須 bump 版本（比照 `ADVERSARIAL_PROFILE_VERSION` / `SCORER_VERSION`，守「判官不可自我放鬆門檻」）。
- **advisory**：divergence 不自動阻塞/改寫 AC，只導向人工澄清（守 `AmbiguityScorer` advisory 精神 + Rule 8）。

### 1.4 PK-3 因果定位（advisory，無新狀態）

`spec_localizer` 以 **RTM（AC↔TC↔FRD）+ decision_trace + spec_anchor** 合成因果圖；任一下游訊號（`ADVERSARIAL_EVALUATION` counterexample / `PRODUCTION_SIGNAL` drift / `RTM_VERIFY` gap）進來時，計算 blast-radius、輸出 ranked suspect spec 節點 + 證據鏈。結果**餵入既有狀態**（`SPEC_PATCH_PROPOSAL` / `SPEC_AUDIT` / `steersman_renderer`），取代 sa-analyst 手動指認，但**只建議不自動改 spec**。

### 1.5 典型軌跡（含 Phase K 改善後的 self-verification 案例）

```
AGENT_LOAD（人類交付意圖：「加一個含折扣的下單流程」）
  → [K-1] INTENT_DECOMPOSITION：自動分解成 spec-DAG（下單 AC、折扣規則 AC、庫存扣減 AC…）
     ├─ 偵測「折扣 AC」與「庫存扣減 AC」依賴成環 → 不可分解 → underspecified → HUMAN_PENDING（請人類釐清順序）
     └─（釐清後）acyclic DAG → BACKLOG_PRIORITIZED（value_planner 排 ROI）→ 人工 signoff → SPEC_DRAFTING
  → SCG_VALIDATION（SCG-0）：AmbiguityScorer 對「折扣可疊加？」落 near-threshold
  → [K-2] SPEC_DEBATE：詮釋 A=「折扣可疊加」 vs 詮釋 B=「折扣互斥」，divergence ≥ D_thresh
     → HUMAN_PENDING（附兩詮釋 + 證據，人類一句話定案）→ 凍結前消歧完成
  → SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION → … → ADVERSARIAL_EVALUATION（Phase J）
  →（若仍有漏網 spec_gap 到生產）PRODUCTION_SIGNAL：drift 進來
  → [K-3] spec_localizer 自動定位「= 折扣 AC-014」+ 證據 → SPEC_PATCH_PROPOSAL（Phase J 自擬 diff，現在連「補哪條」都自動）
  → HUMAN_PENDING（人類只 approve/reject 已定位 + 已草擬的補丁）
  → [M5] TLC 已預證此路徑必達 terminal，無 deadlock
```

**對比 L7 現況**：L7 在此案例（a）需人類**先手寫**下單/折扣/庫存三條規格；（b）「折扣可否疊加」的歧義靠單視角 scorer，可能漏到實作後才爆；（c）生產 drift 需 sa-analyst **手動**指認是折扣 AC。Phase K 讓系統**自動長出規格樹、辯證式凍結前消歧、自動定位生產根因**——人類三處都從「作者/偵探」升為「裁決者」，精準對應提示「確保人類維持設計環境掌舵者高度」。

---

## 2. 環境建構與記憶體管理策略（Phase K 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/spec-dag-{date}.yaml`（新增，`file_lock.py` 保護）：意圖分解產出的規格 DAG（節點=候選 AC/FRD、邊=依賴）。**落盤不常駐**，由 `rule_loader` 風格的 lazy 讀取按需載入，避免 DAG 膨脹汙染 context。
- `knowledge/intent-patterns/`（新增，對稱於 `failure-patterns`(FPL)/`skill-patterns`(SPL)/`adversarial-patterns`(ADV)）：存放 `INT-*.yaml` 分解模式（常見意圖→規格骨架）。初始僅 `INT-INDEX.md`，由分解器於成功分解後**結晶 proposed 草案**（≥3 次同型分解 → proposed，**禁自動 verified**，比照 SPL/ADV 治理）。
- `knowledge/disambiguation/`（新增）：存放 `SPEC_DEBATE` 解出的歧義對（兩詮釋 + 人類裁決），回饋 `AmbiguityScorer` 校準語料（advisory）。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 新增 runtime invariant（由 `spec_monitor` 合成）：`spec-DAG 必 acyclic`、`SPEC_DEBATE ∈ ObservationStates 且有離開 transition`、`INTENT_DECOMPOSITION ∉ Terminals`。
- 鷹架代謝銜接 Phase J 能力代謝：`intent_decomposer` / `spec_debate` 兩鷹架本身納入 `scaffold_roi` 帳本（`fire_count/catch_count/false_positive_count`），未來模型若強到能直接吐 acyclic 規格樹、辯證零分歧，仍須經 `set_maturity(reviewed_by=)` 人工 gate 才退役（守 Rule 9.20.5 / 9.22.3）。

### 2.3 Prompt / 上下文與防衰減
- Phase K 不新增常駐 eager prompt。意圖分解、辯證詮釋的 prompt 由對應 runtime agent 在**隔離 context** 持有，結論才回主線。
- 分解完成即觸發 `stage-compaction`（DAG 已落盤，主線只留摘要），辯證結論以 Markdown disambiguation request 落地——全部「AI 可直接推理格式」（守智慧體可讀性）。
- 所有新產物（spec-DAG / disambiguation request / localization report）皆 Markdown/YAML，無二進位、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-081~088）

#### Pillar A — 宏觀規劃半邊（PK-1）

**ACT-081 — Intent Decomposer**
- **檔案**：`tools/fsm_runtime/intent_decomposer.py` + `build/state/spec-dag-{date}.yaml` + `knowledge/intent-patterns/INT-INDEX.md`
- **設計**：rule-based v1（零 LLM 成本預設，守 G/H/I/J 慣例）。讀 high-level intent 文件 → 套 `intent-patterns` 骨架 + 啟發式切分 → 產出 acyclic spec-DAG（節點=候選 `BacklogCandidate`、邊=依賴）。節點數 clamp `SDD_INTENT_MAX_NODES`[4,128]；拓樸排序拒環。
- **介面收斂**：輸出直接餵 Phase I `value_planner.rank_candidates()`（不重造排序）。
- **驗收**：20 fixture（12 可分解意圖 + 8 模糊/成環意圖）；可分解者 DAG acyclic 且節點 ≤ 上限、覆蓋率 ≥ 80%；模糊/成環者正確回 `underspecified`、誤分解率 < 15%。

**ACT-082 — INTENT_DECOMPOSITION 狀態接線**
- **檔案**：`fsm_runtime.py`（`enter/exit_intent_decomposition`）、`transition_rules._HAPPY_PATH`、`formal/SDD_FSM.tla`、`SDD_FSM_ENGINE.md`
- **接線**：`AGENT_LOAD → {SPEC_DRAFTING, BACKLOG_PRIORITIZED, INTENT_DECOMPOSITION}`（加法式）；`INTENT_DECOMPOSITION → {BACKLOG_PRIORITIZED, HUMAN_PENDING}`。
- **有界**：分解迭代上限；underspecified→HUMAN_PENDING。**gatekeep 不引入新非 terminal cycle**（分解迭代硬上限為論證關鍵）。
- **驗收**：三源同步測試綠；TLC `SDD_FSM` reachable 39→40、`TypeOK/RetryBounded/RecoveryBounded/NotInBothSets/EventuallyTerminal` 全 PASS。

#### Pillar B — 規格辯證消歧（PK-2）

**ACT-083 — Spec Debate Engine**
- **檔案**：`tools/fsm_runtime/spec_debate.py`
- **設計**：對 `AmbiguityScorer` 落 near-threshold band 的 AC，啟兩條隔離詮釋 pass（pro/con 偏置），以 `pattern_matcher.is_same_pattern` 反向量化 divergence；輪數 clamp `SDD_SPEC_DEBATE_ROUNDS`[1,8]；強度凍結 `SPEC_DEBATE_PROFILE_VERSION`。
- **驗收**：24 fixture（12 雙詮釋互斥 AC + 12 真清晰 AC）；互斥者 divergence 偵出率 ≥ 80%、清晰者誤報率 < 15%。

**ACT-084 — SPEC_DEBATE 觀測態接線 + SCG-0 整合**
- **檔案**：`fsm_runtime.py`（`enter/exit_spec_debate`）、FSM 三源、`workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`（SCG-0 step 2a-ter）
- **接線**：`SCG_VALIDATION → SPEC_DEBATE`（observation）；`SPEC_DEBATE → {SCG_VALIDATION, HUMAN_PENDING}`。
- **驗收**：非阻塞、transient、有離開 transition；TLC reachable 40→41、`ObservationsTransient`（含 `SF_vars(T_SpecDebateConsensus)`）PASS。

#### Pillar C — 因果規格定位（PK-3）

**ACT-085 — Causal Spec Localizer**
- **檔案**：`tools/fsm_runtime/spec_localizer.py`
- **設計**：合 RTM + decision_trace + spec_anchor 為因果圖；輸入下游訊號 → BFS/權重回溯 → ranked suspect 節點 + 證據鏈。純離線、可重現、零外網。advisory。
- **驗收**：18 fixture（訊號→已知根因 AC）；top-1 定位準確率 ≥ 70%、top-3 ≥ 90%。

**ACT-086 — Localizer 整合（無新狀態）**
- **檔案**：`spec_patch_proposer.py`（Phase J，擴充吃 localizer 輸出）、`production_monitor.py`（PBS-DRIFT 附 suspect 節點）、`steersman_renderer.py`（人機介面顯示已定位根因 + 證據）
- **規則**：localizer 只「建議」，**絕不自動改 spec**；定位結果供 `SPEC_PATCH_PROPOSAL`（自擬 diff）與人類裁決。
- **驗收**：整合測試；localization report 正確附掛於 patch/digest/steersman 輸出。

#### 收官

**ACT-087 — Rule 9.23 治理落地**
- **檔案**：`governance/rules/R-9.23-intent-planning-dialectic-phase-k.yaml` + `governance/RULES_INDEX.md` + CLAUDE.md §9.23 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加。
- 子規則 9.23.1~9.23.6 見 §4。

**ACT-088 — Phase K 形式化重證 + 全綠驗收**
- **三源同步**：2 新狀態入 `SDD_FSM.tla`（`INTENT_DECOMPOSITION`∈HappyStates/gatekeep、`SPEC_DEBATE`∈ObservationStates）+ `_HAPPY_PATH` + MD。
- **TLC**：`SDD_FSM` reachable 39→41 = 100%；safety 4 invariant + `EventuallyTerminal` + `ObservationsTransient` 全 PASS。
- **Chaos**：100 輪（新增 `INTENT_DECOMPOSE_STORM`〔連續觸發分解逼近節點上限〕+ `DEBATE_FLAKY`〔辯證 divergence 抖動〕兩故障型）bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：目標 **≈ 575 + 約 80 = 655 passed**（K-1 32 / K-2 24 / K-3 18 + 整合 6）；**實際達 781 passed / 4 skipped（含後續 chaos 兩故障型、離線可達性測試與 QA 審計補強 18 項）**。

### 3.2 執行依賴圖

```
ACT-081（Intent Decomposer）──► ACT-082（INTENT_DECOMPOSITION + FSM/TLC）
ACT-083（Spec Debate Engine）──► ACT-084（SPEC_DEBATE + SCG-0 + FSM/TLC）
ACT-085（Spec Localizer）──────► ACT-086（整合 patch/prod/steersman）
                       三柱完成 ──► ACT-087（Rule 9.23）──► ACT-088（形式化重證 + 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L8 入口**，並標 L9/L10 horizon：

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L4.9 | 精準停機 | E M1 |
| L5 | Self-Driving（學習層 + 形式化停機） | A~G |
| L6 | Trustworthy Scaled（判官自審 + 增殖 + 雙形式化） | I |
| L7 入口 | Adversarial & Self-Improving（對抗判官 + 能力代謝 + 規格自癒） | J |
| **L8 入口** | **Intent-Driven（意圖分解 + 辯證消歧 + 因果接地）** | **K（本份）** |
| L9（horizon） | 主動現實實驗（counterfactual canary / shadow-traffic 自主驗證規格假設） | 未來 Phase L |
| L10（horizon） | 組合級自治 + 自我改進元迴圈形式化停機證明 | 未來 Phase M |

### 3.4 L9/L10 Horizon（本份不實作，僅定錨）
- **L9 — 主動現實實驗**：系統自主提出 canary/shadow 實驗以統計驗證規格假設，閉合「生產→規格」主動迴圈。**前置阻礙**：受 OPEN-10.6（本地唯讀 / 無 HTTP）約束，需先有使用者決策放寬沙箱外聯邊界。grep `experiment|counterfactual|shadow_traffic|portfolio` 現為零命中。
- **L10 — 組合級自治 + 元迴圈停機**：跨多軌意圖的組合優化，且對「框架自我改進迴圈」（學習層加規則 ↔ 鷹架 GC 退規則）本身證明不震盪（meta-halting）。需新 `META_FSM` 形式化層。

---

## 4. 防護規則新增（CLAUDE.md §9.23 Phase K）

> 待執行完成後正式寫入 CLAUDE.md §9.23（此處為草案，供 SCG-0 審視）。

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.23.1 分解有界 | ACT-081/082 | `INTENT_DECOMPOSITION` 節點/迭代硬上限 `SDD_INTENT_MAX_NODES`（clamp[4,128]）；spec-DAG 必 acyclic（拒環）；觸頂無法收斂→`HUMAN_PENDING` |
| 9.23.2 規劃不自我裁決 | ACT-081/082 | 自動產出候選只建議排序；最高 ROI 必經 `BACKLOG_PRIORITIZED` 人工 signoff（Rule 8）；planner 永不自選目標執行 |
| 9.23.3 辯證有界 + 不自我放水 | ACT-083/084 | `SPEC_DEBATE` 輪數硬上限 `SDD_SPEC_DEBATE_ROUNDS`（clamp[1,8]）；辯證強度凍結 `SPEC_DEBATE_PROFILE_VERSION`，變更須 bump |
| 9.23.4 辯證 advisory | ACT-083/084 | divergence 不自動阻塞/改寫 AC，僅導 `HUMAN_PENDING` 澄清；人工裁決才升級 |
| 9.23.5 因果定位 advisory-only | ACT-085/086 | `spec_localizer` 只建議 suspect 節點 + 證據，**絕不自動改 spec**；餵 `SPEC_PATCH_PROPOSAL`/steersman 供人裁決 |
| 9.23.6 三源 + TLC 同步 | ACT-082/084/088 | 2 新狀態同步 `_HAPPY_PATH ↔ SDD_FSM.tla ↔ SDD_FSM_ENGINE.md`，reachable 41/41；`INTENT_DECOMPOSITION` gatekeep 有界（不引入新非 terminal cycle）、`SPEC_DEBATE` observation 有離開 transition |

### ❌ Phase K 新增禁止行為（草案）
- planner 自動選最高 ROI 目標直接 `SPEC_DRAFTING`、繞過 `BACKLOG_PRIORITIZED` 人工 signoff（破 9.23.2 / Rule 8）
- `INTENT_DECOMPOSITION` 產出含環 spec-DAG，或超節點上限仍續分解（破 9.23.1）
- 調 `SPEC_DEBATE` 強度權重不 bump `SPEC_DEBATE_PROFILE_VERSION`（破 9.23.3，辯證自我放水）
- 讓 `SPEC_DEBATE` divergence 自動阻塞 SCG 或自動改寫 AC（破 9.23.4）
- `spec_localizer` 自動套用定位結果改 FRD/AC（破 9.23.5 / Rule 8）
- 把 `INTENT_DECOMPOSITION` 誤列為 observation，或把 `SPEC_DEBATE` 放入 Terminals（破 9.23.6 / Rule 9.18.4）
- 2 新狀態不同步 `SDD_FSM.tla`（破 9.23.6 / Rule 9.18.1）

---

## 5. Self-Verification Protocol（內部模擬：Spec 寫錯 → 測試永不過）

| 生命週期點 | L7（Phase J）現況行為 | Phase K 強化後行為 |
|------------|----------------------|--------------------|
| **凍結前·結構** | 人類須**手寫**全部規格；依賴矛盾（如折扣↔庫存成環）要到實作才浮現 | **`INTENT_DECOMPOSITION` 分解時即偵測成環** → underspecified → `HUMAN_PENDING`（根本進不了實作） |
| **凍結前·語義** | 「折扣可否疊加」歧義靠單視角 `AmbiguityScorer`，可能漏到下游 | **`SPEC_DEBATE` 兩詮釋分歧當場揭露** → `HUMAN_PENDING` 凍結前消歧 |
| **實作後** | `ADVERSARIAL_EVALUATION` 抓 spec_gap → `SPEC_AUDIT` → `SPEC_PATCH_PROPOSAL` | 同左（Phase J 既有），但多兩道上游攔截 → 多數案例根本到不了這裡 |
| **生產後** | drift 進來，**sa-analyst 手動**指認是哪條 AC | **`spec_localizer` 自動定位 + 證據** → 直接餵 `SPEC_PATCH_PROPOSAL` |
| **引導人類** | 自擬 AC diff（需人先指認補哪條） | 自動定位 + 自擬 diff，人類只 approve/reject（舵手更高） |
| **有界性** | TLC 已證必達 terminal | + 分解節點上限 + 辯證輪上限 + patch ≤2 次，TLC reachable 41/41 重證無新 cycle |
| **Token** | 早停不浪費 | **更省**（凍結前消歧免去整段實作-對抗-修補往返） |

✅ **模擬通過**：對「Spec 寫錯導致測試永不過」案例，Phase K 在**三個不同生命週期點**（凍結前辯證、實作後對抗、生產後定位）皆能優雅停機並引導人類，每道閘形式化有界，絕不無限重試耗 Token。人類在三處全部從「作者/偵探」升為「裁決者」——維持「設計環境掌舵者」高度，正是提示終極驗收標準。

---

## 6. 執行順序與里程碑

```
M-K1 宏觀規劃：ACT-081 → ACT-082（FSM+TLC）   ── 先做，補 GAN 缺的宏觀 Planner 半邊，價值最高
M-K2 規格辯證：ACT-083 → ACT-084（SCG-0+FSM+TLC）── 緊接，凍結前消歧，最省下游 token
M-K3 因果接地：ACT-085 → ACT-086              ── 中期，放大 Phase J 規格自癒的人機價值
M-K4 收官：ACT-087（Rule 9.23）→ ACT-088（三源 + TLC 重證 + chaos + pytest 全綠）
```

**每個 M-Kx 完成即跑該層 pytest + 必要時 TLC，絕不累積**（守 Rule 4 開發-編譯-測試循環）。

---

## 7. 待人工決策（OPEN-K）

> ✅ **SCG-0 凍結 2026-06-02**：OPEN-K.1 已實作固化；**OPEN-K.2~K.5 全採建議預設定案**（rule-based v1 / 參數 32·4 env 可調 / 單 Stage DAG / 不放寬沙箱）。Phase K 進入可執行狀態，分 M-K1~M-K4 里程碑逐段交付。

| ID | 議題 | 決議 |
|----|------|---------|
| OPEN-K.1 | 編號徵用 ACT-081~088 / Rule 9.23 是否確認（排擠 backup 分支 M3 Hook Health）？ | ✅ **RESOLVED 2026-06-02**：已建立 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml) 單一真實來源 + `tools/fsm_runtime/id_registry.py` + `test_id_registry.py` pytest 守門。Phase K 正式持有 ACT-081~088/R-9.23；M3 Hook Health **不再預留號**，復活時取 `next_free`（現 ACT-089/R-9.24）。此後撞號由 CI 自動攔截，不再靠人工記憶 |
| OPEN-K.2 | Intent Decomposer v1 限 rule-based（零成本）抑或允許 LLM 分解？ | rule-based v1（守 G/H/I/J 慣例）；LLM 留 v2 並更新成本 gate（比照 OPEN-J.1） |
| OPEN-K.3 | `SDD_INTENT_MAX_NODES` 預設 32 / `SDD_SPEC_DEBATE_ROUNDS` 預設 4 是否合適？ | 預設 32 / 4，env 可調（執行時校準） |
| OPEN-K.4 | `spec-DAG` 是否允許跨 Stage 依賴（影響 BACKLOG 排程）抑或限單 Stage 內？ | 預設限單 Stage 內依賴；跨 Stage 只「標註」不自動排程 |
| OPEN-K.5 | L9 主動現實實驗是否啟動 OPEN-10.6 沙箱外聯放寬評估？ | 暫不；維持本地唯讀，L9 列 horizon，待專案有真實生產整合需求再評 |

---

**藍圖等級目標**：L7 → **L8 入口 — Intent-Driven Generative Planning & Dialectic-Grounded SDD**（意圖分解 + 辯證消歧 + 因果接地）
**前置 SCG**：✅ SCG-0（需求凍結）PASSED 2026-06-02 — 範疇完整、OPEN-K 定案、無矛盾，准予逐 ACT 執行。
**形式化承諾**：2 新狀態三源同步、TLC `SDD_FSM` reachable 39→41=100%、`EventuallyTerminal` + `ObservationsTransient` 不回歸、chaos bounded_ratio=1.0。
**TLC 本地實證（2026-06-02）**：`tlc_runner.py` 跑 TLC = **807 distinct states / No error found**（4 safety invariant + 2 liveness 全 PASS）；並以 `test_tla_python_sync` 的**離線可達性 BFS 不變量**常駐守門 reachable=N/N（零 Java 依賴）——「reachable 僅 CI 推算」caveat 已徹底消除。
