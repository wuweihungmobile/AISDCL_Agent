"""PtyExecutor 單元測試（Phase 1）。

驗證 IExecutor 介面契約：
  - PtyExecutor 可建構（介面契約存在）
  - PtyExecutor.execute 簽章正確（不啟動真實 PTY，避免 CI 卡死）
  - 完整 PTY 行為留給整合測試（tests/test_playbook_runner.py）
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from autoclaude.core.ports import ExecutionOutput
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
