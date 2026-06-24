# SDD_improving_Automation_12 — Phase L 藍圖

**主題**：自我改進元迴圈的形式化停機 + 離線反事實實驗 + 主動規格脆弱性預測（Meta-Halting Formalization & Offline Counterfactual Reality-Grounding）
**目標等級**：L8 入口 → **L9 入口（離線切片）+ L10 元停機形式化奠基**（系統不只在單軌內有界停機，連「學習層加規則 ↔ 鷹架 GC 退規則」這對跨 session 自我改進元迴圈本身都被形式化證明不震盪；並以自身歷史軌跡作為「現實」做離線反事實驗證規格假設；舵手高度從「審單一意圖的分解/詮釋/補丁」升至「審整個框架自我演化的收斂界限」）
**建立日期**：2026-06-03
**前置基線**：Phase K 完整（ACT-081~088，L8 入口 Intent-Driven Generative Planning & Dialectic-Grounded SDD，pytest 781 綠、TLC `SDD_FSM` reachable 41/41、`FLEET_FSM` 無死鎖 + AllEventuallyDone、chaos bounded 1.0）
**狀態**：✅ **EXECUTED 2026-06-03（L8 入口 → L9 入口離線切片 + L10 元停機奠基達成）** — 人工 signoff 採 OPEN-L 建議預設值後，M-L1（ACT-089/090）、M-L2（ACT-091/092）、M-L3（ACT-093/094）、M-L4（ACT-095/096 收官：R-9.24 active + ID_REGISTRY 翻牌 next_free act=97/rule=9.25 + CLAUDE §9.24 + INIT 禁止事項）全部完成。驗收：**pytest 815 passed / 5 skipped（含 +55 Phase L：test_meta_halt 21 + test_phase_l 33 + test_id_registry +1；歷史基線 760）+ chaos 套件 21 passed；META_FSM TLC No error（13 distinct，4 safety + EventuallyMetaStable liveness）；單軌 SDD_FSM TLC No error（105 distinct，42 態含 EXPERIMENT_REPLAY，EventuallyTerminal/ObservationsTransient 不回歸）；chaos 100 輪 bounded_ratio=1.0 / avg 1604 tokens（含 META_CHURN_STORM / REPLAY_FLAKY 兩 Phase-L 故障型）；離線可達性 BFS reachable=N/N（META_FSM 5/5 + 單軌 42/42）**。

> 🔴 **原 DRAFT 紀錄（保留）**：本份為 Karpathy 式前沿評估的規劃產出，OPEN-L 待人工裁決後方可逐 ACT 執行（守 Rule 8 / Rule 9.23.2 planner 不自我裁決）。已於 2026-06-03 獲使用者「直接進入執行」signoff，採 OPEN-L 全建議預設值（含 OPEN-L.5 暫不放寬沙箱、維持 L9 離線切片）。
>
> 📌 **字面收口稽核（2026-06-03，回應「有無遺漏」）**：首輪執行有 4 個邊緣項以替代 locus 處理或暫緩，已全數補齊至藍圖字面：①ACT-092 `spec_patch_proposer.propose(replay_evidence=)` 附掛重放證據（指定 locus）；②ACT-094 `intent_decomposer.annotate_fragile()`（指定 locus）；③§2.1 `spec_fragility_scorer.write_report()` 落盤 `build/reports/fragility/FRAGILITY-{date}.md`；④§2.1 `counterfactual_replay.crystallize_patterns()` + `knowledge/experiment-patterns/EXP-INDEX.md`（≥3 同型→proposed，禁自動 verified）。各附回歸測試（test_phase_l 28→33）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 本份為 L8→L9/L10 續推。

> 🔴 **編號徵用告示（承 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml) `next_free`）**：
> 本藍圖徵用 **ACT-089~096 與 Rule 9.24**（取自登記簿前緣 act=89 / rule=9.24，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> 執行收官（ACT-095）時須由 `id_registry` 翻牌 + `test_id_registry.py` pytest 守門固化，撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase L？——對既有設計的誠實剖析（含 `<thinking>`）

<thinking>
這份提示要求「驗證圖靈完備自動化閉環、進化 Level 10 自治」，並附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。和 Phase K 一樣，正確的第一步是**對賬而非設計**——這套系統已走過 Phase A~K、是自稱 L8 入口的成熟框架，盲目套提示的前沿清單只會重造輪子。

【一、提示前沿清單 × 既有落地對賬（再次確認，且補上 Phase K 新增）】
- 生成與評估分離（GAN 啟發）→ ✅ Phase H `sdd-evaluator`（獨立 context/worktree）+ Phase J `adversarial_synthesizer`（主動攻擊半邊）+ Phase K `spec_debate`（規格詮釋端對抗）。三個層級皆已分離生成/評估。
- 主觀標準量化 → ✅ Phase G M3 `AmbiguityScorer`（6 維、`SCORER_VERSION` 凍結）+ Phase H `output_quality_scorer`（OQS）+ Phase J `ADVERSARIAL_PROFILE_VERSION`。
- 評估器實體操作（Playwright/沙箱）→ ✅ Phase H `sandbox_runner` + Phase I `evaluate_hermetic`（`--network none`/`--cap-drop ALL`）+ `R-SELF-STRIDE`（評估迴圈自身安全）。
- 動態演進框架、移除鷹架 → ✅ Phase H `SCAFFOLD_GC` + Phase J 能力感知 graduation（`scaffold_gc.py` 有 graduation/set_maturity/retire）。
- 單一真實來源、漸進式揭露 → ✅ `governance/RULES_INDEX.md` + `rule_loader.load_for_state()` + `ID_REGISTRY.yaml`。
- 運行時可觀測性（LogQL/PromQL）→ ✅ Phase H `observability_query`（本地唯讀）。
- 不變量 + 垃圾回收 → ✅ Rule 9 全鏈 + `spec_monitor`（.tla 4 invariant 合成 runtime assertion）+ `SCAFFOLD_GC` + **一條完整的自我演化動態工作流 `SDD_SELF_EVOLUTION.md`（FSE 狀態機 + `arch_fitness` 15 道 fitness function，已抵 score=0 不動點）**。
- Planner→G/E 合約談判（宏觀+微觀）→ ✅ 微觀 `TEST_CONTRACT_NEGOTIATED`（Phase H）+ 宏觀 `INTENT_DECOMPOSITION`（Phase K）。兩層皆已落地。
- 上下文重置與結構化交接 → ✅ `stage-compaction` + Context Governor + `CONTEXT-SNAPSHOT` 恢復鏈。
- 停機問題 + 人類掌舵者 → ✅ 單軌 FSM 有界停機 + TLC 形式化（`SDD_FSM` reachable 41/41）+ **艦隊並行 `FLEET_FSM` 無死鎖 + AllEventuallyDone（Phase I M5）** + `steersman_renderer` + Phase J `spec_patch_proposer` + Phase K `spec_localizer`（自動定位該補哪條 AC）。

