"""git_verifier.py 單元測試（SD_07 W3-T3-10）。

對應子模組：autoclaude/plugins/token_guard/git_verifier.py
測試 API：verify_correction_applied (Gap-009-C)

目標：≥ 5 case + coverage 100%
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch

from autoclaude.plugins.token_guard.git_verifier import verify_correction_applied


class TestVerifyCorrectionApplied:
    def test_attempt_zero_returns_none(self):
        """attempt=0 不檢查 git diff。"""
        assert verify_correction_applied(0) is None

    def test_empty_diff_returns_warning(self):
        """git diff --stat HEAD 空輸出 → 警告字串。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result):
            warning = verify_correction_applied(1)
        assert warning is not None
        assert "attempt 1" in warning
        assert "git diff HEAD 為空" in warning

    def test_non_empty_diff_returns_none(self):
        """git diff --stat HEAD 有輸出（已修改檔案）→ None。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout=" autoclaude/foo.py | 5 ++++-\n 1 file changed", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(2) is None

    def test_git_not_found_returns_none(self):
        """git 不存在 → 安靜返回 None（不阻塞）。"""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert verify_correction_applied(1) is None

    def test_timeout_returns_none(self):
        """git diff timeout → 安靜返回 None。"""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ):
            assert verify_correction_applied(1) is None

    def test_warning_includes_attempt_number(self):
        """警告字串應顯示正確 attempt 編號。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="   \n  \t  ", stderr="",
        )
        with patch("subprocess.run", return_value=fake_result):
            warning = verify_correction_applied(3)
        assert warning is not None
        assert "attempt 3" in warning

    def test_non_zero_returncode_returns_none(self):
        """git diff returncode != 0（如 repo 不存在）→ 不發警告。"""
        fake_result = subprocess.CompletedProcess(
            args=[], returncode=128, stdout="", stderr="not a git repo",
        )
        with patch("subprocess.run", return_value=fake_result):
            assert verify_correction_applied(1) is None
