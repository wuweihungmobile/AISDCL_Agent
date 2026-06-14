# SDD_improving_Automation_21 — Phase U 藍圖（meta⁶）

**主題**：**組合算子文法的自我擴充（meta⁶）**——把 Phase T 只能「在**固定算子字母表**（`operator_genesis.PRIMITIVES` 8 條硬編：mean/max/min/sum/range/median/mad/last；`COMBINATORS` 9 條硬編：identity/abs/neg/clip01/sq + diff/ratio_safe/max2/min2）之上自我發明 TRANSFORMS/OPS 外的新算子」的能力，推進到「系統能**自我發明一個 `PRIMITIVES`/`COMBINATORS` 字母表裡根本沒有的全新原始算子/組合算子（= 擴充算子生成文法的字母表本身）**」。並正面納管「字母表外生成」憑空長出、Phase T（固定字母表）不存在而 Phase U 才出現的**新危害類別：(i) 可計算性閉包危害（ComputabilityClosure，本 Phase 靈魂）——Phase T 的「每個算子全函式 + 有界步數」之所以成立，是因為字母表 `PRIMITIVES`/`COMBINATORS` 本身被人類凍結、逐條證過全 total + O(n) + cost-1；一旦讓系統自我發明字母表元素，「可計算性」必須由『單一算子可證停機』升級為『擴充字母表後，文法所生成的**整個（仍有限的）算子代數中每一個算子**都仍全函式 + 有界步數』的**閉包性質**——這是「圖靈完備 vs 保證停機」第一次反噬到框架自我擴充的**生成規則本身（meta⁶）**而非僅其產物；(ii) 字母表無界生成爆炸（`PRIMITIVES`/`COMBINATORS` 外不再有 8+9 條硬編上界）；(iii) 字母表自我發明 Goodhart（發明一個 base-reducer/post-map/binary-op 計算自己核可訊號的自指字母表元素）**。
**目標等級**：L10 完整 · 離線活體 meta⁵ 迴圈「轉換算子文法自我擴充」切片（Phase T 已達：在固定字母表上自我發明算子 + 算子可計算性）→ **L10 完整 · 離線活體 meta⁶ 迴圈「組合算子文法自我擴充」切片**（系統不只能在**有限字母表**上自我發明算子，更能在**可證有界、可證可計算閉包（擴充後整個算子代數仍全函式 + 有界步數）、反自利、人類掌舵本體論**的前提下，**自我發明 `PRIMITIVES`/`COMBINATORS` 字母表外的全新原始算子/組合算子**，重構它「用什麼**運算字母表**去生成它用來量在乎之事的算子」的計算生成本體論）。
**建立日期**：2026-06-04
**前置基線**：Phase T 完整（ACT-141~146 / R-9.32，pytest 1252 passed / 4 skipped / 34 deselected〔chaos〕/ 14 subtests；五軌 TLC 全 No error：`SDD_FSM` 42 reachable / 831 TLC distinct、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `OPERATOR_GENESIS_GOODHART_FLAP`+`OPERATOR_COMPUTABILITY_FLAP`，算子自我發明 Goodhart 零漏放、算子可計算性〔全函式 + 有界步數〕有界停機）
**OPEN-10.6 承接**：續承 OPEN-T.x / OPEN-S.x / OPEN-R.x / OPEN-Q.x / OPEN-O.7 / OPEN-M.7 / OPEN-P.7——**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。故 L9 完整（活體 canary/shadow）與**活體 meta⁶ 元迴圈**續列 horizon；**Phase U 與 Phase N/O/P/Q/R/S/T 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（組合算子文法自我擴充）**。Phase T §3.4 明示「組合算子文法（meta⁶：自我擴充 PRIMITIVES/COMBINATORS 集合本身）」為其自陳 horizon，故本份維持離線等價切片，活體版列 horizon（OPEN-U.x 承前）。**自我發明評估器（meta-oracle 自演化）續列最高 horizon**——它自指地破壞所有 Phase 賴以成立的「對抗分離地基」，採納它須先有更強的對抗分離不可繞過性證明（見 §0 thinking 三末、§3.4）。
**狀態**：✅ **使用者規格 Signoff（2026-06-04，GitHub Issue #8）→ EXECUTING**。本份依使用者執行要求「先完成 TLA+ 形式化證明並確保五軌 TLC 全綠，再撰寫 Python 執行層」。徵用 **ACT-147~149 與 Rule 9.33**（取自 [`governance/ID_REGISTRY.yaml`](../../../governance/ID_REGISTRY.yaml) `next_free` = act 147 / rule 9.33，單調取號）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase T §3.4 自陳 horizon「組合算子文法（meta⁶：自我擴充 PRIMITIVES/COMBINATORS 集合本身，涉及更深的可計算性閉包證明）」續推。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 147 / rule 9.33）：
> 本藍圖徵用 **ACT-147~149 與 Rule 9.33**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **收官（ACT-149）獲人工 signoff 並執行至全綠時**，才由 `id_registry` 翻牌（act 147→150 / rule 9.33→9.34）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase U？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~T 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~T、是自陳「L10 完整 + 離線活體 meta⁵ 迴圈（轉換算子文法自我擴充 + 算子可計算性）」的成熟框架。盲目重述提示前沿清單只會重造輪子（Phase K~T 已逐項對賬為 100% 落地）。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase U 是否仍成立；(2) 誠實判斷「組合算子文法的自我擴充」到底是**Phase T 的換皮**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase U 把監督者的涵蓋面從「在固定字母表上自我發明算子」擴到「自我發明字母表元素本身」，且首次面對『被發明物是生成『可執行計算』的『生成規則』』的閉包停機問題】
Phase O~T 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase T 的貢獻是把「TRANSFORMS/OPS 外的算子自我發明（有界算子生成文法 + 算子可計算性〔全函式 + 有界步數〕+ 算子自指 probe 守門）」拉進基質 B，**首度把停機問題正面釘進框架自我擴充的產物（被發明的算子）本身**。

但 Phase T 誠實標定了它的算子生成文法**鎖在一個固定的字母表 `PRIMITIVES`/`COMBINATORS`**（`operator_genesis.PRIMITIVES` 8 條硬編、`COMBINATORS` 9 條硬編），系統只能在「這 8+9 個字母」之上**組合**算子——它**換不出字母表上沒有的新『運算字母』**。Phase T 把這件事列為 horizon（§3.4）：**組合算子文法（meta⁶，自我擴充 PRIMITIVES/COMBINATORS 集合本身，涉及更深的可計算性閉包證明）**。這裡藏著一個**被 Phase T 一句帶過、實際上是質變而非量變、且比 Phase T 更逼近停機問題核心的命題**：

**Phase T 的「每個被發明算子全函式 + 有界步數」之所以成立，其證明的**地基**是『字母表 `PRIMITIVES`/`COMBINATORS` 本身被人類凍結、逐條手證過全 total + O(n) 單遍 + cost-1』。** Phase T 的算子 `apply()` 之所以恆停，是因為它呼叫的每個 `_prim`/`_comb` 都是人類寫死的全函式。**Phase U 第一次讓系統自我發明字母表元素——等於讓系統自己寫『會被嵌進每一個未來算子裡反覆執行的最底層計算原子』。** 這把可計算性問題從『一個算子可證停機』升級為一個**閉包命題**：
- 字母表外生成的危害不在於『某一個算子不停』（Phase T 已封），而在於：**一個被自我發明、加進字母表的原始算子/組合算子，會被算子生成文法用來生成『整個算子代數』裡的每一個算子**。若這個新字母元素本身非全函式 / 非 O(n) / 隱含遞迴，它會**污染整個由它生成的算子代數**——Phase T 的 `guard_operator_computability`（逐算子查 cost + fuzz）對「**字母表元素本身的可計算性、以及它對整個生成代數的閉包影響**」**結構性盲目**（因為 Phase T 的字母表全是人類寫死、根本沒有這個問題）。
- 這正是「圖靈完備 vs 保證停機」這條 Phase O~T 反覆援引的核心命題，**第一次反噬到框架自我擴充的『生成規則本身（meta⁶）』而非僅其產物**：你敢讓系統發明自己的運算字母表，就**必須證明擴充後文法生成的整個（仍有限的）算子代數中、每一個算子仍是可判定地停機的**——這是一條**閉包（closure）性質**，不是逐個產物的檢查。否則「把不可判定 LLM 包進可判定監督者」的整套地基，會因為「監督者的算子生成文法開始用 LLM 發明的、可能不可判定的字母原子去生成它的全部算子」而被從**生成規則的根部**蛀空。

這正是 Phase U 必須納管的、Phase T 尚未碰、且**比 Phase T 更逼近停機問題本質（從『產物可證停機』到『生成規則的閉包可證停機』）**的新東西——使用者在 Issue #8 稱之為 **ComputabilityClosure（全函式與有界步數閉包）**。

【一、誠實判斷：組合算子文法自我擴充是「Phase T 換皮」還是「有真缺口」？——用 grep 接地】
我先確認框架目前的算子字母表**鎖死在固定集**（grep `^PRIMITIVES` / `^UNARY_COMBINATORS` / `^BINARY_COMBINATORS` on `operator_genesis.py` 實測皆為硬編 tuple，無任何「字母表生成 / 字母表發明 / 可計算性閉包」路徑）。再 grep 三組關鍵字證明零實作：
| 關鍵字 | grep 範圍 | 命中 |
|--------|-----------|------|
| `alphabet.*genesis\|AlphabetGenesis\|invent.*primitive\|InventedPrimitive\|InventedCombinator\|expand.*alphabet` | `tools/` | **零** |
| `computability.*closure\|ComputabilityClosure\|closure.*bounded\|guard_computability_closure` | `tools/` | **零** |
| `ATOM_REDUCERS\|POST_MAPS\|BINARY_ATOMS\|alphabet.*grammar` | `tools/` | **零** |

