"""GoalDecomposer — 自主任務拆解的有界閘（F-A1 / ADR-AGT-002）。

對應 SRD_AGT_Phase3_Autonomy.md §2：

    高階 goal
      → IBrain.decide_decomposition 一次取得候選步驟 DAG（不遞迴）
      → 三道機械有界閘（任一不過即拒絕，不重試、不截斷）：
           (a) 步驟數 ≤ MAX_DECOMPOSITION_STEPS（硬上限 24，config 可下調不可上調）
           (b) DAG 無環（拓撲排序）
           (c) 每節點具非空可執行 prompt
      → 產出 Playbook 草稿（既有 models/playbook.py schema，不改 schema）
      → 🔴 人工 signoff 硬閘：signoff 前不釋出可執行 Playbook
      → signoff 後交既有 PlaybookRunner 執行

有界性保證（對齊 R-9.23 / Rule 8 棘輪）：
  - 步驟數有界（硬上限 24，超限拒絕非截斷）
  - 無環（拓撲排序偵測）
  - 不自我放大（每次拆解僅 1 次 Brain 呼叫，拆解結果不再觸發拆解）
  - 人工棘輪（signoff 為釋出前置硬閘；signoff 記錄人/日期/goal hash 入審計）
  - Token 有界（驗證走本地拓撲排序，不呼叫 Brain）

capability 守門：不支援 decomposition 之 brain 直接拒絕（不靜默降級）。

設計原則（strategy tier ≤ 300）：純本地驗證 + 既有 schema 序列化，零 infra 依賴。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime

import yaml

from ..core.ports.brain import IBrain
from ..core.ports.observability import IObservabilityPort, NullObservability
from ..core.ports.tool_invocation import IToolInvocation
from ..models.decision import DecompositionDecision, DecompositionStep
from ..models.playbook import Playbook, PlaybookTask

# ADR-AGT-002 §2：硬上限 24（config 可下調不可上調）
MAX_DECOMPOSITION_STEPS = 24


class DecompositionError(Exception):
    """拆解被有界閘拒絕（超限 / 含環 / 空 prompt / capability 不支援 / API 故障）。"""


@dataclass(frozen=True)
class DecompositionDraft:
    """拆解草稿 + signoff 狀態。

    signoff 前 signed_off=False，release_for_execution() 拒絕釋出可執行 Playbook
    （ADR-AGT-002 §2.4 人工棘輪硬閘）。
    """

    playbook: Playbook
    goal: str
    goal_hash: str
    reasoning: str = ""
    signed_off: bool = False
    approver: str = ""
    approved_at: str = ""


class GoalDecomposer:
    """高階 goal → 有界步驟 DAG → Playbook 草稿 → 🔴 signoff（A 能力，F-A1）。"""

    def __init__(
        self,
        brain: IBrain,
        *,
        max_steps: int = MAX_DECOMPOSITION_STEPS,
        observability: IObservabilityPort | None = None,
        tool_invocation: IToolInvocation | None = None,
    ):
        self._brain = brain
        # 硬上限 24：config 可下調不可上調（ADR-AGT-002 §2）
        self._max_steps = min(int(max_steps), MAX_DECOMPOSITION_STEPS)
        self._obs = observability or NullObservability()
        # F-A2 注入點：拆解出的步驟若需工具，經此 port 查 allowlist 可用性（保留擴充點）
        self._tool = tool_invocation

    # ──────────────────────────────────────────────
    # 公開 API
    # ──────────────────────────────────────────────
    def decompose(
        self,
        goal: str,
        *,
        context: str = "",
        project: str = "decomposed-goal",
    ) -> DecompositionDraft:
        """拆解 goal 為 Playbook 草稿（未 signoff）。任一有界閘不過即 raise。"""
        if not goal or not goal.strip():
            self._audit("decomposition_rejected", goal, reason="empty_goal")
            raise DecompositionError("goal 為空，拒絕拆解")

        # capability 守門：不支援即拒絕，不靜默降級（ADR-AGT-002 §5）
        if not self._brain.capabilities().supports_decomposition:
            self._audit("decomposition_rejected", goal, reason="brain_unsupported")
            raise DecompositionError(
                "目前 brain 不支援 decomposition"
                "（capabilities.supports_decomposition=False），拒絕拆解"
            )

        # 一次性 Brain 呼叫（不遞迴）
        decision = self._brain.decide_decomposition(goal=goal, context=context)
        if decision is None:
            self._audit("decomposition_rejected", goal, reason="brain_returned_none")
            raise DecompositionError("brain 拆解失敗（回傳 None），不重試")

        self._validate_bounded(goal, decision)  # 三道有界閘
        ordered = self._topological_order(decision.steps)  # 無環 + 拓撲序
        playbook = self._to_playbook_draft(goal, project, ordered)
        goal_hash = self._goal_hash(goal)
        self._audit(
            "decomposition_accepted", goal, reason="ok", steps=len(ordered),
            goal_hash=goal_hash,
        )
        return DecompositionDraft(
            playbook=playbook, goal=goal, goal_hash=goal_hash,
            reasoning=decision.reasoning,
        )

    def approve(self, draft: DecompositionDraft, *, approver: str) -> DecompositionDraft:
        """🔴 人工 signoff：記錄人/日期/goal hash 入審計，回傳已簽署草稿。"""
        if not approver or not approver.strip():
            raise DecompositionError("signoff 需要 approver（人工棘輪不可匿名）")
        approved_at = datetime.now(UTC).isoformat()
        self._audit(
            "decomposition_signoff", draft.goal, reason="approved",
            approver=approver, approved_at=approved_at, goal_hash=draft.goal_hash,
        )
        return replace(
            draft, signed_off=True, approver=approver, approved_at=approved_at,
        )

    def release_for_execution(self, draft: DecompositionDraft) -> Playbook:
        """signoff 硬閘：僅已簽署草稿可釋出可執行 Playbook；否則拒絕（零步驟執行）。"""
        if not draft.signed_off:
            self._audit("decomposition_release_denied", draft.goal, reason="not_signed_off")
            raise DecompositionError(
                "草稿未經 🔴 人工 signoff，拒絕釋出可執行 Playbook（ADR-AGT-002 §2.4）"
            )
        return draft.playbook

    @staticmethod
    def draft_to_yaml(playbook: Playbook) -> str:
        """序列化 Playbook 草稿為 YAML（可被既有 load_playbook 往返載入）。"""
        return yaml.safe_dump(
            playbook.model_dump(exclude_none=True),
            allow_unicode=True, sort_keys=False,
        )

    # ──────────────────────────────────────────────
    # 三道機械有界閘（純本地，不呼叫 Brain）
    # ──────────────────────────────────────────────
    def _validate_bounded(self, goal: str, decision: DecompositionDecision) -> None:
        steps = decision.steps
        if not steps:
            self._audit("decomposition_rejected", goal, reason="no_steps")
            raise DecompositionError("拆解結果為空，拒絕")
        # (a) 步驟數有界
        if len(steps) > self._max_steps:
            self._audit(
                "decomposition_rejected", goal, reason="too_many_steps",
                steps=len(steps), limit=self._max_steps,
            )
            raise DecompositionError(
                f"拆解步驟數 {len(steps)} 超過上限 {self._max_steps}，拒絕（不截斷、不重試）"
            )
        # step_id 唯一
        ids = [s.step_id for s in steps]
        if len(set(ids)) != len(ids):
            self._audit("decomposition_rejected", goal, reason="duplicate_step_id")
            raise DecompositionError("拆解步驟 step_id 重複，拒絕")
        # (c) 每節點非空 prompt
        for s in steps:
            if not s.prompt or not s.prompt.strip():
                self._audit(
                    "decomposition_rejected", goal, reason="empty_prompt",
                    step_id=s.step_id,
                )
                raise DecompositionError(f"步驟 {s.step_id} 的 prompt 為空，拒絕")

    def _topological_order(self, steps: list[DecompositionStep]) -> list[DecompositionStep]:
        """(b) DAG 無環檢查 + 拓撲排序（Kahn）。偵測到環即拒絕。"""
        by_id = {s.step_id: s for s in steps}
        # 入度 + 鄰接（depends_on：dep → self 的邊）
        indeg = {sid: 0 for sid in by_id}
        adj: dict[str, list[str]] = {sid: [] for sid in by_id}
        for s in steps:
            for dep in s.depends_on:
                if dep not in by_id:
                    self._audit(
                        "decomposition_rejected", s.step_id, reason="dangling_dependency",
                        dep=dep,
                    )
                    raise DecompositionError(
                        f"步驟 {s.step_id} 相依不存在的 step_id={dep}，拒絕"
                    )
                adj[dep].append(s.step_id)
                indeg[s.step_id] += 1
        # 以原始順序為 tie-breaker，保拆解穩定性
        queue = [s.step_id for s in steps if indeg[s.step_id] == 0]
        order: list[str] = []
        while queue:
            cur = queue.pop(0)
            order.append(cur)
            for nxt in adj[cur]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(steps):
            self._audit("decomposition_rejected", "", reason="cycle_detected")
            raise DecompositionError("拆解 DAG 含環（拓撲排序失敗），拒絕")
        return [by_id[sid] for sid in order]

    # ──────────────────────────────────────────────
    # 草稿產出（既有 Playbook schema，不改 schema）
    # ──────────────────────────────────────────────
    @staticmethod
    def _to_playbook_draft(
        goal: str, project: str, ordered: list[DecompositionStep],
    ) -> Playbook:
        tasks = [
            PlaybookTask(
                step_id=s.step_id,
                name=s.name or s.step_id,
                prompt=s.prompt,
                evaluator_command=s.evaluator_command,
            )
            for s in ordered
        ]
        return Playbook(project=project, global_goal=goal, tasks=tasks)

    @staticmethod
    def _goal_hash(goal: str) -> str:
        return hashlib.sha256(goal.encode("utf-8")).hexdigest()[:16]

    def _audit(self, event: str, target: str, **attrs) -> None:
        self._obs.record_event(event, {"target": target, **attrs})


__all__ = [
    "GoalDecomposer",
    "DecompositionDraft",
    "DecompositionError",
    "MAX_DECOMPOSITION_STEPS",
]