結論：**提示前沿清單已 100% 對應到落地元件，且使用者本身要的「具自我修正能力的動態工作流」也早已存在（`SDD_SELF_EVOLUTION.md`）。** 提示的 self-verification 案例在 L8 現況的**單軌內**即可優雅停機（凍結前辯證 + 實作後對抗 + 生產後定位三道攔截）。所以 Phase L 不能重述——必須挖出 L8 仍真實存在、grep 可證零實作的**新**結構性缺口。

【二、用提示三個指定漏洞視角，逐一往 L8 深處挖】

(A) 狀態轉換——把停機論證從「單軌」推到「元迴圈」。
單軌 `SDD_FSM.tla` 已被 TLC 窮舉證明必達 terminal（`EventuallyTerminal`），艦隊層 `FLEET_FSM.tla` 也證了 N 軌並行 `AllEventuallyDone`。但框架現在**有兩條會跨 session 修改「常駐治理規則集」本身的相反迴圈**：
  - **學習層（Phase E M4）**：ESCALATION → FPL → `slv_generator` 產 SLV proposed → 人工 review → verified。這條**單調增加**規則。
  - **鷹架 GC（Phase H M5）+ 能力代謝（Phase J）**：`scaffold_gc.set_maturity()` 把長期 0-fire 的規則退役（deprecated）。這條**移除**規則。
  - 外加 **FSE 自我演化迴圈**：`arch_fitness` 持續新增 fitness function、重構結構。
這三條迴圈的**共同操作對象是 always-loaded 的治理規則/鷹架集合**，而它們的**聯合收斂性從未被形式化證明**。理論上可以震盪：學到 `SLV-N` → 一段時間 0-fire → GC 退役 → 同類歧義再次 escalate → 重新學 `SLV-N'`（語意同型）→ 再 0-fire → 再退…… 這是經典的 add↔remove 抖動，會讓「框架自我改進」這件事本身**不停機**——正是提示「停機問題」視角推到極致的型態，也是 Phase K §3.4 親自點名、列為 L10 horizon 的「自我改進元迴圈形式化停機證明（meta-halting）」。`SDD_SELF_EVOLUTION.md` 自陳「協調層刻意不併入單軌 `SDD_FSM.tla`」——這個刻意的留白，正是目前**唯一一處沒有形式化停機保證的閉環**。grep `meta_halt|meta_fsm|rule_churn|meta_loop` 在 `tools/` **零命中**。→ **PL-1**（最關鍵；這是 L10 的奠基石，且純離線、純形式化，不受 OPEN-10.6 約束）。

(B) 生成-評估分離 / 對抗——已套到 code（J）、套到 spec 詮釋（K），但「規格假設 vs 現實」這層仍是**開迴圈**。
L9 的定義是「系統主動提出實驗、用現實統計驗證規格假設」。Phase J 的 `spec_patch_proposer` 能**自擬** AC diff、Phase K 的 `spec_localizer` 能**自動定位**該補哪條，但「**這個補丁如果早點存在，到底能不能擋住已發生的失敗？**」目前無人回答——補丁是「相信它有效」地送進 `HUMAN_PENDING`，沒有對「現實」的對照評估。真正的 L9 需要 shadow-traffic/canary，但受 OPEN-10.6（本地唯讀 / 無 HTTP）約束，活體實驗暫不可行。**然而框架手上握有大量現成的「現實代理」**：`decision_trace`（決策證據鏈）、`knowledge/failure-patterns/FPL-*`（歷史失敗）、`chaos_runner` 場景、`PBS-DRIFT` 報告。把「補丁（生成）」對「歷史失敗軌跡（現實代理）」做**離線反事實重放（counterfactual replay）**，估計「這個補丁能擋住過去 N 筆 escalation 中的幾筆」——這就是生成-評估分離推到**規格假設層**的離線切片，完全不違反本地唯讀。grep `counterfactual|shadow_traffic|experiment_replay|canary` **零命中**。→ **PL-2**（L9 離線切片）。

(C) 絕對運行時可觀測性——`spec_localizer`（K）是**反應式**定位，缺**主動式**風險預測。
Phase K 的因果定位是「訊號進來 → 回溯該補哪條」。但提示的 OpenAI「環境防護」精神要的是**在訊號發生前就豎好邊界**。系統有三張現成的圖（RTM 的 AC↔TC↔FRD 追溯、`decision_trace`、`spec_anchor` 跨媒介錨點）卻只在事後當因果圖用，從不在事前算「哪些 spec 節點最脆弱（高 blast-radius × 低測試覆蓋 × 高歷史漂移頻率）= 最可能成為下一個 escalation 源」。grep `fragility|brittle|spec_risk` **零命中**。一個 `spec_fragility_scorer` 能把 `spec_localizer` 的反應式因果圖升級為**主動式風險熱圖**，餵 `steersman_renderer` 讓舵手在凍結前就看到「這條 AC 是定時炸彈」，也回饋 `intent_decomposer` 在分解時就標記脆弱依賴。→ **PL-3**（主動規格脆弱性預測，advisory，無新單軌狀態）。

【三、上下文衰減（Context Degradation）視角覆查】
- PL-1 的 `META_FSM` 是**形式化規格 + 跨 session 帳本**，不常駐主線 context：churn 事件落 `build/state/meta-loop-ledger.yaml`（`file_lock` 保護），`.tla` 由 CI/本地 `tlc_runner` 跑，主線只在 ESCALATION/收官時讀摘要。仿 `FLEET_FSM` 既有作法，零新增常駐 prompt。
- PL-2 的反事實重放在**隔離 context** 跑（仿 `sdd-evaluator` worktree 哲學），只把「擋住 N/M 筆」結論 + 證據回主線。重放語料（FPL/chaos/trace）皆落盤按需 lazy-load，不灌入 context。
- PL-3 脆弱性熱圖落 `build/reports/fragility/*.md`，`steersman_renderer` 只渲染 top-K。
→ 三者皆守漸進式揭露，不引入新的脈絡焦慮。

