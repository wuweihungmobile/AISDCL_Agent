"""BoundedGoalFreezeGate — IGoalFreezeGate 的有界自動凍結策略（adapter tier ≤400）。

improving_57 A 軌：在「比 GoalDecomposer 三道硬閘更嚴格」的有界子集上自動 signoff——
  (1) 步驟數 1 ≤ n ≤ max_auto_steps（預設 12 = 硬上限 24 之半，config 可下調不可上調）：
      小規模拆解才自動信任，大規模一律回退人工 review。
  (2) 無步驟 prompt 含注入嫌疑字元（黑名單 ⊇ SddToPlaybookAdapter._DENY / CONDITIONAL，
      防自動放行夾帶鏈式攻擊向量——深度防禦，與末端 pre_run_validator 互補）。
  (3) goal_hash 具備（審計可追溯）。
任一條件不成立 → auto_approved=False + 具體理由（fail-closed 回退 🔴 人工 signoff）。
全程不呼叫 Brain、無外部 I/O；裁決與條件清單回傳供審計與 XAI 拓樸審查。
"""
from __future__ import annotations

from ...core.ports.goal_freeze_gate import FreezeVerdict

# 自動放行硬上限（config 可下調不可上調，鏡像 GoalDecomposer.MAX_DECOMPOSITION_STEPS 紀律）
DEFAULT_MAX_AUTO_STEPS = 12
# 注入嫌疑字元集（⊇ SddToPlaybookAdapter._DENY {!,`,>,<,~,$,&,;}，再加管線 |）
_DENY = set("!`><~$&;|")


class BoundedGoalFreezeGate:
    """IGoalFreezeGate 有界自動凍結策略（純本地、可解釋、fail-closed）。"""

    def __init__(self, *, max_auto_steps: int = DEFAULT_MAX_AUTO_STEPS):
        # 可下調不可上調：夾在 [1, DEFAULT_MAX_AUTO_STEPS]
        self._max_auto_steps = max(1, min(int(max_auto_steps), DEFAULT_MAX_AUTO_STEPS))

    # IGoalFreezeGate 契約
    def evaluate(
        self, *, goal_hash: str, step_count: int, prompts: tuple[str, ...]
    ) -> FreezeVerdict:
        # 條件 1：步驟數有界（空拆解或超上限皆回退人工）
        if step_count <= 0:
            return FreezeVerdict(
                False, "拆解步驟為空，拒絕自動放行", ("step_count>0",)
            )
        if step_count > self._max_auto_steps:
            return FreezeVerdict(
                False,
                f"步驟數 {step_count} 超過自動放行上限 {self._max_auto_steps}，"
                "回退 🔴 人工 signoff",
                (f"step_count<={self._max_auto_steps}",),
            )
        conditions = [f"step_count={step_count}<={self._max_auto_steps}"]
        # 條件 2：無注入嫌疑字元（深度防禦）
        for i, prompt in enumerate(prompts):
            tainted = sorted(ch for ch in set(prompt) if ch in _DENY)
            if tainted:
                return FreezeVerdict(
                    False,
                    f"步驟 {i} prompt 含注入嫌疑字元 {tainted}，回退 🔴 人工 signoff",
                    (*conditions, "prompts_untainted"),
                )
        conditions.append("prompts_untainted")
        # 條件 3：goal_hash 具備（審計可追溯）
        if not goal_hash:
            return FreezeVerdict(
                False,
                "缺 goal_hash（審計不可追溯），回退 🔴 人工 signoff",
                (*conditions, "goal_hash_present"),
            )
        conditions.append(f"goal_hash={goal_hash}")
        return FreezeVerdict(
            True,
            f"有界條件全部成立（步驟≤{self._max_auto_steps}、prompt 無注入、"
            "有審計鍵）→ 自動 signoff",
            tuple(conditions),
        )


__all__ = ["BoundedGoalFreezeGate", "DEFAULT_MAX_AUTO_STEPS"]
