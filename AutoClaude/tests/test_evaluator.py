"""Evaluator 單元測試（評估指令子進程執行）。"""
from autoclaude.execution.evaluator import Evaluator


def test_evaluator_success():
    ev = Evaluator()
    result = ev.run("echo hello")
    assert result.success is True
    assert "hello" in result.output
    assert result.exit_code == 0


def test_evaluator_failure():
    ev = Evaluator()
    result = ev.run("python -c \"import sys; sys.exit(1)\"")
    assert result.success is False
    assert result.exit_code != 0


def test_evaluator_timeout():
    ev = Evaluator(timeout=1)
    result = ev.run("python -c \"import time; time.sleep(5)\"", timeout=1)
    assert result.success is False
    assert "逾時" in result.output
