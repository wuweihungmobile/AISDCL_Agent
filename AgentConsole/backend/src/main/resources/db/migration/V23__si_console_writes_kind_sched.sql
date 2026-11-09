-- V23__si_console_writes_kind_sched.sql — console.si_console_writes.kind 放寬為五值（P4：sched-set、run-request；TCS-SelfImprovingSchedule W-S7、D-CS-1）
-- WHY：V13 的 kind 是欄位內聯的匿名 CHECK（PostgreSQL 自動命名為 si_console_writes_kind_check），只認 decide、obs-add、obs-close；
-- 排程設定（sched-set）與立即啟動請求（run-request）寫不進來。結構層正解＝新遷移放寬 CHECK（與 V22 同型），不改已發佈的 V13。
-- 只動這一條 CHECK：不改欄寬（run-request 11 字元、sched-set 9 字元，VARCHAR(12) 足夠；再加 kind 須先放寬欄寬並在此註記）、
-- 不改 si_console_writes_guard() 觸發器（kind 仍不可改）、不新增表。subject_id 與 digest 於兩個新 kind 為 NULL（欄位本即可為 NULL）。

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c
                   JOIN pg_class t ON t.oid = c.conrelid
                   JOIN pg_namespace n ON n.oid = t.relnamespace
                   WHERE n.nspname = 'console' AND t.relname = 'si_console_writes'
                     AND c.conname = 'si_console_writes_kind_check' AND c.contype = 'c') THEN
        RAISE EXCEPTION 'V23: 找不到 si_console_writes_kind_check，拒絕在未確認舊 CHECK 的情況下加新 CHECK'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
END
$$;
ALTER TABLE console.si_console_writes DROP CONSTRAINT si_console_writes_kind_check;
ALTER TABLE console.si_console_writes ADD CONSTRAINT si_console_writes_kind_check
    CHECK (kind IN ('decide', 'obs-add', 'obs-close', 'sched-set', 'run-request'));
