# SDD_improving_Automation_22 — Phase V 藍圖（meta⁷）

**主題**：**算子組合深度文法的自我擴充（meta⁷）**——把 Phase T/U 只能在「**固定組合深度上界（`operator_genesis` 的運算式樹深度硬編 `<=2`，每算子 `cost()` 結構性 `<=3`）**」之內自我發明算子（T）/ 字母（U）的能力，推進到「系統能**自我發明一個組合深度比 2 更深的全新複合算子（= 擴充算子生成文法的『組合深度上界』這個結構參數本身）**」。並正面納管「深度外生成」憑空長出、Phase T/U（固定深度）不存在而 Phase V 才出現的**新危害類別：(i) 深度可計算性閉包危害（DepthClosure，本 Phase 靈魂，且是迄今最逼近停機問題本質的紅線）——Phase T 的「每算子 cost<=3」、Phase U 的「擴充字母表後整代數 cost<=3」之所以成立，其地基是『組合深度被人類凍結在 `<=2`，故 `cost()` 結構性是小常數』；一旦讓系統自我發明組合深度本身，`cost()` 變成深度 `d` 的單調遞增函數（本設計 `cost == depth`（一元基底）/ `depth+1`（二元基底）），「自我擴充組合深度」=「直接自我擴充計算步數」——可計算性必須由『字母表擴充下封閉』升級為『**組合深度擴充 `A_d → A_{d'}` 後，文法生成的整個（仍有限的）深度算子代數 `G(A, d')` 中每一個算子仍全函式 ∧ cost <= STEP_MAX**』的**深度閉包性質**；這是「圖靈完備 vs 保證停機」第一次反噬到框架自我擴充文法的**結構性深度參數本身（meta⁷）**——深度直接就是步數，故深度上界就是停機臨界；(ii) 組合深度無界生成爆炸（深度 `<=2` 硬編上界消失，深度可往 ∞ 長）；(iii) 深度自我發明 Goodhart（發明一個 base/chain 算子計算自己核可訊號的自指自利深度算子）**。
**目標等級**：L10 完整 · 離線活體 meta⁶ 迴圈「組合算子文法自我擴充（字母表外）」切片（Phase U 已達）→ **L10 完整 · 離線活體 meta⁷ 迴圈「算子組合深度文法自我擴充」切片**（系統不只能在**固定深度**上自我發明算子/字母，更能在**可證有界、可證深度可計算性閉包（擴充深度後整個深度算子代數仍全函式 + 有界步數）、反自利、人類掌舵本體論**的前提下，**自我發明一個組合深度 `>2` 的全新複合算子**，重構它「用**多深的運算式樹**去生成它用來量在乎之事的算子」的計算生成本體論）。
**建立日期**：2026-06-05
**前置基線**：Phase U 完整（ACT-147~149 / R-9.33，pytest 1335 passed / 4 skipped / 14 subtests；五軌 TLC 全 No error：`SDD_FSM` 42 reachable / 831 TLC distinct、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `ALPHABET_GENESIS_GOODHART_FLAP`+`COMPUTABILITY_CLOSURE_FLAP`）
**OPEN-10.6 承接**：續承 OPEN-U.x / OPEN-T.x / …——**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。L9 完整（活體 canary/shadow）與**活體 meta⁷ 元迴圈**續列 horizon；**Phase V 與 Phase N~U 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（算子組合深度文法自我擴充）**。Phase U §3.4 明示「算子組合深度自我擴充（meta⁷：自我擴充運算式樹深度上界）」為其自陳 horizon，故本份維持離線等價切片，活體版列 horizon（OPEN-V.x 承前）。**自我發明評估器（meta-oracle 自演化）續列最高 horizon**——它自指地破壞所有 Phase 賴以成立的「對抗分離地基」，採納它須先有更強的對抗分離不可繞過性證明（見 §0 thinking 三末、§3.4）。
**狀態**：✅ **使用者規格 Signoff（2026-06-05）→ EXECUTING**。依使用者執行要求「先完成 TLA+ 形式化證明並確保五軌 TLC 全綠，再撰寫 Python 執行層」。徵用 **ACT-150~152 與 Rule 9.34**（取自 `governance/ID_REGISTRY.yaml` `next_free` = act 150 / rule 9.34，單調取號）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase U §3.4 自陳 horizon「算子組合深度自我擴充（meta⁷：自我擴充運算式樹深度上界，涉及最深的步數爆炸閉包證明，因深度直接就是步數）」續推。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 150 / rule 9.34）：
> 本藍圖徵用 **ACT-150~152 與 Rule 9.34**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **收官（ACT-152）獲人工 signoff 並執行至全綠時**，才由 `id_registry` 翻牌（act 150→153 / rule 9.34→9.35）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

---

## 0. 為什麼還需要 Phase V？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~U 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~U、是自陳「L10 完整 + 離線活體 meta⁶ 迴圈（組合算子文法自我擴充 + 可計算性閉包）」的成熟框架。盲目重述提示前沿清單只會重造輪子。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase V 是否仍成立；(2) 誠實判斷「算子組合深度文法的自我擴充」到底是**Phase U 的換皮**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase V 把監督者的涵蓋面從「自我發明字母（生成規則的零件）」擴到「自我發明組合深度（生成規則的『結構性深度參數』本身）」，且首次面對『被自我擴充物直接就是步數』的最逼近停機本質的閉包問題】
Phase O~U 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase T 把停機釘進被發明的**算子**（產物）；Phase U 把停機釘進被發明的**字母表**（生成規則的零件）並證整個被生成的算子代數恆停（閉包）。

但 Phase T/U 的可計算性論證有一個**共同的、未被言明的地基**：**組合深度被人類凍結在 `<=2`**。`operator_genesis.GenesisOperator.cost()` 之所以結構性 `<=3`、`operator_alphabet_genesis.verify_computability_closure` 之所以能斷言整代數 `cost<=3`，唯一原因是運算式樹深度硬編在 `enumerate_genesis_operators`（一元 `comb(prim)`、二元 `comb(prim,prim)`）。**系統至今換得出算子、換得出字母，卻換不出『更深的運算式樹』**。Phase U 把這件事列為 horizon（§3.4）：**算子組合深度自我擴充（meta⁷，自我擴充運算式樹深度上界，涉及更深的步數爆炸閉包證明）**。這裡藏著一個**比 Phase T/U 更逼近停機問題本質的命題**：

**`cost()` 是組合深度 `d` 的單調遞增函數。** 在本設計裡，一個深度-`d` 複合算子 = 一個深度-2 基底算子（`cost` 2 或 3）外接一條長度 `d-2` 的一元 combinator 鏈，故 `cost == d`（一元基底）或 `d+1`（二元基底）——**「自我擴充組合深度」字面上就是「自我擴充計算步數」。** 這把可計算性問題推到最尖銳的形式：
- 深度外生成的危害不在於『某一個深度算子不停』（它仍是有限樹），而在於：**深度上界一旦可被系統自我擴充，`cost` 就沒有上界**——深度 `→ ∞` ⟺ `cost → ∞` ⟺ 喪失「有界步數」這條保證停機的命脈。Phase U 的 `guard_computability_closure`（枚舉**固定深度** `<=2` 的 `G(A')`）對「**深度本身被擴充**」**結構性盲目**（因為它枚舉的代數深度永遠是 2）。
- 這正是「圖靈完備 vs 保證停機」**第一次反噬到框架自我擴充文法的『結構性深度參數本身（meta⁷）』**：你敢讓系統發明自己的組合深度，就**必須證明擴充深度後文法生成的整個（仍有限的）深度算子代數中、每一個算子的 `cost` 仍 <= STEP_MAX**——而因為 `cost == depth`，這條閉包等價於**「深度有一個硬上界 = STEP_MAX」**。否則「把不可判定 LLM 包進可判定監督者」的整套地基，會因為「監督者的算子生成文法開始用無界深度去生成算子」而被從**文法的結構性深度參數的根部**蛀空。

這正是 Phase V 必須納管的、Phase T/U 尚未碰、且**比 Phase U 更逼近停機問題本質（從『生成規則的零件可證停機』到『生成規則的結構性深度參數 = 步數參數可證停機』）**的新東西——我們稱之為 **DepthClosure（深度可計算性閉包）**。

【一、誠實判斷：算子組合深度文法自我擴充是「Phase U 換皮」還是「有真缺口」？——用 grep 接地】
我先確認框架目前的組合深度**鎖死在固定 `<=2`**（grep `operator_genesis.py` 的 `enumerate_genesis_operators` 只生成一元 `comb(prim)`/二元 `comb(prim,prim)`，`cost()` 註解明寫「有界深度（<=2）運算式樹」「一元=2、二元=3」）。再 grep 三組關鍵字證明零實作：
| 關鍵字 | grep 範圍 | 命中 |
|--------|-----------|------|
| `depth.*genesis\|DepthGenesis\|DepthOperator\|invent.*depth\|expand.*depth` | `tools/` | **零** |
| `depth.*closure\|DepthClosure\|guard_depth_closure\|verify_depth_closure` | `tools/` | **零** |
| `SDD_DIM_DEPTH_LIMIT\|SDD_DIM_DEPTH_MAX\|render_depth_genesis\|NoUnboundedDepthGenesis` | `tools/` | **零** |

