"""Phase N / ACT-106 — Composition Optimizer（全域組合最優 bounded branch-and-bound）.

對應藍圖：SDD_improving_Automation_14.md §1.2 / §3 ACT-106 / Rule 9.26.1/9.26.3/9.26.5。
形式化對應：formal/OPTIMIZATION_FSM.tla（SearchBounded + EventuallyScheduled）。

給定 N 個一致意圖（承 intent_composer / composition_blast_analyzer），在「高 blast 對不可
同批 + 批量 ≤ K」硬約束下，找**最小成本全域排程**（圖著色/裝箱型，NP-hard）。採 bounded
branch-and-bound：節點展開有硬上限（SDD_OPT_NODE_BUDGET）→ 永不指數爆炸無限搜尋。

回傳 schedule + nodes_expanded + optimal(是否在預算內窮舉證明最優) + gap（best − 下界）+
feasible + escalated。預算耗盡仍無可行解 → escalated=True（呼叫端導 OPT_ESCALATION，人工
放寬 budget/拆問題）。**advisory（Rule 9.26.3）：只推薦排程，絕不自動 commit、繞過
BACKLOG_PRIORITIZED 人工 signoff。** deterministic、純離線、零 LLM。
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .composition_objective_scorer import (
    OptProblem, score_schedule, is_feasible, lower_bound_batches,
)
from .optimization_halt_monitor import opt_node_budget
from .state_loader import REPO_ROOT

OPTIMIZATION_REPORT_DIR = REPO_ROOT / "build" / "reports" / "optimization"


@dataclass
class OptResult:
    schedule: Optional[List[List[str]]]   # 最優（或 best-so-far）排程；無可行解時 None
    nodes_expanded: int
    optimal: bool                         # True = 預算內窮舉證明最優；False = 預算限制下 best-so-far
    gap: float                            # optimal=True → 0（已證最優）；best-so-far → best_cost − 寬鬆批次數下界
    feasible: bool                        # 是否找到任一可行排程
    escalated: bool                       # True = 預算內無可行解 → OPT_ESCALATION
    best_cost: float = float("inf")


def optimize(problem: OptProblem, *, node_budget: Optional[int] = None) -> OptResult:
    """bounded branch-and-bound 求全域最優排程（SearchBounded 硬上限保證有界停機）。"""
    budget = node_budget if node_budget is not None else opt_node_budget()
    order = problem.intent_ids()
    n = len(order)

    state = {"nodes": 0, "best_cost": float("inf"), "best": None, "exhausted_budget": False}

    def can_place(intent: str, batch: List[str]) -> bool:
        if len(batch) >= problem.max_parallel:
            return False
        return all(not problem.conflicts(intent, x) for x in batch)

    def recurse(idx: int, batches: List[List[str]]) -> None:
        # leaf（完整排程）必先評分——leaf 非「展開」，不受 node 預算剪枝（否則剛好在預算
        # 邊界抵達的完整可行解會被誤殺，造成假性 escalation）。
        if idx == n:
            cost = score_schedule(batches, problem.values)
            if cost < state["best_cost"]:
                state["best_cost"] = cost
                state["best"] = [list(b) for b in batches]
            return
        # SearchBounded（Rule 9.26.1）：node 展開硬上限——超預算即停止展開內部節點。
        if state["nodes"] >= budget:
            state["exhausted_budget"] = True
            return
        # 界限剪枝：當前批次數已 ≥ best 完整解成本對應的批次，無法更優 → 剪。
        if state["best"] is not None and len(batches) >= state["best_cost"]:
            return
        state["nodes"] += 1
        intent = order[idx]
        # 先試放入既有批次（deterministic 序），再開新批次
        for b in batches:
            if can_place(intent, b):
                b.append(intent)
                recurse(idx + 1, batches)
                b.pop()
                if state["nodes"] >= budget:
                    return
        # 開新批次
        batches.append([intent])
        recurse(idx + 1, batches)
        batches.pop()

    if n > 0:
        recurse(0, [])

    best = state["best"]
    feasible = best is not None and is_feasible(best, problem)
    # optimal：搜尋未因預算中斷（窮舉完成）且找到可行解
    optimal = feasible and not state["exhausted_budget"]
    if n == 0:
        return OptResult(schedule=[], nodes_expanded=0, optimal=True, gap=0.0,
                         feasible=True, escalated=False, best_cost=0.0)
    # gap：optimal 已證最優 → 0；best-so-far → 與寬鬆批次數下界成本的距離（誠實揭露次優界限，
    # 非謊報 proven-optimal，守 Rule 9.26.5）。
    if not feasible:
        gap = float("inf")
    elif optimal:
        gap = 0.0
    else:
        lb_cost = float(lower_bound_batches(problem)) * 1.0   # 批次數下界 × BATCH_W（latency≥0）
        gap = round(max(0.0, state["best_cost"] - lb_cost), 6)
    # escalated（對應 TLA EscalationExhausted: expanded=MAX ∧ found=0）：not feasible ⟹ 預算耗盡——
    # 因 K≥1 時「每意圖獨佔一批」恆為可行排程，唯一找不到任何可行解的原因是 node 預算截斷。
    escalated = not feasible
    return OptResult(
        schedule=best, nodes_expanded=state["nodes"], optimal=optimal,
        gap=gap, feasible=feasible,
        escalated=escalated, best_cost=state["best_cost"],
    )


def optimization_markdown(result: OptResult) -> str:
    """產出 markdown 最優排程報告（advisory，餵 steersman；不阻塞、不自動 commit）。"""
    lines = [
        "## 🎯 全域組合最優排程（Composition Optimization — advisory，Rule 9.26.3）",
        "",
        f"- 展開節點數：{result.nodes_expanded}（SearchBounded 有界）",
        f"- 最優性：{'已窮舉證明最優（gap=0）' if result.optimal else f'best-so-far（預算限制，gap={result.gap}）'}",
        f"- 總成本：{result.best_cost}",
        "",
    ]
    if result.escalated:
        lines.append("🛑 **OPT_ESCALATION**：預算內找不到可行排程——請人工放寬 K / 拆解問題 / 接受序列化。")
    else:
        lines.append("| 批次 | 並行意圖 |")
        lines.append("|------|----------|")
        for i, batch in enumerate(result.schedule or [], 1):
            lines.append(f"| {i} | {', '.join(batch)} |")
    lines += ["",
              "> advisory：僅**推薦**排程；最終須 `BACKLOG_PRIORITIZED` 人工 signoff，**絕不自動 commit**（Rule 9.26.3）。"]
    return "\n".join(lines) + "\n"


def write_report(result: OptResult, *, out_dir: Optional[Path] = None,
                 today: Optional[str] = None) -> Path:
    """落盤 build/reports/optimization/OPT-SCHEDULE-{date}.md（§2 承諾產物，與 L/M 對稱）。"""
    target_dir = out_dir or OPTIMIZATION_REPORT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    date = today or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    path = target_dir / f"OPT-SCHEDULE-{date}.md"
    path.write_text(optimization_markdown(result), encoding="utf-8")
    return path
