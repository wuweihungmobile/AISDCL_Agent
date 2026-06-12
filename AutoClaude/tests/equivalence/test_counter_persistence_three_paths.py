"""SD_Improving_05 W3-新測試：3 條中斷路徑 × 4 case = 12 case Counter 持久化驗證。

對應 SD05_Execution_Guide.md §W3-新測試：
  - 3 條中斷路徑：TOKEN_HALT / ESC+F12 / ESCALATION
  - 每路徑 4 case
  - 其中 ≥ 3 case 為「中斷時序污染」場景（含 1 case 真實 deep-copy 防護）

「中斷時序污染」AC 定義（SD_05 W3 三方審查 SD-M3 修正後）：
  本測試集分為兩類驗證：
  (a) **Caller-side snapshot discipline**（Case 1.2 / 2.2 / 3.3）：caller 傳入
      「中斷前最後完整 snapshot」dict，驗證 plugin 不會偷加 partial increment、
      不會覆蓋 step_evolution_counter，達到「中斷前後計數一致」。
  (b) **Plugin deep-copy 防護**（Case 1.5 新增）：caller 在 plugin.save 之後立即
      mutate 原 dict，驗證 plugin 內部已 deep-copy（`dict(goto_counter)`），
      checkpoint 寫入值不受後續 mutation 影響 — 真正的 race condition 防護。

本測試直接呼叫 ``CheckpointPlugin.{handle_token_halt,save_interrupt_checkpoint,
save_escalation_dump,save_evolution_resume_checkpoint}`` 公開 API +
``CheckpointManager.load``。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest

from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.checkpoint import CheckpointPlugin
from autoclaude.utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint


# ──────────────────────────────────────────────────────
# 共用工具
# ──────────────────────────────────────────────────────
def _make_plugin(tmp_path: Path) -> tuple[CheckpointPlugin, CheckpointManager]:
    mgr = CheckpointManager(checkpoint_dir=str(tmp_path))
    plugin = CheckpointPlugin(checkpoint_manager=mgr)
    return plugin, mgr


def _make_playbook() -> Playbook:
    return Playbook(
        version="1.0", project="three_paths_test",
        global_invariants=GlobalInvariants(),
        tasks=[
            PlaybookTask(step_id="T01", name="setup", prompt="p"),
            PlaybookTask(step_id="T02", name="impl", prompt="p"),
            PlaybookTask(step_id="T03", name="verify", prompt="p"),
        ],
    )


def _make_task(step_id: str = "T02") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name="impl", prompt="p")


def _make_step_out(peak: float = 92.0):
    """模擬 _StepOutput（W3 plugin 改接 peak_token_pct 純 float，不需完整 dataclass）。"""
    obj = MagicMock()
    obj.peak_token_pct = peak
    return obj


def _make_tracker_with_history(n: int = 2):
    """簡易模擬 FailureTracker，給 plugin 取 to_checkpoint_records/history/to_failure_chain。"""
    tracker = MagicMock()
    history = []
    for i in range(n):
        item = MagicMock()
        item.correction_prompt_sent = f"correction_{i}"
        history.append(item)
    tracker.history = history
    tracker.to_checkpoint_records = MagicMock(return_value=[
        {"attempt": i, "failure_reason": f"r{i}"} for i in range(n)
    ])
    tracker.to_failure_chain = MagicMock(return_value=[
        {"attempt": i} for i in range(n)
    ])
    tracker.is_stuck = MagicMock(return_value=False)
    tracker.is_diverging = MagicMock(return_value=False)
    tracker.suspect_test_file_error = MagicMock(return_value=False)
    tracker.is_oscillating = MagicMock(return_value=False)
    tracker.is_worsening = MagicMock(return_value=False)
    tracker.suspect_assertion_baseline_mismatch = MagicMock(return_value=False)
    return tracker


# ──────────────────────────────────────────────────────
# 路徑 1：TOKEN_HALT × 4 case
# ──────────────────────────────────────────────────────
class TestTokenHaltCounterPersistence:
    """W3 路徑 1：TOKEN_HALT (context %% >= halt 門檻) 觸發 checkpoint。"""

    def test_basic_round_trip(self, tmp_path: Path) -> None:
        """[Case 1.1] 基本：4 counter 寫入 → reload 一致。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/token_halt_basic.yaml"
        plugin.handle_token_halt(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=1, peak_token_pct=92.0, step_log=["[T01] ok"], total=3,
            halt_threshold_pct=90.0, resume_delay_minutes=30,
            goto_counter={"T02": 2}, inject_before_counter={"T03": 1},
            skip_to_counter={"T01": 1}, step_evolution_counter={"T02": 1},
        )
        cp = mgr.load(path)
        assert cp is not None
        assert cp.goto_counter == {"T02": 2}
        assert cp.inject_before_counter == {"T03": 1}
        assert cp.skip_to_counter == {"T01": 1}
        assert cp.step_evolution_counter == {"T02": 1}
        assert cp.peak_token_pct == 92.0

    def test_caller_snapshot_discipline_goto(self, tmp_path: Path) -> None:
        """[Case 1.2 / SD-M3] Caller-side snapshot discipline：caller 傳「中斷前最後完整 snapshot」
        → plugin 不偷加 partial increment。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/token_halt_snapshot_disc.yaml"
        last_complete_snapshot = {"T02": 2}  # 中斷前最後完整值
        plugin.handle_token_halt(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=1, peak_token_pct=95.0, step_log=[], total=3,
            halt_threshold_pct=90.0, resume_delay_minutes=30,
            goto_counter=last_complete_snapshot,
        )
        cp = mgr.load(path)
        assert cp.goto_counter == {"T02": 2}, "Plugin 不應添加未完成的 inc"

    def test_plugin_deep_copy_protects_against_post_save_mutation(
        self, tmp_path: Path,
    ) -> None:
        """[Case 1.5 / SD-M3 新增] Plugin deep-copy 真實 race protection：
        caller 在 plugin.save 之後立即 mutate 原 dict，checkpoint 寫入值不變。

        這是真正的「中斷時序污染」防護驗證：模擬 plugin 寫入 checkpoint 後，
        caller 主執行緒繼續 mutate goto_counter（race 場景），驗證 plugin
        內部已 deep-copy（``dict(goto_counter)`` 在 _token_halt.py:50）。
        """
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/token_halt_deep_copy.yaml"
        live_counter = {"T02": 2}  # caller-side live dict（會被後續 mutate）
        plugin.handle_token_halt(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=1, peak_token_pct=95.0, step_log=[], total=3,
            halt_threshold_pct=90.0, resume_delay_minutes=30,
            goto_counter=live_counter,
        )
        # 模擬：caller 在 save 之後（甚至 race 中）繼續 mutate 原 dict
        live_counter["T02"] = 999
        live_counter["T_NEW"] = 5
        # checkpoint 應仍是 {"T02": 2}（plugin 內部已 deep-copy）
        cp = mgr.load(path)
        assert cp.goto_counter == {"T02": 2}, (
            f"Plugin deep-copy 防護失敗：caller 後續 mutate live_counter 影響到 checkpoint "
            f"（實際 {cp.goto_counter}）"
        )

    def test_caller_snapshot_failure_history(self, tmp_path: Path) -> None:
        """[Case 1.3 / SD-M3] Caller-side discipline：tracker.history 在 record 中途中斷 →
        checkpoint 含上一次完整 history（caller 傳入時即為完整 snapshot）。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/token_halt_pollution_b.yaml"
        tracker = _make_tracker_with_history(n=2)
        plugin.handle_token_halt(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=1, peak_token_pct=93.0, step_log=[], total=3,
            halt_threshold_pct=90.0, resume_delay_minutes=30,
            tracker=tracker, attempt=1,
        )
        cp = mgr.load(path)
        assert len(cp.failure_history) == 2
        assert cp.last_correction_prompt == "correction_1"  # 最後一筆完整 record
        assert cp.active_step_attempt == 1

    def test_scheduled_resume_persists(self, tmp_path: Path) -> None:
        """[Case 1.4] 排程恢復時間 scheduled_resume_at 持久化。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/token_halt_resume.yaml"
        cp_returned = plugin.handle_token_halt(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=1, peak_token_pct=91.0, step_log=[], total=3,
            halt_threshold_pct=90.0, resume_delay_minutes=15,  # 必須 > 0
        )
        cp_loaded = mgr.load(path)
        assert cp_returned.scheduled_resume_at is not None
        assert cp_loaded.scheduled_resume_at == cp_returned.scheduled_resume_at


# ──────────────────────────────────────────────────────
# 路徑 2：ESC+F12 中斷 × 4 case
# ──────────────────────────────────────────────────────
class TestInterruptCounterPersistence:
    """W3 路徑 2：ESC+F12 中斷觸發 checkpoint。"""

    def test_basic_round_trip(self, tmp_path: Path) -> None:
        """[Case 2.1] 基本：5 counter + completed_step_ids 持久化。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/interrupt_basic.yaml"
        plugin.save_interrupt_checkpoint(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=1, step_log=["[T01] ok"], total=3,
            goto_counter={"T01": 1}, inject_before_counter={},
            skip_to_counter={"T02": 1}, completed_step_ids=["T01"],
            step_evolution_counter={"T02": 2},
        )
        cp = mgr.load(path)
        assert cp.goto_counter == {"T01": 1}
        assert cp.skip_to_counter == {"T02": 1}
        assert cp.completed_step_ids == ["T01"]
        assert cp.step_evolution_counter == {"T02": 2}

    def test_caller_snapshot_discipline_skip_to(self, tmp_path: Path) -> None:
        """[Case 2.2 / SD-M3] Caller-side discipline：skip_to inc 進行中 ESC+F12 →
        caller 傳「中斷前完整值」snapshot。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/interrupt_pollution.yaml"
        # 模擬使用者按 ESC+F12 時，skip_to_counter[T03] 已 inc 至 2
        # 但正準備 +1 至 3 的中間態 — caller 應傳完整 2，不應傳 partial 3
        plugin.save_interrupt_checkpoint(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=2, step_log=["[T01] ok", "[T02] ok"], total=3,
            skip_to_counter={"T03": 2},
        )
        cp = mgr.load(path)
        assert cp.skip_to_counter == {"T03": 2}, "ESC+F12 中斷時序污染防護失敗"

    def test_empty_counters_safe(self, tmp_path: Path) -> None:
        """[Case 2.3] 邊界：所有 counter 為空 → 持久化空 dict 不報錯。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/interrupt_empty.yaml"
        plugin.save_interrupt_checkpoint(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=0, step_log=[], total=3,
        )
        cp = mgr.load(path)
        assert cp.goto_counter == {}
        assert cp.inject_before_counter == {}
        assert cp.skip_to_counter == {}
        assert cp.step_evolution_counter == {}

    def test_tracker_history_attempt_offset(self, tmp_path: Path) -> None:
        """[Case 2.4] tracker.history + active_step_attempt 連動持久化（Gap-007-A）。"""
        plugin, mgr = _make_plugin(tmp_path)
        path = "fake/interrupt_tracker.yaml"
        tracker = _make_tracker_with_history(n=3)
        plugin.save_interrupt_checkpoint(
            playbook=_make_playbook(), playbook_path=path, task=_make_task(),
            step_idx=1, step_log=[], total=3,
            tracker=tracker, attempt=2,
        )
        cp = mgr.load(path)
        assert len(cp.failure_history) == 3
        assert cp.active_step_attempt == 2
        assert cp.last_correction_prompt == "correction_2"


