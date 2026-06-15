# SDD_improving_Automation_20 — Phase T 藍圖（DRAFT）

**主題**：轉換算子文法的**自我擴充（meta⁵）**——把 Phase S 只能「在**固定轉換算子 `TRANSFORMS`**（6 條硬編：rate/window/depth/delta/ratio/count）上自我發明 VOCAB 外的新原始特徵『字』」的能力，推進到「系統能**自我發明一個 `TRANSFORMS` 裡根本沒有的全新轉換/聚合算子語意**（算子生成文法 meta⁵）」。並正面納管「算子外生成」憑空長出的、Phase S（固定 TRANSFORMS / 固定 OPS）不存在而 Phase T 才出現的**新危害類別：(i) 算子可計算性危害（一個算子是『可執行語意』而非僅標籤——自我發明的算子可能非全函式 / 無界計算步數 / 隱含遞迴或迴圈，這是「圖靈完備 vs 保證停機」直接打到算子本身的最深層停機問題）；(ii) 算子無界生成爆炸（TRANSFORMS/OPS 外不再有硬編上界）；(iii) 算子自我發明 Goodhart（發明一個『計算自己核可訊號』的自指算子）**。
**目標等級**：L10 完整 · 離線活體 meta⁴ 迴圈「生成文法詞彙自我擴充 + 批次退役聯動」切片（Phase S 已達：在固定 TRANSFORMS 上自我發明 VOCAB 外詞彙 + 批次退役）→ **L10 完整 · 離線活體 meta⁵ 迴圈「轉換算子文法自我擴充」切片**（系統不只能在**有限 TRANSFORMS/OPS**上自我發明特徵詞彙，更能在**可證有界、可證可計算（全函式 + 有界步數）、反自利、人類掌舵本體論**的前提下，**自我發明 TRANSFORMS/OPS 外的全新轉換/聚合算子語意**，重構它「用什麼運算去量它在乎什麼」的價值計算本體論）。
**建立日期**：2026-06-04
**前置基線**：Phase S 完整（ACT-135~140 / R-9.31，pytest 1206 passed / 4 skipped / 34 deselected〔chaos〕/ 14 subtests；五軌 TLC 全 No error：`SDD_FSM` 42 reachable / 831 TLC distinct（42=FSM 狀態節點 reachable、831=含計數器變數的 TLC distinct states，兩者皆正確指同一軌）、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `VOCAB_GENESIS_GOODHART_FLAP`+`BATCH_SWAP_THRASH_FLAP`，詞彙自我發明 Goodhart 零漏放、批次旋轉有界停機）
**OPEN-10.6 承接**：續承 OPEN-S.x / OPEN-R.x / OPEN-Q.x / OPEN-O.7 / OPEN-M.7 / OPEN-P.7——**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary/shadow）與**活體 meta⁵ 元迴圈**續列 horizon；**Phase T 與 Phase N/O/P/Q/R/S 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（轉換算子文法自我擴充）**。Phase S §3.4 明示「轉換算子文法的自我擴充（meta⁵）」為其自陳 horizon #3，故本份維持離線等價切片，活體版列 horizon（OPEN-T.x 承前）。**自我發明評估器（meta-oracle 自演化）續列最高 horizon**——它自指地破壞所有 Phase 賴以成立的「對抗分離地基」，採納它須先有更強的對抗分離不可繞過性證明（見 §0 thinking 三末、§3.4）。
**狀態**：✅ **EXECUTED 2026-06-04（L10 完整 · 離線活體 meta⁵ 迴圈「轉換算子文法自我擴充」切片達成）** — ACT-141~146 全部完成。**驗收：pytest 1206→1252 passed / 4 skipped / 34 deselected〔chaos〕/ 14 subtests（+46，零回歸）；五軌 TLC 全 No error（`META_FSM` 維持 13 distinct 不回歸、新增 `OperatorGenesisBounded` + `OperatorComputabilityBounded` INVARIANT PASS；SDD 42 reachable / 831 TLC distinct / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12 不回歸）；chaos 100 輪 bounded_ratio=1.0（新增 `OPERATOR_GENESIS_GOODHART_FLAP` 自指算子+算子外噪音算子零漏放 + `OPERATOR_COMPUTABILITY_FLAP` → `OperatorComputabilityExceeded`〔非全函式/超步數〕有界）；不增第六形式化軌（operator-genesis 重用既有 META_FSM）；單軌 SDD_FSM 零 operator-genesis 洩漏；12 凍結 OPR 算子必要性語料零漏放。** `ID_REGISTRY` 已翻牌 act 141→147 / rule 9.32→9.33。OPEN-T.x 承 OPEN-S.x/R.x/Q.x/O.7/M.7/P.7 暫不放寬 OPEN-10.6 沙箱；自我發明評估器（meta-oracle 自演化）續列最高 horizon（須先有對抗分離不可繞過性證明）。原 DRAFT 紀錄保留如下。徵用 ACT-141~146 / Rule 9.32（取自 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml)，單調取號）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase S §3.4 自陳 horizon「轉換算子文法的自我擴充（meta⁵：自我發明新聚合/轉換算子語意，涉及更深的無界生成 + **算子可計算性**，需另證有界 + 反自利）」續推。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 141 / rule 9.32）：
> 本藍圖徵用 **ACT-141~146 與 Rule 9.32**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **DRAFT 期間不得翻牌**——僅在獲人工 signoff 並執行至收官（ACT-145）時，才由 `id_registry` 翻牌（act 141→147 / rule 9.32→9.33）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase T？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~S 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~S、是自陳「L10 完整 + 離線活體 meta⁴ 迴圈（生成文法詞彙自我擴充 + 批次退役聯動）」的成熟框架。盲目重述提示前沿清單只會重造輪子（Phase K~S 已逐項對賬為 100% 落地）。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase T 是否仍成立；(2) 誠實判斷「轉換算子文法的自我擴充」到底是**Phase S 的換皮**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase T 把監督者的涵蓋面從「在固定 TRANSFORMS/OPS 上自我發明詞彙」擴到「自我發明 TRANSFORMS/OPS 外的算子本身」，且首次面對『被發明物本身就是一段可執行計算』的停機問題】
Phase O~S 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase S 的貢獻是把「VOCAB 外的原始特徵『字』的自我發明（有界詞彙生成文法 + feature-grounded 必要性 + 詞彙自指 probe 守門）+ 批次退役」拉進基質 B。

但 Phase S 誠實標定了它的詞彙生成文法**鎖在一個固定的轉換算子集 `TRANSFORMS`**（`vocabulary_genesis.TRANSFORMS` = rate/window/depth/delta/ratio/count，6 條硬編；維度聚合算子 `dimension_semantics_synthesizer.OPS` = mean/max/min/sum，4 條硬編），系統只能在「這 6+4 個算子」之上**選用**——它**換不出選單上沒有的新『運算』**。Phase S 把這件事列為 horizon（§3.4 行 270）：**轉換算子文法的自我擴充（meta⁵，TRANSFORMS/OPS 外、發明新算子語意，涉及更深的無界生成 + 算子可計算性，需另證有界 + 反自利）**。這裡藏著一個**被 Phase S 一句帶過、實際上是質變而非量變、且比前所有 Phase 都更貼近停機問題核心的命題**：

**前所有 meta 層（Q 增維 / R 維度語意發明 / S 詞彙發明）的被發明物，本質上都是『描述子 / 標籤 / 對既有原始信號的引用』——它們是「資料」。**Phase S 的 `transform` 只是個字串標籤（`features.get("secret.window")` 取一個**事先算好**的特徵值），真正的「計算」永遠是那 4 條硬編 OPS（mean/max/…）或那 6 條硬編 TRANSFORMS 之一，全是**人類寫死、保證全函式、保證 O(n) 停機**的運算。**Phase T 的被發明物第一次是『可執行語意 / 一段計算 / 一個函式』——它是「程式」。**讓系統**自我發明一個 TRANSFORMS/OPS 外的新算子**，等於讓系統**自己寫一小段會被嵌進評估迴圈反覆執行的計算邏輯**。這**直接把圖靈完備的停機問題打到被發明物本身**：
- 一個自我發明的算子若允許任意計算，就可能**非全函式**（某些輸入無定義 / 拋例外）、**無界計算步數**（隱含遞迴 / 迴圈 / 對輸入規模指數展開）、甚至**不停機**。Phase S 的有界性只管「詞彙基數 stock + 批次速率」——它對「**被採納的算子每次被呼叫時到底會不會停、會燒多少步**」**結構性盲目**（因為 Phase S 的算子全是人類寫死的全函式，根本沒有這個問題）。
- 這正是「圖靈完備 vs 保證停機」這條 Phase O~S 反覆援引的核心命題，**第一次反噬到框架自我擴充的產物本身**：你敢讓系統發明自己的算子，就**必須證明每一個被發明的算子仍是可判定地停機的**——否則「把不可判定 LLM 包進可判定監督者」的整套地基，會因為「監督者開始執行 LLM 發明的、可能不可判定的算子」而被從內部蛀空。

這正是 Phase T 必須納管的、Phase S 尚未碰、且**比前所有 Phase 都更逼近停機問題本質**的新東西。