【四、停機問題（Halting）視角覆查——這是不可退讓的紅線，且本份正是衝著它來】
這次的反諷是：本份的核心交付（PL-1）**就是把停機保證本身往上推一層**。所以每個新機制的有界性要加倍嚴謹：
- PL-1 `META_FSM` 必證一條核心 meta-invariant **`ChurnBounded`**：任一規則的「加→退→再加」循環次數有硬上限，且**再採納必須挾帶 capability-delta 證據**（不能無證據地把剛退役的同型規則重新學回來）——這就破除了 add↔remove 抖動。配 `EventuallyMetaStable`（liveness：元迴圈最終抵達不再 churn 的不動點，仿 `SDD_SELF_EVOLUTION` 已論證的「fitness 嚴格遞減→well-ordering→必收斂」與 `FLEET_FSM` 的 fairness liveness）。
- PL-2 `EXPERIMENT_REPLAY` 為**有界 observation**（重放筆數 clamp、純離線、transient、必有離開 transition），advisory **絕不自動 approve 補丁**——只把「歷史命中率」當證據附在 `SPEC_PATCH_PROPOSAL` 上，人類仍是最終 approve/reject 者。
- PL-3 為純 advisory **不新增單軌狀態**（比照 `spec_localizer` / `AmbiguityScorer`），脆弱性分數凍結於 `FRAGILITY_PROFILE_VERSION`，調權重須 bump（守「評分器不可自我放水」）。
- 人類掌舵者高度**不降反升**：從 Phase K 的「審單一意圖的分解/詮釋/補丁」升至「審整個框架自我演化的收斂界限與離線實驗結論」——這恰是提示「確保人類維持設計環境掌舵者高度、而非降級為編碼員」的最高體現。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性）：把「框架自我演化的收斂界限」「離線實驗結論」「規格脆弱性熱圖」三者全部落地為 **Markdown/YAML 可推理產物**（meta-loop ledger、replay report、fragility heatmap），不藏在 prompt 裡；`META_FSM` 形式化規格本身就是「AI 可直接推理的環境邊界宣告」。
- Anthropic（對抗 / 動態演進）：把「生成-評估分離」從 code（J）、spec 詮釋（K）再往上游推到**規格假設層**（離線反事實 = 拿歷史現實當判官）；並把「動態演進框架、大膽移除鷹架」這件事**本身**納入形式化停機證明——你敢自動退役鷹架，就得先證明退役迴圈不會抖動。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H/I/J/K 落地元件**（對賬見上 thinking 一節），連使用者要的「具自我修正能力的動態工作流」本身都已存在（[`SDD_SELF_EVOLUTION.md`](../../../workflow/sdd-self-evolution/SDD_SELF_EVOLUTION.md) 的 FSE 狀態機 + `arch_fitness`）。Phase L 的價值在用提示三漏洞視角挖出 L8 仍真實存在、grep 證零實作的 **3 個結構性缺口**：

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PL-1** | **停機證明只到單軌/艦隊，沒到元迴圈**——`SDD_FSM`（單軌）、`FLEET_FSM`（N 軌並行）皆已形式化必達 terminal，但「學習層**單調加規則** ↔ 鷹架 GC **退規則** ↔ FSE **加 fitness**」這對跨 session **修改常駐治理規則集**的相反迴圈，其聯合收斂性**從未形式化**。理論上可 add↔remove 抖動（學 SLV→0-fire 退役→同型歧義再 escalate→重學），即「框架自我改進」本身不停機。`SDD_SELF_EVOLUTION.md` 自陳「協調層刻意不併入單軌 .tla」=**唯一無形式化停機保證的閉環**。 | `meta_halt\|meta_fsm\|rule_churn\|meta_loop` **零命中** |
| **PL-2** | **規格假設 vs 現實仍是開迴圈**——`spec_patch_proposer`（J）能自擬 diff、`spec_localizer`（K）能自動定位，但「此補丁若早存在，能否擋住已發生的失敗」無人評估（相信即送 `HUMAN_PENDING`）。L9 活體實驗受 OPEN-10.6 阻擋，但 `decision_trace`/`FPL`/`chaos`/`PBS-DRIFT` 是現成「現實代理」，可做**離線反事實重放**（補丁=生成、歷史失敗=現實判官）。 | `counterfactual\|shadow_traffic\|experiment_replay\|canary` **零命中** |
| **PL-3** | **因果定位只反應、不主動**——`spec_localizer`（K）是訊號進來才回溯該補哪條；缺「凍結前就算哪些 spec 最脆弱（blast-radius × 測試覆蓋缺口 × 歷史漂移頻率）= 最可能成為下一個 escalation 源」的**主動風險預測**。RTM + decision_trace + spec_anchor 三張現成圖未被當事前風險圖用。 | `fragility\|brittle\|spec_risk` **零命中** |

**三缺口的共同主軸**：L8 的人類站在「審單一意圖的分解/詮釋/補丁」的高度，而框架的**自我演化迴圈本身仍是憑紀律維持的開迴圈、規格風險只能事後救火、補丁只能憑信任送審**。Phase L 把人類抬到「審整個框架自我演化的**收斂界限**、審離線實驗對現實的**命中證據**、在炸彈引爆前就看到**脆弱性熱圖**」——這正是 L9 離線切片 + L10 元停機奠基的定義，也精準補上提示在「停機問題」與「動態演進框架」兩個視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase L 增量）

Phase L 對狀態機的改動刻意**極小化單軌表面積**：單軌 `SDD_FSM` 只新增 **1 個 observation 狀態**（PL-2），PL-3 為 advisory **不新增狀態**，而 PL-1 比照 `FLEET_FSM` / `SDD_SELF_EVOLUTION` 的「協調層獨立命名空間」原則，**另闢 `META_FSM` 形式化層**，**不污染單軌 `SDD_FSM.tla`** 的既有 41/41 證明。

### 1.1 新增狀態總覽

| 狀態 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `EXPERIMENT_REPLAY` | 單軌 `SDD_FSM` | observation（advisory, transient, 有界） | `SPEC_PATCH_PROPOSAL`（補丁草擬後、送 `HUMAN_PENDING` 前） | done→回 `SPEC_PATCH_PROPOSAL`（附命中證據）/ inconclusive→`HUMAN_PENDING` | 否 |
| `META_FSM`（`MFSM-*` 狀態族） | **獨立 `META_FSM.tla`**（不入單軌） | meta 協調層 | 跨 session：學習層 commit / GC 退役 / FSE apply 事件 | 抵 `MFSM_STABLE`（不動點）或 `MFSM_ESCALATION`（churn 觸頂） | — |

