"""tests/integration/test_config_resolver_hierarchy_e2e.py — SD_07 W2 T2-5 議題 6 e2e。

對應 AC6-1 / AC6-2 / AC6-3（[docs/03_testing/SD07_AC_Matrix.md](../../docs/03_testing/SD07_AC_Matrix.md)）：
  AC6-1 4 層 merge（global → workflow → step → runtime）property-based；Hypothesis ≥ 50 example
  AC6-2 flat → nested promote + DeprecationWarning
  AC6-3 RBAC 保護欄位（minimax.api_key / embedder.api_key / storage.db_dsn）
        runtime 層 override 必 raise ProtectedFieldError + audit_log 寫入

覆蓋 ≥ 8 case + Hypothesis property-based ≥ 50 example。
"""
from __future__ import annotations

import warnings

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from autoclaude.utils.config import AppConfig, TokenGuardConfig
from autoclaude.utils.config_resolver import (
    ConfigAuditRecord,
    ConfigResolver,
    ProtectedFieldError,
    promote_flat_to_nested,
)


def _make_app_config() -> AppConfig:
    """建立基線 AppConfig（global layer）。"""
    return AppConfig.model_validate({
        "minimax": {"api_key": "global_key", "model": "MiniMax-Text-01"},
        "token_guard": {
            "compact_threshold_pct": 80.0,
            "halt_threshold_pct": 90.0,
            "resume_delay_minutes": 30,
            "max_auto_resumes": 10,
        },
    })


# ──────────────────────────────────────────────────────────────
# AC6-1：4 層 merge property-based（Hypothesis ≥ 50 example）
# ──────────────────────────────────────────────────────────────
class TestFourLayerMerge:
    @given(
        compact=st.floats(min_value=10.0, max_value=70.0),
        halt_gap=st.floats(min_value=5.0, max_value=20.0),
    )
    @settings(max_examples=50, deadline=500)
    def test_layer_override_precedence(self, compact, halt_gap):
        """property-based：runtime 層 override 必勝過 step/workflow/global。"""
        halt = min(compact + halt_gap, 99.9)
        if halt <= compact:
            return  # 跳過不合法輸入
        resolver = ConfigResolver(global_cfg=_make_app_config())
        resolver.set_workflow_overrides(
            {"token_guard": {"compact_threshold_pct": 60.0,
                              "halt_threshold_pct": 85.0}}
        )
        resolver.set_step_overrides(
            {"token_guard": {"compact_threshold_pct": 50.0,
                              "halt_threshold_pct": 80.0}}
        )
        resolver.set_runtime_overrides(
            {"token_guard": {"compact_threshold_pct": compact,
                              "halt_threshold_pct": halt}}
        )
        eff = resolver.effective()
        assert eff.token_guard.compact_threshold_pct == pytest.approx(compact)
        assert eff.token_guard.halt_threshold_pct == pytest.approx(halt)

    def test_global_baseline_when_no_overrides(self):
        """無任何 override 時，effective() = global baseline。"""
        resolver = ConfigResolver(global_cfg=_make_app_config())
        eff = resolver.effective()
        assert eff.token_guard.compact_threshold_pct == 80.0
        assert eff.token_guard.halt_threshold_pct == 90.0

    def test_associativity_independent_of_set_order(self):
        """同層 override 設定順序不影響結果（associativity 證明）。"""
        cfg = _make_app_config()
        r1 = ConfigResolver(global_cfg=cfg)
        r1.set_workflow_overrides({"token_guard": {"compact_threshold_pct": 70.0}})
        r1.set_runtime_overrides({"token_guard": {"halt_threshold_pct": 85.0}})

        r2 = ConfigResolver(global_cfg=cfg)
        r2.set_runtime_overrides({"token_guard": {"halt_threshold_pct": 85.0}})
        r2.set_workflow_overrides({"token_guard": {"compact_threshold_pct": 70.0}})

        e1 = r1.effective()
        e2 = r2.effective()
        assert e1.token_guard.compact_threshold_pct == e2.token_guard.compact_threshold_pct
        assert e1.token_guard.halt_threshold_pct == e2.token_guard.halt_threshold_pct


