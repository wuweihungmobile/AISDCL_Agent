package com.aisdlc.console.application.service;

import com.aisdlc.console.application.service.SiAuditSigner.SignedAudit;
import com.aisdlc.console.domain.model.si.SiAuditKeyRing;
import com.aisdlc.console.domain.model.si.SiCloseCommand;
import com.aisdlc.console.domain.model.si.SiDecideCommand;
import com.aisdlc.console.domain.model.si.SiObservationCommand;
import com.aisdlc.console.domain.model.si.SiWriteKind;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 稽核 JSON 的簽章與位元組契約（TCS-SelfImprovingDecide-P2b AT-950-4-1、4-2、4-E-1、4-E-2、4-E-3；W7、W8）。為什麼重要：稽核檔要被主機端
 * 根層 Python CLI 逐位元組驗簽——Java 這一側序列化器多一個空白、少一個鍵、把 UTC 寫成 {@code Z}，入帳就是 AUDIT-MAC-MISMATCH 或
 * AUDIT-TIME-FORMAT，而且只有到了主機入帳那一刻才發現。所以這裡用 TCS §5.1 的跨語言向量（Python 標準庫重算過、真 CLI 驗過）當唯一真相，
 * 逐位元組比對，並以獨立的 JDK 計算與 Jackson 解析當對照（不呼叫被測碼自己的輔助函式）。
 */
class SiAuditSignerTest {

    /** §5.1 的公開測試金鑰（UTF-8 字串、不做 base64 解碼；字面刻意不用 sk- 形態）。 */
    private static final String K0 = "si-p2-vector-key-0123456789-abcdefghijklmnopqrstuvwxyz";
    private static final String K0_ID = "f076edf0";
    private static final String D1 = "sha256:a45ee65aa8547255f96c45d106da2a239e0c6db4fc9c06a9af229cb9e9ec9bfe";
    private static final String D0 = "sha256:d21ae6f5a48de71266479e0a7f6278786764f9a52bbb0a7c6d82b7f1419cec9c";
    private static final String VECTOR_TIME = "2026-10-21T09:15:30+08:00";
    private static final String STD_TIME = "2026-10-24T22:30:15+08:00";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final SiAuditKeyRing RING = SiAuditKeyRing.parse(K0);

    private final SiAuditSigner signer = new SiAuditSigner(
            Clock.fixed(Instant.parse("2026-10-24T14:30:15Z"), ZoneOffset.ofHours(8)));

    private static SiDecideCommand decide(String dkind, String digest, String reasonClass, String reason, String... flags) {
        return new SiDecideCommand("PROP-SI-004", dkind, digest, reasonClass, reason, List.of(flags));
    }

