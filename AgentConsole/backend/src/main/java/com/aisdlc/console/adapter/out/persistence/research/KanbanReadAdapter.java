package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchKanbanReadPort;
import com.aisdlc.console.domain.model.research.ResearchP2Views.GateRow;
import com.aisdlc.console.domain.model.research.ResearchP2Views.PendingReview;
import com.aisdlc.console.domain.model.research.ResearchP2Views.TaskCounts;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** 看板投影的 JDBC <b>唯讀</b>實作：只有 SELECT；不動既有 {@code ReviewRequestRepositoryAdapter}。 */
@Component
class KanbanReadAdapter implements ResearchKanbanReadPort {

    private static final String LATEST_RUN = "select id from console.execution_runs where project_id = :project order by run_number desc limit 1";

    private final JdbcClient jdbc;

    KanbanReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<UUID> latestRunId(UUID consoleProjectId) {
        return jdbc.sql(LATEST_RUN).param("project", consoleProjectId).query((rs, n) -> ResearchJdbc.uuid(rs, "id")).optional();
    }

    @Override
    public TaskCounts taskCounts(UUID consoleProjectId) {
        return jdbc.sql("select count(*) as total, count(*) filter (where t.status = 'RUNNING') as running, "
                + "count(*) filter (where t.status = 'COMPLETED') as completed, count(*) filter (where t.status = 'SKIPPED') as skipped, "
                + "count(*) filter (where t.status = 'FAILED') as failed, count(*) filter (where t.status = 'ESCALATED') as escalated, "
                + "(select count(distinct es.task_id) from console.execution_steps es where es.run_id = (" + LATEST_RUN + ") and es.status = 'RETRYING' "
                + "and not exists (select 1 from console.execution_steps e2 where e2.run_id = es.run_id and e2.task_id = es.task_id "
                + "and e2.step_number > es.step_number and e2.status <> 'RETRYING')) as retrying "
                + "from console.tasks t join console.goals g on g.id = t.goal_id where g.project_id = :project and coalesce(t.is_deleted, false) = false")
                .param("project", consoleProjectId)
                .query((rs, n) -> new TaskCounts(rs.getInt("total"), rs.getInt("running"), rs.getInt("completed"), rs.getInt("skipped"),
                        rs.getInt("failed"), rs.getInt("escalated"), rs.getInt("retrying")))
                .single();
    }

    @Override
    public List<PendingReview> pendingReviews(UUID consoleProjectId) {
        return jdbc.sql("select q.id, q.run_id, q.kind, q.task_id, q.reason, q.requested_at from console.review_requests q "
                + "join console.execution_runs r on r.id = q.run_id where r.project_id = :project and q.status = 'PENDING' "
                + "order by q.requested_at, q.id")
                .param("project", consoleProjectId)
                .query((rs, n) -> new PendingReview(ResearchJdbc.uuid(rs, "id"), ResearchJdbc.uuid(rs, "run_id"), rs.getString("kind"),
                        ResearchJdbc.uuid(rs, "task_id"), rs.getString("reason"), ResearchJdbc.ts(rs, "requested_at")))
                .list();
    }

    @Override
    public List<GateRow> gateDecisions(UUID researchId, int perGate) {
        return jdbc.sql("select gate, decision, decided_by, decided_at, fsm_state_after, reason from ("
                + "select d.*, row_number() over (partition by d.gate order by d.decided_at desc, d.id desc) as rn "
                + "from console.research_gate_decisions d where d.research_id = :id and d.gate in ('SCG4','SCG5','SCG6')) x "
                + "where rn <= :n order by gate, decided_at desc, id desc")
                .param("id", researchId).param("n", perGate)
                .query((rs, n) -> new GateRow(rs.getString("gate"), rs.getString("decision"), rs.getString("decided_by"),
                        ResearchJdbc.ts(rs, "decided_at"), rs.getString("fsm_state_after"), rs.getString("reason")))
                .list();
    }

    @Override
    public Optional<OffsetDateTime> latestEventAt(UUID consoleProjectId) {
        return jdbc.sql("select max(es.\"timestamp\") as at from console.execution_steps es join console.execution_runs r on r.id = es.run_id "
                + "where r.project_id = :project").param("project", consoleProjectId)
                .query((rs, n) -> Optional.ofNullable(ResearchJdbc.ts(rs, "at"))).single();
    }

    @Override
    public Optional<OffsetDateTime> latestDecisionAt(UUID researchId) {
        return jdbc.sql("select max(decided_at) as at from console.research_gate_decisions where research_id = :id").param("id", researchId)
                .query((rs, n) -> Optional.ofNullable(ResearchJdbc.ts(rs, "at"))).single();
    }
}
