"""SD_Improving_05 W1 Step-1 — Counter SSOT 遷移合約測試。

驗證：
  1. PlaybookRunner 持有 GotoCounterPlugin 實例（單一 SSOT 入口）
  2. _run_steps 主迴圈內 4 個 local counter（`_goto_counter` / `_inject_before_counter` /
     `_skip_to_counter` / `_step_evolution_counter`）皆為 plugin 內部 dict 的 alias
     （非 deep copy，是 live reference）
  3. plugin.snapshot() 對外回傳 deep copy，不影響本體
  4. plugin.restore() 從 checkpoint 還原 4 個 counter
  5. 跨 session 持久化：resume_checkpoint 還原後 plugin 內部狀態正確
  6. SD_05 §1 Critical-3 強制順序：counter SSOT 遷移（Step-1）必須在
     CheckpointPlugin save 路徑（Step-2）之前完成 — 本測試驗證 Step-1 已完成

涵蓋風險：R-SD05-W1-1（counter SSOT 遷移順序錯誤打破 Gap-042 / Gap-048）
"""
from __future__ import annotations

import pytest

from autoclaude.models.counter_snapshot import CounterSnapshot
from autoclaude.plugins.goto_counter_plugin import GotoCounterPlugin
from autoclaude.utils.config import PlaybookConfig


class TestGotoCounterPluginSSOT:
    """plugin 為唯一 SSOT 的 API 契約。"""

    def test_four_counters_initialized_empty(self):
        plugin = GotoCounterPlugin(playbook_cfg=PlaybookConfig())
        assert plugin.goto_counter == {}
        assert plugin.inject_before_counter == {}
        assert plugin.skip_to_counter == {}
        assert plugin.step_evolution_counter == {}

    def test_property_returns_live_reference_not_copy(self):
        """關鍵：property 回傳 live reference，外部寫入直達 plugin 內部。"""
        plugin = GotoCounterPlugin()
        ref = plugin.goto_counter
        ref["T01"] = 5
        # plugin.goto_counter 又一次取得時應看到該寫入（同一物件）
        assert plugin.goto_counter["T01"] == 5
        assert plugin.goto_counter is ref  # 物件 identity

    def test_increment_writes_to_internal_snapshot(self):
        plugin = GotoCounterPlugin()
        plugin.increment_goto("T01")
        plugin.increment_goto("T01")
        plugin.increment_inject_before("T02")
        plugin.increment_skip_to("T03")
        plugin.increment_step_evolution("T04")
        assert plugin.goto_counter["T01"] == 2
        assert plugin.inject_before_counter["T02"] == 1
        assert plugin.skip_to_counter["T03"] == 1
        assert plugin.step_evolution_counter["T04"] == 1

    def test_snapshot_returns_deep_copy(self):
        plugin = GotoCounterPlugin()
        plugin.increment_goto("T01")
        snap = plugin.snapshot()
        # snapshot 是 deep copy：修改 snap 不影響 plugin
        snap.goto_counter["T01"] = 999
        assert plugin.goto_counter["T01"] == 1, "snapshot 必須為 deep copy"
        # 同樣，plugin 後續變動不影響 snap
        plugin.increment_goto("T01")
        assert snap.goto_counter["T01"] == 999

    def test_restore_overrides_internal_state(self):
        plugin = GotoCounterPlugin()
        plugin.increment_goto("T_OLD")
        plugin.restore(CounterSnapshot(
            goto_counter={"T01": 3, "T02": 1},
            inject_before_counter={"T03": 2},
            skip_to_counter={"T04": 1},
            step_evolution_counter={"T05": 4},
        ))
        assert plugin.goto_counter == {"T01": 3, "T02": 1}
        assert plugin.inject_before_counter == {"T03": 2}
        assert plugin.skip_to_counter == {"T04": 1}
        assert plugin.step_evolution_counter == {"T05": 4}
        assert "T_OLD" not in plugin.goto_counter

    def test_restore_deep_copies_input_snapshot(self):
        """restore 後外部修改傳入的 snapshot 不影響 plugin。"""
        plugin = GotoCounterPlugin()
        input_snap = CounterSnapshot(goto_counter={"T01": 1})
        plugin.restore(input_snap)
        input_snap.goto_counter["T01"] = 999
        assert plugin.goto_counter["T01"] == 1


