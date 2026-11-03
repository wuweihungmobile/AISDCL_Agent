package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.SiKeyNames;
import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.BridgeSource;
import com.aisdlc.console.support.ResearchFixtures;
import com.aisdlc.minibridge.MiniResearch;
import com.aisdlc.minibridge.MiniResearch.Call;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 研究面其餘端點的行為整合測試（ResearchToPRD P0；API 契約 §1.1、§0.2）：{@code ResearchApiIT} 釘住 TCS 列出的 AT，本類別補上各端點自己的規格——
 * 來源、證據、PRD 版本、事件分頁等唯讀投影；建立、存檔、啟動階段、退回等寫入的成功路徑、輸入閘與 Bridge 失敗的原樣轉述。
 * 全部走完整 Spring context、真 PostgreSQL 與迷你 Bridge（{@link MiniResearch}）：console-api 對 {@code console.research_*} 零寫入，資料由夾具（扮演 Bridge）寫入。
 */
class ResearchEndpointsIT extends AbstractResearchIT {

    private static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    private Call onlyWriteTo(String method, String pathSuffix) {
        List<Call> matches = bridge().calls.stream().filter(c -> c.method().equals(method) && c.path().endsWith(pathSuffix)).toList();
        assertThat(matches).as("迷你 Bridge 收到的 " + method + " …" + pathSuffix).hasSize(1);
        return matches.get(0);
    }

    // ── 能力探針與 allowlist ─────────────────────────────────────────────────────────────

    @Test
    void capabilitiesAreProjectedToCamelCaseCachedForThirtySecondsAndStillAnswerWhenTheDatabaseIsOff() {
        Resp first = api.get(viewer(), RESEARCH + "/capabilities");

        assertThat(first.status()).isEqualTo(200);
        Map<String, Object> data = first.read("$.data");
        assertThat(data).containsEntry("mode", "local").containsEntry("db", true).containsEntry("researchRoot", MiniResearch.RESEARCH_ROOT)
                .containsEntry("sddRoot", MiniResearch.SDD_ROOT).containsEntry("webLayerEnabled", true).containsEntry("repoWritable", true)
                .containsKey("scaffoldRoot");
        assertThat(data.get("scaffoldRoot")).as("未設定的腳手架根是 null、不是缺鍵").isNull();
        assertThat(first.<Boolean>read("$.data.claudeCli.ok")).isTrue();
        assertThat(first.<String>read("$.data.claudeCli.version")).isEqualTo("2.1.0");
        assertThat(first.<Boolean>read("$.data.ghCli.authenticated")).isFalse();
        assertThat(first.<List<String>>read("$.data.fetchHosts")).containsExactlyElementsOf(MiniResearch.FETCH_HOSTS);

        api.get(operator(), RESEARCH + "/capabilities");
        assertThat(bridge().countCalls("GET", "/research/capabilities")).as("30 秒內第二次讀取走快取，不再問 Bridge").isEqualTo(1);

        researchQuery.invalidateCapabilities();
        bridge().db = false;
        Resp noDb = api.get(viewer(), RESEARCH + "/capabilities");
        assertThat(noDb.status()).as("沒有 DSN 時研究端點一律 503，唯一例外是能力探針：仍 200、以 db=false 說明").isEqualTo(200);
        assertThat(noDb.<Boolean>read("$.data.db")).isFalse();
        assertThat(bridge().countCalls("GET", "/research/capabilities")).isEqualTo(2);
    }

    @Test
    void theFetchHostsFollowTheEffectiveAllowlistSoAnAdminEntryAppearsAndDisappearsWithIt() {
        assertThat(api.get(viewer(), RESEARCH + "/capabilities").<List<String>>read("$.data.fetchHosts")).containsExactlyElementsOf(MiniResearch.FETCH_HOSTS);

        Resp added = api.post(admin(), RESEARCH + "/allowlist", map("listKind", "FETCH", "host", "docs.python.org", "layer", "OSS", "purpose", "官方文件",
                "minIntervalSeconds", 5));
        assertThat(added.status()).isEqualTo(201);
        researchQuery.invalidateCapabilities();
        assertThat(api.get(viewer(), RESEARCH + "/capabilities").<List<String>>read("$.data.fetchHosts")).as("INT-08：新增的 ADMIN 條目進有效清單")
                .containsAll(MiniResearch.FETCH_HOSTS).contains("docs.python.org");

        api.raw(admin(), HttpMethod.PATCH, RESEARCH + "/allowlist/" + added.read("$.data.id"), ApiClient.toJson(map("enabled", false)));
        researchQuery.invalidateCapabilities();
        assertThat(api.get(viewer(), RESEARCH + "/capabilities").<List<String>>read("$.data.fetchHosts")).as("停用即消失")
                .containsExactlyElementsOf(MiniResearch.FETCH_HOSTS);
    }

    @Test
    void anOlderBridgeThatOnlyKnowsRootStillYieldsTheResearchRootAndEveryMissingKeyIsADefaultNotAnError() {
        bridge().next("capabilities", Reply.ok(200, "mode", "local", "root", "/legacy-root", "db", true));

        Resp resp = api.get(viewer(), RESEARCH + "/capabilities");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.researchRoot")).as("research_root 缺席時回退 root").isEqualTo("/legacy-root");
        Map<String, Object> data = resp.read("$.data");
        assertThat(data).as("沒回的鍵：鍵在、值是預設（OpenAPI 的 required＋nullable）").containsKeys("sddRoot", "scaffoldRoot").containsEntry("repoWritable", false)
                .containsEntry("webLayerEnabled", false);
        assertThat(data.get("sddRoot")).isNull();
        assertThat(resp.<List<String>>read("$.data.fetchHosts")).isEmpty();
    }

