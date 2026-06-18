--------------------------- MODULE COMPOSITION_FSM ---------------------------
(***************************************************************************)
(* Phase M M-M1 / ACT-098 — Composition-Level Intent Autonomy FSM         *)
(* （跨意圖語義組合層形式化停機）                                          *)
(*                                                                         *)
(* 對應實作: tools/fsm_runtime/{intent_composer,composition_halt_monitor}.py*)
(* 對應藍圖: SDD_improving_Automation_13.md §1.2 / PM-1（L10 完整奠基石）   *)
(* 對應規則: CLAUDE.md Rule 9.25.1（RenegotiationBounded）/ 9.25.2          *)
(*           （CompositionConsistent）                                      *)
(*                                                                         *)
(* 單軌 SDD_FSM.tla 證「一個 feature 的開發迴圈」必達 terminal；FLEET_FSM.tla *)
(* 證「N feature 並行（資源鎖層）」無死鎖；META_FSM.tla 證「學習↔退役元迴圈」 *)
(* 不抖動。本模組證**第四條迴圈**：跨意圖**語義組合層**——兩意圖在共享 spec     *)
(* 節點上的「協商→否定→再協商」不會無限 livelock，最終必抵不動點 CPLAN_STABLE  *)
(* （全域一致可排程）或人工閘 CPLAN_ESCALATION（協商預算耗盡）。比照 META_FSM   *)
(* 採**獨立命名空間**，不併入單軌（守 Rule 9.18.1 與既有 42/42 reachable 不回歸）*)
(*                                                                         *)
(* 證明目標：                                                              *)
(*   1. TypeOK                                                             *)
(*   2. CompositionConsistent — 進入 COMMIT/STABLE 的組合，未解衝突 = 0      *)
(*                              （Rule 9.25.2：不帶矛盾規格提交）            *)
(*   3. RenegotiationBounded   — reneg ≤ MAX_RENEG（Rule 9.25.1，協商有界）  *)
(*   4. ConflictResolvedOrEscalated — 進 ESCALATION 必因協商預算耗盡         *)
(*                              （reneg = MAX_RENEG，非過早升級）            *)
(*   5. StableIsFixpoint  — CPLAN_STABLE 為吸收不動點；ESCALATION ∉ 不動點   *)
(*   6. EventuallyComposed（liveness）— 組合層最終必抵 {STABLE, ESCALATION}  *)
(*       （SF 推向 CommitClean/Settle/ConflictEscalate；對應 META_FSM 手法）  *)
(***************************************************************************)

EXTENDS Naturals

CONSTANTS MAX_RENEG,      \* 共享節點跨意圖再協商硬上限（runtime: SDD_COMPOSITION_RENEG_MAX 預設 2）
          MAX_CONFLICTS   \* 初始未解衝突數上界（small-model：結構等價於真實衝突集大小）

VARIABLES cstate,        \* 組合層狀態
          reneg,         \* 累計協商輪數（每進一次 NEGOTIATE +1）
          conflicts      \* 尚未解決的共享節點衝突數

vars == <<cstate, reneg, conflicts>>

CompStates == {"CPLAN_OBSERVE", "CPLAN_NEGOTIATE", "CPLAN_COMMIT",
               "CPLAN_STABLE", "CPLAN_ESCALATION"}
CompTerminals == {"CPLAN_STABLE", "CPLAN_ESCALATION"}

TypeOK == /\ cstate \in CompStates
          /\ reneg \in 0..MAX_RENEG
          /\ conflicts \in 0..MAX_CONFLICTS

Init == /\ cstate = "CPLAN_OBSERVE"
        /\ reneg = 0
        /\ conflicts \in 0..MAX_CONFLICTS   \* 非決定性初始衝突數，窮舉 clean / conflict 兩路

(* 無衝突 → 直接提交（全域一致）。conflicts 維持 0。*)
CommitClean ==
    /\ cstate = "CPLAN_OBSERVE"
    /\ conflicts = 0
    /\ cstate' = "CPLAN_COMMIT"
    /\ UNCHANGED <<reneg, conflicts>>

