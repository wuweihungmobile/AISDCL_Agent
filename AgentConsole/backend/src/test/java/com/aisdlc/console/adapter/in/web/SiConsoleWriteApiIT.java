package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbruptCloseServer;
import com.aisdlc.console.support.AbstractSiWriteIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SiWriteSeam;
import com.aisdlc.minibridge.MiniBridge.Si.WriteReply;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SelfImproving 寫入載體的 backend 面（TCS-SelfImprovingDecide-P2b：AT-933-1-4、933-2-1、935-1-3、935-1-E-3、935-2-3、935-2-E-2、935-3-E-1、
 * 935-4-1、935-4-E-1、935-4-E-2、950-5-E-2、950-6-3、950-6-E-1、950-6-E-2、950-6-E-3），對<b>真的 HTTP</b> 迷你 Bridge 與真 PostgreSQL 驗每一列。
 * 為什麼重要：這條路徑把「掌舵者的決定」變成會被主機端 CLI 驗簽入帳的位元組——簽章與落檔的位元組若有一個不同（黃金檔鎖住）、
 * 授權閘門序若錯（名單外的人得到 422 而不是 403，等於替他驗證了表單）、補償若錯（確定未落檔卻留列＝幽靈待入帳；結果不明卻刪列＝帳本多出
 * Console 看不見的 orphan），Console 的稽核就會對帳不起來。
 */
class SiConsoleWriteApiIT extends AbstractSiWriteIT {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    private static JsonNode outer(int index) {
        return JSON.readTree(receivedText(index));
    }

    private static List<String> violationFields(Resp resp) {
        return resp.read("$.details.violations[*].field");
    }

    private static List<String> allPaths() {
        return List.of("/proposals/" + PROP + "/decide", "/observations", "/observations/" + OBS + "/close", "/observations/validate");
    }

    private Object validBodyFor(String path) {
        if (path.endsWith("/decide")) {
            return approve();
        }
        return path.endsWith("/close") ? closeDecided() : observation();
    }

    // ── AT-933-1-4：九個 dkind 端對端，Bridge 本文位元組等於黃金檔 ─────────────────────────────────────

    @Test
    void AT_933_1_4_nineVerbsGet201AndTheBridgeReceivesTheGoldenBytesForApproveAndReject() {
        refs.refs(ref("a1", 1), ref("a1", 2), ref("b2", 3), ref("b2", 4), ref("b2", 5), ref("b2", 6), ref("b2", 7), ref("b2", 8),
                ref("b2", 9));
        int index = 0;
        for (Map.Entry<String, Map<String, Object>> verb : allDecides().entrySet()) {
            String dkind = verb.getKey();
            String id = idFor(dkind);

            Resp resp = post(admin(), "/proposals/" + id + "/decide", verb.getValue());

            assertThat(resp.status()).as(dkind).isEqualTo(201);
            assertThat(MINI.si.writes).as("%s：Bridge 恰收到一個 POST", dkind).hasSize(index + 1);
            assertThat(MINI.si.writes.get(index).path()).isEqualTo("/si/proposals/" + id + ":decide");
            assertThat(MINI.si.writes.get(index).token()).as("附 X-Bridge-Token（SelfImproving 寫入權杖）").isEqualTo(SiWriteSeam.T0);
            JsonNode outer = outer(index);
            assertThat(outer.get("kind").asString()).isEqualTo("decide");
            assertThat(outer.get("subject").asString()).as("%s 的外層 subject 等於路徑 id", dkind).isEqualTo(id);
            JsonNode body = JSON.readTree(outer.get("body").asString());
            assertThat(body.get("dkind").asString()).isEqualTo(dkind);
            assertThat(body.has(index == 7 ? "run" : "prop")).as("%s 的 body 綁 prop 或 run", dkind).isTrue();
            assertThat(body.get("time").asString()).isEqualTo(SiWriteSeam.FIXED_TIME);
            assertThat(body.get("user").asString()).isEqualTo("admin");
            assertThat(body.get("role").asString()).isEqualTo("ADMIN");
            index++;
        }

        assertThat(receivedBytes(0)).as("approve＝黃金檔 G1").isEqualTo(golden("decide-approve.json"));
        assertThat(receivedBytes(1)).as("reject＝黃金檔 G2").isEqualTo(golden("decide-reject.json"));
        assertThat(MINI.requests()).as("每個請求恰一個 Bridge POST").hasSize(9).allSatisfy(r -> assertThat(r).startsWith("POST /si/proposals/"));
        assertThat(writeCount()).isEqualTo(9);
    }

