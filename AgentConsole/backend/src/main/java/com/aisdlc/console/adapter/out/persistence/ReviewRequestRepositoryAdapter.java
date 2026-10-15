package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.domain.model.execution.ReviewKind;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** {@link ReviewRequestRepository} 的 JDBC 實作（{@code review_requests}；錨點欄位 {@code event_seq／event_sub} 見 V7）。 */
@Component
class ReviewRequestRepositoryAdapter implements ReviewRequestRepository {

    private static final String COLUMNS = "id, run_id, step_id, task_id, goal_id, kind, status, reason, requested_at, "
            + "decided_by, decided_at, comment, event_seq, event_sub";

    private static final RowMapper<ReviewRequest> MAPPER = (rs, rowNum) -> new ReviewRequest(
            JdbcSupport.uuid(rs, "id"), JdbcSupport.uuid(rs, "run_id"), JdbcSupport.uuid(rs, "step_id"),
            JdbcSupport.uuid(rs, "task_id"), JdbcSupport.uuid(rs, "goal_id"), ReviewKind.valueOf(rs.getString("kind")),
            ReviewStatus.valueOf(rs.getString("status")), rs.getString("reason"),
            JdbcSupport.instant(rs, "requested_at"), rs.getString("decided_by"), JdbcSupport.instant(rs, "decided_at"),
            rs.getString("comment"), rs.getInt("event_seq"), rs.getInt("event_sub"));

    private final JdbcTemplate jdbc;

    ReviewRequestRepositoryAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public ReviewRequest insert(ReviewRequest r) {
        jdbc.update("insert into console.review_requests (id, run_id, step_id, task_id, goal_id, kind, status, reason, "
                + "requested_at, decided_by, decided_at, comment, event_seq, event_sub) "
                + "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", r.id(), r.runId(), r.stepRowId(), r.taskId(),
                r.goalId(), r.kind().name(), r.status().name(), r.reason(), JdbcSupport.ts(r.requestedAt()),
                r.decidedBy(), JdbcSupport.ts(r.decidedAt()), r.comment(), r.eventSeq(), r.eventSub());
        return r;
    }

    @Override
    public Optional<ReviewRequest> findById(UUID id) {
        return jdbc.query("select " + COLUMNS + " from console.review_requests where id = ?", MAPPER, id).stream()
                .findFirst();
    }

    @Override
    public Optional<ReviewRequest> findByIdForUpdate(UUID id) {
        return jdbc.query("select " + COLUMNS + " from console.review_requests where id = ? for update", MAPPER, id)
                .stream().findFirst();
    }

    @Override
    public List<ReviewRequest> findByRunAndStatus(UUID runId, ReviewStatus status) {
        return jdbc.query("select " + COLUMNS + " from console.review_requests where run_id = ? and status = ? "
                + "order by requested_at asc, event_seq asc, event_sub asc", MAPPER, runId, status.name());
    }

    @Override
    public List<ReviewRequest> findByRun(UUID runId) {
        return jdbc.query("select " + COLUMNS + " from console.review_requests where run_id = ? "
                + "order by requested_at asc, event_seq asc, event_sub asc", MAPPER, runId);
    }

    @Override
    public List<ReviewRequest> findPendingOfOtherRuns(UUID projectId, UUID exceptRunId) {
        return jdbc.query("select " + COLUMNS + " from console.review_requests where status = 'PENDING' "
                + "and run_id <> ? and run_id in (select id from console.execution_runs where project_id = ?) "
                + "order by requested_at asc", MAPPER, exceptRunId, projectId);
    }

    @Override
    public List<ReviewRequest> findByProject(UUID projectId, UUID runIdOrNull) {
        if (runIdOrNull != null) {
            return findByRun(runIdOrNull);
        }
        return jdbc.query("select " + COLUMNS + " from console.review_requests where run_id in "
                + "(select id from console.execution_runs where project_id = ?) order by requested_at asc", MAPPER,
                projectId);
    }

    @Override
    public void update(ReviewRequest r) {
        jdbc.update("update console.review_requests set status = ?, decided_by = ?, decided_at = ?, comment = ? "
                + "where id = ?", r.status().name(), r.decidedBy(), JdbcSupport.ts(r.decidedAt()), r.comment(), r.id());
    }

    @Override
    public List<ReviewRequest> findAnchoredAfter(UUID runId, int seq, int sub) {
        return jdbc.query("select " + COLUMNS + " from console.review_requests where run_id = ? and event_sub >= 1 "
                + "and (event_seq > ? or (event_seq = ? and event_sub > ?)) order by event_seq asc, event_sub asc",
                MAPPER, runId, seq, seq, sub);
    }

    @Override
    public int nextEventSub(UUID runId, int anchorSeq) {
        Integer next = jdbc.queryForObject("select coalesce(max(m), 0) + 1 from ("
                + "select max(event_sub) as m from console.review_requests where run_id = ? and event_seq = ? "
                + "union all select max(event_sub) from console.alerts where run_id = ? and event_seq = ?) x",
                Integer.class, runId, anchorSeq, runId, anchorSeq);
        return next == null ? 1 : next;
    }
}
