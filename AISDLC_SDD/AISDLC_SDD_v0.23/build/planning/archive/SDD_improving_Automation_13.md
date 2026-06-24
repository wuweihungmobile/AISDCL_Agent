# SDD_improving_Automation_13 — Phase M 藍圖（DRAFT）

**主題**：組合級意圖自治形式化 + 自我演化進步性監測 + 組合級脆弱性（Composition-Level Intent Autonomy & Self-Evolution Progress Monitoring）
**目標等級**：L9 入口（離線切片）+ L10 元停機奠基（Phase L 已達）→ **L10 完整奠基（組合級）+ 自我演化進步性形式化**（系統不只證明「單意圖開發迴圈」「N 軌資源並行」「學習↔退役元迴圈」皆有界停機，更把停機論證推到**多意圖語義組合層**——證明「同時推進 N 個意圖、其規格在共享節點上不會永久互相否定」必收斂；同時補上 Phase L `META_FSM` 的**對偶盲區**：`ChurnBounded` 只證「不抖動」、未證「真進步」，本份加上**進步性監測**，當自我演化陷入「有界但停滯」的高原時主動引導人類舵手注入新工具/典範）
**建立日期**：2026-06-03
**前置基線**：Phase L 完整（ACT-089~096，L9 入口離線切片 + L10 元停機奠基；pytest 844 綠、單軌 `SDD_FSM` TLC reachable 42/42、`META_FSM` No error（13 distinct，5 safety + EventuallyMetaStable liveness）、`FLEET_FSM` 無死鎖 + AllEventuallyDone、chaos 100 輪 bounded_ratio=1.0）
**狀態**：✅ **EXECUTED 2026-06-03（L10 完整奠基（組合級）+ 自我演化進步性形式化達成）** — 使用者「直接進入執行」signoff（採 OPEN-M 全建議預設值，含 OPEN-M.7 暫不放寬沙箱、維持 L9 離線切片），M-M1（ACT-097/098）、M-M2（ACT-099/100）、M-M3（ACT-101/102）、M-M4 收官（ACT-103 R-9.25 active + ID_REGISTRY 翻牌 next_free act=105/rule=9.26 + CLAUDE §9 禁令#15 + INIT 禁止事項；ACT-104 形式化重證 + chaos + pytest 全綠）全部完成。**驗收：pytest 885 passed / 6 skipped（基線 844 → +41 Phase M：test_phase_m 37 + test_id_registry +1 + test_chaos +3）+ chaos 套件 27 passed（含 COMPOSITION_CONFLICT_STORM / CEILING_FLAP 兩 Phase-M 故障型，100 輪 bounded_ratio=1.0）；COMPOSITION_FSM TLC No error（21 distinct，5 safety + EventuallyComposed liveness）+ 離線 BFS reachable=5/5；四軌 TLC 全 No error 不回歸（單軌 SDD_FSM 556 distinct / META_FSM 13 / FLEET_FSM 7 / COMPOSITION_FSM 21）；單軌 CPLAN_* 零洩漏（Rule 9.25.3 隔離成立）。** QA/Architect 抓漏稽核：BLOCKER 0 / MAJOR 0。

> 🔴 **原 DRAFT 紀錄（保留）**：本份為 Karpathy 式前沿評估的規劃產出，OPEN-M 待人工裁決後方可逐 ACT 執行（守 Rule 8 / Rule 9.23.2：planner 不自我裁決、不繞過 `BACKLOG_PRIORITIZED` 人工 signoff）。已於 2026-06-03 獲使用者「直接進入執行」signoff，採 OPEN-M 全建議預設值。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 本份為 L9/L10 奠基 → **L10 完整奠基（組合級）** 續推。

> 🔴 **編號徵用告示（承 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml) `next_free`）**：
> 本藍圖徵用 **ACT-097~104 與 Rule 9.25**（取自登記簿前緣 act=97 / rule=9.25，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> 執行收官（ACT-103）時須由 `id_registry` 翻牌（act 97→105 / rule 9.25→9.26）+ `test_id_registry.py` pytest 守門固化，撞號由 CI 自動攔截。
> **DRAFT 期間不得翻牌**——僅在獲人工 signoff 並執行至收官時才推進 `next_free`。

---

## 0. 為什麼還需要 Phase M？——對既有設計的誠實剖析（含 `<thinking>`）

<thinking>
這份提示要求「驗證圖靈完備自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K/L 的紀律，正確的第一步是**對賬而非設計**——這套系統已走過 Phase A~L、是自稱「L9 入口 + L10 奠基」的成熟框架，盲目套提示的前沿清單只會重造輪子（提示本身的清單在 Phase K/L 已逐項對賬為 100% 落地）。我的任務是用提示三漏洞視角，往 **L9/L10 奠基已完成的現況之上**，挖出 grep 可證零實作的**新**結構性缺口。

【一、提示前沿清單 × 既有落地對賬（承 Phase K/L，補上 Phase L 新增）】
- 生成與評估分離（GAN 啟發）→ ✅ Phase H `sdd-evaluator`（獨立 worktree）+ Phase J `adversarial_synthesizer` + Phase K `spec_debate` + **Phase L `counterfactual_replay`（補丁 vs 歷史現實判官）**。四層分離。
- 主觀標準量化 → ✅ `AmbiguityScorer`（G M3，`SCORER_VERSION`）+ `output_quality_scorer`（OQS）+ `ADVERSARIAL_PROFILE_VERSION`（J）+ **`FRAGILITY_PROFILE_VERSION`（L）**。
- 評估器實體操作（Playwright/沙箱）→ ✅ `sandbox_runner` + `evaluate_hermetic`（`--network none`/`--cap-drop ALL`）+ `R-SELF-STRIDE`。
- 動態演進框架、移除鷹架 → ✅ `SCAFFOLD_GC`（H）+ 能力感知 graduation（J，`capability_surpassed`）+ **`META_FSM` 形式化證 add↔retire 不抖動（L）**。
- 單一真實來源、漸進式揭露 → ✅ `RULES_INDEX.md` + `rule_loader.load_for_state()` + `ID_REGISTRY.yaml`。
- 運行時可觀測性（LogQL/PromQL）→ ✅ `observability_query`（H，本地唯讀）。
- 不變量 + GC → ✅ Rule 9 全鏈 + `spec_monitor`（.tla invariant→runtime assertion）+ `SCAFFOLD_GC` + `SDD_SELF_EVOLUTION.md`（FSE + `arch_fitness`）。
- Planner→G/E 合約談判 → ✅ 微觀 `TEST_CONTRACT_NEGOTIATED`（H）+ 宏觀 `INTENT_DECOMPOSITION`（K，**單意圖**）。
- 停機問題 + 人類掌舵者 → ✅ 單軌 `SDD_FSM` 42/42 + 艦隊 `FLEET_FSM` `AllEventuallyDone` + **元迴圈 `META_FSM` `EventuallyMetaStable`（L）** + `steersman_renderer` + `spec_patch_proposer`（J）+ `spec_localizer`（K）+ **`EXPERIMENT_REPLAY` 離線反事實（L）**。

