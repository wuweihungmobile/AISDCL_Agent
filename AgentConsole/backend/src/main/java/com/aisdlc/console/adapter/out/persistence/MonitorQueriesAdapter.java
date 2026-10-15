package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.MonitorQueries;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** {@link MonitorQueries} 的 JDBC 實作：只讀、只取事實列（公式在 application 層）。 */
@Component
class MonitorQueriesAdapter implements MonitorQueries {

    private static final RowMapper<StepFact> STEP_MAPPER = (rs, rowNum) -> new StepFact(JdbcSupport.uuid(rs, "id"),
            JdbcSupport.uuid(rs, "run_id"), JdbcSupport.uuid(rs, "task_id"), rs.getString("status"),
            JdbcSupport.instant(rs, "timestamp"), rs.getString("step_id"), JdbcSupport.nullableInt(rs, "attempt"),
            rs.getString("error_message"));

    private static final RowMapper<TokenFact> TOKEN_MAPPER = (rs, rowNum) -> new TokenFact(JdbcSupport.uuid(rs, "run_id"),
            JdbcSupport.instant(rs, "ts"), rs.getLong("delta"), JdbcSupport.nullableLong(rs, "token_budget"),
            JdbcSupport.instant(rs, "run_started_at"));

    private final JdbcTemplate jdbc;

    MonitorQueriesAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<StepFact> steps(UUID projectId, UUID runIdOrNull, Instant fromInclusiveOrNull, Instant toExclusive) {
        StringBuilder sql = new StringBuilder("select s.id, s.run_id, s.task_id, s.status, s.timestamp, "
                + "s.input ->> 'step_id' as step_id, (s.input ->> 'attempt')::int as attempt, s.error_message "
                + "from console.execution_steps s join console.execution_runs r on r.id = s.run_id "
                + "where r.project_id = ?");
        List<Object> args = new ArrayList<>();
        args.add(projectId);
        if (runIdOrNull != null) {
            sql.append(" and s.run_id = ?");
            args.add(runIdOrNull);
        }
        if (fromInclusiveOrNull != null) {
            sql.append(" and s.timestamp >= ?");
            args.add(JdbcSupport.ts(fromInclusiveOrNull));
        }
        sql.append(" and s.timestamp < ? order by s.timestamp asc, s.id asc");
        args.add(JdbcSupport.ts(toExclusive));
        return jdbc.query(sql.toString(), STEP_MAPPER, args.toArray());
    }

    @Override
    public List<TokenFact> tokens(UUID projectId, UUID runIdOrNull, Instant fromInclusive, Instant toExclusive) {
        StringBuilder sql = new StringBuilder("select t.run_id, t.ts, t.delta, r.token_budget, "
                + "r.started_at as run_started_at from console.run_token_samples t "
                + "join console.execution_runs r on r.id = t.run_id where r.project_id = ?");
        List<Object> args = new ArrayList<>();
        args.add(projectId);
        if (runIdOrNull != null) {
            sql.append(" and t.run_id = ?");
            args.add(runIdOrNull);
        }
        sql.append(" and t.ts >= ? and t.ts < ? order by t.ts asc, t.seq asc");
        args.add(JdbcSupport.ts(fromInclusive));
        args.add(JdbcSupport.ts(toExclusive));
        return jdbc.query(sql.toString(), TOKEN_MAPPER, args.toArray());
    }

    @Override
    public ProjectCounts projectCounts() {
        return jdbc.queryForObject("select count(*) filter (where status = 'COMPLETED') as completed, "
                + "count(*) as countable from console.projects "
                + "where status <> 'ARCHIVED' and coalesce(is_deleted, false) = false",
                (rs, rowNum) -> new ProjectCounts(rs.getLong("completed"), rs.getLong("countable")));
    }
}