> **選位說明**：
> - `EXPERIMENT_REPLAY` 插在 Phase J `SPEC_PATCH_PROPOSAL`（自擬 diff）與既有 `HUMAN_PENDING`（人工 approve）**之間**——補丁先過離線重放取得「歷史命中率」證據，再連同證據送人工。既有 `SPEC_PATCH_PROPOSAL → HUMAN_PENDING` 完全向後相容（加法式插一個非阻塞觀測態）。
> - `META_FSM` **不是單軌狀態**。它是把 `SDD_SELF_EVOLUTION.md` 自陳的 meta-loop（學習/GC/FSE）顯式形式化的獨立層，沿用 `FLEET_FSM` 既有「另開 .tla + 自有 invariant/liveness + 自有 reachability」的成功模式，**不動 Rule 9.18.1 的單軌三源一致性**。

### 1.2 META_FSM 元迴圈有界停機契約（最關鍵；L10 奠基石）

```
（跨 session 元迴圈，狀態變數 = {rule_set, scaffold_roi[], capability_level, churn_log}）
MFSM_OBSERVE（讀 meta-loop-ledger：本期有無 學習層加規則 / GC 退規則 / FSE 加 fitness）
  ├─ 學習層 commit verified 規則 → MFSM_GROW（rule_set++，記 churn_log{add, rule_id, capability_at})
  ├─ GC set_maturity=deprecated → MFSM_SHRINK（記 churn_log{retire, rule_id})
  ├─ 無變動 → MFSM_STABLE（不動點：本期零 churn）
  └─ 偵測「同型規則 add→retire→re-add」且無 capability-delta → MFSM_ESCALATION（churn 觸頂，人工裁決）
```

- **核心 meta-invariant `ChurnBounded`**：任一規則語意指紋（`pattern_matcher` 正規化）的「加→退→再加」循環次數 ≤ `SDD_META_CHURN_MAX`（clamp[1,5]，預設 2）。超限即 `MFSM_ESCALATION`，**絕不無限抖動**。
- **`GraduationRatchet`（棘輪不變量）**：被 GC 退役過的規則指紋，**再採納（re-adopt）必須挾帶 `capability_level` 嚴格變化證據**（capability-delta）——破除「學了又退、退了又學」的同型震盪。比照 Phase J「能力感知 graduation」精神，把它從機制升級為**形式化約束**。
- **`EventuallyMetaStable`（liveness）**：在公平性假設下，元迴圈最終抵達 `MFSM_STABLE`（不再 churn）。論證同構於 `SDD_SELF_EVOLUTION.md §3` 已證的「`arch_fitness` 加權缺陷分數嚴格遞減 → 良序原理 → 必收斂」與 `FLEET_FSM` 的 `AllEventuallyDone` fairness liveness。
- **可觀測落盤**：churn 事件寫 `build/state/meta-loop-ledger.yaml`（`file_lock` 保護），跨 session 審計鏈；`META_FSM.tla` + `META_FSM.cfg` 由 `tlc_runner` 跑，並以離線可達性 BFS 不變量常駐守門（零 Java 依賴，比照 ACT-088 既有作法）。

### 1.3 EXPERIMENT_REPLAY 離線反事實契約

```
SPEC_PATCH_PROPOSAL（Phase J 自擬 AC diff，已挾 spec_localizer 定位）
  → EXPERIMENT_REPLAY（replay_budget = SDD_REPLAY_MAX_CASES，clamp[5,200]，預設 50）
     對「歷史現實代理」逐筆反事實重放：FPL-* 失敗、chaos 場景、PBS-DRIFT、decision_trace escalation
     ├─ done：算出「此補丁可擋住 X/Y 筆歷史失敗」+ 反例（擋不住的） → 回 SPEC_PATCH_PROPOSAL（附命中證據）
     └─ inconclusive：歷史語料不足 / 重放觸頂無法判定 → HUMAN_PENDING（不臆測，守 Rule 8）
```

- **生成-評估分離**：補丁是「生成」，歷史失敗軌跡是「現實判官」，兩者在**隔離 context** 重放（仿 `sdd-evaluator`），oracle 不被補丁作者預先知悉。
- **有界 + advisory**：重放筆數硬上限 clamp；transient observation、必有離開 transition；**命中率只是證據，絕不自動 approve 補丁**——人類仍是 `HUMAN_PENDING` 的最終裁決者（守 Rule 8 / 對齊 Phase K advisory 哲學）。
- **純離線、守 OPEN-10.6**：所有重放語料皆本地既有產物，無 HTTP、無外網、可重現。

### 1.4 PL-3 主動規格脆弱性預測（advisory，無新狀態）

`spec_fragility_scorer` 合 RTM（AC↔TC↔FRD blast-radius）+ 測試覆蓋缺口 + 歷史漂移頻率（`PBS-DRIFT`/`DRIFT_OBSERVATION` 紀錄）+ `decision_trace` escalation 命中，對每個 spec 節點算**脆弱性分數**（凍結於 `FRAGILITY_PROFILE_VERSION`）。輸出 ranked 熱圖**餵入既有狀態/介面**：`steersman_renderer`（凍結前舵手即見炸彈）、`intent_decomposer`（分解時標記脆弱依賴）。**只建議不自動改 spec**。

### 1.5 典型軌跡（含 Phase L 改善後的 self-verification 案例）

```
（跨 session 元層）MFSM_OBSERVE：上期學習層加了 SLV-012、GC 退了 SLV-007
  → ChurnBounded 檢查：SLV-007 指紋此前未曾 add→retire→re-add → 合法 → MFSM_SHRINK → 趨穩
  →（若偵測 SLV-007 被退役後又無 capability-delta 地重新學回）→ MFSM_ESCALATION（人工：是真盲區還是抖動？）

（單軌）… SPEC_FROZEN 前 spec_fragility_scorer 報「折扣 AC-014 脆弱性 top-1（高 blast × 零 mutation 覆蓋 × 3 次歷史漂移）」
  → steersman 渲染熱圖，舵手凍結前即決定加強該 AC 的測試合約
  → …（仍漏網到生產）PRODUCTION_SIGNAL：drift 進來
  → spec_localizer（K）自動定位 = AC-014 → SPEC_PATCH_PROPOSAL（J 自擬 diff）
  → [L-2] EXPERIMENT_REPLAY：對 FPL/chaos/trace 反事實重放 → 「此補丁可擋住過去 4/5 筆同源 escalation，1 筆擋不住（反例附上）」
  → HUMAN_PENDING（人類看著「命中 4/5 + 1 反例」approve/reject，而非憑信任）
  → [M5] TLC 已預證單軌此路徑必達 terminal；[L-1] META_FSM 已預證採納此補丁衍生的規則變動不會引發 churn 抖動
```

