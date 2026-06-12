"""SD_Improving_05 W0 三方審查 SA-C3：wiring SSOT 兩路徑等價斷言。

驗證 `wire_plugins_with_registry()` 與 `build_kernel()` 透過 `_build_plugin_set`
+ `_register_in_order` 共享 SSOT，產出的 Plugin 集合與註冊順序完全等價，
杜絕 M-3 漂移風險。

特別檢查：
  - Plugin name 集合相等（含 / 不含 hotkey 兩 case）
  - 註冊順序相等（依 _REGISTER_ORDER）
  - state_repository 參數兩條路徑對稱（Arch-M3 / SD-M7）
"""
from __future__ import annotations

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import KernelPhase
from autoclaude.core.wiring import (
    _REGISTER_ORDER,
    _build_plugin_set,
    _register_in_order,
    build_kernel,
    wire_plugins_with_registry,
)
from autoclaude.utils.config import AppConfig
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator


class _DummyExecutor:
    def execute(self, prompt, *, maintain_context=True, timeout=600, label=""):
        from autoclaude.core.ports.executor import ExecutionOutput
        return ExecutionOutput(text="", exit_code=0)


def _cfg(tmp_path) -> AppConfig:
    cfg = AppConfig()
    cfg.checkpoint_dir = str(tmp_path / "ckpts")
    return cfg


class TestSSOTPluginSetEquivalence:
    """兩條路徑共用 _build_plugin_set 後的等價性。"""

    def test_no_hotkey_plugin_set_equal(self, tmp_path):
        cfg = _cfg(tmp_path)
        wire_bus = EventBus()
        wire_plugins = wire_plugins_with_registry(wire_bus, config=cfg, hotkey=None)
        # 用 _build_plugin_set 模擬 build_kernel 的內部呼叫
        kernel_plugins = _build_plugin_set(cfg, hotkey=None, state_repository=None)
        # 比較 name 集合（hotkey 兩條路徑都不應出現）
        wire_names = set(wire_plugins.keys())
        kernel_names = set(kernel_plugins.keys())
        assert wire_names == kernel_names
        assert "hotkey" not in wire_names

    def test_with_hotkey_plugin_set_equal(self, tmp_path):
        cfg = _cfg(tmp_path)
        class _Hotkey:
            pass
        hk = _Hotkey()
        wire_bus = EventBus()
        wire_plugins = wire_plugins_with_registry(wire_bus, config=cfg, hotkey=hk)
        kernel_plugins = _build_plugin_set(cfg, hotkey=hk, state_repository=None)
        assert set(wire_plugins.keys()) == set(kernel_plugins.keys())
        assert "hotkey" in wire_plugins
        assert "hotkey" in kernel_plugins

    def test_register_order_constant_matches_plugin_keys(self, tmp_path):
        """_REGISTER_ORDER 中所有 name 必須在 _build_plugin_set 結果中（或為 hotkey 選用）。"""
        cfg = _cfg(tmp_path)
        plugins = _build_plugin_set(cfg, hotkey=None, state_repository=None)
        for name in _REGISTER_ORDER:
            if name == "hotkey":
                continue  # 選用
            assert name in plugins, f"_REGISTER_ORDER 含 '{name}' 但 _build_plugin_set 未提供"


class TestRegistrationOrderEquivalence:
    """兩條路徑透過 _register_in_order 後，bus._subscribers 註冊順序相同。"""

    def test_register_order_follows_REGISTER_ORDER_constant(self, tmp_path):
        cfg = _cfg(tmp_path)
        bus = EventBus()
        plugins = _build_plugin_set(cfg, hotkey=None, state_repository=None)
        _register_in_order(bus, plugins)

        # 依 register_seq 取所有已註冊 plugin
        registered_names = []
        seen = set()
        for hooks in bus._subscribers.values():
            for h in hooks:
                if h.name() not in seen:
                    seen.add(h.name())
                    registered_names.append((h._register_idx, h.name()))
        registered_names.sort()
        actual_order = [n for _, n in registered_names]

        # 對齊 _REGISTER_ORDER（扣除 hotkey 因為未傳）
        expected_order = [n for n in _REGISTER_ORDER if n != "hotkey"]
        assert actual_order == expected_order


class TestStateRepositorySymmetry:
    """Arch-M3 / SD-M7：state_repository 兩條路徑對稱。"""

    def test_wire_plugins_accepts_state_repository(self, tmp_path):
        """wire_plugins_with_registry 必須接受 state_repository 參數。"""
        import inspect
        sig = inspect.signature(wire_plugins_with_registry)
        assert "state_repository" in sig.parameters

    def test_build_kernel_accepts_state_repository(self):
        import inspect
        sig = inspect.signature(build_kernel)
        assert "state_repository" in sig.parameters


class TestW4PriorityInvariant:
    """SD_05 W4 三方審查 SA-m4：新 plugin priority 順序不變式。

    確保 W4 加入的 FastPathPlugin / PlaybookPersistencePlugin 之 priority
    保持設計值（40 / 50），重構時自動偵測誤改。
    """

    def test_playbook_persistence_priority_40(self):
        from autoclaude.plugins.playbook_persistence_plugin import PlaybookPersistencePlugin
        assert PlaybookPersistencePlugin.PRIORITY == 40

    def test_fast_path_priority_50(self):
        from autoclaude.plugins.fast_path_plugin import FastPathPlugin
        assert FastPathPlugin.PRIORITY == 50

    def test_register_order_w4_tie_breaker_invariant(self):
        # PRE_ATTEMPT phase 之 plugin（fast_path）必須先於 notification/knowledge_base/
        # goal_synthesis（同 priority=50）出現於 _REGISTER_ORDER
        order = list(_REGISTER_ORDER)
        idx_fast = order.index("fast_path")
        assert idx_fast < order.index("notification")
        assert idx_fast < order.index("knowledge_base")
        assert idx_fast < order.index("goal_synthesis")
        # playbook_persistence 必須在 global_goal_anchor 之後、fast_path 之前
        idx_pp = order.index("playbook_persistence")
        assert order.index("global_goal_anchor") < idx_pp < idx_fast

    def test_state_repository_flows_through_both_paths(self, tmp_path):
        """兩條路徑都把 state_repository 注入 CheckpointPlugin/Manager。"""
        cfg = _cfg(tmp_path)
        fake_repo = object()

        # 路徑 A
        bus_a = EventBus()
        plugins_a = wire_plugins_with_registry(
            bus_a, config=cfg, state_repository=fake_repo
        )
        cp_a = plugins_a["checkpoint"]

        # 路徑 B
        plugins_b = _build_plugin_set(cfg, state_repository=fake_repo)
        cp_b = plugins_b["checkpoint"]

        # 兩條路徑的 CheckpointPlugin 都應持有同一個 fake_repo
        # （透過 CheckpointManager._repo；屬性名為 _repo 見 checkpoint_manager.py:90）
        assert cp_a._mgr._repo is fake_repo
        assert cp_b._mgr._repo is fake_repo