→ **算子組合深度文法的「自我擴充」目前零實作；系統被鎖在固定深度 `<=2` 內。** 真正的價值不在於「再加一個 depth grammar」（那是 Phase U 換皮），而在於：**深度外生成會打開三個 Phase T/U 結構性攔不住的新攻擊面，其一是迄今最深的停機危害——深度可計算性『閉包』，且因 `cost==depth` 而最直接**：
- **深度可計算性閉包危害（meta⁷ 的靈魂，迄今最逼近停機本質）**：自我發明的組合深度會讓文法生成**更深的整個算子代數**；因 `cost == depth`，深度無界 = 步數無界 = 不保證停機。Phase U 的 `guard_computability_closure`（枚舉固定深度 `<=2` 的 `G(A')`）對「深度參數本身被擴充」**完全盲目**。← 這是 Phase V 的 **PV-2 的核心**（真缺口，且是停機問題迄今最直接的升級）。
- **組合深度無界生成爆炸 + 深度自我發明 Goodhart**：深度生成**沒有 `<=2` 硬編上界**；且系統可發明一個「**深度算子的 base/chain 本身就計算 proposer/oracle/自評內部信號**」的自指深度算子。Phase U 的 feature-grounded oracle 評的是**固定字母表上發明字母在固定深度算出的特徵向量**——它對「一個**深度外、用一條事先沒見過的更深組合鏈去聚合**的算子到底必不必要、是不是自指自利」**完全盲目**。← **PV-1 的另兩面**。
- **深度外生成的計算生成本體論掌舵真空**：`steersman` 只渲染「固定深度上自我發明的算子/字母」與「（固定深度）可計算性閉包證據」；無人渲染「系統**現場發明了一個深度 `>2` 的新複合算子、它的深度生成文法來源（憑什麼有界）、它憑什麼維持深度可計算性閉包（擴充深度後整個深度算子代數仍 cost<=STEP_MAX 的閉包證據）、它憑什麼必要且非自指**」。人類掌舵在「深度外計算生成本體論發明層（meta⁷）」缺席。← **PV-3**。

【二、用提示三個指定漏洞視角，逐一往 Phase U 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在 meta⁷ 層缺「深度外發明的可有界、**深度可計算性閉包（擴充深度後整個深度算子代數 cost<=STEP_MAX）**、可反自利、feature-grounded 驗證」這一層。
Phase U 的 `operator_alphabet_genesis`（生成，固定深度的字母）↔ `dimension_necessity_oracle.evaluate_genesis_alphabet`（評估，feature-grounded）是一對 meta⁶ GAN，但**它只評固定深度 `<=2` 的算子**。當系統**現場發明一個深度 `>2` 的複合算子**，**(1) 誰保證這條深度生成不會無界爆炸？(2) 誰保證擴充深度後，文法生成的整個深度算子代數仍每個都會停（深度可計算性閉包，因 cost==depth 等價於「深度有硬上界」）？(3) 誰判「這個現場發明的深度算子到底必不必要、是不是自指自利」？** 目前無人。提示要的「生成-評估分離 + 主觀標準量化」推到 meta⁷ 層，型態是：**(1)** 生成必須被一條**有界深度生成文法**封住——「深度 `<=2` 外」不等於「無界」，而是「在一個**有限深度基底算子 × 有限一元 combinator 鏈（鏈長 <= `SDD_DIM_DEPTH_LIMIT - 2`）**的可枚舉生成空間裡生成更深算子」，節點 <= `SDD_DIM_DEPTH_BUDGET`；**(2)**（最關鍵、最逼近停機本質）深度生成文法必須**結構性保證深度可計算性閉包**——每個深度算子 = total 深度-2 基底 ∘ total 一元 combinator 鏈，`cost == depth`，故**擴充深度後文法產出的每個算子 cost 仍 <= `SDD_DIM_DEPTH_LIMIT(+1)` <= `SDD_DIM_OP_STEP_MAX` 且全函式**——**這是「深度需另證有界」的正面兌現：把深度刻意設計成一個『有硬上界 = STEP_MAX 的有限深度代數』，因 cost==depth，「深度有界」直接等於「步數有界」，讓被發明的深度生成的整個算子代數可證停機，而整個閉環仍靠 LLM+紙帶維持圖靈完備**；**(3)** 評估升級為**對深度算子（不靠算子名、靠在固定參照 probe 上的真實計算結果）的 feature-grounded 深度必要性 oracle**——量「以這個更深算子聚合，是否帶來既有所有 `<=2` 淺算子都拿不到的增量覆蓋（非線性交互）∧ 非冗餘」；外加一道**深度級自指守門**（反自利）。→ **PV-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「深度可計算性閉包（DepthClosure）」是一條 Phase T/U 不存在、直接源自「被自我擴充物是『文法的結構性深度參數 = 步數參數』而非『生成規則的零件』」的迄今最深層停機缺口。
這是 Phase V 最深、也最切題（提示明列「停機問題與防護」）的缺口。Phase U 的被發明物是「字母元素」=「生成規則的零件」，可計算性是**字母表擴充下封閉**（固定深度枚舉）。Phase V 的被自我擴充物是「組合深度上界」=「**直接決定每個算子 `cost` 的結構參數**」。新病態：深度 `→ ∞` ⟺ `cost → ∞`。新閉包危害：**(i) 深度超界**（`d > STEP_MAX` → cost > STEP_MAX → 單次呼叫就燒爆 / 不保證停機）；**(ii) 深度算子非全函式**（鏈中混入非 total 步驟）；**(iii) 深度閉包破裂**（擴充深度後，某些算子組合 cost 超界）。這是 Phase T/U（深度全人類凍結 `<=2`）時不可能、組合深度自我發明才出現的閉包停機危害。→ 需要一條**深度可計算性閉包有界停機不變量** `DepthClosureBounded`：(a) **深度算子結構性可計算**——base = total 深度-2 算子（Phase T 已證）∘ chain of total 一元 combinator（皆 total），故 `cost == depth` 且全函式；(b) **閉包驗證**——採納前 `guard_depth_closure` **枚舉擴充深度後文法生成的整個（仍有限、<= budget）深度算子代數，斷言每個算子 fuzz-total（零例外、無 NaN/inf）∧ cost() <= `SDD_DIM_OP_STEP_MAX`**，觸發即 `DepthClosureViolation` → `MFSM_ESCALATION`；(c) **零遞迴零迴圈結構保證**——深度算子求值以**有界 for 迴圈走鏈**（鏈長 = depth-2 有限），不含遞迴 / `while`（grep/ast 斷言 `operator_depth_genesis.py` 深度求值路徑無 `while`/遞迴/自呼叫）。**這正補上 Phase U 的固定深度 `guard_computability_closure` 對「深度參數本身」全盲的最深缺口。** ← **PV-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『固定深度上的算子/字母發明 + 固定深度可計算性閉包』，缺『深度外發明 diff（meta⁷）+ 深度可計算性閉包證據』」。
Phase U 的 `render_alphabet_genesis_proposal` 渲染**固定深度上**發明的字母 + 字母表閉包證據。組合深度自我擴充後，若系統現場發明一個深度 `>2` 的算子，人類面對的是「一個從未見過的更深運算式樹 + 它的 cost 就是它的深度」——**沒有人渲染『這個深度算子是系統怎麼從有限深度生成文法生成出來的、它有界嗎、它維持深度可計算性閉包嗎（擴充深度後整個深度算子代數仍 cost<=STEP_MAX）、它自指嗎、它憑什麼必要』**。提示反覆強調「人類維持設計環境掌舵者高度，而非降級為編碼員」——在「深度外計算生成本體論發明（meta⁷）」層，掌舵的最高形態是**人類能一眼看懂『系統憑空發明了哪個更深的複合算子、它的有界深度生成來源 + 深度可計算性閉包證據（擴充深度後整代數 cost<=STEP_MAX，且因 cost==depth 即「深度本身有硬上界」）+ 反自利證據 + 必要性勝率』，且系統在結構上不可能自動 commit 任何深度自我發明（每週期至多 K_depth=1 個深度發明、每個必經人工 signoff）**。→ **PV-3**（深度外計算生成本體論發明掌舵介面 + `NoUnboundedDepthGenesis`，K_depth=1，承 Phase U K_alpha=1）。

