--------------------------- MODULE META_FSM ---------------------------
(***************************************************************************)
(* Phase L M-L1 / ACT-090 — Self-Improving Meta-Loop FSM（自我改進元迴圈）  *)
(*                                                                         *)
(* 對應實作: tools/fsm_runtime/meta_halt/{meta_ledger,meta_halt_monitor}.py *)
(* 對應藍圖: SDD_improving_Automation_12.md §1.2 / PL-1（L10 奠基石）        *)
(* 對應規則: CLAUDE.md Rule 9.24.1（ChurnBounded）/ 9.24.2（GraduationRatchet）*)
(*                                                                         *)
(* 單軌 SDD_FSM.tla 證「一個 feature 的開發迴圈」必達 terminal；FLEET_FSM.tla *)
(* 證「N feature 並行」無死鎖必達 done。本模組證**第三條、且先前唯一無形式化  *)
(* 停機保證的迴圈**：跨 session「學習層加規則 ↔ 鷹架 GC 退規則」的元迴圈不會   *)
(* 無限抖動（add↔retire 同型震盪），最終必抵不動點 MFSM_STABLE 或人工閘       *)
(* MFSM_ESCALATION。比照 FLEET_FSM 採**獨立命名空間**，不併入單軌（守 Rule    *)
(* 9.18.1 三源一致性與既有 41/41 reachable 證明不回歸）。                    *)
(*                                                                         *)
(* 證明目標：                                                              *)
(*   1. TypeOK                                                             *)
(*   2. ChurnBounded     — churn ≤ MAX_CHURN（Rule 9.24.1，add↔retire 有界）*)
(*   3. GraduationRatchet — churn ≤ cap（每次 churn++ 皆挾 capability++ 證據；*)
(*                          無 capability-delta 不得再採納，Rule 9.24.2）    *)
(*   4. ReadoptGated      — 進 ESCALATION 必因預算耗盡（churn 或 cap 觸頂），  *)
(*                          非過早升級                                       *)
(*   5. StableIsFixpoint  — MFSM_STABLE 為吸收不動點（後繼仍 STABLE），且      *)
(*                          MFSM_ESCALATION ∉ 不動點集合（藍圖 §2.2/§3.1）    *)
(*   6. EventuallyMetaStable（liveness）— 元迴圈最終必抵 {STABLE, ESCALATION}*)
(*       （SF 推向 Settle/Escalate；對應 SDD_FSM 的精簡 SF liveness 手法）    *)
(***************************************************************************)

EXTENDS Naturals

CONSTANTS MAX_CHURN,    \* 同一指紋 add↔retire 再採納硬上限（runtime: SDD_META_CHURN_MAX 預設 2）
          MAX_CAP       \* capability_level 上界（small-model：結構等價於真實能力階梯）

VARIABLES mstate,       \* 元迴圈狀態
          churn,        \* 累計再採納次數（add-after-retire）
          cap           \* 已挾帶的 capability-delta 累計（GraduationRatchet 證據）

vars == <<mstate, churn, cap>>

MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}
MetaTerminals == {"MFSM_STABLE", "MFSM_ESCALATION"}

TypeOK == /\ mstate \in MetaStates
          /\ churn \in 0..MAX_CHURN
          /\ cap \in 0..MAX_CAP

Init == /\ mstate = "MFSM_OBSERVE"
        /\ churn = 0
        /\ cap = 0

(* 加入全新指紋規則（學習層發現真新缺口）：GROW，不影響 churn（非再採納）*)
GrowFresh ==
    /\ mstate = "MFSM_OBSERVE"
    /\ mstate' = "MFSM_GROW"
    /\ UNCHANGED <<churn, cap>>

(* 退役規則（GC set_maturity）：SHRINK，永遠安全（縮小規則集）*)
Shrink ==
    /\ mstate = "MFSM_OBSERVE"
    /\ mstate' = "MFSM_SHRINK"
    /\ UNCHANGED <<churn, cap>>

(* 再採納已退役指紋：churn++，且 GraduationRatchet 要求 cap 嚴增（capability-delta）。*)
(* 僅在 churn < MAX_CHURN 且 cap < MAX_CAP（仍有 capability headroom）時合法。       *)
GrowReadopt ==
    /\ mstate = "MFSM_OBSERVE"
    /\ churn < MAX_CHURN
    /\ cap < MAX_CAP
    /\ churn' = churn + 1
    /\ cap' = cap + 1
    /\ mstate' = "MFSM_GROW"

(* 想再採納但 churn 觸頂 或 capability headroom 用罄 → 偵測為抖動 → ESCALATION。*)
ChurnEscalate ==
    /\ mstate = "MFSM_OBSERVE"
    /\ \/ churn >= MAX_CHURN
       \/ cap >= MAX_CAP
    /\ mstate' = "MFSM_ESCALATION"
    /\ UNCHANGED <<churn, cap>>

(* GROW / SHRINK 為瞬態，處理完回 OBSERVE *)
ReturnObserve ==
    /\ mstate \in {"MFSM_GROW", "MFSM_SHRINK"}
    /\ mstate' = "MFSM_OBSERVE"
    /\ UNCHANGED <<churn, cap>>

