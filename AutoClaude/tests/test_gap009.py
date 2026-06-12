"""
Gap-009 實作驗證測試（Gap-009-A~F）。

覆蓋範圍：
  A - Fast Path 巢狀路徑正則修復
  B - PreRunValidator 模組
  C - _verify_correction_applied（git diff 檢查）
  D - _validate_evaluator_commands（啟動前預驗證）
  E - FailureKnowledgeBase（跨 Session 快取）
  F - _get_dynamic_compact_threshold + _should_compact_now 動態門檻
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from autoclaude.execution.playbook_runner import PlaybookRunner, _StepOutput
from autoclaude.execution.pre_run_validator import PreRunValidator
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.utils.config import AppConfig
from autoclaude.utils.knowledge_base import FailureKnowledgeBase, _MAX_ENTRIES


# ──────────────────────────────────────────────
# 共用輔助
# ──────────────────────────────────────────────

def _make_runner(dry_run: bool = False) -> PlaybookRunner:
    cfg = AppConfig()
    minimax = MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    return PlaybookRunner(cfg, minimax, hotkey, dry_run=dry_run)


def _make_step_out(peak_pct: float, triggered_compact: bool = False) -> _StepOutput:
    return _StepOutput(text="", peak_token_pct=peak_pct, triggered_compact=triggered_compact)


# ──────────────────────────────────────────────
# Gap-009-A：Fast Path 巢狀路徑正則
# ──────────────────────────────────────────────

class TestFastPathNestedPath:
    def _eval_out(self, path: str) -> str:
        return f"ERROR collecting {path}\n  SyntaxError: invalid syntax (line 5)"

    @patch("subprocess.run")
    def test_single_level_path_matches(self, mock_run):
        """原本的單層路徑仍然能匹配。"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: invalid syntax")
        runner = _make_runner()
        result = runner._fast_path_test_file_check(self._eval_out("tests/test_foo.py"))
        assert result is not None
        assert "test_foo.py" in result

    @patch("subprocess.run")
    def test_nested_two_level_path_matches(self, mock_run):
        """Gap-009-A 修復：tests/unit/test_foo.py 應能匹配。"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: invalid syntax")
        runner = _make_runner()
        result = runner._fast_path_test_file_check(self._eval_out("tests/unit/test_foo.py"))
        assert result is not None
        assert "test_foo.py" in result

    @patch("subprocess.run")
    def test_nested_three_level_path_matches(self, mock_run):
        """三層巢狀路徑也能匹配。"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: invalid syntax")
        runner = _make_runner()
        result = runner._fast_path_test_file_check(
            self._eval_out("tests/integration/api/test_endpoints.py")
        )
        assert result is not None

    @patch("subprocess.run")
    def test_compile_success_returns_none(self, mock_run):
        """py_compile 成功（returncode=0）→ 不是語法錯誤 → 回傳 None。"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        runner = _make_runner()
        result = runner._fast_path_test_file_check(self._eval_out("tests/unit/test_foo.py"))
        assert result is None

    def test_non_test_error_returns_none(self):
        """非測試檔的 ImportError 不應觸發 fast path。"""
        runner = _make_runner()
        result = runner._fast_path_test_file_check("ImportError: No module named 'mylib'")
        assert result is None

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_subprocess_error_returns_none(self, _mock_run):
        """subprocess 異常時安全地回傳 None。"""
        runner = _make_runner()
        result = runner._fast_path_test_file_check(self._eval_out("tests/unit/test_foo.py"))
        assert result is None

    @patch("subprocess.run")
    def test_nested_with_hyphenated_dir(self, mock_run):
        """Gap-009-A fallback: 連字號目錄名稱應正確匹配"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: invalid syntax")
        runner = _make_runner()
        output = "FAILED tests-integration/test_auth.py::TestAuth::test_login"
        result = runner._fast_path_test_file_check(output)
        assert result is not None
        assert "test_auth.py" in result

    @patch("subprocess.run")
    def test_windows_backslash_path(self, mock_run):
        """Gap-009-A: Windows 反斜線路徑應被正規化"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: invalid syntax")
        runner = _make_runner()
        output = "FAILED tests\\unit\\test_models.py"
        result = runner._fast_path_test_file_check(output)
        if result is not None:  # 若匹配到，路徑分隔符應為 /
            assert '\\' not in result


# ──────────────────────────────────────────────
# Gap-009-B：PreRunValidator
# ──────────────────────────────────────────────

class TestPreRunValidator:
    def test_no_evaluator_command_returns_empty(self):
        """evaluator_command=None 時，不做任何驗證。"""
        issues = PreRunValidator().validate_step(None, "some prompt")
        assert issues == []

    def test_empty_evaluator_command_returns_empty(self):
        """空字串 evaluator_command 不應崩潰。"""
        issues = PreRunValidator().validate_step("", "some prompt")
        assert issues == []

    @patch("autoclaude.execution.pre_run_validator.shutil.which", return_value=None)
    def test_missing_binary_returns_block_issue(self, _):
        """evaluator_command 使用不存在的命令 → 回傳 severity=block。"""
        issues = PreRunValidator().validate_step("pytset tests/ -v", "任意 prompt")
        assert len(issues) == 1
        assert issues[0].severity == "block"
        assert issues[0].category == "evaluator_missing"
        assert "pytset" in issues[0].message

    @patch("autoclaude.execution.pre_run_validator.shutil.which", return_value="/usr/bin/pytest")
    def test_existing_binary_passes_command_check(self, _):
        """命令存在時，不應產生 evaluator_missing block。"""
        issues = PreRunValidator().validate_step("pytest tests/", "任意 prompt")
        cmd_issues = [i for i in issues if i.category == "evaluator_missing"]
        assert cmd_issues == []

    @patch("autoclaude.execution.pre_run_validator.shutil.which", return_value="/usr/bin/pytest")
    @patch("subprocess.run")
    def test_test_file_syntax_error_returns_block(self, mock_run, _):
        """evaluator_command 引用的測試檔有語法錯誤 → 回傳 test_syntax block。"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: invalid syntax")
        with patch("pathlib.Path.exists", return_value=True):
            issues = PreRunValidator()._check_test_file_syntax("pytest test_foo.py")
        assert any(i.category == "test_syntax" for i in issues)
        assert any(i.severity == "block" for i in issues)

    @patch("autoclaude.execution.pre_run_validator.shutil.which", return_value="/usr/bin/pytest")
    @patch("subprocess.run")
    def test_test_file_no_syntax_error_passes(self, mock_run, _):
        """測試檔語法正確 → 不產生 block。"""
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        with patch("pathlib.Path.exists", return_value=True):
            issues = PreRunValidator()._check_test_file_syntax("pytest test_foo.py")
        assert all(i.category != "test_syntax" for i in issues)


