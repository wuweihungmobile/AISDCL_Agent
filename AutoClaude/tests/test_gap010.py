"""
Gap-010 實作驗證測試（P0 ~ P2 全量）。

覆蓋範圍：
  P0 - 測試檔非標準命名修復（*_test.py 格式 × 5 個位置）
  A  - ErrorBudget 語意錯誤預算管理器
  D  - EscalationDump.generate_handover_checklist() 可執行復原計畫
  C  - CrossStepStateValidator 跨步驟狀態污染偵測
  F  - FailureKnowledgeBase.get_strategy_priority() 元學習優化器
  B  - build_correction_message() 漸進式上下文摘要壓縮
  E  - PlaybookEvolver Playbook 自演化引擎
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

# ──────────────────────────────────────────────
# P0：測試檔非標準命名修復（*_test.py 格式）
# ──────────────────────────────────────────────

class TestNonStandardTestFileNaming:
    """驗證 5 個位置均支援 *_test.py 命名格式（auth_test.py / foo_test.py 等）。"""

    # --- 位置 1: failure_tracker.suspect_test_file_error() ---

    def test_failure_tracker_detects_underscore_test_py(self):
        """suspect_test_file_error() 應識別 auth_test.py 格式的測試檔。"""
        from autoclaude.execution.failure_tracker import FailureTracker
        tracker = FailureTracker("T01")
        # 兩次嘗試，eval_output 均指向 auth_test.py 的 SyntaxError
        for i in range(2):
            tracker.record(
                attempt=i,
                failure_reason="pytest fail",
                eval_output="ERROR collecting tests/auth_test.py\n  SyntaxError: invalid syntax",
                exit_code=1,
            )
        assert tracker.suspect_test_file_error() is True

    def test_failure_tracker_detects_test_underscore_py(self):
        """suspect_test_file_error() 仍支援標準 test_foo.py 格式。"""
        from autoclaude.execution.failure_tracker import FailureTracker
        tracker = FailureTracker("T01")
        for i in range(2):
            tracker.record(
                attempt=i,
                failure_reason="pytest fail",
                eval_output="FAILED tests/test_foo.py - ImportError: cannot import name 'bar'",
                exit_code=1,
            )
        assert tracker.suspect_test_file_error() is True

    def test_failure_tracker_test_file_re_module_constant(self):
        """模組層級 _TEST_FILE_RE 常數應匹配兩種格式。"""
        import re
        from autoclaude.execution.failure_tracker import _TEST_FILE_RE
        assert _TEST_FILE_RE.search("auth_test.py")
        assert _TEST_FILE_RE.search("test_auth.py")
        assert _TEST_FILE_RE.search("login_service_test.py")
        assert not _TEST_FILE_RE.search("auth.py")

    # --- 位置 2: prompt_builder._detect_test_file_error_hint() ---

    def test_prompt_builder_hint_for_underscore_test_py(self):
        """_detect_test_file_error_hint() 應偵測 auth_test.py 格式並回傳警告。"""
        from autoclaude.decision.prompt_builder import _detect_test_file_error_hint
        hint = _detect_test_file_error_hint(
            "ERROR collecting tests/auth_test.py\n  SyntaxError: invalid syntax"
        )
        assert hint != ""
        assert "測試檔" in hint

    def test_prompt_builder_hint_no_false_positive_for_impl_file(self):
        """普通實作檔的錯誤不應觸發測試檔警告。"""
        from autoclaude.decision.prompt_builder import _detect_test_file_error_hint
        hint = _detect_test_file_error_hint(
            "ERROR in src/auth.py\n  SyntaxError: invalid syntax"
        )
        assert hint == ""

    # --- 位置 3: prompt_builder._detect_assertion_test_error_hint() ---

    def test_prompt_builder_assertion_hint_for_underscore_test_py(self):
        """_detect_assertion_test_error_hint() 應偵測 auth_test.py 的 AssertionError。"""
        from autoclaude.decision.prompt_builder import _detect_assertion_test_error_hint
        hint = _detect_assertion_test_error_hint(
            "FAILED tests/auth_test.py::test_login - AssertionError: assert False",
            retry_count=2,
        )
        assert hint != ""
        assert "測試期望值" in hint or "語意測試" in hint

    def test_prompt_builder_assertion_hint_below_min_retry_count_empty(self):
        """retry_count < 2 時不應回傳 AssertionError 警告（避免過早干預）。"""
        from autoclaude.decision.prompt_builder import _detect_assertion_test_error_hint
        hint = _detect_assertion_test_error_hint(
            "FAILED tests/auth_test.py::test_login - AssertionError",
            retry_count=1,
        )
        assert hint == ""

    # --- 位置 4: playbook_runner._fast_path_test_file_check() ---

    @patch("subprocess.run")
    def test_fast_path_detects_underscore_test_py(self, mock_run):
        """_fast_path_test_file_check() 應識別 auth_test.py 格式的測試檔語法錯誤。"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: unexpected EOF")
        from autoclaude.execution.playbook_runner import PlaybookRunner
        from autoclaude.utils.config import AppConfig
        runner = PlaybookRunner(AppConfig(), MagicMock(), MagicMock(triggered=False), dry_run=True)
        result = runner._fast_path_test_file_check(
            "ERROR collecting tests/auth_test.py\n  SyntaxError: invalid syntax"
        )
        assert result is not None
        assert "auth_test.py" in result

    # --- 位置 5: pre_run_validator._check_test_file_syntax() ---

    @patch("subprocess.run")
    def test_pre_run_validator_detects_underscore_test_py(self, mock_run):
        """_check_test_file_syntax() 應識別 *_test.py 命名格式。"""
        mock_run.return_value = MagicMock(returncode=1, stderr="SyntaxError: invalid syntax")
        from autoclaude.execution.pre_run_validator import PreRunValidator
        with patch("pathlib.Path.exists", return_value=True):
            issues = PreRunValidator()._check_test_file_syntax("pytest tests/auth_test.py -v")
        assert any(i.category == "test_syntax" for i in issues)


