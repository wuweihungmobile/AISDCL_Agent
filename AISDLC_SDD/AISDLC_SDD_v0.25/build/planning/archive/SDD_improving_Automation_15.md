# SDD_improving_Automation_15 — Phase O 藍圖（DRAFT）

**主題**：自我調參的對抗式有界元最佳化（Self-Tuning Adversarial Bounded **Meta-Optimization**）— 把「最佳化器自身的目標權重」從人工凍結常數，升級為**可學習、但受既有 `META_FSM` ChurnBounded 封頂 + 反 Goodhart 對抗分離把關**的自我演化迴圈
**目標等級**：L10 完整（組合一致 + 組合最優，Phase M/N 已達）→ **L10 完整之「離線活體元迴圈」切片**（系統不只能找全域最優排程，更能**自我學習「何謂最優」的目標函式本身**，且形式化證明這條「調參迴圈」有界停機、對抗式防止自評放水）
**建立日期**：2026-06-03
**前置基線**：Phase N 完整（ACT-105~110 / R-9.26，pytest 912 綠 / 7 skipped；五軌 TLC 全 No error：`SDD_FSM` 308 distinct / 42 reachable、`META_FSM` 13、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 29 passed 含 `OPT_SEARCH_STORM` bounded_ratio=1.0）
**OPEN-M.7 承接**：✅ 使用者 2026-06-03 已拍板**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary/shadow）續列 horizon；**Phase O 與 Phase N 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（元最佳化）**。
**狀態**：✅ **EXECUTED 2026-06-03（L10 完整之離線活體元迴圈切片達成）** — 使用者「直接執行（採 OPEN-O 全預設）」signoff，ACT-111~116 全部完成。**驗收：pytest 951 passed / 7 skipped（Phase N 912 → +39 Phase O：test_phase_o 36 + test_chaos +2 + test_id_registry +1）；opt-in 完整 TLC 4 passed（五軌 SDD/META/FLEET/COMPOSITION/OPTIMIZATION 全 No error 不回歸）；chaos 100 輪 bounded_ratio=1.0（新增 `OBJECTIVE_TUNE_FLAP` 故障型，Goodhart 提案零漏放 + obj-profile churn 觸頂 MFSM_ESCALATION）；不增第六形式化軌（obj-profile 重用既有 META_FSM ChurnBounded）；單軌 SDD_FSM 零 OBJ_ 洩漏。** 原 DRAFT 紀錄保留如下。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase N 自陳的兩個 horizon 之一「元最佳化形式化（最佳化器學習調參納入 `META_FSM` ChurnBounded）」續推。

> 🔴 **編號徵用告示**（承 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml) `next_free`）：
> 本藍圖徵用 **ACT-111~116 與 Rule 9.27**（取自登記簿前緣 act=111 / rule=9.27，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **DRAFT 期間不得翻牌**——僅在獲人工 signoff 並執行至收官（ACT-115）時，才由 `id_registry` 翻牌（act 111→117 / rule 9.27→9.28）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase O？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性驗證）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~N 的紀律，正確的第一步是**對賬而非設計**——這套系統已走過 Phase A~N、是自陳「L10 完整（組合一致 + 組合最優 + NP-hard 搜尋形式化停機）」的成熟框架，盲目套提示的前沿清單只會重造輪子（提示清單在 Phase K~N 已逐項對賬為 100% 落地）。我的任務是先**形式化回答「圖靈完備 vs 保證停機」這個被提示放在標題卻從未被任何前一份藍圖正面證明的核心命題**，再用三漏洞視角往 Phase N 之上挖出 grep 可證零實作的**新**結構性缺口。

【零、先正面回答提示標題的核心命題：這個自動化閉環「圖靈完備」嗎？它又如何「保證停機」？這兩件事不矛盾嗎？】
這是整個提示最深、卻被歷份藍圖視為已解而略過的問題。我要把它講透，因為 Phase O 的設計正建立在這個論證的最後一塊拼圖上。

- **圖靈完備性來自哪裡？** 不是來自 FSM。`SDD_FSM`/`META_FSM`/`FLEET_FSM`/`COMPOSITION_FSM`/`OPTIMIZATION_FSM` 全是**有限狀態機**——它們**故意不是**圖靈完備的，這正是它們能被 TLC 窮舉證明停機的前提。真正的圖靈完備性來自**嵌在迴圈裡的 LLM 生成器 + 無界的 `docs/` 檔案系統（紙帶）**：LLM 能生成任意程式、`docs/` 能存任意狀態、FSM 能依生成結果條件轉移並回讀——這三者合起來，計算能力等價於一台圖靈機（能表達任意可計算函式）。
- **那為什麼能保證停機？** 停機問題（Halting Problem）的鐵律是：**沒有任何單一圖靈完備基質能對自身保證停機**。所以這套系統的架構天才之處，是把「圖靈完備的表達力」與「可證停機的控制」**拆到兩個不同基質**：
  - 基質 A（不可判定、圖靈完備）：LLM 生成器。「它這次會不會收斂到通過 SCG 的規格／實作？」——這是不可判定的。
  - 基質 B（有限狀態、可判定、可證停機）：FSM 監督者 + retry budget（SCG 3 / PR 5 / RTM 2）+ context budget（95% 停機）+ 五軌 TLC 形式化。它把基質 A 的「也許無限」**包進一個有界預算**：retry 觸頂 → `ESCALATION` → 人工。
  - **結論**：系統在**能力**上圖靈完備（能算任意可計算的開發任務），在**控制**上可證有界停機（任何一條迴圈都被 TLC 證明必抵 terminal 或人工閘）。兩者不矛盾，因為它們不在同一基質——這正是「把不可判定的 LLM 包進可判定的預算監督者」的工程實現。**✅ 圖靈完備自動化閉環 = 已驗證成立**，且這正是提示「停機問題與防護」要的最高答案：不是讓 AI 自己證明自己會停（不可能），而是用一個外部有限狀態監督者強制把「也許無限」轉成「有界重試 → 交棒人類」。