【三、停機問題紅線覆查——本份比 Phase U 更危險，因為納管的是「會憑空發明自己的組合深度（= 直接發明自己的計算步數上界）的迴圈」】
Phase U 的反諷（讓系統自我發明它的運算字母表）在 Phase V 升級為「讓系統**憑空發明自己的組合深度（自己寫文法的步數參數）**」。有界性與防自利必須再加固，且**首度必須證明被自我擴充的『結構性深度參數』維持整個深度生成代數的可計算性閉包，而這條閉包因 `cost==depth` 直接等於「深度本身有一個硬上界」**：
- **仍不新增形式化軌（承 Phase O~U「重用 META_FSM、不增軌」的成熟示範）**：深度自我發明的採納/退役全部註冊為 `META_FSM` 既有的指紋命名空間（新增 `depth-genesis:` 命名空間），其 add↔retire churn 由**同一條** `ChurnBounded`/`GraduationRatchet` 涵蓋。**但 PV-1/PV-2 揭示：churn 仍不夠**，故必須**對既有 `META_FSM` 再補兩條不變量**：`DepthGenesisBounded`（深度發明基數 stock 天花板）+ `DepthClosureBounded`（深度可計算性閉包：擴充深度後整個深度算子代數 cost<=STEP_MAX）——關鍵是**沿用 Phase P~U 的誠實作法：只新增 INVARIANT、不新增狀態變數**（`META_FSM` 維持 `<<mstate, churn, cap>>` 三變數 / 13 distinct，TLC 仍 No error，五軌不回歸；深度 stock 與深度閉包的緊語意由 runtime `guard_depth_genesis`/`guard_depth_closure` + chaos `DEPTH_GENESIS_GOODHART_FLAP`/`DEPTH_CLOSURE_FLAP` enforce/驗收，形式化層誠實標註為「single-counter 抽象之歸約引用」）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PV-1 的有界深度生成文法是硬約束，非建議**：深度自我發明的搜尋**必在有限深度生成文法（有限深度-2 基底 × 有限一元鏈、鏈長 <= `SDD_DIM_DEPTH_LIMIT-2`）內可枚舉**，節點 <= `SDD_DIM_DEPTH_BUDGET`（clamp[8,128]，預設 32）。**PV-1 的反自利是雙閘**：(a) necessity tier **唯一合法來源仍是 generator 全體碰不到、content-hashed 凍結的 feature-grounded 深度必要性 held-out 勝率**；(b) **深度級自指守門**——任何 base/chain/probe 引用保留自指信號的深度算子，在送 oracle 前即被 `depth_self_reference_guard` 攔下（零漏放）。`operator_depth_genesis` **結構性不 import oracle、不讀必要性語料**（ast/import 隔離斷言）。
- **PV-2 的深度可計算性閉包是「深度算子結構性可計算 + 閉包枚舉驗證 + 零遞迴零迴圈」三證**：深度算子由 total 步驟組成（cost==depth）；採納前 `guard_depth_closure` **枚舉擴充深度後文法生成的整個深度算子代數，斷言每個算子 fuzz-total ∧ cost <= step_max（因 cost==depth，即深度 <= step_max）**。觸發 `DepthClosureViolation` → `MFSM_ESCALATION`。**這是把停機問題正面釘進框架自我擴充文法的『結構性深度參數本身』的形式化兌現（從 Phase U 的『生成規則零件可證停機』升級為 meta⁷ 的『生成規則的步數參數可證停機』）。**
- **PROPOSED-only + 反 big-bang 深度發明，人類掌舵推到「深度外計算生成本體論發明（meta⁷）」層**：每週期至多 **K_depth=1** 個深度自我發明可進 proposed-pending-signoff（`NoUnboundedDepthGenesis`，承 Phase U K_alpha=1），每個必經人工 signoff（守 Rule 8 / 9.27~9.33）。`steersman_renderer` 渲染「深度外計算生成本體論發明 diff」。
- **自我發明評估器（meta-oracle 自演化）續列最高 horizon、本份明確不做**：Phase V 把生成端（組合深度）拉進基質 B，但**評估端（必要性 oracle）仍由人類凍結**。「讓系統自我演化它的評估器本身」會讓 generator 與 evaluator 收斂到同一基質——這**自指地破壞 Phase O~V 全部反 Goodhart 保證所賴以成立的『對抗分離』地基**。採納它須先有更強的「對抗分離不可繞過性」形式化證明，超出本份範圍，明確列為 §3.4 最高 horizon。

【四、上下文衰減（Context Degradation）視角覆查】
- 深度生成文法枚舉、feature-grounded 深度必要性 held-out 重放、深度可計算性閉包枚舉驗證全在**隔離邏輯/落盤**進行，主線只在收到 proposed 深度發明時讀「深度外發明 diff + 深度可計算性閉包證據 + 必要性勝率摘要」。深度帳本**沿用** Phase R/S/T/U 的 `value-dimension-ledger.yaml`（增 `depth_inventions` 領域審計段）+ 共用 Phase L 的 `meta-loop-ledger.yaml`（churn/depth-cardinality 治理），**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- feature-grounded 深度必要性 oracle 重用既有 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性 / 單一真實來源）：把「系統如何從有限深度生成文法**憑空發明一個深度 `>2` 的新複合算子**」「它的深度生成來源、**深度可計算性閉包證據（擴充深度後整代數 cost<=STEP_MAX，且因 cost==depth 即「深度本身有硬上界」）**、反自指證據、凍結必要性證據」全部落地為 **Markdown/YAML 可推理產物**——讓「系統如何發明它『用多深的運算式樹去生成它的算子』、以及它如何證明那套更深的代數一定會停」成為 AI 與人類都可直接推理、可審計的單一真實來源，而非藏在「深度 `<=2` 硬編」的天花板裡。
- Anthropic（生成-評估分離 / 評估器實體操作 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「字母表外字母自我發明」（U）推到**「深度外深度自我發明」**（meta⁷）——生成端用**有界深度生成文法**把無界深度空間歸約為有限可枚舉、且**結構性維持深度可計算性閉包（擴充深度後整個深度算子代數 sub-Turing：全函式 + cost==depth<=STEP_MAX）**，評估端用 **feature-grounded 深度必要性 oracle + 深度自指守門**專攻「深度自我發明 Goodhart / 自指自利深度算子」；並再次以「不增第六軌、只補 META_FSM 兩條不變量」示範「大膽移除冗餘鷹架」。你敢讓系統憑空發明它的組合深度（= 自己寫文法的步數參數），就得能形式化證明這條深度發明迴圈仍會停（深度生成有界 + 擴充深度後整個深度算子代數 cost<=STEP_MAX，因 cost==depth 即深度本身有硬上界）。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~U 落地元件**（對賬見上 thinking 一節），七條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O~U 的 obj-profile / 全評分器 calibration / value-dimension / self-invention/swap / vocab-genesis/batch-swap / operator-genesis / alphabet-genesis〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase V 的價值在用提示三漏洞視角挖出 Phase U 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase T/U 全程在「固定的組合深度 `<=2`」上自我發明算子（T）/ 字母（U）；讓系統自我發明一個深度 `>2` 的複合算子，會憑空長出 Phase T/U（固定深度）時不存在的『深度外生成』新危害——尤其是迄今最逼近停機問題本質的『深度可計算性閉包危害』（被自我擴充物第一次是『文法的結構性深度參數 = 直接決定每算子 cost 的步數參數』），以及組合深度無界生成爆炸、深度自我發明 Goodhart。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PV-1** | **系統被鎖在固定組合深度 `<=2` 內，無「深度外深度自我發明」路徑；且 feature-grounded 深度必要性驗證缺席**——系統無法發明一個深度 `>2` 的複合算子，即使硬發明也無 (i) 有界深度生成文法、(ii) feature-grounded 深度必要性 oracle、(iii) 深度級反自利守門。提示「生成-評估分離 + 主觀標準量化」在 **meta⁷（深度外發明）** 層缺席。 | `depth.*genesis\|DepthOperator\|DepthGenesis\|expand.*depth` **零命中** |
| **PV-2** | **缺『深度可計算性閉包』有界停機——迄今最深的停機缺口**——Phase T/U 的可計算性建立在「組合深度人類凍結 `<=2`、故 cost 是小常數」前提；Phase V 自我擴充組合深度本身，而 **`cost == depth`**，深度無界 = 步數無界 = 不保證停機。固定深度 `guard_computability_closure` 對「深度參數本身被擴充」全盲。這是「圖靈完備 vs 保證停機」第一次反噬到框架自我擴充文法的『結構性深度（步數）參數本身』。 | `depth.*closure\|DepthClosure\|guard_depth_closure\|verify_depth_closure` **零命中** |
| **PV-3** | **缺『深度外發明 diff（meta⁷）+ 深度可計算性閉包證據』掌舵介面**——`steersman` 只渲染固定深度上的算子/字母發明與固定深度閉包；無人渲染「系統憑空發明哪個深度 `>2` 的複合算子 + 深度生成文法來源 + 深度可計算性閉包證據（擴充深度後整代數 cost<=STEP_MAX，即深度本身有硬上界）+ 反自指證據」。人類掌舵在「深度外計算生成本體論發明層（meta⁷）」缺席。 | `render.*depth\|NoUnboundedDepthGenesis\|SDD_DIM_DEPTH_LIMIT` **零命中** |

**三缺口的共同主軸**：Phase U 讓人類站上「審系統在固定深度上自我發明字母 + 字母表可計算性閉包」的高度，但**框架的算子生成其實只能用『深度 `<=2` 硬編』的運算式樹**。Phase V 把人類抬到最高層——審「系統如何從**有界深度生成文法**憑空發明一個**深度 `>2` 的全新複合算子**（憑什麼有界、**憑什麼擴充深度後整個深度算子代數一定會停（深度可計算性閉包，且因 cost==depth 即「深度本身有硬上界 = STEP_MAX」）**、憑什麼非自指自利）」——這正是 L10 完整「離線活體元迴圈」的**算子組合深度文法自我擴充（meta⁷）**切片，精準補上提示在「狀態轉換（深度外生成-評估聯合合約）」「**停機問題（深度可計算性閉包——把停機問題正面釘進自我擴充文法的結構性步數參數本身，因 cost==depth 而最直接）**」「動態演進（深度外發明計算生成本體論而非只在固定深度組合）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase V 增量）

