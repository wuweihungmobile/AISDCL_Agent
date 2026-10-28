package com.aisdlc.console.application.port.out;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Console 發起的備份工作表（{@code console.backup_jobs}；TCS-SysAdminBackup-20261027 §C5、R-BK-55）。<b>寫入者唯一</b>是它的 JDBC 實作
 * {@code BackupJobAdapter}；寫入敘述只有 INSERT（QUEUED）與三種條件式 UPDATE，沒有 DELETE、TRUNCATE：
 * 「條件式」讓並發的兩方（撿取、對帳、過期兜底）只有一方生效——回傳值是「這一次有沒有更新到列」。
 */
public interface BackupJobRepository {

    /** 狀態的六個值（V15 的 CHECK 同集合）。 */
    enum Status {
        QUEUED, RUNNING, SUCCEEDED, FAILED, REJECTED, EXPIRED;

        /** 進行中（佔住部分唯一索引 ux_backup_jobs_one_active）。 */
        public boolean isActive() {
            return this == QUEUED || this == RUNNING;
        }
    }

    /**
     * 一列。{@code type}＝{@code full}｜{@code diff}｜{@code verify}；{@code reason} 為封閉詞彙（{@code BackupJobReason#value}）或 null；
     * {@code detail} 已遮罩、≤2000 字元（寫入時再遮一次）。
     */
    record Job(UUID id, String type, Status status, String requestedBy, Instant requestedAt, Instant startedAt,
               Instant finishedAt, Integer exitCode, String reason, String detail) {
    }

    /** 進行中（QUEUED、RUNNING）的列；部分唯一索引保證至多一列，但對帳以清單處理。資料庫讀取失敗丟 {@code DataAccessException}。 */
    List<Job> findActive();

    /** 新增一列 QUEUED；已有進行中的列時資料庫以唯一鍵拒絕（丟 {@code DuplicateKeyException}，呼叫端轉 409）。 */
    void insertQueued(Job job);

    /** {@code WHERE id=? AND status='QUEUED'}：撿取（runner 已寫 running）；回是否更新到列。 */
    boolean markRunningIfQueued(UUID id, Instant startedAt);

    /** {@code WHERE id=? AND status IN ('QUEUED','RUNNING')}：寫終態；{@code startedAt} 為 null 時保留原值；回是否更新到列。 */
    boolean markTerminalIfActive(UUID id, Status status, Integer exitCode, String reason, Instant startedAt,
                                 Instant finishedAt, String detail);

    /** {@code WHERE id=? AND status='QUEUED'}：過期兜底（EXPIRED、reason expired）；回是否更新到列。 */
    boolean markExpiredIfQueued(UUID id, Instant finishedAt);

    /** 單筆；查無回空。 */
    Optional<Job> findById(UUID id);

    /** 依 {@code requested_at} 新到舊的一頁；{@code before} 為 null＝從最新開始，否則只取嚴格早於它者；最多 {@code limit} 筆。 */
    List<Job> findPage(Instant before, int limit);
}
