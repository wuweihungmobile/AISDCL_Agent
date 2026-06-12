"""PreferenceMemoryPlugin 測試（F-C1 / US-AGT-003）。

驗證意圖：偏好必須在 PRE_CORRECTION 以 PromptInjectionResult 形式注入
（Brain 據此調整修正策略）；無偏好/無 store 時零干擾（向下相容）。
"""
from __future__ import annotations

from autoclaude.core.hookspec import HookContext, KernelPhase, PromptInjectionResult
from autoclaude.models.playbook import Playbook, PlaybookTask
from autoclaude.plugins.preference_memory_plugin import PreferenceMemoryPlugin


class _FakeStore:
    def __init__(self, data=None, playbook_data=None):
        self._g = data or {}
        self._p = playbook_data or {}

    def get(self, key, scope="global"):
        return (self._p if scope.startswith("playbook:") else self._g).get(key)

    def set(self, key, value, scope="global"):
        (self._p if scope.startswith("playbook:") else self._g)[key] = value

    def list(self, scope=None):
        if scope and scope.startswith("playbook:"):
            return dict(self._p)
        return dict(self._g)


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="P",
        tasks=[PlaybookTask(step_id="T01", name="t", prompt="p")],
    )


def _ctx(phase=KernelPhase.PRE_CORRECTION) -> HookContext:
    return HookContext(phase=phase, playbook=_pb(), attempt=1)


class TestBasics:
    def test_name_and_priority(self):
        p = PreferenceMemoryPlugin()
        assert p.name() == "preference_memory"
        assert p.priority() == 50

    def test_subscribes_pre_correction_only(self):
        assert PreferenceMemoryPlugin().subscribed_phases() == [
            KernelPhase.PRE_CORRECTION
        ]


class TestInjection:
    def test_injects_preferences_section(self):
        plugin = PreferenceMemoryPlugin(
            preference_store=_FakeStore({"correction_strategy": "prefer SPLIT_STEP"})
        )
        result = plugin.on_event(_ctx())
        assert isinstance(result, PromptInjectionResult)
        assert "## 使用者偏好" in result.prefix
        assert "correction_strategy: prefer SPLIT_STEP" in result.prefix

    def test_playbook_scope_overrides_global(self):
        plugin = PreferenceMemoryPlugin(preference_store=_FakeStore(
            {"k": "global-v"}, playbook_data={"k": "pb-v"}
        ))
        result = plugin.on_event(_ctx())
        assert "k: pb-v" in result.prefix
        assert "global-v" not in result.prefix

    def test_caps_at_exactly_ten_keys(self):
        """ADR-AGT-003 §4 風險緩解：區段上限恰為 10 鍵防 prompt 膨脹
        （精確計數：_MAX_KEYS 上修或下修皆必紅）。"""
        plugin = PreferenceMemoryPlugin(
            preference_store=_FakeStore({f"k{i:02d}": "v" for i in range(15)})
        )
        result = plugin.on_event(_ctx())
        bullet_lines = [
            line for line in result.prefix.splitlines() if line.startswith("- ")
        ]
        assert len(bullet_lines) == 10
        assert "k14" in result.prefix  # 保留最新（最後）鍵
        assert "k00" not in result.prefix  # 最舊鍵被截斷


class TestNoInterference:
    def test_no_store_returns_none(self):
        assert PreferenceMemoryPlugin().on_event(_ctx()) is None

    def test_empty_prefs_returns_none(self):
        plugin = PreferenceMemoryPlugin(preference_store=_FakeStore())
        assert plugin.on_event(_ctx()) is None

    def test_other_phase_returns_none(self):
        plugin = PreferenceMemoryPlugin(preference_store=_FakeStore({"k": "v"}))
        assert plugin.on_event(_ctx(KernelPhase.POST_RUN)) is None

    def test_broken_store_returns_none(self):
        class _Broken:
            def list(self, scope=None):
                raise RuntimeError("boom")

        plugin = PreferenceMemoryPlugin(preference_store=_Broken())
        assert plugin.on_event(_ctx()) is None
