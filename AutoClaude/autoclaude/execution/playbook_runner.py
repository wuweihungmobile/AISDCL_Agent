"""PlaybookRunner — Thin Facade（SD_Improving_04 W3-T12）。

W3-T12 變更（≤ 450 行 LOC 預算達成）：
  - 所有重型實作搬到 _runner_internals._PlaybookRunnerInternalsMixin
  - 本檔僅保留 __init__、run（外層自動恢復迴圈）、M1 shim、backward-compat helper
  - PlaybookRunner 繼承 mixin，行為 100% 等價（測試對內部屬性/方法的引用全部維持）

歷史脈絡：
  - W5（SD_Delete_RunnerImpl）：_runner_impl mixin 完全削除，所有方法內嵌
  - W3-T12（SD_Improving_04）：mixin 方式重新拆分，主檔瘦身至 ≤ 450 行
  - M1 shim（_evaluate / _apply_single_mutation / _validate_batch_compatibility）
    持續保留並通過 tools/check_frozen_surface_shim.py Gate
"""
from __future__ import annotations

import logging
import shutil  # noqa: F401  re-export
import time
from pathlib import Path

from ..core.services.auto_resume import AutoResumeService
from ..decision.minimax_client import MinimaxClient
from ..evolution.minimax_evolver import MinimaxEvolver
from ..evolution.playbook_evolver import PlaybookEvolver
from ..execution.convergence_monitor import ConvergenceMonitor  # noqa: F401  re-export
from ..execution.cross_step_validator import CrossStepStateValidator  # noqa: F401  re-export
from ..execution.error_classifier import ErrorClassifier
from ..execution.workflow_detector import WorkflowDetector
from ..perception.hotkey_handler import HotkeyHandler
from ..perception.pty_wrapper import PtyWrapper  # noqa: F401  re-export

# SD_Improving_05 W3：CheckpointPlugin 吸收 3 中斷路徑（TOKEN_HALT/ESC+F12/ESCALATION dump）+ 演化後 checkpoint  # noqa: E501
from ..plugins.checkpoint import CheckpointPlugin

# SD_Improving_05 W1 Step-1：counter SSOT 遷移 — Runner 直接持有 GotoCounterPlugin
from ..plugins.goto_counter_plugin import GotoCounterPlugin

# SD_Improving_05 W2：TokenGuardPlugin 吸收 5 方法群（M-2 雙寫拔除 + M-7 per-step override）
from ..plugins.token_guard_plugin import TokenGuardPlugin
from ..utils.checkpoint_manager import CheckpointManager
from ..utils.config import AppConfig
from ..utils.knowledge_base import FailureKnowledgeBase
from ..utils.notifier import notify, notify_escalation  # noqa: F401  re-export
from ..utils.token_tracker import TokenUsageLogger, build_patterns

# SD_06 W6-T6-6/T6-7：資料類別（PlaybookState / _StepOutput / PlaybookResult / _MutationResult）
# + 純函式已搬移至 autoclaude.execution.types（_runner_compat.py 物理刪除）。
# SD_07 W4-T4-8：`_prepend_global_goal_brief` shim 已物理拔除（plugin SSOT GoalSynthesisPlugin）。
from .types import (
    PlaybookResult,
    PlaybookState,  # noqa: F401  re-export
    _evaluate_impl,
    _MutationResult,  # noqa: F401  re-export
    _StepOutput,  # noqa: F401  re-export
    _validate_batch_compatibility_impl,
)

logger = logging.getLogger("autoclaude.execution.playbook")


def _pr():
    """延遲取得 playbook_runner 模組（SD_06 W6 從 _runner_internals 搬入）。

    供 strategy 模組（boot_helper / prompt_dispatcher / escalation_dumper /
    steps_orchestrator/_impl / _step_init）lazy 取得 PlaybookRunner module 上
    re-export 的全域屬性（PtyWrapper / shutil / notify_escalation 等），維持
    既有測試 patch 路徑 `autoclaude.execution.playbook_runner.XXX` 相容。
    """
    import sys
    return sys.modules[__name__]