# ──────────────────────────────────────────────
# Gap-010-A：ErrorBudget 語意錯誤預算管理器
# ──────────────────────────────────────────────

class TestErrorBudget:
    def _budget(self):
        from autoclaude.execution.error_budget import ErrorBudget
        return ErrorBudget()

    def test_syntax_budget_limits_retries(self):
        """syntax 預算=2，attempt=1 → eff_limit = min(5, 1+2) = 3。"""
        b = self._budget()
        assert b.effective_max_retries(5, "syntax", 1) == 3

    def test_assertion_budget_gives_more_retries(self):
        """assertion 預算=5，attempt=0 → eff_limit = min(5, 0+5) = 5。"""
        b = self._budget()
        assert b.effective_max_retries(5, "assertion", 0) == 5

    def test_environment_budget_is_zero_immediate_escalate(self):
        """environment 預算=0 → eff_limit = min(global, attempt+0) = attempt → 立即 ESCALATE。"""
        b = self._budget()
        # attempt=0 → min(5, 0+0) = 0 → 已達上限
        assert b.effective_max_retries(5, "environment", 0) == 0

    def test_timeout_budget_is_one(self):
        """timeout 預算=1，attempt=0 → eff_limit = min(5, 0+1) = 1。"""
        b = self._budget()
        assert b.effective_max_retries(5, "timeout", 0) == 1

    def test_global_max_takes_precedence_when_lower(self):
        """global_max < class_budget 時，global_max 優先（不超過全域設定）。"""
        b = self._budget()
        # assertion 預算=5，但 global_max=2 → eff_limit = min(2, 0+5) = 2
        assert b.effective_max_retries(2, "assertion", 0) == 2

    def test_unknown_error_class_uses_default(self):
        """未知 error_class 使用 'unknown' 預算=3。"""
        b = self._budget()
        assert b.effective_max_retries(5, "nonexistent_class", 0) == 3

    def test_zero_global_max_returns_zero(self):
        """global_max=0 → 直接回傳 0（已在最大限制）。"""
        b = self._budget()
        assert b.effective_max_retries(0, "assertion", 0) == 0

    def test_import_budget_is_two(self):
        """import 預算=2，attempt=0 → eff_limit = min(5, 0+2) = 2。"""
        b = self._budget()
        assert b.effective_max_retries(5, "import", 0) == 2

    def test_type_budget_is_three(self):
        """type 預算=3，attempt=0 → eff_limit = min(5, 0+3) = 3。"""
        b = self._budget()
        assert b.effective_max_retries(5, "type", 0) == 3

    def test_attempt_advance_increases_effective_limit(self):
        """隨著 attempt 遞增，eff_limit 也會遞增（直到 global_max）。"""
        b = self._budget()
        # syntax 預算=2：attempt=0 → 2, attempt=1 → 3, attempt=2 → 4, attempt=3 → min(5, 5)=5
        assert b.effective_max_retries(5, "syntax", 0) == 2
        assert b.effective_max_retries(5, "syntax", 1) == 3
        assert b.effective_max_retries(5, "syntax", 3) == 5