(* 有衝突且仍有協商預算 → 進協商（reneg++，守 reneg < MAX_RENEG → reneg' ≤ MAX_RENEG）。*)
Negotiate ==
    /\ cstate = "CPLAN_OBSERVE"
    /\ conflicts > 0
    /\ reneg < MAX_RENEG
    /\ reneg' = reneg + 1
    /\ cstate' = "CPLAN_NEGOTIATE"
    /\ UNCHANGED conflicts

(* 協商成功調和一個衝突 → 回 OBSERVE（conflicts--）。*)
NegotiateResolve ==
    /\ cstate = "CPLAN_NEGOTIATE"
    /\ conflicts > 0
    /\ conflicts' = conflicts - 1
    /\ cstate' = "CPLAN_OBSERVE"
    /\ UNCHANGED reneg

(* 協商未能調和（反覆否定）→ 回 OBSERVE，衝突不變（reneg 已於進 NEGOTIATE 時 +1）。*)
NegotiateStall ==
    /\ cstate = "CPLAN_NEGOTIATE"
    /\ cstate' = "CPLAN_OBSERVE"
    /\ UNCHANGED <<reneg, conflicts>>

(* 有衝突但協商預算耗盡 → 升級人工裁決（哪個意圖讓步 / 共享節點是否需統一上位規格）。*)
ConflictEscalate ==
    /\ cstate = "CPLAN_OBSERVE"
    /\ conflicts > 0
    /\ reneg >= MAX_RENEG
    /\ cstate' = "CPLAN_ESCALATION"
    /\ UNCHANGED <<reneg, conflicts>>

(* 提交後抵穩定不動點 *)
Settle ==
    /\ cstate = "CPLAN_COMMIT"
    /\ cstate' = "CPLAN_STABLE"
    /\ UNCHANGED <<reneg, conflicts>>

(* terminal-like 自我遷移（避免 TLC 誤判 deadlock；對應 META_FSM 的 TerminalStutter）*)
TerminalStutter ==
    /\ cstate \in CompTerminals
    /\ UNCHANGED vars

Next == \/ CommitClean
        \/ Negotiate
        \/ NegotiateResolve
        \/ NegotiateStall
        \/ ConflictEscalate
        \/ Settle
        \/ TerminalStutter

(* 公平性：SF 推 OBSERVE 的三條離開動作 + COMMIT→STABLE；WF 保證瞬態 NEGOTIATE 必離開。 *)
(* reneg 單調遞增且有界、conflicts 單調遞減 → well-founded 下降 → 必抵 terminal。       *)
Fairness == /\ SF_vars(CommitClean)
            /\ SF_vars(ConflictEscalate)
            /\ SF_vars(Settle)
            /\ WF_vars(Negotiate)
            /\ WF_vars(NegotiateResolve)
            /\ WF_vars(NegotiateStall)

Spec == Init /\ [][Next]_vars /\ Fairness

(***************************************************************************)
(* Safety                                                                  *)
(***************************************************************************)

(* Rule 9.25.1：協商輪數有硬上界 → 跨意圖協商不會無限 livelock。*)
RenegotiationBounded == reneg <= MAX_RENEG

(* Rule 9.25.2：進入 COMMIT/STABLE（提交組合排程）時，未解衝突必為 0 → 不可能帶著      *)
(* 互相矛盾的規格進入並行執行（FLEET_FSM 之前的橫向一致性保證）。*)
CompositionConsistent ==
    (cstate \in {"CPLAN_COMMIT", "CPLAN_STABLE"}) => (conflicts = 0)

(* ESCALATION 非過早：進入組合層停機點必因協商預算耗盡（reneg 觸頂）。*)
ConflictResolvedOrEscalated ==
    (cstate = "CPLAN_ESCALATION") => (reneg = MAX_RENEG)

(* 穩定不動點集合：組合層唯一可「停在這裡不再動」且代表健康收斂的態 = CPLAN_STABLE。  *)
(* CPLAN_ESCALATION 雖也是 terminal（人工閘），但**不屬於**不動點集合（停機求援，非     *)
(* 健康收斂），故被明確排除。*)
StableFixpoints == {"CPLAN_STABLE"}

(* StableIsFixpoint（藍圖 §1.2 明列）：                                          *)
(*   1. CPLAN_STABLE 屬穩定不動點集合（吸收態，後繼仍 STABLE 由 TerminalStutter 保證）*)
(*   2. CPLAN_ESCALATION ∉ 不動點集合（人工求援態，非健康收斂）                   *)
(*   3. 凡落在不動點集合者必為 terminal。*)
StableIsFixpoint ==
    /\ "CPLAN_STABLE" \in StableFixpoints
    /\ "CPLAN_ESCALATION" \notin StableFixpoints
    /\ ((cstate \in StableFixpoints) => (cstate \in CompTerminals))

(***************************************************************************)
(* Liveness — 組合層必抵不動點或人工閘（不會永久協商）                       *)
(***************************************************************************)

EventuallyComposed == <>(cstate \in CompTerminals)

=============================================================================
\* Created 2026-06-03 — Phase M M-M1 / ACT-098