結論：**提示前沿清單已 100% 對應落地，且三條停機論證（單軌/艦隊/元迴圈）皆已形式化。** 所以 Phase M 必須挖出 L9/L10 奠基之上**仍真實存在、grep 可證零實作**的結構性缺口。我用提示三漏洞視角逐一往深處挖，並對照框架自陳的 horizon（[`SDD_improving_Automation_12.md`](../archive/SDD_improving_Automation_12.md) §3.4 的「L10 完整 = 組合級意圖自治」）。

【二、用提示三個指定漏洞視角，逐一往 L9/L10 奠基深處挖】

(A) 狀態轉換——「Planner 宏觀規格擴展 → Generator/Evaluator 微觀合約談判」這個分層，在**單意圖**內完整，在**多意圖組合層卻是開迴圈**。
框架的宏觀談判 `INTENT_DECOMPOSITION`（K）只處理**一個**意圖→子規格 DAG；艦隊 `FLEET_FSM`（I）證了 N 軌並行，但讀 `FLEET_FSM.tla` 可見：它鎖的是**抽象 spec 區段鎖（Locks）**，證的是 `LockMutex`/`NoPartialHold`/`AllEventuallyDone`——即「資源層級」無死鎖。但兩個意圖**完全可以各自正確地取放鎖、卻在語義上留下互相矛盾的規格**（意圖 A 把共享 AC-014 設成 X、意圖 B 把重疊的 AC-014′ 設成 ¬X）。`value_planner.py`（I）只做**逐意圖獨立 ROI 排序**（`business_value × confidence / cost`），輸出扁平 `BACKLOG-RANK`——**它不偵測「兩個意圖踩同一個 spec 節點」，更沒有「組合後全域規格一致」的形式化保證**。這正是提示「狀態轉換／開發前對測試標準達成共識」推到**組合層**的型態，也精準對應框架自陳的 L10 完整 horizon「組合級意圖自治 + 該組合層也須形式化停機」。grep `composition|multi_intent|cross_intent|intent_composer|COMPOSITION_FSM` 在 `tools/` **零命中**（唯一命中是**單意圖** `INTENT_DECOMPOSITION`）。→ **PM-1**（最關鍵；L10 完整奠基石，純離線、純形式化，不受 OPEN-10.6 約束）。

(B) 停機問題——`META_FSM`（L）證了「不抖動」，但**沒證「真進步」**，這是它的對偶盲區。
讀 `META_FSM.tla`：`ChurnBounded`（churn≤MAX）只排除 add↔retire 無限震盪；`GraduationRatchet`（churn≤cap）要求再採納挾 capability-delta；`EventuallyMetaStable` 證必抵 `{STABLE, ESCALATION}`。**但一個 `ChurnBounded` 成立、卻永遠停在 `MFSM_STABLE` 而能力毫無長進的系統，照樣是失敗**——「穩定地平庸」。提示明確要的是「評估框架能隨底層模型能力提升而**動態演進**、**大膽移除**不再需要的鷹架」「人類維持設計環境掌舵者高度」。框架現況：`scaffold_gc.py` 只退役 **0-fire 死鷹架** 或 **`capability_surpassed` 已被模型超越** 的鷹架；它**偵測不到「仍在 fire、未被正式判定超越、但已成淨負天花板（crutch/ceiling）的鷹架」**——即鷹架還在動、卻在拖慢/封頂產出（拿掉它反而更好）。更關鍵：**整個框架沒有任何元件回答「我的自我演化到底在不在進步，還是已陷高原？」** grep `ceiling|crutch|net_negative|capability_trajectory|capability_plateau|plateau|stagnat|diminishing_return` 在 `tools/` **零命中**。`META_FSM` 的 liveness 只證「會停」，缺一個**進步性（progress）對偶**：偵測「有界但停滯」→ 引導人類舵手注入新工具/典範（而非系統自己亂改）。→ **PM-2**（自我演化進步性監測 + 淨負鷹架天花板偵測；advisory，是 `ChurnBounded` 的對偶補強）。

(C) 上下文污染／絕對可觀測性——脆弱性預測（L）是**單一規格**視角，組合後的**爆炸半徑會相乘**卻無人估。
Phase L 的 `spec_fragility_scorer.py`（grep 證 `blast.radius` 2 處）算的是**單一 AC** 的 blast-radius × 覆蓋缺口 × 漂移頻率。但在 PM-1 的組合層，**一個脆弱的共享 spec 節點若被 ≥2 個在飛的意圖同時依賴，它一旦爆炸會跨多個意圖串級失敗**——這個「組合級爆炸半徑乘數」目前無人計算。提示的 OpenAI「環境防護／在訊號發生前豎好邊界」精神要的正是：在組合排程**提交前**就看到「哪些共享節點是跨意圖的定時炸彈」，據此把高共享脆弱度的意圖**排成序列而非並行**，並餵 `steersman_renderer` 讓舵手在組合凍結前就看到。grep `composition_blast|cross_intent_blast|blast_multiplier` **零命中**。→ **PM-3**（組合級脆弱性，advisory，支撐 PM-1 排程器；把 L 的單一脆弱性升級為組合脆弱性）。

【三、上下文衰減（Context Degradation）視角覆查】
- PM-1 的 `COMPOSITION_FSM` 是**形式化規格 + 協調層帳本**，不常駐主線 context：組合協商事件落 `build/state/composition-ledger.yaml`（`file_lock` 保護），`.tla` 由 `tlc_runner` 跑，主線只在 `BACKLOG_PRIORITIZED` 後與收官時讀組合摘要。**完全比照 `FLEET_FSM`/`META_FSM` 既有的「獨立命名空間協調層」作法**，零新增常駐 prompt、不污染單軌 `SDD_FSM`。
- PM-2 的軌跡監測讀既有落盤訊號（OQS 報告、escalation 紀錄、`meta-loop-ledger`、`scaffold_roi`），結論落 `build/reports/trajectory/*.md`；鷹架 A/B 影子評估在**隔離 context** 跑（仿 `sdd-evaluator`），只把「淨值差」回主線。
- PM-3 組合脆弱性熱圖落 `build/reports/composition-fragility/*.md`，`steersman_renderer` 只渲染 top-K。
→ 三者皆守漸進式揭露，不引入新的脈絡焦慮。

