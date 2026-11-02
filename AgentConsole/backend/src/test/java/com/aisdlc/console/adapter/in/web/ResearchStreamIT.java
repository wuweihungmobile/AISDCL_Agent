package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SseProbe;
import com.aisdlc.console.support.SseProbe.Frame;
import org.junit.jupiter.api.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.test.context.TestPropertySource;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 研究事件串流 {@code GET /api/v1/stream/research/{id}} 的整合測試（TCS-ResearchToPRD-P0 §3：AT-960-10-1、AT-960-10-2；契約 API-RP-05／06、ADR-003 D6）：
 * 真 HTTP 伺服器（RANDOM_PORT）＋真 PostgreSQL；測試扮演唯一的寫入者 Bridge，把事件寫進 append-only 的事件帳 {@code console.research_events}，
 * console-api 的每個連線自己尾隨事件帳。重播視窗在本測試的 context 注入為 20（TCS：「緩衝容量注入為 20」），輪詢間隔與 heartbeat 間隔取測試 profile 的短值
 * （poll 50 毫秒、heartbeat 2 秒）。
 */
@TestPropertySource(properties = "console.research.stream.replay-window=20")
class ResearchStreamIT extends AbstractResearchIT {

    private static final Logger LOG = LoggerFactory.getLogger(ResearchStreamIT.class);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Duration WAIT = Duration.ofSeconds(20);

    // ── 小工具 ───────────────────────────────────────────────────────────────────────────

    private SseProbe open(UUID id, String token, String lastEventId) {
        Map<String, String> headers = new LinkedHashMap<>();
        if (token != null) {
            headers.put("Authorization", "Bearer " + token);
        }
        if (lastEventId != null) {
            headers.put("Last-Event-ID", lastEventId);
        }
        return SseProbe.open(baseUrl() + "/api/v1/stream/research/" + id, headers);
    }

    /** 不含 heartbeat 的事件框架（依到達順序）：heartbeat 的時機取決於牆鐘，不是這些案例要斷言的內容。 */
    private static List<Frame> business(SseProbe probe) {
        return probe.events().stream().filter(frame -> !"heartbeat".equals(frame.event())).toList();
    }

    /** 等到不含 heartbeat 的事件框架至少 {@code count} 個（逾時就以目前收到的為準，由斷言報錯）。 */
    private static List<Frame> awaitBusiness(SseProbe probe, int count) {
        long deadline = System.nanoTime() + WAIT.toNanos();
        while (System.nanoTime() < deadline && business(probe).size() < count) {
            sleep(20);
        }
        return business(probe);
    }

    private static Map<String, Object> data(Frame frame) {
        return JSON.readValue(frame.data(), new TypeReference<Map<String, Object>>() { });
    }

    private static List<String> seqs(int from, int to) {
        return IntStream.rangeClosed(from, to).mapToObj(Integer::toString).toList();
    }

    // ── AT-960-10-1：單調遞增與延遲 ────────────────────────────────────────────────────────

