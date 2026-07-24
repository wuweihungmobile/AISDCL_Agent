"""CheckpointPlugin 單元測試（Phase 3 / W8 #9，≥ 12 cases）。

驗證：
  - PRE_RUN：載入 checkpoint 並 push 到 GotoCounterPlugin（Gap-042/048）
  - ON_INTERRUPT：儲存帶計數器 snapshot 的 checkpoint
  - ON_TOKEN_USAGE (request_halt)：儲存 + 排程恢復
  - ON_EVOLUTION：儲存
  - POST_STEP：不主動清除
  - 公開 API：load / save / clear
"""
from __future__ import annotations

from pathlib import Path

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import (
    CheckpointPlugin,
    GotoCounterPlugin,
)
from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(),
                    tasks=[PlaybookTask(step_id="T01", name="n", prompt="p")])


def _task() -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p")


def _make_plugin(
    tmp_path: Path, with_counter: bool = True
) -> tuple[CheckpointPlugin, GotoCounterPlugin]:
    """SD_05 W6：CheckpointPlugin 不再持有 GotoCounterPlugin 參考。

    解耦透過 EventBus 廣播 ON_CHECKPOINT_RESTORE / ON_CHECKPOINT_SAVE_REQUEST 完成。
    `with_counter=True` 時將兩個 plugin 註冊至同一 EventBus 並 attach 給 checkpoint plugin。
    """
    counter = GotoCounterPlugin()
    mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
    plugin = CheckpointPlugin(checkpoint_manager=mgr)
    if with_counter:
        bus = EventBus()
        bus.register(counter)
        bus.register(plugin)
        plugin.attach_bus(bus)
    return plugin, counter


