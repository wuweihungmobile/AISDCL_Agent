"""F-B1 AlertLadder 單元測試（Improving_012 Phase 2 / ADR-AGT-004）。

測試意圖（Rule 9）：
  - 三階梯轉換（WARNING→HINT→ESCALATE）保證收斂失敗獲得 2 次自救機會後才升級，
    防止單級跳 ESCALATION 浪費既有重試預算（F-B1 業務目的）。
  - bypass 保證「不可自救」（environment_error）與「已證實無效」（F-B2 streak）
    不被緩階拖延，人工介入不延誤。
  - snapshot/restore 保證跨 TOKEN_HALT / ESC+F12 後階梯不歸零（否則緩階次數
    可被中斷重置而無限延長，破壞有界性）。
"""
from __future__ import annotations

import pytest

from autoclaude.execution.alert_ladder import (
    AlertLadder,
    LadderDecision,
    build_from_config,
)
from autoclaude.execution.convergence_monitor import ConvergenceReport


def _report(trend: str = "stuck", reasoning: str = "特徵碼連續相同且無數量改善"):
    return ConvergenceReport(0.0, trend, [], "escalate", reasoning)


class TestLadderTransitions:
    def test_first_signal_is_warning(self):
        ladder = AlertLadder()
        d = ladder.intercept("T01", _report())
        assert d.action == "warning"
        assert d.hint_text == ""

    def test_second_signal_is_hint_with_local_text(self):
        ladder = AlertLadder()
        ladder.intercept("T01", _report())
        d = ladder.intercept("T01", _report())
        assert d.action == "hint"
        # HINT 必須是本地生成的非空提示（不呼叫 Brain）
        assert "AlertLadder" in d.hint_text
        assert "stuck" in d.hint_text

    def test_third_signal_escalates(self):
        ladder = AlertLadder()
        ladder.intercept("T01", _report())
        ladder.intercept("T01", _report())
        d = ladder.intercept("T01", _report())
        assert d.action == "escalate"

    def test_steps_are_independent(self):
        """每步驟各自有完整三階梯（避免 A 步驟耗盡階梯連坐 B 步驟）。"""
        ladder = AlertLadder()
        ladder.intercept("T01", _report())
        ladder.intercept("T01", _report())
        d = ladder.intercept("T02", _report())
        assert d.action == "warning"


class TestBypass:
    def test_environment_error_bypasses_ladder(self):
        """環境錯誤 AutoClaude 無法修復，緩階只會浪費重試預算。"""
        ladder = AlertLadder()
        d = ladder.intercept("T01", _report(trend="environment_error"))
        assert d.action == "escalate"
        # bypass 不消耗階梯計數
        assert ladder.snapshot() == {}

    def test_no_improve_streak_at_threshold_escalates(self):
        """F-B2：同 signature 無改善 N=2 次 → 穿透剩餘階梯提前升級。"""
        ladder = AlertLadder(threshold_no_improve=2)
        d = ladder.intercept("T01", _report(), no_improve_streak=2)
        assert d.action == "escalate"
        assert "F-B2" in d.reasoning

    def test_streak_below_threshold_enters_ladder(self):
        ladder = AlertLadder(threshold_no_improve=2)
        d = ladder.intercept("T01", _report(), no_improve_streak=1)
        assert d.action == "warning"

    def test_streak_read_from_internal_state_when_not_passed(self):
        ladder = AlertLadder(threshold_no_improve=2)
        ladder.set_no_improve_streak("T01", 2)
        d = ladder.intercept("T01", _report())
        assert d.action == "escalate"


class TestPersistence:
    def test_snapshot_restore_roundtrip_preserves_rung(self):
        """跨中斷恢復後階梯位置不歸零（有界性：緩階最多 2 次/步）。"""
        ladder = AlertLadder()
        ladder.intercept("T01", _report())          # warning 已耗
        snap = ladder.snapshot()

        restored = AlertLadder()
        restored.restore(snap)
        d = restored.intercept("T01", _report())
        assert d.action == "hint"                    # 接續第 2 階，而非重來

    def test_snapshot_is_deep_copy(self):
        ladder = AlertLadder()
        ladder.intercept("T01", _report())
        snap = ladder.snapshot()
        snap["T01"]["warning"] = 99
        assert ladder.snapshot()["T01"]["warning"] == 1

    def test_restore_none_and_empty_are_blank(self):
        ladder = AlertLadder()
        ladder.restore(None)
        assert ladder.snapshot() == {}
        ladder.restore({})
        assert ladder.snapshot() == {}

    def test_restore_skips_malformed_entries(self):
        ladder = AlertLadder()
        ladder.restore({"T01": {"warning": 1}, "BAD": "not-a-dict"})
        assert "BAD" not in ladder.snapshot()
        assert ladder.snapshot()["T01"]["warning"] == 1

    def test_streak_setter_clamps_negative_to_zero(self):
        ladder = AlertLadder()
        ladder.set_no_improve_streak("T01", -3)
        assert ladder.get_no_improve_streak("T01") == 0


