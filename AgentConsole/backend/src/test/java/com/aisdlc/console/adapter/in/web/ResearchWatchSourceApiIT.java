package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniResearch.Reply;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.http.HttpMethod;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 追蹤來源 console-api 端點 API-RP-29（TCS-ResearchRegistry AT-965-5-1～5-4、5-6；契約 §5A.2），對真的 HTTP 迷你 Bridge 與真 PostgreSQL 驗每一列。
 * 為什麼重要：追蹤來源決定自我進化去抓什麼——角色矩陣若有洞，OPERATOR 就能改掉掌舵者的來源清單；輸入閘若在 Bridge 之後，明知會被拒的本文會白白打到 Bridge；
 * 操作人若可由本文指定，稽核就不再可信。console-api 對 {@code console.research_watch_sources} 零寫入，所以這裡也驗「表不動」。
 */
@ExtendWith(OutputCaptureExtension.class)
class ResearchWatchSourceApiIT extends AbstractResearchIT {

    private static final String WATCH = RESEARCH + "/watch-sources";
    private static final String UNIT = "t-unit";

    private static Map<String, Object> body(String slug) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("slug", slug);
        body.put("url", "https://www.anthropic.com/news");
        body.put("kind", "blog");
        body.put("extract", "最新 3 篇標題");
        body.put("layer", "INDUSTRY");
        body.put("expand", map("mode", "links", "prefix", "/news/", "max", 2));
        return body;
    }

    private static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    private long watchCalls() {
        return MINI.research.calls.stream().filter(c -> c.path().startsWith("/research/watch-sources") && !"GET".equals(c.method())).count();
    }

    private List<Map<String, Object>> auditRows() {
        return jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, http_status, trace_id from console.audit_log order by occurred_at, id");
    }

    // ── AT-965-5-1 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_5_1_onlyAdminCanWriteAndEveryoneCanReadAndDeniedCallsReachNeitherTheBridgeNorTheTable() {
        long tableBefore = rows("research_watch_sources");
        assertThat(tableBefore).as("V24 種子 17 列").isEqualTo(17);
        for (String path : List.of(WATCH, WATCH + "/t-x")) {
            assertThat(api.get(null, path).status()).as("匿名 GET " + path).isEqualTo(401);
        }
        assertThat(api.post(null, WATCH, body(UNIT)).status()).isEqualTo(401);
        assertThat(api.raw(null, HttpMethod.PATCH, WATCH + "/t-x", ApiClient.toJson(map("enabled", false))).status()).isEqualTo(401);
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(api.get(token, WATCH).status()).as("GET 三角色皆 200").isEqualTo(200);
        }
        for (String token : List.of(viewer(), operator())) {
            Resp post = api.post(token, WATCH, body(UNIT));
            assertThat(post.status()).isEqualTo(403);
            assertThat(post.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
            Resp patch = api.raw(token, HttpMethod.PATCH, WATCH + "/t-x", ApiClient.toJson(map("enabled", false)));
            assertThat(patch.status()).isEqualTo(403);
            assertThat(patch.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        }
        assertThat(watchCalls()).as("迷你 Bridge 的 watch 寫入請求數為 0").isZero();
        assertThat(rows("research_watch_sources")).as("console-api 零寫入：表不動").isEqualTo(tableBefore);
        Resp created = api.post(admin(), WATCH, body(UNIT));
        assertThat(created.status()).as("ADMIN 通過授權層").isEqualTo(201);
        Resp patched = api.raw(admin(), HttpMethod.PATCH, WATCH + "/" + UNIT, ApiClient.toJson(map("enabled", false)));
        assertThat(patched.status()).isEqualTo(200);
        assertThat(rows("research_watch_sources")).as("成功之後 console-api 仍不寫表（迷你 Bridge 才是寫入者）").isEqualTo(tableBefore);

        String config = readSecurityConfig();
        int generic = config.indexOf("requestMatchers(\"/api/v1/**\").hasAnyRole(\"OPERATOR\", \"ADMIN\")");
        assertThat(generic).isPositive();
        for (String matcher : List.of("requestMatchers(HttpMethod.POST, \"/api/v1/research/watch-sources\").hasRole(\"ADMIN\")",
                "requestMatchers(HttpMethod.PATCH, \"/api/v1/research/watch-sources/*\").hasRole(\"ADMIN\")")) {
            int index = config.indexOf(matcher);
            assertThat(index).as("存在：%s", matcher).isPositive();
            assertThat(index).as("置於通用 /api/v1/** 規則之前（先中者定案）").isLessThan(generic);
        }
    }

    private static String readSecurityConfig() {
        try {
            return Files.readString(Path.of("src", "main", "java", "com", "aisdlc", "console", "infrastructure", "config", "SecurityConfig.java"), StandardCharsets.UTF_8);
        } catch (java.io.IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    // ── AT-965-5-2 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_5_2_everyAdminWriteLeavesOneAuditRowForTheSlugAndNeverTouchesTheEventLedger(CapturedOutput output) {
        long audits = rows("audit_log");
        long events = rows("research_events");

        Resp created = api.post(adminAs("alice"), WATCH, body(UNIT));
        assertThat(created.status()).isEqualTo(201);
        assertThat(rows("audit_log")).isEqualTo(audits + 1);
        Map<String, Object> row = auditRows().get(auditRows().size() - 1);
        assertThat(row).containsEntry("entity_type", "research_watch_source").containsEntry("entity_id", UNIT).containsEntry("subject", "alice")
                .containsEntry("role", "ADMIN").containsEntry("http_status", 201).containsEntry("method", "POST");
        assertThat((String) row.get("trace_id")).isNotBlank();
        assertThat(output.getAll().lines().filter(l -> l.contains("{\"event\":\"audit\"") && l.contains("research.watch_source"))
                .map(l -> l.substring(l.indexOf("{\"event\":\"audit\""))).toList())
                .anySatisfy(line -> {
                    assertThat(JsonPath.<String>read(line, "$.action")).isEqualTo("research.watch_source");
                    assertThat(JsonPath.<String>read(line, "$.entity")).isEqualTo("research_watch_source:" + UNIT);
                });
        assertThat(MINI.research.lastCall().body()).as("轉給 Bridge 的 added_by 取 JWT subject").containsEntry("added_by", "alice");

        Resp off = api.raw(adminAs("alice"), HttpMethod.PATCH, WATCH + "/" + UNIT, ApiClient.toJson(map("enabled", false)));
        assertThat(off.status()).isEqualTo(200);
        assertThat(rows("audit_log")).isEqualTo(audits + 2);
        assertThat(auditRows().get(auditRows().size() - 1)).containsEntry("entity_type", "research_watch_source").containsEntry("entity_id", UNIT)
                .containsEntry("http_status", 200).containsEntry("method", "PATCH");
        assertThat(MINI.research.lastCall().body()).containsEntry("disabled_by", "alice").containsEntry("enabled", false);

        MINI.research.next("watch.add", Reply.error(422, "host_not_allowed", "details", map("host", "unknown.example.com")));
        Resp refused = api.post(admin(), WATCH, body("t-unit-2"));
        assertThat(refused.status()).isEqualTo(422);
        assertThat(rows("audit_log")).as("被拒的 422 也多恰一列").isEqualTo(audits + 3);
        assertThat(auditRows().get(auditRows().size() - 1)).containsEntry("http_status", 422);
        Resp forbidden = api.post(operator(), WATCH, body("t-unit-3"));
        assertThat(forbidden.status()).isEqualTo(403);
        assertThat(rows("audit_log")).as("403 也多恰一列").isEqualTo(audits + 4);
        assertThat(auditRows().get(auditRows().size() - 1)).containsEntry("http_status", 403).containsEntry("role", "OPERATOR");
        assertThat(rows("research_events")).as("追蹤來源是全域資源：事件帳不變").isEqualTo(events);
    }

    // ── AT-965-5-3 ───────────────────────────────────────────────────────────────────────────

    private record Bad(String label, Map<String, Object> body, String field, String rule) {
    }

    @Test
    void AT_965_5_3_theInputGateRejectsEveryViolationWith400BeforeTheBridgeAndUnknownKeysAreNotIgnored() {
        List<Bad> cases = new ArrayList<>();
        cases.add(new Bad("slug 33 字元", with(body(UNIT), "slug", "a".repeat(33)), "slug", "invalid_slug"));
        cases.add(new Bad("url 非 https", with(body(UNIT), "url", "http://www.anthropic.com/x"), "url", "invalid_url"));
        cases.add(new Bad("url 大寫 host", with(body(UNIT), "url", "https://EXAMPLE.org/x"), "url", "invalid_url"));
        cases.add(new Bad("url 顯式 443", with(body(UNIT), "url", "https://example.org:443/x"), "url", "invalid_url"));
        cases.add(new Bad("url IP 字面", with(body(UNIT), "url", "https://93.184.216.34/x"), "url", "invalid_url"));
        cases.add(new Bad("kind 列舉外", with(body(UNIT), "kind", "rss"), "kind", "invalid_kind"));
        cases.add(new Bad("layer 列舉外", with(body(UNIT), "layer", "X"), "layer", "invalid_layer"));
        cases.add(new Bad("extract 空", with(body(UNIT), "extract", ""), "extract", "invalid_extract"));
        cases.add(new Bad("extract 201 字", with(body(UNIT), "extract", "字".repeat(201)), "extract", "invalid_extract"));
        cases.add(new Bad("expand 缺 max", with(body(UNIT), "expand", map("mode", "links", "prefix", "/a/")), "expand", "invalid_expand"));
        cases.add(new Bad("expand.max 為 4", with(body(UNIT), "expand", map("mode", "links", "prefix", "/a/", "max", 4)), "expand", "invalid_expand"));
        cases.add(new Bad("expand.prefix 無前導斜線", with(body(UNIT), "expand", map("mode", "links", "prefix", "a/", "max", 1)), "expand", "invalid_expand"));
        cases.add(new Bad("本文含 addedBy", with(body(UNIT), "addedBy", "evil"), "addedBy", "unknown_field"));
        for (Bad bad : cases) {
            Resp resp = api.post(admin(), WATCH, bad.body());
            assertThat(resp.status()).as(bad.label()).isEqualTo(400);
            assertThat(resp.<List<String>>read("$.errors[*].field")).as("%s：errors[] 逐欄", bad.label()).contains(bad.field());
            assertThat(resp.<List<String>>read("$.details.violations[*].rule")).as("%s：rule", bad.label()).contains(bad.rule());
        }
        Resp everything = api.post(admin(), WATCH, map("slug", "-Bad", "url", "http://x", "kind", "rss", "extract", "", "layer", "X", "expand", map("mode", "x")));
        assertThat(everything.status()).isEqualTo(400);
        assertThat(everything.<List<String>>read("$.details.violations[*].rule")).as("一次全列").containsExactlyInAnyOrder("invalid_slug", "invalid_url", "invalid_kind",
                "invalid_layer", "invalid_extract", "invalid_expand");
        Resp array = api.raw(admin(), HttpMethod.POST, WATCH, "[1,2]");
        assertThat(array.status()).as("本文非物件").isEqualTo(400);
        assertThat(watchCalls()).as("迷你 Bridge 的 watch 寫入請求數為 0").isZero();
        assertThat(MINI.research.calls).as("輸入閘先於 Bridge：一個請求都沒有").isEmpty();
    }

    private static Map<String, Object> with(Map<String, Object> source, String key, Object value) {
        Map<String, Object> out = new LinkedHashMap<>(source);
        out.put(key, value);
        return out;
    }

    // ── AT-965-5-4 ───────────────────────────────────────────────────────────────────────────

    private record Relay(String label, Reply reply, int status, String reason) {
    }

    @Test
    void AT_965_5_4_bridgeErrorsAreRelayedVerbatimAndPostIsNeverRetried() {
        List<Relay> relays = List.of(
                new Relay("409", Reply.error(409, "watch_source_exists", "details", map("slug", UNIT)), 409, ErrorReasons.REGISTRY_WATCH_SOURCE_EXISTS),
                new Relay("422 host", Reply.error(422, "host_not_allowed", "details", map("host", "x.example.com")), 422, ErrorReasons.REGISTRY_HOST_NOT_ALLOWED),
                new Relay("422 too large", Reply.error(422, "registry_too_large", "details", map("what", "registry_text", "limit", 24576, "size", 24577)), 422,
                        ErrorReasons.REGISTRY_TOO_LARGE),
                new Relay("422 invalid", Reply.error(422, "invalid_request", "violations", List.of(map("field", "url", "rule", "invalid_url", "message", "不合"))), 422,
                        "invalid_request"),
                new Relay("404", Reply.error(404, "research_not_found", "details", map("slug", UNIT)), 404, ErrorReasons.RESEARCH_NOT_FOUND),
                new Relay("503", Reply.error(503, "research_requires_db"), 503, "research_requires_db"),
                new Relay("403", Reply.error(403, "research_write_forbidden"), 403, ErrorReasons.RESEARCH_WRITE_FORBIDDEN));
        for (Relay relay : relays) {
            MINI.research.reset();
            MINI.research.next("watch.add", relay.reply());
            Resp resp = api.post(admin(), WATCH, body(UNIT));
            assertThat(resp.status()).as(relay.label()).isEqualTo(relay.status());
            assertThat(resp.<String>read("$.reason")).as("%s：reason 逐字", relay.label()).isEqualTo(relay.reason());
            assertThat(MINI.research.countCalls("POST", "/research/watch-sources")).as("%s：POST 不重試（恰 1）", relay.label()).isEqualTo(1);
            if (relay.label().equals("409") || relay.label().equals("404")) {
                assertThat(resp.<String>read("$.details.slug")).isEqualTo(UNIT);
            }
            if (relay.label().equals("422 host")) {
                assertThat(resp.<String>read("$.details.host")).isEqualTo("x.example.com");
            }
            if (relay.label().equals("422 too large")) {
                assertThat(resp.<String>read("$.details.what")).isEqualTo("registry_text");
                assertThat(resp.<Integer>read("$.details.limit")).isEqualTo(24576);
            }
        }
        MINI.research.reset();
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp down = api.post(admin(), WATCH, body(UNIT));
        assertThat(down.status()).isEqualTo(502);
        assertThat(down.<String>read("$.reason")).isEqualTo("bridge_unreachable");
        resetSystemConfigs();
        readTimeout.cap(Duration.ofMillis(400));
        MINI.research.delayMillis = 2_500;
        Resp slow = api.post(admin(), WATCH, body(UNIT));
        assertThat(slow.status()).isEqualTo(504);
        assertThat(slow.<String>read("$.reason")).isEqualTo("bridge_timeout");
        assertThat(MINI.research.countCalls("POST", "/research/watch-sources")).as("逾時也只送一次").isEqualTo(1);
        assertThat(List.of(ErrorReasons.REGISTRY_WATCH_SOURCE_EXISTS, ErrorReasons.REGISTRY_HOST_NOT_ALLOWED, ErrorReasons.REGISTRY_TOO_LARGE))
                .as("reason 字串住 REGISTRY_ 常數家族").containsExactly("watch_source_exists", "host_not_allowed", "registry_too_large");
    }

    // ── AT-965-5-6 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_5_6_openApiDocumentsTheThreeOperationsTheirDtoAndTheirFailureCodes() {
        Resp docs = api.get(viewer(), "/v3/api-docs");
        assertThat(docs.status()).isEqualTo(200);
        assertThat(docs.<String>read("$.paths['/api/v1/research/watch-sources'].get.operationId")).isEqualTo("listResearchWatchSources");
        assertThat(docs.<String>read("$.paths['/api/v1/research/watch-sources'].post.operationId")).isEqualTo("addResearchWatchSource");
        assertThat(docs.<String>read("$.paths['/api/v1/research/watch-sources/{slug}'].patch.operationId")).isEqualTo("updateResearchWatchSource");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/research/watch-sources']").keySet()).containsExactlyInAnyOrder("get", "post");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/research/watch-sources/{slug}']").keySet()).containsExactly("patch");
        List<String> required = docs.read("$.components.schemas.WatchSourceDto.required");
        assertThat(required).contains("slug", "url", "host", "kind", "extract", "layer", "expand", "enabled", "hostAllowed", "addedBy", "addedAt", "disabledBy", "disabledAt");
        Map<String, Object> properties = docs.read("$.components.schemas.WatchSourceDto.properties");
        assertThat(properties.keySet()).as("camelCase 欄名").doesNotContain("host_allowed", "added_by", "disabled_by");
        Map<String, List<String>> expected = Map.of(
                "$.paths['/api/v1/research/watch-sources'].post.responses", List.of("201", "400", "401", "403", "409", "422", "429", "502", "503", "504"),
                "$.paths['/api/v1/research/watch-sources/{slug}'].patch.responses", List.of("200", "400", "401", "403", "404", "422", "429", "502", "503", "504"),
                "$.paths['/api/v1/research/watch-sources'].get.responses", List.of("200", "401", "429", "502", "503", "504"));
        expected.forEach((path, codes) -> {
            Map<String, Map<String, Object>> responses = docs.read(path);
            assertThat(responses.keySet()).as(path).containsExactlyInAnyOrderElementsOf(codes);
            responses.forEach((code, response) -> assertThat(String.valueOf(response.get("description"))).as("%s %s 說明非空", path, code).isNotBlank());
        });
    }
}
