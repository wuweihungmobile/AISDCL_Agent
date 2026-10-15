package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * {@link ExecutionRunRepository} 的 JDBC 實作。刻意不用 JPA 實體做寫入：{@code execution_runs} 的大半欄位由 Bridge
 * 直接更新，整列回寫（merge）會蓋掉它們（PRD §0.2.2）；INSERT 只列 console 欄位，更新只有目標明確的
 * {@code UPDATE … SET console_last_seq}。
 */
@Component
class ExecutionRunRepositoryAdapter implements ExecutionRunRepository {

    private static final String COLUMNS = "id, project_id, run_number, status, autonomy_level, scope::text as scope, "
            + "total_tokens_used, token_budget, started_at, completed_at, dag::text as dag, console_last_seq, "
            + "bridge_instance";

    private static final RowMapper<ExecutionRun> MAPPER = (rs, rowNum) -> new ExecutionRun(
            JdbcSupport.uuid(rs, "id"), JdbcSupport.uuid(rs, "project_id"), rs.getInt("run_number"),
            RunStatus.valueOf(rs.getString("status")), rs.getInt("autonomy_level"),
            ExecutionJson.scopeFromJson(rs.getString("scope")), rs.getLong("total_tokens_used"),
            JdbcSupport.nullableLong(rs, "token_budget"), JdbcSupport.instant(rs, "started_at"),
            JdbcSupport.instant(rs, "completed_at"), ExecutionJson.dagFromJson(rs.getString("dag")),
            rs.getInt("console_last_seq"), rs.getString("bridge_instance"));

    private final JdbcTemplate jdbc;

    ExecutionRunRepositoryAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public ExecutionRun insert(ExecutionRun run) {
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, autonomy_level, scope, "
                        + "token_budget, dag, started_at) values (?, ?, ?, ?, ?::jsonb, ?, ?::jsonb, ?)",
                run.id(), run.projectId(), run.runNumber(), run.autonomyLevel(), ExecutionJson.scopeToJson(run.scope()),
                run.tokenBudget(), ExecutionJson.dagToJson(run.dag()), JdbcSupport.ts(run.startedAt()));
        return findById(run.id()).orElseThrow();
    }

    @Override
    public Optional<ExecutionRun> findById(UUID id) {
        return jdbc.query("select " + COLUMNS + " from console.execution_runs where id = ?", MAPPER, id).stream()
                .findFirst();
    }

    @Override
    public Optional<ExecutionRun> findLatestByProject(UUID projectId) {
        return jdbc.query("select " + COLUMNS + " from console.execution_runs where project_id = ? "
                + "order by run_number desc limit 1", MAPPER, projectId).stream().findFirst();
    }

    @Override
    public int nextRunNumber(UUID projectId) {
        Integer max = jdbc.queryForObject("select coalesce(max(run_number), 0) from console.execution_runs "
                + "where project_id = ?", Integer.class, projectId);
        return (max == null ? 0 : max) + 1;
    }

    @Override
    public Optional<UUID> findActiveRunId(UUID projectId) {
        return jdbc.query("select id from console.execution_runs where project_id = ? "
                + "and status in ('INITIALIZING', 'RUNNING') order by run_number desc limit 1",
                (rs, n) -> JdbcSupport.uuid(rs, "id"), projectId).stream().findFirst();
    }

    @Override
    public PageResult<ExecutionRun> findPageByProject(UUID projectId, RunStatus status, boolean byRunNumber,
                                                      boolean ascending, int page, int size) {
        List<Object> args = new ArrayList<>();
        args.add(projectId);
        String where = "where project_id = ?";
        if (status != null) {
            where += " and status = ?";
            args.add(status.name());
        }
        Long total = jdbc.queryForObject("select count(*) from console.execution_runs " + where, Long.class,
                args.toArray());
        String order = (byRunNumber ? "run_number" : "started_at") + (ascending ? " asc" : " desc")
                + ", run_number " + (ascending ? "asc" : "desc");
        args.add(size);
        args.add((long) page * size);
        List<ExecutionRun> content = jdbc.query("select " + COLUMNS + " from console.execution_runs " + where
                + " order by " + order + " limit ? offset ?", MAPPER, args.toArray());
        return new PageResult<>(content, page, size, total == null ? 0 : total);
    }

    @Override
    public List<ExecutionRun> findByStatuses(Collection<RunStatus> statuses) {
        if (statuses.isEmpty()) {
            return List.of();
        }
        String in = String.join(",", statuses.stream().map(s -> "'" + s.name() + "'").toList());
        return jdbc.query("select " + COLUMNS + " from console.execution_runs where status in (" + in
                + ") order by started_at", MAPPER);
    }

    @Override
    public List<ExecutionRun> findAllByProject(UUID projectId) {
        return jdbc.query("select " + COLUMNS + " from console.execution_runs where project_id = ? "
                + "order by run_number asc", MAPPER, projectId);
    }

    @Override
    public List<ExecutionRun> findTerminalOfExecutingProjects() {
        return jdbc.query("select " + COLUMNS + " from console.execution_runs r where r.status in "
                + "('COMPLETED', 'FAILED', 'CANCELLED') and r.project_id in "
                + "(select id from console.projects where status = 'EXECUTING') and r.run_number = "
                + "(select max(x.run_number) from console.execution_runs x where x.project_id = r.project_id) "
                + "order by r.started_at", MAPPER);
    }

    @Override
    public boolean deleteById(UUID id) {
        return jdbc.update("delete from console.execution_runs where id = ?", id) > 0;
    }

    @Override
    public void updateConsoleLastSeq(UUID id, int seq) {
        jdbc.update("update console.execution_runs set console_last_seq = ? where id = ? and console_last_seq < ?",
                seq, id, seq);
    }
}