    @Test
    void AT_960_10_1_theStreamCarriesEveryPushedEventInStrictlyIncreasingSeqWithP95LatencyUnder500ms() throws InterruptedException {
        UUID id = fx.project("stream-latency");
        try (SseProbe probe = open(id, viewer(), null)) {
            assertThat(probe.status()).as("VIEWER 可讀").isEqualTo(200);
            assertThat(probe.header("Content-Type")).startsWith("text/event-stream");
            Frame retry = probe.await(frame -> frame.retry() != null, Duration.ofSeconds(5));
            assertThat(retry).as("第一個框架是 retry:3000（瀏覽器 EventSource 的重連等待）").isNotNull();
            assertThat(retry.retry()).isEqualTo(3000);

            int total = 200;
            long[] seenAt = new long[total];
            CountDownLatch pushed = bridge().pushEvents(id, 1, total, 10);
            int seen = 0;
            long deadline = System.nanoTime() + Duration.ofSeconds(60).toNanos();
            while (seen < total && System.nanoTime() < deadline) {
                int available = probe.events("research.step").size();
                long now = System.currentTimeMillis();
                for (; seen < available && seen < total; seen++) {
                    seenAt[seen] = now;   // 接收時間＝該框架第一次被觀察到的牆鐘（高估至多一個觀察間隔，所以對 P95 斷言偏保守）
                }
                sleep(2);
            }
            assertThat(pushed.await(30, TimeUnit.SECONDS)).as("200 筆事件都已推送").isTrue();

            List<Frame> events = probe.events("research.step");
            assertThat(events).as("收到 200 筆").hasSize(total);
            assertThat(events).extracting(Frame::id).as("id 等於送出的 seq（1 到 200，無缺無重）").containsExactlyElementsOf(seqs(1, total));
            assertThat(SseProbe.strictlyIncreasing(events)).as("id 嚴格遞增").isTrue();
            assertThat(probe.events("research.replay_gap")).as("連續推送沒有缺口").isEmpty();

            List<Long> latencies = new ArrayList<>();
            for (int i = 0; i < total; i++) {
                Map<String, Object> data = data(events.get(i));
                assertThat(((Number) data.get("seq")).longValue()).as("data.seq 與 id 一致").isEqualTo(i + 1L);
                @SuppressWarnings("unchecked")
                Map<String, Object> payload = (Map<String, Object>) data.get("payload");
                latencies.add(seenAt[i] - ((Number) payload.get("emitted_at")).longValue());
            }
            Collections.sort(latencies);
            long p95 = latencies.get((int) Math.ceil(total * 0.95) - 1);
            LOG.info("AT-960-10-1 事件延遲（毫秒；輪詢 50、推送間隔 10）：p50={} p95={} max={}", latencies.get(total / 2), p95, latencies.get(total - 1));
            assertThat(p95).as("延遲 P95（毫秒；最大 %d）", latencies.get(total - 1)).isLessThan(500);
            assertThat(latencies.get(0)).as("沒有負延遲（同一個 JVM 的牆鐘）").isGreaterThanOrEqualTo(0);

            Map<String, Object> first = data(events.get(0));
            assertThat(first.keySet()).as("data 是 ResearchEvent（camelCase、保留 null 欄位）")
                    .containsExactlyInAnyOrder("seq", "eventType", "step", "actor", "refKind", "refId", "payload", "occurredAt");
            assertThat(first).containsEntry("eventType", "research.step").containsEntry("actor", "bridge").containsEntry("refKind", null);
            assertThat(String.valueOf(first.get("occurredAt"))).matches("\\d{4}-\\d{2}-\\d{2}T.*\\+00:00");

            Frame heartbeat = probe.awaitEvent("heartbeat", Duration.ofSeconds(10));
            assertThat(heartbeat).as("安靜下來之後每 heartbeat 間隔（測試注入 2 秒）送一則 heartbeat").isNotNull();
            assertThat(heartbeat.id()).as("heartbeat 是傳輸層訊號：沒有 id:").isNull();
            assertThat(heartbeat.data()).isEqualTo("{}");
            int firstHeartbeat = probe.eventNames().indexOf("heartbeat");
            assertThat(firstHeartbeat).as("事件持續流動時（每 10 毫秒一筆）不送 heartbeat：它出現在第 200 筆之後").isGreaterThanOrEqualTo(total);
        }
    }

    @Test
    void AT_960_10_1_aConnectionWithoutLastEventIdOnlyGetsEventsWrittenAfterItAndAGapOfTheLedgerIsAnnouncedBeforeTheNextEvent() {
        UUID id = fx.project("stream-live");
        fx.events(id, 1, 3);
        try (SseProbe probe = open(id, viewer(), null)) {
            sleep(400);
            assertThat(probe.events("research.step")).as("沒有 Last-Event-ID：不重播既有事件").isEmpty();

            fx.event(id, 4, "research.step", "{}");
            fx.event(id, 7, "research.step", "{}");   // 缺 5、6

            List<Frame> events = awaitBusiness(probe, 3);
            assertThat(events).extracting(Frame::event).containsExactly("research.step", "research.replay_gap", "research.step");
            assertThat(events).extracting(Frame::id).containsExactly("4", null, "7");
            assertThat(data(events.get(1))).as("尾隨中遇到序號不連續：先送缺口訊號再送下一筆").isEqualTo(Map.of("fromSeq", 5, "toSeq", 6));
        }
    }

