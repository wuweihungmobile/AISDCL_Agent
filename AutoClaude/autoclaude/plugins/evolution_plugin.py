"""EvolutionPlugin — 取代 PlaybookRunner 中 _evolver + _minimax_evolver fallback 邏輯。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 5 列（priority=70）
  - SD_Improving_02.md v1.1 §2.5 W10 #11（極高風險）
  - SD_Improving_05 W3-3：擴 phase 訂閱（ON_EVOLUTION_PROPOSE / ON_EVOLUTION_APPLY /
    ON_ESCALATION_DUMP_REQUEST），承接 CheckpointPlugin emit 的 escalation 事件。

訂閱 phase（W3-3 由 1 個擴至 4 個）：
  - ON_ESCALATION              → AI + 規則 fallback 鏈，提議 PlaybookEvolutionProposal
                                  （正向實作；回傳 MutationProposal）
  - ON_EVOLUTION_PROPOSE       → 與 ON_ESCALATION 共用 propose 路徑（正向實作）
  - ON_EVOLUTION_APPLY         → **NO-OP**（過渡訂閱位；audit log only）
                                  W6 完整下沉：MutationApplyService.apply 結果回饋
                                  與 goal_summary clear 動作
  - ON_ESCALATION_DUMP_REQUEST → **NO-OP**（過渡訂閱位；audit log only）
                                  W6 完整下沉：notify_escalation 將從 CheckpointPlugin
                                  callback 路徑移轉至此 plugin（接收 EscalationDumpedResult
                                  並廣播 user notification）

SD_05 W3 三方審查 Arch-C2 / SA-C1 註：兩個 NO-OP phase 已明確標註為「過渡訂閱位」，
audit log 等級由 debug 改為 info（dispatch 時可被 monitoring 系統觀察）。W6 拔除清單
§6.3 W3 第 6 項列出此兩 phase 的「完整下沉」工作。

設計原則：
  1. 優先諮詢 MinimaxEvolver（AI 驅動）
  2. AI 失敗 → fallback PlaybookEvolver（規則驅動）
  3. 兩者皆失敗 → 回傳 None（呼叫端處理 ESCALATION）
  4. 將 PlaybookEvolutionProposal 轉換為 StepMutation + MutationProposal

對應 Gap：
  - Gap-010-E / Gap-016 / Gap-022-C / Gap-033
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from ..core.hookspec import HookContext, KernelPhase, MutationProposal
from ..core.ports.rtm_feedback import coverage_trend
from ..evolution.minimax_evolver import MinimaxEvolver
from ..evolution.playbook_evolver import PlaybookEvolutionProposal, PlaybookEvolver
from ..models.step_mutation import StepMutation, StepMutationType

logger = logging.getLogger("autoclaude.plugins.evolution")


class EvolutionPlugin:
    """Playbook 自演化 Plugin（AI + 規則 fallback）。"""

    PRIORITY = 70

    def __init__(
        self,
        rule_evolver: Optional[PlaybookEvolver] = None,
        ai_evolver: Optional[MinimaxEvolver] = None,
        minimax_client: Optional[Any] = None,
        *,
        rtm_feedback: Optional[Any] = None,
        enable_rtm_feedback: bool = False,
    ):
        self._rule_evolver = rule_evolver or PlaybookEvolver()
        self._ai_evolver = ai_evolver or MinimaxEvolver()
        self._minimax_client = minimax_client
        self._latest_proposal: Optional[PlaybookEvolutionProposal] = None
        # AutoSDD_improving_27 W1：A 軌 RTM 反饋讀回（flag-gated，預設 OFF）。
        # 啟用後 ON_ESCALATION 時讀回上次 RTM coverage，把 gap 摘要附 proposal.rationale
        # 作為**諮詢**輸入（不改 mutation 決策、不自動套用 RTM/SPEC）。對齊紅線：
        # 演化仍走 require_evolution_signoff + max_evolutions 硬閘。
        self._rtm_feedback = rtm_feedback  # IRtmFeedbackSource（Any 型別，不 import infra）
        self._enable_rtm_feedback = enable_rtm_feedback

    def name(self) -> str:
        return "evolution"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [
            KernelPhase.ON_ESCALATION,
            # SD_05 W3-3：擴 3 新 phase
            KernelPhase.ON_EVOLUTION_PROPOSE,
            KernelPhase.ON_EVOLUTION_APPLY,
            KernelPhase.ON_ESCALATION_DUMP_REQUEST,
        ]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        phase = ctx.phase
        # ON_ESCALATION 與 ON_EVOLUTION_PROPOSE 共用 propose 路徑
        if phase in (KernelPhase.ON_ESCALATION, KernelPhase.ON_EVOLUTION_PROPOSE):
            return self._handle_propose(ctx)
        if phase == KernelPhase.ON_EVOLUTION_APPLY:
            # W3 NO-OP（過渡訂閱位，W6 完整下沉）；audit log info 級供 monitoring 觀察
            payload = ctx.payload or {}
            logger.info(
                "EvolutionPlugin[ON_EVOLUTION_APPLY/no-op] clear_goal_summary=%s "
                "(W6 將完整下沉 MutationApplyService 結果回饋)",
                payload.get("clear_goal_summary", False),
            )
            return None
        if phase == KernelPhase.ON_ESCALATION_DUMP_REQUEST:
            # W3 NO-OP（過渡訂閱位，W6 完整下沉）；notify 仍由 CheckpointPlugin
            # callback 路徑觸發，W6 將完整移轉至本 plugin。
            logger.info(
                "EvolutionPlugin[ON_ESCALATION_DUMP_REQUEST/no-op] step_id=%s "
                "(W6 將完整下沉 notify_escalation)",
                ctx.task.step_id if ctx.task else "<no-task>",
            )
            return None
        return None

    def _handle_propose(self, ctx: HookContext) -> Optional[MutationProposal]:
        payload = ctx.payload or {}
        proposal = self._propose(ctx, payload)
        if proposal is None:
            return None

        self._latest_proposal = proposal
        mutation = self._proposal_to_mutation(proposal)
        if mutation is None:
            return None

        return MutationProposal(
            contributor=self.name(),
            mutation=mutation,
            rationale=(
                proposal.reasoning
                + self._rtm_gap_annotation(ctx)
                + self._rtm_trend_annotation(ctx)
            ),
        )

    def _rtm_gap_annotation(self, ctx: HookContext) -> str:
        """W1：讀回上次 RTM coverage gap，回傳附加到 rationale 的**諮詢**註記。

        僅在 flag ON ∧ 有注入 source ∧ 失敗步驟為 SDD 編譯步驟（step_id 前綴 sdd-）
        ∧ 上次報告存在且未完全覆蓋時回非空字串；其餘一律回 ""（零退化）。
        fail-soft：讀回任何例外吞掉回 ""（諮詢功能不得阻斷演化）。
        """
        if not self._enable_rtm_feedback or self._rtm_feedback is None:
            return ""
        try:
            task = ctx.task
            step_id = (getattr(task, "step_id", "") or "") if task else ""
            if not step_id.startswith("sdd-"):
                return ""
            report = self._rtm_feedback.read_report(ctx.playbook.project)
            if report is None or report.is_fully_covered:
                return ""
            failed = ", ".join(report.failed_at_ids) or "(無)"
            return (
                "\n\n[RTM 反饋｜上次覆蓋諮詢（不自動套用，僅供 signoff 判讀）]\n"
                f"- AC 覆蓋：{report.ac_covered}/{report.ac_total}"
                f"（{report.ac_coverage_pct}%）\n"
                f"- 未通過 AT：{failed}"
            )
        except Exception as exc:  # noqa: BLE001 — fail-soft（諮詢不得阻斷主流程）
            logger.warning("RTM 反饋讀回 fail-soft: %s", exc)
            return ""

    def _rtm_trend_annotation(self, ctx: HookContext) -> str:
        """W-28-1：讀回跨輪覆蓋趨勢，回傳附加到 rationale 的**諮詢**註記。

        與 _rtm_gap_annotation 同守門（flag ON ∧ 有注入 source ∧ SDD 編譯步驟），
        但消費 read_history（跨輪）而非 read_report（最新單筆），閉合 improving_27
        W3 留下的「趨勢 history 寫出後無人讀」冷資料斷鏈。需 ≥2 輪才有趨勢，否則回 ""。
        紅線：僅增補 rationale 供 signoff 判讀，不改 mutation 決策、不碰 max_evolutions。
        fail-soft：讀回任何例外吞掉回 ""（諮詢不得阻斷演化）。
        """
        if not self._enable_rtm_feedback or self._rtm_feedback is None:
            return ""
        try:
            task = ctx.task
            step_id = (getattr(task, "step_id", "") or "") if task else ""
            if not step_id.startswith("sdd-"):
                return ""
            trend = coverage_trend(self._rtm_feedback.read_history(ctx.playbook.project))
            if trend is None or trend.previous_pct is None:
                return ""  # 無足夠輪數（<2）→ 尚無趨勢
            arrow = {"improving": "↑ 改善", "declining": "↓ 下降", "flat": "→ 持平"}.get(
                trend.direction, trend.direction
            )
            streak = (
                f"，連續 {trend.consecutive_declines} 輪下降"
                if trend.consecutive_declines >= 2
                else ""
            )
            return (
                "\n\n[RTM 反饋｜跨輪覆蓋趨勢諮詢（不自動套用，僅供 signoff 判讀）]\n"
                f"- 近 {trend.rounds} 輪 AC 覆蓋：上輪 {trend.previous_pct}%"
                f" → 本輪 {trend.latest_pct}%（{arrow} {trend.delta_pct:+}%{streak}）"
            )
        except Exception as exc:  # noqa: BLE001 — fail-soft（諮詢不得阻斷主流程）
            logger.warning("RTM 趨勢讀回 fail-soft: %s", exc)
            return ""

    # ──────────────────────────────────────────────
    # 公開 API
    # ──────────────────────────────────────────────
    def latest_proposal(self) -> Optional[PlaybookEvolutionProposal]:
        return self._latest_proposal

    def propose(
        self,
        playbook,
        failed_step_idx: int,
        escalation_dump,
        escalation_history: Optional[list] = None,
    ) -> Optional[PlaybookEvolutionProposal]:
        """供 Kernel / 呼叫端直接觸發 evolution 鏈。"""
        # 優先 AI
        if self._minimax_client is not None:
            try:
                ai_proposal = self._ai_evolver.propose_evolution_via_ai(
                    playbook=playbook,
                    failed_step_idx=failed_step_idx,
                    escalation_dump=escalation_dump,
                    minimax_client=self._minimax_client,
                )
                if ai_proposal is not None:
                    return ai_proposal
            except Exception as exc:
                logger.warning("AI evolver 失敗，fallback 至規則引擎: %s", exc)
        # Fallback：規則引擎
        return self._rule_evolver.propose_evolution(
            playbook=playbook,
            failed_step_idx=failed_step_idx,
            escalation_dump=escalation_dump,
            escalation_history=escalation_history,
        )

    # ──────────────────────────────────────────────
    # 內部
    # ──────────────────────────────────────────────
    def _propose(
        self, ctx: HookContext, payload: dict,
    ) -> Optional[PlaybookEvolutionProposal]:
        escalation_dump = payload.get("escalation_dump")
        if escalation_dump is None:
            return None
        failed_step_idx = int(payload.get("failed_step_idx",
                                          ctx.step_idx or 0))
        escalation_history = payload.get("escalation_history") or []
        return self.propose(
            playbook=ctx.playbook,
            failed_step_idx=failed_step_idx,
            escalation_dump=escalation_dump,
            escalation_history=escalation_history,
        )

    @staticmethod
    def _proposal_to_mutation(
        proposal: PlaybookEvolutionProposal,
    ) -> Optional[StepMutation]:
        """將 PlaybookEvolutionProposal 轉換為 StepMutation。

        - INJECT_STEP   → INJECT_BEFORE
        - REVISE_EVALUATOR → REVISE_CURRENT（暫以 prompt 包裝）
        - SPLIT_STEP    → INJECT_BEFORE（拆分後第一個步驟）
        """
        if proposal.evolution_type == "INJECT_STEP" and proposal.new_step:
            ns = proposal.new_step
            return StepMutation(
                mutation_type=StepMutationType.INJECT_BEFORE,
                new_step_id=ns.step_id,
                new_step_name=ns.name,
                new_step_prompt=ns.prompt,
                new_step_evaluator_command=ns.evaluator_command,
                new_step_expected_regex=ns.expected_output_regex,
                new_step_max_retries=ns.max_retries,
                reasoning=proposal.reasoning,
            )
        if proposal.evolution_type == "SPLIT_STEP" and proposal.split_steps:
            first = proposal.split_steps[0]
            return StepMutation(
                mutation_type=StepMutationType.INJECT_BEFORE,
                new_step_id=first.step_id,
                new_step_name=first.name,
                new_step_prompt=first.prompt,
                new_step_evaluator_command=first.evaluator_command,
                reasoning=proposal.reasoning,
            )
        if proposal.evolution_type == "REVISE_EVALUATOR" and proposal.revised_evaluator:
            return StepMutation(
                mutation_type=StepMutationType.REVISE_CURRENT,
                revised_prompt=f"[evolved evaluator suggested]\n{proposal.revised_evaluator}",
                reasoning=proposal.reasoning,
            )
        return None
