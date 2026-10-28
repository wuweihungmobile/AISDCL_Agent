package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.WalArchiveStatsPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;

/**
 * WAL 歸檔健康的讀取（Q7；TCS-SysAdminBackup-20261027 D-BK-T20、R-BK-22）：<b>一條唯讀 SELECT</b> 讀 PostgreSQL 的歸檔統計視圖（console-api 既有連線）。
 * 讀不到（連線失敗、查詢失敗）<b>丟出例外</b>、不吞、不回零物件——由呼叫端降級為 {@code walArchive:null} 加 {@code db_unavailable}；
 * 真實的零（全新叢集：{@code failed_count=0}、兩個時間為 NULL）仍是物件。這張視圖只被本類別觸及（ArchUnit 鎖住）。
 */
@Component
class WalArchiveStatsAdapter implements WalArchiveStatsPort {

    private static final String SQL = "select failed_count, last_archived_time, last_failed_time from pg_stat_archiver";

    private final JdbcTemplate jdbc;

    WalArchiveStatsAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Stats read() {
        return jdbc.queryForObject(SQL, (rs, rowNumber) -> new Stats(instant(rs, "last_archived_time"),
                rs.getLong("failed_count"), instant(rs, "last_failed_time")));
    }

    private static Instant instant(ResultSet rs, String column) throws SQLException {
        OffsetDateTime value = rs.getObject(column, OffsetDateTime.class);
        return value == null ? null : value.toInstant();
    }
}
