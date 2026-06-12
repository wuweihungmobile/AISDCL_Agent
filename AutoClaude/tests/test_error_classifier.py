"""ErrorClassifier 單元測試。"""
import pytest
from autoclaude.execution.error_classifier import ErrorClassifier, ErrorClass


@pytest.fixture
def clf():
    return ErrorClassifier()


# ─────────────────────────────
# 各錯誤類型分類
# ─────────────────────────────

class TestErrorClassifierPatterns:
    def test_syntax_error(self, clf):
        assert clf.classify("SyntaxError: invalid syntax at line 5") == ErrorClass.SYNTAX

    def test_indentation_error(self, clf):
        assert clf.classify("IndentationError: unexpected indent") == ErrorClass.SYNTAX

    def test_import_error(self, clf):
        assert clf.classify("ImportError: cannot import name 'foo'") == ErrorClass.IMPORT

    def test_module_not_found(self, clf):
        assert clf.classify("ModuleNotFoundError: No module named 'bar'") == ErrorClass.IMPORT

    def test_no_module_named(self, clf):
        assert clf.classify("No module named 'requests'") == ErrorClass.IMPORT

    def test_assertion_error(self, clf):
        assert clf.classify("AssertionError: assert 1 == 2") == ErrorClass.ASSERTION

    def test_pytest_failed_count(self, clf):
        assert clf.classify("3 failed, 10 passed") == ErrorClass.ASSERTION

    def test_type_error(self, clf):
        assert clf.classify("TypeError: foo() takes 1 argument but 2 were given") == ErrorClass.TYPE

    def test_attribute_error(self, clf):
        assert clf.classify("AttributeError: 'NoneType' object has no attribute 'x'") == ErrorClass.TYPE

    def test_file_not_found(self, clf):
        assert clf.classify("FileNotFoundError: [Errno 2] No such file or directory") == ErrorClass.ENVIRONMENT

    def test_permission_error(self, clf):
        assert clf.classify("PermissionError: [Errno 13] Permission denied") == ErrorClass.ENVIRONMENT

    def test_no_such_file(self, clf):
        assert clf.classify("Error: No such file or directory: 'config.yaml'") == ErrorClass.ENVIRONMENT

    def test_timeout(self, clf):
        assert clf.classify("Timeout: command timed out after 120s") == ErrorClass.TIMEOUT

    def test_unknown(self, clf):
        assert clf.classify("Something went wrong") == ErrorClass.UNKNOWN

    def test_empty_output_unknown(self, clf):
        assert clf.classify("") == ErrorClass.UNKNOWN


# ─────────────────────────────
# 優先級驗證（ENVIRONMENT > SYNTAX）
# ─────────────────────────────

class TestErrorClassifierPriority:
    def test_environment_takes_priority_over_syntax(self, clf):
        """同時含有 FileNotFoundError 和 SyntaxError 時，應分類為 ENVIRONMENT。"""
        output = "SyntaxError: invalid syntax\nFileNotFoundError: config.yaml not found"
        assert clf.classify(output) == ErrorClass.ENVIRONMENT

    def test_syntax_takes_priority_over_import(self, clf):
        """同時含有 SyntaxError 和 ImportError 時，應分類為 SYNTAX。"""
        output = "SyntaxError: invalid syntax\nImportError: cannot import"
        assert clf.classify(output) == ErrorClass.SYNTAX

    def test_import_takes_priority_over_type(self, clf):
        """同時含有 ImportError 和 TypeError 時，應分類為 IMPORT。"""
        output = "ImportError: no module\nTypeError: wrong type"
        assert clf.classify(output) == ErrorClass.IMPORT


# ─────────────────────────────
# ErrorClass 為 str 子類（可直接序列化）
# ─────────────────────────────

class TestErrorClassEnum:
    def test_error_class_is_str(self):
        assert ErrorClass.SYNTAX.value == "syntax"
        assert ErrorClass.ENVIRONMENT.value == "environment"

    def test_error_class_comparison(self):
        assert ErrorClass.SYNTAX == "syntax"
        assert ErrorClass.UNKNOWN == "unknown"