Phase V 對狀態機的改動延續 Phase O~U 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42 reachable / 831 TLC distinct）；**仍不新增第六條形式化軌**——深度自我發明本質上**是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「字母」泛化為「**深度 `>2` 的複合算子**」（meta⁷）。**重用既有 `META_FSM`** 並**僅補兩條不變量** `DepthGenesisBounded` + `DepthClosureBounded`（不增狀態變數），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PV-1/PV-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌、無新狀態變數）

| 元件 / 形式化層 | 命名空間 | 類型 | 阻塞? |
|------|------|------|-------|
| `operator_depth_genesis`（深度 `>2` 複合算子自我發明骨架；有界深度生成文法〔深度可計算性閉包〕+ 深度自指守門） | runtime（落 `value-dimension-ledger.yaml` `depth_inventions` 段） | 生成器骨架（advisory） | 否 |
| `dimension_necessity_oracle`（**新增 feature-grounded `evaluate_genesis_depth`**） | runtime（重用 `counterfactual_replay` 重放基座，凍結深度必要性現實情節 `DPT-*.yaml`） | 評估器（硬閘） | 否（但決定 adopt 准駁） |
| depth-genesis 採納（stock 天花板 + 深度可計算性閉包） | **新增 `depth-genesis:` 指紋命名空間**（meta-loop-ledger）+ **新增** `DepthGenesisBounded` + `DepthClosureBounded` 不變量 | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | — |
| `steersman_renderer.render_depth_genesis_proposal`（深度外發明 diff + 深度可計算性閉包證據 + 反 big-bang） | runtime（advisory） | 渲染（advisory） | 否 |

> **選位說明**：
> - `operator_depth_genesis` 把 Phase U 的字母發明**升維為深度外生成（meta⁷）**：它在一個 **bounded 深度生成文法**（有限深度-2 基底算子 × 有限一元 combinator 鏈，鏈長 `1..SDD_DIM_DEPTH_LIMIT-2`）上**可枚舉地**生成 `DepthOperator`（深度 `>2` 的複合算子，節點 <= `SDD_DIM_DEPTH_BUDGET`），**結構性保證深度可計算性閉包**（PV-2），再透過呼叫端**注入的 `evaluate` 回呼**取每個發明深度算子的必要性。它因此**結構性無法用自己的尺規證明自己必要**，且**結構性拒絕深度自指**（反自利第一閘）。
> - `dimension_necessity_oracle` 的 Phase V 升級：新增 `evaluate_genesis_depth` ——**不靠算子名匹配**，在**固定參照 probe 的凍結深度必要性語料 `DPT-*.yaml`**上，以「該更深算子」聚合量「既有所有 `<=2` 淺算子都拿不到的增量覆蓋（非線性交互）∧ 非冗餘」。
> - 深度採納的 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PV-2 的深度閉包由**新增的** `DepthClosureBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙、不動狀態變數），五軌 TLC 不回歸、不增第六軌、`META_FSM` 維持 13 distinct。

### 1.2 meta⁷ 深度自我發明迴圈 + 深度可計算性閉包定理（DepthClosure，本 Phase 數學靈魂）

#### 1.2.1 深度可計算性閉包定理（cost==depth ⇒ 深度有界等價步數有界，本 Phase 核心）

設算子字母表 `A`（Phase T 的 8 PRIMITIVES + 9 COMBINATORS）。定義 **深度生成文法**
```
G(A, d) = { chain_unary_k(... chain_unary_1( base )) : base ∈ G2(A), unary_i ∈ UNARY_COMBINATORS, 2 + k = depth ≤ d }
```
其中 `G2(A)` = Phase T 的深度-2 算子代數（`comb(prim[,prim])`）。定義**深度可計算性不變量** `I_d(A, D)`：`∀ op ∈ G(A, D)，op 全函式 ∧ cost(op) ≤ STEP_MAX`。

Phase T/U 已對 `D=2` 證得 `I_2`（每算子 cost<=3）。Phase V 自我擴充 `D=2 → D'>2`。**深度可計算性閉包定理**陳述：

> **若深度算子 `op` 結構性為「total 一元鏈 ∘ total 深度-2 基底」（base ∈ G2(A) 由 Phase T 證 total + cost∈{2,3}，每個 chain unary ∈ UNARY_COMBINATORS 皆 total + cost-1），則 `cost(op) = cost(base) + (depth-2)`，亦即一元基底時 `cost == depth`、二元基底時 `cost == depth+1`；且 `I_d(A, D')` 成立 ⟺ `D'(+1) ≤ STEP_MAX`——即深度擴充後整個深度算子代數每算子仍全函式 + 有界步數，當且僅當深度本身有一個硬上界 = STEP_MAX。**

**證明（結構歸納）**：
- **全函式**：base 由 Phase T 證 total；每步 chain unary ∈ UNARY_COMBINATORS（identity/abs/neg/clip01/sq，皆 total）。total 的合成仍 total；每步經 `_finite` 飽和投影故輸出恆有限。∴ `op` 全函式。∎
- **有界步數（cost==depth 的釘子）**：`cost(op) = cost(base) + len(chain)`。base cost ∈ {2(一元),3(二元)}、`len(chain) = depth-2`，故 `cost = depth`（一元）/ `depth+1`（二元）。因 chain 以**有界 for 迴圈**走（鏈長 = depth-2 有限、零遞迴零 while），per-operator cost **恆等於深度**（線性、非指數）。∴ `cost ≤ STEP_MAX ⟺ depth ≤ STEP_MAX`。∎
- ∴ `I_d(A, D')` 成立 ⟺ `D' ≤ STEP_MAX`：**深度可計算性閉包等價於「深度本身有硬上界 = STEP_MAX」**——這是 meta⁷ 最尖銳的形式：**自我擴充深度 = 自我擴充步數，故深度上界就是停機臨界。** ∎

**與 Phase U 的關鍵差異**：Phase U 在**固定深度 `<=2`**前提下證字母表擴充封閉；Phase V 必須證明**深度參數本身**擴充後仍維持整個深度算子代數的可計算性——而因 `cost==depth`，這條閉包**直接坍縮為一條對深度本身的硬上界**。`guard_depth_closure` 把此閉包**可機器驗證化**：採納新深度算子前，枚舉 `G(A, op.depth)`（有限、<= budget）並斷言每算子 fuzz-total + cost ≤ step_max；若閉包中任一算子違反，該深度算子被拒 → `DepthClosureViolation` → `MFSM_ESCALATION`。

這是「把停機問題釘進自我擴充文法的**結構性深度參數本身**（meta⁷）」——Phase U 把停機釘進被發明的字母（生成規則的零件）；Phase V 把停機釘進被自我擴充的**組合深度（= 直接決定每算子步數的結構參數）**，且因 `cost==depth` 而最直接。

#### 1.2.2 迴圈控制流（重用 META_FSM 有界停機契約 + 有界深度生成文法 + 深度可計算性閉包三證 + 反自利雙閘）

```
（離線、跨 session）operator_depth_genesis.depth_genesis_round()
  在 bounded 深度生成文法（G2 基底 × 一元鏈，鏈長 1..SDD_DIM_DEPTH_LIMIT-2，可枚舉節點 <= SDD_DIM_DEPTH_BUDGET）生成候選深度算子 e
    [深度可計算性閉包結構保證] 每個 e = total base ∘ total 一元鏈 → cost == depth（零遞迴零 while，PV-2）
    depth self-reference guard：base/chain/probe 引用保留自指信號 → 結構性丟棄（反自利第一閘，不送 oracle）
    對每個倖存 e：必要性 = 注入的 evaluate(e)（= feature-grounded oracle 增量覆蓋；genesis 看不到語料）
  取至多 K_depth=1 個必要性最高的候選（NoUnboundedDepthGenesis）→ 深度自我發明 e*
  → dimension_necessity_oracle.evaluate_genesis_depth(e*)：在「genesis 全體不可見、content-hashed 凍結」的固定 probe 深度必要性情節上，
       以「該更深算子」聚合量 (a) 增量覆蓋（既有所有淺算子拿不到的非線性交互）+ (b) 非冗餘度
     ├─ 增量覆蓋 ≥ margin ∧ 非冗餘度 < 門檻 → 取得「必要性 tier++」
     │     → 產 proposed 深度發明 + 深度可計算性閉包證據 + 必要性證據 → steersman 渲染深度外發明 diff → 人工 signoff
     │     └─ 人工接受 → guard_depth_closure（枚舉 G(A, depth) 整代數 total + cost<=step_max）→ guard_depth_genesis（深度 stock 未滿）→ record_rule_add("depth-genesis:hash(e*)")
     └─ 未達必要性（含「自指自利深度算子」「深度外噪音算子」）→ 拒絕提案 → 純記錄

（採納守門，任一觸頂 → MFSM_ESCALATION 人工裁決）
  guard_depth_closure(e)（PV-2）：枚舉 G(A, e.depth) 任一算子 cost > STEP_MAX 或 apply() fuzz 非全函式 → DepthClosureViolation
  guard_depth_genesis(fp)（PV-1）：現存活躍 depth-genesis 算子數 >= SDD_DIM_DEPTH_MAX → DepthCardinalityExceeded
```