【四、停機問題（Halting）視角覆查——不可退讓的紅線，且本份核心 PM-1 正是衝著它來】
本份的反諷與 Phase L 同構：核心交付（PM-1）**就是把停機保證推到第四條迴圈（組合層）**。所以每個新機制的有界性要加倍嚴謹：
- PM-1 `COMPOSITION_FSM` 必證核心 meta-invariant **`RenegotiationBounded`**：任兩意圖在共享節點上的「協商→否定→再協商」循環 ≤ `SDD_COMPOSITION_RENEG_MAX`（clamp[1,5]，預設 2），超限即 `CPLAN_ESCALATION`（人工裁決哪個意圖讓步 / 共享 AC 是否需要統一規格）。配 `CompositionConsistent`（已提交意圖兩兩在共享節點上不矛盾）+ `EventuallyComposed`（liveness：必抵 `{CPLAN_STABLE, CPLAN_ESCALATION}`）。論證同構於 `META_FSM` 的 `ChurnBounded`/`EventuallyMetaStable` 與 `FLEET_FSM` 的 fairness liveness。**這直接排除「兩意圖規格永久互相否定」的組合層 livelock**。
- PM-2 為純 advisory：plateau / ceiling 訊號**絕不自動觸發典範轉移或自動退役仍在 fire 的鷹架**——只把「進步停滯」「此鷹架淨負」當證據導向**人類舵手**（這恰是提示「引導人類提供 AI 缺失的工具/環境限制、人類維持掌舵者」的最高體現）。鷹架退役仍須 `set_maturity(reviewed_by=)` 人工 gate（守 Rule 9.20.5）。
- PM-3 純 advisory **不新增任何狀態**（比照 `spec_fragility_scorer`/`spec_localizer`），分數凍結 `COMPOSITION_FRAGILITY_PROFILE_VERSION`，調權重須 bump（守「評分器不可自我放水」）。
- 人類掌舵者高度**不降反升**：從 Phase L 的「審單一補丁的現實命中、審元迴圈收斂界限」升至「審**多意圖組合的全域一致性界限**、審**框架自我演化是否真在進步**」——把「掌舵者而非編碼員」推到組合層與進步性層。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性）：把「組合一致性界限」「進步性軌跡」「組合脆弱性熱圖」全部落地為 **Markdown/YAML/TLA+ 可推理產物**（composition-ledger、trajectory report、composition-fragility heatmap、`COMPOSITION_FSM.tla`），不藏在 prompt 裡；`COMPOSITION_FSM` 形式化規格本身就是「AI 可直接推理的組合層環境邊界宣告」。
- Anthropic（對抗 / 動態演進）：把「動態演進框架、大膽移除鷹架」從「退死鷹架」（H）、「退被超越的鷹架」（J）再往前推到**「退淨負的天花板鷹架」**（PM-2 A/B 影子評估）；並補上「自我演化是否真進步」的**進步性對偶**——你敢說自己在自我改進，就得能證明（或至少測量）你真的在變強，而非有界地原地打轉。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H/I/J/K/L 落地元件**（對賬見上 thinking 一節），三條停機論證（單軌 `SDD_FSM` 42/42、艦隊 `FLEET_FSM`、元迴圈 `META_FSM`）皆已形式化。Phase M 的價值在用提示三漏洞視角挖出 L9/L10 奠基之上仍真實存在、grep 證零實作的 **3 個結構性缺口**：

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PM-1** | **停機/合約談判只到「單意圖 + 資源並行」，沒到「多意圖語義組合」**——`INTENT_DECOMPOSITION`（K）只分解單意圖；`FLEET_FSM`（I）只證資源鎖層級無死鎖（`LockMutex`/`AllEventuallyDone`）；`value_planner`（I）只做逐意圖獨立 ROI 排序。**兩意圖可各自正確取放鎖、卻在共享 spec 節點留下互相矛盾的規格**，且「組合後全域一致」從未形式化。框架自陳此為 L10 完整 horizon。 | `composition\|multi_intent\|cross_intent\|intent_composer\|COMPOSITION_FSM` **零命中**（唯一命中為單意圖 `INTENT_DECOMPOSITION`） |
| **PM-2** | **`META_FSM`（L）證「不抖動」但沒證「真進步」**——`ChurnBounded` 排除 add↔retire 震盪，卻容許「`ChurnBounded` 成立、能力卻原地踏步」的高原；`scaffold_gc`（H/J）只退 0-fire 死鷹架或 `capability_surpassed` 被超越的鷹架，**偵測不到「仍 fire、未被判定超越、卻已淨負（crutch/ceiling）」的鷹架**；全框架無任何元件回答「我的自我演化在不在進步」。 | `ceiling\|crutch\|net_negative\|capability_trajectory\|plateau\|stagnat\|diminishing_return` **零命中** |
| **PM-3** | **脆弱性預測只到單一規格，沒到組合**——`spec_fragility_scorer`（L）算單一 AC 的 blast-radius；但組合層**一個脆弱的共享節點被 ≥2 意圖同時依賴時，爆炸半徑會跨意圖相乘串級**，這個「組合級爆炸半徑乘數」無人計算，無法在組合排程提交前把高共享脆弱度意圖排成序列。 | `composition_blast\|cross_intent_blast\|blast_multiplier` **零命中**（單一規格 `blast_radius` 已存在於 `spec_fragility_scorer.py`） |

**三缺口的共同主軸**：L9/L10 奠基讓人類站在「審單意圖的分解/詮釋/補丁/現實命中、審元迴圈收斂」的高度，而框架的**多意圖組合仍是憑紀律維持的開迴圈、自我演化只證不抖動卻不證真進步、組合脆弱性只能事後串級爆炸才暴露**。Phase M 把人類抬到「審整個**意圖組合**的全域一致性收斂界限、審框架**是否真在自我精進**、在組合炸彈跨意圖引爆前就看到**組合脆弱性熱圖**」——這正是 L10 完整奠基（組合級）+ 自我演化進步性形式化的定義，也精準補上提示在「狀態轉換（組合層合約談判）」「停機問題（組合 livelock + 進步性對偶）」「動態演進（退淨負鷹架）」三個視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase M 增量）

Phase M 對狀態機的改動刻意**對單軌零表面積**：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42 reachable 不回歸），PM-2/PM-3 為 advisory 不新增狀態，而 PM-1 比照 `FLEET_FSM`/`META_FSM` 的「協調層獨立命名空間」原則，**另闢 `COMPOSITION_FSM` 形式化層**，**不污染單軌 `SDD_FSM.tla`** 的既有 42/42 證明。

### 1.1 新增狀態總覽

| 狀態 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `COMPOSITION_FSM`（`CPLAN-*` 狀態族） | **獨立 `COMPOSITION_FSM.tla`**（不入單軌） | 組合協調層 | `BACKLOG_PRIORITIZED` 後選定 **≥2** 意圖時觸發 | 抵 `CPLAN_STABLE`（全域一致、可排程）或 `CPLAN_ESCALATION`（協商觸頂，人工裁決） | — |
| PM-2（`capability_trajectory_monitor` / `scaffold_ceiling_detector`） | advisory（無狀態） | — | 跨 session 收官 / `MEMORY_CONSOLIDATION` / `SCAFFOLD_GC` 旁路 | 報告落盤 + 高原/天花板訊號導人工 | 否 |
| PM-3（`composition_blast_analyzer`） | advisory（無狀態，餵 `COMPOSITION_FSM` 排程器 + steersman） | — | 組合排程提交前 | 熱圖落盤 + 排程建議 | 否 |

> **選位說明**：
> - `COMPOSITION_FSM` **不是單軌狀態**，也**不是 `FLEET_FSM` 的替代**。`FLEET_FSM` 證「N 軌**已開始後**的資源鎖無死鎖」；`COMPOSITION_FSM` 證「N 意圖**開始前**的語義規格組合一致性收斂」——兩者是**前後相鄰的兩個協調層**（組合協商 → 確定全域一致 → 才交給艦隊並行執行）。沿用 `FLEET_FSM`/`META_FSM` 既有「另開 .tla + 自有 invariant/liveness/reachability」的成功模式，**不動 Rule 9.18.1 的單軌三源一致性**。
> - 單意圖（僅 1 個意圖選定）走原 happy-path，**完全向後相容**，不進 `COMPOSITION_FSM`。

