"""Counter persistence round-trip（Gap-042 / Gap-048 / Gap-049 真實驗證）。

對應稽核 finding F7：fixture 11/12/13 在 dry_run baseline 下計數器恆為空 dict，
無法真正驗證 Gap-042/048/049 跨 Session 持久化邏輯。本檔以「直接操作
CheckpointManager + GotoCounterPlugin」的方式進行完整 round-trip 驗證：

  - Gap-042（fixture 11 對應）：goto_counter / inject_before_counter / skip_to_counter
    跨 TOKEN_HALT 寫入 checkpoint → 重新載入後計數器值不變
  - Gap-048（fixture 12 對應）：step_evolution_counter 跨 ESC+F12 中斷不重置
  - Gap-049（fixture 13 對應）：max_goto_per_step 配置可覆寫預設值，超出時阻擋

這些測試 **不修改** PlaybookRunner / CheckpointManager / FailureKnowledgeBase
（屬於 Pass 2 範圍），僅透過既有公開 API 驗證計數器欄位的持久化契約。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from autoclaude.plugins.goto_counter_plugin import (
    CounterSnapshot,
    GotoCounterPlugin,
)
from autoclaude.utils.checkpoint_manager import (
    CheckpointManager,
    PlaybookCheckpoint,
)
from autoclaude.utils.config import PlaybookConfig


# ──────────────────────────────────────────────────────
# 共用工具
# ──────────────────────────────────────────────────────
def _make_checkpoint(
    playbook_path: str,
    *,
    goto_counter: dict | None = None,
    inject_before_counter: dict | None = None,
    skip_to_counter: dict | None = None,
    step_evolution_counter: dict | None = None,
) -> PlaybookCheckpoint:
    return PlaybookCheckpoint(
        playbook_path=playbook_path,
        step_idx=1,
        step_id="T02",
        total_steps=3,
        project="counter_persistence_test",
        goto_counter=dict(goto_counter or {}),
        inject_before_counter=dict(inject_before_counter or {}),
        skip_to_counter=dict(skip_to_counter or {}),
        step_evolution_counter=dict(step_evolution_counter or {}),
    )


# ──────────────────────────────────────────────────────
# Gap-042 — fixture 11 對應
# ──────────────────────────────────────────────────────
class TestGap042GotoCounterTokenHalt:
    """Gap-042：goto_counter 跨 TOKEN_HALT 持久化（fixture 11 對應）。"""

    def test_goto_counter_persists_through_token_halt(self, tmp_path: Path) -> None:
        """模擬 GOTO_STEP 累計 → TOKEN_HALT save → resume load 後 counter 不變。"""
        cm = CheckpointManager(checkpoint_dir=str(tmp_path))
        plugin = GotoCounterPlugin()

        # Phase 1：累計 GOTO_STEP（模擬 1 次）
        plugin.increment_goto("T01")
        snap_before = plugin.snapshot()
        assert snap_before.goto_counter == {"T01": 1}

        # Phase 2：模擬 TOKEN_HALT 觸發 checkpoint save
        cp = _make_checkpoint(
            "fake/11_goto_counter.yaml",
            goto_counter=snap_before.goto_counter,
        )
        cm.save(cp, "fake/11_goto_counter.yaml")

        # Phase 3：模擬 resume — 重新建立 plugin + 載入 checkpoint
        cp_loaded = cm.load("fake/11_goto_counter.yaml")
        assert cp_loaded is not None
        assert cp_loaded.goto_counter == {"T01": 1}, "TOKEN_HALT 後 goto_counter 必須持久化"

        plugin_resumed = GotoCounterPlugin()
        plugin_resumed.restore(CounterSnapshot(goto_counter=cp_loaded.goto_counter))
        assert plugin_resumed.snapshot().goto_counter == {"T01": 1}

    def test_inject_before_and_skip_to_counter_persist(self, tmp_path: Path) -> None:
        """Gap-042 完整：inject_before_counter + skip_to_counter 同樣跨 TOKEN_HALT 持久化。"""
        cm = CheckpointManager(checkpoint_dir=str(tmp_path))
        plugin = GotoCounterPlugin()
        plugin.increment_inject_before("T02")
        plugin.increment_inject_before("T02")
        plugin.increment_skip_to("T03")

        snap = plugin.snapshot()
        cp = _make_checkpoint(
            "fake/11b_three_counters.yaml",
            inject_before_counter=snap.inject_before_counter,
            skip_to_counter=snap.skip_to_counter,
        )
        cm.save(cp, "fake/11b_three_counters.yaml")

        cp_loaded = cm.load("fake/11b_three_counters.yaml")
        assert cp_loaded is not None
        assert cp_loaded.inject_before_counter == {"T02": 2}
        assert cp_loaded.skip_to_counter == {"T03": 1}


# ──────────────────────────────────────────────────────
# Gap-048 — fixture 12 對應
# ──────────────────────────────────────────────────────
class TestGap048StepEvolutionCounterEscF12:
    """Gap-048：step_evolution_counter 跨 ESC+F12 中斷不重置（fixture 12 對應）。"""

    def test_step_evolution_counter_survives_esc_f12(self, tmp_path: Path) -> None:
        """演化 1 次後 ESC+F12 中斷 → resume 後 counter 仍 == 1。"""
        cm = CheckpointManager(checkpoint_dir=str(tmp_path))
        plugin = GotoCounterPlugin()

        # 模擬 1 次演化
        plugin.increment_step_evolution("T02")
        snap = plugin.snapshot()
        assert snap.step_evolution_counter == {"T02": 1}

        # ESC+F12 中斷時寫入 checkpoint
        cp = _make_checkpoint(
            "fake/12_evo_counter.yaml",
            step_evolution_counter=snap.step_evolution_counter,
        )
        cm.save(cp, "fake/12_evo_counter.yaml")

        # resume：counter 必須仍 == 1（不歸零）
        cp_loaded = cm.load("fake/12_evo_counter.yaml")
        assert cp_loaded is not None
        assert cp_loaded.step_evolution_counter == {"T02": 1}

        plugin_resumed = GotoCounterPlugin()
        plugin_resumed.restore(
            CounterSnapshot(step_evolution_counter=cp_loaded.step_evolution_counter)
        )
        assert plugin_resumed.snapshot().step_evolution_counter == {"T02": 1}

    def test_max_evolutions_check_uses_persisted_counter(self, tmp_path: Path) -> None:
        """resume 後 is_step_evolution_over_limit() 必須以還原後的 counter 判斷。"""
        cfg = PlaybookConfig()  # max_evolutions 預設 = 3

        # 模擬 resume：counter 已累計到 3，應直接判定 over_limit
        plugin = GotoCounterPlugin(playbook_cfg=cfg)
        plugin.restore(CounterSnapshot(step_evolution_counter={"T02": 3}))
        assert plugin.is_step_evolution_over_limit("T02") is True

        # counter < limit 不應 over_limit
        plugin2 = GotoCounterPlugin(playbook_cfg=cfg)
        plugin2.restore(CounterSnapshot(step_evolution_counter={"T02": 2}))
        assert plugin2.is_step_evolution_over_limit("T02") is False


# ──────────────────────────────────────────────────────
# Gap-049 — fixture 13 對應
# ──────────────────────────────────────────────────────
class TestGap049MaxGotoPerStepCap:
    """Gap-049：max_goto_per_step 配置可覆寫，超出時阻擋（fixture 13 對應）。"""

    def test_default_max_goto_blocks_at_third_attempt(self) -> None:
        """預設 max_goto_per_step = 3：第 3 次 GOTO 後 is_over_limit 為 True。"""
        cfg = PlaybookConfig()  # max_goto_per_step 預設 = 3
        plugin = GotoCounterPlugin(playbook_cfg=cfg)

        plugin.increment_goto("T01")
        assert plugin.is_goto_over_limit("T01") is False  # count=1
        plugin.increment_goto("T01")
        assert plugin.is_goto_over_limit("T01") is False  # count=2
        plugin.increment_goto("T01")
        # count=3 → 達到 limit（>= 3）
        assert plugin.is_goto_over_limit("T01") is True

    def test_custom_max_goto_per_step_overrides_default(self) -> None:
        """fixture 13 場景：config 設定 max_goto_per_step = 5，第 5 次才阻擋。"""
        cfg = PlaybookConfig()
        cfg.max_goto_per_step = 5
        plugin = GotoCounterPlugin(playbook_cfg=cfg)

        for _ in range(4):
            plugin.increment_goto("T01")
        assert plugin.is_goto_over_limit("T01") is False  # count=4 < 5

        plugin.increment_goto("T01")
        assert plugin.is_goto_over_limit("T01") is True  # count=5 → 達到 limit

    def test_consecutive_4_gotos_with_cap_3_blocks_4th(self, tmp_path: Path) -> None:
        """連續 4 次 GOTO 觸發 max_goto_per_step=3 → 第 4 次應 over_limit（阻擋）。

        對應稽核要求：『模擬連續 4 次 GOTO 觸發 max_goto_per_step=3 → 第 4 次應 raise / log warning』
        本測試以 is_goto_over_limit() 表達「應被阻擋」的契約。
        """
        cfg = PlaybookConfig()
        cfg.max_goto_per_step = 3
        plugin = GotoCounterPlugin(playbook_cfg=cfg)

        # 1~3 次 GOTO 累計（第 3 次後即達 limit）
        plugin.increment_goto("T01")
        plugin.increment_goto("T01")
        plugin.increment_goto("T01")
        # 第 4 次嘗試前，is_goto_over_limit 應為 True，Kernel/EvolutionPlugin
        # 看到後應拒絕第 4 次 GOTO
        assert plugin.is_goto_over_limit("T01") is True, (
            "max_goto_per_step=3 下，count=3 應立即阻擋第 4 次 GOTO"
        )

    def test_max_goto_cap_persists_through_token_halt(self, tmp_path: Path) -> None:
        """跨 Session 驗證：counter 達 cap 後 TOKEN_HALT → resume → 仍 over_limit。"""
        cm = CheckpointManager(checkpoint_dir=str(tmp_path))
        cfg = PlaybookConfig()
        cfg.max_goto_per_step = 3
        plugin = GotoCounterPlugin(playbook_cfg=cfg)

        for _ in range(3):
            plugin.increment_goto("T01")
        assert plugin.is_goto_over_limit("T01") is True

        cp = _make_checkpoint(
            "fake/13_max_goto.yaml",
            goto_counter=plugin.snapshot().goto_counter,
        )
        cm.save(cp, "fake/13_max_goto.yaml")

        cp_loaded = cm.load("fake/13_max_goto.yaml")
        assert cp_loaded is not None
        plugin_resumed = GotoCounterPlugin(playbook_cfg=cfg)
        plugin_resumed.restore(CounterSnapshot(goto_counter=cp_loaded.goto_counter))
        assert plugin_resumed.is_goto_over_limit("T01") is True, (
            "TOKEN_HALT 後計數器持久化失效時，resume 會重置 over_limit 判斷"
        )


# ──────────────────────────────────────────────────────
# Smoke：fixture 11/12/13 仍存在（保留 dry_run baseline）
# ──────────────────────────────────────────────────────
def test_fixtures_11_12_13_still_present() -> None:
    """fixture 11/12/13 的 dry_run snapshot baseline 仍在 test_runner_snapshot.py 中
    以 byte-level 比對驗證，本檔僅補充計數器 round-trip 真實驗證。"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    assert (fixtures_dir / "11_goto_counter_token_halt.yaml").exists()
    assert (fixtures_dir / "12_evolution_counter_esc_f12.yaml").exists()
    assert (fixtures_dir / "13_max_goto_per_step_override.yaml").exists()


@pytest.fixture(autouse=True)
def _isolate_logger_warnings(caplog) -> None:
    """確保 caplog 不溢出影響其他測試。"""
    yield
