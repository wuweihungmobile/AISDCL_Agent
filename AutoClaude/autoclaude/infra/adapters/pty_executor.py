"""PtyExecutor — IExecutor 的真實 PTY 實作（Phase 1）。

職責：
  - 建構 PtyWrapper 執行 Claude Code CLI
  - 收集輸出文字並回傳 ExecutionOutput
  - 不含 token guard（由 Phase 3 TokenGuardPlugin 透過 ON_TOKEN_USAGE 處理）
  - 不含 hotkey 檢查（由 Phase 3 HotkeyPlugin 透過 PRE_ATTEMPT 處理）

注意：
  - 此 Adapter 在 Phase 1 / Phase 2 期間「並存」於 PlaybookRunner._execute_prompt 之側
  - 真正取代 _execute_prompt 是 Phase 4 Facade 切換時
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from ...core.ports.executor import (
    ExecutionEvent,
    ExecutionEventCallback,
    ExecutionEventKind,
    ExecutionOutput,
)
from ...perception.pty_wrapper import CmdLineTooLongError, PtyWrapper
from ...utils.config import ClaudeConfig, LoopConfig
from ...utils.logger import _sanitize_log_filename
from ...utils.token_tracker import context_pct_from_claude_json

logger = logging.getLogger("autoclaude.infra.adapters.pty_executor")


class PtyExecutor:
    """以 PtyWrapper 包裝 Claude Code CLI 執行。"""

    def __init__(
        self,
        claude_cfg: ClaudeConfig,
        loop_cfg: LoopConfig,
        log_dir: str = "logs",
        hotkey: object | None = None,
    ):
        self._claude = claude_cfg
        self._loop = loop_cfg
        self._log_dir = log_dir
        self._hotkey = hotkey   # 可選，提供時於 readline 期間檢查中斷
        # SD_Improving_06 W1 T1-2：interrupt 旗標（send_interrupt 觸發；execute 迴圈檢查）
        self._interrupt_requested: bool = False
        self._interrupt_reason: str = ""

    def send_interrupt(self, reason: str = "") -> bool:
        """請求中斷下一個 readline 輪詢（ADR-SD06-001 §6.4）。

        Phase 1：標記旗標；execute 主迴圈下一輪 poll 時偵測並結束。
        Phase 2+：將改由 Coordinator 訂閱 ON_INTERRUPT_REQUEST event 後呼叫。
        """
        self._interrupt_requested = True
        self._interrupt_reason = reason
        return True

    def execute(
        self,
        prompt: str,
        *,
        maintain_context: bool = True,
        timeout: int = 600,
        label: str = "",
        on_event: ExecutionEventCallback | None = None,
    ) -> ExecutionOutput:
        args = list(self._claude.extra_args)
        if maintain_context and self._claude.continue_flag:
            args.append(self._claude.continue_flag)
        # W-82-1 / DEF-81-001：以 --output-format json 啟動，使結束後可從結構化 usage
        # 推算真實 context%（純文字模式無從取得）。output_format="" 則退回純文字舊行為。
        output_format = self._claude.output_format
        if output_format:
            args += ["--output-format", output_format]
        args += ["-p", prompt]

        # R43 Scan-A（DEF-101-352）：label 源自 PlaybookTask.step_id（YAML 可控字串），
        # 未淨化直接組檔名可逃出 log_dir（如 step_id="../../evil"）；比照 SSOT
        # utils/logger.py::_sanitize_log_filename（該函式對空字串已回退為 "untitled"）。
        log_path = Path(self._log_dir) / f"playbook_{_sanitize_log_filename(label)}.log"
        pty = PtyWrapper(
            command=self._claude.command,
            args=args,
            auth_patterns=self._loop.auth_patterns,
            auth_response=self._loop.auth_response,
            raw_log_path=log_path,
            encoding=self._claude.encoding,
        )

        output_lines: list[str] = []
        deadline = time.monotonic() + timeout
        completed = True
        # SD_Improving_06 W1 T1-2：重置 interrupt 旗標 + event sequence
        self._interrupt_requested = False
        self._interrupt_reason = ""
        event_seq = 0
        # R69：啟動期長度守門（Windows .cmd shim 超長 prompt）降級為「單步失敗」訊號
        # ——completed=False + 非零 exit_code，交由上游 CORRECTION／ESCALATION 承接；
        # 讓例外原樣往上炸＝整場 run 崩潰、其餘步驟全不執行（R68 落地時的實況）。
        try:
            pty.start()
        except CmdLineTooLongError as exc:
            return ExecutionOutput(f"[EXEC_START_FAILED] {exc}", exit_code=1, completed=False)
        try:
            while time.monotonic() < deadline:
                if self._interrupt_requested:
                    completed = False
                    break
                if self._hotkey is not None and getattr(self._hotkey, "triggered", False):
                    completed = False
                    break
                if not pty.is_alive:
                    break
                line = pty.readline(timeout=self._loop.poll_interval_seconds)
                if line is None:
                    break
                if not line:
                    continue
                output_lines.append(line)
                if on_event is not None:
                    event_seq += 1
                    try:
                        on_event(ExecutionEvent(
                            kind=ExecutionEventKind.PARTIAL_OUTPUT,
                            payload={"text": line},
                            sequence=event_seq,
                        ))
                    except Exception:
                        # adapter 不可因 callback 失敗影響執行（callback 邊界錯誤吞掉）
                        pass
        finally:
            pty.close()

        if time.monotonic() >= deadline:
            completed = False

        # W-82-1 / DEF-81-001：json 模式解析結構化用量 → 真實 context%（emit TOKEN_PCT 於
        # COMPLETION 之前），並還原 result 作答案文字（保下游 expected_output_regex 比對零退化）。
        # parse 失敗 → fail-loud warn + text 退回原始輸出（＝純文字舊行為，零退化 fallback）。
        raw_text = "".join(output_lines)
        text = raw_text
        if output_format == "json" and raw_text.strip():
            parsed = self._try_parse_json(raw_text)
            if parsed is not None:
                result = parsed.get("result")
                if isinstance(result, str):
                    text = result
                pct = context_pct_from_claude_json(parsed)
                if pct is not None and on_event is not None:
                    event_seq += 1
                    try:
                        on_event(ExecutionEvent(
                            kind=ExecutionEventKind.TOKEN_PCT,
                            payload={"pct": pct},
                            sequence=event_seq,
                        ))
                    except Exception:
                        pass
            else:
                logger.warning(
                    "PtyExecutor: --output-format json 輸出無法解析為 JSON（label=%s），"
                    "token%% 訊號源未產出，text 退回原始輸出（fail-loud，DEF-81-001）",
                    label or "untitled",
                )

        if on_event is not None:
            event_seq += 1
            try:
                on_event(ExecutionEvent(
                    kind=ExecutionEventKind.COMPLETION,
                    payload={
                        "exit_code": 0 if completed else 1,
                        "completed": completed,
                        "text_len": len(text),
                    },
                    sequence=event_seq,
                ))
            except Exception:
                pass

        return ExecutionOutput(
            text=text,
            exit_code=0 if completed else 1,
            completed=completed,
        )

    @staticmethod
    def _try_parse_json(raw: str) -> dict | None:
        """容錯解析 claude --output-format json 輸出為 dict；失敗回 None（不拋）。

        claude -p --output-format json 為 single-result：整段 stdout 即一個 JSON object。
        PTY 可能夾雜授權提示/雜訊行，故先試整段、再退而試最後一個非空行（json 通常在末行）。
        """
        stripped = raw.strip()
        candidates = [stripped]
        lines = [ln for ln in stripped.splitlines() if ln.strip()]
        if lines:
            candidates.append(lines[-1])
        for candidate in candidates:
            try:
                obj = json.loads(candidate)
            except (ValueError, TypeError):
                continue
            if isinstance(obj, dict):
                return obj
        return None
