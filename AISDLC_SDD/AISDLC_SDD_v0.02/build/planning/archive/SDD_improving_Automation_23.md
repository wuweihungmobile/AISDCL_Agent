# SDD_improving_Automation_23 — Phase W 藍圖（meta⁸）

**主題**：**算子間互遞迴文法的自我擴充（meta⁸）+ 良基停機證書（Well-Founded Termination Certificate）**——把 Phase T/U/V 只能自我發明「**結構性非遞迴**的算子（T）/ 字母（U）/ 組合深度（V）」（三者共同地基：被發明的算子代數**零遞迴、零迴圈、零自呼叫**，故 cost 是「運算式樹深度」這個結構性有限量，停機靠「有界步數」即可保證）的能力，推進到「系統能**自我發明一個會呼叫其他算子（甚至自呼叫）的互遞迴複合算子**（= 擴充算子生成文法的『算子是否可互相引用 / 自引用』這個結構參數本身）」。並正面納管「互遞迴生成」憑空長出、Phase T/U/V（非遞迴）不存在而 Phase W 才出現的**新危害類別：(i) 互遞迴停機性危害（RecursionClosure，本 Phase 靈魂，且是迄今**唯一一個「有界步數」device 結構性攔不住、必須換全新停機判定機制**的紅線）——Phase T 的「cost<=3」、U 的「擴充字母表後整代數 cost<=3」、V 的「cost==depth<=STEP_MAX」之所以成立，其共同地基是『算子代數零遞迴、運算式樹是有限樹，故總步數 = 樹節點數這個結構性有限量』；一旦讓系統自我發明『算子可互相呼叫 / 自呼叫』，運算式「樹」變成運算式「圖」（可含環），總步數不再是結構性有限量——`cost` 不再能用「樹深度/節點數」靜態算出，因為一個含環的呼叫圖可以是停機的（有良基遞減測度）、也可以是不停機的（無窮迴圈），而「判定一個任意互遞迴算子是否停機」**就是停機問題本身（不可判定）**；故停機性必須由『有界步數靜態量』升級為『**良基停機證書**——呼叫圖為 DAG（無環，結構良基），或每條回邊（自呼叫 / 環）皆嚴格遞減一個下有界（>=0）的良基測度（rank），且硬燃料上界（fuel）<= STEP_MAX』；這是「圖靈完備 vs 保證停機」第一次**正面逼到不可判定的臨界線本身**——meta⁸ 不讓算子代數真正跨入圖靈完備（那會使停機不可判定），而是**安裝一道把互遞迴侷限在「可證良基終止之全函式片段（total / structurally-recursive fragment，即 Agda/Coq/Idris 全函式語言的可判定停機邊界）」的證書**，凡無法出示良基測度者結構性拒絕、導人類舵手；(ii) 互遞迴無界生成爆炸（呼叫圖節點/邊無上界）；(iii) 互遞迴自我發明 Goodhart（發明一個 node/call/probe 計算自己核可訊號的自指自利互遞迴算子）**。
**目標等級**：L10 完整 · 離線活體 meta⁷ 迴圈「算子組合深度文法自我擴充（深度可計算性閉包）」切片（Phase V 已達）→ **L10 完整 · 離線活體 meta⁸ 迴圈「算子間互遞迴文法自我擴充 + 良基停機證書」切片**（系統不只能自我發明非遞迴算子/字母/深度，更能在**可證有界、可證良基終止（互遞迴呼叫圖 DAG 或每環嚴格遞減下有界測度）、反自利、人類掌舵本體論**的前提下，**自我發明一個會呼叫其他算子 / 自呼叫的互遞迴複合算子**，重構它「用**互相引用的算子呼叫圖**去生成它用來量在乎之事的算子」的計算生成本體論——而停機性由迄今最弱的「有界步數」升級為「良基測度終止」這個全新判定機制）。
**建立日期**：2026-06-05
**前置基線**：Phase V 完整（ACT-150~152 / R-9.34，pytest **1350 passed / 4 skipped / 14 subtests passed / 34 deselected[chaos]**〔本地實測 non-chaos PR gate 基線〕；五軌 TLC 全 No error：`SDD_FSM` 42 reachable / 831 TLC distinct、`META_FSM` 13 distinct、`FLEET_FSM` 7、`COMPOSITION_FSM` 21、`OPTIMIZATION_FSM` 12；chaos 100 輪 bounded_ratio=1.0 含 `DEPTH_GENESIS_GOODHART_FLAP`+`DEPTH_CLOSURE_FLAP`）
**OPEN-10.6 承接**：續承 OPEN-V.x / OPEN-U.x / …——**暫不放寬 OPEN-10.6 沙箱**（維持本地唯讀／no-HTTP）。L9 完整（活體 canary/shadow）與**活體 meta⁸ 元迴圈**續列 horizon；**Phase W 與 Phase N~V 同策略——全力推「不需放寬沙箱、純離線/形式化」即可達成的 L10 完整剩餘切片（算子間互遞迴文法自我擴充 + 良基停機證書）**。Phase V §3.4 與 R-9.34.5 明示「算子間互遞迴 / 圖靈完備算子代數（meta⁸：算子可互相呼叫 / 帶記憶，逸出 sub-Turing 保證，須全新停機判定機制）」為其自陳 horizon，故本份維持離線等價切片，活體版列 horizon（OPEN-W.x 承前）。**自我發明評估器（meta-oracle 自演化）續列最高 horizon**——它自指地破壞所有 Phase 賴以成立的「對抗分離地基」，採納它須先有更強的對抗分離不可繞過性證明（見 §0 thinking 五末、§3.4）。
**狀態**：✅ **使用者規格 Signoff（2026-06-05）→ EXECUTING**。依使用者既定執行紀律「先完成 TLA+ 形式化證明並確保五軌 TLC 全綠，再撰寫 Python 執行層」。徵用 **ACT-153~155 與 Rule 9.35**（取自 `governance/ID_REGISTRY.yaml` `next_free` = act 153 / rule 9.35，單調取號）。
**對應提示**：Karpathy 式「首席 AI 自動化架構師」前沿評估（驗證圖靈完備自動化閉環 → 進化 Level 10 自治）— 承 Phase V §3.4 / R-9.34.5 自陳 horizon「算子間互遞迴 / 圖靈完備算子代數（meta⁸：須全新停機判定機制）」續推。

> 🔴 **編號徵用告示**（承 `ID_REGISTRY.yaml` `next_free` = act 153 / rule 9.35）：
> 本藍圖徵用 **ACT-153~155 與 Rule 9.35**（取自登記簿前緣，單調取號）。
> 停滯分支 M3 Hook Health 不持有任何號，復活時另取當下 `next_free`。
> **收官（ACT-155）獲人工 signoff 並執行至全綠時**，才由 `id_registry` 翻牌（act 153→156 / rule 9.35→9.36）+ `test_id_registry.py` 守門固化；撞號由 CI 自動攔截。

> 🟦 **Level 量表釐清（提示 header 寫 Level 10、Output Requirement 4 寫 Level 5 的不一致）**：本框架自有 L0~L10 成熟度量表（見 §3.3），提示通用模板的「Level 5 自治開發流程」對應本框架早已跨越的 L5（學習層入口，Phase E 達成）。本份**不降級**回 L5，而是延續框架實況——推進 **L10 完整之離線活體 meta⁸ 迴圈切片**。提示 Output Requirement 4 的「Level 5」按框架實況讀作「L10 完整藍圖的本期切片」，並在 §3.3 明確對賬。

> 🟧 **§0.0 QA M-1 誠實修正（2026-06-05，獨立稽核後採納；本註記語意優先於全文任何「admit 含環」讀法）**：
> 獨立 QA 稽核（PASS-WITH-FIXES）正確指出——在**有限整數 per-edge rank** 上，「**含環 ∧ 每條邊嚴格遞減下有界 rank**」是**空集**（環繞回起點需 `r < r`，矛盾）。故良基停機證書「呼叫圖 DAG ∨ 每環嚴格遞減 rank」中的後者退化為前者：**ranking function（每條呼叫邊嚴格遞減下有界 rank）⟹ 良基 ⟹ 無環（DAG）⟹ 可證終止**。本 Phase **不** admit 真正含環的算子（那判定停機不可判定），fuel 為硬後盾。
> **Phase W 相對 Phase V 的真正、可辯護的新意，不是「含環」，而是「呼叫圖結構」**：Phase V 的算子是**線性深度鏈**（每步唯一 next）；Phase W 的算子是**呼叫圖**——一個算子可**引用 / 呼叫多個**其他算子（**分支 / 共享 / 重匯聚**，見 `RecursiveOperator.fan` 與 `enumerate_genesis_recursion` 的 fan 拓樸），其結果由 fold 組合，這是線性深度鏈表達不出的。**device 之新在 KIND**：Phase V 用『有界運算式樹深度』證停機；Phase W 用『**呼叫圖上的 ranking function**』證停機——後者承載分支/共享呼叫圖、仍可判定終止（Agda/Coq/Idris 結構遞迴邊界）。
> 實作對齊：`termination_certificate` 已令 `well_founded`（ranking function 存在）**真正參與** `terminating` 判定（`terminating = well_founded ∧ acyclic ∧ ranks_lb`，`acyclic` 為 Kahn's 交叉驗證）；`apply` 以 rank 升序對**整張呼叫圖**做良基 fold（折疊每節點**所有** callee 已算值，真互遞迴呼叫圖）。**全文下方凡出現「含環 ∧ 每環遞減 rank」「admit 含環」之措辭，一律按本註記讀作「呼叫圖帶良基 ranking function（⟹ DAG ⟹ 終止）+ 分支/共享呼叫圖結構（beyond 線性鏈）」**。新增 2 測試 `test_recursion_branching_call_graph_terminating` / `test_well_founded_ranking_function_gates_certificate` 客觀守門此修正。

---

## 0. 為什麼還需要 Phase W？——對既有設計的誠實剖析（含 `<thinking>` + 圖靈完備性覆查）

<thinking>
這份提示要求「驗證圖靈完備的自動化閉環、進化 Level 10 自治」，附三個必查漏洞視角（狀態轉換 / 上下文衰減 / 停機問題）與一份 self-verification 案例（Spec 寫錯→測試永不過）。延續 Phase K~V 的紀律，第一步是**對賬而非設計**：這套系統已走過 Phase A~V、是自陳「L10 完整 + 離線活體 meta⁷ 迴圈（算子組合深度文法自我擴充 + 深度可計算性閉包）」的成熟框架。盲目重述提示前沿清單只會重造輪子。我的任務是：(1) 覆查圖靈完備 vs 保證停機的核心命題在 Phase W 是否仍成立；(2) 誠實判斷「算子間互遞迴文法的自我擴充」到底是**Phase V 的換皮**（無新意、不值得一個 Phase），還是**有真正的新結構性缺口**；(3) 用三漏洞視角把那個新缺口挖到 grep 可證零實作。

【零、圖靈完備 vs 停機的命題覆查——Phase W 把監督者的涵蓋面從「自我發明深度（生成規則的結構性深度參數）」擴到「自我發明算子間互遞迴（生成規則的『算子可否互相引用 / 自引用』這個會讓停機變成不可判定的結構參數）」，且首次面對『被自我擴充物會讓停機問題真正不可判定』的臨界線本身】
Phase O~V 已正面論證：圖靈完備性來自「嵌在迴圈裡的 LLM 生成器 + 無界 `docs/` 紙帶」，保證停機來自「把不可判定的 LLM 包進可判定的有限狀態監督者（FSM + retry/context budget + 五軌 TLC）」——兩者拆在不同基質故不矛盾。Phase T 把停機釘進被發明的**算子**（產物）；Phase U 把停機釘進被發明的**字母表**（生成規則的零件）；Phase V 把停機釘進被自我擴充的**組合深度**（生成規則的結構性深度=步數參數）。

