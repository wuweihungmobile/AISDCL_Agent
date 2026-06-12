"""CheckpointPlugin 與 GotoCounterPlugin 解耦測試（W4-T17 / M-11）。

驗證 CheckpointPlugin 不再直接持有 GotoCounterPlugin 參考，
改透過 EventBus 廣播 ON_CHECKPOINT_RESTORE / ON_CHECKPOINT_SAVE_REQUEST。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.counter_snapshot import CounterSnapshot
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import CheckpointPlugin, GotoCounterPlugin
from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint


def _pb() -> Playbook:
    return Playbook(
        version="1.0",
        project="P",
        global_invariants=GlobalInvariants(),
        tasks=[PlaybookTask(step_id="T01", name="n", prompt="p")],
    )


def _build_wired(tmp_path: Path) -> tuple[EventBus, CheckpointPlugin, GotoCounterPlugin, CheckpointManager]:
    bus = EventBus()
    mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
    cp_plugin = CheckpointPlugin(checkpoint_manager=mgr)  # 不傳 goto_counter
    goto = GotoCounterPlugin()
    bus.register(goto)
    bus.register(cp_plugin)
    cp_plugin.attach_bus(bus)
    return bus, cp_plugin, goto, mgr


class TestCheckpointGotoDecoupling:
    """W4-T17：解耦驗證 4 個必要測試 + 額外覆蓋。"""

    def test_checkpoint_emits_on_restore_event(self, tmp_path: Path) -> None:
        """CheckpointPlugin._on_pre_run 應 emit ON_CHECKPOINT_RESTORE。"""
        bus, cp_plugin, goto, mgr = _build_wired(tmp_path)

        # 先寫入一筆 checkpoint，使 PRE_RUN 載入後有實際 snapshot 可廣播
        playbook_path = str(tmp_path / "demo.yaml")
        cp = PlaybookCheckpoint(
            playbook_path=playbook_path,
            step_idx=2,
            step_id="T03",
            total_steps=5,
            goto_counter={"T02": 3},
            inject_before_counter={"T01": 1},
            skip_to_counter={"T04": 2},
            step_evolution_counter={"T03": 1},
        )
        mgr.save(cp, playbook_path)

        captured: list[HookContext] = []
        original_emit = bus.emit

        def spy_emit(ctx: HookContext):  # type: ignore[no-redef]
            captured.append(ctx)
            return original_emit(ctx)

        bus.emit = spy_emit  # type: ignore[assignment]

        # 觸發 PRE_RUN
        cp_plugin._on_pre_run(HookContext(
            phase=KernelPhase.PRE_RUN,
            playbook=_pb(),
            payload={"playbook_path": playbook_path},
        ))

        restore_emissions = [c for c in captured if c.phase == KernelPhase.ON_CHECKPOINT_RESTORE]
        assert len(restore_emissions) == 1, "CheckpointPlugin 應 emit ON_CHECKPOINT_RESTORE 一次"
        assert "counter_snapshot" in restore_emissions[0].payload
        assert "checkpoint" in restore_emissions[0].payload
        # W4 三方審查 Dev-W4-Maj-3：驗證真正路由生效
        # （spy_emit 保留呼叫 original_emit，故 GotoCounterPlugin 應已透過 EventBus 收到事件並更新狀態）
        assert goto.snapshot().goto_counter == {"T02": 3}, "EventBus 路由未生效"

    def test_goto_counter_receives_restore_event_and_updates_state(self, tmp_path: Path) -> None:
        """GotoCounterPlugin 訂閱 ON_CHECKPOINT_RESTORE 並還原 counter。"""
        bus, cp_plugin, goto, mgr = _build_wired(tmp_path)

        playbook_path = str(tmp_path / "demo.yaml")
        cp = PlaybookCheckpoint(
            playbook_path=playbook_path,
            step_idx=0,
            step_id="T01",
            total_steps=3,
            goto_counter={"T01": 5, "T02": 2},
            inject_before_counter={"T01": 1},
            skip_to_counter={},
            step_evolution_counter={"T02": 1},
        )
        mgr.save(cp, playbook_path)

        cp_plugin._on_pre_run(HookContext(
            phase=KernelPhase.PRE_RUN,
            playbook=_pb(),
            payload={"playbook_path": playbook_path},
        ))

        snap = goto.snapshot()
        assert snap.goto_counter == {"T01": 5, "T02": 2}
        assert snap.inject_before_counter == {"T01": 1}
        assert snap.step_evolution_counter == {"T02": 1}

    def test_checkpoint_save_collects_goto_snapshot_via_event(self, tmp_path: Path) -> None:
        """CheckpointPlugin._build_checkpoint 應透過 ON_CHECKPOINT_SAVE_REQUEST
        從 GotoCounterPlugin 收集 snapshot。"""
        bus, cp_plugin, goto, mgr = _build_wired(tmp_path)

        # 先讓 GotoCounter 累積一些值
        goto.increment_goto("T01")
        goto.increment_goto("T01")
        goto.increment_inject_before("T02")
        goto.increment_step_evolution("T03")

        playbook_path = str(tmp_path / "demo.yaml")
        built = cp_plugin._build_checkpoint(
            HookContext(
                phase=KernelPhase.ON_INTERRUPT,
                playbook=_pb(),
                payload={"playbook_path": playbook_path, "step_idx": 0},
            ),
            {"playbook_path": playbook_path, "step_idx": 0},
        )
        assert built is not None
        assert built.goto_counter == {"T01": 2}
        assert built.inject_before_counter == {"T02": 1}
        assert built.step_evolution_counter == {"T03": 1}

    def test_two_plugins_have_no_direct_reference(self, tmp_path: Path) -> None:
        """SD_05 W6：CheckpointPlugin.__init__ 不再支援 goto_counter_plugin 參數，
        且 attribute `_goto_counter` 已徹底拔除（解耦完整）。"""
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        cp_plugin = CheckpointPlugin(checkpoint_manager=mgr)
        assert not hasattr(cp_plugin, "_goto_counter"), (
            "SD_05 W6：_goto_counter 屬性已拔除，CheckpointPlugin 不可保留任何直接參照"
        )
        # attach_bus 後仍不應 lazy 建立任何 goto counter 直接引用（純 EventBus 路徑）
        cp_plugin.attach_bus(EventBus())
        assert not hasattr(cp_plugin, "_goto_counter")

    def test_deprecated_goto_counter_plugin_kwarg_emits_warning(self, tmp_path: Path) -> None:
        """SD_05 W6 四方審議 QA 條件補強：deprecated alias `goto_counter_plugin=...` 仍可呼叫
        並觸發 DeprecationWarning（過渡期）；plugin 本身不持有任何 _goto_counter 屬性。"""
        import warnings as _warnings
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        goto = GotoCounterPlugin()
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            cp_plugin = CheckpointPlugin(
                checkpoint_manager=mgr,
                goto_counter_plugin=goto,  # deprecated 過渡 alias
            )
        deprecation = [
            w for w in caught
            if issubclass(w.category, DeprecationWarning)
            and "goto_counter_plugin" in str(w.message)
        ]
        assert deprecation, "deprecated alias `goto_counter_plugin=...` 應觸發 DeprecationWarning"
        # 但 plugin 仍**不**持有 _goto_counter（pop 後忽略）
        assert not hasattr(cp_plugin, "_goto_counter")

    def test_unknown_kwarg_raises_type_error(self, tmp_path: Path) -> None:
        """SD_05 W6 四方審議 QA 條件補強：未知 keyword argument 應 raise TypeError。"""
        import pytest as _pytest
        mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
        with _pytest.raises(TypeError, match="未知 keyword argument"):
            CheckpointPlugin(
                checkpoint_manager=mgr,
                some_unknown_kwarg=True,  # 未知參數
            )