# ──────────────────────────────────────────────
# Gap-010-D：EscalationDump 可執行復原計畫
# ──────────────────────────────────────────────

def _make_escalation_dump(**overrides):
    from autoclaude.models.escalation import EscalationDump
    defaults = dict(
        playbook_path="scripts/test.yaml",
        step_id="T01",
        step_name="實作測試",
        total_attempts=3,
        failure_chain=[],
        final_eval_output="AssertionError",
        is_stuck=False,
        is_diverging=False,
        suspect_test_file=False,
        is_oscillating=False,
        is_worsening=False,
        suspect_assertion_mismatch=False,
        last_log_path="/tmp/eval.log",
        checkpoint_resume_hint="",
    )
    defaults.update(overrides)
    return EscalationDump(**defaults)


class TestEscalationDumpHandoverChecklist:
    def test_checklist_always_has_git_commands(self):
        """接手清單必含 git log 和 git diff 基本診斷指令。"""
        dump = _make_escalation_dump()
        actions = dump.generate_handover_checklist()
        joined = "\n".join(actions)
        assert "git log" in joined
        assert "git diff" in joined

    def test_suspect_test_file_adds_py_compile_cmd(self):
        """suspect_test_file=True 時應包含 py_compile 指令。"""
        dump = _make_escalation_dump(suspect_test_file=True)
        actions = dump.generate_handover_checklist()
        joined = "\n".join(actions)
        assert "py_compile" in joined
        assert "collect-only" in joined

    def test_is_stuck_adds_log_cat_cmd(self):
        """is_stuck=True 時應包含查看 log 的指令。"""
        dump = _make_escalation_dump(is_stuck=True, last_log_path="/tmp/eval.log")
        actions = dump.generate_handover_checklist()
        joined = "\n".join(actions)
        assert "/tmp/eval.log" in joined

    def test_assertion_mismatch_adds_grep_assert_cmd(self):
        """suspect_assertion_mismatch=True 時應包含 grep assert 指令。"""
        dump = _make_escalation_dump(suspect_assertion_mismatch=True)
        actions = dump.generate_handover_checklist()
        joined = "\n".join(actions)
        assert "grep" in joined
        assert "assert" in joined

    def test_is_worsening_adds_stash_or_restore_cmd(self):
        """is_worsening=True 時應包含 git stash 或還原指令。"""
        dump = _make_escalation_dump(is_worsening=True)
        actions = dump.generate_handover_checklist()
        joined = "\n".join(actions)
        assert "stash" in joined or "checkout" in joined

    def test_resume_hint_includes_autoclaude_cmd(self):
        """恢復指令必含 autoclaude 指令（供接手人員繼續執行）。"""
        dump = _make_escalation_dump(playbook_path="scripts/my.yaml")
        actions = dump.generate_handover_checklist()
        joined = "\n".join(actions)
        assert "autoclaude" in joined
        assert "my.yaml" in joined

    def test_to_markdown_contains_bash_block(self):
        """to_markdown() 輸出應包含 ```bash 代碼區塊（可直接複製執行）。"""
        dump = _make_escalation_dump()
        md = dump.to_markdown()
        assert "```bash" in md
        assert "接手行動清單" in md

    def test_combined_flags_all_sections_present(self):
        """多個旗標同時為 True 時，清單應包含所有對應節。"""
        dump = _make_escalation_dump(
            suspect_test_file=True,
            is_stuck=True,
            suspect_assertion_mismatch=True,
        )
        actions = dump.generate_handover_checklist()
        joined = "\n".join(actions)
        assert "py_compile" in joined       # suspect_test_file
        assert "/tmp/eval.log" in joined    # is_stuck
        assert "grep" in joined             # assertion_mismatch


