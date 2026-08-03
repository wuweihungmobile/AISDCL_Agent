"""
SD_07 W1: ESCALATION 處理區塊（從 _impl.py 抽出，原 L276-379 / L420-522）

職責：統一處理 convergence escalate 與 max_retries escalate 兩條路徑，
含 GOAL_SYNTHESIS 三條件、Gap-048 per-step evolution 上限、
MinimaxEvolver → 規則引擎 fallback、apply_evolution、notify、PlaybookResult 回傳。

設計原則（依 ADR-SD07-001 strategy tier ≤ 300 LOC）：
- 兩條 escalation 路徑以個別 public function 暴露，避免過度合併致可讀性下降
- 共用 helper（_handle_goal_synthesis_recovery / _handle_per_step_evolution）置於私有區段
- 完整保留原 logger 訊息與 escalation_history.append / save_evolution_resume_checkpoint 順序
"""
from __future__ import annotations

import logging

from ...models.playbook import Playbook
from ..types import PlaybookResult

logger = logging.getLogger("autoclaude.execution.playbook")


def record_escalation_and_dump(
    runner, tracker, task, error_cls, playbook_path, eval_output, human_hint: str,
):
    # ESCALATION 三處共用的「記 KB → 存 EscalationDump → 追加歷史」三連，原本逐字
    # 重複三份、只有 human_hint 不同（本檔兩條路徑 ＋ _impl.py 的 Gap-010-A 語意預算
    # 耗盡分支）。順序是契約的一部分：KB 先於 dump、dump 後才 append。
    # 回傳 dump 供呼叫端後續使用（GOAL_SYNTHESIS 復原 / MinimaxEvolver 都要吃它）。
    if tracker.history:
        kb_key = f"{error_cls.value}:{tracker.history[-1].error_signature[:60]}"
        runner._knowledge_base.record_escalation(
            kb_key, list(tracker._tried_strategies), task.step_id
        )
    _dump = runner._save_escalation_dump(
        tracker, task, playbook_path, eval_output, human_hint=human_hint,
    )
    runner._escalation_history.append(_dump)
    return _dump


def handle_convergence_escalation(
    *,
    runner,
    playbook: Playbook,
    playbook_path: str,
    task,
    step_idx: int,
    tracker,
    convergence_trend: str,
    convergence_reasoning: str,
    eval_output: str,
    error_cls,
    step_log: list[str],
    workflow,
    total: int,
    mutation_log: list[str],
    completed_step_ids: set[str],
    step_evolution_counter: dict[str, int],
    alert_ladder: dict | None = None,
) -> PlaybookResult:
    """收斂評估 ESCALATION（原 _impl.py L276-379）"""
    logger.error(
        "=== STATE: ESCALATION | [%s] %s ===",
        task.step_id, convergence_reasoning,
    )
    _dump = record_escalation_and_dump(
        runner, tracker, task, error_cls, playbook_path, eval_output,
        f"收斂評估（trend={convergence_trend}）：{convergence_reasoning}")

    _is_goal_synthesis_esc = (task.step_id == "GOAL_SYNTHESIS")
    if _is_goal_synthesis_esc:
        gs_result = _handle_goal_synthesis_recovery(
            runner=runner, playbook=playbook, playbook_path=playbook_path,
            task=task, step_idx=step_idx, dump=_dump,
            step_log=step_log, workflow=workflow, total=total,
            mutation_log=mutation_log, completed_step_ids=completed_step_ids,
            step_evolution_counter=step_evolution_counter,
            convergence_label="收斂",
            max_retries=None,
            alert_ladder=alert_ladder,
        )
        if gs_result is not None:
            return gs_result

    _step_evo_count = step_evolution_counter.get(task.step_id, 0)
    if _step_evo_count >= 2:
        logger.warning(
            "=== Gap-048 | [%s] 已觸發 %d 次演化（收斂），強制人工介入 ===",
            task.step_id, _step_evo_count,
        )
        runner._notify("AutoClaude — 需要人工介入",
                       f"[{task.step_id}] 已演化 {_step_evo_count} 次仍失敗，請人工分析。")
        return PlaybookResult(
            False, len(step_log), total,
            f"[{task.step_id}] Gap-048: per-step 演化次數已達上限 ({_step_evo_count}次)",
            workflow, step_log,
        )

    _proposal = runner._minimax_evolver.propose_evolution_via_ai(
        playbook, step_idx, _dump, runner._minimax
    )
    if _proposal is None:
        logger.info("=== Gap-016-C | MinimaxEvolver 無提議，回退至規則引擎 ===")
        _proposal = runner._evolver.propose_evolution(
            playbook, step_idx, _dump, runner._escalation_history
        )
    _evolved_path_esc: str | None = None
    _esc_save_ok = True
    if _proposal:
        _evolved_path_esc = runner._evolver.apply_evolution(
            playbook, _proposal, playbook_path, mutation_log=mutation_log
        )
        if _evolved_path_esc:
            step_evolution_counter[task.step_id] = _step_evo_count + 1
            _esc_save_ok = runner._checkpoint_plugin.save_evolution_resume_checkpoint(
                _evolved_path_esc, playbook, step_log, completed_step_ids,
                step_evolution_counter=step_evolution_counter,
                alert_ladder=alert_ladder,
            )
        runner._notify(
            "AutoClaude — Playbook 自動演化（Level 5）",
            f"演化版本: {_evolved_path_esc}\n原因: {_proposal.reasoning}",
        )
    if not _evolved_path_esc:
        runner._notify(
            "AutoClaude — 需要人工介入",
            f"[{task.step_id}] {convergence_reasoning}",
        )
    return PlaybookResult(
        False, len(step_log), total,
        f"[{task.step_id}] {convergence_reasoning}",
        workflow, step_log,
        evolved_playbook_path=_evolved_path_esc,
        evolution_fresh_required=not _esc_save_ok,
    )


