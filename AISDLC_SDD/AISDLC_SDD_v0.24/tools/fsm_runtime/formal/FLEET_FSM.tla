--------------------------- MODULE FLEET_FSM ---------------------------
(***************************************************************************)
(* Phase I M5 / ACT-072 — Parametric Fleet FSM（艦隊並行形式化）           *)
(*                                                                         *)
(* 對應實作: tools/fsm_runtime/fleet_orchestrator.py                       *)
(* 對應藍圖: SDD_improving_Automation_09.md §5.4 / PI-1                    *)
(*                                                                         *)
(* 單軌 FSM（SDD_FSM.tla）以 scalar state 描述「一個 feature」；本模組以    *)
(* state[Feature] 參數化，描述「N feature 並行」+ 共享 spec 區段鎖的協調層。 *)
(*                                                                         *)
(* 證明目標：                                                              *)
(*   1. LockMutex     — 任一共享鎖至多被一個 feature 持有（互斥）          *)
(*   2. NoCircularWait— 全域鎖序（atomic all-or-nothing acquire）→ 無循環   *)
(*                      等待 → 結構性無死鎖（Coffman circular-wait 被破壞） *)
(*   3. TypeOK                                                             *)
(*   4. AllEventuallyDone — 加 fairness 後所有 feature 必達 done（bounded   *)
(*                          join，無 feature 永久卡住）                     *)
(*                                                                         *)
(* Symmetry：feature 可交換（Permutations(Features)）→ 大幅縮減狀態空間，    *)
(* 對應 Apalache symmetry reduction 的精神（本檔以 TLC + SYMMETRY 驗證；     *)
(* Apalache 可用時亦可 `apalache check` 做無界 parametric 驗證）。          *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Features,    \* 並行的 feature 集合（model：{"A","B"}）
          Locks        \* 共享 spec 區段鎖集合（model：{"L1"}）

VARIABLES pc,          \* Features -> per-track 階段
          owner        \* Locks -> Features \cup {"free"}

vars == <<pc, owner>>

(* per-track 階段：init → locked（atomically 取得所需鎖）→ merged → done *)
Stages == {"init", "locked", "merged", "done"}

(* 每個 feature 需要的鎖集合（model：皆需 L1，製造最強的競爭以驗互斥/無死鎖）*)
Needs(f) == Locks

(* Symmetry reduction：feature 可交換（cfg SYMMETRY 引用此命名運算子）*)
Symmetry == Permutations(Features)

TypeOK == /\ pc \in [Features -> Stages]
          /\ owner \in [Locks -> (Features \cup {"free"})]

Init == /\ pc = [f \in Features |-> "init"]
        /\ owner = [l \in Locks |-> "free"]

(* Atomic all-or-nothing acquire（對應 SpecDependencyLock.acquire_all）：       *)
(* 只有當所需鎖全部 free 時，一次全取得 → 不可能部分持有 → 無循環等待。       *)
Acquire(f) ==
    /\ pc[f] = "init"
    /\ \A l \in Needs(f) : owner[l] = "free"
    /\ owner' = [l \in Locks |-> IF l \in Needs(f) THEN f ELSE owner[l]]
    /\ pc' = [pc EXCEPT ![f] = "locked"]

Merge(f) ==
    /\ pc[f] = "locked"
    /\ pc' = [pc EXCEPT ![f] = "merged"]
    /\ UNCHANGED owner

(* 完成即釋放自己持有的鎖（讓其他 feature 前進 → bounded join）*)
Done(f) ==
    /\ pc[f] = "merged"
    /\ pc' = [pc EXCEPT ![f] = "done"]
    /\ owner' = [l \in Locks |-> IF owner[l] = f THEN "free" ELSE owner[l]]

Step(f) == Acquire(f) \/ Merge(f) \/ Done(f)

Next == \E f \in Features : Step(f)

(* 公平性：每個 feature 的前進步驟都有 weak fairness → 不被永久餓死。        *)
Fairness == \A f \in Features : WF_vars(Step(f))

Spec == Init /\ [][Next]_vars /\ Fairness

(***************************************************************************)
(* Safety                                                                  *)
(***************************************************************************)

(* 互斥：同一鎖不可同時被兩個 feature 持有（owner 是函式，天然單值；此處      *)
(* 斷言「持有者若非 free 必為某 feature」並無雙持有）*)
LockMutex ==
    \A l \in Locks : owner[l] \in (Features \cup {"free"})

(* 無循環等待：因 Acquire 為 atomic all-or-nothing，任一 feature 要嘛 0 鎖     *)
(* （init）要嘛持有其完整 Needs（locked/merged）。不存在「持有部分、等待其餘」 *)
(* 的中間態 → 無循環等待 → 無死鎖。形式化為：locked/merged 的 feature 必持有   *)
(* 其所有 Needs。*)
NoPartialHold ==
    \A f \in Features :
        (pc[f] \in {"locked", "merged"}) => (\A l \in Needs(f) : owner[l] = f)

(***************************************************************************)
(* Liveness — bounded join（所有 feature 終達 done）                        *)
(***************************************************************************)

AllEventuallyDone == <>(\A f \in Features : pc[f] = "done")

=============================================================================
\* Created 2026-06-01 — Phase I M5 / ACT-072