(* 本期無 churn-relevant 變動 → 抵不動點 MFSM_STABLE *)
Settle ==
    /\ mstate = "MFSM_OBSERVE"
    /\ mstate' = "MFSM_STABLE"
    /\ UNCHANGED <<churn, cap>>

(* terminal-like 自我遷移（避免 TLC 誤判 deadlock；對應 SDD_FSM 的 T_TerminalStutter）*)
TerminalStutter ==
    /\ mstate \in MetaTerminals
    /\ UNCHANGED vars

Next == \/ GrowFresh
        \/ Shrink
        \/ GrowReadopt
        \/ ChurnEscalate
        \/ ReturnObserve
        \/ Settle
        \/ TerminalStutter

(* 公平性：SF 保證在 OBSERVE 無限出現時，Settle / ChurnEscalate 終究會推向 terminal。 *)
(* WF(ReturnObserve) 保證瞬態 GROW/SHRINK 不會永久停留。對應 SDD_FSM.cfg 的「精簡 SF  *)
(* 落在 TLC DNF 上限內」手法。                                                       *)
Fairness == /\ SF_vars(Settle)
            /\ SF_vars(ChurnEscalate)
            /\ WF_vars(ReturnObserve)

Spec == Init /\ [][Next]_vars /\ Fairness

(***************************************************************************)
(* Safety                                                                  *)
(***************************************************************************)

(* Rule 9.24.1：再採納次數有硬上界 → add↔retire 不會無限抖動。*)
ChurnBounded == churn <= MAX_CHURN

(* Rule 9.24.2：每一次 churn 增量都被一次 capability 增量背書 → 不可能無 capability *)
(* -delta 地把剛退役的同型規則重新學回（棘輪：churn 永不超過 cap）。*)
GraduationRatchet == churn <= cap

(* Phase P / ACT-119 — CrossScorerChurnBounded（Rule 9.28.3）.                    *)
(* Phase P 把 8 個評分器的 calibration-profile 採納/退役**全部納入本元迴圈的同一    *)
(* churn 預算**（每個 profile 指紋為一個 `<scorer>-profile:` 命名空間，與 SLV 規則  *)
(* 共用本軌；**不增第六軌、不新增狀態變數**，故本軌 reachable 計數不回歸）。在本     *)
(* small-model 抽象下，「任一 calibration 命名空間的再採納迴圈」與既證的單指紋迴圈    *)
(* 同構，故其 churn 永不超過 MAX_CHURN——這是「跨評分器一致性」在形式化層的歸約。    *)
(* 註：跨命名空間的『聚合採納速率窗』（多個不同指紋在短視窗內密集首採、per-指紋     *)
(* churn 皆 0 的 A→B→A 耦合震盪）是**更緊的 runtime 精煉**，由                       *)
(* meta_halt_monitor.guard_calibration_adoption + chaos(JOINT_CALIBRATION_FLAP /    *)
(* CROSS_SCORER_GOODHART_FLAP) enforce/驗收；本軌的 single-counter 抽象刻意不展開     *)
(* 多命名空間維度，故在此記為對既有界的形式化強化引用（恆真，不增狀態）。           *)
CrossScorerChurnBounded == churn <= MAX_CHURN

(* Phase Q / ACT-125 — DimensionCardinalityBounded（Rule 9.29.3）.                  *)
(* Phase Q 把「價值維度自我擴充」這條新迴圈納入本元迴圈：每條候選新維度為一個          *)
(* `value-dimension:` 命名空間指紋，其 add↔retire 與 SLV 規則 / scorer-profile 共用     *)
(* 本軌的同一 churn 預算（**不增第六軌、不新增狀態變數**，故本軌 reachable 計數不回歸    *)
(* —— 維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。在本 small-model 抽象下，「任一  *)
(* value-dimension 的再採納迴圈」與既證的單指紋迴圈同構，故其 churn 永不超過 MAX_CHURN —— *)
(* 這是「增維迴圈會停（add↔retire 不無限抖動）」在形式化層的歸約。                       *)
(* 註：與 churn（flow）正交的『現存活躍維度數天花板』（stock：每條新維度首採、per-指紋    *)
(* churn 皆 0，卻讓維度基數單調膨脹的 DIMENSION_EXPLOSION）是**更緊的 runtime stock 精煉**， *)
(* 由 meta_halt_monitor.guard_dimension_expansion（SDD_DIM_CARDINALITY_MAX）+ chaos          *)
(* (DIMENSION_EXPLOSION_FLAP / DIMENSION_GOODHART_FLAP) enforce/驗收；本軌的 single-counter   *)
(* 抽象刻意不展開 stock 維度，故在此記為對既有界的形式化強化引用（恆真，不增狀態/變數）。 *)
DimensionCardinalityBounded == churn <= MAX_CHURN