class TestPlaybookRunnerHoldsPlugin:
    """PlaybookRunner 持有 GotoCounterPlugin，作為 SSOT 入口。"""

    def test_runner_has_goto_counter_plugin_attribute(self, tmp_path):
        from autoclaude.execution.playbook_runner import PlaybookRunner
        from autoclaude.utils.config import AppConfig
        from autoclaude.decision.minimax_client import MinimaxClient
        from autoclaude.perception.hotkey_handler import HotkeyHandler
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        runner = PlaybookRunner(
            config=cfg,
            minimax_client=MinimaxClient(api_key="dummy", base_url="x", model="m"),
            hotkey_handler=HotkeyHandler(),
            dry_run=True,
        )
        assert hasattr(runner, "_goto_counter_plugin")
        assert isinstance(runner._goto_counter_plugin, GotoCounterPlugin)

    def test_runner_plugin_is_only_data_source(self, tmp_path):
        """SSOT 驗證：寫入 plugin → 任何透過 property 取的 reference 都看到。

        SD-m3 修正：使用公開 API（plugin.goto_counter property）兩次取得 reference
        驗證 identity，而非直接存取 plugin._snapshot 私有屬性。
        """
        from autoclaude.execution.playbook_runner import PlaybookRunner
        from autoclaude.utils.config import AppConfig
        from autoclaude.decision.minimax_client import MinimaxClient
        from autoclaude.perception.hotkey_handler import HotkeyHandler
        cfg = AppConfig()
        cfg.checkpoint_dir = str(tmp_path)
        runner = PlaybookRunner(
            config=cfg,
            minimax_client=MinimaxClient(api_key="dummy", base_url="x", model="m"),
            hotkey_handler=HotkeyHandler(),
            dry_run=True,
        )
        plugin = runner._goto_counter_plugin
        plugin.increment_goto("T_TEST")
        # 多次取得 property 應為同一物件（live reference，非 copy）
        ref_a = plugin.goto_counter
        ref_b = plugin.goto_counter
        assert ref_a is ref_b
        assert ref_a["T_TEST"] == 1


class TestLocalCounterIsAliasNotCopy:
    """W1 Step-1 核心驗證：_run_steps 內 local 變數為 plugin live alias。

    模擬 _run_steps line 153 的初始化模式，確認語意正確。
    """

    def test_local_alias_writes_propagate_to_plugin(self):
        plugin = GotoCounterPlugin()
        # 模擬 _run_steps line 153 alias
        _goto_counter = plugin.goto_counter
        _inject_before_counter = plugin.inject_before_counter
        _skip_to_counter = plugin.skip_to_counter
        _step_evolution_counter = plugin.step_evolution_counter

        # 模擬 _apply_single_mutation_full 內的寫入路徑
        _goto_counter["T01"] = 3
        _inject_before_counter["T02"] = 2
        _skip_to_counter["T03"] = 1
        _step_evolution_counter["T04"] = 5

        # plugin 內部資料應同步反映
        assert plugin.goto_counter["T01"] == 3
        assert plugin.inject_before_counter["T02"] == 2
        assert plugin.skip_to_counter["T03"] == 1
        assert plugin.step_evolution_counter["T04"] == 5
        # snapshot() 取出 deep copy 驗證
        snap = plugin.snapshot()
        assert snap.goto_counter == {"T01": 3}
        assert snap.inject_before_counter == {"T02": 2}
        assert snap.skip_to_counter == {"T03": 1}
        assert snap.step_evolution_counter == {"T04": 5}

    def test_resume_checkpoint_restored_into_plugin(self):
        """模擬 _run_steps 從 resume_checkpoint 還原的路徑。"""
        plugin = GotoCounterPlugin()
        # 模擬有 checkpoint 的還原
        cp_snap = CounterSnapshot(
            goto_counter={"T01": 2},
            inject_before_counter={},
            skip_to_counter={},
            step_evolution_counter={"T03": 1},
        )
        plugin.restore(cp_snap)
        # 取 alias
        _goto_counter = plugin.goto_counter
        # 應看到 checkpoint 內容
        assert _goto_counter["T01"] == 2
        # 修改 alias，plugin 內部應同步
        _goto_counter["T02"] = 1
        assert plugin.goto_counter["T02"] == 1