### 1.2 COMPOSITION_FSM 組合層有界停機契約（最關鍵；L10 完整奠基石）

```
（組合協調層，狀態變數 = {intents[], shared_nodes, conflict_set, reneg_count, capability_level}）
CPLAN_OBSERVE（讀 BACKLOG_PRIORITIZED 選定的 ≥2 意圖；intent_composer 算共享 spec 節點 + 衝突集）
  ├─ 無共享節點衝突 → CPLAN_COMMIT（全域一致，產組合排程）→ CPLAN_STABLE
  ├─ 有衝突且 reneg_count < MAX_RENEG → CPLAN_NEGOTIATE（記 reneg++，要求意圖在共享節點調和）→ 回 CPLAN_OBSERVE
  └─ 有衝突且 reneg_count ≥ MAX_RENEG → CPLAN_ESCALATION（協商觸頂，人工裁決）
```

- **核心 meta-invariant `RenegotiationBounded`**：任兩意圖在任一共享 spec 節點指紋（`pattern_matcher` 正規化）的「協商→否定→再協商」循環次數 ≤ `SDD_COMPOSITION_RENEG_MAX`（clamp[1,5]，預設 2）。超限即 `CPLAN_ESCALATION`，**絕不無限協商 livelock**。
- **`CompositionConsistent`（一致性不變量）**：任何進入 `CPLAN_COMMIT` 的意圖集合，其在共享節點上**兩兩不矛盾**（衝突集為空）；否則不得 commit、必導 `CPLAN_NEGOTIATE` 或 `CPLAN_ESCALATION`。
- **`ConflictResolvedOrEscalated`**：`CPLAN_COMMIT` ⟹ 所有共享節點衝突已解；不可能帶著未解衝突進入排程。
- **`StableIsFixpoint`**：`CPLAN_STABLE` 為吸收不動點（後繼仍 STABLE）；`CPLAN_ESCALATION ∉ 不動點集合`（人工求援態，非健康收斂）。比照 `META_FSM.StableIsFixpoint` 既有寫法。
- **`EventuallyComposed`（liveness）**：在公平性假設（`SF_vars`）下，組合層最終抵達 `{CPLAN_STABLE, CPLAN_ESCALATION}`，不會永久協商。論證同構於 `META_FSM.EventuallyMetaStable` 與 `FLEET_FSM.AllEventuallyDone`。
- **可觀測落盤**：組合協商事件寫 `build/state/composition-ledger.yaml`（`file_lock` 保護），跨 session 審計鏈；`COMPOSITION_FSM.tla` + `.cfg` 由 `tlc_runner` 跑，並以離線可達性 BFS 不變量常駐守門（零 Java 依賴，比照 ACT-090 `META_FSM` 既有作法）。

### 1.3 PM-2 自我演化進步性監測（advisory，無新狀態；ChurnBounded 的對偶）

```
capability_trajectory_monitor（跨 session）
  讀 {OQS 歷史, escalation_rate, meta-loop-ledger churn, scaffold_roi, arch_fitness}
  → 算「淨能力軌跡」（凍結 TRAJECTORY_PROFILE_VERSION）
  ├─ 軌跡上升 → 健康（純記錄）
  ├─ 軌跡平坦且 churn 仍在發生（ChurnBounded 成立但不進步）→ PLATEAU 訊號 → 導人類舵手（「自我演化停滯，請注入新工具/典範」）
  └─ 軌跡下降 → REGRESSION 訊號 → 導人類舵手（高優先）

scaffold_ceiling_detector（旁路 SCAFFOLD_GC）
  對「仍在 fire、未被 capability_surpassed 判定退役」的鷹架，做 A/B 影子評估（隔離 context）：
    代表性任務 WITH 鷹架 vs WITHOUT 鷹架 → 比較 OQS
  ├─ WITHOUT 顯著優於 WITH（淨負）→ CEILING 訊號 → 建議人工退役（須 set_maturity(reviewed_by=)）
  └─ WITH ≥ WITHOUT → 鷹架仍有價值（保留）
```

- **進步性是 `ChurnBounded` 的對偶**：`META_FSM` 證「不會無限抖動」（safety）+「會停在不動點」（liveness）；PM-2 補上「停下來的那個不動點到底是不是更高的能力台階」——這是 liveness 無法表達、只能靠**跨 session 經驗測量**的進步性。
- **嚴守人類舵手**：plateau/regression/ceiling 三訊號**絕不自動觸發任何 spec/規則/鷹架變更**，只導向人類（提示「引導人類提供缺失工具、維持掌舵者高度」）。鷹架退役仍走 `rule_loader.set_maturity(reviewed_by=)` 人工 gate。
- **A/B 影子評估純離線**：WITH/WITHOUT 兩臂皆在本地隔離 context 跑既有代表性 fixture，無 HTTP、可重現（守 OPEN-10.6）。v1 rule-based（用既有 OQS，零 LLM 成本）；LLM 版留 v2 並更新成本 gate。

### 1.4 PM-3 組合級脆弱性（advisory，無新狀態）

`composition_blast_analyzer` 合 PM-1 的共享節點圖 + Phase L `spec_fragility_scorer` 的單一脆弱分數，對每個**被 ≥2 意圖共享的 spec 節點**算**組合爆炸半徑乘數**（= 單一脆弱分數 × 共享意圖數 × 跨意圖耦合度，凍結 `COMPOSITION_FRAGILITY_PROFILE_VERSION`）。輸出 ranked 熱圖**餵入既有介面**：`COMPOSITION_FSM` 排程器（高組合脆弱度的意圖排**序列**而非並行）、`steersman_renderer`（組合凍結前舵手即見跨意圖炸彈）。**只建議不自動改 spec、不阻塞 SCG**。

### 1.5 典型軌跡（含 Phase M 改善後的 self-verification 案例）

```
（組合協調層）BACKLOG_PRIORITIZED：人工 signoff 選定意圖 {折扣重構, 結帳優化}（共享 AC-014 折扣規則）
  → CPLAN_OBSERVE：intent_composer 偵測「兩意圖都改 AC-014」→ conflict_set={AC-014}
  → composition_blast_analyzer：AC-014 組合脆弱 top-1（單一脆弱 × 2 意圖共享 × 高耦合）→ 排程器建議序列化
  → CPLAN_NEGOTIATE（reneg=1）：要求兩意圖在 AC-014 調和
     ├─ 調和成功 → conflict_set=∅ → CPLAN_COMMIT（產序列排程）→ CPLAN_STABLE → 交艦隊 FLEET_FSM 並行其餘無衝突部分
     └─ 反覆否定（意圖 A 要 X、意圖 B 要 ¬X）reneg 達 MAX_RENEG=2 → CPLAN_ESCALATION
        → 人類裁決：哪個意圖讓步 / AC-014 是否需要統一上位規格（舵手在組合層做設計決策）

（進步性元層，跨 session）capability_trajectory_monitor：近 3 session OQS 平坦、churn 仍在發生
  → PLATEAU 訊號 → steersman：「自我演化停滯於高原，ChurnBounded 成立但無淨進步，請考慮注入新工具/典範或移除天花板鷹架」
  → scaffold_ceiling_detector：對仍 fire 的 SLV-009 做 A/B → WITHOUT 顯著優 → CEILING 訊號 → 建議人工 set_maturity 退役
  → 人類舵手決策（非系統自改）
```

