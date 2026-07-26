"""_simple_mutations.py — REVISE_CURRENT / INJECT_AFTER / DELETE_STEP / SKIP_TO handlers.

對應 SD_06 W2 G2 deferred：簡單變異（不含 escalation/evolution 觸發路徑）。
"""
from __future__ import annotations

import base64
import logging
import sys
from typing import TYPE_CHECKING

from ...models.playbook import PlaybookTask

if TYPE_CHECKING:
    from ...models.step_mutation import StepMutation
    from ..types import _MutationResult
    from ._dispatcher import MutationCtx

logger = logging.getLogger("autoclaude.execution.playbook")

# R52 P2 修復：INJECT_AFTER / INJECT_BEFORE 未提供 new_step_evaluator_command 時的
# 兜底來源碼——以 git diff --stat HEAD 是否存在非空行判定「是否有實際變更」，
# 語意對齊原本的 POSIX-only `git diff --stat HEAD | grep -c .`。
#
# R52 round 2 修復：此字串於子行程以 exec() 動態組譯執行，其內的 subprocess.run(...,
# text=True) 若未顯式指定 encoding，會依 locale.getpreferredencoding() 隱式解碼
# git 輸出——在 Windows zh-TW（cp950）環境下，若 git diff --stat 輸出含本 repo 大量
# 存在的非 ASCII（中文）檔名，會拋 UnicodeDecodeError 讓此「為可攜到 Windows 而新寫」
# 的兜底程式碼自己以未捕捉例外崩潰。因位於字串字面值內，供另一子行程動態 exec()，
# 本檔案的 AST 掃描器（tools/tests/test_subprocess_encoding_hygiene.py）結構性看不到
# 此呼叫，故需與 evaluator.py／Evaluator.run() 對其自身 subprocess.run 呼叫一致，
# 顯式指定 encoding="utf-8", errors="replace"。
_FALLBACK_EVALUATOR_SRC = (
    "import subprocess, sys\n"
    "out = subprocess.run(['git', 'diff', '--stat', 'HEAD'], "
    "capture_output=True, text=True, encoding='utf-8', errors='replace').stdout\n"
    "sys.exit(0 if any(line.strip() for line in out.splitlines()) else 1)\n"
)


def _default_fallback_evaluator_command() -> str:
    """INJECT_AFTER / INJECT_BEFORE 未提供 evaluator_command 時的可攜兜底指令。

    原字面值 `git diff --stat HEAD | grep -c .` 依賴 POSIX-only 管線；
    evaluator_command 經 `subprocess.run(shell=True)` 交給平台原生殼執行
    （Windows 為 cmd.exe），改以 base64 包裝的 Python 一行式重現同一語意
    （HEAD 存在非空 diff 才視為成功），不含 shell 管線，跨平台可執行。

    已知限制（文件化非修復，R52 P3）：以 `sys.executable`（編譯時絕對路徑）
    組字串，隨 mutated YAML 跨行程/環境重新載入執行時可能路徑已不存在
    （與 sdd_to_playbook_adapter.py 拒絕同款寫法同一風險類別）；此呼叫路徑
    （PlaybookRunner 直連模式）W6 已拔除、目前無非測試呼叫點，暫不可觸發，
    未來重新接線時需改為執行期嘗試 `python3`/`python` 而非編譯期寫死路徑。
    """
    payload = base64.b64encode(_FALLBACK_EVALUATOR_SRC.encode("utf-8")).decode("ascii")
    python_bin = sys.executable or "python3"
    return f'"{python_bin}" -c "import base64; exec(base64.b64decode(\'{payload}\'))"'


def handle_revise_current(
    ctx: MutationCtx, mutation: StepMutation, result: _MutationResult
) -> None:
    ctx.task.prompt = mutation.revised_prompt
    logger.info("=== Gap-011-B | REVISE_CURRENT 步驟 %s prompt 已更新 ===", ctx.task.step_id)
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] REVISE_CURRENT: 步驟 {ctx.task.step_id} prompt 已更新"
    )
    ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)
    result.clear_goal_summary = True


