package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.ProjectPurger;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * {@link ProjectPurger} 的 JDBC 實作。刪除順序由外鍵決定（子表先於父表）：審核項（參照步驟、任務、目標、批次）→ 告警（參照專案與批次）→
 * 斷點與 token 樣本（隨批次）→ 步驟（參照批次與任務）→ 批次 → 任務 → 目標（目標依賴以 {@code ON DELETE CASCADE} 隨目標）→
 * 匯入記錄的 {@code project_id} 置 NULL → 專案。呼叫端提供交易，所以任何一步失敗整個專案原封不動。
 */
@Component
class ProjectPurgerAdapter implements ProjectPurger {

    private static final String RUNS_OF_PROJECT = "(select id from console.execution_runs where project_id = ?)";

    private final JdbcTemplate jdbc;

    ProjectPurgerAdapter(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<UUID> findExpired(Instant cutoff) {
        return jdbc.query("select id from console.projects where is_deleted = true and deleted_at < ? "
                + "order by deleted_at asc, id asc", (rs, n) -> JdbcSupport.uuid(rs, "id"), JdbcSupport.ts(cutoff));
    }

    @Override
    public boolean purge(UUID projectId) {
        jdbc.update("delete from console.review_requests where run_id in " + RUNS_OF_PROJECT, projectId);
        jdbc.update("delete from console.alerts where project_id = ?", projectId);
        jdbc.update("delete from console.checkpoints where run_id in " + RUNS_OF_PROJECT, projectId);
        jdbc.update("delete from console.run_token_samples where run_id in " + RUNS_OF_PROJECT, projectId);
        jdbc.update("delete from console.execution_steps where run_id in " + RUNS_OF_PROJECT, projectId);
        jdbc.update("delete from console.execution_runs where project_id = ?", projectId);
        jdbc.update("delete from console.tasks where goal_id in (select id from console.goals where project_id = ?)",
                projectId);
        jdbc.update("delete from console.goals where project_id = ?", projectId);
        jdbc.update("update console.import_records set project_id = null where project_id = ?", projectId);
        return jdbc.update("delete from console.projects where id = ? and is_deleted = true", projectId) > 0;
    }
}
