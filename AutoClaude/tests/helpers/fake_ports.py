"""Fake Port 實作 — 供 W1 後測試直接測試 AutoResumeService + Kernel 使用。

替代 PlaybookRunner(dry_run=True) 模式：
  FakeExecutor  ← IExecutor   (可配置 per-call 輸出列表)
  FakeEvaluator ← IEvaluator  (可配置永遠通過 / 永遠失敗 / 逐步結果)
  FakeBrain     ← IBrain      (可配置固定修正回傳或 None)
"""
from __future__ import annotations

from typing import Optional

from autoclaude.core.ports.brain import CorrectionResult
from autoclaude.core.ports.executor import ExecutionOutput


class FakeExecutor:
    """可配置輸出的測試用 IExecutor。

    outputs 用完後自動回退為 "[DONE]"，永不拋例外。
    calls 紀錄每次 execute() 收到的 prompt，供斷言使用。
    """

    def __init__(self, outputs: list[str] | None = None):
        self._outputs = list(outputs or ["[DONE]"])
        self._idx = 0
        self.calls: list[str] = []

    def execute(
        self,
        prompt: str,
        *,
        maintain_context: bool = True,
        timeout: int = 600,
        label: str = "",
    ) -> ExecutionOutput:
        self.calls.append(prompt)
        if self._idx < len(self._outputs):
            text = self._outputs[self._idx]
            self._idx += 1
        else:
            text = "[DONE]"
        return ExecutionOutput(text=text)


class FakeEvaluator:
    """可配置評估結果的測試用 IEvaluator。

    優先消耗 results 列表；耗盡後以 always_pass 作為預設值。
    """

    def __init__(self, always_pass: bool = True, results: list[bool] | None = None):
        self._results = list(results or [])
        self._idx = 0
        self._default = always_pass

    def evaluate(self, task, output: str) -> tuple[Optional[str], str, int]:
        """回傳 (failure_reason, eval_output, exit_code)；None = 成功。"""
        if self._idx < len(self._results):
            passed = self._results[self._idx]
            self._idx += 1
        else:
            passed = self._default
        if passed:
            return None, "", 0
        return "fake_evaluation_failed", "", 1


class FakeBrain:
    """可配置修正決策的測試用 IBrain。

    預設回傳 None（模擬 Brain 不可用 / 無修正建議）。
    傳入 correction 可指定固定回傳值。
    """

    def __init__(self, correction: Optional[CorrectionResult] = None):
        self._correction = correction

    def decide_correction(
        self,
        *,
        task=None,
        failure_reason: str = "",
        eval_output: str = "",
        attempt: int = 0,
        **kwargs,
    ) -> Optional[CorrectionResult]:
        return self._correction
