"""G-W1 Gate — tests/helpers/ 自身測試。

驗證 FakeExecutor / FakeEvaluator / FakeBrain / make_kernel / make_service
均可正確初始化並執行基本場景，確保 W2+ 遷移有穩固的測試基礎設施。
"""
from __future__ import annotations

import pytest
import yaml

from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.brain import CorrectionResult
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.models.playbook import PlaybookTask

from .fake_ports import FakeBrain, FakeEvaluator, FakeExecutor
from .kernel_fixtures import make_kernel, make_service


# ──────────────────────────────────────────────
# FakeExecutor
# ──────────────────────────────────────────────

class TestFakeExecutor:
    def test_returns_outputs_in_order(self):
        e = FakeExecutor(outputs=["hello", "world"])
        assert e.execute("p1").text == "hello"
        assert e.execute("p2").text == "world"

    def test_fallback_to_done_when_exhausted(self):
        e = FakeExecutor(outputs=["x"])
        e.execute("p1")
        assert e.execute("p2").text == "[DONE]"

    def test_default_output_is_done(self):
        e = FakeExecutor()
        assert e.execute("p").text == "[DONE]"

    def test_tracks_calls(self):
        e = FakeExecutor(outputs=["x", "y"])
        e.execute("prompt_a")
        e.execute("prompt_b")
        assert e.calls == ["prompt_a", "prompt_b"]

    def test_returns_execution_output_type(self):
        from autoclaude.core.ports.executor import ExecutionOutput
        e = FakeExecutor()
        out = e.execute("p")
        assert isinstance(out, ExecutionOutput)
        assert out.completed is True
        assert out.exit_code == 0


# ──────────────────────────────────────────────
# FakeEvaluator
# ──────────────────────────────────────────────

class TestFakeEvaluator:
    def _task(self) -> PlaybookTask:
        return PlaybookTask(step_id="T1", name="n", prompt="p")

    def test_always_pass_returns_none_failure(self):
        ev = FakeEvaluator(always_pass=True)
        failure, _, _ = ev.evaluate(self._task(), "output")
        assert failure is None

    def test_always_fail_returns_failure_reason(self):
        ev = FakeEvaluator(always_pass=False)
        failure, _, exit_code = ev.evaluate(self._task(), "output")
        assert failure is not None
        assert isinstance(failure, str)
        assert exit_code == 1

    def test_results_list_consumed_in_order(self):
        ev = FakeEvaluator(results=[True, False, True])
        task = self._task()
        assert ev.evaluate(task, "o")[0] is None        # True → pass
        assert ev.evaluate(task, "o")[0] is not None    # False → fail
        assert ev.evaluate(task, "o")[0] is None        # True → pass

    def test_fallback_to_default_after_results_exhausted(self):
        ev = FakeEvaluator(always_pass=True, results=[False])
        task = self._task()
        ev.evaluate(task, "o")        # consumes False
        assert ev.evaluate(task, "o")[0] is None   # falls back to always_pass=True

    def test_returns_three_tuple(self):
        ev = FakeEvaluator()
        result = ev.evaluate(self._task(), "o")
        assert len(result) == 3


# ──────────────────────────────────────────────
# FakeBrain
# ──────────────────────────────────────────────

class TestFakeBrain:
    def test_default_returns_none(self):
        b = FakeBrain()
        result = b.decide_correction(task=None, failure_reason="", eval_output="", attempt=0)
        assert result is None

    def test_custom_correction_returned(self):
        correction = CorrectionResult(
            correction_prompt="fix it", reasoning="reason"
        )
        b = FakeBrain(correction=correction)
        result = b.decide_correction(task=None, failure_reason="x", eval_output="", attempt=1)
        assert result is correction

    def test_accepts_arbitrary_kwargs(self):
        b = FakeBrain()
        b.decide_correction(
            task=None, failure_reason="", eval_output="",
            attempt=0, convergence_trend="stuck", strategy_hint="retry",
        )


