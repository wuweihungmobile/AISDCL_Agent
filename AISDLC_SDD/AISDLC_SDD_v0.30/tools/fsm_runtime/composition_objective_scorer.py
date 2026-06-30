"""Phase N / ACT-105 — Composition Objective Scorer（全域組合最佳化目標函式）.

對應藍圖：SDD_improving_Automation_14.md §1.3 / §3 ACT-105 / Rule 9.26.4。

Phase M 的 COMPOSITION_FSM 證了組合**一致**；本模組提供 L10 完整（組合**最優**）所需的
**全域目標函式**——把一個排程（intents 分批）量化成單一可比較成本，供 composition_optimizer
的 bounded branch-and-bound 最小化。

成本（越低越好）= batch_count × BATCH_W + Σ_b（批次序 i × Σ批內 value）× LATENCY_W
  - batch_count：序列批次數（越少＝越並行＝吞吐越好）
  - latency 項：高 value 意圖排在越後面的批次成本越高（鼓勵高價值早做）

凍結 `OBJECTIVE_PROFILE_VERSION`，調權重須 bump（Rule 9.26.4，防評分器自我放水）。
advisory：只算成本，**絕不自動改 spec、絕不阻塞 SCG**。純函式、deterministic、零 LLM。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Dict, FrozenSet, List, Optional, Set

# === 凍結評分強度（Rule 9.26.4：調整須 bump version）===
OBJECTIVE_PROFILE_VERSION = "v1.0"
BATCH_W = 1.0       # 批次數權重（主導項）
LATENCY_W = 0.1     # 高價值晚做懲罰（tie-break）


@dataclass
class OptProblem:
    """全域組合最佳化問題：intents 分批，高 blast 對不可同批，批量 ≤ K。"""
    values: Dict[str, float]                       # intent_id → 商業價值（ROI）
    conflict_edges: Set[FrozenSet] = field(default_factory=set)  # {frozenset({a,b})}：高 blast 不可同批
    max_parallel: int = 3                          # 每批最大並行數 K

    def intent_ids(self) -> List[str]:
        # deterministic 展開序：value 由高到低、再 id 字典序
        return sorted(self.values.keys(), key=lambda i: (-self.values.get(i, 0.0), i))

    def conflicts(self, a: str, b: str) -> bool:
        return frozenset({a, b}) in self.conflict_edges


def score_schedule(schedule: List[List[str]], values: Dict[str, float]) -> float:
    """量化一個排程（有序批次清單）的成本（越低越好，deterministic）。"""
    batch_count = len(schedule)
    latency = 0.0
    for i, batch in enumerate(schedule):
        latency += i * sum(values.get(x, 0.0) for x in batch)
    return round(batch_count * BATCH_W + latency * LATENCY_W, 6)


def is_feasible(schedule: List[List[str]], problem: OptProblem) -> bool:
    """硬約束：批量 ≤ K 且任一批內無高 blast 衝突對；且涵蓋全部 intent 各一次。"""
    seen: List[str] = []
    for batch in schedule:
        if len(batch) > problem.max_parallel:
            return False
        for x in range(len(batch)):
            for y in range(x + 1, len(batch)):
                if problem.conflicts(batch[x], batch[y]):
                    return False
        seen.extend(batch)
    return sorted(seen) == sorted(problem.values.keys())


def lower_bound_batches(problem: OptProblem) -> int:
    """可行排程的批次數理論下界（relaxation）：ceil(N / K)。

    每批至多 K 個意圖，故 N 個意圖至少需 ceil(N/K) 批——這是放鬆「衝突約束」後的
    optimistic 下界（衝突只會讓真實最優 ≥ 此值），供 optimizer 計算 best-so-far 的 gap。
    """
    n = len(problem.values)
    if n == 0:
        return 0
    return max(1, ceil(n / max(1, problem.max_parallel)))