**對比 L8 現況**：L8（a）規格脆弱性只能事後由 drift 暴露；（b）補丁憑「相信有效」送審，人類缺現實對照；（c）框架自我演化（學/退/演化）靠紀律不抖動、無數學保證。Phase L 讓系統**事前預測脆弱性、用歷史現實驗證補丁、形式化證明自我演化收斂**——人類三處全部從「救火/信任/憑紀律」升為「審風險/審證據/審界限」，精準對應提示「人類維持設計環境掌舵者高度」於**最高（元）層**。

---

## 2. 環境建構與記憶體管理策略（Phase L 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/meta-loop-ledger.yaml`（新增，`file_lock` 保護）：跨 session 的規則 churn 事件帳本（add/retire/re-adopt + capability_at + 指紋）。**落盤不常駐**，`META_FSM` 與收官審計按需 lazy 讀。
- `tools/fsm_runtime/formal/META_FSM.tla` + `META_FSM.cfg`（新增）：元迴圈形式化規格，比照 `FLEET_FSM.tla` 自有 invariant/liveness/symmetry，**獨立命名空間不入單軌**。
- `build/reports/replay/REPLAY-{date}.md`（新增）：反事實重放報告（命中 X/Y + 反例清單），附掛於 `SPEC_PATCH_PROPOSAL`。
- `build/reports/fragility/FRAGILITY-{date}.md`（新增）：脆弱性熱圖（ranked top-K + 證據），餵 `steersman_renderer`。
- `knowledge/experiment-patterns/`（新增，對稱於 `failure-patterns`/`intent-patterns`/`adversarial-patterns`）：存 `EXP-*.yaml` 常見「補丁→歷史命中」模式，≥3 次同型 → 結晶 proposed 草案，**禁自動 verified**（比照 SPL/ADV/INT 治理）。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 新增形式化 meta-invariant（`META_FSM.tla`）：`ChurnBounded`、`GraduationRatchet`、`EventuallyMetaStable`、`TypeOK`、`MFSM_ESCALATION ∉` 不動點集合。
- 新增單軌 runtime invariant（`spec_monitor` 合成）：`EXPERIMENT_REPLAY ∈ ObservationStates 且有離開 transition`、`EXPERIMENT_REPLAY ∉ Terminals`。
- 鷹架代謝閉環：`meta_halt_monitor` / `counterfactual_replay` / `spec_fragility_scorer` 三鷹架本身納入 `scaffold_roi` 帳本——**而這正是 PL-1 的妙處**：新鷹架的退役也會被它自己證明的 `META_FSM` 納管，元迴圈自洽地涵蓋自己（守 Rule 9.20.5 / 9.22.3，退役須 `set_maturity(reviewed_by=)` 人工 gate）。

### 2.3 Prompt / 上下文與防衰減
- Phase L **不新增任何常駐 eager prompt**。反事實重放的詮釋、脆弱性評分皆由對應 runtime agent 在**隔離 context** 持有，結論才回主線。
- 補丁進 `EXPERIMENT_REPLAY` 前主線只留 patch 摘要 + 定位結果；重放語料（FPL/chaos/trace）全落盤 lazy-load，不灌 context。
- 所有新產物（meta-loop ledger / replay report / fragility heatmap / `META_FSM.tla`）皆 Markdown/YAML/TLA+ 純文字，無二進位、無外網依賴（守 OPEN-10.6 + 智慧體可讀性）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-089~096）

#### Pillar A — 自我改進元迴圈形式化停機（PL-1；L10 奠基石）

**ACT-089 — Meta-Loop Ledger + churn 帳本**
- **檔案**：`tools/fsm_runtime/meta_halt/meta_ledger.py` + `build/state/meta-loop-ledger.yaml`
- **設計**：純離線。記錄每次 規則 add（學習層 verified）/ retire（GC deprecated）/ FSE fitness 增刪事件，附 `rule_fingerprint`（`pattern_matcher` 正規化）+ `capability_level_at` + 時戳。提供 `compute_churn(fingerprint)` 回該指紋的 add↔retire 循環次數。
- **驗收**：20 fixture（含 3 條人工合成抖動序列 + 17 正常單調序列）；抖動序列 `compute_churn ≥ SDD_META_CHURN_MAX` 偵出率 100%、正常序列零誤判。

**ACT-090 — META_FSM 形式化 + meta_halt_monitor runtime 守門**
- **檔案**：`tools/fsm_runtime/formal/META_FSM.tla` + `META_FSM.cfg` + `tools/fsm_runtime/meta_halt/meta_halt_monitor.py` + `tlc_runner.py` 擴充 + 離線可達性 BFS 測試
- **設計**：仿 `FLEET_FSM.tla`。狀態變數 `{rule_set, churn_log, capability_level}`，宣告 `MFSM_OBSERVE/GROW/SHRINK/STABLE/ESCALATION`。證 5 safety（`TypeOK`/`ChurnBounded`/`GraduationRatchet`/`ReadoptGated`/`StableIsFixpoint`，後二者皆保留 → 較原規劃更強）+ 1 liveness（`EventuallyMetaStable`，需 `SF_vars`）。`meta_halt_monitor` 為 runtime assertion：每次學習層 `exit_learning_commit("approved")` 或 GC `set_maturity()` 前呼叫，違反 `ChurnBounded` 即拒絕並導 `MFSM_ESCALATION`。
- **驗收**：`META_FSM` 經 `tlc_runner` = No error（5 invariant 全 PASS）+ 離線 BFS reachable=N/N；`meta_halt_monitor` 攔截 ACT-089 的 3 條抖動序列；**單軌 `SDD_FSM` reachable 維持 41/41 不回歸**（META_FSM 不污染單軌）。
> 📌 **稽核收口落地（2026-06-03，第二輪）**：①**StableIsFixpoint 已補真**——`META_FSM.tla` 新增 `StableIsFixpoint` invariant（`MFSM_STABLE` 為吸收不動點、`MFSM_ESCALATION ∉ StableFixpoints`），`META_FSM.cfg` INVARIANT 區塊加入（保留既有 `ReadoptGated` 為額外保證 → 實證 **5 safety**），TLC No error / 13 distinct 不回歸；R-9.24 yaml 與本藍圖字面同步。②**meta_halt_monitor 已接線生產路徑**——`fsm_runtime.exit_learning_commit("approved")` 採納 verified 規則前經 `record_rule_add`（語意指紋排除 id、capability 取自 rule_doc），違反 ChurnBounded/GraduationRatchet 改導 `ESCALATION`（category=structural，例外不外炸破 FSM）；`rule_loader.set_maturity` 退役方向（active/audit-only→audit-only/deprecated）經 `record_rule_retire` 落帳（只記帳不 raise）。預設 ledger 路徑新增 `SDD_META_LEDGER_PATH` 覆寫鉤子 + tests/conftest.py session 隔離，杜絕生產接線污染 repo。接線守門測試見 `test_meta_halt.py`（approved 落 add / churn 抖動導 ESCALATION / 退役落 retire）。③chaos 補 Phase L 對稱專屬測試（`test_phase_l_faults_are_declared_types` + `_meta_churn_storm_is_bounded`/`_replay_flaky_is_bounded` 直測）。