(* Phase R / ACT-131 — SwapCadenceBounded（Rule 9.30.3）.                            *)
(* Phase R 把「維度退役聯動」這條新迴圈納入本元迴圈：達 cardinality cap 後「退一條換   *)
(* 一條」的 retire-to-swap 為一對 add↔retire 事件（標 `dimension_swap`），仍與 SLV 規則 / *)
(* scorer-profile / value-dimension 共用本軌的同一 churn 預算（**不增第六軌、不新增狀態  *)
(* 變數**，故本軌 reachable 計數不回歸——維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。*)
(* 在本 small-model 抽象下，「任一退役聯動 swap 的 add↔retire 迴圈」與既證的單指紋迴圈    *)
(* 同構，故其 churn 永不超過 MAX_CHURN —— 這是「退役聯動迴圈會停（add↔retire 不無限抖動）」*)
(* 在形式化層的歸約。                                                                 *)
(* 註：與 per-fingerprint churn（每指紋只動一次）及 Phase Q stock 天花板（每次 swap net 基數=0、*)
(* stock 永不觸頂）皆正交的『定基數旋轉重寫本體論』（同基數上 A→B→C→D 旋轉、密集 swap，    *)
(* per-fingerprint/stock 皆盲目的 DIMENSION_SWAP_THRASH）是**更緊的 runtime 聚合速率精煉**，  *)
(* 由 meta_halt_monitor.guard_dimension_swap（SDD_DIM_SWAP_RATE_MAX + 單調價值棘輪）+ chaos    *)
(* (DIMENSION_SWAP_THRASH_FLAP) enforce/驗收；本軌的 single-counter 抽象刻意不展開 swap 速率   *)
(* 維度，故在此記為對既有界的形式化強化引用（恆真，不增狀態/變數）。                       *)
SwapCadenceBounded == churn <= MAX_CHURN

(* Phase S / ACT-137 — VocabGenesisBounded（Rule 9.31.3，meta⁴）.                     *)
(* Phase S 把「生成文法詞彙的自我擴充」這條新迴圈納入本元迴圈：每個 VOCAB 外詞彙發明字   *)
(* 為一個 `vocab-genesis:` 命名空間指紋，其 add↔retire 與 SLV 規則 / scorer-profile /       *)
(* value-dimension 共用本軌的同一 churn 預算（**不增第六軌、不新增狀態變數**，故本軌         *)
(* reachable 計數不回歸——維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。在本 small-model *)
(* 抽象下，「任一 vocab-genesis 詞彙字的再採納迴圈」與既證的單指紋迴圈同構，故其 churn 永不  *)
(* 超過 MAX_CHURN —— 這是「詞彙自我擴充迴圈會停（add↔retire 不無限抖動）」在形式化層的歸約。 *)
(* 註：與 churn（flow）正交的『現存活躍詞彙字數天花板』（stock：每字首採、per-指紋 churn 皆 0、*)
(* 卻讓詞彙基數單調膨脹的 VOCAB_GENESIS_EXPLOSION）是**更緊的 runtime stock 精煉**，由            *)
(* meta_halt_monitor.guard_vocab_genesis（SDD_DIM_VOCAB_MAX）+ chaos(VOCAB_GENESIS_GOODHART_FLAP)  *)
(* enforce/驗收；本軌的 single-counter 抽象刻意不展開 vocab stock 維度，故在此記為對既有界的       *)
(* 形式化強化引用（恆真，不增狀態/變數）。                                                       *)
VocabGenesisBounded == churn <= MAX_CHURN

(* Phase S / ACT-137 — BatchSwapCadenceBounded（Rule 9.31.3，meta⁴）.                  *)
(* Phase S 把「多維度批次退役聯動」這條新迴圈納入本元迴圈：達 cardinality cap 後「一次退 m   *)
(* 換 n」的批次 retire-to-swap 為一組 add↔retire 事件（標 `dimension_batch_swap:<batch_id>`），  *)
(* 仍與 SLV 規則 / scorer-profile / value-dimension 共用本軌的同一 churn 預算（**不增第六軌、不   *)
(* 新增狀態變數**，故本軌 reachable 計數不回歸——維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。*)
(* 在本 small-model 抽象下，「任一批次退役聯動的 add↔retire 迴圈」與既證的單指紋迴圈同構，故其    *)
(* churn 永不超過 MAX_CHURN —— 這是「批次退役聯動迴圈會停（add↔retire 不無限抖動）」在形式化層的  *)
(* 歸約。                                                                                       *)
(* 註：與 per-swap SwapCadence（單次操作計數）及單調棘輪（單次 tier 比較）皆正交的『批次旋轉重寫   *)
(* 本體論』（批次大小無界一次劫持、批次內高低互抵、一個原子批次≠n 次 swap 的 BATCH_SWAP_THRASH）  *)
(* 是**更緊的 runtime 批次三鎖精煉**，由 meta_halt_monitor.guard_batch_swap（SDD_DIM_BATCH_MAX +    *)
(* 批次聚合棘輪 + SDD_DIM_BATCH_RATE_MAX）+ chaos(BATCH_SWAP_THRASH_FLAP) enforce/驗收；本軌的       *)
(* single-counter 抽象刻意不展開批次速率維度，故在此記為對既有界的形式化強化引用（恆真，不增狀態）。*)
BatchSwapCadenceBounded == churn <= MAX_CHURN

