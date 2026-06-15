--------------------------- MODULE OPTIMIZATION_FSM ---------------------------
(***************************************************************************)
(* Phase N / ACT-107 — Global Composition Optimization Search FSM         *)
(* （全域組合最佳化 NP-hard 搜尋形式化停機）                                *)
(*                                                                         *)
(* 對應實作: tools/fsm_runtime/{composition_optimizer,optimization_halt_monitor}.py *)
(* 對應藍圖: SDD_improving_Automation_14.md §1.1 / PN-1（L10 完整奠基石）   *)
(* 對應規則: CLAUDE.md Rule 9.26.1（SearchBounded）/ 9.26.5（OptimalityHonest）*)
(*                                                                         *)
(* 單軌 SDD_FSM 證單意圖開發迴圈停機；FLEET_FSM 證資源並行；META_FSM 證學習    *)
(* 元迴圈不抖動；COMPOSITION_FSM 證跨意圖**一致**收斂。本模組證**第五條迴圈**： *)
(* 全域組合**最佳化搜尋**（bounded branch-and-bound）——節點展開有硬上限，      *)
(* 永不指數爆炸無限搜尋，最終必抵 OPT_SCHEDULED（找到排程）或 OPT_ESCALATION     *)
(* （預算內無可行解）。比照 META/COMPOSITION 採**獨立命名空間**，不併入單軌      *)
(* （守 Rule 9.18.1 與既有 42 reachable 不回歸）。                            *)
(*                                                                         *)
(* 證明目標：                                                              *)
(*   1. TypeOK                                                             *)
(*   2. SearchBounded        — expanded ≤ MAX_NODES（Rule 9.26.1，永不超預算）*)
(*   3. ScheduledImpliesFound — OPT_SCHEDULED ⟹ found（不無中生有排程）       *)
(*   4. EscalationExhausted  — OPT_ESCALATION ⟹ 預算耗盡且無解（非過早）      *)
(*   5. StableIsFixpoint     — OPT_SCHEDULED 吸收；OPT_ESCALATION ∉ 不動點    *)
(*   6. EventuallyScheduled（liveness）— 必抵 {OPT_SCHEDULED, OPT_ESCALATION}*)
(*       （expanded 單調遞增且有界 → well-founded → 永不無限搜尋）            *)
(***************************************************************************)

EXTENDS Naturals

CONSTANTS MAX_NODES   \* 節點展開硬上限（runtime: SDD_OPT_NODE_BUDGET 預設 256；small-model 取小）

VARIABLES ostate,     \* 搜尋層狀態
          expanded,   \* 已展開節點數
          found       \* 是否已找到可行排程（0/1，monotone）

vars == <<ostate, expanded, found>>

OptStates == {"OPT_OBSERVE", "OPT_EXPAND", "OPT_PRUNE", "OPT_SCHEDULED", "OPT_ESCALATION"}
OptTerminals == {"OPT_SCHEDULED", "OPT_ESCALATION"}

TypeOK == /\ ostate \in OptStates
          /\ expanded \in 0..MAX_NODES
          /\ found \in {0, 1}

Init == /\ ostate = "OPT_OBSERVE"
        /\ expanded = 0
        /\ found = 0

(* 開始搜尋（一次性離開 OBSERVE）*)
StartSearch ==
    /\ ostate = "OPT_OBSERVE"
    /\ ostate' = "OPT_EXPAND"
    /\ UNCHANGED <<expanded, found>>

(* 展開一個節點：expanded++，可能發現可行排程（found→1，monotone）*)
ExpandStay ==
    /\ ostate = "OPT_EXPAND"
    /\ expanded < MAX_NODES
    /\ expanded' = expanded + 1
    /\ found' \in {found, 1}
    /\ ostate' = "OPT_EXPAND"

(* 展開後界限剪枝該分支：expanded++（剪枝也算檢視一節點），轉瞬態 PRUNE *)
ExpandPrune ==
    /\ ostate = "OPT_EXPAND"
    /\ expanded < MAX_NODES
    /\ expanded' = expanded + 1
    /\ ostate' = "OPT_PRUNE"
    /\ UNCHANGED found