#### Pillar B — 離線反事實實驗（PL-2；L9 離線切片）

**ACT-091 — Counterfactual Replay Engine**
- **檔案**：`tools/fsm_runtime/counterfactual_replay.py`
- **設計**：rule-based v1（零 LLM 成本預設，守 G~K 慣例）。輸入 `SPEC_PATCH_PROPOSAL` 的 AC diff → 對 `knowledge/failure-patterns/FPL-*`、`chaos_runner` 場景、`PBS-DRIFT`、`decision_trace` escalation 逐筆反事實判定「此 diff 是否會改變該歷史失敗的結局」→ 輸出 `prevented X / total Y` + 反例清單。重放筆數 clamp `SDD_REPLAY_MAX_CASES`[5,200]。
- **驗收**：24 fixture（12「補丁確能擋」+ 12「補丁擋不住/無關」）；能擋者命中率 ≥ 80%、無關者誤報率 < 15%。

**ACT-092 — EXPERIMENT_REPLAY 觀測態接線 + SPEC_PATCH_PROPOSAL 整合**
- **檔案**：`fsm_runtime.py`（`enter/exit_experiment_replay`）、FSM 三源（`_HAPPY_PATH` ↔ `SDD_FSM.tla` ↔ `SDD_FSM_ENGINE.md`）、`spec_patch_proposer.py`（patch 附掛 replay 證據）
- **接線**：`SPEC_PATCH_PROPOSAL → EXPERIMENT_REPLAY`（observation）；`EXPERIMENT_REPLAY → {SPEC_PATCH_PROPOSAL, HUMAN_PENDING}`。
- **驗收**：非阻塞、transient、有離開 transition；TLC `SDD_FSM` reachable 41→42、`ObservationsTransient`（含 `SF_vars(T_ExperimentReplayDone)`）+ `EventuallyTerminal` 全 PASS。

#### Pillar C — 主動規格脆弱性預測（PL-3；無新狀態）

**ACT-093 — Spec Fragility Scorer**
- **檔案**：`tools/fsm_runtime/spec_fragility_scorer.py`
- **設計**：合 RTM blast-radius + mutation/測試覆蓋缺口 + 歷史漂移頻率 + escalation 命中，加權出脆弱性分數（凍結 `FRAGILITY_PROFILE_VERSION`）。純離線、可重現、advisory。
- **驗收**：18 fixture（標註已知脆弱/穩健 AC）；脆弱 AC top-3 命中率 ≥ 85%、穩健 AC 誤列率 < 15%；改權重不 bump 版本 → 測試 fail（守自我放水禁令）。

**ACT-094 — Fragility 整合（無新狀態）**
- **檔案**：`steersman_renderer.py`（凍結前渲染熱圖 top-K）、`intent_decomposer.py`（分解時標記脆弱依賴節點）
- **規則**：fragility 只「標記/建議」，**絕不自動改 spec、絕不阻塞 SCG**（advisory）。
- **驗收**：整合測試；熱圖正確附掛 steersman digest；分解 DAG 的脆弱節點被標記但不改變 acyclic 結構。

#### 收官

**ACT-095 — Rule 9.24 治理落地**
- **檔案**：`governance/rules/R-9.24-meta-halting-offline-experiment-phase-l.yaml` + `governance/RULES_INDEX.md` + CLAUDE.md §9.24 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 89→97 / rule 9.24→9.25）。
- 子規則 9.24.1~9.24.6 見 §4。

**ACT-096 — Phase L 形式化重證 + 全綠驗收**
- **形式化**：`META_FSM.tla` 5 invariant No error + 離線 BFS reachable=N/N（PL-1）；單軌 `SDD_FSM` 加 `EXPERIMENT_REPLAY` 後三源同步、reachable 41→42=100%、4 safety + 2 liveness 全 PASS（PL-2）；`FLEET_FSM` 不回歸。
- **Chaos**：100 輪（新增 `META_CHURN_STORM`〔連續注入 add↔retire 抖動序列，驗 `ChurnBounded`〕+ `REPLAY_FLAKY`〔反事實判定抖動，驗 `EXPERIMENT_REPLAY` transient〕兩故障型）bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：估 K-1 20 + K-2 24 + K-3 18 + 整合/chaos/形式化 ≈ 20 ≈ **+82**（781 → 約 863 passed）。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-089（Meta-Loop Ledger）─────► ACT-090（META_FSM + meta_halt_monitor + TLC/BFS）
ACT-091（Counterfactual Replay）─► ACT-092（EXPERIMENT_REPLAY + SPEC_PATCH 整合 + 單軌 TLC 41→42）
ACT-093（Fragility Scorer）──────► ACT-094（steersman/intent 整合）
                        三柱完成 ─► ACT-095（Rule 9.24 + ID 翻牌）─► ACT-096（雙形式化重證 + chaos + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L9 入口（離線切片）+ L10 元停機形式化奠基**：

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L5 | Self-Driving（學習層 + 形式化停機） | A~G |
| L6 | Trustworthy Scaled（判官自審 + 增殖 + 雙形式化 + 艦隊並行） | I |
| L7 入口 | Adversarial & Self-Improving（對抗判官 + 能力代謝 + 規格自癒） | J |
| L8 入口 | Intent-Driven（意圖分解 + 辯證消歧 + 因果接地） | K |
| **L9 入口（離線切片）** | **Counterfactual Reality-Grounding（離線反事實驗證規格假設 + 主動脆弱性預測）** | **L（本份 PL-2/PL-3）** |
| **L10 奠基** | **Meta-Halting 形式化（自我改進元迴圈不震盪證明）** | **L（本份 PL-1）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— 受 OPEN-10.6 約束，待 OPEN-L.5 放寬沙箱決策 | 未來 Phase M |
| L10 完整（horizon） | 組合級意圖自治（跨多軌意圖組合優化，承 `FLEET_FSM` 並行基座往「意圖組合」延伸） | 未來 Phase M |

