"""prompt_dispatcher.py — _execute_prompt 拆解承接模組（SD_06 W2-T2-5 / T2-6）。

對應：
  - SD_Improving_06.md v1.2 §4 W2-3（≤ 100 LOC，下沉 ExecutorPort）
  - SD06_Execution_Guide.md W2 T2-5 / T2-6

設計原則：
  - `execute_prompt_impl(runner, ...)` 為純函式，runner 提供 _cfg / _hotkey / _token_patterns
    / _token_guard_plugin 等屬性
  - PTY 透過 `_pr().PtyWrapper` 動態查詢（mixin patch path 相容；T2-2 完成後可改注入）
  - token watch 委派 `runner._token_guard_plugin.observe_token_line`（SD_05 W2-1e）
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils.logger import _sanitize_log_filename
from ..utils.token_tracker import extract_context_pct
from .types import _StepOutput

if TYPE_CHECKING:
    from .playbook_runner import PlaybookRunner

logger = logging.getLogger("autoclaude.execution.playbook")


def execute_prompt_impl(
    runner: PlaybookRunner,
    prompt: str,
    maintain_context: bool,
    timeout: int,
    step_label: str,
) -> _StepOutput:
    """SD_06 W2-T2-6：_execute_prompt 全文下沉。

    從 mixin 完整搬出 — 包含 PTY 啟動、token watch、deadline 控制、hotkey 中斷偵測。
    runner 提供：_cfg / _hotkey / _token_patterns / _token_guard_plugin。
    """
    # late import 以保留既有 patch 路徑 `_pr().PtyWrapper`（SD_06 W6：_pr 改自 playbook_runner）
    from .playbook_runner import _pr

    cfg = runner._cfg
    args = list(cfg.claude.extra_args)
    if maintain_context and cfg.claude.continue_flag:
        args.append(cfg.claude.continue_flag)
    args += ["-p", prompt]

    # R43 SD 一審（DEF-101-352 同構第二例）：step_label 源自 `f"{task.step_id}_attempt{n}"`
    # （task.step_id 為 YAML 可控字串），未淨化直接組檔名可逃出 log_dir；比照
    # pty_executor.py 同款修法委派 SSOT（該函式對空字串已回退 "untitled"）。
    log_path = Path(cfg.log_dir) / f"playbook_{_sanitize_log_filename(step_label)}.log"
    pty = _pr().PtyWrapper(
        command=cfg.claude.command,
        args=args,
        auth_patterns=cfg.loop.auth_patterns,
        auth_response=cfg.loop.auth_response,
        raw_log_path=log_path,
        encoding=cfg.claude.encoding,
    )

    output_lines: list[str] = []
    peak_pct = 0.0
    should_compact = False
    should_halt = False
    deadline = time.monotonic() + timeout
    pty.start()

    try:
        while time.monotonic() < deadline:
            if runner._hotkey.triggered:
                break
            if not pty.is_alive:
                break
            line = pty.readline(timeout=cfg.loop.poll_interval_seconds)
            if line is None:
                break
            if not line:
                continue

            output_lines.append(line)
            logger.debug("[claude] %s", line.rstrip())

            if cfg.token_guard.enabled:
                pct = extract_context_pct(line, runner._token_patterns)
                _prev_peak = peak_pct
                peak_pct, should_compact, should_halt = (
                    runner._token_guard_plugin.observe_token_line(
                        pct=pct, peak_pct=peak_pct,
                        triggered_compact=should_compact, triggered_halt=should_halt,
                    )
                )
                if peak_pct > _prev_peak:
                    logger.debug("Context 使用率偵測: %.1f%%", peak_pct)
                    if should_halt and not (_prev_peak >= cfg.token_guard.halt_threshold_pct):
                        logger.warning(
                            "Context %.0f%% 達 halt 門檻 %.0f%%，步驟完成後將儲存 checkpoint",
                            peak_pct, cfg.token_guard.halt_threshold_pct,
                        )
                    elif should_compact and not (
                        _prev_peak >= cfg.token_guard.compact_threshold_pct
                    ):
                        logger.info(
                            "Context %.0f%% 達 compact 門檻 %.0f%%，步驟完成後觸發 /compact",
                            peak_pct, cfg.token_guard.compact_threshold_pct,
                        )
    finally:
        pty.close()

    return _StepOutput(
        text="".join(output_lines),
        peak_token_pct=peak_pct,
        triggered_compact=should_compact and not should_halt,
        triggered_halt=should_halt,
    )