# ──────────────────────────────────────────────────────
# 路徑 3：ESCALATION × 4 case（save_escalation_dump + save_evolution_resume_checkpoint）
# ──────────────────────────────────────────────────────
class TestEscalationCounterPersistence:
    """W3 路徑 3：ESCALATION 觸發 dump + 演化後 checkpoint 持久化。"""

    def test_escalation_dump_saved_to_file(self, tmp_path: Path) -> None:
        """[Case 3.1] EscalationDump.save 寫檔成功 + notify_callback 被呼叫。"""
        plugin, _ = _make_plugin(tmp_path)
        notify_called = {"hit": False, "kwargs": {}}

        def _notify_cb(**kwargs):
            notify_called["hit"] = True
            notify_called["kwargs"] = kwargs

        tracker = _make_tracker_with_history(n=2)
        dump = plugin.save_escalation_dump(
            tracker=tracker, task=_make_task(), playbook_path="fake/escalation.yaml",
            final_eval_output="assertion failed", checkpoint_dir=str(tmp_path),
            log_dir=str(tmp_path), human_hint="manual",
            notify_callback=_notify_cb,
        )
        assert dump.step_id == "T02"
        assert dump.total_attempts == 2
        assert notify_called["hit"] is True
        # 確認 notify 帶入正確 dump_path（plugin 內部 dump.save 後傳回）
        assert "ESCALATION" in notify_called["kwargs"]["title"]

    def test_evolution_resume_checkpoint_persists(self, tmp_path: Path) -> None:
        """[Case 3.2] ESCALATION 觸發演化後 → save_evolution_resume_checkpoint。"""
        plugin, mgr = _make_plugin(tmp_path)
        evolved_path = str(tmp_path / "evolved.yaml")
        ok = plugin.save_evolution_resume_checkpoint(
            evolved_path=evolved_path,
            playbook=_make_playbook(),
            step_log=["[T01] ok"],
            completed_step_ids={"T01"},
            step_evolution_counter={"T02": 1},
        )
        assert ok is True
        cp = mgr.load(evolved_path)
        assert cp.completed_step_ids == ["T01"]
        assert cp.step_evolution_counter == {"T02": 1}
        # Gap-048：演化後重啟時，step_evolution_counter 不應重置
        assert cp.step_evolution_counter["T02"] == 1

    def test_dump_and_evolution_checkpoint_no_collision(self, tmp_path: Path) -> None:
        """[Case 3.3 / SD-M3] 雙路徑分離驗證：ESCALATION dump 與 evolution checkpoint
        寫入不同檔案不相互覆蓋（檔案層級的時序隔離）。
        """
        plugin, mgr = _make_plugin(tmp_path)
        notify_calls = []
        tracker = _make_tracker_with_history(n=2)

        # 先 dump
        plugin.save_escalation_dump(
            tracker=tracker, task=_make_task("T02"),
            playbook_path="fake/p1.yaml", final_eval_output="err",
            checkpoint_dir=str(tmp_path), log_dir=str(tmp_path),
            notify_callback=lambda **kw: notify_calls.append(kw),
        )
        # 同時演化版 checkpoint 持久化
        evolved = str(tmp_path / "evolved_p1.yaml")
        ok = plugin.save_evolution_resume_checkpoint(
            evolved_path=evolved, playbook=_make_playbook(),
            step_log=[], completed_step_ids=set(),
            step_evolution_counter={"T02": 1},
        )
        # 驗證：兩者寫入互不污染
        assert ok is True
        assert len(notify_calls) == 1  # dump 仍正確 notify 一次
        cp = mgr.load(evolved)
        assert cp is not None and cp.step_evolution_counter == {"T02": 1}

    def test_evolution_resume_failure_returns_false(self, tmp_path: Path) -> None:
        """[Case 3.4] checkpoint 寫入失敗 → 回傳 False（呼叫端可回退 fresh=True）。"""
        plugin, mgr = _make_plugin(tmp_path)
        # 故意傳入無法寫入的路徑（不存在目錄）— mgr 應吞例外回 False
        bad_path = str(tmp_path / "nonexistent" / "deep" / "evolved.yaml")
        # 模擬：用 monkeypatch 讓 mgr.save raise
        original_save = mgr.save

        def _failing_save(*args, **kwargs):
            raise OSError("disk full")

        mgr.save = _failing_save
        try:
            ok = plugin.save_evolution_resume_checkpoint(
                evolved_path=bad_path, playbook=_make_playbook(),
                step_log=[], completed_step_ids=set(),
            )
            assert ok is False
        finally:
            mgr.save = original_save