    @Test
    void aFailedCapabilitiesProbeIsNeverCachedAndTheNextCallAsksTheBridgeAgain() {
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp down = api.get(viewer(), RESEARCH + "/capabilities");
        assertThat(down.status()).isEqualTo(502);
        assertThat(down.<String>read("$.reason")).isEqualTo("bridge_unreachable");
        resetSystemConfigs();

        Resp back = api.get(viewer(), RESEARCH + "/capabilities");
        assertThat(back.status()).as("失敗不進快取：Bridge 回來之後第一次呼叫就成功").isEqualTo(200);

        researchQuery.invalidateCapabilities();
        readTimeout.cap(Duration.ofMillis(400));
        bridge().delayMillis = 2500;
        Resp slow = api.get(viewer(), RESEARCH + "/capabilities");
        assertThat(slow.status()).isEqualTo(504);
        assertThat(slow.<String>read("$.reason")).isEqualTo("bridge_timeout");
    }

    @Test
    void theAllowlistListsTheEnvBaseThenTheAdminEntriesAndRelaysTheBridgeDatabaseFailures() {
        Resp base = api.get(viewer(), RESEARCH + "/allowlist");
        assertThat(base.<List<String>>read("$.data[*].source")).containsOnly("ENV");
        assertThat(base.<List<Object>>read("$.data[*].layer")).as("ENV 基底條目沒有 layer").containsOnlyNulls();
        assertThat(base.<List<Integer>>read("$.data[*].minIntervalSeconds")).containsOnly(3);
        assertThat(base.<List<Boolean>>read("$.data[*].enabled")).containsOnly(true);

        Resp added = api.post(admin(), RESEARCH + "/allowlist", map("listKind", "WEB", "host", "example.com", "layer", "INDUSTRY", "purpose", "產業部落格",
                "tosNote", "條款已讀", "minIntervalSeconds", 5, "tosAcknowledged", true));
        assertThat(added.status()).isEqualTo(201);
        Resp after = api.get(viewer(), RESEARCH + "/allowlist");
        assertThat(after.<List<String>>read("$.data[*].host")).endsWith("example.com");
        Map<String, Object> entry = after.<List<Map<String, Object>>>read("$.data").get(4);
        assertThat(entry).containsEntry("source", "ADMIN").containsEntry("layer", "INDUSTRY").containsEntry("minIntervalSeconds", 5)
                .containsEntry("tosAcknowledged", true).containsEntry("addedBy", "admin").containsEntry("purpose", "產業部落格");
        assertThat(entry.get("addedAt")).isInstanceOf(String.class);
        assertThat(entry.get("id")).isEqualTo(added.read("$.data.id"));

        bridge().db = false;
        Resp noDb = api.get(viewer(), RESEARCH + "/allowlist");
        assertThat(noDb.status()).isEqualTo(503);
        assertThat(noDb.<String>read("$.reason")).isEqualTo("research_requires_db");
        bridge().always("allowlist.list", Reply.error(503, "db_blocked"));
        Resp blocked = api.get(viewer(), RESEARCH + "/allowlist");
        assertThat(blocked.status()).isEqualTo(503);
        assertThat(blocked.<String>read("$.reason")).isEqualTo("db_blocked");
    }

    @Test
    void theAllowlistInputGateListsEveryViolationAtOnceAndNeverCallsTheBridge() {
        Resp bad = api.post(admin(), RESEARCH + "/allowlist", map("listKind", "FTP", "host", "https://Example.com/path", "layer", "NEWS",
                "purpose", "字".repeat(201), "minIntervalSeconds", 0));

        assertThat(bad.status()).isEqualTo(422);
        assertThat(bad.<String>read("$.reason")).isEqualTo("invalid_request");
        assertThat(bad.<List<String>>read("$.details.violations[*].field")).containsExactlyInAnyOrder("listKind", "host", "layer", "purpose", "minIntervalSeconds");
        assertThat(bad.<List<String>>read("$.details.violations[*].rule")).containsExactlyInAnyOrder("invalid_value", "invalid_host", "invalid_value", "max_length",
                "out_of_range");
        assertThat(bad.errorFields()).containsExactlyInAnyOrder("listKind", "host", "layer", "purpose", "minIntervalSeconds");

        Resp notBoolean = api.raw(admin(), HttpMethod.PATCH, RESEARCH + "/allowlist/" + UUID.randomUUID(), ApiClient.toJson(map("enabled", "no")));
        assertThat(notBoolean.status()).isEqualTo(422);
        assertThat(notBoolean.<List<String>>read("$.details.violations[*].rule")).containsExactly("invalid_type");
        Resp missing = api.raw(admin(), HttpMethod.PATCH, RESEARCH + "/allowlist/" + UUID.randomUUID(), "{}");
        assertThat(missing.<List<String>>read("$.details.violations[*].rule")).containsExactly("required");
        assertThat(bridge().calls).as("輸入閘擋下的請求一個都沒到 Bridge").isEmpty();

        assertThat(api.post(admin(), RESEARCH + "/allowlist", map("listKind", "WEB", "host", "example.com", "layer", "INDUSTRY")).status()).isEqualTo(201);
        Resp duplicate = api.post(admin(), RESEARCH + "/allowlist", map("listKind", "WEB", "host", "example.com", "layer", "INDUSTRY"));
        assertThat(duplicate.status()).isEqualTo(409);
        assertThat(duplicate.<String>read("$.reason")).as("同 listKind 與 host 已有條目").isEqualTo("allowlist_exists");
        assertThat(duplicate.<String>read("$.details.host")).isEqualTo("example.com");
    }

    // ── 建立專案 ────────────────────────────────────────────────────────────────────────

