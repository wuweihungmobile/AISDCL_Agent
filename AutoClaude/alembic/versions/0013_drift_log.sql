-- 0013_drift_log.sql — DualStateRepository drift 紀錄表
-- SD_Improving_06 W5-T5-5
-- 對應 .py：alembic/versions/0013_drift_log.py
BEGIN;

-- drift_log（partition by month, 365 天 TTL）
CREATE TABLE drift_log (
    drift_id        uuid        NOT NULL DEFAULT gen_random_uuid(),
    detected_at     timestamptz NOT NULL DEFAULT now(),
    run_id          uuid,
    playbook_id     text        NOT NULL,
    source_left     text        NOT NULL,
    source_right    text        NOT NULL,
    field_drift     jsonb       NOT NULL,
    severity        text        NOT NULL DEFAULT 'warn',
    resolved_at     timestamptz,
    resolver        text,
    notes           text,
    PRIMARY KEY (drift_id, detected_at),
    CONSTRAINT ck_drift_severity CHECK (severity IN ('info', 'warn', 'critical')),
    CONSTRAINT ck_drift_source CHECK (
        source_left IN ('primary', 'shadow', 'file', 'pg')
        AND source_right IN ('primary', 'shadow', 'file', 'pg')
    )
) PARTITION BY RANGE (detected_at);

CREATE INDEX idx_drift_log_playbook ON drift_log (playbook_id, detected_at DESC);
CREATE INDEX idx_drift_log_unresolved
    ON drift_log (severity, detected_at DESC)
    WHERE resolved_at IS NULL;
CREATE INDEX idx_drift_log_run_id
    ON drift_log (run_id, detected_at DESC)
    WHERE run_id IS NOT NULL;

COMMENT ON TABLE drift_log IS
    'SD_06 W5-T5-5：DualStateRepository detect_drift() 紀錄表。'
    '365 天 partition by month；過期 partition 由 cron drop。';

DO $$
DECLARE
    start_month date := date_trunc('month', now())::date;
    cur_month date;
    next_month date;
    part_name text;
BEGIN
    FOR i IN 0..12 LOOP
        cur_month := (start_month + (i || ' month')::interval)::date;
        next_month := (start_month + ((i + 1) || ' month')::interval)::date;
        part_name := 'drift_log_p_' || to_char(cur_month, 'YYYYMM');
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF drift_log '
            'FOR VALUES FROM (%L) TO (%L)',
            part_name, cur_month, next_month
        );
    END LOOP;
END$$;

COMMIT;