class TestSSOTSingleDataSource:
    """負面測試：local 變數絕不獨立於 plugin。"""

    def test_local_alias_writes_visible_via_property(self):
        """SD-m3：用公開 API 驗證 SSOT — local alias 寫入後，再次取 property 看到結果。"""
        plugin = GotoCounterPlugin()
        _goto_counter = plugin.goto_counter
        _goto_counter["T_LOCAL"] = 7
        # 再次透過公開 property 取得 — 必看到寫入（同物件）
        assert plugin.goto_counter["T_LOCAL"] == 7
        # 取另一個 property 也是同物件
        assert plugin.goto_counter is _goto_counter

    def test_restore_preserves_alias_identity(self):
        """SD_05 W1 三方審查 Arch-M2 修正後：restore() 就地 clear+update，
        不再替換 _snapshot 物件 — 任何先前取的 alias 在 restore 後仍指向正確資料。

        此 case 直接驗證 W6 拔除前的隱性 bug 已被結構性消除（不再仰賴
        「restore 後立即重取 alias」的設計信任）。
        """
        plugin = GotoCounterPlugin()
        # 取得 alias（持有 reference）
        _goto_alias = plugin.goto_counter
        _inject_alias = plugin.inject_before_counter
        _skip_alias = plugin.skip_to_counter
        _evo_alias = plugin.step_evolution_counter

        # restore 後內部 _snapshot 物件 identity 應保持
        plugin.restore(CounterSnapshot(
            goto_counter={"T01": 5},
            inject_before_counter={"T02": 3},
            skip_to_counter={"T03": 2},
            step_evolution_counter={"T04": 7},
        ))

        # 舊 alias 仍指向同一 dict 物件（identity 不變）
        assert plugin.goto_counter is _goto_alias
        assert plugin.inject_before_counter is _inject_alias
        assert plugin.skip_to_counter is _skip_alias
        assert plugin.step_evolution_counter is _evo_alias

        # 舊 alias 自動看到新資料（就地 clear+update 效果）
        assert _goto_alias["T01"] == 5
        assert _inject_alias["T02"] == 3
        assert _skip_alias["T03"] == 2
        assert _evo_alias["T04"] == 7

    def test_restore_clears_old_entries(self):
        """restore() 必須 clear 舊資料（避免 stale entry 殘留）。"""
        plugin = GotoCounterPlugin()
        plugin.increment_goto("T_OLD")
        plugin.restore(CounterSnapshot(goto_counter={"T_NEW": 1}))
        assert "T_OLD" not in plugin.goto_counter
        assert plugin.goto_counter["T_NEW"] == 1


