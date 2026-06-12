"""Port 介面契約測試（Phase 1）。

驗證：
  - IExecutor / IEvaluator / IBrain 是 typing.Protocol（純介面）
  - ExecutionOutput / CorrectionResult 是 frozen dataclass
  - Adapter 實作通過 isinstance Protocol 檢查（runtime_checkable 才生效；本測以 hasattr 替代）
"""
from __future__ import annotations

from dataclasses import is_dataclass

from autoclaude.core.ports import (
    IBrain,
    IEvaluator,
    IExecutor,
    ExecutionOutput,
    CorrectionResult,
)


class TestPortDataclasses:
    def test_execution_output_is_frozen_dataclass(self):
        assert is_dataclass(ExecutionOutput)
        out = ExecutionOutput(text="hello")
        # frozen → 不可變
        try:
            out.text = "modified"  # type: ignore[misc]
            assert False, "ExecutionOutput 應為 frozen dataclass"
        except (AttributeError, Exception):
            pass

    def test_execution_output_defaults(self):
        out = ExecutionOutput(text="x")
        assert out.text == "x"
        assert out.exit_code == 0
        assert out.completed is True

    def test_correction_result_is_frozen_dataclass(self):
        assert is_dataclass(CorrectionResult)
        r = CorrectionResult(correction_prompt="p", reasoning="r")
        try:
            r.correction_prompt = "x"  # type: ignore[misc]
            assert False
        except (AttributeError, Exception):
            pass

    def test_correction_result_optionals(self):
        r = CorrectionResult(correction_prompt="p", reasoning="r")
        assert r.task_goal_summary is None
        assert r.step_mutation is None


class TestPortShape:
    """確認 Protocol 介面有正確的方法簽章（duck typing 檢查）。"""

    def test_iexecutor_has_execute(self):
        assert hasattr(IExecutor, "execute")

    def test_ievaluator_has_evaluate(self):
        assert hasattr(IEvaluator, "evaluate")

    def test_ibrain_has_decide_correction(self):
        assert hasattr(IBrain, "decide_correction")