class PlaybookRunner:
    """PlaybookRunner（SD_06 W6 從 mixin 繼承改為直接定義所有 shim 方法）。

    歷史脈絡：
      - W5（SD_Delete_RunnerImpl）：_runner_impl mixin 完全削除，所有方法內嵌
      - W3-T12（SD_Improving_04）：重新拆分為 thin mixin facade
      - **SD_06 W6**：物理刪除 _runner_internals.py + _runner_compat.py；
        所有 17 mixin shim + _pr() 直接放回 PlaybookRunner class；
        資料類別搬至 autoclaude.execution.types；
        PlaybookResult 改為 KernelResult subclass + halt_for_token property
        backward compat。

    本檔包含：
      - __init__：所有屬性建構（測試引用 180+ 處）
      - run：外層自動重載演化版 + auto-resume 迴圈
      - M1 shim 三方法（check_frozen_surface_shim.py Gate）
      - backward-compat shim（_get_correction/_notify；SD_07 W4 已拔除 _prepend_global_goal_brief）
      - 17 個 strategy delegate shim（原 _runner_internals mixin）
    """

    def __init__(
        self,
        config: AppConfig,
        minimax_client: MinimaxClient,
        hotkey_handler: HotkeyHandler,
        dry_run: bool = False,
        *,
        checkpoint_mgr: CheckpointManager | None = None,
        knowledge_base: FailureKnowledgeBase | None = None,
        kernel: AutoResumeService | None = None,
        evolution_approver: object | None = None,
    ):
        self._cfg = config
        self._minimax = minimax_client
        self._hotkey = hotkey_handler
        self._dry_run = dry_run
        # R90／DEF-200-126：此處原有 `executor=` / `evaluator=` / `brain=` 三個 kwarg
        # ＋ 一個 `self._evaluator = Evaluator(...)`，四者**全部只寫不讀**（AST 掃 502 檔，
        # 三筆 port 屬性皆 ctx=Store 零 Load；`._evaluator` 全庫零讀取），已拆除。
        # 真正的 executor DI 住 Kernel 那條路（`main.py` → `build_kernel(executor=…)`）；
        # 本 facade 的執行接縫見 `_execute_prompt` 上方註解。
        # DEF-13-004（L5 signoff 守界）：演化重載核可者 callable(count, evolved_path)->bool。
        # 僅在 cfg.playbook.require_evolution_signoff=True 時生效；None＝未注入。
        self._evolution_approver = evolution_approver

        self._detector = WorkflowDetector()
        self._checkpoint_mgr = checkpoint_mgr or CheckpointManager(config.checkpoint_dir)
        self._error_classifier = ErrorClassifier()
        self._token_logger = TokenUsageLogger(config.log_dir)
        self._token_patterns = build_patterns(config.token_guard.context_patterns)
        self._step_counter = 0
        self._notify_enabled = config.notification.enabled
        # SD_Improving_05 W2 (M-2)：TokenGuardPlugin 為 compact_failure SSOT。
        # SD_07 W4-T4-4：原 `_consecutive_compact_failures` property + setter 已物理拔除；
        # 直接透過 `self._token_guard_plugin.compact_failure_count` 讀取 / `_compact_failure_count` 寫入。  # noqa: E501
        self._token_guard_plugin = TokenGuardPlugin(token_guard_cfg=config.token_guard)
        self._knowledge_base = knowledge_base or FailureKnowledgeBase(
            str(Path(config.checkpoint_dir) / "failure_knowledge_base.jsonl")
        )
        self._evolver = PlaybookEvolver()
        self._minimax_evolver = MinimaxEvolver()
        self._escalation_history: list = []
        self._orchestrator: AutoResumeService | None = kernel
        # SD_Improving_05 W1 Step-1：counter SSOT — GotoCounterPlugin 成為 4 個計數器
        # （goto / inject_before / skip_to / step_evolution）的唯一資料儲存點。
        # _run_steps 內 local 變數 `_goto_counter` 等將為此 plugin 內部 dict 的 alias，
        # 而非獨立 dict 副本，達成 SSOT。CheckpointPlugin 與 _save_*_checkpoint 走
        # plugin.snapshot() 取 deep copy 進行持久化（Gap-042/048/049 跨 session 防護）。
        self._goto_counter_plugin = GotoCounterPlugin(playbook_cfg=config.playbook)
        # SD_Improving_05 W3：CheckpointPlugin 為 3 中斷路徑 + 演化後 checkpoint 的 SSOT；
        # _runner_internals 的 4 個 _save_*_checkpoint 方法將委派至此 plugin（W6 全部拔除）。
        self._checkpoint_plugin = CheckpointPlugin(checkpoint_manager=self._checkpoint_mgr)
        # SD_Improving_05 W4-2/3/4：3 個新 plugin（mixin delegate；W6 完整下沉）
        from ..plugins.fast_path_plugin import FastPathPlugin
        from ..plugins.goal_synthesis_plugin import GoalSynthesisPlugin
        from ..plugins.playbook_persistence_plugin import PlaybookPersistencePlugin
        self._fast_path_plugin = FastPathPlugin()
        # SD_05 W4 三方審查修復：callable resolver 使 cfg.checkpoint_dir 動態變動同步生效
        self._playbook_persistence_plugin = PlaybookPersistencePlugin(
            checkpoint_dir=lambda: self._cfg.checkpoint_dir,
        )
        self._goal_synthesis_plugin = GoalSynthesisPlugin(minimax_client=self._minimax)

    # ──────────────────────────────────────────────────────────────────────
    # M1 shim（check_frozen_surface_shim.py Gate 必須通過）
    # ──────────────────────────────────────────────────────────────────────

    def _evaluate(self, task, output):
        """W5: _runner_compat._evaluate_impl 委派（ANSI strip + regex）。"""
        return _evaluate_impl(task, output)

    def _apply_single_mutation(self, mutation, playbook, *args, **kwargs):
        """W5: orchestrator 路徑 Kernel，其餘 _apply_single_mutation_full() 委派。"""
        if self._orchestrator:
            return self._orchestrator.kernel.mutation_service.apply(
                mutation, playbook, args[2] if len(args) > 2 else 0
            )
        return self._apply_single_mutation_full(mutation, playbook, *args, **kwargs)

    def _validate_batch_compatibility(self, mutations):
        """W5: _runner_compat._validate_batch_compatibility_impl 委派。"""
        if self._orchestrator:
            return self._orchestrator.kernel.mutation_service.validate_batch(mutations)
        return _validate_batch_compatibility_impl(mutations)

    # ──────────────────────────────────────────────────────────────────────
    # backward-compat shim
    # ──────────────────────────────────────────────────────────────────────

    def _get_correction(
        self, task=None, failure_reason=None, eval_output=None, attempt=None, **kwargs
    ):
        """backward compat: minimax.decide_correction 呼叫後 4-tuple 回傳。"""
        try:
            decision = self._minimax.decide_correction(
                task=task,
                task_prompt=task.prompt,
                failure_reason=failure_reason,
                eval_output=eval_output,
                attempt=attempt,
                **kwargs,
            )
        except Exception:
            return None
        if decision is None:
            return None
        return (
            decision.correction_prompt,
            decision.reasoning,
            getattr(decision, "task_goal_summary", None),
            getattr(decision, "step_mutation", None),
        )

    def _notify(self, title: str, message: str) -> None:
        notify(title, message, enabled=self._notify_enabled)

    # ──────────────────────────────────────────────────────────────────────
    # SD_06 W6：原 _runner_internals._PlaybookRunnerInternalsMixin 17 個 shim
    # 全部下沉直接定義；mixin 物理刪除。
    # ──────────────────────────────────────────────────────────────────────

    def _run_steps(self, *a, **kw):
        from .steps_orchestrator import run_steps_impl
        return run_steps_impl(self, *a, **kw)

    def _fast_path_test_file_check(self, eval_output):
        return self._fast_path_plugin._check(eval_output)

    def _handle_token_halt(self, *a, **kw):
        from .halt_handler import handle_token_halt_impl
        return handle_token_halt_impl(self, *a, **kw)

    def _save_escalation_dump(self, *a, **kw):
        from .escalation_dumper import dump_escalation_impl
        return dump_escalation_impl(self, *a, **kw)

    def _persist_mutated_playbook(self, playbook, playbook_path):
        self._playbook_persistence_plugin.persist_mutated_playbook(playbook, playbook_path)

    def _prepend_global_goal(self, prompt, goal):
        return self._goal_synthesis_plugin.prepend_global_goal(prompt, goal)

    @staticmethod
    def _build_achievement_summary(step_log):
        from ..plugins.goal_synthesis_plugin import GoalSynthesisPlugin
        return GoalSynthesisPlugin.build_achievement_summary(step_log)

    def _validate_global_goal_achievement(self, playbook, step_log, goal):
        from ..decision.prompt_builder import build_file_state_snapshot
        snap = build_file_state_snapshot() if not self._dry_run else ""
        return self._goal_synthesis_plugin.validate_global_goal_achievement(
            playbook, step_log, goal, code_state_snapshot=snap)

    def _resolve_start(self, *a, **kw):
        from .boot_helper import resolve_start_impl
        return resolve_start_impl(self, *a, **kw)

    def _wait_for_scheduled_resume(self, *a, **kw):
        from .boot_helper import wait_for_scheduled_resume_impl
        return wait_for_scheduled_resume_impl(self, *a, **kw)

    def _load_playbook(self, path):
        from .boot_helper import load_playbook_impl
        return load_playbook_impl(path)

    def _detect_workflow(self, playbook):
        from .boot_helper import detect_workflow_impl
        return detect_workflow_impl(self, playbook)

    # 🔴 執行接縫住這裡，而它**不是**建構子注入（R90／DEF-200-126）。
    # 實際取得執行器的路徑是模組全域查詢：
    #   execute_prompt_impl → `_pr().PtyWrapper(...)`（prompt_dispatcher.py:44,56）
    #   → sys.modules["autoclaude.execution.playbook_runner"].PtyWrapper
    # ⇒ 測試要換掉執行器一律 `patch("autoclaude.execution.playbook_runner.PtyWrapper", …)`
    #   （全庫既有 26 個站點；共用 fixture＝tests/helpers/fake_pty.py）。
    # 不要在本 class 的 __init__ 再加一個 `executor=` port：那個東西存在過、零讀取、
    # 已於 R90 拆除，而 production 根本不建構本 class（`main.py` 走 Kernel 那條路）。
    def _execute_prompt(self, *a, **kw):
        from .prompt_dispatcher import execute_prompt_impl
        return execute_prompt_impl(self, *a, **kw)

    def _should_compact_now(self, step_out, in_correction_loop, correction_history_len,
                            attempt=0, max_retries=3):
        return self._token_guard_plugin.should_compact(
            token_pct=step_out.peak_token_pct, attempt=attempt, max_retries=max_retries,
            in_correction_loop=in_correction_loop,
            correction_history_len=correction_history_len)

    def _send_compact(self, *a, **kw):
        from .compact_controller import send_compact_impl
        return send_compact_impl(self, *a, **kw)

    def _get_dynamic_compact_threshold(self, attempt, max_retries):
        return self._token_guard_plugin.get_dynamic_compact_threshold(attempt, max_retries)

    def _verify_correction_applied(self, attempt):
        return self._token_guard_plugin.verify_correction_applied(attempt)

    def _apply_single_mutation_full(self, *a, **kw):
        from .mutation_applier import apply_single_mutation_full_impl
        return apply_single_mutation_full_impl(self, *a, **kw)

    def _validate_evaluator_commands(self, playbook):
        from .boot_helper import validate_evaluator_commands_impl
        return validate_evaluator_commands_impl(playbook)

    def _evolution_signoff_granted(self, count: int, evolved_path: str) -> bool:
        """DEF-13-004（L5 signoff 守界）：演化版重載前的人工核可閘。

        require_evolution_signoff=False（預設）→ 永遠放行，維持 Gap-012-D
        自動重載（零退化）。為 True 時 fail-closed：須有 evolution_approver
        且回傳 True 才放行；approver 缺失或拋例外一律 deny（停機不重載）。
        """
        if not self._cfg.playbook.require_evolution_signoff:
            return True
        approver = self._evolution_approver
        if approver is None:
            logger.warning(
                "DEF-13-004 | require_evolution_signoff=True 但未注入 "
                "evolution_approver → fail-closed 拒絕重載 #%d: %s",
                count, evolved_path,
            )
            return False
        try:
            return bool(approver(count, evolved_path))
        except Exception as exc:  # noqa: BLE001 fail-closed：核可者異常一律 deny
            logger.warning(
                "DEF-13-004 | evolution_approver 例外，fail-closed 拒絕重載: %s", exc
            )
            return False

    # ──────────────────────────────────────────────────────────────────────
    # 公開進入點（外層自動恢復迴圈）
    # ──────────────────────────────────────────────────────────────────────

    def run(self, playbook_path: str, fresh: bool = False) -> PlaybookResult:
        """執行 Playbook：含演化版重載 + Token HALT auto-resume 外層迴圈。

        內部委派 self._run_steps（來自 _PlaybookRunnerInternalsMixin）。
        """
        _current_path = playbook_path
        _original_path = playbook_path
        _evolution_count = 0
        _max_evolutions = self._cfg.playbook.max_evolutions

        auto_resume_count = 0
        max_resumes = self._cfg.token_guard.max_auto_resumes

        while True:
            playbook = self._load_playbook(_current_path)

            if not fresh:
                # SD_05 W4-3：delegate 至 PlaybookPersistencePlugin.load_mutated_if_exists
                _checkpoint_exists = (
                    self._checkpoint_mgr.load(_current_path) is not None
                )
                _mutated_path = (
                    self._playbook_persistence_plugin.load_mutated_if_exists(
                        _current_path, checkpoint_exists=_checkpoint_exists,
                    )
                )
                if _mutated_path is not None:
                    try:
                        playbook = self._load_playbook(str(_mutated_path))
                    except Exception as exc:
                        logger.warning("Gap-013-C | 載入 .mutated.yaml 失敗，使用原始 Playbook: %s", exc)  # noqa: E501

            self._validate_evaluator_commands(playbook)
            total = len(playbook.tasks)
            workflow = self._detect_workflow(playbook)

            logger.info(
                "Playbook 啟動 | 專案: %s | 工作流程: %s | 步驟: %d | fresh=%s | path=%s",
                playbook.project, workflow, total, fresh, _current_path,
            )

            start_idx, prior_log, is_first, resume_cp = self._resolve_start(
                _current_path, fresh, playbook
            )
            fresh = False

            self._step_counter = 0
            self._hotkey.register()
            try:
                result = self._run_steps(
                    playbook, _current_path, start_idx,
                    prior_log, is_first, workflow, total,
                    resume_checkpoint=resume_cp,
                )
            finally:
                self._hotkey.unregister()

            if result.evolved_playbook_path and _evolution_count < _max_evolutions:
                # DEF-13-004（L5 signoff 守界）：重載前須過人工核可閘；未獲准則
                # 停機不重載，落入下方終止回報（escalation 已在 result 內）。
                if not self._evolution_signoff_granted(
                    _evolution_count + 1, result.evolved_playbook_path
                ):
                    logger.warning(
                        "=== DEF-13-004 | 演化版重載未獲 signoff，停機不重載: %s ===",
                        result.evolved_playbook_path,
                    )
                    self._notify(
                        "AutoClaude — 演化版重載未獲 signoff（停機）",
                        f"演化版: {result.evolved_playbook_path}",
                    )
                    return result
                _evolution_count += 1
                logger.info(
                    "=== Gap-012-D | Level 5 自動重載演化版 Playbook #%d: %s ===",
                    _evolution_count, result.evolved_playbook_path,
                )
                self._notify(
                    f"AutoClaude — 自動重載演化版 Playbook（第 {_evolution_count} 次）",
                    f"演化版: {result.evolved_playbook_path}",
                )
                _current_path = result.evolved_playbook_path
                fresh = result.evolution_fresh_required
                if fresh:
                    logger.warning(
                        "=== Gap-041 | 演化後 checkpoint 儲存失敗，回退至 fresh=True 重新執行 ==="
                    )
                auto_resume_count = 0
                continue

            if (
                result.halt_for_token
                and self._cfg.token_guard.auto_resume
                and auto_resume_count < max_resumes
            ):
                auto_resume_count += 1
                wait_secs = self._wait_for_scheduled_resume(_current_path, auto_resume_count)
                logger.info(
                    "=== AUTO_RESUME #%d/%d | 等待 %.0fs 後繼續 ===",
                    auto_resume_count, max_resumes, wait_secs,
                )
                if wait_secs > 0:
                    time.sleep(wait_secs)
                continue

            if result.success:
                self._checkpoint_mgr.clear(_current_path)
                # SD_05 W4-3：delegate 至 PlaybookPersistencePlugin.cleanup_mutated_for_paths
                _paths_to_cleanup = [_current_path]
                if _current_path != _original_path:
                    _paths_to_cleanup.append(_original_path)
                self._playbook_persistence_plugin.cleanup_mutated_for_paths(
                    _paths_to_cleanup,
                )
            return result