【一、誠實判斷：轉換算子文法自我擴充是「Phase S 換皮」還是「有真缺口」？——用 grep 接地】
我先確認框架目前的算子**鎖死在固定集**（grep `^TRANSFORMS` on `vocabulary_genesis.py` 實測 6 條硬編 tuple、`^OPS` on `dimension_semantics_synthesizer.py` 實測 4 條硬編 tuple，無任何「算子生成 / 算子發明 / 算子文法 / 算子可計算性」路徑）。再 grep 三組關鍵字證明零實作：
| 關鍵字 | grep 範圍 | 命中 |
|--------|-----------|------|
| `operator.*genesis\|GenesisOperator\|invent.*operator\|OperatorGenesis\|expand.*ops` | `tools/` | **零** |
| `operator.*comput\|OperatorComputability\|step.*budget\|op.*cost\|total.*function.*guard` | `tools/` | **零** |
| `PRIMITIVES\|COMBINATORS\|operator.*grammar\|op_expr` | `tools/` | **零** |

→ **轉換算子文法的「自我擴充」目前零實作；系統被鎖在固定 6+4 個算子內。** 真正的價值不在於「再加一個 operator grammar」（那是 Phase S 換皮），而在於：**算子外生成會打開三個 Phase S 結構性攔不住的新攻擊面，其一是前所有 Phase 都不存在的最深層停機危害**：
- **算子可計算性危害（meta⁵ 的靈魂，前所未有）**：自我發明的算子是**可執行計算**——若無界，它可非全函式 / 無界步數 / 隱含遞迴。Phase S 的有界性（詞彙 stock / 批次速率）對「算子每次執行的可計算性與步數」**完全盲目**。← 這是 Phase T 的 **PT-1 的核心**（真缺口，且是停機問題本身）。
- **算子無界生成爆炸 + 算子自我發明 Goodhart**：算子生成**沒有 6+4 條硬編上界**；且系統可發明一個「**算子本身就計算 proposer/oracle/自評內部信號**」的自指算子，讓自我發明的算子「看起來必要」實際只是自利。Phase S 的 feature-grounded oracle 評的是**現場發明詞彙在既有 OPS/TRANSFORMS 算出的特徵向量上的增量覆蓋**——它對「一個**算子外、用一個語料事先沒見過的新運算去聚合**的算子到底必不必要、是不是自指自利」**完全盲目**。← **PT-1 的另兩面**。
- **算子外生成的計算本體論掌舵真空**：`steersman` 只渲染「固定 OPS/TRANSFORMS 上自我發明的詞彙」與「批次退役」；無人渲染「系統**現場發明了一個選單外的新算子、它的算子生成文法來源（憑什麼有界）、它憑什麼可計算（全函式 + 有界步數證據）、它憑什麼必要且非自指**」。人類掌舵在「算子外計算本體論發明層（meta⁵）」缺席。← **PT-3**。

【二、用提示三個指定漏洞視角，逐一往 Phase S 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在 meta⁵ 層缺「算子外發明的可有界、**可計算（全函式+有界步數）**、可反自利、feature-grounded 驗證」這一層。
Phase S 的 `vocabulary_genesis`（生成，固定 TRANSFORMS 詞彙）↔ `dimension_necessity_oracle.evaluate_genesis_feature`（評估，feature-grounded）是一對 meta⁴ GAN，但**它只評在固定算子上算出的特徵**。當系統**現場發明一個選單外的新算子**，**(1) 誰保證這條算子生成不會無界爆炸？(2) 誰保證這個算子每次執行都會停（全函式 + 有界步數）？(3) 誰判「這個現場發明的算子到底必不必要、是不是自指自利」？** 目前無人。提示要的「生成-評估分離 + 主觀標準量化」推到 meta⁵ 層，型態是：**(1)** 生成必須被一條**有界算子生成文法**封住——「TRANSFORMS/OPS 外」不等於「無界」，而是「在一個**有限原始算子 PRIMITIVES × 有限組合算子 COMBINATORS**的可枚舉生成空間裡生成新算子」，節點 <= `SDD_DIM_OP_BUDGET`；**(2)**（最關鍵、前所未有）算子文法必須**結構性保證每個生成的算子都是全函式 + 有界計算步數**——`PRIMITIVES` 皆為 total list-reduction（mean/max/min/sum/range/median/spread/last…，對任何輸入有定義、O(n) 一遍掃描、零遞迴零迴圈）、`COMBINATORS` 皆為 total 後變換（identity/abs/neg/clip01/sq…）或有界元數二元組合（diff/ratio_safe/max2…），算子 = **有界深度（<= 2）的運算式樹**，故每個算子的計算步數 `cost()` 結構性 <= 常數 <= `SDD_DIM_OP_STEP_MAX`——**這是「算子可計算性需另證有界」的正面兌現：把「可執行計算」刻意設計成 sub-Turing（全函式 + 有界步數）的有限代數，讓每個被發明的算子可證停機，而整個閉環仍靠 LLM+紙帶維持圖靈完備**；**(3)** 評估升級為**對算子（不靠算子名、靠在固定參照 probe 上的真實計算結果）的 feature-grounded 算子必要性 oracle**——量「以這個新算子在固定 probe 上聚合，是否帶來既有 OPS/TRANSFORMS 全算子都拿不到的增量覆蓋 ∧ 非冗餘」；外加一道**算子級自指守門**（反自利：算子的 primitive/combinator/probe 引用保留自指信號 → 結構性拒絕，零漏放）。→ **PT-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「算子可計算性」是一條前所有 Phase 都不存在、直接源自「被發明物是程式而非資料」的最深層停機缺口。
這是 Phase T 最深、也最切題（提示明列「停機問題與防護」）的缺口。Phase Q/R/S 的被發明物都是「資料」（維度名 / 探針 / 詞彙字），執行它們的永遠是人類寫死的全函式運算，**根本沒有可計算性問題**。Phase T 的被發明物是「算子」=「一段會被反覆執行的計算」。新病態：**(i) 非全函式**（某輸入無定義 / 除零 / 拋例外 → 評估迴圈崩潰或行為未定）；**(ii) 無界步數**（隱含遞迴 / 對輸入規模迴圈 → 單次算子呼叫就能燒爆 token / 卡死）；**(iii) 不停機**（最壞）。這是 Phase S（算子全是人類寫死全函式）時不可能、算子自我發明才出現的停機危害。→ 需要一條**算子可計算性有界停機不變量** `OperatorComputabilityBounded`：(a) **全函式保證**——算子由 total PRIMITIVES × total COMBINATORS 組成，`apply()` 對任何輸入（含空、含極端值）皆有定義、永不拋例外（測試斷言 fuzz 輸入零例外）；(b) **有界步數保證**——算子是有界深度運算式樹，`cost()`（primitive 評估 + combinator 運算次數）結構性 <= `SDD_DIM_OP_STEP_MAX`（clamp，預設 8）；採納前 `guard_operator_computability` 驗 `cost() <= step_max` 且 fuzz-total，觸頂即 `OperatorComputabilityExceeded` → `MFSM_ESCALATION`；(c) **零遞迴零迴圈結構保證**——文法不含任何遞迴產生式 / 迴圈算子（grep 斷言 `operator_genesis.py` 無 `while`/`recursion`/自呼叫於算子求值路徑）。**這正補上 Phase S 的詞彙 stock / 批次速率對「被發明物本身的計算停機」全盲的最深缺口。** ← **PT-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『固定算子上的詞彙發明 + 批次退役』，缺『算子外發明 diff（meta⁵）+ 可計算性證據』」。
Phase S 的 `render_vocab_genesis_proposal` 渲染**固定 TRANSFORMS 上**發明的詞彙；`render_batch_recomposition_proposal` 渲染批次退役。算子自我擴充後，若系統現場發明一個選單外的新算子，人類面對的是「一個從未見過的新運算 + 它的算子生成文法來源」——**沒有人渲染『這個算子是系統怎麼從有限算子文法生成出來的、它有界嗎、它（全函式+有界步數）可計算嗎、它自指嗎、它憑什麼必要』**。提示反覆強調「人類維持設計環境掌舵者高度，而非降級為編碼員」——在「算子外計算本體論發明（meta⁵）」層，掌舵的最高形態是**人類能一眼看懂『系統憑空發明了哪個新算子、它的有界算子生成來源 + 可計算性證據（全函式 + cost<=step_max）+ 反自利證據 + 必要性勝率』，且系統在結構上不可能自動 commit 任何算子自我發明（每週期至多 K_op=1 個算子發明、每個必經人工 signoff）**。→ **PT-3**（算子外計算本體論發明掌舵介面 + `NoUnboundedOperatorGenesis`，K_op=1，承 Phase S K_vocab=1）。

