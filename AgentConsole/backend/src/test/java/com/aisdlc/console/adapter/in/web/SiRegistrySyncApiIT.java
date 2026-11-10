package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.service.SiAuditSigner;
import com.aisdlc.console.support.AbruptCloseServer;
import com.aisdlc.console.support.AbstractRegistryIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SiWriteSeam;
import com.aisdlc.minibridge.MiniBridge.Si.WriteReply;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import tools.jackson.databind.json.JsonMapper;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 登記同步端點 API-SI-15（TCS-ResearchRegistry AT-965-6-1～6-5、6-8、6-9；契約 §5A.4），對<b>真的 HTTP</b> 迷你 Bridge 與真 PostgreSQL 驗每一列。
 * 為什麼重要：同步把「Console 當下的研究來源登記」變成會被主機端驗簽入帳的位元組——快照若被 console-api 重新序列化（鍵序、跳脫、換行）、冪等若只比歷史
 * 而不比「最新」（D→E→D 的第二個 D 被誤當 unchanged）、序 4～6 的拒絕若留下副作用，自我進化就會抓到與使用者設定不同的來源，或永遠停在舊登記。
 */
class SiRegistrySyncApiIT extends AbstractRegistryIT {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String K0_ID = "f076edf0";

    private Resp sync(String token) {
        return api.post(token, SYNC, Map.of());
    }