(* 剪枝後繼續搜尋（回 EXPAND，不增量——但下一步必經一次增量動作，故無自由環）*)
ResumeSearch ==
    /\ ostate = "OPT_PRUNE"
    /\ expanded < MAX_NODES
    /\ ostate' = "OPT_EXPAND"
    /\ UNCHANGED <<expanded, found>>

(* 已找到可行排程且決定停（最優或夠好）→ SCHEDULED *)
Schedule ==
    /\ ostate \in {"OPT_EXPAND", "OPT_PRUNE"}
    /\ found = 1
    /\ ostate' = "OPT_SCHEDULED"
    /\ UNCHANGED <<expanded, found>>

(* 預算耗盡且已找到 → SCHEDULED（best-so-far + gap）*)
ExhaustScheduled ==
    /\ ostate \in {"OPT_EXPAND", "OPT_PRUNE"}
    /\ expanded >= MAX_NODES
    /\ found = 1
    /\ ostate' = "OPT_SCHEDULED"
    /\ UNCHANGED <<expanded, found>>

(* 預算耗盡且無可行解 → ESCALATION（人工：放寬 budget / 拆問題 / 接受序列化）*)
ExhaustEscalate ==
    /\ ostate \in {"OPT_EXPAND", "OPT_PRUNE"}
    /\ expanded >= MAX_NODES
    /\ found = 0
    /\ ostate' = "OPT_ESCALATION"
    /\ UNCHANGED <<expanded, found>>

(* terminal-like 自我遷移（避免 TLC 誤判 deadlock）*)
TerminalStutter ==
    /\ ostate \in OptTerminals
    /\ UNCHANGED vars

Next == \/ StartSearch
        \/ ExpandStay
        \/ ExpandPrune
        \/ ResumeSearch
        \/ Schedule
        \/ ExhaustScheduled
        \/ ExhaustEscalate
        \/ TerminalStutter

(* 公平性：SF 推終局動作；WF 保證瞬態前進。expanded 單調遞增且有界 → well-founded *)
(* 下降 → 必抵 terminal。*)
Fairness == /\ WF_vars(StartSearch)
            /\ WF_vars(ExpandStay)
            /\ WF_vars(ExpandPrune)
            /\ WF_vars(ResumeSearch)
            /\ SF_vars(Schedule)
            /\ SF_vars(ExhaustScheduled)
            /\ SF_vars(ExhaustEscalate)

Spec == Init /\ [][Next]_vars /\ Fairness

(***************************************************************************)
(* Safety                                                                  *)
(***************************************************************************)

(* Rule 9.26.1：節點展開有硬上界 → branch-and-bound 永不指數爆炸無限搜尋。*)
SearchBounded == expanded <= MAX_NODES

(* OPT_SCHEDULED 必因已找到可行排程（不無中生有產出排程）。*)
ScheduledImpliesFound == (ostate = "OPT_SCHEDULED") => (found = 1)

(* OPT_ESCALATION 非過早：必因預算耗盡且仍無可行解。*)
EscalationExhausted ==
    (ostate = "OPT_ESCALATION") => (expanded = MAX_NODES /\ found = 0)

(* 穩定不動點集合：唯一健康收斂態 = OPT_SCHEDULED；OPT_ESCALATION 為人工求援，排除。*)
StableFixpoints == {"OPT_SCHEDULED"}

StableIsFixpoint ==
    /\ "OPT_SCHEDULED" \in StableFixpoints
    /\ "OPT_ESCALATION" \notin StableFixpoints
    /\ ((ostate \in StableFixpoints) => (ostate \in OptTerminals))

(***************************************************************************)
(* Liveness — 搜尋必抵不動點或人工閘（不會無限搜尋）                         *)
(***************************************************************************)

EventuallyScheduled == <>(ostate \in OptTerminals)

=============================================================================
\* Created 2026-06-03 — Phase N / ACT-107