    // ── AT-960-10-2：重連、缺口與回補 ─────────────────────────────────────────────────────

    @Test
    void AT_960_10_2_reconnectingInsideTheBufferReplaysTheMissedEventsExactlyOnceWithoutAGap() {
        UUID id = fx.project("replay-in-buffer");
        fx.events(id, 1, 60);
        try (SseProbe probe = open(id, viewer(), "45")) {
            assertThat(probe.status()).isEqualTo(200);
            awaitBusiness(probe, 15);
            sleep(500);   // 多等幾個輪詢間隔：恰一次＝之後不再有重播

            List<Frame> events = business(probe);
            assertThat(events).extracting(Frame::id).as("依序收到 46 至 60 恰一次").containsExactlyElementsOf(seqs(46, 60));
            assertThat(events).extracting(Frame::event).containsOnly("research.step");
            assertThat(probe.events("research.replay_gap")).as("沒有缺口訊號").isEmpty();
        }
    }

    @Test
    void AT_960_10_2_reconnectingBeyondTheBufferSendsTheGapSignalFirstAndThenTheAvailableEvents() {
        UUID id = fx.project("replay-expired");
        fx.events(id, 1, 60);
        long before = rows("research_events");
        try (SseProbe probe = open(id, viewer(), "5")) {
            List<Frame> events = awaitBusiness(probe, 21);
            sleep(300);
            events = business(probe);

            assertThat(events).as("1 則缺口訊號＋41 至 60 共 20 筆").hasSize(21);
            Frame gap = events.get(0);
            assertThat(gap.event()).as("伺服器先送缺口訊號").isEqualTo("research.replay_gap");
            assertThat(gap.id()).as("無 id: 行、不佔 seq").isNull();
            assertThat(data(gap)).as("fromSeq 為請求點加一、toSeq 為緩衝內最舊 seq 減一（camelCase）").isEqualTo(Map.of("fromSeq", 6, "toSeq", 40));
            assertThat(events.subList(1, events.size())).extracting(Frame::id).as("其後依序收到 41 至 60 恰一次").containsExactlyElementsOf(seqs(41, 60));
        }
        assertThat(rows("research_events")).as("缺口訊號不寫入事件帳").isEqualTo(before);
        assertThat(jdbc.queryForObject("select count(*) from console.research_events where event_type = 'research.replay_gap'", Long.class)).isZero();
    }

    @Test
    void AT_960_10_2_aSequenceGapInsideTheBufferIsAnnouncedAfterTheLastContiguousEvent() {
        UUID id = fx.project("replay-hole");
        fx.events(id, 1, 50);
        fx.events(id, 53, 60);   // 緩衝內缺 51 與 52
        try (SseProbe probe = open(id, viewer(), "45")) {
            List<Frame> events = awaitBusiness(probe, 14);
            sleep(300);
            events = business(probe);

            List<String> expected = new ArrayList<>(seqs(46, 50));
            expected.add("gap");
            expected.addAll(seqs(53, 60));
            assertThat(events).extracting(frame -> frame.id() == null ? "gap" : frame.id()).as("送完 46 至 50 後先送缺口訊號，再續送 53 起").containsExactlyElementsOf(expected);
            assertThat(events.get(5).event()).isEqualTo("research.replay_gap");
            assertThat(data(events.get(5))).isEqualTo(Map.of("fromSeq", 51, "toSeq", 52));
        }
    }

    @Test
    void AT_960_10_2_aMalformedOrFutureLastEventIdReplaysNothingAndRaisesNoGap() {
        UUID id = fx.project("replay-edge");
        fx.events(id, 1, 60);
        for (String lastEventId : List.of("abc", "-3", "999")) {
            try (SseProbe probe = open(id, viewer(), lastEventId)) {
                assertThat(probe.status()).as("Last-Event-ID=" + lastEventId + " 不報錯（EventSource 會原樣回送收到的最後 id）").isEqualTo(200);
                sleep(300);
                assertThat(business(probe)).as("Last-Event-ID=" + lastEventId + "：格式不合視為沒帶、超前者從最大序號起——都不重播也沒有缺口").isEmpty();
            }
        }
    }

