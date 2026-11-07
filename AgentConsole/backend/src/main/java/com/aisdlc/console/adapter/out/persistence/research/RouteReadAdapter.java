package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.application.port.out.ResearchRouteReadPort;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Route;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.RouteStep;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 分流決定與步驟的 JDBC <b>唯讀</b>實作（{@link ResearchRouteReadPort}；ADR-003 D4）。沒有 JPA 實體、沒有任何寫入敘述：V19 的分流表只有 Bridge 能寫。
 * 時間欄位一律 {@code timestamptz}、以 {@code OffsetDateTime} 取回。
 */
@Component
class RouteReadAdapter implements ResearchRouteReadPort {

    private static final String ROUTE_COLUMNS = "select id, research_id, track, target_kind, target_module, target_path, git_branch, base_ref, repo_url, "
            + "repo_visibility, stack_template, console_project_id, impl_fsm_project, impl_state_dir, published_docs::text as published_docs, "
            + "scope_differs_reason, status, failure_step, decided_by, created_at, finished_at from console.research_route_decisions where research_id = :id";

    private final JdbcClient jdbc;

    RouteReadAdapter(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public Optional<Route> latest(UUID researchId) {
        return jdbc.sql(ROUTE_COLUMNS + " order by created_at desc, id limit 1").param("id", researchId)
                .query(RouteReadAdapter::route).optional().map(this::withSteps);
    }

    @Override
    public Optional<Route> active(UUID researchId) {
        return jdbc.sql(ROUTE_COLUMNS + " and status in ('PENDING', 'RUNNING', 'SUCCEEDED') order by created_at desc limit 1")
                .param("id", researchId).query(RouteReadAdapter::route).optional().map(this::withSteps);
    }

    private Route withSteps(Route route) {
        List<RouteStep> steps = jdbc.sql("select step_no, step, status, argv_redacted, exit_code, stdout_tail, stderr_tail, started_at, finished_at "
                + "from console.research_route_steps where route_id = :route order by step_no").param("route", route.id())
                .query((rs, n) -> new RouteStep(rs.getInt("step_no"), rs.getString("step"), rs.getString("status"), rs.getString("argv_redacted"),
                        ResearchJdbc.nullableInt(rs, "exit_code"), rs.getString("stdout_tail"), rs.getString("stderr_tail"),
                        ResearchJdbc.ts(rs, "started_at"), ResearchJdbc.ts(rs, "finished_at")))
                .list();
        return new Route(route.id(), route.researchId(), route.track(), route.targetKind(), route.targetModule(), route.targetPath(), route.gitBranch(),
                route.baseRef(), route.repoUrl(), route.repoVisibility(), route.stackTemplate(), route.consoleProjectId(), route.implFsmProject(),
                route.implStateDir(), route.publishedDocs(), route.scopeDiffersReason(), route.status(), route.failureStep(), route.decidedBy(),
                route.createdAt(), route.finishedAt(), List.copyOf(steps));
    }

    private static Route route(ResultSet rs, int row) throws SQLException {
        return new Route(ResearchJdbc.uuid(rs, "id"), ResearchJdbc.uuid(rs, "research_id"), rs.getString("track"), rs.getString("target_kind"),
                rs.getString("target_module"), rs.getString("target_path"), rs.getString("git_branch"), rs.getString("base_ref"),
                rs.getString("repo_url"), rs.getString("repo_visibility"), rs.getString("stack_template"), ResearchJdbc.uuid(rs, "console_project_id"),
                rs.getString("impl_fsm_project"), rs.getString("impl_state_dir"), ResearchJdbc.object(rs.getString("published_docs")),
                rs.getString("scope_differs_reason"), rs.getString("status"), rs.getString("failure_step"), rs.getString("decided_by"),
                ResearchJdbc.ts(rs, "created_at"), ResearchJdbc.ts(rs, "finished_at"), List.of());
    }
}