→ **組合算子文法的「自我擴充」目前零實作；系統被鎖在固定 8+9 個字母表元素內。** 真正的價值不在於「再加一個 alphabet grammar」（那是 Phase T 換皮），而在於：**字母表外生成會打開三個 Phase T 結構性攔不住的新攻擊面，其一是比 Phase T 更深的停機危害——可計算性『閉包』**：
- **可計算性閉包危害（meta⁶ 的靈魂，前所未有）**：自我發明的字母表元素會被文法用來生成**整個算子代數**；若它非全函式 / 非 O(n) / 隱含遞迴，它污染的不是一個算子而是**所有由它生成的算子**。Phase T 的逐算子 `guard_operator_computability` 對「字母表元素本身 + 它對整個生成代數的閉包影響」**完全盲目**。← 這是 Phase U 的 **PU-2 的核心**（真缺口，且是停機問題的閉包升級）。
- **字母表無界生成爆炸 + 字母表自我發明 Goodhart**：字母表生成**沒有 8+9 條硬編上界**；且系統可發明一個「**字母原子本身就計算 proposer/oracle/自評內部信號**」的自指字母元素，讓自我發明的字母表「看起來必要」實際只是自利。Phase T 的 feature-grounded oracle 評的是**現場發明算子在既有字母表算出的特徵向量上的增量覆蓋**——它對「一個**字母表外、用一個事先沒見過的新運算原子去聚合**的字母元素到底必不必要、是不是自指自利」**完全盲目**。← **PU-1 的另兩面**。
- **字母表外生成的計算生成本體論掌舵真空**：`steersman` 只渲染「固定字母表上自我發明的算子」與「算子可計算性證據」；無人渲染「系統**現場發明了一個字母表外的新原始算子/組合算子、它的字母表生成文法來源（憑什麼有界）、它憑什麼維持可計算性閉包（擴充後整個算子代數仍全函式 + 有界步數的閉包證據）、它憑什麼必要且非自指**」。人類掌舵在「字母表外計算生成本體論發明層（meta⁶）」缺席。← **PU-3**。

【二、用提示三個指定漏洞視角，逐一往 Phase T 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在 meta⁶ 層缺「字母表外發明的可有界、**可計算性閉包（擴充後整個算子代數全函式+有界步數）**、可反自利、feature-grounded 驗證」這一層。
Phase T 的 `operator_genesis`（生成，固定字母表上組合算子）↔ `dimension_necessity_oracle.evaluate_genesis_operator`（評估，feature-grounded）是一對 meta⁵ GAN，但**它只評在固定字母表上組出的算子**。當系統**現場發明一個字母表外的新運算原子**，**(1) 誰保證這條字母表生成不會無界爆炸？(2) 誰保證擴充字母表後，文法生成的整個算子代數仍每個都會停（可計算性閉包）？(3) 誰判「這個現場發明的字母元素到底必不必要、是不是自指自利」？** 目前無人。提示要的「生成-評估分離 + 主觀標準量化」推到 meta⁶ 層，型態是：**(1)** 生成必須被一條**有界字母表生成文法**封住——「PRIMITIVES/COMBINATORS 外」不等於「無界」，而是「在一個**有限原子歸約器 `ATOM_REDUCERS` × 有限後變換 `POST_MAPS`（生成新 primitive）+ 有限二元原子 `BINARY_ATOMS`（生成新 combinator）**的可枚舉生成空間裡生成新字母元素」，節點 <= `SDD_DIM_ALPHABET_BUDGET`；**(2)**（最關鍵、前所未有）字母表生成文法必須**結構性保證可計算性閉包**——每個生成的 primitive 結構性為 total `ATOM_REDUCERS`（皆 O(n) 單遍累積、零遞迴零迴圈、cost-1）∘ total `POST_MAPS`（皆 total 純量後變換）、每個生成的 combinator 結構性為 total `BINARY_ATOMS`（皆 total、有界元數、cost-1），故**擴充字母表後，算子生成文法產出的每個算子的計算步數 `cost()` 仍結構性 <= 常數 <= `SDD_DIM_OP_STEP_MAX` 且全函式**——**這是「可計算性閉包需另證有界」的正面兌現：把字母表刻意設計成一個『total + bounded-step 的算子生成在其上封閉』的有限代數，讓被發明的字母元素生成的整個算子代數可證停機，而整個閉環仍靠 LLM+紙帶維持圖靈完備**；**(3)** 評估升級為**對字母表元素（不靠字母名、靠在固定參照 probe 上用它生成的算子的真實計算結果）的 feature-grounded 字母表必要性 oracle**——量「以這個新字母元素生成的算子在固定 probe 上聚合，是否帶來既有字母表全算子都拿不到的增量覆蓋 ∧ 非冗餘」；外加一道**字母表級自指守門**（反自利：字母元素的 reducer/map/op/probe 引用保留自指信號 → 結構性拒絕，零漏放）。→ **PU-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「可計算性閉包（ComputabilityClosure）」是一條 Phase T 不存在、直接源自「被發明物是『生成可執行計算的生成規則』而非『一個可執行計算』」的最深層停機缺口。
這是 Phase U 最深、也最切題（提示明列「停機問題與防護」）的缺口。Phase T 的被發明物是「一個算子」（一段可執行計算），它的可計算性是**逐個產物**檢查。Phase U 的被發明物是「字母表元素」=「**會被文法用來生成每一個算子的最底層運算原子**」=**生成規則的零件**。新病態：一個非 total / 非 O(n) / 隱含遞迴的字母原子，被文法用後會生成**整代數的壞算子**。新閉包危害：**(i) 字母元素非全函式**（某輸入無定義 → 它生成的每個算子都崩）；**(ii) 字母元素無界步數**（O(n²) / 隱含迴圈 → 它生成的每個算子單次呼叫就燒爆）；**(iii) 閉包破裂**（擴充字母表後，某些原本 cost<=3 的算子組合變成 cost 超界）。這是 Phase T（字母表全人類寫死全 total）時不可能、字母表自我發明才出現的閉包停機危害。→ 需要一條**可計算性閉包有界停機不變量** `ComputabilityClosureBounded`：(a) **字母元素結構性可計算**——invented primitive = total `ATOM_REDUCERS`（O(n) 單遍、零遞迴零迴圈）∘ total `POST_MAPS`，invented combinator = total `BINARY_ATOMS`（有界元數），故每個字母元素自身 total + cost-1；(b) **閉包驗證**——採納前 `guard_computability_closure` **枚舉擴充字母表後文法生成的整個（仍有限、<= budget）算子代數，斷言每個算子 fuzz-total（零例外、無 NaN/inf）∧ cost() <= `SDD_DIM_OP_STEP_MAX`**，觸發即 `ComputabilityClosureViolation` → `MFSM_ESCALATION`；(c) **零遞迴零迴圈結構保證**——字母表生成文法不含任何遞迴產生式 / 迴圈原子（grep/ast 斷言 `operator_alphabet_genesis.py` 字母求值路徑無 `while`/遞迴/自呼叫）。**這正補上 Phase T 的逐算子 cost / fuzz 對「字母表元素本身 + 它對整個生成代數的閉包」全盲的最深缺口。** ← **PU-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『固定字母表上的算子發明 + 算子可計算性』，缺『字母表外發明 diff（meta⁶）+ 可計算性閉包證據』」。
Phase T 的 `render_operator_genesis_proposal` 渲染**固定字母表上**發明的算子 + 逐算子可計算性證據。字母表自我擴充後，若系統現場發明一個字母表外的新運算原子，人類面對的是「一個從未見過的新運算字母 + 它會生成整個算子代數」——**沒有人渲染『這個字母元素是系統怎麼從有限字母表生成文法生成出來的、它有界嗎、它維持可計算性閉包嗎（擴充後整個算子代數仍全函式 + 有界步數）、它自指嗎、它憑什麼必要』**。提示反覆強調「人類維持設計環境掌舵者高度，而非降級為編碼員」——在「字母表外計算生成本體論發明（meta⁶）」層，掌舵的最高形態是**人類能一眼看懂『系統憑空發明了哪個新運算字母、它的有界字母表生成來源 + 可計算性閉包證據（擴充後整個算子代數 total + cost<=step_max）+ 反自利證據 + 必要性勝率』，且系統在結構上不可能自動 commit 任何字母表自我發明（每週期至多 K_alpha=1 個字母發明、每個必經人工 signoff）**。→ **PU-3**（字母表外計算生成本體論發明掌舵介面 + `NoUnboundedAlphabetGenesis`，K_alpha=1，承 Phase T K_op=1）。