    // ── AT-933-2-1：DB 同型列，列在 Bridge 呼叫前已存在 ─────────────────────────────────────────────

    @Test
    void AT_933_2_1_theAuditRowExistsBeforeTheBridgeIsCalledAndEveryColumnMatchesTheSignedBody() {
        refs.refs(ref("a1", 1));
        AtomicReference<List<Map<String, Object>>> atRequestTime = new AtomicReference<>();
        MINI.si.onWrite = write -> atRequestTime.set(writeRows());

        Resp resp = post(admin(), "/proposals/" + PROP + "/decide", approve());

        assertThat(resp.status()).isEqualTo(201);
        assertThat(atRequestTime.get()).as("MiniBridge 收到請求的當下，表內已有該 audit_ref 一列").hasSize(1);
        assertThat(atRequestTime.get().get(0)).containsEntry("audit_ref", ref("a1", 1));
        List<Map<String, Object>> rows = writeRows();
        assertThat(rows).as("成功後列仍在、表內恰一列").hasSize(1);
        JsonNode outer = outer(0);
        Map<String, Object> row = rows.get(0);
        assertThat(row).containsEntry("audit_ref", ref("a1", 1)).containsEntry("kind", "decide").containsEntry("user", "admin")
                .containsEntry("role", "ADMIN").containsEntry("subject_id", PROP).containsEntry("digest", D0)
                .containsEntry("time_utc", "2026-10-24T14:30:15Z");
        assertThat(row.get("body")).as("body 等於外層的 body 字串（簽章的對象）").isEqualTo(outer.get("body").asString());
        assertThat(row.get("key_id").toString().strip()).isEqualTo(outer.get("key_id").asString());
        assertThat(row.get("mac").toString().strip()).isEqualTo(outer.get("mac").asString());
        assertThat(JSON.readTree(row.get("body").toString()).get("time").asString()).as("time 與 body.time 同刻")
                .isEqualTo(SiWriteSeam.FIXED_TIME);
    }

    // ── AT-935-1-3：obs-add 端對端；validate 零副作用 ───────────────────────────────────────────────

    @Test
    void AT_935_1_3_obsAddEndToEndMatchesGoldenG3AndG4AndValidateHasNoSideEffects() {
        refs.refs(ref("a1", 3), ref("a1", 4));
        Map<String, Object> correcting = new LinkedHashMap<>(observation());
        correcting.put("corrects", "OBS-SI-001");

        Resp g3 = post(admin(), "/observations", observation());
        Resp g4 = post(admin(), "/observations", correcting);

        assertThat(g3.status()).isEqualTo(201);
        assertThat(g4.status()).isEqualTo(201);
        assertThat(receivedBytes(0)).as("G3").isEqualTo(golden("obs-add.json"));
        assertThat(receivedBytes(1)).as("G4（含 corrects）").isEqualTo(golden("obs-add-corrects.json"));
        assertThat(writeRows()).hasSize(2).allSatisfy(row -> {
            assertThat(row).containsEntry("kind", "obs-add");
            assertThat(row.get("subject_id")).as("obs-add 入帳前沒有新列號").isNull();
            assertThat(row.get("digest")).isNull();
        });
        int takenBefore = refs.taken();

        Resp validate = post(admin(), "/observations/validate", observation());

        assertThat(validate.status()).isEqualTo(200);
        assertThat(writeCount()).as("預檢不寫 DB").isEqualTo(2);
        assertThat(refs.taken()).as("預檢不取 audit_ref").isEqualTo(takenBefore);
        assertThat(MINI.si.writes).hasSize(3);
        assertThat(MINI.si.writes.get(2).path()).isEqualTo("/si/observations:validate");
        assertThat(MINI.si.writes.get(2).token()).as("預檢不帶權杖").isNull();
        assertThat(MINI.si.writes.get(2).text()).as("Bridge 收到的是未簽 body").doesNotContain("\"mac\"").doesNotContain("key_id")
                .doesNotContain("audit_ref").startsWith("{\"schema_rev\":1,\"kind\":\"obs-add\",\"user\":\"admin\"");
    }

    // ── AT-935-1-E-3：obs-add 與 validate 的違規一律 422、零副作用 ──────────────────────────────────

    private static Map<String, Object> obsWith(String key, Object value) {
        Map<String, Object> body = new LinkedHashMap<>(observation());
        if (value == null) {
            body.remove(key);
        } else {
            body.put(key, value);
        }
        return body;
    }