    @Test
    void AT_960_10_2_restBackfillReturnsTheWholeTailAndAnOversizedLimitIsClampedTo500WithTheContinuationCursor() {
        UUID small = fx.project("backfill-small");
        fx.events(small, 1, 60);
        UUID large = fx.project("backfill-large");
        fx.events(large, 1, 600);

        Resp backfill = api.get(viewer(), RESEARCH + "/projects/" + small + "/events?afterSeq=5&limit=500");
        assertThat(backfill.status()).isEqualTo(200);
        assertThat(backfill.<List<Integer>>read("$.data.items[*].seq")).as("6 至 60 完整").containsExactlyElementsOf(IntStream.rangeClosed(6, 60).boxed().toList());
        assertThat(backfill.<Integer>read("$.data.nextSeq")).isEqualTo(60);
        assertThat(backfill.<Boolean>read("$.data.truncated")).isFalse();

        Resp clamped = api.get(viewer(), RESEARCH + "/projects/" + large + "/events?afterSeq=0&limit=501");
        assertThat(clamped.status()).as("limit 501 被夾到 500，不是 400").isEqualTo(200);
        assertThat(clamped.<List<Integer>>read("$.data.items[*].seq")).hasSize(500);
        assertThat(clamped.<Integer>read("$.data.items[0].seq")).isEqualTo(1);
        assertThat(clamped.<Integer>read("$.data.nextSeq")).isEqualTo(500);
        assertThat(clamped.<Boolean>read("$.data.truncated")).isTrue();

        Resp rest = api.get(viewer(), RESEARCH + "/projects/" + large + "/events?afterSeq=" + clamped.<Integer>read("$.data.nextSeq") + "&limit=500");
        assertThat(rest.<List<Integer>>read("$.data.items[*].seq")).as("以 nextSeq 接續就補齊 501 至 600").containsExactlyElementsOf(IntStream.rangeClosed(501, 600).boxed().toList());
        assertThat(rest.<Integer>read("$.data.nextSeq")).isEqualTo(600);
        assertThat(rest.<Boolean>read("$.data.truncated")).isFalse();

        assertThat(api.get(null, RESEARCH + "/projects/" + small + "/events?afterSeq=0").status()).as("匿名 GET 為 401").isEqualTo(401);
    }

    @Test
    void AT_960_10_2_authenticationAndRolesAreTheSameAsRestGetAndAnUnknownProjectIsA404WithTheResearchReason() {
        UUID id = fx.project("stream-auth");
        fx.events(id, 1, 3);

        for (String token : List.of(viewer(), operator(), admin())) {
            try (SseProbe probe = open(id, token, "0")) {
                assertThat(probe.status()).isEqualTo(200);
                assertThat(awaitBusiness(probe, 3)).extracting(Frame::id).containsExactly("1", "2", "3");
            }
        }
        try (SseProbe anonymous = open(id, null, null)) {
            assertThat(anonymous.status()).as("匿名 401").isEqualTo(401);
        }
        try (SseProbe viaQuery = SseProbe.open(baseUrl() + "/api/v1/stream/research/" + id + "?access_token=" + viewer(), Map.of())) {
            assertThat(viaQuery.status()).as("EventSource 不能帶標頭：?access_token= 與 Authorization 標頭兩者皆收").isEqualTo(200);
        }
        try (SseProbe unknown = open(UUID.randomUUID(), viewer(), null)) {
            assertThat(unknown.status()).isEqualTo(404);
            assertThat(unknown.rawBody()).contains("\"reason\":\"research_not_found\"");
        }
        fx.archive(id);
        try (SseProbe archived = open(id, viewer(), "1")) {
            assertThat(archived.status()).as("已封存的專案仍可讀").isEqualTo(200);
            assertThat(awaitBusiness(archived, 2)).extracting(Frame::id).containsExactly("2", "3");
        }
    }
}