class TestCheckpointFieldRoundtrip:
    def test_playbook_checkpoint_alert_ladder_file_roundtrip(self, tmp_path):
        """File backend：alert_ladder 欄位存讀往返（凍結驗收「計數持久化於 checkpoint」）。"""
        from autoclaude.utils.checkpoint_manager import (
            CheckpointManager,
            PlaybookCheckpoint,
        )
        mgr = CheckpointManager(str(tmp_path))
        cp = PlaybookCheckpoint(
            playbook_path="pb.yaml", step_idx=1, step_id="T02", total_steps=3,
            alert_ladder={"T02": {"warning": 1, "hint": 1, "no_improve_streak": 1}},
        )
        mgr.save(cp, "pb.yaml")
        loaded = mgr.load("pb.yaml")
        assert loaded is not None
        assert loaded.alert_ladder == {
            "T02": {"warning": 1, "hint": 1, "no_improve_streak": 1}
        }

    def test_old_checkpoint_without_field_defaults_empty(self):
        """舊 checkpoint 反序列化 → default_factory 補空 dict（additive 相容）。"""
        from autoclaude.utils.checkpoint_manager import PlaybookCheckpoint
        cp = PlaybookCheckpoint(
            playbook_path="pb.yaml", step_idx=0, step_id="T01", total_steps=1,
        )
        assert cp.alert_ladder == {}


class TestConfig:
    def test_alert_ladder_config_defaults_off(self):
        """feature flag 預設 off（凍結計畫 §4 風險緩解；零回歸保證的根）。"""
        from autoclaude.utils.config import AlertLadderConfig, AppConfig
        cfg = AlertLadderConfig()
        assert cfg.enabled is False
        assert cfg.no_improve_escalate_threshold == 2
        assert AppConfig().alert_ladder.enabled is False

    def test_threshold_bounds(self):
        import pydantic

        from autoclaude.utils.config import AlertLadderConfig
        with pytest.raises(pydantic.ValidationError):
            AlertLadderConfig(no_improve_escalate_threshold=0)
        with pytest.raises(pydantic.ValidationError):
            AlertLadderConfig(no_improve_escalate_threshold=6)


class TestBuildFromConfig:
    def test_enabled_requires_literal_true(self):
        """Mock cfg 的 getattr 回傳 truthy Mock 不可誤判 enabled。"""
        from unittest.mock import MagicMock
        cfg = MagicMock()  # getattr(cfg.alert_ladder, "enabled") → truthy Mock
        _, enabled = build_from_config(cfg, None)
        assert enabled is False

    def test_non_numeric_threshold_falls_back_to_default(self):
        """alert_ladder.py:42-43 例外回退分支：非數值 threshold → 預設 2。"""
        from types import SimpleNamespace
        cfg = SimpleNamespace(
            alert_ladder=SimpleNamespace(
                enabled=True, no_improve_escalate_threshold="abc",
            )
        )
        ladder, enabled = build_from_config(cfg, None)
        assert enabled is True
        # 回退預設 2：streak=2 即觸發 bypass 提前升級
        d = ladder.intercept("T01", _report(), no_improve_streak=2)
        assert d.action == "escalate"
        assert "門檻 2" in d.reasoning

    def test_restore_state_applied(self):
        from types import SimpleNamespace
        cfg = SimpleNamespace(alert_ladder=SimpleNamespace(enabled=False))
        ladder, _ = build_from_config(cfg, {"T01": {"warning": 1}})
        # warning 已耗 → 下一次為 hint
        assert ladder.intercept("T01", _report()).action == "hint"


class TestLadderDecisionDataclass:
    def test_defaults(self):
        d = LadderDecision(action="warning")
        assert d.hint_text == ""
        assert d.reasoning == ""
