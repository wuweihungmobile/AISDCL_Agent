package com.aisdlc.console.application.service;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 軟刪除專案的清除（契約 §1.6.5，C-3）對真 PostgreSQL 18 的行為。為什麼重要：清除是系統裡唯一不可逆的資料操作——
 * 它必須①真的把一個專案底下「每一種參照它的資料」都清乾淨（少一張表就是外鍵違反、清不掉；多清一張就是誤刪），
 * ②只動「已過保留期的軟刪除專案」，不碰保留期內（仍可復原）的專案、也不碰存活專案內單獨軟刪的目標與任務，
 * ③一個專案失敗時整個專案原封不動（不是「刪了一半」）且不影響其他專案。
 */
class SoftDeletePurgeIT extends AbstractApiIT {

    private static final String PROJECTS = "/api/v1/projects";

    @Autowired
    private SoftDeletePurge purge;

    /** 一個專案底下「每一種會參照它的資料」各一筆：外鍵圖上的每一條邊都走到。 */
    private record Tree(String project, String g1, String g2, String t1, String t2, UUID run, UUID importRecord) {
    }

    private Tree fullTree(String name) {
        String project = createProject(name);
        String g1 = createGoal(project, "G1");
        String g2 = createGoal(project, "G2", g1);
        String t1 = createTask(g1, "T1");
        String t2 = createTask(g2, "T2");
        UUID p = UUID.fromString(project);
        UUID run = UUID.randomUUID();
        UUID step = UUID.randomUUID();
        UUID importRecord = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) "
                + "values (?, ?, 1, 'COMPLETED', 3, '{}'::jsonb)", run, p);
        jdbc.update("insert into console.execution_steps (id, run_id, task_id, step_number, action, status) "
                + "values (?, ?, ?, 1, 'run', 'COMPLETED')", step, run, UUID.fromString(t1));
        jdbc.update("insert into console.checkpoints (run_id, name, state_snapshot) values (?, 'cp', '{}'::jsonb)", run);
        jdbc.update("insert into console.run_token_samples (run_id, seq, ts, tokens_used, delta, task_id) "
                + "values (?, 1, now(), 100, 100, ?)", run, UUID.fromString(t1));
        jdbc.update("insert into console.alerts (project_id, run_id, rule, severity, subject, message) "
                + "values (?, ?, 'HIGH_RETRY_RATE', 'WARNING', 'run:x', 'm')", p, run);
        jdbc.update("insert into console.review_requests (run_id, step_id, task_id, goal_id, kind) "
                + "values (?, ?, ?, ?, 'ESCALATED')", run, step, UUID.fromString(t1), UUID.fromString(g1));
        jdbc.update("insert into console.import_records (id, source_type, source_content, project_id, status) "
                + "values (?, 'MARKDOWN', '# prd', ?, 'IMPORTED')", importRecord, p);
        return new Tree(project, g1, g2, t1, t2, run, importRecord);
    }

    private Tree deletedFullTree(String name, String ago) {
        Tree tree = fullTree(name);
        assertThat(api.delete(operator(), PROJECTS + "/" + tree.project()).status()).isEqualTo(204);
        backdateSoftDeletion(tree.project(), ago);
        return tree;
    }

    private long count(String sql, Object... args) {
        Long n = jdbc.queryForObject(sql, Long.class, args);
        return n == null ? 0 : n;
    }

    /** 這個專案在每一張表裡還剩幾列（import_records 數的是「仍指向它」的列）。 */
    private Map<String, Long> footprint(String project) {
        UUID p = UUID.fromString(project);
        String goalsOf = "(select id from console.goals where project_id = ?)";
        String runsOf = "(select id from console.execution_runs where project_id = ?)";
        Map<String, Long> m = new LinkedHashMap<>();
        m.put("projects", count("select count(*) from console.projects where id = ?", p));
        m.put("goals", count("select count(*) from console.goals where project_id = ?", p));
        m.put("goal_dependencies",
                count("select count(*) from console.goal_dependencies where goal_id in " + goalsOf, p));
        m.put("tasks", count("select count(*) from console.tasks where goal_id in " + goalsOf, p));
        m.put("execution_runs", count("select count(*) from console.execution_runs where project_id = ?", p));
        m.put("execution_steps", count("select count(*) from console.execution_steps where run_id in " + runsOf, p));
        m.put("checkpoints", count("select count(*) from console.checkpoints where run_id in " + runsOf, p));
        m.put("run_token_samples",
                count("select count(*) from console.run_token_samples where run_id in " + runsOf, p));
        m.put("alerts", count("select count(*) from console.alerts where project_id = ?", p));
        m.put("review_requests", count("select count(*) from console.review_requests where run_id in " + runsOf, p));
        m.put("import_records", count("select count(*) from console.import_records where project_id = ?", p));
        return m;
    }

    // ── 預設關閉 ──────────────────────────────────────────────────────────────────────

    @Test
    void thePurgeScheduleIsNotRegisteredInTheRealApplicationByDefault() {
        assertThat(purge.isScheduled()).as("console.retention.purge-enabled 預設 false：應用程式啟動後沒有任何清除排程").isFalse();
        assertThat(purge.start()).isFalse();
    }

    // ── 整棵清掉 ──────────────────────────────────────────────────────────────────────

    @Test
    void anExpiredProjectIsPurgedWithEveryRowThatReferencesItAndTheImportRecordOnlyLosesItsProject() {
        Tree tree = deletedFullTree("purge-all", "31 days");
        assertThat(footprint(tree.project())).as("清除前：每張表各有資料（goal_dependencies 與 goals 各一條邊）")
                .containsExactly(
                        Map.entry("projects", 1L), Map.entry("goals", 2L), Map.entry("goal_dependencies", 1L),
                        Map.entry("tasks", 2L), Map.entry("execution_runs", 1L), Map.entry("execution_steps", 1L),
                        Map.entry("checkpoints", 1L), Map.entry("run_token_samples", 1L), Map.entry("alerts", 1L),
                        Map.entry("review_requests", 1L), Map.entry("import_records", 1L));

        int purged = purge.runOnce();

        assertThat(purged).isEqualTo(1);
        assertThat(footprint(tree.project()).values()).as("整棵消失").containsOnly(0L);
        assertThat(count("select count(*) from console.import_records where id = ?", tree.importRecord()))
                .as("匯入記錄是獨立的歷史，只失去對專案的指向").isEqualTo(1);
        assertThat(jdbc.queryForObject("select project_id from console.import_records where id = ?", UUID.class,
                tree.importRecord())).isNull();
        assertThat(jdbc.queryForObject("select source_content from console.import_records where id = ?", String.class,
                tree.importRecord())).isEqualTo("# prd");

        // 清除後：列表不再有它、復原回 404（與「從未存在」同一個說法）
        assertThat(api.get(operator(), PROJECTS + "?deleted=true").<List<String>>read("$.data.content[*].id"))
                .doesNotContain(tree.project());
        Resp restore = api.post(operator(), PROJECTS + "/" + tree.project() + "/restore");
        assertThat(restore.status()).isEqualTo(404);
        assertThat(restore.<String>read("$.message")).isEqualTo("專案不存在或已清除：" + tree.project());
    }

    @Test
    void thePurgeIsAuditedAsTheSystemWithTheRetentionInTheDetails() {
        Tree tree = deletedFullTree("purge-audit", "40 days");
        jdbc.execute("TRUNCATE console.audit_log");

        assertThat(purge.runOnce()).isEqualTo(1);

        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, "
                + "http_status from console.audit_log");
        assertThat(rows).singleElement().satisfies(r -> assertThat(r)
                .containsEntry("subject", "system").containsEntry("role", null).containsEntry("method", "SYSTEM")
                .containsEntry("path", "system:project.purge").containsEntry("entity_type", "project")
                .containsEntry("entity_id", tree.project()).containsEntry("http_status", 200));
    }

    // ── 只清該清的 ────────────────────────────────────────────────────────────────────

    @Test
    void onlyProjectsPastTheRetentionAreTouchedAndNeitherARestorableProjectNorAGoalDeletedInsideALiveProject() {
        Tree expired = deletedFullTree("past-retention", "30 days 1 minute");
        Tree restorable = deletedFullTree("within-retention", "29 days 23 hours");
        Map<String, Long> restorableBefore = footprint(restorable.project());

        String alive = createProject("alive-project");
        String keptGoal = createGoal(alive, "留下的目標");
        String oldGoal = createGoal(alive, "很久以前單獨刪除的目標");
        String keptTask = createTask(keptGoal, "留下的任務");
        String oldTask = createTask(keptGoal, "很久以前單獨刪除的任務");
        assertThat(api.delete(operator(), "/api/v1/goals/" + oldGoal).status()).isEqualTo(204);
        assertThat(api.delete(operator(), "/api/v1/tasks/" + oldTask).status()).isEqualTo(204);
        jdbc.update("update console.goals set deleted_at = now() - interval '100 days' where id = ?",
                UUID.fromString(oldGoal));
        jdbc.update("update console.tasks set deleted_at = now() - interval '100 days' where id = ?",
                UUID.fromString(oldTask));
        Map<String, Long> aliveBefore = footprint(alive);

        int purged = purge.runOnce();

        assertThat(purged).as("只有逾期的那一個").isEqualTo(1);
        assertThat(footprint(expired.project()).values()).containsOnly(0L);
        assertThat(footprint(restorable.project())).as("保留期內的專案連同整棵子資料原封不動").isEqualTo(restorableBefore);
        assertThat(footprint(alive)).as("存活專案內單獨軟刪的目標與任務（再舊也一樣）不是清除的對象").isEqualTo(aliveBefore);
        assertThat(count("select count(*) from console.goals where id = ? and is_deleted = true",
                UUID.fromString(oldGoal))).isEqualTo(1);
        assertThat(count("select count(*) from console.tasks where id = ? and is_deleted = true",
                UUID.fromString(oldTask))).isEqualTo(1);
        assertThat(count("select count(*) from console.tasks where id = ? and is_deleted = false",
                UUID.fromString(keptTask))).isEqualTo(1);
        assertThat(api.post(operator(), PROJECTS + "/" + restorable.project() + "/restore").status())
                .as("清除與復原視窗是同一條線：沒被清掉的仍可復原").isEqualTo(200);
    }

    @Test
    void aSecondRoundHasNothingLeftToDo() {
        deletedFullTree("purge-twice", "35 days");

        assertThat(purge.runOnce()).isEqualTo(1);
        assertThat(purge.runOnce()).isZero();
    }

    // ── 單一專案失敗 ──────────────────────────────────────────────────────────────────

    @Test
    void aProjectThatCannotBePurgedIsLeftWhollyIntactAndTheOtherExpiredProjectsAreStillPurged() {
        Tree stuck = deletedFullTree("stuck-project", "45 days");
        Tree fine = deletedFullTree("fine-project", "45 days");
        Map<String, Long> stuckBefore = footprint(stuck.project());
        // 模擬「之後新增了一張參照 goals、清除器還不認得的表」：刪到 goals 那一步會違反外鍵——
        // 此時 review_requests／alerts／checkpoints／token 樣本／步驟／批次／任務都已在同一個交易內刪過，必須全部回滾
        jdbc.execute("create table console.zz_purge_blocker (goal_id uuid not null references console.goals(id))");
        try {
            jdbc.update("insert into console.zz_purge_blocker (goal_id) values (?)", UUID.fromString(stuck.g1()));

            int purged = purge.runOnce();

            assertThat(purged).as("卡住的不算，另一個照清").isEqualTo(1);
            assertThat(footprint(stuck.project())).as("整個專案原封不動，不是刪了一半").isEqualTo(stuckBefore);
            assertThat(count("select count(*) from console.projects where id = ? and is_deleted = true",
                    UUID.fromString(stuck.project()))).isEqualTo(1);
            assertThat(footprint(fine.project()).values()).containsOnly(0L);
            assertThat(count("select count(*) from console.audit_log where method = 'SYSTEM' and entity_id = ?",
                    stuck.project())).as("沒清掉就不留「已清除」的審計").isZero();
            assertThat(count("select count(*) from console.audit_log where method = 'SYSTEM' and entity_id = ?",
                    fine.project())).isEqualTo(1);
        } finally {
            jdbc.execute("drop table if exists console.zz_purge_blocker");
        }
    }
}
