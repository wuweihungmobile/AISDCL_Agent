"""ConvergenceMonitor 單元測試：_extract_fail_count 多框架格式（Gap-006-F）。"""
from autoclaude.execution.convergence_monitor import ConvergenceMonitor


class TestExtractFailCount:
    def test_pytest_format(self):
        assert ConvergenceMonitor._extract_fail_count("3 failed, 2 passed in 0.1s") == 3

    def test_pytest_format_zero(self):
        assert ConvergenceMonitor._extract_fail_count("0 failed, 5 passed") == 0

    def test_unittest_failures_equal(self):
        """unittest: 'FAILED (failures=2)'"""
        assert ConvergenceMonitor._extract_fail_count("FAILED (failures=2)") == 2

    def test_unittest_failures_colon(self):
        """通用格式: 'failures: 3'"""
        assert ConvergenceMonitor._extract_fail_count("failures: 3") == 3

    def test_go_test_format(self):
        """go test: '1 test failed'"""
        assert ConvergenceMonitor._extract_fail_count("--- FAIL: TestFoo\n1 test failed") == 1

    def test_go_test_plural(self):
        assert ConvergenceMonitor._extract_fail_count("2 tests failed") == 2

    def test_junit_format(self):
        """JUnit: 'Tests run: 5, Failures: 2, Errors: 0'"""
        assert ConvergenceMonitor._extract_fail_count(
            "Tests run: 5, Failures: 2, Errors: 0"
        ) == 2

    def test_unknown_format_returns_none(self):
        assert ConvergenceMonitor._extract_fail_count("build error: missing symbol") is None

    def test_empty_string_returns_none(self):
        assert ConvergenceMonitor._extract_fail_count("") is None

    def test_pytest_takes_priority_over_generic(self):
        """pytest 'N failed' 優先匹配（排在第一位）"""
        output = "5 failed, failures=3"
        result = ConvergenceMonitor._extract_fail_count(output)
        assert result == 5  # pytest pattern 優先
