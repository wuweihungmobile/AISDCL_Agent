package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 寫入端點審計落庫（NFR-9.2-07；V6 {@code audit_log}）。為什麼重要：審計表是「誰在什麼時候對什麼做了什麼」的事後證據——
 * 讀取不能灌進去（表會被輪詢塞爆）、被拒絕的寫入要留下（探測行為的線索）、query string（可能含 access_token）與請求本文
 * （可能含密碼、金鑰）絕不能落庫、審計寫入失敗絕不能讓主請求跟著失敗。
 */
@ExtendWith(OutputCaptureExtension.class)
class AuditPersistenceApiIT extends AbstractApiIT {

    private List<Map<String, Object>> rows(String where, Object... args) {
        return jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, http_status, trace_id "
                + "from console.audit_log where " + where + " order by occurred_at", args);
    }

    private int totalRows() {
        return jdbc.queryForObject("select count(*) from console.audit_log", Integer.class);
    }

    @Test
    void everyWriteMethodUnderApiLeavesExactlyOneRowAndReadsLeaveNone() {
        String project = createProject("審計專案");
        String goal = createGoal(project, "G");
        jdbc.execute("TRUNCATE console.audit_log");

        api.get(viewer(), "/api/v1/projects");
        api.get(viewer(), "/api/v1/projects/" + project);
        assertThat(totalRows()).as("讀取不審計").isZero();

        assertThat(api.post(operator(), "/api/v1/goals/" + goal + "/tasks",
                Map.of("name", "T", "passCriteria", "c")).status()).isEqualTo(201);
        assertThat(api.put(operator(), "/api/v1/projects/" + project, Map.of("name", "改名")).status()).isEqualTo(200);
        assertThat(api.delete(operator(), "/api/v1/goals/" + goal).status()).isEqualTo(204);

        assertThat(rows("true")).extracting(r -> r.get("method")).containsExactly("POST", "PUT", "DELETE");
        assertThat(rows("true")).extracting(r -> r.get("http_status")).containsExactly(201, 200, 204);
        assertThat(rows("true")).extracting(r -> r.get("subject")).containsOnly("operator");
        assertThat(rows("true")).extracting(r -> r.get("role")).containsOnly("OPERATOR");
    }

    @Test
    void theEntityTypeComesFromThePathAndTheEntityIdFromTheFirstUuidInIt() {
        String project = createProject("實體專案");
        jdbc.execute("TRUNCATE console.audit_log");

        api.delete(operator(), "/api/v1/projects/" + project);

        Map<String, Object> row = rows("true").get(0);
        assertThat(row).containsEntry("entity_type", "projects").containsEntry("entity_id", project)
                .containsEntry("path", "/api/v1/projects/" + project);
    }

    @Test
    void aWriteThatTheUseCaseTaggedKeepsTheUseCasesEntityId() {
        jdbc.execute("TRUNCATE console.audit_log");
        Resp created = api.post(operator(), "/api/v1/import/text", Map.of("content", "做一個待辦清單"));

        Map<String, Object> row = rows("path = '/api/v1/import/text'").get(0);
        assertThat(row).containsEntry("entity_type", "import").containsEntry("entity_id", created.id());
    }

    @Test
    void rejectedWritesAreRecordedWithWhoTriedAndAnonymousOnesWithNullSubject() {
        String project = createProject("被拒絕");
        jdbc.execute("TRUNCATE console.audit_log");

        assertThat(api.delete(viewer(), "/api/v1/projects/" + project).status()).isEqualTo(403);
        assertThat(api.delete(null, "/api/v1/projects/" + project).status()).isEqualTo(401);

        List<Map<String, Object>> rows = rows("true");
        assertThat(rows).hasSize(2);
        assertThat(rows.get(0)).containsEntry("subject", "viewer").containsEntry("role", "VIEWER")
                .containsEntry("http_status", 403);
        assertThat(rows.get(1)).containsEntry("subject", null).containsEntry("role", null)
                .containsEntry("http_status", 401);
    }

    @Test
    void aQueryStringNeverReachesTheTable() {
        String project = createProject("含 query");
        jdbc.execute("TRUNCATE console.audit_log");

        api.send(operator(), MockMvcRequestBuilders.put("/api/v1/projects/" + project + "?access_token=SECRET-TOKEN-123")
                .contentType("application/json").content("{\"name\":\"x\"}"));

        assertThat(rows("true")).hasSize(1);
        assertThat(rows("true").get(0)).containsEntry("path", "/api/v1/projects/" + project);
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where path like '%SECRET%' or "
                + "entity_id like '%SECRET%'", Integer.class)).isZero();
    }

    @Test
    void theRowCarriesTheTraceIdOfTheResponse() {
        jdbc.execute("TRUNCATE console.audit_log");

        Resp resp = api.post(operator(), "/api/v1/projects", Map.of("name", "追蹤", "executionPath", "/work/t",
                "passCriteria", "c"));

        assertThat(resp.header("X-Trace-Id")).isNotBlank();
        assertThat(rows("true").get(0)).containsEntry("trace_id", resp.header("X-Trace-Id"));
    }

    @Test
    void aLoginAttemptIsAuditedWithoutItsBody() {
        jdbc.execute("TRUNCATE console.audit_log");

        Resp resp = api.post(null, "/api/v1/auth/login", Map.of("username", "admin", "password", "Wrong-Pa55word!"));

        assertThat(resp.status()).isEqualTo(401);
        List<Map<String, Object>> rows = rows("path = '/api/v1/auth/login'");
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0)).containsEntry("subject", null).containsEntry("http_status", 401);
        assertThat(rows.toString()).doesNotContain("Wrong-Pa55word!");
    }

    @Test
    void aFailingAuditInsertNeverFailsTheRequestAndOnlyLeavesAWarning(CapturedOutput output) {
        String project = createProject("審計失敗");
        jdbc.execute("TRUNCATE console.audit_log");
        // 讓之後的每一次 INSERT 都違反檢查約束（NOT VALID：不檢查既有列）
        jdbc.execute("alter table console.audit_log add constraint zz_block_all check (http_status < 0) not valid");
        try {
            Resp resp = api.put(operator(), "/api/v1/projects/" + project, Map.of("name", "照樣成功"));

            assertThat(resp.status()).as("審計失敗不得影響主請求").isEqualTo(200);
            assertThat(resp.<String>read("$.data.name")).isEqualTo("照樣成功");
            assertThat(totalRows()).isZero();
            assertThat(output.getAll()).contains("審計落庫失敗（不影響主請求）");
        } finally {
            jdbc.execute("alter table console.audit_log drop constraint zz_block_all");
        }

        api.put(operator(), "/api/v1/projects/" + project, Map.of("name", "恢復後"));
        assertThat(totalRows()).as("約束移除後審計恢復").isEqualTo(1);
    }
}
