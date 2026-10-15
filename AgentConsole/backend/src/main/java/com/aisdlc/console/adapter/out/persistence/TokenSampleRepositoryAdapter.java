package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.TokenSampleRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.UUID;

/** {@link TokenSampleRepository} 的 JDBC 實作（{@code run_token_samples}）。 */
@Component
class TokenSampleRepositoryAdapter implements TokenSampleRepository {

    private final JdbcTemplate jdbc;

    TokenSampleRepositoryAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public boolean insert(Sample sample) {
        return jdbc.update("insert into console.run_token_samples (run_id, seq, ts, tokens_used, delta, context_pct, "
                + "task_id) values (?, ?, ?, ?, ?, ?, ?) on conflict (run_id, seq) do nothing", sample.runId(),
                sample.seq(), JdbcSupport.ts(sample.ts()), sample.tokensUsed(), sample.delta(), sample.contextPct(),
                sample.taskId()) > 0;
    }

    @Override
    public Optional<Sample> latest(UUID runId) {
        return jdbc.query("select run_id, seq, ts, tokens_used, delta, context_pct, task_id "
                + "from console.run_token_samples where run_id = ? order by seq desc limit 1",
                (rs, n) -> new Sample(JdbcSupport.uuid(rs, "run_id"), rs.getInt("seq"), JdbcSupport.instant(rs, "ts"),
                        rs.getLong("tokens_used"), rs.getLong("delta"),
                        rs.getObject("context_pct") == null ? null : rs.getDouble("context_pct"),
                        JdbcSupport.uuid(rs, "task_id")), runId).stream().findFirst();
    }

    @Override
    public long sumDeltaForTask(UUID runId, UUID taskId) {
        Long sum = jdbc.queryForObject("select coalesce(sum(delta), 0) from console.run_token_samples "
                + "where run_id = ? and task_id = ?", Long.class, runId, taskId);
        return sum == null ? 0 : sum;
    }

    @Override
    public long sumDeltaForGoal(UUID runId, UUID goalId) {
        Long sum = jdbc.queryForObject("select coalesce(sum(s.delta), 0) from console.run_token_samples s "
                + "join console.tasks t on t.id = s.task_id where s.run_id = ? and t.goal_id = ?", Long.class, runId,
                goalId);
        return sum == null ? 0 : sum;
    }
}
