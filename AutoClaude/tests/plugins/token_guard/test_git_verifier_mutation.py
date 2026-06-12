"""git_verifier.py 補強測試 — SD_09 W1 A-1（mutation pilot kill rate ≥ 70%）。

對應 SD_Improving_09 W1 範疇：git_verifier.py 13 個 survived mutation
（id: 53-57, 59-60, 63-68）。

聚焦：
  - subprocess.run 參數精確值（command list、timeout=10、env、cwd）
  - returncode == 0 boundary mutation
  - stdout.strip() 空字串檢查
  - attempt == 0 早返回
  - 警告字串模板插值精確匹配
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch

from autoclaude.plugins.token_guard.git_verifier import (
    _WARNING_TEMPLATE,
    _propagate_trace_env,
    verify_correction_applied,
)


class TestPropagateTraceEnv:
    def test_returns_dict(self):
        """殺 `return dict(os.environ)` → `return os.environ` mutation。"""
        env = _propagate_trace_env()
        assert isinstance(env, dict)

    def test_returns_copy_not_alias(self):
        """殺 alias mutation：必須是 dict copy，後續變更不影響 os.environ。"""
        import os
        env = _propagate_trace_env()
        env["__TEST_MARKER_FAKE__"] = "1"
        assert "__TEST_MARKER_FAKE__" not in os.environ


class TestVerifyCorrectionMutations:
    def test_attempt_zero_exact_check(self):
        """殺 `if attempt == 0` → `<= 0` / `< 0` / `== 1` mutation。"""
        # attempt=0 → 必須 None，不可呼叫 subprocess
        with patch("subprocess.run") as mock_run:
            assert verify_correction_applied(0) is None
            mock_run.assert_not_called()

    def test_attempt_one_does_check(self):
        """殺 attempt 邊界 mutation：attempt=1 必須走 subprocess。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="some diff", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            verify_correction_applied(1)
            assert mock_run.called

    def test_subprocess_command_exact(self):
        """殺 subprocess args 字串 mutation：必須是 `git diff --stat HEAD`。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="x", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            verify_correction_applied(1)
        called_args = mock_run.call_args[0][0]
        assert called_args == ["git", "diff", "--stat", "HEAD"]

    def test_subprocess_capture_and_text_kwargs(self):
        """殺 `capture_output=True` / `text=True` → False mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="x", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            verify_correction_applied(1)
        kwargs = mock_run.call_args.kwargs
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

    def test_subprocess_timeout_default_is_10(self):
        """殺 `timeout: int = 10` default value mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="x", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            verify_correction_applied(1)
        assert mock_run.call_args.kwargs["timeout"] == 10

    def test_subprocess_cwd_default_is_dot(self):
        """殺 `cwd: str = '.'` default value mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="x", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            verify_correction_applied(1)
        assert mock_run.call_args.kwargs["cwd"] == "."

    def test_custom_cwd_and_timeout_propagated(self):
        """殺 keyword propagation mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="x", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            verify_correction_applied(1, cwd="/tmp/repo", timeout=33)
        assert mock_run.call_args.kwargs["cwd"] == "/tmp/repo"
        assert mock_run.call_args.kwargs["timeout"] == 33

    def test_returncode_zero_empty_stdout_warns(self):
        """殺 `result.returncode == 0` → `!= 0` mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(1) is not None

    def test_returncode_zero_whitespace_only_stdout_warns(self):
        """殺 `stdout.strip()` 條件 mutation：只有空白 → 視為空。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="   \n\t  ", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result):
            warning = verify_correction_applied(2)
        assert warning is not None
        assert "attempt 2" in warning

    def test_nonzero_returncode_no_warning(self):
        """殺 `returncode == 0` 反向 mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error",
        )
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(1) is None

    def test_warning_template_contains_critical_phrases(self):
        """殺 `_WARNING_TEMPLATE` 字串字面值刪除 mutation。"""
        assert "{attempt}" in _WARNING_TEMPLATE
        assert "git diff HEAD" in _WARNING_TEMPLATE
        assert "Edit" in _WARNING_TEMPLATE
        assert "Write" in _WARNING_TEMPLATE
        assert "重新執行修正" in _WARNING_TEMPLATE

    def test_warning_attempt_interpolation(self):
        """殺 attempt {attempt} format mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result):
            w = verify_correction_applied(7)
        assert "（attempt 7）" in w

    def test_returns_none_on_filenotfound(self):
        """殺 except FileNotFoundError mutation。"""
        with patch("subprocess.run", side_effect=FileNotFoundError("git missing")):
            assert verify_correction_applied(1) is None

    def test_returns_none_on_timeout(self):
        """殺 except TimeoutExpired mutation。"""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ):
            assert verify_correction_applied(1) is None

    def test_env_passed_to_subprocess(self):
        """殺 `env=_propagate_trace_env()` 參數刪除 mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="x", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result) as mock_run:
            verify_correction_applied(1)
        assert "env" in mock_run.call_args.kwargs
        assert isinstance(mock_run.call_args.kwargs["env"], dict)

    def test_stdout_with_content_no_warning(self):
        """殺 `not result.stdout.strip()` → `result.stdout.strip()` mutation。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="real diff line", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(1) is None
