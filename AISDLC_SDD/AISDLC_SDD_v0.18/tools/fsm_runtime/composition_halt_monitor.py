"""Phase M M-M1 / ACT-098 — Composition-Halt Monitor（組合層有界停機 runtime 守門）.

對應藍圖：SDD_improving_Automation_13.md §1.2 / §3.1 ACT-098 / Rule 9.25.1~9.25.2。
形式化對應：formal/COMPOSITION_FSM.tla（獨立命名空間，reneg/conflicts 兩計數器）。

單軌 SDD_FSM.tla 證「一個 feature 的開發迴圈」必達 terminal；FLEET_FSM.tla 證「N feature
並行（資源鎖層）」無死鎖；META_FSM.tla 證「跨 session 學習↔退役元迴圈」不抖動。本模組
對應**第四條形式化迴圈**：跨意圖**語義組合層**——兩意圖在共享 spec 節點上的「協商→否定
→再協商」不會無限 livelock，最終必抵 CPLAN_STABLE（全域一致可排程）或 CPLAN_ESCALATION
（協商預算耗盡，人工裁決）。比照 META_FSM / FLEET_FSM 採**獨立命名空間**，不併入單軌
（守 Rule 9.18.1 三源一致性與既有 42/42 reachable 不回歸）。

核心守門 RenegotiationBounded（Rule 9.25.1）—— 任一共享節點指紋的跨意圖再協商輪數
≤ SDD_COMPOSITION_RENEG_MAX（clamp[1,5]，預設 2）。超限即拒絕，呼叫端導 CPLAN_ESCALATION
（破組合層 livelock）。advisory：監控只守邊界，**絕不自動 commit 排程、絕不自動改 spec**。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import intent_composer as _ic

# COMPOSITION_FSM 狀態宇宙（與 formal/COMPOSITION_FSM.tla 的 CompStates 同步；由
# tests/test_phase_m.py 的 test_composition_fsm_states_match_python 守雙源一致，
# 比照 META_FSM ↔ meta_halt_monitor 的 Rule 9.18.1 精神）。
COMPOSITION_STATES = frozenset({
    "CPLAN_OBSERVE", "CPLAN_NEGOTIATE", "CPLAN_COMMIT", "CPLAN_STABLE", "CPLAN_ESCALATION",
})
COMPOSITION_TERMINALS = frozenset({"CPLAN_STABLE", "CPLAN_ESCALATION"})

_DEFAULT_RENEG_MAX = 2
_RENEG_MAX_CLAMP = (1, 5)


class RenegotiationBoundExceeded(RuntimeError):
    """Rule 9.25.1：共享節點跨意圖協商輪數觸頂——禁止再協商，導 CPLAN_ESCALATION。"""


def reneg_max() -> int:
    """讀 SDD_COMPOSITION_RENEG_MAX（env 可調），clamp[1,5]，預設 2。"""
    raw = os.environ.get("SDD_COMPOSITION_RENEG_MAX")
    if not raw:
        return _DEFAULT_RENEG_MAX
    try:
        val = int(raw)
    except ValueError:
        return _DEFAULT_RENEG_MAX
    lo, hi = _RENEG_MAX_CLAMP
    return max(lo, min(hi, val))


@dataclass
class GuardResult:
    allowed: bool
    reneg: int
    reneg_max: int
    reason: str = ""


def guard_negotiate(node_id: str, *, ledger_path: Optional[Path] = None) -> GuardResult:
    """檢查一次「共享節點再協商」是否仍在預算內（不寫入 ledger，純判定）。

    reneg < reneg_max → 放行；reneg ≥ reneg_max → raise（呼叫端轉 CPLAN_ESCALATION）。
    """
    rmax = reneg_max()
    reneg = _ic.compute_reneg(node_id, ledger_path=ledger_path)
    if reneg >= rmax:
        raise RenegotiationBoundExceeded(
            f"共享節點 {node_id!r} 跨意圖協商輪數 reneg={reneg} ≥ "
            f"SDD_COMPOSITION_RENEG_MAX={rmax}：偵測組合層 livelock，禁止再協商，"
            f"導 CPLAN_ESCALATION（Rule 9.25.1）"
        )
    return GuardResult(allowed=True, reneg=reneg, reneg_max=rmax,
                       reason="協商預算未耗盡，放行")


def record_negotiate(node_id: str, *, intent_a: str = "", intent_b: str = "",
                     ledger_path: Optional[Path] = None) -> dict:
    """共享節點再協商的**唯一合法入口**：先過 guard_negotiate，再落帳。

    guard 拋出（RenegotiationBoundExceeded）時不落帳，呼叫端轉 CPLAN_ESCALATION
    （守 Rule 9.25.1 不可繞過守門）。
    """
    guard_negotiate(node_id, ledger_path=ledger_path)  # 可能 raise
    return _ic.record_negotiate(node_id, intent_a=intent_a, intent_b=intent_b,
                                ledger_path=ledger_path)


def compose_state(result: "_ic.CompositionResult", *,
                  ledger_path: Optional[Path] = None) -> str:
    """回傳組合層當前持久態（observability）。

    - 無衝突 → CPLAN_STABLE（全域一致，可排程）
    - 有衝突且任一衝突節點 reneg ≥ reneg_max → CPLAN_ESCALATION（協商預算耗盡，待人工）
    - 有衝突但仍有協商預算 → CPLAN_NEGOTIATE（尚在協商）
    """
    if not result.has_conflicts():
        return "CPLAN_STABLE"
    rmax = reneg_max()
    for node in result.conflicting_nodes():
        if _ic.compute_reneg(node, ledger_path=ledger_path) >= rmax:
            return "CPLAN_ESCALATION"
    return "CPLAN_NEGOTIATE"
