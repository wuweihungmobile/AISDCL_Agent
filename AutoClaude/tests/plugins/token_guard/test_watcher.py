"""watcher.py 純函式單元測試（SD_07 W3-T3-10）。

對應子模組：autoclaude/plugins/token_guard/watcher.py
測試 API：
  - observe_token_line (SD_05 W2-1e)
  - resolve_per_step_cfg (SD_05 W2-4 M-7，per-step override)

目標：≥ 5 case + coverage 100%
"""
from __future__ import annotations

from autoclaude.models.playbook import PlaybookTask
from autoclaude.plugins.token_guard.watcher import (
    observe_token_line,
    resolve_per_step_cfg,
)
from autoclaude.utils.config import TokenGuardConfig


class TestObserveTokenLine:
    def test_none_pct_keeps_state(self):
        cfg = TokenGuardConfig()
        peak, c, h = observe_token_line(
            pct=None, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert (peak, c, h) == (50.0, False, False)

    def test_pct_below_peak_no_update(self):
        cfg = TokenGuardConfig()
        peak, c, h = observe_token_line(
            pct=40.0, peak_pct=70.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert (peak, c, h) == (70.0, False, False)

    def test_pct_above_halt_threshold_sets_halt(self):
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=95.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert peak == 95.0
        assert h is True
        assert c is False  # halt 優先，compact 不單獨觸發

    def test_pct_between_compact_and_halt_sets_compact(self):
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=85.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert peak == 85.0
        assert c is True
        assert h is False

    def test_pct_below_compact_only_updates_peak(self):
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=60.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert peak == 60.0
        assert c is False
        assert h is False

    def test_existing_flags_preserved_when_pct_below_peak(self):
        cfg = TokenGuardConfig()
        peak, c, h = observe_token_line(
            pct=10.0, peak_pct=85.0,
            triggered_compact=True, triggered_halt=False, cfg=cfg,
        )
        assert (peak, c, h) == (85.0, True, False)


class TestResolvePerStepCfg:
    def test_no_task_returns_global(self):
        g = TokenGuardConfig(compact_threshold_pct=80.0)
        assert resolve_per_step_cfg(global_cfg=g, task=None) is g

    def test_no_override_returns_global(self):
        g = TokenGuardConfig(compact_threshold_pct=80.0)
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        assert resolve_per_step_cfg(global_cfg=g, task=task) is g

    def test_override_dict_merges(self):
        g = TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        )
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={"compact_threshold_pct": 70.0},
        )
        merged = resolve_per_step_cfg(global_cfg=g, task=task)
        assert merged.compact_threshold_pct == 70.0
        assert merged.halt_threshold_pct == 90.0  # 未覆寫保持原值

    def test_override_non_dict_returns_global(self):
        g = TokenGuardConfig()
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard=None,  # 非 dict
        )
        assert resolve_per_step_cfg(global_cfg=g, task=task) is g

    def test_override_empty_dict_returns_global(self):
        # empty dict 視同無 override（`if not override` 判斷）
        g = TokenGuardConfig()
        task = PlaybookTask(step_id="T01", name="n", prompt="p", token_guard={})
        assert resolve_per_step_cfg(global_cfg=g, task=task) is g
