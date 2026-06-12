"""SD_06 W5-T5-14：ConfigResolver 4 層 merge property-based test。

對應規格：
  - SD_Improving_06.md §6.5 AC6-1（4 層 ConfigResolver）
  - SD06_Execution_Guide.md W5 T5-14：≥ 6 case property-based
  - autoclaude/utils/config_resolver.py（ConfigResolver / promote_flat_to_nested）

驗證不變式：
  1. 4 層 merge：global → workflow → step → runtime；右側覆蓋左側
  2. 巢狀 dict 遞迴 merge；scalar / list 整體覆寫
  3. flat → nested 自動 promote + DeprecationWarning
  4. RBAC 保護欄位由 runtime 覆寫 → ProtectedFieldError
  5. effective() 結果為合法 AppConfig（Pydantic invariants 自動執行）
  6. OpenAPI 3.1 schema 結構合規
"""
from __future__ import annotations

import warnings

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from autoclaude.utils.config import AppConfig
from autoclaude.utils.config_resolver import (
    ConfigAuditRecord,
    ConfigResolver,
    ProtectedFieldError,
    promote_flat_to_nested,
)


# ──────────────────────────────────────────────
# Case 1：4 層 merge 順序（runtime > step > workflow > global）
# ──────────────────────────────────────────────
def test_layer_priority_runtime_wins():
    resolver = ConfigResolver(global_cfg=AppConfig())
    resolver.set_workflow_overrides(
        {"token_guard": {"compact_threshold_pct": 75.0}}
    )
    resolver.set_step_overrides(
        {"token_guard": {"compact_threshold_pct": 78.0}}
    )
    resolver.set_runtime_overrides(
        {"token_guard": {"compact_threshold_pct": 70.0}}
    )
    cfg = resolver.effective()
    assert cfg.token_guard.compact_threshold_pct == 70.0


def test_layer_priority_step_above_workflow():
    resolver = ConfigResolver(global_cfg=AppConfig())
    resolver.set_workflow_overrides(
        {"token_guard": {"halt_threshold_pct": 95.0}}
    )
    resolver.set_step_overrides(
        {"token_guard": {"halt_threshold_pct": 99.0}}
    )
    cfg = resolver.effective()
    assert cfg.token_guard.halt_threshold_pct == 99.0


# ──────────────────────────────────────────────
# Case 2：巢狀 dict 遞迴 merge
# ──────────────────────────────────────────────
def test_nested_dict_recursive_merge():
    resolver = ConfigResolver(global_cfg=AppConfig())
    resolver.set_workflow_overrides({
        "token_guard": {
            "compact_threshold_pct": 75.0,
            "halt_threshold_pct": 95.0,
        }
    })
    resolver.set_step_overrides({
        "token_guard": {"halt_threshold_pct": 97.0}
    })
    cfg = resolver.effective()
    assert cfg.token_guard.compact_threshold_pct == 75.0  # 來自 workflow
    assert cfg.token_guard.halt_threshold_pct == 97.0    # 來自 step


# ──────────────────────────────────────────────
# Case 3：flat → nested 自動 promote + DeprecationWarning
# ──────────────────────────────────────────────
def test_flat_to_nested_promotion_emits_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        promoted = promote_flat_to_nested(
            {"compact_threshold_pct": 75.0, "halt_threshold_pct": 95.0},
            warn=True,
        )
    matches = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(matches) >= 2
    assert promoted == {
        "token_guard": {
            "compact_threshold_pct": 75.0,
            "halt_threshold_pct": 95.0,
        }
    }


def test_flat_promotion_respects_existing_nested():
    """nested 已明確指定時，flat 不覆寫 nested。"""
    promoted = promote_flat_to_nested(
        {
            "compact_threshold_pct": 75.0,
            "token_guard": {"compact_threshold_pct": 80.0},
        },
        warn=False,
    )
    # nested 優先（已明確指定 80.0）
    assert promoted["token_guard"]["compact_threshold_pct"] == 80.0


# ──────────────────────────────────────────────
# Case 4：RBAC 保護欄位由 runtime 覆寫 → ProtectedFieldError
# ──────────────────────────────────────────────
def test_runtime_cannot_override_protected_minimax_api_key():
    resolver = ConfigResolver(global_cfg=AppConfig())
    with pytest.raises(ProtectedFieldError, match="api_key"):
        resolver.set_runtime_overrides({"minimax": {"api_key": "leaked"}})