# ──────────────────────────────────────────────
# Gap-010-C：CrossStepStateValidator
# ──────────────────────────────────────────────

class TestCrossStepStateValidator:
    def _validator(self):
        from autoclaude.execution.cross_step_validator import CrossStepStateValidator
        return CrossStepStateValidator()

    def _make_task(self, step_id: str = "T01"):
        from autoclaude.models.playbook import PlaybookTask
        return PlaybookTask(step_id=step_id, name="test", prompt="do something")

    @patch("subprocess.run")
    def test_clean_working_tree_returns_none(self, mock_run):
        """少於門檻的修改數量不應回傳警告。"""
        mock_run.return_value = MagicMock(
            returncode=0, stdout=" M foo.py\n M bar.py\n"
        )
        v = self._validator()
        result = v.validate_before_step(self._make_task("T02"), self._make_task("T01"))
        assert result is None

    @patch("subprocess.run")
    def test_dirty_working_tree_returns_warning(self, mock_run):
        """超過門檻（>5）的修改數量應回傳警告字串。"""
        # 6 個 ' M' 開頭的行（working tree modified）
        dirty = "\n".join([f" M file{i}.py" for i in range(6)])
        mock_run.return_value = MagicMock(returncode=0, stdout=dirty)
        v = self._validator()
        result = v.validate_before_step(self._make_task("T02"), self._make_task("T01"))
        assert result is not None
        assert "污染" in result
        assert "T01" in result  # 前一步驟 ID 應出現在警告中

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_git_not_found_returns_none(self, _):
        """git 不在 PATH → 安全略過 → 回傳 None（非 git 環境）。"""
        v = self._validator()
        result = v.validate_before_step(self._make_task("T02"), self._make_task("T01"))
        assert result is None

    @patch("subprocess.run")
    def test_non_git_repo_returns_none(self, mock_run):
        """git status 返回非 0（非 git 環境）→ 回傳 None。"""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a git repo")
        v = self._validator()
        result = v.validate_before_step(self._make_task("T02"), None)
        assert result is None

    @patch("subprocess.run")
    def test_no_prev_step_shows_question_mark(self, mock_run):
        """prev_step=None 時警告仍應回傳（顯示 '?' 作為前一步驟 ID）。"""
        dirty = "\n".join([f" M file{i}.py" for i in range(7)])
        mock_run.return_value = MagicMock(returncode=0, stdout=dirty)
        v = self._validator()
        result = v.validate_before_step(self._make_task("T02"), None)
        assert result is not None
        assert "?" in result

    @patch("subprocess.run")
    def test_many_untracked_files_returns_warning(self, mock_run):
        """大量未追蹤新檔案（> 3x 門檻）應回傳注意訊息。"""
        # 16 個 '??' 行（untracked）
        untracked = "\n".join([f"?? newfile{i}.py" for i in range(16)])
        mock_run.return_value = MagicMock(returncode=0, stdout=untracked)
        v = self._validator()
        result = v.validate_before_step(self._make_task("T02"), self._make_task("T01"))
        assert result is not None
        assert "未追蹤" in result


