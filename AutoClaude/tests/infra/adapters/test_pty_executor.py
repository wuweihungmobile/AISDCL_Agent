"""PtyExecutor 單元測試（Phase 1）。

驗證 IExecutor 介面契約：
  - PtyExecutor 可建構（介面契約存在）
  - PtyExecutor.execute 簽章正確（不啟動真實 PTY，避免 CI 卡死）
  - 完整 PTY 行為留給整合測試（tests/test_playbook_runner.py）
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from autoclaude.core.ports import ExecutionOutput
from autoclaude.core.ports.executor import ExecutionEventKind
from autoclaude.infra.adapters import PtyExecutor
from autoclaude.utils.config import ClaudeConfig, LoopConfig


class TestPtyExecutorConstruction:
    def test_can_construct(self):
        ex = PtyExecutor(ClaudeConfig(), LoopConfig())
        assert ex is not None

    def test_constructor_accepts_log_dir(self):
        ex = PtyExecutor(ClaudeConfig(), LoopConfig(), log_dir="custom_logs")
        assert ex._log_dir == "custom_logs"

    def test_constructor_accepts_hotkey(self):
        hk = MagicMock()
        ex = PtyExecutor(ClaudeConfig(), LoopConfig(), hotkey=hk)
        assert ex._hotkey is hk


class TestPtyExecutorBehavior:
    """以 mock PtyWrapper 驗證 execute 流程，不啟動真實 PTY。"""

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_execute_collects_lines_until_dead(self, mock_pty_class):
        # arrange：模擬 PtyWrapper 三行輸出後結束
        pty = MagicMock()
        # is_alive 第 1~3 次 True（讀 3 行），第 4 次 False（結束）
        pty.is_alive = True

        responses = ["line1\n", "line2\n", "line3\n", None]
        pty.readline.side_effect = responses

        mock_pty_class.return_value = pty
        ex = PtyExecutor(ClaudeConfig(), LoopConfig())

        out = ex.execute("hi", maintain_context=False, timeout=10, label="t01")

        assert isinstance(out, ExecutionOutput)
        # text 應含全部三行
        assert "line1" in out.text and "line2" in out.text and "line3" in out.text
        pty.start.assert_called_once()
        pty.close.assert_called_once()

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_execute_respects_hotkey(self, mock_pty_class):
        pty = MagicMock()
        pty.is_alive = True
        pty.readline.return_value = "x\n"
        mock_pty_class.return_value = pty

        hk = MagicMock()
        hk.triggered = True   # 立即觸發
        ex = PtyExecutor(ClaudeConfig(), LoopConfig(), hotkey=hk)
        out = ex.execute("hi", timeout=10, label="t01")

        # hotkey 觸發 → completed=False
        assert out.completed is False
        assert out.exit_code == 1
        pty.close.assert_called_once()

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_execute_passes_continue_flag(self, mock_pty_class):
        pty = MagicMock()
        pty.is_alive = False  # 立即結束
        pty.readline.return_value = None
        mock_pty_class.return_value = pty

        cfg = ClaudeConfig()
        ex = PtyExecutor(cfg, LoopConfig())
        ex.execute("prompt", maintain_context=True, timeout=10, label="t02")

        # 驗證 PtyWrapper 收到 --continue（如果有設）
        call = mock_pty_class.call_args
        args = call.kwargs.get("args") or (call.args[1] if len(call.args) >= 2 else [])
        if cfg.continue_flag:
            assert cfg.continue_flag in args
        # -p prompt 必定存在
        assert "-p" in args
        assert "prompt" in args

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_execute_returns_executionoutput_instance(self, mock_pty_class):
        pty = MagicMock()
        pty.is_alive = False
        pty.readline.return_value = None
        mock_pty_class.return_value = pty

        ex = PtyExecutor(ClaudeConfig(), LoopConfig())
        out = ex.execute("p", timeout=10)
        assert isinstance(out, ExecutionOutput)
        assert out.text == ""
        assert out.completed is True
        assert out.exit_code == 0


class TestPtyExecutorJsonTokenPct:
    """W-82-2 / DEF-81-001：PTY 以 --output-format json 接通真實 context% 訊號源。"""

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_pty_json_emits_token_pct_and_unwraps_result(self, mock_pty_class):
        """RTM-82-5：parse 成功 → emit TOKEN_PCT（真值）且 text 還原為 result（非整坨 JSON）。"""
        pty = MagicMock()
        pty.is_alive = True
        json_line = json.dumps({
            "result": "the answer text [DONE]",
            "usage": {
                "input_tokens": 6,
                "cache_read_input_tokens": 21676,
                "cache_creation_input_tokens": 37121,
            },
            "modelUsage": {"claude-opus-4-7[1m]": {"contextWindow": 1000000}},
        })
        pty.readline.side_effect = [json_line + "\n", None]
        mock_pty_class.return_value = pty

        events = []
        ex = PtyExecutor(ClaudeConfig(), LoopConfig())
        out = ex.execute("hi", maintain_context=False, timeout=10,
                         label="t01", on_event=events.append)

        # text 還原為 result → 下游 expected_output_regex 比對對象正確（零退化）
        assert out.text == "the answer text [DONE]"
        # TOKEN_PCT 真值 emit（≈5.88%），且在 COMPLETION 之前
        token_events = [e for e in events if e.kind == ExecutionEventKind.TOKEN_PCT]
        assert len(token_events) == 1
        assert abs(token_events[0].payload["pct"] - 5.8803) < 0.001
        kinds = [e.kind for e in events]
        assert ExecutionEventKind.COMPLETION in kinds
        assert kinds.index(ExecutionEventKind.TOKEN_PCT) < kinds.index(ExecutionEventKind.COMPLETION)

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_pty_json_parse_failure_failloud_fallback(self, mock_pty_class):
        """RTM-82-6：非 JSON 輸出 → fail-loud fallback：text 退回原始、不 emit TOKEN_PCT、不拋。"""
        pty = MagicMock()
        pty.is_alive = True
        pty.readline.side_effect = ["plain answer line1\n", "line2 [DONE]\n", None]
        mock_pty_class.return_value = pty

        events = []
        ex = PtyExecutor(ClaudeConfig(), LoopConfig())
        out = ex.execute("hi", maintain_context=False, timeout=10,
                         label="t02", on_event=events.append)

        assert "plain answer line1" in out.text and "line2 [DONE]" in out.text
        assert not [e for e in events if e.kind == ExecutionEventKind.TOKEN_PCT]

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_pty_json_no_token_pct_when_usage_missing(self, mock_pty_class):
        """parse 成功但無 usage（context% 算不出）→ 不 emit TOKEN_PCT，但 text 仍還原 result。"""
        pty = MagicMock()
        pty.is_alive = True
        json_line = json.dumps({"result": "answer only", "type": "result"})
        pty.readline.side_effect = [json_line + "\n", None]
        mock_pty_class.return_value = pty

        events = []
        ex = PtyExecutor(ClaudeConfig(), LoopConfig())
        out = ex.execute("hi", maintain_context=False, timeout=10, on_event=events.append)

        assert out.text == "answer only"
        assert not [e for e in events if e.kind == ExecutionEventKind.TOKEN_PCT]

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_pty_output_format_in_args_by_default(self, mock_pty_class):
        """RTM-82-7：預設 output_format="json" → args 含 --output-format json。"""
        pty = MagicMock()
        pty.is_alive = False
        pty.readline.return_value = None
        mock_pty_class.return_value = pty

        ex = PtyExecutor(ClaudeConfig(), LoopConfig())
        ex.execute("prompt", timeout=10)

        call = mock_pty_class.call_args
        args = call.kwargs.get("args") or (call.args[1] if len(call.args) >= 2 else [])
        assert "--output-format" in args
        assert args[args.index("--output-format") + 1] == "json"

    @patch("autoclaude.infra.adapters.pty_executor.PtyWrapper")
    def test_pty_output_format_disable_switch(self, mock_pty_class):
        """RTM-82-7：output_format="" → 不加 --output-format、不 parse（向後相容純文字）。"""
        pty = MagicMock()
        pty.is_alive = True
        pty.readline.side_effect = ["plain text\n", None]
        mock_pty_class.return_value = pty

        events = []
        ex = PtyExecutor(ClaudeConfig(output_format=""), LoopConfig())
        out = ex.execute("p", timeout=10, on_event=events.append)

        call = mock_pty_class.call_args
        args = call.kwargs.get("args") or (call.args[1] if len(call.args) >= 2 else [])
        assert "--output-format" not in args
        assert not [e for e in events if e.kind == ExecutionEventKind.TOKEN_PCT]
        assert "plain text" in out.text