**對比 L9/L10 奠基現況**：奠基後（a）多意圖組合靠紀律不矛盾、無形式化保證；（b）自我演化只證不抖動、不知是否真進步；（c）組合脆弱性只能跨意圖串級爆炸後才暴露。Phase M 讓系統**形式化證明組合一致收斂、測量並引導自我演化的真進步、事前預測組合脆弱性**——人類三處全部從「憑紀律/不知情/事後救火」升為「審組合界限/審進步證據/審組合風險」，精準對應提示「人類維持設計環境掌舵者高度」於**組合層與進步性層**。

---

## 2. 環境建構與記憶體管理策略（Phase M 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/composition-ledger.yaml`（新增，`file_lock` 保護）：跨 session 的組合協商事件帳本（intent 集合、共享節點、衝突集、reneg 次數、capability_at）。**落盤不常駐**，`COMPOSITION_FSM` 與收官審計按需 lazy 讀。
- `tools/fsm_runtime/formal/COMPOSITION_FSM.tla` + `COMPOSITION_FSM.cfg`（新增）：組合層形式化規格，比照 `FLEET_FSM.tla`/`META_FSM.tla` 自有 invariant/liveness/symmetry，**獨立命名空間不入單軌**。
- `build/reports/trajectory/TRAJECTORY-{date}.md`（新增）：進步性軌跡報告（淨能力曲線 + plateau/regression 判定 + 證據），餵 `steersman_renderer`。
- `build/reports/composition-fragility/COMP-FRAGILITY-{date}.md`（新增）：組合脆弱性熱圖（ranked top-K + 共享意圖數 + 排程建議）。
- `knowledge/composition-patterns/`（新增，對稱於 `failure-patterns`/`intent-patterns`/`adversarial-patterns`/`experiment-patterns`）：存 `COMP-*.yaml` 常見「跨意圖衝突 → 調和」模式，≥3 次同型 → 結晶 proposed 草案，**禁自動 verified**（比照 SPL/ADV/INT/EXP 治理）。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 新增形式化組合層 invariant（`COMPOSITION_FSM.tla`）：`TypeOK`、`CompositionConsistent`、`RenegotiationBounded`、`ConflictResolvedOrEscalated`、`StableIsFixpoint`、`EventuallyComposed`。
- PM-2 把 `capability_trajectory_monitor` / `scaffold_ceiling_detector`、PM-3 把 `composition_blast_analyzer`、PM-1 把 `intent_composer` / `composition_halt_monitor` 四鷹架本身納入 `scaffold_roi` 帳本——**並由 PM-2 自己的天花板偵測涵蓋自己**（新鷹架若日後成淨負天花板，會被自己證明的機制建議退役；元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.22.3，退役須 `set_maturity(reviewed_by=)` 人工 gate）。
- **PM-1 與 META_FSM 的接點**：組合層採納/退役共享規格調和規則，仍受 `META_FSM` 的 `ChurnBounded` 納管——`COMPOSITION_FSM` 是**新增的第四條形式化迴圈**，與 `META_FSM`（元迴圈）正交：前者管「同期多意圖橫向一致」，後者管「跨期規則集縱向不抖動」。

### 2.3 Prompt / 上下文與防衰減
- Phase M **不新增任何常駐 eager prompt**。組合協商詮釋、進步性評分、組合脆弱性評分皆由對應 runtime agent 在**隔離 context** 持有，結論才回主線。
- 組合協商前主線只留意圖摘要 + 共享節點清單；協商語料、A/B 影子評估 fixture 全落盤 lazy-load，不灌 context。
- 所有新產物（composition-ledger / trajectory report / composition-fragility heatmap / `COMPOSITION_FSM.tla`）皆 Markdown/YAML/TLA+ 純文字，無二進位、無外網依賴（守 OPEN-10.6 + 智慧體可讀性）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-097~104）

#### Pillar A — 組合級意圖自治形式化（PM-1；L10 完整奠基石）

**ACT-097 — Intent Composer + 跨意圖衝突偵測 + 組合帳本**
- **檔案**：`tools/fsm_runtime/intent_composer.py` + `build/state/composition-ledger.yaml`
- **設計**：純離線。輸入 `BACKLOG_PRIORITIZED` 選定的 ≥2 意圖（各自的 spec 觸及節點集，承 `intent_decomposer` 的 DAG 葉節點 + RTM 對應）→ 算**共享 spec 節點集** + **衝突集**（同節點上語義方向相反；用 `pattern_matcher` 正規化指紋比對）。提供 `compute_conflicts(intents)` 與 `compute_reneg(node_fingerprint)`。
- **驗收**：22 fixture（含 6 條人工合成跨意圖衝突序列〔3 可調和 + 3 不可調和〕+ 16 無衝突組合）；衝突偵出率 100%、無衝突誤判 0；不可調和序列 `compute_reneg ≥ MAX_RENEG`。

**ACT-098 — COMPOSITION_FSM 形式化 + composition_halt_monitor runtime 守門**
- **檔案**：`tools/fsm_runtime/formal/COMPOSITION_FSM.tla` + `.cfg` + `tools/fsm_runtime/composition_halt_monitor.py` + `tlc_runner.py` 擴充 + 離線可達性 BFS 測試
- **設計**：仿 `META_FSM.tla`/`FLEET_FSM.tla`。狀態變數 `{intents, conflict_set, reneg, cap}`，宣告 `CPLAN_OBSERVE/NEGOTIATE/COMMIT/STABLE/ESCALATION`。證 5 safety（`TypeOK`/`CompositionConsistent`/`RenegotiationBounded`/`ConflictResolvedOrEscalated`/`StableIsFixpoint`）+ 1 liveness（`EventuallyComposed`，需 `SF_vars`）。`composition_halt_monitor` 為 runtime assertion：每次 `CPLAN_NEGOTIATE` 前呼叫，違反 `RenegotiationBounded` 即拒絕並導 `CPLAN_ESCALATION`（category=structural，例外不外炸破 FSM）。
- **驗收**：`COMPOSITION_FSM` 經 `tlc_runner` = No error（5 invariant 全 PASS）+ 離線 BFS reachable=N/N；`composition_halt_monitor` 攔截 ACT-097 的 3 條不可調和序列；**單軌 `SDD_FSM` reachable 維持 42/42、`META_FSM`/`FLEET_FSM` 不回歸**（COMPOSITION_FSM 不污染既有證明）。

#### Pillar B — 自我演化進步性監測（PM-2；ChurnBounded 的對偶）