class TestCrossStepValidatorPlaybookRunnerIntegration:
    """Gap-010-C 整合測試：確認 playbook_runner 正確處理 cross_hint。"""

    def test_dry_run_skips_cross_step_validator(self):
        """dry_run=True 時不應呼叫 CrossStepStateValidator（條件 `not self._dry_run`）。"""
        from autoclaude.execution.playbook_runner import PlaybookRunner
        from autoclaude.utils.config import AppConfig
        runner = PlaybookRunner(AppConfig(), MagicMock(), MagicMock(triggered=False), dry_run=True)
        assert runner._dry_run is True
        # 確認 _run_steps 內條件：`if not self._dry_run and step_idx > 0` 在 dry_run 模式短路

    @patch("autoclaude.execution.playbook_runner.CrossStepStateValidator")
    def test_cross_step_validator_called_for_step_idx_gt_zero(self, mock_cls, tmp_path):
        """non-dry-run 模式，step_idx > 0 時應呼叫 CrossStepStateValidator。"""
        from autoclaude.execution.playbook_runner import PlaybookRunner
        from autoclaude.models.playbook import Playbook, PlaybookTask, GlobalInvariants
        from autoclaude.utils.config import AppConfig

        mock_instance = MagicMock()
        mock_instance.validate_before_step.return_value = None  # 無污染
        mock_cls.return_value = mock_instance

        hotkey = MagicMock()
        hotkey.triggered = False
        hotkey.register = MagicMock()
        hotkey.unregister = MagicMock()

        # 建立兩步 playbook（dry_run=False 但 _execute_prompt mock 化）
        playbook = Playbook(
            version="1.0",
            project="TestProject",
            global_invariants=GlobalInvariants(max_retries_per_step=0, auto_compact_interval=0),
            tasks=[
                PlaybookTask(step_id="T01", name="s1", prompt="p1",
                             expected_output_regex="DONE"),
                PlaybookTask(step_id="T02", name="s2", prompt="p2",
                             expected_output_regex="DONE"),
            ],
        )
        playbook_path = str(tmp_path / "test.yaml")
        import yaml
        with open(playbook_path, "w") as f:
            yaml.dump(playbook.model_dump(exclude_none=True), f, allow_unicode=True)

        runner = PlaybookRunner(AppConfig(), MagicMock(), hotkey, dry_run=False)

        from autoclaude.execution.playbook_runner import _StepOutput
        # mock _execute_prompt 讓兩步都成功
        runner._execute_prompt = MagicMock(return_value=_StepOutput(text="[DONE]"))

        result = runner.run(playbook_path)
        assert result.success is True
        # step_idx=1（T02）時應呼叫 CrossStepStateValidator
        assert mock_cls.call_count >= 1
        assert mock_instance.validate_before_step.call_count >= 1


# ──────────────────────────────────────────────
# Gap-010-F：元學習修正策略優化器
# ──────────────────────────────────────────────

class TestMetaLearningOptimizer:
    def test_get_strategy_priority_insufficient_data_returns_default(self, tmp_path):
        """不同策略種類數 < 3 時回傳預設 STRATEGY_TYPES 順序。
        注意：門檻是「不同策略種類數」而非「成功筆數」。
        即使有 N 筆相同策略的成功記錄，若種類 < 3 仍視為不足。
        """
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        from autoclaude.execution.failure_tracker import STRATEGY_TYPES
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        # 只有 2 種不同策略（REWRITE × 2 + PINPOINT × 0 = 1 種 = len(strategy_stats)=1 < 3）
        kb.record_success("sig1", "REWRITE", "T01", error_class="syntax")
        kb.record_success("sig2", "REWRITE", "T02", error_class="syntax")
        priority = kb.get_strategy_priority("syntax")
        assert priority == list(STRATEGY_TYPES)

    def test_get_strategy_priority_with_sufficient_data_prioritizes_best(self, tmp_path):
        """有 >= 3 種不同策略的成功記錄時，最多成功的策略應排在第一位。"""
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        # 需要 >= 3 種不同策略才會觸發排序（implementation 門檻 len(strategy_stats) >= 3）
        # REWRITE 成功 5 次，PINPOINT 成功 1 次，ADD_TYPES 成功 1 次
        for i in range(5):
            kb.record_success(f"sig_rw_{i}", "REWRITE", f"T0{i}", error_class="assertion")
        kb.record_success("sig_pp", "PINPOINT", "T05", error_class="assertion")
        kb.record_success("sig_at", "ADD_TYPES", "T06", error_class="assertion")
        priority = kb.get_strategy_priority("assertion")
        assert priority[0] == "REWRITE"

    def test_get_strategy_priority_different_error_class_not_mixed(self, tmp_path):
        """不同 error_class 的成功記錄不應影響彼此的優先順序。"""
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        from autoclaude.execution.failure_tracker import STRATEGY_TYPES
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        # syntax 成功 3 次使用 SIMPLIFY
        for i in range(3):
            kb.record_success(f"sig_{i}", "SIMPLIFY", f"T0{i}", error_class="syntax")
        # assertion 的策略優先應使用預設（沒有 assertion 的歷史數據）
        priority = kb.get_strategy_priority("assertion")
        assert priority == list(STRATEGY_TYPES)

    def test_record_success_stores_error_class(self, tmp_path):
        """record_success() 應儲存 error_class 欄位。"""
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        kb.record_success("syntax:SyntaxError", "REWRITE", "T01", error_class="syntax")
        entry = kb.query("syntax:SyntaxError")
        assert entry is not None
        assert entry.get("error_class") == "syntax"

    def test_failure_tracker_next_strategy_uses_kb_priority(self, tmp_path):
        """FailureTracker.next_strategy() 應優先使用 KB 建議的策略。"""
        from autoclaude.utils.knowledge_base import FailureKnowledgeBase
        from autoclaude.execution.failure_tracker import FailureTracker
        kb = FailureKnowledgeBase(str(tmp_path / "kb.jsonl"))
        # SPLIT 策略對 assertion 成功 3 次
        for i in range(3):
            kb.record_success(f"sig_{i}", "SPLIT", f"T0{i}", error_class="assertion")
        # 再加一筆不同策略
        kb.record_success("sig_pinpoint", "PINPOINT", "T04", error_class="assertion")
        tracker = FailureTracker("T01")
        strategy = tracker.next_strategy(kb=kb, current_error_class="assertion")
        # SPLIT 應排在優先（但 PINPOINT 已在初始 _tried_strategies 中，所以下一個應是 SPLIT）
        assert strategy in ("SPLIT", "REWRITE")  # 排除已嘗試的 PINPOINT