【三、停機問題紅線覆查——本份比 Phase S 更危險，因為納管的是「會憑空發明自己算子（=自己寫一段會被反覆執行的計算）的迴圈」】
Phase S 的反諷（讓系統自我發明它的特徵詞彙）在 Phase T 升級為「讓系統**憑空發明自己的轉換/聚合算子（自己寫計算）**」。有界性與防自利必須再加固，且**首度必須證明被發明物本身可計算地停機**：
- **仍不新增形式化軌（承 Phase O/P/Q/R/S「重用 META_FSM、不增軌」的成熟示範）**：算子自我發明的採納/退役全部註冊為 `META_FSM` 既有的指紋命名空間（算子用新增 `operator-genesis:` 命名空間），其 add↔retire churn 由**同一條** `ChurnBounded`/`GraduationRatchet` 涵蓋。**但 PT-1/PT-2 揭示：churn 仍不夠**，故必須**對既有 `META_FSM` 再補兩條不變量**：`OperatorGenesisBounded`（算子基數 stock 天花板）+ `OperatorComputabilityBounded`（算子可計算性：全函式 + 有界步數）——關鍵是**沿用 Phase P/Q/R/S 對 `CrossScorerChurnBounded`/`DimensionCardinalityBounded`/`SwapCadenceBounded`/`VocabGenesisBounded`/`BatchSwapCadenceBounded` 的誠實作法：只新增 INVARIANT、不新增狀態變數**（`META_FSM` 維持 `<<mstate, churn, cap>>` 三變數 / 13 distinct，TLC 仍 No error，五軌不回歸；算子 stock 與可計算性的緊語意由 runtime `guard_operator_genesis`/`guard_operator_computability` + chaos `OPERATOR_GENESIS_GOODHART_FLAP`/`OPERATOR_COMPUTABILITY_FLAP` enforce/驗收，形式化層誠實標註為「single-counter 抽象之歸約引用」）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PT-1 的有界算子生成文法是硬約束，非建議**：算子自我發明的搜尋**必在有限算子文法（有限 `PRIMITIVES` × 有限 `COMBINATORS`）內可枚舉**，節點 <= `SDD_DIM_OP_BUDGET`（clamp[8,128]，預設 32）。**PT-1 的反自利是雙閘**：(a) 算子自我發明的 necessity tier **唯一合法來源仍是 generator 全體碰不到、content-hashed 凍結的 feature-grounded 算子必要性 held-out 勝率**（增量覆蓋 ∧ 非冗餘）；(b) **算子級自指守門**——任何 primitive/combinator/probe 引用保留自指信號（`self_score`/`proposer_*`/`necessity`/`oracle_*`…）的算子，在送 oracle 前即被 `operator_self_reference_guard` 攔下（零漏放）。`operator_genesis` **結構性不 import oracle、不讀必要性語料**（ast/import 隔離斷言，承 Phase S）。
- **PT-2 的算子可計算性是「全函式 + 有界步數 + 零遞迴零迴圈結構」三證**：算子由 total PRIMITIVES × total COMBINATORS 在有界深度運算式樹組成；`apply()` fuzz-total（任何輸入零例外）；`cost() <= SDD_DIM_OP_STEP_MAX`；採納前 `guard_operator_computability` 驗。觸頂 `OperatorComputabilityExceeded` → `MFSM_ESCALATION`。**這是把停機問題正面釘進框架自我擴充產物本身的形式化兌現。**
- **PROPOSED-only + 反 big-bang 算子發明，人類掌舵推到「算子外計算本體論發明（meta⁵）」層**：每週期至多 **K_op=1** 個算子自我發明可進 proposed-pending-signoff（`NoUnboundedOperatorGenesis`，承 Phase S K_vocab=1），每個必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4 / 9.30.4 / 9.31.4）。`steersman_renderer` 渲染「算子外計算本體論發明 diff（系統憑空發明哪個算子 + 算子生成文法來源 + 可計算性證據〔全函式 + cost<=step_max〕+ 反自指證據 + 必要性勝率）」，讓人類**不讀程式碼就能掌舵整個系統算子外的價值計算本體論發明**。
- **自我發明評估器（meta-oracle 自演化）續列最高 horizon、本份明確不做**：Phase T 把生成端（算子）拉進基質 B，但**評估端（必要性 oracle）仍由人類凍結**。「讓系統自我演化它的評估器本身」會讓 generator 與 evaluator 收斂到同一基質——這**自指地破壞 Phase O~T 全部反 Goodhart 保證所賴以成立的『對抗分離』地基**（生成者不可碰評估者的尺規）。採納它須先有更強的「對抗分離不可繞過性」形式化證明（例如一個 evaluator-of-evaluators 的、generator 全體碰不到的更高階 held-out meta-corpus + 其本身的反自利證明），這超出本份範圍，明確列為 §3.4 最高 horizon。

【四、上下文衰減（Context Degradation）視角覆查】
- 算子文法枚舉、feature-grounded 算子必要性 held-out 重放、可計算性驗證全在**隔離邏輯/落盤**進行，主線只在收到 proposed 算子發明時讀「算子外發明 diff + 可計算性證據 + 必要性勝率摘要」。算子帳本**沿用** Phase S 的 `value-dimension-ledger.yaml`（增 `operator_inventions` 領域審計段）+ 共用 Phase L 的 `meta-loop-ledger.yaml`（churn/operator-cardinality 治理），**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- feature-grounded 算子必要性 oracle 重用既有 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物（算子發明帳本 / 算子必要性勝率表 / 算子外發明 diff 報告）皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性 / 單一真實來源）：把「系統如何從有限算子文法**憑空發明一個 TRANSFORMS/OPS 外的新算子**」「它的算子生成來源、**可計算性證據（全函式 + 有界步數）**、反自指證據、凍結必要性證據」全部落地為 **Markdown/YAML 可推理產物**——**讓「系統如何發明它『用什麼運算去量它在乎什麼』、以及它如何證明那個運算一定會停」成為 AI 與人類都可直接推理、可審計的單一真實來源**，而非藏在 6+4 條硬編算子的天花板裡。以漸進式揭露重構知識（算子帳本落盤、按需 lazy 讀），守 `docs/` 作為地圖。
- Anthropic（生成-評估分離 / 評估器實體操作 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「固定算子上發明詞彙」（S）推到**「算子外算子自我發明」**（meta⁵）——生成端用**有界算子生成文法**把無界算子空間歸約為有限可枚舉、且**結構性 sub-Turing（全函式 + 有界步數）**（雙證有界），評估端用 **feature-grounded 算子必要性 oracle + 算子自指守門**專攻「算子自我發明 Goodhart / 自指自利算子」；評估器在**凍結 held-out 現實代理語料上實際以新算子計算、量客觀增量覆蓋**（對應提示「賦予 Evaluator 實體操作能力」於離線等價層——以現實代理語料替代生產流量，待 OPEN-10.6 改判再升活體）；並再次以「不增第六軌、只補 META_FSM 兩條不變量」示範「大膽移除冗餘鷹架」。你敢讓系統憑空發明它的算子（自己寫計算），就得能形式化證明這條算子發明迴圈仍會停（算子生成有界 + 每個算子可計算地停機）、且新算子不會在自指守門裡給自己發明一個「計算自己核可」的算子。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~S 落地元件**（對賬見上 thinking 一節），六條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O 的 obj-profile、P 的全評分器 calibration、Q 的 value-dimension、R 的 self-invention/swap、S 的 vocab-genesis/batch-swap〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase T 的價值在用提示三漏洞視角挖出 Phase S 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase S 全程在「固定的 6 條 TRANSFORMS + 4 條 OPS 算子」上自我發明特徵詞彙；讓系統自我發明一個算子外的全新算子，會憑空長出 Phase S（固定算子）時不存在的『算子外生成』新危害——尤其是前所有 Phase 都不存在的、最逼近停機問題本質的『算子可計算性危害』（被發明物第一次是『一段會被反覆執行的計算』而非『資料』），以及算子無界生成爆炸、算子自我發明 Goodhart（自指自利算子）。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PT-1** | **系統被鎖在固定 6 TRANSFORMS + 4 OPS 內，無「算子外算子自我發明」路徑；且 feature-grounded 算子必要性驗證缺席**——系統無法發明一個選單外的全新算子，即使硬發明也無 (i) 有界算子生成文法、(ii) feature-grounded 算子必要性 oracle、(iii) 算子級反自利守門。提示「生成-評估分離 + 主觀標準量化」在 **meta⁵（算子外發明）** 層缺席。 | `operator.*genesis\|GenesisOperator\|invent.*operator\|PRIMITIVES\|COMBINATORS` **零命中** |
| **PT-2** | **缺『算子可計算性』有界停機——前所有 Phase 都不存在的最深層停機缺口**——Phase Q/R/S 的被發明物都是「資料」，執行它們的是人類寫死全函式；Phase T 的被發明物是「算子」=「可執行計算」，自我發明的算子可非全函式 / 無界步數 / 隱含遞迴 → 單次呼叫燒爆 token / 崩潰 / 不停機。詞彙 stock / 批次速率對「被發明物本身的計算停機」全盲。這是「圖靈完備 vs 保證停機」第一次反噬到框架自我擴充產物本身。 | `operator.*comput\|OperatorComputability\|step.*budget\|op.*cost` **零命中** |
| **PT-3** | **缺『算子外發明 diff（meta⁵）+ 可計算性證據』掌舵介面**——`steersman` 只渲染固定算子上的詞彙發明與批次退役；無人渲染「系統憑空發明哪個算子 + 算子生成文法來源 + 可計算性證據（全函式 + cost<=step_max）+ 反自指證據」。人類掌舵在「算子外計算本體論發明層（meta⁵）」缺席。 | `render.*operator\|render.*op_genesis\|NoUnboundedOperatorGenesis` **零命中** |

**三缺口的共同主軸**：Phase S 讓人類站上「審系統在固定算子上自我發明詞彙 + 批次退役」的高度，但**框架的價值計算其實只能用一張『6+4 個算子的硬編選單』裡的運算**。Phase T 把人類抬到最高層——審「系統如何從**有界算子生成文法**憑空發明一個**選單外的全新算子**（憑什麼有界、**憑什麼一定會停（全函式 + 有界步數）**、憑什麼非自指自利）」——這正是 L10 完整「離線活體元迴圈」的**轉換算子文法自我擴充（meta⁵）**切片，精準補上提示在「狀態轉換（算子外生成-評估聯合合約）」「**停機問題（算子可計算性——把停機問題正面釘進自我擴充產物本身）**」「動態演進（算子外發明計算本體論而非只在固定算子選用）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase T 增量）

