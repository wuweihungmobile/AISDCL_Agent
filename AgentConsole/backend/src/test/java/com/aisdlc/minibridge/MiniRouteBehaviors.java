package com.aisdlc.minibridge;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static com.aisdlc.minibridge.MiniBridge.map;

/**
 * 迷你 Bridge 的 P1 預設行為（分流、SCR、拆解；形狀照真 Bridge 的 {@code routers/research_route.py} 與 IFACE §1）。迷你 Bridge 自己是 Bridge——<b>研究表的唯一寫入者</b>：
 * 預設的 {@code :route} 把成功的分流列、步驟與游標直接寫進同一顆資料庫（含回填 {@code research_projects.console_project_id}），console-api 之後讀得到。測試以
 * {@link MiniResearch#next}／{@link MiniResearch#always}（路由鍵＝動詞：{@code route-preview}、{@code route}、{@code route-compensated}、{@code scr}、{@code scr-apply}、
 * {@code decompose}、{@code decomposition-signoff}）覆寫成腳本回應。
 */
final class MiniRouteBehaviors {

    private MiniRouteBehaviors() {
    }

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }

    private static Map<String, Object> row(MiniResearch research, UUID id) {
        return research.jdbc().queryForMap("select slug, rp_no, target_scope from console.research_projects where id = ?", id);
    }

    /** 預演：回 200 的動作清單；內環鍵＝軌道 A 的 {@code <module>-<slug>}、軌道 B 的 {@code project_name}；執行路徑預設 {@code /e2e/route/<內環鍵>}。 */
    static MiniResearch.Reply preview(MiniResearch research, UUID id, Map<String, Object> body) {
        Map<String, Object> project = row(research, id);
        String track = text(body.get("track"));
        String impl = "A".equals(track) ? text(body.getOrDefault("target_module", "monorepo")) + "-" + project.get("slug") : text(body.get("project_name"));
        String executionPath = research.executionPathOverride != null ? research.executionPathOverride : "/e2e/route/" + impl;
        List<Map<String, Object>> actions = new ArrayList<>();
        actions.add(map("seq", 1, "action", "validate_target", "step", "VALIDATE_TARGET", "target", executionPath, "touches_external", false, "detail", "驗證目標"));
        actions.add(map("seq", 2, "action", "A".equals(track) ? "worktree_add" : "scaffold_render", "step", "A".equals(track) ? "GIT_SWITCH" : "SCAFFOLD_FILES",
                "target", executionPath, "touches_external", false, "detail", "建立目標"));
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("research_id", id.toString());
        out.put("track", track);
        out.put("prd", map("version_no", 1, "semver", "v1.0.0", "sha256", "a".repeat(64), "target_scope", project.get("target_scope"), "scope_differs", false));
        out.put("scope_differs", false);
        out.put("impl_fsm_project", impl);
        out.put("impl_state_dir", executionPath + "/build/reports/fsm");
        out.put("execution_path", executionPath);
        out.put("actions", actions);
        out.put("expected_tracked_files", "B".equals(track) ? List.of("README.md") : List.of());
        out.put("warnings", List.of());
        return new MiniResearch.Reply(200, out);
    }

    /** 確認：把成功的分流列、步驟與游標寫進資料庫（測試掛的鉤子在控制器收到請求的當下已呼叫，腳本回應與預設行為皆然）。 */
    static MiniResearch.Reply route(MiniResearch research, UUID id, Map<String, Object> body) {
        String track = text(body.get("track"));
        String impl = "A".equals(track) ? text(body.getOrDefault("target_module", "monorepo")) + "-" + row(research, id).get("slug") : text(body.get("project_name"));
        String path = research.executionPathOverride != null ? research.executionPathOverride : "/e2e/route/" + impl;
        UUID routeId = UUID.randomUUID();
        UUID consoleProject = UUID.fromString(text(body.get("console_project_id")));
        research.jdbc().update("insert into console.research_route_decisions (id, research_id, track, target_kind, target_module, target_path, git_branch, base_ref, "
                + "console_project_id, impl_fsm_project, impl_state_dir, published_docs, status, decided_by, finished_at) "
                + "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{\"docs/01_requirements/X_PRD.md\":\"" + "b".repeat(64) + "\"}'::jsonb, 'SUCCEEDED', ?, now())",
                routeId, id, track, "A".equals(track) ? "MODULE" : "STANDALONE", "A".equals(track) ? body.getOrDefault("target_module", "monorepo") : null, path,
                "A".equals(track) ? "feature/issue-0001" : null, "A".equals(track) ? "main" : null, consoleProject, impl, path + "/build/reports/fsm",
                text(body.get("approver")));
        research.jdbc().update("insert into console.research_route_steps (route_id, step_no, step, status, finished_at) values (?, 1, 'VALIDATE_TARGET', 'OK', now())", routeId);
        research.jdbc().update("update console.research_projects set console_project_id = ?, flow_step = 'build', flow_phase = 'ROUTED', flow_status = 'IDLE', flow_detail = '' "
                + "where id = ?", consoleProject, id);
        return new MiniResearch.Reply(200, map("route_id", routeId.toString(), "status", "SUCCEEDED", "steps", List.of(map("step_no", 1, "step", "VALIDATE_TARGET", "status", "OK")),
                "impl_fsm_project", impl, "impl_state_dir", path + "/build/reports/fsm", "published_docs", map("docs/01_requirements/X_PRD.md", "b".repeat(64)),
                "flow", map("step", "build", "phase", "ROUTED", "status", "IDLE", "detail", "")));
    }

    /** 補償通知：該列為 FAILED 才改 COMPENSATED，否則 409 {@code route_conflict}（{@code details.status}）；無此列 404。 */
    static MiniResearch.Reply compensated(MiniResearch research, UUID id, Map<String, Object> body) {
        UUID routeId = UUID.fromString(text(body.get("route_id")));
        List<String> statuses = research.jdbc().queryForList("select status from console.research_route_decisions where id = ? and research_id = ?", String.class, routeId, id);
        if (statuses.isEmpty()) {
            return MiniResearch.Reply.error(404, "research_not_found", "route_id", routeId.toString());
        }
        if (!"FAILED".equals(statuses.get(0))) {
            return MiniResearch.Reply.error(409, "route_conflict", "details", map("status", statuses.get(0)));
        }
        research.jdbc().update("update console.research_route_decisions set status = 'COMPENSATED' where id = ?", routeId);
        return new MiniResearch.Reply(200, map("route_id", routeId.toString(), "status", "COMPENSATED"));
    }

    /** 發起 SCR：MINOR／MAJOR 202、HEALING_FAILED 200（帶恢復指令）；同研究專案 MINOR 已有 2 筆有效者第 3 次 409 {@code scr_limit}。 */
    static MiniResearch.Reply scr(MiniResearch research, UUID id, Map<String, Object> body) {
        String kind = text(body.get("kind"));
        String source = text(body.get("source_kind"));
        Integer next = research.jdbc().queryForObject("select coalesce(max(scr_no), 0) + 1 from console.research_scr where research_id = ?", Integer.class, id);
        int scrNo = next == null ? 1 : next;
        if ("MINOR".equals(kind)) {
            Integer active = research.jdbc().queryForObject("select count(*) from console.research_scr where research_id = ? and kind = 'MINOR' "
                    + "and status in ('OPEN','APPROVED','APPLIED')", Integer.class, id);
            if (active != null && active >= 2) {
                return MiniResearch.Reply.error(409, "scr_limit", "details", map("limit", 2));
            }
        }
        if ("HEALING_FAILED".equals(source)) {
            return new MiniResearch.Reply(200, map("scr_no", scrNo, "recovery", map("target", "SPEC_DRAFTING", "powershell", "Push-Location x; Pop-Location", "posix", "echo x")));
        }
        research.jdbc().update("insert into console.research_scr (research_id, scr_no, kind, source_kind, reason, reason_class, requested_by) values (?, ?, ?, ?, ?, ?, ?)",
                id, scrNo, kind, source, text(body.get("reason")), text(body.getOrDefault("reason_class", "OTHER")), text(body.get("requested_by")));
        return "MAJOR".equals(kind) ? new MiniResearch.Reply(202, map("scr_no", scrNo, "successor_research_id", UUID.randomUUID().toString()))
                : new MiniResearch.Reply(202, map("scr_no", scrNo, "status", "OPEN"));
    }

    /** 簽核：把拆解列改為 SIGNED_OFF 並記 import_record_id（D-113：一次寫兩欄）。 */
    static MiniResearch.Reply signoff(MiniResearch research, UUID id, Map<String, Object> body) {
        UUID decomposition = UUID.fromString(text(body.get("decomposition_id")));
        research.jdbc().update("update console.research_decompositions set status = 'SIGNED_OFF', import_record_id = ?::uuid where id = ? and research_id = ?",
                text(body.get("import_record_id")), decomposition, id);
        return new MiniResearch.Reply(200, map("decomposition_id", decomposition.toString(), "status", "SIGNED_OFF", "artifact_sha256", "c".repeat(64)));
    }
}
