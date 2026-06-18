"""Phase N / ACT-107 — Optimization-Halt Monitor（NP-hard 搜尋有界停機 runtime 守門）.

對應藍圖：SDD_improving_Automation_14.md §1.1 / §3 ACT-107 / Rule 9.26.1。
形式化對應：formal/OPTIMIZATION_FSM.tla（獨立命名空間，expanded/found 兩變數）。

單軌 SDD_FSM 證單意圖開發迴圈停機；FLEET_FSM 證資源並行；META_FSM 證學習元迴圈不抖動；
COMPOSITION_FSM 證跨意圖**一致**收斂。本模組對應**第五條形式化迴圈**：全域組合**最佳化
搜尋**——bounded branch-and-bound 的節點展開有硬上限，永不指數爆炸無限搜尋，最終必抵
OPT_SCHEDULED（找到排程）或 OPT_ESCALATION（預算內無可行解，人工放寬/拆問題）。

核心守門 SearchBounded（Rule 9.26.1）—— node 展開數 ≤ SDD_OPT_NODE_BUDGET
（clamp[8,4096]，預設 256）。超限即停止搜尋，呼叫端導 OPT_ESCALATION（若尚無可行解）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# OPTIMIZATION_FSM 狀態宇宙（與 formal/OPTIMIZATION_FSM.tla 的 OptStates 同步；由
# tests/test_phase_n.py 的 test_optimization_fsm_states_match_python 守雙源一致）。
OPTIMIZATION_STATES = frozenset({
    "OPT_OBSERVE", "OPT_EXPAND", "OPT_PRUNE", "OPT_SCHEDULED", "OPT_ESCALATION",
})
OPTIMIZATION_TERMINALS = frozenset({"OPT_SCHEDULED", "OPT_ESCALATION"})

_DEFAULT_NODE_BUDGET = 256
_BUDGET_CLAMP = (8, 4096)


class SearchBudgetExceeded(RuntimeError):
    """Rule 9.26.1：node 展開預算耗盡——停止搜尋；若尚無可行解則導 OPT_ESCALATION。"""


def opt_node_budget() -> int:
    """讀 SDD_OPT_NODE_BUDGET（env 可調），clamp[8,4096]，預設 256。"""
    raw = os.environ.get("SDD_OPT_NODE_BUDGET")
    if not raw:
        return _DEFAULT_NODE_BUDGET
    try:
        val = int(raw)
    except ValueError:
        return _DEFAULT_NODE_BUDGET
    lo, hi = _BUDGET_CLAMP
    return max(lo, min(hi, val))


@dataclass
class GuardResult:
    allowed: bool
    expanded: int
    budget: int
    reason: str = ""


def guard_expand(expanded: int, *, budget: int | None = None) -> GuardResult:
    """檢查再展開一個搜尋節點是否仍在預算內（純判定）。

    expanded < budget → 放行；expanded ≥ budget → raise（呼叫端停止搜尋、按 found 決定
    回 OPT_SCHEDULED〔best-so-far〕或 OPT_ESCALATION〔無可行解〕）。
    """
    b = budget if budget is not None else opt_node_budget()
    if expanded >= b:
        raise SearchBudgetExceeded(
            f"node 展開 expanded={expanded} ≥ SDD_OPT_NODE_BUDGET={b}：搜尋預算耗盡，"
            f"停止 branch-and-bound（Rule 9.26.1）"
        )
    return GuardResult(allowed=True, expanded=expanded, budget=b, reason="預算未耗盡，放行")


def opt_state(*, found: bool, exhausted: bool) -> str:
    """回傳最佳化搜尋層的持久態（observability）。

    - 已找到可行排程（found）→ OPT_SCHEDULED（不論是否耗盡：耗盡則 best-so-far）
    - 預算耗盡且未找到 → OPT_ESCALATION（人工：放寬 budget / 拆問題 / 接受序列化）
    - 仍在搜尋（未耗盡未找到）→ OPT_EXPAND
    """
    if found:
        return "OPT_SCHEDULED"
    if exhausted:
        return "OPT_ESCALATION"
    return "OPT_EXPAND"
