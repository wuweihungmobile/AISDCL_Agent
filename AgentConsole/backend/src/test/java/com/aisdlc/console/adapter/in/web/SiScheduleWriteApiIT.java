package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractSiWriteIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SiWriteSeam;
import com.aisdlc.minibridge.MiniBridge;
import com.aisdlc.minibridge.MiniBridge.Si.WriteReply;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpMethod;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SelfImproving P4 排程控制載體的 backend 面（TCS-SelfImprovingSchedule：AT-964-7-1～7-5、7-E-1～7-E-5；W-S7），對<b>真的 HTTP</b> 迷你 Bridge 與真 PostgreSQL 驗每一列。
 * 為什麼重要：這兩個端點把「掌舵者要改排程、要立即跑一次」變成會被主機端 CLI 驗簽入帳的位元組——body 鍵序錯一個字，入帳就是 AUDIT-MAC-MISMATCH；
 * 取界那一關若在取不到界時放行，會簽出週期超界、CLI 才拒收的稽核檔（accept-then-reject）；若新 kind 誤走決定的重送閘，連點「立即啟動」會被 409 擋下，
 * 與「不設重送閘、防連點只靠前端軟停用」的決策（D-CS-5）相反。所以逐項驗：閘門序、零副作用、界每次現取、補償與結果不明、位元組等於黃金檔。
 */
class SiScheduleWriteApiIT extends AbstractSiWriteIT {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String SET = "/schedule/set";
    private static final String RUN = "/runs/request";
    /** TCS §5.1 的界夾具：預期值一律由這些常數導出，不在斷言中另寫一份（NFR-SC-4）。 */
    private static final int LO = 60;
    private static final int HI = 10080;
    private static final int LO2 = 30;
    private static final int HI2 = 120;
    private static final int DEFAULT_PERIOD = 1440;

    private static void bounds(int lo, int hi) {
        MINI.si.status(MiniBridge.Si.scheduleWithBounds(lo, hi));
    }

    private static Map<String, Object> schedBody(Object enabled, Object period, String reason) {
        Map<String, Object> body = new LinkedHashMap<>();
        if (enabled != null) {
            body.put("enabled", enabled);
        }
        if (period != null) {
            body.put("periodMinutes", period);
        }
        if (reason != null) {
            body.put("reason", reason);
        }
        return body;
    }

    private static JsonNode outer(int index) {
        return JSON.readTree(receivedText(index));
    }

    private static List<String> keysOf(JsonNode node) {
        List<String> keys = new ArrayList<>();
        for (Iterator<String> it = node.propertyNames().iterator(); it.hasNext();) {
            keys.add(it.next());
        }
        return keys;
    }

    private static List<String> violationFields(Resp resp) {
        return resp.read("$.details.violations[*].field");
    }