**ACT-099 — Capability Trajectory Monitor**
- **檔案**：`tools/fsm_runtime/capability_trajectory_monitor.py` + `build/reports/trajectory/`
- **設計**：rule-based v1（零 LLM 成本）。讀既有落盤訊號（OQS 歷史、escalation_rate、`meta-loop-ledger` churn、`scaffold_roi`、`arch_fitness`）算近 `SDD_TRAJECTORY_WINDOW`（預設 3 session）的淨能力斜率（凍結 `TRAJECTORY_PROFILE_VERSION`）。判 {RISING / PLATEAU（平坦但仍 churn）/ REGRESSION}。產 `TRAJECTORY-{date}.md` 餵 steersman。**純 advisory，絕不自動改任何東西**。
- **驗收**：18 fixture（6 上升 + 6 高原〔含 churn〕+ 6 下降）；PLATEAU/REGRESSION 命中率 ≥ 85%、RISING 誤報率 < 15%；改權重不 bump 版本 → 測試 fail（守自我放水禁令）。

**ACT-100 — Scaffold Ceiling Detector（淨負天花板 A/B 影子評估）**
- **檔案**：`tools/fsm_runtime/scaffold_ceiling_detector.py`（旁路 `scaffold_gc`，不改其 0-fire/surpassed 既有路徑）
- **設計**：對「仍 fire、未被 `capability_surpassed` 判退」的鷹架，取代表性 fixture 做 A/B 影子評估（隔離 context，WITH vs WITHOUT，比 OQS）。WITHOUT 顯著優（淨負，閾值 `SDD_CEILING_DELTA`）→ 輸出 CEILING 建議（**只建議，退役須人工 `set_maturity(reviewed_by=)`**）。v1 rule-based 用既有 OQS。
- **驗收**：16 fixture（8 淨正鷹架 + 8 人工注入的淨負天花板鷹架）；淨負偵出率 ≥ 80%、淨正誤報率 < 15%；驗證 detector **無法**自行退役任何鷹架（須走人工 gate，測試斷言無 set_maturity 自呼叫）。

#### Pillar C — 組合級脆弱性（PM-3；無新狀態）

**ACT-101 — Composition Blast Analyzer**
- **檔案**：`tools/fsm_runtime/composition_blast_analyzer.py`
- **設計**：合 ACT-097 共享節點圖 + Phase L `spec_fragility_scorer` 單一脆弱分數，算組合爆炸半徑乘數（= 單一脆弱 × 共享意圖數 × 跨意圖耦合度，凍結 `COMPOSITION_FRAGILITY_PROFILE_VERSION`）。純離線、可重現、advisory。
- **驗收**：16 fixture（標註已知組合脆弱/穩健共享節點）；組合脆弱 top-3 命中率 ≥ 85%、穩健誤列率 < 15%；改權重不 bump 版本 → 測試 fail。

**ACT-102 — 組合脆弱性 + 軌跡整合（無新狀態）**
- **檔案**：`composition_halt_monitor.py`（排程器吃 blast 建議：高組合脆弱 → 序列化）、`steersman_renderer.py`（渲染組合脆弱熱圖 top-K + 軌跡 plateau/regression 警示）
- **規則**：blast/trajectory 只「標記/建議」，**絕不自動改 spec、絕不阻塞 SCG、絕不自動退役鷹架或改排序**（advisory）。
- **驗收**：整合測試；熱圖與軌跡警示正確附掛 steersman digest；排程器在高組合脆弱時建議序列化但不改變 `CompositionConsistent` 證明。

#### 收官

**ACT-103 — Rule 9.25 治理落地**
- **檔案**：`governance/rules/R-9.25-composition-autonomy-progress-monitoring-phase-m.yaml` + `governance/RULES_INDEX.md` + CLAUDE.md §9.25 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 97→105 / rule 9.25→9.26）。
- 子規則 9.25.1~9.25.7 見 §4。

**ACT-104 — Phase M 形式化重證 + 全綠驗收**
- **形式化**：`COMPOSITION_FSM.tla` 5 invariant No error + 離線 BFS reachable=N/N（PM-1）；單軌 `SDD_FSM` 維持 42/42、`META_FSM`（13 distinct）、`FLEET_FSM` 全不回歸。
- **Chaos**：100 輪（新增 `COMPOSITION_CONFLICT_STORM`〔連續注入不可調和跨意圖衝突，驗 `RenegotiationBounded`〕+ `CEILING_FLAP`〔鷹架 A/B 淨值抖動，驗 detector 不自動退役〕兩故障型）bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：估 M-1 22+ M-2 18+16 + M-3 16 + 整合/chaos/形式化 ≈ 20 ≈ **+92**（844 → 約 936 passed）。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-097（Intent Composer + 衝突偵測）──► ACT-098（COMPOSITION_FSM + composition_halt_monitor + TLC/BFS）
ACT-099（Trajectory Monitor）──────────► ACT-102（軌跡警示整合 steersman）
ACT-100（Scaffold Ceiling Detector）──┘
ACT-101（Composition Blast Analyzer）──► ACT-102（排程器序列化 + steersman 熱圖）
                          三柱完成 ────► ACT-103（Rule 9.25 + ID 翻牌）─► ACT-104（COMPOSITION_FSM 形式化重證 + chaos + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L10 完整奠基（組合級）+ 自我演化進步性形式化**：

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L5 | Self-Driving（學習層 + 形式化停機） | A~G |
| L6 | Trustworthy Scaled（判官自審 + 增殖 + 雙形式化 + 艦隊並行） | I |
| L7 入口 | Adversarial & Self-Improving（對抗判官 + 能力代謝 + 規格自癒） | J |
| L8 入口 | Intent-Driven（單意圖分解 + 辯證消歧 + 因果接地） | K |
| L9 入口（離線切片） | Counterfactual Reality-Grounding（離線反事實 + 單一脆弱性預測） | L |
| L10 奠基 | Meta-Halting 形式化（單元迴圈 add↔retire 不震盪） | L |
| **L10 完整奠基（組合級）** | **Composition-Level Intent Autonomy（多意圖語義組合一致性形式化停機）** | **M（本份 PM-1）** |
| **自我演化進步性（ChurnBounded 對偶）** | **Progress Monitoring（高原偵測 + 淨負天花板鷹架退役引導）** | **M（本份 PM-2）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— 受 OPEN-10.6 約束，待 OPEN-M.7 放寬沙箱決策 | 未來 Phase N |
| L10 完整（horizon） | 全域組合最佳化 + 活體元迴圈（跨多軌意圖**最佳化**而非僅一致、且元迴圈在活體生產形式化停機） | 未來 Phase N |

> **誠實標定**：本份**不宣稱達成完整 L10**。完整 L10 需「跨多意圖的全域**最佳化**（不只一致，還要 ROI/資源全域最優）」+「元迴圈在活體生產的形式化停機」；本份只交付其**組合一致性形式化奠基石**（`COMPOSITION_FSM` 證一致收斂，尚非全域最優）與**進步性監測**。完整 L9/L10 列 horizon，前置阻礙明列於 §3.4 與 OPEN-M。