    @Test
    void creatingAProjectSendsOneSignedBridgeRequestWithTheJwtSubjectAndReturnsTheProjectTheBridgeWrote() {
        Map<String, Object> body = validCreate("alpha-1");
        body.put("createdBy", "mallory");
        body.put("created_by", "mallory");
        body.put("targetScopeHint", "AISDLC_MODULE");

        Resp created = api.post(operator(), RESEARCH + "/projects", body);

        assertThat(created.status()).isEqualTo(201);
        assertThat(created.<Integer>read("$.code")).isEqualTo(201);
        assertThat(created.<String>read("$.data.slug")).isEqualTo("alpha-1");
        assertThat(created.<String>read("$.data.rpNo")).matches("RP-\\d{4,}");
        assertThat(created.<String>read("$.data.flowStep")).isEqualTo("topic");
        assertThat(created.<String>read("$.data.flowPhase")).isEqualTo("INGESTED");
        assertThat(created.<String>read("$.data.flowStatus")).isEqualTo("IDLE");
        assertThat(created.<String>read("$.data.createdBy")).as("Bridge 寫入的 created_by 就是 console-api 送出的值＝JWT subject").isEqualTo("operator");
        assertThat(created.<String>read("$.data.fsmProject")).isEqualTo("research-alpha-1");
        assertThat(created.<Integer>read("$.data.fsmGeneration")).isEqualTo(1);
        assertThat(created.<String>read("$.data.targetScope")).isEqualTo("AISDLC_MODULE");
        assertThat(created.<Boolean>read("$.data.scope.layers.academic")).isTrue();
        assertThat(created.<Boolean>read("$.data.scope.layers.industry")).isFalse();
        assertThat(created.<List<String>>read("$.data.scope.inScope")).as("INT-03：scope 的鍵在邊界轉成 camelCase（前端讀 inScope，不讀 Bridge 的 in_scope）")
                .containsExactly("範圍內一項");
        assertThat(created.<Integer>read("$.data.scope.recencyYears")).isEqualTo(2);
        assertThat(created.<Map<String, Object>>read("$.data.scope")).doesNotContainKeys("in_scope", "recency_years");
        assertThat(created.<Integer>read("$.data.counts.sources")).isZero();

        Call call = onlyWriteTo("POST", "/research/projects");
        assertThat(call.token()).as("寫入帶研究寫入權杖").isEqualTo(MiniResearch.TOKEN);
        assertThat(call.traceId()).as("X-Trace-Id 與回應的追蹤碼相同").isEqualTo(created.header("X-Trace-Id"));
        assertThat(call.body()).containsEntry("research_id", created.read("$.data.id")).containsEntry("created_by", "operator")
                .containsEntry("slug", "alpha-1").containsEntry("depth_level", "STANDARD");
        assertThat(call.body()).doesNotContainKeys("createdBy", "targetScopeHint");
        assertThat(rows("research_projects")).isEqualTo(1);

        Resp duplicate = api.post(operator(), RESEARCH + "/projects", validCreate("alpha-1"));
        assertThat(duplicate.status()).isEqualTo(409);
        assertThat(duplicate.<String>read("$.reason")).isEqualTo("slug_in_use");
        assertThat(duplicate.<String>read("$.details.slug")).isEqualTo("alpha-1");
        assertThat(rows("research_projects")).as("409 之後仍只有一個專案").isEqualTo(1);
    }

    @Test
    @SuppressWarnings("unchecked")
    void theProjectScopeIsExposedInCamelCaseForEveryKeyTheBridgeKeepsInItsScopeMirror() {
        Map<String, Object> body = validCreate("scope-keys");
        Map<String, Object> scope = (Map<String, Object>) body.get("scope");
        scope.put("techStack", "Java 21、Spring Boot 4");
        scope.put("outOfScope", List.of("範圍外一項"));
        scope.put("applicabilityAxes", List.of("技術可行", "效能邊界"));
        body.put("targetScopeHint", "AISDLC_MODULE");

        Resp created = api.post(operator(), RESEARCH + "/projects", body);

        assertThat(created.status()).isEqualTo(201);
        String id = created.read("$.data.id");
        List<String> bridgeKeys = BridgeSource.constants("SCOPE_KEYS", "research", "export.py");
        for (Resp resp : List.of(created, api.get(viewer(), RESEARCH + "/projects/" + id))) {
            Map<String, Object> out = resp.read("$.data.scope");
            assertThat(out.keySet()).as("Bridge 的 scope 鏡像有哪些鍵（export.py 的 SCOPE_KEYS），console-api 就逐一以 camelCase 轉出，建立回應與詳情一致")
                    .containsExactlyInAnyOrderElementsOf(bridgeKeys.stream().map(SiKeyNames::camel).toList());
            assertThat(out.keySet()).noneMatch(key -> key.contains("_"));
            assertThat(out).containsEntry("techStack", "Java 21、Spring Boot 4").containsEntry("inScope", List.of("範圍內一項"))
                    .containsEntry("outOfScope", List.of("範圍外一項")).containsEntry("recencyYears", 2)
                    .containsEntry("applicabilityAxes", List.of("技術可行", "效能邊界")).containsEntry("targetScopeHint", "AISDLC_MODULE");
            assertThat(resp.<Boolean>read("$.data.scope.layers.oss")).as("layers 的四個鍵本來就是單字").isTrue();
        }
    }

    @Test
    void theWriteTokenCheckComesBeforeTheInputGateSoAnUnconfiguredBackendNeverEvenValidates() {
        Map<String, Object> bad = validCreate("Bad_Slug");
        endpoints.tokenUnset();

        Resp disabled = api.post(operator(), RESEARCH + "/projects", bad);

        assertThat(disabled.status()).as("契約 §0.2：503 先於 400／422").isEqualTo(503);
        assertThat(disabled.<String>read("$.reason")).isEqualTo("research_write_disabled");
        assertThat(bridge().calls).isEmpty();
        endpoints.reset();
        assertThat(api.post(operator(), RESEARCH + "/projects", bad).status()).as("權杖回來之後同一個請求是輸入閘的 400").isEqualTo(400);
    }