    private static String hmacHex(String key, String message) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return HexFormat.of().formatHex(mac.doFinal(message.getBytes(StandardCharsets.UTF_8)));
    }

    /** 零副作用的斷言：表內列數、Bridge 收到的稽核請求數、ref 來源取用次數、取界的 GET status 次數（NFR-SC-3）。 */
    private void assertNoSideEffects(String label, long rows, int writes, int refsTaken, long statusRequests) {
        assertThat(writeCount()).as("%s：表內列數", label).isEqualTo(rows);
        assertThat(MINI.si.writes).as("%s：Bridge 收到的稽核請求數", label).hasSize(writes);
        assertThat(refs.taken()).as("%s：ref 來源取用次數", label).isEqualTo(refsTaken);
        assertThat(MINI.si.statusRequests()).as("%s：GET status 次數", label).isEqualTo(statusRequests);
    }

    // ── AT-964-7-1：sched-set 的 201、收據、表內新列、Bridge 收到的外層與 body 鍵序與簽章 ──────────────────────

    @Test
    void AT_964_7_1_aScheduleSetGets201AndTheBridgeReceivesTheGoldenBytesWithTheSpecificKeysAfterTheCommonOnes() throws Exception {
        bounds(LO, HI);
        refs.refs(ref("a1", 6));
        Logger root = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        root.addAppender(appender);
        Resp resp;
        try {
            resp = post(admin(), SET, schedBody(true, 120, "夾具啟用"));
        } finally {
            root.detachAppender(appender);
        }

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.data().keySet()).as("收據鍵集合恰五個").containsExactlyInAnyOrder("auditRef", "kind", "subject", "time", "keyId");
        assertThat(resp.<String>read("$.data.kind")).isEqualTo("sched-set");
        assertThat(resp.data()).containsEntry("subject", null);
        assertThat(resp.<String>read("$.data.time")).isEqualTo(SiWriteSeam.FIXED_TIME).matches("\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d[+-]\\d\\d:\\d\\d")
                .doesNotContain("Z");
        assertThat(resp.<String>read("$.data.auditRef")).isEqualTo(ref("a1", 6));
        assertThat(resp.body()).as("不含 body 與 mac").doesNotContain("\"body\"").doesNotContain("\"mac\"");
        assertThat(writeRows()).as("表內恰新增一列").hasSize(1).first().satisfies(row -> assertThat(row).containsEntry("kind", "sched-set")
                .containsEntry("user", "admin").containsEntry("role", "ADMIN").containsEntry("subject_id", null).containsEntry("digest", null));
        assertThat(MINI.si.writes).hasSize(1);
        assertThat(MINI.si.writes.get(0).path()).isEqualTo("/si/schedule:set");
        assertThat(MINI.si.writes.get(0).token()).isEqualTo(SiWriteSeam.T0);
        JsonNode outer = outer(0);
        assertThat(keysOf(outer)).as("外層恰七鍵").containsExactly("schema_rev", "kind", "audit_ref", "subject", "body", "key_id", "mac");
        assertThat(outer.get("subject").isNull()).isTrue();
        String body = outer.get("body").asString();
        assertThat(keysOf(JSON.readTree(body))).as("body 鍵序：共通鍵之後依書寫序接專屬鍵")
                .containsExactly("schema_rev", "audit_ref", "kind", "user", "role", "time", "enabled", "period_minutes", "reason");
        assertThat(JSON.readTree(body).get("enabled").asBoolean()).isTrue();
        assertThat(JSON.readTree(body).get("period_minutes").asInt()).isEqualTo(120);
        assertThat(outer.get("mac").asString()).as("以測試金鑰重算 HMAC 等於外層 mac").isEqualTo(hmacHex(SiWriteSeam.K0, body));
        assertThat(receivedBytes(0)).as("位元組等於黃金檔 G6").isEqualTo(golden("sched-set-enable.json"));
        List<String> texts = new ArrayList<>(List.of(resp.body(), receivedText(0)));
        appender.list.forEach(event -> texts.add(event.getFormattedMessage()));
        assertThat(appender.list).as("防反空轉：日誌確實擷取到了這次請求的輸出").isNotEmpty();
        for (String text : texts) {
            assertThat(text).as("回應、日誌與 Bridge 本文不含金鑰與權杖值").doesNotContain(SiWriteSeam.K0).doesNotContain(SiWriteSeam.T0);
        }
    }

    // ── AT-964-7-2：run-request 的 201，空物件與含備註；不取界 ───────────────────────────────────────────────

    @Test
    void AT_964_7_2_aRunRequestGets201WithAnEmptyObjectAndWithANoteAndNeverAsksTheBridgeForBounds() {
        refs.refs(ref("a1", 9), ref("a1", 8));

        Resp empty = post(admin(), RUN, Map.of());
        Resp noted = post(admin(), RUN, map("note", "夾具立即啟動"));

        for (Resp resp : List.of(empty, noted)) {
            assertThat(resp.status()).isEqualTo(201);
            assertThat(resp.<String>read("$.data.kind")).isEqualTo("run-request");
            assertThat(resp.data()).containsEntry("subject", null);
            assertThat(resp.data().keySet()).containsExactlyInAnyOrder("auditRef", "kind", "subject", "time", "keyId");
        }
        assertThat(writeRows()).hasSize(2).allSatisfy(row -> assertThat(row).containsEntry("kind", "run-request")
                .containsEntry("subject_id", null).containsEntry("digest", null));
        assertThat(MINI.si.writes.get(0).path()).isEqualTo("/si/runs:request");
        assertThat(keysOf(JSON.readTree(outer(0).get("body").asString()))).as("沒有 note 鍵")
                .containsExactly("schema_rev", "audit_ref", "kind", "user", "role", "time");
        assertThat(keysOf(JSON.readTree(outer(1).get("body").asString()))).as("共通鍵之後接 note")
                .containsExactly("schema_rev", "audit_ref", "kind", "user", "role", "time", "note");
        assertThat(receivedBytes(0)).as("空物件＝黃金檔 G9").isEqualTo(golden("run-request.json"));
        assertThat(receivedBytes(1)).as("含備註＝黃金檔 G8").isEqualTo(golden("run-request-note.json"));
        assertThat(MINI.si.statusRequests()).as("run-request 沒有序 5′：GET status 請求數為 0").isZero();
    }

    // ── AT-964-7-3：停用方向帶界內週期仍 201，且同樣經過序 5′ ─────────────────────────────────────────────────

    @Test
    void AT_964_7_3_disablingStillCarriesAnInBoundsPeriodAndGoesThroughTheBoundsCheck() {
        bounds(LO, HI);
        refs.refs(ref("a1", 7));

        Resp resp = post(admin(), SET, schedBody(false, DEFAULT_PERIOD, null));

        assertThat(resp.status()).isEqualTo(201);
        JsonNode body = JSON.readTree(outer(0).get("body").asString());
        assertThat(body.get("enabled").asBoolean()).isFalse();
        assertThat(body.get("period_minutes").asInt()).isEqualTo(DEFAULT_PERIOD);
        assertThat(keysOf(body)).as("沒有 reason 鍵").containsExactly("schema_rev", "audit_ref", "kind", "user", "role", "time", "enabled",
                "period_minutes");
        assertThat(receivedBytes(0)).as("＝黃金檔 G7").isEqualTo(golden("sched-set-disable.json"));
        assertThat(MINI.si.statusRequests()).as("停用方向同樣經序 5′").isEqualTo(1);
    }

    // ── AT-964-7-4：序 5′ 的界檢查：端點、端點外、訊息取自當下的界、界改變後隨之改變 ──────────────────────────────

    @Test
    void AT_964_7_4_thePeriodBoundsAreReadFromTheCurrentStatusEveryTimeAndOutOfBoundsIs422WithTheCurrentNumbers() {
        refs.refs(ref("b4", 1), ref("b4", 2), ref("b4", 3), ref("b4", 4));
        bounds(LO, HI);

        assertThat(post(admin(), SET, schedBody(true, LO, null)).status()).as("下界端點").isEqualTo(201);
        assertThat(post(admin(), SET, schedBody(true, HI, null)).status()).as("上界端點").isEqualTo(201);
        long rows = writeCount();
        for (int outside : new int[] {LO - 1, HI + 1}) {
            Resp resp = post(admin(), SET, schedBody(true, outside, null));

            assertThat(resp.status()).as("界外 %d", outside).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
            assertThat(violationFields(resp)).containsExactly("periodMinutes");
            assertThat(resp.<List<String>>read("$.details.violations[*].message")).singleElement()
                    .satisfies(message -> assertThat(message).contains(String.valueOf(LO)).contains(String.valueOf(HI)));
        }
        assertNoSideEffects("界外的請求", rows, 2, 2, 4);

        bounds(LO2, HI2);
        assertThat(post(admin(), SET, schedBody(true, 100, null)).status()).as("新界內").isEqualTo(201);
        Resp outside = post(admin(), SET, schedBody(true, HI2 + 1, null));
        assertThat(outside.status()).as("新界外：舊界內的值").isEqualTo(422);
        assertThat(outside.<List<String>>read("$.details.violations[*].message")).singleElement()
                .satisfies(message -> assertThat(message).contains(String.valueOf(LO2)).contains(String.valueOf(HI2)).doesNotContain(String.valueOf(HI)));
        assertThat(writeCount()).isEqualTo(rows + 1);
        assertThat(MINI.si.statusRequests()).as("每個 sched-set 請求各取一次界").isEqualTo(6);
    }

    // ── AT-964-7-5：不走重送閘 ─────────────────────────────────────────────────────────────────────────────

    @Test
    void AT_964_7_5_theSameRequestSentTwiceGetsTwo201sWithDifferentAuditRefsAndNeverAResendConflict() {
        bounds(LO, HI);
        for (int i = 1; i <= 4; i++) {
            refs.refs(ref("b4", i));
        }
        List<Resp> all = new ArrayList<>();
        List<String> setRefs = new ArrayList<>();
        List<String> runRefs = new ArrayList<>();
        for (int i = 0; i < 2; i++) {
            Resp set = post(admin(), SET, schedBody(true, 120, "同一份"));
            setRefs.add(set.<String>read("$.data.auditRef"));
            all.add(set);
        }
        for (int i = 0; i < 2; i++) {
            Resp run = post(admin(), RUN, map("note", "同一份"));
            runRefs.add(run.<String>read("$.data.auditRef"));
            all.add(run);
        }

        assertThat(all).extracting(Resp::status).containsOnly(201);
        assertThat(setRefs).doesNotHaveDuplicates();
        assertThat(runRefs).doesNotHaveDuplicates();
        assertThat(writeCount()).isEqualTo(4);
        assertThat(all).allSatisfy(resp -> assertThat(resp.body()).doesNotContain(ErrorReasons.SI_DECISION_DUPLICATE));
        assertThat(MINI.si.writes).hasSize(4);
    }

    // ── AT-964-7-E-1：閘門序逐級，每級零副作用 ──────────────────────────────────────────────────────────────

    @Test
    void AT_964_7_E_1_theGatesRunInOrderAndEveryRefusalBeforeTheInputGateHasNoSideEffect() {
        bounds(LO, HI);
        Map<String, Object> validSet = schedBody(true, 120, null);
        Map<String, Object> invalidSet = schedBody("yes", 0, "a\nb");
        Map<String, Object> validRun = map("note", "ok");
        Map<String, Object> invalidRun = map("note", "a\nb");
        long statusBase = MINI.si.statusRequests();
        record Step(String label, String path, Object body) {
        }
        for (Step step : List.of(new Step("sched-set", SET, validSet), new Step("run-request", RUN, validRun))) {
            Object invalid = step.path().equals(SET) ? invalidSet : invalidRun;
            assertThat(post(null, step.path(), step.body()).status()).as("%s 無 JWT", step.label()).isEqualTo(401);
            for (String role : List.of("viewer", "operator")) {
                Resp resp = post(role.equals("viewer") ? viewer() : operator(), step.path(), step.body());
                assertThat(resp.status()).as("%s %s", step.label(), role).isEqualTo(403);
                assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
            }
            Resp outsider = post(adminAs("outsider"), step.path(), step.body());
            assertThat(outsider.status()).as("%s 名單外的 ADMIN", step.label()).isEqualTo(403);
            assertThat(outsider.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_FORBIDDEN);

            settings.noKey();
            Resp noKey = post(admin(), step.path(), step.body());
            settings.reset();
            assertThat(noKey.status()).as("%s 金鑰環未設", step.label()).isEqualTo(503);
            assertThat(noKey.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_DISABLED);
            assertThat(noKey.<String>read("$.details.cause")).isEqualTo("audit_key_unset");
            settings.noToken();
            Resp noToken = post(admin(), step.path(), step.body());
            settings.reset();
            assertThat(noToken.status()).as("%s Bridge 權杖未設", step.label()).isEqualTo(503);
            assertThat(noToken.<String>read("$.details.cause")).isEqualTo("bridge_token_unset");

            // 組合情境：取序較前者
            Resp viewerInvalid = post(viewer(), step.path(), invalid);
            assertThat(viewerInvalid.status()).as("%s Viewer 且輸入違規：先 403", step.label()).isEqualTo(403);
            assertThat(viewerInvalid.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
            settings.noKey();
            Resp outsiderNoKey = post(adminAs("outsider"), step.path(), step.body());
            assertThat(outsiderNoKey.status()).as("%s 名單外且金鑰未設：授權先於停用", step.label()).isEqualTo(403);
            assertThat(outsiderNoKey.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_WRITE_FORBIDDEN);
            Resp noKeyInvalid = post(admin(), step.path(), invalid);
            settings.reset();
            assertThat(noKeyInvalid.status()).as("%s 金鑰未設且輸入違規：停用先於輸入閘", step.label()).isEqualTo(503);
            assertThat(noKeyInvalid.<String>read("$.details.cause")).isEqualTo("audit_key_unset");
        }
        assertNoSideEffects("閘門序全程", 0, 0, 0, statusBase);
    }

    // ── AT-964-7-E-2：序 5 輸入閘，全部違規一次回報，與根層字串規則同表 ──────────────────────────────────────────

    private static final String EMOJI_120 = "\uD83D\uDE00".repeat(120);

    /** 字串規則向量表 M-X 的拒收清單（reason 與 note 共用；TCS §5.1；與根層 TCS R141 (c) 同表）。 */
    private static Map<String, String> textRejections() {
        Map<String, String> bad = new LinkedHashMap<>();
        bad.put("121 個 U+4E2D", "\u4E2D".repeat(121));
        bad.put("121 個 U+1F600", "\uD83D\uDE00".repeat(121));
        bad.put("含 LF", "a\nb");
        bad.put("含 CR", "a\rb");
        bad.put("含 U+0000", "a\u0000b");
        bad.put("含 U+001F", "a\u001fb");
        bad.put("含 U+007F", "a\u007fb");
        bad.put("TAB", "a\tb");
        bad.put("首尾換行", "\nok\n");
        bad.put("空字串", "");
        bad.put("全空白", "   ");
        bad.put("全是不斷行空白", "\u00a0\u00a0");
        return bad;
    }

    @Test
    void AT_964_7_E_2_everyViolationIsReportedAtOnceAndTheTextRulesMatchTheRootTable() {
        bounds(LO, HI);
        long statusBase = MINI.si.statusRequests();
        Map<String, Map<String, Object>> badSet = new LinkedHashMap<>();
        badSet.put("enabled 缺", schedBody(null, 120, null));
        badSet.put("enabled 為字串 true", schedBody("true", 120, null));
        badSet.put("enabled 為數字 1", schedBody(1, 120, null));
        badSet.put("periodMinutes 缺", schedBody(true, null, null));
        badSet.put("periodMinutes 為小數", schedBody(true, 90.5, null));
        badSet.put("periodMinutes 為字串", schedBody(true, "120", null));
        badSet.put("periodMinutes 為負數", schedBody(true, -5, null));
        badSet.put("periodMinutes 為 0", schedBody(true, 0, null));
        badSet.put("periodMinutes 為布林", schedBody(true, true, null));
        Map<String, String> fields = new LinkedHashMap<>();
        badSet.keySet().forEach(label -> fields.put(label, label.startsWith("enabled") ? "enabled" : "periodMinutes"));
        textRejections().forEach((label, text) -> {
            badSet.put("sched-set reason " + label, schedBody(true, 120, text));
            fields.put("sched-set reason " + label, "reason");
        });
        for (Map.Entry<String, Map<String, Object>> entry : badSet.entrySet()) {
            Resp resp = post(admin(), SET, entry.getValue());

            assertThat(resp.status()).as(entry.getKey()).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).as(entry.getKey()).isEqualTo("invalid_request");
            assertThat(violationFields(resp)).as(entry.getKey()).containsExactly(fields.get(entry.getKey()));
            assertThat(resp.<List<String>>read("$.errors[*].field")).as("errors[] 與 details.violations 同內容").containsExactly(fields.get(entry.getKey()));
        }
        for (Map.Entry<String, String> entry : textRejections().entrySet()) {
            Resp resp = post(admin(), RUN, map("note", entry.getValue()));

            assertThat(resp.status()).as("run-request note %s", entry.getKey()).isEqualTo(422);
            assertThat(violationFields(resp)).as("note %s", entry.getKey()).containsExactly("note");
        }
        Resp surrogate = api.raw(admin(), HttpMethod.POST, SI + SET, "{\"enabled\":true,\"periodMinutes\":120,\"reason\":\"a\\ud800b\"}");
        assertThat(surrogate.status()).as("孤立代理字元（sched-set reason）").isEqualTo(422);
        assertThat(violationFields(surrogate)).containsExactly("reason");
        Resp surrogateNote = api.raw(admin(), HttpMethod.POST, SI + RUN, "{\"note\":\"a\\udc00b\"}");
        assertThat(surrogateNote.status()).as("孤立代理字元（run-request note）").isEqualTo(422);
        assertThat(violationFields(surrogateNote)).containsExactly("note");
        Resp noteNumber = post(admin(), RUN, map("note", 7));
        assertThat(noteNumber.status()).as("note 非字串").isEqualTo(422);

        settings.deciders("bad name");
        Resp fourAtOnce = post(adminAs("bad name"), SET, schedBody("true", 1.5, ""));
        settings.reset();
        assertThat(fourAtOnce.status()).isEqualTo(422);
        assertThat(violationFields(fourAtOnce)).as("同時違規四處的請求一次回報四項").containsExactlyInAnyOrder("user", "enabled", "periodMinutes",
                "reason");
        assertNoSideEffects("422 之前後", 0, 0, 0, statusBase);

        refs.refs(ref("b4", 1), ref("b4", 2), ref("b4", 3), ref("b4", 4), ref("b4", 5), ref("b4", 6));
        for (String reason : List.of(EMOJI_120, "a|b", "  ok  ")) {
            assertThat(post(admin(), SET, schedBody(true, 120, reason)).status()).as("放行 sched-set reason").isEqualTo(201);
            assertThat(post(admin(), RUN, map("note", reason)).status()).as("放行 run-request note").isEqualTo(201);
        }
        assertThat(JSON.readTree(outer(4).get("body").asString()).get("reason").asString()).as("前後空白去除後簽進 body").isEqualTo("ok");
        assertThat(JSON.readTree(outer(5).get("body").asString()).get("note").asString()).isEqualTo("ok");
        assertThat(JSON.readTree(outer(2).get("body").asString()).get("reason").asString()).as("豎線原樣").isEqualTo("a|b");
    }

    // ── AT-964-7-E-3：取不到界＝503 schedule_bounds_unavailable；status 自己失敗沿 GET 對映；不用快取值 ────────────────

    private void assertBoundsUnavailable(String label, Object schedule, String detailMentions) {
        MINI.si.status(schedule);
        long rows = writeCount();
        int writes = MINI.si.writes.size();
        int taken = refs.taken();

        Resp resp = post(admin(), SET, schedBody(true, 120, null));

        assertThat(resp.status()).as(label).isEqualTo(503);
        assertThat(resp.<String>read("$.reason")).as(label).isEqualTo(ErrorReasons.SI_UNAVAILABLE);
        assertThat(resp.<String>read("$.details.cause")).as(label).isEqualTo("schedule_bounds_unavailable");
        assertThat(resp.<String>read("$.details.detail")).as(label).contains(detailMentions);
        assertThat(writeCount()).as("%s：零列", label).isEqualTo(rows);
        assertThat(MINI.si.writes).as("%s：零落檔", label).hasSize(writes);
        assertThat(refs.taken()).as("%s：ref 不取", label).isEqualTo(taken);
    }

    @Test
    void AT_964_7_E_3_missingOrMalformedBoundsAre503WithTheBoundsCauseAndAFailingStatusIsForwardedLikeTheGetAndNoCachedBoundIsUsed() {
        refs.refs(ref("b4", 1), ref("b4", 2), ref("b4", 3));
        assertBoundsUnavailable("schedule 鍵缺席", MiniBridge.Si.DROP, "schedule");
        Map<String, Object> noMin = MiniBridge.Si.scheduleWithBounds(LO, HI);
        noMin.remove("period_min");
        assertBoundsUnavailable("period_min 缺席", noMin, "period_min");
        Map<String, Object> noMax = MiniBridge.Si.scheduleWithBounds(LO, HI);
        noMax.remove("period_max");
        assertBoundsUnavailable("period_max 缺席", noMax, "period_max");
        assertBoundsUnavailable("period_min 為字串", MiniBridge.Si.scheduleWithBounds("60", HI), "period_min");
        assertBoundsUnavailable("period_min 大於 period_max", MiniBridge.Si.scheduleWithBounds(HI, LO), "period_max");
        assertBoundsUnavailable("period_max 為小數", MiniBridge.Si.scheduleWithBounds(LO, 100.5), "period_max");
        assertThat(refs.taken()).isZero();

        // GET status 自己失敗：狀態碼與 reason 與 GET /api/v1/si/status 在同樣失敗下的回應逐項相同
        bounds(LO, HI);
        MINI.si.unavailable = Map.of("cause", "schema_rev_mismatch", "detail", "schema_rev=2 不等於 1");
        Resp getUnavailable = api.get(viewer(), SI + "/status");
        Resp setUnavailable = post(admin(), SET, schedBody(true, 120, null));
        assertThat(setUnavailable.status()).isEqualTo(503).isEqualTo(getUnavailable.status());
        assertThat(setUnavailable.<String>read("$.reason")).isEqualTo(getUnavailable.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_UNAVAILABLE);
        assertThat(setUnavailable.<String>read("$.details.cause")).as("原因逐字轉出").isEqualTo("schema_rev_mismatch")
                .isEqualTo(getUnavailable.<String>read("$.details.cause"));
        assertThat(setUnavailable.<String>read("$.details.detail")).isEqualTo(getUnavailable.<String>read("$.details.detail"));
        MINI.si.unavailable = Map.of();

        MINI.si.status500 = true;
        Resp getBad = api.get(viewer(), SI + "/status");
        Resp setBad = post(admin(), SET, schedBody(true, 120, null));
        MINI.si.status500 = false;
        assertThat(setBad.status()).isEqualTo(502).isEqualTo(getBad.status());
        assertThat(setBad.<String>read("$.reason")).isEqualTo(getBad.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_ERROR);

        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp getRefused = api.get(viewer(), SI + "/status");
        Resp setRefused = post(admin(), SET, schedBody(true, 120, null));
        resetSystemConfigs();
        thresholds.invalidate();
        assertThat(setRefused.status()).isEqualTo(502).isEqualTo(getRefused.status());
        assertThat(setRefused.<String>read("$.reason")).isEqualTo(getRefused.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_UNREACHABLE);

        readTimeout.cap(Duration.ofSeconds(1));
        MINI.si.delayMillis = 3_000;
        Resp getTimeout = api.get(viewer(), SI + "/status");
        Resp setTimeout = post(admin(), SET, schedBody(true, 120, null));
        MINI.si.delayMillis = 0;
        readTimeout.reset();
        assertThat(setTimeout.status()).isEqualTo(504).isEqualTo(getTimeout.status());
        assertThat(setTimeout.<String>read("$.reason")).isEqualTo(getTimeout.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_TIMEOUT);
        assertThat(writeCount()).as("status 失敗的四種情境：全部零副作用").isZero();
        assertThat(MINI.si.writes).isEmpty();
        assertThat(refs.taken()).isZero();

        // 不用快取值：第一個請求取得界、第二個 status 失敗＝503（不沿用第一個取得的界）
        MINI.si.reset();
        bounds(LO, HI);
        assertThat(post(admin(), SET, schedBody(true, 120, null)).status()).as("第一個：取得界").isEqualTo(201);
        MINI.si.unavailable = Map.of("cause", "nonzero_rc", "detail", "rc=3");
        Resp second = post(admin(), SET, schedBody(true, 120, null));
        MINI.si.unavailable = Map.of();
        assertThat(second.status()).as("第二個：status 失敗，不沿用 A").isEqualTo(503);
        assertThat(writeCount()).isEqualTo(1);

        // run-request 不經序 5′：同一個壞 status 下仍 201
        refs.refs(ref("b4", 9));
        MINI.si.status(MiniBridge.Si.DROP);
        long statusBefore = MINI.si.statusRequests();
        assertThat(post(admin(), RUN, Map.of()).status()).as("run-request 對照").isEqualTo(201);
        assertThat(MINI.si.statusRequests()).isEqualTo(statusBefore);
    }

    // ── AT-964-7-E-4：補償與結果不明 ───────────────────────────────────────────────────────────────────────

    @Test
    void AT_964_7_E_4_explicitBridgeRefusalsDeleteTheRowAndAnUnknownOutcomeKeepsItWithTheReasonForwardedVerbatim() {
        bounds(LO, HI);
        record Case(String label, WriteReply reply, int status, String reason) {
        }
        List<Case> cases = List.of(
                new Case("422", WriteReply.error(422, "invalid_request", "violations", List.of(map("field", "subject", "rule", "mismatch",
                        "message", "須為 null"))), 422, ErrorReasons.BRIDGE_REJECTED),
                new Case("409", WriteReply.error(409, "si_audit_exists"), 409, "si_audit_exists"),
                new Case("503 unavailable", WriteReply.error(503, "si_unavailable", "cause", "audit_write_failed", "detail", "errno=28; OSError"), 503,
                        "si_unavailable"),
                new Case("503 disabled", WriteReply.error(503, "si_write_disabled", "detail", "BRIDGE_SI_AUDIT_DIR 未設"), 503, "si_write_disabled"),
                new Case("403", WriteReply.error(403, "si_write_forbidden"), 403, "si_write_forbidden"));
        long expectedRows = 0;
        int sent = 0;
        for (String path : List.of(SET, RUN)) {
            Object body = path.equals(SET) ? schedBody(true, 120, null) : Map.of();
            for (Case c : cases) {
                refs.refs(ref("b2", sent + 1));
                MINI.si.writeReply = c.reply();

                Resp resp = post(admin(), path, body);

                assertThat(resp.status()).as("%s %s", path, c.label()).isEqualTo(c.status());
                assertThat(resp.<String>read("$.reason")).as("%s %s", path, c.label()).isEqualTo(c.reason());
                assertThat(writeCount()).as("%s %s：補償後列數回到送出前", path, c.label()).isEqualTo(expectedRows);
                assertThat(MINI.si.writes).as("每次 Bridge 恰一個稽核請求").hasSize(++sent);
                assertThat(resp.has("$.details.outcomeUnknown")).as("確定未落檔：沒有 outcomeUnknown").isFalse();
                if (c.label().equals("503 unavailable")) {
                    assertThat(resp.<String>read("$.details.cause")).isEqualTo("audit_write_failed");
                    assertThat(resp.<String>read("$.details.detail")).isEqualTo("errno=28; OSError");
                }
                if (c.label().equals("422")) {
                    assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("invalid_request");
                }
            }
            MINI.si.writeReply = null;
            // 逾時：結果不明，列保留
            refs.refs(ref("b2", sent + 1));
            readTimeout.cap(Duration.ofSeconds(1));
            MINI.si.writeDelayMillis = 3_000;
            Resp timedOut = post(admin(), path, body);
            MINI.si.writeDelayMillis = 0;
            readTimeout.reset();
            expectedRows++;
            sent++;
            assertThat(timedOut.status()).as("%s 逾時", path).isEqualTo(504);
            assertThat(timedOut.<Boolean>read("$.details.outcomeUnknown")).isTrue();
            assertThat(writeCount()).as("%s 逾時：該列保留", path).isEqualTo(expectedRows);
        }
        assertThat(refs.taken()).as("每次請求恰取用一次 ref").isEqualTo(sent);
    }

    // ── AT-964-7-E-5：其餘方法 ─────────────────────────────────────────────────────────────────────────────

    @Test
    void AT_964_7_E_5_putPatchAndDeleteAre403ForViewerAnd405ForOperatorAndAdminAndGetIs405WithoutSideEffects() {
        Map<String, String> tokens = new LinkedHashMap<>();
        tokens.put("viewer", viewer());
        tokens.put("operator", operator());
        tokens.put("admin", admin());
        int checked = 0;
        for (String path : List.of(SET, RUN)) {
            String url = SI + path;
            for (Map.Entry<String, String> role : tokens.entrySet()) {
                List<MockHttpServletRequestBuilder> writes = List.of(MockMvcRequestBuilders.delete(url),
                        MockMvcRequestBuilders.put(url).contentType("application/json").content("{}"),
                        MockMvcRequestBuilders.patch(url).contentType("application/json").content("{}"));
                for (MockHttpServletRequestBuilder request : writes) {
                    int expected = role.getKey().equals("viewer") ? 403 : 405;
                    assertThat(api.send(role.getValue(), request).status()).as("%s %s", role.getKey(), path).isEqualTo(expected);
                    checked++;
                }
                // GET：SecurityConfig 對 GET /api/v1/** 放行 VIEWER 以上，沒有 GET 對映 ⇒ 任何已登入角色都是 405（契約字面寫 VIEWER／OPERATOR 為 403，見交卷偏離）
                assertThat(api.send(role.getValue(), MockMvcRequestBuilders.get(url)).status()).as("GET %s %s", role.getKey(), path)
                        .isEqualTo(405);
                checked++;
            }
            assertThat(api.send(null, MockMvcRequestBuilders.get(url)).status()).as("GET 無 token %s", path).isEqualTo(401);
            checked++;
        }
        assertThat(checked).isEqualTo(26);
        assertNoSideEffects("其餘方法", 0, 0, 0, 0);
    }
}