def handle_max_retries_escalation(
    *,
    runner,
    playbook: Playbook,
    playbook_path: str,
    task,
    step_idx: int,
    tracker,
    max_retries: int,
    eval_output: str,
    error_cls,
    failure_reason: str,
    step_log: list[str],
    workflow,
    total: int,
    mutation_log: list[str],
    completed_step_ids: set[str],
    step_evolution_counter: dict[str, int],
    alert_ladder: dict | None = None,
) -> PlaybookResult:
    """重試耗盡 ESCALATION（原 _impl.py L420-522）"""
    logger.error(
        "=== STATE: ESCALATION | [%s] 達最大重試次數 %d ===",
        task.step_id, max_retries + 1,
    )
    _dump = record_escalation_and_dump(
        runner, tracker, task, error_cls, playbook_path, eval_output,
        f"已重試 {max_retries + 1} 次仍失敗，請人工分析失敗鏈。")

    _is_goal_synthesis_max = (task.step_id == "GOAL_SYNTHESIS")
    if _is_goal_synthesis_max:
        gs_result = _handle_goal_synthesis_recovery(
            runner=runner, playbook=playbook, playbook_path=playbook_path,
            task=task, step_idx=step_idx, dump=_dump,
            step_log=step_log, workflow=workflow, total=total,
            mutation_log=mutation_log, completed_step_ids=completed_step_ids,
            step_evolution_counter=step_evolution_counter,
            convergence_label="重試耗盡",
            max_retries=max_retries,
            alert_ladder=alert_ladder,
        )
        if gs_result is not None:
            return gs_result

    _step_evo_count_max = step_evolution_counter.get(task.step_id, 0)
    if _step_evo_count_max >= 2:
        logger.warning(
            "=== Gap-048 | [%s] 已觸發 %d 次演化（重試耗盡），強制人工介入 ===",
            task.step_id, _step_evo_count_max,
        )
        runner._notify("AutoClaude — 需要人工介入",
                       f"[{task.step_id}] 已演化 {_step_evo_count_max} 次仍失敗，請人工分析。")
        return PlaybookResult(
            False, len(step_log), total,
            f"[{task.step_id}] Gap-048: per-step 演化次數已達上限 ({_step_evo_count_max}次)",
            workflow, step_log,
        )

    _proposal_max = runner._minimax_evolver.propose_evolution_via_ai(
        playbook, step_idx, _dump, runner._minimax
    )
    if _proposal_max is None:
        logger.info("=== Gap-016-C | MinimaxEvolver 無提議（重試耗盡路徑），回退至規則引擎 ===")
        _proposal_max = runner._evolver.propose_evolution(
            playbook, step_idx, _dump, runner._escalation_history
        )
    _evolved_path_max: str | None = None
    _max_save_ok = True
    if _proposal_max:
        _evolved_path_max = runner._evolver.apply_evolution(
            playbook, _proposal_max, playbook_path, mutation_log=mutation_log
        )
        if _evolved_path_max:
            step_evolution_counter[task.step_id] = _step_evo_count_max + 1
            _max_save_ok = runner._checkpoint_plugin.save_evolution_resume_checkpoint(
                _evolved_path_max, playbook, step_log, completed_step_ids,
                step_evolution_counter=step_evolution_counter,
                alert_ladder=alert_ladder,
            )
        runner._notify(
            "AutoClaude — Playbook 自動演化（Level 5）",
            f"演化版本: {_evolved_path_max}\n原因: {_proposal_max.reasoning}",
        )
    if not _evolved_path_max:
        runner._notify(
            "AutoClaude — 需要人工介入",
            f"步驟 [{task.step_id}] {task.name} 失敗 {max_retries + 1} 次，請檢查日誌。",
        )
    return PlaybookResult(
        False, len(step_log), total,
        f"[{task.step_id}] 重試超限: {failure_reason}",
        workflow, step_log,
        evolved_playbook_path=_evolved_path_max,
        evolution_fresh_required=not _max_save_ok,
    )