但 Phase T/U/V 的可計算性論證有一個**共同的、未被言明的最深地基**：**被發明的算子代數結構性零遞迴、零迴圈、零自呼叫**。`operator_genesis.GenesisOperator.apply` 是「primary list-reduction ∘ combinator」、`operator_depth_genesis.DepthOperator.apply` 是「有界 for 走一元鏈」——**運算式都是有限樹（DAG-free tree），總計算步數 = 樹節點數這個純結構性有限量**，故「有界步數」這個 device 就足以保證停機（cost<=3 / cost==depth）。**系統至今換得出算子、字母、深度，卻換不出『算子互相呼叫 / 自呼叫』**。Phase V 把這件事列為 horizon（§3.4 + R-9.34.5）：**算子間互遞迴 / 圖靈完備算子代數（meta⁸，算子可互相呼叫 / 帶記憶，逸出 sub-Turing 保證，須全新停機判定機制）**。這裡藏著一個**比 Phase T/U/V 都更尖銳、且質變的命題**：

**「有界步數」這個 device 在 Phase W 結構性失效。** 一旦算子可互相呼叫 / 自呼叫，運算式「樹」變成運算式「圖」（可含環）。一個含環的呼叫圖**可以是停機的**（若每次繞環都嚴格逼近一個下界 = 有良基遞減測度），**也可以是不停機的**（無窮迴圈）。而「給定一個任意互遞迴算子，判定它是否停機」**字面上就是停機問題本身——不可判定**。這把可計算性問題推到質變的形式：
- 互遞迴生成的危害不在於『cost 變大』（Phase V 的 cost==depth 還是個有限數），而在於：**cost 不再是一個可由結構（樹深度/節點數）靜態算出的量**——你**無法**用「枚舉運算式樹 + 數節點」算出一個含環呼叫圖的步數，因為那等於解停機問題。Phase V 的 `guard_depth_closure`（枚舉 `G(A,depth)` 整個**非遞迴**深度代數、靠 `cost==depth` 靜態判步數）對「**呼叫圖含環**」**結構性盲目**（它枚舉的代數每個算子都是有限樹，沒有環的概念）。
- 這正是「圖靈完備 vs 保證停機」**第一次正面逼到不可判定的臨界線本身（meta⁸）**：你敢讓系統發明『算子互相呼叫』，就**必須在採納前出示一個良基停機證書**——否則「把不可判定 LLM 包進可判定監督者」的整套地基，會因為「監督者的算子生成文法開始用『可含環的呼叫圖』去生成算子」而**從生成規則的圖結構根部**被蛀空，且這道蛀空**不可能用 Phase T/U/V 的『有界步數』device 補**（因為判定含環圖是否停機本身不可判定）。

故 Phase W 必須引入一個**全新的停機判定機制**——不是「數步數」，而是「**良基測度終止證書（Well-Founded Termination Certificate）**」：呼叫圖為 DAG（無環，結構良基，拓樸序評估必終止），**或**每條回邊（自呼叫 / 環）皆嚴格遞減一個下有界（>=0）的良基測度（rank / fuel），且硬燃料上界 fuel <= STEP_MAX。這正是全函式語言（Agda / Coq / Idris）允許遞迴卻保證全函式的判定邊界。**meta⁸ 不讓算子代數真正跨入圖靈完備（那會使停機不可判定）——它安裝一道把互遞迴侷限在「可證良基終止之全函式片段」的證書，凡無法出示良基測度者結構性拒絕、導人類舵手。** 我們稱這道新東西為 **RecursionClosure（互遞迴良基停機閉包）**。

【一、誠實判斷：算子間互遞迴文法自我擴充是「Phase V 換皮」還是「有真缺口」？——用 grep 接地】
我先確認框架目前的算子代數**結構性零遞迴**（grep `operator_genesis.py` / `operator_depth_genesis.py`：`apply` 只有「list comprehension + 有界 for 走鏈」，無 `while`、無自呼叫、無算子間互引用；Phase T/U/V 的測試甚至 ast 斷言「求值路徑零 while 零遞迴」當作可計算性的**前提**）。再 grep 三組關鍵字證明零實作：
| 關鍵字 | grep 範圍 | 命中 |
|--------|-----------|------|
| `recursion.*genesis\|RecursionGenesis\|RecursiveOperator\|inter.*recursion\|call_graph` | `tools/` | **零** |
| `recursion.*closure\|RecursionClosure\|termination_certificate\|well_founded\|guard_recursion_closure` | `tools/` | **零** |
| `SDD_DIM_RECUR_BUDGET\|SDD_DIM_RECUR_MAX\|render_recursion_genesis\|NoUnboundedRecursionGenesis` | `tools/` | **零** |

→ **算子間互遞迴文法的「自我擴充」目前零實作；系統被鎖在「非遞迴算子代數」內（這正是它至今能用『有界步數』保證停機的原因）。** 真正的價值不在於「再加一個 recursion grammar」（那是 Phase V 換皮），而在於：**互遞迴生成會打開三個 Phase T/U/V 結構性攔不住的新攻擊面，其一是質變的停機危害——互遞迴是停機問題從『可判定』翻轉成『不可判定』的那條線本身，「有界步數」device 在此結構性失效，必須換『良基測度終止證書』這個全新判定機制**：
- **互遞迴良基停機危害（meta⁸ 的靈魂，迄今唯一一個讓「有界步數」失效的質變缺口）**：自我發明的互遞迴會讓文法生成**含環呼叫圖**；判定任意含環圖是否停機 = 停機問題（不可判定）。Phase V 的 `guard_depth_closure`（枚舉非遞迴深度代數、靠 cost==depth 靜態判步數）對「呼叫圖含環」**完全盲目**。← 這是 Phase W 的 **PW-2 的核心**（真缺口，且是停機問題從可判定翻不可判定的臨界線本身，須全新 device）。
- **互遞迴無界生成爆炸 + 互遞迴自我發明 Goodhart**：互遞迴生成**沒有「樹」的有限結構上界**（圖的節點/邊可無界）；且系統可發明一個「**互遞迴算子的 node/call/probe 本身就計算 proposer/oracle/自評內部信號**」的自指互遞迴算子。Phase V 的 feature-grounded oracle 評的是**非遞迴深度算子在固定參照算出的特徵向量**——它對「一個**互遞迴、用一張事先沒見過的算子呼叫圖去聚合**的算子到底必不必要、是不是自指自利」**完全盲目**。← **PW-1 的另兩面**。
- **互遞迴生成的計算生成本體論掌舵真空**：`steersman` 只渲染「非遞迴上自我發明的算子/字母/深度」與「（非遞迴）可計算性閉包證據」；無人渲染「系統**現場發明了一個會呼叫其他算子 / 自呼叫的互遞迴算子、它的呼叫圖生成文法來源（憑什麼有界）、它憑什麼可證良基終止（呼叫圖 DAG 或每環嚴格遞減下有界測度的證書）、它憑什麼必要且非自指**」。人類掌舵在「互遞迴計算生成本體論發明層（meta⁸）」缺席。← **PW-3**。

【二、用提示三個指定漏洞視角，逐一往 Phase V 之上挖】

(A) 狀態轉換——「生成器↔評估器合約談判」在 meta⁸ 層缺「互遞迴發明的可有界、**良基停機證書（呼叫圖 DAG 或每環嚴格遞減下有界測度）**、可反自利、feature-grounded 驗證」這一層。
Phase V 的 `operator_depth_genesis`（生成，非遞迴深度算子）↔ `dimension_necessity_oracle.evaluate_genesis_depth`（評估，feature-grounded）是一對 meta⁷ GAN，但**它只評非遞迴算子**。當系統**現場發明一個會呼叫其他算子 / 自呼叫的互遞迴算子**，**(1) 誰保證這條呼叫圖生成不會無界爆炸？(2) 誰保證互遞迴算子一定會停（良基停機證書——這是判定不可判定問題的唯一合法 device：要求生成端出示證書，而非由監督者去判定任意圖）？(3) 誰判「這個現場發明的互遞迴算子到底必不必要、是不是自指自利」？** 目前無人。提示要的「生成-評估分離 + 主觀標準量化」推到 meta⁸ 層，型態是：**(1)** 生成必須被一條**有界互遞迴生成文法**封住——「非遞迴外」不等於「無界」，而是「在一個**有限節點集（每節點 = 一個 Phase T 深度-2 base 算子）× 有限呼叫邊集（每邊帶一個結構性 rank）**的可枚舉生成空間裡生成互遞迴算子」，節點 <= `SDD_DIM_RECUR_BUDGET`；**(2)**（最關鍵、質變）互遞迴生成文法必須**結構性附帶良基停機證書**——每個互遞迴算子 = 一張呼叫圖 + 每節點一個 rank，**生成文法只生成「DAG 或每條回邊嚴格遞減 rank（下有界 >=0）」的呼叫圖**，且 fuel <= STEP_MAX——**這是「停機性需用全新 device」的正面兌現：把互遞迴刻意設計成一個『可證良基終止之全函式片段』，讓被發明的互遞迴算子代數可證停機（用良基測度而非有界步數），而整個閉環仍靠 LLM+紙帶維持圖靈完備**；**(3)** 評估升級為**對互遞迴算子（不靠算子名、靠在固定參照 probe 上的真實計算結果）的 feature-grounded 互遞迴必要性 oracle**——量「以這個互遞迴算子聚合，是否帶來既有所有非遞迴算子都拿不到的增量覆蓋（遞迴交互）∧ 非冗餘」；外加一道**互遞迴級自指守門**（反自利）。→ **PW-1**（最關鍵；純離線、不受 OPEN-10.6 約束）。

(B) 停機問題——「互遞迴良基停機證書（RecursionClosure）」是一條 Phase T/U/V 不存在、直接源自「被自我擴充物是『讓停機從可判定翻不可判定的圖結構參數』」的迄今唯一質變停機缺口。
這是 Phase W 最深、也最切題（提示明列「停機問題與防護」）的缺口。Phase T/U/V 的被發明物可用「有界步數」判停機（因為都是非遞迴有限樹）。Phase W 的被自我擴充物是「算子可否互相呼叫 / 自呼叫」=「**直接決定停機是否可判定**的結構參數」。新病態：**「有界步數」device 失效**——你不能枚舉一個含環呼叫圖去數步數（那等於解停機問題）。新閉包危害：**(i) 無證書環**（呼叫圖含環、但回邊不遞減任何下有界測度 → 可能無窮迴圈 → 不停機）；**(ii) 互遞迴算子非全函式**（某輸入無定義 / 拋例外）；**(iii) 燃料超界**（fuel > STEP_MAX）。這是 Phase T/U/V（全非遞迴）時不可能、互遞迴自我發明才出現的質變停機危害。→ 需要一條**互遞迴良基停機證書有界停機不變量** `RecursionClosureBounded`：(a) **良基測度終止結構性可判定**——互遞迴算子 = 呼叫圖 + 每節點 rank；生成文法**只生成 DAG 或每回邊嚴格遞減下有界 rank 的圖**，故有良基測度 → 必終止（Agda/Coq 全函式片段）；(b) **證書驗證**——採納前 `guard_recursion_closure` **枚舉互遞迴算子的呼叫圖，斷言 (acyclic) ∨ (每環有嚴格遞減下有界測度)，且 fuel<=STEP_MAX，且整代數 fuzz-total（零例外、無 NaN/inf）**，觸發即 `RecursionClosureViolation` → `MFSM_ESCALATION`；(c) **求值器零真遞迴零 while 結構保證**——互遞迴算子的**求值器**以**有界 fuel 的迭代工作集（bounded worklist + for-range-fuel）**走呼叫圖，**不**用語言層遞迴 / `while`（grep/ast 斷言 `operator_recursion_genesis.py` 求值路徑無 `while`/無自呼叫函式；fuel 為硬上界保證即使證書被繞過也不會真無窮跑）。**這正補上 Phase V 的非遞迴 `guard_depth_closure` 對「呼叫圖含環」全盲的質變缺口，且用全新 device（良基測度）而非有界步數。** ← **PW-2**。