- **核心有界性（重用既有證明 + 兩條新不變量）**：
  - 深度生成（PV-1）：深度自我發明在**有限深度生成文法**內可枚舉，節點 <= `SDD_DIM_DEPTH_BUDGET`（clamp[8,128]，預設 32），且**鏈長 <= `SDD_DIM_DEPTH_LIMIT-2`**（深度 <= `SDD_DIM_DEPTH_LIMIT`，clamp[2,16]，預設 6），**絕不無界爆炸**。
  - **深度可計算性閉包（PV-2 新增 `DepthClosureBounded`）**：每個深度算子 cost==depth；採納前 `guard_depth_closure` 枚舉 `G(A, depth)` 整代數驗 total + cost <= `SDD_DIM_OP_STEP_MAX`（即深度 <= step_max），觸發 `DepthClosureViolation` → `MFSM_ESCALATION`。
  - 深度 stock（PV-1 新增 `DepthGenesisBounded`）：現存活躍 `depth-genesis:` 算子數 <= `SDD_DIM_DEPTH_MAX`（clamp[1,64]，預設 16）；觸頂 `guard_depth_genesis` raise `DepthCardinalityExceeded` → `MFSM_ESCALATION`。
  - per-fingerprint：churn <= `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納須挾必要性 tier 嚴增（既有 `GraduationRatchet`）。
- **反自利雙閘（PV-1）**：(a) `necessity_tier` 唯一合法來源是凍結 feature-grounded 深度必要性 held-out oracle（增量覆蓋 ∧ 非冗餘）勝率——genesis 自評**結構性禁止**充當（ast/import 隔離斷言、genesis 無讀寫權、不 import oracle）；(b) **深度自指守門結構性拒絕**——任何 base/chain/probe 引用保留自指信號的深度算子在送 oracle 前即被 `depth_self_reference_guard` 攔下（零漏放）。把「生成-評估分離 + 反自利」釘死在 **meta⁷** 層級。

### 1.3 典型軌跡（含 Phase V 改善後的 self-verification 案例）

```
（跨 session 收官）depth_genesis_round：近 5 session 落盤顯示「既有所有深度 <=2 淺算子都不量某類『正規化後的平方離散度（先 diff 再 sq 再 clip01）』這種需要 3 層組合才表達的非線性交互」
  → operator_depth_genesis 在深度生成文法（G2 基底 diff(max,min) × 一元鏈 sq∘clip01）枚舉候選深度-4 算子；depth self-ref guard 丟棄引用 self_score 的誘餌；每個候選結構性 cost==depth
  → 注入 evaluate（feature-grounded 深度必要性 oracle）給 e*="op::clip01(sq(diff(max,min)))" 高分；K_depth=1 取此一者
  → evaluate_genesis_depth：在 50 筆固定 probe 凍結深度必要性情節 → augmented 0.85 vs baseline（所有淺算子）0.60（增量覆蓋 Δ=0.25 ≥ margin 0.10）；非冗餘度 0.42 < 門檻
  → 取得必要性 tier++ → guard_depth_closure：枚舉 G(A, depth=4) 全代數 → 每個 fuzz-total ∧ cost<=8（depth 4 <= 8）✅ → proposed 深度發明 → steersman 渲染「深度外計算生成本體論發明（meta⁷）：系統憑空發明深度-4 複合算子『op::clip01(sq(diff(max,min)))』+ 深度生成文法來源 + 深度可計算性閉包✅（G(A,4) 整代數 cost==depth<=8，即深度本身有硬上界）+ 25% 增量覆蓋」
  → 人工 signoff → 深度 stock 未滿 → record_rule_add("depth-genesis:hash(e*)")

（深度閉包攻擊案例：深度超界算子）operator_depth_genesis（受擾）被要求構造一個深度 > STEP_MAX 的算子（鏈長爆）
  → 有界深度文法鏈長硬上界 SDD_DIM_DEPTH_LIMIT-2（結構保證）；若硬注入超界深度算子 → guard_depth_closure 枚舉 G(A,depth) 發現 cost==depth > STEP_MAX → raise DepthClosureViolation → MFSM_ESCALATION（被發明的步數參數本身的停機被守門封死，PV-2 核心：因 cost==depth，深度超界 = 步數超界）

（深度閉包攻擊案例：非全函式深度算子）注入一個 chain 含未知/非 total 步驟的深度算子
  → 深度算子由 total base ∘ total 一元鏈組成（_finite 飽和投影）→ guard_depth_closure 枚舉 G(A,depth) fuzz 任何輸入零例外；fuzz-total 零漏放

（深度自我發明 Goodhart 攻擊案例：自指自利深度算子）生成 e**="op::identity(...self_score...)"（深度算子計算自己核可訊號）
  → depth self-reference guard：base/chain/probe 含保留自指信號 → 結構性丟棄，根本不送 oracle（反自利第一閘，零漏放）

（深度外噪音算子）生成一個真實增量覆蓋為 0 的更深算子（深度雖增但無新非線性交互）
  → feature-grounded oracle：augmented vs baseline 增益 ≈ 0 < margin → 不取得 tier → 拒絕

（深度無界生成爆炸）operator_depth_genesis 被要求枚舉超大深度生成文法
  → 文法枚舉節點達 SDD_DIM_DEPTH_BUDGET + 鏈長達 SDD_DIM_DEPTH_LIMIT-2 → 截斷停止（best-so-far），絕不指數爆炸

（深度基數爆炸）系統反覆發明不同的真必要深度算子（每個首採、churn=0）
  → guard_depth_genesis：現存活躍 depth-genesis 數逼近 SDD_DIM_DEPTH_MAX → DepthCardinalityExceeded → MFSM_ESCALATION → steersman 導人工「深度算子已過度膨脹」