Phase T 對狀態機的改動延續 Phase O/P/Q/R/S 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42）；**仍不新增第六條形式化軌**——算子自我發明本質上**是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「VOCAB 外發明的詞彙字」泛化為「**TRANSFORMS/OPS 外現場發明的算子**」（meta⁵）。**重用既有 `META_FSM`** 並**僅補兩條不變量** `OperatorGenesisBounded` + `OperatorComputabilityBounded`（不增狀態變數），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PT-1/PT-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌、無新狀態變數）

| 元件 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `operator_genesis`（TRANSFORMS/OPS 外算子自我發明骨架；有界算子生成文法〔全函式 + 有界步數〕+ 算子自指守門） | runtime（落 `value-dimension-ledger.yaml` `operator_inventions` 段） | 生成器骨架（advisory） | 跨 session 收官 / `MEMORY_CONSOLIDATION` 旁路 | 產 `proposed` 算子發明（only 透過注入 evaluate 取必要性，無自評；算子自指守門 + 可計算性結構性保證） | 否 |
| `dimension_necessity_oracle`（**新增 feature-grounded `evaluate_genesis_operator`**） | runtime（重用 `counterfactual_replay` 重放基座，凍結算子必要性現實情節） | 評估器（硬閘） | 算子發明提案後 | 必要性 tier（feature-grounded 增量覆蓋 ∧ 非冗餘；capability-delta 唯一合法來源） | 否（但決定 adopt 准駁） |
| operator-genesis 採納（stock 天花板 + 可計算性） | **新增 `operator-genesis:` 指紋命名空間**（meta-loop-ledger）+ **新增** `OperatorGenesisBounded` + `OperatorComputabilityBounded` 不變量 | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | `meta_halt_monitor.guard_operator_genesis` + `guard_operator_computability` + `record_rule_add` | `ChurnBounded` ∧ `GraduationRatchet` ∧ `OperatorGenesisBounded`（op stock）∧ `OperatorComputabilityBounded`（cost<=step_max + total）准駁；觸頂 → `MFSM_ESCALATION` | — |
| `steersman_renderer.render_operator_genesis_proposal`（算子外發明 diff + 可計算性證據 + 反 big-bang） | runtime（advisory） | 算子發明過必要性 oracle 後 | 算子外發明 diff + 可計算性證據；標「待人工 signoff、本週期 ≤K_op=1」 | 否 |

> **選位說明**：
> - `operator_genesis` 把 Phase S 的 `vocabulary_genesis`（在**固定 TRANSFORMS**上組合詞彙）**升維為算子外生成（meta⁵）**：它在一個 **bounded 算子生成文法**（有限原始算子 `PRIMITIVES` × 有限組合算子 `COMBINATORS`）上**可枚舉地**生成 `GenesisOperator`（算子，節點 <= `SDD_DIM_OP_BUDGET`），**結構性保證每個算子全函式 + 有界步數**（PT-2），再透過呼叫端**注入的 `evaluate` 回呼**（= feature-grounded 算子必要性 oracle）取每個發明算子的必要性。`operator_genesis` 因此**結構性無法用自己的尺規證明自己必要**（它根本沒有必要性語料），且**結構性拒絕算子自指**（反自利第一閘）。`expanded_ops()` = 基礎 OPS ∪ 已採納算子發明——synthesizer 之後可在這擴充後的算子上組合維度（meta⁵ 對 meta-meta-meta 的供料）。
> - `dimension_necessity_oracle` 的 Phase T 升級是其**靈魂**：新增 `evaluate_genesis_operator` ——**不靠算子名匹配**，而是在**固定參照 probe 的凍結算子必要性語料**上，以發明算子聚合量「既有 OPS 全算子都拿不到的增量覆蓋 ∧ 非冗餘」。專攻 feature-grounded oracle（預設只見固定算子）看不見的**算子外自我發明 Goodhart**。
> - 算子採納的 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PT-2 的可計算性由**新增的可計算性不變量** `OperatorComputabilityBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙、不動狀態變數），五軌 TLC 不回歸、不增第六軌、`META_FSM` 維持 13 distinct。

### 1.2 meta⁵ 算子自我發明迴圈（重用 META_FSM 有界停機契約 + 有界算子生成文法 + 可計算性三證 + 反自利雙閘）

```
（離線、跨 session）
operator_genesis.genesis_round()
  在 bounded 算子生成文法（PRIMITIVES × COMBINATORS，有界深度運算式樹，可枚舉節點 <= SDD_DIM_OP_BUDGET）生成候選 GenesisOperator go
    [可計算性結構保證] 每個 go 由 total PRIMITIVES × total COMBINATORS 組成 → 全函式 + cost(go) <= SDD_DIM_OP_STEP_MAX（零遞迴零迴圈，PT-2）
    operator self-reference guard：primitive/combinator/probe 引用保留自指信號（self_score/proposer_*/necessity/oracle_*）→ 結構性丟棄（反自利第一閘，不送 oracle）
    對每個倖存 go：必要性 = 注入的 evaluate(go)（= feature-grounded oracle 增量覆蓋；genesis 看不到語料）
  取至多 K_op=1 個必要性最高的候選（NoUnboundedOperatorGenesis）→ 算子自我發明 go*
  → dimension_necessity_oracle.evaluate_genesis_operator(go*)：在「genesis 全體不可見、content-hashed 凍結」的固定 probe 算子必要性情節上，
       以 go* 聚合量 (a) 增量覆蓋（既有 OPS 全算子拿不到的）+ (b) 非冗餘度
     ├─ 增量覆蓋 ≥ margin ∧ 非冗餘度 < 門檻 → 取得「必要性 tier++」
     │     → 產 proposed 算子發明 + 可計算性證據 + 必要性證據 → steersman 渲染算子外發明 diff → 人工 signoff
     │     └─ 人工接受 → guard_operator_computability（cost<=step_max + fuzz-total）→ guard_operator_genesis（op stock 未滿）→ record_rule_add("operator-genesis:hash(go*)")（擴充 OPS）
     └─ 未達必要性（含「自指自利算子」「算子外噪音算子」）→ 拒絕提案 → 純記錄

（採納守門，任一觸頂 → MFSM_ESCALATION 人工裁決）
  guard_operator_computability(go)（PT-2）：cost(go) > SDD_DIM_OP_STEP_MAX 或 apply() fuzz 非全函式 → OperatorComputabilityExceeded
  guard_operator_genesis(fp)（PT-1）：現存活躍 operator-genesis 算子數 >= SDD_DIM_OP_MAX → OperatorCardinalityExceeded
```

- **核心有界性（重用既有證明 + 兩條新不變量）**：
  - 算子生成（PT-1）：算子自我發明在**有限算子文法**內可枚舉，節點 <= `SDD_DIM_OP_BUDGET`（clamp[8,128]，預設 32），**絕不無界爆炸**（「TRANSFORMS/OPS 外」≠「無界」的形式化兌現）。
  - **算子可計算性（PT-2 新增 `OperatorComputabilityBounded`）**：每個算子 = 有界深度運算式樹 over total PRIMITIVES × total COMBINATORS → 全函式（apply 對任何輸入零例外）+ `cost() <= SDD_DIM_OP_STEP_MAX`（clamp[1,64]，預設 8）+ 零遞迴零迴圈；`guard_operator_computability` 採納前驗，觸頂 `OperatorComputabilityExceeded` → `MFSM_ESCALATION`。
  - op stock（PT-1 新增 `OperatorGenesisBounded`）：現存活躍 `operator-genesis:` 算子數 <= `SDD_DIM_OP_MAX`（clamp[1,64]，預設 16）；觸頂 `guard_operator_genesis` raise `OperatorCardinalityExceeded` → `MFSM_ESCALATION`。
  - per-fingerprint：任一 `operator-genesis:hash` 的 add↔retire churn <= `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納須挾必要性 tier 嚴增（既有 `GraduationRatchet`）。
- **反自利雙閘（PT-1）**：(a) `necessity_tier`（capability-delta）的**唯一合法來源是凍結 feature-grounded 算子必要性 held-out oracle 的（增量覆蓋 ∧ 非冗餘）勝率**——任何 genesis 自評，**結構性禁止**充當必要性 capability-delta（ast/import 隔離斷言、genesis 無讀寫權、不 import oracle）；(b) **算子自指守門結構性拒絕**——任何 primitive/combinator/probe 引用保留自指信號的算子在送 oracle 前即被 `operator_self_reference_guard` 攔下（零漏放）。把「生成-評估分離 + 反自利」釘死在 **meta⁵** 層級。

### 1.3 典型軌跡（含 Phase T 改善後的 self-verification 案例）