    private static String hmac(String body) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(SiWriteSeam.K0.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(body.getBytes(StandardCharsets.UTF_8)));
        } catch (java.security.GeneralSecurityException e) {
            throw new IllegalStateException(e);
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> object(String json) {
        return JSON.readValue(json, Map.class);
    }

    /** 副作用量測：稽核列數、迷你 Bridge 收到的落檔請求數、ref 取用次數、迷你 Bridge 的 GET /research/registry 次數。 */
    private record Counts(long rows, int writes, int refsTaken, long snapshots) {
    }

    private Counts counts() {
        return new Counts(writeCount(), MINI.si.writes.size(), refs.taken(), registryRequests());
    }

    // ── AT-965-6-1 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_6_1_theReceiptIsPendingAndTheAuditFileEmbedsTheBridgeSnapshotVerbatim() {
        refs.refs(ref("a1", 1));
        snapshot(APPENDIX_B, APPENDIX_B_SHA);

        Resp resp = sync(admin());

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.outcome")).isEqualTo("written");
        assertThat(resp.<String>read("$.data.state")).isEqualTo("pending");
        assertThat(resp.<String>read("$.data.kind")).isEqualTo("src-registry");
        assertThat(resp.<String>read("$.data.auditRef")).isEqualTo(ref("a1", 1));
        assertThat(resp.<String>read("$.data.registrySha256")).isEqualTo(APPENDIX_B_SHA);
        assertThat(resp.<String>read("$.data.time")).matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{2}:\\d{2}").doesNotContain("Z");
        assertThat(resp.<String>read("$.data.keyId")).isEqualTo(K0_ID);
        assertThat(resp.body()).as("收據與回應文案不含「已同步」「已生效」").doesNotContain("已同步").doesNotContain("已生效");

        List<Map<String, Object>> rows = writeRows();
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0)).containsEntry("kind", "src-registry").containsEntry("user", "admin").containsEntry("role", "ADMIN")
                .containsEntry("subject_id", null).containsEntry("digest", APPENDIX_B_SHA);
        assertThat(MINI.si.writes).hasSize(1);
        assertThat(MINI.si.writes.get(0).path()).isEqualTo("/si/registry:sync");
        assertThat(MINI.si.writes.get(0).token()).isEqualTo(SiWriteSeam.T0);
        String file = receivedText(0);
        assertThat(file).as("外層檔緊湊、無 BOM、無結尾換行").doesNotStartWith("﻿").doesNotEndWith("\n").doesNotContain("\n  ");
        Map<String, Object> outer = object(file);
        assertThat(new ArrayList<>(outer.keySet())).containsExactly("schema_rev", "kind", "audit_ref", "subject", "body", "key_id", "mac");
        assertThat(outer.get("kind")).isEqualTo("src-registry");
        assertThat(outer.get("subject")).as("subject 為 null").isNull();
        String bodyText = (String) outer.get("body");
        Map<String, Object> body = object(bodyText);
        assertThat(new ArrayList<>(body.keySet())).containsExactly("schema_rev", "audit_ref", "kind", "user", "role", "time", "registry_text", "registry_sha256");
        assertThat(body.get("registry_text")).as("registry_text 逐位元組取自 Bridge（含換行與中文）").isEqualTo(APPENDIX_B);
        assertThat(body.get("registry_sha256")).isEqualTo(APPENDIX_B_SHA);
        assertThat(rows.get(0).get("body")).as("列的 body＝簽章的 body 字串").isEqualTo(bodyText);
        assertThat(outer.get("mac")).as("mac 以 K0 對 body 位元組重算相等").isEqualTo(hmac(bodyText));
        assertThat(file).as("非 ASCII 不跳脫、/ 不跳脫").contains("最新 3 篇研究文章的全文（逐字）").doesNotContain("\\u6700").doesNotContain("\\/");
    }

    // ── AT-965-6-2 ───────────────────────────────────────────────────────────────────────────

    private record Gate(String label, Runnable setup, Supplier<Resp> call, int status, String reason, String cause, boolean beforeSnapshot) {
    }

    /** 每個情境之間回到乾淨基線（設定、迷你 Bridge、逾時上限、系統參數、ref 佇列）。 */
    private void resetRow() {
        settings.reset();
        MINI.research.reset();
        MINI.si.reset();
        readTimeout.reset();
        resetSystemConfigs();
        mirror(null, List.of(), DROP);
        snapshot(APPENDIX_B, APPENDIX_B_SHA);
        refs.reset();
        refs.refs(ref("a1", 1), ref("a1", 2));
        jdbc.execute("TRUNCATE console.si_console_writes");
    }

    @Test
    void AT_965_6_2_everyRefusedGateLeavesNoSideEffectAndTheEarlierGateWins() {
        String evilText = "\"\n".repeat(11_000);
        List<Gate> gates = new ArrayList<>();
        gates.add(new Gate("1 OPERATOR", () -> { }, () -> sync(operator()), 403, "ACCESS_DENIED", null, true));
        gates.add(new Gate("2 ADMIN 不在名單", () -> { }, () -> sync(adminAs("admin2")), 403, "si_write_forbidden", null, true));
        gates.add(new Gate("3a 金鑰未設", () -> settings.noKey(), () -> sync(admin()), 503, "si_write_disabled", "audit_key_unset", true));
        gates.add(new Gate("3b 權杖未設", () -> settings.noToken(), () -> sync(admin()), 503, "si_write_disabled", "bridge_token_unset", true));
        gates.add(new Gate("4a 快照 503 research_requires_db", () -> MINI.research.always("registry", Reply.error(503, "research_requires_db")),
                () -> sync(admin()), 503, "research_requires_db", null, false));
        gates.add(new Gate("4b 快照連線失敗", () -> setting("sdd", "engineUrl", "http://127.0.0.1:1"), () -> sync(admin()), 502, "bridge_unreachable", null, false));
        gates.add(new Gate("4c 快照逾時", () -> {
            readTimeout.cap(Duration.ofMillis(400));
            MINI.research.delayMillis = 2_500;
        }, () -> sync(admin()), 504, "bridge_timeout", null, false));
        gates.add(new Gate("4d 快照 422 registry_too_large", () -> MINI.research.always("registry", Reply.error(422, "registry_too_large", "details",
                map("what", "registry_text", "limit", 24576, "size", 30000))), () -> sync(admin()), 422, "registry_too_large", null, false));
        gates.add(new Gate("5 鏡像不可用", () -> MINI.si.unavailable = Map.of("cause", "nonzero_rc", "detail", "rc=3"), () -> sync(admin()), 503, "si_unavailable",
                "si_unavailable", false));
        gates.add(new Gate("5′ 鏡像掃描超上限", () -> MINI.si.payloads.put("events", export("events", List.of(), true, 1)), () -> sync(admin()), 503, "si_unavailable",
                "scan_cap_exceeded", false));
        gates.add(new Gate("6 外層檔超界", () -> snapshot(evilText, SHA_D), () -> sync(admin()), 422, "registry_too_large", null, false));

        for (Gate gate : gates) {
            resetRow();
            gate.setup().run();
            Counts before = counts();
            Resp resp = gate.call().get();
            Counts after = counts();
            assertThat(resp.status()).as("%s：狀態碼", gate.label()).isEqualTo(gate.status());
            assertThat(resp.<String>read("$.reason")).as("%s：reason", gate.label()).isEqualTo(gate.reason());
            if (gate.cause() != null) {
                assertThat(resp.<String>read("$.details.cause")).as("%s：details.cause", gate.label()).isEqualTo(gate.cause());
            }
            assertThat(after.rows()).as("%s：稽核列數不變", gate.label()).isEqualTo(before.rows());
            assertThat(after.writes()).as("%s：迷你 Bridge 的落檔請求數不變", gate.label()).isEqualTo(before.writes());
            assertThat(after.refsTaken()).as("%s：ref 取用數不變", gate.label()).isEqualTo(before.refsTaken());
            if (gate.beforeSnapshot()) {
                assertThat(after.snapshots()).as("%s：序 4 尚未到，快照請求數為 0", gate.label()).isZero();
            }
            if (gate.label().startsWith("6")) {
                assertThat(resp.<String>read("$.details.what")).isEqualTo("audit_file");
                assertThat(resp.<Integer>read("$.details.limit")).isEqualTo(SiAuditSigner.AUDIT_FILE_MAX_BYTES).isEqualTo(65536);
                assertThat(resp.<Integer>read("$.details.size")).isGreaterThan(65536);
            }
            if (gate.label().startsWith("4d")) {
                assertThat(resp.<String>read("$.details.what")).isEqualTo("registry_text");
            }
        }
        resetRow();
    }

    // ── AT-965-6-3 ───────────────────────────────────────────────────────────────────────────

    private record Case(String label, Object latest, List<String> ingested, List<String[]> writes, int status, String outcome, String state, String auditRef) {
    }

    private static String[] w(String ref, String digest, String time) {
        return new String[] {ref, digest, time};
    }

    @Test
    void AT_965_6_3_idempotencyOnlyComparesTheLatestAndALaterPendingWriteBlocksUnchanged() {
        String r1 = ref("c1", 1);
        String r2 = ref("c1", 2);
        String r3 = ref("c1", 3);
        List<Case> cases = List.of(
                new Case("a 最新已入帳＝當前", latest(r1, SHA_D), List.of(r1), List.<String[]>of(w(r1, SHA_D, T1)), 200, "unchanged", "synced", r1),
                new Case("b 有待入帳列＝當前", latest(r1, SHA_E), List.of(r1), List.<String[]>of(w(r1, SHA_E, T1), w(r2, SHA_D, T2)), 200, "unchanged", "pending", r2),
                new Case("c 無相符列", latest(r1, SHA_E), List.of(r1), List.<String[]>of(w(r1, SHA_E, T1)), 201, "written", "pending", null),
                new Case("d A→B→A：舊的 D 已入帳不算待入帳", latest(r2, SHA_E), List.of(r1, r2), List.<String[]>of(w(r1, SHA_D, T1), w(r2, SHA_E, T2)), 201, "written", "pending", null),
                new Case("e 待入帳列 digest＝E≠D", latest(r1, SHA_F), List.of(r1), List.<String[]>of(w(r1, SHA_F, T1), w(r2, SHA_E, T2)), 201, "written", "pending", null),
                new Case("f 從未同步", null, List.of(), List.of(), 201, "written", "pending", null),
                new Case("g research_registry 缺鍵", DROP, List.of(), List.of(), 503, null, null, null),
                new Case("h 已入帳＝D 但有更新的待入帳 E", latest(r1, SHA_D), List.of(r1), List.<String[]>of(w(r1, SHA_D, T1), w(r2, SHA_E, T2)), 201, "written", "pending", null),
                new Case("i 更舊的未入帳列不算 P", latest(r2, SHA_D), List.of(r2), List.<String[]>of(w(r1, SHA_E, T1), w(r2, SHA_D, T2)), 200, "unchanged", "synced", r2),
                new Case("j 兩個待入帳列取最新者", latest(r1, SHA_E), List.of(r1), List.<String[]>of(w(r1, SHA_E, T1), w(r2, SHA_D, T2), w(r3, SHA_D, T3)), 200, "unchanged", "pending", r3));
        for (Case c : cases) {
            MINI.si.reset();
            MINI.research.reset();
            jdbc.execute("TRUNCATE console.si_console_writes");
            refs.reset();
            refs.refs(ref("d1", 1));
            snapshot("{}\n", SHA_D);
            mirror(c.latest(), c.ingested(), DROP);
            for (String[] row : c.writes()) {
                insertRegistryWrite(row[0], row[1], row[2]);
            }
            Counts before = counts();

            Resp resp = sync(admin());

            assertThat(resp.status()).as("%s：狀態碼", c.label()).isEqualTo(c.status());
            Counts after = counts();
            if (c.status() == 503) {
                assertThat(resp.<String>read("$.reason")).as(c.label()).isEqualTo("si_unavailable");
                assertThat(after.rows()).as("%s：零副作用", c.label()).isEqualTo(before.rows());
                assertThat(after.writes()).isEqualTo(before.writes());
                continue;
            }
            assertThat(resp.<String>read("$.data.outcome")).as("%s：outcome", c.label()).isEqualTo(c.outcome());
            assertThat(resp.<String>read("$.data.state")).as("%s：state", c.label()).isEqualTo(c.state());
            if ("unchanged".equals(c.outcome())) {
                assertThat(resp.<String>read("$.data.auditRef")).as("%s：auditRef", c.label()).isEqualTo(c.auditRef());
                assertThat(resp.<Object>read("$.data.kind")).as("%s：kind 為 null", c.label()).isNull();
                assertThat(resp.<Object>read("$.data.time")).isNull();
                assertThat(resp.<Object>read("$.data.keyId")).isNull();
                assertThat(after.rows()).as("%s：unchanged 零副作用（列）", c.label()).isEqualTo(before.rows());
                assertThat(after.writes()).as("%s：落檔請求", c.label()).isEqualTo(before.writes());
                assertThat(after.refsTaken()).as("%s：ref", c.label()).isEqualTo(before.refsTaken());
            } else {
                assertThat(after.rows()).as("%s：written 多一列", c.label()).isEqualTo(before.rows() + 1);
            }
        }
    }

    // ── AT-965-6-9 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_6_9_theSequenceDEDKeepsSendingAndTimeIsStrictlyIncreasing() {
        String rD1 = ref("e1", 1);
        refs.refs(ref("e2", 2), ref("e3", 3));
        insertRegistryWrite(rD1, SHA_D, T1);
        mirror(latest(rD1, SHA_D), List.of(rD1), DROP);
        snapshot("{}\n", SHA_D);

        Resp step1 = sync(admin());
        assertThat(step1.status()).isEqualTo(200);
        assertThat(step1.<String>read("$.data.outcome")).isEqualTo("unchanged");
        assertThat(step1.<String>read("$.data.state")).isEqualTo("synced");
        assertThat(writeCount()).isEqualTo(1);

        snapshot("{}\n", SHA_E);
        Resp step2 = sync(admin());
        assertThat(step2.status()).isEqualTo(201);
        assertThat(step2.<String>read("$.data.state")).isEqualTo("pending");
        String rE = step2.read("$.data.auditRef");

        snapshot("{}\n", SHA_D);
        Resp step3 = sync(admin());
        assertThat(step3.status()).as("有更新的待入帳寫入 E：當前 D 不得回 unchanged").isEqualTo(201);
        String rD2 = step3.read("$.data.auditRef");

        Resp step4 = api.get(viewer(), REGISTRY);
        assertThat(step4.<String>read("$.data.state")).isEqualTo("pending");
        assertThat(step4.<String>read("$.data.pendingAuditRef")).isEqualTo(rD2);

        Resp step5 = sync(admin());
        assertThat(step5.status()).isEqualTo(200);
        assertThat(step5.<String>read("$.data.outcome")).isEqualTo("unchanged");
        assertThat(step5.<String>read("$.data.state")).isEqualTo("pending");
        assertThat(step5.<String>read("$.data.auditRef")).isEqualTo(rD2);
        assertThat(writeCount()).as("src-registry 列恰三（原已入帳的 D、E、D2）").isEqualTo(3);
        List<Map<String, Object>> rows = writeRows();
        assertThat(rows).extracting(r -> r.get("audit_ref")).contains(rE, rD2);
        String timeE = String.valueOf(rows.stream().filter(r -> r.get("audit_ref").equals(rE)).findFirst().orElseThrow().get("time_utc"));
        String timeD2 = String.valueOf(rows.stream().filter(r -> r.get("audit_ref").equals(rD2)).findFirst().orElseThrow().get("time_utc"));
        assertThat(timeD2).as("R_D2 的 time 嚴格大於 R_E（根層 REG-STALE 單調性的前提）").isGreaterThan(timeE);

        mirror(latest(rD2, SHA_D), List.of(rD1, rE, rD2), DROP);
        Resp step6 = api.get(viewer(), REGISTRY);
        assertThat(step6.<String>read("$.data.state")).isEqualTo("synced");
        Resp again = sync(admin());
        assertThat(again.status()).isEqualTo(200);
        assertThat(again.<String>read("$.data.state")).isEqualTo("synced");
        assertThat(writeCount()).isEqualTo(3);
    }

    // ── AT-965-6-4 ───────────────────────────────────────────────────────────────────────────

    private record Failure(String label, Runnable setup, int status, boolean keeps, int bridgeWrites) {
    }

    @Test
    void AT_965_6_4_definiteFailuresCompensateAndUncertainOnesKeepTheRowWithoutRetry() {
        List<Failure> failures = new ArrayList<>();
        failures.add(new Failure("Bridge 422", () -> MINI.si.writeReply = WriteReply.error(422, "invalid_request", "violations",
                List.of(map("field", "kind", "rule", "kind_mismatch", "message", "kind 須為 src-registry"))), 422, false, 1));
        failures.add(new Failure("Bridge 503", () -> MINI.si.writeReply = WriteReply.error(503, "si_write_disabled", "detail", "BRIDGE_SI_AUDIT_DIR 未設"), 503, false, 1));
        failures.add(new Failure("Bridge 500", () -> MINI.si.writeReply = WriteReply.error(500, "internal_error"), 502, false, 1));
        failures.add(new Failure("連線階段失敗", () -> MINI.si.onRead = path -> {
            if ("/si/events".equals(path)) {
                setting("sdd", "engineUrl", "http://127.0.0.1:1");           // 讀完鏡像之後、落檔之前才讓位址失效
            }
        }, 502, false, 0));
        failures.add(new Failure("讀取逾時", () -> {
            readTimeout.cap(Duration.ofSeconds(1));
            MINI.si.writeDelayMillis = 3_000;
        }, 504, true, 1));
        failures.add(new Failure("2xx 本文無法解析", () -> MINI.si.writeReply = new WriteReply(201, "not json"), 502, true, 1));
        for (Failure failure : failures) {
            resetRow();
            failure.setup().run();
            Resp resp = sync(admin());
            assertThat(resp.status()).as("%s：狀態碼", failure.label()).isEqualTo(failure.status());
            assertThat(MINI.si.writes).as("%s：落檔請求數（不重試）", failure.label()).hasSize(failure.bridgeWrites());
            assertThat(writeCount()).as("%s：稽核列%s", failure.label(), failure.keeps() ? "保留" : "已補償刪除").isEqualTo(failure.keeps() ? 1 : 0);
            if (failure.keeps()) {
                assertThat(resp.<Boolean>read("$.details.outcomeUnknown")).as("%s：outcomeUnknown", failure.label()).isTrue();
                resetSystemConfigs();
                MINI.si.writeReply = null;
                Resp status = api.get(viewer(), REGISTRY);
                assertThat(status.<String>read("$.data.state")).as("%s：保留列使狀態為 pending", failure.label()).isEqualTo("pending");
            } else {
                assertThat(resp.has("$.details.outcomeUnknown")).as("%s：確定未落檔，沒有 outcomeUnknown", failure.label()).isFalse();
            }
        }
        resetRow();
        try (AbruptCloseServer abrupt = AbruptCloseServer.start()) {
            MINI.si.onRead = path -> {
                if ("/si/events".equals(path)) {
                    setting("sdd", "engineUrl", abrupt.url());
                }
            };
            Resp reset = sync(admin());
            assertThat(reset.status()).as("送出後連線重設").isEqualTo(502);
            assertThat(reset.<Boolean>read("$.details.outcomeUnknown")).isTrue();
            assertThat(writeCount()).as("結果不明：保留").isEqualTo(1);
        } finally {
            resetSystemConfigs();
        }
    }

    // ── AT-965-6-5 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_6_5_theOuterFileSizeIsMeasuredFromTheSignedBytesNotEstimated() {
        refs.refs(ref("a1", 1));
        String evil = "\"\n".repeat(11_000);
        assertThat(evil.getBytes(StandardCharsets.UTF_8).length).as("registry_text 本身遠低於 24576").isLessThan(24_576);
        snapshot(evil, SHA_D);
        Counts before = counts();

        Resp big = sync(admin());

        assertThat(big.status()).isEqualTo(422);
        assertThat(big.<String>read("$.reason")).isEqualTo("registry_too_large");
        assertThat(big.<String>read("$.details.what")).isEqualTo("audit_file");
        assertThat(big.<Integer>read("$.details.limit")).isEqualTo(65536);
        assertThat(big.<Integer>read("$.details.size")).isGreaterThan(65536);
        Counts after = counts();
        assertThat(after.refsTaken()).as("尚未取 ref").isEqualTo(before.refsTaken()).isZero();
        assertThat(after.rows()).isZero();
        assertThat(after.writes()).isZero();

        snapshot(APPENDIX_B, APPENDIX_B_SHA);
        assertThat(sync(admin()).status()).as("典型內容（外層檔≤65536）").isEqualTo(201);
    }

    // ── AT-965-6-8 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_6_8_secretsNeverLeakIntoResponsesLogsRowsOrErrorDetails() {
        Logger root = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        root.addAppender(appender);
        try {
            List<String> haystack = new ArrayList<>();
            refs.refs(ref("a1", 1), ref("a1", 2));
            snapshot(APPENDIX_B, APPENDIX_B_SHA);
            haystack.add(sync(admin()).body());
            haystack.add(sync(operator()).body());
            MINI.research.always("registry", Reply.error(503, "research_requires_db"));
            haystack.add(sync(admin()).body());
            MINI.research.reset();
            MINI.si.writeReply = WriteReply.error(503, "si_write_disabled", "detail", "BRIDGE_SI_AUDIT_DIR 未設");
            snapshot("{}\n", SHA_F);
            haystack.add(sync(admin()).body());
            MINI.si.writeReply = null;
            haystack.add(String.valueOf(writeRows()));
            appender.list.forEach(event -> haystack.add(event.getFormattedMessage()));
            String all = String.join("\n", haystack);
            assertThat(all).as("金鑰值不出現在回應、錯誤 details、日誌與列").doesNotContain(SiWriteSeam.K0);
            assertThat(all).as("寫入權杖值不出現").doesNotContain(SiWriteSeam.T0);
            assertThat(MINI.si.writes.get(0).token()).as("迷你 Bridge 收到的標頭 X-Bridge-Token 為正確值").isEqualTo(SiWriteSeam.T0);
            assertThat(appender.list.stream().map(ILoggingEvent::getFormattedMessage)).anySatisfy(
                    m -> assertThat(m).contains("kind=src-registry").contains("auditRef=").contains("keyId="));
        } finally {
            root.detachAppender(appender);
        }
    }
}
