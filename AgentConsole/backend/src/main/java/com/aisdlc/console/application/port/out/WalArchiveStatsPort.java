package com.aisdlc.console.application.port.out;

import java.time.Instant;

/**
 * WAL 歸檔健康（Q7；TCS-SysAdminBackup-20261027 D-BK-T20、R-BK-22）：讀 {@code pg_stat_archiver} 的一條唯讀 SELECT
 * （{@code WalArchiveStatsAdapter}，console-api 既有連線）。讀不到丟例外（{@code DataAccessException} 等），由呼叫端降級為
 * {@code walArchive:null} 加 {@code db_unavailable}——<b>不當 0、不吞例外回零物件</b>（真實的零＝全新叢集，仍是物件）。
 */
public interface WalArchiveStatsPort {

    /** {@code lastArchivedAt}、{@code lastFailedAt} 可為 null（尚未歸檔／從未失敗）。 */
    record Stats(Instant lastArchivedAt, long failedCount, Instant lastFailedAt) {
    }

    /** 讀一次；失敗丟例外。 */
    Stats read();
}