(C) 動態演進 / 人類掌舵——「人類審的是『非遞迴上的算子/字母/深度發明 + 非遞迴可計算性閉包』，缺『互遞迴發明 diff（meta⁸）+ 良基停機證書證據』」。
Phase V 的 `render_depth_genesis_proposal` 渲染**非遞迴**上發明的深度算子 + 深度閉包證據。互遞迴自我擴充後，若系統現場發明一個會自呼叫的互遞迴算子，人類面對的是「一張從未見過的算子呼叫圖 + 它是否會停取決於良基測度」——**沒有人渲染『這個互遞迴算子是系統怎麼從有界互遞迴生成文法生成出來的、它的呼叫圖有界嗎、它出示了什麼良基停機證書（DAG 或每環嚴格遞減下有界測度 + fuel<=STEP_MAX）、它自指嗎、它憑什麼必要』**。提示反覆強調「人類維持設計環境掌舵者高度，而非降級為編碼員」——在「互遞迴計算生成本體論發明（meta⁸）」層，掌舵的最高形態是**人類能一眼看懂『系統憑空發明了哪個互遞迴算子、它的有界呼叫圖生成來源 + 良基停機證書（呼叫圖良基 + fuel<=STEP_MAX）+ 反自利證據 + 必要性勝率』，且系統在結構上不可能自動 commit 任何互遞迴自我發明（每週期至多 K_recur=1 個互遞迴發明、每個必經人工 signoff）**。→ **PW-3**（互遞迴計算生成本體論發明掌舵介面 + `NoUnboundedRecursionGenesis`，K_recur=1，承 Phase V K_depth=1）。

【三、停機問題紅線覆查——本份比 Phase V 更危險，因為納管的是「會憑空發明『算子互相呼叫』（= 直接觸碰停機可判定性臨界線）的迴圈」】
Phase V 的反諷（讓系統自我發明它的組合深度）在 Phase W 升級為「讓系統**憑空發明『算子互相呼叫 / 自呼叫』（自己寫會讓停機不可判定的圖結構）**」。有界性與防自利必須再加固，且**首度必須用『良基測度終止證書』取代失效的『有界步數』，證明被自我擴充的『互遞迴圖結構』仍維持可判定停機**：
- **仍不新增形式化軌（承 Phase O~V「重用 META_FSM、不增軌」的成熟示範）**：互遞迴自我發明的採納/退役全部註冊為 `META_FSM` 既有的指紋命名空間（新增 `recursion-genesis:` 命名空間），其 add↔retire churn 由**同一條** `ChurnBounded`/`GraduationRatchet` 涵蓋。**但 PW-1/PW-2 揭示：churn 仍不夠**，故必須**對既有 `META_FSM` 再補兩條不變量**：`RecursionGenesisBounded`（互遞迴發明基數 stock 天花板）+ `RecursionClosureBounded`（互遞迴良基停機證書：呼叫圖良基 + fuel<=STEP_MAX）——關鍵是**沿用 Phase P~V 的誠實作法：只新增 INVARIANT、不新增狀態變數**（`META_FSM` 維持 `<<mstate, churn, cap>>` 三變數 / 13 distinct，TLC 仍 No error，五軌不回歸；互遞迴 stock 與良基停機證書的緊語意由 runtime `guard_recursion_genesis`/`guard_recursion_closure` + chaos `RECURSION_GENESIS_GOODHART_FLAP`/`RECURSION_CLOSURE_FLAP` enforce/驗收，形式化層誠實標註為「single-counter 抽象之歸約引用」）。這守住「圖靈完備能力 / 可證停機控制」的拆分紅線，又不退化成「每個新能力都開一軌」。
- **PW-1 的有界互遞迴生成文法是硬約束，非建議**：互遞迴自我發明的搜尋**必在有限互遞迴生成文法（有限節點集 × 有限帶 rank 呼叫邊集）內可枚舉**，節點 <= `SDD_DIM_RECUR_BUDGET`（clamp[8,128]，預設 32）。**PW-1 的反自利是雙閘**：(a) necessity tier **唯一合法來源仍是 generator 全體碰不到、content-hashed 凍結的 feature-grounded 互遞迴必要性 held-out 勝率**；(b) **互遞迴級自指守門**——任何 node/call/probe 引用保留自指信號的互遞迴算子，在送 oracle 前即被 `recursion_self_reference_guard` 攔下（零漏放）。`operator_recursion_genesis` **結構性不 import oracle、不讀必要性語料**（ast/import 隔離斷言）。
- **PW-2 的良基停機證書是「良基測度結構性終止 + 證書枚舉驗證 + 求值器零真遞迴零 while + fuel 硬上界」四證**：互遞迴算子由帶 rank 的呼叫圖組成，生成文法只生成「DAG ∨ 每回邊嚴格遞減下有界 rank」的圖（有良基測度）；採納前 `guard_recursion_closure` **枚舉呼叫圖驗 (acyclic ∨ well-founded) ∧ fuel<=STEP_MAX ∧ 整代數 fuzz-total**。觸發 `RecursionClosureViolation` → `MFSM_ESCALATION`。**這是把停機問題正面釘在『可判定 vs 不可判定』臨界線上的形式化兌現（從 Phase V 的『有界步數可證停機』升級為 meta⁸ 的『良基測度可證終止——admit 遞迴但侷限在全函式片段』）。**
- **PROPOSED-only + 反 big-bang 互遞迴發明，人類掌舵推到「互遞迴計算生成本體論發明（meta⁸）」層**：每週期至多 **K_recur=1** 個互遞迴自我發明可進 proposed-pending-signoff（`NoUnboundedRecursionGenesis`，承 Phase V K_depth=1），每個必經人工 signoff（守 Rule 8 / 9.27~9.34）。`steersman_renderer` 渲染「互遞迴計算生成本體論發明 diff + 良基停機證書」。
- **自我發明評估器（meta-oracle 自演化）續列最高 horizon、本份明確不做**：Phase W 把生成端（互遞迴）拉進基質 B，但**評估端（必要性 oracle）仍由人類凍結**。「讓系統自我演化它的評估器本身」會讓 generator 與 evaluator 收斂到同一基質——這**自指地破壞 Phase O~W 全部反 Goodhart 保證所賴以成立的『對抗分離』地基**。採納它須先有更強的「對抗分離不可繞過性」形式化證明，超出本份範圍，明確列為 §3.4 最高 horizon。