def handle_inject_after(ctx: MutationCtx, mutation: StepMutation, result: _MutationResult) -> None:
    new_task = PlaybookTask(
        step_id=mutation.new_step_id or f"{ctx.task.step_id}_INJECT",
        name=mutation.new_step_name or f"{ctx.task.name}（注入步驟）",
        prompt=mutation.new_step_prompt,
        expected_output_regex=mutation.new_step_expected_regex,
        evaluator_command=(
            mutation.new_step_evaluator_command or _default_fallback_evaluator_command()
        ),
        max_retries=mutation.new_step_max_retries,
    )
    ctx.playbook.tasks.insert(ctx.step_idx + 1, new_task)
    logger.info(
        "=== Gap-011-B / Gap-036 | INJECT_AFTER 插入步驟 %s 於 %s 後（evaluator=%s）===",
        new_task.step_id, ctx.task.step_id,
        new_task.evaluator_command[:60] if new_task.evaluator_command else "None",
    )
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] INJECT_AFTER: 插入步驟 {new_task.step_id} "
        f"於 {ctx.task.step_id} 後"
    )
    ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)


def handle_delete_step(ctx: MutationCtx, mutation: StepMutation, result: _MutationResult) -> None:
    del_id = mutation.delete_step_id
    del_idx = next(
        (i for i, t in enumerate(ctx.playbook.tasks) if t.step_id == del_id), None,
    )
    if del_idx is not None and del_idx > ctx.step_idx:
        del ctx.playbook.tasks[del_idx]
        ctx.step_log.append(f"[DELETED] {del_id}（Minimax 判定為冗餘）")
        logger.info("=== Gap-012-C | DELETE_STEP 刪除步驟 %s（原 idx=%d）===", del_id, del_idx)
        ctx.mutation_log.append(f"[attempt {ctx.attempt}] DELETE_STEP: 刪除步驟 {del_id}")
        ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)
    else:
        logger.warning(
            "=== Gap-012-C | 刪除目標 %s 不存在或不在當前步驟之後（idx=%s），忽略 ===",
            del_id, del_idx,
        )


def handle_skip_to(ctx: MutationCtx, mutation: StepMutation, result: _MutationResult) -> None:
    skip_id = mutation.skip_to_step_id
    skip_target_idx = next(
        (i for i, t in enumerate(ctx.playbook.tasks) if t.step_id == skip_id), None,
    )
    if skip_target_idx is None:
        logger.warning("=== Gap-017-C | SKIP_TO 目標步驟 %s 不存在，忽略 ===", skip_id)
        return
    if skip_target_idx <= ctx.step_idx:
        logger.warning(
            "=== Gap-017-C | 禁止 SKIP_TO 向後（target=%s idx=%d <= current=%d），忽略 ===",
            skip_id, skip_target_idx, ctx.step_idx,
        )
        return
    if ctx.skip_to_counter.get(ctx.task.step_id, 0) >= 1:
        logger.warning(
            "=== Gap-017-C | 步驟 %s 的 SKIP_TO 已執行 1 次，防護限制觸發，忽略 ===",
            ctx.task.step_id,
        )
        return
    ctx.skip_to_counter[ctx.task.step_id] = ctx.skip_to_counter.get(ctx.task.step_id, 0) + 1
    for skipped in ctx.playbook.tasks[ctx.step_idx + 1:skip_target_idx]:
        note = (
            f"[SKIPPED] {skipped.step_id}（Gap-017：Minimax 判定為已隱性完成"
            + (f"，原因：{mutation.skip_reason}" if mutation.skip_reason else "")
            + "）"
        )
        ctx.step_log.append(note)
    result.goto_target_idx = skip_target_idx
    logger.info(
        "=== Gap-017-C | SKIP_TO 跳轉至 %s（idx=%d），跳過 %d 個步驟 ===",
        skip_id, skip_target_idx, skip_target_idx - ctx.step_idx - 1,
    )
    ctx.mutation_log.append(
        f"[attempt {ctx.attempt}] SKIP_TO: 跳轉至 {skip_id}，"
        f"跳過步驟 {[t.step_id for t in ctx.playbook.tasks[ctx.step_idx + 1:skip_target_idx]]}"
    )
    ctx.runner._persist_mutated_playbook(ctx.playbook, ctx.playbook_path)
    result.should_break = True