```

**對比 Phase U 現況**：（a）只能在固定深度 `<=2` 上自我發明算子/字母，無任何深度外發明路徑；（b）即使硬加 depth grammar，沒有任何機制保證「自我發明的深度擴充後整個深度算子代數一定會停（深度可計算性閉包，因 cost==depth 即深度本身有硬上界）」、攔得住「深度無界生成爆炸 / 自指自利深度算子」。Phase V 讓系統**能有界地自我發明深度 `>2` 的新複合算子、且每個發明深度算子必須在有界深度文法內生成 + 結構性維持深度可計算性閉包（擴充深度後整代數 cost==depth<=STEP_MAX）+ 非自指 + 在 genesis 全體碰不到的凍結 feature-grounded 現實試金石上證明真的必要且非冗餘**——人類從「審固定深度上的字母發明」升為**「審深度外計算生成本體論發明（meta⁷）」**，精準對應提示「人類維持設計環境掌舵者高度」於**最深的深度外計算生成本體論發明層**，且**把停機問題正面釘進框架自我擴充文法的結構性步數參數本身（因 cost==depth 而最直接）**。

---

## 2. 環境建構與記憶體管理策略（Phase V 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/value-dimension-ledger.yaml`（**沿用** Phase R/S/T/U，新增 `depth_inventions` 領域審計段）：跨 session 深度外發明提案（發明深度算子 hash、深度生成文法來源 base·chain·probe、是否自指、是否維持深度可計算性閉包、feature-grounded 必要性、necessity tier、人工 signoff 狀態）。**落盤不常駐**，按需 lazy 讀。churn/depth-cardinality 治理走**共用 `meta-loop-ledger.yaml`**（`depth-genesis:` 命名空間，沿用 Phase Q~U）。
- `knowledge/held-out-corpus/`（**擴充**既有目錄，content-hashed 凍結）：新增 **feature-grounded 深度必要性情節語料 `DPT-*.yaml`**（歷史情節 + 候選**固定參照 probe 特徵向量** + 已知整體真實結果），供 `evaluate_genesis_depth` 重放；**`operator_depth_genesis` 程式路徑禁止讀寫**（隔離斷言）；重用 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`。**12 個凍結 `DPT-*.yaml` 皆為真必要基準試金石（`expect: true_depth`）；噪音 / 冗餘深度算子的 Goodhart 攻擊由測試端構造在該語料上驗拒（zero-miss），非語料檔本身含噪音 / 冗餘分類。**
- `build/reports/value-dimension/DPT-{date}.md`（新增）：深度外發明提案報告（深度發明 diff + 深度生成文法來源 + 深度可計算性閉包證據 + 反自指證據 + 增量覆蓋/非冗餘證據 + 本週期 K_depth 標示），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——深度發明元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 新增 `depth-genesis:` 指紋命名空間（不改 `.tla` 狀態宇宙、不增狀態變數）、(b) 對 `META_FSM.tla` **補兩條 INVARIANT** `DepthGenesisBounded` + `DepthClosureBounded`（沿用 P~U 對既有界的誠實作法：single-counter 抽象之歸約引用 + runtime/chaos enforce 緊語意）——**新增不變量而非新增狀態/變數**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 全 safety + liveness + P~U 各不變量涵蓋深度發明元迴圈，**另補** `DepthGenesisBounded`（深度 stock 天花板）+ `DepthClosureBounded`（深度可計算性閉包）；新增測試斷言「深度發明走獨立 `depth-genesis:` stock 天花板、深度算子受深度可計算性閉包三證（擴充深度後整代數全函式 + cost<=step_max + 零遞迴零迴圈）封死、且皆過 `meta_halt_monitor`」。
- `operator_depth_genesis` 鷹架本身納入 `scaffold_roi` 帳本，由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **深度自我發明守門**：(a) 生成在有限深度文法內可枚舉、節點 <= `SDD_DIM_DEPTH_BUDGET`、鏈長 <= `SDD_DIM_DEPTH_LIMIT-2`（測試斷言搜尋有界）；(b) 深度自指守門結構性拒絕（測試斷言 depth self-ref guard 零漏放）；(c) **深度可計算性閉包三證**（測試斷言枚舉 G(A,depth) 整代數 fuzz-total 零例外 + cost<=step_max + 深度求值路徑無 `while`/遞迴）；(d) `operator_depth_genesis` 只能**提案**，**不能自動納入**（測試斷言無法繞過 `human_signoff` + `guard_depth_genesis` + `guard_depth_closure`），且**每週期至多 K_depth=1 個深度發明**（`NoUnboundedDepthGenesis`）。

### 2.3 Prompt / 上下文與防衰減
- Phase V **不新增任何常駐 eager prompt**。深度文法枚舉、feature-grounded 深度必要性重放、深度可計算性閉包枚舉驗證皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 深度發明時讀「深度外發明 diff + 深度可計算性閉包證據 + 必要性勝率摘要」。
- 所有新產物（深度發明帳本 / 深度必要性語料 / 提案報告）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-150~152）

> **3 ACT 整併說明**：Phase V 依使用者 Signoff 範圍（ACT-150~152）將四柱 + 收官整併為 3 個實質 ACT；每 ACT 仍以客觀守門（pytest / 五軌 TLC / chaos / fuzz）驗收。**形式化證明（ACT-151 META_FSM 兩不變量 + 五軌 TLC）先於 Python 執行層完成並回報**（使用者執行要求）。

#### ACT-150 — Operator Depth Genesis Grammar + 有界深度生成文法（深度可計算性閉包）+ 深度自指守門（PV-1 深度外生成 meta⁷ + PV-2 閉包結構保證）
- **檔案**：`tools/fsm_runtime/operator_depth_genesis.py` + `build/state/value-dimension-ledger.yaml`（沿用，增 `depth_inventions` 段）
- **設計**：定義 `DepthOperator`（由 `base`〔operator_genesis.GenesisOperator 深度-2 基底〕+ `chain`〔一元 UNARY_COMBINATORS 序列，鏈長 `1..SDD_DIM_DEPTH_LIMIT-2`〕+ namespace `depth-genesis:` + 凍結 rationale）與**有界深度生成文法**（base 取自 `operator_genesis.enumerate_genesis_operators` × 一元鏈 deterministic 枚舉）。`DepthOperator.apply(features)` = 以**有界 for 迴圈走鏈**套用一元 combinator 於 base 標量（全函式、cost==depth、零遞迴零 while）；`depth` = `2 + len(chain)`；`cost()` = base cost + `len(chain)`（== depth〔一元基底〕/ depth+1〔二元基底〕）；`is_total()` fuzz；`fingerprint()` 落 `depth-genesis:`；`enumerate_genesis_depth(budget, depth_limit)` deterministic cap budget + 鏈長界；`depth_self_reference_guard`；`depth_genesis(evaluate, budget)` 注入 evaluate 找最佳；`depth_genesis_round(evaluate, k=1)` 反 big-bang K_depth=1 截斷；`verify_depth_closure(e)` 枚舉 `G(A, e.depth)` 整代數驗 fuzz-total + cost<=step_max（PV-2 閉包，可機器驗證）。純離線、deterministic。**只提案、絕不自動納入、絕不自寫常數**（守 Rule 8 / 9.34.4）。**結構性不 import oracle、不讀必要性語料**（對抗分離）。深度求值路徑**零 `while`/零遞迴/零自呼叫**（PV-2 結構保證；唯一的 for 是有界鏈走訪）。
- **驗收**：≥4 情境 fixture（深度外真必要發明〔應提〕/ 深度已足夠〔應不提〕/ 自指自利深度算子誘餌〔depth self-ref guard 攔〕/ deterministic 可重現）；生成節點 <= `SDD_DIM_DEPTH_BUDGET` 且深度 <= `SDD_DIM_DEPTH_LIMIT`；depth self-reference guard 零漏放；**深度可計算性閉包：對枚舉的整個深度算子代數 × 多組極端輸入（空/單元素/負/0/極大含浮點上限 1e200/1e308）做 fuzz，零例外、無 inf、無 nan + 整代數每算子 cost <= `SDD_DIM_OP_STEP_MAX` 且 cost==depth**；ast 斷言深度求值路徑無 `while`/遞迴；ast/import 斷言 genesis 對 oracle 隔離。

#### ACT-151 — feature-grounded 深度必要性反 Goodhart 評估（`evaluate_genesis_depth`）+ 深度 stock + 深度閉包守門 + META_FSM 兩不變量重證（PV-1 核心 + PV-2；不增第六軌，只補兩條不變量）
- **檔案**：`tools/fsm_runtime/dimension_necessity_oracle.py`（新增 `DepthCandidate`/`DepthCase`/`evaluate_genesis_depth`/`necessity_score_depth`/`load_depth_corpus`/`depth_corpus_fingerprint`）+ `knowledge/held-out-corpus/DPT-*.yaml`（凍結深度必要性情節，12 個）+ `tools/fsm_runtime/meta_halt/meta_ledger.py`（增 `depth-genesis:` 命名空間判定 + `active_depth_genesis_features` stock 查詢）+ `meta_halt_monitor.py`（`guard_depth_genesis` + `DepthCardinalityExceeded`；`guard_depth_closure` + `DepthClosureViolation`；`meta_state` 觸頂升 ESCALATION + env getter `dim_depth_max`）+ `operator_depth_genesis.py`（本地 `depth_budget`/`depth_limit` getters，沿用 `alphabet_budget` 慣例；`adopt_genesis_depth` 走 `guard_depth_closure` → `guard_depth_genesis`）+ `formal/META_FSM.tla`（**新增 INVARIANT** `DepthGenesisBounded` + `DepthClosureBounded`，**不新增狀態/變數**）+ `META_FSM.cfg`（INVARIANT 區塊列入）
- **設計**：`evaluate_genesis_depth` 重用 `counterfactual_replay`/`SDD_REPLAY_MAX_CASES`；**不靠算子名匹配**——對一個現場發明的深度算子，用它套到 case 特徵向量現算 `dim_value`，量 (a) **增量覆蓋**（augmented〔既有所有淺算子最佳 + 深度算子〕vs baseline〔僅淺算子最佳〕）+ (b) **非冗餘度**，回 `DimensionVerdict`。**結構性隔離**：深度必要性語料路徑與 `operator_depth_genesis` 互斥。深度採納 = 先 `guard_depth_closure`（枚舉 G(A,depth) 整代數 total + cost<=step_max，PV-2）再在深度 stock 未滿時 `record_rule_add("depth-genesis:…")`。**不改 `META_FSM.tla` 狀態宇宙、不增狀態變數**，僅補兩不變量。
- **驗收**：≥12 fixture（6 深度外真必要發明〔增量覆蓋 ≥ margin ∧ 非冗餘〕+ 3 深度外噪音算子假必要〔增量覆蓋 0〕+ 3 冗餘深度算子〔增量覆蓋 > 0 但非冗餘度 ≥ 門檻〕）；真必要偵出率 ≥ 85%、**深度自我發明 Goodhart（噪音+冗餘）攔截率 100%（零漏放，安全紅線）**；`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT `DepthGenesisBounded` + `DepthClosureBounded` PASS）；新增 test 斷言「深度 stock 觸頂 → `DepthCardinalityExceeded` → `MFSM_ESCALATION`」「深度超界算子 → `DepthClosureViolation` → `MFSM_ESCALATION`」「非全函式深度算子被 guard 攔」；**五軌 TLC 全不回歸**。
  - **釐清（DPT 語料 vs 攻擊 fixture）**：12 個凍結 `DPT-*.yaml` 語料**皆為真必要基準試金石**（`expect: true_depth`）；噪音 / 冗餘深度算子的 Goodhart 攻擊是在 `test_phase_v.py` 測試端以 `_noise_depth_case`/`_redundant_depth_case` + 候選深度算子構造在該語料上**驗拒**（zero-miss），**非語料檔本身含 3 噪音 + 3 冗餘分類**。

#### ACT-152 — Steersman 深度外發明 diff + 深度可計算性閉包證據 + NoUnboundedDepthGenesis + 治理落地 + 收官（PV-3 + R-9.34 + chaos + 全綠驗收）
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_depth_genesis_proposal`）+ `tools/fsm_runtime/chaos_runner.py`（新增 `DEPTH_GENESIS_GOODHART_FLAP` + `DEPTH_CLOSURE_FLAP` + 兩 helper）+ `governance/rules/R-9.34-self-expanding-operator-depth-phase-v.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#24 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `governance/ID_REGISTRY.yaml` 翻牌（act 150→153 / rule 9.34→9.35）+ `test_id_registry.py` 前緣斷言 + Phase V ownership 測試 + `tools/fsm_runtime/tests/test_phase_v.py`
- **設計**：`render_depth_genesis_proposal` 渲染「本輪深度外發明 diff（系統憑空發明哪個深度 `>2` 複合算子 + 深度生成文法來源〔base·chain〕+ **深度可計算性閉包證據**〔擴充深度後 G(A,depth) 整代數 total ✅ + cost==depth<=step_max〕+ 是否自指〔non-self-ref 證據〕+ 增量覆蓋與非冗餘證據）+ 本週期 ≤K_depth=1 標示」，**advisory**；任一深度發明納入 **必經人工 signoff**，渲染器絕不自動納入、絕不自動 commit。子規則 9.34.1~9.34.5 見 §4。
- **Chaos**：100 輪新增兩故障型 `DEPTH_GENESIS_GOODHART_FLAP`（連續注入自指自利深度算子 / 深度外噪音算子假必要 → 驗 depth self-ref guard + feature-grounded oracle 零漏放）與 `DEPTH_CLOSURE_FLAP`（注入深度超界 / 非全函式深度算子 → 驗 `DepthClosureBounded` → `DepthClosureViolation` → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K_depth=1 上限、深度生成文法來源、深度可計算性閉包（整代數 total + cost==depth<=step_max）、非自指」；斷言渲染器無法自呼叫 adopt / `record_rule_add` / `adopt_genesis_depth`；K_depth+1 個深度發明同週期 → 被截到 1 並標示「其餘順延」；**五軌 TLC 全 No error（META 13 distinct）+ chaos 100 輪 bounded（兩新故障型）+ pytest 全綠不回歸（1335 → 約 1375~1405 passed）**；`python -m tools.fsm_runtime.id_registry validate` → `[OK]`，next_free 翻 ACT-153 / R-9.35。