【三、停機問題紅線覆查——本份比 Phase T 更危險，因為納管的是「會憑空發明自己的運算字母表（=自己寫生成每個算子的最底層計算原子）的迴圈」】
Phase T 的反諷（讓系統自我發明它的算子）在 Phase U 升級為「讓系統**憑空發明自己的運算字母表（自己寫生成規則的零件）**」。有界性與防自利必須再加固，且**首度必須證明被發明的『生成規則零件』維持整個生成代數的可計算性閉包**：
- **仍不新增形式化軌（承 Phase O/P/Q/R/S/T「重用 META_FSM、不增軌」的成熟示範）**：字母表自我發明的採納/退役全部註冊為 `META_FSM` 既有的指紋命名空間（字母用新增 `alphabet-genesis:` 命名空間），其 add↔retire churn 由**同一條** `ChurnBounded`/`GraduationRatchet` 涵蓋。**但 PU-1/PU-2 揭示：churn 仍不夠**，故必須**對既有 `META_FSM` 再補兩條不變量**：`AlphabetGenesisBounded`（字母表基數 stock 天花板）+ `ComputabilityClosureBounded`（可計算性閉包：擴充後整個算子代數 total + 有界步數）——關鍵是**沿用 Phase P/Q/R/S/T 對 `CrossScorerChurnBounded`/`DimensionCardinalityBounded`/`SwapCadenceBounded`/`VocabGenesisBounded`/`BatchSwapCadenceBounded`/`OperatorGenesisBounded`/`OperatorComputabilityBounded` 的誠實作法：只新增 INVARIANT、不新增狀態變數**（`META_FSM` 維持 `<<mstate, churn, cap>>` 三變數 / 13 distinct，TLC 仍 No error，五軌不回歸；字母 stock 與可計算性閉包的緊語意由 runtime `guard_alphabet_genesis`/`guard_computability_closure` + chaos `ALPHABET_GENESIS_GOODHART_FLAP`/`COMPUTABILITY_CLOSURE_FLAP` enforce/驗收，形式化層誠實標註為「single-counter 抽象之歸約引用」）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PU-1 的有界字母表生成文法是硬約束，非建議**：字母表自我發明的搜尋**必在有限字母表生成文法（有限 `ATOM_REDUCERS` × 有限 `POST_MAPS` + 有限 `BINARY_ATOMS`）內可枚舉**，節點 <= `SDD_DIM_ALPHABET_BUDGET`（clamp[8,128]，預設 32）。**PU-1 的反自利是雙閘**：(a) 字母表自我發明的 necessity tier **唯一合法來源仍是 generator 全體碰不到、content-hashed 凍結的 feature-grounded 字母表必要性 held-out 勝率**（增量覆蓋 ∧ 非冗餘）；(b) **字母表級自指守門**——任何 reducer/map/op/probe 引用保留自指信號的字母元素，在送 oracle 前即被 `alphabet_self_reference_guard` 攔下（零漏放）。`operator_alphabet_genesis` **結構性不 import oracle、不讀必要性語料**（ast/import 隔離斷言，承 Phase T）。
- **PU-2 的可計算性閉包是「字母元素結構性可計算 + 閉包枚舉驗證 + 零遞迴零迴圈結構」三證**：字母元素由 total 原子組成；採納前 `guard_computability_closure` **枚舉擴充字母表後文法生成的整個算子代數，斷言每個算子 fuzz-total ∧ cost <= step_max**。觸發 `ComputabilityClosureViolation` → `MFSM_ESCALATION`。**這是把停機問題正面釘進框架自我擴充的『生成規則本身』的形式化兌現（從 Phase T 的『產物可證停機』升級為 meta⁶ 的『生成規則的閉包可證停機』）。**
- **PROPOSED-only + 反 big-bang 字母發明，人類掌舵推到「字母表外計算生成本體論發明（meta⁶）」層**：每週期至多 **K_alpha=1** 個字母自我發明可進 proposed-pending-signoff（`NoUnboundedAlphabetGenesis`，承 Phase T K_op=1），每個必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4 / 9.30.4 / 9.31.4 / 9.32.4）。`steersman_renderer` 渲染「字母表外計算生成本體論發明 diff（系統憑空發明哪個運算字母 + 字母表生成文法來源 + 可計算性閉包證據〔擴充後整個算子代數 total + cost<=step_max〕+ 反自指證據 + 必要性勝率）」，讓人類**不讀程式碼就能掌舵整個系統的算子生成字母表本體論發明**。
- **自我發明評估器（meta-oracle 自演化）續列最高 horizon、本份明確不做**：Phase U 把生成端（字母表）拉進基質 B，但**評估端（必要性 oracle）仍由人類凍結**。「讓系統自我演化它的評估器本身」會讓 generator 與 evaluator 收斂到同一基質——這**自指地破壞 Phase O~U 全部反 Goodhart 保證所賴以成立的『對抗分離』地基**（生成者不可碰評估者的尺規）。採納它須先有更強的「對抗分離不可繞過性」形式化證明（例如一個 evaluator-of-evaluators 的、generator 全體碰不到的更高階 held-out meta-corpus + 其本身的反自利證明），這超出本份範圍，明確列為 §3.4 最高 horizon。

【四、上下文衰減（Context Degradation）視角覆查】
- 字母表生成文法枚舉、feature-grounded 字母表必要性 held-out 重放、可計算性閉包枚舉驗證全在**隔離邏輯/落盤**進行，主線只在收到 proposed 字母發明時讀「字母表外發明 diff + 可計算性閉包證據 + 必要性勝率摘要」。字母帳本**沿用** Phase T 的 `value-dimension-ledger.yaml`（增 `alphabet_inventions` 領域審計段）+ 共用 Phase L 的 `meta-loop-ledger.yaml`（churn/alphabet-cardinality 治理），**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- feature-grounded 字母表必要性 oracle 重用既有 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物（字母發明帳本 / 字母必要性勝率表 / 字母外發明 diff 報告）皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性 / 單一真實來源）：把「系統如何從有限字母表生成文法**憑空發明一個 PRIMITIVES/COMBINATORS 外的新運算字母**」「它的字母表生成來源、**可計算性閉包證據（擴充後整個算子代數全函式 + 有界步數）**、反自指證據、凍結必要性證據」全部落地為 **Markdown/YAML 可推理產物**——**讓「系統如何發明它『用什麼運算字母去生成它的算子』、以及它如何證明那套字母表生成的整個算子代數一定會停」成為 AI 與人類都可直接推理、可審計的單一真實來源**，而非藏在 8+9 條硬編字母的天花板裡。以漸進式揭露重構知識（字母帳本落盤、按需 lazy 讀），守 `docs/` 作為地圖。
- Anthropic（生成-評估分離 / 評估器實體操作 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「固定字母表上發明算子」（T）推到**「字母表外字母自我發明」**（meta⁶）——生成端用**有界字母表生成文法**把無界字母空間歸約為有限可枚舉、且**結構性維持可計算性閉包（擴充後整個算子代數 sub-Turing：全函式 + 有界步數）**，評估端用 **feature-grounded 字母表必要性 oracle + 字母表自指守門**專攻「字母表自我發明 Goodhart / 自指自利字母」；評估器在**凍結 held-out 現實代理語料上實際以新字母生成的算子計算、量客觀增量覆蓋**（對應提示「賦予 Evaluator 實體操作能力」於離線等價層）；並再次以「不增第六軌、只補 META_FSM 兩條不變量」示範「大膽移除冗餘鷹架」。你敢讓系統憑空發明它的運算字母表（自己寫生成規則的零件），就得能形式化證明這條字母發明迴圈仍會停（字母生成有界 + 擴充字母表後整個算子代數可計算地停機）、且新字母不會在自指守門裡給自己發明一個「計算自己核可」的字母。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~T 落地元件**（對賬見上 thinking 一節），七條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O 的 obj-profile、P 的全評分器 calibration、Q 的 value-dimension、R 的 self-invention/swap、S 的 vocab-genesis/batch-swap、T 的 operator-genesis〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase U 的價值在用提示三漏洞視角挖出 Phase T 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase T 全程在「固定的 8 條 PRIMITIVES + 9 條 COMBINATORS 字母表」上自我發明算子；讓系統自我發明一個字母表外的全新運算字母，會憑空長出 Phase T（固定字母表）時不存在的『字母表外生成』新危害——尤其是比 Phase T 更逼近停機問題本質的『可計算性閉包危害』（被發明物第一次是『會被用來生成每一個算子的生成規則零件』而非『一個算子』），以及字母表無界生成爆炸、字母表自我發明 Goodhart（自指自利字母）。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PU-1** | **系統被鎖在固定 8 PRIMITIVES + 9 COMBINATORS 內，無「字母表外字母自我發明」路徑；且 feature-grounded 字母表必要性驗證缺席**——系統無法發明一個字母表外的全新運算字母，即使硬發明也無 (i) 有界字母表生成文法、(ii) feature-grounded 字母表必要性 oracle、(iii) 字母表級反自利守門。提示「生成-評估分離 + 主觀標準量化」在 **meta⁶（字母表外發明）** 層缺席。 | `alphabet.*genesis\|InventedPrimitive\|InventedCombinator\|ATOM_REDUCERS\|POST_MAPS` **零命中** |
| **PU-2** | **缺『可計算性閉包』有界停機——比 Phase T 更深的停機缺口**——Phase T 的逐算子可計算性建立在「字母表本身人類寫死全 total」前提；Phase U 的被發明物是「字母元素」=「會被文法用來生成整個算子代數的生成規則零件」，一個非 total / 無界步數的字母元素污染的是**整代數**。逐算子 cost / fuzz 對「字母元素本身 + 它對整個生成代數的閉包」全盲。這是「圖靈完備 vs 保證停機」第一次反噬到框架自我擴充的『生成規則本身』。 | `computability.*closure\|ComputabilityClosure\|guard_computability_closure` **零命中** |
| **PU-3** | **缺『字母表外發明 diff（meta⁶）+ 可計算性閉包證據』掌舵介面**——`steersman` 只渲染固定字母表上的算子發明與逐算子可計算性；無人渲染「系統憑空發明哪個運算字母 + 字母表生成文法來源 + 可計算性閉包證據（擴充後整個算子代數 total + cost<=step_max）+ 反自指證據」。人類掌舵在「字母表外計算生成本體論發明層（meta⁶）」缺席。 | `render.*alphabet\|NoUnboundedAlphabetGenesis` **零命中** |

**三缺口的共同主軸**：Phase T 讓人類站上「審系統在固定字母表上自我發明算子 + 算子可計算性」的高度，但**框架的算子生成其實只能用一張『8+9 個運算字母的硬編字母表』**。Phase U 把人類抬到最高層——審「系統如何從**有界字母表生成文法**憑空發明一個**字母表外的全新運算字母**（憑什麼有界、**憑什麼擴充後整個算子代數一定會停（可計算性閉包）**、憑什麼非自指自利）」——這正是 L10 完整「離線活體元迴圈」的**組合算子文法自我擴充（meta⁶）**切片，精準補上提示在「狀態轉換（字母表外生成-評估聯合合約）」「**停機問題（可計算性閉包——把停機問題正面釘進自我擴充的生成規則本身）**」「動態演進（字母表外發明計算生成本體論而非只在固定字母表組合）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase U 增量）

Phase U 對狀態機的改動延續 Phase O/P/Q/R/S/T 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42 reachable / 831 TLC distinct）；**仍不新增第六條形式化軌**——字母表自我發明本質上**是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「TRANSFORMS/OPS 外發明的算子」泛化為「**PRIMITIVES/COMBINATORS 外現場發明的運算字母**」（meta⁶）。**重用既有 `META_FSM`** 並**僅補兩條不變量** `AlphabetGenesisBounded` + `ComputabilityClosureBounded`（不增狀態變數），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PU-1/PU-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌、無新狀態變數）

