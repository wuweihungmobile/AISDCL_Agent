# _conditional.py — CONDITIONAL handler（含 shell 安全 + 遞迴 dispatch）。
#
# 對應 SD_06 W2 G2 deferred + SD_05 W4 Gap-046 安全強化。
#
# 🔴 R85：模組說明由 docstring 改為 `#` 註解（`#` 不計 LOC，內容一字未改）；理由同
# execution/evaluator.py 檔頭那一段——把 LOC total 餘裕留給下一個人。
from __future__ import annotations

import logging
import os
import re
import subprocess
from typing import TYPE_CHECKING

from ...utils.trace_context import propagate_to_subprocess_env
from ..evaluator import _NEW_SESSION_KWARGS, kill_process_tree, portability_note, unattended_refusal

if TYPE_CHECKING:
    from ...models.step_mutation import StepMutation
    from ..types import _MutationResult
    from ._dispatcher import MutationCtx

logger = logging.getLogger("autoclaude.execution.playbook")

_SHELL_TRUE_COND_WHITELIST = re.compile(r'^[\w\s\-./=:!"\']+$')


def handle_conditional(ctx: MutationCtx, mutation: StepMutation, result: _MutationResult) -> None:
    # 依 condition_evaluator 的 exit code 選擇 true/false 分支並遞迴 dispatch。
    #
    # 跨平台注意（對稱 execution/evaluator.py Evaluator.run 警語）：condition_evaluator
    # 以 subprocess.run(shell=True) 執行，實際呼叫的是「作業系統原生殼」——Windows 為
    # cmd.exe，POSIX 為 /bin/sh，而非固定的 bash。因此 condition_evaluator 必須寫成
    # 可攜指令（如 `python -c "..."`），避免 POSIX 專屬語法（test -f、grep 等 shell
    # builtin/GNU 工具），否則在 Windows 上會被 cmd.exe 解讀出非預期結果，而非清楚的
    # 「找不到指令」失敗。（`&&`/`||` 則已被上方 Gap-046 _SHELL_TRUE_COND_WHITELIST 擋下。）
    #
    # 🔴 R85（AC-(a)）：說明由 docstring 改為 `#` 註解（`#` 不計 LOC），內容一字未改。
    # 本函式是 autoclaude/ 內**第二個** `shell=True` 執行面（第一個是 Evaluator.run）；
    # 兩個都接同一道無人看管能力閘，否則關掉一扇門只會讓人走另一扇。
    if not mutation.condition_evaluator:
        logger.warning("=== Gap-021 | CONDITIONAL 缺少 condition_evaluator，略過 ===")
        return
    _denied = unattended_refusal(mutation.condition_evaluator)
    if _denied:
        logger.warning("=== R85 AC-(a) | %s，略過 ===", _denied)
        return
    # R85 P7：可攜性診斷。刻意擺在 Gap-046 白名單**之前**——被白名單擋下時本函式是
    # 靜默 `return`（兩個分支都不跑），那正是最需要一句話說明「為什麼什麼都沒發生」
    # 的時刻。回傳值刻意忽略：這道是診斷不是閘，不改控制流。
    portability_note(mutation.condition_evaluator)
    if not _SHELL_TRUE_COND_WHITELIST.match(mutation.condition_evaluator.strip()):
        logger.warning(
            "=== Gap-046 | CONDITIONAL evaluator 包含不安全字符，略過: %s ===",
            mutation.condition_evaluator[:80],
        )
        return
    try:
        # R68：與 Evaluator.run 同一缺陷類別（shell=True + timeout 逾時只殺直接
        # 子行程、孫行程變孤兒續跑）。共用 evaluator.kill_process_tree 收殺路徑，
        # 不各寫一份。
        cond_proc = subprocess.Popen(
            mutation.condition_evaluator,
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=propagate_to_subprocess_env(dict(os.environ)),
            **_NEW_SESSION_KWARGS,
        )
        try:
            cond_proc.communicate(
                timeout=ctx.runner._cfg.playbook.conditional_evaluator_timeout_seconds
            )
        except subprocess.TimeoutExpired:
            kill_process_tree(cond_proc)
            try:
                cond_proc.communicate(timeout=5)
            except Exception:
                pass
            raise
        cond_exit = cond_proc.returncode
    except Exception as exc:
        logger.warning("=== Gap-021 | CONDITIONAL evaluator 執行失敗: %s，視為 false ===", exc)
        cond_exit = 1
    branch = mutation.true_mutation if cond_exit == 0 else mutation.false_mutation
    logger.info(
        "=== Gap-021 | CONDITIONAL exit=%d，選擇分支: %s ===",
        cond_exit, "true_mutation" if cond_exit == 0 else "false_mutation",
    )
    if branch is None:
        return
    branch_result = ctx.runner._apply_single_mutation(
        branch, ctx.playbook, ctx.playbook_path, ctx.task, ctx.step_idx,
        ctx.step_log, ctx.mutation_log, ctx.attempt,
        ctx.inject_before_counter, ctx.goto_counter, ctx.skip_to_counter,
        ctx.workflow, ctx.total, ctx.tracker, ctx.eval_output,
    )
    result.should_break = branch_result.should_break
    result.inject_before_pending = branch_result.inject_before_pending
    result.goto_target_idx = branch_result.goto_target_idx
    result.early_return = branch_result.early_return
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] CONDITIONAL: exit={cond_exit} → "
        f"{'true' if cond_exit == 0 else 'false'} branch ({branch.mutation_type})"
    )