> **誠實標定**：本份**不宣稱達成完整 L10**。完整 L10 需「跨多軌意圖的組合級優化」+「元迴圈在活體生產的形式化停機」；本份只交付其**形式化奠基石（meta-halting 證明）**與 **L9 離線切片**。完整 L9/L10 列 horizon，前置阻礙明列於 §3.4 與 OPEN-L。

### 3.4 L9 完整 / L10 完整 Horizon（本份不實作，僅定錨）
- **L9 完整 — 活體現實實驗**：系統對活體生產流量自主下 canary/shadow 實驗統計驗證規格假設。**前置阻礙**：OPEN-10.6（本地唯讀 / 無 HTTP）+ 需真實生產整合。本份以「離線反事實重放（拿自身歷史當現實代理）」交付**可在本地完成的等價驗證價值**，活體版待 OPEN-L.5 決策。
- **L10 完整 — 組合級意圖自治**：承 Phase I `FLEET_FSM`（N 軌並行已證無死鎖）+ Phase K `intent_decomposer`（單意圖分解），延伸為「多意圖組合排程 + 跨軌資源/規格依賴的全域最佳化」，且該組合層也須形式化停機。本份的 `META_FSM` 已示範「協調層獨立形式化」的可複用路徑，為其鋪路。

---

## 4. 防護規則新增（CLAUDE.md §9.24 Phase L）

> 待 SCG-0 凍結並執行完成後正式寫入 CLAUDE.md §9.24（此處為草案，供 SCG-0 審視）。

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.24.1 元迴圈 churn 有界 | ACT-089/090 | 任一規則指紋的 add→retire→re-add 循環 ≤ `SDD_META_CHURN_MAX`（clamp[1,5]，預設 2）；超限→`MFSM_ESCALATION`，絕不無限抖動 |
| 9.24.2 退役棘輪（GraduationRatchet） | ACT-090 | 被 GC 退役的規則指紋，再採納必須挾帶 `capability_level` 嚴格變化證據；無 capability-delta 的同型 re-adopt 一律拒絕 |
| 9.24.3 META_FSM 獨立形式化 | ACT-090/096 | `META_FSM.tla` 自有命名空間，**不併入單軌 `SDD_FSM.tla`**；5 invariant + 離線 BFS reachable=N/N；單軌 `SDD_FSM` reachable 維持不回歸（41→42 僅因 `EXPERIMENT_REPLAY`，非 meta 污染） |
| 9.24.4 反事實重放 advisory + 有界 | ACT-091/092 | `EXPERIMENT_REPLAY` 重放筆數 ≤ `SDD_REPLAY_MAX_CASES`（clamp[5,200]）；命中率僅為證據，**絕不自動 approve/改寫補丁**，最終 approve 必經 `HUMAN_PENDING`（Rule 8） |
| 9.24.5 脆弱性評分 advisory + 不自我放水 | ACT-093/094 | `spec_fragility_scorer` 只標記/建議，**絕不自動改 spec、絕不阻塞 SCG**；分數凍結 `FRAGILITY_PROFILE_VERSION`，調權重須 bump（比照 `SCORER_VERSION`/`ADVERSARIAL_PROFILE_VERSION`） |
| 9.24.6 單軌三源 + 雙形式化同步 | ACT-092/096 | `EXPERIMENT_REPLAY` 同步 `_HAPPY_PATH ↔ SDD_FSM.tla ↔ SDD_FSM_ENGINE.md`（observation 有離開 transition、∉ Terminals）；`META_FSM` 與單軌雙形式化皆過 `tlc_runner` + 離線 BFS |

### ❌ Phase L 新增禁止行為（草案）
- 學習層 `exit_learning_commit("approved")` 或 GC `set_maturity()` 繞過 `meta_halt_monitor` 的 `ChurnBounded` 檢查（破 9.24.1）
- 把被退役規則無 capability-delta 地重新學回（破 9.24.2 GraduationRatchet，製造同型震盪）
- 把 `META_FSM` 狀態併入單軌 `SDD_FSM.tla`、或讓 meta churn 污染單軌 reachable 計數（破 9.24.3 / Rule 9.18.1）
- 讓 `EXPERIMENT_REPLAY` 命中率自動 approve 補丁、或自動改寫 AC（破 9.24.4 / Rule 8）
- `EXPERIMENT_REPLAY` 重放筆數無上限、或誤列為 Terminals/blocking（破 9.24.4 / 9.24.6 / Rule 9.18.4）
- `spec_fragility_scorer` 自動改 FRD/AC 或阻塞 SCG（破 9.24.5 / Rule 8）
- 調 fragility 權重不 bump `FRAGILITY_PROFILE_VERSION`（破 9.24.5，評分器自我放水）
- 為 L9 完整活體實驗私自開 HTTP 外聯而未經 OPEN-L.5 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：Spec 寫錯 → 測試永不過；並推到元層）

| 生命週期點 | L8（Phase K）現況行為 | Phase L 強化後行為 |
|------------|----------------------|--------------------|
| **凍結前·風險** | 規格脆弱性只能等 drift 事後暴露 | **`spec_fragility_scorer` 凍結前即報「此 AC top-1 脆弱」** → steersman 熱圖 → 舵手提前加強測試合約 |
| **凍結前·結構/語義** | `INTENT_DECOMPOSITION` 偵環 + `SPEC_DEBATE` 辯證消歧（K 既有） | 同左，且分解時 fragility 標記脆弱依賴節點 |
| **實作後** | `ADVERSARIAL_EVALUATION` 抓 spec_gap → `SPEC_AUDIT`（J/K 既有） | 同左 |
| **生產後·定位** | `spec_localizer` 自動定位該補哪條 AC（K 既有） | 同左 |
| **生產後·補丁驗證** | `spec_patch_proposer` 自擬 diff，**憑信任**送 `HUMAN_PENDING` | **`EXPERIMENT_REPLAY` 對歷史失敗反事實重放** → 「擋住 4/5 + 1 反例」附證據送審 |
| **元層·自我演化** | 學習加規則 / GC 退規則 / FSE 演化**靠紀律不抖動，無數學保證** | **`META_FSM` 形式化證 `ChurnBounded` + `GraduationRatchet` + `EventuallyMetaStable`**；抖動即 `MFSM_ESCALATION` 導人工 |
| **引導人類** | 自動定位 + 自擬 diff，人類 approve/reject（K） | + 人類看「歷史命中證據」approve、+ 人類審「框架自我演化收斂界限」——舵手升至**元層** |
| **有界性** | 單軌 TLC 41/41 + 艦隊 `AllEventuallyDone` | + **元迴圈 `META_FSM` 形式化必達不動點** + 單軌 41→42 重證 + 重放/churn 雙故障型 chaos bounded 1.0 |
| **Token** | 凍結前消歧已省（K） | **更省**（脆弱性事前預防 + 補丁先離線驗證命中率，免去無效補丁的實作-對抗-修補往返；且元層保證不會「學了又退」白燒 token） |