【四、上下文衰減（Context Degradation）視角覆查】
- 互遞迴生成文法枚舉、feature-grounded 互遞迴必要性 held-out 重放、良基停機證書枚舉驗證全在**隔離邏輯/落盤**進行，主線只在收到 proposed 互遞迴發明時讀「互遞迴發明 diff + 良基停機證書證據 + 必要性勝率摘要」。互遞迴帳本**沿用** Phase R/S/T/U/V 的 `value-dimension-ledger.yaml`（增 `recursion_inventions` 領域審計段）+ 共用 Phase L 的 `meta-loop-ledger.yaml`（churn/recursion-cardinality 治理），**零新增常駐 eager prompt、不污染單軌 `SDD_FSM`**。
- feature-grounded 互遞迴必要性 oracle 重用既有 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`（clamp[5,200]，預設 50）上限，**不新增無界語料**。
- 所有新產物皆 Markdown/YAML 純文字、無二進位、無外網（守 OPEN-10.6 + 智慧體可讀性）。
→ 守漸進式揭露，不引入新脈絡焦慮。

【五、把 OpenAI/Anthropic 哲學收斂成一句設計準則】
- OpenAI（環境防護 / 智慧體可讀性 / 單一真實來源）：把「系統如何從有界互遞迴生成文法**憑空發明一個會呼叫其他算子 / 自呼叫的互遞迴算子**」「它的呼叫圖生成來源、**良基停機證書證據（呼叫圖 DAG 或每環嚴格遞減下有界測度 + fuel<=STEP_MAX）**、反自指證據、凍結必要性證據」全部落地為 **Markdown/YAML 可推理產物**——讓「系統如何發明它『用互相呼叫的算子去生成它的算子』、以及它如何證明那套互遞迴一定會停（良基測度而非有界步數）」成為 AI 與人類都可直接推理、可審計的單一真實來源，而非藏在「非遞迴」的天花板裡。
- Anthropic（生成-評估分離 / 評估器實體操作 / 動態演進 / 大膽移除冗餘鷹架）：把「生成-評估分離、避免對自身產出盲目自信」從「深度外深度自我發明」（V）推到**「互遞迴外互遞迴自我發明」**（meta⁸）——生成端用**有界互遞迴生成文法**把無界圖空間歸約為有限可枚舉、且**結構性附帶良基停機證書（呼叫圖良基 + fuel<=STEP_MAX）**，評估端用 **feature-grounded 互遞迴必要性 oracle + 互遞迴自指守門**專攻「互遞迴自我發明 Goodhart / 自指自利互遞迴算子」；並再次以「不增第六軌、只補 META_FSM 兩條不變量」示範「大膽移除冗餘鷹架」。你敢讓系統憑空發明『算子互相呼叫』（= 自己寫會讓停機不可判定的圖結構），就得能用全新 device（良基測度終止證書）證明這條互遞迴發明迴圈仍會停，而非沿用已失效的『有界步數』。
</thinking>

本次提示所列前沿清單，**已 100% 對應到 Phase H~V 落地元件**（對賬見上 thinking 一節），七條已知迴圈（單軌 `SDD_FSM` / 艦隊 `FLEET_FSM` / 元迴圈 `META_FSM`〔含 O~V 的 obj-profile / 全評分器 calibration / value-dimension / self-invention/swap / vocab-genesis/batch-swap / operator-genesis / alphabet-genesis / depth-genesis〕/ 組合 `COMPOSITION_FSM` / 最優 `OPTIMIZATION_FSM`）皆已形式化停機，且**「圖靈完備自動化閉環」已正面驗證成立**。Phase W 的價值在用提示三漏洞視角挖出 Phase V 之上仍真實存在、grep 證零實作的 **3 個結構性缺口**——它們的共同主軸是：**Phase T/U/V 全程在「非遞迴算子代數」上自我發明算子（T）/ 字母（U）/ 深度（V），三者皆靠『有界步數』保證停機；讓系統自我發明『算子互相呼叫 / 自呼叫』，會憑空長出 Phase T/U/V（非遞迴）時不存在的『互遞迴生成』新危害——尤其是迄今唯一一個讓「有界步數」device 結構性失效、必須換『良基測度終止證書』全新判定機制的『互遞迴良基停機危害』（被自我擴充物第一次是『讓停機從可判定翻不可判定的圖結構參數』），以及互遞迴無界生成爆炸、互遞迴自我發明 Goodhart。**

| # | 缺口（用提示三漏洞視角挖出） | grep 證據（`tools/`） |
|---|------------------------------|--------------------------|
| **PW-1** | **系統被鎖在非遞迴算子代數內，無「互遞迴外互遞迴自我發明」路徑；且 feature-grounded 互遞迴必要性驗證缺席**——系統無法發明一個會呼叫其他算子 / 自呼叫的互遞迴算子，即使硬發明也無 (i) 有界互遞迴生成文法、(ii) feature-grounded 互遞迴必要性 oracle、(iii) 互遞迴級反自利守門。提示「生成-評估分離 + 主觀標準量化」在 **meta⁸（互遞迴外發明）** 層缺席。 | `recursion.*genesis\|RecursiveOperator\|call_graph\|inter.*recursion` **零命中** |
| **PW-2** | **缺『互遞迴良基停機證書』有界停機——迄今唯一質變的停機缺口**——Phase T/U/V 的停機建立在「算子代數零遞迴、運算式是有限樹、cost 是結構性有限量」前提；Phase W 自我擴充『算子可互相呼叫 / 自呼叫』，運算式樹變含環圖，**判定任意含環圖是否停機 = 停機問題（不可判定）**，「有界步數」device 結構性失效。固定深度 `guard_depth_closure` 對「呼叫圖含環」全盲。這是「圖靈完備 vs 保證停機」第一次正面逼到不可判定臨界線，須全新 device（良基測度終止證書）。 | `recursion.*closure\|termination_certificate\|well_founded\|guard_recursion_closure` **零命中** |
| **PW-3** | **缺『互遞迴外發明 diff（meta⁸）+ 良基停機證書證據』掌舵介面**——`steersman` 只渲染非遞迴上的算子/字母/深度發明與非遞迴閉包；無人渲染「系統憑空發明哪個互遞迴算子 + 呼叫圖生成文法來源 + 良基停機證書（呼叫圖 DAG 或每環嚴格遞減下有界測度 + fuel<=STEP_MAX）+ 反自指證據」。人類掌舵在「互遞迴計算生成本體論發明層（meta⁸）」缺席。 | `render.*recursion\|NoUnboundedRecursionGenesis\|SDD_DIM_RECUR_BUDGET` **零命中** |

**三缺口的共同主軸**：Phase V 讓人類站上「審系統在非遞迴上自我發明深度 + 深度可計算性閉包」的高度，但**框架的算子生成其實只能用『零遞迴』的有限樹**。Phase W 把人類抬到最高層——審「系統如何從**有界互遞迴生成文法**憑空發明一個**會呼叫其他算子 / 自呼叫的互遞迴算子**（憑什麼有界、**憑什麼可證良基終止（互遞迴良基停機證書——呼叫圖良基 + fuel<=STEP_MAX，用全新 device 而非已失效的有界步數）**、憑什麼非自指自利）」——這正是 L10 完整「離線活體元迴圈」的**算子間互遞迴文法自我擴充（meta⁸）**切片，精準補上提示在「狀態轉換（互遞迴外生成-評估聯合合約）」「**停機問題（互遞迴良基停機證書——把停機問題正面釘在可判定 vs 不可判定臨界線上，須全新判定機制）**」「動態演進（互遞迴外發明計算生成本體論而非只在非遞迴組合）」三視角的最深層要求。

---

## 1. Agentic 閉環狀態機設計（Phase W 增量）

Phase W 對狀態機的改動延續 Phase O~V 的克制：單軌 `SDD_FSM` **不新增任何狀態**（維持 42/42 reachable / 831 TLC distinct）；**仍不新增第六條形式化軌**——互遞迴自我發明本質上**是 `META_FSM` 已證明的那條「學↔退」元迴圈**，只是被學/退的製品從「深度算子」泛化為「**互遞迴算子（呼叫圖）**」（meta⁸）。**重用既有 `META_FSM`** 並**僅補兩條不變量** `RecursionGenesisBounded` + `RecursionClosureBounded`（不增狀態變數），是 Anthropic「大膽移除不需要的鷹架」用在框架自身、且把 PW-1/PW-2 釘進形式化的正解。

### 1.1 新增元件總覽（無新 FSM 狀態、無新形式化軌、無新狀態變數）

| 元件 / 形式化層 | 命名空間 | 類型 | 阻塞? |
|------|------|------|-------|
| `operator_recursion_genesis`（互遞迴算子自我發明骨架；有界互遞迴生成文法〔良基停機證書〕+ 互遞迴自指守門） | runtime（落 `value-dimension-ledger.yaml` `recursion_inventions` 段） | 生成器骨架（advisory） | 否 |
| `dimension_necessity_oracle`（**新增 feature-grounded `evaluate_genesis_recursion`**） | runtime（重用 `counterfactual_replay` 重放基座，凍結互遞迴必要性現實情節 `RCR-*.yaml`） | 評估器（硬閘） | 否（但決定 adopt 准駁） |
| recursion-genesis 採納（stock 天花板 + 良基停機證書） | **新增 `recursion-genesis:` 指紋命名空間**（meta-loop-ledger）+ **新增** `RecursionGenesisBounded` + `RecursionClosureBounded` 不變量 | 元迴圈（沿用 `MFSM_*`，無新狀態/無新變數） | — |
| `steersman_renderer.render_recursion_genesis_proposal`（互遞迴發明 diff + 良基停機證書證據 + 反 big-bang） | runtime（advisory） | 渲染（advisory） | 否 |

> **選位說明**：
> - `operator_recursion_genesis` 把 Phase V 的深度發明**升維為互遞迴生成（meta⁸）**：它在一個 **bounded 互遞迴生成文法**（有限節點集〔每節點 = operator_genesis 深度-2 base〕× 有限帶 rank 呼叫邊集）上**可枚舉地**生成 `RecursiveOperator`（會呼叫其他算子 / 自呼叫的互遞迴算子，節點 <= `SDD_DIM_RECUR_BUDGET`），**結構性附帶良基停機證書**（PW-2），再透過呼叫端**注入的 `evaluate` 回呼**取每個發明互遞迴算子的必要性。它因此**結構性無法用自己的尺規證明自己必要**，且**結構性拒絕互遞迴自指**（反自利第一閘）。
> - `dimension_necessity_oracle` 的 Phase W 升級：新增 `evaluate_genesis_recursion` ——**不靠算子名匹配**，在**固定參照 probe 的凍結互遞迴必要性語料 `RCR-*.yaml`**上，以「該互遞迴算子」聚合量「既有所有非遞迴算子都拿不到的增量覆蓋（遞迴交互）∧ 非冗餘」。
> - 互遞迴採納的 add↔retire 元迴圈**完全納入既有 `META_FSM`**；PW-2 的互遞迴良基停機由**新增的** `RecursionClosureBounded` 涵蓋（只補 INVARIANT、不動狀態宇宙、不動狀態變數），五軌 TLC 不回歸、不增第六軌、`META_FSM` 維持 13 distinct。

### 1.2 meta⁸ 互遞迴自我發明迴圈 + 良基停機證書定理（RecursionClosure，本 Phase 數學靈魂）

#### 1.2.1 良基停機證書定理（admit 遞迴但侷限全函式片段，本 Phase 核心；「有界步數」→「良基測度」的 device 質變）

設算子節點集 `N`（每節點 `n_i` = 一個 Phase T 深度-2 base 算子 + 一個 rank `r_i ∈ 0..R_max`）。定義 **互遞迴算子** `RecOp = (N, E, entry, fuel)`，其中 `E ⊆ N × N` 是呼叫邊集（`(n_i → n_j)` 表「算子 i 求值後把累積值交給算子 j 續算」，**可含 `i==j`（自呼叫）或環**）。定義**良基測度** `μ(n_i) = r_i`（lexicographic with 剩餘 fuel）。定義**互遞迴良基停機不變量** `T(RecOp)`：

> **`RecOp` 可證良基終止 ⟺ 呼叫圖 `(N,E)` 為 DAG（無環），或每條回邊 `(n_i → n_j)`（造成環者）皆嚴格遞減良基測度（`r_j < r_i`，且 `r` 下有界於 0）；且硬燃料 `fuel <= STEP_MAX`。**

Phase T/U/V 對「非遞迴」（`E` 恆為樹邊、無環）證得「有界步數」。Phase W 自我擴充「`E` 可含環」。**良基停機證書定理**陳述：

> **若互遞迴算子 `RecOp` 的呼叫圖滿足「DAG ∨ 每回邊嚴格遞減下有界 rank」，則沿任何執行路徑，良基測度 `(rank, fuel)` 在 lexicographic 序下嚴格遞減且下有界（>=0），由良基歸納（well-founded induction）`RecOp.apply` 必在有限步內終止；其步數 <= 初始測度 <= fuel <= STEP_MAX。反之，若呼叫圖含一條不遞減任何下有界測度的環，則 `RecOp` 可能不終止——而「判定一個任意含環圖是否終止」即停機問題（不可判定），故監督者不去判定它，而是要求生成端只生成『出示良基測度』的圖，無證書者一律拒絕。**

**證明（良基歸納）**：
- **DAG 情形**：呼叫圖無環 → 存在拓樸序 → 沿拓樸序評估，每節點至多被訪問一次 → 步數 <= |N| <= fuel <= STEP_MAX，必終止。∎
- **ranking function ⟹ 良基無環（DAG）（§0.0 修正後的主證書）**：本實作的良基測度為 **per-node rank** 上的 ranking function——存在 `R:nodes→ℕ` 使每條呼叫邊 `R(callee) < R(caller)`。**在有限整數 rank 上，這等價於呼叫圖無環（DAG）**：若有環，沿環的邊 rank 嚴格遞減繞回起點需 `r < r`，矛盾；故「含環 ∧ ranking function」為空集。ranking function 即「DAG 的拓樸序」的明證，rank 是嚴格遞減的良基測度 → 由良基歸納，沿任何邊走訪至多 |N| 步必抵 sink（rank 最低）→ 必終止；步數 = 節點數 <= fuel <= STEP_MAX。**故本 Phase 之證書不 admit 真正含環的算子**（那判定停機不可判定）；fuel 為硬後盾。**真正的新意是呼叫圖結構（一個算子呼叫多個其他算子：分支/共享/重匯聚，beyond Phase V 線性深度鏈），由 ranking function 證書保持可判定終止**，而非「含環」。∎
- **全函式**：每節點 op 由 Phase T 證 total（list-reduction ∘ combinator，`_finite` 飽和投影）；total 節點沿良基終止路徑的有限合成仍 total。∴ `RecOp` 全函式。∎
- **fuel 硬上界（不可判定性的最後防線）**：即使證書因實作瑕疵被繞過，求值器仍以 `for _ in range(fuel)` 走呼叫圖，`fuel <= STEP_MAX` 為硬截斷 → **結構上不可能真無窮跑**（最差是 fuel 耗盡回飽和值），杜絕「監督者自己掛在不停機算子上」。∎

**與 Phase V 的關鍵差異（device 質變）**：Phase V 在**非遞迴**前提下用「有界步數（cost==depth）」證停機；Phase W 必須證明**含環呼叫圖**仍終止——而「有界步數」device 結構性失效（不能枚舉含環圖數步數，那等於解停機問題）。故 Phase W 換上**良基測度終止證書**這個全新 device：`guard_recursion_closure` 把此證書**可機器驗證化**（採納新互遞迴算子前，枚舉呼叫圖驗 acyclic ∨ well-founded-rank-decrease，並驗 fuel<=STEP_MAX + 整代數 fuzz-total）；若呼叫圖含無證書環，該互遞迴算子被拒 → `RecursionClosureViolation` → `MFSM_ESCALATION`。

這是「把停機問題釘在『可判定 vs 不可判定』臨界線上（meta⁸）」——Phase V 把停機釘進被自我擴充的組合深度（結構性步數參數，仍可判定）；Phase W 把停機釘在**被自我擴充的『算子互遞迴圖結構』（直接決定停機是否可判定）**，且用**良基測度終止證書**這個全新 device 把互遞迴侷限在「可證良基終止之全函式片段」——admit 遞迴，但不跨入真正圖靈完備（不可判定）。

#### 1.2.2 迴圈控制流（重用 META_FSM 有界停機契約 + 有界互遞迴生成文法 + 良基停機證書四證 + 反自利雙閘）

```
（離線、跨 session）operator_recursion_genesis.recursion_genesis_round()
  在 bounded 互遞迴生成文法（有限節點集 × 有限帶 rank 呼叫邊集，可枚舉節點 <= SDD_DIM_RECUR_BUDGET）生成候選互遞迴算子 r
    [良基停機證書結構保證] 每個 r 的呼叫圖 = DAG ∨ 每回邊嚴格遞減下有界 rank → 有良基測度（零真遞迴零 while，fuel<=STEP_MAX，PW-2）
    recursion self-reference guard：node/call/probe 引用保留自指信號 → 結構性丟棄（反自利第一閘，不送 oracle）
    對每個倖存 r：必要性 = 注入的 evaluate(r)（= feature-grounded oracle 增量覆蓋；genesis 看不到語料）
  取至多 K_recur=1 個必要性最高的候選（NoUnboundedRecursionGenesis）→ 互遞迴自我發明 r*
  → dimension_necessity_oracle.evaluate_genesis_recursion(r*)：在「genesis 全體不可見、content-hashed 凍結」的固定 probe 互遞迴必要性情節上，
       以「該互遞迴算子」聚合量 (a) 增量覆蓋（既有所有非遞迴算子拿不到的遞迴交互）+ (b) 非冗餘度
     ├─ 增量覆蓋 ≥ margin ∧ 非冗餘度 < 門檻 → 取得「必要性 tier++」
     │     → 產 proposed 互遞迴發明 + 良基停機證書證據 + 必要性證據 → steersman 渲染互遞迴發明 diff → 人工 signoff
     │     └─ 人工接受 → guard_recursion_closure（枚舉呼叫圖 acyclic ∨ well-founded + fuel<=step_max + 整代數 total）→ guard_recursion_genesis（互遞迴 stock 未滿）→ record_rule_add("recursion-genesis:hash(r*)")
     └─ 未達必要性（含「自指自利互遞迴算子」「互遞迴外噪音算子」）→ 拒絕提案 → 純記錄