- **這個論證對 Phase O 的意義（關鍵）**：五軌 FSM 證的是**五條已知迴圈**會停。但其中四個評分器（`composition_objective_scorer` 的 `OBJECTIVE_PROFILE_VERSION`、`ambiguity_scorer` 的 `SCORER_VERSION`、`spec_fragility_scorer` 的 `FRAGILITY_PROFILE_VERSION`、`adversarial_synthesizer` 的 `ADVERSARIAL_PROFILE_VERSION`、`capability_trajectory_monitor` 的 `TRAJECTORY_PROFILE_VERSION`）的**權重是人工凍結的常數**——也就是說，系統的「價值觀／偏好函式」目前是**外生的、不在任何迴圈裡**。一旦我們想讓系統**自我學習這些權重**（這是 L10 完整最後一塊「活體元迴圈」），就**憑空多出一條新迴圈：調參迴圈**。而這條迴圈是**所有自我修改裡最危險的一條**，因為它修改的是「評判一切好壞的尺規本身」。如果這條迴圈沒有被納入基質 B 的有界監督，圖靈完備性會反噬——系統會用無界的 LLM 表達力去無限調整自己的尺規，且更糟：**用尺規給自己打高分（Goodhart 崩塌）**。所以 Phase O 的全部價值，就是把這條新迴圈也拉進「可證停機 + 對抗式防自評」的基質 B。

【一、提示前沿清單 × 既有落地對賬（承 Phase K~N）】
- 生成與評估分離（GAN 啟發）→ ✅ `sdd-evaluator`（H，獨立 worktree）+ `adversarial_synthesizer`（J）+ `spec_debate`（K）+ `counterfactual_replay`（L，補丁 vs 歷史現實判官）。**但這四層分離全部用在「規格/實作/補丁」上，從未用在「評分器權重」上**——評分器至今是凍結常數，沒有「生成新權重 vs 評估新權重」的分離。← Phase O 的 PO-2 缺口正在這裡。
- 主觀標準量化 → ✅ `AmbiguityScorer`/`OQS`/`ADVERSARIAL_PROFILE_VERSION`/`FRAGILITY_PROFILE_VERSION`/`OBJECTIVE_PROFILE_VERSION`。**但這些「量化標準」本身的權重是人工調的，系統不會自己校準它們**。← PO-1。
- 評估器實體操作（Playwright/沙箱）→ ✅ `sandbox_runner` + `evaluate_hermetic`（`--network none`/`--cap-drop ALL`）+ `R-SELF-STRIDE`。
- 動態演進框架、移除鷹架 → ✅ `SCAFFOLD_GC`（H）+ 能力感知 graduation（J）+ `scaffold_ceiling_detector`（M，退淨負天花板）+ `META_FSM` 證 add↔retire 不抖動（L）。**這條最關鍵**：提示明說「評估框架能隨底層模型能力提升而**動態演進**」——目前框架能演進「規則集」（學/退 SLV 規則），卻不能演進「評分權重」。Phase O 把「動態演進」從規則集推到**評分器的價值權重**。
- 單一真實來源、漸進式揭露 → ✅ `RULES_INDEX.md` + `rule_loader.load_for_state()` + `ID_REGISTRY.yaml`。
- 運行時可觀測性（LogQL/PromQL）→ ✅ `observability_query`（H，本地唯讀）。
- 不變量 + GC → ✅ Rule 9 全鏈 + `spec_monitor` + `SCAFFOLD_GC` + 五軌 `.tla` invariant。
- Planner→G/E 合約談判 → ✅ 微觀 `TEST_CONTRACT_NEGOTIATED`（H）+ 宏觀單意圖 `INTENT_DECOMPOSITION`（K）+ 組合一致 `COMPOSITION_FSM`（M）+ 組合最優 `OPTIMIZATION_FSM`（N）。
- 停機問題 + 人類掌舵者 → ✅ 五軌形式化（單軌/艦隊/元迴圈/組合/最優）+ `steersman_renderer` + `spec_patch_proposer` + `spec_localizer` + `EXPERIMENT_REPLAY`。

結論：**提示前沿清單已 100% 對應落地，五條已知迴圈皆形式化停機。** 但對賬同時暴露一條共同主軸：**框架能自我演化「規則集」與「排程」，卻不能自我演化「評判一切的評分權重」——這些權重是外生凍結常數，是系統價值觀裡唯一還沒進閉環的部分。** 而這恰恰是 Phase N §6 horizon #2 自陳的待辦「元最佳化形式化」。

【二、用提示三個指定漏洞視角，逐一往 Phase N 之上挖】

(A) 狀態轉換——「生成器 ↔ 評估器合約談判」這個分層，在規格/實作/排程都完整，唯獨**在「評分器權重」這個元層級是完全缺席的**。
框架的 `composition_objective_scorer.py`（N）成本函式 = `batch_count × BATCH_W + latency × LATENCY_W`，其中 `BATCH_W=1.0`、`LATENCY_W=0.1`、`OBJECTIVE_PROFILE_VERSION="v1.0"` 全是**人工硬編的常數**。要改？必須人工 bump 版本（Rule 9.26.4）。這在「人工偶爾微調」時是對的紀律，但它意味著：**系統永遠不會從「哪些排程實際上跑得好（OQS 高、escalation 少、軌跡上升）」這些已累積的落盤現實裡，學到「我的目標權重設錯了」**。提示要的「生成與評估分離」若推到這個元層級，型態是：要有個東西**生成候選權重 profile**（Generator），再有個**獨立、tuner 碰不到的現實代理**去**評估這個 profile 到底好不好**（Evaluator）。grep `objective_tuner|weight_learning|profile_adopt|meta_optimiz|tune.*objective|learned_weight` 在 `tools/` **零命中**。→ **PO-1**（最關鍵；L10 完整「離線活體元迴圈」奠基石，純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「調參迴圈」是憑空多出的第六條迴圈，**它若不被封頂，就是 Goodhart 式無限自我放水的完美溫床**。
這是 Phase O 最深的反諷，也是它與前幾 Phase 的本質差異：前面五軌證的都是「做事的迴圈」會停；Phase O 要納管的是「**改變評判標準的迴圈**」。讓系統調自己的目標函式，最大的風險不是「不停機」（雖然也會），而是**評估器墮落成生成器**——tuner 學到「把 `BATCH_W` 設成 0，每個排程成本看起來都超低」，於是它用自己的尺規給自己打滿分。這正是提示反覆強調的「**避免 AI 對自身產出盲目自信**」的最尖銳形態。防線必須是雙重的：(b1) **對抗式分離**——候選 profile 的勝負，必須由一個 **tuner 結構性看不到、且內容雜湊凍結的 held-out 現實代理語料**（拿框架自身歷史上「已知真實結果」的排程當試金石，承 `counterfactual_replay`/`EXPERIMENT_REPLAY` 基座）來判，**絕不准 tuner 用 objective scorer 自己的分數當證據**；(b2) **有界停機**——profile 的「採納→退役→再採納」必須納入**既有 `META_FSM` 的 `ChurnBounded`**（churn ≤ `SDD_META_CHURN_MAX`），且再採納須挾 `GraduationRatchet` 的 capability-delta（這裡 capability-delta = held-out 勝率 tier 嚴格提升）。grep `held_out|anti_goodhart|objective_replay|tuning_ledger|obj_profile.*fingerprint` **零命中**。→ **PO-2**（反 Goodhart 對抗分離 oracle）+ **PO-1 的形式化納管**。