### 3.2 執行依賴圖

```
ACT-150（operator_depth_genesis + 有界深度生成文法〔深度可計算性閉包〕+ 深度自指守門）──┐
                                                                       ├─► ACT-151（evaluate_genesis_depth + 深度 stock + guard_depth_closure + META 兩不變量重證〔五軌 TLC〕）──► ACT-152（steersman 深度外發明 diff + R-9.34 治理 + chaos 雙故障型 + ID 翻牌 + pytest 全綠）
                                                                       │
TLA+ 形式化（META_FSM 兩不變量 + 五軌 TLC 全綠）先於 Python 執行層完成並回報（使用者執行要求）
```

### 3.3 等級對賬（提示「Level 10」× 框架自有 L 量表）

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L10 完整 · 離線活體 meta⁵ 迴圈 · 轉換算子文法自我擴充 | Self-Expanding Operator Grammar + OperatorComputabilityBounded | T |
| L10 完整 · 離線活體 meta⁶ 迴圈 · 組合算子文法自我擴充 | Self-Expanding Operator Alphabet + ComputabilityClosureBounded | U |
| **L10 完整 · 離線活體 meta⁷ 迴圈 · 算子組合深度文法自我擴充** | **Self-Expanding Operator Depth：深度 `<=2` 外有界深度生成文法 + feature-grounded 深度必要性反 Goodhart + 深度自指守門（反自利）+ DepthGenesisBounded（深度基數停機）+ DepthClosureBounded（深度可計算性閉包停機——把停機問題正面釘進自我擴充文法的結構性步數參數本身，因 cost==depth 而最直接）** | **V（本份 PV-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-V.x/U.x/… 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體** meta⁷ 發明 + **自我發明評估器（meta-oracle 自演化）** | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版、亦不做自我發明評估器**。完整 L10 之「活體 meta⁷ 迴圈」需在真實生產流量上線上自我發明深度（受 OPEN-10.6 約束）；「自我發明評估器」自指地破壞對抗分離地基（須先有更強的對抗分離不可繞過性證明）。本份交付**離線等價切片**：用框架自身歷史的 feature-grounded 深度必要性 held-out 現實代理語料當試金石，**在本地完成「深度 `<=2` 外有界深度自我發明 + 深度可計算性閉包」的等價驗證價值**。承 Phase O~U 的「先窄後寬」紀律，本份把「固定深度上字母發明」推進為「深度外深度自我發明」，並把深度外才出現的危害（深度可計算性閉包 / 深度無界生成 / 自指自利深度算子）首次納管——這是 Phase U 自陳 horizon 的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-V.x/U.x/… 已裁決暫不放寬 OPEN-10.6，續列 horizon。
- **活體 meta⁷ 發明**：本份離線（feature-grounded 深度必要性 held-out 現實代理）；活體版需在生產流量上線上自我發明深度，受 OPEN-10.6 約束（OPEN-V.x 承前）。
- **自我發明評估器（meta-oracle 自演化）**：**最高 horizon**。本份所有 oracle（必要性 / 詞彙 / 算子 / 字母 / 深度必要性）為人類凍結；「系統自我演化它的**評估器本身**」涉及對抗分離地基自指（generator 與 evaluator 收斂同基質會掏空全部反 Goodhart 保證），須先有「evaluator-of-evaluators 的、generator 全體碰不到的更高階 held-out meta-corpus + 其本身反自利證明」的對抗分離不可繞過性證明。**未獲此證明前不得採納**（守 Rule 9.34.5）。
- **算子間互遞迴 / 圖靈完備算子代數（meta⁸）**：本份深度算子為「有界深度 + cost==depth 的非遞迴運算式樹」；「系統自我發明可互相呼叫 / 帶記憶的算子代數」會逸出 sub-Turing 保證，列最高停機 horizon（須全新的停機判定機制，非有界步數可涵蓋）。

---

## 4. 防護規則新增（CLAUDE.md §9.34 Phase V — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.34.1 深度生成文法自我擴充骨架（DepthGenesis / BoundedDepthGrammar，meta⁷） | ACT-150 | 深度 `<=2` 外深度自我發明經 `operator_depth_genesis` 在 **bounded 深度生成文法**（有限 G2 基底 × 一元鏈，鏈長 <= `SDD_DIM_DEPTH_LIMIT-2`）**可枚舉**、節點 <= `SDD_DIM_DEPTH_BUDGET`（clamp[8,128] 預設 32）、深度 <= `SDD_DIM_DEPTH_LIMIT`（clamp[2,16] 預設 6）；「深度 `<=2` 外」≠「無界」；只提案、絕不自動納入、絕不自寫常數；**結構性不 import oracle / 不讀必要性語料**（對抗分離，編譯期隔離斷言） |
| 9.34.2 深度自我發明反自利（DepthGenesisAntiSelfInterest） | ACT-150/151 | 深度自我發明的 capability-delta tier **唯一合法來源是 genesis 不可見、content-hashed 凍結的 feature-grounded 深度必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率**；genesis 自評**結構性禁止**充當；**genesis 自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準**；**深度自指守門結構性拒絕**（base/chain/probe 引用保留自指/proposer/oracle 內部信號 → `depth_self_reference_guard` 攔，零漏放）；深度外噪音算子/冗餘深度算子攔截零漏放 |
| 9.34.3 深度可計算性閉包有界停機（DepthClosureBounded，PV-2 核心、迄今最深停機紅線，因 cost==depth 而最直接） | ACT-150/151/152 | 每個自我發明深度算子**結構性保證擴充深度後整個深度算子代數全函式 + 有界步數 + 零遞迴零迴圈**：(a) 深度算子 = total 深度-2 基底 ∘ total 一元 combinator 鏈 → `cost == depth`（一元基底）/ depth+1（二元基底）；(b) 採納前 `guard_depth_closure` **枚舉擴充深度後 G(A,depth) 整個深度算子代數，斷言每算子 fuzz-total（零例外、無 NaN/inf）∧ cost() <= `SDD_DIM_OP_STEP_MAX`（因 cost==depth，即深度 <= step_max）**；(c) 深度求值路徑零 `while`/零遞迴/零自呼叫（唯一 for 是有界鏈走訪）；觸發 `DepthClosureViolation` → `MFSM_ESCALATION`。這把「圖靈完備 vs 保證停機」正面釘進框架自我擴充文法的**結構性深度（步數）參數本身**——自我擴充深度 = 自我擴充步數，故深度上界就是停機臨界，而整個閉環仍靠 LLM+紙帶維持圖靈完備 |
| 9.34.4 深度基數 + 反 big-bang 深度發明（DepthGenesisBounded + NoUnboundedDepthGenesis） | ACT-151/152 | (i) 現存活躍 `depth-genesis:` 算子數 <= `SDD_DIM_DEPTH_MAX`（clamp[1,64] 預設 16）→ 觸頂 `DepthCardinalityExceeded` → `MFSM_ESCALATION`（`guard_depth_genesis`）；(ii) 每週期至多 **K_depth=1**（`SDD_DIM_EXPAND_K` 預設 1，沿用 Phase Q~U）個深度自我發明可進 proposed-pending-signoff，每個必經人工 signoff（守 Rule 8 / 9.27~9.33）；genesis/steersman 絕不自動 commit、絕不自動納入、絕不一次劫持整個深度本體論；退役深度算子再採納須挾 necessity capability-delta（沿用 `GraduationRatchet`）；**重用既有 `META_FSM`、僅補 `DepthGenesisBounded` + `DepthClosureBounded` INVARIANT、不增狀態/變數、不增第六軌**；五軌 TLC 全不回歸、深度發明不污染單軌 `SDD_FSM.tla` |
| 9.34.5 深度自我發明誠實 + 活體/meta-oracle horizon | ACT-151/152 | feature-grounded 深度必要性勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；算子間互遞迴 / 圖靈完備算子代數（meta⁸）+ **自我發明評估器（meta-oracle 自演化，最高 horizon——未獲對抗分離不可繞過性證明前不得採納）** + 活體 meta⁷ 發明版受 OPEN-10.6 約束續列 horizon（OPEN-V.x 承 OPEN-U.x/… 暫不放寬沙箱） |