    @Test
    void AT_935_1_E_3_observationViolationsAre422WithoutAnySideEffectAndTheBoundaryControlsAre201() {
        Map<String, Map<String, Object>> bad = new LinkedHashMap<>();
        bad.put("context", obsWith("context", "含|豎線"));
        bad.put("symptom", obsWith("symptom", "含\n換行"));
        Map<String, Object> guardNoExposure = new LinkedHashMap<>(observation());
        guardNoExposure.put("face", "守衛");
        bad.put("exposure", guardNoExposure);
        Map<String, Object> sum701 = new LinkedHashMap<>(observation());
        sum701.put("context", "a".repeat(300));
        sum701.put("symptom", "b".repeat(300));
        sum701.put("evidence", "c".repeat(101));
        bad.put("evidence", sum701);

        for (Map.Entry<String, Map<String, Object>> entry : bad.entrySet()) {
            for (String path : List.of("/observations", "/observations/validate")) {
                Resp resp = post(admin(), path, entry.getValue());

                assertThat(resp.status()).as("%s %s", path, entry.getKey()).isEqualTo(422);
                assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
                assertThat(violationFields(resp)).as("%s %s", path, entry.getKey()).contains(entry.getKey());
                assertThat(resp.<List<String>>read("$.errors[*].field")).as("errors[] 與 details.violations 同內容").contains(entry.getKey());
            }
        }
        assertThat(writeCount()).as("DB 零列").isZero();
        assertThat(MINI.requests()).as("Bridge 零請求").isEmpty();
        assertThat(refs.taken()).as("audit_ref 來源零次取用").isZero();

        refs.refs(ref("b3", 1), ref("b3", 2));
        Map<String, Object> exactly700 = new LinkedHashMap<>(observation());
        exactly700.put("context", "a".repeat(300));
        exactly700.put("symptom", "b".repeat(300));
        exactly700.put("evidence", "c".repeat(100));
        Map<String, Object> single300 = new LinkedHashMap<>(observation());
        single300.put("context", "x".repeat(300));
        assertThat(post(admin(), "/observations", exactly700).status()).as("位元組和恰 700").isEqualTo(201);
        assertThat(post(admin(), "/observations", single300).status()).as("單欄恰 300 字元").isEqualTo(201);
    }

    // ── AT-935-2-3：close 端對端，終值組成 disposition ───────────────────────────────────────────────

    @Test
    void AT_935_2_3_closeEndToEndMatchesGoldenG5AndTheSevenTerminalsComposeTheirDisposition() {
        refs.refs(ref("a1", 5));
        Resp g5 = post(admin(), "/observations/" + OBS + "/close", closeDecided());

        assertThat(g5.status()).isEqualTo(201);
        assertThat(receivedBytes(0)).as("G5").isEqualTo(golden("obs-close.json"));

        Map<String, Map<String, Object>> terminals = new LinkedHashMap<>();
        terminals.put("fixed@2b2b0b3d", map("terminal", "fixed", "ref", "2b2b0b3d"));
        terminals.put("DEF-200-559", map("terminal", "def", "ref", "DEF-200-559"));
        terminals.put("deferred：等 P3 輪", map("terminal", "deferred", "text", "等 P3 輪"));
        terminals.put("retired：docs/06_quality/SelfImproving_Protocol/params.json",
                map("terminal", "retired", "text", "docs/06_quality/SelfImproving_Protocol/params.json"));
        terminals.put("decided：夾具關閉", map("terminal", "decided", "text", "夾具關閉"));
        terminals.put("merged@OBS-SI-001", map("terminal", "merged", "ref", "OBS-SI-001"));
        terminals.put("proposed@PROP-SI-004", map("terminal", "proposed", "ref", "PROP-SI-004"));
        for (int i = 1; i <= 7; i++) {
            refs.refs(ref("b4", i));
        }
        int index = 1;
        for (Map.Entry<String, Map<String, Object>> terminal : terminals.entrySet()) {
            Resp resp = post(admin(), "/observations/" + OBS + "/close", terminal.getValue());

            assertThat(resp.status()).as(terminal.getKey()).isEqualTo(201);
            assertThat(JSON.readTree(outer(index).get("body").asString()).get("disposition").asString()).isEqualTo(terminal.getKey());
            assertThat(outer(index).get("subject").asString()).isEqualTo(OBS);
            index++;
        }
        assertThat(writeRows()).hasSize(8).allSatisfy(row -> {
            assertThat(row).containsEntry("kind", "obs-close").containsEntry("subject_id", OBS);
            assertThat(row.get("digest")).isNull();
        });
    }

