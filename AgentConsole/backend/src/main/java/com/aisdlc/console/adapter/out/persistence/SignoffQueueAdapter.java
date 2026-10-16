package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.SignoffQueue;
import com.aisdlc.console.domain.model.signoff.PendingSignoffCounts;
import com.aisdlc.console.domain.model.signoff.PendingSignoffItem;
import com.aisdlc.console.domain.model.signoff.PendingSignoffKind;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/**
 * 待簽核草案的跨專案佇列（只讀；契約 §1.8.1；D-18）：用單純的 SQL，不載入任何實體。述詞全部來自 {@link PendingSignoffSql}
 * （與通知摘要的 {@code pendingSignoffs} 同一組）。
 */
@Component
class SignoffQueueAdapter implements SignoffQueue {

    private final JdbcTemplate jdbc;

    SignoffQueueAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public PendingSignoffCounts counts() {
        PendingSignoffCounts counts = jdbc.queryForObject(PendingSignoffSql.COUNTS, (rs, row) ->
                new PendingSignoffCounts(rs.getInt("projects"), rs.getInt("goals"), rs.getInt("tasks"),
                        rs.getInt("imports")));
        return counts == null ? new PendingSignoffCounts(0, 0, 0, 0) : counts;
    }

    @Override
    public List<PendingSignoffItem> items(int limit) {
        return jdbc.query(PendingSignoffSql.ITEMS, SignoffQueueAdapter::item, limit);
    }

    private static PendingSignoffItem item(ResultSet rs, int row) throws SQLException {
        OffsetDateTime createdAt = rs.getObject("created_at", OffsetDateTime.class);
        return new PendingSignoffItem(PendingSignoffKind.valueOf(rs.getString("kind")), rs.getObject("id", UUID.class),
                rs.getObject("project_id", UUID.class), rs.getString("project_name"),
                rs.getObject("parent_id", UUID.class), rs.getString("title"),
                createdAt == null ? null : createdAt.toInstant());
    }
}