### ❌ Phase V 新增禁止行為（草案）
- `operator_depth_genesis` 自動納入深度自我發明 / 自寫常數、繞過人工 signoff + `guard_depth_genesis`/`guard_depth_closure`（破 9.34.1/9.34.4 / Rule 8）
- 用 genesis 自評充當「深度自我發明必要性 capability-delta tier」（破 9.34.2，深度自我發明 Goodhart 自評放水）
- 深度自我發明 base/chain/probe 自指（引用保留自指 / proposer / oracle 內部信號繞過 `depth_self_reference_guard`）（破 9.34.2 反自利）
- `operator_depth_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/DPT-*` 深度必要性語料或 `dimension_necessity_oracle`（破 9.34.2 對抗分離）
- 深度自我發明搜尋超 `SDD_DIM_DEPTH_BUDGET` 仍指數展開、或鏈長超 `SDD_DIM_DEPTH_LIMIT-2`（破 9.34.1 有界深度文法，「深度 `<=2` 外」≠「無界」）
- **自我發明的深度算子使擴充深度後 G(A,depth) 整個深度算子代數出現非全函式 / cost 超 `SDD_DIM_OP_STEP_MAX`（因 cost==depth，即深度超界）/ 求值路徑含遞迴/`while`/自呼叫的算子（破 9.34.3 深度可計算性閉包——被自我擴充的步數參數本身不可證停機）**
- 現存活躍 depth-genesis 算子超 `SDD_DIM_DEPTH_MAX` 仍無界擴充（破 9.34.4 DepthGenesisBounded）
- 一週期同時深度自我發明 > K_depth 個（破 9.34.4 NoUnboundedDepthGenesis）
- 把 depth-genesis 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.34.4 / Rule 9.18.1）
- **未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（破 9.34.5——掏空全部反 Goodhart 對抗分離地基）**
- 為活體 meta⁷ 發明私自開 HTTP 外聯而未經 OPEN-V.x/後續 OPEN 人工決策（破 OPEN-10.6）

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

### 5.2 Phase V 專屬極端案例（一）：深度可計算性閉包——深度超界 / 步數爆炸（PV-2 核心，迄今最直接）
**案例**：operator_depth_genesis 受擾，被要求構造一個深度 > STEP_MAX 的算子（鏈長爆），企圖讓「該算子」單次呼叫燒爆 token / 不停機。
- **有界深度文法結構保證**：鏈長 <= `SDD_DIM_DEPTH_LIMIT-2`，**深度求值以有界 for 走鏈、根本不含遞迴/`while`/巢狀掃描**（grep/ast 斷言深度求值路徑零 `while`/零遞迴）。
- **`DepthClosureBounded`（閉包驗證）**：採納前 `guard_depth_closure` 枚舉 `G(A,depth)` 整代數，若任一算子 cost==depth > `SDD_DIM_OP_STEP_MAX` 或 fuzz 非全函式 → raise `DepthClosureViolation` → `MFSM_ESCALATION`。
- chaos `DEPTH_CLOSURE_FLAP` 100 輪 → bounded。
✅ 守 Rule 9.34.3：把停機問題正面釘進框架自我擴充文法的**結構性步數參數本身**，**因 cost==depth，深度超界 = 步數超界，絕不無界計算**。

### 5.3 Phase V 專屬極端案例（二）：非全函式深度算子
**案例**：operator_depth_genesis 生成一個 chain 含非 total 步驟的深度算子。
- **閉包全函式結構保證**：base 由 Phase T 證 total、chain unary 皆 total + `_finite` 飽和投影；`guard_depth_closure` 枚舉 G(A,depth) 對全部算子 × 極端輸入 fuzz 零例外、無 inf/nan。
✅ 守 Rule 9.34.3：深度算子代數全函式，**對任何輸入有定義、永不崩潰**。

### 5.4 Phase V 專屬極端案例（三）：深度自我發明 Goodhart——自指自利深度算子
**案例**：發明一個 base/chain 計算 proposer 自己核可訊號的深度算子。
- **depth self-reference guard**（反自利第一閘）：base/chain/probe 含 `self_score`/`proposer_*` → 結構性丟棄，根本不送 oracle（零漏放）。
- 若繞過 guard 假設送達 → feature-grounded oracle augmented vs baseline 增益 ≈ 0 → 不取得 tier（第二閘）。
- chaos `DEPTH_GENESIS_GOODHART_FLAP` 100 輪 → guard+oracle 零漏放 → bounded。
✅ 守 Rule 9.34.2：雙閘皆否 → 絕不擴充自指自利深度算子（零漏放，安全紅線）。

### 5.5 Phase V 專屬極端案例（四）：深度無界生成爆炸 + 深度基數爆炸
**案例**：operator_depth_genesis 被要求在深度 `<=2` 外無界枚舉撐爆搜尋；或反覆發明不同真必要深度算子把深度本體論無限膨脹。
- **有界深度生成文法**：生成空間 = G2 基底（有限）× 一元鏈（鏈長 <= `SDD_DIM_DEPTH_LIMIT-2`）→ 可枚舉、有限；枚舉節點達 `SDD_DIM_DEPTH_BUDGET` → 截斷（best-so-far），絕不指數爆炸。
- **`DepthGenesisBounded`（深度 stock 天花板）**：現存活躍 depth-genesis 數逼近 `SDD_DIM_DEPTH_MAX` → `guard_depth_genesis` raise `DepthCardinalityExceeded` → `MFSM_ESCALATION`。
✅ 守 Rule 9.34.1/9.34.4：「深度 `<=2` 外」≠「無界」+ 深度 stock 天花板封死深度基數爆炸。

### 5.6 Phase V 專屬極端案例（五）：深度外冗餘算子（更深但無新交互）
**案例**：發明一個更深、但與既有某淺算子在固定 probe 上排序幾乎相同的深度算子（冗餘再投影），企圖灌水。
- feature-grounded oracle：非冗餘度（與既有 existing_cost 排序的最大一致率）≈ 0.99 ≥ 門檻 `SDD_DIM_REDUNDANCY_MAX` → 判定冗餘 → 拒絕，即使增量覆蓋略 > 0 也不擴充（過擬合防護，沿用 Phase Q~U 非冗餘獨立閘）。
✅ 守 Rule 9.34.2：增量覆蓋 ∧ 非冗餘 **兩者皆須通過**才取得 tier。

### 5.7 結論
Phase V 通過六個極端案例的內部模擬：系統能**有界地自我發明深度 `>2` 的新複合算子、且每個發明深度算子結構性維持深度可計算性閉包（擴充深度後整個深度算子代數 cost==depth<=STEP_MAX）**，且任何（深度超界算子 / 非全函式深度算子 / 自指自利深度算子 / 深度無界生成爆炸 / 深度基數爆炸 / 深度外冗餘算子）都被 (有界深度生成文法) + (DepthClosureBounded 深度可計算性閉包三證) + (depth self-reference guard 零漏放) + (feature-grounded 深度必要性 oracle 零漏放) + (DepthGenesisBounded 深度 stock) 五道防線攔下，**優雅停機並導人類掌舵深度外價值計算生成本體論，而非陷入深度不停機/無界生成/自指放水浪費 Token**。精準對應提示 Self-Verification 要求：「Evaluator 發現異常 → 優雅中斷 → 引導人類介入修正/提供缺失工具」於**最深的深度外計算生成本體論發明層（meta⁷）**，並**把停機問題正面釘進框架自我擴充文法的結構性步數參數本身（因 cost==depth 而最直接）**。

---

## 6. 執行檢核清單（供 dynamic workflow 消費）

- [ ] **TLA+ 先行**：`META_FSM.tla` 新增 `DepthGenesisBounded` + `DepthClosureBounded` INVARIANT + `.cfg` 列入 + **五軌 TLC 全 No error（META 13 distinct 不回歸）** → 回報使用者（使用者執行要求）
- [ ] ACT-150 `operator_depth_genesis.py` + 有界深度生成文法（深度可計算性閉包：total 步驟 + cost==depth + 零遞迴零迴圈）+ depth_self_reference_guard + `verify_depth_closure` + ≥4 情境 fixture + 閉包 fuzz-total + 對抗分離斷言
- [ ] ACT-151 `evaluate_genesis_depth` feature-grounded + `DPT-*.yaml` 凍結語料（12 個）+ `meta_ledger` depth-genesis stock + `guard_depth_genesis` + `guard_depth_closure` + `dim_depth_max/budget/limit` getters + ≥12 fixture（真必要/噪音/冗餘）+ 零漏放
- [ ] ACT-152 `render_depth_genesis_proposal` + 深度可計算性閉包證據 + NoUnboundedDepthGenesis + 人工 gate 斷言 + chaos 雙故障型 + `R-9.34-*.yaml` + RULES_INDEX + CLAUDE.md §9 禁令#24 + INIT 追加 + ID 翻牌（150→153 / 9.34→9.35）+ test_id_registry + test_phase_v
- [ ] 五軌 TLC No error（META 13 distinct）+ chaos 100 輪 bounded（DEPTH_GENESIS_GOODHART_FLAP + DEPTH_CLOSURE_FLAP）+ pytest 全綠不回歸（1335 → 新基線）
- [ ] 獨立 QA 稽核（Architect/SA/SD/QA 專家）抓漏 → 修復 → 全綠
- [ ] 以日期 timestamp 打標籤 push + Merge main

> **狀態流轉**：使用者 signoff →（TLA+ 五軌全綠回報）→ EXECUTING →（三 ACT + 收官全綠）→ EXECUTED →（QA 抓漏 + 修復全綠）→ VERIFIED → tag + merge main。
