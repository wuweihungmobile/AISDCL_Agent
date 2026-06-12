"""W2（AutoSDD_improving_01 §4.2）：ErrorClass 第 8 類 SDD_CONTRACT_VIOLATION。

驗證 additive 擴充零破壞：
  1. 結構化標記 "SDD-VIOLATION[" 命中第 8 類
  2. 標記優先於 ASSERTION 啟發式（同訊息含 pytest 失敗痕跡仍判 SDD）
  3. 既有 7 類分類行為不變（回歸保護）
"""
from __future__ import annotations

from autoclaude.execution.error_classifier import ErrorClass, ErrorClassifier


class TestSddContractViolation:
    def setup_method(self):
        self.clf = ErrorClassifier()

    def test_marker_classified_as_sdd_violation(self):
        out = "SDD-VIOLATION[AT-001-2-1] contract assertion failed"
        assert self.clf.classify(out) is ErrorClass.SDD_CONTRACT_VIOLATION

    def test_marker_wins_over_assertion_heuristic(self):
        # evaluator 輸出常同時含 pytest 痕跡（"1 failed" / AssertionError）
        out = (
            "FAILED tests/test_x.py::test_at - AssertionError\n"
            "1 failed in 0.3s\n"
            "SDD-VIOLATION[AT-002-1-1]"
        )
        assert self.clf.classify(out) is ErrorClass.SDD_CONTRACT_VIOLATION

    def test_marker_requires_bracket(self):
        # 無 "[" 的散文提及不觸發（防止誤判一般輸出）
        out = "discussing SDD-VIOLATION policy in docs; 1 failed"
        assert self.clf.classify(out) is ErrorClass.ASSERTION

    def test_enum_value_string(self):
        assert ErrorClass.SDD_CONTRACT_VIOLATION.value == "sdd_contract_violation"


class TestExistingClassesUnchanged:
    """回歸保護：既有 7 類行為不受第 8 類插入影響。"""

    def setup_method(self):
        self.clf = ErrorClassifier()

    def test_environment_still_first(self):
        assert self.clf.classify("FileNotFoundError: x") is ErrorClass.ENVIRONMENT

    def test_syntax(self):
        assert self.clf.classify("SyntaxError: invalid") is ErrorClass.SYNTAX

    def test_import(self):
        assert self.clf.classify("No module named foo") is ErrorClass.IMPORT

    def test_type(self):
        assert self.clf.classify("TypeError: bad arg") is ErrorClass.TYPE

    def test_assertion(self):
        assert self.clf.classify("AssertionError: nope") is ErrorClass.ASSERTION

    def test_timeout(self):
        assert self.clf.classify("operation timed out") is ErrorClass.TIMEOUT

    def test_unknown(self):
        assert self.clf.classify("???") is ErrorClass.UNKNOWN

    def test_enum_membership_count_is_eight(self):
        assert len(ErrorClass) == 8
