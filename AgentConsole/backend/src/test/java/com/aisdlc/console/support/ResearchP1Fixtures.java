package com.aisdlc.console.support;

import org.springframework.jdbc.core.JdbcTemplate;

import java.util.UUID;

/**
 * P1（分流、SCR、拆解）研究表的資料庫夾具：測試扮演唯一的寫入者 Bridge，直接以 JDBC 寫 V19 的表（console-api 對它們只讀）。清表不用在這裡做：
 * {@code AbstractApiIT} 每個測試前的 {@code TRUNCATE console.projects CASCADE} 沿外鍵一路清到 {@code research_*}。
 */
public final class ResearchP1Fixtures {

    private final JdbcTemplate jdbc;

    public ResearchP1Fixtures(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** 已過 Gate 0、等待分流的研究專案（route／FROZEN／IDLE）；{@code targetScope}＝AISDLC_MODULE｜STANDALONE_PROJECT｜UNDECIDED。 */
    public UUID project(String slug, String targetScope) {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.research_projects (id, slug, title, topic, scope, workspace_path, fsm_project, fsm_state_dir, target_scope, "
                + "flow_step, flow_phase, flow_status, flow_detail, created_by) values (?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, 'route', 'FROZEN', 'IDLE', '', 'operator')",
                id, slug, "研究 " + slug, "議題 " + slug, "{}", "/research-root/" + slug, "research-" + slug, "/research-root/" + slug + "/build/reports/fsm", targetScope);
        return id;
    }

    /** 一筆分流列（軌道 A、monorepo）；{@code consoleProject} 可為 null。 */
    public UUID route(UUID research, String status, UUID consoleProject) {
        UUID id = UUID.randomUUID();
        route(id, research, status, consoleProject);
        return id;
    }

    public void route(UUID id, UUID research, String status, UUID consoleProject) {
        jdbc.update("insert into console.research_route_decisions (id, research_id, track, target_kind, target_module, target_path, git_branch, base_ref, "
                + "console_project_id, impl_fsm_project, status, failure_step, decided_by) values (?, ?, 'A', 'MODULE', 'monorepo', '/e2e/fixture', 'feature/issue-0001', 'main', ?, ?, "
                + "?, ?, 'admin')", id, research, consoleProject, "monorepo-fixture", status, "FAILED".equals(status) ? "GIT_SWITCH" : null);
    }

    public void routeStep(UUID route, int stepNo, String step, String status) {
        jdbc.update("insert into console.research_route_steps (route_id, step_no, step, status, argv_redacted, finished_at) values (?, ?, ?, ?, 'git worktree add', now())",
                route, stepNo, step, status);
    }

    public void scr(UUID research, int scrNo, String kind, String status) {
        jdbc.update("insert into console.research_scr (research_id, scr_no, kind, source_kind, reason, requested_by, status) values (?, ?, ?, 'HUMAN', '夾具理由', 'operator', ?)",
                research, scrNo, kind, status);
    }

    /** 一筆拆解列與它對應的 TASK_DECOMPOSITION 產物新版本（內容為 JSON 全文）。回拆解列 id。 */
    public UUID decomposition(UUID research, String status, String prdSha256, String contentJson) {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.research_decompositions (id, research_id, path, prd_sha256, tasks_count, status, created_by) values (?, ?, 'C', ?, ?, ?, 'operator')",
                id, research, prdSha256, 1, status);
        Integer next = jdbc.queryForObject("select coalesce(max(version), 0) + 1 from console.research_artifacts where research_id = ? and kind = 'TASK_DECOMPOSITION'",
                Integer.class, research);
        jdbc.update("insert into console.research_artifacts (research_id, kind, version, rel_path, sha256, bytes, origin, content, created_by) "
                + "values (?, 'TASK_DECOMPOSITION', ?, '03_execution/task_decomposition.json', ?, ?, 'AGENT', ?, 'bridge')", research, next,
                ResearchFixtures.sha256(contentJson), contentJson.getBytes(java.nio.charset.StandardCharsets.UTF_8).length, contentJson);
        return id;
    }

    /** 綁定 Console 專案（Bridge 在分流成功時回填；受控更新守衛放行 console_project_id）。 */
    public void bind(UUID research, UUID consoleProject) {
        jdbc.update("update console.research_projects set console_project_id = ? where id = ?", consoleProject, research);
    }

    /** 拆解內容：兩個 AC、兩個 task，task 1 涵蓋 AC-001-1、AC-001-2；{@code uncovered} 清單由呼叫端決定。 */
    public static String content(String prdSha256, String uncoveredJson, int total, int covered) {
        return "{\"schema_rev\":1,\"prd_sha256\":\"" + prdSha256 + "\",\"coverage\":{\"total\":" + total + ",\"covered\":" + covered + ",\"uncovered\":" + uncoveredJson + "},"
                + "\"goals\":[{\"goal_id\":\"G-1\",\"name\":\"目標一\",\"pass_criteria\":\"目標一完成\",\"depends_on\":[],\"tasks\":["
                + "{\"task_id\":\"T-1\",\"name\":\"任務一\",\"prompt\":\"實作任務一\",\"covers_us\":[\"US-001\"],\"covers_ac\":[\"AC-001-1\"],\"evaluator_command\":null,\"estimated_tokens\":null},"
                + "{\"task_id\":\"T-2\",\"name\":\"任務二\",\"prompt\":\"實作任務二\",\"covers_us\":[\"US-001\"],\"covers_ac\":[\"AC-001-2\"],\"evaluator_command\":null,\"estimated_tokens\":null}]}],"
                + "\"waivers\":[]}";
    }
}
