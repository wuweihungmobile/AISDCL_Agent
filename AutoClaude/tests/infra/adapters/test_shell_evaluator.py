"""ShellEvaluator 單元測試（Phase 1）。

驗證 IEvaluator 介面契約：
  - regex 比對通過 → (None, "", 0)
  - regex 比對失敗 → (reason, output_tail, 0)
  - regex 比對前自動 strip ANSI
  - evaluator_command 失敗 → (reason, eval_output, exit_code)
  - 與 PlaybookRunner._evaluate 行為等價（Frozen Surface 一致性）
"""
from __future__ import annotations

from autoclaude.infra.adapters import ShellEvaluator
from autoclaude.models.playbook import PlaybookTask
from autoclaude.utils.config import PlaybookConfig


def _task(regex=None, evaluator_command=None):
    return PlaybookTask(
        step_id="T01", name="n", prompt="p",
        expected_output_regex=regex,
        evaluator_command=evaluator_command,
    )


class TestShellEvaluatorRegex:
    def setup_method(self):
        self.ev = ShellEvaluator(PlaybookConfig())

    def test_regex_match_returns_none_reason(self):
        reason, out, code = self.ev.evaluate(_task(r"\[DONE\]"), "output [DONE] here")
        assert reason is None
        assert out == ""
        assert code == 0

    def test_regex_miss_returns_reason(self):
        reason, out, code = self.ev.evaluate(_task(r"\[DONE\]"), "no keyword here")
        assert reason is not None
        assert "DONE" in reason
        assert "no keyword here" in out
        assert code == 0

    def test_regex_strips_ansi_before_match(self):
        reason, *_ = self.ev.evaluate(_task(r"\[INIT_DONE\]"), "\x1b[32m[INIT_DONE]\x1b[0m")
        assert reason is None  # ANSI 已 strip → regex 命中

    def test_no_regex_no_command_passes(self):
        reason, *_ = self.ev.evaluate(_task(None, None), "any output")
        assert reason is None


class TestShellEvaluatorCommand:
    def setup_method(self):
        self.ev = ShellEvaluator(PlaybookConfig())

    def test_command_success_returns_none(self):
        # 使用 echo 一定成功
        task = _task(None, "echo ok")
        reason, *_ = self.ev.evaluate(task, "")
        assert reason is None

    def test_command_failure_returns_reason(self):
        # 使用 false / exit 1 一定失敗
        # Windows 兼容：用 python -c "import sys; sys.exit(1)"
        task = _task(None, 'python -c "import sys; sys.exit(1)"')
        reason, _out, code = self.ev.evaluate(task, "")
        assert reason is not None
        assert "exit=1" in reason or "exit_code=1" in reason or "1" in reason
        assert code == 1


class TestShellEvaluatorBehavioralEquivalence:
    """Phase 1 硬性承諾：與 PlaybookRunner._evaluate 行為等價（Frozen Surface 不變）。"""

    def test_regex_with_command_failure_returns_command_reason(self):
        ev = ShellEvaluator(PlaybookConfig())
        # regex 通過但 command 失敗 → 回傳 command 失敗原因
        task = _task(r"\[OK\]", 'python -c "import sys; sys.exit(2)"')
        reason, _out, code = ev.evaluate(task, "[OK]")
        assert reason is not None
        assert code == 2

    def test_regex_failure_short_circuits_command(self):
        ev = ShellEvaluator(PlaybookConfig())
        # regex 失敗 → 不執行 command（短路），exit_code=0
        task = _task(r"\[OK\]", "echo should-not-run")
        reason, _out, code = ev.evaluate(task, "no keyword")
        assert reason is not None
        assert "OK" in reason
        assert code == 0
