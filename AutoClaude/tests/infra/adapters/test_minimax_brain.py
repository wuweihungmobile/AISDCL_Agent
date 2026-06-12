"""MinimaxBrainAdapter 單元測試（Phase 1）。

驗證 IBrain 介面契約：
  - 成功路徑：返回 CorrectionResult
  - API 故障（MinimaxError）→ 返回 None（不向上拋例外）
  - PlaybookTask → MinimaxClient kwargs 正確展開
  - CorrectionDecision → CorrectionResult 欄位正確映射
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from autoclaude.core.ports import CorrectionResult
from autoclaude.decision.minimax_client import MinimaxError
from autoclaude.infra.adapters import MinimaxBrainAdapter
from autoclaude.models.playbook import PlaybookTask


def _task():
    return PlaybookTask(
        step_id="T01", name="測試步驟", prompt="prompt body",
        expected_output_regex=r"\[DONE\]",
    )


def _make_decision(prompt="fix it", reasoning="r", task_goal_summary=None, step_mutation=None):
    """建構一個 mock 的 CorrectionDecision-like 物件。"""
    d = MagicMock()
    d.correction_prompt = prompt
    d.reasoning = reasoning
    d.task_goal_summary = task_goal_summary
    d.step_mutation = step_mutation
    return d


class TestMinimaxBrainAdapterSuccess:
    def test_returns_correction_result_on_success(self):
        client = MagicMock()
        client.decide_correction.return_value = _make_decision(prompt="please retry", reasoning="r1")
        adapter = MinimaxBrainAdapter(client)

        result = adapter.decide_correction(
            task=_task(),
            failure_reason="regex miss",
            eval_output="",
            attempt=1,
        )
        assert isinstance(result, CorrectionResult)
        assert result.correction_prompt == "please retry"
        assert result.reasoning == "r1"
        assert result.task_goal_summary is None
        assert result.step_mutation is None

    def test_passes_task_fields_to_client(self):
        client = MagicMock()
        client.decide_correction.return_value = _make_decision()
        adapter = MinimaxBrainAdapter(client)
        task = _task()

        adapter.decide_correction(
            task=task, failure_reason="x", eval_output="y", attempt=2,
            global_goal="GG", allow_step_mutation=True,
        )
        # 驗證 client 收到 task 的展開欄位
        call = client.decide_correction.call_args
        kwargs = call.kwargs
        assert kwargs["step_id"] == "T01"
        assert kwargs["task_name"] == "測試步驟"
        assert kwargs["task_prompt"] == "prompt body"
        assert kwargs["expected_regex"] == r"\[DONE\]"
        assert kwargs["retry_count"] == 3  # attempt=2 → retry_count=attempt+1=3
        assert kwargs["global_goal"] == "GG"
        assert kwargs["allow_step_mutation"] is True

    def test_passes_optional_step_mutation(self):
        client = MagicMock()
        mut = MagicMock()
        client.decide_correction.return_value = _make_decision(step_mutation=mut)
        adapter = MinimaxBrainAdapter(client)

        result = adapter.decide_correction(
            task=_task(), failure_reason="x", eval_output="", attempt=1,
        )
        assert result is not None
        assert result.step_mutation is mut


class TestMinimaxBrainAdapterFailure:
    def test_returns_none_on_minimax_error(self):
        client = MagicMock()
        client.decide_correction.side_effect = MinimaxError("API down")
        adapter = MinimaxBrainAdapter(client)

        result = adapter.decide_correction(
            task=_task(), failure_reason="x", eval_output="", attempt=1,
        )
        assert result is None

    def test_other_exceptions_propagate(self):
        """非 MinimaxError 的例外應向上傳播（不吞例外）。"""
        client = MagicMock()
        client.decide_correction.side_effect = RuntimeError("network reset")
        adapter = MinimaxBrainAdapter(client)

        with pytest.raises(RuntimeError):
            adapter.decide_correction(
                task=_task(), failure_reason="x", eval_output="", attempt=1,
            )


class TestMinimaxBrainAdapterDefaults:
    def test_mutation_history_default_empty_list(self):
        client = MagicMock()
        client.decide_correction.return_value = _make_decision()
        adapter = MinimaxBrainAdapter(client)
        adapter.decide_correction(
            task=_task(), failure_reason="x", eval_output="", attempt=1,
        )
        kwargs = client.decide_correction.call_args.kwargs
        assert kwargs["mutation_history"] == []

    def test_mutation_pressure_default_zero(self):
        client = MagicMock()
        client.decide_correction.return_value = _make_decision()
        adapter = MinimaxBrainAdapter(client)
        adapter.decide_correction(
            task=_task(), failure_reason="x", eval_output="", attempt=1,
        )
        kwargs = client.decide_correction.call_args.kwargs
        assert kwargs["mutation_pressure"] == 0