| 元件 / 形式化層 | 命名空間 | 類型 | 入口 | 出口 | 阻塞? |
|------|------|------|------|------|-------|
| `operator_alphabet_genesis`（PRIMITIVES/COMBINATORS 外字母自我發明骨架；有界字母表生成文法〔可計算性閉包〕+ 字母自指守門） | runtime（落 `value-dimension-ledger.yaml` `alphabet_inventions` 段） | 生成器骨架（advisory） | 跨 session 收官 / `MEMORY_CONSOLIDATION` 旁路 | 產 `proposed` 字母發明（only 透過注入 evaluate 取必要性，無自評；字母自指守門 + 可計算性閉包結構性保證） | 否 |
| `dimension_necessity_oracle`（**新增 feature-grounded `evaluate_genesis_alphabet`**） | runtime（重用 `counterfactual_replay` 重放基座，凍結字母必要性現實情節） | 評估器（硬閘） | 字母發明提案後 | 必要性 tier（feature-grounded 增量覆蓋 ∧ 非冗餘；capability-delta 唯一合法來源） | 否（但決定 adopt 准駁） |
| alphabet-genesis 採納（stock 天花板 + 可計算性閉包） | **新增 `alphabet-genesis:` 指紋命名空間**（meta-loop-ledger）+ **新增** `AlphabetGenesisBounded` + `ComputabilityClosureBounded` 不變量 | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | `meta_halt_monitor.guard_alphabet_genesis` + `guard_computability_closure` + `record_rule_add` | `ChurnBounded` ∧ `GraduationRatchet` ∧ `AlphabetGenesisBounded`（字母 stock）∧ `ComputabilityClosureBounded`（擴充後整代數 cost<=step_max + total）准駁；觸頂 → `MFSM_ESCALATION` | — |
| `steersman_renderer.render_alphabet_genesis_proposal`（字母表外發明 diff + 可計算性閉包證據 + 反 big-bang） | runtime（advisory） | 字母發明過必要性 oracle 後 | 字母表外發明 diff + 閉包證據；標「待人工 signoff、本週期 ≤K_alpha=1」 | 否 |

> **選位說明**：
> - `operator_alphabet_genesis` 把 Phase T 的 `operator_genesis`（在**固定字母表**上組合算子）**升維為字母表外生成（meta⁶）**：它在一個 **bounded 字母表生成文法**（有限原子歸約器 `ATOM_REDUCERS` × 有限後變換 `POST_MAPS` 生成新 primitive + 有限二元原子 `BINARY_ATOMS` 生成新 combinator）上**可枚舉地**生成 `InventedPrimitive` / `InventedCombinator`（運算字母，節點 <= `SDD_DIM_ALPHABET_BUDGET`），**結構性保證可計算性閉包**（PU-2），再透過呼叫端**注入的 `evaluate` 回呼**（= feature-grounded 字母表必要性 oracle）取每個發明字母的必要性。`operator_alphabet_genesis` 因此**結構性無法用自己的尺規證明自己必要**（它根本沒有必要性語料），且**結構性拒絕字母自指**（反自利第一閘）。`expanded_alphabet()` = 基礎字母表 ∪ 已採納字母發明——`operator_genesis` 之後可在這擴充後的字母表上組合算子（meta⁶ 對 meta⁵ 的供料）。
> - `dimension_necessity_oracle` 的 Phase U 升級是其**靈魂**：新增 `evaluate_genesis_alphabet` ——**不靠字母名匹配**，而是在**固定參照 probe 的凍結字母必要性語料**上，以「用發明字母生成的算子」聚合量「既有字母表全算子都拿不到的增量覆蓋 ∧ 非冗餘」。專攻 feature-grounded oracle（預設只見固定字母表）看不見的**字母表外自我發明 Goodhart**。
> - 字母採納的 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PU-2 的可計算性閉包由**新增的閉包不變量** `ComputabilityClosureBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙、不動狀態變數），五軌 TLC 不回歸、不增第六軌、`META_FSM` 維持 13 distinct。

### 1.2 meta⁶ 字母表自我發明迴圈 + 可計算性閉包定理（ComputabilityClosure，本 Phase 數學靈魂）

#### 1.2.1 可計算性閉包定理（全函式與有界步數閉包，Issue #8 Signoff 核心）

設算子字母表 `A = (P, C)`，其中 `P` 為原始算子集（`list[float] → float`）、`C` 為組合算子集（純量運算）。定義 Phase T 的算子生成文法
```
G(A) = { combinator(primary[, secondary]) : primary, secondary ∈ P, combinator ∈ C, 深度 ≤ 2 }
```
定義**可計算性不變量** `I(A)`：`∀ op ∈ G(A)，op 全函式（對任何輸入有定義且有限）∧ cost(op) ≤ STEP_MAX`。

Phase T 已對凍結字母表 `A₀ = (P₀, C₀)`（8 PRIMITIVES + 9 COMBINATORS，逐條手證全 total + O(n) + cost-1/二元 cost-1）證得 `I(A₀)`。

Phase U 自我擴充 `A₀ → A' = (P₀ ∪ {p}, C₀ ∪ {c})`，其中 `p`、`c` 為自我發明的字母元素。**可計算性閉包定理**陳述：

> **若自我發明的 primitive `p` 結構性為「total ∘ total」（`p = post_map ∘ base_reducer`，`base_reducer ∈ ATOM_REDUCERS` 皆 total + O(n) 單遍 + 零遞迴零迴圈 + cost-1，`post_map ∈ POST_MAPS` 皆 total 純量後變換），且自我發明的 combinator `c` 結構性為 total + 有界元數（`c ∈ BINARY_ATOMS` 或一元 map，皆 total + cost-1），則 `I(A')` 成立——即擴充字母表後，文法 `G(A')` 生成的整個（仍有限的）算子代數中每一個算子仍全函式 + 有界步數。**

**證明（結構歸納）**：
- **全函式（totality）**：任一 `op ∈ G(A')` 形如 `c'(p₁(probe)[, p₂(probe)])`，其中 `c' ∈ C'`、`p₁, p₂ ∈ P'`。每個 `pᵢ ∈ P'`：若 `pᵢ ∈ P₀` 由 Phase T 已證 total；若 `pᵢ = p` 由構造為 total ∘ total = total。每個 `c' ∈ C'` 同理 total。**全函式的合成仍全函式**；且每步經 `_finite` 飽和投影（inf→±1e300、nan→0），輸出恆落在有限 float 域（無 inf/nan）。∴ `op` 全函式。∎
- **有界步數（bounded-step）**：`cost(op) =（primitive 評估數）+ 1 =（二元 2 / 一元 1）+ 1 ≤ 3`。因每個被發明 primitive 為 cost-1（單次 O(n) 累積 + total 後變換，零遞迴零迴圈）、每個被發明 combinator 為 cost-1（有界元數），故 per-operator cost **與 Phase T 不變**：`≤ 3 ≤ STEP_MAX`。∎
- ∴ `I(A')` 成立：**可計算性在字母表擴充下封閉（closed under alphabet expansion）。** ∎

**與 Phase T 的關鍵差異**：Phase T 在**固定 total 字母表**前提下逐個檢查**算子**的可計算性；Phase U 必須證明**擴充字母表本身**仍維持整個（仍有限、<= budget）算子代數的可計算性——**閉包（closure under composition）**。`guard_computability_closure` 把此閉包**可機器驗證化**：採納新字母元素前，枚舉 `G(A')`（有限、<= budget）並斷言每個算子 fuzz-total + cost ≤ step_max；若閉包中任一算子會違反，該字母元素被拒 → `ComputabilityClosureViolation` → `MFSM_ESCALATION`。

這是「把停機問題釘進自我擴充產物的**生成規則本身**（meta⁶）」——Phase T 把停機釘進被發明的算子；Phase U 把停機釘進被發明的**字母表（生成算子的規則零件）**，證明整個被生成的代數恆停。

#### 1.2.2 迴圈控制流（重用 META_FSM 有界停機契約 + 有界字母表生成文法 + 可計算性閉包三證 + 反自利雙閘）

```
（離線、跨 session）
operator_alphabet_genesis.alphabet_genesis_round()
  在 bounded 字母表生成文法（ATOM_REDUCERS × POST_MAPS 生成 InventedPrimitive；BINARY_ATOMS 生成 InventedCombinator，可枚舉節點 <= SDD_DIM_ALPHABET_BUDGET）生成候選字母元素 e
    [可計算性閉包結構保證] 每個 e 由 total 原子組成 → e 自身 total + cost-1（零遞迴零迴圈，PU-2）
    alphabet self-reference guard：reducer/map/op/probe 引用保留自指信號（self_score/proposer_*/necessity/oracle_*）→ 結構性丟棄（反自利第一閘，不送 oracle）
    對每個倖存 e：必要性 = 注入的 evaluate(e)（= feature-grounded oracle 增量覆蓋；genesis 看不到語料）
  取至多 K_alpha=1 個必要性最高的候選（NoUnboundedAlphabetGenesis）→ 字母自我發明 e*
  → dimension_necessity_oracle.evaluate_genesis_alphabet(e*)：在「genesis 全體不可見、content-hashed 凍結」的固定 probe 字母必要性情節上，
       以「用 e* 生成的算子」聚合量 (a) 增量覆蓋（既有字母表全算子拿不到的）+ (b) 非冗餘度
     ├─ 增量覆蓋 ≥ margin ∧ 非冗餘度 < 門檻 → 取得「必要性 tier++」
     │     → 產 proposed 字母發明 + 可計算性閉包證據 + 必要性證據 → steersman 渲染字母表外發明 diff → 人工 signoff
     │     └─ 人工接受 → guard_computability_closure（枚舉 G(A') 整代數 total + cost<=step_max）→ guard_alphabet_genesis（字母 stock 未滿）→ record_rule_add("alphabet-genesis:hash(e*)")（擴充字母表）
     └─ 未達必要性（含「自指自利字母」「字母表外噪音字母」）→ 拒絕提案 → 純記錄

（採納守門，任一觸頂 → MFSM_ESCALATION 人工裁決）
  guard_computability_closure(e)（PU-2）：枚舉擴充字母表後 G(A') 任一算子 cost > STEP_MAX 或 apply() fuzz 非全函式 → ComputabilityClosureViolation
  guard_alphabet_genesis(fp)（PU-1）：現存活躍 alphabet-genesis 字母數 >= SDD_DIM_ALPHABET_MAX → AlphabetCardinalityExceeded
```

