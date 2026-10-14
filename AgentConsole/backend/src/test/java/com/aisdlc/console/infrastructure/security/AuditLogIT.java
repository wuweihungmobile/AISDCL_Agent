package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** NFR-9.2-07：每次寫入操作輸出結構化 JSON 審計日誌（subject、method、path、目標 id、status、traceId）。 */
@ExtendWith(OutputCaptureExtension.class)
class AuditLogIT extends AbstractApiIT {

    private static List<String> auditLines(CapturedOutput output) {
        return output.getAll().lines().filter(line -> line.contains("{\"event\":\"audit\"")).map(line ->
                line.substring(line.indexOf("{\"event\":\"audit\""))).toList();
    }

    @Test
    void aWriteProducesOneJsonAuditLineWithSubjectMethodPathTargetStatusAndTraceId(CapturedOutput output) {
        String project = createProject("Audited");
        int before = auditLines(output).size();

        Resp resp = api.put(operator(), "/api/v1/projects/" + project, Map.of("name", "Audited v2"));

        List<String> lines = auditLines(output);
        assertThat(lines).hasSize(before + 1);
        String json = lines.get(lines.size() - 1);
        assertThat(JsonPath.<String>read(json, "$.event")).isEqualTo("audit");
        assertThat(JsonPath.<String>read(json, "$.subject")).isEqualTo("operator");
        assertThat(JsonPath.<String>read(json, "$.method")).isEqualTo("PUT");
        assertThat(JsonPath.<String>read(json, "$.path")).isEqualTo("/api/v1/projects/" + project);
        assertThat(JsonPath.<String>read(json, "$.targetId")).isEqualTo(project);
        assertThat(JsonPath.<Integer>read(json, "$.status")).isEqualTo(200);
        assertThat(JsonPath.<String>read(json, "$.traceId")).isEqualTo(resp.header("X-Trace-Id"));
    }

    @Test
    void readsAreNotAudited(CapturedOutput output) {
        int before = auditLines(output).size();
        api.get(admin(), "/api/v1/projects");
        assertThat(auditLines(output)).hasSize(before);
    }

    @Test
    void rejectedWritesAreAuditedToo(CapturedOutput output) {
        String project = createProject("Denied");
        int before = auditLines(output).size();

        api.delete(viewer(), "/api/v1/projects/" + project);
        api.delete(null, "/api/v1/projects/" + project);

        List<String> lines = auditLines(output);
        assertThat(lines).hasSize(before + 2);
        assertThat(JsonPath.<String>read(lines.get(lines.size() - 2), "$.subject")).isEqualTo("viewer");
        assertThat(JsonPath.<Integer>read(lines.get(lines.size() - 2), "$.status")).isEqualTo(403);
        assertThat(JsonPath.<Object>read(lines.get(lines.size() - 1), "$.subject")).isNull();
        assertThat(JsonPath.<Integer>read(lines.get(lines.size() - 1), "$.status")).isEqualTo(401);
    }

    @Test
    void requestBodiesNeverReachTheAuditLog(CapturedOutput output) {
        api.post(null, "/api/v1/auth/login", Map.of("username", "admin", "password", "Super-Secret-Pa55word!"));
        assertThat(output.getAll()).doesNotContain("Super-Secret-Pa55word!");
        assertThat(auditLines(output)).anySatisfy(line ->
                assertThat(JsonPath.<String>read(line, "$.path")).isEqualTo("/api/v1/auth/login"));
    }
}
