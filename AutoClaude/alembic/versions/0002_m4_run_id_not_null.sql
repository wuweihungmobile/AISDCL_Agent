-- M4 migration：checkpoints.run_id NOT NULL（Phase 6 P1 先決條件）
-- 對應 SD_Improving_03.md v1.1 §1.2 M4 finding
-- 可直接以 psql 執行，或由 0002_m4_run_id_not_null.py 調用

-- ──────────────────────────────────────────────
-- Step 1：為現有孤立 checkpoint（run_id IS NULL）補建 playbook_runs 佔位記錄
--   （全新部署無此問題；灰度升級保護）
-- ──────────────────────────────────────────────
DO $$
BEGIN
    -- 為每個 run_id IS NULL 的 playbook_id 建立 running 狀態的 playbook_runs
    INSERT INTO playbook_runs (playbook_id, project, status)
    SELECT DISTINCT c.playbook_id, c.playbook_id, 'running'
    FROM   checkpoints c
    WHERE  c.run_id IS NULL
    ON CONFLICT DO NOTHING;

    -- 將孤立 checkpoint 指向剛建立的 playbook_runs 記錄
    UPDATE checkpoints c
    SET    run_id = pr.run_id
    FROM   playbook_runs pr
    WHERE  c.run_id IS NULL
      AND  pr.playbook_id = c.playbook_id;
END $$;

-- ──────────────────────────────────────────────
-- Step 2：強制 NOT NULL
-- ──────────────────────────────────────────────
ALTER TABLE checkpoints ALTER COLUMN run_id SET NOT NULL;