```
（跨 session 收官）genesis_round：近 5 session 真實落盤顯示「既有 4 條 OPS（mean/max/min/sum）都不量某類『離散度尖峰』失敗、現有算子連『運算』都沒有」
  → operator_genesis 在算子文法（PRIMITIVES 含 range/median/spread × COMBINATORS 含 clip01/diff）枚舉候選算子；operator self-ref guard 丟棄引用 self_score 的誘餌算子；每個候選結構性保證全函式 + cost<=8
  → 注入 evaluate（feature-grounded 算子必要性 oracle）給 go*="diff(max,median)"（峰度差）高分；K_op=1 取此一者
  → dimension_necessity_oracle.evaluate_genesis_operator：在 50 筆固定 probe 的凍結算子必要性情節，以 go* 聚合 → augmented 真實品質 0.81 vs baseline（僅既有 OPS 全算子）0.58（增量覆蓋 Δ=0.23 ≥ margin 0.10）；非冗餘度 0.42 < 門檻 0.95
  → 取得必要性 tier++ → guard_operator_computability：cost(diff(max,median))=3 <= 8 ∧ fuzz-total ✅ → proposed 算子發明 → steersman 渲染「算子外計算本體論發明（meta⁵）：系統憑空發明算子『diff(max,median)』（算子文法來源：primitive=max·secondary=median·combinator=diff、全函式 cost=3<=8、非自指）+ 23% 增量覆蓋證據」
  → 人工 signoff → op stock 未滿 → record_rule_add("operator-genesis:hash(go*)") → 正式擴充 OPS（synthesizer 之後可用 diff(max,median) 算子組合維度）

（算子可計算性攻擊案例：無界步數算子）operator_genesis（受擾）被要求構造一個隱含對輸入規模迴圈/遞迴的算子
  → 有界算子文法根本不含遞迴/迴圈產生式（結構保證）；若硬注入超深運算式樹 → cost() > SDD_DIM_OP_STEP_MAX → guard_operator_computability raise OperatorComputabilityExceeded → MFSM_ESCALATION（被發明物本身的停機被守門封死，PT-2 核心）

（算子可計算性攻擊案例：非全函式算子）注入一個對某輸入除零/拋例外的算子
  → apply() 由 total PRIMITIVES × total COMBINATORS 組成（ratio_safe 對 0 分母回退、空輸入回 0.0）→ fuzz 任何輸入零例外（全函式保證）；guard_operator_computability fuzz-total 檢查零漏放

（算子自我發明 Goodhart 攻擊案例：自指自利算子）operator_genesis（受擾）生成 go**="identity(self_score)"（算子計算自己核可訊號）
  → operator self-reference guard：primitive/combinator/probe 含保留自指信號 self_score → 結構性丟棄，根本不送 oracle（反自利第一閘，零漏放）

（算子外噪音算子）operator_genesis 生成一個真實增量覆蓋為 0 的算子
  → feature-grounded oracle：augmented vs baseline 真實品質增益 ≈ 0 < margin → 不取得 tier → 拒絕，絕不擴充 OPS

（算子無界生成爆炸）operator_genesis 被要求枚舉超大算子文法
  → 算子文法枚舉節點達 SDD_DIM_OP_BUDGET → 截斷停止（best-so-far），絕不指數爆炸（有界算子文法）

（算子基數爆炸）系統反覆發明不同的真必要算子（每個首採、churn=0）
  → guard_operator_genesis：現存活躍 operator-genesis 算子數逼近 SDD_DIM_OP_MAX → OperatorCardinalityExceeded → MFSM_ESCALATION → steersman 導人工「算子已過度膨脹」
```

**對比 Phase S 現況**：（a）只能在固定 6+4 個算子上自我發明詞彙，無任何算子外算子發明路徑；（b）即使硬加 operator grammar，沒有任何機制保證「自我發明的算子一定會停（全函式 + 有界步數）」、攔得住「算子無界生成爆炸 / 自指自利算子」。Phase T 讓系統**能有界地自我發明 TRANSFORMS/OPS 外的新算子、且每個發明算子必須在有界算子文法內生成 + 結構性可計算（全函式 + 有界步數）+ 非自指 + 在 genesis 全體碰不到的凍結 feature-grounded 現實試金石上證明真的必要且非冗餘**——人類從「審固定算子上的詞彙發明 + 批次退役」升為**「審 TRANSFORMS/OPS 外的算子計算本體論發明（meta⁵）」**，精準對應提示「人類維持設計環境掌舵者高度」於**最高的算子外計算本體論發明層**，且**首度把停機問題正面釘進框架自我擴充的產物本身**。

---

