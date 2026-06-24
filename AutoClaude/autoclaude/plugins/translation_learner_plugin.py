"""TranslationLearnerPlugin — A 軌轉譯策略元學習活體化（AutoSDD_improving_60，plugin_entry ≤250）。

A 軸協作自治 L4→L5「有界自演化、人在環上」：在既有 IRtmFeedbackSource（improving_27
回流讀回邊）之上，POST_RUN 跨 session 讀回覆蓋度 history，以純函數 select_proposals 依
**失敗頻次**元學習出「轉譯策略改進候選」並自動提議（活體 propose 預設 ON）。

訂閱 phase：
  - POST_RUN → 讀 rtm_feedback.read_history(project) → select_proposals → sink.record_proposal

🔴 紅線（沿用 rtm_writeback/evolution「RTM/SPEC-PATCH 絕不自動套用」）：
  本 plugin **只產 proposed 提議供人工 review**，絕不改 SddToPlaybookAdapter 轉譯行為、
  絕不釋出可執行變更（apply=人工 signoff 守界）。proposals 純諮詢 → 轉譯行為零退化。

活體化（L5）vs 零退化（紅線）並存：
  - propose 預設 ON（config flag enable_translation_auto_propose，env opt-out 見 _ENV_FLAG，
    鏡像 B 軌 SLV）→ 元學習迴圈常態運轉（活體）。
  - 非 SDD playbook / flag OFF / 無注入 / 無 history → no-op（零退化）。
  - 提議數有界（max_proposals_per_run）、不遞迴、dedup → 守界。
  - 全程 fail-soft（諮詢不阻斷主流程，鏡像 evolution_plugin）。

設計原則：plugin 僅 import core.ports.translation_learning + core.hookspec；sink/rtm_feedback/
observability 經 wiring constructor 注入（Any 型別，不 import infra），plugin 間零互 import。
"""
from __future__ import annotations

import logging
import os
from typing import Any

from ..core.hookspec import HookContext, KernelPhase
from ..core.ports.translation_learning import select_proposals

logger = logging.getLogger("autoclaude.plugins.translation_learner")

_ENV_FLAG = "AUTOCLAUDE_ENABLE_TRANSLATION_AUTO_PROPOSE"
_OPT_OUT = {"0", "false", "no", "off"}


def _auto_propose_enabled(config_enabled: bool) -> bool:
    """活體 propose 是否啟用：env opt-out（0/false/no/off）優先，否則取 config flag。

    鏡像 B 軌 SLV `_slv_auto_propose_enabled()`：env 未設＝沿用 config（預設 ON）；
    顯式 opt-out＝關閉還原零退化。
    """
    raw = os.environ.get(_ENV_FLAG)
    if raw is not None and raw.strip().lower() in _OPT_OUT:
        return False
    return config_enabled


class TranslationLearnerPlugin:
    """A 軸 L5 轉譯策略元學習 Plugin（improving_60，US: A→L5 協作元學習）。"""

    PRIORITY = 55  # 介於 rtm_writeback(52) 與 convergence(65) 之間（A 軌反饋族群相鄰，獨佔值）

    def __init__(
        self,
        *,
        sink: Any | None = None,            # ITranslationLearningSink（不 import infra）
        rtm_feedback: Any | None = None,    # IRtmFeedbackSource（不 import infra）
        observability: Any | None = None,
        enabled: bool = True,                  # config flag（預設 ON＝活體）
        max_proposals_per_run: int = 3,        # 有界硬閘
        min_failing_runs: int = 2,             # 元學習門檻（降噪）
    ):
        self._sink = sink
        self._rtm_feedback = rtm_feedback
        self._obs = observability
        self._enabled = enabled
        self._max = max(0, int(max_proposals_per_run))
        self._min_failing_runs = max(1, int(min_failing_runs))

    def name(self) -> str:
        return "translation_learner"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [KernelPhase.POST_RUN]

    def on_event(self, ctx: HookContext) -> Any | None:
        if ctx.phase != KernelPhase.POST_RUN:
            return None
        # opt-out / 未注入 → no-op（零退化）
        if not _auto_propose_enabled(self._enabled):
            return None
        if self._sink is None or self._rtm_feedback is None:
            return None
        # 非 SDD playbook → no-op（轉譯元學習僅對 aisdlc_sdd 工作流有意義）
        if getattr(ctx.playbook, "workflow_type", None) != "aisdlc_sdd":
            return None

        try:
            project = ctx.playbook.project
            history = self._rtm_feedback.read_history(project)
            already = frozenset(p.at_id for p in self._sink.list_proposals(project))
            proposals = select_proposals(
                history, already,
                min_failing_runs=self._min_failing_runs, max_new=self._max,
            )
            for p in proposals:
                self._sink.record_proposal(project, p)
                self._emit(p, project)
            if proposals:
                logger.info(
                    "TranslationLearner[%s]：自跨 session history 元學習提議 %d 筆轉譯改進"
                    "候選（proposed，待人工 review；絕不自動套用）",
                    project, len(proposals),
                )
        except Exception as exc:  # noqa: BLE001 — fail-soft（諮詢不阻斷主流程）
            logger.warning("TranslationLearner fail-soft: %s", exc)
        return None

    def _emit(self, proposal: Any, project: str) -> None:
        """XAI 審計痕：提議入 observability（拓樸可審；不阻斷）。"""
        if self._obs is None:
            return
        try:
            self._obs.record_event("sdd.translation_proposal", {
                "project": project,
                "at_id": proposal.at_id,
                "failing_runs": proposal.failing_runs,
                "total_runs": proposal.total_runs,
                "status": proposal.status,
            })
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("translation_proposal emit fail-soft: %s", exc)


__all__ = ["TranslationLearnerPlugin"]
