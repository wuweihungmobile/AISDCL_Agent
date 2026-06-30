"""watcher.py 補強測試 — SD_09 W1 A-1（mutation pilot kill rate ≥ 70%）。

對應 SD_Improving_09 W1 範疇：watcher.py 3 個 survived mutation
（id: 132, 137, 140）。

聚焦：
  - observe_token_line：peak 更新 boundary（`pct > peak_pct` vs `>=`）
  - resolve_per_step_cfg：merged_data 疊加順序、isinstance 檢查
"""
from __future__ import annotations

from autoclaude.models.playbook import PlaybookTask
from autoclaude.plugins.token_guard.watcher import (
    observe_token_line,
    resolve_per_step_cfg,
)
from autoclaude.utils.config import TokenGuardConfig


class TestObserveTokenLineMutations:
    def test_pct_equals_peak_no_update(self):
        """殺 `pct <= peak_pct` → `< peak_pct` boundary mutation。

        pct 等於 peak → 不更新（避免重複觸發）。
        """
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=70.0, peak_pct=70.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert peak == 70.0
        assert c is False
        assert h is False

    def test_pct_equals_peak_at_halt_threshold_no_reupdate(self):
        """殺 `pct <= peak_pct` → `< peak_pct` boundary mutation（#71）。

        SD_09 W1 improving_100：既有 test_pct_equals_peak_no_update 用 pct=70
        （低於所有門檻）→ 變異走更新分支但 70 不觸發任何 flag、結果相同 → 殺不掉
        （`.mutmut-cache` #71 survived 即此因）。本測試令 pct==peak==halt_threshold：
        原式 `pct<=peak`(90<=90) True → 立即 return 不更新、triggered_halt 維持 False；
        變異 `pct<peak`(90<90) False → 進入更新分支、`90>=90` 誤觸 new_halt=True。
        期望 triggered_halt 維持 False 殺之。

        Rule 9（為何）：pct 等於既有 peak 時必須短路不重算門檻，否則「持平不前進」
        的觀測會重複觸發 halt，違反 peak 單調語意。
        """
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=90.0, peak_pct=90.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert peak == 90.0
        assert h is False  # 持平不更新 → 不重觸 halt
        assert c is False

    def test_pct_one_above_peak_updates(self):
        """殺 `pct > peak_pct` 邊界 mutation。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, _, _ = observe_token_line(
            pct=70.001, peak_pct=70.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert peak == 70.001

    def test_exact_halt_threshold_sets_halt(self):
        """殺 `pct >= halt_threshold_pct` → `>` mutation。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=90.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert h is True
        assert c is False  # halt 優先（elif）
        assert peak == 90.0

    def test_exact_compact_threshold_sets_compact(self):
        """殺 `pct >= compact_threshold_pct` → `>` mutation。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        peak, c, h = observe_token_line(
            pct=80.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert c is True
        assert h is False
        assert peak == 80.0

    def test_below_compact_no_change_compact_flag(self):
        """殺 elif 分支 mutation：低於 compact 不應翻 flag。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        _, c, h = observe_token_line(
            pct=79.99, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert c is False
        assert h is False

    def test_halt_priority_elif_not_if(self):
        """殺 `elif` → `if` mutation（halt + compact 同時翻會違反 elif 排他性）。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        # pct=95 同時超過 halt+compact；elif 確保 compact 不額外翻
        _, c, h = observe_token_line(
            pct=95.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        assert h is True
        assert c is False  # elif 排他

    def test_returned_tuple_order(self):
        """殺 return tuple 順序 mutation（peak/compact/halt vs halt/compact/peak）。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        result = observe_token_line(
            pct=85.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False, cfg=cfg,
        )
        peak, c, h = result
        assert peak == 85.0     # 第 1 個
        assert c is True        # 第 2 個 compact
        assert h is False       # 第 3 個 halt

    def test_existing_halt_preserved_when_below_thresholds(self):
        """殺 `new_halt = triggered_halt` initialization mutation。"""
        cfg = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        # pct 提高但仍低於 compact；已 triggered_halt=True 須被保留
        _, c, h = observe_token_line(
            pct=70.0, peak_pct=60.0,
            triggered_compact=False, triggered_halt=True, cfg=cfg,
        )
        assert h is True


class TestResolvePerStepCfgMutations:
    def test_none_task_returns_same_global_instance(self):
        """殺 `return global_cfg` mutation。"""
        g = TokenGuardConfig(compact_threshold_pct=75.0)
        result = resolve_per_step_cfg(global_cfg=g, task=None)
        assert result is g  # 同一 instance

    def test_override_dict_takes_precedence(self):
        """殺 `merged_data.update(override)` → `override.update(merged_data)` mutation。"""
        g = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={"compact_threshold_pct": 70.0, "halt_threshold_pct": 85.0},
        )
        merged = resolve_per_step_cfg(global_cfg=g, task=task)
        # override 必須勝出
        assert merged.compact_threshold_pct == 70.0
        assert merged.halt_threshold_pct == 85.0

    def test_partial_override_preserves_global(self):
        """殺 `model_dump()` → `dict()` 之類 mutation；只覆寫部分欄位。"""
        g = TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)
        task = PlaybookTask(
            step_id="T01", name="n", prompt="p",
            token_guard={"compact_threshold_pct": 60.0},
        )
        merged = resolve_per_step_cfg(global_cfg=g, task=task)
        assert merged.compact_threshold_pct == 60.0
        assert merged.halt_threshold_pct == 90.0  # 未動

    def test_non_dict_override_falls_back_to_global(self):
        """殺 `isinstance(override, dict)` → 反向 mutation。"""
        g = TokenGuardConfig(compact_threshold_pct=80.0)

        class _Fake:
            token_guard = "not_a_dict_at_all"

        assert resolve_per_step_cfg(global_cfg=g, task=_Fake()) is g

    def test_empty_dict_falls_back_to_global(self):
        """殺 `not override` 條件 mutation。"""
        g = TokenGuardConfig(compact_threshold_pct=80.0)
        task = PlaybookTask(step_id="T01", name="n", prompt="p", token_guard={})
        assert resolve_per_step_cfg(global_cfg=g, task=task) is g
