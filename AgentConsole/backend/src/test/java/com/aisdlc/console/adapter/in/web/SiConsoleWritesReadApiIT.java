package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractSiWriteIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Console 稽核列與 SelfImproving 帳本的對帳讀面（{@code GET /api/v1/si/console-writes}；TCS-SelfImprovingDecide-P2b：AT-933-2-E-1、935-5-1、
 * 935-5-2、935-5-E-1、935-5-E-2、935-5-E-3；W14）。為什麼重要：對帳是「Console 的決定有沒有真的進帳本」的唯一獨立證據——
 * 量不到卻顯示無待入帳、帳本有而 Console 沒有的項被漏報（偽造或遺失的徵兆）、回填誤動已有值的列、或讀路徑偷偷寫了別的東西，
 * 掌舵者都會被誤導；所以每個狀態都要有對應的輸出，且「量不到」必須與「沒有」分得開。
 */
class SiConsoleWritesReadApiIT extends AbstractSiWriteIT {

    private static final String PATH = SI + "/console-writes";

    private static String c5(int i) {
        return String.format("c5000000-0000-4000-8000-%012d", i);
    }

    private static List<Map<String, Object>> list(Object value) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) value;
        return items;
    }

    /** 回應 {@code items[]} 中 {@code auditRef} 相符的那一筆。 */
    private static Map<String, Object> itemOf(Resp resp, String auditRef) {
        return list(resp.read("$.data.items")).stream().filter(item -> auditRef.equals(item.get("auditRef"))).findFirst()
                .orElseThrow(() -> new AssertionError("回應的 items 沒有 " + auditRef));
    }

    private static Map<String, Object> goldenObservations() {
        return MiniBridge.Si.golden("A.snake").get("observations");
    }

    private Resp read(String token, String query) {
        return api.get(token, PATH + query);
    }

    /** MiniBridge 自上次 {@code MINI.si.reset()} 起對某個 SI 路徑（原始 URI，不含查詢字串）收到的請求數。 */
    private long pagesRequested(String uri) {
        return MINI.si.seen.stream().filter(seen -> uri.equals(seen.uri())).count();
    }

    // ── AT-933-2-E-1：decide 的對帳 ───────────────────────────────────────────────────────────────

    @Test
    void AT_933_2_E_1_aLedgerDecisionWithoutARowIsAnOrphanAndARowWithoutADecisionIsPending() {
        String r1 = ref("c1", 1);
        String r2 = ref("c1", 2);
        String r3 = ref("c1", 3);
        insertWrite(r1, "decide", PROP, D0, "2026-10-24T14:30:15Z");
        insertWrite(r3, "decide", PROP, D0, "2026-10-24T14:30:16Z");
        MINI.si.payloads.put("events", export("events", List.of(event(7, "dec", "console", r1, "prop", PROP),
                event(8, "dec", "console", r2, "prop", PROP)), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.reconcile.status")).isEqualTo("ok");
        assertThat(itemOf(resp, r1).get("ingested")).isEqualTo(true);
        assertThat(itemOf(resp, r3).get("ingested")).isEqualTo(false);
        assertThat(list(resp.read("$.data.orphans"))).singleElement().satisfies(orphan -> assertThat(orphan)
                .containsEntry("auditRef", r2).containsEntry("kind", "decide").containsEntry("subject", PROP));
    }

    // ── AT-935-5-1：三種 kind 的 ingested 旗標與欄位集合 ─────────────────────────────────────────────

    @Test
    void AT_935_5_1_ingestedFlagsForAllThreeKindsAndTheItemKeySetIsExact() {
        String decIn = ref("c2", 1);
        String decOut = ref("c2", 2);
        String addIn = ref("c2", 3);
        String addOut = ref("c2", 4);
        String closeIn = ref("c2", 5);
        String closeOut = ref("c2", 6);
        insertWrite(decIn, "decide", PROP, D0, "2026-10-24T14:30:11Z");
        insertWrite(decOut, "decide", PROP, D0, "2026-10-24T14:30:12Z");
        insertWrite(addIn, "obs-add", null, null, "2026-10-24T14:30:13Z");
        insertWrite(addOut, "obs-add", null, null, "2026-10-24T14:30:14Z");
        insertWrite(closeIn, "obs-close", OBS, null, "2026-10-24T14:30:15Z");
        insertWrite(closeOut, "obs-close", OBS, null, "2026-10-24T14:30:16Z");
        MINI.si.payloads.put("events", export("events", List.of(event(7, "dec", "console", decIn, "prop", PROP),
                event(8, "obs.add", "console", addIn, "obs", "OBS-SI-013"), event(9, "obs.close", "console", closeIn, "obs", OBS)),
                false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(observationRow("OBS-SI-013", "console", addIn, 20)),
                false, null));

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        for (String in : List.of(decIn, addIn, closeIn)) {
            assertThat(itemOf(resp, in).get("ingested")).as("已入帳 %s", in).isEqualTo(true);
        }
        for (String out : List.of(decOut, addOut, closeOut)) {
            assertThat(itemOf(resp, out).get("ingested")).as("待入帳 %s", out).isEqualTo(false);
        }
        assertThat(list(resp.read("$.data.items"))).hasSize(6).allSatisfy(item -> assertThat(item.keySet())
                .containsExactlyInAnyOrder("auditRef", "kind", "user", "role", "time", "subjectId", "digest", "keyId", "ingested"));
        assertThat(resp.<String>read("$.data.reconcile.status")).isEqualTo("ok");
        assertThat(resp.<Boolean>read("$.data.truncated")).isFalse();
        assertThat(list(resp.read("$.data.orphans"))).as("三個已入帳項都有對應列：沒有 orphan（空陣列，不是 null）").isEmpty();
        assertThat(resp.body()).doesNotContain("\"body\"").doesNotContain("\"mac\"");
    }

    // ── AT-935-5-2：subject_id 回填 ────────────────────────────────────────────────────────────────

    @Test
    void AT_935_5_2_backfillOnlyFillsNullIsIdempotentAndTouchesNothingElse() {
        String r4 = ref("c3", 4);
        String r5 = ref("c3", 5);
        insertWrite(r4, "obs-add", null, null, "2026-10-24T14:30:14Z");
        insertWrite(r5, "obs-add", "OBS-SI-012", null, "2026-10-24T14:30:15Z");
        MINI.si.payloads.put("events", export("events", List.of(), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(observationRow("OBS-SI-013", "console", r4, 20),
                observationRow("OBS-SI-014", "console", r5, 21)), false, null));
        List<Map<String, Object>> before = writeRows();

        Resp first = read(viewer(), "");
        Resp second = read(viewer(), "");

        assertThat(first.<Integer>read("$.data.reconcile.backfilled")).as("第一次回填 1 筆").isEqualTo(1);
        assertThat(second.<Integer>read("$.data.reconcile.backfilled")).as("第二次冪等：0 筆").isZero();
        assertThat(itemOf(first, r4).get("subjectId")).isEqualTo("OBS-SI-013");
        assertThat(itemOf(second, r5).get("subjectId")).as("已有值的列不動").isEqualTo("OBS-SI-012");
        List<Map<String, Object>> after = writeRows();
        assertThat(after).hasSameSizeAs(before);
        for (int i = 0; i < before.size(); i++) {
            Map<String, Object> expected = new LinkedHashMap<>(before.get(i));
            if (r4.equals(expected.get("audit_ref"))) {
                expected.put("subject_id", "OBS-SI-013");
            }
            assertThat(after.get(i)).as("除 R4 的 subject_id 外整列不變").isEqualTo(expected);
        }
        assertThat(MINI.requests()).as("Bridge 只被呼叫 GET").isNotEmpty().allSatisfy(r -> assertThat(r).startsWith("GET "));
    }

    // ── AT-935-5-E-1：orphans 的來源、排序與去重 ───────────────────────────────────────────────────

    @Test
    void AT_935_5_E_1_orphansListEventsFirstBySeqThenObservationRowsAndDeduplicateByAuditRef() {
        String x1 = ref("c4", 1);
        String x2 = ref("c4", 2);
        String x3 = ref("c4", 3);
        MINI.si.payloads.put("events", export("events", List.of(
                event(5, "dec", "transcript", null, "prop", PROP),
                event(7, "dec", "console", x1, "prop", PROP),
                event(8, "obs.close", "console", x2, "obs", OBS),
                event(9, "obs.add", "console", x3, "obs", "OBS-SI-013"),
                event(10, "app.sandbox", null, null, null, null)), false, null));
        Map<String, Object> observations = goldenObservations();
        list(observations.get("items")).add(observationRow("OBS-SI-013", "console", x3, 99));
        MINI.si.payloads.put("observations", observations);

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        List<Map<String, Object>> orphans = list(resp.read("$.data.orphans"));
        assertThat(orphans).as("事件側依 seq 升冪在前、觀察列側在後；同一 obs-add 只計一項；非 console 載體不列入").hasSize(4);
        assertThat(orphans.get(0)).containsEntry("auditRef", x1).containsEntry("kind", "decide").containsEntry("subject", PROP);
        assertThat(orphans.get(1)).containsEntry("auditRef", x2).containsEntry("kind", "obs-close").containsEntry("subject", OBS);
        assertThat(orphans.get(2)).containsEntry("auditRef", x3).containsEntry("kind", "obs-add").containsEntry("subject", "OBS-SI-013");
        assertThat(orphans.get(3)).containsEntry("kind", "obs-add").containsEntry("subject", "OBS-SI-009");
        assertThat(orphans).extracting(o -> o.get("auditRef")).doesNotHaveDuplicates();
    }

    // ── AT-935-5-E-2：量不到＝NOT-EVALUABLE，絕不冒充沒有 ─────────────────────────────────────────

    @Test
    void AT_935_5_E_2_aLedgerThatCannotBeReadIsNotEvaluableWithTheRowsStillReturnedAndNothingBackfilled() {
        insertWrite(ref("c6", 1), "decide", PROP, D0, "2026-10-24T14:30:11Z");
        insertWrite(ref("c6", 2), "obs-add", null, null, "2026-10-24T14:30:12Z");
        insertWrite(ref("c6", 3), "obs-close", OBS, null, "2026-10-24T14:30:13Z");
        List<Map<String, Object>> before = writeRows();
        List<Resp> responses = new ArrayList<>();
        List<String> expectedReasons = List.of("si_unavailable", "bridge_unreachable", "bridge_timeout", "scan_cap_exceeded", "scan_cap_exceeded");

        MINI.si.unavailable = Map.of("cause", "nonzero_rc", "detail", "rc=3; stderr=壞了");
        responses.add(read(viewer(), ""));
        MINI.si.reset();

        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        responses.add(read(viewer(), ""));
        resetSystemConfigs();
        thresholds.invalidate();

        readTimeout.cap(Duration.ofSeconds(1));
        MINI.si.delayMillis = 3_000;
        responses.add(read(viewer(), ""));
        MINI.si.reset();
        readTimeout.reset();

        // 頁數上限（W14：各 20 頁）要被釘住：events 先掃——observations 無窮時，events 一頁收斂、observations 恰 20 次分頁請求後放棄；
        // events 無窮時，events 恰 20 次就超限、observations 一頁都沒請求。改成 19、21 或 40 都會讓下面的恰值斷言紅。
        MINI.si.payloads.put("observations", export("observations", List.of(observationRow("OBS-SI-013", "console", ref("c6", 2), 20)),
                true, 5));
        responses.add(read(viewer(), ""));
        assertThat(pagesRequested("/si/events")).as("observations 無窮：events 一頁收斂").isEqualTo(1);
        assertThat(pagesRequested("/si/observations")).as("observations 無窮：恰 PAGE_CAP＝20 次分頁請求").isEqualTo(20);
        MINI.si.reset();

        MINI.si.payloads.put("events", export("events", List.of(event(9, "dec", "console", ref("c6", 1), "prop", PROP)), true, 5));
        responses.add(read(viewer(), ""));
        assertThat(pagesRequested("/si/events")).as("events 無窮：恰 PAGE_CAP＝20 次分頁請求").isEqualTo(20);
        assertThat(pagesRequested("/si/observations")).as("events 先超限：observations 一頁都沒請求").isZero();
        MINI.si.reset();

        for (int i = 0; i < responses.size(); i++) {
            Resp resp = responses.get(i);
            assertThat(resp.status()).as("情境 %d：仍是 200", i).isEqualTo(200);
            assertThat(resp.<String>read("$.data.reconcile.status")).as("情境 %d", i).isEqualTo("NOT-EVALUABLE");
            assertThat(resp.<String>read("$.data.reconcile.reason")).as("情境 %d", i).isEqualTo(expectedReasons.get(i));
            assertThat(resp.<Integer>read("$.data.reconcile.backfilled")).isZero();
            assertThat(list(resp.read("$.data.items"))).as("情境 %d：items 仍回", i).hasSize(3)
                    .allSatisfy(item -> assertThat(item).containsEntry("ingested", null));
            assertThat(resp.data()).as("orphans 為 null（不是空陣列）").containsEntry("orphans", null);
        }
        assertThat(writeRows()).as("沒有回填寫入").isEqualTo(before);
    }

    // ── AT-935-5-E-3：讀面邊界 ───────────────────────────────────────────────────────────────────────

    @Test
    void AT_935_5_E_3_authorizationLimitBoundsOrderingAndNoSecretsInTheResponse() {
        Instant base = Instant.parse("2026-10-24T10:00:00Z");
        for (int i = 1; i <= 130; i++) {
            insertWrite(c5(i), i % 2 == 0 ? "decide" : "obs-close", PROP, i % 2 == 0 ? D0 : null, base.plusSeconds(i).toString());
        }
        MINI.si.payloads.put("events", export("events", List.of(), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));

        assertThat(read(null, "").status()).as("無 token").isEqualTo(401);
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(read(token, "").status()).isEqualTo(200);
        }
        Resp defaults = read(viewer(), "");
        List<Map<String, Object>> items = list(defaults.read("$.data.items"));
        assertThat(items).as("預設回 100 列").hasSize(100);
        assertThat(defaults.<Boolean>read("$.data.truncated")).isTrue();
        assertThat(items.get(0)).containsEntry("auditRef", c5(130));
        for (int i = 1; i < items.size(); i++) {
            assertThat(OffsetDateTime.parse((String) items.get(i - 1).get("time")).toInstant()).as("時間新到舊")
                    .isAfterOrEqualTo(OffsetDateTime.parse((String) items.get(i).get("time")).toInstant());
        }
        Resp one = read(viewer(), "?limit=1");
        assertThat(list(one.read("$.data.items"))).hasSize(1);
        assertThat(one.<Boolean>read("$.data.truncated")).isTrue();
        Resp max = read(viewer(), "?limit=500");
        assertThat(list(max.read("$.data.items"))).hasSize(130);
        assertThat(max.<Boolean>read("$.data.truncated")).isFalse();
        for (String bad : List.of("?limit=0", "?limit=501", "?limit=abc", "?limit=-1", "?limit=1.5")) {
            assertThat(read(viewer(), bad).status()).as(bad).isEqualTo(400);
        }
        assertThat(defaults.body()).as("回應任何位置都沒有 body、mac 鍵").doesNotContain("\"body\"").doesNotContain("\"mac\"");
        assertThat(max.body()).doesNotContain("\"body\"").doesNotContain("\"mac\"");
        assertThat(MINI.requests()).as("Bridge 的請求全為 GET").isNotEmpty().allSatisfy(r -> assertThat(r).startsWith("GET "));
        assertThat(writeCount()).isEqualTo(130);
    }
}
