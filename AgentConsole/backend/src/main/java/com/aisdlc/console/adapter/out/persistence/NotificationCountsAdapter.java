package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.NotificationCounts;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/**
 * 通知摘要的三個計數（只讀；契約 §1.4.1）。用單純的 SQL 計數：不載入任何實體。{@code pendingSignoffs} 的述詞<b>不在這裡寫</b>：
 * 它與 {@code GET /signoffs/pending} 的計數與清單共用 {@link PendingSignoffSql} 那一組（契約 §1.8.1 的實作約束：不得計數一份、清單一份）。
 */
@Component
class NotificationCountsAdapter implements NotificationCounts {

    private final JdbcTemplate jdbc;

    NotificationCountsAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public int pendingSignoffs() {
        return count(PendingSignoffSql.TOTAL);
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