    /** 獨立於被測碼的 HMAC-SHA256 參照（直接用 JDK）。 */
    private static String hmacHex(String key, String message) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return HexFormat.of().formatHex(mac.doFinal(message.getBytes(StandardCharsets.UTF_8)));
    }

    private static int utf8(String text) {
        return text.getBytes(StandardCharsets.UTF_8).length;
    }

    // ── AT-950-4-1：跨語言向量 V1～V4 ─────────────────────────────────────────────────────────

    private record Vector(String name, SiWriteKind kind, String ref, String subject, String body, String mac, int bodyBytes,
                          int fileBytes, String fileSha) {
    }

    private static List<Vector> vectors() {
        return List.of(
                new Vector("V1", SiWriteKind.DECIDE, "6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b", "PROP-SI-004",
                        "{\"schema_rev\":1,\"audit_ref\":\"6f1c2a3e-8b4d-4e5f-9a7b-0c1d2e3f4a5b\",\"kind\":\"decide\",\"user\":\"admin\","
                                + "\"role\":\"ADMIN\",\"time\":\"2026-10-21T09:15:30+08:00\",\"prop\":\"PROP-SI-004\",\"digest\":\"" + D1
                                + "\",\"dkind\":\"approve\",\"flags\":[]}",
                        "a23f62da5cc2b8668a05570632b60700316350667c2fef600beda100c4bf3c21", 281, 527,
                        "sha256:4e35c9e5df306c11d77698bd0dbca4090d46fa4d09b8ffae87f135b27335c43f"),
                new Vector("V2", SiWriteKind.DECIDE, "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d", "PROP-SI-004",
                        "{\"schema_rev\":1,\"audit_ref\":\"0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d\",\"kind\":\"decide\",\"user\":\"admin\","
                                + "\"role\":\"ADMIN\",\"time\":\"2026-10-21T09:15:30+08:00\",\"prop\":\"PROP-SI-004\",\"digest\":\"" + D1
                                + "\",\"dkind\":\"reject\",\"reason_class\":\"證據不足\",\"reason\":\"證據座標不足，無法判定\",\"flags\":[]}",
                        "830722c9fcfccc37861f9fe62498aa0074822595e85578e48c8a04298de0ce9b", 355, 609,
                        "sha256:df7419ef9502262538fe8640a23a6bb691299b683929858178b02b89fe1ed3eb"),
                new Vector("V3", SiWriteKind.OBS_ADD, "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e", null,
                        "{\"schema_rev\":1,\"audit_ref\":\"b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e\",\"kind\":\"obs-add\",\"user\":\"admin\","
                                + "\"role\":\"ADMIN\",\"time\":\"2026-10-21T09:15:30+08:00\",\"context\":\"Console・自我進化頁\","
                                + "\"symptom\":\"待入帳徽章在入帳後仍顯示\",\"evidence\":\"AgentConsole/frontend/components/domain/si/SiView.tsx:88\","
                                + "\"category\":\"bug\",\"severity\":\"P3\",\"face\":\"產品\",\"external_derived\":false}",
                        "0e67b0e0be050c07dc3b539fed87b3f53f88856446d2468b0e9f1da71cb94f35", 380, 630,
                        "sha256:a923a24521bb7a05e2e05427e0b5f7e30d7080350c8ce6cba6944ae887cef601"),
                new Vector("V4", SiWriteKind.OBS_CLOSE, "c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f", "OBS-SI-247",
                        "{\"schema_rev\":1,\"audit_ref\":\"c3d4e5f6-a7b8-4c9d-8e0f-1a2b3c4d5e6f\",\"kind\":\"obs-close\",\"user\":\"admin\","
                                + "\"role\":\"ADMIN\",\"time\":\"2026-10-21T09:15:30+08:00\",\"obs_id\":\"OBS-SI-247\","
                                + "\"disposition\":\"decided：掌舵者裁決，已修復\"}",
                        "f299d74dd7c261072b69a4c14a79999cda39716b5a9851b65fce8b6da016f6bc", 227, 469,
                        "sha256:5d3f20980c464cb020b8031a3009435ecc94e408c1f8b5873a45610bb590eba4"));
    }

    private String composeVectorBody(Vector v) {
        return switch (v.name()) {
            case "V1" -> signer.decideBody(v.ref(), "admin", VECTOR_TIME, decide("approve", D1, null, null));
            case "V2" -> signer.decideBody(v.ref(), "admin", VECTOR_TIME, decide("reject", D1, "證據不足", "證據座標不足，無法判定"));
            case "V3" -> signer.observationBody(v.ref(), "admin", VECTOR_TIME, new SiObservationCommand("Console・自我進化頁",
                    "待入帳徽章在入帳後仍顯示", "AgentConsole/frontend/components/domain/si/SiView.tsx:88", "bug", "P3", "產品",
                    null, false, null));
            default -> signer.closeBody(v.ref(), "admin", VECTOR_TIME, new SiCloseCommand(v.subject(), "decided：掌舵者裁決，已修復"));
        };
    }

    @Test
    void AT_950_4_1_theFourCrossLanguageVectorsMatchByteForByte() throws Exception {
        for (Vector v : vectors()) {
            String body = composeVectorBody(v);

            assertThat(body).as("%s 的 body 字串逐字相等", v.name()).isEqualTo(v.body());
            assertThat(utf8(body)).as("%s 的 body 位元組數", v.name()).isEqualTo(v.bodyBytes());
            SignedAudit signed = signer.sign(v.kind(), v.ref(), v.subject(), body, RING);

            assertThat(signed.mac()).as("%s 的 mac", v.name()).isEqualTo(v.mac());
            assertThat(signed.keyId()).as("%s 的 key_id", v.name()).isEqualTo(K0_ID);
            assertThat(signed.fileBytes()).as("%s 的外層檔位元組數", v.name()).hasSize(v.fileBytes());
            assertThat(signed.fileSha256()).as("%s 的外層檔 sha256", v.name()).isEqualTo(v.fileSha());
            assertThat(signed.file()).as("緊湊、無結尾換行、無 BOM").doesNotEndWith("\n").doesNotStartWith("\uFEFF").doesNotContain(": ")
                    .doesNotContain(", ");
            // 外層恰七鍵、序固定
            JsonNode outer = JSON.readTree(signed.file());
            List<String> keys = new ArrayList<>();
            for (Iterator<String> it = outer.propertyNames().iterator(); it.hasNext();) {
                keys.add(it.next());
            }
            assertThat(keys).as("%s 的外層鍵序", v.name())
                    .containsExactly("schema_rev", "kind", "audit_ref", "subject", "body", "key_id", "mac");
            assertThat(outer.get("body").asString()).as("body 是字串且逐字等於被簽的 body").isEqualTo(body);
            assertThat(outer.get("mac").asString()).isEqualTo(hmacHex(K0, body));
            if (v.subject() == null) {
                assertThat(outer.get("subject").isNull()).as("obs-add 的 subject 為 JSON null").isTrue();
            } else {
                assertThat(outer.get("subject").asString()).isEqualTo(v.subject());
            }
        }
    }

    @Test
    void AT_950_4_1_anyNonAsciiTextStaysVerbatimAndSpecialCharactersRoundTripThroughBothLayers() {
        String awkward = "含\"引號\"與\\反斜線\\、/斜線、emoji 😀 與全形，。";

        String body = signer.decideBody("a1000000-0000-4000-8000-000000000001", "admin", STD_TIME,
                decide("rollback", null, null, awkward));
        SignedAudit signed = signer.sign(SiWriteKind.DECIDE, "a1000000-0000-4000-8000-000000000001", "PROP-SI-004", body, RING);

        assertThat(body).as("非 ASCII 原樣、斜線不逸出").contains("全形，。").contains("😀").contains("/斜線").doesNotContain("\\u");
        assertThat(JSON.readTree(body).get("reason").asString()).as("內層 JSON 可還原").isEqualTo(awkward);
        assertThat(JSON.readTree(signed.file()).get("body").asString()).as("外層 JSON 還原出的 body 與被簽的逐字相同").isEqualTo(body);
    }

    // ── AT-950-4-2：body 鍵序與鍵集合（表 M-D、M-O、M-C）────────────────────────────────────────

    private static String head(String ref) {
        return "{\"schema_rev\":1,\"audit_ref\":\"" + ref + "\",\"kind\":\"decide\",\"user\":\"admin\",\"role\":\"ADMIN\","
                + "\"time\":\"" + STD_TIME + "\",";
    }

    private static String headObs(String ref, String kind) {
        return "{\"schema_rev\":1,\"audit_ref\":\"" + ref + "\",\"kind\":\"" + kind + "\",\"user\":\"admin\",\"role\":\"ADMIN\","
                + "\"time\":\"" + STD_TIME + "\",";
    }

    private static String refD(int n) {
        return "b2000000-0000-4000-8000-0000000000" + String.format("%02d", n);
    }

    @Test
    void AT_950_4_2_everyDecideVerbComposesTheTableMdBodyAndOnlyPromoteMayCarryTheAckFlag() {
        record Case(int n, SiDecideCommand command, String tail) {
        }
        List<Case> cases = List.of(
                new Case(1, decide("approve", D0, null, null),
                        "\"prop\":\"PROP-SI-004\",\"digest\":\"" + D0 + "\",\"dkind\":\"approve\",\"flags\":[]}"),
                new Case(2, decide("reject", D0, "證據不足", "證據座標不足，無法判定"),
                        "\"prop\":\"PROP-SI-004\",\"digest\":\"" + D0
                                + "\",\"dkind\":\"reject\",\"reason_class\":\"證據不足\",\"reason\":\"證據座標不足，無法判定\",\"flags\":[]}"),
                new Case(3, decide("return", D0, "工件類別錯", "改用 M 類"),
                        "\"prop\":\"PROP-SI-004\",\"digest\":\"" + D0
                                + "\",\"dkind\":\"return\",\"reason_class\":\"工件類別錯\",\"reason\":\"改用 M 類\",\"flags\":[]}"),
                new Case(4, decide("promote", D0, null, null),
                        "\"prop\":\"PROP-SI-004\",\"digest\":\"" + D0 + "\",\"dkind\":\"promote\",\"flags\":[]}"),
                new Case(5, decide("decline-promote", D0, "風險過高", "風險太高"),
                        "\"prop\":\"PROP-SI-004\",\"digest\":\"" + D0
                                + "\",\"dkind\":\"decline-promote\",\"reason_class\":\"風險過高\",\"reason\":\"風險太高\",\"flags\":[]}"),
                new Case(6, decide("rollback", null, null, "太慢"),
                        "\"prop\":\"PROP-SI-004\",\"dkind\":\"rollback\",\"reason\":\"太慢\",\"flags\":[]}"),
                new Case(7, decide("unblock", null, null, null), "\"prop\":\"PROP-SI-004\",\"dkind\":\"unblock\",\"flags\":[]}"),
                new Case(8, new SiDecideCommand("RUN-SI-001", "resume", null, null, "兩個壞窗已人工檢視", List.of()),
                        "\"run\":\"RUN-SI-001\",\"dkind\":\"resume\",\"reason\":\"兩個壞窗已人工檢視\",\"flags\":[]}"),
                new Case(9, decide("ack-handoff", D0, null, null),
                        "\"prop\":\"PROP-SI-004\",\"digest\":\"" + D0 + "\",\"dkind\":\"ack-handoff\",\"flags\":[]}"),
                new Case(10, decide("promote", D0, null, null, "unverified_ack"),
                        "\"prop\":\"PROP-SI-004\",\"digest\":\"" + D0 + "\",\"dkind\":\"promote\",\"flags\":[\"unverified_ack\"]}"));
        for (Case c : cases) {
            assertThat(signer.decideBody(refD(c.n()), "admin", STD_TIME, c.command())).as("dkind=%s", c.command().dkind())
                    .isEqualTo(head(refD(c.n())) + c.tail());
        }
    }

    @Test
    void AT_950_4_2_observationBodiesPlaceExposureRightAfterFaceAndCorrectsLast() {
        String ctx = "Console・自我進化頁";
        String symptom = "待入帳徽章在入帳後仍顯示";
        String evidence = "AgentConsole/frontend/components/domain/si/SiView.tsx:88";
        String common = "\"context\":\"" + ctx + "\",\"symptom\":\"" + symptom + "\",\"evidence\":\"" + evidence + "\",";
        String o1 = signer.observationBody("b3000000-0000-4000-8000-000000000001", "admin", STD_TIME,
                new SiObservationCommand(ctx, symptom, evidence, "bug", "P3", "產品", null, false, null));
        String o2 = signer.observationBody("b3000000-0000-4000-8000-000000000002", "admin", STD_TIME,
                new SiObservationCommand(ctx, symptom, evidence, "tooling", "P2", "守衛", "b", true, null));
        String o3 = signer.observationBody("b3000000-0000-4000-8000-000000000003", "admin", STD_TIME,
                new SiObservationCommand(ctx, symptom, evidence, "bug", "P3", "產品", null, false, "OBS-SI-001"));

        assertThat(o1).isEqualTo(headObs("b3000000-0000-4000-8000-000000000001", "obs-add") + common
                + "\"category\":\"bug\",\"severity\":\"P3\",\"face\":\"產品\",\"external_derived\":false}");
        assertThat(o2).isEqualTo(headObs("b3000000-0000-4000-8000-000000000002", "obs-add") + common
                + "\"category\":\"tooling\",\"severity\":\"P2\",\"face\":\"守衛\",\"exposure\":\"b\",\"external_derived\":true}");
        assertThat(o3).isEqualTo(headObs("b3000000-0000-4000-8000-000000000003", "obs-add") + common
                + "\"category\":\"bug\",\"severity\":\"P3\",\"face\":\"產品\",\"external_derived\":false,\"corrects\":\"OBS-SI-001\"}");
        String unsigned = signer.observationBody(null, "admin", STD_TIME,
                new SiObservationCommand(ctx, symptom, evidence, "bug", "P3", "產品", null, false, null));
        assertThat(unsigned).as("預檢的未簽 body：沒有 audit_ref").startsWith("{\"schema_rev\":1,\"kind\":\"obs-add\",\"user\":\"admin\"")
                .doesNotContain("audit_ref").doesNotContain("mac").doesNotContain("key_id");
    }

    @Test
    void AT_950_4_2_theSevenCloseTerminalsComposeTheirDispositionVerbatim() {
        String[][] rows = {
                {"fixed@2b2b0b3d"}, {"DEF-200-559"}, {"deferred：等 P3 輪"}, {"retired：docs/06_quality/SelfImproving_Protocol/params.json"},
                {"decided：夾具關閉"}, {"merged@OBS-SI-001"}, {"proposed@PROP-SI-004"}};
        for (int i = 0; i < rows.length; i++) {
            String ref = "b4000000-0000-4000-8000-0000000000" + String.format("%02d", i + 1);

            String body = signer.closeBody(ref, "admin", STD_TIME, new SiCloseCommand("OBS-SI-005", rows[i][0]));

            assertThat(body).isEqualTo(headObs(ref, "obs-close") + "\"obs_id\":\"OBS-SI-005\",\"disposition\":\"" + rows[i][0] + "\"}");
        }
    }

    // ── AT-950-4-E-1：負控 ───────────────────────────────────────────────────────────────────

    @Test
    void AT_950_4_E_1_changingOneByteOrTheKeyOrWritingZGivesTheContractsControlValues() throws Exception {
        Vector v1 = vectors().get(0);
        String reject = v1.body().replace("\"dkind\":\"approve\"", "\"dkind\":\"reject\"");

        SignedAudit tampered = signer.sign(SiWriteKind.DECIDE, v1.ref(), "PROP-SI-004", reject, RING);
        SignedAudit longerKey = signer.sign(SiWriteKind.DECIDE, v1.ref(), "PROP-SI-004", v1.body(), SiAuditKeyRing.parse(K0 + "x"));

        assertThat(tampered.mac()).isEqualTo("7801839b8fd4d641711b8a982ae18526bc8ae9857f5c5fdc3df19e1b4d5c6b2b").isNotEqualTo(v1.mac());
        assertThat(longerKey.mac()).isEqualTo("e4a88cff0a4a932fc930efa4d3b1caeda3f4ad64ebfa82dfedffc1358a61e967").isNotEqualTo(v1.mac());
        assertThat(longerKey.keyId()).as("金鑰不同，key_id 也不同").isNotEqualTo(K0_ID);
        assertThat(tampered.mac()).isEqualTo(hmacHex(K0, reject));

        OffsetDateTime utc = OffsetDateTime.of(2026, 10, 21, 9, 15, 30, 0, ZoneOffset.UTC);
        assertThat(SiAuditSigner.formatTime(utc)).as("UTC 瞬間格式化得 +00:00，絕不輸出 Z").isEqualTo("2026-10-21T09:15:30+00:00")
                .doesNotContain("Z");
        assertThat(SiAuditSigner.formatTime(new SiAuditSigner(Clock.fixed(Instant.parse("2026-10-21T09:15:30Z"), ZoneId.of("UTC"))).now()))
                .isEqualTo("2026-10-21T09:15:30+00:00");
        assertThat(SiAuditSigner.formatTime(OffsetDateTime.parse("2026-10-21T01:15:30Z"))).doesNotEndWith("Z");
    }

    // ── AT-950-4-E-2：金鑰環語意 ─────────────────────────────────────────────────────────────

    @Test
    void AT_950_4_E_2_theFirstKeyOfTheRingSignsAndSeparatorsAndWhitespaceAreStripped() throws Exception {
        String k2 = "k2-another-key-abcdefghijklmnopqrstuvwxyz-0123";
        Vector v1 = vectors().get(0);

        SiAuditKeyRing ring = SiAuditKeyRing.parse("  " + K0 + " , ," + k2);
        SignedAudit signed = signer.sign(SiWriteKind.DECIDE, v1.ref(), "PROP-SI-004", v1.body(), ring);

        assertThat(ring.keys()).containsExactly(K0, k2);
        assertThat(signed.mac()).as("簽章用 k1（與 V1 的 mac 相同）").isEqualTo(v1.mac());
        assertThat(signed.keyId()).isEqualTo(K0_ID);
        assertThat(ring.keys()).as("k2 保留供輪替、不簽").contains(k2);

        SignedAudit swapped = signer.sign(SiWriteKind.DECIDE, v1.ref(), "PROP-SI-004", v1.body(), SiAuditKeyRing.parse(k2 + "," + K0));
        assertThat(swapped.keyId()).as("環序改為 k2 先：key_id 隨之改變").isNotEqualTo(K0_ID);
        assertThat(swapped.mac()).isNotEqualTo(v1.mac()).isEqualTo(hmacHex(k2, v1.body()));

        for (String blank : new String[] {null, "", "   ", " , ,, ", "\t,\n"}) {
            SiAuditKeyRing empty = SiAuditKeyRing.parse(blank);
            assertThat(empty.isEmpty()).as("空項環視同未設：%s", blank).isTrue();
        }
        assertThatThrownBy(() -> signer.sign(SiWriteKind.DECIDE, v1.ref(), "PROP-SI-004", v1.body(), SiAuditKeyRing.EMPTY))
                .isInstanceOf(IllegalStateException.class).hasMessageNotContaining(K0);
        assertThat(ring.toString()).as("環的 toString 不含任何金鑰").doesNotContain(K0).doesNotContain(k2);
        assertThat(signed.toString()).as("簽章結果不含金鑰").doesNotContain(K0);
    }

    // ── AT-950-4-E-3：time 格式邊界 ───────────────────────────────────────────────────────────

    @Test
    void AT_950_4_E_3_timeIsSecondPrecisionWithAnOffsetAndTheMillisecondsAreTruncatedNotRounded() {
        record ZoneCase(ZoneId zone, String expected) {
        }
        Instant instant = Instant.parse("2026-10-24T14:30:15.999Z");
        List<ZoneCase> cases = List.of(
                new ZoneCase(ZoneOffset.UTC, "2026-10-24T14:30:15+00:00"),
                new ZoneCase(ZoneOffset.ofHours(8), "2026-10-24T22:30:15+08:00"),
                new ZoneCase(ZoneOffset.ofHoursMinutes(-5, -30), "2026-10-24T09:00:15-05:30"),
                new ZoneCase(ZoneId.of("Asia/Taipei"), "2026-10-24T22:30:15+08:00"));
        for (ZoneCase c : cases) {
            String formatted = SiAuditSigner.formatTime(new SiAuditSigner(Clock.fixed(instant, c.zone())).now());

            assertThat(formatted).as("時區 %s", c.zone()).isEqualTo(c.expected())
                    .matches("\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d[+-]\\d\\d:\\d\\d");
        }
        assertThat(SiAuditSigner.formatTime(new SiAuditSigner(Clock.fixed(Instant.parse("2026-10-24T14:30:15.500Z"), ZoneOffset.UTC)).now()))
                .as("四捨五入會進到 :16；截斷停在 :15").endsWith("T14:30:15+00:00");
        assertThat(VECTOR_TIME).as("與 §5.1 向量的 time 同形").matches("\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d[+-]\\d\\d:\\d\\d");
    }
}