【三、停機問題視角的紅線覆查——本份核心正衝著它來，故有界性要加倍嚴謹】
本份的反諷與 Phase L/M 同構但更尖銳：核心交付（PO-1）**就是新增一條「修改評判標準」的迴圈**，所以它的有界性與防自評要做到滴水不漏：
- **不新增第六條形式化軌（關鍵設計決策 + Anthropic「大膽移除不需要的鷹架」的正面示範）**：調參迴圈在本質上**不是一條新迴圈**——它就是 `META_FSM` 已經形式化的那條「跨期學習↔退役元迴圈」，只是被學/退的**製品**從「SLV 規則」換成「objective-profile 權重」。`meta_halt_monitor.guard_readopt(fingerprint, capability_level)` 的簽章本來就是**對任意指紋泛型**的。所以正確做法是**重用既有 `META_FSM`**，把 objective-profile 註冊為一個新的指紋命名空間（`obj-profile:*`），由**同一條 `ChurnBounded`/`GraduationRatchet`/`EventuallyMetaStable` 證明涵蓋**，而非再開一個 `OBJOPT_FSM`。這既守了停機紅線，又示範了框架成熟到「不是每個新能力都要新開一軌」——這恰是提示 Anthropic「動態演進、大膽移除冗餘鷹架」的精神用在框架自身。（另開獨立軌列為 OPEN-O.2 供人工裁決，但建議重用。）
- **PO-2 為對抗式硬閘，非 advisory**：held-out oracle 是 tuner 與 capability-delta 之間的**唯一合法橋樑**——profile 沒在凍結 held-out 語料上贏過 incumbent ≥ margin，就拿不到 capability tier，`guard_readopt` 直接 `GraduationRatchetViolation` 拒絕。oracle 語料 content-hashed、tuner 程式路徑禁止讀取（測試斷言隔離）。
- **PROPOSED-only，人類掌舵者高度推到最高層——「價值觀層」**：tuner 只產 `proposed` profile，`OBJECTIVE_PROFILE_VERSION` 的 bump **必經人工 signoff**（守 Rule 8 / 9.26.4）。`steersman_renderer` 渲染「新舊權重的價值取捨 diff + held-out 證據」，讓人類**不必讀程式碼就能掌舵系統的目標函式**。這是「人類維持設計環境掌舵者、而非降級為編碼員」的終極體現：人類從「審規格/審排程」升到**「審系統用什麼價值觀評判一切」**。

