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
 * 935-5-2、935-5-E-1、935-5-E-2、935-5-E-3；W14；TCS-SelfImprovingDecideDedupe 的取代判定：AT-951-3-1、3-E-1、3-E-2、3-E-3；W-D3）。為什麼重要：對帳是「Console 的決定有沒有真的進帳本」的唯一獨立證據——
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
                .containsExactlyInAnyOrder("auditRef", "kind", "dkind", "user", "role", "time", "subjectId", "digest", "keyId", "ingested",
                        "supersededBy"));
        // 夾具列的 body 只有 fixture 鍵、沒有 dkind：decIn 與 decOut 同 subject、同 digest，若「dkind 為 null」被當成同一個決定，decOut 會被誤標為
        // 被 decIn 取代（TCS-SelfImprovingDecideDedupe ⚖6：看不出 dkind 的列不參與取代判定）
        assertThat(list(resp.read("$.data.items"))).allSatisfy(item -> {
            assertThat(item.get("dkind")).as("%s：body 沒有 dkind 鍵", item.get("auditRef")).isNull();
            assertThat(item.get("supersededBy")).as("%s：看不出 dkind 的列不被取代", item.get("auditRef")).isNull();
        });
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

    // ══ P4 兩種新 kind 的對帳（TCS-SelfImprovingSchedule：AT-964-9-4、9-5、9-E-2、9-E-3；W-S9 (e)；契約 P2c §4.2）══════════════════
    // 為什麼重要：排程設定與立即啟動請求的「待入帳」狀態是掌舵者唯一看得到的回饋——判準若把 run-request 以 sched.skip 入帳誤判成待入帳，
    // 畫面會永遠顯示「已送出待入帳」並讓軟停用鎖死按鈕；若把量不到判成已入帳或待入帳，掌舵者會被誤導。

    /** 帳本事件（P4 的三種新事件；{@code subject} 鍵一律省略：兩種新 kind 沒有對象）。 */
    private static Map<String, Object> schedEvent(int seq, String kind, String carrier, String auditRef) {
        return event(seq, kind, carrier, auditRef, null, null);
    }

    @Test
    void AT_964_9_4_theTwoNewKindsListWithNullSubjectDigestDkindAndSupersededByAndIngestedFollowsTheThreeEventKinds() {
        String a = ref("d9", 1);
        String b = ref("d9", 2);
        String c = ref("d9", 3);
        String d = ref("d9", 4);
        String decide = ref("d9", 5);
        insertWrite(a, "sched-set", null, null, "2026-10-24T14:30:11Z");
        insertWrite(b, "sched-set", null, null, "2026-10-24T14:30:12Z");
        insertWrite(c, "run-request", null, null, "2026-10-24T14:30:13Z");
        insertWrite(d, "run-request", null, null, "2026-10-24T14:30:14Z");
        insertDecide(decide, PROP, D0, "approve", "2026-10-24T14:30:15Z");
        MINI.si.payloads.put("events", export("events", List.of(schedEvent(1, "sched.set", "console", a),
                schedEvent(2, "run.open", "console", c), schedEvent(3, "sched.skip", "console", d),
                event(4, "dec", "console", decide, "prop", PROP)), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.reconcile.status")).isEqualTo("ok");
        for (String ref : List.of(a, b, c, d)) {
            Map<String, Object> item = itemOf(resp, ref);
            assertThat(item.get("kind")).as(ref).isIn("sched-set", "run-request");
            assertThat(item).as("%s：無對象、無 digest、不取代", ref).containsEntry("subjectId", null).containsEntry("digest", null)
                    .containsEntry("dkind", null).containsEntry("supersededBy", null);
            assertThat(item.keySet()).as("鍵集合仍為十一鍵")
                    .containsExactlyInAnyOrder("auditRef", "kind", "dkind", "user", "role", "time", "subjectId", "digest", "keyId", "ingested",
                            "supersededBy");
        }
        assertThat(itemOf(resp, a)).containsEntry("kind", "sched-set").containsEntry("ingested", true);
        assertThat(itemOf(resp, b)).containsEntry("kind", "sched-set").containsEntry("ingested", false);
        assertThat(itemOf(resp, c)).containsEntry("kind", "run-request").containsEntry("ingested", true);
        assertThat(itemOf(resp, d)).containsEntry("kind", "run-request").containsEntry("ingested", true);
        assertThat(itemOf(resp, decide)).as("既有 decide 列的判準與值不變").containsEntry("kind", "decide").containsEntry("dkind", "approve")
                .containsEntry("subjectId", PROP).containsEntry("ingested", true);
        assertThat(list(resp.read("$.data.orphans"))).as("四個新 kind 列都有對應列：沒有 orphan").isEmpty();
    }

    @Test
    void AT_964_9_5_orphansMapTheThreeEventKindsToTheTwoNewKindsInSeqOrderDeduplicateByAuditRefAndSkipNonConsoleCarriers() {
        String x1 = ref("d9", 11);
        String x2 = ref("d9", 12);
        String x3 = ref("d9", 13);
        String x4 = ref("d9", 14);
        MINI.si.payloads.put("events", export("events", List.of(
                schedEvent(1, "sched.set", "console", x1),
                schedEvent(2, "sched.set", "console", x1),
                schedEvent(3, "run.open", "console", x2),
                schedEvent(4, "sched.skip", "console", x3),
                schedEvent(5, "sched.set", "transcript", x4)), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        List<Map<String, Object>> orphans = list(resp.read("$.data.orphans"));
        assertThat(orphans).as("兩筆同 audit_ref 的 sched.set 去重為一；carrier 非 console 者不入列").hasSize(3);
        assertThat(orphans.get(0)).containsEntry("auditRef", x1).containsEntry("kind", "sched-set").containsEntry("subject", null);
        assertThat(orphans.get(1)).containsEntry("auditRef", x2).containsEntry("kind", "run-request").containsEntry("subject", null);
        assertThat(orphans.get(2)).containsEntry("auditRef", x3).containsEntry("kind", "run-request").containsEntry("subject", null);
        assertThat(orphans).extracting(o -> o.get("auditRef")).doesNotContain(x4).doesNotHaveDuplicates();
    }

    @Test
    void AT_964_9_E_2_whenTheLedgerCannotBeReadTheNewKindsAreNeitherIngestedNorPending() {
        String sched = ref("d9", 21);
        String run = ref("d9", 22);
        insertWrite(sched, "sched-set", null, null, "2026-10-24T14:30:11Z");
        insertWrite(run, "run-request", null, null, "2026-10-24T14:30:12Z");

        MINI.si.unavailable = Map.of("cause", "nonzero_rc", "detail", "rc=3; stderr=壞了");
        Resp unavailable = read(viewer(), "");
        MINI.si.reset();
        MINI.si.payloads.put("events", export("events", List.of(schedEvent(1, "sched.set", "console", sched)), true, 5));
        Resp capped = read(viewer(), "");

        for (Resp resp : List.of(unavailable, capped)) {
            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.<String>read("$.data.reconcile.status")).isEqualTo("NOT-EVALUABLE");
            assertThat(list(resp.read("$.data.items"))).hasSize(2).allSatisfy(item -> assertThat(item).containsEntry("ingested", null)
                    .containsEntry("supersededBy", null));
            assertThat(resp.data()).containsEntry("orphans", null);
        }
        assertThat(unavailable.<String>read("$.data.reconcile.reason")).isEqualTo("si_unavailable");
        assertThat(capped.<String>read("$.data.reconcile.reason")).isEqualTo("scan_cap_exceeded");
    }

    @Test
    void AT_964_9_E_3_aRunRequestIngestedAsASchedSkipCountsAsIngestedAndIsNotAnOrphan() {
        String run = ref("d9", 31);
        insertWrite(run, "run-request", null, null, "2026-10-24T14:30:12Z");
        Map<String, Object> skip = schedEvent(3, "sched.skip", "console", run);
        skip.put("reason", "run-open");
        MINI.si.payloads.put("events", export("events", List.of(skip), false, null));
        MINI.si.payloads.put("observations", export("observations", List.of(), false, null));

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(itemOf(resp, run)).as("只有 sched.skip、沒有 run.open：請求已被消耗，算已入帳").containsEntry("ingested", true);
        assertThat(list(resp.read("$.data.orphans"))).as("有對應列：不是 orphan").isEmpty();
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
                    .allSatisfy(item -> assertThat(item).containsEntry("ingested", null).containsEntry("supersededBy", null));
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

    // ══ 取代判定（TCS-SelfImprovingDecideDedupe：AT-951-3-1、3-E-1、3-E-2、3-E-3；W-D3；NFR-DD-2、DD-3、DD-4）══════════════════════════════════
    // 為什麼重要：OBS-SI-348——同一個決定落了四份稽核檔，主機端只能入帳一份，其餘三份永遠顯示待入帳而誤導掌舵者。取代判定要「找得到該標的」
    // （事故形狀）、「找對那一個」（最早者、同刻字串序、不受 limit 影響）、「不該標的絕不標」（不同決定、無 digest 的動詞、看不出 dkind、orphan）、
    // 「量不到就不標」（NOT-EVALUABLE 時與 ingested 一起為 null）；標錯方向的代價不對稱——誤標會把一個真正待入帳的決定從待辦清單藏起來。

    private static final String EVENTS = "events";
    private static final String OBSERVATIONS = "observations";

    private static String t(int minute) {
        return String.format("2026-10-31T09:%02d:00Z", minute);
    }

    private void ledger(List<Map<String, Object>> events) {
        MINI.si.payloads.put(EVENTS, export(EVENTS, events, false, null));
        MINI.si.payloads.put(OBSERVATIONS, export(OBSERVATIONS, List.of(), false, null));
    }

    // ── AT-951-3-1：事故形狀 ─────────────────────────────────────────────────────────────────────────

    @Test
    void AT_951_3_1_theIncidentShapeFourFilesForOneDecisionOnlyOneIngestedTheOtherThreeAreSupersededButStayNotIngested() {
        String r1 = ref("e1", 1);
        String r2 = ref("e1", 2);
        String r3 = ref("e1", 3);
        String r4 = ref("e1", 4);
        insertDecide(r1, PROP, D0, "promote", "2026-10-31T10:19:51Z");
        insertDecide(r2, PROP, D0, "promote", "2026-10-31T10:20:30Z");
        insertDecide(r3, PROP, D0, "promote", "2026-10-31T10:21:00Z");
        insertDecide(r4, PROP, D0, "promote", "2026-10-31T10:21:26Z");
        ledger(List.of(event(7, "dec", "console", r1, "prop", PROP)));

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.reconcile.status")).isEqualTo("ok");
        for (String pending : List.of(r2, r3, r4)) {
            assertThat(itemOf(resp, pending)).as("%s 待入帳而被取代", pending).containsEntry("ingested", false).containsEntry("supersededBy", r1)
                    .containsEntry("dkind", "promote");
        }
        assertThat(itemOf(resp, r1)).as("已入帳的那一份").containsEntry("ingested", true).containsEntry("supersededBy", null);
        assertThat(list(resp.read("$.data.items"))).hasSize(4).allSatisfy(item -> assertThat(item.keySet()).containsExactlyInAnyOrder("auditRef",
                "kind", "dkind", "user", "role", "time", "subjectId", "digest", "keyId", "ingested", "supersededBy"));
        assertThat(list(resp.read("$.data.orphans"))).as("沒有 orphan（空陣列）").isEmpty();
        assertThat(resp.body()).doesNotContain("\"body\"").doesNotContain("\"mac\"");
    }

    // ── AT-951-3-E-1：最早者、同刻字串序、與 limit 無關 ────────────────────────────────────────────────

    @Test
    void AT_951_3_E_1_theEarliestIngestedTwinWinsTiesGoByStringOrderAndTheVerdictIgnoresLimit() {
        String a1 = ref("e2", 1);
        String a2 = ref("e2", 2);
        String p1 = ref("e2", 3);
        String p2 = ref("e2", 4);
        // 組 A：A1（09:00）與 A2（10:00）已入帳，P1（11:00）待入帳；組 B：同刻（09:00）已入帳的 B1（UT1）與 B2（UT2，先插入），P2（10:30）待入帳
        insertDecide(a2, PROP, D0, "approve", "2026-10-31T10:00:00Z");
        insertDecide(a1, PROP, D0, "approve", "2026-10-31T09:00:00Z");
        insertDecide(p1, PROP, D0, "approve", "2026-10-31T11:00:00Z");
        insertDecide(UT2, PROP5, D0, "approve", "2026-10-31T09:00:00Z");
        insertDecide(UT1, PROP5, D0, "approve", "2026-10-31T09:00:00Z");
        insertDecide(p2, PROP5, D0, "approve", "2026-10-31T10:30:00Z");
        ledger(List.of(event(1, "dec", "console", a1, "prop", PROP), event(2, "dec", "console", a2, "prop", PROP),
                event(3, "dec", "console", UT1, "prop", PROP5), event(4, "dec", "console", UT2, "prop", PROP5)));

        Resp byDefault = read(viewer(), "");
        Resp one = read(viewer(), "?limit=1");

        assertThat(itemOf(byDefault, p1).get("supersededBy")).as("P1 的取代者是 time 最早的 A1，不是 A2").isEqualTo(a1);
        assertThat(itemOf(byDefault, p2).get("supersededBy")).as("P2 的取代者是同刻中字串序較小的 UT1，不是 UUID.compareTo 判較小的 UT2").isEqualTo(UT1);
        assertThat(list(one.read("$.data.items"))).as("limit=1 只含最新的一列 P1").singleElement()
                .satisfies(item -> assertThat(item).containsEntry("auditRef", p1).containsEntry("supersededBy", a1));
        assertThat(one.<Boolean>read("$.data.truncated")).isTrue();
    }

    // ── AT-951-3-E-2：量不到＝整欄 null ──────────────────────────────────────────────────────────────────

    @Test
    void AT_951_3_E_2_whenTheLedgerCannotBeReadSupersededByIsNullJustLikeIngested() {
        for (int i = 1; i <= 4; i++) {
            insertDecide(ref("e3", i), PROP, D0, "promote", t(i));
        }
        List<Map<String, Object>> before = writeRows();
        List<Resp> responses = new ArrayList<>();

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

        List<String> expectedReasons = List.of("si_unavailable", "bridge_unreachable", "bridge_timeout");
        for (int i = 0; i < responses.size(); i++) {
            Resp resp = responses.get(i);
            assertThat(resp.status()).as("情境 %d：仍是 200", i).isEqualTo(200);
            assertThat(resp.<String>read("$.data.reconcile.status")).as("情境 %d", i).isEqualTo("NOT-EVALUABLE");
            assertThat(resp.<String>read("$.data.reconcile.reason")).as("情境 %d", i).isEqualTo(expectedReasons.get(i));
            assertThat(list(resp.read("$.data.items"))).as("情境 %d：items 仍含四列", i).hasSize(4)
                    .allSatisfy(item -> assertThat(item).containsEntry("ingested", null).containsEntry("supersededBy", null));
            assertThat(resp.data()).as("情境 %d：orphans 為 null", i).containsEntry("orphans", null);
        }
        assertThat(writeRows()).as("表內各列逐位元組不變").isEqualTo(before);
    }

    // ── AT-951-3-E-3：不該取代的情形一律不取代 ──────────────────────────────────────────────────────────

    @Test
    void AT_951_3_E_3_nothingThatIsNotTheSameDecisionIsEverSuperseded() {
        // (a) 已入帳的 approve 與其下三列待入帳者：不同 dkind、不同 digest、不同對象
        String a0 = ref("e4", 1);
        String aReject = ref("e4", 2);
        String aDigest = ref("e4", 3);
        String aOther = ref("e4", 4);
        insertDecide(a0, PROP, D0, "approve", t(1));
        insertDecide(aReject, PROP, D0, "reject", t(2));
        insertDecide(aDigest, PROP, D1, "approve", t(3));
        insertDecide(aOther, PROP5, D0, "approve", t(4));
        // (b) 兩列皆未入帳的 approve：互不取代
        String b1 = ref("e4", 5);
        String b2 = ref("e4", 6);
        insertDecide(b1, PROP6, D0, "approve", t(5));
        insertDecide(b2, PROP6, D0, "approve", t(6));
        // (c) 待入帳的 obs-close 與已入帳的 obs-close（同對象）：非 decide 不參與
        String cPending = ref("e4", 7);
        String cIngested = ref("e4", 8);
        insertWrite(cPending, "obs-close", OBS, null, t(7));
        insertWrite(cIngested, "obs-close", OBS, null, t(8));
        // (d) 兩列只含 fixture 鍵、沒有 dkind 的 decide（同 subject、同 digest）：一列已入帳、一列待入帳——看不出 dkind 的列不參與
        String dIngested = ref("e4", 9);
        String dPending = ref("e4", 10);
        insertWrite(dIngested, "decide", PROP6, D1, t(9));
        insertWrite(dPending, "decide", PROP6, D1, t(10));
        // (e) 待入帳的 return；帳本裡同 prop、同 digest、dkind 為 return、carrier 為 console 的 dec，其 audit_ref 不在表內（orphan，不充當取代者）
        String ePending = ref("e4", 11);
        String eOrphan = ref("e4", 12);
        insertDecide(ePending, PROP5, D0, "return", t(11));
        Map<String, Object> orphanEvent = event(20, "dec", "console", eOrphan, "prop", PROP5);
        orphanEvent.put("digest", D0);
        orphanEvent.put("dkind", "return");
        // (f) 無 digest 的動詞：resume（RUN）與 rollback（PROP）都是先一列已入帳、其後一列待入帳（同 subject、同 dkind、digest 皆為 null）
        String resumeIngested = ref("e4", 13);
        String resumePending = ref("e4", 14);
        String rollbackIngested = ref("e4", 15);
        String rollbackPending = ref("e4", 16);
        insertDecide(resumeIngested, RUN, null, "resume", t(13));
        insertDecide(resumePending, RUN, null, "resume", t(14));
        insertDecide(rollbackIngested, PROP, null, "rollback", t(15));
        insertDecide(rollbackPending, PROP, null, "rollback", t(16));
        ledger(List.of(event(10, "dec", "console", a0, "prop", PROP), event(11, "obs.close", "console", cIngested, "obs", OBS),
                event(12, "dec", "console", dIngested, "prop", PROP6), orphanEvent,
                event(13, "dec", "console", resumeIngested, "run", RUN), event(14, "dec", "console", rollbackIngested, "prop", PROP)));

        Resp resp = read(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.reconcile.status")).isEqualTo("ok");
        Map<String, String> pendingLabels = new LinkedHashMap<>();
        pendingLabels.put(aReject, "(a) 不同 dkind");
        pendingLabels.put(aDigest, "(a) 不同 digest");
        pendingLabels.put(aOther, "(a) 不同對象");
        pendingLabels.put(b1, "(b) 兩列皆未入帳 #1");
        pendingLabels.put(b2, "(b) 兩列皆未入帳 #2");
        pendingLabels.put(cPending, "(c) obs-close");
        pendingLabels.put(dPending, "(d) 看不出 dkind 的 decide");
        pendingLabels.put(ePending, "(e) 取代者不在表內（orphan）");
        pendingLabels.put(resumePending, "(f) 第二次合法的 resume");
        pendingLabels.put(rollbackPending, "(f) 第二個 rollback");
        pendingLabels.forEach((pendingRef, label) -> assertThat(itemOf(resp, pendingRef)).as(label).containsEntry("ingested", false)
                .containsEntry("supersededBy", null));
        for (String ingested : List.of(a0, cIngested, dIngested, resumeIngested, rollbackIngested)) {
            assertThat(itemOf(resp, ingested)).as("已入帳列 %s", ingested).containsEntry("ingested", true).containsEntry("supersededBy", null);
        }
        assertThat(list(resp.read("$.data.items"))).as("全部 items 沒有任何一列的 supersededBy 非 null（十五列：十列待入帳、五列已入帳）").hasSize(15)
                .allSatisfy(item -> assertThat(item.get("supersededBy")).isNull());
        assertThat(list(resp.read("$.data.orphans"))).as("(e) 那一筆帳本項出現在 orphans").singleElement()
                .satisfies(orphan -> assertThat(orphan).containsEntry("auditRef", eOrphan).containsEntry("kind", "decide").containsEntry("subject", PROP5));
    }
}