def _handle_goal_synthesis_recovery(
    *,
    runner,
    playbook: Playbook,
    playbook_path: str,
    task,
    step_idx: int,
    dump,
    step_log: list[str],
    workflow,
    total: int,
    mutation_log: list[str],
    completed_step_ids: set[str],
    step_evolution_counter: dict[str, int],
    convergence_label: str,
    max_retries: int | None,
    alert_ladder: dict | None = None,
) -> PlaybookResult | None:
    """Gap-044 GOAL_SYNTHESIS 復原（共用於收斂 + 重試耗盡兩路徑）"""
    logger.warning(
        "=== Gap-044 | GOAL_SYNTHESIS ESCALATION（%s）：先嘗試 MinimaxEvolver 修復 ===",
        convergence_label,
    )
    _gs_proposal = runner._minimax_evolver.propose_evolution_via_ai(
        playbook, step_idx, dump, runner._minimax
    )
    if _gs_proposal and _gs_proposal.evolution_type in ("INJECT_STEP", "REVISE_EVALUATOR"):
        _gs_evolved = runner._evolver.apply_evolution(
            playbook, _gs_proposal, playbook_path, mutation_log=mutation_log
        )
        if _gs_evolved:
            if convergence_label == "重試耗盡":
                logger.info(
                    "=== Gap-044 | GOAL_SYNTHESIS 補完步驟已注入（重試耗盡，type=%s），重載演化版 ===",  # noqa: E501
                    _gs_proposal.evolution_type,
                )
                return_msg = "GOAL_SYNTHESIS ESCALATION（重試耗盡）：MinimaxEvolver 已補完步驟"
            else:
                logger.info(
                    "=== Gap-044 | GOAL_SYNTHESIS 補完步驟已注入（type=%s），重載演化版 ===",
                    _gs_proposal.evolution_type,
                )
                return_msg = "GOAL_SYNTHESIS ESCALATION（收斂）：MinimaxEvolver 已補完步驟"
            _gs_save_ok = runner._checkpoint_plugin.save_evolution_resume_checkpoint(
                _gs_evolved, playbook, step_log, completed_step_ids,
                step_evolution_counter=step_evolution_counter,
                alert_ladder=alert_ladder,
            )
            return PlaybookResult(
                False, len(step_log), total, return_msg,
                workflow, step_log,
                evolved_playbook_path=_gs_evolved,
                evolution_fresh_required=not _gs_save_ok,
            )
    logger.error(
        "=== Gap-044 / Gap-035 | MinimaxEvolver 無法修復 GOAL_SYNTHESIS（%s），需人工介入 ===",
        convergence_label,
    )
    if convergence_label == "重試耗盡":
        runner._notify(
            "AutoClaude — 全局目標驗證失敗，需人工介入",
            f"global_goal 在 GOAL_SYNTHESIS 步驟重試 {max_retries + 1} 次後仍無法達成。\n"
            f"缺口分析請查閱 EscalationDump。",
        )
        return PlaybookResult(
            False, len(step_log), total,
            "GOAL_SYNTHESIS ESCALATION：全局目標未達成，需人工介入",
            workflow, step_log,
        )
    runner._notify(
        "AutoClaude — 全局目標驗證失敗，需人工介入",
        "global_goal 在 GOAL_SYNTHESIS 步驟重試多次後仍無法達成。\n"
        "缺口分析請查閱 EscalationDump。",
    )
    return PlaybookResult(
        False, len(step_log), total,
        "GOAL_SYNTHESIS ESCALATION：全局目標未達成（收斂評估），需人工介入",
        workflow, step_log,
    )