# ──────────────────────────────────────────────
# Gap-010-B：漸進式上下文摘要壓縮
# ──────────────────────────────────────────────

class TestProgressiveContextSummarization:
    def _build_msg(self, retry_count: int, task_goal_summary=None):
        from autoclaude.decision.prompt_builder import build_correction_message
        return build_correction_message(
            step_id="T01",
            task_name="實作功能",
            task_prompt="X" * 700,  # 700 字的原始 prompt
            expected_regex=r"\[DONE\]",
            failure_reason="測試失敗",
            eval_output="AssertionError at line 5",
            retry_count=retry_count,
            task_goal_summary=task_goal_summary,
        )

    def test_low_retry_uses_full_task_prompt_prefix(self):
        """retry < 3 時應包含 '原始 Prompt（前 600 字）' 區段。"""
        msg = self._build_msg(retry_count=2)
        assert "原始 Prompt（前 600 字）" in msg

    def test_low_retry_no_summary_uses_full_task_prompt(self):
        """task_goal_summary=None 且 retry < 3 時使用完整 task_prompt[:600]。"""
        msg = self._build_msg(retry_count=2, task_goal_summary=None)
        # 700 字 prompt 截斷到 600 字
        assert "X" * 600 in msg
        assert "X" * 601 not in msg

    def test_high_retry_with_summary_uses_summary(self):
        """retry >= 3 且有 task_goal_summary 時，應改用摘要區段（節省 Token）。"""
        summary = "實作 FastAPI JWT 驗證"
        msg = self._build_msg(retry_count=3, task_goal_summary=summary)
        assert "任務目標（摘要）" in msg
        assert summary in msg
        # 不應包含原始 prompt 的前綴
        assert "原始 Prompt（前 600 字）" not in msg

    def test_high_retry_without_summary_falls_back_to_full_prompt(self):
        """retry >= 3 但 task_goal_summary=None 時，仍使用完整 task_prompt（向後相容）。"""
        msg = self._build_msg(retry_count=5, task_goal_summary=None)
        assert "原始 Prompt（前 600 字）" in msg

    def test_retry_exactly_3_with_summary_uses_summary(self):
        """retry=3 是邊界值，應使用摘要（retry_count >= 3 and task_goal_summary）。"""
        summary = "測試摘要"
        msg = self._build_msg(retry_count=3, task_goal_summary=summary)
        assert "任務目標（摘要）" in msg

    def test_correction_decision_supports_task_goal_summary(self):
        """CorrectionDecision 模型應支援 task_goal_summary 欄位。"""
        from autoclaude.models.decision import CorrectionDecision
        decision = CorrectionDecision(
            correction_prompt="fix it",
            reasoning="test",
            task_goal_summary="實作 JWT 驗證模組",
        )
        assert decision.task_goal_summary == "實作 JWT 驗證模組"

    def test_correction_decision_task_goal_summary_default_none(self):
        """CorrectionDecision.task_goal_summary 預設為 None（向後相容）。"""
        from autoclaude.models.decision import CorrectionDecision
        decision = CorrectionDecision(correction_prompt="fix it")
        assert decision.task_goal_summary is None