# ──────────────────────────────────────────────
# make_kernel
# ──────────────────────────────────────────────

class TestMakeKernel:
    def test_returns_kernel_and_plugins_dict(self):
        kernel, plugins = make_kernel()
        assert isinstance(kernel, PlaybookKernel)
        assert isinstance(plugins, dict)

    def test_plugins_dict_has_expected_keys(self):
        _, plugins = make_kernel()
        required = {
            "pre_run_validator", "cross_step_validator", "token_guard",
            "global_goal_anchor", "notification", "knowledge_base",
            "goal_synthesis", "convergence", "evolution",
            "goto_counter", "checkpoint", "mutation_service",
        }
        assert required.issubset(plugins.keys())

    def test_goto_counter_accessible(self):
        _, plugins = make_kernel()
        gc = plugins["goto_counter"]
        # GotoCounterPlugin 狀態透過 snapshot() 存取
        assert hasattr(gc, "_snapshot")
        assert hasattr(gc._snapshot, "goto_counter")

    def test_custom_outputs_passed_to_executor(self):
        kernel, _ = make_kernel(outputs=["custom_output"])
        assert kernel._exec._outputs == ["custom_output"]

    def test_eval_pass_false_configures_evaluator(self):
        kernel, _ = make_kernel(eval_pass=False)
        assert kernel._eval._default is False


# ──────────────────────────────────────────────
# make_service
# ──────────────────────────────────────────────

class TestMakeService:
    def test_returns_service_and_plugins_dict(self):
        service, plugins = make_service()
        assert isinstance(service, AutoResumeService)
        assert isinstance(plugins, dict)

    def test_service_kernel_uses_fake_executor(self):
        service, _ = make_service(outputs=["out1"])
        assert isinstance(service._kernel._exec, FakeExecutor)
        assert service._kernel._exec._outputs == ["out1"]

    def test_full_run_single_step_success(self, tmp_path):
        """整合場景：1 個步驟的 Playbook，FakeExecutor + FakeEvaluator 通過。"""
        pb = {
            "version": "1.0",
            "project": "GW1Test",
            "global_invariants": {"max_retries_per_step": 0, "auto_compact_interval": 0},
            "tasks": [
                {"step_id": "T01", "name": "hello", "prompt": "hello world"}
            ],
        }
        pb_path = tmp_path / "test.yaml"
        pb_path.write_text(yaml.dump(pb, allow_unicode=True), encoding="utf-8")

        service, _ = make_service(outputs=["[DONE]"])
        result = service.run(str(pb_path))

        assert result.success
        assert result.completed_steps == 1

    def test_full_run_multi_step_success(self, tmp_path):
        """整合場景：3 個步驟全部通過。"""
        pb = {
            "version": "1.0",
            "project": "GW1Test",
            "global_invariants": {"max_retries_per_step": 0, "auto_compact_interval": 0},
            "tasks": [
                {"step_id": f"T0{i}", "name": f"step{i}", "prompt": "p"}
                for i in range(1, 4)
            ],
        }
        pb_path = tmp_path / "test.yaml"
        pb_path.write_text(yaml.dump(pb, allow_unicode=True), encoding="utf-8")

        service, _ = make_service(outputs=["[DONE]", "[DONE]", "[DONE]"])
        result = service.run(str(pb_path))

        assert result.success
        assert result.completed_steps == 3

    def test_full_run_fail_escalates(self, tmp_path):
        """整合場景：評估失敗 + max_retries=0 → escalated。"""
        pb = {
            "version": "1.0",
            "project": "GW1Test",
            "global_invariants": {"max_retries_per_step": 0, "auto_compact_interval": 0},
            "tasks": [
                {"step_id": "T01", "name": "fail_step", "prompt": "p"}
            ],
        }
        pb_path = tmp_path / "test.yaml"
        pb_path.write_text(yaml.dump(pb, allow_unicode=True), encoding="utf-8")

        service, _ = make_service(eval_pass=False)
        result = service.run(str(pb_path))

        assert not result.success
        assert result.escalated