### 3.4 L9 完整 / L10 完整 Horizon（本份不實作，僅定錨）
- **L9 完整 — 活體現實實驗**：承 Phase L `EXPERIMENT_REPLAY`（離線反事實），延伸為對活體生產流量自主下 canary/shadow 統計驗證規格假設。**前置阻礙**：OPEN-10.6（本地唯讀 / 無 HTTP）+ 需真實生產整合。本份不觸碰（守 OPEN-L.5/OPEN-M.7）。
- **L10 完整 — 全域組合最佳化 + 活體元迴圈**：本份 `COMPOSITION_FSM` 只證「組合一致收斂」（衝突必解或升級），**尚未做「全域 ROI/資源最佳化排程」**（那是 NP-hard 最佳化層，須另立形式化界限證明「最佳化搜尋本身有界停機」）。承 `value_planner`（逐意圖 ROI）+ 本份 `intent_composer`（組合一致）往「組合最佳化」延伸，且該最佳化層也須形式化停機——本份的 `COMPOSITION_FSM` 已示範「組合協調層獨立形式化」的可複用路徑，為其鋪路。

---

## 4. 防護規則新增（CLAUDE.md §9.25 Phase M）

> 待 SCG-0 凍結並執行完成後正式寫入 CLAUDE.md §9.25（此處為草案，供 SCG-0 審視）。

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.25.1 組合協商有界（RenegotiationBounded） | ACT-097/098 | 任兩意圖在共享節點的「協商→否定→再協商」循環 ≤ `SDD_COMPOSITION_RENEG_MAX`（clamp[1,5]，預設 2）；超限→`CPLAN_ESCALATION`，絕不無限協商 livelock |
| 9.25.2 組合一致性（CompositionConsistent） | ACT-098 | 進入 `CPLAN_COMMIT` 的意圖集合在共享節點上兩兩不矛盾；帶未解衝突不得 commit（必導 NEGOTIATE/ESCALATION） |
| 9.25.3 COMPOSITION_FSM 獨立形式化 | ACT-098/104 | `COMPOSITION_FSM.tla` 自有命名空間，**不併入單軌 `SDD_FSM.tla`**；5 invariant + 離線 BFS reachable=N/N；單軌 `SDD_FSM` 維持 42/42、`META_FSM`/`FLEET_FSM` 不回歸 |
| 9.25.4 進步性監測 advisory + 不自我放水 | ACT-099 | `capability_trajectory_monitor` 只標記/建議；plateau/regression **絕不自動觸發典範轉移或任何 spec/規則變更**，只導人類舵手；分數凍結 `TRAJECTORY_PROFILE_VERSION`，調權重須 bump |
| 9.25.5 淨負天花板鷹架退役須人工 gate | ACT-100 | `scaffold_ceiling_detector` 只建議；退役仍在 fire 的鷹架**必經 `set_maturity(reviewed_by=)` 人工 gate**，detector 絕不自呼叫退役（守 Rule 9.20.5） |
| 9.25.6 組合脆弱性 advisory | ACT-101/102 | `composition_blast_analyzer` 只餵排程器/steersman 建議；**絕不自動改 spec、絕不阻塞 SCG**；分數凍結 `COMPOSITION_FRAGILITY_PROFILE_VERSION`，調權重須 bump |
| 9.25.7 進步性訊號不可降級為 auto-action | ACT-099/102 | plateau/regression/ceiling 三訊號一律 route 至人類舵手，**絕不自動 paradigm-shift / 自動退役 / 自動改排序**（守 Rule 8：人類維持設計環境掌舵者，非降級為編碼員） |

### ❌ Phase M 新增禁止行為（草案）
- `intent_composer` 自動 commit 跨意圖 schedule 繞過 `BACKLOG_PRIORITIZED` 人工 signoff（破 9.25.1 / Rule 8 / Rule 9.23.2）
- 把 `COMPOSITION_FSM` 狀態併入單軌 `SDD_FSM.tla`、或讓組合協商污染單軌/META/FLEET reachable 計數（破 9.25.3 / Rule 9.18.1）
- 跨意圖再協商無上限、或誤把 `CPLAN_ESCALATION` 列為不動點（破 9.25.1 / 9.25.2）
- `capability_trajectory_monitor` 的 plateau/regression 訊號自動觸發典範轉移或自動退役鷹架（破 9.25.4 / 9.25.7 / Rule 8）
- `scaffold_ceiling_detector` 自動退役仍在 fire 的鷹架而不經 `set_maturity(reviewed_by=)`（破 9.25.5 / Rule 9.20.5）
- `composition_blast_analyzer` 自動改 FRD/AC 或阻塞 SCG（破 9.25.6 / Rule 8）
- 調 trajectory / composition-fragility 權重不 bump 對應 `*_PROFILE_VERSION`（破 9.25.4/9.25.6，評分器自我放水）
- `COMPOSITION_FSM` 不過 `tlc_runner` + 離線 BFS 即宣稱組合層停機（破 9.25.3 / Rule 9.18）
- 為 L9 完整活體實驗私自開 HTTP 外聯而未經 OPEN-M.7 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：Spec 寫錯 → 測試永不過；並推到組合層與進步性層）

| 生命週期點 | L9/L10 奠基（Phase L）現況行為 | Phase M 強化後行為 |
|------------|----------------------|--------------------|
| **組合前·衝突** | 多意圖共享節點衝突只能等並行執行時 merge 撞車才暴露 | **`intent_composer` 在 `CPLAN_OBSERVE` 即偵測共享節點衝突**，未解不得進排程 |
| **組合前·脆弱** | 脆弱性只算單一 AC | **`composition_blast_analyzer` 算組合爆炸半徑乘數** → 高共享脆弱意圖建議序列化 → steersman 熱圖 |
| **組合協商** | 無此層；兩意圖規格永久互否會在 merge 層 livelock 燒 token | **`RenegotiationBounded`：協商 ≤ MAX_RENEG → 達頂即 `CPLAN_ESCALATION`** 導人工裁決，絕不無限協商 |
| **凍結前·結構/語義** | `INTENT_DECOMPOSITION` 偵環 + `SPEC_DEBATE` 辯證（K 既有，單意圖） | 同左（單意圖內），且組合層另有 `CompositionConsistent` 守橫向一致 |
| **生產後·補丁驗證** | `EXPERIMENT_REPLAY` 反事實重放（L 既有） | 同左 |
| **元層·自我演化收斂** | `META_FSM` 證 `ChurnBounded`（不抖動）（L 既有） | 同左，且 **`COMPOSITION_FSM` 證組合層 `EventuallyComposed`（橫向收斂）** |
| **元層·自我演化進步** | **只證不抖動，不知是否真進步**（ChurnBounded 的盲區） | **`capability_trajectory_monitor` 偵 plateau/regression** → 導人類注入新工具/典範；**`scaffold_ceiling_detector` A/B 偵淨負天花板鷹架** → 建議人工退役 |
| **引導人類** | 審補丁現實命中 + 審元迴圈收斂界限（L） | + 審**組合全域一致界限** + 審**框架是否真在自我精進**——舵手升至**組合層與進步性層** |
| **有界性** | 單軌 42/42 + 艦隊 `AllEventuallyDone` + 元迴圈 `EventuallyMetaStable` | + **組合層 `COMPOSITION_FSM` 形式化必達 `{CPLAN_STABLE, CPLAN_ESCALATION}`** + 單軌 42/42 不回歸 + 衝突/天花板雙故障型 chaos bounded 1.0 |
| **Token** | 補丁先離線驗證命中率，省（L） | **更省**（組合衝突凍結前先解、高脆弱意圖序列化避免並行串級爆炸返工；且進步性監測避免「有界地原地空轉燒 token 卻無淨進步」） |

