-- ============================================================================
-- V15__backup_jobs.sql — 系統管理／資料庫備份：Console 發起的手動備份工作（TCS-SysAdminBackup-20261027 §C5、R-BK-55；PRD §8.1）
-- 排程工作（sidecar crond 觸發）不建列，狀態在 sidecar 的 jobs/<job>.json（控制面檔案協定 v1）；這張表只記「掌舵者按鈕觸發的」工作：
-- 誰、何時、做什麼、結果如何。寫入者唯一＝console-api 的 BackupJobAdapter（Bridge、sidecar 不讀不寫）。
-- ① 單工：部分唯一索引 ux_backup_jobs_one_active（運算式 (1)，條件 status IN ('QUEUED','RUNNING')）——至多一個進行中的工作；
--    應用層的「已有進行中」檢查只是友善的 409，兩個併發 POST 的輸家由這個索引擋下（轉成同一個 409，不是 500）。
-- ② type 只有 full、diff、verify（dump 是排程專屬、不可手動；incr 不是手動型別）；status 六值；reason 為封閉詞彙（BackupJobReason）。
-- ③ detail 是已遮罩的輸出尾段（≤2000 字元；console-api 寫入前再遮罩一次），NOT NULL 預設空字串。
-- ④ 敘述種類恆為：INSERT（QUEUED）、條件式 UPDATE（WHERE status 仍在進行中）與唯讀 SELECT；沒有 DELETE、TRUNCATE。
-- 沒有 JPA 實體（ddl-auto=validate 不檢查本表）：以 JDBC 配接器存取；既有表零變動。
-- ============================================================================
CREATE TABLE console.backup_jobs (
    id           UUID PRIMARY KEY,
    type         VARCHAR(10)  NOT NULL CHECK (type IN ('full','diff','verify')),
    status       VARCHAR(12)  NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','REJECTED','EXPIRED')),
    requested_by VARCHAR(100) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at   TIMESTAMP WITH TIME ZONE,
    finished_at  TIMESTAMP WITH TIME ZONE,
    exit_code    INTEGER,
    reason       VARCHAR(30),   -- 封閉詞彙，見 AC-BK-06-8
    detail       VARCHAR(2000) NOT NULL DEFAULT ''   -- 已遮罩
);
CREATE UNIQUE INDEX ux_backup_jobs_one_active ON console.backup_jobs ((1)) WHERE status IN ('QUEUED','RUNNING');
CREATE INDEX idx_backup_jobs_requested_at ON console.backup_jobs (requested_at DESC);
