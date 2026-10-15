package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.NotificationCounts;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/**
 * 通知摘要的三個計數（只讀；契約 §1.4.1）。用單純的 SQL 計數：不載入任何實體。
 * {@code is_deleted} 在 DDL 允許 NULL，一律以 {@code coalesce(…, false)} 視為未刪除。
 */
@Component
class NotificationCountsAdapter implements NotificationCounts {

    private static final String PENDING_SIGNOFFS = """
            select
              (select count(*) from console.projects p
                where p.signed_off = false and coalesce(p.is_deleted, false) = false)
            + (select count(*) from console.goals g join console.projects p on p.id = g.project_id
                where g.signed_off = false and coalesce(g.is_deleted, false) = false
                  and coalesce(p.is_deleted, false) = false)
            + (select count(*) from console.tasks t
                join console.goals g on g.id = t.goal_id join console.projects p on p.id = g.project_id
                where t.signed_off = false and coalesce(t.is_deleted, false) = false
                  and coalesce(g.is_deleted, false) = false and coalesce(p.is_deleted, false) = false)
            + (select count(*) from console.import_records i
                where i.status in ('PARSED', 'REVIEWING') and i.signed_off = false)
            """;

    private final JdbcTemplate jdbc;

    NotificationCountsAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public int pendingSignoffs() {
        return count(PENDING_SIGNOFFS);
    }

    @Override
    public int pendingReviews() {
        return count("select count(*) from console.review_requests where status = 'PENDING'");
    }

    @Override
    public int unacknowledgedAlerts() {
        return count("select count(*) from console.alerts where acknowledged = false");
    }

    private int count(String sql) {
        Long value = jdbc.queryForObject(sql, Long.class);
        return value == null ? 0 : Math.toIntExact(value);
    }
}