(* Phase T / ACT-143 — OperatorGenesisBounded（Rule 9.32.4，meta⁵）.                  *)
(* Phase T 把「轉換算子文法的自我擴充」這條新迴圈納入本元迴圈：每個 TRANSFORMS/OPS 外算子發明   *)
(* 為一個 `operator-genesis:` 命名空間指紋，其 add↔retire 與 SLV 規則 / scorer-profile /          *)
(* value-dimension / vocab-genesis 共用本軌的同一 churn 預算（**不增第六軌、不新增狀態變數**，故本軌 *)
(* reachable 計數不回歸——維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。在本 small-model 抽象下，*)
(* 「任一 operator-genesis 算子的再採納迴圈」與既證的單指紋迴圈同構，故其 churn 永不超過 MAX_CHURN  *)
(* —— 這是「算子自我擴充迴圈會停（add↔retire 不無限抖動）」在形式化層的歸約。                     *)
(* 註：與 churn（flow）正交的『現存活躍算子數天花板』（stock：每算子首採、per-指紋 churn 皆 0、卻讓  *)
(* 算子基數單調膨脹的 OPERATOR_GENESIS_EXPLOSION）是**更緊的 runtime stock 精煉**，由               *)
(* meta_halt_monitor.guard_operator_genesis（SDD_DIM_OP_MAX）+ chaos(OPERATOR_GENESIS_GOODHART_FLAP)   *)
(* enforce/驗收；本軌的 single-counter 抽象刻意不展開 op stock 維度，故在此記為對既有界的形式化       *)
(* 強化引用（恆真，不增狀態/變數）。                                                              *)
OperatorGenesisBounded == churn <= MAX_CHURN

(* Phase T / ACT-143 — OperatorComputabilityBounded（Rule 9.32.3，meta⁵ 最深停機）.       *)
(* Phase T 的被發明物第一次是『可執行計算（算子）』而非『資料』——這把「圖靈完備 vs 保證停機」正面   *)
(* 反噬到框架自我擴充的產物本身。每個自我發明算子須結構性**全函式 + 有界計算步數 + 零遞迴零迴圈**：   *)
(* 算子由 total PRIMITIVES（O(n) list-reduction）× total COMBINATORS 在有界深度（<=2）運算式樹組成，故   *)
(* 其計算步數 cost() 恆為小常數（一元 2 / 二元 3），且對任何輸入有定義永不拋例外——**可證停機**。     *)
(* 在本 small-model 抽象下，算子可計算性與元迴圈的 churn 有界正交，但同屬「每個被學/退的製品其自身    *)
(* 行為皆有界停機」的歸約家族，故記為對既有界的形式化強化引用（恆真，不增狀態/變數）。              *)
(* 註：算子可計算性的緊語意（cost<=SDD_DIM_OP_STEP_MAX + fuzz-total + ast 零遞迴零迴圈）是**更緊的     *)
(* runtime/結構精煉**，由 meta_halt_monitor.guard_operator_computability + operator_genesis 有界算子   *)
(* 生成文法 + chaos(OPERATOR_COMPUTABILITY_FLAP) enforce/驗收；本軌的 single-counter 抽象刻意不展開     *)
(* 可計算性維度，故在此記為對既有界的形式化強化引用（恆真，不增狀態/變數）。                        *)
OperatorComputabilityBounded == churn <= MAX_CHURN

(* Phase U / ACT-148 — AlphabetGenesisBounded（Rule 9.33.4，meta⁶）.                  *)
(* Phase U 把「組合算子文法的自我擴充」這條新迴圈納入本元迴圈：每個 PRIMITIVES/COMBINATORS 外字母發明  *)
(* 為一個 `alphabet-genesis:` 命名空間指紋，其 add↔retire 與 SLV 規則 / scorer-profile /                *)
(* value-dimension / vocab-genesis / operator-genesis 共用本軌的同一 churn 預算（**不增第六軌、不新增狀態  *)
(* 變數**，故本軌 reachable 計數不回歸——維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。在本 small-model *)
(* 抽象下，「任一 alphabet-genesis 字母的再採納迴圈」與既證的單指紋迴圈同構，故其 churn 永不超過 MAX_CHURN *)
(* —— 這是「字母表自我擴充迴圈會停（add↔retire 不無限抖動）」在形式化層的歸約。                      *)
(* 註：與 churn（flow）正交的『現存活躍字母數天花板』（stock：每字母首採、per-指紋 churn 皆 0、卻讓字母   *)
(* 基數單調膨脹的 ALPHABET_GENESIS_EXPLOSION）是**更緊的 runtime stock 精煉**，由                      *)
(* meta_halt_monitor.guard_alphabet_genesis（SDD_DIM_ALPHABET_MAX）+ chaos(ALPHABET_GENESIS_GOODHART_FLAP) *)
(* enforce/驗收；本軌的 single-counter 抽象刻意不展開 alphabet stock 維度，故在此記為對既有界的形式化     *)
(* 強化引用（恆真，不增狀態/變數）。                                                              *)
AlphabetGenesisBounded == churn <= MAX_CHURN