    @Test
    void aBridgeThatRejectsOrFailsTheCreateIsRelayedNotPretendedAsSuccess() {
        bridge().next("create", Reply.error(502, "init_failed", "details", map("step", "fsm")));
        Resp failed = api.post(operator(), RESEARCH + "/projects", validCreate("beta-1"));
        assertThat(failed.status()).isEqualTo(502);
        assertThat(failed.<String>read("$.reason")).as("Bridge 專屬 reason 逐字").isEqualTo("init_failed");
        assertThat(failed.<String>read("$.details.step")).isEqualTo("fsm");
        assertThat(failed.has("$.data")).isFalse();

        bridge().next("create", Reply.error(422, "sanitization_failed", "violations", List.of(map("field", "slug", "rule", "reserved", "message", "保留字"))));
        Resp rejected = api.post(operator(), RESEARCH + "/projects", validCreate("beta-2"));
        assertThat(rejected.status()).isEqualTo(422);
        assertThat(rejected.<String>read("$.reason")).isEqualTo("sanitization_failed");
        assertThat(rejected.<List<String>>read("$.details.violations[*].rule")).containsExactly("reserved");

        bridge().next("create", Reply.ok(201, "research_id", UUID.randomUUID().toString(), "rp_no", "RP-9999"));
        Resp ghost = api.post(operator(), RESEARCH + "/projects", validCreate("beta-3"));
        assertThat(ghost.status()).as("Bridge 說成功、資料庫卻查無該專案＝上游故障，不是 404 也不是假成功").isEqualTo(502);
        assertThat(ghost.has("$.data")).isFalse();
        assertThat(rows("research_projects")).isZero();
    }