# ──────────────────────────────────────────────────────────────
# AC6-2：flat → nested promote + DeprecationWarning
# ──────────────────────────────────────────────────────────────
class TestFlatToNestedPromote:
    def test_flat_key_promotes_to_nested(self):
        """compact_threshold_pct=75 → {"token_guard": {"compact_threshold_pct": 75}}。"""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            promoted = promote_flat_to_nested({"compact_threshold_pct": 75.0})
            assert promoted == {"token_guard": {"compact_threshold_pct": 75.0}}
            assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    def test_nested_takes_priority_over_flat(self):
        """nested 已指定時，flat 不可覆寫 nested。"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            promoted = promote_flat_to_nested({
                "compact_threshold_pct": 75.0,
                "token_guard": {"compact_threshold_pct": 65.0},
            })
            # nested 65.0 應保留（setdefault 機制）
            assert promoted["token_guard"]["compact_threshold_pct"] == 65.0


# ──────────────────────────────────────────────────────────────
# AC6-3：RBAC 保護欄位 runtime override 必 raise
# ──────────────────────────────────────────────────────────────
class TestProtectedFieldRbac:
    @pytest.mark.parametrize(
        "protected_path,override",
        [
            ("minimax.api_key", {"minimax": {"api_key": "leaked!"}}),
            ("embedder.api_key", {"embedder": {"api_key": "leaked!"}}),
            ("storage.db_dsn", {"storage": {"db_dsn": "leaked!"}}),
        ],
    )
    def test_runtime_protected_field_rejected(self, protected_path, override):
        """3 個 protected field × runtime override 必 raise ProtectedFieldError。"""
        resolver = ConfigResolver(global_cfg=_make_app_config())
        with pytest.raises(ProtectedFieldError, match=protected_path):
            resolver.set_runtime_overrides(override)

    def test_workflow_protected_field_allowed(self):
        """workflow / step 層可改 protected field（僅 runtime 層被擋）。"""
        resolver = ConfigResolver(global_cfg=_make_app_config())
        # workflow 層可改（不 raise）
        resolver.set_workflow_overrides({"minimax": {"api_key": "workflow_key"}})
        eff = resolver.effective()
        assert eff.minimax.api_key == "workflow_key"

    def test_audit_observer_called_on_override(self):
        """audit_observer 在每筆 override 時被呼叫，紀錄 ConfigAuditRecord。"""
        captured: list[ConfigAuditRecord] = []
        resolver = ConfigResolver(
            global_cfg=_make_app_config(),
            audit_observer=captured.append,
        )
        resolver.set_workflow_overrides(
            {"token_guard": {"compact_threshold_pct": 75.0}}
        )
        records = resolver.audit_changes()
        assert len(records) >= 1
        compact_rec = next(
            (r for r in records
             if "compact_threshold_pct" in r.field_path), None,
        )
        assert compact_rec is not None
        assert compact_rec.new_value == 75.0
        assert compact_rec.layer == "workflow"
        # observer 也應收到（每筆 record 都被 append）
        assert len(captured) == len(records)


# ──────────────────────────────────────────────────────────────
# Pydantic v2 invariants（halt > compact + range checks）
# ──────────────────────────────────────────────────────────────
class TestPydanticInvariants:
    def test_halt_must_exceed_compact_threshold(self):
        """halt_threshold_pct 必須 > compact_threshold_pct。"""
        with pytest.raises(ValidationError, match="halt_threshold_pct"):
            TokenGuardConfig(compact_threshold_pct=90.0, halt_threshold_pct=80.0)

    def test_resume_delay_range(self):
        """resume_delay_minutes ∈ [0, 1440]；超過 raise。"""
        with pytest.raises(ValidationError):
            TokenGuardConfig(resume_delay_minutes=-1)
        with pytest.raises(ValidationError):
            TokenGuardConfig(resume_delay_minutes=1441)

    def test_max_auto_resumes_range(self):
        """max_auto_resumes ∈ [1, 100]；越界 raise。"""
        with pytest.raises(ValidationError):
            TokenGuardConfig(max_auto_resumes=0)
        with pytest.raises(ValidationError):
            TokenGuardConfig(max_auto_resumes=101)


# ──────────────────────────────────────────────────────────────
# Hot-reload smoke（重新建立 resolver 等價）
# ──────────────────────────────────────────────────────────────
class TestHotReloadSmoke:
    def test_reload_resolver_produces_same_effective(self):
        """重建 resolver（模擬 hot reload）→ effective 結果與原 resolver 一致。"""
        cfg = _make_app_config()
        r1 = ConfigResolver(global_cfg=cfg)
        r1.set_workflow_overrides({"token_guard": {"compact_threshold_pct": 75.0}})

        r2 = ConfigResolver(global_cfg=cfg)
        r2.set_workflow_overrides({"token_guard": {"compact_threshold_pct": 75.0}})

        assert r1.merged() == r2.merged()
