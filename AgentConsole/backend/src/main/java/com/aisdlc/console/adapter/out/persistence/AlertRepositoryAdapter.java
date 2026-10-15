package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.AlertRepository;
import com.aisdlc.console.domain.model.monitor.Alert;
import com.aisdlc.console.domain.model.monitor.AlertRule;
import com.aisdlc.console.domain.model.monitor.AlertSeverity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** {@link AlertRepository} 的 JDBC 實作（{@code alerts}；去重靠 V7 的 partial unique index）。 */
@Component
class AlertRepositoryAdapter implements AlertRepository {

    private static final String COLUMNS = "id, project_id, run_id, rule, severity, subject, message, created_at, "
            + "acknowledged, acknowledged_by, acknowledged_at, event_seq, event_sub";

    private static final RowMapper<Alert> MAPPER = (rs, rowNum) -> new Alert(JdbcSupport.uuid(rs, "id"),
            JdbcSupport.uuid(rs, "project_id"), JdbcSupport.uuid(rs, "run_id"), AlertRule.valueOf(rs.getString("rule")),
            AlertSeverity.valueOf(rs.getString("severity")), rs.getString("subject"), rs.getString("message"),
            JdbcSupport.instant(rs, "created_at"), rs.getBoolean("acknowledged"), rs.getString("acknowledged_by"),
            JdbcSupport.instant(rs, "acknowledged_at"), rs.getInt("event_seq"), rs.getInt("event_sub"));

    private final JdbcTemplate jdbc;

    AlertRepositoryAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<Alert> insertIfAbsent(Alert a) {
        int inserted = jdbc.update("insert into console.alerts (id, project_id, run_id, rule, severity, subject, "
                + "message, created_at, acknowledged, event_seq, event_sub) values (?, ?, ?, ?, ?, ?, ?, ?, false, ?, ?) "
                + "on conflict (project_id, rule, subject) where acknowledged = false do nothing", a.id(),
                a.projectId(), a.runId(), a.rule().name(), a.severity().name(), a.subject(), a.message(),
                JdbcSupport.ts(a.createdAt()), a.eventSeq(), a.eventSub());
        return inserted > 0 ? Optional.of(a) : Optional.empty();
    }

    @Override
    public Optional<Alert> findById(UUID id) {
        return jdbc.query("select " + COLUMNS + " from console.alerts where id = ?", MAPPER, id).stream().findFirst();
    }

    @Override
    public void acknowledge(UUID id, String by, Instant at) {
        jdbc.update("update console.alerts set acknowledged = true, acknowledged_by = ?, acknowledged_at = ? "
                + "where id = ? and acknowledged = false", by, JdbcSupport.ts(at), id);
    }

    @Override
    public List<Alert> find(UUID projectId, UUID runIdOrNull, Boolean acknowledged, int limit) {
        StringBuilder sql = new StringBuilder("select " + COLUMNS + " from console.alerts where project_id = ?");
        List<Object> args = new ArrayList<>();
        args.add(projectId);
        if (runIdOrNull != null) {
            sql.append(" and run_id = ?");
            args.add(runIdOrNull);
        }
        if (acknowledged != null) {
            sql.append(" and acknowledged = ?");
            args.add(acknowledged);
        }
        sql.append(" order by created_at desc, event_seq desc, event_sub desc limit ?");
        args.add(limit);
        return jdbc.query(sql.toString(), MAPPER, args.toArray());
    }

    @Override
    public List<Alert> findAnchoredAfter(UUID runId, int seq, int sub) {
        return jdbc.query("select " + COLUMNS + " from console.alerts where run_id = ? and event_sub >= 1 "
                + "and (event_seq > ? or (event_seq = ? and event_sub > ?)) order by event_seq asc, event_sub asc",
                MAPPER, runId, seq, seq, sub);
    }

    @Override
    public List<Alert> findByRun(UUID runId) {
        return jdbc.query("select " + COLUMNS + " from console.alerts where run_id = ? order by created_at asc",
                MAPPER, runId);
    }
}
