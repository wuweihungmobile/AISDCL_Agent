-- V25__si_console_writes_kind_src_registry.sql — console.si_console_writes.kind 放寬為六值（研究來源單一化：src-registry；TCS-ResearchRegistry W-R2、契約 §5A.1）
-- WHY：V23 的 CHECK 只認五值；登記同步（src-registry）寫不進來。結構層正解＝新遷移放寬 CHECK（與 V22／V23 同型），不改已發佈的 V13／V23。
-- 只動這一條 CHECK：不改欄寬（src-registry 恰 12 字元＝VARCHAR(12) 上限；再加 kind 須先放寬欄寬並在此註記）、
-- 不改 si_console_writes_guard() 觸發器（kind 仍不可改）、不新增表。subject_id 於 src-registry 為 NULL（欄位本即可為 NULL）。

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c
                   JOIN pg_class t ON t.oid = c.conrelid
                   JOIN pg_namespace n ON n.oid = t.relnamespace
                   WHERE n.nspname = 'console' AND t.relname = 'si_console_writes'
                     AND c.conname = 'si_console_writes_kind_check' AND c.contype = 'c') THEN
        RAISE EXCEPTION 'V25: 找不到 si_console_writes_kind_check，拒絕在未確認舊 CHECK 的情況下加新 CHECK'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
END
$$;
ALTER TABLE console.si_console_writes DROP CONSTRAINT si_console_writes_kind_check;
ALTER TABLE console.si_console_writes ADD CONSTRAINT si_console_writes_kind_check
    CHECK (kind IN ('decide', 'obs-add', 'obs-close', 'sched-set', 'run-request', 'src-registry'));