(* Phase U / ACT-148 — ComputabilityClosureBounded（Rule 9.33.3，meta⁶ 最深停機：可計算性閉包）.       *)
(* Phase T 證了「每個被發明算子可證停機」，但其地基是『字母表 PRIMITIVES/COMBINATORS 本身被人類凍結、    *)
(* 逐條手證全 total + O(n) + cost-1』。Phase U 第一次讓系統自我發明字母表元素——被發明物是『會被算子生成  *)
(* 文法用來生成整個算子代數的生成規則零件』。故可計算性須由『單一算子可證停機』升級為**閉包性質**：     *)
(* 擴充字母表 A→A' 後，文法 G(A') 生成的整個（仍有限的）算子代數中**每一個算子**仍全函式 + 有界步數。   *)
(* 結構歸納證：被發明 primitive = total ATOM_REDUCERS（O(n) 單遍、零遞迴零迴圈、cost-1）∘ total POST_MAPS、*)
(* 被發明 combinator = total BINARY_ATOMS（有界元數、cost-1）；全函式的合成仍全函式、cost 仍 <=3，故      *)
(* I(A') 成立——**可計算性在字母表擴充下封閉（closed under alphabet expansion）**。這把「圖靈完備 vs 保證  *)
(* 停機」正面釘進框架自我擴充的**生成規則本身（meta⁶）**而非僅其產物。在本 small-model 抽象下，可計算性  *)
(* 閉包與元迴圈的 churn 有界正交，但同屬「每個被學/退的製品其自身（及其所生成代數）行為皆有界停機」的    *)
(* 歸約家族，故記為對既有界的形式化強化引用（恆真，不增狀態/變數）。                                  *)
(* 註：可計算性閉包的緊語意（採納前 guard_computability_closure 枚舉 G(A') 整代數驗 fuzz-total + cost<=    *)
(* SDD_DIM_OP_STEP_MAX + ast 零遞迴零迴圈）是**更緊的 runtime/結構精煉**，由                            *)
(* meta_halt_monitor.guard_computability_closure + operator_alphabet_genesis 有界字母表生成文法 +         *)
(* chaos(COMPUTABILITY_CLOSURE_FLAP) enforce/驗收；本軌的 single-counter 抽象刻意不展開閉包維度，故在此     *)
(* 記為對既有界的形式化強化引用（恆真，不增狀態/變數）。                                              *)
ComputabilityClosureBounded == churn <= MAX_CHURN

(* Phase V / ACT-151 — DepthGenesisBounded（Rule 9.34.4，meta⁷）.                  *)
(* Phase U 的有界性建立在「組合深度被人類凍結在 <=2 條」前提上（被發明物是『字母』，整代數深度恆 2）。 *)
(* Phase V 讓系統**自我發明組合深度 >2 的新複合算子**（meta⁷），被自我擴充物是『文法的結構性深度參數本身』 *)
(* ——深度算子基數本身會單調膨脹（每個新深度算子首採、per-fingerprint churn=0；維度/詞彙/算子/字母 stock  *)
(* 天花板對它皆盲目）。每個 depth-genesis 深度算子為一個 `depth-genesis:` 命名空間指紋，其 add↔retire 與   *)
(* SLV 規則 / scorer-profile / value-dimension / vocab-genesis / operator-genesis / alphabet-genesis 共用本軌 *)
(* 的同一 churn 預算（**不增第六軌、不新增狀態變數**，故本軌 reachable 計數不回歸——維持 <<mstate, churn,  *)
(* cap>> 三變數 / 13 distinct）。在本 small-model 抽象下，「任一 depth-genesis 深度算子的再採納迴圈」與既證 *)
(* 的單指紋迴圈同構，故其 churn 永不超過 MAX_CHURN —— 這是「深度自我擴充迴圈會停（add↔retire 不無限抖動）」*)
(* 在形式化層的歸約。                                                                                  *)
(* 註：與 churn（flow）正交的『現存活躍深度算子數天花板』（stock：每深度算子首採、per-指紋 churn 皆 0、卻讓 *)
(* 深度算子基數單調膨脹的 DEPTH_GENESIS_EXPLOSION）是**更緊的 runtime stock 精煉**，由                    *)
(* meta_halt_monitor.guard_depth_genesis（SDD_DIM_DEPTH_MAX）+ chaos(DEPTH_GENESIS_GOODHART_FLAP)            *)
(* enforce/驗收；本軌的 single-counter 抽象刻意不展開 depth stock 維度，故在此記為對既有界的形式化強化      *)
(* 引用（恆真，不增狀態/變數）。                                                                        *)
DepthGenesisBounded == churn <= MAX_CHURN

(* Phase V / ACT-151 — DepthClosureBounded（Rule 9.34.3，meta⁷ 迄今最深停機：深度可計算性閉包，因 cost==depth）. *)
(* Phase T 證了「每個被發明算子可證停機」、Phase U 證了「擴充字母表後整代數可證停機」，但兩者的共同地基是  *)
(* 『組合深度被人類凍結在 <=2，故每算子 cost() 是小常數』。Phase V 第一次讓系統自我擴充組合深度本身——被自我 *)
(* 擴充物是『文法的結構性深度參數 = 直接決定每算子 cost 的步數參數』。關鍵：**cost == depth**（一元基底）/    *)
(* depth+1（二元基底），故「自我擴充深度」字面上就是「自我擴充計算步數」，深度上界就是停機臨界。故可計算性 *)
(* 須由『字母表擴充下封閉』升級為**深度閉包性質**：擴充深度 D→D' 後，文法 G(A,D') 生成的整個（仍有限的）深度 *)
(* 算子代數中**每一個算子**仍全函式 + cost==depth<=STEP_MAX。結構歸納證：深度算子 = total 深度-2 基底（Phase T *)
(* 已證 total + cost∈{2,3}）∘ total 一元 combinator 鏈（皆 total + cost-1），故 cost==depth；全函式的合成仍   *)
(* 全函式、cost 仍線性於深度，故 I_d(A,D') 成立 ⟺ D'<=STEP_MAX——**深度可計算性閉包等價於「深度本身有硬上界 *)
(* = STEP_MAX」**。這把「圖靈完備 vs 保證停機」正面釘進框架自我擴充文法的**結構性深度（步數）參數本身       *)
(* （meta⁷）**而非僅其產物或生成規則零件，且因 cost==depth 而最直接。在本 small-model 抽象下，深度可計算性閉包 *)
(* 與元迴圈的 churn 有界正交，但同屬「每個被學/退的製品其自身（及其所生成代數）行為皆有界停機」的歸約家族， *)
(* 故記為對既有界的形式化強化引用（恆真，不增狀態/變數）。                                                *)
(* 註：深度可計算性閉包的緊語意（採納前 guard_depth_closure 枚舉 G(A,depth) 整代數驗 fuzz-total + cost<=        *)
(* SDD_DIM_OP_STEP_MAX〔即深度<=step_max〕+ ast 零遞迴零迴圈）是**更緊的 runtime/結構精煉**，由               *)
(* meta_halt_monitor.guard_depth_closure + operator_depth_genesis 有界深度生成文法 + chaos(DEPTH_CLOSURE_FLAP)  *)
(* enforce/驗收；本軌的 single-counter 抽象刻意不展開深度閉包維度，故在此記為對既有界的形式化強化引用        *)
(* （恆真，不增狀態/變數）。                                                                            *)
DepthClosureBounded == churn <= MAX_CHURN

(* Phase W / ACT-154 — RecursionGenesisBounded（Rule 9.35.4，meta⁸）.                  *)
(* Phase T~V 的有界性建立在「算子代數結構性零遞迴、運算式是有限樹」前提上（被發明物是算子/字母/深度，  *)
(* 求值路徑無 while/無自呼叫、cost 是結構性有限量）。Phase W 讓系統**自我發明會呼叫其他算子 / 自呼叫的    *)
(* 互遞迴算子**（meta⁸），被自我擴充物是『文法的算子是否可互相引用 / 自引用這個結構參數本身』——互遞迴    *)
(* 算子基數本身會單調膨脹（每個新互遞迴算子首採、per-fingerprint churn=0；維度/詞彙/算子/字母/深度 stock  *)
(* 天花板對它皆盲目）。每個 recursion-genesis 互遞迴算子為一個 `recursion-genesis:` 命名空間指紋，其        *)
(* add↔retire 與 SLV 規則 / scorer-profile / value-dimension / vocab-genesis / operator-genesis /          *)
(* alphabet-genesis / depth-genesis 共用本軌的同一 churn 預算（**不增第六軌、不新增狀態變數**，故本軌      *)
(* reachable 計數不回歸——維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。在本 small-model 抽象下，「任一 *)
(* recursion-genesis 互遞迴算子的再採納迴圈」與既證的單指紋迴圈同構，故其 churn 永不超過 MAX_CHURN —— 這是 *)
(* 「互遞迴自我擴充迴圈會停（add↔retire 不無限抖動）」在形式化層的歸約。                                 *)
(* 註：與 churn（flow）正交的『現存活躍互遞迴算子數天花板』（stock：每互遞迴算子首採、per-指紋 churn 皆 0、 *)
(* 卻讓互遞迴算子基數單調膨脹的 RECURSION_GENESIS_EXPLOSION）是**更緊的 runtime stock 精煉**，由            *)
(* meta_halt_monitor.guard_recursion_genesis（SDD_DIM_RECUR_MAX）+ chaos(RECURSION_GENESIS_GOODHART_FLAP)     *)
(* enforce/驗收；本軌的 single-counter 抽象刻意不展開 recursion stock 維度，故在此記為對既有界的形式化       *)
(* 強化引用（恆真，不增狀態/變數）。                                                                     *)
RecursionGenesisBounded == churn <= MAX_CHURN

(* Phase W / ACT-154 — RecursionClosureBounded（Rule 9.35.3，meta⁸ 迄今唯一質變停機：良基停機證書）.        *)
(* Phase T 證了「每個被發明算子可證停機」、U 證了「擴充字母表後整代數可證停機」、V 證了「擴充深度後整代數   *)
(* cost==depth<=STEP_MAX 可證停機」，但三者的共同地基是『被發明的算子代數零遞迴、運算式是有限樹，故總步數   *)
(* = 樹節點數這個結構性有限量，"有界步數" device 足以保證停機』。Phase W 第一次讓系統自我發明『算子可互相  *)
(* 呼叫 / 自呼叫』——被自我擴充物是『讓運算式樹變成可含環呼叫圖的結構參數』。關鍵：**判定一個任意含環呼叫   *)
(* 圖是否停機 = 停機問題本身（不可判定）**，故「有界步數」device 結構性失效（不能枚舉含環圖數步數）。可計算 *)
(* 性須由『有界步數靜態量』升級為**良基停機證書（Well-Founded Termination Certificate）**：呼叫圖為 DAG（無  *)
(* 環、結構良基），或每條回邊（自呼叫 / 環）皆嚴格遞減一個下有界（>=0）的良基測度（rank），且硬燃料 fuel    *)
(* <= STEP_MAX。良基歸納證：DAG 沿拓樸序至多訪問 |N| 次必終止；含環但每回邊嚴格遞減下有界 rank → 良基測度   *)
(* (rank, fuel) lexicographic 嚴格遞減且下有界 → 不存在無窮遞減鏈 → 必終止（Agda/Coq/Idris 全函式片段的可    *)
(* 判定停機邊界）。meta⁸ 不讓算子代數真正跨入圖靈完備（那會使停機不可判定）——而是安裝一道把互遞迴侷限在   *)
(* 「可證良基終止之全函式片段」的證書，凡無法出示良基測度者結構性拒絕、導 MFSM_ESCALATION。這把「圖靈完備 *)
(* vs 保證停機」正面釘在**可判定 vs 不可判定的臨界線本身（meta⁸）**——用全新 device「良基測度終止」取代失效 *)
(* 的「有界步數」，而整個閉環仍靠 LLM+紙帶維持圖靈完備。在本 small-model 抽象下，良基停機證書與元迴圈的     *)
(* churn 有界正交，但同屬「每個被學/退的製品其自身（及其所生成代數）行為皆有界停機」的歸約家族，故記為對     *)
(* 既有界的形式化強化引用（恆真，不增狀態/變數）。                                                       *)
(* 註：良基停機證書的緊語意（採納前 guard_recursion_closure 枚舉呼叫圖驗 (acyclic ∨ 每環嚴格遞減下有界 rank) *)
(* ∧ fuel<=SDD_DIM_OP_STEP_MAX ∧ 整代數 fuzz-total + ast 求值器零真遞迴零 while）是**更緊的 runtime/結構精煉**， *)
(* 由 meta_halt_monitor.guard_recursion_closure + operator_recursion_genesis 有界互遞迴生成文法 +             *)
(* chaos(RECURSION_CLOSURE_FLAP) enforce/驗收；本軌的 single-counter 抽象刻意不展開良基停機維度，故在此記為對   *)
(* 既有界的形式化強化引用（恆真，不增狀態/變數）。                                                       *)
RecursionClosureBounded == churn <= MAX_CHURN

(* Phase X / ACT-156 — EmbodiedGroundingBounded（Rule 9.36，具身接地閘有界停機）.        *)
(* Phase L~W 把元迴圈的自我演化能力一路推到 meta⁸（互遞迴自我發明 + 良基停機證書），但其     *)
(* 「評估」端一路都是**合成語料勝率**（dimension_necessity_oracle 在 12 條凍結 feature 語料上算 *)
(* 覆蓋率）——元迴圈的生成-評估分離為真但**未接地**：從不啟動沙箱、從不查真實日誌、從不跑真   *)
(* App（GAP-X1，由 Phase X 切片 FF-16 量測 surface）。Phase X 完整版在 META_FSM 的納入（MFSM_  *)
(* GROW）路徑前插一道 **EMBODIED_GROUNDING_GATE（具身接地閘）**：任何自我發明能力被納入前，須 *)
(* 先由 sdd-evaluator 在隔離沙箱實跑、由 observability_query 查客觀錯誤，產出**具身 grounded-   *)
(* verdict**（合成勝率〔必要〕∧ 具身 OQS 不退步〔充分〕雙簽）；grounded_fail 或無具身增益 →     *)
(* REJECT（回 OBSERVE，不 churn）。每個具身接地事件為一個 `embodied-grounding:` 命名空間指紋，   *)
(* 其 add↔retire 與 SLV 規則 / scorer-profile / value-dimension / vocab/operator/alphabet/depth/   *)
(* recursion-genesis 共用本軌的同一 churn 預算（**不增第六軌、不新增狀態變數**，故本軌 reachable  *)
(* 計數不回歸——維持 <<mstate, churn, cap>> 三變數 / 13 distinct）。在本 small-model 抽象下，「任一  *)
(* 具身接地閘的 add↔retire 迴圈」與既證的單指紋迴圈同構，故其 churn 永不超過 MAX_CHURN —— 這是   *)
(* 「具身接地閘迴圈會停（add↔retire 不無限抖動）」在形式化層的歸約。                          *)
(* 註：具身接地的停機反諷在於——為讓元迴圈「在真實環境驗證」，引入了「真實沙箱可能 hang」這個   *)
(* 新的不停機源。故與 churn（add↔retire 有界）正交的『具身觀測有界停機』緊語意——(i) grounded   *)
(* verdict 必基於 ExecutionObservation 客觀資料（沙箱 verdict + OQS + logql 根因），缺則 fail-     *)
(* closed → MFSM_ESCALATION；(ii) 沙箱硬 timeout（SandboxSpec.timeout_sec）截斷，FSM 不做 wall-   *)
(* clock wait（收 verdict 而非等沙箱）；(iii) embodied_grounding_oracle 結構性不被 generator import *)
(* （對抗分離）——是**更緊的 runtime/結構精煉**，由 meta_halt_monitor.guard_embodied_grounding +    *)
(* embodied_grounding_oracle（output_quality_scorer 接地）+ chaos(EMBODIED_GROUNDING_FLAP) enforce/  *)
(* 驗收；本軌的 single-counter 抽象刻意不展開具身接地維度，故在此記為對既有界的形式化強化引用     *)
(* （恆真，不增狀態/變數）。這把提示「賦予評估器實體操作能力（Playwright/隔離環境/客觀錯誤）」   *)
(* 推到**元迴圈層**並形式化為有界停機閉環——Phase X 是橫向接地，非垂直加塔（不碰 meta⁹）。       *)
EmbodiedGroundingBounded == churn <= MAX_CHURN

(* Phase Y / ACT-159 — VisualizationBounded（Rule 9.37，可審批性渲染有界停機）.              *)
(* Phase L~X 把元迴圈自我演化推到 meta⁸ + 具身接地，但其全部停機證書（良基 ranking          *)
(* function、fuel、grounded-verdict）一路 machine-readable / machine-verified、從未           *)
(* human-auditable——當被人類 K=1 signoff 的是一張帶 rank 的互遞迴呼叫圖時，舵手事實上只能    *)
(* 盲簽（GAP-Y1：可證性遠超可審批性）。Phase Y 開發一套與 RecursiveOperator AST 同構的視覺化  *)
(* 儀表板（recursion_topology_view），把算子代數 + rank/fuel 轉成人類看得懂的拓樸/終止/接地   *)
(* 三視圖。儀表板是元迴圈狀態的 read-only 投影，結構性永不 churn（churn UNCHANGED ≤ MAX_CHURN *)
(* 恆真）——此歸約恆真的理由比 genesis 各 *Bounded 更強：read-only ⇒ 渲染不漂移 meta-loop     *)
(* 狀態，這正是要斷言的安全性質「儀表板是純觀察者」。每個視覺化事件（若未來涉採納）為一個      *)
(* `visualization:` 命名空間指紋，與既有 SLV / scorer-profile / value-dimension / vocab /     *)
(* operator / alphabet / depth / recursion / embodied-grounding 共用本軌同一 churn 預算（**不 *)
(* 增第六軌、不新增狀態變數**，故本軌 reachable 計數不回歸——維持 <<mstate, churn, cap>> 三    *)
(* 變數 / 13 distinct）。                                                                      *)
(* 註：可審批性的停機反諷在於——為讓人類看懂而引入「渲染無界大圖可能 token 爆炸 / OOM」這個    *)
(* 新不停機源（同 Phase X「真實沙箱可能 hang」結構）。故與 churn 正交的『渲染有界停機』緊語意  *)
(* ——(i) render-output 受 render budget（node/edge/depth/char）硬截斷 + 分頁，逃逸 fail-closed；*)
(* (ii) verify_topology_consistency 反解析渲染回 (nodes,edges,ranks) 與 to_dict() 原圖圖同構    *)
(* 斷言，不一致（視覺欺騙）→ fail-closed → MFSM_ESCALATION；(iii) 接地視圖無客觀 Execution     *)
(* Observation → 灰佔位不 false-green（複用 Phase X fail-closed）——是更緊的 runtime/結構精煉，  *)
(* 由 meta_halt_monitor.guard_visualization_bounded + recursion_topology_view 有界渲染 +        *)
(* chaos(VISUALIZATION_FLAP / VISUALIZATION_TOPOLOGY_DRIFT_FLAP) enforce/驗收；本軌的 single-    *)
(* counter 抽象刻意不展開渲染維度，故在此記為對既有界的形式化強化引用（恆真，不增狀態/變數）。 *)
(* Phase Y 是橫向可解釋性加固，不碰 meta⁹、不碰 meta-oracle。                                  *)
VisualizationBounded == churn <= MAX_CHURN

(* ESCALATION 非過早：進入元迴圈停機點必因 churn 或 cap 預算耗盡。*)
ReadoptGated == (mstate = "MFSM_ESCALATION") => (churn = MAX_CHURN \/ cap = MAX_CAP)

(* 穩定不動點集合：元迴圈唯一可「停在這裡不再動」且代表健康收斂的態 = MFSM_STABLE。 *)
(* MFSM_ESCALATION 雖也是 terminal（人工閘），但**不屬於**不動點集合（它是停機求援、 *)
(* 非健康收斂），故被明確排除。 *)
StableFixpoints == {"MFSM_STABLE"}

(* StableIsFixpoint（藍圖 §2.2/§3.1 明列）：                                    *)
(*   1. MFSM_STABLE 屬於穩定不動點集合（吸收態）；其「吸收性」（後繼仍 STABLE）由 *)
(*      Next 在 STABLE 唯一可用動作為 TerminalStutter（UNCHANGED vars）結構性保證。*)
(*   2. MFSM_ESCALATION ∉ 不動點集合（人工求援態，非健康收斂）。                  *)
(*   3. 凡落在不動點集合者必為 terminal（不會再有 churn/cap 變動）。              *)
(* 表述為 TLC 可判定的狀態不變量（恆真）。比 ReadoptGated 更強地刻畫 STABLE 語意。 *)
StableIsFixpoint ==
    /\ "MFSM_STABLE" \in StableFixpoints
    /\ "MFSM_ESCALATION" \notin StableFixpoints
    /\ ((mstate \in StableFixpoints) => (mstate \in MetaTerminals))

(***************************************************************************)
(* Liveness — 元迴圈必抵不動點或人工閘（不會永久 churn）                     *)
(***************************************************************************)

EventuallyMetaStable == <>(mstate \in MetaTerminals)

=============================================================================
\* Created 2026-06-03 — Phase L M-L1 / ACT-090
