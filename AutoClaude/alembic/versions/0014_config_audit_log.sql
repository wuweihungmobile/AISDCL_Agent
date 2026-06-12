-- 0014_config_audit_log.sql — ConfigResolver 設定變更稽核紀錄表
-- SD_Improving_06 W5-T5-16
-- 對應 .py：alembic/versions/0014_config_audit_log.py
BEGIN;

CREATE TABLE config_audit_log (
    audit_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    changed_at      timestamptz NOT NULL DEFAULT now(),
    user_id         uuid,
    layer           text        NOT NULL,
    field_path      text        NOT NULL,
    old_value       jsonb,
    new_value       jsonb,
    action          text        NOT NULL DEFAULT 'update',
    reason          text,
    CONSTRAINT ck_config_audit_layer CHECK (
        layer IN ('global', 'workflow', 'step', 'runtime')
    ),
    CONSTRAINT ck_config_audit_action CHECK (
        action IN ('insert', 'update', 'delete', 'reject')
    )
);

CREATE INDEX idx_config_audit_field ON config_audit_log (field_path, changed_at DESC);
CREATE INDEX idx_config_audit_layer
    ON config_audit_log (layer, changed_at DESC);
CREATE INDEX idx_config_audit_user
    ON config_audit_log (user_id, changed_at DESC)
    WHERE user_id IS NOT NULL;

COMMENT ON TABLE config_audit_log IS
    'SD_06 W5-T5-16：ConfigResolver 設定變更稽核紀錄。'
    '對應 4 層 hierarchical config merge：global → workflow → step → runtime。';

COMMIT;