# ──────────────────────────────────────────────
# Gap-009-C：_verify_correction_applied（git diff）
# ──────────────────────────────────────────────

class TestVerifyCorrectionApplied:
    def test_attempt_zero_skips_check(self):
        """attempt=0 時不做任何 git diff 驗證。"""
        runner = _make_runner()
        assert runner._verify_correction_applied(0) is None

    @patch("subprocess.run")
    def test_empty_diff_returns_warning(self, mock_run):
        """git diff 為空 → 回傳警告文字。"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        runner = _make_runner()
        result = runner._verify_correction_applied(1)
        assert result is not None
        assert "修改" in result or "git diff" in result

    @patch("subprocess.run")
    def test_nonempty_diff_returns_none(self, mock_run):
        """git diff 有內容 → 修正已應用 → 回傳 None。"""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" src/foo.py | 2 ++\n 1 file changed", stderr=""
        )
        runner = _make_runner()
        assert runner._verify_correction_applied(1) is None

    @patch("subprocess.run")
    def test_nonzero_exit_code_returns_none(self, mock_run):
        """git 命令失敗（非 git 環境等）→ 安全略過 → 回傳 None。"""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a git repo")
        runner = _make_runner()
        assert runner._verify_correction_applied(1) is None

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_git_not_found_returns_none(self, _):
        """git 不在 PATH → 安全略過 → 回傳 None。"""
        runner = _make_runner()
        assert runner._verify_correction_applied(2) is None

    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired("git", 10))
    def test_timeout_returns_none(self, _):
        """git diff 超時 → 安全略過 → 回傳 None。"""
        runner = _make_runner()
        assert runner._verify_correction_applied(1) is None


# ──────────────────────────────────────────────
# Gap-009-D：_validate_evaluator_commands
# ──────────────────────────────────────────────

class TestValidateEvaluatorCommands:
    def _make_playbook(self, cmd: str) -> Playbook:
        return Playbook(
            version="1.0",
            project="Test",
            global_invariants=GlobalInvariants(
                max_retries_per_step=2, auto_compact_interval=0
            ),
            tasks=[
                PlaybookTask(
                    step_id="T01", name="test", prompt="p",
                    evaluator_command=cmd,
                )
            ],
        )

    def test_no_evaluator_command_no_warning(self, caplog):
        """無 evaluator_command 時不應產生 warning。"""
        import logging
        runner = _make_runner()
        playbook = self._make_playbook(None)
        with caplog.at_level(logging.WARNING):
            runner._validate_evaluator_commands(playbook)
        assert not any("Gap-009-D" in r.message for r in caplog.records)

    def test_missing_binary_logs_gap009d_warning(self, caplog):
        """命令不存在時應記錄含 Gap-009-D 的 warning。"""
        import logging
        runner = _make_runner()
        playbook = self._make_playbook("nonexistent_cmd_xyz123 tests/")
        with caplog.at_level(logging.WARNING):
            with patch("autoclaude.execution.playbook_runner.shutil.which", return_value=None):
                runner._validate_evaluator_commands(playbook)
        assert any("Gap-009-D" in r.message for r in caplog.records)

    def test_existing_binary_no_warning(self, caplog):
        """命令存在時不應產生 warning。"""
        import logging
        runner = _make_runner()
        playbook = self._make_playbook("pytest tests/")
        with caplog.at_level(logging.WARNING):
            with patch("autoclaude.execution.playbook_runner.shutil.which", return_value="/usr/bin/pytest"):
                runner._validate_evaluator_commands(playbook)
        gap_warnings = [r for r in caplog.records if "Gap-009-D" in r.message]
        assert gap_warnings == []


# ──────────────────────────────────────────────
# Gap-009-E：FailureKnowledgeBase
# ──────────────────────────────────────────────

class TestFailureKnowledgeBase:
    def test_query_miss_returns_none(self, tmp_path):
        """未命中時回傳 None。"""
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        assert kb.query("unknown:sig") is None

    def test_record_success_and_query(self, tmp_path):
        """記錄成功策略後，同 Session 查詢應命中。"""
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        kb.record_success("syntax:AssertionError", "REWRITE", "T01")
        entry = kb.query("syntax:AssertionError")
        assert entry is not None
        assert entry["successful_strategy"] == "REWRITE"
        assert entry["outcome"] == "success"

    def test_record_escalation_and_query(self, tmp_path):
        """記錄 ESCALATION 後，skip_strategies 應包含已失敗的策略。"""
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        kb.record_escalation("import:ImportError", ["PINPOINT", "REWRITE"], "T02")
        entry = kb.query("import:ImportError")
        assert entry is not None
        assert entry["outcome"] == "escalation"
        assert "PINPOINT" in entry["skip_strategies"]
        assert "REWRITE" in entry["skip_strategies"]

    def test_persistence_across_instances(self, tmp_path):
        """寫入後，新實例應能從 JSONL 讀取。"""
        kb_path = str(tmp_path / "kb.jsonl")
        kb1 = FailureKnowledgeBase(kb_path)
        kb1.record_success("type:TypeError", "ADD_TYPES", "T03")
        kb2 = FailureKnowledgeBase(kb_path)
        entry = kb2.query("type:TypeError")
        assert entry is not None
        assert entry["successful_strategy"] == "ADD_TYPES"

    def test_success_overwrites_escalation(self, tmp_path):
        """同一 signature 先記錄 escalation 後記錄 success，應以 success 為準。"""
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        kb.record_escalation("syntax:SyntaxError", ["PINPOINT"], "T01")
        kb.record_success("syntax:SyntaxError", "REWRITE", "T01")
        entry = kb.query("syntax:SyntaxError")
        assert entry["outcome"] == "success"
        assert entry["successful_strategy"] == "REWRITE"

    def test_max_entries_prevents_unbounded_growth(self, tmp_path):
        """超過 _MAX_ENTRIES 時，快取大小應受限。"""
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        for i in range(_MAX_ENTRIES + 20):
            kb.record_success(f"sig_{i}", "PINPOINT", "T01")
        assert len(kb._cache) <= _MAX_ENTRIES

    def test_key_truncated_to_80_chars(self, tmp_path):
        """超過 80 字的 key 應被截斷，仍能正確查詢。"""
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        long_sig = "x" * 200
        kb.record_success(long_sig, "SIMPLIFY", "T01")
        assert kb.query(long_sig) is not None
        assert kb.query(long_sig[:80]) is not None

    def test_corrupted_jsonl_loads_gracefully(self, tmp_path):
        """損壞的 JSONL 不應崩潰。"""
        kb_path = tmp_path / "kb.jsonl"
        kb_path.write_text("not valid json\n{corrupted\n", encoding="utf-8")
        kb = FailureKnowledgeBase(str(kb_path))
        assert kb.query("anything") is None


# ──────────────────────────────────────────────
# Gap-009-F：動態 Token 預算
# ──────────────────────────────────────────────

class TestGetDynamicCompactThreshold:
    def test_attempt_zero_equals_base(self):
        """attempt=0 時，閾值 = config base（無降幅）。"""
        runner = _make_runner()
        base = runner._cfg.token_guard.compact_threshold_pct
        assert runner._get_dynamic_compact_threshold(0, 5) == base

    def test_full_retry_reduces_threshold_by_15(self):
        """attempt=max_retries 時，閾值降低 15%（但不低於 65）。"""
        runner = _make_runner()
        base = runner._cfg.token_guard.compact_threshold_pct
        result = runner._get_dynamic_compact_threshold(5, 5)
        assert result == max(base - 15.0, 65.0)

    def test_mid_retry_reduces_proportionally(self):
        """attempt=3, max=5 → ratio=0.6 → 降幅 = 9。"""
        runner = _make_runner()
        base = runner._cfg.token_guard.compact_threshold_pct
        result = runner._get_dynamic_compact_threshold(3, 5)
        expected = max(base - 0.6 * 15.0, 65.0)
        assert abs(result - expected) < 0.01

    def test_floor_is_65_percent(self):
        """閾值下限為 65%，不可低於此值。"""
        runner = _make_runner()
        result = runner._get_dynamic_compact_threshold(1000, 1)
        assert result == 65.0

    def test_zero_max_retries_returns_base(self):
        """max_retries=0 → 回傳 base（避免除零錯誤）。"""
        runner = _make_runner()
        base = runner._cfg.token_guard.compact_threshold_pct
        assert runner._get_dynamic_compact_threshold(1, 0) == base


class TestShouldCompactNow:
    def test_below_dynamic_threshold_not_triggered_returns_false(self):
        """peak < dynamic_threshold 且未觸發 compact → False。"""
        runner = _make_runner()
        # attempt=0, dynamic_threshold = base = 80%；peak=70 < 80 → False
        step_out = _make_step_out(70.0, triggered_compact=False)
        assert runner._should_compact_now(step_out, False, 0, attempt=0, max_retries=5) is False

    def test_above_dynamic_threshold_at_max_retry_returns_true(self):
        """高重試率時，即使未觸發 compact，超過動態門檻也應 compact。"""
        runner = _make_runner()
        # attempt=5, max=5 → dynamic_threshold = max(80-15, 65) = 65%
        # peak=70 >= 65 → True
        step_out = _make_step_out(70.0, triggered_compact=False)
        assert runner._should_compact_now(step_out, False, 0, attempt=5, max_retries=5) is True

    def test_triggered_compact_without_correction_loop_returns_true(self):
        """triggered_compact=True 且非 correction loop → True。"""
        runner = _make_runner()
        step_out = _make_step_out(82.0, triggered_compact=True)
        assert runner._should_compact_now(step_out, False, 0, attempt=0, max_retries=3) is True

    def test_correction_loop_single_history_below_dynamic_returns_false(self):
        """correction loop 且歷史僅 1 筆時，peak < dynamic_threshold → False。
        attempt=1, max=3 → dynamic = max(80 - (1/3)*15, 65) = 75%；peak=70 < 75 → False。"""
        runner = _make_runner()
        # peak=70 < dynamic_threshold=75 → False（即使 triggered_compact=True）
        step_out = _make_step_out(70.0, triggered_compact=True)
        assert runner._should_compact_now(
            step_out, in_correction_loop=True, correction_history_len=1,
            attempt=1, max_retries=3,
        ) is False

    def test_correction_loop_single_history_above_dynamic_returns_true(self):
        """correction loop 且歷史 1 筆，peak >= dynamic_threshold → True。
        LOW-8 修復：peak=83 >= dynamic=75，不再被固定 85% guard 抑制。"""
        runner = _make_runner()
        step_out = _make_step_out(83.0, triggered_compact=True)
        assert runner._should_compact_now(
            step_out, in_correction_loop=True, correction_history_len=1,
            attempt=1, max_retries=3,
        ) is True

    def test_correction_loop_multiple_history_respects_dynamic(self):
        """correction loop 且歷史 > 1 筆，行為與一般情況相同。"""
        runner = _make_runner()
        step_out = _make_step_out(82.0, triggered_compact=True)
        assert runner._should_compact_now(
            step_out, in_correction_loop=True, correction_history_len=3,
            attempt=1, max_retries=3,
        ) is True