✅ **模擬通過（含組合層與進步性層）**：對「Spec 寫錯導致測試永不過」案例，Phase M 在**組合前（衝突 + 脆弱）、組合協商（有界協商）、進步性元層（高原/天花板）** 三個新生命週期點皆能優雅停機並引導人類，每道閘形式化有界。**兩個最關鍵的躍遷**：
1. **組合層 livelock 被數學排除**——「兩意圖規格永久互相否定」這種**組合層的潛在無限迴圈**，被 `COMPOSITION_FSM` 的 `RenegotiationBounded` 在 MAX_RENEG 處強制升級人工，而非在 merge 層無限撞車燒 token。
2. **進步性盲區被補上**——`ChurnBounded` 只保證「不會無限抖動」，本份補上「停下來時到底有沒有變強」的測量，當系統陷入「有界但停滯」的高原時，**主動引導人類舵手注入缺失的工具/典範**——這正是提示「遇到死迴圈/停滯時引導人類提供 AI 缺失的工具或環境限制、確保人類維持設計環境掌舵者高度而非降級為編碼員」的最高體現。

人類在所有層級全部從「憑紀律/事後救火/不知情」升為「審組合界限/審進步證據/審組合風險」，維持「設計環境掌舵者」高度於最高層。

---

## 6. 執行順序與里程碑

```
M-M1 組合奠基：ACT-097 → ACT-098（COMPOSITION_FSM + TLC/BFS）  ── 先做，L10 完整奠基石、純離線、價值最高、不受 OPEN-10.6 約束
M-M2 進步性監測：ACT-099 + ACT-100（軌跡 + 天花板 A/B）── 緊接，補 ChurnBounded 對偶盲區
M-M3 組合脆弱性：ACT-101 → ACT-102（排程器序列化 + steersman 整合）── 中期，把單一脆弱升為組合脆弱
M-M4 收官：ACT-103（Rule 9.25 + ID 翻牌）→ ACT-104（COMPOSITION_FSM 形式化重證 + chaos + pytest 全綠）
```

**每個 M-Mx 完成即跑該層 pytest + 必要時 `tlc_runner`，絕不累積**（守 Rule 4 開發-編譯-測試循環）。
**M-M1 與既有動態工作流的接點**：PL-1 的 `META_FSM`（縱向：跨期規則不抖動）+ 本份 `COMPOSITION_FSM`（橫向：同期多意圖一致）共同把「具自我修正能力的動態工作流」（`SDD_SELF_EVOLUTION.md` + 學習層 + GC + 艦隊）補齊為**四條全形式化的閉環**（單軌 / 艦隊資源 / 縱向元迴圈 / 橫向組合）。

---

## 7. 待人工決策（OPEN-M）

> 🔴 本份為 DRAFT。以下 OPEN-M 須人工裁決後方可凍結 SCG-0、進入逐 ACT 執行（守 Rule 8 / Rule 9.23.2：planner 不自我裁決）。建議預設值已標於「建議」欄，可一次採納或逐項調整。

| ID | 議題 | 建議 |
|----|------|---------|
| OPEN-M.1 | 徵用 ACT-097~104 / Rule 9.25 是否確認（由 `id_registry next-act/next-rule` 取自前緣 97 / 9.25）？ | ✅ 建議確認；收官 ACT-103 翻牌 + `test_id_registry.py` 守門 |
| OPEN-M.2 | `COMPOSITION_FSM` 是否如建議**獨立命名空間**（不入單軌 `SDD_FSM.tla`），沿用 `FLEET_FSM`/`META_FSM` 模式？ | 建議獨立（守 Rule 9.18.1 單軌 42/42 不回歸） |
| OPEN-M.3 | `SDD_COMPOSITION_RENEG_MAX` 預設 2 / `SDD_TRAJECTORY_WINDOW` 預設 3 session / `SDD_CEILING_DELTA` 閾值是否合適？ | 預設 2 / 3 / 執行時校準；env 可調 |
| OPEN-M.4 | `scaffold_ceiling_detector` A/B 影子評估限 rule-based（用既有 OQS，零成本）抑或允許 LLM A/B 推理？ | rule-based v1（守 G~L 慣例）；LLM 留 v2 並更新成本 gate（比照 OPEN-J.1/K.2/L.4） |
| OPEN-M.5 | `capability_trajectory_monitor` 的 plateau 判定窗口與斜率閾值（幾個 session 平坦算高原）？ | 建議 3 session 平坦 + 仍有 churn = plateau；env 可調，執行時校準 |
| OPEN-M.6 | `composition_blast_analyzer` 分數是否影響 `value_planner`/`COMPOSITION_FSM` 排序（高組合脆弱=高優先修或強制序列化），抑或純 advisory 顯示 + 排程器建議？ | 建議排程器**建議**序列化（不強制改 ROI 排序，守 planner 不自我裁決）；v2 再評是否納入排程硬約束（比照 OPEN-L.6） |
| OPEN-M.7 | 是否啟動 OPEN-10.6 沙箱外聯放寬評估，以推進 **L9 完整（活體 canary/shadow）**？ | 暫不；維持本地唯讀，延續 OPEN-L.5 立場，活體版待專案有真實生產整合需求再評 |

---

**藍圖等級目標**：L9 入口（離線切片）+ L10 元停機奠基 → **L10 完整奠基（組合級）+ 自我演化進步性形式化 — Composition-Level Intent Autonomy & Self-Evolution Progress Monitoring**
**前置 SCG**：✅ SCG-0（需求凍結）**PASSED**（2026-06-03 使用者 signoff、OPEN-M 全採建議預設值、範疇確認無矛盾）。
**形式化承諾**：`COMPOSITION_FSM` 5 invariant（含 `CompositionConsistent`/`RenegotiationBounded`/`EventuallyComposed`）No error + 離線 BFS reachable=N/N；單軌 `SDD_FSM` 維持 42/42、`META_FSM`（13 distinct）、`FLEET_FSM` 全不回歸；chaos（含 `COMPOSITION_CONFLICT_STORM`/`CEILING_FLAP`）bounded_ratio=1.0。
**與動態工作流的關係**：本藍圖即「具自我修正能力的動態工作流深度優化」之續推——它把使用者既有的自我演化迴圈（`SDD_SELF_EVOLUTION.md` + 學習層 + GC + 艦隊 + 元迴圈）從「三條形式化閉環（單軌/艦隊/縱向元迴圈）」補上**第四條橫向組合閉環的形式化收斂**，並補上「框架是否真在自我精進」的進步性測量與「淨負天花板鷹架」的主動退役引導——人類舵手高度推到組合層與進步性層的最高點。
