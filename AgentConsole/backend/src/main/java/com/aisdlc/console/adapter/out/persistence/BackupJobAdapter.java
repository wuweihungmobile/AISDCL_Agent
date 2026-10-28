package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.BackupJobRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 備份工作表（{@code console.backup_jobs}；TCS-SysAdminBackup-20261027 R-BK-55、§C5）的 JDBC 實作：<b>整個 backend 唯一存取這張表的類別</b>
 * （ArchUnit 鎖住）。沒有 JPA 實體。寫入敘述種類恆為：INSERT（QUEUED）與三種<b>條件式</b> UPDATE（{@code markRunningIfQueued}、
 * {@code markTerminalIfActive}、{@code markExpiredIfQueued}，每一條的 WHERE 都限定 status 仍在進行中）；沒有 DELETE、TRUNCATE，也沒有無條件的 UPDATE——
 * 條件式讓並發的撿取、對帳、過期兜底只有一方生效（回傳值＝這一次有沒有更新到列）。
 */
@Component
class BackupJobAdapter implements BackupJobRepository {

    private static final String COLUMNS = "id, type, status, requested_by, requested_at, started_at, finished_at, exit_code, reason, detail";

    private static final RowMapper<Job> ROW = BackupJobAdapter::job;

    private final JdbcTemplate jdbc;

    BackupJobAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<Job> findActive() {
        return jdbc.query("select " + COLUMNS + " from console.backup_jobs where status in ('QUEUED','RUNNING') "
                + "order by requested_at", ROW);
    }

    @Override
    public void insertQueued(Job job) {
        jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at) values (?, ?, ?, ?, ?)",
                job.id(), job.type(), Status.QUEUED.name(), job.requestedBy(), at(job.requestedAt()));
    }

    @Override
    public boolean markRunningIfQueued(UUID id, Instant startedAt) {
        return jdbc.update("update console.backup_jobs set status = 'RUNNING', started_at = ? "
                + "where id = ? and status = 'QUEUED'", at(startedAt), id) > 0;
    }

    @Override
    public boolean markTerminalIfActive(UUID id, Status status, Integer exitCode, String reason, Instant startedAt,
                                        Instant finishedAt, String detail) {
        return jdbc.update("update console.backup_jobs set status = ?, exit_code = ?, reason = ?, "
                + "started_at = coalesce(?, started_at), finished_at = ?, detail = ? "
                + "where id = ? and status in ('QUEUED','RUNNING')", status.name(), exitCode, reason, at(startedAt),
                at(finishedAt), detail == null ? "" : detail, id) > 0;
    }

    @Override
    public boolean markExpiredIfQueued(UUID id, Instant finishedAt) {
        return jdbc.update("update console.backup_jobs set status = 'EXPIRED', reason = 'expired', finished_at = ? "
                + "where id = ? and status = 'QUEUED'", at(finishedAt), id) > 0;
    }

    @Override
    public Optional<Job> findById(UUID id) {
        return jdbc.query("select " + COLUMNS + " from console.backup_jobs where id = ?", ROW, id).stream().findFirst();
    }

    @Override
    public List<Job> findPage(Instant before, int limit) {
        if (before == null) {
            return jdbc.query("select " + COLUMNS + " from console.backup_jobs order by requested_at desc limit ?", ROW, limit);
        }
        return jdbc.query("select " + COLUMNS + " from console.backup_jobs where requested_at < ? "
                + "order by requested_at desc limit ?", ROW, at(before), limit);
    }

    private static OffsetDateTime at(Instant instant) {
        return instant == null ? null : OffsetDateTime.ofInstant(instant, ZoneOffset.UTC);
    }

    private static Instant instant(ResultSet rs, String column) throws SQLException {
        OffsetDateTime value = rs.getObject(column, OffsetDateTime.class);
        return value == null ? null : value.toInstant();
    }

    private static Job job(ResultSet rs, int rowNumber) throws SQLException {
        int exit = rs.getInt("exit_code");
        Integer exitCode = rs.wasNull() ? null : exit;
        return new Job(rs.getObject("id", UUID.class), rs.getString("type"), Status.valueOf(rs.getString("status")),
                rs.getString("requested_by"), instant(rs, "requested_at"), instant(rs, "started_at"),
                instant(rs, "finished_at"), exitCode, rs.getString("reason"), rs.getString("detail"));
    }
}