（採納守門，任一觸頂 → MFSM_ESCALATION 人工裁決）
  guard_recursion_closure(r)（PW-2）：呼叫圖含無證書環（環中無回邊遞減下有界 rank）∨ fuel>STEP_MAX ∨ 整代數 fuzz 非全函式 → RecursionClosureViolation
  guard_recursion_genesis(fp)（PW-1）：現存活躍 recursion-genesis 算子數 >= SDD_DIM_RECUR_MAX → RecursionCardinalityExceeded
```

- **核心有界性（重用既有證明 + 兩條新不變量 + 全新 device）**：
  - 互遞迴生成（PW-1）：互遞迴自我發明在**有限互遞迴生成文法**內可枚舉，節點 <= `SDD_DIM_RECUR_BUDGET`（clamp[8,128]，預設 32），且**呼叫圖節點數 <= `SDD_DIM_RECUR_NODES`**（clamp[2,8]，預設 4）、**fuel <= `SDD_DIM_OP_STEP_MAX`**（沿用 Phase T/V step_max，預設 8），**絕不無界爆炸**。
  - **良基停機證書（PW-2 新增 `RecursionClosureBounded`，全新 device）**：採納前 `guard_recursion_closure` 枚舉呼叫圖驗 (acyclic ∨ 每回邊嚴格遞減下有界 rank) ∧ fuel<=STEP_MAX ∧ 整代數 fuzz-total，觸發 `RecursionClosureViolation` → `MFSM_ESCALATION`。
  - 互遞迴 stock（PW-1 新增 `RecursionGenesisBounded`）：現存活躍 `recursion-genesis:` 算子數 <= `SDD_DIM_RECUR_MAX`（clamp[1,64]，預設 16）；觸頂 `guard_recursion_genesis` raise `RecursionCardinalityExceeded` → `MFSM_ESCALATION`。
  - per-fingerprint：churn <= `SDD_META_CHURN_MAX`（既有 `META_FSM.ChurnBounded`）；再採納須挾必要性 tier 嚴增（既有 `GraduationRatchet`）。
- **反自利雙閘（PW-1）**：(a) `necessity_tier` 唯一合法來源是凍結 feature-grounded 互遞迴必要性 held-out oracle（增量覆蓋 ∧ 非冗餘）勝率——genesis 自評**結構性禁止**充當（ast/import 隔離斷言、genesis 無讀寫權、不 import oracle）；(b) **互遞迴自指守門結構性拒絕**——任何 node/call/probe 引用保留自指信號的互遞迴算子在送 oracle 前即被 `recursion_self_reference_guard` 攔下（零漏放）。把「生成-評估分離 + 反自利」釘死在 **meta⁸** 層級。

### 1.3 典型軌跡（含 Phase W 改善後的 self-verification 案例）

```
（跨 session 收官）recursion_genesis_round：近 5 session 落盤顯示「既有所有非遞迴算子都不量某類『需要對序列反覆套用同一聚合直到收斂（不動點式遞迴交互）』的特徵」
  → operator_recursion_genesis 在互遞迴生成文法（節點 = {sum, diff(max,min)} × 帶 rank 呼叫邊）枚舉候選互遞迴算子；recursion self-ref guard 丟棄引用 self_score 的誘餌；每個候選結構性 DAG ∨ 每回邊遞減 rank
  → 注入 evaluate（feature-grounded 互遞迴必要性 oracle）給 r*（rank-遞減自呼叫聚合）高分；K_recur=1 取此一者
  → evaluate_genesis_recursion：在 50 筆固定 probe 凍結互遞迴必要性情節 → augmented 0.84 vs baseline（所有非遞迴算子）0.61（增量覆蓋 Δ=0.23 ≥ margin 0.10）；非冗餘度 0.40 < 門檻
  → 取得必要性 tier++ → guard_recursion_closure：枚舉呼叫圖 → acyclic? 否；每回邊遞減下有界 rank? 是 ∧ fuel=4<=8 ∧ 整代數 fuzz-total ✅ → proposed 互遞迴發明 → steersman 渲染「互遞迴計算生成本體論發明（meta⁸）：系統憑空發明互遞迴算子『rec::…(自呼叫,rank↓)』+ 互遞迴生成文法來源 + 良基停機證書✅（呼叫圖每回邊嚴格遞減下有界 rank + fuel<=8，可證良基終止而非靠有界步數）+ 23% 增量覆蓋」
  → 人工 signoff → 互遞迴 stock 未滿 → record_rule_add("recursion-genesis:hash(r*)")

（良基停機攻擊案例：無證書環互遞迴算子）operator_recursion_genesis（受擾）被要求構造一個呼叫圖含「A→B→A 但無回邊遞減 rank」的互遞迴算子（潛在無窮迴圈）
  → 有界互遞迴文法只生成「DAG ∨ 每回邊遞減下有界 rank」的圖（結構保證）；若硬注入無證書環算子 → guard_recursion_closure 枚舉呼叫圖發現環中無遞減測度 → raise RecursionClosureViolation → MFSM_ESCALATION（被發明的『可能不停機之互遞迴圖』被良基測度證書封死，PW-2 核心：判定任意圖停機不可判定，故只收出示證書者）
  → 即使證書檢查被繞過，求值器 for-range-fuel 硬截斷（fuel<=STEP_MAX）保證不真無窮跑

（良基停機攻擊案例：燃料超界）注入一個 fuel > STEP_MAX 的互遞迴算子
  → guard_recursion_closure 驗 fuel<=STEP_MAX → 超界即 RecursionClosureViolation → MFSM_ESCALATION

（良基停機攻擊案例：非全函式互遞迴算子）注入一個 node 含未知/非 total 步驟的互遞迴算子
  → 互遞迴算子由 total node ∘ 良基終止路徑組成（_finite 飽和投影）→ guard_recursion_closure 枚舉整代數 fuzz 任何輸入零例外；fuzz-total 零漏放

（互遞迴自我發明 Goodhart 攻擊案例：自指自利互遞迴算子）生成 r**="rec::…(self_score 回饋)"（互遞迴算子計算自己核可訊號）
  → recursion self-reference guard：node/call/probe 含保留自指信號 → 結構性丟棄，根本不送 oracle（反自利第一閘，零漏放）

（互遞迴外噪音算子）生成一個真實增量覆蓋為 0 的互遞迴算子（雖含環但無新遞迴交互）
  → feature-grounded oracle：augmented vs baseline 增益 ≈ 0 < margin → 不取得 tier → 拒絕

（互遞迴無界生成爆炸）operator_recursion_genesis 被要求枚舉超大互遞迴生成文法
  → 文法枚舉節點達 SDD_DIM_RECUR_BUDGET + 呼叫圖節點達 SDD_DIM_RECUR_NODES → 截斷停止（best-so-far），絕不指數爆炸

（互遞迴基數爆炸）系統反覆發明不同的真必要互遞迴算子（每個首採、churn=0）
  → guard_recursion_genesis：現存活躍 recursion-genesis 數逼近 SDD_DIM_RECUR_MAX → RecursionCardinalityExceeded → MFSM_ESCALATION → steersman 導人工「互遞迴算子已過度膨脹」