## 2. 環境建構與記憶體管理策略（Phase T 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/value-dimension-ledger.yaml`（**沿用** Phase R/S，新增 `operator_inventions` 領域審計段）：跨 session 算子外發明提案（發明算子 hash、算子文法來源 primitive·combinator·secondary·probe、是否自指、cost、是否全函式、feature-grounded 必要性、necessity tier、人工 signoff 狀態）。**落盤不常駐**，按需 lazy 讀。churn/operator-cardinality 治理走的是**共用 `meta-loop-ledger.yaml`**（`operator-genesis:` 命名空間，沿用 Phase Q/R/S）。
- `knowledge/held-out-corpus/`（**擴充** Phase O/P/Q/R/S 既有目錄，content-hashed 凍結）：新增 **feature-grounded 算子必要性情節語料 `OPR-*.yaml`**（歷史情節 + 候選**固定參照 probe 特徵向量** + 已知整體真實結果），供 `evaluate_genesis_operator` 重放；**`operator_genesis` 程式路徑禁止讀寫**（隔離斷言）；重用 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`。**12 個凍結 `OPR-*.yaml` 皆為真必要基準試金石（`expect: true_operator`）；噪音 / 冗餘算子的 Goodhart 攻擊由測試端構造算子在該語料上驗拒（zero-miss），非語料檔本身含噪音 / 冗餘分類。**
- `build/reports/value-dimension/OPR-{date}.md`（新增）：算子外發明提案報告（算子發明 diff + 算子文法來源 + 可計算性證據 + 反自指證據 + 增量覆蓋/非冗餘證據 + 本週期 K_op 標示），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——算子發明元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 新增 `operator-genesis:` 指紋命名空間（不改 `.tla` 狀態宇宙、不增狀態變數）、(b) 對 `META_FSM.tla` **補兩條 INVARIANT** `OperatorGenesisBounded` + `OperatorComputabilityBounded`（沿用 P/Q/R/S 對既有界的誠實作法：single-counter 抽象之歸約引用 + runtime/chaos enforce 緊語意）——**新增不變量而非新增狀態/變數**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 五 safety + liveness + P 的 `CrossScorerChurnBounded` + Q 的 `DimensionCardinalityBounded` + R 的 `SwapCadenceBounded` + S 的 `VocabGenesisBounded`/`BatchSwapCadenceBounded` 涵蓋算子發明元迴圈，**另補** `OperatorGenesisBounded`（op stock 天花板）+ `OperatorComputabilityBounded`（算子可計算性）；新增測試斷言「算子發明走獨立 `operator-genesis:` stock 天花板、算子受可計算性三證（全函式 + cost<=step_max + 零遞迴零迴圈）封死、且皆過 `meta_halt_monitor`」。
- `operator_genesis` 鷹架本身納入 `scaffold_roi` 帳本，並由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **算子自我發明守門**：(a) 生成在有限算子文法內可枚舉、節點 <= `SDD_DIM_OP_BUDGET`（測試斷言搜尋有界）；(b) 算子自指守門結構性拒絕（測試斷言 operator self-ref guard 零漏放）；(c) **可計算性三證**（測試斷言 fuzz-total 零例外 + cost<=step_max + 算子求值路徑無 `while`/遞迴）；(d) `operator_genesis` 只能**提案**，**不能自動納入**（測試斷言無法繞過 `human_signoff` + `guard_operator_genesis` + `guard_operator_computability`），且**每週期至多 K_op=1 個算子發明**（`NoUnboundedOperatorGenesis`）。

### 2.3 Prompt / 上下文與防衰減
- Phase T **不新增任何常駐 eager prompt**。算子文法枚舉、feature-grounded 算子必要性重放、可計算性驗證皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 算子發明時讀「算子外發明 diff + 可計算性證據 + 必要性勝率摘要」。
- 所有新產物（算子發明帳本 / 算子必要性語料 / 提案報告）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-141~146）

#### Pillar A — 算子生成文法自我擴充骨架（PT-1 算子外生成 meta⁵ + PT-2 可計算性結構保證）

**ACT-141 — Operator Genesis Grammar + 有界算子生成文法（全函式 + 有界步數）+ 算子自指守門**
- **檔案**：`tools/fsm_runtime/operator_genesis.py` + `build/state/value-dimension-ledger.yaml`（沿用，增 `operator_inventions` 段）
- **設計**：定義 `GenesisOperator`（由 `primary`〔PRIMITIVE〕+ `combinator`〔COMBINATOR〕+ optional `secondary`〔PRIMITIVE，供二元組合〕+ 固定 `probe`〔base VOCAB 特徵子集〕決定性編碼 + namespace `operator-genesis:` + 凍結 rationale）與**有界算子生成文法**（`PRIMITIVES` 有限 total list-reduction × `COMBINATORS` 有限 total 後變換/二元組合）。`PRIMITIVES`（全 total、O(n)、零遞迴）：`mean/max/min/sum/range/median/spread/last`。`COMBINATORS`（全 total）：`identity/abs/neg/clip01/sq`（一元）+ `diff/ratio_safe/max2/min2`（二元，需 secondary）。`GenesisOperator.apply(features)` = 把 probe 特徵以算子（有界深度運算式樹）聚合為一純量，**全函式**（空輸入回 0.0、ratio_safe 0 分母回退、無例外）；`cost()` = primitive 評估 + combinator 運算次數（結構性 <= 常數，二元組合 <= 3）。`enumerate_genesis_operators(budget)` 在文法上**可枚舉、deterministic、cap 在 budget**（`SDD_DIM_OP_BUDGET`，clamp[8,128]，預設 32）；`operator_self_reference_guard(go)` 拒絕 primitive/combinator/secondary/probe 引用保留自指信號（沿用 synthesizer `RESERVED_SELF_REF`）；`operator_genesis(evaluate, budget)` 在倖存候選上以注入 `evaluate` 找最佳；`operator_genesis_round(evaluate, k=1)` 套反 big-bang K_op=1 截斷；`expanded_ops(accepted)` 回基礎 OPS ∪ 已採納算子名。純離線、deterministic。**只提案、絕不自動納入、絕不自寫常數**（守 Rule 8 / 9.31.4）。**結構性不 import oracle、不讀必要性語料**（對抗分離，承 Phase S）。算子求值路徑**零 `while`/零遞迴/零自呼叫**（PT-2 結構保證）。
- **驗收**：≥4 情境 fixture（算子外真必要發明〔應提〕/ 算子已足夠〔應不提〕/ 自指自利算子誘餌〔operator self-ref guard 攔〕/ deterministic 可重現）；生成節點 <= `SDD_DIM_OP_BUDGET`；operator self-reference guard 零漏放；**可計算性：對全部枚舉算子（264 個）× 多組極端輸入（空/單元素/負/0/極大含浮點上限 1e200/1e308）做 fuzz，合計 264 × 16 = 4224 次 apply 呼叫，零例外、無 inf、無 nan（全函式，由 `_finite` 飽和投影結構性兌現）+ 所有枚舉算子 cost <= `SDD_DIM_OP_STEP_MAX`**；ast 斷言算子求值路徑無 `while`/遞迴；ast/import 斷言 genesis 對 oracle 隔離。

#### Pillar B — feature-grounded 算子必要性反 Goodhart 評估（PT-1 核心；L10 meta⁵ 的安全紅線）

**ACT-142 — Dimension Necessity Oracle feature-grounded 擴充（`evaluate_genesis_operator`）**
- **檔案**：`tools/fsm_runtime/dimension_necessity_oracle.py`（新增 `OperatorCandidate`/`OperatorCase`/`evaluate_genesis_operator`/`necessity_score_operator`/`load_operator_corpus`）+ `knowledge/held-out-corpus/OPR-*.yaml`（凍結算子必要性情節，含固定參照 probe 特徵向量）
- **設計**：重用 `counterfactual_replay`/`SDD_REPLAY_MAX_CASES` 重放基座；**不靠算子名匹配**——對一個現場發明的新算子，把它（以固定參照 probe 聚合）套到 case 特徵向量現算 `dim_value`，量 (a) **增量覆蓋**（augmented〔既有 OPS 全算子最佳 + 發明算子〕vs baseline〔僅既有 OPS 全算子最佳〕的真實品質增益）+ (b) **非冗餘度**（發明算子候選排序與既有 existing_cost 排序的最大一致率），回 `DimensionVerdict`（necessity tier = capability-delta 唯一合法來源）。**結構性隔離**：算子必要性語料路徑與 `operator_genesis` 互斥，genesis 無讀寫權；**「genesis 自評必要、但 oracle 判不必要/冗餘 → 以 oracle 為準」**。oracle 可知 `operator_genesis` 的 `GenesisOperator` 介面（duck-typed `.apply()`/`.name`，反向不可，承 Phase S）。
- **驗收**：≥12 fixture（6 算子外真必要發明〔增量覆蓋 ≥ margin ∧ 非冗餘〕+ 3 算子外噪音算子假必要〔增量覆蓋 0〕+ 3 冗餘算子〔增量覆蓋 > 0 但非冗餘度 ≥ 門檻〕）；真必要偵出率 ≥ 85%、**算子自我發明 Goodhart（噪音算子+冗餘算子）攔截率 100%（零漏放，安全紅線）**；斷言 `operator_genesis` 程式無法觸及算子必要性語料。
  - **釐清（OPR 語料 vs 攻擊 fixture）**：12 個凍結 `OPR-*.yaml` 語料**皆為真必要基準試金石**（`expect: true_operator`）；噪音算子 / 冗餘算子的 Goodhart 攻擊是在 `test_phase_t.py` 測試端以 `_noise_operator_case`/`_redundant_operator_case` + 候選算子構造（壞算子 × case 屬性）在該語料上**驗拒**（zero-miss），**非語料檔本身含 3 噪音 + 3 冗餘分類**。

#### Pillar C — 算子 stock + 可計算性有界停機納入既有 META_FSM（PT-1/PT-2；不增第六軌，只補兩條不變量）

**ACT-143 — op stock + 可計算性守門 + `OperatorGenesisBounded` + `OperatorComputabilityBounded` + META_FSM 重證（無新狀態/無新變數）**
- **檔案**：`tools/fsm_runtime/meta_halt/meta_ledger.py`（增 `operator-genesis:` 命名空間判定 + active operator-genesis stock 查詢）+ `meta_halt_monitor.py`（`guard_operator_genesis` + `OperatorCardinalityExceeded`；`guard_operator_computability` + `OperatorComputabilityExceeded`；`meta_state` 觸頂升 ESCALATION + env getters `op_max`/`op_step_max`）+ `operator_genesis.py`（`adopt_genesis_operator` 算子採納入口走 `guard_operator_computability` → `guard_operator_genesis`）+ `formal/META_FSM.tla`（**新增 INVARIANT** `OperatorGenesisBounded` + `OperatorComputabilityBounded`，**不新增狀態/變數**）+ `META_FSM.cfg`（INVARIANT 區塊列入）
- **設計**：算子採納 = 先 `guard_operator_computability`（cost<=step_max + fuzz-total，PT-2）再在 op stock 未滿時 `record_rule_add("operator-genesis:…")`，`guard_operator_genesis` 以「現存活躍 operator-genesis 算子數 < `SDD_DIM_OP_MAX`」守門。**不改 `META_FSM.tla` 狀態宇宙、不增狀態變數**，僅補兩不變量（誠實標註：op stock / 可計算性緊語意 runtime+chaos enforce）+ 測試證明算子走獨立 stock、算子受可計算性三證封死。
- **驗收**：`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT `OperatorGenesisBounded` + `OperatorComputabilityBounded` PASS）+ 離線 BFS reachable 不變；新增 test 斷言「op stock 觸頂 → `OperatorCardinalityExceeded` → `MFSM_ESCALATION`」「算子 cost 超界 → `OperatorComputabilityExceeded` → `MFSM_ESCALATION`」「非全函式算子被 guard 攔」；**五軌 TLC 全不回歸（SDD 42 reachable / 831 TLC distinct / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）**。

#### Pillar D — 人類掌舵「算子外計算本體論發明（meta⁵）」層 + 可計算性證據 + 反 big-bang（PT-3；無新狀態）

**ACT-144 — Steersman 算子外發明 diff + 可計算性證據 + NoUnboundedOperatorGenesis + PROPOSED 人工 gate**
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_operator_genesis_proposal`）
- **設計**：`render_operator_genesis_proposal` 渲染「本輪算子外發明 diff（系統憑空發明哪個算子 + 算子生成文法來源〔primitive·combinator·secondary·probe〕+ **可計算性證據**〔全函式 ✅ + cost<=step_max〕+ 是否自指〔non-self-ref 證據〕+ 增量覆蓋與非冗餘證據）+ 本週期 ≤K_op=1 標示」，**advisory**；任一算子發明納入 **必經人工 signoff**，渲染器絕不自動納入、絕不自動 commit；**每週期至多 K_op=1 個算子發明**（`NoUnboundedOperatorGenesis`）。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K_op=1 上限、算子生成文法來源、可計算性（全函式 + cost）、非自指」；斷言渲染器無法自呼叫 adopt / `record_rule_add` / `adopt_genesis_operator`；K_op+1 個算子發明同週期 → 被截到 1 並標示「其餘順延」。

#### 收官

**ACT-145 — Rule 9.32 治理落地 + ID 翻牌**
- **檔案**：`governance/rules/R-9.32-self-expanding-operator-grammar-phase-t.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#22 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `ID_REGISTRY.yaml` 翻牌（act 141→147 / rule 9.32→9.33）+ `test_id_registry.py` 前緣斷言 + Phase T ownership 測試。
- 子規則 9.32.1~9.32.5 見 §4。

**ACT-146 — Phase T 形式化重證 + chaos + 全綠驗收**
- **形式化**：`META_FSM` 維持 No error（13 distinct，新 INVARIANT `OperatorGenesisBounded` + `OperatorComputabilityBounded` PASS）+ 算子發明元迴圈納管測試全綠；**五軌 TLC 全 No error 不回歸**（不增第六軌）。
- **Chaos**：100 輪新增兩故障型 `OPERATOR_GENESIS_GOODHART_FLAP`（連續注入自指自利算子 / 算子外噪音算子假必要 → 驗 operator self-ref guard + feature-grounded oracle 零漏放）與 `OPERATOR_COMPUTABILITY_FLAP`（注入超步數 / 非全函式算子 → 驗 `OperatorComputabilityBounded` → `OperatorComputabilityExceeded` → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K。
- **pytest**：估 +50~70（ACT-141 ~18 + ACT-142 ~16 + ACT-143 ~14 + ACT-144/整合/chaos ~10，扣重疊）≈ **1206 → 約 1256~1276 passed**。實際以執行時為準。

### 3.2 執行依賴圖

