"""Kernel PRE_CORRECTION dispatch 端到端測試（F-C1 / US-AGT-003）。

驗證意圖：凍結計畫 Phase 1 驗收條件二「偏好出現在 correction prompt」—
Kernel 必須在 decide_correction 前 dispatch PRE_CORRECTION 並將
PreferenceMemoryPlugin 的注入區段以 preferences_section 傳入 Brain；
無偏好時不傳該 kwarg（fake brain 向下相容）。
"""
from __future__ import annotations

from autoclaude.core.event_bus import EventBus
from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.ports.brain import CorrectionResult
from autoclaude.plugins.preference_memory_plugin import PreferenceMemoryPlugin
from tests.plugins._template import (
    FakeBrain,
    FakeEvaluator,
    FakeExecutor,
    sample_playbook,
)


class _FakeStore:
    def __init__(self, data):
        self._data = data

    def get(self, key, scope="global"):
        return self._data.get(key)

    def set(self, key, value, scope="global"):
        self._data[key] = value

    def list(self, scope=None):
        return dict(self._data) if scope in (None, "global") else {}


def _kernel(brain, bus) -> PlaybookKernel:
    # 第一次 attempt 失敗（觸發 correction）、第二次成功
    evaluator = FakeEvaluator(next_results=[("regex 不符", "boom", 1), (None, "", 0)])
    return PlaybookKernel(
        executor=FakeExecutor(), evaluator=evaluator, bus=bus, brain=brain,
    )


def _correction() -> CorrectionResult:
    return CorrectionResult(correction_prompt="fix it", reasoning="r")


class TestPreferencesReachBrain:
    def test_preferences_section_passed_to_brain(self):
        bus = EventBus()
        bus.register(PreferenceMemoryPlugin(
            preference_store=_FakeStore({"correction_strategy": "prefer SPLIT_STEP"})
        ))
        brain = FakeBrain(next_decisions=[_correction()])
        result = _kernel(brain, bus).run(sample_playbook(n_tasks=1))

        assert result.success
        kwargs = brain.calls[0].kwargs
        assert "## 使用者偏好" in kwargs["preferences_section"]
        assert "prefer SPLIT_STEP" in kwargs["preferences_section"]

    def test_no_preferences_omits_kwarg(self):
        """無偏好 → 不傳 preferences_section（簽名向下相容保證）。"""
        bus = EventBus()  # 未註冊 preference plugin
        brain = FakeBrain(next_decisions=[_correction()])
        result = _kernel(brain, bus).run(sample_playbook(n_tasks=1))

        assert result.success
        assert "preferences_section" not in brain.calls[0].kwargs