class TestCheckpointPluginBasics:
    def test_name(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        assert plugin.name() == "checkpoint"

    def test_priority_is_90(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        assert plugin.priority() == 90

    def test_subscribed_phases_includes_persistence_events(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        phases = plugin.subscribed_phases()
        assert KernelPhase.PRE_RUN in phases
        assert KernelPhase.ON_INTERRUPT in phases
        assert KernelPhase.ON_TOKEN_USAGE in phases
        assert KernelPhase.ON_EVOLUTION in phases
        assert KernelPhase.POST_STEP in phases


class TestCheckpointPluginPreRunRestore:
    def test_pre_run_loads_and_pushes_to_goto_counter_gap_042(self, tmp_path):
        plugin, counter = _make_plugin(tmp_path)
        # 預先寫入一個 checkpoint
        cp = PlaybookCheckpoint(
            playbook_path="x.yaml", step_idx=2, step_id="T02", total_steps=3,
            goto_counter={"T01": 2}, step_evolution_counter={"T03": 1},
        )
        plugin.save_checkpoint("x.yaml", cp)
        # PRE_RUN 觸發
        ctx = HookContext(
            phase=KernelPhase.PRE_RUN, playbook=_pb(),
            payload={"playbook_path": "x.yaml"},
        )
        plugin.on_event(ctx)
        # GotoCounterPlugin 應已被推送
        snap = counter.snapshot()
        assert snap.goto_counter == {"T01": 2}
        assert snap.step_evolution_counter == {"T03": 1}

    def test_pre_run_no_payload_safe(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb())
        # 不應拋例外
        assert plugin.on_event(ctx) is None

    def test_pre_run_no_checkpoint_file_safe(self, tmp_path):
        plugin, counter = _make_plugin(tmp_path)
        ctx = HookContext(
            phase=KernelPhase.PRE_RUN, playbook=_pb(),
            payload={"playbook_path": "nonexistent.yaml"},
        )
        plugin.on_event(ctx)
        # counter 仍為空
        assert counter.snapshot().goto_counter == {}


class TestCheckpointPluginOnInterrupt:
    def test_save_interrupt_with_counter_snapshot(self, tmp_path):
        plugin, counter = _make_plugin(tmp_path)
        counter.increment_goto("T01")
        counter.increment_step_evolution("T05")

        ctx = HookContext(
            phase=KernelPhase.ON_INTERRUPT, playbook=_pb(),
            task=_task(), step_idx=0, attempt=1,
            payload={
                "playbook_path": "y.yaml",
                "step_idx": 0, "step_id": "T01",
                "completed_step_ids": ["T00"],
            },
        )
        plugin.on_event(ctx)
        cp = plugin.load_checkpoint("y.yaml")
        assert cp is not None
        assert cp.goto_counter == {"T01": 1}
        assert cp.step_evolution_counter == {"T05": 1}
        assert cp.completed_step_ids == ["T00"]

    def test_save_interrupt_no_path_no_save(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        ctx = HookContext(
            phase=KernelPhase.ON_INTERRUPT, playbook=_pb(), task=_task(),
        )
        plugin.on_event(ctx)
        # 無 playbook_path 時不應呼叫 save
        # 透過 ls 驗證沒有檔案被寫入
        files = list(tmp_path.glob("*.checkpoint.json"))
        assert len(files) == 0


class TestCheckpointPluginOnTokenUsage:
    def test_save_only_when_request_halt(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        # request_halt=False → 不儲存
        plugin.on_event(HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(),
            payload={"playbook_path": "z.yaml", "request_halt": False},
        ))
        assert plugin.load_checkpoint("z.yaml") is None

    def test_save_when_request_halt_true_with_resume_delay(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        plugin.on_event(HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={
                "playbook_path": "z.yaml",
                "request_halt": True,
                "resume_delay_minutes": 5,
                "step_idx": 1,
            },
        ))
        cp = plugin.load_checkpoint("z.yaml")
        assert cp is not None
        assert cp.scheduled_resume_at is not None  # 已排程恢復


class TestCheckpointPluginOnEvolution:
    def test_save_evolution_with_counter(self, tmp_path):
        plugin, counter = _make_plugin(tmp_path)
        counter.increment_step_evolution("T03")
        plugin.on_event(HookContext(
            phase=KernelPhase.ON_EVOLUTION, playbook=_pb(), task=_task(),
            payload={"playbook_path": "evo.yaml", "step_idx": 2},
        ))
        cp = plugin.load_checkpoint("evo.yaml")
        assert cp is not None
        assert cp.step_evolution_counter == {"T03": 1}


class TestCheckpointPluginPostStep:
    def test_post_step_does_not_auto_clear(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        # 先寫入 checkpoint
        cp = PlaybookCheckpoint(
            playbook_path="x.yaml", step_idx=0, step_id="T01", total_steps=1,
        )
        plugin.save_checkpoint("x.yaml", cp)
        # POST_STEP 不應清除
        plugin.on_event(HookContext(
            phase=KernelPhase.POST_STEP, playbook=_pb(), task=_task(),
        ))
        assert plugin.load_checkpoint("x.yaml") is not None


class TestCheckpointPluginPublicApi:
    def test_clear_removes_checkpoint(self, tmp_path):
        plugin, _ = _make_plugin(tmp_path)
        cp = PlaybookCheckpoint(
            playbook_path="x.yaml", step_idx=0, step_id="T01", total_steps=1,
        )
        plugin.save_checkpoint("x.yaml", cp)
        assert plugin.load_checkpoint("x.yaml") is not None
        plugin.clear_checkpoint("x.yaml")
        assert plugin.load_checkpoint("x.yaml") is None


class TestW3PersistenceRequestPositive:
    """SD_05 W3 三方審查 SA-M1 + SD-M1：補 ON_PERSISTENCE_REQUEST /
    ON_ESCALATION_DUMP_REQUEST 正向 IHookResult 回傳測試（含失敗分支）。
    """

    def test_persistence_request_evolution_resume_returns_result(self, tmp_path):
        from autoclaude.core.hookspec import PersistenceResult
        plugin, _ = _make_plugin(tmp_path)
        evolved = str(tmp_path / "evolved.yaml")
        ctx = HookContext(
            phase=KernelPhase.ON_PERSISTENCE_REQUEST, playbook=_pb(), task=_task(),
            payload={
                "kind": "evolution_resume",
                "evolved_path": evolved,
                "step_log": ["[T01] ok"],
                "completed_step_ids": {"T01"},
                "step_evolution_counter": {"T02": 1},
            },
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, PersistenceResult)
        assert result.succeeded is True
        assert result.path == evolved
        assert result.kind == "checkpoint"

    def test_persistence_request_interrupt_returns_result(self, tmp_path):
        from autoclaude.core.hookspec import PersistenceResult
        plugin, _ = _make_plugin(tmp_path)
        ctx = HookContext(
            phase=KernelPhase.ON_PERSISTENCE_REQUEST, playbook=_pb(), task=_task(),
            payload={
                "kind": "interrupt",
                "playbook_path": "x.yaml",
                "step_idx": 0,
                "step_log": [],
                "total": 1,
                "goto_counter": {"T01": 1},
            },
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, PersistenceResult)
        assert result.succeeded is True
        assert result.kind == "interrupt"
        assert result.path == "x.yaml"

    def test_escalation_dump_request_returns_real_dump_path(self, tmp_path):
        """SD_05 W3 Arch-C1/SD-C1 修復驗證：EscalationDumpedResult.dump_path
        必須等於 dump.save() 真實寫入路徑（非手構字串）。"""
        from unittest.mock import MagicMock

        from autoclaude.core.hookspec import EscalationDumpedResult
        plugin, _ = _make_plugin(tmp_path)
        tracker = MagicMock()
        tracker.history = []
        tracker.to_checkpoint_records = MagicMock(return_value=[])
        tracker.to_failure_chain = MagicMock(return_value=[])
        for m in ("is_stuck", "is_diverging", "suspect_test_file_error",
                  "is_oscillating", "is_worsening",
                  "suspect_assertion_baseline_mismatch"):
            setattr(tracker, m, MagicMock(return_value=False))
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION_DUMP_REQUEST,
            playbook=_pb(), task=_task(),
            payload={
                "tracker": tracker,
                "playbook_path": "x.yaml",
                "final_eval_output": "err",
                "checkpoint_dir": str(tmp_path),
                "log_dir": str(tmp_path),
            },
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, EscalationDumpedResult)
        # SD_05 W3 Arch-C1/SD-C1 修：dump_path 必須是真實 dump.save() 寫入路徑
        # （EscalationDump.save 預期格式 escalation_{step_id}_{timestamp}.md）
        from pathlib import Path as _P
        assert result.dump_path != ""
        assert _P(result.dump_path).exists(), (
            f"EscalationDumpedResult.dump_path={result.dump_path} 必須指向真實檔案"
        )
        assert "T01" in result.dump_path

    def test_escalation_dump_save_failure_notifies_with_none_path(
        self, tmp_path, monkeypatch,
    ):
        """SD_05 W3 SD-M1 修復驗證：dump.save 失敗時 notify_callback 收到 dump_path=None。"""
        from unittest.mock import MagicMock

        from autoclaude.models import escalation as esc_mod

        plugin, _ = _make_plugin(tmp_path)
        # 讓 EscalationDump.save 拋例外
        def _failing_save(self, dump_dir):
            raise OSError("disk full")
        monkeypatch.setattr(esc_mod.EscalationDump, "save", _failing_save)

        tracker = MagicMock()
        tracker.history = []
        tracker.to_checkpoint_records = MagicMock(return_value=[])
        tracker.to_failure_chain = MagicMock(return_value=[])
        for m in ("is_stuck", "is_diverging", "suspect_test_file_error",
                  "is_oscillating", "is_worsening",
                  "suspect_assertion_baseline_mismatch"):
            setattr(tracker, m, MagicMock(return_value=False))

        notify_calls = []
        plugin.save_escalation_dump(
            tracker=tracker, task=_task(), playbook_path="x.yaml",
            final_eval_output="err", checkpoint_dir=str(tmp_path),
            log_dir=str(tmp_path),
            notify_callback=lambda **kw: notify_calls.append(kw),
        )
        assert len(notify_calls) == 1
        assert notify_calls[0]["dump_path"] is None, (
            "dump.save 失敗時 notify_callback dump_path 必須為 None（不是空字串）"
        )

    def test_escalation_dump_sanitizes_step_id_with_windows_forbidden_chars(
        self, tmp_path,
    ):
        """DEF-101（Mac/Windows 相容性）：task.step_id 是完全自由格式欄位，playbook
        作者手寫 YAML 可能寫成 "Step 1: Setup" 這種含冒號的自然字串。驗證：
        (1) dump.save() 實際落地的檔名不含任何 Windows 禁用字元；
        (2) last_log_path 顯示字串也套用同一淨化規則，與 RawStreamLogger 實際
            落地時對相同原始檔名產生的結果一致（不再顯示與真實檔案不符的路徑）。
        """
        from pathlib import Path as _P
        from unittest.mock import MagicMock

        from autoclaude.utils.logger import _WIN_FORBIDDEN_CHARS, _sanitize_log_filename

        plugin, _ = _make_plugin(tmp_path)
        tracker = MagicMock()
        tracker.history = []
        tracker.to_checkpoint_records = MagicMock(return_value=[])
        tracker.to_failure_chain = MagicMock(return_value=[])
        for m in ("is_stuck", "is_diverging", "suspect_test_file_error",
                  "is_oscillating", "is_worsening",
                  "suspect_assertion_baseline_mismatch"):
            setattr(tracker, m, MagicMock(return_value=False))

        bad_task = PlaybookTask(step_id="Step 1: Setup", name="n", prompt="p")
        dump = plugin.save_escalation_dump(
            tracker=tracker, task=bad_task, playbook_path="x.yaml",
            final_eval_output="err", checkpoint_dir=str(tmp_path),
            log_dir=str(tmp_path),
        )

        saved_path = _P(plugin._last_dump_path)
        assert saved_path.exists()
        for ch in _WIN_FORBIDDEN_CHARS:
            assert ch not in saved_path.name, (
                f"禁用字元 {ch!r} 洩漏進 EscalationDump 真實落地檔名 {saved_path.name!r}"
            )

        # last_log_path 為純文字顯示欄位（無實體檔案），需與 RawStreamLogger 對
        # 同一原始檔名套用 _sanitize_log_filename() 後的結果一致
        expected_log_name = _sanitize_log_filename("playbook_Step 1: Setup_attempt0.log")
        assert _P(dump.last_log_path).name == expected_log_name
        for ch in _WIN_FORBIDDEN_CHARS:
            assert ch not in dump.last_log_path, (
                f"禁用字元 {ch!r} 洩漏進顯示用 last_log_path {dump.last_log_path!r}"
            )


class TestW3EvolutionPluginNewPhases:
    """SD_05 W3 三方審查 SA-M2：驗證 EvolutionPlugin 訂閱的 NO-OP phase 回 None。"""

    def test_on_evolution_apply_returns_none_no_op(self):
        from autoclaude.plugins import EvolutionPlugin
        plugin = EvolutionPlugin()
        ctx = HookContext(
            phase=KernelPhase.ON_EVOLUTION_APPLY, playbook=_pb(), task=_task(),
            payload={"clear_goal_summary": True},
        )
        assert plugin.on_event(ctx) is None

    def test_on_escalation_dump_request_returns_none_no_op(self):
        from autoclaude.plugins import EvolutionPlugin
        plugin = EvolutionPlugin()
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION_DUMP_REQUEST,
            playbook=_pb(), task=_task(),
        )
        assert plugin.on_event(ctx) is None


class TestCheckpointPluginObserverContract:
    """SD_05 W3-2 更新：CheckpointPlugin 在 W3 後遵循 PHASE_RESULT_CONTRACT，
    ON_INTERRUPT / ON_TOKEN_USAGE(request_halt) / ON_EVOLUTION 等持久化 phase
    必須回傳 PersistenceResult；本測試僅驗證「不應觸發 save 的 phase」回 None。
    """

    def test_returns_none_when_no_persistence_triggered(self, tmp_path):
        """PRE_RUN（無 checkpoint 檔）/ POST_STEP / ON_TOKEN_USAGE(無 halt) /
        ON_PERSISTENCE_REQUEST(無 kind) / ON_ESCALATION_DUMP_REQUEST(無 tracker)
        在無有效觸發條件時應回 None。
        """
        plugin, _ = _make_plugin(tmp_path)
        none_phases = [
            (KernelPhase.PRE_RUN, {"playbook_path": "x.yaml"}),  # 無 checkpoint 檔
            (KernelPhase.POST_STEP, {}),
            (KernelPhase.ON_TOKEN_USAGE, {"playbook_path": "x.yaml"}),  # 無 request_halt
            (KernelPhase.ON_PERSISTENCE_REQUEST, {}),  # 無 kind
            (KernelPhase.ON_ESCALATION_DUMP_REQUEST, {}),  # 無 tracker
        ]
        for phase, payload in none_phases:
            ctx = HookContext(phase=phase, playbook=_pb(), task=_task(), payload=payload)
            assert plugin.on_event(ctx) is None, (
                f"phase={phase} 在 payload={payload} 應回 None"
            )