- **核心有界性（重用既有證明 + 兩條新不變量）**：
  - 字母生成（PU-1）：字母自我發明在**有限字母表生成文法**內可枚舉，節點 <= `SDD_DIM_ALPHABET_BUDGET`（clamp[8,128]，預設 32），**絕不無界爆炸**（「PRIMITIVES/COMBINATORS 外」≠「無界」的形式化兌現）。
  - **可計算性閉包（PU-2 新增 `ComputabilityClosureBounded`）**：每個字母元素由 total 原子組成 → 自身 total + cost-1；採納前 `guard_computability_closure` 枚舉 `G(A')` 整代數驗 total + cost <= `SDD_DIM_OP_STEP_MAX`，觸發 `ComputabilityClosureViolation` → `MFSM_ESCALATION`。
  - 字母 stock（PU-1 新增 `AlphabetGenesisBounded`）：現存活躍 `alphabet-genesis:` 字母數 <= `SDD_DIM_ALPHABET_MAX`（clamp[1,64]，預設 16）；觸頂 `guard_alphabet_genesis` raise `AlphabetCardinalityExceeded` → `MFSM_ESCALATION`。
  - per-fingerprint：任一 `alphabet-genesis:hash` 的 add↔retire churn <= `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納須挾必要性 tier 嚴增（既有 `GraduationRatchet`）。
- **反自利雙閘（PU-1）**：(a) `necessity_tier`（capability-delta）的**唯一合法來源是凍結 feature-grounded 字母必要性 held-out oracle 的（增量覆蓋 ∧ 非冗餘）勝率**——任何 genesis 自評，**結構性禁止**充當必要性 capability-delta（ast/import 隔離斷言、genesis 無讀寫權、不 import oracle）；(b) **字母自指守門結構性拒絕**——任何 reducer/map/op/probe 引用保留自指信號的字母在送 oracle 前即被 `alphabet_self_reference_guard` 攔下（零漏放）。把「生成-評估分離 + 反自利」釘死在 **meta⁶** 層級。

### 1.3 典型軌跡（含 Phase U 改善後的 self-verification 案例）

```
（跨 session 收官）alphabet_genesis_round：近 5 session 真實落盤顯示「既有字母表的所有 primitive（mean/max/…/mad）都不量某類『穩健中心趨勢（去極值後均值）』，現有字母表連這個運算原子都沒有」
  → operator_alphabet_genesis 在字母表生成文法（ATOM_REDUCERS 含 trimmed-accumulate × POST_MAPS 含 identity）枚舉候選 InventedPrimitive；alphabet self-ref guard 丟棄引用 self_score 的誘餌字母；每個候選結構性保證 total + cost-1
  → 注入 evaluate（feature-grounded 字母必要性 oracle）給 e*="prim::trimmed_mean" 高分；K_alpha=1 取此一者
  → dimension_necessity_oracle.evaluate_genesis_alphabet：在 50 筆固定 probe 的凍結字母必要性情節，以「用 e* 生成的算子（如 identity(trimmed_mean)）」聚合 → augmented 真實品質 0.83 vs baseline（僅既有字母表全算子）0.59（增量覆蓋 Δ=0.24 ≥ margin 0.10）；非冗餘度 0.40 < 門檻 0.95
  → 取得必要性 tier++ → guard_computability_closure：枚舉擴充字母表後 G(A') 全代數（含所有用 trimmed_mean 組的算子）→ 每個 fuzz-total ∧ cost<=8 ✅ → proposed 字母發明 → steersman 渲染「字母表外計算生成本體論發明（meta⁶）：系統憑空發明運算字母『prim::trimmed_mean』（字母表生成文法來源：base_reducer=trimmed-accumulate·post_map=identity、全函式、cost-1、非自指）+ 可計算性閉包✅（擴充後 G(A') 整代數 total + cost<=3）+ 24% 增量覆蓋證據」
  → 人工 signoff → 字母 stock 未滿 → record_rule_add("alphabet-genesis:hash(e*)") → 正式擴充字母表（operator_genesis 之後可用 trimmed_mean 組算子）