【四、上下文衰減（Context Degradation）視角覆查】
- PO-1/PO-2 的調參語料、held-out oracle 語料、A/B 評估全在**隔離邏輯/落盤**進行，主線只在收到 `proposed` profile 時讀「權重 diff + 勝率摘要」。調參帳本落 `build/state/objective-tuning-ledger.yaml`（`file_lock` 保護），完全比照 `meta-loop-ledger`/`composition-ledger` 既有「獨立命名空間協調層」作法，**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- held-out oracle 語料重用既有 `EXPERIMENT_REPLAY` 的重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物（tuning ledger / objective-tuning proposal report / held-out 勝率表）皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性）：把「系統的目標函式」「調參的每一次提案與其 held-out 證據」「新舊價值觀 diff」全部落地為 **Markdown/YAML 可推理產物**（objective-tuning-ledger、proposal report、held-out 勝率表），不藏在 prompt 或硬編常數裡——**讓「系統的價值觀」本身成為 AI 與人類都可直接推理、可審計的單一真實來源**。
- Anthropic（對抗 / 動態演進）：把「生成與評估分離、避免對自身產出盲目自信」推到**最危險的元層級——評分器權重**：tuner 生成、held-out 現實代理對抗式評估，**嚴禁自評**；並把「動態演進框架」從「演進規則集」（L）推到「演進評判標準」（O），同時用「不增第六軌、重用 META_FSM」示範「大膽移除冗餘鷹架」。你敢讓系統自己調整「何謂最優」，就得能形式化證明這條調參迴圈會停、且不會自己給自己打高分。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~N 落地元件**（對賬見上 thinking 一節），五條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM` / 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**（能力圖靈完備、控制可證有界，兩者拆在 LLM 與 FSM 兩基質）。Phase O 的價值在用提示三漏洞視角挖出 Phase N 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**框架能自我演化「規則集」與「排程」，卻不能自我演化「評判一切的評分權重」；這些權重是外生凍結常數，是系統價值觀裡唯一還沒進閉環、也是最危險（Goodhart）的一塊**。

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PO-1** | **目標函式是人工凍結常數，系統不會從已累積的現實學「我的權重設錯了」**——`composition_objective_scorer`（N）的 `BATCH_W/LATENCY_W/OBJECTIVE_PROFILE_VERSION` 全硬編；五個評分器皆然。提示「主觀標準量化 + 動態演進框架」要的「系統隨能力提升自我校準評判標準」在元層級缺席。Phase N §6 自陳此為待辦 horizon。 | `objective_tuner\|weight_learning\|profile_adopt\|meta_optimiz\|learned_weight` **零命中** |
| **PO-2** | **「生成-評估分離」從未用在評分器權重上——讓系統調自己的尺規卻沒有反 Goodhart 防線**——`adversarial_synthesizer`/`counterfactual_replay`（J/L）只對抗「規格/補丁」，沒有「tuner 碰不到的凍結 held-out 現實代理」去判「新權重是否真的更好」。系統若自調權重，會墮落成「用自己的尺規給自己打高分」。 | `held_out\|anti_goodhart\|objective_replay\|tuning_ledger` **零命中** |
| **PO-3** | **若要自調目標函式，必須有一條可證停機的調參迴圈 + 人類掌舵「價值觀層」的介面**——目前 `META_FSM`（L）只納管「SLV 規則」的 add↔retire，未涵蓋「objective-profile 權重」的採納/退役；`steersman_renderer` 未渲染「新舊價值觀 diff」。 | `obj.*profile.*fingerprint\|objective.*ledger\|render.*objective` **零命中** |

**三缺口的共同主軸**：Phase A~N 讓人類站在「審規格/審排程/審補丁/審元迴圈收斂」的高度，但**框架評判一切的「價值觀」（評分權重）仍是憑人工直覺凍結的外生常數，從未進閉環、也最容易被自評汙染**。Phase O 把人類抬到最高層——**審「系統用什麼價值觀評判一切」、以及「系統自我校準價值觀的提案是否在 tuner 碰不到的現實試金石上真的更好」**——這正是 L10 完整最後一塊「離線活體元迴圈」，也精準補上提示在「狀態轉換（元層級的生成-評估合約）」「停機問題（調參迴圈 + 防 Goodhart）」「動態演進（演進評判標準而非僅規則集）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase O 增量）

Phase O 對狀態機的改動刻意**對單軌與既有四軌零表面積**：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42）；**且刻意不新增第六條形式化軌**——調參迴圈本質上就是 `META_FSM` 已證明的那條「跨期學習↔退役元迴圈」，只是被學/退的製品從 SLV 規則換成 objective-profile 權重。**重用既有 `META_FSM`** 不僅省一軌，更是 Anthropic「大膽移除不需要的鷹架」用在框架自身的正面示範。

### 1.1 新增元件總覽（無新 FSM 狀態）

| 元件 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `objective_tuner`（候選權重 profile 生成器） | runtime（落 `objective-tuning-ledger.yaml`） | 生成器（advisory） | 跨 session 收官 / `MEMORY_CONSOLIDATION` 旁路 | 產 `proposed` profile + held-out 證據 → steersman | 否 |
| `objective_replay_oracle`（反 Goodhart held-out 評估器） | runtime（重用 `EXPERIMENT_REPLAY` 重放基座） | 評估器（硬閘） | tuner 提案後 | 勝率 tier（capability-delta 的唯一合法來源） | 否（但決定 guard 准駁） |
| objective-profile 採納/退役 | **既有 `META_FSM`**（`obj-profile:*` 指紋命名空間） | 元迴圈（沿用 `MFSM_*`） | `meta_halt_monitor.record_rule_add/retire` | `ChurnBounded`/`GraduationRatchet` 准駁；觸頂 → `MFSM_ESCALATION` | — |

> **選位說明**：
> - `objective_tuner` 與 `objective_replay_oracle` 是**一對 GAN**（生成器 / 評估器），但**兩者皆 advisory、皆不自動 commit**——真正改 `OBJECTIVE_PROFILE_VERSION` 的權力只在人工 signoff（守 Rule 8）。
> - objective-profile 的「採納就是被人工 bump 接受、退役就是被新 profile 取代」這條 add↔retire 元迴圈，**完全納入既有 `META_FSM`**：`fingerprint = "obj-profile:" + hash(weights)`，`capability_level = held-out 勝率 tier`。由**同一條已證明的 `ChurnBounded`/`GraduationRatchet`/`EventuallyMetaStable`** 涵蓋，**五軌 TLC 不回歸、不新增第六軌**。

### 1.2 元最佳化迴圈（重用 META_FSM 的有界停機契約）

```
（離線、跨 session）
objective_tuner.propose()
  讀 {已累積排程的真實結果：OQS、escalation_rate、trajectory 斜率、實際 batch 數}
  → 在 BOUNDED 候選空間內（權重格點 ≤ SDD_OBJ_TUNE_BUDGET，clamp[8,256]，預設 64）搜出候選 profile P'
  → objective_replay_oracle.evaluate(P')：在「tuner 不可見、content-hashed 凍結」的 held-out 排程語料上，
       比 P' 與 incumbent 的真實結果勝率（重用 counterfactual_replay 基座，≤ SDD_REPLAY_MAX_CASES）
     ├─ P' 勝率 − incumbent 勝率 ≥ SDD_OBJ_WIN_MARGIN → 取得「capability tier++」→ 產 proposed profile + 證據 → steersman → 人工 signoff
     │     └─ 人工接受 → meta_halt_monitor.record_rule_add("obj-profile:hash(P')", cap=tier)
     │           ├─ guard 放行（churn < MAX 且 tier 嚴增）→ bump OBJECTIVE_PROFILE_VERSION（人工）
     │           └─ guard 拒絕（churn 觸頂 / 無 capability-delta）→ MFSM_ESCALATION（人工裁決）
     └─ P' 未達 margin（含「P' 只在 objective scorer 自評上贏、在 held-out 真實上輸」的 Goodhart 案例）
           → 拒絕提案（不取得 tier）→ 純記錄；連續 N 次拒絕 → 導人類「目標維度可能不足，請注入新維度」
```

- **核心有界性（重用既有證明）**：objective-profile 的 add↔retire churn ≤ `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`），**絕不無限調參抖動**；再採納退役過的 profile 必須挾 held-out 勝率 tier 嚴增（既有 `GraduationRatchet`），**杜絕「調了又退、退了又調」白燒 token**。觸頂 → `MFSM_ESCALATION`（既有人工閘）。
- **反 Goodhart 硬閘（PO-2）**：`capability_level`（tier）的**唯一合法來源是 held-out oracle 勝率**——`objective_tuner` 與 `composition_objective_scorer` 的自評分數**結構性禁止**充當 capability-delta（測試斷言 oracle 語料路徑與 tuner 隔離、tuner 無法讀寫 oracle 語料）。這把「生成與評估分離」釘死在元層級。
- **搜尋有界（PO-1）**：候選權重在離散格點上 bounded 搜尋，節點 ≤ `SDD_OBJ_TUNE_BUDGET`，**絕不指數爆炸**（比照 `OPTIMIZATION_FSM` 的 `SearchBounded` 精神，但因納入 `META_FSM` 故不另立軌）。

### 1.3 典型軌跡（含 Phase O 改善後的 self-verification 案例）

```
（跨 session 收官）objective_tuner：近 5 session 真實 OQS 顯示「高價值意圖常被排到末批、實測返工率高」
  → 推論 incumbent LATENCY_W=0.1 過低 → 候選 P'（LATENCY_W=0.35）
  → objective_replay_oracle：在 50 筆凍結 held-out 歷史排程上重放 → P' 真實勝率 0.72 vs incumbent 0.58（Δ=0.14 ≥ margin 0.10）
  → 取得 capability tier++ → proposed profile + 勝率表 → steersman 渲染「LATENCY_W 0.1→0.35 的價值取捨 + 14% 勝率證據」
  → 人工 signoff 接受 → record_rule_add("obj-profile:9f2c…", cap=tier) → guard 放行 → 人工 bump OBJECTIVE_PROFILE_VERSION v1.0→v1.1

（Goodhart 攻擊案例）objective_tuner（受擾）：候選 P''（BATCH_W=0，使一切成本看似極低）
  → objective_replay_oracle：held-out 重放 → P'' 把所有意圖塞一批 → 真實衝突爆炸 → 真實勝率 0.20（遠輸 incumbent）
  → Δ<0 → 不取得 tier → guard_readopt 拒絕（GraduationRatchetViolation）→ 提案丟棄，絕不採納
  → 若 tuner 反覆送 Goodhart 變體 → churn++ 至 SDD_META_CHURN_MAX → MFSM_ESCALATION
  → steersman：「調參在 held-out 上反覆失敗、疑似自評放水，請人工檢視目標維度或接受 incumbent」
```

**對比 Phase N 現況**：（a）目標權重憑人工直覺凍結、不會自我校準；（b）若硬要自調，沒有任何防線阻止「用自己的尺規給自己打高分」。Phase O 讓系統**能從真實結果自我提案校準目標函式、且該提案必須在 tuner 碰不到的現實試金石上真的更好、且整條調參迴圈被既有 `META_FSM` 證明有界停機**——人類從「審排程」升為**「審系統的價值觀演化」**，精準對應提示「人類維持設計環境掌舵者高度」於**最高的價值觀層**。

---

## 2. 環境建構與記憶體管理策略（Phase O 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/objective-tuning-ledger.yaml`（新增，`file_lock` 保護）：跨 session 調參帳本（候選 profile hash、held-out 勝率、tier、churn、人工 signoff 狀態）。**落盤不常駐**，按需 lazy 讀；比照 `meta-loop-ledger`/`composition-ledger`。
- `knowledge/held-out-corpus/`（新增，content-hashed 凍結）：反 Goodhart 現實代理語料（歷史排程 + 已知真實結果），**tuner 程式路徑禁止讀寫**（隔離斷言）；重用 `EXPERIMENT_REPLAY` 重放基座。
- `build/reports/objective-tuning/OBJ-TUNE-{date}.md`（新增）：調參提案報告（新舊權重 diff + held-out 勝率表 + 證據），餵 `steersman_renderer`，advisory。
- 不新增任何形式化軌——objective-profile 元迴圈納入既有 `formal/META_FSM.tla`，僅在 `meta_ledger` 增 `obj-profile:*` 指紋命名空間（不改 `.tla` 狀態宇宙，故五軌證明不回歸）。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 五 safety + liveness 涵蓋 objective-profile 元迴圈（`ChurnBounded`/`GraduationRatchet`/`ReadoptGated`/`StableIsFixpoint`/`EventuallyMetaStable`），**不新增 `.tla` 狀態**；新增測試斷言「`obj-profile:*` 指紋與 SLV 規則指紋共用同一 churn 預算、且皆過 `meta_halt_monitor`」。
- `objective_tuner`/`objective_replay_oracle` 兩鷹架本身納入 `scaffold_roi` 帳本，並由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **凍結版本守門**：`OBJECTIVE_PROFILE_VERSION` 仍由人工 bump；tuner 只能**提案** profile，**不能自寫常數**（測試斷言 tuner 無法改 `composition_objective_scorer` 原始碼）。

### 2.3 Prompt / 上下文與防衰減
- Phase O **不新增任何常駐 eager prompt**。調參搜尋、held-out 重放、A/B 評估皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 `proposed` profile 時讀「權重 diff + 勝率摘要」。
- 所有新產物（tuning ledger / held-out corpus / proposal report）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-111~116）

#### Pillar A — 自我調參生成器 + 反 Goodhart 對抗評估（PO-1 + PO-2；L10 完整離線活體元迴圈奠基石）

**ACT-111 — Objective Tuner（bounded 候選權重生成器）**
- **檔案**：`tools/fsm_runtime/objective_tuner.py` + `build/state/objective-tuning-ledger.yaml`
- **設計**：純離線、deterministic。讀已累積落盤現實（OQS 歷史、escalation_rate、trajectory 斜率、實測 batch 數）→ 在離散權重格點上 bounded 搜尋（節點 ≤ `SDD_OBJ_TUNE_BUDGET` clamp[8,256] 預設 64）產候選 profile。**只提案、絕不自動 commit、絕不自寫常數**（守 Rule 8 / 9.26.4）。
- **驗收**：18 fixture（含 6 條已知「incumbent 明顯次優」序列〔tuner 應提出更優 P'〕+ 6 條「incumbent 已最優」〔tuner 應不提案或提案被 oracle 駁回〕+ 6 條 Goodhart 誘餌〔自評高、真實差〕）；搜尋節點 ≤ budget；deterministic 可重現。

**ACT-112 — Objective Replay Oracle（反 Goodhart held-out 評估器）**
- **檔案**：`tools/fsm_runtime/objective_replay_oracle.py` + `knowledge/held-out-corpus/`
- **設計**：重用 `counterfactual_replay`/`EXPERIMENT_REPLAY` 重放基座。在 content-hashed 凍結 held-out 語料（≤ `SDD_REPLAY_MAX_CASES`）上比 P' vs incumbent 的**真實結果勝率**，回 `tier`（capability-delta 唯一合法來源）。**結構性隔離**：oracle 語料路徑與 `objective_tuner` 互斥，tuner 無讀寫權。
- **驗收**：16 fixture（8 真優 profile〔勝率 ≥ margin〕+ 8 Goodhart 假優〔自評高、held-out 輸〕）；真優偵出率 ≥ 85%、Goodhart 假優攔截率 100%（**零漏放**，因這是安全紅線）；斷言 tuner 程式無法觸及 oracle 語料。

#### Pillar B — 納入既有 META_FSM（PO-3 之有界停機；不增第六軌）

**ACT-113 — objective-profile 元迴圈納管 + META_FSM 重證（無新狀態）**
- **檔案**：`tools/fsm_runtime/meta_halt/meta_ledger.py`（增 `obj-profile:*` 指紋命名空間）+ `meta_halt_monitor` 接 objective-profile 採納/退役路徑 + `objective_tuner` 接 `record_rule_add/retire`
- **設計**：`fingerprint = "obj-profile:" + hash(weights)`、`capability_level = held-out tier`。採納/退役**必經 `guard_readopt`**（既有 `ChurnBounded`/`GraduationRatchet`）。**不改 `formal/META_FSM.tla` 狀態宇宙**，僅新增測試證明 objective-profile 與 SLV 規則共用同一 churn 預算、同一 `meta_halt_monitor`。
- **驗收**：`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸）+ 離線 BFS reachable 不變；新增 test 斷言「Goodhart 變體反覆提案 → churn 觸頂 → `MFSM_ESCALATION`」「無 capability-delta re-adopt → `GraduationRatchetViolation`」；**五軌 TLC 全不回歸（SDD 42 / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）**。

#### Pillar C — 人類掌舵「價值觀層」介面（PO-3 之 steersman；無新狀態）

**ACT-114 — Steersman 價值觀 diff 渲染 + PROPOSED 人工 gate**
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_objective_tuning_proposal`）
- **設計**：渲染「新舊權重 diff + held-out 勝率表 + 證據摘要 + churn/tier 狀態」，**advisory**；`OBJECTIVE_PROFILE_VERSION` bump **必經人工 signoff**，渲染器絕不自動 bump。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff」；斷言渲染器無法自呼叫 bump 或 `record_rule_add`。

#### 收官

**ACT-115 — Rule 9.27 治理落地 + ID 翻牌**
- **檔案**：`governance/rules/R-9.27-meta-optimization-self-tuning-phase-o.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#17 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 111→117 / rule 9.27→9.28）+ `test_id_registry.py` 前緣斷言 + Phase O ownership 測試。
- 子規則 9.27.1~9.27.5 見 §4。

**ACT-116 — Phase O 形式化重證 + chaos + 全綠驗收**
- **形式化**：`META_FSM` 維持 No error（13 distinct）+ objective-profile 納管測試全綠；**五軌 TLC 全 No error 不回歸**（不增第六軌）。
- **Chaos**：100 輪新增 `OBJECTIVE_TUNE_FLAP` 故障型（連續注入 Goodhart 假優提案 → 驗 `ChurnBounded` → `MFSM_ESCALATION` 有界、且 oracle 零漏放）bounded_ratio=1.0、avg tokens < 25K×80%。
- **pytest**：估 +30（ACT-111 18 + ACT-112 16 + ACT-113 ~12 + ACT-114/整合/chaos ~10，扣重疊）≈ **912 → 約 942 passed**。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-111（Objective Tuner）──┐
                            ├─► ACT-113（納入 META_FSM + 重證）──► ACT-114（steersman 價值觀 diff + 人工 gate）
ACT-112（Replay Oracle）────┘                                              │
                                          三柱完成 ──► ACT-115（R-9.27 + ID 翻牌）──► ACT-116（META_FSM 重證 + OBJECTIVE_TUNE_FLAP chaos + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L10 完整之「離線活體元迴圈」切片**：

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L5 | Self-Driving（學習層 + 形式化停機） | A~G |
| L6 | Trustworthy Scaled（判官自審 + 增殖 + 雙形式化 + 艦隊並行） | I |
| L7 入口 | Adversarial & Self-Improving（對抗判官 + 能力代謝 + 規格自癒） | J |
| L8 入口 | Intent-Driven（單意圖分解 + 辯證消歧 + 因果接地） | K |
| L9 入口（離線切片） | Counterfactual Reality-Grounding（離線反事實 + 單一脆弱性） | L |
| L10 奠基 | Meta-Halting 形式化（add↔retire 不震盪） | L |
| L10 完整奠基（組合一致） | Composition-Level Intent Autonomy | M |
| L10 完整（組合最優） | Global Composition Optimization + NP-hard 搜尋形式化停機 | N |
| **L10 完整 · 離線活體元迴圈切片** | **Meta-Optimization：自我學習目標函式 + 反 Goodhart 對抗分離 + 調參迴圈納入 META_FSM ChurnBounded** | **O（本份 PO-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-M.7 已裁決暫不放寬 OPEN-10.6 | 未來 Phase（待真實生產整合 + OPEN 改判） |
| L10 完整（horizon） | **活體**元最佳化（在真實生產流量上線上調參 + 全評分器自校準）+ 全評分器一體化自演化 | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版**。完整 L10 之「活體元迴圈」需在真實生產流量上線上調參（受 OPEN-10.6 約束，OPEN-M.7 已裁決暫不放寬）。本份交付其**離線等價切片**：用框架自身歷史的 held-out 現實代理語料當試金石，**在本地完成「自我校準目標函式」的等價驗證價值**，且**只示範 objective scorer 一個評分器**（推廣到 ambiguity/fragility/adversarial/trajectory 五器一體化自校準列為 horizon）。完整活體版與五器一體化列 horizon。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-M.7 已裁決暫不放寬 OPEN-10.6，續列 horizon，待真實生產整合需求再評。
- **活體元最佳化**：本份離線（held-out 現實代理）；活體版需在生產流量上線上調參，受 OPEN-10.6 約束。
- **全評分器一體化自校準**：本份只做 `composition_objective_scorer`；推廣到全部五個評分器（共用同一「tuner + held-out oracle + META_FSM 納管」骨架）為自然延伸。

---

## 4. 防護規則新增（CLAUDE.md §9.27 Phase O — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.27.1 調參有界（ObjectiveTuningBounded） | ACT-111/113 | `objective_tuner` 候選搜尋節點 ≤ `SDD_OBJ_TUNE_BUDGET`（clamp[8,256] 預設 64）；objective-profile 採納/退役 churn ≤ `SDD_META_CHURN_MAX`（重用既有 `META_FSM.ChurnBounded`）；超限→`MFSM_ESCALATION`，絕不無限調參抖動或指數搜尋 |
| 9.27.2 反 Goodhart 對抗分離（Anti-Goodhart Separation） | ACT-112 | 候選 profile 的 capability-delta tier **唯一合法來源是 tuner 不可見、content-hashed 凍結的 held-out 現實代理勝率**；`objective_tuner` 與 `composition_objective_scorer` 自評分數**結構性禁止**充當 capability-delta；tuner 程式路徑禁止讀寫 oracle 語料（測試斷言隔離） |
| 9.27.3 調參 PROPOSED + 不自我裁決 | ACT-111/114 | `objective_tuner` 只產 `proposed` profile，`OBJECTIVE_PROFILE_VERSION` bump **必經人工 signoff**（守 Rule 8 / 9.26.4）；tuner/steersman **絕不自動 commit 改 scorer 權重、絕不自寫常數** |
| 9.27.4 元最佳化納入既有 META_FSM（不增第六軌） | ACT-113/116 | objective-profile 採納/退役走 `meta_halt_monitor` 的 `obj-profile:*` 指紋命名空間，受既有 `ChurnBounded`/`GraduationRatchet` 納管；**不改 `META_FSM.tla` 狀態宇宙、不新增第六軌**；五軌 TLC 全不回歸（除非 OPEN-O.2 人工另裁獨立軌） |
| 9.27.5 最優性/進步性誠實 | ACT-112/113 | held-out 勝率 tier 為 `capability_level` 唯一合法來源；不得用 objective scorer 自身分數充當 capability-delta（防自評）；提案報告須誠實附 held-out 勝率與樣本數，不得謊報 |

### ❌ Phase O 新增禁止行為（草案）
- `objective_tuner` 自動 commit / 自寫 `composition_objective_scorer` 權重常數、繞過人工 `OBJECTIVE_PROFILE_VERSION` bump（破 9.27.3 / Rule 8 / Rule 9.26.4）
- 用 objective scorer 自評分數或 tuner 自報數充當 capability-delta tier（破 9.27.2 / 9.27.5，Goodhart 自評放水）
- `objective_tuner` 讀寫 / 影響 `knowledge/held-out-corpus/` oracle 語料（破 9.27.2 對抗分離）
- objective-profile 採納/退役繞過 `meta_halt_monitor`、或無 capability-delta re-adopt 退役過的 profile（破 9.27.1 / 9.27.4，重蹈 Rule 9.24.1/9.24.2）
- 候選權重搜尋無上限指數爆炸（超 `SDD_OBJ_TUNE_BUDGET` 仍展開）（破 9.27.1）
- 把 objective-profile 元迴圈另併入單軌 `SDD_FSM.tla` 或污染五軌 reachable（破 9.27.4 / Rule 9.18.1）
- 為活體元最佳化私自開 HTTP 外聯而未經 OPEN-M.7/後續 OPEN 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：兩個極端案例）

### 5.1 經典案例：Spec 寫錯 → 測試永不過（承前 Phase 不回歸）
| 生命週期點 | 行為 |
|------------|------|
| 凍結前·邏輯 | `spec-logical-validator`（SLV-001~011）在 SCG-0/3 前攔物理不可行/不可測 AC |
| 開發中·重試 | retry budget（SCG 3 / PR 5 / RTM 2）+ `trajectory_predictor` 2 信號預測切換 / 3 信號早停 |
| 對抗·補丁 | `adversarial_synthesizer` + `spec_patch_proposer`（proposed）+ `counterfactual_replay` 離線命中 |
| 停機 | 觸頂 → `ESCALATION` / `MFSM_ESCALATION` → `steersman_renderer` 導人工，**絕不無限重試燒 token** |
✅ 不回歸：五軌形式化 + retry/context budget 保證有界。

### 5.2 Phase O 專屬極端案例：Objective Tuner 自評放水（Goodhart 崩塌）
**案例**：tuner 受擾，學到「`BATCH_W=0` 讓一切排程成本看似極低」，企圖用自己的尺規給自己打滿分、無限自我「改進」。

| 生命週期點 | Phase N 現況（無此迴圈） | Phase O 強化後行為 |
|------------|----------------------|--------------------|
| **調參·生成** | 無自調能力（權重凍結） | `objective_tuner` 產候選 P''（`BATCH_W=0`），**只提案** |
| **調參·對抗評估** | — | `objective_replay_oracle` 在 tuner 碰不到的凍結 held-out 語料重放 P'' → 全塞一批 → 真實衝突爆炸 → 真實勝率 0.20 ≪ incumbent → **Δ<0、零漏放** |
| **取得 capability tier** | — | 拒絕（無 capability-delta）→ `guard_readopt` `GraduationRatchetViolation` → 提案丟棄，**絕不採納** |
| **反覆攻擊** | — | tuner 反覆送 Goodhart 變體 → churn++ 至 `SDD_META_CHURN_MAX` → **`MFSM_ESCALATION`**（既有元迴圈閘） |
| **引導人類** | — | steersman：「調參在 held-out 反覆失敗、疑似自評放水；請審目標維度或接受 incumbent」——人類掌舵**價值觀層** |
| **有界性** | — | 重用 `META_FSM` `ChurnBounded` + `EventuallyMetaStable` 數學保證必停；`OBJECTIVE_TUNE_FLAP` chaos 100 輪 bounded_ratio=1.0 |
| **Token** | — | Goodhart 提案在離線 held-out 即被駁，**絕不進主線燒 token**；省 |

✅ **模擬通過（兩案例）**。**Phase O 最關鍵的躍遷**：把「讓系統自己調整評判一切的尺規」這個**最危險的自我修改**，用**生成-評估對抗分離（tuner 生成、tuner 碰不到的 held-out 現實對抗式評估）+ 既有 META_FSM 有界停機**雙保險封死——系統能自我校準目標函式變強，**卻在結構上不可能用自己的尺規給自己打高分、也不可能無限調參燒 token**。這正是提示「避免 AI 對自身產出盲目自信」「遇到死迴圈/停滯引導人類提供缺失工具、人類維持設計環境掌舵者高度」在**最高的價值觀元層級**的終極體現。

---

## 6. 執行順序與里程碑

```
O-M1 對抗 GAN 對：ACT-111（tuner）+ ACT-112（held-out oracle）── 先做，L10 離線活體元迴圈奠基石、純離線、不受 OPEN-10.6 約束；oracle 的 Goodhart 攔截為安全紅線
O-M2 有界納管：ACT-113（納入既有 META_FSM + 重證不增軌）── 緊接，把調參迴圈釘進既有停機證明
O-M3 掌舵介面：ACT-114（steersman 價值觀 diff + 人工 bump gate）── 中期，人類掌舵價值觀層
O-M4 收官：ACT-115（R-9.27 + ID 翻牌）→ ACT-116（META_FSM 重證 + OBJECTIVE_TUNE_FLAP chaos + pytest 全綠）
```

**每個 O-Mx 完成即跑該層 pytest + 必要時 `tlc_runner`，絕不累積**（守 Rule 4 開發-編譯-測試循環）。
**與既有動態工作流的接點**：本份把使用者既有的五條形式化閉環（單軌 / 艦隊資源 / 縱向元迴圈 / 橫向組合一致 / 組合最優）中的**縱向元迴圈（`META_FSM`）從「納管 SLV 規則的學/退」擴充為「同時納管 objective-profile 權重的學/退」**——不新增閉環、不新增軌，而是**讓既有元迴圈涵蓋系統價值觀本身的自我演化**。這是「具自我修正能力的動態工作流」最後一塊：連「評判一切的尺規」都進了可證停機 + 反自評的閉環。

---

## 7. 待人工決策（OPEN-O）

> 🔴 本份為 DRAFT。以下 OPEN-O 須人工裁決後方可凍結 SCG-0、進入逐 ACT 執行（守 Rule 8 / Rule 9.23.2：planner 不自我裁決）。建議預設值已標於「建議」欄，可一次採納或逐項調整。

| ID | 議題 | 建議 |
|----|------|---------|
| OPEN-O.1 | 徵用 ACT-111~116 / Rule 9.27 是否確認（由 `id_registry next-act/next-rule` 取自前緣 111 / 9.27）？ | ✅ 建議確認；收官 ACT-115 翻牌 + `test_id_registry.py` 守門 |
| OPEN-O.2 | objective-profile 元迴圈**重用既有 `META_FSM`**（不增第六軌，建議）抑或**另開 `OBJOPT_FSM` 獨立軌**（比照 N 的 OPTIMIZATION_FSM）？ | **建議重用 `META_FSM`**（調參本質就是「學↔退」元迴圈、製品換成權重；不增軌＝Anthropic「移除冗餘鷹架」示範，且五軌證明不回歸）。若人工偏好對稱性可選獨立軌，但須額外證 5 safety+liveness |
| OPEN-O.3 | `SDD_OBJ_TUNE_BUDGET` 預設 64 / `SDD_OBJ_WIN_MARGIN` 預設 0.10 / 重用 `SDD_REPLAY_MAX_CASES` 預設 50 是否合適？ | 預設 64 / 0.10 / 50；env 可調，執行時校準 |
| OPEN-O.4 | `objective_tuner` v1 限 rule-based 格點搜尋（零 LLM）抑或允許 LLM 啟發式提案？ | rule-based v1（守 G~N 慣例，零成本、deterministic）；LLM 啟發式留 v2 並更新成本 gate（比照 OPEN-N.3） |
| OPEN-O.5 | 本份只自校準 `composition_objective_scorer` 一個評分器（示範），抑或一次推廣到全部五個評分器？ | 建議**先單一示範**（降風險、骨架可複用）；五器一體化列 horizon，待單一驗證穩定再推廣 |
| OPEN-O.6 | held-out 現實代理語料來源——重用 `EXPERIMENT_REPLAY` 既有歷史排程語料（建議）抑或另建標註語料？ | 建議重用既有歷史排程 + 已知真實結果（零新依賴、可重現）；content-hash 凍結 + tuner 隔離 |
| OPEN-O.7 | 是否啟動 OPEN-10.6 沙箱外聯放寬評估，以推進**活體元最佳化 / L9 完整**？ | 暫不；維持本地唯讀，延續 OPEN-M.7 立場，活體版待專案有真實生產整合需求再評 |

---

**藍圖等級目標**：L10 完整（組合一致 + 組合最優，M/N 已達）→ **L10 完整之離線活體元迴圈切片 — Self-Tuning Adversarial Bounded Meta-Optimization**
**前置 SCG**：✅ SCG-0 PASSED（2026-06-03 使用者「直接執行」signoff、OPEN-O 全採建議預設、OPEN-O.7=暫不放寬沙箱承 OPEN-M.7）。
**形式化承諾**：`META_FSM` 維持 No error（13 distinct）+ objective-profile 納管測試全綠；**五軌 TLC 全 No error 不回歸（不增第六軌）**；chaos（含 `OBJECTIVE_TUNE_FLAP`）bounded_ratio=1.0、oracle Goodhart 零漏放。
**與動態工作流的關係**：本藍圖即「具自我修正能力的動態工作流深度優化」之續推——它把使用者既有的自我演化迴圈，從「能演進規則集與排程」推進到**「連評判一切的目標函式都能自我校準，且該自我校準受對抗式防自評 + 既有元迴圈有界停機雙重封頂」**——人類舵手高度推到**價值觀層**的最高點，同時正面驗證了「圖靈完備自動化閉環」之所以能與「保證停機」並存，是因為把不可判定的 LLM 生成器包進可判定的有限狀態監督者，而 Phase O 把這個監督者的涵蓋範圍擴張到了系統的價值觀本身。