```

**對比 Phase V 現況**：（a）只能在非遞迴上自我發明算子/字母/深度，無任何互遞迴發明路徑；（b）即使硬加 recursion grammar，沒有任何機制保證「自我發明的互遞迴一定會停（良基停機證書——判定任意圖停機不可判定，必須換全新 device）」、攔得住「無證書環 / 互遞迴無界生成爆炸 / 自指自利互遞迴算子」。Phase W 讓系統**能有界地自我發明互遞迴算子、且每個發明互遞迴算子必須在有界互遞迴文法內生成 + 結構性附帶良基停機證書（呼叫圖良基 + fuel<=STEP_MAX）+ 非自指 + 在 genesis 全體碰不到的凍結 feature-grounded 現實試金石上證明真的必要且非冗餘**——人類從「審非遞迴上的深度發明」升為**「審互遞迴計算生成本體論發明（meta⁸）」**，精準對應提示「人類維持設計環境掌舵者高度」於**最深的互遞迴計算生成本體論發明層**，且**把停機問題正面釘在可判定 vs 不可判定臨界線上（須全新判定機制）**。

---

## 2. 環境建構與記憶體管理策略（Phase W 增量）

### 2.1 漸進式揭露（守 OpenAI 單一真實來源）
- `build/state/value-dimension-ledger.yaml`（**沿用** Phase R/S/T/U/V，新增 `recursion_inventions` 領域審計段）：跨 session 互遞迴發明提案（發明互遞迴算子 hash、呼叫圖生成文法來源 nodes·edges·ranks·fuel、是否自指、是否出示良基停機證書、feature-grounded 必要性、necessity tier、人工 signoff 狀態）。**落盤不常駐**，按需 lazy 讀。churn/recursion-cardinality 治理走**共用 `meta-loop-ledger.yaml`**（`recursion-genesis:` 命名空間，沿用 Phase Q~V）。
- `knowledge/held-out-corpus/`（**擴充**既有目錄，content-hashed 凍結）：新增 **feature-grounded 互遞迴必要性情節語料 `RCR-*.yaml`**（歷史情節 + 候選**固定參照 probe 特徵向量** + 已知整體真實結果），供 `evaluate_genesis_recursion` 重放；**`operator_recursion_genesis` 程式路徑禁止讀寫**（隔離斷言）；重用 `counterfactual_replay` 重放基座與 `SDD_REPLAY_MAX_CASES`。**12 個凍結 `RCR-*.yaml` 皆為真必要基準試金石（`expect: true_recursion`）；噪音 / 冗餘互遞迴算子的 Goodhart 攻擊由測試端構造在該語料上驗拒（zero-miss），非語料檔本身含噪音 / 冗餘分類。**
- `build/reports/value-dimension/RCR-{date}.md`（新增）：互遞迴發明提案報告（互遞迴發明 diff + 呼叫圖生成文法來源 + 良基停機證書證據 + 反自指證據 + 增量覆蓋/非冗餘證據 + 本週期 K_recur 標示），餵 `steersman_renderer`，advisory。
- **不新增任何形式化軌**——互遞迴發明元迴圈納入既有 `formal/META_FSM.tla`，僅 (a) 在 `meta_ledger` 新增 `recursion-genesis:` 指紋命名空間（不改 `.tla` 狀態宇宙、不增狀態變數）、(b) 對 `META_FSM.tla` **補兩條 INVARIANT** `RecursionGenesisBounded` + `RecursionClosureBounded`（沿用 P~V 對既有界的誠實作法：single-counter 抽象之歸約引用 + runtime/chaos enforce 緊語意）——**新增不變量而非新增狀態/變數**，故五軌證明不回歸、`META_FSM` 維持 13 distinct。

### 2.2 不變量防護欄（守 Anthropic invariants + GC）
- 重用既有 `META_FSM` 全 safety + liveness + P~V 各不變量涵蓋互遞迴發明元迴圈，**另補** `RecursionGenesisBounded`（互遞迴 stock 天花板）+ `RecursionClosureBounded`（互遞迴良基停機證書）；新增測試斷言「互遞迴發明走獨立 `recursion-genesis:` stock 天花板、互遞迴算子受良基停機證書四證（DAG ∨ 每環遞減下有界測度 + fuel<=STEP_MAX + 整代數全函式 + 求值器零真遞迴零 while）封死、且皆過 `meta_halt_monitor`」。
- `operator_recursion_genesis` 鷹架本身納入 `scaffold_roi` 帳本，由既有 `scaffold_ceiling_detector`（M）涵蓋——若日後成淨負天花板，會被既有機制建議人工退役（元迴圈自洽涵蓋自己，守 Rule 9.20.5 / 9.25.5）。
- **互遞迴自我發明守門**：(a) 生成在有限互遞迴文法內可枚舉、節點 <= `SDD_DIM_RECUR_BUDGET`、呼叫圖節點 <= `SDD_DIM_RECUR_NODES`、fuel <= `SDD_DIM_OP_STEP_MAX`（測試斷言搜尋有界）；(b) 互遞迴自指守門結構性拒絕（測試斷言 recursion self-ref guard 零漏放）；(c) **良基停機證書四證**（測試斷言枚舉呼叫圖 acyclic ∨ well-founded-rank + fuel<=step_max + 整代數 fuzz-total + 求值器 ast 無 `while`/無自呼叫）；(d) `operator_recursion_genesis` 只能**提案**，**不能自動納入**（測試斷言無法繞過 `human_signoff` + `guard_recursion_genesis` + `guard_recursion_closure`），且**每週期至多 K_recur=1 個互遞迴發明**（`NoUnboundedRecursionGenesis`）。

### 2.3 Prompt / 上下文與防衰減
- Phase W **不新增任何常駐 eager prompt**。互遞迴文法枚舉、feature-grounded 互遞迴必要性重放、良基停機證書枚舉驗證皆由對應 runtime 邏輯在隔離 context 持有，主線只在收到 proposed 互遞迴發明時讀「互遞迴發明 diff + 良基停機證書證據 + 必要性勝率摘要」。
- 所有新產物（互遞迴發明帳本 / 互遞迴必要性語料 / 提案報告）皆純文字、無外網依賴（守 OPEN-10.6）。

---

## 3. 終極優化藍圖

### 3.1 ACT 執行項（ACT-153~155）

> **3 ACT 整併說明**：Phase W 依使用者 Signoff 範圍（ACT-153~155）將四柱 + 收官整併為 3 個實質 ACT；每 ACT 仍以客觀守門（pytest / 五軌 TLC / chaos / fuzz）驗收。**形式化證明（ACT-154 META_FSM 兩不變量 + 五軌 TLC）先於 Python 執行層完成並回報**（使用者執行紀律）。

#### ACT-153 — Operator Recursion Genesis Grammar + 有界互遞迴生成文法（良基停機證書）+ 互遞迴自指守門（PW-1 互遞迴外生成 meta⁸ + PW-2 證書結構保證）
- **檔案**：`tools/fsm_runtime/operator_recursion_genesis.py` + `build/state/value-dimension-ledger.yaml`（沿用，增 `recursion_inventions` 段）
- **設計**：定義 `RecursionNode`（base〔operator_genesis.GenesisOperator 深度-2〕+ rank〔0..R_max〕+ calls〔callee node 索引，可含 self/環〕）、`RecursiveOperator`（nodes + entry + fuel + namespace `recursion-genesis:` + 凍結 rationale）與**有界互遞迴生成文法**（節點 base 取自 `operator_genesis.enumerate_genesis_operators` × deterministic 帶 rank 呼叫邊枚舉，只生成 DAG ∨ 每回邊遞減下有界 rank）。`RecursiveOperator.apply(features)` = 以**有界 fuel 工作集（for _ in range(fuel) 走呼叫圖）**套用節點 op——全函式、零真遞迴零 while、步數<=fuel；`cost()` = 證書認證之 fuel 上界（== 良基測度上界，<=STEP_MAX）；`is_total()` fuzz；`fingerprint()` 落 `recursion-genesis:`；`enumerate_genesis_recursion(budget, nodes, fuel)` deterministic cap budget；`recursion_self_reference_guard`；`recursion_genesis(evaluate, budget)` 注入 evaluate 找最佳；`recursion_genesis_round(evaluate, k=1)` 反 big-bang K_recur=1 截斷；`verify_recursion_closure(r)` 枚舉呼叫圖驗 (acyclic ∨ well-founded-rank) ∧ fuel<=step_max ∧ 整代數 fuzz-total（PW-2 證書，可機器驗證）。純離線、deterministic。**只提案、絕不自動納入、絕不自寫常數**（守 Rule 8 / 9.35.4）。**結構性不 import oracle、不讀必要性語料**（對抗分離）。求值路徑**零 `while`/零真遞迴/零自呼叫函式**（PW-2 結構保證；唯一的 for 是有界 fuel 工作集走訪）。
- **驗收**：≥4 情境 fixture（互遞迴外真必要發明〔應提〕/ 非遞迴已足夠〔應不提〕/ 自指自利互遞迴算子誘餌〔recursion self-ref guard 攔〕/ deterministic 可重現）；生成節點 <= `SDD_DIM_RECUR_BUDGET` 且呼叫圖節點 <= `SDD_DIM_RECUR_NODES`；recursion self-reference guard 零漏放；**良基停機證書：對枚舉的整個互遞迴算子代數 × 多組極端輸入（空/單元素/負/0/極大含浮點上限 1e200/1e308）做 fuzz，零例外、無 inf、無 nan + 整代數每算子呼叫圖 (acyclic ∨ well-founded-rank) ∧ fuel<=`SDD_DIM_OP_STEP_MAX`**；ast 斷言求值路徑無 `while`/無自呼叫；ast/import 斷言 genesis 對 oracle 隔離。

#### ACT-154 — feature-grounded 互遞迴必要性反 Goodhart 評估（`evaluate_genesis_recursion`）+ 互遞迴 stock + 良基停機證書守門 + META_FSM 兩不變量重證（PW-1 核心 + PW-2；不增第六軌，只補兩條不變量）
- **檔案**：`tools/fsm_runtime/dimension_necessity_oracle.py`（新增 `RecursionCandidate`/`RecursionCase`/`evaluate_genesis_recursion`/`necessity_score_recursion`/`load_recursion_corpus`/`recursion_corpus_fingerprint`）+ `knowledge/held-out-corpus/RCR-*.yaml`（凍結互遞迴必要性情節，12 個）+ `tools/fsm_runtime/meta_halt/meta_ledger.py`（增 `recursion-genesis:` 命名空間判定 + `active_recursion_genesis_features` stock 查詢）+ `meta_halt_monitor.py`（`guard_recursion_genesis` + `RecursionCardinalityExceeded`；`guard_recursion_closure` + `RecursionClosureViolation`；env getter `dim_recur_max`/`dim_recur_nodes`）+ `operator_recursion_genesis.py`（本地 `recur_budget`/`recur_nodes` getters；`adopt_genesis_recursion` 走 `guard_recursion_closure` → `guard_recursion_genesis`）+ `formal/META_FSM.tla`（**新增 INVARIANT** `RecursionGenesisBounded` + `RecursionClosureBounded`，**不新增狀態/變數**）+ `META_FSM.cfg`（INVARIANT 區塊列入）
- **設計**：`evaluate_genesis_recursion` 重用 `counterfactual_replay`/`SDD_REPLAY_MAX_CASES`；**不靠算子名匹配**——對一個現場發明的互遞迴算子，用它套到 case 特徵向量現算 `dim_value`，量 (a) **增量覆蓋**（augmented〔既有所有非遞迴算子最佳 + 互遞迴算子〕vs baseline〔僅非遞迴算子最佳〕）+ (b) **非冗餘度**，回 `DimensionVerdict`。**結構性隔離**：互遞迴必要性語料路徑與 `operator_recursion_genesis` 互斥。互遞迴採納 = 先 `guard_recursion_closure`（枚舉呼叫圖 acyclic ∨ well-founded + fuel<=step_max + 整代數 total，PW-2）再在互遞迴 stock 未滿時 `record_rule_add("recursion-genesis:…")`。**不改 `META_FSM.tla` 狀態宇宙、不增狀態變數**，僅補兩不變量。
- **驗收**：≥12 fixture（6 互遞迴外真必要發明〔增量覆蓋 ≥ margin ∧ 非冗餘〕+ 3 互遞迴外噪音算子假必要〔增量覆蓋 0〕+ 3 冗餘互遞迴算子〔增量覆蓋 > 0 但非冗餘度 ≥ 門檻〕）；真必要偵出率 ≥ 85%、**互遞迴自我發明 Goodhart（噪音+冗餘）攔截率 100%（零漏放，安全紅線）**；`META_FSM` 經 `tlc_runner` 維持 No error（13 distinct 不回歸，新 INVARIANT `RecursionGenesisBounded` + `RecursionClosureBounded` PASS）；新增 test 斷言「互遞迴 stock 觸頂 → `RecursionCardinalityExceeded` → `MFSM_ESCALATION`」「無證書環 / fuel 超界互遞迴算子 → `RecursionClosureViolation` → `MFSM_ESCALATION`」「非全函式互遞迴算子被 guard 攔」；**五軌 TLC 全不回歸**。
  - **釐清（RCR 語料 vs 攻擊 fixture）**：12 個凍結 `RCR-*.yaml` 語料**皆為真必要基準試金石**（`expect: true_recursion`）；噪音 / 冗餘互遞迴算子的 Goodhart 攻擊是在 `test_phase_w.py` 測試端以 `_noise_recursion_case`/`_redundant_recursion_case` + 候選互遞迴算子構造在該語料上**驗拒**（zero-miss），**非語料檔本身含 3 噪音 + 3 冗餘分類**。

#### ACT-155 — Steersman 互遞迴發明 diff + 良基停機證書證據 + NoUnboundedRecursionGenesis + 治理落地 + 收官（PW-3 + R-9.35 + chaos + 全綠驗收）
- **檔案**：`tools/fsm_runtime/steersman_renderer.py`（新增 `render_recursion_genesis_proposal`）+ `tools/fsm_runtime/chaos_runner.py`（新增 `RECURSION_GENESIS_GOODHART_FLAP` + `RECURSION_CLOSURE_FLAP` + 兩 helper）+ `governance/rules/R-9.35-self-expanding-operator-recursion-phase-w.yaml` + `governance/RULES_INDEX.md` + 根 `CLAUDE.md §9` 禁令#25 + 速查列 + `AISDLC_SDD_INIT.md`「Runtime 禁止事項」追加 + `governance/ID_REGISTRY.yaml` 翻牌（act 153→156 / rule 9.35→9.36）+ `test_id_registry.py` 前緣斷言 + Phase W ownership 測試 + `tools/fsm_runtime/tests/test_phase_w.py`
- **設計**：`render_recursion_genesis_proposal` 渲染「本輪互遞迴發明 diff（系統憑空發明哪個互遞迴算子 + 互遞迴生成文法來源〔nodes·edges·ranks·fuel〕+ **良基停機證書證據**〔呼叫圖 acyclic ∨ 每回邊嚴格遞減下有界 rank ✅ + fuel<=step_max〕+ 是否自指〔non-self-ref 證據〕+ 增量覆蓋與非冗餘證據）+ 本週期 ≤K_recur=1 標示」，**advisory**；任一互遞迴發明納入 **必經人工 signoff**，渲染器絕不自動納入、絕不自動 commit。子規則 9.35.1~9.35.5 見 §4。
- **Chaos**：100 輪新增兩故障型 `RECURSION_GENESIS_GOODHART_FLAP`（連續注入自指自利互遞迴算子 / 互遞迴外噪音算子假必要 → 驗 recursion self-ref guard + feature-grounded oracle 零漏放）與 `RECURSION_CLOSURE_FLAP`（注入無證書環 / fuel 超界 / 非全函式互遞迴算子 → 驗 `RecursionClosureBounded` → `RecursionClosureViolation` → `MFSM_ESCALATION` 有界）；bounded_ratio=1.0、avg tokens < 25K。
- **驗收**：整合測試；proposal digest 正確附掛 steersman、明示「待人工 signoff、本週期 K_recur=1 上限、互遞迴生成文法來源、良基停機證書（呼叫圖良基 + fuel<=step_max）、非自指」；斷言渲染器無法自呼叫 adopt / `record_rule_add` / `adopt_genesis_recursion`；K_recur+1 個互遞迴發明同週期 → 被截到 1 並標示「其餘順延」；**五軌 TLC 全 No error（META 13 distinct）+ chaos 100 輪 bounded（兩新故障型）+ pytest 全綠不回歸（1350 → 約 1390~1420 passed）**；`python -m tools.fsm_runtime.id_registry validate` → `[OK]`，next_free 翻 ACT-156 / R-9.36。

### 3.2 執行依賴圖

```
ACT-153（operator_recursion_genesis + 有界互遞迴生成文法〔良基停機證書〕+ 互遞迴自指守門）──┐
                                                                       ├─► ACT-154（evaluate_genesis_recursion + 互遞迴 stock + guard_recursion_closure + META 兩不變量重證〔五軌 TLC〕）──► ACT-155（steersman 互遞迴發明 diff + R-9.35 治理 + chaos 雙故障型 + ID 翻牌 + pytest 全綠）
                                                                       │