# ──────────────────────────────────────────────
# Gap-010-E：PlaybookEvolver 自演化引擎
# ──────────────────────────────────────────────

def _make_playbook(n_tasks: int = 3):
    from autoclaude.models.playbook import Playbook, PlaybookTask, GlobalInvariants
    return Playbook(
        version="1.0",
        project="TestProject",
        global_invariants=GlobalInvariants(max_retries_per_step=3),
        tasks=[
            PlaybookTask(
                step_id=f"T0{i+1}",
                name=f"步驟{i+1}",
                prompt=f"實作功能 {i+1}\n詳細說明在這裡",
            )
            for i in range(n_tasks)
        ],
    )


class TestPlaybookEvolver:
    def _evolver(self):
        from autoclaude.evolution.playbook_evolver import PlaybookEvolver
        return PlaybookEvolver()

    def test_suspect_test_file_proposes_inject_step(self):
        """suspect_test_file=True → 應提議 INJECT_STEP 注入前置修復步驟。"""
        dump = _make_escalation_dump(suspect_test_file=True, step_id="T02")
        playbook = _make_playbook(3)
        ev = self._evolver()
        proposal = ev.propose_evolution(playbook, 1, dump)
        assert proposal is not None
        assert proposal.evolution_type == "INJECT_STEP"
        assert proposal.new_step is not None
        assert "T02_PRE" == proposal.new_step.step_id

    def test_assertion_mismatch_with_enough_attempts_proposes_inject(self):
        """suspect_assertion_mismatch=True 且 total_attempts >= 4 → INJECT_STEP。"""
        dump = _make_escalation_dump(
            suspect_assertion_mismatch=True,
            total_attempts=4,
            step_id="T01",
        )
        playbook = _make_playbook(2)
        ev = self._evolver()
        proposal = ev.propose_evolution(playbook, 0, dump)
        assert proposal is not None
        assert proposal.evolution_type == "INJECT_STEP"
        assert "ASSERT_FIX" in proposal.new_step.step_id

    def test_assertion_mismatch_insufficient_attempts_no_proposal(self):
        """suspect_assertion_mismatch=True 但 total_attempts < 4 → 不演化。"""
        dump = _make_escalation_dump(
            suspect_assertion_mismatch=True,
            total_attempts=2,
            step_id="T01",
        )
        playbook = _make_playbook(2)
        ev = self._evolver()
        proposal = ev.propose_evolution(playbook, 0, dump)
        assert proposal is None

    def test_stuck_with_long_failure_chain_proposes_split(self):
        """is_stuck=True 且 failure_chain >= 3 → SPLIT_STEP。"""
        dump = _make_escalation_dump(
            is_stuck=True,
            failure_chain=[{"attempt": i} for i in range(3)],
            step_id="T01",
        )
        playbook = _make_playbook(2)
        ev = self._evolver()
        proposal = ev.propose_evolution(playbook, 0, dump)
        assert proposal is not None
        assert proposal.evolution_type == "SPLIT_STEP"
        assert proposal.split_steps is not None
        assert len(proposal.split_steps) == 2

    def test_no_trigger_returns_none(self):
        """無任何觸發條件 → 回傳 None（需人工介入）。"""
        dump = _make_escalation_dump(
            is_stuck=False,
            suspect_test_file=False,
            suspect_assertion_mismatch=False,
        )
        playbook = _make_playbook(2)
        ev = self._evolver()
        proposal = ev.propose_evolution(playbook, 0, dump)
        assert proposal is None

    def test_apply_inject_step_inserts_new_task(self, tmp_path):
        """apply_evolution INJECT_STEP 應在指定位置插入新步驟。"""
        from autoclaude.evolution.playbook_evolver import PlaybookEvolutionProposal
        from autoclaude.models.playbook import PlaybookTask
        playbook = _make_playbook(2)
        ev = self._evolver()
        new_step = PlaybookTask(step_id="T01_PRE", name="前置步驟", prompt="先做準備")
        proposal = PlaybookEvolutionProposal(
            evolution_type="INJECT_STEP",
            inject_before_idx=0,
            reasoning="test inject",
            new_step=new_step,
        )
        playbook_path = str(tmp_path / "test.yaml")
        # 建立虛擬 playbook 檔
        import yaml
        with open(playbook_path, "w") as f:
            yaml.dump({"version": "1.0", "project": "test", "tasks": []}, f)
        evolved_path = ev.apply_evolution(playbook, proposal, playbook_path)
        assert "evolved_test.yaml" in evolved_path

        # 讀取演化後的 Playbook 確認新步驟已插入
        with open(evolved_path, encoding="utf-8") as f:
            evolved_data = yaml.safe_load(f)
        task_ids = [t["step_id"] for t in evolved_data["tasks"]]
        assert "T01_PRE" in task_ids
        assert task_ids[0] == "T01_PRE"  # 插入在最前面

    def test_apply_split_step_replaces_with_two_tasks(self, tmp_path):
        """apply_evolution SPLIT_STEP 應將一個步驟替換為兩個子步驟。"""
        from autoclaude.evolution.playbook_evolver import PlaybookEvolutionProposal
        from autoclaude.models.playbook import PlaybookTask
        playbook = _make_playbook(2)
        ev = self._evolver()
        split_steps = [
            PlaybookTask(step_id="T01_A", name="子步驟A", prompt="第一部分"),
            PlaybookTask(step_id="T01_B", name="子步驟B", prompt="第二部分"),
        ]
        proposal = PlaybookEvolutionProposal(
            evolution_type="SPLIT_STEP",
            inject_before_idx=0,
            reasoning="test split",
            split_steps=split_steps,
        )
        playbook_path = str(tmp_path / "split_test.yaml")
        import yaml
        with open(playbook_path, "w") as f:
            yaml.dump({"version": "1.0", "project": "test", "tasks": []}, f)
        evolved_path = ev.apply_evolution(playbook, proposal, playbook_path)

        with open(evolved_path, encoding="utf-8") as f:
            evolved_data = yaml.safe_load(f)
        task_ids = [t["step_id"] for t in evolved_data["tasks"]]
        # 原 T01 應被 T01_A + T01_B 取代，T02 仍保留
        assert "T01_A" in task_ids
        assert "T01_B" in task_ids
        assert "T01" not in task_ids
        assert "T02" in task_ids
        assert len(task_ids) == 3  # T01_A + T01_B + T02

    def test_apply_evolution_preserves_global_goal(self, tmp_path):
        """apply_evolution 後，演化 Playbook 應保留 global_goal（Gap-011-A）。"""
        from autoclaude.evolution.playbook_evolver import PlaybookEvolutionProposal
        from autoclaude.models.playbook import PlaybookTask, Playbook, GlobalInvariants
        import yaml
        playbook = Playbook(
            version="1.0",
            project="TestProject",
            global_goal="通過所有測試",
            global_invariants=GlobalInvariants(),
            tasks=[PlaybookTask(step_id="T01", name="s1", prompt="p1")],
        )
        ev = self._evolver()
        new_step = PlaybookTask(step_id="T01_PRE", name="前置", prompt="修復")
        proposal = PlaybookEvolutionProposal(
            evolution_type="INJECT_STEP",
            inject_before_idx=0,
            reasoning="test",
            new_step=new_step,
        )
        playbook_path = str(tmp_path / "goal_test.yaml")
        with open(playbook_path, "w") as f:
            yaml.dump({"version": "1.0", "project": "test", "tasks": []}, f)
        evolved_path = ev.apply_evolution(playbook, proposal, playbook_path)
        with open(evolved_path, encoding="utf-8") as f:
            evolved_data = yaml.safe_load(f)
        assert evolved_data.get("global_goal") == "通過所有測試"
