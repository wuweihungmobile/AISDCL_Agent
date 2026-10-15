package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.CheckpointRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** {@link CheckpointRepository} 的 JDBC 實作（唯讀；{@code state_snapshot} 只取三個欄位，不回傳本體）。 */
@Component
class CheckpointRepositoryAdapter implements CheckpointRepository {

    private static final String COLUMNS = "id, run_id, name, created_at, is_automatic, state_snapshot::text as snapshot";

    private static final RowMapper<CheckpointRow> MAPPER = (rs, rowNum) -> {
        String snapshot = rs.getString("snapshot");
        return new CheckpointRow(JdbcSupport.uuid(rs, "id"), JdbcSupport.uuid(rs, "run_id"), rs.getString("name"),
                JdbcSupport.instant(rs, "created_at"), rs.getBoolean("is_automatic"),
                ExecutionJson.snapshotStepIdx(snapshot), ExecutionJson.snapshotStepId(snapshot),
                ExecutionJson.snapshotCompletedStepIds(snapshot));
    };

    private final JdbcTemplate jdbc;

    CheckpointRepositoryAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<CheckpointRow> findByRun(UUID runId) {
        return jdbc.query("select " + COLUMNS + " from console.checkpoints where run_id = ? "
                + "order by created_at asc, id asc", MAPPER, runId);
    }

    @Override
    public Optional<CheckpointRow> findById(UUID id) {
        return jdbc.query("select " + COLUMNS + " from console.checkpoints where id = ?", MAPPER, id).stream()
                .findFirst();
    }
}
