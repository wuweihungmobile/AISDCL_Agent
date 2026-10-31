package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.port.out.SiConsoleWriteRepository;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbruptCloseServer;
import com.aisdlc.console.support.AbstractSiWriteIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SiWriteSeam;
import com.aisdlc.minibridge.MiniBridge.Si.WriteReply;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
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
            // 兩個帳號送不同動詞：重送閘不看帳號（TCS-SelfImprovingDecideDedupe 已知邊界 4），同一決定由第二個帳號再送會被 409 擋下；
            // 這裡驗的仍是「名單內的 Admin 皆放行」，所以讓兩邊各下一個不同的決定
            Map<String, Object> decision = account.equals("admin") ? approve() : reject();

            assertThat(post(token, "/observations/validate", observation()).status()).as("%s validate", account).isEqualTo(200);
            assertThat(post(token, "/proposals/" + PROP + "/decide", decision).status()).as("%s decide", account).isEqualTo(201);
            assertThat(post(token, "/observations", observation()).status()).as("%s obs-add", account).isEqualTo(201);
            assertThat(post(token, "/observations/" + OBS + "/close", closeDecided()).status()).as("%s close", account).isEqualTo(201);
        }
        assertThat(writeRows()).extracting(row -> row.get("user")).containsOnly("admin", "ops_admin");

        Resp otherAccount = post(adminAs("ops_admin"), "/proposals/" + PROP + "/decide", approve());

        assertThat(otherAccount.status()).as("閘不看帳號：admin 已送過的 approve，ops_admin 再送同一決定也被擋（表 M-G 情境 9）").isEqualTo(409);
        assertThat(otherAccount.<String>read("$.reason")).as("線上 reason 字面（不比常數自己）").isEqualTo("si_decision_duplicate")
                .isEqualTo(ErrorReasons.SI_DECISION_DUPLICATE);
        assertThat(writeCount()).as("被擋的重送不留列").isEqualTo(6);

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
            // 四次各用不同的動詞：同一決定的重送會被重送閘（409）擋在 Bridge 之前（TCS-SelfImprovingDecideDedupe §4 第 3 項），
            // 而這個 AT 要四種結果（成功、Bridge 403、Bridge 503、逾時）都真的走到 Bridge
            Map<String, Map<String, Object>> verbs = allDecides();
            String decide = "/proposals/" + PROP + "/decide";
            texts.addAll(capture(post(admin(), decide, verbs.get("approve"))));                         // 成功寫入

            MINI.si.writeReply = WriteReply.error(403, "si_write_forbidden");
            texts.addAll(capture(post(admin(), decide, verbs.get("reject"))));                          // Bridge 403

            MINI.si.writeReply = WriteReply.error(503, "si_unavailable", "cause", "audit_write_failed", "detail", "errno=28; OSError");
            texts.addAll(capture(post(admin(), decide, verbs.get("return"))));                          // Bridge 503

            MINI.si.writeReply = null;
            MINI.si.writeDelayMillis = 3_000;
            texts.addAll(capture(post(admin(), decide, verbs.get("promote"))));                         // 逾時
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

    // ══ 決定重送閘與 dkind（TCS-SelfImprovingDecideDedupe：AT-951-1-1、1-2、1-E-1～1-E-4、2-E-1；W-D1、W-D2）══════════════════════════════════
    // 為什麼重要：OBS-SI-348——同一張卡的同一決定被連送四次，落四份稽核檔，主機端只能入帳一份，其餘三份在對帳面板永遠顯示待入帳。閘擋錯方向的代價不對稱：
    // 該擋的沒擋＝誤導再現；不該擋的擋了＝掌舵者的合法決定（入帳前改變主意、同一 RUN 再度暫停後的第二次恢復）被封死。所以逐項驗：擋什麼（六個帶 digest 的動詞）、
    // 不擋什麼（不同 dkind、digest、subject、無 digest 的動詞、obs-add、obs-close、validate）、排在哪裡（授權與輸入閘之後）、擋下時的零副作用，以及與補償、結果不明的互動。

    private static final String DECIDE = "/proposals/" + PROP + "/decide";

    @Autowired
    private SiConsoleWriteRepository writeRepository;

    // ── AT-951-1-1：六個帶 digest 的動詞重送皆 409，details 恰四鍵，零副作用 ─────────────────────────────

    @Test
    void AT_951_1_1_aResendOfEachOfTheSixDigestVerbsGets409WithExactlyFourDetailKeysAndNoSideEffect() {
        List<String> verbs = List.of("approve", "reject", "return", "promote", "decline-promote", "ack-handoff");
        for (int i = 1; i <= verbs.size(); i++) {
            refs.refs(ref("d1", i));
        }
        Map<String, Map<String, Object>> decides = allDecides();
        Map<String, String> firstReceipts = new LinkedHashMap<>();
        for (String dkind : verbs) {
            Resp first = post(admin(), DECIDE, decides.get(dkind));

            assertThat(first.status()).as("%s 首次", dkind).isEqualTo(201);
            firstReceipts.put(dkind, first.<String>read("$.data.auditRef"));
        }
        List<Map<String, Object>> rowsBefore = writeRows();
        assertThat(rowsBefore).as("六個動詞各落一列").hasSize(6);
        int bridgeWritesBefore = MINI.si.writes.size();
        List<String> bridgeRequestsBefore = MINI.requests();
        int takenBefore = refs.taken();

        for (String dkind : verbs) {
            Map<String, Object> resend = new LinkedHashMap<>(decides.get(dkind));
            if (resend.containsKey("reason")) {
                resend.put("reason", "重送時改過的理由：" + dkind);   // 理由不同也擋：閘只看 subject＋digest＋dkind
            }
            if (resend.containsKey("reasonClass")) {
                resend.put("reasonClass", "未說明");
            }

            Resp resp = post(admin(), DECIDE, resend);

            assertThat(resp.status()).as("%s 重送", dkind).isEqualTo(409);
            assertThat(resp.<String>read("$.reason")).as("%s：線上 reason 字面（不比常數自己）", dkind).isEqualTo("si_decision_duplicate")
                    .isEqualTo(ErrorReasons.SI_DECISION_DUPLICATE);
            assertThat(resp.<String>read("$.details.existingAuditRef")).as("%s：existingAuditRef 為首次收據的 auditRef", dkind)
                    .isEqualTo(firstReceipts.get(dkind));
            Map<String, Object> details = resp.read("$.details");
            assertThat(details.keySet()).as("%s：details 恰四鍵", dkind).containsExactlyInAnyOrder("existingAuditRef", "dkind", "subject", "digest8");
            assertThat(details).as(dkind).containsEntry("digest8", "d21ae6f5").containsEntry("dkind", dkind).containsEntry("subject", PROP);
            assertThat(resp.<String>read("$.message")).as(dkind).contains("請以對帳面板為準");
        }

        assertThat(writeRows()).as("重送後六列逐位元組不變").isEqualTo(rowsBefore);
        assertThat(MINI.si.writes).as("Bridge 的寫入請求筆數不變").hasSize(bridgeWritesBefore);
        assertThat(MINI.requests()).as("Bridge 的請求（含 GET）完全不變").isEqualTo(bridgeRequestsBefore);
        assertThat(refs.taken()).as("ref 來源取用次數不變").isEqualTo(takenBefore);
    }

    // ── AT-951-1-2：不論先前那一列是否已入帳都擋，且重送閘不呼叫 Bridge ───────────────────────────────

    @Test
    void AT_951_1_2_theGateRejectsWhetherOrNotThePriorRowIsIngestedAndNeverCallsTheBridge() {
        refs.refs(ref("d1", 1), ref("d1", 2));
        Resp first = post(admin(), DECIDE, approve());
        assertThat(first.status()).isEqualTo(201);
        String r1 = first.<String>read("$.data.auditRef");
        MINI.si.payloads.put("events", export("events", List.of(event(7, "dec", "console", r1, "prop", PROP)), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));
        Resp reconcile = api.get(viewer(), SI + "/console-writes");
        assertThat(reconcile.<Boolean>read("$.data.items[0].ingested")).as("情境前提：R1 已入帳（帳本有同 auditRef 的 dec）").isTrue();
        List<String> bridgeRequestsBefore = MINI.requests();
        int bridgeWritesBefore = MINI.si.writes.size();
        int takenBefore = refs.taken();
        List<Map<String, Object>> rowsBefore = writeRows();

        Resp resend = post(admin(), DECIDE, approve());

        assertThat(resend.status()).isEqualTo(409);
        assertThat(resend.<String>read("$.reason")).as("線上 reason 字面（不比常數自己）").isEqualTo("si_decision_duplicate")
                .isEqualTo(ErrorReasons.SI_DECISION_DUPLICATE);
        assertThat(resend.<String>read("$.details.existingAuditRef")).isEqualTo(r1);
        assertThat(writeRows()).as("表內仍恰一列").hasSize(1).isEqualTo(rowsBefore);
        assertThat(MINI.requests()).as("重送前後沒有任何 GET events、GET observations 或 POST").isEqualTo(bridgeRequestsBefore);
        assertThat(MINI.si.writes).hasSize(bridgeWritesBefore);
        assertThat(refs.taken()).isEqualTo(takenBefore);

        // 一審 F-02：existingAuditRef 是「time 最早、同刻 audit_ref 小寫字串序最小」的那一列——不是最後一列，也不是 UUID.compareTo 的最小者。
        // 上面單一列的情境分不出「取第一個」與「取最後一個」，所以另植同一決定的多列（表內清空後各植一次；插入次序故意與期望次序相反）
        String t09 = "2026-10-31T09:00:00Z";
        String t10 = "2026-10-31T10:00:00Z";
        String x1 = ref("d1", 11);
        jdbc.execute("TRUNCATE console.si_console_writes");
        insertDecide(UT2, PROP, D0, "approve", t10);
        insertDecide(x1, PROP, D0, "approve", t09);
        insertDecide(UT1, PROP, D0, "approve", t10);
        assertResendRejectedPointingAt("子情境一（三列：X1 時間最早、X2＝UT1 與 X3＝UT2 同刻且晚於 X1）", x1);

        jdbc.execute("TRUNCATE console.si_console_writes");
        insertDecide(UT2, PROP, D0, "approve", t10);
        insertDecide(UT1, PROP, D0, "approve", t10);
        assertResendRejectedPointingAt("子情境二（只有同刻的 UT1、UT2 兩列：取小寫 UUID 字串序較小者，不是 UUID.compareTo 的順序）", UT1);
    }

    /** 表內已植好同一決定（approve、{@code PROP}、{@code D0}）的列時再送一次：409、{@code existingAuditRef} 為期望的那一列，且零副作用（列、Bridge 請求、ref 取用都不變）。 */
    private void assertResendRejectedPointingAt(String scenario, String expectedExistingAuditRef) {
        List<String> bridgeRequestsBefore = MINI.requests();
        int bridgeWritesBefore = MINI.si.writes.size();
        int takenBefore = refs.taken();
        List<Map<String, Object>> rowsBefore = writeRows();

        Resp resend = post(admin(), DECIDE, approve());

        assertThat(resend.status()).as("%s：重送", scenario).isEqualTo(409);
        assertThat(resend.<String>read("$.reason")).as("%s：線上 reason 字面", scenario).isEqualTo("si_decision_duplicate");
        assertThat(resend.<String>read("$.details.existingAuditRef")).as("%s：existingAuditRef", scenario).isEqualTo(expectedExistingAuditRef);
        assertThat(writeRows()).as("%s：表內列數與內容不變", scenario).isEqualTo(rowsBefore);
        assertThat(MINI.requests()).as("%s：Bridge 零新增請求", scenario).isEqualTo(bridgeRequestsBefore);
        assertThat(MINI.si.writes).as("%s：Bridge 寫入筆數不變", scenario).hasSize(bridgeWritesBefore);
        assertThat(refs.taken()).as("%s：ref 取用次數不變", scenario).isEqualTo(takenBefore);
    }

    // ── AT-951-1-E-1：不該被擋的請求照常受理 ────────────────────────────────────────────────────────────

    @Test
    void AT_951_1_E_1_requestsThatAreNotTheSameDecisionAreAcceptedAsUsual() {
        for (int i = 1; i <= 8; i++) {
            refs.refs(ref("d1", i));
        }
        assertThat(post(admin(), DECIDE, approve()).status()).as("起手的 approve").isEqualTo(201);

        assertThat(post(admin(), DECIDE, reject()).status()).as("(a) 同 subject、同 digest、不同 dkind").isEqualTo(201);
        assertThat(post(admin(), DECIDE, map("dkind", "approve", "digest", D1)).status()).as("(b) 同 subject、同 dkind、不同 digest").isEqualTo(201);
        assertThat(post(admin(), "/proposals/" + PROP5 + "/decide", approve()).status()).as("(c) 不同 subject").isEqualTo(201);
        assertThat(post(admin(), "/observations", observation()).status()).as("(d) obs-add 第一次").isEqualTo(201);
        assertThat(post(admin(), "/observations", observation()).status()).as("(d) obs-add 同本文第二次").isEqualTo(201);
        assertThat(post(admin(), "/observations/" + OBS + "/close", closeDecided()).status()).as("(e) obs-close 第一次").isEqualTo(201);
        assertThat(post(admin(), "/observations/" + OBS + "/close", closeDecided()).status()).as("(e) obs-close 同本文第二次").isEqualTo(201);

        assertThat(writeCount()).as("表內列數為 8（含起手的 approve）").isEqualTo(8);
        assertThat(MINI.si.writes).as("到這裡 Bridge 恰收到 8 個寫入（預檢另計）").hasSize(8);
        assertThat(post(admin(), "/observations/validate", observation()).status()).as("(f) validate 第一次").isEqualTo(200);
        assertThat(post(admin(), "/observations/validate", observation()).status()).as("(f) validate 第二次").isEqualTo(200);
        assertThat(writeCount()).as("預檢不寫表").isEqualTo(8);
        assertThat(MINI.si.writes).as("預檢也記在迷你 Bridge 的 writes，故總數為 10").hasSize(10);
    }

    // ── AT-951-1-E-2：補償刪列後可重送；結果不明而保留的列擋住重送（已知邊界）─────────────────────────────

    @Test
    void AT_951_1_E_2_aCompensatedRowDoesNotBlockAResendButARowKeptForAnUnknownOutcomeDoes() {
        for (int i = 1; i <= 3; i++) {
            refs.refs(ref("d1", i));
        }
        MINI.si.writeReply = WriteReply.error(503, "si_unavailable", "cause", "audit_write_failed", "detail", "errno=28; OSError");
        Resp refused = post(admin(), DECIDE, approve());
        MINI.si.writeReply = null;
        assertThat(refused.status()).as("Bridge 確定未落檔").isEqualTo(503);
        assertThat(writeCount()).as("補償刪列：表內零列").isZero();

        Resp again = post(admin(), DECIDE, approve());

        assertThat(again.status()).as("補償後重送同一個 approve").isEqualTo(201);
        assertThat(writeRows()).as("表內恰一列，且為第二次取的 ref").hasSize(1).first()
                .satisfies(row -> assertThat(row).containsEntry("audit_ref", ref("d1", 2)));

        readTimeout.cap(Duration.ofSeconds(1));
        MINI.si.writeDelayMillis = 3_000;
        Resp timedOut = post(admin(), DECIDE, promote());
        MINI.si.writeDelayMillis = 0;
        readTimeout.reset();
        assertThat(timedOut.status()).as("讀取逾時").isEqualTo(504);
        assertThat(timedOut.<Boolean>read("$.details.outcomeUnknown")).isTrue();
        assertThat(writeCount()).as("promote 的列因結果不明而保留：表內共二列").isEqualTo(2);
        int bridgeWritesBefore = MINI.si.writes.size();
        int takenBefore = refs.taken();

        Resp resend = post(admin(), DECIDE, promote());

        assertThat(resend.status()).as("結果不明而保留的列擋住重送（已知邊界 1）").isEqualTo(409);
        assertThat(resend.<String>read("$.reason")).as("線上 reason 字面（不比常數自己）").isEqualTo("si_decision_duplicate")
                .isEqualTo(ErrorReasons.SI_DECISION_DUPLICATE);
        assertThat(resend.<String>read("$.details.existingAuditRef")).isEqualTo(ref("d1", 3));
        assertThat(writeCount()).isEqualTo(2);
        assertThat(MINI.si.writes).as("重送前後 Bridge 的寫入筆數相同").hasSize(bridgeWritesBefore);
        assertThat(refs.taken()).isEqualTo(takenBefore);
    }

    private static Map<String, Object> promote() {
        return allDecides().get("promote");
    }

    // ── AT-951-1-E-3：重送閘排在授權、停用與輸入閘之後 ──────────────────────────────────────────────────

    @Test
    void AT_951_1_E_3_theGateComesAfterAuthorizationTheDisabledCheckAndTheInputGate() {
        refs.refs(ref("d1", 1));
        assertThat(post(admin(), DECIDE, approve()).status()).as("起手的 approve").isEqualTo(201);
        int takenBefore = refs.taken();
        long rowsBefore = writeCount();

        Resp outsider = post(adminAs("outsider"), DECIDE, approve());
        Resp viewer = post(viewer(), DECIDE, approve());
        Resp operator = post(operator(), DECIDE, approve());
        Resp anonymous = post(null, DECIDE, approve());
        settings.noKey();
        Resp noKey = post(admin(), DECIDE, approve());
        settings.reset();
        settings.noToken();
        Resp noToken = post(admin(), DECIDE, approve());
        settings.reset();
        Resp withReason = post(admin(), DECIDE, map("dkind", "approve", "digest", D0, "reason", "多餘的理由"));

        assertThat(outsider.status()).as("(a) 名單外的 Admin").isEqualTo(403);
        assertThat(outsider.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_FORBIDDEN);
        assertThat(viewer.status()).as("(b) Viewer").isEqualTo(403);
        assertThat(viewer.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
        assertThat(operator.status()).as("(c) Operator").isEqualTo(403);
        assertThat(operator.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
        assertThat(anonymous.status()).as("(d) 無 token").isEqualTo(401);
        assertThat(noKey.status()).as("(e) 金鑰環為空").isEqualTo(503);
        assertThat(noKey.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_DISABLED);
        assertThat(noKey.<String>read("$.details.cause")).isEqualTo("audit_key_unset");
        assertThat(noToken.status()).as("(f) Bridge 權杖為空").isEqualTo(503);
        assertThat(noToken.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_DISABLED);
        assertThat(noToken.<String>read("$.details.cause")).isEqualTo("bridge_token_unset");
        assertThat(withReason.status()).as("(g) 本文違規：輸入閘先於重送閘").isEqualTo(422);
        assertThat(withReason.<String>read("$.reason")).isEqualTo("invalid_request");
        assertThat(violationFields(withReason)).contains("reason");
        for (Resp resp : List.of(outsider, viewer, operator, anonymous, noKey, noToken, withReason)) {
            assertThat(resp.status()).as("全程沒有 409").isNotEqualTo(409);
        }
        assertThat(writeCount()).as("表內列數不變").isEqualTo(rowsBefore);
        assertThat(refs.taken()).as("ref 取用次數不變").isEqualTo(takenBefore);
    }

    // ── AT-951-1-E-4：無 digest 的動詞不受重送閘 ────────────────────────────────────────────────────────

    @Test
    void AT_951_1_E_4_verbsWithoutADigestAreNotGatedSoResumeRollbackAndUnblockMayBeSentTwice() {
        for (int i = 1; i <= 6; i++) {
            refs.refs(ref("d1", i));
        }
        Map<String, Map<String, Object>> decides = allDecides();
        String resume = "/proposals/" + RUN + "/decide";
        Map<String, String> auditRefs = new LinkedHashMap<>();

        Resp resume1 = post(admin(), resume, decides.get("resume"));
        Resp resume2 = post(admin(), resume, map("dkind", "resume", "reason", "同一 RUN 再度暫停後的第二次恢復"));
        Resp rollback1 = post(admin(), DECIDE, decides.get("rollback"));
        Resp rollback2 = post(admin(), DECIDE, decides.get("rollback"));
        Resp unblock1 = post(admin(), DECIDE, decides.get("unblock"));
        Resp unblock2 = post(admin(), DECIDE, decides.get("unblock"));

        Map<String, Resp> all = new LinkedHashMap<>();
        all.put("(a) resume 第一次", resume1);
        all.put("(a) resume 第二次（理由不同）", resume2);
        all.put("(b) rollback 第一次", rollback1);
        all.put("(b) rollback 第二次", rollback2);
        all.put("(c) unblock 第一次", unblock1);
        all.put("(c) unblock 第二次", unblock2);
        all.forEach((label, resp) -> {
            assertThat(resp.status()).as(label).isEqualTo(201);
            auditRefs.put(label, resp.<String>read("$.data.auditRef"));
        });
        assertThat(writeCount()).as("表內列數為 6").isEqualTo(6);
        assertThat(MINI.si.writes).as("每次都落檔：Bridge 恰 6 筆").hasSize(6);
        assertThat(refs.taken()).as("每次都取新 ref").isEqualTo(6);
        assertThat(auditRefs.values()).as("每個請求的 auditRef 都不同（含兩次 resume）").doesNotHaveDuplicates();
        assertThat(resume1.<String>read("$.data.auditRef")).isNotEqualTo(resume2.<String>read("$.data.auditRef"));
    }

    // ── AT-951-2-E-1：findDecideAuditRefs 的查詢語意 ────────────────────────────────────────────────────

    @Test
    void AT_951_2_E_1_findDecideAuditRefsOrdersByTimeThenByStringOrderAndMatchesOnlyTheExactDecision() {
        String x1 = ref("d2", 1);
        String t09 = "2026-10-31T09:00:00Z";
        String t10 = "2026-10-31T10:00:00Z";
        // 插入次序故意是 X3、X1、X2：回傳順序不得取決於插入次序
        insertDecide(UT2, PROP, D0, "promote", t10);
        insertDecide(x1, PROP, D0, "promote", t09);
        insertDecide(UT1, PROP, D0, "promote", t10);
        // 干擾列：同 subject 與 digest 但不同 dkind／不同 digest／不同 subject／非 decide 列（body 含 dkind 也不算）／沒有 digest 的 rollback
        insertDecide(ref("d2", 11), PROP, D0, "approve", t09);
        insertDecide(ref("d2", 12), PROP, D1, "promote", t09);
        insertDecide(ref("d2", 13), PROP5, D0, "promote", t09);
        insertAudit(ref("d2", 14), "obs-add", PROP, D0, "{\"dkind\":\"promote\"}", t09);
        insertDecide(ref("d2", 21), PROP, null, "rollback", t09);
        insertDecide(ref("d2", 22), PROP, null, "rollback", t10);

        List<String> promotes = toText(writeRepository.findDecideAuditRefs(PROP, D0, "promote"));
        List<String> rollbacks = toText(writeRepository.findDecideAuditRefs(PROP, null, "rollback"));
        List<String> rejects = toText(writeRepository.findDecideAuditRefs(PROP, D0, "reject"));
        List<String> upper = toText(writeRepository.findDecideAuditRefs(PROP, D0, "PROMOTE"));

        assertThat(promotes).as("(a) 依 time 升冪；同刻依小寫 UUID 字串序（UT1 在前、UT2 在後，不是 UUID.compareTo 的順序）")
                .containsExactly(x1, UT1, UT2);
        assertThat(rollbacks).as("(b) digest 為 null 一律不命中（即使表內有 digest 為 null 的 rollback 列）").isEmpty();
        assertThat(rejects).as("(c) dkind 不同").isEmpty();
        assertThat(upper).as("(d) dkind 區分大小寫").isEmpty();
        assertThat(writeRepository.findDecideAuditRefs(PROP, D0, null)).as("dkind 為 null 回空清單").isEmpty();
        assertThat(writeRepository.findDecideAuditRefs(null, D0, "promote")).as("subject 為 null 回空清單").isEmpty();
    }

    private static List<String> toText(List<UUID> refs) {
        return refs.stream().map(UUID::toString).toList();
    }

    // ── AT-951-2-1：九個動詞經 API 寫入後，對帳讀面的 dkind 逐一相符 ───────────────────────────────────

    @Test
    void AT_951_2_1_afterTheNineVerbsAreWrittenEveryDecideItemCarriesItsDkindAndTheOtherKindsCarryNull() {
        for (int i = 1; i <= 11; i++) {
            refs.refs(ref("d3", i));
        }
        MINI.si.payloads.put("events", export("events", List.of(), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));
        Map<String, String> dkindByRef = new LinkedHashMap<>();
        for (Map.Entry<String, Map<String, Object>> verb : allDecides().entrySet()) {
            Resp resp = post(admin(), "/proposals/" + idFor(verb.getKey()) + "/decide", verb.getValue());

            assertThat(resp.status()).as(verb.getKey()).isEqualTo(201);
            dkindByRef.put(resp.<String>read("$.data.auditRef"), verb.getKey());
        }
        Resp add = post(admin(), "/observations", observation());
        Resp close = post(admin(), "/observations/" + OBS + "/close", closeDecided());
        assertThat(add.status()).isEqualTo(201);
        assertThat(close.status()).isEqualTo(201);

        Resp resp = api.get(viewer(), SI + "/console-writes");

        assertThat(resp.status()).isEqualTo(200);
        List<Map<String, Object>> items = resp.read("$.data.items");
        assertThat(items).as("九個決定加一個 obs-add 與一個 obs-close").hasSize(11);
        List<String> digestVerbs = List.of("approve", "reject", "return", "promote", "decline-promote", "ack-handoff");
        for (Map<String, Object> item : items) {
            String auditRef = (String) item.get("auditRef");
            if ("decide".equals(item.get("kind"))) {
                String dkind = dkindByRef.get(auditRef);
                assertThat(item.get("dkind")).as("decide 項 %s 的 dkind 等於寫入的動詞", auditRef).isEqualTo(dkind);
                assertThat(item.get("digest")).as("%s 的 digest", dkind).isEqualTo(digestVerbs.contains(dkind) ? D0 : null);
            } else {
                assertThat(item).as("非 decide 項 %s：dkind 鍵仍在、值為 null", auditRef).containsEntry("dkind", null);
            }
        }
        assertThat(items.stream().filter(item -> "decide".equals(item.get("kind"))).map(item -> (String) item.get("dkind")).toList())
                .as("九個動詞一個不漏").containsExactlyInAnyOrderElementsOf(allDecides().keySet());
        assertThat(resp.body()).as("body 與 mac 兩個鍵不出現在回應任何位置").doesNotContain("\"body\"").doesNotContain("\"mac\"");
    }

    // ── AT-951-2-E-2：看不出 dkind 的列與非 decide 列一律為 null ─────────────────────────────────────────

    @Test
    void AT_951_2_E_2_rowsWithoutADkindAndRowsThatAreNotDecideAreNullAndNeitherBreaksTheReadNorFoolsTheGate() {
        String w1 = ref("d4", 1);
        String w2 = ref("d4", 2);
        String w3 = ref("d4", 3);
        String w4 = ref("d4", 4);
        insertWrite(w1, "decide", PROP, D0, "2026-10-31T09:01:00Z");                      // body 只有 fixture 鍵、沒有 dkind
        insertAudit(w2, "obs-add", null, null, "{\"dkind\":\"approve\"}", "2026-10-31T09:02:00Z");   // 非 decide：body 含 dkind 也不取
        insertWrite(w3, "obs-close", OBS, null, "2026-10-31T09:03:00Z");
        insertDecide(w4, PROP, D0, "approve", "2026-10-31T09:04:00Z");
        MINI.si.payloads.put("events", export("events", List.of(), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));

        Resp resp = api.get(viewer(), SI + "/console-writes");
        List<UUID> gate = writeRepository.findDecideAuditRefs(PROP, D0, "approve");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.reconcile.status")).isEqualTo("ok");
        List<Map<String, Object>> items = resp.read("$.data.items");
        assertThat(items).as("四列皆在 items").hasSize(4);
        Map<String, Object> dkinds = new LinkedHashMap<>();
        items.forEach(item -> dkinds.put((String) item.get("auditRef"), item.get("dkind")));
        assertThat(dkinds.get(w1)).as("W1：沒有 dkind 鍵的 decide 列").isNull();
        assertThat(dkinds.get(w2)).as("W2：kind 非 decide，不因 body 含 dkind 就取值").isNull();
        assertThat(dkinds.get(w3)).as("W3：obs-close").isNull();
        assertThat(dkinds.get(w4)).as("W4：有 dkind 的 decide 列").isEqualTo("approve");
        assertThat(dkinds).as("四列的 dkind 鍵都在").containsKeys(w1, w2, w3, w4);
        assertThat(toText(gate)).as("重送閘只認 W4：W1 沒有 dkind，不會被誤認為同一決定").containsExactly(w4);
        assertThat(resp.body()).doesNotContain("\"body\"").doesNotContain("\"mac\"");
    }
}
