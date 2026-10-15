package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.ExecutionStepRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** {@link ExecutionStepRepository} 的 JDBC 實作（唯讀；{@code step_id}／{@code attempt} 取自 {@code input} JSON）。 */
@Component
class ExecutionStepRepositoryAdapter implements ExecutionStepRepository {

    private static final String COLUMNS = "id, run_id, task_id, step_number, action, status, "
            + "input ->> 'step_id' as step_id, (input ->> 'attempt')::int as attempt, error_message, output, timestamp";

    private static final RowMapper<StepRow> MAPPER = (rs, rowNum) -> new StepRow(JdbcSupport.uuid(rs, "id"),
            JdbcSupport.uuid(rs, "run_id"), JdbcSupport.uuid(rs, "task_id"), rs.getInt("step_number"),
            rs.getString("action"), rs.getString("status"), rs.getString("step_id"),
            JdbcSupport.nullableInt(rs, "attempt"), rs.getString("error_message"), rs.getString("output"),
            JdbcSupport.instant(rs, "timestamp"));

    private final JdbcTemplate jdbc;

    ExecutionStepRepositoryAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public PageResult<StepRow> findPage(UUID runId, int afterSeq, int page, int size) {
        Long total = jdbc.queryForObject("select count(*) from console.execution_steps where run_id = ? "
                + "and step_number > ?", Long.class, runId, afterSeq);
        List<StepRow> content = jdbc.query("select " + COLUMNS + " from console.execution_steps where run_id = ? "
                + "and step_number > ? order by step_number asc, timestamp asc, id asc limit ? offset ?", MAPPER,
                runId, afterSeq, size, (long) page * size);
        return new PageResult<>(content, page, size, total == null ? 0 : total);
    }

    @Override
    public boolean existsByRun(UUID runId) {
        Boolean exists = jdbc.queryForObject("select exists (select 1 from console.execution_steps where run_id = ?)",
                Boolean.class, runId);
        return Boolean.TRUE.equals(exists);
    }

    @Override
    public Optional<StepRow> findLatest(UUID runId, String stepId, String status) {
        return jdbc.query("select " + COLUMNS + " from console.execution_steps where run_id = ? "
                + "and input ->> 'step_id' = ? and status = ? order by step_number desc limit 1", MAPPER, runId,
                stepId, status).stream().findFirst();
    }

    @Override
    public List<StepRow> findAllByRun(UUID runId) {
        return jdbc.query("select " + COLUMNS + " from console.execution_steps where run_id = ? "
                + "order by step_number asc, timestamp asc, id asc", MAPPER, runId);
    }

    @Override
    public List<StepRow> findByRunAndTask(UUID runId, UUID taskId) {
        return jdbc.query("select " + COLUMNS + " from console.execution_steps where run_id = ? and task_id = ? "
                + "order by step_number asc, timestamp asc, id asc", MAPPER, runId, taskId);
    }

    @Override
    public List<StepRow> findRecentByTask(UUID taskId, int limit) {
        // 先取最近 limit 筆（降冪），再翻成升冪：任務的歷史跨批次，seq 每批次重新起算，所以以 timestamp 為主鍵、seq 為次鍵
        List<StepRow> newestFirst = jdbc.query("select " + COLUMNS + " from console.execution_steps where task_id = ? "
                + "order by timestamp desc, step_number desc, id desc limit ?", MAPPER, taskId, limit);
        return newestFirst.reversed();
    }
}
