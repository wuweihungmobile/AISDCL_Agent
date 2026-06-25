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


class TestCorrectionObservabilityMarker:
    """improving_71 W-71-2：Kernel 取得有效修正時發 CORRECTION 可觀測標記，
    使 pty/sdk A/B（tools/ab_compare_backends.py）能計數 CORRECTION 次數。
    Rule 9：此標記是 A/B 第四指標的唯一可觀測來源，缺失即 A/B 無法量 CORRECTION。
    """

    def test_correction_marker_emitted_once_per_correction(self, caplog):
        import logging

        bus = EventBus()
        brain = FakeBrain(next_decisions=[_correction()])
        with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
            result = _kernel(brain, bus).run(sample_playbook(n_tasks=1))

        assert result.success  # 第二次 attempt 成功
        markers = [r for r in caplog.records if "STATE: CORRECTION" in r.getMessage()]
        assert len(markers) == 1  # 恰一次修正（第一次 attempt 失敗後）

    def test_no_marker_when_first_attempt_passes(self, caplog):
        """一次通過（無失敗）→ 不發 CORRECTION 標記（不可虛報修正）。"""
        import logging

        bus = EventBus()
        evaluator = FakeEvaluator(next_results=[(None, "", 0)])  # 第一次即過
        brain = FakeBrain(next_decisions=[_correction()])
        kernel = PlaybookKernel(
            executor=FakeExecutor(), evaluator=evaluator, bus=bus, brain=brain,
        )
        with caplog.at_level(logging.INFO, logger="autoclaude.core.kernel"):
            result = kernel.run(sample_playbook(n_tasks=1))

        assert result.success
        markers = [r for r in caplog.records if "STATE: CORRECTION" in r.getMessage()]
        assert markers == []