```
ACT-141（Operator Genesis Grammar + 有界算子生成文法〔全函式+有界步數〕+ 算子自指守門）──┐
                                                                       ├─► ACT-143（op stock + 可計算性 + OperatorGenesisBounded + OperatorComputabilityBounded + META 重證）──► ACT-144（steersman 算子外發明 diff + 可計算性證據 + 人工 gate）
ACT-142（Necessity Oracle feature-grounded evaluate_genesis_operator）──┘                                                                       │
                                     四柱完成 ──► ACT-145（R-9.32 + ID 翻牌）──► ACT-146（META 重證 + 雙 chaos 故障型 + pytest 全綠）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

提示輸出要求 #4 的「Level 5」是通用模板殘留；使用者標題明示終極目標 **Level 10**。框架自有 L 量表（仿自動駕駛分級）對賬如下，本份明確交付 **L10 完整之「離線活體 meta⁵ 迴圈 · 轉換算子文法自我擴充」切片**：

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L10 完整 · 離線活體元迴圈（單評分器） | Meta-Optimization：自校準 1 個目標函式 | O |
| L10 完整 · 離線活體元迴圈 · 全評分器一體化 | Unified All-Scorer Self-Calibration | P |
| L10 完整 · 離線活體 meta-meta 迴圈 · 價值維度自我擴充 | Self-Expanding Value Dimensions + DimensionCardinalityBounded | Q |
| L10 完整 · 離線活體 meta-meta-meta 迴圈 · 維度語意自我發明 + 退役聯動 | Self-Inventing Value Dimensions：候選池外有界生成文法 + 自指守門 + SwapCadenceBounded | R |
| L10 完整 · 離線活體 meta⁴ 迴圈 · 生成文法詞彙自我擴充 + 批次退役聯動 | Self-Expanding Vocabulary & Batch Retirement：VOCAB 外有界詞彙生成 + VocabGenesisBounded + BatchSwapCadenceBounded | S |
| **L10 完整 · 離線活體 meta⁵ 迴圈 · 轉換算子文法自我擴充** | **Self-Expanding Operator Grammar：TRANSFORMS/OPS 外有界算子生成文法（sub-Turing：全函式 + 有界步數，把停機問題正面釘進自我擴充產物本身）+ feature-grounded 算子必要性反 Goodhart + 算子自指守門（反自利）+ OperatorGenesisBounded（算子基數停機）+ OperatorComputabilityBounded（算子可計算性停機）** | **T（本份 PT-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-S.x/R.x/Q.x/M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體** meta⁵ 發明 + **自我發明評估器（meta-oracle 自演化）** | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版、亦不做自我發明評估器**。完整 L10 之「活體 meta⁵ 迴圈」需在真實生產流量上線上自我發明算子（受 OPEN-10.6 約束）；「自我發明評估器」自指地破壞對抗分離地基（須先有更強的對抗分離不可繞過性證明）。本份交付**離線等價切片**：用框架自身歷史的 feature-grounded 算子必要性 held-out 現實代理語料當試金石，**在本地完成「TRANSFORMS/OPS 外有界算子自我發明」的等價驗證價值**。承 Phase O/P/Q/R/S 的「先窄後寬」紀律，本份把「固定算子上詞彙發明」推進為「算子外算子自我發明」，並把算子外才出現的危害（算子可計算性 / 算子無界生成 / 自指自利算子）首次納管——這是 Phase S 自陳 horizon #3 的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-S.x/R.x/Q.x/M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6，續列 horizon。
- **活體 meta⁵ 發明**：本份離線（feature-grounded 算子必要性 held-out 現實代理）；活體版需在生產流量上線上自我發明算子，受 OPEN-10.6 約束（OPEN-T.x 承前）。
- **自我發明評估器（meta-oracle 自演化）**：**最高 horizon**。本份所有 oracle（必要性 / 詞彙必要性 / 算子必要性）為人類凍結；「系統自我演化它的**評估器本身**」涉及對抗分離地基自指（generator 與 evaluator 收斂同基質會掏空全部反 Goodhart 保證），須先有「evaluator-of-evaluators 的、generator 全體碰不到的更高階 held-out meta-corpus + 其本身反自利證明」的對抗分離不可繞過性證明。**未獲此證明前不得採納**（守 Rule 9.32.5）。
- **組合算子文法（meta⁶）**：本份算子文法為「PRIMITIVES × COMBINATORS 有界深度」；「系統自我擴充 `PRIMITIVES`/`COMBINATORS` 集合本身」是更高階開放問題，列 horizon（涉及更深的可計算性證明）。

---

## 4. 防護規則新增（CLAUDE.md §9.32 Phase T — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.32.1 算子生成文法自我擴充骨架（OperatorGenesis / BoundedGrammar，meta⁵） | ACT-141 | TRANSFORMS/OPS 外算子自我發明經 `operator_genesis` 在 **bounded 算子生成文法**（有限原始算子 `PRIMITIVES` × 有限組合算子 `COMBINATORS`）**可枚舉**、節點 <= `SDD_DIM_OP_BUDGET`（clamp[8,128] 預設 32）；「TRANSFORMS/OPS 外」≠「無界」（更深的無界生成需另證有界的形式化兌現）；只提案、絕不自動納入、絕不自寫常數；**結構性不 import oracle / 不讀必要性語料**（對抗分離，編譯期隔離斷言） |
| 9.32.2 算子自我發明反自利（OperatorGenesisAntiSelfInterest） | ACT-141/142 | 算子自我發明的 capability-delta tier **唯一合法來源是 genesis 不可見、content-hashed 凍結的 feature-grounded 算子必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率**；genesis 自評**結構性禁止**充當；**genesis 自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準**；**算子自指守門結構性拒絕**（primitive/combinator/secondary/probe 引用保留自指/proposer/oracle 內部信號 → `operator_self_reference_guard` 攔，零漏放）；算子外噪音算子/冗餘算子攔截零漏放 |
| 9.32.3 算子可計算性有界停機（OperatorComputabilityBounded，PT-2 核心） | ACT-141/143/146 | 每個自我發明算子**結構性保證全函式 + 有界計算步數 + 零遞迴零迴圈**：(a) 算子由 total `PRIMITIVES`（O(n) list-reduction）× total `COMBINATORS`（total 後變換/有界元數二元組合）在**有界深度運算式樹**組成 → `apply()` 對任何輸入（含空/極端值）有定義、永不拋例外（fuzz-total）；(b) `cost()` <= `SDD_DIM_OP_STEP_MAX`（clamp[1,64] 預設 8）；(c) 算子求值路徑零 `while`/零遞迴/零自呼叫；採納前 `guard_operator_computability` 驗，觸頂 `OperatorComputabilityExceeded` → `MFSM_ESCALATION`。這把「圖靈完備 vs 保證停機」正面釘進框架自我擴充的產物本身——被發明物（算子=可執行計算）本身可證停機，而整個閉環仍靠 LLM+紙帶維持圖靈完備 |
| 9.32.4 算子基數 + 反 big-bang 算子發明（OperatorGenesisBounded + NoUnboundedOperatorGenesis） | ACT-143/144 | (i) 現存活躍 `operator-genesis:` 算子數 <= `SDD_DIM_OP_MAX`（clamp[1,64] 預設 16）→ 觸頂 `OperatorCardinalityExceeded` → `MFSM_ESCALATION`（`guard_operator_genesis`）；(ii) 每週期至多 **K_op=1**（`SDD_DIM_EXPAND_K` 預設 1，沿用 Phase Q/R/S）個算子自我發明可進 proposed-pending-signoff，每個必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4 / 9.30.4 / 9.31.4）；genesis/steersman 絕不自動 commit、絕不自動納入、絕不一次劫持整個算子本體論；退役算子再採納須挾 necessity capability-delta（沿用 `GraduationRatchet`）；**重用既有 `META_FSM`、僅補 `OperatorGenesisBounded` + `OperatorComputabilityBounded` INVARIANT、不增狀態/變數、不增第六軌**；五軌 TLC 全不回歸、算子發明不污染單軌 `SDD_FSM.tla` |
| 9.32.5 算子自我發明誠實 + 活體/meta-oracle horizon | ACT-142/146 | feature-grounded 算子必要性勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；組合算子文法（meta⁶：自我擴充 PRIMITIVES/COMBINATORS 集合）+ **自我發明評估器（meta-oracle 自演化，最高 horizon——未獲對抗分離不可繞過性證明前不得採納）** + 活體 meta⁵ 發明版受 OPEN-10.6 約束續列 horizon（OPEN-T.x 承 OPEN-S.x/R.x/Q.x/O.7/M.7/P.7 暫不放寬沙箱） |

### ❌ Phase T 新增禁止行為（草案）
- `operator_genesis` 自動納入算子自我發明 / 自寫常數、繞過人工 signoff + `guard_operator_genesis`/`guard_operator_computability`（破 9.32.1/9.32.4 / Rule 8）
- 用 genesis 自評充當「算子自我發明必要性 capability-delta tier」（破 9.32.2，算子自我發明 Goodhart 自評放水）
- 算子自我發明 primitive/combinator/secondary/probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 `operator_self_reference_guard`）（破 9.32.2 反自利）
- `operator_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/OPR-*` 算子必要性語料或 `dimension_necessity_oracle`（破 9.32.2 對抗分離）
- 算子自我發明搜尋超 `SDD_DIM_OP_BUDGET` 仍指數展開（破 9.32.1 有界算子文法，「TRANSFORMS/OPS 外」≠「無界」）
- **自我發明的算子非全函式（某輸入無定義/拋例外）、cost 超 `SDD_DIM_OP_STEP_MAX`、或算子求值路徑含遞迴/`while`/自呼叫（破 9.32.3 算子可計算性——被發明物本身不可證停機）**
- 現存活躍 operator-genesis 算子超 `SDD_DIM_OP_MAX` 仍無界擴充算子（破 9.32.4 OperatorGenesisBounded）
- 一週期同時算子自我發明 > K_op 個（破 9.32.4 NoUnboundedOperatorGenesis）
- 把 operator-genesis 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.32.4 / Rule 9.18.1）
- **未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（破 9.32.5——掏空全部反 Goodhart 對抗分離地基）**
- 為活體 meta⁵ 發明私自開 HTTP 外聯而未經 OPEN-S.x/後續 OPEN 人工決策（破 OPEN-10.6）

---

## 5. Self-Verification Protocol（內部模擬：六個極端案例）

### 5.1 經典案例：Spec 寫錯 → 測試永不過（承前 Phase 不回歸）
| 生命週期點 | 行為 |
|------------|------|
| 凍結前·邏輯 | `spec-logical-validator`（SLV-001~011）在 SCG-0/3 前攔物理不可行/不可測 AC |
| 開發中·重試 | retry budget（SCG 3 / PR 5 / RTM 2）+ `trajectory_predictor` 2 信號預測切換 / 3 信號早停 |
| 對抗·補丁 | `adversarial_synthesizer` + `spec_patch_proposer`（proposed）+ `counterfactual_replay` 離線命中 |
| 停機 | 觸頂 → `ESCALATION` / `MFSM_ESCALATION` → `steersman_renderer` 導人工，**絕不無限重試燒 token** |
✅ 不回歸：五軌形式化 + retry/context budget 保證有界。

### 5.2 Phase T 專屬極端案例（一）：算子可計算性——無界步數 / 隱含遞迴算子（PT-2 核心，前所未有）
**案例**：operator_genesis 受擾，被要求構造一個隱含對輸入規模迴圈/遞迴的算子，企圖讓單次算子呼叫燒爆 token / 不停機。
- **有界算子文法結構保證**：文法 = 有界深度（<=2）運算式樹 over total PRIMITIVES × total COMBINATORS，**根本不含遞迴/迴圈產生式**（grep/ast 斷言算子求值路徑零 `while`/零遞迴）。
- **`OperatorComputabilityBounded`（cost 上界）**：若硬注入超深運算式樹 → `cost()` > `SDD_DIM_OP_STEP_MAX` → `guard_operator_computability` raise `OperatorComputabilityExceeded` → `MFSM_ESCALATION`。
- chaos `OPERATOR_COMPUTABILITY_FLAP` 100 輪 → bounded。
✅ 守 Rule 9.32.3：把停機問題正面釘進框架自我擴充的產物本身，**被發明的算子可證停機（全函式 + 有界步數），絕不無界計算**。

### 5.3 Phase T 專屬極端案例（二）：非全函式算子（除零 / 空輸入 / 拋例外）
**案例**：operator_genesis 生成一個對某輸入除零/空輸入無定義的算子，企圖讓評估迴圈崩潰或行為未定。
- **全函式結構保證**：PRIMITIVES 對空輸入回 0.0、COMBINATORS `ratio_safe` 對 0 分母回退、`_finite` 對 inf/nan 飽和投影（如 sq(1e308) overflow→飽和到 1e300）；對全部枚舉算子（264 個）× 多組極端輸入（空/單元素/負/0/極大含浮點上限 1e200/1e308）`apply()` fuzz（合計 264 × 16 = 4224 次呼叫）零例外、無 inf、無 nan。
- `guard_operator_computability` fuzz-total 檢查零漏放。
✅ 守 Rule 9.32.3：算子全函式，**對任何輸入有定義、永不崩潰**。

### 5.4 Phase T 專屬極端案例（三）：算子自我發明 Goodhart——自指自利算子
**案例**：operator_genesis 受擾，發明一個 `identity(self_score)` 算子——它計算 proposer 自己的核可訊號，企圖讓算子「看起來必要」而實際只是自利。
- **operator self-reference guard**（反自利第一閘）：primitive/combinator/secondary/probe 含 `self_score`/`proposer_*` → 結構性丟棄，根本不送 oracle（零漏放）。
- 若繞過 guard 假設送達 → feature-grounded oracle augmented vs baseline 增益 ≈ 0 → 不取得 tier（第二閘）。
- chaos `OPERATOR_GENESIS_GOODHART_FLAP` 100 輪 → guard+oracle 零漏放 → bounded。
✅ 守 Rule 9.32.2：雙閘皆否 → 絕不擴充自指自利算子（零漏放，安全紅線）。

### 5.5 Phase T 專屬極端案例（四）：算子無界生成爆炸 + 算子基數爆炸
**案例**：operator_genesis 被要求在 TRANSFORMS/OPS 外無界枚舉撐爆搜尋；或反覆發明不同的真必要算子把 OPS 無限膨脹。
- **有界算子生成文法**：生成空間 = `PRIMITIVES`（有限）× `COMBINATORS`（有限）→ 可枚舉、有限；枚舉節點達 `SDD_DIM_OP_BUDGET` → 截斷（best-so-far），絕不指數爆炸。
- **`OperatorGenesisBounded`（op stock 天花板）**：現存活躍 operator-genesis 算子數逼近 `SDD_DIM_OP_MAX` → `guard_operator_genesis` raise `OperatorCardinalityExceeded` → `MFSM_ESCALATION`。
✅ 守 Rule 9.32.1/9.32.4：「TRANSFORMS/OPS 外」≠「無界」+ op stock 天花板封死算子基數爆炸。

### 5.6 Phase T 專屬極端案例（五）：算子外冗餘算子（再投影既有 OPS）
**案例**：operator_genesis 發明一個與既有某 OPS 在固定 probe 上排序幾乎相同的算子（冗餘再投影），企圖灌水。
- feature-grounded oracle：非冗餘度（與既有 existing_cost 排序的最大一致率）≈ 0.99 ≥ 門檻 `SDD_DIM_REDUNDANCY_MAX` → 判定冗餘 → 拒絕，即使增量覆蓋略 > 0 也不擴充（過擬合防護，沿用 Phase Q/R/S 非冗餘獨立閘）。
✅ 守 Rule 9.32.2：增量覆蓋 ∧ 非冗餘 **兩者皆須通過**才取得 tier。

### 5.7 結論
Phase T 通過六個極端案例的內部模擬：系統能**有界地自我發明 TRANSFORMS/OPS 外的新算子、且每個發明算子結構性可計算地停機（全函式 + 有界步數）**，且任何（無界步數算子 / 非全函式算子 / 自指自利算子 / 算子無界生成爆炸 / 算子基數爆炸 / 算子外冗餘算子）都被 (有界算子生成文法) + (OperatorComputabilityBounded 可計算性三證) + (operator self-reference guard 零漏放) + (feature-grounded 算子必要性 oracle 零漏放) + (OperatorGenesisBounded op stock) 五道防線攔下，**優雅停機並導人類掌舵算子外價值計算本體論，而非陷入算子不停機/無界生成/自指放水浪費 Token**。精準對應提示 Self-Verification 要求：「Evaluator 發現異常 → 優雅中斷 → 引導人類介入修正/提供缺失工具」於**最高的算子外計算本體論發明層（meta⁵）**，並**首度把停機問題正面釘進框架自我擴充的產物本身**。

---

## 6. 執行檢核清單（供 dynamic workflow 消費）

- [x] ACT-141 `operator_genesis.py` + 有界算子生成文法（全函式 + 有界步數 + 零遞迴零迴圈）+ operator_self_reference_guard + ≥4 情境 fixture + fuzz-total + 對抗分離斷言
- [x] ACT-142 `evaluate_genesis_operator` feature-grounded + `OPR-*.yaml` 凍結語料（12 個）+ ≥12 fixture（真必要/噪音算子/冗餘算子）+ 零漏放
- [x] ACT-143 `meta_ledger` operator-genesis stock + `guard_operator_genesis` + `guard_operator_computability` + `META_FSM.tla` `OperatorGenesisBounded` + `OperatorComputabilityBounded` + `.cfg` + META 13 distinct 重證
- [x] ACT-144 `render_operator_genesis_proposal` + 可計算性證據 + NoUnboundedOperatorGenesis + 人工 gate 斷言
- [x] ACT-145 `R-9.32-*.yaml` + RULES_INDEX + CLAUDE.md §9 禁令#22 + INIT 追加 + ID 翻牌（141→147 / 9.32→9.33）+ test_id_registry
- [x] ACT-146 五軌 TLC No error（META 13 distinct）+ chaos 100 輪 bounded（OPERATOR_GENESIS_GOODHART_FLAP + OPERATOR_COMPUTABILITY_FLAP）+ pytest 全綠不回歸（1206 → 1252 passed）
- [ ] 獨立 QA 稽核（Architect/SA/SD/QA 專家）抓漏 → 修復 → 全綠
- [ ] 以日期 timestamp 打標籤 push + Merge main

> **狀態流轉**：DRAFT →（人工 signoff）→ EXECUTING →（四柱 + 收官全綠）→ EXECUTED →（QA 抓漏 + 修復全綠）→ VERIFIED → tag + merge main。