def test_runtime_cannot_override_storage_db_dsn():
    resolver = ConfigResolver(global_cfg=AppConfig())
    with pytest.raises(ProtectedFieldError, match="db_dsn"):
        resolver.set_runtime_overrides(
            {"storage": {"db_dsn": "postgresql://attacker/db"}}
        )


def test_workflow_layer_can_set_protected_field():
    """workflow / step / global 層仍可設定保護欄位（僅 runtime 受限）。"""
    resolver = ConfigResolver(global_cfg=AppConfig())
    resolver.set_workflow_overrides({"minimax": {"api_key": "configured_via_workflow"}})
    cfg = resolver.effective()
    assert cfg.minimax.api_key == "configured_via_workflow"


# ──────────────────────────────────────────────
# Case 5：effective() Pydantic invariants（halt > compact）
# ──────────────────────────────────────────────
def test_effective_pydantic_invariant_halt_must_exceed_compact():
    resolver = ConfigResolver(global_cfg=AppConfig())
    resolver.set_workflow_overrides({
        "token_guard": {
            "compact_threshold_pct": 90.0,
            "halt_threshold_pct": 85.0,  # 違反 halt > compact
        }
    })
    with pytest.raises(Exception):
        resolver.effective()


# ──────────────────────────────────────────────
# Case 6：audit_changes 紀錄逐層變更
# ──────────────────────────────────────────────
def test_audit_changes_records_per_layer_diffs():
    captured: list[ConfigAuditRecord] = []
    resolver = ConfigResolver(
        global_cfg=AppConfig(),
        audit_observer=captured.append,
    )
    resolver.set_workflow_overrides({
        "token_guard": {"compact_threshold_pct": 75.0}
    })
    resolver.set_step_overrides({
        "token_guard": {"halt_threshold_pct": 97.0}
    })
    resolver.set_runtime_overrides({
        "log_dir": "custom_logs"
    })
    records = resolver.audit_changes()
    assert len(records) >= 3
    # 每個記錄至少有 layer + field_path
    paths = {r.field_path for r in records}
    assert "token_guard.compact_threshold_pct" in paths
    assert "token_guard.halt_threshold_pct" in paths
    assert "log_dir" in paths
    # observer 也收到
    assert len(captured) >= 3


# ──────────────────────────────────────────────
# Case 7：OpenAPI 3.1 schema export（AC6-3）
# ──────────────────────────────────────────────
def test_openapi_schema_3_1_structure():
    schema = ConfigResolver.openapi_schema()
    assert schema["openapi"] == "3.1.0"
    assert "components" in schema
    assert "AppConfig" in schema["components"]["schemas"]
    # 確保 paths 含 /api/config/schema
    assert "/api/config/schema" in schema["paths"]


def test_openapi_schema_appconfig_has_token_guard_section():
    schema = ConfigResolver.openapi_schema()
    appcfg_schema = schema["components"]["schemas"]["AppConfig"]
    # AppConfig nested model 至少需含 token_guard 子節
    assert "properties" in appcfg_schema
    assert "token_guard" in appcfg_schema["properties"]


# ──────────────────────────────────────────────
# Property-based：4 層 merge 結果為合法 AppConfig
# ──────────────────────────────────────────────
@st.composite
def valid_token_guard_overrides(draw):
    compact = draw(st.floats(min_value=10.0, max_value=70.0, allow_nan=False))
    halt = draw(st.floats(min_value=compact + 5.0, max_value=99.0, allow_nan=False))
    return {
        "token_guard": {
            "compact_threshold_pct": compact,
            "halt_threshold_pct": halt,
            "resume_delay_minutes": draw(st.integers(min_value=0, max_value=120)),
            "max_auto_resumes": draw(st.integers(min_value=1, max_value=50)),
        }
    }


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(workflow=valid_token_guard_overrides(), step=valid_token_guard_overrides())
def test_merge_property_effective_is_valid(workflow, step):
    """任意合法的 workflow + step overrides，effective() 必須產生合法 AppConfig。"""
    resolver = ConfigResolver(global_cfg=AppConfig())
    resolver.set_workflow_overrides(workflow)
    resolver.set_step_overrides(step)
    cfg = resolver.effective()
    # step 層的 token_guard 應覆寫 workflow 層
    assert cfg.token_guard.compact_threshold_pct == step["token_guard"]["compact_threshold_pct"]
    assert cfg.token_guard.halt_threshold_pct == step["token_guard"]["halt_threshold_pct"]
    # Pydantic invariants 應保持（halt > compact）
    assert cfg.token_guard.halt_threshold_pct > cfg.token_guard.compact_threshold_pct