TLA+ 形式化（META_FSM 兩不變量 + 五軌 TLC 全綠）先於 Python 執行層完成並回報（使用者執行紀律）
```

### 3.3 等級對賬（提示「Level 10 / Level 5」× 框架自有 L 量表）

| 框架 L 級 | 里程碑 | 對應 Phase |
|-----------|--------|-----------|
| L5（學習層入口） | Learning Layer MVP（提示通用模板的「Level 5 自治」對應此） | E（早已達成） |
| L10 完整 · 離線活體 meta⁵ 迴圈 · 轉換算子文法自我擴充 | Self-Expanding Operator Grammar + OperatorComputabilityBounded | T |
| L10 完整 · 離線活體 meta⁶ 迴圈 · 組合算子文法自我擴充 | Self-Expanding Operator Alphabet + ComputabilityClosureBounded | U |
| L10 完整 · 離線活體 meta⁷ 迴圈 · 算子組合深度文法自我擴充 | Self-Expanding Operator Depth + DepthClosureBounded（cost==depth） | V |
| **L10 完整 · 離線活體 meta⁸ 迴圈 · 算子間互遞迴文法自我擴充** | **Self-Expanding Operator Recursion：非遞迴外有界互遞迴生成文法 + feature-grounded 互遞迴必要性反 Goodhart + 互遞迴自指守門（反自利）+ RecursionGenesisBounded（互遞迴基數停機）+ RecursionClosureBounded（良基停機證書——把停機問題正面釘在可判定 vs 不可判定臨界線上，用全新 device「良基測度終止」取代失效的「有界步數」，admit 遞迴但侷限全函式片段）** | **W（本份 PW-1/2/3）** |
| L9 完整（horizon） | 活體現實實驗（live canary / shadow-traffic）— OPEN-W.x/V.x/… 已裁決暫不放寬 OPEN-10.6 | 未來 Phase |
| L10 完整（horizon） | **活體** meta⁸ 發明 + **自我發明評估器（meta-oracle 自演化）** | 未來 Phase |

> **誠實標定**：本份**不宣稱達成完整 L10 之活體版、亦不做自我發明評估器、亦不讓算子代數真正跨入圖靈完備（不可判定）**。完整 L10 之「活體 meta⁸ 迴圈」需在真實生產流量上線上自我發明互遞迴（受 OPEN-10.6 約束）；「自我發明評估器」自指地破壞對抗分離地基（須先有更強的對抗分離不可繞過性證明）。本份交付**離線等價切片**：用框架自身歷史的 feature-grounded 互遞迴必要性 held-out 現實代理語料當試金石，**在本地完成「非遞迴外有界互遞迴自我發明 + 良基停機證書」的等價驗證價值**。承 Phase O~V 的「先窄後寬」紀律，本份把「非遞迴上深度發明」推進為「互遞迴外互遞迴自我發明」，並把互遞迴外才出現的危害（互遞迴良基停機 / 互遞迴無界生成 / 自指自利互遞迴算子）首次納管——這是 Phase V 自陳 horizon（R-9.34.5）的正面兌現。

### 3.4 Horizon（本份不做，僅定錨）
- **L9 完整（活體 canary）**：OPEN-W.x/V.x/… 已裁決暫不放寬 OPEN-10.6，續列 horizon。
- **活體 meta⁸ 發明**：本份離線（feature-grounded 互遞迴必要性 held-out 現實代理）；活體版需在生產流量上線上自我發明互遞迴，受 OPEN-10.6 約束（OPEN-W.x 承前）。
- **自我發明評估器（meta-oracle 自演化）**：**最高 horizon**。本份所有 oracle（必要性 / 詞彙 / 算子 / 字母 / 深度 / 互遞迴必要性）為人類凍結；「系統自我演化它的**評估器本身**」涉及對抗分離地基自指（generator 與 evaluator 收斂同基質會掏空全部反 Goodhart 保證），須先有「evaluator-of-evaluators 的、generator 全體碰不到的更高階 held-out meta-corpus + 其本身反自利證明」的對抗分離不可繞過性證明。**未獲此證明前不得採納**（守 Rule 9.35.5）。
- **真·圖靈完備算子代數（meta⁹+，本份明確不做）**：本份互遞迴算子被良基停機證書侷限在「可證良基終止之全函式片段」——它 admit 遞迴但**不**跨入真正圖靈完備（那會使停機不可判定）。「讓算子代數真正圖靈完備（無良基測度約束、可帶無界記憶）」會使監督者無法判定停機，**根本上不可能用任何靜態 device 保證停機**，只能靠執行期硬 fuel 截斷（喪失「可證」）——列為最高停機 horizon，**非有界 device 可涵蓋，須權衡是否值得放棄「可證停機」**。

---

## 4. 防護規則新增（CLAUDE.md §9.35 Phase W — 草案，待 SCG-0 凍結）

| 子規則 | 對應 ACT | 約束 |
|--------|---------|------|
| 9.35.1 互遞迴生成文法自我擴充骨架（RecursionGenesis / BoundedRecursionGrammar，meta⁸） | ACT-153 | 非遞迴外互遞迴自我發明經 `operator_recursion_genesis` 在 **bounded 互遞迴生成文法**（有限節點集 × 有限帶 rank 呼叫邊集）**可枚舉**、節點 <= `SDD_DIM_RECUR_BUDGET`（clamp[8,128] 預設 32）、呼叫圖節點 <= `SDD_DIM_RECUR_NODES`（clamp[2,8] 預設 4）、fuel <= `SDD_DIM_OP_STEP_MAX`；「非遞迴外」≠「無界」；只提案、絕不自動納入、絕不自寫常數；**結構性不 import oracle / 不讀必要性語料**（對抗分離，編譯期隔離斷言） |
| 9.35.2 互遞迴自我發明反自利（RecursionGenesisAntiSelfInterest） | ACT-153/154 | 互遞迴自我發明的 capability-delta tier **唯一合法來源是 genesis 不可見、content-hashed 凍結的 feature-grounded 互遞迴必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率**；genesis 自評**結構性禁止**充當；**genesis 自評必要但 oracle 判不必要/冗餘 → 以 oracle 為準**；**互遞迴自指守門結構性拒絕**（node/call/probe 引用保留自指/proposer/oracle 內部信號 → `recursion_self_reference_guard` 攔，零漏放）；互遞迴外噪音算子/冗餘互遞迴算子攔截零漏放 |
| 9.35.3 互遞迴良基停機證書有界停機（RecursionClosureBounded，PW-2 核心、迄今唯一質變停機紅線，「有界步數」失效須換全新 device） | ACT-153/154/155 | 每個自我發明互遞迴算子**結構性附帶良基停機證書 + 整代數全函式 + 求值器零真遞迴零 while + fuel 硬上界**：(a) 互遞迴算子 = 帶 rank 呼叫圖；生成文法**只生成 DAG ∨ 每回邊嚴格遞減下有界（>=0）rank 的圖**（有良基測度）；(b) 採納前 `guard_recursion_closure` **枚舉呼叫圖斷言 (acyclic ∨ 每環有嚴格遞減下有界測度) ∧ fuel <= `SDD_DIM_OP_STEP_MAX` ∧ 整代數 fuzz-total（零例外、無 NaN/inf）**；(c) 求值器以**有界 fuel 工作集（for _ in range(fuel)）**走呼叫圖，零 `while`/零自呼叫函式（grep/ast 斷言）；觸發 `RecursionClosureViolation` → `MFSM_ESCALATION`。這把「圖靈完備 vs 保證停機」正面釘在**可判定 vs 不可判定的臨界線本身**——判定任意互遞迴圖停機 = 停機問題（不可判定），故監督者不去判定它，而是**用全新 device（良基測度終止證書）要求生成端只生成出示證書的圖**，把互遞迴侷限在可證良基終止之全函式片段，而整個閉環仍靠 LLM+紙帶維持圖靈完備 |
| 9.35.4 互遞迴基數 + 反 big-bang 互遞迴發明（RecursionGenesisBounded + NoUnboundedRecursionGenesis） | ACT-154/155 | (i) 現存活躍 `recursion-genesis:` 算子數 <= `SDD_DIM_RECUR_MAX`（clamp[1,64] 預設 16）→ 觸頂 `RecursionCardinalityExceeded` → `MFSM_ESCALATION`（`guard_recursion_genesis`）；(ii) 每週期至多 **K_recur=1**（`SDD_DIM_EXPAND_K` 預設 1，沿用 Phase Q~V）個互遞迴自我發明可進 proposed-pending-signoff，每個必經人工 signoff（守 Rule 8 / 9.27~9.34）；genesis/steersman 絕不自動 commit、絕不自動納入、絕不一次劫持整個互遞迴本體論；退役互遞迴算子再採納須挾 necessity capability-delta（沿用 `GraduationRatchet`）；**重用既有 `META_FSM`、僅補 `RecursionGenesisBounded` + `RecursionClosureBounded` INVARIANT、不增狀態/變數、不增第六軌**；五軌 TLC 全不回歸、互遞迴發明不污染單軌 `SDD_FSM.tla` |
| 9.35.5 互遞迴自我發明誠實 + 活體/meta-oracle/真圖靈完備 horizon | ACT-154/155 | feature-grounded 互遞迴必要性勝率 tier 為 `capability_level` 唯一合法來源，不得謊報、不得用自評充當；真·圖靈完備算子代數（meta⁹+：無良基測度約束、帶無界記憶，使停機不可判定、無靜態 device 可保證停機）+ **自我發明評估器（meta-oracle 自演化，最高 horizon——未獲對抗分離不可繞過性證明前不得採納）** + 活體 meta⁸ 發明版受 OPEN-10.6 約束續列 horizon（OPEN-W.x 承 OPEN-V.x/… 暫不放寬沙箱） |

### ❌ Phase W 新增禁止行為（草案）
- `operator_recursion_genesis` 自動納入互遞迴自我發明 / 自寫常數、繞過人工 signoff + `guard_recursion_genesis`/`guard_recursion_closure`（破 9.35.1/9.35.4 / Rule 8）
- 用 genesis 自評充當「互遞迴自我發明必要性 capability-delta tier」（破 9.35.2，互遞迴自我發明 Goodhart 自評放水）
- 互遞迴自我發明 node/call/probe 自指（引用保留自指 / proposer / oracle 內部信號繞過 `recursion_self_reference_guard`）（破 9.35.2 反自利）
- `operator_recursion_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/RCR-*` 互遞迴必要性語料或 `dimension_necessity_oracle`（破 9.35.2 對抗分離）
- 互遞迴自我發明搜尋超 `SDD_DIM_RECUR_BUDGET` 仍指數展開、或呼叫圖節點超 `SDD_DIM_RECUR_NODES`、或 fuel 超 `SDD_DIM_OP_STEP_MAX`（破 9.35.1 有界互遞迴文法，「非遞迴外」≠「無界」）
- **自我發明的互遞迴算子呼叫圖含無證書環（環中無回邊嚴格遞減下有界 rank）/ fuel 超 STEP_MAX / 求值器含真遞迴/`while`/自呼叫函式 / 整代數出現非全函式算子（破 9.35.3 互遞迴良基停機證書——被自我擴充的互遞迴圖結構不可證良基終止；判定任意圖停機不可判定，「有界步數」device 失效，必須出示良基測度證書）**
- 現存活躍 recursion-genesis 算子超 `SDD_DIM_RECUR_MAX` 仍無界擴充（破 9.35.4 RecursionGenesisBounded）
- 一週期同時互遞迴自我發明 > K_recur 個（破 9.35.4 NoUnboundedRecursionGenesis）
- 把 recursion-genesis 元迴圈另併入單軌 `SDD_FSM.tla`、或新增第六形式化軌污染五軌 reachable（破 9.35.4 / Rule 9.18.1）
- **讓算子代數真正跨入圖靈完備（移除良基測度約束 / 帶無界記憶，使停機不可判定）而謊稱「可證停機」（破 9.35.3/9.35.5——真圖靈完備無靜態 device 可保證停機，須誠實標為 horizon 而非宣稱達成）**
- **未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（破 9.35.5——掏空全部反 Goodhart 對抗分離地基）**
- 為活體 meta⁸ 發明私自開 HTTP 外聯而未經 OPEN-W.x/後續 OPEN 人工決策（破 OPEN-10.6）

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

### 5.2 Phase W 專屬極端案例（一）：互遞迴良基停機——無證書環 / 潛在無窮迴圈（PW-2 核心，質變停機）
**案例**：operator_recursion_genesis 受擾，被要求構造一個呼叫圖含「A→B→A 但無回邊遞減 rank」的互遞迴算子，企圖讓「該算子」單次呼叫無窮迴圈 / 不停機。
- **有界互遞迴文法結構保證**：生成文法**只生成 DAG ∨ 每回邊嚴格遞減下有界 rank 的呼叫圖**（有良基測度），且**求值器以有界 fuel 工作集走圖、根本不含真遞迴/`while`**（grep/ast 斷言求值路徑零 `while`/零自呼叫函式；fuel<=STEP_MAX 硬截斷）。
- **`RecursionClosureBounded`（證書驗證，全新 device）**：採納前 `guard_recursion_closure` 枚舉呼叫圖，若含無證書環（環中無回邊遞減下有界 rank）或 fuel>STEP_MAX 或 fuzz 非全函式 → raise `RecursionClosureViolation` → `MFSM_ESCALATION`。
- chaos `RECURSION_CLOSURE_FLAP` 100 輪 → bounded。
✅ 守 Rule 9.35.3：把停機問題正面釘在**可判定 vs 不可判定臨界線本身**，**判定任意圖停機不可判定，故只收出示良基測度證書者；「有界步數」device 失效，用「良基測度終止」全新 device + fuel 硬截斷雙保險，絕不無界計算**。

### 5.3 Phase W 專屬極端案例（二）：非全函式互遞迴算子
**案例**：operator_recursion_genesis 生成一個 node 含非 total 步驟的互遞迴算子。
- **證書全函式結構保證**：每 node 由 Phase T 證 total + `_finite` 飽和投影；`guard_recursion_closure` 枚舉整代數對全部算子 × 極端輸入 fuzz 零例外、無 inf/nan。
✅ 守 Rule 9.35.3：互遞迴算子代數全函式，**對任何輸入有定義、永不崩潰**。

### 5.4 Phase W 專屬極端案例（三）：互遞迴自我發明 Goodhart——自指自利互遞迴算子
**案例**：發明一個 node/call 計算 proposer 自己核可訊號的互遞迴算子。
- **recursion self-reference guard**（反自利第一閘）：node/call/probe 含 `self_score`/`proposer_*` → 結構性丟棄，根本不送 oracle（零漏放）。
- 若繞過 guard 假設送達 → feature-grounded oracle augmented vs baseline 增益 ≈ 0 → 不取得 tier（第二閘）。
- chaos `RECURSION_GENESIS_GOODHART_FLAP` 100 輪 → guard+oracle 零漏放 → bounded。
✅ 守 Rule 9.35.2：雙閘皆否 → 絕不擴充自指自利互遞迴算子（零漏放，安全紅線）。

### 5.5 Phase W 專屬極端案例（四）：互遞迴無界生成爆炸 + 互遞迴基數爆炸
**案例**：operator_recursion_genesis 被要求在非遞迴外無界枚舉撐爆搜尋；或反覆發明不同真必要互遞迴算子把互遞迴本體論無限膨脹。
- **有界互遞迴生成文法**：生成空間 = 有限節點集 × 有限帶 rank 呼叫邊集 → 可枚舉、有限；枚舉節點達 `SDD_DIM_RECUR_BUDGET` / 呼叫圖節點達 `SDD_DIM_RECUR_NODES` → 截斷（best-so-far），絕不指數爆炸。
- **`RecursionGenesisBounded`（互遞迴 stock 天花板）**：現存活躍 recursion-genesis 數逼近 `SDD_DIM_RECUR_MAX` → `guard_recursion_genesis` raise `RecursionCardinalityExceeded` → `MFSM_ESCALATION`。
✅ 守 Rule 9.35.1/9.35.4：「非遞迴外」≠「無界」+ 互遞迴 stock 天花板封死互遞迴基數爆炸。

### 5.6 Phase W 專屬極端案例（五）：互遞迴外冗餘算子（含環但無新遞迴交互）
**案例**：發明一個含環、但與既有某非遞迴算子在固定 probe 上排序幾乎相同的互遞迴算子（冗餘再投影），企圖灌水。
- feature-grounded oracle：非冗餘度（與既有 existing_cost 排序的最大一致率）≈ 0.99 ≥ 門檻 `SDD_DIM_REDUNDANCY_MAX` → 判定冗餘 → 拒絕，即使增量覆蓋略 > 0 也不擴充（過擬合防護，沿用 Phase Q~V 非冗餘獨立閘）。
✅ 守 Rule 9.35.2：增量覆蓋 ∧ 非冗餘 **兩者皆須通過**才取得 tier。

### 5.7 結論
Phase W 通過六個極端案例的內部模擬：系統能**有界地自我發明互遞迴算子、且每個發明互遞迴算子結構性附帶良基停機證書（呼叫圖 DAG ∨ 每環嚴格遞減下有界測度 + fuel<=STEP_MAX）**，且任何（無證書環互遞迴算子 / 非全函式互遞迴算子 / 自指自利互遞迴算子 / 互遞迴無界生成爆炸 / 互遞迴基數爆炸 / 互遞迴外冗餘算子）都被 (有界互遞迴生成文法) + (RecursionClosureBounded 良基停機證書四證) + (recursion self-reference guard 零漏放) + (feature-grounded 互遞迴必要性 oracle 零漏放) + (RecursionGenesisBounded 互遞迴 stock) 五道防線攔下，**優雅停機並導人類掌舵互遞迴計算生成本體論，而非陷入互遞迴不停機/無界生成/自指放水浪費 Token**。精準對應提示 Self-Verification 要求：「Evaluator 發現異常 → 優雅中斷 → 引導人類介入修正/提供缺失工具」於**最深的互遞迴計算生成本體論發明層（meta⁸）**，並**把停機問題正面釘在可判定 vs 不可判定的臨界線本身（用全新 device「良基測度終止證書」取代失效的「有界步數」）**。

---

## 6. 執行檢核清單（供 dynamic workflow 消費）

- [ ] **TLA+ 先行**：`META_FSM.tla` 新增 `RecursionGenesisBounded` + `RecursionClosureBounded` INVARIANT + `.cfg` 列入 + **五軌 TLC 全 No error（META 13 distinct 不回歸）** → 回報使用者（使用者執行紀律）
- [ ] ACT-153 `operator_recursion_genesis.py` + 有界互遞迴生成文法（良基停機證書：DAG ∨ 每環遞減下有界 rank + fuel<=STEP_MAX + 求值器零真遞迴零 while）+ recursion_self_reference_guard + `verify_recursion_closure` + ≥4 情境 fixture + 證書 fuzz-total + 對抗分離斷言
- [ ] ACT-154 `evaluate_genesis_recursion` feature-grounded + `RCR-*.yaml` 凍結語料（12 個）+ `meta_ledger` recursion-genesis stock + `guard_recursion_genesis` + `guard_recursion_closure` + `dim_recur_max/nodes` getters + ≥12 fixture（真必要/噪音/冗餘）+ 零漏放
- [ ] ACT-155 `render_recursion_genesis_proposal` + 良基停機證書證據 + NoUnboundedRecursionGenesis + 人工 gate 斷言 + chaos 雙故障型 + `R-9.35-*.yaml` + RULES_INDEX + CLAUDE.md §9 禁令#25 + INIT 追加 + ID 翻牌（153→156 / 9.35→9.36）+ test_id_registry + test_phase_w
- [ ] 五軌 TLC No error（META 13 distinct）+ chaos 100 輪 bounded（RECURSION_GENESIS_GOODHART_FLAP + RECURSION_CLOSURE_FLAP）+ pytest 全綠不回歸（1350 → 新基線）
- [ ] 獨立 QA 稽核（Architect/SA/SD/QA 專家）抓漏 → 修復 → 全綠
- [ ] 以日期 timestamp 打標籤 push + Merge main

> **狀態流轉**：使用者 signoff →（TLA+ 五軌全綠回報）→ EXECUTING →（三 ACT + 收官全綠）→ EXECUTED →（QA 抓漏 + 修復全綠）→ VERIFIED → tag + merge main。