class TestCheckpointRoundTripSSOT:
    """SA 補：CheckpointPlugin ↔ GotoCounterPlugin 透過 CounterSnapshotResult 互動。

    驗證 W1 Step-2 路徑：CheckpointPlugin emit ON_CHECKPOINT_SAVE_REQUEST →
    GotoCounterPlugin 回傳 CounterSnapshotResult → CheckpointPlugin 從
    MergedResult.counter_diff 取資料寫入 PlaybookCheckpoint。
    """

    def test_save_request_returns_counter_snapshot_result(self):
        from autoclaude.core.hookspec import (
            CounterSnapshotResult, HookContext, KernelPhase,
        )
        from autoclaude.models.playbook import GlobalInvariants, Playbook
        plugin = GotoCounterPlugin()
        plugin.increment_goto("T01")
        plugin.increment_goto("T01")
        plugin.increment_inject_before("T02")
        plugin.increment_skip_to("T03")
        plugin.increment_step_evolution("T04")

        ctx = HookContext(
            phase=KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,
            playbook=Playbook(version="1.0", project="t",
                              global_invariants=GlobalInvariants(), tasks=[]),
            payload={},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, CounterSnapshotResult)
        assert result.snapshot["goto_counter"] == {"T01": 2}
        assert result.snapshot["inject_before_counter"] == {"T02": 1}
        assert result.snapshot["skip_to_counter"] == {"T03": 1}
        assert result.snapshot["step_evolution_counter"] == {"T04": 1}
        assert result.contributor == "goto_counter"

    def test_event_bus_merge_to_counter_diff(self):
        """完整路徑：plugin → EventBus → MergedResult.counter_diff。"""
        from autoclaude.core.event_bus import EventBus
        from autoclaude.core.hookspec import HookContext, KernelPhase
        from autoclaude.models.playbook import GlobalInvariants, Playbook
        bus = EventBus()
        plugin = GotoCounterPlugin()
        plugin.increment_goto("T01")
        bus.register(plugin)
        ctx = HookContext(
            phase=KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,
            playbook=Playbook(version="1.0", project="t",
                              global_invariants=GlobalInvariants(), tasks=[]),
            payload={},
        )
        merged = bus.emit(ctx)
        assert merged.counter_diff["goto_counter"] == {"T01": 1}
        assert merged.counter_diff["inject_before_counter"] == {}
        assert merged.counter_diff["skip_to_counter"] == {}
        assert merged.counter_diff["step_evolution_counter"] == {}

    # SD_06 W6（T6-8）：mutable container backward compat 路徑已物理拔除；
    # 原 test_backward_compat_container_write / test_backward_compat_legacy_snapshot_out_key
    # 兩個測試（測 `counter_snapshot_out` / `snapshot_out` payload 寫入）一併移除。


class TestGap042Gap048CrossSession:
    """SA 補：Gap-042 / Gap-048 跨 session 防護端對端驗證。"""

    def test_gap042_goto_counter_survives_restore(self):
        """模擬 TOKEN_HALT → checkpoint 持久化 → 跨 session 還原。"""
        plugin = GotoCounterPlugin()
        plugin.increment_goto("T01")
        plugin.increment_goto("T01")
        plugin.increment_goto("T01")
        # 持久化 snapshot
        snap = plugin.snapshot()
        assert snap.goto_counter["T01"] == 3
        # 模擬「新 session」：建新 plugin 從 snap 還原
        new_plugin = GotoCounterPlugin()
        new_plugin.restore(snap)
        assert new_plugin.goto_counter["T01"] == 3
        # 新 session 內遞增，繼續累積
        new_plugin.increment_goto("T01")
        assert new_plugin.goto_counter["T01"] == 4

    def test_gap048_step_evolution_survives_restore(self):
        """跨 ESC+F12 / TOKEN_HALT 中斷的 step_evolution 計數保留。"""
        plugin = GotoCounterPlugin()
        plugin.increment_step_evolution("T01")
        plugin.increment_step_evolution("T01")
        snap = plugin.snapshot()
        # 跨 session
        new_plugin = GotoCounterPlugin()
        new_plugin.restore(snap)
        assert new_plugin.step_evolution_counter["T01"] == 2

    def test_simulate_run_steps_mutation_writes_to_plugin(self):
        """模擬 _apply_single_mutation_full 透過 alias 寫入 counter。"""
        plugin = GotoCounterPlugin()
        _goto_counter = plugin.goto_counter
        _inject_before_counter = plugin.inject_before_counter
        # 模擬 GOTO_STEP mutation 套用（_runner_internals line 1651）
        _goto_counter["T01"] = _goto_counter.get("T01", 0) + 1
        # 模擬 INJECT_BEFORE mutation 套用（line 1559）
        _inject_before_counter["T02"] = _inject_before_counter.get("T02", 0) + 1
        # plugin 必看到（SSOT）
        assert plugin.goto_counter["T01"] == 1
        assert plugin.inject_before_counter["T02"] == 1
        # snapshot 持久化也看到
        snap = plugin.snapshot()
        assert snap.goto_counter["T01"] == 1
        assert snap.inject_before_counter["T02"] == 1