    @Test
    void aMalformedBodyAndAnUnparseableIdAreA400() {
        Resp malformed = api.raw(operator(), HttpMethod.POST, RESEARCH + "/projects", "{not json");
        assertThat(malformed.status()).isEqualTo(400);
        assertThat(api.get(viewer(), RESEARCH + "/projects/not-a-uuid").status()).isEqualTo(400);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + UUID.randomUUID() + "/prd/versions/abc").status()).isEqualTo(400);
        assertThat(bridge().calls).isEmpty();
    }

    // ── 讀取投影 ────────────────────────────────────────────────────────────────────────

    @Test
    void sourcesCarryTheirFetchesAndTierThreeSourcesAreOnlySearchClues() {
        UUID id = fx.project("sources");
        UUID primary = fx.source(id, "S-001", "https://example.org/a", "T1");
        fx.fetch(id, primary, "F-0001", "OK");
        fx.source(id, "S-002", "https://example.org/b", "T3");

        Resp resp = api.get(viewer(), RESEARCH + "/projects/" + id + "/sources");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data[*].sourceNo")).containsExactly("S-001", "S-002");
        assertThat(resp.<List<Boolean>>read("$.data[*].clueOnly")).containsExactly(false, true);
        assertThat(resp.<String>read("$.data[0].publishedAt")).isEqualTo("2025-03-01");
        assertThat(resp.<String>read("$.data[0].layer")).isEqualTo("ACADEMIC");
        assertThat(resp.<String>read("$.data[0].verification")).isEqualTo("V2");
        Map<String, Object> source = resp.<List<Map<String, Object>>>read("$.data").get(0);
        assertThat(source).containsKeys("doi", "gitCommit", "licenseSpdx");
        assertThat(source.get("licenseSpdx")).as("未見的授權是 null").isNull();
        assertThat(resp.<List<Object>>read("$.data[0].fetches")).hasSize(1);
        assertThat(resp.<String>read("$.data[0].fetches[0].fetchNo")).isEqualTo("F-0001");
        assertThat(resp.<String>read("$.data[0].fetches[0].observedBy")).isEqualTo("BRIDGE");
        assertThat(resp.<String>read("$.data[0].fetches[0].host")).isEqualTo("example.org");
        assertThat(resp.<Integer>read("$.data[0].fetches[0].httpStatus")).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data[0].fetches[0].rawBytes")).isEqualTo(1024);
        assertThat(resp.<List<Object>>read("$.data[1].fetches")).as("沒有抓取紀錄的來源回空陣列").isEmpty();
    }

    @Test
    void theEvidenceMatrixCombinesTheItemRowsWithTheArtifactDocumentAndAnEmptyProjectGetsAnEmptyMatrixNotAnError() {
        UUID empty = fx.project("no-evidence");
        Resp none = api.get(viewer(), RESEARCH + "/projects/" + empty + "/evidence");
        assertThat(none.status()).as("剛建立、尚未研究：200 的空矩陣").isEqualTo(200);
        assertThat(none.<Integer>read("$.data.matrixVersion")).isZero();
        assertThat(none.<List<Object>>read("$.data.items")).isEmpty();
        assertThat(none.<List<Object>>read("$.data.counterEvidence")).isEmpty();
        assertThat(none.<String>read("$.data.sha256")).isEmpty();
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + empty + "/evidence?matrixVersion=1").status()).as("指定的版本不存在＝404").isEqualTo(404);

        UUID id = fx.project("with-evidence");
        UUID source = fx.source(id, "S-001", "https://example.org/a", "T1");
        fx.evidenceItem(id, source, 1, "E-002", "技術乙");
        fx.evidenceItem(id, source, 1, "E-001", "技術甲");
        fx.artifact(id, "EVIDENCE_ITEMS", 1, "{\"counter_evidence\":[{\"evidence_no\":\"E-001\",\"search_id\":\"Q-002\",\"conclusion\":\"LIMIT\","
                + "\"source_no\":\"S-001\",\"note\":\"僅限小規模\"},{\"evidence_no\":\"E-002\",\"search_id\":null,\"conclusion\":\"NOT_SEARCHED\","
                + "\"source_no\":null,\"note\":\"\"}],\"honest_bounds\":{\"not_found\":[{\"query\":\"替代方案\",\"date\":\"2026-10-01\",\"result\":\"無\"}],"
                + "\"summary_only\":[\"S-003\"],\"not_read_fully\":[\"S-004\"]},\"search_log\":[{\"id\":1,\"layer\":\"ACADEMIC\",\"tool\":\"WebSearch\","
                + "\"query\":\"q\",\"at\":\"2026-10-01T10:00:00+00:00\",\"result_urls\":[\"https://example.org/a\"]}]}");

        Resp latest = api.get(viewer(), RESEARCH + "/projects/" + id + "/evidence");
        Resp explicit = api.get(viewer(), RESEARCH + "/projects/" + id + "/evidence?matrixVersion=1");

        assertThat(latest.status()).isEqualTo(200);
        assertThat(latest.<Integer>read("$.data.matrixVersion")).isEqualTo(1);
        assertThat(latest.<List<String>>read("$.data.items[*].evidenceNo")).as("依證據編號排序").containsExactly("E-001", "E-002");
        assertThat(latest.<String>read("$.data.items[0].candidate")).isEqualTo("技術甲");
        assertThat(latest.<String>read("$.data.items[0].sourceNo")).isEqualTo("S-001");
        assertThat(latest.<String>read("$.data.items[0].strength")).isEqualTo("MEDIUM");
        assertThat(latest.<Boolean>read("$.data.items[0].unanchored")).isFalse();
        assertThat(latest.<String>read("$.data.items[0].f5Applicability.technical.grade")).isEqualTo("A");
        assertThat(latest.<String>read("$.data.sha256")).matches("[0-9a-f]{64}");
        assertThat(latest.<List<String>>read("$.data.counterEvidence[*].evidenceNo")).containsExactly("E-001", "E-002");
        assertThat(latest.<String>read("$.data.counterEvidence[0].searchId")).isEqualTo("Q-002");
        assertThat(latest.<String>read("$.data.counterEvidence[0].conclusion")).isEqualTo("LIMIT");
        assertThat(latest.<Object>read("$.data.counterEvidence[1].searchId")).isNull();
        assertThat(latest.<String>read("$.data.honestBounds.notFound[0].query")).isEqualTo("替代方案");
        assertThat(latest.<List<String>>read("$.data.honestBounds.summaryOnly")).containsExactly("S-003");
        assertThat(latest.<List<String>>read("$.data.honestBounds.notReadFully")).containsExactly("S-004");
        assertThat(latest.<String>read("$.data.searchLog[0].searchNo")).as("資料庫的整數 id 補零成 Q-NNN").isEqualTo("Q-001");
        assertThat(latest.<List<String>>read("$.data.searchLog[0].resultUrls")).containsExactly("https://example.org/a");
        assertThat(explicit.<Object>read("$.data")).as("指定最新的版本號與預設相同").isEqualTo(latest.read("$.data"));
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/evidence?matrixVersion=2").status()).isEqualTo(404);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/evidence?matrixVersion=0").status()).as("版本號須 ≥1").isEqualTo(400);
    }

    @Test
    void prdVersionListsOmitTheFullTextWhileTheSingleVersionCarriesIt() {
        UUID id = fx.project("versions");
        fx.prdVersion(id, 1, "v0.1.0-draft", "# 第一版");
        fx.prdVersion(id, 2, "v0.2.0-draft", "# 第二版\n\n全文內容");

        Resp list = api.get(viewer(), RESEARCH + "/projects/" + id + "/prd/versions");
        Resp second = api.get(viewer(), RESEARCH + "/projects/" + id + "/prd/versions/2");

        assertThat(list.<List<Integer>>read("$.data[*].versionNo")).containsExactly(1, 2);
        assertThat(list.<List<Map<String, Object>>>read("$.data")).as("清單不含全文").allSatisfy(version -> assertThat(version).doesNotContainKey("content"));
        assertThat(list.<Object>read("$.data[0].parentVersionNo")).isNull();
        assertThat(list.<Integer>read("$.data[1].parentVersionNo")).isEqualTo(1);
        assertThat(list.<String>read("$.data[1].semver")).isEqualTo("v0.2.0-draft");
        assertThat(list.<String>read("$.data[1].authorKind")).isEqualTo("AGENT");
        assertThat(second.<String>read("$.data.content")).isEqualTo("# 第二版\n\n全文內容");
        assertThat(second.<String>read("$.data.sha256")).isEqualTo(ResearchFixtures.sha256("# 第二版\n\n全文內容"));
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/prd/versions/9").<String>read("$.reason")).isEqualTo("research_not_found");
    }

    @Test
    void theEventPageDefaultsTo100ClampsTo500AndRejectsNegativeCursorsAndNonPositiveLimits() {
        UUID id = fx.project("event-paging");
        fx.events(id, 1, 650);

        Resp byDefault = api.get(viewer(), RESEARCH + "/projects/" + id + "/events");
        assertThat(byDefault.<List<Integer>>read("$.data.items[*].seq")).hasSize(100);
        assertThat(byDefault.<Integer>read("$.data.nextSeq")).isEqualTo(100);
        assertThat(byDefault.<Boolean>read("$.data.truncated")).isTrue();
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/events?afterSeq=0&limit=5000").<List<Integer>>read("$.data.items[*].seq")).hasSize(500);

        Resp tail = api.get(viewer(), RESEARCH + "/projects/" + id + "/events?afterSeq=640&limit=50");
        assertThat(tail.<List<Integer>>read("$.data.items[*].seq")).hasSize(10);
        assertThat(tail.<Integer>read("$.data.nextSeq")).isEqualTo(650);
        assertThat(tail.<Boolean>read("$.data.truncated")).isFalse();
        Resp beyond = api.get(viewer(), RESEARCH + "/projects/" + id + "/events?afterSeq=650");
        assertThat(beyond.<List<Object>>read("$.data.items")).isEmpty();
        assertThat(beyond.<Integer>read("$.data.nextSeq")).as("沒有新事件時游標原地不動").isEqualTo(650);
        assertThat(beyond.<Boolean>read("$.data.truncated")).isFalse();

        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/events?afterSeq=-1").status()).isEqualTo(400);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/events?limit=0").status()).isEqualTo(400);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/events?limit=abc").status()).isEqualTo(400);
    }

    // ── 存 PRD、啟動階段、退回、核准的輸入閘 ───────────────────────────────────────────────────

    @Test
    void savingAPrdVersionIsAnOptimisticWriteThroughTheBridgeAndTheResponseNeverCarriesTheFullText() {
        UUID id = fx.project("save-prd");

        Resp first = api.put(operator(), RESEARCH + "/projects/" + id + "/prd", map("baseVersion", 0, "content", "# 第一版", "changeSummary", "  初稿  ",
                "author", "mallory"));

        assertThat(first.status()).isEqualTo(201);
        assertThat(first.<Integer>read("$.code")).isEqualTo(201);
        assertThat(first.<Integer>read("$.data.versionNo")).isEqualTo(1);
        assertThat(first.<String>read("$.data.authorKind")).isEqualTo("HUMAN");
        assertThat(first.<String>read("$.data.author")).as("作者取 JWT subject，本文偽造的 author 被忽略").isEqualTo("operator");
        assertThat(first.<String>read("$.data.changeSummary")).as("前後空白被去掉").isEqualTo("初稿");
        assertThat(first.<Map<String, Object>>read("$.data")).doesNotContainKey("content");
        Call call = onlyWriteTo("PUT", "/prd");
        assertThat(call.body()).containsEntry("base_version", 0).containsEntry("author", "operator").containsEntry("content", "# 第一版");

        Resp stale = api.put(operator(), RESEARCH + "/projects/" + id + "/prd", map("baseVersion", 0, "content", "# 又一版"));
        assertThat(stale.status()).isEqualTo(409);
        assertThat(stale.<String>read("$.reason")).isEqualTo("prd_version_conflict");
        assertThat(stale.<Integer>read("$.details.headVersion")).as("衝突時回目前 head，客戶端據以重新載入").isEqualTo(1);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id + "/prd/versions").<List<Object>>read("$.data")).hasSize(1);

        Resp second = api.put(operator(), RESEARCH + "/projects/" + id + "/prd", map("baseVersion", 1, "content", "# 第二版"));
        assertThat(second.<Integer>read("$.data.versionNo")).isEqualTo(2);
        assertThat(second.<Integer>read("$.data.parentVersionNo")).isEqualTo(1);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + id).<Integer>read("$.data.headPrdVersion")).isEqualTo(2);
    }

    @Test
    void thePrdSaveGateRejectsMissingBlankNulAndOversizedContentWithoutCallingTheBridge() {
        UUID id = fx.project("prd-gate");
        String url = RESEARCH + "/projects/" + id + "/prd";

        Resp missing = api.put(operator(), url, map("changeSummary", "x"));
        assertThat(missing.status()).isEqualTo(422);
        assertThat(missing.<List<String>>read("$.details.violations[*].field")).containsExactlyInAnyOrder("baseVersion", "content");
        Resp blank = api.put(operator(), url, map("baseVersion", 0, "content", "   \n  "));
        assertThat(blank.<List<String>>read("$.details.violations[*].rule")).containsExactly("required");
        Resp nul = api.put(operator(), url, map("baseVersion", 0, "content", "a\u0000b"));
        assertThat(nul.<List<String>>read("$.details.violations[*].rule")).containsExactly("invalid_content");
        Resp tooLarge = api.put(operator(), url, map("baseVersion", 0, "content", "字".repeat(400_000)));
        assertThat(tooLarge.<List<String>>read("$.details.violations[*].rule")).as("1 MiB 以 UTF-8 位元組計（40 萬個中文字＝120 萬位元組）").containsExactly("too_large");
        Resp negative = api.put(operator(), url, map("baseVersion", -1, "content", "x", "changeSummary", "字".repeat(501)));
        assertThat(negative.<List<String>>read("$.details.violations[*].field")).containsExactlyInAnyOrder("baseVersion", "changeSummary");
        assertThat(bridge().calls).isEmpty();
        assertThat(rows("research_prd_versions")).isZero();
    }

    @Test
    void thePrdContentLimitIsExactlyOneMebibyteOfUtf8BytesInclusiveNotACharacterCount() {
        UUID id = fx.project("prd-limit");
        String url = RESEARCH + "/projects/" + id + "/prd";
        int mebibyte = 1_048_576;

        Resp exact = api.put(operator(), url, map("baseVersion", 0, "content", "a".repeat(mebibyte)));
        assertThat(exact.status()).as("恰 1 MiB（ASCII 一字元一位元組）放行").isEqualTo(201);
        assertThat(exact.<Integer>read("$.data.bytes")).isEqualTo(mebibyte);

        Resp over = api.put(operator(), url, map("baseVersion", 1, "content", "a".repeat(mebibyte + 1)));
        assertThat(over.status()).as("1 MiB 加 1 位元組被拒").isEqualTo(422);
        assertThat(over.<List<String>>read("$.details.violations[*].rule")).containsExactly("too_large");

        // 「字」在 UTF-8 是 3 位元組：349_525 個＝1_048_575 位元組，再加一個 ASCII 字元恰 1 MiB（放行），再加兩個就超界（被拒）——界線以位元組計、不是字元數
        String threeByteChars = "字".repeat(349_525);
        Resp exactMultibyte = api.put(operator(), url, map("baseVersion", 1, "content", threeByteChars + "a"));
        assertThat(exactMultibyte.status()).as("多位元組內容以位元組計：恰 1 MiB 放行").isEqualTo(201);
        assertThat(exactMultibyte.<Integer>read("$.data.bytes")).isEqualTo(mebibyte);
        Resp overMultibyte = api.put(operator(), url, map("baseVersion", 2, "content", threeByteChars + "aa"));
        assertThat(overMultibyte.status()).as("字元數遠小於 1 M 但位元組數是 1 MiB 加 1").isEqualTo(422);
        assertThat(overMultibyte.<List<String>>read("$.details.violations[*].rule")).containsExactly("too_large");

        assertThat(bridge().countCalls("PUT", "/research/projects/")).as("被拒的兩次沒有送到 Bridge").isEqualTo(2);
        assertThat(rows("research_prd_versions")).isEqualTo(2);
    }

    @Test
    void startingAStageForwardsTheCallerAndTheOptionsAndAnUnknownStageNeverReachesTheBridge() {
        UUID id = fx.project("stages");

        Resp started = api.post(operator(), RESEARCH + "/projects/" + id + "/stages/draft", map("auto", true, "note", "  先出初稿 ", "afterEscalation", true));

        assertThat(started.status()).isEqualTo(202);
        assertThat(started.<Integer>read("$.code")).isEqualTo(202);
        assertThat(started.<String>read("$.data.stageRunId")).isNotBlank();
        assertThat(started.<String>read("$.data.flowPhase")).isEqualTo("RESEARCHING");
        assertThat(started.<String>read("$.data.flowStatus")).isEqualTo("RUNNING");
        Call call = onlyWriteTo("POST", "/stages/draft:start");
        assertThat(call.body()).containsEntry("auto", true).containsEntry("note", "先出初稿").containsEntry("requested_by", "operator")
                .containsEntry("after_escalation", true);

        Resp plain = api.post(operator(), RESEARCH + "/projects/" + id + "/stages/review", null);
        assertThat(plain.status()).as("本文可省略").isEqualTo(202);
        Call defaults = bridge().lastCall();
        assertThat(defaults.body()).containsEntry("auto", false).containsEntry("after_escalation", false).doesNotContainKey("note");

        long before = bridge().calls.size();
        Resp unknown = api.post(operator(), RESEARCH + "/projects/" + id + "/stages/deploy", Map.of());
        assertThat(unknown.status()).isEqualTo(422);
        assertThat(unknown.<List<String>>read("$.details.violations[*].field")).containsExactly("stage");
        assertThat(bridge().calls).hasSize((int) before);
    }

    @Test
    void aStageTheBridgeHasNotImplementedYetIsReportedAsAnUpstreamFailureWithTheEndpointNotAFakeSuccess() {
        UUID id = fx.project("stage-skeleton");
        // 真 Bridge 現在唯一還回 501 的是 P1 的 tcs-draft（routers/research.py 的 _not_implemented）：本文形狀照它——endpoint、detail、stage 三個頂層補充欄位
        bridge().next("stage:tcs-draft", Reply.error(501, "not_implemented", "endpoint", "stages/tcs-draft:start", "detail", "尚未實作：這是 P1 功能，P0 不提供",
                "stage", "tcs-draft"));

        Resp resp = api.post(operator(), RESEARCH + "/projects/" + id + "/stages/tcs-draft", Map.of());

        assertThat(resp.status()).as("501 骨架轉成契約 §0.2 的上游失敗（502；主控裁決：上游未實作屬上游失敗類），不假裝成功").isEqualTo(502);
        assertThat(resp.<String>read("$.reason")).isEqualTo("not_implemented");
        assertThat(resp.<String>read("$.details.endpoint")).as("INT-14①：details.endpoint 指出哪個端點未實作").isEqualTo("stages/tcs-draft:start");
        assertThat(resp.<String>read("$.details.stage")).isEqualTo("tcs-draft");
        assertThat(resp.<Integer>read("$.details.bridgeStatus")).as("Bridge 的原狀態碼 501 留在 details").isEqualTo(501);
        assertThat(resp.has("$.data")).isFalse();
        assertThat(bridge().calls).as("不重試").hasSize(1);
    }

    @Test
    void returningThePrdForChangesForwardsTheReasonAndTheJwtSubjectAndTheReasonIsRequired() {
        UUID id = fx.project("return-gate");
        String url = RESEARCH + "/projects/" + id + "/return";

        Resp ok = api.post(adminAs("alice"), url, map("reason", "  第三章缺風險分析  ", "approver", "mallory"));

        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<String>read("$.data.gateDecisionId")).isNotBlank();
        assertThat(ok.<Integer>read("$.data.fsmRetryCount")).isEqualTo(1);
        assertThat(ok.<Boolean>read("$.data.escalated")).isFalse();
        Call call = onlyWriteTo("POST", ":return");
        assertThat(call.body()).containsEntry("reason", "第三章缺風險分析").containsEntry("approver", "alice");

        long before = bridge().calls.size();
        for (Map<String, Object> bad : List.of(map(), map("reason", "   "), map("reason", "字".repeat(501)))) {
            Resp resp = api.post(admin(), url, bad);
            assertThat(resp.status()).as(String.valueOf(bad)).isEqualTo(422);
            assertThat(resp.<List<String>>read("$.details.violations[*].field")).containsExactly("reason");
        }
        assertThat(bridge().calls).hasSize((int) before);
    }

    @Test
    void theApproveGateRejectsMalformedDigestsAndVersionsAllAtOnceBeforeAnyBridgeCall() {
        UUID id = fx.project("approve-gate");
        Map<String, Object> digests = new LinkedHashMap<>();
        digests.put("/etc/passwd", "sha256:" + "a".repeat(64));
        digests.put("01_specs/../x.md", "sha256:" + "a".repeat(64));
        digests.put("01_specs/PRD.md", "sha256:" + "A".repeat(64));
        digests.put("00_research/evidence_matrix.md", "md5:abc");

        Resp bad = api.post(admin(), RESEARCH + "/projects/" + id + "/approve", map("prdVersion", 0, "expectedDigests", digests, "reason", "   "));

        assertThat(bad.status()).isEqualTo(422);
        assertThat(bad.<String>read("$.reason")).isEqualTo("invalid_request");
        List<String> rules = bad.read("$.details.violations[*].rule");
        assertThat(rules).contains("invalid_value", "invalid_path", "invalid_digest", "invalid_length");
        assertThat(bad.<List<String>>read("$.details.violations[*].field")).contains("prdVersion", "expectedDigests", "expectedDigests.01_specs/PRD.md",
                "expectedDigests.00_research/evidence_matrix.md", "reason");
        Resp missing = api.post(admin(), RESEARCH + "/projects/" + id + "/approve", Map.of());
        assertThat(missing.<List<String>>read("$.details.violations[*].field")).containsExactlyInAnyOrder("prdVersion", "expectedDigests");
        assertThat(bridge().calls).isEmpty();
    }

    @Test
    void anApproveWithoutAnyDigestKeyIsABlindApprovalRefusedAsMissingDigestsButASingleKeyIsEnoughForTheGate() {
        UUID id = fx.project("approve-blind", "studio", "GATE0_PENDING", "WAITING_HUMAN", "");
        String url = RESEARCH + "/projects/" + id + "/approve";

        for (Map<String, Object> blind : List.of(map("prdVersion", 1, "expectedDigests", Map.of()), map("prdVersion", 1))) {
            Resp resp = api.post(admin(), url, blind);

            assertThat(resp.status()).as(String.valueOf(blind)).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).as("D-72：零鍵單獨出現時頂層 reason 是 missing_digests（不是 invalid_request）").isEqualTo("missing_digests");
            assertThat(resp.<List<String>>read("$.details.violations[*].field")).containsExactly("expectedDigests");
            assertThat(resp.<List<String>>read("$.details.violations[*].rule")).containsExactly("missing_digests");
            assertThat(resp.errorFields()).containsExactly("expectedDigests");
            assertThat(resp.has("$.data")).isFalse();
        }
        Resp combined = api.post(admin(), url, map("expectedDigests", Map.of()));
        assertThat(combined.<String>read("$.reason")).as("另有其他違規時頂層 reason 回 invalid_request，零鍵仍列在 violations 裡").isEqualTo("invalid_request");
        assertThat(combined.<List<String>>read("$.details.violations[*].rule")).containsExactlyInAnyOrder("required", "missing_digests");
        assertThat(bridge().calls).as("閘擋下的請求一個都沒到 Bridge").isEmpty();

        String matrix = "00_research/evidence_matrix.md";
        Resp one = api.post(admin(), url, map("prdVersion", 1, "expectedDigests", map(matrix, "sha256:" + "a".repeat(64))));
        assertThat(one.status()).as("只比對送來的鍵：一鍵就夠，不再要求涵蓋四個檔").isEqualTo(200);
        assertThat(onlyWriteTo("POST", ":approve-baseline").body().get("expected_digests")).isEqualTo(Map.of(matrix, "sha256:" + "a".repeat(64)));
    }

    // ── 找不到專案、換世代與重試初始化 ──────────────────────────────────────────────────────

    @Test
    void everyWriteOnAnUnknownProjectIs404BeforeTheBridgeIsCalled() {
        String ghost = RESEARCH + "/projects/" + UUID.randomUUID();
        Map<String, Object> approve = map("prdVersion", 1, "expectedDigests", map("01_specs/PRD-v1.0.0.md", "sha256:" + "a".repeat(64)));
        List<Resp> responses = List.of(
                api.put(operator(), ghost + "/prd", map("baseVersion", 0, "content", "# x")),
                api.post(operator(), ghost + "/stages/research", Map.of()),
                api.post(admin(), ghost + "/approve", approve),
                api.post(admin(), ghost + "/return", map("reason", "退回")),
                api.post(operator(), ghost + "/cancel"),
                api.post(operator(), ghost + "/reconcile"),
                api.post(operator(), ghost + "/archive"),
                api.post(operator(), ghost + "/restore"),
                api.post(operator(), ghost + "/reinit", Map.of()),
                api.post(admin(), ghost + "/reinit", map("generation", "next", "reason", "換世代")));

        assertThat(responses).allSatisfy(resp -> {
            assertThat(resp.status()).isEqualTo(404);
            assertThat(resp.<String>read("$.reason")).isEqualTo("research_not_found");
        });
        assertThat(bridge().calls).as("不存在的專案：一個 Bridge 請求都沒送").isEmpty();
    }

    @Test
    void reinitRejectsAnUnknownGenerationAndForwardsTheRetryInitModeWithoutAnyDeciderFields() {
        UUID id = fx.project("reinit-modes", "topic", "INGESTED", "FAILED", "init_failed:fsm");
        String url = RESEARCH + "/projects/" + id + "/reinit";

        Resp unknown = api.post(admin(), url, map("generation", "prev", "reason", "x"));
        assertThat(unknown.status()).isEqualTo(422);
        assertThat(unknown.<List<String>>read("$.details.violations[*].rule")).containsExactly("invalid_value");
        assertThat(bridge().calls).isEmpty();

        Resp retry = api.post(operator(), url, null);
        assertThat(retry.status()).as("本文省略＝重試初始化").isEqualTo(200);
        assertThat(retry.<Map<String, Object>>read("$.data")).as("重試初始化只回 flow，沒有換世代的三個欄位（鍵省略）").containsKey("flow")
                .doesNotContainKeys("fsmProject", "fsmGeneration", "gateDecisionId");
        assertThat(onlyWriteTo("POST", ":reinit").body()).isEmpty();

        bridge().next("reinit", Reply.error(409, "stage_conflict", "details", map("flowStatus", "RUNNING", "flowDetail", "")));
        Resp conflict = api.post(operator(), url, Map.of());
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(conflict.<String>read("$.reason")).isEqualTo("stage_conflict");
        assertThat(conflict.<String>read("$.details.flowStatus")).isEqualTo("RUNNING");
    }

    @Test
    void aGenerationChangeForwardsTheTrimmedReasonAndTheJwtSubjectAsTheDecider() {
        UUID id = fx.project("reinit-reason", "studio", "REVIEWING", "ESCALATED", "");
        String url = RESEARCH + "/projects/" + id + "/reinit";

        Resp ok = api.post(adminAs("carol"), url, map("generation", "next", "reason", "  換世代  "));

        assertThat(ok.status()).isEqualTo(200);
        assertThat(onlyWriteTo("POST", ":reinit").body()).containsEntry("generation", "next").containsEntry("reason", "換世代").containsEntry("decided_by", "carol");
    }
}