✅ **模擬通過（含元層）**：對「Spec 寫錯導致測試永不過」案例，Phase L 在**凍結前（脆弱性預測）、補丁前（反事實重放）、元層（自我演化收斂）** 三個新生命週期點皆能優雅停機並引導人類，每道閘形式化有界。**最關鍵的躍遷**：連「框架不斷學新規則又退舊規則」這種**元層的潛在無限迴圈**，都被 `META_FSM` 的 `ChurnBounded`/`GraduationRatchet` 數學上排除——這把提示「停機問題、絕不無限重試耗 Token」的要求，從單一任務層**提升到框架自我改進層**，是 L10 的真正門檻。人類在所有層級全部從「救火/信任/憑紀律」升為「審風險/審證據/審界限」，維持「設計環境掌舵者」高度於最高層。

---

## 6. 執行順序與里程碑

```
M-L1 元停機奠基：ACT-089 → ACT-090（META_FSM + TLC/BFS）  ── 先做，L10 奠基石、純離線、價值最高、不受 OPEN-10.6 約束
M-L2 離線反事實：ACT-091 → ACT-092（EXPERIMENT_REPLAY + SPEC_PATCH + 單軌 TLC 41→42）── 緊接，補丁送審前先取現實命中證據
M-L3 主動脆弱性：ACT-093 → ACT-094（steersman/intent 整合）── 中期，把因果定位從反應式升為主動式
M-L4 收官：ACT-095（Rule 9.24 + ID 翻牌）→ ACT-096（雙形式化重證 + chaos + pytest 全綠）
```

**每個 M-Lx 完成即跑該層 pytest + 必要時 `tlc_runner`，絕不累積**（守 Rule 4 開發-編譯-測試循環）。
**M-L1 與既有動態工作流的接點**：PL-1 的 `META_FSM` 直接為使用者所指的「具自我修正能力的動態工作流」（`SDD_SELF_EVOLUTION.md` FSE + 學習層 + GC）補上其**唯一缺失的形式化停機保證**——FSE 已用「fitness 嚴格遞減 → well-ordering」論證單次 run 收斂，`META_FSM` 則把這個保證提升到跨 session、跨三條相反迴圈的聯合層級。

---

## 7. 待人工決策（OPEN-L）

> 🔴 本份為 DRAFT。以下 OPEN-L 須人工裁決後方可凍結 SCG-0、進入逐 ACT 執行（守 Rule 8 / Rule 9.23.2）。建議預設值已標於「建議」欄，可一次採納或逐項調整。

| ID | 議題 | 建議 |
|----|------|---------|
| OPEN-L.1 | 徵用 ACT-089~096 / Rule 9.24 是否確認（由 `id_registry next-act/next-rule` 取自前緣 89 / 9.24）？ | ✅ 建議確認；收官 ACT-095 翻牌 + `test_id_registry.py` 守門 |
| OPEN-L.2 | `META_FSM` 是否如建議**獨立命名空間**（不入單軌 `SDD_FSM.tla`），沿用 `FLEET_FSM` 模式？ | 建議獨立（守 Rule 9.18.1 單軌證明不回歸） |
| OPEN-L.3 | `SDD_META_CHURN_MAX` 預設 2 / `SDD_REPLAY_MAX_CASES` 預設 50 是否合適？ | 預設 2 / 50，env 可調（執行時校準） |
| OPEN-L.4 | Counterfactual Replay v1 限 rule-based（零成本）抑或允許 LLM 反事實推理？ | rule-based v1（守 G~K 慣例）；LLM 留 v2 並更新成本 gate（比照 OPEN-J.1/K.2） |
| OPEN-L.5 | 是否啟動 OPEN-10.6 沙箱外聯放寬評估，以推進 **L9 完整（活體 canary/shadow）**？ | 暫不；維持本地唯讀，本份交付 L9 離線切片，活體版待專案有真實生產整合需求再評（延續 OPEN-K.5） |
| OPEN-L.6 | fragility 分數是否影響 `value_planner` ROI 排序（高脆弱 = 高優先修），抑或純 advisory 顯示？ | 建議純 advisory 顯示（不自動改排序，守 planner 不自我裁決）；v2 再評是否納入 ROI 公式 |

---

**藍圖等級目標**：L8 入口 → **L9 入口（離線切片）+ L10 元停機形式化奠基 — Meta-Halting Formalization & Offline Counterfactual Reality-Grounding**
**前置 SCG**：🟡 SCG-0（需求凍結）**PENDING** — 待 OPEN-L 裁決、範疇確認、無矛盾後，方准予逐 ACT 執行。
**形式化承諾**：`META_FSM` 5 invariant（含 `ChurnBounded`/`GraduationRatchet`/`EventuallyMetaStable`）No error + 離線 BFS reachable=N/N；單軌 `SDD_FSM` 加 `EXPERIMENT_REPLAY` 後 reachable 41→42=100%、`EventuallyTerminal`/`ObservationsTransient` 不回歸；`FLEET_FSM` 不回歸；chaos（含 `META_CHURN_STORM`/`REPLAY_FLAKY`）bounded_ratio=1.0。
**與動態工作流的關係**：本藍圖即「具自我修正能力的動態工作流深度優化」之續推——它把使用者既有的自我演化迴圈（`SDD_SELF_EVOLUTION.md` + 學習層 + GC）從「靠紀律收斂」升級為「形式化證明收斂」，並補上「拿歷史現實驗證補丁」與「事前預測規格脆弱性」兩道主動防線。
