"""SD_06 W5-T5-19 / T5-20：ConfigResolver + PII filter integration test。

對應規格：
  - SD_Improving_06.md §6.5 AC6-5（每次 ConfigResolver 變更都寫 audit_log）
  - SD_Improving_06.md §9.2 #11（PM hybrid PII filter 應用至三表）
  - SD06_Execution_Guide.md W5 T5-19 + T5-20

驗證：
  1. ConfigResolver.audit_changes 在每層覆寫時產生 ConfigAuditRecord
  2. audit_observer 被觸發 N 次
  3. PIIFilter 對 ConfigAuditRecord.new_value 套用：
     - SECRET → PIIFilterViolation raise
     - PII → masked
     - NORMAL → passthrough
  4. DriftReport.apply_pii_filter 同樣行為
"""
from __future__ import annotations

import pytest

from autoclaude.infra.repositories.dual_state_repository import DriftReport
from autoclaude.infra.services.pii_filter import (
    FieldRegistry,
    PIIFilter,
    PIIFilterViolation,
)
from autoclaude.models.pii_classification import PIIClassification
from autoclaude.utils.config import AppConfig
from autoclaude.utils.config_resolver import (
    ConfigAuditRecord,
    ConfigResolver,
)


# ──────────────────────────────────────────────
# Case 1：ConfigResolver.audit_changes 觸發 audit_observer
# ──────────────────────────────────────────────
def test_audit_observer_invoked_per_layer_change():
    captured: list[ConfigAuditRecord] = []
    resolver = ConfigResolver(
        global_cfg=AppConfig(),
        audit_observer=captured.append,
    )
    resolver.set_workflow_overrides({"log_dir": "workflow_logs"})
    resolver.set_step_overrides({"backup_dir": "step_backups"})
    resolver.set_runtime_overrides({"checkpoint_dir": "runtime_ckpt"})

    records = resolver.audit_changes()
    assert len(records) >= 3
    assert len(captured) >= 3
    layers = {r.layer for r in records}
    assert {"workflow", "step", "runtime"}.issubset(layers)


# ──────────────────────────────────────────────
# Case 2：ConfigAuditRecord.apply_pii_filter — NORMAL 欄位 passthrough
# ──────────────────────────────────────────────
def test_audit_record_pii_filter_passthrough_normal():
    registry = FieldRegistry(rules={})
    pii_filter = PIIFilter(registry=registry, enabled=True)
    rec = ConfigAuditRecord(
        layer="runtime",
        field_path="log_dir",
        old_value="old_logs",
        new_value="new_logs",
    )
    filtered = rec.apply_pii_filter(pii_filter)
    assert filtered.old_value == "old_logs"
    assert filtered.new_value == "new_logs"


# ──────────────────────────────────────────────
# Case 3：ConfigAuditRecord.apply_pii_filter — SECRET 欄位 drop write
# ──────────────────────────────────────────────
def test_audit_record_pii_filter_secret_blocks_write():
    registry = FieldRegistry(rules={
        "config_audit_log.new_value.minimax.api_key": PIIClassification.SECRET,
        "config_audit_log.old_value.minimax.api_key": PIIClassification.SECRET,
    })
    pii_filter = PIIFilter(registry=registry, enabled=True)
    rec = ConfigAuditRecord(
        layer="workflow",
        field_path="minimax.api_key",
        old_value="sk-old-secret-key",
        new_value="sk-new-secret-key",
    )
    with pytest.raises(PIIFilterViolation, match="SECRET"):
        rec.apply_pii_filter(pii_filter)


# ──────────────────────────────────────────────
# Case 4：ConfigAuditRecord.apply_pii_filter — PII 欄位 masked
# ──────────────────────────────────────────────
def test_audit_record_pii_filter_pii_masked():
    registry = FieldRegistry(rules={
        "config_audit_log.new_value.notification.webhook_url": PIIClassification.PII,
        "config_audit_log.old_value.notification.webhook_url": PIIClassification.PII,
    })
    pii_filter = PIIFilter(registry=registry, enabled=True)
    rec = ConfigAuditRecord(
        layer="runtime",
        field_path="notification.webhook_url",
        old_value="user@example.com",
        new_value="another@example.com",
    )
    filtered = rec.apply_pii_filter(pii_filter)
    assert "@example.com" not in filtered.new_value or "***" in filtered.new_value
    assert filtered.old_value != "user@example.com"


# ──────────────────────────────────────────────
# Case 5：DriftReport.apply_pii_filter — 套用至 field_drift
# ──────────────────────────────────────────────
def test_drift_report_pii_filter_masks_pii():
    registry = FieldRegistry(rules={
        "drift_log.field_drift.user_email": PIIClassification.PII,
    })
    pii_filter = PIIFilter(registry=registry, enabled=True)
    report = DriftReport(
        playbook_id="pb1",
        source_left="primary",
        source_right="shadow",
        field_drift={
            "user_email": {"left": "alice@example.com", "right": "bob@example.com"},
        },
    )
    filtered = report.apply_pii_filter(pii_filter)
    # PII masked → 不含原始 email
    left = filtered.field_drift["user_email"]["left"]
    right = filtered.field_drift["user_email"]["right"]
    assert "alice@example.com" not in left
    assert "bob@example.com" not in right


# ──────────────────────────────────────────────
# Case 6：DriftReport.apply_pii_filter — SECRET drop
# ──────────────────────────────────────────────
def test_drift_report_pii_filter_secret_aborts():
    registry = FieldRegistry(rules={
        "drift_log.field_drift.api_key": PIIClassification.SECRET,
    })
    pii_filter = PIIFilter(registry=registry, enabled=True)
    report = DriftReport(
        playbook_id="pb1",
        source_left="primary",
        source_right="shadow",
        field_drift={
            "api_key": {"left": "sk-leak", "right": "sk-other"},
        },
    )
    with pytest.raises(PIIFilterViolation, match="SECRET"):
        report.apply_pii_filter(pii_filter)


# ──────────────────────────────────────────────
# Case 7：完整流程 — resolver 變更 → audit → PII filter → ready for DB
# ──────────────────────────────────────────────
def test_full_audit_pipeline_pii_filter_applied():
    registry = FieldRegistry(rules={
        # log_dir 視為 NORMAL（預設）
    })
    pii_filter = PIIFilter(registry=registry, enabled=True)

    persisted: list[dict] = []

    def observer(rec: ConfigAuditRecord) -> None:
        filtered = rec.apply_pii_filter(pii_filter)
        persisted.append({
            "layer": filtered.layer,
            "field_path": filtered.field_path,
            "new_value": filtered.new_value,
        })

    resolver = ConfigResolver(global_cfg=AppConfig(), audit_observer=observer)
    resolver.set_workflow_overrides({"log_dir": "workflow_logs"})
    resolver.audit_changes()

    assert any(r["field_path"] == "log_dir" for r in persisted)
    log_record = next(r for r in persisted if r["field_path"] == "log_dir")
    assert log_record["layer"] == "workflow"
    assert log_record["new_value"] == "workflow_logs"