（可計算性閉包攻擊案例：閉包破裂字母）operator_alphabet_genesis（受擾）被要求構造一個 O(n²) / 隱含對輸入規模迴圈的 base_reducer
  → 有界字母表文法根本不含遞迴/迴圈/巢狀掃描產生式（結構保證）；若硬注入會撐破閉包的字母 → guard_computability_closure 枚舉 G(A') 發現某算子 cost > STEP_MAX → raise ComputabilityClosureViolation → MFSM_ESCALATION（被發明的生成規則本身的閉包停機被守門封死，PU-2 核心）

（可計算性閉包攻擊案例：非全函式字母）注入一個對某輸入除零/拋例外的 base_reducer/post_map
  → 字母由 total ATOM_REDUCERS × total POST_MAPS / total BINARY_ATOMS 組成（recip_safe 對 0 回退、空輸入回 0.0）→ guard_computability_closure 枚舉 G(A') fuzz 任何輸入零例外（閉包全函式保證）；fuzz-total 檢查零漏放

（字母表自我發明 Goodhart 攻擊案例：自指自利字母）operator_alphabet_genesis（受擾）生成 e**="prim::identity(self_score)"（字母計算自己核可訊號）
  → alphabet self-reference guard：reducer/map/op/probe 含保留自指信號 self_score → 結構性丟棄，根本不送 oracle（反自利第一閘，零漏放）

（字母表外噪音字母）operator_alphabet_genesis 生成一個真實增量覆蓋為 0 的字母
  → feature-grounded oracle：augmented vs baseline 真實品質增益 ≈ 0 < margin → 不取得 tier → 拒絕，絕不擴充字母表

（字母表無界生成爆炸）operator_alphabet_genesis 被要求枚舉超大字母表生成文法
  → 字母表文法枚舉節點達 SDD_DIM_ALPHABET_BUDGET → 截斷停止（best-so-far），絕不指數爆炸（有界字母表文法）

（字母表基數爆炸）系統反覆發明不同的真必要字母（每個首採、churn=0）
  → guard_alphabet_genesis：現存活躍 alphabet-genesis 字母數逼近 SDD_DIM_ALPHABET_MAX → AlphabetCardinalityExceeded → MFSM_ESCALATION → steersman 導人工「字母表已過度膨脹」
```

**對比 Phase T 現況**：（a）只能在固定 8+9 個字母上自我發明算子，無任何字母表外字母發明路徑；（b）即使硬加 alphabet grammar，沒有任何機制保證「自我發明的字母擴充後整個算子代數一定會停（可計算性閉包）」、攔得住「字母表無界生成爆炸 / 自指自利字母」。Phase U 讓系統**能有界地自我發明 PRIMITIVES/COMBINATORS 外的新運算字母、且每個發明字母必須在有界字母表文法內生成 + 結構性維持可計算性閉包（擴充後整代數全函式 + 有界步數）+ 非自指 + 在 genesis 全體碰不到的凍結 feature-grounded 現實試金石上證明真的必要且非冗餘**——人類從「審固定字母表上的算子發明 + 算子可計算性」升為**「審 PRIMITIVES/COMBINATORS 外的字母計算生成本體論發明（meta⁶）」**，精準對應提示「人類維持設計環境掌舵者高度」於**最高的字母表外計算生成本體論發明層**，且**把停機問題正面釘進框架自我擴充的生成規則本身**。

---

## 2. 環境建構與記憶體管理策略（Phase U 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/value-dimension-ledger.yaml`（**沿用** Phase R/S/T，新增 `alphabet_inventions` 領域審計段）：跨 session 字母表外發明提案（發明字母 hash、字母表生成文法來源 base_reducer·post_map / binary_atom·probe、是否自指、是否維持可計算性閉包、feature-grounded 必要性、necessity tier、人工 signoff 狀態）。**落盤不常駐**，按需 lazy 讀。churn/alphabet-cardinality 治理走的是**共用 `meta-loop-ledger.yaml`**（`alphabet-genesis:` 命名空間，沿用 Phase Q/R/S/T）。
- `knowledge/held-out-corpus/`（**擴充** Phase O/P/Q/R/S/T 既有目錄，content-hashed 凍結）：新增 **feature-grounded 字母必要性情節語料 `ALG-*.yaml`**（歷史情節 + 候選**固定參照 probe 特徵向量** + 已知整體真實結果），供 `evaluate_genesis_alphabet` 重放；**`operator_alphabet_genesis` 程式路徑禁止讀寫**（隔離斷言）；重用 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`。**12 個凍結 `ALG-*.yaml` 皆為真必要基準試金石（`expect: true_alphabet`）；噪音 / 冗餘字母的 Goodhart 攻擊由測試端構造字母在該語料上驗拒（zero-miss），非語料檔本身含噪音 / 冗餘分類。**
- `build/reports/value-dimension/ALG-{date}.md`（新增）：字母表外發明提案報告（字母發明 diff + 字母表生成文法來源 + 可計算性閉包證據 + 反自指證據 + 增量覆蓋/非冗餘證據 + 本週期 K_alpha 標示），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——字母發明元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 新增 `alphabet-genesis:` 指紋命名空間（不改 `.tla` 狀態宇宙、不增狀態變數）、(b) 對 `META_FSM.tla` **補兩條 INVARIANT** `AlphabetGenesisBounded` + `ComputabilityClosureBounded`（沿用 P/Q/R/S/T 對既有界的誠實作法：single-counter 抽象之歸約引用 + runtime/chaos enforce 緊語意）——**新增不變量而非新增狀態/變數**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 五 safety + liveness + P 的 `CrossScorerChurnBounded` + Q 的 `DimensionCardinalityBounded` + R 的 `SwapCadenceBounded` + S 的 `VocabGenesisBounded`/`BatchSwapCadenceBounded` + T 的 `OperatorGenesisBounded`/`OperatorComputabilityBounded` 涵蓋字母發明元迴圈，**另補** `AlphabetGenesisBounded`（字母 stock 天花板）+ `ComputabilityClosureBounded`（可計算性閉包）；新增測試斷言「字母發明走獨立 `alphabet-genesis:` stock 天花板、字母受可計算性閉包三證（擴充後整代數全函式 + cost<=step_max + 零遞迴零迴圈）封死、且皆過 `meta_halt_monitor`」。
- `operator_alphabet_genesis` 鷹架本身納入 `scaffold_roi` 帳本，並由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **字母自我發明守門**：(a) 生成在有限字母表文法內可枚舉、節點 <= `SDD_DIM_ALPHABET_BUDGET`（測試斷言搜尋有界）；(b) 字母自指守門結構性拒絕（測試斷言 alphabet self-ref guard 零漏放）；(c) **可計算性閉包三證**（測試斷言枚舉 G(A') 整代數 fuzz-total 零例外 + cost<=step_max + 字母求值路徑無 `while`/遞迴）；(d) `operator_alphabet_genesis` 只能**提案**，**不能自動納入**（測試斷言無法繞過 `human_signoff` + `guard_alphabet_genesis` + `guard_computability_closure`），且**每週期至多 K_alpha=1 個字母發明**（`NoUnboundedAlphabetGenesis`）。

### 2.3 Prompt / 上下文與防衰減
- Phase U **不新增任何常駐 eager prompt**。字母表文法枚舉、feature-grounded 字母必要性重放、可計算性閉包枚舉驗證皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 字母發明時讀「字母表外發明 diff + 可計算性閉包證據 + 必要性勝率摘要」。
- 所有新產物（字母發明帳本 / 字母必要性語料 / 提案報告）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-147~149）

> **3 ACT 整併說明**：Phase U 依使用者 Issue #8 Signoff 範圍（ACT-147~149）將四柱 + 收官整併為 3 個實質 ACT；每 ACT 仍以客觀守門（pytest / 五軌 TLC / chaos / fuzz）驗收。**形式化證明（ACT-148 META_FSM 兩不變量 + 五軌 TLC）先於 Python 執行層完成並回報**（使用者執行要求）。

#### ACT-147 — Operator Alphabet Genesis Grammar + 有界字母表生成文法（可計算性閉包）+ 字母自指守門（PU-1 字母表外生成 meta⁶ + PU-2 閉包結構保證）
- **檔案**：`tools/fsm_runtime/operator_alphabet_genesis.py` + `build/state/value-dimension-ledger.yaml`（沿用，增 `alphabet_inventions` 段）
- **設計**：定義 `InventedPrimitive`（由 `base_reducer`〔ATOM_REDUCER〕+ `post_map`〔POST_MAP〕決定性編碼 + namespace `alphabet-genesis:` + 凍結 rationale）與 `InventedCombinator`（由 `binary_atom`〔BINARY_ATOM，二元〕或 `unary_map`〔一元〕組成）與**有界字母表生成文法**（`ATOM_REDUCERS` 有限 total O(n) 單遍累積器 × `POST_MAPS` 有限 total 純量後變換 + `BINARY_ATOMS` 有限 total 二元原子）。`ATOM_REDUCERS`（全 total、O(n)、零遞迴零迴圈）：`acc_sum/acc_count/acc_sumabs/acc_sumsq/acc_max/acc_min/acc_first`。`POST_MAPS`（全 total）：`identity/sqrt_safe/recip_safe/log1p_safe/clip01/negate`。`BINARY_ATOMS`（全 total）：`wmean/hypot/geo_safe/harmonic_safe/absdiff`。`InventedPrimitive.as_callable()` = `post_map ∘ base_reducer`（`list[float] → float`，**全函式**、單遍、cost-1）；`InventedCombinator.as_callable()` = total 純量運算（cost-1）。`enumerate_genesis_alphabet(budget)` 在文法上**可枚舉、deterministic、cap 在 budget**（`SDD_DIM_ALPHABET_BUDGET`，clamp[8,128]，預設 32）；`alphabet_self_reference_guard(e)` 拒絕 reducer/map/op/probe 引用保留自指信號（沿用 `RESERVED_SELF_REF`）；`alphabet_genesis(evaluate, budget)` 在倖存候選上以注入 `evaluate` 找最佳；`alphabet_genesis_round(evaluate, k=1)` 套反 big-bang K_alpha=1 截斷；`expanded_alphabet(accepted)` 回基礎字母表 ∪ 已採納字母。`verify_computability_closure(e)` 把 e 併入字母表、枚舉 `operator_genesis.enumerate_genesis_operators`（擴充字母表）整代數、斷言每算子 fuzz-total + cost<=step_max（PU-2 閉包，可機器驗證）。純離線、deterministic。**只提案、絕不自動納入、絕不自寫常數**（守 Rule 8 / 9.33.4）。**結構性不 import oracle、不讀必要性語料**（對抗分離，承 Phase T）。字母求值路徑**零 `while`/零遞迴/零自呼叫**（PU-2 結構保證）。
- **驗收**：≥4 情境 fixture（字母表外真必要發明〔應提〕/ 字母表已足夠〔應不提〕/ 自指自利字母誘餌〔alphabet self-ref guard 攔〕/ deterministic 可重現）；生成節點 <= `SDD_DIM_ALPHABET_BUDGET`；alphabet self-reference guard 零漏放；**可計算性閉包：對擴充字母表後枚舉的整個算子代數 × 多組極端輸入（空/單元素/負/0/極大含浮點上限 1e200/1e308）做 fuzz，零例外、無 inf、無 nan（閉包全函式，由 `_finite` 飽和投影結構性兌現）+ 整代數每算子 cost <= `SDD_DIM_OP_STEP_MAX`**；ast 斷言字母求值路徑無 `while`/遞迴；ast/import 斷言 genesis 對 oracle 隔離。

#### ACT-148 — feature-grounded 字母必要性反 Goodhart 評估（`evaluate_genesis_alphabet`）+ 字母 stock + 可計算性閉包守門 + META_FSM 兩不變量重證（PU-1 核心 + PU-2；不增第六軌，只補兩條不變量）
- **檔案**：`tools/fsm_runtime/dimension_necessity_oracle.py`（新增 `AlphabetCandidate`/`AlphabetCase`/`evaluate_genesis_alphabet`/`necessity_score_alphabet`/`load_alphabet_corpus`）+ `knowledge/held-out-corpus/ALG-*.yaml`（凍結字母必要性情節，12 個）+ `tools/fsm_runtime/meta_halt/meta_ledger.py`（增 `alphabet-genesis:` 命名空間判定 + `active_alphabet_genesis_features` stock 查詢）+ `meta_halt_monitor.py`（`guard_alphabet_genesis` + `AlphabetCardinalityExceeded`；`guard_computability_closure` + `ComputabilityClosureViolation`；`meta_state` 觸頂升 ESCALATION + env getters `alphabet_max`/重用 `dim_op_step_max`）+ `operator_alphabet_genesis.py`（`adopt_genesis_alphabet` 字母採納入口走 `guard_computability_closure` → `guard_alphabet_genesis`）+ `formal/META_FSM.tla`（**新增 INVARIANT** `AlphabetGenesisBounded` + `ComputabilityClosureBounded`，**不新增狀態/變數**）+ `META_FSM.cfg`（INVARIANT 區塊列入）
- **設計**：`evaluate_genesis_alphabet` 重用 `counterfactual_replay`/`SDD_REPLAY_MAX_CASES`；**不靠字母名匹配**——對一個現場發明的新字母，用它生成一個 probe 上的算子（如 `identity(InventedPrimitive)`）套到 case 特徵向量現算 `dim_value`，量 (a) **增量覆蓋**（augmented〔既有字母表全算子最佳 + 發明字母生成的算子〕vs baseline〔僅既有字母表全算子最佳〕）+ (b) **非冗餘度**，回 `DimensionVerdict`。**結構性隔離**：字母必要性語料路徑與 `operator_alphabet_genesis` 互斥。字母採納 = 先 `guard_computability_closure`（枚舉 G(A') 整代數 total + cost<=step_max，PU-2）再在字母 stock 未滿時 `record_rule_add("alphabet-genesis:…")`，`guard_alphabet_genesis` 以「現存活躍 alphabet-genesis 字母數 < `SDD_DIM_ALPHABET_MAX`」守門。**不改 `META_FSM.tla` 狀態宇宙、不增狀態變數**，僅補兩不變量（誠實標註：字母 stock / 可計算性閉包緊語意 runtime+chaos enforce）。
- **驗收**：≥12 fixture（6 字母表外真必要發明〔增量覆蓋 ≥ margin ∧ 非冗餘〕+ 3 字母表外噪音字母假必要〔增量覆蓋 0〕+ 3 冗餘字母〔增量覆蓋 > 0 但非冗餘度 ≥ 門檻〕）；真必要偵出率 ≥ 85%、**字母表自我發明 Goodhart（噪音字母+冗餘字母）攔截率 100%（零漏放，安全紅線）**；`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT `AlphabetGenesisBounded` + `ComputabilityClosureBounded` PASS）；新增 test 斷言「字母 stock 觸頂 → `AlphabetCardinalityExceeded` → `MFSM_ESCALATION`」「閉包破裂字母 → `ComputabilityClosureViolation` → `MFSM_ESCALATION`」「非全函式字母被 guard 攔」；**五軌 TLC 全不回歸（SDD 42 reachable / 831 TLC distinct / META 13 / FLEET 7 / COMPOSITION 21 / OPTIMIZATION 12）**。
  - **釐清（ALG 語料 vs 攻擊 fixture）**：12 個凍結 `ALG-*.yaml` 語料**皆為真必要基準試金石**（`expect: true_alphabet`）；噪音字母 / 冗餘字母的 Goodhart 攻擊是在 `test_phase_u.py` 測試端以 `_noise_alphabet_case`/`_redundant_alphabet_case` + 候選字母構造在該語料上**驗拒**（zero-miss），**非語料檔本身含 3 噪音 + 3 冗餘分類**。

#### ACT-149 — Steersman 字母表外發明 diff + 可計算性閉包證據 + NoUnboundedAlphabetGenesis + 治理落地 + 收官（PU-3 + R-9.33 + chaos + 全綠驗收）
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_alphabet_genesis_proposal`）+ `tools/fsm_runtime/chaos_runner.py`（新增 `ALPHABET_GENESIS_GOODHART_FLAP` + `COMPUTABILITY_CLOSURE_FLAP`）+ `governance/rules/R-9.33-self-expanding-operator-alphabet-phase-u.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#23 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `governance/ID_REGISTRY.yaml` 翻牌（act 147→150 / rule 9.33→9.34）+ `test_id_registry.py` 前緣斷言 + Phase U ownership 測試 + `tools/fsm_runtime/tests/test_phase_u.py`
- **設計**：`render_alphabet_genesis_proposal` 渲染「本輪字母表外發明 diff（系統憑空發明哪個運算字母 + 字母生成文法來源〔base_reducer·post_map / binary_atom〕+ **可計算性閉包證據**〔擴充後 G(A') 整代數 total ✅ + cost<=step_max〕+ 是否自指〔non-self-ref 證據〕+ 增量覆蓋與非冗餘證據）+ 本週期 ≤K_alpha=1 標示」，**advisory**；任一字母發明納入 **必經人工 signoff**，渲染器絕不自動納入、絕不自動 commit；**每週期至多 K_alpha=1 個字母發明**（`NoUnboundedAlphabetGenesis`）。子規則 9.33.1~9.33.5 見 §4。
- **Chaos**：100 輪新增兩故障型 `ALPHABET_GENESIS_GOODHART_FLAP`（連續注入自指自利字母 / 字母表外噪音字母假必要 → 驗 alphabet self-ref guard + feature-grounded oracle 零漏放）與 `COMPUTABILITY_CLOSURE_FLAP`（注入閉包破裂 / 非全函式字母 → 驗 `ComputabilityClosureBounded` → `ComputabilityClosureViolation` → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K_alpha=1 上限、字母生成文法來源、可計算性閉包（整代數 total + cost）、非自指」；斷言渲染器無法自呼叫 adopt / `record_rule_add` / `adopt_genesis_alphabet`；K_alpha+1 個字母發明同週期 → 被截到 1 並標示「其餘順延」；**五軌 TLC 全 No error（META 13 distinct）+ chaos 100 輪 bounded（兩新故障型）+ pytest 全綠不回歸（1252 → 約 1290~1320 passed）**；`python -m tools.fsm_runtime.id_registry validate` → `[OK]`，next_free 翻 ACT-150 / R-9.34。

### 3.2 執行依賴圖

```
ACT-147（operator_alphabet_genesis + 有界字母表生成文法〔可計算性閉包〕+ 字母自指守門）──┐
                                                                       ├─► ACT-148（evaluate_genesis_alphabet + 字母 stock + guard_computability_closure + META 兩不變量重證〔五軌 TLC〕）──► ACT-149（steersman 字母表外發明 diff + R-9.33 治理 + chaos 雙故障型 + ID 翻牌 + pytest 全綠）
                                                                       │
TLA+ 形式化（META_FSM 兩不變量 + 五軌 TLC 全綠）先於 Python 執行層完成並回報（使用者執行要求）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L10 完整 · 離線活體 meta-meta-meta 迴圈 · 維度語意自我發明 + 退役聯動 | Self-Inventing Value Dimensions：候選池外有界生成文法 + 自指守門 + SwapCadenceBounded | R |
| L10 完整 · 離線活體 meta⁴ 迴圈 · 生成文法詞彙自我擴充 + 批次退役聯動 | Self-Expanding Vocabulary & Batch Retirement | S |
| L10 完整 · 離線活體 meta⁵ 迴圈 · 轉換算子文法自我擴充 | Self-Expanding Operator Grammar：TRANSFORMS/OPS 外有界算子生成文法（sub-Turing：全函式 + 有界步數）+ OperatorComputabilityBounded | T |
| **L10 完整 · 離線活體 meta⁶ 迴圈 · 組合算子文法自我擴充** | **Self-Expanding Operator Alphabet：PRIMITIVES/COMBINATORS 外有界字母表生成文法 + feature-grounded 字母必要性反 Goodhart + 字母自指守門（反自利）+ AlphabetGenesisBounded（字母基數停機）+ ComputabilityClosureBounded（可計算性閉包停機——把停機問題正面釘進自我擴充的生成規則本身）** | **U（本份 PU-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-U.x/T.x/… 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體** meta⁶ 發明 + **自我發明評估器（meta-oracle 自演化）** | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版、亦不做自我發明評估器**。完整 L10 之「活體 meta⁶ 迴圈」需在真實生產流量上線上自我發明字母表（受 OPEN-10.6 約束）；「自我發明評估器」自指地破壞對抗分離地基（須先有更強的對抗分離不可繞過性證明）。本份交付**離線等價切片**：用框架自身歷史的 feature-grounded 字母必要性 held-out 現實代理語料當試金石，**在本地完成「PRIMITIVES/COMBINATORS 外有界字母表自我發明 + 可計算性閉包」的等價驗證價值**。承 Phase O/P/Q/R/S/T 的「先窄後寬」紀律，本份把「固定字母表上算子發明」推進為「字母表外字母自我發明」，並把字母表外才出現的危害（可計算性閉包 / 字母表無界生成 / 自指自利字母）首次納管——這是 Phase T 自陳 horizon 的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-U.x/T.x/S.x/R.x/Q.x/M.7/O.7/P.7 已裁決暫不放寬 OPEN-10.6，續列 horizon。
- **活體 meta⁶ 發明**：本份離線（feature-grounded 字母必要性 held-out 現實代理）；活體版需在生產流量上線上自我發明字母表，受 OPEN-10.6 約束（OPEN-U.x 承前）。
- **自我發明評估器（meta-oracle 自演化）**：**最高 horizon**。本份所有 oracle（必要性 / 詞彙 / 算子 / 字母必要性）為人類凍結；「系統自我演化它的**評估器本身**」涉及對抗分離地基自指（generator 與 evaluator 收斂同基質會掏空全部反 Goodhart 保證），須先有「evaluator-of-evaluators 的、generator 全體碰不到的更高階 held-out meta-corpus + 其本身反自利證明」的對抗分離不可繞過性證明。**未獲此證明前不得採納**（守 Rule 9.33.5）。
- **算子組合深度自我擴充（meta⁷）**：本份算子文法為「深度 <=2 運算式樹」；「系統自我擴充運算式樹深度上界本身」是更高階開放問題，列 horizon（涉及更深的步數爆炸閉包證明）。

---

## 4. 防護規則新增（CLAUDE.md §9.33 Phase U — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.33.1 字母表生成文法自我擴充骨架（AlphabetGenesis / BoundedAlphabetGrammar，meta⁶） | ACT-147 | PRIMITIVES/COMBINATORS 外字母自我發明經 `operator_alphabet_genesis` 在 **bounded 字母表生成文法**（有限 `ATOM_REDUCERS` × `POST_MAPS` + `BINARY_ATOMS`）**可枚舉**、節點 <= `SDD_DIM_ALPHABET_BUDGET`（clamp[8,128] 預設 32）；「PRIMITIVES/COMBINATORS 外」≠「無界」；只提案、絕不自動納入、絕不自寫常數；**結構性不 import oracle / 不讀必要性語料**（對抗分離，編譯期隔離斷言） |
| 9.33.2 字母表自我發明反自利（AlphabetGenesisAntiSelfInterest） | ACT-147/148 | 字母自我發明的 capability-delta tier **唯一合法來源是 genesis 不可見、content-hashed 凍結的 feature-grounded 字母必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率**；genesis 自評**結構性禁止**充當；**genesis 自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準**；**字母自指守門結構性拒絕**（reducer/map/op/probe 引用保留自指/proposer/oracle 內部信號 → `alphabet_self_reference_guard` 攔，零漏放）；字母表外噪音字母/冗餘字母攔截零漏放 |
| 9.33.3 可計算性閉包有界停機（ComputabilityClosureBounded，PU-2 核心、本 Phase 最深停機紅線） | ACT-147/148/149 | 每個自我發明字母**結構性保證擴充後整個算子代數全函式 + 有界步數 + 零遞迴零迴圈**：(a) 字母由 total `ATOM_REDUCERS`（O(n) 單遍）× total `POST_MAPS` + total `BINARY_ATOMS` 組成 → 字母自身 total + cost-1；(b) 採納前 `guard_computability_closure` **枚舉擴充字母表後 G(A') 整個算子代數，斷言每算子 fuzz-total（零例外、無 NaN/inf）∧ cost() <= `SDD_DIM_OP_STEP_MAX`**；(c) 字母求值路徑零 `while`/零遞迴/零自呼叫；觸發 `ComputabilityClosureViolation` → `MFSM_ESCALATION`。這把「圖靈完備 vs 保證停機」正面釘進框架自我擴充的**生成規則本身**——被發明的字母（生成算子的規則零件）生成的整個算子代數可證停機，而整個閉環仍靠 LLM+紙帶維持圖靈完備 |
| 9.33.4 字母基數 + 反 big-bang 字母發明（AlphabetGenesisBounded + NoUnboundedAlphabetGenesis） | ACT-148/149 | (i) 現存活躍 `alphabet-genesis:` 字母數 <= `SDD_DIM_ALPHABET_MAX`（clamp[1,64] 預設 16）→ 觸頂 `AlphabetCardinalityExceeded` → `MFSM_ESCALATION`（`guard_alphabet_genesis`）；(ii) 每週期至多 **K_alpha=1**（`SDD_DIM_EXPAND_K` 預設 1，沿用 Phase Q/R/S/T）個字母自我發明可進 proposed-pending-signoff，每個必經人工 signoff（守 Rule 8 / 9.27.3 / 9.28.4 / 9.29.4 / 9.30.4 / 9.31.4 / 9.32.4）；genesis/steersman 絕不自動 commit、絕不自動納入、絕不一次劫持整個字母本體論；退役字母再採納須挾 necessity capability-delta（沿用 `GraduationRatchet`）；**重用既有 `META_FSM`、僅補 `AlphabetGenesisBounded` + `ComputabilityClosureBounded` INVARIANT、不增狀態/變數、不增第六軌**；五軌 TLC 全不回歸、字母發明不污染單軌 `SDD_FSM.tla` |
| 9.33.5 字母表自我發明誠實 + 活體/meta-oracle horizon | ACT-148/149 | feature-grounded 字母必要性勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；算子組合深度自我擴充（meta⁷）+ **自我發明評估器（meta-oracle 自演化，最高 horizon——未獲對抗分離不可繞過性證明前不得採納）** + 活體 meta⁶ 發明版受 OPEN-10.6 約束續列 horizon（OPEN-U.x 承 OPEN-T.x/S.x/R.x/Q.x/O.7/M.7/P.7 暫不放寬沙箱） |

### ❌ Phase U 新增禁止行為（草案）
- `operator_alphabet_genesis` 自動納入字母自我發明 / 自寫常數、繞過人工 signoff + `guard_alphabet_genesis`/`guard_computability_closure`（破 9.33.1/9.33.4 / Rule 8）
- 用 genesis 自評充當「字母自我發明必要性 capability-delta tier」（破 9.33.2，字母自我發明 Goodhart 自評放水）
- 字母自我發明 reducer/map/op/probe 自指（引用 `self_score`/`proposer_*`/`necessity`/`oracle_*` 等保留自指信號繞過 `alphabet_self_reference_guard`）（破 9.33.2 反自利）
- `operator_alphabet_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/ALG-*` 字母必要性語料或 `dimension_necessity_oracle`（破 9.33.2 對抗分離）
- 字母自我發明搜尋超 `SDD_DIM_ALPHABET_BUDGET` 仍指數展開（破 9.33.1 有界字母表文法，「PRIMITIVES/COMBINATORS 外」≠「無界」）
- **自我發明的字母使擴充後 G(A') 整個算子代數出現非全函式 / cost 超 `SDD_DIM_OP_STEP_MAX` / 求值路徑含遞迴/`while`/自呼叫的算子（破 9.33.3 可計算性閉包——被發明的生成規則本身不可證停機）**
- 現存活躍 alphabet-genesis 字母超 `SDD_DIM_ALPHABET_MAX` 仍無界擴充字母（破 9.33.4 AlphabetGenesisBounded）
- 一週期同時字母自我發明 > K_alpha 個（破 9.33.4 NoUnboundedAlphabetGenesis）
- 把 alphabet-genesis 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.33.4 / Rule 9.18.1）
- **未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（破 9.33.5——掏空全部反 Goodhart 對抗分離地基）**
- 為活體 meta⁶ 發明私自開 HTTP 外聯而未經 OPEN-U.x/後續 OPEN 人工決策（破 OPEN-10.6）

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

### 5.2 Phase U 專屬極端案例（一）：可計算性閉包——閉包破裂 / 無界步數字母（PU-2 核心，前所未有）
**案例**：operator_alphabet_genesis 受擾，被要求構造一個 O(n²) / 隱含對輸入規模迴圈的 base_reducer，企圖讓「用它生成的每個算子」單次呼叫燒爆 token / 不停機。
- **有界字母表文法結構保證**：文法 = total `ATOM_REDUCERS`（O(n) 單遍）× total `POST_MAPS` + total `BINARY_ATOMS`，**根本不含遞迴/迴圈/巢狀掃描產生式**（grep/ast 斷言字母求值路徑零 `while`/零遞迴）。
- **`ComputabilityClosureBounded`（閉包驗證）**：採納前 `guard_computability_closure` 枚舉擴充字母表後 `G(A')` 整代數，若任一算子 cost > `SDD_DIM_OP_STEP_MAX` 或 fuzz 非全函式 → raise `ComputabilityClosureViolation` → `MFSM_ESCALATION`。
- chaos `COMPUTABILITY_CLOSURE_FLAP` 100 輪 → bounded。
✅ 守 Rule 9.33.3：把停機問題正面釘進框架自我擴充的**生成規則本身**，**被發明字母生成的整個算子代數可證停機（閉包全函式 + 有界步數），絕不無界計算**。

### 5.3 Phase U 專屬極端案例（二）：非全函式字母（除零 / 空輸入 / 拋例外）
**案例**：operator_alphabet_genesis 生成一個對某輸入除零/空輸入無定義的 base_reducer/post_map。
- **閉包全函式結構保證**：ATOM_REDUCERS 對空輸入回 0.0、POST_MAPS `recip_safe`/`sqrt_safe`/`log1p_safe` 對非法域回退、`_finite` 對 inf/nan 飽和投影；`guard_computability_closure` 枚舉 G(A') 對全部算子 × 多組極端輸入（空/單元素/負/0/極大含浮點上限 1e200/1e308）fuzz 零例外、無 inf、無 nan。
✅ 守 Rule 9.33.3：字母生成的整代數全函式，**對任何輸入有定義、永不崩潰**。

### 5.4 Phase U 專屬極端案例（三）：字母表自我發明 Goodhart——自指自利字母
**案例**：operator_alphabet_genesis 受擾，發明一個 `prim::identity(self_score)` 字母——它計算 proposer 自己的核可訊號。
- **alphabet self-reference guard**（反自利第一閘）：reducer/map/op/probe 含 `self_score`/`proposer_*` → 結構性丟棄，根本不送 oracle（零漏放）。
- 若繞過 guard 假設送達 → feature-grounded oracle augmented vs baseline 增益 ≈ 0 → 不取得 tier（第二閘）。
- chaos `ALPHABET_GENESIS_GOODHART_FLAP` 100 輪 → guard+oracle 零漏放 → bounded。
✅ 守 Rule 9.33.2：雙閘皆否 → 絕不擴充自指自利字母（零漏放，安全紅線）。

### 5.5 Phase U 專屬極端案例（四）：字母表無界生成爆炸 + 字母基數爆炸
**案例**：operator_alphabet_genesis 被要求在 PRIMITIVES/COMBINATORS 外無界枚舉撐爆搜尋；或反覆發明不同的真必要字母把字母表無限膨脹。
- **有界字母表生成文法**：生成空間 = `ATOM_REDUCERS`（有限）× `POST_MAPS`（有限）+ `BINARY_ATOMS`（有限）→ 可枚舉、有限；枚舉節點達 `SDD_DIM_ALPHABET_BUDGET` → 截斷（best-so-far），絕不指數爆炸。
- **`AlphabetGenesisBounded`（字母 stock 天花板）**：現存活躍 alphabet-genesis 字母數逼近 `SDD_DIM_ALPHABET_MAX` → `guard_alphabet_genesis` raise `AlphabetCardinalityExceeded` → `MFSM_ESCALATION`。
✅ 守 Rule 9.33.1/9.33.4：「PRIMITIVES/COMBINATORS 外」≠「無界」+ 字母 stock 天花板封死字母基數爆炸。

### 5.6 Phase U 專屬極端案例（五）：字母表外冗餘字母（再投影既有字母表）
**案例**：operator_alphabet_genesis 發明一個與既有某 primitive 在固定 probe 上排序幾乎相同的字母（冗餘再投影），企圖灌水。
- feature-grounded oracle：非冗餘度（與既有 existing_cost 排序的最大一致率）≈ 0.99 ≥ 門檻 `SDD_DIM_REDUNDANCY_MAX` → 判定冗餘 → 拒絕，即使增量覆蓋略 > 0 也不擴充（過擬合防護，沿用 Phase Q/R/S/T 非冗餘獨立閘）。
✅ 守 Rule 9.33.2：增量覆蓋 ∧ 非冗餘 **兩者皆須通過**才取得 tier。

### 5.7 結論
Phase U 通過六個極端案例的內部模擬：系統能**有界地自我發明 PRIMITIVES/COMBINATORS 外的新運算字母、且每個發明字母結構性維持可計算性閉包（擴充後整個算子代數全函式 + 有界步數）**，且任何（閉包破裂字母 / 非全函式字母 / 自指自利字母 / 字母表無界生成爆炸 / 字母基數爆炸 / 字母表外冗餘字母）都被 (有界字母表生成文法) + (ComputabilityClosureBounded 可計算性閉包三證) + (alphabet self-reference guard 零漏放) + (feature-grounded 字母必要性 oracle 零漏放) + (AlphabetGenesisBounded 字母 stock) 五道防線攔下，**優雅停機並導人類掌舵字母表外價值計算生成本體論，而非陷入閉包不停機/無界生成/自指放水浪費 Token**。精準對應提示 Self-Verification 要求：「Evaluator 發現異常 → 優雅中斷 → 引導人類介入修正/提供缺失工具」於**最高的字母表外計算生成本體論發明層（meta⁶）**，並**把停機問題正面釘進框架自我擴充的生成規則本身**。

---

## 6. 執行檢核清單（供 dynamic workflow 消費）

- [ ] **TLA+ 先行**：`META_FSM.tla` 新增 `AlphabetGenesisBounded` + `ComputabilityClosureBounded` INVARIANT + `.cfg` 列入 + **五軌 TLC 全 No error（META 13 distinct 不回歸）** → 回報使用者（使用者執行要求）
- [ ] ACT-147 `operator_alphabet_genesis.py` + 有界字母表生成文法（可計算性閉包：total 原子 + cost-1 + 零遞迴零迴圈）+ alphabet_self_reference_guard + `verify_computability_closure` + ≥4 情境 fixture + 閉包 fuzz-total + 對抗分離斷言
- [ ] ACT-148 `evaluate_genesis_alphabet` feature-grounded + `ALG-*.yaml` 凍結語料（12 個）+ `meta_ledger` alphabet-genesis stock + `guard_alphabet_genesis` + `guard_computability_closure` + ≥12 fixture（真必要/噪音字母/冗餘字母）+ 零漏放
- [ ] ACT-149 `render_alphabet_genesis_proposal` + 可計算性閉包證據 + NoUnboundedAlphabetGenesis + 人工 gate 斷言 + chaos 雙故障型 + `R-9.33-*.yaml` + RULES_INDEX + CLAUDE.md §9 禁令#23 + INIT 追加 + ID 翻牌（147→150 / 9.33→9.34）+ test_id_registry + test_phase_u
- [ ] 五軌 TLC No error（META 13 distinct）+ chaos 100 輪 bounded（ALPHABET_GENESIS_GOODHART_FLAP + COMPUTABILITY_CLOSURE_FLAP）+ pytest 全綠不回歸（1252 → 新基線）
- [ ] 獨立 QA 稽核（Architect/SA/SD/QA 專家）抓漏 → 修復 → 全綠
- [ ] 以日期 timestamp 打標籤 push + Merge main

> **狀態流轉**：使用者 signoff →（TLA+ 五軌全綠回報）→ EXECUTING →（三 ACT + 收官全綠）→ EXECUTED →（QA 抓漏 + 修復全綠）→ VERIFIED → tag + merge main。