    // ── AT-935-2-E-2：close 違規一律 422，零副作用 ─────────────────────────────────────────────────

    @Test
    void AT_935_2_E_2_closeViolationsAre422WithoutAnySideEffect() {
        record Bad(String label, String id, Map<String, Object> body, String field) {
        }
        List<Bad> samples = List.of(
                new Bad("open", OBS, map("terminal", "open"), "terminal"),
                new Bad("decided 缺 text", OBS, map("terminal", "decided"), "text"),
                new Bad("fixed 的 ref 非十六進位", OBS, map("terminal", "fixed", "ref", "zzzzzzzz"), "ref"),
                new Bad("text 含之後再看", OBS, map("terminal", "deferred", "text", "之後再看"), "text"),
                new Bad("路徑 id 格式不合", "OBS-SI-" + "05", map("terminal", "fixed", "ref", "2b2b0b3d"), "id"));

        for (Bad bad : samples) {
            Resp resp = post(admin(), "/observations/" + bad.id() + "/close", bad.body());

            assertThat(resp.status()).as(bad.label()).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
            assertThat(violationFields(resp)).as(bad.label()).contains(bad.field());
        }
        assertThat(writeCount()).isZero();
        assertThat(MINI.requests()).isEmpty();
        assertThat(refs.taken()).isZero();
    }

    // ── AT-935-3-E-1：DELETE、PUT、PATCH 矩陣 ───────────────────────────────────────────────────────

    @Test
    void AT_935_3_E_1_deletePutAndPatchAreForbiddenForViewerAnd405ForOperatorAndAdminWithoutTouchingBridgeOrDb() {
        List<String> paths = List.of("/proposals/" + PROP + "/decide", "/observations", "/observations/" + OBS + "/close",
                "/observations/validate", "/status", "/console-writes");
        Map<String, Integer> expected = new LinkedHashMap<>();
        expected.put("viewer", 403);
        expected.put("operator", 405);
        expected.put("admin", 405);
        Map<String, String> tokens = Map.of("viewer", viewer(), "operator", operator(), "admin", admin());
        int checked = 0;
        for (Map.Entry<String, Integer> role : expected.entrySet()) {
            for (String path : paths) {
                String url = SI + path;
                List<MockHttpServletRequestBuilder> requests = List.of(MockMvcRequestBuilders.delete(url),
                        MockMvcRequestBuilders.put(url).contentType("application/json").content("{}"),
                        MockMvcRequestBuilders.patch(url).contentType("application/json").content("{}"));
                for (MockHttpServletRequestBuilder request : requests) {
                    Resp resp = api.send(tokens.get(role.getKey()), request);

                    assertThat(resp.status()).as("%s %s", role.getKey(), path).isEqualTo(role.getValue());
                    checked++;
                }
            }
        }
        assertThat(checked).isEqualTo(54);
        assertThat(MINI.requests()).as("Bridge 零請求").isEmpty();
        assertThat(writeCount()).as("si_console_writes 零列").isZero();
    }

    // ── AT-935-4-1：資格通過矩陣 ─────────────────────────────────────────────────────────────────────

    @Test
    void AT_935_4_1_adminsOnTheListPassAllFourPostsAndTheMatchIsCaseSensitive() {
        for (int i = 1; i <= 6; i++) {
            refs.refs(ref("b2", i));
        }
        for (String account : List.of("admin", "ops_admin")) {
            String token = account.equals("admin") ? admin() : adminAs(account);

            assertThat(post(token, "/observations/validate", observation()).status()).as("%s validate", account).isEqualTo(200);
            assertThat(post(token, "/proposals/" + PROP + "/decide", approve()).status()).as("%s decide", account).isEqualTo(201);
            assertThat(post(token, "/observations", observation()).status()).as("%s obs-add", account).isEqualTo(201);
            assertThat(post(token, "/observations/" + OBS + "/close", closeDecided()).status()).as("%s close", account).isEqualTo(201);
        }
        assertThat(writeRows()).extracting(row -> row.get("user")).containsOnly("admin", "ops_admin");

        Resp capitalised = post(adminAs("Admin"), "/proposals/" + PROP + "/decide", approve());

        assertThat(capitalised.status()).as("名單只含小寫 admin：Admin 不在名單內").isEqualTo(403);
        assertThat(capitalised.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_FORBIDDEN);
        assertThat(writeCount()).as("被拒的請求不留列").isEqualTo(6);
    }

    // ── AT-935-4-E-1：資格拒收矩陣 ───────────────────────────────────────────────────────────────────

