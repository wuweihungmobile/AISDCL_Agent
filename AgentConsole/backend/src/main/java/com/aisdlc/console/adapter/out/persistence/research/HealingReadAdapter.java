package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchHealingReadPort;
import com.aisdlc.console.domain.model.research.ResearchP2Views.HealingAttempt;
import com.aisdlc.console.domain.model.research.ResearchP2Views.HealingFacts;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.UUID;

/**
 * 自癒視圖 {@code console.v_research_healing_attempts}（V19）的 JDBC <b>唯讀</b>實作。{@code attempt}＝同 (run, task) 內依 step_number 的序號；
 * {@code resolved}＝該任務現為 COMPLETED；{@code escalated}＝該任務現為 ESCALATED 且此列是該任務的最後一列；excerpt 先遮蔽再取尾端 300 字元。
 */
@Component
class HealingReadAdapter implements ResearchHealingReadPort {

    private static final String LATEST_RUN = "select id from console.execution_runs where project_id = :project order by run_number desc limit 1";

    private final JdbcClient jdbc;

    HealingReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<HealingAttempt> attempts(UUID researchId) {
        return jdbc.sql("select v.run_id, v.task_id, v.step_number, v.status, v.error_message, v.occurred_at, "
                + "row_number() over (partition by v.run_id, v.task_id order by v.step_number) as attempt, t.status as task_status, "
                + "(v.step_number = max(v.step_number) over (partition by v.run_id, v.task_id)) as is_last "
                + "from console.v_research_healing_attempts v join console.tasks t on t.id = v.task_id "
                + "where v.research_id = :id order by v.run_number, v.task_id, v.step_number")
                .param("id", researchId)
                .query((rs, n) -> new HealingAttempt(ResearchJdbc.uuid(rs, "run_id"), ResearchJdbc.uuid(rs, "task_id"), rs.getInt("step_number"),
                        rs.getInt("attempt"), rs.getString("status"), HealingExcerptMasker.excerpt(rs.getString("error_message")),
                        ResearchJdbc.ts(rs, "occurred_at"), "COMPLETED".equals(rs.getString("task_status")),
                        "ESCALATED".equals(rs.getString("task_status")) && rs.getBoolean("is_last")))
                .list();
    }

    @Override
    public HealingFacts facts(UUID consoleProjectId) {
        int retrying = jdbc.sql("select count(*) from console.execution_steps es where es.run_id = (" + LATEST_RUN + ") and es.status = 'RETRYING' "
                + "and not exists (select 1 from console.execution_steps e2 where e2.run_id = es.run_id and e2.task_id = es.task_id "
                + "and e2.step_number > es.step_number and e2.status <> 'RETRYING')")
                .param("project", consoleProjectId).query(Integer.class).single();
        int escalated = jdbc.sql("select count(*) from console.tasks t join console.goals g on g.id = t.goal_id where g.project_id = :project "
                + "and t.status = 'ESCALATED' and coalesce(t.is_deleted, false) = false")
                .param("project", consoleProjectId).query(Integer.class).single();
        return new HealingFacts(retrying, escalated);
    }
}