    @Test
    void AT_935_4_E_1_everyIneligibleCallerIsRefusedWithoutTouchingTheBridgeOrTheDatabase() {
        for (String path : allPaths()) {
            Object body = validBodyFor(path);

            assertThat(post(null, path, body).status()).as("無 token %s", path).isEqualTo(401);
            assertThat(post("garbage", path, body).status()).as("亂碼 token %s", path).isEqualTo(401);
            Resp viewer = post(viewer(), path, body);
            assertThat(viewer.status()).as("Viewer %s", path).isEqualTo(403);
            assertThat(viewer.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
            Resp operator = post(operator(), path, body);
            assertThat(operator.status()).as("Operator %s", path).isEqualTo(403);
            assertThat(operator.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
            Resp outsider = post(adminAs("outsider"), path, body);
            assertThat(outsider.status()).as("名單外的 Admin %s", path).isEqualTo(403);
            assertThat(outsider.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_FORBIDDEN);
        }
        settings.noDeciders();
        for (String path : allPaths()) {
            Resp resp = post(admin(), path, validBodyFor(path));

            assertThat(resp.status()).as("名單為空後的 admin %s", path).isEqualTo(403);
            assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_FORBIDDEN);
        }
        assertThat(MINI.requests()).as("Bridge 零請求").isEmpty();
        assertThat(writeCount()).as("DB 零列").isZero();
        assertThat(refs.taken()).isZero();
    }

    // ── AT-935-4-E-2：閘門序 ─────────────────────────────────────────────────────────────────────────

    @Test
    void AT_935_4_E_2_authorizationComesFirstThenDisabledThenInputAndTheAccountNameIsCheckedSeparately() {
        Map<String, Object> invalid = map("dkind", "approve", "digest", D0, "reason", "多餘的理由");
        String decide = "/proposals/" + PROP + "/decide";

        Resp outsider = post(adminAs("outsider"), decide, invalid);
        assertThat(outsider.status()).as("名單外：先 403、不是 422").isEqualTo(403);
        assertThat(outsider.<String>read("$.reason")).isEqualTo("si_write_forbidden");

        settings.noKey();
        Resp noKey = post(admin(), decide, invalid);
        assertThat(noKey.status()).isEqualTo(503);
        assertThat(noKey.<String>read("$.reason")).isEqualTo("si_write_disabled");
        assertThat(noKey.<String>read("$.details.cause")).isEqualTo("audit_key_unset");
        settings.reset();

        settings.noToken();
        Resp noToken = post(admin(), decide, invalid);
        assertThat(noToken.status()).isEqualTo(503);
        assertThat(noToken.<String>read("$.reason")).isEqualTo("si_write_disabled");
        assertThat(noToken.<String>read("$.details.cause")).isEqualTo("bridge_token_unset");
        settings.reset();

        // W10 的第三、四關次序（突變自證補強：交換「名單」與「停用」兩關時，上面五例仍全綠）：名單外的人在寫入面停用時仍得 403、不得借 503 探知設定
        settings.noKey();
        Resp outsiderNoKey = post(adminAs("outsider"), decide, invalid);
        assertThat(outsiderNoKey.status()).as("名單外＋金鑰未設：授權先於停用，仍是 403").isEqualTo(403);
        assertThat(outsiderNoKey.<String>read("$.reason")).isEqualTo("si_write_forbidden");
        settings.reset();

        settings.noToken();
        Resp outsiderNoToken = post(adminAs("outsider"), decide, invalid);
        assertThat(outsiderNoToken.status()).as("名單外＋權杖未設：授權先於停用，仍是 403").isEqualTo(403);
        assertThat(outsiderNoToken.<String>read("$.reason")).isEqualTo("si_write_forbidden");
        settings.reset();

        settings.deciders("bad name");
        Resp badName = post(adminAs("bad name"), decide, approve());
        assertThat(badName.status()).as("帳號名含空白：值域另判").isEqualTo(422);
        assertThat(violationFields(badName)).contains("user");
        settings.reset();

        Resp withReason = post(admin(), decide, invalid);
        Resp missingClass = post(admin(), "/proposals/" + PROP + "/decide", map("dkind", "reject", "digest", D0, "reason", "理由"));
        assertThat(withReason.status()).as("設定齊全：本文違規得 422").isEqualTo(422);
        assertThat(withReason.<String>read("$.reason")).isEqualTo("invalid_request");
        assertThat(violationFields(withReason)).contains("reason");
        assertThat(missingClass.status()).isEqualTo(422);
        assertThat(violationFields(missingClass)).contains("reasonClass");

        assertThat(writeCount()).as("五例全程 DB 零列").isZero();
        assertThat(MINI.requests()).as("Bridge 零請求").isEmpty();
        assertThat(refs.taken()).as("SiAuditRefSource 零次取用").isZero();
    }

    // ── AT-950-5-E-2：機密不外洩 ──────────────────────────────────────────────────────────────────────

    private static void assertNoSubstringOf(String secret, String label, List<String> texts) {
        for (int i = 0; i + 8 <= secret.length(); i++) {
            String piece = secret.substring(i, i + 8);
            for (String text : texts) {
                assertThat(text).as("%s 不得含祕密的 8 字元子字串（位置 %d）", label, i).doesNotContain(piece);
            }
        }
    }

    @Test
    void AT_950_5_E_2_neitherTheSigningKeyNorTheBridgeTokenAppearsInResponsesLogsOrTheDatabase() {
        Logger root = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        root.addAppender(appender);
        List<String> texts = new ArrayList<>();
        try {
            refs.refs(ref("b2", 1), ref("b2", 2), ref("b2", 3), ref("b2", 4));
            readTimeout.cap(Duration.ofSeconds(1));
            texts.addAll(capture(post(admin(), "/proposals/" + PROP + "/decide", approve())));          // 成功寫入

            MINI.si.writeReply = WriteReply.error(403, "si_write_forbidden");
            texts.addAll(capture(post(admin(), "/proposals/" + PROP + "/decide", approve())));          // Bridge 403

            MINI.si.writeReply = WriteReply.error(503, "si_unavailable", "cause", "audit_write_failed", "detail", "errno=28; OSError");
            texts.addAll(capture(post(admin(), "/proposals/" + PROP + "/decide", approve())));          // Bridge 503

            MINI.si.writeReply = null;
            MINI.si.writeDelayMillis = 3_000;
            texts.addAll(capture(post(admin(), "/proposals/" + PROP + "/decide", approve())));          // 逾時
        } finally {
            root.detachAppender(appender);
        }
        assertThat(MINI.si.writes).as("權杖只出現在送往 MiniBridge 的 X-Bridge-Token 標頭").hasSize(4)
                .allSatisfy(write -> assertThat(write.token()).isEqualTo(SiWriteSeam.T0));
        for (ILoggingEvent event : appender.list) {
            texts.add(event.getFormattedMessage() + " " + event.getLoggerName());
            if (event.getThrowableProxy() != null) {
                texts.add(event.getThrowableProxy().getMessage() == null ? "" : event.getThrowableProxy().getMessage());
            }
        }
        for (Map<String, Object> row : jdbc.queryForList("select * from console.si_console_writes")) {
            texts.add(row.toString());
        }
        for (Map<String, Object> row : jdbc.queryForList("select * from console.audit_log")) {
            texts.add(row.toString());
        }

        assertThat(appender.list).as("防反空轉：日誌確實擷取到了這四次請求的輸出").isNotEmpty();
        assertNoSubstringOf(SiWriteSeam.K0, "簽章金鑰", texts);
        assertNoSubstringOf(SiWriteSeam.T0, "Bridge 權杖", texts);
    }

    private static List<String> capture(Resp resp) {
        List<String> parts = new ArrayList<>();
        parts.add(resp.body());
        resp.headers().forEach((name, value) -> parts.add(name + ": " + value));
        return parts;
    }

    // ── AT-950-6-3：回應形態 ──────────────────────────────────────────────────────────────────────────

    @Test
    void AT_950_6_3_receiptsHaveExactlyFiveCamelCaseKeysAndTheValidationMirrorsTheBridgeObject() {
        refs.refs(ref("a1", 1), ref("a1", 3), ref("a1", 5));
        MINI.si.validateReply = map("ok", false, "row", "", "row_bytes", 0, "row_max_bytes", 700, "findings",
                List.of(map("code", "FIELD-EMPTY", "detail", "欄「情境」為空"), map("code", "COORD-NONE", "detail", "證據座標不合")));

        Resp decide = post(admin(), "/proposals/" + PROP + "/decide", approve());
        Resp add = post(admin(), "/observations", observation());
        Resp close = post(admin(), "/observations/" + OBS + "/close", closeDecided());
        Resp validate = post(admin(), "/observations/validate", observation());

        for (Resp resp : List.of(decide, add, close)) {
            assertThat(resp.status()).isEqualTo(201);
            assertThat(resp.<Integer>read("$.code")).isEqualTo(201);
            assertThat(resp.data().keySet()).containsExactlyInAnyOrder("auditRef", "kind", "subject", "time", "keyId");
            assertThat(resp.<String>read("$.data.time")).isEqualTo(SiWriteSeam.FIXED_TIME);
            assertThat(resp.<String>read("$.data.keyId")).isEqualTo("f076edf0");
            assertThat(resp.body()).as("不含 body 與 mac").doesNotContain("\"body\"").doesNotContain("\"mac\"");
        }
        assertThat(decide.<String>read("$.data.kind")).isEqualTo("decide");
        assertThat(decide.<String>read("$.data.subject")).isEqualTo(PROP);
        assertThat(decide.<String>read("$.data.auditRef")).isEqualTo(ref("a1", 1));
        assertThat(add.<String>read("$.data.kind")).isEqualTo("obs-add");
        assertThat(add.data()).as("obs-add 的 subject 為 null（鍵仍在）").containsEntry("subject", null);
        assertThat(close.<String>read("$.data.subject")).isEqualTo(OBS);

        assertThat(validate.status()).as("ok=false 仍是 200").isEqualTo(200);
        assertThat(validate.data().keySet()).containsExactlyInAnyOrder("ok", "row", "rowBytes", "rowMaxBytes", "findings");
        assertThat(validate.<Boolean>read("$.data.ok")).isFalse();
        assertThat(validate.<Integer>read("$.data.rowMaxBytes")).isEqualTo(700);
        assertThat(validate.<List<Map<String, Object>>>read("$.data.findings")).hasSize(2).first()
                .satisfies(f -> assertThat(f).containsOnlyKeys("code", "detail").containsEntry("code", "FIELD-EMPTY")
                        .containsEntry("detail", "欄「情境」為空"));
        assertThat(validate.body()).doesNotContain("\"mac\"").doesNotContain("\"body\"");
    }

    // ── AT-950-6-E-1：補償矩陣 ────────────────────────────────────────────────────────────────────────

    @Test
    void AT_950_6_E_1_explicitRejectionsAndServerErrorsDeleteTheRowAndForwardTheReasonVerbatim() {
        record Case(String label, WriteReply reply, int status, String reason) {
        }
        List<Case> cases = List.of(
                new Case("403", WriteReply.error(403, "si_write_forbidden"), 403, "si_write_forbidden"),
                new Case("409", WriteReply.error(409, "si_audit_exists"), 409, "si_audit_exists"),
                new Case("503 disabled", WriteReply.error(503, "si_write_disabled", "detail", "BRIDGE_SI_AUDIT_DIR 未設"), 503, "si_write_disabled"),
                new Case("503 unavailable", WriteReply.error(503, "si_unavailable", "cause", "audit_write_failed", "detail",
                        "errno=28; OSError"), 503, "si_unavailable"),
                new Case("422", WriteReply.error(422, "invalid_request", "violations", List.of(map("field", "subject", "rule", "mismatch",
                        "message", "與路徑不符"))), 422, ErrorReasons.BRIDGE_REJECTED),
                new Case("500", WriteReply.error(500, "internal_error"), 502, ErrorReasons.BRIDGE_ERROR));
        for (int i = 1; i <= cases.size(); i++) {
            refs.refs(ref("b2", i));
        }
        int sent = 0;
        for (Case c : cases) {
            MINI.si.writeReply = c.reply();

            Resp resp = post(admin(), "/proposals/" + PROP + "/decide", approve());

            assertThat(resp.status()).as(c.label()).isEqualTo(c.status());
            assertThat(resp.<String>read("$.reason")).as(c.label()).isEqualTo(c.reason());
            assertThat(writeCount()).as("%s：補償後表內零列", c.label()).isZero();
            assertThat(MINI.si.writes).as("%s：每次 Bridge 恰一個請求", c.label()).hasSize(++sent);
            assertThat(resp.has("$.details.outcomeUnknown")).as("%s：確定未落檔，沒有 outcomeUnknown", c.label()).isFalse();
            switch (c.label()) {
                case "503 disabled" -> assertThat(resp.<String>read("$.details.detail")).isEqualTo("BRIDGE_SI_AUDIT_DIR 未設");
                case "503 unavailable" -> {
                    assertThat(resp.<String>read("$.details.cause")).isEqualTo("audit_write_failed");
                    assertThat(resp.<String>read("$.details.detail")).isEqualTo("errno=28; OSError");
                }
                case "422" -> {
                    assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("invalid_request");
                    assertThat(resp.<List<Map<String, Object>>>read("$.details.violations")).singleElement()
                            .satisfies(v -> assertThat(v).containsEntry("field", "subject"));
                }
                default -> {
                    // 其餘列只驗狀態、reason 與補償
                }
            }
        }
    }

    // ── AT-950-6-E-2：結果不明保留列，確定未送達刪列 ──────────────────────────────────────────────────

    @Test
    void AT_950_6_E_2_anUnknownOutcomeKeepsTheRowAndTellsSoWhileACertainNonDeliveryDeletesIt() {
        for (int i = 1; i <= 4; i++) {
            refs.refs(ref("b3", i));
        }
        // ① 讀取逾時（縮短到 1 秒，Bridge 延遲 3 秒）
        readTimeout.cap(Duration.ofSeconds(1));
        MINI.si.writeDelayMillis = 3_000;
        Resp timedOut = post(admin(), "/observations", observation());
        MINI.si.writeDelayMillis = 0;
        readTimeout.reset();
        assertThat(timedOut.status()).isEqualTo(504);
        assertThat(timedOut.<Boolean>read("$.details.outcomeUnknown")).isTrue();
        assertThat(writeRows()).as("逾時：保留恰一列（該 audit_ref）").hasSize(1).first().satisfies(row -> assertThat(row).containsEntry("audit_ref", ref("b3", 1)));

        // ② 收到請求後直接關連線
        try (AbruptCloseServer abrupt = AbruptCloseServer.start()) {
            setting("sdd", "engineUrl", abrupt.url());
            Resp reset = post(admin(), "/observations", observation());
            assertThat(abrupt.requests()).as("請求確實送達了假伺服器").isEqualTo(1);
            assertThat(reset.status()).isEqualTo(502);
            assertThat(reset.<Boolean>read("$.details.outcomeUnknown")).isTrue();
        }
        resetSystemConfigs();
        thresholds.invalidate();
        assertThat(writeCount()).as("送出後連線被重設：再保留一列").isEqualTo(2);

        // ③ 201 加非 JSON 本文
        MINI.si.writeReply = new WriteReply(201, "created, trust me");
        Resp garbage = post(admin(), "/observations", observation());
        MINI.si.writeReply = null;
        assertThat(garbage.status()).isEqualTo(502);
        assertThat(garbage.<Boolean>read("$.details.outcomeUnknown")).isTrue();
        assertThat(writeCount()).as("2xx 本文無法解析：再保留一列").isEqualTo(3);

        // ④ 連線被拒（確定未送達）
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp refused = post(admin(), "/observations", observation());
        resetSystemConfigs();
        thresholds.invalidate();
        assertThat(refused.status()).isEqualTo(502);
        assertThat(refused.has("$.details.outcomeUnknown")).as("確定未送達：沒有 outcomeUnknown").isFalse();
        assertThat(writeCount()).as("連線被拒：該列已補償刪除，仍是 3 列").isEqualTo(3);
        assertThat(writeRows()).extracting(row -> row.get("audit_ref")).containsExactlyInAnyOrder(ref("b3", 1), ref("b3", 2), ref("b3", 3));

        // 之後的對帳面：三列都顯示待入帳（ingested 為 false）
        Resp reconcile = api.get(viewer(), SI + "/console-writes");
        assertThat(reconcile.status()).isEqualTo(200);
        assertThat(reconcile.<List<Boolean>>read("$.data.items[*].ingested")).containsExactly(false, false, false);
    }

    // ── AT-950-6-E-3：不重試、每次新 audit_ref ────────────────────────────────────────────────────────

    @Test
    void AT_950_6_E_3_aResendGetsANewAuditRefAndNothingIsRetriedAutomatically() {
        refs.refs(ref("b3", 1), ref("b3", 2));
        MINI.si.writeReply = WriteReply.error(503, "si_unavailable", "cause", "nonzero_rc", "detail", "rc=3");

        Resp first = post(admin(), "/observations", observation());

        assertThat(first.status()).isEqualTo(503);
        assertThat(writeCount()).as("第一次：補償後零列").isZero();
        MINI.si.writeReply = null;

        Resp second = post(admin(), "/observations", observation());

        assertThat(second.status()).isEqualTo(201);
        assertThat(MINI.si.writes).as("請求總數為 2：沒有自動重試").hasSize(2);
        String firstRef = outer(0).get("audit_ref").asString();
        String secondRef = outer(1).get("audit_ref").asString();
        assertThat(firstRef).isNotEqualTo(secondRef);
        assertThat(writeRows()).hasSize(1).first().satisfies(row -> assertThat(row).containsEntry("audit_ref", secondRef));
    }
}
